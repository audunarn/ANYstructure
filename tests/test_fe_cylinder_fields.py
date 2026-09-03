"""Geometry tests for cylindrical FE field extraction."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from anystruct import fe_plate_fields
from anystruct.fe_plate_fields import (
    CylinderStress,
    FeShellModel,
    FrdStressResult,
    ShellElement,
    ShellSection,
    anystructure_input_for_cylinder_field,
    calculate_cylinder_buckling,
    create_fea_buckling_session,
    detect_cylinder_geometry,
    infer_cylinder_fields,
    reduce_cylinder_stresses,
)


CYLINDER_SAMPLE_INP = Path(r"C:\PrePoMax v2.5.1 dev\Temp\Analysis-cylinder-simple.inp")
CYLINDER_SAMPLE_FRD = Path(r"C:\PrePoMax v2.5.1 dev\Temp\Analysis-cylinder-simple.frd")


def _orthogonally_stiffened_cylinder() -> FeShellModel:
    nodes = {}
    elements = {}
    node_id = 1
    element_id = 1

    radius = 2.0
    length = 6.0
    circumferential_divisions = 64
    axial_divisions = 6

    skin_grid = {}
    for axial_index in range(axial_divisions + 1):
        z = length * axial_index / axial_divisions
        for angular_index in range(circumferential_divisions):
            angle = 2.0 * math.pi * angular_index / circumferential_divisions
            skin_grid[(axial_index, angular_index)] = node_id
            nodes[node_id] = (
                radius * math.cos(angle),
                radius * math.sin(angle),
                z,
            )
            node_id += 1

    for axial_index in range(axial_divisions):
        for angular_index in range(circumferential_divisions):
            next_angle = (angular_index + 1) % circumferential_divisions
            elements[element_id] = ShellElement(
                element_id=element_id,
                node_ids=(
                    skin_grid[(axial_index, angular_index)],
                    skin_grid[(axial_index, next_angle)],
                    skin_grid[(axial_index + 1, next_angle)],
                    skin_grid[(axial_index + 1, angular_index)],
                ),
                element_type="S4",
                elset="SKIN",
            )
            element_id += 1

    # Four longitudinal flat-bar webs.
    for angular_index in (0, 16, 32, 48):
        angle = 2.0 * math.pi * angular_index / circumferential_divisions
        for axial_index in range(axial_divisions):
            z0 = length * axial_index / axial_divisions
            z1 = length * (axial_index + 1) / axial_divisions
            web_nodes = []
            for local_radius, z in (
                (radius, z0),
                (radius - 0.2, z0),
                (radius - 0.2, z1),
                (radius, z1),
            ):
                nodes[node_id] = (
                    local_radius * math.cos(angle),
                    local_radius * math.sin(angle),
                    z,
                )
                web_nodes.append(node_id)
                node_id += 1
            elements[element_id] = ShellElement(
                element_id=element_id,
                node_ids=tuple(web_nodes),
                element_type="S4",
                elset="LONGITUDINALS",
            )
            element_id += 1

    # Two ring webs.
    for z in (2.0, 4.0):
        for angular_index in range(circumferential_divisions):
            angle0 = 2.0 * math.pi * angular_index / circumferential_divisions
            angle1 = 2.0 * math.pi * ((angular_index + 1) % circumferential_divisions) / circumferential_divisions
            ring_nodes = []
            for local_radius, angle in (
                (radius, angle0),
                (radius - 0.3, angle0),
                (radius - 0.3, angle1),
                (radius, angle1),
            ):
                nodes[node_id] = (
                    local_radius * math.cos(angle),
                    local_radius * math.sin(angle),
                    z,
                )
                ring_nodes.append(node_id)
                node_id += 1
            elements[element_id] = ShellElement(
                element_id=element_id,
                node_ids=tuple(ring_nodes),
                element_type="S4",
                elset="RINGS",
            )
            element_id += 1

    elsets = {
        "ALL": tuple(sorted(elements)),
        "SKIN": tuple(element_id for element_id, element in elements.items() if element.elset == "SKIN"),
        "LONGITUDINALS": tuple(
            element_id for element_id, element in elements.items() if element.elset == "LONGITUDINALS"
        ),
        "RINGS": tuple(element_id for element_id, element in elements.items() if element.elset == "RINGS"),
    }
    return FeShellModel(
        nodes=nodes,
        shell_elements=elements,
        elsets=elsets,
        shell_sections=(ShellSection(elset="ALL", material="S355", thickness_m=0.01),),
    )


def _global_stress_components_from_local(first_axis, second_axis, sigma_first, sigma_second, tau):
    third_axis = (
        first_axis[1] * second_axis[2] - first_axis[2] * second_axis[1],
        first_axis[2] * second_axis[0] - first_axis[0] * second_axis[2],
        first_axis[0] * second_axis[1] - first_axis[1] * second_axis[0],
    )
    tensor = [[0.0, 0.0, 0.0] for _ in range(3)]
    for first, second, value in (
        (first_axis, first_axis, sigma_first),
        (second_axis, second_axis, sigma_second),
        (first_axis, second_axis, tau),
        (second_axis, first_axis, tau),
        (third_axis, third_axis, 0.0),
    ):
        for row in range(3):
            for col in range(3):
                tensor[row][col] += value * first[row] * second[col]
    return (
        tensor[0][0],
        tensor[1][1],
        tensor[2][2],
        tensor[0][1],
        tensor[1][2],
        tensor[2][0],
    )


def _flat_stiffened_panel_model() -> FeShellModel:
    """Small flat panel with webs/flanges that lures a degenerate circle fit."""

    nodes = {}
    elements = {}
    node_id = 1
    element_id = 1

    def add_node(x: float, y: float, z: float) -> int:
        nonlocal node_id
        nodes[node_id] = (x, y, z)
        node_id += 1
        return node_id - 1

    def add_quad(corners, elset: str) -> None:
        nonlocal element_id
        elements[element_id] = ShellElement(
            element_id=element_id,
            node_ids=tuple(add_node(*corner) for corner in corners),
            element_type="S4",
            elset=elset,
        )
        element_id += 1

    for x0 in (0.0, 1.0):
        for y0 in (0.0, 0.7):
            add_quad(
                ((x0, y0, 0.0), (x0 + 1.0, y0, 0.0), (x0 + 1.0, y0 + 0.7, 0.0), (x0, y0 + 0.7, 0.0)),
                "BASE",
            )
    for y_station in (0.0, 0.7, 1.4):
        add_quad(
            ((0.0, y_station, 0.0), (2.0, y_station, 0.0), (2.0, y_station, 0.2), (0.0, y_station, 0.2)),
            "WEBS",
        )
        add_quad(
            ((0.0, y_station - 0.05, 0.2), (2.0, y_station - 0.05, 0.2), (2.0, y_station + 0.05, 0.2), (0.0, y_station + 0.05, 0.2)),
            "FLANGES",
        )

    return FeShellModel(
        nodes=nodes,
        shell_elements=elements,
        elsets={"ALL": tuple(sorted(elements))},
        shell_sections=(ShellSection(elset="ALL", material="S355", thickness_m=0.01),),
    )


def test_detects_cylinder_axis_and_radius() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)

    assert geometry.radius_m == pytest.approx(2.0, abs=1.0e-8)
    assert abs(geometry.axis_direction[2]) == pytest.approx(1.0, abs=1.0e-8)
    assert len(geometry.skin_element_ids) == 64 * 6


def test_cylinder_detection_requires_angular_coverage() -> None:
    # A full cylinder is detected while a small flat stiffened panel is not,
    # even when a large-radius circle fits its few radial positions with a
    # near-zero residual.
    assert fe_plate_fields.is_cylindrical_shell_model(_orthogonally_stiffened_cylinder()) is True
    assert fe_plate_fields.is_cylindrical_shell_model(_flat_stiffened_panel_model()) is False


def _coarse_skin_only_cylinder(circumferential_divisions: int) -> FeShellModel:
    """Full closed cylinder skin meshed with few circumferential elements."""

    nodes = {}
    elements = {}
    node_id = 1
    element_id = 1
    radius = 1.0
    length = 4.0
    axial_divisions = 8

    skin_grid = {}
    for axial_index in range(axial_divisions + 1):
        z = length * axial_index / axial_divisions
        for angular_index in range(circumferential_divisions):
            angle = 2.0 * math.pi * angular_index / circumferential_divisions
            skin_grid[(axial_index, angular_index)] = node_id
            nodes[node_id] = (radius * math.cos(angle), radius * math.sin(angle), z)
            node_id += 1

    for axial_index in range(axial_divisions):
        for angular_index in range(circumferential_divisions):
            next_angle = (angular_index + 1) % circumferential_divisions
            elements[element_id] = ShellElement(
                element_id=element_id,
                node_ids=(
                    skin_grid[(axial_index, angular_index)],
                    skin_grid[(axial_index, next_angle)],
                    skin_grid[(axial_index + 1, next_angle)],
                    skin_grid[(axial_index + 1, angular_index)],
                ),
                element_type="S4",
                elset="SKIN",
            )
            element_id += 1

    return FeShellModel(
        nodes=nodes,
        shell_elements=elements,
        elsets={"ALL": tuple(sorted(elements)), "SKIN": tuple(sorted(elements))},
        shell_sections=(ShellSection(elset="ALL", material="S355", thickness_m=0.01),),
    )


def test_cylinder_detection_is_mesh_resolution_independent() -> None:
    # Regression: a full cylinder meshed with fewer circumferential elements
    # than the old fixed bin count (72) was mis-detected as a flat plate, so
    # SESAM/CalculiX cylinders imported as flat panels. Coverage is now the
    # angular range spanned by the skin, independent of mesh resolution.
    for circumferential_divisions in (12, 20, 32, 48):
        model = _coarse_skin_only_cylinder(circumferential_divisions)
        assert fe_plate_fields.is_cylindrical_shell_model(model) is True, (
            f"cylinder with {circumferential_divisions} circumferential elements "
            "should be detected as cylindrical"
        )


_REF_CYLINDER_SIF = Path(__file__).resolve().parents[1] / "ref_Cases" / "allQuadLinear_cylinder_multiple_LCs.SIF"


@pytest.mark.skipif(not _REF_CYLINDER_SIF.exists(), reason="reference cylinder SIF not available")
def test_reference_cylinder_sif_is_detected_as_cylinder() -> None:
    # The exact user-reported file: a coarse-mesh SESAM cylinder that used to
    # slip through detection and import as flat plates.
    model = fe_plate_fields.read_fea_shell_model(str(_REF_CYLINDER_SIF))
    assert fe_plate_fields.is_cylindrical_shell_model(model) is True


def test_extracts_orthogonal_cylinder_bays() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)
    fields = infer_cylinder_fields(model, geometry)

    # 4 angular bays x 3 axial bays.
    assert len(fields) == 12
    assert all(field.element_ids for field in fields)
    assert all(field.radius_m == pytest.approx(2.0) for field in fields)

    members = {
        member.member_id: member
        for field in fields
        for member in field.members
    }
    roles = [member.role for member in members.values()]
    assert roles.count("longitudinal_stiffener") == 4
    assert roles.count("ring_stiffener") == 2


def test_orthogonal_cylinder_uses_ring_stiffener_as_frame_for_calculation() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)
    fields = infer_cylinder_fields(model, geometry)
    field = fields[0]
    stress = CylinderStress(
        field_id=field.field_id,
        axial_stress_mpa=-0.2,
        hoop_stress_mpa=-20.0,
        torsional_shear_mpa=0.1,
        transverse_shear_mpa=0.0,
        sample_count=1,
        reduction="test",
    )

    input_data = anystructure_input_for_cylinder_field(field, stress)
    results = calculate_cylinder_buckling([field], [stress])

    assert input_data["calculation_domain"] == "Orthogonally Stiffened shell"
    assert input_data["ring_stiffener"] is None
    assert input_data["ring_frame"]["source_member_id"].startswith("ring_stiffener_")
    assert results[0]["available"] is True
    assert results[0].get("error") is None
    assert results[0]["result"]["Heavy ring frame"] is not None


def test_cylinder_can_run_semi_analytical_as_equivalent_flat_panel_with_warning() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)
    fields = infer_cylinder_fields(model, geometry)
    stress = CylinderStress(
        field_id=fields[0].field_id,
        axial_stress_mpa=-12.0,
        hoop_stress_mpa=-34.0,
        torsional_shear_mpa=7.0,
        transverse_shear_mpa=0.0,
        sample_count=4,
        reduction="test",
    )

    results = calculate_cylinder_buckling(
        [fields[0]],
        [stress],
        calculation_method="SemiAnalytical S3/U3",
        buckling_acceptance="ultimate",
    )

    assert results[0]["domain"] == "Equivalent flat panel from cylindrical shell"
    assert results[0]["calculation_method"] == "SemiAnalytical S3/U3"
    assert "flat plate/stiffened-panel checks" in results[0]["cylinder_method_warning"]
    assert results[0]["stress"]["sigma_x1_mpa"] == pytest.approx(12.0)
    assert results[0]["stress"]["sigma_y1_mpa"] == pytest.approx(34.0)
    assert results[0]["stress"]["tau_xy_mpa"] == pytest.approx(7.0)
    assert "result" in results[0] or "error" in results[0]


def test_cylinder_can_route_ml_numeric_as_equivalent_flat_panel_with_warning() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)
    fields = infer_cylinder_fields(model, geometry)
    stress = CylinderStress(
        field_id=fields[0].field_id,
        axial_stress_mpa=-12.0,
        hoop_stress_mpa=-34.0,
        torsional_shear_mpa=7.0,
        transverse_shear_mpa=0.0,
        sample_count=4,
        reduction="test",
    )

    results = calculate_cylinder_buckling(
        [fields[0]],
        [stress],
        calculation_method="ML-Numeric (PULS based)",
        buckling_acceptance="buckling",
        ml_algo={},
    )

    assert results[0]["domain"] == "Equivalent flat panel from cylindrical shell"
    assert results[0]["calculation_method"] == "ML-Numeric (PULS based)"
    assert "flat plate/stiffened-panel checks" in results[0]["cylinder_method_warning"]
    assert results[0]["available"] is False
    assert "Missing numeric ML model" in results[0]["error"]


def test_cylinder_stresses_are_projected_to_axial_and_circumferential_axes() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)
    fields = infer_cylinder_fields(model, geometry)
    nodal_stress = {}
    for node_id, point in model.nodes.items():
        radial = fe_plate_fields._normalise(
            fe_plate_fields._radial_vector(point, geometry.axis_origin, geometry.axis_direction)
        )
        circumferential = fe_plate_fields._normalise(fe_plate_fields._cross(geometry.axis_direction, radial))
        nodal_stress[node_id] = _global_stress_components_from_local(
            geometry.axis_direction,
            circumferential,
            sigma_first=-12.0e6,
            sigma_second=-34.0e6,
            tau=7.0e6,
        )
    frd_stress = FrdStressResult(
        path="synthetic",
        nodes=model.nodes,
        element_nodes={
            element_id: element.corner_node_ids
            for element_id, element in model.shell_elements.items()
        },
        components=("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"),
        nodal_stress=nodal_stress,
    )

    cylinder_stresses = reduce_cylinder_stresses(model, geometry, fields[:1], frd_stress)
    panel_input = anystructure_input_for_cylinder_field(fields[0], cylinder_stresses[0])

    assert len(cylinder_stresses) == 1
    assert cylinder_stresses[0].axial_stress_mpa == pytest.approx(-12.0)
    assert cylinder_stresses[0].hoop_stress_mpa == pytest.approx(-34.0)
    assert cylinder_stresses[0].torsional_shear_mpa == pytest.approx(7.0)
    assert cylinder_stresses[0].reduction == "CSR area weighted membrane mean in axial/circumferential axes"
    assert panel_input["stresses"]["sasd_mpa"] == pytest.approx(-12.0)
    assert panel_input["stresses"]["shsd_mpa"] == pytest.approx(-34.0)
    assert panel_input["stresses"]["tTsd_mpa"] == pytest.approx(7.0)

    nodal_stresses = reduce_cylinder_stresses(
        model,
        geometry,
        fields[:1],
        frd_stress,
        stress_reduction_method="Whole panel nodal mean",
    )
    assert nodal_stresses[0].reduction == "whole-panel nodal membrane mean in axial/circumferential axes"


def test_cylinder_panel_3d_records_include_local_axes() -> None:
    model = _orthogonally_stiffened_cylinder()
    geometry = detect_cylinder_geometry(model)
    fields = infer_cylinder_fields(model, geometry)

    records = fe_plate_fields.panel_3d_records(model, fields[:1])

    assert records
    assert records[0]["local_x"] == pytest.approx(geometry.axis_direction)
    assert fe_plate_fields._length(records[0]["local_y"]) == pytest.approx(1.0)


@pytest.mark.skipif(
    not (CYLINDER_SAMPLE_INP.exists() and CYLINDER_SAMPLE_FRD.exists()),
    reason="Provided PrePoMax cylinder sample is not available",
)
@pytest.mark.fem_integration
def test_provided_prepomax_cylinder_import_calculates_panel_ufs() -> None:
    session = create_fea_buckling_session(CYLINDER_SAMPLE_INP, CYLINDER_SAMPLE_FRD, run_buckling=True)

    assert session.summary()["geometry_type"] == "cylinder"
    assert session.panel_count == 84
    assert session.field_count == 84
    assert session.geometry.radius_m == pytest.approx(5.0, abs=5.0e-5)
    assert session.geometry.skin_thickness_m == pytest.approx(0.015)
    assert len(session.usage_factors()) == session.panel_count
    assert all(panel.buckling_result["available"] is True for panel in session.panels)
    assert session.panels[0].usage_factor == pytest.approx(0.511746358910791)
