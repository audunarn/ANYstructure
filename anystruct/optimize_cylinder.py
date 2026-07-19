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
    import anystruct.main_application as main_application
    import anystruct.optimize as op
    import anystruct.example_data as test
    import anystruct.helper as hlp
    import anystruct.line_structure as line_structure
    import anystruct.ml_models as ml_models
except ModuleNotFoundError:
    import ANYstructure.anystruct.main_application as main_application
    import ANYstructure.anystruct.optimize as op
    import ANYstructure.anystruct.example_data as test
    import ANYstructure.anystruct.helper as hlp
    import ANYstructure.anystruct.line_structure as line_structure
    import ANYstructure.anystruct.ml_models as ml_models


class CreateOptimizeCylinderWindow():
    '''
    This class initiates the single optimization window.
    '''

    def __init__(self, master, app=None):
        super(CreateOptimizeCylinderWindow, self).__init__()
        if __name__ == '__main__':
            import anystruct.calc_structure as calc
            self._initial_structure_obj = test.get_structure_calc_object(heavy=True)
            self._initial_calc_obj = test.get_structure_calc_object(heavy=True)
            self._fatigue_object = test.get_fatigue_object()
            self._fatigue_pressure = test.get_fatigue_pressures()
            self._slamming_pressure = test.get_slamming_pressure()
            self._root_dir = os.path.dirname(os.path.abspath(__file__))
            image_dir = self._root_dir + '\\images\\'
            self._initial_cylinder_obj = calc.CylinderAndCurvedPlate(main_dict=test.shell_main_dict,
                                                                     shell=calc.Shell(test.shell_dict),
                                                                     long_stf=calc.Structure(test.obj_dict_cyl_long2),
                                                                     ring_stf=None,
                                                                     # calc.Structure(test.obj_dict_cyl_ring2),
                                                                     ring_frame=None)  # calc.Structure(test.obj_dict_cyl_heavy_ring2))
            self._ML_buckling = ml_models.load_buckling_models((self._root_dir,))
            self._ML_classes = ml_models.default_ml_class_messages()
        else:
            self.app = app
            active_bundle = app._line_to_struc[app._active_line]
            self._initial_structure_obj = line_structure.structure(active_bundle)
            self._initial_calc_obj = line_structure.structure(active_bundle)
            self._initial_cylinder_obj = line_structure.cylinder(active_bundle)
            self._fatigue_object = line_structure.fatigue(active_bundle)
            try:
                self._fatigue_pressure = app.get_fatigue_pressures(app._active_line,
                                                                   self._fatigue_object.get_accelerations())
            except AttributeError:
                self._fatigue_pressure = None
            try:
                self._lateral_pressure = 0
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

        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1700x1000')
        self._frame.grab_set()

        '''
            shell_upper_bounds = np.array( [0.03, 3, 5, 5, 10, None, None, None])
            shell_deltas = np.array(       [0.005, 0.5, 1, 0.1,1, None, None, None])
            shell_lower_bounds = np.array( [0.02, 2.5, 5, 5, 10, None, None, None])

            long_upper_bounds = np.array(   [0.8, None, 0.5, 0.02, 0.2, 0.03, None, None])
            long_deltas = np.array(         [0.1, None, 0.1, 0.01, 0.1, 0.01, None, None])
            long_lower_bounds = np.array(   [0.7, None, 0.3,  0.01, 0.1, 0.01, None, None])

            ring_stf_upper_bounds = np.array(   [None, None, 0.5, 0.018, 0.2, 0.03, None, None])
            ring_stf_deltas = np.array(         [None, None, 0.1, 0.004, 0.1, 0.01, None, None])
            ring_stf_lower_bounds = np.array(   [None, None, 0.3,  0.010, 0.1, 0.010, None, None])

            ring_frame_upper_bounds = np.array( [None, None, 0.9, 0.04, 0.3, 0.04, None, None])
            ring_frame_deltas = np.array(       [None, None, 0.2, 0.01, 0.1, 0.01, None, None])
            ring_frame_lower_bounds = np.array( [None, None, 0.7,  0.02, 0.2, 0.02, None, None])
        '''
        ent_w = 12

        default_shell_upper_bounds = np.array([0.03, 3, 5, 5, 10, None, None, None])
        default_shell_deltas = np.array([0.005, 0.005, 0.005, 0.005, 0.005, None, None, None])
        default_shell_lower_bounds = np.array([0.01, 2.5, 5, 5, 10, None, None, None])

        default_long_upper_bounds = np.array([0.8, None, 0.5, 0.03, 0.3, 0.03, None, None])
        default_long_deltas = np.array([0.005, None, 0.05, 0.005, 0.05, 0.005, None, None])
        default_long_lower_bounds = np.array([0.7, None, 0.2, 0.01, 0.1, 0.01, None, None])

        default_ring_stf_upper_bounds = np.array([None, None, 0.5, 0.03, 0.3, 0.03, None, None])
        default_ring_stf_deltas = np.array([None, None, 0.05, 0.005, 0.05, 0.005, None, None])
        default_ring_stf_lower_bounds = np.array([None, None, 0.2, 0.010, 0.1, 0.010, None, None])

        default_ring_frame_upper_bounds = np.array([None, None, 1.0, 0.03, 0.3, 0.03, None, None])
        default_ring_frame_deltas = np.array([None, None, 0.1, 0.005, 0.05, 0.005, None, None])
        default_ring_frame_lower_bounds = np.array([None, None, 0.5, 0.01, 0.1, 0.01, None, None])

        self._default_data = [[default_shell_upper_bounds, default_shell_deltas, default_shell_lower_bounds],
                              [default_long_upper_bounds, default_long_deltas, default_long_lower_bounds],
                              [default_ring_stf_upper_bounds, default_ring_stf_deltas, default_ring_stf_lower_bounds],
                              [default_ring_frame_upper_bounds, default_ring_frame_deltas,
                               default_ring_frame_lower_bounds]]

        shell_example = [0.03, 3, 5, 5, 10, None, None, None]
        long_example = ring_stf_example = ring_frame_example = [0.8, None, 0.5, 0.02, 0.2, 0.03, None, None]

        shell_upper_bounds = [tk.DoubleVar() for dummy in shell_example]
        shell_deltas = [tk.DoubleVar() for dummy in shell_example]
        shell_lower_bounds = [tk.DoubleVar() for dummy in shell_example]

        long_upper_bounds = [tk.DoubleVar() for dummy in long_example]
        long_deltas = [tk.DoubleVar() for dummy in long_example]
        long_lower_bounds = [tk.DoubleVar() for dummy in long_example]

        ring_stf_upper_bounds = [tk.DoubleVar() for dummy in ring_stf_example]
        ring_stf_deltas = [tk.DoubleVar() for dummy in ring_stf_example]
        ring_stf_lower_bounds = [tk.DoubleVar() for dummy in ring_stf_example]

        ring_frame_upper_bounds = [tk.DoubleVar() for dummy in ring_frame_example]
        ring_frame_deltas = [tk.DoubleVar() for dummy in ring_frame_example]
        ring_frame_lower_bounds = [tk.DoubleVar() for dummy in ring_frame_example]
        self._new_geo_data = list()

        self._new_geo_data = [[shell_upper_bounds, shell_deltas, shell_lower_bounds],
                              [long_upper_bounds, long_deltas, long_lower_bounds],
                              [ring_stf_upper_bounds, ring_stf_deltas, ring_stf_lower_bounds],
                              [ring_frame_upper_bounds, ring_frame_deltas, ring_frame_lower_bounds]]

        # Gridded layout scaffolding: header row on top, the bounds table on
        # the left with the stress inputs and result text below it, and a
        # right-hand column with the run controls, optimization objective and
        # the drawing canvas.  Mirrors the old fixed-pixel arrangement.
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(3, weight=1)
        self._header_frame = tk.Frame(self._frame)
        self._header_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(8, 4))
        self._bounds_frame = tk.Frame(self._frame)
        self._bounds_frame.grid(row=1, column=0, sticky=tk.NW, padx=10)
        self._stress_frame = tk.Frame(self._frame)
        self._stress_frame.grid(row=2, column=0, sticky=tk.NW, padx=10, pady=(8, 0))
        self._footer_frame = tk.Frame(self._frame)
        self._footer_frame.grid(row=3, column=0, sticky=tk.NW, padx=10, pady=(4, 8))
        self._right_column = tk.Frame(self._frame)
        self._right_column.grid(row=1, column=1, rowspan=3, sticky=tk.NW, padx=(10, 10))
        self._run_controls_frame = tk.Frame(self._right_column)
        self._run_controls_frame.grid(row=0, column=0, sticky=tk.NW)
        self._objective_frame = tk.Frame(self._right_column)
        self._objective_frame.grid(row=1, column=0, sticky=tk.NW, pady=(12, 0))
        self._canvas_holder = tk.Frame(self._right_column)
        self._canvas_holder.grid(row=2, column=0, sticky=tk.NW, pady=(12, 0))

        self._new_entries = list()
        map_type = {'shell': 0, 'long': 1, 'ring stf': 2, 'ring heavy': 3}
        map_type_idx = {
            0: True,
            1: self._initial_cylinder_obj.LongStfObj is not None,
            2: self._initial_cylinder_obj.RingStfObj is not None,
            3: self._initial_cylinder_obj.RingFrameObj is not None,
        }
        self._map_type_idx = map_type_idx

        for idx_1, geo_i in enumerate(self._new_geo_data):
            all_geos = list()
            if map_type_idx[idx_1] == False:
                continue
            for idx_2, entries in enumerate(geo_i):
                these_ents = list()
                for idx_3, ent_i in enumerate(entries):
                    self._new_geo_data[idx_1][idx_2][idx_3].trace_add('write', self.schedule_running_time_update)
                    these_ents.append(tk.Entry(self._bounds_frame,
                                               textvariable=self._new_geo_data[idx_1][idx_2][idx_3], width=ent_w))
                    self._new_geo_data[idx_1][idx_2][idx_3].set(0 if self._default_data[idx_1][idx_2][idx_3] is None
                                                                else self._default_data[idx_1][idx_2][idx_3] * 1000)
                all_geos.append(these_ents)
            self._new_entries.append(all_geos)

        self._is_conical_optimizer = getattr(self._initial_cylinder_obj, 'geometry', None) == 9
        if self._is_conical_optimizer:
            self._set_conical_optimizer_shell_defaults()

        self._predefined_stiffener_iter = None
        self._running_time_after_id = None

        # Optimization objective bias.
        # 0.0 = pure weight optimization (no weld consumable calculations in optimizer).
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
        self._new_include_builtup_weld = tk.BooleanVar()
        self._new_include_builtup_weld.set(False)

        self._opt_runned = False
        self._opt_results = ()
        self._opt_actual_running_time = tk.Label(self._run_controls_frame, text='', font='Verdana 12 bold')

        self._draw_scale = 600
        self._canvas_dim = (550, 490)
        self._canvas_opt = tk.Canvas(self._canvas_holder, width=self._canvas_dim[0], height=self._canvas_dim[1],
                                     background='azure', relief='groove', borderwidth=2)

        self._canvas_opt.grid(row=0, column=0, sticky=tk.NW)

        algorithms = ('anysmart cylinder', 'scipy_de cylinder', 'random', 'random_no_delta')

        tk.Label(self._header_frame, text='-- Cylinder optimizer --', font='Verdana 15 bold') \
            .grid(row=0, column=0, sticky=tk.W, padx=(0, 20))

        # upper and lower bounds for optimization
        # [0.6, 0.012, 0.3, 0.01, 0.1, 0.01]

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

        # additional choices for the random and pso algorithm; the dynamic
        # per-algorithm controls live in their own sub-frame so they can be
        # shown/hidden with grid/grid_remove.
        self._algo_params_frame = tk.Frame(self._run_controls_frame)
        self._ent_algorithm = tk.OptionMenu(self._run_controls_frame, self._new_algorithm,
                                            command=self.selected_algorithm, *algorithms)
        self._ent_random_trials = tk.Entry(self._algo_params_frame, textvariable=self._new_algorithm_random_trials)

        pso_width = 10
        self._ent_swarm_size = tk.Entry(self._algo_params_frame, textvariable=self._new_swarm_size, width=pso_width)
        self._ent_omega = tk.Entry(self._algo_params_frame, textvariable=self._new_omega, width=pso_width)
        self._ent_phip = tk.Entry(self._algo_params_frame, textvariable=self._new_phip, width=pso_width)
        self._ent_phig = tk.Entry(self._algo_params_frame, textvariable=self._new_phig, width=pso_width)
        self._ent_maxiter = tk.Entry(self._algo_params_frame, textvariable=self._new_maxiter, width=pso_width)
        self._ent_minstep = tk.Entry(self._algo_params_frame, textvariable=self._new_minstep, width=pso_width)
        self._ent_minfunc = tk.Entry(self._algo_params_frame, textvariable=self._new_minfunc, width=pso_width)

        # stresses in plate and stiffener

        self._new_sasd = tk.DoubleVar()
        self._new_smsd = tk.DoubleVar()
        self._new_tTsd = tk.DoubleVar()
        self._new_tQsd = tk.DoubleVar()
        self._new_design_pressure = tk.DoubleVar()
        self._new_shsd = tk.DoubleVar()

        self._new_sasd.set(self._initial_cylinder_obj.sasd)
        self._new_smsd.set(self._initial_cylinder_obj.smsd)
        self._new_tTsd.set(self._initial_cylinder_obj.tTsd)
        self._new_tQsd.set(self._initial_cylinder_obj.tQsd)
        self._new_design_pressure.set(self._initial_cylinder_obj.psd)
        self._new_shsd.set(self._initial_cylinder_obj.shsd)

        self._ent_sasd = tk.Entry(self._stress_frame, textvariable=self._new_sasd, width=ent_w)
        self._ent_smsd = tk.Entry(self._stress_frame, textvariable=self._new_smsd, width=ent_w)
        self._ent_tTsd = tk.Entry(self._stress_frame, textvariable=self._new_tTsd, width=ent_w)
        self._ent_tQsd = tk.Entry(self._stress_frame, textvariable=self._new_tQsd, width=ent_w)
        self._ent_design_pressure = tk.Entry(self._stress_frame, textvariable=self._new_design_pressure, width=ent_w)
        self._ent_shsd = tk.Entry(self._stress_frame, textvariable=self._new_shsd, width=ent_w)

        self._new_processes = tk.IntVar()
        self._new_processes.set(max(cpu_count() - 1, 1))
        tk.Label(self._header_frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg='silver') \
            .grid(row=0, column=4, sticky=tk.W, padx=(20, 4))
        tk.Entry(self._header_frame, textvariable=self._new_processes, width=12, bg='silver') \
            .grid(row=0, column=5, sticky=tk.W)

        self._runnig_time_label = tk.Label(
            self._objective_frame,
            text='',
            font='Verdana 12 bold',
            fg='red',
            wraplength=520,
            justify=tk.LEFT,
        )
        self._result_label = tk.Label(self._footer_frame, text='', font='Verdana 9 bold', wraplength=460,
                                      justify=tk.LEFT)
        self._result_label.grid(row=1, column=0, sticky=tk.W, pady=(4, 0))

        '''
                self._new_geo_data =  [[shell_upper_bounds,shell_deltas, shell_lower_bounds],
                              [long_upper_bounds, long_deltas, long_lower_bounds],
                              [ring_stf_upper_bounds, ring_stf_deltas, ring_stf_lower_bounds],
                              [ring_frame_upper_bounds, ring_frame_deltas, ring_frame_lower_bounds]]
        '''
        shell = ['Shell thk. [mm]', 'Eq. radius [mm]', 'Eq. length [mm]', 'Eq. shell L [mm]', 'Eq. total L [mm]',
                 'Cone r1 [mm]', 'Cone r2 [mm]', 'Cone l [mm]'] if self._is_conical_optimizer else \
            ['Shell thk. [mm]', 'Shell radius [mm]', 'l rings [mm]', 'L shell [mm]', 'L tot. [mm]', 'N/A - future',
             'N/A - future', 'N/A - future']
        stf_long = ['Spacing [mm]', 'N/A', 'Web height [mm]', 'Web thk. [mm]', 'Flange width [mm]',
                    'Flange thk. [mm]', 'N/A - future', 'N/A - future']
        stf_ring = ['N/A', 'N/A', 'Web height [mm]', 'Web thk. [mm]', 'Flange width [mm]',
                    'Flange thk. [mm]', 'N/A - future', 'N/A - future']
        all_label = [shell, stf_long, stf_ring, stf_ring]
        text_i = ['Upper bounds [mm]', 'Iteration delta [mm]', 'Lower bounds [mm]']
        kind = ['Shell or panel', 'Longitudinal stiffener', 'Ring stiffener', 'Ring frame/girder']
        # Grid rows advance per shown member group (4 rows each: heading with
        # column labels, then upper/delta/lower), so hidden member types no
        # longer leave blank bands in the table.
        bounds_row = 0
        # self._new_entries only holds the visible member groups, so keep a
        # matching index into the label/kind lists.
        visible_indices = [idx for idx in range(len(self._new_geo_data)) if map_type_idx[idx]]
        for member_number, member in enumerate(self._new_entries):
            idx_1 = visible_indices[member_number]
            tk.Label(self._bounds_frame, text=kind[idx_1], font='Verdana 10 bold') \
                .grid(row=bounds_row, column=0, sticky=tk.W, pady=(8, 0))
            for idx_3, header in enumerate(all_label[idx_1]):
                tk.Label(self._bounds_frame, text=header, font='Verdana 7 bold') \
                    .grid(row=bounds_row, column=1 + idx_3, sticky=tk.W, padx=2, pady=(8, 0))
            bounds_row += 1
            for idx_2, bounds in enumerate(member):
                tk.Label(self._bounds_frame, text=text_i[idx_2], font='Verdana 9') \
                    .grid(row=bounds_row, column=0, sticky=tk.W, pady=1)
                for idx_3, entry_i in enumerate(bounds):
                    entry_i.grid(row=bounds_row, column=1 + idx_3, sticky=tk.W, padx=2, pady=1)
                    if 'N/A' in all_label[idx_1][idx_3] or (
                            self._is_conical_optimizer and idx_1 == 0 and idx_3 in [1, 2, 3, 4]):
                        entry_i.configure(bg='grey')
                bounds_row += 1

        ###

        # Labels for the pso

        self._lb_swarm_size = tk.Label(self._algo_params_frame, text='swarm size')
        self._lb_omega = tk.Label(self._algo_params_frame, text='omega')
        self._lb_phip = tk.Label(self._algo_params_frame, text='phip')
        self._lb_phig = tk.Label(self._algo_params_frame, text='phig')
        self._lb_maxiter = tk.Label(self._algo_params_frame, text='maxiter')
        self._lb_minstep = tk.Label(self._algo_params_frame, text='minstep')
        self._lb_minfunc = tk.Label(self._algo_params_frame, text='minfunc')

        ###
        # ---------------------------------------------------------------------
        # Stresses / loads
        # Moved below the upper/lower-bound input fields. The weld-bias
        # objective block now uses the previous right-side stress area.
        # ---------------------------------------------------------------------
        for offset, (text, font, entry) in enumerate((
                ('Design axial stress,          sa,sd', 'Verdana 9', self._ent_sasd),
                ('Design bending stress,   sm,sd', 'Verdana 9', self._ent_smsd),
                ('Design torsional stress,   tT,sd', 'Verdana 9', self._ent_tTsd),
                ('Design shear stress,        tQ,sd', 'Verdana 9', self._ent_tQsd),
                ('Design lateral pressure,    psd', 'Verdana 9 bold', self._ent_design_pressure),
                ('Additional hoop stress, sh,sd,    psd', 'Verdana 9 bold', self._ent_shsd),
        )):
            tk.Label(self._stress_frame, text=text, font=font).grid(row=offset, column=0, sticky=tk.W, pady=1)
            entry.grid(row=offset, column=1, sticky=tk.W, padx=(16, 4), pady=1)
            tk.Label(self._stress_frame, text='Pa', font='Verdana 9').grid(row=offset, column=2, sticky=tk.W, pady=1)

        if self._fatigue_pressure is not None:
            tk.Label(self._footer_frame,
                     text='Fatigue pressure: internal= ' + str(self._fatigue_pressure['p_int']) + ' external= '
                          + str(self._fatigue_pressure['p_ext']), font='Verdana 7',
                     wraplength=980, justify=tk.LEFT) \
                .grid(row=0, column=0, sticky=tk.W)
        else:
            tk.Label(self._footer_frame, text='Fatigue pressure: internal= ' + str(0) + ' external= '
                                       + str(0), font='Verdana 7',
                     wraplength=980, justify=tk.LEFT) \
                .grid(row=0, column=0, sticky=tk.W)

        # setting default values
        init_dim = float(5)  # mm
        init_thk = float(5)  # mm

        self._new_slamming_pressure.set(self._slamming_pressure)
        if self._fatigue_pressure is None:
            self._new_fatigue_ext_press.set(0), self._new_fatigue_int_press.set(0)
        else:
            self._new_fatigue_int_press.set(self._fatigue_pressure['p_int']), \
                self._new_fatigue_ext_press.set(self._fatigue_pressure['p_ext'])

        self._new_algorithm.set('anysmart cylinder')
        self._new_algorithm_random_trials.set(100000)
        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)

        self._new_algorithm_random_trials.trace_add('write', self.schedule_running_time_update)
        self._new_algorithm.trace_add('write', self.schedule_running_time_update)

        self.running_time_per_item = {'RP': 1.009943181818182e-5}
        self.running_time_no_filter_factor = 4.0

        # self.running_time_per_item = {'PULS':0.2489626556016598, 'RP': 1.009943181818182e-5}
        # self.initial_weight = op.calc_weight([self._spacing,self._pl_thk,self._stf_web_h,self._stf_web_thk,
        #                                       self._fl_w,self._fl_thk,self._new_span.get(),self._new_width_lg.get()])

        # img_file_name = 'img_plate_and_stiffener.gif'
        # if os.path.isfile('images/' + img_file_name):
        #     file_path = 'images/' + img_file_name
        # else:
        #     file_path = self._root_dir + '/images/' + img_file_name
        # photo = tk.PhotoImage(file=file_path)
        # label = tk.Label(self._frame,image=photo)
        # label.image = photo  # keep a reference!
        # label.place(x=550, y=300)

        # tk.Label(self._frame,text='Select algorithm', font = 'Verdana 8 bold').place(x=start_x+dx*11, y=start_y+7*dy)
        # self._ent_algorithm.place(x=start_x+dx*11, y=start_y+dy*8)
        self.algorithm_random_label = tk.Label(self._algo_params_frame, text='Number of trials')

        self.run_button = tk.Button(self._run_controls_frame, text='RUN OPTIMIZATION!', command=self.run_optimizaion,
                                    bg='red', font='Verdana 10 bold', fg='Yellow', relief="raised")
        self.run_button.grid(row=0, column=0, sticky=tk.EW, pady=(0, 4))

        self._opt_actual_running_time.grid(row=1, column=0, sticky=tk.W, pady=(0, 8))

        self.weight_weld_study_button = tk.Button(
            self._run_controls_frame,
            text='weight/weld study',
            command=self.run_weight_weld_study,
            bg='white',
            font='Verdana 10',
            fg='black',
        )
        self.weight_weld_study_button.grid(row=2, column=0, sticky=tk.EW, pady=2)
        weld_delta_row = tk.Frame(self._run_controls_frame)
        weld_delta_row.grid(row=2, column=1, sticky=tk.W, padx=8)
        tk.Label(weld_delta_row, text='delta', font='Verdana 8').grid(row=0, column=0, sticky=tk.W)
        self._ent_weld_study_delta = tk.Entry(
            weld_delta_row,
            textvariable=self._new_weld_study_delta,
            width=5,
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
        self.show_previous_weld_study_button.grid(row=3, column=0, sticky=tk.EW, pady=2)
        self.cost_study_button = tk.Button(
            self._run_controls_frame,
            text='cost study',
            command=self.open_cost_study_window,
            bg='white',
            font='Verdana 10',
            fg='black',
        )
        self.cost_study_button.grid(row=4, column=0, sticky=tk.EW, pady=2)

        tk.Label(self._run_controls_frame, text='Select algorithm', font='Verdana 8 bold') \
            .grid(row=0, column=2, sticky=tk.SW, padx=(16, 0))
        self._ent_algorithm.grid(row=1, column=2, sticky=tk.EW, padx=(16, 0))
        tk.Button(self._run_controls_frame, text='algorithm information', command=self.algorithm_info, bg='white') \
            .grid(row=2, column=2, sticky=tk.EW, padx=(16, 0))
        self._algo_params_frame.grid(row=3, column=2, rowspan=3, sticky=tk.NW, padx=(16, 0))

        self.close_and_save = tk.Button(self._header_frame, text='Return and replace initial structure with optimized',
                                        command=self.save_and_close, bg='green', font='Verdana 10', fg='yellow')
        self.close_and_save.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))

        tk.Button(self._header_frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10') \
            .grid(row=0, column=2, sticky=tk.W, padx=(0, 12))

        # ---------------------------------------------------------------------
        # Optimization objective bias
        # ---------------------------------------------------------------------
        tk.Label(self._objective_frame, text='Optimization objective', font='Verdana 9 bold') \
            .grid(row=0, column=0, columnspan=3, sticky=tk.W)

        tk.Label(self._objective_frame, text='Weight', font='Verdana 7') \
            .grid(row=1, column=0, sticky=tk.S)

        self._weld_bias_slider = tk.Scale(
            self._objective_frame,
            variable=self._new_weld_bias,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=300,
            showvalue=False,
            command=self._update_weld_bias_label,
        )
        self._weld_bias_slider.grid(row=1, column=1, sticky=tk.W, padx=8)

        tk.Label(self._objective_frame, text='Weld consumables', font='Verdana 7') \
            .grid(row=1, column=2, sticky=tk.S)

        self._weld_bias_value_label = tk.Label(
            self._objective_frame,
            text='Weld bias: 0.0',
            font='Verdana 8 bold',
        )
        self._weld_bias_value_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(4, 0))

        self._weld_bias_info_label = tk.Label(
            self._objective_frame,
            text=self._get_weld_bias_text(),
            font='Verdana 7',
            wraplength=470,
            justify=tk.LEFT,
        )
        self._weld_bias_info_label.grid(row=3, column=0, columnspan=3, sticky=tk.W)

        weld_metric_row = tk.Frame(self._objective_frame)
        weld_metric_row.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(4, 0))
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
            variable=self._new_include_builtup_weld
        ).grid(row=0, column=1, sticky=tk.W, padx=(16, 0))

        tk.Label(
            weld_metric_row,
            text='Include web-to-flange weld for built-up stiffeners',
            font='Verdana 7',
            wraplength=300,
            justify=tk.LEFT,
        ).grid(row=0, column=2, sticky=tk.W)

        # Runtime estimate belongs to the optimization objective block.
        self._runnig_time_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))

        self._new_weld_bias.trace_add('write', self._update_weld_bias_label)
        self._new_weld_metric.trace_add('write', self._update_weld_bias_label)

        # Stress scaling
        self._new_fup = tk.DoubleVar()
        self._new_fup.set(0.5)
        self._new_fdwn = tk.DoubleVar()
        self._new_fdwn.set(1)

        tk.Label(self._stress_frame, text='Factor when scaling stresses up, fup') \
            .grid(row=0, column=3, sticky=tk.W, padx=(40, 8))
        ent_fup = tk.Entry(self._stress_frame, textvariable=self._new_fup, width=10)
        ent_fup.grid(row=0, column=4, sticky=tk.W)
        tk.Label(self._stress_frame, text='Factor when scaling stresses up, fdown') \
            .grid(row=1, column=3, sticky=tk.W, padx=(40, 8))
        ent_fdwn = tk.Entry(self._stress_frame, textvariable=self._new_fdwn, width=10)
        ent_fdwn.grid(row=1, column=4, sticky=tk.W)

        self._toggle_btn = tk.Button(self._header_frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg='salmon')
        self._toggle_btn.grid(row=0, column=3, sticky=tk.W, padx=(0, 12))
        self._toggle_object, self._filez = self._initial_structure_obj, None
        self.selected_algorithm(None)
        self.draw_properties()
        self.update_running_time()

        main_application.Application.draw_cylinder(text_size='Verdana 8 bold',
                                                   canvas=self._canvas_opt,
                                                   CylObj=self._initial_cylinder_obj,
                                                   start_x_cyl=350, start_y_cyl=300, text_x=230,
                                                   text_y=110)

    def selected_algorithm(self, event):
        '''
        Action when selecting an algorithm.
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

        elif self._new_algorithm.get() == 'scipy_de cylinder':
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

        self.schedule_running_time_update()

    def _set_conical_optimizer_shell_defaults(self):
        """Keep cone geometry explicit in the cylinder optimizer shell slots."""
        try:
            shell = self._initial_cylinder_obj.get_x_opt()[0]
        except Exception:
            return

        for idx, value in enumerate(shell):
            if idx == 0:
                continue
            try:
                value_mm = 0 if value is None or np.isnan(value) else float(value) * 1000
            except Exception:
                value_mm = 0
            for bounds_idx in [0, 2]:
                try:
                    self._new_geo_data[0][bounds_idx][idx].set(value_mm)
                except Exception:
                    pass
            try:
                self._new_geo_data[0][1][idx].set(0)
            except Exception:
                pass

    def modify_structure_object(self):
        ''' Chaning parameters in the structure object before running. '''
        pass

    def _get_weld_bias_for_optimization(self):
        """
        Return weld consumable bias in range [0, 1].

        0.0 = pure weight optimization.
              optimize.py should not perform weld consumable calculations.
        1.0 = pure estimated weld consumable optimization.
        """
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
        """
        User-readable explanation for the current weld bias.
        """
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
        """
        Refresh objective labels when slider changes.
        """
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

    def _get_fatigue_pressure_tuple(self):
        if self._fatigue_pressure is None:
            return None

        return ((self._fatigue_pressure['p_ext']['loaded'], self._fatigue_pressure['p_ext']['ballast'],
                 self._fatigue_pressure['p_ext']['part']),
                (self._fatigue_pressure['p_int']['loaded'], self._fatigue_pressure['p_int']['ballast'],
                 self._fatigue_pressure['p_int']['part']))

    def _prepare_cylinder_for_optimization(self):
        self._new_sasd.set(self._new_sasd.get())
        self._new_smsd.set(self._new_smsd.get())
        self._new_tTsd.set(self._new_tTsd.get())
        self._new_tQsd.set(self._new_tQsd.get())
        self._new_design_pressure.set(self._new_design_pressure.get())
        self._new_shsd.set(self._new_shsd.get())

        self._initial_cylinder_obj.sasd = self._new_sasd.get()
        self._initial_cylinder_obj.smsd = self._new_smsd.get()
        self._initial_cylinder_obj.tTsd = self._new_tTsd.get()
        self._initial_cylinder_obj.tQsd = self._new_tQsd.get()
        self._initial_cylinder_obj.psd = self._new_design_pressure.get()
        self._initial_cylinder_obj.shsd = self._new_shsd.get()

    def _run_optimizer_with_weld_bias(self, weld_bias, cost_factors=None):
        self._prepare_cylinder_for_optimization()
        return op.run_optmizataion(initial_structure_obj=self._initial_cylinder_obj,
                                   min_var=self.get_lower_bounds(),
                                   max_var=self.get_upper_bounds(),
                                   lateral_pressure=self._new_design_pressure.get(),
                                   deltas=self.get_deltas(),
                                   algorithm=self._new_algorithm.get(),
                                   trials=self._new_algorithm_random_trials.get(),
                                   fatigue_obj=self._fatigue_object,
                                   fat_press_ext_int=self._get_fatigue_pressure_tuple(),
                                   slamming_press=self._new_slamming_pressure.get(),
                                   predefined_stiffener_iter=self._predefined_stiffener_iter,
                                   processes=self._new_processes.get(),
                                   use_weight_filter=True,
                                   fdwn=self._new_fdwn.get(),
                                   fup=self._new_fup.get(),
                                   cylinder=True,
                                   weld_bias=weld_bias,
                                   builtup_stiffener=self._new_include_builtup_weld.get(),
                                   weld_metric=self._get_weld_metric_for_optimization(),
                                   cost_factors=cost_factors)

    def open_cost_study_window(self):
        cost_window = tk.Toplevel(self._frame)
        cost_window.title('Cylinder cost study')
        cost_window.geometry('360x170')
        cost_window.grab_set()

        steel_cost = tk.DoubleVar()
        weld_cost = tk.DoubleVar()
        steel_cost.set(1.0)
        weld_cost.set(1.0)

        tk.Label(cost_window, text='Steel cost per kg').grid(row=0, column=0, sticky=tk.W, padx=20, pady=(20, 4))
        tk.Entry(cost_window, textvariable=steel_cost, width=12).grid(row=0, column=1, sticky=tk.W, pady=(20, 4))
        tk.Label(cost_window, text='Weld cost per ' + self._get_weld_metric_unit()) \
            .grid(row=1, column=0, sticky=tk.W, padx=20, pady=4)
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

        tk.Button(cost_window, text='Run cost optimization', command=run_cost_study, bg='white') \
            .grid(row=2, column=0, sticky=tk.EW, padx=20, pady=(16, 8))
        tk.Button(cost_window, text='Cancel', command=cost_window.destroy, bg='white') \
            .grid(row=2, column=1, sticky=tk.EW, pady=(16, 8))

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
        self._canvas_opt.delete('all')
        main_application.Application.draw_cylinder(text_size='Verdana 8 bold',
                                                   canvas=self._canvas_opt,
                                                   CylObj=self._opt_results[0],
                                                   start_x_cyl=350, start_y_cyl=300, text_x=230,
                                                   text_y=110)

        result_x = self._opt_results[0].get_x_opt()
        result_weight = op.calc_weight_cylinder(result_x)
        result_weld = op.calc_weld_objective_cylinder(
            result_x,
            include_web_to_flange=self._new_include_builtup_weld.get(),
            weld_metric=self._get_weld_metric_for_optimization(),
        )
        result_cost = cost_factors['steel'] * result_weight + cost_factors['weld'] * result_weld
        steel_cost = cost_factors['steel'] * result_weight
        weld_cost = cost_factors['weld'] * result_weld
        self._result_label.config(
            text='Cost optimization result | Cost: ' + str(round(result_cost, 2))
                 + ' | Weight: ' + str(round(result_weight, 1)) + ' kg'
                 + ' | ' + self._get_weld_metric_text() + ': ' + str(round(result_weld, 3))
                 + ' ' + self._get_weld_metric_unit()
        )
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
        shell, long_stf, ring_stf, ring_frame = result_x
        return {
            'title': 'Cylinder cost study report',
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
                ('Shell thickness [mm]', self._format_study_value(shell[0] * 1000, 2)),
                ('Shell radius [m]', self._format_study_value(shell[1], 3)),
                ('Ring spacing [mm]', self._format_study_value(shell[2] * 1000, 2)),
                ('Shell length [mm]', self._format_study_value(shell[3] * 1000, 2)),
                ('Total length [mm]', self._format_study_value(shell[4] * 1000, 2)),
                ('Longitudinal spacing [mm]', self._format_study_value(long_stf[0] * 1000, 2)),
                ('Longitudinal web height [mm]', self._format_study_value(long_stf[2] * 1000, 2)),
                ('Longitudinal web thickness [mm]', self._format_study_value(long_stf[3] * 1000, 2)),
                ('Longitudinal flange width [mm]', self._format_study_value(long_stf[4] * 1000, 2)),
                ('Longitudinal flange thickness [mm]', self._format_study_value(long_stf[5] * 1000, 2)),
                ('Ring stiffener web height [mm]', self._format_study_value(ring_stf[2] * 1000, 2)),
                ('Ring stiffener web thickness [mm]', self._format_study_value(ring_stf[3] * 1000, 2)),
                ('Ring frame web height [mm]', self._format_study_value(ring_frame[2] * 1000, 2)),
                ('Ring frame web thickness [mm]', self._format_study_value(ring_frame[3] * 1000, 2)),
            ],
            'field_size': [
                ('Cylinder radius used [m]', self._format_study_value(shell[1], 3)),
                ('Distance between rings used [mm]', self._format_study_value(shell[2] * 1000, 2)),
                ('Shell length used [mm]', self._format_study_value(shell[3] * 1000, 2)),
                ('Total cylinder length used [mm]', self._format_study_value(shell[4] * 1000, 2)),
                ('Design lateral pressure used [Pa]', self._format_study_value(self._new_design_pressure.get(), 3)),
            ],
        }

    def _show_cost_study_report(self, report):
        result_window = tk.Toplevel(self._frame)
        result_window.title(report.get('title', 'Cylinder cost study report'))
        result_window.geometry('1220x660')

        tk.Label(
            result_window,
            text='Cylinder cost optimization report',
            font='Verdana 12 bold',
        ).pack(side=tk.TOP, anchor='w', padx=10, pady=(10, 4))

        tk.Label(
            result_window,
            text='Objective = steel cost per kg * weight + weld cost per '
                 + self._get_weld_metric_unit() + ' * ' + self._get_weld_metric_text() + '.',
            font='Verdana 8',
            wraplength=1180,
            justify=tk.LEFT,
        ).pack(side=tk.TOP, anchor='w', padx=10, pady=(0, 8))

        table_frame = tk.Frame(result_window)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ('item', 'value')
        summary_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=16)
        geometry_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=16)
        field_size_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=16)

        for tree, heading in (
                (summary_tree, 'Cost and run data'),
                (geometry_tree, 'Optimized geometry'),
                (field_size_tree, 'Optimization field size')):
            tree.heading('item', text=heading)
            tree.heading('value', text='Value')
            tree.column('item', width=270, anchor=tk.W)
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
            # self._result_label.config(text=self._opt_results[0].__str__)
            self._canvas_opt.delete('all')

            main_application.Application.draw_cylinder(text_size='Verdana 8 bold',
                                                       canvas=self._canvas_opt,
                                                       CylObj=self._opt_results[0],
                                                       start_x_cyl=350, start_y_cyl=300, text_x=230,
                                                       text_y=110)
            self._new_sasd.set(self._opt_results[0].sasd)
            self._new_smsd.set(self._opt_results[0].smsd)
            self._new_tTsd.set(self._opt_results[0].tTsd)
            self._new_tQsd.set(self._opt_results[0].tQsd)
            self._new_design_pressure.set(self._opt_results[0].psd)
            self._new_shsd.set(self._opt_results[0].shsd)

            result_text = 'Optimization result'
            if self._get_weld_bias_for_optimization() > 0.0:
                result_text += (
                        ' | Weld bias: '
                        + str(round(self._get_weld_bias_for_optimization(), 2))
                        + ' | Weld metric: '
                        + self._get_weld_metric_text()
                        + ' | Built-up weld: '
                        + str(bool(self._new_include_builtup_weld.get()))
                )
            self._result_label.config(text=result_text)
            # self.draw_properties()
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
            'shell_thk': None,
            'radius': None,
            'long_s': None,
            'long_web_h': None,
            'ring_web_h': None,
            'frame_web_h': None,
            'elapsed': elapsed_seconds,
            'status': 'No result',
        }

        if opt_results is None or len(opt_results) == 0 or opt_results[0] is None:
            return row

        result_x = opt_results[0].get_x_opt()

        try:
            row['weight'] = op.calc_weight_cylinder(result_x)
        except Exception:
            row['weight'] = None

        try:
            row['weld'] = op.calc_weld_objective_cylinder(
                result_x,
                include_web_to_flange=self._new_include_builtup_weld.get(),
                weld_metric=self._get_weld_metric_for_optimization(),
            )
        except Exception:
            row['weld'] = None

        row['shell_thk'] = result_x[0][0] * 1000
        row['radius'] = result_x[0][1]
        row['long_s'] = result_x[1][0] * 1000 if sum(result_x[1][0:6]) != 0 else None
        row['long_web_h'] = result_x[1][2] * 1000 if sum(result_x[1][0:6]) != 0 else None
        row['ring_web_h'] = result_x[2][2] * 1000 if sum(result_x[2][0:6]) != 0 else None
        row['frame_web_h'] = result_x[3][2] * 1000 if sum(result_x[3][0:6]) != 0 else None
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
        result_window.title('Cylinder weight/weld study')
        result_window.geometry('1180x720')

        table_frame = tk.Frame(result_window)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = (
            'bias', 'weight', 'weld', 'shell_thk', 'radius',
            'long_s', 'long_web_h', 'ring_web_h', 'frame_web_h', 'elapsed', 'status'
        )
        weld_heading = rows[0].get('weld_heading', 'Weld [kg]') if len(rows) > 0 else 'Weld [kg]'
        weld_axis_label = rows[0].get('weld_axis_label', 'Weld consumables [kg]') if len(rows) > 0 \
            else 'Weld consumables [kg]'
        headings = {
            'bias': 'Bias',
            'weight': 'Weight [kg]',
            'weld': weld_heading,
            'shell_thk': 'shell t [mm]',
            'radius': 'radius [m]',
            'long_s': 'long s [mm]',
            'long_web_h': 'long h [mm]',
            'ring_web_h': 'ring h [mm]',
            'frame_web_h': 'frame h [mm]',
            'elapsed': 'Time [s]',
            'status': 'Status',
        }

        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=100 if column not in ('weight', 'weld', 'status') else 115, anchor=tk.CENTER)

        for row in rows:
            tree.insert(
                '',
                tk.END,
                values=(
                    self._format_study_value(row['bias'], 2),
                    self._format_study_value(row['weight'], 1),
                    self._format_study_value(row['weld'], 3),
                    self._format_study_value(row['shell_thk'], 1),
                    self._format_study_value(row['radius'], 3),
                    self._format_study_value(row['long_s'], 1),
                    self._format_study_value(row['long_web_h'], 1),
                    self._format_study_value(row['ring_web_h'], 1),
                    self._format_study_value(row['frame_web_h'], 1),
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
            title='Cylinder weight/weld study',
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
        Fast count equivalent to the optimizer's discrete range, without
        generating combinations.
        """
        try:
            lower = float(lower)
            upper = float(upper)
            delta = float(delta)
        except Exception:
            return 1

        if upper < lower:
            return 0

        if delta <= 0.0:
            return 1 if abs(upper - lower) < 1e-12 else 0

        if abs(upper - lower) < 1e-12:
            return 1

        values = np.arange(lower, upper + delta, delta)
        return int(np.count_nonzero(values <= upper + abs(delta) * 1e-9))

    def _count_cylinder_component_combinations(self, idx, lower, upper, delta):
        """
        Count combinations for one cylinder component.

        The optimizer uses a zero tuple for inactive components where all lower
        values are zero. Those components contribute one combination.
        """
        try:
            if idx != 0 and not self._map_type_idx.get(idx, False):
                return 1
        except Exception:
            pass

        try:
            if sum(abs(float(v)) for v in lower) == 0.0:
                return 1
        except Exception:
            pass

        if idx != 0 and self._predefined_stiffener_iter is not None:
            n0 = self._count_steps(lower[0], upper[0], delta[0])
            n1 = self._count_steps(lower[1], upper[1], delta[1])
            return max(n0, 1) * max(n1, 1) * len(self._predefined_stiffener_iter)

        count = 1
        component_values = zip(lower[:8], upper[:8], delta[:8]) if idx == 0 else zip(lower[:6], upper[:6], delta[:6])
        for low, up, dlt in component_values:
            n_steps = self._count_steps(low, up, dlt)
            count *= max(n_steps, 0)

        return count

    def get_running_time(self):
        """
        Estimate running time without generating all combinations.

        This is intentionally lightweight because it is triggered from GUI
        variable changes.
        """
        try:
            algorithm = self._new_algorithm.get()
        except TclError:
            return 0, 0

        if algorithm in ['random', 'random_no_delta', 'scipy_de cylinder']:
            try:
                number_of_combinations = int(self._new_algorithm_random_trials.get())
                seconds = number_of_combinations * self.running_time_per_item['RP']
                return int(seconds), number_of_combinations
            except Exception:
                return 0, 0

        try:
            lower = self.get_lower_bounds()
            upper = self.get_upper_bounds()
            deltas = self.get_deltas()
        except Exception:
            return 0, 0

        number_of_combinations = 1
        for idx in range(len(lower)):
            number_of_combinations *= self._count_cylinder_component_combinations(
                idx,
                lower[idx],
                upper[idx],
                deltas[idx],
            )

        seconds = number_of_combinations * self.running_time_per_item['RP']
        try:
            if 0.0 < self._get_weld_bias_for_optimization() < 1.0:
                seconds *= self.running_time_no_filter_factor
        except Exception:
            pass

        return int(seconds), int(number_of_combinations)

    def _get_optimizer_count_label(self):
        try:
            if self._new_algorithm.get() == 'scipy_de cylinder':
                return 'Estimated max evaluations'
        except Exception:
            pass
        return 'Estimated combinations'

    def schedule_running_time_update(self, *args):
        """
        Debounce running-time updates.

        Tkinter variable traces fire on every keystroke. Without debouncing,
        the GUI may repeatedly recompute estimates while the user is still
        typing, which makes the window feel frozen.
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

    def get_deltas(self):
        '''
        Return a numpy array of the deltas.
        :return:
        '''
        all_deltas = list()
        for idx_1, geo_i in enumerate(self._new_geo_data):
            these_deltas = list()
            for idx_3, val in enumerate(geo_i[1]):
                these_deltas.append(val.get() / 1000)
            all_deltas.append(these_deltas)
        return all_deltas

    def update_running_time(self, *args):
        '''
        Estimate the running time of the algorithm.
        '''
        self._running_time_after_id = None

        try:
            seconds, number_of_combinations = self.get_running_time()
            weld_bias = self._get_weld_bias_for_optimization()
            warning_text = ''

            if 0.0 < weld_bias < 1.0:
                warning_text = (
                    '\nWARNING: mixed weight/weld combination disables the initial filter.'
                    '\nEstimate uses no-filter runtime.'
                )
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

    def get_upper_bounds(self):
        '''
        Return an numpy array of upper bounds.
        :return:
        '''
        all_upper = list()
        for idx_1, geo_i in enumerate(self._new_geo_data):
            these_upper = list()
            for idx_3, val in enumerate(geo_i[0]):
                these_upper.append(val.get() / 1000)
            all_upper.append(these_upper)
        return all_upper

    def get_lower_bounds(self):
        '''
        Return an numpy array of lower bounds.
        :return:
        '''
        all_lower = list()
        for idx_1, geo_i in enumerate(self._new_geo_data):
            these_lower = list()
            for idx_3, val in enumerate(geo_i[2]):
                these_lower.append(val.get() / 1000)
            all_lower.append(these_lower)
        return all_lower

    def get_sigmas(self):
        '''
        Returns the stressess.
        :return:
        '''
        return np.array([self._new_sasd.get(), self._new_smsd.get(),
                         self._new_tTsd.get(), self._new_tQsd.get(),
                         self._new_design_pressure.get(), self._new_shsd.get()])

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
        # self.checkered(10)
        ctr_x = self._canvas_dim[0] / 2
        ctr_y = self._canvas_dim[1] / 2 + 200
        m = self._draw_scale
        init_color, init_stipple = 'blue', 'gray12'
        opt_color, opt_stippe = 'red', 'gray12'
        # self._canvas_opt.create_rectangle(0,0,self._canvas_dim[0]+10,80,fill='white')
        # self._canvas_opt.create_line(10,10,30,10,fill = init_color,width=5)

        if self._opt_runned:

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_s() / 2, ctr_y,
                                              ctr_x + m * self._opt_results[0].get_s() / 2,
                                              ctr_y - m * self._opt_results[0].get_pl_thk(), fill=opt_color,
                                              stipple=opt_stippe)

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_web_thk() / 2, ctr_y -
                                              m * self._opt_results[0].get_pl_thk(),
                                              ctr_x + m * self._opt_results[0].get_web_thk() / 2,
                                              ctr_y - m * (self._opt_results[0].get_web_h() + self._opt_results[
                                                  0].get_pl_thk())
                                              , fill=opt_color, stipple=opt_stippe)
            if self._opt_results[0].get_stiffener_type() not in ['L', 'L-bulb']:
                self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_fl_w() / 2, ctr_y
                                                  - m * (self._opt_results[0].get_pl_thk() + self._opt_results[
                    0].get_web_h()),
                                                  ctr_x + m * self._opt_results[0].get_fl_w() / 2, ctr_y -
                                                  m * (self._opt_results[0].get_pl_thk() + self._opt_results[
                        0].get_web_h() +
                                                       self._opt_results[0].get_fl_thk()),
                                                  fill=opt_color, stipple=opt_stippe)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_web_thk() / 2, ctr_y
                                                  - m * (self._opt_results[0].get_pl_thk() + self._opt_results[
                    0].get_web_h()),
                                                  ctr_x + m * self._opt_results[0].get_fl_w(), ctr_y -
                                                  m * (self._opt_results[0].get_pl_thk() + self._opt_results[
                        0].get_web_h() +
                                                       self._opt_results[0].get_fl_thk()),
                                                  fill=opt_color, stipple=opt_stippe)

            self._canvas_opt.create_line(10, 50, 30, 50, fill=opt_color, width=5)
            self._canvas_opt.create_text(270, 50,
                                         text='Optimized - Pl.: ' + str(round(self._opt_results[0].get_s() * 1000, 1))
                                              + 'x' + str(round(self._opt_results[0].get_pl_thk() * 1000, 1)) +
                                              ' Stf.: ' + str(round(self._opt_results[0].get_web_h() * 1000, 1)) +
                                              'x' + str(round(self._opt_results[0].get_web_thk() * 1000, 1)) + '+' +
                                              str(round(self._opt_results[0].get_fl_w() * 1000, 1)) +
                                              'x' + str(round(self._opt_results[0].get_fl_thk() * 1000, 1)),
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
            self.app.on_close_opt_cyl_window(self._opt_results)
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
                                    'SCIPY_DE CYLINDER:\n'
                                    '           Uses SciPy differential evolution to sample snapped cylinder\n'
                                    '           candidates from the current bounds and deltas.\n'
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
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg='salmon')

            predefined_stiffener_iter = []
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg='salmon')
            self._toggle_btn.config(bg='lightgreen')

            predefined_stiffener_iter = []
            open_files = askopenfilenames(parent=self._frame, title='Choose files to open', initialdir=self._root_dir)
            if self._initial_cylinder_obj.LongStfObj is not None:
                predefined_stiffener_iter = hlp.helper_read_section_file(files=list(open_files),
                                                                         obj=self._initial_cylinder_obj.LongStfObj)

        if predefined_stiffener_iter == []:
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg='salmon')

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
    my_app = CreateOptimizeCylinderWindow(master=root)
    root.mainloop()




