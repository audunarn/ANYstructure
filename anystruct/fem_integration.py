"""ANYstructure integration and UI for the external ANYsolver package.

This module owns application-state extraction, option mapping, Tk controls,
and result presentation. Neutral meshing comes from ANYmesher through the
runtime adapter; numerical analysis lives in ``anysolver.runtime``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields
from typing import Any, Iterable, Sequence
import argparse
import gzip
import inspect
import json
import queue
import math
import os
import re
import sys
import threading
import time
import types
import weakref

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np

from matplotlib import cm, colormaps, colors as mcolors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anysolver as _anysolver_package
from anysolver import runtime as fe_solver

try:
    from anystruct import ecosystem_gui, geometry_generators, representation_geometry
    from anystruct.viewer_backend import (
        BACKEND_LABELS,
        BACKEND_NAMES,
        active_backend,
        apply_view_state,
        backend_diagnostic,
        create_3d_viewer,
        event_widget,
        export_view_state,
        normalize_backend,
        viewport_size,
    )
except ModuleNotFoundError:
    from ANYstructure.anystruct import ecosystem_gui, geometry_generators, representation_geometry
    from ANYstructure.anystruct.viewer_backend import (
        BACKEND_LABELS,
        BACKEND_NAMES,
        active_backend,
        apply_view_state,
        backend_diagnostic,
        create_3d_viewer,
        event_widget,
        export_view_state,
        normalize_backend,
        viewport_size,
    )

try:
    from anystruct import tkinter_3d_canvas_thickness_v6 as _tk3d_canvas_module
except ModuleNotFoundError:
    from ANYstructure.anystruct import tkinter_3d_canvas_thickness_v6 as _tk3d_canvas_module

Tkinter3DCanvas = _tk3d_canvas_module.Tkinter3DCanvas
Point3D = _tk3d_canvas_module.Point3D
_interpolate_thickness_color = _tk3d_canvas_module._interpolate_thickness_color


MINIMUM_ANYSOLVER_VERSION = "0.3.0"


def _numeric_version(value: Any) -> tuple[int, int, int]:
    """Return the first three numeric version components for a local gate."""

    parts = [int(item) for item in re.findall(r"\d+", str(value or ""))[:3]]
    return tuple((parts + [0, 0, 0])[:3])


def _require_supported_anysolver() -> str:
    """Fail clearly when an old editable/runtime ANYsolver shadows the requirement."""

    installed = str(getattr(_anysolver_package, "__version__", "0"))
    installed_numeric = _numeric_version(installed)
    if installed_numeric < _numeric_version(MINIMUM_ANYSOLVER_VERSION):
        raise RuntimeError(
            "ANYstructure FEM requires ANYsolver>="
            + MINIMUM_ANYSOLVER_VERSION
            + "; imported "
            + installed
            + " from "
            + str(getattr(_anysolver_package, "__file__", "unknown location"))
        )
    return installed


def _normalise_pressure_side(value: Any) -> str:
    """Return the user-facing pressure side while accepting legacy inputs."""

    side = str(value or "front").strip().lower()
    if side in {"back", "internal", "inside", "inward side", "positive normal", "outward"}:
        return "back"
    return "front"


def _pressure_surface_sign(value: Any) -> float:
    return -1.0 if _normalise_pressure_side(value) == "back" else 1.0


_KINEMATICS_LABELS = ("Von Karman", "Corotational")


def _normalise_kinematics(value: Any) -> str:
    choice = str(value or "von karman").strip().lower().replace("_", " ").replace("-", " ")
    choice = " ".join(choice.split())
    if choice in {"corotational", "co rotational", "large rotation", "large rotations"}:
        return "corotational"
    return "von_karman"


def _kinematics_label(value: Any) -> str:
    return "Corotational" if _normalise_kinematics(value) == "corotational" else "Von Karman"


def _format_acceleration_summary(value: Any) -> str:
    """Render an [ax, ay, az] acceleration vector, or 'none' when all zero."""
    try:
        vector = [float(component) for component in (value or (0.0, 0.0, 0.0))]
    except (TypeError, ValueError):
        return "none"
    if len(vector) < 3 or not any(abs(component) > 0.0 for component in vector[:3]):
        return "none"
    return "[{:g}, {:g}, {:g}]".format(vector[0], vector[1], vector[2])


def _format_added_mass_summary(summary: dict[str, Any]) -> str:
    """Render the added-mass magnitude and location, or 'none'."""
    mass = _safe_float(summary.get("added_mass_kg"), 0.0)
    location = str(summary.get("added_mass_location", "none") or "none")
    if mass <= 0.0 or location.lower() in {"", "none"}:
        return "none"
    return "{:g} at {}".format(mass, location)


@dataclass(frozen=True)
class RuntimeFEMLineSnapshot:
    """Minimal active-line payload passed from ANYstructure to the runtime FEM UI."""

    line_name: str
    line_points: Any
    structure_bundle: Any
    pressure_pa: float = 0.0
    axial_force_n: float = 0.0
    top_bottom_moment_nm: float = 0.0
    torsional_moment_nm: float = 0.0
    shear_force_n: float = 0.0
    domain: str = ""
    is_cylinder: bool = False
    # Mirrors the main-application "Opposite side" checkbox: members are
    # placed on the negative plate normal / cylinder outside when True.
    members_opposite_side: bool = False
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuntimeFEMOptions:
    """User-selected runtime FEM options from the popup."""

    mesh_fidelity: str = "coarse"
    pressure_pa: float = 0.0
    load_scale: float = 1.0
    include_stiffeners: bool = True
    include_girders: bool = True
    ignore_girder_length: bool = False
    include_end_lids: bool = True
    num_buckling_modes: int = 5
    mesh_size_m: float = 0.0
    top_bottom_moment_nm: float = 0.0
    torsional_moment_nm: float = 0.0
    shear_force_n: float = 0.0
    acceleration_x_m_s2: float = 0.0
    acceleration_y_m_s2: float = 0.0
    acceleration_z_m_s2: float = 0.0
    added_mass_kg: float = 0.0
    added_mass_location: str = "none"
    boundary_condition: str = "auto"
    boundary_constraint_json: str = "{}"
    boundary_auto_supports: bool = True
    symmetry_mode: str = "none"
    shell_element_order: str = "S4"
    beam_element_order: str = "B2"
    member_model: str = "plates as shell, girders as beams"
    analysis_type: str = "linear eigenvalue"
    buckling_analysis_type: str = "linear eigenvalue"
    pressure_direction: str = "front"
    axial_force_n: float = 0.0
    enforced_displacement_x_m: float = 0.0
    enforced_displacement_y_m: float = 0.0
    enforced_displacement_z_m: float = 0.0
    stiffener_eccentricity_m: float = 0.0
    girder_eccentricity_m: float = 0.0
    member_orientation: str = "auto"
    solver_type: str = "direct"
    stress_percentile: float = 95.0
    elastic_modulus_pa: float = 210.0e9
    poisson_ratio: float = 0.3
    yield_stress_pa: float = 355.0e6
    material_model: str = "linear elastic"
    steel_grade: str = "S355"
    steel_thickness_class: str = "auto"
    nonlinear_max_load_factor: float = 3.0
    nonlinear_steps: int = 12
    nonlinear_max_iterations: int = 25
    nonlinear_tolerance: float = 1.0e-6
    nonlinear_layers: int = 5
    nonlinear_solution_control: str = "newton force control"
    post_buckling_enabled: bool = False
    post_buckling_stop_load_fraction: float = 0.5
    post_buckling_max_displacement_m: float = 0.0
    nonlinear_convergence_profile: str = "auto"
    nonlinear_assembly_threads: int = 0
    nonlinear_static_kinematics: str = "von_karman"
    beam_consistent_mass_enabled: bool = False
    deformation_scale: float = 0.0
    custom_load_bc_enabled: bool = False
    custom_loads_add_to_imported: bool = False
    custom_use_nullspace_projection: bool = True
    custom_pressure_pa: float = 0.0
    plate_edge_x0_support: str = "free"
    plate_edge_x1_support: str = "free"
    plate_edge_y0_support: str = "free"
    plate_edge_y1_support: str = "free"
    cylinder_lower_support: str = "free"
    cylinder_upper_support: str = "free"
    plate_edge_x0_load_n_per_m: float = 0.0
    plate_edge_x1_load_n_per_m: float = 0.0
    plate_edge_y0_load_n_per_m: float = 0.0
    plate_edge_y1_load_n_per_m: float = 0.0
    cylinder_lower_edge_load_n_per_m: float = 0.0
    cylinder_upper_edge_load_n_per_m: float = 0.0
    # Component edge loads on global axes: fx/fy/fz [N/m], mx/my/mz [Nm/m].
    # The whole-edge payload maps edge keys (x0/x1/y0/y1, lower/upper, all)
    # to component dicts; the selected payload is a single component dict.
    edge_load_components_json: str = ""
    custom_loads_json: str = ""
    custom_pressure_patches_json: str = ""
    custom_edge_segments_json: str = ""
    custom_selected_edge_load_n_per_m: float = 0.0
    custom_selected_edge_load_components_json: str = ""
    local_refinement_enabled: bool = False
    local_refinement_patches_json: str = "[]"
    local_refinement_fine_factor: float = 0.3
    local_refinement_fine_size_m: float = 0.0
    local_refinement_extent_m: float = 0.0
    local_refinement_zone_factor: float = 1.0
    local_refinement_growth_factor: float = 1.35
    point_refinement_enabled: bool = False
    point_refinement_x_m: float = 0.0
    point_refinement_y_m: float = 0.0
    point_refinement_fine_factor: float = 0.3
    point_refinement_fine_size_m: float = 0.0
    point_refinement_extent_m: float = 0.25
    point_refinement_growth_factor: float = 1.35
    custom_time_domain_enabled: bool = False
    custom_time_domain_duration_s: float = 0.01
    custom_time_domain_total_time_s: float = 0.05
    custom_time_domain_dt_s: float = 0.0005
    custom_time_domain_result_interval_s: float = 0.0
    custom_time_domain_include_static_load: bool = False
    imperfection_enabled: bool = False
    imperfection_shape: str = "standard plate/cylinder"
    imperfection_amplitude_m: float = 0.0
    imperfection_wave_a: int = 1
    imperfection_wave_b: int = 1
    imperfection_mode_shapes_json: str = "[]"
    runtime_solver: str = "stepwise"
    allow_unbalanced_free_free: bool = False
    buckling_shift_load_factor: float = 0.0
    buckling_min_load_factor: float = 0.0
    buckling_max_load_factor: float = 0.0
    buckling_repeated_tolerance: float = 1.0e-3
    buckling_allow_dense_fallback: bool = False
    recovery_history_mode: str = "full"
    recovery_threads: int = 0
    memory_limit_mb: float = 0.0
    capacity_buckling_mode_number: int = 1
    capacity_mesh_min_elements_per_half_wave: int = 4
    fracture_enabled: bool = False
    fracture_strain_threshold: float = 0.02
    fracture_residual_stiffness_fraction: float = 1.0e-6
    fracture_max_deleted_fraction: float = 0.25
    fracture_min_load_factor: float = 0.0
    collision_enabled: bool = False
    collision_include_static_load: bool = False
    collision_damage_enabled: bool = True
    collision_material_nonlinear_enabled: bool = False
    collision_nonlinear_kinematics: str = "von_karman"
    collision_beam_contact_enabled: bool = False
    collision_adaptive_mesh_enabled: bool = False
    collision_adaptive_fine_factor: float = 0.3
    collision_adaptive_fine_size_m: float = 0.0
    collision_adaptive_extent_m: float = 0.0
    collision_adaptive_growth_factor: float = 1.35
    collision_adaptive_zone_factor: float = 2.5
    detail_transition_style: str = "graded grid"
    custom_bc_segments_json: str = "[]"
    thickness_regions_json: str = "[]"
    collision_nonlinear_max_iterations: int = 20
    collision_nonlinear_tolerance: float = 1.0e-6
    collision_nonlinear_cutbacks: int = 8
    collision_plastic_damage_threshold: float = 0.01
    collision_damage_criterion: str = "rtcl"
    collision_mass_kg: float = 1000.0
    collision_radius_m: float = 0.25
    collision_start_x_m: float = 0.0
    collision_start_y_m: float = 0.0
    collision_start_z_m: float = 1.0
    collision_vector_x: float = 0.0
    collision_vector_y: float = 0.0
    collision_vector_z: float = -1.0
    collision_speed_mps: float = 5.0
    collision_time_mode: str = "auto"
    collision_auto_steps_per_radius: float = 20.0
    collision_auto_post_contact_radii: float = 6.0
    collision_bounce_back_time_s: float = 0.01
    collision_total_time_s: float = 0.05
    collision_dt_s: float = 0.0005
    collision_result_interval_s: float = 0.0
    collision_penalty_stiffness_n_per_m: float = 0.0
    collision_auto_precondition: bool = False
    collision_contact_damping: float = 0.0
    collision_max_iterations: int = 25
    collision_penetration_tolerance_m: float = 1.0e-8
    collision_force_tolerance_n: float = 1.0e-6
    collision_target_penetration_fraction: float = 0.01
    collision_max_event_substeps: int = 16
    collision_contact_surface: str = "midsurface"
    collision_damage_mode: str = "accumulated_damage"
    collision_damage_capacity_basis: str = "yield"
    collision_damage_user_capacity_pa: float = 0.0
    collision_damage_softening_start: float = 0.6
    collision_damage_delete_at: float = 1.0
    collision_damage_min_contact_area_m2: float = 1.0e-6
    collision_damage_max_deleted_fraction: float = 0.25
    collision_damage_neighbor_smoothing: bool = False
    # Append 0.1.3 integration fields so existing positional construction of
    # RuntimeFEMOptions retains its historical field order.
    follower_pressure: bool = False
    collision_penalty_scale: float = 1.0


@dataclass(frozen=True)
class RuntimeFEMRunResult:
    """Structured runtime FEM result used by text, viewers, and exports."""

    status: str
    summary: dict[str, Any]
    diagnostics: tuple[str, ...] = field(default_factory=tuple)
    buckling_factors: tuple[float, ...] = field(default_factory=tuple)
    stress_percentiles: tuple[tuple[str, float], ...] = field(default_factory=tuple)
    displacement_scale: float = 0.0
    visualization: dict[str, Any] = field(default_factory=dict)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _tk_var_float(variable: Any, default: float = 0.0) -> float:
    """Read a tk numeric variable defensively.

    ``DoubleVar.get()`` raises ``TclError`` when its entry widget is empty,
    before any float conversion can apply a default.
    """

    try:
        return _safe_float(variable.get(), default)
    except Exception:
        return float(default)


def _tk_var_int(variable: Any, default: int = 0) -> int:
    """Read a tk integer variable defensively (empty entries raise in get())."""

    try:
        return _safe_int(variable.get(), default)
    except Exception:
        return int(default)


RUNTIME_FEM_STATE_FORMAT = "anystructure-runtime-fem-state-v1"


def _jsonable_state_value(value: Any) -> Any:
    """Convert solver payload values (numpy included) to JSON-safe data."""

    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable_state_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable_state_value(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def runtime_fem_state_to_dict(
    options: RuntimeFEMOptions,
    result: RuntimeFEMRunResult | None = None,
    snapshot: RuntimeFEMLineSnapshot | None = None,
) -> dict[str, Any]:
    """Serialize FE-GUI settings and the solver result (mesh included) to plain data.

    The stored payload is plain JSON data: numpy arrays become nested lists and
    dictionary keys become strings.  All runtime-result consumers already
    normalise those (``int(...)``/``np.asarray`` on read), so a loaded state
    feeds the result viewer and the FEA-buckling handoff unchanged.
    """

    state: dict[str, Any] = {
        "format": RUNTIME_FEM_STATE_FORMAT,
        "saved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "options": {
            item.name: _jsonable_state_value(getattr(options, item.name))
            for item in dataclass_fields(RuntimeFEMOptions)
        },
    }
    if snapshot is not None:
        state["snapshot"] = {
            "line_name": str(snapshot.line_name),
            "domain": str(snapshot.domain),
            "is_cylinder": bool(snapshot.is_cylinder),
            "pressure_pa": _safe_float(snapshot.pressure_pa),
            "axial_force_n": _safe_float(snapshot.axial_force_n),
            "top_bottom_moment_nm": _safe_float(snapshot.top_bottom_moment_nm),
            "torsional_moment_nm": _safe_float(snapshot.torsional_moment_nm),
            "shear_force_n": _safe_float(snapshot.shear_force_n),
            "members_opposite_side": bool(getattr(snapshot, "members_opposite_side", False)),
        }
    if result is not None:
        state["result"] = {
            "status": str(result.status),
            "summary": _jsonable_state_value(result.summary),
            "diagnostics": [str(item) for item in result.diagnostics],
            "buckling_factors": [_safe_float(item) for item in result.buckling_factors],
            "stress_percentiles": [[str(name), _safe_float(value)] for name, value in result.stress_percentiles],
            "displacement_scale": _safe_float(result.displacement_scale),
            "visualization": _jsonable_state_value(result.visualization),
        }
    return state


def save_runtime_fem_state(
    path: Any,
    options: RuntimeFEMOptions,
    result: RuntimeFEMRunResult | None = None,
    snapshot: RuntimeFEMLineSnapshot | None = None,
) -> None:
    """Write settings and (optionally) results including the mesh to ``path``.

    ``*.gz`` paths are gzip-compressed; anything else is plain JSON.
    """

    text = json.dumps(runtime_fem_state_to_dict(options, result=result, snapshot=snapshot))
    path_text = str(path)
    if path_text.lower().endswith(".gz"):
        with gzip.open(path_text, "wt", encoding="utf-8") as handle:
            handle.write(text)
    else:
        with open(path_text, "w", encoding="utf-8") as handle:
            handle.write(text)


def runtime_fem_options_from_dict(data: Any) -> RuntimeFEMOptions:
    """Rebuild options from stored data; unknown keys are ignored and missing
    keys keep their defaults so older/newer files stay loadable."""

    values: dict[str, Any] = {}
    source = data if isinstance(data, dict) else {}
    for item in dataclass_fields(RuntimeFEMOptions):
        if item.name not in source:
            continue
        raw = source[item.name]
        default = item.default
        if isinstance(default, bool):
            values[item.name] = bool(raw)
        elif isinstance(default, int):
            values[item.name] = _safe_int(raw, default)
        elif isinstance(default, float):
            values[item.name] = _safe_float(raw, default)
        else:
            values[item.name] = str(raw)
    return RuntimeFEMOptions(**values)


def runtime_fem_result_from_dict(data: Any) -> RuntimeFEMRunResult | None:
    if not isinstance(data, dict):
        return None
    percentiles: list[tuple[str, float]] = []
    for item in data.get("stress_percentiles", ()) or ():
        try:
            percentiles.append((str(item[0]), float(item[1])))
        except (TypeError, ValueError, IndexError):
            continue
    return RuntimeFEMRunResult(
        status=str(data.get("status", "")),
        summary=dict(data.get("summary", {}) or {}),
        diagnostics=tuple(str(item) for item in data.get("diagnostics", ()) or ()),
        buckling_factors=tuple(_safe_float(item) for item in data.get("buckling_factors", ()) or ()),
        stress_percentiles=tuple(percentiles),
        displacement_scale=_safe_float(data.get("displacement_scale"), 0.0),
        visualization=data.get("visualization", {}) or {},
    )


def load_runtime_fem_state(path: Any) -> dict[str, Any]:
    """Read a saved runtime FEM state: options, optional result, snapshot meta."""

    path_text = str(path)
    if path_text.lower().endswith(".gz"):
        with gzip.open(path_text, "rt", encoding="utf-8") as handle:
            state = json.load(handle)
    else:
        with open(path_text, "r", encoding="utf-8") as handle:
            state = json.load(handle)
    if not isinstance(state, dict) or state.get("format") != RUNTIME_FEM_STATE_FORMAT:
        raise ValueError(
            "not an ANYstructure runtime FEM state file "
            f"(expected format tag {RUNTIME_FEM_STATE_FORMAT!r})"
        )
    return {
        "format": str(state.get("format")),
        "saved_utc": str(state.get("saved_utc", "")),
        "options": runtime_fem_options_from_dict(state.get("options", {})),
        "result": runtime_fem_result_from_dict(state.get("result")),
        "snapshot": state.get("snapshot", {}) or {},
    }


_FE_KERNEL_WARMUP_LOCK = threading.RLock()
_FE_KERNEL_WARMUP_STATE: dict[str, Any] = {
    "status": "not_started",
    "shell_orders": (),
    "total_seconds": 0.0,
    "message": "",
    "nonlinear_impact": False,
}


def _warmup_disabled() -> bool:
    raw = os.environ.get("ANYSTRUCTURE_FE_SOLVER_WARMUP", "")
    return str(raw).strip().lower() in {"0", "false", "no", "off", "disable", "disabled"}


def _summarize_kernel_warmup_report(
        report: dict[str, Any],
        shell_orders: tuple[str, ...],
        *,
        include_nonlinear_impact: bool = False,
) -> dict[str, Any]:
    warmed = report.get("shell_orders") if isinstance(report, dict) else {}
    warmed = warmed if isinstance(warmed, dict) else {}
    max_difference = 0.0
    for item in warmed.values():
        if isinstance(item, dict):
            max_difference = max(max_difference, _safe_float(item.get("matrix_difference_norm"), 0.0))
    nonlinear = report.get("nonlinear_impact") if isinstance(report, dict) else None
    nonlinear = nonlinear if isinstance(nonlinear, dict) else None
    return {
        "status": str(report.get("status", "completed") if isinstance(report, dict) else "completed"),
        "shell_orders": tuple(str(key) for key in warmed.keys()) or shell_orders,
        "total_seconds": _safe_float(report.get("total_seconds"), 0.0) if isinstance(report, dict) else 0.0,
        "jit_enabled": bool((report.get("jit") or {}).get("enabled")) if isinstance(report, dict) else False,
        "parallel_threads": (report.get("jit") or {}).get("num_threads") if isinstance(report, dict) else None,
        "max_matrix_difference_norm": float(max_difference),
        "message": "",
        "nonlinear_impact": bool(nonlinear is not None or include_nonlinear_impact),
        "nonlinear_impact_status": str((nonlinear or {}).get("status", "")),
        "nonlinear_impact_seconds": _safe_float((nonlinear or {}).get("seconds"), 0.0),
    }


def fe_solver_kernel_warmup_status() -> dict[str, Any]:
    """Return the process-wide FE kernel warmup state for runtime diagnostics."""

    with _FE_KERNEL_WARMUP_LOCK:
        return dict(_FE_KERNEL_WARMUP_STATE)


def start_fe_solver_kernel_warmup(
        shell_orders: tuple[str, ...] = ("S4", "Q8", "Q8R"),
        *,
        background: bool = True,
        status_callback=None,
        include_nonlinear_impact: bool = False,
) -> dict[str, Any]:
    """Start optional FE backend kernel warmup once per process."""

    requested = tuple(str(order).upper() for order in shell_orders)
    if _warmup_disabled():
        with _FE_KERNEL_WARMUP_LOCK:
            _FE_KERNEL_WARMUP_STATE.update(
                {
                    "status": "disabled",
                    "shell_orders": requested,
                    "total_seconds": 0.0,
                    "message": "Disabled by ANYSTRUCTURE_FE_SOLVER_WARMUP.",
                }
            )
            return dict(_FE_KERNEL_WARMUP_STATE)

    with _FE_KERNEL_WARMUP_LOCK:
        status = str(_FE_KERNEL_WARMUP_STATE.get("status", "not_started"))
        requested_set = set(requested)
        warmed_set = set(str(order) for order in _FE_KERNEL_WARMUP_STATE.get("shell_orders", ()) or ())
        nonlinear_done = bool(_FE_KERNEL_WARMUP_STATE.get("nonlinear_impact", False))
        request_satisfied = requested_set.issubset(warmed_set) and (not include_nonlinear_impact or nonlinear_done)
        if status == "running":
            return dict(_FE_KERNEL_WARMUP_STATE)
        if status in {"completed", "failed", "backend_unavailable", "disabled"} and request_satisfied:
            return dict(_FE_KERNEL_WARMUP_STATE)
        _FE_KERNEL_WARMUP_STATE.update(
            {
                "status": "running",
                "shell_orders": requested,
                "total_seconds": 0.0,
                "message": "FE solver kernel warmup is running.",
                "nonlinear_impact": bool(include_nonlinear_impact),
                "started_at": time.time(),
            }
        )

    def worker() -> None:
        start = time.perf_counter()
        try:
            if status_callback is not None:
                status_callback("Warming FE solver shell kernels" + (
                    " and nonlinear impact kernels" if include_nonlinear_impact else "") + "...")
            report = fe_solver.warm_fe_solver_kernels(requested, include_nonlinear_impact=include_nonlinear_impact)
            summary = _summarize_kernel_warmup_report(report, requested,
                                                      include_nonlinear_impact=include_nonlinear_impact)
            summary["total_seconds"] = summary["total_seconds"] or float(time.perf_counter() - start)
            with _FE_KERNEL_WARMUP_LOCK:
                _FE_KERNEL_WARMUP_STATE.update(summary)
                _FE_KERNEL_WARMUP_STATE["completed_at"] = time.time()
            if status_callback is not None:
                status_callback("FE solver kernel warmup " + str(summary["status"]).replace("_", " ") + ".")
        except Exception as exc:
            with _FE_KERNEL_WARMUP_LOCK:
                _FE_KERNEL_WARMUP_STATE.update(
                    {
                        "status": "failed",
                        "shell_orders": requested,
                        "total_seconds": float(time.perf_counter() - start),
                        "message": str(exc),
                        "completed_at": time.time(),
                    }
                )
            if status_callback is not None:
                status_callback("FE solver kernel warmup failed: " + str(exc))

    if background:
        threading.Thread(target=worker, name="ANYstructureFEKernelWarmup", daemon=True).start()
    else:
        worker()
    return fe_solver_kernel_warmup_status()


def _warmup_diagnostics() -> list[str]:
    state = fe_solver_kernel_warmup_status()
    status = str(state.get("status", "not_started"))
    if status == "not_started":
        return ["FE solver kernel warmup: not started."]
    orders = ", ".join(str(order) for order in state.get("shell_orders", ()) or ())
    seconds = _safe_float(state.get("total_seconds"), 0.0)
    text = "FE solver kernel warmup: " + status.replace("_", " ")
    if orders:
        text += " for " + orders
    if seconds > 0.0:
        text += " in " + str(round(seconds, 3)) + " s"
    if state.get("nonlinear_impact"):
        nl_seconds = _safe_float(state.get("nonlinear_impact_seconds"), 0.0)
        text += "; nonlinear impact warmed"
        if nl_seconds > 0.0:
            text += " in " + str(round(nl_seconds, 3)) + " s"
    if status == "completed":
        text += "; max matrix difference " + str(round(_safe_float(state.get("max_matrix_difference_norm")), 12))
        if state.get("jit_enabled") is not None:
            text += "; JIT " + ("enabled" if state.get("jit_enabled") else "disabled")
        if state.get("parallel_threads") is not None:
            text += "; threads " + str(state.get("parallel_threads"))
    if state.get("message") and status not in {"running", "completed"}:
        text += " (" + str(state.get("message")) + ")"
    return [text + "."]


def _nearest_nonlinear_layer_count(value: Any) -> int:
    requested = max(_safe_int(value, 5), 3)
    supported = (3, 5, 7, 9, 11)
    return min(supported, key=lambda item: abs(item - requested))


def _read_attr_or_call(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if obj is None:
            break
        value = getattr(obj, name, None)
        if value is None:
            continue
        try:
            return value() if callable(value) else value
        except Exception:
            continue
    return default


def _read_tk_var_or_value(obj: Any, name: str, default: Any = None) -> Any:
    value = getattr(obj, name, default)
    try:
        return value.get() if hasattr(value, "get") else value
    except Exception:
        return default


def _dict_value(data: Any, key: str, default: Any = None) -> Any:
    if not isinstance(data, dict) or key not in data:
        return default
    value = data.get(key)
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _mm_or_m_to_m(value: Any, default: float = 0.0) -> float:
    number = _safe_float(value, default)
    if number <= 0.0:
        return default
    return number / 1000.0 if number > 1.0 else number


def _length_input_to_m(value: Any, default: float = 0.0) -> float:
    """Return a structural length in metres from saved-object or GUI-style values."""

    number = _safe_float(value, default)
    if number <= 0.0:
        return default
    return number / 1000.0 if number > 100.0 else number


def _flat_lg_from_objects(plate: Any, stiffener: Any, girder: Any, spacing: float, fallback: float | None = None) -> float:
    for obj in (girder, stiffener, plate):
        if obj is None:
            continue
        value = _read_attr_or_call(obj, "get_girder_lg", "get_lg", "get_LG", "girder_lg", "lg", "LG", default=None)
        lg = _length_input_to_m(value, 0.0)
        if lg > 1.0e-9:
            return lg
    if fallback is not None:
        return fallback
    return max(4.0 * spacing, 0.8)


def _flat_lp_from_structure(all_obj: Any, span: float, spacing: float, has_girder: bool) -> float:
    for obj in (all_obj,):
        if obj is None:
            continue
        value = _read_attr_or_call(obj, "panel_length_Lp", "_panel_length_Lp", "panel_length", "lp", "Lp", default=None)
        lp = _length_input_to_m(value, 0.0)
        if lp > 1.0e-9:
            return lp
    if has_girder:
        return max(2.0 * span, 2.0 * spacing, 0.8)
    return max(span, spacing, 0.8)


def _member_section(member: Any) -> dict[str, float] | None:
    if member is None:
        return None
    section = _read_attr_or_call(member, "cross_section", "section", default=None)
    if isinstance(section, dict):
        return dict(section)

    stiffener_type = str(_read_attr_or_call(member, "stiffener_type", "stf_type", default="")).upper()
    height = _mm_or_m_to_m(_read_attr_or_call(member, "hw", "height", "web_height", default=None), 0.0)
    thickness = _mm_or_m_to_m(_read_attr_or_call(member, "tw", "thickness", "web_thickness", default=None), 0.0)
    flange_width = _mm_or_m_to_m(_read_attr_or_call(member, "b", "bf", "flange_width", default=None), 0.0)
    flange_thickness = _mm_or_m_to_m(_read_attr_or_call(member, "tf", "flange_thickness", default=None), 0.0)
    if stiffener_type in {"T", "TEE",
                          "T-BAR"} and height > 0.0 and thickness > 0.0 and flange_width > 0.0 and flange_thickness > 0.0:
        web_area = height * thickness
        flange_area = flange_width * flange_thickness
        area = web_area + flange_area
        web_y = 0.5 * height
        flange_y = height + 0.5 * flange_thickness
        centroid = (web_area * web_y + flange_area * flange_y) / area
        iy = thickness * height ** 3 / 12.0 + web_area * (web_y - centroid) ** 2
        iy += flange_width * flange_thickness ** 3 / 12.0 + flange_area * (flange_y - centroid) ** 2
        iz = height * thickness ** 3 / 12.0 + flange_thickness * flange_width ** 3 / 12.0
        return {
            "area": area,
            "Iy": max(iy, 1.0e-12),
            "Iz": max(iz, 1.0e-12),
            "J": max(iy + iz, 1.0e-12),
            "shear_factor_y": 5.0 / 6.0,
            "shear_factor_z": 5.0 / 6.0,
            "web_height": height,
            "web_thickness": thickness,
            "flange_width": flange_width,
            "flange_thickness": flange_thickness,
            "label": "T" + str(round(height * 1000.0)) + "x" + str(round(thickness * 1000.0))
                     + "+" + str(round(flange_width * 1000.0)) + "x" + str(round(flange_thickness * 1000.0)),
        }

    if stiffener_type not in {"FB", "FLAT", "FLATBAR", "FLAT BAR"} and not (height > 0.0 and thickness > 0.0):
        return None
    if height <= 0.0 or thickness <= 0.0:
        return None

    area = height * thickness
    iy = thickness * height ** 3 / 12.0
    iz = height * thickness ** 3 / 12.0
    return {
        "area": area,
        "Iy": max(iy, 1.0e-12),
        "Iz": max(iz, 1.0e-12),
        "J": max(iy + iz, 1.0e-12),
        "shear_factor_y": 5.0 / 6.0,
        "shear_factor_z": 5.0 / 6.0,
        "web_height": height,
        "web_thickness": thickness,
        "flange_width": 0.0,
        "flange_thickness": 0.0,
        "label": "FB" + str(round(height * 1000.0)) + "x" + str(round(thickness * 1000.0)),
    }


def _plate_edge_supports_from_line_properties(plate: Any) -> tuple[str, str, str, str]:
    raw = _read_attr_or_call(plate, "get_puls_up_boundary", "_puls_up_boundary", "puls_up_boundary", default=None)
    if isinstance(raw, (list, tuple)) and raw:
        raw = raw[0]
    text = str(raw or "").strip().upper().replace(" ", "")
    if len(text) < 4 or any(letter not in {"S", "C"} for letter in text[:4]):
        return ("simply supported", "simply supported", "simply supported", "simply supported")
    return tuple("fixed" if letter == "C" else "simply supported" for letter in text[:4])  # type: ignore[return-value]


def _structure_pressure_pa(bundle: Any, cylinder_obj: Any | None) -> float:
    if cylinder_obj is not None:
        pressure = _safe_float(_read_attr_or_call(cylinder_obj, "psd", "_psd", default=0.0), 0.0)
        return abs(pressure)
    all_obj = bundle[0] if bundle and len(bundle) > 0 else None
    pressure_mpa = _safe_float(_read_attr_or_call(all_obj, "lat_press", "_lat_press", default=0.0), 0.0)
    return abs(pressure_mpa) * 1.0e6


def _cylinder_pressure_pa_from_app(app: Any) -> float:
    pressure_n_per_mm2 = _safe_float(_read_tk_var_or_value(app, "_new_shell_psd", None), 0.0)
    return abs(pressure_n_per_mm2) * 1.0e6


def _cylinder_force_defaults_from_properties(cylinder_obj: Any | None) -> tuple[float, float, float, float]:
    if cylinder_obj is None:
        return (0.0, 0.0, 0.0, 0.0)
    main_properties: dict[str, Any] = {}
    try:
        main_properties = cylinder_obj.get_main_properties()
    except Exception:
        try:
            main_properties = (cylinder_obj.get_all_properties() or {}).get("Main class", {})
        except Exception:
            main_properties = {}
    axial_kn = _safe_float(
        _dict_value(main_properties, "cone Nsd", _read_attr_or_call(cylinder_obj, "_cone_Nsd", default=0.0)),
        0.0,
    )
    moment_knm = _safe_float(
        _dict_value(main_properties, "cone M1sd", _read_attr_or_call(cylinder_obj, "_cone_M1sd", default=0.0)),
        0.0,
    )
    return (axial_kn * 1000.0, moment_knm * 1000.0, 0.0, 0.0)


def _cylinder_force_defaults_from_app(app: Any) -> tuple[float, float, float, float]:
    axial = _safe_float(_read_tk_var_or_value(app, "_new_shell_Nsd", None), 0.0) * 1000.0
    moment = _safe_float(_read_tk_var_or_value(app, "_new_shell_Msd", None), 0.0) * 1000.0
    return (axial, moment, 0.0, 0.0)


def _runtime_line_load_defaults(app: Any, cylinder_obj: Any | None) -> tuple[float, float, float, float]:
    if cylinder_obj is None:
        return (0.0, 0.0, 0.0, 0.0)
    property_axial, property_moment, property_torsional, property_shear = _cylinder_force_defaults_from_properties(cylinder_obj)
    app_axial, app_moment, app_torsional, app_shear = _cylinder_force_defaults_from_app(app)
    return (
        app_axial if abs(app_axial) > 0.0 else property_axial,
        app_moment if abs(app_moment) > 0.0 else property_moment,
        app_torsional if abs(app_torsional) > 0.0 else property_torsional,
        app_shear if abs(app_shear) > 0.0 else property_shear,
    )


def active_line_snapshot(app: Any) -> RuntimeFEMLineSnapshot:
    """Collect current active-line data for the experimental runtime FEM mode."""

    active_line = getattr(app, "_active_line", "")
    if not active_line:
        raise ValueError("No active line selected.")
    line_dict = getattr(app, "_line_dict", {})
    line_to_struc = getattr(app, "_line_to_struc", {})
    if active_line not in line_dict:
        raise ValueError("The active line is not available in the geometry model.")
    if active_line not in line_to_struc:
        raise ValueError("The active line has no assigned structure properties.")

    diagnostics = []
    pressure = 0.0
    try:
        pressure_data = app.get_highest_pressure(active_line)
        pressure = _safe_float(pressure_data.get("normal", 0.0))
    except Exception as error:
        diagnostics.append("Pressure unavailable: " + str(error))

    bundle = line_to_struc[active_line]
    cylinder_obj = None
    try:
        cylinder_obj = bundle[5]
    except Exception:
        cylinder_obj = None

    domain = ""
    try:
        if cylinder_obj is not None:
            domain = "cylinder"
        elif bundle[0] is not None:
            domain = str(bundle[0].Plate.get_structure_type())
    except Exception:
        domain = ""

    structure_pressure = _structure_pressure_pa(bundle, cylinder_obj)
    app_cylinder_pressure = _cylinder_pressure_pa_from_app(app) if cylinder_obj is not None else 0.0
    if cylinder_obj is not None and app_cylinder_pressure > 0.0:
        pressure = app_cylinder_pressure
    elif cylinder_obj is not None and structure_pressure > 0.0:
        pressure = structure_pressure
    elif abs(pressure) <= 1.0e-12 and structure_pressure > 0.0:
        pressure = structure_pressure
    axial_force_n, top_bottom_moment_nm, torsional_moment_nm, shear_force_n = _runtime_line_load_defaults(app, cylinder_obj)

    # The main-application "Opposite side" checkbox flips the member side in
    # the 3D preview and CAD export; the FE geometry must follow it too.
    members_opposite_side = False
    try:
        members_opposite_side = bool(app._new_prop_3d_opposite_side.get())
    except Exception:
        members_opposite_side = False

    return RuntimeFEMLineSnapshot(
        line_name=active_line,
        line_points=line_dict[active_line],
        structure_bundle=bundle,
        pressure_pa=pressure,
        axial_force_n=axial_force_n,
        top_bottom_moment_nm=top_bottom_moment_nm,
        torsional_moment_nm=torsional_moment_nm,
        shear_force_n=shear_force_n,
        domain=domain,
        is_cylinder=cylinder_obj is not None,
        members_opposite_side=members_opposite_side,
        diagnostics=tuple(diagnostics),
    )


def _flat_geometry_summary(snapshot: RuntimeFEMLineSnapshot, ignore_girder_length: bool = False) -> dict[str, Any]:
    bundle = snapshot.structure_bundle
    all_obj = bundle[0] if bundle and len(bundle) > 0 else None
    plate = getattr(all_obj, "Plate", None)
    stiffener = getattr(all_obj, "Stiffener", None)
    girder = getattr(all_obj, "Girder", None)
    span = _safe_float(_read_attr_or_call(plate, "get_span", "span"), 1.0)
    spacing = _safe_float(_read_attr_or_call(plate, "get_s", default=None), 1.0)
    has_girder = girder is not None
    length = _flat_lp_from_structure(all_obj, span, spacing, has_girder)
    if has_girder:
        width = _flat_lg_from_objects(plate, stiffener, girder, spacing)
    elif ignore_girder_length:
        width = spacing
    else:
        # A stiffened panel without girders still spans the girder length LG in
        # the main-application 3D model, so mirror that here to get the full
        # stiffener count. Falls back to one bay when LG is undefined.
        width = _flat_lg_from_objects(plate, stiffener, girder, spacing, fallback=spacing)
    girder_spacing = span if has_girder else _safe_float(
        _read_attr_or_call(girder, "get_s", "spacing", "s", default=None), 0.0)
    return {
        "geometry": "flat panel",
        "length_m": length,
        "width_m": width,
        "thickness_m": _safe_float(_read_attr_or_call(plate, "get_pl_thk", default=None), 0.0),
        "has_stiffener": stiffener is not None,
        "has_girder": has_girder,
        "stiffener_spacing_m": spacing,
        "girder_spacing_m": girder_spacing,
        "stiffener_span_m": span,
        "girder_length_m": width if has_girder else 0.0,
        "panel_length_m": length,
        "stiffener_section": _member_section(stiffener),
        "girder_section": _member_section(girder),
        "plate_edge_supports": _plate_edge_supports_from_line_properties(plate),
        "members_opposite_side": bool(getattr(snapshot, "members_opposite_side", False)),
    }


def _cylinder_geometry_summary(snapshot: RuntimeFEMLineSnapshot) -> dict[str, Any]:
    bundle = snapshot.structure_bundle
    cyl_obj = bundle[5] if bundle and len(bundle) > 5 else None
    shell = getattr(cyl_obj, "ShellObj", None)
    stiffener = getattr(cyl_obj, "LongStfObj", None)
    girder = getattr(cyl_obj, "RingFrameObj", None)
    cone_r1 = _safe_float(_read_attr_or_call(shell, "cone_r1", default=None), 0.0)
    cone_r2 = _safe_float(_read_attr_or_call(shell, "cone_r2", default=None), 0.0)
    if hasattr(cyl_obj, "geometry"):
        is_cone = getattr(cyl_obj, "geometry") == 9
    else:
        is_cone = bool(cone_r1 > 0.0 and cone_r2 > 0.0 and abs(cone_r1 - cone_r2) > 1e-6)

    # Standard cylinders might be imported as cones (geometry=9) but have constant diameter
    if is_cone and abs(cone_r1 - cone_r2) < 1e-6:
        is_cone = False

    radius = _safe_float(_read_attr_or_call(shell, "radius", default=None), 0.0)
    if radius <= 1e-6:
        radius = cone_r1 if cone_r1 > 1e-6 else 1.0

    return {
        "geometry": "cylinder",
        "radius_m": radius,
        "length_m": _safe_float(_read_attr_or_call(shell, "length_of_shell", "tot_cyl_length", default=None), 1.0),
        "thickness_m": _safe_float(_read_attr_or_call(shell, "thk", default=None), 0.0),
        "is_cone": is_cone,
        "cone_r1_m": cone_r1,
        "cone_r2_m": cone_r2,
        "cone_length_m": _safe_float(_read_attr_or_call(shell, "cone_length", default=None), 0.0),
        "has_stiffener": stiffener is not None,
        "has_girder": girder is not None,
        "stiffener_spacing_m": _safe_float(_read_attr_or_call(stiffener, "get_s", "spacing", "s", default=None), 0.0),
        "ring_spacing_m": _safe_float(
            _read_attr_or_call(shell, "_dist_between_rings", "dist_between_rings", default=None), 0.0),
        "girder_spacing_m": _safe_float(_read_attr_or_call(cyl_obj, "length_between_girders", default=None), 0.0),
        "stiffener_section": _member_section(stiffener),
        "girder_section": _member_section(girder),
        "members_opposite_side": bool(getattr(snapshot, "members_opposite_side", False)),
    }


def runtime_geometry_summary(
    snapshot: RuntimeFEMLineSnapshot,
    options: RuntimeFEMOptions | None = None,
) -> dict[str, Any]:
    """Return compact geometry metadata for plotting and future solver handoff."""

    if snapshot.is_cylinder:
        return _cylinder_geometry_summary(snapshot)
    ignore_girder_length = bool(getattr(options, "ignore_girder_length", False)) if options is not None else False
    return _flat_geometry_summary(snapshot, ignore_girder_length=ignore_girder_length)


def _popup_geometry_summary(popup: Any) -> dict[str, Any]:
    """Geometry summary for popup drawing code, honouring the popup options.

    Test harnesses drive popup methods with plain stand-in objects, so missing
    or partially built option controls fall back to default options.
    """

    options = None
    options_getter = getattr(popup, "_options", None)
    if callable(options_getter):
        try:
            options = options_getter()
        except Exception:
            options = None
    return runtime_geometry_summary(popup.snapshot, options)


def _runtime_custom_load_entries(raw_json: str) -> list[dict[str, Any]]:
    try:
        raw_entries = json.loads(raw_json or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(raw_entries, list):
        return []
    return [entry for entry in raw_entries if isinstance(entry, dict)]


def _runtime_custom_pressure_patches(options: RuntimeFEMOptions) -> list[dict[str, float]]:
    entries = _runtime_custom_load_entries(options.custom_loads_json)
    raw_patches: list[Any] = []
    if entries:
        for entry in entries:
            if str(entry.get("type", "")).lower() not in {"pressure", "panel_pressure"}:
                continue
            patches = entry.get("patches", [])
            if isinstance(patches, list):
                raw_patches.extend(patches)
    else:
        try:
            raw_loaded = json.loads(options.custom_pressure_patches_json or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_loaded = []
        if isinstance(raw_loaded, list):
            raw_patches = raw_loaded

    patches: list[dict[str, float]] = []
    for raw_patch in raw_patches:
        if not isinstance(raw_patch, dict):
            continue
        patch = {
            "min_a": _safe_float(raw_patch.get("min_a")),
            "max_a": _safe_float(raw_patch.get("max_a")),
            "min_b": _safe_float(raw_patch.get("min_b")),
            "max_b": _safe_float(raw_patch.get("max_b")),
        }
        if patch["max_a"] > patch["min_a"] and patch["max_b"] > patch["min_b"]:
            patches.append(patch)
    return patches


def _runtime_local_refinement_patches(options: RuntimeFEMOptions) -> list[dict[str, float | str]]:
    try:
        raw_patches = json.loads(options.local_refinement_patches_json or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        raw_patches = []
    if not isinstance(raw_patches, list):
        return []

    patches: list[dict[str, float | str]] = []
    for raw_patch in raw_patches:
        if not isinstance(raw_patch, dict):
            continue
        patch: dict[str, float | str] = {
            "min_a": _safe_float(raw_patch.get("min_a")),
            "max_a": _safe_float(raw_patch.get("max_a")),
            "min_b": _safe_float(raw_patch.get("min_b")),
            "max_b": _safe_float(raw_patch.get("max_b")),
        }
        axis_origin = str(raw_patch.get("axis_a_origin", "") or "")
        if axis_origin:
            patch["axis_a_origin"] = axis_origin
        if float(patch["max_a"]) > float(patch["min_a"]) and float(patch["max_b"]) > float(patch["min_b"]):
            patches.append(patch)
    return patches


def _runtime_custom_edges(options: RuntimeFEMOptions) -> list[dict[str, float | str]]:
    entries = _runtime_custom_load_entries(options.custom_loads_json)
    raw_edges: list[Any] = []
    if entries:
        for entry in entries:
            if str(entry.get("type", "")).lower() not in {"edge", "edge_load"}:
                continue
            edges = entry.get("edges", [])
            if isinstance(edges, list):
                raw_edges.extend(edges)
    else:
        try:
            raw_loaded = json.loads(options.custom_edge_segments_json or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_loaded = []
        if isinstance(raw_loaded, list):
            raw_edges = raw_loaded

    custom_edges: list[dict[str, float | str]] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            continue
        start = _safe_float(raw_edge.get("start_coordinate"))
        end = _safe_float(raw_edge.get("end_coordinate"))
        if abs(end - start) <= 1.0e-12:
            continue
        custom_edges.append({
            "varying_axis": str(raw_edge.get("varying_axis", "a")),
            "fixed_coordinate": _safe_float(raw_edge.get("fixed_coordinate")),
            "start_coordinate": min(start, end),
            "end_coordinate": max(start, end),
        })
    return custom_edges


def _solver_config_from_options(options: RuntimeFEMOptions):
    """Build the LightweightFEMConfig from runtime options (shared by run and preview)."""
    _require_supported_anysolver()
    pressure_side = _normalise_pressure_side(options.pressure_direction)
    return fe_solver.LightweightFEMConfig(
        mesh_fidelity=options.mesh_fidelity,
        pressure_pa=options.pressure_pa,
        load_scale=options.load_scale,
        include_stiffeners=options.include_stiffeners,
        include_girders=options.include_girders,
        include_end_lids=options.include_end_lids,
        num_buckling_modes=options.num_buckling_modes,
        mesh_size_m=options.mesh_size_m,
        top_bottom_moment_nm=options.top_bottom_moment_nm,
        torsional_moment_nm=options.torsional_moment_nm,
        shear_force_n=options.shear_force_n,
        acceleration_x_m_s2=options.acceleration_x_m_s2,
        acceleration_y_m_s2=options.acceleration_y_m_s2,
        acceleration_z_m_s2=options.acceleration_z_m_s2,
        added_mass_kg=options.added_mass_kg,
        added_mass_location=options.added_mass_location,
        boundary_condition=options.boundary_condition,
        boundary_constraint_json=str(options.boundary_constraint_json),
        boundary_auto_supports=bool(options.boundary_auto_supports),
        symmetry_mode=options.symmetry_mode,
        shell_element_order=options.shell_element_order,
        beam_element_order=options.beam_element_order,
        member_model=options.member_model,
        analysis_type=options.analysis_type,
        buckling_analysis_type=options.buckling_analysis_type,
        pressure_direction=pressure_side,
        follower_pressure=bool(options.follower_pressure),
        axial_force_n=options.axial_force_n,
        enforced_displacement_x_m=options.enforced_displacement_x_m,
        enforced_displacement_y_m=options.enforced_displacement_y_m,
        enforced_displacement_z_m=options.enforced_displacement_z_m,
        stiffener_eccentricity_m=options.stiffener_eccentricity_m,
        girder_eccentricity_m=options.girder_eccentricity_m,
        member_orientation=options.member_orientation,
        solver_type=options.solver_type,
        stress_percentile=options.stress_percentile,
        elastic_modulus_pa=options.elastic_modulus_pa,
        poisson_ratio=options.poisson_ratio,
        yield_stress_pa=options.yield_stress_pa,
        material_model=options.material_model,
        steel_grade=options.steel_grade,
        steel_thickness_class=options.steel_thickness_class,
        nonlinear_max_load_factor=options.nonlinear_max_load_factor,
        nonlinear_steps=options.nonlinear_steps,
        nonlinear_max_iterations=options.nonlinear_max_iterations,
        nonlinear_tolerance=options.nonlinear_tolerance,
        nonlinear_layers=options.nonlinear_layers,
        nonlinear_solution_control=options.nonlinear_solution_control,
        nonlinear_convergence_profile=options.nonlinear_convergence_profile,
        nonlinear_assembly_threads=options.nonlinear_assembly_threads,
        nonlinear_static_kinematics=_normalise_kinematics(options.nonlinear_static_kinematics),
        post_buckling_enabled=bool(options.post_buckling_enabled),
        post_buckling_stop_load_fraction=float(options.post_buckling_stop_load_fraction),
        post_buckling_max_displacement_m=float(options.post_buckling_max_displacement_m),
        beam_consistent_mass_enabled=bool(options.beam_consistent_mass_enabled),
        custom_loads_add_to_imported=options.custom_loads_add_to_imported,
        custom_use_nullspace_projection=options.custom_use_nullspace_projection,
        custom_pressure_pa=options.custom_pressure_pa,
        custom_load_bc_enabled=options.custom_load_bc_enabled,
        plate_edge_x0_support=options.plate_edge_x0_support,
        plate_edge_x1_support=options.plate_edge_x1_support,
        plate_edge_y0_support=options.plate_edge_y0_support,
        plate_edge_y1_support=options.plate_edge_y1_support,
        cylinder_lower_support=options.cylinder_lower_support,
        cylinder_upper_support=options.cylinder_upper_support,
        plate_edge_x0_load_n_per_m=options.plate_edge_x0_load_n_per_m,
        plate_edge_x1_load_n_per_m=options.plate_edge_x1_load_n_per_m,
        plate_edge_y0_load_n_per_m=options.plate_edge_y0_load_n_per_m,
        plate_edge_y1_load_n_per_m=options.plate_edge_y1_load_n_per_m,
        cylinder_lower_edge_load_n_per_m=options.cylinder_lower_edge_load_n_per_m,
        cylinder_upper_edge_load_n_per_m=options.cylinder_upper_edge_load_n_per_m,
        edge_load_components_json=str(options.edge_load_components_json),
        custom_loads_json=options.custom_loads_json,
        custom_pressure_patches_json=options.custom_pressure_patches_json,
        custom_edge_segments_json=options.custom_edge_segments_json,
        custom_selected_edge_load_n_per_m=options.custom_selected_edge_load_n_per_m,
        custom_selected_edge_load_components_json=str(options.custom_selected_edge_load_components_json),
        local_refinement_enabled=bool(options.local_refinement_enabled),
        local_refinement_patches_json=str(options.local_refinement_patches_json),
        local_refinement_fine_factor=float(options.local_refinement_fine_factor),
        local_refinement_fine_size_m=float(options.local_refinement_fine_size_m),
        local_refinement_extent_m=float(options.local_refinement_extent_m),
        local_refinement_zone_factor=float(options.local_refinement_zone_factor),
        local_refinement_growth_factor=float(options.local_refinement_growth_factor),
        point_refinement_enabled=bool(options.point_refinement_enabled),
        point_refinement_x_m=float(options.point_refinement_x_m),
        point_refinement_y_m=float(options.point_refinement_y_m),
        point_refinement_fine_factor=float(options.point_refinement_fine_factor),
        point_refinement_fine_size_m=float(options.point_refinement_fine_size_m),
        point_refinement_extent_m=float(options.point_refinement_extent_m),
        point_refinement_growth_factor=float(options.point_refinement_growth_factor),
        custom_time_domain_enabled=options.custom_time_domain_enabled,
        custom_time_domain_duration_s=options.custom_time_domain_duration_s,
        custom_time_domain_total_time_s=options.custom_time_domain_total_time_s,
        custom_time_domain_dt_s=options.custom_time_domain_dt_s,
        custom_time_domain_result_interval_s=options.custom_time_domain_result_interval_s,
        custom_time_domain_include_static_load=options.custom_time_domain_include_static_load,
        imperfection_enabled=options.imperfection_enabled,
        imperfection_shape=options.imperfection_shape,
        imperfection_amplitude_m=options.imperfection_amplitude_m,
        imperfection_wave_a=options.imperfection_wave_a,
        imperfection_wave_b=options.imperfection_wave_b,
        imperfection_mode_shapes_json=options.imperfection_mode_shapes_json,
        runtime_solver=options.runtime_solver,
        allow_unbalanced_free_free=options.allow_unbalanced_free_free,
        buckling_shift_load_factor=options.buckling_shift_load_factor,
        buckling_min_load_factor=options.buckling_min_load_factor,
        buckling_max_load_factor=options.buckling_max_load_factor,
        buckling_repeated_tolerance=options.buckling_repeated_tolerance,
        buckling_allow_dense_fallback=options.buckling_allow_dense_fallback,
        recovery_history_mode=options.recovery_history_mode,
        recovery_threads=options.recovery_threads,
        memory_limit_mb=options.memory_limit_mb,
        capacity_buckling_mode_number=options.capacity_buckling_mode_number,
        capacity_mesh_min_elements_per_half_wave=options.capacity_mesh_min_elements_per_half_wave,
        fracture_enabled=options.fracture_enabled,
        fracture_strain_threshold=options.fracture_strain_threshold,
        fracture_residual_stiffness_fraction=options.fracture_residual_stiffness_fraction,
        fracture_max_deleted_fraction=options.fracture_max_deleted_fraction,
        fracture_min_load_factor=options.fracture_min_load_factor,
        collision_enabled=options.collision_enabled,
        collision_include_static_load=options.collision_include_static_load,
        collision_damage_enabled=options.collision_damage_enabled,
        collision_material_nonlinear_enabled=options.collision_material_nonlinear_enabled,
        collision_nonlinear_kinematics=_normalise_kinematics(options.collision_nonlinear_kinematics),
        collision_beam_contact_enabled=bool(options.collision_beam_contact_enabled),
        collision_adaptive_mesh_enabled=bool(options.collision_adaptive_mesh_enabled),
        collision_adaptive_fine_factor=float(options.collision_adaptive_fine_factor),
        collision_adaptive_fine_size_m=float(options.collision_adaptive_fine_size_m),
        collision_adaptive_extent_m=float(options.collision_adaptive_extent_m),
        collision_adaptive_growth_factor=float(options.collision_adaptive_growth_factor),
        collision_adaptive_zone_factor=float(options.collision_adaptive_zone_factor),
        detail_transition_style=str(options.detail_transition_style),
        custom_bc_segments_json=str(options.custom_bc_segments_json),
        thickness_regions_json=str(options.thickness_regions_json),
        collision_nonlinear_max_iterations=options.collision_nonlinear_max_iterations,
        collision_nonlinear_tolerance=options.collision_nonlinear_tolerance,
        collision_nonlinear_cutbacks=options.collision_nonlinear_cutbacks,
        collision_plastic_damage_threshold=options.collision_plastic_damage_threshold,
        collision_damage_criterion=options.collision_damage_criterion,
        collision_mass_kg=options.collision_mass_kg,
        collision_radius_m=options.collision_radius_m,
        collision_start_x_m=options.collision_start_x_m,
        collision_start_y_m=options.collision_start_y_m,
        collision_start_z_m=options.collision_start_z_m,
        collision_vector_x=options.collision_vector_x,
        collision_vector_y=options.collision_vector_y,
        collision_vector_z=options.collision_vector_z,
        collision_speed_mps=options.collision_speed_mps,
        collision_time_mode=options.collision_time_mode,
        collision_auto_steps_per_radius=options.collision_auto_steps_per_radius,
        collision_auto_post_contact_radii=options.collision_auto_post_contact_radii,
        collision_bounce_back_time_s=options.collision_bounce_back_time_s,
        collision_total_time_s=options.collision_total_time_s,
        collision_dt_s=options.collision_dt_s,
        collision_result_interval_s=options.collision_result_interval_s,
        collision_penalty_stiffness_n_per_m=options.collision_penalty_stiffness_n_per_m,
        collision_penalty_scale=options.collision_penalty_scale,
        collision_auto_precondition=bool(options.collision_auto_precondition),
        collision_contact_damping=options.collision_contact_damping,
        collision_max_iterations=options.collision_max_iterations,
        collision_penetration_tolerance_m=options.collision_penetration_tolerance_m,
        collision_force_tolerance_n=options.collision_force_tolerance_n,
        collision_target_penetration_fraction=options.collision_target_penetration_fraction,
        collision_max_event_substeps=options.collision_max_event_substeps,
        collision_contact_surface=options.collision_contact_surface,
        collision_damage_mode=options.collision_damage_mode,
        collision_damage_capacity_basis=options.collision_damage_capacity_basis,
        collision_damage_user_capacity_pa=options.collision_damage_user_capacity_pa,
        collision_damage_softening_start=options.collision_damage_softening_start,
        collision_damage_delete_at=options.collision_damage_delete_at,
        collision_damage_min_contact_area_m2=options.collision_damage_min_contact_area_m2,
        collision_damage_max_deleted_fraction=options.collision_damage_max_deleted_fraction,
        collision_damage_neighbor_smoothing=options.collision_damage_neighbor_smoothing,
    )


def runtime_geometry_projection(
    geometry: dict[str, Any],
    config: Any | None = None,
) -> geometry_generators.GeometryBackedProjection:
    """Return the unchanged runtime mapping backed by one exact owner model."""

    authority = geometry_generators.build_runtime_geometry_authority(
        geometry,
        include_stiffeners=bool(getattr(config, "include_stiffeners", True)),
        include_girders=bool(getattr(config, "include_girders", True)),
    )
    return geometry_generators.project_runtime_geometry(authority)


def build_runtime_generated_geometry(
    geometry: dict[str, Any] | geometry_generators.GeometryBackedProjection,
    config: Any,
) -> geometry_generators.GeometryBackedProjection:
    """Build the legacy FE/render payload from a geometry-backed projection."""

    projection = (
        geometry_generators.project_runtime_geometry(geometry.geometry_authority)
        if isinstance(geometry, geometry_generators.GeometryBackedProjection)
        else runtime_geometry_projection(geometry, config)
    )
    generated = fe_solver.build_generated_geometry(projection, config)
    return geometry_generators.project_runtime_payload(
        generated,
        projection.geometry_authority,
    )


def run_runtime_fem(snapshot: RuntimeFEMLineSnapshot, options: RuntimeFEMOptions,
                    status_callback=None, imported_fem_model=None,
                    precomputed_generated_geometry=None) -> RuntimeFEMRunResult:
    """Run the external ANYsolver production runtime for an ANYstructure model."""

    geometry = runtime_geometry_summary(snapshot, options)
    diagnostics = list(snapshot.diagnostics)
    if precomputed_generated_geometry is not None:
        diagnostics.append(
            "Using the generated custom imperfection mesh (mode shapes set to mesh) for this run."
        )
    imperfection_active = precomputed_generated_geometry is not None or bool(options.imperfection_enabled)
    if imperfection_active and str(options.analysis_type).strip().lower() == "linear eigenvalue":
        diagnostics.append(
            "NOTE: linear eigenvalue buckling of an imperfect geometry does not include the "
            "imperfection knockdown - eigenvalues of the deformed shape can even increase. "
            "Use a nonlinear runtime path (nonlinear static / nonlinear stability / capacity "
            "workflow) to capture imperfection sensitivity."
        )
    pressure_side = _normalise_pressure_side(options.pressure_direction)
    custom_load_entries = _runtime_custom_load_entries(options.custom_loads_json)
    listed_pressure = sum(
        abs(_safe_float(entry.get("pressure_pa"), 0.0))
        for entry in custom_load_entries
        if str(entry.get("type", "")).lower() in {"pressure", "panel_pressure"}
    )
    effective_pressure = float(
        options.pressure_pa if (not options.custom_load_bc_enabled or options.custom_loads_add_to_imported) else 0.0)
    if options.custom_load_bc_enabled:
        effective_pressure += float(listed_pressure if custom_load_entries else options.custom_pressure_pa)
    if bool(options.collision_enabled) and bool(options.collision_material_nonlinear_enabled):
        start_fe_solver_kernel_warmup((), background=False, status_callback=status_callback,
                                      include_nonlinear_impact=True)

    solver_config = _solver_config_from_options(options)
    # The GUI is a production ANYsolver client. Preserve fail-closed backend
    # statuses instead of replacing an invalid/nonconverged solve with the
    # compact estimator and presenting that estimate as a successful FE run.
    geometry_projection = runtime_geometry_projection(geometry, solver_config)
    solver_result = fe_solver.run_production_fem(
        geometry_projection,
        solver_config,
        status_callback=status_callback,
        imported_fem_model=imported_fem_model,
        precomputed_generated_geometry=precomputed_generated_geometry,
    )
    diagnostics.extend(solver_result.diagnostics)
    diagnostics.extend(_warmup_diagnostics())

    custom_patches = _runtime_custom_pressure_patches(options)
    custom_edges = _runtime_custom_edges(options)
    local_refinement_patches = _runtime_local_refinement_patches(options)
    warmup_state = fe_solver_kernel_warmup_status()
    solve_outcome = solver_result.outcome.to_dict()
    quantity_descriptors = tuple(
        descriptor.to_dict() for descriptor in solver_result.quantity_metadata
    )
    reaction_descriptors = tuple(
        descriptor
        for descriptor in quantity_descriptors
        if str(descriptor.get("quantity_id", "")).startswith("reaction")
    )

    summary = {
        **geometry,
        "line": snapshot.line_name,
        "mesh_fidelity": options.mesh_fidelity,
        "pressure_pa": effective_pressure * float(options.load_scale),
        "imported_pressure_pa": float(options.pressure_pa),
        "include_stiffeners": bool(options.include_stiffeners),
        "include_girders": bool(options.include_girders),
        "include_end_lids": bool(options.include_end_lids),
        "num_buckling_modes": int(options.num_buckling_modes),
        "mesh_size_m": float(options.mesh_size_m),
        "top_bottom_moment_nm": float(options.top_bottom_moment_nm),
        "torsional_moment_nm": float(options.torsional_moment_nm),
        "shear_force_n": float(options.shear_force_n),
        "boundary_condition": str(options.boundary_condition),
        "boundary_constraint_json": str(options.boundary_constraint_json),
        "boundary_auto_supports": bool(options.boundary_auto_supports),
        "symmetry_mode": str(options.symmetry_mode),
        "shell_element_order": str(options.shell_element_order),
        "beam_element_order": str(options.beam_element_order),
        "member_model": str(options.member_model),
        "analysis_type": str(options.analysis_type),
        "buckling_analysis_type": str(options.buckling_analysis_type),
        "pressure_direction": pressure_side,
        "pressure_side": pressure_side,
        "follower_pressure": bool(options.follower_pressure),
        "axial_force_n": float(options.axial_force_n),
        "acceleration_m_s2": [float(options.acceleration_x_m_s2), float(options.acceleration_y_m_s2),
                              float(options.acceleration_z_m_s2)],
        "added_mass_kg": float(options.added_mass_kg),
        "added_mass_location": str(options.added_mass_location),
        "enforced_displacement_x_m": float(options.enforced_displacement_x_m),
        "enforced_displacement_y_m": float(options.enforced_displacement_y_m),
        "enforced_displacement_z_m": float(options.enforced_displacement_z_m),
        "stiffener_eccentricity_m": float(options.stiffener_eccentricity_m),
        "girder_eccentricity_m": float(options.girder_eccentricity_m),
        "member_orientation": str(options.member_orientation),
        "solver_type": str(options.solver_type),
        "stress_percentile": float(options.stress_percentile),
        "elastic_modulus_pa": float(options.elastic_modulus_pa),
        "poisson_ratio": float(options.poisson_ratio),
        "yield_stress_pa": float(options.yield_stress_pa),
        "material_model": str(options.material_model),
        "steel_grade": str(options.steel_grade),
        "steel_thickness_class": str(options.steel_thickness_class),
        "nonlinear_max_load_factor": float(options.nonlinear_max_load_factor),
        "nonlinear_steps": int(options.nonlinear_steps),
        "nonlinear_max_iterations": int(options.nonlinear_max_iterations),
        "nonlinear_tolerance": float(options.nonlinear_tolerance),
        "nonlinear_layers": int(options.nonlinear_layers),
        "nonlinear_solution_control": str(options.nonlinear_solution_control),
        "nonlinear_convergence_profile": str(options.nonlinear_convergence_profile),
        "nonlinear_assembly_threads": int(options.nonlinear_assembly_threads),
        "nonlinear_static_kinematics": _normalise_kinematics(options.nonlinear_static_kinematics),
        "beam_consistent_mass_enabled": bool(options.beam_consistent_mass_enabled),
        "deformation_scale": float(options.deformation_scale),
        "custom_load_bc_enabled": bool(options.custom_load_bc_enabled),
        "custom_loads_add_to_imported": bool(options.custom_loads_add_to_imported),
        "custom_use_nullspace_projection": bool(options.custom_use_nullspace_projection),
        "custom_pressure_pa": float(options.custom_pressure_pa),
        "plate_edge_x0_support": str(options.plate_edge_x0_support),
        "plate_edge_x1_support": str(options.plate_edge_x1_support),
        "plate_edge_y0_support": str(options.plate_edge_y0_support),
        "plate_edge_y1_support": str(options.plate_edge_y1_support),
        "cylinder_lower_support": str(options.cylinder_lower_support),
        "cylinder_upper_support": str(options.cylinder_upper_support),
        "plate_edge_x0_load_n_per_m": float(options.plate_edge_x0_load_n_per_m),
        "plate_edge_x1_load_n_per_m": float(options.plate_edge_x1_load_n_per_m),
        "plate_edge_y0_load_n_per_m": float(options.plate_edge_y0_load_n_per_m),
        "plate_edge_y1_load_n_per_m": float(options.plate_edge_y1_load_n_per_m),
        "cylinder_lower_edge_load_n_per_m": float(options.cylinder_lower_edge_load_n_per_m),
        "cylinder_upper_edge_load_n_per_m": float(options.cylinder_upper_edge_load_n_per_m),
        "custom_loads_json": str(options.custom_loads_json),
        "custom_load_count": len(custom_load_entries),
        "custom_pressure_patches_json": str(options.custom_pressure_patches_json),
        "custom_edge_segments_json": str(options.custom_edge_segments_json),
        "custom_selected_edge_load_n_per_m": float(options.custom_selected_edge_load_n_per_m),
        "custom_selected_edge_load_components_json": str(options.custom_selected_edge_load_components_json),
        "edge_load_components_json": str(options.edge_load_components_json),
        "custom_pressure_patch_count": len(custom_patches),
        "custom_pressure_patch_area_m2": sum(
            max(0.0, patch["max_a"] - patch["min_a"])
            * max(0.0, patch["max_b"] - patch["min_b"])
            for patch in custom_patches
        ),
        "local_refinement_enabled": bool(options.local_refinement_enabled),
        "local_refinement_patch_count": len(local_refinement_patches),
        "local_refinement_patch_area_m2": sum(
            max(0.0, float(patch["max_a"]) - float(patch["min_a"]))
            * max(0.0, float(patch["max_b"]) - float(patch["min_b"]))
            for patch in local_refinement_patches
        ),
        "local_refinement_fine_factor": float(options.local_refinement_fine_factor),
        "local_refinement_fine_size_m": float(options.local_refinement_fine_size_m),
        "local_refinement_extent_m": float(options.local_refinement_extent_m),
        "local_refinement_growth_factor": float(options.local_refinement_growth_factor),
        "point_refinement_enabled": bool(options.point_refinement_enabled),
        "point_refinement_point_m": (
            float(options.point_refinement_x_m),
            float(options.point_refinement_y_m),
        ),
        "point_refinement_fine_factor": float(options.point_refinement_fine_factor),
        "point_refinement_fine_size_m": float(options.point_refinement_fine_size_m),
        "point_refinement_extent_m": float(options.point_refinement_extent_m),
        "point_refinement_growth_factor": float(options.point_refinement_growth_factor),
        "custom_edge_segment_count": len(custom_edges),
        "custom_time_domain_enabled": bool(options.custom_time_domain_enabled),
        "custom_time_domain_duration_s": float(options.custom_time_domain_duration_s),
        "custom_time_domain_total_time_s": float(options.custom_time_domain_total_time_s),
        "custom_time_domain_dt_s": float(options.custom_time_domain_dt_s),
        "custom_time_domain_result_interval_s": float(options.custom_time_domain_result_interval_s),
        "custom_time_domain_include_static_load": bool(options.custom_time_domain_include_static_load),
        "imperfection_enabled": bool(options.imperfection_enabled),
        "imperfection_shape": str(options.imperfection_shape),
        "imperfection_amplitude_m": float(options.imperfection_amplitude_m),
        "imperfection_wave_a": int(options.imperfection_wave_a),
        "imperfection_wave_b": int(options.imperfection_wave_b),
        "imperfection_mode_shapes_json": str(options.imperfection_mode_shapes_json),
        "runtime_solver": str(options.runtime_solver),
        "allow_unbalanced_free_free": bool(options.allow_unbalanced_free_free),
        "buckling_shift_load_factor": float(options.buckling_shift_load_factor),
        "buckling_min_load_factor": float(options.buckling_min_load_factor),
        "buckling_max_load_factor": float(options.buckling_max_load_factor),
        "buckling_repeated_tolerance": float(options.buckling_repeated_tolerance),
        "buckling_allow_dense_fallback": bool(options.buckling_allow_dense_fallback),
        "recovery_history_mode": str(options.recovery_history_mode),
        "recovery_threads": int(options.recovery_threads),
        "memory_limit_mb": float(options.memory_limit_mb),
        "capacity_buckling_mode_number": int(options.capacity_buckling_mode_number),
        "capacity_mesh_min_elements_per_half_wave": int(options.capacity_mesh_min_elements_per_half_wave),
        "fracture_enabled": bool(options.fracture_enabled),
        "fracture_strain_threshold": float(options.fracture_strain_threshold),
        "fracture_residual_stiffness_fraction": float(options.fracture_residual_stiffness_fraction),
        "fracture_max_deleted_fraction": float(options.fracture_max_deleted_fraction),
        "fracture_min_load_factor": float(options.fracture_min_load_factor),
        "collision_enabled": bool(options.collision_enabled),
        "collision_include_static_load": bool(options.collision_include_static_load),
        "collision_damage_enabled": bool(options.collision_damage_enabled),
        "collision_material_nonlinear_enabled": bool(options.collision_material_nonlinear_enabled),
        "collision_nonlinear_kinematics": _normalise_kinematics(options.collision_nonlinear_kinematics),
        "collision_beam_contact_enabled": bool(options.collision_beam_contact_enabled),
        "collision_adaptive_mesh_enabled": bool(options.collision_adaptive_mesh_enabled),
        "collision_adaptive_fine_factor": float(options.collision_adaptive_fine_factor),
        "collision_adaptive_fine_size_m": float(options.collision_adaptive_fine_size_m),
        "collision_adaptive_extent_m": float(
            options.collision_adaptive_extent_m
            if float(options.collision_adaptive_extent_m) > 0.0
            else float(options.collision_radius_m) * max(float(options.collision_adaptive_zone_factor), 0.5)
        ),
        "collision_adaptive_growth_factor": float(options.collision_adaptive_growth_factor),
        "collision_adaptive_zone_factor": float(options.collision_adaptive_zone_factor),
        "detail_transition_style": str(options.detail_transition_style),
        "custom_bc_segments_json": str(options.custom_bc_segments_json),
        "thickness_regions_json": str(options.thickness_regions_json),
        "collision_nonlinear_max_iterations": int(options.collision_nonlinear_max_iterations),
        "collision_nonlinear_tolerance": float(options.collision_nonlinear_tolerance),
        "collision_nonlinear_cutbacks": int(options.collision_nonlinear_cutbacks),
        "collision_plastic_damage_threshold": float(options.collision_plastic_damage_threshold),
        "collision_damage_criterion": str(options.collision_damage_criterion),
        "collision_mass_kg": float(options.collision_mass_kg),
        "collision_radius_m": float(options.collision_radius_m),
        "collision_start_m": (
            float(options.collision_start_x_m),
            float(options.collision_start_y_m),
            float(options.collision_start_z_m),
        ),
        "collision_vector": (
            float(options.collision_vector_x),
            float(options.collision_vector_y),
            float(options.collision_vector_z),
        ),
        "collision_speed_mps": float(options.collision_speed_mps),
        "collision_time_mode": str(options.collision_time_mode),
        "collision_auto_steps_per_radius": float(options.collision_auto_steps_per_radius),
        "collision_auto_post_contact_radii": float(options.collision_auto_post_contact_radii),
        "collision_bounce_back_time_s": float(options.collision_bounce_back_time_s),
        "collision_total_time_s": float(options.collision_total_time_s),
        "collision_dt_s": float(options.collision_dt_s),
        "collision_result_interval_s": float(options.collision_result_interval_s),
        "collision_penalty_stiffness_n_per_m": float(options.collision_penalty_stiffness_n_per_m),
        "collision_penalty_scale": float(options.collision_penalty_scale),
        "collision_auto_precondition": bool(options.collision_auto_precondition),
        "collision_contact_damping": float(options.collision_contact_damping),
        "collision_max_iterations": int(options.collision_max_iterations),
        "collision_penetration_tolerance_m": float(options.collision_penetration_tolerance_m),
        "collision_force_tolerance_n": float(options.collision_force_tolerance_n),
        "collision_target_penetration_fraction": float(options.collision_target_penetration_fraction),
        "collision_max_event_substeps": int(options.collision_max_event_substeps),
        "collision_contact_surface": str(options.collision_contact_surface),
        "collision_damage_mode": str(options.collision_damage_mode),
        "collision_damage_capacity_basis": str(options.collision_damage_capacity_basis),
        "collision_damage_user_capacity_pa": float(options.collision_damage_user_capacity_pa),
        "collision_damage_softening_start": float(options.collision_damage_softening_start),
        "collision_damage_delete_at": float(options.collision_damage_delete_at),
        "collision_damage_min_contact_area_m2": float(options.collision_damage_min_contact_area_m2),
        "collision_damage_max_deleted_fraction": float(options.collision_damage_max_deleted_fraction),
        "collision_damage_neighbor_smoothing": bool(options.collision_damage_neighbor_smoothing),
        "kernel_warmup_status": str(warmup_state.get("status", "not_started")),
        "kernel_warmup_shell_orders": tuple(str(order) for order in warmup_state.get("shell_orders", ()) or ()),
        "kernel_warmup_total_seconds": _safe_float(warmup_state.get("total_seconds"), 0.0),
        "kernel_warmup_jit_enabled": bool(warmup_state.get("jit_enabled", False)),
        "kernel_warmup_parallel_threads": warmup_state.get("parallel_threads"),
        "kernel_warmup_max_matrix_difference_norm": _safe_float(warmup_state.get("max_matrix_difference_norm"), 0.0),
        "solver": solver_result.solver_name,
        "solve_outcome": solve_outcome,
        "result_quantities": quantity_descriptors,
        "reaction_quantities": reaction_descriptors,
        "anysolver_version": _require_supported_anysolver(),
        "mesh_info": dict(solver_result.mesh_info),
        "max_displacement_m": solver_result.displacement_max_m,
        "prestress_summary": dict(solver_result.prestress_summary),
        "load_resultant": dict(solver_result.load_resultant),
    }
    return RuntimeFEMRunResult(
        status=solver_result.status,
        summary=summary,
        diagnostics=tuple(diagnostics),
        buckling_factors=solver_result.buckling_factors,
        stress_percentiles=(
            ("p95", solver_result.stress_p95_pa),
            ("max", solver_result.stress_max_pa),
        ),
        displacement_scale=solver_result.displacement_max_m,
        visualization=dict(solver_result.visualization),
    )


def _plot_grid_values(grid: Any) -> list[list[float]]:
    try:
        return [[_safe_float(value) for value in row] for row in grid]
    except TypeError:
        return []


def _all_grid_values(grid: list[list[float]]) -> list[float]:
    return [value for row in grid for value in row]


def _clamped_alpha(value: Any, default: float = 1.0) -> float:
    return min(max(_safe_float(value, default), 0.0), 1.0)


def _crisp_canvas_alpha(value: Any, default: float = 1.0) -> float:
    """Avoid soft-looking near-opaque Tk canvas surfaces."""

    alpha = _clamped_alpha(value, default)
    if alpha >= 0.98:
        return 1.0
    return alpha


def _blend_hex_color(color: str, alpha: float, background: str = "#ffffff") -> str:
    """Blend a solid Tk colour towards the background to emulate opacity."""

    alpha = _clamped_alpha(alpha, 1.0)
    try:
        foreground_rgb = np.asarray(mcolors.to_rgb(color), dtype=float)
        background_rgb = np.asarray(mcolors.to_rgb(background), dtype=float)
        return mcolors.to_hex(alpha * foreground_rgb + (1.0 - alpha) * background_rgb)
    except Exception:
        return color


def _tk_color_value(value: Any, default: str) -> str:
    color = str(value or "").strip()
    if not color:
        return default
    try:
        mcolors.to_rgb(color)
    except ValueError:
        return default
    return color


#: Positions at which a matplotlib colormap is sampled for the Tk canvas.
#: The canvas interpolates linearly between stops, so an even, reasonably
#: dense set reproduces a smooth map such as viridis or turbo faithfully.
_CANVAS_COLORMAP_SAMPLES = 17


def _resolve_colormap(name: str) -> Any:
    """
    Look a colormap up by name, ignoring case.

    Matplotlib's registry is case-sensitive, so the "greys" entry in the
    Visualization tab used to miss `Greys` and silently fall back to jet.
    """
    text = str(name or "jet").strip()
    try:
        return colormaps[text]
    except (KeyError, ValueError, TypeError):
        pass
    lowered = text.lower()
    try:
        for candidate in colormaps:
            if str(candidate).lower() == lowered:
                return colormaps[candidate]
    except TypeError:
        pass
    return colormaps["jet"]


def _configure_tk_canvas_colormap(colormap: str) -> None:
    """Keep the interactive canvas surface colours and legend in sync."""

    cmap = _resolve_colormap(colormap)
    positions = tuple(
        index / (_CANVAS_COLORMAP_SAMPLES - 1) for index in range(_CANVAS_COLORMAP_SAMPLES)
    )
    stops = tuple((position, mcolors.to_hex(cmap(position), keep_alpha=False)) for position in positions)

    setter = getattr(_tk3d_canvas_module, "set_color_stops", None)
    if callable(setter):
        try:
            setter(stops)
            return
        except Exception:
            pass

    # ANYtk3D before the public colour-scale API read a module constant.
    # Patch it wherever the interpolation actually lives - the function moved
    # between modules once, and a stale target silently disables the setting.
    targets = {_tk3d_canvas_module, inspect.getmodule(_interpolate_thickness_color)}
    for target in targets:
        if target is None:
            continue
        try:
            setattr(target, "_THICKNESS_COLOR_STOPS", stops)
        except Exception:
            pass


def _finite_values(values: Iterable[float]) -> list[float]:
    result = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            result.append(number)
    return result


def _finite_value_range(values: Iterable[float], default: tuple[float, float] = (0.0, 1.0)) -> tuple[float, float]:
    clean = _finite_values(values)
    if not clean:
        return default
    minimum = min(clean)
    maximum = max(clean)
    if maximum <= minimum:
        pad = max(abs(minimum) * 0.05, 1.0e-9)
        return minimum - pad, maximum + pad
    return minimum, maximum


def _resolved_color_limits(
        values: Iterable[float],
        manual_limits: tuple[float | None, float | None] | None = None,
) -> tuple[float, float]:
    data_min, data_max = _finite_value_range(values)
    if manual_limits is None:
        return data_min, data_max
    lower, upper = manual_limits
    if lower is None and upper is None:
        return data_min, data_max
    vmin = data_min if lower is None else float(lower)
    vmax = data_max if upper is None else float(upper)
    if vmax < vmin:
        vmin, vmax = vmax, vmin
    if vmax <= vmin:
        pad = max(abs(vmin) * 0.05, 1.0e-9)
        vmin -= pad
        vmax += pad
    return vmin, vmax


def _surface_facecolors(
        values_grid: list[list[float]],
        colormap: str = "jet",
        extra_values: list[float] | None = None,
        value_range: tuple[float, float] | None = None,
):
    values = _all_grid_values(values_grid)
    if extra_values:
        values.extend(float(value) for value in extra_values)
    if value_range is None:
        vmin, vmax = _finite_value_range(values)
    else:
        vmin, vmax = _resolved_color_limits(values, value_range)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax, clip=True)
    cmap = colormaps.get(colormap, colormaps["jet"])
    return [[cmap(norm(value)) for value in row] for row in values_grid], norm, cmap


def _visualization_displacement_extent(visualization: dict[str, Any]) -> float:
    if visualization.get("type") == "cylinder":
        values = _all_grid_values(_plot_grid_values(visualization.get("radial_displacement_m")))
    else:
        values = _all_grid_values(_plot_grid_values(visualization.get("w_m")))
    return max((abs(value) for value in values), default=0.0)


def _displacement_plot_scale(
        geometry: dict[str, Any],
        result: RuntimeFEMRunResult | None,
        visualization: dict[str, Any] | None = None,
        override_scale: float | None = None,
) -> float:
    if override_scale is not None and override_scale > 0.0:
        return float(override_scale)
    summary_scale = _safe_float((result.summary if result is not None else {}).get("deformation_scale"), 0.0)
    if summary_scale > 0.0:
        return summary_scale
    display_displacement = _visualization_displacement_extent(visualization or {})
    result_displacement = 0.0 if result is None else result.displacement_scale
    displacement = max(display_displacement, result_displacement)
    if displacement <= 0.0:
        return 1.0
    length = _safe_float(geometry.get("length_m"), 1.0)
    width = _safe_float(geometry.get("width_m"), _safe_float(geometry.get("radius_m"), 1.0))
    reference = max(length, width, _safe_float(geometry.get("radius_m"), 0.0), 1.0e-9)
    return min(max(0.08 * reference / max(displacement, 1.0e-12), 1.0), 1.0e5)


def _set_3d_axes_limits(axis: Any, x: list[list[float]], y: list[list[float]], z: list[list[float]]) -> None:
    xs = _all_grid_values(x)
    ys = _all_grid_values(y)
    zs = _all_grid_values(z)
    if not xs or not ys or not zs:
        return
    axis.set_xlim(min(xs), max(xs))
    axis.set_ylim(min(ys), max(ys))
    axis.set_zlim(min(zs), max(zs) if max(zs) > min(zs) else min(zs) + 1.0e-9)
    try:
        axis.set_box_aspect((max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0, max(zs) - min(zs) or 1.0))
    except Exception:
        pass


def _plot_member_lines(
        axis: Any,
        visualization: dict[str, Any],
        scale: float,
        show_stiffeners: bool = True,
        show_girders: bool = True,
        member_alpha: float = 0.95,
) -> None:
    role_style = {
        "stiffener": ("#1f2937", 1.7),
        "girder": ("#7f1d1d", 2.2),
    }
    for line in visualization.get("member_lines") or ():
        role = str(line.get("role", "member")).lower()
        if role == "stiffener" and not show_stiffeners:
            continue
        if role == "girder" and not show_girders:
            continue

        points = list(line.get("points") or ())
        displaced = list(line.get("displaced_points") or ())
        if len(points) < 2:
            continue
        plot_points = []
        for index, point in enumerate(points):
            try:
                base = np.asarray(point, dtype=float)
                moved = np.asarray(displaced[index], dtype=float) if index < len(displaced) else base
            except Exception:
                continue
            plot_points.append(base + (moved - base) * float(scale))
        if len(plot_points) < 2:
            continue
        color, width = role_style.get(role, ("#475569", 1.4))
        for start, end in zip(plot_points, plot_points[1:]):
            axis.plot(
                [start[0], end[0]],
                [start[1], end[1]],
                [start[2], end[2]],
                color=color,
                linewidth=width,
                alpha=member_alpha,
                solid_capstyle="round",
            )


def _sphere_display_center(
        sphere: dict[str, Any],
        visualization: dict[str, Any],
        deformation_scale: float,
) -> np.ndarray:
    """Return sphere center in the same displayed coordinates as deformed shell surfaces."""

    center = np.asarray(sphere.get("position", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
    scale = float(deformation_scale)
    if abs(scale - 1.0) <= 1.0e-12:
        return center
    contacts = tuple(sphere.get("active_contacts") or visualization.get("active_contacts") or ())
    if not contacts:
        return center
    best_offset: np.ndarray | None = None
    best_distance = float("inf")
    surfaces = tuple(visualization.get("skin_shell_surfaces") or ()) + tuple(visualization.get("shell_surfaces") or ())
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
        try:
            element_id = int(contact.get("element_id"))
            contact_point = np.asarray(contact.get("contact_point", ()), dtype=float).reshape(3)
        except Exception:
            continue
        for surface in surfaces:
            try:
                if int(surface.get("id", -1)) != element_id:
                    continue
            except Exception:
                continue
            points = tuple(surface.get("points") or ())
            displaced = tuple(surface.get("displaced_points") or ())
            if len(points) < 1 or len(displaced) != len(points):
                continue
            local_offsets: list[np.ndarray] = []
            for point, moved in zip(points, displaced):
                try:
                    base = np.asarray(point, dtype=float).reshape(3)
                    deformed = np.asarray(moved, dtype=float).reshape(3)
                except Exception:
                    continue
                offset = deformed - base
                distance = float(np.linalg.norm(deformed - contact_point))
                if distance < best_distance:
                    best_distance = distance
                    best_offset = offset
                local_offsets.append(offset)
            if best_offset is None and local_offsets:
                best_offset = np.mean(np.vstack(local_offsets), axis=0)
    if best_offset is None:
        return center
    return center + (scale - 1.0) * best_offset


def _plot_rigid_sphere(axis: Any, visualization: dict[str, Any], deformation_scale: float = 1.0) -> None:
    sphere = visualization.get("rigid_sphere") or {}
    if not isinstance(sphere, dict) or not bool(sphere.get("visible", True)):
        return
    try:
        center = _sphere_display_center(sphere, visualization, deformation_scale)
        radius = max(_safe_float(sphere.get("radius"), 0.0), 0.0)
    except Exception:
        return
    if radius <= 0.0:
        return
    u = np.linspace(0.0, 2.0 * math.pi, 18)
    v = np.linspace(0.0, math.pi, 10)
    x = center[0] + radius * np.outer(np.cos(u), np.sin(v))
    y = center[1] + radius * np.outer(np.sin(u), np.sin(v))
    z = center[2] + radius * np.outer(np.ones_like(u), np.cos(v))
    axis.plot_surface(x, y, z, color="#9ca3af", alpha=0.32, linewidth=0.0, shade=True, zorder=10)
    axis.scatter([center[0]], [center[1]], [center[2]], color="#4b5563", s=14, alpha=0.55, zorder=10)


def _format_dimension(value: float) -> str:
    value = float(value)
    if abs(value) >= 100.0:
        return f"{value:.0f} m"
    if abs(value) >= 10.0:
        return f"{value:.1f} m"
    if abs(value) >= 1.0:
        return f"{value:.2f} m"
    return f"{value:.3f} m"


def _base_geometry_height_extent(geometry: dict[str, Any]) -> float:
    heights = [0.0]
    for key in ("stiffener_section", "girder_section"):
        section = geometry.get(key) or {}
        heights.append(_safe_float(section.get("web_height") or section.get("web_h"), 0.0))
        heights.append(_safe_float(section.get("flange_thickness") or section.get("flange_t"), 0.0))
    return max(heights)


def _plot_geometry_dimension_annotations(axis: Any, geometry: dict[str, Any], is_cylinder: bool) -> None:
    color = "#6b7280"
    if is_cylinder:
        radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-6)
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        y = -1.18 * radius
        z = -0.18 * radius
        axis.plot([-radius, radius], [y, y], [z, z], color=color, linewidth=0.8, alpha=0.6)
        axis.text(0.0, y, z, "D " + _format_dimension(2.0 * radius), color=color, fontsize=8, ha="center", va="top")
        x = 1.18 * radius
        y2 = 1.18 * radius
        axis.plot([x, x], [y2, y2], [0.0, length], color=color, linewidth=0.8, alpha=0.6)
        axis.text(x, y2, 0.5 * length, "L " + _format_dimension(length), color=color, fontsize=8, ha="left",
                  va="center")
        return
    length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
    width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-6)
    offset = 0.06 * max(length, width, 1.0)
    axis.plot([0.0, length], [-offset, -offset], [0.0, 0.0], color=color, linewidth=0.8, alpha=0.6)
    axis.text(0.5 * length, -offset, 0.0, _format_dimension(length), color=color, fontsize=8, ha="center", va="top")
    axis.plot([-offset, -offset], [0.0, width], [0.0, 0.0], color=color, linewidth=0.8, alpha=0.6)
    axis.text(-offset, 0.5 * width, 0.0, _format_dimension(width), color=color, fontsize=8, ha="right", va="center")
    height = _base_geometry_height_extent(geometry)
    if height > 0.0:
        axis.plot([length + offset, length + offset], [width + offset, width + offset], [0.0, height], color=color,
                  linewidth=0.8, alpha=0.6)
        axis.text(length + offset, width + offset, 0.5 * height, _format_dimension(height), color=color, fontsize=8,
                  ha="left", va="center")


def _buckling_mode_shapes(result: RuntimeFEMRunResult | None) -> list[dict[str, Any]]:
    if result is None:
        return []
    return list((result.visualization or {}).get("buckling_modes") or [])


def _member_endpoint_displacements(line: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    points = list(line.get("points") or ())
    displaced = list(line.get("displaced_points") or ())
    if len(points) < 2 or len(displaced) < 2:
        zero = np.zeros(3, dtype=float)
        return zero, zero
    try:
        disp_a = np.asarray(displaced[0], dtype=float) - np.asarray(points[0], dtype=float)
        disp_b = np.asarray(displaced[1], dtype=float) - np.asarray(points[1], dtype=float)
    except Exception:
        zero = np.zeros(3, dtype=float)
        return zero, zero
    return disp_a, disp_b


def _member_component_value(line: dict[str, Any], component: str, *, is_mode: bool, flange: bool = False) -> float:
    disp_a, disp_b = _member_endpoint_displacements(line)
    if is_mode:
        return 0.5 * (float(np.linalg.norm(disp_a)) + float(np.linalg.norm(disp_b)))
    if component == "disp_mag":
        return 500.0 * (float(np.linalg.norm(disp_a)) + float(np.linalg.norm(disp_b)))
    if component == "disp_x":
        return 500.0 * float(disp_a[0] + disp_b[0])
    if component == "disp_y":
        return 500.0 * float(disp_a[1] + disp_b[1])
    if component == "disp_z":
        return 500.0 * float(disp_a[2] + disp_b[2])
    if component == "plastic_strain":
        return 0.0
    if component.startswith("impact_damage"):
        return 0.0

    sig_axial = _safe_float(line.get("axial_stress"), 0.0)
    sig_bend_y = _safe_float(line.get("bending_stress_y"), 0.0)
    sig_bend_z = _safe_float(line.get("bending_stress_z"), 0.0)
    tau_y = _safe_float(line.get("shear_stress_y"), 0.0)
    tau_z = _safe_float(line.get("shear_stress_z"), 0.0)
    tau_t = _safe_float(line.get("torsional_stress"), 0.0)
    if component == "von_mises_pa":
        if "von_mises" in line:
            return _safe_float(line.get("von_mises"), 0.0) / 1.0e6
        sig_x = sig_axial + (sig_bend_y if flange else 0.0)
        return math.sqrt(max(sig_x * sig_x + 3.0 * (tau_y * tau_y + tau_z * tau_z + tau_t * tau_t), 0.0)) / 1.0e6
    if component == "stress_x_membrane_pa":
        return (sig_axial + (sig_bend_y if flange else 0.0)) / 1.0e6
    if component == "stress_xy_membrane_pa":
        return tau_y / 1.0e6
    if component == "stress_y_membrane_pa":
        return sig_bend_z / 1.0e6
    if component == "strain_x_membrane":
        return _safe_float(line.get("axial_strain"), 0.0)
    if component in {"strain_y_membrane", "strain_xy_membrane"}:
        return 0.0
    return _safe_float(line.get("von_mises"), 0.0) / 1.0e6


_SHELL_FIELD_COMPONENTS = {
    "von_mises_pa",
    "stress_x_membrane_pa",
    "stress_y_membrane_pa",
    "stress_xy_membrane_pa",
    "strain_x_membrane",
    "strain_y_membrane",
    "strain_xy_membrane",
    "plastic_strain",
    "impact_damage",
    "impact_damage_utilization",
    "impact_damage_scale",
}

_COMPONENT_DISPLAY_LABELS = {
    "von_mises_pa": "stress von Mises [Pa]",
    "stress_x_membrane_pa": "stress X membrane [Pa]",
    "stress_y_membrane_pa": "stress Y membrane [Pa]",
    "stress_xy_membrane_pa": "stress XY membrane [Pa]",
    "strain_x_membrane": "strain X membrane [-]",
    "strain_y_membrane": "strain Y membrane [-]",
    "strain_xy_membrane": "strain XY membrane [-]",
    "impact_damage": "impact damage [-]",
    "impact_damage_utilization": "impact damage utilization [-]",
    "impact_damage_scale": "impact damage stiffness scale [-]",
    "plastic_strain": "equiv. engineering plastic strain [-]",
}


def _summary_uses_nonlinear_material(summary: dict[str, Any] | None) -> bool:
    text = str((summary or {}).get("material_model", "")).lower()
    prestress = (summary or {}).get("prestress_summary", {}) or {}
    return "dnv-rp-c208" in text or str(prestress.get("material_model", "")).upper() == "DNV-RP-C208"


def _include_member_component_in_color_range(
        summary: dict[str, Any] | None,
        component: str,
        *,
        is_mode: bool,
) -> bool:
    if is_mode or component.startswith("disp"):
        return True
    if component in {"plastic_strain", "impact_damage", "impact_damage_utilization", "impact_damage_scale",
                     "strain_x_membrane", "strain_y_membrane", "strain_xy_membrane"}:
        return False
    if component in {"stress_x_membrane_pa", "stress_y_membrane_pa", "stress_xy_membrane_pa"}:
        return False
    if component == "von_mises_pa" and _summary_uses_nonlinear_material(summary):
        return False
    return True


def _shell_surface_component_value(surface: dict[str, Any], component: str, *, is_mode: bool) -> float:
    values = surface.get("field_values", {}) or {}
    if is_mode:
        return _safe_float(values.get(component), _safe_float(values.get("disp_mag"), 0.0))
    if component in values:
        value = _safe_float(values.get(component), 0.0)
    elif component in _SHELL_FIELD_COMPONENTS or component.startswith("disp"):
        value = 0.0
    else:
        value = _safe_float(values.get("von_mises_pa"), 0.0)
    if component.endswith("_pa"):
        return value / 1.0e6
    if "disp" in component:
        return value * 1000.0
    return value


def _shell_surface_role_visible(surface: dict[str, Any], show_stiffeners: bool, show_girders: bool) -> bool:
    role = str(surface.get("role", "member")).lower()
    if "stiffener" in role and not show_stiffeners:
        return False
    if ("girder" in role or "frame" in role) and not show_girders:
        return False
    return True


def _shell_surface_points(surface: dict[str, Any], scale: float) -> list[tuple[float, float, float]]:
    points = list(surface.get("points") or ())
    displaced = list(surface.get("displaced_points") or ())
    result: list[tuple[float, float, float]] = []
    for index, point in enumerate(points):
        try:
            base = np.asarray(point, dtype=float)
            moved = np.asarray(displaced[index], dtype=float) if index < len(displaced) else base
        except Exception:
            continue
        plotted = base + (moved - base) * float(scale)
        result.append((float(plotted[0]), float(plotted[1]), float(plotted[2])))
    return result


def _selected_visualization(result: RuntimeFEMRunResult, display_mode: str, component: str = "von_mises_pa") -> tuple[
    dict[str, Any], str, bool]:
    def _zero_scalar_like(vis: dict[str, Any]) -> tuple[Any, ...]:
        source = vis.get("stress_pa")
        if not source:
            fields = vis.get("fields", {})
            source = next(iter(fields.values()), ()) if fields else ()
        zeros = []
        for grid in source or ():
            try:
                zeros.append(np.zeros_like(np.asarray(grid, dtype=float)).tolist())
            except Exception:
                zeros.append(grid)
        return tuple(zeros)

    def _set_unavailable_plastic(vis: dict[str, Any]) -> None:
        vis["stress_pa"] = _zero_scalar_like(vis)
        vis["scalar_label"] = "equiv. engineering plastic strain unavailable [-]"
        vis["scalar_kind"] = "raw"

    def _set_unavailable_component(vis: dict[str, Any], label: str) -> None:
        vis["stress_pa"] = _zero_scalar_like(vis)
        vis["scalar_label"] = label + " unavailable"
        vis["scalar_kind"] = "raw"

    if display_mode == "plastic":
        visualization = dict(result.visualization or {})
        if visualization.get("plastic_strain"):
            visualization["stress_pa"] = visualization.get("plastic_strain")
            visualization["scalar_label"] = visualization.get(
                "plastic_strain_label") or "equiv. engineering plastic strain [-]"
            visualization["scalar_kind"] = "raw"
            return visualization, "Engineering plastic strain", False
        _set_unavailable_plastic(visualization)
        return visualization, "Engineering plastic strain unavailable", False

    def apply_component(vis: dict[str, Any], title: str) -> tuple[dict[str, Any], str]:
        fields = vis.get("fields", {})
        disps = vis.get("displacements", {})
        if component == "plastic_strain":
            if vis.get("plastic_strain"):
                vis["stress_pa"] = vis["plastic_strain"]
                vis["scalar_label"] = vis.get("plastic_strain_label", "equiv. engineering plastic strain [-]")
                vis["scalar_kind"] = "raw"
            else:
                _set_unavailable_plastic(vis)
        elif component in fields:
            vis["stress_pa"] = fields[component]
            vis["scalar_label"] = _COMPONENT_DISPLAY_LABELS.get(component, component.replace("_", " "))
            if component.endswith("_pa"):
                vis.pop("scalar_kind", None)
            else:
                vis["scalar_kind"] = "raw"
        elif component == "von_mises_pa" and vis.get("stress_pa"):
            label = str(vis.get("scalar_label", "stress [Pa]") or "stress [Pa]")
            if "displacement" in label.lower() or label.lower().startswith("disp"):
                _set_unavailable_component(vis, "Stress von Mises")
            else:
                vis["scalar_label"] = label
        elif component in disps:
            vis["stress_pa"] = disps[component]
            vis["scalar_label"] = component.replace("_", " ") + " [m]"
            vis.pop("scalar_kind", None)
        elif component in _SHELL_FIELD_COMPONENTS:
            _set_unavailable_component(vis, _COMPONENT_DISPLAY_LABELS.get(component, component.replace("_", " ")))
        return vis, title

    if display_mode.startswith("mode:"):
        try:
            mode_number = int(display_mode.split(":", 1)[1])
        except (IndexError, ValueError):
            mode_number = -1
        for mode in _buckling_mode_shapes(result):
            if int(mode.get("mode_number", -1)) == mode_number:
                factor = _safe_float(mode.get("load_factor"))
                title = "Buckling mode " + str(mode_number) + "  LF=" + str(round(factor, 4))
                vis, _ = apply_component(dict(mode.get("shape") or {}), title)
                return vis, title, True

    if display_mode.startswith("time:"):
        try:
            step_index = int(display_mode.split(":", 1)[1])
        except (IndexError, ValueError):
            step_index = -1
        time_domain = (result.visualization or {}).get("time_domain", {}) or {}
        snapshots = tuple(time_domain.get("snapshots") or ())
        if 0 <= step_index < len(snapshots):
            snapshot_vis = dict(snapshots[step_index] or {})
            time_value = _safe_float(snapshot_vis.get("time_s"), 0.0)
            vis, _ = apply_component(snapshot_vis, "Time-domain t=" + f"{time_value:.6g}" + " s")
            return vis, "Time-domain t=" + f"{time_value:.6g}" + " s", False

    vis, title = apply_component(dict(result.visualization or {}), "Static stress/displacement")
    return vis, title, False


def _visualization_color_grid_and_label(
        visualization: dict[str, Any],
        component: str,
        is_mode: bool,
) -> tuple[list[list[float]], str]:
    def convert_label(raw_label: str, source_unit: str, target_unit: str) -> str:
        label = raw_label.replace("_pa", "").strip()
        label = re.sub(r"\s*\[" + re.escape(source_unit) + r"\]\s*$", "", label).strip()
        label = re.sub(r"\s*\[[^\]]+\]\s*$", "", label).strip()
        return (label or raw_label or "value") + " [" + target_unit + "]"

    scalar_values = _plot_grid_values(visualization.get("stress_pa"))
    if is_mode:
        return scalar_values, str(visualization.get("scalar_label") or "mode amplitude")
    if visualization.get("scalar_kind") == "raw":
        return scalar_values, str(visualization.get("scalar_label") or "value")
    if component.endswith("_pa"):
        return (
            [[value / 1.0e6 for value in row] for row in scalar_values],
            convert_label(str(visualization.get("scalar_label", "stress")), "Pa", "MPa"),
        )
    if "disp" in component:
        return (
            [[value * 1000.0 for value in row] for row in scalar_values],
            convert_label(str(visualization.get("scalar_label", "displacement")), "m", "mm"),
        )
    return scalar_values, str(visualization.get("scalar_label", component))


def _visualization_color_values(
        visualization: dict[str, Any],
        component: str,
        is_mode: bool,
        summary: dict[str, Any] | None = None,
        show_stiffeners: bool = True,
        show_girders: bool = True,
        include_members: bool = True,
) -> tuple[list[float], list[list[float]], str]:
    color_grid, colorbar_label = _visualization_color_grid_and_label(visualization, component, is_mode)
    values = _all_grid_values(color_grid)
    for surface in visualization.get("skin_shell_surfaces") or ():
        values.append(_shell_surface_component_value(surface, component, is_mode=is_mode))
    if include_members:
        include_member_range = _include_member_component_in_color_range(summary, component, is_mode=is_mode)
        if include_member_range:
            for line in visualization.get("member_lines") or ():
                role = str(line.get("role", "member")).lower()
                if role == "stiffener" and not show_stiffeners:
                    continue
                if role == "girder" and not show_girders:
                    continue
                values.append(_member_component_value(line, component, is_mode=is_mode, flange=False))
                if _safe_float(line.get("flange_width"), 0.0) > 0.0:
                    values.append(_member_component_value(line, component, is_mode=is_mode, flange=True))
        for surface in visualization.get("shell_surfaces") or ():
            if not _shell_surface_role_visible(surface, show_stiffeners, show_girders):
                continue
            values.append(_shell_surface_component_value(surface, component, is_mode=is_mode))
    return values, color_grid, colorbar_label


def _plot_visualization_surface(
        figure: Figure,
        axis: Any,
        geometry: dict[str, Any],
        result: RuntimeFEMRunResult,
        display_mode: str = "static",
        deformation_scale: float | None = None,
        show_plate: bool = True,
        show_stiffeners: bool = True,
        show_girders: bool = True,
        plate_alpha: float = 1.0,
        member_alpha: float = 0.95,
        colormap: str = "jet",
        component: str = "von_mises_pa",
        color_limits: tuple[float | None, float | None] | None = None,
        show_sphere: bool = True,
) -> None:
    plate_alpha = _clamped_alpha(plate_alpha, 1.0)
    member_alpha = _clamped_alpha(member_alpha, 0.95)
    visualization, title, is_mode = _selected_visualization(result, display_mode, component)
    _all_values, color_grid, colorbar_label = _visualization_color_values(
        visualization,
        component,
        is_mode,
        geometry,
        show_stiffeners,
        show_girders,
        include_members=member_alpha > 0.0,
    )
    scale = _displacement_plot_scale(geometry, result, visualization, deformation_scale)
    skin_polygons = []
    skin_values = []
    for surface in visualization.get("skin_shell_surfaces") or ():
        polygon = _shell_surface_points(surface, scale)
        if len(polygon) < 3:
            continue
        value = _shell_surface_component_value(surface, component, is_mode=is_mode)
        skin_polygons.append(polygon)
        skin_values.append(value)

    shell_polygons = []
    shell_values = []
    for surface in visualization.get("shell_surfaces") or ():
        if member_alpha <= 0.0 or not _shell_surface_role_visible(surface, show_stiffeners, show_girders):
            continue
        polygon = _shell_surface_points(surface, scale)
        if len(polygon) < 3:
            continue
        value = _shell_surface_component_value(surface, component, is_mode=is_mode)
        shell_polygons.append(polygon)
        shell_values.append(value)

    surface_values = skin_values + shell_values
    value_range = _resolved_color_limits(_all_values, color_limits)
    facecolors, norm, cmap = _surface_facecolors(color_grid, colormap, surface_values, value_range)
    skin_colors = [cmap(norm(value)) for value in skin_values]
    shell_colors = [cmap(norm(value)) for value in shell_values]

    if visualization.get("type") == "cylinder":
        axial = _plot_grid_values(visualization.get("axial_m"))
        theta = _plot_grid_values(visualization.get("theta_rad"))
        radius = max(_safe_float(visualization.get("radius_m"), _safe_float(geometry.get("radius_m"), 1.0)), 1.0e-9)

        disps = visualization.get("displacements", {})
        dx_grid = _plot_grid_values(disps.get("disp_x", []))
        dy_grid = _plot_grid_values(disps.get("disp_y", []))
        dz_grid = _plot_grid_values(disps.get("disp_z", []))

        if not dx_grid or not dy_grid or not dz_grid:
            radial_displacement = _plot_grid_values(visualization.get("radial_displacement_m"))
            x = [
                [(radius + radial_displacement[row_index][col_index] * scale) * math.cos(theta[row_index][col_index])
                 for col_index in range(len(theta[row_index]))]
                for row_index in range(len(theta))
            ]
            y = [
                [(radius + radial_displacement[row_index][col_index] * scale) * math.sin(theta[row_index][col_index])
                 for col_index in range(len(theta[row_index]))]
                for row_index in range(len(theta))
            ]
            z = axial
        else:
            x = [
                [(radius * math.cos(theta[row_index][col_index]) + dx_grid[row_index][col_index] * scale)
                 for col_index in range(len(theta[row_index]))]
                for row_index in range(len(theta))
            ]
            y = [
                [(radius * math.sin(theta[row_index][col_index]) + dy_grid[row_index][col_index] * scale)
                 for col_index in range(len(theta[row_index]))]
                for row_index in range(len(theta))
            ]
            z = [
                [(axial[row_index][col_index] + dz_grid[row_index][col_index] * scale)
                 for col_index in range(len(axial[row_index]))]
                for row_index in range(len(axial))
            ]

        if show_plate:
            if skin_polygons:
                collection = Poly3DCollection(
                    skin_polygons,
                    facecolors=skin_colors,
                    edgecolors="#111827",
                    linewidths=0.25,
                    alpha=plate_alpha,
                )
                axis.add_collection3d(collection)
            else:
                axis.plot_surface(
                    np.asarray(x),
                    np.asarray(y),
                    np.asarray(z),
                    facecolors=np.asarray(facecolors),
                    rstride=1,
                    cstride=1,
                    linewidth=0.15,
                    antialiased=True,
                    shade=False,
                    alpha=plate_alpha,
                )
        if shell_polygons:
            collection = Poly3DCollection(
                shell_polygons,
                facecolors=shell_colors,
                edgecolors="#111827",
                linewidths=0.35,
                alpha=member_alpha,
            )
            axis.add_collection3d(collection)
        axis.set_xlabel("x [m]")
        axis.set_ylabel("y [m]")
        axis.set_zlabel("height [m]")
        _plot_member_lines(axis, visualization, scale, show_stiffeners, show_girders, member_alpha)
        _set_3d_axes_limits(axis, x, y, z)
        if show_sphere:
            _plot_rigid_sphere(axis, visualization, scale)
        try:
            axis.view_init(elev=18.0, azim=-45.0)
        except Exception:
            pass
    else:
        x = _plot_grid_values(visualization.get("x_m"))
        y = _plot_grid_values(visualization.get("y_m"))
        w = _plot_grid_values(visualization.get("w_m"))
        z = [[value * scale for value in row] for row in w]
        if show_plate:
            if skin_polygons:
                collection = Poly3DCollection(
                    skin_polygons,
                    facecolors=skin_colors,
                    edgecolors="#111827",
                    linewidths=0.25,
                    alpha=_clamped_alpha(plate_alpha, 1.0),
                )
                axis.add_collection3d(collection)
            else:
                axis.plot_surface(
                    np.asarray(x),
                    np.asarray(y),
                    np.asarray(z),
                    facecolors=np.asarray(facecolors),
                    rstride=1,
                    cstride=1,
                    linewidth=0.15,
                    antialiased=True,
                    shade=False,
                    alpha=_clamped_alpha(plate_alpha, 1.0),
                )
        if shell_polygons:
            collection = Poly3DCollection(
                shell_polygons,
                facecolors=shell_colors,
                edgecolors="#111827",
                linewidths=0.35,
                alpha=member_alpha,
            )
            axis.add_collection3d(collection)
        axis.set_xlabel("length [m]")
        axis.set_ylabel("width [m]")
        axis.set_zlabel("w x" + str(round(scale, 1)))
        _plot_member_lines(axis, visualization, scale, show_stiffeners, show_girders, member_alpha)
        _set_3d_axes_limits(axis, x, y, z)
        if show_sphere:
            _plot_rigid_sphere(axis, visualization, scale)

    _plot_geometry_dimension_annotations(axis, geometry, visualization.get("type") == "cylinder")
    axis.set_title(title)
    mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array(_all_grid_values(color_grid) + surface_values)
    figure.colorbar(mappable, ax=axis, shrink=0.68, pad=0.1, label=colorbar_label)


def _plot_base_geometry_surface(
        axis: Any,
        geometry: dict[str, Any],
        is_cylinder: bool,
        show_plate: bool = True,
        show_stiffeners: bool = True,
        show_girders: bool = True,
        plate_alpha: float = 1.0,
        member_alpha: float = 0.95,
) -> None:
    """Draw the unsolved model with the same visibility controls as results."""

    plate_alpha = _clamped_alpha(plate_alpha, 1.0)
    member_alpha = _clamped_alpha(member_alpha, 0.95)
    drew_anything = False

    if is_cylinder:
        radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-6)
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        theta = np.linspace(0.0, 2.0 * math.pi, 49)
        axial = np.linspace(0.0, length, 13)
        theta_grid, axial_grid = np.meshgrid(theta, axial)
        x_grid = radius * np.cos(theta_grid)
        y_grid = radius * np.sin(theta_grid)

        if show_plate and plate_alpha > 0.0:
            axis.plot_surface(
                x_grid,
                y_grid,
                axial_grid,
                color="#d8e2ea",
                edgecolor="#708090",
                linewidth=0.18,
                alpha=plate_alpha,
                antialiased=True,
                shade=False,
            )
            drew_anything = True

        if show_stiffeners and member_alpha > 0.0 and geometry.get("has_stiffener"):
            spacing = _safe_float(geometry.get("stiffener_spacing_m"), 0.0)
            if spacing > 0.0:
                count = max(1, representation_geometry.closed_loop_member_count(2.0 * math.pi * radius, spacing))
                section = geometry.get("stiffener_section") or {}
                web_height = max(_safe_float(section.get("web_height"), 0.1), 0.0)
                member_radius = max(radius - 0.5 * web_height, 1.0e-6)
                for index in range(count):
                    angle = 2.0 * math.pi * index / count
                    axis.plot(
                        [member_radius * math.cos(angle)] * 2,
                        [member_radius * math.sin(angle)] * 2,
                        [0.0, length],
                        color="#334155",
                        linewidth=1.3,
                        alpha=member_alpha,
                    )
                drew_anything = True

        if show_girders and member_alpha > 0.0 and geometry.get("has_girder"):
            spacing = _safe_float(geometry.get("girder_spacing_m"), 0.0)
            if spacing > 0.0:
                section = geometry.get("girder_section") or {}
                web_height = max(_safe_float(section.get("web_height"), 0.12), 0.0)
                member_radius = max(radius - 0.5 * web_height, 1.0e-6)
                ring_theta = np.linspace(0.0, 2.0 * math.pi, 97)
                for station in representation_geometry.centered_member_positions(
                        length,
                        spacing,
                        fallback_midpoint=True,
                        include_ends=True,
                ):
                    z_position = station
                    axis.plot(
                        member_radius * np.cos(ring_theta),
                        member_radius * np.sin(ring_theta),
                        np.full_like(ring_theta, z_position),
                        color="#7f1d1d",
                        linewidth=1.8,
                        alpha=member_alpha,
                    )
                drew_anything = True

        axis.set_xlabel("x [m]")
        axis.set_ylabel("y [m]")
        axis.set_zlabel("height [m]")
        try:
            axis.set_box_aspect((2.0 * radius, 2.0 * radius, length))
            axis.view_init(elev=18.0, azim=-45.0)
        except Exception:
            pass
    else:
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-6)
        x_grid, y_grid = np.meshgrid([0.0, length], [0.0, width])
        z_grid = np.zeros_like(x_grid)

        if show_plate and plate_alpha > 0.0:
            axis.plot_surface(
                x_grid,
                y_grid,
                z_grid,
                color="#d1d5db",
                edgecolor="#64748b",
                linewidth=0.3,
                alpha=plate_alpha,
                shade=False,
            )
            drew_anything = True

        if show_stiffeners and member_alpha > 0.0 and geometry.get("has_stiffener"):
            spacing = _safe_float(geometry.get("stiffener_spacing_m"), 0.0)
            section = geometry.get("stiffener_section") or {}
            web_height = max(_safe_float(section.get("web_height"), 0.1), 0.0)
            if spacing > 0.0:
                for y_position in representation_geometry.centered_member_positions(
                        width,
                        spacing,
                        fallback_midpoint=True,
                        include_ends=True,
                ):
                    axis.plot(
                        [0.0, length],
                        [y_position, y_position],
                        [web_height, web_height],
                        color="#334155",
                        linewidth=1.5,
                        alpha=member_alpha,
                    )
                drew_anything = True

        if show_girders and member_alpha > 0.0 and geometry.get("has_girder"):
            section = geometry.get("girder_section") or {}
            web_height = max(_safe_float(section.get("web_height"), 0.15), 0.0)
            spacing = _safe_float(geometry.get("girder_spacing_m"), 0.0)
            for x_position in representation_geometry.centered_member_positions(
                    length,
                    spacing,
                    fallback_midpoint=True,
                    include_ends=True,
            ):
                axis.plot(
                    [x_position, x_position],
                    [0.0, width],
                    [web_height, web_height],
                    color="#7f1d1d",
                    linewidth=2.0,
                    alpha=member_alpha,
                )
            drew_anything = True

        axis.set_xlabel("length [m]")
        axis.set_ylabel("width [m]")
        axis.set_zlabel("height [m]")
        try:
            axis.set_box_aspect((length, width, max(0.18 * min(length, width), 0.1)))
            axis.view_init(elev=22.0, azim=-55.0)
        except Exception:
            pass

    axis.set_title("Base model geometry")
    _plot_geometry_dimension_annotations(axis, geometry, is_cylinder)
    if not drew_anything:
        axis.text2D(0.08, 0.56, "All model display items are hidden.", transform=axis.transAxes)


def _history_component_series(
        histories: dict[Any, Any],
        requested_id: int | None,
        component: str,
) -> tuple[int | None, tuple[float, ...]]:
    if not isinstance(histories, dict) or not histories:
        return None, ()
    selected_id = requested_id if requested_id in histories else None
    if selected_id is None:
        try:
            selected_id = int(next(iter(histories)))
        except Exception:
            return None, ()
    values = histories.get(selected_id, {}) or histories.get(str(selected_id), {}) or {}
    if not isinstance(values, dict):
        return selected_id, ()
    series = tuple(float(value) for value in values.get(component, ()) or ())
    return selected_id, series


def _history_plot_units(component: str) -> tuple[str, float]:
    if component.endswith("_pa"):
        return "MPa", 1.0e-6
    if component.startswith("disp"):
        return "mm", 1000.0
    return "-", 1.0


def _plot_time_history(
        axis: Any,
        result: RuntimeFEMRunResult | None,
        component: str,
        probe_node_id: int | None = None,
        probe_element_id: int | None = None,
) -> None:
    time_domain = ((result.visualization if result is not None else {}) or {}).get("time_domain", {}) or {}
    times = tuple(float(value) for value in time_domain.get("times_s", ()) or ())
    if not times:
        axis.text(0.05, 0.55, "No time-domain history is available.", transform=axis.transAxes)
        axis.set_axis_off()
        return

    if component.startswith("disp"):
        selected_id, series = _history_component_series(
            time_domain.get("node_histories", {}) or {},
            probe_node_id,
            component,
        )
        target = "node"
    else:
        selected_id, series = _history_component_series(
            time_domain.get("element_histories", {}) or {},
            probe_element_id,
            component,
        )
        target = "element"

    if not series and (probe_element_id is not None or not component.startswith("disp")):
        snapshots = tuple(time_domain.get("snapshots", ()) or ())
        selected_element = probe_element_id
        if selected_element is None:
            for snapshot in snapshots:
                surfaces = tuple((snapshot or {}).get("skin_shell_surfaces", ()) or ()) + tuple(
                    (snapshot or {}).get("shell_surfaces", ()) or ())
                if surfaces:
                    try:
                        selected_element = int((surfaces[0] or {}).get("id"))
                    except Exception:
                        selected_element = None
                    break
        if selected_element is not None:
            values = []
            for snapshot in snapshots:
                found = None
                for surface in tuple((snapshot or {}).get("skin_shell_surfaces", ()) or ()) + tuple(
                        (snapshot or {}).get("shell_surfaces", ()) or ()):
                    try:
                        if int((surface or {}).get("id")) == int(selected_element):
                            found = _safe_float(((surface or {}).get("field_values", {}) or {}).get(component), 0.0)
                            break
                    except Exception:
                        continue
                values.append(0.0 if found is None else float(found))
            selected_id = int(selected_element)
            series = tuple(values)
            target = "element"

    if not series:
        axis.text(
            0.05,
            0.55,
            "No " + target + " history is available for " + component.replace("_", " ") + ".",
            transform=axis.transAxes,
        )
        axis.set_axis_off()
        return

    count = min(len(times), len(series))
    unit, scale = _history_plot_units(component)
    y_values = [float(value) * scale for value in series[:count]]
    axis.plot(times[:count], y_values, color="#2563eb", linewidth=1.8)
    axis.set_xlabel("time [s]")
    axis.set_ylabel(component.replace("_", " ") + " [" + unit + "]")
    axis.set_title("Time history: " + target + " " + str(selected_id))
    axis.grid(True, color="#d1d5db", linewidth=0.7)


def create_runtime_fem_result_figure(
        snapshot: RuntimeFEMLineSnapshot,
        result: RuntimeFEMRunResult | None = None,
        display_mode: str = "static",
        deformation_scale: float | None = None,
        show_plate: bool = True,
        show_stiffeners: bool = True,
        show_girders: bool = True,
        plate_alpha: float = 1.0,
        member_alpha: float = 0.95,
        colormap: str = "jet",
        component: str = "von_mises_pa",
        color_limits: tuple[float | None, float | None] | None = None,
        probe_node_id: int | None = None,
        probe_element_id: int | None = None,
        show_sphere: bool = True,
        base_sphere: dict[str, Any] | None = None,
        options: RuntimeFEMOptions | None = None,
) -> Figure:
    """Create an export figure or the runtime popup's 2D history plot.

    Maintained interactive 3D result views are rendered through the shared
    ANY3dView backend factory.  The non-history branch remains public for
    report/export compatibility and is not selected by the desktop viewer.
    """

    figure = Figure(figsize=(8.0, 4.1), dpi=100)
    if display_mode == "time_history":
        axis = figure.add_subplot(111)
        _plot_time_history(axis, result, component, probe_node_id, probe_element_id)
        figure.tight_layout()
        return figure

    geometry_ax = figure.add_subplot(111, projection="3d")
    geometry = runtime_geometry_summary(snapshot, options) if result is None else result.summary
    if result is None:
        geometry = runtime_geometry_projection(geometry)

    if result is None or not result.visualization:
        _plot_base_geometry_surface(
            geometry_ax,
            geometry,
            snapshot.is_cylinder,
            show_plate=show_plate,
            show_stiffeners=show_stiffeners,
            show_girders=show_girders,
            plate_alpha=plate_alpha,
            member_alpha=member_alpha,
        )
        if show_sphere and base_sphere:
            _plot_rigid_sphere(geometry_ax, base_sphere)
    else:
        _plot_visualization_surface(
            figure, geometry_ax, geometry, result, display_mode, deformation_scale,
            show_plate=show_plate, show_stiffeners=show_stiffeners, show_girders=show_girders,
            plate_alpha=plate_alpha, member_alpha=member_alpha, colormap=colormap,
            component=component, color_limits=color_limits, show_sphere=show_sphere,
        )

    figure.tight_layout()
    return figure


def create_runtime_fem_mesh_preview_figure(generated_geometry: dict) -> Figure:
    """Top-down preview of the generated mesh with active detail regions.

    Renders every shell element as an outline so local adaptive refinement is
    visible, marks point/impact detail radii and selected-panel regions, and
    titles the plot with concrete mesh metrics (element count and size range).
    """
    figure = Figure(figsize=(3.4, 2.6), dpi=100)
    axis = figure.add_subplot(111)
    nodes = {int(n["id"]): n["coords"] for n in generated_geometry.get("nodes", ()) or () if "id" in n}
    shells = generated_geometry.get("shells", ()) or ()
    from matplotlib.collections import LineCollection

    segments: list = []
    for shell in shells:
        ids = [int(i) for i in shell.get("node_ids", ()) or () if int(i) in nodes]
        corners = ids[:4] if len(ids) >= 4 else ids
        if len(corners) < 3:
            continue
        pts = [(float(nodes[i][0]), float(nodes[i][1])) for i in corners]
        for k in range(len(pts)):
            segments.append([pts[k], pts[(k + 1) % len(pts)]])
    if segments:
        axis.add_collection(LineCollection(segments, colors="#475569", linewidths=0.35))

    metrics = generated_geometry.get("mesh_metrics", {}) or {}
    adaptive = generated_geometry.get("adaptive_mesh", {}) or {}
    if adaptive.get("enabled"):
        sources = adaptive.get("sources") or [adaptive]
        for source in sources:
            if not isinstance(source, dict):
                continue
            if source.get("source") == "selected_panels":
                extent = float(source.get("extent_m", 0.0) or 0.0)
                for region in source.get("regions", ()) or ():
                    min_a = float(region.get("min_a", 0.0)) - extent
                    max_a = float(region.get("max_a", 0.0)) + extent
                    min_b = float(region.get("min_b", 0.0)) - extent
                    max_b = float(region.get("max_b", 0.0)) + extent
                    rect_x = [min_a, max_a, max_a, min_a, min_a]
                    rect_y = [min_b, min_b, max_b, max_b, min_b]
                    axis.plot(rect_x, rect_y, color="#f59e0b", linewidth=1.1, linestyle="--", zorder=5)
                continue
            point = source.get("impact_point_m") or source.get("point_m")
            if not point:
                continue
            cx, cy = float(point[0]), float(point[1])
            radius = float(source.get("extent_m", source.get("fine_radius_m", 0.0)) or 0.0)
            color = "#dc2626" if source.get("source") == "impact" else "#7c3aed"
            axis.plot([cx], [cy], marker="x", color=color, markersize=7, markeredgewidth=1.6, zorder=5)
            if radius > 0.0:
                theta = np.linspace(0.0, 2.0 * math.pi, 64)
                axis.plot(
                    cx + radius * np.cos(theta),
                    cy + radius * np.sin(theta),
                    color=color,
                    linewidth=0.9,
                    linestyle="--",
                    zorder=5,
                )

    all_x = [float(c[0]) for c in nodes.values()]
    all_y = [float(c[1]) for c in nodes.values()]
    if all_x and all_y:
        axis.set_xlim(min(all_x), max(all_x))
        axis.set_ylim(min(all_y), max(all_y))
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x [m]", fontsize=6)
    axis.set_ylabel("y [m]", fontsize=6)
    axis.tick_params(labelsize=6)
    count = int(metrics.get("shell_element_count", len(shells)))
    if metrics:
        title = f"{count} elements  |  {metrics.get('min_element_size_m', 0.0) * 1000:.0f}-{metrics.get('max_element_size_m', 0.0) * 1000:.0f} mm"
    else:
        title = f"{count} elements"
    if adaptive.get("enabled"):
        title += "  (adaptive)"
    axis.set_title(title, fontsize=7)
    figure.tight_layout(pad=0.5)
    return figure


def create_runtime_fem_geometry_preview_figure(
    snapshot: RuntimeFEMLineSnapshot,
    app: Any | None = None,
    options: RuntimeFEMOptions | None = None,
) -> Figure:
    """Create the 3D geometry preview shown in the runtime FEM popup."""

    if app is not None and hasattr(app, "create_prop_3d_figure_for_line"):
        try:
            preview = app.create_prop_3d_figure_for_line(snapshot.line_name)
            if isinstance(preview, tuple) and preview:
                figure = preview[0]
                if isinstance(figure, Figure):
                    return figure
        except Exception:
            pass

    geometry = runtime_geometry_projection(runtime_geometry_summary(snapshot, options))
    figure = Figure(figsize=(3.0, 2.05), dpi=100)
    axis = figure.add_subplot(111, projection="3d")

    if snapshot.is_cylinder:
        radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-6)
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        theta = np.linspace(0.0, 2.0 * math.pi, 38)
        z = np.linspace(0.0, length, 8)
        theta_grid, z_grid = np.meshgrid(theta, z)
        x_grid = radius * np.cos(theta_grid)
        y_grid = radius * np.sin(theta_grid)
        axis.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            color="#c7d2fe",
            edgecolor="#64748b",
            linewidth=0.12,
            alpha=0.78,
            shade=False,
        )
        axis.set_xlabel("x", fontsize=6)
        axis.set_ylabel("y", fontsize=6)
        axis.set_zlabel("L", fontsize=6)
        try:
            axis.set_box_aspect((1.0, 1.0, max(length / max(2.0 * radius, 1.0e-6), 0.35)))
        except Exception:
            pass
    else:
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-6)
        thickness = max(_safe_float(geometry.get("thickness_m"), 0.0), 0.0)
        x_grid, y_grid = np.meshgrid([0.0, length], [0.0, width])
        z_grid = np.zeros_like(x_grid)
        axis.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            color="#d1d5db",
            edgecolor="#64748b",
            linewidth=0.25,
            alpha=0.92,
            shade=False,
        )
        web_height = max(width * 0.18, thickness * 10.0, 0.08)
        if geometry.get("has_stiffener"):
            y_mid = 0.5 * width
            axis.plot([0.0, length], [y_mid, y_mid], [web_height, web_height], color="#334155", linewidth=2.0)
            axis.plot([0.0, length], [y_mid, y_mid], [0.0, web_height], color="#475569", linewidth=1.2)
        if geometry.get("has_girder"):
            x_mid = 0.5 * length
            axis.plot([x_mid, x_mid], [0.0, width], [web_height * 1.35, web_height * 1.35], color="#7f1d1d",
                      linewidth=2.0)
            axis.plot([x_mid, x_mid], [0.0, width], [0.0, web_height * 1.35], color="#991b1b", linewidth=1.2)
        axis.set_xlabel("L", fontsize=6)
        axis.set_ylabel("s", fontsize=6)
        axis.set_zlabel("h", fontsize=6)
        try:
            axis.set_box_aspect((length, width, max(web_height * 1.6, width * 0.18)))
        except Exception:
            pass

    axis.set_title("3D section view", fontsize=8)
    axis.tick_params(labelsize=5, pad=0)
    try:
        axis.view_init(elev=22, azim=-55)
    except Exception:
        pass
    figure.tight_layout(pad=0.3)
    return figure


def format_runtime_fem_result(result: RuntimeFEMRunResult) -> str:
    """Format runtime FEM result text for the popup."""

    summary = result.summary
    lines = [
        "Runtime FEM status: " + result.status.replace("_", " "),
        "",
        "Line: " + str(summary.get("line", "")),
        "Geometry: " + str(summary.get("geometry", "")),
        "Mesh fidelity: " + str(summary.get("mesh_fidelity", "")),
        "Shell element: " + str(summary.get("shell_element_order", "")),
        "Beam element: " + str(summary.get("beam_element_order", "")),
        "Member model: " + str(summary.get("member_model", "")),
        "Member side: " + ("opposite (main-app setting)" if summary.get("members_opposite_side") else "default"),
        "Boundary condition: " + str(summary.get("boundary_condition", "")),
        "Symmetry: " + str(summary.get("symmetry_mode", "")),
        "Analysis type: " + str(summary.get("analysis_type", "")),
        "Buckling type: " + str(summary.get("buckling_analysis_type", "")),
        "Runtime solver: " + str(summary.get("runtime_solver", "stepwise")),
        "Linear solver: " + str(summary.get("solver_type", "")),
        "Pressure [Pa]: " + str(round(_safe_float(summary.get("pressure_pa")), 3)),
        "Pressure side: " + str(summary.get("pressure_side", summary.get("pressure_direction", ""))),
        "Axial force [N]: " + str(round(_safe_float(summary.get("axial_force_n")), 3)),
        "Enforced disp X [m]: " + str(round(_safe_float(summary.get("enforced_displacement_x_m")), 6)),
        "Enforced disp Y [m]: " + str(round(_safe_float(summary.get("enforced_displacement_y_m")), 6)),
        "Enforced disp Z [m]: " + str(round(_safe_float(summary.get("enforced_displacement_z_m")), 6)),
        "Mesh size override [m]: " + str(round(_safe_float(summary.get("mesh_size_m")), 4)),
        "Panel detail mesh: "
        + (
            str(_safe_int(summary.get("local_refinement_patch_count"), 0))
            + " region(s), fine "
            + str(round(_safe_float(summary.get("local_refinement_fine_size_m")), 4))
            + " m, growth "
            + str(round(_safe_float(summary.get("local_refinement_growth_factor"), 1.0), 3))
            if bool(summary.get("local_refinement_enabled"))
            else "off"
        ),
        "Point detail mesh: "
        + (
            "("
            + ", ".join(
                str(round(_safe_float(value), 3)) for value in (summary.get("point_refinement_point_m") or (0.0, 0.0)))
            + ") m, radius "
            + str(round(_safe_float(summary.get("point_refinement_extent_m")), 4))
            + " m, growth "
            + str(round(_safe_float(summary.get("point_refinement_growth_factor"), 1.0), 3))
            if bool(summary.get("point_refinement_enabled"))
            else "off"
        ),
        "Top/bottom moment [Nm]: " + str(round(_safe_float(summary.get("top_bottom_moment_nm")), 3)),
        "Torsional moment [Nm]: " + str(round(_safe_float(summary.get("torsional_moment_nm")), 3)),
        "Shear force [N]: " + str(round(_safe_float(summary.get("shear_force_n")), 3)),
        "Acceleration [m/s2]: " + _format_acceleration_summary(summary.get("acceleration_m_s2")),
        "Added mass [kg]: " + _format_added_mass_summary(summary),
        "Include stiffener beams: " + str(bool(summary.get("include_stiffeners"))),
        "Include girder/frame beams: " + str(bool(summary.get("include_girders"))),
        "Include top/bottom lid: " + str(bool(summary.get("include_end_lids"))),
        "Member orientation: " + str(summary.get("member_orientation", "")),
        "Stiffener eccentricity [m]: " + str(round(_safe_float(summary.get("stiffener_eccentricity_m")), 6)),
        "Girder eccentricity [m]: " + str(round(_safe_float(summary.get("girder_eccentricity_m")), 6)),
        "Material model: " + str(summary.get("material_model", "")),
        "Steel grade/class: " + str(summary.get("steel_grade", "")) + " / " + str(
            summary.get("steel_thickness_class", "")),
        "Material E [GPa]: " + str(round(_safe_float(summary.get("elastic_modulus_pa")) / 1.0e9, 3)),
        "Poisson ratio: " + str(round(_safe_float(summary.get("poisson_ratio")), 4)),
        "Yield stress [MPa]: " + str(round(_safe_float(summary.get("yield_stress_pa")) / 1.0e6, 3)),
        "Stress percentile: " + str(round(_safe_float(summary.get("stress_percentile")), 2)),
        "Nonlinear max LF / steps: "
        + str(round(_safe_float(summary.get("nonlinear_max_load_factor")), 3))
        + " / "
        + str(_safe_int(summary.get("nonlinear_steps"), 0)),
        "Nonlinear layers / max iterations: "
        + str(_safe_int(summary.get("nonlinear_layers"), 0))
        + " / "
        + str(_safe_int(summary.get("nonlinear_max_iterations"), 0)),
        "Nonlinear solution control: " + str(summary.get("nonlinear_solution_control", "newton force control")),
        "Nonlinear static kinematics: " + str(summary.get("nonlinear_static_kinematics", "von_karman")),
        "Nonlinear convergence profile: " + str(summary.get("nonlinear_convergence_profile", "auto")),
        "Nonlinear assembly threads: " + (
            "auto" if _safe_int(summary.get("nonlinear_assembly_threads"), 0) <= 0 else str(
                _safe_int(summary.get("nonlinear_assembly_threads"), 0))),
        "Consistent beam mass: " + str(bool(summary.get("beam_consistent_mass_enabled"))),
        "Deformation plot scale: " + ("auto" if _safe_float(summary.get("deformation_scale"), 0.0) <= 0.0 else str(
            round(_safe_float(summary.get("deformation_scale")), 3))),
        "Recovery history: " + str(summary.get("recovery_history_mode", "full")),
        "Memory limit [MB]: " + ("none" if _safe_float(summary.get("memory_limit_mb"), 0.0) <= 0.0 else str(
            round(_safe_float(summary.get("memory_limit_mb")), 1))),
        "Custom load/BC mode: " + str(bool(summary.get("custom_load_bc_enabled"))),
        "Buckling modes: " + str(summary.get("num_buckling_modes", "")),
        "Max displacement [mm]: " + str(round(1000.0 * _safe_float(summary.get("max_displacement_m")), 4)),
    ]
    if summary.get("custom_load_bc_enabled"):
        lines.append(
            "Custom loads add to imported/generated loads: " + str(bool(summary.get("custom_loads_add_to_imported"))))
        lines.append("Custom nullspace boundary: " + str(bool(summary.get("custom_use_nullspace_projection"))))
        lines.append("Allow unbalanced free-free loads: " + str(bool(summary.get("allow_unbalanced_free_free"))))
        lines.append("Custom pressure [Pa]: " + str(round(_safe_float(summary.get("custom_pressure_pa")), 3)))
        lines.append("Selected pressure panels: " + str(_safe_int(summary.get("custom_pressure_patch_count"), 0)))
        lines.append("Selected pressure panel area [m2]: " + str(
            round(_safe_float(summary.get("custom_pressure_patch_area_m2")), 4)))
        lines.append("Selected edge segments: " + str(_safe_int(summary.get("custom_edge_segment_count"), 0)))
        lines.append(
            "Selected edge load [N/m]: " + str(round(_safe_float(summary.get("custom_selected_edge_load_n_per_m")), 3)))
        if str(summary.get("geometry", "")).lower().startswith("cylinder"):
            lines.extend(
                [
                    "Cylinder lower/upper support: "
                    + str(summary.get("cylinder_lower_support", ""))
                    + " / "
                    + str(summary.get("cylinder_upper_support", "")),
                    "Cylinder lower/upper edge load [N/m]: "
                    + str(round(_safe_float(summary.get("cylinder_lower_edge_load_n_per_m")), 3))
                    + " / "
                    + str(round(_safe_float(summary.get("cylinder_upper_edge_load_n_per_m")), 3)),
                ]
            )
        else:
            lines.extend(
                [
                    "Plate edge supports x0/x1/y0/y1: "
                    + ", ".join(
                        str(summary.get(key, ""))
                        for key in ("plate_edge_x0_support", "plate_edge_x1_support", "plate_edge_y0_support",
                                    "plate_edge_y1_support")
                    ),
                    "Plate edge loads x0/x1/y0/y1 [N/m]: "
                    + ", ".join(
                        str(round(_safe_float(summary.get(key)), 3))
                        for key in (
                            "plate_edge_x0_load_n_per_m",
                            "plate_edge_x1_load_n_per_m",
                            "plate_edge_y0_load_n_per_m",
                            "plate_edge_y1_load_n_per_m",
                        )
                    ),
                ]
            )
    if summary.get("imperfection_enabled"):
        lines.extend(
            [
                "",
                "Geometric imperfection input:",
                " - shape: " + str(summary.get("imperfection_shape", "")),
                " - amplitude [mm]: "
                + ("standard default" if _safe_float(summary.get("imperfection_amplitude_m"), 0.0) <= 0.0 else str(
                    round(1000.0 * _safe_float(summary.get("imperfection_amplitude_m")), 4))),
                " - waves A/B: " + str(_safe_int(summary.get("imperfection_wave_a"), 1)) + " / " + str(
                    _safe_int(summary.get("imperfection_wave_b"), 1)),
            ]
        )
    if summary.get("fracture_enabled"):
        lines.extend(
            [
                "",
                "Nonlinear static fracture input:",
                " - plastic strain threshold: " + str(round(_safe_float(summary.get("fracture_strain_threshold")), 6)),
                " - residual stiffness fraction: " + str(
                    round(_safe_float(summary.get("fracture_residual_stiffness_fraction")), 10)),
                " - max deleted fraction: " + str(round(_safe_float(summary.get("fracture_max_deleted_fraction")), 6)),
                " - min load factor: " + str(round(_safe_float(summary.get("fracture_min_load_factor")), 6)),
            ]
        )
    if summary.get("custom_time_domain_enabled"):
        lines.extend(
            [
                "",
                "Custom time-domain input:",
                " - pressure [Pa]: " + str(round(_safe_float(summary.get("custom_pressure_pa")), 3)),
                " - duration / total time [s]: "
                + str(round(_safe_float(summary.get("custom_time_domain_duration_s")), 6))
                + " / "
                + str(round(_safe_float(summary.get("custom_time_domain_total_time_s")), 6)),
                " - dt [s]: " + str(round(_safe_float(summary.get("custom_time_domain_dt_s")), 8)),
                " - result interval [s]: " + (
                    "auto" if _safe_float(summary.get("custom_time_domain_result_interval_s"), 0.0) <= 0.0
                    else str(round(_safe_float(summary.get("custom_time_domain_result_interval_s")), 8))
                ),
                " - selected patches: " + str(_safe_int(summary.get("custom_pressure_patch_count"), 0)),
                " - selected patch area [m2]: " + str(
                    round(_safe_float(summary.get("custom_pressure_patch_area_m2")), 4)),
                " - include static load in time domain: " + str(
                    bool(summary.get("custom_time_domain_include_static_load"))),
            ]
        )
    if summary.get("collision_enabled"):
        lines.extend(
            [
                "",
                "Rigid-sphere collision input:",
                " - mass/radius: "
                + str(round(_safe_float(summary.get("collision_mass_kg")), 6))
                + " kg / "
                + str(round(_safe_float(summary.get("collision_radius_m")), 6))
                + " m",
                " - start [m]: " + ", ".join(
                    str(round(_safe_float(v), 6)) for v in summary.get("collision_start_m", ()) or ()),
                " - vector: " + ", ".join(
                    str(round(_safe_float(v), 6)) for v in summary.get("collision_vector", ()) or ()),
                " - speed [m/s]: " + str(round(_safe_float(summary.get("collision_speed_mps")), 6)),
                " - time setup: " + str(summary.get("collision_time_mode", "auto")),
                " - total time / dt [s]: "
                + str(round(_safe_float(summary.get("collision_total_time_s")), 8))
                + " / "
                + str(round(_safe_float(summary.get("collision_dt_s")), 8)),
                " - auto steps/radius, post radii: "
                + str(round(_safe_float(summary.get("collision_auto_steps_per_radius")), 3))
                + " / "
                + str(round(_safe_float(summary.get("collision_auto_post_contact_radii")), 3)),
                " - bounce-back stop hold [s]: "
                + str(round(_safe_float(summary.get("collision_bounce_back_time_s")), 8)),
                " - contact surface: " + str(summary.get("collision_contact_surface", "")),
                " - direct beam/stiffener contact: " + str(bool(summary.get("collision_beam_contact_enabled"))),
                " - material nonlinear impact: " + str(bool(summary.get("collision_material_nonlinear_enabled"))),
                " - nonlinear impact kinematics: " + str(summary.get("collision_nonlinear_kinematics", "von_karman")),
                " - impact detail mesh: "
                + (
                    "fine "
                    + str(round(_safe_float(summary.get("collision_adaptive_fine_size_m")), 4))
                    + " m, radius "
                    + str(round(_safe_float(summary.get("collision_adaptive_extent_m")), 4))
                    + " m, growth "
                    + str(round(_safe_float(summary.get("collision_adaptive_growth_factor"), 1.0), 3))
                    if bool(summary.get("collision_adaptive_mesh_enabled"))
                    else "off"
                ),
                " - damage active: " + str(bool(summary.get("collision_damage_enabled"))),
            ]
        )
    if (
            str(summary.get("runtime_solver", "stepwise")).lower() != "stepwise"
            or _safe_float(summary.get("buckling_shift_load_factor"), 0.0) > 0.0
            or _safe_float(summary.get("buckling_min_load_factor"), 0.0) > 0.0
            or _safe_float(summary.get("buckling_max_load_factor"), 0.0) > 0.0
            or bool(summary.get("buckling_allow_dense_fallback"))
    ):
        lines.extend(
            [
                "",
                "Solver validity controls:",
                " - runtime path: " + str(summary.get("runtime_solver", "stepwise")),
                " - buckling shift/range: "
                + str(round(_safe_float(summary.get("buckling_shift_load_factor")), 4))
                + " / "
                + str(round(_safe_float(summary.get("buckling_min_load_factor")), 4))
                + "-"
                + str(round(_safe_float(summary.get("buckling_max_load_factor")), 4)),
                " - repeated-mode tolerance: " + str(
                    round(_safe_float(summary.get("buckling_repeated_tolerance"), 1.0e-3), 6)),
                " - dense fallback: " + str(bool(summary.get("buckling_allow_dense_fallback"))),
            ]
        )
    if result.buckling_factors:
        lines.append("Critical load factor: " + str(round(result.buckling_factors[0], 4)))
    warmup_status = str(summary.get("kernel_warmup_status", "") or "")
    if warmup_status:
        orders = ", ".join(str(order) for order in summary.get("kernel_warmup_shell_orders", ()) or ())
        lines.extend(["", "FE solver kernel warmup:"])
        lines.append(" - status: " + warmup_status.replace("_", " "))
        if orders:
            lines.append(" - shell orders: " + orders)
        if _safe_float(summary.get("kernel_warmup_total_seconds"), 0.0) > 0.0:
            lines.append(" - time [s]: " + str(round(_safe_float(summary.get("kernel_warmup_total_seconds")), 3)))
        lines.append(
            " - JIT: " + ("enabled" if bool(summary.get("kernel_warmup_jit_enabled")) else "disabled or unavailable"))
        if summary.get("kernel_warmup_parallel_threads") is not None:
            lines.append(" - threads: " + str(summary.get("kernel_warmup_parallel_threads")))
        lines.append(" - max matrix difference: " + str(
            round(_safe_float(summary.get("kernel_warmup_max_matrix_difference_norm")), 12)))
    mesh_info = summary.get("mesh_info") or {}
    if mesh_info:
        lines.extend([
            "",
            "FE mesh:",
            " - nodes: " + str(mesh_info.get("nodes", 0)),
            " - shells: " + str(mesh_info.get("shells", 0)),
            " - beams: " + str(mesh_info.get("beams", 0)),
            " - rigid lids: " + str(mesh_info.get("rigid_lids", 0)),
            " - shell order: " + str(mesh_info.get("shell_order", "")),
            " - beam order: " + str(mesh_info.get("beam_order", "")),
        ])
        for key in ("max_x_edge_m", "max_y_edge_m", "max_circumferential_edge_m", "max_axial_edge_m"):
            if key in mesh_info:
                lines.append(" - " + key + ": " + str(round(_safe_float(mesh_info.get(key)), 4)))
        for key in (
                "skin_shells",
                "member_shells",
                "invalid_shell_quality_count",
                "max_shell_aspect_ratio",
                "mean_shell_aspect_ratio",
                "max_shell_skew_deg",
                "max_shell_warp",
                "min_shell_area_m2",
        ):
            if key in mesh_info:
                lines.append(" - " + key + ": " + str(round(_safe_float(mesh_info.get(key)), 6)))
        if mesh_info.get("mesh_quality_warnings"):
            lines.append(" - mesh_quality_warnings: " + str(mesh_info.get("mesh_quality_warnings")))
        for key in (
                "mesh_pressure_patch_boundary_breaks",
                "mesh_pressure_patch_min_axial_width_m",
                "mesh_pressure_patch_min_circumferential_width_m",
        ):
            if key in mesh_info:
                value = mesh_info.get(key)
                if isinstance(value, (int, float)):
                    value = round(_safe_float(value), 6)
                lines.append(" - " + key + ": " + str(value))
    prestress = summary.get("prestress_summary") or {}
    if prestress:
        constraint_method = str(prestress.get("constraint_method", "") or "")
        if constraint_method:
            lines.extend(["", "Linear constraint handling:"])
            lines.append(" - method: " + constraint_method)
            if _safe_float(prestress.get("nullspace_projection"), 0.0) > 0.0:
                lines.append(" - nullspace projection: used")
                lines.append(" - remaining rigid-body modes: " + str(_safe_int(prestress.get("nullspace_rank"), 0)))
                lines.append(" - relative load imbalance: " + str(
                    round(_safe_float(prestress.get("relative_rigid_body_load_imbalance")), 6)))
                lines.append(
                    " - meaning: remaining rigid-body modes were projected out and any rigid-body load imbalance was carried as generalized balancing reactions.")
            else:
                lines.append(" - nullspace projection: not used")
        lines.extend(["", "Recovered prestress / reference state:"])
        material_keys = {
            "material_model",
            "steel_grade",
            "steel_thickness_class",
            "sigma_prop_pa",
            "sigma_yield_pa",
            "sigma_yield_2_pa",
            "eps_p_y1",
            "eps_p_y2",
            "hardening_K_pa",
            "hardening_n",
        }
        nonlinear_static_keys = {
            "nonlinear_static_control",
            "nonlinear_static_status",
            "nonlinear_static_load_factor",
            "nonlinear_static_peak_load_factor",
            "nonlinear_static_peak_step",
            "nonlinear_static_initial_arc_increment",
            "nonlinear_static_steps",
            "nonlinear_static_total_iterations",
            "nonlinear_static_kinematics",
            "nonlinear_static_layers",
            "nonlinear_static_max_plastic_strain",
        }
        fracture_keys = {
            "fracture_enabled",
            "fracture_deleted_count",
            "fracture_max_utilization",
            "fracture_first_deletion_load_factor",
        }
        imperfection_keys = {
            "imperfection_status",
            "imperfection_kind",
            "imperfection_amplitude_m",
            "imperfection_max_offset_m",
            "imperfection_waves_a",
            "imperfection_waves_b",
        }
        custom_time_domain_keys = {
            "custom_time_domain_status",
            "custom_time_domain_pressure_pa",
            "custom_time_domain_selected_shells",
            "custom_time_domain_peak_displacement_m",
            "custom_time_domain_peak_von_mises_pa",
            "custom_time_domain_result_interval_s",
            "custom_time_domain_saved_steps",
        }
        collision_keys = {
            "collision_status",
            "collision_time_mode",
            "collision_resolved_dt_s",
            "collision_resolved_total_time_s",
            "collision_estimated_arrival_time_s",
            "collision_contact_penalty_stiffness_n_per_m",
            "collision_contact_penalty_basis",
            "collision_target_penetration_m",
            "collision_stop_reason",
            "collision_separation_stop_time_s",
            "collision_auto_requested_total_time_s",
            "collision_auto_impact_window_s",
            "collision_peak_contact_force_n",
            "collision_max_penetration_m",
            "collision_max_penetration_ratio",
            "collision_contact_duration_s",
            "collision_sphere_momentum_balance_error",
            "collision_saved_steps",
            "collision_damage_enabled",
            "collision_material_nonlinear_enabled",
            "collision_nonlinear_kinematics",
            "collision_nonlinear_assembly_threads",
            "collision_beam_contact_enabled",
            "collision_nonlinear_status",
            "collision_nonlinear_iterations",
            "collision_nonlinear_cutbacks",
            "collision_nonlinear_max_plastic_strain",
            "collision_plastic_damage_threshold",
            "collision_deleted_shell_elements",
            "collision_deleted_eroded_elements",
            "collision_energy_initial_j",
            "collision_energy_final_j",
            "collision_sphere_kinetic_initial_j",
            "collision_sphere_kinetic_final_j",
            "collision_energy_max_relative_drift",
            "collision_adaptive_cutback_retries",
            "collision_solution_control",
            "collision_arc_length_applicability",
            "collision_failure_time_s",
            "collision_failure_dt_s",
            "collision_failure_iterations",
            "collision_failure_force_change_n",
            "collision_failure_effective_force_tolerance_n",
            "collision_failure_penetration_change_m",
            "collision_failure_max_penetration_m",
            "collision_failure_active_element_ids",
            "collision_failure_residual_norm",
            "collision_failure_effective_residual_tolerance_n",
            "collision_failure_displacement_increment_m",
            "impact_damage_max_utilization",
            "impact_damage_deleted_count",
        }
        runtime_keys = {
            "runtime_solver",
            "allow_unbalanced_free_free",
            "recovery_history_mode",
            "recovery_threads",
            "memory_limit_mb",
            "buckling_solver_status",
            "buckling_modes_returned",
            "buckling_repeated_groups",
            "buckling_shift_load_factor",
            "buckling_min_load_factor",
            "buckling_max_load_factor",
            "buckling_allow_dense_fallback",
            "buckling_mesh_status",
            "buckling_mesh_active_nodes",
            "buckling_mesh_active_elements",
            "buckling_mesh_estimated_half_waves",
            "buckling_mesh_elements_per_half_wave",
            "capacity_workflow_status",
            "capacity_workflow_capacity_factor",
            "capacity_workflow_critical_load_factor",
            "capacity_workflow_mesh_status",
            "capacity_workflow_elements_per_half_wave",
        }
        special_keys = {
            "nonlinear_status",
            "nonlinear_limit_factor",
            "nonlinear_steps",
            "constraint_method",
            "constraint_mode",
            "nullspace_projection",
            "nullspace_rank",
            "relative_rigid_body_load_imbalance",
            "rigid_body_load_imbalance_norm",
            *material_keys,
            *nonlinear_static_keys,
            *fracture_keys,
            *imperfection_keys,
            *custom_time_domain_keys,
            *collision_keys,
            *runtime_keys,
        }
        if prestress.get("material_model"):
            lines.extend(["", "DNV-RP-C208 material curve:"])
            lines.append(" - grade: " + str(prestress.get("steel_grade", "")))
            lines.append(" - thickness class: " + str(prestress.get("steel_thickness_class", "")))
            lines.append(" - sigma_prop/yield/yield2 [MPa]: " + " / ".join(
                str(round(_safe_float(prestress.get(key)) / 1.0e6, 3))
                for key in ("sigma_prop_pa", "sigma_yield_pa", "sigma_yield_2_pa")
            ))
            lines.append(" - eps_p_y1/eps_p_y2: " + str(prestress.get("eps_p_y1", "")) + " / " + str(
                prestress.get("eps_p_y2", "")))
            lines.append(
                " - K [MPa] / n: " + str(round(_safe_float(prestress.get("hardening_K_pa")) / 1.0e6, 3)) + " / " + str(
                    prestress.get("hardening_n", "")))
        runtime_solver = str(prestress.get("runtime_solver", summary.get("runtime_solver", "")) or "")
        if runtime_solver:
            lines.extend(["", "Runtime solver provenance:"])
            lines.append(" - runtime path: " + runtime_solver)
            lines.append(" - buckling status: " + str(prestress.get("buckling_solver_status", "")))
            lines.append(" - modes returned: " + str(_safe_int(prestress.get("buckling_modes_returned"), 0)))
            lines.append(" - repeated mode groups: " + str(_safe_int(prestress.get("buckling_repeated_groups"), 0)))
            if _safe_float(prestress.get("allow_unbalanced_free_free"), 0.0) > 0.0:
                lines.append(" - free-free load handling: explicit generalized balancing reactions allowed")
            lines.append(" - recovery history: " + str(
                prestress.get("recovery_history_mode", summary.get("recovery_history_mode", "full"))))
            if _safe_float(prestress.get("memory_limit_mb"), 0.0) > 0.0:
                lines.append(" - memory limit [MB]: " + str(round(_safe_float(prestress.get("memory_limit_mb")), 1)))
            if prestress.get("buckling_mesh_status"):
                lines.append(" - mode mesh adequacy: " + str(prestress.get("buckling_mesh_status", "")))
                lines.append(" - active elements per estimated half-wave: " + str(
                    round(_safe_float(prestress.get("buckling_mesh_elements_per_half_wave")), 3)))
                lines.append(" - estimated half-waves: " + str(
                    _safe_int(prestress.get("buckling_mesh_estimated_half_waves"), 0)))
        capacity_status = str(prestress.get("capacity_workflow_status", "") or "")
        if capacity_status:
            lines.extend(["", "ANYsolver capacity workflow:"])
            lines.append(" - status: " + capacity_status.replace("_", " "))
            lines.append(
                " - capacity factor: " + str(round(_safe_float(prestress.get("capacity_workflow_capacity_factor")), 4)))
            critical = _safe_float(prestress.get("capacity_workflow_critical_load_factor"), 0.0)
            lines.append(
                " - eigenvalue critical factor: " + ("not available" if critical <= 0.0 else str(round(critical, 4))))
            lines.append(" - mode mesh adequacy: " + str(prestress.get("capacity_workflow_mesh_status", "")))
            lines.append(" - active elements per estimated half-wave: " + str(
                round(_safe_float(prestress.get("capacity_workflow_elements_per_half_wave")), 3)))
            lines.append(
                " - meaning: linear static prestress, eigenmode buckling, stress-free imperfection and nonlinear static capacity were run as one traceable workflow.")
        nonlinear_static_status = str(prestress.get("nonlinear_static_status", "") or "")
        if nonlinear_static_status:
            lines.extend(["", "Incremental nonlinear static solve:"])
            control_mode = str(prestress.get("nonlinear_static_control",
                                             summary.get("nonlinear_solution_control", "newton force control")))
            lines.append(" - control: " + control_mode)
            lines.append(" - kinematics: " + str(
                prestress.get("nonlinear_static_kinematics", summary.get("nonlinear_static_kinematics", "von_karman"))))
            lines.append(" - status: " + nonlinear_static_status.replace("_", " "))
            lines.append(" - last converged load factor: " + str(
                round(_safe_float(prestress.get("nonlinear_static_load_factor")), 4)))
            if _safe_float(prestress.get("nonlinear_static_peak_load_factor"), 0.0) > 0.0:
                lines.append(" - peak load factor: " + str(
                    round(_safe_float(prestress.get("nonlinear_static_peak_load_factor")), 4)))
            if _safe_float(prestress.get("nonlinear_static_peak_step"), -1.0) >= 0.0:
                lines.append(" - peak step: " + str(_safe_int(prestress.get("nonlinear_static_peak_step"), 0)))
            lines.append(" - completed steps: " + str(_safe_int(prestress.get("nonlinear_static_steps"), 0)))
            lines.append(
                " - Newton iterations: " + str(_safe_int(prestress.get("nonlinear_static_total_iterations"), 0)))
            if _safe_float(prestress.get("nonlinear_static_assembly_threads"), 0.0) > 0.0:
                lines.append(" - resolved assembly threads: " + str(
                    _safe_int(prestress.get("nonlinear_static_assembly_threads"), 0)))
            lines.append(" - through-thickness layers: " + str(_safe_int(prestress.get("nonlinear_static_layers"), 0)))
            lines.append(" - max equivalent plastic strain: " + str(
                round(_safe_float(prestress.get("nonlinear_static_max_plastic_strain")), 6)))
            if nonlinear_static_status == "completed":
                lines.append(
                    " - interpretation: all requested proportional load was reached; this is not necessarily a collapse load.")
            elif nonlinear_static_status == "stopped_at_limit":
                lines.append(
                    " - interpretation: the adaptive Newton solve stopped at the last stable converged load increment.")
            if _safe_float(prestress.get("fracture_enabled"), 0.0) > 0.0:
                lines.append(
                    " - fracture deleted elements: " + str(_safe_int(prestress.get("fracture_deleted_count"), 0)))
                lines.append(" - fracture max utilization: " + str(
                    round(_safe_float(prestress.get("fracture_max_utilization")), 6)))
                first_lf = _safe_float(prestress.get("fracture_first_deletion_load_factor"), 0.0)
                if first_lf > 0.0:
                    lines.append(" - first deletion load factor: " + str(round(first_lf, 4)))
        imperfection_status = str(prestress.get("imperfection_status", "") or "")
        if imperfection_status:
            lines.extend(["", "Applied geometric imperfection:"])
            lines.append(" - status: " + imperfection_status)
            lines.append(" - kind: " + str(prestress.get("imperfection_kind", "")))
            lines.append(" - input amplitude [mm]: " + str(
                round(1000.0 * _safe_float(prestress.get("imperfection_amplitude_m")), 4)))
            lines.append(" - max offset [mm]: " + str(
                round(1000.0 * _safe_float(prestress.get("imperfection_max_offset_m")), 4)))
            lines.append(" - waves A/B: " + str(_safe_int(prestress.get("imperfection_waves_a"), 0)) + " / " + str(
                _safe_int(prestress.get("imperfection_waves_b"), 0)))
            lines.append(
                " - meaning: the coordinates were offset before solving, so zero displacement in the imperfect model is stress free.")
        custom_time_domain_status = str(prestress.get("custom_time_domain_status", "") or "")
        if custom_time_domain_status:
            lines.extend(["", "Custom time-domain response:"])
            lines.append(" - status: " + custom_time_domain_status)
            lines.append(
                " - selected shell elements: " + str(_safe_int(prestress.get("custom_time_domain_selected_shells"), 0)))
            lines.append(" - peak displacement [mm]: " + str(
                round(1000.0 * _safe_float(prestress.get("custom_time_domain_peak_displacement_m")), 4)))
            lines.append(" - peak von Mises [MPa]: " + str(
                round(_safe_float(prestress.get("custom_time_domain_peak_von_mises_pa")) / 1.0e6, 3)))
            if _safe_float(prestress.get("custom_time_domain_saved_steps"), 0.0) > 0.0:
                lines.append(
                    " - saved result steps: " + str(_safe_int(prestress.get("custom_time_domain_saved_steps"), 0)))
            if _safe_float(prestress.get("custom_time_domain_result_interval_s"), 0.0) > 0.0:
                lines.append(" - result interval [s]: " + str(
                    round(_safe_float(prestress.get("custom_time_domain_result_interval_s")), 8)))
            lines.append(
                " - meaning: this is a linear Newmark response to the prescribed pressure pulse; it is reported separately from the static buckling prestress.")
        collision_status = str(prestress.get("collision_status", "") or "")
        if collision_status:
            lines.extend(["", "Rigid-sphere collision response:"])
            lines.append(" - status: " + collision_status.replace("_", " "))
            lines.append(
                " - time mode: " + str(prestress.get("collision_time_mode", summary.get("collision_time_mode", ""))))
            if _safe_float(prestress.get("collision_resolved_dt_s"), 0.0) > 0.0:
                lines.append(
                    " - resolved dt [s]: " + str(round(_safe_float(prestress.get("collision_resolved_dt_s")), 9)))
            if _safe_float(prestress.get("collision_resolved_total_time_s"), 0.0) > 0.0:
                lines.append(" - resolved total time [s]: " + str(
                    round(_safe_float(prestress.get("collision_resolved_total_time_s")), 6)))
            if _safe_float(prestress.get("collision_estimated_arrival_time_s"), 0.0) > 0.0:
                lines.append(" - estimated arrival [s]: " + str(
                    round(_safe_float(prestress.get("collision_estimated_arrival_time_s")), 6)))
            if _safe_float(prestress.get("collision_contact_penalty_stiffness_n_per_m"), 0.0) > 0.0:
                lines.append(
                    " - contact penalty [N/m]: "
                    + str(round(_safe_float(prestress.get("collision_contact_penalty_stiffness_n_per_m")), 3))
                    + " ("
                    + str(prestress.get("collision_contact_penalty_basis", ""))
                    + ")"
                )
            if _safe_float(prestress.get("collision_target_penetration_m"), 0.0) > 0.0:
                lines.append(" - target penetration [mm]: " + str(
                    round(1000.0 * _safe_float(prestress.get("collision_target_penetration_m")), 4)))
            if str(prestress.get("collision_stop_reason", "") or ""):
                lines.append(" - stop reason: " + str(prestress.get("collision_stop_reason", "")).replace("_", " "))
            if _safe_float(prestress.get("collision_separation_stop_time_s"), 0.0) > 0.0:
                lines.append(" - separation stop hold [s]: " + str(
                    round(_safe_float(prestress.get("collision_separation_stop_time_s")), 9)))
            if _safe_float(prestress.get("collision_auto_impact_window_s"), 0.0) > 0.0:
                lines.append(" - auto impact window [s]: " + str(
                    round(_safe_float(prestress.get("collision_auto_impact_window_s")), 6)))
            lines.append(" - peak contact force [kN]: " + str(
                round(_safe_float(prestress.get("collision_peak_contact_force_n")) / 1000.0, 4)))
            lines.append(" - max penetration [mm]: " + str(
                round(1000.0 * _safe_float(prestress.get("collision_max_penetration_m")), 4)))
            lines.append(" - max penetration ratio: " + str(
                round(_safe_float(prestress.get("collision_max_penetration_ratio")), 6)))
            lines.append(
                " - contact duration [s]: " + str(round(_safe_float(prestress.get("collision_contact_duration_s")), 8)))
            lines.append(" - saved result steps: " + str(_safe_int(prestress.get("collision_saved_steps"), 0)))
            if _safe_float(prestress.get("collision_adaptive_cutback_retries"), 0.0) > 0.0:
                lines.append(" - adaptive contact cutbacks: " + str(
                    _safe_int(prestress.get("collision_adaptive_cutback_retries"), 0)))
            if str(prestress.get("collision_solution_control", "") or ""):
                lines.append(
                    " - solution control: " + str(prestress.get("collision_solution_control", "")).replace("_", " "))
            if str(prestress.get("collision_arc_length_applicability", "") or ""):
                lines.append(" - arc length: static continuation only; not used for collision impact")
            if _safe_float(prestress.get("collision_beam_contact_enabled"), 0.0) > 0.0:
                lines.append(" - direct beam/stiffener contact: enabled")
            if _safe_float(prestress.get("collision_material_nonlinear_enabled"), 0.0) > 0.0:
                lines.append(" - material nonlinear impact: enabled")
                lines.append(" - impact kinematics: " + str(prestress.get("collision_nonlinear_kinematics",
                                                                          summary.get("collision_nonlinear_kinematics",
                                                                                      "von_karman"))))
                if _safe_float(prestress.get("collision_nonlinear_assembly_threads"), 0.0) > 0.0:
                    lines.append(" - resolved assembly threads: " + str(
                        _safe_int(prestress.get("collision_nonlinear_assembly_threads"), 0)))
                if str(prestress.get("collision_nonlinear_status", "") or ""):
                    lines.append(
                        " - nonlinear impact status: " + str(prestress.get("collision_nonlinear_status", "")).replace(
                            "_", " "))
                lines.append(" - nonlinear Newton iterations: " + str(
                    _safe_int(prestress.get("collision_nonlinear_iterations"), 0)))
                lines.append(
                    " - nonlinear cutbacks: " + str(_safe_int(prestress.get("collision_nonlinear_cutbacks"), 0)))
                lines.append(" - max equivalent plastic strain: " + str(
                    round(_safe_float(prestress.get("collision_nonlinear_max_plastic_strain")), 8)))
                lines.append(" - plastic damage strain limit: " + str(
                    round(_safe_float(prestress.get("collision_plastic_damage_threshold")), 8)))
            lines.append(" - sphere momentum balance error: " + str(
                round(_safe_float(prestress.get("collision_sphere_momentum_balance_error")), 6)))
            if "collision_energy_initial_j" in prestress or "collision_energy_final_j" in prestress:
                lines.extend(["", "Impact energy balance:"])
                lines.append(
                    " - total initial/final [J]: "
                    + str(round(_safe_float(prestress.get("collision_energy_initial_j")), 6))
                    + " / "
                    + str(round(_safe_float(prestress.get("collision_energy_final_j")), 6))
                )
                lines.append(
                    " - sphere kinetic initial/final [J]: "
                    + str(round(_safe_float(prestress.get("collision_sphere_kinetic_initial_j")), 6))
                    + " / "
                    + str(round(_safe_float(prestress.get("collision_sphere_kinetic_final_j")), 6))
                )
                lines.append(" - max relative drift: " + str(
                    round(_safe_float(prestress.get("collision_energy_max_relative_drift")), 8)))
            if collision_status in {"contact_iteration_failed", "nonlinear_iteration_failed"}:
                lines.extend(["", "Collision solver failure detail:"])
                if _safe_float(prestress.get("collision_failure_time_s"), 0.0) > 0.0:
                    lines.append(
                        " - failure time [s]: " + str(round(_safe_float(prestress.get("collision_failure_time_s")), 9)))
                if _safe_float(prestress.get("collision_failure_dt_s"), 0.0) > 0.0:
                    lines.append(" - failed local dt [s]: " + str(
                        round(_safe_float(prestress.get("collision_failure_dt_s")), 9)))
                lines.append(" - iterations used: " + str(_safe_int(prestress.get("collision_failure_iterations"), 0)))
                if _safe_float(prestress.get("collision_failure_residual_norm"), 0.0) > 0.0:
                    lines.append(" - residual norm: " + str(
                        round(_safe_float(prestress.get("collision_failure_residual_norm")), 6)))
                if _safe_float(prestress.get("collision_failure_effective_residual_tolerance_n"), 0.0) > 0.0:
                    lines.append(" - effective residual tolerance [N]: " + str(
                        round(_safe_float(prestress.get("collision_failure_effective_residual_tolerance_n")), 6)))
                if _safe_float(prestress.get("collision_failure_displacement_increment_m"), 0.0) > 0.0:
                    lines.append(" - displacement increment [m]: " + str(
                        round(_safe_float(prestress.get("collision_failure_displacement_increment_m")), 9)))
                lines.append(" - force change [N]: " + str(
                    round(_safe_float(prestress.get("collision_failure_force_change_n")), 6)))
                if _safe_float(prestress.get("collision_failure_effective_force_tolerance_n"), 0.0) > 0.0:
                    lines.append(
                        " - effective force tolerance [N]: "
                        + str(round(_safe_float(prestress.get("collision_failure_effective_force_tolerance_n")), 6))
                    )
                lines.append(" - penetration change [mm]: " + str(
                    round(1000.0 * _safe_float(prestress.get("collision_failure_penetration_change_m")), 6)))
                lines.append(" - failure penetration [mm]: " + str(
                    round(1000.0 * _safe_float(prestress.get("collision_failure_max_penetration_m")), 6)))
                active_ids = str(prestress.get("collision_failure_active_element_ids", "") or "")
                if active_ids:
                    lines.append(" - active element(s): " + active_ids)
                if collision_status == "nonlinear_iteration_failed":
                    lines.append(
                        " - suggestion: reduce manual dt, increase NL cutbacks, or reduce contact penalty/target stiffness.")
                else:
                    lines.append(" - suggestion: reduce dt/penalty or increase event substeps/contact iterations.")
            if _safe_float(prestress.get("collision_damage_enabled"), 0.0) > 0.0:
                lines.append(" - impact damage max utilization: " + str(
                    round(_safe_float(prestress.get("impact_damage_max_utilization")), 6)))
                deleted_count = _safe_int(
                    prestress.get("collision_deleted_eroded_elements",
                                  prestress.get("collision_deleted_shell_elements")),
                    0,
                )
                lines.append(" - deleted/eroded elements: " + str(deleted_count))
            if _safe_float(prestress.get("collision_material_nonlinear_enabled"), 0.0) > 0.0:
                lines.append(
                    " - meaning: this is a material-nonlinear implicit transient with frictionless sphere-shell contact"
                    + (" and direct beam/stiffener contact." if _safe_float(
                        prestress.get("collision_beam_contact_enabled"), 0.0) > 0.0 else "."))
            else:
                lines.append(
                    " - meaning: this is a linear structural transient with nonlinear frictionless sphere-shell contact"
                    + (" and direct beam/stiffener contact." if _safe_float(
                        prestress.get("collision_beam_contact_enabled"), 0.0) > 0.0 else "."))
        for key, value in prestress.items():
            if key in special_keys:
                continue
            lines.append(" - " + key + ": " + str(round(_safe_float(value), 3)))
        nonlinear_status = str(prestress.get("nonlinear_status", "") or "")
        if nonlinear_status:
            lines.extend(["", "Nonlinear tangent-stability check:"])
            lines.append(" - status: " + nonlinear_status.replace("_", " "))
            steps = _safe_float(prestress.get("nonlinear_steps"), 0.0)
            lines.append(" - completed load steps: " + str(int(steps)))
            limit_factor = _safe_float(prestress.get("nonlinear_limit_factor"), 0.0)
            if nonlinear_status in {"limit_point_detected", "near_limit_point", "completed"} and limit_factor > 0.0:
                lines.append(" - estimated nonlinear load factor: " + str(round(limit_factor, 4)))
            else:
                lines.append(" - estimated nonlinear load factor: not available")
                if nonlinear_status == "initial_tangent_not_positive":
                    lines.append(
                        " - explanation: the initial tangent stiffness was not positive for the selected prestress state.")
                elif steps == 0:
                    lines.append(" - explanation: the nonlinear check stopped before the first load increment.")
                else:
                    lines.append(" - explanation: no usable limit point was found in the configured load-step range.")
    load_resultant = summary.get("load_resultant") or {}
    if load_resultant:
        force = load_resultant.get("force_n", (0.0, 0.0, 0.0))
        lines.extend(["", "Load resultant force [N]: " + ", ".join(
            str(round(_safe_float(component), 3)) for component in force)])
    if result.diagnostics:
        lines.extend(["", "Diagnostics:"])
        lines.extend(" - " + item for item in result.diagnostics)
    return "\n".join(lines)


FEM_OPTION_INFO: dict[str, dict[str, str]] = {
    "mesh_fidelity": {
        "title": "Mesh Fidelity",
        "purpose": "Controls the default shell mesh density when no explicit mesh size is given.",
        "use": (
            "Each level sets a target number of shell elements across each plate field between members: "
            "coarse ~= 4 per field, medium ~= 8, fine ~= 12, very fine ~= 20. The generator always inserts "
            "mesh lines at stiffeners and girders, so the true element size also depends on member spacing. "
            "Use the 'Preview mesh' button (Collision tab) to see the exact element count and size range in mm "
            "for the current geometry."
        ),
        "output": "Changes node, shell and beam counts, stress recovery, displacement shape and eigenvalue buckling factors.",
        "caution": "Very fine meshes can become expensive for cylinders with many stiffeners. Use explicit mesh size when you need a repeatable target element length.",
    },
    "mesh_size_m": {
        "title": "Mesh Size",
        "purpose": "Optional target element edge length in metres.",
        "use": "When greater than zero, generated mesh divisions are based on this size. The generator still limits the size so stiffener and girder lines remain represented by mesh edges.",
        "output": "Reported in FE mesh diagnostics as maximum axial, circumferential, x or y edge size.",
        "caution": "A value of zero lets the selected mesh fidelity decide. A very small value can make the solve slow.",
    },
    "pressure_pa": {
        "title": "Pressure",
        "purpose": "Uniform pressure magnitude used for the static prestress calculation.",
        "use": "The pressure is applied to shell elements using the selected pressure direction and load scale. The recovered membrane stresses are then used for buckling.",
        "output": "Affects displacements, stresses, recovered prestress and buckling load factors.",
        "caution": "When analysing imported FEA result stresses, avoid double counting pressure unless pressure is intentionally part of the buckling load case.",
    },
    "custom_time_domain_enabled": {
        "title": "Custom Time-Domain Load",
        "purpose": "Runs the synced ANYsolver linear time-domain pressure-patch solver for a custom load pulse.",
        "use": "When enabled, a prescribed shell-normal pressure pulse is applied to the selected shell patch and advanced with Newmark average acceleration. This is a separate transient response calculation after the normal static solve.",
        "output": "Adds custom load status, selected shell count, peak transient displacement and peak transient von Mises stress to the result print.",
        "caution": "This is prescribed structural response only: no fluid-structure interaction, added mass, water entry, cavitation or pressure feedback is included.",
    },
    "custom_pressure_pa": {
        "title": "Custom Load Pressure",
        "purpose": "Peak pressure magnitude for the transient custom load pulse.",
        "use": "The pressure sign follows the selected pressure direction. The pulse starts at t = 0 and remains constant until the custom load duration.",
        "output": "Controls the transient impulse, peak displacement and transient stress response.",
        "caution": "Do not also include the same pressure as a static pressure unless that is the intended load history.",
    },
    "custom_time_domain_duration_s": {
        "title": "Custom Load Duration",
        "purpose": "Length of the constant pressure pulse in seconds.",
        "use": "The transient load is active from t = 0 to this time, then returns to zero.",
        "output": "Controls impulse and dynamic amplification.",
        "caution": "Use a time step small enough to resolve the pulse duration.",
    },
    "custom_time_domain_total_time_s": {
        "title": "Custom Load Total Time",
        "purpose": "Total transient analysis time.",
        "use": "The solver saves the response until this time, including the free vibration after the pulse has ended.",
        "output": "Controls how much of the transient response is searched for peak displacement and stress.",
        "caution": "Long runs with small dt increase runtime.",
    },
    "custom_time_domain_dt_s": {
        "title": "Custom Load Time Step",
        "purpose": "Fixed Newmark time step.",
        "use": "The transient solver reuses the effective stiffness factorization when possible, but the number of steps still scales with total_time / dt.",
        "output": "Affects transient accuracy and runtime.",
        "caution": "The Newmark method is stable for the default parameters, but a coarse time step can miss the pressure pulse and peak response.",
    },
    "custom_time_domain_result_interval_s": {
        "title": "Custom Load Result Interval",
        "purpose": "Time spacing for saved transient result snapshots and probe history points.",
        "use": "Set a positive interval to choose the saved time-domain result spacing. Leave 0 for automatic decimation.",
        "output": "Controls which time steps appear in the result-case selector and node/element history graphs.",
        "caution": "Small intervals on fine meshes increase stress recovery time and stored result size.",
    },
    "custom_pressure_patch_center": {
        "title": "Custom Pressure Patch Centre",
        "purpose": "Patch centre coordinates used to select shell elements by centroid.",
        "use": "For flat panels, A is x and B is y. For cylinders, A is axial z and B is circumferential arc length measured from the positive X direction. Zero uses the model centre for A and the positive X seam for B.",
        "output": "Changes which shell elements receive the transient custom load pulse.",
        "caution": "Selection is centroid based. If exact patch membership is required, verify selected shell count and plot resolution.",
    },
    "custom_pressure_patch_size": {
        "title": "Custom Pressure Patch Size",
        "purpose": "Patch dimensions used for centroid-based shell selection.",
        "use": "For flat panels, A/B are x/y dimensions. For cylinders, A is axial length and B is circumferential arc length. If either value is zero, all shell elements are loaded.",
        "output": "Changes the loaded area, impulse and transient response.",
        "caution": "Very small patches may select no element on a coarse mesh; the wrapper then falls back to loading all shells to avoid a silent zero-load run.",
    },
    "custom_time_domain_include_static_load": {
        "title": "Custom Load Base Load",
        "purpose": "Adds the current static load vector as a constant base load in the transient custom load run.",
        "use": "Leave off to study the custom load pulse alone. Enable when the transient pressure is intentionally superposed on the static load case.",
        "output": "Changes transient displacement, stress and impulse resultants.",
        "caution": "This can double count pressure if the static pressure already represents the same custom load event.",
    },
    "load_scale": {
        "title": "Load Scale",
        "purpose": "Multiplier on pressure and generated design loads.",
        "use": "The solver multiplies the input pressure by this factor before the static solve.",
        "output": "Changes load resultant, static stresses and buckling prestress.",
        "caution": "Keep at 1.0 unless running a sensitivity or intentionally scaling the load case.",
    },
    "top_bottom_moment_nm": {
        "title": "Top/Bottom Moment",
        "purpose": "Applies an opposite shell bending-style moment couple at cylinder ends.",
        "use": "The generated load case distributes nodal moments on the end rings. It is mainly useful for cylinder examples and controlled studies.",
        "output": "Shown in diagnostics and contributes to static displacement/stress recovery.",
        "caution": "This is a simplified end moment input, not a full end-cap or external frame model.",
    },
    "acceleration_x_m_s2": {
        "title": "Acceleration X / Y / Z",
        "purpose": "Body-load acceleration field in the global x, y and z directions (m/s^2).",
        "use": (
            "Each nonzero component applies a consistent inertial body load (mass x acceleration) over the whole "
            "structure and over any added masses. Use it for design accelerations such as ship motions or a 1 g "
            "gravity check (set Z to -9.81). Values add to any pressure and edge loads."
        ),
        "output": "Adds distributed nodal forces; reported in the load resultant and reaction summary.",
        "caution": "This is a quasi-static body load. It is not a base-excitation transient; for impact use the collision tab.",
    },
    "added_mass_kg": {
        "title": "Added Mass",
        "purpose": "Total lumped mass (kg) attached to the selected location.",
        "use": (
            "The mass is split equally over the nodes of the chosen location. It enters the global mass matrix, so "
            "it lowers natural frequencies and participates in transient/collision dynamics, and it produces an "
            "inertial load under the acceleration field above."
        ),
        "output": "Changes modal frequencies, dynamic response and (with acceleration) the load resultant.",
        "caution": "Zero mass or a location that matches no nodes is ignored (a diagnostic is printed).",
    },
    "added_mass_location": {
        "title": "Added Mass Location",
        "purpose": "Where the added mass is attached.",
        "use": (
            "Flat panels: a single plate edge (x0/x1/y0/y1) or all edges. Cylinders: the top or bottom end ring. "
            "Nodes are matched from the generated mesh, so the count follows the mesh density."
        ),
        "output": "Determines which nodes receive the added mass and inertial load.",
        "caution": "Choose a plate option for flat panels and a cylinder option for cylinders; a mismatch matches no nodes.",
    },
    "local_refinement_enabled": {
        "title": "Panel Detail Mesh",
        "purpose": "Turns selected panel patches into local mesh-refinement regions.",
        "use": "Select/split panels in the 3D selection view, then use the Mesh-tab button to adopt those panels as refinement regions. Fine size, extra extent and growth control the resulting detail mesh.",
        "output": "Increases shell element density over selected regions and shows the regions in the mesh preview.",
        "caution": "Structured panel meshes propagate grid lines across the panel, so several small regions can still increase the whole mesh noticeably.",
    },
    "local_refinement_fine_factor": {
        "title": "Panel Fine Factor",
        "purpose": "Fallback panel detail size as a fraction of the global mesh size.",
        "use": "Used only when Panel fine size is zero. Smaller values create denser selected-panel regions.",
        "output": "Changes the finest shell element size inside selected panel refinement regions.",
        "caution": "Prefer an explicit fine size for final studies.",
    },
    "local_refinement_fine_size_m": {
        "title": "Panel Fine Size",
        "purpose": "Exact target element size inside selected panel detail regions.",
        "use": "Enter metres. Zero falls back to the panel fine factor. The solver floors the final value at the plate thickness and caps it at the global mesh size.",
        "output": "Sets the finest shell element size for selected panel regions.",
        "caution": "Thickness-scale sizes can grow the model quickly.",
    },
    "local_refinement_extent_m": {
        "title": "Panel Extent",
        "purpose": "Extra distance around selected panel regions that remains part of the fine/detail zone.",
        "use": "Set zero to refine only the selected panels before geometric growth begins. Positive values expand the detail zone around each selected panel.",
        "output": "Changes the highlighted panel refinement rectangle and the number of refined elements.",
        "caution": "Large extents can effectively refine most of the panel.",
    },
    "local_refinement_growth_factor": {
        "title": "Panel Growth",
        "purpose": "Geometric growth factor from selected-panel detail size back to the global mesh size.",
        "use": "Values near 1.1 give a smooth transition; larger values coarsen faster.",
        "output": "Changes the transition band and element-count increase around selected panel regions.",
        "caution": "Too abrupt a growth can produce poor element-size jumps; too gentle can over-refine.",
    },
    "point_refinement_enabled": {
        "title": "Point Detail Mesh",
        "purpose": "Adds a local circular detail mesh around a user-selected point.",
        "use": "Use Pick point in the Mesh tab and click a panel, or enter Point X/Y manually. Fine size, extent and growth match the impact detail-mesh controls.",
        "output": "Adds a highlighted point-detail circle and local mesh refinement in the preview.",
        "caution": "Point picking is exact for flat panels; curved/cylinder picks fall back to the picked patch centre.",
    },
    "point_refinement_x_m": {
        "title": "Point X",
        "purpose": "X coordinate of the manual point detail mesh centre.",
        "use": "Enter metres in the generated flat-panel coordinate system, or set it by clicking Pick point.",
        "output": "Moves the point-detail mesh centre.",
        "caution": "Coordinates outside the panel are clamped by the mesh generator.",
    },
    "point_refinement_y_m": {
        "title": "Point Y",
        "purpose": "Y coordinate of the manual point detail mesh centre.",
        "use": "Enter metres in the generated flat-panel coordinate system, or set it by clicking Pick point.",
        "output": "Moves the point-detail mesh centre.",
        "caution": "Coordinates outside the panel are clamped by the mesh generator.",
    },
    "point_refinement_fine_size_m": {
        "title": "Point Fine Size",
        "purpose": "Exact target element size inside the point detail radius.",
        "use": "Enter metres. Zero falls back to the point fine factor.",
        "output": "Sets the finest shell element size around the selected point.",
        "caution": "Small values over large extents can dominate runtime.",
    },
    "point_refinement_extent_m": {
        "title": "Point Extent",
        "purpose": "Radius of the circular fine/detail zone around the selected point.",
        "use": "Elements are kept at the fine size inside this radius, then grow geometrically back to global size.",
        "output": "Sets the point-detail circle drawn in mesh preview.",
        "caution": "Use enough extent to cover the local stress/contact feature, but not the whole panel.",
    },
    "point_refinement_growth_factor": {
        "title": "Point Growth",
        "purpose": "Geometric growth factor from point fine size back to global mesh size.",
        "use": "Values near 1.1 transition smoothly; values around 1.3-1.5 coarsen faster.",
        "output": "Changes the size and smoothness of the transition band.",
        "caution": "A very high value makes abrupt mesh-size jumps.",
    },
    "point_refinement_z_m": {
        "title": "Point Z",
        "purpose": "World-space height of the point-refinement centre.",
        "use": "Filled automatically when you pick a point. On a cylinder the axial coordinate equals world z, so "
               "editing Point Z also updates Point X (and vice versa). On a flat panel the plate lies at z = 0 and "
               "this field is informational.",
        "output": "Shows where the refinement centre sits in the 3D view.",
        "caution": "For cylinders the circumferential position is set by the arc-length Point Y, not by X/Z.",
    },
    "collision_adaptive_mesh": {
        "title": "Impact Detail Mesh",
        "purpose": "Uses the sphere trajectory impact point as a point-detail mesh source.",
        "use": (
            "The generator traces the sphere trajectory onto the panel, keeps elements fine inside the impact "
            "extent radius, then grows geometrically back to global mesh size. Use Preview mesh to inspect the result."
        ),
        "output": "Increases element count locally; improves contact-force and local-stress resolution at impact.",
        "caution": "A small fine size with a large extent can create many elements; check the preview element count.",
    },
    "collision_adaptive_fine_factor": {
        "title": "Impact Fine Factor",
        "purpose": "Element size at the impact point as a fraction of the base element size.",
        "use": (
            "For example 0.25 makes impact elements about a quarter of the base size. Smaller = finer and more "
            "elements. Ignored when an explicit 'Impact fine size' is given."
        ),
        "output": "Sets the finest local element size shown in the mesh preview metrics.",
        "caution": "Values below ~0.05 rarely help and grow the model quickly; use 'Impact fine size' for an exact target.",
    },
    "collision_adaptive_fine_size_m": {
        "title": "Impact Fine Size",
        "purpose": "Exact finest element edge length at the impact point, in metres (0 = use the fine factor instead).",
        "use": (
            "Set an absolute target such as the plate thickness for a very fine impact mesh (e.g. 0.012 for a 12 mm "
            "plate gives ~t x t elements). Takes precedence over the fine factor. The size is floored at the plate "
            "thickness (elements are never smaller than t) and capped at the base element size."
        ),
        "output": "Sets the finest local element size; check the preview element count as small sizes grow the model fast.",
        "caution": "A thickness-scale size on a large panel can produce many thousands of elements and a slow solve.",
    },
    "collision_adaptive_extent_m": {
        "title": "Impact Extent",
        "purpose": "Radius of the fine/detail mesh zone around the traced impact point.",
        "use": "Enter metres. Zero falls back to Sphere radius multiplied by Impact extent/radius.",
        "output": "Sets the red impact-detail circle in the mesh preview.",
        "caution": "Large extents refine broad areas and can dominate runtime.",
    },
    "collision_adaptive_growth_factor": {
        "title": "Impact Growth",
        "purpose": "Geometric growth factor from impact fine size back to global mesh size.",
        "use": "Values near 1.1 transition smoothly; values around 1.3-1.5 coarsen faster.",
        "output": "Changes transition smoothness and element count around the impact point.",
        "caution": "Abrupt growth can reduce local quality; gentle growth can over-refine.",
    },
    "collision_adaptive_zone_factor": {
        "title": "Impact Extent / Radius",
        "purpose": "Legacy fallback for impact detail extent when explicit Impact extent is zero.",
        "use": "For example 2.5 gives a detail radius of 2.5 sphere radii.",
        "output": "Controls the impact-detail circle only when Impact extent is zero.",
        "caution": "Prefer explicit Impact extent for final studies.",
    },
    "custom_bc_segments": {
        "title": "Edge Boundary Conditions",
        "purpose": "Apply a support condition to edges selected in the 3D view, same workflow as edge loads.",
        "use": "Start selection, right-click edges in the 3D view, choose 'simply supported' or 'fixed' and press "
               "'Set BC on selected edges'. The BC appears in the applied list below and can be deleted there.",
        "output": "Creates support constraints for the mesh nodes along the selected edge segments.",
        "caution": "Available for flat panels in custom load/BC mode; segments also become mesh break lines.",
    },
    "thickness_regions": {
        "title": "Plate Thickness Regions",
        "purpose": "Assign a plate thickness to whole panels or divided panel regions.",
        "use": "Select panels in the 3D view (optionally divide them first), enter a thickness and press "
               "'Set on selected panels'; 'Set on whole plate' assigns every panel. Regions apply in order - "
               "the last matching region wins.",
        "output": "Skin shell elements inside each region get the region thickness; region boundaries become "
                  "mesh break lines so elements never straddle a thickness step. Affects stiffness, stress and mass.",
        "caution": "Member (stiffener/girder) shells keep their section thickness. Check the thickness plot before running.",
    },
    "division_plane": {
        "title": "Divide Panels By Plane",
        "purpose": "Cut the selectable panels with a global x, y or z plane so sub-regions can get their own thickness.",
        "use": "Choose the plane normal and coordinate, then press 'Add division plane'. All panels crossing the "
               "plane are split. On a cylinder an x or y plane cuts at the two matching circumferential positions; "
               "a z plane cuts at the axial height. On a flat panel use x or y.",
        "output": "More, smaller selectable panels; the cut lines also act as mesh break lines once used by a region.",
        "caution": "Divisions only affect the selection grid until a thickness (or load) is assigned to the parts.",
    },
    "detail_transition_style": {
        "title": "Detail Mesh Transition",
        "purpose": "How local detail meshes (panel, point, impact) blend into the global mesh.",
        "use": "'graded grid' grades the structured grid lines from fine to coarse; the refinement "
               "bands extend across the full model in both directions. 'local patch (quad+tri)' "
               "subdivides only the cells inside the detail window (2:1 per level, up to 3 levels) "
               "and closes the transition with conforming quad templates plus a small number of "
               "triangles, leaving the rest of the structure completely untouched.",
        "output": "Local patch keeps element aspect ratios near 1 and removes the fine bands seen "
                  "far from the detail zone; a few S3 triangles appear in the one-element transition ring. "
                  "Beam members crossing the patch are split to stay connected.",
        "caution": "Local patch requires linear shells (S4/S3), B2 beams and beam-type members; with "
                   "shell-web members, B3 beams, S6/S8 shells or conical geometry it falls back to the graded grid. "
                   "Fine size snaps to the nearest 2:1 subdivision of the base mesh (max 3 levels = 1/8).",
    },
    "include_stiffeners": {
        "title": "Include Stiffener Beams",
        "purpose": "Controls whether generated stiffener beam members are included in the FE model.",
        "use": "When enabled, stiffeners are represented as beam elements tied to shell plating. When disabled, only shell plating and other enabled members are solved.",
        "output": "Changes beam count, local stiffness, stress distribution and buckling modes.",
        "caution": "Disabling stiffeners is useful for comparison only; it usually does not represent the real structure.",
    },
    "include_girders": {
        "title": "Include Girder/Frame Beams",
        "purpose": "Controls whether generated girders, frames or ring members are included.",
        "use": "When enabled, girders are represented as beam elements. Cylinder ring frames are tied into the shell model.",
        "output": "Changes beam count, global stiffness, local buckling boundary behaviour and recovered stresses.",
        "caution": "For stiffened cylinders, girder/frame modelling has a strong effect on global shell modes.",
    },
    "include_end_lids": {
        "title": "Top/Bottom Lid",
        "purpose": "Adds stress-free rigid diaphragm constraints at cylinder ends.",
        "use": "The end ring nodes are tied to free reference nodes. The lid adds local diaphragm behaviour without shell elements, pressure loads or lid stress recovery.",
        "output": "Shown as rigid lids in mesh diagnostics and affects cylinder end deformation.",
        "caution": "At least one global motion remains free before buckling gauge constraints are added, avoiding artificial axial membrane locking.",
    },
    "imperfection_enabled": {
        "title": "Geometric Imperfection",
        "purpose": "Applies a stress-free initial geometry offset before the static/nonlinear solve.",
        "use": "Flat panels use a sinusoidal plate half-wave over the shell region. Cylinders use a radial out-of-roundness field. An amplitude of zero uses the standard default scale.",
        "output": "Changes static stress recovery, nonlinear response and buckling factors because the reference geometry is imperfect.",
        "caution": "This is a geometric imperfection, not a residual-stress field. Verify the selected shape and amplitude before using nonlinear capacity results.",
    },
    "imperfection_shape": {
        "title": "Imperfection Shape",
        "purpose": "Chooses the standard imperfection family applied to the generated shell model.",
        "use": "The current runtime option maps flat panels to plate half-wave imperfections and cylinders to radial out-of-roundness. Future solver work can add eigenmode-scaled imperfections.",
        "output": "Affects the offset field applied to nodes before the solve.",
        "caution": "Member-only bows are not yet separately exposed in this runtime GUI; the shape is intended as a panel/cylinder equivalent imperfection.",
    },
    "imperfection_amplitude_m": {
        "title": "Imperfection Amplitude",
        "purpose": "Maximum geometric imperfection amplitude in metres.",
        "use": "Enter a positive value to force the amplitude. Enter zero to use the standard default in the wrapper: s/200 for flat plate mode or spacing/200 for cylinder radial mode.",
        "output": "Reported in the result print together with the actual maximum applied nodal offset.",
        "caution": "Capacity can be sensitive to this value. Use code/rule tolerance values or calibrated amplitudes for final assessments.",
    },
    "imperfection_waves": {
        "title": "Imperfection Waves",
        "purpose": "Number of half waves in the generated imperfection field.",
        "use": "For flat panels, A/B are x/y half-wave counts. For cylinders, A is circumferential waves and B is axial half waves.",
        "output": "Changes the shape of the imperfect reference geometry.",
        "caution": "Use wave counts consistent with the expected buckling mode or rule requirement.",
    },
    "num_buckling_modes": {
        "title": "Buckling Modes",
        "purpose": "Number of positive buckling factors/mode shapes requested.",
        "use": "The eigensolver returns the lowest positive modes available from the recovered prestress state.",
        "output": "Controls the number of mode entries in the display selector and load-factor table.",
        "caution": "More modes require more solver work and may include local modes that are not design governing.",
    },
    "runtime_solver": {
        "title": "Runtime Solver",
        "purpose": "Selects the high-level runtime path used after the FE model and loads are generated.",
        "use": "Stepwise keeps the familiar ANYstructure sequence: linear static, prestress recovery, optional nonlinear solve and buckling. ANYsolver capacity workflow runs the new traceable solver-wide sequence: linear static, eigenvalue buckling, stress-free imperfection and nonlinear static capacity in one workflow.",
        "output": "The result print records the selected path, workflow status, capacity factor and mesh-mode adequacy when the capacity workflow is selected.",
        "caution": "The capacity workflow is intentionally opt-in because it can be slower and applies a different capacity interpretation than the default static/eigenvalue result.",
    },
    "buckling_shift_load_factor": {
        "title": "Buckling Shift",
        "purpose": "Optional shift target for the sparse buckling eigensolver.",
        "use": "A positive value asks the backend to search near that load factor. Zero uses the default lowest-positive-factor search.",
        "output": "Affects which buckling modes are returned and is recorded in the solver provenance.",
        "caution": "Use only when you understand the expected load-factor range; an unsuitable shift can hide lower modes.",
    },
    "buckling_load_factor_range": {
        "title": "Buckling Range",
        "purpose": "Optional accepted load-factor interval for buckling modes.",
        "use": "Positive lower and/or upper values filter returned eigenmodes. Zero means open-ended.",
        "output": "Controls which modes appear in the display selector and load-factor table.",
        "caution": "Filtering is useful for numerical searches but can remove physically relevant low modes.",
    },
    "buckling_repeated_tolerance": {
        "title": "Repeated Mode Tolerance",
        "purpose": "Tolerance used to group nearly repeated buckling factors.",
        "use": "The backend marks close eigenvalues as repeated-mode groups for validity diagnostics.",
        "output": "The result print reports the number of repeated mode groups found.",
        "caution": "Repeated modes are common in symmetric cylinders and panels; they are not automatically an error.",
    },
    "buckling_allow_dense_fallback": {
        "title": "Dense Buckling Fallback",
        "purpose": "Allows a dense eigenvalue fallback when the sparse buckling solve cannot return useful modes.",
        "use": "Leave off for normal runs. Enable for small models when diagnosing sparse solver behaviour.",
        "output": "May return modes for small reduced systems that sparse search did not resolve.",
        "caution": "Dense fallback is not suitable for large models and may consume significant memory.",
    },
    "recovery_history_mode": {
        "title": "Recovery History",
        "purpose": "Controls how much transient/nonlinear history data the backend is allowed to retain.",
        "use": "Full keeps all selected histories, selected limits recovery scope, and envelope stores peak/envelope style histories where supported.",
        "output": "Recorded in result provenance and passed to transient custom load recovery policy.",
        "caution": "This is mostly a memory-management control; static stress plots still recover the full current field needed for the display.",
    },
    "recovery_threads": {
        "title": "Recovery Threads",
        "purpose": "Optional thread count for backend result-recovery phases that support measured parallel recovery.",
        "use": "Zero lets the backend choose the default serial path. Positive values request that many recovery workers.",
        "output": "Can change recovery timing; result values should remain deterministic.",
        "caution": "Small models may run slower with threads due to overhead.",
    },
    "memory_limit_mb": {
        "title": "Memory Limit",
        "purpose": "Optional soft memory limit for recovery/resource-policy checks.",
        "use": "Zero disables the limit. Positive values are converted to bytes and passed to backend resource policy objects.",
        "output": "If supported recovery would exceed the limit, the backend can reject the run before allocating large histories.",
        "caution": "This is a guardrail, not a full process memory sandbox.",
    },
    "capacity_buckling_mode_number": {
        "title": "Capacity Mode Number",
        "purpose": "Selects which eigenmode seeds the capacity workflow imperfection.",
        "use": "Mode 1 normally means the lowest positive buckling factor. Higher values can be used to study a known local/global mode.",
        "output": "Affects the stress-free imperfection used by the ANYsolver capacity workflow.",
        "caution": "Choosing a non-governing mode can produce a non-conservative or misleading capacity estimate.",
    },
    "capacity_mesh_min_elements_per_half_wave": {
        "title": "Mode Mesh Adequacy",
        "purpose": "Minimum target number of active elements per estimated half-wave in the selected buckling mode.",
        "use": "The capacity workflow estimates active half-waves and reports whether the mesh is coarse for the selected mode.",
        "output": "Printed as mode mesh adequacy and active elements per estimated half-wave.",
        "caution": "This is a coarse screening metric, not a replacement for mesh convergence.",
    },
    "boundary_condition": {
        "title": "Boundary Condition",
        "purpose": "Defines the generated global support assumptions.",
        "use": "Flat automatic mode always gives pressure-loaded plating physical edge supports: line-property edge supports are used when available, otherwise all four edges default to simply supported. Cylinders keep the existing rigid-body anchor/lid behaviour unless custom mode is used.",
        "output": "Affects stiffness, displacement, stress recovery and buckling factors.",
        "caution": "Nullspace projection is only a numerical gauge, not the plate bending support. For manual flat-plate support studies, use custom load/BC mode.",
    },
    "boundary_auto_supports": {
        "title": "Automatic supports",
        "purpose": "Applies the generator's automatic, well-posed supports to the whole boundary when no DOF is "
                   "constrained in the grid below.",
        "use": "Leave ticked for the usual behaviour (flat: simply supported edges; cylinder: end supports). Tick "
               "any DOF below to define the boundary explicitly instead. Untick with no DOF selected for a truly "
               "free (unsupported) boundary.",
        "output": "Determines the whole-boundary restraint when the DOF grid is empty.",
        "caution": "A free boundary needs another restraint (selected-edge BC or symmetry) or the static solve is "
                   "a mechanism.",
    },
    "boundary_edge_select": {
        "title": "Apply to edge",
        "purpose": "Choose which boundary edge the DOF grid below edits.",
        "use": "Cylinder: Bottom, Top, or Both ends. Flat plate: any of the four edges (x0/x1/y0/y1), or All "
               "edges. Each edge keeps its own DOF selection and enforced values; switching the radio loads that "
               "edge's spec. 'Both ends'/'All edges' applies the grid to every edge at once.",
        "output": "Determines which edge nodes receive the DOFs set in the grid.",
        "caution": "A per-edge value overrides the 'All'/'Both' value on that edge.",
    },
    "boundary_dof_grid": {
        "title": "Whole-boundary DOFs",
        "purpose": "Constrain chosen degrees of freedom on the entire model boundary (all plate edges / both "
                   "cylinder ends).",
        "use": "Tick the DOFs to constrain (Ux/Uy/Uz translations, Rx/Ry/Rz rotations) and set the enforced value "
               "(0 = fixed). Non-zero values are enforced displacements/rotations applied in every run and can "
               "drive significant geometric nonlinearity.",
        "output": "Generates a support on all boundary nodes with the selected DOFs held at their values.",
        "caution": "Enforced rotations/displacements are real loads; large values may need the nonlinear solver.",
    },
    "edge_dof_grid": {
        "title": "Selected-edge DOFs",
        "purpose": "Constrain chosen degrees of freedom on the edges picked in the 3D view only.",
        "use": "Right-click edges in the selection view, tick the DOFs and enforced values, then 'Set BC on "
               "selected edges'. Each set is added to the applied list below and can be deleted there. Additive on "
               "top of the whole-boundary supports.",
        "output": "Generates supports on the selected edge nodes with the chosen DOFs/values.",
        "caution": "Enforced values here also apply to every run and can cause nonlinearity.",
    },
    "symmetry_mode": {
        "title": "Symmetry",
        "purpose": "Applies global symmetry constraints for x, y or z symmetry planes.",
        "use": "The generator constrains normal displacement and compatible rotations on the detected symmetry plane. Cyclic is recorded for full 360 degree cylinder models.",
        "output": "Shown in diagnostics and changes the constrained DOF set.",
        "caution": "Only use symmetry if the geometry, load and expected buckling mode are symmetric.",
    },
    "shell_element_order": {
        "title": "Shell Element",
        "purpose": "Selects triangular or quadrilateral shell elements.",
        "use": "S4 is fastest for quadrilateral meshes. S3 splits generated quads into linear triangles. S6 adds triangular midside nodes. S8 adds quadrilateral midside nodes, and S8R is the reduced integration version of S8.",
        "output": "Mesh diagnostics report the shell order. S3/S6 are useful for SESAM/GeniE-style triangular compatibility checks; S6 and S8 increase node count and runtime.",
        "caution": "Triangular and higher-order shells should be checked with mesh convergence. S8R exhibits hourglass modes, so use with caution for unconstrained models.",
    },
    "beam_element_order": {
        "title": "Beam Element",
        "purpose": "Selects 2-node or 3-node beam elements for generated stiffeners, girders and frames.",
        "use": "B2 keeps the current two-node Timoshenko beam mesh. B3 inserts beam-direction mid nodes and emits quadratic three-node beam elements.",
        "output": "Mesh diagnostics report the beam order. B3 increases beam interpolation order and adds nodes along member lines.",
        "caution": "B3 is useful for member curvature studies but adds degrees of freedom. Use B2 for faster routine runs.",
    },
    "analysis_type": {
        "title": "Analysis Type",
        "purpose": "Controls how the reference stress/prestress state is established before buckling capacity is interpreted.",
        "use": "Linear eigenvalue runs one linear static solve, recovers membrane prestress, and sends that state to the eigenvalue buckling solver. Nonlinear stability is the older tangent-stability check: it scales the linear prestress and monitors K - lambda KG. Direct geometric/material nonlinear static uses incremental Newton-Raphson with the selected nonlinear kinematics.",
        "output": "Linear analysis produces static displacement/stress and eigenvalue buckling factors. Tangent stability prints a tangent limit estimate when one is found. Incremental nonlinear static prints status, completed load factor, Newton iterations, through-thickness layers and maximum equivalent plastic strain.",
        "caution": "Incremental nonlinear static is more expensive than linear eigenvalue analysis. A completed nonlinear static run at the requested max load factor means the target load was reached; it is not automatically a collapse load unless the run stops at a limit.",
    },
    "buckling_analysis_type": {
        "title": "Buckling Type",
        "purpose": "Controls how the instability result is reported after the reference stress state has been recovered.",
        "use": "Linear eigenvalue solves K phi = lambda KG phi and reports positive eigenvalues as load factors with corresponding mode shapes. Nonlinear limit uses the tangent-stability load-step estimate when available; it is a capacity estimate from stiffness loss rather than an eigenmode table.",
        "output": "Linear eigenvalue output gives several mode numbers and load factors. Nonlinear limit output gives one estimated limit factor when the load-step procedure finds a limit point; otherwise the output explains why the estimate is unavailable.",
        "caution": "Eigenvalue factors are elastic bifurcation factors around the current prestress state. Nonlinear limit estimates include tangent-stiffness degradation in the current simplified solver, but they are not a full post-buckling collapse trace.",
    },
    "pressure_direction": {
        "title": "Pressure Side",
        "purpose": "Selects the plate side where pressure is applied.",
        "use": "Front is the generated shell-normal side shown by the front marker in the 3D view. Back is the opposite side. Legacy external/internal values are accepted and mapped to front/back.",
        "output": "Changes load resultant, stress signs and buckling prestress.",
        "caution": "The 3D side markers follow generated element ordering. Verify the active side using the red pressure arrows in the preview.",
    },
    "follower_pressure": {
        "title": "Current-area Follower Pressure",
        "purpose": "Updates shell-pressure directions and loaded area as the nonlinear model deforms.",
        "use": "Enable it for nonlinear static or arc-length pressure loading when the pressure follows the moving shell surface. Select the Static only or Nonlinear static runtime path.",
        "output": "Uses ANYsolver's exact external-load tangent; corotational runs automatically select the consistent tangent.",
        "caution": "Disabled for linear, stepwise eigenvalue-buckling, transient, collision and capacity-workflow paths. It is a nonconservative load and is not a general linear eigenvalue-buckling input.",
    },
    "axial_force_n": {
        "title": "Axial Force",
        "purpose": "Adds a balanced axial force to the generated model.",
        "use": "For flat panels the force is applied on opposite x edges. For cylinders it is applied to the end rings.",
        "output": "Shown in diagnostics and included in load resultant/prestress recovery.",
        "caution": "Positive sign follows the current runtime convention; verify whether it produces tension or compression for the case.",
    },
    "enforced_displacement_x_m": {
        "title": "Enforced Displacement",
        "purpose": "Adds a prescribed displacement constraint to study displacement-controlled response.",
        "use": "Flat panels prescribe out-of-plane displacement near the panel centre. Cylinders prescribe radial displacement on a representative ring.",
        "output": "Appears as prescribed displacement constraints and affects static stress recovery.",
        "caution": "This is a modelling study input. Avoid combining with incompatible supports that over-constrain the same DOF.",
    },
    "stiffener_eccentricity_m": {
        "title": "Stiffener Eccentricity",
        "purpose": "Offsets generated stiffener beam nodes from the shell midsurface.",
        "use": "The offset is represented with exact beam-shell MPC constraints, so beam nodes are separate from shell nodes.",
        "output": "Changes beam-shell coupling stiffness and member stress recovery.",
        "caution": "Positive eccentricity follows the generated shell normal/radial direction.",
    },
    "girder_eccentricity_m": {
        "title": "Girder Eccentricity",
        "purpose": "Offsets generated girder/frame beam nodes from the shell midsurface.",
        "use": "The runtime creates separate girder nodes and beam-shell MPC coupling where applicable.",
        "output": "Changes frame/girder stiffness contribution and stress recovery.",
        "caution": "For cylinders with rigid lids, lid-ring nodes are kept compatible with one-level MPC constraints.",
    },
    "member_orientation": {
        "title": "Member Orientation",
        "purpose": "Controls beam local section orientation for asymmetric members.",
        "use": "Auto uses the backend default. Global Y/Z prescribe section local direction. Radial aligns cylinder members with the local radial direction.",
        "output": "Affects bending stiffness axes and member stress recovery.",
        "caution": "Wrong orientation can swap strong/weak axes. Use the 3D preview and diagnostics to verify.",
    },
    "solver_type": {
        "title": "Linear Solver",
        "purpose": "Selects the linear equation solver used by the static solve.",
        "use": "Direct is robust for normal model sizes. Iterative solvers are available for experiments on larger sparse systems.",
        "output": "Solver status and convergence information are printed in run status.",
        "caution": "Use direct unless memory or runtime requires experimenting with iterative solvers.",
    },
    "stress_percentile": {
        "title": "Stress Percentile",
        "purpose": "Controls the reported percentile stress used for summary output.",
        "use": "The solver samples recovered von Mises stresses and reports the requested percentile.",
        "output": "Affects p95/pXX stress summaries and plot annotations.",
        "caution": "Percentile stress is for summary robustness; design checks may require location-specific stresses.",
    },
    "elastic_modulus_gpa": {
        "title": "Elastic Modulus",
        "purpose": "Young's modulus used for shell and beam material stiffness.",
        "use": "Converted from GPa to Pa before the solver is called.",
        "output": "Affects stiffness, displacement, stress recovery and buckling factors.",
        "caution": "Typical steel value is about 210 GPa.",
    },
    "poisson_ratio": {
        "title": "Poisson Ratio",
        "purpose": "Material Poisson ratio used in shell constitutive stiffness.",
        "use": "The GUI clamps it below 0.5 for numerical stability.",
        "output": "Affects shell bending/membrane stiffness and buckling estimates.",
        "caution": "Typical steel value is about 0.3.",
    },
    "yield_stress_mpa": {
        "title": "Yield Stress",
        "purpose": "Material yield stress stored in the FE material model.",
        "use": "Converted from MPa to Pa and passed to the backend. For linear elastic material this is metadata. For DNV-RP-C208 material, the selected table row supplies sigma_yield and overrides this value in the nonlinear shell material.",
        "output": "Included in run summary and used by downstream utilization checks. In material nonlinear static the DNV curve section reports the active low-fractile yield values.",
        "caution": "Linear eigenvalue buckling is still elastic. Select geometric + material nonlinear static and a DNV-RP-C208 material model to include yielding in the incremental static solve.",
    },
    "material_model": {
        "title": "Material Model",
        "purpose": "Selects whether the FE material remains linear elastic or uses the DNV-RP-C208 low-fractile steel curve in nonlinear static analysis.",
        "use": "Linear elastic keeps generated sections elastic. DNV-RP-C208 steel attaches the low-fractile true-stress versus true-plastic-strain curve for nonlinear static and nonlinear impact paths supported by the backend.",
        "output": "Affects incremental nonlinear static response, plastic strain output and the nonlinear load-factor estimate. Linear static and eigenvalue buckling stay elastic.",
        "caution": "Use mesh and member-model convergence for capacity studies; nonlinear shell and beam-framed paths now use the backend nonlinear element support, but material modelling is still a simplified single-steel runtime setup.",
    },
    "steel_grade": {
        "title": "Steel Grade",
        "purpose": "DNV-RP-C208 steel grade used for nonlinear shell plasticity.",
        "use": "Available presets are S235, S275, S355, S420 and S460. The values are the low-fractile true stress-strain properties from DNV-RP-C208 Table 4-2 to Table 4-6.",
        "output": "Sets E, sigma_prop, sigma_yield, sigma_yield_2, eps_p_y1, eps_p_y2, K and n for the nonlinear shell material curve.",
        "caution": "Use the grade matching the plate material. If an imported model has mixed steels, this single setting is still a simplification.",
    },
    "steel_thickness_class": {
        "title": "Steel Thickness Class",
        "purpose": "Selects the DNV-RP-C208 table column for the chosen steel grade.",
        "use": "Auto uses the generated plate thickness. Manual choices force a table class such as t <= 16 mm or 16 < t <= 40 mm.",
        "output": "Changes the low-fractile yield and hardening values used by the material nonlinear solver.",
        "caution": "Some grades in the RP tables are only provided up to 63 mm in the attached values; auto uses the largest available class when the thickness exceeds the listed range.",
    },
    "nonlinear_max_load_factor": {
        "title": "Nonlinear Max Load Factor",
        "purpose": "Maximum proportional load multiplier attempted by the incremental nonlinear static solver.",
        "use": "The load case is ramped from zero to this factor using adaptive increments. If convergence fails repeatedly, the solver reports the last stable factor.",
        "output": "Controls whether the result is a reached target load or a stopped-at-limit estimate.",
        "caution": "A very high value can increase runtime. A value of 1.0 checks the design load only; it may not find collapse.",
    },
    "nonlinear_steps": {
        "title": "Nonlinear Steps",
        "purpose": "Initial number of proportional load increments for nonlinear static analysis.",
        "use": "The solver starts with max load factor divided by this count, then halves or grows the increment adaptively depending on Newton convergence.",
        "output": "Affects runtime, convergence robustness and the load factor resolution near a limit.",
        "caution": "Too few steps can make a nonlinear solve fail early. Too many steps can be slow.",
    },
    "nonlinear_max_iterations": {
        "title": "Nonlinear Max Iterations",
        "purpose": "Maximum Newton iterations allowed inside one nonlinear load increment.",
        "use": "Each increment solves internal force equilibrium. The solver retries difficult increments with line search before cutting the step size.",
        "output": "Printed as total Newton iterations in the nonlinear static result.",
        "caution": "Increasing this may help difficult cases but can also spend time on a step that should be cut smaller.",
    },
    "nonlinear_tolerance": {
        "title": "Nonlinear Tolerance",
        "purpose": "Relative residual tolerance for Newton convergence in nonlinear static analysis.",
        "use": "The increment converges when the reduced residual norm is below this tolerance times the reference load norm.",
        "output": "Controls numerical convergence strictness of the nonlinear static status.",
        "caution": "Very tight tolerances can make plastic or near-limit steps expensive. Very loose tolerances can hide residual imbalance.",
    },
    "nonlinear_layers": {
        "title": "Nonlinear Layers",
        "purpose": "Number of through-thickness Gauss-Lobatto layers used for shell plasticity.",
        "use": "Layered integration captures bending plastification through the plate thickness. Supported values are odd Lobatto rules such as 3, 5, 7, 9 or 11.",
        "output": "Affects plastic strain, bending capacity and nonlinear static runtime.",
        "caution": "Five layers is a practical default. More layers cost more but can improve plastic bending resolution.",
    },
    "nonlinear_solution_control": {
        "title": "Nonlinear Solution Control",
        "purpose": "Chooses the nonlinear static path-following method.",
        "use": "Newton force control is the default proportional load-step solve. Arc length uses bounded Crisfield-style continuation to trace through a limit point and report the peak load factor.",
        "output": "Changes nonlinear static control mode and result interpretation; it does not change element formulation or loads.",
        "caution": "Arc length is more expensive and intended for collapse/path-following checks. Keep Newton for ordinary target-load verification.",
    },
    "post_buckling_enabled": {
        "title": "Post-buckling",
        "purpose": "Trace the post-buckling (post-collapse) response instead of stopping at the limit point.",
        "use": "Forces a FULL geometric + material nonlinear arc-length solve: the Analysis, Material and NL "
               "control fields are set automatically (geom. + material nonlinear static, DNV-RP-C208 steel, arc "
               "length) because an elastic post-buckling branch is non-physical for steel design. Follows the "
               "descending equilibrium branch after the peak; use with an imperfection so the buckling mode is "
               "seeded.",
        "output": "The equilibrium path (load factor vs displacement) continues past the peak; the live run graph "
                  "shows the full path and the result reports the peak and final load factors.",
        "caution": "Post-buckling paths can be mesh- and imperfection-sensitive. The trace stops automatically at "
                   "the configured load fraction, displacement guard, or step limit.",
    },
    "post_buckling_stop_load_fraction": {
        "title": "Post-buckling Stop Fraction",
        "purpose": "Automatic stop: end the trace when the load factor has fallen to this fraction of the peak.",
        "use": "0.5 traces until half the peak load is shed; smaller values follow the collapse further.",
        "output": "Sets how much of the descending branch is resolved; status becomes 'post buckling traced'.",
        "caution": "Very small fractions can require many arc-length steps on flat post-collapse plateaus.",
    },
    "post_buckling_max_displacement_m": {
        "title": "Post-buckling Displacement Guard",
        "purpose": "Optional absolute stop on the largest nodal translation, in metres.",
        "use": "0 disables the guard. Set a physical bound (e.g. several plate thicknesses) to stop runaway paths.",
        "output": "The trace stops with status 'displacement limit reached' when exceeded.",
        "caution": "A too-tight guard can stop the trace before the post-buckling response develops.",
    },
    "nonlinear_convergence_profile": {
        "title": "Nonlinear Convergence Profile",
        "purpose": "Selects automatic Newton globalization and adaptive load-step behavior for nonlinear static runs.",
        "use": "Auto is the default. Fast grows smooth increments more aggressively, robust uses stronger line search for difficult plastic or near-limit cases, and legacy keeps the previous behavior.",
        "output": "Changes convergence speed and robustness only; it does not change element theory or loads.",
        "caution": "Fast is best for well-behaved cases. Use robust when convergence stalls or near collapse.",
    },
    "nonlinear_assembly_threads": {
        "title": "Nonlinear Assembly Threads",
        "purpose": "Controls backend worker threads used during nonlinear tangent/internal-force assembly.",
        "use": "Use 0 for the runtime auto policy. Auto keeps small models serial, uses a small count for medium models, and caps larger models to avoid oversubscription. Enter a positive integer to force a manual count.",
        "output": "The resolved assembly thread count is printed in nonlinear static and nonlinear impact summaries.",
        "caution": "More threads can be slower when assembly work is small or when sparse factorization is already using CPU resources. Treat manual high counts as something to benchmark.",
    },
    "nonlinear_static_kinematics": {
        "title": "Nonlinear Static Kinematics",
        "purpose": "Selects the geometric kinematics for direct nonlinear static solves.",
        "use": "Von Karman is the default and preserves previous behavior. Corotational is available for direct Newton nonlinear static runs with large rotations such as panel folding or tripping.",
        "output": "Reported in the nonlinear static result summary and passed to the backend only for the direct solve_static_nonlinear path.",
        "caution": "Arc length, tangent-stability, capacity workflow and linear paths keep Von Karman. Corotational static does not support fracture/erosion.",
    },
    "beam_consistent_mass": {
        "title": "Consistent Beam Mass",
        "purpose": "Uses consistent beam mass matrices for generated stiffener and girder sections.",
        "use": "Enable for modal or transient studies where beam rotational inertia affects natural frequencies. Leave off to preserve previous lumped-mass results.",
        "output": "Beam section dictionaries carry consistent_mass=True into the backend model.",
        "caution": "This affects mass/inertia, not static stiffness. Compare against previous lumped-mass baselines when reproducing old runs.",
    },
    "display_choice": {
        "title": "Display",
        "purpose": "Chooses which result visualization is shown after a run.",
        "use": "Static view shows displacement/stress. Engineering plastic strain is available after a material nonlinear run. Buckling mode views show mode shape and load factor.",
        "output": "Only affects plotting; it does not rerun the solver.",
        "caution": "Mode amplitudes are normalized for visualization, not physical displacement magnitudes.",
    },
    "plate_front_color": {
        "title": "Plate Front Colour",
        "purpose": "Sets the colour used for the generated plate front side in the base 3D view.",
        "use": "Enter a colour name such as grey or a hex value such as #d1d5db.",
        "output": "Only changes the base 3D preview. Result contour colours are unchanged.",
        "caution": "Invalid colour text falls back to the default front grey.",
    },
    "plate_back_color": {
        "title": "Plate Back Colour",
        "purpose": "Sets the colour used for the generated plate back side in the base 3D view.",
        "use": "Enter a colour name such as brown or a hex value such as #8b5e3c.",
        "output": "Only changes the base 3D preview. Result contour colours are unchanged.",
        "caution": "Invalid colour text falls back to the default back brown.",
    },
    "deformation_scale": {
        "title": "Deformation Scale",
        "purpose": "Controls the visual magnification of displacement in the 3D result plot.",
        "use": "Set 0 for automatic scaling. Set a positive value to multiply physical displacements by that value in the plot.",
        "output": "Only affects the visualization. The solver, stresses and load factors are not changed.",
        "caution": "A very large scale can make the shape easier to see but can also make the geometry look physically misleading.",
    },
    "nullspace_projection": {
        "title": "Nullspace Projection",
        "purpose": "Explains how the linear solver handles a free-free or under-constrained model.",
        "use": "After fixed supports and MPCs are applied, the solver checks for rigid-body modes. If no fixed DOFs remain and rigid-body modes are present, the static solve uses an augmented nullspace system. This projects out pure rigid-body motion and returns a gauged deformation field.",
        "output": "The run print says whether nullspace projection was used. If it is used with non-self-equilibrated loads, the core solver may also report balancing generalized reactions.",
        "caution": "Nullspace projection is not a physical support. It prevents numerical rigid-body drift so stress recovery can proceed. For a physical static solution, use self-equilibrated loads or define real supports.",
    },
    "custom_load_bc_enabled": {
        "title": "Custom Load/BC Mode",
        "purpose": "Switches from automatic generated boundary/load assumptions to user-defined supports and edge loads.",
        "use": "When enabled, plate side supports or cylinder end supports are taken only from the custom fields below. By default the imported pressure, axial force and end moment inputs are not used; enter manual pressure and edge loads here instead. Tick the additive-load option if the custom loads should be added to those imported/generated loads.",
        "output": "The run summary prints the custom support choices and edge loads. Diagnostics show that custom mode is active.",
        "caution": "This mode can easily create free-free or over-constrained models. Check the nullspace projection status and load resultant after each run.",
    },
    "custom_loads_add_to_imported": {
        "title": "Add To Imported Loads",
        "purpose": "Controls whether custom edge loads replace or supplement the pressure and other generated load inputs.",
        "use": "Unchecked means manual pressure and custom edge loads are the complete load case. Checked means imported/generated pressure, axial force and top/bottom moment are applied first, then manual pressure and custom edge loads are added.",
        "output": "Changes load resultant, stress recovery and buckling prestress.",
        "caution": "Use this deliberately. Leaving it unchecked is safest when studying a clean custom load path.",
    },
    "custom_pressure_pa": {
        "title": "Manual Pressure",
        "purpose": "Pressure value used inside custom load/BC mode.",
        "use": "When custom mode is active and additive loads are unchecked, this pressure replaces the imported pressure from the active line. When additive loads are checked, it is added to the imported/generated pressure.",
        "output": "Affects shell pressure loads, displacement, stress recovery and buckling prestress.",
        "caution": "Manual mode assumes the user has evaluated whether pressure, edge loads and supports form the intended load case.",
    },
    "custom_use_nullspace_projection": {
        "title": "Nullspace Boundary",
        "purpose": "Uses rigid-body nullspace projection as the boundary condition for custom load/BC mode.",
        "use": "No explicit support edges are applied. The solver projects out rigid-body motion and reports any rigid-body load imbalance as balancing generalized reactions.",
        "output": "The result print reports nullspace rank and relative rigid-body load imbalance.",
        "caution": "This is a mathematical free-body gauge, not a physical support. It is useful for understanding self-equilibrated loads and free-body behaviour.",
    },
    "allow_unbalanced_free_free": {
        "title": "Allow Free-Free Imbalance",
        "purpose": "Explicitly allows the backend to solve a free-free or nullspace-gauged static problem even when loads are not self-equilibrated.",
        "use": "When enabled, rigid-body generalized load components are not rejected; they are reported as balancing generalized reactions. Selecting the nullspace boundary also enables this behaviour because the user has explicitly chosen a mathematical free-body gauge.",
        "output": "The result print reports relative rigid-body load imbalance and notes that generalized balancing reactions were allowed.",
        "caution": "This does not create a physical support. For pressure-loaded flat plates, define real edge supports unless the goal is a deliberate free-body load-path study.",
    },
    "plate_edge_supports": {
        "title": "Plate Edge Supports",
        "purpose": "Defines supports on the four generated plate sides x0, x1, y0 and y1.",
        "use": "Free applies no restraint. Simply supported restrains out-of-plane displacement. Fixed restrains translations and rotations on the selected edge.",
        "output": "Changes support constraints, displacement, stress recovery and buckling factors.",
        "caution": "The side names follow generated coordinates: x0/x1 are the low/high x edges, y0/y1 are the low/high y edges.",
    },
    "cylinder_end_supports": {
        "title": "Cylinder End Supports",
        "purpose": "Defines support assumptions at the lower and upper cylinder ends.",
        "use": "Free applies no restraint. Simply supported restrains axial displacement at the end. Fixed restrains translations at the end. If rigid lids are active, support is applied to the lid reference node.",
        "output": "Changes cylinder global stiffness, membrane stress recovery and buckling factors.",
        "caution": "Fixed cylinder ends can significantly increase membrane stiffness. Use free or simple ends when global motion should be allowed.",
    },
    "plate_edge_loads": {
        "title": "Plate Edge Loads",
        "purpose": "Adds in-plane normal line loads to plate edges in N/m.",
        "use": "Positive x0/x1 loads act outward from the low/high x sides. Positive y0/y1 loads act outward from the low/high y sides.",
        "output": "Loads are distributed to edge nodes and included in the load resultant, recovered stresses and buckling prestress.",
        "caution": "Use sign carefully. Compressive edge load usually means load directed into the panel, which may require a negative value on an outward-positive edge.",
    },
    "cylinder_edge_loads": {
        "title": "Cylinder End Edge Loads",
        "purpose": "Adds axial line loads to lower and upper cylinder end rings in N/m.",
        "use": "Positive lower load acts in negative global z, and positive upper load acts in positive global z, giving an outward end-pull convention.",
        "output": "Loads are distributed around the end ring and included in load resultant, stresses and buckling prestress.",
        "caution": "For axial compression, choose signs so the loads act toward the cylinder mid-height.",
    },
    "selected_edge_load_components": {
        "title": "Selected-Edge Load Components",
        "purpose": "Applies distributed loads to the right-clicked edge segments as separate fx/fy/fz forces in N/m and mx/my/mz moments in Nm/m.",
        "use": "Enter the components on the global axes, select edge segments in the 3D view and press Add load. A component left at 0 applies nothing; there are no implicit directions or sign conventions.",
        "output": "Each added entry appears in the loads-to-run list and is distributed to the segment nodes, included in the load resultant, stresses and buckling prestress.",
        "caution": "Values are per metre of edge length. Moments load the rotational shell DOFs directly, so use them for genuine edge torques rather than force couples.",
    },
    "edge_load_components": {
        "title": "Whole-Edge Load Components",
        "purpose": "Applies distributed loads to the whole edge picked above as separate fx/fy/fz forces in N/m and mx/my/mz moments in Nm/m.",
        "use": "Pick an edge (or All) with the radio buttons, then enter the components on the global axes. Each edge remembers its own values when you switch, like the per-edge boundary conditions.",
        "output": "Loads are distributed along the full edge or end ring and included in the load resultant, stresses and buckling prestress.",
        "caution": "Components are entered on global axes with no outward-positive convention, unlike the legacy scalar edge loads. The All choice loads every boundary edge with the same global components.",
    },
    "edge_load_edge_select": {
        "title": "Edge Selection For Whole-Edge Loads",
        "purpose": "Chooses which plate edge or cylinder end the component grid below edits.",
        "use": "x0/x1 are the low/high x edges and y0/y1 the low/high y edges; cylinders offer bottom and top rings. All applies one component set to every boundary edge.",
        "output": "Switching edges stores the grid into the per-edge load set included in the run.",
        "caution": "Check each edge before running: a non-zero grid left on a previously edited edge stays active even though it is not currently displayed.",
    },
}

FEM_OPTION_INFO.update({
    "collision_enabled": {
        "title": "Collision Transient",
        "purpose": "Runs the rigid-sphere impact solver instead of the usual static/eigenvalue workflow.",
        "use": "Enable this for one rigid sphere travelling along the specified vector. At least one real side/end support is required; nullspace/free-body collision is not used.",
        "output": "Produces saved time snapshots, sphere motion, contact force, penetration, energy balance and optional deleted/eroded element summaries.",
        "caution": "This is frictionless rigid-sphere contact against shell surfaces and, when enabled, direct beam/stiffener targets. Contact friction, fluid-structure interaction and calibrated fracture mechanics are not included.",
    },
    "collision_include_static_load": {
        "title": "Collision Base Load",
        "purpose": "Adds the current generated/static FE load vector as a constant base load during the collision transient.",
        "use": "Leave off for an isolated impact event. Enable only when the sphere impact is intentionally superposed on pressure, axial force, moment or custom static loads.",
        "output": "Changes the transient displacement and stress state used during contact.",
        "caution": "This can double count loading if the static load represents the same physical event as the impact.",
    },
    "collision_mass_kg": {
        "title": "Sphere Mass",
        "purpose": "Rigid sphere mass used for translational inertia.",
        "use": "Enter the impacting body's mass directly in kg. Radius affects geometry/contact only; it does not imply density.",
        "output": "Controls sphere deceleration, impulse and contact duration.",
        "caution": "Very large mass or speed can require smaller time steps and stronger supports.",
    },
    "collision_radius_m": {
        "title": "Sphere Radius",
        "purpose": "Rigid sphere radius used for contact geometry and preview display.",
        "use": "The preview sphere updates immediately from this value. The solver uses this radius for closest-point contact and automatic time-step estimates.",
        "output": "Affects first contact time, contact area estimate, penetration ratio and damage demand.",
        "caution": "Beam contact uses each beam section's contact radius when provided, otherwise the backend equivalent-area radius is used automatically.",
    },
    "collision_beam_contact": {
        "title": "Direct Beam Contact",
        "purpose": "Allows the rigid sphere to contact generated stiffener/girder beam targets directly.",
        "use": "Enable for edge-on hits or cases where the striker may hit a stiffener or girder rather than only shell plating. Leave off to preserve previous shell-only contact behavior.",
        "output": "The collision result reports beam contact enabled and backend diagnostics include beam/contact warnings when applicable.",
        "caution": "Capacity-based impact damage remains shell-contact based; use material nonlinear plastic damage for beam erosion.",
    },
    "collision_speed_mps": {
        "title": "Sphere Speed",
        "purpose": "Initial speed along the travel vector.",
        "use": "The travel vector sets direction; this value sets magnitude in m/s.",
        "output": "Controls kinetic energy, impulse and automatic total time/dt estimates.",
        "caution": "Higher speeds need smaller dt. Auto time setup limits step count, but inspect resolved dt in the result text.",
    },
    "collision_contact_surface": {
        "title": "Contact Surface",
        "purpose": "Chooses the shell contact surface used by the sphere.",
        "use": "Midsurface is the default. Top or bottom offsets contact by shell half-thickness according to shell normal convention.",
        "output": "Changes first contact time, penetration and load distribution.",
        "caution": "Use top/bottom only when the shell normal convention is clear for the model.",
    },
    "collision_start_x_m": {
        "title": "Sphere Start X",
        "purpose": "Initial global X coordinate of the sphere centre.",
        "use": "Changing this value moves the preview sphere immediately when collision preview is visible.",
        "output": "Affects trajectory, first-contact location and automatic timing.",
        "caution": "The start point is the sphere centre, not the nearest surface point.",
    },
    "collision_start_y_m": {
        "title": "Sphere Start Y",
        "purpose": "Initial global Y coordinate of the sphere centre.",
        "use": "Changing this value moves the preview sphere immediately when collision preview is visible.",
        "output": "Affects trajectory, first-contact location and automatic timing.",
        "caution": "The start point is the sphere centre, not the nearest surface point.",
    },
    "collision_start_z_m": {
        "title": "Sphere Start Z",
        "purpose": "Initial global Z coordinate of the sphere centre.",
        "use": "Changing this value moves the preview sphere immediately when collision preview is visible.",
        "output": "Affects trajectory, first-contact location and automatic timing.",
        "caution": "For cylinders, generated axial height is along global Z in the runtime view.",
    },
    "collision_vector_x": {
        "title": "Travel Vector X",
        "purpose": "X component of the sphere travel direction.",
        "use": "The vector is normalized internally; combine X/Y/Z entries to aim the sphere.",
        "output": "Affects contact location and automatic timing.",
        "caution": "The vector must not be zero.",
    },
    "collision_vector_y": {
        "title": "Travel Vector Y",
        "purpose": "Y component of the sphere travel direction.",
        "use": "The vector is normalized internally; combine X/Y/Z entries to aim the sphere.",
        "output": "Affects contact location and automatic timing.",
        "caution": "The vector must not be zero.",
    },
    "collision_vector_z": {
        "title": "Travel Vector Z",
        "purpose": "Z component of the sphere travel direction.",
        "use": "The vector is normalized internally; combine X/Y/Z entries to aim the sphere.",
        "output": "Affects contact location and automatic timing.",
        "caution": "The vector must not be zero.",
    },
    "collision_time_mode": {
        "title": "Collision Time Setup",
        "purpose": "Chooses automatic or manual collision time stepping.",
        "use": "Auto estimates first arrival from the sphere path and model bounds, then chooses dt from sphere travel per step and optional contact penalty period. Manual uses the entered total time and dt.",
        "output": "Resolved dt, total time and estimated arrival are printed after a run.",
        "caution": "Auto is a practical starting point, not a substitute for time-step convergence checks on final impact cases.",
    },
    "collision_auto_steps_per_radius": {
        "title": "Auto Steps Per Radius",
        "purpose": "Controls automatic time-step fineness by limiting sphere travel per step.",
        "use": "A value of 20 means the sphere travels about radius/20 per step before step-count guards are applied.",
        "output": "Higher values reduce dt and increase runtime.",
        "caution": "Use higher values for sharp contact events or high penalty stiffness.",
    },
    "collision_auto_post_contact": {
        "title": "Auto Post-Contact Time",
        "purpose": "Adds extra automatic simulation time after the sphere has crossed the model bounds.",
        "use": "The value is measured in sphere radii of travel after contact traversal.",
        "output": "Larger values save more rebound/free-vibration history.",
        "caution": "Longer histories increase runtime and result storage.",
    },
    "collision_bounce_back_time": {
        "title": "Bounce-Back Stop Hold",
        "purpose": "Stops collision runs cleanly after the sphere has separated from contact for this duration.",
        "use": "Use a small value to keep a visible rebound tail without simulating long free-flight. Set zero to disable this early stop.",
        "output": "Successful early stops report completed_after_contact_separation instead of a contact failure.",
        "caution": "This is a stop criterion only; it does not change contact force, damping or impact response before separation.",
    },
    "collision_total_time_s": {
        "title": "Manual Total Time",
        "purpose": "Total transient duration used when time setup is manual.",
        "use": "Choose a duration long enough to include approach, contact and rebound/free vibration.",
        "output": "Controls saved time range and peak search duration.",
        "caution": "Ignored in auto mode except as a fallback if automatic setup cannot estimate geometry.",
    },
    "collision_dt_s": {
        "title": "Manual Time Step",
        "purpose": "Fixed transient time step used when time setup is manual.",
        "use": "Choose dt small enough to resolve contact. A common starting point is sphere radius divided by speed and by 20 or more.",
        "output": "Controls accuracy and runtime.",
        "caution": "Ignored in auto mode except as a fallback if automatic setup cannot estimate geometry.",
    },
    "collision_result_interval_s": {
        "title": "Collision Result Interval",
        "purpose": "Controls spacing of saved animation/result snapshots.",
        "use": "Set zero to save every solver step. Enter a positive interval to decimate saved frames.",
        "output": "Controls available animation frames and result-case time snapshots.",
        "caution": "Saving every step can be heavy for long fine-step runs.",
    },
    "collision_penalty_stiffness": {
        "title": "Contact Penalty",
        "purpose": "Normal penalty stiffness for sphere-shell contact.",
        "use": "Leave zero for automatic recommendation. Enter a positive N/m value to force a penalty.",
        "output": "Higher values reduce penetration but can require smaller dt and more iterations.",
        "caution": "Too high can make contact numerically stiff; too low permits excessive penetration.",
    },
    "collision_penalty_scale": {
        "title": "Automatic Penalty Scale",
        "purpose": "Scales ANYsolver's automatically estimated contact penalty without replacing it.",
        "use": "Leave at 1.0 normally. Values below 1 soften stubborn contact iterations; values above 1 reduce penetration but increase numerical stiffness.",
        "output": "Changes the resolved automatic contact penalty and its provenance. A positive manual penalty overrides this scale.",
        "caution": "Use positive values only. Excessively high values can make nonlinear contact convergence worse.",
    },
    "collision_auto_precondition": {
        "title": "Extra-conservative contact",
        "purpose": "Softens the contact penalty further for stubborn high-energy impacts that still fail to "
                   "converge at the automatic penalty.",
        "use": "The automatic penalty is already capped at the shell contact-stiffness scale (E*t) so contact "
               "stays well conditioned at any mesh. Enable this only if a heavy/fast impact still reports "
               "'nonlinear iteration failed'; it halves the penalty for more margin. Ignored when a manual "
               "penalty is set.",
        "output": "The resolved penalty basis reports the applied scale factor.",
        "caution": "Softer contact slightly increases penetration; leave off for ordinary impacts.",
    },
    "collision_contact_damping": {
        "title": "Contact Damping",
        "purpose": "Optional normal damping in the penalty contact law.",
        "use": "Use small nonnegative values to reduce contact oscillation.",
        "output": "Changes rebound, energy balance and peak force.",
        "caution": "Damping is numerical/engineering damping, not friction or material loss modelling.",
    },
    "collision_max_iterations": {
        "title": "Max Contact Iterations",
        "purpose": "Maximum contact-force iterations per time step/substep.",
        "use": "Increase if contact_iteration_failed appears in diagnostics.",
        "output": "Affects convergence robustness and runtime.",
        "caution": "Repeated failures usually indicate dt/penalty/support issues, not just too few iterations.",
    },
    "collision_penetration_tolerance": {
        "title": "Penetration Tolerance",
        "purpose": "Convergence tolerance for penetration change during contact iteration.",
        "use": "Smaller values require more stable contact iteration before accepting a step.",
        "output": "Affects contact convergence status.",
        "caution": "Very small values can increase iterations without meaningful accuracy gain.",
    },
    "collision_force_tolerance": {
        "title": "Force Tolerance",
        "purpose": "Relative contact-force convergence tolerance.",
        "use": "The contact iteration stops when force change is small relative to current contact force scale.",
        "output": "Affects contact convergence status and step acceptance.",
        "caution": "Very tight tolerances increase runtime.",
    },
    "collision_target_penetration": {
        "title": "Target Penetration Fraction",
        "purpose": "Target penetration fraction used by automatic penalty recommendation.",
        "use": "A value of 0.01 targets penetration around one percent of sphere radius in the recommendation model.",
        "output": "Affects automatically selected contact penalty.",
        "caution": "This is a recommendation target, not a hard bound.",
    },
    "collision_max_event_substeps": {
        "title": "Max Event Substeps",
        "purpose": "Maximum substeps used when the sphere may cross the shell surface within one time step.",
        "use": "Increase for high-speed impacts where contact can be missed between coarse steps.",
        "output": "Improves event capture at the cost of more contact work.",
        "caution": "If many event substeps are used, consider reducing dt or increasing auto steps/radius.",
    },

    "collision_material_nonlinear": {
        "title": "Material Nonlinear Impact",
        "purpose": "Uses the nonlinear transient impact path so plastic strain can be committed during collision.",
        "use": "Enable for damage driven by equivalent plastic strain. Leave off for the faster linear elastic contact proxy.",
        "output": "Makes Equivalent Plastic Strain available when plasticity develops and reports Newton iterations/cutbacks.",
        "caution": "This is much slower than the linear collision path and still uses simplified frictionless rigid-sphere contact.",
    },
    "collision_nonlinear_kinematics": {
        "title": "Impact Kinematics",
        "purpose": "Selects Von Karman or corotational kinematics for material nonlinear collision runs.",
        "use": "Von Karman preserves previous behavior. Corotational is useful when the struck panel can fold or rotate through large angles during impact.",
        "output": "Passed into NonlinearTransientConfig and reported in the collision result summary.",
        "caution": "This selector is active only when collision and material nonlinear impact are both enabled; linear impact keeps Von Karman.",
    },
    "collision_nonlinear_iterations": {
        "title": "Impact Newton Iterations",
        "purpose": "Maximum Newton iterations for each nonlinear impact substep.",
        "use": "Increase if a nonlinear impact step fails after contact or plasticity starts.",
        "output": "Affects robustness and runtime.",
        "caution": "Convergence failures usually also need smaller dt or more cutbacks.",
    },
    "collision_nonlinear_tolerance": {
        "title": "Impact Residual Tolerance",
        "purpose": "Residual tolerance for the material-nonlinear transient equilibrium iterations.",
        "use": "Use the default for screening; tighten for convergence studies.",
        "output": "Affects accepted nonlinear impact steps.",
        "caution": "Overly tight tolerance can make impact runs slow or fail without improving engineering decisions.",
    },
    "collision_nonlinear_cutbacks": {
        "title": "Impact Cutbacks",
        "purpose": "Maximum automatic time-step halvings when a nonlinear impact step fails.",
        "use": "Higher values allow the solver to recover from abrupt contact/plasticity events.",
        "output": "Increases robustness at the cost of more substeps.",
        "caution": "Many cutbacks indicate the requested dt/penalty/contact setup should be reviewed.",
    },
    "collision_damage_criterion": {
        "title": "Damage Criterion",
        "purpose": "Select the evaluation method for plasticity-based impact damage.",
        "use": "Fixed applies the manual strain threshold. Mesh-scaled (GL) computes the limit per element from "
               "thickness/size (0.056 + 0.54 t/l). RTCL additionally weights damage by stress triaxiality "
               "(Rice-Tracey/Cockcroft-Latham, the standard in ship-collision analysis): no damage in compression, "
               "reduced in shear, accelerated in biaxial tension, on top of the mesh-scaled limit. RTCL modified "
               "recalibrates the limit so plane-strain tension fails exactly at the GL curve (limit x 1.44).",
        "output": "RTCL gives the most stable erosion: compressed dent sides no longer erode spuriously and damage "
                  "accumulates smoothly instead of jumping with the plastic-strain peak.",
        "caution": "Mesh-scaled (GL) and RTCL ignore the manual threshold for shell elements (beams still use it).",
    },
    "collision_plastic_damage_threshold": {
        "title": "Plastic Damage Strain",
        "purpose": "Equivalent plastic strain threshold for plasticity-based impact damage/erosion.",
        "use": "Used only when material nonlinear impact and damage are enabled.",
        "output": "Controls when damaged shell/beam elements soften or delete after converged substeps.",
        "caution": "This is engineering erosion, not calibrated crack propagation.",
    },
    "collision_damage_enabled": {
        "title": "Impact Damage",
        "purpose": "Activates engineering damage/erosion during collision.",
        "use": "Capacity-based damage accumulates from shell contact demand. With material nonlinear impact enabled, plastic-damage erosion also applies to backend-supported shell and beam element states.",
        "output": "Deleted/fully damaged elements are removed from the visualization and reported in the result text.",
        "caution": "Capacity-based impact damage is shell-only; with direct beam contact use material nonlinear plastic damage for beam erosion. This is not crack propagation or validated fracture mechanics.",
    },
    "collision_damage_mode": {
        "title": "Damage Mode",
        "purpose": "Chooses accumulated or instant threshold damage behavior.",
        "use": "Accumulated damage allows repeated/subthreshold contact to build damage. Instant threshold reacts to a single exceeded demand.",
        "output": "Changes when softening/deletion occurs.",
        "caution": "Accumulated damage is usually the more stable screening mode.",
    },
    "collision_damage_capacity": {
        "title": "Damage Capacity Basis",
        "purpose": "Material capacity reference for impact damage utilization.",
        "use": "Yield uses yield stress, ultimate proxy uses a higher proxy, and user uses the entered capacity value.",
        "output": "Higher capacity delays damage and deletion.",
        "caution": "User capacity must be positive when selected.",
    },
    "collision_damage_user_capacity": {
        "title": "User Damage Capacity",
        "purpose": "User-defined capacity in MPa for impact damage calculations.",
        "use": "Only used when capacity basis is user.",
        "output": "Controls damage utilization scaling.",
        "caution": "This is an engineering screening input; choose defensible values.",
    },
    "collision_damage_softening": {
        "title": "Damage Softening Start",
        "purpose": "Damage level where stiffness/contact participation starts reducing.",
        "use": "Values below delete-at create gradual softening before deletion.",
        "output": "Affects impact force redistribution and later contact response.",
        "caution": "Too low can over-soften from small numerical damage.",
    },
    "collision_damage_delete_at": {
        "title": "Damage Deletion Level",
        "purpose": "Damage level at which a shell element is treated as fully eroded/deleted.",
        "use": "Default 1.0 deletes at full damage.",
        "output": "Deleted/eroded elements are hidden in visualization and removed from later contact/load participation where the backend erosion scope applies.",
        "caution": "Topology is still simplified for screening; do not treat deletion as calibrated fracture separation.",
    },
    "collision_damage_min_area": {
        "title": "Minimum Contact Area",
        "purpose": "Lower bound on estimated contact patch area used for damage demand.",
        "use": "Prevents unrealistically high pressure from vanishingly small numerical contact areas.",
        "output": "Affects contact pressure utilization and damage accumulation.",
        "caution": "Choose an area consistent with mesh size and shell thickness for final screening.",
    },
    "collision_damage_max_deleted": {
        "title": "Max Deleted Fraction",
        "purpose": "Stops the collision damage run after too much shell area has been eroded.",
        "use": "Keeps the v1 erosion model inside a controlled range.",
        "output": "Can stop the transient with a max-deleted-fraction status.",
        "caution": "Large deletion fractions are outside this simplified model's intended reliability.",
    },
    "collision_damage_smoothing": {
        "title": "Neighbor Smoothing",
        "purpose": "Reduces isolated single-element damage spikes.",
        "use": "Enable when a coarse contact mesh produces isolated erosion not supported by neighbouring/contact history.",
        "output": "Can delay or prevent isolated deletion.",
        "caution": "This is a numerical guardrail, not a crack-path model.",
    },
    "show_collision_sphere": {
        "title": "Show Rigid Sphere",
        "purpose": "Displays the rigid sphere in preview and result snapshots.",
        "use": "When collision is enabled, the pre-result sphere updates from start/radius inputs. Result snapshots show saved sphere positions.",
        "output": "Changes visualization only.",
        "caution": "The displayed sphere represents the rigid body centre/radius, not deformation or spin.",
    },
})

FEM_OPTION_INFO.update({
    "ignore_girder_length": {
        "title": "Ignore Girder Length",
        "purpose": "Models a single stiffener bay instead of the full girder length LG.",
        "use": "When off (default), the panel width follows the girder length so several stiffeners and girder bays are meshed. Turn it on to analyse one stiffener spacing only, matching the classic single-bay idealization.",
        "output": "Changes the generated panel width, stiffener count and girder stations shown in the mesh preview and used by the solver.",
        "caution": "A single bay cannot capture girder bending or multi-bay interaction; keep it off when girder response matters.",
    },
    "member_model": {
        "title": "Member Model",
        "purpose": "Chooses how stiffeners and girders are idealized in the FE model.",
        "use": "'plates as shell, girders as beams' uses beam elements for all members. 'webs as shells, flanges as beams' meshes member webs with shell elements and keeps flanges as beams. 'all shell' meshes webs and flanges as shells.",
        "output": "Changes mesh size, member stress recovery (beam fiber sections vs shell layers) and the surfaces shown in the 3D result view.",
        "caution": "Shell-web models are heavier to solve; beam models cannot show local web buckling or web plasticity distribution.",
    },
    "acceleration_y_m_s2": {
        "title": "Acceleration X / Y / Z",
        "purpose": "Body-load acceleration field in the global x, y and z directions (m/s^2).",
        "use": "Each nonzero component applies a consistent inertial body load over the structure and added masses; see the Accel X info for details.",
        "output": "Adds distributed nodal forces; reported in the load resultant and reaction summary.",
        "caution": "Accelerations act on structural mass, so density and added masses must be realistic.",
    },
    "acceleration_z_m_s2": {
        "title": "Acceleration X / Y / Z",
        "purpose": "Body-load acceleration field in the global x, y and z directions (m/s^2).",
        "use": "Each nonzero component applies a consistent inertial body load over the structure and added masses; set Z to -9.81 for a 1 g gravity check.",
        "output": "Adds distributed nodal forces; reported in the load resultant and reaction summary.",
        "caution": "Accelerations act on structural mass, so density and added masses must be realistic.",
    },
    "torsional_moment_nm": {
        "title": "Torsional Moment",
        "purpose": "Applies a torsional moment about the cylinder axis in Nm.",
        "use": "The moment is distributed as tangential edge loads on the cylinder end rings, twisting the shell about its axis.",
        "output": "Shown in diagnostics and included in the load resultant, stresses and buckling prestress.",
        "caution": "Only meaningful for cylinder geometries; flat panels ignore it.",
    },
    "shear_force_n": {
        "title": "Shear Force",
        "purpose": "Applies a transverse shear force in N across the cylinder section.",
        "use": "The force is distributed over the end ring as a transverse load, giving beam-like shear of the whole cylinder.",
        "output": "Shown in diagnostics and included in the load resultant, stresses and buckling prestress.",
        "caution": "Only meaningful for cylinder geometries; flat panels ignore it.",
    },
    "fracture_enabled": {
        "title": "Strain-Triggered Erosion",
        "purpose": "Deletes shell elements whose plastic strain exceeds the threshold during nonlinear solves.",
        "use": "Enable together with a material-nonlinear analysis to trace tearing/penetration-style failures. The thresholds below control when and how much material may be removed.",
        "output": "Deleted elements vanish from the result view; diagnostics report the deleted count and the load level at first erosion.",
        "caution": "Erosion is mesh-dependent and needs Von Karman kinematics; use it for capacity trends, not as a certified fracture model.",
    },
    "fracture_strain_threshold": {
        "title": "Plastic Strain Threshold",
        "purpose": "Equivalent plastic strain at which a shell element is considered failed.",
        "use": "Typical shipbuilding steel values are 0.1-0.2 depending on mesh size; smaller meshes tolerate larger thresholds.",
        "output": "Elements above the threshold are eroded (deleted or softened) during the nonlinear solve.",
        "caution": "The threshold is mesh-size dependent. Calibrate against tests or rules before drawing conclusions.",
    },
    "fracture_residual_stiffness": {
        "title": "Residual Stiffness Fraction",
        "purpose": "Stiffness kept by an eroded element instead of full deletion.",
        "use": "0 removes failed elements completely; a small value such as 0.01 keeps a numerical remnant that stabilizes the solve.",
        "output": "Affects post-failure equilibrium and how abruptly load is shed from eroded regions.",
        "caution": "Large residual fractions understate damage; keep the value small.",
    },
    "fracture_max_deleted": {
        "title": "Max Deleted Fraction",
        "purpose": "Upper bound on the fraction of shell elements that may erode.",
        "use": "The solve stops eroding (and reports it) once this fraction is reached, preventing runaway element deletion.",
        "output": "Diagnostics state whether the limit was hit.",
        "caution": "If the limit is reached the remaining capacity is not a converged physical answer; inspect the state.",
    },
    "fracture_min_load_factor": {
        "title": "Min Load Factor Before Erosion",
        "purpose": "Load factor below which no element is allowed to erode.",
        "use": "Protects the early load steps from spurious erosion while contact and plasticity develop.",
        "output": "Erosion only starts above this load factor.",
        "caution": "Setting it too high can suppress genuine early failure.",
    },
    "show_plate": {
        "title": "Show Plate Surface",
        "purpose": "Toggles the plate/skin shell surfaces in the 3D result view.",
        "use": "Turn off to inspect stiffeners, girders and member webs hidden behind the plating.",
        "output": "Visualization only; results are unchanged.",
        "caution": "Hidden surfaces are still part of the solution and the reported statistics.",
    },
    "show_stiffeners": {
        "title": "Show Stiffeners",
        "purpose": "Toggles stiffener members in the 3D result view.",
        "use": "Turn off to declutter the view when only plate response matters.",
        "output": "Visualization only; results are unchanged.",
        "caution": "Hidden members are still part of the solution and the reported statistics.",
    },
    "show_girders": {
        "title": "Show Girders / Frames",
        "purpose": "Toggles girder and ring-frame members in the 3D result view.",
        "use": "Turn off to declutter the view when only plate or stiffener response matters.",
        "output": "Visualization only; results are unchanged.",
        "caution": "Hidden members are still part of the solution and the reported statistics.",
    },
    "show_mesh_lines": {
        "title": "Show Mesh Lines",
        "purpose": "Draws element edges on the shaded result surfaces.",
        "use": "Useful for judging mesh density and element quality directly in the result view.",
        "output": "Visualization only.",
        "caution": "On fine meshes the lines can dominate visually; turn them off for stress contour reading.",
    },
    "show_axis_ruler": {
        "title": "Show Axis Ruler",
        "purpose": "Displays the coordinate axes and dimension ruler in the 3D view.",
        "use": "Keep on to read off global directions (matches the fx/fy/fz load axes and BC DOF axes).",
        "output": "Visualization only.",
        "caution": "None.",
    },
    "plate_alpha": {
        "title": "Plate Alpha",
        "purpose": "Opacity of the plate/skin surfaces in the 3D view (0 transparent, 1 opaque).",
        "use": "Lower it to see members through the plating without hiding the plate entirely.",
        "output": "Visualization only.",
        "caution": "Very low values can make the stress colours hard to judge.",
    },
    "member_alpha": {
        "title": "Member Alpha",
        "purpose": "Opacity of stiffener/girder members in the 3D view (0 transparent, 1 opaque).",
        "use": "Lower it to emphasise the plate response, raise it to inspect member stresses.",
        "output": "Visualization only.",
        "caution": "Very low values can make the stress colours hard to judge.",
    },
    "colormap": {
        "title": "Colormap",
        "purpose": "Colour scale used for the stress/displacement contours.",
        "use": "Pick any matplotlib colormap name; viridis and turbo are good defaults for stress plots.",
        "output": "Visualization only; the underlying values and limits are unchanged.",
        "caution": "Diverging maps can suggest a false zero point for quantities that are strictly positive.",
    },
    "shading": {
        "title": "Lighting",
        "purpose": "Shades every surface with a directional light so curvature and member orientation read as 3D.",
        "use": "Keep on for geometry and mesh inspection. Turn off to read contour colours as literal values.",
        "output": "Visualization only.",
        "caution": (
            "Shading only darkens a surface - a face turned toward the light keeps its exact contour colour - "
            "but a shadowed face still reads darker than its legend entry."
        ),
    },
    "light_azimuth": {
        "title": "Light Azimuth",
        "purpose": "Compass direction the light comes from, in degrees about the global Z axis.",
        "use": "Rotate the light when a feature of interest falls in shadow. Press Enter to apply.",
        "output": "Visualization only.",
        "caution": "Lighting the model straight down the view direction flattens it; keep the light off to one side.",
    },
    "light_elevation": {
        "title": "Light Elevation",
        "purpose": "Height of the light above the horizon, in degrees.",
        "use": "High values light top surfaces, low values rake across the model and emphasise plate curvature.",
        "output": "Visualization only.",
        "caution": "Negative elevations light the model from below, which can read as inverted geometry.",
    },
    "light_ambient": {
        "title": "Ambient Light",
        "purpose": "Brightness of surfaces that face away from the light (0 black, 1 unshaded).",
        "use": "Raise it to keep shadowed members readable, lower it for more three-dimensional contrast.",
        "output": "Visualization only.",
        "caution": "Low ambient values make contour colours on shadowed faces hard to compare with the legend.",
    },
    "light_specular": {
        "title": "Highlight",
        "purpose": "Strength of the specular highlight, the bright glint where the surface mirrors the light.",
        "use": "A small amount helps read curvature on shells; set to 0 for flat, purely value-based colours.",
        "output": "Visualization only.",
        "caution": "Highlights brighten a surface past its base colour, so keep it low when reading contours.",
    },
    "light_follow_camera": {
        "title": "Light Follows Camera",
        "purpose": "Attaches the light to the viewpoint, like a head lamp, instead of fixing it in the model.",
        "use": "Useful while orbiting: whatever faces you never goes dark.",
        "output": "Visualization only.",
        "caution": "Shading then changes as you rotate, so it is a poorer cue for comparing two orientations.",
    },
    "show_axis_indicator": {
        "title": "Show Axis Indicator",
        "purpose": "Draws the small X/Y/Z orientation triad in the corner of the 3D view.",
        "use": "Keep on to confirm which way the global axes point (matches the fx/fy/fz load axes).",
        "output": "Visualization only.",
        "caution": "None.",
    },
    "occlude_lines": {
        "title": "Hide Lines Behind Geometry",
        "purpose": "Lets 3D lines - beam elements, member outlines, grids - be hidden by surfaces in front of them.",
        "use": (
            "Keep on for a solid, correctly ordered view. Turn off to keep beam elements and markers "
            "visible through the plating, as an X-ray view."
        ),
        "output": "Visualization only.",
        "caution": "Dimension annotations and labels stay on top either way.",
    },
    "interactive_detail": {
        "title": "Interactive Detail",
        "purpose": "Face budget used while orbiting, panning or zooming; full detail returns on mouse release.",
        "use": "Lower it if dragging a large model feels sluggish, raise it if interaction already feels smooth.",
        "output": "Visualization only; the released view is always drawn at full detail.",
        "caution": (
            "The budget self-tunes from measured frame times, so this is the starting point rather than a "
            "hard limit."
        ),
    },
    "animation_detail": {
        "title": "Animation Detail",
        "purpose": "Render quality used during animation playback.",
        "use": (
            "'auto' starts at full detail and drops to reduced detail as soon as a frame misses its slot; "
            "'full' keeps every face, stipple and outline; 'fast' always uses the reduced path."
        ),
        "output": "Visualization only; the frames themselves are unchanged and the view is redrawn in full on stop.",
        "caution": "Reduced detail drops transparency stippling and element outlines while playing.",
    },
})


class RuntimeFEMWindow:
    """Popup window for the experimental full-geometry FEM runtime solver."""

    def __init__(self, parent: Any, app: Any, use_parent_as_window: bool = False, imported_fem_model=None,
                 imported_path=None):
        self.app = app
        self.imported_fem_model = imported_fem_model
        if self.imported_fem_model is not None:
            self.snapshot = RuntimeFEMLineSnapshot(
                line_name=str(imported_path or "Imported FEM"),
                line_points=[],
                structure_bundle=[],
                pressure_pa=0.0,
                domain="FEM File",
                is_cylinder=False,
            )
        else:
            self.snapshot = active_line_snapshot(app)
        if use_parent_as_window:
            self.window = parent
            self.window.configure(background=getattr(app, "_general_color", "#f0f0f0"))
        else:
            self.window = tk.Toplevel(parent, background=getattr(app, "_general_color", "#f0f0f0"))
        self.window.title("Experimental FEM solver")
        self.window.geometry("1100x760")
        self.window.minsize(980, 640)
        self.window.resizable(True, True)
        if not use_parent_as_window:
            try:
                self.window.group(parent)
            except Exception:
                pass
        try:
            self.window.attributes("-toolwindow", False)
        except Exception:
            pass

        self.mesh_fidelity = tk.StringVar(value="coarse")
        self.mesh_size_m = tk.DoubleVar(value=0.0)
        self.load_scale = tk.DoubleVar(value=1.0)
        self.pressure_pa = tk.DoubleVar(value=self.snapshot.pressure_pa)
        snapshot_moment_nm = _safe_float(self.snapshot.top_bottom_moment_nm, 0.0)
        fallback_moment_nm = _safe_float(getattr(app, "_fem_default_top_bottom_moment_nm", 0.0))
        self.top_bottom_moment_nm = tk.DoubleVar(
            value=snapshot_moment_nm if abs(snapshot_moment_nm) > 0.0 else fallback_moment_nm
        )
        self.torsional_moment_nm = tk.DoubleVar(
            value=_safe_float(self.snapshot.torsional_moment_nm, 0.0)
        )
        self.shear_force_n = tk.DoubleVar(
            value=_safe_float(self.snapshot.shear_force_n, 0.0)
        )
        self.include_stiffeners = tk.BooleanVar(value=True)
        self.include_girders = tk.BooleanVar(value=True)
        self.ignore_girder_length = tk.BooleanVar(value=False)
        self.include_end_lids = tk.BooleanVar(value=bool(self.snapshot.is_cylinder))
        self.num_buckling_modes = tk.IntVar(value=5)
        self.boundary_condition = tk.StringVar(value="auto")
        # Per-DOF boundary model (redesigned BC tab): whole-boundary grid,
        # selected-edge staging grid, and the automatic-supports fallback.
        self._bc_dof_names = ("ux", "uy", "uz", "rx", "ry", "rz")
        self._bc_dof_labels = {
            "ux": "Ux [m]", "uy": "Uy [m]", "uz": "Uz [m]",
            "rx": "Rx [rad]", "ry": "Ry [rad]", "rz": "Rz [rad]",
        }
        self.boundary_auto_supports = tk.BooleanVar(value=True)
        # Whole-boundary grid is edited one named edge at a time; the staging
        # DOF vars reflect the currently selected edge and are persisted into
        # _boundary_edge_specs when the radio changes.
        self.boundary_dof_on = {dof: tk.BooleanVar(value=False) for dof in self._bc_dof_names}
        self.boundary_dof_value = {dof: tk.DoubleVar(value=0.0) for dof in self._bc_dof_names}
        self._boundary_edge_specs: dict[str, dict[str, dict]] = {}
        self.boundary_edge_choice = tk.StringVar(value="all")
        self._boundary_active_edge = "all"
        self.edge_dof_on = {dof: tk.BooleanVar(value=False) for dof in self._bc_dof_names}
        self.edge_dof_value = {dof: tk.DoubleVar(value=0.0) for dof in self._bc_dof_names}
        self.symmetry_mode = tk.StringVar(value="none")
        self.shell_element_order = tk.StringVar(value="S4")
        self.beam_element_order = tk.StringVar(value="B2")
        self.member_model = tk.StringVar(value="plates as shell, girders as beams")
        self.analysis_type = tk.StringVar(value="linear eigenvalue")
        self.buckling_analysis_type = tk.StringVar(value="linear eigenvalue")
        self.pressure_direction = tk.StringVar(value="front")
        self.follower_pressure = tk.BooleanVar(value=False)
        self.axial_force_n = tk.DoubleVar(value=_safe_float(self.snapshot.axial_force_n, 0.0))
        self.acceleration_x_m_s2 = tk.DoubleVar(value=0.0)
        self.acceleration_y_m_s2 = tk.DoubleVar(value=0.0)
        self.acceleration_z_m_s2 = tk.DoubleVar(value=0.0)
        self.added_mass_kg = tk.DoubleVar(value=0.0)
        self.added_mass_location = tk.StringVar(value="none")
        self.enforced_displacement_x_m = tk.DoubleVar(value=_safe_float(getattr(self.snapshot, 'enforced_displacement_x_m', 0.0), 0.0))
        self.enforced_displacement_y_m = tk.DoubleVar(value=_safe_float(getattr(self.snapshot, 'enforced_displacement_y_m', 0.0), 0.0))
        self.enforced_displacement_z_m = tk.DoubleVar(value=_safe_float(getattr(self.snapshot, 'enforced_displacement_z_m', 0.0), 0.0))
        self.stiffener_eccentricity_m = tk.DoubleVar(value=0.0)
        self.girder_eccentricity_m = tk.DoubleVar(value=0.0)
        self.member_orientation = tk.StringVar(value="auto")
        self.solver_type = tk.StringVar(value="direct")
        self.stress_percentile = tk.DoubleVar(value=95.0)
        self.material_library_names = ecosystem_gui.material_library_names()
        self.material_library_name = tk.StringVar(
            value=ecosystem_gui.default_material_name(self.material_library_names)
        )
        self._last_isotropic_material_name = self.material_library_name.get()
        self.elastic_modulus_gpa = tk.DoubleVar(value=210.0)
        self.poisson_ratio = tk.DoubleVar(value=0.3)
        self.yield_stress_mpa = tk.DoubleVar(value=355.0)
        self.material_model = tk.StringVar(value="linear elastic")
        self.steel_grade = tk.StringVar(value="S355")
        self.steel_thickness_class = tk.StringVar(value="auto")
        self.nonlinear_max_load_factor = tk.DoubleVar(value=3.0)
        self.nonlinear_steps = tk.IntVar(value=12)
        self.nonlinear_max_iterations = tk.IntVar(value=25)
        self.nonlinear_tolerance = tk.DoubleVar(value=1.0e-6)
        self.nonlinear_layers = tk.IntVar(value=5)
        self.nonlinear_solution_control = tk.StringVar(value="newton force control")
        self.post_buckling_enabled = tk.BooleanVar(value=False)
        self.post_buckling_stop_load_fraction = tk.DoubleVar(value=0.5)
        self.post_buckling_max_displacement_m = tk.DoubleVar(value=0.0)
        self.nonlinear_convergence_profile = tk.StringVar(value="auto")
        self.nonlinear_assembly_threads = tk.IntVar(value=0)
        self.nonlinear_static_kinematics = tk.StringVar(value="Von Karman")
        self.beam_consistent_mass_enabled = tk.BooleanVar(value=True)
        self.deformation_scale = tk.StringVar(value="0.0")
        self.custom_load_bc_enabled = tk.BooleanVar(value=False)
        self.custom_loads_add_to_imported = tk.BooleanVar(value=False)
        self.custom_use_nullspace_projection = tk.BooleanVar(value=True)
        self.custom_pressure_pa = tk.DoubleVar(value=0.0)
        # Small status text showing whether the last run used nullspace projection (updated after runs)
        self.last_run_nullspace_text = tk.StringVar(value="Last run nullspace: unknown")
        self.plate_edge_x0_support = tk.StringVar(value="free")
        self.plate_edge_x1_support = tk.StringVar(value="free")
        self.plate_edge_y0_support = tk.StringVar(value="free")
        self.plate_edge_y1_support = tk.StringVar(value="free")
        self.cylinder_lower_support = tk.StringVar(value="free")
        self.cylinder_upper_support = tk.StringVar(value="free")
        self.plate_edge_x0_load_n_per_m = tk.DoubleVar(value=0.0)
        self.plate_edge_x1_load_n_per_m = tk.DoubleVar(value=0.0)
        self.plate_edge_y0_load_n_per_m = tk.DoubleVar(value=0.0)
        self.plate_edge_y1_load_n_per_m = tk.DoubleVar(value=0.0)
        self.cylinder_lower_edge_load_n_per_m = tk.DoubleVar(value=0.0)
        self.cylinder_upper_edge_load_n_per_m = tk.DoubleVar(value=0.0)
        self.custom_time_domain_enabled = tk.BooleanVar(value=False)
        self.custom_time_domain_duration_s = tk.DoubleVar(value=0.01)
        self.custom_time_domain_total_time_s = tk.DoubleVar(value=0.05)
        self.custom_time_domain_dt_s = tk.DoubleVar(value=0.0005)
        self.custom_time_domain_result_interval_s = tk.DoubleVar(value=0.0)
        self.custom_loads_json = tk.StringVar(value="[]")
        self.custom_pressure_patches_json = tk.StringVar(value="[]")
        self.custom_edge_segments_json = tk.StringVar(value="[]")
        self.custom_selected_edge_load_n_per_m = tk.DoubleVar(value=0.0)
        # Component load grids (fx/fy/fz [N/m], mx/my/mz [Nm/m], global axes).
        # The whole-edge grid is edited one named edge at a time, mirroring the
        # per-edge boundary-condition grid: the staging vars show the edge
        # picked by the radio and are persisted into _edge_load_specs.
        self._load_dof_names = ("fx", "fy", "fz", "mx", "my", "mz")
        self._load_dof_labels = {
            "fx": "Fx [N/m]", "fy": "Fy [N/m]", "fz": "Fz [N/m]",
            "mx": "Mx [Nm/m]", "my": "My [Nm/m]", "mz": "Mz [Nm/m]",
        }
        self.selected_edge_load_components = {dof: tk.DoubleVar(value=0.0) for dof in self._load_dof_names}
        self.edge_load_components = {dof: tk.DoubleVar(value=0.0) for dof in self._load_dof_names}
        self._edge_load_specs: dict[str, dict[str, float]] = {}
        self.edge_load_edge_choice = tk.StringVar(value="all")
        self._edge_load_active_edge = "all"
        self.local_refinement_enabled = tk.BooleanVar(value=False)
        self.local_refinement_patches_json = tk.StringVar(value="[]")
        self.local_refinement_fine_factor = tk.DoubleVar(value=0.3)
        self.local_refinement_fine_size_m = tk.DoubleVar(value=0.0)
        self.local_refinement_extent_m = tk.DoubleVar(value=0.0)
        self.local_refinement_growth_factor = tk.DoubleVar(value=1.35)
        self.local_refinement_summary_var = tk.StringVar(value="Detail panels: 0")
        self.point_refinement_enabled = tk.BooleanVar(value=False)
        self.point_refinement_x_m = tk.DoubleVar(value=0.0)
        self.point_refinement_y_m = tk.DoubleVar(value=0.0)
        self.point_refinement_fine_factor = tk.DoubleVar(value=0.3)
        self.point_refinement_fine_size_m = tk.DoubleVar(value=0.0)
        self.point_refinement_extent_m = tk.DoubleVar(value=0.25)
        self.point_refinement_growth_factor = tk.DoubleVar(value=1.35)
        self.point_refinement_z_m = tk.DoubleVar(value=0.0)
        self._point_refinement_z_sync_active = False
        self._bind_point_refinement_z_sync()
        self._live_graph_figure = None
        self._live_graph_axis = None
        self._live_graph_axis2 = None
        self._live_graph_canvas = None
        self._live_graph_state: dict[str, Any] = {"kind": "idle", "series": {}, "last_draw": 0.0}
        self._custom_load_entries: list[dict[str, Any]] = []
        self._custom_selected_edge_keys: set[tuple[str, float, float, float]] = set()
        self._custom_load_tree: ttk.Treeview | None = None
        self._custom_load_tree_scrollbar: ttk.Scrollbar | None = None
        self._custom_load_trace_ids: list[tuple[tk.Variable, str]] = []
        self._custom_load_patches: list[dict] = []
        self._custom_load_manual_cuts: list[dict[str, Any]] = []
        self._custom_load_selected_index: int = -1
        self._custom_load_selection_active = False
        self._custom_load_click_origin: tuple[int, int] | None = None
        self._mesh_point_selection_active = False
        self._mesh_point_click_origin: tuple[int, int] | None = None
        self._mesh_point_selection_button = None
        self._probe_click_origin: tuple[int, int] | None = None
        self._selected_probe_node_id: int | None = None
        self._selected_probe_element_id: int | None = None
        self._last_mesh_result_case_label = "Static displacement/stress"
        self._custom_load_edge_click_origin: tuple[int, int] | None = None
        self._custom_load_selection_button = None
        self._generate_default_custom_load_patches()
        self.custom_time_domain_include_static_load = tk.BooleanVar(value=False)
        self.imperfection_enabled = tk.BooleanVar(value=False)
        self.imperfection_shape = tk.StringVar(value="standard plate/cylinder")
        self.imperfection_amplitude_m = tk.DoubleVar(value=0.0)
        self.imperfection_wave_a = tk.IntVar(value=1)
        self.imperfection_wave_b = tk.IntVar(value=1)
        self.imperfection_mode_shapes_json = tk.StringVar(value="[]")
        self.runtime_solver = tk.StringVar(value="stepwise")
        self.allow_unbalanced_free_free = tk.BooleanVar(value=False)
        self.buckling_shift_load_factor = tk.DoubleVar(value=0.0)
        self.buckling_min_load_factor = tk.DoubleVar(value=0.0)
        self.buckling_max_load_factor = tk.DoubleVar(value=0.0)
        self.buckling_repeated_tolerance = tk.DoubleVar(value=1.0e-3)
        self.buckling_allow_dense_fallback = tk.BooleanVar(value=False)
        self.recovery_history_mode = tk.StringVar(value="full")
        self.recovery_threads = tk.IntVar(value=0)
        self.memory_limit_mb = tk.DoubleVar(value=0.0)
        self.capacity_buckling_mode_number = tk.IntVar(value=1)
        self.capacity_mesh_min_elements_per_half_wave = tk.IntVar(value=4)
        self.fracture_enabled = tk.BooleanVar(value=False)
        self.fracture_strain_threshold = tk.DoubleVar(value=0.02)
        self.fracture_residual_stiffness_fraction = tk.DoubleVar(value=1.0e-6)
        self.fracture_max_deleted_fraction = tk.DoubleVar(value=0.25)
        self.fracture_min_load_factor = tk.DoubleVar(value=0.0)
        self.collision_enabled = tk.BooleanVar(value=False)
        self.collision_include_static_load = tk.BooleanVar(value=False)
        self.collision_damage_enabled = tk.BooleanVar(value=True)
        self.collision_material_nonlinear_enabled = tk.BooleanVar(value=False)
        self.collision_nonlinear_kinematics = tk.StringVar(value="Von Karman")
        self.collision_beam_contact_enabled = tk.BooleanVar(value=False)
        self.collision_adaptive_mesh_enabled = tk.BooleanVar(value=False)
        self.collision_adaptive_fine_factor = tk.DoubleVar(value=0.3)
        self.collision_adaptive_fine_size_m = tk.DoubleVar(value=0.0)
        self.collision_adaptive_extent_m = tk.DoubleVar(value=0.0)
        self.collision_adaptive_growth_factor = tk.DoubleVar(value=1.35)
        self.detail_transition_style = tk.StringVar(value="graded grid")
        self.custom_bc_segments_json = tk.StringVar(value="[]")
        self.custom_bc_support_choice = tk.StringVar(value="fixed")
        self._custom_bc_entries: list[dict[str, Any]] = []
        self.thickness_regions_json = tk.StringVar(value="[]")
        self.geometry_thickness_m = tk.DoubleVar(value=0.0)
        self.division_plane_axis = tk.StringVar(value="x")
        self.division_plane_coord_m = tk.DoubleVar(value=0.0)
        self._thickness_region_entries: list[dict[str, Any]] = []
        self.geometry_preview_canvas = None
        self.geometry_preview_parent = None
        self.collision_adaptive_zone_factor = tk.DoubleVar(value=2.5)
        self.collision_nonlinear_max_iterations = tk.IntVar(value=20)
        self.collision_nonlinear_tolerance = tk.DoubleVar(value=1.0e-6)
        self.collision_nonlinear_cutbacks = tk.IntVar(value=8)
        self.collision_plastic_damage_threshold = tk.DoubleVar(value=0.05)
        self.collision_damage_criterion = tk.StringVar(value="rtcl")
        self.collision_mass_kg = tk.DoubleVar(value=1000.0)
        self.collision_radius_m = tk.DoubleVar(value=0.25)
        self.collision_start_x_m = tk.DoubleVar(value=0.0)
        self.collision_start_y_m = tk.DoubleVar(value=0.0)
        self.collision_start_z_m = tk.DoubleVar(value=1.0)
        self.collision_vector_x = tk.DoubleVar(value=0.0)
        self.collision_vector_y = tk.DoubleVar(value=0.0)
        self.collision_vector_z = tk.DoubleVar(value=-1.0)
        self.collision_speed_mps = tk.DoubleVar(value=5.0)
        self.collision_time_mode = tk.StringVar(value="auto")
        self.collision_auto_steps_per_radius = tk.DoubleVar(value=20.0)
        self.collision_auto_post_contact_radii = tk.DoubleVar(value=6.0)
        self.collision_bounce_back_time_s = tk.DoubleVar(value=0.01)
        self.collision_total_time_s = tk.DoubleVar(value=0.05)
        self.collision_dt_s = tk.DoubleVar(value=0.0005)
        self.collision_result_interval_s = tk.DoubleVar(value=0.0)
        self.collision_penalty_stiffness_n_per_m = tk.DoubleVar(value=0.0)
        self.collision_penalty_scale = tk.DoubleVar(value=1.0)
        self.collision_auto_precondition = tk.BooleanVar(value=False)
        self.collision_contact_damping = tk.DoubleVar(value=0.0)
        self.collision_max_iterations = tk.IntVar(value=25)
        self.collision_penetration_tolerance_m = tk.DoubleVar(value=1.0e-8)
        self.collision_force_tolerance_n = tk.DoubleVar(value=1.0e-6)
        self.collision_target_penetration_fraction = tk.DoubleVar(value=0.01)
        self.collision_max_event_substeps = tk.IntVar(value=16)
        self.collision_contact_surface = tk.StringVar(value="midsurface")
        self.collision_damage_mode = tk.StringVar(value="accumulated_damage")
        self.collision_damage_capacity_basis = tk.StringVar(value="yield")
        self.collision_damage_user_capacity_mpa = tk.DoubleVar(value=0.0)
        self.collision_damage_softening_start = tk.DoubleVar(value=0.6)
        self.collision_damage_delete_at = tk.DoubleVar(value=1.0)
        self.collision_damage_min_contact_area_m2 = tk.DoubleVar(value=1.0e-6)
        self.collision_damage_max_deleted_fraction = tk.DoubleVar(value=0.25)
        self.collision_damage_neighbor_smoothing = tk.BooleanVar(value=False)
        self.result_case_choice = tk.StringVar(value="Static displacement/stress")
        self.result_case_labels: dict[str, str] = {"Static displacement/stress": "static"}
        self.component_choice = tk.StringVar(value="Stress von Mises")
        self.component_labels: dict[str, str] = {
            "Stress von Mises": "von_mises_pa",
            "Displacement Magnitude": "disp_mag",
            "Displacement X": "disp_x",
            "Displacement Y": "disp_y",
            "Displacement Z": "disp_z",
            "Stress X (membrane)": "stress_x_membrane_pa",
            "Stress Y (membrane)": "stress_y_membrane_pa",
            "Stress XY (membrane)": "stress_xy_membrane_pa",
            "Strain X (membrane)": "strain_x_membrane",
            "Strain Y (membrane)": "strain_y_membrane",
            "Strain XY (membrane)": "strain_xy_membrane",
            "Equivalent Plastic Strain": "plastic_strain",
            "Impact Damage": "impact_damage",
            "Impact Damage Utilization": "impact_damage_utilization",
        }
        self.current_result: RuntimeFEMRunResult | None = None
        self.result_text = None
        self.figure_canvas = None
        self.figure_toolbar = None
        self.figure_toolbar_frame = None
        self.preview_canvas = None
        self.figure_parent = None
        self.mesh_preview_canvas = None
        self.mesh_preview_parent = None
        self._last_run_result_status_text = ""
        self.result_case_selector = None
        self.component_selector = None
        self.probe_node_id = tk.StringVar(value="")
        self.probe_element_id = tk.StringVar(value="")
        self.color_min_vis = tk.StringVar(value="")
        self.color_max_vis = tk.StringVar(value="")
        self.color_min_slider = tk.DoubleVar(value=0.0)
        self.color_max_slider = tk.DoubleVar(value=1.0)
        self.color_min_scale = None
        self.color_max_scale = None
        self._color_limit_signature: tuple[str, str] | None = None
        self._color_limit_range: tuple[float, float] = (0.0, 1.0)
        self._color_limit_syncing = False
        self.run_button = None
        self.cancel_button = None
        self.use_for_buckling_button = None
        self._cancel_requested = False
        self.progress_bar = None
        self.result_canvas = None
        initial_renderer = normalize_backend(
            getattr(app, "_renderer_requested", "auto")
        )
        self.renderer_backend_choice = tk.StringVar(
            value=BACKEND_NAMES[initial_renderer]
        )
        self.renderer_backend_status = tk.StringVar(value="Renderer: starting")
        self._renderer_requested = initial_renderer
        self._renderer_switching = False
        self._live_collision_sphere_visualization: dict[str, Any] = {}
        # Kept for integrations that inspect the historical flag. Maintained
        # 3D results always use the shared viewer; only 2D histories use
        # Matplotlib in the desktop.
        self.use_interactive_3d = tk.BooleanVar(value=True)
        self.interactive_3d_checkbox = None
        self.show_plate_vis = tk.BooleanVar(value=True)
        self.show_stiffener_vis = tk.BooleanVar(value=True)
        self.show_girder_vis = tk.BooleanVar(value=True)
        self.show_collision_sphere_vis = tk.BooleanVar(value=True)
        self.show_mesh_lines_vis = tk.BooleanVar(value=True)
        self.show_axis_ruler_vis = tk.BooleanVar(value=False)
        self.show_imperfections_vis = tk.BooleanVar(value=False)
        self.imperfection_preview_scale = tk.DoubleVar(value=0.0)
        # 3D view options handled by the canvas itself rather than by the
        # geometry we hand it; all of them go through
        # _apply_canvas_view_options so every canvas stays consistent.
        self.show_axis_indicator_vis = tk.BooleanVar(value=True)
        self.shading_vis = tk.BooleanVar(value=True)
        self.light_azimuth_vis = tk.DoubleVar(value=300.0)
        self.light_elevation_vis = tk.DoubleVar(value=50.0)
        self.light_ambient_vis = tk.StringVar(value="0.45")
        self.light_specular_vis = tk.StringVar(value="0.12")
        self.light_follow_camera_vis = tk.BooleanVar(value=False)
        self.occlude_lines_vis = tk.BooleanVar(value=True)
        self.interactive_detail_vis = tk.IntVar(value=4000)
        self.animation_fast_mode = tk.BooleanVar(value=False)
        self.animation_detail_vis = tk.StringVar(value="auto")
        self.animation_interval_ms = tk.IntVar(value=80)
        self.animation_speed_multiplier = tk.DoubleVar(value=1.0)
        self.time_step_slider_value = tk.DoubleVar(value=0.0)
        self.time_step_slider = None
        self.time_step_label = None
        self._time_slider_syncing = False
        self.plate_alpha_vis = tk.StringVar(value="1.0")
        self.plate_front_color_vis = tk.StringVar(value="#d1d5db")
        self.plate_back_color_vis = tk.StringVar(value="#8b5e3c")
        self.member_alpha_vis = tk.StringVar(value="1.0")
        self.colormap_vis = tk.StringVar(value="jet")
        self.upper_result_frame = None
        self.upper_result_text = None
        self.solver_thread = None
        self.solver_queue = queue.Queue()
        self._active_run_options: RuntimeFEMOptions | None = None
        self._plot_refresh_after_id: str | None = None
        self._plot_trace_ids: list[tuple[tk.Variable, str]] = []
        self._force_fit_next_refresh = True
        self._display_base_geometry = True
        self._animation_after_id: str | None = None
        self._animation_running = False
        self._animation_index = 0
        self._animation_cache_origin = 0
        self._nonlinear_static_kinematics_control = None
        self._follower_pressure_control = None
        self._collision_nonlinear_kinematics_control = None
        self._collision_damage_beam_hint = None
        self._option_state_trace_ids: list[tuple[tk.Variable, str]] = []
        self.body_panes = None
        self.result_panes = None

        self._build()
        self._bind_option_state_traces()
        self._bind_plot_configuration_traces()
        self._show_as_normal_maximizable_window()
        self._start_kernel_warmup()
        register = getattr(app, "_register_runtime_fem_window", None)
        if callable(register):
            register(self)

    def _bind_plot_configuration_traces(self) -> None:
        """Redraw both the base model and solved result when plot options change."""

        variables = (
            self.deformation_scale,
            self.show_plate_vis,
            self.show_stiffener_vis,
            self.show_girder_vis,
            self.show_collision_sphere_vis,
            self.plate_alpha_vis,
            self.plate_front_color_vis,
            self.plate_back_color_vis,
            self.member_alpha_vis,
            self.colormap_vis,
            self.collision_enabled,
            self.collision_radius_m,
            self.collision_start_x_m,
            self.collision_start_y_m,
            self.collision_start_z_m,
            self.collision_vector_x,
            self.collision_vector_y,
            self.collision_vector_z,
            self.collision_speed_mps,
        )
        for variable in variables:
            try:
                trace_id = variable.trace_add("write", self._schedule_plot_refresh)
                self._plot_trace_ids.append((variable, trace_id))
            except Exception:
                pass

    @staticmethod
    def _choice_key(value: Any) -> str:
        text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
        return " ".join(text.split())

    @staticmethod
    def _set_control_state(control: Any, enabled: bool) -> None:
        if control is None:
            return
        try:
            control.configure(state=(tk.NORMAL if enabled else tk.DISABLED))
        except Exception:
            pass

    def _static_kinematics_selector_enabled(self) -> bool:
        if bool(self.collision_enabled.get()):
            return False
        if self._choice_key(self.runtime_solver.get()) in {
            "anysolver capacity workflow",
            "capacity workflow",
            "nonlinear capacity workflow",
        }:
            return False
        analysis = self._choice_key(self.analysis_type.get())
        runtime = self._choice_key(self.runtime_solver.get())
        return runtime == "nonlinear static" or analysis in {
            "geometric nonlinear static",
            "material nonlinear static",
            "geom. + material nonlinear static",
            "geom + material nonlinear static",
            "geometric and material nonlinear static",
        }

    def _follower_pressure_selector_enabled(self) -> bool:
        """Follower pressure is meaningful only on supported nonlinear paths."""

        runtime = self._choice_key(self.runtime_solver.get())
        return (
            self._static_kinematics_selector_enabled()
            and runtime in {"static only", "nonlinear static"}
            and not bool(self.custom_time_domain_enabled.get())
            and not bool(self.collision_enabled.get())
        )

    def _collision_kinematics_selector_enabled(self) -> bool:
        return bool(self.collision_enabled.get()) and bool(self.collision_material_nonlinear_enabled.get())

    def _apply_post_buckling_field_sync(self) -> None:
        """Mirror the post-buckling solve mode in the dependent input fields.

        Post-buckling always runs a geometric + material nonlinear arc-length
        solve (the solver enforces this), so the Analysis, Material and NL
        control fields are set to match what actually executes.  Values are
        only written when different, which also terminates the trace
        recursion from the option-state bindings.
        """
        try:
            if not bool(self.post_buckling_enabled.get()):
                return
            if str(self.analysis_type.get()) != "geom. + material nonlinear static":
                self.analysis_type.set("geom. + material nonlinear static")
            if str(self.material_model.get()) != "DNV-RP-C208 steel":
                self.material_model.set("DNV-RP-C208 steel")
            if self._choice_key(self.nonlinear_solution_control.get()) != "arc length":
                self.nonlinear_solution_control.set("arc length")
        except Exception:
            pass

    def _refresh_option_states(self, *_args: Any) -> None:
        self._apply_post_buckling_field_sync()
        static_enabled = self._static_kinematics_selector_enabled()
        if not static_enabled and _normalise_kinematics(self.nonlinear_static_kinematics.get()) != "von_karman":
            self.nonlinear_static_kinematics.set("Von Karman")
        elif static_enabled:
            self.nonlinear_static_kinematics.set(_kinematics_label(self.nonlinear_static_kinematics.get()))
        self._set_control_state(self._nonlinear_static_kinematics_control, static_enabled)

        follower_enabled = self._follower_pressure_selector_enabled()
        if not follower_enabled and bool(self.follower_pressure.get()):
            self.follower_pressure.set(False)
        self._set_control_state(self._follower_pressure_control, follower_enabled)

        collision_enabled = self._collision_kinematics_selector_enabled()
        if not collision_enabled and _normalise_kinematics(self.collision_nonlinear_kinematics.get()) != "von_karman":
            self.collision_nonlinear_kinematics.set("Von Karman")
        elif collision_enabled:
            self.collision_nonlinear_kinematics.set(_kinematics_label(self.collision_nonlinear_kinematics.get()))
        self._set_control_state(self._collision_nonlinear_kinematics_control, collision_enabled)

        if self._collision_damage_beam_hint is not None:
            hint = ""
            if (
                    bool(self.collision_enabled.get())
                    and bool(self.collision_beam_contact_enabled.get())
                    and bool(self.collision_damage_enabled.get())
                    and not bool(self.collision_material_nonlinear_enabled.get())
            ):
                hint = "Capacity damage is shell-contact based; use material nonlinear plastic damage for beam erosion."
            try:
                self._collision_damage_beam_hint.configure(text=hint)
            except Exception:
                pass

        try:
            # We had forced beam contact here, but the user explicitly wants manual control over beam contact.
            pass
        except Exception:
            pass

        criterion_fixed = (self.collision_damage_criterion.get() not in ("mesh_scaled_gl", "rtcl", "rtcl_modified"))
        if hasattr(self, "_collision_plastic_damage_threshold_control"):
            is_active = criterion_fixed and bool(self.collision_damage_enabled.get())
            self._set_control_state(self._collision_plastic_damage_threshold_control, is_active)

    def _bind_option_state_traces(self) -> None:
        variables: tuple[tk.Variable, ...] = (
            self.analysis_type,
            self.runtime_solver,
            self.nonlinear_solution_control,
            self.material_model,
            self.post_buckling_enabled,
            self.collision_enabled,
            self.custom_time_domain_enabled,
            self.collision_material_nonlinear_enabled,
            self.collision_beam_contact_enabled,
            self.collision_damage_enabled,
            self.collision_damage_criterion,
        )
        for variable in variables:
            try:
                trace_id = variable.trace_add("write", self._refresh_option_states)
                self._option_state_trace_ids.append((variable, trace_id))
            except Exception:
                pass
        self._refresh_option_states()

    def _start_kernel_warmup(self) -> None:
        state = start_fe_solver_kernel_warmup(background=True)
        status = str(state.get("status", "not_started"))
        if status in {"running", "completed", "disabled", "backend_unavailable", "failed"}:
            self._write_status(_warmup_diagnostics()[0], keep_run_results=True)
        if status == "running":
            try:
                self.window.after(600, self._poll_kernel_warmup)
            except Exception:
                pass

    def _poll_kernel_warmup(self) -> None:
        state = fe_solver_kernel_warmup_status()
        if str(state.get("status", "")) == "running":
            try:
                self.window.after(600, self._poll_kernel_warmup)
            except Exception:
                pass
            return
        self._write_status(_warmup_diagnostics()[0], keep_run_results=True)

    def _schedule_plot_refresh(self, *_args: Any) -> None:
        """Debounce entry edits so typing does not rebuild the 3D scene per key."""

        if self.figure_parent is None:
            return
        if self._plot_refresh_after_id is not None:
            try:
                self.window.after_cancel(self._plot_refresh_after_id)
            except Exception:
                pass
            self._plot_refresh_after_id = None
        try:
            self._plot_refresh_after_id = self.window.after(90, self._run_scheduled_plot_refresh)
        except Exception:
            self._plot_refresh_after_id = None

    def _run_scheduled_plot_refresh(self) -> None:
        self._plot_refresh_after_id = None
        try:
            self._refresh_figure(preserve_view=True)
        except tk.TclError:
            pass

    def _show_as_normal_maximizable_window(self) -> None:
        """Keep the solver as a normal window with maximize controls available."""

        try:
            self.window.update_idletasks()
        except Exception:
            pass
        try:
            self.window.state("zoomed")
            return
        except Exception:
            pass
        try:
            self.window.attributes("-zoomed", True)
            return
        except Exception:
            pass
        try:
            screen_width = max(int(self.window.winfo_screenwidth()), 1100)
            screen_height = max(int(self.window.winfo_screenheight()), 760)
            self.window.geometry(str(screen_width - 80) + "x" + str(screen_height - 100) + "+20+20")
        except Exception:
            pass

    def _requested_renderer_backend(self) -> str:
        return normalize_backend(getattr(self, "_renderer_requested", "auto"))

    def _create_3d_canvas(self, parent: Any, **options: Any) -> Any:
        """Create one viewer using the application-wide renderer policy."""

        viewer = create_3d_viewer(
            parent,
            backend=self._requested_renderer_backend(),
            **options,
        )
        self.renderer_backend_status.set("Renderer: " + backend_diagnostic(viewer))
        return viewer

    @staticmethod
    def _viewer_dimensions(viewer: Any) -> tuple[int, int]:
        return viewport_size(viewer)

    def _populate_result_switch_candidate(self, canvas: Any) -> None:
        self._apply_canvas_view_options(canvas)
        canvas.clear(keep_canvas=False)
        canvas.clear_thickness_legend()
        show_base = self.current_result is None or self._display_base_geometry
        if show_base:
            self._populate_canvas_with_geometry(canvas, fit_view=False)
        else:
            self._populate_canvas_with_results(canvas, fit_view=False)

    def _renderer_switch_specs(self) -> list[tuple[str, Any, Any, bool]]:
        specs: list[tuple[str, Any, Any, bool]] = []
        if self.result_canvas is not None and self.figure_parent is not None:
            specs.append(
                (
                    "result_canvas",
                    self.figure_parent,
                    self._populate_result_switch_candidate,
                    True,
                )
            )
        generated = getattr(self, "_last_preview_mesh", None)
        if self.mesh_preview_canvas is not None and self.mesh_preview_parent is not None:
            specs.append(
                (
                    "mesh_preview_canvas",
                    self.mesh_preview_parent,
                    lambda canvas, value=generated: (
                        self._apply_canvas_view_options(canvas),
                        canvas.clear(keep_canvas=False),
                        self._populate_canvas_with_mesh(canvas, value)
                        if value is not None
                        else None,
                    ),
                    False,
                )
            )
        geometry = getattr(self, "_last_geometry_preview", None)
        if (
            self.geometry_preview_canvas is not None
            and self.geometry_preview_parent is not None
        ):
            specs.append(
                (
                    "geometry_preview_canvas",
                    self.geometry_preview_parent,
                    lambda canvas, value=geometry: (
                        self._apply_canvas_view_options(canvas),
                        canvas.clear(keep_canvas=False),
                        self._populate_canvas_with_thickness(canvas, value)
                        if value is not None
                        else None,
                    ),
                    False,
                )
            )
        return specs

    def _animation_state_for_renderer_switch(self) -> dict[str, Any]:
        """Snapshot the logical animation frame before replacing a viewer."""

        labels = self._time_result_labels()
        current_label = str(self.result_case_choice.get())
        current_index = labels.index(current_label) if current_label in labels else 0
        next_index = int(getattr(self, "_animation_index", current_index))
        canvas = getattr(self, "result_canvas", None)
        viewer_playing = getattr(canvas, "is_playing_animation", False)
        if callable(viewer_playing):
            viewer_playing = viewer_playing()
        running = bool(getattr(self, "_animation_running", False) or viewer_playing)
        fast = bool(self.animation_fast_mode.get()) and canvas is not None

        if labels:
            current_index %= len(labels)
            next_index %= len(labels)
            if running and canvas is not None:
                frame_count = getattr(canvas, "animation_frames", 0)
                if callable(frame_count):
                    frame_count = frame_count()
                if bool(viewer_playing) and int(frame_count or 0) > 0:
                    cache_index = getattr(canvas, "animation_frame_index", 0)
                    if callable(cache_index):
                        cache_index = cache_index()
                    origin = int(getattr(self, "_animation_cache_origin", 0))
                    current_index = (origin + int(cache_index) - 1) % len(labels)
                    next_index = (current_index + 1) % len(labels)
            current_label = labels[current_index]

        return {
            "running": running,
            "fast": fast,
            "current_index": current_index,
            "next_index": next_index,
            "current_label": current_label,
        }

    def _pause_animation_for_renderer_switch(self) -> dict[str, Any]:
        """Pause playback without losing the displayed or next frame."""

        state = self._animation_state_for_renderer_switch()
        if state["running"]:
            self._stop_animation()
        self._animation_index = int(state["next_index"])
        if state["current_label"]:
            self.result_case_choice.set(str(state["current_label"]))
            self._sync_time_slider(index=int(state["current_index"]))
        return state

    def _resume_animation_after_renderer_switch(
        self,
        state: dict[str, Any],
    ) -> None:
        """Restore playback on either the candidate or the retained old viewer."""

        labels = self._time_result_labels()
        if not labels:
            return
        current_index = int(state.get("current_index", 0)) % len(labels)
        next_index = int(state.get("next_index", current_index)) % len(labels)
        self._animation_index = next_index
        self.result_case_choice.set(labels[current_index])
        self._sync_time_slider(index=current_index)
        if not bool(state.get("running", False)):
            return

        try:
            if bool(state.get("fast", False)) and self.result_canvas is not None:
                self._play_animation(start_index=current_index)
                return

            self._animation_running = True
            speed = max(_tk_var_float(self.animation_speed_multiplier, 1.0), 0.05)
            interval = max(
                int(
                    round(
                        max(_tk_var_int(self.animation_interval_ms, 80), 20)
                        / speed
                    )
                ),
                5,
            )
            self._animation_after_id = self.window.after(
                interval, self._advance_animation_frame
            )
        except Exception as error:
            self._animation_running = False
            self._animation_after_id = None
            try:
                self._write_status(
                    "3D renderer switched, but animation playback could not be "
                    + "resumed: "
                    + str(error),
                    keep_run_results=True,
                )
            except Exception:
                pass

    def _switch_renderer_backend(
        self,
        _event: Any = None,
        *,
        _application_coordinated: bool = False,
    ) -> bool:
        """Transactionally replace all live 3D canvases."""

        if self._renderer_switching:
            return False
        previous = self._requested_renderer_backend()
        requested = normalize_backend(self.renderer_backend_choice.get())
        if requested == previous:
            return True
        if not _application_coordinated:
            coordinate = getattr(
                self.app, "_switch_renderer_backend_from_runtime", None
            )
            if callable(coordinate):
                return bool(coordinate(self, requested))

        specs = self._renderer_switch_specs()
        if not specs:
            self._renderer_requested = requested
            try:
                self.app._renderer_requested = requested
                self.app._renderer_backend_choice.set(BACKEND_NAMES[requested])
            except Exception:
                pass
            self.renderer_backend_status.set(
                "Renderer: " + BACKEND_NAMES[requested] + " (used by the next 3D view)"
            )
            return True

        self._renderer_switching = True
        candidates: list[tuple[str, Any, Any, bool]] = []
        animation_state: dict[str, Any] = {}
        try:
            animation_state = self._pause_animation_for_renderer_switch()
            for attribute, parent, populate, needs_selection in specs:
                old = getattr(self, attribute)
                width, height = self._viewer_dimensions(old)
                candidate = create_3d_viewer(
                    parent,
                    backend=requested,
                    width=width,
                    height=height,
                    bg=str(getattr(old, "bg", "white")),
                )
                try:
                    state = export_view_state(old)
                    populate(candidate)
                    apply_view_state(candidate, state, redraw=False)
                    candidate.redraw()
                except Exception:
                    candidate.destroy()
                    raise
                candidates.append((attribute, old, candidate, needs_selection))

            # Commit only after every candidate has accepted its scene/state.
            for attribute, old, candidate, needs_selection in candidates:
                old.pack_forget()
                candidate.pack(fill=tk.BOTH, expand=True)
                setattr(self, attribute, candidate)
                if needs_selection:
                    self._bind_custom_load_canvas_selection(candidate)
                old.destroy()

            self._renderer_requested = requested
            actual = ", ".join(
                sorted({backend_diagnostic(candidate) for _, _, candidate, _ in candidates})
            )
            if self.app is not None:
                try:
                    self.app._renderer_requested = requested
                    self.app._renderer_backend_choice.set(BACKEND_NAMES[requested])
                    self.app._renderer_backend_status.set("Renderer: " + actual)
                except Exception:
                    pass
            self.renderer_backend_status.set("Renderer: " + actual)
            self._write_status("3D renderer switched to " + actual + ".", keep_run_results=True)
            if animation_state:
                self._resume_animation_after_renderer_switch(animation_state)
            return True
        except Exception as error:
            for _attribute, _old, candidate, _needs_selection in candidates:
                try:
                    candidate.destroy()
                except Exception:
                    pass
            if animation_state:
                self._resume_animation_after_renderer_switch(animation_state)
            self.renderer_backend_choice.set(BACKEND_NAMES[previous])
            self.renderer_backend_status.set("Renderer switch failed: " + str(error))
            messagebox.showerror(
                "Renderer unavailable",
                "The working 3D view was kept unchanged.\n\n" + str(error),
                parent=self.window,
            )
            return False
        finally:
            self._renderer_switching = False

    def _canvas_view_targets(self) -> tuple:
        """Every Tkinter3DCanvas the visualization options apply to."""
        return tuple(
            canvas
            for canvas in (
                getattr(self, "result_canvas", None),
                getattr(self, "geometry_preview_canvas", None),
                getattr(self, "mesh_preview_canvas", None),
            )
            if canvas is not None
        )

    def _apply_canvas_view_options(self, canvas: Any) -> None:
        """
        Push the Visualization-tab display settings onto one 3D canvas.

        These are the options the canvas applies itself - mesh lines, rulers,
        lighting, line occlusion, interactive detail - as opposed to the ones
        that change the geometry we build (alpha, colours, deformation
        scale), which are read while populating the scene.  Routing them all
        through here keeps the result view, the geometry preview and the mesh
        preview in step, and keeps working against an ANYtk3D build that
        predates any individual setting.
        """
        if canvas is None:
            return

        def call(name: str, *args: Any, **kwargs: Any) -> None:
            method = getattr(canvas, name, None)
            if callable(method):
                try:
                    method(*args, **kwargs)
                except Exception:
                    pass

        call("set_mesh_lines", bool(self.show_mesh_lines_vis.get()))
        call("set_axis_ruler", bool(self.show_axis_ruler_vis.get()))
        call("set_axis_indicator", bool(self.show_axis_indicator_vis.get()))
        call("set_occlude_lines", bool(self.occlude_lines_vis.get()))
        call("set_interactive_detail", max(200, _tk_var_int(self.interactive_detail_vis, 4000)))
        call("set_shading", bool(self.shading_vis.get()))

        direction = None
        sun = getattr(_tk3d_canvas_module, "sun_direction", None)
        if callable(sun):
            try:
                direction = sun(
                    _tk_var_float(self.light_azimuth_vis, 300.0),
                    _tk_var_float(self.light_elevation_vis, 50.0),
                )
            except Exception:
                direction = None
        call(
            "set_light",
            direction=direction,
            ambient=_clamped_alpha(self.light_ambient_vis.get(), 0.45),
            specular=max(0.0, min(1.0, _safe_float(self.light_specular_vis.get(), 0.12))),
            follow_camera=bool(self.light_follow_camera_vis.get()),
        )

    def _refresh_canvas_view_options(self) -> None:
        """Re-apply the display options to every live canvas and redraw."""
        for canvas in self._canvas_view_targets():
            self._apply_canvas_view_options(canvas)
            redraw = getattr(canvas, "redraw", None)
            if callable(redraw):
                try:
                    redraw()
                except Exception:
                    pass

    def _reset_lighting_defaults(self) -> None:
        """Restore the shipped lighting setup."""
        self.shading_vis.set(True)
        self.light_azimuth_vis.set(300.0)
        self.light_elevation_vis.set(50.0)
        self.light_ambient_vis.set("0.45")
        self.light_specular_vis.set("0.12")
        self.light_follow_camera_vis.set(False)
        self.show_axis_indicator_vis.set(True)
        self.occlude_lines_vis.set(True)
        self.interactive_detail_vis.set(4000)
        self._refresh_canvas_view_options()

    def _animation_playback_detail(self) -> bool | None:
        """Map the detail choice onto ANYtk3D's play_animation(fast=...)."""
        return {"auto": None, "full": False, "fast": True}.get(
            str(self.animation_detail_vis.get()).strip().lower(), None
        )

    def _info_button(self, parent: Any, key: str) -> ttk.Button:
        return ttk.Button(parent, text="i", width=2, command=lambda info_key=key: self._show_solver_info(info_key))

    def _add_control_row(
            self,
            parent: Any,
            row: int,
            key: str,
            label: str,
            control: Any,
            sticky: str = tk.EW,
    ) -> Any:
        self._info_button(parent, key).grid(row=row, column=0, sticky=tk.W, padx=(8, 4), pady=4)
        ttk.Label(parent, text=label).grid(row=row, column=1, sticky=tk.W, padx=(0, 8), pady=4)
        control.grid(row=row, column=2, sticky=sticky, padx=(0, 8), pady=4)
        return control

    def _add_option_row(
            self,
            parent: Any,
            row: int,
            key: str,
            label: str,
            variable: tk.Variable,
            values: tuple[str, ...],
            width: int | None = None,
            command: Any = None,
    ) -> ttk.OptionMenu:
        control = ttk.OptionMenu(
            parent,
            variable,
            variable.get(),
            *values,
            command=command,
        )
        if width is not None:
            try:
                control.configure(width=width)
            except Exception:
                pass
        return self._add_control_row(parent, row, key, label, control)

    def _add_entry_row(
            self,
            parent: Any,
            row: int,
            key: str,
            label: str,
            variable: tk.Variable,
            width: int = 12,
    ) -> ttk.Entry:
        control = ttk.Entry(parent, textvariable=variable, width=width)
        return self._add_control_row(parent, row, key, label, control)

    def _add_check_row(self, parent: Any, row: int, key: str, text: str, variable: tk.BooleanVar) -> ttk.Checkbutton:
        self._info_button(parent, key).grid(row=row, column=0, sticky=tk.W, padx=(8, 4), pady=4)
        control = ttk.Checkbutton(parent, text=text, variable=variable)
        control.grid(row=row, column=1, columnspan=2, sticky=tk.W, padx=(0, 8), pady=4)
        return control

    def _build_dof_constraint_grid(self, parent: Any, start_row: int, prefix: str,
                                   on_vars: dict, value_vars: dict) -> None:
        """Six DOF rows: [constrain checkbox] <dof label> [enforced value].

        A ticked DOF is held at the enforced value (0 = fixed); the value box
        accepts translations (m) and rotations (rad).  Same layout for the
        whole-boundary and selected-edge sections.
        """
        info_key = "boundary_dof_grid" if prefix == "boundary" else "edge_dof_grid"
        self._info_button(parent, info_key).grid(row=start_row, column=0, sticky=tk.W, padx=(8, 4), pady=(2, 0))
        ttk.Label(parent, text="Constrain DOF (tick) and enforced value:").grid(
            row=start_row, column=1, columnspan=3, sticky=tk.W, padx=(0, 8), pady=(2, 0))
        for offset, dof in enumerate(self._bc_dof_names):
            row = start_row + 1 + offset
            ttk.Checkbutton(parent, text=self._bc_dof_labels[dof], variable=on_vars[dof]).grid(
                row=row, column=1, sticky=tk.W, padx=(0, 6), pady=1)
            ttk.Entry(parent, textvariable=value_vars[dof], width=12).grid(
                row=row, column=2, sticky=tk.W, padx=(0, 8), pady=1)

    def _dof_grid_constraints(self, on_vars: dict, value_vars: dict) -> dict:
        """Collect {dof: enforced_value} for the ticked DOFs of a grid."""
        constraints: dict = {}
        for dof in self._bc_dof_names:
            try:
                if bool(on_vars[dof].get()):
                    constraints[dof] = _safe_float(value_vars[dof].get(), 0.0)
            except Exception:
                continue
        return constraints

    def _boundary_edge_options(self) -> list:
        """(key, label) edge choices for the whole-boundary radio, per geometry."""
        if getattr(self.snapshot, "is_cylinder", False):
            return [("all", "Both ends"), ("lower", "Bottom"), ("upper", "Top")]
        return [("all", "All edges"), ("x0", "Edge x0"), ("x1", "Edge x1"),
                ("y0", "Edge y0"), ("y1", "Edge y1")]

    def _persist_boundary_edge(self, edge_key: str) -> None:
        """Store the current DOF grid into the per-edge spec for edge_key."""
        spec = {}
        for dof in self._bc_dof_names:
            try:
                if bool(self.boundary_dof_on[dof].get()):
                    spec[dof] = {"on": True, "value": _safe_float(self.boundary_dof_value[dof].get(), 0.0)}
            except Exception:
                continue
        if spec:
            self._boundary_edge_specs[edge_key] = spec
        else:
            self._boundary_edge_specs.pop(edge_key, None)

    def _load_boundary_edge(self, edge_key: str) -> None:
        """Load the stored spec for edge_key into the DOF grid (blank if none)."""
        spec = self._boundary_edge_specs.get(edge_key, {})
        for dof in self._bc_dof_names:
            entry = spec.get(dof)
            self.boundary_dof_on[dof].set(bool(entry))
            self.boundary_dof_value[dof].set(float(entry.get("value", 0.0)) if entry else 0.0)

    def _on_boundary_edge_change(self) -> None:
        """Radio callback: persist the edge just left, load the newly picked one."""
        previous = getattr(self, "_boundary_active_edge", "all")
        current = str(self.boundary_edge_choice.get())
        if previous != current:
            self._persist_boundary_edge(previous)
            self._load_boundary_edge(current)
            self._boundary_active_edge = current

    def _collect_boundary_constraint_json(self) -> str:
        """JSON of the per-edge whole-boundary constraints for the solver.

        {edge: {dof: value}} for edges with any constrained DOF; the "all"
        edge means every boundary edge.
        """
        self._persist_boundary_edge(str(self.boundary_edge_choice.get()))
        payload = {}
        for edge_key, spec in self._boundary_edge_specs.items():
            dofs = {dof: float(entry.get("value", 0.0))
                    for dof, entry in spec.items() if entry.get("on", True)}
            if dofs:
                payload[edge_key] = dofs
        return json.dumps(payload)

    def _build_load_component_grid(self, parent: Any, start_row: int, info_key: str, label: str,
                                   component_vars: dict) -> None:
        """Fx/Fy/Fz [N/m] and Mx/My/Mz [Nm/m] entries on global axes.

        Compact two-row layout (forces above moments) so the loads-to-run list
        below keeps its space; a component left at 0 applies no load.
        """
        header = ttk.Frame(parent)
        header.grid(row=start_row, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(2, 0))
        self._info_button(header, info_key).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(header, text=label).pack(side=tk.LEFT)
        grid = ttk.Frame(parent)
        grid.grid(row=start_row + 1, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(0, 2))
        for row_offset, dofs in enumerate((("fx", "fy", "fz"), ("mx", "my", "mz"))):
            for col_offset, dof in enumerate(dofs):
                ttk.Label(grid, text=self._load_dof_labels[dof]).grid(
                    row=row_offset, column=2 * col_offset, sticky=tk.W,
                    padx=(0 if col_offset == 0 else 10, 4), pady=1)
                ttk.Entry(grid, textvariable=component_vars[dof], width=10).grid(
                    row=row_offset, column=2 * col_offset + 1, sticky=tk.W, pady=1)

    def _load_component_values(self, component_vars: dict) -> dict[str, float]:
        """Collect the non-zero fx..mz values of a component grid."""
        values: dict[str, float] = {}
        for dof in self._load_dof_names:
            value = _tk_var_float(component_vars[dof], 0.0)
            if abs(value) > 0.0:
                values[dof] = float(value)
        return values

    def _selected_edge_load_components_json(self) -> str:
        values = self._load_component_values(self.selected_edge_load_components)
        return json.dumps(values) if values else ""

    def _persist_edge_load_edge(self, edge_key: str) -> None:
        """Store the current component grid into the per-edge spec for edge_key."""
        values = self._load_component_values(self.edge_load_components)
        if values:
            self._edge_load_specs[edge_key] = values
        else:
            self._edge_load_specs.pop(edge_key, None)

    def _load_edge_load_edge(self, edge_key: str) -> None:
        """Load the stored component spec for edge_key into the grid (0 if none)."""
        spec = self._edge_load_specs.get(edge_key, {})
        for dof in self._load_dof_names:
            self.edge_load_components[dof].set(float(spec.get(dof, 0.0)))

    def _on_edge_load_edge_change(self) -> None:
        """Radio callback: persist the edge just left, load the newly picked one."""
        previous = getattr(self, "_edge_load_active_edge", "all")
        current = str(self.edge_load_edge_choice.get())
        if previous != current:
            self._persist_edge_load_edge(previous)
            self._load_edge_load_edge(current)
            self._edge_load_active_edge = current

    def _collect_edge_load_components_json(self) -> str:
        """JSON of the per-edge component loads: {edge: {fx..mz}} for loaded edges."""
        self._persist_edge_load_edge(str(self.edge_load_edge_choice.get()))
        payload = {edge_key: dict(spec) for edge_key, spec in self._edge_load_specs.items() if spec}
        return json.dumps(payload) if payload else ""

    @staticmethod
    def _configure_option_grid(parent: Any) -> None:
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=0)
        parent.columnconfigure(2, weight=1)

    @staticmethod
    def _configure_compact_option_grid(parent: Any) -> None:
        for column in (0, 3):
            parent.columnconfigure(column, weight=0)
        for column in (1, 4):
            parent.columnconfigure(column, weight=0)
        for column in (2, 5):
            parent.columnconfigure(column, weight=1)

    def _add_compact_entry(
            self,
            parent: Any,
            row: int,
            side: int,
            key: str,
            label: str,
            variable: tk.Variable,
            width: int = 10,
    ) -> ttk.Entry:
        offset = 0 if side == 0 else 3
        self._info_button(parent, key).grid(row=row, column=offset, sticky=tk.W, padx=(6, 3), pady=2)
        ttk.Label(parent, text=label).grid(row=row, column=offset + 1, sticky=tk.W, padx=(0, 6), pady=2)
        control = ttk.Entry(parent, textvariable=variable, width=width)
        control.grid(row=row, column=offset + 2, sticky=tk.EW, padx=(0, 8), pady=2)
        return control

    def _add_compact_option(
            self,
            parent: Any,
            row: int,
            side: int,
            key: str,
            label: str,
            variable: tk.Variable,
            values: tuple[str, ...],
            width: int | None = None,
    ) -> ttk.OptionMenu:
        offset = 0 if side == 0 else 3
        self._info_button(parent, key).grid(row=row, column=offset, sticky=tk.W, padx=(6, 3), pady=2)
        ttk.Label(parent, text=label).grid(row=row, column=offset + 1, sticky=tk.W, padx=(0, 6), pady=2)
        control = ttk.OptionMenu(parent, variable, variable.get(), *values)
        if width is not None:
            try:
                control.configure(width=width)
            except Exception:
                pass
        control.grid(row=row, column=offset + 2, sticky=tk.EW, padx=(0, 8), pady=2)
        return control

    def _add_compact_check(
            self,
            parent: Any,
            row: int,
            side: int,
            key: str,
            text: str,
            variable: tk.BooleanVar,
    ) -> ttk.Checkbutton:
        offset = 0 if side == 0 else 3
        self._info_button(parent, key).grid(row=row, column=offset, sticky=tk.W, padx=(6, 3), pady=2)
        control = ttk.Checkbutton(parent, text=text, variable=variable)
        control.grid(row=row, column=offset + 1, columnspan=2, sticky=tk.W, padx=(0, 8), pady=2)
        return control

    def _show_solver_info(self, key: str) -> None:
        info = FEM_OPTION_INFO.get(key)
        if not info:
            messagebox.showinfo("FEM option", "No detailed information is available for this option.")
            return
        dialog = tk.Toplevel(self.window)
        dialog.title(str(info.get("title", "FEM option")))
        dialog.geometry("560x520")
        dialog.minsize(480, 420)
        dialog.transient(self.window)
        dialog.configure(background="#f5f7fb")

        header = tk.Frame(dialog, background="#172033")
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=str(info.get("title", "FEM option")),
            background="#172033",
            foreground="white",
            font=("Segoe UI", 14, "bold"),
            padx=16,
            pady=12,
        ).pack(anchor=tk.W)

        body = ttk.Frame(dialog, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(
            body,
            wrap=tk.WORD,
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=10,
            background="white",
            foreground="#111827",
            font=("Segoe UI", 10),
        )
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.configure(yscrollcommand=scrollbar.set)
        text.tag_configure("section", font=("Segoe UI", 10, "bold"), foreground="#172033", spacing1=8, spacing3=2)
        text.tag_configure("body", lmargin1=10, lmargin2=10, spacing3=6)
        for title, field in (
                ("Purpose", "purpose"),
                ("How It Is Used", "use"),
                ("Output Affected", "output"),
                ("Cautions", "caution"),
        ):
            text.insert(tk.END, title + "\n", "section")
            text.insert(tk.END, str(info.get(field, "")) + "\n", "body")
        text.configure(state=tk.DISABLED)

        footer = ttk.Frame(dialog, padding=(14, 0, 14, 14))
        footer.pack(fill=tk.X)
        ttk.Button(footer, text="Close", command=dialog.destroy).pack(side=tk.RIGHT)
        try:
            dialog.grab_set()
            dialog.focus_set()
        except Exception:
            pass

    @staticmethod
    def _visible_paned_window(parent: Any, orient: str) -> tk.PanedWindow:
        """Create a clean cross-theme pane with a discoverable resize divider."""

        cursor = "sb_h_double_arrow" if orient == tk.HORIZONTAL else "sb_v_double_arrow"
        divider_color = "#475569"
        divider_hover_color = "#38bdf8"
        panes = tk.PanedWindow(
            parent,
            orient=orient,
            background=divider_color,
            borderwidth=0,
            relief=tk.FLAT,
            sashwidth=6,
            sashpad=2,
            sashrelief=tk.FLAT,
            showhandle=False,
            opaqueresize=True,
            cursor=cursor,
        )

        def highlight_divider(event: Any) -> None:
            hit = panes.identify(event.x, event.y)
            over_divider = bool(hit and len(hit) > 1 and hit[1] in {"sash", "handle"})
            panes.configure(background=divider_hover_color if over_divider else divider_color)

        def restore_divider(_event: Any) -> None:
            panes.configure(background=divider_color)

        panes.bind("<Motion>", highlight_divider, add="+")
        panes.bind("<Leave>", restore_divider, add="+")
        panes.bind("<ButtonRelease-1>", restore_divider, add="+")
        return panes

    def _apply_material_spec(self, spec: Any) -> bool:
        """Map an ANYmaterial specification onto the solver's scalar controls."""
        try:
            selected = ecosystem_gui.isotropic_material_selection(spec)
        except ecosystem_gui.UnsupportedMaterialSelection as error:
            self.material_library_name.set(self._last_isotropic_material_name)
            messagebox.showerror("Unsupported material", str(error), parent=self.window)
            return False

        self.material_library_name.set(selected.name)
        self._last_isotropic_material_name = selected.name
        self.elastic_modulus_gpa.set(selected.elastic_modulus_gpa)
        self.poisson_ratio.set(selected.poisson_ratio)
        self.yield_stress_mpa.set(selected.yield_stress_mpa)
        self.material_model.set(selected.material_model)
        self.steel_grade.set(selected.steel_grade)
        self.steel_thickness_class.set(selected.steel_thickness_class)
        if selected.unsupported_hardening_kind:
            messagebox.showwarning(
                "Material curve simplified",
                "ANYstructure applied the selected elastic constants and yield stress, but the "
                f"{selected.unsupported_hardening_kind!r} hardening curve is not exposed by the "
                "current runtime controls. The FEM material was set to linear elastic.",
                parent=self.window,
            )
        return True

    def _on_material_library_selected(self, name: str | None = None) -> bool:
        """Apply a public ANYmaterial library entry selected in the dropdown."""
        selected_name = str(name or self.material_library_name.get())
        try:
            spec = ecosystem_gui.material_spec_from_library(selected_name)
        except (KeyError, ValueError) as error:
            self.material_library_name.set(self._last_isotropic_material_name)
            messagebox.showerror("Material library", str(error), parent=self.window)
            return False
        return self._apply_material_spec(spec)

    def _open_material_editor(self) -> tuple[Any, Any]:
        """Open ANYmaterial in a child of the runtime FEM window."""
        try:
            initial_spec = ecosystem_gui.material_spec_from_library(self.material_library_name.get())
        except (KeyError, ValueError):
            initial_spec = None
        return ecosystem_gui.open_material_editor(
            self.window,
            initial_spec=initial_spec,
            on_apply=self._apply_material_spec,
        )

    def _open_anymesher(self) -> tuple[Any, Any]:
        """Open the extracted neutral mesher without starting another mainloop."""
        return ecosystem_gui.open_mesher(self.window)

    def _open_file_inspector(self) -> tuple[Any, Any]:
        """Open the extracted interchange-file inspector."""
        return ecosystem_gui.open_file_inspector(self.window)

    def _build(self) -> None:
        outer = ttk.Frame(self.window, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, background="#172033", bd=0, highlightthickness=0)
        header.pack(fill=tk.X, pady=(0, 12))
        header_inner = tk.Frame(header, background="#172033")
        header_inner.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(
            header_inner,
            text="Experimental full-geometry FEM",
            background="#172033",
            foreground="white",
            font=("Segoe UI", 15, "bold"),
        ).pack(side=tk.LEFT)
        tk.Label(
            header_inner,
            text="ANYsolver " + _require_supported_anysolver(),
            background="#2563eb",
            foreground="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=3,
        ).pack(side=tk.RIGHT)
        tk.Label(
            header,
            text=(
                "Active-line shell/beam analysis. Drag the blue-gray dividers to resize sections; "
                "they highlight blue on hover, and the result divider moves vertically."
            ),
            background="#172033",
            foreground="#d7deeb",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, padx=16, pady=(0, 12))

        self.body_panes = self._visible_paned_window(outer, tk.HORIZONTAL)
        self.body_panes.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(self.body_panes)
        mid_panel = ttk.Frame(self.body_panes)
        right_panel = ttk.Frame(self.body_panes)
        self.body_panes.add(left_panel, minsize=260, width=300, stretch="always")
        self.body_panes.add(mid_panel, minsize=340, width=390, stretch="always")
        self.body_panes.add(right_panel, minsize=360, width=470, stretch="always")

        summary = ttk.LabelFrame(left_panel, text="Active line")
        summary.pack(fill=tk.X, pady=(0, 10))
        summary_text = (
                "Line: " + self.snapshot.line_name
                + "\nDomain: " + (self.snapshot.domain or "unknown")
                + "\nGeometry: " + ("cylinder/panel" if self.snapshot.is_cylinder else "flat panel")
                + "\nPressure [Pa]: " + str(round(self.snapshot.pressure_pa, 3))
        )
        ttk.Label(summary, text=summary_text, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=8)

        buttons = ttk.Frame(left_panel)
        buttons.pack(fill=tk.X, pady=(0, 10))
        self.run_button = ttk.Button(buttons, text="Run FEM", command=self.run)
        self.run_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(buttons, text="Stop", command=self.cancel_run, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=(4, 0))
        self.use_for_buckling_button = ttk.Button(
            buttons,
            text="Use results for prescriptive buckling",
            command=self._send_results_to_fea_buckling,
            state=tk.DISABLED,
        )
        self.use_for_buckling_button.pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(buttons, text="Save FEM...", command=self._save_fem_state).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(buttons, text="Load FEM...", command=self._load_fem_state).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(buttons, text="Inspect FE file...", command=self._open_file_inspector).pack(
            side=tk.LEFT, padx=(4, 0)
        )
        self.progress_bar = ttk.Progressbar(buttons, mode="indeterminate", length=140)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        ttk.Button(buttons, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)

        status_frame = ttk.LabelFrame(left_panel, text="Run status")
        status_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(status_frame, height=8, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 2))

        # Live run graph: replaces the lower third of the status text with a
        # small figure that streams run-type-appropriate measures (collision:
        # displacement/contact force/plastic strain vs time; nonlinear static
        # and post-buckling: the equilibrium path; buckling: mode factors).
        self._live_graph_figure = Figure(figsize=(3.4, 1.8), dpi=100)
        self._live_graph_axis = self._live_graph_figure.add_subplot(111)
        self._live_graph_canvas = FigureCanvasTkAgg(self._live_graph_figure, master=status_frame)
        live_graph_widget = self._live_graph_canvas.get_tk_widget()
        live_graph_widget.configure(height=170)
        live_graph_widget.pack(fill=tk.X, expand=False, padx=8, pady=(0, 8))
        self._live_graph_reset("idle")

        self.options_notebook = ttk.Notebook(mid_panel)
        self.options_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        tab_general = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_general, text="General")

        tab_mesh = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_mesh, text="Mesh")

        tab_geometry = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_geometry, text="Geometry")

        tab_properties = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_properties, text="Properties")

        tab_loads = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_loads, text="Loads")
        tab_bc = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_bc, text="Boundary conditions")

        tab_transient = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_transient, text="Transient runs")

        tab_visualization = ttk.Frame(self.options_notebook)
        self.options_notebook.add(tab_visualization, text="Visualization")

        # --- Mesh tab: sizing, local refinement, and a no-run preview ---
        mesh_size = ttk.LabelFrame(tab_mesh, text="Mesh size")
        mesh_size.pack(fill=tk.X, padx=8, pady=(8, 6))
        self._configure_option_grid(mesh_size)
        self._add_option_row(mesh_size, 0, "mesh_fidelity", "Mesh fidelity", self.mesh_fidelity,
                             ("coarse", "medium", "fine", "very fine"))
        self._add_entry_row(mesh_size, 1, "mesh_size_m", "Mesh size [m]", self.mesh_size_m)

        local_mesh = ttk.LabelFrame(tab_mesh, text="Local mesh refinement (select panels under load and BCs)")
        local_mesh.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_compact_option_grid(local_mesh)
        self._add_compact_check(local_mesh, 0, 0, "local_refinement_enabled", "Refine selected panels",
                                self.local_refinement_enabled)
        self._add_compact_option(local_mesh, 0, 1, "detail_transition_style", "Transition",
                                 self.detail_transition_style, ("graded grid", "local patch (quad+tri)"))
        self._add_compact_entry(local_mesh, 1, 0, "local_refinement_fine_size_m", "Panel fine [m]",
                                self.local_refinement_fine_size_m)
        self._add_compact_entry(local_mesh, 1, 1, "local_refinement_fine_factor", "Panel factor",
                                self.local_refinement_fine_factor)
        self._add_compact_entry(local_mesh, 2, 0, "local_refinement_extent_m", "Panel extent [m]",
                                self.local_refinement_extent_m)
        self._add_compact_entry(local_mesh, 2, 1, "local_refinement_growth_factor", "Panel growth",
                                self.local_refinement_growth_factor)
        panel_actions = ttk.Frame(local_mesh)
        panel_actions.grid(row=3, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=3)
        ttk.Button(panel_actions, text="Use selected panels", command=self._set_local_refinement_from_selection).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(panel_actions, text="Clear panels", command=self._clear_local_refinement_patches).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        ttk.Label(panel_actions, textvariable=self.local_refinement_summary_var).pack(side=tk.LEFT)
        point_group = ttk.LabelFrame(local_mesh, text="Point detail")
        point_group.grid(row=4, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=(3, 6))
        self._configure_compact_option_grid(point_group)
        self._add_compact_check(point_group, 0, 0, "point_refinement_enabled", "Refine selected point",
                                self.point_refinement_enabled)
        self._add_compact_entry(point_group, 1, 0, "point_refinement_x_m", "Point X [m]",
                                self.point_refinement_x_m)
        self._add_compact_entry(point_group, 1, 1, "point_refinement_y_m", "Point Y [m]",
                                self.point_refinement_y_m)
        self._add_compact_entry(point_group, 2, 0, "point_refinement_fine_size_m", "Point fine [m]",
                                self.point_refinement_fine_size_m)
        self._add_compact_entry(point_group, 2, 1, "point_refinement_extent_m", "Point extent [m]",
                                self.point_refinement_extent_m)
        self._add_compact_entry(point_group, 3, 0, "point_refinement_growth_factor", "Point growth",
                                self.point_refinement_growth_factor)
        self._add_compact_entry(point_group, 3, 1, "point_refinement_z_m", "Point Z [m]",
                                self.point_refinement_z_m)
        point_actions = ttk.Frame(point_group)
        point_actions.grid(row=4, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=2)
        self._mesh_point_selection_button = ttk.Button(
            point_actions,
            text="Start selection",
            command=self._toggle_mesh_point_selection,
        )
        self._mesh_point_selection_button.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(point_actions, text="Stop selection",
                   command=lambda: self._set_mesh_point_selection_active(False)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(point_actions, text="Use selected panel center",
                   command=self._set_point_refinement_from_selected_panel).pack(side=tk.LEFT)

        impact_group = ttk.LabelFrame(local_mesh, text="Impact detail preset")
        impact_group.grid(row=5, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=(0, 6))
        self._configure_compact_option_grid(impact_group)
        self._add_compact_check(impact_group, 0, 0, "collision_adaptive_mesh", "Adopt impact point",
                                self.collision_adaptive_mesh_enabled)
        self._add_compact_entry(impact_group, 1, 0, "collision_adaptive_fine_size_m", "Impact fine [m]",
                                self.collision_adaptive_fine_size_m)
        self._add_compact_entry(impact_group, 1, 1, "collision_adaptive_extent_m", "Impact extent [m]",
                                self.collision_adaptive_extent_m)
        self._add_compact_entry(impact_group, 2, 0, "collision_adaptive_growth_factor", "Impact growth",
                                self.collision_adaptive_growth_factor)
        self._add_compact_entry(impact_group, 2, 1, "collision_adaptive_fine_factor", "Impact factor",
                                self.collision_adaptive_fine_factor)
        self._add_compact_entry(impact_group, 3, 0, "collision_adaptive_zone_factor", "Extent / radius",
                                self.collision_adaptive_zone_factor)

        mesh_preview = ttk.LabelFrame(tab_mesh, text="Mesh preview and statistics")
        mesh_preview.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        preview_actions = ttk.Frame(mesh_preview)
        preview_actions.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._mesh_preview_button = ttk.Button(preview_actions, text="Generate mesh", command=self._generate_mesh)
        self._mesh_preview_button.pack(side=tk.LEFT)
        ttk.Button(preview_actions, text="Open ANYmesher...", command=self._open_anymesher).pack(
            side=tk.LEFT, padx=(4, 0)
        )
        ttk.Checkbutton(
            preview_actions,
            text="Show imperfections",
            variable=self.show_imperfections_vis,
            command=self._refresh_mesh_preview_current,
        ).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(preview_actions, text="Scale (0 = auto):").pack(side=tk.LEFT, padx=(12, 4))
        imperfection_scale_entry = ttk.Entry(preview_actions, textvariable=self.imperfection_preview_scale, width=8)
        imperfection_scale_entry.pack(side=tk.LEFT)
        imperfection_scale_entry.bind("<Return>", lambda _event: self._refresh_mesh_preview_current())
        imperfection_scale_entry.bind("<FocusOut>", lambda _event: self._refresh_mesh_preview_current())
        self.mesh_statistics_text = tk.Text(mesh_preview, height=4, wrap=tk.WORD)
        self.mesh_statistics_text.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.mesh_statistics_text.insert(
            "1.0",
            "Press \"Generate mesh\" to build the mesh and see element counts, node counts and element sizes.",
        )
        self.mesh_statistics_text.configure(state=tk.DISABLED)
        self.mesh_preview_parent = ttk.Frame(mesh_preview)
        self.mesh_preview_parent.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.mesh_preview_canvas = None

        # --- Geometry tab: plate thickness regions, plane division, thickness plot ---
        thickness_group = ttk.LabelFrame(tab_geometry, text="Plate thickness regions")
        thickness_group.pack(fill=tk.X, padx=8, pady=(8, 6))
        self._configure_compact_option_grid(thickness_group)
        self._add_compact_entry(thickness_group, 0, 0, "thickness_regions", "Thickness [m]",
                                self.geometry_thickness_m)
        thickness_actions = ttk.Frame(thickness_group)
        thickness_actions.grid(row=1, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=3)
        ttk.Button(thickness_actions, text="Set on selected panels",
                   command=lambda: self._set_thickness_region_from_selection(whole=False)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(thickness_actions, text="Set on whole plate",
                   command=lambda: self._set_thickness_region_from_selection(whole=True)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(thickness_actions, text="Delete region",
                   command=self._delete_selected_thickness_region).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(thickness_actions, text="Clear all",
                   command=self._clear_thickness_regions).pack(side=tk.LEFT)
        selection_geometry = ttk.Frame(thickness_group)
        selection_geometry.grid(row=2, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=3)
        self._geometry_selection_button = ttk.Button(selection_geometry, text="Start selection",
                                                     command=self._toggle_custom_load_selection)
        self._geometry_selection_button.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(selection_geometry, text="Stop selection",
                   command=lambda: self._set_custom_load_selection_active(False)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(selection_geometry, text="Select All",
                   command=self._custom_load_select_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(selection_geometry, text="Clear selection",
                   command=self._custom_load_clear_all).pack(side=tk.LEFT)
        self._thickness_region_tree = ttk.Treeview(
            thickness_group, columns=("thickness", "panels", "area"), show="headings", height=4, selectmode="browse")
        self._thickness_region_tree.heading("thickness", text="Thickness [mm]")
        self._thickness_region_tree.heading("panels", text="Panels")
        self._thickness_region_tree.heading("area", text="Area [m2]")
        self._thickness_region_tree.column("thickness", width=110, stretch=False, anchor=tk.W)
        self._thickness_region_tree.column("panels", width=80, stretch=False, anchor=tk.W)
        self._thickness_region_tree.column("area", width=100, stretch=True, anchor=tk.W)
        self._thickness_region_tree.grid(row=3, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=(3, 8))

        division_group = ttk.LabelFrame(tab_geometry, text="Divide panels by plane")
        division_group.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_compact_option_grid(division_group)
        self._add_compact_option(division_group, 0, 0, "division_plane", "Plane normal",
                                 self.division_plane_axis, ("x", "y", "z"))
        self._add_compact_entry(division_group, 0, 1, "division_plane", "Coordinate [m]",
                                self.division_plane_coord_m)
        division_actions = ttk.Frame(division_group)
        division_actions.grid(row=1, column=0, columnspan=6, sticky=tk.EW, padx=8, pady=(3, 6))
        ttk.Button(division_actions, text="Add division plane",
                   command=self._add_division_plane).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(division_actions,
                  text="Cuts all panels crossing the plane so parts can be selected separately.",
                  foreground="#475569").pack(side=tk.LEFT)

        thickness_plot = ttk.LabelFrame(tab_geometry, text="Thickness plot")
        thickness_plot.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        plot_actions = ttk.Frame(thickness_plot)
        plot_actions.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Button(plot_actions, text="Show thickness plot",
                   command=self._show_thickness_plot).pack(side=tk.LEFT)
        ttk.Label(plot_actions, text="Draws the model coloured by plate thickness.",
                  foreground="#475569").pack(side=tk.LEFT, padx=(8, 0))
        self.geometry_preview_parent = ttk.Frame(thickness_plot)
        self.geometry_preview_parent.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # --- General tab: model contents + solver + buckling resources ---
        contents = ttk.LabelFrame(tab_general, text="Model contents")
        contents.pack(fill=tk.X, padx=8, pady=(8, 6))
        self._configure_option_grid(contents)
        self._add_check_row(contents, 0, "include_stiffeners", "Include stiffener beams", self.include_stiffeners)
        self._add_check_row(contents, 1, "include_girders", "Include girder/frame beams", self.include_girders)
        self._add_check_row(
            contents,
            2,
            "ignore_girder_length",
            "Ignore girder length (single stiffener bay)",
            self.ignore_girder_length,
        )
        self._add_check_row(contents, 3, "include_end_lids", "Top/bottom lid", self.include_end_lids)

        solver_options = ttk.LabelFrame(tab_general, text="Solver")
        solver_options.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_option_grid(solver_options)
        self._add_option_row(
            solver_options,
            0,
            "runtime_solver",
            "Runtime path",
            self.runtime_solver,
            ("stepwise", "static only", "nonlinear static", "ANYsolver capacity workflow"),
        )
        self._add_option_row(solver_options, 1, "shell_element_order", "Shell element", self.shell_element_order,
                             ("S4", "S3", "S6", "S8", "S8R"))
        self._add_option_row(solver_options, 2, "beam_element_order", "Beam element", self.beam_element_order,
                             ("B2", "B3"))
        self._add_option_row(
            solver_options,
            3,
            "analysis_type",
            "Analysis",
            self.analysis_type,
            ("linear eigenvalue", "nonlinear stability", "geometric nonlinear static",
             "geom. + material nonlinear static"),
        )
        self._add_option_row(solver_options, 4, "buckling_analysis_type", "Buckling", self.buckling_analysis_type,
                             ("linear eigenvalue", "nonlinear limit"))
        self._add_option_row(solver_options, 5, "solver_type", "Linear solver", self.solver_type,
                             ("direct", "gmres", "minres", "bicgstab"))
        self._add_entry_row(solver_options, 6, "nonlinear_max_load_factor", "NL max LF", self.nonlinear_max_load_factor)
        self._add_entry_row(solver_options, 7, "nonlinear_steps", "NL steps", self.nonlinear_steps, width=8)
        self._add_entry_row(solver_options, 8, "nonlinear_max_iterations", "NL iterations",
                            self.nonlinear_max_iterations, width=8)
        self._add_entry_row(solver_options, 9, "nonlinear_tolerance", "NL tolerance", self.nonlinear_tolerance)
        self._add_option_row(solver_options, 10, "nonlinear_solution_control", "NL control",
                             self.nonlinear_solution_control, ("newton force control", "arc length"))
        self._add_option_row(solver_options, 11, "nonlinear_convergence_profile", "NL profile",
                             self.nonlinear_convergence_profile, ("auto", "fast", "robust", "balanced", "legacy"))
        self._add_entry_row(solver_options, 12, "nonlinear_assembly_threads", "NL threads",
                            self.nonlinear_assembly_threads, width=8)
        self._nonlinear_static_kinematics_control = self._add_option_row(
            solver_options,
            13,
            "nonlinear_static_kinematics",
            "Kinematics",
            self.nonlinear_static_kinematics,
            _KINEMATICS_LABELS,
        )

        post_buckling = ttk.LabelFrame(tab_general, text="Post-buckling continuation")
        post_buckling.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_compact_option_grid(post_buckling)
        self._add_compact_check(post_buckling, 0, 0, "post_buckling_enabled", "Trace post-buckling response",
                                self.post_buckling_enabled)
        self._add_compact_entry(post_buckling, 1, 0, "post_buckling_stop_load_fraction", "Stop at load fraction",
                                self.post_buckling_stop_load_fraction)
        self._add_compact_entry(post_buckling, 1, 1, "post_buckling_max_displacement_m", "Max displacement [m]",
                                self.post_buckling_max_displacement_m)

        buckling_validity = ttk.LabelFrame(tab_general, text="Buckling validity and resources")
        buckling_validity.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_option_grid(buckling_validity)
        self._add_entry_row(buckling_validity, 0, "buckling_shift_load_factor", "Buckling shift LF",
                            self.buckling_shift_load_factor, width=8)
        self._add_entry_row(buckling_validity, 1, "buckling_load_factor_range", "Buckling LF min/max",
                            self.buckling_min_load_factor, width=8)
        ttk.Entry(buckling_validity, textvariable=self.buckling_max_load_factor, width=8).grid(row=1, column=3,
                                                                                               sticky=tk.EW,
                                                                                               padx=(0, 8), pady=4)
        self._add_entry_row(buckling_validity, 2, "buckling_repeated_tolerance", "Repeated tol.",
                            self.buckling_repeated_tolerance, width=8)
        self._add_check_row(buckling_validity, 3, "buckling_allow_dense_fallback", "Allow dense buckling fallback",
                            self.buckling_allow_dense_fallback)
        self._add_option_row(buckling_validity, 4, "recovery_history_mode", "Recovery history",
                             self.recovery_history_mode, ("full", "selected", "envelope"))
        self._add_entry_row(buckling_validity, 5, "recovery_threads", "Recovery threads", self.recovery_threads,
                            width=8)
        self._add_entry_row(buckling_validity, 6, "memory_limit_mb", "Memory limit [MB]", self.memory_limit_mb, width=8)
        self._add_entry_row(buckling_validity, 7, "capacity_buckling_mode_number", "Capacity mode no.",
                            self.capacity_buckling_mode_number, width=8)
        self._add_entry_row(buckling_validity, 8, "capacity_mesh_min_elements_per_half_wave", "Mode elems/half-wave",
                            self.capacity_mesh_min_elements_per_half_wave, width=8)
        self._add_entry_row(buckling_validity, 9, "num_buckling_modes", "Buckling modes",
                            self.num_buckling_modes, width=8)
        buckling_validity.columnconfigure(3, weight=1)

        members = ttk.LabelFrame(tab_properties, text="Member modelling")
        members.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_option_grid(members)
        self._add_option_row(
            members,
            0,
            "member_model",
            "Member model",
            self.member_model,
            (
                "plates as shell, girders as beams",
                "webs as shells, flanges as beams",
                "all shell",
            ),
        )
        self._add_entry_row(members, 1, "stiffener_eccentricity_m", "Stf. ecc. [m]", self.stiffener_eccentricity_m)
        self._add_entry_row(members, 2, "girder_eccentricity_m", "Girder ecc. [m]", self.girder_eccentricity_m)
        self._add_option_row(members, 3, "member_orientation", "Member orient.", self.member_orientation,
                             ("auto", "global Y", "global Z", "radial"))
        self._add_check_row(members, 4, "beam_consistent_mass", "Consistent beam mass",
                            self.beam_consistent_mass_enabled)

        material = ttk.LabelFrame(tab_properties, text="Material and recovery")
        material.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._configure_option_grid(material)
        self._add_entry_row(material, 0, "stress_percentile", "Stress pct.", self.stress_percentile)
        self._add_option_row(
            material,
            1,
            "material_library",
            "Library material",
            self.material_library_name,
            self.material_library_names,
            command=self._on_material_library_selected,
        )
        self._add_option_row(material, 2, "material_model", "Constitutive", self.material_model,
                             ("linear elastic", "DNV-RP-C208 steel"))
        self._add_option_row(material, 3, "steel_grade", "Steel grade", self.steel_grade,
                             ("S235", "S275", "S355", "S420", "S460"))
        self._add_option_row(
            material,
            4,
            "steel_thickness_class",
            "Steel class",
            self.steel_thickness_class,
            ("auto", "t <= 16", "16 < t <= 40", "40 < t <= 63", "63 < t <= 100"),
        )
        self._add_entry_row(material, 5, "elastic_modulus_gpa", "E [GPa]", self.elastic_modulus_gpa)
        self._add_entry_row(material, 6, "poisson_ratio", "Poisson", self.poisson_ratio)
        self._add_entry_row(material, 7, "yield_stress_mpa", "Yield [MPa]", self.yield_stress_mpa)
        self._add_entry_row(material, 8, "nonlinear_layers", "NL layers", self.nonlinear_layers, width=8)
        ttk.Button(material, text="Choose/edit in ANYmaterial...", command=self._open_material_editor).grid(
            row=9, column=1, columnspan=2, sticky=tk.W, padx=(0, 8), pady=(2, 6)
        )

        imperfections = ttk.LabelFrame(tab_properties, text="Imperfections")
        imperfections.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._configure_option_grid(imperfections)
        self._add_check_row(imperfections, 0, "imperfection_enabled", "Use geometric imperfection",
                            self.imperfection_enabled)
        self._add_option_row(
            imperfections,
            1,
            "imperfection_shape",
            "Shape",
            self.imperfection_shape,
            ("standard plate/cylinder", "none"),
        )
        self._add_entry_row(imperfections, 2, "imperfection_amplitude_m", "Amplitude [m]",
                            self.imperfection_amplitude_m)
        self._add_entry_row(imperfections, 3, "imperfection_waves", "Waves A / B", self.imperfection_wave_a, width=8)
        ttk.Entry(imperfections, textvariable=self.imperfection_wave_b, width=8).grid(row=3, column=3, sticky=tk.EW,
                                                                                      padx=(0, 8), pady=4)
        imperfections.columnconfigure(3, weight=1)

        self._build_mode_shape_imperfection_ui(tab_properties)

        fracture = ttk.LabelFrame(tab_properties, text="Nonlinear static fracture / erosion")
        fracture.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._configure_option_grid(fracture)
        self._add_check_row(fracture, 0, "fracture_enabled", "Use strain-triggered erosion",
                            self.fracture_enabled)
        self._add_entry_row(fracture, 1, "fracture_strain_threshold", "Plastic strain threshold",
                            self.fracture_strain_threshold)
        self._add_entry_row(fracture, 2, "fracture_residual_stiffness", "Residual stiffness frac.",
                            self.fracture_residual_stiffness_fraction)
        self._add_entry_row(fracture, 3, "fracture_max_deleted", "Max deleted fraction",
                            self.fracture_max_deleted_fraction)
        self._add_entry_row(fracture, 4, "fracture_min_load_factor", "Min LF before erosion",
                            self.fracture_min_load_factor)

        # --- Loads tab ---
        general_loads = ttk.LabelFrame(tab_loads, text="Imported loads")
        general_loads.pack(fill=tk.X, padx=8, pady=(8, 6))
        self._configure_option_grid(general_loads)
        self._add_entry_row(general_loads, 0, "pressure_pa", "Pressure [Pa]", self.pressure_pa)
        self._add_entry_row(general_loads, 1, "load_scale", "Load scale", self.load_scale)
        self._add_entry_row(general_loads, 2, "axial_force_n", "Axial force [N]", self.axial_force_n)
        self._add_entry_row(general_loads, 3, "top_bottom_moment_nm", "Bending moment [Nm]", self.top_bottom_moment_nm)
        self._add_entry_row(general_loads, 4, "torsional_moment_nm", "Torsional moment [Nm]", self.torsional_moment_nm)
        self._add_entry_row(general_loads, 5, "shear_force_n", "Shear force [N]", self.shear_force_n)

        self._add_option_row(general_loads, 6, "pressure_direction", "Pressure side", self.pressure_direction,
                             ("front", "back"))
        self._follower_pressure_control = self._add_check_row(
            general_loads,
            7,
            "follower_pressure",
            "Current-area follower pressure (nonlinear only)",
            self.follower_pressure,
        )

        # --- Boundary conditions tab ---
        whole_bc = ttk.LabelFrame(tab_bc, text="Whole-boundary supports (per edge)")
        whole_bc.pack(fill=tk.X, padx=8, pady=(8, 6))
        self._configure_option_grid(whole_bc)
        self._add_check_row(whole_bc, 0, "boundary_auto_supports",
                            "Automatic supports when no edge is constrained below", self.boundary_auto_supports)
        self._add_check_row(whole_bc, 1, "custom_use_nullspace_projection",
                            "Use nullspace projection", self.custom_use_nullspace_projection)
        edge_pick = ttk.Frame(whole_bc)
        edge_pick.grid(row=2, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(2, 0))
        self._info_button(edge_pick, "boundary_edge_select").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(edge_pick, text="Apply to edge:").pack(side=tk.LEFT, padx=(0, 6))
        for key, label in self._boundary_edge_options():
            ttk.Radiobutton(edge_pick, text=label, value=key, variable=self.boundary_edge_choice,
                            command=self._on_boundary_edge_change).pack(side=tk.LEFT, padx=(0, 6))
        self._build_dof_constraint_grid(whole_bc, start_row=3, prefix="boundary",
                                        on_vars=self.boundary_dof_on, value_vars=self.boundary_dof_value)
        self._add_option_row(whole_bc, 10, "symmetry_mode", "Symmetry", self.symmetry_mode,
                             ("none", "x", "y", "z", "cyclic"))

        edge_bc = ttk.LabelFrame(tab_bc, text="Selected-edge supports")
        edge_bc.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_option_grid(edge_bc)
        edge_select = ttk.Frame(edge_bc)
        edge_select.grid(row=0, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(4, 2))
        self.custom_bc_area_var = tk.StringVar(value="Selected Area: 0.000 m2")
        ttk.Label(edge_select, textvariable=self.custom_bc_area_var).pack(side=tk.LEFT, padx=(0, 8))
        self._custom_bc_selection_button = ttk.Button(edge_select, text="Start selection",
                                                      command=self._toggle_custom_load_selection)
        self._custom_bc_selection_button.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(edge_select, text="Select All", command=self._custom_load_select_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(edge_select, text="Clear", command=self._custom_load_clear_all).pack(side=tk.LEFT)
        self._build_dof_constraint_grid(edge_bc, start_row=1, prefix="edge",
                                        on_vars=self.edge_dof_on, value_vars=self.edge_dof_value)
        ttk.Button(edge_bc, text="Set BC on selected edges",
                   command=self._add_custom_bc_from_selection).grid(row=7, column=0, columnspan=4,
                                                                    sticky=tk.EW, padx=8, pady=(2, 6))

        accel = ttk.LabelFrame(tab_loads, text="Acceleration and added mass")
        accel.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_option_grid(accel)
        self._add_entry_row(accel, 0, "acceleration_x_m_s2", "Accel X [m/s2]", self.acceleration_x_m_s2, width=8)
        self._add_entry_row(accel, 1, "acceleration_y_m_s2", "Accel Y [m/s2]", self.acceleration_y_m_s2, width=8)
        self._add_entry_row(accel, 2, "acceleration_z_m_s2", "Accel Z [m/s2]", self.acceleration_z_m_s2, width=8)
        self._add_entry_row(accel, 3, "added_mass_kg", "Added mass [kg]", self.added_mass_kg, width=8)
        self._add_option_row(accel, 4, "added_mass_location", "Mass location", self.added_mass_location,
                             ("none", "plate edge x0", "plate edge x1", "plate edge y0", "plate edge y1",
                              "plate all edges", "cylinder bottom", "cylinder top"))
        custom_loads = ttk.LabelFrame(tab_loads, text="Custom loads")
        custom_loads.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._configure_option_grid(custom_loads)
        self._add_check_row(custom_loads, 0, "custom_load_bc_enabled", "Use custom load/BC mode", self.custom_load_bc_enabled)
        self._add_check_row(custom_loads, 1, "custom_loads_add_to_imported", "Add custom loads to imported/generated loads", self.custom_loads_add_to_imported)
        self._add_check_row(custom_loads, 2, "allow_unbalanced_free_free", "Allow unbalanced free-free loads", self.allow_unbalanced_free_free)

        selection_loads = ttk.LabelFrame(custom_loads, text="Panel and edge selection")
        selection_loads.grid(row=3, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(4, 8))
        self._configure_option_grid(selection_loads)
        self._add_entry_row(selection_loads, 0, "custom_pressure_pa", "Pressure [Pa]", self.custom_pressure_pa)
        self._build_load_component_grid(selection_loads, 1, "selected_edge_load_components",
                                        "Selected-edge load components (global axes):",
                                        self.selected_edge_load_components)
        self.custom_load_area_var = tk.StringVar(value="Selected Area: 0.000 m2")
        ttk.Label(selection_loads, textvariable=self.custom_load_area_var).grid(row=3, column=0, sticky=tk.W, padx=8, pady=4)
        self._custom_load_selection_button = ttk.Button(selection_loads, text="Start selection", command=self._toggle_custom_load_selection)
        self._custom_load_selection_button.grid(row=3, column=1, sticky=tk.EW, padx=(0, 4), pady=4)
        ttk.Button(selection_loads, text="Select All", command=self._custom_load_select_all).grid(row=3, column=2, sticky=tk.EW, padx=(0, 4), pady=4)
        ttk.Button(selection_loads, text="Clear", command=self._custom_load_clear_all).grid(row=3, column=3, sticky=tk.EW, padx=(0, 8), pady=4)
        split_actions_loads = ttk.Frame(selection_loads)
        split_actions_loads.grid(row=4, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=4)
        ttk.Button(split_actions_loads, text="Split A (Z/X)", command=lambda: self._custom_load_split_field("a")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(split_actions_loads, text="Split B (Arc/Y)", command=lambda: self._custom_load_split_field("b")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        selection_loads.columnconfigure(3, weight=1)

        whole_edge_loads = ttk.LabelFrame(custom_loads, text="Whole edge / top-bottom loads")
        whole_edge_loads.grid(row=4, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(0, 8))
        self._configure_option_grid(whole_edge_loads)
        edge_pick_loads = ttk.Frame(whole_edge_loads)
        edge_pick_loads.grid(row=0, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(4, 0))
        self._info_button(edge_pick_loads, "edge_load_edge_select").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(edge_pick_loads, text="Apply to edge:").pack(side=tk.LEFT, padx=(0, 6))
        for key, label in self._boundary_edge_options():
            ttk.Radiobutton(edge_pick_loads, text=label, value=key, variable=self.edge_load_edge_choice,
                            command=self._on_edge_load_edge_change).pack(side=tk.LEFT, padx=(0, 6))
        self._build_load_component_grid(whole_edge_loads, 1, "edge_load_components",
                                        "Edge load components (global axes):",
                                        self.edge_load_components)
        custom_loads.columnconfigure(3, weight=1)

        load_list = ttk.LabelFrame(tab_loads, text="Loads to run")
        load_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        actions_loads = ttk.Frame(load_list)
        actions_loads.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Button(actions_loads, text="Add load", command=self._add_custom_load_from_selection).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(actions_loads, text="Delete load", command=self._delete_selected_custom_load).pack(side=tk.LEFT)
        columns = ("type", "value", "selection", "notes")
        # Modest minimum height: the component grids above take a few extra
        # rows, and the list grows with the window (fill/expand) anyway.
        self._custom_load_tree = ttk.Treeview(load_list, columns=columns, show="headings", height=7, selectmode="browse")
        self._custom_load_tree.heading("type", text="Type")
        self._custom_load_tree.heading("value", text="Value")
        self._custom_load_tree.heading("selection", text="Selection")
        self._custom_load_tree.heading("notes", text="Boundary / notes")
        self._custom_load_tree.column("type", width=88, stretch=False, anchor=tk.W)
        # Wide enough for component summaries such as "fy 1000 N/m; mz 50 Nm/m".
        self._custom_load_tree.column("value", width=170, stretch=False, anchor=tk.W)
        self._custom_load_tree.column("selection", width=160, stretch=True, anchor=tk.W)
        self._custom_load_tree.column("notes", width=200, stretch=True, anchor=tk.W)
        self._custom_load_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self._custom_load_tree_scrollbar = ttk.Scrollbar(load_list, orient=tk.VERTICAL, command=self._custom_load_tree.yview)
        self._custom_load_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))
        self._custom_load_tree.configure(yscrollcommand=self._custom_load_tree_scrollbar.set)

        bc_list = ttk.LabelFrame(tab_bc, text="Applied boundary conditions")
        bc_list.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        actions_bc = ttk.Frame(bc_list)
        actions_bc.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Button(actions_bc, text="Delete BC", command=self._delete_selected_custom_bc).pack(side=tk.LEFT)
        # Show last-run nullspace projection status on the Boundary Conditions tab
        ttk.Label(actions_bc, textvariable=self.last_run_nullspace_text, justify=tk.LEFT).pack(side=tk.RIGHT)
        self._custom_bc_tree = ttk.Treeview(bc_list, columns=columns, show="headings", height=4, selectmode="browse")
        self._custom_bc_tree.heading("type", text="Type")
        self._custom_bc_tree.heading("value", text="Value")
        self._custom_bc_tree.heading("selection", text="Selection")
        self._custom_bc_tree.heading("notes", text="Boundary / notes")
        self._custom_bc_tree.column("type", width=88, stretch=False, anchor=tk.W)
        self._custom_bc_tree.column("value", width=110, stretch=False, anchor=tk.W)
        self._custom_bc_tree.column("selection", width=180, stretch=True, anchor=tk.W)
        self._custom_bc_tree.column("notes", width=240, stretch=True, anchor=tk.W)
        self._custom_bc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self._custom_bc_tree_scrollbar = ttk.Scrollbar(bc_list, orient=tk.VERTICAL, command=self._custom_bc_tree.yview)
        self._custom_bc_tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=(0, 8))
        self._custom_bc_tree.configure(yscrollcommand=self._custom_bc_tree_scrollbar.set)
        self._bind_custom_load_list_traces()
        self._refresh_custom_load_list()

        collision_scroll_frame = ttk.Frame(tab_transient)
        collision_scroll_frame.pack(fill=tk.BOTH, expand=True)
        collision_canvas = tk.Canvas(collision_scroll_frame, highlightthickness=0)
        collision_scrollbar = ttk.Scrollbar(collision_scroll_frame, orient=tk.VERTICAL, command=collision_canvas.yview)
        collision_canvas.configure(yscrollcommand=collision_scrollbar.set)
        collision_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        collision_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        collision_body = ttk.Frame(collision_canvas)
        collision_window_id = collision_canvas.create_window((0, 0), window=collision_body, anchor=tk.NW)
        collision_body.bind(
            "<Configure>",
            lambda _event, canvas=collision_canvas: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        collision_canvas.bind(
            "<Configure>",
            lambda event, canvas=collision_canvas, window_id=collision_window_id: canvas.itemconfigure(
                window_id,
                width=event.width,
            ),
        )

        def _scroll_collision_tab(event: Any, canvas: tk.Canvas = collision_canvas) -> str:
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(3, "units")
            else:
                delta = getattr(event, "delta", 0)
                if delta:
                    canvas.yview_scroll(-max(-3, min(3, int(delta / 120))), "units")
            return "break"

        def _bind_collision_wheel(_event: Any, canvas: tk.Canvas = collision_canvas) -> None:
            canvas.bind_all("<MouseWheel>", _scroll_collision_tab)
            canvas.bind_all("<Button-4>", _scroll_collision_tab)
            canvas.bind_all("<Button-5>", _scroll_collision_tab)

        def _unbind_collision_wheel(_event: Any, canvas: tk.Canvas = collision_canvas) -> None:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        collision_canvas.bind("<Enter>", _bind_collision_wheel)
        collision_canvas.bind("<Leave>", _unbind_collision_wheel)
        self._collision_scroll_canvas = collision_canvas

        time_domain = ttk.LabelFrame(collision_body, text="Custom time-domain load")
        time_domain.pack(fill=tk.X, padx=8, pady=(6, 4))
        self._configure_option_grid(time_domain)
        self._add_check_row(time_domain, 0, "custom_time_domain_enabled", "Run custom load in time domain",
                            self.custom_time_domain_enabled)
        self._add_check_row(time_domain, 1, "custom_time_domain_include_static_load",
                            "Include static load in time domain",
                            self.custom_time_domain_include_static_load)
        self._add_entry_row(time_domain, 2, "custom_time_domain_duration_s", "Duration [s]",
                            self.custom_time_domain_duration_s)
        self._add_entry_row(time_domain, 3, "custom_time_domain_total_time_s", "Total time [s]",
                            self.custom_time_domain_total_time_s)
        self._add_entry_row(time_domain, 4, "custom_time_domain_dt_s", "dt [s]", self.custom_time_domain_dt_s)
        self._add_entry_row(time_domain, 5, "custom_time_domain_result_interval_s", "Result interval [s]",
                            self.custom_time_domain_result_interval_s)
        time_domain.columnconfigure(3, weight=1)

        collision_main = ttk.LabelFrame(collision_body, text="Rigid-sphere collision")
        collision_main.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._configure_compact_option_grid(collision_main)
        self._add_compact_check(collision_main, 0, 0, "collision_enabled", "Run collision transient",
                                self.collision_enabled)
        self._add_compact_check(collision_main, 0, 1, "collision_include_static_load", "Include static FE loads",
                                self.collision_include_static_load)
        self._add_compact_entry(collision_main, 1, 0, "collision_mass_kg", "Mass [kg]",
                                self.collision_mass_kg)
        self._add_compact_entry(collision_main, 1, 1, "collision_radius_m", "Radius [m]",
                                self.collision_radius_m)
        self._add_compact_entry(collision_main, 2, 0, "collision_speed_mps", "Speed [m/s]",
                                self.collision_speed_mps)
        self._add_compact_option(collision_main, 2, 1, "collision_contact_surface", "Surface",
                                 self.collision_contact_surface, ("midsurface", "top", "bottom"))
        self._collision_beam_contact_control = self._add_compact_check(collision_main, 3, 0, "collision_beam_contact",
                                                                       "Direct beam/stiffener contact",
                                                                       self.collision_beam_contact_enabled)
        ttk.Label(collision_main, text="Mesh refinement at the impact point is configured on the Mesh tab.",
                  foreground="#475569").grid(row=3, column=3, columnspan=3, sticky=tk.W, padx=6, pady=2)

        collision_path = ttk.LabelFrame(collision_body, text="Path and time")
        collision_path.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._configure_compact_option_grid(collision_path)
        self._add_compact_entry(collision_path, 0, 0, "collision_start_x_m", "Start X [m]",
                                self.collision_start_x_m)
        self._add_compact_entry(collision_path, 0, 1, "collision_vector_x", "Vector X",
                                self.collision_vector_x)
        self._add_compact_entry(collision_path, 1, 0, "collision_start_y_m", "Start Y [m]",
                                self.collision_start_y_m)
        self._add_compact_entry(collision_path, 1, 1, "collision_vector_y", "Vector Y",
                                self.collision_vector_y)
        self._add_compact_entry(collision_path, 2, 0, "collision_start_z_m", "Start Z [m]",
                                self.collision_start_z_m)
        self._add_compact_entry(collision_path, 2, 1, "collision_vector_z", "Vector Z",
                                self.collision_vector_z)
        self._add_compact_option(collision_path, 3, 0, "collision_time_mode", "Time setup",
                                 self.collision_time_mode, ("auto", "manual"))
        self._add_compact_entry(collision_path, 3, 1, "collision_result_interval_s", "Result int. [s]",
                                self.collision_result_interval_s)
        self._add_compact_entry(collision_path, 4, 0, "collision_auto_steps_per_radius", "Auto steps/r",
                                self.collision_auto_steps_per_radius)
        self._add_compact_entry(collision_path, 4, 1, "collision_auto_post_contact", "Auto post r",
                                self.collision_auto_post_contact_radii)
        self._add_compact_entry(collision_path, 5, 0, "collision_total_time_s", "Manual time [s]",
                                self.collision_total_time_s)
        self._add_compact_entry(collision_path, 5, 1, "collision_dt_s", "Manual dt [s]",
                                self.collision_dt_s)

        collision_stop = ttk.LabelFrame(collision_body, text="Contact and stop controls")
        collision_stop.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._configure_compact_option_grid(collision_stop)
        self._add_compact_entry(collision_stop, 0, 0, "collision_penalty_stiffness", "Penalty [N/m]",
                                self.collision_penalty_stiffness_n_per_m)
        self._add_compact_entry(collision_stop, 0, 1, "collision_contact_damping", "Damping",
                                self.collision_contact_damping)
        self._add_compact_entry(collision_stop, 1, 0, "collision_max_iterations", "Max iters",
                                self.collision_max_iterations, width=8)
        self._add_compact_entry(collision_stop, 1, 1, "collision_max_event_substeps", "Event substeps",
                                self.collision_max_event_substeps, width=8)
        self._add_compact_entry(collision_stop, 2, 0, "collision_penetration_tolerance", "Pen. tol. [m]",
                                self.collision_penetration_tolerance_m)
        self._add_compact_entry(collision_stop, 2, 1, "collision_force_tolerance", "Force tol. [N]",
                                self.collision_force_tolerance_n)
        self._add_compact_entry(collision_stop, 3, 0, "collision_target_penetration", "Target pen. frac.",
                                self.collision_target_penetration_fraction)
        self._add_compact_entry(collision_stop, 3, 1, "collision_bounce_back_time", "Bounce stop [s]",
                                self.collision_bounce_back_time_s)
        self._add_compact_check(collision_stop, 4, 0, "collision_auto_precondition", "Auto-precondition (scout)",
                                self.collision_auto_precondition)
        self._add_compact_entry(collision_stop, 4, 1, "collision_penalty_scale", "Auto penalty scale",
                                self.collision_penalty_scale)

        collision_damage = ttk.LabelFrame(collision_body, text="Impact damage")
        collision_damage.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._configure_compact_option_grid(collision_damage)
        self._add_compact_check(collision_damage, 0, 0, "collision_damage_enabled", "Activate damage",
                                self.collision_damage_enabled)
        self._add_compact_check(collision_damage, 0, 1, "collision_material_nonlinear", "Material nonlinear",
                                self.collision_material_nonlinear_enabled)
        self._add_compact_check(collision_damage, 1, 0, "collision_damage_smoothing", "Neighbor smoothing",
                                self.collision_damage_neighbor_smoothing)
        self._add_compact_option(collision_damage, 1, 1, "collision_damage_criterion", "Damage Criterion",
                                 self.collision_damage_criterion, ("fixed", "mesh_scaled_gl", "rtcl", "rtcl_modified"))
        self._collision_plastic_damage_threshold_control = self._add_compact_entry(
            collision_damage, 2, 0, "collision_plastic_damage_threshold", "Plastic strain lim.",
            self.collision_plastic_damage_threshold)
        self._add_compact_option(collision_damage, 2, 1, "collision_damage_mode", "Mode",
                                 self.collision_damage_mode, ("accumulated_damage", "instant_threshold"))
        self._add_compact_option(collision_damage, 3, 0, "collision_damage_capacity", "Capacity",
                                 self.collision_damage_capacity_basis, ("yield", "ultimate_proxy", "user"))
        self._add_compact_entry(collision_damage, 3, 1, "collision_damage_user_capacity", "User cap. [MPa]",
                                self.collision_damage_user_capacity_mpa)
        self._add_compact_entry(collision_damage, 4, 0, "collision_damage_min_area", "Min area [m2]",
                                self.collision_damage_min_contact_area_m2)
        self._add_compact_entry(collision_damage, 4, 1, "collision_damage_softening", "Softening start",
                                self.collision_damage_softening_start)
        self._add_compact_entry(collision_damage, 5, 0, "collision_damage_delete_at", "Delete damage",
                                self.collision_damage_delete_at)
        self._add_compact_entry(collision_damage, 5, 1, "collision_damage_max_deleted", "Max deleted frac.",
                                self.collision_damage_max_deleted_fraction)

        self._add_compact_entry(collision_damage, 6, 0, "collision_nonlinear_iterations", "NL iters",
                                self.collision_nonlinear_max_iterations, width=8)
        self._add_compact_entry(collision_damage, 6, 1, "collision_nonlinear_tolerance", "NL tol.",
                                self.collision_nonlinear_tolerance)
        self._add_compact_entry(collision_damage, 7, 0, "collision_nonlinear_cutbacks", "NL cutbacks",
                                self.collision_nonlinear_cutbacks, width=8)
        self._collision_nonlinear_kinematics_control = self._add_compact_option(
            collision_damage,
            7,
            1,
            "collision_nonlinear_kinematics",
            "Kinematics",
            self.collision_nonlinear_kinematics,
            _KINEMATICS_LABELS,
        )
        self._collision_damage_beam_hint = ttk.Label(collision_damage, text="", foreground="#7f1d1d")
        self._collision_damage_beam_hint.grid(row=8, column=0, columnspan=6, sticky=tk.W, padx=6, pady=(0, 4))

        renderer_group = ttk.LabelFrame(tab_visualization, text="3D renderer")
        renderer_group.pack(fill=tk.X, padx=8, pady=(8, 0))
        ttk.Label(renderer_group, text="Renderer").pack(
            side=tk.LEFT, padx=(8, 6), pady=6
        )
        renderer_selector = ttk.Combobox(
            renderer_group,
            textvariable=self.renderer_backend_choice,
            values=tuple(BACKEND_LABELS),
            state="readonly",
            width=18,
        )
        renderer_selector.pack(side=tk.LEFT, pady=6)
        renderer_selector.bind("<<ComboboxSelected>>", self._switch_renderer_backend)
        ttk.Label(
            renderer_group,
            textvariable=self.renderer_backend_status,
        ).pack(side=tk.LEFT, padx=10, pady=6)

        vis_group = ttk.LabelFrame(tab_visualization, text="Plot configuration")
        vis_group.pack(fill=tk.X, padx=8, pady=(8, 8))
        self._configure_option_grid(vis_group)
        self._add_check_row(vis_group, 0, "show_plate", "Show plate surface", self.show_plate_vis)
        self._add_check_row(vis_group, 1, "show_stiffeners", "Show stiffeners", self.show_stiffener_vis)
        self._add_check_row(vis_group, 2, "show_girders", "Show girders/frames", self.show_girder_vis)
        self._add_check_row(vis_group, 3, "show_collision_sphere", "Show rigid sphere", self.show_collision_sphere_vis)

        update_canvas_options = self._refresh_canvas_view_options

        self._add_check_row(vis_group, 4, "show_mesh_lines", "Show mesh lines", self.show_mesh_lines_vis).configure(command=update_canvas_options)
        self._add_check_row(vis_group, 5, "show_axis_ruler", "Show axis ruler", self.show_axis_ruler_vis).configure(command=update_canvas_options)

        self._add_entry_row(vis_group, 6, "plate_alpha", "Plate alpha [0-1]", self.plate_alpha_vis, width=8)
        self._add_entry_row(vis_group, 7, "plate_front_color", "Plate front", self.plate_front_color_vis, width=10)
        self._add_entry_row(vis_group, 8, "plate_back_color", "Plate back", self.plate_back_color_vis, width=10)
        self._add_entry_row(vis_group, 9, "member_alpha", "Member alpha [0-1]", self.member_alpha_vis, width=8)
        self._add_entry_row(vis_group, 10, "deformation_scale", "Deformation scale", self.deformation_scale, width=8)
        self._add_option_row(vis_group, 11, "colormap", "Colormap", self.colormap_vis,
                             ("jet", "viridis", "plasma", "inferno", "coolwarm", "greys"))
        vis_actions = ttk.Frame(vis_group)
        vis_actions.grid(row=12, column=0, columnspan=4, sticky=tk.W, padx=8, pady=4)
        ttk.Button(vis_actions, text="Redraw base 3D", command=self._redraw_base_3d).pack(side=tk.LEFT)
        ttk.Button(vis_actions, text="Show results", command=self._show_results).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(vis_actions, text="Previous step", command=self._previous_time_step).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(vis_actions, text="Next step", command=self._next_time_step).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(vis_actions, text="Play", command=self._play_animation).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(vis_actions, text="Stop", command=self._stop_animation).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Checkbutton(vis_actions, text="Fast animation", variable=self.animation_fast_mode).pack(side=tk.LEFT,
                                                                                                    padx=(8, 0))
        self._info_button(vis_actions, "animation_detail").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Label(vis_actions, text="detail").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Combobox(
            vis_actions,
            textvariable=self.animation_detail_vis,
            values=("auto", "full", "fast"),
            state="readonly",
            width=6,
        ).pack(side=tk.LEFT)
        ttk.Label(vis_actions, text="x").pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Entry(vis_actions, textvariable=self.animation_speed_multiplier, width=5).pack(side=tk.RIGHT)
        ttk.Label(vis_actions, text="speed").pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Label(vis_actions, text="ms").pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Entry(vis_actions, textvariable=self.animation_interval_ms, width=5).pack(side=tk.RIGHT)
        replay_slider = ttk.Frame(vis_group)
        replay_slider.grid(row=13, column=0, columnspan=4, sticky=tk.EW, padx=8, pady=(0, 4))
        replay_slider.columnconfigure(1, weight=1)
        self.time_step_label = ttk.Label(replay_slider, text="Time step")
        self.time_step_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self.time_step_slider = ttk.Scale(
            replay_slider,
            from_=0.0,
            to=0.0,
            orient=tk.HORIZONTAL,
            variable=self.time_step_slider_value,
            command=self._on_time_slider,
        )
        self.time_step_slider.grid(row=0, column=1, sticky=tk.EW)
        view_actions = ttk.Frame(vis_group)
        view_actions.grid(row=14, column=0, columnspan=4, sticky=tk.W, padx=8, pady=(0, 4))
        ttk.Button(view_actions, text="Fit", command=lambda: self._set_runtime_3d_view("fit")).pack(side=tk.LEFT,
                                                                                                    padx=(0, 4))
        ttk.Button(view_actions, text="Reset", command=lambda: self._set_runtime_3d_view("reset")).pack(side=tk.LEFT,
                                                                                                        padx=(0, 4))
        ttk.Button(view_actions, text="ISO", command=lambda: self._set_runtime_3d_view("iso")).pack(side=tk.LEFT,
                                                                                                    padx=(0, 4))
        ttk.Button(view_actions, text="Front", command=lambda: self._set_runtime_3d_view("front")).pack(side=tk.LEFT,
                                                                                                        padx=(0, 4))
        ttk.Button(view_actions, text="Side", command=lambda: self._set_runtime_3d_view("side")).pack(side=tk.LEFT,
                                                                                                      padx=(0, 4))
        ttk.Button(view_actions, text="Top", command=lambda: self._set_runtime_3d_view("top")).pack(side=tk.LEFT)

        # --- 3D view and lighting -------------------------------------
        # These settings are applied by the canvas itself, so they take effect
        # immediately on every open view without rebuilding the geometry.
        light_group = ttk.LabelFrame(tab_visualization, text="3D view and lighting")
        light_group.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._configure_option_grid(light_group)

        self._add_check_row(
            light_group, 0, "shading", "Lighting (shaded surfaces)", self.shading_vis,
        ).configure(command=update_canvas_options)
        self._add_entry_row(
            light_group, 1, "light_azimuth", "Light azimuth [deg]", self.light_azimuth_vis, width=8,
        ).bind("<Return>", lambda _event: update_canvas_options())
        self._add_entry_row(
            light_group, 2, "light_elevation", "Light elevation [deg]", self.light_elevation_vis, width=8,
        ).bind("<Return>", lambda _event: update_canvas_options())
        self._add_entry_row(
            light_group, 3, "light_ambient", "Ambient light [0-1]", self.light_ambient_vis, width=8,
        ).bind("<Return>", lambda _event: update_canvas_options())
        self._add_entry_row(
            light_group, 4, "light_specular", "Highlight [0-1]", self.light_specular_vis, width=8,
        ).bind("<Return>", lambda _event: update_canvas_options())
        self._add_check_row(
            light_group, 5, "light_follow_camera", "Light follows camera", self.light_follow_camera_vis,
        ).configure(command=update_canvas_options)
        self._add_check_row(
            light_group, 6, "show_axis_indicator", "Show axis indicator", self.show_axis_indicator_vis,
        ).configure(command=update_canvas_options)
        self._add_check_row(
            light_group, 7, "occlude_lines", "Hide lines behind geometry", self.occlude_lines_vis,
        ).configure(command=update_canvas_options)
        self._add_entry_row(
            light_group, 8, "interactive_detail", "Interactive detail [faces]",
            self.interactive_detail_vis, width=8,
        ).bind("<Return>", lambda _event: update_canvas_options())

        light_actions = ttk.Frame(light_group)
        light_actions.grid(row=9, column=0, columnspan=4, sticky=tk.W, padx=8, pady=(0, 4))
        ttk.Button(
            light_actions, text="Apply view options", command=update_canvas_options,
        ).pack(side=tk.LEFT)
        ttk.Button(
            light_actions, text="Reset lighting", command=self._reset_lighting_defaults,
        ).pack(side=tk.LEFT, padx=(6, 0))

        self.result_panes = self._visible_paned_window(right_panel, tk.VERTICAL)
        self.result_panes.pack(fill=tk.BOTH, expand=True)
        self.upper_result_frame = ttk.LabelFrame(self.result_panes, text="Result text")
        result_frame = ttk.LabelFrame(self.result_panes, text="Run visualization")
        self.result_panes.add(self.upper_result_frame, minsize=120, height=190, stretch="always")
        self.result_panes.add(result_frame, minsize=260, height=430, stretch="always")

        self.upper_result_text = tk.Text(self.upper_result_frame, wrap=tk.WORD, height=10)
        self.upper_result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        scrollbar = ttk.Scrollbar(self.upper_result_frame, orient=tk.VERTICAL, command=self.upper_result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 8), pady=8)
        self.upper_result_text.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(self.upper_result_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(button_frame, text="Copy to Clipboard", command=self._copy_results_to_clipboard).pack(side=tk.RIGHT)
        plot_holder = ttk.Frame(result_frame)
        plot_holder.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.figure_parent = plot_holder
        ttk.Label(
            plot_holder,
            text="Drag divider to resize  |  Left-drag move  |  Right-drag rotate  |  Wheel zoom",
            foreground="#475569",
        ).pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        selector_bar = ttk.Frame(plot_holder)
        selector_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        self._info_button(selector_bar, "display_choice").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(selector_bar, text="Result Case:").pack(side=tk.LEFT, padx=(0, 6))
        self.result_case_selector = ttk.Combobox(
            selector_bar,
            textvariable=self.result_case_choice,
            state="readonly",
            values=tuple(self.result_case_labels),
            width=20,
        )
        self.result_case_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.result_case_selector.bind("<<ComboboxSelected>>", self._on_visualization_choice_changed)

        ttk.Label(selector_bar, text=" Component:").pack(side=tk.LEFT, padx=(6, 6))
        self.component_selector = ttk.Combobox(
            selector_bar,
            textvariable=self.component_choice,
            state="readonly",
            values=tuple(self.component_labels.keys()),
            width=26,
        )
        self.component_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.component_selector.bind("<<ComboboxSelected>>", self._on_visualization_choice_changed)
        probe_bar = ttk.Frame(plot_holder)
        probe_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        ttk.Label(probe_bar, text="Node:").pack(side=tk.LEFT, padx=(0, 4))
        node_entry = ttk.Entry(probe_bar, textvariable=self.probe_node_id, width=8)
        node_entry.pack(side=tk.LEFT)
        node_entry.bind("<Return>", lambda _event: self._show_probe_history())
        ttk.Label(probe_bar, text=" Element:").pack(side=tk.LEFT, padx=(8, 4))
        element_entry = ttk.Entry(probe_bar, textvariable=self.probe_element_id, width=8)
        element_entry.pack(side=tk.LEFT)
        element_entry.bind("<Return>", lambda _event: self._show_probe_history())
        ttk.Button(probe_bar, text="Show history", command=self._show_probe_history).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(probe_bar, text="Show mesh", command=self._show_probe_mesh).pack(side=tk.LEFT, padx=(6, 0))

        color_bar = ttk.Frame(plot_holder)
        color_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        ttk.Label(color_bar, text="Color min:").pack(side=tk.LEFT, padx=(0, 4))
        color_min_entry = ttk.Entry(color_bar, textvariable=self.color_min_vis, width=10)
        color_min_entry.pack(side=tk.LEFT)
        color_min_entry.bind("<Return>", self._on_color_entry_changed)
        color_min_entry.bind("<FocusOut>", self._on_color_entry_changed)
        self.color_min_scale = ttk.Scale(
            color_bar,
            orient=tk.HORIZONTAL,
            variable=self.color_min_slider,
            command=lambda value: self._on_color_slider("min", value),
        )
        self.color_min_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 8))
        ttk.Label(color_bar, text="Max:").pack(side=tk.LEFT, padx=(0, 4))
        color_max_entry = ttk.Entry(color_bar, textvariable=self.color_max_vis, width=10)
        color_max_entry.pack(side=tk.LEFT)
        color_max_entry.bind("<Return>", self._on_color_entry_changed)
        color_max_entry.bind("<FocusOut>", self._on_color_entry_changed)
        self.color_max_scale = ttk.Scale(
            color_bar,
            orient=tk.HORIZONTAL,
            variable=self.color_max_slider,
            command=lambda value: self._on_color_slider("max", value),
        )
        self.color_max_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self._refresh_figure()
        self._write_status("Ready. ANYstructure production FE mesh solver is available.")

    def _build_mode_shape_imperfection_ui(self, parent: ttk.Widget) -> None:
        group = ttk.LabelFrame(parent, text="Mode Shape Imperfections")
        group.pack(fill=tk.X, padx=8, pady=(0, 8))

        note = ttk.Label(group,
                         text="Note: The first imperfection type (DNVGL recommendations) can be set before obtaining the mode shape. The second type requires you to obtain the mode shape first.",
                         wraplength=400, justify=tk.LEFT)
        note.pack(fill=tk.X, padx=8, pady=4)

        columns = ("mode", "factor")
        self.mode_shape_tree = ttk.Treeview(group, columns=columns, show="headings", height=3)
        self.mode_shape_tree.heading("mode", text="Mode shape number")
        self.mode_shape_tree.heading("factor", text="Scaling factor")
        self.mode_shape_tree.column("mode", width=150)
        self.mode_shape_tree.column("factor", width=150)
        self.mode_shape_tree.pack(fill=tk.X, padx=8, pady=4)

        controls = ttk.Frame(group)
        controls.pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(controls, text="Mode:").pack(side=tk.LEFT, padx=(0, 4))
        self.mode_shape_entry = ttk.Entry(controls, width=10)
        self.mode_shape_entry.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(controls, text="Factor:").pack(side=tk.LEFT, padx=(0, 4))
        self.mode_factor_entry = ttk.Entry(controls, width=10)
        self.mode_factor_entry.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(controls, text="Add", command=self._add_mode_shape_imperfection).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(controls, text="Remove", command=self._remove_mode_shape_imperfection).pack(side=tk.LEFT,
                                                                                               padx=(0, 4))

        ttk.Button(group, text="Set to mesh", command=self._set_mode_shapes_to_mesh).pack(anchor=tk.W, padx=8,
                                                                                          pady=(4, 8))

        self._sync_mode_shapes_from_json()

    def _add_mode_shape_imperfection(self):
        mode = self.mode_shape_entry.get().strip()
        factor = self.mode_factor_entry.get().strip()
        if mode and factor:
            self.mode_shape_tree.insert("", tk.END, values=(mode, factor))
            self._sync_mode_shapes_to_json()

    def _remove_mode_shape_imperfection(self):
        for item in self.mode_shape_tree.selection():
            self.mode_shape_tree.delete(item)
        self._sync_mode_shapes_to_json()

    def _sync_mode_shapes_to_json(self):
        items = []
        for item in self.mode_shape_tree.get_children():
            values = self.mode_shape_tree.item(item, "values")
            items.append({"mode": int(values[0]), "factor": float(values[1])})
        self.imperfection_mode_shapes_json.set(json.dumps(items))

    def _sync_mode_shapes_from_json(self):
        for item in self.mode_shape_tree.get_children():
            self.mode_shape_tree.delete(item)
        try:
            items = json.loads(self.imperfection_mode_shapes_json.get())
            for item in items:
                self.mode_shape_tree.insert("", tk.END, values=(str(item["mode"]), str(item["factor"])))
        except Exception:
            pass

    def cancel_run(self) -> None:
        self._cancel_requested = True
        if self.cancel_button is not None:
            self.cancel_button.configure(state=tk.DISABLED)

    def _show_figure(self, figure: Figure, parent: Any | None = None) -> None:
        if parent is None and self.figure_canvas is not None:
            parent = self.figure_canvas.get_tk_widget().master
        if parent is None:
            return
        if self.figure_canvas is not None:
            self.figure_canvas.get_tk_widget().destroy()
            self.figure_canvas = None
        if self.figure_toolbar is not None:
            self.figure_toolbar.destroy()
            self.figure_toolbar = None
        if self.figure_toolbar_frame is not None:
            self.figure_toolbar_frame.destroy()
            self.figure_toolbar_frame = None

        toolbar_frame = ttk.Frame(parent)
        self.figure_toolbar_frame = toolbar_frame
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        self.figure_canvas = FigureCanvasTkAgg(figure, master=parent)
        self.figure_toolbar = NavigationToolbar2Tk(self.figure_canvas, toolbar_frame, pack_toolbar=False)
        self.figure_toolbar.update()
        self.figure_toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.figure_canvas.draw()
        self.figure_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    @staticmethod
    def _fit_preview_figure_to_canvas(figure: Figure, width: int, height: int) -> None:
        if width < 80 or height < 80:
            return
        figure.set_size_inches(width / figure.dpi, height / figure.dpi, forward=False)
        try:
            figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=0.96)
        except Exception:
            pass
        zoom = 2.25
        if min(width, height) > 340:
            zoom = 2.75
        if min(width, height) > 520:
            zoom = 3.25
        for axis in figure.axes:
            if not hasattr(axis, "get_zlim"):
                continue
            axis.set_position([-0.08, -0.12, 1.16, 1.16])
            axis.margins(0.0)
            try:
                axis.set_anchor("C")
            except Exception:
                pass
            try:
                axis.set_proj_type("ortho")
            except Exception:
                pass
            try:
                extents = RuntimeFEMWindow._preview_axis_data_extents(axis)
                if extents is not None:
                    x_limits, y_limits, z_limits = extents
                    x_span_raw = max(abs(x_limits[1] - x_limits[0]), 1.0e-6)
                    y_span_raw = max(abs(y_limits[1] - y_limits[0]), 1.0e-6)
                    z_span_raw = max(abs(z_limits[1] - z_limits[0]), 1.0e-6)
                    pad = 0.04 * max(x_span_raw, y_span_raw, z_span_raw)
                    x_mid = 0.5 * (x_limits[0] + x_limits[1])
                    y_mid = 0.5 * (y_limits[0] + y_limits[1])
                    z_mid = 0.5 * (z_limits[0] + z_limits[1])
                    axis.set_xlim3d(x_mid - 0.5 * x_span_raw - pad, x_mid + 0.5 * x_span_raw + pad)
                    axis.set_ylim3d(y_mid - 0.5 * y_span_raw - pad, y_mid + 0.5 * y_span_raw + pad)
                    axis.set_zlim3d(z_mid - 0.5 * z_span_raw - pad, z_mid + 0.5 * z_span_raw + pad)
                x_limits = axis.get_xlim3d()
                y_limits = axis.get_ylim3d()
                z_limits = axis.get_zlim3d()
                x_span = max(abs(x_limits[1] - x_limits[0]), 1.0e-6)
                y_span = max(abs(y_limits[1] - y_limits[0]), 1.0e-6)
                z_span = max(abs(z_limits[1] - z_limits[0]), 1.0e-6)
                axis.set_box_aspect((x_span, y_span, z_span), zoom=zoom)
            except TypeError:
                try:
                    axis.set_box_aspect((x_span, y_span, z_span))
                except Exception:
                    pass
            except Exception:
                pass

    @staticmethod
    def _preview_axis_data_extents(axis: Any) -> tuple[tuple[float, float], tuple[float, float], tuple[
        float, float]] | None:
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []

        def add(values: Any, target: list[float]) -> None:
            try:
                arr = np.asarray(values, dtype=float).reshape(-1)
            except Exception:
                return
            arr = arr[np.isfinite(arr)]
            target.extend(float(value) for value in arr)

        for line in getattr(axis, "lines", []):
            try:
                x_data, y_data, z_data = line.get_data_3d()
            except Exception:
                continue
            add(x_data, xs)
            add(y_data, ys)
            add(z_data, zs)
        for collection in getattr(axis, "collections", []):
            segments = getattr(collection, "_segments3d", None)
            if segments is not None:
                for segment in segments:
                    arr = np.asarray(segment, dtype=float)
                    if arr.ndim == 2 and arr.shape[1] >= 3:
                        add(arr[:, 0], xs)
                        add(arr[:, 1], ys)
                        add(arr[:, 2], zs)
                continue
            vec = getattr(collection, "_vec", None)
            if vec is not None:
                arr = np.asarray(vec, dtype=float)
                if arr.ndim == 2 and arr.shape[0] >= 3:
                    add(arr[0], xs)
                    add(arr[1], ys)
                    add(arr[2], zs)
        if not xs or not ys or not zs:
            return None
        return ((min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs)))

    def _generate_mesh(self) -> None:
        """Build the mesh for the current options and draw the full 3D model (no analysis run).

        The mesh is rendered in the internal 2.5D tkinter viewer embedded on the
        Mesh tab - the same viewer used for results, but showing the bare mesh.
        """
        if getattr(self, "_imperfection_mesh", None) is not None:
            if not messagebox.askyesno("Generate mesh",
                                       "Warning: You are about to overwrite the generated custom imperfection mesh. Do you want to continue?"):
                return
            self._imperfection_mesh = None
            self._imperfection_base_mesh = None

        try:
            options = self._options()
            config = _solver_config_from_options(options)
            geometry = _popup_geometry_summary(self)
            generated = build_runtime_generated_geometry(geometry, config)
        except Exception as error:
            messagebox.showwarning("Mesh generation", "Could not build the mesh:\n" + str(error))
            return
        self._render_mesh_preview_canvas(generated)
        metrics = generated.get("mesh_metrics", {}) or {}
        adaptive = generated.get("adaptive_mesh", {}) or {}
        summary = "Generated mesh: {count} elements, {lo:.0f}-{hi:.0f} mm".format(
            count=int(metrics.get("shell_element_count", 0)),
            lo=float(metrics.get("min_element_size_m", 0.0)) * 1000.0,
            hi=float(metrics.get("max_element_size_m", 0.0)) * 1000.0,
        )
        if adaptive.get("enabled"):
            summary += " (adaptive refinement)"
        self._write_status(summary)
        self._write_mesh_statistics(generated, metrics, adaptive)

    def _selected_mode_shape_rows(self) -> list[dict[str, Any]]:
        try:
            rows = json.loads(str(self.imperfection_mode_shapes_json.get()) or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            rows = []
        return [row for row in rows if isinstance(row, dict) and row.get("mode") is not None]

    def _set_mode_shapes_to_mesh(self):
        """Build mesh, run linear buckling, extract mode shapes, and perturb the mesh."""
        if not self._selected_mode_shape_rows():
            messagebox.showinfo(
                "Imperfection generation",
                "No buckling mode shapes are selected, so there is nothing to set on the mesh.\n\n"
                "In the 'Mode Shape Imperfections' table above, enter a mode shape number "
                "and a scaling factor and press 'Add' (repeat for every mode you want to "
                "combine), then press 'Set to mesh' again.",
            )
            return
        try:
            options = self._options()
            config = _solver_config_from_options(options)
            geometry = _popup_geometry_summary(self)
            generated = build_runtime_generated_geometry(geometry, config)

            # We need to run a buckling solve using fe_solver.
            # But the buckling is normally run in run_production_fem or lightweight.
            # I will add a helper to run just buckling and perturb the mesh.
            self._write_status("Running buckling analysis to extract mode shapes...")
            self.window.update_idletasks()
            perturbed_mesh = fe_solver.apply_mode_shape_imperfections(generated, config, geometry)
            self._imperfection_mesh = perturbed_mesh
            self._imperfection_base_mesh = generated

            self.show_imperfections_vis.set(True)
            self._render_mesh_preview_canvas(generated)
            self._write_status("Mode shape imperfections applied successfully.")
        except Exception as error:
            messagebox.showwarning("Imperfection generation",
                                   "Could not generate mode shape imperfections:\n" + str(error))

    def _render_mesh_preview_canvas(self, generated: dict, fit_view: bool | None = None) -> None:
        """Draw the generated mesh into the embedded Mesh-tab 3D viewer.

        The camera is fitted only for a new mesh (or when ``fit_view`` forces
        it) so re-rendering after a view-option change keeps the user's view,
        exactly like the result canvas refresh.
        """
        parent = getattr(self, "mesh_preview_parent", None)
        if parent is None:
            return
        if self.mesh_preview_canvas is None:
            self.mesh_preview_canvas = self._create_3d_canvas(parent, bg="white")
            self.mesh_preview_canvas.pack(fill=tk.BOTH, expand=True)
        if fit_view is None:
            fit_view = getattr(self, "_last_preview_mesh", None) is not generated
        self._last_preview_mesh = generated
        canvas = self.mesh_preview_canvas
        self._apply_canvas_view_options(canvas)
        # Same refresh contract as the result canvas: smooth (item-reusing)
        # refresh when only view options changed, full clear for a new mesh.
        canvas.clear(keep_canvas=not fit_view)
        self._populate_canvas_with_mesh(canvas, generated)
        if fit_view:
            canvas.fit_to_scene()
        canvas.redraw()

    def _refresh_mesh_preview_current(self) -> None:
        """Redraw the mesh preview with the current view options (no rebuild)."""
        generated = getattr(self, "_last_preview_mesh", None)
        if generated is None or getattr(self, "mesh_preview_canvas", None) is None:
            return
        self._render_mesh_preview_canvas(generated, fit_view=False)

    def _mesh_preview_imperfection_offsets(self, generated: dict) -> dict[int, tuple[float, float, float]]:
        """Nodal imperfection offsets to visualize on the mesh preview."""
        if not bool(getattr(self, "show_imperfections_vis", None) and self.show_imperfections_vis.get()):
            return {}
        imperfect = getattr(self, "_imperfection_mesh", None)
        base = getattr(self, "_imperfection_base_mesh", None)
        if imperfect is not None and base is not None:
            base_nodes = {int(n["id"]): n["coords"] for n in base.get("nodes", ()) or () if "id" in n}
            offsets: dict[int, tuple[float, float, float]] = {}
            for n in imperfect.get("nodes", ()) or ():
                node_id = int(n.get("id", 0))
                base_coords = base_nodes.get(node_id)
                if base_coords is None:
                    continue
                delta = (
                    float(n["coords"][0]) - float(base_coords[0]),
                    float(n["coords"][1]) - float(base_coords[1]),
                    float(n["coords"][2]) - float(base_coords[2]),
                )
                if max(abs(value) for value in delta) > 1.0e-15:
                    offsets[node_id] = delta
            return offsets
        try:
            options = self._options()
            # Standard-imperfection offsets require a backend model build, so
            # cache them per generated mesh + imperfection settings; toggling
            # the checkbox or rotating must not rebuild the FE model.
            cache_key = (
                id(generated),
                bool(options.imperfection_enabled),
                str(options.imperfection_shape),
                float(options.imperfection_amplitude_m),
                int(options.imperfection_wave_a),
                int(options.imperfection_wave_b),
                str(options.member_model),
            )
            cached = getattr(self, "_imperfection_offsets_cache", None)
            if cached is not None and cached[0] == cache_key:
                return cached[1]
            config = _solver_config_from_options(options)
            geometry = _popup_geometry_summary(self)
            offsets = fe_solver.runtime_imperfection_preview_offsets(generated, config, geometry)
            self._imperfection_offsets_cache = (cache_key, offsets)
            return offsets
        except Exception:
            return {}

    def _imperfection_preview_scale_value(
        self,
        offsets: dict[int, tuple[float, float, float]],
        nodes: dict[int, Any],
    ) -> float:
        """Display multiplier for imperfection offsets; 0 in the entry = auto."""
        requested = _tk_var_float(self.imperfection_preview_scale, 0.0)
        if requested > 0.0:
            return requested
        max_offset = max(
            (math.sqrt(dx * dx + dy * dy + dz * dz) for dx, dy, dz in offsets.values()),
            default=0.0,
        )
        if max_offset <= 0.0 or not nodes:
            return 1.0
        values = list(nodes.values())
        spans = [
            max(float(coord[axis]) for coord in values) - min(float(coord[axis]) for coord in values)
            for axis in range(3)
        ]
        extent = max(max(spans), 1.0e-6)
        return max(0.05 * extent / max_offset, 1.0)

    def _refresh_mesh_preview_if_present(self) -> None:
        """Rebuild and redraw the left mesh preview if it has already been shown.

        Called after a point pick or panel-centre selection so the detail-mesh
        marker appears immediately, without the user pressing Generate mesh
        again.  No-op before the first preview build.
        """
        if getattr(self, "mesh_preview_canvas", None) is None:
            return
        try:
            options = self._options()
            config = _solver_config_from_options(options)
            geometry = _popup_geometry_summary(self)
            generated = build_runtime_generated_geometry(geometry, config)
        except Exception:
            return
        self._render_mesh_preview_canvas(generated)

    def _populate_canvas_with_mesh(self, canvas: "Tkinter3DCanvas", generated: dict) -> None:
        """Render shell elements as outlined faces and beams as lines (mesh only).

        With "Show imperfections" enabled, the nodes are displaced by the
        applied imperfection field (scaled for visibility) and the elements are
        colour coded by imperfection magnitude with a colour bar.
        """
        nodes = {int(n["id"]): n["coords"] for n in generated.get("nodes", ()) or () if "id" in n}
        offsets = self._mesh_preview_imperfection_offsets(generated)
        scale = self._imperfection_preview_scale_value(offsets, nodes) if offsets else 0.0
        magnitudes_mm = {
            node_id: 1000.0 * math.sqrt(dx * dx + dy * dy + dz * dz)
            for node_id, (dx, dy, dz) in offsets.items()
        }
        max_magnitude_mm = max(magnitudes_mm.values(), default=0.0)
        if offsets and max_magnitude_mm > 0.0:
            try:
                canvas.set_thickness_legend(
                    list(magnitudes_mm.values()),
                    unit="mm",
                    title="Imperfection",
                    width=120,
                    value_range=(0.0, max_magnitude_mm),
                )
            except Exception:
                pass
        else:
            try:
                canvas.clear_thickness_legend()
            except Exception:
                pass

        def display_point(node_id: int) -> Point3D:
            coords = nodes[node_id]
            offset = offsets.get(node_id)
            if offset is None or scale <= 0.0:
                return Point3D(float(coords[0]), float(coords[1]), float(coords[2]))
            return Point3D(
                float(coords[0]) + offset[0] * scale,
                float(coords[1]) + offset[1] * scale,
                float(coords[2]) + offset[2] * scale,
            )

        shell_polygons = []
        shell_colors = []
        shell_back_colors = []
        for shell in generated.get("shells", ()) or ():
            ids = [int(i) for i in shell.get("node_ids", ()) or () if int(i) in nodes]
            if len(ids) in (3, 6):
                corners = ids[:3]
            elif len(ids) >= 4:
                corners = ids[:4]
            else:
                corners = ids
            if len(corners) < 3:
                continue
            shell_polygons.append([display_point(i) for i in corners])
            if offsets and max_magnitude_mm > 0.0:
                element_magnitude = sum(magnitudes_mm.get(i, 0.0) for i in corners) / len(corners)
                face_color = _interpolate_thickness_color(element_magnitude, 0.0, max_magnitude_mm)
                back_color = face_color
            else:
                face_color = "#dbe4f0"
                back_color = "#c3cede"
            shell_colors.append(face_color)
            shell_back_colors.append(back_color)
        if shell_polygons:
            canvas.add_faces(
                shell_polygons,
                colors=shell_colors,
                back_colors=shell_back_colors,
                outline="#334155",
                width=1,
            )
        for beam in generated.get("beams", ()) or ():
            ids = [int(i) for i in beam.get("node_ids", ()) or () if int(i) in nodes]
            if len(ids) < 2:
                continue
            pts = [display_point(i) for i in ids]
            for k in range(len(pts) - 1):
                canvas.add_line(pts[k], pts[k + 1], color="#1d4ed8", width=2)
        self._draw_mesh_detail_overlays(canvas, generated, nodes)
        # Live point-refinement crosshair: the extent circle already comes from
        # the adaptive overlay above, so only the centre marker is added here.
        if hasattr(self, "point_refinement_enabled"):
            self._draw_point_refinement_marker(canvas, _popup_geometry_summary(self), draw_circle=False)

    def _draw_mesh_detail_overlays(self, canvas: "Tkinter3DCanvas", generated: dict, nodes: dict[int, Any]) -> None:
        adaptive = generated.get("adaptive_mesh", {}) or {}
        if not adaptive.get("enabled"):
            return
        plot_type = str(generated.get("plot_type", "flat")).lower()
        if plot_type == "cylinder":
            self._draw_cylinder_mesh_detail_overlays(canvas, generated, adaptive)
            return
        if plot_type != "flat":
            return
        if nodes:
            xs = [float(coord[0]) for coord in nodes.values()]
            ys = [float(coord[1]) for coord in nodes.values()]
            span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0e-6)
            z = max(float(coord[2]) for coord in nodes.values()) + 0.004 * span
        else:
            z = 0.0
        for source in adaptive.get("sources") or [adaptive]:
            if not isinstance(source, dict):
                continue
            if source.get("source") == "selected_panels":
                extent = float(source.get("extent_m", 0.0) or 0.0)
                for region in source.get("regions", ()) or ():
                    min_a = float(region.get("min_a", 0.0)) - extent
                    max_a = float(region.get("max_a", 0.0)) + extent
                    min_b = float(region.get("min_b", 0.0)) - extent
                    max_b = float(region.get("max_b", 0.0)) + extent
                    pts = [
                        Point3D(min_a, min_b, z),
                        Point3D(max_a, min_b, z),
                        Point3D(max_a, max_b, z),
                        Point3D(min_a, max_b, z),
                        Point3D(min_a, min_b, z),
                    ]
                    for start, end in zip(pts, pts[1:]):
                        canvas.add_line(start, end, color="#f59e0b", width=3, draw_overlay=True)
                continue
            point = source.get("impact_point_m") or source.get("point_m")
            if not point:
                continue
            cx, cy = float(point[0]), float(point[1])
            radius = float(source.get("extent_m", source.get("fine_radius_m", 0.0)) or 0.0)
            if radius <= 0.0:
                continue
            color = "#dc2626" if source.get("source") == "impact" else "#7c3aed"
            theta = np.linspace(0.0, 2.0 * math.pi, 48)
            pts = [Point3D(cx + radius * math.cos(t), cy + radius * math.sin(t), z) for t in theta]
            pts.append(pts[0])
            for start, end in zip(pts, pts[1:]):
                canvas.add_line(start, end, color=color, width=3, draw_overlay=True)

    def _draw_cylinder_mesh_detail_overlays(self, canvas: "Tkinter3DCanvas", generated: dict, adaptive: dict) -> None:
        if generated.get("is_cone"):
            base_radius = max(_safe_float(generated.get("cone_r1_m"), 1.0), 1.0e-9)
            base_radius_top = max(_safe_float(generated.get("cone_r2_m"), 1.0), 1.0e-9)
        else:
            base_radius = max(_safe_float(generated.get("radius_m"), 1.0), 1.0e-9)
            base_radius_top = base_radius
        length = max(_safe_float(generated.get("length_m"), 1.0), 1.0e-9)
        offset = max(base_radius * 0.006, 2.0e-4)

        def surface_point(z: float, arc: float) -> Point3D:
            z_clamped = min(max(float(z), 0.0), length)
            arc_wrapped = float(arc) % max(2.0 * math.pi * base_radius, 1.0e-9)
            theta = arc_wrapped / base_radius
            t = z_clamped / length if length > 0 else 0.0
            r_local = base_radius + t * (base_radius_top - base_radius)
            draw_radius = r_local + offset
            return Point3D(draw_radius * math.cos(theta), draw_radius * math.sin(theta), z_clamped)

        def draw_polyline(points: list[Point3D], color: str, width: int = 3) -> None:
            for start, end in zip(points, points[1:]):
                canvas.add_line(start, end, color=color, width=width, draw_overlay=True)

        for source in adaptive.get("sources") or [adaptive]:
            if not isinstance(source, dict):
                continue
            if source.get("source") == "selected_panels":
                extent = max(_safe_float(source.get("extent_m")), 0.0)
                for region in source.get("regions", ()) or ():
                    min_z = min(max(_safe_float(region.get("min_a")) - extent, 0.0), length)
                    max_z = min(max(_safe_float(region.get("max_a")) + extent, 0.0), length)
                    min_arc = _safe_float(region.get("min_b")) - extent
                    max_arc = _safe_float(region.get("max_b")) + extent
                    steps = max(4, int(math.ceil(abs(max_arc - min_arc) / max(radius * math.pi / 36.0, 1.0e-9))))
                    lower = [surface_point(min_z, min_arc + (max_arc - min_arc) * index / steps) for index in
                             range(steps + 1)]
                    upper = [surface_point(max_z, min_arc + (max_arc - min_arc) * index / steps) for index in
                             range(steps + 1)]
                    draw_polyline(lower, "#f59e0b")
                    draw_polyline(upper, "#f59e0b")
                    draw_polyline([surface_point(min_z, min_arc), surface_point(max_z, min_arc)], "#f59e0b")
                    draw_polyline([surface_point(min_z, max_arc), surface_point(max_z, max_arc)], "#f59e0b")
                continue

            point = source.get("impact_point_m") or source.get("point_m")
            if not point:
                continue
            center_z, center_arc = float(point[0]), float(point[1])
            extent = _safe_float(source.get("extent_m", source.get("fine_radius_m", 0.0)))
            if extent <= 0.0:
                continue
            color = "#dc2626" if source.get("source") == "impact" else "#7c3aed"
            angles = np.linspace(0.0, 2.0 * math.pi, 72)
            circle = [
                surface_point(center_z + extent * math.cos(angle), center_arc + extent * math.sin(angle))
                for angle in angles
            ]
            circle.append(circle[0])
            draw_polyline(circle, color)

    def _write_mesh_statistics(self, generated: dict, metrics: dict, adaptive: dict) -> None:
        """Populate the Mesh-tab statistics box from a preview build (no analysis run)."""
        widget = getattr(self, "mesh_statistics_text", None)
        if widget is None:
            return
        node_count = len(generated.get("nodes", ()) or ())
        shell_count = int(metrics.get("shell_element_count", len(generated.get("shells", ()) or ())))
        beam_count = len(generated.get("beams", ()) or ())
        lines = [
            "Mesh statistics (preview only - no analysis run)",
            "",
            f"Shell elements : {shell_count}",
            f"Beam elements  : {beam_count}",
            f"Nodes          : {node_count}",
        ]
        if metrics:
            lines.append(
                "Element size   : {nom:.0f} mm nominal ({lo:.0f}-{hi:.0f} mm range)".format(
                    nom=float(metrics.get("nominal_element_size_m", 0.0)) * 1000.0,
                    lo=float(metrics.get("min_element_size_m", 0.0)) * 1000.0,
                    hi=float(metrics.get("max_element_size_m", 0.0)) * 1000.0,
                )
            )
            ratio = metrics.get("min_edge_over_max_edge")
            if ratio is not None:
                lines.append(f"Min/max edge   : {float(ratio):.2f}")
        if adaptive.get("enabled"):
            lines.append("")
            lines.append("Local detail meshes: ON")
            for source in (adaptive.get("sources") or [adaptive]):
                if not isinstance(source, dict):
                    continue
                fine_mm = float(source.get("fine_element_size_m", 0.0)) * 1000.0
                requested_mm = float(source.get("requested_fine_size_m", 0.0)) * 1000.0
                if source.get("source") == "selected_panels":
                    lines.append(
                        "  Panels: {count} region(s), fine {fine:.1f} mm, growth {growth:.2f}".format(
                            count=int(source.get("region_count", 0)),
                            fine=fine_mm,
                            growth=float(source.get("growth_factor", 1.0)),
                        )
                    )
                else:
                    point = source.get("impact_point_m") or source.get("point_m") or [0.0, 0.0]
                    label = "Impact" if source.get("source") == "impact" else "Point"
                    radius_mm = float(source.get("extent_m", source.get("fine_radius_m", 0.0))) * 1000.0
                    lines.append(
                        "  {label}: fine {fine:.1f} mm, radius {radius:.0f} mm, growth {growth:.2f} at ({x:.2f}, {y:.2f}) m".format(
                            label=label,
                            fine=fine_mm,
                            radius=radius_mm,
                            growth=float(source.get("growth_factor", 1.0)),
                            x=float(point[0]),
                            y=float(point[1]),
                        )
                    )
                if requested_mm > 0.0:
                    lines.append(f"    Requested size: {requested_mm:.1f} mm")
                if source.get("floored_at_thickness"):
                    thickness_mm = float(source.get("plate_thickness_m", 0.0)) * 1000.0
                    lines.append(f"    Floored at plate thickness t = {thickness_mm:.1f} mm")
        else:
            lines.append("")
            lines.append("Local detail meshes: OFF")
        text = "\n".join(lines)
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state=tk.DISABLED)

    def _show_preview_figure(self, figure: Figure, parent: Any) -> None:
        if self.preview_canvas is not None:
            self.preview_canvas.get_tk_widget().destroy()
            self.preview_canvas = None

        self.preview_canvas = FigureCanvasTkAgg(figure, master=parent)
        self.preview_canvas.draw()
        widget = self.preview_canvas.get_tk_widget()
        redraw_after_id = {"value": None}

        def resize_preview(event: Any) -> None:
            if event.width < 80 or event.height < 80:
                return
            if redraw_after_id["value"] is not None:
                try:
                    widget.after_cancel(redraw_after_id["value"])
                except Exception:
                    pass

            def redraw() -> None:
                redraw_after_id["value"] = None
                if self.preview_canvas is None:
                    return
                canvas_widget = self.preview_canvas.get_tk_widget()
                if canvas_widget.winfo_width() < 80 or canvas_widget.winfo_height() < 80:
                    return
                try:
                    self._fit_preview_figure_to_canvas(
                        figure,
                        canvas_widget.winfo_width(),
                        canvas_widget.winfo_height(),
                    )
                    self.preview_canvas.draw_idle()
                except Exception:
                    pass

            try:
                redraw_after_id["value"] = widget.after(80, redraw)
            except Exception:
                pass

        widget.bind("<Configure>", resize_preview)
        widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=4, pady=4)
        try:
            widget.after(120, lambda: (
                    self.preview_canvas is not None
                    and self._fit_preview_figure_to_canvas(figure, widget.winfo_width(), widget.winfo_height()) is None
                    and self.preview_canvas.draw_idle()
            ))
        except Exception:
            pass

    def _selected_display_mode(self) -> str:
        return self.result_case_labels.get(str(self.result_case_choice.get()), "static")

    def _selected_component(self) -> str:
        return self.component_labels.get(str(self.component_choice.get()), "von_mises_pa")

    def _set_display_modes(self, result: RuntimeFEMRunResult) -> None:
        has_plastic = bool((result.visualization or {}).get("plastic_strain"))
        uses_nonlinear_material = _summary_uses_nonlinear_material(result.summary)
        prestress_summary = (result.summary or {}).get("prestress_summary", {}) or {}
        is_collision_result = str(prestress_summary.get("runtime_solver", "") or "") == "sphere collision transient"
        labels = {"Static displacement/stress": "static"}
        for mode in _buckling_mode_shapes(result):
            mode_number = int(mode.get("mode_number", 0))
            load_factor = _safe_float(mode.get("load_factor"))
            label = "Mode " + str(mode_number) + "  LF " + str(round(load_factor, 4))
            labels[label] = "mode:" + str(mode_number)
        time_domain = (result.visualization or {}).get("time_domain", {}) or {}
        snapshots = tuple(time_domain.get("snapshots") or ())
        if snapshots:
            labels["Time history graph"] = "time_history"
        for index, snapshot in enumerate(snapshots):
            time_value = _safe_float((snapshot or {}).get("time_s"), 0.0)
            labels["Time t=" + f"{time_value:.6g}" + " s"] = "time:" + str(index)
        self.result_case_labels = labels
        self.result_case_choice.set("Static displacement/stress")
        if self.result_case_selector is not None:
            self.result_case_selector.configure(values=tuple(labels))

        component_labels = {
            "Stress von Mises": "von_mises_pa",
            "Displacement Magnitude": "disp_mag",
            "Displacement X": "disp_x",
            "Displacement Y": "disp_y",
            "Displacement Z": "disp_z",
            "Stress X (membrane)": "stress_x_membrane_pa",
            "Stress Y (membrane)": "stress_y_membrane_pa",
            "Stress XY (membrane)": "stress_xy_membrane_pa",
            "Strain X (membrane)": "strain_x_membrane",
            "Strain Y (membrane)": "strain_y_membrane",
            "Strain XY (membrane)": "strain_xy_membrane",
        }
        if has_plastic or (uses_nonlinear_material and not is_collision_result):
            component_labels["Equivalent Plastic Strain"] = "plastic_strain"
        damage_summary = (result.visualization or {}).get("impact_damage_summary", {}) or {}
        if bool(damage_summary.get("enabled", False)) or is_collision_result:
            component_labels["Impact Damage"] = "impact_damage"
            component_labels["Impact Damage Utilization"] = "impact_damage_utilization"
            component_labels["Impact Damage Stiffness Scale"] = "impact_damage_scale"
        self.component_labels = component_labels
        if self.component_choice.get() not in component_labels:
            self.component_choice.set("Stress von Mises")
        if self.component_selector is not None:
            self.component_selector.configure(values=tuple(component_labels.keys()))
        sync_time_slider = getattr(self, "_sync_time_slider", None)
        if callable(sync_time_slider):
            sync_time_slider()

    def _update_nullspace_status(self) -> None:
        """Update the small status label on the Boundary Conditions tab showing whether
        the last run used nullspace projection and how many rigid-body modes remain.
        """
        text = "Last run nullspace: unknown"
        try:
            result = getattr(self, "current_result", None)
            if result is None:
                self.last_run_nullspace_text.set(text)
                return
            prestress = (result.summary or {}).get("prestress_summary", {}) or {}
            proj = _safe_float(prestress.get("nullspace_projection"), 0.0)
            rank = _safe_int(prestress.get("nullspace_rank"), 0)
            if proj > 0.0:
                text = f"Last run nullspace: used, remaining modes: {rank}"
            else:
                text = "Last run nullspace: not used"
        except Exception:
            text = "Last run nullspace: unknown"
        try:
            self.last_run_nullspace_text.set(text)
        except Exception:
            pass

    def _time_result_labels(self) -> list[str]:
        return [label for label, mode in self.result_case_labels.items() if str(mode).startswith("time:")]

    def _time_result_index(self) -> int:
        labels = self._time_result_labels()
        current = str(self.result_case_choice.get())
        return labels.index(current) if current in labels else 0

    def _set_time_result_index(self, index: int, *, stop_animation: bool = True) -> None:
        labels = self._time_result_labels()
        if not labels:
            return
        if stop_animation:
            self._stop_animation()
        index = int(index) % len(labels)
        self.result_case_choice.set(labels[index])
        self._sync_time_slider(index=index)
        self._sync_color_limit_controls(force=True)
        self._refresh_figure(preserve_view=True)

    def _sync_time_slider(self, index: int | None = None) -> None:
        labels = self._time_result_labels()
        count = len(labels)
        if index is None:
            index = self._time_result_index() if count else 0
        index = min(max(int(index), 0), max(count - 1, 0))
        self._time_slider_syncing = True
        try:
            if self.time_step_slider is not None:
                self.time_step_slider.configure(from_=0.0, to=float(max(count - 1, 0)))
                try:
                    self.time_step_slider.configure(state=tk.NORMAL if count else tk.DISABLED)
                except tk.TclError:
                    pass
            self.time_step_slider_value.set(float(index))
            if self.time_step_label is not None:
                if count:
                    self.time_step_label.configure(text="Time step " + str(index + 1) + "/" + str(count))
                else:
                    self.time_step_label.configure(text="Time step")
        finally:
            self._time_slider_syncing = False

    def _on_time_slider(self, value: Any) -> None:
        if self._time_slider_syncing:
            return
        labels = self._time_result_labels()
        if not labels:
            return
        index = int(round(_safe_float(value, 0.0)))
        index = min(max(index, 0), len(labels) - 1)
        self._set_time_result_index(index, stop_animation=True)

    def _step_time_result(self, direction: int) -> None:
        labels = self._time_result_labels()
        if not labels:
            self._write_status("No saved time-domain result steps are available.", keep_run_results=True)
            return
        self._set_time_result_index(self._time_result_index() + int(direction), stop_animation=True)

    def _previous_time_step(self) -> None:
        self._step_time_result(-1)

    def _next_time_step(self) -> None:
        self._step_time_result(1)

    def _play_animation(self, *, start_index: int | None = None) -> None:
        labels = self._time_result_labels()
        if not labels:
            self._write_status("No saved time-domain result steps are available for animation.", keep_run_results=True)
            return

        current = str(self.result_case_choice.get())
        if start_index is None:
            start_index = labels.index(current) if current in labels else 0
        start_index = int(start_index) % len(labels)
        self._stop_animation()

        if bool(self.animation_fast_mode.get()) and self.result_canvas is not None:
            self.use_interactive_3d.set(True)
            self._write_status(f"Pre-calculating {len(labels)} animation frames for fast playback...")
            self.window.update_idletasks()

            self.result_canvas.begin_animation_cache()
            frame_indices = [
                (start_index + offset) % len(labels)
                for offset in range(len(labels))
            ]
            for index in frame_indices:
                label = labels[index]
                self.result_case_choice.set(label)
                self._sync_time_slider(index=index)

                # Suppress the automatic full refresh during capture by temporarily disabling _animation_running
                self._animation_running = False
                self._refresh_figure(preserve_view=True)
                self.result_canvas.capture_animation_frame()

            self._write_status(f"Captured {len(labels)} frames. Playing at high speed.", keep_run_results=True)

            speed = max(_tk_var_float(self.animation_speed_multiplier, 1.0), 0.05)
            interval = max(int(round(max(_tk_var_int(self.animation_interval_ms, 80), 20) / speed)), 5)
            fps = 1000 // interval
            self._animation_running = True
            self._animation_cache_origin = start_index
            self._animation_index = (start_index + 1) % len(labels)
            detail = self._animation_playback_detail()
            try:
                self.result_canvas.play_animation(fps=fps, fast=detail)
            except TypeError:
                # Older ANYtk3D without the playback-detail argument.
                self.result_canvas.play_animation(fps=fps)
            self.result_case_choice.set(labels[start_index])
            self._sync_time_slider(index=start_index)
            return

        self._animation_cache_origin = 0
        self._animation_index = start_index
        self._animation_running = True
        self._advance_animation_frame()

    def _stop_animation(self) -> None:
        self._animation_running = False
        if self._animation_after_id is not None:
            try:
                self.window.after_cancel(self._animation_after_id)
            except Exception:
                pass
            self._animation_after_id = None
        if self.result_canvas is not None:
            stop_anim = getattr(self.result_canvas, "stop_animation", None)
            if callable(stop_anim):
                stop_anim()

    def _advance_animation_frame(self) -> None:
        if not self._animation_running:
            return
        labels = self._time_result_labels()
        if not labels:
            self._stop_animation()
            return
        self.result_case_choice.set(labels[self._animation_index % len(labels)])
        self._sync_time_slider(index=self._animation_index % len(labels))
        self._animation_index = (self._animation_index + 1) % len(labels)
        self._sync_color_limit_controls(force=True)
        self._refresh_figure(preserve_view=True)
        speed = max(_tk_var_float(self.animation_speed_multiplier, 1.0), 0.05)
        interval = max(int(round(max(_tk_var_int(self.animation_interval_ms, 80), 20) / speed)), 5)
        self._animation_after_id = self.window.after(interval, self._advance_animation_frame)

    def _get_shell_normal(self, p: np.ndarray, is_cylinder: bool) -> np.ndarray:
        if is_cylinder:
            r = np.array([p[0], p[1], 0.0], dtype=float)
            norm_r = np.linalg.norm(r)
            if norm_r > 1.0e-9:
                return r / norm_r
            return np.array([1.0, 0.0, 0.0], dtype=float)
        else:
            return np.array([0.0, 0.0, 1.0], dtype=float)

    @staticmethod
    def _add_runtime_arrow(
            canvas: Tkinter3DCanvas,
            start: Point3D,
            end: Point3D,
            color: str,
            width: int = 3,
    ) -> None:
        direction = (end - start).normalized()
        if direction.length() <= 1.0e-12:
            return
        length = (end - start).length()
        head_length = max(length * 0.22, 1.0e-5)
        tangent = direction.cross(Point3D(0.0, 0.0, 1.0))
        if tangent.length() <= 1.0e-9:
            tangent = direction.cross(Point3D(0.0, 1.0, 0.0))
        tangent = tangent.normalized() * (0.45 * head_length)
        base = end - direction * head_length
        canvas.add_line(start, end, color=color, width=width, draw_overlay=True)
        canvas.add_line(end, base + tangent, color=color, width=max(1, width - 1), draw_overlay=True)
        canvas.add_line(end, base - tangent, color=color, width=max(1, width - 1), draw_overlay=True)

    def _draw_pressure_side_indicators(
            self,
            canvas: Tkinter3DCanvas,
            geometry: dict[str, Any],
    ) -> None:
        side_var = getattr(self, "pressure_direction", None)
        side_value = side_var.get() if side_var is not None and hasattr(side_var, "get") else "front"
        side = _normalise_pressure_side(side_value)
        surface_sign = _pressure_surface_sign(side)
        active_color = "#dc2626"
        front_color = "#0891b2"
        back_color = "#a16207"

        if self.snapshot.is_cylinder:
            radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-6)
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
            arrow_length = max(radius * 0.22, length * 0.025, 0.02)
            z_mid = 0.5 * length
            for angle in (math.radians(25.0), math.radians(145.0), math.radians(265.0)):
                radial = Point3D(math.cos(angle), math.sin(angle), 0.0)
                surface = radial * (radius + surface_sign * arrow_length * 0.08) + Point3D(0.0, 0.0, z_mid)
                start = radial * (radius + surface_sign * arrow_length) + Point3D(0.0, 0.0, z_mid)
                self._add_runtime_arrow(canvas, start, surface, active_color)

            label_angle = math.radians(55.0)
            radial = Point3D(math.cos(label_angle), math.sin(label_angle), 0.0)
            canvas.add_text(
                radial * (radius + arrow_length * 1.35) + Point3D(0.0, 0.0, 0.75 * length),
                "Front",
                color=front_color,
                draw_overlay=True,
            )
            canvas.add_text(
                radial * max(radius - arrow_length * 1.35, radius * 0.35) + Point3D(0.0, 0.0, 0.25 * length),
                "Back",
                color=back_color,
                draw_overlay=True,
            )
            return

        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-6)
        reference = max(length, width, 1.0)
        side_offset = reference * 0.12
        label_offset = reference * 0.18
        x0 = 0.08 * length
        y0 = 0.08 * width
        canvas.add_line(
            Point3D(x0, y0, 0.0),
            Point3D(x0, y0, label_offset),
            color=front_color,
            width=3,
            draw_overlay=True,
        )
        canvas.add_line(
            Point3D(x0 + 0.05 * length, y0, 0.0),
            Point3D(x0 + 0.05 * length, y0, -label_offset),
            color=back_color,
            width=3,
            draw_overlay=True,
        )
        canvas.add_text(Point3D(x0, y0, label_offset * 1.08), "Front", color=front_color, draw_overlay=True)
        canvas.add_text(
            Point3D(x0 + 0.05 * length, y0, -label_offset * 1.08),
            "Back",
            color=back_color,
            draw_overlay=True,
        )

        arrow_z = surface_sign * side_offset
        target_z = surface_sign * side_offset * 0.08
        for fx in (0.28, 0.50, 0.72):
            for fy in (0.35, 0.65):
                self._add_runtime_arrow(
                    canvas,
                    Point3D(length * fx, width * fy, arrow_z),
                    Point3D(length * fx, width * fy, target_z),
                    active_color,
                )

    def _populate_canvas_with_geometry(self, canvas: Tkinter3DCanvas, fit_view: bool = True) -> None:
        geometry = _popup_geometry_summary(self)
        show_plate_var = getattr(self, "show_plate_vis", None)
        show_plate = show_plate_var.get() if show_plate_var is not None else True
        show_stiffeners_var = getattr(self, "show_stiffener_vis", None)
        show_stiffeners = show_stiffeners_var.get() if show_stiffeners_var is not None else True
        show_girders_var = getattr(self, "show_girder_vis", None)
        show_girders = show_girders_var.get() if show_girders_var is not None else True
        plate_alpha_var = getattr(self, "plate_alpha_vis", None)
        member_alpha_var = getattr(self, "member_alpha_vis", None)
        colormap_var = getattr(self, "colormap_vis", None)
        plate_alpha = _crisp_canvas_alpha(plate_alpha_var.get() if plate_alpha_var is not None else 1.0, 1.0)
        member_alpha = _crisp_canvas_alpha(member_alpha_var.get() if member_alpha_var is not None else 1.0, 1.0)
        # Alpha goes straight to the canvas: ANYtk3D resolves an opacity into
        # a 16-step dither with separate front/back patterns, so the alpha
        # entries are proportional across their whole range and a surface
        # behind a transparent one still shows through.
        plate_front_color = _tk_color_value(
            getattr(getattr(self, "plate_front_color_vis", None), "get", lambda: "#d1d5db")(),
            "#d1d5db",
        )
        plate_back_color = _tk_color_value(
            getattr(getattr(self, "plate_back_color_vis", None), "get", lambda: "#8b5e3c")(),
            "#8b5e3c",
        )
        _configure_tk_canvas_colormap(str(colormap_var.get() if colormap_var is not None else "jet"))

        if hasattr(self, "imported_fem_model") and self.imported_fem_model is not None:
            get_node = self.imported_fem_model.mesh.get_node
            imported_shells = []
            for element in self.imported_fem_model.mesh.elements.values():
                if element.__class__.__name__ == "ShellElement":
                    if not show_plate: continue
                    nodes = [get_node(int(nid)) for nid in element.node_ids]
                    if all(n is not None for n in nodes):
                        imported_shells.append([n.coords() for n in nodes])
                elif element.__class__.__name__ == "BeamElement":
                    if not show_stiffeners: continue
                    nodes = [get_node(int(nid)) for nid in element.node_ids]
                    if len(nodes) >= 2 and all(n is not None for n in nodes):
                        pts = [Point3D(*n.coords()) for n in nodes]
                        for i in range(len(pts) - 1):
                            canvas.add_line(pts[i], pts[i + 1], color="blue", width=2)
            if imported_shells:
                canvas.add_faces(
                    imported_shells,
                    colors=plate_front_color,
                    back_colors=[plate_back_color] * len(imported_shells),
                    outline="gray",
                    opacity=plate_alpha,
                )
            if fit_view:
                canvas.fit_to_scene()
            return

        if self.snapshot.is_cylinder:
            if geometry.get("is_cone"):
                radius = max(_safe_float(geometry.get("cone_r1_m"), 1.0), 1.0e-6)
                radius_top = max(_safe_float(geometry.get("cone_r2_m"), 1.0), 1.0e-6)
            else:
                radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-6)
                radius_top = radius
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
            if show_plate and plate_alpha > 0.0:
                canvas.add_cylinder(
                    radius=radius,
                    radius_top=radius_top,
                    height=length,
                    center=Point3D(0.0, 0.0, 0.5 * length),
                    color=plate_front_color,
                    back_color=plate_back_color,
                    outline="",
                    segments=32,
                    height_segments=12,
                    capped=False,
                    opacity=plate_alpha,
                    show_backfaces=bool(plate_back_color) or plate_alpha < 0.94,
                    show_thickness_legend=False
                )
            if show_stiffeners and member_alpha > 0.0 and geometry.get("has_stiffener"):
                stf_spacing = _safe_float(geometry.get("stiffener_spacing_m"))
                if stf_spacing > 0.0:
                    num_longs = max(1, representation_geometry.closed_loop_member_count(
                        2.0 * math.pi * radius,
                        stf_spacing,
                    ))
                    stf_sec = geometry.get("stiffener_section") or {}
                    hw = _safe_float(stf_sec.get("web_height") or stf_sec.get("web_h") or 0.1)
                    tw = _safe_float(stf_sec.get("web_thickness") or stf_sec.get("web_t") or 0.01)
                    b = _safe_float(stf_sec.get("flange_width") or stf_sec.get("flange_w") or 0.0)
                    tf = _safe_float(stf_sec.get("flange_thickness") or stf_sec.get("flange_t") or 0.0)
                    for i in range(num_longs):
                        angle = 2.0 * math.pi * i / num_longs
                        canvas.add_longitudinal_stiffener(
                            radius=radius,
                            radius_top=radius_top,
                            height=length,
                            angle=angle,
                            web_height=hw,
                            web_thickness=tw,
                            flange_width=b,
                            flange_thickness=tf,
                            color=_blend_hex_color("#a0a0ff", member_alpha),
                            outline=_blend_hex_color("#404080", member_alpha),
                            segments=4,
                            height_segments=8,
                            inside=True,
                            z_offset=0.5 * length,
                        )
            if show_girders and member_alpha > 0.0 and geometry.get("has_girder"):
                gir_spacing = _safe_float(geometry.get("girder_spacing_m"))
                gir_sec = geometry.get("girder_section") or {}
                ghw = _safe_float(gir_sec.get("web_height") or gir_sec.get("web_h") or 0.12)
                gtw = _safe_float(gir_sec.get("web_thickness") or gir_sec.get("web_t") or 0.02)
                gb = _safe_float(gir_sec.get("flange_width") or gir_sec.get("flange_w") or 0.08)
                gtf = _safe_float(gir_sec.get("flange_thickness") or gir_sec.get("flange_t") or 0.015)
                if gir_spacing > 0.0:
                    for station in representation_geometry.centered_member_positions(
                            length,
                            gir_spacing,
                            fallback_midpoint=True,
                            include_ends=True,
                    ):
                        z_pos = station
                        t = z_pos / length if length > 0 else 0.0
                        r_z = radius + t * (radius_top - radius)
                        canvas.add_ring_stiffener(
                            radius=r_z,
                            z_position=z_pos,
                            web_height=ghw,
                            web_thickness=gtw,
                            flange_width=gb,
                            flange_thickness=gtf,
                            color=_blend_hex_color("#ffa0a0", member_alpha),
                            outline=_blend_hex_color("#804040", member_alpha),
                            segments=32,
                            inside=True,
                        )
        else:
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
            width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-6)
            if show_plate and plate_alpha > 0.0:
                canvas.add_rectangular_plate(
                    x_start=0.0, x_end=length,
                    y_start=0.0, y_end=width,
                    z=0.0,
                    color=plate_front_color,
                    back_color=plate_back_color,
                    outline="#64748b",
                    layer=5,
                    opacity=plate_alpha
                )
            if show_stiffeners and member_alpha > 0.0 and geometry.get("has_stiffener"):
                spacing = _safe_float(geometry.get("stiffener_spacing_m"))
                stf_sec = geometry.get("stiffener_section") or {}
                hw = _safe_float(stf_sec.get("web_height") or stf_sec.get("web_h") or 0.1)
                b = _safe_float(stf_sec.get("flange_width") or stf_sec.get("flange_w") or 0.0)
                if spacing > 0.0:
                    for y_pos in representation_geometry.centered_member_positions(
                            width,
                            spacing,
                            fallback_midpoint=True,
                            include_ends=True,
                    ):
                        canvas.add_flat_stiffener(
                            x_start=0.0, x_end=length,
                            y=y_pos,
                            z_base=0.0,
                            hw=hw,
                            b=b,
                            color="#94a3b8",
                            outline="#1f2937",
                            opacity=member_alpha,
                        )
            if show_girders and member_alpha > 0.0 and geometry.get("has_girder"):
                gir_sec = geometry.get("girder_section") or {}
                ghw = _safe_float(gir_sec.get("web_height") or gir_sec.get("web_h") or 0.15)
                gb = _safe_float(gir_sec.get("flange_width") or gir_sec.get("flange_w") or 0.08)
                spacing = _safe_float(geometry.get("girder_spacing_m"), 0.0)
                for x_mid in representation_geometry.centered_member_positions(
                        length,
                        spacing,
                        fallback_midpoint=True,
                        include_ends=True,
                ):
                    canvas.add_flat_girder(
                        x=x_mid,
                        y_start=0.0, y_end=width,
                        z_base=0.0,
                        ghw=ghw,
                        gb=gb,
                        color="#fca5a5",
                        outline="#991b1b",
                        opacity=member_alpha,
                    )
        if callable(getattr(canvas, "add_line", None)) and callable(getattr(canvas, "add_text", None)):
            self._draw_base_dimension_annotations(canvas, geometry)
            RuntimeFEMWindow._draw_pressure_side_indicators(self, canvas, geometry)
            self._draw_collision_sphere_overlay(canvas, self._collision_sphere_preview_visualization())
        if hasattr(self, "_custom_load_patches"):
            self._draw_custom_load_patch_outlines(canvas)
        if hasattr(self, "point_refinement_enabled"):
            self._draw_point_refinement_marker(canvas, geometry, draw_circle=True)
        if fit_view:
            canvas.after_idle(canvas.fit_to_scene)

    def _point_refinement_marker_xyz(self, geometry: dict[str, Any]) -> tuple[Point3D, float] | None:
        """World position and extent radius of the current point-refinement centre.

        Uses the live GUI values (not a rebuilt mesh) so the marker tracks the
        Point X/Y fields immediately after a pick.  Returns ``None`` when point
        refinement is off.  Cylinder mapping matches ``marker_xyz`` in
        ``fe_solver`` (arc -> angle, axial -> z).
        """
        try:
            if not bool(self.point_refinement_enabled.get()):
                return None
            point_x = float(self.point_refinement_x_m.get())
            point_y = float(self.point_refinement_y_m.get())
            extent = max(float(self.point_refinement_extent_m.get()), 0.0)
        except Exception:
            return None
        if self.snapshot.is_cylinder:
            radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-9)
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
            z = min(max(point_x, 0.0), length)
            theta = point_y / radius
            return Point3D(radius * math.cos(theta), radius * math.sin(theta), z), extent
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
        width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-9)
        x = min(max(point_x, 0.0), length)
        y = min(max(point_y, 0.0), width)
        return Point3D(x, y, 0.0), extent

    def _bind_point_refinement_z_sync(self) -> None:
        """Keep the world-space Point Z field consistent with Point X/Y.

        On a cylinder the axial parametric coordinate (Point X) IS the world
        z, so the two fields mirror each other and either can be edited.  On
        a flat panel the plate lies at z = 0, so Point Z is informational.
        A guard flag breaks the trace recursion; partially typed values raise
        in ``get()`` and are ignored until the entry parses.
        """

        def sync(source: str) -> None:
            if self._point_refinement_z_sync_active:
                return
            if not getattr(self.snapshot, "is_cylinder", False):
                return
            self._point_refinement_z_sync_active = True
            try:
                if source == "z":
                    self.point_refinement_x_m.set(float(self.point_refinement_z_m.get()))
                else:
                    self.point_refinement_z_m.set(float(self.point_refinement_x_m.get()))
            except Exception:
                pass
            finally:
                self._point_refinement_z_sync_active = False

        try:
            self.point_refinement_x_m.trace_add("write", lambda *_a: sync("x"))
            self.point_refinement_z_m.trace_add("write", lambda *_a: sync("z"))
        except Exception:
            pass

    def _sync_point_refinement_z_from_marker(self) -> None:
        """Fill Point Z from the current refinement centre's world position."""
        try:
            marker = self._point_refinement_marker_xyz(_popup_geometry_summary(self))
        except Exception:
            marker = None
        if marker is None:
            return
        centre, _extent = marker
        self._point_refinement_z_sync_active = True
        try:
            self.point_refinement_z_m.set(float(centre.z))
        except Exception:
            pass
        finally:
            self._point_refinement_z_sync_active = False

    def _point_refinement_report(self, point_x: float, point_y: float) -> str:
        """Status text for a picked point: parametric input plus 3D world XYZ.

        For a cylinder the input pair is (axial, arc-length); the world triple
        adds the Cartesian x/y and the axial z so the picked height is explicit.
        For a flat panel the plate sits at z = 0.
        """
        base = f"Point mesh refinement set at ({point_x:.3f}, {point_y:.3f}) m"
        try:
            marker = self._point_refinement_marker_xyz(_popup_geometry_summary(self))
        except Exception:
            marker = None
        if marker is None:
            return base + "."
        centre, _extent = marker
        return base + f"; 3D point ({centre.x:.3f}, {centre.y:.3f}, {centre.z:.3f}) m."

    def _draw_point_refinement_marker(
            self,
            canvas: "Tkinter3DCanvas",
            geometry: dict[str, Any],
            draw_circle: bool = True,
    ) -> None:
        """Bold crosshair (+ optional extent circle) at the point-refinement centre.

        Drawn as an overlay from the live Point X/Y/extent inputs so the picked
        location is visible in the geometry view and mesh preview without
        rebuilding the mesh.
        """
        if not (callable(getattr(canvas, "add_line", None))):
            return
        marker = self._point_refinement_marker_xyz(geometry)
        if marker is None:
            return
        centre, extent = marker
        color = "#7c3aed"
        if self.snapshot.is_cylinder:
            radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-9)
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
            star = max(extent * 0.6, min(radius, length) * 0.03)
        else:
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
            width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-9)
            star = max(extent * 0.6, min(length, width) * 0.03)
        # Three-axis star: view-independent so the centre reads from any angle.
        for axis in ((star, 0.0, 0.0), (0.0, star, 0.0), (0.0, 0.0, star)):
            a = Point3D(centre.x - axis[0], centre.y - axis[1], centre.z - axis[2])
            b = Point3D(centre.x + axis[0], centre.y + axis[1], centre.z + axis[2])
            canvas.add_line(a, b, color=color, width=3, draw_overlay=True)
        if draw_circle and extent > 0.0:
            self._draw_point_refinement_circle(canvas, geometry, centre, extent, color)

    def _draw_point_refinement_circle(
            self,
            canvas: "Tkinter3DCanvas",
            geometry: dict[str, Any],
            centre: Point3D,
            extent: float,
            color: str,
    ) -> None:
        angles = np.linspace(0.0, 2.0 * math.pi, 48)
        if self.snapshot.is_cylinder:
            radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-9)
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
            offset = max(radius * 0.006, 2.0e-4)
            center_z = float(centre.z)
            center_arc = math.atan2(float(centre.y), float(centre.x)) * radius
            pts = []
            for angle in angles:
                z = min(max(center_z + extent * math.cos(angle), 0.0), length)
                theta = (center_arc + extent * math.sin(angle)) / radius
                draw_radius = radius + offset
                pts.append(Point3D(draw_radius * math.cos(theta), draw_radius * math.sin(theta), z))
        else:
            z = float(centre.z) + max(extent * 0.02, 1.0e-3)
            pts = [Point3D(float(centre.x) + extent * math.cos(a), float(centre.y) + extent * math.sin(a), z)
                   for a in angles]
        pts.append(pts[0])
        for start, end in zip(pts, pts[1:]):
            canvas.add_line(start, end, color=color, width=2, draw_overlay=True)

    def _draw_base_dimension_annotations(self, canvas: Tkinter3DCanvas, geometry: dict[str, Any]) -> None:
        color = "#6b7280"
        if self.snapshot.is_cylinder:
            if geometry.get("is_cone"):
                radius = max(_safe_float(geometry.get("cone_r1_m"), 1.0), 1.0e-6)
                radius_top = max(_safe_float(geometry.get("cone_r2_m"), 1.0), 1.0e-6)
            else:
                radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-6)
                radius_top = radius
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
            y = -1.18 * radius
            z = -0.18 * radius
            canvas.add_line(Point3D(-radius, y, z), Point3D(radius, y, z), color=color, width=1, layer=2,
                            draw_overlay=False)
            canvas.add_text(Point3D(0.0, y, z), "D1 " + _format_dimension(2.0 * radius), color=color,
                            font=("Segoe UI", 8, "normal"), layer=42, draw_overlay=False)

            y_top = -1.18 * radius_top
            z_top = length + 0.18 * radius_top
            canvas.add_line(Point3D(-radius_top, y_top, z_top), Point3D(radius_top, y_top, z_top), color=color, width=1, layer=2,
                            draw_overlay=False)
            canvas.add_text(Point3D(0.0, y_top, z_top), "D2 " + _format_dimension(2.0 * radius_top), color=color,
                            font=("Segoe UI", 8, "normal"), layer=42, draw_overlay=False)

            x = 1.18 * max(radius, radius_top)
            y2 = 1.18 * max(radius, radius_top)
            canvas.add_line(Point3D(x, y2, 0.0), Point3D(x, y2, length), color=color, width=1, layer=2,
                            draw_overlay=False)
            canvas.add_text(Point3D(x, y2, 0.5 * length), "L " + _format_dimension(length), color=color,
                            font=("Segoe UI", 8, "normal"), layer=42, draw_overlay=False)
            return
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-6)
        width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-6)
        offset = 0.06 * max(length, width, 1.0)
        canvas.add_line(Point3D(0.0, -offset, 0.0), Point3D(length, -offset, 0.0), color=color, width=1, layer=2,
                        draw_overlay=False)
        canvas.add_text(Point3D(0.5 * length, -offset, 0.0), _format_dimension(length), color=color,
                        font=("Segoe UI", 8, "normal"), layer=42, draw_overlay=False)
        canvas.add_line(Point3D(-offset, 0.0, 0.0), Point3D(-offset, width, 0.0), color=color, width=1, layer=2,
                        draw_overlay=False)
        canvas.add_text(Point3D(-offset, 0.5 * width, 0.0), _format_dimension(width), color=color,
                        font=("Segoe UI", 8, "normal"), layer=42, draw_overlay=False)
        height = _base_geometry_height_extent(geometry)
        if height > 0.0:
            canvas.add_line(Point3D(length + offset, width + offset, 0.0),
                            Point3D(length + offset, width + offset, height), color=color, width=1, layer=2,
                            draw_overlay=False)
            canvas.add_text(Point3D(length + offset, width + offset, 0.5 * height), _format_dimension(height),
                            color=color, font=("Segoe UI", 8, "normal"), layer=42, draw_overlay=False)

    def _collision_sphere_preview_visualization(self) -> dict[str, Any]:
        if not bool(self.collision_enabled.get()):
            return {}
        return {
            "rigid_sphere": {
                "position": (
                    _tk_var_float(self.collision_start_x_m, 0.0),
                    _tk_var_float(self.collision_start_y_m, 0.0),
                    _tk_var_float(self.collision_start_z_m, 1.0),
                ),
                "radius": max(_tk_var_float(self.collision_radius_m, 0.25), 1.0e-9),
                "visible": True,
            }
        }

    def _populate_canvas_with_results(self, canvas: Tkinter3DCanvas, fit_view: bool = True) -> None:
        result = self.current_result
        geometry = result.summary
        display_mode = self._selected_display_mode()
        deformation_scale = max(_tk_var_float(self.deformation_scale, 0.0), 0.0)
        component = self._selected_component()
        plate_alpha = _crisp_canvas_alpha(self.plate_alpha_vis.get(), 1.0)
        member_alpha = _crisp_canvas_alpha(self.member_alpha_vis.get(), 1.0)
        # Alpha goes straight to the canvas: ANYtk3D resolves an opacity into
        # a 16-step dither with separate front/back patterns, so the alpha
        # entries are proportional across their whole range and a surface
        # behind a transparent one still shows through.
        _configure_tk_canvas_colormap(str(self.colormap_vis.get()))
        visualization_payload = ((self.current_result.visualization if self.current_result is not None else {}) or {})
        has_explicit_shell_surfaces = bool(
            visualization_payload.get("shell_surfaces") or visualization_payload.get("skin_shell_surfaces")
        )
        if self.snapshot.is_cylinder and plate_alpha >= 0.94 and not has_explicit_shell_surfaces:
            set_occluder = getattr(canvas, "set_opaque_cylinder_occluder", None)
            if callable(set_occluder):
                radius = max(_safe_float(geometry.get("cone_r1_m") if geometry.get("is_cone") else geometry.get("radius_m"), 1.0), 1.0e-9)
                set_occluder(
                    radius=radius,
                    height=max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9),
                    center=Point3D(0.0, 0.0, 0.5 * max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)),
                )

        visualization, title, is_mode = _selected_visualization(result, display_mode, component)

        show_stiffeners_for_range = self.show_stiffener_vis.get() if getattr(self, "show_stiffener_vis",
                                                                             None) is not None else True
        show_girders_for_range = self.show_girder_vis.get() if getattr(self, "show_girder_vis",
                                                                       None) is not None else True
        all_vals, color_grid, colorbar_label = _visualization_color_values(
            visualization,
            component,
            is_mode,
            geometry,
            show_stiffeners_for_range,
            show_girders_for_range,
            include_members=member_alpha > 0.0,
        )
        vmin, vmax = _resolved_color_limits(all_vals, self._manual_color_limits())

        scale = _displacement_plot_scale(geometry, result, visualization, deformation_scale)

        if visualization.get("type") == "cylinder":
            axial = _plot_grid_values(visualization.get("axial_m"))
            theta = _plot_grid_values(visualization.get("theta_rad"))
            if geometry.get("is_cone"):
                base_radius = max(_safe_float(geometry.get("cone_r1_m"), 1.0), 1.0e-9)
                base_radius_top = max(_safe_float(geometry.get("cone_r2_m"), 1.0), 1.0e-9)
            else:
                base_radius = max(_safe_float(visualization.get("radius_m"), _safe_float(geometry.get("radius_m"), 1.0)), 1.0e-9)
                base_radius_top = base_radius

            cyl_len = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)

            def get_r(z_val):
                t = z_val / cyl_len if cyl_len > 0 else 0.0
                return base_radius + t * (base_radius_top - base_radius)

            disps = visualization.get("displacements", {})
            dx_grid = _plot_grid_values(disps.get("disp_x", []))
            dy_grid = _plot_grid_values(disps.get("disp_y", []))
            dz_grid = _plot_grid_values(disps.get("disp_z", []))

            if not dx_grid or not dy_grid or not dz_grid:
                radial_displacement = _plot_grid_values(visualization.get("radial_displacement_m"))
                x = [
                    [(get_r(axial[row_index][col_index]) + radial_displacement[row_index][col_index] * scale) * math.cos(
                        theta[row_index][col_index])
                     for col_index in range(len(theta[row_index]))]
                    for row_index in range(len(theta))
                ]
                y = [
                    [(get_r(axial[row_index][col_index]) + radial_displacement[row_index][col_index] * scale) * math.sin(
                        theta[row_index][col_index])
                     for col_index in range(len(theta[row_index]))]
                    for row_index in range(len(theta))
                ]
                z = axial
            else:
                x = [
                    [(get_r(axial[row_index][col_index]) * math.cos(theta[row_index][col_index]) + dx_grid[row_index][col_index] * scale)
                     for col_index in range(len(theta[row_index]))]
                    for row_index in range(len(theta))
                ]
                y = [
                    [(get_r(axial[row_index][col_index]) * math.sin(theta[row_index][col_index]) + dy_grid[row_index][col_index] * scale)
                     for col_index in range(len(theta[row_index]))]
                    for row_index in range(len(theta))
                ]
                z = [
                    [(axial[row_index][col_index] + dz_grid[row_index][col_index] * scale)
                     for col_index in range(len(axial[row_index]))]
                    for row_index in range(len(axial))
                ]
        else:
            x = _plot_grid_values(visualization.get("x_m"))
            y = _plot_grid_values(visualization.get("y_m"))
            w = _plot_grid_values(visualization.get("w_m"))
            z = [[value * scale for value in row] for row in w]

        show_plate_var = getattr(self, "show_plate_vis", None)
        show_plate = show_plate_var.get() if show_plate_var is not None else True
        if show_plate and plate_alpha > 0.0:
            # Result fields are handed to the canvas as one batch: a colour
            # per element, but a single object with one flat vertex array.
            # Adding them one polygon at a time costs a dict and a Python
            # centroid/normal per element, which dominates on real meshes.
            skin_shell_surfaces = tuple(visualization.get("skin_shell_surfaces") or ())
            if skin_shell_surfaces:
                polygons = []
                colors = []
                for surface in skin_shell_surfaces:
                    polygon = _shell_surface_points(surface, scale)
                    if len(polygon) < 3:
                        continue
                    value = _shell_surface_component_value(surface, component, is_mode=is_mode)
                    polygons.append(polygon)
                    colors.append(_interpolate_thickness_color(value, vmin, vmax))
                if polygons:
                    canvas.add_faces(
                        polygons,
                        colors=colors,
                        outline="#111827",
                        width=1,
                        layer=5,
                        opacity=plate_alpha,
                    )
            else:
                R = len(x)
                C = len(x[0]) if R > 0 else 0
                polygons = []
                colors = []
                for i in range(R - 1):
                    for j in range(C - 1):
                        polygons.append((
                            (x[i][j], y[i][j], z[i][j]),
                            (x[i + 1][j], y[i + 1][j], z[i + 1][j]),
                            (x[i + 1][j + 1], y[i + 1][j + 1], z[i + 1][j + 1]),
                            (x[i][j + 1], y[i][j + 1], z[i][j + 1]),
                        ))
                        avg_val = 0.25 * (
                                color_grid[i][j] + color_grid[i + 1][j] + color_grid[i + 1][j + 1] + color_grid[i][
                            j + 1])
                        colors.append(_interpolate_thickness_color(avg_val, vmin, vmax))
                if polygons:
                    canvas.add_faces(
                        polygons,
                        colors=colors,
                        outline="#64748b",
                        layer=5,
                        opacity=plate_alpha,
                    )

        show_stiffeners_var = getattr(self, "show_stiffener_vis", None)
        show_stiffeners = show_stiffeners_var.get() if show_stiffeners_var is not None else True
        show_girders_var = getattr(self, "show_girder_vis", None)
        show_girders = show_girders_var.get() if show_girders_var is not None else True

        if member_alpha > 0.0:
            polygons = []
            colors = []
            for surface in visualization.get("shell_surfaces") or ():
                if not _shell_surface_role_visible(surface, show_stiffeners, show_girders):
                    continue
                polygon = _shell_surface_points(surface, scale)
                if len(polygon) < 3:
                    continue
                value = _shell_surface_component_value(surface, component, is_mode=is_mode)
                polygons.append(polygon)
                colors.append(_interpolate_thickness_color(value, vmin, vmax))
            if polygons:
                canvas.add_faces(
                    polygons,
                    colors=colors,
                    outline="#111827",
                    width=2,
                    layer=11,
                    opacity=member_alpha,
                )

        web_polygons = []
        web_colors = []
        flange_polygons = []
        flange_colors = []
        for line in visualization.get("member_lines") or ():
            role = str(line.get("role", "member")).lower()
            if role == "stiffener" and (not show_stiffeners or member_alpha <= 0.0):
                continue
            if role == "girder" and (not show_girders or member_alpha <= 0.0):
                continue

            points = list(line.get("points") or ())
            displaced = list(line.get("displaced_points") or ())
            if len(points) < 2 or len(displaced) < 2:
                continue

            pts = []
            for idx in range(2):
                base = np.asarray(points[idx], dtype=float)
                moved = np.asarray(displaced[idx], dtype=float)
                pts.append(base + (moved - base) * float(scale))

            pA = pts[0]
            pB = pts[1]
            vec_AB = pB - pA
            len_AB = np.linalg.norm(vec_AB)
            if len_AB < 1.0e-9:
                continue
            u = vec_AB / len_AB

            nA = self._get_shell_normal(pA, self.snapshot.is_cylinder)
            nB = self._get_shell_normal(pB, self.snapshot.is_cylinder)

            e = line.get("eccentricity", 0.0)
            if abs(e) > 1.0e-9:
                web_sign = np.sign(e)
            else:
                web_sign = -1.0 if self.snapshot.is_cylinder else 1.0

            wA = web_sign * nA
            wB = web_sign * nB

            hw = line.get("web_height", 0.1)
            b_f = line.get("flange_width", 0.0)

            s_stops = [0.0, 1.0]
            centroids = [0.5]

            for k in range(1):
                z_start = s_stops[k] * hw
                z_end = s_stops[k + 1] * hw

                pAk = pA + z_start * wA
                pAk1 = pA + z_end * wA
                pBk = pB + z_start * wB
                pBk1 = pB + z_end * wB

                web_polygons.append((pAk, pBk, pBk1, pAk1))
                val = _member_component_value(line, component, is_mode=is_mode, flange=False)
                web_colors.append(_interpolate_thickness_color(val, vmin, vmax))

            if b_f > 0.0:
                pA_top = pA + hw * wA
                pB_top = pB + hw * wB

                v_flange_A = np.cross(u, wA)
                v_flange_B = np.cross(u, wB)

                fA1 = pA_top - 0.5 * b_f * v_flange_A
                fA2 = pA_top + 0.5 * b_f * v_flange_A
                fB1 = pB_top - 0.5 * b_f * v_flange_B
                fB2 = pB_top + 0.5 * b_f * v_flange_B

                flange_polygons.append((fA1, fB1, fB2, fA2))
                val = _member_component_value(line, component, is_mode=is_mode, flange=True)
                flange_colors.append(_interpolate_thickness_color(val, vmin, vmax))

        # Member webs and flanges sit on their own layers, so they go over as
        # two batches rather than a polygon per member.
        for polygons, colors, layer in (
            (web_polygons, web_colors, 12),
            (flange_polygons, flange_colors, 13),
        ):
            if polygons:
                canvas.add_faces(
                    polygons,
                    colors=colors,
                    outline="#000000",
                    width=2,
                    layer=layer,
                    opacity=member_alpha,
                )

        self._draw_base_dimension_annotations(canvas, geometry)
        self._draw_collision_sphere_overlay(canvas, visualization, deformation_scale=scale)
        self._draw_selected_probe_overlay(canvas, visualization, component, is_mode, scale)

        canvas.set_thickness_legend(
            values=all_vals,
            unit="",
            title=colorbar_label,
            width=210,
            value_range=(vmin, vmax),
        )
        if fit_view:
            canvas.after_idle(canvas.fit_to_scene)

    def _draw_collision_sphere_overlay(
            self,
            canvas: Tkinter3DCanvas,
            visualization: dict[str, Any],
            deformation_scale: float = 1.0,
    ) -> None:
        if not bool(self.show_collision_sphere_vis.get()):
            return
        sphere = visualization.get("rigid_sphere") or {}
        if (
                str(getattr(self.current_result, "status", "") or "") == "running"
                and isinstance(getattr(self, "_live_collision_sphere_visualization", None), dict)
                and self._live_collision_sphere_visualization
        ):
            sphere = self._live_collision_sphere_visualization.get("rigid_sphere") or sphere
        if not isinstance(sphere, dict) or not bool(sphere.get("visible", True)):
            return
        try:
            center = _sphere_display_center(sphere, visualization, deformation_scale)
            radius = max(_safe_float(sphere.get("radius"), 0.0), 0.0)
        except Exception:
            return
        if radius <= 0.0:
            return
        segments = 32
        rings = 18
        base_color = "#9ca3af"
        light_color = _blend_hex_color(base_color, 0.30)
        outline_color = _blend_hex_color("#4b5563", 0.42)
        sphere_opacity = 0.45
        light = np.asarray((-0.35, -0.55, 0.76), dtype=float)
        light /= max(float(np.linalg.norm(light)), 1.0e-12)

        def sphere_point(latitude: float, longitude: float) -> Point3D:
            cos_lat = math.cos(latitude)
            return Point3D(
                center[0] + radius * cos_lat * math.cos(longitude),
                center[1] + radius * cos_lat * math.sin(longitude),
                center[2] + radius * math.sin(latitude),
            )

        sphere_polygons = []
        sphere_colors = []
        for ring in range(rings):
            lat0 = -0.5 * math.pi + math.pi * ring / rings
            lat1 = -0.5 * math.pi + math.pi * (ring + 1) / rings
            for segment in range(segments):
                lon0 = 2.0 * math.pi * segment / segments
                lon1 = 2.0 * math.pi * (segment + 1) / segments
                if ring == 0:
                    # Wind the south-cap triangles so the face normal points
                    # outward (matching the body quads); the previous order gave
                    # inward normals, misclassifying the cap as back-facing.
                    vertices = (
                        sphere_point(lat0, lon0),
                        sphere_point(lat1, lon1),
                        sphere_point(lat1, lon0),
                    )
                elif ring == rings - 1:
                    vertices = (
                        sphere_point(lat0, lon0),
                        sphere_point(lat0, lon1),
                        sphere_point(lat1, lon1),
                    )
                else:
                    vertices = (
                        sphere_point(lat0, lon0),
                        sphere_point(lat0, lon1),
                        sphere_point(lat1, lon1),
                        sphere_point(lat1, lon0),
                    )
                centroid = np.asarray(
                    (
                        sum(point.x for point in vertices) / len(vertices),
                        sum(point.y for point in vertices) / len(vertices),
                        sum(point.z for point in vertices) / len(vertices),
                    ),
                    dtype=float,
                )
                normal = centroid - center
                normal /= max(float(np.linalg.norm(normal)), 1.0e-12)
                shade = 0.44 + 0.38 * max(float(np.dot(normal, light)), 0.0)
                sphere_polygons.append(vertices)
                sphere_colors.append(_blend_hex_color(base_color, shade))

        if sphere_polygons:
            canvas.add_faces(
                sphere_polygons,
                colors=sphere_colors,
                back_colors=[light_color] * len(sphere_polygons),
                outline=outline_color,
                width=1,
                cull_backface=False,
                layer=39,
                opacity=sphere_opacity,
                tags="rigid_sphere",
                two_sided_shell=True,
            )

        marker = max(radius * 0.025, 1.0e-3)
        canvas.add_line(
            Point3D(center[0] - marker, center[1], center[2]),
            Point3D(center[0] + marker, center[1], center[2]),
            color="#4b5563",
            width=2,
            layer=41,
            draw_overlay=False,
        )

    def _update_result_text(self) -> None:
        if self.upper_result_text is None:
            return
        self.upper_result_text.config(state=tk.NORMAL)
        self.upper_result_text.delete("1.0", tk.END)

        if self.current_result is None:
            self.upper_result_text.insert(tk.END, "No solver results available yet. Run FEM to calculate results.")
            self.upper_result_text.config(state=tk.DISABLED)
            return

        result = self.current_result
        geometry = result.summary
        display_mode = self._selected_display_mode()

        lines = []
        if str(display_mode).startswith("mode:"):
            lines.extend([
                "--- BUCKLING MODES ANALYSIS ---",
                "Status: " + result.status.replace("_", " "),
                "Solver: " + str(geometry.get("solver", "")),
                "Max displacement [mm]: " + str(round(1000.0 * _safe_float(geometry.get("max_displacement_m")), 4)),
            ])
            for label, value in result.stress_percentiles:
                lines.append(label.upper() + " stress [MPa]: " + str(round(value / 1.0e6, 3)))
            lines.append("")
            lines.append("Mode\tLoad factor")
            lines.append("----\t-----------")

            active_mode_str = display_mode.split(":", 1)[1]
            active_idx = -1
            try:
                active_idx = int(active_mode_str)
            except ValueError:
                pass

            if result.buckling_factors:
                for idx, factor in enumerate(result.buckling_factors, start=1):
                    prefix = "--> " if idx == active_idx else "    "
                    lines.append(f"{prefix}{idx}\t{round(factor, 4)}")
            else:
                lines.append("No positive buckling modes found.")
        elif bool(geometry.get("collision_enabled")) or str(
                (geometry.get("prestress_summary") or {}).get("collision_status", "") or ""):
            prestress = geometry.get("prestress_summary") or {}
            lines.extend([
                "--- RIGID-SPHERE COLLISION TRANSIENT ---",
                "Status: " + result.status.replace("_", " "),
                "Solver: " + str(geometry.get("solver", "")),
                "Time mode: " + str(prestress.get("collision_time_mode", geometry.get("collision_time_mode", ""))),
                "Resolved dt / total [s]: "
                + str(round(_safe_float(prestress.get("collision_resolved_dt_s")), 9))
                + " / "
                + str(round(_safe_float(prestress.get("collision_resolved_total_time_s")), 6)),
                "Peak contact force [kN]: " + str(
                    round(_safe_float(prestress.get("collision_peak_contact_force_n")) / 1000.0, 4)),
                "Max penetration [mm]: " + str(
                    round(1000.0 * _safe_float(prestress.get("collision_max_penetration_m")), 4)),
                "Max penetration ratio: " + str(
                    round(_safe_float(prestress.get("collision_max_penetration_ratio")), 6)),
                "Contact duration [s]: " + str(round(_safe_float(prestress.get("collision_contact_duration_s")), 8)),
                "Beam contact: " + (
                    "enabled" if _safe_float(prestress.get("collision_beam_contact_enabled"), 0.0) > 0.0 else "off"),
                "Impact kinematics: " + str(prestress.get("collision_nonlinear_kinematics",
                                                          geometry.get("collision_nonlinear_kinematics",
                                                                       "von_karman"))),
                "Contact patch: factor "
                + str(round(_safe_float(prestress.get("collision_contact_patch_radius_factor")), 3))
                + ", nodes "
                + str(_safe_int(prestress.get("collision_contact_patch_min_nodes"), 0))
                + "-"
                + str(_safe_int(prestress.get("collision_contact_patch_max_nodes"), 0)),
                "Saved steps: " + str(_safe_int(prestress.get("collision_saved_steps"), 0)),
                "Deleted/eroded elements: "
                + str(_safe_int(prestress.get("collision_deleted_eroded_elements",
                                              prestress.get("collision_deleted_shell_elements")), 0)),
            ])
            if "collision_energy_initial_j" in prestress or "collision_energy_final_j" in prestress:
                lines.extend([
                    "Energy initial/final [J]: "
                    + str(round(_safe_float(prestress.get("collision_energy_initial_j")), 6))
                    + " / "
                    + str(round(_safe_float(prestress.get("collision_energy_final_j")), 6)),
                    "Energy max relative drift: "
                    + str(round(_safe_float(prestress.get("collision_energy_max_relative_drift")), 8)),
                ])
            if result.status == "running":
                sphere_position = tuple(prestress.get("collision_live_sphere_position_m") or ())
                lines.extend([
                    "Live time [s]: " + str(round(_safe_float(prestress.get("collision_live_time_s")), 8)),
                    "Live max displacement [mm]: " + str(
                        round(1000.0 * _safe_float(prestress.get("collision_live_max_displacement_m")), 6)),
                ])
                if sphere_position:
                    lines.append(
                        "Live sphere [m]: "
                        + ", ".join(str(round(_safe_float(value), 5)) for value in sphere_position[:3])
                    )
            lines.extend([
                "",
                "Time snapshots are available from the Result Case selector.",
            ])
        else:
            force = tuple((geometry.get("load_resultant") or {}).get("force_n") or ())
            applied_pressure = _safe_float(geometry.get("pressure_pa"))
            lines.extend([
                "--- STATIC RESPONSE ANALYSIS ---",
                "Status: " + result.status.replace("_", " "),
                "Solver: " + str(geometry.get("solver", "")),
                "Pressure [Pa]: " + str(round(applied_pressure, 3)),
                "Load scale: " + str(round(_safe_float(geometry.get("load_scale"), 1.0), 4)),
                "Max displacement [mm]: " + str(round(1000.0 * _safe_float(geometry.get("max_displacement_m")), 4)),
            ])
            for label, value in result.stress_percentiles:
                lines.append(label.upper() + " stress [MPa]: " + str(round(value / 1.0e6, 3)))
            if force:
                lines.append("Resultant force [N]: " + ", ".join(str(round(_safe_float(v), 2)) for v in force))

            lines.extend([
                "",
                "Buckling mode shapes are available from the Display selector.",
            ])

        self.upper_result_text.insert(tk.END, "\n".join(lines))
        self.upper_result_text.config(state=tk.DISABLED)

    def _copy_results_to_clipboard(self) -> None:
        if self.upper_result_text is None:
            return
        text = self.upper_result_text.get("1.0", tk.END).strip()
        if text:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
            self.window.update()

    def _parse_probe_id(self, variable: tk.StringVar) -> int | None:
        value = str(variable.get() or "").strip()
        if not value:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _manual_color_limits(self) -> tuple[float | None, float | None]:
        def parse(value: Any) -> float | None:
            text = str(value or "").strip()
            if not text:
                return None
            try:
                number = float(text)
            except (TypeError, ValueError):
                return None
            return number if math.isfinite(number) else None

        return parse(self.color_min_vis.get()), parse(self.color_max_vis.get())

    def _selected_color_data_range(self) -> tuple[float, float]:
        if self.current_result is None:
            return (0.0, 1.0)
        display_mode = self._selected_display_mode()
        if display_mode == "time_history":
            return (0.0, 1.0)
        component = self._selected_component()
        visualization, _title, is_mode = _selected_visualization(self.current_result, display_mode, component)
        values, _grid, _label = _visualization_color_values(
            visualization,
            component,
            is_mode,
            self.current_result.summary,
            self.show_stiffener_vis.get() if getattr(self, "show_stiffener_vis", None) is not None else True,
            self.show_girder_vis.get() if getattr(self, "show_girder_vis", None) is not None else True,
            include_members=_tk_var_float(self.member_alpha_vis, 1.0) > 0.0,
        )
        return _finite_value_range(values)

    def _sync_color_limit_controls(self, force: bool = False) -> None:
        signature = (self._selected_display_mode(), self._selected_component())
        data_min, data_max = self._selected_color_data_range()
        if data_max <= data_min:
            data_max = data_min + 1.0
        changed = force or signature != self._color_limit_signature
        self._color_limit_signature = signature
        self._color_limit_range = (data_min, data_max)
        self._color_limit_syncing = True
        try:
            if changed or not str(self.color_min_vis.get()).strip():
                self.color_min_vis.set(f"{data_min:.6g}")
            if changed or not str(self.color_max_vis.get()).strip():
                self.color_max_vis.set(f"{data_max:.6g}")
            for scale in (self.color_min_scale, self.color_max_scale):
                if scale is not None:
                    scale.configure(from_=data_min, to=data_max)
            self.color_min_slider.set(_tk_var_float(self.color_min_vis, data_min))
            self.color_max_slider.set(_tk_var_float(self.color_max_vis, data_max))
        finally:
            self._color_limit_syncing = False

    def _on_visualization_choice_changed(self, _event: Any = None) -> None:
        if self._selected_display_mode() != "time_history":
            self._last_mesh_result_case_label = str(self.result_case_choice.get())
        self._sync_time_slider()
        self._sync_color_limit_controls(force=True)
        self._refresh_figure(preserve_view=True)

    def _on_color_entry_changed(self, _event: Any = None) -> None:
        if self._color_limit_syncing:
            return
        self._sync_color_limit_controls(force=False)
        self._refresh_figure(preserve_view=True)

    def _on_color_slider(self, which: str, value: Any) -> None:
        if self._color_limit_syncing:
            return
        self._color_limit_syncing = True
        try:
            number = _safe_float(value, 0.0)
            if which == "min":
                self.color_min_vis.set(f"{number:.6g}")
            else:
                self.color_max_vis.set(f"{number:.6g}")
        finally:
            self._color_limit_syncing = False
        self._refresh_figure(preserve_view=True)

    def _show_probe_history(self) -> None:
        if self.current_result is None:
            self._write_status("Run FEM before showing a node or element history.", keep_run_results=True)
            return
        self._sync_selected_probe_from_entries()
        if self._selected_display_mode() != "time_history":
            self._last_mesh_result_case_label = str(self.result_case_choice.get())
        self.result_case_labels.setdefault("Time history graph", "time_history")
        if self.result_case_selector is not None:
            self.result_case_selector.configure(values=tuple(self.result_case_labels))
        self.result_case_choice.set("Time history graph")
        self._sync_color_limit_controls(force=True)
        self._refresh_figure(preserve_view=True)

    def _show_probe_mesh(self) -> None:
        if self.current_result is None:
            self._write_status("Run FEM before returning to the mesh view.", keep_run_results=True)
            return
        self._sync_selected_probe_from_entries()
        mesh_label = self._last_mesh_result_case_label
        if mesh_label not in self.result_case_labels:
            mesh_label = "Static displacement/stress"
        if mesh_label not in self.result_case_labels:
            mesh_label = next(iter(self.result_case_labels), "Static displacement/stress")
        self.result_case_choice.set(mesh_label)
        self._sync_color_limit_controls(force=True)
        self._refresh_figure(preserve_view=True)

    def _sync_selected_probe_from_entries(self) -> None:
        node_id = _tk_var_int(self.probe_node_id, -1)
        element_id = _tk_var_int(self.probe_element_id, -1)
        self._selected_probe_node_id = node_id if node_id >= 0 else None
        self._selected_probe_element_id = element_id if element_id >= 0 else None

    @staticmethod
    def _probe_component_unit(component: str) -> str:
        if component.endswith("_pa"):
            return "MPa"
        if component.startswith("disp") or component == "radial_displacement":
            return "mm"
        return ""

    def _probe_component_label(self, component: str) -> str:
        for label, key in getattr(self, "component_labels", {}).items():
            if key == component:
                return re.sub(r"\s*\[[^\]]+\]\s*$", "", str(label)).strip()
        return component.replace("_pa", "").replace("_", " ").strip()

    def _format_probe_value_label(self, target: str, component: str, value: float) -> str:
        unit = self._probe_component_unit(component)
        suffix = f" {unit}" if unit else ""
        return f"{target} {self._probe_component_label(component)}: {value:.6g}{suffix}"

    @staticmethod
    def _probe_node_displacement_value(surface: dict[str, Any], node_id: int, component: str) -> float | None:
        if not component.startswith("disp") and component != "radial_displacement":
            return None
        node_ids = tuple(int(candidate) for candidate in surface.get("node_ids", ()) or ())
        points = list(surface.get("points") or ())
        displaced_points = list(surface.get("displaced_points") or ())
        for index, candidate in enumerate(node_ids):
            if candidate != node_id or index >= len(points):
                continue
            try:
                base = np.asarray(points[index], dtype=float)
                moved = np.asarray(displaced_points[index], dtype=float) if index < len(displaced_points) else base
            except Exception:
                return None
            delta = moved - base
            if component == "disp_x":
                return float(delta[0]) * 1000.0
            if component == "disp_y":
                return float(delta[1]) * 1000.0
            if component == "disp_z":
                return float(delta[2]) * 1000.0
            return float(np.linalg.norm(delta)) * 1000.0
        return None

    @staticmethod
    def _probe_overlay_span(points: Sequence[Point3D]) -> float:
        if not points:
            return 1.0
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        zs = [point.z for point in points]
        return max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0e-6)

    def _draw_selected_probe_overlay(
            self,
            canvas: Tkinter3DCanvas,
            visualization: dict[str, Any],
            component: str,
            is_mode: bool,
            scale: float,
    ) -> None:
        element_id = self._selected_probe_element_id
        node_id = self._selected_probe_node_id
        if element_id is None and node_id is None:
            return

        surfaces = list(visualization.get("skin_shell_surfaces") or ()) + list(
            visualization.get("shell_surfaces") or ())
        all_points: list[Point3D] = []
        surface_points_by_id: dict[int, list[Point3D]] = {}
        node_points: dict[int, Point3D] = {}
        node_values: dict[int, float] = {}
        node_adjacent_element_values: dict[int, tuple[int, float]] = {}
        element_values: dict[int, float] = {}

        for surface in surfaces:
            polygon = [Point3D(x, y, z) for x, y, z in _shell_surface_points(surface, scale)]
            if len(polygon) < 3:
                continue
            all_points.extend(polygon)
            candidate_element_id = _safe_int(surface.get("id"), -1)
            if candidate_element_id >= 0:
                surface_points_by_id[candidate_element_id] = polygon
                element_values[candidate_element_id] = _shell_surface_component_value(surface, component,
                                                                                      is_mode=is_mode)
            element_value = element_values.get(candidate_element_id)
            node_ids = tuple(int(candidate) for candidate in surface.get("node_ids", ()) or ())
            for index, candidate_node_id in enumerate(node_ids):
                if index >= len(polygon):
                    continue
                node_points.setdefault(candidate_node_id, polygon[index])
                if candidate_element_id >= 0 and element_value is not None:
                    node_adjacent_element_values.setdefault(candidate_node_id, (candidate_element_id, element_value))
                node_value = self._probe_node_displacement_value(surface, candidate_node_id, component)
                if node_value is not None:
                    node_values[candidate_node_id] = node_value

        span = self._probe_overlay_span(all_points)
        marker = max(span * 0.012, 1.0e-4)
        label_offset = Point3D(marker * 1.8, marker * 1.8, marker * 1.2)
        label_text: str | None = None
        label_point: Point3D | None = None

        if element_id is not None and element_id in surface_points_by_id:
            polygon = surface_points_by_id[element_id]
            for index, start in enumerate(polygon):
                end = polygon[(index + 1) % len(polygon)]
                canvas.add_line(start, end, color="#facc15", width=4, layer=90, draw_overlay=True)
            centroid = Point3D(
                sum(point.x for point in polygon) / len(polygon),
                sum(point.y for point in polygon) / len(polygon),
                sum(point.z for point in polygon) / len(polygon),
            )
            element_value = element_values.get(element_id)
            if element_value is not None:
                label_text = self._format_probe_value_label(f"E{element_id}", component, element_value)
                label_point = centroid + label_offset

        if node_id is not None and node_id in node_points:
            point = node_points[node_id]
            canvas.add_line(
                Point3D(point.x - marker, point.y, point.z),
                Point3D(point.x + marker, point.y, point.z),
                color="#ef4444",
                width=4,
                layer=92,
                draw_overlay=True,
            )
            canvas.add_line(
                Point3D(point.x, point.y - marker, point.z),
                Point3D(point.x, point.y + marker, point.z),
                color="#ef4444",
                width=4,
                layer=92,
                draw_overlay=True,
            )
            canvas.add_line(
                Point3D(point.x, point.y, point.z - marker),
                Point3D(point.x, point.y, point.z + marker),
                color="#ef4444",
                width=4,
                layer=92,
                draw_overlay=True,
            )
            node_value = node_values.get(node_id)
            if node_value is not None or label_text is None:
                if node_value is not None:
                    label_text = self._format_probe_value_label(f"N{node_id}", component, node_value)
                else:
                    adjacent = node_adjacent_element_values.get(node_id)
                    if adjacent is not None:
                        adjacent_element_id, adjacent_value = adjacent
                        label_text = self._format_probe_value_label(f"E{adjacent_element_id}", component,
                                                                    adjacent_value)
                    else:
                        label_text = f"N{node_id} selected"
                label_point = point + label_offset

        if label_text and label_point is not None:
            canvas.add_text(
                label_point,
                label_text,
                color="#111827",
                font=("Segoe UI", 10, "bold"),
                anchor=tk.W,
                layer=95,
                draw_overlay=True,
            )

    def _refresh_figure(self, preserve_view: bool = False) -> None:
        self._update_result_text()
        if self.figure_parent is None:
            return

        show_base_geometry = self.current_result is None or self._display_base_geometry
        display_mode = self._selected_display_mode()
        if not show_base_geometry:
            self._sync_color_limit_controls(force=False)

        if hasattr(self, "preview_canvas") and self.preview_canvas is not None:
            try:
                self.preview_canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self.preview_canvas = None

        if display_mode != "time_history":
            if self.figure_canvas is not None:
                try:
                    self.figure_canvas.get_tk_widget().destroy()
                except Exception:
                    pass
                self.figure_canvas = None
            if self.figure_toolbar is not None:
                try:
                    self.figure_toolbar.destroy()
                except Exception:
                    pass
                self.figure_toolbar = None
            if self.figure_toolbar_frame is not None:
                try:
                    self.figure_toolbar_frame.destroy()
                except Exception:
                    pass
                self.figure_toolbar_frame = None

            canvas_created = self.result_canvas is None
            if canvas_created:
                self.result_canvas = self._create_3d_canvas(self.figure_parent, bg="white")
                self.result_canvas.pack(fill=tk.BOTH, expand=True)
                self._bind_custom_load_canvas_selection(self.result_canvas)
            self._apply_canvas_view_options(self.result_canvas)

            try:
                event_widget(self.result_canvas).configure(
                    cursor="crosshair" if self._custom_load_selection_active else ""
                )
            except Exception:
                pass

            fit_view = bool(canvas_created or self._force_fit_next_refresh or not preserve_view)
            self._force_fit_next_refresh = False
            smooth_refresh = bool(
                not canvas_created
                and preserve_view
                and (self._animation_running or str(getattr(self.current_result, "status", "") or "") == "running")
            )
            self.result_canvas.clear(keep_canvas=smooth_refresh)
            self.result_canvas.clear_thickness_legend()

            if show_base_geometry:
                self._populate_canvas_with_geometry(self.result_canvas, fit_view=fit_view)
            else:
                self._populate_canvas_with_results(self.result_canvas, fit_view=fit_view)
            if smooth_refresh and self.result_canvas is not None:
                cancel_redraw = getattr(self.result_canvas, "_cancel_scheduled_redraw", None)
                if callable(cancel_redraw):
                    cancel_redraw()
                self.result_canvas.redraw()
        else:
            if self.result_canvas is not None:
                try:
                    self.result_canvas.destroy()
                except Exception:
                    pass
                self.result_canvas = None

            self._force_fit_next_refresh = False
            self._show_figure(
                create_runtime_fem_result_figure(
                    self.snapshot,
                    None if show_base_geometry else self.current_result,
                    self._selected_display_mode(),
                    max(_tk_var_float(self.deformation_scale, 0.0), 0.0),
                    show_plate=self.show_plate_vis.get(),
                    show_stiffeners=self.show_stiffener_vis.get(),
                    show_girders=self.show_girder_vis.get(),
                    plate_alpha=_clamped_alpha(self.plate_alpha_vis.get(), 1.0),
                    member_alpha=_clamped_alpha(self.member_alpha_vis.get(), 0.95),
                    colormap=str(self.colormap_vis.get()),
                    component=self._selected_component(),
                    color_limits=self._manual_color_limits(),
                    probe_node_id=self._parse_probe_id(self.probe_node_id),
                    probe_element_id=self._parse_probe_id(self.probe_element_id),
                    show_sphere=bool(self.show_collision_sphere_vis.get()),
                    base_sphere=self._collision_sphere_preview_visualization(),
                    options=self._options(),
                ),
                self.figure_parent,
            )

    def _write_status(self, text: str, keep_run_results: bool = False) -> None:
        if self.result_text is None:
            return
        display_text = str(text)
        if keep_run_results and self._last_run_result_status_text:
            display_text = self._last_run_result_status_text + "\n\nRun status update:\n" + display_text
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, display_text)

    def _format_run_status_text(
            self,
            options: RuntimeFEMOptions,
            history: list[str],
            extra: str = "",
    ) -> str:
        detail_bits: list[str] = []
        if bool(options.local_refinement_enabled):
            detail_bits.append("panels=" + str(len(_runtime_local_refinement_patches(options))))
        if bool(options.point_refinement_enabled):
            detail_bits.append(
                "point=({x:.2f}, {y:.2f}) r={r:.2f}m".format(
                    x=float(options.point_refinement_x_m),
                    y=float(options.point_refinement_y_m),
                    r=float(options.point_refinement_extent_m),
                )
            )
        if bool(options.collision_adaptive_mesh_enabled):
            extent = (
                float(options.collision_adaptive_extent_m)
                if float(options.collision_adaptive_extent_m) > 0.0
                else float(options.collision_radius_m) * max(float(options.collision_adaptive_zone_factor), 0.5)
            )
            detail_bits.append("impact r={:.2f}m".format(extent))
        if bool(options.collision_enabled):
            if bool(options.collision_include_static_load):
                analysis_text = f"collision transient (+{options.analysis_type})"
            else:
                analysis_text = "collision transient (standalone)"
        else:
            analysis_text = str(options.analysis_type)

        lines = [
            "Running FEM solver...",
            "",
            "Setup",
            " - analysis: " + analysis_text,
            " - mesh: "
            + str(options.mesh_fidelity)
            + ", "
            + str(options.shell_element_order)
            + "/"
            + str(options.beam_element_order),
            " - detail mesh: " + (", ".join(detail_bits) if detail_bits else "off"),
            " - members: stiffeners="
            + str(bool(options.include_stiffeners))
            + ", girders="
            + str(bool(options.include_girders)),
        ]
        if bool(options.collision_enabled):
            lines.append(
                " - collision: "
                + ("nonlinear " if bool(options.collision_material_nonlinear_enabled) else "linear ")
                + "beam_contact="
                + str(bool(options.collision_beam_contact_enabled))
            )
        elif str(options.analysis_type).lower() == "nonlinear static":
            lines.append(
                " - nonlinear static: "
                + _normalise_kinematics(options.nonlinear_static_kinematics)
                + ", threads="
                + ("auto" if int(options.nonlinear_assembly_threads) <= 0 else str(
                    int(options.nonlinear_assembly_threads)))
            )
        messages = [str(message) for message in history if str(message).strip()]
        lines.extend(["", "Solver messages"])
        if messages:
            lines.extend(" - " + message for message in messages[-6:])
        else:
            lines.append(" - preparing request")
        if extra:
            lines.extend(["", str(extra)])
        return "\n".join(lines)

    def _set_solver_running(self, is_running: bool) -> None:
        if self.run_button is not None:
            self.run_button.configure(state=tk.DISABLED if is_running else tk.NORMAL)
        if self.cancel_button is not None:
            self.cancel_button.configure(state=tk.NORMAL if is_running else tk.DISABLED)
        self._update_buckling_handoff_button(is_running=is_running)
        if self.progress_bar is not None:
            if is_running:
                self.progress_bar.start(12)
            else:
                self.progress_bar.stop()

    def _has_runtime_fea_import_payload(self) -> bool:
        visualization = (self.current_result.visualization if self.current_result is not None else {}) or {}
        return isinstance(visualization.get("fea_result_import"), dict)

    def _update_buckling_handoff_button(self, is_running: bool = False) -> None:
        if self.use_for_buckling_button is None:
            return
        enabled = (not is_running) and self.current_result is not None and self._has_runtime_fea_import_payload()
        self.use_for_buckling_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _send_results_to_fea_buckling(self) -> None:
        if self.current_result is None or not self._has_runtime_fea_import_payload():
            messagebox.showinfo("FEA result buckling", "No importable FEM result is available yet. Run FEM first.")
            return
        importer = getattr(self.app, "import_runtime_fem_buckling_result", None)
        if importer is None:
            messagebox.showerror("FEA result buckling", "The main application cannot receive runtime FEM results.")
            return
        try:
            imported = bool(importer(self.current_result))
        except Exception as error:
            messagebox.showerror("FEA result buckling", str(error))
            return
        if imported:
            self._write_status("Returned FEM result to FEA-result buckling mode.", keep_run_results=True)

    _FEM_STATE_FILETYPES = (
        ("ANYstructure FEM state (compressed)", "*.fem.json.gz"),
        ("ANYstructure FEM state (plain JSON)", "*.fem.json"),
        ("All files", "*.*"),
    )

    def _save_fem_state(self) -> None:
        """Save the FE-GUI settings and, when available, the solver results with mesh."""
        path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save FEM settings and results",
            defaultextension=".fem.json.gz",
            filetypes=self._FEM_STATE_FILETYPES,
        )
        if not path:
            return
        try:
            save_runtime_fem_state(
                path,
                self._options(),
                result=self.current_result,
                snapshot=self.snapshot,
            )
        except Exception as error:
            messagebox.showerror("Save FEM state", str(error))
            return
        note = "settings only (run FEM to include results)" if self.current_result is None \
            else "settings and results including the mesh"
        self._write_status(f"Saved {note} to {os.path.basename(path)}.", keep_run_results=True)

    def _load_fem_state(self) -> None:
        """Load previously saved FE-GUI settings and solver results with mesh."""
        if self.run_button is not None and str(self.run_button["state"]) == "disabled":
            messagebox.showinfo("Load FEM state", "Wait for the running analysis to finish first.")
            return
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Load FEM settings and results",
            filetypes=self._FEM_STATE_FILETYPES,
        )
        if not path:
            return
        try:
            state = load_runtime_fem_state(path)
        except Exception as error:
            messagebox.showerror("Load FEM state", str(error))
            return
        self._apply_options_to_controls(state["options"])
        result = state["result"]
        if result is not None:
            self._adopt_loaded_result(result, source=os.path.basename(path))
        else:
            self._write_status(
                f"Loaded FEM settings from {os.path.basename(path)} (file holds no stored results)."
            )

    def _apply_options_to_controls(self, options: RuntimeFEMOptions) -> None:
        """Push a RuntimeFEMOptions object back into the popup controls."""
        for item in dataclass_fields(RuntimeFEMOptions):
            variable = getattr(self, item.name, None)
            if variable is None or not hasattr(variable, "set"):
                continue
            try:
                variable.set(getattr(options, item.name))
            except Exception:
                continue
        # Per-edge whole-boundary constraints live outside the tk variables.
        try:
            constraints = json.loads(options.boundary_constraint_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            constraints = {}
        specs: dict[str, dict[str, dict[str, Any]]] = {}
        for edge_key, dofs in (constraints or {}).items():
            if not isinstance(dofs, dict):
                continue
            spec = {
                str(dof): {"on": True, "value": _safe_float(value, 0.0)}
                for dof, value in dofs.items()
            }
            if spec:
                specs[str(edge_key)] = spec
        self._boundary_edge_specs = specs
        try:
            self._load_boundary_edge(str(self.boundary_edge_choice.get()))
        except Exception:
            pass
        # Per-edge component loads and the selected-edge component grid also
        # live outside the plain tk variables.
        try:
            raw_edge_loads = json.loads(options.edge_load_components_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_edge_loads = {}
        edge_load_specs: dict[str, dict[str, float]] = {}
        for edge_key, payload in (raw_edge_loads or {}).items():
            if not isinstance(payload, dict):
                continue
            spec = {
                dof: _safe_float(payload.get(dof), 0.0)
                for dof in self._load_dof_names
                if abs(_safe_float(payload.get(dof), 0.0)) > 0.0
            }
            if spec:
                edge_load_specs[str(edge_key)] = spec
        self._edge_load_specs = edge_load_specs
        try:
            self._load_edge_load_edge(str(self.edge_load_edge_choice.get()))
        except Exception:
            pass
        try:
            raw_selected = json.loads(options.custom_selected_edge_load_components_json or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_selected = {}
        if not isinstance(raw_selected, dict):
            raw_selected = {}
        for dof in self._load_dof_names:
            try:
                self.selected_edge_load_components[dof].set(_safe_float(raw_selected.get(dof), 0.0))
            except Exception:
                continue
        try:
            self._sync_mode_shapes_from_json()
        except Exception:
            pass

    def _adopt_loaded_result(self, result: RuntimeFEMRunResult, source: str = "") -> None:
        """Show a loaded solver result exactly like a freshly finished run."""
        self.current_result = result
        self._live_collision_sphere_visualization = {}
        self._display_base_geometry = False
        try:
            self._set_custom_load_selection_active(False, refresh=False)
        except Exception:
            pass
        self._force_fit_next_refresh = True
        self._set_display_modes(result)
        self._sync_color_limit_controls(force=True)
        self._last_run_result_status_text = format_runtime_fem_result(result)
        prefix = f"Loaded FEM settings and results from {source}.\n\n" if source else ""
        self._write_status(prefix + self._last_run_result_status_text)
        self._refresh_figure()
        self._update_buckling_handoff_button(is_running=False)

    def _options(self) -> RuntimeFEMOptions:
        return RuntimeFEMOptions(
            mesh_fidelity=str(self.mesh_fidelity.get()),
            pressure_pa=_tk_var_float(self.pressure_pa),
            load_scale=_tk_var_float(self.load_scale, 1.0),
            include_stiffeners=bool(self.include_stiffeners.get()),
            include_girders=bool(self.include_girders.get()),
            ignore_girder_length=bool(self.ignore_girder_length.get()),
            include_end_lids=bool(self.include_end_lids.get()),
            num_buckling_modes=max(_tk_var_int(self.num_buckling_modes, 5), 1),
            mesh_size_m=max(_tk_var_float(self.mesh_size_m, 0.0), 0.0),
            top_bottom_moment_nm=_tk_var_float(self.top_bottom_moment_nm, 0.0),
            torsional_moment_nm=_tk_var_float(self.torsional_moment_nm, 0.0),
            shear_force_n=_tk_var_float(self.shear_force_n, 0.0),
            acceleration_x_m_s2=_tk_var_float(self.acceleration_x_m_s2, 0.0),
            acceleration_y_m_s2=_tk_var_float(self.acceleration_y_m_s2, 0.0),
            acceleration_z_m_s2=_tk_var_float(self.acceleration_z_m_s2, 0.0),
            added_mass_kg=_tk_var_float(self.added_mass_kg, 0.0),
            added_mass_location=str(self.added_mass_location.get() or "none"),
            boundary_condition=str(self.boundary_condition.get()),
            boundary_constraint_json=self._collect_boundary_constraint_json(),
            boundary_auto_supports=bool(self.boundary_auto_supports.get()),
            symmetry_mode=str(self.symmetry_mode.get()),
            shell_element_order=str(self.shell_element_order.get()),
            beam_element_order=str(self.beam_element_order.get()),
            member_model=str(self.member_model.get()),
            analysis_type=str(self.analysis_type.get()),
            buckling_analysis_type=str(self.buckling_analysis_type.get()),
            pressure_direction=_normalise_pressure_side(self.pressure_direction.get()),
            follower_pressure=bool(self.follower_pressure.get()),
            axial_force_n=_tk_var_float(self.axial_force_n, 0.0),
            enforced_displacement_x_m=_tk_var_float(self.enforced_displacement_x_m, 0.0),
            enforced_displacement_y_m=_tk_var_float(self.enforced_displacement_y_m, 0.0),
            enforced_displacement_z_m=_tk_var_float(self.enforced_displacement_z_m, 0.0),
            stiffener_eccentricity_m=_tk_var_float(self.stiffener_eccentricity_m, 0.0),
            girder_eccentricity_m=_tk_var_float(self.girder_eccentricity_m, 0.0),
            member_orientation=str(self.member_orientation.get()),
            solver_type=str(self.solver_type.get()),
            stress_percentile=min(max(_tk_var_float(self.stress_percentile, 95.0), 0.0), 100.0),
            elastic_modulus_pa=max(_tk_var_float(self.elastic_modulus_gpa, 210.0), 1.0e-9) * 1.0e9,
            poisson_ratio=min(max(_tk_var_float(self.poisson_ratio, 0.3), 0.0), 0.49),
            yield_stress_pa=max(_tk_var_float(self.yield_stress_mpa, 355.0), 0.0) * 1.0e6,
            material_model=str(self.material_model.get()),
            steel_grade=str(self.steel_grade.get()),
            steel_thickness_class=str(self.steel_thickness_class.get()),
            nonlinear_max_load_factor=max(_tk_var_float(self.nonlinear_max_load_factor, 3.0), 1.0e-9),
            nonlinear_steps=max(_tk_var_int(self.nonlinear_steps, 12), 1),
            nonlinear_max_iterations=max(_tk_var_int(self.nonlinear_max_iterations, 25), 1),
            nonlinear_tolerance=max(_tk_var_float(self.nonlinear_tolerance, 1.0e-6), 1.0e-12),
            nonlinear_layers=_nearest_nonlinear_layer_count(self.nonlinear_layers.get()),
            nonlinear_solution_control=str(self.nonlinear_solution_control.get()),
            post_buckling_enabled=bool(self.post_buckling_enabled.get()),
            post_buckling_stop_load_fraction=float(self.post_buckling_stop_load_fraction.get()),
            post_buckling_max_displacement_m=float(self.post_buckling_max_displacement_m.get()),
            nonlinear_convergence_profile=str(self.nonlinear_convergence_profile.get()),
            nonlinear_assembly_threads=max(_tk_var_int(self.nonlinear_assembly_threads, 0), 0),
            nonlinear_static_kinematics=_normalise_kinematics(self.nonlinear_static_kinematics.get()),
            beam_consistent_mass_enabled=bool(self.beam_consistent_mass_enabled.get()),
            deformation_scale=max(_tk_var_float(self.deformation_scale, 0.0), 0.0),
            custom_load_bc_enabled=bool(self.custom_load_bc_enabled.get()),
            custom_loads_add_to_imported=bool(self.custom_loads_add_to_imported.get()),
            custom_use_nullspace_projection=(
                        bool(self.custom_use_nullspace_projection.get()) and not bool(self.collision_enabled.get())),
            custom_pressure_pa=_tk_var_float(self.custom_pressure_pa, 0.0),
            plate_edge_x0_support=str(self.plate_edge_x0_support.get()),
            plate_edge_x1_support=str(self.plate_edge_x1_support.get()),
            plate_edge_y0_support=str(self.plate_edge_y0_support.get()),
            plate_edge_y1_support=str(self.plate_edge_y1_support.get()),
            cylinder_lower_support=str(self.cylinder_lower_support.get()),
            cylinder_upper_support=str(self.cylinder_upper_support.get()),
            plate_edge_x0_load_n_per_m=_tk_var_float(self.plate_edge_x0_load_n_per_m, 0.0),
            plate_edge_x1_load_n_per_m=_tk_var_float(self.plate_edge_x1_load_n_per_m, 0.0),
            plate_edge_y0_load_n_per_m=_tk_var_float(self.plate_edge_y0_load_n_per_m, 0.0),
            plate_edge_y1_load_n_per_m=_tk_var_float(self.plate_edge_y1_load_n_per_m, 0.0),
            cylinder_lower_edge_load_n_per_m=_tk_var_float(self.cylinder_lower_edge_load_n_per_m, 0.0),
            cylinder_upper_edge_load_n_per_m=_tk_var_float(self.cylinder_upper_edge_load_n_per_m, 0.0),
            edge_load_components_json=self._collect_edge_load_components_json(),
            custom_loads_json=str(self.custom_loads_json.get()),
            custom_bc_segments_json=str(self.custom_bc_segments_json.get()),
            thickness_regions_json=str(self.thickness_regions_json.get()),
            custom_pressure_patches_json=str(self.custom_pressure_patches_json.get()),
            custom_edge_segments_json=str(self.custom_edge_segments_json.get()),
            custom_selected_edge_load_n_per_m=_tk_var_float(self.custom_selected_edge_load_n_per_m, 0.0),
            custom_selected_edge_load_components_json=self._selected_edge_load_components_json(),
            local_refinement_enabled=bool(self.local_refinement_enabled.get()),
            local_refinement_patches_json=str(self.local_refinement_patches_json.get()),
            local_refinement_fine_factor=_tk_var_float(self.local_refinement_fine_factor, 0.3),
            local_refinement_fine_size_m=max(_tk_var_float(self.local_refinement_fine_size_m, 0.0), 0.0),
            local_refinement_extent_m=max(_tk_var_float(self.local_refinement_extent_m, 0.0), 0.0),
            local_refinement_zone_factor=1.0,
            local_refinement_growth_factor=max(_tk_var_float(self.local_refinement_growth_factor, 1.35), 1.01),
            point_refinement_enabled=bool(self.point_refinement_enabled.get()),
            point_refinement_x_m=max(_tk_var_float(self.point_refinement_x_m, 0.0), 0.0),
            point_refinement_y_m=max(_tk_var_float(self.point_refinement_y_m, 0.0), 0.0),
            point_refinement_fine_factor=_tk_var_float(self.point_refinement_fine_factor, 0.3),
            point_refinement_fine_size_m=max(_tk_var_float(self.point_refinement_fine_size_m, 0.0), 0.0),
            point_refinement_extent_m=max(_tk_var_float(self.point_refinement_extent_m, 0.25), 0.0),
            point_refinement_growth_factor=max(_tk_var_float(self.point_refinement_growth_factor, 1.35), 1.01),
            custom_time_domain_enabled=bool(self.custom_time_domain_enabled.get()),
            custom_time_domain_duration_s=max(_tk_var_float(self.custom_time_domain_duration_s, 0.01), 0.0),
            custom_time_domain_total_time_s=max(_tk_var_float(self.custom_time_domain_total_time_s, 0.05), 0.0),
            custom_time_domain_dt_s=max(_tk_var_float(self.custom_time_domain_dt_s, 0.0005), 1.0e-9),
            custom_time_domain_result_interval_s=max(_tk_var_float(self.custom_time_domain_result_interval_s, 0.0),
                                                     0.0),
            custom_time_domain_include_static_load=bool(self.custom_time_domain_include_static_load.get()),
            imperfection_enabled=bool(self.imperfection_enabled.get()),
            imperfection_shape=str(self.imperfection_shape.get()),
            imperfection_amplitude_m=max(_tk_var_float(self.imperfection_amplitude_m, 0.0), 0.0),
            imperfection_wave_a=max(_tk_var_int(self.imperfection_wave_a, 1), 1),
            imperfection_wave_b=max(_tk_var_int(self.imperfection_wave_b, 1), 1),
            imperfection_mode_shapes_json=str(self.imperfection_mode_shapes_json.get()),
            runtime_solver=str(self.runtime_solver.get()),
            allow_unbalanced_free_free=bool(self.allow_unbalanced_free_free.get()),
            buckling_shift_load_factor=max(_tk_var_float(self.buckling_shift_load_factor, 0.0), 0.0),
            buckling_min_load_factor=max(_tk_var_float(self.buckling_min_load_factor, 0.0), 0.0),
            buckling_max_load_factor=max(_tk_var_float(self.buckling_max_load_factor, 0.0), 0.0),
            buckling_repeated_tolerance=max(_tk_var_float(self.buckling_repeated_tolerance, 1.0e-3), 0.0),
            buckling_allow_dense_fallback=bool(self.buckling_allow_dense_fallback.get()),
            recovery_history_mode=str(self.recovery_history_mode.get()),
            recovery_threads=max(_tk_var_int(self.recovery_threads, 0), 0),
            memory_limit_mb=max(_tk_var_float(self.memory_limit_mb, 0.0), 0.0),
            capacity_buckling_mode_number=max(_tk_var_int(self.capacity_buckling_mode_number, 1), 1),
            capacity_mesh_min_elements_per_half_wave=max(
                _tk_var_int(self.capacity_mesh_min_elements_per_half_wave, 4), 1),
            fracture_enabled=bool(self.fracture_enabled.get()),
            fracture_strain_threshold=max(_tk_var_float(self.fracture_strain_threshold, 0.02), 1.0e-12),
            fracture_residual_stiffness_fraction=min(
                max(_tk_var_float(self.fracture_residual_stiffness_fraction, 1.0e-6), 0.0), 1.0),
            fracture_max_deleted_fraction=min(max(_tk_var_float(self.fracture_max_deleted_fraction, 0.25), 1.0e-9),
                                              1.0),
            fracture_min_load_factor=max(_tk_var_float(self.fracture_min_load_factor, 0.0), 0.0),
            collision_enabled=bool(self.collision_enabled.get()),
            collision_include_static_load=bool(self.collision_include_static_load.get()),
            collision_damage_enabled=bool(self.collision_damage_enabled.get()),
            collision_material_nonlinear_enabled=bool(self.collision_material_nonlinear_enabled.get()),
            collision_nonlinear_kinematics=_normalise_kinematics(self.collision_nonlinear_kinematics.get()),
            collision_beam_contact_enabled=bool(self.collision_beam_contact_enabled.get()),
            collision_adaptive_mesh_enabled=bool(self.collision_adaptive_mesh_enabled.get()),
            collision_adaptive_fine_factor=_tk_var_float(self.collision_adaptive_fine_factor, 0.3),
            collision_adaptive_fine_size_m=_tk_var_float(self.collision_adaptive_fine_size_m, 0.0),
            collision_adaptive_extent_m=max(_tk_var_float(self.collision_adaptive_extent_m, 0.0), 0.0),
            collision_adaptive_growth_factor=max(_tk_var_float(self.collision_adaptive_growth_factor, 1.35), 1.01),
            detail_transition_style=str(self.detail_transition_style.get() or "graded grid"),
            collision_adaptive_zone_factor=_tk_var_float(self.collision_adaptive_zone_factor, 2.5),
            collision_nonlinear_max_iterations=max(_tk_var_int(self.collision_nonlinear_max_iterations, 20), 1),
            collision_nonlinear_tolerance=max(_tk_var_float(self.collision_nonlinear_tolerance, 1.0e-6), 1.0e-12),
            collision_nonlinear_cutbacks=max(_tk_var_int(self.collision_nonlinear_cutbacks, 8), 0),
            collision_plastic_damage_threshold=max(_tk_var_float(self.collision_plastic_damage_threshold, 0.01),
                                                   1.0e-12),
            collision_damage_criterion=str(self.collision_damage_criterion.get()),
            collision_mass_kg=max(_tk_var_float(self.collision_mass_kg, 1000.0), 1.0e-9),
            collision_radius_m=max(_tk_var_float(self.collision_radius_m, 0.25), 1.0e-9),
            collision_start_x_m=_tk_var_float(self.collision_start_x_m, 0.0),
            collision_start_y_m=_tk_var_float(self.collision_start_y_m, 0.0),
            collision_start_z_m=_tk_var_float(self.collision_start_z_m, 1.0),
            collision_vector_x=_tk_var_float(self.collision_vector_x, 0.0),
            collision_vector_y=_tk_var_float(self.collision_vector_y, 0.0),
            collision_vector_z=_tk_var_float(self.collision_vector_z, -1.0),
            collision_speed_mps=max(_tk_var_float(self.collision_speed_mps, 5.0), 0.0),
            collision_time_mode=str(self.collision_time_mode.get()),
            collision_auto_steps_per_radius=max(_tk_var_float(self.collision_auto_steps_per_radius, 20.0), 2.0),
            collision_auto_post_contact_radii=max(_tk_var_float(self.collision_auto_post_contact_radii, 6.0), 0.0),
            collision_bounce_back_time_s=max(_tk_var_float(self.collision_bounce_back_time_s, 0.01), 0.0),
            collision_total_time_s=max(_tk_var_float(self.collision_total_time_s, 0.05), 1.0e-9),
            collision_dt_s=max(_tk_var_float(self.collision_dt_s, 0.0005), 1.0e-9),
            collision_result_interval_s=max(_tk_var_float(self.collision_result_interval_s, 0.0), 0.0),
            collision_penalty_stiffness_n_per_m=max(_tk_var_float(self.collision_penalty_stiffness_n_per_m, 0.0),
                                                    0.0),
            collision_penalty_scale=max(_tk_var_float(self.collision_penalty_scale, 1.0), 1.0e-9),
            collision_auto_precondition=bool(self.collision_auto_precondition.get()),
            collision_contact_damping=max(_tk_var_float(self.collision_contact_damping, 0.0), 0.0),
            collision_max_iterations=max(_tk_var_int(self.collision_max_iterations, 25), 1),
            collision_penetration_tolerance_m=max(_tk_var_float(self.collision_penetration_tolerance_m, 1.0e-8),
                                                  1.0e-12),
            collision_force_tolerance_n=max(_tk_var_float(self.collision_force_tolerance_n, 1.0e-6), 1.0e-12),
            collision_target_penetration_fraction=max(
                _tk_var_float(self.collision_target_penetration_fraction, 0.01), 1.0e-9),
            collision_max_event_substeps=max(_tk_var_int(self.collision_max_event_substeps, 16), 1),
            collision_contact_surface=str(self.collision_contact_surface.get()),
            collision_damage_mode=str(self.collision_damage_mode.get()),
            collision_damage_capacity_basis=str(self.collision_damage_capacity_basis.get()),
            collision_damage_user_capacity_pa=max(_tk_var_float(self.collision_damage_user_capacity_mpa, 0.0),
                                                  0.0) * 1.0e6,
            collision_damage_softening_start=max(_tk_var_float(self.collision_damage_softening_start, 0.6), 0.0),
            collision_damage_delete_at=max(_tk_var_float(self.collision_damage_delete_at, 1.0), 1.0e-9),
            collision_damage_min_contact_area_m2=max(
                _tk_var_float(self.collision_damage_min_contact_area_m2, 1.0e-6), 1.0e-12),
            collision_damage_max_deleted_fraction=min(
                max(_tk_var_float(self.collision_damage_max_deleted_fraction, 0.25), 1.0e-9), 1.0),
            collision_damage_neighbor_smoothing=bool(self.collision_damage_neighbor_smoothing.get()),
        )

    def _bind_custom_load_list_traces(self) -> None:
        if self._custom_load_trace_ids:
            return
        variables: list[tk.Variable] = [
            self.custom_load_bc_enabled,
            self.custom_loads_add_to_imported,
            self.custom_use_nullspace_projection,
            self.allow_unbalanced_free_free,
            self.plate_edge_x0_support,
            self.plate_edge_x1_support,
            self.plate_edge_y0_support,
            self.plate_edge_y1_support,
            self.cylinder_lower_support,
            self.cylinder_upper_support,
            self.plate_edge_x0_load_n_per_m,
            self.plate_edge_x1_load_n_per_m,
            self.plate_edge_y0_load_n_per_m,
            self.plate_edge_y1_load_n_per_m,
            self.cylinder_lower_edge_load_n_per_m,
            self.cylinder_upper_edge_load_n_per_m,
            self.custom_time_domain_enabled,
            self.custom_time_domain_duration_s,
            self.custom_time_domain_total_time_s,
            self.custom_time_domain_dt_s,
            self.custom_time_domain_result_interval_s,
            self.custom_time_domain_include_static_load,
            self.boundary_edge_choice,
        ]
        for var in self.boundary_dof_on.values():
            variables.append(var)
        for var in self.boundary_dof_value.values():
            variables.append(var)
        variables.append(self.edge_load_edge_choice)
        for var in self.edge_load_components.values():
            variables.append(var)
        for var in self.selected_edge_load_components.values():
            variables.append(var)

        for variable in variables:
            trace_id = variable.trace_add("write", lambda *_args: self._refresh_custom_load_list())
            self._custom_load_trace_ids.append((variable, trace_id))

    def _custom_boundary_summary(self) -> tuple[str, str]:
        flags = [
            "custom on" if bool(self.custom_load_bc_enabled.get()) else "custom off",
            "add imported" if bool(self.custom_loads_add_to_imported.get()) else "replace imported",
        ]
        if bool(self.custom_use_nullspace_projection.get()):
            flags.append("nullspace")
        if bool(self.allow_unbalanced_free_free.get()):
            flags.append("allow free-free")

        try:
            constraints = json.loads(self._collect_boundary_constraint_json())
        except Exception:
            constraints = {}

        if not constraints:
            supports = "free"
        else:
            parts = []
            for edge, dofs in constraints.items():
                if edge == "all":
                    edge_name = "all edges"
                else:
                    edge_name = edge
                dof_strs = []
                for k, v in dofs.items():
                    if abs(v) > 1e-12:
                        dof_strs.append(f"{k}={v:g}")
                    else:
                        dof_strs.append(k)
                dof_str = ",".join(sorted(dof_strs))
                parts.append(f"{edge_name}=[{dof_str}]")
            supports = "; ".join(parts)

        # Whole-edge loads: fx..mz component sets per edge, with the legacy
        # scalar values shown only when non-zero (loaded from older states).
        edge_load_parts = []
        try:
            component_specs = json.loads(self._collect_edge_load_components_json() or "{}")
        except Exception:
            component_specs = {}
        for edge_key, spec in (component_specs or {}).items():
            if isinstance(spec, dict) and spec:
                dof_text = ",".join(f"{dof}={_safe_float(value, 0.0):g}" for dof, value in spec.items())
                edge_load_parts.append(f"{edge_key}=[{dof_text}]")
        if self.snapshot.is_cylinder:
            legacy = (("lower", self.cylinder_lower_edge_load_n_per_m),
                      ("upper", self.cylinder_upper_edge_load_n_per_m))
        else:
            legacy = (("x0", self.plate_edge_x0_load_n_per_m), ("x1", self.plate_edge_x1_load_n_per_m),
                      ("y0", self.plate_edge_y0_load_n_per_m), ("y1", self.plate_edge_y1_load_n_per_m))
        for name, variable in legacy:
            value = _tk_var_float(variable)
            if abs(value) > 0.0:
                edge_load_parts.append(f"{name} {value:g} N/m (legacy)")
        edge_loads = ", ".join(edge_load_parts) if edge_load_parts else "no edge loads"
        time_domain = "time off"
        if bool(self.custom_time_domain_enabled.get()):
            time_domain = (
                    "time dt="
                    + f"{_tk_var_float(self.custom_time_domain_dt_s):g}"
                    + " s, duration="
                    + f"{_tk_var_float(self.custom_time_domain_duration_s):g}"
                    + " s, total="
                    + f"{_tk_var_float(self.custom_time_domain_total_time_s):g}"
                    + " s"
            )
            interval = _tk_var_float(self.custom_time_domain_result_interval_s)
            if interval > 0.0:
                time_domain += ", result interval=" + f"{interval:g}" + " s"
            if bool(self.custom_time_domain_include_static_load.get()):
                time_domain += ", static included"
        notes = "; ".join(flags)
        if edge_loads:
            notes += "; " + edge_loads
        notes += "; " + time_domain
        return supports, notes

    @staticmethod
    def _custom_load_entry_selection_text(entry: dict[str, Any]) -> str:
        if str(entry.get("type", "")).lower() in {"pressure", "panel_pressure"}:
            patches = entry.get("patches", [])
            count = len(patches) if isinstance(patches, list) else 0
            area = 0.0
            if isinstance(patches, list):
                for patch in patches:
                    if not isinstance(patch, dict):
                        continue
                    area += max(0.0, _safe_float(patch.get("max_a")) - _safe_float(patch.get("min_a"))) * max(
                        0.0,
                        _safe_float(patch.get("max_b")) - _safe_float(patch.get("min_b")),
                    )
            return f"{count} panel(s), {area:.3f} m2"
        edges = entry.get("edges", [])
        count = len(edges) if isinstance(edges, list) else 0
        return f"{count} edge segment(s)"

    @staticmethod
    def _custom_load_entry_value_text(entry: dict[str, Any]) -> str:
        if str(entry.get("type", "")).lower() in {"pressure", "panel_pressure"}:
            return f"{_safe_float(entry.get('pressure_pa'), 0.0):g} Pa"
        components = entry.get("components")
        if isinstance(components, dict) and components:
            parts = []
            for key in ("fx", "fy", "fz", "mx", "my", "mz"):
                value = _safe_float(components.get(key), 0.0)
                if abs(value) > 0.0:
                    unit = "N/m" if key.startswith("f") else "Nm/m"
                    parts.append(f"{key} {value:g} {unit}")
            if parts:
                return "; ".join(parts)
        return f"{_safe_float(entry.get('line_load_n_per_m'), 0.0):g} N/m"

    def _refresh_custom_load_list(self) -> None:
        # Update Load tree
        tree = getattr(self, "_custom_load_tree", None)
        if tree is not None:
            selected = tree.selection()
            selected_iid = selected[0] if selected else ""
            for item in tree.get_children():
                tree.delete(item)
            for index, entry in enumerate(self._custom_load_entries):
                entry_type = str(entry.get("type", "")).lower()
                type_text = "Pressure" if entry_type in {"pressure", "panel_pressure"} else "Edge load"
                notes = "time-domain capable" if type_text == "Pressure" and bool(
                    self.custom_time_domain_enabled.get()) else ""
                tree.insert("", tk.END, iid=f"load:{index}", values=(
                    type_text, self._custom_load_entry_value_text(entry),
                    self._custom_load_entry_selection_text(entry), notes))
            if selected_iid and tree.exists(selected_iid):
                tree.selection_set(selected_iid)

        # Update BC tree
        bc_tree = getattr(self, "_custom_bc_tree", None)
        if bc_tree is not None:
            for item in bc_tree.get_children():
                bc_tree.delete(item)
            boundary_selection, boundary_notes = self._custom_boundary_summary()
            bc_tree.insert("", tk.END, iid="boundary", values=("Boundary", "", boundary_selection, boundary_notes))
            for index, entry in enumerate(getattr(self, "_custom_bc_entries", [])):
                edges = entry.get("edges", [])
                count = len(edges) if isinstance(edges, list) else 0
                bc_tree.insert("", tk.END, iid=f"bc:{index}", values=(
                    "Edge BC", str(entry.get("support", "")), f"{count} edge segment(s)", "selected edges"))

    def _local_refinement_patch_summary(self) -> tuple[int, float]:
        patches = _runtime_local_refinement_patches(
            RuntimeFEMOptions(local_refinement_patches_json=str(self.local_refinement_patches_json.get()))
        )
        area = sum(
            max(0.0, float(patch["max_a"]) - float(patch["min_a"]))
            * max(0.0, float(patch["max_b"]) - float(patch["min_b"]))
            for patch in patches
        )
        return len(patches), float(area)

    def _refresh_local_refinement_summary(self) -> None:
        if not hasattr(self, "local_refinement_summary_var"):
            return
        count, area = self._local_refinement_patch_summary()
        self.local_refinement_summary_var.set(f"Detail panels: {count} ({area:.3f} m2)")

    def _set_local_refinement_from_selection(self) -> None:
        selected_patches = [
            dict(patch)
            for patch in getattr(self, "_custom_load_patches", ())
            if bool(patch.get("selected", False))
        ]
        if not selected_patches:
            self._write_status("Select one or more panels in the 3D selection view before adding panel refinement.",
                               keep_run_results=True)
            return
        self.local_refinement_patches_json.set(json.dumps(selected_patches))
        self.local_refinement_enabled.set(True)
        self._refresh_local_refinement_summary()
        self._write_status(f"Added {len(selected_patches)} selected panel(s) as local mesh refinement regions.",
                           keep_run_results=True)

    def _clear_local_refinement_patches(self) -> None:
        self.local_refinement_patches_json.set("[]")
        self.local_refinement_enabled.set(False)
        self._refresh_local_refinement_summary()
        self._write_status("Cleared selected-panel mesh refinement regions.", keep_run_results=True)

    def _selected_or_active_custom_load_patch(self) -> dict[str, Any] | None:
        patches = getattr(self, "_custom_load_patches", ())
        if self._custom_load_selected_index >= 0 and self._custom_load_selected_index < len(patches):
            return dict(patches[self._custom_load_selected_index])
        for patch in patches:
            if bool(patch.get("selected", False)):
                return dict(patch)
        return None

    def _set_point_refinement_from_selected_panel(self) -> None:
        patch = self._selected_or_active_custom_load_patch()
        if patch is None:
            self._write_status("Select a panel before using its center as a point refinement source.",
                               keep_run_results=True)
            return
        min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(patch)
        x = 0.5 * (min_a + max_a)
        y = 0.5 * (min_b + max_b)
        self.point_refinement_x_m.set(float(x))
        self.point_refinement_y_m.set(float(y))
        self.point_refinement_enabled.set(True)
        self._sync_point_refinement_z_from_marker()
        self._write_status(self._point_refinement_report(float(x), float(y)), keep_run_results=True)
        self._refresh_figure(preserve_view=True)
        self._refresh_mesh_preview_if_present()

    def _set_mesh_point_selection_active(self, active: bool, refresh: bool = True) -> None:
        self._mesh_point_selection_active = bool(active)
        self._mesh_point_click_origin = None
        if self._mesh_point_selection_button is not None:
            self._mesh_point_selection_button.configure(text="Finish selection" if active else "Start selection")
        if self.result_canvas is not None:
            try:
                event_widget(self.result_canvas).configure(
                    cursor="crosshair" if (
                                self._mesh_point_selection_active or self._custom_load_selection_active) else ""
                )
            except Exception:
                pass
        if refresh:
            self._refresh_figure(preserve_view=True)

    def _toggle_mesh_point_selection(self) -> None:
        start_selection = not self._mesh_point_selection_active
        if start_selection:
            self.use_interactive_3d.set(True)
            self._display_base_geometry = True
            self._force_fit_next_refresh = self.result_canvas is None
            self._set_custom_load_selection_active(False, refresh=False)
            self._set_mesh_point_selection_active(True, refresh=False)
            self._write_status(
                "Point mesh selection is active. Click a panel in the 3D view to set the detail-mesh center.",
                keep_run_results=True)
        else:
            self._set_mesh_point_selection_active(False, refresh=False)
            self._write_status("Point mesh selection cancelled.", keep_run_results=True)
        self._refresh_figure(preserve_view=True)

    def _sync_custom_load_payloads(self) -> None:
        entries = [dict(entry) for entry in self._custom_load_entries]
        self.custom_loads_json.set(json.dumps(entries))
        pressure_patches: list[dict[str, Any]] = []
        edge_segments: list[dict[str, Any]] = []
        for entry in entries:
            if str(entry.get("type", "")).lower() in {"pressure", "panel_pressure"}:
                patches = entry.get("patches", [])
                if isinstance(patches, list):
                    pressure_patches.extend([dict(patch) for patch in patches if isinstance(patch, dict)])
            elif str(entry.get("type", "")).lower() in {"edge", "edge_load"}:
                edges = entry.get("edges", [])
                if isinstance(edges, list):
                    edge_segments.extend([dict(edge) for edge in edges if isinstance(edge, dict)])
        self.custom_pressure_patches_json.set(json.dumps(pressure_patches))
        self.custom_edge_segments_json.set(json.dumps(edge_segments))
        self._refresh_custom_load_list()

    def _add_custom_load_from_selection(self) -> None:
        selected_patches = []
        for patch in getattr(self, "_custom_load_patches", ()):
            if bool(patch.get("selected", False)):
                p = dict(patch)
                min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(p)
                p["min_a"] = min_a
                p["max_a"] = max_a
                p["min_b"] = min_b
                p["max_b"] = max_b
                if "axis_a_origin" in p:
                    del p["axis_a_origin"]
                selected_patches.append(p)
        selected_edges = self._selected_custom_load_edges()
        pressure = _tk_var_float(self.custom_pressure_pa, 0.0)
        components = self._load_component_values(self.selected_edge_load_components)
        added = 0
        if selected_patches and abs(pressure) > 0.0:
            self._custom_load_entries.append({
                "type": "pressure",
                "pressure_pa": float(pressure),
                "patches": selected_patches,
            })
            added += 1
        if selected_edges and components:
            self._custom_load_entries.append({
                "type": "edge",
                "components": components,
                "edges": selected_edges,
            })
            added += 1
        if added == 0:
            self._write_status(
                "Select at least one panel with non-zero pressure or right-click at least one edge "
                "with a non-zero fx-mz load component before adding.",
                keep_run_results=True,
            )
            return
        self.custom_load_bc_enabled.set(True)
        self._sync_custom_load_payloads()
        self._write_status(f"Added {added} custom load item(s) to the run list.", keep_run_results=True)

    def _sync_custom_bc_payloads(self) -> None:
        segments: list[dict[str, Any]] = []
        for entry in self._custom_bc_entries:
            constraints = entry.get("constraints")
            support = str(entry.get("support", "")) if not constraints else ""
            for edge in entry.get("edges", []) or []:
                if isinstance(edge, dict):
                    segment = dict(edge)
                    if constraints:
                        segment["constraints"] = dict(constraints)
                    else:
                        segment["support"] = support
                    segments.append(segment)
        self.custom_bc_segments_json.set(json.dumps(segments))
        self._refresh_custom_load_list()

    def _add_custom_bc_from_selection(self) -> None:
        """Apply the chosen boundary condition to the selected edges (mirrors Add load)."""
        selected_edges = self._selected_custom_load_edges()
        if not selected_edges:
            self._write_status(
                "Right-click at least one edge in the 3D selection view before setting a boundary condition.",
                keep_run_results=True,
            )
            return
        constraints = self._dof_grid_constraints(self.edge_dof_on, self.edge_dof_value)
        if not constraints:
            self._write_status(
                "Tick at least one DOF in the Selected-edge supports grid before setting a boundary condition.",
                keep_run_results=True,
            )
            return
        self._custom_bc_entries.append({"constraints": constraints, "edges": selected_edges})
        self._sync_custom_bc_payloads()
        label = ", ".join(f"{dof}={value:g}" for dof, value in constraints.items())
        self._write_status(
            f"Set edge BC ({label}) on {len(selected_edges)} selected edge segment(s).",
            keep_run_results=True,
        )

    def _delete_selected_custom_bc(self) -> None:
        tree = getattr(self, "_custom_bc_tree", None)
        if tree is None:
            return
        selected = tree.selection()
        if not selected or not selected[0].startswith("bc:"):
            self._write_status("Select an edge boundary condition in the list before deleting.",
                               keep_run_results=True)
            return
        try:
            index = int(selected[0].split(":", 1)[1])
        except (IndexError, ValueError):
            return
        if 0 <= index < len(self._custom_bc_entries):
            del self._custom_bc_entries[index]
            self._sync_custom_bc_payloads()
            self._write_status("Deleted selected edge boundary condition.", keep_run_results=True)

    # ------------------------------------------------------------------
    # Geometry tab: plate thickness regions and plane division
    # ------------------------------------------------------------------

    def _sync_thickness_regions(self) -> None:
        self.thickness_regions_json.set(json.dumps([dict(entry) for entry in self._thickness_region_entries]))
        self._refresh_thickness_region_list()

    def _refresh_thickness_region_list(self) -> None:
        tree = getattr(self, "_thickness_region_tree", None)
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)
        for index, entry in enumerate(self._thickness_region_entries):
            patches = entry.get("patches", []) or []
            area = 0.0
            for patch in patches:
                min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(patch)
                area += max(0.0, max_a - min_a) * max(0.0, max_b - min_b)
            tree.insert("", tk.END, iid=f"thick:{index}", values=(
                f"{_safe_float(entry.get('thickness_m'), 0.0) * 1000.0:.1f}",
                len(patches),
                f"{area:.3f}",
            ))

    def _set_thickness_region_from_selection(self, whole: bool = False) -> None:
        thickness = _tk_var_float(self.geometry_thickness_m, 0.0)
        if thickness <= 0.0:
            self._write_status("Enter a positive plate thickness [m] before assigning it.", keep_run_results=True)
            return
        patches = []
        for patch in getattr(self, "_custom_load_patches", ()):
            if whole or bool(patch.get("selected", False)):
                p = dict(patch)
                min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(p)
                p["min_a"] = min_a
                p["max_a"] = max_a
                p["min_b"] = min_b
                p["max_b"] = max_b
                if "axis_a_origin" in p:
                    del p["axis_a_origin"]
                patches.append(p)
        if not patches:
            self._write_status(
                "Select one or more panels in the 3D selection view first (or use 'Set on whole plate').",
                keep_run_results=True,
            )
            return
        self._thickness_region_entries.append({"thickness_m": float(thickness), "patches": patches})
        self._sync_thickness_regions()
        scope = "whole plate" if whole else f"{len(patches)} selected panel(s)"
        self._write_status(
            f"Set plate thickness {thickness * 1000.0:.1f} mm on {scope}.",
            keep_run_results=True,
        )

    def _delete_selected_thickness_region(self) -> None:
        tree = getattr(self, "_thickness_region_tree", None)
        if tree is None:
            return
        selected = tree.selection()
        if not selected or not selected[0].startswith("thick:"):
            self._write_status("Select a thickness region in the list before deleting.", keep_run_results=True)
            return
        try:
            index = int(selected[0].split(":", 1)[1])
        except (IndexError, ValueError):
            return
        if 0 <= index < len(self._thickness_region_entries):
            del self._thickness_region_entries[index]
            self._sync_thickness_regions()
            self._write_status("Deleted thickness region.", keep_run_results=True)

    def _clear_thickness_regions(self) -> None:
        self._thickness_region_entries.clear()
        self._sync_thickness_regions()
        self._write_status("Cleared all plate thickness regions.", keep_run_results=True)

    def _division_plane_param_cuts(self, axis: str, coordinate: float) -> tuple[list[tuple[str, float]], str]:
        """World plane -> parametric cut coordinates ((param_axis, value), ...)."""
        geometry = _popup_geometry_summary(self)
        axis = str(axis).lower()
        if self.snapshot.is_cylinder:
            radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-9)
            length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
            circumference = 2.0 * math.pi * radius
            if axis == "z":
                if not 0.0 < coordinate < length:
                    return [], f"Plane z={coordinate:g} m does not cut the cylinder (0..{length:g} m)."
                return [("a", coordinate)], ""
            if abs(coordinate) >= radius:
                return [], f"Plane {axis}={coordinate:g} m misses the cylinder (radius {radius:g} m)."
            if axis == "x":
                theta = math.acos(coordinate / radius)
                thetas = [theta, 2.0 * math.pi - theta]
            else:  # y plane
                theta = math.asin(coordinate / radius)
                thetas = [theta % (2.0 * math.pi), (math.pi - theta) % (2.0 * math.pi)]
            return [("b", value * radius) for value in sorted(set(round(t, 12) for t in thetas))
                    if 1.0e-9 < value * radius < circumference - 1.0e-9], ""
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
        width = max(_safe_float(geometry.get("width_m"), 1.0), 1.0e-9)
        if axis == "x":
            if not 0.0 < coordinate < length:
                return [], f"Plane x={coordinate:g} m does not cut the panel (0..{length:g} m)."
            return [("a", coordinate)], ""
        if axis == "y":
            if not 0.0 < coordinate < width:
                return [], f"Plane y={coordinate:g} m does not cut the panel (0..{width:g} m)."
            return [("b", coordinate)], ""
        return [], "A z-plane does not divide a flat panel; use x or y."

    def _split_all_patches_at(self, param_axis: str, coordinate: float) -> int:
        """Split every selection patch crossing the parametric coordinate."""
        patches = getattr(self, "_custom_load_patches", None)
        if not patches:
            return 0
        tol = 1.0e-9
        new_patches: list[dict[str, Any]] = []
        splits = 0
        for patch in patches:
            min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(patch)
            if param_axis == "a" and min_a + tol < coordinate < max_a - tol:
                first = dict(patch)
                first["max_a"] = coordinate
                second = dict(patch)
                second["min_a"] = coordinate
                new_patches.extend([first, second])
                cut = {"varying_axis": "b", "fixed_coordinate": coordinate,
                       "start_coordinate": min_b, "end_coordinate": max_b}
                self._custom_load_manual_cuts.append(cut)
                splits += 1
            elif param_axis == "b" and min_b + tol < coordinate < max_b - tol:
                first = dict(patch)
                first["max_b"] = coordinate
                second = dict(patch)
                second["min_b"] = coordinate
                new_patches.extend([first, second])
                cut = {"varying_axis": "a", "fixed_coordinate": coordinate,
                       "start_coordinate": min_a, "end_coordinate": max_a}
                self._custom_load_manual_cuts.append(cut)
                splits += 1
            else:
                new_patches.append(patch)
        self._custom_load_patches = new_patches
        return splits

    def _add_division_plane(self) -> None:
        axis = str(self.division_plane_axis.get() or "x")
        coordinate = _tk_var_float(self.division_plane_coord_m, 0.0)
        cuts, error = self._division_plane_param_cuts(axis, coordinate)
        if error:
            self._write_status(error, keep_run_results=True)
            return
        if not getattr(self, "_custom_load_patches", None):
            self._custom_load_select_all()
        total = 0
        for param_axis, value in cuts:
            total += self._split_all_patches_at(param_axis, value)
        if total == 0:
            self._write_status("The plane does not cross any panel; nothing was divided.", keep_run_results=True)
            return
        self._display_base_geometry = True
        self._refresh_figure(preserve_view=True)
        self._write_status(
            f"Division plane {axis}={coordinate:g} m split {total} panel(s).",
            keep_run_results=True,
        )

    def _show_thickness_plot(self) -> None:
        """Draw the generated model coloured by plate thickness (geometry tab)."""
        try:
            options = self._options()
            config = _solver_config_from_options(options)
            geometry = _popup_geometry_summary(self)
            generated = build_runtime_generated_geometry(geometry, config)
        except Exception as error:
            messagebox.showwarning("Thickness plot", "Could not build the geometry:\n" + str(error))
            return
        parent = getattr(self, "geometry_preview_parent", None)
        if parent is None:
            return
        self._last_geometry_preview = generated
        if self.geometry_preview_canvas is None:
            self.geometry_preview_canvas = self._create_3d_canvas(parent, bg="white")
            self.geometry_preview_canvas.pack(fill=tk.BOTH, expand=True)
        canvas = self.geometry_preview_canvas
        self._apply_canvas_view_options(canvas)
        canvas.clear()
        self._populate_canvas_with_thickness(canvas, generated)
        canvas.fit_to_scene()
        canvas.redraw()
        info = generated.get("thickness_regions") or {}
        if info:
            self._write_status(
                "Thickness plot: {count} shells in {regions} region(s), thicknesses {values} mm.".format(
                    count=int(info.get("shells_assigned", 0)),
                    regions=int(info.get("regions", 0)),
                    values=", ".join(f"{t * 1000.0:.1f}" for t in info.get("thicknesses_m", ())),
                ),
                keep_run_results=True,
            )
        else:
            self._write_status("Thickness plot: uniform plate thickness (no regions set).", keep_run_results=True)

    def _populate_canvas_with_thickness(self, canvas: "Tkinter3DCanvas", generated: dict) -> None:
        """Render all shells coloured by their plate thickness with a legend."""
        nodes = {int(n["id"]): n["coords"] for n in generated.get("nodes", ()) or () if "id" in n}
        thicknesses = [
            _safe_float(shell.get("thickness"), 0.0) * 1000.0
            for shell in generated.get("shells", ()) or ()
        ]
        values = sorted({round(t, 3) for t in thicknesses if t > 0.0})
        if values:
            canvas.set_thickness_legend(values, unit="mm", title="Plate thickness")
        shell_polygons = []
        shell_colors = []
        for shell in generated.get("shells", ()) or ():
            ids = [int(i) for i in shell.get("node_ids", ()) or () if int(i) in nodes]
            corners = ids[:3] if len(ids) in (3, 6) else ids[:4]
            if len(corners) < 3:
                continue
            shell_polygons.append([nodes[i] for i in corners])
            thickness_mm = _safe_float(shell.get("thickness"), 0.0) * 1000.0
            shell_colors.append(canvas.thickness_color(thickness_mm) if values else "#dbe4f0")
        if shell_polygons:
            canvas.add_faces(
                shell_polygons,
                colors=shell_colors,
                back_colors=shell_colors,
                outline="#334155",
                width=1,
            )
        for beam in generated.get("beams", ()) or ():
            ids = [int(i) for i in beam.get("node_ids", ()) or () if int(i) in nodes]
            if len(ids) < 2:
                continue
            pts = [Point3D(*[float(c) for c in nodes[i]]) for i in ids]
            for k in range(len(pts) - 1):
                canvas.add_line(pts[k], pts[k + 1], color="#1d4ed8", width=2)

    def _delete_selected_custom_load(self) -> None:
        tree = getattr(self, "_custom_load_tree", None)
        if tree is None:
            return
        selected = tree.selection()
        if not selected:
            self._write_status("Select a pressure or edge load in the list before deleting.", keep_run_results=True)
            return
        iid = selected[0]
        if not iid.startswith("load:"):
            self._write_status("Boundary-condition information cannot be deleted from the load list.",
                               keep_run_results=True)
            return
        try:
            index = int(iid.split(":", 1)[1])
        except (IndexError, ValueError):
            return
        if 0 <= index < len(self._custom_load_entries):
            del self._custom_load_entries[index]
            self._sync_custom_load_payloads()
            self._write_status("Deleted selected custom load from the run list.", keep_run_results=True)

    def _collision_support_is_valid(self) -> bool:
        boundary = str(self.boundary_condition.get() or "auto").strip().lower()
        if boundary not in {"auto", "free", "none"}:
            return True
        if self._custom_bc_entries:
            return True
        if self.snapshot.is_cylinder:
            supports = (self.cylinder_lower_support.get(), self.cylinder_upper_support.get())
        else:
            supports = (
                self.plate_edge_x0_support.get(),
                self.plate_edge_x1_support.get(),
                self.plate_edge_y0_support.get(),
                self.plate_edge_y1_support.get(),
            )
        return any(str(support or "free").strip().lower() not in {"free", "none"} for support in supports)

    def _collision_inputs_are_valid(self) -> bool:
        if not bool(self.collision_enabled.get()):
            return True
        if not self._collision_support_is_valid():
            messagebox.showerror(
                "Collision setup",
                "Collision requires at least one fixed, pinned, clamped, or otherwise constrained side/top/bottom. "
                "Choose a supported boundary condition or set custom edge/end supports; nullspace projection is not used for collision.",
            )
            return False
        direction = np.array(
            [
                _tk_var_float(self.collision_vector_x, 0.0),
                _tk_var_float(self.collision_vector_y, 0.0),
                _tk_var_float(self.collision_vector_z, 0.0),
            ],
            dtype=float,
        )
        if float(np.linalg.norm(direction)) <= 1.0e-12:
            messagebox.showerror("Collision setup", "Sphere travel vector must be non-zero.")
            return False
        if str(self.collision_time_mode.get()).strip().lower() == "manual" and (
                _tk_var_float(self.collision_dt_s, 0.0) <= 0.0
                or _tk_var_float(self.collision_total_time_s, 0.0) <= 0.0
        ):
            messagebox.showerror("Collision setup", "Collision total time and time step must be positive.")
            return False
        return True

    def _static_inputs_are_valid(self) -> bool:
        if (
                self._static_kinematics_selector_enabled()
                and _normalise_kinematics(self.nonlinear_static_kinematics.get()) == "corotational"
                and bool(self.fracture_enabled.get())
        ):
            messagebox.showerror(
                "FEM solver",
                "Corotational nonlinear static does not support fracture/erosion. "
                "Use Von Karman kinematics or disable strain-triggered erosion.",
            )
            return False
        return True

    def _reflect_effective_run_inputs(self) -> list[str]:
        """Push solver auto-set values back into the controls at run start.

        The solver promotes some inputs (material model, solution control,
        kinematics, layer count) depending on the analysis; the controls must
        show what the run actually uses.  Returns human-readable change notes.
        """
        changes: list[str] = []
        config = _solver_config_from_options(self._options())
        selection = fe_solver.resolve_runtime_analysis(config)
        material_choice = str(self.material_model.get() or "linear elastic")
        if (
                selection.material_nonlinear
                and material_choice.strip().lower() != "dnv-rp-c208 steel"
        ):
            self.material_model.set("DNV-RP-C208 steel")
            changes.append("Material model set to 'DNV-RP-C208 steel' (material-nonlinear run).")
        if selection.static_nonlinear:
            if (
                    selection.solution_control == "arc length"
                    and str(self.nonlinear_solution_control.get()).strip().lower() != "arc length"
            ):
                self.nonlinear_solution_control.set("arc length")
                changes.append("Nonlinear control set to 'arc length' (post-buckling continuation).")
            effective_kinematics = selection.kinematics
            if effective_kinematics != _normalise_kinematics(self.nonlinear_static_kinematics.get()):
                self.nonlinear_static_kinematics.set(_kinematics_label(effective_kinematics))
                changes.append("Kinematics set to '" + _kinematics_label(effective_kinematics) + "'.")
        if selection.material_nonlinear:
            requested_layers = max(_tk_var_int(self.nonlinear_layers, 5), 1)
            effective_layers = _nearest_nonlinear_layer_count(requested_layers)
            if effective_layers != requested_layers:
                self.nonlinear_layers.set(effective_layers)
                changes.append(
                    "Shell integration layers set to " + str(effective_layers) + " (supported: 3, 5, 7, 9, 11)."
                )
        return changes

    def run(self) -> None:
        """Prepare/run the runtime FEM request and render shared-viewer results."""

        if self.solver_thread is not None and self.solver_thread.is_alive():
            return
        self._stop_animation()
        self._refresh_option_states()
        if not self.include_stiffeners.get() and not self.include_girders.get():
            messagebox.showwarning("FEM solver", "At least one member beam family should normally be included.")
        if not self._static_inputs_are_valid():
            return
        if not self._collision_inputs_are_valid():
            return

        auto_set_notes = self._reflect_effective_run_inputs()
        options = self._options()
        self._active_run_options = options
        self._set_solver_running(True)
        self._cancel_requested = False
        self._last_run_result_status_text = ""
        self._live_collision_sphere_visualization = {}
        self._run_status_history = ["The result plot will update when the solver finishes.", ""]
        for note in auto_set_notes:
            self._run_status_history.append("Auto-set at run start: " + note)
        self._write_status(self._format_run_status_text(options, self._run_status_history))
        self._live_graph_reset(self._live_graph_kind_for_options(options))

        def worker() -> None:
            def status_cb(msg: str):
                if getattr(self, "_cancel_requested", False):
                    raise RuntimeError("Run stopped by user.")
                self.solver_queue.put(msg)

            try:
                # A custom mode-shape imperfection mesh ("Set to mesh") is used
                # whenever it exists. The imperfection checkbox only controls
                # the analytic standard shape applied by the solver itself, so
                # gating on it silently discarded the perturbed mesh.
                precomputed = getattr(self, "_imperfection_mesh", None)
                self.solver_queue.put((run_runtime_fem(self.snapshot, options, status_callback=status_cb,
                                                       imported_fem_model=self.imported_fem_model,
                                                       precomputed_generated_geometry=precomputed), None))
            except Exception as error:
                self.solver_queue.put((None, error))

        self.solver_thread = threading.Thread(target=worker, daemon=True)
        self.solver_thread.start()
        self.window.after(100, self._poll_solver_result)

    def _poll_solver_result(self) -> None:
        messages_processed = 0
        needs_status_update = False
        options = self._active_run_options or self._options()

        if not hasattr(self, "_run_status_history"):
            self._run_status_history = []

        while messages_processed < 50:
            try:
                msg = self.solver_queue.get_nowait()
            except queue.Empty:
                if self.solver_thread is not None and self.solver_thread.is_alive():
                    if needs_status_update:
                        self._write_status(self._format_run_status_text(options, self._run_status_history))
                    self.window.after(100, self._poll_solver_result)
                    return
                if needs_status_update:
                    self._write_status(self._format_run_status_text(options, self._run_status_history))
                self._set_solver_running(False)
                self._active_run_options = None
                return

            if isinstance(msg, str):
                if msg.startswith("\r"):
                    clean_msg = msg[1:]
                    if self._run_status_history:
                        self._run_status_history[-1] = clean_msg
                    else:
                        self._run_status_history.append(clean_msg)
                else:
                    self._run_status_history.append(msg)
                    self._run_status_history = self._run_status_history[-8:]
                needs_status_update = True
                messages_processed += 1
                continue

            if isinstance(msg, dict) and msg.get("type") == "live_visualization":
                self._apply_live_visualization(msg)
                messages_processed += 1
                # Visualizations are slightly heavy, maybe break to yield back to UI
                break

            if isinstance(msg, dict) and msg.get("type") == "nonlinear_static_step":
                self._apply_nonlinear_static_step(msg)
                needs_status_update = True
                messages_processed += 1
                continue

            if isinstance(msg, dict):
                # Unknown structured payload: ignore rather than crash the
                # result unpack below.
                messages_processed += 1
                continue

            # If we get here, it must be the result tuple
            result, error = msg
            if needs_status_update:
                self._write_status(self._format_run_status_text(options, self._run_status_history))
            self._set_solver_running(False)
            self._active_run_options = None
            if error is not None:
                self._write_status("Runtime FEM failed:\n" + str(error))
                messagebox.showerror("FEM solver", str(error))
                return

            self.current_result = result
            self._live_collision_sphere_visualization = {}
            self._display_base_geometry = False
            self._set_custom_load_selection_active(False, refresh=False)
            self._force_fit_next_refresh = True
            self._set_display_modes(result)
            self._sync_color_limit_controls(force=True)
            self._live_graph_finalize(result)
            self._last_run_result_status_text = format_runtime_fem_result(result)
            # Update the small Boundary tab label to reflect whether this run used nullspace projection
            try:
                self._update_nullspace_status()
            except Exception:
                pass
            self._write_status(self._last_run_result_status_text)
            self._refresh_figure()
            self._update_buckling_handoff_button(is_running=False)
            return

        if needs_status_update:
            self._write_status(self._format_run_status_text(options, self._run_status_history))
        self.window.after(20, self._poll_solver_result)

    _LIVE_GRAPH_LABELS = {
        "collision": ("time [s]", "Collision transient"),
        "equilibrium": ("max displacement [mm]", "Equilibrium path"),
        "time_domain": ("time [s]", "Time-domain response"),
        "buckling": ("mode", "Buckling factors"),
        "generic": ("step", "Run measures"),
        "idle": ("", "Live run graph (starts with the next run)"),
    }

    def _live_graph_kind_for_options(self, options: Any) -> str:
        """Pick the live-graph series family for a run configuration."""
        if bool(getattr(options, "collision_enabled", False)):
            return "collision"
        analysis = str(getattr(options, "analysis_type", "") or "").lower()
        runtime = str(getattr(options, "runtime_solver", "") or "").lower()
        control = str(getattr(options, "nonlinear_solution_control", "") or "").lower()
        if (
            bool(getattr(options, "post_buckling_enabled", False))
            or "nonlinear static" in analysis
            or "nonlinear static" in runtime
            or "capacity" in analysis
            or "capacity" in runtime
            or control.startswith("arc")
        ):
            return "equilibrium"
        if bool(getattr(options, "custom_time_domain_enabled", False)):
            return "time_domain"
        return "generic"

    def _live_graph_reset(self, kind: str) -> None:
        self._live_graph_state = {"kind": str(kind), "series": {}, "last_draw": 0.0}
        self._live_graph_redraw(force=True)

    def _live_graph_append(self, series_name: str, x: float, y: float) -> None:
        """Add one live sample and redraw (throttled)."""
        try:
            x_value = float(x)
            y_value = float(y)
        except (TypeError, ValueError):
            return
        if not (np.isfinite(x_value) and np.isfinite(y_value)):
            return
        series = self._live_graph_state.setdefault("series", {})
        xs, ys = series.setdefault(str(series_name), ([], []))
        xs.append(x_value)
        ys.append(y_value)
        self._live_graph_redraw()

    @staticmethod
    def _live_graph_axis_split(series: dict[str, tuple[list, list]]) -> set[str]:
        """Series names that belong on a secondary y-axis.

        When magnitudes are mixed (contact force in kN next to displacement
        in mm), the large series flattens the small ones to the x-axis.  The
        populated series are split at the widest log-scale gap when the
        overall spread exceeds one order of magnitude; the large group moves
        to the right-hand axis.
        """
        scales = {
            name: max((abs(float(value)) for value in ys), default=0.0)
            for name, (xs, ys) in series.items()
            if xs
        }
        positive = {name: scale for name, scale in scales.items() if scale > 0.0}
        if len(positive) < 2:
            return set()
        ordered = sorted(positive.items(), key=lambda item: item[1])
        if ordered[-1][1] / ordered[0][1] < 10.0:
            return set()
        log_scales = [math.log10(scale) for _name, scale in ordered]
        gaps = [log_scales[index + 1] - log_scales[index] for index in range(len(log_scales) - 1)]
        split_index = gaps.index(max(gaps)) + 1
        return {name for name, _scale in ordered[split_index:]}

    def _live_graph_redraw(self, force: bool = False) -> None:
        axis = self._live_graph_axis
        canvas = self._live_graph_canvas
        if axis is None or canvas is None:
            return
        now = time.perf_counter()
        if not force and now - float(self._live_graph_state.get("last_draw", 0.0)) < 0.3:
            return
        self._live_graph_state["last_draw"] = now
        kind = str(self._live_graph_state.get("kind", "idle"))
        xlabel, title = self._LIVE_GRAPH_LABELS.get(kind, self._LIVE_GRAPH_LABELS["generic"])
        secondary = getattr(self, "_live_graph_axis2", None)
        if secondary is not None:
            try:
                secondary.remove()
            except Exception:
                pass
            self._live_graph_axis2 = None
        axis.clear()
        series = self._live_graph_state.get("series", {}) or {}
        right_names = self._live_graph_axis_split(series)
        right_axis = None
        if right_names:
            right_axis = axis.twinx()
            self._live_graph_axis2 = right_axis
        handles = []
        labels = []
        color_cycle = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b")
        for color_index, (name, (xs, ys)) in enumerate(series.items()):
            if not xs:
                continue
            target = right_axis if (right_axis is not None and name in right_names) else axis
            label = name + (" (right)" if target is right_axis else "")
            color = color_cycle[color_index % len(color_cycle)]
            if kind == "buckling":
                line, = target.plot(xs, ys, marker="o", linestyle="", markersize=4, label=label, color=color)
            else:
                line, = target.plot(
                    xs, ys, linewidth=1.2, label=label, color=color,
                    linestyle="--" if target is right_axis else "-",
                )
            handles.append(line)
            labels.append(label)
        if handles:
            axis.legend(handles, labels, fontsize=6, loc="best")
        else:
            axis.text(0.5, 0.5, "waiting for data" if kind != "idle" else title,
                      ha="center", va="center", fontsize=7, color="#6b7280",
                      transform=axis.transAxes)
        axis.set_xlabel(xlabel, fontsize=6)
        axis.set_title(title, fontsize=7)
        axis.tick_params(labelsize=6)
        if right_axis is not None:
            right_axis.tick_params(labelsize=6)
        axis.grid(True, linewidth=0.3, alpha=0.5)
        try:
            self._live_graph_figure.tight_layout(pad=0.4)
        except Exception:
            pass
        try:
            canvas.draw_idle()
        except Exception:
            pass

    def _live_graph_finalize(self, result: Any) -> None:
        """Fill the graph from the final result when no live series streamed."""
        state = self._live_graph_state
        has_data = any(xs for xs, _ys in (state.get("series", {}) or {}).values())
        factors = tuple(getattr(result, "buckling_factors", ()) or ())
        if not has_data and factors:
            state["kind"] = "buckling"
            state["series"] = {
                "load factor": ([float(index + 1) for index in range(len(factors))],
                                 [float(value) for value in factors]),
            }
        self._live_graph_redraw(force=True)

    def _apply_nonlinear_static_step(self, payload: dict[str, Any]) -> None:
        """Equilibrium-path point from the nonlinear static / arc-length solver."""
        load_factor = _safe_float(payload.get("load_factor"), 0.0)
        displacement_mm = _safe_float(payload.get("max_translation"), 0.0) * 1000.0
        self._live_graph_append("load factor", displacement_mm, load_factor)
        plastic = _safe_float(payload.get("max_equivalent_plastic_strain"), 0.0)
        if plastic > 0.0:
            self._live_graph_append("plastic strain [%]", displacement_mm, plastic * 100.0)
        peak = _safe_float(payload.get("peak_load_factor"), 0.0)
        step_line = (
            f"{'Arc-length' if str(payload.get('control', '')) == 'arc length' else 'Nonlinear'} step "
            f"{_safe_int(payload.get('step_index'), 0)}: load factor {load_factor:.4f}"
            + (f" (peak {peak:.4f})" if peak > 0.0 else "")
            + f", max displacement {displacement_mm:.2f} mm"
        )
        if not hasattr(self, "_run_status_history"):
            self._run_status_history = []
        if self._run_status_history and str(self._run_status_history[-1]).startswith(("Arc-length step", "Nonlinear step")):
            self._run_status_history[-1] = step_line
        else:
            self._run_status_history.append(step_line)
            self._run_status_history = self._run_status_history[-8:]

    def _apply_live_visualization(self, payload: dict[str, Any]) -> None:
        live_time = _safe_float(payload.get("time_s"), 0.0)
        self._live_graph_append("max displacement [mm]", live_time,
                                _safe_float(payload.get("displacement_max_m"), 0.0) * 1000.0)
        contact_force = _safe_float(payload.get("contact_force_n"), 0.0)
        if contact_force > 0.0 or self._live_graph_state.get("series", {}).get("contact force [kN]"):
            self._live_graph_append("contact force [kN]", live_time, contact_force / 1000.0)
        plastic = _safe_float(payload.get("max_equivalent_plastic_strain"), 0.0)
        if plastic > 0.0 or self._live_graph_state.get("series", {}).get("plastic strain [%]"):
            self._live_graph_append("plastic strain [%]", live_time, plastic * 100.0)
        visualization = dict(payload.get("visualization") or {})
        if not visualization:
            return
        live_sphere = visualization.get("rigid_sphere") if isinstance(visualization, dict) else None
        self._live_collision_sphere_visualization = {"rigid_sphere": dict(live_sphere)} if isinstance(live_sphere,
                                                                                                      dict) else {}
        live_sphere_position = ()
        if isinstance(live_sphere, dict):
            try:
                live_sphere_position = tuple(
                    float(value) for value in np.asarray(live_sphere.get("position", ()), dtype=float).reshape(-1)[:3])
            except Exception:
                live_sphere_position = ()
        geometry = _popup_geometry_summary(self)
        time_value = _safe_float(payload.get("time_s"), 0.0)
        options = self._active_run_options or self._options()
        summary = {
            **geometry,
            "line": self.snapshot.line_name,
            "solver": "ANYstructure production FE mesh",
            "analysis_type": "collision transient running",
            "runtime_solver": "sphere collision transient",
            "collision_enabled": True,
            "prestress_summary": {
                "collision_status": "running",
                "collision_time_mode": str(self.collision_time_mode.get()),
                "collision_saved_steps": _safe_int(payload.get("step_index"), 0) + 1,
                "collision_live_time_s": float(time_value),
                "collision_live_max_displacement_m": _safe_float(payload.get("displacement_max_m"), 0.0),
                "collision_live_sphere_position_m": live_sphere_position,
                "collision_beam_contact_enabled": 1.0 if bool(options.collision_beam_contact_enabled) else 0.0,
                "collision_damage_enabled": 1.0 if bool(options.collision_damage_enabled) else 0.0,
                "collision_material_nonlinear_enabled": 1.0 if bool(
                    options.collision_material_nonlinear_enabled) else 0.0,
                "collision_nonlinear_kinematics": str(options.collision_nonlinear_kinematics),
            },
            "max_displacement_m": _safe_float(payload.get("displacement_max_m"), 0.0),
        }
        self.current_result = RuntimeFEMRunResult(
            status="running",
            summary=summary,
            diagnostics=("Live collision visualization is throttled and will be replaced by the final result.",),
            buckling_factors=(),
            stress_percentiles=(("p95", 0.0), ("max", 0.0)),
            displacement_scale=max(_safe_float(payload.get("displacement_max_m"), 0.0), 1.0e-12),
            visualization=visualization,
        )
        self._display_base_geometry = False
        self.result_case_labels = {"Live collision t=" + f"{time_value:.6g}" + " s": "static"}
        self.result_case_choice.set(next(iter(self.result_case_labels)))
        if self.result_case_selector is not None:
            self.result_case_selector.configure(values=tuple(self.result_case_labels))
        live_component_labels = {
            "Displacement Magnitude": "disp_mag",
            "Displacement X": "disp_x",
            "Displacement Y": "disp_y",
            "Displacement Z": "disp_z",
        }
        self.component_labels = live_component_labels
        if self.component_choice.get() not in live_component_labels:
            self.component_choice.set("Displacement Magnitude")
        if self.component_selector is not None:
            self.component_selector.configure(values=tuple(live_component_labels.keys()))
        if bool(self.animation_fast_mode.get()):
            self.use_interactive_3d.set(True)
        self._sync_color_limit_controls(force=True)
        self._refresh_figure(preserve_view=True)
        if hasattr(self, "_run_status_history"):
            options = self._active_run_options or self._options()
            self._write_status(
                self._format_run_status_text(
                    options,
                    list(self._run_status_history)[-8:],
                    "Live collision t=" + f"{time_value:.6g}" + " s",
                )
            )

    def _set_custom_load_selection_active(self, active: bool, refresh: bool = True) -> None:
        self._custom_load_selection_active = bool(active)
        self._custom_load_click_origin = None
        self._custom_load_edge_click_origin = None
        label = "Finish selection" if self._custom_load_selection_active else "Start selection"
        for button_name in ("_custom_load_selection_button", "_custom_bc_selection_button",
                            "_geometry_selection_button"):
            button = getattr(self, button_name, None)
            if button is not None:
                try:
                    button.configure(text=label)
                except Exception:
                    pass
        if self.result_canvas is not None:
            try:
                event_widget(self.result_canvas).configure(
                    cursor="crosshair" if (
                                self._custom_load_selection_active or self._mesh_point_selection_active) else ""
                )
            except Exception:
                pass
        if refresh:
            self._refresh_figure(preserve_view=True)

    def _toggle_custom_load_selection(self) -> None:
        start_selection = not self._custom_load_selection_active
        if start_selection:
            self.use_interactive_3d.set(True)
            self._display_base_geometry = True
            self._force_fit_next_refresh = self.result_canvas is None
            self._set_mesh_point_selection_active(False, refresh=False)
            self._set_custom_load_selection_active(True, refresh=False)
            self._write_status(
                "Custom load selection is active. Left-click panels for pressure; right-click edges for line loads; right-drag rotates, left-drag moves, wheel zooms.",
                keep_run_results=True,
            )
        else:
            self._set_custom_load_selection_active(False, refresh=False)
            self._write_status("Custom load selection finished.", keep_run_results=True)
        self._refresh_figure(preserve_view=True)

    def _bind_custom_load_canvas_selection(self, canvas: Tkinter3DCanvas) -> None:
        widget = event_widget(canvas)
        widget.bind("<ButtonPress-1>", self._on_custom_load_canvas_press, add="+")
        widget.bind("<ButtonRelease-1>", self._on_custom_load_canvas_release, add="+")
        widget.bind("<ButtonPress-3>", self._on_custom_load_edge_canvas_press, add="+")
        widget.bind("<ButtonRelease-3>", self._on_custom_load_edge_canvas_release, add="+")

    def _on_custom_load_canvas_press(self, event: Any) -> None:
        if self._mesh_point_selection_active:
            self._mesh_point_click_origin = (int(event.x), int(event.y))
        elif self._custom_load_selection_active:
            self._custom_load_click_origin = (int(event.x), int(event.y))
        else:
            self._probe_click_origin = (int(event.x), int(event.y))

    def _on_custom_load_canvas_release(self, event: Any) -> None:
        mesh_origin = self._mesh_point_click_origin
        self._mesh_point_click_origin = None
        if self._mesh_point_selection_active:
            if mesh_origin is None or self.result_canvas is None:
                return
            if math.hypot(float(event.x) - mesh_origin[0], float(event.y) - mesh_origin[1]) > 5.0:
                return
            point = self._pick_mesh_refinement_point(self.result_canvas, float(event.x), float(event.y))
            if point is None:
                self._write_status("Point mesh selection: no panel was found at the clicked position.",
                                   keep_run_results=True)
                return
            self.point_refinement_x_m.set(float(point[0]))
            self.point_refinement_y_m.set(float(point[1]))
            self.point_refinement_enabled.set(True)
            self._sync_point_refinement_z_from_marker()
            self._set_mesh_point_selection_active(False, refresh=False)
            self._write_status(self._point_refinement_report(float(point[0]), float(point[1])),
                               keep_run_results=True)
            self._refresh_figure(preserve_view=True)
            self._refresh_mesh_preview_if_present()
            return

        origin = self._custom_load_click_origin
        self._custom_load_click_origin = None
        probe_origin = self._probe_click_origin
        self._probe_click_origin = None
        if not self._custom_load_selection_active:
            if probe_origin is not None and self.result_canvas is not None:
                if math.hypot(float(event.x) - probe_origin[0], float(event.y) - probe_origin[1]) <= 5.0:
                    self._select_probe_from_result_click(self.result_canvas, float(event.x), float(event.y))
            return
        if origin is None or self.result_canvas is None:
            return
        if math.hypot(float(event.x) - origin[0], float(event.y) - origin[1]) > 5.0:
            return

        patch_index = self._pick_custom_load_patch(self.result_canvas, float(event.x), float(event.y))
        if patch_index is None:
            self._write_status("Custom load selection: no panel was found at the clicked position.",
                               keep_run_results=True)
            return

        self._custom_load_selected_index = patch_index
        patch = self._custom_load_patches[patch_index]
        patch["selected"] = not bool(patch.get("selected", False))
        self._update_custom_load_summary()
        state = "selected" if patch["selected"] else "cleared"
        self._write_status(f"Custom load panel {patch_index + 1} {state}.", keep_run_results=True)
        self._refresh_figure(preserve_view=True)

    def _select_probe_from_result_click(
            self,
            canvas: Tkinter3DCanvas,
            screen_x: float,
            screen_y: float,
    ) -> None:
        if self.current_result is None or self._display_base_geometry:
            return
        display_mode = self._selected_display_mode()
        if display_mode == "time_history":
            return
        component = self._selected_component()
        visualization, _title, is_mode = _selected_visualization(self.current_result, display_mode, component)
        if is_mode:
            return

        scale = _displacement_plot_scale(
            self.current_result.summary,
            self.current_result,
            visualization,
            max(_tk_var_float(self.deformation_scale, 0.0), 0.0),
        )
        surfaces = list(visualization.get("skin_shell_surfaces") or ()) + list(
            visualization.get("shell_surfaces") or ())
        best_element_id: int | None = None
        best_element_depth = float("inf")
        best_node_id: int | None = None
        best_node_distance = 18.0

        for surface in surfaces:
            polygon = _shell_surface_points(surface, scale)
            if len(polygon) < 3:
                continue
            points = [Point3D(x, y, z) for x, y, z in polygon]
            projected = self._project_custom_load_points(canvas, points)
            if len(projected) < 3:
                continue
            projected_xy = [(x, y) for x, y, _depth in projected]
            mean_depth = sum(depth for _x, _y, depth in projected) / len(projected)

            if self._point_in_polygon_2d(screen_x, screen_y, projected_xy) and mean_depth < best_element_depth:
                best_element_depth = mean_depth
                best_element_id = _safe_int(surface.get("id"), -1)
                if best_element_id < 0:
                    best_element_id = None

            node_ids = tuple(int(node_id) for node_id in surface.get("node_ids", ()) or ())
            for index, (proj_x, proj_y, _depth) in enumerate(projected):
                if index >= len(node_ids):
                    continue
                distance = math.hypot(screen_x - proj_x, screen_y - proj_y)
                if distance < best_node_distance:
                    best_node_distance = distance
                    best_node_id = int(node_ids[index])

        if best_element_id is None and surfaces:
            best_distance = 36.0
            best_depth = float("inf")
            for surface in surfaces:
                polygon = _shell_surface_points(surface, scale)
                points = [Point3D(x, y, z) for x, y, z in polygon]
                projected = self._project_custom_load_points(canvas, points)
                if not projected:
                    continue
                cx = sum(x for x, _y, _depth in projected) / len(projected)
                cy = sum(y for _x, y, _depth in projected) / len(projected)
                depth = sum(depth for _x, _y, depth in projected) / len(projected)
                distance = math.hypot(screen_x - cx, screen_y - cy)
                if distance < best_distance and depth < best_depth:
                    candidate_id = _safe_int(surface.get("id"), -1)
                    if candidate_id >= 0:
                        best_element_id = candidate_id
                        best_distance = distance
                        best_depth = depth

        if best_node_id is None and best_element_id is None:
            self._write_status("No result node or element was found at the clicked position.", keep_run_results=True)
            return

        self.probe_node_id.set(str(best_node_id) if best_node_id is not None else "")
        self.probe_element_id.set(str(best_element_id) if best_element_id is not None else "")
        self._selected_probe_node_id = best_node_id
        self._selected_probe_element_id = best_element_id
        self._last_mesh_result_case_label = str(self.result_case_choice.get())
        self._refresh_figure(preserve_view=True)

        time_domain = (self.current_result.visualization or {}).get("time_domain", {}) or {}
        history_hint = " Use Show history to plot the time response." if time_domain else " Run a time-domain case to show history graphs."
        self._write_status(
            "Selected node "
            + (str(best_node_id) if best_node_id is not None else "-")
            + " / element "
            + (str(best_element_id) if best_element_id is not None else "-")
            + "."
            + history_hint,
            keep_run_results=True,
        )

    def _on_custom_load_edge_canvas_press(self, event: Any) -> None:
        if self._custom_load_selection_active:
            self._custom_load_edge_click_origin = (int(event.x), int(event.y))

    def _on_custom_load_edge_canvas_release(self, event: Any) -> None:
        origin = self._custom_load_edge_click_origin
        self._custom_load_edge_click_origin = None
        if not self._custom_load_selection_active or origin is None or self.result_canvas is None:
            return
        if math.hypot(float(event.x) - origin[0], float(event.y) - origin[1]) > 5.0:
            return

        edge = self._pick_custom_load_edge(self.result_canvas, float(event.x), float(event.y))
        if edge is None:
            self._write_status("Custom load selection: no edge was found at the clicked position.",
                               keep_run_results=True)
            return

        key = self._custom_load_edge_key(*edge)
        if key in self._custom_selected_edge_keys:
            self._custom_selected_edge_keys.remove(key)
            state = "cleared"
        else:
            self._custom_selected_edge_keys.add(key)
            state = "selected"
        self._update_custom_load_summary()
        self._write_status(f"Custom load edge {state}.", keep_run_results=True)
        self._refresh_figure(preserve_view=True)

    @staticmethod
    def _point_segment_distance_2d(
            px: float,
            py: float,
            ax: float,
            ay: float,
            bx: float,
            by: float,
    ) -> float:
        dx = bx - ax
        dy = by - ay
        length_sq = dx * dx + dy * dy
        if length_sq <= 1.0e-12:
            return math.hypot(px - ax, py - ay)
        fraction = ((px - ax) * dx + (py - ay) * dy) / length_sq
        fraction = min(max(fraction, 0.0), 1.0)
        return math.hypot(px - (ax + fraction * dx), py - (ay + fraction * dy))

    @classmethod
    def _point_in_polygon_2d(cls, x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
        if len(polygon) < 3:
            return False
        inside = False
        previous = polygon[-1]
        for current in polygon:
            if cls._point_segment_distance_2d(x, y, previous[0], previous[1], current[0], current[1]) <= 4.0:
                return True
            x1, y1 = previous
            x2, y2 = current
            if (y1 > y) != (y2 > y):
                crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if x < crossing_x:
                    inside = not inside
            previous = current
        return inside

    def _normalise_cylinder_axial_coordinate(self, value: float, patch: dict[str, Any] | None = None) -> float:
        geometry = _popup_geometry_summary(self)
        length = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)
        coordinate = float(value)
        origin = str((patch or {}).get("axis_a_origin", "") or "").strip().lower()
        centered_origin = origin in {"center", "centered", "mid", "midspan", "middle"}
        if not centered_origin and patch is None:
            for candidate in getattr(self, "_custom_load_patches", ()) or ():
                candidate_origin = str(candidate.get("axis_a_origin", "") or "").strip().lower()
                if candidate_origin in {"center", "centered", "mid", "midspan", "middle"}:
                    centered_origin = True
                    break
        if not centered_origin and -0.5 * length - 1.0e-9 <= coordinate <= 0.5 * length + 1.0e-9 and coordinate < 0.0:
            centered_origin = True
        if centered_origin:
            coordinate += 0.5 * length
        return min(max(coordinate, 0.0), length)

    def _custom_load_patch_intervals(self, patch: dict[str, Any]) -> tuple[float, float, float, float]:
        min_a = _safe_float(patch.get("min_a"))
        max_a = _safe_float(patch.get("max_a"))
        min_b = _safe_float(patch.get("min_b"))
        max_b = _safe_float(patch.get("max_b"))
        if self.snapshot.is_cylinder:
            min_a = self._normalise_cylinder_axial_coordinate(min_a, patch)
            max_a = self._normalise_cylinder_axial_coordinate(max_a, patch)
        min_a, max_a = min(min_a, max_a), max(min_a, max_a)
        min_b, max_b = min(min_b, max_b), max(min_b, max_b)
        return min_a, max_a, min_b, max_b

    def _custom_load_patch_boundary_points(
            self,
            patch: dict[str, Any],
            surface_offset: float = 0.0,
    ) -> list[Point3D]:
        geometry = _popup_geometry_summary(self)
        min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(patch)

        if self.snapshot.is_cylinder:
            if geometry.get("is_cone"):
                base_radius = max(_safe_float(geometry.get("cone_r1_m"), 1.0), 1.0e-9)
                base_radius_top = max(_safe_float(geometry.get("cone_r2_m"), 1.0), 1.0e-9)
            else:
                base_radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-9)
                base_radius_top = base_radius

            cyl_len = max(_safe_float(geometry.get("length_m"), 1.0), 1.0e-9)

            def get_r(z_val):
                t = z_val / cyl_len if cyl_len > 0 else 0.0
                return base_radius + t * (base_radius_top - base_radius)

            theta_0 = min_b / base_radius
            theta_1 = max_b / base_radius
            arc_steps = max(2, int(math.ceil(abs(theta_1 - theta_0) / (math.pi / 24.0))))
            angles = [theta_0 + (theta_1 - theta_0) * index / arc_steps for index in range(arc_steps + 1)]

            r_lower = get_r(min_a) + surface_offset
            lower = [Point3D(r_lower * math.cos(theta), r_lower * math.sin(theta), min_a)
                     for theta in angles]

            r_upper = get_r(max_a) + surface_offset
            upper = [Point3D(r_upper * math.cos(theta), r_upper * math.sin(theta), max_a)
                     for theta in reversed(angles)]

            return lower + upper

        return [
            Point3D(min_a, min_b, surface_offset),
            Point3D(max_a, min_b, surface_offset),
            Point3D(max_a, max_b, surface_offset),
            Point3D(min_a, max_b, surface_offset),
        ]

    def _pick_custom_load_patch(
            self,
            canvas: Tkinter3DCanvas,
            screen_x: float,
            screen_y: float,
    ) -> int | None:
        if not self._custom_load_patches:
            return None

        best_index: int | None = None
        best_depth = float("inf")
        for index, patch in enumerate(self._custom_load_patches):
            projected = self._project_custom_load_points(
                canvas, self._custom_load_patch_boundary_points(patch)
            )
            projected_xy = [(x, y) for x, y, _depth in projected]
            if projected and self._point_in_polygon_2d(
                screen_x, screen_y, projected_xy
            ):
                mean_depth = sum(item[2] for item in projected) / len(projected)
                if mean_depth < best_depth:
                    best_depth = mean_depth
                    best_index = index
        return best_index

    @staticmethod
    def _inverse_projected_quad_fraction(
            projected: list[tuple[float, float]],
            screen_x: float,
            screen_y: float,
    ) -> tuple[float, float] | None:
        if len(projected) != 4:
            return None
        p0 = np.asarray(projected[0], dtype=float)
        p1 = np.asarray(projected[1], dtype=float)
        p2 = np.asarray(projected[2], dtype=float)
        p3 = np.asarray(projected[3], dtype=float)
        target = np.asarray([screen_x, screen_y], dtype=float)
        u = 0.5
        v = 0.5
        for _iteration in range(10):
            point = (1.0 - u) * (1.0 - v) * p0 + u * (1.0 - v) * p1 + u * v * p2 + (1.0 - u) * v * p3
            residual = point - target
            d_du = -(1.0 - v) * p0 + (1.0 - v) * p1 + v * p2 - v * p3
            d_dv = -(1.0 - u) * p0 - u * p1 + u * p2 + (1.0 - u) * p3
            jacobian = np.column_stack([d_du, d_dv])
            try:
                delta = np.linalg.solve(jacobian, residual)
            except Exception:
                return None
            u = min(max(u - float(delta[0]), -0.05), 1.05)
            v = min(max(v - float(delta[1]), -0.05), 1.05)
            if float(np.linalg.norm(delta)) < 1.0e-4:
                break
        return min(max(u, 0.0), 1.0), min(max(v, 0.0), 1.0)

    def _pick_mesh_refinement_point(
            self,
            canvas: Tkinter3DCanvas,
            screen_x: float,
            screen_y: float,
    ) -> tuple[float, float] | None:
        patch_index = self._pick_custom_load_patch(canvas, screen_x, screen_y)
        if patch_index is None or patch_index < 0 or patch_index >= len(self._custom_load_patches):
            return None
        patch = self._custom_load_patches[patch_index]
        min_a, max_a, min_b, max_b = self._custom_load_patch_intervals(patch)
        if self.snapshot.is_cylinder:
            return 0.5 * (min_a + max_a), 0.5 * (min_b + max_b)
        projected = self._project_custom_load_points(canvas, self._custom_load_patch_boundary_points(patch))
        projected_xy = [(x, y) for x, y, _depth in projected]
        uv = self._inverse_projected_quad_fraction(projected_xy, screen_x, screen_y)
        if uv is None:
            return 0.5 * (min_a + max_a), 0.5 * (min_b + max_b)
        u, v = uv
        return min_a + u * (max_a - min_a), min_b + v * (max_b - min_b)

    def _project_custom_load_points(
            self,
            canvas: Tkinter3DCanvas,
            points: list[Point3D],
    ) -> list[tuple[float, float, float]]:
        projector = getattr(canvas, "project_points", None)
        if callable(projector):
            projected = projector(points)
            if any(item is None for item in projected):
                return []
            return [
                (float(item[0]), float(item[1]), float(item[2]))
                for item in projected
            ]

        # Compatibility fallback for viewers without bulk point projection.
        plot_width, height = viewport_size(canvas)
        right, camera_up, forward = canvas.camera.basis()
        position = canvas.camera.position
        scale = 1.0 / math.tan(canvas.camera.fov / 2.0)
        aspect = plot_width / height
        x_scale = scale / aspect
        half_width = 0.5 * plot_width
        half_height = 0.5 * height
        projected: list[tuple[float, float, float]] = []
        for point in points:
            relative = point - position
            depth = relative.dot(forward)
            if depth <= canvas.camera.near or depth >= canvas.camera.far:
                return []
            camera_x = relative.dot(right)
            camera_y = relative.dot(camera_up)
            projected.append((
                (camera_x * x_scale / depth + 1.0) * half_width,
                (1.0 - camera_y * scale / depth) * half_height,
                float(depth),
            ))
        return projected

    def _custom_load_outline_edge_points(
            self,
            varying_axis: str,
            fixed_coordinate: float,
            start_coordinate: float,
            end_coordinate: float,
            surface_offset: float,
    ) -> list[Point3D]:
        # Convert one boundary segment in patch coordinates to 3D points.
        geometry = _popup_geometry_summary(self)
        start_coordinate = float(start_coordinate)
        end_coordinate = float(end_coordinate)
        fixed_coordinate = float(fixed_coordinate)

        if self.snapshot.is_cylinder:
            radius = max(_safe_float(geometry.get("radius_m"), 1.0), 1.0e-9)
            draw_radius = max(radius + surface_offset, 1.0e-9)
            if varying_axis == "a":
                start_coordinate = self._normalise_cylinder_axial_coordinate(start_coordinate)
                end_coordinate = self._normalise_cylinder_axial_coordinate(end_coordinate)
                theta = fixed_coordinate / radius
                return [
                    Point3D(
                        draw_radius * math.cos(theta),
                        draw_radius * math.sin(theta),
                        start_coordinate,
                    ),
                    Point3D(
                        draw_radius * math.cos(theta),
                        draw_radius * math.sin(theta),
                        end_coordinate,
                    ),
                ]

            fixed_coordinate = self._normalise_cylinder_axial_coordinate(fixed_coordinate)
            theta_0 = start_coordinate / radius
            theta_1 = end_coordinate / radius
            arc_steps = max(
                2,
                int(math.ceil(abs(theta_1 - theta_0) / (math.pi / 36.0))),
            )
            return [
                Point3D(
                    draw_radius * math.cos(
                        theta_0 + (theta_1 - theta_0) * index / arc_steps
                    ),
                    draw_radius * math.sin(
                        theta_0 + (theta_1 - theta_0) * index / arc_steps
                    ),
                    fixed_coordinate,
                )
                for index in range(arc_steps + 1)
            ]

        if varying_axis == "a":
            return [
                Point3D(start_coordinate, fixed_coordinate, surface_offset),
                Point3D(end_coordinate, fixed_coordinate, surface_offset),
            ]
        return [
            Point3D(fixed_coordinate, start_coordinate, surface_offset),
            Point3D(fixed_coordinate, end_coordinate, surface_offset),
        ]

    @staticmethod
    def _custom_load_edge_key(
            varying_axis: str,
            fixed_coordinate: float,
            start_coordinate: float,
            end_coordinate: float,
    ) -> tuple[str, float, float, float]:
        start = float(start_coordinate)
        end = float(end_coordinate)
        if end < start:
            start, end = end, start
        return (
            str(varying_axis).lower(),
            round(float(fixed_coordinate), 10),
            round(start, 10),
            round(end, 10),
        )

    @staticmethod
    def _custom_load_edge_payload_from_key(
            key: tuple[str, float, float, float],
    ) -> dict[str, float | str]:
        return {
            "varying_axis": key[0],
            "fixed_coordinate": float(key[1]),
            "start_coordinate": float(key[2]),
            "end_coordinate": float(key[3]),
        }

    def _all_custom_load_edges(self) -> list[tuple[str, float, float, float]]:
        edges: dict[tuple[str, float, float, float], tuple[str, float, float, float]] = {}
        for patch in getattr(self, "_custom_load_patches", ()):
            min_a = _safe_float(patch.get("min_a"))
            max_a = _safe_float(patch.get("max_a"))
            min_b = _safe_float(patch.get("min_b"))
            max_b = _safe_float(patch.get("max_b"))
            candidates = (
                ("a", min_b, min_a, max_a),
                ("a", max_b, min_a, max_a),
                ("b", min_a, min_b, max_b),
                ("b", max_a, min_b, max_b),
            )
            for candidate in candidates:
                key = self._custom_load_edge_key(*candidate)
                edges[key] = candidate
        return [edges[key] for key in sorted(edges)]

    def _selected_custom_load_edges(self) -> list[dict[str, float | str]]:
        all_keys = {self._custom_load_edge_key(*edge) for edge in self._all_custom_load_edges()}
        self._custom_selected_edge_keys.intersection_update(all_keys)
        return [
            self._custom_load_edge_payload_from_key(key)
            for key in sorted(self._custom_selected_edge_keys)
        ]

    def _custom_load_selection_visual_offset(self) -> float:
        geometry = _popup_geometry_summary(self)
        side_var = getattr(self, "pressure_direction", None)
        side_value = side_var.get() if side_var is not None and hasattr(side_var, "get") else "front"
        side_sign = _pressure_surface_sign(side_value)
        if self.snapshot.is_cylinder:
            return side_sign * max(_safe_float(geometry.get("radius_m"), 1.0) * 2.0e-3, 2.0e-4)
        return side_sign * max(
            _safe_float(geometry.get("length_m"), 1.0),
            _safe_float(geometry.get("width_m"), 1.0),
        ) * 2.0e-4

    def _pick_custom_load_edge(
            self,
            canvas: Tkinter3DCanvas,
            screen_x: float,
            screen_y: float,
    ) -> tuple[str, float, float, float] | None:
        best_edge: tuple[str, float, float, float] | None = None
        best_distance = 9.0
        best_depth = float("inf")
        surface_offset = self._custom_load_selection_visual_offset()
        for edge in self._all_custom_load_edges():
            points = self._custom_load_outline_edge_points(*edge, surface_offset=surface_offset)
            projected = self._project_custom_load_points(canvas, points)
            if len(projected) < 2:
                continue
            min_distance = min(
                self._point_segment_distance_2d(
                    screen_x,
                    screen_y,
                    projected[index][0],
                    projected[index][1],
                    projected[index + 1][0],
                    projected[index + 1][1],
                )
                for index in range(len(projected) - 1)
            )
            mean_depth = sum(item[2] for item in projected) / len(projected)
            if min_distance <= best_distance and mean_depth < best_depth:
                best_distance = min_distance
                best_depth = mean_depth
                best_edge = edge
        return best_edge

    def _selected_custom_load_boundary_edges(
            self,
    ) -> list[tuple[str, float, float, float]]:
        # Return only the external boundary of the combined selected patch area.
        selected_patches = [
            patch
            for patch in self._custom_load_patches
            if bool(patch.get("selected", False))
        ]
        if not selected_patches:
            return []

        tolerance_digits = 10

        def clean(value: Any) -> float:
            return round(_safe_float(value), tolerance_digits)

        a_values = sorted(
            {
                clean(patch.get(key))
                for patch in self._custom_load_patches
                for key in ("min_a", "max_a")
            }
        )
        b_values = sorted(
            {
                clean(patch.get(key))
                for patch in self._custom_load_patches
                for key in ("min_b", "max_b")
            }
        )
        if len(a_values) < 2 or len(b_values) < 2:
            return []

        selected_cells: set[tuple[int, int]] = set()
        for index_a in range(len(a_values) - 1):
            mid_a = 0.5 * (a_values[index_a] + a_values[index_a + 1])
            for index_b in range(len(b_values) - 1):
                mid_b = 0.5 * (b_values[index_b] + b_values[index_b + 1])
                for patch in selected_patches:
                    if (
                            _safe_float(patch.get("min_a")) - 1.0e-9
                            <= mid_a
                            <= _safe_float(patch.get("max_a")) + 1.0e-9
                            and _safe_float(patch.get("min_b")) - 1.0e-9
                            <= mid_b
                            <= _safe_float(patch.get("max_b")) + 1.0e-9
                    ):
                        selected_cells.add((index_a, index_b))
                        break

        is_cylinder = bool(self.snapshot.is_cylinder)
        number_b_cells = len(b_values) - 1
        edges: list[tuple[str, float, float, float]] = []

        for index_a, index_b in sorted(selected_cells):
            a_0 = a_values[index_a]
            a_1 = a_values[index_a + 1]
            b_0 = b_values[index_b]
            b_1 = b_values[index_b + 1]

            below = (index_a - 1, index_b)
            above = (index_a + 1, index_b)
            left_b = (
                index_a,
                (index_b - 1) % number_b_cells
                if is_cylinder
                else index_b - 1,
            )
            right_b = (
                index_a,
                (index_b + 1) % number_b_cells
                if is_cylinder
                else index_b + 1,
            )

            if below not in selected_cells:
                edges.append(("b", a_0, b_0, b_1))
            if above not in selected_cells:
                edges.append(("b", a_1, b_0, b_1))
            if left_b not in selected_cells:
                edges.append(("a", b_0, a_0, a_1))
            if right_b not in selected_cells:
                edges.append(("a", b_1, a_0, a_1))

        return edges

    def _draw_custom_load_patch_outlines(self, canvas: Tkinter3DCanvas) -> None:
        # Draw selectable panels, selected perimeter and user-created cuts.
        if not self._custom_load_patches:
            return

        surface_offset = self._custom_load_selection_visual_offset()

        if self._custom_load_selection_active:
            for patch in self._custom_load_patches:
                points = self._custom_load_patch_boundary_points(
                    patch,
                    surface_offset=surface_offset,
                )
                if len(points) < 2:
                    continue
                for start, end in zip(points, points[1:] + points[:1]):
                    canvas.add_line(
                        start,
                        end,
                        color="#94a3b8",
                        width=1,
                        draw_overlay=True,
                    )

        for varying_axis, fixed_coordinate, start_coordinate, end_coordinate in (
                self._selected_custom_load_boundary_edges()
        ):
            points = self._custom_load_outline_edge_points(
                varying_axis,
                fixed_coordinate,
                start_coordinate,
                end_coordinate,
                surface_offset,
            )
            for start, end in zip(points, points[1:]):
                canvas.add_line(
                    start,
                    end,
                    color="#dc2626",
                    width=4,
                    draw_overlay=True,
                )

        for edge in self._selected_custom_load_edges():
            points = self._custom_load_outline_edge_points(
                str(edge.get("varying_axis", "a")),
                _safe_float(edge.get("fixed_coordinate")),
                _safe_float(edge.get("start_coordinate")),
                _safe_float(edge.get("end_coordinate")),
                surface_offset,
            )
            for start, end in zip(points, points[1:]):
                canvas.add_line(
                    start,
                    end,
                    color="#16a34a",
                    width=4,
                    draw_overlay=True,
                )

        for cut in getattr(self, "_custom_load_manual_cuts", ()):
            points = self._custom_load_outline_edge_points(
                str(cut.get("varying_axis", "a")),
                _safe_float(cut.get("fixed_coordinate")),
                _safe_float(cut.get("start_coordinate")),
                _safe_float(cut.get("end_coordinate")),
                surface_offset,
            )
            for start, end in zip(points, points[1:]):
                canvas.add_line(
                    start,
                    end,
                    color="#f59e0b",
                    width=3,
                    draw_overlay=True,
                )

    def _custom_load_select_all(self) -> None:
        if not hasattr(self, "_custom_load_patches"): return
        for f in self._custom_load_patches: f["selected"] = True
        self._update_custom_load_summary()
        self._refresh_figure()

    def _custom_load_clear_all(self) -> None:
        # Remove the selection and restore the unsplit default panel layout.
        self._custom_load_manual_cuts.clear()
        self._custom_selected_edge_keys.clear()
        self._generate_default_custom_load_patches()
        self._custom_load_selected_index = -1
        self._display_base_geometry = True
        self._force_fit_next_refresh = False
        self._update_custom_load_summary()
        self._write_status(
            "Custom load selection and all manually created panel cuts were cleared.",
            keep_run_results=True,
        )
        self._refresh_figure(preserve_view=True)

    def _custom_load_split_field(self, axis: str) -> None:
        # Split the active selected panel exactly at its local midpoint.
        if not self._custom_load_patches:
            return
        if (
                self._custom_load_selected_index < 0
                or self._custom_load_selected_index >= len(self._custom_load_patches)
        ):
            self._write_status(
                "Select a custom load panel before using Split A or Split B.",
                keep_run_results=True,
            )
            return

        field = self._custom_load_patches[self._custom_load_selected_index]
        if not bool(field.get("selected", False)):
            self._write_status(
                "The active panel is not selected. Select it before cutting.",
                keep_run_results=True,
            )
            return

        axis = str(axis).lower()
        min_a = _safe_float(field.get("min_a"))
        max_a = _safe_float(field.get("max_a"))
        min_b = _safe_float(field.get("min_b"))
        max_b = _safe_float(field.get("max_b"))

        if axis == "a":
            split_coordinate = 0.5 * (min_a + max_a)
            first = dict(field)
            first["max_a"] = split_coordinate
            second = dict(field)
            second["min_a"] = split_coordinate
            cut = {
                "varying_axis": "b",
                "fixed_coordinate": split_coordinate,
                "start_coordinate": min_b,
                "end_coordinate": max_b,
            }
            direction_label = "A"
        elif axis == "b":
            split_coordinate = 0.5 * (min_b + max_b)
            first = dict(field)
            first["max_b"] = split_coordinate
            second = dict(field)
            second["min_b"] = split_coordinate
            cut = {
                "varying_axis": "a",
                "fixed_coordinate": split_coordinate,
                "start_coordinate": min_a,
                "end_coordinate": max_a,
            }
            direction_label = "B"
        else:
            raise ValueError(f"Unknown custom load split axis: {axis!r}")

        cut_key = (
            str(cut["varying_axis"]),
            round(float(cut["fixed_coordinate"]), 10),
            round(float(cut["start_coordinate"]), 10),
            round(float(cut["end_coordinate"]), 10),
        )
        existing_keys = {
            (
                str(item.get("varying_axis", "")),
                round(_safe_float(item.get("fixed_coordinate")), 10),
                round(_safe_float(item.get("start_coordinate")), 10),
                round(_safe_float(item.get("end_coordinate")), 10),
            )
            for item in getattr(self, "_custom_load_manual_cuts", ())
        }
        if cut_key not in existing_keys:
            self._custom_load_manual_cuts.append(cut)

        index = self._custom_load_selected_index
        self._custom_load_patches[index:index + 1] = [first, second]
        self._custom_load_selected_index = index
        self._display_base_geometry = True
        self._force_fit_next_refresh = False
        self._update_custom_load_summary()
        self._write_status(
            f"Selected custom load panel was split in local {direction_label} "
            "at its midpoint. Press Clear to remove all cuts.",
            keep_run_results=True,
        )
        self._refresh_figure(preserve_view=True)

    def _update_custom_load_summary(self) -> None:
        if not hasattr(self, "_custom_load_patches"): return
        total = 0.0
        for f in self._custom_load_patches:
            if f.get("selected", False):
                total += (f["max_a"] - f["min_a"]) * (f["max_b"] - f["min_b"])
        if hasattr(self, "custom_load_area_var") and self.custom_load_area_var is not None:
            self.custom_load_area_var.set(f"Selected Area: {total:.3f} m2")
        self._sync_custom_load_payloads()

    def _generate_default_custom_load_patches(self) -> None:
        geometry = _popup_geometry_summary(self)
        is_cylinder = str(geometry.get("geometry", "")).lower() == "cylinder"
        if is_cylinder:
            length = max(float(geometry.get("length_m") or 1.0), 1.0e-6)
            min_a = -0.5 * length
            max_a = 0.5 * length
            radius = max(float(geometry.get("radius_m") or 1.0), 1.0e-6)
            circumference = 2.0 * math.pi * radius
            min_b = 0.0
            max_b = circumference
        else:
            min_a = 0.0
            max_a = max(float(geometry.get("length_m") or 1.0), 1.0e-6)
            min_b = 0.0
            max_b = max(float(geometry.get("width_m") or 1.0), 1.0e-6)

        a_breaks = [min_a, max_a]
        b_breaks = [min_b, max_b]

        if is_cylinder:
            if geometry.get("has_girder"):
                girder_spacing = float(geometry.get("girder_spacing_m") or 0.0)
                if girder_spacing > 0.0:
                    for pos in representation_geometry.centered_member_positions(
                            max_a - min_a, girder_spacing, fallback_midpoint=True
                    ):
                        a_breaks.append(min_a + pos)
            stiffener_spacing = float(geometry.get("stiffener_spacing_m") or 0.0)
            if geometry.get("has_stiffener") and stiffener_spacing > 0.0:
                circumferential_bays = max(1, int((max_b - min_b) / stiffener_spacing))
            else:
                circumferential_bays = 16
            b_breaks = [
                min_b + (max_b - min_b) * index / circumferential_bays
                for index in range(circumferential_bays + 1)
            ]
        else:
            if geometry.get("has_girder"):
                girder_spacing = float(geometry.get("girder_spacing_m") or 0.0)
                if girder_spacing > 0.0:
                    for pos in representation_geometry.centered_member_positions(
                            max_a - min_a, girder_spacing, fallback_midpoint=True
                    ):
                        a_breaks.append(min_a + pos)

            if geometry.get("has_stiffener"):
                stiffener_spacing = float(geometry.get("stiffener_spacing_m") or 0.0)
                if stiffener_spacing > 0.0:
                    for pos in representation_geometry.centered_member_positions(
                            max_b - min_b, stiffener_spacing, fallback_midpoint=True
                    ):
                        b_breaks.append(min_b + pos)

        a_breaks = sorted(set(a_breaks))
        b_breaks = sorted(set(b_breaks))

        self._custom_load_patches = []
        self._custom_load_selected_index = -1
        for index_a in range(len(a_breaks) - 1):
            for index_b in range(len(b_breaks) - 1):
                patch = {
                    "min_a": a_breaks[index_a],
                    "max_a": a_breaks[index_a + 1],
                    "min_b": b_breaks[index_b],
                    "max_b": b_breaks[index_b + 1],
                    "selected": False,
                }
                if is_cylinder:
                    patch["axis_a_origin"] = "centered"
                self._custom_load_patches.append(patch)
        self._update_custom_load_summary()

    def _redraw_base_3d(self) -> None:
        self._display_base_geometry = True
        self._force_fit_next_refresh = True
        self._refresh_figure()
        self._write_status("Displaying base 3D model geometry.", keep_run_results=True)

    def _show_results(self) -> None:
        if self.current_result is None:
            messagebox.showinfo("FEM results", "No solver results are available yet. Run FEM first.")
            return
        self._display_base_geometry = False
        self._set_custom_load_selection_active(False, refresh=False)
        self._force_fit_next_refresh = True
        self._refresh_figure()
        self._write_status("Displaying the latest FEM results.", keep_run_results=True)

    def _set_runtime_3d_view(self, view_name: str) -> None:
        self.use_interactive_3d.set(True)
        if self.result_canvas is None:
            self._force_fit_next_refresh = True
            self._refresh_figure(preserve_view=False)
        canvas = self.result_canvas
        if canvas is None:
            return
        view = str(view_name).lower()
        if view == "fit":
            canvas.fit_to_scene()
        elif view == "reset":
            canvas.reset_camera()
        elif view == "iso":
            canvas.set_iso_view()
        elif view == "front":
            canvas.set_front_view()
        elif view == "side":
            canvas.set_side_view()
        elif view == "top":
            canvas.set_top_view()
        else:
            return
        self._write_status("3D view set to " + view + ".", keep_run_results=True)


def open_runtime_fem_window(parent: Any, app: Any, imported_fem_model=None,
                            imported_path=None) -> RuntimeFEMWindow | None:
    """Open the experimental runtime FEM popup for the app active line, or a direct FEM import."""

    try:
        return RuntimeFEMWindow(parent, app, imported_fem_model=imported_fem_model, imported_path=imported_path)
    except Exception as error:
        messagebox.showinfo("Experimental FEM solver", str(error))
        return None


class _ExamplePlate:
    girder_lg = 10.0

    def get_structure_type(self):
        return "Flat plate, stiffened with girder"

    def get_span(self):
        return 3.5

    def get_s(self):
        return 0.75

    def get_pl_thk(self):
        return 0.018

    def get_puls_up_boundary(self):
        return "SSSS"


class _ExampleTMember:
    stiffener_type = "T"

    def __init__(self, spacing: float, web_h: float, web_t: float, flange_w: float, flange_t: float):
        self.spacing = spacing
        self.hw = web_h
        self.tw = web_t
        self.b = flange_w
        self.tf = flange_t
        self.girder_lg = 10.0

    def get_s(self):
        return self.spacing

    def get_web_h(self):
        return self.hw

    def get_web_thk(self):
        return self.tw

    def get_fl_w(self):
        return self.b

    def get_fl_thk(self):
        return self.tf

    def get_stiffener_type(self):
        return self.stiffener_type


class _ExampleAllStructure:
    Plate = _ExamplePlate()
    Stiffener = _ExampleTMember(spacing=0.75, web_h=0.400, web_t=0.012, flange_w=0.250, flange_t=0.012)
    Girder = _ExampleTMember(spacing=3.5, web_h=0.800, web_t=0.020, flange_w=0.200, flange_t=0.030)
    _panel_length_Lp = 10.0


class _ExampleShell:
    radius = 2.0
    length_of_shell = 8.0
    tot_cyl_length = 8.0
    thk = 0.012
    cone_r1 = None
    cone_r2 = None
    cone_length = None
    _dist_between_rings = 2.0


class _ExampleLongitudinalStiffener:
    stiffener_type = "FB"
    spacing = 0.5
    hw = 0.150
    tw = 0.010
    b = 0.0
    tf = 0.0


class _ExampleRingGirder:
    stiffener_type = "T"
    hw = 0.400
    tw = 0.010
    b = 0.150
    tf = 0.020


class _ExampleCylinder:
    geometry = 7
    ShellObj = _ExampleShell()
    LongStfObj = _ExampleLongitudinalStiffener()
    RingStfObj = None
    RingFrameObj = _ExampleRingGirder()
    length_between_girders = 4.0


class _ExampleTkVariable:
    def __init__(self, value: Any):
        self.value = value

    def get(self) -> Any:
        return self.value

    def set(self, value: Any) -> None:
        self.value = value


class _ExampleRuntimeApp:
    _general_color = "#f0f0f0"
    _active_line = "line_example"
    _line_is_active = True
    _line_dict = {"line_example": [1, 2]}
    _simplified_calculation_mode = True

    def __init__(self, example: str = "girder_panel"):
        # RuntimeFEMWindow registers with the owning application so renderer
        # changes can be coordinated across every live viewer.  The standalone
        # example delegates that hook to Application through __getattr__, so it
        # needs the same registry as the real application.
        self._runtime_fem_windows = weakref.WeakSet()
        self.example = "cylinder" if str(example).lower() == "cylinder" else "girder_panel"
        cylinder = _ExampleCylinder() if self.example == "cylinder" else None
        self._fem_default_top_bottom_moment_nm = 30_000_000.0 if self.example == "cylinder" else 0.0
        self._line_to_struc = {"line_example": [_ExampleAllStructure(), None, None, object(), None, cylinder]}
        self._new_prop_3d_opposite_side = _ExampleTkVariable(False)
        self._new_shell_ring_frame_length_between_girders = _ExampleTkVariable(4.0)
        self._new_shell_dist_rings = _ExampleTkVariable(2.0)
        self._new_panel_length_Lp = _ExampleTkVariable(10_000.0)
        self._new_girder_length_LG = _ExampleTkVariable(10_000.0)

    def __getattr__(self, name: str) -> Any:
        try:
            from anystruct.main_application import Application
        except ModuleNotFoundError:
            from ANYstructure.anystruct.main_application import Application
        descriptor = Application.__dict__.get(name)
        if isinstance(descriptor, staticmethod):
            return descriptor.__func__
        if isinstance(descriptor, classmethod):
            return types.MethodType(descriptor.__func__, Application)
        attr = getattr(Application, name)
        if callable(attr):
            return types.MethodType(attr, self)
        return attr

    def get_highest_pressure(self, line):
        if line != self._active_line:
            return {"normal": 0.0}
        return {"normal": 100_000.0 if self.example == "cylinder" else 459_639.0}


def example_runtime_app(example: str = "girder_panel") -> _ExampleRuntimeApp:
    """Return a tiny active-line app fixture for running this module directly."""

    return _ExampleRuntimeApp(example)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the standalone experimental ANYstructure FEM window.")
    parser.add_argument(
        "--example",
        choices=("girder_panel", "cylinder"),
        default="cylinder",
        help="Standalone example to open. Default is the flat stiffened girder panel.",
    )
    args = parser.parse_args()
    root = tk.Tk()
    my_app = RuntimeFEMWindow(root, example_runtime_app(args.example), use_parent_as_window=True)
    my_app.window.protocol("WM_DELETE_WINDOW", root.destroy)
    my_app.window.focus_force()
    root.mainloop()
