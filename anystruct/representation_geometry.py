"""Compatibility imports for geometry representation layout helpers.

The implementation moved to :mod:`anygeometry.generators.layout` so previews,
exporters, meshers, and finite-element workflows use one deterministic station
placement authority.  This module remains for third-party ANYstructure callers
during the package migration.
"""

from anygeometry.generators.layout import (
    EPS,
    bay_ranges as bay_ranges_from_support_positions,
    centered_bay_breaks,
    centered_member_positions,
    cleanup_axis as cleaned_axis_values,
    closed_loop_member_count,
    positive_spacing,
    symmetric_samples,
)

__all__ = [
    "EPS",
    "bay_ranges_from_support_positions",
    "centered_bay_breaks",
    "centered_member_positions",
    "cleaned_axis_values",
    "closed_loop_member_count",
    "positive_spacing",
]


def _symmetrically_sample_positions(positions: list[float], max_count: int) -> list[float]:
    """Retain the historical private helper's list return type."""

    return list(symmetric_samples(positions, max_count))
