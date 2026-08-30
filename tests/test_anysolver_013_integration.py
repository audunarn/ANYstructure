"""Focused extraction-era ANYsolver application-boundary regressions.

This module intentionally imports only the FEM integration layer.  Keeping
these contract checks separate from the broad GUI regression module makes
version, option-wiring, and fail-closed failures quick to isolate.
"""

from dataclasses import fields
import json
from pathlib import Path
import types

import pytest

import anysolver
from anystruct import fem_integration
from anysolver import runtime as anysolver_runtime


class _Plate:
    girder_lg = 3.5

    def get_structure_type(self):
        return "Flat plate, stiffened"

    def get_span(self):
        return 2.5

    def get_s(self):
        return 0.75

    def get_pl_thk(self):
        return 0.012

    def get_puls_up_boundary(self):
        return "SSSS"


class _StructureBundle:
    Plate = _Plate()
    Stiffener = object()
    Girder = object()
    _panel_length_Lp = None


def _snapshot():
    return fem_integration.RuntimeFEMLineSnapshot(
        line_name="line1",
        line_points=(1, 2),
        structure_bundle=[_StructureBundle(), None, None, object(), None, None],
        pressure_pa=12_345.0,
        torsional_moment_nm=222.0,
        shear_force_n=333.0,
        domain="Flat plate, stiffened",
        is_cylinder=False,
    )


def test_runtime_options_cover_and_map_solver_fields():
    option_names = {item.name for item in fields(fem_integration.RuntimeFEMOptions)}
    solver_names = {item.name for item in fields(anysolver_runtime.LightweightFEMConfig)}
    assert solver_names <= option_names

    config = fem_integration._solver_config_from_options(
        fem_integration.RuntimeFEMOptions(
            torsional_moment_nm=12_345.0,
            shear_force_n=-6_789.0,
            follower_pressure=True,
            collision_damage_criterion="mesh_scaled_gl",
            collision_penalty_scale=0.725,
        )
    )

    assert config.torsional_moment_nm == pytest.approx(12_345.0)
    assert config.shear_force_n == pytest.approx(-6_789.0)
    assert config.follower_pressure is True
    assert config.collision_damage_criterion == "mesh_scaled_gl"
    assert config.collision_penalty_scale == pytest.approx(0.725)


def test_failed_production_status_is_not_replaced_by_lightweight_result(monkeypatch):
    def fake_failed_production(
        geometry,
        config,
        status_callback=None,
        imported_fem_model=None,
        precomputed_generated_geometry=None,
    ):
        native = types.SimpleNamespace(
            outcome=anysolver.SolveOutcome.stopped(
                "minimum_load_increment_reached",
                control_kind="load_factor",
                requested_control=1.0,
                achieved_control=0.42,
                last_converged_increment=7,
            ),
            displacements=[0.0] * 6,
            reactions={1: (-3.0, 0.0, 0.0, 0.0, 0.0, 0.0)},
        )
        return anysolver_runtime.LightweightFEMResult(
            status="nonlinear_not_converged",
            stress_max_pa=0.0,
            stress_p95_pa=0.0,
            displacement_max_m=0.0,
            diagnostics=("production solve did not converge",),
            mesh_info={"nodes": 4, "shells": 1, "beams": 0},
            prestress_summary={"nonlinear_status": "not_converged"},
            load_resultant={},
            visualization={},
            solver_name="ANYsolver production",
            result_carrier=native,
        )

    def forbidden_lightweight_fallback(*args, **kwargs):
        raise AssertionError("failed production must not run a lightweight fallback")

    monkeypatch.setattr(
        fem_integration.fe_solver, "run_production_fem", fake_failed_production
    )
    monkeypatch.setattr(
        fem_integration.fe_solver,
        "run_lightweight_fem",
        forbidden_lightweight_fallback,
    )

    result = fem_integration.run_runtime_fem(
        _snapshot(), fem_integration.RuntimeFEMOptions()
    )

    assert result.status == "nonlinear_not_converged"
    assert result.summary["solver"] == "ANYsolver production"
    assert result.summary["prestress_summary"]["nonlinear_status"] == "not_converged"
    assert result.summary["solve_outcome"]["disposition"] == "partial"
    assert result.summary["solve_outcome"]["control_kind"] == "load_factor"
    assert result.summary["solve_outcome"]["achieved_control"] == pytest.approx(0.42)
    assert {
        item["quantity_id"] for item in result.summary["result_quantities"]
    } >= {"displacement", "reaction"}
    assert [
        item["quantity_id"] for item in result.summary["reaction_quantities"]
    ] == ["reaction"]
    assert "production solve did not converge" in result.diagnostics
    assert not any("compact fallback" in item.lower() for item in result.diagnostics)


def test_anysolver_version_guard_rejects_pre_extraction_0_1_3(monkeypatch):
    monkeypatch.setattr(fem_integration._anysolver_package, "__version__", "0.1.3")

    with pytest.raises(RuntimeError, match=r"requires ANYsolver>=0\.4\.0"):
        fem_integration._solver_config_from_options(
            fem_integration.RuntimeFEMOptions(shear_force_n=321.0)
        )


def test_anysolver_version_guard_rejects_published_0_1_2(monkeypatch):
    monkeypatch.setattr(fem_integration._anysolver_package, "__version__", "0.1.2")

    with pytest.raises(RuntimeError, match=r"requires ANYsolver>=0\.4\.0"):
        fem_integration._solver_config_from_options(
            fem_integration.RuntimeFEMOptions()
        )


def test_anysolver_version_guard_rejects_0_2_9(monkeypatch):
    monkeypatch.setattr(fem_integration._anysolver_package, "__version__", "0.2.9")

    with pytest.raises(RuntimeError, match=r"requires ANYsolver>=0\.4\.0"):
        fem_integration._require_supported_anysolver()


def test_anysolver_version_guard_rejects_pre_activation_0_3_0(monkeypatch):
    monkeypatch.setattr(fem_integration._anysolver_package, "__version__", "0.3.0")

    with pytest.raises(RuntimeError, match=r"ANYsolver>=0\.4\.0"):
        fem_integration._require_supported_anysolver()


def test_anysolver_version_guard_accepts_newer_0_4_0(monkeypatch):
    monkeypatch.setattr(fem_integration._anysolver_package, "__version__", "0.4.0")

    assert fem_integration._require_supported_anysolver() == "0.4.0"


@pytest.mark.parametrize("suffix", (".fem.json", ".fem.json.gz"))
def test_saved_state_round_trips_solver_inputs(tmp_path, suffix):
    options = fem_integration.RuntimeFEMOptions(
        torsional_moment_nm=4321.0,
        shear_force_n=8765.0,
        follower_pressure=True,
        collision_damage_criterion="fixed",
        collision_penalty_scale=0.625,
    )
    path = tmp_path / ("state" + suffix)

    fem_integration.save_runtime_fem_state(path, options, snapshot=_snapshot())
    state = fem_integration.load_runtime_fem_state(path)

    assert state["options"] == options
    assert state["snapshot"]["torsional_moment_nm"] == pytest.approx(222.0)
    assert state["snapshot"]["shear_force_n"] == pytest.approx(333.0)


@pytest.mark.parametrize(
    ("container", "field"),
    (("options", "pressure_pa"), ("result", "displacement_scale")),
)
def test_saved_state_rejects_finite_syntax_numeric_overflow(
    tmp_path, container, field
):
    state = fem_integration.runtime_fem_state_to_dict(
        fem_integration.RuntimeFEMOptions(),
        result=fem_integration.RuntimeFEMRunResult(
            status="ok", summary={}, displacement_scale=0.0
        ),
    )
    state[container][field] = "OVERFLOW_SENTINEL"
    text = json.dumps(state, allow_nan=False, separators=(",", ":"), sort_keys=True)
    text = text.replace('"OVERFLOW_SENTINEL"', "1e999", 1)
    path = tmp_path / "overflow.fem.json"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="nonfinite JSON number"):
        fem_integration.load_runtime_fem_state(path)


def test_fem_gui_uses_visible_horizontal_and_vertical_pane_handles():
    source = Path(fem_integration.__file__).read_text(encoding="utf-8")

    assert "def _visible_paned_window(parent: Any, orient: str) -> tk.PanedWindow:" in source
    assert "panes = tk.PanedWindow(" in source
    assert "sashwidth=6" in source
    assert "sashrelief=tk.FLAT" in source
    assert "showhandle=False" in source
    assert 'panes.bind("<Motion>", highlight_divider, add="+")' in source
    assert "self.body_panes = self._visible_paned_window(outer, tk.HORIZONTAL)" in source
    assert 'self.body_panes.add(left_panel, minsize=260, width=300, stretch="always")' in source
    assert 'self.body_panes.add(mid_panel, minsize=340, width=390, stretch="always")' in source
    assert 'self.body_panes.add(right_panel, minsize=360, width=470, stretch="always")' in source
    assert "self.result_panes = self._visible_paned_window(right_panel, tk.VERTICAL)" in source
    assert 'self.result_panes.add(self.upper_result_frame, minsize=120, height=190, stretch="always")' in source
    assert 'self.result_panes.add(result_frame, minsize=260, height=430, stretch="always")' in source


def test_fem_gui_uses_supported_runtime_analysis_api():
    source = Path(fem_integration.__file__).read_text(encoding="utf-8")

    assert "selection = fe_solver.resolve_runtime_analysis(config)" in source
    assert "fe_solver._wants_" not in source
    assert "fe_solver._nonlinear_solution_control" not in source
    assert "fe_solver._effective_nonlinear_static_kinematics" not in source


def test_arc_length_keeps_corotational_and_follower_controls_selectable():
    class Var:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

    window = types.SimpleNamespace(
        collision_enabled=Var(False),
        runtime_solver=Var("nonlinear static"),
        analysis_type=Var("geometric nonlinear static"),
        nonlinear_solution_control=Var("arc length"),
        nonlinear_static_kinematics=Var("Corotational"),
        custom_time_domain_enabled=Var(False),
    )
    window._choice_key = fem_integration.RuntimeFEMWindow._choice_key
    window._static_kinematics_selector_enabled = types.MethodType(
        fem_integration.RuntimeFEMWindow._static_kinematics_selector_enabled,
        window,
    )
    window._follower_pressure_selector_enabled = types.MethodType(
        fem_integration.RuntimeFEMWindow._follower_pressure_selector_enabled,
        window,
    )

    assert window._static_kinematics_selector_enabled() is True
    assert window._follower_pressure_selector_enabled() is True
    assert window.nonlinear_static_kinematics.get() == "Corotational"
    assert anysolver_runtime._effective_nonlinear_static_kinematics(
        anysolver_runtime.LightweightFEMConfig(
            analysis_type="geometric nonlinear static",
            nonlinear_solution_control="arc length",
            nonlinear_static_kinematics="corotational",
        )
    ) == "corotational"
