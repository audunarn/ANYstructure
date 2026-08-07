"""Infer flat and cylindrical stiffened fields from FE shell models.

Flat structures are interpreted from connected coplanar patches. Cylindrical
structures use a separate best-fit axis/radius pipeline, preserve periodic
circumferential topology, and infer longitudinal stiffeners plus ring
stiffeners/frames from local shell orientation. CalculiX FRD and SESAM SIF
stresses can be projected to either flat panel axes or local
axial/circumferential cylinder axes.
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Sequence


Point3D = tuple[float, float, float]
Vector3D = tuple[float, float, float]

STRESS_REDUCTION_METHODS: tuple[str, ...] = (
    "CSR area weighted mean",
    "Whole panel nodal mean",
    "Centre strip mean",
)

_STRESS_REDUCTION_METHOD_ALIASES = {
    "csr": "CSR area weighted mean",
    "csr area mean": "CSR area weighted mean",
    "csr area average": "CSR area weighted mean",
    "csr area weighted": "CSR area weighted mean",
    "csr area weighted mean": "CSR area weighted mean",
    "area": "CSR area weighted mean",
    "area weighted": "CSR area weighted mean",
    "area weighted mean": "CSR area weighted mean",
    "nodal": "Whole panel nodal mean",
    "nodal mean": "Whole panel nodal mean",
    "whole panel nodal mean": "Whole panel nodal mean",
    "whole panel mean": "Whole panel nodal mean",
    "centre strip": "Centre strip mean",
    "centre strip mean": "Centre strip mean",
    "center strip": "Centre strip mean",
    "center strip mean": "Centre strip mean",
    "line": "Centre strip mean",
    "line mean": "Centre strip mean",
}


@dataclass(frozen=True)
class ShellElement:
    """One shell element from a CalculiX input deck."""

    element_id: int
    node_ids: tuple[int, ...]
    element_type: str = ""
    elset: str | None = None

    @property
    def corner_node_ids(self) -> tuple[int, ...]:
        element_type = self.element_type.upper()
        # SESAM Q8/SCQS and T6/SCTS number nodes around the perimeter with
        # corners and midside nodes alternating; CalculiX S8/S8R and S6 list
        # the corner nodes first.
        if element_type.startswith("Q8") and len(self.node_ids) >= 8:
            return (self.node_ids[0], self.node_ids[2], self.node_ids[4], self.node_ids[6])
        if element_type.startswith("T6") and len(self.node_ids) >= 6:
            return (self.node_ids[0], self.node_ids[2], self.node_ids[4])
        if element_type.startswith("S8") and len(self.node_ids) >= 4:
            return self.node_ids[:4]
        if element_type.startswith(("S6", "T6")) and len(self.node_ids) >= 3:
            return self.node_ids[:3]
        return self.node_ids[:4]


@dataclass(frozen=True)
class FeBeamElement:
    """One beam element carried alongside shell geometry for panel inference."""

    element_id: int
    node_ids: tuple[int, ...]
    element_type: str = ""
    property_id: int | None = None
    material_id: int | None = None
    cross_section: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ShellSection:
    """Shell-section metadata from ``*Shell section`` cards."""

    elset: str | None
    material: str | None
    thickness_m: float | None
    offset: str | None = None


@dataclass(frozen=True)
class FeShellModel:
    """Parsed shell model used by the plate-field interpreter."""

    nodes: dict[int, Point3D]
    shell_elements: dict[int, ShellElement]
    beam_elements: dict[int, FeBeamElement] = field(default_factory=dict)
    elsets: dict[str, tuple[int, ...]] = field(default_factory=dict)
    shell_sections: tuple[ShellSection, ...] = ()
    source_path: str | None = None


@dataclass(frozen=True)
class FrdStressResult:
    """Expanded CalculiX FRD shell result data needed for stress reduction."""

    path: str
    nodes: dict[int, Point3D]
    element_nodes: dict[int, tuple[int, ...]]
    components: tuple[str, ...]
    nodal_stress: dict[int, tuple[float, ...]]
    units: str = "Pa"
    element_stress: dict[int, tuple[float, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class SurfacePatch:
    """A connected coplanar shell-element component."""

    patch_id: str
    element_ids: tuple[int, ...]
    normal: Vector3D
    offset: float
    bbox: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    area: float
    centroid: Point3D


@dataclass(frozen=True)
class InferredMember:
    """A shell-plate web and optional flange interpreted as one member."""

    member_id: str
    role: str
    section_type: str
    web_patch_id: str
    flange_patch_id: str | None
    direction: Vector3D
    station: float
    web_height_m: float
    flange_width_m: float | None
    web_thickness_m: float | None = None
    flange_thickness_m: float | None = None
    thickness_source: str | None = None
    run_length_m: float = 0.0
    confidence: float = 1.0
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlateField:
    """One inferred plate bay between adjacent stiffener/girder web lines."""

    field_id: str
    base_patch_id: str
    element_ids: tuple[int, ...]
    bbox: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    span_m: float
    spacing_m: float
    transverse_bounds: tuple[float, float]
    attached_member_ids: tuple[str, ...]
    members: tuple[InferredMember, ...] = ()
    shell_section_thickness_m: float | None = None
    confidence: float = 1.0
    diagnostics: tuple[str, ...] = ()
    # In-plane axes fixed at inference time so stress reduction uses the same
    # frame as span/spacing/transverse_bounds: sigma_x acts along
    # span_direction (the stiffener direction when stiffeners exist) and
    # transverse_bounds is measured along transverse_direction.
    span_direction: Vector3D | None = None
    transverse_direction: Vector3D | None = None


@dataclass(frozen=True)
class PanelStress:
    """PULS/ANYstructure stress input reduced from FE nodal stresses."""

    field_id: str
    sigma_x1_mpa: float
    sigma_x2_mpa: float
    sigma_y1_mpa: float
    sigma_y2_mpa: float
    tau_xy_mpa: float
    sample_count: int
    reduction: str
    source_units: str = "Pa"
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeaBucklingPanel:
    """One GUI/API selectable buckling panel discovered from FE results."""

    field_id: str
    field: PlateField
    stress: PanelStress | None
    anystructure_input: dict[str, Any]
    plot_bounds: tuple[float, float, float, float]
    buckling_result: dict[str, Any] | None = None
    usage_factor: float | None = None


@dataclass(frozen=True)
class FeaBucklingSession:
    """Complete FE-result buckling import used by both API and GUI workflows."""

    inp_path: str
    frd_path: str | None
    model: FeShellModel
    fields: tuple[PlateField, ...]
    panels: tuple[FeaBucklingPanel, ...]
    frd_summary: dict[str, Any] | None = None
    diagnostics: tuple[str, ...] = ()
    active_load_case: int | None = None

    @property
    def load_cases(self) -> tuple[int, ...]:
        if self.frd_summary and "load_cases" in self.frd_summary:
            return tuple(self.frd_summary["load_cases"])
        return ()

    @property
    def load_case_names(self) -> dict[int, str]:
        if self.frd_summary and "load_case_names" in self.frd_summary:
            return dict(self.frd_summary["load_case_names"])
        return {}

    @property
    def field_count(self) -> int:
        return len(self.fields)

    @property
    def panel_count(self) -> int:
        return len(self.panels)

    def panel(self, field_id: str) -> FeaBucklingPanel:
        for panel in self.panels:
            if panel.field_id == field_id:
                return panel
        raise KeyError(field_id)

    def usage_factors(self) -> dict[str, float]:
        return {
            panel.field_id: panel.usage_factor
            for panel in self.panels
            if panel.usage_factor is not None
        }

    def summary(self) -> dict[str, Any]:
        payload = _summary_payload(self.model, self.fields, self.frd_summary)
        payload["inp_path"] = self.inp_path
        payload["frd_path"] = self.frd_path
        surface_records = {record["field_id"]: record for record in panel_3d_records(self.model, self.fields)}
        payload["panels"] = [
            {
                "field_id": panel.field_id,
                "plot_bounds": list(panel.plot_bounds),
                "surface_3d": surface_records.get(panel.field_id),
                "usage_factor": panel.usage_factor,
                "anystructure_input": panel.anystructure_input,
                "stress": None if panel.stress is None else summarize_panel_stresses([panel.stress])[0],
                "buckling_result": panel.buckling_result,
            }
            for panel in self.panels
        ]
        payload["diagnostics"] = list(self.diagnostics)
        return payload


@dataclass(frozen=True)
class _PatchInference:
    base_patch: SurfacePatch
    members: tuple[InferredMember, ...]
    stiffeners: tuple[InferredMember, ...]
    girders: tuple[InferredMember, ...]
    base_normal: Vector3D
    member_direction: Vector3D
    transverse_direction: Vector3D


def available_stress_reduction_methods() -> tuple[str, ...]:
    """Return the supported FE-to-buckling-panel stress reduction methods."""

    return STRESS_REDUCTION_METHODS


def normalize_stress_reduction_method(method: str | None) -> str:
    """Normalize a public stress-reduction method label or shorthand."""

    if method is None:
        return STRESS_REDUCTION_METHODS[0]
    text = str(method).strip()
    if text in STRESS_REDUCTION_METHODS:
        return text
    normalized = _STRESS_REDUCTION_METHOD_ALIASES.get(text.lower())
    if normalized is None:
        raise ValueError(
            "stress_reduction_method must be one of: "
            + ", ".join(STRESS_REDUCTION_METHODS)
        )
    return normalized


def read_calculix_inp(path: str | os.PathLike[str]) -> FeShellModel:
    """Read shell nodes/elements, elsets, and shell-section metadata from ``.inp``."""

    path = str(path)
    nodes: dict[int, Point3D] = {}
    shell_elements: dict[int, ShellElement] = {}
    elsets: dict[str, list[int]] = {}
    shell_sections: list[ShellSection] = []

    mode: str | None = None
    attrs: dict[str, str | bool] = {}
    pending_shell_section: dict[str, str | None] | None = None

    with open(path, "r", encoding="utf-8", errors="ignore") as inp_file:
        for raw_line in inp_file:
            line = raw_line.strip()
            if not line or line.startswith("**"):
                continue

            if line.startswith("*"):
                mode = None
                attrs = _parse_keyword_attributes(line)
                keyword = _keyword_name(line)
                pending_shell_section = None
                if keyword == "node":
                    mode = "node"
                elif keyword == "element":
                    mode = "element"
                elif keyword == "elset":
                    mode = "elset"
                    name = str(attrs.get("elset", "")).strip()
                    if name:
                        elsets.setdefault(name, [])
                elif keyword == "shell section":
                    mode = "shell_section"
                    pending_shell_section = {
                        "elset": _optional_attr(attrs, "elset"),
                        "material": _optional_attr(attrs, "material"),
                        "offset": _optional_attr(attrs, "offset"),
                    }
                continue

            if mode == "node":
                parts = _csv_parts(line)
                if len(parts) >= 4:
                    nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif mode == "element":
                parts = _csv_parts(line)
                if len(parts) >= 4:
                    element_id = int(parts[0])
                    element_type = str(attrs.get("type", ""))
                    elset = _optional_attr(attrs, "elset")
                    shell_elements[element_id] = ShellElement(
                        element_id=element_id,
                        node_ids=tuple(int(item) for item in parts[1:]),
                        element_type=element_type,
                        elset=elset,
                    )
                    if elset:
                        elsets.setdefault(elset, []).append(element_id)
            elif mode == "elset":
                name = str(attrs.get("elset", "")).strip()
                if not name:
                    continue
                values = [int(float(part)) for part in _csv_parts(line)]
                if "generate" in attrs and len(values) >= 2:
                    step = values[2] if len(values) >= 3 else 1
                    elsets.setdefault(name, []).extend(range(values[0], values[1] + 1, step))
                else:
                    elsets.setdefault(name, []).extend(values)
            elif mode == "shell_section" and pending_shell_section is not None:
                parts = _csv_parts(line)
                thickness = _safe_float(parts[0]) if parts else None
                shell_sections.append(
                    ShellSection(
                        elset=pending_shell_section.get("elset"),
                        material=pending_shell_section.get("material"),
                        offset=pending_shell_section.get("offset"),
                        thickness_m=thickness,
                    )
                )
                pending_shell_section = None
                mode = None

    return FeShellModel(
        nodes=nodes,
        shell_elements=shell_elements,
        elsets={name: tuple(values) for name, values in elsets.items()},
        shell_sections=tuple(shell_sections),
        source_path=path,
    )


def read_calculix_frd_summary(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Return lightweight metadata and result-block discovery for a CalculiX ``.frd`` file."""

    path = str(path)
    result_blocks: list[dict[str, Any]] = []
    current_block: dict[str, Any] | None = None
    current_step: int | None = None
    node_count: int | None = None
    material_names: list[str] = []

    with open(path, "r", encoding="utf-8", errors="ignore") as frd_file:
        for line_number, raw_line in enumerate(frd_file, start=1):
            line = raw_line.rstrip("\n")
            stripped = line.strip()
            if stripped.startswith("1PSTEP"):
                numbers = [int(value) for value in re.findall(r"[-+]?\d+", stripped)]
                current_step = numbers[0] if numbers else None
            elif stripped.startswith("2C") and node_count is None:
                numbers = [int(value) for value in re.findall(r"[-+]?\d+", stripped[2:])]
                if numbers:
                    node_count = numbers[0]
            elif stripped.startswith("1UMAT"):
                name = stripped[5:].strip()
                if name:
                    material_names.append(name)
            elif stripped.startswith("-4"):
                parts = stripped.split()
                if len(parts) >= 2:
                    current_block = {
                        "name": parts[1],
                        "step": current_step,
                        "line_number": line_number,
                        "components": [],
                    }
                    result_blocks.append(current_block)
            elif stripped.startswith("-5") and current_block is not None:
                parts = stripped.split()
                if len(parts) >= 2:
                    current_block["components"].append(parts[1])

    return {
        "path": path,
        "file_size": os.path.getsize(path),
        "node_count": node_count,
        "materials": material_names,
        "result_blocks": result_blocks,
    }


def read_calculix_frd_stress(path: str | os.PathLike[str], load_case: int | None = None) -> FrdStressResult:
    """Read expanded FRD nodes/connectivity and the first ``STRESS`` result block."""

    path = str(path)
    nodes: dict[int, Point3D] = {}
    element_nodes: dict[int, tuple[int, ...]] = {}
    components: list[str] = []
    nodal_stress: dict[int, tuple[float, ...]] = {}

    mode: str | None = None
    current_element_id: int | None = None
    current_element_nodes: list[int] = []

    def finish_element() -> None:
        nonlocal current_element_id, current_element_nodes
        if current_element_id is not None:
            element_nodes[current_element_id] = tuple(current_element_nodes)
        current_element_id = None
        current_element_nodes = []

    with open(path, "r", encoding="utf-8", errors="ignore") as frd_file:
        for raw_line in frd_file:
            stripped = raw_line.strip()
            if not stripped:
                continue

            if stripped.startswith("2C"):
                finish_element()
                mode = "nodes"
                continue
            if stripped.startswith("3C"):
                finish_element()
                mode = "elements"
                continue
            if stripped.startswith("-4"):
                finish_element()
                parts = stripped.split()
                mode = "stress_header" if len(parts) >= 2 and parts[1].upper() == "STRESS" else None
                if mode == "stress_header":
                    components = []
                continue
            if stripped.startswith("-3"):
                finish_element()
                mode = None
                continue

            if mode == "nodes" and stripped.startswith("-1"):
                values = _frd_numbers_after_marker(raw_line)
                if len(values) >= 4:
                    nodes[int(values[0])] = (float(values[1]), float(values[2]), float(values[3]))
            elif mode == "elements" and stripped.startswith("-1"):
                finish_element()
                values = _frd_numbers_after_marker(raw_line)
                if values:
                    current_element_id = int(values[0])
            elif mode == "elements" and stripped.startswith("-2"):
                values = _frd_numbers_after_marker(raw_line)
                current_element_nodes.extend(int(value) for value in values)
            elif mode == "stress_header" and stripped.startswith("-5"):
                parts = stripped.split()
                if len(parts) >= 2:
                    components.append(parts[1].upper())
            elif mode in {"stress_header", "stress_data"} and stripped.startswith("-1"):
                mode = "stress_data"
                values = _frd_numbers_after_marker(raw_line)
                if len(values) >= 1 + len(components):
                    node_id = int(values[0])
                    nodal_stress[node_id] = tuple(float(value) for value in values[1 : 1 + len(components)])

    return FrdStressResult(
        path=path,
        nodes=nodes,
        element_nodes=element_nodes,
        components=tuple(components),
        nodal_stress=nodal_stress,
    )


def _path_suffix(path: str | os.PathLike[str] | None) -> str:
    return "" if path is None else Path(str(path)).suffix.lower()


def _is_sesam_model_path(path: str | os.PathLike[str] | None) -> bool:
    return _path_suffix(path) in {".fem", ".sif"}


def _is_sesam_result_path(path: str | os.PathLike[str] | None) -> bool:
    return _path_suffix(path) == ".sif"


def _paired_sesam_sif_path(path: str | os.PathLike[str]) -> str | None:
    source = Path(str(path))
    if source.suffix.lower() != ".fem":
        return None
    for suffix in (".SIF", ".sif"):
        candidate = source.with_suffix(suffix)
        if candidate.exists():
            return str(candidate)
    return None


def _default_fea_result_path(
    inp_path: str | os.PathLike[str],
    frd_path: str | os.PathLike[str] | None,
) -> str | None:
    if frd_path is not None:
        return str(frd_path)
    if _is_sesam_result_path(inp_path):
        return str(inp_path)
    if _path_suffix(inp_path) == ".fem":
        return _paired_sesam_sif_path(inp_path)
    return None


def read_sesam_shell_model(path: str | os.PathLike[str]) -> FeShellModel:
    """Read SESAM FEM/SIF shell geometry into the FE-results interpreter model."""

    from anyfileio.sesam import beam_section, get_element_spec, read_sesam_fem_document

    path_text = str(path)
    document = read_sesam_fem_document(path_text, strict=False)

    shell_elements: dict[int, ShellElement] = {}
    elsets: dict[str, list[int]] = defaultdict(list)
    section_by_elset: dict[str, ShellSection] = {}
    beam_elements: dict[int, FeBeamElement] = {}

    for element in document.elements.values():
        spec = get_element_spec(element.type_code)
        if spec is None:
            continue

        material_id = element.material_id if element.material_id is not None else 0
        section_id = element.section_id if element.section_id is not None else 0

        if spec.is_shell:
            elset = f"sesam_shell_{spec.name.lower()}_prop_{section_id}_mat_{material_id}"
            shell_elements[element.element_id] = ShellElement(
                element_id=element.element_id,
                node_ids=element.node_ids,
                element_type=spec.name,
                elset=elset,
            )
            elsets[elset].append(element.element_id)
            if elset not in section_by_elset:
                thickness = None
                if element.section_id is not None:
                    section = document.sections.get(element.section_id)
                    if section is not None and section.thickness is not None and section.thickness > 0.0:
                        thickness = float(section.thickness)
                if thickness is None and document.sections:
                    for s in document.sections.values():
                        if s.thickness is not None and s.thickness > 0.0:
                            thickness = float(s.thickness)
                            break
                if thickness is None:
                    thickness = 0.01
                section_by_elset[elset] = ShellSection(
                    elset=elset,
                    material=f"sesam_material_{material_id}" if material_id else None,
                    thickness_m=thickness,
                )
        elif spec.is_beam:
            cross_section = beam_section(document.sections.get(section_id))
            beam_elements[element.element_id] = FeBeamElement(
                element_id=element.element_id,
                node_ids=element.node_ids,
                element_type=spec.name,
                property_id=section_id,
                material_id=material_id,
                cross_section=cross_section,
            )

    return FeShellModel(
        nodes={node_id: tuple(node.coordinates) for node_id, node in document.nodes.items()},
        shell_elements=shell_elements,
        beam_elements=beam_elements,
        elsets={name: tuple(values) for name, values in elsets.items()},
        shell_sections=tuple(section_by_elset.values()),
        source_path=path_text,
    )


def read_sesam_sif_stress_result(path: str | os.PathLike[str], load_case: int | None = None) -> FrdStressResult:
    """Read SESAM SIF RVSTRESS as the FRD-like stress object used here."""

    from anyfileio.sesam import read_sesam_sif_stress

    stress = read_sesam_sif_stress(path, load_case=load_case)
    return FrdStressResult(
        path=stress.path,
        nodes=dict(stress.nodes),
        element_nodes=dict(stress.element_nodes),
        components=tuple(stress.components),
        nodal_stress=dict(stress.nodal_stress),
        units=stress.units,
        element_stress=dict(stress.element_stress),
    )


@functools.lru_cache(maxsize=4)
def _cached_read_fea_shell_model(path: str) -> FeShellModel:
    if _is_sesam_model_path(path):
        return read_sesam_shell_model(path)
    return read_calculix_inp(path)


def read_fea_shell_model(path: str | os.PathLike[str]) -> FeShellModel:
    """Read a supported FE shell model: CalculiX INP or SESAM FEM/SIF."""
    return _cached_read_fea_shell_model(str(path))


@functools.lru_cache(maxsize=4)
def _cached_read_fea_result_summary(path: str) -> dict[str, Any]:
    if _is_sesam_result_path(path):
        from anyfileio.sesam import read_sesam_sif_summary

        return read_sesam_sif_summary(path)
    return read_calculix_frd_summary(path)


def read_fea_result_summary(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Return lightweight result metadata for FRD or SIF files."""
    return _cached_read_fea_result_summary(str(path))


@functools.lru_cache(maxsize=16)
def _cached_read_fea_stress(path: str, load_case: int | None) -> FrdStressResult:
    if _is_sesam_result_path(path):
        return read_sesam_sif_stress_result(path, load_case=load_case)
    return read_calculix_frd_stress(path, load_case=load_case)


def read_fea_stress(path: str | os.PathLike[str], load_case: int | None = None) -> FrdStressResult:
    """Read supported FE stress results: CalculiX FRD or SESAM SIF."""
    return _cached_read_fea_stress(str(path), load_case)


def reduce_field_stresses(
    model: FeShellModel,
    fields: Sequence[PlateField],
    frd_stress: FrdStressResult,
    *,
    transverse_edge_fraction: float = 0.2,
    stress_reduction_method: str | None = None,
    centre_strip_fraction: float = 0.25,
) -> list[PanelStress]:
    """Reduce FRD shell stresses to one ANYstructure/PULS stress set per field.

    The default method follows the CSR/PULS-style recommendation to use area
    weighted average membrane stresses over the finite elements of the panel.
    Alternative methods are offered for sensitivity checks.  CalculiX stresses
    are interpreted as tension-positive Pa; returned normal stresses are
    compression-positive MPa.
    """

    reduction_method = normalize_stress_reduction_method(stress_reduction_method)
    patches = detect_surface_patches(model)
    if not patches:
        return []
    inference = _infer_members_from_patches(model, patches)
    base_normal = inference.base_normal
    base_offset = inference.base_patch.offset
    default_member_direction = inference.member_direction
    default_transverse_direction = inference.transverse_direction
    use_field_axes = _is_sesam_model_path(model.source_path)

    panel_stresses: list[PanelStress] = []
    for field_item in fields:
        has_stored_axes = (
            field_item.span_direction is not None
            and field_item.transverse_direction is not None
        )
        if has_stored_axes:
            # Use the axes fixed at field-inference time so sigma_x follows the
            # span/stiffener direction and the centre-strip filter compares
            # coordinates against transverse_bounds in the same frame.
            member_direction = field_item.span_direction
            transverse_direction = field_item.transverse_direction
        if use_field_axes:
            if not has_stored_axes:
                member_direction, transverse_direction = _field_local_axes(model, field_item)
            field_normal = _field_representative_normal(model, field_item)
            field_points = [
                point
                for polygon in _field_element_polygons(model, field_item)
                for point in polygon
            ]
            field_centroid = _mean_point(field_points)
            stress_base_normal = field_normal
            stress_base_offset = _dot(field_centroid, field_normal)
        else:
            if not has_stored_axes:
                member_direction = default_member_direction
                transverse_direction = default_transverse_direction
            stress_base_normal = base_normal
            stress_base_offset = base_offset
        if reduction_method == "CSR area weighted mean":
            samples = _field_element_stress_samples(
                model,
                field_item,
                frd_stress,
                member_direction,
                transverse_direction,
            )
        else:
            samples = _field_stress_samples(
                field_item,
                frd_stress,
                stress_base_normal,
                stress_base_offset,
                member_direction,
                transverse_direction,
            )
        if not samples:
            panel_stresses.append(
                PanelStress(
                    field_id=field_item.field_id,
                    sigma_x1_mpa=0.0,
                    sigma_x2_mpa=0.0,
                    sigma_y1_mpa=0.0,
                    sigma_y2_mpa=0.0,
                    tau_xy_mpa=0.0,
                    sample_count=0,
                    reduction="no FRD stress samples",
                    diagnostics=("no stress samples found for field element ids",),
                )
            )
            continue

        panel_stresses.append(
            _reduced_panel_stress_from_samples(
                field_item,
                samples,
                reduction_method,
                transverse_edge_fraction=transverse_edge_fraction,
                centre_strip_fraction=centre_strip_fraction,
            )
        )
    return panel_stresses


def summarize_panel_stresses(panel_stresses: Sequence[PanelStress]) -> list[dict[str, Any]]:
    """Flatten reduced panel stresses for JSON/CSV-style inspection."""

    return [
        {
            "field_id": stress.field_id,
            "sigma_x1_mpa": stress.sigma_x1_mpa,
            "sigma_x2_mpa": stress.sigma_x2_mpa,
            "sigma_y1_mpa": stress.sigma_y1_mpa,
            "sigma_y2_mpa": stress.sigma_y2_mpa,
            "tau_xy_mpa": stress.tau_xy_mpa,
            "sample_count": stress.sample_count,
            "reduction": stress.reduction,
            "source_units": stress.source_units,
            "diagnostics": list(stress.diagnostics),
        }
        for stress in panel_stresses
    ]


def _format_detail_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return f"{value:.4f}" if abs(value) < 1.0e4 else f"{value:.4g}"
    if isinstance(value, (list, tuple, set)):
        items = [_format_detail_value(item) for item in list(value)[:8]]
        suffix = ", ..." if len(value) > 8 else ""
        return "[" + ", ".join(items) + suffix + "]"
    return str(value)


def _format_result_tree(value: dict[str, Any], indent: int = 1) -> list[str]:
    pad = "  " * indent
    lines: list[str] = []
    for key, nested in value.items():
        if isinstance(nested, dict):
            if not nested:
                continue
            lines.append(f"{pad}{key}:")
            lines.extend(_format_result_tree(nested, indent + 1))
        else:
            text = _format_detail_value(nested)
            if text == "":
                continue
            lines.append(f"{pad}{key}: {text}")
    return lines


def format_panel_buckling_details(panel: Any, uf_basis: str | None = None) -> str:
    """Return a readable multi-line report of all UFs/details for one FE panel.

    Works for flat and cylinder FE-result panels and for every calculation
    method: prescriptive results list each plate/stiffener/girder sub-check,
    SemiAnalytical results list buckling/ultimate UFs, raw values, validity,
    controlling limits and CSR information.
    """

    field_id = getattr(panel, "field_id", "?")
    data = getattr(panel, "anystructure_input", None) or {}
    buckling_input = data.get("buckling", {}) if isinstance(data, dict) else {}
    result_record = getattr(panel, "buckling_result", None) or {}

    lines: list[str] = [f"Panel {field_id}"]
    domain = result_record.get("domain") or (data.get("calculation_domain") if isinstance(data, dict) else None)
    if domain:
        lines.append(f"Domain: {domain}")
    method = result_record.get("calculation_method") or buckling_input.get("calculation_method")
    if method:
        lines.append(f"Calculation method: {method}")
    acceptance = uf_basis or result_record.get("buckling_acceptance") or buckling_input.get("buckling_acceptance")
    if acceptance:
        lines.append(f"UF basis (acceptance): {acceptance}")
    usage_factor = getattr(panel, "usage_factor", None)
    lines.append(f"Governing UF: {'-' if usage_factor is None else f'{usage_factor:.4f}'}")

    result = result_record.get("result")
    if isinstance(result, dict) and result:
        lines.append("")
        lines.append("Calculated usage factors and results:")
        lines.extend(_format_result_tree(result))
    error = result_record.get("error")
    if error:
        lines.append(f"Message: {error}")
    if not result_record:
        lines.append("No buckling calculation stored for this panel.")

    stress = getattr(panel, "stress", None)
    if stress is not None:
        lines.append("")
        lines.append("Reduced FE stresses:")
        if hasattr(stress, "sigma_x1_mpa"):
            lines.append(f"  sigma_x1 / sigma_x2: {stress.sigma_x1_mpa:.2f} / {stress.sigma_x2_mpa:.2f} MPa")
            lines.append(f"  sigma_y1 / sigma_y2: {stress.sigma_y1_mpa:.2f} / {stress.sigma_y2_mpa:.2f} MPa")
            lines.append(f"  tau_xy: {stress.tau_xy_mpa:.2f} MPa")
        else:
            lines.append(f"  axial: {stress.axial_stress_mpa:.2f} MPa")
            lines.append(f"  hoop: {stress.hoop_stress_mpa:.2f} MPa")
            lines.append(f"  torsional shear: {stress.torsional_shear_mpa:.2f} MPa")
        lines.append(f"  samples: {stress.sample_count}")
        lines.append(f"  reduction: {stress.reduction}")

    field = getattr(panel, "field", None)
    if field is not None and hasattr(field, "span_m"):
        lines.append("")
        lines.append("Panel geometry:")
        lines.append(
            f"  span {field.span_m:.3f} m, spacing {field.spacing_m:.3f} m, "
            f"thickness {(getattr(field, 'shell_section_thickness_m', None) or 0.0) * 1000.0:.2f} mm"
        )
    return "\n".join(lines)


def calculate_field_buckling(
    fields: Sequence[PlateField],
    panel_stresses: Sequence[PanelStress],
    *,
    calculation_method: str = "SemiAnalytical S3/U3",
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    ml_algo: Any = None,
) -> list[dict[str, Any]]:
    """Run ANYstructure buckling checks for fields using reduced FE stresses."""

    from anystruct.api import FlatStru

    stresses_by_field = {stress.field_id: stress for stress in panel_stresses}
    results: list[dict[str, Any]] = []
    for field_item in fields:
        stress = stresses_by_field.get(field_item.field_id)
        if stress is None:
            results.append(
                {
                    "field_id": field_item.field_id,
                    "available": False,
                    "error": "missing reduced panel stress",
                }
            )
            continue

        domain = _flat_structure_domain_for_field(field_item)
        try:
            panel = FlatStru(domain)
            panel.set_material(
                mat_yield=material_yield_mpa,
                emodule=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
            )
            panel.set_plate_geometry(
                spacing=field_item.spacing_m * 1000.0,
                thickness=(field_item.shell_section_thickness_m or 0.0) * 1000.0,
                span=field_item.span_m * 1000.0,
            )
            panel.set_stresses(
                pressure=pressure_mpa,
                sigma_x1=stress.sigma_x1_mpa,
                sigma_x2=stress.sigma_x2_mpa,
                sigma_y1=stress.sigma_y1_mpa,
                sigma_y2=stress.sigma_y2_mpa,
                tau_xy=stress.tau_xy_mpa,
            )
            stiffener = _first_member_by_role(field_item, "stiffener")
            if stiffener is not None and domain != "Flat plate, unstiffened":
                panel.set_stiffener(
                    hw=stiffener.web_height_m * 1000.0,
                    tw=(stiffener.web_thickness_m or 0.0) * 1000.0,
                    bf=(stiffener.flange_width_m or 0.0) * 1000.0,
                    tf=(stiffener.flange_thickness_m or 0.0) * 1000.0,
                    stf_type=stiffener.section_type,
                    spacing=field_item.spacing_m * 1000.0,
                )
            girder = _first_member_by_role(field_item, "girder")
            if girder is not None and domain == "Flat plate, stiffened with girder":
                panel.set_girder(
                    hw=girder.web_height_m * 1000.0,
                    tw=(girder.web_thickness_m or 0.0) * 1000.0,
                    bf=(girder.flange_width_m or 0.0) * 1000.0,
                    tf=(girder.flange_thickness_m or 0.0) * 1000.0,
                    stf_type=girder.section_type,
                    spacing=field_item.span_m * 1000.0,
                )
            panel.set_puls_parameters(sp_or_up="UP" if stiffener is None else "SP", puls_boundary="Int")
            panel.set_buckling_parameters(
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
                ml_algo=ml_algo,
            )
            buckling_result = panel.get_buckling_results(calculation_method=calculation_method, ml_algo=ml_algo)
            result_record = {
                "field_id": field_item.field_id,
                "domain": domain,
                "calculation_method": calculation_method,
                "buckling_acceptance": buckling_acceptance,
                "stress": summarize_panel_stresses([stress])[0],
                "result": buckling_result,
            }
            selected_uf = _selected_uf_from_buckling_result(result_record)
            api_available = (
                bool(buckling_result.get("available", True))
                if isinstance(buckling_result, dict)
                else buckling_result is not None
            )
            # A finite UF is a valid result even when an older/newer API wrapper
            # reports ``available`` differently.
            result_record["available"] = selected_uf is not None or api_available
            result_record["usage_factor"] = selected_uf
            if selected_uf is None and isinstance(buckling_result, dict):
                result_record["error"] = str(
                    buckling_result.get("error")
                    or buckling_result.get("message")
                    or "buckling calculation returned no identifiable usage factor"
                )
            results.append(result_record)
        except Exception as err:
            results.append(
                {
                    "field_id": field_item.field_id,
                    "domain": domain,
                    "available": False,
                    "calculation_method": calculation_method,
                    "buckling_acceptance": buckling_acceptance,
                    "stress": summarize_panel_stresses([stress])[0],
                    "error": str(err),
                }
            )
    return results


def _create_flat_fea_buckling_session(
    inp_path: str | os.PathLike[str],
    frd_path: str | os.PathLike[str] | None = None,
    *,
    load_case: int | None = None,
    calculation_method: str = "SemiAnalytical S3/U3",
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    ml_algo: Any = None,
    run_buckling: bool = True,
    stress_reduction_method: str | None = None,
) -> FeaBucklingSession:
    """Create a selectable FE-result buckling session for API and GUI callers."""

    inp_path = str(inp_path)
    frd_path_text = _default_fea_result_path(inp_path, frd_path)
    model = read_fea_shell_model(inp_path)
    fields = tuple(infer_plate_fields(model))
    frd_summary = read_fea_result_summary(frd_path_text) if frd_path_text else None
    diagnostics: list[str] = []
    reduction_method = normalize_stress_reduction_method(stress_reduction_method)
    diagnostics.append(f"stress reduction method: {reduction_method}")

    if frd_summary and "load_cases" in frd_summary and load_case is None:
        if frd_summary["load_cases"]:
            load_case = frd_summary["load_cases"][0]

    if frd_path_text:
        frd_stress = read_fea_stress(frd_path_text, load_case=load_case)
        panel_stresses = tuple(
            reduce_field_stresses(
                model,
                fields,
                frd_stress,
                stress_reduction_method=reduction_method,
            )
        )
    else:
        panel_stresses = ()
        diagnostics.append("no FRD result file supplied; panel stresses set to defaults")

    buckling_results: tuple[dict[str, Any], ...] = ()
    if run_buckling and panel_stresses:
        buckling_results = tuple(
            calculate_field_buckling(
                fields,
                panel_stresses,
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
                ml_algo=ml_algo,
            )
        )

    unavailable_results = [
        result for result in buckling_results
        if not result.get("available", False)
    ]
    if unavailable_results:
        diagnostics.append(
            f"{len(unavailable_results)} of {len(buckling_results)} flat-panel buckling calculations "
            "returned no identifiable usage factor"
        )
        diagnostics.extend(
            f"{result.get('field_id', '?')}: {result.get('error', 'no result')}"
            for result in unavailable_results[:20]
        )

    plot_records = panel_plot_records(model, fields)
    plot_by_field = {record["field_id"]: record for record in plot_records}
    stress_by_field = {stress.field_id: stress for stress in panel_stresses}
    result_by_field = {str(result.get("field_id")): result for result in buckling_results if result.get("field_id")}

    panels = tuple(
        FeaBucklingPanel(
            field_id=field_item.field_id,
            field=field_item,
            stress=stress_by_field.get(field_item.field_id),
            anystructure_input=anystructure_input_for_field(
                field_item,
                stress_by_field.get(field_item.field_id),
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
            ),
            plot_bounds=tuple(plot_by_field.get(field_item.field_id, {}).get("bounds", (0.0, 0.0, 0.0, 0.0))),
            buckling_result=result_by_field.get(field_item.field_id),
            usage_factor=_selected_uf_from_buckling_result(result_by_field.get(field_item.field_id, {})),
        )
        for field_item in fields
    )

    return FeaBucklingSession(
        inp_path=inp_path,
        frd_path=frd_path_text,
        model=model,
        fields=fields,
        panels=panels,
        frd_summary=frd_summary,
        diagnostics=tuple(diagnostics),
        active_load_case=load_case,
    )


def anystructure_input_for_field(
    field_item: PlateField,
    stress: PanelStress | None = None,
    *,
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    calculation_method: str = "SemiAnalytical S3/U3",
    buckling_acceptance: str = "ultimate",
) -> dict[str, Any]:
    """Return normal ANYstructure input values inferred for one FE panel."""

    stiffener = _first_member_by_role(field_item, "stiffener")
    girder = _first_member_by_role(field_item, "girder")
    section_member = stiffener or girder
    section_type = "FB" if section_member is None else section_member.section_type
    panel_stress = stress or PanelStress(
        field_id=field_item.field_id,
        sigma_x1_mpa=0.0,
        sigma_x2_mpa=0.0,
        sigma_y1_mpa=0.0,
        sigma_y2_mpa=0.0,
        tau_xy_mpa=0.0,
        sample_count=0,
        reduction="default zero stress",
    )
    return {
        "field_id": field_item.field_id,
        "calculation_domain": _flat_structure_domain_for_field(field_item),
        "geometry": {
            "span_mm": field_item.span_m * 1000.0,
            "spacing_mm": field_item.spacing_m * 1000.0,
            "plate_thickness_mm": (field_item.shell_section_thickness_m or 0.0) * 1000.0,
        },
        "section": {
            "type": section_type,
            "web_height_mm": 0.0 if section_member is None else section_member.web_height_m * 1000.0,
            "web_thickness_mm": 0.0 if section_member is None else (section_member.web_thickness_m or 0.0) * 1000.0,
            "flange_width_mm": 0.0 if section_member is None else (section_member.flange_width_m or 0.0) * 1000.0,
            "flange_thickness_mm": 0.0 if section_member is None else (section_member.flange_thickness_m or 0.0) * 1000.0,
            "source_member_id": None if section_member is None else section_member.member_id,
        },
        "girder": None if girder is None else {
            "type": girder.section_type,
            "web_height_mm": girder.web_height_m * 1000.0,
            "web_thickness_mm": (girder.web_thickness_m or 0.0) * 1000.0,
            "flange_width_mm": (girder.flange_width_m or 0.0) * 1000.0,
            "flange_thickness_mm": (girder.flange_thickness_m or 0.0) * 1000.0,
            "source_member_id": girder.member_id,
        },
        "material": {
            "yield_mpa": material_yield_mpa,
            "elastic_modulus_mpa": elastic_modulus_mpa,
            "material_factor": material_factor,
            "poisson": poisson,
        },
        "stresses": {
            "pressure_mpa": pressure_mpa,
            "sigma_x1_mpa": panel_stress.sigma_x1_mpa,
            "sigma_x2_mpa": panel_stress.sigma_x2_mpa,
            "sigma_y1_mpa": panel_stress.sigma_y1_mpa,
            "sigma_y2_mpa": panel_stress.sigma_y2_mpa,
            "tau_xy_mpa": panel_stress.tau_xy_mpa,
            "sample_count": panel_stress.sample_count,
            "reduction": panel_stress.reduction,
        },
        "buckling": {
            "calculation_method": calculation_method,
            "buckling_acceptance": buckling_acceptance,
            "puls_boundary": "Int",
            "puls_sp_or_up": "UP" if stiffener is None else "SP",
            "puls_up_boundary": "SSSS",
            "stiffener_end_support": "Continuous",
        },
    }


def panel_plot_records(
    model: FeShellModel,
    fields: Sequence[PlateField],
    field_values: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return 2D plot rectangles for clickable GUI rendering of FE panels."""

    patches = detect_surface_patches(model)
    inference = _infer_members_from_patches(model, patches) if patches else None
    member_direction = inference.member_direction if inference is not None else (1.0, 0.0, 0.0)
    transverse_direction = inference.transverse_direction if inference is not None else (0.0, 1.0, 0.0)
    records: list[dict[str, Any]] = []
    for index, field_item in enumerate(fields):
        bounds = _field_plot_bounds(field_item, member_direction, transverse_direction)
        value = None if field_values is None else field_values.get(field_item.field_id)
        records.append(
            {
                "field_id": field_item.field_id,
                "index": index,
                "bounds": bounds,
                "value": value,
                "span_m": field_item.span_m,
                "spacing_m": field_item.spacing_m,
            }
        )
    return records


def panel_3d_records(
    model: FeShellModel,
    fields: Sequence[PlateField],
    field_values: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return 3D buckling-panel polygons.

    Unlike ``panel_plot_records`` this does not flatten panels into one plane.
    For SESAM imports the field is drawn from its actual shell polygons because
    those models often contain skewed plate strips where one bounding rectangle
    visually overstates the panel.
    """

    if fields and isinstance(fields[0], CylinderField):
        geometry = detect_cylinder_geometry(model)
        return cylinder_3d_records(
            model,
            geometry,
            fields,  # type: ignore[arg-type]
            field_values=field_values,
        )

    use_element_polygons = _is_sesam_model_path(model.source_path)
    records: list[dict[str, Any]] = []
    for index, field_item in enumerate(fields):
        if use_element_polygons:
            polygons = _field_element_polygons(model, field_item)
        else:
            polygons = [_field_representative_panel_polygon(model, field_item)]
        if not polygons:
            polygons = [_field_bbox_representative_polygon(field_item)]
        points = [point for polygon in polygons for point in polygon]
        bbox = _bbox(points) if points else field_item.bbox
        value = None if field_values is None else field_values.get(field_item.field_id)
        local_x, local_y = _field_local_axes(model, field_item)
        records.append(
            {
                "field_id": field_item.field_id,
                "index": index,
                "polygons": polygons,
                "bbox": bbox,
                "centroid": _mean_point(points) if points else (
                    (bbox[0][0] + bbox[0][1]) / 2.0,
                    (bbox[1][0] + bbox[1][1]) / 2.0,
                    (bbox[2][0] + bbox[2][1]) / 2.0,
                ),
                "normal": _field_representative_normal(model, field_item),
                "local_x": local_x,
                "local_y": local_y,
                "value": value,
                "span_m": field_item.span_m,
                "spacing_m": field_item.spacing_m,
            }
        )
    return records


def _field_representative_panel_polygon(model: FeShellModel, field_item: PlateField) -> list[Point3D]:
    """Return one oriented rectangle covering the FE elements in a panel field."""

    element_polygons = _field_element_polygons(model, field_item)
    points = [point for polygon in element_polygons for point in polygon]
    if len(points) < 3:
        return _field_bbox_representative_polygon(field_item)

    normal = _field_representative_normal(model, field_item)
    centroid = _mean_point(points)
    bbox = _bbox(points)
    axis_vectors = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    projected_axes: list[tuple[float, Vector3D]] = []
    for axis_index, axis_vector in enumerate(axis_vectors):
        projected = _project_to_plane(axis_vector, normal)
        projected_axes.append((bbox[axis_index][1] - bbox[axis_index][0], projected))
    projected_axes = [
        (extent, axis)
        for extent, axis in sorted(projected_axes, key=lambda item: item[0], reverse=True)
        if _length(axis) > 1.0e-12
    ]
    if projected_axes:
        u_axis = projected_axes[0][1]
    else:
        u_axis = _normalise(_subtract(points[1], points[0]))
    v_axis = _normalise(_cross(normal, u_axis))
    if _length(v_axis) <= 1.0e-12:
        return _field_bbox_representative_polygon(field_item)

    u_values = [_dot(_subtract(point, centroid), u_axis) for point in points]
    v_values = [_dot(_subtract(point, centroid), v_axis) for point in points]
    u_min, u_max = min(u_values), max(u_values)
    v_min, v_max = min(v_values), max(v_values)

    def corner(u_value: float, v_value: float) -> Point3D:
        return (
            centroid[0] + u_axis[0] * u_value + v_axis[0] * v_value,
            centroid[1] + u_axis[1] * u_value + v_axis[1] * v_value,
            centroid[2] + u_axis[2] * u_value + v_axis[2] * v_value,
        )

    return [
        corner(u_min, v_min),
        corner(u_max, v_min),
        corner(u_max, v_max),
        corner(u_min, v_max),
    ]


def plot_plate_fields_3d(
    model: FeShellModel,
    fields: Sequence[PlateField] | None = None,
    *,
    output_path: str | os.PathLike[str] | None = None,
    field_values: dict[str, float] | None = None,
    value_label: str = "UF",
    cmap_name: str = "tab20",
    annotate: bool = True,
    dpi: int = 180,
) -> Any:
    """Plot discovered buckling panels as 3D shell-panel surfaces only."""

    from matplotlib import colors as matplotlib_colors
    from matplotlib import pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fields = list(infer_plate_fields(model) if fields is None else fields)
    records = panel_3d_records(model, fields, field_values=field_values)
    fig = plt.figure(figsize=(9.0, 5.5), dpi=dpi)
    ax = fig.add_subplot(111, projection="3d")
    scalar_values = _finite_field_values(field_values)
    if scalar_values:
        scalar_cmap_name = "RdYlGn_r" if cmap_name == "tab20" else cmap_name
        cmap = plt.get_cmap(scalar_cmap_name)
        value_min = min(min(scalar_values.values()), 0.0)
        value_max = max(max(scalar_values.values()), 1.0)
        if math.isclose(value_min, value_max):
            value_max = value_min + 1.0
        norm = matplotlib_colors.Normalize(vmin=value_min, vmax=value_max)
    else:
        cmap = plt.get_cmap(cmap_name, max(len(records), 1))
        norm = None

    all_points: list[Point3D] = []
    for record in records:
        value = record.get("value")
        if norm is not None:
            color = cmap(norm(value)) if value is not None and math.isfinite(float(value)) else "0.82"
        else:
            color = cmap(record["index"] % max(len(records), 1))
        collection = Poly3DCollection(
            record["polygons"],
            facecolor=color,
            edgecolor="black",
            linewidth=0.35,
            alpha=0.78,
        )
        ax.add_collection3d(collection)
        all_points.extend(point for polygon in record["polygons"] for point in polygon)
        if annotate:
            centroid = record["centroid"]
            label = record["field_id"].replace("field_", "")
            if value is not None and math.isfinite(float(value)):
                label = f"{label}\n{float(value):.2f}"
            ax.text(centroid[0], centroid[1], centroid[2], label, fontsize=7, ha="center", va="center")

    _set_equal_3d_limits(ax, all_points)
    ax.set_xlabel("X [m]")
    ax.set_ylabel("Y [m]")
    ax.set_zlabel("Z [m]")
    ax.set_title(f"Discovered buckling panels ({len(records)})" if norm is None else f"Buckling panels by {value_label}")
    if norm is not None:
        scalar_map = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
        scalar_map.set_array([])
        colorbar = fig.colorbar(scalar_map, ax=ax, fraction=0.036, pad=0.04)
        colorbar.set_label(value_label)
    fig.tight_layout()
    if output_path is not None:
        fig.savefig(output_path, bbox_inches="tight")
    return fig


def analyze_frd_buckling(
    inp_path: str | os.PathLike[str],
    frd_path: str | os.PathLike[str],
    **buckling_kwargs: Any,
) -> dict[str, Any]:
    """Read INP/FRD, infer fields, reduce stresses, and run buckling checks."""

    model = read_fea_shell_model(inp_path)
    fields = infer_plate_fields(model)
    frd_summary = read_fea_result_summary(frd_path)
    frd_stress = read_fea_stress(frd_path)
    panel_stresses = reduce_field_stresses(model, fields, frd_stress)
    buckling_results = calculate_field_buckling(fields, panel_stresses, **buckling_kwargs)
    payload = _summary_payload(model, fields, frd_summary)
    payload["panel_stresses"] = summarize_panel_stresses(panel_stresses)
    payload["buckling_results"] = buckling_results
    return payload


def detect_surface_patches(model: FeShellModel, decimals: int = 6) -> list[SurfacePatch]:
    """Group shell elements into connected coplanar surface patches."""

    grouped: dict[tuple[Vector3D, float], list[int]] = defaultdict(list)
    for element in model.shell_elements.values():
        points = [model.nodes[node_id] for node_id in element.corner_node_ids]
        normal = _canonical_normal(_element_normal(points), decimals=decimals)
        offset = round(_dot(normal, points[0]), decimals)
        grouped[(normal, offset)].append(element.element_id)

    patches: list[SurfacePatch] = []
    for group_index, ((normal, offset), element_ids) in enumerate(
        sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1]))
    ):
        components = _connected_components_by_corner_edges(model, element_ids)
        for component_index, component in enumerate(components):
            patches.append(
                _make_surface_patch(
                    model,
                    patch_id=f"patch_{group_index + 1:03d}_{component_index + 1:03d}",
                    element_ids=tuple(sorted(component)),
                    normal=normal,
                    offset=offset,
                )
            )
    return patches


def infer_plate_fields(model: FeShellModel) -> list[PlateField]:
    """Infer flat plate fields and shell-plate stiffener sections from a shell model."""

    if _is_sesam_model_path(model.source_path):
        sesam_fields = _infer_sesam_plate_fields(model)
        if sesam_fields:
            return sesam_fields

    patches = detect_surface_patches(model)
    if not patches:
        return []

    inference = _infer_members_from_patches(model, patches)
    base_patch = inference.base_patch
    members = tuple(sorted(inference.members, key=lambda member: (member.role, member.station)))
    stiffeners = tuple(sorted(inference.stiffeners, key=lambda member: member.station))
    girders = tuple(sorted(inference.girders, key=lambda member: member.station))
    member_by_id = {member.member_id: member for member in members}
    base_section_thickness = _shell_section_thickness_for_patch(model, base_patch)

    if not stiffeners:
        return [
            PlateField(
                field_id="field_001",
                base_patch_id=base_patch.patch_id,
                element_ids=base_patch.element_ids,
                bbox=base_patch.bbox,
                span_m=_extent_along_patch(base_patch, inference.member_direction),
                spacing_m=_extent_along_patch(base_patch, inference.transverse_direction),
                transverse_bounds=_projected_bounds(base_patch, inference.transverse_direction),
                attached_member_ids=(),
                shell_section_thickness_m=base_section_thickness,
                diagnostics=("unstiffened base plate",),
                span_direction=inference.member_direction,
                transverse_direction=inference.transverse_direction,
            )
        ]

    fields: list[PlateField] = []
    base_centroids = {
        element_id: _element_centroid(model, model.shell_elements[element_id])
        for element_id in base_patch.element_ids
    }
    longitudinal_bounds = _split_bounds_with_members(base_patch, inference.member_direction, girders)

    field_index = 1
    for lower_stiffener, upper_stiffener in zip(stiffeners[:-1], stiffeners[1:]):
        lower_transverse = min(lower_stiffener.station, upper_stiffener.station)
        upper_transverse = max(lower_stiffener.station, upper_stiffener.station)
        transverse_tolerance = max((upper_transverse - lower_transverse) * 1.0e-6, 1.0e-9)
        for lower_longitudinal, upper_longitudinal, boundary_girders in longitudinal_bounds:
            longitudinal_tolerance = max((upper_longitudinal - lower_longitudinal) * 1.0e-6, 1.0e-9)
            attached_ids = [lower_stiffener.member_id, upper_stiffener.member_id]
            attached_ids.extend(member.member_id for member in boundary_girders)
            field_members = tuple(member_by_id[member_id] for member_id in dict.fromkeys(attached_ids))
            field_element_ids = tuple(
                sorted(
                    element_id
                    for element_id, centroid in base_centroids.items()
                    if lower_transverse + transverse_tolerance
                    <= _dot(centroid, inference.transverse_direction)
                    <= upper_transverse - transverse_tolerance
                    and lower_longitudinal + longitudinal_tolerance
                    <= _dot(centroid, inference.member_direction)
                    <= upper_longitudinal - longitudinal_tolerance
                )
            )
            field_bbox = _bbox_for_elements(model, field_element_ids) if field_element_ids else base_patch.bbox
            fields.append(
                PlateField(
                    field_id=f"field_{field_index:03d}",
                    base_patch_id=base_patch.patch_id,
                    element_ids=field_element_ids,
                    bbox=field_bbox,
                    span_m=upper_longitudinal - lower_longitudinal,
                    spacing_m=upper_transverse - lower_transverse,
                    transverse_bounds=(lower_transverse, upper_transverse),
                    attached_member_ids=tuple(dict.fromkeys(attached_ids)),
                    members=field_members,
                    shell_section_thickness_m=base_section_thickness,
                    diagnostics=("bounded by adjacent stiffener stations and longitudinal girder/boundary",),
                    span_direction=inference.member_direction,
                    transverse_direction=inference.transverse_direction,
                )
            )
            field_index += 1

    return fields


def _infer_sesam_plate_fields(model: FeShellModel) -> list[PlateField]:
    """Infer SESAM buckling panels from beam sections and geometric plate edges."""

    patches = [
        patch
        for patch in detect_surface_patches(model, decimals=3)
        if patch.area > 1.0e-3 and len(patch.element_ids) > 0
    ]
    if not patches:
        return []

    fields: list[PlateField] = []
    field_index = 1
    for patch in sorted(patches, key=lambda item: (-item.area, item.patch_id)):
        patch_fields = _split_sesam_patch_by_beams(
            model,
            patch,
            field_index,
        )
        fields.extend(patch_fields)
        field_index += len(patch_fields)
    fields = _merge_sesam_curved_side_fields(model, fields)
    fields = _merge_sesam_sliver_fields(model, fields)
    fields = _deduplicate_plate_field_elements(model, fields)
    return _renumber_plate_fields(fields)


def _split_sesam_patch_by_beams(
    model: FeShellModel,
    patch: SurfacePatch,
    start_index: int,
) -> list[PlateField]:
    patch_polygons = _element_polygons_for_ids(model, patch.element_ids)
    points = [point for polygon in patch_polygons for point in polygon]
    if len(points) < 3:
        return []
    normal = patch.normal
    local_u, local_v = _patch_local_axes_from_polygons(patch_polygons, normal)
    u_min, u_max = _point_bounds_along(points, local_u)
    v_min, v_max = _point_bounds_along(points, local_v)
    u_extent = u_max - u_min
    v_extent = v_max - v_min
    if u_extent <= 1.0e-8 or v_extent <= 1.0e-8:
        return []

    plane_tolerance = max(0.03, min(u_extent, v_extent) * 0.02)
    station_tolerance = max(0.04, min(u_extent, v_extent) * 0.015)
    overlap_tolerance = max(0.03, min(u_extent, v_extent) * 0.02)
    u_members: list[InferredMember] = []
    v_members: list[InferredMember] = []

    for beam in model.beam_elements.values():
        cross = beam.cross_section or {}
        if not cross.get("web_height"):
            continue
        beam_points = [model.nodes[node_id] for node_id in beam.node_ids if node_id in model.nodes]
        if len(beam_points) < 2:
            continue
        distances = [abs(_dot(point, normal) - patch.offset) for point in beam_points]
        if min(distances) > plane_tolerance or sum(distances) / len(distances) > plane_tolerance * 2.0:
            continue
        projected = [_dot(point, local_u) for point in beam_points]
        transverse = [_dot(point, local_v) for point in beam_points]
        tangent = _normalise(_subtract(beam_points[-1], beam_points[0]))
        tangent_in_plane = _project_to_plane(tangent, normal)
        if _length(tangent_in_plane) <= 1.0e-8:
            continue
        align_u = abs(_dot(tangent_in_plane, local_u))
        align_v = abs(_dot(tangent_in_plane, local_v))
        if max(align_u, align_v) < 0.93:
            continue
        runs_u = align_u >= align_v
        if runs_u:
            run_min, run_max = min(projected), max(projected)
            station = sum(transverse) / len(transverse)
            if max(transverse) - min(transverse) > station_tolerance:
                continue
            if station < v_min - station_tolerance or station > v_max + station_tolerance:
                continue
            if min(run_max, u_max) - max(run_min, u_min) < overlap_tolerance:
                continue
            station = min(max(station, v_min), v_max)
            run_length = max(min(run_max, u_max) - max(run_min, u_min), 0.0)
            u_members.append(
                _sesam_beam_member(
                    beam,
                    "beam_u",
                    len(u_members) + 1,
                    tangent_in_plane,
                    station,
                    run_length_m=run_length,
                )
            )
        else:
            run_min, run_max = min(transverse), max(transverse)
            station = sum(projected) / len(projected)
            if max(projected) - min(projected) > station_tolerance:
                continue
            if station < u_min - station_tolerance or station > u_max + station_tolerance:
                continue
            if min(run_max, v_max) - max(run_min, v_min) < overlap_tolerance:
                continue
            station = min(max(station, u_min), u_max)
            run_length = max(min(run_max, v_max) - max(run_min, v_min), 0.0)
            v_members.append(
                _sesam_beam_member(
                    beam,
                    "beam_v",
                    len(v_members) + 1,
                    tangent_in_plane,
                    station,
                    run_length_m=run_length,
                )
            )

    u_members = _filter_sesam_sustained_beam_members(
        u_members,
        station_tolerance,
        min_required_length=min(max(u_extent * 0.10, overlap_tolerance * 2.0), 0.80),
    )
    v_members = _filter_sesam_sustained_beam_members(
        v_members,
        station_tolerance,
        min_required_length=min(max(v_extent * 0.10, overlap_tolerance * 2.0), 0.80),
    )
    u_members = _merge_sesam_members(u_members, station_tolerance)
    v_members = _merge_sesam_members(v_members, station_tolerance)
    u_plate_members, v_plate_members = _sesam_out_of_plane_plate_members(
        model,
        patch,
        local_u,
        local_v,
        normal,
        (u_min, u_max),
        (v_min, v_max),
        plane_tolerance,
        station_tolerance,
        overlap_tolerance,
    )
    u_plate_members = _filter_sesam_sustained_boundary_members(
        u_plate_members,
        station_tolerance,
        min_required_length=min(max(u_extent * 0.08, overlap_tolerance * 1.5), 0.60),
    )
    v_plate_members = _filter_sesam_sustained_boundary_members(
        v_plate_members,
        station_tolerance,
        min_required_length=min(max(v_extent * 0.08, overlap_tolerance * 1.5), 0.60),
    )
    if abs(normal[2]) < 0.35:
        u_free_edge_members, v_free_edge_members = _sesam_internal_free_edge_members(
            model,
            patch,
            local_u,
            local_v,
            normal,
            (u_min, u_max),
            (v_min, v_max),
            station_tolerance,
            overlap_tolerance,
        )
    else:
        u_free_edge_members, v_free_edge_members = [], []
    split_u_members, split_v_members = _sesam_split_member_families(
        _filter_sesam_sustained_boundary_members(
            u_members,
            station_tolerance,
            min_required_length=max(u_extent * 0.25, overlap_tolerance * 1.5),
        ),
        _filter_sesam_sustained_boundary_members(
            v_members,
            station_tolerance,
            min_required_length=max(v_extent * 0.25, overlap_tolerance * 1.5),
        ),
    )
    has_u_beam_splits = bool(split_u_members)
    has_v_beam_splits = bool(split_v_members)
    split_u_members = list(split_u_members) if has_u_beam_splits else list(u_plate_members)
    split_v_members = list(split_v_members) if has_v_beam_splits else list(v_plate_members)
    if has_u_beam_splits:
        split_u_members.extend(u_plate_members)
    if has_v_beam_splits:
        split_v_members.extend(v_plate_members)
    split_u_members.extend(u_free_edge_members)
    split_v_members.extend(v_free_edge_members)
    split_u_members = _merge_sesam_members(split_u_members, station_tolerance)
    split_v_members = _merge_sesam_members(split_v_members, station_tolerance)
    u_stations = _sesam_split_stations(u_min, u_max, split_v_members, station_tolerance)
    v_stations = _sesam_split_stations(v_min, v_max, split_u_members, station_tolerance)
    u_stations = _sesam_merge_short_intervals(
        u_stations,
        min_interval=0.0 if v_free_edge_members else (0.55 if u_extent > 2.0 else 0.0),
    )
    v_stations = _sesam_merge_short_intervals(
        v_stations,
        min_interval=0.0 if u_free_edge_members else (0.55 if v_extent > 2.0 else 0.0),
    )
    if len(u_stations) * len(v_stations) > max(len(patch.element_ids) * 3, 200):
        u_stations = [u_min, u_max]
        v_stations = [v_min, v_max]

    centroids = {
        element_id: _element_centroid(model, model.shell_elements[element_id])
        for element_id in patch.element_ids
    }
    element_uv = {
        element_id: (_dot(centroid, local_u), _dot(centroid, local_v))
        for element_id, centroid in centroids.items()
    }
    elements_by_cell: dict[tuple[int, int], list[int]] = defaultdict(list)
    for element_id, (u_value, v_value) in element_uv.items():
        u_index = _station_interval_index(u_value, u_stations, station_tolerance)
        v_index = _station_interval_index(v_value, v_stations, station_tolerance)
        if u_index is None or v_index is None:
            continue
        elements_by_cell[(u_index, v_index)].append(element_id)

    fields: list[PlateField] = []
    seen_element_sets: set[tuple[int, ...]] = set()
    for u_index, (u0, u1) in enumerate(zip(u_stations[:-1], u_stations[1:])):
        for v_index, (v0, v1) in enumerate(zip(v_stations[:-1], v_stations[1:])):
            if u1 - u0 <= 1.0e-8 or v1 - v0 <= 1.0e-8:
                continue
            selected = tuple(sorted(elements_by_cell.get((u_index, v_index), ())))
            if not selected:
                continue
            if selected in seen_element_sets:
                continue
            seen_element_sets.add(selected)
            attached = [
                member
                for member in split_v_members
                if abs(member.station - u0) <= station_tolerance or abs(member.station - u1) <= station_tolerance
            ]
            attached.extend(
                member
                for member in split_u_members
                if abs(member.station - v0) <= station_tolerance or abs(member.station - v1) <= station_tolerance
            )
            unique_members = tuple({member.member_id: member for member in attached}.values())
            u_size = u1 - u0
            v_size = v1 - v0
            span_axis = _sesam_span_axis_from_members(unique_members, local_u, local_v)
            if span_axis is None:
                span_axis = "u" if u_size >= v_size else "v"
            if span_axis == "u":
                span_m = u_size
                spacing_m = v_size
                span_direction = local_u
                transverse_direction = local_v
                transverse_bounds = (min(v0, v1), max(v0, v1))
            else:
                span_m = v_size
                spacing_m = u_size
                span_direction = local_v
                transverse_direction = local_u
                transverse_bounds = (min(u0, u1), max(u0, u1))
            fields.append(
                PlateField(
                    field_id=f"field_{start_index + len(fields):03d}",
                    base_patch_id=patch.patch_id,
                    element_ids=selected,
                    bbox=_bbox_for_elements(model, selected),
                    span_m=span_m,
                    spacing_m=spacing_m,
                    transverse_bounds=transverse_bounds,
                    attached_member_ids=tuple(member.member_id for member in unique_members),
                    members=unique_members,
                    shell_section_thickness_m=_shell_section_thickness_for_elements(model, selected),
                    diagnostics=("SESAM plate patch split by beam sections, out-of-plane plates, and free edges",),
                    span_direction=span_direction,
                    transverse_direction=transverse_direction,
                )
            )
    return fields


def _sesam_span_axis_from_members(
    members: Sequence[InferredMember],
    local_u: Vector3D,
    local_v: Vector3D,
) -> str | None:
    """Return "u" or "v" when attached stiffeners identify the panel span axis."""

    counts = {"u": 0, "v": 0}
    for member in members:
        if member.role != "stiffener":
            continue
        align_u = abs(_dot(member.direction, local_u))
        align_v = abs(_dot(member.direction, local_v))
        if align_u > align_v:
            counts["u"] += 1
        elif align_v > align_u:
            counts["v"] += 1
    if counts["u"] == counts["v"]:
        return None
    return "u" if counts["u"] > counts["v"] else "v"


def _sesam_split_member_families(
    u_members: Sequence[InferredMember],
    v_members: Sequence[InferredMember],
) -> tuple[Sequence[InferredMember], Sequence[InferredMember]]:
    """Return beam families that should split a SESAM plate patch.

    All sustained beams (both longitudinal and transverse) act as boundaries
    to divide the plate into stiffened sub-panels, where the boundaries themselves
    are treated as the panel's stiffeners.
    """
    return u_members, v_members


def _merge_sesam_curved_side_fields(model: FeShellModel, fields: Sequence[PlateField]) -> list[PlateField]:
    candidates: list[PlateField] = []
    passthrough: list[PlateField] = []
    for field_item in fields:
        if _is_sesam_curved_side_field(model, field_item):
            candidates.append(field_item)
        else:
            passthrough.append(field_item)
    if not candidates:
        return list(fields)

    groups: defaultdict[tuple[int, int, int], list[PlateField]] = defaultdict(list)
    for field_item in candidates:
        points = [point for polygon in _field_element_polygons(model, field_item) for point in polygon]
        if not points:
            passthrough.append(field_item)
            continue
        radii = [math.hypot(point[0], point[1]) for point in points]
        z_min, z_max = field_item.bbox[2]
        thickness_mm = int(round((_shell_section_thickness_for_elements(model, field_item.element_ids) or 0.0) * 1000.0))
        key = (
            int(round(min(z_min, z_max) / 0.05)),
            int(round(max(z_min, z_max) / 0.05)),
            int(round((sum(radii) / len(radii)) / 0.25)),
            thickness_mm,
        )
        groups[key].append(field_item)

    merged: list[PlateField] = list(passthrough)
    for group_fields in groups.values():
        if len(group_fields) <= 1:
            merged.extend(group_fields)
            continue
        for component in _connected_field_components(model, group_fields):
            if len(component) <= 1:
                merged.extend(component)
                continue
            for chunk in _split_curved_component_by_span(model, component):
                if len(chunk) <= 1:
                    merged.extend(chunk)
                else:
                    merged.append(_merge_plate_field_component(model, chunk))
    return merged


def _merge_sesam_sliver_fields(model: FeShellModel, fields: Sequence[PlateField]) -> list[PlateField]:
    """Merge small SESAM edge fragments into adjacent panels.

    Irregular access holes and trimmed plate ends can produce one- or two-element
    panels bounded by incidental mesh edges.  GeniE generally folds those
    fragments into the neighbouring geometric panel unless they form a sustained
    bay.  This pass preserves shell ownership while removing those mesh slivers.
    """

    field_by_id = {field_item.field_id: field_item for field_item in fields}
    if not field_by_id:
        return []

    def is_sliver(field_item: PlateField) -> bool:
        if not (field_item.spacing_m < 0.30 or field_item.span_m < 0.45):
            return False
        if len(field_item.element_ids) > 4 and field_item.spacing_m >= 0.25:
            return False
        return True

    changed = True
    while changed:
        changed = False
        current_fields = list(field_by_id.values())
        edge_to_fields: defaultdict[tuple[int, int], set[str]] = defaultdict(set)
        node_to_fields: defaultdict[int, set[str]] = defaultdict(set)
        edges_by_field: dict[str, tuple[tuple[int, int], ...]] = {}
        nodes_by_field: dict[str, set[int]] = {}
        for field_item in current_fields:
            edges = tuple(_field_shell_edges(model, field_item))
            nodes = _field_shell_nodes(model, field_item)
            edges_by_field[field_item.field_id] = edges
            nodes_by_field[field_item.field_id] = nodes
            for edge in edges:
                edge_to_fields[edge].add(field_item.field_id)
            for node_id in nodes:
                node_to_fields[node_id].add(field_item.field_id)

        ordered = sorted(
            current_fields,
            key=lambda item: (len(item.element_ids), item.spacing_m, item.span_m, item.field_id),
        )
        for field_item in ordered:
            if field_item.field_id not in field_by_id or not is_sliver(field_item):
                continue
            neighbour_scores: defaultdict[str, int] = defaultdict(int)
            for edge in edges_by_field.get(field_item.field_id, ()):
                for neighbour_id in edge_to_fields.get(edge, ()):
                    if neighbour_id != field_item.field_id and neighbour_id in field_by_id:
                        neighbour_scores[neighbour_id] += 10
            for node_id in nodes_by_field.get(field_item.field_id, ()):
                for neighbour_id in node_to_fields.get(node_id, ()):
                    if neighbour_id != field_item.field_id and neighbour_id in field_by_id:
                        neighbour_scores[neighbour_id] += 1
            if not neighbour_scores:
                continue

            field_normal = _field_representative_normal(model, field_item)
            field_thickness = field_item.shell_section_thickness_m or 0.0

            def neighbour_score(neighbour_id: str) -> tuple[bool, bool, bool, int, int, float]:
                neighbour = field_by_id[neighbour_id]
                neighbour_normal = _field_representative_normal(model, neighbour)
                normal_match = abs(_dot(field_normal, neighbour_normal)) >= 0.70
                thickness_delta = abs((neighbour.shell_section_thickness_m or 0.0) - field_thickness)
                thickness_match = thickness_delta <= 0.002
                return (
                    normal_match,
                    thickness_match,
                    not is_sliver(neighbour),
                    neighbour_scores[neighbour_id],
                    len(neighbour.element_ids),
                    -thickness_delta,
                )

            target_id = max(neighbour_scores, key=neighbour_score)
            field_by_id[target_id] = _merge_sesam_general_fields(
                model,
                field_by_id[target_id],
                field_item,
                "SESAM mesh sliver merged into adjacent geometric panel",
            )
            del field_by_id[field_item.field_id]
            changed = True
            break

    return list(field_by_id.values())


def _field_shell_edges(model: FeShellModel, field_item: PlateField) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    for element_id in field_item.element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        nodes = list(element.corner_node_ids)
        edges.extend(tuple(sorted((first, second))) for first, second in zip(nodes, nodes[1:] + nodes[:1]))
    return edges


def _field_shell_nodes(model: FeShellModel, field_item: PlateField) -> set[int]:
    return {
        node_id
        for element_id in field_item.element_ids
        if element_id in model.shell_elements
        for node_id in model.shell_elements[element_id].corner_node_ids
    }


def _merge_sesam_general_fields(
    model: FeShellModel,
    first: PlateField,
    second: PlateField,
    diagnostic: str,
) -> PlateField:
    element_ids = tuple(sorted(set(first.element_ids).union(second.element_ids)))
    bbox = _bbox_for_elements(model, element_ids)
    polygons = _element_polygons_for_ids(model, element_ids)
    points = [point for polygon in polygons for point in polygon]
    normal = _field_representative_normal(model, first)
    members = tuple({member.member_id: member for field_item in (first, second) for member in field_item.members}.values())
    try:
        local_u, local_v = _patch_local_axes_from_polygons(polygons, normal)
        u_values = [_dot(point, local_u) for point in points]
        v_values = [_dot(point, local_v) for point in points]
        u_extent = max(u_values) - min(u_values)
        v_extent = max(v_values) - min(v_values)
        span_axis = _sesam_span_axis_from_members(members, local_u, local_v)
        if span_axis is None:
            span_axis = "u" if u_extent >= v_extent else "v"
        if span_axis == "u":
            span = u_extent
            spacing = v_extent
            transverse_bounds = (min(v_values), max(v_values))
            span_direction: Vector3D | None = local_u
            transverse_direction: Vector3D | None = local_v
        else:
            span = v_extent
            spacing = u_extent
            transverse_bounds = (min(u_values), max(u_values))
            span_direction = local_v
            transverse_direction = local_u
    except Exception:
        ranges = [bbox[index][1] - bbox[index][0] for index in range(3)]
        span = max(ranges)
        spacing = sorted(ranges)[1]
        transverse_bounds = (0.0, spacing)
        span_direction = None
        transverse_direction = None

    return replace(
        first,
        base_patch_id=f"merged_{first.base_patch_id}",
        element_ids=element_ids,
        bbox=bbox,
        span_m=span,
        spacing_m=spacing,
        transverse_bounds=transverse_bounds,
        attached_member_ids=tuple(member.member_id for member in members),
        members=members,
        shell_section_thickness_m=_shell_section_thickness_for_elements(model, element_ids),
        confidence=min(first.confidence, second.confidence),
        diagnostics=first.diagnostics + (diagnostic,),
        span_direction=span_direction,
        transverse_direction=transverse_direction,
    )


def _is_sesam_curved_side_field(model: FeShellModel, field_item: PlateField) -> bool:
    polygons = _field_element_polygons(model, field_item)
    points = [point for polygon in polygons for point in polygon]
    if len(points) < 4:
        return False
    z_extent = field_item.bbox[2][1] - field_item.bbox[2][0]
    if z_extent < 0.15:
        return False
    normal = _field_representative_normal(model, field_item)
    if abs(normal[2]) > 0.35:
        return False
    radii = [math.hypot(point[0], point[1]) for point in points]
    mean_radius = sum(radii) / len(radii)
    if mean_radius < 5.0:
        return False
    if max(radii) - min(radii) > max(0.35, mean_radius * 0.025):
        return False
    centroid = _mean_point(points)
    radial = _normalise((centroid[0], centroid[1], 0.0))
    if _length(radial) <= 1.0e-8:
        return False
    return abs(_dot(normal, radial)) > 0.70


def _connected_field_components(model: FeShellModel, fields: Sequence[PlateField]) -> list[list[PlateField]]:
    node_sets = {
        field_item.field_id: {
            node_id
            for element_id in field_item.element_ids
            for node_id in model.shell_elements[element_id].corner_node_ids
            if element_id in model.shell_elements
        }
        for field_item in fields
    }
    by_id = {field_item.field_id: field_item for field_item in fields}
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    for index, first in enumerate(fields):
        first_nodes = node_sets[first.field_id]
        for second in fields[index + 1:]:
            if len(first_nodes.intersection(node_sets[second.field_id])) >= 2:
                adjacency[first.field_id].add(second.field_id)
                adjacency[second.field_id].add(first.field_id)

    components: list[list[PlateField]] = []
    visited: set[str] = set()
    for field_item in fields:
        if field_item.field_id in visited:
            continue
        stack = [field_item.field_id]
        visited.add(field_item.field_id)
        component_ids: list[str] = []
        while stack:
            current = stack.pop()
            component_ids.append(current)
            for next_id in adjacency.get(current, ()):
                if next_id not in visited:
                    visited.add(next_id)
                    stack.append(next_id)
        components.append([by_id[field_id] for field_id in component_ids])
    return components


def _merge_plate_field_component(model: FeShellModel, fields: Sequence[PlateField]) -> PlateField:
    element_ids = tuple(sorted({element_id for field_item in fields for element_id in field_item.element_ids}))
    bbox = _bbox_for_elements(model, element_ids)
    polygons = _element_polygons_for_ids(model, element_ids)
    points = [point for polygon in polygons for point in polygon]
    z_extent = bbox[2][1] - bbox[2][0]
    horizontal_extent = _curved_horizontal_extent(points)
    members = tuple({member.member_id: member for field_item in fields for member in field_item.members}.values())
    attached_member_ids = tuple(member.member_id for member in members)
    return PlateField(
        field_id=fields[0].field_id,
        base_patch_id=f"curved_{fields[0].base_patch_id}",
        element_ids=element_ids,
        bbox=bbox,
        span_m=max(horizontal_extent, z_extent),
        spacing_m=min(horizontal_extent, z_extent),
        transverse_bounds=(bbox[2][0], bbox[2][1]),
        attached_member_ids=attached_member_ids,
        members=members,
        shell_section_thickness_m=_shell_section_thickness_for_elements(model, element_ids),
        confidence=min(field_item.confidence for field_item in fields),
        diagnostics=("SESAM curved side fields merged across connected circumferential facets",),
    )


def _split_curved_component_by_span(
    model: FeShellModel,
    fields: Sequence[PlateField],
    max_span_m: float = 2.70,
) -> list[list[PlateField]]:
    ordered = sorted(fields, key=lambda field_item: _field_circumferential_angle(model, field_item))
    hard_split_indices = _curved_component_perpendicular_split_indices(model, ordered)
    if hard_split_indices:
        chunks: list[list[PlateField]] = []
        start = 0
        for split_index in sorted(hard_split_indices):
            segment = ordered[start:split_index]
            if segment:
                chunks.extend(_split_ordered_curved_fields_by_span(model, segment, max_span_m))
            start = split_index
        tail = ordered[start:]
        if tail:
            chunks.extend(_split_ordered_curved_fields_by_span(model, tail, max_span_m))
        return chunks

    return _split_ordered_curved_fields_by_span(model, ordered, max_span_m)


def _split_ordered_curved_fields_by_span(
    model: FeShellModel,
    ordered: Sequence[PlateField],
    max_span_m: float,
) -> list[list[PlateField]]:
    chunks: list[list[PlateField]] = []
    current: list[PlateField] = []
    for field_item in ordered:
        trial = [*current, field_item]
        trial_points = [
            point
            for trial_field in trial
            for polygon in _field_element_polygons(model, trial_field)
            for point in polygon
        ]
        if current and _curved_horizontal_extent(trial_points) > max_span_m:
            chunks.append(current)
            current = [field_item]
        else:
            current = trial
    if current:
        chunks.append(current)
    return chunks


def _curved_component_perpendicular_split_indices(
    model: FeShellModel,
    ordered: Sequence[PlateField],
) -> set[int]:
    if len(ordered) < 3:
        return set()
    component_element_ids = {
        element_id
        for field_item in ordered
        for element_id in field_item.element_ids
    }
    edge_to_elements: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for element_id, element in model.shell_elements.items():
        nodes = list(element.corner_node_ids)
        for first, second in zip(nodes, nodes[1:] + nodes[:1]):
            edge_to_elements[tuple(sorted((first, second)))].append(element_id)

    contact_flags = [
        _curved_field_has_perpendicular_plate_contact(
            model,
            field_item,
            component_element_ids,
            edge_to_elements,
        )
        for field_item in ordered
    ]
    return {
        index + 1
        for index in range(len(contact_flags) - 1)
        if contact_flags[index] and contact_flags[index + 1]
    }


def _curved_field_has_perpendicular_plate_contact(
    model: FeShellModel,
    field_item: PlateField,
    component_element_ids: set[int],
    edge_to_elements: dict[tuple[int, int], Sequence[int]],
) -> bool:
    points = [point for polygon in _field_element_polygons(model, field_item) for point in polygon]
    if not points:
        return False
    centroid = _mean_point(points)
    radial = _normalise((centroid[0], centroid[1], 0.0))
    if _length(radial) <= 1.0e-8:
        return False

    for element_id in field_item.element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        nodes = list(element.corner_node_ids)
        for first, second in zip(nodes, nodes[1:] + nodes[:1]):
            for adjacent_id in edge_to_elements.get(tuple(sorted((first, second))), ()):
                if adjacent_id == element_id or adjacent_id in component_element_ids:
                    continue
                polygons = _element_polygons_for_ids(model, (adjacent_id,))
                if not polygons:
                    continue
                adjacent_normal = _element_normal(polygons[0])
                if abs(adjacent_normal[2]) > 0.35:
                    continue
                # On the cylindrical/faceted side, true bounding bulkheads or
                # perpendicular plates have a tangential normal.  The adjacent
                # horizontal/top-bottom plate strips have radial normals and
                # must not split the circumferential panel extent.
                if abs(_dot(adjacent_normal, radial)) < 0.35:
                    return True
    return False


def _field_circumferential_angle(model: FeShellModel, field_item: PlateField) -> float:
    points = [point for polygon in _field_element_polygons(model, field_item) for point in polygon]
    centroid = _mean_point(points)
    return math.atan2(centroid[1], centroid[0])


def _curved_horizontal_extent(points: Sequence[Point3D]) -> float:
    if len(points) < 2:
        return 0.0
    radii = [math.hypot(point[0], point[1]) for point in points]
    mean_radius = sum(radii) / len(radii)
    angles = sorted(math.atan2(point[1], point[0]) for point in points)
    if len(angles) < 2 or mean_radius <= 1.0e-8:
        return 0.0
    gaps = [
        (angles[index + 1] - angles[index], index)
        for index in range(len(angles) - 1)
    ]
    wrap_gap = (angles[0] + 2.0 * math.pi - angles[-1], len(angles) - 1)
    largest_gap, gap_index = max([*gaps, wrap_gap], key=lambda item: item[0])
    if gap_index == len(angles) - 1:
        unwrapped = angles
    else:
        unwrapped = [angle if angle >= angles[gap_index + 1] else angle + 2.0 * math.pi for angle in angles]
    angle_span = max(unwrapped) - min(unwrapped)
    arc_length = mean_radius * angle_span
    chord_extent = max(
        math.hypot(first[0] - second[0], first[1] - second[1])
        for first in points
        for second in points
    )
    return max(arc_length, chord_extent)


def _station_interval_index(value: float, stations: Sequence[float], tolerance: float) -> int | None:
    if len(stations) < 2:
        return None
    if value < stations[0] - tolerance or value > stations[-1] + tolerance:
        return None
    for index, (lower, upper) in enumerate(zip(stations[:-1], stations[1:])):
        is_last = index == len(stations) - 2
        if lower - tolerance <= value < upper - tolerance:
            return index
        if is_last and lower - tolerance <= value <= upper + tolerance:
            return index
    centers = [abs(value - (stations[index] + stations[index + 1]) * 0.5) for index in range(len(stations) - 1)]
    return min(range(len(centers)), key=centers.__getitem__)


def _patch_local_axes_from_polygons(polygons: Sequence[Sequence[Point3D]], normal: Vector3D) -> tuple[Vector3D, Vector3D]:
    direction_clusters: list[tuple[Vector3D, float]] = []
    for polygon in polygons:
        if len(polygon) < 2:
            continue
        for start, end in zip(polygon, [*polygon[1:], polygon[0]]):
            edge = _project_to_plane(_subtract(end, start), normal)
            edge_length = _length(edge)
            if edge_length <= 1.0e-8:
                continue
            direction = _canonical_direction(_normalise(edge))
            for cluster_index, (cluster_direction, cluster_weight) in enumerate(direction_clusters):
                dot_value = _dot(direction, cluster_direction)
                if abs(dot_value) < 0.985:
                    continue
                if dot_value < 0.0:
                    direction = (-direction[0], -direction[1], -direction[2])
                combined = (
                    cluster_direction[0] * cluster_weight + direction[0] * edge_length,
                    cluster_direction[1] * cluster_weight + direction[1] * edge_length,
                    cluster_direction[2] * cluster_weight + direction[2] * edge_length,
                )
                direction_clusters[cluster_index] = (_normalise(combined), cluster_weight + edge_length)
                break
            else:
                direction_clusters.append((direction, edge_length))

    if not direction_clusters:
        points = [point for polygon in polygons for point in polygon]
        return _patch_local_axes_from_points(points, normal)

    direction_clusters.sort(key=lambda item: item[1], reverse=True)
    local_u = direction_clusters[0][0]
    local_v_candidate: Vector3D | None = None
    for direction, _weight in direction_clusters[1:]:
        transverse = (
            direction[0] - local_u[0] * _dot(direction, local_u),
            direction[1] - local_u[1] * _dot(direction, local_u),
            direction[2] - local_u[2] * _dot(direction, local_u),
        )
        if _length(transverse) > 0.15:
            local_v_candidate = transverse
            break
    if local_v_candidate is None:
        local_v = _normalise(_cross(normal, local_u))
    else:
        local_v = _normalise(local_v_candidate)
        if _dot(_cross(local_u, local_v), normal) < 0.0:
            local_v = (-local_v[0], -local_v[1], -local_v[2])
    if _length(local_v) <= 1.0e-8:
        local_v = _normalise(_cross(normal, local_u))
    return local_u, local_v


def _canonical_direction(direction: Vector3D) -> Vector3D:
    dominant_index = max(range(3), key=lambda index: abs(direction[index]))
    if direction[dominant_index] < 0.0:
        return (-direction[0], -direction[1], -direction[2])
    return direction


def _patch_local_axes_from_points(points: Sequence[Point3D], normal: Vector3D) -> tuple[Vector3D, Vector3D]:
    bbox = _bbox(points)
    axis_vectors: tuple[Vector3D, ...] = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    candidates: list[tuple[float, Vector3D]] = []
    for index, axis in enumerate(axis_vectors):
        projected = _project_to_plane(axis, normal)
        if _length(projected) > 1.0e-8:
            candidates.append((bbox[index][1] - bbox[index][0], projected))
    if not candidates:
        return (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    local_u = sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
    local_v = _normalise(_cross(normal, local_u))
    if _length(local_v) <= 1.0e-8:
        local_v = sorted(candidates, key=lambda item: item[0])[-1][1]
    return local_u, local_v


def _point_bounds_along(points: Sequence[Point3D], direction: Vector3D) -> tuple[float, float]:
    values = [_dot(point, direction) for point in points]
    return min(values), max(values)


def _sesam_split_stations(
    lower: float,
    upper: float,
    members: Sequence[InferredMember],
    tolerance: float,
) -> list[float]:
    stations = [
        member.station
        for member in members
        if lower + tolerance < member.station < upper - tolerance
    ]
    return _unique_sorted([lower, *stations, upper], tolerance=tolerance)


def _sesam_merge_short_intervals(stations: Sequence[float], min_interval: float) -> list[float]:
    if min_interval <= 0.0 or len(stations) <= 2:
        return list(stations)
    result = [float(stations[0])]
    for station in stations[1:-1]:
        if float(station) - result[-1] >= min_interval:
            result.append(float(station))
    upper = float(stations[-1])
    if upper - result[-1] < min_interval and len(result) > 1:
        result.pop()
    if not result or not math.isclose(result[-1], upper, rel_tol=0.0, abs_tol=1.0e-12):
        result.append(upper)
    return result


def _sesam_beam_member(
    beam: FeBeamElement,
    prefix: str,
    index: int,
    direction: Vector3D,
    station: float,
    *,
    run_length_m: float = 0.0,
) -> InferredMember:
    cross = beam.cross_section or {}
    web_height = float(cross.get("web_height") or 0.0)
    role = "girder" if web_height > 0.6 else "stiffener"
    return InferredMember(
        member_id=f"{prefix}_{index:03d}",
        role=role,
        section_type=str(cross.get("section_type") or "FB"),
        web_patch_id=f"beam_{beam.element_id}",
        flange_patch_id=None,
        direction=direction,
        station=station,
        web_height_m=web_height,
        flange_width_m=_safe_float(cross.get("flange_width")),
        web_thickness_m=_safe_float(cross.get("web_thickness")),
        flange_thickness_m=_safe_float(cross.get("flange_thickness")),
        thickness_source="SESAM beam section",
        run_length_m=max(float(run_length_m), 0.0),
        diagnostics=(f"SESAM beam section {cross.get('name', beam.property_id)}",),
    )


def _filter_sesam_sustained_beam_members(
    members: Sequence[InferredMember],
    tolerance: float,
    *,
    min_required_length: float,
) -> list[InferredMember]:
    if not members:
        return []
    groups: list[list[InferredMember]] = []
    for member in sorted(members, key=lambda item: item.station):
        for group in groups:
            if abs(member.station - group[0].station) <= tolerance:
                group.append(member)
                break
        else:
            groups.append([member])

    kept: list[InferredMember] = []
    for group in groups:
        if any(member.role == "girder" for member in group):
            kept.extend(group)
            continue
        total_run = sum(max(member.run_length_m, 0.0) for member in group)
        if total_run >= min_required_length:
            kept.extend(group)
    return kept


def _filter_sesam_sustained_boundary_members(
    members: Sequence[InferredMember],
    tolerance: float,
    *,
    min_required_length: float,
) -> list[InferredMember]:
    if not members:
        return []
    groups: list[list[InferredMember]] = []
    for member in sorted(members, key=lambda item: item.station):
        for group in groups:
            if abs(member.station - group[0].station) <= tolerance:
                group.append(member)
                break
        else:
            groups.append([member])

    kept: list[InferredMember] = []
    for group in groups:
        total_run = sum(max(member.run_length_m, 0.0) for member in group)
        if total_run >= min_required_length:
            kept.extend(group)
    return kept


def _sesam_out_of_plane_plate_members(
    model: FeShellModel,
    patch: SurfacePatch,
    local_u: Vector3D,
    local_v: Vector3D,
    normal: Vector3D,
    u_bounds: tuple[float, float],
    v_bounds: tuple[float, float],
    plane_tolerance: float,
    station_tolerance: float,
    overlap_tolerance: float,
) -> tuple[list[InferredMember], list[InferredMember]]:
    patch_element_ids = set(patch.element_ids)
    u_min, u_max = u_bounds
    v_min, v_max = v_bounds
    u_members: list[InferredMember] = []
    v_members: list[InferredMember] = []

    for element_id, element in model.shell_elements.items():
        if element_id in patch_element_ids:
            continue
        polygon = [model.nodes[node_id] for node_id in element.corner_node_ids if node_id in model.nodes]
        if len(polygon) < 3:
            continue
        element_normal = _element_normal(polygon)
        if _length(element_normal) <= 1.0e-8:
            continue
        if abs(_dot(_normalise(element_normal), normal)) > 0.88:
            continue
        for start, end in zip(polygon, [*polygon[1:], polygon[0]]):
            start_distance = abs(_dot(start, normal) - patch.offset)
            end_distance = abs(_dot(end, normal) - patch.offset)
            if start_distance > plane_tolerance or end_distance > plane_tolerance:
                continue
            tangent_in_plane = _project_to_plane(_subtract(end, start), normal)
            if _length(tangent_in_plane) <= 1.0e-8:
                continue
            tangent_in_plane = _normalise(tangent_in_plane)
            align_u = abs(_dot(tangent_in_plane, local_u))
            align_v = abs(_dot(tangent_in_plane, local_v))
            if max(align_u, align_v) < 0.86:
                continue
            projected = [_dot(point, local_u) for point in (start, end)]
            transverse = [_dot(point, local_v) for point in (start, end)]
            if align_u >= align_v:
                run_min, run_max = min(projected), max(projected)
                station = sum(transverse) / len(transverse)
                if max(transverse) - min(transverse) > station_tolerance * 2.0:
                    continue
                if station < v_min - station_tolerance or station > v_max + station_tolerance:
                    continue
                run_length = max(min(run_max, u_max) - max(run_min, u_min), 0.0)
                if run_length < overlap_tolerance:
                    continue
                u_members.append(
                    _sesam_plate_boundary_member(
                        "plate_u",
                        len(u_members) + 1,
                        tangent_in_plane,
                        min(max(station, v_min), v_max),
                        element_id,
                        run_length_m=run_length,
                    )
                )
            else:
                run_min, run_max = min(transverse), max(transverse)
                station = sum(projected) / len(projected)
                if max(projected) - min(projected) > station_tolerance * 2.0:
                    continue
                if station < u_min - station_tolerance or station > u_max + station_tolerance:
                    continue
                run_length = max(min(run_max, v_max) - max(run_min, v_min), 0.0)
                if run_length < overlap_tolerance:
                    continue
                v_members.append(
                    _sesam_plate_boundary_member(
                        "plate_v",
                        len(v_members) + 1,
                        tangent_in_plane,
                        min(max(station, u_min), u_max),
                        element_id,
                        run_length_m=run_length,
                    )
                )

    return (
        _merge_sesam_members(u_members, station_tolerance),
        _merge_sesam_members(v_members, station_tolerance),
    )


def _sesam_internal_free_edge_members(
    model: FeShellModel,
    patch: SurfacePatch,
    local_u: Vector3D,
    local_v: Vector3D,
    normal: Vector3D,
    u_bounds: tuple[float, float],
    v_bounds: tuple[float, float],
    station_tolerance: float,
    overlap_tolerance: float,
) -> tuple[list[InferredMember], list[InferredMember]]:
    patch_element_ids = set(patch.element_ids)
    if not patch_element_ids:
        return [], []
    u_min, u_max = u_bounds
    v_min, v_max = v_bounds
    edge_to_patch_elements: defaultdict[tuple[int, int], list[int]] = defaultdict(list)
    for element_id in patch_element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        nodes = list(element.corner_node_ids)
        for first, second in zip(nodes, nodes[1:] + nodes[:1]):
            edge_to_patch_elements[tuple(sorted((first, second)))].append(element_id)

    u_candidates: list[tuple[float, Vector3D, int, float]] = []
    v_candidates: list[tuple[float, Vector3D, int, float]] = []
    for edge, owner_ids in edge_to_patch_elements.items():
        if len(owner_ids) != 1:
            continue
        if edge[0] not in model.nodes or edge[1] not in model.nodes:
            continue
        start = model.nodes[edge[0]]
        end = model.nodes[edge[1]]
        tangent_in_plane = _project_to_plane(_subtract(end, start), normal)
        if _length(tangent_in_plane) <= 1.0e-8:
            continue
        tangent_in_plane = _normalise(tangent_in_plane)
        align_u = abs(_dot(tangent_in_plane, local_u))
        align_v = abs(_dot(tangent_in_plane, local_v))
        if max(align_u, align_v) < 0.86:
            continue
        projected = [_dot(point, local_u) for point in (start, end)]
        transverse = [_dot(point, local_v) for point in (start, end)]
        if align_u >= align_v:
            run_min, run_max = min(projected), max(projected)
            station = sum(transverse) / len(transverse)
            if max(transverse) - min(transverse) > station_tolerance * 2.0:
                continue
            if station <= v_min + station_tolerance or station >= v_max - station_tolerance:
                continue
            if min(run_max, u_max) - max(run_min, u_min) < overlap_tolerance:
                continue
            u_candidates.append((station, tangent_in_plane, owner_ids[0], max(run_max - run_min, 0.0)))
        else:
            run_min, run_max = min(transverse), max(transverse)
            station = sum(projected) / len(projected)
            if max(projected) - min(projected) > station_tolerance * 2.0:
                continue
            if station <= u_min + station_tolerance or station >= u_max - station_tolerance:
                continue
            if min(run_max, v_max) - max(run_min, v_min) < overlap_tolerance:
                continue
            v_candidates.append((station, tangent_in_plane, owner_ids[0], max(run_max - run_min, 0.0)))

    return (
        _sesam_free_edge_members_from_candidates(
            "free_u",
            u_candidates,
            station_tolerance,
            min_required_length=min(max((u_max - u_min) * 0.20, overlap_tolerance * 2.0), 0.80),
        ),
        _sesam_free_edge_members_from_candidates(
            "free_v",
            v_candidates,
            station_tolerance,
            min_required_length=min(max((v_max - v_min) * 0.20, overlap_tolerance * 2.0), 0.80),
        ),
    )


def _sesam_free_edge_members_from_candidates(
    prefix: str,
    candidates: Sequence[tuple[float, Vector3D, int, float]],
    tolerance: float,
    *,
    min_required_length: float,
) -> list[InferredMember]:
    groups: list[list[tuple[float, Vector3D, int, float]]] = []
    for candidate in sorted(candidates, key=lambda item: item[0]):
        for group in groups:
            if abs(candidate[0] - group[0][0]) <= tolerance:
                group.append(candidate)
                break
        else:
            groups.append([candidate])

    members: list[InferredMember] = []
    for group in groups:
        total_length = sum(item[3] for item in group)
        if total_length < min_required_length:
            continue
        station = sum(item[0] * item[3] for item in group) / max(total_length, 1.0e-12)
        representative = max(group, key=lambda item: item[3])
        members.append(
            _sesam_plate_boundary_member(
                prefix,
                len(members) + 1,
                representative[1],
                station,
                representative[2],
                source="SESAM sustained internal free plate edge",
                run_length_m=total_length,
            )
        )
    return members


def _sesam_plate_boundary_member(
    prefix: str,
    index: int,
    direction: Vector3D,
    station: float,
    element_id: int,
    *,
    source: str = "SESAM out-of-plane plate edge",
    run_length_m: float = 0.0,
) -> InferredMember:
    return InferredMember(
        member_id=f"{prefix}_{index:03d}",
        role="plate_boundary",
        section_type="plate",
        web_patch_id=f"shell_{element_id}",
        flange_patch_id=None,
        direction=direction,
        station=station,
        web_height_m=0.0,
        flange_width_m=None,
        thickness_source=source,
        run_length_m=max(float(run_length_m), 0.0),
        diagnostics=(source,),
    )


def _merge_sesam_members(
    members: Sequence[InferredMember],
    tolerance: float,
) -> list[InferredMember]:
    groups: list[list[InferredMember]] = []
    for member in sorted(members, key=lambda item: item.station):
        for group in groups:
            if abs(member.station - group[0].station) <= tolerance:
                group.append(member)
                break
        else:
            groups.append([member])
    merged: list[InferredMember] = []
    for index, group in enumerate(groups, start=1):
        representative = max(group, key=lambda item: item.web_height_m)
        station = sum(item.station for item in group) / len(group)
        merged.append(
            InferredMember(
                member_id=f"{representative.member_id.rsplit('_', 1)[0]}_{index:03d}",
                role=representative.role,
                section_type=representative.section_type,
                web_patch_id=representative.web_patch_id,
                flange_patch_id=representative.flange_patch_id,
                direction=representative.direction,
                station=station,
                web_height_m=representative.web_height_m,
                flange_width_m=representative.flange_width_m,
                web_thickness_m=representative.web_thickness_m,
                flange_thickness_m=representative.flange_thickness_m,
                thickness_source=representative.thickness_source,
                run_length_m=sum(max(item.run_length_m, 0.0) for item in group),
                diagnostics=representative.diagnostics + (f"merged {len(group)} collinear beam elements",),
            )
        )
    return merged


def _deduplicate_plate_field_elements(model: FeShellModel, fields: Sequence[PlateField]) -> list[PlateField]:
    seen: set[int] = set()
    deduplicated: list[PlateField] = []
    for field_item in fields:
        element_ids = tuple(element_id for element_id in field_item.element_ids if element_id not in seen)
        if not element_ids:
            continue
        seen.update(element_ids)
        if element_ids == field_item.element_ids:
            deduplicated.append(field_item)
            continue
        deduplicated.append(
            replace(
                field_item,
                element_ids=element_ids,
                bbox=_bbox_for_elements(model, element_ids),
                shell_section_thickness_m=_shell_section_thickness_for_elements(model, element_ids),
                diagnostics=field_item.diagnostics + ("overlapping shell elements assigned to first owning panel",),
            )
        )
    return deduplicated


def _renumber_plate_fields(fields: Sequence[PlateField]) -> list[PlateField]:
    return [
        replace(field_item, field_id=f"field_{index:03d}")
        for index, field_item in enumerate(fields, start=1)
    ]


def summarize_plate_fields(fields: Sequence[PlateField]) -> list[dict[str, Any]]:
    """Flatten inferred plate fields for JSON/CSV-style inspection."""

    summary: list[dict[str, Any]] = []
    for field_item in fields:
        members = [
            {
                "member_id": member.member_id,
                "role": member.role,
                "section_type": member.section_type,
                "web_height_m": member.web_height_m,
                "flange_width_m": member.flange_width_m,
                "web_thickness_m": member.web_thickness_m,
                "flange_thickness_m": member.flange_thickness_m,
                "thickness_source": member.thickness_source,
                "station_m": member.station,
                "web_patch_id": member.web_patch_id,
                "flange_patch_id": member.flange_patch_id,
                "confidence": member.confidence,
                "diagnostics": list(member.diagnostics),
            }
            for member in field_item.members
        ]
        summary.append(
            {
                "field_id": field_item.field_id,
                "base_patch_id": field_item.base_patch_id,
                "element_count": len(field_item.element_ids),
                "span_m": field_item.span_m,
                "spacing_m": field_item.spacing_m,
                "transverse_bounds": list(field_item.transverse_bounds),
                "attached_member_ids": list(field_item.attached_member_ids),
                "shell_section_thickness_m": field_item.shell_section_thickness_m,
                "bbox": [list(bounds) for bounds in field_item.bbox],
                "confidence": field_item.confidence,
                "diagnostics": list(field_item.diagnostics),
                "members": members,
            }
        )
    return summary


def plot_plate_fields(
    model: FeShellModel,
    fields: Sequence[PlateField] | None = None,
    *,
    output_path: str | os.PathLike[str] | None = None,
    annotate: bool = True,
    show_members: bool = True,
    field_values: dict[str, float] | None = None,
    value_label: str = "UF",
    cmap_name: str = "tab20",
    dpi: int = 180,
) -> Any:
    """Plot inferred buckling panels in the base-plate plane.

    Axes are the inferred member direction and transverse direction.  By
    default each ``PlateField`` gets a distinct diagnostic color; when
    ``field_values`` is supplied, those scalar values drive the panel colors and
    a colorbar is added.
    """

    from matplotlib import colors as matplotlib_colors
    from matplotlib import pyplot as plt
    from matplotlib.patches import Rectangle

    fields = list(infer_plate_fields(model) if fields is None else fields)
    patches = detect_surface_patches(model)
    inference = _infer_members_from_patches(model, patches) if patches else None

    fig, ax = plt.subplots(figsize=_plot_figure_size(fields), dpi=dpi)
    scalar_values = _finite_field_values(field_values)
    if scalar_values:
        scalar_cmap_name = "RdYlGn_r" if cmap_name == "tab20" else cmap_name
        cmap = plt.get_cmap(scalar_cmap_name)
        value_min = min(min(scalar_values.values()), 0.0)
        value_max = max(max(scalar_values.values()), 1.0)
        if math.isclose(value_min, value_max):
            value_max = value_min + 1.0
        norm = matplotlib_colors.Normalize(vmin=value_min, vmax=value_max)
    else:
        cmap = plt.get_cmap(cmap_name, max(len(fields), 1))
        norm = None

    for index, field_item in enumerate(fields):
        lower_longitudinal, upper_longitudinal, lower_transverse, upper_transverse = _field_plot_bounds(
            field_item,
            inference.member_direction if inference is not None else (1.0, 0.0, 0.0),
            inference.transverse_direction if inference is not None else (0.0, 1.0, 0.0),
        )
        width = upper_longitudinal - lower_longitudinal
        height = upper_transverse - lower_transverse
        field_value = None if field_values is None else field_values.get(field_item.field_id)
        if norm is not None:
            color = cmap(norm(field_value)) if field_value is not None and math.isfinite(field_value) else "0.82"
        else:
            color = cmap(index % max(len(fields), 1))
        ax.add_patch(
            Rectangle(
                (lower_longitudinal, lower_transverse),
                width,
                height,
                facecolor=color,
                edgecolor="black",
                linewidth=0.8,
                alpha=0.72,
            )
        )
        if annotate and width > 0.0 and height > 0.0:
            label = field_item.field_id.replace("field_", "")
            if field_value is not None and math.isfinite(field_value):
                label = f"{label}\n{field_value:.2f}"
            ax.text(
                lower_longitudinal + width / 2.0,
                lower_transverse + height / 2.0,
                label,
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    if inference is not None and show_members:
        _plot_member_lines(ax, inference)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("member direction [m]")
    ax.set_ylabel("transverse direction [m]")
    ax.set_title(f"Discovered buckling panels ({len(fields)})" if norm is None else f"Buckling panels by {value_label}")
    ax.grid(True, color="0.88", linewidth=0.5)
    ax.autoscale_view()
    if norm is not None:
        scalar_map = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
        scalar_map.set_array([])
        colorbar = fig.colorbar(scalar_map, ax=ax, fraction=0.046, pad=0.04)
        colorbar.set_label(value_label)
    fig.tight_layout()

    if output_path is not None:
        fig.savefig(output_path, bbox_inches="tight")
    return fig


def _summary_payload(model: FeShellModel, fields: Sequence[PlateField], frd_summary: dict[str, Any] | None) -> dict[str, Any]:
    members = _unique_members(fields)
    stiffeners = [member for member in members if member.role == "stiffener"]
    girders = [member for member in members if member.role == "girder"]
    flanges = [member for member in members if member.flange_patch_id is not None]
    section_types = sorted({member.section_type for member in members})
    spacings = [field_item.spacing_m for field_item in fields if field_item.spacing_m is not None]
    return {
        "source": model.source_path,
        "node_count": len(model.nodes),
        "element_count": len(model.shell_elements),
        "field_count": len(fields),
        "member_count": len(members),
        "web_count": len(members),
        "stiffener_count": len(stiffeners),
        "girder_count": len(girders),
        "flange_count": len(flanges),
        "section_types": section_types,
        "median_spacing_m": _median(spacings) if spacings else None,
        "shell_sections": [
            {
                "elset": section.elset,
                "material": section.material,
                "thickness_m": section.thickness_m,
                "offset": section.offset,
            }
            for section in model.shell_sections
        ],
        "frd": frd_summary,
        "fields": summarize_plate_fields(fields),
    }


def _infer_members_from_patches(model: FeShellModel, patches: Sequence[SurfacePatch]) -> _PatchInference:
    base_patch = _select_base_patch(patches)
    base_normal = base_patch.normal
    base_offset = base_patch.offset

    web_candidates = [
        patch
        for patch in patches
        if patch.patch_id != base_patch.patch_id
        and abs(_dot(patch.normal, base_normal)) < 0.25
        and _patch_crosses_base_plane(patch, base_normal, base_offset)
    ]

    web_families = _parallel_patch_families(web_candidates)
    stiffener_patches = web_families[0] if web_families else []
    girder_patches = [patch for family in web_families[1:] for patch in family]

    if stiffener_patches:
        transverse_direction = _normalise(
            tuple(sum(patch.normal[index] for patch in stiffener_patches) for index in range(3))
        )
        transverse_direction = _project_to_plane(transverse_direction, base_normal)
    else:
        transverse_direction = _fallback_base_transverse_direction(base_patch, base_normal)
    member_direction = _normalise(_cross(transverse_direction, base_normal))
    if _length(member_direction) <= 0.0:
        member_direction = _fallback_member_direction(base_patch, transverse_direction)

    flange_candidates = [
        patch
        for patch in patches
        if patch.patch_id != base_patch.patch_id
        and abs(_dot(patch.normal, base_normal)) > 0.95
        and _dot(patch.centroid, base_normal) > base_offset + 1.0e-8
    ]

    members: list[InferredMember] = []
    stiffeners = _members_from_web_patches(
        stiffener_patches,
        flange_candidates,
        base_normal,
        transverse_direction,
        member_direction,
        "stiffener",
        "stiffener",
        1,
        model,
    )
    girders = _members_from_web_patches(
        girder_patches,
        flange_candidates,
        base_normal,
        member_direction,
        transverse_direction,
        "girder",
        "girder",
        1,
        model,
    )
    members.extend(stiffeners)
    members.extend(girders)

    if getattr(model, "beam_elements", None):
        beam_stiffeners = []
        beam_girders = []
        for element in model.beam_elements.values():
            nodes = [model.nodes[n] for n in element.node_ids]
            centroid = _mean_point(nodes)
            if len(nodes) >= 2:
                tangent = _normalise((nodes[-1][0]-nodes[0][0], nodes[-1][1]-nodes[0][1], nodes[-1][2]-nodes[0][2]))
            else:
                tangent = member_direction

            stiff_align = abs(_dot(tangent, member_direction))
            gird_align = abs(_dot(tangent, transverse_direction))

            if stiff_align > gird_align:
                # Stiffener! Station is along transverse_direction
                station = _dot(centroid, transverse_direction)
                beam_stiffeners.append((station, element, tangent))
            else:
                # Girder! Station is along member_direction
                station = _dot(centroid, member_direction)
                beam_girders.append((station, element, tangent))

        def group_flat_beams(items, tolerance):
            groups = []
            for station, element, tangent in items:
                for index, (existing_station, elements, existing_tangent) in enumerate(groups):
                    if abs(station - existing_station) <= tolerance:
                        elements.append(element)
                        groups[index] = ((existing_station + station) / 2.0, elements, existing_tangent)
                        break
                else:
                    groups.append((station, [element], tangent))
            return groups

        axial_length = max((_length((model.nodes[n][0], model.nodes[n][1], model.nodes[n][2])) for n in model.nodes), default=1.0)
        linear_tolerance = max(axial_length * 1.0e-5, 1.0e-5)

        for index, (station, elements, tangent) in enumerate(group_flat_beams(beam_stiffeners, linear_tolerance), start=len(stiffeners)+1):
            cross = elements[0].cross_section
            members.append(InferredMember(
                member_id=f"beam_stiffener_{index:03d}",
                role="stiffener",
                section_type=cross.get("section_type", "L"),
                web_patch_id="beam_element",
                flange_patch_id=None,
                direction=tangent,
                station=station,
                web_height_m=cross.get("web_height", 0.0),
                flange_width_m=cross.get("flange_width", 0.0) or None,
                web_thickness_m=cross.get("web_thickness", 0.0) or None,
                flange_thickness_m=cross.get("flange_thickness", 0.0) or None,
                thickness_source="beam cross section",
                diagnostics=("inferred from beam elements",),
            ))
            stiffeners.append(members[-1])

        for index, (station, elements, tangent) in enumerate(group_flat_beams(beam_girders, linear_tolerance), start=len(girders)+1):
            cross = elements[0].cross_section
            members.append(InferredMember(
                member_id=f"beam_girder_{index:03d}",
                role="girder",
                section_type=cross.get("section_type", "T"),
                web_patch_id="beam_element",
                flange_patch_id=None,
                direction=tangent,
                station=station,
                web_height_m=cross.get("web_height", 0.0),
                flange_width_m=cross.get("flange_width", 0.0) or None,
                web_thickness_m=cross.get("web_thickness", 0.0) or None,
                flange_thickness_m=cross.get("flange_thickness", 0.0) or None,
                thickness_source="beam cross section",
                diagnostics=("inferred from beam elements",),
            ))
            girders.append(members[-1])

    return _PatchInference(
        base_patch=base_patch,
        members=tuple(members),
        stiffeners=tuple(stiffeners),
        girders=tuple(girders),
        base_normal=base_normal,
        member_direction=member_direction,
        transverse_direction=transverse_direction,
    )


def _members_from_web_patches(
    web_patches: Sequence[SurfacePatch],
    flange_candidates: Sequence[SurfacePatch],
    base_normal: Vector3D,
    station_direction: Vector3D,
    member_direction: Vector3D,
    role: str,
    id_prefix: str,
    start_index: int,
    model: FeShellModel,
) -> list[InferredMember]:
    members: list[InferredMember] = []
    for offset, web_patch in enumerate(sorted(web_patches, key=lambda patch: _dot(patch.centroid, station_direction))):
        station = _dot(web_patch.centroid, station_direction)
        web_height = _extent_along_patch(web_patch, base_normal)
        flange_patch = _matching_flange_patch(web_patch, flange_candidates, base_normal, station_direction)
        flange_width: float | None = None
        section_type = "FB"
        diagnostics = ["section dimensions inferred from shell midsurface geometry"]
        if flange_patch is not None:
            flange_width = _extent_along_patch(flange_patch, station_direction)
            lower, upper = _projected_bounds(flange_patch, station_direction)
            centre_error = abs(station - (lower + upper) / 2.0)
            if centre_error <= max(flange_width * 0.05, 1.0e-6):
                section_type = "T"
            else:
                section_type = "L"
        else:
            diagnostics.append("no matching flange patch found")

        web_thickness = _shell_section_thickness_for_patch(model, web_patch)
        flange_thickness = None if flange_patch is None else _shell_section_thickness_for_patch(model, flange_patch)
        thickness_source = "shell section metadata" if web_thickness is not None or flange_thickness is not None else None
        if thickness_source:
            diagnostics.append("nominal thickness from shell section metadata")

        members.append(
            InferredMember(
                member_id=f"{id_prefix}_{start_index + offset:03d}",
                role=role,
                section_type=section_type,
                web_patch_id=web_patch.patch_id,
                flange_patch_id=None if flange_patch is None else flange_patch.patch_id,
                direction=member_direction,
                station=station,
                web_height_m=web_height,
                flange_width_m=flange_width,
                web_thickness_m=web_thickness,
                flange_thickness_m=flange_thickness,
                thickness_source=thickness_source,
                diagnostics=tuple(diagnostics),
            )
        )
    return members


def _select_base_patch(patches: Sequence[SurfacePatch]) -> SurfacePatch:
    horizontal = [patch for patch in patches if abs(patch.normal[2]) > 0.8]
    candidates = horizontal or list(patches)
    return sorted(candidates, key=lambda patch: (-patch.area, patch.bbox[2][0], patch.patch_id))[0]


def _parallel_patch_families(patches: Sequence[SurfacePatch]) -> list[list[SurfacePatch]]:
    """Return web patch families grouped by near-parallel normals."""

    families: list[list[SurfacePatch]] = []
    for patch in sorted(patches, key=lambda item: item.patch_id):
        for family in families:
            if abs(_dot(patch.normal, family[0].normal)) > 0.95:
                family.append(patch)
                break
        else:
            families.append([patch])
    families.sort(key=lambda family: (-len(family), -sum(patch.area for patch in family), family[0].patch_id))
    return families


def _split_bounds_with_members(
    base_patch: SurfacePatch,
    direction: Vector3D,
    boundary_members: Sequence[InferredMember],
) -> list[tuple[float, float, tuple[InferredMember, ...]]]:
    lower, upper = _projected_bounds(base_patch, direction)
    internal_members = [
        member
        for member in boundary_members
        if lower + 1.0e-8 < member.station < upper - 1.0e-8
    ]
    stations = [lower] + [member.station for member in sorted(internal_members, key=lambda item: item.station)] + [upper]
    result: list[tuple[float, float, tuple[InferredMember, ...]]] = []
    for first, second in zip(stations[:-1], stations[1:]):
        if second - first <= 1.0e-10:
            continue
        attached = tuple(
            member for member in internal_members
            if abs(member.station - first) <= 1.0e-8 or abs(member.station - second) <= 1.0e-8
        )
        result.append((first, second, attached))
    return result or [(lower, upper, ())]


def _matching_flange_patch(
    web_patch: SurfacePatch,
    flange_candidates: Sequence[SurfacePatch],
    base_normal: Vector3D,
    transverse_direction: Vector3D,
) -> SurfacePatch | None:
    station = _dot(web_patch.centroid, transverse_direction)
    web_top = max(_projected_bounds(web_patch, base_normal))
    best: tuple[float, SurfacePatch] | None = None
    for flange_patch in flange_candidates:
        lower, upper = _projected_bounds(flange_patch, transverse_direction)
        width = max(upper - lower, 1.0e-9)
        if lower - max(width * 0.1, 1.0e-6) <= station <= upper + max(width * 0.1, 1.0e-6):
            height_error = abs(_dot(flange_patch.centroid, base_normal) - web_top)
            score = height_error + abs(station - (lower + upper) / 2.0) * 0.01
            if best is None or score < best[0]:
                best = (score, flange_patch)
    return None if best is None else best[1]


def _patch_crosses_base_plane(patch: SurfacePatch, base_normal: Vector3D, base_offset: float) -> bool:
    lower, upper = _projected_bounds(patch, base_normal)
    tolerance = max((upper - lower) * 1.0e-6, 1.0e-8)
    return lower - tolerance <= base_offset <= upper + tolerance and upper - lower > tolerance


def _connected_components_by_corner_edges(model: FeShellModel, element_ids: Iterable[int]) -> list[list[int]]:
    edge_to_elements: dict[tuple[int, int], list[int]] = defaultdict(list)
    element_ids = list(element_ids)
    for element_id in element_ids:
        corners = list(model.shell_elements[element_id].corner_node_ids)
        for first, second in zip(corners, corners[1:] + corners[:1]):
            edge_to_elements[tuple(sorted((first, second)))].append(element_id)

    adjacency: dict[int, set[int]] = {element_id: set() for element_id in element_ids}
    for shared_elements in edge_to_elements.values():
        if len(shared_elements) < 2:
            continue
        for element_id in shared_elements:
            adjacency[element_id].update(other for other in shared_elements if other != element_id)

    components: list[list[int]] = []
    seen: set[int] = set()
    for element_id in element_ids:
        if element_id in seen:
            continue
        stack = [element_id]
        seen.add(element_id)
        component: list[int] = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        components.append(sorted(component))
    return components


def _make_surface_patch(
    model: FeShellModel,
    patch_id: str,
    element_ids: tuple[int, ...],
    normal: Vector3D,
    offset: float,
) -> SurfacePatch:
    coords = [
        model.nodes[node_id]
        for element_id in element_ids
        for node_id in model.shell_elements[element_id].corner_node_ids
    ]
    bbox = _bbox(coords)
    area = sum(_element_area([model.nodes[node_id] for node_id in model.shell_elements[element_id].corner_node_ids])
               for element_id in element_ids)
    centroid = (
        sum(point[0] for point in coords) / len(coords),
        sum(point[1] for point in coords) / len(coords),
        sum(point[2] for point in coords) / len(coords),
    )
    return SurfacePatch(
        patch_id=patch_id,
        element_ids=element_ids,
        normal=normal,
        offset=offset,
        bbox=bbox,
        area=area,
        centroid=centroid,
    )


def _bbox_for_elements(model: FeShellModel, element_ids: Iterable[int]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    points = [
        model.nodes[node_id]
        for element_id in element_ids
        for node_id in model.shell_elements[element_id].corner_node_ids
    ]
    return _bbox(points)


def _field_element_polygons(model: FeShellModel, field_item: PlateField) -> list[list[Point3D]]:
    return _element_polygons_for_ids(model, field_item.element_ids)


def _element_polygons_for_ids(model: FeShellModel, element_ids: Iterable[int]) -> list[list[Point3D]]:
    polygons: list[list[Point3D]] = []
    for element_id in element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        polygon = [model.nodes[node_id] for node_id in element.corner_node_ids if node_id in model.nodes]
        if len(polygon) >= 3:
            polygons.append(polygon)
    return polygons


def _field_representative_normal(model: FeShellModel, field_item: PlateField) -> Vector3D:
    for polygon in _field_element_polygons(model, field_item):
        normal = _element_normal(polygon)
        if _length(normal) > 0.0:
            return _normalise(normal)
    corners = _field_bbox_representative_polygon(field_item)
    normal = _element_normal(corners)
    return _normalise(normal) if _length(normal) > 0.0 else (0.0, 0.0, 1.0)


def _field_local_axes(model: FeShellModel, field_item: PlateField) -> tuple[Vector3D, Vector3D]:
    polygons = _field_element_polygons(model, field_item)
    points = [point for polygon in polygons for point in polygon]
    normal = _field_representative_normal(model, field_item)
    if len(points) >= 3:
        return _patch_local_axes_from_polygons(polygons, normal)
    corners = _field_bbox_representative_polygon(field_item)
    return _patch_local_axes_from_points(corners, normal)


def _field_bbox_representative_polygon(field_item: PlateField) -> list[Point3D]:
    bbox = field_item.bbox
    x0, x1 = bbox[0]
    y0, y1 = bbox[1]
    z0, z1 = bbox[2]
    ranges = [abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)]
    collapsed_axis = min(range(3), key=lambda index: ranges[index])
    if collapsed_axis == 0:
        x = (x0 + x1) / 2.0
        return [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    if collapsed_axis == 1:
        y = (y0 + y1) / 2.0
        return [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
    z = (z0 + z1) / 2.0
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


def _mean_point(points: Sequence[Point3D]) -> Point3D:
    if not points:
        return (0.0, 0.0, 0.0)
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
        sum(point[2] for point in points) / len(points),
    )


def _set_equal_3d_limits(ax: Any, points: Sequence[Point3D]) -> None:
    if not points:
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_zlim(0.0, 1.0)
        return
    bbox = _bbox(points)
    centers = [(axis[0] + axis[1]) / 2.0 for axis in bbox]
    half_span = max((axis[1] - axis[0]) / 2.0 for axis in bbox)
    half_span = max(half_span, 0.5)
    pad = half_span * 0.08
    half_span += pad
    ax.set_xlim(centers[0] - half_span, centers[0] + half_span)
    ax.set_ylim(centers[1] - half_span, centers[1] + half_span)
    ax.set_zlim(centers[2] - half_span, centers[2] + half_span)
    try:
        ax.set_box_aspect((1.0, 1.0, 1.0))
    except Exception:
        pass


def _bbox(points: Sequence[Point3D]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    return tuple((min(point[index] for point in points), max(point[index] for point in points)) for index in range(3))  # type: ignore[return-value]


def _bbox_corners(
    bbox: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> list[Point3D]:
    return [(x, y, z) for x in bbox[0] for y in bbox[1] for z in bbox[2]]


def _shell_section_thickness_for_patch(model: FeShellModel, patch: SurfacePatch) -> float | None:
    return _shell_section_thickness_for_elements(model, patch.element_ids)


def _unique_members(fields: Sequence[PlateField]) -> list[InferredMember]:
    by_id: dict[str, InferredMember] = {}
    for field_item in fields:
        for member in field_item.members:
            by_id[member.member_id] = member
    return [by_id[key] for key in sorted(by_id)]


def _buckling_uf_by_field(buckling_results: Sequence[dict[str, Any]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in buckling_results:
        field_id = item.get("field_id")
        if not field_id:
            continue
        uf = _selected_uf_from_buckling_result(item)
        if uf is not None:
            values[str(field_id)] = uf
    return values


def _selected_uf_from_buckling_result(item: dict[str, Any]) -> float | None:
    """Return the governing UF from one stored panel calculation.

    API result dictionaries have changed shape over time.  Do not require one
    exact key layout; search recognised UF/utilisation keys recursively and use
    the governing finite value.
    """
    if not isinstance(item, dict):
        return None
    result = item.get("result", item)
    if not isinstance(result, dict):
        return _first_finite_float(result)
    cylinder_uf = _find_cylinder_usage_factor(result)
    if cylinder_uf is not None:
        return cylinder_uf
    return _find_usage_factor(result)


def _find_cylinder_usage_factor(result: dict[str, Any]) -> float | None:
    values: list[float] = []
    for key in (
        "Unstiffened shell",
        "Unstiffened conical shell",
        "Longitudinal stiffened shell",
        "Ring stiffened shell",
        "Heavy ring frame",
    ):
        uf = _first_finite_float(result.get(key))
        if uf is not None:
            values.append(uf)
    need_column = result.get("Need to check column buckling", False) is True
    if need_column:
        column_uf = _first_finite_float(result.get("Column stability UF"))
        if column_uf is not None:
            values.append(column_uf)
    return max(values) if values else None


def _usage_key_priority(key: object) -> int:
    """Return a positive priority for keys that represent utilisation factors."""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(key).lower()).strip()
    exact = {
        "selected uf": 100,
        "governing uf": 100,
        "ultimate uf": 95,
        "buckling uf": 95,
        "actual usage factor": 95,
        "usage factor": 90,
        "utilization factor": 90,
        "utilisation factor": 90,
        "plate buckling": 85,
        "overpressure plate side": 80,
        "overpressure stiffener side": 80,
        "overpressure girder side": 80,
        "resistance between stiffeners": 80,
        "shear capacity": 80,
        "uf": 80,
    }
    if normalized in exact:
        return exact[normalized]
    words = set(normalized.split())
    if "uf" in words:
        return 70
    if "usage" in words and "factor" in words:
        return 65
    if ("utilization" in words or "utilisation" in words) and "factor" in words:
        return 65
    if "buckling" in words and ("factor" in words or "ratio" in words):
        return 55
    return 0


def _find_usage_factor(value: object) -> float | None:
    """Find the governing finite UF in nested API output.

    Earlier code returned the first numeric scalar found during recursion.
    That could miss valid UFs in newer result layouts or accidentally select a
    confidence/geometry value.  Only UF-like keys are considered first; the
    governing value is the maximum finite candidate.
    """
    candidates: list[tuple[int, float]] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                priority = _usage_key_priority(key)
                if priority:
                    numeric = _first_finite_float(nested)
                    if numeric is not None:
                        candidates.append((priority, numeric))
                visit(nested)
        elif isinstance(item, (list, tuple, set)):
            for nested in item:
                visit(nested)

    visit(value)
    if candidates:
        top_priority = max(priority for priority, _number in candidates)
        if top_priority >= 100:
            # "selected UF"/"governing UF" already reflect the chosen
            # buckling/ultimate acceptance basis, so other UF keys in the same
            # result must not override the basis with a larger value.
            return max(number for priority, number in candidates if priority >= 100)
        # Legacy prescriptive results have no selected key: the governing UF
        # is the largest calculated plate/stiffener/girder sub-check.
        return max(number for _priority, number in candidates)

    # Compatibility fallback for APIs returning a bare scalar/list as result.
    if not isinstance(value, dict):
        return _first_finite_float(value)
    return None


def _first_finite_float(value: object) -> float | None:
    direct = _safe_float(value)
    if direct is not None:
        return direct
    if isinstance(value, dict):
        values = [
            nested
            for nested_value in value.values()
            for nested in [_first_finite_float(nested_value)]
            if nested is not None
        ]
        return max(values) if values else None
    if isinstance(value, (list, tuple, set)):
        values = [
            nested
            for item in value
            for nested in [_first_finite_float(item)]
            if nested is not None
        ]
        return max(values) if values else None
    return None


def _finite_field_values(field_values: dict[str, float] | None) -> dict[str, float]:
    if not field_values:
        return {}
    return {
        str(key): float(value)
        for key, value in field_values.items()
        if _safe_float(value) is not None
    }


def _field_stress_samples(
    field_item: PlateField,
    frd_stress: FrdStressResult,
    base_normal: Vector3D,
    base_offset: float,
    member_direction: Vector3D,
    transverse_direction: Vector3D,
) -> list[tuple[float, float, float, float, float]]:
    if frd_stress.element_stress:
        element_samples: list[tuple[float, float, float, float, float]] = []
        for element_id in field_item.element_ids:
            stress = frd_stress.element_stress.get(element_id)
            node_ids = frd_stress.element_nodes.get(element_id, ())
            points = [frd_stress.nodes[node_id] for node_id in node_ids if node_id in frd_stress.nodes]
            if stress is None or len(points) < 3:
                continue
            centroid = _mean_point(points)
            sigma_x, sigma_y, tau_xy = _project_frd_stress(
                frd_stress.components,
                stress,
                member_direction,
                transverse_direction,
            )
            distance_to_mid_surface = abs(_dot(centroid, base_normal) - base_offset)
            element_samples.append(
                (_dot(centroid, transverse_direction), sigma_x, sigma_y, tau_xy, distance_to_mid_surface)
            )
        if element_samples:
            return [sample[:4] + (1.0,) for sample in element_samples]

    all_samples: list[tuple[float, float, float, float, float]] = []
    seen_node_ids: set[int] = set()
    for element_id in field_item.element_ids:
        for node_id in frd_stress.element_nodes.get(element_id, ()):
            if node_id in seen_node_ids or node_id not in frd_stress.nodal_stress:
                continue
            point = frd_stress.nodes.get(node_id)
            if point is None:
                continue
            seen_node_ids.add(node_id)
            sigma_x, sigma_y, tau_xy = _project_frd_stress(
                frd_stress.components,
                frd_stress.nodal_stress[node_id],
                member_direction,
                transverse_direction,
            )
            distance_to_mid_surface = abs(_dot(point, base_normal) - base_offset)
            all_samples.append((_dot(point, transverse_direction), sigma_x, sigma_y, tau_xy, distance_to_mid_surface))

    if not all_samples:
        return []

    mid_surface_tolerance = max((field_item.shell_section_thickness_m or 0.0) * 0.2, 1.0e-8)
    mid_surface_samples = [sample for sample in all_samples if sample[4] <= mid_surface_tolerance]
    selected = mid_surface_samples or all_samples
    return [sample[:4] + (1.0,) for sample in selected]


def _field_element_stress_samples(
    model: FeShellModel,
    field_item: PlateField,
    frd_stress: FrdStressResult,
    member_direction: Vector3D,
    transverse_direction: Vector3D,
) -> list[tuple[float, float, float, float, float]]:
    samples: list[tuple[float, float, float, float, float]] = []
    for element_id in field_item.element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        corner_points = [model.nodes[node_id] for node_id in element.corner_node_ids if node_id in model.nodes]
        if len(corner_points) < 3:
            continue
        if element_id in frd_stress.element_stress:
            sigma_x, sigma_y, tau_xy = _project_frd_stress(
                frd_stress.components,
                frd_stress.element_stress[element_id],
                member_direction,
                transverse_direction,
            )
        else:
            projected_values = []
            for node_id in frd_stress.element_nodes.get(element_id, element.corner_node_ids):
                if node_id not in frd_stress.nodal_stress:
                    continue
                projected_values.append(
                    _project_frd_stress(
                        frd_stress.components,
                        frd_stress.nodal_stress[node_id],
                        member_direction,
                        transverse_direction,
                    )
                )
            if not projected_values:
                continue
            sigma_x = _mean(value[0] for value in projected_values)
            sigma_y = _mean(value[1] for value in projected_values)
            tau_xy = _mean(value[2] for value in projected_values)
        centroid = _mean_point(corner_points)
        area = _element_area(corner_points)
        samples.append(
            (
                _dot(centroid, transverse_direction),
                sigma_x,
                sigma_y,
                tau_xy,
                max(area, 1.0e-12),
            )
        )
    return samples


def _weighted_mean(values: Iterable[tuple[float, float]]) -> float:
    weighted_sum = 0.0
    weight_sum = 0.0
    for value, weight in values:
        weighted_sum += float(value) * float(weight)
        weight_sum += float(weight)
    return 0.0 if weight_sum == 0.0 else weighted_sum / weight_sum


def _reduced_panel_stress_from_samples(
    field_item: PlateField,
    samples: Sequence[tuple[float, float, float, float, float]],
    reduction_method: str,
    *,
    transverse_edge_fraction: float,
    centre_strip_fraction: float,
) -> PanelStress:
    selected_samples = list(samples)
    lower_transverse, upper_transverse = field_item.transverse_bounds
    width = max(upper_transverse - lower_transverse, 1.0e-9)

    if reduction_method == "Centre strip mean":
        centre = 0.5 * (lower_transverse + upper_transverse)
        half_strip = max(width * centre_strip_fraction * 0.5, 1.0e-9)
        selected_samples = [
            sample for sample in samples
            if abs(sample[0] - centre) <= half_strip
        ]
        if not selected_samples:
            ordered = sorted(samples, key=lambda sample: abs(sample[0] - centre))
            selected_samples = ordered[: max(1, int(math.ceil(len(ordered) * centre_strip_fraction)))]

    sigma_x = [-sample[1] / 1.0e6 for sample in selected_samples]
    sigma_y = [-sample[2] / 1.0e6 for sample in selected_samples]
    tau_xy = [sample[3] / 1.0e6 for sample in selected_samples]
    weights = [sample[4] for sample in selected_samples]

    if reduction_method == "Whole panel nodal mean":
        weights = [1.0 for _sample in selected_samples]

    sigma_x_nominal = _weighted_mean(zip(sigma_x, weights))
    sigma_y_nominal = _weighted_mean(zip(sigma_y, weights))
    tau_xy_nominal = _weighted_mean(zip(tau_xy, weights))

    if reduction_method == "Whole panel nodal mean":
        reduction = "whole-panel nodal membrane mean"
        sample_note = "all matching mid-surface result nodes weighted equally"
    elif reduction_method == "Centre strip mean":
        reduction = f"centre-strip membrane mean over {centre_strip_fraction:.0%} panel width"
        sample_note = "only stresses in the centre strip are averaged"
    else:
        reduction = "CSR area weighted membrane mean"
        sample_note = "finite-element membrane stresses weighted by shell element area"

    return PanelStress(
        field_id=field_item.field_id,
        sigma_x1_mpa=sigma_x_nominal,
        sigma_x2_mpa=sigma_x_nominal,
        sigma_y1_mpa=sigma_y_nominal,
        sigma_y2_mpa=sigma_y_nominal,
        tau_xy_mpa=tau_xy_nominal,
        sample_count=len(selected_samples),
        reduction=reduction,
        diagnostics=(
            "FRD stress tensors projected to inferred panel axes",
            "normal stresses converted from FE tension-positive Pa to compression-positive MPa",
            sample_note,
            "CSR reference: area-weighted average membrane stress over panel finite elements",
        ),
    )


def _project_frd_stress(
    components: Sequence[str],
    values: Sequence[float],
    member_direction: Vector3D,
    transverse_direction: Vector3D,
) -> tuple[float, float, float]:
    stress_by_component = {component.upper(): float(value) for component, value in zip(components, values)}
    sxx = stress_by_component.get("SXX", 0.0)
    syy = stress_by_component.get("SYY", 0.0)
    szz = stress_by_component.get("SZZ", 0.0)
    sxy = stress_by_component.get("SXY", 0.0)
    syz = stress_by_component.get("SYZ", 0.0)
    szx = stress_by_component.get("SZX", stress_by_component.get("SXZ", 0.0))
    tensor = (
        (sxx, sxy, szx),
        (sxy, syy, syz),
        (szx, syz, szz),
    )
    sigma_x = _quadratic_tensor_product(member_direction, tensor)
    sigma_y = _quadratic_tensor_product(transverse_direction, tensor)
    tau_xy = _mixed_tensor_product(member_direction, tensor, transverse_direction)
    return sigma_x, sigma_y, tau_xy


def _quadratic_tensor_product(vector: Vector3D, tensor: tuple[Vector3D, Vector3D, Vector3D]) -> float:
    return _mixed_tensor_product(vector, tensor, vector)


def _mixed_tensor_product(
    first: Vector3D,
    tensor: tuple[Vector3D, Vector3D, Vector3D],
    second: Vector3D,
) -> float:
    return sum(first[row] * tensor[row][col] * second[col] for row in range(3) for col in range(3))


def _flat_structure_domain_for_field(field_item: PlateField) -> str:
    has_stiffener = any(member.role == "stiffener" for member in field_item.members)
    has_girder = any(member.role == "girder" for member in field_item.members)
    if has_stiffener and has_girder:
        return "Flat plate, stiffened with girder"
    if has_stiffener:
        return "Flat plate, stiffened"
    return "Flat plate, unstiffened"


def _first_member_by_role(field_item: PlateField, role: str) -> InferredMember | None:
    members = [member for member in field_item.members if member.role == role]
    if not members:
        return None
    return sorted(members, key=lambda member: member.member_id)[0]


def _plot_figure_size(fields: Sequence[PlateField]) -> tuple[float, float]:
    if not fields:
        return (8.0, 4.5)
    bbox = _bbox([corner for field_item in fields for corner in _bbox_corners(field_item.bbox)])
    x_range = max(bbox[0][1] - bbox[0][0], 1.0)
    y_range = max(bbox[1][1] - bbox[1][0], 1.0)
    ratio = max(min(x_range / y_range, 3.0), 1.2)
    return (min(max(5.0 * ratio, 7.0), 14.0), 5.0)


def _field_plot_bounds(
    field_item: PlateField,
    member_direction: Vector3D,
    transverse_direction: Vector3D,
) -> tuple[float, float, float, float]:
    corners = _bbox_corners(field_item.bbox)
    longitudinal_values = [_dot(point, member_direction) for point in corners]
    transverse_values = [_dot(point, transverse_direction) for point in corners]
    return (
        min(longitudinal_values),
        max(longitudinal_values),
        min(transverse_values),
        max(transverse_values),
    )


def _plot_member_lines(ax: Any, inference: _PatchInference) -> None:
    lower_longitudinal, upper_longitudinal = _projected_bounds(inference.base_patch, inference.member_direction)
    lower_transverse, upper_transverse = _projected_bounds(inference.base_patch, inference.transverse_direction)
    for member in inference.stiffeners:
        ax.plot(
            [lower_longitudinal, upper_longitudinal],
            [member.station, member.station],
            color="black",
            linewidth=0.7,
            alpha=0.72,
        )
    for member in inference.girders:
        ax.plot(
            [member.station, member.station],
            [lower_transverse, upper_transverse],
            color="black",
            linewidth=1.4,
            linestyle="--",
            alpha=0.82,
        )


def _element_centroid(model: FeShellModel, element: ShellElement) -> Point3D:
    points = [model.nodes[node_id] for node_id in element.corner_node_ids]
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
        sum(point[2] for point in points) / len(points),
    )


def _element_normal(points: Sequence[Point3D]) -> Vector3D:
    if len(points) < 3:
        return (0.0, 0.0, 0.0)
    for idx in range(1, len(points) - 1):
        normal = _cross(_subtract(points[idx], points[0]), _subtract(points[idx + 1], points[0]))
        if _length(normal) > 1.0e-12:
            return _normalise(normal)
    return (0.0, 0.0, 0.0)


def _element_area(points: Sequence[Point3D]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for idx in range(1, len(points) - 1):
        area += 0.5 * _length(_cross(_subtract(points[idx], points[0]), _subtract(points[idx + 1], points[0])))
    return area


def _canonical_normal(normal: Vector3D, decimals: int = 6) -> Vector3D:
    normal = _normalise(normal)
    largest = max(range(3), key=lambda index: abs(normal[index]))
    if normal[largest] < 0.0:
        normal = tuple(-value for value in normal)  # type: ignore[assignment]
    return tuple(round(value, decimals) for value in normal)  # type: ignore[return-value]


def _projected_bounds(patch: SurfacePatch, direction: Vector3D) -> tuple[float, float]:
    corners = [
        (x, y, z)
        for x in patch.bbox[0]
        for y in patch.bbox[1]
        for z in patch.bbox[2]
    ]
    values = [_dot(point, direction) for point in corners]
    return min(values), max(values)


def _extent_along_patch(patch: SurfacePatch, direction: Vector3D) -> float:
    lower, upper = _projected_bounds(patch, direction)
    return upper - lower


def _extent_from_bbox(
    bbox: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    direction: Vector3D,
) -> float:
    corners = [(x, y, z) for x in bbox[0] for y in bbox[1] for z in bbox[2]]
    values = [_dot(point, direction) for point in corners]
    return max(values) - min(values)


def _fallback_base_transverse_direction(patch: SurfacePatch, base_normal: Vector3D) -> Vector3D:
    ranges = [patch.bbox[index][1] - patch.bbox[index][0] for index in range(3)]
    normal_axis = max(range(3), key=lambda index: abs(base_normal[index]))
    candidates = [index for index in range(3) if index != normal_axis]
    axis = min(candidates, key=lambda index: ranges[index])
    vector = [0.0, 0.0, 0.0]
    vector[axis] = 1.0
    return tuple(vector)  # type: ignore[return-value]


def _fallback_member_direction(patch: SurfacePatch, transverse_direction: Vector3D) -> Vector3D:
    ranges = [patch.bbox[index][1] - patch.bbox[index][0] for index in range(3)]
    transverse_axis = max(range(3), key=lambda index: abs(transverse_direction[index]))
    candidates = [index for index in range(3) if index != transverse_axis]
    axis = max(candidates, key=lambda index: ranges[index])
    vector = [0.0, 0.0, 0.0]
    vector[axis] = 1.0
    return tuple(vector)  # type: ignore[return-value]


def _subtract(first: Point3D, second: Point3D) -> Vector3D:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def _cross(first: Vector3D, second: Vector3D) -> Vector3D:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _dot(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(first, second))


def _length(vector: Sequence[float]) -> float:
    return math.sqrt(sum(float(value) * float(value) for value in vector))


def _normalise(vector: Sequence[float]) -> Vector3D:
    length = _length(vector)
    if length <= 1.0e-15:
        return (0.0, 0.0, 0.0)
    return tuple(float(value) / length for value in vector)  # type: ignore[return-value]


def _project_to_plane(vector: Vector3D, normal: Vector3D) -> Vector3D:
    projected = tuple(vector[index] - _dot(vector, normal) * normal[index] for index in range(3))
    return _normalise(projected)


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(float(value) for value in values)
    mid = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def _mean(values: Iterable[float]) -> float:
    values = [float(value) for value in values]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _parse_keyword_attributes(line: str) -> dict[str, str | bool]:
    parts = [part.strip() for part in line.split(",")]
    attrs: dict[str, str | bool] = {}
    for item in parts[1:]:
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            attrs[key.strip().lower()] = value.strip()
        else:
            attrs[item.strip().lower()] = True
    return attrs


def _keyword_name(line: str) -> str:
    return line.split(",", 1)[0].strip().lstrip("*").lower()


def _optional_attr(attrs: dict[str, str | bool], name: str) -> str | None:
    value = attrs.get(name.lower())
    if value is None or value is True:
        return None
    return str(value)


def _csv_parts(line: str) -> list[str]:
    return [part.strip() for part in line.split(",") if part.strip()]


_FRD_NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+)(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?")


def _frd_numbers_after_marker(line: str) -> list[float]:
    stripped = line.strip()
    return [float(match.group(0)) for match in _FRD_NUMBER_PATTERN.finditer(stripped[2:])]


def _safe_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result



# ---------------------------------------------------------------------------
# Cylindrical shell extraction
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CylinderGeometry:
    """Best-fit circular-cylinder geometry inferred from the shell mesh."""

    axis_origin: Point3D
    axis_direction: Vector3D
    radius_m: float
    axial_bounds: tuple[float, float]
    radial_rms_error_m: float
    skin_element_ids: tuple[int, ...]
    skin_thickness_m: float | None = None
    confidence: float = 1.0
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class CylinderMember:
    """One longitudinal stiffener or circumferential ring member."""

    member_id: str
    role: str
    section_type: str
    web_element_ids: tuple[int, ...]
    flange_element_ids: tuple[int, ...]
    station: float
    direction: Vector3D
    web_height_m: float
    flange_width_m: float | None
    web_thickness_m: float | None = None
    flange_thickness_m: float | None = None
    confidence: float = 1.0
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class CylinderField:
    """One curved shell bay bounded by adjacent rings and longitudinal stiffeners."""

    field_id: str
    element_ids: tuple[int, ...]
    axial_bounds: tuple[float, float]
    angular_bounds_rad: tuple[float, float]
    axial_length_m: float
    circumferential_spacing_m: float
    radius_m: float
    shell_thickness_m: float | None
    attached_member_ids: tuple[str, ...]
    members: tuple[CylinderMember, ...] = ()
    confidence: float = 1.0
    diagnostics: tuple[str, ...] = ()

    @property
    def angular_span_rad(self) -> float:
        return _positive_angle(self.angular_bounds_rad[1] - self.angular_bounds_rad[0])

    # Compatibility aliases used by the existing FEA-result GUI.  The GUI was
    # originally written for PlateField and expects span/spacing/thickness names.
    # For a cylinder bay, span is axial and spacing is circumferential arc length.
    @property
    def span_m(self) -> float:
        return self.axial_length_m

    @property
    def spacing_m(self) -> float:
        return self.circumferential_spacing_m

    @property
    def shell_section_thickness_m(self) -> float | None:
        return self.shell_thickness_m

    @property
    def transverse_bounds(self) -> tuple[float, float]:
        return self.angular_bounds_rad

    @property
    def base_patch_id(self) -> str:
        return "cylinder_skin"


@dataclass(frozen=True)
class CylinderStress:
    """Nominal local cylinder stresses reduced from an FRD result."""

    field_id: str
    axial_stress_mpa: float
    hoop_stress_mpa: float
    torsional_shear_mpa: float
    transverse_shear_mpa: float
    sample_count: int
    reduction: str
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeaCylinderPanel:
    """One selectable cylindrical shell bay."""

    field_id: str
    field: CylinderField
    stress: CylinderStress | None
    anystructure_input: dict[str, Any]
    buckling_result: dict[str, Any] | None = None
    usage_factor: float | None = None


@dataclass(frozen=True)
class FeaCylinderSession:
    """Complete cylindrical FE-result interpretation."""

    inp_path: str
    frd_path: str | None
    model: FeShellModel
    geometry: CylinderGeometry
    fields: tuple[CylinderField, ...]
    panels: tuple[FeaCylinderPanel, ...]
    frd_summary: dict[str, Any] | None = None
    diagnostics: tuple[str, ...] = ()
    active_load_case: int | None = None

    @property
    def load_cases(self) -> tuple[int, ...]:
        if self.frd_summary and "load_cases" in self.frd_summary:
            return tuple(self.frd_summary["load_cases"])
        return ()

    @property
    def load_case_names(self) -> dict[int, str]:
        if self.frd_summary and "load_case_names" in self.frd_summary:
            return dict(self.frd_summary["load_case_names"])
        return {}

    @property
    def field_count(self) -> int:
        return len(self.fields)

    @property
    def panel_count(self) -> int:
        return len(self.panels)

    def panel(self, field_id: str) -> FeaCylinderPanel:
        for panel in self.panels:
            if panel.field_id == field_id:
                return panel
        raise KeyError(field_id)

    def usage_factors(self) -> dict[str, float]:
        return {
            panel.field_id: panel.usage_factor
            for panel in self.panels
            if panel.usage_factor is not None
        }

    def summary(self) -> dict[str, Any]:
        return {
            "geometry_type": "cylinder",
            "inp_path": self.inp_path,
            "frd_path": self.frd_path,
            "node_count": len(self.model.nodes),
            "element_count": len(self.model.shell_elements),
            "field_count": len(self.fields),
            "geometry": {
                "axis_origin": list(self.geometry.axis_origin),
                "axis_direction": list(self.geometry.axis_direction),
                "radius_m": self.geometry.radius_m,
                "axial_bounds": list(self.geometry.axial_bounds),
                "radial_rms_error_m": self.geometry.radial_rms_error_m,
                "skin_element_count": len(self.geometry.skin_element_ids),
                "skin_thickness_m": self.geometry.skin_thickness_m,
                "confidence": self.geometry.confidence,
                "diagnostics": list(self.geometry.diagnostics),
            },
            "fields": summarize_cylinder_fields(self.fields),
            "panels": [
                {
                    "field_id": panel.field_id,
                    "usage_factor": panel.usage_factor,
                    "anystructure_input": panel.anystructure_input,
                    "stress": None if panel.stress is None else {
                        "axial_stress_mpa": panel.stress.axial_stress_mpa,
                        "hoop_stress_mpa": panel.stress.hoop_stress_mpa,
                        "torsional_shear_mpa": panel.stress.torsional_shear_mpa,
                        "transverse_shear_mpa": panel.stress.transverse_shear_mpa,
                        "sample_count": panel.stress.sample_count,
                        "reduction": panel.stress.reduction,
                    },
                    "buckling_result": panel.buckling_result,
                }
                for panel in self.panels
            ],
            "frd": self.frd_summary,
            "diagnostics": list(self.diagnostics),
        }


def is_cylindrical_shell_model(
    model: FeShellModel,
    *,
    minimum_skin_fraction: float = 0.35,
    maximum_relative_rms_error: float = 0.03,
    minimum_angular_coverage_rad: float = math.pi,
) -> bool:
    """Return whether the shell mesh contains a credible circular cylindrical skin."""

    try:
        geometry = detect_cylinder_geometry(model)
    except (ValueError, ArithmeticError):
        return False
    relative_error = geometry.radial_rms_error_m / max(geometry.radius_m, 1.0e-12)
    skin_fraction = len(geometry.skin_element_ids) / max(len(model.shell_elements), 1)
    if relative_error > maximum_relative_rms_error or skin_fraction < minimum_skin_fraction:
        return False
    # A flat or shallow model can fit a large-radius circle with a tiny
    # residual (a degenerate fit through few distinct radial positions), but
    # its "skin" only subtends a narrow arc. A credible cylinder wraps around
    # its axis, so require the skin to cover a substantial angular range.
    coverage = _cylinder_skin_angular_coverage_rad(model, geometry)
    return coverage >= minimum_angular_coverage_rad


def _element_angular_span(
    model: FeShellModel,
    element: ShellElement,
    origin: Point3D,
    axis: Vector3D,
) -> float:
    """Return the largest angle subtended about the axis by the element corners."""

    radial_units = []
    for node_id in element.corner_node_ids:
        point = model.nodes.get(node_id)
        if point is None:
            continue
        radial = _radial_vector(point, origin, axis)
        length = _length(radial)
        if length <= 1.0e-12:
            continue
        radial_units.append(tuple(value / length for value in radial))
    if len(radial_units) < 2:
        return 0.0
    smallest_dot = min(
        _dot(radial_units[first], radial_units[second])
        for first in range(len(radial_units) - 1)
        for second in range(first + 1, len(radial_units))
    )
    return math.acos(max(-1.0, min(1.0, smallest_dot)))


def _cylinder_skin_angular_coverage_rad(
    model: FeShellModel,
    geometry: CylinderGeometry,
) -> float:
    """Return the angular range (rad) the skin subtends about the cylinder axis.

    Coverage is measured as ``2*pi`` minus the largest empty angular gap
    between consecutive skin-element centroids.  This is independent of the
    circumferential mesh resolution: a full cylinder wraps all the way around
    (only the one-element gap between neighbours remains), whereas a flat or
    shallow patch clusters in a narrow arc and leaves one large gap.  A
    bin-count metric instead under-reports coverage for coarse meshes, because
    a full cylinder meshed with fewer circumferential elements than bins can
    never fill every bin.
    """

    axis = _normalise(geometry.axis_direction)
    reference = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
    plane_u = _normalise(_cross(axis, reference))
    if _length(plane_u) <= 1.0e-12:
        return 0.0
    plane_v = _normalise(_cross(axis, plane_u))
    angles: list[float] = []
    for element_id in geometry.skin_element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        centroid = _element_centroid(model, element)
        radial = _radial_vector(centroid, geometry.axis_origin, axis)
        if _length(radial) <= 1.0e-12:
            continue
        angles.append(math.atan2(_dot(radial, plane_v), _dot(radial, plane_u)))
    if len(angles) < 2:
        return 0.0
    angles.sort()
    largest_gap = max(
        (second - first)
        for first, second in zip(angles, angles[1:])
    )
    # Close the circle: the wrap-around gap from the last angle back to the first.
    largest_gap = max(largest_gap, angles[0] + 2.0 * math.pi - angles[-1])
    return max(0.0, 2.0 * math.pi - largest_gap)


def detect_cylinder_geometry(
    model: FeShellModel,
    *,
    radial_tolerance_fraction: float = 0.006,
    normal_alignment: float = 0.65,
) -> CylinderGeometry:
    """Fit a circular cylinder and identify the true shell skin.

    The axis is estimated from the full point cloud, but the final radius and
    skin set are derived from radially oriented shell elements close to the
    outermost dominant cylindrical surface.  This prevents inward ring webs,
    longitudinal webs and flanges from inflating the radial tolerance and being
    mistaken for shell plating.
    """

    if len(model.nodes) < 6 or not model.shell_elements:
        raise ValueError("not enough shell geometry to fit a cylinder")

    import numpy as np

    points = np.asarray(list(model.nodes.values()), dtype=float)
    centre = points.mean(axis=0)
    covariance = np.cov((points - centre).T)
    _, eigenvectors = np.linalg.eigh(covariance)

    best: tuple[float, Vector3D, Point3D, float, float] | None = None
    for index in range(3):
        axis = _canonical_axis(tuple(float(value) for value in eigenvectors[:, index]))
        origin, radius, rms = _fit_circle_about_axis(points, axis)
        axial_extent = _point_cloud_extent(points, axis)
        score = rms / max(radius, 1.0e-12)
        if radius <= 1.0e-10 or axial_extent <= 1.0e-10:
            continue
        if best is None or score < best[0]:
            best = (score, axis, origin, radius, rms)

    if best is None:
        raise ValueError("could not determine a cylindrical axis")

    _, axis, origin, _initial_radius, _initial_rms = best

    radial_candidates: list[tuple[int, float, float]] = []
    for element in model.shell_elements.values():
        points_element = [model.nodes[node_id] for node_id in element.corner_node_ids]
        centroid = _element_centroid(model, element)
        radial_vector = _radial_vector(centroid, origin, axis)
        radial_distance = _median(
            _length(_radial_vector(point, origin, axis))
            for point in points_element
        ) or _length(radial_vector)
        if radial_distance <= 1.0e-12:
            continue
        normal = _element_normal(points_element)
        alignment = abs(_dot(normal, _normalise(radial_vector)))
        if alignment >= normal_alignment:
            radial_candidates.append((element.element_id, radial_distance, alignment))

    if not radial_candidates:
        raise ValueError("no radially oriented shell elements found")

    candidate_distances = sorted(item[1] for item in radial_candidates)
    upper_index = min(
        len(candidate_distances) - 1,
        max(0, int(math.floor(0.90 * (len(candidate_distances) - 1)))),
    )
    outer_reference = candidate_distances[upper_index]

    coarse_tolerance = max(
        outer_reference * max(radial_tolerance_fraction * 2.0, 0.01),
        1.0e-7,
    )
    coarse_ids = [
        element_id
        for element_id, distance, _alignment in radial_candidates
        if abs(distance - outer_reference) <= coarse_tolerance
    ]
    if not coarse_ids:
        raise ValueError("could not isolate the cylindrical shell surface")

    coarse_node_ids = {
        node_id
        for element_id in coarse_ids
        for node_id in model.shell_elements[element_id].corner_node_ids
    }
    coarse_node_distances = [
        _length(_radial_vector(model.nodes[node_id], origin, axis))
        for node_id in coarse_node_ids
    ]
    radius = _median(coarse_node_distances) or outer_reference

    # Coarse or faceted meshes place skin nodes between circumferential
    # vertices genuinely inside the true radius (facet sagitta), so widen the
    # base tolerance with the sagitta implied by the element angular pitch
    # instead of using one fixed fraction for every mesh density.
    element_angular_spans = sorted(
        span
        for span in (
            _element_angular_span(model, model.shell_elements[element_id], origin, axis)
            for element_id in coarse_ids
        )
        if span > 0.0
    )
    # Use a high percentile so irregular meshes report the coarse facet pitch
    # rather than their smallest elements.
    angular_pitch = (
        element_angular_spans[int(0.90 * (len(element_angular_spans) - 1))]
        if element_angular_spans
        else 0.0
    )
    facet_sagitta = radius * (1.0 - math.cos(min(angular_pitch, math.pi) / 2.0))
    radial_tolerance = max(radius * radial_tolerance_fraction, 2.0 * facet_sagitta, 1.0e-7)

    # Skin deviations form a continuum (mesh facets sweep from the vertices
    # to the deepest facet middle) while internal flanges sit a web height
    # inside, so grow the band while candidate deviations stay continuous and
    # stop at the first clear radial gap.
    gap_threshold = max(0.5 * radial_tolerance, 0.002 * radius)
    maximum_band = 0.04 * radius
    for deviation in sorted(abs(distance - radius) for _eid, distance, _al in radial_candidates):
        if deviation <= radial_tolerance:
            continue
        if deviation - radial_tolerance <= gap_threshold and deviation <= maximum_band:
            radial_tolerance = deviation
        else:
            break
    skin_ids: list[int] = []
    axial_values: list[float] = []
    skin_node_ids: set[int] = set()

    for element_id, radial_distance, _alignment in radial_candidates:
        if abs(radial_distance - radius) > radial_tolerance:
            continue
        element = model.shell_elements[element_id]
        skin_ids.append(element_id)
        skin_node_ids.update(element.corner_node_ids)
        axial_values.extend(
            _axial_coordinate(model.nodes[node_id], origin, axis)
            for node_id in element.corner_node_ids
        )

    if not skin_ids:
        raise ValueError("no cylindrical skin elements satisfied the final fit tolerance")

    skin_radial_distances = [
        _length(_radial_vector(model.nodes[node_id], origin, axis))
        for node_id in skin_node_ids
    ]
    radius = _median(skin_radial_distances) or radius
    rms = math.sqrt(_mean((distance - radius) ** 2 for distance in skin_radial_distances))

    skin_thickness = _shell_section_thickness_for_elements(model, skin_ids)
    relative_rms = rms / max(radius, 1.0e-12)
    confidence = max(0.0, min(1.0, 1.0 - relative_rms / 0.01))
    return CylinderGeometry(
        axis_origin=origin,
        axis_direction=axis,
        radius_m=radius,
        axial_bounds=(min(axial_values), max(axial_values)),
        radial_rms_error_m=rms,
        skin_element_ids=tuple(sorted(skin_ids)),
        skin_thickness_m=skin_thickness,
        confidence=confidence,
        diagnostics=(
            "axis inferred from shell-node covariance",
            "skin isolated from the outer dominant radially oriented shell surface",
            "inward webs and flanges excluded before the final radius fit",
        ),
    )


def infer_cylinder_fields(
    model: FeShellModel,
    geometry: CylinderGeometry | None = None,
    members: Sequence[CylinderMember] | None = None,
) -> list[CylinderField]:
    """Infer cylindrical bays, longitudinal stiffeners, and ring frames."""

    geometry = detect_cylinder_geometry(model) if geometry is None else geometry
    members = tuple(_infer_cylinder_members(model, geometry) if members is None else members)
    longitudinals = sorted(
        (member for member in members if member.role == "longitudinal_stiffener"),
        key=lambda member: member.station,
    )
    rings = sorted(
        (member for member in members if member.role in {"ring_stiffener", "ring_frame"}),
        key=lambda member: member.station,
    )

    if longitudinals:
        angular_intervals = [
            (longitudinals[index].station, longitudinals[(index + 1) % len(longitudinals)].station)
            for index in range(len(longitudinals))
        ]
    else:
        angular_intervals = [(-math.pi, math.pi)]

    axial_stations = [geometry.axial_bounds[0]]
    axial_stations.extend(
        member.station
        for member in rings
        if geometry.axial_bounds[0] + 1.0e-8 < member.station < geometry.axial_bounds[1] - 1.0e-8
    )
    axial_stations.append(geometry.axial_bounds[1])
    axial_stations = _unique_sorted(axial_stations, tolerance=1.0e-7)

    shell_centres = {
        element_id: _element_centroid(model, model.shell_elements[element_id])
        for element_id in geometry.skin_element_ids
    }
    members_by_id = {member.member_id: member for member in members}
    fields: list[CylinderField] = []
    field_index = 1

    for axial_index, (lower_axial, upper_axial) in enumerate(zip(axial_stations[:-1], axial_stations[1:])):
        lower_ring = _member_at_station(rings, lower_axial)
        upper_ring = _member_at_station(rings, upper_axial)
        for angular_index, (start_angle, end_angle) in enumerate(angular_intervals):
            attached: list[str] = []
            if longitudinals:
                attached.extend(
                    (
                        longitudinals[angular_index].member_id,
                        longitudinals[(angular_index + 1) % len(longitudinals)].member_id,
                    )
                )
            if lower_ring is not None:
                attached.append(lower_ring.member_id)
            if upper_ring is not None:
                attached.append(upper_ring.member_id)

            selected_ids: list[int] = []
            for element_id, centroid in shell_centres.items():
                axial = _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
                if not (lower_axial - 1.0e-8 <= axial <= upper_axial + 1.0e-8):
                    continue
                angle = _cylinder_angle(centroid, geometry)
                if _angle_in_interval(angle, start_angle, end_angle):
                    selected_ids.append(element_id)
            if not selected_ids:
                continue

            angle_span = _positive_angle(end_angle - start_angle)
            if not longitudinals:
                angle_span = 2.0 * math.pi
            field_members = tuple(
                members_by_id[member_id]
                for member_id in dict.fromkeys(attached)
                if member_id in members_by_id
            )
            fields.append(
                CylinderField(
                    field_id=f"cyl_field_{field_index:03d}",
                    element_ids=tuple(sorted(selected_ids)),
                    axial_bounds=(lower_axial, upper_axial),
                    angular_bounds_rad=(start_angle, end_angle),
                    axial_length_m=upper_axial - lower_axial,
                    circumferential_spacing_m=geometry.radius_m * angle_span,
                    radius_m=geometry.radius_m,
                    shell_thickness_m=geometry.skin_thickness_m,
                    attached_member_ids=tuple(dict.fromkeys(attached)),
                    members=field_members,
                    confidence=geometry.confidence,
                    diagnostics=(
                        "bounded axially by adjacent ring stations or shell ends",
                        "bounded circumferentially by adjacent longitudinal stiffener angles",
                    ),
                )
            )
            field_index += 1
    return fields


def summarize_cylinder_fields(fields: Sequence[CylinderField]) -> list[dict[str, Any]]:
    """Flatten inferred cylindrical fields for JSON inspection."""

    return [
        {
            "field_id": field_item.field_id,
            "element_count": len(field_item.element_ids),
            "axial_bounds_m": list(field_item.axial_bounds),
            "angular_bounds_rad": list(field_item.angular_bounds_rad),
            "angular_span_deg": math.degrees(field_item.angular_span_rad),
            "axial_length_m": field_item.axial_length_m,
            "circumferential_spacing_m": field_item.circumferential_spacing_m,
            "radius_m": field_item.radius_m,
            "shell_thickness_m": field_item.shell_thickness_m,
            "attached_member_ids": list(field_item.attached_member_ids),
            "confidence": field_item.confidence,
            "diagnostics": list(field_item.diagnostics),
            "members": [
                {
                    "member_id": member.member_id,
                    "role": member.role,
                    "section_type": member.section_type,
                    "station": member.station,
                    "web_height_m": member.web_height_m,
                    "flange_width_m": member.flange_width_m,
                    "web_thickness_m": member.web_thickness_m,
                    "flange_thickness_m": member.flange_thickness_m,
                    "web_element_count": len(member.web_element_ids),
                    "flange_element_count": len(member.flange_element_ids),
                    "confidence": member.confidence,
                    "diagnostics": list(member.diagnostics),
                }
                for member in field_item.members
            ],
        }
        for field_item in fields
    ]


def reduce_cylinder_stresses(
    model: FeShellModel,
    geometry: CylinderGeometry,
    fields: Sequence[CylinderField],
    frd_stress: FrdStressResult,
    *,
    stress_reduction_method: str | None = None,
    centre_strip_fraction: float = 0.25,
) -> list[CylinderStress]:
    """Project FRD stresses into local axial/circumferential cylinder axes.

    Cylinder stresses retain the CalculiX tension-positive sign convention,
    which matches the ANYstructure cylinder API where compression is negative.
    """

    reduction_method = normalize_stress_reduction_method(stress_reduction_method)
    result: list[CylinderStress] = []
    for field_item in fields:
        if reduction_method == "CSR area weighted mean":
            samples = _cylinder_element_stress_samples(model, geometry, field_item, frd_stress)
        else:
            samples = _cylinder_nodal_stress_samples(model, geometry, field_item, frd_stress)

        selected_samples = list(samples)
        if reduction_method == "Centre strip mean" and selected_samples:
            lower_axial, upper_axial = field_item.axial_bounds
            width = max(upper_axial - lower_axial, 1.0e-9)
            centre = 0.5 * (lower_axial + upper_axial)
            half_strip = max(width * centre_strip_fraction * 0.5, 1.0e-9)
            selected_samples = [
                sample for sample in samples
                if abs(sample[0] - centre) <= half_strip
            ]
            if not selected_samples:
                ordered = sorted(samples, key=lambda sample: abs(sample[0] - centre))
                selected_samples = ordered[: max(1, int(math.ceil(len(ordered) * centre_strip_fraction)))]

        if reduction_method == "Whole panel nodal mean":
            selected_samples = [
                (sample[0], sample[1], sample[2], sample[3], 1.0)
                for sample in selected_samples
            ]

        if selected_samples:
            if reduction_method == "Whole panel nodal mean":
                reduction = "whole-panel nodal membrane mean in axial/circumferential axes"
            elif reduction_method == "Centre strip mean":
                reduction = f"centre-strip membrane mean over {centre_strip_fraction:.0%} axial panel length"
            else:
                reduction = "CSR area weighted membrane mean in axial/circumferential axes"
            result.append(
                CylinderStress(
                    field_id=field_item.field_id,
                    axial_stress_mpa=_weighted_mean((sample[1], sample[4]) for sample in selected_samples),
                    hoop_stress_mpa=_weighted_mean((sample[2], sample[4]) for sample in selected_samples),
                    torsional_shear_mpa=_weighted_mean((sample[3], sample[4]) for sample in selected_samples),
                    transverse_shear_mpa=0.0,
                    sample_count=len(selected_samples),
                    reduction=reduction,
                    diagnostics=(
                        "CalculiX tension-positive sign retained; cylinder compression is negative",
                        "S_axial, S_hoop and tau_axial-hoop projected at every result node",
                        "CSR reference: area-weighted average membrane stress over panel finite elements",
                    ),
                )
            )
        else:
            result.append(
                CylinderStress(
                    field_id=field_item.field_id,
                    axial_stress_mpa=0.0,
                    hoop_stress_mpa=0.0,
                    torsional_shear_mpa=0.0,
                    transverse_shear_mpa=0.0,
                    sample_count=0,
                    reduction="no FRD stress samples",
                    diagnostics=("no result nodes matched the cylinder field elements",),
                )
            )
    return result


def _cylinder_nodal_stress_samples(
    model: FeShellModel,
    geometry: CylinderGeometry,
    field_item: CylinderField,
    frd_stress: FrdStressResult,
) -> list[tuple[float, float, float, float, float]]:
    samples: list[tuple[float, float, float, float, float]] = []
    seen: set[int] = set()
    for element_id in field_item.element_ids:
        for node_id in frd_stress.element_nodes.get(element_id, ()):
            if node_id in seen or node_id not in frd_stress.nodal_stress:
                continue
            point = frd_stress.nodes.get(node_id)
            if point is None:
                continue
            seen.add(node_id)
            axial, hoop, shear = _project_cylinder_point_stress(point, geometry, frd_stress, node_id)
            samples.append((_dot(_subtract(point, geometry.axis_origin), geometry.axis_direction), axial, hoop, shear, 1.0))
    return samples


def _cylinder_element_stress_samples(
    model: FeShellModel,
    geometry: CylinderGeometry,
    field_item: CylinderField,
    frd_stress: FrdStressResult,
) -> list[tuple[float, float, float, float, float]]:
    samples: list[tuple[float, float, float, float, float]] = []
    for element_id in field_item.element_ids:
        element = model.shell_elements.get(element_id)
        if element is None:
            continue
        corner_points = [model.nodes[node_id] for node_id in element.corner_node_ids if node_id in model.nodes]
        if len(corner_points) < 3:
            continue
        projected_values = []
        for node_id in frd_stress.element_nodes.get(element_id, element.corner_node_ids):
            if node_id not in frd_stress.nodal_stress:
                continue
            point = frd_stress.nodes.get(node_id)
            if point is None:
                continue
            projected_values.append(_project_cylinder_point_stress(point, geometry, frd_stress, node_id))
        if not projected_values:
            continue
        centroid = _mean_point(corner_points)
        area = _element_area(corner_points)
        samples.append(
            (
                _dot(_subtract(centroid, geometry.axis_origin), geometry.axis_direction),
                _mean(value[0] for value in projected_values),
                _mean(value[1] for value in projected_values),
                _mean(value[2] for value in projected_values),
                max(area, 1.0e-12),
            )
        )
    return samples


def _project_cylinder_point_stress(
    point: Point3D,
    geometry: CylinderGeometry,
    frd_stress: FrdStressResult,
    node_id: int,
) -> tuple[float, float, float]:
    radial = _normalise(_radial_vector(point, geometry.axis_origin, geometry.axis_direction))
    circumferential = _normalise(_cross(geometry.axis_direction, radial))
    axial, hoop, shear = _project_frd_stress(
        frd_stress.components,
        frd_stress.nodal_stress[node_id],
        geometry.axis_direction,
        circumferential,
    )
    return axial / 1.0e6, hoop / 1.0e6, shear / 1.0e6


def anystructure_input_for_cylinder_field(
    field_item: CylinderField,
    stress: CylinderStress | None = None,
    *,
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
) -> dict[str, Any]:
    """Return CylStru-compatible values inferred for one cylindrical bay."""

    longitudinal = _first_cylinder_member(field_item, "longitudinal_stiffener")
    panel_stress = stress or CylinderStress(
        field_id=field_item.field_id,
        axial_stress_mpa=0.0,
        hoop_stress_mpa=0.0,
        torsional_shear_mpa=0.0,
        transverse_shear_mpa=0.0,
        sample_count=0,
        reduction="default zero stress",
    )
    domain = _cylinder_domain_for_field(field_item)
    calculation_longitudinal, calculation_ring, calculation_frame = _cylinder_calculation_members(
        field_item,
        domain,
    )
    return {
        "field_id": field_item.field_id,
        "calculation_domain": domain,
        "shell": {
            "radius_mm": field_item.radius_m * 1000.0,
            "thickness_mm": (field_item.shell_thickness_m or 0.0) * 1000.0,
            "total_length_mm": field_item.axial_length_m * 1000.0,
            "distance_between_rings_mm": field_item.axial_length_m * 1000.0,
            "panel_spacing_mm": field_item.circumferential_spacing_m * 1000.0,
        },
        "longitudinal_stiffener": _cylinder_member_input(calculation_longitudinal or longitudinal),
        "ring_stiffener": _cylinder_member_input(calculation_ring),
        "ring_frame": _cylinder_member_input(calculation_frame),
        "material": {
            "yield_mpa": material_yield_mpa,
            "elastic_modulus_mpa": elastic_modulus_mpa,
            "material_factor": material_factor,
            "poisson": poisson,
        },
        "stresses": {
            "sasd_mpa": panel_stress.axial_stress_mpa,
            "smsd_mpa": 0.0,
            "tTsd_mpa": panel_stress.torsional_shear_mpa,
            "tQsd_mpa": panel_stress.transverse_shear_mpa,
            "psd_mpa": pressure_mpa,
            "shsd_mpa": panel_stress.hoop_stress_mpa,
            "sample_count": panel_stress.sample_count,
            "reduction": panel_stress.reduction,
        },
    }


_FLAT_PANEL_BUCKLING_METHODS = {"SemiAnalytical S3/U3", "ML-Numeric (PULS based)"}


def _cylinder_flat_panel_method_warning(calculation_method: str) -> str:
    return (
        "WARNING: "
        f"{calculation_method} is calibrated for flat plate/stiffened-panel checks. "
        "For cylindrical FE bays ANYstructure maps axial length, circumferential spacing, "
        "axial/hoop stresses and local stiffener data to an equivalent flat panel. "
        "Use this as an engineering approximation; cylindrical DNV rule checks may have "
        "separate geometry and validity limits."
    )


def _cylinder_member_to_flat_member(member: CylinderMember, role: str) -> InferredMember:
    return InferredMember(
        member_id=member.member_id,
        role=role,
        section_type=member.section_type,
        web_patch_id=member.member_id,
        flange_patch_id=member.member_id if member.flange_element_ids else None,
        direction=member.direction,
        station=member.station,
        web_height_m=member.web_height_m,
        flange_width_m=member.flange_width_m,
        web_thickness_m=member.web_thickness_m,
        flange_thickness_m=member.flange_thickness_m,
        thickness_source="cylinder shell section metadata",
        confidence=member.confidence,
        diagnostics=member.diagnostics + ("mapped from cylindrical member for equivalent flat-panel buckling",),
    )


def _equivalent_flat_field_for_cylinder(field_item: CylinderField) -> PlateField:
    flat_members: list[InferredMember] = []
    for member in field_item.members:
        if member.role == "longitudinal_stiffener":
            flat_members.append(_cylinder_member_to_flat_member(member, "stiffener"))
        elif member.role in {"ring_stiffener", "ring_frame"}:
            flat_members.append(_cylinder_member_to_flat_member(member, "girder"))

    return PlateField(
        field_id=field_item.field_id,
        base_patch_id="equivalent_cylinder_flat_panel",
        element_ids=field_item.element_ids,
        bbox=((0.0, field_item.axial_length_m), (0.0, field_item.circumferential_spacing_m), (0.0, 0.0)),
        span_m=field_item.axial_length_m,
        spacing_m=field_item.circumferential_spacing_m,
        transverse_bounds=(0.0, field_item.circumferential_spacing_m),
        attached_member_ids=field_item.attached_member_ids,
        members=tuple(flat_members),
        shell_section_thickness_m=field_item.shell_thickness_m,
        confidence=field_item.confidence,
        diagnostics=field_item.diagnostics + (
            "equivalent flat-panel input: span=axial length, spacing=circumferential arc length",
        ),
    )


def _equivalent_panel_stress_for_cylinder(stress: CylinderStress) -> PanelStress:
    return PanelStress(
        field_id=stress.field_id,
        sigma_x1_mpa=-stress.axial_stress_mpa,
        sigma_x2_mpa=-stress.axial_stress_mpa,
        sigma_y1_mpa=-stress.hoop_stress_mpa,
        sigma_y2_mpa=-stress.hoop_stress_mpa,
        tau_xy_mpa=stress.torsional_shear_mpa,
        sample_count=stress.sample_count,
        reduction=(
            "equivalent flat-panel stress: axial compression -> sigma_x, "
            "hoop compression -> sigma_y, torsion -> tau_xy"
        ),
        source_units="MPa",
        diagnostics=stress.diagnostics + (
            "converted from cylinder tension-positive convention to flat compression-positive convention",
        ),
    )


def calculate_equivalent_flat_buckling_for_cylinder(
    fields: Sequence[CylinderField],
    stresses: Sequence[CylinderStress],
    *,
    calculation_method: str,
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    ml_algo: Any = None,
) -> list[dict[str, Any]]:
    """Run flat-panel methods on cylindrical bays using a documented equivalent mapping."""

    equivalent_fields = tuple(_equivalent_flat_field_for_cylinder(field_item) for field_item in fields)
    equivalent_stresses = tuple(_equivalent_panel_stress_for_cylinder(stress) for stress in stresses)
    warning = _cylinder_flat_panel_method_warning(calculation_method)
    results = calculate_field_buckling(
        equivalent_fields,
        equivalent_stresses,
        calculation_method=calculation_method,
        buckling_acceptance=buckling_acceptance,
        pressure_mpa=pressure_mpa,
        material_yield_mpa=material_yield_mpa,
        elastic_modulus_mpa=elastic_modulus_mpa,
        material_factor=material_factor,
        poisson=poisson,
        ml_algo=ml_algo,
    )
    for result in results:
        result["domain"] = "Equivalent flat panel from cylindrical shell"
        result["cylinder_method_warning"] = warning
        result["warnings"] = tuple(dict.fromkeys(tuple(result.get("warnings", ())) + (warning,)))
        result["calculation_method"] = calculation_method
        result["buckling_acceptance"] = buckling_acceptance
    return results


def calculate_cylinder_buckling(
    fields: Sequence[CylinderField],
    stresses: Sequence[CylinderStress],
    *,
    calculation_method: str = "DNV-RP-C201 - prescriptive",
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    imperfection_factor: float = 0.005,
    effective_buckling_length_factor: float = 1.0,
    ml_algo: Any = None,
) -> list[dict[str, Any]]:
    """Run the existing ANYstructure CylStru check for each inferred bay."""

    if calculation_method in _FLAT_PANEL_BUCKLING_METHODS:
        return calculate_equivalent_flat_buckling_for_cylinder(
            fields,
            stresses,
            calculation_method=calculation_method,
            buckling_acceptance=buckling_acceptance,
            pressure_mpa=pressure_mpa,
            material_yield_mpa=material_yield_mpa,
            elastic_modulus_mpa=elastic_modulus_mpa,
            material_factor=material_factor,
            poisson=poisson,
            ml_algo=ml_algo,
        )

    from anystruct.api import CylStru

    stress_by_field = {stress.field_id: stress for stress in stresses}
    results: list[dict[str, Any]] = []
    for field_item in fields:
        stress = stress_by_field.get(field_item.field_id)
        input_data = anystructure_input_for_cylinder_field(
            field_item,
            stress,
            pressure_mpa=pressure_mpa,
            material_yield_mpa=material_yield_mpa,
            elastic_modulus_mpa=elastic_modulus_mpa,
            material_factor=material_factor,
            poisson=poisson,
        )
        try:
            cylinder = CylStru(calculation_domain=input_data["calculation_domain"])
            cylinder.set_material(
                mat_yield=material_yield_mpa,
                emodule=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
            )
            cylinder.set_imperfection(delta_0=imperfection_factor)
            cylinder.set_shell_geometry(
                radius=input_data["shell"]["radius_mm"],
                thickness=input_data["shell"]["thickness_mm"],
                tot_length_of_shell=input_data["shell"]["total_length_mm"],
                distance_between_rings=input_data["shell"]["distance_between_rings_mm"],
            )
            cylinder.set_shell_buckling_parmeters(
                eff_buckling_length_factor=effective_buckling_length_factor
            )
            cylinder.set_length_between_girder(input_data["shell"]["distance_between_rings_mm"])
            cylinder.set_panel_spacing(input_data["shell"]["panel_spacing_mm"])

            calculation_longitudinal, calculation_ring, calculation_frame = _cylinder_calculation_members(
                field_item,
                input_data["calculation_domain"],
            )
            if calculation_longitudinal is not None:
                _set_cylinder_member(
                    cylinder.set_longitudinal_stiffener,
                    calculation_longitudinal,
                    field_item.circumferential_spacing_m,
                )
            if calculation_ring is not None:
                _set_cylinder_member(cylinder.set_ring_stiffener, calculation_ring, field_item.axial_length_m)
            if calculation_frame is not None:
                _set_cylinder_member(cylinder.set_ring_girder, calculation_frame, field_item.axial_length_m)

            cylinder.set_stresses(
                sasd=0.0 if stress is None else stress.axial_stress_mpa,
                smsd=0.0,
                tTsd=0.0 if stress is None else stress.torsional_shear_mpa,
                tQsd=0.0 if stress is None else stress.transverse_shear_mpa,
                psd=pressure_mpa,
                shsd=0.0 if stress is None else stress.hoop_stress_mpa,
            )
            buckling_result = cylinder.get_buckling_results()
            results.append(
                {
                    "field_id": field_item.field_id,
                    "domain": input_data["calculation_domain"],
                    "available": True,
                    "calculation_method": calculation_method,
                    "buckling_acceptance": buckling_acceptance,
                    "input": input_data,
                    "result": buckling_result,
                }
            )
        except Exception as err:
            results.append(
                {
                    "field_id": field_item.field_id,
                    "domain": input_data["calculation_domain"],
                    "available": False,
                    "calculation_method": calculation_method,
                    "buckling_acceptance": buckling_acceptance,
                    "input": input_data,
                    "error": str(err),
                }
            )
    return results


def _runtime_fea_payload(runtime_result: Any) -> dict[str, Any]:
    if isinstance(runtime_result, dict):
        if str(runtime_result.get("format", "")) == "anystructure-runtime-fe-results-v1":
            return runtime_result
        nested = runtime_result.get("fea_result_import")
        if isinstance(nested, dict):
            return nested
        visualization = runtime_result.get("visualization")
        if isinstance(visualization, dict) and isinstance(visualization.get("fea_result_import"), dict):
            return visualization["fea_result_import"]
    visualization = getattr(runtime_result, "visualization", None)
    if isinstance(visualization, dict) and isinstance(visualization.get("fea_result_import"), dict):
        return visualization["fea_result_import"]
    raise ValueError(
        "runtime_result does not contain visualization['fea_result_import']; "
        "run the production runtime FEM solver and pass its result object"
    )


def fe_shell_model_from_runtime_result(runtime_result: Any) -> FeShellModel:
    """Build the normal FE-results shell model from a runtime FEM result payload."""

    payload = _runtime_fea_payload(runtime_result)
    nodes: dict[int, Point3D] = {}
    for item in payload.get("nodes", ()) or ():
        if isinstance(item, dict):
            node_id = int(item.get("id"))
            coords = item.get("coords", (0.0, 0.0, 0.0))
        else:
            node_id = int(item[0])
            coords = item[1]
        nodes[node_id] = (float(coords[0]), float(coords[1]), float(coords[2]))

    shell_elements: dict[int, ShellElement] = {}
    elsets: dict[str, list[int]] = defaultdict(list)
    for item in payload.get("shells", ()) or ():
        element_id = int(item.get("id", item.get("element_id", 0)))
        if element_id <= 0:
            continue
        node_ids = tuple(int(node_id) for node_id in item.get("node_ids", ()))
        elset = item.get("elset")
        shell_elements[element_id] = ShellElement(
            element_id=element_id,
            node_ids=node_ids,
            element_type=str(item.get("type", "S4") or "S4"),
            elset=None if elset is None else str(elset),
        )
        if elset:
            elsets[str(elset)].append(element_id)

    for name, values in (payload.get("elsets", {}) or {}).items():
        elsets[str(name)].extend(int(value) for value in values)

    shell_sections: list[ShellSection] = []
    for section in payload.get("shell_sections", ()) or ():
        shell_sections.append(
            ShellSection(
                elset=None if section.get("elset") is None else str(section.get("elset")),
                material=None if section.get("material") is None else str(section.get("material")),
                thickness_m=_safe_float(section.get("thickness_m")),
                offset=None if section.get("offset") is None else str(section.get("offset")),
            )
        )
    if not shell_sections and shell_elements:
        elset = "runtime_all_shells"
        elsets[elset].extend(shell_elements)
        shell_sections.append(ShellSection(elset=elset, material="steel", thickness_m=None))

    return FeShellModel(
        nodes=nodes,
        shell_elements=shell_elements,
        elsets={name: tuple(sorted(set(values))) for name, values in elsets.items()},
        shell_sections=tuple(shell_sections),
        source_path=str(payload.get("source", "runtime FEM result")),
    )


def frd_stress_from_runtime_result(runtime_result: Any) -> FrdStressResult:
    """Build an FRD-like stress result from a runtime FEM result payload."""

    payload = _runtime_fea_payload(runtime_result)
    model = fe_shell_model_from_runtime_result(payload)
    raw_stress = payload.get("nodal_stress_pa", {}) or {}
    nodal_stress: dict[int, tuple[float, ...]] = {}
    for node_id, values in raw_stress.items():
        nodal_stress[int(node_id)] = tuple(float(value) for value in values)
    return FrdStressResult(
        path=str(payload.get("source", "runtime FEM result")),
        nodes=model.nodes,
        element_nodes={
            int(element_id): tuple(int(node_id) for node_id in element.node_ids)
            for element_id, element in model.shell_elements.items()
        },
        components=tuple(str(component) for component in payload.get("stress_components", ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"))),
        nodal_stress=nodal_stress,
        units=str(payload.get("units", "Pa")),
    )


def cylinder_geometry_from_runtime_result(runtime_result: Any, model: FeShellModel | None = None) -> CylinderGeometry | None:
    """Return runtime-provided cylinder metadata when available."""

    payload = _runtime_fea_payload(runtime_result)
    geometry = payload.get("cylinder_geometry")
    if not isinstance(geometry, dict):
        return None
    valid_shell_ids = set(model.shell_elements) if model is not None else None
    skin_id_values: list[int] = []
    for value in geometry.get("skin_element_ids", ()) or ():
        try:
            element_id = int(value)
        except (TypeError, ValueError):
            continue
        if valid_shell_ids is None or element_id in valid_shell_ids:
            skin_id_values.append(element_id)
    skin_ids = tuple(skin_id_values)
    if not skin_ids:
        return None
    axial_bounds = geometry.get("axial_bounds", (0.0, 0.0))
    return CylinderGeometry(
        axis_origin=tuple(float(value) for value in geometry.get("axis_origin", (0.0, 0.0, 0.0))),
        axis_direction=_normalise(tuple(float(value) for value in geometry.get("axis_direction", (0.0, 0.0, 1.0)))),
        radius_m=float(geometry.get("radius_m", 0.0) or 0.0),
        axial_bounds=(float(axial_bounds[0]), float(axial_bounds[1])),
        radial_rms_error_m=float(geometry.get("radial_rms_error_m", 0.0) or 0.0),
        skin_element_ids=tuple(sorted(set(skin_ids))),
        skin_thickness_m=_safe_float(geometry.get("skin_thickness_m")),
        confidence=float(geometry.get("confidence", 1.0) or 1.0),
        diagnostics=tuple(str(item) for item in geometry.get("diagnostics", ()) or ()),
    )


def cylinder_members_from_runtime_result(
    runtime_result: Any,
    geometry: CylinderGeometry,
) -> tuple[CylinderMember, ...]:
    """Return runtime beam stiffeners/girders as cylinder member boundaries."""

    payload = _runtime_fea_payload(runtime_result)
    members: list[CylinderMember] = []
    seen: set[tuple[str, int]] = set()
    for item in payload.get("runtime_members", ()) or ():
        role_text = str(item.get("role", "")).lower()
        if "flange" in role_text:
            continue
        if "stiffener" in role_text:
            role = "longitudinal_stiffener"
        elif "girder" in role_text or "frame" in role_text:
            role = "ring_frame"
        else:
            continue
        try:
            points = [tuple(float(value) for value in point) for point in item.get("points", ()) or ()]
        except (TypeError, ValueError):
            continue
        if len(points) < 2:
            continue
        section = item.get("section", {}) or {}
        centroid = _mean_point(points)
        if role == "longitudinal_stiffener":
            station = _cylinder_angle(centroid, geometry)
            direction = geometry.axis_direction
        else:
            station = _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
            radial = _normalise(_radial_vector(centroid, geometry.axis_origin, geometry.axis_direction))
            direction = _normalise(_cross(geometry.axis_direction, radial))
        key = (role, int(round(station * 1.0e7)))
        if key in seen:
            continue
        seen.add(key)
        web_height = max(_safe_float(section.get("web_height")) or 0.0, 0.0)
        web_thickness = max(_safe_float(section.get("web_thickness")) or 0.0, 0.0)
        flange_width = max(_safe_float(section.get("flange_width")) or 0.0, 0.0)
        flange_thickness = max(_safe_float(section.get("flange_thickness")) or 0.0, 0.0)
        section_type = "T" if flange_width > 0.0 and flange_thickness > 0.0 else "FB"
        members.append(
            CylinderMember(
                member_id=f"runtime_{role}_{len(members) + 1:03d}",
                role=role,
                section_type=section_type,
                web_element_ids=(),
                flange_element_ids=(int(item.get("id", 0) or 0),) if section_type == "T" else (),
                station=station,
                direction=direction,
                web_height_m=web_height,
                flange_width_m=flange_width if flange_width > 0.0 else None,
                web_thickness_m=web_thickness if web_thickness > 0.0 else None,
                flange_thickness_m=flange_thickness if flange_thickness > 0.0 else None,
                confidence=1.0,
                diagnostics=("runtime beam member used as cylinder bay boundary",),
            )
        )
    return tuple(sorted(members, key=lambda member: (member.role, member.station)))


def _runtime_payload_has_member_web_shells(payload: dict[str, Any]) -> bool:
    for shell in payload.get("shells", ()) or ():
        role = str(shell.get("role", shell.get("elset", ""))).lower()
        if "stiffener_web" in role or "girder_web" in role or "frame_web" in role:
            return True
    return False


def _runtime_flange_beams_by_station(
    runtime_result: Any,
    geometry: CylinderGeometry,
) -> dict[str, list[tuple[float, dict[str, Any], int]]]:
    payload = _runtime_fea_payload(runtime_result)
    flanges: dict[str, list[tuple[float, dict[str, Any], int]]] = {
        "longitudinal_stiffener": [],
        "ring_stiffener": [],
        "ring_frame": [],
    }
    for item in payload.get("runtime_members", ()) or ():
        role_text = str(item.get("role", "")).lower()
        if "flange" not in role_text:
            continue
        try:
            points = [tuple(float(value) for value in point) for point in item.get("points", ()) or ()]
        except (TypeError, ValueError):
            continue
        if len(points) < 2:
            continue
        centroid = _mean_point(points)
        if "stiffener" in role_text:
            role = "longitudinal_stiffener"
            station = _cylinder_angle(centroid, geometry)
        elif "girder" in role_text or "frame" in role_text:
            role = "ring_frame"
            station = _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
        else:
            continue
        flanges.setdefault(role, []).append((station, dict(item.get("section") or {}), int(item.get("id", 0) or 0)))
    return flanges


def _runtime_flange_dimensions(section: dict[str, Any]) -> tuple[float | None, float | None]:
    width = _safe_float(section.get("web_thickness"))
    thickness = _safe_float(section.get("web_height"))
    if width is None or width <= 0.0:
        width = _safe_float(section.get("flange_width"))
    if thickness is None or thickness <= 0.0:
        thickness = _safe_float(section.get("flange_thickness"))
    return width, thickness


def _augment_cylinder_members_with_runtime_flange_beams(
    members: Sequence[CylinderMember],
    runtime_result: Any,
    geometry: CylinderGeometry,
) -> tuple[CylinderMember, ...]:
    flanges_by_role = _runtime_flange_beams_by_station(runtime_result, geometry)
    if not any(flanges_by_role.values()):
        return tuple(members)
    axial_tol = max((geometry.axial_bounds[1] - geometry.axial_bounds[0]) * 1.0e-5, 1.0e-7)
    angular_tol = max(axial_tol / max(geometry.radius_m, 1.0e-12), 1.0e-5)
    augmented: list[CylinderMember] = []
    for member in members:
        matched_role = member.role
        candidates = flanges_by_role.get(member.role, [])
        if not candidates and member.role == "ring_stiffener":
            candidates = flanges_by_role.get("ring_frame", [])
            if candidates:
                matched_role = "ring_frame"
        best: tuple[float, dict[str, Any], int] | None = None
        for station, section, beam_id in candidates:
            if member.role == "longitudinal_stiffener":
                distance = abs(_wrapped_angle_difference(station, member.station))
                tolerance = angular_tol
            else:
                distance = abs(station - member.station)
                tolerance = axial_tol
            if distance <= tolerance and (best is None or distance < best[0]):
                best = (distance, section, beam_id)
        if best is None:
            augmented.append(member)
            continue
        flange_width, flange_thickness = _runtime_flange_dimensions(best[1])
        if not flange_width or not flange_thickness:
            augmented.append(member)
            continue
        augmented.append(
            CylinderMember(
                member_id=member.member_id,
                role=matched_role,
                section_type="T",
                web_element_ids=member.web_element_ids,
                flange_element_ids=tuple(sorted(set(member.flange_element_ids + ((best[2],) if best[2] else ())))),
                station=member.station,
                direction=member.direction,
                web_height_m=member.web_height_m,
                flange_width_m=flange_width,
                web_thickness_m=member.web_thickness_m,
                flange_thickness_m=flange_thickness,
                confidence=member.confidence,
                diagnostics=member.diagnostics + ("runtime flange beam supplied flange dimensions",),
            )
        )
    return tuple(augmented)


def _runtime_frd_summary(payload: dict[str, Any], stress: FrdStressResult | None) -> dict[str, Any]:
    return {
        "source": str(payload.get("source", "runtime FEM result")),
        "format": str(payload.get("format", "anystructure-runtime-fe-results-v1")),
        "result_blocks": [
            {
                "name": "STRESS",
                "components": list(stress.components if stress is not None else payload.get("stress_components", ())),
                "node_count": 0 if stress is None else len(stress.nodal_stress),
                "units": str(payload.get("units", "Pa")),
            }
        ],
    }


def _create_flat_fea_buckling_session_from_model(
    model: FeShellModel,
    frd_stress: FrdStressResult | None = None,
    *,
    inp_path: str = "runtime FEM result",
    frd_path: str | None = None,
    frd_summary: dict[str, Any] | None = None,
    load_case: int | None = None,
    calculation_method: str = "SemiAnalytical S3/U3",
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    ml_algo: Any = None,
    run_buckling: bool = True,
    stress_reduction_method: str | None = None,
) -> FeaBucklingSession:
    fields = tuple(infer_plate_fields(model))
    diagnostics: list[str] = []
    reduction_method = normalize_stress_reduction_method(stress_reduction_method)
    diagnostics.append(f"stress reduction method: {reduction_method}")

    if frd_stress is not None and frd_stress.nodal_stress:
        panel_stresses = tuple(
            reduce_field_stresses(
                model,
                fields,
                frd_stress,
                stress_reduction_method=reduction_method,
            )
        )
    else:
        panel_stresses = ()
        diagnostics.append("no runtime/FRD stresses supplied; panel stresses set to defaults")

    buckling_results: tuple[dict[str, Any], ...] = ()
    if run_buckling and panel_stresses:
        buckling_results = tuple(
            calculate_field_buckling(
                fields,
                panel_stresses,
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
                ml_algo=ml_algo,
            )
        )

    unavailable_results = [result for result in buckling_results if not result.get("available", False)]
    if unavailable_results:
        diagnostics.append(
            f"{len(unavailable_results)} of {len(buckling_results)} flat-panel buckling calculations "
            "returned no identifiable usage factor"
        )
        diagnostics.extend(
            f"{result.get('field_id', '?')}: {result.get('error', 'no result')}"
            for result in unavailable_results[:20]
        )

    plot_by_field = {record["field_id"]: record for record in panel_plot_records(model, fields)}
    stress_by_field = {stress.field_id: stress for stress in panel_stresses}
    result_by_field = {str(result.get("field_id")): result for result in buckling_results if result.get("field_id")}
    panels = tuple(
        FeaBucklingPanel(
            field_id=field_item.field_id,
            field=field_item,
            stress=stress_by_field.get(field_item.field_id),
            anystructure_input=anystructure_input_for_field(
                field_item,
                stress_by_field.get(field_item.field_id),
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
            ),
            plot_bounds=tuple(plot_by_field.get(field_item.field_id, {}).get("bounds", (0.0, 0.0, 0.0, 0.0))),
            buckling_result=result_by_field.get(field_item.field_id),
            usage_factor=_selected_uf_from_buckling_result(result_by_field.get(field_item.field_id, {})),
        )
        for field_item in fields
    )
    return FeaBucklingSession(
        inp_path=inp_path,
        frd_path=frd_path,
        model=model,
        fields=fields,
        panels=panels,
        frd_summary=frd_summary,
        diagnostics=tuple(diagnostics),
        active_load_case=load_case,
    )


def _create_cylinder_fea_buckling_session_from_model(
    model: FeShellModel,
    frd_stress: FrdStressResult | None = None,
    *,
    geometry: CylinderGeometry | None = None,
    members: Sequence[CylinderMember] | None = None,
    inp_path: str = "runtime FEM result",
    frd_path: str | None = None,
    frd_summary: dict[str, Any] | None = None,
    load_case: int | None = None,
    calculation_method: str = "DNV-RP-C202",
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    ml_algo: Any = None,
    run_buckling: bool = True,
    stress_reduction_method: str | None = None,
) -> FeaCylinderSession:
    geometry = detect_cylinder_geometry(model) if geometry is None else geometry
    fields = tuple(infer_cylinder_fields(model, geometry, members=members))
    diagnostics: list[str] = []
    reduction_method = normalize_stress_reduction_method(stress_reduction_method)
    diagnostics.append(f"stress reduction method: {reduction_method}")
    if calculation_method in _FLAT_PANEL_BUCKLING_METHODS:
        diagnostics.append(_cylinder_flat_panel_method_warning(calculation_method))
    else:
        diagnostics.append(
            "cylinder calculation uses CylStru; requested common GUI method="
            f"{calculation_method!r}, acceptance={buckling_acceptance!r}"
        )

    if frd_stress is not None and frd_stress.nodal_stress:
        stresses = tuple(
            reduce_cylinder_stresses(
                model,
                geometry,
                fields,
                frd_stress,
                stress_reduction_method=reduction_method,
            )
        )
    else:
        stresses = ()
        diagnostics.append("no runtime/FRD stresses supplied; cylinder stresses set to defaults")

    buckling_results: tuple[dict[str, Any], ...] = ()
    if run_buckling and stresses:
        buckling_results = tuple(
            calculate_cylinder_buckling(
                fields,
                stresses,
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
                ml_algo=ml_algo,
            )
        )

    unavailable_results = [result for result in buckling_results if not result.get("available", False)]
    if unavailable_results:
        diagnostics.append(
            f"{len(unavailable_results)} of {len(buckling_results)} cylinder buckling calculations "
            "returned no identifiable usage factor"
        )
        diagnostics.extend(
            f"{result.get('field_id', '?')}: {result.get('error', 'no result')}"
            for result in unavailable_results[:20]
        )

    stress_by_field = {stress.field_id: stress for stress in stresses}
    result_by_field = {str(result["field_id"]): result for result in buckling_results if result.get("field_id")}
    panels = tuple(
        FeaCylinderPanel(
            field_id=field_item.field_id,
            field=field_item,
            stress=stress_by_field.get(field_item.field_id),
            anystructure_input=anystructure_input_for_cylinder_field(
                field_item,
                stress_by_field.get(field_item.field_id),
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
            ),
            buckling_result=result_by_field.get(field_item.field_id),
            usage_factor=_selected_uf_from_buckling_result(result_by_field.get(field_item.field_id, {})),
        )
        for field_item in fields
    )
    return FeaCylinderSession(
        inp_path=inp_path,
        frd_path=frd_path,
        model=model,
        geometry=geometry,
        fields=fields,
        panels=panels,
        frd_summary=frd_summary,
        diagnostics=tuple(diagnostics),
        active_load_case=load_case,
    )


def create_runtime_fea_buckling_session(
    runtime_result: Any,
    *,
    geometry_type: str = "auto",
    load_case: int | None = None,
    **kwargs: Any,
) -> FeaBucklingSession | FeaCylinderSession:
    """Return panel-by-panel buckling sessions directly from a runtime FEM result."""

    payload = _runtime_fea_payload(runtime_result)
    model = fe_shell_model_from_runtime_result(payload)
    frd_stress = frd_stress_from_runtime_result(payload)
    frd_summary = _runtime_frd_summary(payload, frd_stress)
    source = str(payload.get("source", "runtime FEM result"))

    geometry_choice = geometry_type.strip().lower()
    if geometry_choice not in {"auto", "flat", "cylinder"}:
        raise ValueError("geometry_type must be 'auto', 'flat', or 'cylinder'")
    if geometry_choice == "cylinder":
        runtime_geometry = cylinder_geometry_from_runtime_result(payload, model)
        runtime_members = None
        if runtime_geometry is not None:
            if _runtime_payload_has_member_web_shells(payload):
                runtime_members = _augment_cylinder_members_with_runtime_flange_beams(
                    _infer_cylinder_members(model, runtime_geometry),
                    payload,
                    runtime_geometry,
                )
            else:
                runtime_members = cylinder_members_from_runtime_result(payload, runtime_geometry)
        return _create_cylinder_fea_buckling_session_from_model(
            model,
            frd_stress,
            geometry=runtime_geometry,
            members=runtime_members,
            inp_path=source,
            frd_path=source,
            frd_summary=frd_summary,
            load_case=load_case,
            **kwargs,
        )
    if geometry_choice == "flat":
        return _create_flat_fea_buckling_session_from_model(
            model,
            frd_stress,
            inp_path=source,
            frd_path=source,
            frd_summary=frd_summary,
            load_case=load_case,
            **kwargs,
        )

    if str(payload.get("geometry_type", "")).strip().lower() == "cylinder" or is_cylindrical_shell_model(model):
        runtime_geometry = cylinder_geometry_from_runtime_result(payload, model)
        runtime_members = None
        if runtime_geometry is not None:
            if _runtime_payload_has_member_web_shells(payload):
                runtime_members = _augment_cylinder_members_with_runtime_flange_beams(
                    _infer_cylinder_members(model, runtime_geometry),
                    payload,
                    runtime_geometry,
                )
            else:
                runtime_members = cylinder_members_from_runtime_result(payload, runtime_geometry)
        return _create_cylinder_fea_buckling_session_from_model(
            model,
            frd_stress,
            geometry=runtime_geometry,
            members=runtime_members,
            inp_path=source,
            frd_path=source,
            frd_summary=frd_summary,
            load_case=load_case,
            **kwargs,
        )
    return _create_flat_fea_buckling_session_from_model(
        model,
        frd_stress,
        inp_path=source,
        frd_path=source,
        frd_summary=frd_summary,
        load_case=load_case,
        **kwargs,
    )


def create_fea_cylinder_buckling_session(
    inp_path: str | os.PathLike[str],
    frd_path: str | os.PathLike[str] | None = None,
    *,
    load_case: int | None = None,
    calculation_method: str = "DNV-RP-C202",
    buckling_acceptance: str = "ultimate",
    pressure_mpa: float = 0.0,
    material_yield_mpa: float = 355.0,
    elastic_modulus_mpa: float = 210000.0,
    material_factor: float = 1.15,
    poisson: float = 0.3,
    ml_algo: Any = None,
    run_buckling: bool = True,
    stress_reduction_method: str | None = None,
) -> FeaCylinderSession:
    """Create the cylinder equivalent of ``create_fea_buckling_session``.

    ``calculation_method`` and ``buckling_acceptance`` are accepted because the
    FEA-result GUI sends the same common keyword set for flat and cylindrical
    models. Cylinder buckling is still evaluated by ``CylStru``.
    """

    inp_path = str(inp_path)
    frd_path_text = _default_fea_result_path(inp_path, frd_path)
    model = read_fea_shell_model(inp_path)
    geometry = detect_cylinder_geometry(model)
    fields = tuple(infer_cylinder_fields(model, geometry))
    frd_summary = read_fea_result_summary(frd_path_text) if frd_path_text else None
    diagnostics: list[str] = []
    reduction_method = normalize_stress_reduction_method(stress_reduction_method)
    diagnostics.append(f"stress reduction method: {reduction_method}")
    if calculation_method in _FLAT_PANEL_BUCKLING_METHODS:
        diagnostics.append(_cylinder_flat_panel_method_warning(calculation_method))
    else:
        diagnostics.append(
            "cylinder calculation uses CylStru; requested common GUI method="
            f"{calculation_method!r}, acceptance={buckling_acceptance!r}"
        )

    if frd_path_text:
        frd_stress = read_fea_stress(frd_path_text)
        stresses = tuple(
            reduce_cylinder_stresses(
                model,
                geometry,
                fields,
                frd_stress,
                stress_reduction_method=reduction_method,
            )
        )
    else:
        stresses = ()
        diagnostics.append("no FRD result file supplied; cylinder stresses set to defaults")

    buckling_results: tuple[dict[str, Any], ...] = ()
    if run_buckling and stresses:
        buckling_results = tuple(
            calculate_cylinder_buckling(
                fields,
                stresses,
                calculation_method=calculation_method,
                buckling_acceptance=buckling_acceptance,
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
                ml_algo=ml_algo,
            )
        )

    unavailable_results = [
        result for result in buckling_results
        if not result.get("available", False)
    ]
    if unavailable_results:
        diagnostics.append(
            f"{len(unavailable_results)} of {len(buckling_results)} cylinder buckling calculations "
            "returned no identifiable usage factor"
        )
        diagnostics.extend(
            f"{result.get('field_id', '?')}: {result.get('error', 'no result')}"
            for result in unavailable_results[:20]
        )

    stress_by_field = {stress.field_id: stress for stress in stresses}
    result_by_field = {
        str(result["field_id"]): result
        for result in buckling_results
        if result.get("field_id")
    }
    panels = tuple(
        FeaCylinderPanel(
            field_id=field_item.field_id,
            field=field_item,
            stress=stress_by_field.get(field_item.field_id),
            anystructure_input=anystructure_input_for_cylinder_field(
                field_item,
                stress_by_field.get(field_item.field_id),
                pressure_mpa=pressure_mpa,
                material_yield_mpa=material_yield_mpa,
                elastic_modulus_mpa=elastic_modulus_mpa,
                material_factor=material_factor,
                poisson=poisson,
            ),
            buckling_result=result_by_field.get(field_item.field_id),
            usage_factor=_selected_uf_from_buckling_result(result_by_field.get(field_item.field_id, {})),
        )
        for field_item in fields
    )
    return FeaCylinderSession(
        inp_path=inp_path,
        frd_path=frd_path_text,
        model=model,
        geometry=geometry,
        fields=fields,
        panels=panels,
        frd_summary=frd_summary,
        diagnostics=tuple(diagnostics),
    )


def create_fea_structure_buckling_session(
    inp_path: str | os.PathLike[str],
    frd_path: str | os.PathLike[str] | None = None,
    *,
    geometry_type: str = "auto",
    load_case: int | None = None,
    **kwargs: Any,
) -> FeaBucklingSession | FeaCylinderSession:
    """Dispatch to flat-plate or cylindrical-shell extraction.

    ``geometry_type`` may be ``"auto"``, ``"flat"`` or ``"cylinder"``.
    """

    geometry_type = geometry_type.strip().lower()
    if geometry_type not in {"auto", "flat", "cylinder"}:
        raise ValueError("geometry_type must be 'auto', 'flat', or 'cylinder'")
    if geometry_type == "cylinder":
        return create_fea_cylinder_buckling_session(inp_path, frd_path, load_case=load_case, **kwargs)
    if geometry_type == "flat":
        return _create_flat_fea_buckling_session(inp_path, frd_path, load_case=load_case, **kwargs)

    model = read_fea_shell_model(inp_path)
    if _is_sesam_model_path(inp_path):
        return _create_flat_fea_buckling_session(inp_path, frd_path, load_case=load_case, **kwargs)
    if is_cylindrical_shell_model(model):
        return create_fea_cylinder_buckling_session(inp_path, frd_path, load_case=load_case, **kwargs)
    return _create_flat_fea_buckling_session(inp_path, frd_path, load_case=load_case, **kwargs)


def create_fea_buckling_session(
    inp_path: str | os.PathLike[str],
    frd_path: str | os.PathLike[str] | None = None,
    *,
    geometry_type: str = "auto",
    load_case: int | None = None,
    **kwargs: Any,
) -> FeaBucklingSession | FeaCylinderSession:
    """Public FEA-session entry point used by the ANYstructure GUI.

    Existing callers continue to use this function.  Cylindrical shell models
    are detected automatically and returned as ``FeaCylinderSession`` objects.
    """
    return create_fea_structure_buckling_session(
        inp_path,
        frd_path,
        geometry_type=geometry_type,
        load_case=load_case,
        **kwargs,
    )


def cylinder_3d_records(
    model: FeShellModel,
    geometry: CylinderGeometry,
    fields: Sequence[CylinderField],
    field_values: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return actual curved FE polygons for cylinder GUI rendering."""

    records: list[dict[str, Any]] = []
    for index, field_item in enumerate(fields):
        polygons = _field_element_polygons(
            model,
            PlateField(
                field_id=field_item.field_id,
                base_patch_id="cylinder_skin",
                element_ids=field_item.element_ids,
                bbox=_bbox_for_elements(model, field_item.element_ids) if field_item.element_ids else (
                    (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)
                ),
                span_m=field_item.axial_length_m,
                spacing_m=field_item.circumferential_spacing_m,
                transverse_bounds=field_item.angular_bounds_rad,
                attached_member_ids=field_item.attached_member_ids,
            ),
        )
        points = [point for polygon in polygons for point in polygon]
        centroid = _mean_point(points)
        radial = _normalise(_radial_vector(centroid, geometry.axis_origin, geometry.axis_direction))
        local_y = _normalise(_cross(geometry.axis_direction, radial))
        records.append(
            {
                "field_id": field_item.field_id,
                "index": index,
                "polygons": polygons,
                "bbox": _bbox(points) if points else None,
                "centroid": centroid,
                "normal": radial,
                "local_x": geometry.axis_direction,
                "local_y": local_y,
                "value": None if field_values is None else field_values.get(field_item.field_id),
                "axial_length_m": field_item.axial_length_m,
                "circumferential_spacing_m": field_item.circumferential_spacing_m,
            }
        )
    return records


def _infer_cylinder_members(
    model: FeShellModel,
    geometry: CylinderGeometry,
) -> tuple[CylinderMember, ...]:
    skin_ids = set(geometry.skin_element_ids)
    longitudinal_web_ids: list[int] = []
    ring_web_ids: list[int] = []
    flange_ids: list[int] = []

    radial_margin = max(geometry.radius_m * 0.002, 1.0e-7)
    for element in model.shell_elements.values():
        if element.element_id in skin_ids:
            continue
        points = [model.nodes[node_id] for node_id in element.corner_node_ids]
        centroid = _mean_point(points)
        radial = _radial_vector(centroid, geometry.axis_origin, geometry.axis_direction)
        radial_distance = _length(radial)
        normal = _element_normal(points)
        radial_direction = _normalise(radial)
        radial_alignment = abs(_dot(normal, radial_direction))
        axial_alignment = abs(_dot(normal, geometry.axis_direction))
        radial_extent = _point_radial_extent(points, geometry)

        if radial_extent > radial_margin and axial_alignment >= 0.60:
            ring_web_ids.append(element.element_id)
        elif radial_extent > radial_margin and axial_alignment <= 0.40 and radial_alignment <= 0.45:
            longitudinal_web_ids.append(element.element_id)
        elif abs(radial_distance - geometry.radius_m) > radial_margin and radial_alignment >= 0.55:
            flange_ids.append(element.element_id)

    longitudinal_components = _merge_cylinder_components_by_station(
        model,
        _connected_components_by_corner_edges(model, longitudinal_web_ids),
        geometry,
        role="longitudinal",
    )
    ring_components = _merge_cylinder_components_by_station(
        model,
        _connected_components_by_corner_edges(model, ring_web_ids),
        geometry,
        role="ring",
    )
    flange_components = _connected_components_by_corner_edges(model, flange_ids)

    flange_data = [
        (
            tuple(component),
            _component_centroid(model, component),
            _component_radial_height(model, component, geometry),
            _component_axial_bounds(model, component, geometry),
            _component_angular_mean(model, component, geometry),
        )
        for component in flange_components
    ]

    members: list[CylinderMember] = []
    for index, component in enumerate(longitudinal_components, start=1):
        centroid = _component_centroid(model, component)
        angle = _cylinder_angle(centroid, geometry)
        flange = _match_cylinder_flange(
            flange_data,
            role="longitudinal_stiffener",
            station=angle,
            component=component,
            model=model,
            geometry=geometry,
        )
        members.append(
            _make_cylinder_member(
                model,
                geometry,
                member_id=f"longitudinal_stiffener_{index:03d}",
                role="longitudinal_stiffener",
                station=angle,
                web_component=component,
                flange_component=() if flange is None else flange,
            )
        )

    raw_rings: list[CylinderMember] = []
    for index, component in enumerate(ring_components, start=1):
        centroid = _component_centroid(model, component)
        station = _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
        flange = _match_cylinder_flange(
            flange_data,
            role="ring",
            station=station,
            component=component,
            model=model,
            geometry=geometry,
        )
        raw_rings.append(
            _make_cylinder_member(
                model,
                geometry,
                member_id=f"ring_{index:03d}",
                role="ring_stiffener",
                station=station,
                web_component=component,
                flange_component=() if flange is None else flange,
            )
        )

    if raw_rings:
        heights = [member.web_height_m for member in raw_rings]
        median_height = _median(heights) or 0.0
        for index, member in enumerate(raw_rings, start=1):
            role = "ring_frame" if member.web_height_m > max(median_height * 1.35, median_height + 1.0e-8) else "ring_stiffener"
            members.append(
                CylinderMember(
                    member_id=f"{role}_{index:03d}",
                    role=role,
                    section_type=member.section_type,
                    web_element_ids=member.web_element_ids,
                    flange_element_ids=member.flange_element_ids,
                    station=member.station,
                    direction=member.direction,
                    web_height_m=member.web_height_m,
                    flange_width_m=member.flange_width_m,
                    web_thickness_m=member.web_thickness_m,
                    flange_thickness_m=member.flange_thickness_m,
                    confidence=member.confidence,
                    diagnostics=member.diagnostics,
                )
            )

    if getattr(model, "beam_elements", None):
        beam_longitudinals = []
        beam_rings = []
        for element in model.beam_elements.values():
            nodes = [model.nodes[n] for n in element.node_ids]
            centroid = _mean_point(nodes)
            if len(nodes) >= 2:
                tangent = _normalise((nodes[-1][0]-nodes[0][0], nodes[-1][1]-nodes[0][1], nodes[-1][2]-nodes[0][2]))
            else:
                tangent = geometry.axis_direction
            axial_alignment = abs(_dot(tangent, geometry.axis_direction))
            role = "longitudinal" if axial_alignment >= 0.8 else "ring"
            station = (
                _cylinder_angle(centroid, geometry)
                if role == "longitudinal"
                else _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
            )
            if role == "longitudinal":
                beam_longitudinals.append((station, element))
            else:
                beam_rings.append((station, element))

        axial_length = geometry.axial_bounds[1] - geometry.axial_bounds[0]
        linear_tolerance = max(axial_length * 1.0e-5, geometry.radius_m * 1.0e-5, 1.0e-7)
        angular_tolerance = max(linear_tolerance / max(geometry.radius_m, 1.0e-12), 1.0e-5)

        def group_beams(items, tolerance, is_angle):
            groups = []
            for station, element in items:
                for index, (existing_station, elements) in enumerate(groups):
                    error = abs(_wrapped_angle_difference(station, existing_station)) if is_angle else abs(station - existing_station)
                    if error <= tolerance:
                        elements.append(element)
                        if is_angle:
                            merged = math.atan2(
                                math.sin(existing_station) + math.sin(station),
                                math.cos(existing_station) + math.cos(station),
                            )
                        else:
                            merged = (existing_station + station) / 2.0
                        groups[index] = (merged, elements)
                        break
                else:
                    groups.append((station, [element]))
            return groups

        for index, (station, elements) in enumerate(group_beams(beam_longitudinals, angular_tolerance, True), start=1):
            cross = elements[0].cross_section
            members.append(CylinderMember(
                member_id=f"beam_longitudinal_{index:03d}",
                role="longitudinal_stiffener",
                section_type=cross.get("section_type", "L"),
                web_element_ids=tuple(e.element_id for e in elements),
                flange_element_ids=(),
                station=station,
                direction=geometry.axis_direction,
                web_height_m=cross.get("web_height", 0.0),
                flange_width_m=cross.get("flange_width", 0.0) or None,
                web_thickness_m=cross.get("web_thickness", 0.0) or None,
                flange_thickness_m=cross.get("flange_thickness", 0.0) or None,
                confidence=1.0,
            ))

        for index, (station, elements) in enumerate(group_beams(beam_rings, linear_tolerance, False), start=1):
            cross = elements[0].cross_section
            members.append(CylinderMember(
                member_id=f"beam_ring_{index:03d}",
                role="ring_stiffener",
                section_type=cross.get("section_type", "T"),
                web_element_ids=tuple(e.element_id for e in elements),
                flange_element_ids=(),
                station=station,
                direction=_normalise((model.nodes[elements[0].node_ids[-1]][0]-model.nodes[elements[0].node_ids[0]][0], model.nodes[elements[0].node_ids[-1]][1]-model.nodes[elements[0].node_ids[0]][1], model.nodes[elements[0].node_ids[-1]][2]-model.nodes[elements[0].node_ids[0]][2])) if len(elements[0].node_ids) >= 2 else geometry.axis_direction,
                web_height_m=cross.get("web_height", 0.0),
                flange_width_m=cross.get("flange_width", 0.0) or None,
                web_thickness_m=cross.get("web_thickness", 0.0) or None,
                flange_thickness_m=cross.get("flange_thickness", 0.0) or None,
                confidence=1.0,
            ))

    return tuple(members)



def _merge_cylinder_components_by_station(
    model: FeShellModel,
    components: Sequence[Sequence[int]],
    geometry: CylinderGeometry,
    *,
    role: str,
) -> list[list[int]]:
    """Merge disconnected mesh strips that represent one physical member."""

    groups: list[tuple[float, list[int]]] = []
    axial_length = geometry.axial_bounds[1] - geometry.axial_bounds[0]
    linear_tolerance = max(axial_length * 1.0e-5, geometry.radius_m * 1.0e-5, 1.0e-7)
    angular_tolerance = max(linear_tolerance / max(geometry.radius_m, 1.0e-12), 1.0e-5)

    for component in components:
        centroid = _component_centroid(model, component)
        station = (
            _cylinder_angle(centroid, geometry)
            if role == "longitudinal"
            else _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
        )
        for index, (existing_station, element_ids) in enumerate(groups):
            error = (
                abs(_wrapped_angle_difference(station, existing_station))
                if role == "longitudinal"
                else abs(station - existing_station)
            )
            tolerance = angular_tolerance if role == "longitudinal" else linear_tolerance
            if error <= tolerance:
                element_ids.extend(component)
                if role == "longitudinal":
                    merged_station = math.atan2(
                        math.sin(existing_station) + math.sin(station),
                        math.cos(existing_station) + math.cos(station),
                    )
                else:
                    merged_station = (existing_station + station) / 2.0
                groups[index] = (merged_station, element_ids)
                break
        else:
            groups.append((station, list(component)))
    return [sorted(set(element_ids)) for _, element_ids in groups]


def _make_cylinder_member(
    model: FeShellModel,
    geometry: CylinderGeometry,
    *,
    member_id: str,
    role: str,
    station: float,
    web_component: Sequence[int],
    flange_component: Sequence[int],
) -> CylinderMember:
    web_points = _component_points(model, web_component)
    flange_points = _component_points(model, flange_component)
    web_height = _component_radial_height(model, web_component, geometry)
    if role == "longitudinal_stiffener":
        direction = geometry.axis_direction
        flange_width = _component_circumferential_extent(flange_points, geometry) if flange_points else None
    else:
        centroid = _component_centroid(model, web_component)
        radial = _normalise(_radial_vector(centroid, geometry.axis_origin, geometry.axis_direction))
        direction = _normalise(_cross(geometry.axis_direction, radial))
        flange_width = _point_cloud_extent_raw(flange_points, geometry.axis_direction) if flange_points else None

    section_type = "FB"
    diagnostics = ["web classified from local shell orientation and radial extent"]
    if flange_component:
        section_type = "T"
        diagnostics.append("flange matched by shared geometry and station proximity")
    else:
        diagnostics.append("no matching flange shell component found")
    return CylinderMember(
        member_id=member_id,
        role=role,
        section_type=section_type,
        web_element_ids=tuple(sorted(web_component)),
        flange_element_ids=tuple(sorted(flange_component)),
        station=station,
        direction=direction,
        web_height_m=web_height,
        flange_width_m=flange_width,
        web_thickness_m=_shell_section_thickness_for_elements(model, web_component),
        flange_thickness_m=_shell_section_thickness_for_elements(model, flange_component),
        diagnostics=tuple(diagnostics),
    )


def _match_cylinder_flange(
    flange_data: Sequence[tuple[tuple[int, ...], Point3D, float, tuple[float, float], float]],
    *,
    role: str,
    station: float,
    component: Sequence[int],
    model: FeShellModel,
    geometry: CylinderGeometry,
) -> tuple[int, ...] | None:
    web_nodes = {
        node_id
        for element_id in component
        for node_id in model.shell_elements[element_id].corner_node_ids
    }
    best: tuple[float, tuple[int, ...]] | None = None
    for flange_component, centroid, _, axial_bounds, angle in flange_data:
        flange_nodes = {
            node_id
            for element_id in flange_component
            for node_id in model.shell_elements[element_id].corner_node_ids
        }
        shares_node = bool(web_nodes & flange_nodes)
        if role == "longitudinal_stiffener":
            station_error = abs(_wrapped_angle_difference(angle, station)) * geometry.radius_m
        else:
            flange_station = _axial_coordinate(centroid, geometry.axis_origin, geometry.axis_direction)
            station_error = abs(flange_station - station)
        score = station_error - (1.0 if shares_node else 0.0)
        if shares_node or station_error <= max(geometry.radius_m * 0.02, 1.0e-4):
            if best is None or score < best[0]:
                best = (score, flange_component)
    return None if best is None else best[1]


def _cylinder_domain_for_field(field_item: CylinderField) -> str:
    roles = {member.role for member in field_item.members}
    has_longitudinal = "longitudinal_stiffener" in roles
    has_ring = bool(roles & {"ring_stiffener", "ring_frame"})
    if has_longitudinal and has_ring:
        return "Orthogonally Stiffened shell"
    if has_longitudinal:
        return "Longitudinal Stiffened shell"
    if has_ring:
        return "Ring Stiffened shell"
    return "Unstiffened shell"


def _cylinder_calculation_members(
    field_item: CylinderField,
    domain: str | None = None,
) -> tuple[CylinderMember | None, CylinderMember | None, CylinderMember | None]:
    """Return member objects compatible with the selected ``CylStru`` domain.

    The FE geometry may contain several plausible calculation domains in one
    bay.  The legacy cylinder API represents orthogonal stiffening as
    longitudinal stiffeners plus a ring frame object; when the scan finds a
    transverse ring stiffener but no heavy frame, use that transverse member as
    the frame for the calculation instead of calling a setter for an object the
    selected domain does not own.
    """

    domain = _cylinder_domain_for_field(field_item) if domain is None else str(domain)
    longitudinal = _first_cylinder_member(field_item, "longitudinal_stiffener")
    ring = _first_cylinder_member(field_item, "ring_stiffener")
    frame = _first_cylinder_member(field_item, "ring_frame")
    domain_lower = domain.lower()

    if "orthogonally" in domain_lower:
        return longitudinal, None, frame or ring
    if "longitudinal" in domain_lower:
        return longitudinal, None, None
    if "ring stiffened" in domain_lower:
        return None, ring or frame, None
    return None, None, None


def _cylinder_member_input(member: CylinderMember | None) -> dict[str, Any] | None:
    if member is None:
        return None
    return {
        "type": member.section_type,
        "web_height_mm": member.web_height_m * 1000.0,
        "web_thickness_mm": (member.web_thickness_m or 0.0) * 1000.0,
        "flange_width_mm": (member.flange_width_m or 0.0) * 1000.0,
        "flange_thickness_mm": (member.flange_thickness_m or 0.0) * 1000.0,
        "source_member_id": member.member_id,
    }


def _set_cylinder_member(setter: Any, member: CylinderMember, spacing_m: float) -> None:
    setter(
        hw=member.web_height_m * 1000.0,
        tw=(member.web_thickness_m or 0.0) * 1000.0,
        bf=(member.flange_width_m or 0.0) * 1000.0,
        tf=(member.flange_thickness_m or 0.0) * 1000.0,
        stf_type=member.section_type,
        spacing=spacing_m * 1000.0,
    )


def _first_cylinder_member(field_item: CylinderField, role: str) -> CylinderMember | None:
    candidates = [member for member in field_item.members if member.role == role]
    if not candidates:
        return None
    return sorted(candidates, key=_cylinder_member_selection_key, reverse=True)[0]


def _cylinder_member_selection_key(member: CylinderMember) -> tuple[float, float, float, float, int, str]:
    web_thickness = member.web_thickness_m or 0.0
    flange_width = member.flange_width_m or 0.0
    flange_thickness = member.flange_thickness_m or 0.0
    area_proxy = max(member.web_height_m, 0.0) * max(web_thickness, 0.0)
    area_proxy += max(flange_width, 0.0) * max(flange_thickness, 0.0)
    return (
        area_proxy,
        member.web_height_m,
        flange_width,
        flange_thickness,
        len(member.web_element_ids),
        member.member_id,
    )


def _fit_circle_about_axis(points: Any, axis: Vector3D) -> tuple[Point3D, float, float]:
    import numpy as np

    axis_array = np.asarray(axis, dtype=float)
    basis_u = np.asarray(_orthogonal_unit(axis), dtype=float)
    basis_v = np.cross(axis_array, basis_u)
    coordinates_u = points @ basis_u
    coordinates_v = points @ basis_v
    matrix = np.column_stack((2.0 * coordinates_u, 2.0 * coordinates_v, np.ones(len(points))))
    rhs = coordinates_u ** 2 + coordinates_v ** 2
    solution, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    centre_u, centre_v, constant = solution
    radius_squared = max(float(constant + centre_u ** 2 + centre_v ** 2), 0.0)
    radius = math.sqrt(radius_squared)
    axial_centre = float((points @ axis_array).mean())
    origin_array = basis_u * centre_u + basis_v * centre_v + axis_array * axial_centre
    radial_distances = np.sqrt((coordinates_u - centre_u) ** 2 + (coordinates_v - centre_v) ** 2)
    rms = float(np.sqrt(np.mean((radial_distances - radius) ** 2)))
    return tuple(float(value) for value in origin_array), radius, rms


def _orthogonal_unit(axis: Vector3D) -> Vector3D:
    reference = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.8 else (0.0, 1.0, 0.0)
    return _normalise(_cross(axis, reference))


def _canonical_axis(axis: Vector3D) -> Vector3D:
    axis = _normalise(axis)
    largest = max(range(3), key=lambda index: abs(axis[index]))
    if axis[largest] < 0.0:
        axis = tuple(-value for value in axis)  # type: ignore[assignment]
    return axis


def _point_cloud_extent(points: Any, direction: Vector3D) -> float:
    import numpy as np

    values = points @ np.asarray(direction, dtype=float)
    return float(values.max() - values.min())


def _point_cloud_extent_raw(points: Sequence[Point3D], direction: Vector3D) -> float:
    if not points:
        return 0.0
    values = [_dot(point, direction) for point in points]
    return max(values) - min(values)


def _axial_coordinate(point: Point3D, origin: Point3D, axis: Vector3D) -> float:
    return _dot(_subtract(point, origin), axis)


def _radial_vector(point: Point3D, origin: Point3D, axis: Vector3D) -> Vector3D:
    relative = _subtract(point, origin)
    axial = _dot(relative, axis)
    return tuple(relative[index] - axial * axis[index] for index in range(3))  # type: ignore[return-value]


def _cylinder_basis(geometry: CylinderGeometry) -> tuple[Vector3D, Vector3D]:
    first = _orthogonal_unit(geometry.axis_direction)
    second = _normalise(_cross(geometry.axis_direction, first))
    return first, second


def _cylinder_angle(point: Point3D, geometry: CylinderGeometry) -> float:
    radial = _radial_vector(point, geometry.axis_origin, geometry.axis_direction)
    first, second = _cylinder_basis(geometry)
    return math.atan2(_dot(radial, second), _dot(radial, first))


def _positive_angle(angle: float) -> float:
    value = angle % (2.0 * math.pi)
    return value if value > 1.0e-12 else 2.0 * math.pi


def _wrapped_angle_difference(first: float, second: float) -> float:
    return (first - second + math.pi) % (2.0 * math.pi) - math.pi


def _angle_in_interval(angle: float, start: float, end: float) -> bool:
    span = _positive_angle(end - start)
    relative = (angle - start) % (2.0 * math.pi)
    return relative <= span + 1.0e-10


def _component_points(model: FeShellModel, component: Sequence[int]) -> list[Point3D]:
    return [
        model.nodes[node_id]
        for element_id in component
        for node_id in model.shell_elements[element_id].corner_node_ids
    ]


def _component_centroid(model: FeShellModel, component: Sequence[int]) -> Point3D:
    return _mean_point(_component_points(model, component))


def _component_radial_height(
    model: FeShellModel,
    component: Sequence[int],
    geometry: CylinderGeometry,
) -> float:
    points = _component_points(model, component)
    if not points:
        return 0.0
    distances = [
        _length(_radial_vector(point, geometry.axis_origin, geometry.axis_direction))
        for point in points
    ]
    return max(distances) - min(distances)


def _component_axial_bounds(
    model: FeShellModel,
    component: Sequence[int],
    geometry: CylinderGeometry,
) -> tuple[float, float]:
    values = [
        _axial_coordinate(point, geometry.axis_origin, geometry.axis_direction)
        for point in _component_points(model, component)
    ]
    return (min(values), max(values)) if values else (0.0, 0.0)


def _component_angular_mean(
    model: FeShellModel,
    component: Sequence[int],
    geometry: CylinderGeometry,
) -> float:
    angles = [_cylinder_angle(point, geometry) for point in _component_points(model, component)]
    if not angles:
        return 0.0
    return math.atan2(_mean(math.sin(value) for value in angles), _mean(math.cos(value) for value in angles))


def _component_circumferential_extent(
    points: Sequence[Point3D],
    geometry: CylinderGeometry,
) -> float:
    if not points:
        return 0.0
    angles = [_cylinder_angle(point, geometry) for point in points]
    reference = angles[0]
    unwrapped = [reference + _wrapped_angle_difference(angle, reference) for angle in angles]
    return geometry.radius_m * (max(unwrapped) - min(unwrapped))


def _point_radial_extent(points: Sequence[Point3D], geometry: CylinderGeometry) -> float:
    distances = [
        _length(_radial_vector(point, geometry.axis_origin, geometry.axis_direction))
        for point in points
    ]
    return max(distances) - min(distances) if distances else 0.0


def _shell_section_thickness_for_elements(
    model: FeShellModel,
    element_ids: Iterable[int],
) -> float | None:
    element_set = set(element_ids)
    if not element_set or not model.shell_sections:
        return None
    thickness_by_element: dict[int, float] = {}
    fallback_thickness: float | None = None
    for section in model.shell_sections:
        if section.thickness_m is None:
            continue
        if fallback_thickness is None:
            fallback_thickness = section.thickness_m
        if not section.elset:
            continue
        for element_id in model.elsets.get(section.elset, ()):
            thickness_by_element[int(element_id)] = section.thickness_m

    weighted_sum = 0.0
    area_sum = 0.0
    for element_id in element_set:
        thickness = thickness_by_element.get(element_id, fallback_thickness)
        if thickness is None:
            continue
        polygons = _element_polygons_for_ids(model, (element_id,))
        area = _element_area(polygons[0]) if polygons else 1.0
        area = max(area, 1.0e-12)
        weighted_sum += thickness * area
        area_sum += area
    if area_sum > 0.0:
        return weighted_sum / area_sum
    for section in model.shell_sections:
        if section.thickness_m is not None:
            return section.thickness_m
    return None


def _unique_sorted(values: Sequence[float], tolerance: float) -> list[float]:
    result: list[float] = []
    for value in sorted(values):
        if not result or abs(value - result[-1]) > tolerance:
            result.append(value)
    return result


def _member_at_station(
    members: Sequence[CylinderMember],
    station: float,
    tolerance: float = 1.0e-6,
) -> CylinderMember | None:
    candidates = [member for member in members if abs(member.station - station) <= tolerance]
    return None if not candidates else min(candidates, key=lambda member: abs(member.station - station))

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Infer flat stiffened plate fields from FE shell files.")
    parser.add_argument("inp", help="CalculiX/PrePoMax .inp, SESAM .FEM, or SESAM .SIF file")
    parser.add_argument("--frd", help="Optional CalculiX .frd or SESAM .SIF result file")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a compact text summary")
    parser.add_argument("--plot", metavar="PNG", help="Save a colored 2D plot of the inferred buckling panels")
    parser.add_argument("--no-plot-labels", action="store_true", help="Do not annotate panel ids on the plot")
    parser.add_argument(
        "--plot-color-by",
        choices=("panel", "uf"),
        help="Color plot by panel id or buckling utilization factor; default is uf with --buckling, otherwise panel",
    )
    parser.add_argument("--stresses", action="store_true", help="Reduce FE result stresses to one stress set per field")
    parser.add_argument(
        "--stress-method",
        default=STRESS_REDUCTION_METHODS[0],
        choices=STRESS_REDUCTION_METHODS,
        help="Representative FE stress interpretation used with --stresses/--buckling",
    )
    parser.add_argument("--buckling", action="store_true", help="Run ANYstructure buckling checks from reduced FE result stresses")
    parser.add_argument(
        "--buckling-method",
        default="SemiAnalytical S3/U3",
        choices=("DNV-RP-C201 - prescriptive", "SemiAnalytical S3/U3", "ML-Numeric (PULS based)"),
        help="ANYstructure buckling method used with --buckling",
    )
    parser.add_argument(
        "--buckling-acceptance",
        default="ultimate",
        choices=("buckling", "ultimate"),
        help="Buckling result branch used with --buckling",
    )
    parser.add_argument("--pressure-mpa", type=float, default=0.0, help="Optional lateral pressure for buckling checks")
    args = parser.parse_args(argv)

    model = read_fea_shell_model(args.inp)
    fields = infer_plate_fields(model)
    result_path = _default_fea_result_path(args.inp, args.frd)
    frd_summary = read_fea_result_summary(result_path) if result_path else None
    payload = _summary_payload(model, fields, frd_summary)
    panel_stresses: list[PanelStress] = []
    if args.stresses or args.buckling:
        if not result_path:
            parser.error("--stresses/--buckling requires --frd or a SESAM .SIF input/result file")
        frd_stress = read_fea_stress(result_path)
        panel_stresses = reduce_field_stresses(
            model,
            fields,
            frd_stress,
            stress_reduction_method=args.stress_method,
        )
        payload["panel_stresses"] = summarize_panel_stresses(panel_stresses)
    if args.buckling:
        payload["buckling_results"] = calculate_field_buckling(
            fields,
            panel_stresses,
            calculation_method=args.buckling_method,
            buckling_acceptance=args.buckling_acceptance,
            pressure_mpa=args.pressure_mpa,
        )
    if args.plot:
        plot_path = Path(args.plot)
        if plot_path.parent:
            plot_path.parent.mkdir(parents=True, exist_ok=True)
        plot_color_by = args.plot_color_by or ("uf" if args.buckling else "panel")
        if plot_color_by == "uf" and not args.buckling:
            parser.error("--plot-color-by uf requires --buckling")
        field_values = _buckling_uf_by_field(payload["buckling_results"]) if plot_color_by == "uf" else None
        fig = plot_plate_fields(
            model,
            fields,
            output_path=plot_path,
            annotate=not args.no_plot_labels,
            field_values=field_values,
            value_label="UF",
        )
        from matplotlib import pyplot as plt

        plt.close(fig)
        payload["plot_path"] = str(plot_path)
        payload["plot_color_by"] = plot_color_by

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Nodes: {payload['node_count']}")
        print(f"Shell elements: {payload['element_count']}")
        print(f"Plate fields: {payload['field_count']}")
        print(f"Members/webs: {payload['web_count']}")
        print(f"Stiffeners: {payload['stiffener_count']}")
        print(f"Girders: {payload['girder_count']}")
        print(f"Flanges: {payload['flange_count']}")
        print(f"Section types: {', '.join(payload['section_types']) or 'n/a'}")
        if payload["median_spacing_m"] is not None:
            print(f"Median spacing: {payload['median_spacing_m']:.6g} m")
        if args.stresses or args.buckling:
            max_abs_sigma = max(
                (
                    abs(value)
                    for stress in panel_stresses
                    for value in (
                        stress.sigma_x1_mpa,
                        stress.sigma_x2_mpa,
                        stress.sigma_y1_mpa,
                        stress.sigma_y2_mpa,
                    )
                ),
                default=0.0,
            )
            print(f"Reduced stress panels: {len(panel_stresses)}")
            print(f"Max abs reduced normal stress: {max_abs_sigma:.6g} MPa")
        if args.buckling:
            available = [result for result in payload["buckling_results"] if result.get("available")]
            print(f"Buckling panels evaluated: {len(available)}")
        if args.plot:
            print(f"Panel plot: {payload['plot_path']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
