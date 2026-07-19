# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError
from tkinter.ttk import Progressbar
from tkinter import messagebox
from tkinter.filedialog import askopenfilenames
from multiprocessing import Pool, cpu_count
import os
import numpy as np

try:
    import anystruct.main_application
    import anystruct.optimize as op
    import anystruct.example_data as test
    import anystruct.line_structure as line_structure
    import anystruct.ml_models as ml_models
    from anystruct.calc_structure import *
    import anystruct.calc_structure as calc
    from anystruct.helper import *
    import anystruct.optimize as opt
except ModuleNotFoundError:
    import ANYstructure.anystruct.main_application
    import ANYstructure.anystruct.optimize as op
    import ANYstructure.anystruct.example_data as test
    import ANYstructure.anystruct.line_structure as line_structure
    import ANYstructure.anystruct.ml_models as ml_models
    from ANYstructure.anystruct.calc_structure import *
    import ANYstructure.anystruct.calc_structure as calc
    from ANYstructure.anystruct.helper import *
    import ANYstructure.anystruct.optimize as opt


def helper_harmonizer_multi(iterator):
    """
    Multiprocessing helper for harmonized optimization.

    The ML result payload is selected from the active constraint:
        chk[8] -> ML-CL, deactivated
        chk[9] -> ML-Numeric result, expected [buckling_uf, ultimate_uf, valid_prediction]
    """

    this_check, master_x = list(), None
    use_semi_analytical = len(iterator['info']['checks']) > 7 and iterator['info']['checks'][7]
    use_ml_numeric = len(iterator['info']['checks']) > 9 and iterator['info']['checks'][9]
    use_ml_cl = len(iterator['info']['checks']) > 8 and iterator['info']['checks'][8]

    for slave_line in iterator['info']['lines']:
        lateral_press = iterator['info'][slave_line]['lateral pressure']
        fat_press = iterator['info'][slave_line]['fatigue pressure']
        fat_obj = iterator['info'][slave_line]['fatigue object']
        slamming_pressure = iterator['info'][slave_line]['slamming pressure']
        chk_calc_obj = iterator['info'][slave_line]['chk_calc_obj']
        master_x = list(iterator['x'])

        if use_semi_analytical:
            ml_result = iterator['info'][slave_line].get('SemiAnalytical', [float('inf'), float('inf'), 0, 0.87])
        elif use_ml_numeric:
            ml_result = iterator['info'][slave_line].get('ML-Numeric', [float('inf'), float('inf'), 0])
        elif use_ml_cl:
            ml_result = [0, 0]
        else:
            ml_result = None

        fup = iterator['info'][slave_line]['fup']
        fdwn = iterator['info'][slave_line]['fdwn']

        if iterator['info']['keep spacing']:
            x = [chk_calc_obj.get_s()] + master_x[1:] + [chk_calc_obj.span, chk_calc_obj.girder_lg]
        else:
            x = master_x + [chk_calc_obj.span, chk_calc_obj.girder_lg]

        chk_any = op.any_constraints_all(
            x=x,
            obj=chk_calc_obj,
            lat_press=lateral_press,
            init_weight=float('inf'),
            side='p',
            chk=iterator['info']['checks'],
            fat_dict=None if fat_obj is None else fat_obj.get_fatigue_properties(),
            fat_press=fat_press,
            slamming_press=slamming_pressure,
            PULSrun=None,
            print_result=False,
            fdwn=fdwn,
            fup=fup,
            ml_results=ml_result,
            weld_bias=iterator['info'].get('weld bias', 0.0),
            builtup_stiffener=iterator['info'].get('builtup stiffener', False),
            weld_metric=iterator['info'].get('weld metric', 'weld_consumables'),
        )
        this_check.append(chk_any[0])

    if all(this_check) and master_x is not None:
        return tuple(master_x)
    else:
        return None


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
            self._normal_pressure = test.get_random_pressure()
            self._root_dir = os.path.dirname(os.path.abspath(__file__))
            image_dir = self._root_dir + '\\images\\'
            self._active_lines = []
            self._ML_buckling = ml_models.load_buckling_models((self._root_dir,))
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
            self._active_lines = app._multiselect_lines
            self._ML_buckling = app._ML_buckling

        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1850x1250')
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

        # Gridded layout scaffolding: header on top; bounds table (left) and
        # run/algorithm controls (right); the line-selection canvas bottom
        # left with the objective, checks and result canvas on the right.
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(2, weight=1)
        self._header_frame = tk.Frame(self._frame)
        self._header_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(8, 4))
        self._bounds_frame = tk.Frame(self._frame)
        self._bounds_frame.grid(row=1, column=0, sticky=tk.NW, padx=10)
        self._controls_frame = tk.Frame(self._frame)
        self._controls_frame.grid(row=1, column=1, sticky=tk.NW, padx=(10, 10))
        self._select_canvas_holder = tk.Frame(self._frame)
        self._select_canvas_holder.grid(row=2, column=0, rowspan=2, sticky=tk.NW, padx=10, pady=(8, 8))
        self._right_column = tk.Frame(self._frame)
        self._right_column.grid(row=2, column=1, rowspan=2, sticky=tk.NW, padx=(10, 10), pady=(8, 8))
        self._objective_frame = tk.Frame(self._right_column)
        self._objective_frame.grid(row=0, column=0, sticky=tk.NW)
        self._opt_canvas_holder = tk.Frame(self._right_column)
        self._opt_canvas_holder.grid(row=1, column=0, sticky=tk.NW, pady=(8, 0))
        self._checks_frame = tk.Frame(self._right_column)
        self._checks_frame.grid(row=2, column=0, sticky=tk.NW, pady=(8, 0))

        self._opt_actual_running_time = tk.Label(self._controls_frame, text='')

        algorithms = ('anysmart', 'scipy_de', 'random', 'random_no_delta')

        tk.Label(self._header_frame, text='-- Structural optimizer for multiple selections --',
                 font='Verdana 15 bold').grid(row=0, column=0, sticky=tk.W, padx=(0, 20))

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
        self._new_weld_bias = tk.DoubleVar()
        self._new_weld_metric = tk.StringVar()
        self._new_include_builtup_weld = tk.BooleanVar()
        self._running_time_after_id = None
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

        ent_w = 10
        # Dynamic per-algorithm parameter controls live in their own frame so
        # they can be shown/hidden with grid/grid_remove.
        self._algo_params_frame = tk.Frame(self._controls_frame)
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
        self._ent_span = tk.Entry(self._frame, textvariable=self._new_span, width=ent_w)
        self._ent_width_lg = tk.Entry(self._frame, textvariable=self._new_width_lg, width=ent_w)
        self._ent_algorithm = tk.OptionMenu(self._controls_frame, self._new_algorithm, command=self.selected_algorithm,
                                            *algorithms)
        self._ent_random_trials = tk.Entry(self._algo_params_frame, textvariable=self._new_algorithm_random_trials)
        self._ent_delta_spacing = tk.Entry(self._bounds_frame, textvariable=self._new_delta_spacing, width=ent_w)
        self._ent_delta_pl_thk = tk.Entry(self._bounds_frame, textvariable=self._new_delta_pl_thk, width=ent_w)
        self._ent_delta_web_h = tk.Entry(self._bounds_frame, textvariable=self._new_delta_web_h, width=ent_w)
        self._ent_delta_web_thk = tk.Entry(self._bounds_frame, textvariable=self._new_delta_web_thk, width=ent_w)
        self._ent_delta_fl_w = tk.Entry(self._bounds_frame, textvariable=self._new_delta_fl_w, width=ent_w)
        self._ent_delta_fl_thk = tk.Entry(self._bounds_frame, textvariable=self._new_delta_fl_thk, width=ent_w)

        pso_width = 10
        self._ent_swarm_size = tk.Entry(self._algo_params_frame, textvariable=self._new_swarm_size, width=pso_width)
        self._ent_omega = tk.Entry(self._algo_params_frame, textvariable=self._new_omega, width=pso_width)
        self._ent_phip = tk.Entry(self._algo_params_frame, textvariable=self._new_phip, width=pso_width)
        self._ent_phig = tk.Entry(self._algo_params_frame, textvariable=self._new_phig, width=pso_width)
        self._ent_maxiter = tk.Entry(self._algo_params_frame, textvariable=self._new_maxiter, width=pso_width)
        self._ent_minstep = tk.Entry(self._algo_params_frame, textvariable=self._new_minstep, width=pso_width)
        self._ent_minfunc = tk.Entry(self._algo_params_frame, textvariable=self._new_minfunc, width=pso_width)

        start_x, start_y, dx, dy = 20, 70, 100, 40

        self._new_processes = tk.IntVar()
        self._new_processes.set(max(cpu_count() - 1, 1))
        tk.Label(self._header_frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg='silver') \
            .grid(row=0, column=3, sticky=tk.W, padx=(20, 4))
        tk.Entry(self._header_frame, textvariable=self._new_processes, width=12, bg='silver') \
            .grid(row=0, column=4, sticky=tk.W)

        self._prop_canvas_dim = (500, 450)
        self._draw_scale = 500
        self._canvas_opt = tk.Canvas(self._opt_canvas_holder, width=self._prop_canvas_dim[0],
                                     height=self._prop_canvas_dim[1],
                                     background='azure', relief='groove', borderwidth=2)
        self._canvas_opt.grid(row=0, column=0, sticky=tk.NW)
        self._select_canvas_dim = (1000, 720)
        self._canvas_select = tk.Canvas(self._select_canvas_holder, width=self._select_canvas_dim[0],
                                        height=self._select_canvas_dim[1],
                                        background='azure', relief='groove', borderwidth=2)
        self._canvas_select.grid(row=0, column=0, sticky=tk.NW)

        # Labels for the pso
        self._lb_swarm_size = tk.Label(self._algo_params_frame, text='swarm size')
        self._lb_omega = tk.Label(self._algo_params_frame, text='omega')
        self._lb_phip = tk.Label(self._algo_params_frame, text='phip')
        self._lb_phig = tk.Label(self._algo_params_frame, text='phig')
        self._lb_maxiter = tk.Label(self._algo_params_frame, text='maxiter')
        self._lb_minstep = tk.Label(self._algo_params_frame, text='minstep')
        self._lb_minfunc = tk.Label(self._algo_params_frame, text='minfunc')

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
        tk.Label(self._bounds_frame, text='Estimated running time for algorithm: ',
                 font='Verdana 9 bold').grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        self._runnig_time_label = tk.Label(self._bounds_frame, text='', font='Verdana 9 bold')
        self._runnig_time_label.grid(row=4, column=3, sticky=tk.W, pady=(6, 0))
        tk.Label(self._bounds_frame, text='seconds ', font='Verdana 9 bold') \
            .grid(row=4, column=4, sticky=tk.W, pady=(6, 0))
        self._result_label = tk.Label(self._bounds_frame, text='', font='Verdana 9 bold')
        self._result_label.grid(row=5, column=0, columnspan=7, sticky=tk.W, pady=(6, 0))

        # setting default values
        init_dim = float(50)  # mm
        init_thk = float(5)  # mm
        self._new_delta_spacing.set(5)
        self._new_delta_pl_thk.set(init_thk)
        self._new_delta_web_h.set(init_dim)
        self._new_delta_web_thk.set(init_thk)
        self._new_delta_fl_w.set(init_dim)
        self._new_delta_fl_thk.set(init_thk)
        self._new_spacing_upper.set(round(800, 5))
        self._new_spacing_lower.set(round(600, 5))
        self._new_pl_thk_upper.set(round(30, 5))
        self._new_pl_thk_lower.set(round(10, 5))
        self._new_web_h_upper.set(round(500, 5))
        self._new_web_h_lower.set(round(200, 5))
        self._new_web_thk_upper.set(round(30, 5))
        self._new_web_thk_lower.set(round(10, 5))
        self._new_fl_w_upper.set(round(300, 5))
        self._new_fl_w_lower.set(round(100, 5))
        self._new_fl_thk_upper.set(round(30, 5))
        self._new_fl_thk_lower.set(round(10, 5))
        self._new_algorithm.set('anysmart')
        self._new_algorithm_random_trials.set(10000)
        self._new_weld_bias.set(0.0)
        self._new_weld_metric.set('Weld consumables')
        self._new_include_builtup_weld.set(False)
        # Selection of constraints
        self._new_check_sec_mod = tk.BooleanVar()
        self._new_check_min_pl_thk = tk.BooleanVar()
        self._new_check_shear_area = tk.BooleanVar()
        self._new_check_buckling = tk.BooleanVar()
        self._new_check_fatigue = tk.BooleanVar()
        self._new_check_slamming = tk.BooleanVar()
        self._new_check_local_buckling = tk.BooleanVar()
        self._new_check_semi_analytical_buckling = tk.BooleanVar()
        self._new_check_ml_buckling = tk.BooleanVar()
        self._new_check_ml_numeric_buckling = tk.BooleanVar()
        self._new_harmonizer = tk.BooleanVar()
        self._keep_spacing = tk.BooleanVar()

        self._new_check_sec_mod.set(True)
        self._new_check_min_pl_thk.set(True)
        self._new_check_shear_area.set(True)
        self._new_check_buckling.set(True)
        self._new_check_fatigue.set(True)
        self._new_check_slamming.set(False)
        self._new_check_local_buckling.set(True)
        self._new_harmonizer.set(False)
        self._keep_spacing.set(False)
        self._new_check_semi_analytical_buckling.set(False)
        self._new_check_ml_buckling.set(False)
        self._new_check_ml_numeric_buckling.set(False)

        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)

        self._new_delta_spacing.trace_add('write', self.schedule_running_time_update)
        self._new_delta_pl_thk.trace_add('write', self.schedule_running_time_update)
        self._new_delta_web_h.trace_add('write', self.schedule_running_time_update)
        self._new_delta_web_thk.trace_add('write', self.schedule_running_time_update)
        self._new_delta_fl_w.trace_add('write', self.schedule_running_time_update)
        self._new_delta_fl_thk.trace_add('write', self.schedule_running_time_update)
        self._new_spacing_upper.trace_add('write', self.schedule_running_time_update)
        self._new_spacing_lower.trace_add('write', self.schedule_running_time_update)
        self._new_pl_thk_upper.trace_add('write', self.schedule_running_time_update)
        self._new_pl_thk_lower.trace_add('write', self.schedule_running_time_update)
        self._new_web_h_upper.trace_add('write', self.schedule_running_time_update)
        self._new_web_h_lower.trace_add('write', self.schedule_running_time_update)
        self._new_web_thk_upper.trace_add('write', self.schedule_running_time_update)
        self._new_web_thk_lower.trace_add('write', self.schedule_running_time_update)
        self._new_fl_w_upper.trace_add('write', self.schedule_running_time_update)
        self._new_fl_w_lower.trace_add('write', self.schedule_running_time_update)
        self._new_fl_thk_upper.trace_add('write', self.schedule_running_time_update)
        self._new_fl_thk_lower.trace_add('write', self.schedule_running_time_update)
        self._new_algorithm_random_trials.trace_add('write', self.schedule_running_time_update)
        self._new_algorithm.trace_add('write', self.schedule_running_time_update)
        self._keep_spacing.trace_add('write', self.trace_keep_spacing_check)
        self._new_check_semi_analytical_buckling.trace_add('write', self.schedule_running_time_update)
        self._new_check_ml_buckling.trace_add('write', self.schedule_running_time_update)
        self._new_check_ml_numeric_buckling.trace_add('write', self.schedule_running_time_update)
        self._new_weld_bias.trace_add('write', self._update_weld_bias_label)
        self._new_weld_metric.trace_add('write', self._update_weld_bias_label)

        self.running_time_per_item = 1.009943181818182e-5
        self._runnig_time_label.config(text=str(self.get_running_time()))
        self._opt_actual_running_time.grid(row=0, column=0, columnspan=2, sticky=tk.W)
        self.run_button = tk.Button(self._controls_frame, text='RUN OPTIMIZATION!', command=self.run_optimizaion,
                                    bg='red', font='Verdana 10', fg='Yellow')
        self.run_button.grid(row=1, column=0, sticky=tk.EW, pady=2)
        tk.Label(self._controls_frame, text='Select algorithm type --->', font='Verdana 8 bold') \
            .grid(row=2, column=0, sticky=tk.W, pady=2)
        self._ent_algorithm.grid(row=2, column=1, sticky=tk.W, padx=8, pady=2)
        self.algorithm_random_label = tk.Label(self._algo_params_frame, text='Number of trials')
        tk.Button(self._controls_frame, text='algorithm information', command=self.algorithm_info, bg='white') \
            .grid(row=1, column=1, sticky=tk.W, padx=8, pady=2)
        self.run_results = tk.Button(self._controls_frame, text='show calculated', command=self.plot_results,
                                     bg='white', font='Verdana 10', fg='black')
        self.run_results.grid(row=3, column=0, sticky=tk.EW, pady=2)
        self._algo_params_frame.grid(row=2, column=2, rowspan=4, sticky=tk.NW, padx=(16, 0))
        self.close_and_save = tk.Button(self._header_frame,
                                        text='Return and replace with selected optimized structure',
                                        command=self.save_and_close, bg='green', font='Verdana 10 bold', fg='yellow')
        self.close_and_save.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))

        tk.Button(self._header_frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10') \
            .grid(row=0, column=2, sticky=tk.W, padx=(0, 12))

        check_rows = (
            ('Check for minimum section modulus', self._new_check_sec_mod, 'normal'),
            ('Check for minimum plate thk.', self._new_check_min_pl_thk, 'normal'),
            ('Check for minimum shear area', self._new_check_shear_area, 'normal'),
            ('Check for buckling (RP-C201)', self._new_check_buckling, 'normal'),
            ('Check for fatigue (RP-C203)', self._new_check_fatigue, 'normal'),
            ('Check for bow slamming', self._new_check_slamming, 'normal'),
            ('Check for local stf. buckling', self._new_check_local_buckling, 'normal'),
            ('Check for buckling (SemiAnalytical S3/U3)', self._new_check_semi_analytical_buckling, 'normal'),
            ('Check for buckling (ML-CL deactivated)', self._new_check_ml_buckling, 'disabled'),
            ('Check for buckling (ML-Numeric)', self._new_check_ml_numeric_buckling, 'normal'),
        )
        for row, (text, variable, state) in enumerate(check_rows):
            tk.Label(self._checks_frame, text=text).grid(row=row, column=0, sticky=tk.W)
            tk.Checkbutton(self._checks_frame, variable=variable, state=state).grid(row=row, column=1, sticky=tk.W)
        harmonize_row = tk.Frame(self._objective_frame)
        harmonize_row.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))
        tk.Checkbutton(harmonize_row, variable=self._new_harmonizer).grid(row=0, column=0, sticky=tk.W)
        tk.Label(harmonize_row, text='Check to harmonize results. Same stiffener and plate dimensions '
                                     '(defined by largest in opt).', font='Verdana 9 bold', wraplength=460,
                 justify=tk.LEFT).grid(row=0, column=1, sticky=tk.W)
        tk.Checkbutton(harmonize_row, variable=self._keep_spacing).grid(row=1, column=0, sticky=tk.W)
        tk.Label(harmonize_row, text='Check to skip iterating over spacing (respective line spacing used).',
                 font='Verdana 9 bold', wraplength=460, justify=tk.LEFT).grid(row=1, column=1, sticky=tk.W)

        # Optimization objective bias. 0.0 keeps the old weight-only behaviour.
        tk.Label(self._objective_frame, text='Optimization objective', font='Verdana 9 bold') \
            .grid(row=0, column=0, columnspan=3, sticky=tk.W)

        self._weld_bias_slider = tk.Scale(
            self._objective_frame,
            variable=self._new_weld_bias,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=240,
            showvalue=False,
            command=self._update_weld_bias_label,
        )
        self._weld_bias_slider.grid(row=1, column=0, columnspan=2, sticky=tk.W)

        tk.Label(self._objective_frame, text='Weight', font='Verdana 7') \
            .grid(row=2, column=0, sticky=tk.W)
        tk.Label(self._objective_frame, text='Weld consumables', font='Verdana 7') \
            .grid(row=2, column=1, sticky=tk.E)

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
            wraplength=330,
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
        ).grid(row=0, column=1, sticky=tk.W, padx=(16, 0))

        tk.Label(
            weld_metric_row,
            text='Include web-to-flange weld for built-up stiffeners',
            font='Verdana 7',
            wraplength=300,
            justify=tk.LEFT,
        ).grid(row=0, column=2, sticky=tk.W)

        self._toggle_btn = tk.Button(self._controls_frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg='salmon')

        self._toggle_btn.grid(row=4, column=0, sticky=tk.EW, pady=2)
        self._toggle_object, self._filez = None, None

        # Stress scaling
        self._new_fup = tk.DoubleVar()
        self._new_fup.set(0.5)
        self._new_fdwn = tk.DoubleVar()
        self._new_fdwn.set(1)

        fup_row = tk.Frame(self._checks_frame)
        fup_row.grid(row=len(check_rows), column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        tk.Label(fup_row, text='Factor when scaling stresses up, fup').grid(row=0, column=0, sticky=tk.W)
        ent_fup = tk.Entry(fup_row, textvariable=self._new_fup, width=10)
        ent_fup.grid(row=0, column=1, sticky=tk.W, padx=8)
        tk.Label(fup_row, text='Factor when scaling stresses up, fdown').grid(row=1, column=0, sticky=tk.W)
        ent_fdwn = tk.Entry(fup_row, textvariable=self._new_fdwn, width=10)
        ent_fdwn.grid(row=1, column=1, sticky=tk.W, padx=8)

        self.draw_properties()

        # ----------------------------------END OF OPTIMIZE SINGLE COPY-----------------------------------------------
        self.progress_count = tk.IntVar()
        self.progress_count.set(0)
        self.progress_bar = Progressbar(self._controls_frame, orient="horizontal", length=200, mode="determinate",
                                        variable=self.progress_count)
        self.progress_bar.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        self.controls()
        self.draw_select_canvas()
        self._harmonizer_data = {}

    def _get_weld_bias_for_optimization(self):
        """
        Return weld consumable bias in range [0, 1].

        0.0 = pure weight optimization. The optimizer should not perform
              weld-consumable calculations.
        1.0 = pure estimated weld-consumable optimization.
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
        try:
            self._weld_bias_value_label.config(
                text='Weld bias: ' + str(round(self._get_weld_bias_for_optimization(), 2))
            )
            self._weld_bias_info_label.config(text=self._get_weld_bias_text())
        except Exception:
            pass

        try:
            self.schedule_running_time_update()
        except Exception:
            pass

    def _get_objective_warning_text(self):
        weld_bias = self._get_weld_bias_for_optimization()

        if 0.0 < weld_bias < 1.0:
            return '\nWARNING: mixed weight/weld combination disables the initial filter.'

        if weld_bias >= 1.0:
            return '\nPure weld objective: multi-line filter is disabled to preserve harmonizing candidates for ' \
                   + self._get_weld_metric_text() + '.'

        return ''

    def schedule_running_time_update(self, *args):
        """
        Debounce running-time estimate updates. Tkinter variable callbacks fire
        on every keystroke, so the estimate should only run after typing pauses.
        """
        try:
            if self._running_time_after_id is not None:
                self._frame.after_cancel(self._running_time_after_id)
        except Exception:
            pass

        self._running_time_after_id = self._frame.after(500, self.update_running_time)

    def _count_steps(self, lower, upper, delta):
        """
        Fast count equivalent to len(np.arange(lower, upper + delta, delta)),
        without allocating the full array.
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

    def _objective_for_x(self, x, line_structure_obj=None):
        """
        Mixed objective for harmonizing multi-line results.

        weld_bias == 0 keeps the old area/weight-style behaviour and avoids
        weld-consumable calculations.
        """
        weld_bias = self._get_weld_bias_for_optimization()

        if line_structure_obj is None:
            return sum(op.get_field_tot_area(x))

        if weld_bias <= 0.0:
            return op.calc_weight(x)

        try:
            weight = op.calc_weight(x)
        except Exception:
            weight = float('inf')

        try:
            stiffener_type = (
                line_structure_obj.Stiffener.get_stiffener_type()
                if line_structure_obj.Stiffener is not None else 'T'
            )
            weld = op.calc_weld_objective(
                x,
                stiffener_type=stiffener_type,
                include_web_to_flange=self._new_include_builtup_weld.get(),
                weld_metric=self._get_weld_metric_for_optimization(),
            )
        except Exception:
            weld = float('inf')

        return (1.0 - weld_bias) * weight + weld_bias * weld

    def trace_keep_spacing_check(self, *args):
        if self._keep_spacing.get():
            self._ent_spacing_lower.configure({"background": "red"})
            self._ent_delta_spacing.configure({"background": "red"})
            self._ent_spacing_upper.configure({"background": "red"})

    def selected_algorithm(self, event):
        '''
        Action when selecting an algorithm in the optionm menu.
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

    def get_pressure_input(self, line):
        if __name__ == '__main__':
            lateral_press = self._normal_pressure
            fat_press = self._fatigue_pressure
            slamming_pressure = self._slamming_pressure
            fat_obj = self._fatigue_object
        else:
            lateral_press = self.app.get_highest_pressure(line)['normal'] / 1e6

            fat_obj = line_structure.fatigue(self.app._line_to_struc[line])
            if fat_obj is not None:
                try:
                    fat_press = self.app.get_fatigue_pressures(line, fat_obj.get_accelerations())
                except AttributeError:
                    fat_press = None
            else:
                fat_press = {'p_ext': {'loaded': 0, 'ballast': 0, 'part': 0},
                             'p_int': {'loaded': 0, 'ballast': 0, 'part': 0}}

            try:
                if self.app.get_highest_pressure(line)['slamming'] is None:
                    slamming_pressure = 0
                else:
                    slamming_pressure = self.app.get_highest_pressure(line)['slamming']
            except (KeyError, AttributeError):
                slamming_pressure = 0

        fat_press = ((fat_press['p_ext']['loaded'], fat_press['p_ext']['ballast'],
                      fat_press['p_ext']['part']),
                     (fat_press['p_int']['loaded'], fat_press['p_int']['ballast'],
                      fat_press['p_int']['part']))
        return {'lateral pressure': lateral_press, 'fatigue pressure': fat_press,
                'slamming pressure': slamming_pressure, 'fatigue object': fat_obj}

    def run_optimizaion(self):
        '''
        Function when pressing the optimization botton inside this window.
        :return:
        '''
        self.run_button.config(bg='white')
        self._opt_results = {}
        t_start = time.time()

        self.progress_bar.config(maximum=len(self._active_lines))
        self._opt_actual_running_time.config(text='')

        contraints = (self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
                      self._new_check_shear_area.get(), self._new_check_buckling.get(),
                      self._new_check_fatigue.get(), self._new_check_slamming.get(),
                      self._new_check_local_buckling.get(), self._new_check_semi_analytical_buckling.get(),
                      self._new_check_ml_buckling.get(),
                      self._new_check_ml_numeric_buckling.get())

        self.pso_parameters = (self._new_swarm_size.get(), self._new_omega.get(), self._new_phip.get(),
                               self._new_phig.get(), self._new_maxiter.get(), self._new_minstep.get(),
                               self._new_minfunc.get())

        max_min_span = None

        self.progress_count.set(0)
        counter = 0
        found_files = self._filez
        selected_mat_fac = self._get_selected_material_factor()

        for line in self._active_lines:
            init_obj = self._line_structure(line)
            self._apply_material_factor_to_structure(init_obj, selected_mat_fac)

            if __name__ == '__main__':
                lateral_press = 200  # for testing
                fat_obj = test.get_fatigue_object()
                fat_press = test.get_fatigue_pressures()
                slamming_pressure = test.get_slamming_pressure()
                fat_press = ((fat_press['p_ext']['loaded'], fat_press['p_ext']['ballast'],
                              fat_press['p_ext']['part']),
                             (fat_press['p_int']['loaded'], fat_press['p_int']['ballast'],
                              fat_press['p_int']['part']))

            else:
                input_pressures = self.get_pressure_input(line)
                lateral_press = input_pressures['lateral pressure']
                fat_press = input_pressures['fatigue pressure']
                slamming_pressure = input_pressures['slamming pressure']
                fat_obj = input_pressures['fatigue object']

            if self._toggle_btn.config('relief')[-1] == 'sunken':
                found_files, predefined_stiffener_iter = self.toggle(found_files=found_files, obj=init_obj,
                                                                     iterating=True)
            else:
                predefined_stiffener_iter = None

            self._opt_results[line] = list(op.run_optmizataion(init_obj, self.get_lower_bounds(init_obj),
                                                               self.get_upper_bounds(init_obj),
                                                               lateral_press, self.get_deltas(),
                                                               algorithm=self._new_algorithm.get(),
                                                               trials=self._new_algorithm_random_trials.get(),
                                                               side=init_obj.Plate.get_side(),
                                                               const_chk=contraints,
                                                               pso_options=self.pso_parameters,
                                                               fatigue_obj=fat_obj,
                                                               fat_press_ext_int=fat_press,
                                                               slamming_press=slamming_pressure,
                                                               predefined_stiffener_iter=predefined_stiffener_iter,
                                                               processes=self._new_processes.get(),
                                                               min_max_span=max_min_span, use_weight_filter=False,
                                                               fdwn=self._new_fdwn.get(), fup=self._new_fup.get(),
                                                               ml_algo=self._get_selected_ml_algo(),
                                                               material_factor=selected_mat_fac,
                                                               weld_bias=self._get_weld_bias_for_optimization(),
                                                               builtup_stiffener=self._new_include_builtup_weld.get(),
                                                               weld_metric=self._get_weld_metric_for_optimization()))
            self._harmonizer_data[line] = {}
            counter += 1
            self.progress_count.set(counter)
            self.progress_bar.update_idletasks()

            if self._opt_results[line] != None:
                self._opt_actual_running_time.config(text='Accumulated running time: \n'
                                                          + str(time.time() - t_start) + ' sec')
            #     print('Runned', line, 'OK')
            # else:
            #     print('Runned', line, 'NOT OK - no results')

        self.draw_select_canvas()

        if self._new_harmonizer.get() == True:
            self._canvas_opt.config(bg='yellow')
            self._canvas_opt.create_text(200, 200, text='Harmonizing results',
                                         font='Verdana 14 bold')
            self.opt_harmonizer_historic()

        counter += 1

        self.progress_bar.stop()
        self.run_button.config(bg='green')
        self.draw_properties()

    def opt_harmonizer_historic(self):
        # getting all acceptable solutions.
        all_ok_checks = []
        for line, data in self._opt_results.items():
            for fail_ok in data[4]:
                if fail_ok[0] == True:
                    # try:
                    #     [round(val, 10) for val in fail_ok[2]]
                    # except TypeError:
                    #     [print(val) for val in fail_ok[2]]

                    all_ok_checks.append(tuple([round(val, 10) for val in fail_ok[2][0:6]]))
        all_ok_checks = set(all_ok_checks)

        # make iterator for multiprocessing
        iterator = list()
        to_check = [self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
                    self._new_check_shear_area.get(), self._new_check_buckling.get(),
                    self._new_check_fatigue.get(), self._new_check_slamming.get(),
                    self._new_check_local_buckling.get(), self._new_check_semi_analytical_buckling.get(),
                    False,
                    self._new_check_ml_numeric_buckling.get()]
        iter_run_info = dict()
        selected_mat_fac = self._get_selected_material_factor()

        for slave_line in self._opt_results.keys():
            input_pressures = self.get_pressure_input(slave_line)
            iter_run_info[slave_line] = {'lateral pressure': input_pressures['lateral pressure'],
                                         'fatigue pressure': input_pressures['fatigue pressure'],
                                         'fatigue object': input_pressures['fatigue object'],
                                         'slamming pressure': input_pressures['slamming pressure'],
                                         'chk_calc_obj': self._opt_results[slave_line][0],
                                         'SemiAnalytical': [float('inf'), float('inf'), 0, 0.87],
                                         'ML-Numeric': [float('inf'), float('inf'), 0],
                                         'fup': self._new_fup.get(), 'fdwn': self._new_fdwn.get()}
        iter_run_info['lines'] = list(self._opt_results.keys())
        iter_run_info['checks'] = to_check
        iter_run_info['keep spacing'] = self._keep_spacing.get()
        iter_run_info['weld bias'] = self._get_weld_bias_for_optimization()
        iter_run_info['builtup stiffener'] = self._new_include_builtup_weld.get()
        iter_run_info['weld metric'] = self._get_weld_metric_for_optimization()

        for x_check in all_ok_checks:
            iterator.append({'x': x_check, 'info': iter_run_info})

        if to_check[7] or to_check[9]:
            # Do SemiAnalytical or ML-Numeric checks for harmonized candidates
            to_run = list()
            to_run_owner = list()

            for x_and_info in iterator:
                for slave_line in x_and_info['info']['lines']:
                    iter_run_info = x_and_info['info']
                    lateral_press = iter_run_info[slave_line]['lateral pressure']
                    fat_obj = iter_run_info[slave_line]['fatigue object']
                    chk_calc_obj = iter_run_info[slave_line]['chk_calc_obj']
                    master_x = list(x_and_info['x'])

                    if iter_run_info['keep spacing']:
                        x = [chk_calc_obj.Plate.get_s()] + master_x[1:] + [
                            chk_calc_obj.Plate.span,
                            chk_calc_obj.Plate.girder_lg,
                        ]
                    else:
                        x = master_x + [chk_calc_obj.Plate.span, chk_calc_obj.Plate.girder_lg]

                    fdwn = self._new_fdwn.get()
                    fup = self._new_fup.get()

                    calc_object_stf = op.create_new_calc_obj(
                        chk_calc_obj.Stiffener,
                        x,
                        None if fat_obj is None else fat_obj.get_fatigue_properties(),
                        fdwn=fdwn,
                        fup=fup,
                    )
                    calc_object_pl = op.create_new_calc_obj(
                        chk_calc_obj.Plate,
                        x,
                        None if fat_obj is None else fat_obj.get_fatigue_properties(),
                        fdwn=fdwn,
                        fup=fup,
                    )
                    calc_object = [
                        calc.AllStructure(
                            Plate=calc_object_pl[0],
                            Stiffener=None if chk_calc_obj.Stiffener is None else calc_object_stf[0],
                            Girder=None,
                            main_dict=chk_calc_obj.get_main_properties()['main dict'],
                        ),
                        calc_object_pl[1],
                    ]
                    calc_object[0].lat_press = lateral_press

                    to_run_owner.append((x_and_info, slave_line))
                    to_run.append((calc_object, x, lateral_press))

            if to_check[7]:
                sort_again = self._predict_semi_analytical_for_to_run(to_run)
                result_key = 'SemiAnalytical'
            else:
                sort_again = self._predict_ml_numeric_for_to_run(to_run)
                result_key = 'ML-Numeric'

            for idx, (x_and_info, slave_line) in enumerate(to_run_owner):
                x_and_info['info'][slave_line][result_key] = sort_again[idx]

        # END ML calc

        processes = max(cpu_count() - 1, 1)
        with Pool(processes) as my_process:
            res_pre = my_process.map(helper_harmonizer_multi, iterator)

        after_multirun_check_ok = list()
        for res in res_pre:
            if res is not None:
                after_multirun_check_ok.append(res)

        lowest_objective, lowest_x = float('inf'), None
        for ok_chkd in set(after_multirun_check_ok):
            total_objective = 0.0

            for line in self._opt_results.keys():
                line_structure_obj = self._line_structure(line)

                if self._keep_spacing.get():
                    this_x = [line_structure_obj.Plate.get_s()] + list(ok_chkd)[1:] + [
                        line_structure_obj.Plate.span,
                        line_structure_obj.Plate.girder_lg,
                    ]
                else:
                    this_x = list(ok_chkd) + [
                        line_structure_obj.Plate.span,
                        line_structure_obj.Plate.girder_lg,
                    ]

                total_objective += self._objective_for_x(this_x, line_structure_obj)

            if total_objective < lowest_objective:
                lowest_objective = total_objective
                lowest_x = ok_chkd

        if lowest_objective != float('inf'):
            for line in self._opt_results.keys():
                line_structure_obj = self._line_structure(line)
                if self._keep_spacing:
                    this_x = [line_structure_obj.Plate.get_s()] + list(lowest_x)[1:] + \
                             [line_structure_obj.Plate.span, line_structure_obj.Plate.girder_lg]
                else:
                    this_x = list(lowest_x) + [line_structure_obj.Plate.span,
                                               line_structure_obj.Plate.girder_lg]

                calc_object_stf = op.create_new_calc_obj(line_structure_obj.Plate, this_x,
                                                         fat_obj.get_fatigue_properties(), fdwn=fdwn, fup=fup)
                calc_object_pl = op.create_new_calc_obj(line_structure_obj.Stiffener, this_x,
                                                        fat_obj.get_fatigue_properties(), fdwn=fdwn, fup=fup)
                self._opt_results[line][0] = [
                    calc.AllStructure(Plate=calc_object_pl[0], Stiffener=calc_object_stf[0], Girder=None,
                                      main_dict=chk_calc_obj.get_main_properties()['main dict']),
                    calc_object_pl[1]]

                self._update_harmonized_fatigue_result(line, this_x)
            return True
        else:
            for line in self._opt_results.keys():
                self._opt_results[line][0] = None

            return False

    def opt_harmonizer(self):
        '''
        Harmonizes the results of you run.
        :return:
        '''

        # Find highest section modulus.
        harm_res = {}
        chk = (self._new_check_sec_mod.get(), self._new_check_min_pl_thk.get(),
               self._new_check_shear_area.get(), self._new_check_buckling.get(),
               self._new_check_fatigue.get(), self._new_check_slamming.get(),
               self._new_check_local_buckling.get())
        for master_line in self._opt_results.keys():
            master_obj = self._opt_results[master_line][0]
            master_x = [master_obj.Plate.get_s(), master_obj.Plate.get_pl_thk(), master_obj.Stiffener.get_web_h(),
                        master_obj.Stiffener.get_web_thk(), master_obj.Stiffener.get_fl_w(),
                        master_obj.Stiffener.get_fl_thk(),
                        master_obj.Plate.span, master_obj.Plate.girder_lg]
            harm_res[master_line] = []
            for slave_line in self._opt_results.keys():
                input_pressures = self.get_pressure_input(slave_line)
                lateral_press = input_pressures['lateral pressure']
                fat_press = input_pressures['fatigue pressure']
                fat_obj = input_pressures['fatigue object']
                slamming_pressure = input_pressures['slamming pressure']
                chk_calc_obj = self._opt_results[slave_line][1]

                chk_result = list(op.run_optmizataion(chk_calc_obj,
                                                      master_x[0:6] + [chk_calc_obj.Plate.span,
                                                                       chk_calc_obj.Plate.girder_lg],
                                                      master_x[0:6] + [chk_calc_obj.Plate.span,
                                                                       chk_calc_obj.Plate.girder_lg],
                                                      lateral_press, self.get_deltas(),
                                                      algorithm=self._new_algorithm.get(),
                                                      trials=self._new_algorithm_random_trials.get(),
                                                      side=chk_calc_obj.Plate.get_side(), const_chk=chk,
                                                      pso_options=self.pso_parameters, fatigue_obj=fat_obj,
                                                      fat_press_ext_int=fat_press, slamming_press=slamming_pressure,
                                                      predefined_stiffener_iter=None,
                                                      processes=self._new_processes.get(), min_max_span=None,
                                                      use_weight_filter=True,
                                                      fdwn=self._new_fdwn.get(), fup=self._new_fup.get(),
                                                      weld_bias=self._get_weld_bias_for_optimization(),
                                                      builtup_stiffener=self._new_include_builtup_weld.get(),
                                                      weld_metric=self._get_weld_metric_for_optimization()))[0:4]
                print('Master:', master_line, 'Slave', slave_line, 'Check', chk_result[-1])
                harm_res[master_line].append(chk_result)

        harmonized_area, harmonized_line = float('inf'), None
        for master_line, all_slave_res in harm_res.items():
            if all([slave_line_res[-1] for slave_line_res in all_slave_res]):
                master_obj = self._opt_results[master_line][0]
                master_area = sum(op.get_field_tot_area([master_obj.Plate.get_s(), master_obj.Plate.get_pl_thk(),
                                                         master_obj.Stiffener.get_web_h(),
                                                         master_obj.Stiffener.get_web_thk(),
                                                         master_obj.Stiffener.get_fl_w(),
                                                         master_obj.Stiffener.get_fl_thk(),
                                                         master_obj.Plate.span, master_obj.Plate.girder_lg]))
                if master_area < harmonized_area:
                    harmonized_area = master_area
                    harmonized_line = master_line

        if harmonized_area != 0 and harmonized_line is not None:
            harmonized_x_pl = self._opt_results[harmonized_line][0].Plate.get_tuple()
            harmonized_x_stf = self._opt_results[harmonized_line][0].Stiffener.get_tuple()
            harmonized_x = harmonized_x_pl[0:2] + harmonized_x_stf[2:]
            for line in self._opt_results.keys():
                line_structure_obj = self._line_structure(line)
                self._opt_results[line][0] = opt.create_new_structure_obj(line_structure_obj, harmonized_x)

                calc_object_stf = op.create_new_calc_obj(line_structure_obj.Plate, harmonized_x)
                calc_object_pl = op.create_new_calc_obj(line_structure_obj.Stiffener, harmonized_x)
                self._opt_results[line][0] = [calc.AllStructure(Plate=calc_object_pl[0], Stiffener=calc_object_stf[0],
                                                                Girder=None,
                                                                main_dict=chk_calc_obj.get_main_properties()[
                                                                    'main dict']),
                                              calc_object_pl[1]]

                self._update_harmonized_fatigue_result(line, harmonized_x)
            return True
        else:
            for line in self._opt_results.keys():
                self._opt_results[line][0] = None
                self._opt_results[line][1] = None
            return False

    def get_running_time(self):
        """
        Estimate running time without creating combinations.

        Returns seconds for all currently selected lines.
        """
        try:
            active_line_count = max(len(self._active_lines), 1)
            algorithm = self._new_algorithm.get()
        except Exception:
            return 0

        if algorithm in ['random', 'random_no_delta', 'scipy_de']:
            try:
                return int(self._new_algorithm_random_trials.get() * self.running_time_per_item) * active_line_count
            except Exception:
                return 0

        try:
            if self._keep_spacing.get():
                n_spacing = 1
            else:
                n_spacing = self._count_steps(
                    self._new_spacing_lower.get(),
                    self._new_spacing_upper.get(),
                    self._new_delta_spacing.get(),
                )

            n_plate = self._count_steps(
                self._new_pl_thk_lower.get(),
                self._new_pl_thk_upper.get(),
                self._new_delta_pl_thk.get(),
            )
            n_web_h = self._count_steps(
                self._new_web_h_lower.get(),
                self._new_web_h_upper.get(),
                self._new_delta_web_h.get(),
            )
            n_web_thk = self._count_steps(
                self._new_web_thk_lower.get(),
                self._new_web_thk_upper.get(),
                self._new_delta_web_thk.get(),
            )
            n_fl_w = self._count_steps(
                self._new_fl_w_lower.get(),
                self._new_fl_w_upper.get(),
                self._new_delta_fl_w.get(),
            )
            n_fl_thk = self._count_steps(
                self._new_fl_thk_lower.get(),
                self._new_fl_thk_upper.get(),
                self._new_delta_fl_thk.get(),
            )

            if self._toggle_btn.config('relief')[-1] == 'sunken' and self._filez is not None:
                # With predefined stiffeners, only spacing and plate thickness
                # are varied in the optimizer.
                number_of_combinations = n_spacing * n_plate * max(len(self._filez), 1)
            else:
                number_of_combinations = n_spacing * n_plate * n_web_h * n_web_thk * n_fl_w * n_fl_thk

            return int(number_of_combinations * self.running_time_per_item) * active_line_count
        except Exception:
            return 0

    def get_deltas(self):
        '''
        Return a numpy array of the deltas.
        :return:
        '''
        return np.array([float(self._ent_delta_spacing.get()) / 1000, float(self._new_delta_pl_thk.get()) / 1000,
                         float(self._new_delta_web_h.get()) / 1000, float(self._new_delta_web_thk.get()) / 1000,
                         float(self._new_delta_fl_w.get()) / 1000, float(self._new_delta_fl_thk.get()) / 1000])

    def _get_selected_material_factor(self):
        """
        Return selected material factor from the main application when available.
        Fallback is the material factor on the first selected line, and then 1.15.
        """
        try:
            return float(self.app._new_material_factor.get())
        except Exception:
            pass

        try:
            if len(self._active_lines) > 0:
                first_line = self._active_lines[0]
                return float(self._line_structure(first_line).Plate.mat_factor)
        except Exception:
            pass

        return 1.15

    def _apply_material_factor_to_structure(self, obj, mat_fac):
        """Apply selected material factor to Plate/Stiffener/Girder for optimizer checks."""
        try:
            mat_fac = float(mat_fac)
        except Exception:
            return obj

        for attr_name in ('Plate', 'Stiffener', 'Girder'):
            try:
                part = getattr(obj, attr_name)
            except Exception:
                part = None
            if part is not None:
                try:
                    part.mat_factor = mat_fac
                except Exception:
                    pass

        return obj

    def _get_selected_ml_algo(self):
        """
        Return ML model dictionary for the selected material factor.

        Main app usually stores:
            self._ML_buckling[1.10][key]
            self._ML_buckling[1.15][key]

        Standalone/test mode may store a flat dictionary:
            self._ML_buckling[key]
        """
        mat_fac = self._get_selected_material_factor()

        try:
            if mat_fac in self._ML_buckling:
                return self._ML_buckling[mat_fac]
        except Exception:
            pass

        return self._ML_buckling

    def _get_ml_input_for_calc_object(self, calc_object, lat_press):
        """
        Return the correct ML input row for SP/UP candidate objects.
        """
        if calc_object[0].Plate.get_puls_sp_or_up() == 'UP' or calc_object[0].Stiffener is None:
            return calc_object[0].Plate.get_buckling_ml_input(lat_press, alone=False)

        return calc_object[0].Stiffener.get_buckling_ml_input(lat_press, alone=False)

    def _predict_ml_cl_for_to_run(self, to_run):
        """
        Predict ML-CL class results for harmonizer candidate objects.

        ML-CL is deactivated; this method is retained only for compatibility
        with older internal call sites.

        Returns
        -------
        np.ndarray
            shape = (len(to_run), 2)
            columns = [buckling_class, ultimate_class]
        """
        ml_algo = self._get_selected_ml_algo()

        sp_int, sp_gl_gt, up_int, up_gl_gt = list(), list(), list(), list()
        sp_int_idx, sp_gl_gt_idx, up_int_idx, up_gl_gt_idx = list(), list(), list(), list()

        for idx, (calc_object, x, lat_press) in enumerate(to_run):
            ml_input = self._get_ml_input_for_calc_object(calc_object, lat_press)

            if calc_object[0].Plate.get_puls_sp_or_up() == 'UP':
                if op._is_integrated_puls_boundary(calc_object[0].Plate.get_puls_boundary()):
                    up_int.append(ml_input)
                    up_int_idx.append(idx)
                else:
                    up_gl_gt.append(ml_input)
                    up_gl_gt_idx.append(idx)
            else:
                if op._is_integrated_puls_boundary(calc_object[0].Stiffener.get_puls_boundary()):
                    sp_int.append(ml_input)
                    sp_int_idx.append(idx)
                else:
                    sp_gl_gt.append(ml_input)
                    sp_gl_gt_idx.append(idx)

        sort_again = np.zeros([len(to_run), 2])

        if len(sp_int) != 0:
            x_buc = ml_algo['cl SP buc int scaler'].transform(sp_int)
            x_ult = ml_algo['cl SP ult int scaler'].transform(sp_int)
            sp_int_res = [
                ml_algo['cl SP buc int predictor'].predict(x_buc),
                ml_algo['cl SP ult int predictor'].predict(x_ult),
            ]
            for idx, res_buc, res_ult in zip(sp_int_idx, sp_int_res[0], sp_int_res[1]):
                sort_again[idx] = [res_buc, res_ult]

        if len(sp_gl_gt) != 0:
            x_buc = ml_algo['cl SP buc GLGT scaler'].transform(sp_gl_gt)
            x_ult = ml_algo['cl SP ult GLGT scaler'].transform(sp_gl_gt)
            sp_gl_gt_res = [
                ml_algo['cl SP buc GLGT predictor'].predict(x_buc),
                ml_algo['cl SP ult GLGT predictor'].predict(x_ult),
            ]
            for idx, res_buc, res_ult in zip(sp_gl_gt_idx, sp_gl_gt_res[0], sp_gl_gt_res[1]):
                sort_again[idx] = [res_buc, res_ult]

        if len(up_int) != 0:
            x_buc = ml_algo['cl UP buc int scaler'].transform(up_int)
            x_ult = ml_algo['cl UP ult int scaler'].transform(up_int)
            up_int_res = [
                ml_algo['cl UP buc int predictor'].predict(x_buc),
                ml_algo['cl UP ult int predictor'].predict(x_ult),
            ]
            for idx, res_buc, res_ult in zip(up_int_idx, up_int_res[0], up_int_res[1]):
                sort_again[idx] = [res_buc, res_ult]

        if len(up_gl_gt) != 0:
            x_buc = ml_algo['cl UP buc GLGT scaler'].transform(up_gl_gt)
            x_ult = ml_algo['cl UP ult GLGT scaler'].transform(up_gl_gt)
            up_gl_gt_res = [
                ml_algo['cl UP buc GLGT predictor'].predict(x_buc),
                ml_algo['cl UP ult GLGT predictor'].predict(x_ult),
            ]
            for idx, res_buc, res_ult in zip(up_gl_gt_idx, up_gl_gt_res[0], up_gl_gt_res[1]):
                sort_again[idx] = [res_buc, res_ult]

        return sort_again

    def _predict_semi_analytical_for_to_run(self, to_run):
        """
        Predict built-in SemiAnalytical UF results for harmonizer candidate objects.

        Returns columns [buckling_uf, ultimate_uf, valid_prediction, acceptance].
        U3 reuses this GUI slot through the runtime S3/U3 adapter.
        """
        sort_again = np.full([len(to_run), 4], float('inf'), dtype=float)
        sort_again[:, 2] = 0
        sort_again[:, 3] = 0.87

        try:
            if hasattr(op.semi_analytical, 'predict_anystructure_uf_batch'):
                return op.semi_analytical.predict_anystructure_uf_batch(
                    to_run,
                    default_acceptance=0.87,
                    cache={},
                )
        except Exception:
            pass

        local_cache = {}
        for idx, (calc_object, x, lat_press) in enumerate(to_run):
            sort_again[idx, 0:4] = op._predict_semi_analytical_uf(
                calc_object,
                lat_press,
                cache=local_cache,
            )

        return sort_again

    def _predict_ml_numeric_for_to_run(self, to_run):
        """
        Predict ML-Numeric UF results for harmonizer candidate objects.

        The numeric regressor predicts raw UF. The optimization check expects
        material-factored UF, so this method applies:
            UF = predicted_UF * material_factor

        Returns
        -------
        np.ndarray
            shape = (len(to_run), 3)
            columns = [buckling_uf, ultimate_uf, valid_prediction]
        """
        ml_algo = self._get_selected_ml_algo()
        mat_fac = self._get_selected_material_factor()

        groups = {
            'sp_int': {'x': [], 'idx': [], 'prefix': 'num SP int'},
            'sp_glgt': {'x': [], 'idx': [], 'prefix': 'num SP GLGT'},
            'up_int': {'x': [], 'idx': [], 'prefix': 'num UP int'},
            'up_glgt': {'x': [], 'idx': [], 'prefix': 'num UP GLGT'},
        }

        for idx, (calc_object, x, lat_press) in enumerate(to_run):
            ml_input = self._get_ml_input_for_calc_object(calc_object, lat_press)

            if calc_object[0].Plate.get_puls_sp_or_up() == 'UP':
                if op._is_integrated_puls_boundary(calc_object[0].Plate.get_puls_boundary()):
                    key = 'up_int'
                else:
                    key = 'up_glgt'
            else:
                if op._is_integrated_puls_boundary(calc_object[0].Stiffener.get_puls_boundary()):
                    key = 'sp_int'
                else:
                    key = 'sp_glgt'

            groups[key]['x'].append(ml_input)
            groups[key]['idx'].append(idx)

        sort_again = np.zeros([len(to_run), 3])
        sort_again[:, 0] = float('inf')
        sort_again[:, 1] = float('inf')
        sort_again[:, 2] = 0

        for group in groups.values():
            if len(group['x']) == 0:
                continue

            prefix = group['prefix']

            valid_predictor_key = f'{prefix} validity predictor'
            valid_xscaler_key = f'{prefix} validity xscaler'
            reg_predictor_key = f'{prefix} UF reg predictor'
            reg_xscaler_key = f'{prefix} UF reg xscaler'
            reg_yscaler_key = f'{prefix} UF reg yscaler'

            required_keys = [
                valid_predictor_key,
                valid_xscaler_key,
                reg_predictor_key,
                reg_xscaler_key,
                reg_yscaler_key,
            ]

            if any(key not in ml_algo or ml_algo[key] is None for key in required_keys):
                continue

            x_valid = ml_algo[valid_xscaler_key].transform(group['x'])
            valid_pred = ml_algo[valid_predictor_key].predict(x_valid)

            x_reg = ml_algo[reg_xscaler_key].transform(group['x'])
            y_scaled = ml_algo[reg_predictor_key].predict(x_reg)
            y_numeric_raw = ml_algo[reg_yscaler_key].inverse_transform(y_scaled)

            for local_idx, global_idx in enumerate(group['idx']):
                valid_int = int(valid_pred[local_idx])
                if valid_int == 1:
                    sort_again[global_idx, 0] = float(y_numeric_raw[local_idx, 0]) * mat_fac
                    sort_again[global_idx, 1] = float(y_numeric_raw[local_idx, 1]) * mat_fac
                    sort_again[global_idx, 2] = 1
                else:
                    sort_again[global_idx, 0] = float('inf')
                    sort_again[global_idx, 1] = float('inf')
                    sort_again[global_idx, 2] = valid_int

        return sort_again

    def update_running_time(self, *args):
        """
        Estimate the running time of the algorithm and keep buckling checks mutually exclusive.
        """
        self._running_time_after_id = None

        try:
            self._runnig_time_label.config(text=str(self.get_running_time()) + self._get_objective_warning_text())
        except (ZeroDivisionError, TclError):
            pass
        except Exception:
            pass

        selected_buckling_checks = [
            self._new_check_buckling.get(),
            self._new_check_semi_analytical_buckling.get(),
            False,
            self._new_check_ml_numeric_buckling.get(),
        ]

        if selected_buckling_checks.count(True) > 1:
            tk.messagebox.showerror('You can only select one buckling type. Reselect.')

            self._new_check_buckling.set(False)
            self._new_check_local_buckling.set(False)
            self._new_check_semi_analytical_buckling.set(False)
            self._new_check_ml_buckling.set(False)
            self._new_check_ml_numeric_buckling.set(False)

        elif (self._new_check_semi_analytical_buckling.get() or self._new_check_ml_numeric_buckling.get()):
            self._new_check_buckling.set(False)
            self._new_check_local_buckling.set(False)

    def _line_bundle(self, line):
        return self._line_to_struc[line]

    def _line_structure(self, line):
        return line_structure.structure(self._line_bundle(line))

    def _line_stiffener(self, line):
        return line_structure.stiffener(self._line_bundle(line))

    def _line_fatigue(self, line):
        return line_structure.fatigue(self._line_bundle(line))

    def _update_harmonized_fatigue_result(self, line, x):
        fatigue_obj = self._line_fatigue(line)
        if fatigue_obj is not None:
            self._opt_results[line][2] = opt.create_new_calc_obj(
                init_obj=self._line_stiffener(line),
                x=x,
                fat_dict=fatigue_obj.get_fatigue_properties())[1]
        else:
            self._clear_line_fatigue(line)

    def _clear_line_fatigue(self, line):
        self._line_bundle(line)[line_structure.FATIGUE] = None

    def get_upper_bounds(self, obj):
        '''
        Return an numpy array of upper bounds.
        :return:
        '''
        if self._keep_spacing:
            spacing = obj.Plate.get_s()
        else:
            spacing = self._new_spacing_lower.get() / 1000
        return np.array([spacing, self._new_pl_thk_upper.get() / 1000,
                         self._new_web_h_upper.get() / 1000, self._new_web_thk_upper.get() / 1000,
                         self._new_fl_w_upper.get() / 1000, self._new_fl_thk_upper.get() / 1000,
                         obj.Plate.span, obj.Plate.girder_lg])

    def get_lower_bounds(self, obj):
        '''
        Return an numpy array of lower bounds.
        :return:
        '''
        if self._keep_spacing:
            spacing = obj.Plate.get_s()
        else:
            spacing = self._new_spacing_lower.get() / 1000
        return np.array([spacing, self._new_pl_thk_lower.get() / 1000,
                         self._new_web_h_lower.get() / 1000, self._new_web_thk_lower.get() / 1000,
                         self._new_fl_w_lower.get() / 1000, self._new_fl_thk_lower.get() / 1000,
                         obj.Plate.span, obj.Plate.girder_lg])

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
        self._canvas_opt.delete('all')
        if init_obj != None:

            self.checkered(10)
            init_color, init_stipple = 'blue', 'gray12'

            self._canvas_opt.create_rectangle(0, 0, self._prop_canvas_dim[0] + 10, 80, fill='white')
            self._canvas_opt.create_line(10, 10, 30, 10, fill=init_color, width=5)
            self._canvas_opt.create_text(270, 10,
                                         text='Initial    - Pl.: ' + str(init_obj.Plate.get_s() * 1000) + 'x' + str(
                                             init_obj.Plate.get_pl_thk() * 1000) +
                                              ' Stf.: ' + str(init_obj.Stiffener.get_web_h() * 1000) + 'x' + str(
                                             init_obj.Stiffener.get_web_thk() * 1000) + '+' +
                                              str(init_obj.Stiffener.get_fl_w() * 1000) + 'x' +
                                              str(init_obj.Stiffener.get_fl_thk() * 1000),
                                         font='Verdana 8',
                                         fill=init_color)
            self._canvas_opt.create_text(120, 30, text='Weight (per Lg width): ' +
                                                       str(int(op.calc_weight([init_obj.Plate.get_s(),
                                                                               init_obj.Plate.get_pl_thk(),
                                                                               init_obj.Stiffener.get_web_h(),
                                                                               init_obj.Stiffener.get_web_thk(),
                                                                               init_obj.Stiffener.get_fl_w(),
                                                                               init_obj.Stiffener.get_fl_thk(),
                                                                               init_obj.Stiffener.span,
                                                                               init_obj.Stiffener.girder_lg]))),
                                         font='Verdana 8', fill=init_color)

            self._canvas_opt.create_rectangle(ctr_x - m * init_obj.Plate.get_s() / 2, ctr_y,
                                              ctr_x + m * init_obj.Plate.get_s() / 2,
                                              ctr_y - m * init_obj.Plate.get_pl_thk(), fill=init_color,
                                              stipple=init_stipple)
            self._canvas_opt.create_rectangle(ctr_x - m * init_obj.Stiffener.get_web_thk() / 2,
                                              ctr_y - m * init_obj.Stiffener.get_pl_thk(),
                                              ctr_x + m * init_obj.Stiffener.get_web_thk() / 2, ctr_y - m * (
                                                          init_obj.Stiffener.get_web_h() + init_obj.Stiffener.get_pl_thk())
                                              , fill=init_color, stipple=init_stipple)
            if init_obj.Stiffener.get_stiffener_type() not in ['L', 'L-bulb']:
                self._canvas_opt.create_rectangle(ctr_x - m * init_obj.Stiffener.get_fl_w() / 2, ctr_y - m * (
                            init_obj.Plate.get_pl_thk() + init_obj.Stiffener.get_web_h()),
                                                  ctr_x + m * init_obj.Stiffener.get_fl_w() / 2,
                                                  ctr_y - m * (
                                                              init_obj.Plate.get_pl_thk() + init_obj.Stiffener.get_web_h() + init_obj.Stiffener.get_fl_thk()),
                                                  fill=init_color, stipple=init_stipple)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * init_obj.Stiffener.get_web_thk() / 2,
                                                  ctr_y - m * (
                                                              init_obj.Plate.get_pl_thk() + init_obj.Stiffener.get_web_h()),
                                                  ctr_x + m * init_obj.Stiffener.get_fl_w(),
                                                  ctr_y - m * (
                                                              init_obj.Plate.get_pl_thk() + init_obj.Stiffener.get_web_h() + init_obj.Stiffener.get_fl_thk()),
                                                  fill=init_color, stipple=init_stipple)

        if opt_obj != None:
            # [0.6, 0.012, 0.25, 0.01, 0.1, 0.01]
            self._canvas_opt.config(bg='palegreen')
            self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.Plate.get_s() / 2, ctr_y,
                                              ctr_x + m * opt_obj.Plate.get_s() / 2,
                                              ctr_y - m * opt_obj.Plate.get_pl_thk(), fill=opt_color,
                                              stipple=opt_stippe)

            self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.Stiffener.get_web_thk() / 2, ctr_y -
                                              m * opt_obj.Plate.get_pl_thk(),
                                              ctr_x + m * opt_obj.Stiffener.get_web_thk() / 2,
                                              ctr_y - m * (
                                                      opt_obj.Stiffener.get_web_h() + opt_obj.Plate.get_pl_thk())
                                              , fill=opt_color, stipple=opt_stippe)
            if init_obj.Stiffener.get_stiffener_type() not in ['L', 'L-bulb']:
                self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.Stiffener.get_fl_w() / 2, ctr_y
                                                  - m * (
                                                          opt_obj.Plate.get_pl_thk() + opt_obj.Stiffener.get_web_h()),
                                                  ctr_x + m * opt_obj.Stiffener.get_fl_w() / 2, ctr_y -
                                                  m * (
                                                          opt_obj.Plate.get_pl_thk() + opt_obj.Stiffener.get_web_h() +
                                                          opt_obj.Stiffener.get_fl_thk()),
                                                  fill=opt_color, stipple=opt_stippe)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * opt_obj.Stiffener.get_web_thk() / 2, ctr_y
                                                  - m * (
                                                          opt_obj.Plate.get_pl_thk() + opt_obj.Stiffener.get_web_h()),
                                                  ctr_x + m * opt_obj.Stiffener.get_fl_w(), ctr_y -
                                                  m * (
                                                          opt_obj.Plate.get_pl_thk() + opt_obj.Stiffener.get_web_h() +
                                                          opt_obj.Stiffener.get_fl_thk()),
                                                  fill=opt_color, stipple=opt_stippe)

            self._canvas_opt.create_line(10, 50, 30, 50, fill=opt_color, width=5)
            self._canvas_opt.create_text(270, 50,
                                         text='Optimized - Pl.: ' + str(round(opt_obj.Plate.get_s() * 1000, 1)) + 'x' +
                                              str(round(opt_obj.Plate.get_pl_thk() * 1000, 1)) + ' Stf.: '
                                              + str(round(opt_obj.Stiffener.get_web_h() * 1000, 1)) +
                                              'x' + str(round(opt_obj.Stiffener.get_web_thk() * 1000, 1)) + '+' +
                                              str(round(opt_obj.Stiffener.get_fl_w() * 1000, 1)) +
                                              'x' + str(round(opt_obj.Stiffener.get_fl_thk() * 1000, 1)),
                                         font='Verdana 8', fill=opt_color)
            self._canvas_opt.create_text(120, 70, text='Weight (per Lg width): '
                                                       + str(int(op.calc_weight([opt_obj.Plate.get_s(),
                                                                                 opt_obj.Plate.get_pl_thk(),
                                                                                 opt_obj.Stiffener.get_web_h(),
                                                                                 opt_obj.Stiffener.get_web_thk(),
                                                                                 opt_obj.Stiffener.get_fl_w(),
                                                                                 opt_obj.Stiffener.get_fl_thk(),
                                                                                 opt_obj.Plate.span,
                                                                                 opt_obj.Plate.girder_lg]))),
                                         font='Verdana 8', fill=opt_color)

        elif self._opt_results != {}:
            self._canvas_opt.config(bg='green')
            self._canvas_opt.create_text(200, 200, text='Optimization results avaliable.\n\n'
                                                        'Middle click orange lines to\n view results.',
                                         font='Verdana 14 bold')

        else:
            self._canvas_opt.config(bg='mistyrose')
            self._canvas_opt.create_text(200, 60, text='No optimization results found.', font='Verdana 14 bold')

        if line != None:
            if __name__ == '__main__':
                lateral_press = 200  # for testing
            else:
                lateral_press = self.app.get_highest_pressure(line)['normal'] / 1000
            self._canvas_opt.create_text(250, self._prop_canvas_dim[1] - 10,
                                         text=line + ' lateral pressure: ' + str(lateral_press) + ' kPa',
                                         font='Verdana 10 bold', fill='red')

    def draw_select_canvas(self, load_selected=False):
        '''
        Making the lines canvas.
        :return:
        '''
        self._canvas_select.delete('all')

        # grid for the canavs

        self._canvas_select.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0],
                                        self._select_canvas_dim[1],
                                        stipple='gray50')
        self._canvas_select.create_line(0, self._canvas_draw_origo[1], self._select_canvas_dim[0],
                                        self._canvas_draw_origo[1],
                                        stipple='gray50')
        self._canvas_select.create_text(self._canvas_draw_origo[0] - 30,
                                        self._canvas_draw_origo[1] + 20, text='(0,0)',
                                        font='Text 10')
        self._canvas_select.create_text([800, 60],
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
        point_coord_x = self._canvas_draw_origo[0] + self._point_dict[point_no][0] * self._canvas_scale
        point_coord_y = self._canvas_draw_origo[1] - self._point_dict[point_no][1] * self._canvas_scale

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
                        elif self._add_to_lines == False:
                            if key in self._active_lines:
                                self._active_lines.remove(key)
                        self._canvas_select.delete('all')
                        break
        self.draw_select_canvas()
        self.update_running_time()

    def right_click(self, event):
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

    def mid_click(self, event):
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
                        if key in self._opt_results.keys() and self._opt_results[key] != None:
                            self.draw_properties(init_obj=self._line_structure(key), opt_obj=self._opt_results[key][0],
                                                 line=key)
                            self._mid_click_line = key
                        else:
                            self.draw_properties(init_obj=self._line_structure(key), line=key)
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
        if self._opt_results == {}:
            messagebox.showinfo(title='Nothing to return', message='No results to return.')
            return
        else:
            to_return = {}
            for line in self._active_lines:
                if self._opt_results[line][0] is not None:
                    to_return[line] = self._opt_results[line]
                else:
                    messagebox.showinfo(title='None in results, cannot return', message='None in results, c'
                                                                                        'annot return values.')
                    return

            self.app.on_close_opt_multiple_window(to_return)
            messagebox.showinfo(title='Return info', message='Returning: ' + str(list(to_return.keys())) +
                                                             '\nLines without results are not returned.')

        self._frame.destroy()

    def toggle(self, found_files=None, obj=None, iterating=False):
        '''
        On off button.
        :param found_files:
        :param obj:
        :return:
        '''
        if iterating:
            if found_files is not None:
                predefined_structure = hlp.helper_read_section_file(files=found_files, obj=obj.Stiffener)
        else:
            predefined_structure = None
            if self._toggle_btn.config('relief')[-1] == 'sunken':
                self._toggle_btn.config(relief="raised")
                self._toggle_btn.config(bg='salmon')
                self._ent_spacing_upper.config(bg='white')
                self._ent_spacing_lower.config(bg='white')
                self._ent_delta_spacing.config(bg='white')
            else:
                self._toggle_btn.config(relief="sunken")
                self._toggle_btn.config(bg='lightgreen')
                self._ent_spacing_upper.config(bg='lightgreen')
                self._ent_spacing_lower.config(bg='lightgreen')
                self._ent_delta_spacing.config(bg='lightgreen')
                openfile = list(askopenfilenames(parent=self._frame, title='Choose files to open',
                                                 initialdir=self._root_dir))
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

    def mouse_scroll(self, event):
        self._canvas_scale += event.delta / 50
        self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale

        self.draw_select_canvas()

    def button_2_click_and_drag(self, event):

        self._canvas_draw_origo = (self._canvas_draw_origo[0] - (self._previous_drag_mouse[0] - event.x),
                                   self._canvas_draw_origo[1] - (self._previous_drag_mouse[1] - event.y))

        self._previous_drag_mouse = (event.x, event.y)
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



