# This scripts provide dtat to be used for testing the code

import ANYstructure.make_grid_numpy as grid
import ANYstructure.calc_loads as load
import ANYstructure.calc_structure as calc_structure
import random

obj_dict = {'mat_yield': [355e6, 'Pa'], 'span': [4, 'm'], 'spacing': [0.75, 'm'],
            'plate_thk': [0.015, 'm'],
            'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.018, 'm'], 'stf_flange_width': [0.15, 'm'],
            'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
            'stf_type': ['T', '']}

obj_dict_heavy = {'mat_yield': [355e6, 'Pa'], 'span': [4, 'm'], 'spacing': [0.75, 'm'],
            'plate_thk': [0.015, 'm'],
            'stf_web_height': [0.5, 'm'], 'stf_web_thk': [0.025, 'm'], 'stf_flange_width': [0.2, 'm'],
            'stf_flange_thk': [0.03, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
            'stf_type': ['T', '']}

obj_dict2 = {'mat_yield': [355e6, 'Pa'], 'span': [4, 'm'], 'spacing': [0.7, 'm'],
            'plate_thk': [0.018, 'm'],
            'stf_web_height': [0.36, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
            'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [100, 'MPa'], 'sigma_y2': [100, 'MPa'], 'sigma_x': [50, 'MPa'], 'tau_xy': [5, 'MPa'],
            'stf_type': ['T', '']}

obj_dict_L = {'mat_yield': [355e6, 'Pa'], 'span': [2, 'm'], 'spacing': [0.6, 'm'],
            'plate_thk': [0.010, 'm'],
            'stf_web_height': [0.188, 'm'], 'stf_web_thk': [0.009, 'm'], 'stf_flange_width': [0.09, 'm'],
            'stf_flange_thk': [0.012, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [0.5, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [30, 'MPa'], 'sigma_y2': [5, 'MPa'], 'sigma_x': [15, 'MPa'], 'tau_xy': [20, 'MPa'],
            'stf_type': ['L', '']}

obj_dict_fr = {'mat_yield': [355e6, 'Pa'], 'span': [3.5, 'm'], 'spacing': [0.7, 'm'],
               'plate_thk': [0.015, 'm'],
               'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
               'stf_flange_thk': [0.02, 'm'], 'structure_type': ['FRAME', ''], 'plate_kpp': [1, ''],
               'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
               'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
               'stf_type': ['T', '']}

point_dict = {'point5': [12.0, 2.5], 'point8': [0.0, 2.5], 'point3': [8.0, 0.0], 'point2': [4.0, 0.0],
              'point6': [8.0, 2.5], 'point7': [4.0, 2.5], 'point9': [0.0, 20.0], 'point4': [12.0, 0.0],
              'point10': [12.0, 20.0], 'point1': [0.0, 0.0]}

line_dict = {'line8': [9, 8], 'line6': [7, 6], 'line12': [2, 7], 'line3': [3, 4], 'line13': [3, 6], 'line1': [1, 2],
             'line10': [5, 10], 'line11': [1, 8], 'line7': [7, 8], 'line9': [9, 10], 'line5': [5, 6],
             'line4': [5, 4], 'line2': [3, 2]}

opt_frames = {'opt_frame1': [[2.4, 0.0], [2.4, 2.5]], 'opt_frame2': [[4.8, 0.0], [4.8, 2.5]],
              'opt_frame3': [[7.2, 0.0], [7.2, 2.5]], 'opt_frame4': [[9.6, 0.0], [9.6, 2.5]],
              'opt_frame_start': [[0.0, 0.0], [0.0, 2.5]], 'opt_frame_stop': [[12.0, 0.0], [12.0, 2.5]]}

fat_obj_dict = {'SN-curve': 'Ec','SCF': 1,'Design life': 20, 'n0':10000, 'Weibull': (0.8, 0.8, 0.8),
                'Period': (9, 9, 9), 'Fraction': (1, 0, 0), 'CorrLoc': (0.5, 0.5, 0.5),
                'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations':(0.5, 0.5, 0.5), 'DFF':2}

fat_obj_dict2 = {'SN-curve': 'Ec','SCF': 1,'Design life': 20, 'n0':10000, 'Weibull': (0, 1, 0),
                'Period': (0, 9, 0), 'Fraction': (0, 1, 0), 'CorrLoc': (0, 0.5, 0),
                'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations':(0, 2, 0), 'DFF':2}

loa_fls = {'static_draft':None,'poly_third':1,'poly_second':50,'poly_first':10,'poly_const':5000,'man_press':0,
           'load_condition':'loaded','name_of_load':'test_load_laoded_FLS','limit_state':'FLS'}

loa_uls = {'static_draft':None,'poly_third':2,'poly_second':20,'poly_first':20,'poly_const':2000,'man_press':0,
           'load_condition':'loaded','name_of_load':'test_load_loaded_ULS','limit_state':'ULS'}

bal_fls = {'static_draft':None,'poly_third':5.5,'poly_second':10,'poly_first':5.5,'poly_const':1000,'man_press':0,
           'load_condition':'ballast','name_of_load':'test_load_ballast_FLS','limit_state':'FLS'}

bal_uls = {'static_draft':None,'poly_third':2,'poly_second':20,'poly_first':20,'poly_const':2000,'man_press':0,
           'load_condition':'ballast','name_of_load':'test_load_ballast_ULS','limit_state':'ULS'}

tank_dict_ballast = {'acc': {'dyn_ballast': 3.0, 'dyn_loaded': 3.0, 'static': 9.81}, 'added_press': 25000.0,
                     'cells': 10632,'comp_no': 4, 'content': 'ballast', 'density': 1025.0, 'max_el': 20.0,
                     'min_el': 0.0}

comp2 = {'acc': {'static': 9.81, 'dyn_ballast': 3.0, 'dyn_loaded': 3.0}, 'max_el': 29.5, 'added_press': 25000.0,
         'cells': 29591, 'density': 1025.0, 'content': 'crude_oil', 'comp_no': 2, 'min_el': 2.5}
comp3 = {'acc': {'static': 9.81, 'dyn_ballast': 3.0, 'dyn_loaded': 3.0}, 'max_el': 29.5, 'added_press': 25000.0,
         'cells': 19638, 'density': 1025.0, 'content': 'crude_oil', 'comp_no': 3, 'min_el': 2.5}
comp4 = {'acc': {'static': 9.81, 'dyn_ballast': 3.0, 'dyn_loaded': 3.0}, 'max_el': 29.5, 'added_press': 25000.0,
         'cells': 19072, 'density': 1025.0, 'content': 'ballast', 'comp_no': 4, 'min_el': 0.0}

load_side = {'poly_third': 0.0, 'poly_second': 303.0, 'poly_first': -3750.0, 'poly_const': 153000.0,
             'load_condition': 'ballast', 'structure_type': None, 'man_press': None, 'static_draft': None,
             'name_of_load': 'ballast_side', 'limit_state': 'ULS'}
load_bottom = {'poly_third': 0.0, 'poly_second': 31.0, 'poly_first': -83.0, 'poly_const': 45800.0,
               'load_condition': 'ballast', 'structure_type': None, 'man_press': None, 'static_draft': None,
               'name_of_load': 'ballast_bottom', 'limit_state': 'ULS'}
load_static = {'poly_third': None, 'poly_second': None, 'poly_first': None, 'poly_const': None,
               'load_condition': 'ballast', 'structure_type': None, 'man_press': None, 'static_draft': 15.0,
               'name_of_load': 'ballast_static', 'limit_state': 'ULS'}
load_slamming = {'poly_third': 0, 'poly_second': 0, 'poly_first': 0, 'poly_const': 1000000.0,
                 'load_condition': 'slamming', 'structure_type': None, 'man_press': None, 'static_draft': None,
                 'name_of_load': 'slamming', 'limit_state': None}

ex_comp1 = {'comp_no': 2, 'cells': 32829, 'min_el': 2.5, 'max_el': 30.9, 'content': '', 'added_press': 25000.0,
            'acc': {'static': 9.81, 'dyn_loaded': 3.0, 'dyn_ballast': 3.0}, 'density': 1025.0,
            'all_types': ['BOTTOM', 'BBS', 'BBT', 'HOPPER', 'SIDE_SHELL', 'INNER_SIDE', 'FRAME', 'FRAME_WT',
                          'SSS', 'MD', 'GENERAL_INTERNAL_WT', 'GENERAL_INTERNAL_NONWT', 'INTERNAL_1_MPA',
                          'INTERNAL_LOW_STRESS_WT']}
ex_comp2 = {'comp_no': 3, 'cells': 62530, 'min_el': 2.5, 'max_el': 30.900000000000002, 'content': '',
            'added_press': 25000.0, 'acc': {'static': 9.81, 'dyn_loaded': 3.0, 'dyn_ballast': 3.0},
            'density': 1025.0, 'all_types': ['BOTTOM', 'BBS', 'BBT', 'HOPPER', 'SIDE_SHELL', 'INNER_SIDE', 'FRAME',
                                             'FRAME_WT', 'SSS', 'MD', 'GENERAL_INTERNAL_WT', 'GENERAL_INTERNAL_NONWT',
                                             'INTERNAL_1_MPA', 'INTERNAL_LOW_STRESS_WT']}
ex_comp3 = {'comp_no': 4, 'cells': 14559, 'min_el': 0.0, 'max_el': 30.900000000000002, 'content': '',
            'added_press': 25000.0, 'acc': {'static': 9.81, 'dyn_loaded': 3.0, 'dyn_ballast': 3.0},
            'density': 1025.0, 'all_types': ['BOTTOM', 'BBS', 'BBT', 'HOPPER', 'SIDE_SHELL', 'INNER_SIDE',
                                             'FRAME', 'FRAME_WT', 'SSS', 'MD', 'GENERAL_INTERNAL_WT',
                                             'GENERAL_INTERNAL_NONWT', 'INTERNAL_1_MPA', 'INTERNAL_LOW_STRESS_WT']}
ex_comp4 = {'comp_no': 5, 'cells': 2785, 'min_el': 0.0, 'max_el': 2.5, 'content': '', 'added_press': 25000.0,
            'acc': {'static': 9.81, 'dyn_loaded': 3.0, 'dyn_ballast': 3.0}, 'density': 1025.0,
            'all_types': ['BOTTOM', 'BBS', 'BBT', 'HOPPER', 'SIDE_SHELL', 'INNER_SIDE', 'FRAME', 'FRAME_WT',
                          'SSS', 'MD', 'GENERAL_INTERNAL_WT', 'GENERAL_INTERNAL_NONWT', 'INTERNAL_1_MPA',
                          'INTERNAL_LOW_STRESS_WT']}


def get_slamming_pressure():
    return 1000000

def get_fatigue_pressures():
    return {'p_ext':{'loaded':50000,'ballast':60000,'part':0}, 'p_int':{'loaded':0, 'ballast':20000,'part':0}}

def get_loa_fls_load():
    return load.Loads(loa_fls)

def get_loa_uls_load():
    return load.Loads(loa_uls)

def get_bal_fls_load():
    return load.Loads(bal_fls)

def get_bal_uls_load():
    return load.Loads(bal_uls)

def get_object_dictionary():
    return obj_dict

def get_structure_object(line=None):
    if line in ('line12','line13','line11','line4'):
        return calc_structure.Structure(obj_dict_fr)
    else:
        return calc_structure.Structure(obj_dict)

def get_structure_calc_object(line=None, heavy = False):
    if line in ('line12','line13','line11','line4'):
        return calc_structure.CalcScantlings(obj_dict_fr)
    else:
        return calc_structure.CalcScantlings(obj_dict if not heavy else obj_dict_heavy)

def get_fatigue_object():
    return calc_structure.CalcFatigue(obj_dict, fat_obj_dict)

def get_tank_object():
    return load.Tanks(tank_dict=tank_dict_ballast)

def get_line_to_struc(geo = False):
    to_return = {}
    for line in line_dict.keys():
        to_return[line]=[get_structure_object(line), get_structure_calc_object(), None, [None], {}]
    return to_return

def get_default_stresses():
    return {'BOTTOM':(100,100,50,5), 'BBS':(70,70,30,3), 'BBT':(80,80,30,3), 'HOPPER':(70,70,50,3),
                                 'SIDE_SHELL':(100,100,40,3),'INNER_SIDE':(80,80,40,5), 'FRAME':(70,70,60,10),
                                 'FRAME_WT':(70,70,60,10),'SSS':(100,100,50,20), 'MD':(70,70,40,3),
                                 'GENERAL_INTERNAL_WT':(90,90,40,5),'GENERAL_INTERNAL_NONWT':(70,70,30,3)}

def get_opt_frames():
    return opt_frames,['point1', 'point4', 'point8', 'point5']

def get_point_dict():
    return point_dict

def get_line_dict():
    return line_dict

def get_grid(origo,base_canvas_dim):
    return grid.Grid(origo[1] + 1, base_canvas_dim[0] - origo[0] + 1)

def get_grid_no_inp():
    origo = (50,670)
    base_canvas_dim = [1000,720]
    grid_return = grid.Grid(origo[1] + 1, base_canvas_dim[0] - origo[0] + 1)
    for line,coords in get_to_draw().items():
        for point in grid_return.get_points_along_line(coords[0],coords[1]):
            grid_return.set_barrier(point[0],point[1])
    return  grid_return

def get_grid_empty():
    origo = (50,670)
    base_canvas_dim = [1000,720]
    grid_return = grid.Grid(origo[1] + 1, base_canvas_dim[0] - origo[0] + 1)
    return grid_return

def get_to_draw():
    to_return = {}
    for line in line_dict.keys():
        p1 = line_dict[line][0]
        p2 = line_dict[line][1]
        p1_coord = point_dict['point'+str(p1)]
        p2_coord = point_dict['point'+str(p2)]
        point_coord = (p1_coord,p2_coord)
        to_return[line]= get_grid_coord_from_points_coords(point_coord[0]),\
                         get_grid_coord_from_points_coords(point_coord[1])
    return to_return

def get_geo_opt_presure():
    return (200,200,200,200,200,200)

def get_random_pressure():
    return 150 + 100*random.random()

def get_random_color():
    return random.choice(['red','green','green','green'])

def get_geo_opt_object():
    dicts = ({'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
             'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
             'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
             'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
             'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', '']},
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
              'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
              'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
              'stf_type': ['T', '']},
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', '']},
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['GENERAL_INTERNAL_WT', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', '']},
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['GENERAL_INTERNAL_WT', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', '']},
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['GENERAL_INTERNAL_WT', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', '']})
    return [calc_structure.CalcScantlings(dic) for dic in dicts]

def get_geo_opt_fatigue():
    return [get_fatigue_object() for dummy in range(len(get_geo_opt_presure()))]

def get_geo_opt_fat_press():
    return [get_fatigue_pressures() for dummy in range(len(get_geo_opt_presure()))]

def get_geo_opt_fat_press():
    return [get_fatigue_pressures() for dummy in range(len(get_geo_opt_presure()))]

def get_geo_opt_slamming_none():
    return [0 for dummy in range(len(get_geo_opt_presure()))]

def get_geo_opt_slamming():
    return [get_slamming_pressure() for dummy in range(len(get_geo_opt_presure()))]

def get_grid_coord_from_points_coords(point_coord):
    '''
    Converts coordinates to be used in the grid. Returns (row,col). This value will not change with slider.
    :param point:
    :return:
    '''
    canvas_origo = (50,670)
    row = canvas_origo[1] - point_coord[1]*10
    col = point_coord[0]*10
    return (row,col)



if __name__ == '__main__':
    print(get_random_color())




