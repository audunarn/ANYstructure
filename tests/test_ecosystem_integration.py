from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from anystruct import ecosystem_gui, fe_plate_fields, fem_integration


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class _Var:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Messages:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def showerror(self, *args, **kwargs):
        self.errors.append((args, kwargs))

    def showwarning(self, *args, **kwargs):
        self.warnings.append((args, kwargs))


def _material_spec(
    *,
    name="Test S355",
    symmetry="isotropic",
    elastic_modulus=205.0e9,
    poisson_ratio=0.29,
    yield_stress=360.0e6,
    hardening=None,
):
    constants = {
        "elastic_modulus": elastic_modulus,
        "poisson_ratio": poisson_ratio,
    }
    if symmetry == "orthotropic":
        constants = {
            "elastic_modulus_1": 150.0e9,
            "elastic_modulus_2": 10.0e9,
            "elastic_modulus_3": 8.0e9,
        }
    return SimpleNamespace(
        name=name,
        symmetry=symmetry,
        constants=constants,
        yield_stress=yield_stress,
        hardening=hardening,
    )


def test_isotropic_material_selection_maps_si_to_gui_units_and_dnv_controls():
    selected = ecosystem_gui.isotropic_material_selection(
        _material_spec(
            hardening={"kind": "dnv_c208", "grade": "S355", "thickness": 0.025}
        )
    )

    assert selected.name == "Test S355"
    assert selected.elastic_modulus_gpa == pytest.approx(205.0)
    assert selected.poisson_ratio == pytest.approx(0.29)
    assert selected.yield_stress_mpa == pytest.approx(360.0)
    assert selected.material_model == "DNV-RP-C208 steel"
    assert selected.steel_grade == "S355"
    assert selected.steel_thickness_class == "16 < t <= 40"


def test_isotropic_material_selection_rejects_orthotropic_without_reduction():
    with pytest.raises(ecosystem_gui.UnsupportedMaterialSelection, match="isotropic materials only"):
        ecosystem_gui.isotropic_material_selection(_material_spec(symmetry="orthotropic"))


@pytest.mark.gui
def test_main_application_material_callback_updates_flat_and_shell_scalars(monkeypatch):
    # Importing the legacy monolithic desktop module loads Tk, Matplotlib and
    # scikit-learn.  Keep that import inside the explicit GUI qualification so
    # ordinary headless collection stays bounded.
    from anystruct import main_application

    messages = _Messages()
    monkeypatch.setattr(main_application, "messagebox", messages)
    app = SimpleNamespace(
        _parent=object(),
        _new_material_name=_Var("old"),
        _last_isotropic_material_name="old",
        _new_material=_Var(),
        _new_shell_yield=_Var(),
        _new_shell_e_module=_Var(),
        _new_shell_poisson=_Var(),
    )

    assert main_application.Application._apply_material_spec(app, _material_spec()) is True
    assert app._new_material_name.get() == "Test S355"
    assert app._new_material.get() == pytest.approx(360.0)
    assert app._new_shell_yield.get() == pytest.approx(360.0)
    assert app._new_shell_e_module.get() == pytest.approx(205.0e9)
    assert app._new_shell_poisson.get() == pytest.approx(0.29)
    assert not messages.errors


@pytest.mark.gui
def test_main_application_material_callback_rejects_orthotropic(monkeypatch):
    from anystruct import main_application

    messages = _Messages()
    monkeypatch.setattr(main_application, "messagebox", messages)
    app = SimpleNamespace(
        _parent=object(),
        _new_material_name=_Var("orthotropic"),
        _last_isotropic_material_name="previous steel",
    )

    assert main_application.Application._apply_material_spec(
        app, _material_spec(symmetry="orthotropic")
    ) is False
    assert app._new_material_name.get() == "previous steel"
    assert messages.errors


def test_runtime_material_callback_updates_solver_dropdowns(monkeypatch):
    messages = _Messages()
    monkeypatch.setattr(fem_integration, "messagebox", messages)
    window = SimpleNamespace(
        window=object(),
        material_library_name=_Var("old"),
        _last_isotropic_material_name="old",
        elastic_modulus_gpa=_Var(),
        poisson_ratio=_Var(),
        yield_stress_mpa=_Var(),
        material_model=_Var(),
        steel_grade=_Var(),
        steel_thickness_class=_Var(),
    )

    assert fem_integration.RuntimeFEMWindow._apply_material_spec(
        window,
        _material_spec(hardening={"kind": "dnv_c208", "grade": "S355", "thickness": 0.050}),
    ) is True
    assert window.material_library_name.get() == "Test S355"
    assert window.elastic_modulus_gpa.get() == pytest.approx(205.0)
    assert window.material_model.get() == "DNV-RP-C208 steel"
    assert window.steel_grade.get() == "S355"
    assert window.steel_thickness_class.get() == "40 < t <= 63"
    assert not messages.errors


def test_runtime_material_callback_warns_when_curve_cannot_be_preserved(monkeypatch):
    messages = _Messages()
    monkeypatch.setattr(fem_integration, "messagebox", messages)
    window = SimpleNamespace(
        window=object(),
        material_library_name=_Var("old"),
        _last_isotropic_material_name="old",
        elastic_modulus_gpa=_Var(),
        poisson_ratio=_Var(),
        yield_stress_mpa=_Var(),
        material_model=_Var(),
        steel_grade=_Var(),
        steel_thickness_class=_Var(),
    )

    assert fem_integration.RuntimeFEMWindow._apply_material_spec(
        window, _material_spec(hardening={"kind": "linear"})
    ) is True
    assert window.material_model.get() == "linear elastic"
    assert messages.warnings


def test_ecosystem_gui_delegates_to_embedded_package_hosts(monkeypatch):
    import anyfileio.gui
    import anymaterial.gui
    import anymesher.gui

    master = object()
    callback = object()
    calls = []

    monkeypatch.setattr(
        anymaterial.gui,
        "open_material_editor",
        lambda owner, **kwargs: calls.append(("material", owner, kwargs)) or ("mw", "me"),
    )
    monkeypatch.setattr(
        anymesher.gui,
        "open_mesher",
        lambda owner, **kwargs: calls.append(("mesh", owner, kwargs)) or ("xw", "xe"),
    )
    monkeypatch.setattr(
        anyfileio.gui,
        "open_inspector",
        lambda owner, **kwargs: calls.append(("file", owner, kwargs)) or ("fw", "fe"),
    )

    assert ecosystem_gui.open_material_editor(master, on_apply=callback) == ("mw", "me")
    assert ecosystem_gui.open_mesher(master) == ("xw", "xe")
    assert ecosystem_gui.open_file_inspector(master, "model.FEM") == ("fw", "fe")
    assert calls == [
        ("material", master, {"initial_spec": None, "on_apply": callback}),
        ("mesh", master, {}),
        ("file", master, {"path": "model.FEM"}),
    ]


def test_sesam_shell_model_uses_anyfileio_public_document_layer(monkeypatch):
    import anyfileio.sesam

    calls = []
    document = SimpleNamespace(
        nodes={
            1: SimpleNamespace(coordinates=(0.0, 0.0, 0.0)),
            2: SimpleNamespace(coordinates=(1.0, 0.0, 0.0)),
            3: SimpleNamespace(coordinates=(1.0, 1.0, 0.0)),
            4: SimpleNamespace(coordinates=(0.0, 1.0, 0.0)),
        },
        elements={
            10: SimpleNamespace(
                element_id=10,
                type_code=24,
                node_ids=(1, 2, 3, 4),
                material_id=1,
                section_id=2,
            )
        },
        sections={2: SimpleNamespace(thickness=0.012)},
    )
    monkeypatch.setattr(
        anyfileio.sesam,
        "read_sesam_fem_document",
        lambda path, strict=False: calls.append((path, strict)) or document,
    )
    monkeypatch.setattr(
        anyfileio.sesam,
        "get_element_spec",
        lambda code: SimpleNamespace(name="Q4", is_shell=True, is_beam=False),
    )

    model = fe_plate_fields.read_sesam_shell_model("model.FEM")

    assert calls == [("model.FEM", False)]
    assert tuple(model.nodes) == (1, 2, 3, 4)
    assert model.shell_elements[10].element_type == "Q4"
    assert model.shell_sections[0].thickness_m == pytest.approx(0.012)


def test_dependency_and_gui_wiring_is_declared_in_release_surfaces():
    setup_source = (REPOSITORY_ROOT / "setup.py").read_text(encoding="utf-8")
    requirements = (REPOSITORY_ROOT / "requirements-core.txt").read_text(encoding="utf-8")
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    app_source = (REPOSITORY_ROOT / "anystruct" / "main_application.py").read_text(encoding="utf-8")
    runtime_source = (REPOSITORY_ROOT / "anystruct" / "fem_integration.py").read_text(encoding="utf-8")

    for distribution in ("ANYgeometry", "ANYmaterial", "ANYmesher", "ANYfileio"):
        assert distribution in setup_source
        assert distribution in requirements
    assert "ANYfileio[semantics]>=0.2.1'" in setup_source
    assert "ANYgeometry>=0.2.4'" in setup_source
    assert "ANYmesher>=0.3.2'" in setup_source
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'anymesher = ">=0.3.2"' in pyproject
    assert 'anysolver = ">=0.4.0"' in pyproject
    assert "ANYsolver>=0.4.0'" in setup_source
    assert "ANY3dView[gpu]>=0.5.1'" in setup_source
    assert "ANYbuckling>=0.1.1'" in setup_source
    assert "ANYmaterial>=0.1.1'" in setup_source
    assert "ANYtk3D>=0.5.1'" in setup_source
    assert "<0." not in setup_source
    assert "python_requires='>=3.13'" in setup_source
    assert "Programming Language :: Python :: 3.13" in setup_source
    assert "Programming Language :: Python :: 3.14" in setup_source
    assert "repository: audunarn/ANYmaterial" in workflow
    assert "repository: audunarn/ANY3dView" in workflow
    assert "repository: audunarn/ANYgeometry" in workflow
    assert "repository: audunarn/ANYmesh" in workflow
    assert "repository: audunarn/ANYfileIO" in workflow
    assert "path: .ecosystem/ANYfileIO" in workflow
    assert ".ecosystem/ANYfileIO[semantics]" in workflow
    assert "repository: audunarn/ANYio" not in workflow
    assert ".ecosystem/ANYio" not in workflow
    assert "import any3dview, anybuckling, anyfileio" in workflow
    assert "repository: audunarn/ANYsolver" in workflow
    assert "repository: audunarn/ANYbuckling" in workflow
    assert "repository: audunarn/ANYtk3D" in workflow
    assert 'python -m pip install --no-deps -e ".ecosystem/ANY3dView[gpu]"' in workflow
    assert "-e .ecosystem/ANYmaterial" in workflow
    assert ".ecosystem/ANYgeometry" in workflow
    assert "python -m build" in workflow
    assert "python -m twine check dist/*" in workflow
    assert 'python -m venv "$smoke_dir"' in workflow
    assert '"$smoke_python" -m pip check' in workflow
    assert "Choose/edit material (ANYmaterial)..." in app_source
    assert "Open mesher (ANYmesher)..." in app_source
    assert "Inspect FE file (ANYfileio)..." in app_source
    assert 'text="Open ANYmesher..."' in runtime_source
    assert 'text="Choose/edit in ANYmaterial..."' in runtime_source
