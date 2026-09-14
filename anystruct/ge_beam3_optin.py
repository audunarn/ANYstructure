"""Explicit GE-B3 construction for advanced runtime adapters only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from anysolver.beam_sections import GeneralizedBeamSection
from anysolver.elements import create_element
from anysolver.ge_beam3_element import GE_BEAM3_QUALIFIED_FORMULATION_ID, GeometricallyExactBeam3D3NElement
from anysolver.ge_beam3_native import ConsumerPolicy


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
    policy = ConsumerPolicy.ge_beam3()
    return {"beam_element": "GE-B3 straight — mixed Simo–Reissner",
            "selector": policy.selector,
            "formulation_id": GE_BEAM3_QUALIFIED_FORMULATION_ID,
            "explicit_opt_in": True, "default_changed": False}


__all__ = ["GeBeam3RuntimeDefinition", "runtime_status"]
