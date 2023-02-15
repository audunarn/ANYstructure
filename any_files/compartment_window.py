# Compartments are created here.
# NOT USED YET

import tkinter as tk
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
try:
    import any_files.test
except ModuleNotFoundError:
    import ANYstructure.any_files.test
import numpy as np

class CreateCompartmentWindow():

    def __init__(self, master,app=None):
        super(CreateCompartmentWindow, self).__init__()

        if __name__ == '__main__':
            base_canvas_dim = [1000, 720]
            self.canvas_origo = [50, base_canvas_dim[1] - 50]
            self.grid = test.get_grid(origo=self.canvas_origo,base_canvas_dim=base_canvas_dim)
            self.parent_dimensions = base_canvas_dim
            self.to_draw = test.get_to_draw()
        else:
            self.app = app
            self.grid = app._main_grid
            self.parent_dimensions = app._canvas_dim
            self.to_draw = app._pending_grid_draw
            self.parent_origo = app._canvas_origo

        frame_dim = (1500,980)
        self.canvas_origo = (50,720-50)
        self.canvas_dim = (1000,720)

        self.frame = master
        self.frame.wm_title("Load properties")
        self.frame.geometry(str(frame_dim[0])+'x'+str(frame_dim[1]))
        self.frame.grab_set()

        self.points_child = {}
        self.child_dimensions = (self.parent_dimensions[0]-self.parent_dimensions[0]+1, self.parent_dimensions[1]+1)

        for line,point in self.to_draw.items():
            point1 = (int(point[0][0]),int(point[0][1]))
            point2 = (int(point[1][0]),int(point[1][1]))
            self.points_child[line] = [point1,point2]

        for line, points in self.points_child.items():
            for point in self.grid.get_points_along_line(points[0],points[1]):
                self.grid.set_barrier(point[0],point[1])

        fig = plt.figure()
        self.draw_grid()
        self.canvas_plt = FigureCanvasTkAgg(fig,self.frame)
        self.canvas_plt.show()
        self.canvas_plt.get_tk_widget().place(relx=0.5,rely=0.5)


        #self.draw_grid()
        tk.Button(self.frame,text='DRAW',command=self.draw_grid).place(relx=0.1,rely=0.1)

    def __str__(self):
        return 'class CreateCompartmentWindow(): Compartment string not implemented'

    def draw_grid(self):
        '''
        Drawing grid
        EMPTY = yellow
        FULL = red
        :return:
        '''

        def discrete_matshow(data):
            # get discrete colormap
            cmap = plt.get_cmap('RdBu', np.max(data) - np.min(data) + 1)
            # set limits .5 outside true range
            mat = plt.matshow(data, cmap=cmap, vmin=np.min(data) - .5, vmax=np.max(data) + .5)
            # tell the colorbar to tick at integers
            cax = plt.colorbar(mat, ticks=np.arange(np.min(data), np.max(data) + 1))
        # # generate data
        # a = np.random.randint(1, 20, size=(10, 10))
        discrete_matshow(self.grid.get_matrix())
        plt.suptitle('Tanks defined by numbers from 2 and up.')
        return plt
        #plt.show()

    def search_dfs(self):
        '''
        Depth first search method.
        :return:
        '''
        start = (0,0)
        stack = make_stack.Stack()
        stack.push_item(start)

        while len(stack) != 0:
            cell = stack.pop_item()
            if self.grid.is_empty(cell[0], cell[1]):
                self.grid.set_full(cell[0], cell[1])
                for item in self.grid.four_neighbors(cell[0], cell[1]):
                    stack.push_item(item)

    def search_bfs(self):
        '''
        Bredth first search method.

        Searcing evry 20th pixel for empty places in the grid. When a empty cell is found, the search starts.
        The search ends when no more empty cells are found in the boudnary regions (circular expansion of search).

        USE GRID CONVENSION HERE. NOT POINTS.

        grid(row,col) is same as grid(y,x)

        points uses

        point(x , y) is same as grid(col,row)
        :return:
        '''
        compartment_count = 1
        cells = 0
        el_max = ''
        el_min = ''
        compartments = {}

        for startrow in range(0, self.child_dimensions[1], 20):
            for startcol in range(0, self.child_dimensions[0], 20):
                if self.grid.is_empty(startrow,startcol):
                    el_max = ''
                    el_min = ''
                    cells = 0
                    boundary = deque()
                    boundary.append((startrow,startcol))
                    corners = []

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
                        neighbors = self.grid.eight_neighbors(current_cell[0], current_cell[1])

                        #doing serach operations and looking for corners
                        no_of_barriers = 0
                        for neighbor in neighbors[0:4]:
                            if self.grid.get_value(neighbor[0], neighbor[1]) == -1: no_of_barriers += 1
                            else: pass

                            if self.grid.is_empty(neighbor[0], neighbor[1]):
                                self.grid.set_value(neighbor[0], neighbor[1],compartment_count)
                                boundary.append(neighbor)

                        #finding corners on diagonal cells
                        for neighbor in neighbors[4:]:
                            if self.grid.get_value(neighbor[0], neighbor[1]) == -1: no_of_barriers += 1
                            else: pass

                        if no_of_barriers > 4:
                            corners.append((neighbor[0], neighbor[1]))

                    # returning values to the program
                    compartments[compartment_count] = cells, corners
                    compartment_count += 1

        return compartments

if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateCompartmentWindow(master=root)
    root.mainloop()