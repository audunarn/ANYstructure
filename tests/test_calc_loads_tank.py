from any_files import calc_loads as calcl, example_data as ex
import pytest


# Testing the Structure class

@pytest.fixture
def tank_cls():
    return calcl.Tanks(ex.comp2), calcl.Tanks(ex.comp3), calcl.Tanks(ex.comp4)

def test_get_bottom_pressure(tank_cls):
    for load, result1, result2, result3 in zip(tank_cls, [90712.5, 90712.5, 90712.5], [87637.5, 87637.5, 87637.5],
                                               [296629.875, 296629.875, 296629.875]):
        assert load.get_calculated_pressure((0, 0), 3) == result1
        assert load.get_calculated_pressure((1, 1), 3) == result2
        assert load.get_calculated_pressure((10, 0), 9.81) == result3

def test_dnv_min_pressure(tank_cls):
    for load, result1, result2 in zip(tank_cls, [411056.775, 411056.775, 449117.5875],
                                      [379424.25, 379424.25, 414556.125]):
        assert load.get_tank_dnv_minimum_pressure(1.3, 0.7) == result1
        assert load.get_tank_dnv_minimum_pressure(1, 1.3) == result2
