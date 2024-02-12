import pytest
import sys
sys.path.append(".")
from anystruct import example_data as ex, calc_structure as calc


# Testing the Structure class

@pytest.fixture
def structure_cls():
    return calc.Structure(ex.obj_dict), calc.Structure(ex.obj_dict2), calc.Structure(ex.obj_dict_L)

def test_section_modulus(structure_cls):
    sec_mod1 = structure_cls[0].get_section_modulus()
    sec_mod2 = structure_cls[1].get_section_modulus()
    sec_mod3 = structure_cls[2].get_section_modulus()
    assert sec_mod1 == (0.0006303271987905085, 0.003096298566158356)
    assert sec_mod2 == (0.001514995958173724, 0.004116734923760761)
    assert sec_mod3 == (0.0018379700862006152, 0.005438443157566722)

def test_shear_center(structure_cls):
    item1 = structure_cls[0].get_shear_center()
    item2 = structure_cls[1].get_shear_center()
    item3 = structure_cls[2].get_shear_center()
    assert item1 == 0.03894073197367731
    assert item2 == 0.09396749072714805
    assert item3 == 0.10696231835880587

def test_shear_area(structure_cls):
    item1 = structure_cls[0].get_shear_area()
    item2 = structure_cls[1].get_shear_area()
    item3 = structure_cls[2].get_shear_area()
    assert item1 == 0.0036600000000000005
    assert item2 == 0.004776
    assert item3 == 0.006466600000000001

def test_plastic_sec_mod(structure_cls):
    item1 = structure_cls[0].get_plasic_section_modulus()
    item2 = structure_cls[1].get_plasic_section_modulus()
    item3 = structure_cls[2].get_plasic_section_modulus()
    assert item1 == 0.01781929526454241
    assert item2 == 0.009138647999999996
    assert item3 == 0.012164186637142855

def test_moment_of_inertia(structure_cls):
    item1 = structure_cls[0].get_moment_of_intertia()
    item2 = structure_cls[1].get_moment_of_intertia()
    item3 = structure_cls[2].get_moment_of_intertia()
    assert item1 == 0.0001597323702732991
    assert item2 == 0.0004407634325301207
    assert item3 == 0.0006345175505307731

def test_weight(structure_cls):
    item1 = structure_cls[0].get_weight()
    item2 = structure_cls[1].get_weight()
    item3 = structure_cls[2].get_weight()
    assert item1 == 558.2036776404001 
    assert item2 == 625.4879999999999
    assert item3 == 664.697808

def test_cross_section_area(structure_cls):
    item1 = structure_cls[0].get_cross_section_area()
    item2 = structure_cls[1].get_cross_section_area()
    item3 = structure_cls[2].get_cross_section_area()
    assert item1 == 0.021548105680000002
    assert item2 == 0.01992
    assert item3 == 0.0235208

def test_input_properties(structure_cls):
    item1 = structure_cls[0].get_structure_prop()
    item2 = structure_cls[1].get_structure_prop()
    item3 = structure_cls[2].get_structure_prop()
    assert item1 == {'mat_yield': [355000000.0, 'Pa'], 'span': [4, 'm'], 'spacing': [0.75, 'm'],
                     'plate_thk': [0.015, 'm'], 'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.018, 'm'],
                     'stf_flange_width': [0.15, 'm'], 'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''],
                     'plate_kpp': [1, ''], 'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''],
                     'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'],
                     'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
                                             'structure_types': [{'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                                                                   'internals': ['INNER_SIDE','FRAME_WT',
                                                                                 'GENERAL_INTERNAL_WT',
                                                                                 'INTERNAL_ZERO_STRESS_WT',
                                                                                 'INTERNAL_LOW_STRESS_WT'],
                                                                   'non-wt': ['FRAME','GENERAL_INTERNAL_NONWT'],
                                                                   'vertical': ['BBS', 'SIDE_SHELL', 'SSS']},''],
                                              'zstar_optimization': [True, '']}
    assert item2 == {'mat_yield': [355000000.0, 'Pa'], 'span': [4, 'm'], 'spacing': [0.7, 'm'],
                     'plate_thk': [0.018, 'm'], 'stf_web_height': [0.36, 'm'], 'stf_web_thk': [0.012, 'm'],
                     'stf_flange_width': [0.15, 'm'], 'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''],
                     'plate_kpp': [1, ''], 'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''],
                     'stf_km3': [12, ''], 'sigma_y1': [100, 'MPa'], 'sigma_y2': [100, 'MPa'], 'sigma_x': [50, 'MPa'],
                     'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
                                             'structure_types': [{'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                                                                   'internals': ['INNER_SIDE','FRAME_WT',
                                                                                 'GENERAL_INTERNAL_WT',
                                                                                 'INTERNAL_ZERO_STRESS_WT',
                                                                                 'INTERNAL_LOW_STRESS_WT'],
                                                                   'non-wt': ['FRAME','GENERAL_INTERNAL_NONWT'],
                                                                   'vertical': ['BBS', 'SIDE_SHELL', 'SSS']},''],
                                              'zstar_optimization': [True, '']}
    assert item3 == {'mat_yield': [355000000.0, 'Pa'], 'span': [2, 'm'], 'spacing': [0.6, 'm'],
                     'plate_thk': [0.01, 'm'], 'stf_web_height': [0.188, 'm'], 'stf_web_thk': [0.009, 'm'],
                     'stf_flange_width': [0.09, 'm'], 'stf_flange_thk': [0.012, 'm'], 'structure_type': ['BOTTOM', ''],
                     'plate_kpp': [0.5, ''], 'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''],
                     'stf_km3': [12, ''], 'sigma_y1': [30, 'MPa'], 'sigma_y2': [5, 'MPa'], 'sigma_x': [15, 'MPa'],
                     'tau_xy': [20, 'MPa'], 'stf_type': ['L', ''],
                                             'structure_types': [{'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                                                                   'internals': ['INNER_SIDE','FRAME_WT',
                                                                                 'GENERAL_INTERNAL_WT',
                                                                                 'INTERNAL_ZERO_STRESS_WT',
                                                                                 'INTERNAL_LOW_STRESS_WT'],
                                                                   'non-wt': ['FRAME','GENERAL_INTERNAL_NONWT'],
                                                                   'vertical': ['BBS', 'SIDE_SHELL', 'SSS']},''],
                                              'zstar_optimization': [True, '']}

