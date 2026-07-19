# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError
import numpy as np
import time, os, datetime
from tkinter import messagebox
from tkinter import ttk
from tkinter.filedialog import askopenfilenames
from multiprocessing import cpu_count

try:
    from anystruct.calc_structure import CalcScantlings, AllStructure
    import anystruct.example_data as test
    import anystruct.example_data as ex
    import anystruct.helper as hlp
    import anystruct.line_structure as line_structure
    import anystruct.ml_models as ml_models
    import anystruct.optimize as op
except ModuleNotFoundError:
    from ANYstructure.anystruct.calc_structure import CalcScantlings, AllStructure
    import ANYstructure.anystruct.example_data as test
    import ANYstructure.anystruct.example_data as ex
    import ANYstructure.anystruct.helper as hlp
    import ANYstructure.anystruct.line_structure as line_structure
    import ANYstructure.anystruct.ml_models as ml_models
    import ANYstructure.anystruct.optimize as op


class CreateOptimizeWindow():
    '''
    This class initiates the single optimization window.
    '''

    def __init__(self, master, app=None):
        super(CreateOptimizeWindow, self).__init__()
        if __name__ == '__main__':
            Plate = CalcScantlings(ex.obj_dict)
            Stiffener = None  # CalcScantlings(ex.obj_dict)
            Girder = None  # CalcScantlings(ex.obj_dict_heavy)
            self._initial_calc_obj = AllStructure(Plate=Plate, Stiffener=Stiffener, Girder=Girder,
                                                  main_dict=ex.prescriptive_main_dict)

            # self._initial_calc_obj = test.get_structure_calc_object(heavy=True)
            self._lateral_pressure = 0.2
            self._fatigue_object = test.get_fatigue_object()
            self._fatigue_pressure = test.get_fatigue_pressures()
            self._slamming_pressure = test.get_slamming_pressure()
            self._root_dir = os.path.dirname(os.path.abspath(__file__))
            image_dir = self._root_dir + '\\images\\'
            self._initial_calc_obj.lat_press = self._lateral_pressure / 1000
            self._ML_buckling = ml_models.load_buckling_models((self._root_dir,))
            self._ML_classes = ml_models.default_ml_class_messages()
        else:
            self.app = app

            active_bundle = app._line_to_struc[app._active_line]
            self._initial_calc_obj = line_structure.structure(active_bundle)
            self._fatigue_object = line_structure.fatigue(active_bundle)
            try:
                self._fatigue_pressure = app.get_fatigue_pressures(app._active_line,
                                                                   self._fatigue_object.get_accelerations())
            except AttributeError:
                self._fatigue_pressure = None
            try:
                self._lateral_pressure = self.app.get_highest_pressure(self.app._active_line)['normal'] / 1e6
            except KeyError:
                self._lateral_pressure = 0
            try:

                if self.app.get_highest_pressure(self.app._active_line)['slamming'] is None:
                    self._slamming_pressure = 0
                else:
                    self._slamming_pressure = self.app.get_highest_pressure(self.app._active_line)['slamming']
            except KeyError:
                self._slamming_pressure = 0
            image_dir = app._root_dir + '\\images\\'
            self._root_dir = app._root_dir
            self._ML_buckling = app._ML_buckling

        self._predefined_stiffener_iter = None
        self._is_unstiffened_plate = self._initial_calc_obj.Stiffener is None
        self._has_girder = self._initial_calc_obj.Girder is not None

        self._frame = master
        if self._is_unstiffened_plate:
            window_title = "Optimize unstiffened plate"
        elif self._has_girder:
            window_title = "Optimize structure with girder"
        else:
            window_title = "Optimize structure"
        self._frame.wm_title(window_title)
        self._frame.geometry('1600x1000')
        self._frame.grab_set()

        self._opt_runned = False
        self._running_time_after_id = None
        self._opt_results = ()

        # Gridded layout scaffolding: header row, bounds table with the run
        # and algorithm controls to its right, then canvas/optimized values,
        # the stress inputs and the constraint checks column.
        self._frame.columnconfigure(1, weight=1)
        self._frame.rowconfigure(2, weight=1)
        self._header_frame = tk.Frame(self._frame)
        self._header_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(8, 4))
        self._bounds_frame = tk.Frame(self._frame)
        self._bounds_frame.grid(row=1, column=0, columnspan=2, sticky=tk.NW, padx=10)
        self._run_controls_frame = tk.Frame(self._frame)
        self._run_controls_frame.grid(row=1, column=2, sticky=tk.NW, padx=(10, 10))
        self._algo_params_frame = tk.Frame(self._run_controls_frame)
        self._objective_frame = tk.Frame(self._run_controls_frame)
        self._canvas_holder = tk.Frame(self._frame)
        self._canvas_holder.grid(row=2, column=0, sticky=tk.NW, padx=10, pady=(8, 8))
        self._stress_frame = tk.Frame(self._frame)
        self._stress_frame.grid(row=2, column=1, sticky=tk.NW, padx=(10, 10), pady=(8, 8))
        self._right_column = tk.Frame(self._frame)
        self._right_column.grid(row=2, column=2, sticky=tk.NW, padx=(10, 10), pady=(8, 8))
        self._girder_frame = tk.Frame(self._right_column)
        self._girder_frame.grid(row=0, column=0, sticky=tk.NW)
        self._checks_frame = tk.Frame(self._right_column)
        self._checks_frame.grid(row=1, column=0, sticky=tk.NW, pady=(8, 0))

        self._opt_actual_running_time = tk.Label(self._run_controls_frame, text='', font='Verdana 12 bold')

        self._draw_scale = 500
        self._canvas_dim = (500, 450)
        self._canvas_opt = tk.Canvas(self._canvas_holder, width=self._canvas_dim[0], height=self._canvas_dim[1],
                                     background='azure', relief='groove', borderwidth=2)
        self._canvas_opt.grid(row=0, column=0, sticky=tk.NW)
        self._opt_values_frame = tk.Frame(self._canvas_holder)
        self._opt_values_frame.grid(row=1, column=0, sticky=tk.NW, pady=(6, 0))

        algorithms = ('anysmart', 'scipy_de', 'random', 'random_no_delta', 'anydetail')

        tk.Label(self._header_frame, text='-- Structural optimizer --', font='Verdana 15 bold') \
            .grid(row=0, column=0, sticky=tk.W, padx=(0, 20))

        if self._initial_calc_obj.Stiffener is not None:
            self._spacing = self._initial_calc_obj.Plate.get_s()
            self._pl_thk = self._initial_calc_obj.Plate.get_pl_thk()
            self._stf_web_h = self._initial_calc_obj.Stiffener.get_web_h()
            self._stf_web_thk = self._initial_calc_obj.Stiffener.get_web_thk()
            self._fl_w = self._initial_calc_obj.Stiffener.get_fl_w()
            self._fl_thk = self._initial_calc_obj.Stiffener.get_fl_thk()
        else:
            self._spacing = self._initial_calc_obj.Plate.get_s()
            self._pl_thk = self._initial_calc_obj.Plate.get_pl_thk()
            self._stf_web_h = 0
            self._stf_web_thk = 0
            self._fl_w = 0
            self._fl_thk = 0

        if self._has_girder:
            self._girder_web_h = self._initial_calc_obj.Girder.get_web_h()
            self._girder_web_thk = self._initial_calc_obj.Girder.get_web_thk()
            self._girder_fl_w = self._initial_calc_obj.Girder.get_fl_w()
            self._girder_fl_thk = self._initial_calc_obj.Girder.get_fl_thk()
        else:
            self._girder_web_h = 0
            self._girder_web_thk = 0
            self._girder_fl_w = 0
            self._girder_fl_thk = 0

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
        self._new_girder_web_h_upper = tk.DoubleVar()
        self._new_girder_web_h_lower = tk.DoubleVar()
        self._new_girder_web_thk_upper = tk.DoubleVar()
        self._new_girder_web_thk_lower = tk.DoubleVar()
        self._new_girder_fl_w_upper = tk.DoubleVar()
        self._new_girder_fl_w_lower = tk.DoubleVar()
        self._new_girder_fl_thk_upper = tk.DoubleVar()
        self._new_girder_fl_thk_lower = tk.DoubleVar()
        self._new_span = tk.DoubleVar()
        self._new_width_lg = tk.DoubleVar()
        self._new_algorithm = tk.StringVar()
        self._new_algorithm_random_trials = tk.IntVar()
        self._new_swarm_size = tk.IntVar()
        self._new_omega = tk.DoubleVar()
        self._new_phip = tk.DoubleVar()
        self._new_phig = tk.DoubleVar()
        self._new_maxiter = tk.IntVar()
        self._new_minstep = tk.DoubleVar()
        self._new_minfunc = tk.DoubleVar()
        self._new_slamming_pressure = tk.DoubleVar()
        self._new_fatigue_int_press = tk.DoubleVar()
        self._new_fatigue_ext_press = tk.DoubleVar()

        ent_w = 10
        self._ent_spacing_upper = tk.Entry(self._bounds_frame, textvariable=self._new_spacing_upper, width=ent_w)
        self._ent_spacing_lower = tk.Entry(self._bounds_frame, textvariable=self._new_spacing_lower, width=ent_w)

        self._ent_pl_thk_upper = tk.Entry(self._bounds_frame, textvariable=self._new_pl_thk_upper, width=ent_w)
        self._ent_pl_thk_lower = tk.Entry(self._bounds_frame, textvariable=self._new_pl_thk_lower, width=ent_w)

        self._ent_web_h_upper = tk.Entry(self._bounds_frame, textvariable=self._new_web_h_upper, width=ent_w)
        self._ent_web_h_lower = tk.Entry(self._bounds_frame, textvariable=self._new_web_h_lower, width=ent_w)

        self._ent_web_thk_upper = tk.Entry(self._bounds_frame, textvariable=self._new_web_thk_upper, width=ent_w)
        self._ent_web_thk_lower = tk.Entry(self._bounds_frame, textvariable=self._new_web_thk_lower, width=ent_w)

        self._ent_fl_w_upper = tk.Entry(self._bounds_frame, textvariable=self._new_fl_w_upper, width=ent_w)
        self._ent_fl_w_lower = tk.Entry(self._bounds_frame, textvariable=self._new_fl_w_lower, width=ent_w)

        self._ent_fl_thk_upper = tk.Entry(self._bounds_frame, textvariable=self._new_fl_thk_upper, width=ent_w)
        self._ent_fl_thk_lower = tk.Entry(self._bounds_frame, textvariable=self._new_fl_thk_lower, width=ent_w)

        girder_ent_w = 8
        self._ent_girder_web_h_upper = tk.Entry(self._girder_frame, textvariable=self._new_girder_web_h_upper,
                                                width=girder_ent_w)
        self._ent_girder_web_h_lower = tk.Entry(self._girder_frame, textvariable=self._new_girder_web_h_lower,
                                                width=girder_ent_w)
        self._ent_girder_web_thk_upper = tk.Entry(self._girder_frame, textvariable=self._new_girder_web_thk_upper,
                                                  width=girder_ent_w)
        self._ent_girder_web_thk_lower = tk.Entry(self._girder_frame, textvariable=self._new_girder_web_thk_lower,
                                                  width=girder_ent_w)
        self._ent_girder_fl_w_upper = tk.Entry(self._girder_frame, textvariable=self._new_girder_fl_w_upper,
                                               width=girder_ent_w)
        self._ent_girder_fl_w_lower = tk.Entry(self._girder_frame, textvariable=self._new_girder_fl_w_lower,
                                               width=girder_ent_w)
        self._ent_girder_fl_thk_upper = tk.Entry(self._girder_frame, textvariable=self._new_girder_fl_thk_upper,
                                                 width=girder_ent_w)
        self._ent_girder_fl_thk_lower = tk.Entry(self._girder_frame, textvariable=self._new_girder_fl_thk_lower,
                                                 width=girder_ent_w)

        self._ent_span = tk.Entry(self._stress_frame, textvariable=self._new_span, width=ent_w)
        self._ent_width_lg = tk.Entry(self._stress_frame, textvariable=self._new_width_lg, width=ent_w)
        self._ent_slamming_pressure = tk.Entry(self._stress_frame, textvariable=self._new_slamming_pressure, width=ent_w)

        # additional choices for the random and pso algorithm
        self._ent_algorithm = tk.OptionMenu(self._run_controls_frame, self._new_algorithm, command=self.selected_algorithm,
                                            *algorithms)
        self._ent_random_trials = tk.Entry(self._algo_params_frame, textvariable=self._new_algorithm_random_trials)

        pso_width = 10
        self._ent_swarm_size = tk.Entry(self._algo_params_frame, textvariable=self._new_swarm_size, width=pso_width)
        self._ent_omega = tk.Entry(self._algo_params_frame, textvariable=self._new_omega, width=pso_width)
        self._ent_phip = tk.Entry(self._algo_params_frame, textvariable=self._new_phip, width=pso_width)
        self._ent_phig = tk.Entry(self._algo_params_frame, textvariable=self._new_phig, width=pso_width)
        self._ent_maxiter = tk.Entry(self._algo_params_frame, textvariable=self._new_maxiter, width=pso_width)
        self._ent_minstep = tk.Entry(self._algo_params_frame, textvariable=self._new_minstep, width=pso_width)
        self._ent_minfunc = tk.Entry(self._algo_params_frame, textvariable=self._new_minfunc, width=pso_width)

        self._new_delta_spacing = tk.DoubleVar()
        self._new_delta_pl_thk = tk.DoubleVar()
        self._new_delta_web_h = tk.DoubleVar()
        self._new_delta_web_thk = tk.DoubleVar()
        self._new_delta_fl_w = tk.DoubleVar()
        self._new_delta_fl_thk = tk.DoubleVar()
        self._new_delta_girder_web_h = tk.DoubleVar()
        self._new_delta_girder_web_thk = tk.DoubleVar()
        self._new_delta_girder_fl_w = tk.DoubleVar()
        self._new_delta_girder_fl_thk = tk.DoubleVar()

        self._new_opt_spacing = tk.DoubleVar()
        self._new_opt_pl_thk = tk.DoubleVar()
        self._new_opt_web_h = tk.DoubleVar()
        self._new_opt_web_thk = tk.DoubleVar()
        self._new_opt_fl_w = tk.DoubleVar()
        self._new_opt_fl_thk = tk.DoubleVar()
        self._new_opt_girder_web_h = tk.DoubleVar()
        self._new_opt_girder_web_thk = tk.DoubleVar()
        self._new_opt_girder_fl_w = tk.DoubleVar()
        self._new_opt_girder_fl_thk = tk.DoubleVar()

        self._ent_delta_spacing = tk.Entry(self._bounds_frame, textvariable=self._new_delta_spacing, width=ent_w)
        self._ent_delta_pl_thk = tk.Entry(self._bounds_frame, textvariable=self._new_delta_pl_thk, width=ent_w)
        self._ent_delta_web_h = tk.Entry(self._bounds_frame, textvariable=self._new_delta_web_h, width=ent_w)
        self._ent_delta_web_thk = tk.Entry(self._bounds_frame, textvariable=self._new_delta_web_thk, width=ent_w)
        self._ent_delta_fl_w = tk.Entry(self._bounds_frame, textvariable=self._new_delta_fl_w, width=ent_w)
        self._ent_delta_fl_thk = tk.Entry(self._bounds_frame, textvariable=self._new_delta_fl_thk, width=ent_w)
        self._ent_delta_girder_web_h = tk.Entry(self._girder_frame, textvariable=self._new_delta_girder_web_h,
                                                width=girder_ent_w)
        self._ent_delta_girder_web_thk = tk.Entry(self._girder_frame, textvariable=self._new_delta_girder_web_thk,
                                                  width=girder_ent_w)
        self._ent_delta_girder_fl_w = tk.Entry(self._girder_frame, textvariable=self._new_delta_girder_fl_w,
                                               width=girder_ent_w)
        self._ent_delta_girder_fl_thk = tk.Entry(self._girder_frame, textvariable=self._new_delta_girder_fl_thk,
                                                 width=girder_ent_w)

        bg_col = 'pink'
        self._ent_opt_spacing = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_spacing, width=ent_w, bg=bg_col)
        self._ent_opt_pl_thk = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_pl_thk, width=ent_w, bg=bg_col)
        self._ent_opt_web_h = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_web_h, width=ent_w, bg=bg_col)
        self._ent_opt_web_thk = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_web_thk, width=ent_w, bg=bg_col)
        self._ent_opt_fl_w = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_fl_w, width=ent_w, bg=bg_col)
        self._ent_opt_fl_thk = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_fl_thk, width=ent_w, bg=bg_col)
        self._ent_opt_girder_web_h = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_girder_web_h,
                                              width=girder_ent_w, bg=bg_col)
        self._ent_opt_girder_web_thk = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_girder_web_thk,
                                                width=girder_ent_w, bg=bg_col)
        self._ent_opt_girder_fl_w = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_girder_fl_w,
                                             width=girder_ent_w, bg=bg_col)
        self._ent_opt_girder_fl_thk = tk.Entry(self._opt_values_frame, textvariable=self._new_opt_girder_fl_thk,
                                               width=girder_ent_w, bg=bg_col)

        # stresses in plate and stiffener

        self._new_trans_stress_high = tk.DoubleVar()
        self._new_trans_stress_low = tk.DoubleVar()
        self._new_axial_stress = tk.DoubleVar()
        self._new_shear_stress = tk.DoubleVar()
        self._new_design_pressure = tk.DoubleVar()
        self._new_pressure_side = tk.StringVar()

        self._ent_trans_stress_high = tk.Entry(self._stress_frame, textvariable=self._new_trans_stress_high, width=ent_w)
        self._ent_trans_stress_low = tk.Entry(self._stress_frame, textvariable=self._new_trans_stress_low, width=ent_w)
        self._ent_axial_stress = tk.Entry(self._stress_frame, textvariable=self._new_axial_stress, width=ent_w)
        self._ent_design_pressure = tk.Entry(self._stress_frame, textvariable=self._new_design_pressure, width=ent_w)
        self._ent_design_pressure_side = tk.OptionMenu(self._stress_frame, self._new_pressure_side, *('p', 's'))
        self._ent_shear_stress = tk.Entry(self._stress_frame, textvariable=self._new_shear_stress, width=ent_w)

        start_x, start_y, dx, dy = 20, 100, 100, 40

        self._new_processes = tk.IntVar()
        self._new_processes.set(max(cpu_count() - 1, 1))

        # Weld consumable optimization bias.
        # 0.0 = pure weight optimization. No weld consumable calculations shall be performed.
        # 1.0 = pure estimated weld consumable optimization.
        self._new_weld_bias = tk.DoubleVar()
        self._new_weld_bias.set(0.0)
        self._new_weld_metric = tk.StringVar()
        self._new_weld_metric.set('Weld consumables')
        self._new_weld_study_delta = tk.DoubleVar()
        self._new_weld_study_delta.set(0.1)
        self._last_weight_weld_study_rows = None
        self._last_cost_study_report = None
        self._last_study_type = None

        # Optional addition for built-up welded stiffeners.
        # Keep False by default because many stiffeners may be rolled/profile sections.
        self._new_include_builtup_weld = tk.BooleanVar()
        self._new_include_builtup_weld.set(False)
        tk.Label(self._header_frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg='silver') \
            .grid(row=0, column=4, sticky=tk.W, padx=(20, 4))
        tk.Entry(self._header_frame, textvariable=self._new_processes, width=12, bg='silver') \
            .grid(row=0, column=5, sticky=tk.W)

        for column, header in enumerate(('Spacing [mm]', 'Plate thk. [mm]', 'Web height [mm]', 'Web thk. [mm]',
                                         'Flange width [mm]', 'Flange thk. [mm]')):
            tk.Label(self._bounds_frame, text=header, font='Verdana 7 bold') \
                .grid(row=0, column=1 + column, sticky=tk.W, padx=2)
        bound_rows = (
            ('Upper bounds [mm]', (self._ent_spacing_upper, self._ent_pl_thk_upper, self._ent_web_h_upper,
                                   self._ent_web_thk_upper, self._ent_fl_w_upper, self._ent_fl_thk_upper)),
            ('Iteration delta [mm]', (self._ent_delta_spacing, self._ent_delta_pl_thk, self._ent_delta_web_h,
                                      self._ent_delta_web_thk, self._ent_delta_fl_w, self._ent_delta_fl_thk)),
            ('Lower bounds [mm]', (self._ent_spacing_lower, self._ent_pl_thk_lower, self._ent_web_h_lower,
                                   self._ent_web_thk_lower, self._ent_fl_w_lower, self._ent_fl_thk_lower)),
        )
        for row, (text, entries) in enumerate(bound_rows):
            tk.Label(self._bounds_frame, text=text, font='Verdana 9').grid(row=1 + row, column=0, sticky=tk.W, pady=1)
            for column, entry in enumerate(entries):
                entry.grid(row=1 + row, column=1 + column, sticky=tk.W, padx=2, pady=1)
        tk.Label(self._bounds_frame, text='--------- Number of combinations to run --------->\n'
                                   'RP-C203 can run many combinations, 1M+.\n'
                                   'ML-Numeric is about as fast as RP-C203.',
                 font='Verdana 9 bold', justify=tk.LEFT) \
            .grid(row=4, column=0, columnspan=4, sticky=tk.NW, pady=(6, 0))

        self._runnig_time_label = tk.Label(
            self._bounds_frame,
            text='',
            font='Verdana 12 bold',
            fg='red',
            wraplength=360,
            justify=tk.CENTER,
        )
        self._runnig_time_label.grid(row=4, column=4, columnspan=3, sticky=tk.W, pady=(6, 0))
        self._result_label = tk.Label(
            self._bounds_frame,
            text='',
            font='Verdana 9 bold',
            wraplength=780,
            justify=tk.LEFT,
        )
        self._result_label.grid(row=5, column=0, columnspan=7, sticky=tk.W, pady=(6, 0))

        if self._has_girder:
            tk.Label(self._girder_frame, text='Girder iteration [mm]', font='Verdana 9 bold') \
                .grid(row=0, column=0, columnspan=5, sticky=tk.W)
            for column, header in enumerate(('Web h', 'Web t', 'Fl. w', 'Fl. t')):
                tk.Label(self._girder_frame, text=header, font='Verdana 7 bold') \
                    .grid(row=1, column=1 + column, sticky=tk.W, padx=2)
            girder_rows = (
                ('Upper', (self._ent_girder_web_h_upper, self._ent_girder_web_thk_upper,
                           self._ent_girder_fl_w_upper, self._ent_girder_fl_thk_upper)),
                ('Delta', (self._ent_delta_girder_web_h, self._ent_delta_girder_web_thk,
                           self._ent_delta_girder_fl_w, self._ent_delta_girder_fl_thk)),
                ('Lower', (self._ent_girder_web_h_lower, self._ent_girder_web_thk_lower,
                           self._ent_girder_fl_w_lower, self._ent_girder_fl_thk_lower)),
            )
            for row, (text, entries) in enumerate(girder_rows):
                tk.Label(self._girder_frame, text=text, font='Verdana 8').grid(row=2 + row, column=0, sticky=tk.W)
                for column, entry in enumerate(entries):
                    entry.grid(row=2 + row, column=1 + column, sticky=tk.W, padx=2, pady=1)

        ###

        # tk.Label(self._frame,text='Optimized result:\n')\
        #     .place(x=start_x,y=start_y+ver_mult*dy*0.9)
        tk.Label(self._opt_values_frame, text='Optimized values') \
            .grid(row=0, column=0, columnspan=4, sticky=tk.W)

        opt_value_rows = (
            (('s', self._ent_opt_spacing), ('web_h', self._ent_opt_web_h), ('fl_thk', self._ent_opt_fl_w)),
            (('pl_thk', self._ent_opt_pl_thk), ('web_htk', self._ent_opt_web_thk), ('fl_ttk.', self._ent_opt_fl_thk)),
        )
        for row, pairs in enumerate(opt_value_rows):
            for pair_number, (text, entry) in enumerate(pairs):
                tk.Label(self._opt_values_frame, text=text).grid(row=1 + row, column=2 * pair_number,
                                                                 sticky=tk.W, padx=(0, 4))
                entry.grid(row=1 + row, column=2 * pair_number + 1, sticky=tk.W, padx=(0, 12), pady=1)

        if self._has_girder:
            girder_value_rows = (
                (('girder web_h', self._ent_opt_girder_web_h), ('girder fl_w', self._ent_opt_girder_fl_w)),
                (('girder web_t', self._ent_opt_girder_web_thk), ('girder fl_t', self._ent_opt_girder_fl_thk)),
            )
            for row, pairs in enumerate(girder_value_rows):
                for pair_number, (text, entry) in enumerate(pairs):
                    tk.Label(self._opt_values_frame, text=text).grid(row=3 + row, column=2 * pair_number,
                                                                     sticky=tk.W, padx=(0, 4))
                    entry.grid(row=3 + row, column=2 * pair_number + 1, sticky=tk.W, padx=(0, 12), pady=1)

        # Labels for the pso

        self._lb_swarm_size = tk.Label(self._algo_params_frame, text='swarm size')
        self._lb_omega = tk.Label(self._algo_params_frame, text='omega')
        self._lb_phip = tk.Label(self._algo_params_frame, text='phip')
        self._lb_phig = tk.Label(self._algo_params_frame, text='phig')
        self._lb_maxiter = tk.Label(self._algo_params_frame, text='maxiter')
        self._lb_minstep = tk.Label(self._algo_params_frame, text='minstep')
        self._lb_minfunc = tk.Label(self._algo_params_frame, text='minfunc')

        ###

        stress_rows = (
            ('Sigma,y1_Sd - large transversal stress', 'Verdana 9', self._ent_trans_stress_high, 'MPa'),
            ('Sigma,y2_Sd - small transversal stress', 'Verdana 9', self._ent_trans_stress_low, 'MPa'),
            ('Sigma,x_Sd - axial stress', 'Verdana 9', self._ent_axial_stress, 'MPa'),
            ('Tau,xy - shear stress', 'Verdana 9', self._ent_shear_stress, 'MPa'),
            ('Applied pressure ', 'Verdana 9 bold', self._ent_design_pressure, 'kPa'),
            ('Span: ', 'Verdana 9', self._ent_span, 'm'),
            ('Girder length,Lg: ', 'Verdana 9', self._ent_width_lg, 'm'),
            ('Slamming pressure ', 'Verdana 9', self._ent_slamming_pressure, 'Pa'),
            ('Plate or stiffener side (p/s): ', 'Verdana 9 bold', self._ent_design_pressure_side, ''),
        )
        for row, (text, font, widget, unit) in enumerate(stress_rows):
            tk.Label(self._stress_frame, text=text, font=font).grid(row=row, column=0, sticky=tk.W, pady=2)
            widget.grid(row=row, column=1, sticky=tk.W, padx=(12, 4), pady=2)
            if unit:
                tk.Label(self._stress_frame, text=unit, font='Verdana 9').grid(row=row, column=2, sticky=tk.W, pady=2)

        if self._fatigue_pressure is not None:
            tk.Label(self._stress_frame,
                     text='Fatigue pressure: internal= ' + str(self._fatigue_pressure['p_int']) + ' external= '
                          + str(self._fatigue_pressure['p_ext']),
                     font='Verdana 7', wraplength=520, justify=tk.LEFT) \
                .grid(row=len(stress_rows), column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        else:
            tk.Label(self._stress_frame, text='Fatigue pressure: internal= ' + str(0) + ' external= '
                                       + str(0),
                     font='Verdana 7', wraplength=520, justify=tk.LEFT) \
                .grid(row=len(stress_rows), column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        # setting default values
        init_dim = float(50)  # mm
        init_thk = float(5)  # mm
        self._new_delta_spacing.set(5)
        self._new_delta_pl_thk.set(init_thk)
        self._new_delta_web_h.set(init_dim)
        self._new_delta_web_thk.set(init_thk)
        self._new_delta_fl_w.set(init_dim)
        self._new_delta_fl_thk.set(init_thk)
        self._new_delta_girder_web_h.set(100)
        self._new_delta_girder_web_thk.set(init_thk)
        self._new_delta_girder_fl_w.set(init_dim)
        self._new_delta_girder_fl_thk.set(init_thk)
        self._new_trans_stress_high.set(self._initial_calc_obj.Plate.sigma_y1)
        self._new_trans_stress_low.set(self._initial_calc_obj.Plate.sigma_y2)
        self._new_axial_stress.set(self._initial_calc_obj.Plate.sigma_x1)

        self._new_shear_stress.set(self._initial_calc_obj.Plate.tau_xy)

        self._new_design_pressure.set(self._lateral_pressure)
        self._new_slamming_pressure.set(self._slamming_pressure)
        if self._fatigue_pressure is None:
            self._new_fatigue_ext_press.set(0), self._new_fatigue_int_press.set(0)
        else:
            self._new_fatigue_int_press.set(self._fatigue_pressure['p_int']), \
                self._new_fatigue_ext_press.set(self._fatigue_pressure['p_ext'])

        self._new_spacing_upper.set(round(self._spacing * 1000, 5))
        self._new_spacing_lower.set(round(max(self._spacing * 1000, 0), 5))
        self._new_pl_thk_upper.set(30)
        self._new_pl_thk_lower.set(10)
        self._new_web_h_upper.set(500)
        self._new_web_h_lower.set(200)
        self._new_web_thk_upper.set(30)
        self._new_web_thk_lower.set(10)
        if self._initial_calc_obj.Stiffener is not None:
            if self._initial_calc_obj.Stiffener.get_stiffener_type() != 'FB':
                self._new_fl_w_upper.set(300)
                self._new_fl_w_lower.set(100)
                self._new_fl_thk_upper.set(30)
                self._new_fl_thk_lower.set(10)

        else:
            self._new_fl_w_upper.set(0)
            self._new_fl_w_lower.set(0)
            self._new_fl_thk_upper.set(0)
            self._new_fl_thk_lower.set(0)
        if self._is_unstiffened_plate:
            self._set_fixed_stiffener_iteration_bounds()
        if self._has_girder:
            self._set_girder_iteration_bounds()

        self._new_pressure_side.set('p')
        self._new_width_lg.set(round(self._initial_calc_obj.Girder.girder_lg, 5) if self._has_girder else 10)
        self._new_span.set(round(self._initial_calc_obj.Plate.span, 5))
        self._new_algorithm.set('anysmart')
        self._new_algorithm_random_trials.set(100000)
        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)

        self._new_delta_spacing.trace('w', self.schedule_running_time_update)
        self._new_delta_pl_thk.trace('w', self.schedule_running_time_update)
        self._new_delta_web_h.trace('w', self.schedule_running_time_update)
        self._new_delta_web_thk.trace('w', self.schedule_running_time_update)
        self._new_delta_fl_w.trace('w', self.schedule_running_time_update)
        self._new_delta_fl_thk.trace('w', self.schedule_running_time_update)

        self._new_spacing_upper.trace('w', self.schedule_running_time_update)
        self._new_spacing_lower.trace('w', self.schedule_running_time_update)
        self._new_pl_thk_upper.trace('w', self.schedule_running_time_update)
        self._new_pl_thk_lower.trace('w', self.schedule_running_time_update)
        self._new_web_h_upper.trace('w', self.schedule_running_time_update)
        self._new_web_h_lower.trace('w', self.schedule_running_time_update)
        self._new_web_thk_upper.trace('w', self.schedule_running_time_update)
        self._new_web_thk_lower.trace('w', self.schedule_running_time_update)
        self._new_fl_w_upper.trace('w', self.schedule_running_time_update)
        self._new_fl_w_lower.trace('w', self.schedule_running_time_update)
        self._new_fl_thk_upper.trace('w', self.schedule_running_time_update)
        self._new_fl_thk_lower.trace('w', self.schedule_running_time_update)
        self._new_delta_girder_web_h.trace('w', self.schedule_running_time_update)
        self._new_delta_girder_web_thk.trace('w', self.schedule_running_time_update)
        self._new_delta_girder_fl_w.trace('w', self.schedule_running_time_update)
        self._new_delta_girder_fl_thk.trace('w', self.schedule_running_time_update)
        self._new_girder_web_h_upper.trace('w', self.schedule_running_time_update)
        self._new_girder_web_h_lower.trace('w', self.schedule_running_time_update)
        self._new_girder_web_thk_upper.trace('w', self.schedule_running_time_update)
        self._new_girder_web_thk_lower.trace('w', self.schedule_running_time_update)
        self._new_girder_fl_w_upper.trace('w', self.schedule_running_time_update)
        self._new_girder_fl_w_lower.trace('w', self.schedule_running_time_update)
        self._new_girder_fl_thk_upper.trace('w', self.schedule_running_time_update)
        self._new_girder_fl_thk_lower.trace('w', self.schedule_running_time_update)

        self._new_algorithm_random_trials.trace('w', self.schedule_running_time_update)
        self._new_algorithm.trace('w', self.schedule_running_time_update)

        self.running_time_per_item = {'RP': 1.009943181818182e-5}
        self.running_time_no_filter_factor = 4.0
        initial_x = [self._spacing, self._pl_thk, self._stf_web_h, self._stf_web_thk, self._fl_w, self._fl_thk,
                     self._new_span.get(), self._new_width_lg.get()]
        if self._has_girder:
            initial_x.extend([self._girder_web_h, self._girder_web_thk, self._girder_fl_w, self._girder_fl_thk])
        self.initial_weight = op.calc_weight(initial_x)

        img_file_name = 'img_plate_and_stiffener.gif'
        if os.path.isfile('images/' + img_file_name):
            file_path = 'images/' + img_file_name
        else:
            file_path = self._root_dir + '/images/' + img_file_name
        photo = tk.PhotoImage(file=file_path)
        label = tk.Label(self._stress_frame, image=photo)
        label.image = photo  # keep a reference!
        label.grid(row=0, column=3, rowspan=9, sticky=tk.NW, padx=(20, 0))

        tk.Label(self._run_controls_frame, text='Select algorithm', font='Verdana 8 bold') \
        	.grid(row=0, column=1, sticky=tk.SW, padx=(16, 0))
        self._ent_algorithm.grid(row=1, column=1, sticky=tk.EW, padx=(16, 0))
        self.algorithm_random_label = tk.Label(self._algo_params_frame, text='Number of trials')

        tk.Button(self._run_controls_frame, text='algorithm information', command=self.algorithm_info, bg='white') \
            .grid(row=2, column=1, sticky=tk.EW, padx=(16, 0))
        self._algo_params_frame.grid(row=3, column=1, rowspan=3, sticky=tk.NW, padx=(16, 0))
        self._objective_frame.grid(row=0, column=2, rowspan=6, sticky=tk.NW, padx=(16, 0))

        # ---------------------------------------------------------------------
        # Optimization objective bias
        # ---------------------------------------------------------------------
        tk.Label(
            self._objective_frame,
            text='Optimization objective',
            font='Verdana 8 bold',
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W)

        tk.Label(
            self._objective_frame,
            text='Weight',
            font='Verdana 7',
        ).grid(row=2, column=0, sticky=tk.W)

        self._weld_bias_slider = tk.Scale(
            self._objective_frame,
            variable=self._new_weld_bias,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=170,
            showvalue=False,
            command=self._update_weld_bias_label,
        )
        self._weld_bias_slider.grid(row=1, column=0, columnspan=2, sticky=tk.W)

        tk.Label(
            self._objective_frame,
            text='Weld',
            font='Verdana 7',
        ).grid(row=2, column=1, sticky=tk.E)

        self._weld_bias_value_label = tk.Label(
            self._objective_frame,
            text='Weld bias: 0.0',
            font='Verdana 8 bold',
        )
        self._weld_bias_value_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        self._weld_bias_info_label = tk.Label(
            self._objective_frame,
            text=self._get_weld_bias_text(),
            font='Verdana 7',
            wraplength=270,
            justify=tk.LEFT,
        )
        self._weld_bias_info_label.grid(row=4, column=0, columnspan=3, sticky=tk.W)

        weld_metric_row = tk.Frame(self._objective_frame)
        weld_metric_row.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(4, 0))
        self._weld_metric_menu = tk.OptionMenu(
            weld_metric_row,
            self._new_weld_metric,
            'Weld consumables',
            'Weld length',
            command=self._update_weld_bias_label,
        )
        self._weld_metric_menu.grid(row=0, column=0, sticky=tk.W)

        tk.Checkbutton(
            weld_metric_row,
            variable=self._new_include_builtup_weld,
        ).grid(row=0, column=1, sticky=tk.W, padx=(12, 0))

        tk.Label(
            weld_metric_row,
            text='Built-up weld',
            font='Verdana 7',
        ).grid(row=0, column=2, sticky=tk.W)

        self._new_weld_bias.trace('w', self._update_weld_bias_label)
        self._new_weld_metric.trace('w', self._update_weld_bias_label)

        self._opt_actual_running_time.grid(row=0, column=0, sticky=tk.W)
        self.run_button = tk.Button(self._run_controls_frame, text='RUN OPTIMIZATION!',
                                    command=self.run_optimizaion, bg='red',
                                    font='Verdana 10 bold', fg='Yellow', relief="raised")
        self.run_button.grid(row=1, column=0, sticky=tk.EW, pady=2)
        self.run_results = tk.Button(self._run_controls_frame, text='show calculated', command=self.plot_results,
                                     bg='white', font='Verdana 10', fg='black')
        self.run_results.grid(row=2, column=0, sticky=tk.EW, pady=2)
        self.weight_weld_study_button = tk.Button(
            self._run_controls_frame,
            text='weight/weld study',
            command=self.run_weight_weld_study,
            bg='white',
            font='Verdana 10',
            fg='black',
        )
        self.weight_weld_study_button.grid(row=3, column=0, sticky=tk.EW, pady=2)
        weld_delta_row = tk.Frame(self._run_controls_frame)
        weld_delta_row.grid(row=4, column=0, sticky=tk.W, pady=2)
        tk.Label(weld_delta_row, text='delta', font='Verdana 8').grid(row=0, column=0, sticky=tk.W)
        self._ent_weld_study_delta = tk.Entry(
            weld_delta_row,
            textvariable=self._new_weld_study_delta,
            width=6,
            bg='white',
        )
        self._ent_weld_study_delta.grid(row=0, column=1, sticky=tk.W, padx=4)
        self.show_previous_weld_study_button = tk.Button(
            self._run_controls_frame,
            text='show previous study',
            command=self.show_previous_weight_weld_study,
            bg='white',
            font='Verdana 10',
            fg='black',
        )
        self.show_previous_weld_study_button.grid(row=5, column=0, sticky=tk.EW, pady=2)
        self.cost_study_button = tk.Button(
            self._run_controls_frame,
            text='cost study',
            command=self.open_cost_study_window,
            bg='white',
            font='Verdana 10',
            fg='black',
        )
        self.cost_study_button.grid(row=6, column=0, sticky=tk.EW, pady=2)
        if self._is_unstiffened_plate:
            self._disable_stiffener_iteration_controls()

        self.close_and_save = tk.Button(self._header_frame,
                                        text='Return and replace initial structure with optimized',
                                        command=self.save_and_close, bg='green', font='Verdana 10', fg='yellow')
        self.close_and_save.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))

        tk.Button(self._header_frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10') \
            .grid(row=0, column=2, sticky=tk.W, padx=(0, 12))

        # Selection of constraints
        self._new_check_sec_mod = tk.BooleanVar()
        self._new_check_min_pl_thk = tk.BooleanVar()
        self._new_check_shear_area = tk.BooleanVar()
        self._new_check_buckling = tk.BooleanVar()
        self._new_check_buckling_semi_analytical = tk.BooleanVar()
        self._new_check_buckling_ml_cl = tk.BooleanVar()
        self._new_check_buckling_ml_numeric = tk.BooleanVar()
        self._new_check_fatigue = tk.BooleanVar()
        self._new_check_slamming = tk.BooleanVar()
        self._new_check_local_buckling = tk.BooleanVar()
        self._new_use_weight_filter = tk.BooleanVar()
        self._new_check_sec_mod.set(True)
        self._new_check_min_pl_thk.set(True)
        self._new_check_shear_area.set(True)
        self._new_check_buckling.set(True)
        self._new_check_fatigue.set(True)
        self._new_check_slamming.set(False)
        self._new_check_local_buckling.set(True)
        self._new_use_weight_filter.set(True)
        self._new_check_buckling_semi_analytical.set(False)
        self._new_check_buckling_ml_cl.set(False)
        self._new_check_buckling_ml_numeric.set(False)
        if self._is_unstiffened_plate:
            self._disable_stiffener_only_constraints()
        self._new_check_buckling_semi_analytical.trace('w', self.update_running_time)
        self._new_check_buckling_ml_cl.trace('w', self.update_running_time)
        self._new_check_buckling_ml_numeric.trace('w', self.update_running_time)
        self._new_use_weight_filter.trace('w', self.update_running_time)

        # ---------------------------------------------------------------------
        # Right-hand constraint and stress-scaling panel.
        # Keep this independent of the main start_y used above.  This avoids
        # overlap with the pressure-side selector and fatigue pressure text.
        # ---------------------------------------------------------------------
        tk.Label(self._checks_frame, text='Constraint checks', font='Verdana 9 bold') \
            .grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))

        plain_checks = (
            ('Check for minimum section modulus', self._new_check_sec_mod),
            ('Check for minimum plate thk.', self._new_check_min_pl_thk),
            ('Check for minimum shear area', self._new_check_shear_area),
            ('Check for buckling (RP-C201)', self._new_check_buckling),
            ('Check for fatigue (RP-C203)', self._new_check_fatigue),
            ('Check for bow slamming', self._new_check_slamming),
            ('Check for local stf. buckling', self._new_check_local_buckling),
            ('Use weight filter (for speed)', self._new_use_weight_filter),
        )
        for row, (text, variable) in enumerate(plain_checks):
            tk.Label(self._checks_frame, text=text).grid(row=1 + row, column=0, sticky=tk.W)
            tk.Checkbutton(self._checks_frame, variable=variable).grid(row=1 + row, column=1, sticky=tk.W)

        tk.Label(self._checks_frame, text='Check for buckling (SemiAnalytical S3/U3)') \
            .grid(row=9, column=0, sticky=tk.W)
        self._chk_buckling_semi_analytical = tk.Checkbutton(
            self._checks_frame,
            variable=self._new_check_buckling_semi_analytical,
            state='disabled' if self._has_girder else tk.NORMAL,
        )
        self._chk_buckling_semi_analytical.grid(row=9, column=1, sticky=tk.W)
        tk.Label(self._checks_frame, text='Check for buckling (ML-CL deactivated)') \
            .grid(row=10, column=0, sticky=tk.W)
        self._chk_buckling_ml_cl = tk.Checkbutton(self._checks_frame, variable=self._new_check_buckling_ml_cl,
                                                  state='disabled')
        self._chk_buckling_ml_cl.grid(row=10, column=1, sticky=tk.W)
        tk.Label(self._checks_frame, text='Check for buckling (ML-Numeric)') \
            .grid(row=11, column=0, sticky=tk.W)
        self._chk_buckling_ml_numeric = tk.Checkbutton(
            self._checks_frame,
            variable=self._new_check_buckling_ml_numeric,
            state='disabled' if self._has_girder else tk.NORMAL,
        )
        self._chk_buckling_ml_numeric.grid(row=11, column=1, sticky=tk.W)

        # Stress scaling
        self._new_fup = tk.DoubleVar()
        self._new_fup.set(0.5)
        self._new_fdwn = tk.DoubleVar()
        self._new_fdwn.set(1)

        tk.Label(self._checks_frame, text='Stress scaling', font='Verdana 9 bold') \
            .grid(row=12, column=0, sticky=tk.W, pady=(10, 4))
        tk.Label(self._checks_frame, text='Factor when scaling stresses up, fup') \
            .grid(row=13, column=0, sticky=tk.W)
        ent_fup = tk.Entry(self._checks_frame, textvariable=self._new_fup, width=10)
        ent_fup.grid(row=13, column=1, sticky=tk.W)
        tk.Label(self._checks_frame, text='Factor when scaling stresses up, fdown') \
            .grid(row=14, column=0, sticky=tk.W)
        ent_fdwn = tk.Entry(self._checks_frame, textvariable=self._new_fdwn, width=10)
        ent_fdwn.grid(row=14, column=1, sticky=tk.W)

        # tk.Button(self._frame,text='Iterate predefiened stiffeners',command=self.open_multiple_files ,bg='yellow')\
        #     .place(x=start_x, y=start_y - dy * 2)
        self._toggle_btn = tk.Button(self._header_frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg='salmon')
        self._toggle_btn.grid(row=0, column=3, sticky=tk.W, padx=(0, 12))
        self._toggle_object, self._filez = self._initial_calc_obj, None
        if self._is_unstiffened_plate:
            self._toggle_btn.config(state=tk.DISABLED, text='Plate-only optimization')
        self.draw_properties()
        self.update_running_time()

    def _set_fixed_stiffener_iteration_bounds(self):
        for variable in (
                self._new_web_h_upper, self._new_web_h_lower, self._new_web_thk_upper, self._new_web_thk_lower,
                self._new_fl_w_upper, self._new_fl_w_lower, self._new_fl_thk_upper, self._new_fl_thk_lower):
            variable.set(0)

        for variable in (
                self._new_delta_web_h, self._new_delta_web_thk, self._new_delta_fl_w, self._new_delta_fl_thk):
            variable.set(5)

    def _set_girder_iteration_bounds(self):
        self._new_girder_web_h_upper.set(1000)
        self._new_girder_web_h_lower.set(500)
        self._new_girder_web_thk_upper.set(30)
        self._new_girder_web_thk_lower.set(10)

        if self._initial_calc_obj.Girder.get_stiffener_type() == 'FB':
            self._new_girder_fl_w_upper.set(0)
            self._new_girder_fl_w_lower.set(0)
            self._new_girder_fl_thk_upper.set(0)
            self._new_girder_fl_thk_lower.set(0)
        else:
            self._new_girder_fl_w_upper.set(300)
            self._new_girder_fl_w_lower.set(100)
            self._new_girder_fl_thk_upper.set(30)
            self._new_girder_fl_thk_lower.set(10)

    def _disable_stiffener_only_constraints(self):
        self._new_check_sec_mod.set(False)
        self._new_check_shear_area.set(False)
        self._new_check_slamming.set(False)
        self._new_check_local_buckling.set(False)
        self._new_weld_bias.set(0.0)

    def _disable_stiffener_iteration_controls(self):
        for entry in (
                self._ent_web_h_upper, self._ent_web_h_lower, self._ent_delta_web_h,
                self._ent_web_thk_upper, self._ent_web_thk_lower, self._ent_delta_web_thk,
                self._ent_fl_w_upper, self._ent_fl_w_lower, self._ent_delta_fl_w,
                self._ent_fl_thk_upper, self._ent_fl_thk_lower, self._ent_delta_fl_thk,
                self._ent_opt_web_h, self._ent_opt_web_thk, self._ent_opt_fl_w, self._ent_opt_fl_thk):
            entry.config(state=tk.DISABLED)

        for widget in (
                self._weld_bias_slider, self._weld_metric_menu, self.weight_weld_study_button,
                self.show_previous_weld_study_button, self.cost_study_button):
            widget.config(state=tk.DISABLED)

    def selected_algorithm(self, event):
        '''
        Action when selecting an algorithm.
        :return:
        '''
        # Hide all algorithm-specific controls first (they live in the
        # dedicated parameter sub-frame and are toggled with grid).
        for widget in (self._ent_random_trials, self.algorithm_random_label,
                       self._lb_swarm_size, self._lb_omega, self._lb_phip, self._lb_phig,
                       self._lb_maxiter, self._lb_minstep, self._lb_minfunc,
                       self._ent_swarm_size, self._ent_omega, self._ent_phip, self._ent_phig,
                       self._ent_maxiter, self._ent_minstep, self._ent_minfunc):
            widget.grid_forget()

        if self._new_algorithm.get() in ('random', 'random_no_delta'):
            self.algorithm_random_label.config(text='Number of trials')
            self.algorithm_random_label.grid(row=0, column=0, sticky=tk.W)
            self._ent_random_trials.grid(row=1, column=0, columnspan=2, sticky=tk.W)

        elif self._new_algorithm.get() == 'scipy_de':
            self.algorithm_random_label.config(text='Max evaluations')
            self.algorithm_random_label.grid(row=0, column=0, sticky=tk.W)
            self._ent_random_trials.grid(row=1, column=0, columnspan=2, sticky=tk.W)

        elif self._new_algorithm.get() == 'pso':
            controls = [
                (self._lb_swarm_size, self._ent_swarm_size),
                (self._lb_omega, self._ent_omega),
                (self._lb_phip, self._ent_phip),
                (self._lb_phig, self._ent_phig),
                (self._lb_maxiter, self._ent_maxiter),
                (self._lb_minstep, self._ent_minstep),
                (self._lb_minfunc, self._ent_minfunc),
            ]
            for idx, (label, entry) in enumerate(controls):
                label.grid(row=idx, column=0, sticky=tk.W)
                entry.grid(row=idx, column=1, sticky=tk.W, padx=4)

    def modify_structure_object(self):
        ''' Chaning parameters in the structure object before running. '''
        pass

    def _get_material_factor_for_optimization(self):
        '''
        Returns the material factor used to select ML models and scale numeric UF.

        In normal GUI usage this follows the main application's material-factor selector.
        In standalone/test usage it falls back to the current calculation object's
        material factor.
        '''
        try:
            return float(self.app._new_material_factor.get())
        except Exception:
            try:
                return float(self._initial_calc_obj.Plate.mat_factor)
            except Exception:
                return 1.15

    def schedule_running_time_update(self, *args):
        """
        Debounce running-time updates.

        Tkinter variable traces fire on every keystroke. Without debouncing,
        the GUI repeatedly recomputes the number of combinations while the user
        is still typing, which makes the window feel frozen.
        """
        try:
            if self._running_time_after_id is not None:
                self._frame.after_cancel(self._running_time_after_id)
        except Exception:
            pass

        self._running_time_after_id = self._frame.after(
            500,
            self.update_running_time,
        )

    def _get_ml_algo_for_optimization(self):
        '''
        The main application may store ML models either as a flat dictionary:
            self._ML_buckling['cl SP buc int predictor']

        or as a material-factor dictionary:
            self._ML_buckling[1.15]['cl SP buc int predictor']

        The optimization code expects the flat dictionary for the selected material
        factor, so this helper returns the correct form.
        '''
        mat_fac = self._get_material_factor_for_optimization()

        try:
            if mat_fac in self._ML_buckling and isinstance(self._ML_buckling[mat_fac], dict):
                return self._ML_buckling[mat_fac]
        except Exception:
            pass

        try:
            mat_fac_key = str(mat_fac)
            if mat_fac_key in self._ML_buckling and isinstance(self._ML_buckling[mat_fac_key], dict):
                return self._ML_buckling[mat_fac_key]
        except Exception:
            pass

        return self._ML_buckling

    def _ensure_single_buckling_check(self):
        '''
        Only one buckling formulation should be active at a time:
            RP-C201, SemiAnalytical S3/U3, or ML-Numeric.
        '''
        if getattr(self, '_has_girder', False):
            if self._new_check_buckling_semi_analytical.get():
                self._new_check_buckling_semi_analytical.set(False)
            if self._new_check_buckling_ml_numeric.get():
                self._new_check_buckling_ml_numeric.set(False)
            return

        selected = [
            self._new_check_buckling.get(),
            self._new_check_buckling_semi_analytical.get(),
            False,
            self._new_check_buckling_ml_numeric.get(),
        ]

        if selected.count(True) > 1:
            tk.messagebox.showerror('You can only select one buckling type. Reselect.')

            if self._new_check_buckling.get():
                self._new_check_buckling.set(False)
                self._new_check_local_buckling.set(False)

            if self._new_check_buckling_semi_analytical.get():
                self._new_check_buckling_semi_analytical.set(False)

            if self._new_check_buckling_ml_numeric.get():
                self._new_check_buckling_ml_numeric.set(False)

    def _get_weld_bias_for_optimization(self):
        '''
        Return weld consumable bias in range [0, 1].

        0.0 = pure weight optimization.
              optimize.py shall preserve the old weight-only branch and avoid
              weld consumable calculations.
        1.0 = pure estimated weld consumable optimization.
        '''
        if getattr(self, '_is_unstiffened_plate', False):
            return 0.0
        try:
            return min(max(float(self._new_weld_bias.get()), 0.0), 1.0)
        except Exception:
            return 0.0

    def _get_weld_metric_for_optimization(self):
        try:
            return op.normalize_weld_metric(self._new_weld_metric.get())
        except Exception:
            return 'weld_consumables'

    def _get_weld_metric_text(self):
        return 'weld length' if self._get_weld_metric_for_optimization() == 'weld_length' else 'weld consumables'

    def _get_weld_metric_unit(self):
        return 'm' if self._get_weld_metric_for_optimization() == 'weld_length' else 'kg'

    def _get_weld_bias_text(self):
        '''
        User-readable explanation for the current weld consumable bias.
        '''
        weld_bias = self._get_weld_bias_for_optimization()
        weight_bias = 1.0 - weld_bias

        if weld_bias <= 0.0:
            return 'Pure weight optimization - no weld metric calculations'

        if weld_bias >= 1.0:
            return 'Pure ' + self._get_weld_metric_text() + ' optimization'

        return (
            'Mixed objective: '
            + str(round(100.0 * weight_bias, 0)) + '% weight / '
            + str(round(100.0 * weld_bias, 0)) + '% ' + self._get_weld_metric_text()
        )

    def _update_weld_bias_label(self, *args):
        '''
        Refresh labels when the weld-bias slider changes.
        '''
        try:
            self._weld_bias_value_label.config(
                text='Weld bias: ' + str(round(self._get_weld_bias_for_optimization(), 2))
            )
            self._weld_bias_info_label.config(
                text=self._get_weld_bias_text()
            )
        except Exception:
            pass

        try:
            self.schedule_running_time_update()
        except Exception:
            pass

    def _get_constraint_tuple(self):
        if getattr(self, '_is_unstiffened_plate', False):
            return (False, self._new_check_min_pl_thk.get(),
                    False, self._new_check_buckling.get(),
                    self._new_check_fatigue.get(), False, False,
                    self._new_check_buckling_semi_analytical.get(),
                    False, self._new_check_buckling_ml_numeric.get())

        if getattr(self, '_has_girder', False):
            return (self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
                    self._new_check_shear_area.get(), self._new_check_buckling.get(),
                    self._new_check_fatigue.get(), self._new_check_slamming.get(),
                    self._new_check_local_buckling.get(), False, False, False)

        return (self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
                self._new_check_shear_area.get(), self._new_check_buckling.get(),
                self._new_check_fatigue.get(), self._new_check_slamming.get(),
                self._new_check_local_buckling.get(), self._new_check_buckling_semi_analytical.get(),
                False, self._new_check_buckling_ml_numeric.get())

    def _get_fatigue_pressure_tuple(self):
        if self._fatigue_pressure is None:
            return None

        return ((self._fatigue_pressure['p_ext']['loaded'], self._fatigue_pressure['p_ext']['ballast'],
                 self._fatigue_pressure['p_ext']['part']),
                (self._fatigue_pressure['p_int']['loaded'], self._fatigue_pressure['p_int']['ballast'],
                 self._fatigue_pressure['p_int']['part']))

    def _prepare_structure_for_optimization(self):
        self._initial_calc_obj.Plate.set_span(self._new_span.get())
        selected_mat_fac = self._get_material_factor_for_optimization()
        self._initial_calc_obj.Plate.mat_factor = selected_mat_fac
        if self._initial_calc_obj.Stiffener is not None:
            self._initial_calc_obj.Stiffener.mat_factor = selected_mat_fac
        if self._initial_calc_obj.Girder is not None:
            self._initial_calc_obj.Girder.mat_factor = selected_mat_fac
        return selected_mat_fac

    def _run_optimizer_with_weld_bias(self, weld_bias, cost_factors=None):
        selected_mat_fac = self._prepare_structure_for_optimization()
        return op.run_optmizataion(self._initial_calc_obj, self.get_lower_bounds(),
                                   self.get_upper_bounds(), self._new_design_pressure.get(),
                                   self.get_deltas(), algorithm=self._new_algorithm.get(),
                                   trials=self._new_algorithm_random_trials.get(),
                                   side=self._new_pressure_side.get(),
                                   const_chk=self._get_constraint_tuple(), pso_options=self.pso_parameters,
                                   fatigue_obj=self._fatigue_object,
                                   fat_press_ext_int=self._get_fatigue_pressure_tuple(),
                                   slamming_press=self._new_slamming_pressure.get(),
                                   predefined_stiffener_iter=self._predefined_stiffener_iter,
                                   processes=self._new_processes.get(),
                                   use_weight_filter=self._new_use_weight_filter.get(),
                                   fdwn=self._new_fdwn.get(), fup=self._new_fup.get(),
                                   ml_algo=self._get_ml_algo_for_optimization(),
                                   material_factor=selected_mat_fac,
                                   weld_bias=weld_bias,
                                   builtup_stiffener=self._new_include_builtup_weld.get(),
                                   weld_metric=self._get_weld_metric_for_optimization(),
                                   cost_factors=cost_factors)

    def open_cost_study_window(self):
        cost_window = tk.Toplevel(self._frame)
        cost_window.title('Cost study')
        cost_window.geometry('360x170')
        cost_window.grab_set()

        steel_cost = tk.DoubleVar()
        weld_cost = tk.DoubleVar()
        steel_cost.set(1.0)
        weld_cost.set(1.0)

        tk.Label(cost_window, text='Steel cost per kg').grid(row=0, column=0, sticky=tk.W, padx=20, pady=(20, 4))
        tk.Entry(cost_window, textvariable=steel_cost, width=12).grid(row=0, column=1, sticky=tk.W, pady=(20, 4))
        tk.Label(cost_window, text='Weld cost per ' + self._get_weld_metric_unit())             .grid(row=1, column=0, sticky=tk.W, padx=20, pady=4)
        tk.Entry(cost_window, textvariable=weld_cost, width=12).grid(row=1, column=1, sticky=tk.W, pady=4)

        def run_cost_study():
            try:
                cost_factors = op.normalize_cost_factors((steel_cost.get(), weld_cost.get()))
            except Exception:
                cost_factors = None

            if cost_factors is None:
                messagebox.showerror(
                    title='Cost study',
                    message='Enter non-negative costs. At least one cost must be larger than zero.',
                )
                return

            cost_window.destroy()
            self.run_cost_study(cost_factors)

        tk.Button(cost_window, text='Run cost optimization', command=run_cost_study, bg='white')             .grid(row=2, column=0, sticky=tk.EW, padx=20, pady=(16, 8))
        tk.Button(cost_window, text='Cancel', command=cost_window.destroy, bg='white')             .grid(row=2, column=1, sticky=tk.EW, pady=(16, 8))

    def run_cost_study(self, cost_factors):
        self.run_button.config(state=tk.DISABLED)
        self.cost_study_button.config(state=tk.DISABLED)
        self._opt_actual_running_time.config(text='Cost optimization started ' + datetime.datetime.now().strftime("%H:%M:%S"))
        self._opt_actual_running_time.update()
        t_start = time.time()
        self._opt_results, self._opt_runned = (), False
        self.pso_parameters = (self._new_swarm_size.get(), self._new_omega.get(), self._new_phip.get(),
                               self._new_phig.get(),
                               self._new_maxiter.get(), self._new_minstep.get(), self._new_minfunc.get())

        try:
            self._opt_results = self._run_optimizer_with_weld_bias(
                self._get_weld_bias_for_optimization(),
                cost_factors=cost_factors,
            )
            self._show_cost_study_result(cost_factors, t_start)
        finally:
            self.run_button.config(state=tk.NORMAL)
            self.cost_study_button.config(state=tk.NORMAL)

    def _show_cost_study_result(self, cost_factors, t_start):
        if self._opt_results is None or len(self._opt_results) == 0 or self._opt_results[0] is None:
            messagebox.showinfo(title='Nothing found', message='No cost optimum found. Modify input.\n')
            self._opt_actual_running_time.config(text='Cost optimization finished without result')
            return

        elapsed_seconds = time.time() - t_start
        self._opt_actual_running_time.config(text='Actual running time: \n'
                                                  + str(round(elapsed_seconds / 60, 4)) + ' min')
        self._opt_actual_running_time.update()
        self._opt_runned = True

        result_x = self._result_x_from_structure(self._opt_results[0])
        result_weight = op.calc_weight(result_x)
        result_weld = op.calc_weld_objective(
            result_x,
            stiffener_type=self._stiffener_type_from_structure(self._opt_results[0]),
            include_web_to_flange=self._new_include_builtup_weld.get(),
            weld_metric=self._get_weld_metric_for_optimization(),
        )
        result_cost = cost_factors['steel'] * result_weight + cost_factors['weld'] * result_weld
        steel_cost = cost_factors['steel'] * result_weight
        weld_cost = cost_factors['weld'] * result_weld

        text = (
            'Cost optimization result | Cost: ' + str(round(result_cost, 2))
            + ' | Weight: ' + str(round(result_weight, 1)) + ' kg'
            + ' | ' + self._get_weld_metric_text() + ': ' + str(round(result_weld, 3))
            + ' ' + self._get_weld_metric_unit()
        )
        self._result_label.config(text=text)

        self._new_opt_spacing.set(round(self._opt_results[0].Plate.get_s(), 5))
        self._new_opt_pl_thk.set(round(self._opt_results[0].Plate.get_pl_thk(), 5))
        if self._opt_results[0].Stiffener is not None:
            self._new_opt_web_h.set(round(self._opt_results[0].Stiffener.get_web_h(), 5))
            self._new_opt_web_thk.set(round(self._opt_results[0].Stiffener.get_web_thk(), 5))
            self._new_opt_fl_w.set(round(self._opt_results[0].Stiffener.get_fl_w(), 5))
            self._new_opt_fl_thk.set(round(self._opt_results[0].Stiffener.get_fl_thk(), 5))
        self.draw_properties()
        report = self._build_cost_study_report(
            cost_factors=cost_factors,
            result_x=result_x,
            result_weight=result_weight,
            result_weld=result_weld,
            steel_cost=steel_cost,
            weld_cost=weld_cost,
            result_cost=result_cost,
            elapsed_seconds=elapsed_seconds,
        )
        self._last_cost_study_report = report
        self._last_study_type = 'cost'
        self._show_cost_study_report(report)

    def _build_cost_study_report(self, cost_factors, result_x, result_weight, result_weld,
                                 steel_cost, weld_cost, result_cost, elapsed_seconds):
        seconds, combinations = self.get_running_time()
        count_label = self._get_optimizer_count_label()
        return {
            'title': 'Cost study report',
            'summary': [
                ('Total cost', self._format_study_value(result_cost, 3)),
                ('Steel contribution', self._format_study_value(steel_cost, 3)),
                ('Weld contribution', self._format_study_value(weld_cost, 3)),
                ('Steel cost per kg', self._format_study_value(cost_factors['steel'], 3)),
                ('Weld cost per ' + self._get_weld_metric_unit(), self._format_study_value(cost_factors['weld'], 3)),
                ('Weight [kg]', self._format_study_value(result_weight, 3)),
                (self._get_weld_metric_text().title() + ' [' + self._get_weld_metric_unit() + ']',
                 self._format_study_value(result_weld, 3)),
                ('Weld bias', self._format_study_value(self._get_weld_bias_for_optimization(), 2)),
                ('Weld metric', self._get_weld_metric_text()),
                ('Built-up weld included', str(bool(self._new_include_builtup_weld.get()))),
                ('Algorithm', self._new_algorithm.get()),
                (count_label, self._format_study_value(combinations, 0)),
                ('Elapsed [s]', self._format_study_value(elapsed_seconds, 2)),
            ],
            'geometry': [
                ('Spacing [mm]', self._format_study_value(result_x[0] * 1000, 2)),
                ('Plate thickness [mm]', self._format_study_value(result_x[1] * 1000, 2)),
                ('Web height [mm]', self._format_study_value(result_x[2] * 1000, 2)),
                ('Web thickness [mm]', self._format_study_value(result_x[3] * 1000, 2)),
                ('Flange width [mm]', self._format_study_value(result_x[4] * 1000, 2)),
                ('Flange thickness [mm]', self._format_study_value(result_x[5] * 1000, 2)),
                ('Span [m]', self._format_study_value(result_x[6], 3)),
                ('Girder length [m]', self._format_study_value(result_x[7], 3)),
            ],
            'field_size': [
                ('Panel field span used [m]', self._format_study_value(result_x[6], 3)),
                ('Panel field length used [m]', self._format_study_value(result_x[7], 3)),
                ('Design pressure used [kPa]', self._format_study_value(self._new_design_pressure.get(), 3)),
                ('Pressure side used', self._new_pressure_side.get()),
            ],
        }

    def _show_cost_study_report(self, report):
        result_window = tk.Toplevel(self._frame)
        result_window.title(report.get('title', 'Cost study report'))
        result_window.geometry('1180x620')

        tk.Label(
            result_window,
            text='Cost optimization report',
            font='Verdana 12 bold',
        ).pack(side=tk.TOP, anchor='w', padx=10, pady=(10, 4))

        tk.Label(
            result_window,
            text='Objective = steel cost per kg * weight + weld cost per '
                 + self._get_weld_metric_unit() + ' * ' + self._get_weld_metric_text() + '.',
            font='Verdana 8',
            wraplength=1140,
            justify=tk.LEFT,
        ).pack(side=tk.TOP, anchor='w', padx=10, pady=(0, 8))

        table_frame = tk.Frame(result_window)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ('item', 'value')
        summary_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=14)
        geometry_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=14)
        field_size_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=14)

        for tree, heading in (
                (summary_tree, 'Cost and run data'),
                (geometry_tree, 'Optimized geometry'),
                (field_size_tree, 'Optimization field size')):
            tree.heading('item', text=heading)
            tree.heading('value', text='Value')
            tree.column('item', width=250, anchor=tk.W)
            tree.column('value', width=130, anchor=tk.CENTER)

        for item, value in report.get('summary', []):
            summary_tree.insert('', tk.END, values=(item, value))
        for item, value in report.get('geometry', []):
            geometry_tree.insert('', tk.END, values=(item, value))
        for item, value in report.get('field_size', []):
            field_size_tree.insert('', tk.END, values=(item, value))

        summary_tree.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        geometry_tree.grid(row=0, column=1, sticky='nsew', padx=8)
        field_size_tree.grid(row=0, column=2, sticky='nsew', padx=(8, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.columnconfigure(1, weight=1)
        table_frame.columnconfigure(2, weight=1)
        table_frame.rowconfigure(0, weight=1)

    def _result_x_from_structure(self, structure_obj):
        result = [
            structure_obj.Plate.get_s(),
            structure_obj.Plate.get_pl_thk(),
            0.0 if structure_obj.Stiffener is None else structure_obj.Stiffener.get_web_h(),
            0.0 if structure_obj.Stiffener is None else structure_obj.Stiffener.get_web_thk(),
            0.0 if structure_obj.Stiffener is None else structure_obj.Stiffener.get_fl_w(),
            0.0 if structure_obj.Stiffener is None else structure_obj.Stiffener.get_fl_thk(),
            self._new_span.get(),
            self._new_width_lg.get(),
        ]
        if structure_obj.Girder is not None:
            result.extend([
                structure_obj.Girder.get_web_h(),
                structure_obj.Girder.get_web_thk(),
                structure_obj.Girder.get_fl_w(),
                structure_obj.Girder.get_fl_thk(),
            ])
        return result

    def _stiffener_type_from_structure(self, structure_obj):
        try:
            if structure_obj.Stiffener is not None:
                return structure_obj.Stiffener.get_stiffener_type()
        except Exception:
            pass
        return 'T'

    def run_optimizaion(self):
        '''
        function for button
        :return:
        '''

        self.run_button.config(bg='white')
        self.run_button.config(fg='red')
        self.run_button.config(text='RUNNING OPTIMIZATION')
        self.run_button.config(relief="sunken")
        self._opt_actual_running_time.config(text='Run started ' + datetime.datetime.now().strftime("%H:%M:%S"))
        self._opt_actual_running_time.update()
        t_start = time.time()
        self._opt_results, self._opt_runned = (), False
        self.pso_parameters = (self._new_swarm_size.get(), self._new_omega.get(), self._new_phip.get(),
                               self._new_phig.get(),
                               self._new_maxiter.get(), self._new_minstep.get(), self._new_minfunc.get())

        self._opt_results = self._run_optimizer_with_weld_bias(self._get_weld_bias_for_optimization())

        if self._opt_results is not None and self._opt_results[0] is not None:
            self._opt_actual_running_time.config(text='Actual running time: \n'
                                                      + str(round((time.time() - t_start) / 60, 4)) + ' min')
            self._opt_actual_running_time.update()
            self._opt_runned = True
            if self._opt_results[0].Stiffener is not None:
                text = 'Optimization result | Spacing: ' + str(round(self._opt_results[0].Plate.get_s(), 10) * 1000) + \
                       ' Plate thickness: ' + str(round(self._opt_results[0].Plate.get_pl_thk() * 1000, 10)) + \
                       ' Stiffener - T' + str(round(self._opt_results[0].Stiffener.get_web_h() * 1000, 10)) + 'x' \
                       + str(round(self._opt_results[0].Stiffener.get_web_thk() * 1000, 10)) + \
                       '+' + str(round(self._opt_results[0].Stiffener.get_fl_w() * 1000, 10)) + 'x' \
                       + str(round(self._opt_results[0].Stiffener.get_fl_thk() * 1000, 10))
            else:
                text = 'Optimization result | Spacing: ' + str(round(self._opt_results[0].Plate.get_s(), 10) * 1000) + \
                       ' Plate thickness: ' + str(round(self._opt_results[0].Plate.get_pl_thk() * 1000, 10))

            if self._opt_results[0].Girder is not None:
                text += ' Girder - ' + self._opt_results[0].Girder.get_stiffener_type() + \
                        str(round(self._opt_results[0].Girder.get_web_h() * 1000, 10)) + 'x' + \
                        str(round(self._opt_results[0].Girder.get_web_thk() * 1000, 10)) + '+' + \
                        str(round(self._opt_results[0].Girder.get_fl_w() * 1000, 10)) + 'x' + \
                        str(round(self._opt_results[0].Girder.get_fl_thk() * 1000, 10))

            result_x = self._result_x_from_structure(self._opt_results[0])

            try:
                result_weight = op.calc_weight(result_x)
                text += ' | Weight: ' + str(round(result_weight, 1)) + ' kg'
            except Exception:
                pass

            # Only show weld consumables when the weld objective is active.
            # This mirrors optimize.py, where weld_bias == 0.0 shall avoid weld calculations.
            if self._get_weld_bias_for_optimization() > 0.0:
                try:
                    result_weld_value = op.calc_weld_objective(
                        result_x,
                        stiffener_type=self._stiffener_type_from_structure(self._opt_results[0]),
                        include_web_to_flange=self._new_include_builtup_weld.get(),
                        weld_metric=self._get_weld_metric_for_optimization(),
                    )
                    text += (
                        ' | Est. ' + self._get_weld_metric_text() + ': '
                        + str(round(result_weld_value, 3))
                        + ' ' + self._get_weld_metric_unit()
                    )
                except Exception:
                    pass

            self._result_label.config(text=text)

            self._new_opt_spacing.set(round(self._opt_results[0].Plate.get_s(), 5))
            self._new_opt_pl_thk.set(round(self._opt_results[0].Plate.get_pl_thk(), 5))
            if self._opt_results[0].Stiffener is not None:
                self._new_opt_web_h.set(round(self._opt_results[0].Stiffener.get_web_h(), 5))
                self._new_opt_web_thk.set(round(self._opt_results[0].Stiffener.get_web_thk(), 5))
                self._new_opt_fl_w.set(round(self._opt_results[0].Stiffener.get_fl_w(), 5))
                self._new_opt_fl_thk.set(round(self._opt_results[0].Stiffener.get_fl_thk(), 5))
            if self._opt_results[0].Girder is not None:
                self._new_opt_girder_web_h.set(round(self._opt_results[0].Girder.get_web_h(), 5))
                self._new_opt_girder_web_thk.set(round(self._opt_results[0].Girder.get_web_thk(), 5))
                self._new_opt_girder_fl_w.set(round(self._opt_results[0].Girder.get_fl_w(), 5))
                self._new_opt_girder_fl_thk.set(round(self._opt_results[0].Girder.get_fl_thk(), 5))
            self.draw_properties()
        else:
            messagebox.showinfo(title='Nothing found', message='No better alternatives found. Modify input.\n'
                                                               'There may be no alternative that is acceptable.\n')

        self.run_button.config(bg='green')
        self.run_button.config(fg='yellow')
        self.run_button.config(text='RUN OPTIMIZATION')
        self.run_button.config(relief="raised")

    def _get_weld_study_bias_values(self):
        try:
            delta = float(self._new_weld_study_delta.get())
        except Exception:
            raise ValueError('Weight/weld study delta must be a number between 0 and 1.')

        if delta <= 0.0 or delta > 1.0:
            raise ValueError('Weight/weld study delta must be larger than 0 and no larger than 1.')

        values = []
        value = 0.0
        while value <= 1.0 + 1e-12:
            values.append(round(min(value, 1.0), 10))
            value += delta

        if values[-1] < 1.0:
            values.append(1.0)

        return values

    def _summarize_weight_weld_study_result(self, weld_bias, opt_results, elapsed_seconds):
        row = {
            'bias': weld_bias,
            'weight': None,
            'weld': None,
            'weld_heading': 'Weld [' + self._get_weld_metric_unit() + ']',
            'weld_axis_label': self._get_weld_metric_text().title() + ' [' + self._get_weld_metric_unit() + ']',
            'spacing': None,
            'plate_thk': None,
            'web_h': None,
            'web_thk': None,
            'fl_w': None,
            'fl_thk': None,
            'elapsed': elapsed_seconds,
            'status': 'No result',
        }

        if opt_results is None or len(opt_results) == 0 or opt_results[0] is None:
            return row

        structure_obj = opt_results[0]
        result_x = self._result_x_from_structure(structure_obj)

        try:
            row['weight'] = op.calc_weight(result_x)
        except Exception:
            row['weight'] = None

        try:
            row['weld'] = op.calc_weld_objective(
                result_x,
                stiffener_type=self._stiffener_type_from_structure(structure_obj),
                include_web_to_flange=self._new_include_builtup_weld.get(),
                weld_metric=self._get_weld_metric_for_optimization(),
            )
        except Exception:
            row['weld'] = None

        row['spacing'] = result_x[0] * 1000
        row['plate_thk'] = result_x[1] * 1000
        row['web_h'] = result_x[2] * 1000
        row['web_thk'] = result_x[3] * 1000
        row['fl_w'] = result_x[4] * 1000
        row['fl_thk'] = result_x[5] * 1000
        row['status'] = 'OK'
        return row

    def _format_study_value(self, value, decimals=3):
        if value is None:
            return '-'
        try:
            return str(round(float(value), decimals))
        except Exception:
            return str(value)

    def _show_weight_weld_study_results(self, rows):
        result_window = tk.Toplevel(self._frame)
        result_window.title('Weight/weld study')
        result_window.geometry('1180x720')

        table_frame = tk.Frame(result_window)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = (
            'bias', 'weight', 'weld', 'spacing', 'plate_thk', 'web_h',
            'web_thk', 'fl_w', 'fl_thk', 'elapsed', 'status'
        )
        weld_heading = rows[0].get('weld_heading', 'Weld [kg]') if len(rows) > 0 else 'Weld [kg]'
        weld_axis_label = rows[0].get('weld_axis_label', 'Weld consumables [kg]') if len(rows) > 0 \
            else 'Weld consumables [kg]'
        headings = {
            'bias': 'Bias',
            'weight': 'Weight [kg]',
            'weld': weld_heading,
            'spacing': 's [mm]',
            'plate_thk': 'pl [mm]',
            'web_h': 'web h [mm]',
            'web_thk': 'web t [mm]',
            'fl_w': 'fl w [mm]',
            'fl_thk': 'fl t [mm]',
            'elapsed': 'Time [s]',
            'status': 'Status',
        }

        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=95 if column not in ('status', 'weight', 'weld') else 115, anchor=tk.CENTER)

        for row in rows:
            tree.insert(
                '',
                tk.END,
                values=(
                    self._format_study_value(row['bias'], 2),
                    self._format_study_value(row['weight'], 1),
                    self._format_study_value(row['weld'], 3),
                    self._format_study_value(row['spacing'], 1),
                    self._format_study_value(row['plate_thk'], 1),
                    self._format_study_value(row['web_h'], 1),
                    self._format_study_value(row['web_thk'], 1),
                    self._format_study_value(row['fl_w'], 1),
                    self._format_study_value(row['fl_thk'], 1),
                    self._format_study_value(row['elapsed'], 2),
                    row['status'],
                ),
            )

        tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure

            plot_rows = [row for row in rows if row['status'] == 'OK']
            if len(plot_rows) == 0:
                return

            figure = Figure(figsize=(10.5, 3.5), dpi=100)
            weight_axis = figure.add_subplot(111)
            weld_axis = weight_axis.twinx()

            biases = [row['bias'] for row in plot_rows]
            weights = [row['weight'] for row in plot_rows]
            welds = [row['weld'] for row in plot_rows]

            weight_axis.plot(biases, weights, marker='o', color='tab:blue', label='Weight')
            weld_axis.plot(biases, welds, marker='s', color='tab:red', label='Weld')
            weight_axis.set_xlabel('Weld bias')
            weight_axis.set_ylabel('Weight [kg]', color='tab:blue')
            weld_axis.set_ylabel(weld_axis_label, color='tab:red')
            weight_axis.grid(True, alpha=0.3)
            figure.tight_layout()

            canvas = FigureCanvasTkAgg(figure, master=result_window)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        except Exception as err:
            tk.Label(
                result_window,
                text='Plot unavailable: ' + str(err),
                fg='red',
            ).pack(side=tk.TOP, padx=10, pady=(0, 10))

    def run_weight_weld_study(self):
        self.pso_parameters = (self._new_swarm_size.get(), self._new_omega.get(), self._new_phip.get(),
                               self._new_phig.get(),
                               self._new_maxiter.get(), self._new_minstep.get(), self._new_minfunc.get())

        try:
            bias_values = self._get_weld_study_bias_values()
        except ValueError as err:
            messagebox.showerror(title='Weight/weld study', message=str(err))
            return

        seconds, combinations = self.get_running_time()
        estimated_minutes = max(round((seconds * len(bias_values)) / 60, 2), 0.1)
        count_label = self._get_optimizer_count_label().replace('Estimated ', '').lower()

        proceed = messagebox.askyesno(
            title='Weight/weld study',
            message='This will run ' + str(len(bias_values)) + ' optimizer runs over the current slider range.\n'
                    + 'Each run uses about ' + str(int(combinations)) + ' ' + count_label + '.\n'
                    + 'Estimated total time: about ' + str(estimated_minutes) + ' min.\n\n'
                    + 'Continue?'
        )
        if not proceed:
            return

        original_bias = self._get_weld_bias_for_optimization()
        rows = []

        self.weight_weld_study_button.config(state=tk.DISABLED)
        self.run_button.config(state=tk.DISABLED)

        try:
            for idx, weld_bias in enumerate(bias_values, start=1):
                self._new_weld_bias.set(weld_bias)
                self._opt_actual_running_time.config(
                    text='Weight/weld study: ' + str(idx) + '/' + str(len(bias_values))
                         + ' | bias ' + str(round(weld_bias, 2))
                )
                self._opt_actual_running_time.update()
                self._frame.update_idletasks()

                t_start = time.time()
                opt_results = self._run_optimizer_with_weld_bias(weld_bias)
                rows.append(
                    self._summarize_weight_weld_study_result(
                        weld_bias,
                        opt_results,
                        time.time() - t_start,
                    )
                )

            self._last_weight_weld_study_rows = list(rows)
            self._last_study_type = 'weight_weld'
            self._show_weight_weld_study_results(rows)
        finally:
            self._new_weld_bias.set(original_bias)
            self.weight_weld_study_button.config(state=tk.NORMAL)
            self.run_button.config(state=tk.NORMAL)
            self._opt_actual_running_time.config(text='Weight/weld study finished')
            self._opt_actual_running_time.update()

    def show_previous_weight_weld_study(self):
        if self._last_study_type == 'cost' and self._last_cost_study_report:
            self._show_cost_study_report(self._last_cost_study_report)
            return

        if self._last_study_type == 'weight_weld' and self._last_weight_weld_study_rows:
            self._show_weight_weld_study_results(self._last_weight_weld_study_rows)
            return

        if self._last_cost_study_report:
            self._show_cost_study_report(self._last_cost_study_report)
            return

        if self._last_weight_weld_study_rows:
            self._show_weight_weld_study_results(self._last_weight_weld_study_rows)
            return

        if not self._last_weight_weld_study_rows:
            messagebox.showinfo(
                title='Previous study',
                message='No previous study is available. Run a weight/weld or cost study first.',
            )
            return

    def _count_steps(self, lower, upper, delta):
        """
        Fast count equivalent to np.arange(lower, upper + delta, delta),
        without actually creating the array.

        Inputs are already in SI units.
        """
        try:
            lower = float(lower)
            upper = float(upper)
            delta = float(delta)
        except Exception:
            return 1

        if upper < lower:
            return 0

        if delta <= 0:
            return 1 if abs(upper - lower) < 1e-12 else 0

        if abs(upper - lower) < 1e-12:
            return 1

        values = np.arange(lower, upper + delta, delta)
        return int(np.count_nonzero(values <= upper + abs(delta) * 1e-9))

    def _count_girder_iteration_combinations(self, lower, upper, deltas):
        if not getattr(self, '_has_girder', False):
            return 1

        return (
                self._count_steps(lower[8], upper[8], deltas[6])
                * self._count_steps(lower[9], upper[9], deltas[7])
                * self._count_steps(lower[10], upper[10], deltas[8])
                * self._count_steps(lower[11], upper[11], deltas[9])
        )

    def get_running_time(self):
        """
        Estimate running time without generating all combinations.

        This must stay lightweight because it is called from GUI callbacks.
        """
        try:
            algorithm = self._new_algorithm.get()
        except TclError:
            return 0, 0

        if algorithm in ['random', 'random_no_delta', 'scipy_de']:
            try:
                number_of_combinations = int(self._new_algorithm_random_trials.get())
                return (
                    int(number_of_combinations * self.running_time_per_item['RP']),
                    number_of_combinations,
                )
            except TclError:
                return 0, 0

        try:
            lower = self.get_lower_bounds()
            upper = self.get_upper_bounds()
            deltas = self.get_deltas()
        except TclError:
            return 0, 0
        except Exception:
            return 0, 0

        if getattr(self, '_is_unstiffened_plate', False):
            number_of_combinations = (
                    self._count_steps(lower[0], upper[0], deltas[0])
                    * self._count_steps(lower[1], upper[1], deltas[1])
            )

        # If predefined stiffeners are used, only spacing and plate thickness
        # are iterated in any_get_all_combs(), multiplied by number of sections.
        elif self._predefined_stiffener_iter is not None:
            n_spacing = self._count_steps(lower[0], upper[0], deltas[0])
            n_plate = self._count_steps(lower[1], upper[1], deltas[1])
            n_predef = len(self._predefined_stiffener_iter)
            number_of_combinations = n_spacing * n_plate * n_predef

        else:
            n_spacing = self._count_steps(lower[0], upper[0], deltas[0])
            n_plate = self._count_steps(lower[1], upper[1], deltas[1])
            n_web_h = self._count_steps(lower[2], upper[2], deltas[2])
            n_web_thk = self._count_steps(lower[3], upper[3], deltas[3])
            n_fl_w = self._count_steps(lower[4], upper[4], deltas[4])
            n_fl_thk = self._count_steps(lower[5], upper[5], deltas[5])

            number_of_combinations = (
                    n_spacing
                    * n_plate
                    * n_web_h
                    * n_web_thk
                    * n_fl_w
                    * n_fl_thk
            )
            number_of_combinations *= self._count_girder_iteration_combinations(lower, upper, deltas)

        seconds = number_of_combinations * self.running_time_per_item['RP']
        try:
            weld_bias = self._get_weld_bias_for_optimization()
            weight_filter_is_off = not bool(self._new_use_weight_filter.get())
            objective_disables_filter = 0.0 < weld_bias < 1.0
            if weight_filter_is_off or objective_disables_filter:
                seconds *= self.running_time_no_filter_factor
        except Exception:
            pass

        return int(seconds), int(number_of_combinations)

    def _get_optimizer_count_label(self):
        try:
            if self._new_algorithm.get() == 'scipy_de':
                return 'Estimated max evaluations'
        except Exception:
            pass
        return 'Estimated combinations'

    def get_deltas(self):
        '''
        Return a numpy array of the deltas.
        :return:
        '''
        deltas = [float(self._new_delta_spacing.get()) / 1000, float(self._new_delta_pl_thk.get()) / 1000,
                  float(self._new_delta_web_h.get()) / 1000, float(self._new_delta_web_thk.get()) / 1000,
                  float(self._new_delta_fl_w.get()) / 1000, float(self._new_delta_fl_thk.get()) / 1000]
        if getattr(self, '_has_girder', False):
            deltas.extend([float(self._new_delta_girder_web_h.get()) / 1000,
                           float(self._new_delta_girder_web_thk.get()) / 1000,
                           float(self._new_delta_girder_fl_w.get()) / 1000,
                           float(self._new_delta_girder_fl_thk.get()) / 1000])
        return np.array(deltas)

    def update_running_time(self, *args):
        """
        Estimate the running time of the algorithm.

        This is called through schedule_running_time_update(), not directly
        from every keypress.
        """
        self._running_time_after_id = None

        try:
            seconds, number_of_combinations = self.get_running_time()
            weld_bias = self._get_weld_bias_for_optimization()
            warning_text = ''

            if 0.0 < weld_bias < 1.0:
                warning_text = '\nWARNING: mixed weight/weld combination disables the initial filter.\n' \
                               'Estimate uses no-filter runtime.'
            elif not bool(self._new_use_weight_filter.get()):
                warning_text = '\nWARNING: weight filter is off.\nEstimate uses no-filter runtime.'
            elif weld_bias >= 1.0:
                warning_text = '\nPure weld objective: initial filter uses ' + self._get_weld_metric_text() + '.'

            count_label = self._get_optimizer_count_label().replace('Estimated ', '').lower()
            self._runnig_time_label.config(
                text=str(int(number_of_combinations)) + ' ' + count_label + '\n(about '
                     + str(max(round(seconds / 60, 2), 0.1))
                     + ' min.)'
                     + warning_text
            )

        except (ZeroDivisionError, TclError):
            pass
        except Exception:
            pass

        self._ensure_single_buckling_check()

    def get_upper_bounds(self):
        '''
        Return an numpy array of upper bounds.
        :return:
        '''
        upper = [self._new_spacing_upper.get() / 1000, self._new_pl_thk_upper.get() / 1000,
                 self._new_web_h_upper.get() / 1000, self._new_web_thk_upper.get() / 1000,
                 self._new_fl_w_upper.get() / 1000, self._new_fl_thk_upper.get() / 1000,
                 self._new_span.get(), self._new_width_lg.get()]
        if getattr(self, '_has_girder', False):
            upper.extend([self._new_girder_web_h_upper.get() / 1000,
                          self._new_girder_web_thk_upper.get() / 1000,
                          self._new_girder_fl_w_upper.get() / 1000,
                          self._new_girder_fl_thk_upper.get() / 1000])
        return np.array(upper)

    def get_lower_bounds(self):
        '''
        Return an numpy array of lower bounds.
        :return:
        '''
        lower = [self._new_spacing_lower.get() / 1000, self._new_pl_thk_lower.get() / 1000,
                 self._new_web_h_lower.get() / 1000, self._new_web_thk_lower.get() / 1000,
                 self._new_fl_w_lower.get() / 1000, self._new_fl_thk_lower.get() / 1000,
                 self._new_span.get(), self._new_width_lg.get()]
        if getattr(self, '_has_girder', False):
            lower.extend([self._new_girder_web_h_lower.get() / 1000,
                          self._new_girder_web_thk_lower.get() / 1000,
                          self._new_girder_fl_w_lower.get() / 1000,
                          self._new_girder_fl_thk_lower.get() / 1000])
        return np.array(lower)

    def checkered(self, line_distance):
        # vertical lines at an interval of "line_distance" pixel
        for x in range(line_distance, self._canvas_dim[0], line_distance):
            self._canvas_opt.create_line(x, 0, x, self._canvas_dim[0], fill="grey", stipple='gray50')
        # horizontal lines at an interval of "line_distance" pixel
        for y in range(line_distance, self._canvas_dim[1], line_distance):
            self._canvas_opt.create_line(0, y, self._canvas_dim[0], y, fill="grey", stipple='gray50')

    def draw_properties(self):
        '''
        Drawing properties in the canvas.
        :return:
        '''
        self._canvas_opt.delete('all')
        self.checkered(10)
        ctr_x = self._canvas_dim[0] / 2
        ctr_y = self._canvas_dim[1] / 2 + 200
        m = self._draw_scale
        init_color, init_stipple = 'blue', 'gray12'
        opt_color, opt_stippe = 'red', 'gray12'
        self._canvas_opt.create_rectangle(0, 0, self._canvas_dim[0] + 10, 80, fill='white')
        self._canvas_opt.create_line(10, 10, 30, 10, fill=init_color, width=5)
        initial_text = 'Initial    - Pl.: ' + str(self._spacing * 1000) + 'x' + str(self._pl_thk * 1000)
        if self._initial_calc_obj.Stiffener is not None:
            initial_text += ' Stf.: ' + str(self._stf_web_h * 1000) + 'x' + str(self._stf_web_thk * 1000) + '+' + \
                            str(self._fl_w * 1000) + 'x' + str(self._fl_thk * 1000)
        self._canvas_opt.create_text(270, 10, text=initial_text, font='Verdana 8', fill=init_color)
        self._canvas_opt.create_text(120, 30, text='Weight (per Lg width): ' + str(int(self.initial_weight)),
                                     font='Verdana 8', fill=init_color)

        self._canvas_opt.create_rectangle(ctr_x - m * self._spacing / 2, ctr_y, ctr_x + m * self._spacing / 2,
                                          ctr_y - m * self._pl_thk, fill=init_color, stipple=init_stipple)
        self._canvas_opt.create_rectangle(ctr_x - m * self._stf_web_thk / 2, ctr_y - m * self._pl_thk,
                                          ctr_x + m * self._stf_web_thk / 2,
                                          ctr_y - m * (self._stf_web_h + self._pl_thk)
                                          , fill=init_color, stipple=init_stipple)
        if self._initial_calc_obj.Stiffener is None:
            if self._opt_runned and self._opt_results[0] is not None:
                opt_plate = self._opt_results[0].Plate
                self._canvas_opt.create_rectangle(ctr_x - m * opt_plate.get_s() / 2, ctr_y,
                                                  ctr_x + m * opt_plate.get_s() / 2,
                                                  ctr_y - m * opt_plate.get_pl_thk(), fill=opt_color,
                                                  stipple=opt_stippe)
                self._canvas_opt.create_line(10, 50, 30, 50, fill=opt_color, width=5)
                self._canvas_opt.create_text(270, 50, text='Optimized - Pl.: ' + str(
                    round(opt_plate.get_s() * 1000, 1)) + 'x' + str(round(opt_plate.get_pl_thk() * 1000, 1)),
                                             font='Verdana 8', fill=opt_color)
                self._canvas_opt.create_text(120, 70, text='Weight (per Lg width): ' + str(int(op.calc_weight([
                    opt_plate.get_s(), opt_plate.get_pl_thk(), 0, 0, 0, 0, self._new_span.get(),
                    self._new_width_lg.get()]))), font='Verdana 8', fill=opt_color)
            return

        if self._initial_calc_obj.Stiffener.get_stiffener_type() not in ['L', 'L-bulb']:
            self._canvas_opt.create_rectangle(ctr_x - m * self._fl_w / 2, ctr_y - m * (self._pl_thk + self._stf_web_h),
                                              ctr_x + m * self._fl_w / 2,
                                              ctr_y - m * (self._pl_thk + self._stf_web_h + self._fl_thk),
                                              fill=init_color, stipple=init_stipple)
        else:
            self._canvas_opt.create_rectangle(ctr_x - m * self._stf_web_thk / 2,
                                              ctr_y - m * (self._pl_thk + self._stf_web_h),
                                              ctr_x + m * self._fl_w,
                                              ctr_y - m * (self._pl_thk + self._stf_web_h + self._fl_thk),
                                              fill=init_color, stipple=init_stipple)

        if self._opt_runned:

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].Stiffener.get_s() / 2, ctr_y,
                                              ctr_x + m * self._opt_results[0].Stiffener.get_s() / 2,
                                              ctr_y - m * self._opt_results[0].Stiffener.get_pl_thk(), fill=opt_color,
                                              stipple=opt_stippe)

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].Stiffener.get_web_thk() / 2, ctr_y -
                                              m * self._opt_results[0].Stiffener.get_pl_thk(),
                                              ctr_x + m * self._opt_results[0].Stiffener.get_web_thk() / 2,
                                              ctr_y - m * (self._opt_results[0].Stiffener.get_web_h() +
                                                           self._opt_results[0].Stiffener.get_pl_thk())
                                              , fill=opt_color, stipple=opt_stippe)
            if self._opt_results[0].Stiffener.get_stiffener_type() not in ['L', 'L-bulb']:
                self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].Stiffener.get_fl_w() / 2, ctr_y
                                                  - m * (self._opt_results[0].Stiffener.get_pl_thk() +
                                                         self._opt_results[0].Stiffener.get_web_h()),
                                                  ctr_x + m * self._opt_results[0].Stiffener.get_fl_w() / 2, ctr_y -
                                                  m * (self._opt_results[0].Stiffener.get_pl_thk() + self._opt_results[
                        0].Stiffener.get_web_h() +
                                                       self._opt_results[0].Stiffener.get_fl_thk()),
                                                  fill=opt_color, stipple=opt_stippe)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].Stiffener.get_web_thk() / 2, ctr_y
                                                  - m * (self._opt_results[0].Stiffener.get_pl_thk() +
                                                         self._opt_results[0].Stiffener.get_web_h()),
                                                  ctr_x + m * self._opt_results[0].Stiffener.get_fl_w(), ctr_y -
                                                  m * (self._opt_results[0].Stiffener.get_pl_thk() + self._opt_results[
                        0].Stiffener.get_web_h() +
                                                       self._opt_results[0].Stiffener.get_fl_thk()),
                                                  fill=opt_color, stipple=opt_stippe)

            self._canvas_opt.create_line(10, 50, 30, 50, fill=opt_color, width=5)
            self._canvas_opt.create_text(270, 50, text='Optimized - Pl.: ' + str(
                round(self._opt_results[0].Stiffener.get_s() * 1000, 1))
                                                       + 'x' + str(
                round(self._opt_results[0].Stiffener.get_pl_thk() * 1000, 1)) +
                                                       ' Stf.: ' + str(
                round(self._opt_results[0].Stiffener.get_web_h() * 1000, 1)) +
                                                       'x' + str(
                round(self._opt_results[0].Stiffener.get_web_thk() * 1000, 1)) + '+' +
                                                       str(round(self._opt_results[0].Stiffener.get_fl_w() * 1000, 1)) +
                                                       'x' + str(
                round(self._opt_results[0].Stiffener.get_fl_thk() * 1000, 1)),
                                         font='Verdana 8', fill=opt_color)
            self._canvas_opt.create_text(120, 70, text='Weight (per Lg width): '
                                                       + str(int(op.calc_weight([self._opt_results[0].Stiffener.get_s(),
                                                                                 self._opt_results[
                                                                                     0].Stiffener.get_pl_thk(),
                                                                                 self._opt_results[
                                                                                     0].Stiffener.get_web_h(),
                                                                                 self._opt_results[
                                                                                     0].Stiffener.get_web_thk(),
                                                                                 self._opt_results[
                                                                                     0].Stiffener.get_fl_w(),
                                                                                 self._opt_results[
                                                                                     0].Stiffener.get_fl_thk(),
                                                                                 self._new_span.get(),
                                                                                 self._new_width_lg.get()]))),
                                         font='Verdana 8', fill=opt_color)

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''

        if __name__ == '__main__':
            self._frame.destroy()
            return

        try:
            self.app.on_close_opt_window(self._opt_results)
        except (IndexError, TypeError):
            messagebox.showinfo(title='Nothing to return', message='No results to return.')
            return
        self._frame.destroy()

    def algorithm_info(self):
        ''' When button is clicked, info is displayed.'''

        messagebox.showinfo(title='Algorith information',
                            message='The algorithms currently included is:\n'
                                    'ANYSMART:  \n'
                                    '           Calculates all alternatives using upper and lower bounds.\n'
                                    '           The step used inside the bounds is defined in deltas.\n'
                                    '           This algoritm uses MULTIPROCESSING and will be faster.\n\n'
                                    'RANDOM:    \n'
                                    '           Uses the same bounds and deltas as in ANYSMART.\n'
                                    '           Number of combinations calculated is defined in "trials",\n'
                                    '           which selects withing the bounds and deltas defined.\n\n'
                                    'RANDOM_NO_BOUNDS:\n'
                                    '           Same as RANDOM, but does not use the defined deltas.\n'
                                    '           The deltas is set to 1 mm for all dimensions/thicknesses.\n\n'
                                    'SCIPY_DE:\n'
                                    '           Uses SciPy differential evolution to sample snapped candidates\n'
                                    '           from the current bounds and deltas.\n'
                                    '           Number of trials is used as the max evaluation budget.\n\n'
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

    def toggle(self):
        if getattr(self, '_is_unstiffened_plate', False):
            self._predefined_stiffener_iter = None
            return

        if self._toggle_btn.config('relief')[-1] == 'sunken':
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg='salmon')
            self._ent_spacing_upper.config(bg='white')
            self._ent_spacing_lower.config(bg='white')
            self._ent_delta_spacing.config(bg='white')
            predefined_stiffener_iter = []
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg='salmon')
            self._toggle_btn.config(bg='lightgreen')
            self._ent_spacing_upper.config(bg='lightgreen')
            self._ent_spacing_lower.config(bg='lightgreen')
            self._ent_delta_spacing.config(bg='lightgreen')
            self._ent_pl_thk_upper.config(bg='lightgreen')
            self._ent_pl_thk_lower.config(bg='lightgreen')
            self._ent_delta_pl_thk.config(bg='lightgreen')

            open_files = askopenfilenames(parent=self._frame, title='Choose files to open',
                                          initialdir=self._root_dir)
            # TODO for both stiffeners and girders

            self._initial_calc_obj.Stiffener.t = self._initial_calc_obj.Plate.t
            self._initial_calc_obj.Stiffener.s = self._initial_calc_obj.Plate.spacing
            predefined_stiffener_iter = hlp.helper_read_section_file(files=list(open_files),
                                                                     obj=self._initial_calc_obj.Stiffener)
        if predefined_stiffener_iter == []:
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg='salmon')
            self._ent_spacing_upper.config(bg='white')
            self._ent_spacing_lower.config(bg='white')
            self._ent_delta_spacing.config(bg='white')
            self._ent_pl_thk_upper.config(bg='white')
            self._ent_pl_thk_lower.config(bg='white')
            self._ent_delta_pl_thk.config(bg='white')
            self._predefined_stiffener_iter = None
        else:
            self._predefined_stiffener_iter = predefined_stiffener_iter
        self.update_running_time()

    def open_example_file(self):
        import os
        if os.path.isfile('sections.csv'):
            os.startfile('sections.csv')
        else:
            os.startfile(self._root_dir + '/' + 'sections.csv')

    def show_calculated(self):
        ''' '''
        pass

    def plot_results(self):
        if len(self._opt_results) != 0:
            op.plot_optimization_results(self._opt_results)

    def write_result_csv(self):
        if len(self._opt_results) != 0:
            print(self._opt_results)


def receive_progress_info():
    '''
    Get progress info from optimization algorithm.
    :return:
    '''
    print('hi')


if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateOptimizeWindow(master=root)
    root.mainloop()




