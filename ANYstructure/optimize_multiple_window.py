# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError
from tkinter.ttk import Progressbar
import ANYstructure.optimize as op
import numpy as np
import time, os
from tkinter import messagebox
import ANYstructure.example_data as test
from ANYstructure.helper import *
import ANYstructure.helper as hlp
from tkinter.filedialog import askopenfilenames
from multiprocessing import cpu_count
import ANYstructure.optimize as opt

class CreateOptimizeMultipleWindow():
    '''
    This class initiates the MultiOpt window.
    '''
    def __init__(self, master, app=None):
        super(CreateOptimizeMultipleWindow, self).__init__()
        if __name__ == '__main__':
            self._load_objects = {}
            self._load_comb_dict = {}
            self._line_dict = test.get_line_dict()
            self._load_count = 0
            self._point_dict = test.get_point_dict()
            self._canvas_scale = 25
            self._line_to_struc = test.get_line_to_struc()
            self._slamming_pressure = test.get_slamming_pressure()
            self._fatigue_pressure = test.get_fatigue_pressures()
            self._fatigue_object = test.get_fatigue_object()
            image_dir = os.path.dirname(__file__)+'\\images\\'
        else:
            self.app = app
            self._load_objects = app._load_dict
            self._load_comb_dict = app._new_load_comb_dict
            self._line_dict = app._line_dict
            self._load_count = 0
            self._point_dict = app._point_dict
            self._canvas_scale = app._canvas_scale
            self._line_to_struc = app._line_to_struc
            image_dir = app._root_dir + '\\images\\'
            self._root_dir = app._root_dir

        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1800x950')
        self._frame.grab_set()
        self._canvas_origo = (50, 720 - 50)

        self._canvas_base_origo = self._canvas_origo
        self._canvas_draw_origo = list(self._canvas_base_origo)
        self._previous_drag_mouse = list(self._canvas_draw_origo)

        self._active_lines = []
        self._add_to_lines = True
        self._lines_add_to_load = []
        self._mid_click_line = None

        self._predefined_structure = None

        # ----------------------------------COPIED FROM OPTIMIZE_WINDOW-----------------------------------------------

        self._opt_results = {}
        self._opt_actual_running_time = tk.Label(self._frame, text='')

        tk.Frame(self._frame, width=770, height=5, bg="grey", colormap="new").place(x=20, y=95)
        tk.Frame(self._frame, width=770, height=5, bg="grey", colormap="new").place(x=20, y=135)


        algorithms = ('anysmart', 'random', 'random_no_delta')

        tk.Label(self._frame, text='-- Structural optimizer for multiple selections --',
                 font='Verdana 15 bold').place(x=10, y=10)


        # upper and lower bounds for optimization
        # [0.6, 0.012, 0.3, 0.01, 0.1, 0.01]
        self._new_spacing_upper = tk.DoubleVar()
        self._new_spacing_lower = tk.DoubleVar()
        self._new_pl_thk_upper = tk.DoubleVar()
        self._new_pl_thk_lower = tk.DoubleVar()
        self._new_web_h_upper = tk.DoubleVar()
        self._new_web_h_lower = tk.DoubleVar()
        self._new_web_thk_upper = tk.DoubleVar()
        self._new_web_thk_lower = tk.DoubleVar()
        self._new_fl_w_upper = tk.DoubleVar()
        self._new_fl_w_lower = tk.DoubleVar()
        self._new_fl_thk_upper = tk.DoubleVar()
        self._new_fl_thk_lower = tk.DoubleVar()
        self._new_span = tk.DoubleVar()
        self._new_width_lg = tk.DoubleVar()
        self._new_algorithm = tk.StringVar()
        self._new_algorithm_random_trials = tk.IntVar()
        self._new_delta_spacing = tk.DoubleVar()
        self._new_delta_pl_thk = tk.DoubleVar()
        self._new_delta_web_h = tk.DoubleVar()
        self._new_delta_web_thk = tk.DoubleVar()
        self._new_delta_fl_w = tk.DoubleVar()
        self._new_delta_fl_thk = tk.DoubleVar()
        self._new_swarm_size = tk.IntVar()
        self._new_omega  = tk.DoubleVar()
        self._new_phip  = tk.DoubleVar()
        self._new_phig  = tk.DoubleVar()
        self._new_maxiter = tk.IntVar()
        self._new_minstep  = tk.DoubleVar()
        self._new_minfunc  = tk.DoubleVar()

        ent_w = 10
        self._ent_spacing_upper = tk.Entry(self._frame, textvariable=self._new_spacing_upper, width=ent_w)
        self._ent_spacing_lower = tk.Entry(self._frame, textvariable=self._new_spacing_lower, width=ent_w)
        self._ent_pl_thk_upper = tk.Entry(self._frame, textvariable=self._new_pl_thk_upper, width=ent_w)
        self._ent_pl_thk_lower = tk.Entry(self._frame, textvariable=self._new_pl_thk_lower, width=ent_w)
        self._ent_web_h_upper = tk.Entry(self._frame, textvariable=self._new_web_h_upper, width=ent_w)
        self._ent_web_h_lower = tk.Entry(self._frame, textvariable=self._new_web_h_lower, width=ent_w)
        self._ent_web_thk_upper = tk.Entry(self._frame, textvariable=self._new_web_thk_upper, width=ent_w)
        self._ent_web_thk_lower = tk.Entry(self._frame, textvariable=self._new_web_thk_lower, width=ent_w)
        self._ent_fl_w_upper = tk.Entry(self._frame, textvariable=self._new_fl_w_upper, width=ent_w)
        self._ent_fl_w_lower = tk.Entry(self._frame, textvariable=self._new_fl_w_lower, width=ent_w)
        self._ent_fl_thk_upper = tk.Entry(self._frame, textvariable=self._new_fl_thk_upper, width=ent_w)
        self._ent_fl_thk_lower = tk.Entry(self._frame, textvariable=self._new_fl_thk_lower, width=ent_w)
        self._ent_span = tk.Entry(self._frame, textvariable=self._new_span, width=ent_w)
        self._ent_width_lg = tk.Entry(self._frame, textvariable=self._new_width_lg, width=ent_w)
        self._ent_algorithm = tk.OptionMenu(self._frame, self._new_algorithm, command=self.selected_algorithm, *algorithms)
        self._ent_random_trials = tk.Entry(self._frame, textvariable=self._new_algorithm_random_trials)
        self._ent_delta_spacing = tk.Entry(self._frame, textvariable=self._new_delta_spacing, width=ent_w)
        self._ent_delta_pl_thk = tk.Entry(self._frame, textvariable=self._new_delta_pl_thk, width=ent_w)
        self._ent_delta_web_h = tk.Entry(self._frame, textvariable=self._new_delta_web_h, width=ent_w)
        self._ent_delta_web_thk = tk.Entry(self._frame, textvariable=self._new_delta_web_thk, width=ent_w)
        self._ent_delta_fl_w = tk.Entry(self._frame, textvariable=self._new_delta_fl_w, width=ent_w)
        self._ent_delta_fl_thk = tk.Entry(self._frame, textvariable=self._new_delta_fl_thk, width=ent_w)


        pso_width = 10
        self._ent_swarm_size = tk.Entry(self._frame,textvariable=self._new_swarm_size, width = pso_width)
        self._ent_omega = tk.Entry(self._frame,textvariable=self._new_omega, width = pso_width)
        self._ent_phip = tk.Entry(self._frame,textvariable=self._new_phip, width = pso_width)
        self._ent_phig = tk.Entry(self._frame,textvariable=self._new_phig, width = pso_width)
        self._ent_maxiter = tk.Entry(self._frame,textvariable=self._new_maxiter, width = pso_width)
        self._ent_minstep = tk.Entry(self._frame,textvariable=self._new_minstep, width = pso_width)
        self._ent_minfunc = tk.Entry(self._frame,textvariable=self._new_minfunc, width = pso_width)

        start_x, start_y, dx, dy = 20, 70, 100, 40

        self._new_processes = tk.IntVar()
        self._new_processes.set(max(cpu_count() - 1, 1))
        tk.Label(self._frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg = 'silver')\
            .place(x=start_x + 12.3 * dx, y=start_y - 0.2 * dy)
        tk.Entry(self._frame, textvariable=self._new_processes, width = 12, bg = 'silver')\
            .place(x=start_x + 12.3 * dx, y=start_y + 0.7* dy)

        self._prop_canvas_dim = (500, 450)
        self._draw_scale = 500
        self._canvas_opt = tk.Canvas(self._frame, width=self._prop_canvas_dim[0], height=self._prop_canvas_dim[1],
                                    background='azure',relief='groove', borderwidth=2)
        self._canvas_opt.place(x=start_x+10.5*dx, y=start_y+3.5*dy)
        self._select_canvas_dim = (1000, 720)
        self._canvas_select = tk.Canvas(self._frame, width=self._select_canvas_dim[0], height=self._select_canvas_dim[1],
                                       background='azure',relief='groove', borderwidth=2)
        self._canvas_select.place(x=start_x+0*dx, y=start_y+3.5*dy)



        # Labels for the pso
        self._lb_swarm_size = tk.Label(self._frame, text='swarm size')
        self._lb_omega = tk.Label(self._frame, text='omega')
        self._lb_phip = tk.Label(self._frame, text='phip')
        self._lb_phig = tk.Label(self._frame, text='phig')
        self._lb_maxiter = tk.Label(self._frame, text='maxiter')
        self._lb_minstep = tk.Label(self._frame, text='minstep')
        self._lb_minfunc = tk.Label(self._frame, text='minfunc')

        tk.Label(self._frame, text='Upper bounds [mm]', font='Verdana 9').place(x=start_x, y=start_y)
        tk.Label(self._frame, text='Iteration delta [mm]', font='Verdana 9').place(x=start_x, y=start_y + dy)
        tk.Label(self._frame, text='Lower bounds [mm]', font='Verdana 9').place(x=start_x, y=start_y + 2 * dy)
        tk.Label(self._frame, text='Spacing [mm]', font='Verdana 7 bold').place(x=start_x + 1.97 * dx,
                                                                               y=start_y - 0.6 * dy)
        tk.Label(self._frame, text='Plate thk. [mm]', font='Verdana 7 bold').place(x=start_x + 2.97 * dx,
                                                                                  y=start_y - 0.6 * dy)
        tk.Label(self._frame, text='Web height [mm]', font='Verdana 7 bold').place(x=start_x + 3.97 * dx,
                                                                                  y=start_y - 0.6 * dy)
        tk.Label(self._frame, text='Web thk. [mm]', font='Verdana 7 bold').place(x=start_x + 4.97 * dx,
                                                                                y=start_y - 0.6 * dy)
        tk.Label(self._frame, text='Flange width [mm]', font='Verdana 7 bold').place(x=start_x + 5.97 * dx,
                                                                                    y=start_y - 0.6 * dy)
        tk.Label(self._frame, text='Flange thk. [mm]', font='Verdana 7 bold').place(x=start_x + 6.97 * dx,
                                                                                   y=start_y - 0.6 * dy)
        tk.Label(self._frame, text='Estimated running time for algorithm: ',
                 font='Verdana 9 bold').place(x=start_x, y=start_y + 2.8 * dy)
        self._runnig_time_label = tk.Label(self._frame, text='', font='Verdana 9 bold')
        self._runnig_time_label.place(x=start_x + 2.7 * dx, y=start_y + 2.8 * dy)
        tk.Label(self._frame, text='seconds ', font='Verdana 9 bold').place(x=start_x + 3.3 * dx, y=start_y + 2.8 * dy)
        self._result_label = tk.Label(self._frame, text='', font='Verdana 9 bold')
        self._result_label.place(x=start_x, y=start_y + 4 * dy)

        self._ent_spacing_upper.place(x=start_x + dx * 2, y=start_y)
        self._ent_delta_spacing.place(x=start_x + dx * 2, y=start_y + dy)
        self._ent_spacing_lower.place(x=start_x + dx * 2, y=start_y + 2 * dy)
        self._ent_pl_thk_upper.place(x=start_x + dx * 3, y=start_y)
        self._ent_delta_pl_thk.place(x=start_x + dx * 3, y=start_y + dy)
        self._ent_pl_thk_lower.place(x=start_x + dx * 3, y=start_y + 2 * dy)
        self._ent_web_h_upper.place(x=start_x + dx * 4, y=start_y)
        self._ent_delta_web_h.place(x=start_x + dx * 4, y=start_y + dy)
        self._ent_web_h_lower.place(x=start_x + dx * 4, y=start_y + 2 * dy)
        self._ent_web_thk_upper.place(x=start_x + dx * 5, y=start_y)
        self._ent_delta_web_thk.place(x=start_x + dx * 5, y=start_y + dy)
        self._ent_web_thk_lower.place(x=start_x + dx * 5, y=start_y + 2 * dy)
        self._ent_fl_w_upper.place(x=start_x + dx * 6, y=start_y)
        self._ent_delta_fl_w.place(x=start_x + dx * 6, y=start_y + dy)
        self._ent_fl_w_lower.place(x=start_x + dx * 6, y=start_y + 2 * dy)
        self._ent_fl_thk_upper.place(x=start_x + dx * 7, y=start_y)
        self._ent_delta_fl_thk.place(x=start_x + dx * 7, y=start_y + dy)
        self._ent_fl_thk_lower.place(x=start_x + dx * 7, y=start_y + 2 * dy)

        # setting default values
        init_dim = float(50)  # mm
        init_thk = float(2)  # mm
        self._new_delta_spacing.set(init_dim)
        self._new_delta_pl_thk.set(init_thk)
        self._new_delta_web_h.set(init_dim)
        self._new_delta_web_thk.set(init_thk)
        self._new_delta_fl_w.set(init_dim)
        self._new_delta_fl_thk.set(init_thk)
        self._new_spacing_upper.set(round(800, 5))
        self._new_spacing_lower.set(round(600, 5))
        self._new_pl_thk_upper.set(round(25, 5))
        self._new_pl_thk_lower.set(round(10, 5))
        self._new_web_h_upper.set(round(500, 5))
        self._new_web_h_lower.set(round(300, 5))
        self._new_web_thk_upper.set(round(22, 5))
        self._new_web_thk_lower.set(round(10, 5))
        self._new_fl_w_upper.set(round(250, 5))
        self._new_fl_w_lower.set(round(50, 5))
        self._new_fl_thk_upper.set(round(30, 5))
        self._new_fl_thk_lower.set(round(10, 5))
        self._new_algorithm.set('anysmart')
        self._new_algorithm_random_trials.set(10000)

        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)

        self._new_delta_spacing.trace('w', self.update_running_time)
        self._new_delta_pl_thk.trace('w', self.update_running_time)
        self._new_delta_web_h.trace('w', self.update_running_time)
        self._new_delta_web_thk.trace('w', self.update_running_time)
        self._new_delta_fl_w.trace('w', self.update_running_time)
        self._new_delta_fl_thk.trace('w', self.update_running_time)
        self._new_spacing_upper.trace('w', self.update_running_time)
        self._new_spacing_lower.trace('w', self.update_running_time)
        self._new_pl_thk_upper.trace('w', self.update_running_time)
        self._new_pl_thk_lower.trace('w', self.update_running_time)
        self._new_web_h_upper.trace('w', self.update_running_time)
        self._new_web_h_lower.trace('w', self.update_running_time)
        self._new_web_thk_upper.trace('w', self.update_running_time)
        self._new_web_thk_lower.trace('w', self.update_running_time)
        self._new_fl_w_upper.trace('w', self.update_running_time)
        self._new_fl_w_lower.trace('w', self.update_running_time)
        self._new_fl_thk_upper.trace('w', self.update_running_time)
        self._new_fl_thk_lower.trace('w', self.update_running_time)
        self._new_algorithm_random_trials.trace('w', self.update_running_time)
        self._new_algorithm.trace('w', self.update_running_time)

        self.running_time_per_item = 4e-05*4
        self._runnig_time_label.config(text=str(self.get_running_time()))
        tk.Label(self._frame, text='Select algorithm type --->', font='Verdana 8 bold').place(x=start_x + dx * 8,
                                                                                   y=start_y + 1 * dy)
        self._ent_algorithm.place(x=start_x + dx * 10, y=start_y + dy)
        self.algorithm_random_label = tk.Label(self._frame, text='Number of trials')
        tk.Button(self._frame, text='algorithm information', command=self.algorithm_info, bg='white') \
            .place(x=start_x + dx * 15, y=start_y + dy *-0.5)
        self.run_button = tk.Button(self._frame, text='RUN OPTIMIZATION!', command=self.run_optimizaion, bg='red',
                                    font='Verdana 10', fg='Yellow')
        self.run_button.place(x=start_x + dx * 8, y=start_y)
        self.run_results = tk.Button(self._frame,text='show calculated', command=self.plot_results, bg='white',
                                    font='Verdana 10',fg='black')
        self.run_results.place(x=start_x+dx*8, y=start_y+dy*1.5)
        self._opt_actual_running_time.place(x=start_x + dx * 8, y=start_y - dy * 1.5)
        self.close_and_save = tk.Button(self._frame, text='Return and replace with selected optimized structure',
                                        command=self.save_and_close, bg='green', font='Verdana 10 bold', fg='yellow')
        self.close_and_save.place(x=start_x + dx * 10, y=10)

        tk.Button(self._frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10')\
            .place(x=start_x+dx*15,y=10)

        # Selection of constraints
        self._new_check_sec_mod = tk.BooleanVar()
        self._new_check_min_pl_thk = tk.BooleanVar()
        self._new_check_shear_area = tk.BooleanVar()
        self._new_check_buckling = tk.BooleanVar()
        self._new_check_fatigue = tk.BooleanVar()
        self._new_check_slamming = tk.BooleanVar()
        self._new_check_local_buckling = tk.BooleanVar()
        self._new_harmonizer = tk.BooleanVar()
        self._new_check_sec_mod.set(True)
        self._new_check_min_pl_thk.set(True)
        self._new_check_shear_area.set(True)
        self._new_check_buckling.set(True)
        self._new_check_fatigue.set(True)
        self._new_check_slamming.set(False)
        self._new_check_local_buckling.set(True)
        self._new_harmonizer.set(False)


        start_y, start_x, dy = 530, 200, 35
        tk.Label(self._frame,text='Check for minimum section modulus').place(x=start_x+dx*9.7,y=start_y+4*dy)
        tk.Label(self._frame, text='Check for minimum plate thk.').place(x=start_x+dx*9.7,y=start_y+5*dy)
        tk.Label(self._frame, text='Check for minimum shear area').place(x=start_x+dx*9.7,y=start_y+6*dy)
        tk.Label(self._frame, text='Check for buckling (RP-C201)').place(x=start_x+dx*9.7,y=start_y+7*dy)
        tk.Label(self._frame, text='Check for fatigue (RP-C203)').place(x=start_x + dx * 9.7, y=start_y + 8 * dy)
        tk.Label(self._frame, text='Check for bow slamming').place(x=start_x + dx * 9.7, y=start_y + 9 * dy)
        tk.Label(self._frame, text='Check for local stf. buckling').place(x=start_x + dx * 9.7, y=start_y + 10 * dy)
        tk.Label(self._frame, text='Check to harmonize results. Same stiffener and plate dimensions. \n'
                                   '(defined by largest in opt).', font='Verdana 10 bold')\
            .place(x=start_x + dx * +9.3, y=start_y - 10.5 * dy)

        tk.Checkbutton(self._frame,variable=self._new_check_sec_mod).place(x=start_x+dx*12,y=start_y+4*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_min_pl_thk).place(x=start_x+dx*12,y=start_y+5*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_shear_area).place(x=start_x+dx*12,y=start_y+6*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_buckling).place(x=start_x+dx*12,y=start_y+7*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_fatigue).place(x=start_x + dx * 12, y=start_y + 8 * dy)
        tk.Checkbutton(self._frame, variable=self._new_check_slamming).place(x=start_x + dx * 12, y=start_y + 9 * dy)
        tk.Checkbutton(self._frame, variable=self._new_check_local_buckling).place(x=start_x + dx * 12,
                                                                                   y=start_y + 9.5 * dy)
        tk.Checkbutton(self._frame, variable=self._new_harmonizer).place(x=start_x + dx * 9, y=start_y - 10.5 * dy)

        self._toggle_btn = tk.Button(self._frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg = 'salmon')

        self._toggle_btn.place(x=start_x+dx*8.2, y=start_y - dy * 13)
        self._toggle_object, self._filez = None, None



        self.draw_properties()

        # ----------------------------------END OF OPTIMIZE SINGLE COPY-----------------------------------------------
        self.progress_count = tk.IntVar()
        self.progress_count.set(0)
        self.progress_bar = Progressbar(self._frame, orient="horizontal",length=200, mode="determinate",
                                        variable=self.progress_count)
        self.progress_bar.place(x=start_x+dx*10.5,y=start_y-dy*11.5)

        self._active_lines = []
        self.controls()
        self.draw_select_canvas()

    def selected_algorithm(self, event):
        '''
        Action when selecting an algorithm in the optionm menu.
        :return:
        '''
        start_x, start_y, dx, dy = 20, 100, 100, 40
        if self._new_algorithm.get() == 'random' or self._new_algorithm.get() == 'random_no_delta':
            self._ent_random_trials.place_forget()
            self.algorithm_random_label.place_forget()
            self._lb_swarm_size.place_forget()
            self._lb_omega.place_forget()
            self._lb_phip.place_forget()
            self._lb_phig.place_forget()
            self._lb_maxiter.place_forget()
            self._lb_minstep.place_forget()
            self._lb_minfunc.place_forget()
            self._ent_swarm_size.place_forget()
            self._ent_omega.place_forget()
            self._ent_phip.place_forget()
            self._ent_phig.place_forget()
            self._ent_maxiter.place_forget()
            self._ent_minstep.place_forget()
            self._ent_minfunc.place_forget()
            self._ent_random_trials.place(x=start_x + dx * 11.3, y=start_y + 1.2 * dy)
            self.algorithm_random_label.place(x=start_x + dx * 11.3, y=start_y + 0.5 * dy)

        elif self._new_algorithm.get() == 'anysmart' or self._new_algorithm.get() == 'anydetail':
            self._ent_random_trials.place_forget()
            self.algorithm_random_label.place_forget()
            self._lb_swarm_size.place_forget()
            self._lb_omega.place_forget()
            self._lb_phip.place_forget()
            self._lb_phig.place_forget()
            self._lb_maxiter.place_forget()
            self._lb_minstep.place_forget()
            self._lb_minfunc.place_forget()
            self._ent_swarm_size.place_forget()
            self._ent_omega.place_forget()
            self._ent_phip.place_forget()
            self._ent_phig.place_forget()
            self._ent_maxiter.place_forget()
            self._ent_minstep.place_forget()
            self._ent_minfunc.place_forget()

        elif self._new_algorithm.get() == 'pso':
            y_place_label = 11.2
            y_place = 12.2
            self._ent_random_trials.place_forget()
            start_x = 150

            self._lb_swarm_size.place(x=start_x + dx*11 , y=start_y - 1 * dy)
            self._lb_omega.place(x=start_x + dx*11 , y=start_y - 0 * dy)
            self._lb_phip.place(x=start_x + dx*11 , y=start_y + 1 * dy)
            self._lb_phig.place(x=start_x + dx*11 , y=start_y + 2 * dy)

            self._lb_maxiter.place(x=start_x + dx*14 , y=start_y - 1 * dy)
            self._lb_minstep.place(x=start_x + dx*14, y=start_y + 0 * dy)
            self._lb_minfunc.place(x=start_x + dx*14, y=start_y + 1 * dy)

            self._ent_swarm_size.place(x=start_x + dx*12 , y=start_y - 1 * dy)
            self._ent_omega.place(x=start_x + dx*12 , y=start_y - 0 * dy)
            self._ent_phip.place(x=start_x + dx*12 , y=start_y + 1 * dy)
            self._ent_phig.place(x=start_x + dx*12 , y=start_y + 2 * dy)

            self._ent_maxiter.place(x=start_x + dx*15 , y=start_y - 1 * dy)
            self._ent_minstep.place(x=start_x + dx*15, y=start_y + 0 * dy)
            self._ent_minfunc.place(x=start_x + dx*15, y=start_y + 1 * dy)

    def run_optimizaion(self):
        '''
        Function when pressing the optimization botton inside this window.
        :return:
        '''
        self.run_button.config(bg = 'white')

        t_start = time.time()

        self.progress_bar.config(maximum=len(self._active_lines))
        self._opt_actual_running_time.config(text='')
        
        contraints = (self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
                      self._new_check_shear_area.get(), self._new_check_buckling.get(),
                      self._new_check_fatigue.get(), self._new_check_slamming.get(),
                      self._new_check_local_buckling.get())
        
        self.pso_parameters = (self._new_swarm_size.get(),self._new_omega.get(),self._new_phip.get(),
                               self._new_phig.get(),self._new_maxiter.get(),self._new_minstep.get(),
                               self._new_minfunc.get())

        max_min_span = None
        
        self.progress_count.set(0)
        counter = 0
        found_files = self._filez
        for line in self._active_lines:
            init_obj = self._line_to_struc[line][1]

            if __name__ == '__main__':
                lateral_press = 200 #for testing
                fat_obj = test.get_fatigue_object()
                fat_press = test.get_fatigue_pressures()
                slamming_pressure = test.get_slamming_pressure()

            else:
                lateral_press = self.app.get_highest_pressure(line)['normal']/1000

                fat_obj = self.app._line_to_struc[line][2]
                if fat_obj is not None:
                    try:
                        fat_press = self.app.get_fatigue_pressures(line, fat_obj.get_accelerations())
                    except AttributeError:
                        fat_press = None
                else:
                    fat_press = {'p_ext':{'loaded':0,'ballast':0,'part':0}, 'p_int':{'loaded':0, 'ballast':0,'part':0}}

                try:
                    if self.app.get_highest_pressure(line)['slamming'] is None:
                        slamming_pressure = 0
                    else:
                        slamming_pressure = self.app.get_highest_pressure(line)['slamming']
                except KeyError:
                    slamming_pressure = 0

            fat_press = ((fat_press['p_ext']['loaded'], fat_press['p_ext']['ballast'],
                          fat_press['p_ext']['part']),
                         (fat_press['p_int']['loaded'], fat_press['p_int']['ballast'],
                          fat_press['p_int']['part']))

            if self._toggle_btn.config('relief')[-1] == 'sunken':
                found_files, predefined_stiffener_iter = self.toggle(found_files=found_files, obj = init_obj,
                                                                     iterating=True)
            else:
                predefined_stiffener_iter = None

            self._opt_results[line] = list(op.run_optmizataion(init_obj, self.get_lower_bounds(init_obj),
                                                          self.get_upper_bounds(init_obj),
                                                          lateral_press,self.get_deltas(),
                                                          algorithm=self._new_algorithm.get(),
                                                          trials=self._new_algorithm_random_trials.get(),
                                                          side=init_obj.get_side(),
                                                          const_chk=contraints,
                                                          pso_options=self.pso_parameters,
                                                          fatigue_obj=fat_obj,
                                                          fat_press_ext_int=fat_press,
                                                          slamming_press=slamming_pressure,
                                                          predefined_stiffener_iter = predefined_stiffener_iter,
                                                          processes=self._new_processes.get(),
                                                          min_max_span=max_min_span))

            counter += 1
            self.progress_count.set(counter)
            self.progress_bar.update_idletasks()

            if self._opt_results[line] != None:
                self._opt_actual_running_time.config(text='Accumulated running time: \n'
                                                         + str(time.time() - t_start) + ' sec')
            else:
                pass

        if self._new_harmonizer.get() == True:
            self.opt_harmonizer()

        counter += 1
        self.progress_bar.stop()
        self.run_button.config(bg='green')
        self.draw_properties()

    def opt_harmonizer(self):
        '''
        Harmonizes the results of you run.
        :return:
        '''

        # Find highest section modulus.
        highest = 0

        for line in self._opt_results.keys(): # TODO stresses not set correctly when returning.
            # print(line, self._opt_results[line][1].get_section_modulus())
            # print(self._opt_results[line][1])
            assert self._opt_results[line][1].get_tuple() == self._opt_results[line][1].get_tuple(), \
                'Structure object dimensions and calculation object dimensions are not similar.\n'+ \
                str(self._opt_results[line][1].get_tuple()) + str(self._opt_results[line][1].get_tuple())
            init_obj = self._opt_results[line][1]
            weight = op.calc_weight([init_obj.get_s(), init_obj.get_pl_thk(), init_obj.get_web_h(),
                                     init_obj.get_web_thk(), init_obj.get_fl_w(), init_obj.get_fl_thk(),
                                     init_obj.get_span(),init_obj.get_lg()])
            if weight > highest:
                highest = weight
                highest_line = line

        harmonized_x = self._opt_results[highest_line][1].get_tuple()
        for line in self._opt_results.keys():
            self._opt_results[line][0] = opt.create_new_structure_obj(self._line_to_struc[line][0], harmonized_x)
            self._opt_results[line][1] = opt.create_new_calc_obj(self._line_to_struc[line][1], harmonized_x)[0]

    def get_running_time(self):
        '''
        Estimate the running time of the algorithm.
        :return:
        '''
        if self._new_algorithm.get() in ['anysmart', 'anydetail']:
            try:
                number_of_combinations = \
                    max((self._new_spacing_upper.get() - self._new_spacing_lower.get()) / self._new_delta_spacing.get(),
                        1) * \
                    max((self._new_pl_thk_upper.get() - self._new_pl_thk_lower.get()) / self._new_delta_pl_thk.get(), 1) * \
                    max((self._new_web_h_upper.get() - self._new_web_h_lower.get()) / self._new_delta_web_h.get(), 1) * \
                    max((self._new_web_thk_upper.get() - self._new_web_thk_lower.get()) / self._new_delta_web_thk.get(),
                        1) * \
                    max((self._new_fl_w_upper.get() - self._new_fl_w_lower.get()) / self._new_delta_fl_w.get(), 1) * \
                    max((self._new_fl_thk_upper.get() - self._new_fl_thk_lower.get()) / self._new_delta_fl_thk.get(), 1)
                return int(number_of_combinations * self.running_time_per_item)*len(self._active_lines)
            except TclError:
                return 0
        else:
            try:
                return int(self._new_algorithm_random_trials.get() * self.running_time_per_item)*len(self._active_lines)
            except TclError:
                return 0

    def get_deltas(self):
        '''
        Return a numpy array of the deltas.
        :return:
        '''
        return np.array([float(self._ent_delta_spacing.get()) / 1000, float(self._new_delta_pl_thk.get()) / 1000,
                         float(self._new_delta_web_h.get()) / 1000, float(self._new_delta_web_thk.get()) / 1000,
                         float(self._new_delta_fl_w.get()) / 1000, float(self._new_delta_fl_thk.get()) / 1000])

    def update_running_time(self, *args):
        '''
        Estimate the running time of the algorithm.
        :return:
        '''
        try:
            self._runnig_time_label.config(text=str(self.get_running_time()))
        except ZeroDivisionError:
            pass  # _tkinter.TclError: pass

    def get_upper_bounds(self,obj):
        '''
        Return an numpy array of upper bounds.
        :return: 
        '''
        return np.array([self._new_spacing_upper.get() / 1000, self._new_pl_thk_upper.get() / 1000,
                         self._new_web_h_upper.get() / 1000, self._new_web_thk_upper.get() / 1000,
                         self._new_fl_w_upper.get() / 1000, self._new_fl_thk_upper.get() / 1000,
                         obj.get_span(), obj.get_lg()])

    def get_lower_bounds(self,obj):
        '''
        Return an numpy array of lower bounds.
        :return: 
        '''
        return np.array([self._new_spacing_lower.get() / 1000, self._new_pl_thk_lower.get() / 1000,
                         self._new_web_h_lower.get() / 1000, self._new_web_thk_lower.get() / 1000,
                         self._new_fl_w_lower.get() / 1000, self._new_fl_thk_lower.get() / 1000,
                         obj.get_span(), obj.get_lg()])

    def checkered(self, line_distance):
        '''
        Creates a grid in the properties canvas.
        :param line_distance: 
        :return: 
        '''
        # vertical lines at an interval of "line_distance" pixel
        for x in range(line_distance, self._prop_canvas_dim[0], line_distance):
            self._canvas_opt.create_line(x, 0, x, self._prop_canvas_dim[0], fill="grey", stipple='gray50')
        # horizontal lines at an interval of "line_distance" pixel
        for y in range(line_distance, self._prop_canvas_dim[1], line_distance):
            self._canvas_opt.create_line(0, y, self._prop_canvas_dim[0], y, fill="grey", stipple='gray50')

    def draw_properties(self,init_obj = None, opt_obj=None,line=None):
        '''
        Drawing properties in the canvas.
        :return:
        '''
        ctr_x = self._prop_canvas_dim[0] / 2
        ctr_y = self._prop_canvas_dim[1] / 2 + 200
        opt_color, opt_stippe = 'red', 'gray12'
        m = self._draw_scale
        self._canvas_opt.delete('all')
        if init_obj != None:

            self.checkered(10)
            init_color, init_stipple = 'blue', 'gray12'

            self._canvas_opt.create_rectangle(0, 0, self._prop_canvas_dim[0] + 10, 80, fill='white')
            self._canvas_opt.create_line(10, 10, 30, 10, fill=init_color, width=5)
            self._canvas_opt.create_text(270, 10, text='Initial    - Pl.: ' + str(init_obj.get_s() * 1000) + 'x' + str(
                init_obj.get_pl_thk() * 1000) +
                                                      ' Stf.: ' + str(init_obj.get_web_h() * 1000) + 'x' + str(
                init_obj.get_web_thk() * 1000) + '+' +
                                                      str(init_obj.get_fl_w() * 1000) + 'x' + str(init_obj.get_fl_thk() * 1000),
                                        font='Verdana 8',
                                        fill=init_color)
            self._canvas_opt.create_text(120, 30, text='Weight (per Lg width): ' +
                                                      str(int(op.calc_weight([init_obj.get_s(),
                                                                              init_obj.get_pl_thk(),
                                                                              init_obj.get_web_h(),
                                                                              init_obj.get_web_thk(),
                                                                              init_obj.get_fl_w(),
                                                                              init_obj.get_fl_thk(),
                                                                              init_obj.get_span(),
                                                                              init_obj.get_lg()]))),
                                        font='Verdana 8', fill=init_color)
    
            self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_s() / 2, ctr_y, ctr_x + m * init_obj.get_s() / 2,
                                             ctr_y - m * init_obj.get_pl_thk(), fill=init_color, stipple=init_stipple)
            self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_web_thk() / 2, ctr_y - m * init_obj.get_pl_thk(),
                                             ctr_x + m * init_obj.get_web_thk() / 2, ctr_y - m * (init_obj.get_web_h() + init_obj.get_pl_thk())
                                             , fill=init_color, stipple=init_stipple)
            if init_obj.get_stiffener_type() != 'L':
                self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_fl_w() / 2, ctr_y - m * (init_obj.get_pl_thk() + init_obj.get_web_h()),
                                                 ctr_x + m * init_obj.get_fl_w() / 2,
                                                 ctr_y - m * (init_obj.get_pl_thk() + init_obj.get_web_h() + init_obj.get_fl_thk()),
                                                 fill=init_color, stipple=init_stipple)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_web_thk() / 2,
                                                 ctr_y - m * (init_obj.get_pl_thk() + init_obj.get_web_h()),
                                                 ctr_x + m * init_obj.get_fl_w(),
                                                 ctr_y - m * (init_obj.get_pl_thk() + init_obj.get_web_h() + init_obj.get_fl_thk()),
                                                 fill=init_color, stipple=init_stipple)
    
        if opt_obj != None:
            # [0.6, 0.012, 0.25, 0.01, 0.1, 0.01]
            self._canvas_opt.config(bg = 'palegreen')
            self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.get_s() / 2, ctr_y,
                                             ctr_x + m * opt_obj.get_s() / 2,
                                             ctr_y - m * opt_obj.get_pl_thk(), fill=opt_color,
                                             stipple=opt_stippe)

            self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.get_web_thk() / 2, ctr_y -
                                             m * opt_obj.get_pl_thk(),
                                             ctr_x + m * opt_obj.get_web_thk() / 2,
                                             ctr_y - m * (
                                             opt_obj.get_web_h() + opt_obj.get_pl_thk())
                                             , fill=opt_color, stipple=opt_stippe)
            if init_obj.get_stiffener_type() != 'L':
                self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.get_fl_w() / 2, ctr_y
                                                 - m * (
                                                 opt_obj.get_pl_thk() + opt_obj.get_web_h()),
                                                 ctr_x + m * opt_obj.get_fl_w() / 2, ctr_y -
                                                 m * (
                                                 opt_obj.get_pl_thk() + opt_obj.get_web_h() +
                                                 opt_obj.get_fl_thk()),
                                                 fill=opt_color, stipple=opt_stippe)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.get_web_thk() / 2, ctr_y
                                                 - m * (
                                                 opt_obj.get_pl_thk() + opt_obj.get_web_h()),
                                                 ctr_x + m * opt_obj.get_fl_w(), ctr_y -
                                                 m * (
                                                 opt_obj.get_pl_thk() + opt_obj.get_web_h() +
                                                 opt_obj.get_fl_thk()),
                                                 fill=opt_color, stipple=opt_stippe)

            self._canvas_opt.create_line(10, 50, 30, 50, fill=opt_color, width=5)
            self._canvas_opt.create_text(270, 50,
                                        text='Optimized - Pl.: ' + str(round(opt_obj.get_s() * 1000,1)) + 'x' +
                                             str(round(opt_obj.get_pl_thk() * 1000,1)) + ' Stf.: '
                                             + str(round(opt_obj.get_web_h() * 1000,1)) +
                                             'x' + str(round(opt_obj.get_web_thk() * 1000,1)) + '+' +
                                             str(round(opt_obj.get_fl_w() * 1000,1)) +
                                             'x' + str(round(opt_obj.get_fl_thk() * 1000,1)),
                                        font='Verdana 8', fill=opt_color)
            self._canvas_opt.create_text(120, 70, text='Weight (per Lg width): '
                                                      + str(int(op.calc_weight([opt_obj.get_s(),
                                                                                opt_obj.get_pl_thk(),
                                                                                opt_obj.get_web_h(),
                                                                                opt_obj.get_web_thk(),
                                                                                opt_obj.get_fl_w(),
                                                                                opt_obj.get_fl_thk(),
                                                                                opt_obj.get_span(),
                                                                                opt_obj.get_lg()]))),
                                        font='Verdana 8', fill=opt_color)
        elif self._opt_results != {}:
            self._canvas_opt.config(bg='green')
            self._canvas_opt.create_text(200, 200, text='Optimization results avaliable.\n\n'
                                                       'Middle click line to view results.', font = 'Verdana 14 bold')

        else:
            self._canvas_opt.config(bg='mistyrose')
            self._canvas_opt.create_text(200, 60, text='No optimization results found.', font = 'Verdana 14 bold')



        if line != None:
            if __name__ == '__main__':
                lateral_press = 200  # for testing
            else:
                lateral_press = self.app.get_highest_pressure(line)['normal'] / 1000
            self._canvas_opt.create_text(250, self._prop_canvas_dim[1]-10,
                                        text= line + ' lateral pressure: '+str(lateral_press)+' kPa',
                                        font='Verdana 10 bold',fill='red')
            
    def draw_select_canvas(self, load_selected=False):
        '''
        Making the lines canvas.
        :return:
        '''
        self._canvas_select.delete('all')

        # grid for the canavs

        self._canvas_select.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0], self._select_canvas_dim[1],
                                     stipple='gray50')
        self._canvas_select.create_line(0, self._canvas_draw_origo[1], self._select_canvas_dim[0], self._canvas_draw_origo[1],
                                     stipple='gray50')
        self._canvas_select.create_text(self._canvas_draw_origo[0] - 30 ,
                                     self._canvas_draw_origo[1] + 20 , text='(0,0)',
                                     font='Text 10')
        self._canvas_select.create_text([800 ,60],
                                     text='Mouse left click:  select lines to loads\n'
                                          'Mouse mid click: show properties for one line\n'
                                          'Mouse right click: clear all selection\n'
                                          'Shift key press: add selected line\n'
                                          'Control key press: remove selected line\n\n'
                                          'NOTE! Select lines you want to return before\n'
                                          'pressing return button.', font='Verdana 8 bold',
                                     fill='red')
        # drawing the line dictionary.
        if len(self._line_dict) != 0:
            for line, value in self._line_dict.items():
                color = 'black'
                coord1 = self.get_point_canvas_coord('point' + str(value[0]))
                coord2 = self.get_point_canvas_coord('point' + str(value[1]))

                vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                # drawing a bold line if it is selected
                if line in self._active_lines:
                    width = 6
                    if line in self._opt_results.keys():
                        color, width = 'orange', 8
                    self._canvas_select.create_line(coord1, coord2, width=width, fill=color)
                    self._canvas_select.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 + 10,
                                                 text='Line ' + str(get_num(line)), font='Verdand 10 bold',
                                                 fill='red')
                else:
                    if line in self._opt_results.keys():
                        color = 'orange'
                    self._canvas_select.create_line(coord1, coord2, width=3, fill=color)
                    self._canvas_select.create_text(coord1[0] - 20 + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 + 10,
                                                 text='line' + str(get_num(line)), font="Text 8", fill='black')

    def algorithm_info(self):
        ''' When button is clicked, info is displayed.'''

        messagebox.showinfo(title='Algorithm information',
                            message='The algorithms currently included is:\n'
                                    'ANYSMART:  \n'
                                    '           Calculates all alternatives using upper and lower bounds.\n'
                                    '           The step used inside the bounds is defined in deltas.\n\n'
                                    'RANDOM:    \n'
                                    '           Uses the same bounds and deltas as in ANYSMART.\n'
                                    '           Number of combinations calculated is defined in "trials",\n'
                                    '           which selects withing the bounds and deltas defined.\n\n'
                                    'RANDOM_NO_BOUNDS:\n'
                                    '           Same as RANDOM, but does not use the defined deltas.\n'
                                    '           The deltas is set to 1 mm for all dimensions/thicknesses.\n\n'
                                    'ANYDETAIL:\n'
                                    '           Same as for ANYSMART, but will take some more time and\n'
                                    '           provide a chart of weight development during execution.\n\n'
                                    'PSO - Particle Swarm Search:\n'
                                    '           The information can be found on \n'
                                    '           http://pythonhosted.org/pyswarm/ \n'
                                    '           For further information google it!\n'
                                    '           Parameters:\n'
                                    '           swarmsize : The number of particles in the swarm (Default: 100)\n'
                                    '           omega : Particle velocity scaling factor (Default: 0.5)\n'
                                    '           phip : Scaling factor to search away from the particle’s \n'
                                    '                           best known position (Default: 0.5)\n'
                                    '           phig : Scaling factor to search away from the swarm’s best \n'
                                    '                           known position (Default: 0.5)\n'
                                    '           maxiter : The maximum number of iterations for the swarm \n'
                                    '                           to search (Default: 100)\n'
                                    '           minstep : The minimum stepsize of swarm’s best position \n'
                                    '                           before the search terminates (Default: 1e-8)\n'
                                    '           minfunc : The minimum change of swarm’s best objective value\n'
                                    '                           before the search terminates (Default: 1e-8)\n\n'

                                    '\n'
                                    'All algorithms calculates local scantling and buckling requirements')

    def slider_used(self, event):
        '''
        Action when slider is activated.
        :return:
        '''
        self._canvas_scale = self.slider.get()
        self.draw_canvas()

    def on_closing(self):
        '''
        Action when closing the window without saving.
        :return:
        '''
        if __name__ == '__main__':
            self._frame.destroy()
            return

        mess = tk.messagebox.showwarning('Closed without saving', 'Closing will not save loads you have created',
                                  type = 'okcancel')
        if mess == 'ok':
            self._frame.grab_release()
            self._frame.destroy()
            self.app.on_aborted_load_window()

    def get_point_canvas_coord(self, point_no):
        '''
        Returning the canvas coordinates of the point. This value will change with slider.
        :param point_no: 
        :return: 
        '''
        point_coord_x = self._canvas_draw_origo[0] + self._point_dict[point_no][0]* self._canvas_scale
        point_coord_y = self._canvas_draw_origo[1] - self._point_dict[point_no][1]* self._canvas_scale

        return [point_coord_x, point_coord_y]

    def controls(self):
        '''
        Specifying the controls to be used.
        :return:
        '''
        self._canvas_select.bind('<Button-1>', self.left_click)
        self._canvas_select.bind('<Button-2>', self.mid_click)
        self._canvas_select.bind('<Button-3>', self.right_click)

        self._frame.bind('<Shift_L>', self.shift_pressed)
        self._frame.bind('<Shift_R>', self.shift_pressed)
        self._frame.bind('<Control_L>', self.ctrl_pressed)
        self._frame.bind('<Control_R>', self.ctrl_pressed)
        self._frame.bind("<MouseWheel>", self.mouse_scroll)
        self._frame.bind("<B2-Motion>", self.button_2_click_and_drag)

    def shift_pressed(self,event=None):
        '''
        Event is executed when shift key pressed.
        :return:
        '''
        self._add_to_lines = True

    def ctrl_pressed(self,event=None):
        '''
        Event when control is pressed.
        :param event:
        :return:
        '''
        self._add_to_lines = False

    def left_click(self, event):
        '''
        When clicking the right button, this method is called.
        method is referenced in
        '''
        self._previous_drag_mouse = [event.x, event.y]
        click_x = self._canvas_select.winfo_pointerx() - self._canvas_select.winfo_rootx()
        click_y = self._canvas_select.winfo_pointery() - self._canvas_select.winfo_rooty()
        stop = False

        if len(self._line_dict) > 0:
            for key, value in self._line_dict.items():

                coord1x = self.get_point_canvas_coord('point' + str(value[0]))[0]
                coord2x = self.get_point_canvas_coord('point' + str(value[1]))[0]
                coord1y = self.get_point_canvas_coord('point' + str(value[0]))[1]
                coord2y = self.get_point_canvas_coord('point' + str(value[1]))[1]

                vector = [coord2x - coord1x, coord2y - coord1y]
                click_x_range = [ix for ix in range(click_x - 10, click_x + 10)]
                click_y_range = [iy for iy in range(click_y - 10, click_y + 10)]
                distance = int(dist([coord1x, coord1y], [coord2x, coord2y]))

                # checking along the line if the click is witnin +- 10 around the click
                for dist_mult in range(1, distance - 1):
                    dist_mult = dist_mult / distance
                    x_check = int(coord1x) + int(round(vector[0] * dist_mult, 0))
                    y_check = int(coord1y) + int(round(vector[1] * dist_mult, 0))
                    if x_check in click_x_range and y_check in click_y_range:
                        self.line_is_active = True
                        if self._add_to_lines:
                            if key not in self._active_lines:
                                self._active_lines.append(key)
                        elif self._add_to_lines== False:
                            if key in self._active_lines:
                                self._active_lines.remove(key)
                        self._canvas_select.delete('all')
                        break
        self.draw_select_canvas()
        self.update_running_time()

    def right_click(self,event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
        self._previous_drag_mouse = [event.x, event.y]
        self._active_lines = []
        self._canvas_select.delete('all')
        self.draw_select_canvas()
        self.update_running_time()

    def mid_click(self,event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''

        self._previous_drag_mouse = [event.x, event.y]
        if self._opt_results == {}:
            return
        click_x = self._canvas_select.winfo_pointerx() - self._canvas_select.winfo_rootx()
        click_y = self._canvas_select.winfo_pointery() - self._canvas_select.winfo_rooty()

        if len(self._line_dict) > 0:
            for key, value in self._line_dict.items():

                coord1x = self.get_point_canvas_coord('point' + str(value[0]))[0]
                coord2x = self.get_point_canvas_coord('point' + str(value[1]))[0]
                coord1y = self.get_point_canvas_coord('point' + str(value[0]))[1]
                coord2y = self.get_point_canvas_coord('point' + str(value[1]))[1]

                vector = [coord2x - coord1x, coord2y - coord1y]
                click_x_range = [ix for ix in range(click_x - 10, click_x + 10)]
                click_y_range = [iy for iy in range(click_y - 10, click_y + 10)]
                distance = int(dist([coord1x, coord1y], [coord2x, coord2y]))

                # checking along the line if the click is witnin +- 10 around the click
                for dist_mult in range(1, distance - 1):
                    dist_mult = dist_mult / distance
                    x_check = int(coord1x) + int(round(vector[0] * dist_mult, 0))
                    y_check = int(coord1y) + int(round(vector[1] * dist_mult, 0))
                    if x_check in click_x_range and y_check in click_y_range:
                        self._canvas_select.delete('all')
                        self._active_lines = []
                        self._active_lines.append(key)
                        if key in self._opt_results.keys() and self._opt_results[key]!=None:
                            self.draw_properties(init_obj=self._line_to_struc[key][0],opt_obj=self._opt_results[key][0],
                                                 line=key)
                            self._mid_click_line = key
                        else:
                            self.draw_properties(init_obj=self._line_to_struc[key][0],line=key)
                            self._mid_click_line = None
                        break
                self.draw_select_canvas()
        self.draw_select_canvas()
        self.update_running_time()

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''
        if __name__ == '__main__':
            self._frame.destroy()
            return
        try:
            to_return = {}
            for line in self._active_lines:
                to_return[line] = self._opt_results[line]
            self.app.on_close_opt_multiple_window(to_return)
            messagebox.showinfo(title='Return info', message='Returning: '+str(list(to_return.keys())))
        except IndexError:
            messagebox.showinfo(title='Nothing to return', message='No results to return.')
            return
        self._frame.destroy()

    def toggle(self, found_files = None, obj = None, iterating = False):
        '''
        On off button.
        :param found_files:
        :param obj:
        :return:
        '''
        if iterating:
            if found_files is not None:
                predefined_structure = hlp.helper_read_section_file(files=found_files, obj=obj)
        else:
            predefined_structure = None
            if self._toggle_btn.config('relief')[-1] == 'sunken':
                self._toggle_btn.config(relief="raised")
                self._toggle_btn.config(bg = 'salmon')
                self._ent_spacing_upper.config(bg = 'white')
                self._ent_spacing_lower.config(bg = 'white')
                self._ent_delta_spacing.config(bg = 'white')
            else:
                self._toggle_btn.config(relief="sunken")
                self._toggle_btn.config(bg='lightgreen')
                self._ent_spacing_upper.config(bg = 'lightgreen')
                self._ent_spacing_lower.config(bg = 'lightgreen')
                self._ent_delta_spacing.config(bg = 'lightgreen')
                openfile = list(askopenfilenames(parent=self._frame, title='Choose files to open'))
                if openfile == []:
                    self._toggle_btn.config(relief="raised")
                    self._toggle_btn.config(bg='salmon')
                    self._ent_spacing_upper.config(bg='white')
                    self._ent_spacing_lower.config(bg='white')
                    self._ent_delta_spacing.config(bg='white')
                else:
                    self._filez = openfile

        return found_files, predefined_structure

    def toggle_harmonizer(self):
        pass

    def plot_results(self):
        if self._mid_click_line is not None:
            if len(self._opt_results[self._mid_click_line]) != 0:
                op.plot_optimization_results(self._opt_results[self._mid_click_line])

    def mouse_scroll(self,event):
        self._canvas_scale +=  event.delta/50
        self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale

        self.draw_select_canvas()

    def button_2_click_and_drag(self,event):

        self._canvas_draw_origo = (self._canvas_draw_origo[0]-(self._previous_drag_mouse[0]-event.x),
                                  self._canvas_draw_origo[1]-(self._previous_drag_mouse[1]-event.y))

        self._previous_drag_mouse = (event.x,event.y)
        self.draw_select_canvas()

    def open_example_file(self):
        import os
        if os.path.isfile('sections.csv'):
            os.startfile('sections.csv')
        else:
            os.startfile(self._root_dir + '/' + 'sections.csv')


if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateOptimizeMultipleWindow(master=root)
    root.mainloop()



