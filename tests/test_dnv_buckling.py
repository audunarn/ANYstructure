import pytest

# this is not proper, but it allows to run this from the root of ANYSTRUCTURE
import sys
sys.path.append(".")
from anystruct.calc_structure_classes.example_data import buckling_input1, buckling_input2, buckling_input3


@pytest.fixture
def structure_cls():
    return buckling_input1, buckling_input2, buckling_input3


def test_section_modulus(structure_cls):
    sec_mod1 = structure_cls[0].panel.stiffener.get_section_modulus(plate_width=structure_cls[0].panel.plate.spacing, plate_thickness=structure_cls[0].panel.plate.thickness)
    sec_mod2 = structure_cls[1].panel.stiffener.get_section_modulus(plate_width=structure_cls[1].panel.plate.spacing, plate_thickness=structure_cls[1].panel.plate.thickness)
    sec_mod3 = structure_cls[2].panel.stiffener.get_section_modulus(plate_width=structure_cls[2].panel.plate.spacing, plate_thickness=structure_cls[2].panel.plate.thickness)
    assert sec_mod1 == (0.0006303271987905085, 0.003096298566158356)
    assert sec_mod2 == (0.001514995958173724, 0.004116734923760761)
    assert sec_mod3 == (0.0018379700862006152, 0.005438443157566722)


def test_shear_center(structure_cls):
    item1 = structure_cls[0].panel.get_shear_center()
    item2 = structure_cls[1].panel.get_shear_center()
    item3 = structure_cls[2].panel.get_shear_center()
    assert item1 == 0.03894073197367731
    assert item2 == 0.09396749072714805
    assert item3 == 0.10696231835880587


def test_shear_area(structure_cls):
    item1 = structure_cls[0].panel.get_shear_area()
    item2 = structure_cls[1].panel.get_shear_area()
    item3 = structure_cls[2].panel.get_shear_area()
    assert item1 == 0.0036600000000000005
    assert item2 == 0.004776
    assert item3 == 0.006466600000000001


def test_plastic_sec_mod(structure_cls):
    item1 = structure_cls[0].panel.get_plasic_section_modulus()
    item2 = structure_cls[1].panel.get_plasic_section_modulus()
    item3 = structure_cls[2].panel.get_plasic_section_modulus()
    assert item1 == 0.01781929526454241
    assert item2 == 0.009138647999999996
    assert item3 == 0.012164186637142855


def test_moment_of_intertia(structure_cls):
    item1 = structure_cls[0].panel.stiffener.get_moment_of_intertia(plate_width=structure_cls[0].panel.plate.spacing, plate_thickness=structure_cls[0].panel.plate.thickness)
    item2 = structure_cls[1].panel.stiffener.get_moment_of_intertia(plate_width=structure_cls[1].panel.plate.spacing, plate_thickness=structure_cls[1].panel.plate.thickness)
    item3 = structure_cls[2].panel.stiffener.get_moment_of_intertia(plate_width=structure_cls[2].panel.plate.spacing, plate_thickness=structure_cls[2].panel.plate.thickness)
    assert item1 == 0.0001597323702732991
    assert item2 == 0.0004407634325301207
    assert item3 == 0.0006345175505307731


def test_weight(structure_cls):
    item1: float = structure_cls[0].panel.get_weight(panel_width=2*structure_cls[0].panel.plate.spacing)
    item2 = structure_cls[1].panel.get_weight(panel_width=2*structure_cls[1].panel.plate.spacing)
    item3 = structure_cls[2].panel.get_weight(panel_width=2*structure_cls[2].panel.plate.spacing)
    value1: float = item1 / 2 / structure_cls[0].panel.plate.span
    value2: float = item2 / 2 / structure_cls[1].panel.plate.span
    value3: float = item3 / 2 / structure_cls[2].panel.plate.span
    assert value1 == 558.2036776404001 
    assert value2 == 625.4879999999999
    assert value3 == 664.697808


def test_cross_section_area(structure_cls):
    item1 = structure_cls[0].panel.get_cross_section_area(efficient_se=structure_cls[0].panel.plate.spacing)
    item2 = structure_cls[1].panel.get_cross_section_area(efficient_se=structure_cls[1].panel.plate.spacing)
    item3 = structure_cls[2].panel.get_cross_section_area(efficient_se=structure_cls[2].panel.plate.spacing)
    assert item1 == 0.021548105680000002
    assert item2 == 0.01992
    assert item3 == 0.0235208












# from typing import Dict, Any
# import logging

# # this is not proper, but it allows to run this from the root of ANYSTRUCTURE
# import sys
# sys.path.append(".")

# from anystruct.calc_structure_classes.material import Material
# from anystruct.calc_structure_classes.plate import Plate
# from anystruct.calc_structure_classes.stiffener import Stiffener
# from anystruct.calc_structure_classes.stress import Stress
# from anystruct.calc_structure_classes.stiffened_panel import StiffenedPanel
# from anystruct.calc_structure_classes.buckling_input import BucklingInput
# from anystruct.calc_structure_classes.dnv_buckling import DNVBuckling


# # Create a custom logger
# logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
# logger = logging.getLogger("anystruct")
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# # so not to create another handler if it has already been defined in another module
# # doesn't seem to be working for file, but there the problem of multiple logs does not occur
# if not logger.hasHandlers():
#     ch = logging.StreamHandler()
#     ch.setFormatter(formatter)
#     logger.addHandler(ch)


# def main():
#     mat_steel_355: Material = Material(young=206800e6, poisson=0.3, strength=355e6)
#     plate: Plate = Plate(spacing=0.32, span=8.5, thickness=0.020, material=mat_steel_355)
#     stiffener: Stiffener = Stiffener(type="L", web_height=0.200, web_th=0.010, flange_width=0.100, flange_th=0.010, material=mat_steel_355, dist_between_lateral_supp=None)    
#     stiffened_panel: StiffenedPanel = StiffenedPanel(plate=plate, stiffener=stiffener, stiffener_end_support="continuous", girder_length=5)
#     stress: Stress = Stress(sigma_x1=130e6, sigma_x2=130e6, sigma_y1=0, sigma_y2=0, tauxy=10e6)

#     buckling_input: BucklingInput = BucklingInput(panel=stiffened_panel, pressure=0, pressure_side="both sides", stress=stress)

#     dNVBuckling: DNVBuckling = DNVBuckling(buckling_input=buckling_input, calculation_domain=None)

#     results: Dict[str, Any] = dNVBuckling.plated_structures_buckling()
#     for key, value in results.items():
#         print(key, value)


# if __name__ == '__main__':
#     logger.setLevel(logging.INFO)
#     main()