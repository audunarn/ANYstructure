"""Explicit historical GE-B3 and production B3-GE runtime adapters."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from anysolver import b3_ge
from anysolver._ge_beam3_native_definition import NativeBeamDefinition
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
B3_GE_POLICY = {
    "selector": "b3-ge",
    "native_profile_id": b3_ge.NATIVE_PROFILE_ID,
    "explicit_opt_in": True,
    "legacy_b3_default": True,
}


@dataclass(frozen=True)
class B3GERuntimeDefinition:
    """Detached native definition graph for an explicit B3-GE runtime."""

    definitions: Sequence[NativeBeamDefinition]

    def __post_init__(self) -> None:
        rows = tuple(self.definitions)
        if not rows or any(type(row) is not NativeBeamDefinition for row in rows):
            raise ValueError("one or more exact native B3-GE definitions required")
        object.__setattr__(self, "definitions", tuple(
            NativeBeamDefinition.from_bytes(bytes(row.raw), expected_sha256=row.sha256)
            for row in rows
        ))

    def create_analysis(self, boundaries: Sequence[Any], *, retained_refinement: bool = False):
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
        for item in data["definitions"]:
            if type(item) is not dict or set(item) != {"raw_base64", "sha256"}:
                raise ValueError("strict B3-GE definition binding required")
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
        "native_profile_id": b3_ge.NATIVE_PROFILE_ID,
        "selection": "explicit opt-in",
        "legacy_b3_default": True,
        "default_changed": False,
    }


__all__ = [
    "GeBeam3RuntimeDefinition", "runtime_status", "B3GERuntimeDefinition",
    "b3_ge_runtime_status", "B3_GE_SCHEMA",
]
