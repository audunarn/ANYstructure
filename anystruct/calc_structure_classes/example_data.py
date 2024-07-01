# from .material import Material
# from .plate import Plate
# from .stiffener import Stiffener
# from .stress import Stress
# from .stiffened_panel import StiffenedPanel
# from .buckling_input import BucklingInput

from calc_structure_classes import *

mat_steel_355: Material = Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.1)
plate: Plate = Plate(spacing=0.68, span=3.3, thickness=0.025, material=mat_steel_355)
stiffener: Stiffener = Stiffener(type="T", web_height=0.250297358, web_th=0.012, flange_width=0.052, flange_th=0.029702642, material=mat_steel_355, dist_between_lateral_supp=None)    
stiffened_panel: StiffenedPanel = StiffenedPanel(plate=plate, stiffener=stiffener, stiffener_end_support="continuous", girder_length=5)
stress: Stress = Stress(sigma_x1=102.7e6, sigma_x2=102.7e6, sigma_y1=100, sigma_y2=100, tauxy=5e6)
buckling_input1: BucklingInput = BucklingInput(panel=stiffened_panel, pressure=0, pressure_side="both sides", stress=stress)


mat_steel_355_2: Material = Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
plate2: Plate = Plate(spacing=0.700, span=4.000, thickness=0.018, material=mat_steel_355_2)
stiffener2: Stiffener = Stiffener(type="T", web_height=0.360, web_th=0.012, flange_width=0.150, flange_th=0.020, material=mat_steel_355_2, dist_between_lateral_supp=None)    
stiffened_panel2: StiffenedPanel = StiffenedPanel(plate=plate2, stiffener=stiffener2, stiffener_end_support="continuous", girder_length=5)
stress2: Stress = Stress(sigma_x1=50e6, sigma_x2=80e6, sigma_y1=100e6, sigma_y2=100e6, tauxy=5e6)
buckling_input2: BucklingInput = BucklingInput(panel=stiffened_panel2, pressure=0, pressure_side="both sides", stress=stress2)


mat_steel_355_3: Material = Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
plate3: Plate = Plate(spacing=0.820, span=3.600, thickness=0.018, material=mat_steel_355_3)
stiffener3: Stiffener = Stiffener(type="L", web_height=0.400, web_th=0.014, flange_width=0.072, flange_th=0.0439, material=mat_steel_355_3, dist_between_lateral_supp=None)    
stiffened_panel3: StiffenedPanel = StiffenedPanel(plate=plate3, stiffener=stiffener3, stiffener_end_support="continuous", girder_length=5)
stress3: Stress = Stress(sigma_x1=66.8e6, sigma_x2=66.8e6, sigma_y1=102e6, sigma_y2=106.9e6, tauxy=20e6)
buckling_input3: BucklingInput = BucklingInput(panel=stiffened_panel3, pressure=0, pressure_side="both sides", stress=stress3)


# For the shells, the example data seems not correct. The next is the data, but does not agree with how
# this is passed to the original "CylinderAndCurvedPlate".
# It looks like it is still in the stiffend panel format, but it should be in the shell format.
# obj_dict_cyl_long = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
#                     'plate_thk': [0.015, 'm'],
#                     'stf_web_height': [0.38, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.15, 'm'],
#                     'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
#                     'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
#                     'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
#                     'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
#                     'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
#                     'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

# this is the best I can do with the above data, mainly stress, radius, s and l are missing.
mat_steel_355_shell_1: Material = Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
cyl_stresses: ShellStressAndPressure = ShellStressAndPressure(saSd=-200e6, tQSd=5e6, shSd_add=-60e6)
curved_panel: CurvedPanel = CurvedPanel(thickness=0.015, radius=1, s=0.600, l=5.000, material=mat_steel_355_shell_1)
long_stiff: Stiffener = Stiffener(type='T', web_height=0.380, web_th=0.012, flange_width=0.150, flange_th=0.020, material=mat_steel_355_shell_1)
cyl_long: CylindricalShell = CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      long_stf=long_stiff,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=5.000)



# obj_dict_cyl_ring = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
#                     'plate_thk': [0.015, 'm'],
#                     'stf_web_height': [0.4, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.046, 'm'],
#                     'stf_flange_thk': [0.024957, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
#                     'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
#                     'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
#                     'stf_type': ['L-bulb', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
#                     'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
#                     'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

# obj_dict_cyl_heavy_ring = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
#                     'plate_thk': [0.015, 'm'],
#                     'stf_web_height': [0.77, 'm'], 'stf_web_thk': [0.014, 'm'], 'stf_flange_width': [0.2, 'm'],
#                     'stf_flange_thk': [0.03, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
#                     'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
#                     'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
#                     'stf_type': ['L-bulb', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
#                     'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
#                     'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

# obj_dict_cyl_long2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.65, 'm'],
#                     'plate_thk': [0.02, 'm'],
#                     'stf_web_height': [0.24-0.0249572753957594, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.046, 'm'],
#                     'stf_flange_thk': [0.0249572753957594, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
#                     'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
#                     'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
#                     'stf_type': ['L-bulb', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
#                     'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
#                     'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

# obj_dict_cyl_ring2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.7, 'm'],
#                     'plate_thk': [0.020, 'm'],
#                     'stf_web_height': [0.3, 'm'], 'stf_web_thk': [0.012, 'm'], 'stf_flange_width': [0.12, 'm'],
#                     'stf_flange_thk': [0.02, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
#                     'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
#                     'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
#                     'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
#                     'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
#                     'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }

# obj_dict_cyl_heavy_ring2 = {'mat_yield': [355e6, 'Pa'], 'mat_factor': [1.15, ''],'span': [5, 'm'], 'spacing': [0.6, 'm'],
#                     'plate_thk': [0.015, 'm'],
#                     'stf_web_height': [0.7, 'm'], 'stf_web_thk': [0.016, 'm'], 'stf_flange_width': [0.2, 'm'],
#                     'stf_flange_thk': [0.03, 'm'], 'structure_type': ['BOTTOM', ''], 'plate_kpp': [1, ''],
#                     'stf_kps': [1, ''], 'stf_km1': [12, ''], 'stf_km2': [24, ''], 'stf_km3': [12, ''],
#                     'sigma_y1': [80, 'MPa'], 'sigma_y2': [80, 'MPa'], 'sigma_x2': [80, 'MPa'], 'sigma_x1': [80, 'MPa'], 'tau_xy': [5, 'MPa'],
#                     'stf_type': ['T', ''], 'structure_types': [structure_types, ''], 'zstar_optimization': [True, ''],
#                     'puls buckling method':[2,''], 'puls boundary':['Int',''], 'puls stiffener end':['C',''],
#                     'puls sp or up':['SP',''], 'puls up boundary' :['SSSS',''] , 'panel or shell': ['shell', ''] }