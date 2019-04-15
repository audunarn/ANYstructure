# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError
from tkinter.ttk import Progressbar
import ANYstructure.optimize as op
import numpy as np
import time
from tkinter import messagebox
import ANYstructure.example_data as test
from ANYstructure.helper import *
import copy, pickle
import ANYstructure.calc_structure
import ANYstructure.helper as hlp
from tkinter.filedialog import askopenfilenames
from multiprocessing import cpu_count
from tkinter import filedialog

class CreateOptGeoWindow():
    '''
    This class initiates the MultiOpt window.
    '''

    def __init__(self, master, app=None):
        super(CreateOptGeoWindow, self).__init__()
        if __name__ == '__main__':
            self._load_objects = {}
            self._load_comb_dict = {}
            self._line_dict = test.get_line_dict()
            self._load_count = 0
            self._point_dict = test.get_point_dict()
            self._canvas_scale = 20
            self._line_to_struc = test.get_line_to_struc()
            self._opt_frames = {}
            self._active_points = ['point1','point4','point8','point5']
        else:
            self.app = app
            self._load_objects = app._load_dict
            self._load_comb_dict = app._new_load_comb_dict
            self._line_dict = app._line_dict
            self._load_count = 0
            self._point_dict = app._point_dict
            self._canvas_scale = app._canvas_scale
            self._line_to_struc = app._line_to_struc
            self._opt_frames = {}
            self._active_points = []
            self._root_dir = app._root_dir


        self._opt_structure = {}
        self._opt_frames_obj = []
        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1800x950')
        self._frame.grab_set()
        self._canvas_origo = (50, 720 - 50)

        self._active_lines = []
        self._add_to_lines = True
        self._lines_add_to_load = []
        self._active_point = None
        self._point_is_active = False

        # ----------------------------------COPIED FROM OPTIMIZE_WINDOW----------------------------------------------- #

        self._opt_resutls = {}
        self._geo_results = None
        self._opt_actual_running_time = tk.Label(self._frame, text='')

        tk.Frame(self._frame, width=770, height=5, bg="grey", colormap="new").place(x=20, y=95)
        tk.Frame(self._frame, width=770, height=5, bg="grey", colormap="new").place(x=20, y=135)

        algorithms = ('anysmart',' ')

        tk.Label(self._frame, text='-- Plate field span optimizer for plate fields separated by frames. --',
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
        self._new_omega = tk.DoubleVar()
        self._new_phip = tk.DoubleVar()
        self._new_phig = tk.DoubleVar()
        self._new_maxiter = tk.IntVar()
        self._new_minstep = tk.DoubleVar()
        self._new_minfunc = tk.DoubleVar()
        self._new_processes = tk.IntVar()
        self._new_opt_girder_thk = tk.DoubleVar()
        self._new_opt_girder_stf_web_h = tk.DoubleVar()
        self._new_opt_girder_stf_web_thk = tk.DoubleVar()
        self._new_opt_girder_stf_flange_b = tk.DoubleVar()
        self._new_opt_girder_stf_flange_thk = tk.DoubleVar()
        self._new_opt_girder_scale_high = tk.DoubleVar()
        self._new_opt_girder_scale_low = tk.DoubleVar()
        self._new_opt_span_max = tk.DoubleVar()
        self._new_opt_span_min = tk.DoubleVar()

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
        self._ent_algorithm = tk.OptionMenu(self._frame, self._new_algorithm, command=self.selected_algorithm,
                                            *algorithms)
        self._ent_random_trials = tk.Entry(self._frame, textvariable=self._new_algorithm_random_trials)
        self._ent_delta_spacing = tk.Entry(self._frame, textvariable=self._new_delta_spacing, width=ent_w)
        self._ent_delta_pl_thk = tk.Entry(self._frame, textvariable=self._new_delta_pl_thk, width=ent_w)
        self._ent_delta_web_h = tk.Entry(self._frame, textvariable=self._new_delta_web_h, width=ent_w)
        self._ent_delta_web_thk = tk.Entry(self._frame, textvariable=self._new_delta_web_thk, width=ent_w)
        self._ent_delta_fl_w = tk.Entry(self._frame, textvariable=self._new_delta_fl_w, width=ent_w)
        self._ent_delta_fl_thk = tk.Entry(self._frame, textvariable=self._new_delta_fl_thk, width=ent_w)

        pso_width = 10
        self._ent_swarm_size = tk.Entry(self._frame, textvariable=self._new_swarm_size, width=pso_width)
        self._ent_omega = tk.Entry(self._frame, textvariable=self._new_omega, width=pso_width)
        self._ent_phip = tk.Entry(self._frame, textvariable=self._new_phip, width=pso_width)
        self._ent_phig = tk.Entry(self._frame, textvariable=self._new_phig, width=pso_width)
        self._ent_maxiter = tk.Entry(self._frame, textvariable=self._new_maxiter, width=pso_width)
        self._ent_minstep = tk.Entry(self._frame, textvariable=self._new_minstep, width=pso_width)
        self._ent_minfunc = tk.Entry(self._frame, textvariable=self._new_minfunc, width=pso_width)

        self._ent_opt_girder_thk = tk.Entry(self._frame, textvariable=self._new_opt_girder_thk, width=ent_w)
        self._ent_opt_girder_stf_web_h = tk.Entry(self._frame, textvariable=self._new_opt_girder_stf_web_h,
                                                  width=ent_w)
        self._ent_opt_girder_stf_web_thk = tk.Entry(self._frame, textvariable=self._new_opt_girder_stf_web_thk,
                                                    width=ent_w)
        self._ent_opt_girder_stf_fl_b = tk.Entry(self._frame, textvariable=self._new_opt_girder_stf_flange_b,
                                                 width=ent_w)
        self._ent_opt_girder_stf_fl_thk = tk.Entry(self._frame, textvariable=self._new_opt_girder_stf_flange_thk,
                                                   width=ent_w)

        self._ent_opt_girder_scale_high = tk.Entry(self._frame, textvariable=self._new_opt_girder_scale_high,
                                                   width=int(ent_w/2))
        self._ent_opt_girder_scale_low = tk.Entry(self._frame, textvariable=self._new_opt_girder_scale_low,
                                                   width=int(ent_w/2))

        self._ent_opt_max_span = tk.Entry(self._frame, textvariable=self._new_opt_span_max,
                                                   width=int(ent_w/2))
        self._ent_opt_min_span = tk.Entry(self._frame, textvariable=self._new_opt_span_min,
                                                   width=int(ent_w/2))


        start_x, start_y, dx, dy = 20, 70, 100, 40

        tk.Label(self._frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg = 'silver')\
            .place(x=start_x + 8 * dx, y=start_y + 0.5 * dy)
        tk.Entry(self._frame, textvariable=self._new_processes, width = 12, bg = 'silver')\
            .place(x=start_x + 8 * dx, y=start_y + 1.4 * dy)

        self._prop_canvas_dim = (500, 450)
        self._draw_scale = 500
        self._canvas_opt = tk.Canvas(self._frame, width=self._prop_canvas_dim[0], height=self._prop_canvas_dim[1],
                                     background='azure', relief='groove', borderwidth=2)
        self._canvas_opt.place(x=start_x + 10.5 * dx, y=start_y + 3.5 * dy)
        self._select_canvas_dim = (1000, 720)
        self._canvas_select = tk.Canvas(self._frame, width=self._select_canvas_dim[0],
                                        height=self._select_canvas_dim[1],
                                        background='azure', relief='groove', borderwidth=2)
        self._canvas_select.place(x=start_x + 0 * dx, y=start_y + 3.5 * dy)

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
        self._result_label.place(x=start_x, y=start_y + 3.4 * dy)

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
        self._new_processes.set(max(cpu_count() - 1, 1))
        self._new_opt_girder_thk.set(0.018)
        self._new_opt_girder_stf_web_h.set(0.250)
        self._new_opt_girder_stf_web_thk.set(0.015)
        self._new_opt_girder_stf_flange_b.set(0)
        self._new_opt_girder_stf_flange_thk.set(0)
        self._new_opt_girder_scale_high.set(1.2)
        self._new_opt_girder_scale_low.set(0.8)
        self._new_opt_span_max.set(6)
        self._new_opt_span_min.set(2)

        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)

        # self._new_delta_spacing.trace('w', self.update_running_time)
        # self._new_delta_pl_thk.trace('w', self.update_running_time)
        # self._new_delta_web_h.trace('w', self.update_running_time)
        # self._new_delta_web_thk.trace('w', self.update_running_time)
        # self._new_delta_fl_w.trace('w', self.update_running_time)
        # self._new_delta_fl_thk.trace('w', self.update_running_time)
        # self._new_spacing_upper.trace('w', self.update_running_time)
        # self._new_spacing_lower.trace('w', self.update_running_time)
        # self._new_pl_thk_upper.trace('w', self.update_running_time)
        # self._new_pl_thk_lower.trace('w', self.update_running_time)
        # self._new_web_h_upper.trace('w', self.update_running_time)
        # self._new_web_h_lower.trace('w', self.update_running_time)
        # self._new_web_thk_upper.trace('w', self.update_running_time)
        # self._new_web_thk_lower.trace('w', self.update_running_time)
        # self._new_fl_w_upper.trace('w', self.update_running_time)
        # self._new_fl_w_lower.trace('w', self.update_running_time)
        # self._new_fl_thk_upper.trace('w', self.update_running_time)
        # self._new_fl_thk_lower.trace('w', self.update_running_time)
        # self._new_algorithm_random_trials.trace('w', self.update_running_time)
        # self._new_algorithm.trace('w', self.update_running_time)

        self.running_time_per_item = 4e-05
        self._runnig_time_label.config(text=str(self.get_running_time()))
        self._ent_algorithm.place(x=start_x + dx * 10, y=start_y + dy)
        self.algorithm_random_label = tk.Label(self._frame, text='Number of trials')
        tk.Button(self._frame, text='algorith information', command=self.algorithm_info, bg='white') \
            .place(x=start_x + dx * 10, y=start_y + dy * 2)
        self.run_button = tk.Button(self._frame, text='RUN OPTIMIZATION!', command=self.run_optimizaion, bg='red',
                                    font='Verdana 10', fg='Yellow')
        self.run_button.place(x=start_x + dx * 10, y=start_y)
        self._opt_actual_running_time.place(x=start_x + dx * 8, y=start_y + dy * 1.5)
        # self.close_and_save = tk.Button(self._frame, text='Return and replace with selected optimized structure',
        #                                 command=self.save_and_close, bg='green', font='Verdana 10 bold', fg='yellow')
        # self.close_and_save.place(x=start_x + dx * 10, y=10)


        tk.Button(self._frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10')\
            .place(x=start_x+dx*10,y=10)

        # Selection of constraints
        self._new_check_sec_mod = tk.BooleanVar()
        self._new_check_min_pl_thk = tk.BooleanVar()
        self._new_check_shear_area = tk.BooleanVar()
        self._new_check_buckling = tk.BooleanVar()
        self._new_check_fatigue = tk.BooleanVar()
        self._new_check_slamming = tk.BooleanVar()
        self._new_check_local_buckling = tk.BooleanVar()
        self._new_check_sec_mod.set(True)
        self._new_check_min_pl_thk.set(True)
        self._new_check_shear_area.set(True)
        self._new_check_buckling.set(True)
        self._new_check_fatigue.set(True)
        self._new_check_slamming.set(True)
        self._new_check_local_buckling.set(True)


        start_y, start_x, dy  = 570, 100, 25
        tk.Label(self._frame,text='Check for minimum section modulus').place(x=start_x+dx*9.7,y=start_y+4*dy)
        tk.Label(self._frame, text='Check for minimum plate thk.').place(x=start_x+dx*9.7,y=start_y+5*dy)
        tk.Label(self._frame, text='Check for minimum shear area').place(x=start_x+dx*9.7,y=start_y+6*dy)
        tk.Label(self._frame, text='Check for buckling (RP-C201)').place(x=start_x+dx*9.7,y=start_y+7*dy)
        tk.Label(self._frame, text='Check for fatigue (RP-C203)').place(x=start_x + dx * 9.7, y=start_y + 8 * dy)
        tk.Label(self._frame, text='Check for bow slamming').place(x=start_x + dx * 9.7, y=start_y + 9 * dy)
        tk.Label(self._frame, text='Check for local stf. buckling').place(x=start_x + dx * 9.7, y=start_y + 10 * dy)

        tk.Label(self._frame, text='Frame (girder data) for weight calculation:', font = 'Verdana 9 bold')\
            .place(x=start_x + dx * 13,
                                                                                       y=start_y + 4 * dy)
        tk.Label(self._frame, text='Girder thickness').place(x=start_x + dx * 13, y=start_y + 5 * dy)
        tk.Label(self._frame, text='Stiffener height').place(x=start_x + dx * 13, y=start_y + 6 * dy)
        tk.Label(self._frame, text='Stiffener thickness').place(x=start_x + dx * 13, y=start_y + 7 * dy)
        tk.Label(self._frame, text='Stf. flange width').place(x=start_x + dx * 13, y=start_y + 8 * dy)
        tk.Label(self._frame, text='Stf. flange thickenss').place(x=start_x + dx * 13, y=start_y + 9 * dy)
        tk.Label(self._frame, text='For weight calculation of girder: Max span mult / Min span mult')\
            .place(x=start_x + dx * 13,y=start_y + 10 * dy)
        tk.Label(self._frame, text='Maximum span / Minimum span ->')\
            .place(x=start_x + dx * 13,y=start_y + 12 * dy)

        self._ent_opt_girder_thk.place(x=start_x + dx * 15, y=start_y + 5 * dy)
        self._ent_opt_girder_stf_web_h.place(x=start_x + dx * 15, y=start_y + 6 * dy)
        self._ent_opt_girder_stf_web_thk.place(x=start_x + dx * 15, y=start_y + 7 * dy)
        self._ent_opt_girder_stf_fl_b.place(x=start_x + dx * 15, y=start_y + 8 * dy)
        self._ent_opt_girder_stf_fl_thk.place(x=start_x + dx * 15, y=start_y + 9 * dy)
        self._ent_opt_girder_scale_high.place(x=start_x + dx * 15, y=start_y + 11 * dy)
        self._ent_opt_girder_scale_low.place(x=start_x + dx * 15.5, y=start_y + 11 * dy)
        self._ent_opt_max_span.place(x=start_x + dx * 15, y=start_y + 12 * dy)
        self._ent_opt_min_span.place(x=start_x + dx * 15.5, y=start_y + 12 * dy)

        tk.Checkbutton(self._frame,variable=self._new_check_sec_mod).place(x=start_x+dx*12,y=start_y+4*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_min_pl_thk).place(x=start_x+dx*12,y=start_y+5*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_shear_area).place(x=start_x+dx*12,y=start_y+6*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_buckling).place(x=start_x+dx*12,y=start_y+7*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_fatigue).place(x=start_x + dx * 12, y=start_y + 8 * dy)
        tk.Checkbutton(self._frame, variable=self._new_check_slamming).place(x=start_x + dx * 12, y=start_y + 9 * dy)
        tk.Checkbutton(self._frame, variable=self._new_check_local_buckling).place(x=start_x + dx * 12,
                                                                                   y=start_y + 10 * dy)


        self._toggle_btn = tk.Button(self._frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg = 'salmon')
        self._toggle_btn.place(x=start_x+dx*10.5, y=start_y - dy * 16.8)
        self._toggle_object, self._filez = None, None

        # ----------------------------------END OF OPTIMIZE SINGLE COPY-----------------------------------------------
        self.progress_count = tk.IntVar()
        self.progress_count.set(0)
        self.progress_bar = Progressbar(self._frame, orient="horizontal",length=200, mode="determinate",
                                        variable=self.progress_count)
        #self.progress_bar.place(x=start_x+dx*10.5,y=start_y-dy*16.5)

        self._active_lines = []
        self.controls()
        self.draw_select_canvas()
        # if __name__ == '__main__':
        #     self.run_optimizaion(load_pre = True, save_results=True)



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

            self._lb_swarm_size.place(x=start_x + dx * 11, y=start_y - 1 * dy)
            self._lb_omega.place(x=start_x + dx * 11, y=start_y - 0 * dy)
            self._lb_phip.place(x=start_x + dx * 11, y=start_y + 1 * dy)
            self._lb_phig.place(x=start_x + dx * 11, y=start_y + 2 * dy)

            self._lb_maxiter.place(x=start_x + dx * 14, y=start_y - 1 * dy)
            self._lb_minstep.place(x=start_x + dx * 14, y=start_y + 0 * dy)
            self._lb_minfunc.place(x=start_x + dx * 14, y=start_y + 1 * dy)

            self._ent_swarm_size.place(x=start_x + dx * 12, y=start_y - 1 * dy)
            self._ent_omega.place(x=start_x + dx * 12, y=start_y - 0 * dy)
            self._ent_phip.place(x=start_x + dx * 12, y=start_y + 1 * dy)
            self._ent_phig.place(x=start_x + dx * 12, y=start_y + 2 * dy)

            self._ent_maxiter.place(x=start_x + dx * 15, y=start_y - 1 * dy)
            self._ent_minstep.place(x=start_x + dx * 15, y=start_y + 0 * dy)
            self._ent_minfunc.place(x=start_x + dx * 15, y=start_y + 1 * dy)

    def run_optimizaion(self, load_pre = False, save_results = True):
        '''
        Function when pressing the optimization botton inside this window.
        :return:
        '''
        frames, distances = self.opt_create_frames(self.opt_get_fractions())
        self.opt_create_main_structure(frames,
                                       self._active_points[0], self._active_points[1],
                                       self._active_points[2], self._active_points[3])

        contraints = (self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
                      self._new_check_shear_area.get(), self._new_check_buckling.get(),
                      self._new_check_fatigue.get(), self._new_check_slamming.get(),
                      self._new_check_local_buckling.get())

        self.pso_parameters = (self._new_swarm_size.get(), self._new_omega.get(), self._new_phip.get(),
                               self._new_phig.get(),self._new_maxiter.get(), self._new_minstep.get(),
                               self._new_minfunc.get())

        opt_girder_prop = (self._new_opt_girder_thk.get(), self._new_opt_girder_stf_web_h.get(),
                           self._new_opt_girder_stf_web_thk.get(), self._new_opt_girder_stf_flange_b.get(),
                           self._new_opt_girder_stf_flange_thk.get(),self._new_opt_girder_scale_high.get(),
                           self._new_opt_girder_scale_low.get())
        min_max_span = (self._new_opt_span_min.get(), self._new_opt_span_max.get())


        init_objects, fatigue_objects, fat_press_ext_int, slamming_pressures, lateral_press, fatigue_objects, \
        slamming_press = [list() for dummy in range(7)]

        broke = False
        for line,coord in self._opt_structure.items():
            if self.opt_create_struc_obj(self._opt_structure[line]) is None:
                broke = True
                break
            else:
                init_objects.append(self.opt_create_struc_obj(self._opt_structure[line])[0])
                fat_obj_single = self.opt_create_struc_obj(self._opt_structure[line])[2]
                fatigue_objects.append(fat_obj_single)

            if __name__ == '__main__':
                import ANYstructure.example_data as ex
                lateral_press.append(200)  # for testing
                slamming_press.append(0)
                fatigue_objects.append(ex.get_fatigue_object())
                for pressure in ex.get_geo_opt_fat_press():
                    fat_press_ext_int.append(((pressure['p_ext']['loaded'], pressure['p_ext']['ballast'],
                                               pressure['p_ext']['part']),
                                              (pressure['p_int']['loaded'], pressure['p_int']['ballast'],
                                               pressure['p_int']['part'])))

            else:
                p1, p2 = self._opt_structure[line]
                closet_line = self.opt_find_closest_orig_line([(p2[0]-p1[0])*0.5, (p2[1]-p1[1])*0.5])
                gotten_lat_press = self.app.get_highest_pressure(closet_line)
                lateral_press.append(gotten_lat_press['normal'] / 1000)
                slamming_press.append(gotten_lat_press['slamming'])
                try:
                    fat_press_single = self.app.get_fatigue_pressures(line, fat_obj_single.get_accelerations())
                    fat_press_tuple = ((fat_press_single['p_ext']['loaded'], fat_press_single['p_ext']['ballast'],
                                        fat_press_single['p_ext']['part']),
                                       (fat_press_single['p_int']['loaded'], fat_press_single['p_int']['ballast'],
                                        fat_press_single['p_int']['part']))
                    fat_press_ext_int.append(fat_press_tuple)
                except AttributeError:
                    fat_press_ext_int.append(None)
        if broke:
            messagebox.showinfo(title='Selection error.',
                                message='This field cannot be subdivided or there are no loads. Error.')
            return None

        # found_files = self._filez
        # if self._toggle_btn.config('relief')[-1] == 'sunken':
        #     found_files, predefined_stiffener_iter = self.toggle(found_files=found_files, iterating=True)
        # else:
        #     predefined_stiffener_iter = None

        

        if not load_pre:

            geo_results = op.run_optmizataion(initial_structure_obj=init_objects,min_var=self.get_lower_bounds(),
                                              max_var=self.get_upper_bounds(),lateral_pressure=lateral_press,
                                              deltas=self.get_deltas(), algorithm='anysmart',side='p',
                                              const_chk = contraints,pso_options = self.pso_parameters,
                                              is_geometric=True,fatigue_obj= fatigue_objects,
                                              fat_press_ext_int=fat_press_ext_int,
                                              min_max_span=min_max_span, tot_len=self.opt_get_length(),
                                              frame_height=self.opt_get_distance(), frame_distance = distances,
                                              predefined_stiffener_iter=self._filez,
                                              processes = self._new_processes.get(),
                                              slamming_press=slamming_press, opt_girder_prop=opt_girder_prop)

            self._geo_results = geo_results

            #SAVING RESULTS
            if save_results:
                with open('geo_opt_2.pickle', 'wb') as file:
                    pickle.dump(geo_results, file)
        else:
            with open('geo_opt_2.pickle', 'rb') as file:
                self._geo_results = pickle.load(file)



        save_file, filename = None, None
        if save_results:
            save_file = filedialog.asksaveasfile(mode="w", defaultextension=".txt", title = 'Save results to file')
            if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
                filename = None
            else:
                filename = save_file.name

        save_file = self.draw_result_text(self._geo_results, save_to_file=filename)
        self.draw_select_canvas(opt_results=self._geo_results, save_file = save_file)


    def opt_get_fractions(self):
        ''' Finding initial number of fractions '''
        init_fractions = 0
        # finding number of fractions
        for dummy_i in range(1, 100):
            if 3.8 < self.opt_get_length() / dummy_i < 4.2:
                init_fractions = dummy_i
                break
        to_return = []
        for dummy_i in range(init_fractions):
            to_return.append(1/init_fractions)

        return to_return

    def opt_create_struc_obj(self,opt_line):
        ''' Creating preliminary stucture object from selected optimized line. 
        The properties of the new line oto be optimized is taken from the closest original line.'''

        pt1 = opt_line[0]
        pt2 = opt_line[1]

        vector = [pt2[0] - pt1[0], pt2[1] - pt1[1]]
        point = [pt1[0]+vector[0]*0.5, pt1[1]+vector[1]*0.5]
        if self.opt_find_closest_orig_line(point) == None:
            return None
        objects = [copy.deepcopy(x) if x != None else None for x in
                   self._line_to_struc[self.opt_find_closest_orig_line(point)]]

        objects[0].set_span(dist(pt1,pt2))

        return objects

    def opt_find_closest_orig_line(self,coord):
        ''' Find the closest original line to the optimized line.
            Used to create initial structure objects. '''

        for key,value in self._line_dict.items():

            pt1 = list(self._point_dict['point'+str(value[0])])
            pt2 = list(self._point_dict['point'+str(value[1])])
            distance = dist(pt2,pt1)
            vector = [pt2[0]-pt1[0],pt2[1]-pt1[1]]
            current = list(self._point_dict['point'+str(value[0])])
            for dummy_i in range(1000):
                delta = distance/1000
                current[0] += (vector[0]/distance) * delta
                current[1] += (vector[1]/distance) * delta
                if dist(coord,current) <= 0.1:
                    if self._line_to_struc[key][0].get_structure_type() not in ('GENERAL_INTERNAL_NONWT', 'FRAME'):
                        return key
                    else:
                        return None

    def opt_get_distance(self):
        ''' Getting the largest disctance between the two lines to be optimized. '''
        if len(self._active_points) == 4:
            return dist(self._point_dict[self._active_points[0]],self._point_dict[self._active_points[2]])
        else:
            return None

    def opt_get_length(self):
        ''' Getting the length of the lines to be optimized. '''
        if len(self._active_points)==4:
            return dist(self._point_dict[self._active_points[0]],self._point_dict[self._active_points[1]])

    def opt_get_fraction_bounds(self, max_len = 6, min_len = 2):
        ''' Return the fraction bounds(basis upper/lower) to be considered. '''
        return int(self.opt_get_length()/max_len), int(self.opt_get_length()/min_len)

    def opt_create_frames(self,fractions):
        ''' Creating frames between the the two lines to be optimized. '''
        count = 1

        self._opt_frames['opt_frame_start'] = [[self._point_dict[self._active_points[0]][0],
                                                self._point_dict[self._active_points[0]][1]],
                                               [self._point_dict[self._active_points[2]][0],
                                                self._point_dict[self._active_points[2]][1]]]

        self._opt_frames['opt_frame_stop'] = [[self._point_dict[self._active_points[1]][0],
                                               self._point_dict[self._active_points[1]][1]],
                                              [self._point_dict[self._active_points[3]][0],
                                               self._point_dict[self._active_points[3]][1]]]

        start =  0
        for fraction in fractions:
            start += fraction
            if start != 1:
                self._opt_frames['opt_frame'+str(count)] = [[self._point_dict[self._active_points[0]][0] +
                                                             round(self.opt_get_length()*start,5),
                                                             self._point_dict[self._active_points[0]][1]],
                                                            [self._point_dict[self._active_points[2]][0] +
                                                             round(self.opt_get_length() * start,5),
                                                             self._point_dict[self._active_points[2]][1]]]
            count+=1
        distances = {'start_dist': dist(self._opt_frames['opt_frame_start'][0], self._opt_frames['opt_frame_start'][1]),
                     'stop_dist': dist(self._opt_frames['opt_frame_stop'][0], self._opt_frames['opt_frame_stop'][1])}

        return self._opt_frames, distances

    def opt_create_main_structure(self,frames,start1,stop1,start2,stop2):
        ''' This creates line definition for the new structure objects.
         The scipt searches the line to find frames.'''
        line1_coord = self._point_dict[start1],self._point_dict[stop1]
        line2_coord = self._point_dict[start2],self._point_dict[stop2]

        structure = {}


        p1_low,p1_high = list(line1_coord[0]),list(line2_coord[0])
        p2_low,p2_high = list(line1_coord[1]),list(line2_coord[1])
        vector_low,vector_high = [p2_low[0]-p1_low[0],p2_low[1]-p1_low[1]],[p2_high[0]-p1_high[0],p2_high[1]-p1_high[1]]

        # Starting search on the lower or inner line
        count = 1
        tmp_struc = [p1_low] # starting point defined.
        found = None
        for frame, coords in frames.items():
            current = list(p1_low)
            if frame!='opt_frame_start' and frame!='opt_frame_stop':
                for jump in range(100):
                    current[0] += vector_low[0] / 100
                    current[1] += vector_low[1] / 100
                    if dist(current,coords[0]) < 0.1 and frame != found:
                        found = frame
                        tmp_struc.append(coords[0])
                        self._opt_structure['opt_struc'+str(count)] = tmp_struc # adding found line
                        tmp_struc = [coords[0]]
                        count += 1
        tmp_struc.append(p2_low)
        self._opt_structure['opt_struc'+str(count)] = tmp_struc # adding found line (end)
        count += 1

        # Starting search of upper or outer line.
        tmp_struc = [p1_high] # starting point defined.
        found = None
        for frame, coords in frames.items():
            current = list(p1_high)
            if frame!='opt_frame_start' and frame!='opt_frame_stop':
                for jump in range(100):
                    current[0] += vector_high[0] / 100
                    current[1] += vector_high[1] / 100
                    if dist(current,coords[1]) < 0.1 and frame != found:
                        found = frame
                        tmp_struc.append(coords[1])

                        self._opt_structure['opt_struc'+str(count)] = tmp_struc # adding found line
                        tmp_struc = [coords[1]]
                        count += 1
        tmp_struc.append(p2_high)
        self._opt_structure['opt_struc'+str(count)] = tmp_struc # adding found line (end)

        return self._opt_structure

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
                    max((self._new_pl_thk_upper.get() - self._new_pl_thk_lower.get()) / self._new_delta_pl_thk.get(),
                        1) * \
                    max((self._new_web_h_upper.get() - self._new_web_h_lower.get()) / self._new_delta_web_h.get(), 1) * \
                    max((self._new_web_thk_upper.get() - self._new_web_thk_lower.get()) / self._new_delta_web_thk.get(),
                        1) * \
                    max((self._new_fl_w_upper.get() - self._new_fl_w_lower.get()) / self._new_delta_fl_w.get(), 1) * \
                    max((self._new_fl_thk_upper.get() - self._new_fl_thk_lower.get()) / self._new_delta_fl_thk.get(), 1)
                return int(number_of_combinations * self.running_time_per_item) * len(self._active_lines)
            except TclError:
                return 0
        else:
            try:
                return int(self._new_algorithm_random_trials.get() * self.running_time_per_item) * len(
                    self._active_lines)
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

    def get_upper_bounds(self):
        '''
        Return an numpy array of upper bounds.
        :return:
        '''
        return np.array([self._new_spacing_upper.get() / 1000, self._new_pl_thk_upper.get() / 1000,
                         self._new_web_h_upper.get() / 1000, self._new_web_thk_upper.get() / 1000,
                         self._new_fl_w_upper.get() / 1000, self._new_fl_thk_upper.get() / 1000,
                         6, 10])

    def get_lower_bounds(self):
        '''
        Return an numpy array of lower bounds.
        :return:
        '''
        return np.array([self._new_spacing_lower.get() / 1000, self._new_pl_thk_lower.get() / 1000,
                         self._new_web_h_lower.get() / 1000, self._new_web_thk_lower.get() / 1000,
                         self._new_fl_w_lower.get() / 1000, self._new_fl_thk_lower.get() / 1000,
                         1, 10])

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

    def draw_properties(self, init_obj=None, opt_obj=None, line=None):
        '''
        Drawing properties in the canvas.
        :return:
        '''
        ctr_x = self._prop_canvas_dim[0] / 2
        ctr_y = self._prop_canvas_dim[1] / 2 + 200
        opt_color, opt_stippe = 'red', 'gray12'
        m = self._draw_scale

        if init_obj != None:
            self._canvas_opt.delete('all')
            self.checkered(10)
            init_color, init_stipple = 'blue', 'gray12'

            self._canvas_opt.create_rectangle(0, 0, self._prop_canvas_dim[0] + 10, 80, fill='white')
            self._canvas_opt.create_line(10, 10, 30, 10, fill=init_color, width=5)
            self._canvas_opt.create_text(270, 10, text='Initial    - Pl.: ' + str(init_obj.get_s() * 1000) + 'x' + str(
                init_obj.get_pl_thk() * 1000) +
                                                       ' Stf.: ' + str(init_obj.get_web_h() * 1000) + 'x' + str(
                init_obj.get_web_thk() * 1000) + '+' +
                                                       str(init_obj.get_fl_w() * 1000) + 'x' + str(
                init_obj.get_fl_thk() * 1000),
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
                                              ctr_x + m * init_obj.get_web_thk() / 2,
                                              ctr_y - m * (init_obj.get_web_h() + init_obj.get_pl_thk())
                                              , fill=init_color, stipple=init_stipple)
            if init_obj.get_stiffener_type() != 'L':
                self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_fl_w() / 2,
                                                  ctr_y - m * (init_obj.get_pl_thk() + init_obj.get_web_h()),
                                                  ctr_x + m * init_obj.get_fl_w() / 2,
                                                  ctr_y - m * (
                                                  init_obj.get_pl_thk() + init_obj.get_web_h() + init_obj.get_fl_thk()),
                                                  fill=init_color, stipple=init_stipple)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_web_thk() / 2,
                                                  ctr_y - m * (init_obj.get_pl_thk() + init_obj.get_web_h()),
                                                  ctr_x + m * init_obj.get_fl_w(),
                                                  ctr_y - m * (
                                                  init_obj.get_pl_thk() + init_obj.get_web_h() + init_obj.get_fl_thk()),
                                                  fill=init_color, stipple=init_stipple)

        if opt_obj != None:
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
        else:
            self._canvas_opt.create_text(150, 60, text='No optimized solution found.')

        if line != None:
            if __name__ == '__main__':
                lateral_press = 200  # for testing
            else:
                lateral_press = self.app.get_highest_pressure(line)['normal'] / 1000
            self._canvas_opt.create_text(250, self._prop_canvas_dim[1] - 10,
                                         text='Lateral pressure: ' + str(lateral_press) + ' kPa',
                                         font='Verdana 10 bold', fill='red')

    def draw_select_canvas(self, load_selected=False, opt_results = None, save_file = None):
        '''
        Making the lines canvas.
        :return:
        '''
        self._canvas_select.delete('all')
        text_type = 'Verdana 8'
        if opt_results is None:
            # stippled lines and text.

            self._canvas_select.create_line(self._canvas_origo[0], 0, self._canvas_origo[0], self._select_canvas_dim[1],
                                            stipple='gray50')
            self._canvas_select.create_line(0, self._canvas_origo[1], self._select_canvas_dim[0], self._canvas_origo[1],
                                            stipple='gray50')
            self._canvas_select.create_text(self._canvas_origo[0] - 30,
                                            self._canvas_origo[1] + 20, text='(0,0)',
                                            font='Text 10')
            self._canvas_select.create_text([700, 50],
                                            text='How to:\n'
                                                 'For a double bottom structure: \n'
                                                 'Click start point 1 -> click en point 1 (for example bottom plate)\n'
                                                 'Click start point 2 -> click en point 2 (for example inner bottom\n'
                                                 'Run optimization! Wait for the results...... wait.... wait....\n',
                                            font='Verdana 8 bold',
                                            fill='red')
            # drawing the line dictionary.
            if len(self._line_dict) != 0:
                for line, value in self._line_dict.items():
                    color = 'black'
                    coord1 = self.get_point_canvas_coord('point' + str(value[0]))
                    coord2 = self.get_point_canvas_coord('point' + str(value[1]))
                    vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                    # drawing a bold line if it is selected
                    if self._line_to_struc[line][0].get_structure_type() not in ('GENERAL_INTERNAL_NONWT','FRAME'):

                        if line in self._active_lines:
                            self._canvas_select.create_line(coord1, coord2, width=6, fill=color,stipple='gray50')
                            self._canvas_select.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 + 10,
                                                            text='Line ' + str(get_num(line)), font='Verdand 10 bold',
                                                            fill='red')
                        else:
                            self._canvas_select.create_line(coord1, coord2, width=3, fill=color,stipple='gray25')
                            self._canvas_select.create_text(coord1[0] - 20 + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 +

                                                            10,text='line' + str(get_num(line)),font="Text 8", fill='black')

                if len(self._opt_frames) != 0:
                    for key,value in self._opt_frames.items():
                        coord1 = self.get_canvas_coord(value[0])
                        coord2 = self.get_canvas_coord(value[1])
                        vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                        self._canvas_select.create_line(coord1, coord2, width=3, fill='SkyBlue1')
                else:
                    pass

            if len(self._active_points)>1:
                color = 'blue'
                coord1 = self.get_point_canvas_coord(self._active_points[0])
                coord2 = self.get_point_canvas_coord(self._active_points[1])
                vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                # drawing a bold line if it is selected
                self._canvas_select.create_line(coord1, coord2, width=6, fill=color)
                if len(self._active_points) > 3:
                    coord1 = self.get_point_canvas_coord(self._active_points[2])
                    coord2 = self.get_point_canvas_coord(self._active_points[3])
                    vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                    self._canvas_select.create_line(coord1, coord2, width=6, fill=color)

            # drawing the point dictionary

            for key,value in self._point_dict.items():
                pt_size = 6
                if key in self._active_points:
                    self._canvas_select.create_oval(self.get_point_canvas_coord(key)[0] - pt_size + 2,
                                                  self.get_point_canvas_coord(key)[1] - pt_size + 2,
                                                  self.get_point_canvas_coord(key)[0] + pt_size + 2,
                                                  self.get_point_canvas_coord(key)[1] + pt_size + 2, fill='blue')
                    if self._active_points.index(key) == 0:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14, text='START 1',
                                                        font=text_type, fill = 'blue')
                    elif self._active_points.index(key) == 1:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14,
                                                        text='STOP 1',font=text_type, fill='blue')
                    elif self._active_points.index(key) == 2:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14,
                                                        text='START 2',font=text_type, fill='blue')
                    elif self._active_points.index(key) == 3:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14,
                                                        text='STOP 2',font=text_type, fill='blue')
                    else:
                        pass
                else:
                    self._canvas_select.create_oval(self.get_point_canvas_coord(key)[0] - pt_size,
                                                  self.get_point_canvas_coord(key)[1] - pt_size,
                                                  self.get_point_canvas_coord(key)[0] + pt_size,
                                                  self.get_point_canvas_coord(key)[1] + pt_size, fill='red')

                    self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                    self.get_point_canvas_coord(key)[1] - 14, text='pt.'+str(get_num(key)),
                                                    font='Verdana 8', fill='blue')
        else:
            self._canvas_select.create_text([20, 20], text='Results are presented here. '
                                                           'All results may not fit the screen. '
                                                           'All results are seen in your saved result file.',
                                            font='Verdana 12 bold',
                                            fill='red', anchor = 'w')

            delta, start_x, y_loc = 20, 10, 40

            if save_file is not None:
                save_file.write('\n' + 'Stiffener properties:')

            for key, values in opt_results.items():
                # if y_loc > 700:
                #     start_x = 400
                #     y_loc = 40

                y_loc = y_loc + delta

                check_ok = [val[3] is True for val in opt_results[key][1]]

                if save_file is not None:
                    save_file.write('\n' + str(len(check_ok))+'\n')
                self._canvas_select.create_text([start_x + delta, y_loc],
                                                text=str(len(check_ok))+' panels with weight '+ str(round(values[0],1)),
                                                anchor='w', font=text_type)
                y_loc += delta
                item_count, endstring = 0, ''

                for data_idx, data in enumerate(values[1]):
                    for idx, stuc_info in enumerate(data):
                        if type(stuc_info) == ANYstructure.calc_structure.Structure:
                            if y_loc > 700:
                                y_loc = 120
                                start_x += 350
                            if item_count == 0:
                                endstring = ' START 1'+' OK!\n' if values[1][data_idx][3] else ' START 1'+' NOT OK!\n'
                            elif item_count > 0 and item_count < len(values[1]) / 2-1 and len(values[1]) != 4:
                                endstring = ' -------'+' OK!\n' if values[1][data_idx][3] else ' -------'+' NOT OK!\n'
                            elif item_count == len(values[1])/2-1:
                                endstring = ' -END 1-'+' OK!\n' if values[1][data_idx][3] else ' -END 1-'+' NOT OK!\n'
                            elif item_count == len(values[1])/2:
                                endstring = ' START 2'+' OK!\n' if values[1][data_idx][3] else ' START 2'+' NOT OK!\n'
                            elif item_count > len(values[1])/2 and item_count < len(values[1])-1:
                                endstring = ' -------'+' OK!\n' if values[1][data_idx][3] else ' -------'+' NOT OK!\n'
                            elif item_count == len(values[1])-1:
                                endstring = ' -END 2-'+' OK!\n' if values[1][data_idx][3] else ' -END 2-'+' NOT OK!\n'
                            self._canvas_select.create_text([start_x + delta, y_loc],
                                                            text=stuc_info.get_one_line_string()+endstring,
                                                            anchor='w', font=text_type)
                            y_loc += 15

                            if save_file is not None:
                                save_file.write(stuc_info.get_one_line_string()+stuc_info.get_extended_string() + ' | '+
                                                stuc_info.get_report_stresses()+ endstring)
                            item_count += 1
            if save_file is not None:
                save_file.write('\n -------------  END  ---------------')
                save_file.close()

    def draw_result_text(self, geo_opt_obj, save_to_file = None):
        ''' Textual version of the results. '''

        self._canvas_opt.delete('all')
        start_x = 20
        delta = 25
        start_y = 60
        y_loc = delta + start_y

        self._canvas_opt.create_text([start_x, 40],
                                     text='Results seen next. Weight index is tot_weight / max_weight \n'
                                          'max_weight is the highest total weight of the checked variations.\n'
                                          'Weight index of 1 is the heaviest calculated variation.',
                                     font='Verdana 10', fill='Blue', anchor='w')

        self._canvas_opt.create_text([start_x, y_loc],
                                     text='| Plate fields | Fields length | Weight index | All OK? |',
                                     font='Verdana 10 bold', fill='red', anchor = 'w')
        y_loc += delta / 2
        self._canvas_opt.create_text([start_x, y_loc],
                                     text='************************************************', anchor='w',
                                     font='Verdana 10 bold')
        text_type = 'Verdana 10 bold'
        weights = [self._geo_results[key][0] for key in self._geo_results.keys()]

        max_weight = 0
        for weight in weights:
            if weight != float('inf'):
                max_weight = weight if weight > max_weight else max_weight



        if save_to_file is not None:
            save_file = open(save_to_file, 'w')
            save_file.write('| Plate fields | Fields length | Weight index | All OK? |\n')
            save_file.write('*********************************************************\n')

        for key, value in self._geo_results.items():
            y_loc = y_loc + delta
            check_ok = [val[3] is True for val in self._geo_results[key][1]]

            self._canvas_opt.create_text([start_x + 20, y_loc ], text=str(len(check_ok)),
                                         anchor='w', font=text_type)

            self._canvas_opt.create_text([start_x + 120, y_loc ], text=str('No results\n' if
                                                                           self._geo_results[key][1][0][0] is None else
                                                                           round(self._geo_results[key][1][0][0].get_span(),4)),
                                         anchor='w', font=text_type)
            self._canvas_opt.create_text([start_x + 220, y_loc ],
                                         text=str(round(self._geo_results[key][0] / max_weight, 3))
                                         if max_weight != 0 else '',
                                         anchor='w', font=text_type)
            self._canvas_opt.create_text([start_x + 330, y_loc ], text=str(all(check_ok)),
                                         anchor='w', font=text_type)

            if save_to_file is not None:
                save_file.write(str(len(check_ok))+ ' ' + 'No results\n' if self._geo_results[key][1][0][0] is None
                                                             else str(round(self._geo_results[key][1][0][0].get_span(),
                                                                            4)) + ' ' +
                                                                  str(round(self._geo_results[key][0] / max_weight, 3))
                                                                  + '\n' if max_weight != 0 else
                '' + ' ' + str(all(check_ok))+'\n')

        if save_to_file:
            return save_file


    def algorithm_info(self):
        ''' When button is clicked, info is displayed.'''

        messagebox.showinfo(title='Algorith information',
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
                                         type='okcancel')
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
        point_coord_x = self._canvas_origo[0] + self._point_dict[point_no][0] * self._canvas_scale
        point_coord_y = self._canvas_origo[1] - self._point_dict[point_no][1] * self._canvas_scale

        return [point_coord_x, point_coord_y]

    def get_canvas_coord(self, coord):
        '''
        Returning the canvas coordinates of the point. This value will change with slider.
        :param point_no:
        :return:
        '''
        point_coord_x = self._canvas_origo[0] + coord[0] * self._canvas_scale
        point_coord_y = self._canvas_origo[1] - coord[1] * self._canvas_scale

        return [point_coord_x, point_coord_y]

    def controls(self):
        '''
        Specifying the controls to be used.
        :return:
        '''
        self._canvas_select.bind('<Button-1>', self.button_1_click)
        self._canvas_select.bind('<Button-2>', self.button_2_click)
        self._canvas_select.bind('<Button-3>', self.button_3_click)

        self._frame.bind('<Shift_L>', self.shift_pressed)
        self._frame.bind('<Shift_R>', self.shift_pressed)
        self._frame.bind('<Control_L>', self.ctrl_pressed)
        self._frame.bind('<Control_R>', self.ctrl_pressed)

    def shift_pressed(self, event=None):
        '''
        Event is executed when shift key pressed.
        :return:
        '''
        self._add_to_lines = True

    def ctrl_pressed(self, event=None):
        '''
        Event when control is pressed.
        :param event:
        :return:
        '''
        self._add_to_lines = False

    def button_1_click(self, event):
        '''
        When clicking the right button, this method is called.
        method is referenced in
        '''
        if type(self._geo_results) is not list():
            if self._geo_results is not None:
                return
        else:
            if self._geo_results[0] is not None:
                return
        click_x = self._canvas_select.winfo_pointerx() - self._canvas_select.winfo_rootx()
        click_y = self._canvas_select.winfo_pointery() - self._canvas_select.winfo_rooty()

        self._point_is_active = False
        margin = 10
        self._active_point = ''
        for point, coords in self._point_dict.items():
            point_coord = self.get_point_canvas_coord(point)
            if point_coord[0]-margin < click_x < point_coord[0]+margin and\
                point_coord[1]-margin < click_y < point_coord[1]+margin:
                self._active_point = point
                self._point_is_active = True
                if len(self._active_points)<4:
                    self._active_points.append(self._active_point)

        if len(self._active_points)==4:
            self.opt_create_frames(self.opt_get_fractions())

        self.draw_select_canvas()

    def button_3_click(self, event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
        self._active_lines = []
        self._active_points = []
        self.draw_select_canvas()

    def button_2_click(self, event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
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
                        if key in self._opt_resutls.keys() and self._opt_resutls[key] != None:
                            self.draw_properties(init_obj=self._line_to_struc[key][0],
                                                opt_obj=self._opt_resutls[key][0],
                                                 line=key)
                        else:
                            self.draw_properties(init_obj=self._line_to_struc[key][0], line=key)
                        break
                self.draw_select_canvas()
        self.draw_select_canvas()
        self.update_running_time()

        #############################
        self.opt_create_main_structure(self.opt_create_frames(self.opt_get_fractions())[0],self._active_points[0],
                                       self._active_points[1],self._active_points[2],self._active_points[3])

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
                to_return[line] = self._opt_resutls[line]
            self.app.on_close_opt_multiple_window(to_return)
            messagebox.showinfo(title='Return info', message='Returning: ' + str(self._active_lines))
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
        # if iterating:
        #     if found_files is not None:
        #         predefined_structure = hlp.helper_read_section_file(files=found_files, obj=obj)
        # else:
        predefined_structure = None
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg = 'salmon')
            self._ent_spacing_upper.config(bg = 'white')
            self._ent_spacing_lower.config(bg = 'white')
            self._ent_delta_spacing.config(bg = 'white')
            self._filez = None
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg='lightgreen')
            self._ent_spacing_upper.config(bg = 'lightgreen')
            self._ent_spacing_lower.config(bg = 'lightgreen')
            self._ent_delta_spacing.config(bg = 'lightgreen')
            self._filez = list(askopenfilenames(parent=self._frame, title='Choose files to open'))

        return found_files, predefined_structure

    def open_example_file(self):
        import os
        if os.path.isfile('sections.csv'):
            os.startfile('sections.csv')
        else:
            os.startfile(self._root_dir + '/' + 'sections.csv')

if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateOptGeoWindow(master=root)
    root.mainloop()
