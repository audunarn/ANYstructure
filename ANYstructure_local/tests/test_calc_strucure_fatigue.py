import ANYstructure_local.calc_structure as calc
import pytest
import ANYstructure_local.example_data as ex

# Testing the Structure class

@pytest.fixture
def fatigue_cls():
    return calc.CalcFatigue(ex.obj_dict, ex.fat_obj_dict), calc.CalcFatigue(ex.obj_dict2, ex.fat_obj_dict), \
           calc.CalcFatigue(ex.obj_dict_L, ex.fat_obj_dict)

def test_fatigue_damage(fatigue_cls):
    int_press = (0, 0, 0)
    ext_press = (50000, 60000, 0)
    item1 = fatigue_cls[0].get_total_damage(int_press=int_press, ext_press=ext_press)
    item2 = fatigue_cls[1].get_total_damage(int_press=int_press, ext_press=ext_press)
    item3 = fatigue_cls[2].get_total_damage(int_press=int_press, ext_press=ext_press)
    assert item1 == 0.704573599699811
    assert item2 == 0.07762644793304843
    assert item3 == 2.8810958846658474

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
