"""Small, lazy integration helpers for the extracted ANY ecosystem GUIs.

The standalone packages own their editors and event handling.  ANYstructure
only hosts them in its existing Tk process and translates an isotropic material
specification onto the scalar fields its legacy calculation models understand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class UnsupportedMaterialSelection(ValueError):
    """A material cannot be represented by ANYstructure's scalar inputs."""


@dataclass(frozen=True)
class IsotropicMaterialSelection:
    """Scalar material values in the units used by the ANYstructure GUIs."""

    name: str
    elastic_modulus_gpa: float
    poisson_ratio: float
    yield_stress_mpa: float
    material_model: str
    steel_grade: str
    steel_thickness_class: str
    unsupported_hardening_kind: str | None = None


def material_library_names() -> tuple[str, ...]:
    """Return material names without importing ANYmaterial during module import."""

    from anymaterial import library

    return tuple(library().names)


def default_material_name(names: tuple[str, ...] | None = None) -> str:
    """Choose the familiar S355 thin-plate row when the library provides it."""

    available = material_library_names() if names is None else names
    for name in available:
        lowered = name.lower()
        if "s355" in lowered and "t <= 16" in lowered:
            return name
    for name in available:
        if "s355" in name.lower():
            return name
    return available[0] if available else "S355"


def material_spec_from_library(name: str) -> Any:
    """Resolve one named material specification through ANYmaterial's public API."""

    from anymaterial import library

    return library().get(str(name)).spec


def _dnv_thickness_class(hardening: dict[str, Any]) -> str:
    explicit = str(hardening.get("thickness_class", "")).strip()
    aliases = {
        "t <= 16": "t <= 16",
        "t <= 16 mm": "t <= 16",
        "16 < t <= 40": "16 < t <= 40",
        "16 < t <= 40 mm": "16 < t <= 40",
        "40 < t <= 63": "40 < t <= 63",
        "40 < t <= 63 mm": "40 < t <= 63",
        "63 < t <= 100": "63 < t <= 100",
        "63 < t <= 100 mm": "63 < t <= 100",
    }
    if explicit.lower() == "auto":
        return "auto"
    if explicit in aliases:
        return aliases[explicit]

    try:
        thickness = float(hardening.get("thickness", 0.0))
    except (TypeError, ValueError):
        return "auto"
    if thickness <= 0.0:
        return "auto"
    if thickness <= 0.016:
        return "t <= 16"
    if thickness <= 0.040:
        return "16 < t <= 40"
    if thickness <= 0.063:
        return "40 < t <= 63"
    if thickness <= 0.100:
        return "63 < t <= 100"
    return "auto"


def isotropic_material_selection(spec: Any) -> IsotropicMaterialSelection:
    """Translate a public MaterialSpec into existing scalar GUI values.

    Orthotropic elasticity is refused explicitly: reducing it to one Young's
    modulus and one Poisson ratio would silently change the selected material.
    """

    symmetry = str(getattr(spec, "symmetry", "")).strip().lower()
    if symmetry != "isotropic":
        raise UnsupportedMaterialSelection(
            "ANYstructure's current material inputs support isotropic materials only; "
            f"{getattr(spec, 'name', 'the selected material')!r} is {symmetry or 'not isotropic'}."
        )

    constants = dict(getattr(spec, "constants", {}) or {})
    try:
        elastic_modulus_pa = float(constants["elastic_modulus"])
        poisson_ratio = float(constants["poisson_ratio"])
        yield_stress_pa = float(getattr(spec, "yield_stress"))
    except (KeyError, TypeError, ValueError) as error:
        raise UnsupportedMaterialSelection(
            "The selected isotropic material does not provide E, Poisson ratio, and yield stress."
        ) from error
    if elastic_modulus_pa <= 0.0 or yield_stress_pa <= 0.0:
        raise UnsupportedMaterialSelection(
            "ANYstructure requires positive elastic modulus and yield stress values."
        )

    hardening = dict(getattr(spec, "hardening", None) or {})
    hardening_kind = str(hardening.get("kind", "")).strip().lower()
    is_dnv_c208 = hardening_kind == "dnv_c208"
    return IsotropicMaterialSelection(
        name=str(getattr(spec, "name", "material")),
        elastic_modulus_gpa=elastic_modulus_pa / 1.0e9,
        poisson_ratio=poisson_ratio,
        yield_stress_mpa=yield_stress_pa / 1.0e6,
        material_model="DNV-RP-C208 steel" if is_dnv_c208 else "linear elastic",
        steel_grade=str(hardening.get("grade", "S355")) if is_dnv_c208 else "S355",
        steel_thickness_class=_dnv_thickness_class(hardening) if is_dnv_c208 else "auto",
        unsupported_hardening_kind=(hardening_kind or None) if hardening_kind and not is_dnv_c208 else None,
    )


def open_material_editor(
    master: Any,
    *,
    initial_spec: Any = None,
    on_apply: Callable[[Any], None] | None = None,
) -> tuple[Any, Any]:
    """Open ANYmaterial inside a child Toplevel of the existing application."""

    from anymaterial.gui import open_material_editor as open_editor

    return open_editor(master, initial_spec=initial_spec, on_apply=on_apply)


def open_mesher(master: Any) -> tuple[Any, Any]:
    """Open ANYmesher inside a child Toplevel of the existing application."""

    from anymesher.gui import open_mesher as open_editor

    return open_editor(master)


def open_file_inspector(master: Any, path: str | None = None) -> tuple[Any, Any]:
    """Open ANYfileio inside a child Toplevel of the existing application."""

    from anyfileio.gui import open_inspector

    return open_inspector(master, path=path)
