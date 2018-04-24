import ANYstructure.calc_structure as calc
import pytest
import ANYstructure.example_data as ex

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
    assert item1 == [0.9729020921645564, 0.2793839864786052, 0.5744791009123442, 0.6293847662965585,
                     0.17544156059960886]
    assert item2 == [0.8439747619895035, 0.43111173566762134, 0.47803269770485657, 0.4247719899317283,
                     0.13847708240330897]
    assert item3 == [0.31162369577319593, 0.37504146620034934, 0.250891737333123, 0.23936332420703765,
                     0.09992470990211093]

def test_buckling_plate_side(scantling_cls):
    pressure = 200
    item1 = scantling_cls[0].calculate_buckling_all(design_lat_press=pressure,checked_side='p')
    item2 = scantling_cls[1].calculate_buckling_all(design_lat_press=pressure,checked_side='p')
    item3 = scantling_cls[2].calculate_buckling_all(design_lat_press=pressure,checked_side='p')
    assert item1 == [0.9729020921645564, 0.9256653555796347, -0.1784387693645702, -0.1427637591511474,
                     0.9275723846555355, 0.14585133433472874]
    assert item2 == [0.8439747619895035, 0.8632286783087065, 0.0680393070871874, 0.02253718601860501,
                     0.5476834267999903, 0.12464505355114436]
    assert item3 == [0.31162369577319593, 0.5303793722473008, 0.1292909161741195, 0.132113583815756,
                     0.20893279152530803, 0.05694927561054669]

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
