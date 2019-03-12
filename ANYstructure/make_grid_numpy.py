"""
Grid class
"""

import numpy as np

class Grid:
    """
    Implementation of 2D grid of cells
    Includes boundary handling
    """

    def __init__(self, grid_height, grid_width):
        """
        Initializes grid to be empty, take height and width of grid as parameters
        Indexed by rows (left to right), then by columns (top to bottom)
        """

        self._grid_height = grid_height
        self._grid_width = grid_width
        self._cells = np.zeros((self._grid_height,self._grid_width))
        self.empty, self.full, self.barrier, self.corner = 0, 1, -1, -2
        self._geo_info = {'points': None, 'lines': None}
        self._compressed_grid = None
        self._bfs_search_data = None

    @property
    def cells(self):
        return self._cells

    @cells.setter
    def cells(self, val):
        self._cells = val

    @property
    def bfs_search_data(self):
        return self._bfs_search_data

    @bfs_search_data.setter
    def bfs_search_data(self, val):
        self._bfs_search_data = val

    def __str__(self):
        """
        Return multi-line string represenation for grid
        """
        ans = ""
        for row in range(self._grid_height):
            ans += str(self._cells[row])
            ans += "\n"
        return ans

    def make_empty_grid(self):
        '''
        Making a grid of all 0.
        :return:
        '''
        return np.zeros((self._grid_height,self._grid_width))

    def get_array(self):
        ''' Returning the numpy array '''
        return self._cells

    def provide_line_info(self, lines, points):
        ''' Line information to the grid.
            The geometric infomation is a dictionary
            {   line_dict: line_dict,
                point_dict: point_dict  }
        '''
        self._geo_info['lines'] = lines
        self._geo_info['points'] = points

    def get_grid_height(self):
        """
        Return the height of the grid for use in the GUI
        """
        return self._grid_height

    def get_grid_width(self):
        """
        Return the width of the grid for use in the GUI
        """
        return self._grid_width

    def get_matrix(self):
        """
        Return the complete matrix in numpy list form.
        """
        return self._cells

    def get_highest_number_in_grid(self):
        '''
        Retruns the highes number in the grid.
        :return:
        '''

        return np.amax(self._cells)

    def clear(self):
        """
        Clears grid to be empty
        """
        self._cells = np.zeros((self._grid_height,self._grid_width))

    def set_empty(self, row, col):
        """
        Set cell with index (row, col) to be empty
        """
        self._cells[row][col] = self.empty

    def set_full(self, row, col):
        """
        Set cell with index (row, col) to be full
        """
        self._cells[row][col] = self.full

    def set_value(self, row, col, value):
        """
        Set cell with index (row, col) to be a specified integer
        """
        self._cells[row][col] = value

    def set_barrier(self, row, col, line_number: int = None):
        """
        Set cell with index (row, col) to be full
        """

        if line_number is None:
            self._cells[row][col] = self.barrier
        else:
            self._cells[row][col] = line_number



    def set_number_to_cell(self, row, col, number):
        '''
        Setting an arbritary number to a cell.
        '''
        self._cells[row][col] = number

    def is_empty(self, row, col):
        """
        Checks whether cell with index (row, col) is empty
        """
        return self._cells[row][col] == self.empty

    def is_full(self, row, col):
        """
        Checks whether cell with index (row, col) is empty
        """
        return self._cells[row][col] == self.full

    def is_barrier(self, row, col):
        """
        Checks whether cell with index (row, col) is empty
        """
        return self._cells[row][col] == self.barrier

    def is_corner(self,point):
        '''
        Identifying corners.
        :param point:
        :return:
        '''
        return [self.get_value(item[0],item[1]) for item in
                self.eight_neighbors(point[0],point[1])].count(self.barrier) > 4

    def four_neighbors(self, row, col):
        """
        Returns horiz/vert neighbors of cell (row, col)
        """
        ans = []
        if row > 0:
            ans.append((row - 1, col))
        if row < self._grid_height - 1:
            ans.append((row + 1, col))
        if col > 0:
            ans.append((row, col - 1))
        if col < self._grid_width - 1:
            ans.append((row, col + 1))
        return ans

    def eight_neighbors(self, row, col):
        """
        Returns horiz/vert neighbors of cell (row, col) as well as
        diagonal neighbors
        """
        ans = []
        if row > 0:
            ans.append((row - 1, col))
        if row < self._grid_height - 1:
            ans.append((row + 1, col))
        if col > 0:
            ans.append((row, col - 1))
        if col < self._grid_width - 1:
            ans.append((row, col + 1))
        if (row > 0) and (col > 0):
            ans.append((row - 1, col - 1))
        if (row > 0) and (col < self._grid_width - 1):
            ans.append((row - 1, col + 1))
        if (row < self._grid_height - 1) and (col > 0):
            ans.append((row + 1, col - 1))
        if (row < self._grid_height - 1) and (col < self._grid_width - 1):
            ans.append((row + 1, col + 1))
        return ans

    def get_index(self, point, cell_size):
        """
        Takes point in screen coordinates and returns index of
        containing cell
        """
        return (point[1] / cell_size, point[0] / cell_size)

    def get_value(self, row, col):
        #print('ROW COL: ', row, col)
        #print('CURRENT CELL LEN: ',len(self._cells))
        #print(self._cells[row])
        return self._cells[row][col]

    def get_points_along_line(self,start, end):
        """Bresenham's Line Algorithm
        Produces a list of tuples from start and end
            points1 = get_line((0, 0), (3, 4))
            points2 = get_line((3, 4), (0, 0))
            assert(set(points1) == set(points2))
            print points1
            [(0, 0), (1, 1), (1, 2), (2, 3), (3, 4)]
            [(3, 4), (2, 3), (1, 2), (1, 1), (0, 0)]
        """
        # Setup initial conditions
        x1 = int(start[0])
        y1 = int(start[1])
        x2 = int(end[0])
        y2 = int(end[1])

        dx = x2 - x1
        dy = y2 - y1

        # Determine how steep the line is
        is_steep = abs(dy) > abs(dx)

        # Rotate line
        if is_steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2

        # Swap start and end points if necessary and store swap state
        swapped = False
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            swapped = True

        # Recalculate differentials
        dx = x2 - x1
        dy = y2 - y1

        # Calculate error
        error = int(dx / 2.0)
        ystep = 1 if y1 < y2 else -1

        # Iterate over bounding box generating points between start and end
        y = y1
        points = []
        for x in range(x1, x2 + 1):
            coord = (y, x) if is_steep else (x, y)
            points.append(coord)
            error -= abs(dy)
            if error < 0:
                y += ystep
                error += dx

        # Reverse the list if the coordinates were swapped
        if swapped:
            points.reverse()
        return points

    def get_mid_point(self, cell1, cell2):
        '''
        Get the point that is in the middle between two points.
        :param point1:
        :param point2:
        :return:
        '''
        idx = int(round(len(self.get_points_along_line(cell1,cell2))/2,0))
        return self.get_points_along_line(cell1,cell2)[idx]

    def get_adjacent_values(self,cell):
        '''
        Find the labels in the grid adjacent to the specified point.
        :param point:
        :return:
        '''

        return tuple(set([int(self.get_value(neighbor[0], neighbor[1]))
                          for neighbor in self.four_neighbors(cell[0], cell[1])]))

    def get_adjacent_values_duplicates(self,cell):
        '''
        Find the labels in the grid adjacent to the specified point.
        :param point:
        :return:
        '''

        return_tuple = tuple(list([int(self.get_value(neighbor[0], neighbor[1]))
                                   for neighbor in self.four_neighbors(cell[0], cell[1])]))

        len(tuple(set(return_tuple)))

        if len(tuple(set(return_tuple))) > 1:
            return set(return_tuple)
        else:
            return (tuple(set(return_tuple))[0],tuple(set(return_tuple))[0])

    def get_highest_cell(self, value):
        '''
        Get the cell closes to (0,0) with a given value.
        :param value:
        :return:
        '''
        # TODO this is not very numpy-like
        highest = (self.get_grid_height(),0)
        for row in range(self.get_grid_height()):
            for col in range(self.get_grid_width()):
                if self.get_value(row,col) == value and row < highest[0]:
                    highest = (row,col)
        return highest

    def get_lowest_cell(self,value):
        '''
        Get the cell closest to (height,0) with a given value.
        :param value:
        :return:
        '''
        # TODO this is not very numpy-like
        lowest = (0,0)

        for row in range(self.get_grid_height()):
            for col in range(self.get_grid_width()):
                if self.get_value(row,col) == value and row > lowest[0]:
                    lowest = (row,col)
        return lowest

    def get_number_of_cells_with_value(self,value):
        '''
        Get the number of cells with a certain value.
        :param value:
        :return:
        '''
        # TODO this is not very numpy-like
        counter = 0
        for row in range(self.get_grid_height()):
            for col in range(self.get_grid_width()):
                if self.get_value(row,col) == value:
                    counter += 1
        return counter

    def import_grid(self,grid):
        '''
        Import a grid to replace created grid. Converting to numpy array.
        :param grid:
        :return:
        '''
        if np.array(grid).shape[1] == 2:
            self._cells = self.rebuild_compressed(grid)
        else:
            self.cells = np.array(grid) # old large save files

    def export_grid(self):
        '''
        Converting from array to list of list. Exporting the grid.
        :return:
        '''
        return self.export_compressed_grid()

    def export_compressed_grid(self):
        '''
        Converting from array to list of list. Exporting the grid for saving.
        :return:
        '''
        save_list = list()

        # Compressing horizontally
        for row in self._cells:
            this_counter, this_number, save_row = 1, row[0], list()
            for col_idx in range(len(row)-1):
                last = col_idx == len(row)-2
                if row[col_idx] == row[col_idx+1] and not last:
                    this_counter += 1
                elif row[col_idx] != row[col_idx+1] and not last:
                    save_row.append([this_number, this_counter])
                    this_number = row[col_idx+1]
                    this_counter = 1
                elif last:
                    save_row.append([this_number, this_counter+1])

            save_list.append(save_row)

        # Compressing vertically
        this_counter, this_number, save_vertical = 1, save_list[0], list()
        for row_idx in range(len(save_list) - 1):
            last = row_idx == len(save_list) - 2
            if save_list[row_idx] == save_list[row_idx +1] and not last:
                this_counter += 1
            elif save_list[row_idx] != save_list[row_idx +1] and not last:
                save_vertical.append([this_number, this_counter])
                this_number = save_list[row_idx +1]
                this_counter = 1
            elif last:
                save_vertical.append([this_number, this_counter])
                if save_list[row_idx+1] != save_list[row_idx]:
                    save_vertical.append([save_list[row_idx+1], 1])

        return save_vertical

    def rebuild_compressed(self, compressed_grid = None):
        '''
        Rebuilding a compressed grid made by 'export_compressed_grid(self)'
        :return:
        '''
        compressed_grid = compressed_grid if compressed_grid is not None else self._compressed_grid
        vertical_expansion_list = []

        # Expand vertically
        for row_count, row in enumerate(compressed_grid):
            values = row[0]
            value_count = row[1]
            for dummy_i in range(value_count):
                vertical_expansion_list.append(values)

        # Expand horisontally
        expanded_list = [list() for dummy_i in range(len(vertical_expansion_list))]

        for row_count, row in enumerate(vertical_expansion_list):
            for values in row:
                value = values[0]
                value_count = values[1]
                for dummy_i in range(value_count):
                    expanded_list[row_count].append(value)

        return np.array(expanded_list)

if __name__ ==  '__main__':
    import ANYstructure.example_data as ex
    import ANYstructure.grid_window as grd

    lines = ex.line_dict
    points = ex.point_dict

    canvas_dim = [1000,720]
    canvas_origo = (50,670)
    my_grid = grd.CreateGridWindow(ex.get_grid_no_inp(), canvas_dim, ex.get_to_draw(), canvas_origo)
    search_return = my_grid.search_bfs(animate = True)
    grid_only = my_grid.grid
    grid_only.export_compressed_grid()
    grid_only.rebuild_compressed(grid_only._compressed_grid)