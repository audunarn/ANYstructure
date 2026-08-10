import ast
import importlib
from pathlib import Path
import sys

import pytest


CORE_MODULES = [
    "anystruct.calc_loads",
    "anystruct.calc_structure",
    "anystruct.geometry_generators",
    "anystruct.helper",
    "anystruct.make_grid_numpy",
    "anystruct.ml_models",
    "anystruct.optimize",
    "anystruct.project_application",
    "anystruct.project_io",
    "anystruct.project_services",
    "anystruct.project_state",
    "anystruct.report_generator",
]

PUBLIC_MODULES = [
    "anystruct.api",
]


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module_name", CORE_MODULES + PUBLIC_MODULES)
def test_module_imports(module_name):
    module = importlib.import_module(module_name)

    assert module is not None


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_core_module_imports_without_tkinter_side_effect(module_name):
    sys.modules.pop("tkinter", None)
    sys.modules.pop("_tkinter", None)

    importlib.import_module(module_name)

    assert "tkinter" not in sys.modules
    assert "_tkinter" not in sys.modules


def test_anystructure_does_not_construct_a_second_geometry_authority():
    """Neutral topology must be returned by ANYgeometry, never rebuilt here.

    ANYstructure may accept, annotate, and pass through the shared model, but a
    local ``GeometryModel()`` call would create an independent identity/history
    domain and bypass the owner generators.
    """

    constructors = []
    for path in (REPOSITORY_ROOT / "anystruct").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        constructor_names = {"GeometryModel"}
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module not in {
                "anygeometry",
                "anygeometry.model",
                "anystruct.geometry_generators",
            }:
                continue
            constructor_names.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name == "GeometryModel"
            )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = node.func
            if isinstance(called, ast.Name) and called.id in constructor_names:
                constructors.append((path.relative_to(REPOSITORY_ROOT), node.lineno))
            elif isinstance(called, ast.Attribute) and called.attr == "GeometryModel":
                constructors.append((path.relative_to(REPOSITORY_ROOT), node.lineno))

    assert constructors == []
