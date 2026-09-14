import numpy as np

from anystruct.ge_beam3_optin import (
    B3GERuntimeDefinition,
    GeBeam3RuntimeDefinition,
    b3_ge_runtime_status,
    runtime_status,
)
from anysolver.ge_beam3_element import GeometricallyExactBeam3D3NElement


def test_runtime_ge_beam3_is_exact_explicit_and_descriptive():
    definition = GeBeam3RuntimeDefinition(np.diag((10., 11., 12., 13., 14., 15.)),
                                          np.diag((2., 2., 2., .1, .2, .3)),
                                          (0., 1., 0.))
    element = definition.build(1, (1, 2, 3), "steel")
    assert type(element) is GeometricallyExactBeam3D3NElement
    status = runtime_status(definition)
    assert status["beam_element"] == "GE-B3 straight — mixed Simo–Reissner"
    assert status["explicit_opt_in"] is True and status["default_changed"] is False


def test_runtime_b3_ge_is_native_explicit_and_legacy_b3_stays_default():
    from anysolver import b3_ge
    from anysolver.boundary import BoundaryCondition
    from anysolver.elements import QuadraticBeamElement, create_element

    section = b3_ge.EllipsoidalGeneralizedSection(
        np.diag((10.0, 11.0, 12.0, 13.0, 14.0, 15.0)), np.eye(6), 1.0e6, 1.0
    )
    native = b3_ge.define_beam(
        b3_ge.SELECTOR, 1, (1, 2, 3),
        np.array(((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.0, 0.0))),
        np.repeat(np.eye(3)[None, :, :], 3, axis=0), section,
        np.diag((2.0, 2.0, 2.0, 0.07, 0.09, 0.11)),
    )
    restored = B3GERuntimeDefinition.from_dict(B3GERuntimeDefinition((native,)).to_dict())
    owner = restored.create_analysis((BoundaryCondition(
        "fixed", [1], {"ux": 0.0, "uy": 0.0, "uz": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0}
    ),))
    status = b3_ge_runtime_status(restored)
    assert owner.identity
    assert status["beam_element"] == "B3-GE — geometrically exact Simo–Reissner"
    assert status["selector"] == "b3-ge"
    assert status["selection"] == "explicit opt-in"
    assert status["legacy_b3_default"] is True and status["default_changed"] is False
    assert type(create_element("quadratic_beam", 99, [1, 2, 3])) is QuadraticBeamElement
