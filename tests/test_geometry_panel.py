"""Geometry panel tests: plate thickness regions and selected-edge boundary conditions."""

import json
import math
from collections import Counter

from anysolver.runtime import (
    LightweightFEMConfig,
    build_generated_geometry,
    run_production_fem,
)

FLAT = {
    "geometry": "flat panel",
    "length_m": 4.0,
    "width_m": 3.0,
    "thickness_m": 0.012,
    "has_stiffener": False,
    "has_girder": False,
}
CYLINDER = {
    "geometry": "cylinder",
    "radius_m": 2.0,
    "length_m": 8.0,
    "thickness_m": 0.012,
    "has_stiffener": False,
    "has_girder": False,
}


def test_flat_thickness_region_assigns_shells_and_aligns_breaks() -> None:
    regions = json.dumps(
        [{"thickness_m": 0.020, "patches": [{"min_a": 1.0, "max_a": 3.0, "min_b": 0.75, "max_b": 2.25}]}]
    )
    generated = build_generated_geometry(
        FLAT, LightweightFEMConfig(mesh_fidelity="medium", thickness_regions_json=regions)
    )
    skin = [s for s in generated["shells"] if "role" not in s]
    histogram = Counter(round(float(s["thickness"]), 4) for s in skin)
    assert histogram[0.02] > 0 and histogram[0.012] > 0
    info = generated["thickness_regions"]
    assert info["regions"] == 1 and info["shells_assigned"] == histogram[0.02]
    # Region boundaries are exact break lines: node columns exist at x=1 and x=3.
    xs = {round(float(n["coords"][0]), 6) for n in generated["nodes"]}
    assert 1.0 in xs and 3.0 in xs


def test_cylinder_thickness_region_assigns_shells() -> None:
    circumference = 2.0 * math.pi * 2.0
    regions = json.dumps(
        [{"thickness_m": 0.025, "patches": [{"min_a": 2.0, "max_a": 6.0, "min_b": 0.0, "max_b": circumference / 4.0}]}]
    )
    generated = build_generated_geometry(
        CYLINDER, LightweightFEMConfig(mesh_fidelity="coarse", thickness_regions_json=regions)
    )
    skin = [s for s in generated["shells"] if "role" not in s]
    histogram = Counter(round(float(s["thickness"]), 4) for s in skin)
    assert histogram[0.025] > 0 and histogram[0.012] > 0
    assert generated["thickness_regions"]["shells_assigned"] == histogram[0.025]


def test_thicker_region_stiffens_the_panel() -> None:
    base = dict(mesh_fidelity="medium", pressure_pa=50000.0, boundary_condition="simply supported")
    uniform = run_production_fem(FLAT, LightweightFEMConfig(**base))
    regions = json.dumps(
        [{"thickness_m": 0.024, "patches": [{"min_a": 1.0, "max_a": 3.0, "min_b": 0.75, "max_b": 2.25}]}]
    )
    thickened = run_production_fem(FLAT, LightweightFEMConfig(**base, thickness_regions_json=regions))
    assert uniform.status == "ok" and thickened.status == "ok"
    assert thickened.displacement_max_m < 0.6 * uniform.displacement_max_m
    assert any("Plate thickness regions" in str(d) for d in thickened.diagnostics)


def test_custom_bc_segments_create_edge_supports() -> None:
    bc = json.dumps(
        [{"varying_axis": "a", "fixed_coordinate": 0.0, "start_coordinate": 0.0,
          "end_coordinate": 4.0, "support": "fixed"}]
    )
    generated = build_generated_geometry(
        FLAT, LightweightFEMConfig(mesh_fidelity="coarse", custom_load_bc_enabled=True,
                                   custom_bc_segments_json=bc)
    )
    groups = [s for s in generated["supports"] if str(s.get("name", "")).startswith("custom_edge_bc")]
    assert len(groups) == 1
    # Legacy "fixed" segment maps to a clamped per-DOF constraint set.
    assert set(groups[0]["constraints"]) == {"ux", "uy", "uz", "rx", "ry", "rz"}
    assert len(groups[0]["node_ids"]) >= 2
    # The constrained nodes all lie on the y=0 edge.
    coords = {int(n["id"]): n["coords"] for n in generated["nodes"]}
    assert all(abs(float(coords[i][1])) < 1e-9 for i in groups[0]["node_ids"])


def test_custom_bc_segments_constrain_the_solve() -> None:
    bc_edges = [
        {"varying_axis": "b", "fixed_coordinate": 0.0, "start_coordinate": 0.0, "end_coordinate": 3.0},
        {"varying_axis": "b", "fixed_coordinate": 4.0, "start_coordinate": 0.0, "end_coordinate": 3.0},
        {"varying_axis": "a", "fixed_coordinate": 0.0, "start_coordinate": 0.0, "end_coordinate": 4.0},
        {"varying_axis": "a", "fixed_coordinate": 3.0, "start_coordinate": 0.0, "end_coordinate": 4.0},
    ]
    for edge in bc_edges:
        edge["support"] = "fixed"
    result = run_production_fem(
        FLAT,
        LightweightFEMConfig(
            mesh_fidelity="medium",
            custom_load_bc_enabled=True,
            custom_loads_add_to_imported=True,
            pressure_pa=50000.0,
            custom_bc_segments_json=json.dumps(bc_edges),
        ),
    )
    assert result.status == "ok"
    assert result.displacement_max_m > 0.0
    assert any("boundary condition segment" in str(d) for d in result.diagnostics)
