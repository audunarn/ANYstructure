# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError
from tkinter.ttk import Progressbar
from tkinter import messagebox
import pickle
import os
import time
import copy
import numpy as np
from tkinter.filedialog import askopenfilenames
from multiprocessing import cpu_count
from tkinter import filedialog
from matplotlib import pyplot as plt

try:
    import anystruct.main_application
    import anystruct.optimize as op
    import anystruct.example_data as test
    import anystruct.line_structure as line_structure
    import anystruct.ml_models as ml_models
    from anystruct.calc_structure import *
    import anystruct.calc_structure
    from anystruct.helper import *
except ModuleNotFoundError:
    import ANYstructure.anystruct.main_application
    import ANYstructure.anystruct.optimize as op
    import ANYstructure.anystruct.example_data as test
    import ANYstructure.anystruct.line_structure as line_structure
    import ANYstructure.anystruct.ml_models as ml_models
    from ANYstructure.anystruct.calc_structure import *
    import ANYstructure.anystruct.calc_structure
    from ANYstructure.anystruct.helper import *


class CreateOptGeoWindow():
    '''
    This class initiates the MultiOpt window.
    '''

    def _get_selected_ml_buckling(self):
        """Return the flat ML model dictionary expected by optimize.py."""
        ml_algo = self._ML_buckling

        # In the main app this may be stored as {1.1: {...}, 1.15: {...}}.
        # Optimization needs the flat dictionary for the selected/current material factor.
        if isinstance(ml_algo, dict):
            try:
                mat_fac = float(self.app._new_material_factor.get())
            except Exception:
                try:
                    mat_fac = float(self._initial_calc_obj.Plate.mat_factor)
                except Exception:
                    mat_fac = None

            if mat_fac in ml_algo and isinstance(ml_algo[mat_fac], dict):
                return ml_algo[mat_fac]

            # Fallback: if only one nested material-factor dictionary exists, use it.
            nested_keys = [
                key for key, value in ml_algo.items()
                if isinstance(value, dict)
            ]
            if len(nested_keys) == 1:
                return ml_algo[nested_keys[0]]

        return ml_algo

    def _get_selected_material_factor(self):
        """Return selected material factor from main app or fallback to 1.15."""
        try:
            return float(self.app._new_material_factor.get())
        except Exception:
            pass
        try:
            return float(self._initial_calc_obj.Plate.mat_factor)
        except Exception:
            return 1.15

    def _apply_material_factor_to_structure(self, obj, mat_fac):
        """Apply selected material factor to Plate/Stiffener/Girder before optimization."""
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

    def _get_weld_bias_for_optimization(self):
        """
        Return weld consumable bias in range [0, 1].

        0.0 = pure weight optimization.
              optimize.py should preserve old behaviour and skip weld calculations.
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
            return '\nPure weld objective: span optimizer uses ' + self._get_weld_metric_text() + ' in the objective.'

        return ''

    def _get_objective_index_label(self):
        return 'Weight index' if self._get_weld_bias_for_optimization() <= 0.0 else 'Objective index'


    def _show_weight_figure(self, xplot=None, yplot=None):
        """
        Show the geometric optimization summary figure.

        The latest x/y data is stored so the figure can be re-opened after
        the original run has completed.
        """
        if xplot is None or yplot is None:
            if self._last_weight_plot_data is None:
                messagebox.showinfo(
                    title='No figure data',
                    message='No optimization figure data is available. Run the optimization first.'
                )
                return
            xplot, yplot = self._last_weight_plot_data

        if xplot is None or yplot is None or len(xplot) == 0 or len(yplot) == 0:
            messagebox.showinfo(
                title='No figure data',
                message='No valid optimization points are available to plot.'
            )
            return

        self._last_weight_plot_data = (list(xplot), list(yplot))

        plt.figure()
        plt.axes(facecolor='lightslategray')
        plt.plot(
            xplot,
            yplot,
            color='yellow',
            linestyle='solid',
            marker='o',
            markerfacecolor='white',
            markersize=6,
        )
        plt.xlabel('Length of plate fields [m]')
        objective_label = self._get_objective_index_label()
        plt.ylabel(objective_label)
        plt.title('Length of plate fields vs. total ' + objective_label.replace(' index', '').lower())
        plt.grid()
        plt.show()

    def reshow_weight_figure(self):
        """
        Re-open the last geometric optimization summary figure.
        """
        self._show_weight_figure()

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
            self._active_points = ['point1', 'point4', 'point8', 'point5']
            self._root_dir = os.path.dirname(os.path.abspath(__file__))
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
            self._opt_frames = {}
            self._active_points = []
            self._root_dir = app._root_dir
            self._ML_buckling = app._ML_buckling

        self._opt_structure = {}
        self._opt_frames_obj = []
        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1800x1050')
        self._frame.grab_set()
        self._canvas_origo = (50, 720 - 50)

        self._canvas_base_origo = self._canvas_origo
        self._canvas_draw_origo = list(self._canvas_base_origo)
        self._previous_drag_mouse = list(self._canvas_draw_origo)

        self._active_lines = []
        self._add_to_lines = True
        self._lines_add_to_load = []
        self._active_point = None
        self._point_is_active = False

        # ----------------------------------COPIED FROM OPTIMIZE_WINDOW----------------------------------------------- #

        self._opt_resutls = {}
        self._geo_results = None
        self._last_weight_plot_data = None
        self._running_time_after_id = None

        # Gridded layout scaffolding: header, bounds table + run controls,
        # objective row, then the selection canvas with the result canvas,
        # constraint checks and girder data on the right.
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(3, weight=1)
        self._header_frame = tk.Frame(self._frame)
        self._header_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(8, 4))
        self._bounds_frame = tk.Frame(self._frame)
        self._bounds_frame.grid(row=1, column=0, sticky=tk.NW, padx=10)
        self._controls_frame = tk.Frame(self._frame)
        self._controls_frame.grid(row=1, column=1, rowspan=2, sticky=tk.NW, padx=(10, 10))
        self._algo_params_frame = tk.Frame(self._controls_frame)
        self._objective_frame = tk.Frame(self._frame)
        self._objective_frame.grid(row=2, column=0, sticky=tk.NW, padx=10, pady=(6, 0))
        self._select_canvas_holder = tk.Frame(self._frame)
        self._select_canvas_holder.grid(row=3, column=0, sticky=tk.NW, padx=10, pady=(8, 8))
        self._right_column = tk.Frame(self._frame)
        self._right_column.grid(row=3, column=1, sticky=tk.NW, padx=(10, 10), pady=(8, 8))
        self._opt_canvas_holder = tk.Frame(self._right_column)
        self._opt_canvas_holder.grid(row=0, column=0, columnspan=2, sticky=tk.NW)
        self._checks_frame = tk.Frame(self._right_column)
        self._checks_frame.grid(row=1, column=0, sticky=tk.NW, pady=(8, 0))
        self._girder_data_frame = tk.Frame(self._right_column)
        self._girder_data_frame.grid(row=1, column=1, sticky=tk.NW, padx=(16, 0), pady=(8, 0))

        self._opt_actual_running_time = tk.Label(self._controls_frame, text='')

        algorithms = ('anysmart', 'scipy_de')

        tk.Label(self._header_frame, text='-- Plate field span optimizer for plate fields separated by frames. --',
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
        self._new_option_fraction = tk.IntVar()
        self._new_option_panel = tk.IntVar()
        self._new_weld_bias = tk.DoubleVar()
        self._new_weld_metric = tk.StringVar()
        self._new_include_builtup_weld = tk.BooleanVar()

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

        self._ent_opt_girder_thk = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_thk, width=ent_w)
        self._ent_opt_girder_stf_web_h = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_stf_web_h,
                                                  width=ent_w)
        self._ent_opt_girder_stf_web_thk = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_stf_web_thk,
                                                    width=ent_w)
        self._ent_opt_girder_stf_fl_b = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_stf_flange_b,
                                                 width=ent_w)
        self._ent_opt_girder_stf_fl_thk = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_stf_flange_thk,
                                                   width=ent_w)

        self._ent_opt_girder_scale_high = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_scale_high,
                                                   width=int(ent_w / 2))
        self._ent_opt_girder_scale_low = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_girder_scale_low,
                                                  width=int(ent_w / 2))

        self._ent_opt_max_span = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_span_max,
                                          width=int(ent_w / 2))
        self._ent_opt_min_span = tk.Entry(self._girder_data_frame, textvariable=self._new_opt_span_min,
                                          width=int(ent_w / 2))

        start_x, start_y, dx, dy = 20, 70, 100, 40
        status_y = 170
        objective_y = 205
        canvas_y = 300

        tk.Label(self._header_frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg='silver') \
            .grid(row=0, column=2, sticky=tk.W, padx=(20, 4))
        tk.Entry(self._header_frame, textvariable=self._new_processes, width=12, bg='silver') \
            .grid(row=0, column=3, sticky=tk.W)

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
        self._running_time_info_label = tk.Label(
            self._bounds_frame,
            text='Estimated running time for algorithm not calculated.',
            font='Verdana 9 bold',
            justify=tk.LEFT,
        )
        self._running_time_info_label.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(6, 0))
        self._result_label = tk.Label(self._bounds_frame, text='', font='Verdana 9 bold')
        self._result_label.grid(row=4, column=4, columnspan=3, sticky=tk.W, pady=(6, 0))

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
        self._new_processes.set(max(cpu_count() - 1, 1))
        self._new_opt_girder_thk.set(0.018)
        self._new_opt_girder_stf_web_h.set(0.250)
        self._new_opt_girder_stf_web_thk.set(0.015)
        self._new_opt_girder_stf_flange_b.set(0)
        self._new_opt_girder_stf_flange_thk.set(0)
        self._new_opt_girder_scale_high.set(1.1)
        self._new_opt_girder_scale_low.set(0.9)
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
        # self._runnig_time_label.config(text=str(self.get_running_time()))
        self.run_button = tk.Button(self._controls_frame, text='RUN OPTIMIZATION!', command=self.run_optimizaion,
                                    bg='red', font='Verdana 10', fg='Yellow')
        self.run_button.grid(row=0, column=0, sticky=tk.EW, pady=2)
        self._ent_algorithm.grid(row=1, column=0, sticky=tk.EW, pady=2)
        self.algorithm_random_label = tk.Label(self._algo_params_frame, text='Number of trials')
        tk.Button(self._controls_frame, text='algorithm information', command=self.algorithm_info, bg='white') \
            .grid(row=2, column=0, sticky=tk.EW, pady=2)
        self._opt_actual_running_time.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        self._algo_params_frame.grid(row=0, column=1, rowspan=3, sticky=tk.NW, padx=(16, 0))

        tk.Button(self._header_frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10') \
            .grid(row=0, column=1, sticky=tk.W, padx=(0, 12))

        # Selection of constraints
        self._new_check_sec_mod = tk.BooleanVar()
        self._new_check_min_pl_thk = tk.BooleanVar()
        self._new_check_shear_area = tk.BooleanVar()
        self._new_check_buckling = tk.BooleanVar()
        self._new_check_fatigue = tk.BooleanVar()
        self._new_check_slamming = tk.BooleanVar()
        self._new_check_local_buckling = tk.BooleanVar()
        self._new_harmonize_spacing = tk.BooleanVar()
        self._new_check_buckling_semi_analytical = tk.BooleanVar()
        self._new_check_buckling_ml_cl = tk.BooleanVar()
        self._new_check_buckling_ml_numeric = tk.BooleanVar()

        self._new_check_sec_mod.set(True)
        self._new_check_min_pl_thk.set(True)
        self._new_check_shear_area.set(True)
        self._new_check_buckling.set(True)
        self._new_check_fatigue.set(True)
        self._new_check_slamming.set(True)
        self._new_check_local_buckling.set(True)
        self._new_option_fraction.set(None)
        self._new_option_panel.set(None)
        self._new_weld_bias.set(0.0)
        self._new_weld_metric.set('Weld consumables')
        self._new_include_builtup_weld.set(False)
        self._new_harmonize_spacing.set(False)
        self._new_check_buckling_semi_analytical.set(False)
        self._new_check_buckling_ml_cl.set(False)
        self._new_check_buckling_ml_numeric.set(False)

        self._new_check_buckling_semi_analytical.trace_add('write', self.schedule_running_time_update)
        self._new_check_buckling_ml_cl.trace_add('write', self.schedule_running_time_update)
        self._new_check_buckling_ml_numeric.trace_add('write', self.schedule_running_time_update)
        self._new_weld_bias.trace_add('write', self._update_weld_bias_label)
        self._new_weld_metric.trace_add('write', self._update_weld_bias_label)

        check_rows = (
            ('Check for minimum section modulus', self._new_check_sec_mod, 'normal'),
            ('Check for minimum plate thk.', self._new_check_min_pl_thk, 'normal'),
            ('Check for minimum shear area', self._new_check_shear_area, 'normal'),
            ('Check for buckling (RP-C201)', self._new_check_buckling, 'normal'),
            ('Check for fatigue (RP-C203)', self._new_check_fatigue, 'normal'),
            ('Check for bow slamming', self._new_check_slamming, 'normal'),
            ('Check for local stf. buckling', self._new_check_local_buckling, 'normal'),
            ('Check for buckling, SemiAnalytical S3/U3', self._new_check_buckling_semi_analytical, 'normal'),
            ('Check for buckling, ML-CL deactivated', self._new_check_buckling_ml_cl, 'disabled'),
            ('Check for buckling, ML-Numeric', self._new_check_buckling_ml_numeric, 'normal'),
        )
        for row, (text, variable, state) in enumerate(check_rows):
            tk.Label(self._checks_frame, text=text).grid(row=row, column=0, sticky=tk.W)
            tk.Checkbutton(self._checks_frame, variable=variable, state=state).grid(row=row, column=1, sticky=tk.W)

        tk.Label(self._girder_data_frame, text='Frame (girder data) for weight calculation:',
                 font='Verdana 9 bold').grid(row=0, column=0, columnspan=3, sticky=tk.W)
        girder_data_rows = (
            ('Girder thickness', self._ent_opt_girder_thk),
            ('Stiffener height', self._ent_opt_girder_stf_web_h),
            ('Stiffener thickness', self._ent_opt_girder_stf_web_thk),
            ('Stf. flange width', self._ent_opt_girder_stf_fl_b),
            ('Stf. flange thickenss', self._ent_opt_girder_stf_fl_thk),
        )
        for row, (text, entry) in enumerate(girder_data_rows):
            tk.Label(self._girder_data_frame, text=text).grid(row=1 + row, column=0, sticky=tk.W)
            entry.grid(row=1 + row, column=1, columnspan=2, sticky=tk.W, padx=(8, 0), pady=1)
        tk.Label(self._girder_data_frame, text='For weight calculation of girder: Max span mult / Min span mult') \
            .grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))
        self._ent_opt_girder_scale_high.grid(row=7, column=1, sticky=tk.W, padx=(8, 2))
        self._ent_opt_girder_scale_low.grid(row=7, column=2, sticky=tk.W)
        tk.Label(self._girder_data_frame, text='Maximum span / Minimum span ->') \
            .grid(row=8, column=0, sticky=tk.W)
        self._ent_opt_max_span.grid(row=8, column=1, sticky=tk.W, padx=(8, 2))
        self._ent_opt_min_span.grid(row=8, column=2, sticky=tk.W)

        # Stress scaling
        self._new_fup = tk.DoubleVar()
        self._new_fup.set(0.5)
        self._new_fdwn = tk.DoubleVar()
        self._new_fdwn.set(1)

        tk.Label(self._checks_frame, text='Factor when scaling stresses up, fup') \
            .grid(row=len(check_rows), column=0, sticky=tk.W, pady=(8, 0))
        ent_fup = tk.Entry(self._checks_frame, textvariable=self._new_fup, width=5)
        ent_fup.grid(row=len(check_rows), column=1, sticky=tk.W, pady=(8, 0))
        tk.Label(self._checks_frame, text='Factor when scaling stresses up, fdown') \
            .grid(row=len(check_rows) + 1, column=0, sticky=tk.W)
        ent_fdwn = tk.Entry(self._checks_frame, textvariable=self._new_fdwn, width=5)
        ent_fdwn.grid(row=len(check_rows) + 1, column=1, sticky=tk.W)

        self._toggle_btn = tk.Button(self._controls_frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg='salmon')
        self._toggle_btn.grid(row=4, column=0, sticky=tk.EW, pady=2)
        self._toggle_object, self._filez = None, None

        self._options_fractions = (None,)
        self._options_panels = (None,)

        self._panel_options_frame = tk.Frame(self._controls_frame)
        self._panel_options_frame.grid(row=0, column=2, rowspan=5, sticky=tk.NW, padx=(16, 0))
        tk.Label(self._panel_options_frame, text='Select number of panels:').grid(row=0, column=0, sticky=tk.W)
        tk.Label(self._panel_options_frame, text='Select panel to plot:   ').grid(row=1, column=0, sticky=tk.W)
        self._ent_option_fractions = tk.OptionMenu(self._panel_options_frame, self._new_option_fraction,
                                                   *self._options_fractions,
                                                   command=self.get_plate_field_options)
        self._ent_option_field = tk.OptionMenu(self._panel_options_frame, self._new_option_panel,
                                               *self._options_panels,
                                               command=self.get_plate_field_options)
        self._ent_option_fractions.grid(row=0, column=1, sticky=tk.W, padx=8)
        self._ent_option_field.grid(row=1, column=1, sticky=tk.W, padx=8)

        self.run_results = tk.Button(self._panel_options_frame, text='show calculated', command=self.plot_results,
                                     bg='white', font='Verdana 10', fg='black')
        self.run_results.grid(row=2, column=0, sticky=tk.EW, pady=2)

        self.reshow_figure_button = tk.Button(
            self._panel_options_frame,
            text='re-show figure',
            command=self.reshow_weight_figure,
            bg='white',
            font='Verdana 10',
            fg='black',
        )
        self.reshow_figure_button.grid(row=3, column=0, sticky=tk.EW, pady=2)

        self.run_results_prev = tk.Button(self._panel_options_frame, text='Show previous\n'
                                                            'results', command=self.show_previous_results, bg='white',
                                          font='Verdana 10', fg='black')
        self.run_results_prev.grid(row=2, column=1, rowspan=2, sticky=tk.NW, padx=8, pady=2)

        # Optimization objective bias.
        # For geometric optimization this is forwarded to optimize.py.
        # optimize.py must skip weld calculations when weld_bias == 0.0.
        tk.Label(
            self._objective_frame,
            text='Optimization objective',
            font='Verdana 9 bold',
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W)

        self._weld_bias_slider = tk.Scale(
            self._objective_frame,
            variable=self._new_weld_bias,
            from_=0.0,
            to=1.0,
            resolution=0.05,
            orient=tk.HORIZONTAL,
            length=230,
            showvalue=False,
            command=self._update_weld_bias_label,
        )
        self._weld_bias_slider.grid(row=1, column=0, columnspan=2, sticky=tk.W)

        tk.Label(self._objective_frame, text='Weight', font='Verdana 7').grid(row=2, column=0, sticky=tk.W)
        tk.Label(self._objective_frame, text='Weld', font='Verdana 7').grid(row=2, column=1, sticky=tk.E)

        self._weld_bias_value_label = tk.Label(
            self._objective_frame,
            text='Weld bias: 0.0',
            font='Verdana 8 bold',
        )
        self._weld_bias_value_label.grid(row=0, column=2, sticky=tk.NW, padx=(30, 0))

        self._weld_bias_info_label = tk.Label(
            self._objective_frame,
            text=self._get_weld_bias_text(),
            font='Verdana 7',
            wraplength=300,
            justify=tk.LEFT,
        )
        self._weld_bias_info_label.grid(row=1, column=2, rowspan=2, sticky=tk.NW, padx=(30, 0))

        self._weld_metric_menu = tk.OptionMenu(
            self._objective_frame,
            self._new_weld_metric,
            'Weld consumables',
            'Weld length',
            command=self._update_weld_bias_label,
        )
        self._weld_metric_menu.grid(row=3, column=2, sticky=tk.W, padx=(30, 0), pady=(4, 0))

        tk.Checkbutton(
            self._objective_frame,
            variable=self._new_include_builtup_weld,
        ).grid(row=3, column=3, sticky=tk.W, padx=(12, 0), pady=(4, 0))

        tk.Label(
            self._objective_frame,
            text='Include web-to-flange weld for built-up stiffeners',
            font='Verdana 7',
            wraplength=230,
            justify=tk.LEFT,
        ).grid(row=3, column=4, sticky=tk.W, pady=(4, 0))

        tk.Checkbutton(self._objective_frame, variable=self._new_harmonize_spacing) \
            .grid(row=3, column=0, sticky=tk.W, pady=(4, 0))
        tk.Label(self._objective_frame, text='- Harmonize stiffener spacing for section.', font='Verdana 9 bold') \
            .grid(row=3, column=1, sticky=tk.W, pady=(4, 0))

        # ----------------------------------END OF OPTIMIZE SINGLE COPY-----------------------------------------------
        self.progress_count = tk.IntVar()
        self.progress_count.set(0)
        self.progress_bar = Progressbar(self._frame, orient="horizontal", length=200, mode="determinate",
                                        variable=self.progress_count)
        # self.progress_bar.place(x=start_x+dx*10.5,y=start_y-dy*16.5)

        self._active_lines = []
        self.controls()
        self.draw_select_canvas()
        # if __name__ == '__main__':
        #     self.run_optimizaion(load_pre = True, save_results=True)


    def schedule_running_time_update(self, *args):
        """
        Debounce GUI updates from variable traces.

        This avoids slow or repeated work while the user is typing.
        """
        try:
            if getattr(self, '_running_time_after_id', None) is not None:
                self._frame.after_cancel(self._running_time_after_id)
        except Exception:
            pass

        self._running_time_after_id = self._frame.after(350, self.update_running_time)

    def selected_algorithm(self, event):
        '''
        Action when selecting an algorithm in the option menu.
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

    def show_previous_results(self):
        # if type(self._geo_results) is not list():
        #     if self._geo_results is not None:
        #         return
        # else:
        #     if self._geo_results[0] is not None:
        #         return
        self.draw_select_canvas(opt_results=self._geo_results)

    def run_optimizaion(self, load_pre=False, save_results=False, harmonize=False):
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
                      self._new_check_local_buckling.get(), self._new_check_buckling_semi_analytical.get(),
                      False,
                      self._new_check_buckling_ml_numeric.get())

        selected_ml_algo = self._get_selected_ml_buckling()
        selected_mat_fac = self._get_selected_material_factor()

        self.pso_parameters = (self._new_swarm_size.get(), self._new_omega.get(), self._new_phip.get(),
                               self._new_phig.get(), self._new_maxiter.get(), self._new_minstep.get(),
                               self._new_minfunc.get())

        opt_girder_prop = (self._new_opt_girder_thk.get(), self._new_opt_girder_stf_web_h.get(),
                           self._new_opt_girder_stf_web_thk.get(), self._new_opt_girder_stf_flange_b.get(),
                           self._new_opt_girder_stf_flange_thk.get(), self._new_opt_girder_scale_high.get(),
                           self._new_opt_girder_scale_low.get())
        min_max_span = (self._new_opt_span_min.get(), self._new_opt_span_max.get())

        init_objects, fatigue_objects, fat_press_ext_int, slamming_pressures, lateral_press, fatigue_objects, \
            slamming_press = [list() for dummy in range(7)]

        broke = False
        pressure_side = 'both sides'  # default value
        for line, coord in self._opt_structure.items():
            if self.opt_create_struc_obj(self._opt_structure[line]) is None:
                broke = True
                break
            else:
                init_obj_single = self.opt_create_struc_obj(self._opt_structure[line])[0]
                self._apply_material_factor_to_structure(init_obj_single, selected_mat_fac)
                init_objects.append(init_obj_single)
                fat_obj_single = self.opt_create_struc_obj(self._opt_structure[line])[2]
                fatigue_objects.append(fat_obj_single)

            if __name__ == '__main__':
                import example_data as ex
                lateral_press.append(0.2)  # for testing
                slamming_press.append(0)
                fatigue_objects.append(ex.get_fatigue_object())
                for pressure in ex.get_geo_opt_fat_press():
                    fat_press_ext_int.append(((pressure['p_ext']['loaded'], pressure['p_ext']['ballast'],
                                               pressure['p_ext']['part']),
                                              (pressure['p_int']['loaded'], pressure['p_int']['ballast'],
                                               pressure['p_int']['part'])))
                pressure_side = 'both sides'

            else:
                p1, p2 = self._opt_structure[line]
                # Check if line is horizontal or vertical
                if p2[0] == p1[0]:  # Vertical
                    to_find = [p2[0], min(p2[1], p1[1]) + abs((p2[1] - p1[1]) * 0.5)]
                elif p2[1] == p1[1]:  # Horizontal
                    to_find = [min(p2[0], p1[0]) + (p2[0] - p1[0]) * 0.5, p2[1]]
                else:  # Other orientations
                    to_find = [min(p2[0], p1[0]) + abs((p2[0] - p1[0]) * 0.5),
                               min(p2[1], p1[1]) + abs((p2[1] - p1[1]) * 0.5)]

                # Taking properites from the closest line.
                closet_line = self.opt_find_closest_orig_line(to_find)
                pressure_side = self._line_overpressure_side(closet_line)
                # print('Closest line', closet_line, p1, p2, to_find)
                gotten_lat_press = self.app.get_highest_pressure(closet_line)
                lateral_press.append(gotten_lat_press['normal'] / 1e6)
                slamming_press.append(gotten_lat_press['slamming'])
                if fat_obj_single is not None:
                    fat_press_single = self.app.get_fatigue_pressures(closet_line, fat_obj_single.get_accelerations())
                    fat_press_tuple = ((fat_press_single['p_ext']['loaded'], fat_press_single['p_ext']['ballast'],
                                        fat_press_single['p_ext']['part']),
                                       (fat_press_single['p_int']['loaded'], fat_press_single['p_int']['ballast'],
                                        fat_press_single['p_int']['part']))
                    fat_press_ext_int.append(fat_press_tuple)
                else:
                    fat_press_ext_int.append(((0, 0, 0), (0, 0, 0)))

                # except AttributeError:
                #     print('AttributeError')
                #     fat_press_ext_int.append(None)
        if broke:
            messagebox.showinfo(title='Selection error.',
                                message='This field cannot be subdivided or there are no loads. Error.')
            return None

        if not load_pre:
            min_var = self.get_lower_bounds()
            max_var = self.get_upper_bounds()
            deltas = self.get_deltas()
            spacings = np.arange(min_var[0], max_var[0],
                                 deltas[0])
            resulting_geo = list()

            if self._new_harmonize_spacing.get():
                geo_results = dict()
                for spacing in spacings:
                    this_min_var = copy.deepcopy(min_var)
                    this_min_var[0] = spacing
                    this_max_var = copy.deepcopy(max_var)
                    this_max_var[0] = spacing

                    geo_results = op.run_optmizataion(initial_structure_obj=init_objects, min_var=this_min_var,
                                                      max_var=this_max_var, lateral_pressure=lateral_press,
                                                      deltas=self.get_deltas(), algorithm=self._new_algorithm.get(),
                                                      trials=self._new_algorithm_random_trials.get(),
                                                      side=pressure_side,
                                                      const_chk=contraints, pso_options=self.pso_parameters,
                                                      is_geometric=True, fatigue_obj=fatigue_objects,
                                                      fat_press_ext_int=fat_press_ext_int,
                                                      min_max_span=min_max_span, tot_len=self.opt_get_length(),
                                                      frame_height=self.opt_get_distance(), frame_distance=distances,
                                                      predefined_stiffener_iter=self._filez,
                                                      processes=self._new_processes.get(),
                                                      slamming_press=slamming_press, opt_girder_prop=opt_girder_prop,
                                                      fdwn=self._new_fdwn.get(), fup=self._new_fup.get(),
                                                      ml_algo=selected_ml_algo,
                                                      material_factor=selected_mat_fac,
                                                      weld_bias=self._get_weld_bias_for_optimization(),
                                                      builtup_stiffener=self._new_include_builtup_weld.get(),
                                                      weld_metric=self._get_weld_metric_for_optimization())
                    resulting_geo.append(geo_results)

                # need to find the lowest
                for fraction in resulting_geo[0].keys():
                    weight = float('inf')
                    best_idx = None
                    for idx, geo_res in enumerate(resulting_geo):
                        this_sub_fraction_weight = geo_res[fraction][0]
                        if this_sub_fraction_weight < weight:
                            best_idx = idx
                            weight = this_sub_fraction_weight

                    geo_results[fraction] = resulting_geo[best_idx][fraction]

            else:
                geo_results = op.run_optmizataion(initial_structure_obj=init_objects, min_var=self.get_lower_bounds(),
                                                  max_var=self.get_upper_bounds(), lateral_pressure=lateral_press,
                                                  deltas=self.get_deltas(), algorithm=self._new_algorithm.get(),
                                                  trials=self._new_algorithm_random_trials.get(), side=pressure_side,
                                                  const_chk=contraints, pso_options=self.pso_parameters,
                                                  is_geometric=True, fatigue_obj=fatigue_objects,
                                                  fat_press_ext_int=fat_press_ext_int,
                                                  min_max_span=min_max_span, tot_len=self.opt_get_length(),
                                                  frame_height=self.opt_get_distance(), frame_distance=distances,
                                                  predefined_stiffener_iter=self._filez,
                                                  processes=self._new_processes.get(),
                                                  slamming_press=slamming_press, opt_girder_prop=opt_girder_prop,
                                                  fdwn=self._new_fdwn.get(), fup=self._new_fup.get(),
                                                  ml_algo=selected_ml_algo,
                                                  material_factor=selected_mat_fac,
                                                  weld_bias=self._get_weld_bias_for_optimization(),
                                                  builtup_stiffener=self._new_include_builtup_weld.get(),
                                                  weld_metric=self._get_weld_metric_for_optimization())

            self._geo_results = geo_results

            if len([val * 2 for val in self._geo_results.keys()]) != 0:
                self._ent_option_fractions.destroy()
                self._ent_option_fractions = tk.OptionMenu(self._panel_options_frame, self._new_option_fraction,
                                                           *tuple([val * 2 for val in self._geo_results.keys()]),
                                                           command=self.get_plate_field_options)
                self._ent_option_fractions.grid(row=0, column=1, sticky=tk.W, padx=8)

            # SAVING RESULTS
            if save_results:
                with open('geo_opt_2.pickle', 'wb') as file:
                    pickle.dump(geo_results, file)
        else:
            with open('geo_opt_2.pickle', 'rb') as file:
                self._geo_results = pickle.load(file)

            self._ent_option_fractions.destroy()
            self._ent_option_fractions = tk.OptionMenu(self._panel_options_frame, self._new_option_fraction,
                                                       *tuple([val * 2 for val in self._geo_results.keys()]),
                                                       command=self.get_plate_field_options)
            self._ent_option_fractions.grid(row=0, column=1, sticky=tk.W, padx=8)

        save_file, filename = None, None
        if save_results:
            save_file = filedialog.asksaveasfile(mode="w", defaultextension=".txt", title='Save results to file')
            if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
                filename = None
            else:
                filename = save_file.name

        save_file, xplot, yplot = self.draw_result_text(self._geo_results, save_to_file=filename)
        self.draw_select_canvas(opt_results=self._geo_results, save_file=save_file)

        self._show_weight_figure(xplot, yplot)

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
            to_return.append(1 / init_fractions)

        return to_return

    def opt_create_struc_obj(self, opt_line):
        ''' Creating preliminary stucture object from selected optimized line.
        The properties of the new line oto be optimized is taken from the closest original line.'''

        pt1 = opt_line[0]
        pt2 = opt_line[1]

        vector = [pt2[0] - pt1[0], pt2[1] - pt1[1]]
        point = [pt1[0] + vector[0] * 0.5, pt1[1] + vector[1] * 0.5]
        if self.opt_find_closest_orig_line(point) == None:
            return None
        objects = self._copy_line_structure_bundle(self.opt_find_closest_orig_line(point))
        objects[0].Plate.set_span(dist(pt1, pt2))
        objects[0].Stiffener.set_span(dist(pt1, pt2))

        return objects

    def opt_find_closest_orig_line(self, coord):
        ''' Find the closest original line to the optimized line.
            Used to create initial structure objects. '''

        for key, value in self._line_dict.items():

            pt1 = list(self._point_dict['point' + str(value[0])])
            pt2 = list(self._point_dict['point' + str(value[1])])
            distance = dist(pt2, pt1)
            vector = [pt2[0] - pt1[0], pt2[1] - pt1[1]]
            current = list(self._point_dict['point' + str(value[0])])
            for dummy_i in range(1000):
                delta = distance / 1000
                current[0] += (vector[0] / distance) * delta
                current[1] += (vector[1] / distance) * delta
                if dist(coord, current) <= 0.1:
                    if self._line_structure_type(key) not in ('GENERAL_INTERNAL_NONWT', 'FRAME'):
                        return key
                    else:
                        return None

    def opt_get_distance(self):
        ''' Getting the largest disctance between the two lines to be optimized. '''
        if len(self._active_points) == 4:
            return dist(self._point_dict[self._active_points[0]], self._point_dict[self._active_points[2]])
        else:
            return None

    def opt_get_length(self):
        ''' Getting the length of the lines to be optimized. '''
        if len(self._active_points) == 4:
            return dist(self._point_dict[self._active_points[0]], self._point_dict[self._active_points[1]])

    def opt_get_fraction_bounds(self, max_len=6, min_len=2):
        ''' Return the fraction bounds(basis upper/lower) to be considered. '''
        return int(self.opt_get_length() / max_len), int(self.opt_get_length() / min_len)

    def opt_create_frames(self, fractions):
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

        start = 0
        for fraction in fractions:
            start += fraction
            if start != 1:
                self._opt_frames['opt_frame' + str(count)] = [[self._point_dict[self._active_points[0]][0] +
                                                               round(self.opt_get_length() * start, 5),
                                                               self._point_dict[self._active_points[0]][1]],
                                                              [self._point_dict[self._active_points[2]][0] +
                                                               round(self.opt_get_length() * start, 5),
                                                               self._point_dict[self._active_points[2]][1]]]
            count += 1
        distances = {'start_dist': dist(self._opt_frames['opt_frame_start'][0], self._opt_frames['opt_frame_start'][1]),
                     'stop_dist': dist(self._opt_frames['opt_frame_stop'][0], self._opt_frames['opt_frame_stop'][1])}

        return self._opt_frames, distances

    def opt_create_main_structure(self, frames, start1, stop1, start2, stop2):
        ''' This creates line definition for the new structure objects.
         The scipt searches the line to find frames.'''
        line1_coord = self._point_dict[start1], self._point_dict[stop1]
        line2_coord = self._point_dict[start2], self._point_dict[stop2]

        structure = {}

        p1_low, p1_high = list(line1_coord[0]), list(line2_coord[0])
        p2_low, p2_high = list(line1_coord[1]), list(line2_coord[1])
        vector_low, vector_high = [p2_low[0] - p1_low[0], p2_low[1] - p1_low[1]], [p2_high[0] - p1_high[0],
                                                                                   p2_high[1] - p1_high[1]]

        # Starting search on the lower or inner line
        count = 1
        tmp_struc = [p1_low]  # starting point defined.
        found = None
        for frame, coords in frames.items():
            current = list(p1_low)
            if frame != 'opt_frame_start' and frame != 'opt_frame_stop':
                for jump in range(100):
                    current[0] += vector_low[0] / 100
                    current[1] += vector_low[1] / 100
                    if dist(current, coords[0]) < 0.1 and frame != found:
                        found = frame
                        tmp_struc.append(coords[0])
                        self._opt_structure['opt_struc' + str(count)] = tmp_struc  # adding found line
                        tmp_struc = [coords[0]]
                        count += 1
        tmp_struc.append(p2_low)
        self._opt_structure['opt_struc' + str(count)] = tmp_struc  # adding found line (end)
        count += 1

        # Starting search of upper or outer line.
        tmp_struc = [p1_high]  # starting point defined.
        found = None
        for frame, coords in frames.items():
            current = list(p1_high)
            if frame != 'opt_frame_start' and frame != 'opt_frame_stop':
                for jump in range(100):
                    current[0] += vector_high[0] / 100
                    current[1] += vector_high[1] / 100
                    if dist(current, coords[1]) < 0.1 and frame != found:
                        found = frame
                        tmp_struc.append(coords[1])

                        self._opt_structure['opt_struc' + str(count)] = tmp_struc  # adding found line
                        tmp_struc = [coords[1]]
                        count += 1
        tmp_struc.append(p2_high)
        self._opt_structure['opt_struc' + str(count)] = tmp_struc  # adding found line (end)

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

        self._running_time_after_id = None

        try:
            self._running_time_info_label.config(
                text='Estimated running time for algorithm not calculated.'
                     + self._get_objective_warning_text()
            )
        except Exception:
            pass

        selected_buckling_checks = [
            self._new_check_buckling.get(),
            self._new_check_buckling_semi_analytical.get(),
            False,
            self._new_check_buckling_ml_numeric.get(),
        ]

        if selected_buckling_checks.count(True) > 1:
            messagebox.showerror('You can only select one buckling type. Reselect.')

            if self._new_check_buckling.get():
                self._new_check_buckling.set(False)
                self._new_check_local_buckling.set(False)

            if self._new_check_buckling_semi_analytical.get():
                self._new_check_buckling_semi_analytical.set(False)

            if self._new_check_buckling_ml_numeric.get():
                self._new_check_buckling_ml_numeric.set(False)

        elif (self._new_check_buckling_semi_analytical.get() or self._new_check_buckling_ml_numeric.get()):
            self._new_check_buckling.set(False)
            self._new_check_local_buckling.set(False)

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
                                                                               init_obj.span,
                                                                               init_obj.girder_lg]))),
                                         font='Verdana 8', fill=init_color)

            self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_s() / 2, ctr_y, ctr_x + m * init_obj.get_s() / 2,
                                              ctr_y - m * init_obj.get_pl_thk(), fill=init_color, stipple=init_stipple)
            self._canvas_opt.create_rectangle(ctr_x - m * init_obj.get_web_thk() / 2, ctr_y - m * init_obj.get_pl_thk(),
                                              ctr_x + m * init_obj.get_web_thk() / 2,
                                              ctr_y - m * (init_obj.get_web_h() + init_obj.get_pl_thk())
                                              , fill=init_color, stipple=init_stipple)
            if init_obj.get_stiffener_type() not in ['L', 'L-bulb']:
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
            if init_obj.get_stiffener_type() not in ['L', 'L-bulb']:
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
                                         text='Optimized - Pl.: ' + str(round(opt_obj.get_s() * 1000, 1)) + 'x' +
                                              str(round(opt_obj.get_pl_thk() * 1000, 1)) + ' Stf.: '
                                              + str(round(opt_obj.get_web_h() * 1000, 1)) +
                                              'x' + str(round(opt_obj.get_web_thk() * 1000, 1)) + '+' +
                                              str(round(opt_obj.get_fl_w() * 1000, 1)) +
                                              'x' + str(round(opt_obj.get_fl_thk() * 1000, 1)),
                                         font='Verdana 8', fill=opt_color)
            self._canvas_opt.create_text(120, 70, text='Weight (per Lg width): '
                                                       + str(int(op.calc_weight([opt_obj.get_s(),
                                                                                 opt_obj.get_pl_thk(),
                                                                                 opt_obj.get_web_h(),
                                                                                 opt_obj.get_web_thk(),
                                                                                 opt_obj.get_fl_w(),
                                                                                 opt_obj.get_fl_thk(),
                                                                                 opt_obj.span,
                                                                                 opt_obj.girder_lg]))),
                                         font='Verdana 8', fill=opt_color)
        else:
            self._canvas_opt.create_text(150, 60, text='No optimized solution found.')

        if line != None:
            if __name__ == '__main__':
                lateral_press = 0.2  # for testing
            else:
                lateral_press = self.app.get_highest_pressure(line)['normal'] / 1e6
            self._canvas_opt.create_text(250, self._prop_canvas_dim[1] - 10,
                                         text='Lateral pressure: ' + str(lateral_press) + ' kPa',
                                         font='Verdana 10 bold', fill='red')

    def draw_select_canvas(self, opt_results=None, save_file=None):
        '''
        Making the lines canvas.
        :return:
        '''
        self._canvas_select.delete('all')
        text_type = 'Verdana 8'

        if opt_results is None:
            # stippled lines and text.

            self._canvas_select.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0],
                                            self._select_canvas_dim[1],
                                            stipple='gray50')
            self._canvas_select.create_line(0, self._canvas_draw_origo[1], self._select_canvas_dim[0],
                                            self._canvas_draw_origo[1],
                                            stipple='gray50')
            self._canvas_select.create_text(self._canvas_draw_origo[0] - 30,
                                            self._canvas_draw_origo[1] + 20, text='(0,0)',
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
                    if self._line_structure_type(line) not in ('GENERAL_INTERNAL_NONWT', 'FRAME'):

                        if line in self._active_lines:
                            self._canvas_select.create_line(coord1, coord2, width=6, fill=color, stipple='gray50')
                            self._canvas_select.create_text(coord1[0] + vector[0] / 2 + 5,
                                                            coord1[1] + vector[1] / 2 + 10,
                                                            text='Line ' + str(get_num(line)), font='Verdand 10 bold',
                                                            fill='red')
                        else:
                            self._canvas_select.create_line(coord1, coord2, width=3, fill=color, stipple='gray25')
                            self._canvas_select.create_text(coord1[0] - 20 + vector[0] / 2 + 5,
                                                            coord1[1] + vector[1] / 2 +

                                                            10, text='line' + str(get_num(line)), font="Text 8",
                                                            fill='black')

                if len(self._opt_frames) != 0:
                    for key, value in self._opt_frames.items():
                        coord1 = self.get_canvas_coord(value[0])
                        coord2 = self.get_canvas_coord(value[1])
                        vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                        self._canvas_select.create_line(coord1, coord2, width=3, fill='SkyBlue1')
                else:
                    pass

            if len(self._active_points) > 1:
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

                    # self._canvas_select.create_polygon(points, outline='#f11',
                    #                       fill='#1f1', width=2)

            # drawing the point dictionary

            for key, value in self._point_dict.items():
                pt_size = 6
                if key in self._active_points:
                    self._canvas_select.create_oval(self.get_point_canvas_coord(key)[0] - pt_size + 2,
                                                    self.get_point_canvas_coord(key)[1] - pt_size + 2,
                                                    self.get_point_canvas_coord(key)[0] + pt_size + 2,
                                                    self.get_point_canvas_coord(key)[1] + pt_size + 2, fill='blue')
                    if self._active_points.index(key) == 0:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14, text='START 1',
                                                        font=text_type, fill='blue')
                    elif self._active_points.index(key) == 1:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14,
                                                        text='STOP 1', font=text_type, fill='blue')
                    elif self._active_points.index(key) == 2:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14,
                                                        text='START 2', font=text_type, fill='blue')
                    elif self._active_points.index(key) == 3:
                        self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                        self.get_point_canvas_coord(key)[1] - 14,
                                                        text='STOP 2', font=text_type, fill='blue')
                    else:
                        pass
                else:
                    self._canvas_select.create_oval(self.get_point_canvas_coord(key)[0] - pt_size,
                                                    self.get_point_canvas_coord(key)[1] - pt_size,
                                                    self.get_point_canvas_coord(key)[0] + pt_size,
                                                    self.get_point_canvas_coord(key)[1] + pt_size, fill='red')

                    self._canvas_select.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                                    self.get_point_canvas_coord(key)[1] - 14,
                                                    text='pt.' + str(get_num(key)),
                                                    font='Verdana 8', fill='blue')
        else:
            self._canvas_select.create_text([20, 20], text='Results are presented here. '
                                                           'All results may not fit the screen. '
                                                           'All results are seen in your saved result file.',
                                            font='Verdana 12 bold',
                                            fill='red', anchor='w')

            delta, start_x, y_loc = 20, 10, 40

            for key, values in opt_results.items():
                # if y_loc > 700:
                #     start_x = 400
                #     y_loc = 40

                y_loc = y_loc + delta
                check_ok = [val[2] is True for val in values[1]]

                if save_file is not None:
                    save_file.write('\n')
                    save_file.write('--------------------------------------------------------------------------' + '\n')
                    save_file.write('Plate fields: ' + str(len(values[2]['objects'])) + ' Frames: ' +
                                    str(len(values[2]['frames'])) + '\n')
                self._canvas_select.create_text([start_x + delta, y_loc],
                                                text=str(len(check_ok)) + ' panels with weight ' + str(
                                                    round(values[0], 1)),
                                                anchor='w', font=text_type)
                y_loc += delta
                item_count, endstring = 0, ''

                for data_idx, data in enumerate(values[1]):
                    for idx, stuc_info in enumerate(data):
                        if isinstance(stuc_info, AllStructure):

                            if y_loc > 700:
                                y_loc = 120
                                start_x += 350
                            if item_count == 0:
                                endstring = ' START 1' + ' OK!\n' if values[1][data_idx][
                                    3] else ' START 1' + ' NOT OK!\n'
                            elif item_count > 0 and item_count < len(values[1]) / 2 - 1 and len(values[1]) != 4:
                                endstring = ' -------' + ' OK!\n' if values[1][data_idx][
                                    3] else ' -------' + ' NOT OK!\n'
                            elif item_count == len(values[1]) / 2 - 1:
                                endstring = ' -END 1-' + ' OK!\n' if values[1][data_idx][
                                    3] else ' -END 1-' + ' NOT OK!\n'
                            elif item_count == len(values[1]) / 2:
                                endstring = ' START 2' + ' OK!\n' if values[1][data_idx][
                                    3] else ' START 2' + ' NOT OK!\n'
                            elif item_count > len(values[1]) / 2 and item_count < len(values[1]) - 1:
                                endstring = ' -------' + ' OK!\n' if values[1][data_idx][
                                    3] else ' -------' + ' NOT OK!\n'
                            elif item_count == len(values[1]) - 1:
                                endstring = ' -END 2-' + ' OK!\n' if values[1][data_idx][
                                    3] else ' -END 2-' + ' NOT OK!\n'
                            self._canvas_select.create_text([start_x + delta, y_loc],
                                                            text=stuc_info.get_one_line_string_mixed() + endstring,
                                                            anchor='w', font=text_type)
                            y_loc += 15

                            if save_file is not None:
                                save_file.write(stuc_info.get_one_line_string_mixed() + ' ' +
                                                stuc_info.get_extended_string_mixed() +
                                                ' | ' + stuc_info.Plate.get_report_stresses() +
                                                endstring)
                            item_count += 1

                if save_file is not None:
                    save_file.write('Weight details for this solution:\n')
                    save_file.write('Weight of main structure: ' + str([str(round(val, 1))
                                                                        for val in values[2]['objects']]) + '\n')
                    save_file.write('Weight of frames:         ' + str([str(round(val, 1))
                                                                        for val in values[2]['frames']]) + '\n')
                    save_file.write('Scales used on frames:    ' +
                                    str([str(round(val, 3)) for val in values[2]['scales']]) + '\n')
                    save_file.write(
                        '----------------------------------------------------------------------------' + '\n')

            if save_file is not None:
                save_file.write('\n -------------  END  ---------------')
                save_file.close()

    def draw_result_text(self, geo_opt_obj, save_to_file=None):
        ''' Textual version of the results. '''

        self._canvas_opt.delete('all')
        start_x = 20
        delta = 25
        start_y = 60
        y_loc = delta + start_y
        xplot = list()
        yplot = list()

        objective_label = self._get_objective_index_label()
        objective_description = (
            'Weight index is tot_weight / max_weight \n'
            'max_weight is the highest total weight of the checked variations.\n'
            'Weight index of 1 is the heaviest calculated variation.'
            if objective_label == 'Weight index' else
            'Objective index is objective / max_objective \n'
            'max_objective is the highest objective value of the checked variations.\n'
            'Objective index of 1 is the highest calculated objective.'
        )

        self._canvas_opt.create_text([start_x, 40],
                                     text='Results seen next. ' + objective_description,
                                     font='Verdana 10', fill='Blue', anchor='w')

        self._canvas_opt.create_text([start_x, y_loc],
                                     text='| Plate fields | Fields length | ' + objective_label + ' | All OK? |',
                                     font='Verdana 10 bold', fill='red', anchor='w')
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
            save_file.write('| Plate fields | Fields length | ' + objective_label + ' | All OK? |\n')
            save_file.write('*********************************************************\n')

        for key, value in self._geo_results.items():
            y_loc = y_loc + delta

            check_ok = [val[2] is True for val in value[1]]

            self._canvas_opt.create_text([start_x + 20, y_loc], text=str(len(check_ok)),
                                         anchor='w', font=text_type)

            self._canvas_opt.create_text([start_x + 120, y_loc], text=str('No results\n' if
                                                                          self._geo_results[key][1][0][0] is None else
                                                                          round(self._geo_results[key][1][0][0].
                                                                                Plate.span, 4)),
                                         anchor='w', font=text_type)
            self._canvas_opt.create_text([start_x + 220, y_loc],
                                         text=str(round(self._geo_results[key][0] / max_weight, 3))
                                         if max_weight != 0 else '',
                                         anchor='w', font=text_type)

            self._canvas_opt.create_text([start_x + 330, y_loc], text=str(all(check_ok)),
                                         anchor='w', font=text_type)

            if save_to_file is not None:
                save_file.write(str(len(check_ok)) + ' ' + 'No results\n' if self._geo_results[key][1][0][0] is None
                                else str(round(self._geo_results[key][1][0][0].Plate.span,
                                               4)) + ' ' +
                                     str(round(self._geo_results[key][0] / max_weight, 3))
                                     + '\n' if max_weight != 0 else
                '' + ' ' + str(all(check_ok)) + '\n')
            if self._geo_results[key][1][0][0] is not None:
                xplot.append(round(self._geo_results[key][1][0][0].Plate.span, 4))
                yplot.append(round(self._geo_results[key][0] / max_weight, 4))

        if save_to_file is not None:
            return save_file, xplot, yplot
        else:
            return None, xplot, yplot

    def _line_structure_bundle(self, line):
        return self._line_to_struc[line]

    def _line_structure(self, line):
        return line_structure.structure(self._line_structure_bundle(line))

    def _line_structure_type(self, line):
        return line_structure.plate(self._line_structure_bundle(line)).get_structure_type()

    def _line_overpressure_side(self, line):
        return self._line_structure(line).overpressure_side

    def _copy_line_structure_bundle(self, line):
        return line_structure.copy_bundle(self._line_structure_bundle(line))

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

    def get_canvas_coord(self, coord):
        '''
        Returning the canvas coordinates of the point. This value will change with slider.
        :param point_no:
        :return:
        '''
        point_coord_x = self._canvas_draw_origo[0] + coord[0] * self._canvas_scale
        point_coord_y = self._canvas_draw_origo[1] - coord[1] * self._canvas_scale

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

    def button_1_click(self, event):
        '''
        When clicking the right button, this method is called.
        method is referenced in
        '''
        self._previous_drag_mouse = [event.x, event.y]
        # if type(self._geo_results) is not list():
        #     if self._geo_results is not None:
        #         return
        # else:
        #     if self._geo_results[0] is not None:
        #         return
        click_x = self._canvas_select.winfo_pointerx() - self._canvas_select.winfo_rootx()
        click_y = self._canvas_select.winfo_pointery() - self._canvas_select.winfo_rooty()

        self._point_is_active = False
        margin = 10
        self._active_point = ''
        for point, coords in self._point_dict.items():
            point_coord = self.get_point_canvas_coord(point)
            if point_coord[0] - margin < click_x < point_coord[0] + margin and \
                    point_coord[1] - margin < click_y < point_coord[1] + margin:
                self._active_point = point
                self._point_is_active = True
                if len(self._active_points) < 4:
                    self._active_points.append(self._active_point)

        if len(self._active_points) == 4:
            self.opt_create_frames(self.opt_get_fractions())

        self.draw_select_canvas()

    def button_3_click(self, event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
        self._previous_drag_mouse = [event.x, event.y]
        self._active_lines = []
        self._active_points = []
        self.draw_select_canvas()

    def button_2_click(self, event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
        self._previous_drag_mouse = [event.x, event.y]

        if self._opt_resutls == {}:
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
                        if key in self._opt_resutls.keys() and self._opt_resutls[key] != None:
                            self.draw_properties(init_obj=self._line_structure(key),
                                                 opt_obj=self._opt_resutls[key][0],
                                                 line=key)
                        else:
                            self.draw_properties(init_obj=self._line_structure(key), line=key)
                        break
                self.draw_select_canvas()
        self.draw_select_canvas()
        self.update_running_time()

        #############################
        self.opt_create_main_structure(self.opt_create_frames(self.opt_get_fractions())[0], self._active_points[0],
                                       self._active_points[1], self._active_points[2], self._active_points[3])

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

    def toggle(self, found_files=None, obj=None, iterating=False, given_path: str = None):
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
            self._toggle_btn.config(bg='salmon')
            self._ent_spacing_upper.config(bg='white')
            self._ent_spacing_lower.config(bg='white')
            self._ent_delta_spacing.config(bg='white')
            self._filez = None
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg='lightgreen')
            self._ent_spacing_upper.config(bg='lightgreen')
            self._ent_spacing_lower.config(bg='lightgreen')
            self._ent_delta_spacing.config(bg='lightgreen')
            self._ent_pl_thk_upper.config(bg='lightgreen')
            self._ent_pl_thk_lower.config(bg='lightgreen')
            self._ent_delta_pl_thk.config(bg='lightgreen')
            if given_path is None:
                self._filez = list(askopenfilenames(parent=self._frame, title='Choose files to open',
                                                    initialdir=self._root_dir))
            else:
                self._filez = [given_path]
            if self._filez == []:
                self._toggle_btn.config(relief="raised")
                self._toggle_btn.config(bg='salmon')
                self._ent_spacing_upper.config(bg='white')
                self._ent_spacing_lower.config(bg='white')
                self._ent_delta_spacing.config(bg='white')
                self._ent_pl_thk_upper.config(bg='white')
                self._ent_pl_thk_lower.config(bg='white')
                self._ent_delta_pl_thk.config(bg='white')

        return found_files, predefined_structure

    def open_example_file(self):
        import os
        if os.path.isfile('sections.csv'):
            os.startfile('sections.csv')
        else:
            os.startfile(self._root_dir + '/' + 'sections.csv')

    def plot_results(self):
        """
        Plot optimization details for a selected panel.

        Handles the default OptionMenu value 'None' safely and verifies that
        the selected panel result has the detailed iteration payload expected
        by op.plot_optimization_results().
        """
        if self._geo_results is None:
            messagebox.showinfo(
                title='No results',
                message='No optimization results are available. Run the optimization first.'
            )
            return

        try:
            fraction_value = self._new_option_fraction.get()
            panel_value = self._new_option_panel.get()
        except TclError:
            messagebox.showinfo(
                title='No panel selected',
                message='Select a valid number of panels and panel index first.'
            )
            return

        try:
            fraction_key = int(fraction_value / 2)
            panel_idx = int(panel_value)
        except (TypeError, ValueError, TclError):
            messagebox.showinfo(
                title='No panel selected',
                message='Select a valid number of panels and panel index first.'
            )
            return

        try:
            panel_result = self._geo_results[fraction_key][1][panel_idx]
        except (KeyError, IndexError, TypeError):
            messagebox.showinfo(
                title='Invalid selection',
                message='The selected panel result could not be found.'
            )
            return

        # op.plot_optimization_results expects the detailed optimization tuple,
        # where item[3] is an iterable of detailed check results.
        try:
            detailed_checks = panel_result[3]
        except (IndexError, TypeError):
            detailed_checks = None

        if not isinstance(detailed_checks, (list, tuple)):
            messagebox.showinfo(
                title='No detailed plot data',
                message=(
                    'This geometric result does not contain detailed iteration '
                    'data for the selected panel. Use the summary figure or '
                    'the textual result table instead.'
                )
            )
            return

        try:
            op.plot_optimization_results(panel_result)
        except Exception as err:
            messagebox.showinfo(
                title='Could not plot selected panel',
                message='The selected panel could not be plotted:\n' + str(err)
            )

    def get_plate_field_options(self, event):

        if self._geo_results is None:
            return

        try:
            fraction_value = self._new_option_fraction.get()
            fraction_key = int(fraction_value / 2)
        except (TypeError, ValueError, TclError):
            return

        if fraction_key not in self._geo_results:
            return

        self._ent_option_field.destroy()
        to_add = tuple([val for val in range(len(self._geo_results[fraction_key][1]))])
        if len(to_add) == 0:
            to_add = (None,)

        self._new_option_panel.set(None)
        self._ent_option_field = tk.OptionMenu(
            self._panel_options_frame,
            self._new_option_panel,
            *to_add,
        )
        self._ent_option_field.grid(row=1, column=1, sticky=tk.W, padx=8)

    def mouse_scroll(self, event):
        self._canvas_scale += event.delta / 50
        self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale

        self.draw_select_canvas()

    def button_2_click_and_drag(self, event):

        self._canvas_draw_origo = (self._canvas_draw_origo[0] - (self._previous_drag_mouse[0] - event.x),
                                   self._canvas_draw_origo[1] - (self._previous_drag_mouse[1] - event.y))

        self._previous_drag_mouse = (event.x, event.y)

        self.draw_select_canvas()


if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateOptGeoWindow(master=root)

    root.mainloop()
