import math
import ANYstructure.make_queue as queue
import ANYstructure.make_stack as make_stack
#from matplotlib.backends import backend_qt5agg
from matplotlib import pyplot as plt
import numpy as np
from collections import deque
import copy
import matplotlib.animation as animation
import ANYstructure.example_data as test

def dist(p, q):
    return math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)

class CreateGridWindow():

    def __init__(self, grid, canvas_dim, to_draw, canvas_origo, find_lines: bool = False):
        self._grid = grid
        self._parent_dimensions = canvas_dim
        self._to_draw = to_draw
        self._parent_origo = canvas_origo
        self._points_child = {}
        self._child_dimensions = (canvas_dim[0]-canvas_origo[0]+1, canvas_origo[1]+1)
        self._bfs_search_data = None

        for line,point in to_draw.items():
            point1 = (int(point[0][0]),int(point[0][1]))
            point2 = (int(point[1][0]),int(point[1][1]))
            self._points_child[line] = [point1,point2]

        for line, points in self._points_child.items():
            for point in self._grid.get_points_along_line(points[0],points[1]):
                if not find_lines:
                    self._grid.set_barrier(point[0],point[1])
                else:
                    self._grid.set_barrier(point[0], point[1], line_number = hlp.get_num(line))


    def __str__(self):
        return 'Not implemented'

    @property
    def grid(self):
        return self._grid

    @grid.setter
    def grid(self, val):
        self._grid = val

    @property
    def bfs_search_data(self):
        return self._bfs_search_data

    @bfs_search_data.setter
    def bfs_search_data(self, val):
        self._bfs_search_data = val

    def draw_grid(self, save = False, tank_count = None):
        '''
        Drawing grid
        EMPTY = yellow
        FULL = red
        :return:
        '''
        # TODO make a better plot of the tanks

        def discrete_matshow(data):
            if self._bfs_search_data is not None:
                comp_cell_count = self._bfs_search_data
            area_mult = self._parent_dimensions[0]/(10*self._parent_dimensions[0]) * \
                        self._parent_dimensions[1]/(10*self._parent_dimensions[1])
            plt_txt = list()
            for num in range(tank_count):
                if self._bfs_search_data is not None:
                    tank_area = comp_cell_count[num + 2] * area_mult
                    plt_txt.append('Comp' + str(num + 2) + ' Approx. area: ' + str(round(tank_area,1)))
                else:
                    plt_txt.append('Comp' + str(num + 2))

            fig = plt.figure(figsize=[12, 8])
            ax = fig.add_subplot(111)
            ax.tick_params(labelsize=8)
            fig.subplots_adjust(left=0.05, right=0.90, top=0.95, bottom=0.05)
            # get discrete colormap
            cmap = plt.get_cmap('Accent_r', np.int(np.max(data)) - np.int(np.min(data)) + 1)
            # set limits .5 outside true range
            cax = ax.matshow(data, cmap=cmap, vmin=np.min(data) - .5, vmax=np.max(data) + .5)
            # tell the colorbar to tick at integers
            colb = fig.colorbar(cax, ticks=np.arange(np.min(data), np.max(data) + 1), shrink=0.8)
            if tank_count is not None:
                colb.set_ticks([-1, 0, 1] + [num + 2 for num in range(tank_count)])
                colb.set_ticklabels(['BHD/Deck', 'Not searched', 'External'] + plt_txt)

        # generate data
        discrete_matshow(self._grid.get_matrix())
        plt.suptitle('Compartments returned from search operation displayed below', fontsize=20, color='red')
        plt.xscale('linear')
        plt.axis('off')
        plt.annotate('*area calculation inaccuracies due to thickness of barriers (BHD/Deck)', (0, 0), (0, -20),
                     xycoords='axes fraction', textcoords='offset points', va='top', fontsize = 10)
        if save:
            plt.savefig('current_comps.png')
        else:
            plt.show()

    def animate_grid(self, grids_to_animate: list = None, tank_count = None):
        ''' If animation is selected, the grid is shown here. '''

        all_grids = grids_to_animate

        def generate_data():
            if len(all_grids) == 0:
                ani.event_source.stop()
            current_grid = all_grids.pop(0)
            return current_grid

        def update(data):
            if len(all_grids) == 0:
                ani.event_source.stop()
            cax.set_data(data)
            return cax

        def data_gen():
            if len(all_grids) == 0:
                ani.event_source.stop()
            while True:
                yield generate_data()
        plt.ion()
        #tank_count = np.max(all_grids[-1])
        fig = plt.figure(figsize=[12, 8])
        ax = fig.add_subplot(111)
        ax.tick_params(labelsize=8)
        fig.subplots_adjust(left=0.05, right=0.90, top=0.95, bottom=0.05)
        # get discrete colormap
        cmap = plt.get_cmap('Accent_r', np.int(np.max(all_grids[-1])) - np.int(np.min(all_grids[-1])) + 1)
        # set limits .5 outside true range
        cax = ax.matshow(all_grids[-1], cmap=cmap, vmin=np.min(all_grids[-1]) - .5, vmax=np.max(all_grids[-1]) + .5)
        # tell the colorbar to tick at integers
        colb = fig.colorbar(cax, ticks=np.arange(np.min(all_grids[-1]), np.max(all_grids[-1]) + 1), shrink=0.8)

        if self._bfs_search_data is not None:
            comp_cell_count = self._bfs_search_data
        area_mult = self._parent_dimensions[0] / (10 * self._parent_dimensions[0]) * \
                    self._parent_dimensions[1] / (10 * self._parent_dimensions[1])
        plt_txt = list()
        for num in range(tank_count):
            if self._bfs_search_data is not None:
                tank_area = comp_cell_count[num + 2] * area_mult
                plt_txt.append('Comp' + str(num + 2) + ' Approx. area: ' + str(round(tank_area, 1)))
            else:
                plt_txt.append('Comp' + str(num + 2))

        if tank_count is not None:
            colb.set_ticks([-1, 0, 1] + [num + 2 for num in range(int(tank_count))])
            colb.set_ticklabels(['BHD/Deck', 'Not searched', 'External'] + plt_txt)
        ani = animation.FuncAnimation(fig, update, data_gen, interval=50)
        fm = plt.get_current_fig_manager()
        fm.window.activateWindow()
        fm.window.raise_()
        plt.suptitle('Compartments returned from search operation displayed below', fontsize=20, color='red')
        plt.xscale('linear')
        plt.axis('off')
        plt.annotate('*area calculation inaccuracies due to thickness of barriers (BHD/Deck)', (0, 0), (0, -20),
                     xycoords='axes fraction', textcoords='offset points', va='top', fontsize = 10)
        plt.show()

    def search_bfs(self, animate = False):
        '''
        Bredth first search method.

        Searcing every 20th pixel for empty places in the grid. When a empty cell is found, the search starts.
        The search ends when no more empty cells are found in the boudnary regions (circular expansion of search).

        USE GRID CONVENSION HERE. NOT POINTS.

        grid(row,col) is same as grid(y,x)

        points uses

        point(x , y) is same as grid(col,row)
        :return:
        '''
        compartment_count = 1
        compartments = {}
        all_grids = []
        anim_count = 0

        if animate:
            all_grids.append(self._grid.get_matrix())

        barriers_where = np.where(self._grid.cells.reshape((1,np.product(self._grid.cells.shape))) == -1)
        barrier_comp_count = dict()

        for startrow in range(0, self._child_dimensions[1], 20):
            for startcol in range(0, self._child_dimensions[0], 20):
                if self._grid.is_empty(startrow,startcol):
                    el_max = ''
                    el_min = ''
                    cells = 0
                    boundary = deque()
                    boundary.append((startrow,startcol))
                    corners = []
                    barrier_comp_count[compartment_count] = 0

                    while len(boundary) != 0:
                        current_cell = boundary.pop()
                        #find the min/max elevation, counting cells in tank
                        if el_max == '':
                            el_max = current_cell[0]
                            el_min = current_cell[0]
                        else:
                            if current_cell[0] < el_max:
                                el_max = current_cell[0]
                            if current_cell[0] > el_min:
                                el_min = current_cell[0]
                        cells += 1
                        anim_count += 1

                        four_neighbors = self._grid.four_neighbors(current_cell[0], current_cell[1])
                        neighbors = self._grid.eight_neighbors(current_cell[0], current_cell[1])

                        #doing serach operations and looking for corners
                        no_of_barriers = 0
                        for neighbor in four_neighbors:
                            if self._grid.get_value(neighbor[0], neighbor[1]) == -1:
                                no_of_barriers += 1
                                barrier_comp_count[compartment_count] += 1
                            else:
                                pass

                            if self._grid.is_empty(neighbor[0], neighbor[1]):
                                self._grid.set_value(neighbor[0], neighbor[1],compartment_count)
                                boundary.append(neighbor)
                                if animate:
                                    if compartment_count > 1:
                                        anim_interval = 2000
                                    else:
                                        anim_interval = 20000

                                    if anim_count/anim_interval - anim_count//anim_interval == 0.0:
                                        all_grids.append(copy.deepcopy(self._grid.get_matrix()))
                        #finding corners on diagonal cells
                        for neighbor in [item for item in neighbors if item not in four_neighbors]:
                            if self._grid.get_value(neighbor[0], neighbor[1]) == -1:
                                no_of_barriers += 1
                            else:
                                pass

                        if no_of_barriers > 4:
                            corners.append((neighbor[0], neighbor[1]))

                    # returning values to the program
                    compartments[compartment_count] = cells, corners
                    compartment_count += 1
        if animate:
            all_grids.append(self._grid.get_matrix())

        cells_modified, area_modified = dict(), dict()
        comp_sum = np.sum([data for data in barrier_comp_count.values()])
        for comp_no, data in compartments.items():
            barrier_ratio_of_total = barrier_comp_count[comp_no] / comp_sum
            cells_modified[comp_no] = data[0] + int(barriers_where[0].shape[0] * barrier_ratio_of_total)

        to_return = {'compartments': compartments, 'grids':all_grids, 'modified_cell_count': cells_modified}
        self.bfs_search_data = to_return['modified_cell_count']
        self._grid.bfs_search_data = to_return['modified_cell_count']
        return to_return

    def find_lines_inside_area(self, row1, col1, row2, col2):
        '''
        Define a search area.
        Return the lines in this area.
        This method makes sense if "find_lines" is set to True.
        '''
        return np.unique(self._grid.get_array()[row1:row2, col1:col2])

if __name__ == '__main__':
    import time
    t1 = time.time()
    canvas_dim = [1000,720]
    canvas_origo = (50,670)
    my_grid = CreateGridWindow(test.get_grid_no_inp(), canvas_dim, test.get_to_draw(), canvas_origo)
    search_return = my_grid.search_bfs(animate = True)
    my_grid.draw_grid(tank_count=4)












