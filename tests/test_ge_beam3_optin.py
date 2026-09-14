import numpy as np

from anystruct.ge_beam3_optin import GeBeam3RuntimeDefinition, runtime_status
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
