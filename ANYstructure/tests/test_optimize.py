import ANYstructure.optimize as opt
import ANYstructure.example_data as ex
import ANYstructure.calc_structure as calc
import numpy as np
import pytest

# Testing the Structure class

@pytest.fixture
def opt_input():
    obj_dict = ex.obj_dict
    fat_obj = ex.get_fatigue_object()
    fp = ex.get_fatigue_pressures()
    fat_press = ((fp['p_ext']['loaded'],fp['p_ext']['ballast'],fp['p_ext']['part']),
                 (fp['p_int']['loaded'],fp['p_int']['ballast'],fp['p_int']['part']))
    x0 = [obj_dict['spacing'][0], obj_dict['plate_thk'][0], obj_dict['stf_web_height'][0], obj_dict['stf_web_thk'][0],
          obj_dict['stf_flange_width'][0], obj_dict['stf_flange_thk'][0], obj_dict['span'][0], 10]
    obj = calc.Structure(obj_dict)
    lat_press = 271.124
    calc_object = calc.CalcScantlings(obj_dict)
    upper_bounds = np.array([0.6, 0.01, 0.3, 0.01, 0.1, 0.01, 3.5, 10])
    lower_bounds = np.array([0.8, 0.02, 0.5, 0.02, 0.22, 0.03, 3.5, 10])
    deltas = np.array([0.05, 0.005, 0.05, 0.005, 0.05, 0.005])
    return obj, upper_bounds, lower_bounds, lat_press, deltas, fat_obj, fat_press, x0

def test_optimization(opt_input):
    obj, upper_bounds, lower_bounds, lat_press, deltas, fat_obj, fat_press, x0 = opt_input
    results = opt.run_optmizataion(obj, upper_bounds, lower_bounds, lat_press, deltas, algorithm='anysmart',
                                   fatigue_obj=fat_obj, fat_press_ext_int=fat_press)[0]

    assert results.get_structure_prop() ==  {'mat_yield': [355000000.0, 'Pa'], 'span': [4, 'm'], 'spacing': [0.65, 'm'],
                                             'plate_thk': [0.015, 'm'], 'stf_web_height': [0.3, 'm'],
                                             'stf_web_thk': [0.01, 'm'], 'stf_flange_width': [0.15, 'm'],
                                             'stf_flange_thk': [0.025, 'm'], 'structure_type': ['BOTTOM', ''],
                                             'stf_type': ['T', ''], 'sigma_y1': [80.0, 'MPa'],
                                             'sigma_y2': [80.0, 'MPa'], 'sigma_x': [89.9820895522388, 'MPa'],
                                             'tau_xy': [5.0, 'MPa'], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
                                             'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, '']}

def test_weight_calc(opt_input):
    assert opt.calc_weight(opt_input[-1]) == 8873.64
