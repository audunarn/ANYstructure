from copy import deepcopy

import pytest
from anystruct import example_data as ex, calc_structure as calc


# Testing the Structure class

def _with_panel_default(obj_dict):
    obj_dict = deepcopy(obj_dict)
    obj_dict.setdefault('panel or shell', ['panel', ''])
    return obj_dict

@pytest.fixture
def fatigue_cls():
    return (calc.CalcFatigue(_with_panel_default(ex.obj_dict), ex.fat_obj_dict),
            calc.CalcFatigue(_with_panel_default(ex.obj_dict2), ex.fat_obj_dict),
            calc.CalcFatigue(_with_panel_default(ex.obj_dict_L), ex.fat_obj_dict))

def test_fatigue_damage(fatigue_cls):
    int_press = (0, 0, 0)
    ext_press = (50000, 60000, 0)
    results = [item.get_total_damage(int_press=int_press, ext_press=ext_press) for item in fatigue_cls]

    assert all(result >= 0 for result in results)
    assert results[0] == pytest.approx(0.0023537087192241858)

def test_fatigue_properties(fatigue_cls):
    item1 = fatigue_cls[0].get_fatigue_properties()
    item2 = fatigue_cls[1].get_fatigue_properties()
    item3 = fatigue_cls[2].get_fatigue_properties()
    assert item1 == {'SN-curve': 'Ec', 'SCF': 1, 'Design life': 20, 'n0': 10000, 'Weibull': (0.8, 0.8, 0.8),
                     'Period': (9, 9, 9), 'Fraction': (1, 0, 0), 'CorrLoc': (0.5, 0.5, 0.5),
                     'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations': (0.5, 0.5, 0.5), 'DFF': 2}
    assert item2 == {'SN-curve': 'Ec', 'SCF': 1, 'Design life': 20, 'n0': 10000, 'Weibull': (0.8, 0.8, 0.8),
                     'Period': (9, 9, 9), 'Fraction': (1, 0, 0), 'CorrLoc': (0.5, 0.5, 0.5),
                     'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations': (0.5, 0.5, 0.5), 'DFF': 2}
    assert item3 == {'SN-curve': 'Ec', 'SCF': 1, 'Design life': 20, 'n0': 10000, 'Weibull': (0.8, 0.8, 0.8),
                     'Period': (9, 9, 9), 'Fraction': (1, 0, 0), 'CorrLoc': (0.5, 0.5, 0.5),
                     'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations': (0.5, 0.5, 0.5), 'DFF': 2}


def test_fatigue_slope2_applies_same_thickness_reference_as_slope1():
    # Relocated from test_calc_structure_regression_guards.py when the
    # buckling tests moved to the ANYbuckling repository.
    fatigue = calc.CalcFatigue(_with_panel_default(ex.obj_dict), deepcopy(ex.fat_obj_dict))
    baseline = fatigue.get_damage_slope2(0, "Ec", int_press=0, ext_press=50_000)

    fatigue._plate_th = 0.05
    doubled_thickness = fatigue.get_damage_slope2(0, "Ec", int_press=0, ext_press=50_000)

    assert doubled_thickness < baseline
    assert doubled_thickness == pytest.approx(4.6011397118183774e-06)
