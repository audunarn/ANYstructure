"""Experimental runtime FEM solver window for active ANYstructure lines.

The module owns the active-line handoff, user options and result visualization
for the experimental full-geometry FEM mode.  It calls the ANYstructure-local
``anystruct.fe_solver`` module; solver development happens in ANYintelligent
and can later be copied into that local module without changing this GUI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import queue
import math
import os
import sys
import threading
import types

import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

from matplotlib import cm, colormaps, colors as mcolors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from anystruct import fe_solver
except ModuleNotFoundError:
    from ANYstructure.anystruct import fe_solver


@dataclass(frozen=True)
class RuntimeFEMLineSnapshot:
    """Minimal active-line payload passed from ANYstructure to the runtime FEM UI."""

    line_name: str
    line_points: Any
    structure_bundle: Any
    pressure_pa: float = 0.0
    domain: str = ""
    is_cylinder: bool = False
    diagnostics: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuntimeFEMOptions:
    """User-selected runtime FEM options from the popup."""

    mesh_fidelity: str = "coarse"
    pressure_pa: float = 0.0
    load_scale: float = 1.0
    include_stiffeners: bool = True
    include_girders: bool = True
    num_buckling_modes: int = 5
    mesh_size_m: float = 0.0
    top_bottom_moment_nm: float = 0.0


@dataclass(frozen=True)
class RuntimeFEMRunResult:
    """Structured runtime FEM result used by text and Matplotlib visualization."""

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


def _mm_or_m_to_m(value: Any, default: float = 0.0) -> float:
    number = _safe_float(value, default)
    if number <= 0.0:
        return default
    return number / 1000.0 if number > 1.0 else number


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
    if stiffener_type in {"T", "TEE", "T-BAR"} and height > 0.0 and thickness > 0.0 and flange_width > 0.0 and flange_thickness > 0.0:
        web_area = height * thickness
        flange_area = flange_width * flange_thickness
        area = web_area + flange_area
        web_y = 0.5 * height
        flange_y = height + 0.5 * flange_thickness
        centroid = (web_area * web_y + flange_area * flange_y) / area
        iy = thickness * height**3 / 12.0 + web_area * (web_y - centroid) ** 2
        iy += flange_width * flange_thickness**3 / 12.0 + flange_area * (flange_y - centroid) ** 2
        iz = height * thickness**3 / 12.0 + flange_thickness * flange_width**3 / 12.0
        return {
            "area": area,
            "Iy": max(iy, 1.0e-12),
            "Iz": max(iz, 1.0e-12),
            "J": max(iy + iz, 1.0e-12),
            "shear_factor_y": 5.0 / 6.0,
            "shear_factor_z": 5.0 / 6.0,
            "label": "T" + str(round(height * 1000.0)) + "x" + str(round(thickness * 1000.0))
            + "+" + str(round(flange_width * 1000.0)) + "x" + str(round(flange_thickness * 1000.0)),
        }

    if stiffener_type not in {"FB", "FLAT", "FLATBAR", "FLAT BAR"} and not (height > 0.0 and thickness > 0.0):
        return None
    if height <= 0.0 or thickness <= 0.0:
        return None

    area = height * thickness
    iy = thickness * height**3 / 12.0
    iz = height * thickness**3 / 12.0
    return {
        "area": area,
        "Iy": max(iy, 1.0e-12),
        "Iz": max(iz, 1.0e-12),
        "J": max(iy + iz, 1.0e-12),
        "shear_factor_y": 5.0 / 6.0,
        "shear_factor_z": 5.0 / 6.0,
        "label": "FB" + str(round(height * 1000.0)) + "x" + str(round(thickness * 1000.0)),
    }


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

    return RuntimeFEMLineSnapshot(
        line_name=active_line,
        line_points=line_dict[active_line],
        structure_bundle=bundle,
        pressure_pa=pressure,
        domain=domain,
        is_cylinder=cylinder_obj is not None,
        diagnostics=tuple(diagnostics),
    )


def _flat_geometry_summary(snapshot: RuntimeFEMLineSnapshot) -> dict[str, Any]:
    bundle = snapshot.structure_bundle
    all_obj = bundle[0] if bundle and len(bundle) > 0 else None
    plate = getattr(all_obj, "Plate", None)
    stiffener = getattr(all_obj, "Stiffener", None)
    girder = getattr(all_obj, "Girder", None)
    return {
        "geometry": "flat panel",
        "length_m": _safe_float(_read_attr_or_call(plate, "get_span", "span"), 1.0),
        "width_m": _safe_float(_read_attr_or_call(plate, "get_s", default=None), 1.0),
        "thickness_m": _safe_float(_read_attr_or_call(plate, "get_pl_thk", default=None), 0.0),
        "has_stiffener": stiffener is not None,
        "has_girder": girder is not None,
        "stiffener_spacing_m": _safe_float(_read_attr_or_call(plate, "get_s", default=None), 0.0),
        "girder_spacing_m": _safe_float(_read_attr_or_call(girder, "get_s", "spacing", "s", default=None), 0.0),
    }


def _cylinder_geometry_summary(snapshot: RuntimeFEMLineSnapshot) -> dict[str, Any]:
    bundle = snapshot.structure_bundle
    cyl_obj = bundle[5] if bundle and len(bundle) > 5 else None
    shell = getattr(cyl_obj, "ShellObj", None)
    stiffener = getattr(cyl_obj, "LongStfObj", None)
    girder = getattr(cyl_obj, "RingFrameObj", None)
    return {
        "geometry": "cylinder",
        "radius_m": _safe_float(_read_attr_or_call(shell, "radius", default=None), 1.0),
        "length_m": _safe_float(_read_attr_or_call(shell, "length_of_shell", "tot_cyl_length", default=None), 1.0),
        "thickness_m": _safe_float(_read_attr_or_call(shell, "thk", default=None), 0.0),
        "has_stiffener": stiffener is not None,
        "has_girder": girder is not None,
        "stiffener_spacing_m": _safe_float(_read_attr_or_call(stiffener, "get_s", "spacing", "s", default=None), 0.0),
        "ring_spacing_m": _safe_float(_read_attr_or_call(shell, "_dist_between_rings", "dist_between_rings", default=None), 0.0),
        "girder_spacing_m": _safe_float(_read_attr_or_call(cyl_obj, "length_between_girders", default=None), 0.0),
        "stiffener_section": _member_section(stiffener),
        "girder_section": _member_section(girder),
    }


def runtime_geometry_summary(snapshot: RuntimeFEMLineSnapshot) -> dict[str, Any]:
    """Return compact geometry metadata for plotting and future solver handoff."""

    if snapshot.is_cylinder:
        return _cylinder_geometry_summary(snapshot)
    return _flat_geometry_summary(snapshot)


def run_runtime_fem(snapshot: RuntimeFEMLineSnapshot, options: RuntimeFEMOptions) -> RuntimeFEMRunResult:
    """Run the ANYstructure-owned lightweight FEM solver."""

    geometry = runtime_geometry_summary(snapshot)
    diagnostics = list(snapshot.diagnostics)
    solver_config = fe_solver.LightweightFEMConfig(
        mesh_fidelity=options.mesh_fidelity,
        pressure_pa=options.pressure_pa,
        load_scale=options.load_scale,
        include_stiffeners=options.include_stiffeners,
        include_girders=options.include_girders,
        num_buckling_modes=options.num_buckling_modes,
        mesh_size_m=options.mesh_size_m,
        top_bottom_moment_nm=options.top_bottom_moment_nm,
    )
    if fe_solver.full_backend_available():
        solver_result = fe_solver.run_production_fem(geometry, solver_config)
        if solver_result.status in {"backend_unavailable", "invalid", "static_failed", "production_failed"}:
            fallback = fe_solver.run_lightweight_fem(geometry, solver_config)
            diagnostics.extend(solver_result.diagnostics)
            diagnostics.append("Production FE mesh failed; using compact fallback result.")
            solver_result = fallback
    else:
        solver_result = fe_solver.run_lightweight_fem(geometry, solver_config)
    diagnostics.extend(solver_result.diagnostics)

    summary = {
        **geometry,
        "line": snapshot.line_name,
        "mesh_fidelity": options.mesh_fidelity,
        "pressure_pa": float(options.pressure_pa) * float(options.load_scale),
        "include_stiffeners": bool(options.include_stiffeners),
        "include_girders": bool(options.include_girders),
        "num_buckling_modes": int(options.num_buckling_modes),
        "mesh_size_m": float(options.mesh_size_m),
        "top_bottom_moment_nm": float(options.top_bottom_moment_nm),
        "solver": solver_result.solver_name,
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


def _surface_facecolors(values_grid: list[list[float]]):
    values = _all_grid_values(values_grid) or [0.0]
    norm = mcolors.Normalize(vmin=min(values), vmax=max(values) if max(values) > min(values) else min(values) + 1.0)
    cmap = colormaps["jet"]
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
) -> float:
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


def _buckling_mode_shapes(result: RuntimeFEMRunResult | None) -> list[dict[str, Any]]:
    if result is None:
        return []
    return list((result.visualization or {}).get("buckling_modes") or [])


def _selected_visualization(result: RuntimeFEMRunResult, display_mode: str) -> tuple[dict[str, Any], str, bool]:
    if display_mode.startswith("mode:"):
        try:
            mode_number = int(display_mode.split(":", 1)[1])
        except (IndexError, ValueError):
            mode_number = -1
        for mode in _buckling_mode_shapes(result):
            if int(mode.get("mode_number", -1)) == mode_number:
                factor = _safe_float(mode.get("load_factor"))
                title = "Buckling mode " + str(mode_number) + "  LF=" + str(round(factor, 4))
                return dict(mode.get("shape") or {}), title, True
    return dict(result.visualization or {}), "Static stress/displacement", False


def _plot_visualization_surface(
    figure: Figure,
    axis: Any,
    geometry: dict[str, Any],
    result: RuntimeFEMRunResult,
    display_mode: str = "static",
) -> None:
    visualization, title, is_mode = _selected_visualization(result, display_mode)
    scalar_values = _plot_grid_values(visualization.get("stress_pa"))
    if is_mode:
        color_grid = scalar_values
        colorbar_label = str(visualization.get("scalar_label") or "mode amplitude")
    else:
        color_grid = [[value / 1.0e6 for value in row] for row in scalar_values]
        colorbar_label = "stress [MPa]"
    facecolors, norm, cmap = _surface_facecolors(color_grid)
    scale = _displacement_plot_scale(geometry, result, visualization)

    if visualization.get("type") == "cylinder":
        axial = _plot_grid_values(visualization.get("axial_m"))
        theta = _plot_grid_values(visualization.get("theta_rad"))
        radial_displacement = _plot_grid_values(visualization.get("radial_displacement_m"))
        radius = max(_safe_float(visualization.get("radius_m"), _safe_float(geometry.get("radius_m"), 1.0)), 1.0e-9)
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
        axis.plot_surface(
            np.asarray(x),
            np.asarray(y),
            np.asarray(axial),
            facecolors=np.asarray(facecolors),
            linewidth=0.15,
            antialiased=True,
            shade=False,
        )
        axis.set_xlabel("x [m]")
        axis.set_ylabel("y [m]")
        axis.set_zlabel("height [m]")
        _set_3d_axes_limits(axis, x, y, axial)
        try:
            axis.view_init(elev=18.0, azim=-45.0)
        except Exception:
            pass
    else:
        x = _plot_grid_values(visualization.get("x_m"))
        y = _plot_grid_values(visualization.get("y_m"))
        w = _plot_grid_values(visualization.get("w_m"))
        z = [[value * scale for value in row] for row in w]
        axis.plot_surface(
            np.asarray(x),
            np.asarray(y),
            np.asarray(z),
            facecolors=np.asarray(facecolors),
            linewidth=0.15,
            antialiased=True,
            shade=False,
        )
        axis.set_xlabel("length [m]")
        axis.set_ylabel("width [m]")
        axis.set_zlabel("w x" + str(round(scale, 1)))
        _set_3d_axes_limits(axis, x, y, z)

    axis.set_title(title)
    mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array(_all_grid_values(color_grid))
    figure.colorbar(mappable, ax=axis, shrink=0.68, pad=0.1, label=colorbar_label)


def create_runtime_fem_result_figure(
    snapshot: RuntimeFEMLineSnapshot,
    result: RuntimeFEMRunResult | None = None,
    display_mode: str = "static",
) -> Figure:
    """Create the Matplotlib result visualization used in the runtime popup."""

    figure = Figure(figsize=(8.0, 4.1), dpi=100)
    geometry_ax = figure.add_subplot(121, projection="3d")
    result_ax = figure.add_subplot(122)
    geometry = runtime_geometry_summary(snapshot) if result is None else result.summary

    if result is None or not result.visualization:
        geometry_ax.set_title("Static stress/displacement")
        geometry_ax.text2D(0.08, 0.56, "Run FEM to plot stresses and displacements.", transform=geometry_ax.transAxes)
        geometry_ax.set_xlabel("length [m]")
        geometry_ax.set_ylabel("width/radius [m]")
        geometry_ax.set_zlabel("displacement")
        result_ax.text(0.5, 0.55, "No FEM run yet", ha="center", va="center", fontsize=12)
        result_ax.text(0.5, 0.42, "Results will appear here after Run FEM.", ha="center", va="center", fontsize=9)
        result_ax.set_axis_off()
    else:
        _plot_visualization_surface(figure, geometry_ax, geometry, result, display_mode)
        result_ax.set_title("Buckling modes")
        result_ax.set_axis_off()
        summary_lines = [
            "status: " + result.status.replace("_", " "),
            "solver: " + str(geometry.get("solver", "")),
            "max disp [mm]: " + str(round(1000.0 * _safe_float(geometry.get("max_displacement_m")), 4)),
        ]
        for label, value in result.stress_percentiles:
            summary_lines.append(label + " stress [MPa]: " + str(round(value / 1.0e6, 3)))
        result_ax.text(0.02, 0.98, "\n".join(summary_lines), transform=result_ax.transAxes,
                       ha="left", va="top", fontsize=9)
        if result.buckling_factors:
            rows = [
                [str(index), str(round(factor, 4))]
                for index, factor in enumerate(result.buckling_factors, start=1)
            ]
        else:
            rows = [["-", "No positive modes"]]
        table = result_ax.table(
            cellText=rows,
            colLabels=["Mode", "Load factor"],
            cellLoc="center",
            colLoc="center",
            bbox=[0.02, 0.08, 0.76, 0.58],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        for index in range(1, len(rows) + 1):
            if display_mode == "mode:" + rows[index - 1][0]:
                for col in range(2):
                    table[(index, col)].set_facecolor("#dbeafe")
    figure.tight_layout()
    return figure


def create_runtime_fem_geometry_preview_figure(snapshot: RuntimeFEMLineSnapshot, app: Any | None = None) -> Figure:
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

    geometry = runtime_geometry_summary(snapshot)
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
            axis.plot([x_mid, x_mid], [0.0, width], [web_height * 1.35, web_height * 1.35], color="#7f1d1d", linewidth=2.0)
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
        "Pressure [Pa]: " + str(round(_safe_float(summary.get("pressure_pa")), 3)),
        "Mesh size override [m]: " + str(round(_safe_float(summary.get("mesh_size_m")), 4)),
        "Top/bottom moment [Nm]: " + str(round(_safe_float(summary.get("top_bottom_moment_nm")), 3)),
        "Include stiffener beams: " + str(bool(summary.get("include_stiffeners"))),
        "Include girder/frame beams: " + str(bool(summary.get("include_girders"))),
        "Buckling modes: " + str(summary.get("num_buckling_modes", "")),
        "Max displacement [mm]: " + str(round(1000.0 * _safe_float(summary.get("max_displacement_m")), 4)),
    ]
    if result.buckling_factors:
        lines.append("Critical load factor: " + str(round(result.buckling_factors[0], 4)))
    mesh_info = summary.get("mesh_info") or {}
    if mesh_info:
        lines.extend([
            "",
            "FE mesh:",
            " - nodes: " + str(mesh_info.get("nodes", 0)),
            " - shells: " + str(mesh_info.get("shells", 0)),
            " - beams: " + str(mesh_info.get("beams", 0)),
        ])
    prestress = summary.get("prestress_summary") or {}
    if prestress:
        lines.extend(["", "Recovered prestress / reference state:"])
        for key, value in prestress.items():
            lines.append(" - " + key + ": " + str(round(_safe_float(value), 3)))
    load_resultant = summary.get("load_resultant") or {}
    if load_resultant:
        force = load_resultant.get("force_n", (0.0, 0.0, 0.0))
        lines.extend(["", "Load resultant force [N]: " + ", ".join(str(round(_safe_float(component), 3)) for component in force)])
    if result.diagnostics:
        lines.extend(["", "Diagnostics:"])
        lines.extend(" - " + item for item in result.diagnostics)
    return "\n".join(lines)


class RuntimeFEMWindow:
    """Popup window for the experimental full-geometry FEM runtime solver."""

    def __init__(self, parent: Any, app: Any, use_parent_as_window: bool = False):
        self.app = app
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
        try:
            self.window.attributes("-toolwindow", False)
        except Exception:
            pass
        # Position window relative to parent if possible
        try:
            if not use_parent_as_window:
                parent.update_idletasks()
                root_x = parent.winfo_rootx()
                root_y = parent.winfo_rooty()
                root_w = parent.winfo_width()
                root_h = parent.winfo_height()
                win_w, win_h = 1100, 760
                pos_x = root_x + max((root_w - win_w) // 2, 0)
                pos_y = root_y + max((root_h - win_h) // 2, 0)
                self.window.geometry(f'{win_w}x{win_h}+{pos_x}+{pos_y}')
        except Exception:
            pass

        self.mesh_fidelity = tk.StringVar(value="coarse")
        self.mesh_size_m = tk.DoubleVar(value=0.0)
        self.load_scale = tk.DoubleVar(value=1.0)
        self.pressure_pa = tk.DoubleVar(value=self.snapshot.pressure_pa)
        self.top_bottom_moment_nm = tk.DoubleVar(value=_safe_float(getattr(app, "_fem_default_top_bottom_moment_nm", 0.0)))
        self.include_stiffeners = tk.BooleanVar(value=True)
        self.include_girders = tk.BooleanVar(value=True)
        self.num_buckling_modes = tk.IntVar(value=5)
        self.display_choice = tk.StringVar(value="Static displacement/stress")
        self.display_mode_labels: dict[str, str] = {"Static displacement/stress": "static"}
        self.current_result: RuntimeFEMRunResult | None = None
        self.result_text = None
        self.figure_canvas = None
        self.figure_toolbar = None
        self.preview_canvas = None
        self.figure_parent = None
        self.display_selector = None
        self.run_button = None
        self.progress_bar = None
        self.solver_thread = None
        self.solver_queue = queue.Queue()

        self._build()

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
            text="ANYstructure local solver",
            background="#2563eb",
            foreground="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=3,
        ).pack(side=tk.RIGHT)
        tk.Label(
            header,
            text="Active-line analysis with shell plating, stiffener/girder beams, symmetric pressure and eigenvalue-style buckling factors.",
            background="#172033",
            foreground="#d7deeb",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, padx=16, pady=(0, 12))

        body = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(body)
        mid_panel = ttk.Frame(body)
        right_panel = ttk.Frame(body)
        body.add(left_panel, weight=2)
        body.add(mid_panel, weight=2)
        body.add(right_panel, weight=3)

        summary = ttk.LabelFrame(left_panel, text="Active line")
        summary.pack(fill=tk.X, pady=(0, 10))
        summary_text = (
            "Line: " + self.snapshot.line_name
            + "\nDomain: " + (self.snapshot.domain or "unknown")
            + "\nGeometry: " + ("cylinder/panel" if self.snapshot.is_cylinder else "flat panel")
            + "\nPressure [Pa]: " + str(round(self.snapshot.pressure_pa, 3))
        )
        ttk.Label(summary, text=summary_text, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=8)

        options = ttk.LabelFrame(left_panel, text="Run options")
        options.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(options, text="Mesh fidelity").grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.OptionMenu(options, self.mesh_fidelity, self.mesh_fidelity.get(), "coarse", "medium", "fine", "very fine").grid(
            row=0, column=1, sticky=tk.W, padx=8, pady=6
        )
        ttk.Label(options, text="Mesh size [m]").grid(row=0, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(options, textvariable=self.mesh_size_m, width=10).grid(row=0, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(options, text="Pressure [Pa]").grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(options, textvariable=self.pressure_pa, width=14).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Label(options, text="Load scale").grid(row=1, column=2, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(options, textvariable=self.load_scale, width=10).grid(row=1, column=3, sticky=tk.W, padx=8, pady=6)
        ttk.Label(options, text="Top/bottom moment [Nm]").grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(options, textvariable=self.top_bottom_moment_nm, width=14).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(options, text="Include stiffener beams", variable=self.include_stiffeners).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, padx=8, pady=6
        )
        ttk.Checkbutton(options, text="Include girder/frame beams", variable=self.include_girders).grid(
            row=3, column=2, columnspan=2, sticky=tk.W, padx=8, pady=6
        )
        ttk.Label(options, text="Buckling modes").grid(row=4, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Entry(options, textvariable=self.num_buckling_modes, width=8).grid(row=4, column=1, sticky=tk.W, padx=8, pady=6)

        buttons = ttk.Frame(left_panel)
        buttons.pack(fill=tk.X, pady=(0, 10))
        self.run_button = ttk.Button(buttons, text="Run FEM", command=self.run)
        self.run_button.pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(buttons, mode="indeterminate", length=140)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        ttk.Button(buttons, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)

        status_frame = ttk.LabelFrame(left_panel, text="Run status")
        status_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(status_frame, height=12, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        future_inputs = ttk.LabelFrame(mid_panel, text="Additional inputs")
        future_inputs.pack(fill=tk.BOTH, expand=True)

        preview = ttk.LabelFrame(right_panel, text="3D section view")
        preview.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._show_preview_figure(create_runtime_fem_geometry_preview_figure(self.snapshot, self.app), preview)

        result_frame = ttk.LabelFrame(right_panel, text="Run visualization")
        result_frame.pack(fill=tk.BOTH, expand=True)

        plot_holder = ttk.Frame(result_frame)
        plot_holder.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.figure_parent = plot_holder
        selector_bar = ttk.Frame(plot_holder)
        selector_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
        ttk.Label(selector_bar, text="Display").pack(side=tk.LEFT, padx=(0, 6))
        self.display_selector = ttk.Combobox(
            selector_bar,
            textvariable=self.display_choice,
            state="readonly",
            values=tuple(self.display_mode_labels),
            width=34,
        )
        self.display_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.display_selector.bind("<<ComboboxSelected>>", lambda _event: self._refresh_figure())
        self._show_figure(create_runtime_fem_result_figure(self.snapshot), plot_holder)
        self._write_status("Ready. ANYstructure production FE mesh solver is available.")

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

        toolbar_frame = ttk.Frame(parent)
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
            figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
        except Exception:
            pass
        zoom = 1.18
        if min(width, height) > 340:
            zoom = 1.28
        if min(width, height) > 520:
            zoom = 1.38
        for axis in figure.axes:
            if not hasattr(axis, "get_zlim"):
                continue
            axis.set_position([0.01, 0.03, 0.98, 0.93])
            axis.margins(0.0)
            try:
                axis.set_proj_type("ortho")
            except Exception:
                pass
            try:
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
        return self.display_mode_labels.get(str(self.display_choice.get()), "static")

    def _set_display_modes(self, result: RuntimeFEMRunResult) -> None:
        labels = {"Static displacement/stress": "static"}
        for mode in _buckling_mode_shapes(result):
            mode_number = int(mode.get("mode_number", 0))
            load_factor = _safe_float(mode.get("load_factor"))
            label = "Mode " + str(mode_number) + "  LF " + str(round(load_factor, 4))
            labels[label] = "mode:" + str(mode_number)
        self.display_mode_labels = labels
        self.display_choice.set("Static displacement/stress")
        if self.display_selector is not None:
            self.display_selector.configure(values=tuple(labels))

    def _refresh_figure(self) -> None:
        if self.figure_parent is None:
            return
        self._show_figure(
            create_runtime_fem_result_figure(self.snapshot, self.current_result, self._selected_display_mode()),
            self.figure_parent,
        )

    def _write_status(self, text: str) -> None:
        if self.result_text is None:
            return
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)

    def _set_solver_running(self, is_running: bool) -> None:
        if self.run_button is not None:
            self.run_button.configure(state=tk.DISABLED if is_running else tk.NORMAL)
        if self.progress_bar is not None:
            if is_running:
                self.progress_bar.start(12)
            else:
                self.progress_bar.stop()

    def _options(self) -> RuntimeFEMOptions:
        return RuntimeFEMOptions(
            mesh_fidelity=str(self.mesh_fidelity.get()),
            pressure_pa=_safe_float(self.pressure_pa.get()),
            load_scale=_safe_float(self.load_scale.get(), 1.0),
            include_stiffeners=bool(self.include_stiffeners.get()),
            include_girders=bool(self.include_girders.get()),
            num_buckling_modes=max(_safe_int(self.num_buckling_modes.get(), 5), 1),
            mesh_size_m=max(_safe_float(self.mesh_size_m.get(), 0.0), 0.0),
            top_bottom_moment_nm=_safe_float(self.top_bottom_moment_nm.get(), 0.0),
        )

    def run(self) -> None:
        """Prepare/run the runtime FEM request and render Matplotlib results."""

        if self.solver_thread is not None and self.solver_thread.is_alive():
            return
        if not self.include_stiffeners.get() and not self.include_girders.get():
            messagebox.showwarning("FEM solver", "At least one member beam family should normally be included.")

        options = self._options()
        self._set_solver_running(True)
        self._write_status("Running FEM solver...\n\n" + "The result plot will update when the solver finishes.")

        def worker() -> None:
            try:
                self.solver_queue.put((run_runtime_fem(self.snapshot, options), None))
            except Exception as error:
                self.solver_queue.put((None, error))

        self.solver_thread = threading.Thread(target=worker, daemon=True)
        self.solver_thread.start()
        self.window.after(100, self._poll_solver_result)

    def _poll_solver_result(self) -> None:
        try:
            result, error = self.solver_queue.get_nowait()
        except queue.Empty:
            if self.solver_thread is not None and self.solver_thread.is_alive():
                self.window.after(100, self._poll_solver_result)
                return
            self._set_solver_running(False)
            return

        self._set_solver_running(False)
        if error is not None:
            self._write_status("Runtime FEM failed:\n" + str(error))
            messagebox.showerror("FEM solver", str(error))
            return

        self.current_result = result
        self._set_display_modes(result)
        self._write_status(format_runtime_fem_result(result))
        self._refresh_figure()


def open_runtime_fem_window(parent: Any, app: Any) -> RuntimeFEMWindow | None:
    """Open the experimental runtime FEM popup for the app active line."""

    try:
        return RuntimeFEMWindow(parent, app)
    except Exception as error:
        messagebox.showinfo("Experimental FEM solver", str(error))
        return None


class _ExamplePlate:
    def get_structure_type(self):
        return "Flat plate, stiffened with girder"

    def get_span(self):
        return 2.8

    def get_s(self):
        return 0.72

    def get_pl_thk(self):
        return 0.012


class _ExampleAllStructure:
    Plate = _ExamplePlate()
    Stiffener = object()
    Girder = object()


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
    _fem_default_top_bottom_moment_nm = 30_000_000.0
    _active_line = "line_example"
    _line_is_active = True
    _line_dict = {"line_example": [1, 2]}
    _line_to_struc = {"line_example": [_ExampleAllStructure(), None, None, object(), None, _ExampleCylinder()]}
    _simplified_calculation_mode = True

    def __init__(self):
        self._new_prop_3d_opposite_side = _ExampleTkVariable(False)
        self._new_shell_ring_frame_length_between_girders = _ExampleTkVariable(4.0)
        self._new_shell_dist_rings = _ExampleTkVariable(2.0)
        self._new_panel_length_Lp = _ExampleTkVariable(0.0)
        self._new_girder_length_LG = _ExampleTkVariable(8.0)

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
        return {"normal": 100_000.0 if line == self._active_line else 0.0}


def example_runtime_app() -> _ExampleRuntimeApp:
    """Return a tiny active-line app fixture for running this module directly."""

    return _ExampleRuntimeApp()


if __name__ == "__main__":
    root = tk.Tk()
    my_app = RuntimeFEMWindow(root, example_runtime_app(), use_parent_as_window=True)
    my_app.window.protocol("WM_DELETE_WINDOW", root.destroy)
    my_app.window.focus_force()
    root.mainloop()
