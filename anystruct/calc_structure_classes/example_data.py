from .material import Material
from .plate import Plate
from .stiffener import Stiffener
from .stress import Stress
from .stiffened_panel import StiffenedPanel
from .buckling_input import BucklingInput

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
