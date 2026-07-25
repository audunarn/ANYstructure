"""Triangular shell topology checks for SESAM/GeniE-style meshes."""

from __future__ import annotations

import numpy as np
import pytest

from anysolver import runtime as runtime_fe_solver
from anysolver import (
    AnyStructureFEMConfig,
    FEModel,
    LoadCase,
    ShellElement,
    assemble_geometric_stiffness_matrix,
    assemble_load_vector,
    assemble_mass_matrix,
    assemble_stiffness_matrix,
    build_fe_model_from_generated_geometry,
    create_element,
)


def _tri_model(node_ids: list[int], coords: list[tuple[float, float, float]]) -> FEModel:
    model = FEModel("triangular_shell")
    model.add_material("steel", 210.0e9, 0.3, density=7850.0)
    for node_id, xyz in zip(node_ids, coords):
        model.add_node(node_id, *xyz)
    model.add_element(1, ShellElement(1, node_ids, "steel", thickness=0.02))
    return model


def _rigid_translation(element: ShellElement, direction: int) -> np.ndarray:
    u = np.zeros(element.total_dofs, dtype=float)
    u[direction::6] = 1.0
    return u


def _rigid_rotation(element: ShellElement, model: FEModel, axis: int) -> np.ndarray:
    coords = element.get_node_coordinates(model.mesh)
    centroid = np.mean(coords, axis=0)
    omega = np.zeros(3, dtype=float)
    omega[axis] = 1.0e-3
    u = np.zeros(element.total_dofs, dtype=float)
    for local_index, coord in enumerate(coords):
        base = local_index * 6
        u[base : base + 3] = np.cross(omega, coord - centroid)
        u[base + 3 : base + 6] = omega
    return u


@pytest.mark.parametrize(
    ("node_count", "natural_nodes"),
    [
        (3, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
        (6, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]),
    ],
)
def test_triangular_shell_shape_functions_interpolate_and_reproduce_fields(
    node_count: int,
    natural_nodes: list[tuple[float, float]],
) -> None:
    element = ShellElement(1, list(range(1, node_count + 1)), "steel")
    sample_points = [(0.2, 0.1), (0.45, 0.2), (1.0 / 3.0, 1.0 / 3.0)]

    for node_index, (r, s) in enumerate(natural_nodes):
        N, dN_dr, dN_ds = element.compute_shape_functions(r, s)
        expected = np.zeros(node_count)
        expected[node_index] = 1.0
        np.testing.assert_allclose(N, expected, atol=1.0e-12)
        assert np.sum(dN_dr) == pytest.approx(0.0, abs=1.0e-12)
        assert np.sum(dN_ds) == pytest.approx(0.0, abs=1.0e-12)

    linear_values = np.array([2.0 + 3.0 * r - 0.5 * s for r, s in natural_nodes])
    quadratic_values = np.array([1.0 + r + 2.0 * s + 0.25 * r * r - 0.75 * r * s + 0.5 * s * s for r, s in natural_nodes])
    for r, s in sample_points:
        N, dN_dr, dN_ds = element.compute_shape_functions(r, s)
        assert np.sum(N) == pytest.approx(1.0, abs=1.0e-12)
        assert np.sum(dN_dr) == pytest.approx(0.0, abs=1.0e-12)
        assert np.sum(dN_ds) == pytest.approx(0.0, abs=1.0e-12)
        assert float(N @ linear_values) == pytest.approx(2.0 + 3.0 * r - 0.5 * s, abs=1.0e-12)
        if node_count == 6:
            expected = 1.0 + r + 2.0 * s + 0.25 * r * r - 0.75 * r * s + 0.5 * s * s
            assert float(N @ quadratic_values) == pytest.approx(expected, abs=1.0e-12)


@pytest.mark.parametrize(
    ("node_ids", "coords"),
    [
        ([1, 2, 3], [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0)]),
        (
            [1, 2, 3, 4, 5, 6],
            [
                (0.0, 0.0, 0.0),
                (2.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.5, 0.0),
                (0.0, 0.5, 0.0),
            ],
        ),
    ],
)
def test_triangular_shell_stiffness_mass_pressure_and_geometric_assembly(
    node_ids: list[int],
    coords: list[tuple[float, float, float]],
) -> None:
    model = _tri_model(node_ids, coords)
    element = model.mesh.elements[1]
    material = model.get_material("steel")
    area = 1.0

    K = element.compute_stiffness_matrix(model.mesh, material)
    assert K.shape == (element.total_dofs, element.total_dofs)
    assert np.all(np.isfinite(K))
    np.testing.assert_allclose(K, K.T, rtol=1.0e-10, atol=1.0e-5)

    scale = max(float(np.max(np.abs(np.diag(K)))), 1.0)
    eigenvalues = np.linalg.eigvalsh(0.5 * (K + K.T))
    near_zero_modes = int(np.sum(np.abs(eigenvalues) < 1.0e-8 * max(abs(float(eigenvalues[-1])), 1.0)))
    assert near_zero_modes == 6

    rigid_modes = [_rigid_translation(element, i) for i in range(3)]
    rigid_modes.extend(_rigid_rotation(element, model, i) for i in range(3))
    for mode in rigid_modes:
        assert abs(float(mode @ K @ mode)) < 1.0e-10 * scale

    M = element.compute_mass_matrix(model.mesh, material)
    np.testing.assert_allclose(M, M.T, rtol=1.0e-12, atol=1.0e-12)
    assert float(np.min(np.linalg.eigvalsh(0.5 * (M + M.T)))) > -1.0e-9
    expected_mass = material.density * element.thickness * area
    for direction in range(3):
        unit_velocity = np.zeros(element.total_dofs)
        unit_velocity[direction::6] = 1.0
        assert float(unit_velocity @ M @ unit_velocity) == pytest.approx(expected_mass, rel=1.0e-12)

    load = LoadCase("pressure")
    load.add_pressure_load(1, 5.0)
    F, _info = assemble_load_vector(model, load)
    nodal_forces = F.reshape(len(node_ids), 6)[:, :3]
    np.testing.assert_allclose(np.sum(nodal_forces, axis=0), [0.0, 0.0, 5.0 * area], rtol=1.0e-12, atol=1.0e-12)

    K_global, _ = assemble_stiffness_matrix(model)
    M_global, _ = assemble_mass_matrix(model)
    KG_global, _ = assemble_geometric_stiffness_matrix(model, {1: {"membrane_compression_x": 10.0}})
    assert K_global.shape == M_global.shape == KG_global.shape == (model.mesh.dof_manager.total_dofs, model.mesh.dof_manager.total_dofs)


def test_triangular_pressure_reverses_with_winding() -> None:
    ccw = _tri_model([1, 2, 3], [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
    cw = _tri_model([1, 3, 2], [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (2.0, 0.0, 0.0)])

    load_ccw = LoadCase("ccw")
    load_ccw.add_pressure_load(1, 7.0)
    F_ccw, _ = assemble_load_vector(ccw, load_ccw)

    load_cw = LoadCase("cw")
    load_cw.add_pressure_load(1, 7.0)
    F_cw, _ = assemble_load_vector(cw, load_cw)

    np.testing.assert_allclose(np.sum(F_ccw.reshape(3, 6)[:, :3], axis=0), [0.0, 0.0, 7.0], atol=1.0e-12)
    np.testing.assert_allclose(np.sum(F_cw.reshape(3, 6)[:, :3], axis=0), [0.0, 0.0, -7.0], atol=1.0e-12)


def test_triangular_aliases_and_mixed_q4_t3_assembly() -> None:
    tri3 = create_element("TRIA3", 1, [1, 2, 3], "steel", thickness=0.01)
    tri6 = create_element("t6", 2, [1, 2, 3, 4, 5, 6], "steel", thickness=0.01)
    assert isinstance(tri3, ShellElement)
    assert isinstance(tri6, ShellElement)
    assert tri3.num_nodes == 3
    assert tri6.num_nodes == 6

    model = FEModel("mixed_q4_t3")
    model.add_material("steel", 210.0e9, 0.3, density=7850.0)
    for node_id, xyz in {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (1.0, 1.0, 0.0),
        4: (0.0, 1.0, 0.0),
        5: (2.0, 0.0, 0.0),
    }.items():
        model.add_node(node_id, *xyz)
    model.add_element(1, ShellElement(1, [1, 2, 3, 4], "steel", thickness=0.01))
    model.add_element(2, ShellElement(2, [2, 5, 3], "steel", thickness=0.01))

    K, _ = assemble_stiffness_matrix(model)
    M, _ = assemble_mass_matrix(model)
    assert K.shape == M.shape == (30, 30)
    assert K.nnz > 0
    assert M.nnz > 0

    high_order = FEModel("mixed_q8_t6")
    high_order.add_material("steel", 210.0e9, 0.3, density=7850.0)
    for node_id, xyz in {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (1.0, 1.0, 0.0),
        4: (0.0, 1.0, 0.0),
        5: (0.5, 0.0, 0.0),
        6: (1.0, 0.5, 0.0),
        7: (0.5, 1.0, 0.0),
        8: (0.0, 0.5, 0.0),
        9: (2.0, 0.0, 0.0),
        10: (1.5, 0.0, 0.0),
        11: (1.5, 0.5, 0.0),
    }.items():
        high_order.add_node(node_id, *xyz)
    high_order.add_element(1, ShellElement(1, [1, 2, 3, 4, 5, 6, 7, 8], "steel", thickness=0.01))
    high_order.add_element(2, ShellElement(2, [2, 9, 3, 10, 11, 6], "steel", thickness=0.01))

    K_high, _ = assemble_stiffness_matrix(high_order)
    M_high, _ = assemble_mass_matrix(high_order)
    assert K_high.shape == M_high.shape == (66, 66)
    assert K_high.nnz > 0
    assert M_high.nnz > 0


def test_generated_geometry_accepts_triangular_shell_topology() -> None:
    generated = {
        "name": "tri_generated",
        "nodes": [
            {"id": 1, "coords": [0.0, 0.0, 0.0]},
            {"id": 2, "coords": [1.0, 0.0, 0.0]},
            {"id": 3, "coords": [0.0, 1.0, 0.0]},
        ],
        "shells": [{"id": 10, "node_ids": [1, 2, 3], "thickness": 0.01}],
    }
    model = build_fe_model_from_generated_geometry(generated, AnyStructureFEMConfig(include_beams=False))
    element = model.mesh.elements[10]
    assert isinstance(element, ShellElement)
    assert element.num_nodes == 3


@pytest.mark.parametrize(("order", "node_count", "shell_type"), [("S3", 3, "S3"), ("T3", 3, "S3"), ("S6", 6, "S6"), ("T6", 6, "S6")])
def test_anystructure_runtime_geometry_can_emit_triangular_shells(order: str, node_count: int, shell_type: str) -> None:
    geometry = {
        "geometry": "flat panel",
        "length_m": 1.0,
        "width_m": 0.5,
        "thickness_m": 0.01,
        "has_stiffener": False,
        "has_girder": False,
    }
    baseline = runtime_fe_solver.build_generated_geometry(
        geometry,
        runtime_fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", shell_element_order="S4"),
    )
    generated = runtime_fe_solver.build_generated_geometry(
        geometry,
        runtime_fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", shell_element_order=order),
    )

    assert len(generated["shells"]) == 2 * len(baseline["shells"])
    assert {str(shell["type"]) for shell in generated["shells"]} == {shell_type}
    assert {len(shell["node_ids"]) for shell in generated["shells"]} == {node_count}

    model = build_fe_model_from_generated_geometry(generated, AnyStructureFEMConfig(include_beams=False))
    K, _ = assemble_stiffness_matrix(model)
    M, _ = assemble_mass_matrix(model)
    assert K.shape == M.shape == (model.mesh.dof_manager.total_dofs, model.mesh.dof_manager.total_dofs)
    assert K.nnz > 0
    assert M.nnz > 0


@pytest.mark.parametrize(("order", "node_count", "shell_type"), [("S3", 3, "S3"), ("S6", 6, "S6")])
def test_anystructure_runtime_cylinder_can_emit_triangular_shells(order: str, node_count: int, shell_type: str) -> None:
    geometry = {
        "geometry": "cylinder",
        "radius_m": 1.0,
        "length_m": 1.0,
        "thickness_m": 0.01,
        "has_stiffener": False,
        "has_girder": False,
    }
    generated = runtime_fe_solver.build_generated_geometry(
        geometry,
        runtime_fe_solver.LightweightFEMConfig(mesh_fidelity="coarse", shell_element_order=order),
    )

    assert {str(shell["type"]) for shell in generated["shells"]} == {shell_type}
    assert {len(shell["node_ids"]) for shell in generated["shells"]} == {node_count}
    if order == "S6":
        coords = {int(node["id"]): np.asarray(node["coords"], dtype=float) for node in generated["nodes"]}
        used_node_ids = {int(node_id) for shell in generated["shells"] for node_id in shell["node_ids"]}
        radial_errors = [abs(float(np.linalg.norm(coords[node_id][:2])) - 1.0) for node_id in used_node_ids]
        assert max(radial_errors) < 1.0e-10

    model = build_fe_model_from_generated_geometry(generated, AnyStructureFEMConfig(include_beams=False))
    K, _ = assemble_stiffness_matrix(model)
    assert K.shape == (model.mesh.dof_manager.total_dofs, model.mesh.dof_manager.total_dofs)
    assert K.nnz > 0


def test_anystructure_visualization_preserves_mixed_skin_shell_topology() -> None:
    generated = {
        "name": "mixed_visualization",
        "nodes": [
            {"id": 1, "coords": [0.0, 0.0, 0.0]},
            {"id": 2, "coords": [1.0, 0.0, 0.0]},
            {"id": 3, "coords": [2.0, 0.0, 0.0]},
            {"id": 4, "coords": [0.0, 1.0, 0.0]},
            {"id": 5, "coords": [1.0, 1.0, 0.0]},
            {"id": 6, "coords": [2.0, 1.0, 0.0]},
            {"id": 7, "coords": [1.5, 0.0, 0.0]},
            {"id": 8, "coords": [2.0, 0.5, 0.0]},
            {"id": 9, "coords": [1.5, 0.5, 0.0]},
        ],
        "shells": [
            {"id": 1, "node_ids": [1, 2, 5, 4], "type": "S4", "thickness": 0.01},
            {"id": 2, "node_ids": [2, 6, 5], "type": "S3", "thickness": 0.01},
            {"id": 3, "node_ids": [2, 3, 6, 7, 8, 9], "type": "S6", "thickness": 0.01},
        ],
        "plot_grid": [[1, 2, 3], [4, 5, 6]],
        "plot_type": "flat",
    }
    model = build_fe_model_from_generated_geometry(generated, AnyStructureFEMConfig(include_beams=False))
    displacements = np.zeros(model.mesh.dof_manager.total_dofs, dtype=float)
    scalars = {int(node["id"]): float(node["id"]) for node in generated["nodes"]}

    visualization = runtime_fe_solver._visualization_from_full_result(generated, model, displacements, scalar_by_node=scalars)

    skin_surfaces = tuple(visualization.get("skin_shell_surfaces", ()) or ())
    assert [tuple(surface["node_ids"]) for surface in skin_surfaces] == [
        (1, 2, 5, 4),
        (2, 6, 5),
        (2, 7, 3, 8, 6, 9),
    ]
    assert tuple(visualization.get("shell_surfaces", ()) or ()) == ()


@pytest.mark.parametrize(("order", "expected_diag"), [("S3", "Generated S3 triangular shell elements."), ("S6", "Generated S6 triangular shell elements with shared midside nodes.")])
def test_anystructure_runtime_production_solver_runs_triangular_shell_orders(order: str, expected_diag: str) -> None:
    geometry = {
        "geometry": "flat panel",
        "length_m": 0.6,
        "width_m": 0.3,
        "thickness_m": 0.01,
        "has_stiffener": False,
        "has_girder": False,
    }
    result = runtime_fe_solver.run_production_fem(
        geometry,
        runtime_fe_solver.LightweightFEMConfig(
            mesh_fidelity="coarse",
            shell_element_order=order,
            pressure_pa=1000.0,
            num_buckling_modes=1,
        ),
    )

    assert result.status == "ok"
    assert result.mesh_info["shell_order"] == order
    assert expected_diag in result.diagnostics
    skin_surfaces = tuple(result.visualization.get("skin_shell_surfaces", ()) or ())
    assert skin_surfaces
    assert {len(surface["node_ids"]) for surface in skin_surfaces} == ({3} if order == "S3" else {6})

