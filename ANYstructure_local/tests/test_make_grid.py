import ANYstructure_local.make_grid_numpy as grid
import pytest
import numpy as np


@pytest.fixture
def grid_cls():
    return grid.Grid(10, 11)

def test_grid_height(grid_cls):
    assert grid_cls.get_grid_height() == 10

def test_grid_height(grid_cls):
    assert grid_cls.get_grid_width() == 11

def test_set_barrier(grid_cls):
    for i in range(2,7,1):
        grid_cls.set_barrier(2, i)
        grid_cls.set_barrier(6, i)
    assert np.count_nonzero(grid_cls.get_matrix()) == 10

def test_set_full(grid_cls):
    grid_cls.set_full(4,4)
    assert np.count_nonzero(grid_cls.get_matrix()) == 1
    assert grid_cls.get_highest_number_in_grid() == 1

def test_eight_nighbors(grid_cls):
    assert len(grid_cls.eight_neighbors(4,4)) == 8




