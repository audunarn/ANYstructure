import pprint
from ANYstructure_local.calc_structure import *

structure_types = {'vertical': ['BBS', 'SIDE_SHELL', 'SSS'],
                         'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                         'non-wt': ['FRAME', 'GENERAL_INTERNAL_NONWT'],
                         'internals': ['INNER_SIDE', 'FRAME_WT', 'GENERAL_INTERNAL_WT',
                                       'INTERNAL_ZERO_STRESS_WT', 'INTERNAL_LOW_STRESS_WT']}

obj_dict = {'mat_yield': [355e6, 'Pa'], 
            'mat_factor': [1.15, ''],
            'span': [3.7, 'm'],
            'spacing': [0.75, 'm'],
            'plate_thk': [0.018, 'm'],
            'stf_web_height': [0.4, 'm'],
            'stf_web_thk': [0.012, 'm'],
            'stf_flange_width': [0.25, 'm'],
            'stf_flange_thk': [0.014, 'm'],
            'structure_type': ['BOTTOM', ''],
            'plate_kpp': [1, ''],
            'stf_kps': [1, ''],
            'stf_km1': [12, ''],
            'stf_km2': [24, ''],
            'stf_km3': [12, ''],
            'sigma_y1': [100, 'MPa'],
            'sigma_y2': [100, 'MPa'],
            'sigma_x2': [102.7, 'MPa'],
            'sigma_x1': [102.7, 'MPa'],
            'tau_xy': [5, 'MPa'],
            'stf_type': ['T', ''],
            'structure_types': [structure_types, ''],
            'zstar_optimization': [True, ''],
            'puls buckling method':[1,''],
            'puls boundary':['Int',''],
            'puls stiffener end':['C',''],
            'puls sp or up':['SP',''],
            'puls up boundary' :['SSSS',''],
            'panel or shell': ['panel', ''],
            'pressure side': ['both sides', ''],
            'girder_lg': [5, 'm']}

obj_dict_unitless = {'mat_yield': [355e6, ''], 'mat_factor': [1.15, ''],'span': [3.7, ''], 'spacing': [0.75, ''],
            'plate_thk': [0.018, ''],
            'stf_web_height': [0.4, ''], 'stf_web_thk': [0.012, ''], 'stf_flange_width': [0.25, ''],
            'stf_flange_thk': [0.014, ''], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
            'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
            'sigma_y1': [100, ''], 'sigma_y2': [100, ''], 'sigma_x2': [102.7, ''], 'sigma_x1': [102.7, ''],
            'tau_xy': [5, ''],
            'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
            'puls buckling method':[1,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
            'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''], 'panel or shell': ['panel', ''],
            'pressure side': ['both sides', ''], 'girder_lg': [5, '']}

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
prescriptive_main_dict['stiffener distance between lateral support']  = [None, '']
prescriptive_main_dict['girder distance between lateral support']  = [None, '']
# the following doesn't seem to exist in the class anymore
#prescriptive_main_dict['kgirder']  = [None, '']
prescriptive_main_dict['panel length, Lp']  = [None, '']
prescriptive_main_dict['pressure side']  = ['both sides', '']# either 'stiffener', 'plate', 'both'
prescriptive_main_dict['fabrication method stiffener'] =  ['welded', '']
prescriptive_main_dict['fabrication method girder'] =   ['welded', '']
prescriptive_main_dict['calculation domain'] = ['Flat plate, stiffened', '']

def main():
    # Prescriptive buckling UPDATED
    Plate = CalcScantlings(obj_dict_unitless)
    Stiffener = CalcScantlings(obj_dict_unitless)
    Girder = CalcScantlings(obj_dict_heavy)
    PreBuc = AllStructure(Plate = Plate, Stiffener = Stiffener, Girder = Girder,
                                  main_dict=prescriptive_main_dict)
    print('Results from scantling calculation for plate:')
    print(Plate)
    print('Results from scantling calculation for stiffener:')
    print(Stiffener)
    print('Results from scantling calculation for girder:')
    print(Girder)

    PreBuc.lat_press = 0.412197

    print('Results from buckling calculation for stiffened plate:')
    bucklingResult = PreBuc.plate_buckling()
    #pprint.pprint(bucklingResult)
    for key, value in bucklingResult.items():
        print(key, ': ')
        for key2, value2 in value.items():
            print('\t',key2, ': ', value2)

if __name__ == '__main__':
    main()