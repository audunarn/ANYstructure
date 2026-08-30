from __future__ import annotations

import warnings

from anysolver import LegacyQ4DeprecationWarning, ShellElement
from anysolver.anystructure_fem_mode import (
    AnyStructureFEMConfig,
    build_fe_model_from_generated_geometry,
)
from anysolver import runtime as solver_runtime

from anystruct import fem_integration


def test_runtime_policy_is_legacy_for_every_supported_shell_topology() -> None:
    assert fem_integration._runtime_formulation_for_node_count(3) == "legacy-s3"
    assert fem_integration._runtime_formulation_for_node_count(4) == "legacy"
    assert fem_integration._runtime_formulation_for_node_count(6) == "legacy"
    assert fem_integration._runtime_formulation_for_node_count(8) == "legacy"


def test_generated_geometry_carries_explicit_legacy_formulations(monkeypatch) -> None:
    projection = fem_integration.geometry_generators.project_runtime_geometry(
        fem_integration.geometry_generators.build_runtime_geometry_authority(
            {
                "geometry": "flat panel",
                "length_m": 1.0,
                "width_m": 1.0,
                "plate_thickness_m": 0.01,
            },
            include_stiffeners=False,
            include_girders=False,
        )
    )
    generated = {
        "shells": [
            {"id": 1, "node_ids": [1, 2, 3]},
            {"id": 2, "node_ids": [1, 2, 3, 4]},
        ]
    }
    monkeypatch.setattr(
        fem_integration.fe_solver,
        "build_generated_geometry",
        lambda _projection, _config: generated,
    )

    result = fem_integration.build_runtime_generated_geometry(projection, object())

    assert [item["formulation"] for item in result["shells"]] == [
        "legacy-s3",
        "legacy",
    ]


def test_explicit_runtime_policy_constructs_legacy_q4_elements() -> None:
    summary = {
        "geometry": "flat panel",
        "length_m": 1.0,
        "width_m": 1.0,
        "thickness_m": 0.01,
        "has_stiffener": False,
        "has_girder": False,
    }
    config = solver_runtime.LightweightFEMConfig(mesh_fidelity="coarse")
    generated = fem_integration.build_runtime_generated_geometry(summary, config)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", LegacyQ4DeprecationWarning)
        model = build_fe_model_from_generated_geometry(
            generated,
            AnyStructureFEMConfig(),
        )

    shells = [
        element
        for element in model.mesh.elements.values()
        if isinstance(element, ShellElement)
    ]
    assert shells
    assert all(type(element) is ShellElement for element in shells)
