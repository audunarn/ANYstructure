"""Explicit historical GE-B3 and production B3-GE runtime adapters."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from anysolver.beam_sections import GeneralizedBeamSection
from anysolver.elements import create_element
from anysolver.ge_beam3_element import GE_BEAM3_QUALIFIED_FORMULATION_ID, GeometricallyExactBeam3D3NElement


@dataclass(frozen=True)
class GeBeam3RuntimeDefinition:
    stiffness: Any
    mass_per_length: Any
    physical_orientation: Sequence[float]

    def build(self, element_id: int, node_ids: Sequence[int], material_name: str) -> GeometricallyExactBeam3D3NElement:
        stiffness = np.asarray(self.stiffness, dtype=float)
        mass = np.asarray(self.mass_per_length, dtype=float)
        orientation = np.asarray(self.physical_orientation, dtype=float)
        if stiffness.shape != (6, 6) or mass.shape != (6, 6) or orientation.shape != (3,):
            raise ValueError("complete GE-B3 section and orientation authority required")
        if not np.isfinite(stiffness).all() or not np.isfinite(mass).all() or not np.isfinite(orientation).all():
            raise ValueError("finite GE-B3 runtime definition required")
        section = GeneralizedBeamSection(stiffness, mass_matrix=mass, name="ANYstructure explicit GE-B3")
        made = create_element("ge-beam3", element_id, list(node_ids), material_name,
                              section=section, reference_orientation=orientation)
        if type(made) is not GeometricallyExactBeam3D3NElement:
            raise RuntimeError("ANYstructure resolved an unexpected GE-B3 class")
        return made


def runtime_status(definition: GeBeam3RuntimeDefinition) -> dict[str, Any]:
    if type(definition) is not GeBeam3RuntimeDefinition:
        raise TypeError("exact GE-B3 runtime definition required")
    return {"beam_element": "GE-B3 straight — mixed Simo–Reissner",
            "selector": "ge-beam3",
            "formulation_id": GE_BEAM3_QUALIFIED_FORMULATION_ID,
            "explicit_opt_in": True, "default_changed": False}


B3_GE_SCHEMA = "anystructure.b3-ge-native-opt-in-v2"
B3_GE_SELECTION_SCHEMA = "anystructure.b3-ge-selection-v1"
LEGACY_B3_SELECTOR = "b3"
B3_GE_POLICY = {
    "selector": "b3-ge",
    "native_profile_id": "GE_BEAM3_NATIVE_OWNED_WORKFLOWS_V1",
    "explicit_opt_in": True,
    "legacy_b3_default": True,
}


@dataclass(frozen=True)
class BeamRuntimeSelection:
    """Persisted beam-runtime choice with legacy B3 as the closed default.

    ``b3-ge`` is admitted only through the dedicated, exact selector field.
    Historical project options that do not contain that field therefore keep
    their legacy quadratic B3 behaviour.
    """

    selector: str = LEGACY_B3_SELECTOR

    def __post_init__(self) -> None:
        if type(self.selector) is not str or self.selector not in {
            LEGACY_B3_SELECTOR,
            B3_GE_POLICY["selector"],
        }:
            raise ValueError("beam runtime selector must be 'b3' or exact 'b3-ge'")

    @property
    def explicit_b3_ge(self) -> bool:
        return self.selector == B3_GE_POLICY["selector"]

    def to_dict(self) -> dict[str, str]:
        return {
            "schema": B3_GE_SELECTION_SCHEMA,
            "beam_formulation": self.selector,
        }

    @classmethod
    def from_project_options(cls, data: Mapping[str, Any] | None) -> "BeamRuntimeSelection":
        """Load a project choice without reinterpreting historical fields."""

        if data is None:
            return cls()
        if not isinstance(data, Mapping):
            raise TypeError("beam runtime project options must be a mapping")
        if "beam_formulation" not in data:
            return cls()
        if data.get("schema") != B3_GE_SELECTION_SCHEMA:
            raise ValueError("explicit beam selection requires its versioned schema")
        return cls(data["beam_formulation"])


@dataclass(frozen=True)
class B3GERuntimeDefinition:
    """Detached native definition graph for an explicit B3-GE runtime."""

    definitions: Sequence[Any]

    def __post_init__(self) -> None:
        from anysolver._ge_beam3_native_definition import NativeBeamDefinition

        rows = tuple(self.definitions)
        if not rows or any(type(row) is not NativeBeamDefinition for row in rows):
            raise ValueError("one or more exact native B3-GE definitions required")
        object.__setattr__(self, "definitions", tuple(
            NativeBeamDefinition.from_bytes(bytes(row.raw), expected_sha256=row.sha256)
            for row in rows
        ))

    def create_analysis(self, boundaries: Sequence[Any], *, retained_refinement: bool = False):
        from anysolver import b3_ge

        return b3_ge.create_analysis(
            b3_ge.SELECTOR,
            self.definitions,
            tuple(boundaries),
            retained_refinement=retained_refinement,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": B3_GE_SCHEMA,
            "policy": dict(B3_GE_POLICY),
            "definitions": [
                {"raw_base64": base64.b64encode(row.raw).decode("ascii"), "sha256": row.sha256}
                for row in self.definitions
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "B3GERuntimeDefinition":
        if (
            type(data) is not dict
            or set(data) != {"schema", "policy", "definitions"}
            or data["schema"] != B3_GE_SCHEMA
            or data["policy"] != B3_GE_POLICY
            or type(data["definitions"]) is not list
        ):
            raise ValueError("strict ANYstructure B3-GE native opt-in record required")
        rows = []
        from anysolver._ge_beam3_native_definition import NativeBeamDefinition

        for item in data["definitions"]:
            if type(item) is not dict or set(item) != {"raw_base64", "sha256"}:
                raise ValueError("strict B3-GE definition binding required")
            if (
                type(item["raw_base64"]) is not str
                or len(item["raw_base64"]) > 2_800_000
                or type(item["sha256"]) is not str
                or len(item["sha256"]) != 64
            ):
                raise ValueError("bounded B3-GE definition binding required")
            try:
                raw = base64.b64decode(item["raw_base64"], validate=True)
            except Exception as exc:
                raise ValueError("invalid B3-GE definition encoding") from exc
            rows.append(NativeBeamDefinition.from_bytes(raw, expected_sha256=item["sha256"]))
        return cls(tuple(rows))


def b3_ge_runtime_status(definition: B3GERuntimeDefinition) -> dict[str, Any]:
    if type(definition) is not B3GERuntimeDefinition:
        raise TypeError("exact B3-GE runtime definition required")
    return {
        "beam_element": "B3-GE — geometrically exact Simo–Reissner",
        "selector": "b3-ge",
        "native_profile_id": B3_GE_POLICY["native_profile_id"],
        "selection": "explicit opt-in",
        "legacy_b3_default": True,
        "default_changed": False,
    }


def launch_beam_runtime(
    selection: BeamRuntimeSelection | Mapping[str, Any] | None = None,
    *,
    element_id: int,
    node_ids: Sequence[int],
    material_name: str = "",
    b3_ge_definition: B3GERuntimeDefinition | None = None,
    boundaries: Sequence[Any] = (),
    retained_refinement: bool = False,
) -> Any:
    """Launch the selected real solver path without aliases or fallback.

    Omitted and migrated historical selections construct the established
    quadratic B3 element.  The native B3-GE owner is reachable only when the
    exact versioned ``b3-ge`` selection and a complete native definition are
    both supplied.
    """

    resolved = (
        selection
        if type(selection) is BeamRuntimeSelection
        else BeamRuntimeSelection.from_project_options(selection)
    )
    if not resolved.explicit_b3_ge:
        from anysolver.elements import create_element

        return create_element(
            "quadratic_beam",
            int(element_id),
            [int(node_id) for node_id in node_ids],
            str(material_name),
        )
    if type(b3_ge_definition) is not B3GERuntimeDefinition:
        raise ValueError("explicit b3-ge selection requires a complete native definition")
    return b3_ge_definition.create_analysis(
        tuple(boundaries), retained_refinement=bool(retained_refinement)
    )


__all__ = [
    "GeBeam3RuntimeDefinition", "runtime_status", "B3GERuntimeDefinition",
    "b3_ge_runtime_status", "B3_GE_SCHEMA", "B3_GE_SELECTION_SCHEMA",
    "LEGACY_B3_SELECTOR", "BeamRuntimeSelection", "launch_beam_runtime",
]
