from matplotlib.figure import Figure
from pathlib import Path
import json
import math

import numpy as np
import pytest

from anystruct import api, fe_plate_fields, fem_integration as fe_runtime_solver
from anysolver import runtime as fe_solver


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


class _PlateWithMixedSupports(_Plate):
    def get_puls_up_boundary(self):
        return "CSSC"


class _TMember:
    stiffener_type = "T"

    def __init__(self, spacing=0.75, web_h=0.4, web_t=0.012, flange_w=0.15, flange_t=0.02):
        self._spacing = spacing
        self._web_h = web_h
        self._web_t = web_t
        self._flange_w = flange_w
        self._flange_t = flange_t

    @property
    def hw(self):
        return self._web_h * 1000.0

    @property
    def tw(self):
        return self._web_t * 1000.0

    @property
    def b(self):
        return self._flange_w * 1000.0

    @property
    def tf(self):
        return self._flange_t * 1000.0

    def get_s(self):
        return self._spacing


class _AllStructure:
    Plate = _Plate()
    Stiffener = object()
    Girder = object()
    _panel_length_Lp = None


class _FakeApp:
    _active_line = "line1"
    _line_dict = {"line1": [1, 2]}
    _line_to_struc = {"line1": [_AllStructure(), None, None, object(), None, None]}

    def get_highest_pressure(self, line):
        assert line == "line1"
        return {"normal": 12345.0}


class _AllStructureMixedSupports(_AllStructure):
    Plate = _PlateWithMixedSupports()


class _FakeAppMixedSupports(_FakeApp):
    _line_to_struc = {"line1": [_AllStructureMixedSupports(), None, None, object(), None, None]}


class _AllStructureWithFlatMembers:
    Plate = _Plate()
    Stiffener = _TMember(spacing=0.75, web_h=0.4, web_t=0.012, flange_w=0.15, flange_t=0.02)
    Girder = _TMember(spacing=1.25, web_h=0.8, web_t=0.02, flange_w=0.20, flange_t=0.03)
    _panel_length_Lp = 7.5


class _FakeAppFlatMembers(_FakeApp):
    _line_to_struc = {"line1": [_AllStructureWithFlatMembers(), None, None, object(), None, None]}


class _SimpleVar:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


class _CylinderForces:
    geometry = 7
    psd = -200000.0

    def get_main_properties(self):
        return {
            "psd": [-200000.0, "Pa"],
            "cone Nsd": [1234.0, "kN"],
            "cone M1sd": [5678.0, "kNm"],
        }


class _FakeCylinderForceApp(_FakeApp):
    _line_to_struc = {"line1": [None, None, None, None, None, _CylinderForces()]}
    _new_shell_Nsd = _SimpleVar(499999.999)
    _new_shell_Msd = _SimpleVar(500000.0)
    _new_shell_psd = _SimpleVar(-0.3)

    def get_highest_pressure(self, line):
        assert line == "line1"
        return {"normal": 0.0}


def test_active_line_snapshot_uses_current_anystructure_line():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())

    assert snapshot.line_name == "line1"
    assert snapshot.line_points == [1, 2]
    assert snapshot.pressure_pa == 12345.0
    assert snapshot.axial_force_n == 0.0
    assert snapshot.top_bottom_moment_nm == 0.0
    assert snapshot.domain == "Flat plate, stiffened"
    assert snapshot.is_cylinder is False


def test_active_line_snapshot_transfers_selected_cylinder_force_loads_to_fem_defaults():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeCylinderForceApp())

    assert snapshot.pressure_pa == pytest.approx(300000.0)
    assert snapshot.axial_force_n == pytest.approx(499999999.0)
    assert snapshot.top_bottom_moment_nm == pytest.approx(500000000.0)
    assert snapshot.is_cylinder is True


def test_runtime_geometry_summary_reads_flat_panel_dimensions_and_members():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())

    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    assert summary["geometry"] == "flat panel"
    assert summary["length_m"] == 5.0
    assert summary["width_m"] == 3.5
    assert summary["thickness_m"] == 0.012
    assert summary["has_stiffener"] is True
    assert summary["has_girder"] is True
    assert summary["stiffener_spacing_m"] == 0.75
    assert summary["girder_spacing_m"] == 2.5
    assert summary["girder_length_m"] == 3.5
    assert summary["plate_edge_supports"] == ("simply supported", "simply supported", "simply supported", "simply supported")


def test_runtime_geometry_summary_reads_flat_plate_edge_supports_from_line_properties():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppMixedSupports())

    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    assert summary["plate_edge_supports"] == ("fixed", "simply supported", "simply supported", "fixed")


def test_runtime_geometry_summary_imports_flat_stiffener_and_girder_sections():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())

    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    assert summary["stiffener_section"]["label"] == "T400x12+150x20"
    assert summary["stiffener_section"]["area"] == pytest.approx(0.0048 + 0.003)
    assert summary["length_m"] == pytest.approx(7.5)
    assert summary["width_m"] == pytest.approx(3.5)
    assert summary["girder_spacing_m"] == pytest.approx(2.5)
    assert summary["girder_section"]["label"] == "T800x20+200x30"
    assert summary["girder_section"]["area"] == pytest.approx(0.016 + 0.006)


def test_run_runtime_fem_returns_backend_status_and_visualization_payload():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="medium",
        pressure_pa=100_000.0,
        load_scale=1.2,
        include_stiffeners=True,
        include_girders=True,
        num_buckling_modes=4,
    )

    result = fe_runtime_solver.run_runtime_fem(snapshot, options)

    assert result.status == "ok"
    assert result.summary["pressure_pa"] == 120_000.0
    assert result.summary["mesh_fidelity"] == "medium"
    assert result.summary["solver"] == "ANYsolver production FE mesh"
    assert result.summary["mesh_info"]["shells"] > 0
    assert "kernel_warmup_status" in result.summary
    assert result.summary["prestress_summary"]
    assert result.summary["load_resultant"]
    assert result.visualization["type"] == "flat"
    assert result.visualization["stress_pa"]
    import_payload = result.visualization["fea_result_import"]
    assert import_payload["format"] == "anystructure-runtime-fe-results-v1"
    assert len(import_payload["shells"]) == result.summary["mesh_info"]["shells"]
    assert import_payload["stress_components"] == ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")
    assert import_payload["nodal_stress_pa"]
    session = fe_plate_fields.create_runtime_fea_buckling_session(result, run_buckling=False, geometry_type="flat")
    api_summary = api.analyze_runtime_fea_result_buckling(result, run_buckling=False, geometry_type="flat")
    assert session.panel_count > 0
    assert session.panels[0].stress is not None
    assert session.panels[0].stress.sample_count > 0
    assert api_summary["field_count"] == session.field_count
    assert result.stress_percentiles[0][0] == "p95"
    assert result.stress_percentiles[0][1] > 0.0
    assert result.buckling_factors == tuple(sorted(result.buckling_factors))


def test_production_result_carries_buckling_modes_for_imperfections():
    if fe_solver._full_backend is None:
        pytest.skip("production FE backend unavailable")

    snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app("cylinder"))
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="coarse",
        pressure_pa=200_000.0,
        axial_force_n=500_000_000.0,
        include_end_lids=True,
        num_buckling_modes=3,
        imperfection_mode_shapes_json='[{"mode": 1, "factor": 1.0}, {"mode": 3, "factor": 1.0}]',
    )
    geometry = fe_runtime_solver.runtime_geometry_summary(snapshot, options)
    config = fe_runtime_solver._solver_config_from_options(options)
    generated = fe_solver.build_generated_geometry(geometry, config)

    result = fe_solver.run_production_fem(geometry, config, precomputed_generated_geometry=generated)
    assert result.status == "ok"
    # The raw eigenmodes must ride along on the result so "Set to mesh" can
    # perturb the mesh; previously the field stayed empty and the workflow
    # always failed with "failed to extract mode shapes".
    assert result.buckling_modes
    assert [mode.mode_number for mode in result.buckling_modes][:1] == [1]

    perturbed = fe_solver.apply_mode_shape_imperfections(generated, config, geometry)
    base_nodes = {int(n["id"]): tuple(n["coords"]) for n in generated["nodes"]}
    max_offset = max(
        math.dist(tuple(node["coords"]), base_nodes[int(node["id"])])
        for node in perturbed.get("nodes", [])
        if int(node["id"]) in base_nodes
    )
    assert max_offset > 1.0e-9


def test_runtime_run_uses_mode_shape_imperfection_mesh():
    if fe_solver._full_backend is None:
        pytest.skip("production FE backend unavailable")

    snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app("cylinder"))
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="coarse",
        pressure_pa=200_000.0,
        axial_force_n=500_000_000.0,
        include_end_lids=True,
        num_buckling_modes=3,
        imperfection_mode_shapes_json='[{"mode": 3, "factor": 100.0}]',
    )
    geometry = fe_runtime_solver.runtime_geometry_summary(snapshot, options)
    config = fe_runtime_solver._solver_config_from_options(options)
    generated = fe_solver.build_generated_geometry(geometry, config)
    perturbed = fe_solver.apply_mode_shape_imperfections(generated, config, geometry)

    pristine = fe_runtime_solver.run_runtime_fem(snapshot, options)
    imperfect = fe_runtime_solver.run_runtime_fem(
        snapshot, options, precomputed_generated_geometry=perturbed
    )

    # The perturbed geometry must actually reach the solver: the buckling
    # factors change and the run reports the imperfection mesh usage.
    assert tuple(pristine.buckling_factors) != tuple(imperfect.buckling_factors)
    assert any("imperfection mesh" in item for item in imperfect.diagnostics)
    assert not any("imperfection mesh" in item for item in pristine.diagnostics)
    # Linear eigenvalue analysis of an imperfect geometry cannot show the
    # imperfection knockdown; the run must carry the caveat.
    assert any("does not include the imperfection knockdown" in item for item in imperfect.diagnostics)
    assert not any("imperfection knockdown" in item for item in pristine.diagnostics)

    # The popup run worker hands the stored mesh over unconditionally; the
    # standard-imperfection checkbox must not gate the mode-shape mesh.
    source = Path(fe_runtime_solver.__file__).read_text(encoding="utf-8")
    worker_block = source[
        source.index("def worker() -> None:"):
        source.index("self.solver_thread = threading.Thread(target=worker, daemon=True)")
    ]
    assert 'precomputed = getattr(self, "_imperfection_mesh", None)' in worker_block
    assert 'if getattr(options, "imperfection_enabled", False):' not in worker_block


def test_material_nonlinear_display_stresses_respect_material_curve():
    if fe_solver._full_backend is None:
        pytest.skip("production FE backend unavailable")

    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="coarse",
        pressure_pa=3_000_000.0,
        num_buckling_modes=1,
        analysis_type="geom. + material nonlinear static",
        runtime_solver="nonlinear static",
        material_model="DNV-RP-C208 steel",
        nonlinear_max_load_factor=1.0,
        nonlinear_steps=6,
    )
    result = fe_runtime_solver.run_runtime_fem(snapshot, options)
    assert result.status == "ok"
    prestress = result.summary.get("prestress_summary", {}) or {}
    assert float(prestress.get("nonlinear_static_max_plastic_strain", 0.0) or 0.0) > 0.0

    # Reported stresses come from the committed elastoplastic states — shell
    # layers AND beam fiber sections — so every displayed value respects the
    # DNV-RP-C208 hardening curve sigma = K * eps_p**n (K = 740 MPa, n =
    # 0.166 for S355). The panel sits at its plastic limit load, so the
    # Newton path is branch-sensitive: most runs commit eps_p ~ 6 %
    # (~460 MPa) but a locally collapsed fiber near eps_p ~ 50 % (~665 MPa)
    # is an equally curve-consistent equilibrium. The protective bound is
    # the curve cap at 100 % plastic strain: an elastic recovery from total
    # strains — the regression this test guards against — would report
    # E * eps ~ several thousand MPa.
    curve_cap_pa = 740.0e6
    proportionality_limit_pa = 320.0e6
    reported = dict(result.stress_percentiles)
    assert proportionality_limit_pa < reported["max"] < curve_cap_pa
    assert 0.0 < reported["p95"] <= reported["max"]
    assert any("committed elastoplastic states" in item for item in result.diagnostics)
    # All members are covered by plastic states: no fictitious elastic peak.
    assert float(prestress.get("elastic_member_peak_von_mises_pa", 1.0)) == 0.0

    # The shell colour fields must not be contaminated by elastic beam values
    # averaged into shared nodes.
    skin_values = [
        float((surface.get("field_values") or {}).get("von_mises_pa", 0.0))
        for surface in (result.visualization.get("skin_shell_surfaces") or ())
    ]
    assert skin_values
    assert max(skin_values) < curve_cap_pa

    # Beam member display stresses come from the return-mapped fiber states
    # and are limited by the material curve as well.
    beam_values = [
        float(line.get("von_mises", 0.0))
        for line in (result.visualization.get("member_lines") or ())
    ]
    assert beam_values
    assert max(beam_values) < curve_cap_pa


def test_fiber_section_grid_is_profile_shaped_for_t_sections():
    if fe_solver._full_backend is None:
        pytest.skip("production FE backend unavailable")

    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="coarse",
        material_model="DNV-RP-C208 steel",
        analysis_type="geom. + material nonlinear static",
    )
    geometry = fe_runtime_solver.runtime_geometry_summary(snapshot, options)
    config = fe_runtime_solver._solver_config_from_options(options)
    generated = fe_solver.build_generated_geometry(geometry, config)

    backend = fe_solver.full_backend_api()
    model = backend.build_fe_model_from_generated_geometry(
        generated,
        backend.AnyStructureFEMConfig(pressure_pa=0.0, num_buckling_modes=1),
    )
    curve, props = fe_solver._nonlinear_curve_payload(config, geometry)
    fe_solver._apply_material_curve_to_model(model, curve, props)

    beam = next(
        element
        for element in model.mesh.elements.values()
        if element.__class__.__name__ == "BeamElement"
    )
    # The physical profile dimensions survive the generated-geometry handoff
    # into the backend element cross-section.
    for key in ("web_height", "web_thickness", "flange_width", "flange_thickness"):
        assert float(beam.cross_section.get(key) or 0.0) > 0.0

    material = model.get_material(beam.material_name)
    fiber_config = beam._fiber_plasticity_config(material)
    assert fiber_config is not None
    y, z, w = beam._fiber_section_grid(fiber_config)

    # The shaped layout reproduces the section constants exactly and is
    # centred on the centroid.
    assert float(np.sum(w)) == pytest.approx(beam._A)
    assert float(np.sum(w * z * z)) == pytest.approx(beam._Iy)
    assert float(np.sum(w * y * y)) == pytest.approx(beam._Iz)
    assert float(np.sum(w * z)) / float(np.sum(w)) == pytest.approx(0.0, abs=1.0e-9)
    assert float(np.sum(w * y)) / float(np.sum(w)) == pytest.approx(0.0, abs=1.0e-9)

    # A T-profile concentrates the flange on one side of the centroid: the
    # fiber layout must be skewed toward the flange, unlike the legacy
    # moment-matched rectangle grid whose third moment is exactly zero.
    radius = math.sqrt(beam._Iy / beam._A)
    skewness = float(np.sum(w * z**3)) / (beam._A * radius**3)
    assert abs(skewness) > 0.2
    extent_high = float(np.max(z))
    extent_low = float(-np.min(z))
    assert abs(extent_high - extent_low) / max(extent_high, extent_low) > 0.15


def test_member_shell_material_nonlinear_display_respects_material_curve():
    if fe_solver._full_backend is None:
        pytest.skip("production FE backend unavailable")

    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="coarse",
        member_model="webs as shells, flanges as beams",
        pressure_pa=3_000_000.0,
        num_buckling_modes=1,
        analysis_type="geom. + material nonlinear static",
        runtime_solver="nonlinear static",
        material_model="DNV-RP-C208 steel",
        nonlinear_max_load_factor=1.0,
        nonlinear_steps=6,
    )
    result = fe_runtime_solver.run_runtime_fem(snapshot, options)
    assert result.status == "ok"
    prestress = result.summary.get("prestress_summary", {}) or {}
    assert float(prestress.get("nonlinear_static_max_plastic_strain", 0.0) or 0.0) > 0.0

    # See test_material_nonlinear_display_stresses_respect_material_curve:
    # the bound is the DNV-RP-C208 curve cap at 100 % plastic strain, which
    # stays branch-stable at the plastic limit load while still catching an
    # elastic recovery (E * eps ~ thousands of MPa).
    curve_cap_pa = 740.0e6
    reported = dict(result.stress_percentiles)
    assert 0.0 < reported["max"] < curve_cap_pa
    assert any("committed elastoplastic states" in item for item in result.diagnostics)
    assert float(prestress.get("elastic_member_peak_von_mises_pa", 1.0)) == 0.0

    # Member webs are shells in this model: their displayed stresses come
    # from the committed layer states and respect the material curve.
    web_values = [
        float((surface.get("field_values") or {}).get("von_mises_pa", 0.0))
        for surface in (result.visualization.get("shell_surfaces") or ())
        if str(surface.get("role", "skin") or "skin").lower() not in {"", "skin"}
    ]
    assert web_values
    assert 0.0 < max(web_values) < curve_cap_pa

    # The flange beams recover their display stresses from the return-mapped
    # fiber states.
    beam_values = [
        float(line.get("von_mises", 0.0))
        for line in (result.visualization.get("member_lines") or ())
    ]
    assert beam_values
    assert max(beam_values) < curve_cap_pa


def test_runtime_fem_state_save_load_round_trip(tmp_path):
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="medium",
        pressure_pa=100_000.0,
        load_scale=1.2,
        num_buckling_modes=4,
        include_end_lids=False,
        boundary_constraint_json='{"all": {"uz": 0.0}}',
    )
    result = fe_runtime_solver.run_runtime_fem(snapshot, options)
    assert result.status == "ok"
    original_session = fe_plate_fields.create_runtime_fea_buckling_session(
        result, run_buckling=False, geometry_type="flat"
    )

    for name in ("state.fem.json", "state.fem.json.gz"):
        path = tmp_path / name
        fe_runtime_solver.save_runtime_fem_state(path, options, result=result, snapshot=snapshot)
        state = fe_runtime_solver.load_runtime_fem_state(path)

        assert state["options"] == options
        assert state["snapshot"]["line_name"] == snapshot.line_name

        loaded = state["result"]
        assert loaded is not None
        assert loaded.status == "ok"
        assert loaded.buckling_factors == pytest.approx(result.buckling_factors)
        assert loaded.stress_percentiles[0][0] == "p95"
        assert loaded.summary["mesh_info"]["shells"] == result.summary["mesh_info"]["shells"]

        # The mesh and stresses survive the file round trip: the FEA-result
        # buckling handoff must rebuild the same panels from the loaded state.
        session = fe_plate_fields.create_runtime_fea_buckling_session(
            loaded, run_buckling=False, geometry_type="flat"
        )
        assert session.panel_count == original_session.panel_count
        assert len(session.model.shell_elements) == len(original_session.model.shell_elements)
        assert session.panels[0].stress is not None
        assert session.panels[0].stress.sample_count == original_session.panels[0].stress.sample_count
        assert session.panels[0].stress.sigma_x1_mpa == pytest.approx(
            original_session.panels[0].stress.sigma_x1_mpa, abs=1.0e-9
        )


def test_runtime_fem_options_from_dict_coerces_and_ignores_unknown():
    options = fe_runtime_solver.runtime_fem_options_from_dict(
        {
            "pressure_pa": "2500",
            "num_buckling_modes": 7.0,
            "include_end_lids": 0,
            "mesh_fidelity": "fine",
            "not_a_real_option": 123,
        }
    )

    assert options.pressure_pa == pytest.approx(2500.0)
    assert options.num_buckling_modes == 7
    assert options.include_end_lids is False
    assert options.mesh_fidelity == "fine"
    assert options.load_scale == pytest.approx(1.0)


def test_load_runtime_fem_state_rejects_foreign_json(tmp_path):
    path = tmp_path / "other.fem.json"
    path.write_text(json.dumps({"format": "something-else"}), encoding="utf-8")

    with pytest.raises(ValueError):
        fe_runtime_solver.load_runtime_fem_state(path)


def test_runtime_fem_popup_wires_save_load_buttons():
    source = Path(fe_runtime_solver.__file__).read_text(encoding="utf-8")

    assert 'text="Save FEM..."' in source
    assert "command=self._save_fem_state" in source
    assert 'text="Load FEM..."' in source
    assert "command=self._load_fem_state" in source
    assert "def _apply_options_to_controls(self, options: RuntimeFEMOptions) -> None:" in source
    assert "def _adopt_loaded_result(self, result: RuntimeFEMRunResult" in source
    # Loading a result must reuse the normal post-run ingestion steps.
    adopt_block = source[
        source.index("def _adopt_loaded_result"):
        source.index("def _options(self) -> RuntimeFEMOptions:")
    ]
    assert "self._set_display_modes(result)" in adopt_block
    assert "self._refresh_figure()" in adopt_block
    assert "self._update_buckling_handoff_button(is_running=False)" in adopt_block


def test_run_runtime_fem_passes_phase_five_options_to_solver(monkeypatch):
    captured = {}

    def fake_run_production(geometry, config, status_callback=None, imported_fem_model=None,
                            precomputed_generated_geometry=None):
        captured["geometry"] = geometry
        captured["config"] = config
        return fe_solver.LightweightFEMResult(
            status="ok",
            stress_max_pa=0.0,
            stress_p95_pa=0.0,
            displacement_max_m=0.0,
            mesh_info={"nodes": 1, "shells": 0, "beams": 0},
            prestress_summary={},
            load_resultant={},
            visualization={},
            solver_name="fake production",
        )

    monkeypatch.setattr(fe_runtime_solver.fe_solver, "full_backend_available", lambda: True)
    monkeypatch.setattr(fe_runtime_solver.fe_solver, "run_production_fem", fake_run_production)

    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())
    result = fe_runtime_solver.run_runtime_fem(
        snapshot,
        fe_runtime_solver.RuntimeFEMOptions(
            nonlinear_static_kinematics="Corotational",
            collision_nonlinear_kinematics="Corotational",
            collision_beam_contact_enabled=True,
            beam_consistent_mass_enabled=True,
            local_refinement_enabled=True,
            local_refinement_patches_json='[{"min_a": 0.1, "max_a": 0.4, "min_b": 0.2, "max_b": 0.5}]',
            local_refinement_fine_size_m=0.03,
            local_refinement_extent_m=0.08,
            local_refinement_growth_factor=1.2,
            point_refinement_enabled=True,
            point_refinement_x_m=0.3,
            point_refinement_y_m=0.4,
            point_refinement_fine_size_m=0.025,
            point_refinement_extent_m=0.12,
            point_refinement_growth_factor=1.25,
            collision_adaptive_extent_m=0.45,
            collision_adaptive_growth_factor=1.3,
        ),
    )

    config = captured["config"]

    assert result.status == "ok"
    assert config.nonlinear_static_kinematics == "corotational"
    assert config.collision_nonlinear_kinematics == "corotational"
    assert config.collision_beam_contact_enabled is True
    assert config.beam_consistent_mass_enabled is True
    assert config.local_refinement_enabled is True
    assert config.local_refinement_fine_size_m == pytest.approx(0.03)
    assert config.local_refinement_extent_m == pytest.approx(0.08)
    assert config.local_refinement_growth_factor == pytest.approx(1.2)
    assert config.point_refinement_enabled is True
    assert config.point_refinement_x_m == pytest.approx(0.3)
    assert config.point_refinement_y_m == pytest.approx(0.4)
    assert config.point_refinement_fine_size_m == pytest.approx(0.025)
    assert config.point_refinement_extent_m == pytest.approx(0.12)
    assert config.point_refinement_growth_factor == pytest.approx(1.25)
    assert config.collision_adaptive_extent_m == pytest.approx(0.45)
    assert config.collision_adaptive_growth_factor == pytest.approx(1.3)
    assert result.summary["nonlinear_static_kinematics"] == "corotational"
    assert result.summary["collision_nonlinear_kinematics"] == "corotational"
    assert result.summary["collision_beam_contact_enabled"] is True
    assert result.summary["beam_consistent_mass_enabled"] is True
    assert result.summary["local_refinement_enabled"] is True
    assert result.summary["local_refinement_patch_count"] == 1
    assert result.summary["point_refinement_enabled"] is True
    assert result.summary["collision_adaptive_extent_m"] == pytest.approx(0.45)
    assert result.summary["collision_adaptive_growth_factor"] == pytest.approx(1.3)


def test_fe_solver_kernel_warmup_manager_reports_runtime_state(monkeypatch):
    with fe_runtime_solver._FE_KERNEL_WARMUP_LOCK:
        fe_runtime_solver._FE_KERNEL_WARMUP_STATE.clear()
        fe_runtime_solver._FE_KERNEL_WARMUP_STATE.update(
            {"status": "not_started", "shell_orders": (), "total_seconds": 0.0, "message": ""}
        )

    def fake_warmup(shell_orders, *, include_nonlinear_impact=False):
        return {
            "status": "completed",
            "total_seconds": 0.25,
            "jit": {"enabled": True, "num_threads": 4},
            "shell_orders": {
                str(order): {"matrix_difference_norm": 0.0}
                for order in shell_orders
            },
        }

    monkeypatch.setattr(fe_runtime_solver.fe_solver, "warm_fe_solver_kernels", fake_warmup)
    try:
        state = fe_runtime_solver.start_fe_solver_kernel_warmup(("S4", "Q8"), background=False)
        assert state["status"] == "completed"
        assert state["shell_orders"] == ("S4", "Q8")
        assert state["jit_enabled"] is True
        assert state["parallel_threads"] == 4
        assert state["max_matrix_difference_norm"] == pytest.approx(0.0)
        assert "completed" in fe_runtime_solver._warmup_diagnostics()[0]
    finally:
        with fe_runtime_solver._FE_KERNEL_WARMUP_LOCK:
            fe_runtime_solver._FE_KERNEL_WARMUP_STATE.clear()
            fe_runtime_solver._FE_KERNEL_WARMUP_STATE.update(
                {"status": "not_started", "shell_orders": (), "total_seconds": 0.0, "message": ""}
            )


def test_runtime_result_print_includes_kernel_warmup_summary():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={
            "line": "line",
            "geometry": "flat",
            "kernel_warmup_status": "completed",
            "kernel_warmup_shell_orders": ("S4", "Q8R"),
            "kernel_warmup_total_seconds": 0.25,
            "kernel_warmup_jit_enabled": True,
            "kernel_warmup_parallel_threads": 4,
            "kernel_warmup_max_matrix_difference_norm": 0.0,
            "mesh_info": {},
            "prestress_summary": {},
            "load_resultant": {},
        },
    )

    text = fe_runtime_solver.format_runtime_fem_result(result)

    assert "FE solver kernel warmup:" in text
    assert " - status: completed" in text
    assert " - shell orders: S4, Q8R" in text
    assert " - threads: 4" in text


def test_run_runtime_fem_flat_member_geometry_matches_generated_fe_model():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    generated = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", include_stiffeners=True, include_girders=True),
    )
    result = fe_runtime_solver.run_runtime_fem(
        snapshot,
        fe_runtime_solver.RuntimeFEMOptions(
            mesh_fidelity="coarse",
            pressure_pa=10_000.0,
            include_stiffeners=True,
            include_girders=True,
            num_buckling_modes=1,
        ),
    )

    stiffener = next(beam for beam in generated["beams"] if beam["role"] == "stiffener")
    girder = next(beam for beam in generated["beams"] if beam["role"] == "girder")
    roles = {line["role"] for line in result.visualization["member_lines"]}

    assert stiffener["section"]["label"] == "T400x12+150x20"
    assert stiffener["section"]["area"] == pytest.approx(0.0078)
    assert girder["section"]["label"] == "T800x20+200x30"
    assert girder["section"]["area"] == pytest.approx(0.022)
    assert result.summary["mesh_info"]["beams"] == len(generated["beams"])
    assert {"stiffener", "girder"} <= roles


def _stiffener_web_z_levels(generated):
    node_z = {int(node["id"]): float(node["coords"][2]) for node in generated["nodes"]}
    levels = {
        round(node_z[int(node_id)], 6)
        for shell in generated["shells"]
        if str(shell.get("role", "")) == "stiffener_web"
        for node_id in shell.get("node_ids", ())
    }
    return sorted(levels)


def test_web_shell_depth_follows_mesh_fidelity_with_flange_beams():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    def generated_for(fidelity, mesh_size=0.0):
        return fe_solver.build_generated_geometry(
            summary,
            fe_solver.LightweightFEMConfig(
                mesh_fidelity=fidelity,
                include_stiffeners=True,
                include_girders=True,
                member_model="webs as shells, flanges as beams",
                mesh_size_m=mesh_size,
            ),
        )

    # 0.4 m stiffener web: coarse keeps one row, medium two, fine three.
    assert len(_stiffener_web_z_levels(generated_for("coarse"))) == 2
    assert len(_stiffener_web_z_levels(generated_for("medium"))) == 3
    assert len(_stiffener_web_z_levels(generated_for("fine"))) == 4
    # An explicit mesh-size override refines the web depth further.
    assert len(_stiffener_web_z_levels(generated_for("coarse", mesh_size=0.1))) == 5


def test_flat_stiffened_panel_without_girder_uses_girder_length_by_default():
    class _NoGirderStructure(_AllStructureWithFlatMembers):
        Girder = None

    class _NoGirderApp(_FakeApp):
        _line_to_struc = {"line1": [_NoGirderStructure(), None, None, object(), None, None]}

    snapshot = fe_runtime_solver.active_line_snapshot(_NoGirderApp())

    default_geometry = fe_runtime_solver.runtime_geometry_summary(
        snapshot, fe_runtime_solver.RuntimeFEMOptions()
    )
    single_bay = fe_runtime_solver.runtime_geometry_summary(
        snapshot, fe_runtime_solver.RuntimeFEMOptions(ignore_girder_length=True)
    )

    # Plate.girder_lg = 3.5 in the fake app: the FE model follows the main
    # application 3D model and spans the girder length with several
    # stiffeners unless the user opts out.
    assert default_geometry["width_m"] == pytest.approx(3.5)
    assert single_bay["width_m"] == pytest.approx(0.75)
    assert default_geometry["stiffener_spacing_m"] == pytest.approx(0.75)


def test_flat_end_moment_matches_constant_moment_strip_theory():
    class _NoMembersStructure(_AllStructureWithFlatMembers):
        Stiffener = None
        Girder = None

    class _NoMembersApp(_FakeApp):
        _line_to_struc = {"line1": [_NoMembersStructure(), None, None, object(), None, None]}

        def get_highest_pressure(self, line):
            return {"normal": 0.0}

    moment = -10_000.0
    snapshot = fe_runtime_solver.active_line_snapshot(_NoMembersApp())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="medium",
        pressure_pa=0.0,
        top_bottom_moment_nm=moment,
        include_stiffeners=False,
        include_girders=False,
    )
    geometry = fe_runtime_solver.runtime_geometry_summary(snapshot, options)
    # Free side edges make the panel a beam-like strip: equal-and-opposite end
    # moments then give a constant bending moment and uniform surface stress
    # sigma = 6*M/(b*t^2) along the whole span.
    geometry["plate_edge_supports"] = ("simply supported", "simply supported", "free", "free")
    config = fe_runtime_solver._solver_config_from_options(options)

    result = fe_solver.run_production_fem(geometry, config)
    assert result.status == "ok"

    length = float(geometry["length_m"])
    width = float(geometry["width_m"])
    thickness = float(geometry["thickness_m"])
    expected = 6.0 * abs(moment) / (width * thickness ** 2)

    mid_values = []
    for surface in result.visualization.get("skin_shell_surfaces") or ():
        points = surface.get("points") or ()
        if not points:
            continue
        centroid_x = sum(float(point[0]) for point in points) / len(points)
        if abs(centroid_x - 0.5 * length) <= 0.2 * length:
            mid_values.append(float((surface.get("field_values") or {}).get("von_mises_pa", 0.0)))

    assert mid_values
    mean_mid = sum(mid_values) / len(mid_values)
    assert mean_mid == pytest.approx(expected, rel=0.05)


def test_runtime_imperfection_preview_offsets_follow_solver_shape():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    options = fe_runtime_solver.RuntimeFEMOptions(
        mesh_fidelity="coarse",
        imperfection_enabled=True,
        imperfection_amplitude_m=0.005,
        imperfection_wave_a=1,
        imperfection_wave_b=1,
    )
    geometry = fe_runtime_solver.runtime_geometry_summary(snapshot, options)
    config = fe_runtime_solver._solver_config_from_options(options)
    generated = fe_solver.build_generated_geometry(geometry, config)

    offsets = fe_solver.runtime_imperfection_preview_offsets(generated, config, geometry)

    assert offsets
    magnitudes = [math.sqrt(dx * dx + dy * dy + dz * dz) for dx, dy, dz in offsets.values()]
    # The plate half-wave imperfection peaks at the requested amplitude and
    # acts out of plane only.
    assert max(magnitudes) == pytest.approx(0.005, rel=0.05)
    assert all(abs(dx) <= 1.0e-12 and abs(dy) <= 1.0e-12 for dx, dy, _dz in offsets.values())

    disabled_config = fe_runtime_solver._solver_config_from_options(
        fe_runtime_solver.RuntimeFEMOptions(mesh_fidelity="coarse")
    )
    assert fe_solver.runtime_imperfection_preview_offsets(generated, disabled_config, geometry) == {}


def test_mesh_preview_uses_shared_canvas_refresh_contract():
    source = Path(fe_runtime_solver.__file__).read_text(encoding="utf-8")

    render_block = source[
        source.index("def _render_mesh_preview_canvas"):
        source.index("def _refresh_mesh_preview_current")
    ]
    # Same contract as the result canvas: smooth item-reusing refresh for
    # view-option changes, camera fit only for a new mesh.
    assert "canvas.clear(keep_canvas=not fit_view)" in render_block
    assert "if fit_view:" in render_block
    assert "canvas.fit_to_scene()" in render_block

    offsets_block = source[
        source.index("def _mesh_preview_imperfection_offsets"):
        source.index("def _imperfection_preview_scale_value")
    ]
    # Standard-imperfection preview offsets are cached; redraws must not
    # rebuild the backend FE model.
    assert "_imperfection_offsets_cache" in offsets_block


def test_runtime_fem_mesh_preview_wires_imperfection_controls():
    source = Path(fe_runtime_solver.__file__).read_text(encoding="utf-8")

    assert "self.show_imperfections_vis = tk.BooleanVar(value=False)" in source
    assert "self.imperfection_preview_scale = tk.DoubleVar(value=0.0)" in source
    assert 'text="Show imperfections"' in source
    assert "def _mesh_preview_imperfection_offsets" in source
    assert "fe_solver.runtime_imperfection_preview_offsets" in source

    populate_block = source[
        source.index("def _populate_canvas_with_mesh"):
        source.index("def _draw_mesh_detail_overlays")
    ]
    assert "set_thickness_legend" in populate_block
    assert "_interpolate_thickness_color" in populate_block
    assert "_imperfection_preview_scale_value" in populate_block

    set_block = source[
        source.index("def _set_mode_shapes_to_mesh"):
        source.index("def _render_mesh_preview_canvas")
    ]
    # The popup object is not a tk widget: idle-task flushes must go through
    # self.window, and pressing "Set to mesh" without mode rows must explain
    # what to do instead of failing.
    assert "self.window.update_idletasks()" in set_block
    assert "\n            self.update_idletasks()" not in set_block
    assert "No buckling mode shapes are selected" in set_block


def test_generated_beam_sections_preserve_consistent_mass_in_backend_model():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    disabled = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            include_stiffeners=True,
            include_girders=True,
            beam_consistent_mass_enabled=False,
        ),
    )
    enabled = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            include_stiffeners=True,
            include_girders=True,
            beam_consistent_mass_enabled=True,
        ),
    )
    flange_enabled = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            include_stiffeners=True,
            include_girders=True,
            member_model="webs as shells, flanges as beams",
            beam_consistent_mass_enabled=True,
        ),
    )

    assert disabled["beams"]
    assert enabled["beams"]
    assert flange_enabled["beams"]
    assert all("consistent_mass" not in beam["section"] for beam in disabled["beams"])
    assert all(beam["section"].get("consistent_mass") is True for beam in enabled["beams"])
    assert all(beam["section"].get("consistent_mass") is True for beam in flange_enabled["beams"])

    backend = fe_solver.full_backend_api()
    model = backend.build_fe_model_from_generated_geometry(
        enabled,
        backend.AnyStructureFEMConfig(pressure_pa=0.0, require_idealized_member_beams=False),
    )
    beam_elements = [
        element
        for element in model.mesh.elements.values()
        if element.__class__.__name__ in {"BeamElement", "QuadraticBeamElement"}
    ]

    assert beam_elements
    assert all(element.cross_section.get("consistent_mass") is True for element in beam_elements)


def test_runtime_flat_girder_panel_uses_lg_width_and_span_girder_stations():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    generated = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0, include_stiffeners=True, include_girders=True),
    )
    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}
    x_values = {round(coord[0], 6) for coord in coords.values()}
    y_values = {round(coord[1], 6) for coord in coords.values()}
    girder_x_values = {
        round(coords[node_id][0], 6)
        for beam in generated["beams"]
        if beam["role"] == "girder"
        for node_id in beam["node_ids"]
    }
    stiffener_y_values = {
        round(coords[node_id][1], 6)
        for beam in generated["beams"]
        if beam["role"] == "stiffener"
        for node_id in beam["node_ids"]
    }

    assert max(x_values) == pytest.approx(7.5)
    assert max(y_values) == pytest.approx(3.5)
    # Lp = 7.5 is an exact multiple of the 2.5 m stiffener span, so the
    # girders bound the bays and sit on the panel edges as well.
    assert girder_x_values == {0.0, 2.5, 5.0, 7.5}
    assert stiffener_y_values == {0.25, 1.0, 1.75, 2.5, 3.25}


@pytest.mark.parametrize(
    "member_model",
    (
        "plates as shell, girders as beams",
        "webs as shells, flanges as beams",
    ),
)
def test_runtime_cylinder_beam_members_are_imported_as_buckling_boundaries(member_model):
    snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app("cylinder"))
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)
    generated = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            include_stiffeners=True,
            include_girders=True,
            include_end_lids=True,
            member_model=member_model,
        ),
    )
    node_lookup = {int(node["id"]): tuple(node["coords"]) for node in generated["nodes"]}
    shell_node_ids = {
        int(node_id)
        for shell in generated["shells"]
        for node_id in shell["node_ids"]
    }
    skin_ids = tuple(int(shell["id"]) for shell in generated["shells"] if shell.get("role", "skin") == "skin")
    z_values = [node_lookup[node_id][2] for node_id in shell_node_ids]
    runtime_members = []
    for beam in generated["beams"]:
        role = str(beam.get("role", ""))
        if not any(token in role for token in ("stiffener", "girder", "frame")):
            continue
        node_ids = tuple(int(node_id) for node_id in beam["node_ids"])
        runtime_members.append(
            {
                "id": int(beam["id"]),
                "role": role,
                "node_ids": node_ids,
                "points": tuple(node_lookup[node_id] for node_id in node_ids),
                "section": dict(beam.get("section") or {}),
            }
        )
    payload = {
        "format": "anystructure-runtime-fe-results-v1",
        "source": "runtime FEM result",
        "geometry_type": "cylinder",
        "nodes": tuple({"id": node_id, "coords": node_lookup[node_id]} for node_id in sorted(shell_node_ids)),
        "shells": tuple(
            {
                "id": int(shell["id"]),
                "node_ids": tuple(int(node_id) for node_id in shell["node_ids"]),
                "type": str(shell.get("type", "S4") or "S4"),
                "elset": "runtime_skin_20000um",
                "role": str(shell.get("role", "skin")),
            }
            for shell in generated["shells"]
        ),
        "elsets": {"runtime_skin_20000um": skin_ids},
        "shell_sections": (
            {"elset": "runtime_skin_20000um", "material": "steel", "thickness_m": summary["thickness_m"], "offset": None},
        ),
        "stress_components": ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"),
        "nodal_stress_pa": {},
        "units": "Pa",
        "cylinder_geometry": {
            "axis_origin": (0.0, 0.0, min(z_values)),
            "axis_direction": (0.0, 0.0, 1.0),
            "radius_m": generated["radius_m"],
            "axial_bounds": (min(z_values), max(z_values)),
            "skin_element_ids": skin_ids,
            "skin_thickness_m": summary["thickness_m"],
            "radial_rms_error_m": 0.0,
            "confidence": 1.0,
            "diagnostics": ("runtime cylinder geometry metadata",),
        },
        "runtime_members": tuple(runtime_members),
    }

    session = fe_plate_fields.create_runtime_fea_buckling_session(payload, run_buckling=False)
    first = session.panels[0]

    assert session.panel_count > 1
    assert first.anystructure_input["calculation_domain"] == "Orthogonally Stiffened shell"
    assert {member.role for member in first.field.members} >= {"longitudinal_stiffener", "ring_frame"}
    assert first.anystructure_input["longitudinal_stiffener"]["web_height_mm"] == pytest.approx(150.0)
    assert first.anystructure_input["ring_frame"]["flange_width_mm"] == pytest.approx(150.0)


def test_standalone_girder_panel_centers_cut_bays_for_symmetric_stress_model():
    snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app())
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)

    generated = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0, include_stiffeners=True, include_girders=True),
    )
    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}
    girder_x_values = sorted(
        {
            round(coords[node_id][0], 6)
            for beam in generated["beams"]
            if beam["role"] == "girder"
            for node_id in beam["node_ids"]
        }
    )
    stiffener_y_values = sorted(
        {
            round(coords[node_id][1], 6)
            for beam in generated["beams"]
            if beam["role"] == "stiffener"
            for node_id in beam["node_ids"]
        }
    )

    assert summary["length_m"] == pytest.approx(10.0)
    assert summary["width_m"] == pytest.approx(10.0)
    assert girder_x_values == [1.5, 5.0, 8.5]
    assert stiffener_y_values[0] == pytest.approx(0.125)
    assert stiffener_y_values[-1] == pytest.approx(9.875)
    assert all(
        (left + right) == pytest.approx(10.0)
        for left, right in zip(stiffener_y_values, reversed(stiffener_y_values))
    )


def test_standalone_girder_pressure_static_deflection_is_dominantly_downward_not_nullspace_balanced():
    snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app())
    result = fe_runtime_solver.run_runtime_fem(
        snapshot,
        fe_runtime_solver.RuntimeFEMOptions(
            mesh_fidelity="coarse",
            shell_element_order="S4",
            pressure_pa=snapshot.pressure_pa,
            include_stiffeners=True,
            include_girders=True,
            num_buckling_modes=1,
        ),
    )
    w_values = [value for row in result.visualization.get("w_m", ()) for value in row]
    prestress = result.summary.get("prestress_summary", {})

    assert result.status == "ok"
    assert prestress["constraint_method"] == "transformation_fixed_plus_mpc"
    assert prestress["constraint_mode"] == "transformation"
    assert prestress["nullspace_projection"] == pytest.approx(0.0)
    downward_peak = abs(min(w_values))
    upward_peak = max(w_values)
    assert downward_peak > 1.0e-3
    assert result.summary["max_displacement_m"] == pytest.approx(downward_peak, rel=1.0e-6)
    assert upward_peak <= max(1.0e-3, 5.0e-3 * downward_peak)


def test_runtime_fem_matplotlib_figure_contains_geometry_axis():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())
    result = fe_runtime_solver.run_runtime_fem(
        snapshot,
        fe_runtime_solver.RuntimeFEMOptions(
            mesh_fidelity="coarse",
            pressure_pa=100_000.0,
            load_scale=1.0,
            include_stiffeners=True,
            include_girders=True,
            num_buckling_modes=3,
        ),
    )

    figure = fe_runtime_solver.create_runtime_fem_result_figure(snapshot, result)

    assert isinstance(figure, Figure)
    assert len(figure.axes) >= 1
    assert figure.axes[0].get_title() == "Static stress/displacement"
    assert figure.axes[0].lines


def test_missing_shell_strain_component_does_not_reuse_von_mises_values():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={},
        visualization={
            "type": "flat",
            "stress_pa": ((480.0e6, 500.0e6),),
            "fields": {},
        },
    )

    visualization, _title, _is_mode = fe_runtime_solver._selected_visualization(
        result,
        "static",
        "strain_xy_membrane",
    )

    assert visualization["scalar_kind"] == "raw"
    assert visualization["stress_pa"][0][0] == pytest.approx(0.0)
    assert fe_runtime_solver._shell_surface_component_value(
        {"field_values": {"von_mises_pa": 480.0e6}},
        "strain_xy_membrane",
        is_mode=False,
    ) == pytest.approx(0.0)


def test_stress_colorbar_label_converts_pa_to_mpa_without_duplicate_units():
    grid, label = fe_runtime_solver._visualization_color_grid_and_label(
        {"stress_pa": ((2.0e6,),), "scalar_label": "stress [Pa]"},
        "von_mises_pa",
        is_mode=False,
    )

    assert grid == [[2.0]]
    assert label == "stress [MPa]"


def test_display_modes_keep_equivalent_plastic_strain_for_dnv_material():
    class Var:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    class DummyWindow:
        result_case_choice = Var("Static displacement/stress")
        component_choice = Var("Stress von Mises")
        result_case_selector = None
        component_selector = None

    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={"material_model": "DNV-RP-C208 steel"},
        visualization={},
    )

    window = DummyWindow()

    fe_runtime_solver.RuntimeFEMWindow._set_display_modes(window, result)

    assert window.component_labels["Equivalent Plastic Strain"] == "plastic_strain"


def test_runtime_fem_result_print_explains_unavailable_nonlinear_factor():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={
            "line": "line1",
            "geometry": "cylinder",
            "mesh_fidelity": "coarse",
            "shell_element_order": "S8",
            "boundary_condition": "auto",
            "symmetry_mode": "none",
            "analysis_type": "nonlinear stability",
            "buckling_analysis_type": "nonlinear limit",
            "solver_type": "direct",
            "pressure_pa": 1000.0,
            "pressure_side": "front",
            "pressure_direction": "front",
            "axial_force_n": 0.0,
            "enforced_displacement_m": 0.0,
            "mesh_size_m": 0.0,
            "top_bottom_moment_nm": 0.0,
            "include_stiffeners": True,
            "include_girders": True,
            "include_end_lids": True,
            "member_orientation": "auto",
            "stiffener_eccentricity_m": 0.0,
            "girder_eccentricity_m": 0.0,
            "elastic_modulus_pa": 210.0e9,
            "poisson_ratio": 0.3,
            "yield_stress_pa": 355.0e6,
            "stress_percentile": 95.0,
            "num_buckling_modes": 5,
            "max_displacement_m": 0.0,
            "prestress_summary": {
                "shell_elements": 800,
                "nonlinear_status": "initial_tangent_not_positive",
                "nonlinear_limit_factor": 0.0,
                "nonlinear_steps": 0,
            },
        },
        stress_percentiles=(),
        buckling_factors=(),
        diagnostics=(),
        visualization={},
    )

    text = fe_runtime_solver.format_runtime_fem_result(result)

    assert "Nonlinear tangent-stability check:" in text
    assert "estimated nonlinear load factor: not available" in text
    assert "initial tangent stiffness was not positive" in text
    assert " - nonlinear_limit_factor: 0.0" not in text


def test_runtime_fem_result_print_explains_nullspace_projection():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={
            "line": "line1",
            "geometry": "cylinder",
            "mesh_fidelity": "coarse",
            "shell_element_order": "S4",
            "boundary_condition": "auto",
            "symmetry_mode": "none",
            "analysis_type": "linear eigenvalue",
            "buckling_analysis_type": "linear eigenvalue",
            "solver_type": "direct",
            "pressure_pa": 1000.0,
            "pressure_side": "front",
            "pressure_direction": "front",
            "axial_force_n": 0.0,
            "enforced_displacement_m": 0.0,
            "mesh_size_m": 0.0,
            "top_bottom_moment_nm": 0.0,
            "include_stiffeners": True,
            "include_girders": True,
            "include_end_lids": True,
            "member_orientation": "auto",
            "stiffener_eccentricity_m": 0.0,
            "girder_eccentricity_m": 0.0,
            "elastic_modulus_pa": 210.0e9,
            "poisson_ratio": 0.3,
            "yield_stress_pa": 355.0e6,
            "stress_percentile": 95.0,
            "custom_load_bc_enabled": True,
            "cylinder_lower_support": "free",
            "cylinder_upper_support": "free",
            "cylinder_lower_edge_load_n_per_m": 0.0,
            "cylinder_upper_edge_load_n_per_m": 0.0,
            "num_buckling_modes": 5,
            "max_displacement_m": 0.0,
            "prestress_summary": {
                "shell_elements": 800,
                "constraint_method": "transformation_fixed_plus_mpc_nullspace",
                "nullspace_projection": 1.0,
            },
        },
        stress_percentiles=(),
        buckling_factors=(),
        diagnostics=(),
        visualization={},
    )

    text = fe_runtime_solver.format_runtime_fem_result(result)

    assert "Custom load/BC mode: True" in text
    assert "Linear constraint handling:" in text
    assert "nullspace projection: used" in text
    assert "rigid-body modes were projected out" in text


def test_dnv_c208_steel_properties_use_grade_and_thickness_class():
    props = fe_solver.dnv_c208_steel_properties("S355", thickness_m=0.018, thickness_class="auto")

    assert props["grade"] == "S355"
    assert props["thickness_class"] == "16 < t <= 40"
    assert props["sigma_prop"] == pytest.approx(311.0e6)
    assert props["sigma_yield"] == pytest.approx(346.9e6)
    assert props["sigma_yield_2"] == pytest.approx(353.1e6)
    assert props["eps_p_y1"] == pytest.approx(0.004)
    assert props["eps_p_y2"] == pytest.approx(0.015)
    assert props["K"] == pytest.approx(740.0e6)
    assert props["n"] == pytest.approx(0.166)


def test_nonlinear_shell_display_stresses_use_committed_plastic_state():
    class ShellElement:
        material_name = "steel"
        gauss_points = ((0.0, 0.0),)

    class Mesh:
        def __init__(self):
            self._element = ShellElement()

        def get_element(self, element_id):
            return self._element if element_id == 1 else None

    class Material:
        elastic_modulus = 210.0e9
        poisson_ratio = 0.3

    class Model:
        mesh = Mesh()

        def get_material(self, _name):
            return Material()

    states = {
        1: {
            "layer_strain": np.asarray([[0.003, 0.0, 0.0004]], dtype=float),
            "plastic_strain": np.asarray([[0.002, 0.0, 0.0001]], dtype=float),
            "alpha": np.asarray([0.002], dtype=float),
        }
    }

    stresses = fe_solver._nonlinear_shell_stresses_from_states(Model(), states)

    elastic_overstress = 210.0e9 / (1.0 - 0.3**2) * 0.003
    assert stresses[1]["membrane_strain_xx"][0] == pytest.approx(0.003)
    assert stresses[1]["membrane_strain_xy"][0] == pytest.approx(0.0004)
    assert stresses[1]["membrane_xx"][0] < elastic_overstress
    assert stresses[1]["von_mises"][0] > 0.0


def test_production_solver_runs_incremental_material_nonlinear_static_path():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 0.6,
            "width_m": 0.3,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=1000.0,
            mesh_fidelity="coarse",
            num_buckling_modes=1,
            analysis_type="geom. + material nonlinear static",
            material_model="DNV-RP-C208 steel",
            steel_grade="S355",
            nonlinear_max_load_factor=1.0,
            nonlinear_steps=2,
            nonlinear_layers=4,
        ),
    )

    prestress = result.prestress_summary

    assert result.status == "ok"
    assert prestress["material_model"] == "DNV-RP-C208"
    assert prestress["steel_grade"] == "S355"
    assert prestress["nonlinear_static_status"] == "completed"
    assert prestress["nonlinear_static_load_factor"] == pytest.approx(1.0)
    assert prestress["nonlinear_static_layers"] in {3.0, 5.0}
    assert result.visualization["plastic_strain"]
    assert result.visualization["plastic_strain_label"] == "equiv. engineering plastic strain [-]"
    assert "Ran incremental geometric/material nonlinear static solve: completed." in result.diagnostics


def test_collision_nonlinear_config_normalizes_corotational_kinematics():
    config = fe_solver.LightweightFEMConfig(
        collision_material_nonlinear_enabled=True,
        collision_nonlinear_kinematics="Corotational",
    )

    nonlinear_config = fe_solver._collision_nonlinear_config(config)

    assert nonlinear_config is not None
    assert nonlinear_config.kinematics == "corotational"


def test_direct_nonlinear_static_records_corotational_kinematics():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 0.6,
            "width_m": 0.3,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=250.0,
            mesh_fidelity="coarse",
            num_buckling_modes=1,
            analysis_type="geometric nonlinear static",
            nonlinear_static_kinematics="corotational",
            nonlinear_max_load_factor=0.25,
            nonlinear_steps=1,
            nonlinear_max_iterations=20,
        ),
    )

    assert result.status == "ok"
    assert result.prestress_summary["nonlinear_static_kinematics"] == "corotational"


def test_corotational_static_with_fracture_is_rejected_before_backend_execution():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 0.6,
            "width_m": 0.3,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=250.0,
            mesh_fidelity="coarse",
            num_buckling_modes=1,
            analysis_type="geometric nonlinear static",
            nonlinear_static_kinematics="corotational",
            fracture_enabled=True,
        ),
    )

    assert result.status == "invalid_static_kinematics"
    assert result.prestress_summary["nonlinear_static_kinematics"] == "corotational"
    assert any("Corotational nonlinear static does not support fracture/erosion" in item for item in result.diagnostics)


def test_flat_automatic_nullspace_keeps_physical_edge_pressure_supports():
    geometry = {
        "geometry": "flat panel",
        "length_m": 1.0,
        "width_m": 1.0,
        "thickness_m": 0.01,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(boundary_condition="nullspace", pressure_pa=1000.0, mesh_fidelity="coarse")

    generated = fe_solver.build_generated_geometry(geometry, config)
    result = fe_solver.run_production_fem(geometry, config)

    assert {support["name"] for support in generated["supports"]} >= {
        "plate_x0_simply_supported",
        "plate_x1_simply_supported",
        "plate_y0_simply_supported",
        "plate_y1_simply_supported",
    }
    assert all({"uz": 0.0}.items() <= support["constraints"].items() for support in generated["supports"] if support["name"].startswith("plate_"))
    assert result.status == "ok"
    assert result.prestress_summary["constraint_mode"] == "nullspace"
    assert result.prestress_summary["nullspace_projection"] == pytest.approx(1.0)
    assert (
        "Auto-set: no edge DOF is constrained, so automatic well-posed edge supports were applied "
        "(from line properties, defaulting to simply supported edges when unspecified)."
    ) in result.diagnostics


def test_flat_automatic_supports_use_imported_line_property_pattern():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "flat panel",
            "length_m": 2.0,
            "width_m": 1.0,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
            "plate_edge_supports": ("fixed", "simply supported", "simply supported", "fixed"),
        },
        fe_solver.LightweightFEMConfig(boundary_condition="auto", mesh_fidelity="coarse"),
    )

    supports = {support["name"]: support["constraints"] for support in generated["supports"]}

    assert supports["plate_x0_fixed"] == {"ux": 0.0, "uy": 0.0, "uz": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0}
    assert supports["plate_x1_simply_supported"] == {"uz": 0.0}
    assert supports["plate_y0_simply_supported"] == {"uz": 0.0}
    assert supports["plate_y1_fixed"] == {"ux": 0.0, "uy": 0.0, "uz": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0}


def test_custom_manual_pressure_replaces_imported_flat_pressure():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 2.0,
            "width_m": 1.0,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=1000.0,
            custom_load_bc_enabled=True,
            custom_pressure_pa=500.0,
            plate_edge_x0_support="simply supported",
            plate_edge_x1_support="simply supported",
            plate_edge_y0_support="simply supported",
            plate_edge_y1_support="simply supported",
        ),
    )

    assert result.status == "ok"
    assert result.load_resultant["force_n"][2] == pytest.approx(-1000.0)
    assert "Custom loads replace imported/generated pressure, axial force and end moment inputs." in result.diagnostics
    assert "Applied custom manual pressure: 500.0 Pa." in result.diagnostics


def test_imported_flat_force_and_moment_are_balanced_on_opposite_edges():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 2.0,
            "width_m": 1.0,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(pressure_pa=0.0, axial_force_n=1000.0, top_bottom_moment_nm=200.0, mesh_fidelity="coarse"),
    )

    assert result.status == "ok"
    assert result.load_resultant["force_n"] == pytest.approx((0.0, 0.0, 0.0))
    assert result.load_resultant["moment_nm"] == pytest.approx((0.0, 0.0, 0.0))


def test_runtime_fem_plots_engineering_plastic_strain_and_uses_deformation_scale():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())
    result = fe_runtime_solver.run_runtime_fem(
        snapshot,
        fe_runtime_solver.RuntimeFEMOptions(
            pressure_pa=1000.0,
            mesh_fidelity="coarse",
            num_buckling_modes=1,
            analysis_type="geom. + material nonlinear static",
            material_model="DNV-RP-C208 steel",
            nonlinear_max_load_factor=1.0,
            nonlinear_steps=2,
            nonlinear_layers=3,
            deformation_scale=12.0,
        ),
    )

    figure = fe_runtime_solver.create_runtime_fem_result_figure(snapshot, result, "plastic", deformation_scale=12.0)

    assert result.visualization["plastic_strain"]
    assert figure.axes[0].get_title() == "Engineering plastic strain"
    assert any(getattr(axis, "get_ylabel", lambda: "")() == "equiv. engineering plastic strain [-]" for axis in figure.axes)


def test_runtime_result_print_includes_dnv_curve_and_nonlinear_static_summary():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={
            "line": "line1",
            "geometry": "flat panel",
            "mesh_fidelity": "coarse",
            "shell_element_order": "S4",
            "boundary_condition": "auto",
            "symmetry_mode": "none",
            "analysis_type": "geom. + material nonlinear static",
            "buckling_analysis_type": "linear eigenvalue",
            "solver_type": "direct",
            "pressure_pa": 1000.0,
            "pressure_side": "front",
            "pressure_direction": "front",
            "axial_force_n": 0.0,
            "enforced_displacement_m": 0.0,
            "mesh_size_m": 0.0,
            "top_bottom_moment_nm": 0.0,
            "include_stiffeners": False,
            "include_girders": False,
            "include_end_lids": False,
            "member_orientation": "auto",
            "stiffener_eccentricity_m": 0.0,
            "girder_eccentricity_m": 0.0,
            "material_model": "DNV-RP-C208 steel",
            "steel_grade": "S355",
            "steel_thickness_class": "auto",
            "elastic_modulus_pa": 210.0e9,
            "poisson_ratio": 0.3,
            "yield_stress_pa": 355.0e6,
            "stress_percentile": 95.0,
            "nonlinear_max_load_factor": 1.0,
            "nonlinear_steps": 2,
            "nonlinear_max_iterations": 25,
            "nonlinear_layers": 5,
            "custom_load_bc_enabled": False,
            "num_buckling_modes": 1,
            "max_displacement_m": 0.0,
            "prestress_summary": {
                "material_model": "DNV-RP-C208",
                "steel_grade": "S355",
                "steel_thickness_class": "t <= 16",
                "sigma_prop_pa": 320.0e6,
                "sigma_yield_pa": 357.0e6,
                "sigma_yield_2_pa": 363.3e6,
                "eps_p_y1": 0.004,
                "eps_p_y2": 0.015,
                "hardening_K_pa": 740.0e6,
                "hardening_n": 0.166,
                "nonlinear_static_status": "completed",
                "nonlinear_static_load_factor": 1.0,
                "nonlinear_static_steps": 2,
                "nonlinear_static_total_iterations": 6,
                "nonlinear_static_layers": 5,
                "nonlinear_static_max_plastic_strain": 0.0,
            },
        },
        stress_percentiles=(),
        buckling_factors=(),
        diagnostics=(),
        visualization={},
    )

    text = fe_runtime_solver.format_runtime_fem_result(result)

    assert "Material model: DNV-RP-C208 steel" in text
    assert "DNV-RP-C208 material curve:" in text
    assert "sigma_prop/yield/yield2 [MPa]: 320.0 / 357.0 / 363.3" in text
    assert "Incremental nonlinear static solve:" in text
    assert "last converged load factor: 1.0" in text


def test_runtime_result_print_includes_phase_five_controls_and_collision_energy():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={
            "line": "line1",
            "geometry": "flat panel",
            "mesh_fidelity": "coarse",
            "shell_element_order": "S8",
            "beam_element_order": "B3",
            "member_model": "plates as shell, girders as beams",
            "boundary_condition": "auto",
            "symmetry_mode": "none",
            "analysis_type": "geom. + material nonlinear static",
            "buckling_analysis_type": "linear eigenvalue",
            "runtime_solver": "stepwise",
            "solver_type": "direct",
            "pressure_pa": 1000.0,
            "pressure_side": "front",
            "pressure_direction": "front",
            "axial_force_n": 0.0,
            "enforced_displacement_m": 0.0,
            "mesh_size_m": 0.0,
            "top_bottom_moment_nm": 0.0,
            "include_stiffeners": True,
            "include_girders": True,
            "include_end_lids": False,
            "member_orientation": "auto",
            "stiffener_eccentricity_m": 0.0,
            "girder_eccentricity_m": 0.0,
            "material_model": "DNV-RP-C208 steel",
            "steel_grade": "S355",
            "steel_thickness_class": "auto",
            "elastic_modulus_pa": 210.0e9,
            "poisson_ratio": 0.3,
            "yield_stress_pa": 355.0e6,
            "stress_percentile": 95.0,
            "nonlinear_max_load_factor": 1.0,
            "nonlinear_steps": 2,
            "nonlinear_max_iterations": 10,
            "nonlinear_layers": 5,
            "nonlinear_solution_control": "newton force control",
            "nonlinear_static_kinematics": "corotational",
            "nonlinear_convergence_profile": "auto",
            "nonlinear_assembly_threads": 0,
            "beam_consistent_mass_enabled": True,
            "deformation_scale": 0.0,
            "recovery_history_mode": "full",
            "memory_limit_mb": 0.0,
            "custom_load_bc_enabled": False,
            "num_buckling_modes": 1,
            "max_displacement_m": 0.0,
            "collision_enabled": True,
            "collision_mass_kg": 10.0,
            "collision_radius_m": 0.1,
            "collision_start_m": (0.0, 0.0, 1.0),
            "collision_vector": (0.0, 0.0, -1.0),
            "collision_speed_mps": 3.0,
            "collision_time_mode": "auto",
            "collision_total_time_s": 0.01,
            "collision_dt_s": 0.001,
            "collision_auto_steps_per_radius": 20.0,
            "collision_auto_post_contact_radii": 6.0,
            "collision_bounce_back_time_s": 0.001,
            "collision_contact_surface": "midsurface",
            "collision_beam_contact_enabled": True,
            "collision_material_nonlinear_enabled": True,
            "collision_nonlinear_kinematics": "corotational",
            "collision_damage_enabled": True,
            "mesh_info": {},
            "prestress_summary": {
                "nonlinear_static_status": "completed",
                "nonlinear_static_control": "newton force control",
                "nonlinear_static_kinematics": "corotational",
                "nonlinear_static_load_factor": 1.0,
                "nonlinear_static_steps": 2,
                "nonlinear_static_total_iterations": 6,
                "nonlinear_static_layers": 5,
                "nonlinear_static_max_plastic_strain": 0.0,
                "collision_status": "completed",
                "collision_time_mode": "auto",
                "collision_resolved_dt_s": 0.001,
                "collision_resolved_total_time_s": 0.01,
                "collision_peak_contact_force_n": 12_000.0,
                "collision_max_penetration_m": 0.0005,
                "collision_max_penetration_ratio": 0.005,
                "collision_contact_duration_s": 0.002,
                "collision_sphere_momentum_balance_error": 0.01,
                "collision_saved_steps": 5,
                "collision_damage_enabled": 1.0,
                "collision_material_nonlinear_enabled": 1.0,
                "collision_nonlinear_kinematics": "corotational",
                "collision_beam_contact_enabled": 1.0,
                "collision_nonlinear_status": "completed",
                "collision_nonlinear_iterations": 9,
                "collision_nonlinear_cutbacks": 1,
                "collision_nonlinear_max_plastic_strain": 0.02,
                "collision_plastic_damage_threshold": 0.01,
                "collision_deleted_eroded_elements": 2,
                "collision_energy_initial_j": 45.0,
                "collision_energy_final_j": 44.5,
                "collision_sphere_kinetic_initial_j": 45.0,
                "collision_sphere_kinetic_final_j": 5.0,
                "collision_energy_max_relative_drift": 0.011,
                "impact_damage_max_utilization": 0.75,
                "runtime_solver": "sphere collision transient",
            },
            "load_resultant": {},
        },
    )

    text = fe_runtime_solver.format_runtime_fem_result(result)

    assert "Nonlinear static kinematics: corotational" in text
    assert "Consistent beam mass: True" in text
    assert " - direct beam/stiffener contact: True" in text
    assert " - impact kinematics: corotational" in text
    assert "Impact energy balance:" in text
    assert " - deleted/eroded elements: 2" in text


def test_runtime_fem_popup_has_compact_3d_section_preview():
    snapshot = fe_runtime_solver.active_line_snapshot(_FakeApp())

    figure = fe_runtime_solver.create_runtime_fem_geometry_preview_figure(snapshot)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 1
    assert figure.axes[0].get_title() == "3D section view"
    assert hasattr(figure.axes[0], "get_zlim")


def test_runtime_fem_popup_wires_preview_canvas_in_upper_right():
    source = (Path(__file__).resolve().parents[1] / "anystruct" / "fem_integration.py").read_text(encoding="utf-8")
    solver_source = Path(fe_solver.__file__).read_text(encoding="utf-8")

    assert "import queue" in source
    assert "import threading" in source
    assert "body = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)" in source
    assert "body.add(left_panel, weight=2)" in source
    assert "body.add(mid_panel, weight=2)" in source
    assert "body.add(right_panel, weight=3)" in source
    assert "FEM_OPTION_INFO: dict[str, dict[str, str]]" in source
    assert "def _info_button(self, parent: Any, key: str) -> ttk.Button:" in source
    assert "def _show_solver_info(self, key: str) -> None:" in source
    assert "ttk.Button(parent, text=\"i\", width=2" in source
    assert "self.options_notebook = ttk.Notebook(mid_panel)" in source
    assert "self.options_notebook.add(tab_mesh, text=\"Mesh\")" in source
    assert "self.options_notebook.add(tab_loads, text=\"Loads\")" in source
    assert "self.options_notebook.add(tab_bc, text=\"Boundary conditions\")" in source
    assert "self.options_notebook.add(tab_transient, text=\"Transient runs\")" in source
    assert "mesh_size = ttk.LabelFrame(tab_mesh, text=\"Mesh size\")" in source
    assert "local_mesh = ttk.LabelFrame(tab_mesh, text=\"Local mesh refinement (select panels under load and BCs)\")" in source
    assert "self._add_compact_check(local_mesh, 0, 0, \"local_refinement_enabled\", \"Refine selected panels\"" in source
    assert "self._mesh_point_selection_button = ttk.Button(" in source
    assert "command=self._toggle_mesh_point_selection" in source
    assert "command=lambda: self._set_mesh_point_selection_active(False)" in source
    assert "self._add_compact_check(impact_group, 0, 0, \"collision_adaptive_mesh\", \"Adopt impact point\"" in source
    assert "\"local_refinement_enabled\": {" in source
    assert "\"point_refinement_enabled\": {" in source
    assert "\"collision_adaptive_growth_factor\": {" in source
    assert "def _format_run_status_text(" in source
    assert "mesh_preview = ttk.LabelFrame(tab_mesh, text=\"Mesh preview and statistics\")" in source
    assert "self._mesh_preview_button = ttk.Button(preview_actions, text=\"Generate mesh\", command=self._generate_mesh)" in source
    assert "self.mesh_statistics_text = tk.Text(mesh_preview" in source
    assert "whole_bc = ttk.LabelFrame(tab_bc, text=\"Whole-boundary supports (per edge)\")" in source
    assert "edge_bc = ttk.LabelFrame(tab_bc, text=\"Selected-edge supports\")" in source
    assert "variable=self.boundary_edge_choice" in source
    assert "self._build_dof_constraint_grid(whole_bc, start_row=3, prefix=\"boundary\"" in source
    assert "self._build_dof_constraint_grid(edge_bc, start_row=1, prefix=\"edge\"" in source
    assert "command=self._add_custom_bc_from_selection" in source
    assert "accel = ttk.LabelFrame(tab_loads, text=\"Acceleration and added mass\")" in source
    assert "time_domain = ttk.LabelFrame(collision_body, text=\"Custom time-domain load\")" in source
    assert "solver_options = ttk.LabelFrame(tab_general, text=\"Solver\")" in source
    assert "members = ttk.LabelFrame(tab_properties, text=\"Member modelling\")" in source
    assert "material = ttk.LabelFrame(tab_properties, text=\"Material and recovery\")" in source
    assert "self.upper_result_frame = ttk.LabelFrame(right_panel, text=\"Result text\")" in source
    assert "self.upper_result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))" in source
    assert "self.upper_result_text = tk.Text(" in source
    assert "self.result_canvas = Tkinter3DCanvas(" in source
    # Left-panel live run graph below the status text.
    assert "self._live_graph_canvas = FigureCanvasTkAgg(self._live_graph_figure, master=status_frame)" in source
    assert "self._live_graph_reset(\"idle\")" in source
    # Post-buckling continuation inputs on the General tab.
    assert "post_buckling = ttk.LabelFrame(tab_general, text=\"Post-buckling continuation\")" in source
    assert "\"post_buckling_enabled\", \"Trace post-buckling response\"" in source
    assert "self.interactive_3d_checkbox = ttk.Checkbutton(" in source
    assert "def _populate_canvas_with_geometry(" in source
    assert "def _populate_canvas_with_results(" in source
    assert "self.run_button = ttk.Button(buttons, text=\"Run FEM\", command=self.run)" in source
    assert "text=\"Use results for prescriptive buckling\"" in source
    assert "command=self._send_results_to_fea_buckling" in source
    assert "def _send_results_to_fea_buckling(self) -> None:" in source
    assert "import_runtime_fem_buckling_result" in source
    assert "self.progress_bar = ttk.Progressbar(buttons, mode=\"indeterminate\", length=140)" in source
    assert "self.include_end_lids = tk.BooleanVar(value=bool(self.snapshot.is_cylinder))" in source
    assert "self._add_check_row(contents, 3, \"include_end_lids\", \"Top/bottom lid\", self.include_end_lids)" in source
    assert "include_end_lids=bool(self.include_end_lids.get())" in source
    assert "self.ignore_girder_length = tk.BooleanVar(value=False)" in source
    assert "\"Ignore girder length (single stiffener bay)\"" in source
    assert "ignore_girder_length=bool(self.ignore_girder_length.get())" in source
    assert "self.boundary_condition = tk.StringVar(value=\"auto\")" in source
    assert "self.shell_element_order = tk.StringVar(value=\"S4\")" in source
    assert "self.beam_element_order = tk.StringVar(value=\"B2\")" in source
    assert "self.member_model = tk.StringVar(value=\"plates as shell, girders as beams\")" in source
    assert "self.analysis_type = tk.StringVar(value=\"linear eigenvalue\")" in source
    assert "self.nonlinear_static_kinematics = tk.StringVar(value=\"Von Karman\")" in source
    assert "self.beam_consistent_mass_enabled = tk.BooleanVar(value=True)" in source
    assert "self.collision_nonlinear_kinematics = tk.StringVar(value=\"Von Karman\")" in source
    assert "self.collision_beam_contact_enabled = tk.BooleanVar(value=False)" in source
    assert "self.pressure_direction = tk.StringVar(value=\"front\")" in source
    assert "self._add_option_row(general_loads, 6, \"pressure_direction\", \"Pressure side\", self.pressure_direction" in source
    assert "(\"front\", \"back\")" in source
    assert "def _draw_pressure_side_indicators(" in source
    assert "RuntimeFEMWindow._draw_pressure_side_indicators(self, canvas, geometry)" in source
    assert "self.axial_force_n = tk.DoubleVar(value=_safe_float(self.snapshot.axial_force_n, 0.0))" in source
    assert "self.elastic_modulus_gpa = tk.DoubleVar(value=210.0)" in source
    assert "self.plate_alpha_vis = tk.StringVar(value=\"1.0\")" in source
    assert "self.plate_front_color_vis = tk.StringVar(value=\"#d1d5db\")" in source
    assert "self.plate_back_color_vis = tk.StringVar(value=\"#8b5e3c\")" in source
    assert "self._add_entry_row(vis_group, 7, \"plate_front_color\", \"Plate front\", self.plate_front_color_vis" in source
    assert "self._add_entry_row(vis_group, 8, \"plate_back_color\", \"Plate back\", self.plate_back_color_vis" in source
    assert "boundary_condition=str(self.boundary_condition.get())" in source
    assert "beam_element_order=str(self.beam_element_order.get())" in source
    assert "member_model=str(self.member_model.get())" in source
    # Tk variable reads go through the defensive _tk_var_float helper so an
    # empty entry never raises TclError from DoubleVar.get().
    assert "elastic_modulus_pa=max(_tk_var_float(self.elastic_modulus_gpa, 210.0), 1.0e-9) * 1.0e9" in source
    assert "self.progress_bar.start(12)" in source
    assert "threading.Thread(target=worker, daemon=True)" in source
    assert "self.window.after(100, self._poll_solver_result)" in source
    assert "def _poll_solver_result(self) -> None:" in source
    assert "except queue.Empty:" in source
    assert "self._info_button(selector_bar, \"display_choice\").pack" in source
    assert "\"mesh_fidelity\"" in source
    assert "\"pressure_pa\"" in source
    assert "\"yield_stress_mpa\"" in source
    assert "self.custom_load_bc_enabled = tk.BooleanVar(value=False)" in source
    assert "self.custom_loads_add_to_imported = tk.BooleanVar(value=False)" in source
    assert "self.custom_use_nullspace_projection = tk.BooleanVar(value=True)" in source
    assert "self.custom_pressure_pa = tk.DoubleVar(value=0.0)" in source
    assert "self.custom_loads_json = tk.StringVar(value=\"[]\")" in source
    assert "self._custom_load_entries: list[dict[str, Any]] = []" in source
    assert "self._custom_selected_edge_keys: set[tuple[str, float, float, float]] = set()" in source

    assert "self.deformation_scale = tk.StringVar(value=\"0.0\")" in source
    assert "custom_loads = ttk.LabelFrame(tab_loads, text=\"Custom loads\")" in source
    assert "bc_list = ttk.LabelFrame(tab_bc, text=\"Applied boundary conditions\")" in source
    assert "selection_loads = ttk.LabelFrame(custom_loads, text=\"Panel and edge selection\")" in source
    assert "load_list = ttk.LabelFrame(tab_loads, text=\"Loads to run\")" in source
    assert "ttk.Button(actions_loads, text=\"Add load\", command=self._add_custom_load_from_selection)" in source
    assert "ttk.Button(actions_loads, text=\"Delete load\", command=self._delete_selected_custom_load)" in source
    assert "self._custom_load_tree = ttk.Treeview(" in source
    assert "canvas.canvas.bind(\"<ButtonRelease-3>\", self._on_custom_load_edge_canvas_release, add=\"+\")" in source
    assert "def _custom_load_selection_visual_offset(self) -> float:" in source
    assert "draw_overlay=True" in source
    assert "custom_loads_add_to_imported=bool(self.custom_loads_add_to_imported.get())" in source
    assert "bool(self.custom_use_nullspace_projection.get()) and not bool(self.collision_enabled.get())" in source
    assert "custom_pressure_pa=_tk_var_float(self.custom_pressure_pa, 0.0)" in source
    assert "custom_loads_json=str(self.custom_loads_json.get())" in source
    assert "self._add_entry_row(time_domain, 2, \"custom_pressure_pa\"" not in source
    assert "ttk.Button(view_actions, text=\"ISO\", command=lambda: self._set_runtime_3d_view(\"iso\"))" in source
    assert "ttk.Button(view_actions, text=\"Front\", command=lambda: self._set_runtime_3d_view(\"front\"))" in source
    assert "ttk.Button(view_actions, text=\"Top\", command=lambda: self._set_runtime_3d_view(\"top\"))" in source
    assert "def _set_runtime_3d_view(self, view_name: str) -> None:" in source
    assert "self._add_option_row(" in source and "\"member_model\"" in source
    assert "\"webs as shells, flanges as beams\"" in source
    assert "\"all shell\"" in source
    assert "\"nonlinear_static_kinematics\"" in source
    assert "\"beam_consistent_mass\"" in source
    assert "\"collision_nonlinear_kinematics\"" in source
    assert "\"collision_beam_contact\"" in source
    assert "_normalise_kinematics(self.nonlinear_static_kinematics.get())" in source
    assert "_normalise_kinematics(self.collision_nonlinear_kinematics.get())" in source
    assert "collision_beam_contact_enabled=bool(self.collision_beam_contact_enabled.get())" in source
    assert "beam_consistent_mass_enabled=bool(self.beam_consistent_mass_enabled.get())" in source
    assert "beam_contact=bool(config.collision_beam_contact_enabled)" in solver_source
    assert "kinematics=static_kinematics" in solver_source
    assert "kinematics=_normalized_kinematics(config.collision_nonlinear_kinematics)" in solver_source
    assert "section[\"consistent_mass\"] = True" in (
        Path(fe_solver.full_backend_api().__file__).resolve().parent
        / "anystructure_fem_mode.py"
    ).read_text(encoding="utf-8")
    assert "plate_edge_x0_support=str(self.plate_edge_x0_support.get())" in source
    assert "cylinder_upper_edge_load_n_per_m=_tk_var_float(self.cylinder_upper_edge_load_n_per_m, 0.0)" in source
    assert "\"nullspace_projection\"" in source
    assert "horizontal_span" not in source
    # Loads are entered as separate fx/fy/fz/mx/my/mz components for both the
    # selected edges and the whole-edge/top-bottom loads; the whole-edge grid
    # is edited per edge through radio buttons like the boundary conditions.
    assert "self._build_load_component_grid(selection_loads, 1, \"selected_edge_load_components\"" in source
    assert "whole_edge_loads = ttk.LabelFrame(custom_loads, text=\"Whole edge / top-bottom loads\")" in source
    assert "self._build_load_component_grid(whole_edge_loads, 1, \"edge_load_components\"" in source
    assert "variable=self.edge_load_edge_choice,\n                            command=self._on_edge_load_edge_change" in source
    assert "edge_load_components_json=self._collect_edge_load_components_json()" in source
    assert "custom_selected_edge_load_components_json=self._selected_edge_load_components_json()" in source
    # The single scalar inputs are gone from the loads tab.
    assert "\"Selected edges [N/m]\"" not in source
    assert "\"Plate x0 / x1 [N/m]\"" not in source
    assert "\"Cyl. lower / upper [N/m]\"" not in source
    # Run start reflects solver auto-set values back into the controls before
    # collecting the options, and surfaces the changes in the run status.
    assert "auto_set_notes = self._reflect_effective_run_inputs()" in source
    assert source.index("auto_set_notes = self._reflect_effective_run_inputs()") < source.index(
        "options = self._options()\n        self._active_run_options = options")
    assert "self.material_model.set(\"DNV-RP-C208 steel\")" in source
    assert "self.nonlinear_solution_control.set(\"arc length\")" in source
    assert "self._run_status_history.append(\"Auto-set at run start: \" + note)" in source
    # The solver-side diagnostics carry the same transparency.
    solver_source = Path(fe_solver.__file__).read_text(encoding="utf-8")
    assert "diagnostics.extend(_auto_set_parameter_notes(config))" in solver_source


def test_tkinter_3d_canvas_supports_plate_front_back_colours():
    from anystruct import tkinter_3d_canvas_thickness_v6 as tk3d_canvas_module

    source = Path(tk3d_canvas_module.__file__).read_text(encoding="utf-8")

    assert "back_color: str = \"\"" in source
    assert "\"back_color\": back_color" in source
    assert "fill_color = primitive[\"color\"]" in source
    assert "fill_color = primitive.get(\"back_color\") or fill_color" in source
    assert "needs_facing = (" in source
    assert "show_backfaces = bool(back_color) or opacity < 0.90" in source
    assert "render_phase = 1" in source
    assert "render_phase = 2 if primitive.get(\"_front_facing\", True) else 0" in source
    assert "primitive[\"two_sided_shell\"] = bool(back_color)" in source
    assert "if bool(show_backfaces):" in source


def test_tkinter_3d_two_sided_cylinder_shell_does_not_occlude_backside_members():
    from anystruct.tkinter_3d_canvas_thickness_v6 import Point3D, Tkinter3DCanvas

    canvas = Tkinter3DCanvas.__new__(Tkinter3DCanvas)
    canvas._explicit_opaque_cylinder_occluders = []
    canvas.objects = [
        {
            "type": "cylinder",
            "radius": 1.0,
            "height": 10.0,
            "center": Point3D(0.0, 0.0, 0.0),
            "opacity": 1.0,
            "show_backfaces": True,
            "back_color": "brown",
        }
    ]

    assert canvas._collect_opaque_cylinder_occluders() == []

    occluder = {"radius": 1.0, "height": 10.0, "center": Point3D(0.0, 0.0, 0.0)}
    assert canvas._primitive_hidden_by_opaque_cylinder(
        {"kind": "polygon", "layer": 20, "center": Point3D(0.0, -0.5, 0.0)},
        (occluder,),
        Point3D(0.0, -4.0, 0.0),
    )


def test_runtime_fem_standalone_example_uses_main_application_section_preview():
    app = fe_runtime_solver.example_runtime_app()
    snapshot = fe_runtime_solver.active_line_snapshot(app)

    figure = fe_runtime_solver.create_runtime_fem_geometry_preview_figure(snapshot, app)

    assert isinstance(figure, Figure)
    assert figure.axes[0].get_title() == "3D stiffened panel with girder"
    assert len(figure.axes[0].collections) > 3


def test_lightweight_solver_returns_positive_fast_panel_results():
    result = fe_solver.run_lightweight_fem(
        {
            "geometry": "flat panel",
            "length_m": 2.5,
            "width_m": 0.75,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": True,
        },
        fe_solver.LightweightFEMConfig(pressure_pa=120_000.0, mesh_fidelity="coarse", num_buckling_modes=3),
    )

    assert result.status == "ok"
    assert result.stress_max_pa > 0.0
    assert result.displacement_max_m > 0.0
    assert len(result.buckling_factors) == 3
    assert result.mesh_info["beams"] == 2
    assert result.prestress_summary["critical_stress_pa"] > 0.0
    assert result.load_resultant["force_n"][2] > 0.0
    assert result.visualization["type"] == "flat"
    assert len(result.visualization["x_m"]) == 9
    assert len(result.visualization["stress_pa"]) == 9


def test_production_solver_runs_full_panel_mesh_backend():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 1.2,
            "width_m": 0.6,
            "thickness_m": 0.01,
            "has_stiffener": True,
            "has_girder": True,
        },
        fe_solver.LightweightFEMConfig(pressure_pa=25_000.0, mesh_fidelity="coarse", num_buckling_modes=2),
    )

    assert result.status == "ok"
    assert result.solver_name == "ANYsolver production FE mesh"
    assert result.mesh_info["nodes"] > 0
    assert result.mesh_info["shells"] > 0
    assert result.mesh_info["beams"] > 0
    assert result.stress_max_pa >= 0.0
    assert result.displacement_max_m >= 0.0
    assert result.visualization["type"] == "flat"
    assert result.visualization["stress_pa"]


def test_production_solver_runs_full_cylinder_mesh_with_beams_and_buckling():
    result = fe_solver.run_production_fem(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 1.5,
            "thickness_m": 0.02,
            "has_stiffener": True,
            "has_girder": True,
        },
        fe_solver.LightweightFEMConfig(pressure_pa=10_000.0, mesh_fidelity="coarse", num_buckling_modes=2),
    )

    assert result.status == "ok"
    assert result.mesh_info["shells"] > 0
    assert result.mesh_info["beams"] > 0
    assert result.stress_max_pa > 0.0
    assert result.displacement_max_m > 0.0
    assert result.buckling_factors == tuple(sorted(result.buckling_factors))
    assert result.buckling_factors[0] > 0.0
    assert result.visualization["type"] == "cylinder"
    assert result.visualization["stress_pa"]
    assert len(result.visualization["buckling_modes"]) >= 1
    assert result.visualization["buckling_modes"][0]["shape"]["type"] == "cylinder"


def test_generated_cylinder_mesh_uses_fb100x10_stiffener_section():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 5.0,
        "thickness_m": 0.02,
        "has_stiffener": True,
        "has_girder": False,
        "stiffener_section": {
            "area": 0.1 * 0.01,
            "Iy": 0.01 * 0.1**3 / 12.0,
            "Iz": 0.1 * 0.01**3 / 12.0,
            "J": 0.01 * 0.1**3 / 12.0 + 0.1 * 0.01**3 / 12.0,
        },
    }

    generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse"),
    )
    first_stiffener = next(beam for beam in generated["beams"] if beam["role"] == "stiffener")

    assert first_stiffener["section"]["area"] == 0.001
    assert first_stiffener["section"]["Iy"] == 0.01 * 0.1**3 / 12.0
    assert first_stiffener["section"]["Iz"] == 0.1 * 0.01**3 / 12.0


def test_flat_generated_mesh_forces_edges_at_member_lines_when_mesh_is_coarse():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "flat panel",
            "length_m": 4.0,
            "width_m": 0.7,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": True,
        },
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0),
    )

    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}
    y_values = {round(coords[node_id][1], 6) for node_id in coords}
    x_values = {round(coords[node_id][0], 6) for node_id in coords}
    stiffener_beams = [beam for beam in generated["beams"] if beam["role"] == "stiffener"]
    girder_beams = [beam for beam in generated["beams"] if beam["role"] == "girder"]

    assert 0.35 in y_values
    assert 2.0 in x_values
    assert stiffener_beams
    assert girder_beams
    assert all(round(coords[node_id][1], 6) == 0.35 for beam in stiffener_beams for node_id in beam["node_ids"])
    assert all(round(coords[node_id][0], 6) == 2.0 for beam in girder_beams for node_id in beam["node_ids"])


def test_flat_generated_mesh_caps_element_size_to_stiffener_spacing():
    spacing = 0.7
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "flat panel",
            "length_m": 4.0,
            "width_m": spacing,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": False,
            "stiffener_spacing_m": spacing,
        },
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0),
    )

    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}
    x_values = sorted({coords[node_id][0] for node_id in coords})
    y_values = sorted({coords[node_id][1] for node_id in coords})

    assert max(b - a for a, b in zip(x_values, x_values[1:])) <= spacing + 1.0e-9
    assert max(b - a for a, b in zip(y_values, y_values[1:])) <= spacing + 1.0e-9


def test_flat_mesh_size_is_not_capped_by_disabled_members():
    requested = 3.0
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "flat panel",
            "length_m": 10.0,
            "width_m": 2.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_spacing_m": 0.5,
            "girder_spacing_m": 0.5,
        },
        fe_solver.LightweightFEMConfig(
            mesh_size_m=requested,
            include_stiffeners=False,
            include_girders=False,
        ),
    )

    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}
    x_values = sorted({coords[node_id][0] for node_id in coords})
    y_values = sorted({coords[node_id][1] for node_id in coords})

    assert not generated["beams"]
    assert max(b - a for a, b in zip(x_values, x_values[1:])) <= requested + 1.0e-9
    assert max(b - a for a, b in zip(y_values, y_values[1:])) <= requested + 1.0e-9
    assert max(b - a for a, b in zip(x_values, x_values[1:])) > 0.5


def test_runtime_generated_mesh_uses_boundary_and_member_orientation_options():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "flat panel",
            "length_m": 4.0,
            "width_m": 1.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": False,
            "stiffener_spacing_m": 0.5,
        },
        fe_solver.LightweightFEMConfig(
            boundary_condition="simply supported",
            member_orientation="global Z",
            stiffener_eccentricity_m=0.08,
        ),
    )

    assert generated["supports"][0]["name"] == "simple_panel_boundary"
    assert generated["supports"][0]["constraints"] == {"uz": 0.0}
    first_stiffener = next(beam for beam in generated["beams"] if beam["role"] == "stiffener")
    assert first_stiffener["section"]["orientation"] == (0.0, 0.0, 1.0)
    assert first_stiffener["section"]["eccentricity_m"] == 0.08
    assert generated["couplings"]
    assert first_stiffener["node_ids"][0] != generated["couplings"][0]["shell_node_ids"][0]
    assert generated["couplings"][0]["eccentricity"] == [0.0, 0.0, 0.08]


def test_runtime_generated_mesh_supports_s8_shells_and_enforced_displacement():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "flat panel",
            "length_m": 2.0,
            "width_m": 1.0,
            "thickness_m": 0.012,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            shell_element_order="S8",
            boundary_condition="simply supported",
            symmetry_mode="x",
            enforced_displacement_z_m=0.003,
        ),
    )

    assert all(len(shell["node_ids"]) == 8 for shell in generated["shells"])
    assert len(generated["nodes"]) > len(generated["plot_grid"]) * len(generated["plot_grid"][0])
    assert any(support["name"].startswith("symmetry_") for support in generated["supports"])
    assert any(support["name"] == "enforced_panel_displacement" for support in generated["supports"])


def test_runtime_generated_mesh_supports_b2_and_b3_beam_elements():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": 0.5,
        "girder_spacing_m": 1.0,
    }

    b2 = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", beam_element_order="B2"),
    )
    b3_config = fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", beam_element_order="B3")
    b3 = fe_solver.build_generated_geometry(geometry, b3_config)

    assert b2["beams"]
    assert b3["beams"]
    assert {len(beam["node_ids"]) for beam in b2["beams"]} == {2}
    assert {len(beam["node_ids"]) for beam in b3["beams"]} == {3}
    assert fe_solver._mesh_size_diagnostics(b2)["beam_order"] == "B2"
    assert fe_solver._mesh_size_diagnostics(b3)["beam_order"] == "B3"


def test_runtime_generated_mesh_supports_member_shell_modelling_modes():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": 0.5,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2,
            "web_thickness": 0.01,
            "flange_width": 0.08,
            "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.3,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }

    current = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", member_model="plates as shell, girders as beams"),
    )
    mixed = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", member_model="webs as shells, flanges as beams"),
    )
    all_shell = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", member_model="all shell"),
    )

    assert len(mixed["shells"]) > len(current["shells"])
    assert any(str(shell.get("role", "")).endswith("_web") for shell in mixed["shells"])
    assert any(str(beam.get("role", "")).endswith("_flange") for beam in mixed["beams"])
    assert len(all_shell["shells"]) > len(mixed["shells"])
    assert not all_shell["beams"]
    assert any(str(shell.get("role", "")).endswith("_flange") for shell in all_shell["shells"])
    node_by_id = {int(node["id"]): node for node in mixed["nodes"]}
    web_roles_by_node: dict[int, set[str]] = {}
    for shell in mixed["shells"]:
        role = str(shell.get("role", ""))
        if role in {"stiffener_web", "girder_web"}:
            for node_id in shell["node_ids"]:
                web_roles_by_node.setdefault(int(node_id), set()).add(role)
    shared_above_plate = [
        node_id
        for node_id, roles in web_roles_by_node.items()
        if {"stiffener_web", "girder_web"} <= roles
        and abs(float(node_by_id[node_id]["coords"][2])) > 1.0e-9
    ]
    assert shared_above_plate

    if fe_solver._full_backend is not None:
        for member_model in ("webs as shells, flanges as beams", "all shell"):
            result = fe_solver.run_production_fem(
                geometry,
                fe_solver.LightweightFEMConfig(
                    mesh_fidelity="coarse",
                    pressure_pa=1000.0,
                    member_model=member_model,
                    runtime_solver="static only",
                    boundary_condition="fixed",
                ),
            )
            assert result.status == "ok"
            assert any("Member modelling:" in item for item in result.diagnostics)


def test_cylinder_member_shell_web_crossings_share_connection_nodes():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": math.pi / 2.0,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2,
            "web_thickness": 0.01,
            "flange_width": 0.08,
            "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.35,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }

    generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", member_model="webs as shells, flanges as beams"),
    )

    node_by_id = {int(node["id"]): node for node in generated["nodes"]}
    web_roles_by_node: dict[int, set[str]] = {}
    for shell in generated["shells"]:
        role = str(shell.get("role", ""))
        if role in {"stiffener_web", "girder_web"}:
            for node_id in shell["node_ids"]:
                web_roles_by_node.setdefault(int(node_id), set()).add(role)
    shared_inside_shell = []
    for node_id, roles in web_roles_by_node.items():
        if not {"stiffener_web", "girder_web"} <= roles:
            continue
        x, y, _z = (float(value) for value in node_by_id[node_id]["coords"])
        if math.hypot(x, y) < 1.0 - 1.0e-9:
            shared_inside_shell.append(node_id)

    assert shared_inside_shell


def _role_shells(generated, role):
    return [shell for shell in generated["shells"] if str(shell.get("role", "")) == role]


def _shell_edges(shell):
    node_ids = [int(node_id) for node_id in shell["node_ids"]]
    return {
        tuple(sorted((node_ids[index], node_ids[(index + 1) % len(node_ids)])))
        for index in range(len(node_ids))
    }


def test_all_shell_member_flanges_share_edges_with_web_tops():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": math.pi / 2.0,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2,
            "web_thickness": 0.01,
            "flange_width": 0.08,
            "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.35,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }

    generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="medium", member_model="all shell"),
    )

    for prefix in ("stiffener", "girder"):
        web_shells = _role_shells(generated, prefix + "_web")
        flange_edges = set()
        for flange_shell in _role_shells(generated, prefix + "_flange"):
            flange_edges.update(_shell_edges(flange_shell))

        web_edge_counts = {}
        for shell in web_shells:
            for edge in _shell_edges(shell):
                web_edge_counts[edge] = web_edge_counts.get(edge, 0) + 1
        web_top_edges = {
            tuple(sorted((int(shell["node_ids"][2]), int(shell["node_ids"][3]))))
            for shell in web_shells
            if web_edge_counts.get(tuple(sorted((int(shell["node_ids"][2]), int(shell["node_ids"][3])))), 0) == 1
        }

        assert web_top_edges
        assert flange_edges
        assert web_top_edges <= flange_edges


def test_all_shell_perpendicular_web_crossings_share_s4_edges():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": math.pi / 2.0,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2,
            "web_thickness": 0.01,
            "flange_width": 0.08,
            "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.35,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }

    generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="fine", member_model="all shell"),
    )

    stiffener_edges = set()
    for shell in _role_shells(generated, "stiffener_web"):
        stiffener_edges.update(_shell_edges(shell))
    girder_edges = set()
    for shell in _role_shells(generated, "girder_web"):
        girder_edges.update(_shell_edges(shell))

    shared_web_edges = stiffener_edges & girder_edges
    expected_crossings = int(round(2.0 * math.pi * geometry["radius_m"] / geometry["stiffener_spacing_m"]))
    expected_segments_per_crossing = 3

    assert len(shared_web_edges) >= expected_crossings * expected_segments_per_crossing


@pytest.mark.parametrize(("mesh_fidelity", "expected_segments"), (("medium", 2), ("fine", 3)))
def test_all_shell_web_depth_subdivision_follows_mesh_fidelity(mesh_fidelity, expected_segments):
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": True,
        "girder_spacing_m": 1.0,
        "girder_section": {
            "web_height": 0.35,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }

    generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity=mesh_fidelity, member_model="all shell"),
    )

    circumferential_divisions = len(generated["plot_grid"][0]) - 1

    # L = 2.0 is an exact multiple of the 1.0 m girder spacing: the ring
    # frames bound the bays (bottom, middle, top), giving three frames.
    frame_count = 3
    assert len(_role_shells(generated, "girder_web")) == circumferential_divisions * expected_segments * frame_count
    assert len(_role_shells(generated, "girder_flange")) == circumferential_divisions * 2 * frame_count


@pytest.mark.parametrize("member_model", ("webs as shells, flanges as beams", "all shell"))
def test_runtime_cylinder_member_shell_modes_solve_and_visualize_member_surfaces(member_model):
    if fe_solver._full_backend is None:
        pytest.skip("production FE backend unavailable")

    snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app("cylinder"))
    geometry = fe_runtime_solver.runtime_geometry_summary(snapshot)
    config = fe_solver.LightweightFEMConfig(
        mesh_fidelity="coarse",
        pressure_pa=snapshot.pressure_pa,
        include_stiffeners=True,
        include_girders=True,
        include_end_lids=True,
        member_model=member_model,
        runtime_solver="static only",
        num_buckling_modes=1,
    )
    generated = fe_solver.build_generated_geometry(geometry, config)
    expected_surface_count = sum(
        1
        for shell in generated["shells"]
        if str(shell.get("role", "skin") or "skin").lower() not in {"", "skin"}
    )
    result = fe_solver.run_production_fem(
        geometry,
        config,
    )

    shell_surfaces = tuple(result.visualization.get("shell_surfaces", ()) or ())
    roles = {str(surface.get("role", "")) for surface in shell_surfaces}

    assert result.status == "ok"
    assert result.mesh_info["shells"] > 800
    assert len(shell_surfaces) == expected_surface_count
    assert "stiffener_web" in roles
    assert "girder_web" in roles
    if member_model == "all shell":
        assert any(role.endswith("_flange") for role in roles)
    assert any("plating skin only" in item for item in result.diagnostics)
    assert not any("compact fallback" in item.lower() for item in result.diagnostics)


def test_flat_member_shell_boundary_conditions_include_generated_edge_shell_nodes():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": 0.5,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2,
            "web_thickness": 0.01,
            "flange_width": 0.08,
            "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.3,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }
    configs = (
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            member_model="all shell",
            boundary_condition="fixed",
        ),
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            member_model="all shell",
            custom_load_bc_enabled=True,
            custom_use_nullspace_projection=False,
            plate_edge_x0_support="fixed",
            plate_edge_x1_support="fixed",
            plate_edge_y0_support="fixed",
            plate_edge_y1_support="fixed",
        ),
    )

    for config in configs:
        generated = fe_solver.build_generated_geometry(geometry, config)
        support_nodes = {int(node_id) for support in generated["supports"] for node_id in support["node_ids"]}
        shell_nodes = {int(node_id) for shell in generated["shells"] for node_id in shell["node_ids"]}
        node_by_id = {int(node["id"]): node for node in generated["nodes"]}
        edge_shell_nodes = {
            node_id
            for node_id in shell_nodes
            if abs(float(node_by_id[node_id]["coords"][0])) <= 1.0e-8
            or abs(float(node_by_id[node_id]["coords"][0]) - geometry["length_m"]) <= 1.0e-8
            or abs(float(node_by_id[node_id]["coords"][1])) <= 1.0e-8
            or abs(float(node_by_id[node_id]["coords"][1]) - geometry["width_m"]) <= 1.0e-8
        }

        assert edge_shell_nodes
        assert edge_shell_nodes <= support_nodes


def _member_shell_node_ids(generated: dict) -> set[int]:
    return {
        int(node_id)
        for shell in generated["shells"]
        if str(shell.get("role", "")).endswith(("_web", "_flange"))
        for node_id in shell["node_ids"]
    }


def test_members_opposite_side_flips_flat_member_geometry():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.5,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": 0.5,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2, "web_thickness": 0.01,
            "flange_width": 0.08, "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.3, "web_thickness": 0.012,
            "flange_width": 0.12, "flange_thickness": 0.014,
        },
    }
    config = fe_solver.LightweightFEMConfig(
        mesh_fidelity="coarse",
        member_model="webs as shells, flanges as beams",
        stiffener_eccentricity_m=0.05,
    )

    default = fe_solver.build_generated_geometry(geometry, config)
    flipped = fe_solver.build_generated_geometry(
        {**geometry, "members_opposite_side": True}, config
    )

    for generated, expected_sign in ((default, 1.0), (flipped, -1.0)):
        node_by_id = {int(node["id"]): node for node in generated["nodes"]}
        member_z = [
            float(node_by_id[node_id]["coords"][2])
            for node_id in _member_shell_node_ids(generated)
            if abs(float(node_by_id[node_id]["coords"][2])) > 1.0e-9
        ]
        assert member_z, "member webs must have off-plane nodes"
        assert all(z * expected_sign > 0.0 for z in member_z)

    # Beam-mode eccentricity flips with the side as well.
    beam_config = fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", stiffener_eccentricity_m=0.05)
    default_beams = fe_solver.build_generated_geometry(geometry, beam_config)
    flipped_beams = fe_solver.build_generated_geometry(
        {**geometry, "members_opposite_side": True}, beam_config
    )
    default_ecc = {
        float((beam.get("section") or {}).get("eccentricity_m", 0.0))
        for beam in default_beams["beams"] if beam.get("role") == "stiffener"
    }
    flipped_ecc = {
        float((beam.get("section") or {}).get("eccentricity_m", 0.0))
        for beam in flipped_beams["beams"] if beam.get("role") == "stiffener"
    }
    assert default_ecc == {0.05}
    assert flipped_ecc == {-0.05}


def test_members_opposite_side_flips_cylinder_member_geometry():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": math.pi / 2.0,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2, "web_thickness": 0.01,
            "flange_width": 0.08, "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.35, "web_thickness": 0.012,
            "flange_width": 0.12, "flange_thickness": 0.014,
        },
    }
    config = fe_solver.LightweightFEMConfig(
        mesh_fidelity="coarse",
        member_model="webs as shells, flanges as beams",
        include_end_lids=False,
    )

    default = fe_solver.build_generated_geometry(geometry, config)
    flipped = fe_solver.build_generated_geometry(
        {**geometry, "members_opposite_side": True}, config
    )

    for generated, inward in ((default, True), (flipped, False)):
        node_by_id = {int(node["id"]): node for node in generated["nodes"]}
        member_radii = [
            math.hypot(float(node_by_id[node_id]["coords"][0]), float(node_by_id[node_id]["coords"][1]))
            for node_id in _member_shell_node_ids(generated)
        ]
        off_shell = [radius for radius in member_radii if abs(radius - 1.0) > 1.0e-6]
        assert off_shell, "member webs must extend off the shell surface"
        if inward:
            assert all(radius < 1.0 for radius in off_shell)
        else:
            assert all(radius > 1.0 for radius in off_shell)


class _FakeAppFlatMembersOppositeSide(_FakeAppFlatMembers):
    _new_prop_3d_opposite_side = _SimpleVar(True)


def test_snapshot_and_summary_transfer_main_app_opposite_side_setting():
    default_snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembers())
    assert default_snapshot.members_opposite_side is False
    assert fe_runtime_solver.runtime_geometry_summary(default_snapshot)["members_opposite_side"] is False

    flipped_snapshot = fe_runtime_solver.active_line_snapshot(_FakeAppFlatMembersOppositeSide())
    assert flipped_snapshot.members_opposite_side is True
    summary = fe_runtime_solver.runtime_geometry_summary(flipped_snapshot)
    assert summary["members_opposite_side"] is True

    # The generated FE mesh follows the flag end to end.
    generated = fe_solver.build_generated_geometry(
        summary,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", member_model="webs as shells, flanges as beams"),
    )
    node_by_id = {int(node["id"]): node for node in generated["nodes"]}
    member_z = [
        float(node_by_id[node_id]["coords"][2])
        for node_id in _member_shell_node_ids(generated)
        if abs(float(node_by_id[node_id]["coords"][2])) > 1.0e-9
    ]
    assert member_z
    assert all(z < 0.0 for z in member_z)


def test_cylinder_member_shell_boundary_conditions_cover_generated_end_shell_nodes():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": math.pi / 2.0,
        "girder_spacing_m": 1.0,
        "stiffener_section": {
            "web_height": 0.2,
            "web_thickness": 0.01,
            "flange_width": 0.08,
            "flange_thickness": 0.012,
        },
        "girder_section": {
            "web_height": 0.35,
            "web_thickness": 0.012,
            "flange_width": 0.12,
            "flange_thickness": 0.014,
        },
    }

    no_lid = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            member_model="all shell",
            boundary_condition="fixed",
            include_end_lids=False,
        ),
    )
    support_nodes = {int(node_id) for support in no_lid["supports"] for node_id in support["node_ids"]}
    node_by_id = {int(node["id"]): node for node in no_lid["nodes"]}
    end_shell_nodes = {
        int(node_id)
        for shell in no_lid["shells"]
        for node_id in shell["node_ids"]
        if abs(float(node_by_id[int(node_id)]["coords"][2])) <= 1.0e-8
        or abs(float(node_by_id[int(node_id)]["coords"][2]) - geometry["length_m"]) <= 1.0e-8
    }

    assert end_shell_nodes
    assert end_shell_nodes <= support_nodes

    with_lid = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            member_model="all shell",
            boundary_condition="fixed",
            include_end_lids=True,
        ),
    )
    node_by_id = {int(node["id"]): node for node in with_lid["nodes"]}
    end_shell_nodes = {
        int(node_id)
        for shell in with_lid["shells"]
        for node_id in shell["node_ids"]
        if abs(float(node_by_id[int(node_id)]["coords"][2])) <= 1.0e-8
        or abs(float(node_by_id[int(node_id)]["coords"][2]) - geometry["length_m"]) <= 1.0e-8
    }
    lid_ring_nodes = {int(node_id) for lid in with_lid["rigid_lids"] for node_id in lid["ring_node_ids"]}
    support_nodes = {int(node_id) for support in with_lid["supports"] for node_id in support["node_ids"]}
    lid_reference_nodes = {int(lid["center_node_id"]) for lid in with_lid["rigid_lids"]}

    assert end_shell_nodes <= lid_ring_nodes
    assert support_nodes == lid_reference_nodes


def test_custom_plate_supports_and_edge_loads_are_applied():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        pressure_pa=100.0,
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=False,
        plate_edge_x0_support="fixed",
        plate_edge_x1_support="simply supported",
        plate_edge_x1_load_n_per_m=-1000.0,
    )

    generated = fe_solver.build_generated_geometry(geometry, config)
    result = fe_solver.run_production_fem(geometry, config)

    assert generated["supports"][0]["name"] == "custom_plate_x0_fixed"
    assert generated["supports"][1]["name"] == "custom_plate_x1_simply_supported"
    assert result.status == "ok"
    assert result.load_resultant["force_n"][0] == pytest.approx(-1000.0)
    assert result.load_resultant["force_n"][2] == pytest.approx(0.0)
    assert result.prestress_summary["constraint_method"] == "transformation_fixed_plus_mpc"
    assert result.prestress_summary["nullspace_projection"] == 0.0
    assert any("custom load and boundary-condition mode" in item.lower() for item in result.diagnostics)
    assert any("replace imported/generated" in item.lower() for item in result.diagnostics)


def test_custom_selected_internal_edge_load_adds_mesh_breaks_and_resultant():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        plate_edge_x0_support="fixed",
        custom_selected_edge_load_n_per_m=250.0,
        custom_edge_segments_json=(
            '[{"varying_axis":"a","fixed_coordinate":0.5,'
            '"start_coordinate":0.5,"end_coordinate":1.5}]'
        ),
    )

    generated = fe_solver.build_generated_geometry(geometry, config)
    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}
    result = fe_solver.run_production_fem(geometry, config)

    assert 0.5 in {round(coord[0], 6) for coord in coords.values()}
    assert 1.5 in {round(coord[0], 6) for coord in coords.values()}
    assert 0.5 in {round(coord[1], 6) for coord in coords.values()}
    assert result.status == "ok"
    assert result.load_resultant["force_n"][1] == pytest.approx(250.0)
    assert any("selected edge segments" in item.lower() for item in result.diagnostics)


def test_whole_edge_component_loads_apply_global_forces_and_moments():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=False,
        plate_edge_x0_support="fixed",
        edge_load_components_json=json.dumps({
            "x1": {"fx": 800.0, "fz": -300.0},
            "y1": {"my": 50.0},
        }),
    )

    result = fe_solver.run_production_fem(geometry, config)

    assert result.status == "ok"
    # x1 edge (length 1.0): fx/fz applied per metre on global axes with no
    # implicit outward sign convention.
    assert result.load_resultant["force_n"][0] == pytest.approx(800.0)
    assert result.load_resultant["force_n"][1] == pytest.approx(0.0)
    assert result.load_resultant["force_n"][2] == pytest.approx(-300.0)
    # Moment resultant about the origin: r x F of the x1 edge forces at
    # x=2.0, y-centroid 0.5 gives (-150, 600, -400); the distributed my on
    # the y1 edge (length 2.0) adds 100 as pure nodal moments.
    assert result.load_resultant["moment_nm"][0] == pytest.approx(-150.0)
    assert result.load_resultant["moment_nm"][1] == pytest.approx(700.0)
    assert result.load_resultant["moment_nm"][2] == pytest.approx(-400.0)
    assert any("whole-edge component loads" in item.lower() for item in result.diagnostics)


def test_selected_edge_component_loads_apply_global_forces_and_moments():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    segment = {"varying_axis": "a", "fixed_coordinate": 0.5,
               "start_coordinate": 0.5, "end_coordinate": 1.5}
    entry_config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=False,
        plate_edge_x0_support="fixed",
        custom_loads_json=json.dumps([
            {"type": "edge", "components": {"fy": 250.0, "mz": 40.0}, "edges": [segment]}
        ]),
    )

    result = fe_solver.run_production_fem(geometry, entry_config)

    assert result.status == "ok"
    # Segment length 1.0 at x-centroid 1.0: fy resultant 250 and Mz about the
    # origin 250 (r x F) + 40 (distributed nodal mz).
    assert result.load_resultant["force_n"][1] == pytest.approx(250.0)
    assert result.load_resultant["moment_nm"][2] == pytest.approx(290.0)

    # Without saved entries the staged component grid flows through the
    # config-level payload and the same segments JSON.
    fallback_config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=False,
        plate_edge_x0_support="fixed",
        custom_selected_edge_load_components_json=json.dumps({"fz": -120.0}),
        custom_edge_segments_json=json.dumps([segment]),
    )

    fallback_result = fe_solver.run_production_fem(geometry, fallback_config)

    assert fallback_result.status == "ok"
    assert fallback_result.load_resultant["force_n"][2] == pytest.approx(-120.0)
    assert any("selected edge segments" in item.lower() for item in fallback_result.diagnostics)


def test_runtime_options_pass_edge_load_component_payloads_to_solver_config():
    options = fe_runtime_solver.RuntimeFEMOptions(
        edge_load_components_json='{"x0": {"fy": 10.0}}',
        custom_selected_edge_load_components_json='{"fz": -5.0, "mx": 2.0}',
    )

    config = fe_runtime_solver._solver_config_from_options(options)

    assert config.edge_load_components_json == '{"x0": {"fy": 10.0}}'
    assert config.custom_selected_edge_load_components_json == '{"fz": -5.0, "mx": 2.0}'


def test_auto_set_parameter_notes_report_solver_overrides():
    # A plain linear run auto-sets nothing.
    assert fe_solver._auto_set_parameter_notes(fe_solver.LightweightFEMConfig()) == []

    # Material-nonlinear analysis promotes the linear-elastic dropdown.
    notes = fe_solver._auto_set_parameter_notes(fe_solver.LightweightFEMConfig(
        analysis_type="geom. + material nonlinear static",
        material_model="linear elastic",
    ))
    assert any("material model 'linear elastic' -> 'DNV-RP-C208 steel'" in note for note in notes)
    assert any("the analysis type requests material nonlinearity" in note for note in notes)

    # Post-buckling promotes both the material model and the solution control.
    notes = fe_solver._auto_set_parameter_notes(fe_solver.LightweightFEMConfig(
        post_buckling_enabled=True,
        material_model="linear elastic",
        nonlinear_solution_control="newton force control",
    ))
    assert any("post-buckling continuation always runs with steel plasticity" in note for note in notes)
    assert any("-> 'arc length'" in note for note in notes)

    # Arc length forces Von Karman kinematics over a corotational choice.
    notes = fe_solver._auto_set_parameter_notes(fe_solver.LightweightFEMConfig(
        analysis_type="geometric nonlinear static",
        nonlinear_solution_control="arc length",
        nonlinear_static_kinematics="corotational",
    ))
    assert any("kinematics 'corotational' -> 'Von Karman'" in note for note in notes)

    # Unsupported layer counts snap to the nearest supported value.
    notes = fe_solver._auto_set_parameter_notes(fe_solver.LightweightFEMConfig(
        analysis_type="geom. + material nonlinear static",
        material_model="DNV-RP-C208 steel",
        nonlinear_layers=6,
    ))
    assert any("shell integration layers 6 -> 5" in note for note in notes)

    # Selecting the curve explicitly is not an override.
    notes = fe_solver._auto_set_parameter_notes(fe_solver.LightweightFEMConfig(
        analysis_type="geom. + material nonlinear static",
        material_model="DNV-RP-C208 steel",
    ))
    assert not any("material model" in note for note in notes)


def test_material_nonlinear_run_reports_auto_set_material_model():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        mesh_fidelity="coarse",
        pressure_pa=100_000.0,
        analysis_type="geom. + material nonlinear static",
        material_model="linear elastic",
        nonlinear_steps=3,
        num_buckling_modes=1,
    )

    result = fe_solver.run_production_fem(geometry, config)

    assert result.status == "ok"
    assert any(
        "Auto-set: material model 'linear elastic' -> 'DNV-RP-C208 steel'" in item
        for item in result.diagnostics
    )
    assert any("Using DNV-RP-C208 material curve" in item for item in result.diagnostics)


def test_linear_run_reports_no_auto_set_and_no_plasticity_claims():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        mesh_fidelity="coarse",
        pressure_pa=100_000.0,
        num_buckling_modes=1,
    )

    result = fe_solver.run_production_fem(geometry, config)

    assert result.status == "ok"
    assert result.stress_max_pa > 0.0
    # No parameter overrides happen in a plain linear run.
    assert not any("Auto-set: material model" in item for item in result.diagnostics)
    assert not any("Auto-set: nonlinear solution control" in item for item in result.diagnostics)
    assert not any("Auto-set: kinematics" in item for item in result.diagnostics)
    assert not any("elastoplastic" in item.lower() for item in result.diagnostics)
    assert not any("material curve" in item.lower() for item in result.diagnostics)
    # The automatic support fallback is itself stated explicitly as auto-set.
    assert any(
        "Auto-set: no edge DOF is constrained, so automatic well-posed edge supports were applied" in item
        for item in result.diagnostics
    )


def test_saved_custom_load_entries_add_panel_and_edge_breaks_to_mesh():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        custom_loads_json=json.dumps([
            {
                "type": "pressure",
                "pressure_pa": 500.0,
                "patches": [{"min_a": 0.25, "max_a": 0.75, "min_b": 0.2, "max_b": 0.6}],
            },
            {
                "type": "edge",
                "line_load_n_per_m": 125.0,
                "edges": [{"varying_axis": "a", "fixed_coordinate": 0.5, "start_coordinate": 0.4, "end_coordinate": 0.8}],
            },
        ]),
    )

    generated = fe_solver.build_generated_geometry(geometry, config)
    coords = {node["id"]: tuple(node["coords"]) for node in generated["nodes"]}

    assert {0.25, 0.75, 0.4, 0.8}.issubset({round(coord[0], 6) for coord in coords.values()})
    assert {0.2, 0.5, 0.6}.issubset({round(coord[1], 6) for coord in coords.values()})
    assert fe_solver._custom_pressure_patch_count(config) == 1
    assert len(fe_solver._custom_edge_segments(config)) == 1


def test_centered_cylinder_custom_pressure_patch_selects_matching_axial_location():
    geometry = {
        "geometry": "cylinder",
        "length_m": 5.0,
        "radius_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        custom_loads_json=json.dumps([
            {
                "type": "pressure",
                "pressure_pa": 500.0,
                "patches": [
                    {
                        "min_a": 0.0,
                        "max_a": 2.5,
                        "min_b": 0.0,
                        "max_b": 2.0 * math.pi,
                        "axis_a_origin": "centered",
                    }
                ],
            },
        ]),
    )
    generated = fe_solver.build_generated_geometry(geometry, config)
    nodes = {int(node["id"]): tuple(node["coords"]) for node in generated["nodes"]}

    class DummyElement:
        thickness = 0.012

        def __init__(self, node_ids):
            self.node_ids = tuple(node_ids)

        def get_node_coordinates(self, _mesh):
            return [nodes[int(node_id)] for node_id in self.node_ids]

    class DummyMesh:
        def __init__(self):
            self.elements = {
                int(shell["id"]): DummyElement(shell["node_ids"])
                for shell in generated["shells"]
                if shell.get("role", "skin") == "skin"
            }

        def get_element(self, element_id):
            return self.elements.get(int(element_id))

    class DummyModel:
        mesh = DummyMesh()

    patches = fe_solver._custom_pressure_patches(config)
    selected = fe_solver._custom_pressure_patch_element_ids_from_patches(
        DummyModel(),
        generated,
        geometry,
        patches,
    )
    selected_centroid_z = [
        fe_solver._element_centroid(DummyModel(), element_id)[2]
        for element_id in selected
    ]

    class DummyLoadCase:
        def __init__(self):
            self.pressure_loads = {}

        def add_pressure_load(self, element_id, pressure):
            self.pressure_loads[int(element_id)] = float(pressure)

    load_case = DummyLoadCase()
    applied = fe_solver._add_custom_panel_pressure_loads(
        DummyModel(),
        load_case,
        generated,
        geometry,
        config,
    )

    assert selected
    assert min(selected_centroid_z) >= 2.5 - 1.0e-9
    assert max(selected_centroid_z) <= 5.0 + 1.0e-9
    assert applied == len(selected)
    assert set(load_case.pressure_loads) == set(selected)


def test_custom_plate_loads_can_be_added_to_imported_pressure():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        pressure_pa=100.0,
        custom_load_bc_enabled=True,
        custom_loads_add_to_imported=True,
        plate_edge_x0_support="fixed",
        plate_edge_x1_load_n_per_m=-1000.0,
    )

    result = fe_solver.run_production_fem(geometry, config)

    assert result.status == "ok"
    assert result.load_resultant["force_n"][0] == pytest.approx(-1000.0)
    assert result.load_resultant["force_n"][2] == pytest.approx(-200.0)
    assert any("added to the imported/generated" in item.lower() for item in result.diagnostics)


def test_custom_nullspace_boundary_balances_free_body_loads():
    geometry = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=True,
        plate_edge_x1_load_n_per_m=-1000.0,
    )

    generated = fe_solver.build_generated_geometry(geometry, config)
    result = fe_solver.run_production_fem(geometry, config)

    assert generated["supports"] == []
    assert result.status == "ok"
    assert result.prestress_summary["constraint_method"] == "transformation_fixed_plus_mpc_nullspace"
    assert result.prestress_summary["constraint_mode"] == "nullspace"
    assert result.prestress_summary["relative_rigid_body_load_imbalance"] > 0.0
    assert any("automatic generalized load balancing" in item.lower() for item in result.diagnostics)


def test_custom_cylinder_lid_support_and_edge_loads_constrain_reference_node_kinematics():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        pressure_pa=100.0,
        include_end_lids=True,
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=False,
        cylinder_lower_support="free",
        cylinder_upper_support="simply supported",
        cylinder_upper_edge_load_n_per_m=-500.0,
    )

    generated = fe_solver.build_generated_geometry(geometry, config)
    result = fe_solver.run_production_fem(geometry, config)

    assert len(generated["supports"]) == 1
    assert generated["supports"][0]["name"] == "custom_cylinder_upper_simply_supported"
    assert generated["supports"][0]["node_ids"] == [generated["rigid_lids"][1]["center_node_id"]]
    assert generated["supports"][0]["constraints"] == {"uz": 0.0, "rx": 0.0, "ry": 0.0}
    assert result.status == "ok"
    assert result.load_resultant["force_n"][2] == pytest.approx(-2.0 * math.pi * 1.0 * 500.0)


def test_custom_cylinder_single_fixed_lid_constrains_reference_rotations():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = fe_solver.LightweightFEMConfig(
        include_end_lids=True,
        custom_load_bc_enabled=True,
        custom_use_nullspace_projection=False,
        cylinder_lower_support="fixed",
        cylinder_upper_support="free",
    )

    generated = fe_solver.build_generated_geometry(geometry, config)

    assert len(generated["supports"]) == 1
    assert generated["supports"][0]["name"] == "custom_cylinder_lower_fixed"
    assert generated["supports"][0]["node_ids"] == [generated["rigid_lids"][0]["center_node_id"]]
    assert generated["supports"][0]["constraints"] == {
        "ux": 0.0,
        "uy": 0.0,
        "uz": 0.0,
        "rx": 0.0,
        "ry": 0.0,
        "rz": 0.0,
    }


def test_cylinder_generated_mesh_forces_edges_at_stiffener_spacing_when_mesh_is_coarse():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 2.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": False,
            "stiffener_spacing_m": 0.5,
        },
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0),
    )

    row_node_ids = generated["plot_grid"][0][:-1]
    stiffener_beams = [beam for beam in generated["beams"] if beam["role"] == "stiffener"]
    stiffener_columns = {beam["node_ids"][0] for beam in stiffener_beams if beam["node_ids"][0] in row_node_ids}

    assert len(row_node_ids) == round(2.0 * math.pi / 0.5)
    assert len(stiffener_columns) == len(row_node_ids)
    assert set(row_node_ids) == stiffener_columns


def test_cylinder_generated_mesh_caps_axial_and_circumferential_size_to_stiffener_spacing():
    spacing = 0.5
    radius = 1.0
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "cylinder",
            "radius_m": radius,
            "length_m": 2.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": False,
            "stiffener_spacing_m": spacing,
        },
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0),
    )

    row_node_ids = generated["plot_grid"][0][:-1]
    axial_values = sorted({node["coords"][2] for node in generated["nodes"]})
    circumferential_segment = 2.0 * math.pi * radius / len(row_node_ids)

    assert circumferential_segment <= spacing + 1.0e-9
    assert max(b - a for a, b in zip(axial_values, axial_values[1:])) <= spacing + 1.0e-9


def test_cylinder_mesh_fidelity_refines_real_mesh_below_member_spacing_cap():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 2.0,
        "length_m": 8.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": 0.5,
        "girder_spacing_m": 4.0,
    }

    coarse = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", include_end_lids=True),
    )
    medium = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="medium", include_end_lids=True),
    )
    fine = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="fine", include_end_lids=True),
    )

    assert len(coarse["shells"]) < len(medium["shells"]) < len(fine["shells"])
    assert len(coarse["plot_grid"]) < len(medium["plot_grid"]) < len(fine["plot_grid"])
    assert len(coarse["plot_grid"][0]) < len(medium["plot_grid"][0]) < len(fine["plot_grid"][0])


def test_cylinder_girder_stations_center_non_multiple_length():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 10.0,
            "thickness_m": 0.012,
            "has_stiffener": False,
            "has_girder": True,
            "girder_spacing_m": 4.0,
        },
        fe_solver.LightweightFEMConfig(mesh_size_m=5.0, include_stiffeners=False, include_girders=True),
    )
    coords = {int(node["id"]): tuple(node["coords"]) for node in generated["nodes"]}
    ring_z_values = sorted({
        round(coords[int(node_id)][2], 6)
        for beam in generated["beams"]
        if beam["role"] == "girder"
        for node_id in beam["node_ids"]
    })

    assert ring_z_values == [1.0, 5.0, 9.0]
    assert all(
        left + right == pytest.approx(10.0)
        for left, right in zip(ring_z_values, reversed(ring_z_values))
    )


def test_cylinder_mesh_size_is_not_capped_by_disabled_members():
    requested = 3.0
    radius = 2.0
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "cylinder",
            "radius_m": radius,
            "length_m": 8.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_spacing_m": 0.5,
            "girder_spacing_m": 0.5,
        },
        fe_solver.LightweightFEMConfig(
            mesh_size_m=requested,
            include_stiffeners=False,
            include_girders=False,
        ),
    )

    row_node_ids = generated["plot_grid"][0][:-1]
    axial_values = sorted({node["coords"][2] for node in generated["nodes"]})
    circumferential_segment = 2.0 * math.pi * radius / len(row_node_ids)

    assert not generated["beams"]
    assert circumferential_segment <= requested + 1.0e-9
    assert max(b - a for a, b in zip(axial_values, axial_values[1:])) <= requested + 1.0e-9
    assert circumferential_segment > 0.5
    assert max(b - a for a, b in zip(axial_values, axial_values[1:])) > 0.5


def test_cylinder_end_lids_are_stress_free_rigid_diaphragms():
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 2.0,
        "thickness_m": 0.012,
        "has_stiffener": False,
        "has_girder": False,
    }
    open_generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", include_end_lids=False),
    )
    lidded_generated = fe_solver.build_generated_geometry(
        geometry,
        fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", include_end_lids=True),
    )

    assert len(lidded_generated["shells"]) == len(open_generated["shells"])
    assert len(lidded_generated["nodes"]) == len(open_generated["nodes"]) + 2
    assert len(lidded_generated["rigid_lids"]) == 2
    bottom_lid, top_lid = lidded_generated["rigid_lids"]
    # Auto boundary adds no lid anchor: balanced free-free cylinders solve via
    # the automatic rigid-body nullspace projection, keeping the symmetric
    # membrane solution (a bottom anchor would double the reported uz peak).
    assert lidded_generated["supports"] == []

    backend = fe_solver.full_backend_api()
    backend_config = backend.AnyStructureFEMConfig(pressure_pa=1000.0, require_idealized_member_beams=False)
    model = backend.build_fe_model_from_generated_geometry(lidded_generated, backend_config)
    load_case = backend.build_symmetric_load_case(None, model, backend_config)
    displacements, solver_info = backend.solve_linear(model, load_case, solver_type="direct", constraint_mode="auto")
    lid_elements = [
        element
        for element in model.mesh.elements.values()
        if element.__class__.__name__ == "RigidLidMPCElement"
    ]

    assert len(lid_elements) == 2
    assert len(load_case.pressure_loads) == len(lidded_generated["shells"])
    assert not ({element.element_id for element in lid_elements} & set(load_case.pressure_loads))
    assert sum(len(element.get_mpc_constraints(model.mesh)) for element in lid_elements) > 0
    assert solver_info["convergence_info"]["status"] == "converged"
    assert solver_info["constraint_method"] == "transformation_fixed_plus_mpc_nullspace"
    assert solver_info["constraint_info"]["num_fixed_dofs"] == 0
    uz_bottom = float(displacements[model.mesh.get_node(bottom_lid["center_node_id"]).dofs[2]])
    uz_top = float(displacements[model.mesh.get_node(top_lid["center_node_id"]).dofs[2]])
    assert uz_top != 0.0
    assert uz_bottom == pytest.approx(-uz_top, rel=1.0e-6)


def test_runtime_solver_records_new_analysis_material_and_load_options():
    result = fe_solver.run_production_fem(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 1.5,
            "thickness_m": 0.02,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=10_000.0,
            pressure_direction="back",
            axial_force_n=25_000.0,
            shell_element_order="S8",
            analysis_type="nonlinear stability",
            buckling_analysis_type="nonlinear limit",
            symmetry_mode="cyclic",
            solver_type="direct",
            stress_percentile=90.0,
            elastic_modulus_pa=200.0e9,
            poisson_ratio=0.29,
            yield_stress_pa=300.0e6,
        ),
    )

    assert result.status == "ok"
    assert result.mesh_info["shell_order"] == "S8"
    assert "max_axial_edge_m" in result.mesh_info
    assert any("Applied balanced axial force" in item for item in result.diagnostics)
    assert any("Generated S8 shell elements" in item for item in result.diagnostics)
    assert any("Ran nonlinear tangent-stability load stepping" in item for item in result.diagnostics)
    assert any("Cyclic symmetry requested" in item for item in result.diagnostics)
    assert "nonlinear_steps" in result.prestress_summary
    assert result.prestress_summary["nonlinear_status"] in {
        "completed",
        "limit_point_detected",
        "near_limit_point",
        "initial_tangent_not_positive",
    }


def test_cylinder_s8_lids_and_eccentric_members_solve_without_mpc_id_collision():
    result = fe_solver.run_production_fem(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 1.5,
            "thickness_m": 0.02,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_spacing_m": 0.8,
            "girder_spacing_m": 0.75,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=1000.0,
            include_end_lids=True,
            shell_element_order="S8",
            member_orientation="radial",
            stiffener_eccentricity_m=0.02,
            girder_eccentricity_m=0.03,
        ),
    )

    assert result.status == "ok"
    assert result.mesh_info["shell_order"] == "S8"
    assert result.mesh_info["rigid_lids"] == 2
    assert any("Applied eccentric beam-shell MPC offsets" in item for item in result.diagnostics)


def test_generated_cylinder_mesh_honors_mesh_size_and_middle_t_ring_girder():
    generated = fe_solver.build_generated_geometry(
        {
            "geometry": "cylinder",
            "radius_m": 2.0,
            "length_m": 8.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_section": {
                "area": 0.150 * 0.010,
                "Iy": 0.010 * 0.150**3 / 12.0,
                "Iz": 0.150 * 0.010**3 / 12.0,
                "J": 0.010 * 0.150**3 / 12.0 + 0.150 * 0.010**3 / 12.0,
            },
            "girder_section": {
                "area": 0.400 * 0.010 + 0.150 * 0.020,
                "Iy": 1.0e-4,
                "Iz": 1.0e-5,
                "J": 1.1e-4,
            },
        },
        fe_solver.LightweightFEMConfig(mesh_size_m=1.0),
    )

    assert len(generated["nodes"]) == 9 * 13
    assert len(generated["shells"]) == 8 * 13
    girder_rows = {
        tuple(generated["nodes"][node_id - 1]["coords"] for node_id in beam["node_ids"])[0][2]
        for beam in generated["beams"]
        if beam["role"] == "girder"
    }
    assert girder_rows == {4.0}
    assert all(beam["section"]["area"] == 0.007 for beam in generated["beams"] if beam["role"] == "girder")


def test_runtime_fem_figure_can_display_cylinder_buckling_modes():
    result = fe_solver.run_production_fem(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 1.5,
            "thickness_m": 0.02,
            "has_stiffener": True,
            "has_girder": True,
        },
        fe_solver.LightweightFEMConfig(pressure_pa=10_000.0, mesh_fidelity="coarse", num_buckling_modes=2, include_end_lids=True),
    )
    app = fe_runtime_solver.example_runtime_app("cylinder")
    snapshot = fe_runtime_solver.active_line_snapshot(app)
    runtime_result = fe_runtime_solver.RuntimeFEMRunResult(
        status=result.status,
        summary={
            **fe_runtime_solver.runtime_geometry_summary(snapshot),
            "solver": result.solver_name,
            "max_displacement_m": result.displacement_max_m,
        },
        buckling_factors=result.buckling_factors,
        stress_percentiles=(("p95", result.stress_p95_pa), ("max", result.stress_max_pa)),
        displacement_scale=result.displacement_max_m,
        visualization=dict(result.visualization),
    )

    figure = fe_runtime_solver.create_runtime_fem_result_figure(snapshot, runtime_result, display_mode="mode:1")

    assert figure.axes[0].get_title().startswith("Buckling mode 1")


def test_anystructure_uses_external_anysolver_backend():
    assert fe_solver.full_backend_available() is True

    backend = fe_solver.full_backend_api()

    assert backend.AnyStructureFEMConfig.__name__ == "AnyStructureFEMConfig"
    assert callable(backend.run_anystructure_fem_mode)
    assert callable(backend.solve_transient_newmark)
    assert backend.PressurePatch.__name__ == "PressurePatch"
    assert callable(backend.apply_imperfection)
    assert backend.StandardImperfection.__name__ == "StandardImperfection"
    assert backend.CapacityWorkflowConfig.__name__ == "CapacityWorkflowConfig"
    assert callable(backend.run_nonlinear_capacity_workflow)
    assert backend.RecoveryConfig.__name__ == "RecoveryConfig"
    assert backend.ResourceConfig.__name__ == "ResourceConfig"
    assert backend.FactorizationCache.__name__ == "FactorizationCache"
    assert callable(backend.solve_free_vibration)


def test_production_solver_can_use_anyintelligent_capacity_workflow_path():
    result = fe_solver.run_production_fem(
        {
            "geometry": "cylinder",
            "radius_m": 1.0,
            "length_m": 1.0,
            "thickness_m": 0.02,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=10_000.0,
            mesh_fidelity="coarse",
            num_buckling_modes=1,
            include_end_lids=True,
            runtime_solver="ANYsolver capacity workflow",
            imperfection_enabled=True,
            imperfection_amplitude_m=0.0001,
            nonlinear_max_load_factor=0.5,
            nonlinear_steps=1,
            capacity_mesh_min_elements_per_half_wave=1,
        ),
    )

    prestress = result.prestress_summary

    assert result.status == "ok"
    assert prestress["runtime_solver"] == "anysolver capacity workflow"
    assert prestress["capacity_workflow_status"] == "completed"
    assert prestress["capacity_workflow_capacity_factor"] == pytest.approx(0.5)
    assert prestress["capacity_workflow_mesh_status"] == "ok"
    assert prestress["buckling_solver_status"] == "ok"
    assert result.buckling_factors and result.buckling_factors[0] > 0.0
    assert any("capacity workflow completed" in item.lower() for item in result.diagnostics)


def test_production_solver_runs_custom_time_domain_response_and_stress_free_imperfection():
    result = fe_solver.run_production_fem(
        {
            "geometry": "flat panel",
            "length_m": 0.6,
            "width_m": 0.3,
            "thickness_m": 0.01,
            "has_stiffener": False,
            "has_girder": False,
        },
        fe_solver.LightweightFEMConfig(
            pressure_pa=100.0,
            mesh_fidelity="coarse",
            num_buckling_modes=1,
            imperfection_enabled=True,
            imperfection_amplitude_m=0.001,
            imperfection_wave_a=1,
            imperfection_wave_b=1,
            custom_load_bc_enabled=True,
            custom_pressure_pa=1000.0,
            custom_time_domain_enabled=True,
            custom_time_domain_duration_s=0.001,
            custom_time_domain_total_time_s=0.002,
            custom_time_domain_dt_s=0.001,
        ),
    )

    prestress = result.prestress_summary

    assert result.status == "ok"
    assert prestress["imperfection_status"] == "applied"
    assert prestress["imperfection_kind"] == "plate half-wave"
    assert prestress["imperfection_max_offset_m"] == pytest.approx(0.001)
    assert prestress["custom_time_domain_status"] == "completed"
    assert prestress["custom_time_domain_selected_shells"] == pytest.approx(result.mesh_info["shells"])
    assert prestress["custom_time_domain_peak_displacement_m"] > 0.0
    assert prestress["custom_time_domain_saved_steps"] >= 2.0
    assert result.visualization["time_domain"]["snapshots"]
    assert result.visualization["time_domain"]["node_histories"]
    assert result.visualization["time_domain"]["element_histories"]
    assert any("Custom time-domain response completed" in item for item in result.diagnostics)


def test_runtime_result_print_and_gui_source_include_custom_time_domain_and_imperfection_inputs():
    result = fe_runtime_solver.RuntimeFEMRunResult(
        status="ok",
        summary={
            "geometry": "flat panel",
            "line": "line1",
            "mesh_fidelity": "coarse",
            "shell_element_order": "S4",
            "boundary_condition": "auto",
            "symmetry_mode": "none",
            "analysis_type": "linear eigenvalue",
            "buckling_analysis_type": "linear eigenvalue",
            "solver_type": "direct",
            "pressure_pa": 0.0,
            "pressure_side": "front",
            "pressure_direction": "front",
            "axial_force_n": 0.0,
            "enforced_displacement_m": 0.0,
            "mesh_size_m": 0.0,
            "top_bottom_moment_nm": 0.0,
            "include_stiffeners": True,
            "include_girders": True,
            "include_end_lids": False,
            "member_orientation": "auto",
            "stiffener_eccentricity_m": 0.0,
            "girder_eccentricity_m": 0.0,
            "material_model": "linear elastic",
            "steel_grade": "S355",
            "steel_thickness_class": "auto",
            "elastic_modulus_pa": 210.0e9,
            "poisson_ratio": 0.3,
            "yield_stress_pa": 355.0e6,
            "stress_percentile": 95.0,
            "nonlinear_max_load_factor": 3.0,
            "nonlinear_steps": 12,
            "nonlinear_layers": 5,
            "nonlinear_max_iterations": 25,
            "deformation_scale": 0.0,
            "custom_load_bc_enabled": False,
            "num_buckling_modes": 1,
            "max_displacement_m": 0.0,
            "imperfection_enabled": True,
            "imperfection_shape": "standard plate/cylinder",
            "imperfection_amplitude_m": 0.001,
            "imperfection_wave_a": 1,
            "imperfection_wave_b": 2,
            "custom_time_domain_enabled": True,
            "custom_pressure_pa": 1000.0,
            "custom_time_domain_duration_s": 0.001,
            "custom_time_domain_total_time_s": 0.002,
            "custom_time_domain_dt_s": 0.001,
            "custom_time_domain_result_interval_s": 0.001,
            "custom_pressure_patch_count": 1,
            "custom_pressure_patch_area_m2": 0.18,
            "custom_edge_segment_count": 2,
            "custom_selected_edge_load_n_per_m": 300.0,
            "custom_time_domain_include_static_load": False,
            "prestress_summary": {
                "imperfection_status": "applied",
                "imperfection_kind": "plate half-wave",
                "imperfection_amplitude_m": 0.001,
                "imperfection_max_offset_m": 0.001,
                "imperfection_waves_a": 1,
                "imperfection_waves_b": 2,
                "custom_time_domain_status": "completed",
                "custom_time_domain_selected_shells": 16,
                "custom_time_domain_peak_displacement_m": 0.0002,
                "custom_time_domain_peak_von_mises_pa": 2.5e6,
            },
        },
    )

    text = fe_runtime_solver.format_runtime_fem_result(result)
    source = (Path(__file__).resolve().parents[1] / "anystruct" / "fem_integration.py").read_text(encoding="utf-8")

    assert "Geometric imperfection input:" in text
    assert "Custom time-domain input:" in text
    assert "Applied geometric imperfection:" in text
    assert "Custom time-domain response:" in text
    assert "self.custom_time_domain_enabled = tk.BooleanVar(value=False)" in source
    assert "self.custom_time_domain_result_interval_s = tk.DoubleVar(value=0.0)" in source
    assert "\"custom_time_domain_result_interval_s\"" in source
    assert "self.imperfection_enabled = tk.BooleanVar(value=False)" in source
    assert "Custom time-domain load" in source
    assert "Imperfections" in source
    assert "Time history graph" in source
    assert "self.probe_node_id = tk.StringVar(value=\"\")" in source
    assert "self.color_min_vis = tk.StringVar(value=\"\")" in source
    assert "self.color_min_scale = ttk.Scale(" in source
    assert "self._probe_click_origin: tuple[int, int] | None = None" in source
    assert "self._selected_probe_node_id: int | None = None" in source
    assert "ttk.Button(probe_bar, text=\"Show mesh\", command=self._show_probe_mesh)" in source
    assert "self._select_probe_from_result_click(self.result_canvas" in source
    assert "def _select_probe_from_result_click(" in source
    assert "def _draw_selected_probe_overlay(" in source
    assert "self._refresh_figure(preserve_view=True)" in source


def test_runtime_fem_module_has_ready_to_run_main_example():
    app = fe_runtime_solver.example_runtime_app()
    snapshot = fe_runtime_solver.active_line_snapshot(app)

    assert snapshot.line_name == "line_example"
    assert snapshot.pressure_pa == 459_639.0
    assert snapshot.domain == "Flat plate, stiffened with girder"
    assert snapshot.is_cylinder is False
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)
    assert summary["length_m"] == pytest.approx(10.0)
    assert summary["width_m"] == pytest.approx(10.0)
    assert summary["thickness_m"] == pytest.approx(0.018)
    assert summary["stiffener_spacing_m"] == pytest.approx(0.75)
    assert summary["girder_spacing_m"] == pytest.approx(3.5)
    assert summary["stiffener_section"]["label"] == "T400x12+250x12"
    assert summary["girder_section"]["label"] == "T800x20+200x30"
    assert app._fem_default_top_bottom_moment_nm == 0.0


def test_runtime_fem_module_keeps_cylinder_standalone_example_option():
    app = fe_runtime_solver.example_runtime_app("cylinder")
    snapshot = fe_runtime_solver.active_line_snapshot(app)

    assert snapshot.line_name == "line_example"
    assert snapshot.pressure_pa == 100_000.0
    assert snapshot.domain == "cylinder"
    assert snapshot.is_cylinder is True
    summary = fe_runtime_solver.runtime_geometry_summary(snapshot)
    assert summary["radius_m"] == 2.0
    assert summary["length_m"] == 8.0
    assert summary["thickness_m"] == 0.012
    assert summary["stiffener_section"]["label"] == "FB150x10"
    assert summary["stiffener_section"]["area"] == 0.0015
    assert summary["girder_section"]["label"] == "T400x10+150x20"


def test_startup_cylinder_example_runs_near_200_mpa_with_buckling_modes():
    app = fe_runtime_solver.example_runtime_app("cylinder")
    snapshot = fe_runtime_solver.active_line_snapshot(app)

    result = fe_runtime_solver.run_runtime_fem(
        snapshot,
        fe_runtime_solver.RuntimeFEMOptions(
            mesh_fidelity="coarse",
            pressure_pa=snapshot.pressure_pa,
            load_scale=1.0,
            include_stiffeners=True,
            include_girders=True,
            num_buckling_modes=5,
            mesh_size_m=0.0,
            top_bottom_moment_nm=app._fem_default_top_bottom_moment_nm,
        ),
    )

    assert result.status == "ok"
    assert 150.0 <= result.stress_percentiles[0][1] / 1.0e6 <= 250.0
    assert len(result.buckling_factors) == 5
    assert result.buckling_factors[0] > 0.1
    assert len(result.visualization["buckling_modes"]) == 5


def test_runtime_fem_file_can_be_run_directly_from_pycharm():
    source = (Path(__file__).resolve().parents[1] / "anystruct" / "fem_integration.py").read_text(encoding="utf-8")

    assert 'if __package__ in (None, ""):' in source
    assert "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))" in source
    assert "self.window.transient(parent)" not in source
    assert "state(\"zoomed\")" in source
    assert 'if __name__ == "__main__":' in source
    assert "root.withdraw()" not in source
    assert "argparse.ArgumentParser" in source
    assert "choices=(\"girder_panel\", \"cylinder\")" in source
    assert "RuntimeFEMWindow(root, example_runtime_app(args.example), use_parent_as_window=True)" in source


def test_active_line_snapshot_rejects_missing_structure():
    app = _FakeApp()
    app._active_line = "line2"

    try:
        fe_runtime_solver.active_line_snapshot(app)
    except ValueError as error:
        assert "active line is not available" in str(error)
    else:
        raise AssertionError("missing active line should fail")


def test_populate_canvas_with_geometry_outer_vs_intermediate_stiffeners():
    class DummyCanvas:
        def __init__(self):
            self.polygons = []
            self.flat_stiffeners = []
            self.flat_girders = []

        def add_polygon(self, points, color=None, outline=None, **kwargs):
            self.polygons.append((points, color, outline))

        def add_rectangular_plate(self, *args, **kwargs):
            pass

        def add_flat_stiffener(self, *args, **kwargs):
            self.flat_stiffeners.append(kwargs)

        def add_flat_girder(self, *args, **kwargs):
            self.flat_girders.append(kwargs)

        def add_cylinder(self, *args, **kwargs):
            pass

        def add_ring_stiffener(self, *args, **kwargs):
            pass

        def add_longitudinal_stiffener(self, *args, **kwargs):
            pass

        def after_idle(self, func):
            pass

        def fit_to_scene(self):
            pass

    class DummyWindow:
        def __init__(self):
            self.snapshot = fe_runtime_solver.active_line_snapshot(fe_runtime_solver.example_runtime_app())

        def _populate_canvas_with_geometry(self, canvas):
            fe_runtime_solver.RuntimeFEMWindow._populate_canvas_with_geometry(self, canvas)

    window = DummyWindow()
    canvas = DummyCanvas()
    window._populate_canvas_with_geometry(canvas)

    # One add_flat_stiffener call per stiffener line, web colour #94a3b8.
    assert len(canvas.flat_stiffeners) > 2
    assert all(call.get("color") == "#94a3b8" for call in canvas.flat_stiffeners)
    y_positions = {round(float(call.get("y", 0.0)), 4) for call in canvas.flat_stiffeners}
    # Distinct y per stiffener: outer and intermediate stiffeners all drawn.
    assert len(y_positions) == len(canvas.flat_stiffeners)
    assert len(y_positions) > 2


def test_populate_canvas_with_geometry_accepts_generated_cylinder_preview():
    class DummyCanvas:
        def __init__(self):
            self.cylinders = []
            self.longitudinal_stiffeners = []
            self.ring_stiffeners = []

        def add_cylinder(self, *args, **kwargs):
            self.cylinders.append((args, kwargs))

        def add_longitudinal_stiffener(self, *args, **kwargs):
            self.longitudinal_stiffeners.append((args, kwargs))

        def add_ring_stiffener(self, *args, **kwargs):
            self.ring_stiffeners.append((args, kwargs))

        def after_idle(self, func):
            pass

        def fit_to_scene(self):
            pass

    class DummyWindow:
        def __init__(self):
            app = fe_runtime_solver.example_runtime_app("cylinder")
            self.snapshot = fe_runtime_solver.active_line_snapshot(app)

        def _populate_canvas_with_geometry(self, canvas):
            fe_runtime_solver.RuntimeFEMWindow._populate_canvas_with_geometry(self, canvas)

    window = DummyWindow()
    canvas = DummyCanvas()
    window._populate_canvas_with_geometry(canvas)

    assert len(canvas.cylinders) == 1
    assert canvas.cylinders[0][1]["back_color"] == "#8b5e3c"
    assert canvas.cylinders[0][1]["show_backfaces"] is True
    assert len(canvas.longitudinal_stiffeners) > 0
    assert len(canvas.ring_stiffeners) > 0


def test_point_refinement_marker_drawn_on_cylinder_surface():
    """The picked point-refinement centre is drawn as a bold overlay crosshair
    (+ extent circle) sitting on the cylinder surface, from the live inputs."""
    import types

    class Var:
        def __init__(self, v):
            self._v = v

        def get(self):
            return self._v

    class RecordingCanvas:
        def __init__(self):
            self.lines = []

        def add_line(self, a, b, **kwargs):
            self.lines.append((a, b, kwargs))

    window = types.SimpleNamespace()
    window.snapshot = types.SimpleNamespace(is_cylinder=True)
    window.point_refinement_enabled = Var(True)
    window.point_refinement_x_m = Var(6.0)
    window.point_refinement_y_m = Var(10.3)
    window.point_refinement_extent_m = Var(0.25)
    for name in ("_point_refinement_marker_xyz", "_draw_point_refinement_marker", "_draw_point_refinement_circle"):
        setattr(window, name, types.MethodType(getattr(fe_runtime_solver.RuntimeFEMWindow, name), window))

    geometry = {"radius_m": 2.0, "length_m": 10.3}
    centre, extent = window._point_refinement_marker_xyz(geometry)
    assert extent == pytest.approx(0.25)
    assert math.hypot(centre.x, centre.y) == pytest.approx(2.0, abs=1e-6)  # on surface
    assert centre.z == pytest.approx(6.0)

    canvas = RecordingCanvas()
    window._draw_point_refinement_marker(canvas, geometry, draw_circle=True)
    star = [ln for ln in canvas.lines if ln[2].get("width") == 3]
    circle = [ln for ln in canvas.lines if ln[2].get("width") == 2]
    assert len(star) == 3, "three-axis crosshair"
    assert len(circle) >= 40, "extent circle sampled"
    assert all(ln[2].get("draw_overlay") for ln in canvas.lines), "always-visible overlay"
    assert all(math.hypot(ln[0].x, ln[0].y) == pytest.approx(2.0, abs=0.05) for ln in circle)

    # Disabled point refinement draws nothing.
    window.point_refinement_enabled = Var(False)
    empty = RecordingCanvas()
    window._draw_point_refinement_marker(empty, geometry, draw_circle=True)
    assert empty.lines == []


def test_crisp_canvas_alpha_snaps_near_opaque_values_to_solid():
    assert fe_runtime_solver._crisp_canvas_alpha("1.0") == 1.0
    assert fe_runtime_solver._crisp_canvas_alpha("0.99") == 1.0
    assert fe_runtime_solver._crisp_canvas_alpha("0.95") == pytest.approx(0.95)


def test_runtime_status_updates_do_not_replace_completed_run_results():
    class DummyText:
        def __init__(self):
            self.value = ""

        def delete(self, *_args):
            self.value = ""

        def insert(self, _index, text):
            self.value += str(text)

    class DummyWindow:
        result_text = DummyText()
        _last_run_result_status_text = "RESULTS\nStatus: ok\nBuckling LF: 1.23"

    fe_runtime_solver.RuntimeFEMWindow._write_status(
        DummyWindow(),
        "3D view set to fit.",
        keep_run_results=True,
    )

    assert "RESULTS\nStatus: ok\nBuckling LF: 1.23" in DummyWindow.result_text.value
    assert "Run status update:\n3D view set to fit." in DummyWindow.result_text.value


def test_collision_damage_criterion_reaches_backend_config():
    """The GUI damage-criterion selection must reach PlasticImpactDamageConfig.

    Regression: the criterion was previously dropped in
    _collision_plastic_damage_config, silently running 'fixed' regardless of
    the dropdown."""
    from anysolver import runtime as fe_solver

    for criterion in ("fixed", "mesh_scaled_gl", "rtcl"):
        config = fe_solver.LightweightFEMConfig(
            collision_enabled=True,
            collision_material_nonlinear_enabled=True,
            collision_damage_enabled=True,
            collision_damage_criterion=criterion,
            collision_plastic_damage_threshold=0.05,
        )
        damage = fe_solver._collision_plastic_damage_config(config)
        assert damage is not None
        assert damage.criterion == criterion

    # Unknown strings fall back to 'fixed' instead of raising.
    config = fe_solver.LightweightFEMConfig(
        collision_enabled=True,
        collision_material_nonlinear_enabled=True,
        collision_damage_enabled=True,
        collision_damage_criterion="bogus",
    )
    assert fe_solver._collision_plastic_damage_config(config).criterion == "fixed"

    # RTCL is the app default: stress-state aware and the most stable erosion.
    assert fe_solver.LightweightFEMConfig().collision_damage_criterion == "rtcl"
    assert fe_runtime_solver.RuntimeFEMOptions().collision_damage_criterion == "rtcl"


def test_post_buckling_options_force_arc_length_with_automatic_stop():
    """Post-buckling enable forces arc-length control, activates the nonlinear
    static path, and configures the automatic stopping criteria."""
    from anysolver import runtime as fe_solver

    config = fe_solver.LightweightFEMConfig(
        post_buckling_enabled=True,
        post_buckling_stop_load_fraction=0.4,
        post_buckling_max_displacement_m=0.08,
        nonlinear_solution_control="newton force control",  # overridden
        analysis_type="linear eigenvalue",                   # overridden
        nonlinear_steps=10,
        nonlinear_max_load_factor=2.0,
    )
    assert fe_solver._nonlinear_solution_control(config) == "arc length"
    assert fe_solver._wants_static_nonlinear_analysis(config) is True
    control = fe_solver._arc_length_control(config)
    assert control is not None
    assert control.post_peak_load_fraction == pytest.approx(0.4)
    assert control.max_translation == pytest.approx(0.08)
    assert control.stop_after_peak_steps >= 10_000
    assert control.max_steps >= 100

    # Disabled: plain arc-length keeps the short limit-point confirmation.
    off = fe_solver.LightweightFEMConfig(nonlinear_solution_control="arc length")
    plain = fe_solver._arc_length_control(off)
    assert plain.post_peak_load_fraction is None
    assert plain.max_translation is None
    assert plain.stop_after_peak_steps == 4
    assert fe_solver.LightweightFEMConfig().post_buckling_enabled is False


def test_live_graph_routing_and_series_accumulation():
    """Headless checks of the live-graph state machine: run-kind selection,
    collision/equilibrium feeds, and the buckling fallback finalize."""
    import types

    window = types.SimpleNamespace()
    window._live_graph_axis = None
    window._live_graph_canvas = None
    window._live_graph_figure = None
    window._live_graph_state = {"kind": "idle", "series": {}, "last_draw": 0.0}
    window._run_status_history = []
    for name in ("_live_graph_kind_for_options", "_live_graph_reset", "_live_graph_append",
                 "_live_graph_redraw", "_live_graph_finalize", "_apply_nonlinear_static_step"):
        setattr(window, name, types.MethodType(getattr(fe_runtime_solver.RuntimeFEMWindow, name), window))

    # Run-kind selection.
    kind = window._live_graph_kind_for_options(types.SimpleNamespace(collision_enabled=True))
    assert kind == "collision"
    kind = window._live_graph_kind_for_options(types.SimpleNamespace(
        collision_enabled=False, post_buckling_enabled=True))
    assert kind == "equilibrium"
    kind = window._live_graph_kind_for_options(types.SimpleNamespace(
        collision_enabled=False, post_buckling_enabled=False,
        analysis_type="geom. + material nonlinear static", runtime_solver="stepwise",
        nonlinear_solution_control="newton force control"))
    assert kind == "equilibrium"
    kind = window._live_graph_kind_for_options(types.SimpleNamespace(
        collision_enabled=False, post_buckling_enabled=False,
        analysis_type="linear eigenvalue", runtime_solver="stepwise",
        nonlinear_solution_control="newton force control", custom_time_domain_enabled=False))
    assert kind == "generic"

    # Equilibrium feed from the structured solver payloads.
    window._live_graph_reset("equilibrium")
    for step, (lam, disp) in enumerate(((0.2, 0.001), (0.35, 0.004), (0.30, 0.009)), start=1):
        window._apply_nonlinear_static_step({
            "type": "nonlinear_static_step", "control": "arc length", "step_index": step,
            "load_factor": lam, "peak_load_factor": 0.35, "max_translation": disp,
            "max_equivalent_plastic_strain": 0.0,
        })
    xs, ys = window._live_graph_state["series"]["load factor"]
    assert ys == [0.2, 0.35, 0.30], "descending branch recorded"
    assert xs == [1.0, 4.0, 9.0], "x-axis is max displacement in mm"
    assert window._run_status_history[-1].startswith("Arc-length step 3")

    # Buckling fallback: empty series + factors -> mode/factor markers.
    window._live_graph_reset("generic")
    result = types.SimpleNamespace(buckling_factors=(1.8, 2.4, 3.1))
    window._live_graph_finalize(result)
    assert window._live_graph_state["kind"] == "buckling"
    xs, ys = window._live_graph_state["series"]["load factor"]
    assert xs == [1.0, 2.0, 3.0]
    assert ys == [1.8, 2.4, 3.1]


def test_post_buckling_forces_material_nonlinearity_and_curve():
    """Post-buckling must run FULLY nonlinear: the DNV material curve is
    applied even when the material-model dropdown is left at linear elastic
    (an elastic post-buckling branch is non-physical for steel design)."""
    from anysolver import runtime as fe_solver

    config = fe_solver.LightweightFEMConfig(
        post_buckling_enabled=True,
        material_model="linear elastic",
        analysis_type="linear eigenvalue",
        steel_grade="S355",
    )
    assert fe_solver._wants_material_nonlinear_analysis(config) is True
    curve, properties = fe_solver._nonlinear_curve_payload(config, {"thickness_m": 0.012})
    assert curve is not None, "DNV hardening curve must reach the model"
    assert str(properties.get("grade", "")) == "S355"

    # Without post-buckling the linear-elastic selection stays elastic.
    plain = fe_solver.LightweightFEMConfig(material_model="linear elastic")
    assert fe_solver._wants_material_nonlinear_analysis(plain) is False
    assert fe_solver._nonlinear_curve_payload(plain, {"thickness_m": 0.012})[0] is None


def test_post_buckling_field_sync_sets_dependent_inputs():
    """Enabling post-buckling mirrors the executed solve mode in the GUI
    fields: analysis, material model and NL control are set to match."""
    import types

    class Var:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

        def set(self, value):
            self._value = value

    window = types.SimpleNamespace()
    window.post_buckling_enabled = Var(True)
    window.analysis_type = Var("linear eigenvalue")
    window.material_model = Var("linear elastic")
    window.nonlinear_solution_control = Var("newton force control")
    window._choice_key = fe_runtime_solver.RuntimeFEMWindow._choice_key
    window._apply_post_buckling_field_sync = types.MethodType(
        fe_runtime_solver.RuntimeFEMWindow._apply_post_buckling_field_sync, window)

    window._apply_post_buckling_field_sync()
    assert window.analysis_type.get() == "geom. + material nonlinear static"
    assert window.material_model.get() == "DNV-RP-C208 steel"
    assert window.nonlinear_solution_control.get() == "arc length"

    # Disabled: nothing is touched.
    window.post_buckling_enabled = Var(False)
    window.analysis_type = Var("linear eigenvalue")
    window._apply_post_buckling_field_sync()
    assert window.analysis_type.get() == "linear eigenvalue"


def test_live_graph_axis_split_moves_large_series_to_secondary_axis():
    """Mixed magnitudes: the large series (contact force) moves to the right
    axis so small ones (displacement, strain) stay readable, while similar
    magnitudes keep a single axis."""
    split = fe_runtime_solver.RuntimeFEMWindow._live_graph_axis_split

    mixed = {
        "max displacement [mm]": ([0.0, 1.0], [2.0, 8.0]),
        "contact force [kN]": ([0.0, 1.0], [400.0, 980.0]),
        "plastic strain [%]": ([0.0, 1.0], [0.1, 1.5]),
    }
    assert split(mixed) == {"contact force [kN]"}

    similar = {
        "load factor": ([0.0, 1.0], [0.5, 1.6]),
        "plastic strain [%]": ([0.0, 1.0], [0.2, 0.9]),
    }
    assert split(similar) == set()

    assert split({"only": ([0.0], [5.0])}) == set()
    assert split({}) == set()


def test_nonlinear_collision_snapshots_keep_refined_skin_surfaces():
    """Regression: nonlinear collision snapshots hid the entire refined skin
    because per-element damage-state records (no timestamp) were fed to the
    per-time deletion filter -- the GUI then fell back to the coarse plot
    grid, which only looked right for graded/uniform meshes."""
    from anysolver import runtime as fe_solver

    flat = {
        "geometry": "flat panel",
        "length_m": 2.0,
        "width_m": 1.5,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": False,
        "stiffener_spacing_m": 0.75,
    }
    config = fe_solver.LightweightFEMConfig(
        mesh_fidelity="coarse",
        boundary_condition="clamped",
        collision_enabled=True,
        collision_adaptive_mesh_enabled=True,
        collision_adaptive_fine_size_m=0.06,
        collision_adaptive_extent_m=0.3,
        collision_radius_m=0.15,
        collision_start_x_m=1.0,
        collision_start_y_m=0.75,
        collision_start_z_m=0.3,
        collision_vector_x=0.0,
        collision_vector_y=0.0,
        collision_vector_z=-1.0,
        collision_mass_kg=200.0,
        collision_speed_mps=3.0,
        collision_material_nonlinear_enabled=True,
        detail_transition_style="local patch (quad+tri)",
    )
    generated = fe_solver.build_generated_geometry(flat, config)
    skin_count = sum(1 for shell in generated.get("shells", []) if "role" not in shell)
    assert (generated.get("adaptive_mesh") or {}).get("transition") == "local patch (quad+tri)"

    result = fe_solver.run_production_fem(flat, config)
    visualization = result.visualization or {}
    snapshots = tuple((visualization.get("time_domain") or {}).get("snapshots") or ())
    assert snapshots, result.status
    for snapshot in (snapshots[0], snapshots[-1]):
        surfaces = tuple((snapshot or {}).get("skin_shell_surfaces") or ())
        deleted = len(tuple((snapshot or {}).get("hidden_deleted_element_ids", ()) or ()))
        assert len(surfaces) + deleted == skin_count, (len(surfaces), deleted, skin_count)
        assert len(surfaces) > 0.9 * skin_count, "refined skin must stay visible in snapshots"


def test_collision_penalty_scale_multiplies_auto_penalty():
    """collision_penalty_scale must scale the auto contact penalty so the
    scout preconditioner can carry a convergence-friendly stiffness into the
    real run.  A manual penalty ignores the scale."""
    from anysolver import runtime as fs

    cylinder = {
        "geometry": "cylinder", "radius_m": 1.0, "length_m": 6.0, "thickness_m": 0.02,
        "has_stiffener": False, "has_girder": False,
    }
    base = dict(
        mesh_fidelity="coarse", boundary_condition="auto",
        cylinder_lower_support="fixed", cylinder_upper_support="fixed",
        include_end_lids=True,
        collision_enabled=True, collision_radius_m=0.3, collision_mass_kg=500.0,
        collision_speed_mps=2.0, collision_start_x_m=-1.31, collision_start_y_m=0.0,
        collision_start_z_m=3.0, collision_vector_x=1.0, collision_vector_y=0.0, collision_vector_z=0.0,
        collision_time_mode="manual", collision_total_time_s=0.004, collision_dt_s=5.0e-4,
    )
    full = fs.run_production_fem(cylinder, fs.LightweightFEMConfig(**base))
    half = fs.run_production_fem(cylinder, fs.LightweightFEMConfig(**base, collision_penalty_scale=0.5))
    p_full = float(full.prestress_summary.get("collision_contact_penalty_stiffness_n_per_m", 0.0))
    p_half = float(half.prestress_summary.get("collision_contact_penalty_stiffness_n_per_m", 0.0))
    assert p_full > 0.0 and p_half > 0.0
    assert p_half == pytest.approx(0.5 * p_full, rel=1.0e-6)
    assert "scaled" in str(half.prestress_summary.get("collision_contact_penalty_basis", ""))

    # Manual penalty overrides the scale entirely.
    manual = fs.run_production_fem(
        cylinder,
        fs.LightweightFEMConfig(**base, collision_penalty_stiffness_n_per_m=1.0e9, collision_penalty_scale=0.5),
    )
    assert float(manual.prestress_summary.get("collision_contact_penalty_stiffness_n_per_m", 0.0)) == pytest.approx(1.0e9)


def test_collision_penalty_capped_at_shell_contact_stiffness():
    """The auto contact penalty must be capped at a multiple of the shell
    contact-stiffness scale E*t so heavy/fast impacts stay well conditioned.
    Root cause of 'nonlinear iteration failed' on high-energy runs: the
    energy/dt-based auto penalty ignored the shell stiffness and could be
    ~10x E*t, diverging the staggered contact iteration."""
    from anysolver import runtime as fs

    E = 210.0e9
    t = 0.030
    et_scale = E * t
    cap = fs._COLLISION_PENALTY_STRUCTURAL_FACTOR * et_scale

    # Heavy, fast sphere: the uncapped desired penalty is far above E*t.
    config = fs.LightweightFEMConfig(
        collision_enabled=True, collision_radius_m=1.0, collision_mass_kg=1.0e6,
        collision_speed_mps=5.0, collision_target_penetration_fraction=0.01,
        elastic_modulus_pa=E,
    )
    heavy = fs._collision_dynamic_penalty(config, dt=1.0e-4, contact_stiffness_scale=et_scale)
    assert heavy["penalty_stiffness"] == pytest.approx(cap, rel=1.0e-9)
    assert heavy["basis"] == "dynamic_auto_structural_cap"
    # Desired (uncapped) is far stiffer than the cap, confirming the cap binds.
    assert float(heavy["desired_penalty_stiffness"]) > 3.0 * cap

    # A light impact stays below the cap: the ceiling does not bind and the
    # penalty is unchanged from the energy-based value.
    light = fs.LightweightFEMConfig(
        collision_enabled=True, collision_radius_m=0.15, collision_mass_kg=100.0,
        collision_speed_mps=3.0, elastic_modulus_pa=E,
    )
    light_info = fs._collision_dynamic_penalty(light, dt=1.0e-4, contact_stiffness_scale=et_scale)
    assert light_info["penalty_stiffness"] < cap
    assert light_info["basis"] == "dynamic_auto"


def test_collision_contact_stiffness_scale_uses_thinnest_skin():
    """E*t is taken from the thinnest (most compliant) skin shell."""
    from anysolver import runtime as fs

    config = fs.LightweightFEMConfig(elastic_modulus_pa=200.0e9)
    # Generated skin shells store the plate thickness under the "thickness"
    # key (NOT "thickness_m"); reading the wrong key silently disabled the cap.
    generated = {
        "shells": [
            {"id": 1, "node_ids": [1, 2, 3, 4], "thickness": 0.03},
            {"id": 2, "node_ids": [2, 3, 5, 6], "thickness": 0.012},
            {"id": 9, "node_ids": [1, 2, 7], "role": "stiffener", "thickness": 0.001},
        ]
    }
    scale = fs._collision_contact_stiffness_scale(generated, config)
    assert scale == pytest.approx(200.0e9 * 0.012)  # thinnest skin, member ignored


def test_collision_auto_precondition_softens_penalty_further():
    """The opt-in extra-conservative mode multiplies the (capped) penalty by
    the extra softening factor."""
    from anysolver import runtime as fs

    cylinder = {
        "geometry": "cylinder", "radius_m": 1.0, "length_m": 6.0, "thickness_m": 0.02,
        "has_stiffener": False, "has_girder": False,
    }
    base = dict(
        mesh_fidelity="coarse", boundary_condition="auto",
        cylinder_lower_support="fixed", cylinder_upper_support="fixed", include_end_lids=True,
        collision_enabled=True, collision_radius_m=0.3, collision_mass_kg=5.0e5,
        collision_speed_mps=6.0, collision_start_x_m=-1.31, collision_start_y_m=0.0,
        collision_start_z_m=3.0, collision_vector_x=1.0, collision_vector_y=0.0, collision_vector_z=0.0,
        collision_time_mode="manual", collision_total_time_s=0.004, collision_dt_s=5.0e-4,
    )
    plain = fs.run_production_fem(cylinder, fs.LightweightFEMConfig(**base))
    conservative = fs.run_production_fem(cylinder, fs.LightweightFEMConfig(**base, collision_auto_precondition=True))
    p_plain = float(plain.prestress_summary.get("collision_contact_penalty_stiffness_n_per_m", 0.0))
    p_cons = float(conservative.prestress_summary.get("collision_contact_penalty_stiffness_n_per_m", 0.0))
    assert p_plain > 0.0
    assert p_cons == pytest.approx(fs._COLLISION_PRECONDITION_EXTRA_SCALE * p_plain, rel=1.0e-6)


def test_boundary_dof_constraint_map_parsing():
    """The whole-boundary / selected-edge per-DOF specs parse to {dof: value},
    accepting plain numbers, on/value dicts and bools; enforced rotations kept."""
    from anysolver import runtime as fs
    import json

    parsed = fs._dof_constraint_map(json.dumps({
        "ux": 0.001, "uz": 0.0, "rx": {"on": True, "value": 0.01},
        "ry": {"on": False, "value": 5.0}, "rz": False, "bogus": 1.0,
    }))
    assert parsed == {"ux": 0.001, "uz": 0.0, "rx": 0.01}
    assert fs._dof_constraint_map("") == {}
    assert fs._dof_constraint_map("not json") == {}


def test_whole_boundary_per_dof_supports_and_free_boundary():
    """Whole-boundary DOF grid constrains all boundary nodes with enforced
    values; auto-off + empty grid gives a free boundary; default is unchanged."""
    from anysolver import runtime as fs
    import json

    flat = {"geometry": "flat panel", "length_m": 4.0, "width_m": 3.0, "thickness_m": 0.012,
            "has_stiffener": False, "has_girder": False}

    default = fs.build_generated_geometry(flat, fs.LightweightFEMConfig(mesh_fidelity="coarse"))
    assert any("simply_supported" in s["name"] for s in default["supports"]), "auto default preserved"

    enforced = fs.build_generated_geometry(flat, fs.LightweightFEMConfig(
        mesh_fidelity="coarse",
        boundary_constraint_json=json.dumps({"ux": 0.002, "uz": 0.0, "ry": 0.01})))
    wb = [s for s in enforced["supports"] if s["name"] == "whole_boundary_dof_constraint"]
    assert len(wb) == 1
    assert wb[0]["constraints"] == {"ux": 0.002, "uz": 0.0, "ry": 0.01}  # enforced disp + rotation
    assert len(wb[0]["node_ids"]) > 4
    assert not any("simply_supported" in s["name"] for s in enforced["supports"]), "grid overrides auto"

    free = fs.build_generated_geometry(flat, fs.LightweightFEMConfig(
        mesh_fidelity="coarse", boundary_auto_supports=False))
    assert free["supports"] == []


def test_selected_edge_per_dof_segment_additive():
    """A selected-edge segment carries per-DOF constraints (incl. enforced
    rotation) and is additive on top of the automatic whole-boundary supports."""
    from anysolver import runtime as fs
    import json

    flat = {"geometry": "flat panel", "length_m": 4.0, "width_m": 3.0, "thickness_m": 0.012,
            "has_stiffener": False, "has_girder": False}
    seg = [{"varying_axis": "a", "fixed_coordinate": 0.0, "start_coordinate": 0.0,
            "end_coordinate": 4.0, "constraints": {"uz": 0.0, "ry": 0.02}}]
    generated = fs.build_generated_geometry(flat, fs.LightweightFEMConfig(
        mesh_fidelity="coarse", boundary_auto_supports=True,
        custom_bc_segments_json=json.dumps(seg)))
    edge = [s for s in generated["supports"] if s["name"].startswith("custom_edge_bc")]
    assert len(edge) == 1
    assert edge[0]["constraints"] == {"uz": 0.0, "ry": 0.02}
    assert any("simply_supported" in s["name"] for s in generated["supports"]), "auto still applied"

    # Collision support check accepts a selected-edge segment as valid restraint.
    cfg = fs.LightweightFEMConfig(boundary_auto_supports=True, custom_bc_segments_json=json.dumps(seg))
    assert fs._runtime_collision_has_fixed_support(cfg, flat) is True


def test_selected_edge_overrides_whole_boundary_on_shared_dof():
    """When a selected-edge segment enforces a DOF that the whole-boundary
    grid also constrains, the edge value wins: the whole-boundary support
    splits so overlapping nodes drop that DOF (no conflicting-prescribed
    error) and the run completes."""
    from anysolver import runtime as fs
    import json

    flat = {"geometry": "flat panel", "length_m": 4.0, "width_m": 3.0, "thickness_m": 0.012,
            "has_stiffener": False, "has_girder": False}
    seg = [{"varying_axis": "a", "fixed_coordinate": 0.0, "start_coordinate": 0.0,
            "end_coordinate": 4.0, "constraints": {"ry": 0.05}}]
    cfg = fs.LightweightFEMConfig(
        mesh_fidelity="coarse", pressure_pa=50000.0,
        boundary_constraint_json=json.dumps({d: 0.0 for d in ("ux", "uy", "uz", "rx", "ry", "rz")}),
        custom_bc_segments_json=json.dumps(seg))
    generated = fs.build_generated_geometry(flat, cfg)
    whole = [s for s in generated["supports"] if s["name"].startswith("whole_boundary")]
    edge = [s for s in generated["supports"] if s["name"].startswith("custom_edge_bc")]
    assert edge and edge[0]["constraints"] == {"ry": 0.05}
    # The edge nodes' whole-boundary group must not re-prescribe ry.
    edge_nodes = set(edge[0]["node_ids"])
    for support in whole:
        if edge_nodes.intersection(support["node_ids"]):
            assert "ry" not in support["constraints"], "edge must override whole-boundary ry"
    # No node carries ry from both an edge and a whole-boundary group.
    result = fs.run_production_fem(flat, cfg)
    assert result.status == "ok", result.status


def test_boundary_edge_constraints_per_edge_and_legacy():
    """Per-edge whole-boundary schema {edge: {dof: value}} parses per edge;
    the legacy flat {dof: value} schema maps to the 'all' edge."""
    from anysolver import runtime as fs
    import json

    per_edge = fs._boundary_edge_constraints(fs.LightweightFEMConfig(
        boundary_constraint_json=json.dumps({"x0": {"ux": 0.0, "uz": 0.001}, "y1": {"ry": 0.01}})))
    assert per_edge == {"x0": {"ux": 0.0, "uz": 0.001}, "y1": {"ry": 0.01}}

    legacy = fs._boundary_edge_constraints(fs.LightweightFEMConfig(
        boundary_constraint_json=json.dumps({"uz": 0.0, "ux": 0.0})))
    assert legacy == {"all": {"uz": 0.0, "ux": 0.0}}

    assert fs._boundary_edge_constraints(fs.LightweightFEMConfig(boundary_constraint_json="{}")) == {}


def test_flat_per_edge_supports_target_correct_edges():
    """Each named flat edge receives only its own DOFs on its own nodes; the
    shared corner node takes the union of both edges' DOFs."""
    from anysolver import runtime as fs
    import json

    flat = {"geometry": "flat panel", "length_m": 4.0, "width_m": 3.0, "thickness_m": 0.012,
            "has_stiffener": False, "has_girder": False}
    generated = fs.build_generated_geometry(flat, fs.LightweightFEMConfig(
        mesh_fidelity="coarse",
        boundary_constraint_json=json.dumps({"x0": {"ux": 0.0, "uy": 0.0, "uz": 0.0}, "y1": {"ry": 0.01}})))
    coords = {int(n["id"]): n["coords"] for n in generated["nodes"]}
    whole = [s for s in generated["supports"] if s["name"].startswith("whole_boundary")]
    # Nodes carrying ry must lie on y = 3 (the y1 edge); nodes with the clamp
    # triple must lie on x = 0 (the x0 edge).
    for s in whole:
        if set(s["constraints"]) == {"ry"}:
            assert all(abs(float(coords[i][1]) - 3.0) < 1e-9 for i in s["node_ids"])
        if {"ux", "uy", "uz"}.issubset(set(s["constraints"])):
            assert all(abs(float(coords[i][0])) < 1e-9 for i in s["node_ids"])


def test_cylinder_bottom_only_constraint_leaves_top_free():
    """A 'lower' whole-boundary spec constrains only the z=0 ring; the top
    ring stays free."""
    from anysolver import runtime as fs
    import json

    cyl = {"geometry": "cylinder", "radius_m": 2.0, "length_m": 8.0, "thickness_m": 0.012,
           "has_stiffener": False, "has_girder": False}
    generated = fs.build_generated_geometry(cyl, fs.LightweightFEMConfig(
        mesh_fidelity="coarse", include_end_lids=False,
        boundary_constraint_json=json.dumps({"lower": {d: 0.0 for d in ("ux", "uy", "uz")}})))
    coords = {int(n["id"]): n["coords"] for n in generated["nodes"]}
    whole = [s for s in generated["supports"] if s["name"].startswith("whole_boundary")]
    constrained = {i for s in whole for i in s["node_ids"]}
    assert constrained, "bottom ring must be constrained"
    assert all(abs(float(coords[i][2])) < 1e-6 for i in constrained), "only the z=0 ring"


def test_boundary_edge_grid_persist_and_collect():
    """Headless: editing the DOF grid under one edge radio, switching, and
    editing another persists both into the per-edge JSON payload."""
    import types
    import json as _json

    win = types.SimpleNamespace()
    win._bc_dof_names = ("ux", "uy", "uz", "rx", "ry", "rz")
    win._boundary_edge_specs = {}
    win._boundary_active_edge = "x0"

    class Var:
        def __init__(self, v):
            self._v = v

        def get(self):
            return self._v

        def set(self, v):
            self._v = v

    win.boundary_dof_on = {d: Var(False) for d in win._bc_dof_names}
    win.boundary_dof_value = {d: Var(0.0) for d in win._bc_dof_names}
    win.boundary_edge_choice = Var("x0")
    for name in ("_persist_boundary_edge", "_load_boundary_edge", "_on_boundary_edge_change",
                 "_collect_boundary_constraint_json"):
        setattr(win, name, types.MethodType(getattr(fe_runtime_solver.RuntimeFEMWindow, name), win))

    # Edit x0: clamp uz.
    win.boundary_dof_on["uz"].set(True)
    # Switch to y1 and enforce ry.
    win.boundary_edge_choice.set("y1")
    win._on_boundary_edge_change()
    assert win.boundary_dof_on["uz"].get() is False, "grid reloaded blank for y1"
    win.boundary_dof_on["ry"].set(True)
    win.boundary_dof_value["ry"].set(0.02)

    payload = _json.loads(win._collect_boundary_constraint_json())
    assert payload == {"x0": {"uz": 0.0}, "y1": {"ry": 0.02}}
