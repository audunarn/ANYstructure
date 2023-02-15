# This scripts provide dtat to be used for testing the code


try:
    import calc_loads as load
    import calc_structure as calc_structure
    import make_grid_numpy as grid
except ModuleNotFoundError:
    import ANYstructure.calc_loads as load
    import ANYstructure.calc_structure as calc_structure
    import ANYstructure.make_grid_numpy as grid

import random

structure_types = {'vertical': ['BBS', 'SIDE_SHELL', 'SSS'],
                         'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                         'non-wt': ['FRAME', 'GENERAL_INTERNAL_NONWT'],
                         'internals': ['INNER_SIDE', 'FRAME_WT', 'GENERAL_INTERNAL_WT',
                                       'INTERNAL_ZERO_STRESS_WT', 'INTERNAL_LOW_STRESS_WT']}

obj_dict = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [3.7, 'm'], 'spacing': [0.75, 'm'],
            'plate_thk': [0.018, 'm'],
            'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.25, 'm'],
            'stf_flange_thk': [0.014, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [100, 'MPa'], 'sigma_y2': [100, 'MPa'], 'sigma_x2': [102.7, 'MPa'], 'sigma_x1': [102.7, 'MPa'],
            'tau_xy': [5, 'MPa'],
            'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
            'puls buckling method':[1,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''], 'panel or shell': ['panel', ''],
            'pressure side': ['both sides', ''], 'girder_lg': [5, 'm']}

obj_dict_cyl_long = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
                    'plate_thk': [0.015, 'm'],
                    'stf_web_height': [0.38, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
                    'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
                    'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
                    'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
                    'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                    'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
                    'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

obj_dict_cyl_ring = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
                    'plate_thk': [0.015, 'm'],
                    'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.046, 'm'],
                    'stf_flange_thk': [0.024957, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
                    'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
                    'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
                    'stf_type': ['L-bulb', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                    'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
                    'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

obj_dict_cyl_heavy_ring = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
                    'plate_thk': [0.015, 'm'],
                    'stf_web_height': [0.77, 'm'], 'stf_web_thk': [0.014, 'm'], 'stf_flange_width': [0.2, 'm'],
                    'stf_flange_thk': [0.03, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
                    'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
                    'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
                    'stf_type': ['L-bulb', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                    'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
                    'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

obj_dict_cyl_long2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.65, 'm'],
                    'plate_thk': [0.02, 'm'],
                    'stf_web_height': [0.24-0.0249572753957594, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.046, 'm'],
                    'stf_flange_thk': [0.0249572753957594, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
                    'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
                    'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
                    'stf_type': ['L-bulb', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                    'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
                    'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

obj_dict_cyl_ring2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.7, 'm'],
                    'plate_thk': [0.020, 'm'],
                    'stf_web_height': [0.3, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.12, 'm'],
                    'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
                    'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
                    'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
                    'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                    'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
                    'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

obj_dict_cyl_heavy_ring2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
                    'plate_thk': [0.015, 'm'],
                    'stf_web_height': [0.7, 'm'], 'stf_web_thk': [0.016, 'm'], 'stf_flange_width': [0.2, 'm'],
                    'stf_flange_thk': [0.03, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
                    'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
                    'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
                    'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                    'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
                    'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }


obj_dict_heavy = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [3700, 'm'], 'spacing': [0.75, 'm'],
            'plate_thk': [0.018, 'm'],
            'stf_web_height': [0.500, 'm'], 'stf_web_thk': [0.0120, 'm'], 'stf_flange_width': [0.150, 'm'],
            'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
            'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                  'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''], 'panel or shell': ['panel', ''],
            'pressure side': ['both sides', '']}

obj_dict2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [4, 'm'], 'spacing': [0.7, 'm'],
            'plate_thk': [0.018, 'm'],
            'stf_web_height': [0.36, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
            'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [100, 'MPa'], 'sigma_y2': [100, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [50, 'MPa'], 'tau_xy': [5, 'MPa'],
            'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
             'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] }

obj_dict_sec_error = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [3.5, 'm'], 'spacing': [0.875, 'm'],
            'plate_thk': [0.023, 'm'],
            'stf_web_height': [0.41, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.17, 'm'],
            'stf_flange_thk': [0.015, 'm'], 'structure_type': ['SIDE_SHELL', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [93, 'MPa'], 'sigma_y2': [93, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [39.7, 'MPa'], 'tau_xy': [2.8, 'MPa'],
            'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
                      'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] }

obj_dict_L = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''], 'span': [3.6, 'm'], 'spacing': [0.82, 'm'],
            'plate_thk': [0.018, 'm'],
            'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.014, 'm'], 'stf_flange_width': [0.072, 'm'],
            'stf_flange_thk': [0.0439, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [0.5, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [102, 'MPa'], 'sigma_y2': [106.9, 'MPa'], 'sigma_x2': [66.8, 'MPa'], 'sigma_x1': [66.8, 'MPa'], 'tau_xy': [20, 'MPa'],
            'stf_type': ['L', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
              'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['panel', ''], 'pressure side': ['both sides', ''] }

obj_dict_fr = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [2.5, 'm'], 'spacing': [0.74, 'm'],
               'plate_thk': [0.018, 'm'],
               'stf_web_height': [0.2, 'm'], 'stf_web_thk': [0.018, 'm'], 'stf_flange_width': [0, 'm'],
               'stf_flange_thk': [0, 'm'], 'structure_type': ['FRAME', ''], 'plate_kpp': [1, ''],
               'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
               'sigma_y1': [150, 'MPa'], 'sigma_y2': [92.22, 'MPa'], 'sigma_x2': [-54.566, 'MPa'], 'sigma_x1': [-54.566, 'MPa'], 'tau_xy': [16.67, 'MPa'],
               'stf_type': ['FB', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
               'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''], 'panel or shell': ['panel', ''], 'pressure side': ['both sides', ''] }

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

fat_obj_dict2 = {'SN-curve': 'Ec','SCF': 1,'Design life': 20, 'n0':10000, 'Weibull': (0.8, 0.8, 0.8),
                'Period': (9, 9, 9), 'Fraction': (1, 0, 0), 'CorrLoc': (0.5, 0.5, 0.5),
                'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations':(0.5, 0.5, 0.5), 'DFF':2}

fat_obj_dict_problematic = {'SN-curve': 'Ec','SCF': 1,'Design life': 20, 'n0':500571428.0, 'Weibull': (0.8, 0.8, 0),
                'Period': (8, 8, 0), 'Fraction': (0.5, 0.5, 0), 'CorrLoc': (0.5, 0.5, 0),
                'Order': ('Loaded', 'Ballast', 'Part'), 'Accelerations':(0.5, 0.5, 0), 'DFF':2}


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
run_dict = {'line3': {'Identification': 'line3', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0,
                      'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T',
                      'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 200.0,
                      'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0,
                      'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0,
                      'Yield stress stiffener': 355.0, 'Axial stress': 101.7, 'Trans. stress 1': 100.0,
                      'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.41261,
                      'In-plane support': 'Int'},
            'line4': {'Identification': 'line4', 'Length of panel': 3900.0,  'Stiffener spacing': 700.0, 'Plate thickness': 18.0,
                                                            'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 250.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 100.5, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.406561, 'In-plane support': 'Int'}, 'line5': {'Identification': 'line5', 'Length of panel': 3800.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 250.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 102.7, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.406575, 'In-plane support': 'Int'}, 'line6': {'Identification': 'line6', 'Length of panel': 3700.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 250.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 102.7, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.412197, 'In-plane support': 'Int'}, 'line7': {'Identification': 'line7', 'Length of panel': 3600.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 250.0, 'Flange thick.': 12.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 101.5, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.422985, 'In-plane support': 'Int'}, 'line8': {'Identification': 'line8', 'Length of panel': 3500.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 250.0, 'Flange thick.': 12.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 101.5, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.438508, 'In-plane support': 'Int'}, 'line9': {'Identification': 'line9', 'Length of panel': 3800.0, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 200.0, 'Flange thick.': 18.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 100.7, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.459639, 'In-plane support': 'Int'}, 'line10': {'Identification': 'line10', 'Length of panel': 3800.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 50.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.487211, 'In-plane support': 'Int'}, 'line11': {'Identification': 'line11', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 500.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 50.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.521418, 'In-plane support': 'Int'}, 'line12': {'Identification': 'line12', 'Length of panel': 3905.1200000000003, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 500.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 50.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.557214, 'In-plane support': 'Int'}, 'line50': {'Identification': 'line50', 'Length of panel': 3000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 200.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.300313, 'In-plane support': 'Int'}, 'line51': {'Identification': 'line51', 'Length of panel': 3199.999999999999, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 200.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.295486, 'In-plane support': 'Int'}, 'line52': {'Identification': 'line52', 'Length of panel': 3400.0000000000005, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 200.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.248226, 'In-plane support': 'Int'}, 'line53': {'Identification': 'line53', 'Length of panel': 3400.0000000000005, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 200.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.214038, 'In-plane support': 'Int'}, 'line54': {'Identification': 'line54', 'Length of panel': 3600.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.196177, 'In-plane support': 'Int'}, 'line55': {'Identification': 'line55', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.189068, 'In-plane support': 'Int'}, 'line56': {'Identification': 'line56', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.105442, 'In-plane support': 'Int'}, 'line57': {'Identification': 'line57', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 340.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 100.0, 'Trans. stress 2': 100.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.155554, 'In-plane support': 'Int'}, 'line31': {'Identification': 'line31', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line32': {'Identification': 'line32', 'Length of panel': 3900.0000000000005, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line33': {'Identification': 'line33', 'Length of panel': 3799.999999999999, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line34': {'Identification': 'line34', 'Length of panel': 3699.999999999999, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line35': {'Identification': 'line35', 'Length of panel': 3600.0000000000014, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line36': {'Identification': 'line36', 'Length of panel': 3500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line37': {'Identification': 'line37', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line38': {'Identification': 'line38', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line39': {'Identification': 'line39', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line40': {'Identification': 'line40', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 14.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 3.0, 'Pressure (fixed)': 0.0325, 'In-plane support': 'Int'}, 'line13': {'Identification': 'line13', 'Length of panel': 4000.0, 'Stiffener spacing': 775.0, 'Plate thickness': 20.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 450.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line14': {'Identification': 'line14', 'Length of panel': 4000.0, 'Stiffener spacing': 775.0, 'Plate thickness': 20.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 450.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line15': {'Identification': 'line15', 'Length of panel': 4000.0, 'Stiffener spacing': 775.0, 'Plate thickness': 20.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 450.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line16': {'Identification': 'line16', 'Length of panel': 3699.999999999999, 'Stiffener spacing': 775.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 375.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 18.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line17': {'Identification': 'line17', 'Length of panel': 3600.0000000000014, 'Stiffener spacing': 775.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 375.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 18.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line18': {'Identification': 'line18', 'Length of panel': 3500.0, 'Stiffener spacing': 775.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 375.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 18.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line19': {'Identification': 'line19', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 775.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 375.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 18.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line20': {'Identification': 'line20', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 775.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 375.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 18.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line41': {'Identification': 'line41', 'Length of panel': 5000.0, 'Stiffener spacing': 775.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 500.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 25.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.436313, 'In-plane support': 'Int'}, 'line43': {'Identification': 'line43', 'Length of panel': 3199.999999999999, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.393657, 'In-plane support': 'Int'}, 'line44': {'Identification': 'line44', 'Length of panel': 3400.0000000000005, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.348157, 'In-plane support': 'Int'}, 'line45': {'Identification': 'line45', 'Length of panel': 3400.0000000000005, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.299813, 'In-plane support': 'Int'}, 'line46': {'Identification': 'line46', 'Length of panel': 3600.0000000000014, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.251469, 'In-plane support': 'Int'}, 'line47': {'Identification': 'line47', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.200281, 'In-plane support': 'Int'}, 'line48': {'Identification': 'line48', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.14625, 'In-plane support': 'Int'}, 'line49': {'Identification': 'line49', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 325.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 16.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 80.0, 'Trans. stress 2': 80.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.089375, 'In-plane support': 'Int'}, 'line58': {'Identification': 'line58', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line59': {'Identification': 'line59', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line61': {'Identification': 'line61', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line62': {'Identification': 'line62', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line63': {'Identification': 'line63', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line64': {'Identification': 'line64', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line65': {'Identification': 'line65', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line66': {'Identification': 'line66', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line21': {'Identification': 'line21', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line42': {'Identification': 'line42', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line22': {'Identification': 'line22', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line67': {'Identification': 'line67', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line68': {'Identification': 'line68', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line69': {'Identification': 'line69', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line70': {'Identification': 'line70', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line71': {'Identification': 'line71', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line72': {'Identification': 'line72', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line73': {'Identification': 'line73', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line60': {'Identification': 'line60', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 0.0, 'Flange thick.': 0.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 60.0, 'Trans. stress 1': 70.0, 'Trans. stress 2': 70.0, 'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'Int'}, 'line1': {'Identification': 'line1', 'Length of panel': 2500.0, 'Stiffener spacing': 700.0, 'Plate thickness': 14.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 250.0, 'Web thick.': 18.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 20.0, 'Trans. stress 1': 40.0, 'Trans. stress 2': 40.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.47186, 'In-plane support': 'Int'}, 'line2': {'Identification': 'line2', 'Length of panel': 3000.0, 'Stiffener spacing': 700.0, 'Plate thickness': 16.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'F', 'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 18.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 20.0, 'Trans. stress 1': 40.0, 'Trans. stress 2': 40.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.387068, 'In-plane support': 'Int'}, 'line23': {'Identification': 'line23', 'Length of panel': 3000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 15.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 350.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.387068, 'In-plane support': 'Int'}, 'line24': {'Identification': 'line24', 'Length of panel': 3200.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 350.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.349613, 'In-plane support': 'Int'}, 'line25': {'Identification': 'line25', 'Length of panel': 3400.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 350.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.309662, 'In-plane support': 'Int'}, 'line26': {'Identification': 'line26', 'Length of panel': 3400.0, 'Stiffener spacing': 750.0, 'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 320.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.267214, 'In-plane support': 'Int'}, 'line27': {'Identification': 'line27', 'Length of panel': 3600.0000000000014, 'Stiffener spacing': 750.0, 'Plate thickness': 15.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 320.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.224765, 'In-plane support': 'Int'}, 'line28': {'Identification': 'line28', 'Length of panel': 3800.000000000001, 'Stiffener spacing': 750.0, 'Plate thickness': 15.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 320.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.17982, 'In-plane support': 'Int'}, 'line29': {'Identification': 'line29', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 15.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 300.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.132378, 'In-plane support': 'Int'}, 'line30': {'Identification': 'line30', 'Length of panel': 4000.0, 'Stiffener spacing': 750.0, 'Plate thickness': 15.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T', 'Stiffener boundary': 'C', 'Stiff. Height': 300.0, 'Web thick.': 12.0, 'Flange width': 150.0, 'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0, 'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0, 'Yield stress stiffener': 355.0, 'Axial stress': 40.0, 'Trans. stress 1': 90.0, 'Trans. stress 2': 90.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.082439, 'In-plane support': 'Int'}}
run_dict_one = {'line3': {'Identification': 'line3', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0,
                          'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T',
                          'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 200.0,
                          'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0,
                          'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0,
                          'Yield stress stiffener': 355.0, 'Axial stress': 101.7, 'Trans. stress 1': 100.0,
                          'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.41261,
                          'In-plane support': 'Int'}}

shell_dict = {'plate_thk': [20 / 1000, 'm'],
              'radius': [5000 / 1000, 'm'],
              'distance between rings, l': [700 / 1000, 'm'],
              'length of shell, L': [5000 / 1000, 'm'],
              'tot cyl length, Lc': [5000 / 1000, 'm'],
              'eff. buckling lenght factor': [1, ''],
              'mat_yield': [355 * 1e6, 'Pa'],
              }

shell_main_dict = {'sasd': [-10e6, 'Pa'],
                     'smsd': [-10e6, 'Pa'],
                     'tTsd': [40* 1e6, 'Pa'],
                     'tQsd': [40* 1e6, 'Pa'],
                     'psd': [-0.1e6, 'Pa'],
                     'shsd': [0, 'Pa'],
                     'geometry': [3, '-'],
                     'material factor': [1.15, ''],
                     'delta0': [0.005, ''],
                     'fab method ring stf': [1, ''],
                     'fab method ring girder': [1, ''],
                     'E-module': [2.1e11, 'Pa'],
                     'poisson': [0.3, '-'],
                     'mat_yield': [355 * 1e6, 'Pa'],
                   'length between girders' : [None, 'm'],
                   'panel spacing, s' : [2, 'm'],
                   'ring stf excluded' : [False, ''],
                   'ring frame excluded' : [True, ''],
                   'end cap pressure': ['not included in axial stresses', ''],
                   'ULS or ALS': ['ULS', '']}


'''
        self._length_between_girders = main_dict['length between girders'][0]
        self._panel_spacing = main_dict['panel spacing, s'][0]
        self.__ring_stiffener_excluded = main_dict['ring stf excluded'][0]
        self.__ring_frame_excluded = main_dict['ring frame excluded'][0]'''
shell_main_dict2 = {'sasd': [79.58 * 1e6, 'Pa'],
             'smsd': [31.89* 1e6, 'Pa'],
             'tTsd': [12.73* 1e6, 'Pa'],
             'tQsd': [4.77* 1e6, 'Pa'],
             'psd': [-0.2* 1e6, 'Pa'],
             'shsd': [0, 'Pa'],
             'geometry': [5, '-'],
             'material factor': [1.15, ''],
             'delta0': [0.005, ''],
             'fab method ring stf': [1, ''],
             'fab method ring girder': [1, ''],
             'E-module': [2.1e11, 'Pa'],
             'poisson': [0.3, '-'],
             'mat_yield': [355 * 1e6, 'Pa'],
                    'length between girders': [None, 'm'],
                    'panel spacing, s': [0.7, 'm'],
                    'ring stf excluded': [False, ''],
                    'ring frame excluded': [True, ''],
                    'end cap pressure': ['not included in axial stresses', ''],
                   'ULS or ALS': ['ULS', '']}

prescriptive_main_dict = dict()
prescriptive_main_dict['minimum pressure in adjacent spans']  = [None, '']
prescriptive_main_dict['material yield']  = [355e6, 'Pa']
prescriptive_main_dict['load factor on stresses']  = [1, '']
prescriptive_main_dict['load factor on pressure']  = [1, '']
prescriptive_main_dict['buckling method']  = ['ultimate', '']
prescriptive_main_dict['stiffener end support']  = ['Continuous', '']  # 'Continuous'
prescriptive_main_dict['girder end support']  = ['Continuous', '']  # 'Continuous'
prescriptive_main_dict['tension field']  = ['not allowed', '']  # 'not allowed'
prescriptive_main_dict['plate effective agains sigy']   = [True, ''] # True
prescriptive_main_dict['buckling length factor stf']  = [None, '']
prescriptive_main_dict['buckling length factor girder']  = [None, '']
prescriptive_main_dict['km3']  = [12, '']  # 12
prescriptive_main_dict['km2']  = [24, '']  # 24
prescriptive_main_dict['girder distance between lateral support']  = [None, '']
prescriptive_main_dict['stiffener distance between lateral support']  = [None, '']
prescriptive_main_dict['kgirder']  = [None, '']
prescriptive_main_dict['panel length, Lp']  = [None, '']
prescriptive_main_dict['pressure side']  = ['both sides', '']# either 'stiffener', 'plate', 'both'
prescriptive_main_dict['fabrication method stiffener'] =  ['welded', '']
prescriptive_main_dict['fabrication method girder'] =   ['welded', '']
prescriptive_main_dict['calculation domain'] = ['Flat plate, stiffened', '']

def get_slamming_pressure():
    return 1000000

def get_fatigue_pressures():
    return {'p_ext':{'loaded':50000,'ballast':60000,'part':0}, 'p_int':{'loaded':0, 'ballast':20000,'part':0}}

def get_fatigue_pressures_problematic():
    return {'p_ext': {'loaded': 192632, 'ballast': 198705.5, 'part': 0},
            'p_int': {'loaded': 0, 'ballast': 15118, 'part': 0}}

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
        return calc_structure.CalcScantlings(obj_dict_fr)
    else:
        return calc_structure.CalcScantlings(obj_dict)

def get_structure_calc_object(line=None, heavy = False):
    if line in ('line12','line13','line11','line4'):
        return calc_structure.CalcScantlings(obj_dict_fr)
    else:
        return calc_structure.CalcScantlings(obj_dict if not heavy else obj_dict_heavy)

def get_fatigue_object():
    return calc_structure.CalcFatigue(obj_dict, fat_obj_dict)

def get_fatigue_object_problematic():
    return calc_structure.CalcFatigue(obj_dict_sec_error, fat_obj_dict_problematic)

def get_tank_object():
    return load.Tanks(tank_dict=tank_dict_ballast)

def get_line_to_struc(geo = False):
    to_return = {}
    for line in line_dict.keys():
        Plate = get_structure_object(line)
        Stiffener = get_structure_object(line)
        Girder = None  # CalcScantlings(ex.obj_dict_heavy)
        initial_calc_obj = calc_structure.AllStructure(Plate=Plate, Stiffener=Stiffener, Girder=Girder,
                                              main_dict=prescriptive_main_dict)
        to_return[line]=[initial_calc_obj, None, None, [None], {}]
    return to_return

def get_default_stresses():
    return {'BOTTOM':(100,100,50,50,5), 'BBS':(70,70,30,30,3), 'BBT':(80,80,30,3), 'HOPPER':(70,70,50,50,3),
                                 'SIDE_SHELL':(100,100,40,40,3),'INNER_SIDE':(80,80,40,40,5), 'FRAME':(70,70,60,0,10),
                                 'FRAME_WT':(70,70,60,0,10),'SSS':(100,100,50,50,20), 'MD':(70,70,4,40,3),
                                 'GENERAL_INTERNAL_WT':(90,90,40,40,5),'GENERAL_INTERNAL_NONWT':(70,70,30,30,3),
                                  'INTERNAL_1_MPA':(1,1,1,1,1), 'INTERNAL_LOW_STRESS_WT':(40,40,20,20,5)}

def get_opt_frames():
    return opt_frames,['point1', 'point4', 'point8', 'point5']

def get_point_dict():
    return point_dict

def get_line_dict():
    return line_dict

def get_grid(origo,base_canvas_dim):
    return grid.Grid(origo[1] + 1, base_canvas_dim[0] - origo[0] + 1)

def get_grid_no_inp(empty_grid = False):

    origo = (50,670)
    base_canvas_dim = [1000,720]
    grid_return = grid.Grid(origo[1] + 1, base_canvas_dim[0] - origo[0] + 1)
    if empty_grid:
        return grid_return

    for line,coords in get_to_draw().items():
        for point in grid_return.get_points_along_line(coords[0],coords[1]):
            grid_return.set_barrier(point[0],point[1])
    return grid_return

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
             'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
              'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''] },
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
              'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
              'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
              'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''] },
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
              'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''] },
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['GENERAL_INTERNAL_WT', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
              'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''] },
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['GENERAL_INTERNAL_WT', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
              'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''] },
             {'mat_yield': [355000000.0, 'Pa'], 'span': [4.0, 'm'], 'spacing': [0.7, 'm'], 'plate_thk': [0.015, 'm'],
              'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
              'stf_flange_thk': [0.02, 'm'], 'structure_type': ['GENERAL_INTERNAL_WT', ''], 'plate_kpp': [1, ''], 'stf_kps': [1, ''],
              'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''], 'sigma_y1': [80, 'MPa'],
              'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'], 'stf_type': ['T', ''],
              'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''] })
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

def get_section_list():
    ''' Returning a section list. '''
    import pl_stf_window as plstf
    return [plstf.Section(obj_dict), plstf.Section(obj_dict2), plstf.Section(obj_dict_L)]



if __name__ == '__main__':
    print(get_random_color())




