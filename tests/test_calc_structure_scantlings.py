import calc_structure as calc
import pytest
import example_data as ex

# Testing the Structure class

@pytest.fixture
def scantling_cls():
    return calc.CalcScantlings(ex.obj_dict), calc.CalcScantlings(ex.obj_dict2), calc.CalcScantlings(ex.obj_dict_L)

def test_eff_moment_of_intertia(scantling_cls):
    pressure = 200

    item1 = scantling_cls[0].get_moment_of_intertia(efficent_se=scantling_cls[0].get_plate_efficent_b(
            design_lat_press=pressure))
    item2 = scantling_cls[1].get_moment_of_intertia(efficent_se=scantling_cls[1].get_plate_efficent_b(
            design_lat_press=pressure))
    item3 = scantling_cls[2].get_moment_of_intertia(efficent_se=scantling_cls[2].get_plate_efficent_b(
            design_lat_press=pressure))
    assert item1 == 0.0001954533465023375
    assert item2 == 0.0003855085228421317
    assert item3 == 2.475775492423021e-05

def test_buckling_stiffener_side(scantling_cls):
    pressure = 200
    item1 = scantling_cls[0].calculate_buckling_all(design_lat_press=pressure,checked_side='s')
    item2 = scantling_cls[1].calculate_buckling_all(design_lat_press=pressure,checked_side='s')
    item3 = scantling_cls[2].calculate_buckling_all(design_lat_press=pressure,checked_side='s')
    assert item1 == [0.9729020921645564, 0.40724966707091187, 0.8845350899810523, 0.8749607427920713, -0.11783163665252112, 0.009851334334728623]
    assert item2 == [0.8439747619895035, 0.6874422829139918, 0.6422370465897177, 0.6883978993466389, -0.018448105453830892, 0.018645053551144264]
    assert item3 == [0.31162369577319593, 0.41539277713882866, 0.26782980359706804, 0.41426194993038273, 0.08315101998685921, -0.0450507243894534]

def test_buckling_plate_side(scantling_cls):
    pressure = 200
    item1 = scantling_cls[0].calculate_buckling_all(design_lat_press=pressure,checked_side='p')
    item2 = scantling_cls[1].calculate_buckling_all(design_lat_press=pressure,checked_side='p')
    item3 = scantling_cls[2].calculate_buckling_all(design_lat_press=pressure,checked_side='p')
    assert item1 == [0.9729020921645564, 0.8068668020964379, -0.041396296961396524, 0.2971803834814199, 0.8073127040689398, 0.08785133433472869]
    assert item2 == [0.8439747619895035, 0.7855508533258388, 0.071678887601048, 0.49995924694298943, 0.5513230073138509, 0.12464505355114436]
    assert item3 == [0.31162369577319593, 0.528918649472309, 0.12937310434846616, 0.30073607759690246, 0.2090149796996547, 0.05694927561054669]

def test_minimum_plate_thickenss(scantling_cls):
    pressure = 200
    item1 = scantling_cls[0].get_dnv_min_thickness(pressure)
    item2 = scantling_cls[1].get_dnv_min_thickness(pressure)
    item3 = scantling_cls[2].get_dnv_min_thickness(pressure)
    assert item1 == 9.729196060772338
    assert item2 == 9.214115076089064
    assert item3 == 10.791282866994683

def test_minimum_section_module(scantling_cls):
    pressure = 200
    item1 = scantling_cls[0].get_dnv_min_section_modulus(pressure)
    item2 = scantling_cls[1].get_dnv_min_section_modulus(pressure)
    item3 = scantling_cls[2].get_dnv_min_section_modulus(pressure)
    assert item1 == 0.0008763156387732192
    assert item2 == 0.0008421261216230251
    assert item3 == 0.000147233164952631
