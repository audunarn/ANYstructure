"""Thin ANYstructure adapters for neutral ANYgeometry generators.

Geometry topology, persistent entity identity, and semantic geometry groups are
owned by :mod:`anygeometry`.  This module gives ANYstructure callers explicit,
stable names while keeping materials, thicknesses, sections, design properties,
loads, and finite-element settings out of the geometry model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
import math
from threading import Lock
from typing import Any, Callable, Mapping, Sequence

from anygeometry.generators import (
    cone as _cone,
    cylinder as _cylinder,
    plate as _plate,
    stiffened_panel as _stiffened_panel,
)
from anygeometry.model import GeometryModel

__all__ = [
    "GeometryBackedProjection",
    "RuntimeGeometryAuthority",
    "build_runtime_geometry_authority",
    "generate_cone_geometry",
    "generate_cylinder_geometry",
    "generate_plate_geometry",
    "generate_stiffened_panel_geometry",
    "project_runtime_geometry",
    "project_runtime_payload",
]


_RUNTIME_GEOMETRY_FIELDS = frozenset(
    {
        "geometry",
        "length_m",
        "width_m",
        "radius_m",
        "is_cone",
        "cone_r1_m",
        "cone_r2_m",
        "cone_length_m",
        "has_stiffener",
        "has_girder",
        "stiffener_spacing_m",
        "girder_spacing_m",
        "ring_spacing_m",
    }
)


@dataclass
class RuntimeGeometryAuthority:
    """An exact owner model plus external application/structural metadata.

    The legacy runtime mapping is retained only as a projection contract for
    ANYsolver and existing renderers. Thicknesses, sections, loads and analysis
    settings live in ``structural_metadata`` and are never copied into faces.
    """

    geometry_fields: Mapping[str, Any]
    structural_metadata: Mapping[str, Any]
    legacy_summary: Mapping[str, Any]
    _model_factory: Callable[[], GeometryModel] = field(repr=False)
    _model: GeometryModel | None = field(default=None, init=False, repr=False)
    _model_lock: Any = field(default_factory=Lock, init=False, repr=False)

    @property
    def model(self) -> GeometryModel:
        """Materialize and cache the exact owner model on first explicit use."""

        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = self._model_factory()
        return self._model


class GeometryBackedProjection(dict):
    """Legacy dict payload carrying its exact geometry authority out-of-band.

    It deliberately has no additional mapping keys, so equality, JSON output
    and old render code remain unchanged. New code can use ``geometry_model``
    without a duplicate geometry representation or conversion layer.
    """

    def __init__(
        self,
        payload: Mapping[str, Any],
        authority: RuntimeGeometryAuthority,
    ) -> None:
        super().__init__(payload)
        self.geometry_authority = authority
        self.structural_metadata = authority.structural_metadata

    @property
    def geometry_model(self) -> GeometryModel:
        """Return the lazily materialized exact geometry model."""

        return self.geometry_authority.model


def _positive_or(value: Any, fallback: float) -> float:
    try:
        made = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    return made if made > 0.0 else float(fallback)


def _active_spacing(value: Any, span: float) -> float:
    """Return a usable member spacing, including the legacy midpoint fallback."""

    try:
        spacing = float(value)
    except (TypeError, ValueError):
        spacing = 0.0
    if spacing <= 0.0 or spacing > span:
        return 0.5 * span
    return spacing


def build_runtime_geometry_authority(
    summary: Mapping[str, Any],
    *,
    include_stiffeners: bool = True,
    include_girders: bool = True,
    circumferential_segments: int = 12,
) -> RuntimeGeometryAuthority:
    """Build the neutral owner model behind an ANYstructure runtime summary."""

    legacy_summary = dict(summary)
    geometry_fields = {
        name: value
        for name, value in legacy_summary.items()
        if name in _RUNTIME_GEOMETRY_FIELDS
    }
    structural_metadata = {
        name: value
        for name, value in legacy_summary.items()
        if name not in _RUNTIME_GEOMETRY_FIELDS
    }
    geometry_kind = str(legacy_summary.get("geometry", "flat panel")).lower()
    has_stiffener = bool(include_stiffeners and legacy_summary.get("has_stiffener"))
    has_girder = bool(include_girders and legacy_summary.get("has_girder"))

    if geometry_kind == "cylinder":
        length = _positive_or(legacy_summary.get("length_m"), 1.0)
        is_cone = bool(legacy_summary.get("is_cone"))
        radius_start = _positive_or(legacy_summary.get("cone_r1_m"), 1.0)
        radius_end = _positive_or(legacy_summary.get("cone_r2_m"), 1.0)
        axial_span = (
            _positive_or(legacy_summary.get("cone_length_m"), length)
            if is_cone
            else length
        )
        reference_radius = (
            0.5 * (radius_start + radius_end)
            if is_cone
            else _positive_or(legacy_summary.get("radius_m"), 1.0)
        )
        ring_spacing = (
            _active_spacing(
                legacy_summary.get(
                    "girder_spacing_m",
                    legacy_summary.get("ring_spacing_m"),
                ),
                axial_span,
            )
            if has_girder
            else None
        )
        longitudinal_spacing = None
        if has_stiffener:
            longitudinal_spacing = _active_spacing(
                legacy_summary.get("stiffener_spacing_m"),
                2.0 * math.pi * reference_radius,
            )
        if is_cone:
            model_factory = partial(
                generate_cone_geometry,
                radius_start,
                radius_end,
                axial_span,
                circumferential_segments=circumferential_segments,
                longitudinal_spacing=longitudinal_spacing,
                ring_spacing=ring_spacing,
            )
        else:
            model_factory = partial(
                generate_cylinder_geometry,
                _positive_or(legacy_summary.get("radius_m"), 1.0),
                length,
                circumferential_segments=circumferential_segments,
                longitudinal_spacing=longitudinal_spacing,
                ring_spacing=ring_spacing,
            )
    else:
        length = _positive_or(legacy_summary.get("length_m"), 1.0)
        width = _positive_or(legacy_summary.get("width_m"), 1.0)
        if has_stiffener or has_girder:
            longitudinal_spacing = (
                _active_spacing(
                    legacy_summary.get("stiffener_spacing_m"),
                    width,
                )
                if has_stiffener
                else 2.0 * width
            )
            transverse_spacing = (
                _active_spacing(
                    legacy_summary.get("girder_spacing_m"),
                    length,
                )
                if has_girder
                else None
            )
            model_factory = partial(
                generate_stiffened_panel_geometry,
                length,
                width,
                longitudinal_spacing=longitudinal_spacing,
                transverse_spacing=transverse_spacing,
            )
        else:
            model_factory = partial(generate_plate_geometry, length, width)

    return RuntimeGeometryAuthority(
        geometry_fields=geometry_fields,
        structural_metadata=structural_metadata,
        legacy_summary=legacy_summary,
        _model_factory=model_factory,
    )


def project_runtime_geometry(
    authority: RuntimeGeometryAuthority,
) -> GeometryBackedProjection:
    """Project an owner model to the unchanged normalized-runtime mapping."""

    return GeometryBackedProjection(authority.legacy_summary, authority)


def project_runtime_payload(
    payload: Mapping[str, Any],
    authority: RuntimeGeometryAuthority,
) -> GeometryBackedProjection:
    """Attach the same authority to a legacy generated-mesh/render payload."""

    return GeometryBackedProjection(payload, authority)


def generate_plate_geometry(
    length: float,
    width: float,
    *,
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    u_direction: Sequence[float] = (1.0, 0.0, 0.0),
    v_direction: Sequence[float] = (0.0, 1.0, 0.0),
    semantic_group: str = "shell",
) -> GeometryModel:
    """Return a neutral plate model; structural assignments stay external."""

    return _plate(
        length,
        width,
        origin=origin,
        u_direction=u_direction,
        v_direction=v_direction,
        semantic_group=semantic_group,
    )


def generate_stiffened_panel_geometry(
    length: float,
    width: float,
    *,
    longitudinal_spacing: float,
    transverse_spacing: float | None = None,
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    u_direction: Sequence[float] = (1.0, 0.0, 0.0),
    v_direction: Sequence[float] = (0.0, 1.0, 0.0),
    semantic_group: str = "shell",
) -> GeometryModel:
    """Return a neutral panel with semantic plate/member groups."""

    return _stiffened_panel(
        length,
        width,
        longitudinal_spacing=longitudinal_spacing,
        transverse_spacing=transverse_spacing,
        origin=origin,
        u_direction=u_direction,
        v_direction=v_direction,
        semantic_group=semantic_group,
    )


def generate_cylinder_geometry(
    radius: float,
    height: float,
    *,
    circumferential_segments: int = 12,
    longitudinal_spacing: float | None = None,
    ring_spacing: float | None = None,
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    axis: Sequence[float] = (0.0, 0.0, 1.0),
    radial_direction: Sequence[float] = (1.0, 0.0, 0.0),
) -> GeometryModel:
    """Return neutral cylindrical shell geometry and member groups."""

    return _cylinder(
        radius,
        height,
        circumferential_segments=circumferential_segments,
        longitudinal_spacing=longitudinal_spacing,
        ring_spacing=ring_spacing,
        origin=origin,
        axis=axis,
        radial_direction=radial_direction,
    )


def generate_cone_geometry(
    radius_start: float,
    radius_end: float,
    height: float,
    *,
    circumferential_segments: int = 12,
    longitudinal_spacing: float | None = None,
    ring_spacing: float | None = None,
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    axis: Sequence[float] = (0.0, 0.0, 1.0),
    radial_direction: Sequence[float] = (1.0, 0.0, 0.0),
) -> GeometryModel:
    """Return neutral conical shell geometry and member groups."""

    return _cone(
        radius_start,
        radius_end,
        height,
        circumferential_segments=circumferential_segments,
        longitudinal_spacing=longitudinal_spacing,
        ring_spacing=ring_spacing,
        origin=origin,
        axis=axis,
        radial_direction=radial_direction,
    )
