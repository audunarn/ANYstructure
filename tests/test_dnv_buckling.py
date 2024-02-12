import pytest

# this is not proper, but it allows to run this from the root of ANYSTRUCTURE
import sys
sys.path.append(".")
from anystruct.calc_structure_classes.example_data import buckling_input1, buckling_input2, buckling_input3


@pytest.fixture
def structure_cls():
    return buckling_input1, buckling_input2, buckling_input3


def test_section_modulus(structure_cls):
    sec_mod1 = structure_cls[0].panel.stiffener.get_section_modulus()
    sec_mod2 = structure_cls[1].panel.stiffener.get_section_modulus()
    sec_mod3 = structure_cls[2].panel.stiffener.get_section_modulus()
    print(sec_mod1, sec_mod2, sec_mod3)
    assert sec_mod1 == (0.0019287090971451923, 0.004261170917709274)
    assert sec_mod2 == (0.001514995958173724, 0.004116734923760761)
    assert sec_mod3 == (0.0002956956857932298, 0.0009820952365724583)


def test_shear_center(structure_cls):
    item1 = structure_cls[0].panel.get_shear_center()
    item2 = structure_cls[1].panel.get_shear_center()
    item3 = structure_cls[2].panel.get_shear_center()
    assert item1 == 0.12363562558813218
    assert item2 == 0.09396749072714805
    assert item3 == 0.042793744159682734


def test_shear_area(structure_cls):
    item1 = structure_cls[0].panel.get_shear_area()
    item2 = structure_cls[1].panel.get_shear_area()
    item3 = structure_cls[2].panel.get_shear_area()
    assert item1 == 0.00783
    assert item2 == 0.004776
    assert item3 == 0.00189


def test_plastic_sec_mod(structure_cls):
    item1 = structure_cls[0].panel.get_plasic_section_modulus()
    item2 = structure_cls[1].panel.get_plasic_section_modulus()
    item3 = structure_cls[2].panel.get_plasic_section_modulus()
    assert item1 == 0.006603262500000001
    assert item2 == 0.009138647999999996
    assert item3 == 0.00281844


def test_moment_of_intertia(structure_cls):
    item1 = structure_cls[0].panel.stiffener.get_moment_of_intertia()
    item2 = structure_cls[1].panel.stiffener.get_moment_of_intertia()
    item3 = structure_cls[2].panel.stiffener.get_moment_of_intertia()
    assert item1 == 0.0005775674497377624
    assert item2 == 0.0004407634325301207
    assert item3 == 4.772633540902878e-05


def test_weight(structure_cls):
    item1 = structure_cls[0].panel.get_weight()
    item2 = structure_cls[1].panel.get_weight()
    item3 = structure_cls[2].panel.get_weight()
    assert item1 == 673.53
    assert item2 == 625.4879999999999
    assert item3 == 137.7204


def test_cross_section_area(structure_cls):
    item1 = structure_cls[0].panel.get_cross_section_area()
    item2 = structure_cls[1].panel.get_cross_section_area()
    item3 = structure_cls[2].panel.get_cross_section_area()
    assert item1 == 0.021449999999999997
    assert item2 == 0.01992
    assert item3 == 0.008772












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