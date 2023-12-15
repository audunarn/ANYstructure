import pytest
from anystruct import make_grid_numpy as grid_np, grid_window as grid_operations


# Testing the Structure class

@pytest.fixture
def grid_oper():
    canvas_dim = [10, 10]
    canvas_origo = (10, 0)
    to_draw = {'line1': ((2, 2), (2, 7)), 'line2': ((2, 7), (7, 7)),
               'line3': ((7, 7), (7, 2)), 'line4': ((7, 2), (2, 2))}
    return grid_operations.CreateGridWindow(grid_np.Grid(10, 10), canvas_dim, to_draw, canvas_origo)

def test_bfs_search(grid_oper):
    result = grid_oper.search_bfs()
    assert 'compartments' in result
    assert 'grids' in result