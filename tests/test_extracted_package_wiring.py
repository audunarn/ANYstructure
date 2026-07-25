'''
Wiring guards for the extracted ANY* packages.

ANYstructure delegates its calculation engines to standalone packages:
ANYsolver (FE), ANYbuckling (prescriptive + semi-analytical buckling)
and ANYtk3D (Tkinter 3D canvas). These tests pin the shim wiring so a
refactor cannot silently reintroduce local copies or break the aliases.
The engines' behaviour is tested in their own repositories.
'''


def test_calc_structure_buckling_classes_come_from_anybuckling():
    from anystruct import calc_structure as calc

    assert calc.Structure.__module__ == 'anybuckling.prescriptive.plates'
    assert calc.CalcScantlings.__module__ == 'anybuckling.prescriptive.plates'
    assert calc.AllStructure.__module__ == 'anybuckling.prescriptive.plates'
    assert calc.Shell.__module__ == 'anybuckling.prescriptive.cylinders'
    assert calc.CylinderAndCurvedPlate.__module__ == 'anybuckling.prescriptive.cylinders'
    assert calc.PULSpanel.__module__ == 'anybuckling.puls.panel'


def test_fatigue_stays_in_anystructure():
    from anystruct import calc_structure as calc

    assert calc.CalcFatigue.__module__ == 'anystruct.calc_structure'
    # CalcFatigue extends the ANYbuckling panel data model.
    assert issubclass(calc.CalcFatigue, calc.Structure)


def test_semianalytical_module_is_aliased_to_anybuckling():
    import anybuckling.semianalytical.solver as solver
    import anystruct.calculate_semianalytical as semi

    assert semi is solver


def test_tk3d_module_is_aliased_to_anytk3d():
    import anystruct.tkinter_3d_canvas_thickness_v6 as tk3d
    import anytk3d.canvas as canvas

    assert tk3d is canvas


def test_excel_interface_comes_from_anybuckling():
    import importlib.util

    if importlib.util.find_spec('xlwings') is None:
        import pytest

        pytest.skip('xlwings not installed')
    from anystruct.excel_inteface import ExcelInterface

    assert ExcelInterface.__module__ == 'anybuckling.puls.excel'


def test_fem_integration_uses_anysolver_backend():
    from anystruct import fem_integration

    assert fem_integration.fe_solver.__name__ == 'anysolver.runtime'


def test_anystructure_keeps_ml_numeric_method():
    # The ML-Numeric buckling method stays in ANYstructure; the ANYbuckling
    # package deliberately does not ship it.
    import anybuckling.helpers
    from anystruct import api_helpers

    assert 'ML-Numeric (PULS based)' in api_helpers.BUCKLING_CALCULATION_METHODS
    assert 'ML-Numeric (PULS based)' not in anybuckling.helpers.BUCKLING_CALCULATION_METHODS
