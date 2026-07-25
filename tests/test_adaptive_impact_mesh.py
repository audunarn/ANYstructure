"""Local detail meshing, mesh sizing metrics, and mesh preview."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

from anysolver.runtime import (
    LightweightFEMConfig,
    _collision_impact_point,
    _graded_axis_breaks,
    build_generated_geometry,
)
from anystruct.fem_integration import (
    RuntimeFEMOptions,
    _solver_config_from_options,
    create_runtime_fem_mesh_preview_figure,
)

FLAT = {"geometry": "flat panel", "length_m": 4.0, "width_m": 3.0, "thickness_m": 0.012, "has_stiffener": False, "has_girder": False}
CYLINDER = {
    "geometry": "cylinder",
    "radius_m": 2.0,
    "length_m": 8.0,
    "thickness_m": 0.018,
    "has_stiffener": True,
    "has_girder": True,
    "stiffener_spacing_m": 0.75,
    "girder_spacing_m": 3.5,
}


def test_graded_axis_breaks_are_fine_at_center_and_coarse_away() -> None:
    breaks = _graded_axis_breaks(4.0, 1.5, 0.06, 0.4, 0.4, 0.8, mandatory=(1.0,))
    assert breaks[0] == 0.0 and breaks[-1] == 4.0
    assert any(abs(b - 1.0) < 1e-6 for b in breaks)  # mandatory member line kept
    sizes = np.diff(breaks)
    near = [s for b, s in zip(breaks[:-1], sizes) if abs(b + s / 2 - 1.5) < 0.4]
    far = [s for b, s in zip(breaks[:-1], sizes) if abs(b + s / 2 - 1.5) > 1.2]
    assert max(near) < 0.12  # fine near the impact center
    assert max(far) > 0.25  # coarse away
    assert sizes.min() > 0.0  # strictly increasing, no degenerate elements


def test_collision_impact_point_from_trajectory() -> None:
    cfg = LightweightFEMConfig(
        collision_start_x_m=2.5, collision_start_y_m=1.0, collision_start_z_m=0.5,
        collision_vector_x=0.0, collision_vector_y=0.0, collision_vector_z=-1.0,
    )
    assert _collision_impact_point(cfg, 4.0, 3.0) == pytest.approx((2.5, 1.0))

    # angled trajectory lands downstream of the start point
    cfg2 = LightweightFEMConfig(
        collision_start_x_m=1.0, collision_start_y_m=1.0, collision_start_z_m=1.0,
        collision_vector_x=1.0, collision_vector_y=0.0, collision_vector_z=-1.0,
    )
    x, y = _collision_impact_point(cfg2, 4.0, 3.0)
    assert x == pytest.approx(2.0)
    assert y == pytest.approx(1.0)


def test_adaptive_mesh_refines_at_impact_and_reports_metrics() -> None:
    base_cfg = LightweightFEMConfig(mesh_fidelity="medium", collision_enabled=True,
        collision_start_x_m=2.0, collision_start_y_m=1.5, collision_start_z_m=0.5,
        collision_vector_x=0.0, collision_vector_y=0.0, collision_vector_z=-1.0, collision_radius_m=0.15)
    base = build_generated_geometry(FLAT, base_cfg)
    assert base["adaptive_mesh"]["enabled"] is False

    ad_cfg = LightweightFEMConfig(mesh_fidelity="medium", collision_enabled=True,
        collision_adaptive_mesh_enabled=True, collision_adaptive_fine_factor=0.25, collision_adaptive_zone_factor=2.5,
        collision_start_x_m=2.0, collision_start_y_m=1.5, collision_start_z_m=0.5,
        collision_vector_x=0.0, collision_vector_y=0.0, collision_vector_z=-1.0, collision_radius_m=0.15)
    adaptive = build_generated_geometry(FLAT, ad_cfg)

    a = adaptive["adaptive_mesh"]
    m = adaptive["mesh_metrics"]
    assert a["enabled"] is True
    assert a["impact_point_m"] == pytest.approx([2.0, 1.5])
    # significantly finer locally than the base uniform mesh
    assert m["min_element_size_m"] < 0.6 * base["mesh_metrics"]["nominal_element_size_m"]
    assert m["max_element_size_m"] / m["min_element_size_m"] > 3.0
    assert m["shell_element_count"] > base["mesh_metrics"]["shell_element_count"]
    assert a["sources"][0]["source"] == "impact"
    assert a["sources"][0]["growth_factor"] == pytest.approx(1.35)


def test_point_detail_mesh_refines_at_selected_point_and_reports_extent() -> None:
    base = build_generated_geometry(FLAT, LightweightFEMConfig(mesh_fidelity="medium"))
    cfg = LightweightFEMConfig(
        mesh_fidelity="medium",
        point_refinement_enabled=True,
        point_refinement_x_m=2.2,
        point_refinement_y_m=1.2,
        point_refinement_fine_size_m=0.05,
        point_refinement_extent_m=0.35,
        point_refinement_growth_factor=1.22,
    )
    refined = build_generated_geometry(FLAT, cfg)
    adaptive = refined["adaptive_mesh"]
    source = adaptive["sources"][0]
    assert adaptive["enabled"] is True
    assert source["source"] == "selected_point"
    assert source["point_m"] == pytest.approx([2.2, 1.2])
    assert source["extent_m"] == pytest.approx(0.35)
    assert source["growth_factor"] == pytest.approx(1.22)
    assert source["fine_element_size_m"] == pytest.approx(0.05)
    assert 0.02 <= refined["mesh_metrics"]["min_element_size_m"] <= 0.055
    assert refined["mesh_metrics"]["shell_element_count"] > base["mesh_metrics"]["shell_element_count"]


def test_selected_panel_detail_mesh_refines_patch_and_preview_draws_region() -> None:
    cfg = LightweightFEMConfig(
        mesh_fidelity="medium",
        local_refinement_enabled=True,
        local_refinement_patches_json='[{"min_a": 1.0, "max_a": 1.5, "min_b": 0.75, "max_b": 1.25}]',
        local_refinement_fine_size_m=0.04,
        local_refinement_extent_m=0.1,
        local_refinement_growth_factor=1.2,
    )
    refined = build_generated_geometry(FLAT, cfg)
    source = refined["adaptive_mesh"]["sources"][0]
    assert source["source"] == "selected_panels"
    assert source["region_count"] == 1
    assert source["extent_m"] == pytest.approx(0.1)
    assert source["growth_factor"] == pytest.approx(1.2)
    assert source["fine_element_size_m"] == pytest.approx(0.04)
    assert 0.016 <= refined["mesh_metrics"]["min_element_size_m"] <= 0.045

    figure = create_runtime_fem_mesh_preview_figure(refined)
    assert figure.axes[0].lines


def test_cylinder_selected_panel_detail_mesh_refines_centered_patch() -> None:
    base = build_generated_geometry(CYLINDER, LightweightFEMConfig(mesh_fidelity="coarse"))
    cfg = LightweightFEMConfig(
        mesh_fidelity="coarse",
        local_refinement_enabled=True,
        local_refinement_patches_json=json.dumps(
            [{"min_a": -1.0, "max_a": 1.0, "min_b": 3.0, "max_b": 4.5, "axis_a_origin": "centered"}]
        ),
        local_refinement_fine_size_m=0.1,
        local_refinement_extent_m=0.2,
        local_refinement_growth_factor=1.25,
    )
    refined = build_generated_geometry(CYLINDER, cfg)
    source = refined["adaptive_mesh"]["sources"][0]

    assert refined["adaptive_mesh"]["enabled"] is True
    assert source["source"] == "selected_panels"
    assert source["coordinates"] == "cylinder_axial_arc"
    assert source["regions"][0]["min_a"] == pytest.approx(3.0)
    assert source["regions"][0]["max_a"] == pytest.approx(5.0)
    assert source["growth_factor"] == pytest.approx(1.25)
    assert refined["mesh_metrics"]["shell_element_count"] > base["mesh_metrics"]["shell_element_count"]
    assert refined["mesh_metrics"]["min_element_size_m"] < base["mesh_metrics"]["min_element_size_m"]


def test_cylinder_impact_detail_mesh_refines_axial_arc_impact_point() -> None:
    base_cfg = LightweightFEMConfig(
        mesh_fidelity="coarse",
        collision_enabled=True,
        collision_start_x_m=6.0,
        collision_start_y_m=0.0,
        collision_start_z_m=5.0,
        collision_vector_x=-1.0,
        collision_vector_y=0.0,
        collision_vector_z=0.0,
        collision_radius_m=0.2,
    )
    base = build_generated_geometry(CYLINDER, base_cfg)
    cfg = LightweightFEMConfig(
        mesh_fidelity="coarse",
        collision_enabled=True,
        collision_adaptive_mesh_enabled=True,
        collision_adaptive_fine_size_m=0.08,
        collision_adaptive_extent_m=0.35,
        collision_adaptive_growth_factor=1.2,
        collision_start_x_m=6.0,
        collision_start_y_m=0.0,
        collision_start_z_m=5.0,
        collision_vector_x=-1.0,
        collision_vector_y=0.0,
        collision_vector_z=0.0,
        collision_radius_m=0.2,
    )
    refined = build_generated_geometry(CYLINDER, cfg)
    source = refined["adaptive_mesh"]["sources"][0]

    assert source["source"] == "impact"
    assert source["coordinates"] == "cylinder_axial_arc"
    # Sphere at (6,0,5) travelling -x strikes the wall (radius 2) at (2,0,5):
    # axial height 5.0, circumferential arc 0.0 (theta = 0).
    assert source["impact_point_m"] == pytest.approx([5.0, 0.0])
    assert source["marker_xyz_m"] == pytest.approx([2.0, 0.0, 5.0])
    assert source["extent_m"] == pytest.approx(0.35)
    assert source["growth_factor"] == pytest.approx(1.2)
    assert refined["mesh_metrics"]["shell_element_count"] > base["mesh_metrics"]["shell_element_count"]
    assert refined["mesh_metrics"]["min_element_size_m"] < base["mesh_metrics"]["min_element_size_m"]


def test_mesh_metrics_present_for_uniform_mesh() -> None:
    g = build_generated_geometry(FLAT, LightweightFEMConfig(mesh_fidelity="fine"))
    m = g["mesh_metrics"]
    assert m["shell_element_count"] > 0
    assert m["nominal_element_size_m"] > 0.0
    assert 0.0 < m["min_edge_over_max_edge"] <= 1.0


def test_mesh_preview_figure_builds_from_options() -> None:
    options = RuntimeFEMOptions(mesh_fidelity="medium", collision_enabled=True,
        collision_adaptive_mesh_enabled=True,
        collision_start_x_m=2.0, collision_start_y_m=1.0, collision_start_z_m=0.5,
        collision_vector_x=0.0, collision_vector_y=0.0, collision_vector_z=-1.0, collision_radius_m=0.15)
    config = _solver_config_from_options(options)
    generated = build_generated_geometry(FLAT, config)
    figure = create_runtime_fem_mesh_preview_figure(generated)
    assert figure is not None
    assert figure.axes  # at least one axis rendered


def test_acceleration_and_added_mass_load_resolution() -> None:
    """Frontend resolves plate edges/rings and applies acceleration + added mass loads."""
    from anysolver.runtime import _apply_acceleration_and_masses, _resolve_added_mass_nodes
    from anysolver.anystructure_fem_mode import build_fe_model_from_generated_geometry
    from anysolver.boundary import LoadCase
    from anysolver.matrix_assembly import assemble_load_vector

    geom = {"geometry": "flat panel", "length_m": 4.0, "width_m": 2.0, "thickness_m": 0.01, "has_stiffener": False, "has_girder": False}
    cfg = LightweightFEMConfig(mesh_fidelity="coarse", acceleration_z_m_s2=-9.81, added_mass_kg=500.0, added_mass_location="plate edge x0")
    generated = build_generated_geometry(geom, cfg)

    x0_nodes = _resolve_added_mass_nodes(generated, geom, "plate edge x0")
    all_nodes = _resolve_added_mass_nodes(generated, geom, "plate all edges")
    assert len(x0_nodes) >= 2
    assert len(all_nodes) > len(x0_nodes)
    # x0-edge nodes all lie on the minimum-x edge
    coords = {int(n["id"]): n["coords"] for n in generated["nodes"]}
    assert all(abs(coords[nid][0] - 0.0) < 1e-6 for nid in x0_nodes)

    model = build_fe_model_from_generated_geometry(generated)
    load_case = LoadCase("t")
    summary = _apply_acceleration_and_masses(model, load_case, generated, geom, cfg)
    assert summary["added_mass_nodes"] == len(x0_nodes)

    F, _ = assemble_load_vector(model, load_case)
    fz = sum(F[model.mesh.get_node(nid).dofs[2]] for nid in model.mesh.nodes)
    structural = 7850.0 * 0.01 * 4.0 * 2.0
    assert fz == pytest.approx((structural + 500.0) * -9.81, rel=1e-6)


def test_added_mass_location_none_is_noop() -> None:
    from anysolver.runtime import _resolve_added_mass_nodes

    geom = {"geometry": "flat panel", "length_m": 3.0, "width_m": 2.0, "thickness_m": 0.01, "has_stiffener": False, "has_girder": False}
    generated = build_generated_geometry(geom, LightweightFEMConfig())
    assert _resolve_added_mass_nodes(generated, geom, "none") == []


def test_adaptive_fine_size_is_settable_and_reaches_plate_thickness() -> None:
    """An absolute impact fine size is honoured and floored at the plate thickness."""
    geom = {"geometry": "flat panel", "length_m": 3.0, "width_m": 2.0, "thickness_m": 0.012, "has_stiffener": False, "has_girder": False}
    base = dict(collision_enabled=True, collision_adaptive_mesh_enabled=True,
                collision_start_x_m=1.5, collision_start_y_m=1.0, collision_start_z_m=0.4,
                collision_radius_m=0.15, collision_vector_z=-1.0)

    # absolute fine size = plate thickness -> ~t x t elements at impact
    at_t = build_generated_geometry(geom, LightweightFEMConfig(mesh_fidelity="medium", collision_adaptive_fine_size_m=0.012, **base))
    a = at_t["adaptive_mesh"]
    assert a["fine_element_size_m"] == pytest.approx(0.012, rel=1e-6)
    assert a["floored_at_thickness"] is False
    # the smallest element edge in the model is at the thickness scale
    assert at_t["mesh_metrics"]["min_element_size_m"] == pytest.approx(0.012, abs=2e-3)

    # a requested size below the thickness is floored to the thickness
    below = build_generated_geometry(geom, LightweightFEMConfig(mesh_fidelity="medium", collision_adaptive_fine_size_m=0.004, **base))
    b = below["adaptive_mesh"]
    assert b["floored_at_thickness"] is True
    assert b["fine_element_size_m"] == pytest.approx(0.012, rel=1e-6)
    assert b["requested_fine_size_m"] == pytest.approx(0.004, rel=1e-6)

    # absolute size takes precedence over the fine factor
    both = build_generated_geometry(geom, LightweightFEMConfig(mesh_fidelity="medium",
        collision_adaptive_fine_factor=0.5, collision_adaptive_fine_size_m=0.05, **base))
    assert both["adaptive_mesh"]["fine_element_size_m"] == pytest.approx(0.05, rel=1e-6)
