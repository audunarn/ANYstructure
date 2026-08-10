"""Parity gates for the ANYgeometry-backed runtime/FEM/preview seam."""

from __future__ import annotations

from typing import Any

import pytest

from anygeometry import Cone, Cylinder, EntityRef, GeometryModel, Plane
from anysolver import runtime as solver_runtime

from anystruct import fem_integration, geometry_generators


_CASES = (
    pytest.param(
        {
            "geometry": "flat panel",
            "length_m": 4.0,
            "width_m": 3.0,
            "thickness_m": 0.012,
            "has_stiffener": False,
            "has_girder": False,
        },
        Plane,
        ("shell", "plate", "boundaries"),
        id="flat",
    ),
    pytest.param(
        {
            "geometry": "flat panel",
            "length_m": 4.0,
            "width_m": 3.0,
            "thickness_m": 0.012,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_spacing_m": 1.0,
            "girder_spacing_m": 2.0,
            "stiffener_section": {"web_height": 0.2},
            "girder_section": {"web_height": 0.3},
        },
        Plane,
        (
            "shell",
            "plate",
            "boundaries",
            "longitudinal_stiffeners",
            "transverse_stiffeners",
        ),
        id="stiffened-flat",
    ),
    pytest.param(
        {
            "geometry": "cylinder",
            "radius_m": 2.0,
            "length_m": 5.0,
            "thickness_m": 0.018,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_spacing_m": 1.0,
            "girder_spacing_m": 2.5,
        },
        Cylinder,
        (
            "shell",
            "bottom",
            "top",
            "boundaries",
            "longitudinal_stiffeners",
            "ring_stiffeners",
        ),
        id="cylinder",
    ),
    pytest.param(
        {
            "geometry": "cylinder",
            "radius_m": 2.0,
            "length_m": 5.0,
            "thickness_m": 0.018,
            "is_cone": True,
            "cone_r1_m": 2.0,
            "cone_r2_m": 1.5,
            "cone_length_m": 5.0,
            "has_stiffener": True,
            "has_girder": True,
            "stiffener_spacing_m": 1.0,
            "girder_spacing_m": 2.5,
        },
        Cone,
        (
            "shell",
            "bottom",
            "top",
            "boundaries",
            "longitudinal_stiffeners",
            "ring_stiffeners",
        ),
        id="cone",
    ),
)


def test_projection_materializes_owner_once_only_on_geometry_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[float, float]] = []
    original = geometry_generators.generate_plate_geometry

    def counting_plate(length: float, width: float, **kwargs: Any) -> GeometryModel:
        calls.append((length, width))
        return original(length, width, **kwargs)

    monkeypatch.setattr(
        geometry_generators,
        "generate_plate_geometry",
        counting_plate,
    )
    authority = geometry_generators.build_runtime_geometry_authority(
        {
            "geometry": "flat panel",
            "length_m": 4.0,
            "width_m": 3.0,
            "thickness_m": 0.012,
        }
    )
    first = geometry_generators.project_runtime_geometry(authority)
    second = geometry_generators.project_runtime_payload(dict(first), authority)

    assert calls == []
    model = first.geometry_model
    assert calls == [(4.0, 3.0)]
    assert second.geometry_model is model
    assert authority.model is model
    assert calls == [(4.0, 3.0)]


@pytest.mark.parametrize(("summary", "surface_type", "semantic_groups"), _CASES)
def test_runtime_projection_preserves_legacy_fe_payload_and_owner_groups(
    summary: dict[str, Any],
    surface_type: type,
    semantic_groups: tuple[str, ...],
) -> None:
    config = solver_runtime.LightweightFEMConfig(mesh_fidelity="coarse")
    legacy = solver_runtime.build_generated_geometry(summary, config)

    projection = fem_integration.runtime_geometry_projection(summary, config)
    generated = fem_integration.build_runtime_generated_geometry(projection, config)
    model = projection.geometry_model

    assert dict(projection) == summary
    assert generated == legacy
    assert set(generated) == set(legacy)
    assert type(model) is GeometryModel
    assert generated.geometry_model is model
    assert generated.geometry_authority is projection.geometry_authority
    assert projection.structural_metadata["thickness_m"] == summary["thickness_m"]
    assert "thickness_m" not in projection.geometry_authority.geometry_fields
    assert all(not face.metadata for face in model.faces.values())
    assert all(isinstance(face.surface, surface_type) for face in model.faces.values())

    for group_name in semantic_groups:
        references = model.group(group_name)
        assert references, group_name
        assert all(type(reference) is EntityRef for reference in references)
        assert all(model.resolve_ref(reference) == (reference,) for reference in references)

    remeshed = fem_integration.build_runtime_generated_geometry(generated, config)
    assert remeshed == legacy
    assert remeshed.geometry_model is model


def test_runtime_solver_handoff_receives_geometry_backed_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = {
        "geometry": "flat panel",
        "length_m": 4.0,
        "width_m": 3.0,
        "thickness_m": 0.012,
        "has_stiffener": True,
        "has_girder": True,
        "stiffener_spacing_m": 1.0,
        "girder_spacing_m": 2.0,
        "stiffener_section": {"web_height": 0.2},
        "girder_section": {"web_height": 0.3},
    }
    captured: dict[str, Any] = {}

    def fake_run_production(
        geometry: dict[str, Any],
        config: Any,
        status_callback: Any = None,
        imported_fem_model: Any = None,
        precomputed_generated_geometry: Any = None,
    ) -> Any:
        captured["geometry"] = geometry
        return solver_runtime.LightweightFEMResult(
            status="ok",
            stress_max_pa=0.0,
            stress_p95_pa=0.0,
            displacement_max_m=0.0,
            mesh_info={"nodes": 0, "shells": 0, "beams": 0},
            prestress_summary={},
            load_resultant={},
            visualization={},
            solver_name="geometry authority test",
        )

    monkeypatch.setattr(
        fem_integration,
        "runtime_geometry_summary",
        lambda snapshot, options=None: dict(summary),
    )
    monkeypatch.setattr(
        fem_integration.fe_solver,
        "run_production_fem",
        fake_run_production,
    )
    snapshot = fem_integration.RuntimeFEMLineSnapshot(
        line_name="line1",
        line_points=None,
        structure_bundle=None,
    )

    result = fem_integration.run_runtime_fem(
        snapshot,
        fem_integration.RuntimeFEMOptions(),
    )

    handed_off = captured["geometry"]
    assert result.status == "ok"
    assert isinstance(handed_off, geometry_generators.GeometryBackedProjection)
    assert dict(handed_off) == summary
    assert type(handed_off.geometry_model) is GeometryModel
    assert handed_off.geometry_model.group("longitudinal_stiffeners")
    assert handed_off.geometry_model.group("transverse_stiffeners")
