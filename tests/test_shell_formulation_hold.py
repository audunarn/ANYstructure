from __future__ import annotations

from anysolver import (
    NativeParityE4PLS3V2DShellElement,
    QualifiedE4PLShellElement,
    ShellElement,
)
from anysolver.anystructure_fem_mode import (
    AnyStructureFEMConfig,
    build_fe_model_from_generated_geometry,
)
from anysolver import runtime as solver_runtime

from anystruct import fem_integration


def test_runtime_policy_selects_qualified_q4_and_v2d_s3() -> None:
    assert fem_integration._runtime_formulation_for_node_count(3) == "e4-pl-s3-v2d"
    assert fem_integration._runtime_formulation_for_node_count(4) == "e4-pl"
    assert fem_integration._runtime_formulation_for_node_count(6) == "legacy"
    assert fem_integration._runtime_formulation_for_node_count(8) == "legacy"


def test_generated_geometry_carries_exact_current_formulation_authority(monkeypatch) -> None:
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
            {
                "id": 1,
                "node_ids": [1, 2, 3],
                "reference_normal": [0.0, 0.0, 1.0],
            },
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
        "e4-pl-s3-v2d",
        "e4-pl",
    ]
    assert result["shells"][0]["formulation_id"] == (
        "CANDIDATE_E4_PL_S3_V2D_NATIVE_PARITY_V1"
    )
    assert result["shells"][0]["owner_normal_authority"] == (
        "PHYSICAL_SURFACE_OWNER_NORMAL_V2D_V1"
    )
    assert result["shells"][1]["formulation_id"] == (
        "E4_PL_QUALIFIED_Q4_HYBRID_V2"
    )


def test_runtime_policy_constructs_qualified_q4_elements() -> None:
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
    assert all(type(element) is QualifiedE4PLShellElement for element in shells)


def test_generated_v2d_record_constructs_exact_s3_class(monkeypatch) -> None:
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
        "nodes": [
            {"id": 1, "coords": [0.0, 0.0, 0.0]},
            {"id": 2, "coords": [1.0, 0.0, 0.0]},
            {"id": 3, "coords": [0.5, 0.8660254037844386, 0.0]},
        ],
        "shells": [
            {
                "id": 1,
                "node_ids": [1, 2, 3],
                "thickness": 0.01,
                "material": "steel",
                "reference_normal": [0.0, 0.0, 1.0],
            }
        ],
    }
    monkeypatch.setattr(
        fem_integration.fe_solver,
        "build_generated_geometry",
        lambda _projection, _config: generated,
    )

    authorized = fem_integration.build_runtime_generated_geometry(
        projection, object()
    )
    model = build_fe_model_from_generated_geometry(
        authorized,
        AnyStructureFEMConfig(),
    )

    assert type(model.mesh.get_element(1)) is NativeParityE4PLS3V2DShellElement
