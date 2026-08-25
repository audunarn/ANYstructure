import math
import os  # -*- coding: utf-8 -*-
import weakref
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from typing import Any

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import decimal
from _tkinter import TclError
import multiprocessing
import ctypes
from matplotlib import pyplot as plt
import matplotlib
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics._pairwise_distances_reduction import _datasets_pair, _middle_term_computer

try:
    from anystruct.calc_structure import *
    from anystruct.calc_loads import *
    import anystruct.load_window as load_window
    import anystruct.make_grid_numpy as grid
    import anystruct.grid_window as grid_window
    from anystruct.helper import *
    import anystruct.optimize as op
    import anystruct.optimize_window as opw
    import anystruct.optimize_cylinder as opc
    import anystruct.optimize_multiple_window as opwmult
    import anystruct.optimize_geometry as optgeo
    import anystruct.pl_stf_window as struc
    import anystruct.stresses_window as stress
    import anystruct.fatigue_window as fatigue
    import anystruct.load_factor_window as load_factors
    import anystruct.api_helpers as api_helpers
    import anystruct.ml_models as ml_models
    import anystruct.project_application as project_application
    import anystruct.project_services as project_services
    import anystruct.solid_export as solid_export
    import anystruct.ecosystem_gui as ecosystem_gui
    import anystruct.fe_plate_fields as fe_plate_fields
    import anystruct.fem_integration as fe_runtime_solver
    import anystruct.representation_geometry as representation_geometry
    import anystruct.tkinter_3d_canvas_thickness_v6 as tkinter_3d_canvas
    from anystruct.viewer_backend import (
        BACKEND_LABELS,
        BACKEND_NAMES,
        apply_view_state,
        backend_diagnostic,
        create_3d_viewer,
        event_widget,
        export_view_state,
        normalize_backend,
        viewport_size,
    )
except ModuleNotFoundError:
    # This is due to pyinstaller issues.
    from ANYstructure.anystruct.calc_structure import *
    from ANYstructure.anystruct.calc_loads import *
    import ANYstructure.anystruct.load_window as load_window
    import ANYstructure.anystruct.make_grid_numpy as grid
    import ANYstructure.anystruct.grid_window as grid_window
    from ANYstructure.anystruct.helper import *
    import ANYstructure.anystruct.optimize as op
    import ANYstructure.anystruct.optimize_window as opw
    import ANYstructure.anystruct.optimize_cylinder as opc
    import ANYstructure.anystruct.optimize_multiple_window as opwmult
    import ANYstructure.anystruct.optimize_geometry as optgeo
    import ANYstructure.anystruct.pl_stf_window as struc
    import ANYstructure.anystruct.stresses_window as stress
    import ANYstructure.anystruct.fatigue_window as fatigue
    import ANYstructure.anystruct.load_factor_window as load_factors
    import ANYstructure.anystruct.api_helpers as api_helpers
    import ANYstructure.anystruct.ml_models as ml_models
    import ANYstructure.anystruct.project_application as project_application
    import ANYstructure.anystruct.project_services as project_services
    import ANYstructure.anystruct.solid_export as solid_export
    import ANYstructure.anystruct.ecosystem_gui as ecosystem_gui
    import ANYstructure.anystruct.fe_plate_fields as fe_plate_fields
    import ANYstructure.anystruct.fem_integration as fe_runtime_solver
    import ANYstructure.anystruct.representation_geometry as representation_geometry
    import ANYstructure.anystruct.tkinter_3d_canvas_thickness_v6 as tkinter_3d_canvas
    from ANYstructure.anystruct.viewer_backend import (
        BACKEND_LABELS,
        BACKEND_NAMES,
        apply_view_state,
        backend_diagnostic,
        create_3d_viewer,
        event_widget,
        export_view_state,
        normalize_backend,
        viewport_size,
    )


def _round_calculated(value, decimals: int = 3):
    """Round a value the app calculated before showing it in an input field.

    Conversions (stress <-> force, unit changes) produce long float tails that
    clutter the entries.  Only calculated values pass through here -- text the
    user types is never rounded, so higher manual precision is always allowed.
    """
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return value


@dataclass(frozen=True)
class NewStructureProperties:
    """Resolved structure data needed to add or update one active line."""

    prop_dict: Any
    obj_dict_stf: Any = None
    cylinder_obj: Any = None
    main_dict_cyl: Any = None
    shell_dict: Any = None
    long_dict: Any = None
    ring_stf_dict: Any = None
    ring_frame_dict: Any = None
    geometry: Any = None


class Application():
    '''
    The Application class sets up the GUI using Tkinter.
    It is the main part of the code and calls up all other classes etc.
    '''

    @staticmethod
    def _start_root_fullscreen(parent):
        """Start the main Tk window maximized while keeping normal window chrome."""
        try:
            parent.state('zoomed')
            return
        except Exception:
            pass
        try:
            parent.attributes('-zoomed', True)
            return
        except Exception:
            pass
        try:
            parent.geometry(f'{parent.winfo_screenwidth()}x{parent.winfo_screenheight()}+0+0')
        except Exception:
            pass

    def __init__(self, parent):
        '''
        Initaiting the tkinter frame.
        The GUI is general initiated in the method gui_init.
        :param parent:
        '''

        super(Application, self).__init__()
        parent.wm_title('| ANYstructure |')
        self._start_root_fullscreen(parent)
        self._parent = parent
        self._renderer_requested = "auto"
        self._renderer_backend_choice = tk.StringVar(value="Automatic")
        self._renderer_backend_status = tk.StringVar(value="Renderer: Automatic")
        self._runtime_fem_windows = weakref.WeakSet()
        self._resize_after_id = None
        self._last_resize_size = (0, 0)
        parent.protocol("WM_DELETE_WINDOW", self.close_main_window)
        parent.bind("<Configure>", self.resize)

        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        # self._root_dir = os.path.dirname(os.path.abspath(__file__)).replace('anystruct','')
        # Main frame for the application
        self._main_fr = ttk.Frame(parent)
        self._main_fr.place(in_=parent, relwidth=1, relheight=0.99)

        # Definng general colors
        self._general_color = 'alice blue'  # "'azure2'  # Color for backgrounds.
        self._entry_color = 'white'  # Entry fields color.
        self._entry_text_color = 'black'  # Entry field tex color
        self._button_bg_color = 'LightBlue1'
        self._button_fg_color = 'black'
        self._color_text = 'white'

        ''' Setting the style of ttk'''
        #
        self._style = ttk.Style(parent)

        # vista theme not available in linux
        try:
            # self._style.theme_use('xpnative')
            # self._style.theme_use('ITFT1')
            self._style.theme_use('vista')
        except:
            print('Alternative theme')
            # available themes in linux:
            # ('clam', 'alt', 'default', 'classic')
            self._style.theme_use('clam')

        self._style.layout("TNotebook", [])
        self._style.configure("TNotebook", tabmargins=0)

        # tabbed frames
        self._tabControl = ttk.Notebook(parent)
        self._tab_geo = ttk.Frame(self._tabControl, relief='flat')
        self._tab_prop = ttk.Frame(self._tabControl, relief='flat')
        self._tab_comp = ttk.Frame(self._tabControl, relief='flat')
        self._tab_prop_tools = ttk.Frame(self._tabControl, relief='flat')
        self._tab_information = ttk.Frame(self._tabControl, relief='flat')
        self._tab_help = ttk.Frame(self._tabControl, relief='flat')

        self._tabControl.add(self._tab_geo, text='Geometry')
        self._tabControl.add(self._tab_prop, text='Line properties')
        self._tabControl.add(self._tab_prop_tools, text='Properties tools')
        self._tabControl.add(self._tab_comp, text='Compartments and loads')
        self._tabControl.add(self._tab_information, text='Information')
        self._tabControl.add(self._tab_help, text='Help')

        self._tabControl.place(relwidth=0.2585, relheight=1)
        # self._tabControl.select(self._tab2)

        # Top open/save/new
        menu = tk.Menu(parent)
        parent.config(menu=menu)
        # menu, canvas, etc.
        sub_menu = tk.Menu(menu)
        menu.add_cascade(label='File', menu=sub_menu)
        sub_menu.add_command(label='New project', command=self.reset)
        sub_menu.add_command(label='Save project as...', command=self.savefile)
        self.__last_save_file = None  # Keeping the last filename and path
        sub_menu.add_command(label='Save project, Alt-S', command=self.save_no_dialogue)
        sub_menu.add_command(label='Open project', command=self.openfile)
        sub_menu.add_command(label='Restore previous', command=self.restore_previous)
        sub_menu.add_command(label='Open excel input', command=self.open_excel_file)
        sub_menu.add_separator()
        self._file_menu = sub_menu
        sub_menu.add_command(label='Open FEA result buckling files...', command=self.open_fea_buckling_files)
        sub_menu.add_command(label='Import FEM and run in fe-solver', command=self.on_import_fem_and_run_solver)
        sub_menu.add_command(label='Inspect FE/interchange file...', command=self.on_open_file_inspector)
        file_export_menu = tk.Menu(sub_menu)
        sub_menu.add_cascade(label='Export', menu=file_export_menu)
        file_export_menu.add_command(label='Geometry to SESAM GeniE JS...', command=self.export_to_js)
        file_export_menu.add_command(label='Selected structure IFC/CAD solid model...',
                                     command=self.export_prop_3d_ifc_model)
        file_export_menu.add_command(label='Selected structure IFC/CAD shell/surface model...',
                                     command=self.export_prop_3d_ifc_shell_model)
        self._shortcut_text = 'CTRL-Z Undo geometry action\n' \
                              'CTRL-P Copy selected point\n' \
                              'CTRL-M Move selected point)\n' \
                              'CTRL-N Move selected line)\n' \
                              'CTRL-Q New line (right click two points)\n' \
                              'CTRL-S Assign structure prop. to line\n' \
                              'CTRL-A Select all lines (change param)\n' \
                              'CTRL-T Select all structure types (selected)\n' \
                              'CTRL-DELETE Delete structure prop. from line\n' \
                              'DELETE Delete active line and/or point \n' \
                              'CTRL-E Copy line properties from active line\n' \
                              'CTRL-D Paste line propeties to active line\n' \
                              'Mouse click left/right - select line/point\n' \
                              'Arrows left/right - previous/next line\n' \
                              'Arrows up/down - previous/next point'

        ''' END style setting'''

        undo_redo = tk.Menu(menu)
        menu.add_cascade(label='Geometry', menu=undo_redo)
        undo_redo.add_command(label='Undo geometry action (CTRL-Z)', command=self.undo)
        # undo_redo.add_command(label='Redo geometry action (CTRL-Y)', command=self.redo)
        undo_redo.add_command(label='Copy selected point (CTRL-P)', command=self.copy_point)
        undo_redo.add_command(label='Move selected point (CTRL-M)', command=self.move_point)
        undo_redo.add_command(label='Move selected line (CTRL-N)', command=self.move_line)
        undo_redo.add_command(label='New line (right click two points) (CTRL-Q)', command=self.new_line)
        undo_redo.add_command(label='Assign structure properties to clicked line (CTRL-S)',
                              command=self.new_structure)
        undo_redo.add_command(label='Delete structure properties from clicked line (CTRL-DELETE)',
                              command=self.delete_properties_pressed)
        undo_redo.add_command(label='Delete active line and/or point (DELETE)',
                              command=self.delete_key_pressed)
        undo_redo.add_command(label='Copy line properties from active line (CTRL-E)',
                              command=self.copy_property)
        undo_redo.add_command(label='Paste line propeties to active line (CTRL-D)',
                              command=self.paste_property)

        sub_report = tk.Menu(menu)
        menu.add_cascade(label='Reporting', menu=sub_report)
        sub_report.add_command(label='Generate PDF report', command=self.report_generate)
        sub_report.add_command(label='Generate PDF result table', command=self.table_generate)

        sub_report.add_command(label='Stiffened flat plate - Weight development, plates and beams',
                               command=self.on_plot_cog_dev)

        sub_sesam = tk.Menu(menu)
        menu.add_cascade(label='Interfaces', menu=sub_sesam)
        sub_sesam.add_command(label='Export geometry to SESAM GeniE JS', command=self.export_to_js)
        sub_sesam.add_command(label='Import excel file', command=self.open_excel_file)
        sub_sesam.add_separator()
        sub_sesam.add_command(label='Choose/edit material (ANYmaterial)...', command=self.on_open_material_editor)
        sub_sesam.add_command(label='Open mesher (ANYmesher)...', command=self.on_open_mesher)
        sub_sesam.add_command(label='Inspect FE file (ANYfileio)...', command=self.on_open_file_inspector)

        sub_help = tk.Menu(menu)
        menu.add_cascade(label='Help', menu=sub_help)
        sub_help.add_command(label='Open website (documentation etc.)', command=self.open_documentation)
        sub_help.add_command(label='Open documentation pdf', command=self.open_documentation_pdf)
        sub_help.add_command(label='Donate!', command=self.open_donate)
        sub_help.add_command(label='Open example file', command=self.open_example)
        sub_help.add_command(label='Open example excel input file', command=self.open_example_excel_file)
        sub_help.add_command(label='About ANYstructure', command=self.open_about)

        sub_colors = tk.Menu(menu)
        menu.add_cascade(label='GUI', menu=sub_colors)
        sub_colors.add_command(label='Colors - Default', command=lambda id="default": self.set_colors(id))
        sub_colors.add_command(label='Colors - Light', command=lambda id="light": self.set_colors(id))
        sub_colors.add_command(label='Colors - Grey', command=lambda id="grey": self.set_colors(id))
        sub_colors.add_command(label='Colors - Dark', command=lambda id="dark": self.set_colors(id))
        sub_colors.add_command(label='Colors - Unicorn', command=lambda id="pink": self.set_colors(id))
        sub_colors.add_command(label='Colors - Slava Ukraini', command=lambda id="SlavaUkraini": self.set_colors(id))
        sub_colors.add_command(label='Functional - All items', command=lambda id="all items": self.set_colors(id))
        sub_colors.add_command(label='Functional - Modelling', command=lambda id="modelling": self.set_colors(id))
        sub_colors.add_command(label='Functional - Cylinder', command=lambda id="cylinder": self.set_colors(id))
        sub_colors.add_separator()
        sub_colors.add_command(label='Mode - Single panel/cylinder', command=self.switch_to_single_calculation_mode)
        sub_colors.add_command(label='Mode - Multiple panels', command=self.switch_to_multiple_calculation_mode)
        sub_colors.add_command(label='Mode - FEA result buckling', command=self.switch_to_fea_result_buckling_mode)
        self._gui_menu = sub_colors

        # base_mult = 1.2
        # base_canvas_dim = [int(1000 * base_mult),int(720*base_mult)]  #do not modify this, sets the "orignal" canvas dimensions.
        base_canvas_dim = (1000, 720)  # do not modify this, sets the "orignal" canvas dimensions.

        self._canvas_dim = [int(base_canvas_dim[0] * 1),
                            int(base_canvas_dim[1] * 1)]
        self._canvas_base_origo = [50, base_canvas_dim[1] - 50]  # 50 bottom left location of the canvas, (0,0)

        self._canvas_draw_origo = [self._canvas_base_origo[0], self._canvas_base_origo[1] + 10]
        self._previous_drag_mouse = list(self._canvas_draw_origo)

        # Setting the fonts for all items in the application.

        self.text_scale = 1
        self._text_size = {'Text 14 bold': 'Verdana ' + str(int(14 * self.text_scale)) + ' bold',
                           'Text 16 bold': 'Verdana ' + str(int(16 * self.text_scale)) + ' bold',
                           'Text 18 bold': 'Verdana ' + str(int(18 * self.text_scale)) + ' bold',
                           'Text 12 bold': 'Verdana ' + str(int(12 * self.text_scale)) + ' bold',
                           'Text 10 bold': 'Verdana ' + str(int(10 * self.text_scale)) + ' bold',
                           'Text 9 bold': 'Verdana ' + str(int(9 * self.text_scale)) + ' bold',
                           'Text 8 bold': 'Verdana ' + str(int(8 * self.text_scale)) + ' bold',
                           'Text 8': 'Verdana ' + str(int(8 * self.text_scale)),
                           'Text 9': 'Verdana ' + str(int(8 * self.text_scale)),
                           'Text 7': 'Verdana ' + str(int(7 * self.text_scale)),
                           'Text 10': 'Verdana ' + str(int(10 * self.text_scale)),
                           'Text 7 bold': 'Verdana ' + str(int(7 * self.text_scale)) + ' bold',
                           'Text 6 bold': 'Verdana ' + str(int(6 * self.text_scale)) + ' bold'}

        self._canvas_scale = 20  # Used for slider and can change
        self._base_scale_factor = 10  # Used for grid and will not change, 10 is default
        self._prop_canvas_scale = 100  # Scrolling for property canvas
        # self._prop_canvas_x_base =
        # self._prop_canvas_y_base =

        # # Creating the various canvas next.
        self._main_canvas = tk.Canvas(self._main_fr,
                                      background=self._style.lookup('TFrame', 'background'), bd=0,
                                      highlightthickness=0, relief='ridge')
        self._prop_canvas = tk.Canvas(self._main_fr,
                                      background=self._style.lookup('TFrame', 'background'), bd=0,
                                      highlightthickness=0, relief='ridge')
        self._result_canvas = tk.Canvas(self._main_fr,
                                        background=self._style.lookup('TFrame', 'background'), bd=0,
                                        highlightthickness=0, relief='ridge')

        # # These frames are just visual separations in the GUI.
        # frame_horizontal, frame_vertical = 0.73, 0.258
        # self._frame_viz_hor = tk.Frame(self._main_fr, height=3, bg="black", colormap="new")
        # self._frame_viz_hor.place(relx=0, rely=frame_horizontal, relwidth=1)
        # self._frame_viz_ver = tk.Frame(self._main_fr, width=3, bg="black", colormap="new")
        # self._frame_viz_ver.place(relx=frame_vertical,rely=0 * 1, relheight=1)

        x_canvas_place = 0.26
        self._main_canvas.place(relx=x_canvas_place, rely=0, relwidth=0.523, relheight=0.73)
        self._prop_canvas.place(relx=x_canvas_place, rely=0.73, relwidth=0.38, relheight=0.27)
        self._result_canvas.place(relx=x_canvas_place + 0.38, rely=0.73, relwidth=0.36, relheight=0.27)

        self._simplified_calculation_mode = False
        self._single_line_name = 'line1'
        self._fea_buckling_mode = False
        self._fea_buckling_session = None
        self._fea_selected_panel_id = None
        self._fea_last_inp_path = None
        self._fea_last_frd_path = None
        self._fea_last_runtime_result = None
        self._fea_panel_canvas_items = {}
        self._fea_3d_panel_artists = {}
        self._fea_3d_panel_records = {}
        self._fea_3d_selected_overlay = None
        self._fea_buckling_created = []
        self._fea_panel_line_by_field = {}
        self._fea_imported_line_names = []
        self._fea_imported_point_names = []
        self._fea_imported_endpoint_keys = []
        self._fea_pick_cid = None
        self._fea_pick_after_id = None
        self._fea_uf_color_lower = tk.DoubleVar()
        self._fea_uf_color_upper = tk.DoubleVar()
        self._fea_uf_color_lower.set(0.0)
        self._fea_uf_color_upper.set(1.5)
        self._fea_stress_reduction_method = tk.StringVar()
        self._fea_stress_reduction_method.set(fe_plate_fields.available_stress_reduction_methods()[0])
        self._fea_show_uf_text = tk.BooleanVar(value=False)
        self._fea_show_panel_text = tk.BooleanVar(value=False)
        self._fea_show_local_x_arrow = tk.BooleanVar(value=False)
        self._fea_show_local_y_arrow = tk.BooleanVar(value=False)
        self._fea_show_mesh = tk.BooleanVar(value=False)
        self._fea_color_code = tk.BooleanVar(value=True)

        # Optional Matplotlib based 3D preview. In simplified mode this is promoted
        # to the large main pane; otherwise it remains in the lower property canvas.
        self._new_show_prop_3d = tk.BooleanVar()
        self._new_show_prop_3d.set(self._simplified_calculation_mode)
        self._new_prop_3d_opposite_side = tk.BooleanVar()
        self._new_prop_3d_opposite_side.set(False)
        self._prop_3d_canvas_widget = None
        self._prop_3d_fig_canvas = None
        self._prop_3d_frame = None
        self._prop_3d_toolbar = None
        self._prop_3d_axes = None
        self._prop_3d_tk3d_canvas = None
        self._prop_3d_export_mesh = None
        self._prop_3d_shell_export_mesh = None
        self._prop_3d_default_view = (22, -55)
        self._prop_3d_resize_after_id = None
        self._selected_prepomax_imperfection_row = 0

        # Point frame
        self._pt_frame = tk.Frame(self._main_canvas, width=100, height=100, bg="black", relief='raised')
        # Cylinder gui look placement of optmization button
        self._gui_functional_look_cylinder_opt = [0.82, 0.008, 0.04, 0.175]
        #
        # -------------------------------------------------------------------------------------------------------------
        #
        # The dictionaries below are the main deictionaries used to define this application.
        self._point_dict = {}  # Main point dictionary (point:coords) - see method new_point
        self._line_dict = {}  # Main line dictionary (line:point,point) - see method new_line
        self._line_to_struc = {}  # Main line assosiations (line:various objects) - see method new_structure
        # The dictionary is widely used and includes all classes in the program
        # Example:
        # 'line1':[Structure,CalcScantlings,Fatigue,Load,Combinations]
        self._tank_dict = {}  # Main tank dictionary (created when BFS search is executed for the grid) (comp# : TankObj)
        self._load_dict = {}  # Main load dictionary (created in separate load window (load# : [LoadObj, lines])
        self._new_load_comb_dict = {}  # Load combination dict.(comb,line,load) : [DoubleVar(), DoubleVar(), IntVar()]
        # Example ('dnva', 'line25', 'comp3'),  ('dnvb', 'line14', 'comp4'),
        # ('manual', 'line74', 'manual'), ('tanktest', 'line76', 'comp3')
        self._sections = list()  # A list containing section property objects.
        #
        # -------------------------------------------------------------------------------------------------------------
        #
        self._pending_grid_draw = {}  # Saving lines that shall be transferred to the calculation grid
        # Load combinations definition used in method gui_load_combinations
        # These are created and destroyed and is not permanent in the application.
        self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created = [], [], [], []
        self._state_logger = dict()  # Used to see if recalculation is needed.
        self._weight_logger = {
            'new structure': {'COG': list(), 'weight': list(), 'time': list()}}  # Recording of weight development

        # The next dictionaries feed various infomation to the application
        self._load_factors_dict = {'dnva': [1.3, 1.2, 0.7], 'dnvb': [1, 1, 1.2],
                                   'tanktest': [1, 1, 0]}  # DNV  loads factors
        self._accelerations_dict = {'static': 9.81, 'dyn_loaded': 0, 'dyn_ballast': 0}  # Vertical acclerations
        self._load_conditions = ['loaded', 'ballast', 'tanktest', 'part',
                                 'slamming']  # Should not be modified. Load conditions.
        self._tank_options = {'ballast': 1025, 'crude_oil': 900, 'diesel': 850, 'slop': 1050,
                              'fresh water': 1000}  # Should not be modified.
        self._default_stresses = {'BOTTOM': (100, 100, 50, 50, 5), 'BBS': (70, 70, 30, 30, 3), 'BBT': (80, 80, 30, 3),
                                  'HOPPER': (70, 70, 50, 50, 3),
                                  'SIDE_SHELL': (100, 100, 40, 40, 3), 'INNER_SIDE': (80, 80, 40, 40, 5),
                                  'FRAME': (70, 70, 60, 0, 10),
                                  'FRAME_WT': (70, 70, 60, 0, 10), 'SSS': (100, 100, 50, 50, 20),
                                  'MD': (70, 70, 4, 40, 3),
                                  'GENERAL_INTERNAL_WT': (90, 90, 40, 40, 5),
                                  'GENERAL_INTERNAL_NONWT': (70, 70, 30, 30, 3),
                                  'INTERNAL_1_MPA': (1, 1, 1, 1, 1), 'INTERNAL_LOW_STRESS_WT': (40, 40, 20, 20, 5)}
        # The default stresses are used for buckling calculations.
        self._structure_types = {'vertical': ['BBS', 'SIDE_SHELL', 'SSS'],
                                 'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                                 'non-wt': ['FRAME', 'GENERAL_INTERNAL_NONWT'],
                                 'internals': ['INNER_SIDE', 'FRAME_WT', 'GENERAL_INTERNAL_WT',
                                               'INTERNAL_ZERO_STRESS_WT', 'INTERNAL_LOW_STRESS_WT']}
        self._options_type = [op_typ for op_typ in self._default_stresses.keys()]
        self._point_options = ['fixed', 'free']
        self._load_window_couter = 1  # this is used to create the naming of the tanks in the load window
        self._logger = {'added': list(),
                        'deleted': list()}  # used to log operations for geometry operations, to be used for undo/redo
        self.__returned_load_data = None  # Temporary data for returned loads from the load window.
        self.__previous_load_data = None  # Used to compare loads before and after.
        self.__copied_line_prop = None  # Used to copy line properties to another.

        self._center_of_buoyancy = dict()  # Center of buoyancy for all and for carious static drafts
        # Example {8: (5,20), 22: (12,20), 'all': (16,20)}

        self._ML_buckling = ml_models.load_buckling_models((self._root_dir,))
        self._ML_classes = ml_models.default_ml_class_messages()

        # Used to select parameter
        self._stuctural_definition = ['mat_yield', 'mat_factor', 'span', 'spacing', 'plate_thk', 'stf_web_height',
                                      'stf_web_thk',
                                      'stf_flange_width', 'stf_flange_thk', 'structure_type', 'stf_type',
                                      'sigma_y1', 'sigma_y2', 'sigma_x1', 'sigma_x2', 'tau_xy', 'plate_kpp', 'stf_kps',
                                      'stf_km1',
                                      'stf_km2', 'stf_km3', 'press_side', 'zstar_optimization',
                                      'puls buckling method', 'puls boundary', 'puls stiffener end', 'puls sp or up',
                                      'puls up boundary']
        self._p1_p2_select = False
        self._line_is_active = False  # True when a line is clicked
        self._active_line = ''  # Name of the clicked point
        self._point_is_active = False  # True when a point is clicked
        self._active_point = ''  # Name of the clicked point
        self.controls()  # Function to activate mouse clicks
        self._line_point_to_point_string = []  # This one ensures that a line is not created on top of a line
        self._multiselect_lines = []  # A list used to select many lines. Used to set properties.

        # Initsializing the calculation grid used for tank definition
        self._grid_dimensions = [self._canvas_base_origo[1] + 1, base_canvas_dim[0] - self._canvas_base_origo[0] + 1]

        # self._grid_dimensions = [self._canvas_base_origo[1], base_canvas_dim[0] - self._canvas_base_origo[0] + 1]

        self._main_grid = grid.Grid(self._grid_dimensions[0], self._grid_dimensions[1])
        self._grid_calc = None
        self.text_widget = None
        self._clicked_section_create = None  # Identifiation of the button clicked. Sections.
        self._gui_functional_look = 'all items'  # used to change size and location of frames, canvas etc.

        # These sets the location where entries are placed.
        ent_x = 0.4
        delta_y = 0.025
        delta_x = 0.1
        point_x_start, point_start = 0.005208333, 0.13

        # ----------------------INITIATION OF THE SMALLER PARTS OF THE GUI STARTS HERE--------------------------
        # Help tab
        ttk.Label(self._tab_help, text='Buckling paramenter, flat plates', font=self._text_size["Text 10 bold"], ) \
            .place(relx=0.01, rely=0.05, )
        try:
            img_file_name = 'Panel_geometry_definitions.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            label = tk.Label(self._tab_help, image=photo)
            label.image = photo  # keep a reference!
            label.place(relx=0.01, rely=0.1)
        except TclError:
            pass
        ttk.Label(self._tab_help, text='Buckling parameters, cylinders', font=self._text_size["Text 10 bold"], ) \
            .place(relx=0.01, rely=0.33)
        try:
            img_file_name = 'Buckling_Strength_of_Shells.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            label = tk.Label(self._tab_help, image=photo)
            label.image = photo  # keep a reference!
            label.place(relx=0.01, rely=0.35)
        except TclError:
            pass
        ttk.Label(self._tab_help, text='Buckling cylinder panels', font=self._text_size["Text 10 bold"], ) \
            .place(relx=0.01, rely=0.6)
        try:
            img_file_name = 'buckling_cylinder_panel.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            label = tk.Label(self._tab_help, image=photo)
            label.image = photo  # keep a reference!
            label.place(relx=0.01, rely=0.62)
        except TclError:
            pass

        # --- point input/output ----

        self._new_point_x = tk.DoubleVar()
        self._new_point_y = tk.DoubleVar()
        self._new_point_fix = tk.StringVar()
        self._new_zstar_optimization = tk.BooleanVar()
        self._new_zstar_optimization.set(True)
        ent_width = 6  # width of entries

        self._project_information = tk.Text(self._tab_geo, wrap=tk.WORD, relief=tk.FLAT)
        self._project_information.place(relx=0.005, rely=0.005, relwidth=0.95, relheight=0.1)

        self._project_information.insert(1.0, 'No information on project provided. Input here.')

        ttk.Label(self._tab_geo, text='Input point coordinates [mm]', font=self._text_size['Text 9 bold'],
                  ) \
            .place(rely=point_start, relx=point_x_start, anchor=tk.NW)
        ttk.Label(self._tab_geo, text='Point x (horizontal) [mm]:', font=self._text_size["Text 9"], ) \
            .place(relx=point_x_start, rely=point_start + delta_y, )
        ttk.Label(self._tab_geo, text='Point y (vertical)   [mm]:', font=self._text_size["Text 9"], ) \
            .place(relx=point_x_start, rely=point_start + delta_y * 2)

        ttk.Entry(self._tab_geo, textvariable=self._new_point_x, width=int(ent_width * 1.5)) \
            .place(relx=ent_x, rely=point_start + delta_y)
        ttk.Entry(self._tab_geo, textvariable=self._new_point_y, width=int(ent_width * 1.5)) \
            .place(relx=ent_x, rely=point_start + delta_y * 2)

        ttk.Button(self._tab_geo, text='Add point (coords)', command=self.new_point, style="Bold.TButton") \
            .place(relx=ent_x + 2 * delta_x, rely=point_start + 1 * delta_y, relwidth=0.3)
        ttk.Button(self._tab_geo, text='Copy point (relative)', command=self.copy_point, style="Bold.TButton") \
            .place(relx=ent_x + 2 * delta_x, rely=point_start + 2 * delta_y, relwidth=0.3)
        ttk.Button(self._tab_geo, text='Move point', command=self.move_point, style="Bold.TButton") \
            .place(relx=ent_x + 2 * delta_x, rely=point_start + 3 * delta_y, relwidth=0.3)
        ttk.Button(self._tab_geo, text='Move line', command=self.move_line, style="Bold.TButton") \
            .place(relx=ent_x + 2 * delta_x, rely=point_start + 4 * delta_y, relwidth=0.3)

        self._new_draw_point_name = tk.BooleanVar()
        self._new_draw_point_name.set(False)
        ttk.Label(self._tab_geo, text='Show point names in GUI', font=self._text_size["Text 9"]) \
            .place(relx=point_x_start, rely=point_start + 3 * delta_y)
        ttk.Checkbutton(self._tab_geo, variable=self._new_draw_point_name, command=self.on_color_code_check) \
            .place(relx=ent_x, rely=point_start + 3 * delta_y)

        self._new_line_name = tk.BooleanVar()
        self._new_line_name.set(False)

        line_start, line_x = point_start + 0.2, 0.0055
        ttk.Label(self._tab_geo, text='Input line from "point number" to "point number"',
                  font=self._text_size['Text 9 bold'], ) \
            .place(rely=line_start, relx=line_x, anchor=tk.NW)
        ttk.Label(self._tab_geo, text='Line from point number:', font=self._text_size["Text 9"], ) \
            .place(relx=line_x, rely=line_start + delta_y)
        ttk.Label(self._tab_geo, text='Line to point number:', font=self._text_size["Text 9"], ) \
            .place(relx=line_x, rely=line_start + 2 * delta_y)
        ttk.Label(self._tab_geo, text='Show line names in GUI', font=self._text_size["Text 9"]).place(relx=point_x_start,
                                                                                     rely=line_start + 3 * delta_y)
        ttk.Checkbutton(self._tab_geo, variable=self._new_line_name,
                        command=self.on_color_code_check).place(relx=ent_x, rely=line_start + 3 * delta_y)

        # --- line input/output ---
        self._new_line_p1 = tk.IntVar()
        self._new_line_p2 = tk.IntVar()

        # Check boxes
        self._new_shortcut_backdrop = tk.BooleanVar()
        self._new_shortcut_backdrop.set(False)
        self._new_colorcode_beams = tk.BooleanVar()
        self._new_colorcode_beams.set(False)
        self._new_colorcode_plates = tk.BooleanVar()
        self._new_colorcode_plates.set(False)
        self._new_colorcode_pressure = tk.BooleanVar()
        self._new_colorcode_plates.set(False)
        self._new_colorcode_utilization = tk.BooleanVar()
        self._new_colorcode_utilization.set(False)
        self._new_label_color_coding = tk.BooleanVar()
        self._new_label_color_coding.set(False)

        self._new_colorcode_sigmax = tk.BooleanVar()
        self._new_colorcode_sigmax.set(False)
        self._new_colorcode_sigmay1 = tk.BooleanVar()
        self._new_colorcode_sigmay1.set(False)
        self._new_colorcode_sigmay2 = tk.BooleanVar()
        self._new_colorcode_sigmay2.set(False)
        self._new_colorcode_tauxy = tk.BooleanVar()
        self._new_colorcode_tauxy.set(False)
        self._new_colorcode_structure_type = tk.BooleanVar()
        self._new_colorcode_structure_type.set(False)
        self._new_colorcode_section_modulus = tk.BooleanVar()
        self._new_colorcode_section_modulus.set(False)
        self._new_colorcode_fatigue = tk.BooleanVar()
        self._new_colorcode_fatigue.set(False)
        self._new_colorcode_puls_sp_or_up = tk.BooleanVar()
        self._new_colorcode_puls_sp_or_up.set(False)
        self._new_colorcode_puls_acceptance = tk.BooleanVar()
        self._new_colorcode_puls_acceptance.set(False)
        self._new_colorcode_total = tk.BooleanVar()
        self._new_colorcode_total.set(False)
        self._new_colorcode_spacing = tk.BooleanVar()
        self._new_colorcode_spacing.set(False)
        self._new_toggle_var = tk.StringVar()
        self._new_toggle_select_multiple = tk.BooleanVar()
        self._new_toggle_puls = tk.BooleanVar()
        self._new_toggle_puls.set(False)
        self._new_scale_stresses = tk.BooleanVar()
        self._new_scale_stresses.set(False)
        self._new_fup = tk.DoubleVar()
        self._new_fup.set(0.5)
        self._new_fdwn = tk.DoubleVar()
        self._new_fdwn.set(1)
        self._new_shifted_coords = tk.BooleanVar()
        self._new_shifted_coords.set(False)
        self._new_show_cog = tk.BooleanVar()
        self._new_show_cog.set(False)
        self._new_content_type = tk.StringVar()
        self._new_content_type.set('ballast')
        self._new_panel_or_shell = tk.StringVar()
        self._new_panel_or_shell.set('panel')
        self._new_shift_viz_coord_ver = tk.DoubleVar()
        self._new_shift_viz_coord_ver.set(0)
        self._new_shift_viz_coord_hor = tk.DoubleVar()
        self._new_shift_viz_coord_hor.set(0)

        line_start, line_x = point_start + 0.2, 0.0055

        ttk.Spinbox(self._tab_geo, textvariable=self._new_line_p1, width=int(ent_width * 1), from_=0,
                    to=float('inf')).place(relx=ent_x, rely=line_start + 1 * delta_y)
        ttk.Spinbox(self._tab_geo, textvariable=self._new_line_p2, width=int(ent_width * 1),
                    from_=0, to=float('inf')).place(relx=ent_x, rely=line_start + 2 * delta_y)

        ttk.Button(self._tab_geo, text='Add line', command=self.new_line, style="Bold.TButton") \
            .place(relx=ent_x + 2 * delta_x, rely=line_start + delta_y, relwidth=0.3)

        # --- delete points and lines ---
        self._new_delete_line = tk.IntVar()
        self._new_delete_point = tk.IntVar()
        del_start, del_x = line_start + 0.2, 0.005208333
        ttk.Label(self._tab_geo, text='Delete lines and points (or left/right click and use "Delete key")',
                  font=self._text_size['Text 9 bold'], ) \
            .place(rely=del_start - 0.02, relx=del_x, anchor=tk.NW)
        self._ent_delete_line = ttk.Spinbox(self._tab_geo, textvariable=self._new_delete_line,
                                            from_=0, to=float('inf'),
                                            width=int(ent_width * 1))
        self._ent_delete_line.place(relx=ent_x, rely=del_start + delta_y)

        self._ent_delete_point = ttk.Spinbox(self._tab_geo, textvariable=self._new_delete_point,
                                             from_=0, to=float('inf'),
                                             width=int(ent_width * 1))
        self._ent_delete_point.place(relx=ent_x, rely=del_start + delta_y * 2)

        ttk.Label(self._tab_geo, text='Line number (left click):', font=self._text_size["Text 9"]) \
            .place(relx=del_x, rely=del_start + delta_y)
        ttk.Label(self._tab_geo, text='Point number (right click):', font=self._text_size["Text 9"], ) \
            .place(relx=del_x, rely=del_start + delta_y * 2)

        ttk.Button(self._tab_geo, text='Delete line', command=self.delete_line, style="Bold.TButton"
                   ).place(relx=ent_x + delta_x * 2, rely=del_start + delta_y,
                           relwidth=0.3)
        ttk.Button(self._tab_geo, text='Delete prop.', command=self.delete_properties_pressed, style="Bold.TButton"
                   ).place(relx=ent_x + delta_x * 2, rely=del_start + delta_y * 2,
                           relwidth=0.3)

        ttk.Button(self._tab_geo, text='Delete point', command=self.delete_point, style="Bold.TButton"
                   ).place(relx=ent_x + 2 * delta_x, rely=del_start + delta_y * 3,
                           relwidth=0.3)

        # Shifing of coordinate display
        shift_x = del_x
        shift_y = del_start + 0.2
        ttk.Label(self._tab_geo, text='Shift coordinate labeling [mm]: ', font=self._text_size['Text 8 bold']) \
            .place(relx=shift_x, rely=shift_y - delta_y * 0.5)
        ttk.Label(self._tab_geo, text='Used if you want a different origin of the repoted coordinates. \n'
                                      'Does not affect loads.', font=self._text_size['Text 8']) \
            .place(relx=shift_x, rely=shift_y + delta_y * 0.5)

        ttk.Label(self._tab_geo, text='y shift', font=self._text_size['Text 8'],
                  ).place(relx=shift_x, rely=shift_y + delta_y * 2)
        ttk.Label(self._tab_geo, text='x shift ', font=self._text_size['Text 8'],
                  ).place(relx=shift_x, rely=shift_y + delta_y * 3)

        self._ent_shift_hor = ttk.Entry(self._tab_geo, textvariable=self._new_shift_viz_coord_hor,
                                        width=ent_width)

        self._ent_shift_hor.bind('<FocusOut>', self.trace_shift_change)
        self._ent_shift_ver = ttk.Entry(self._tab_geo, textvariable=self._new_shift_viz_coord_ver,
                                        width=ent_width,
                                        )
        self._ent_shift_ver.bind('<FocusOut>', self.trace_shift_change)
        # self._ent_shift_ver.trace('w', self.trace_shift_change)
        self._ent_shift_hor.place(relx=ent_x, rely=shift_y + delta_y * 2)
        self._ent_shift_ver.place(relx=ent_x, rely=shift_y + delta_y * 3)

        ttk.Label(self._tab_geo, text='Use shifted coordinates', font=self._text_size["Text 9"]) \
            .place(relx=shift_x, rely=shift_y + delta_y * 4)
        ttk.Checkbutton(self._tab_geo, variable=self._new_shifted_coords, command=self.update_frame) \
            .place(relx=ent_x, rely=shift_y + delta_y * 4)

        # --- structure type information ---

        def show_message():
            messagebox.showinfo(title='Structure type', message='Types - sets default stresses (sigy1/sigy2/sigx/tauxy)'
                                                                '\n FOR DYNAMIC EQUATION THE FOLLOWING APPLIES'
                                                                '\n    X (horizontal) used for BOTTOM, BBT, HOPPER, MD'
                                                                '\n    Y (vertical) used for BBS, SIDE_SHELL, SSS'
                                                                '\n'
                                                                '\n Bottom (100/100/50/5) :              BOTTOM '
                                                                '\n Bilge box side (70/70/30/3) :        BBS '
                                                                '\n Bilge box top (80/80/30/3) :         BBT '
                                                                '\n Hopper plate(70/70/50/3) :           HOPPER'
                                                                '\n Side shell (100/100/40/3):           SIDE_SHELL'
                                                                '\n Inner side (80/80/40/5):             INNER_SIDE '
                                                                '\n Non WT self._main_fr (70/70/60/10):  FRAME '
                                                                '\n WT self._main_fr (70/70/60/10):      FRAME_WT '
                                                                '\n Internal BHD WT (70/70/50/10):       INT_BHD'
                                                                '\n Main deck (70/70/40/3) :             MD '
                                                                '\n General (WT) (90/90/40/5):           '
                                                                'GENERAL_INTERNAL_WT'
                                                                '\n General (NONWT) (70/70/30/3):        '
                                                                'GENERAL_INTERNAL_NONWT'
                                                                '\n Side shell slamming (100/100/50/20): SSS '
                                                                '\n Internal 1 MPa wt (1/1/1/1):         INTERNAL_1_MPA '
                                                                '\n Internal low stress wt (40/40/20/5): '
                                                                'INTERNAL_LOW_STRESS_WT ')

        vert_start = 0.1
        hor_start = 0.02

        # Toggle buttons
        ttk.Label(self._tab_prop_tools, text='Change one property for multiple lines here. \n'
                                             '1. Press mulitple select button\n'
                                             '2. Select parameter in option menu\n'
                                             '3. Press Change parameters button', font=self._text_size['Text 9']) \
            .place(relx=hor_start, rely=vert_start - 1 * delta_y)
        self._toggle_btn = tk.Button(self._tab_prop_tools, text="Toggle select\nmultiple", relief="raised",
                                     command=self.toggle_select_multiple, bg='#E1E1E1', activebackground='#E5F1FB')
        self._toggle_change_param = ttk.Button(self._tab_prop_tools, text="Change parameters",
                                               command=self.toggle_set_variable)
        self._toggle_param_to_change = None
        self._toggle_btn.place(relx=hor_start, rely=vert_start + 2 * delta_y, relwidth=0.2, relheight=0.06)

        self._toggle_change_param.place(relx=hor_start + delta_x * 6, rely=vert_start + 2 * delta_y, relwidth=0.25)

        self._toggle_choose = ttk.OptionMenu(self._tab_prop_tools, self._new_toggle_var, self._stuctural_definition[0],
                                             *self._stuctural_definition,
                                             command=self.update_frame)
        self._toggle_choose.place(relx=hor_start + delta_x * 3, rely=vert_start + 2 * delta_y, relwidth=0.25)

        ttk.Label(self._tab_prop_tools, text='Scale stresses when changing properties', font=self._text_size['Text 9']) \
            .place(relx=hor_start + delta_x * 1, rely=vert_start + 6 * delta_y)

        ttk.Checkbutton(self._tab_prop_tools, variable=self._new_scale_stresses, command=self.on_color_code_check) \
            .place(relx=hor_start + delta_x * 0, rely=vert_start + 6 * delta_y)

        ttk.Label(self._tab_prop_tools, text='Factor when scaling stresses up, fup',
                  font=self._text_size['Text 8']).place(relx=hor_start + delta_x,
                                                        rely=vert_start + 7 * delta_y)
        ttk.Label(self._tab_prop_tools, text='Factor when scaling stresses down, fdown',
                  font=self._text_size['Text 8']).place(relx=hor_start + delta_x,
                                                        rely=vert_start + 8 * delta_y)

        ent_fup = ttk.Entry(self._tab_prop_tools, textvariable=self._new_fup)
        ent_fup.place(relx=hor_start, rely=vert_start + 7 * delta_y, relwidth=0.1)

        ent_fdwn = ttk.Entry(self._tab_prop_tools, textvariable=self._new_fdwn)
        ent_fdwn.place(relx=hor_start, rely=vert_start + 8 * delta_y, relwidth=0.1)

        # --- main variable to define the structural properties ---
        self._material_library_names = ecosystem_gui.material_library_names()
        self._new_material_name = tk.StringVar()
        self._new_material_name.set(ecosystem_gui.default_material_name(self._material_library_names))
        self._last_isotropic_material_name = self._new_material_name.get()
        self._new_material = tk.DoubleVar()
        self._new_material_factor = tk.DoubleVar()
        self._new_field_len = tk.DoubleVar()
        self._new_stf_spacing = tk.DoubleVar()
        self._new_plate_thk = tk.DoubleVar()
        self._new_stf_web_h = tk.DoubleVar()
        self._new_stf_web_t = tk.DoubleVar()
        self._new_stf_fl_w = tk.DoubleVar()
        self._new_stf_fl_t = tk.DoubleVar()
        self._new_stucture_type = tk.StringVar()
        self._new_stucture_type_label = tk.StringVar()
        self._new_sigma_y1 = tk.DoubleVar()
        self._new_sigma_y2 = tk.DoubleVar()
        self._new_sigma_x1 = tk.DoubleVar()
        self._new_sigma_x2 = tk.DoubleVar()
        self._new_tauxy = tk.DoubleVar()
        self._new_stf_km1 = tk.DoubleVar()
        self._new_stf_km2 = tk.DoubleVar()
        self._new_stf_km3 = tk.DoubleVar()
        self._new_stf_kps = tk.DoubleVar()
        self._new_plate_kpp = tk.DoubleVar()
        self._new_stf_type = tk.StringVar()

        self._new_girder_web_h = tk.DoubleVar()
        self._new_girder_web_t = tk.DoubleVar()
        self._new_girder_fl_w = tk.DoubleVar()
        self._new_girder_fl_t = tk.DoubleVar()
        self._new_girder_type = tk.StringVar()
        self._new_girder_length_LG = tk.DoubleVar()
        self._new_panel_length_Lp = tk.DoubleVar()

        self._new_pressure_side = tk.StringVar()
        self._new_puls_method = tk.StringVar()
        self._new_puls_panel_boundary = tk.StringVar()
        self._new_puls_sp_or_up = tk.StringVar()
        self._new_puls_up_boundary = tk.StringVar()

        self._new_buckling_min_press_adj_spans = tk.DoubleVar()
        self._new_buckling_lf_stresses = tk.DoubleVar()
        self._new_buckling_stf_end_support = tk.StringVar()
        self._new_buckling_girder_end_support = tk.StringVar()
        self._new_buckling_tension_field = tk.StringVar()
        self._new_buckling_effective_against_sigy = tk.StringVar()
        self._new_buckling_length_factor_stf = tk.DoubleVar()
        self._new_buckling_length_factor_girder = tk.DoubleVar()
        self._new_buckling_km3 = tk.DoubleVar()
        self._new_buckling_km2 = tk.DoubleVar()
        self._new_buckling_stf_dist_bet_lat_supp = tk.DoubleVar()
        self._new_buckling_girder_dist_bet_lat_supp = tk.DoubleVar()
        self._new_buckling_fab_method_stf = tk.StringVar()
        self._new_buckling_fab_method_girder = tk.StringVar()

        self._new_buckling_lf_stresses.set(1)
        self._new_buckling_stf_end_support.set('Continuous')
        self._new_buckling_girder_end_support.set('Continuous')
        self._new_buckling_tension_field.set('not allowed')
        self._new_buckling_effective_against_sigy.set("Stf. pl. effective against sigma y")
        self._new_buckling_km3.set(12)
        self._new_buckling_km2.set(24)
        self._new_buckling_fab_method_stf.set('welded')
        self._new_buckling_fab_method_girder.set('welded')

        # Setting default values to tkinter variables
        self._new_material.set(355)
        self._new_field_len.set(4000)
        self._new_stf_spacing.set(750)
        self._new_plate_thk.set(18)
        self._new_stf_web_h.set(400)
        self._new_stf_web_t.set(12)
        self._new_stf_fl_w.set(150)
        self._new_stf_fl_t.set(20)

        self._new_girder_web_h.set(800)
        self._new_girder_web_t.set(20)
        self._new_girder_fl_w.set(200)
        self._new_girder_fl_t.set(30)
        self._new_girder_length_LG.set(10000)
        self._new_panel_length_Lp.set(0)

        self._new_sigma_y1.set(80)
        self._new_sigma_y2.set(80)
        self._new_sigma_x1.set(50)
        self._new_sigma_x2.set(50)
        self._new_stf_km1.set(12)
        self._new_stf_km2.set(24)
        self._new_stf_km3.set(12)
        self._new_stf_kps.set(1)
        self._new_plate_kpp.set(1)
        self._new_material_factor.set(1.15)

        self._new_overpresure = tk.DoubleVar()
        self._new_overpresure.set(25000)
        self._new_density = tk.DoubleVar()
        self._new_density.set(1025)
        self._new_max_el = tk.DoubleVar()
        self._new_min_el = tk.DoubleVar()
        self._new_calculation_domain = tk.StringVar()

        self._new_stucture_type.set('GENERAL_INTERNAL_WT')
        self.option_meny_structure_type_trace(event='GENERAL_INTERNAL_WT')
        self._new_stf_type.set('T')
        self._new_pressure_side.set('both sides')
        self._new_puls_method.set('ultimate')
        self._new_puls_panel_boundary.set('Int')
        self._new_puls_sp_or_up.set('SP')
        self._new_puls_up_boundary.set('SSSS')
        # self._new_calculation_domain.set('Stiffened panel, flat')
        self._new_calculation_domain.set('Flat plate, stiffened')

        # --- main entries and labels to define the structural properties ---
        ent_width = 12  # width of entries

        '''
        Flat plate input
        '''

        self._flat_gui_headlines = [ttk.Label(self._tab_prop, text='Plate input',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Stiffener',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Girder',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Load/stresses input',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Special provisions input',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Buckling input',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Stiffener',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Girder',
                                              font=self._text_size['Text 8 bold']),
                                    ]

        self._ent_field_len = ttk.Entry(self._tab_prop, textvariable=self._new_field_len, width=int(10))
        self._ent_stf_spacing = ttk.Entry(self._tab_prop, textvariable=self._new_stf_spacing, width=int(10))
        self._ent_plate_thk = ttk.Entry(self._tab_prop, textvariable=self._new_plate_thk, width=int(10))
        self._ent_girder_length = ttk.Entry(self._tab_prop, textvariable=self._new_girder_length_LG, width=int(10))
        self._ent_panel_length = ttk.Entry(self._tab_prop, textvariable=self._new_panel_length_Lp, width=int(10))

        self._lab_span = ttk.Label(self._tab_prop, text='Stiffener/plate length', )
        self._lab_s = ttk.Label(self._tab_prop, text='Stiffener spacing/plate width', )
        self._lab_pl_thk = ttk.Label(self._tab_prop, text='Plate thickness', )
        self._lab_girder_length_LG = ttk.Label(self._tab_prop, text='Girder length, LG')
        self._lab_gpanel_length_Lp = ttk.Label(self._tab_prop, text='Panel length, Lp')

        self._flat_gui_plate = [self._ent_field_len, self._ent_stf_spacing, self._ent_plate_thk,
                                self._ent_girder_length, self._ent_panel_length]
        self._flat_gui_lab_plate = [self._lab_span, self._lab_s, self._lab_pl_thk, self._lab_girder_length_LG,
                                    self._lab_gpanel_length_Lp]

        self._btn_flat_stf_section = ttk.Button(self._tab_prop, text='Stiffener',
                                                command=lambda id="flat stf": self.on_open_structure_window(id))
        self._ent_stf_type = ttk.OptionMenu(self._tab_prop, self._new_stf_type, 'T', *['T', 'FB', 'L', 'L-bulb'])
        self._ent_stf_web_h = ttk.Entry(self._tab_prop, textvariable=self._new_stf_web_h, width=int(10))
        self._ent_stf_web_t = ttk.Entry(self._tab_prop, textvariable=self._new_stf_web_t, width=int(10))
        self._ent_stf_fl_w = ttk.Entry(self._tab_prop, textvariable=self._new_stf_fl_w, width=int(10))
        self._ent_str_fl_t = ttk.Entry(self._tab_prop, textvariable=self._new_stf_fl_t, width=int(10))

        self._lab_stf_section = ttk.Label(self._tab_prop, text='')
        self._lab_stf_type = ttk.Label(self._tab_prop, text='Stiffener/girder type')
        self._lab_web_h = ttk.Label(self._tab_prop, text='Web height, hw', )
        self._lab_web_thk = ttk.Label(self._tab_prop, text='Web thickness, tw', )
        self._lab_fl_w = ttk.Label(self._tab_prop, text='Flange width, b', )
        self._lab_fl_thk = ttk.Label(self._tab_prop, text='Flange thickeness, tf', )

        self._flat_gui_stf = [self._btn_flat_stf_section, self._ent_stf_type, self._ent_stf_web_h, self._ent_stf_web_t,
                              self._ent_stf_fl_w, self._ent_str_fl_t]
        self._flat_gui_lab_stf = [self._lab_stf_section, self._lab_stf_type, self._lab_web_h, self._lab_web_thk,
                                  self._lab_fl_w, self._lab_fl_thk]

        self._btn_flat_girder_section = ttk.Button(self._tab_prop, text='Girder',
                                                   command=lambda id="flat girder": self.on_open_structure_window(id))
        self._ent_girder_type = ttk.OptionMenu(self._tab_prop, self._new_girder_type, 'T', *['T', 'FB', 'L', 'L-bulb'])
        self._ent_girder_web_h = ttk.Entry(self._tab_prop, textvariable=self._new_girder_web_h, width=int(10))
        self._ent_girder_web_t = ttk.Entry(self._tab_prop, textvariable=self._new_girder_web_t, width=int(10))
        self._ent_girder_fl_w = ttk.Entry(self._tab_prop, textvariable=self._new_girder_fl_w, width=int(10))
        self._ent_girder_fl_t = ttk.Entry(self._tab_prop, textvariable=self._new_girder_fl_t, width=int(10))
        self._flat_gui_girder = [self._btn_flat_girder_section, self._ent_girder_type, self._ent_girder_web_h,
                                 self._ent_girder_web_t,
                                 self._ent_girder_fl_w, self._ent_girder_fl_t]

        self._ent_plate_kpp = ttk.Entry(self._tab_prop, textvariable=self._new_plate_kpp, width=int(5 * 1))
        self._ent_plate_kps = ttk.Entry(self._tab_prop, textvariable=self._new_stf_kps, width=int(5 * 1))
        self._ent_stf_km1 = ttk.Entry(self._tab_prop, textvariable=self._new_stf_km1, width=int(5 * 1))
        self._ent_stf_km2 = ttk.Entry(self._tab_prop, textvariable=self._new_stf_km2, width=int(5 * 1))
        self._ent_stf_km3 = ttk.Entry(self._tab_prop, textvariable=self._new_stf_km3, width=int(5 * 1))
        self._lab_kpp = ttk.Label(self._tab_prop, text='kpp', )
        self._lab_kps = ttk.Label(self._tab_prop, text='kps', )
        self._lab_km1 = ttk.Label(self._tab_prop, text='km1', )
        self._lab_km2 = ttk.Label(self._tab_prop, text='km2', )
        self._lab_km3 = ttk.Label(self._tab_prop, text='km3', )
        self._flat_gui_os_c101_provisions = [self._ent_plate_kpp, self._ent_plate_kps, self._ent_stf_km1,
                                             self._ent_stf_km2, self._ent_stf_km3]
        self._flat_gui_lab_os_c101_provisions = [self._lab_kpp, self._lab_kps, self._lab_km1, self._lab_km2,
                                                 self._lab_km3]

        self._ent_pressure_side = ttk.OptionMenu(self._tab_prop, self._new_pressure_side, ('both sides', 'plate side',
                                                                                           'stiffener side')[0],
                                                 *('both sides', 'plate side', 'stiffener side'))
        self._ent_sigma_y1 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_y1, width=int(10))
        self._ent_sigma_y2 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_y2, width=int(10))
        self._ent_sigma_x1 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_x1, width=int(10))
        self._ent_sigma_x2 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_x2, width=int(10))
        self._ent_tauxy = ttk.Entry(self._tab_prop, textvariable=self._new_tauxy, width=int(10))
        self._material_picker = ttk.Frame(self._tab_prop)
        self._ent_material_name = ttk.Combobox(
            self._material_picker,
            textvariable=self._new_material_name,
            values=self._material_library_names,
            state='readonly',
            width=20,
        )
        self._ent_material_name.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._ent_material_name.bind('<<ComboboxSelected>>', self._on_material_library_selected)
        ttk.Button(
            self._material_picker,
            text='Edit...',
            command=self.on_open_material_editor,
        ).pack(side=tk.LEFT, padx=(4, 0))
        self._ent_mat = ttk.Entry(self._tab_prop, textvariable=self._new_material, width=int(10))
        self._ent_mat_factor = ttk.Entry(self._tab_prop, textvariable=self._new_material_factor, width=int(10))
        self._ent_structure_type = ttk.OptionMenu(self._tab_prop, self._new_stucture_type, self._options_type[0],
                                                  *self._options_type, command=self.option_meny_structure_type_trace)

        self._lab_press_side = ttk.Label(self._tab_prop, text='Overpressure side')
        self._lab_sig_x1 = ttk.Label(self._tab_prop, text='Axial stress 1,sig_x1')
        self._lab_sig_x2 = ttk.Label(self._tab_prop, text='Axial stress 2,sig_x2')
        self._lab_sig_y1 = ttk.Label(self._tab_prop, text='Trans. stress 1,sig_y1')
        self._lab_sig_y2 = ttk.Label(self._tab_prop, text='Trans. stress 2,sig_y2')
        self._lab_tau_y1 = ttk.Label(self._tab_prop, text='Shear Stres,tau_y1')
        self._lab_material_library = ttk.Label(self._tab_prop, text='Material library')
        self._lab_yield = ttk.Label(self._tab_prop, text='Material yield stress [MPa]:', font=self._text_size['Text 9'])
        self._lab_mat_fac = ttk.Label(self._tab_prop, text='Mat. factor', font=self._text_size['Text 9'])
        self._lab_structure_type = ttk.Label(self._tab_prop, text='Select structure type:',
                                             font=self._text_size['Text 9'])

        self._flat_gui_lab_loads = [self._lab_press_side, self._lab_sig_x1,
                                    self._lab_sig_x2, self._lab_sig_y1, self._lab_sig_y2,
                                    self._lab_tau_y1, self._lab_material_library, self._lab_yield, self._lab_mat_fac,
                                    self._lab_structure_type]
        self._flat_gui_loads = [self._ent_pressure_side, self._ent_sigma_x1,
                                self._ent_sigma_x2, self._ent_sigma_y1, self._ent_sigma_y2, self._ent_tauxy,
                                self._material_picker, self._ent_mat, self._ent_mat_factor,
                                self._ent_structure_type]

        self._new_buckling_method = tk.StringVar()
        options = [
            'DNV-RP-C201 - prescriptive',
            'ML-Numeric (PULS based)',
            'SemiAnalytical S3/U3',
        ]
        self._lab_buckling_method = ttk.Label(self._tab_prop, text='Set buckling method')
        self._buckling_method = ttk.OptionMenu(self._tab_prop, self._new_buckling_method, options[0], *options,
                                               command=self.trace_buckling_method)

        # SemiAnalytical and ML-Numeric share the historic buckling panel input parameters below.

        self._ent_puls_sp_or_up = ttk.OptionMenu(self._tab_prop, self._new_puls_sp_or_up, 'SP', *['SP', 'UP'],
                                                 command=self.trace_puls_up_or_sp, )
        self._ent_puls_method = ttk.OptionMenu(self._tab_prop, self._new_puls_method, 'buckling',
                                               *['buckling', 'ultimate'])
        self._ent_puls_panel_boundary = ttk.OptionMenu(self._tab_prop, self._new_puls_panel_boundary, 'Int',
                                                       *['Int', 'GL', 'GT'])
        # self._ent_puls_stf_end_type = ttk.OptionMenu(self._tab_prop, self._new_buckling_stf_end_support,'C',*['C', 'S'])
        self._ent_puls_stf_end_type = ttk.OptionMenu(self._tab_prop, self._new_buckling_stf_end_support, 'Continuous',
                                                     *['Continuous', 'Sniped'])
        self._ent_puls_up_boundary = ttk.Entry(self._tab_prop, textvariable=self._new_puls_up_boundary,
                                               width=int(7 * 1))
        self._zstar_chk = ttk.Checkbutton(self._tab_prop, variable=self._new_zstar_optimization)

        self._lab_puls_input = ttk.Label(self._tab_prop, text='Buckling paramenters input',
                                         font=self._text_size['Text 8 bold'])

        self._flat_gui_buc_lab_stf_girder = [ttk.Label(self._tab_prop, text='End support'),
                                             ttk.Label(self._tab_prop, text='Fabrication method'),
                                             ttk.Label(self._tab_prop, text='Buckling length factor'),
                                             ttk.Label(self._tab_prop, text='Distance between lateral support'),
                                             ttk.Label(self._tab_prop, text='Tension field action:')]

        self._flat_gui_buc_stf_opt = [ttk.OptionMenu(self._tab_prop, self._new_buckling_stf_end_support,
                                                     'Continuous', *['Continuous', 'Sniped']),
                                      ttk.OptionMenu(self._tab_prop, self._new_buckling_fab_method_stf,
                                                     'welded', *['welded', 'rolled']),
                                      ttk.Entry(self._tab_prop, textvariable=self._new_buckling_length_factor_stf,
                                                width=int(ent_width * 1)),
                                      ttk.Entry(self._tab_prop, textvariable=self._new_buckling_stf_dist_bet_lat_supp
                                                , width=int(ent_width * 1)),
                                      ttk.OptionMenu(self._tab_prop, self._new_buckling_tension_field,
                                                     'not allowed', *['allowed', 'not allowed'])]
        self._flat_gui_buc_girder_opt = [ttk.OptionMenu(self._tab_prop, self._new_buckling_girder_end_support,
                                                        'Continuous', *['Continuous', 'Sniped']),
                                         ttk.OptionMenu(self._tab_prop, self._new_buckling_fab_method_girder,
                                                        'welded', *['welded', 'rolled']),
                                         ttk.Entry(self._tab_prop, textvariable=self._new_buckling_length_factor_girder
                                                   , width=int(ent_width * 1)),
                                         ttk.Entry(self._tab_prop,
                                                   textvariable=self._new_buckling_girder_dist_bet_lat_supp,
                                                   width=int(ent_width * 1)),
                                         ttk.OptionMenu(self._tab_prop, self._new_buckling_effective_against_sigy,
                                                        'Stf. pl. effective against sigma y',
                                                        *['Stf. pl. effective against sigma y',
                                                          'All sigma y to girder'])]
        self._flat_gui_girder_moment_factor = [
            ttk.Label(self._tab_prop, text='Girder moment factor at support/midspan'),
            ttk.Entry(self._tab_prop, textvariable=self._new_buckling_km3,
                      width=int(ent_width * 1)),
            ttk.Entry(self._tab_prop, textvariable=self._new_buckling_km2,
                      width=int(ent_width * 1))]
        self._flat_gui_buc_lab_common = [ttk.Label(self._tab_prop, text='Minimum pressure in adjacent spans'),
                                         ttk.Label(self._tab_prop, text='Load factor on stresses')]
        self._flat_gui_buc_common_opt = [ttk.Entry(self._tab_prop, textvariable=self._new_buckling_min_press_adj_spans,
                                                   width=int(ent_width * 1)),
                                         ttk.Entry(self._tab_prop, textvariable=self._new_buckling_lf_stresses,
                                                   width=int(ent_width * 1))]

        self._lab_puls_acceptance = ttk.Label(self._tab_prop, text='Buckling acceptance')
        self._lab_puls_int_gt = ttk.Label(self._tab_prop, text='Int-integrated GL-free left/right GT-free top/bottom')
        self._lab_puls_cont_sniped = ttk.Label(self._tab_prop, text='Continous or Sniped',
                                               font=self._text_size['Text 8'])
        self._lab_puls_up_supp = ttk.Label(self._tab_prop, text='UP support - left,right,upper,lower\n'
                                                                'S: simply supported C: Continuous',
                                           font=self._text_size['Text 8'])
        # self._zstar_label = ttk.Label(self._tab_prop, text='z* optimization (buckling RP-C201)',
        #                               font=self._text_size['Text 8'])

        self._flat_gui_buckling = [self._ent_puls_method,
                                   self._ent_puls_panel_boundary,
                                   self._ent_puls_up_boundary]  # , self._zstar_chk]

        self._flat_gui_lab_buckling = [self._lab_puls_acceptance,
                                       self._lab_puls_int_gt,
                                       self._lab_puls_up_supp]  # , self._zstar_label]

        self._button_str_type = ttk.Button(self._tab_prop, text='Show structure types', command=show_message)
        self._structure_types_label = ttk.Label(textvariable=self._new_stucture_type_label,
                                                font=self._text_size['Text 8'], )

        # -------------Color coding-------------------
        self._chk_cc_spacing = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_spacing,
                                               command=self.on_color_code_check)
        self._chk_button_sigmax1 = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_sigmax,
                                                   command=self.on_color_code_check)
        self._chk_button_sigmax2 = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_sigmax,
                                                   command=self.on_color_code_check)
        self._chk_button_sigmay1 = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_sigmay1,
                                                   command=self.on_color_code_check)
        self._chk_button_sigmay2 = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_sigmay2,
                                                   command=self.on_color_code_check)
        self._chk_button_tauxy = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_tauxy,
                                                 command=self.on_color_code_check)
        self._chk_button_structure_type = ttk.Checkbutton(self._tab_information,
                                                          variable=self._new_colorcode_structure_type,
                                                          command=self.on_color_code_check)

        self._chk_button_puls_spup = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_puls_sp_or_up,
                                                     command=self.on_color_code_check)
        self._chk_button_puls_acceptance = ttk.Checkbutton(self._tab_information,
                                                           variable=self._new_colorcode_puls_acceptance,
                                                           command=self.on_color_code_check)

        chk_deltax = 0.1
        chk_deltay = 0.025
        (ttk.Label(self._tab_information, text='Labelling and color code options ', font=self._text_size["Text 9"])
         .place(relx=0.02, rely=2 * chk_deltay))
        self._information_gui_chk_structure = [
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_label_color_coding,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_show_cog,
                            command=self.update_frame),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_shortcut_backdrop,
                            command=self.update_frame),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_beams,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_plates,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_pressure,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_utilization,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_section_modulus,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_fatigue,
                            command=self.on_color_code_check),
            ttk.Checkbutton(self._tab_information,
                            variable=self._new_colorcode_total,
                            command=self.on_color_code_check),
            self._chk_cc_spacing, self._chk_button_sigmax1,
            self._chk_button_sigmax2,
            self._chk_button_sigmay1, self._chk_button_sigmay2,
            self._chk_button_tauxy, self._chk_button_structure_type,
            self._chk_button_puls_spup,
            self._chk_button_puls_acceptance]

        self._information_gui_lab_chk_structure = [
            ttk.Label(self._tab_information, text='Label color code', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Show COG/COB', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Check to see available shortcuts', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Beam prop.', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Plate thk.', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Pressure', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Buckling UF', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Sec. mod. UF', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Fatigue UF', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Total UF', font=self._text_size["Text 9"]),
            ttk.Label(self._tab_information, text='Stiffener spacing'),
            ttk.Label(self._tab_information, text='Stresses, sigma x1'),
            ttk.Label(self._tab_information, text='Stresses, sigma x2'),
            ttk.Label(self._tab_information, text='Stresses, sigma y1'),
            ttk.Label(self._tab_information, text='Stresses, sigma y2'),
            ttk.Label(self._tab_information, text='Stresses, sigma tauxy'),
            ttk.Label(self._tab_information, text='Structure type'),
            ttk.Label(self._tab_information, text='Buckling - SP or UP'),
            ttk.Label(self._tab_information, text='Buckling acceptance criteria')]
        idx = 3
        for lab, ent in zip(self._information_gui_chk_structure, self._information_gui_lab_chk_structure):
            lab.place(relx=0.02, rely=idx * chk_deltay)
            ent.place(relx=0.02 + chk_deltax, rely=idx * chk_deltay)
            idx += 1

        try:
            img_file_name = 'img_stf_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._stf_button = tk.Button(self._tab_prop, image=photo,
                                         command=self.on_open_structure_window)
            self._stf_button.image = photo

        except TclError:
            self._stf_button = tk.Button(self._tab_prop, text='STF.',
                                         command=self.on_open_structure_window,
                                         bg=self._button_bg_color, fg=self._button_fg_color)

        try:
            img_file_name = 'img_stress_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._stress_button = tk.Button(self._tab_prop, image=photo, command=self.on_open_stresses_window,
                                            fg=self._button_fg_color, bg='white')
            self._stress_button.image = photo

        except TclError:
            self._stress_button = tk.Button(self._tab_prop, text='STRESS', command=self.on_open_stresses_window,
                                            bg=self._button_bg_color, fg=self._button_fg_color)

        try:
            img_file_name = 'fls_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._fls_button = tk.Button(self._tab_prop, image=photo, command=self.on_open_fatigue_window,
                                         bg=self._button_bg_color)
            self._fls_button.image = photo

        except TclError:
            self._fls_button = tk.Button(self._tab_prop, text='FLS', command=self.on_open_fatigue_window,
                                         bg=self._button_bg_color, fg=self._button_fg_color, )

        self.add_stucture = ttk.Button(self._tab_prop, text='Press to add input properties\n'
                                                            'to the selected line. Sets all\n'
                                                            'basic structural information.', command=self.new_structure,
                                       style="Bold.TButton")

        ''' Start shell input '''

        '''
        Shell input
        '''
        self._new_shell_thk = tk.DoubleVar()
        self._new_shell_radius = tk.DoubleVar()
        self._new_shell_dist_rings = tk.DoubleVar()
        self._new_shell_cone_r1 = tk.DoubleVar()
        self._new_shell_cone_r2 = tk.DoubleVar()
        self._new_shell_cone_length = tk.DoubleVar()
        self._new_shell_length = tk.DoubleVar()
        self._new_shell_tot_length = tk.DoubleVar()
        self._new_shell_k_factor = tk.DoubleVar()
        self._new_shell_yield = tk.DoubleVar()
        self._new_shell_mat_factor = tk.DoubleVar()
        self._new_shell_poisson = tk.DoubleVar()
        self._new_shell_e_module = tk.DoubleVar()
        self._new_shell_ring_stf_fab_method = tk.IntVar()
        self._new_shell_ring_frame_fab_method = tk.IntVar()
        self._new_shell_exclude_ring_stf = tk.BooleanVar()
        self._new_shell_exclude_ring_frame = tk.BooleanVar()

        self._new_shell_panel_spacing = tk.DoubleVar()
        self._new_shell_thk.set(20)
        self._new_shell_radius.set(5000)
        self._new_shell_dist_rings.set(5000)
        self._new_shell_cone_r1.set(4000)
        self._new_shell_cone_r2.set(6000)
        self._new_shell_cone_length.set(5000)
        self._new_shell_length.set(5000)
        self._new_shell_tot_length.set(5000)
        self._new_shell_k_factor.set(1)
        self._new_shell_yield.set(355)
        self._new_shell_mat_factor.set(1.15)
        self._new_shell_poisson.set(0.3)
        self._new_shell_e_module.set(2.1e11)
        self._new_shell_ring_stf_fab_method.set(1)
        self._new_shell_ring_frame_fab_method.set(2)
        self._new_shell_panel_spacing.set(2000)
        self._new_shell_exclude_ring_stf.set(False)
        self._new_shell_exclude_ring_frame.set(False)

        self._shell_gui_items = list()
        self._lab_shell = ttk.Label(self._tab_prop, text='Shell and curved plate input [mm]')
        self._ent_shell_plate_thk = ttk.Entry(self._tab_prop, textvariable=self._new_shell_thk)

        self._ent_shell_radius = ttk.Entry(self._tab_prop, textvariable=self._new_shell_radius)
        self._ent_shell_dist_rings = ttk.Entry(self._tab_prop, textvariable=self._new_shell_dist_rings)
        self._ent_shell_cone_r1 = ttk.Entry(self._tab_prop, textvariable=self._new_shell_cone_r1)
        self._ent_shell_cone_r2 = ttk.Entry(self._tab_prop, textvariable=self._new_shell_cone_r2)
        self._ent_shell_cone_length = ttk.Entry(self._tab_prop, textvariable=self._new_shell_cone_length)
        self._ent_shell_length = ttk.Entry(self._tab_prop, textvariable=self._new_shell_length, width=int(5 * 1))
        self._ent_shell_tot_length = ttk.Entry(self._tab_prop, textvariable=self._new_shell_tot_length,

                                               )
        self._ent_shell_k_factor = ttk.Entry(self._tab_prop, textvariable=self._new_shell_k_factor,
                                             )
        self._ent_shell_material_factor = ttk.Entry(self._tab_prop, textvariable=self._new_shell_mat_factor)

        self._shell_gui_items = [self._lab_shell, self._ent_shell_plate_thk, self._ent_shell_radius,
                                 self._ent_shell_dist_rings,
                                 self._ent_shell_length, self._ent_shell_tot_length, self._ent_shell_k_factor,
                                 self._ent_shell_material_factor]
        self._shell_conical_gui_items = [self._lab_shell, self._ent_shell_plate_thk, self._ent_shell_cone_r1,
                                         self._ent_shell_cone_r2, self._ent_shell_cone_length,
                                         self._ent_shell_k_factor, self._ent_shell_material_factor]

        '''
        Shell, lognitudinal stiffeners
        '''
        # USING stiffeners for flat plates
        self._lab_shell_long_stiffener = ttk.Label(self._tab_prop, text='Longitudinal stiffener properties [mm]',

                                                   )
        self._btn_shell_stf_section_long_stf = ttk.Button(self._tab_prop, text='STF',
                                                          command=lambda id="long stf": self.on_open_structure_window(
                                                              id))

        self._shell_long_stf_gui_items = [self._lab_shell_long_stiffener, self._ent_stf_web_h, self._ent_stf_web_t,
                                          self._ent_stf_fl_w, self._ent_str_fl_t, self._ent_stf_spacing,
                                          self._ent_stf_type, self._btn_shell_stf_section_long_stf]

        '''
        Shell, ring stiffener
        '''
        self._lab_shell_ring_stiffener = ttk.Label(self._tab_prop, text='Ring stiffener properties [mm]')
        self._new_shell_ring_stf_hw = tk.DoubleVar()
        self._new_shell_ring_stf_tw = tk.DoubleVar()
        self._new_shell_ring_stf_b = tk.DoubleVar()
        self._new_shell_ring_stf_tf = tk.DoubleVar()
        self._new_shell_ring_stf_tripping_brackets = tk.DoubleVar()
        self._new_shell_ring_stf_type = tk.StringVar()
        self._new_shell_ring_stf_hw.set(300)
        self._new_shell_ring_stf_tw.set(12)
        self._new_shell_ring_stf_b.set(120)
        self._new_shell_ring_stf_tf.set(20)
        self._new_shell_ring_stf_tripping_brackets.set(0)
        self._new_shell_ring_stf_type.set('T')

        self._ent_shell_ring_stf_hw = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_hw,
                                                width=int(5 * 1), )
        self._ent_shell_ring_stf_tw = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_tw,
                                                )
        self._ent_shell_ring_stf_b = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_b,
                                               )
        self._ent_shell_ring_stf_tf = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_tf,
                                                )
        self._ent_shell_ring_stf_tripping_brackets = ttk.Entry(self._tab_prop,
                                                               textvariable=self._new_shell_ring_stf_tripping_brackets,
                                                               )

        self._ent_shell_ring_stf_type = ttk.OptionMenu(self._tab_prop, self._new_shell_ring_stf_type, 'T',
                                                       *['T', 'FB', 'L', 'L-bulb'])

        self._chk_shell_ring_frame_exclude = ttk.Checkbutton(self._tab_prop,
                                                             variable=self._new_shell_exclude_ring_stf,
                                                             command=self.calculation_domain_selected)
        self._btn_shell_stf_section_ring_stf = ttk.Button(self._tab_prop, text='STF',
                                                          command=lambda id="ring stf":
                                                          self.on_open_structure_window(id))
        self._shell_ring_stf_gui_items = [self._lab_shell_ring_stiffener, self._ent_shell_ring_stf_hw,
                                          self._ent_shell_ring_stf_tw, self._ent_shell_ring_stf_b,
                                          self._ent_shell_ring_stf_tf, self._ent_shell_ring_stf_tripping_brackets,
                                          self._ent_shell_ring_stf_type, self._chk_shell_ring_frame_exclude,
                                          self._btn_shell_stf_section_ring_stf]
        '''
        Shell ring girder/frame
        '''
        self._lab_shell_ring_frame = ttk.Label(self._tab_prop, text='Ring frame/girder properties [mm]',
                                               )
        self._new_shell_ring_frame_hw = tk.DoubleVar()
        self._new_shell_ring_frame_tw = tk.DoubleVar()
        self._new_shell_ring_frame_b = tk.DoubleVar()
        self._new_shell_ring_frame_tf = tk.DoubleVar()
        self._new_shell_ring_frame_tripping_brackets = tk.DoubleVar()
        self._new_shell_ring_frame_l_between_girders = tk.DoubleVar()
        self._new_shell_ring_frame_type = tk.StringVar()
        self._new_shell_ring_frame_hw.set(300)
        self._new_shell_ring_frame_tw.set(12)
        self._new_shell_ring_frame_b.set(120)
        self._new_shell_ring_frame_tf.set(20)
        self._new_shell_ring_frame_tripping_brackets.set(0)
        self._new_shell_ring_frame_type.set('T')
        self._new_shell_ring_frame_length_between_girders = tk.DoubleVar()
        self._new_shell_ring_frame_length_between_girders.set(2500)

        self._ent_shell_ring_frame_hw = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_frame_hw,
                                                  width=int(5 * 1), )
        self._ent_shell_ring_frame_tw = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_frame_tw,
                                                  )
        self._ent_shell_ring_frame_b = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_frame_b,
                                                 )
        self._ent_shell_ring_frame_tf = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_frame_tf,
                                                  )
        self._ent_shell_ring_frame_tripping_brackets = ttk.Entry(self._tab_prop,
                                                                 textvariable=self._new_shell_ring_frame_tripping_brackets,
                                                                 )
        self._ent_shell_ring_frame_l_between_girders = ttk.Entry(self._tab_prop,
                                                                 textvariable=self._new_shell_ring_frame_length_between_girders,
                                                                 )
        self._ent_shell_ring_stf_type = ttk.OptionMenu(self._tab_prop, self._new_shell_ring_frame_type, 'T',
                                                       *['T', 'FB', 'L', 'L-bulb'])
        self._chk_shell_ring_frame_exclude = ttk.Checkbutton(self._tab_prop,
                                                             variable=self._new_shell_exclude_ring_frame,
                                                             command=self.calculation_domain_selected)
        self._btn_shell_stf_section_ring_frame = ttk.Button(self._tab_prop, text='STF', command=lambda
            id="ring frame": self.on_open_structure_window(id))
        self._shell_ring_frame_gui_items = [self._lab_shell_ring_stiffener, self._ent_shell_ring_frame_hw,
                                            self._ent_shell_ring_frame_tw, self._ent_shell_ring_frame_b,
                                            self._ent_shell_ring_frame_tf, self._ent_shell_ring_frame_tripping_brackets,
                                            self._ent_shell_ring_frame_l_between_girders,
                                            self._ent_shell_ring_stf_type, self._chk_shell_ring_frame_exclude,
                                            self._btn_shell_stf_section_ring_frame]

        '''
        Shell/panel load data
        '''

        self._lab_shell_loads = ttk.Label(self._tab_prop, text='Load data, compression pressure,\n stresses and '
                                                               'forces negative.',
                                          )
        self._new_shell_stress_or_force = tk.IntVar()
        self._new_shell_stress_or_force.set(1)

        self._ent_shell_force_input = ttk.Radiobutton(self._tab_prop, text="Force input",
                                                      variable=self._new_shell_stress_or_force, value=1,
                                                      command=self.calculation_domain_selected)
        self._ent_shell_stress_input = ttk.Radiobutton(self._tab_prop, text="Stress input",
                                                       variable=self._new_shell_stress_or_force, value=2,
                                                       command=self.calculation_domain_selected)

        self._new_shell_Nsd = tk.DoubleVar()
        self._new_shell_Msd = tk.DoubleVar()
        self._new_shell_M2sd = tk.DoubleVar()
        self._new_shell_Tsd = tk.DoubleVar()
        self._new_shell_Qsd = tk.DoubleVar()
        self._new_shell_Q2sd = tk.DoubleVar()
        self._new_shell_psd = tk.DoubleVar()
        self._new_shell_Nsd.set(500000)
        self._new_shell_Msd.set(500000)
        self._new_shell_M2sd.set(0)
        self._new_shell_Tsd.set(40000)
        self._new_shell_Qsd.set(1500)
        self._new_shell_Q2sd.set(0)
        self._new_shell_psd.set(-0.2)

        self._new_shell_uls_or_als = tk.StringVar()
        self._new_shell_end_cap_pressure_included = tk.StringVar()
        self._new_shell_fab_ring_stf = tk.StringVar()
        self._new_shell_fab_ring_frame = tk.StringVar()
        self._new_shell_uls_or_als.set('ULS')
        self._new_shell_end_cap_pressure_included.set('not included in axial force')

        self._new_shell_fab_ring_stf.set('Fabricated')
        self._new_shell_fab_ring_frame.set('Cold formed')

        self._lab_shell_limit_state = ttk.Label(self._tab_prop, text='Limit state:',
                                                font=self._text_size['Text 9 bold'],
                                                )
        self._lab_shell_en_cap_pressure = ttk.Label(self._tab_prop, text='End cap pressure is',
                                                    font=self._text_size['Text 8'],
                                                    )
        self._lab_shell_fab_stf = ttk.Label(self._tab_prop, text='Fabrication method ring stiffener:',
                                            font=self._text_size['Text 8'],
                                            )
        self._lab_shell_fab_frame = ttk.Label(self._tab_prop, text='Fabrication method ring girder:',
                                              font=self._text_size['Text 8'],
                                              )

        self._new_shell_sasd = tk.DoubleVar()
        self._new_shell_smsd = tk.DoubleVar()
        self._new_shell_tTsd = tk.DoubleVar()
        self._new_shell_tQsd = tk.DoubleVar()
        self._new_shell_shsd = tk.DoubleVar()

        self._ent_shell_uls_or_als = ttk.OptionMenu(self._tab_prop, self._new_shell_uls_or_als, 'ULS', *['ULS', 'ALS'])
        self._ent_shell_end_cap_pressure_included = ttk.OptionMenu(self._tab_prop,
                                                                   self._new_shell_end_cap_pressure_included,
                                                                   'included in axial force',
                                                                   *['not included in axial force',
                                                                     'included in axial force'])
        self._ent_shell_fab_ring_stf = ttk.OptionMenu(self._tab_prop, self._new_shell_fab_ring_stf, 'Fabricated',
                                                      *['Fabricated', 'Cold formed'])
        self._ent_shell_fab_ring_frame = ttk.OptionMenu(self._tab_prop, self._new_shell_fab_ring_frame, 'Fabricated',
                                                        *['Fabricated', 'Cold formed'])
        self._ent_shell_yield = ttk.Entry(self._tab_prop, textvariable=self._new_shell_yield,
                                          )

        self._ent_shell_Nsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Nsd,
                                        width=int(5 * 1), )
        self._ent_shell_Msd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Msd,
                                        width=int(5 * 1), )
        self._ent_shell_M2sd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_M2sd,
                                         width=int(5 * 1), )
        self._ent_shell_Tsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Tsd,
                                        width=int(5 * 1), )
        self._ent_shell_Qsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Qsd,
                                        width=int(5 * 1), )
        self._ent_shell_Q2sd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Q2sd,
                                         width=int(5 * 1), )
        self._ent_shell_psd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_psd,
                                        width=int(5 * 1), )

        self._ent_shell_sasd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_sasd,
                                         width=int(5 * 1), )
        self._ent_shell_smsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_smsd,
                                         width=int(5 * 1), )
        self._ent_shell_tTsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_tTsd,
                                         width=int(5 * 1), )
        self._ent_shell_tQsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_tQsd,
                                         width=int(5 * 1), )
        self._new_shell_psd = self._new_shell_psd
        self._ent_shell_shsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_shsd,
                                         width=int(5 * 1), )

        # Load information button

        self._shell_btn_load_info = ttk.Button(self._tab_prop, text='Load info',
                                               command=lambda id="shell": self.stress_information_notebooks(id),
                                               style="Bold.TButton")
        self._flat_btn_load_info = ttk.Button(self._tab_prop, text='Load info',
                                              command=lambda id="flat": self.stress_information_notebooks(id),
                                              style="Bold.TButton")
        self._flat_btn_fixation_info = ttk.Button(self._tab_prop, text='Param. info',
                                                  command=lambda id="fixation": self.stress_information_notebooks(id),
                                                  style="Bold.TButton")
        self._shell_btn_length_info = ttk.Button(self._tab_prop, text='Length info',
                                                 command=lambda id="length": self.stress_information_notebooks(id),
                                                 style="Bold.TButton")

        self._shell_loads_other_gui_items = [self._lab_shell_loads, self._ent_shell_force_input,
                                             self._ent_shell_stress_input]
        self._shell_loads_forces_gui_items = [self._ent_shell_Nsd, self._ent_shell_Msd,
                                              self._ent_shell_Tsd, self._ent_shell_Qsd, self._ent_shell_psd]
        self._shell_loads_conical_forces_gui_items = [self._ent_shell_Nsd, self._ent_shell_Msd,
                                                      self._ent_shell_M2sd, self._ent_shell_Tsd,
                                                      self._ent_shell_Qsd, self._ent_shell_Q2sd,
                                                      self._ent_shell_psd]
        self._shell_loads_stress_gui_items = [self._ent_shell_sasd, self._ent_shell_smsd, self._ent_shell_tTsd,
                                              self._ent_shell_tQsd, self._ent_shell_psd, self._ent_shell_shsd]
        self._shell_other_gui_items = [self._ent_shell_end_cap_pressure_included, self._ent_shell_uls_or_als,
                                       self._ent_shell_fab_ring_stf, self._ent_shell_fab_ring_frame,
                                       self._lab_shell_limit_state,
                                       self._lab_shell_en_cap_pressure, self._lab_shell_fab_stf,
                                       self._lab_shell_fab_frame, self._ent_shell_yield, self._lab_yield]

        self._shell_exclude_ring_stf = tk.Frame(self._tab_prop, height=10, bg="black", colormap="new", )
        self._shell_exclude_ring_frame = tk.Frame(self._tab_prop, height=10, bg="black", colormap="new")

        ''' END shell input '''

        prop_vert_start = 0.01
        types_start = 0.005208333

        options = ['Flat plate, stiffened', 'Flat plate, unstiffened', 'Flat plate, stiffened with girder'] + \
                  list(api_helpers.CYLINDER_STRUCTURE_DOMAINS_WITH_INPUT)
        self._shell_geometries_map = {
            **api_helpers.FLAT_GEOMETRY_IDS,
            **api_helpers.CYLINDER_GEOMETRY_IDS,
        }
        self._current_calculation_domain = 'Flat plate, stiffened'
        self._unit_informations_dimensions = list()

        self._ent_calculation_domain = ttk.OptionMenu(self._tab_prop, self._new_calculation_domain, options[0],
                                                      *options,
                                                      command=self.calculation_domain_selected)

        ttk.Label(self._tab_prop, text='Structural and calculation properties input below:',
                  font=self._text_size['Text 9 bold'],
                  ).place(rely=prop_vert_start - delta_y * 2.1, relx=types_start,
                          anchor=tk.NW)
        ttk.Label(self._tab_prop, text='Select calculation domain ->',
                  font=self._text_size['Text 10 bold'],
                  ).place(rely=prop_vert_start, relx=types_start,
                          anchor=tk.NW)
        self._ent_calculation_domain.place(rely=prop_vert_start, relx=types_start + delta_x * 5)

        # --- Compartment/tank load input and information ---
        load_vert_start = 0.05  # frame_horizontal -0.03

        ttk.Label(self._tab_comp, text='Selected compartment from box below:', ) \
            .place(relx=types_start, rely=load_vert_start + 8 * delta_y)

        self._selected_tank = ttk.Label(self._tab_comp, text='', font='Verdana 20 bold')
        self._selected_tank.place(relx=0.3, rely=load_vert_start + 10 * delta_y)

        self._compartments_listbox = tk.Listbox(self._tab_comp, height=int(10 * 1),
                                                width=int(5 * 1),
                                                font=self._text_size["Text 10 bold"]
                                                ,
                                                selectmode='extended')
        self._compartments_listbox.place(relx=types_start, rely=load_vert_start + 10 * delta_y)
        self._compartments_listbox.bind('<<ListboxSelect>>', self.button_1_click_comp_box)

        ttk.Button(self._tab_comp, text="Set compartment\n""properties.", command=self.update_tank,
                   style="Bold.TButton") \
            .place(relx=types_start + delta_x * 4, rely=load_vert_start + delta_y * 10, relwidth=0.3)

        ttk.Button(self._tab_comp, text="Delete all tanks", command=self.delete_all_tanks,
                   style="Bold.TButton").place(relx=types_start + delta_x * 4, rely=load_vert_start + delta_y * 12,
                                               relwidth=0.3)

        self._ent_content_type = ttk.OptionMenu(self._tab_comp, self._new_content_type,
                                                list(self._tank_options.keys())[0], *list(self._tank_options.keys()),
                                                command=self.tank_density_trace)
        ent_width = 10

        self._ent_overpressure = ttk.Entry(self._tab_comp, textvariable=self._new_overpresure,
                                           width=int(ent_width * 1),
                                           )

        self._ent_density = ttk.Entry(self._tab_comp, textvariable=self._new_density,
                                      width=int(ent_width * 1),
                                      )

        self._ent_max_el = ttk.Entry(self._tab_comp, textvariable=self._new_max_el,
                                     width=int(ent_width * 1),
                                     )

        self._ent_min_el = ttk.Entry(self._tab_comp, textvariable=self._new_min_el,
                                     width=int(ent_width * 1),
                                     )

        comp_dx = delta_x
        comp_dy = delta_y
        comp_ent_x = ent_x
        comp_ent_y = 0.4
        ttk.Label(self._tab_comp, text='', ) \
            .place(relx=0.052083333, rely=comp_ent_y + 3.4 * comp_dy)
        ttk.Label(self._tab_comp, text='Tank content :', font=self._text_size['Text 8'], ) \
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 4.5)
        self._ent_content_type.place(relx=comp_ent_x + 0.35 * comp_dx, rely=comp_ent_y + comp_dy * 4.5)
        ttk.Label(self._tab_comp, text='Tank density [kg/m^3]:', font=self._text_size['Text 8'], ) \
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 6)
        self._ent_density.place(relx=comp_ent_x + 0.4 * comp_dx, rely=comp_ent_y + comp_dy * 6)
        ttk.Label(self._tab_comp, text='Overpressure [Pa]:', font=self._text_size['Text 8'], ) \
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 7)
        self._ent_overpressure.place(relx=comp_ent_x + 0.4 * comp_dx, rely=comp_ent_y + comp_dy * 7)
        ttk.Label(self._tab_comp, text='Max elevation [m]:', font=self._text_size['Text 8'], ) \
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 8)
        self._ent_max_el.place(relx=comp_ent_x + 0.4 * comp_dx, rely=comp_ent_y + comp_dy * 8)
        ttk.Label(self._tab_comp, text='Min elevation [m]:', font=self._text_size['Text 8'], ) \
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 9)
        self._ent_min_el.place(relx=comp_ent_x + 0.4 * comp_dx, rely=comp_ent_y + comp_dy * 9)
        self._tank_acc_label = ttk.Label(self._tab_comp, text='Acceleration [m/s^2]: ',
                                         font=self._text_size['Text 8'], )
        self._tank_acc_label.place(relx=hor_start, rely=comp_ent_y + comp_dy * 10)

        # --- button to create compartments and define external pressures ---

        try:
            img_file_name = 'img_int_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._int_button = tk.Button(self._tab_comp, image=photo, command=self.grid_find_tanks, bg='white')
            self._int_button.image = photo
            self._int_button.place(relx=types_start + delta_x, rely=load_vert_start + delta_y * 3,
                                   relheight=0.07, relwidth=0.6)
        except TclError:
            tk.Button(self._tab_comp, text='New tanks - start search \n'
                                           'to find compartments', command=self.grid_find_tanks,
                      bg=self._button_bg_color, fg=self._button_fg_color, ) \
                .place(relx=types_start, rely=load_vert_start + 1.55 * delta_y,
                       relheight=0.044, relwidth=0.3)

        show_compartment = ttk.Button(self._tab_comp, text='Display current\n compartments',
                                      command=self.grid_display_tanks,
                                      style="Bold.TButton")
        show_compartment.place(relx=types_start + delta_x * 4, rely=load_vert_start + delta_y * 14, relwidth=0.3)

        try:
            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)

            self._ext_button = tk.Button(self._tab_comp, image=photo, command=self.on_show_loads,
                                         bg='white')
            self._ext_button.image = photo
            self._ext_button.place(relx=types_start + delta_x, rely=load_vert_start,
                                   relheight=0.07, relwidth=0.6)
        except TclError:
            tk.Button(self._tab_comp, text='New external load window \nsea - static/dynamic',
                      command=self.on_show_loads
                      ) \
                .place(relx=ent_x + delta_x * 1.5, rely=load_vert_start + 1.55 * delta_y,
                       relheight=0.044, relwidth=0.11)

        lc_x, lc_x_delta, lc_y, lc_y_delta = 0.786458333, 0.015625, 0.12037037, 0.023148148

        # --- infomation on accelerations ----
        ttk.Label(self._main_fr, text='Static and dynamic accelerations',
                  ) \
            .place(relx=lc_x, rely=lc_y - 5 * lc_y_delta)
        ttk.Label(self._main_fr, text='Static acceleration [m/s^2]: ',
                  ) \
            .place(relx=lc_x, rely=lc_y - 4 * lc_y_delta)
        ttk.Label(self._main_fr, text='Dyn. acc. loaded [m/s^2]:',
                  ) \
            .place(relx=lc_x, rely=lc_y - 3 * lc_y_delta)
        ttk.Label(self._main_fr, text='Dyn. acc. ballast [m/s^2]:',
                  ) \
            .place(relx=lc_x, rely=lc_y - 2 * lc_y_delta)
        self._new_dyn_acc_loaded = tk.DoubleVar()
        self._new_dyn_acc_ballast = tk.DoubleVar()
        self._new_static_acc = tk.DoubleVar()
        self._new_static_acc.set(9.81), self._new_dyn_acc_loaded.set(0), self._new_dyn_acc_ballast.set(0)
        shift_x_acc = 0.08
        ttk.Entry(self._main_fr, textvariable=self._new_static_acc, width=10,
                  ) \
            .place(relx=lc_x + shift_x_acc, rely=lc_y - 4 * lc_y_delta)
        ttk.Entry(self._main_fr, textvariable=self._new_dyn_acc_loaded, width=10,
                  ) \
            .place(relx=lc_x + shift_x_acc, rely=lc_y - 3 * lc_y_delta)
        ttk.Entry(self._main_fr, textvariable=self._new_dyn_acc_ballast, width=10,
                  ) \
            .place(relx=lc_x + shift_x_acc, rely=lc_y - 2 * lc_y_delta)
        ttk.Button(self._main_fr, text='Set\naccelerations', command=self.create_accelerations,
                   style="Bold.TButton") \
            .place(relx=lc_x + shift_x_acc * 1.5, rely=lc_y - 4 * lc_y_delta)

        # --- checkbuttons and labels ---
        self._dnv_a_chk, self._dnv_b_chk = tk.IntVar(), tk.IntVar()
        self._tank_test_chk, self._manual_chk = tk.IntVar(), tk.IntVar()
        self._check_button_load_comb = [self._dnv_a_chk, self._dnv_b_chk, self._tank_test_chk, self._manual_chk]
        self._active_label = ttk.Label(self._main_fr, text='',
                                       )
        self._active_label.place(relx=lc_x + lc_x_delta * 10, rely=lc_y - lc_y_delta * 5)
        ttk.Label(self._main_fr, text='Combination for line (select line). Change with slider.: ',
                  ) \
            .place(relx=lc_x, rely=lc_y + 2.5 * delta_y)

        lc_y += 0.148148148
        self._combination_slider = ttk.Scale(self._main_fr, from_=1, to=4, command=self.gui_load_combinations,
                                             length=400,
                                             orient='horizontal')
        ttk.Label(self._main_fr, text='1: DNV a)                    2: DNV b)                    3: TankTest        '
                                      '            4: Cylinder') \
            .place(relx=lc_x + 0 * lc_x_delta, rely=lc_y - 2 * lc_y_delta)

        self._combination_slider.place(relx=lc_x + 0 * lc_x_delta, rely=lc_y - 3 * lc_y_delta)
        self._combination_slider_map = {1: 'dnva', 2: 'dnvb', 3: 'tanktest', 4: 'Cylinder'}
        ttk.Label(self._main_fr, text='Name:', ) \
            .place(relx=lc_x + 0 * lc_x_delta, rely=lc_y)
        ttk.Label(self._main_fr, text='Stat LF', ) \
            .place(relx=lc_x + 8.5 * lc_x_delta, rely=lc_y)
        ttk.Label(self._main_fr, text='Dyn LF', ) \
            .place(relx=lc_x + 10.2 * lc_x_delta, rely=lc_y)
        ttk.Label(self._main_fr, text='Include?', font=self._text_size['Text 7'], ) \
            .place(relx=lc_x + 11.8 * lc_x_delta, rely=lc_y)

        self._result_label_dnva = ttk.Label(self._main_fr, text='DNV a [Pa]: ', font='Text 8', )
        self._result_label_dnvb = ttk.Label(self._main_fr, text='DNV b [Pa]: ', font=self._text_size["Text 8"],
                                            )
        self._result_label_tanktest = ttk.Label(self._main_fr, text='Tank test [Pa]: ', font=self._text_size["Text 8"],
                                                )
        self._result_label_manual = ttk.Label(self._main_fr, text='Manual [Pa]: ', font=self._text_size["Text 8"],
                                              )
        self.results_gui_start = 0.6
        self._lab_pressure = ttk.Label(self._main_fr,
                                       text='Pressures for this line: \n(DNV a/b [loaded/ballast], tank test, manual)\n'
                                            'Note that ch. 4.3.7 and 4.3.8 is accounted for.',
                                       font=self._text_size["Text 10"],
                                       )
        self._lab_pressure.place(relx=0.786458333, rely=self.results_gui_start)

        # --- optimize button ---
        ttk.Label(self._main_fr, text='Optimize selected line/structure (right click line):',
                  font=self._text_size['Text 9 bold'], ) \
            .place(relx=lc_x, rely=lc_y - 7 * lc_y_delta)
        try:
            img_file_name = 'img_optimize.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._opt_button = tk.Button(self._main_fr, image=photo, command=self.on_optimize,
                                         bg='white', fg=self._button_fg_color)
            self._opt_button.image = photo
            self._opt_button.place(relx=lc_x, rely=lc_y - 6 * lc_y_delta, relheight=0.04, relwidth=0.098)
        except TclError:
            self._opt_button = tk.Button(self._main_fr, text='Optimize', command=self.on_optimize,
                                         bg=self._button_bg_color, fg=self._button_fg_color)
            self._opt_button.place(relx=lc_x, rely=lc_y - 6 * lc_y_delta, relheight=0.04, relwidth=0.098)
        try:
            img_file_name = 'img_multi_opt.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._opt_button_mult = tk.Button(self._main_fr, image=photo, command=self.on_optimize_multiple,
                                              bg=self._button_bg_color, fg=self._button_fg_color)
            self._opt_button_mult.image = photo
            self._opt_button_mult.place(relx=lc_x + 0.1, rely=lc_y - 6 * lc_y_delta, relheight=0.04, relwidth=0.065)
        except TclError:
            self._opt_button_mult = tk.Button(self._main_fr, text='MultiOpt', command=self.on_optimize_multiple,
                                              bg=self._button_bg_color, fg=self._button_fg_color)
            self._opt_button_mult.place(relx=lc_x + 0.1, rely=lc_y - 6 * lc_y_delta, relheight=0.04, relwidth=0.065)

        try:
            img_file_name = 'cylinder_opt.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._opt_cylinder = tk.Button(self._main_fr, image=photo, command=self.on_optimize_cylinder,
                                           bg='white', fg='white')
            self._opt_cylinder.image = photo
        except TclError:
            self._opt_cylinder = tk.Button(self._main_fr, text='Cylinder optimization',
                                           command=self.on_optimize_cylinder,
                                           bg=self._button_bg_color, fg=self._button_fg_color)

        self._opt_button_span = ttk.Button(self._main_fr, text='SPAN', command=self.on_geometry_optimize,
                                           style="Bold.TButton")
        self._opt_button_span.place(relx=lc_x + 0.167, rely=lc_y - 6 * lc_y_delta, relheight=0.04,
                                    relwidth=0.04)

        self._optimization_buttons = {'Flat plate, stiffened': [self._opt_button, self._opt_button_mult,
                                                                self._opt_button_span],
                                      'Flat plate, stiffened place': [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.098],
                                                                      [lc_x + 0.1, lc_y - 6 * lc_y_delta, 0.04, 0.065],
                                                                      [lc_x + 0.167, lc_y - 6 * lc_y_delta, 0.04,
                                                                       0.04]],
                                      'Flat plate, unstiffened': [self._opt_button],
                                      'Flat plate, unstiffened place': [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.098]],
                                      'Flat plate, stiffened with girder': [self._opt_button],
                                      'Flat plate, stiffened with girder place':
                                          [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.098]],
                                      'cylinder': [self._opt_cylinder],
                                      'cylinder place': [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.175]]}

        # Load information button
        ttk.Button(self._main_fr, text='Load info', command=self.button_load_info_click, style="Bold.TButton") \
            .place(relx=0.78, rely=0.7, relwidth=0.04)

        # ttk.Button(self._main_fr, text='Load info', command=self.button_load_info_click,style = "Bold.TButton")\
        #    .place(relx=0.78,rely=0.7, relwidth = 0.04)
        # Load information button
        ttk.Button(self._main_fr, text='Load factors', command=self.on_open_load_factor_window, style="Bold.TButton") \
            .place(relx=0.8225, rely=0.7, relwidth=0.05)

        # # Wight developement plot
        # self._weight_button = ttk.Button(self._main_fr, text='Weights',
        #                                  command=self.on_plot_cog_dev, style="Bold.TButton")
        # self._weight_button.place(relx=0.875, rely=0.7, relwidth=0.038)



        try:
            img_file_name = 'fesolver_image.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._runtime_fem_button = tk.Button(self._main_fr, image=photo, command=self.on_open_runtime_fem_solver,
                                           bg='white', fg='white')
            self._runtime_fem_button .image = photo
        except TclError:
            self._runtime_fem_button = ttk.Button(
                self._main_fr,
                text='FEM run',
                command=self.on_open_runtime_fem_solver,
                style="Bold.TButton",
            )

        self._place_runtime_fem_button()

        self._chk_show_prop_3d = ttk.Checkbutton(
            self._main_fr,
            text='3D section view',
            variable=self._new_show_prop_3d,
            command=self.update_frame,
        )
        self._chk_show_prop_3d.place(relx=0.637, rely=0.705)

        # Minimum practical size for the current Tkinter layout.  Apply this
        # before the initial property placement so winfo_width() has a real
        # geometry to work from instead of the transient startup width.
        parent.minsize(1200, 750)
        try:
            parent.update_idletasks()
        except Exception:
            pass

        self.calculation_domain_selected(sync_cylinder_inputs=False)  # Initiating the flat panel structural properties
        self.set_colors('default')  # Setting colors theme
        self._prompt_startup_calculation_mode()

        # self._current_theme = 'default'

    def set_colors(self, theme):
        self._current_theme = theme
        if theme == 'light':
            self._general_color = 'alice blue'
            self._color_text = 'black'
            ent_bg = '#FFFFFF'
        elif theme == 'grey':
            self._general_color = 'light grey'
            self._color_text = 'black'
            ent_bg = '#FFFFFF'
        elif theme == 'dark':
            self._general_color = '#2B2B2B'
            self._color_text = 'light grey'
            ent_bg = '#FFFFFF'
        elif theme == 'default':
            self._general_color = '#F0F0F0'
            self._color_text = 'black'
            ent_bg = '#FFFFFF'
        elif theme == 'pink':
            self._general_color = '#FFD3F6'
            self._color_text = 'black'
            ent_bg = 'white'
            # relx=x_canvas_place, rely=0,relwidth=0.523, relheight = 0.73
        elif theme == 'SlavaUkraini':
            self._general_color = '#0057b7'
            self._color_text = 'white'
            ent_bg = 'white'
            cavas_bg = '#ffd700'
        elif theme == 'modelling':
            self._main_canvas.place_forget()
            x_canvas_place = 0.26
            self._main_canvas.place(relx=x_canvas_place, rely=0, relwidth=0.74, relheight=0.99)
            tk.Misc.lift(self._main_canvas)
            self._gui_functional_look = 'modelling'
            self._place_3d_section_view_checkbox()
        elif theme == 'all items':
            self._gui_functional_look = 'all items'
            self._main_canvas.place_forget()
            x_canvas_place = 0.26
            self._main_canvas.place(relx=x_canvas_place, rely=0, relwidth=0.523, relheight=0.73)
            self._place_3d_section_view_checkbox()
        elif theme == 'cylinder':
            self._main_canvas.place_forget()
            x_canvas_place = 0.26
            self._main_canvas.place(relx=x_canvas_place, rely=0, relwidth=0.74, relheight=0.73)
            tk.Misc.lift(self._main_canvas)
            self._gui_functional_look = 'cylinder'
            self._place_3d_section_view_checkbox()
            placement = self._gui_functional_look_cylinder_opt  # [0.786458333, 0.12962963000000005, 0.04, 0.175]
            self._opt_cylinder.place(relx=placement[0], rely=placement[1], relheight=placement[2],
                                     relwidth=placement[3])
            tk.Misc.lift(self._opt_cylinder)

        if theme not in ['modelling', 'all items', 'cylinder']:
            self._style.configure("Bold.TButton", font=('Sans', '10', 'bold'))
            self._style.configure('TCheckbutton', background=self._general_color)
            self._style.configure('TFrame', background=self._general_color)
            self._style.configure('TLabel', background=self._general_color, foreground=self._color_text)
            self._style.configure('TScale', background=self._general_color)
            self._style.configure('TEntry', background=ent_bg)
            self._style.configure('TOptionMenu', background=ent_bg)
            self._style.configure("TMenubutton", background=ent_bg)
            self._style.configure('TRadiobutton', background=self._general_color, foreground='black')
            if theme in ['SlavaUkraini', ]:
                self._prop_canvas.configure(bg=cavas_bg)
                self._main_canvas.configure(bg=cavas_bg)
                self._result_canvas.configure(bg=cavas_bg)
            else:
                self._prop_canvas.configure(bg=self._general_color)
                self._main_canvas.configure(bg=self._general_color)
                self._result_canvas.configure(bg=self._general_color)

        # self._frame_viz_hor.configure(bg =self._color_text)
        # self._frame_viz_ver.configure(bg=self._color_text)

        self.update_frame()

    def _place_3d_section_view_checkbox(self):
        """Keep the 3D preview checkbox visible when functional modes move the main canvas."""
        try:
            self._chk_show_prop_3d.place(relx=0.637, rely=0.705)
            self._chk_show_prop_3d.lift()
        except Exception:
            pass

    def _place_runtime_fem_button(self):
        """Show the runtime FEM entry point only for single/multi modes."""
        try:
            if not getattr(self, '_fea_buckling_mode', False):
                self._runtime_fem_button.place(relx=0.89, rely=0.69, relwidth=0.095)
                self._runtime_fem_button.lift()
            else:
                self._runtime_fem_button.place_forget()
        except Exception:
            pass

    def _prompt_startup_calculation_mode(self):
        """Let the user choose standard, simplified, or FEA-result buckling workflow."""
        try:
            startup_mode = self._show_startup_calculation_mode_dialog()
        except Exception:
            startup_mode = 'multiple'

        if startup_mode is True:
            startup_mode = 'single'
        elif startup_mode is False:
            startup_mode = 'multiple'

        if startup_mode == 'single':
            self.switch_to_single_calculation_mode()
        elif startup_mode == 'fea':
            self.switch_to_fea_result_buckling_mode()
        else:
            self.switch_to_multiple_calculation_mode()
        self._place_runtime_fem_button()

    def _show_startup_calculation_mode_dialog(self):
        """Show a startup mode picker and return ``multiple``, ``single`` or ``fea``."""
        result = {'mode': 'multiple'}
        app_version = self._get_application_version_from_metadata()
        dialog = tk.Toplevel(self._parent, background='#f5f7fb')
        dialog.title('Start ANYstructure')
        dialog.resizable(False, False)
        dialog.transient(self._parent)

        width, height = 920, 416
        try:
            self._parent.update_idletasks()
            root_x = self._parent.winfo_rootx()
            root_y = self._parent.winfo_rooty()
            root_w = self._parent.winfo_width()
            root_h = self._parent.winfo_height()
            pos_x = root_x + max((root_w - width) // 2, 0)
            pos_y = root_y + max((root_h - height) // 2, 0)
            dialog.geometry(f'{width}x{height}+{pos_x}+{pos_y}')
        except Exception:
            dialog.geometry(f'{width}x{height}')

        def choose(mode):
            result['mode'] = mode
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        dialog.protocol('WM_DELETE_WINDOW', lambda: choose('multiple'))
        dialog.bind('<Return>', lambda _event: choose('multiple'))
        dialog.bind('<Escape>', lambda _event: choose('multiple'))

        header = tk.Frame(dialog, background='#172033', height=116)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header_content = tk.Frame(header, background='#172033')
        header_content.pack(fill=tk.BOTH, expand=True, padx=24, pady=14)
        try:
            from PIL import Image, ImageTk
            img_file_name = 'ANYstructure_logo.jpg'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            with Image.open(file_path) as logo_image:
                logo_image.thumbnail((132, 76), Image.LANCZOS)
                logo = ImageTk.PhotoImage(logo_image)
            logo_label = tk.Label(header_content, image=logo, background='white', bd=0, padx=8, pady=6)
            logo_label.image = logo
            logo_label.pack(side=tk.LEFT, padx=(0, 16))
        except Exception:
            pass
        header_text = tk.Frame(header_content, background='#172033')
        header_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(header_text, text='Choose calculation workflow', background='#172033', foreground='white',
                 font=('Segoe UI', 18, 'bold')).pack(anchor=tk.W, pady=(2, 2))
        tk.Label(header_text, text='Start in the workspace that matches the job in front of you.',
                 background='#172033', foreground='#d7deeb', font=('Segoe UI', 10)).pack(anchor=tk.W)
        if app_version is not None:
            tk.Label(header_text, text='Version ' + app_version, background='#172033', foreground='#aebbd0',
                     font=('Segoe UI', 9)).pack(anchor=tk.W, pady=(7, 0))

        content = tk.Frame(dialog, background='#f5f7fb')
        content.pack(fill=tk.BOTH, expand=True, padx=26, pady=24)
        card_row = tk.Frame(content, background='#f5f7fb')
        card_row.pack(fill=tk.BOTH, expand=True)

        def add_mode_card(parent, title, subtitle, details, button_text, command, primary=False):
            border = '#1f6feb' if primary else '#cad2df'
            button_bg = '#1f6feb' if primary else 'green'
            button_fg = 'white' #if primary else '#172033'
            card = tk.Frame(parent, background='white', highlightbackground=border,
                            highlightthickness=2 if primary else 1, bd=0)
            tk.Label(card, text=title, background='white', foreground='#111827',
                     font=('Segoe UI', 13, 'bold')).pack(anchor=tk.W, padx=18, pady=(16, 2))
            tk.Label(card, text=subtitle, background='white', foreground='#475569',
                     font=('Segoe UI', 9, 'bold')).pack(anchor=tk.W, padx=18)
            tk.Label(card, text=details, background='white', foreground='#475569',
                     justify=tk.LEFT, wraplength=245, font=('Segoe UI', 9)).pack(anchor=tk.W, padx=18, pady=(12, 16))
            tk.Button(card, text=button_text, command=command, background=button_bg, foreground=button_fg,
                      activebackground=button_bg, activeforeground=button_fg, relief=tk.FLAT,
                      padx=14, pady=7, font=('Segoe UI', 9, 'bold'), cursor='hand2').pack(
                anchor=tk.W, padx=18, pady=(0, 16))
            return card

        standard_card = add_mode_card(
            card_row,
            title='Multiple panels',
            subtitle='Default',
            details='For multiple panels/cylinders with advanced load definition.',
            button_text='Start multiple panels',
            command=lambda: choose('multiple'),
            primary=False,
        )
        single_card = add_mode_card(
            card_row,
            title='Single panel/cylinder',
            subtitle='Simplified calculation',
            details='For single panel/cylinder with simplified load interface.',
            button_text='Start single mode',
            command=lambda: choose('single'),
            primary=True,
        )
        fea_card = add_mode_card(
            card_row,
            title='FEA result buckling',
            subtitle='FE panel scan',
            details='Import CalculiX INP/FRD or SESAM FEM/SIF files and select buckling panels directly.',
            button_text='Start FEA mode',
            command=lambda: choose('fea'),
            primary=False,
        )
        standard_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        single_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 8))
        fea_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        try:
            dialog.grab_set()
            dialog.focus_force()
        except Exception:
            pass
        self._parent.wait_window(dialog)
        return result['mode']

    @staticmethod
    def _get_application_version_from_metadata():
        """Return the installed package version when distribution metadata is available."""
        for package_name in ('ANYstructure', 'anystructure'):
            try:
                return importlib_metadata.version(package_name)
            except importlib_metadata.PackageNotFoundError:
                pass
        return None

    def switch_to_single_calculation_mode(self):
        """Switch from standard modelling to the simplified one-line calculation workflow."""
        self._fea_buckling_mode = False
        self._clear_fea_buckling_option_widgets()
        selected_line = self._active_line if self._active_line in self._line_dict else None
        if selected_line is not None:
            self._single_line_name = selected_line
            if selected_line in self._line_to_struc:
                self.set_selected_variables(selected_line)
        elif self._line_dict:
            self._single_line_name = sorted(self._line_dict.keys(), key=get_num)[0]

        self._simplified_calculation_mode = True
        self._activate_simplified_calculation_pipeline()
        self._place_3d_section_view_checkbox()
        self._place_runtime_fem_button()

    def switch_to_multiple_calculation_mode(self):
        """Switch back to the standard multi-panel modelling workflow."""
        self._fea_buckling_mode = False
        self._simplified_calculation_mode = False
        self._new_show_prop_3d.set(False)
        self._show_standard_calculation_layout()
        self.clear_prop_3d()
        self._select_single_calculation_line()
        self.update_frame(force_recalc=True)
        self._place_3d_section_view_checkbox()
        try:
            self.gui_load_combinations(self._combination_slider.get())
        except Exception:
            pass
        self._place_runtime_fem_button()

    def switch_to_fea_result_buckling_mode(self):
        """Switch to FE-result buckling where clickable panels replace ship lines."""
        self._fea_buckling_mode = True
        self._simplified_calculation_mode = False
        self._new_show_prop_3d.set(False)
        self.clear_prop_3d()
        self._apply_fea_buckling_layout()
        self._active_line = ''
        self._line_is_active = False
        self._active_point = ''
        self._point_is_active = False
        self._refresh_fea_buckling_views(rebuild_3d=True)
        self._place_runtime_fem_button()

    def _apply_fea_buckling_layout(self):
        """Hide ship modelling/load tabs and make FE panels the active workspace."""
        try:
            self._tabControl.hide(self._tab_geo)
            self._tabControl.hide(self._tab_comp)
            self._tabControl.select(self._tab_prop)
        except Exception:
            pass

        try:
            self.add_stucture.config(text='Update selected\nFEA panel input')
        except Exception:
            pass
        try:
            self._chk_show_prop_3d.place_forget()
        except Exception:
            pass

    def _activate_simplified_calculation_pipeline(self):
        """Initialize the default one-line calculation model used by the main GUI."""
        if not getattr(self, '_simplified_calculation_mode', False):
            return

        self._ensure_single_dummy_line()
        self._select_single_calculation_line()
        self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)
        self._sync_single_line_structure_from_inputs()
        self._apply_simplified_calculation_layout()
        self._new_show_prop_3d.set(True)
        self.update_frame(force_recalc=True)
        self.gui_load_combinations(self._combination_slider.get())

    def _apply_simplified_calculation_layout(self):
        """Hide modelling tabs and make the line-property tab the primary input surface."""
        try:
            self._tabControl.hide(self._tab_geo)
            self._tabControl.hide(self._tab_comp)
            self._tabControl.select(self._tab_prop)
        except Exception:
            pass

        try:
            self.add_stucture.config(text='Update single-line\ncalculation model')
        except Exception:
            pass

    def _show_standard_calculation_layout(self):
        """Restore modelling tabs and controls for the standard multi-panel workflow."""
        self._clear_fea_buckling_option_widgets()
        try:
            self._tabControl.add(self._tab_geo, text='Geometry')
            self._tabControl.add(self._tab_comp, text='Compartments and loads')
        except Exception:
            pass

        try:
            self._tabControl.select(self._tab_geo)
        except Exception:
            pass

        try:
            self.add_stucture.config(text='Press to add input properties\n'
                                          'to the selected line. Sets all\n'
                                          'basic structural information.')
        except Exception:
            pass

    def _clear_fea_buckling_option_widgets(self):
        frame = getattr(self, '_fea_right_panel_frame', None)
        if frame is not None:
            try:
                frame.destroy()
            except Exception:
                pass
            self._fea_right_panel_frame = None
        for item in getattr(self, '_fea_buckling_created', []):
            try:
                item.destroy()
            except Exception:
                pass
        self._fea_buckling_created = []
    def on_import_fem_and_run_solver(self):
        """Ask for a FEM file, parse it, and send it to the internal FE solver window."""
        inp_path = filedialog.askopenfilename(
            title='Import FEM and run in fe-solver',
            filetypes=(
                ('SESAM FEM', '*.FEM *.fem'),
                ('All files', '*.*'),
            ),
        )
        if not inp_path:
            return

        from anystruct.api import import_sesam_fem_model
        try:
            import_result = import_sesam_fem_model(inp_path)
            if not import_result or import_result.model is None:
                messagebox.showerror("FEM Import Error", "Failed to parse FEM file into a valid model.")
                return

            from anystruct.fem_integration import open_runtime_fem_window
            open_runtime_fem_window(self._parent, self, imported_fem_model=import_result.model, imported_path=inp_path)
        except Exception as e:
            messagebox.showerror("FEM Import Error", f"An error occurred while importing FEM:\n{e}")

    def _launch_fe_solver_with_fem_geometry(self, inp_path):
        """Route an imported SESAM .FEM (geometry only) to the FE-solver GUI.

        SESAM .FEM files carry mesh geometry but no stress results, so they
        cannot be used for FEA-result buckling. Only .SIF (and, once supported,
        .SIN) files contain stresses. When the geometry parses sufficiently,
        offer to launch the FE-GUI with it so the user can solve for stresses.
        """
        from anystruct.api import import_sesam_fem_model
        try:
            import_result = import_sesam_fem_model(inp_path)
        except Exception as err:
            messagebox.showerror("FEM Import Error", f"An error occurred while importing FEM:\n{err}")
            return
        model = None if import_result is None else import_result.model
        mesh = getattr(model, 'mesh', None)
        parsed_ok = (
            model is not None
            and mesh is not None
            and getattr(mesh, 'num_nodes', 0) > 0
            and getattr(mesh, 'num_elements', 0) > 0
        )
        if not parsed_ok:
            messagebox.showerror(
                "FEM Import Error",
                "The SESAM .FEM geometry could not be parsed sufficiently to build a model.\n\n"
                "Note: .FEM files contain geometry only. Buckling results require a .SIF "
                "result file (.SIN results are not yet supported)."
            )
            return
        launch = messagebox.askyesno(
            "Launch FE-solver?",
            "SESAM .FEM files contain geometry only, not stresses, so they cannot be used "
            "directly for FEA buckling results.\n\n"
            f"The geometry was parsed successfully ({mesh.num_nodes} nodes, "
            f"{mesh.num_elements} elements).\n\n"
            "Launch the FE-GUI (FE-solver) with this imported geometry?",
            parent=self._parent,
        )
        if not launch:
            return
        from anystruct.fem_integration import open_runtime_fem_window
        open_runtime_fem_window(self._parent, self, imported_fem_model=model, imported_path=inp_path)

    def open_fea_buckling_files(self):
        """Ask for FE model/result files and import them into FEA-result buckling mode."""
        inp_path = filedialog.askopenfilename(
            title='Open FE model/input deck',
            filetypes=(
                ('Supported FE model/result', '*.inp *.FEM *.fem *.SIF *.sif'),
                ('CalculiX input', '*.inp'),
                ('SESAM SIF (results)', '*.SIF *.sif'),
                ('SESAM FEM (geometry -> FE-solver)', '*.FEM *.fem'),
                ('All files', '*.*'),
            ),
        )
        if not inp_path:
            return
        lower = str(inp_path).lower()
        if lower.endswith('.fem'):
            # SESAM .FEM carries geometry only (no stresses); it is not imported
            # for buckling. Offer to launch the FE-solver with the geometry.
            self._launch_fe_solver_with_fem_geometry(inp_path)
            return
        if lower.endswith('.sif'):
            self.import_fea_buckling_files(inp_path, None)
            return
        frd_path = filedialog.askopenfilename(
            title='Open FE result file',
            filetypes=(
                ('Supported FE result', '*.frd *.SIF *.sif'),
                ('CalculiX result', '*.frd'),
                ('SESAM SIF', '*.SIF *.sif'),
                ('All files', '*.*'),
            ),
        )
        self.import_fea_buckling_files(inp_path, frd_path or None)

    def reimport_fea_buckling_files(self):
        """Re-read the last FEA files using current buckling options."""
        if getattr(self, '_fea_last_runtime_result', None) is not None:
            self.import_runtime_fem_buckling_result(self._fea_last_runtime_result)
            return
        if not self._fea_last_inp_path:
            self.open_fea_buckling_files()
            return
        self.import_fea_buckling_files(
            self._fea_last_inp_path, 
            self._fea_last_frd_path,
            forced_geometry_type=getattr(self, '_fea_last_geometry_type', None)
        )

    @staticmethod
    def _fea_panel_line_length_m(panel):
        try:
            return max(float(panel.field.span_m), 0.001)
        except Exception:
            return 1.0

    @staticmethod
    def _fea_panel_domain(panel):
        try:
            domain = panel.anystructure_input.get('calculation_domain', '')
        except Exception:
            domain = ''
        return str(domain or 'FEA buckling panels')

    @staticmethod
    def _next_numbered_name(existing_names, prefix):
        highest = 0
        for name in existing_names:
            text = str(name)
            if not text.startswith(prefix):
                continue
            try:
                highest = max(highest, int(text[len(prefix):]))
            except ValueError:
                continue
        return highest + 1

    def _clear_fea_panel_line_model(self):
        """Remove only the hidden line model generated by the last FEA import."""
        for line_name in list(getattr(self, '_fea_imported_line_names', [])):
            endpoints = self._line_dict.pop(line_name, None)
            self._line_to_struc.pop(line_name, None)
            self._state_logger.pop(line_name, None)
            if endpoints:
                for endpoint_key in self.make_point_point_line_string(endpoints[0], endpoints[1]):
                    try:
                        self._line_point_to_point_string.remove(endpoint_key)
                    except ValueError:
                        pass
            for key in [
                key for key in self._new_load_comb_dict
                if len(key) > 1 and key[1] == line_name
            ]:
                self._new_load_comb_dict.pop(key, None)

        for point_name in list(getattr(self, '_fea_imported_point_names', [])):
            self._point_dict.pop(point_name, None)

        self._fea_panel_line_by_field = {}
        self._fea_imported_line_names = []
        self._fea_imported_point_names = []
        self._fea_imported_endpoint_keys = []
        if self._active_line not in self._line_dict:
            self._active_line = ''
            self._line_is_active = False

    def _create_fea_panel_structure_objects(self, panel):
        """Build the normal line structure objects for one imported FE panel."""
        old_selected = self._fea_selected_panel_id
        try:
            self._fea_selected_panel_id = panel.field_id
            self._apply_selected_fea_panel_to_inputs()
            all_obj = self._fea_panel_all_structure()
            cylinder_obj = self._fea_panel_cylinder_structure(panel)
            return all_obj, cylinder_obj
        finally:
            self._fea_selected_panel_id = old_selected

    def _rebuild_fea_panel_line_model(self):
        """Represent each imported buckling panel as one hidden project line."""
        self._clear_fea_panel_line_model()
        session = self._fea_buckling_session
        if session is None:
            return

        domain_rows = {}
        for panel in session.panels:
            domain = self._fea_panel_domain(panel)
            if domain not in domain_rows:
                domain_rows[domain] = len(domain_rows)

        x_cursor_by_domain = {domain: 0.0 for domain in domain_rows}
        point_number = self._next_numbered_name(self._point_dict.keys(), 'point')
        line_number = self._next_numbered_name(self._line_dict.keys(), 'line')
        line_structures = project_services.LineStructureService(self._line_to_struc)
        horizontal_gap_m = 0.5
        row_gap_m = 0.5

        old_active_line = self._active_line
        old_line_is_active = self._line_is_active
        old_selected = self._fea_selected_panel_id
        try:
            for panel in session.panels:
                domain = self._fea_panel_domain(panel)
                y = -domain_rows[domain] * row_gap_m
                x0 = x_cursor_by_domain[domain]
                length = self._fea_panel_line_length_m(panel)
                x1 = x0 + length
                point1 = point_number
                point2 = point_number + 1
                point_number += 2
                point_name1 = 'point' + str(point1)
                point_name2 = 'point' + str(point2)
                line_name = 'fea_panel_' + str(line_number).zfill(3)
                while line_name in self._line_dict or line_name in self._line_to_struc:
                    line_number += 1
                    line_name = 'fea_panel_' + str(line_number).zfill(3)
                line_number += 1

                self._point_dict[point_name1] = [x0, y]
                self._point_dict[point_name2] = [x1, y]
                self._line_dict[line_name] = [point1, point2]
                endpoint_keys = self.make_point_point_line_string(point1, point2)
                self._line_point_to_point_string.extend(endpoint_keys)

                self._active_line = line_name
                self._line_is_active = True
                all_obj, cylinder_obj = self._create_fea_panel_structure_objects(panel)
                all_obj.need_recalc = True
                line_structures.assign_structure(line_name, all_obj, cylinder=cylinder_obj)
                self._new_load_comb_dict[('manual', line_name, 'manual')] = [
                    tk.DoubleVar(value=self._fea_panel_pressure_mpa(panel) * 1.0e6),
                    tk.DoubleVar(value=1.0),
                    tk.IntVar(value=1),
                ]

                self._fea_panel_line_by_field[panel.field_id] = line_name
                self._fea_imported_line_names.append(line_name)
                self._fea_imported_point_names.extend([point_name1, point_name2])
                self._fea_imported_endpoint_keys.extend(endpoint_keys)
                x_cursor_by_domain[domain] = x1 + horizontal_gap_m
        finally:
            self._active_line = old_active_line
            self._line_is_active = old_line_is_active
            self._fea_selected_panel_id = old_selected

    def import_fea_buckling_files(self, inp_path, frd_path=None, forced_geometry_type=None):
        """Load FEA files and prepare clickable buckling panels."""
        input_text = str(inp_path)
        input_lower = input_text.lower()
        if input_lower.endswith('.fem'):
            # SESAM .FEM carries geometry only (no stresses) and must never be
            # imported for buckling results; route it to the FE-solver instead.
            self._launch_fe_solver_with_fem_geometry(input_text)
            return
        has_result_source = bool(frd_path) or input_lower.endswith('.sif')

        geometry_type = forced_geometry_type or "auto"
        if geometry_type == "auto":
            try:
                model = fe_plate_fields.read_fea_shell_model(inp_path)
                if fe_plate_fields.is_cylindrical_shell_model(model):
                    ans = messagebox.askyesno(
                        "Cylinder detected",
                        "The imported model appears to be a cylindrical shell.\nDo you want to process it as a cylinder?\n\nSelecting 'No' will process it as a flat plate.",
                        parent=self._parent
                    )
                    geometry_type = "cylinder" if ans else "flat"
            except Exception:
                pass
        self._fea_last_geometry_type = geometry_type

        try:
            self._fea_buckling_session = fe_plate_fields.create_fea_buckling_session(
                inp_path,
                frd_path,
                geometry_type=geometry_type,
                calculation_method=self._new_buckling_method.get(),
                buckling_acceptance=self._new_puls_method.get(),
                pressure_mpa=0.0,
                material_yield_mpa=self._new_material.get(),
                material_factor=self._new_material_factor.get(),
                ml_algo=getattr(self, '_ML_buckling', None),
                run_buckling=has_result_source,
                stress_reduction_method=self._fea_stress_reduction_method.get(),
                load_case=getattr(self, '_fea_selected_load_case', None),
            )
            if self._fea_buckling_session and hasattr(self._fea_buckling_session, 'active_load_case') and self._fea_buckling_session.active_load_case is not None:
                self._fea_selected_load_case = self._fea_buckling_session.active_load_case
        except Exception as err:
            messagebox.showerror('FEA import error', str(err))
            return

        self._fea_last_inp_path = str(inp_path)
        self._fea_last_frd_path = None if frd_path is None else str(frd_path)
        self._fea_last_runtime_result = None
        self._rebuild_fea_panel_line_model()
        first_panel = self._fea_buckling_session.panels[0] if self._fea_buckling_session.panels else None
        self._fea_selected_panel_id = None if first_panel is None else first_panel.field_id
        if self._fea_selected_panel_id in self._fea_panel_line_by_field:
            self._active_line = self._fea_panel_line_by_field[self._fea_selected_panel_id]
            self._line_is_active = True
        self._apply_selected_fea_panel_to_inputs()
        self._refresh_fea_buckling_views(rebuild_3d=True)
        warnings = [
            str(item) for item in getattr(self._fea_buckling_session, 'diagnostics', ())
            if str(item).startswith('WARNING:')
        ]
        if warnings:
            messagebox.showwarning('FEA buckling method warning', '\n\n'.join(warnings))

    def import_runtime_fem_buckling_result(self, runtime_result):
        """Load an in-memory runtime FEM result into FEA-result buckling mode."""
        try:
            self._fea_buckling_session = fe_plate_fields.create_runtime_fea_buckling_session(
                runtime_result,
                calculation_method=self._new_buckling_method.get(),
                buckling_acceptance=self._new_puls_method.get(),
                pressure_mpa=0.0,
                material_yield_mpa=self._new_material.get(),
                material_factor=self._new_material_factor.get(),
                ml_algo=getattr(self, '_ML_buckling', None),
                run_buckling=True,
                stress_reduction_method=self._fea_stress_reduction_method.get(),
                load_case=getattr(self, '_fea_selected_load_case', None),
            )
            if self._fea_buckling_session and hasattr(self._fea_buckling_session, 'active_load_case') and self._fea_buckling_session.active_load_case is not None:
                self._fea_selected_load_case = self._fea_buckling_session.active_load_case
        except Exception as err:
            messagebox.showerror('Runtime FEA import error', str(err))
            return False

        self._fea_last_inp_path = None
        self._fea_last_frd_path = None
        self._fea_last_runtime_result = runtime_result
        self._fea_buckling_mode = True
        self._apply_fea_buckling_layout()
        self._rebuild_fea_panel_line_model()
        first_panel = self._fea_buckling_session.panels[0] if self._fea_buckling_session.panels else None
        self._fea_selected_panel_id = None if first_panel is None else first_panel.field_id
        if self._fea_selected_panel_id in self._fea_panel_line_by_field:
            self._active_line = self._fea_panel_line_by_field[self._fea_selected_panel_id]
            self._line_is_active = True
        self._apply_selected_fea_panel_to_inputs()
        self._refresh_fea_buckling_views(rebuild_3d=True)
        self._place_runtime_fem_button()
        warnings = [
            str(item) for item in getattr(self._fea_buckling_session, 'diagnostics', ())
            if str(item).startswith('WARNING:')
        ]
        if warnings:
            messagebox.showwarning('FEA buckling method warning', '\n\n'.join(warnings))
        return True

    def _apply_selected_fea_panel_to_inputs(self):
        """Copy the selected FE panel into the normal ANYstructure input variables."""
        if self._fea_buckling_session is None or self._fea_selected_panel_id is None:
            return
        try:
            panel = self._fea_buckling_session.panel(self._fea_selected_panel_id)
        except KeyError:
            return
        data = panel.anystructure_input
        if isinstance(data.get('shell'), dict):
            self._apply_selected_fea_cylinder_panel_to_inputs(data)
            return

        geometry = data.get('geometry', {})
        section = data.get('section', {})
        material = data.get('material', {})
        stresses = data.get('stresses', {})
        buckling = data.get('buckling', {})

        self._new_calculation_domain.set(data.get('calculation_domain', 'Flat plate, stiffened'))
        self._new_field_len.set(round(float(geometry.get('span_mm', 0.0)), 5))
        self._new_stf_spacing.set(round(float(geometry.get('spacing_mm', 0.0)), 5))
        self._new_plate_thk.set(round(float(geometry.get('plate_thickness_mm', 0.0)), 5))
        self._new_stf_type.set(str(section.get('type', 'FB') or 'FB'))
        self._new_stf_web_h.set(round(float(section.get('web_height_mm', 0.0)), 5))
        self._new_stf_web_t.set(round(float(section.get('web_thickness_mm', 0.0)), 5))
        self._new_stf_fl_w.set(round(float(section.get('flange_width_mm', 0.0)), 5))
        self._new_stf_fl_t.set(round(float(section.get('flange_thickness_mm', 0.0)), 5))
        self._new_material.set(round(float(material.get('yield_mpa', 355.0)), 5))
        self._new_material_factor.set(float(material.get('material_factor', 1.15)))
        self._new_sigma_x1.set(round(float(stresses.get('sigma_x1_mpa', 0.0)), 5))
        self._new_sigma_x2.set(round(float(stresses.get('sigma_x2_mpa', 0.0)), 5))
        self._new_sigma_y1.set(round(float(stresses.get('sigma_y1_mpa', 0.0)), 5))
        self._new_sigma_y2.set(round(float(stresses.get('sigma_y2_mpa', 0.0)), 5))
        self._new_tauxy.set(round(float(stresses.get('tau_xy_mpa', 0.0)), 5))
        self._new_buckling_method.set(str(buckling.get('calculation_method', self._new_buckling_method.get())))
        self._new_puls_method.set(str(buckling.get('buckling_acceptance', self._new_puls_method.get())))
        self._new_puls_panel_boundary.set(str(buckling.get('puls_boundary', 'Int')))
        self._new_puls_sp_or_up.set(str(buckling.get('puls_sp_or_up', 'SP')))
        self._new_puls_up_boundary.set(str(buckling.get('puls_up_boundary', 'SSSS')))
        self.calculation_domain_selected(sync_cylinder_inputs=False)

    def _apply_selected_fea_cylinder_panel_to_inputs(self, data):
        """Copy one FE cylinder panel into the existing cylinder GUI variables."""

        def number(container, key, default=0.0):
            try:
                value = float(container.get(key, default))
            except (AttributeError, TypeError, ValueError):
                value = default
            return value if math.isfinite(value) else default

        def positive(container, key, default):
            value = number(container, key, default)
            return value if value > 1.0e-9 else default

        def set_member(member, web_h, web_t, flange_w, flange_t, member_type):
            if not isinstance(member, dict):
                return
            web_h.set(round(positive(member, 'web_height_mm', 1.0), 5))
            web_t.set(round(positive(member, 'web_thickness_mm', 1.0), 5))
            flange_w.set(round(max(number(member, 'flange_width_mm', 0.0), 0.0), 5))
            flange_t.set(round(max(number(member, 'flange_thickness_mm', 0.0), 0.0), 5))
            member_type.set(str(member.get('type', 'FB') or 'FB'))

        shell = data.get('shell', {})
        material = data.get('material', {})
        stresses = data.get('stresses', {})
        domain = str(data.get('calculation_domain', 'Unstiffened shell'))
        if domain in api_helpers.CYLINDER_STRUCTURE_DOMAINS:
            domain = api_helpers.cylinder_domain_with_input_mode(domain)

        thickness_mm = positive(shell, 'thickness_mm', max(float(self._new_shell_thk.get() or 0.0), 1.0))
        radius_mm = positive(shell, 'radius_mm', max(float(self._new_shell_radius.get() or 0.0), 1.0))
        length_mm = positive(shell, 'total_length_mm', positive(shell, 'distance_between_rings_mm', 1.0))
        distance_between_rings_mm = positive(shell, 'distance_between_rings_mm', length_mm)
        panel_spacing_mm = positive(shell, 'panel_spacing_mm', max(float(self._new_stf_spacing.get() or 0.0), 1.0))

        self._new_calculation_domain.set(domain)
        self._new_panel_or_shell.set('shell')
        self._new_shell_stress_or_force.set(2)
        self._new_shell_thk.set(round(thickness_mm, 5))
        self._new_shell_radius.set(round(radius_mm, 5))
        self._new_shell_dist_rings.set(round(distance_between_rings_mm, 5))
        self._new_shell_length.set(round(distance_between_rings_mm, 5))
        self._new_shell_tot_length.set(round(length_mm, 5))
        self._new_shell_panel_spacing.set(round(panel_spacing_mm, 5))
        self._new_shell_ring_frame_length_between_girders.set(round(distance_between_rings_mm, 5))
        self._new_shell_k_factor.set(1.0)
        self._new_plate_thk.set(round(thickness_mm, 5))
        self._new_field_len.set(round(distance_between_rings_mm, 5))
        self._new_stf_spacing.set(round(panel_spacing_mm, 5))

        material_yield = number(material, 'yield_mpa', 355.0)
        material_factor = number(material, 'material_factor', 1.15)
        elastic_modulus = number(material, 'elastic_modulus_mpa', 210000.0)
        poisson = number(material, 'poisson', 0.3)
        self._new_material.set(round(material_yield, 5))
        self._new_material_factor.set(material_factor)
        self._new_shell_yield.set(round(material_yield, 5))
        self._new_shell_mat_factor.set(material_factor)
        self._new_shell_e_module.set(elastic_modulus * 1.0e6)
        self._new_shell_poisson.set(poisson)

        sasd = number(stresses, 'sasd_mpa', 0.0)
        smsd = number(stresses, 'smsd_mpa', 0.0)
        tTsd = number(stresses, 'tTsd_mpa', 0.0)
        tQsd = number(stresses, 'tQsd_mpa', 0.0)
        psd = number(stresses, 'psd_mpa', 0.0)
        shsd = number(stresses, 'shsd_mpa', 0.0)
        self._new_shell_sasd.set(round(sasd, 5))
        self._new_shell_smsd.set(round(smsd, 5))
        self._new_shell_tTsd.set(round(tTsd, 5))
        self._new_shell_tQsd.set(round(tQsd, 5))
        self._new_shell_psd.set(round(psd, 5))
        self._new_shell_shsd.set(round(shsd, 5))
        self._new_sigma_x1.set(round(max(-sasd, 0.0), 5))
        self._new_sigma_x2.set(round(max(-sasd, 0.0), 5))
        self._new_sigma_y1.set(round(max(-shsd, 0.0), 5))
        self._new_sigma_y2.set(round(max(-shsd, 0.0), 5))
        self._new_tauxy.set(round(abs(tTsd), 5))

        longitudinal = data.get('longitudinal_stiffener')
        ring_stiffener = data.get('ring_stiffener')
        ring_frame = data.get('ring_frame')
        set_member(
            longitudinal,
            self._new_stf_web_h,
            self._new_stf_web_t,
            self._new_stf_fl_w,
            self._new_stf_fl_t,
            self._new_stf_type,
        )
        set_member(
            ring_stiffener,
            self._new_shell_ring_stf_hw,
            self._new_shell_ring_stf_tw,
            self._new_shell_ring_stf_b,
            self._new_shell_ring_stf_tf,
            self._new_shell_ring_stf_type,
        )
        set_member(
            ring_frame,
            self._new_shell_ring_frame_hw,
            self._new_shell_ring_frame_tw,
            self._new_shell_ring_frame_b,
            self._new_shell_ring_frame_tf,
            self._new_shell_ring_frame_type,
        )
        set_member(
            ring_frame or ring_stiffener,
            self._new_girder_web_h,
            self._new_girder_web_t,
            self._new_girder_fl_w,
            self._new_girder_fl_t,
            self._new_girder_type,
        )
        self._new_girder_length_LG.set(round(distance_between_rings_mm, 5))
        self._new_shell_exclude_ring_stf.set(ring_stiffener is None)
        self._new_shell_exclude_ring_frame.set(ring_frame is None)
        self.calculation_domain_selected(sync_cylinder_inputs=False)

    def _ensure_fea_lower_panes_visible(self):
        """Keep FEA mode's selected-panel sketch and result text panes visible."""
        try:
            main_place = self._main_canvas.place_info()
            x_canvas_place = float(main_place.get('relx', 0.26))
            right_limit = 0.915
            total_width = max(right_limit - x_canvas_place, 0.30)
            prop_width = total_width * 0.43
            result_width = total_width - prop_width
            self._prop_canvas.place(relx=x_canvas_place, rely=0.73, relwidth=prop_width, relheight=0.27)
            self._result_canvas.place(relx=x_canvas_place + prop_width, rely=0.73,
                                      relwidth=result_width, relheight=0.27)
            tk.Misc.lift(self._prop_canvas)
            tk.Misc.lift(self._result_canvas)
        except Exception:
            pass

    def _refresh_fea_lower_panes(self):
        self._ensure_fea_lower_panes_visible()
        self._draw_fea_panel_result_text()
        self._draw_fea_panel_2d_sketch()

    def _refresh_fea_buckling_views(self, rebuild_3d=False):
        if rebuild_3d:
            self._draw_fea_buckling_canvas()
        else:
            self._update_fea_3d_selection()
        self._refresh_fea_lower_panes()
        self._gui_fea_buckling_options()

    def _on_fea_buckling_option_changed(self, *_args):
        if self._fea_last_inp_path:
            self.reimport_fea_buckling_files()
        else:
            self._gui_fea_buckling_options()

    def _on_fea_load_case_changed(self, event=None):
        if not getattr(self, '_fea_buckling_mode', False):
            return
        try:
            val = self._fea_load_case_combobox.get()
            self._fea_selected_load_case = int(val.split(' - ')[0])
            self.reimport_fea_buckling_files()
        except ValueError:
            pass

    @staticmethod
    def _fea_stress_method_description(method):
        if method == 'Centre strip mean':
            return (
                'Averages projected membrane stresses in a narrow centre strip. '
                'Useful as a sensitivity check when panel-edge stress peaks are local.'
            )
        if method == 'Whole panel nodal mean':
            return (
                'Averages all matching FRD result nodes equally. This preserves the '
                'earlier ANYstructure import behaviour for comparison.'
            )
        return (
            'Default CSR-style interpretation: project stresses to local panel axes, '
            'then area-weight membrane stresses over the buckling panel elements.'
        )

    def _draw_fea_stress_interpretation_canvas(self, canvas, panel):
        canvas.delete('all')
        method = self._fea_stress_reduction_method.get()
        width, height = 285, 140
        canvas.configure(width=width, height=height)
        bg = self._style.lookup('TFrame', 'background') or 'white'
        canvas.configure(background=bg)

        x0, y0, x1, y1 = 20, 24, 264, 76
        canvas.create_rectangle(x0, y0, x1, y1, outline='#555555', fill='#f7f7f7', width=1)
        if method == 'Centre strip mean':
            strip_half = 14
            centre = 0.5 * (x0 + x1)
            canvas.create_rectangle(centre - strip_half, y0, centre + strip_half, y1, outline='', fill='#7fc8ff')
            caption = 'centre strip'
        elif method == 'Whole panel nodal mean':
            caption = 'equal nodal mean'
            for ix in range(5):
                for iy in range(3):
                    px = x0 + 24 + ix * 34
                    py = y0 + 11 + iy * 15
                    canvas.create_oval(px - 3, py - 3, px + 3, py + 3, outline='', fill='#2b78c6')
        else:
            caption = 'area weighted'
            for ix in range(4):
                shade = '#f9d58a' if ix % 2 == 0 else '#f3b86a'
                xa = x0 + ix * (x1 - x0) / 4
                xb = x0 + (ix + 1) * (x1 - x0) / 4
                canvas.create_rectangle(xa, y0, xb, y1, outline='#dddddd', fill=shade)

        canvas.create_line(x0, y1 + 9, x1, y1 + 9, arrow=tk.LAST, fill='#444444')
        canvas.create_text(x1 + 5, y1 + 9, text='x', anchor=tk.W, font=self._text_size['Text 8'])
        canvas.create_line(x0 - 10, y1, x0 - 10, y0, arrow=tk.LAST, fill='#444444')
        canvas.create_text(x0 - 10, y0 - 5, text='y', anchor=tk.S, font=self._text_size['Text 8'])
        canvas.create_text(0.5 * (x0 + x1), 12, text=caption, anchor=tk.CENTER, font=self._text_size['Text 8 bold'])

        stress_text = 'no FRD stress'
        reduction_text = method
        if panel is not None and getattr(panel, 'stress', None) is not None:
            stress = panel.stress
            reduction_text = stress.reduction
            if hasattr(stress, 'sigma_x1_mpa'):
                stress_text = (
                    f"sx {stress.sigma_x1_mpa:.1f}, sy {stress.sigma_y1_mpa:.1f}, "
                    f"tau {stress.tau_xy_mpa:.1f} MPa"
                )
            else:
                stress_text = (
                    f"ax {stress.axial_stress_mpa:.1f}, hoop {stress.hoop_stress_mpa:.1f}, "
                    f"tau {stress.torsional_shear_mpa:.1f} MPa"
                )
            stress_text += f" | n={stress.sample_count}"

        canvas.create_text(20, 100, text=stress_text, anchor=tk.W, font=self._text_size['Text 8'], width=250)
        canvas.create_text(20, 116, text=reduction_text, anchor=tk.W, font=self._text_size['Text 8'], width=250)

    def _show_fea_buckling_details_popup(self):
        """Show every calculated UF and buckling detail for the selected FE panel."""
        session = getattr(self, '_fea_buckling_session', None)
        selected_id = getattr(self, '_fea_selected_panel_id', None)
        panel = None
        if session is not None and selected_id is not None:
            try:
                panel = session.panel(selected_id)
            except KeyError:
                panel = None
        if panel is None:
            messagebox.showinfo(
                'FEA buckling details',
                'Select an FE buckling panel first.',
                parent=self._parent,
            )
            return

        details = fe_plate_fields.format_panel_buckling_details(
            panel,
            uf_basis=self._new_puls_method.get(),
        )
        popup = tk.Toplevel(self._parent)
        popup.title(f'Buckling details - {panel.field_id}')
        popup.geometry('560x640')
        text_frame = tk.Frame(popup)
        text_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(
            text_frame,
            wrap=tk.NONE,
            font=('Consolas', 9),
            yscrollcommand=scrollbar.set,
        )
        text_widget.insert('1.0', details)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.configure(command=text_widget.yview)
        ttk.Button(popup, text='Close', command=popup.destroy).pack(side=tk.BOTTOM, pady=4)

    def _select_fea_panel(self, field_id):
        self._fea_selected_panel_id = field_id
        line_name = getattr(self, '_fea_panel_line_by_field', {}).get(field_id)
        if line_name in self._line_dict:
            self._active_line = line_name
            self._line_is_active = True
        self._apply_selected_fea_panel_to_inputs()
        self._refresh_fea_buckling_views(rebuild_3d=False)

    def _single_mode_active_line_candidate(self):
        """Return the selected line when valid, otherwise the remembered dummy/single line."""
        if self._active_line in self._line_dict:
            return self._active_line
        if self._single_line_name in self._line_dict:
            return self._single_line_name
        if self._line_dict:
            return sorted(self._line_dict.keys(), key=get_num)[0]
        return self._single_line_name

    def _ensure_single_dummy_line(self):
        """Create the hidden point/line geometry needed by the legacy calculation pipeline."""
        if self._line_dict:
            self._single_line_name = self._single_mode_active_line_candidate()
            return

        try:
            length = max(float(self._new_field_len.get()) / 1000.0, 1.0)
        except Exception:
            length = 4.0

        self._point_dict['point1'] = [0.0, 0.0]
        self._point_dict['point2'] = [length, 0.0]
        self._line_dict[self._single_line_name] = [1, 2]
        self._line_point_to_point_string = self.make_point_point_line_string(1, 2)

    def _select_single_calculation_line(self):
        """Keep single-line mode bound to the selected line or the dummy line."""
        self._single_line_name = self._single_mode_active_line_candidate()
        self._active_line = self._single_line_name
        self._line_is_active = self._active_line in self._line_dict
        self._active_point = ''
        self._point_is_active = False

    def _ensure_manual_pressure_combination(self, line, default_enabled=False):
        """Ensure the one supported pressure input exists for a line."""
        name = ('manual', line, 'manual')
        created = name not in self._new_load_comb_dict
        if created:
            self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
            self._new_load_comb_dict[name][0].set(0)
            self._new_load_comb_dict[name][1].set(1 if default_enabled else 0)
            self._new_load_comb_dict[name][2].set(1 if default_enabled else 0)
            self._new_load_comb_dict[name][0].trace_add('write', self.trace_acceptance_change)
            self._new_load_comb_dict[name][1].trace_add('write', self.trace_acceptance_change)
        elif default_enabled:
            self._new_load_comb_dict[name][1].set(1)
            self._new_load_comb_dict[name][2].set(1)
        return name

    def _sync_single_line_structure_from_inputs(self):
        """Build or update the selected hidden line from the visible property entries."""
        if not getattr(self, '_simplified_calculation_mode', False):
            return
        if not self._line_is_active:
            return
        if self._structure_input_is_missing():
            return

        resolved = self._resolve_new_structure_properties()
        self._apply_resolved_new_structure(resolved)
        project_services.mark_line_for_recalculation(self._line_to_struc, self._active_line)

    def _sync_simplified_domain_selection(self):
        """Apply a calculation-domain change immediately in simplified mode."""
        if not getattr(self, '_simplified_calculation_mode', False):
            return

        self._ensure_single_dummy_line()
        self._select_single_calculation_line()
        self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)
        self._sync_single_line_structure_from_inputs()
        self._new_show_prop_3d.set(True)
        self.update_frame(force_recalc=True)
        self.gui_load_combinations(self._combination_slider.get())

    def _prepare_simplified_optimizer_replacement(self):
        """Ensure optimizer return values replace the hidden single calculation line."""
        if not getattr(self, '_simplified_calculation_mode', False):
            return False

        self._ensure_single_dummy_line()
        self._select_single_calculation_line()
        self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)
        return True

    def _refresh_simplified_optimizer_replacement(self):
        """Refresh the single-line GUI after optimizer results were returned."""
        if not getattr(self, '_simplified_calculation_mode', False):
            return False

        self._select_single_calculation_line()
        self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)
        self._apply_simplified_calculation_layout()
        self._new_show_prop_3d.set(True)
        self.set_selected_variables(self._active_line)
        self.update_frame(force_recalc=True)
        self.gui_load_combinations(self._combination_slider.get())
        return True

    def gui_structural_properties(self, flat_panel_stf_girder=False, flat_unstf=False, flat_stf=True,
                                  shell=False, long_stf=False, ring_stf=False,
                                  ring_frame=False, force_input=False, stress_input=False, conical=False):
        vert_start = 0.04
        hor_start = 0.02

        width = max(self._parent.winfo_width(), 1)

        if width < 1350:
            delta_y = 0.028
            delta_x = 0.12
        else:
            delta_y = 0.024
            delta_x = 0.13

        ent_relx = hor_start + 6 * delta_x

        geo_ent_width = 0.1
        ent_geo_y = 0.1

        opt_width = 0.2

        self._unit_informations_dimensions = list()
        if any([flat_unstf, flat_stf, flat_panel_stf_girder]):

            '''
                    self._flat_gui_headlines = [ttk.Label(self._tab_prop, text='Plate input'),
                                    ttk.Label(self._tab_prop, text='Stiffener'),
                                    ttk.Label(self._tab_prop, text='Girder'),
                                    ttk.Label(self._tab_prop, text='Load/stresses input'),
                                    ttk.Label(self._tab_prop, text='Special provitions input'),
                                    ttk.Label(self._tab_prop, text='Buckling input')]
            '''
            # Top buttons
            top_button_shift = 0.2
            self._stf_button.place(relx=hor_start, rely=vert_start + top_button_shift * delta_y)
            self._stress_button.place(relx=hor_start + delta_x * 1.5, rely=vert_start + top_button_shift * delta_y)
            self._fls_button.place(relx=hor_start + delta_x * 3, rely=vert_start + top_button_shift * delta_y)
            self.add_stucture.place(relx=hor_start + delta_x * 4.5, rely=vert_start + top_button_shift * delta_y,
                                    relheight=0.065, relwidth=0.39)

            # Input fields
            if any([shell, long_stf, ring_stf, ring_frame, force_input, stress_input]):
                return

            self._flat_gui_headlines[0].place(relx=hor_start, rely=vert_start + 3 * delta_y)

            idx = 4
            for pl_lab, pl_ent in zip(self._flat_gui_lab_plate, self._flat_gui_plate):
                pl_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                pl_ent.place(relx=hor_start + 3 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1

            for stf_lab, stf_ent, girder_ent in zip(self._flat_gui_lab_stf, self._flat_gui_stf, self._flat_gui_girder):
                if flat_panel_stf_girder:
                    girder_ent.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                if flat_stf:
                    stf_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                    stf_ent.place(relx=hor_start + 3 * delta_x, rely=vert_start + idx * delta_y)
                    idx += 1

            self._flat_gui_headlines[3].place(relx=hor_start + 0 * delta_x, rely=vert_start + idx * delta_y)
            idx += 1
            this_count = 1
            for load_lab, load_ent in zip(self._flat_gui_lab_loads, self._flat_gui_loads):
                load_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                load_ent.place(relx=hor_start + 3 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1
                this_count += 1
            idx_now = idx
            idx -= this_count
            self._flat_gui_headlines[4].place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
            idx += 1
            for prov_lab, prov_ent in zip(self._flat_gui_lab_os_c101_provisions, self._flat_gui_os_c101_provisions):
                prov_lab.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                prov_ent.place(relx=hor_start + 6.5 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1
            self._flat_btn_load_info.place(relx=hor_start + 5 * delta_x,
                                           rely=vert_start + (idx + 1) * delta_y)
            self._flat_btn_fixation_info.place(relx=hor_start + 6 * delta_x,
                                               rely=vert_start + (idx - 7.5) * delta_y)
            self._button_str_type.place(relx=hor_start + 5 * delta_x,
                                        rely=vert_start + (idx + 3) * delta_y)
            idx = idx_now
            self._flat_gui_headlines[5].place(relx=hor_start + 0 * delta_x, rely=vert_start + idx * delta_y)
            idx += 1
            self._lab_buckling_method.place(relx=hor_start + 0 * delta_x, rely=vert_start + idx * delta_y)
            self._buckling_method.place(relx=hor_start + 4 * delta_x, rely=vert_start + idx * delta_y * 0.99)
            idx += 1
            if flat_panel_stf_girder:
                self._flat_gui_headlines[7].place(relx=hor_start + 6 * delta_x, rely=vert_start + idx * delta_y)
            if flat_stf:
                self._flat_gui_headlines[6].place(relx=hor_start + 4 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1

            for buckling_lab, buckling_stf_ent, buckling_girder_ent in zip(self._flat_gui_buc_lab_stf_girder,
                                                                           self._flat_gui_buc_stf_opt,
                                                                           self._flat_gui_buc_girder_opt):
                if flat_panel_stf_girder:
                    buckling_girder_ent.place(relx=hor_start + 6 * delta_x, rely=vert_start + idx * delta_y)
                if flat_stf:
                    buckling_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                    buckling_stf_ent.place(relx=hor_start + 4 * delta_x, rely=vert_start + idx * delta_y)
                    idx += 1

            if flat_panel_stf_girder:
                self._flat_gui_girder_moment_factor[0].place(relx=hor_start + 0 * delta_x,
                                                             rely=vert_start + idx * delta_y)
                self._flat_gui_girder_moment_factor[1].place(relx=hor_start + 6 * delta_x,
                                                             rely=vert_start + idx * delta_y,
                                                             relwidth=0.08)
                self._flat_gui_girder_moment_factor[2].place(relx=hor_start + 7 * delta_x,
                                                             rely=vert_start + idx * delta_y,
                                                             relwidth=0.08)
                idx += 1

            for buckling_lab, buckling_ent in zip(self._flat_gui_buc_lab_common, self._flat_gui_buc_common_opt):
                buckling_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                buckling_ent.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1
            for buckling_lab, buckling_ent in zip(self._flat_gui_lab_buckling, self._flat_gui_buckling):
                buckling_lab.place_forget()
                buckling_ent.place_forget()

            if self._new_buckling_method.get() in ['ML-Numeric (PULS based)', 'SemiAnalytical S3/U3']:
                for buckling_lab, buckling_ent in zip(self._flat_gui_lab_buckling[:2],
                                                      self._flat_gui_buckling[:2]):
                    buckling_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                    buckling_ent.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                    idx += 1
                if self._new_puls_sp_or_up.get() == 'UP':
                    self._lab_puls_up_supp.place(relx=hor_start, rely=vert_start + idx * delta_y)
                    self._ent_puls_up_boundary.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                    idx += 1

            # optimize buttons

            for dom in ['Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder',
                        'cylinder']:
                for btn, placement in zip(self._optimization_buttons[dom],
                                          self._optimization_buttons[dom + ' place']):
                    btn.place_forget()

            for btn, placement in zip(self._optimization_buttons[self._new_calculation_domain.get()],
                                      self._optimization_buttons[self._new_calculation_domain.get() + ' place']):
                btn.place(relx=placement[0], rely=placement[1], relheight=placement[2], relwidth=placement[3])

        if shell:
            '''
            self._shell_gui_items = [self._lab_shell, self._ent_shell_plate_thk, self._ent_shell_radius,
                                     self._ent_shell_dist_rings,
                                     self._ent_shell_length,self._ent_shell_tot_length,self._ent_shell_k_factor]
            '''

            self._lab_shell.place(relx=hor_start, rely=ent_geo_y + delta_y)

            tmp_unit_info = list()
            shell_labels = ['Shell plate thickness', 'Cone radius r1', 'Cone radius r2', 'Cone length, l',
                            'Effective buckling length factor, k', 'Material factor'] if conical else \
                ['Shell plate thickness', 'Shell radius (middle of plate)', 'Distance between rings, l',
                 'Length of shell, L', 'Total cylinder length, Lc', 'Effective buckling length factor, k',
                 'Material factor']
            shell_items = self._shell_conical_gui_items if conical else self._shell_gui_items
            for lab in shell_labels:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):
                lab.place(relx=hor_start, rely=ent_geo_y + delta_y * (2 + idx))
                self._unit_informations_dimensions.append(lab)

            for idx, entry in enumerate(shell_items[1:]):
                entry.place(relx=hor_start + 5 * delta_x, rely=ent_geo_y + delta_y * (2 + idx), relwidth=geo_ent_width)

            self._shell_btn_length_info.place(relx=hor_start + 6 * delta_x, rely=ent_geo_y + delta_y * (idx))

            ent_geo_y += delta_y * (len(shell_items[1:]) + 1)

        if long_stf:

            self._lab_shell_long_stiffener.place(relx=hor_start, rely=ent_geo_y + delta_y)

            tmp_unit_info = list()
            for lab in ['Web, hw', 'Web, tw', 'Flange b', 'Flange, tf', 'Spacing, s', 'Stf. type', 'Load section']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):
                lab.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 2)
                self._unit_informations_dimensions.append(lab)

            for idx, entry in enumerate(self._shell_long_stf_gui_items[1:]):
                entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 3, relwidth=geo_ent_width)

            self._unit_informations_dimensions.append(self._lab_shell_long_stiffener)
            ent_geo_y += delta_y * 3

        if ring_stf:
            self._lab_shell_ring_stiffener.place(relx=hor_start, rely=ent_geo_y + delta_y * 1)
            tmp_unit_info = list()
            for lab in ['Web, hw', 'Web, tw', 'Flange, b', 'Flange, tf', 'tr. br. dist', 'Stf. type',
                        'Exclude', 'Load section prop.']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):

                if idx in [6, 7]:
                    lab.place(relx=hor_start + (idx - 6) * delta_x * 3, rely=ent_geo_y + delta_y * 4)
                else:
                    lab.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 2)
                self._unit_informations_dimensions.append(lab)
            self._unit_informations_dimensions.append(self._lab_shell_ring_stiffener)

            for idx, entry in enumerate(self._shell_ring_stf_gui_items[1:]):
                if idx in [6, 7]:
                    entry.place(relx=hor_start + (idx - 6) * delta_x * 4 + delta_x, rely=ent_geo_y + delta_y * 4,
                                relwidth=geo_ent_width)
                else:
                    entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 3, relwidth=geo_ent_width)

            if self._new_shell_exclude_ring_stf.get():
                self._shell_exclude_ring_stf.place(relx=0.005, rely=ent_geo_y + delta_y * 3.15, relwidth=0.9)
                self._unit_informations_dimensions.append(self._shell_exclude_ring_stf)

            ent_geo_y += delta_y * 4

        if ring_frame:
            self._lab_shell_ring_frame.place(relx=hor_start, rely=ent_geo_y + delta_y * 1)

            for idx, entry in enumerate(self._shell_ring_frame_gui_items[1:]):
                if idx in [7, 8]:
                    entry.place(relx=hor_start + (idx - 7) * delta_x * 4 + delta_x, rely=ent_geo_y + delta_y * 4,
                                relwidth=geo_ent_width)
                else:
                    entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 3, relwidth=geo_ent_width)

            tmp_unit_info = list()
            for lab in ['Web, hw', 'Web, tw', 'Flange, b', 'Flange, tf', 'tr. br. dist', 'Lh bet. Gird.',
                        'Stf. type', 'Exclude', 'Load section prop.']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):
                if idx in [7, 8]:
                    lab.place(relx=hor_start + (idx - 7) * delta_x * 3, rely=ent_geo_y + delta_y * 4)
                else:
                    lab.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 2)

                self._unit_informations_dimensions.append(lab)
            self._unit_informations_dimensions.append(self._lab_shell_ring_frame)
            if self._new_shell_exclude_ring_frame.get():
                self._shell_exclude_ring_frame.place(relx=0.005, rely=ent_geo_y + delta_y * 3.15, relwidth=0.9)
                self._unit_informations_dimensions.append(self._shell_exclude_ring_frame)

            ent_geo_y += delta_y * 3

        if not any([flat_panel_stf_girder, flat_stf, flat_unstf]):
            # Other data
            '''
                self._shell_other_gui_items = [self._ent_shell_end_cap_pressure_included, self._ent_shell_uls_or_als,
                                   self._ent_shell_fab_ring_stf, self._ent_shell_fab_ring_frame]
            '''

            self._lab_shell_limit_state.place(relx=hor_start,
                                              rely=ent_geo_y + delta_y * 2.2)
            self._ent_shell_uls_or_als.place(relx=hor_start + 1.6 * delta_x,
                                             rely=ent_geo_y + delta_y * 2.2,
                                             relwidth=geo_ent_width * 2)

            # Load data
            ent_geo_y += 3.3 * delta_y
            # self._lab_shell_loads.place(relx=hor_start, rely=ent_geo_y - delta_y*1.5)
            self._ent_shell_stress_input.place(relx=hor_start, rely=ent_geo_y)
            if 'shell' in self._new_calculation_domain.get():
                self._ent_shell_force_input.place(relx=hor_start + 2 * delta_x, rely=ent_geo_y)
            else:
                self._new_shell_stress_or_force.set(2)

            lab_force = ['Axial', 'Bending M1', 'Bending M2', 'Torsional', 'Shear Q1', 'Shear Q2', 'Lateral'] \
                if conical else ['Axial', 'Bending', 'Torsional', 'Shear', 'Lateral']
            lab_force_unit = ['kN', 'kNm', 'kNm', 'kNm', 'kN', 'kN', 'N/mm2'] if conical else \
                ['kN', 'kNm', 'kNm', 'kN', 'N/mm2']
            lab_stress = ['Axial', 'Bending', 'Torsional', 'Shear',
                          'Lateral', 'Add hoop']
            lab_stress_unit = ['N/mm2', 'N/mm2', 'N/mm2', 'N/mm2', 'N/mm2', 'N/mm2']
            to_use = self._shell_loads_conical_forces_gui_items if conical and self._new_shell_stress_or_force.get() == 1 \
                else self._shell_loads_forces_gui_items if self._new_shell_stress_or_force.get() == 1 \
                    else self._shell_loads_stress_gui_items

            lab_to_use = [lab_force, lab_force_unit] if self._new_shell_stress_or_force.get() == 1 \
                else [lab_stress, lab_stress_unit]

            tmp_unit_info = list()
            tmp_unit_info_unit = list()
            [tmp_unit_info.append(ttk.Label(self._tab_prop, text=val))
             for val in lab_to_use[0]]
            [tmp_unit_info_unit.append(ttk.Label(self._tab_prop, text=val))
             for val in lab_to_use[1]]

            for idx, lab in enumerate(tmp_unit_info):
                lab.place(relx=hor_start, rely=ent_geo_y + (idx + 1) * delta_y)
                self._unit_informations_dimensions.append(lab)

            for idx, entry in enumerate(to_use):
                entry.place(relx=hor_start + 1.5 * delta_x,
                            rely=ent_geo_y + (idx + 1) * delta_y, relwidth=geo_ent_width)

            for idx, lab in enumerate(tmp_unit_info_unit):
                lab.place(relx=hor_start + 2.5 * delta_x,
                          rely=ent_geo_y + (idx + 1) * delta_y)
                self._unit_informations_dimensions.append(lab)

            self._shell_btn_load_info.place(relx=hor_start + 5 * delta_x,
                                            rely=ent_geo_y + 1 * delta_y)

            # Various
            end_y = ent_geo_y + (idx + 1) * delta_y
            other_count = 1

            self._lab_material_library.place(relx=hor_start,
                                             rely=end_y + delta_y * other_count)
            self._material_picker.place(relx=hor_start + 4 * delta_x,
                                        rely=end_y + delta_y * other_count,
                                        relwidth=geo_ent_width * 3)
            other_count += 1

            self._lab_yield.place(relx=hor_start,
                                  rely=end_y + delta_y * other_count)
            self._ent_shell_yield.place(relx=hor_start + 4 * delta_x,
                                        rely=end_y + delta_y * other_count, relwidth=geo_ent_width)
            other_count += 1

            if ring_stf:
                self._lab_shell_fab_stf.place(relx=hor_start,
                                              rely=end_y + delta_y * other_count)
                self._ent_shell_fab_ring_stf.place(relx=hor_start + 4 * delta_x,
                                                   rely=end_y + delta_y * other_count)
                other_count += 1

            if ring_frame:
                self._lab_shell_fab_frame.place(relx=hor_start, rely=end_y + delta_y * other_count)
                self._ent_shell_fab_ring_frame.place(relx=hor_start + 4 * delta_x,
                                                     rely=end_y + delta_y * other_count, relwidth=geo_ent_width * 1.9)
                other_count += 1

            if api_helpers.geometry_id_for_domain(self._new_calculation_domain.get()) in [1, 5]:
                self._lab_shell_en_cap_pressure.place(relx=hor_start,
                                                      rely=end_y + delta_y * other_count)
                self._ent_shell_end_cap_pressure_included.place(relx=3 * delta_x,
                                                                rely=end_y + delta_y * other_count)
                other_count += 1

            # Removing flat stuff

            for dom in ['Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder',
                        'cylinder']:
                for btn, placement in zip(self._optimization_buttons[dom],
                                          self._optimization_buttons[dom + ' place']):
                    btn.place_forget()

            if not any([ring_stf, ring_frame]):  # TODO optmizing not implemented yet for ring stf and frame.
                for btn, placement in zip(self._optimization_buttons['cylinder'],
                                          self._optimization_buttons['cylinder' + ' place']):
                    btn.place(relx=placement[0], rely=placement[1], relheight=placement[2], relwidth=placement[3])

    def calculation_domain_selected(self, event=None, sync_cylinder_inputs=True):
        '''
        ['Stiffened panel, flat', 'Unstiffened shell (Force input)', 'Unstiffened panel (Stress input)',
        'Longitudinal Stiffened shell (Force input)', 'Longitudinal Stiffened panel (Stress input)',
        'Ring Stiffened shell (Force input)', 'Ring Stiffened panel (Stress input)',
        'Orthogonally Stiffened shell (Force input)', 'Orthogonally Stiffened panel (Stress input)']
        '''

        to_process = [self._lab_buckling_method,
                      self._buckling_method, self._lab_yield,
                      self._lab_mat_fac, self._structure_types_label, self._button_str_type, self._ent_structure_type,
                      self._lab_structure_type, self._lab_kpp, self._lab_kps, self._lab_km1, self._lab_km2,
                      self._lab_stf_type, self._lab_press_side, self._ent_pressure_side,
                      self._lab_puls_input, self._lab_puls_up_supp, self._lab_puls_acceptance,
                      self._lab_puls_int_gt, self._lab_puls_cont_sniped, self._lab_span, self._lab_s,
                      self._ent_puls_sp_or_up, self._ent_puls_method, self._ent_puls_panel_boundary,
                      self._ent_puls_stf_end_type,
                      self._stf_button, self._stress_button, self._fls_button, self._shell_btn_load_info,
                      self._flat_btn_load_info, self._shell_btn_length_info, self._button_str_type,
                      self._flat_btn_fixation_info]

        to_process = to_process + self._shell_gui_items + self._shell_conical_gui_items + \
                     self._shell_long_stf_gui_items + self._shell_ring_stf_gui_items + \
                     self._shell_ring_frame_gui_items + self._shell_loads_other_gui_items + \
                     self._shell_loads_forces_gui_items + self._shell_loads_conical_forces_gui_items + \
                     self._shell_loads_stress_gui_items + \
                     self._unit_informations_dimensions + self._shell_other_gui_items + self._flat_gui_plate + \
                     self._flat_gui_lab_plate + self._flat_gui_lab_stf + self._flat_gui_stf + self._flat_gui_girder + \
                     self._flat_gui_lab_loads + self._flat_gui_loads + self._flat_gui_lab_os_c101_provisions + \
                     self._flat_gui_os_c101_provisions + \
                     self._flat_gui_lab_buckling + self._flat_gui_buckling + self._flat_gui_headlines + \
                     self._flat_gui_buc_lab_common + self._flat_gui_buc_common_opt + self._flat_gui_buc_girder_opt + \
                     self._flat_gui_buc_lab_stf_girder + self._flat_gui_buc_stf_opt + self._flat_gui_girder_moment_factor
        for item in to_process:
            item.place_forget()

        if event is not None:
            self._new_shell_exclude_ring_stf.set(False)
            self._new_shell_exclude_ring_frame.set(False)
        '''
            geomeries = {1:'Unstiffened shell (Force input)',
                    2:'Unstiffened panel (Stress input)',
                    3:'Longitudinal Stiffened shell (Force input)',
                    4:'Longitudinal Stiffened panel (Stress input)',
                    5:'Ring Stiffened shell (Force input)',
                    6:'Ring Stiffened panel (Stress input)',
                    7:'Orthogonally Stiffened shell (Force input)',
                    8:'Orthogonally Stiffened panel (Stress input)'}
        '''

        if self._new_calculation_domain.get() == 'Flat plate, unstiffened':
            self._new_puls_sp_or_up.set('UP')
            self.gui_structural_properties(flat_unstf=True, flat_stf=False)

        elif self._new_calculation_domain.get() == 'Flat plate, stiffened':
            self._new_puls_sp_or_up.set('SP')
            self.gui_structural_properties(flat_stf=True)

        elif self._new_calculation_domain.get() == 'Flat plate, stiffened with girder':
            self._new_puls_sp_or_up.set('SP')
            self.gui_structural_properties(flat_panel_stf_girder=True, flat_stf=True)

        elif self._new_calculation_domain.get() in ['Unstiffened shell (Force input)',
                                                    'Unstiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf=False, flat_panel_stf_girder=False,
                                           shell=True, long_stf=False, ring_stf=False, ring_frame=False)
        elif self._new_calculation_domain.get() == 'Unstiffened conical shell (Force input)':
            self.gui_structural_properties(flat_unstf=False, flat_stf=False, flat_panel_stf_girder=False,
                                           shell=True, long_stf=False, ring_stf=False, ring_frame=False,
                                           conical=True)
        elif self._new_calculation_domain.get() in ['Longitudinal Stiffened shell (Force input)',
                                                    'Longitudinal Stiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf=False, flat_panel_stf_girder=False,
                                           shell=True, long_stf=True, ring_stf=False, ring_frame=False)
        elif self._new_calculation_domain.get() in ['Ring Stiffened shell (Force input)',
                                                    'Ring Stiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf=False, flat_panel_stf_girder=False,
                                           shell=True, long_stf=False, ring_stf=True, ring_frame=True)
        elif self._new_calculation_domain.get() in ['Orthogonally Stiffened shell (Force input)',
                                                    'Orthogonally Stiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf=False, flat_panel_stf_girder=False,
                                           shell=True, long_stf=True, ring_stf=True, ring_frame=True)

        if self._line_is_active and self._active_line in self._line_to_struc.keys():
            if sync_cylinder_inputs and event == None and self._line_to_struc[self._active_line][5] is not None:
                struc_obj = self._line_to_struc[self._active_line][5]
                if struc_obj.geometry == 9:
                    cone_r1 = self._new_shell_cone_r1.get()
                    cone_r2 = self._new_shell_cone_r2.get()
                    cone_length = self._new_shell_cone_length.get()
                    cone_alpha = math.degrees(math.atan(abs(cone_r2 - cone_r1) / cone_length)) \
                        if cone_length else 0
                    conical_converter_kwargs = dict(
                        geometry=struc_obj.geometry,
                        shell_t=self._new_shell_thk.get(),
                        shell_radius=min(cone_r1, cone_r2),
                        shell_spacing=cone_length,
                        hw=self._new_stf_web_h.get(),
                        tw=self._new_stf_web_t.get(),
                        b=self._new_stf_fl_w.get(),
                        tf=self._new_stf_fl_t.get(),
                        CylinderAndCurvedPlate=CylinderAndCurvedPlate,
                        conical=True,
                        psd=self._new_shell_psd.get(),
                        cone_r1=cone_r1,
                        cone_r2=cone_r2,
                        cone_alpha=cone_alpha,
                        shell_lenght_l=cone_length,
                    )
                    if self._new_shell_stress_or_force.get() == 1:
                        forces = [self._new_shell_Nsd.get(), self._new_shell_Msd.get(),
                                  self._new_shell_M2sd.get(), self._new_shell_Tsd.get(),
                                  self._new_shell_Qsd.get(), self._new_shell_Q2sd.get()]
                        sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                            stresses=None, forces=forces, **conical_converter_kwargs)
                        self._new_shell_sasd.set(_round_calculated(sasd))
                        self._new_shell_smsd.set(_round_calculated(smsd))
                        self._new_shell_tTsd.set(_round_calculated(abs(tTsd)))
                        self._new_shell_tQsd.set(_round_calculated(tQsd))
                        self._new_shell_shsd.set(_round_calculated(shsd))
                    else:
                        stresses = [self._new_shell_sasd.get(), self._new_shell_smsd.get(),
                                    abs(self._new_shell_tTsd.get()), self._new_shell_tQsd.get(),
                                    self._new_shell_shsd.get()]
                        Nsd, M1sd, M2sd, Tsd, Q1sd, Q2sd = hlp.helper_cylinder_stress_to_force_to_stress(
                            stresses=stresses, **conical_converter_kwargs)[:6]
                        self._new_shell_Nsd.set(_round_calculated(Nsd))
                        self._new_shell_Msd.set(_round_calculated(M1sd))
                        self._new_shell_M2sd.set(_round_calculated(M2sd))
                        self._new_shell_Tsd.set(_round_calculated(Tsd))
                        self._new_shell_Qsd.set(_round_calculated(Q1sd))
                        self._new_shell_Q2sd.set(_round_calculated(Q2sd))
                elif self._new_shell_stress_or_force.get() == 1:
                    forces = [self._new_shell_Nsd.get(), self._new_shell_Msd.get(), \
                              self._new_shell_Tsd.get(), self._new_shell_Qsd.get()]
                    sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                        stresses=None, forces=forces, geometry=struc_obj.geometry, shell_t=self._new_shell_thk.get(),
                        shell_radius=self._new_shell_radius.get(), shell_spacing=self._new_stf_spacing.get(),
                        hw=self._new_stf_web_h.get(), tw=self._new_stf_web_t.get(), b=self._new_stf_fl_w.get(),
                        tf=self._new_stf_fl_t.get(), CylinderAndCurvedPlate=CylinderAndCurvedPlate)
                    self._new_shell_sasd.set(_round_calculated(sasd))
                    self._new_shell_smsd.set(_round_calculated(smsd))
                    self._new_shell_tTsd.set(_round_calculated(abs(tTsd)))
                    self._new_shell_tQsd.set(_round_calculated(tQsd))
                    # self._new_shell_shsd.set(0)
                else:
                    stresses = [self._new_shell_sasd.get(), self._new_shell_smsd.get(), abs(self._new_shell_tTsd.get()),
                                self._new_shell_tQsd.get(), self._new_shell_shsd.get()]
                    sasd, smsd, tTsd, tQsd, shsd = stresses
                    Nsd, Msd, Tsd, Qsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                        stresses=stresses, geometry=struc_obj.geometry, shell_t=self._new_shell_thk.get(),
                        shell_radius=self._new_shell_radius.get(), shell_spacing=self._new_stf_spacing.get(),
                        hw=self._new_stf_web_h.get(), tw=self._new_stf_web_t.get(), b=self._new_stf_fl_w.get(),
                        tf=self._new_stf_fl_t.get(), CylinderAndCurvedPlate=CylinderAndCurvedPlate)
                    self._new_shell_Nsd.set(_round_calculated(Nsd))
                    self._new_shell_Msd.set(_round_calculated(Msd))
                    self._new_shell_Tsd.set(_round_calculated(Tsd))
                    self._new_shell_Qsd.set(_round_calculated(Qsd))

        self._current_calculation_domain = self._new_calculation_domain.get()
        self._sync_simplified_domain_selection()
        # Setting the correct optmization buttons

    def stress_information_notebooks(self, info_type='shell'):
        ''' Shows stress information '''
        text_m = tk.Toplevel(self._parent, background=self._general_color)
        # Create the text widget
        text_widget = tk.Text(text_m, height=35, width=100)
        # Create a scrollbar
        scroll_bar = ttk.Scrollbar(text_m)
        # Pack the scroll bar
        # Place it to the right side, using tk.RIGHT
        scroll_bar.pack(side=tk.RIGHT)
        # Pack it into our tkinter application
        # Place the text widget to the left side
        text_widget.pack(side=tk.LEFT)
        if info_type == 'shell':
            long_text = 'Information on stresses:\n' \
                        ' \n' \
                        'Uniform stresses is assumed.\n' \
                        'Shear stresses are set to positive.\n' \
                        'Compression stress is taken as NEGATIVE.\n' \
                        'Lateral pressure is taken as negative when acting toward cylinder center.\n' \
                        'Hoop stresses are negative when applying negative overpressure.\n ' \
                        '   \n'
        elif info_type == 'flat':
            long_text = 'Information on stresses:\n' \
                        ' \n' \
                        'Uniform or linearly varying stresses are assumed.\n' \
                        'The stresses included in the check are axial membrane stresses.\n' \
                        'Shear stresses are set to positive.\n' \
                        'Bending stresses from lateral pressure are accounted for internally and need not be included.\n' \
                        'Compression stress is taken as POSITIVE.\n' \
                        'The membrane axial stress in the transverse direction that is due to girder bending\n' \
                        'needs to be included in the check according to method 1.\n' \
                        'Lateral outer overpressure is taken as positive.\n' \
                        '   \n'
        else:
            long_text = 'Also see the "Help tab".'
        # Insert text into the text widget
        text_widget.insert('current', long_text)

        try:
            if info_type == 'shell':
                img_file_name = 'Cylinder-Load_distribution.png'
            elif info_type == 'flat':
                img_file_name = 'img_axial_stresses.gif'
            elif info_type == 'fixation':
                img_file_name = 'img_fixation_parameters.gif'
            else:
                img_file_name = 'Definition_of_parameters_L_and_LH.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._int_button.config(image=photo)
            self._int_button.image = photo
        except TclError:
            pass
        text_widget.image_create('current', image=photo)

    def trace_buckling_method(self, event=None):
        self.calculation_domain_selected(sync_cylinder_inputs=False)
        self.update_frame(event)

    def trace_puls_up_or_sp(self, event=None):
        if self._new_puls_sp_or_up.get() == 'UP' and \
                self._new_buckling_method.get() in ['ML-Numeric (PULS based)', 'SemiAnalytical S3/U3']:
            vert_start = 0.1
            hor_start = 0.02
            delta_y = 0.04
            delta_x = 0.13
            opt_width = 0.2
            shift_x = delta_x * 4
            lab_place = delta_y * 13

            self._lab_puls_up_supp.place(relx=hor_start, rely=vert_start + lab_place + 2 * delta_y)
            self._ent_puls_up_boundary.place(relx=hor_start + shift_x, rely=vert_start + lab_place + 2 * delta_y,
                                             relwidth=opt_width)
        else:
            self._lab_puls_up_supp.place_forget()
            self._ent_puls_up_boundary.place_forget()

    def resize(self, event=None):
        """
        Responsive GUI scaling.

        The old implementation kept text_scale = 1 and did not call update_frame().
        On small laptop screens, relative widget placement shrinks the available
        widget area while the text remains full size, causing overlap.
        """

        if event is not None and event.widget is not self._parent:
            return

        width = max(self._parent.winfo_width(), 1)
        height = max(self._parent.winfo_height(), 1)

        if (width, height) == self._last_resize_size:
            return

        self._last_resize_size = (width, height)

        # Scale against a comfortable reference layout.
        # Clamp to avoid unreadably small or unnecessarily large fonts.
        scale_w = width / 1600.0
        scale_h = height / 900.0
        self.text_scale = max(0.78, min(1.05, min(scale_w, scale_h)))

        self._text_size = {
            'Text 14 bold': 'Verdana ' + str(max(9, int(14 * self.text_scale))) + ' bold',
            'Text 16 bold': 'Verdana ' + str(max(10, int(16 * self.text_scale))) + ' bold',
            'Text 18 bold': 'Verdana ' + str(max(11, int(18 * self.text_scale))) + ' bold',
            'Text 12 bold': 'Verdana ' + str(max(8, int(12 * self.text_scale))) + ' bold',
            'Text 10 bold': 'Verdana ' + str(max(7, int(10 * self.text_scale))) + ' bold',
            'Text 9 bold': 'Verdana ' + str(max(7, int(9 * self.text_scale))) + ' bold',
            'Text 8 bold': 'Verdana ' + str(max(6, int(8 * self.text_scale))) + ' bold',
            'Text 8': 'Verdana ' + str(max(6, int(8 * self.text_scale))),
            'Text 9': 'Verdana ' + str(max(6, int(9 * self.text_scale))),
            'Text 7': 'Verdana ' + str(max(6, int(7 * self.text_scale))),
            'Text 10': 'Verdana ' + str(max(7, int(10 * self.text_scale))),
            'Text 7 bold': 'Verdana ' + str(max(6, int(7 * self.text_scale))) + ' bold',
            'Text 6 bold': 'Verdana ' + str(max(6, int(6 * self.text_scale))) + ' bold',
        }

        self._apply_responsive_main_layout(width, height)

        # Throttle redraws while user drags/resizes the window.
        if self._resize_after_id is not None:
            self._parent.after_cancel(self._resize_after_id)

        self._resize_after_id = self._parent.after(150, self._finish_resize)

    def _finish_resize(self):
        self._resize_after_id = None

        try:
            self.update_frame()
        except Exception:
            # Avoid crashing during early initialization.
            pass

    def _apply_responsive_main_layout(self, width, height):
        """
        Adjust the major GUI regions for smaller laptop screens.

        The old layout used:
            tab width  = 0.2585
            main canvas start x = 0.26

        That leaves too little room for the input notebook on small screens.
        """

        if width < 1350:
            left_width = 0.34
        elif width < 1600:
            left_width = 0.30
        else:
            left_width = 0.2585

        x_canvas_place = left_width + 0.005
        remaining_width = 1.0 - x_canvas_place

        self._tabControl.place(relwidth=left_width, relheight=1)

        self._main_canvas.place(
            relx=x_canvas_place,
            rely=0,
            relwidth=remaining_width * 0.70,
            relheight=0.73,
        )

        self._prop_canvas.place(
            relx=x_canvas_place,
            rely=0.73,
            relwidth=remaining_width * 0.52,
            relheight=0.27,
        )

        self._result_canvas.place(
            relx=x_canvas_place + remaining_width * 0.52,
            rely=0.73,
            relwidth=remaining_width * 0.48,
            relheight=0.27,
        )

    def toggle_select_multiple(self, event=None):
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg='#E1E1E1')
            self._multiselect_lines = []
            self._toggle_btn.config(text='Toggle select\n'
                                         'multiple')
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg=self._general_color)
            self._toggle_btn.config(text='select lines')
        self.update_frame()

    def toggle_set_variable(self):
        if self._toggle_btn.config('relief')[-1] == "raised":
            tk.messagebox.showerror('Toggle select not chosen.', 'Toggle select button not pressed.\n'
                                                                 'To change a parameter select a variable, \n'
                                                                 'set the value you want to change and \n'
                                                                 'press Change multi. param.')
            return

        var_to_set = self._new_toggle_var.get()
        if var_to_set == '':
            tk.messagebox.showerror('Select variable', 'Select a variable to change\n'
                                                       'in the drop down menu.')
            return
        # if not self._line_is_active:
        #     tk.messagebox.showerror('Select line', 'Click a line first.')
        obj_dict = {'mat_yield': self._new_material.get,
                    'mat_factor': self._new_material_factor.get,
                    'span': self._new_field_len.get,
                    'spacing': self._new_stf_spacing.get,
                    'plate_thk': self._new_plate_thk.get,
                    'stf_web_height': self._new_stf_web_h.get,
                    'stf_web_thk': self._new_stf_web_t.get,
                    'stf_flange_width': self._new_stf_fl_w.get,
                    'stf_flange_thk': self._new_stf_fl_t.get,
                    'structure_type': self._new_stucture_type.get,
                    'stf_type': self._new_stf_type.get,
                    'sigma_y1': self._new_sigma_y1.get,
                    'sigma_y2': self._new_sigma_y2.get,
                    'sigma_x1': self._new_sigma_x1.get,
                    'sigma_x2': self._new_sigma_x2.get,
                    'tau_xy': self._new_tauxy.get,
                    'plate_kpp': self._new_plate_kpp,
                    'stf_kps': self._new_stf_kps.get,
                    'stf_km1': self._new_stf_km1.get,
                    'stf_km2': self._new_stf_km2.get,
                    'stf_km3': self._new_stf_km3.get,
                    'press_side': self._new_pressure_side.get,
                    # 'structure_types': self._structure_types,
                    'zstar_optimization': self._new_zstar_optimization.get,
                    'puls buckling method': self._new_puls_method.get,
                    'puls boundary': self._new_puls_panel_boundary.get,
                    'puls stiffener end': self._new_buckling_stf_end_support.get,
                    'puls sp or up': self._new_puls_sp_or_up.get,
                    'puls up boundary': self._new_puls_up_boundary.get}

        set_var = obj_dict[var_to_set]()
        if var_to_set == 'mat_yield':
            set_var = set_var * 1e6
        elif var_to_set in ['spacing', 'plate_thk', 'stf_web_height', 'stf_web_thk',
                            'stf_flange_width', 'stf_flange_thk', 'span']:
            set_var = set_var / 1000
        no_of_lines = len(self._multiselect_lines)
        for idx, line in enumerate(self._multiselect_lines):
            self._active_line = line
            self._line_is_active = True
            if self._active_line in self._line_to_struc.keys():
                # if self._active_line[self._active_line][0].Stiffener is not None:
                #     dict = self._line_to_struc[self._active_line][0].Stiffener.get_structure_prop()
                # else:
                #     dict = self._line_to_struc[self._active_line][0].Plate.get_structure_prop()
                prop_dict = self._line_to_struc[self._active_line][0].get_main_properties()

                prop_dict['Plate'][var_to_set][0] = set_var
                prop_dict['Stiffener'][var_to_set][0] = set_var

                # dict[var_to_set][0] = set_var
                self.new_structure(toggle_multi=prop_dict, suspend_recalc=True if (idx + 1) != no_of_lines else False)

    def _gui_single_line_manual_pressure(self):
        """Draw the simplified manual-pressure-only load controls."""
        if not all([self._line_is_active, self._active_line in self._line_to_struc.keys()]):
            return

        lc_x, lc_x_delta, lc_y, lc_y_delta = 0.791666667, 0.026041667, 0.287037037, 0.023148148
        [[item.destroy() for item in items] for items in
         [self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created]]
        self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created = [], [], [], []

        if self._line_to_struc[self._active_line][5] is not None:
            for item in [self._result_label_dnva, self._result_label_dnvb, self._result_label_tanktest,
                         self._result_label_manual, self._lab_pressure]:
                item.place_forget()
            return

        name = self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)
        self._manual_created.append(ttk.Label(self._main_fr, text='Manual pressure [Pa]',
                                              font=self._text_size['Text 8 bold']))
        self._manual_created.append(ttk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][0],
                                              width=15))
        self._manual_created[0].place(relx=lc_x, rely=lc_y)
        self._manual_created[1].place(relx=lc_x + 4 * lc_x_delta, rely=lc_y)

        try:
            results = self.calculate_all_load_combinations_for_line(self._active_line)
            self._result_label_manual.config(text='Manual [Pa]: ' + str(results['manual']),
                                             font=self._text_size['Text 8'])
        except Exception:
            self._result_label_manual.config(text='Manual [Pa]: -', font=self._text_size['Text 8'])

        for item in [self._result_label_dnva, self._result_label_dnvb, self._result_label_tanktest]:
            item.place_forget()

        self._lab_pressure.config(text='Pressure for the single calculation line:')
        self._lab_pressure.place(relx=0.786458333, rely=self.results_gui_start)
        self._result_label_manual.place(relx=lc_x, rely=self.results_gui_start + 0.06)

    def _gui_fea_buckling_options(self):
        """Draw FEA-result buckling controls without pressure input widgets."""
        [[item.destroy() for item in items] for items in
         [self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created]]
        self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created = [], [], [], []
        self._clear_fea_buckling_option_widgets()
        for item in [self._result_label_dnva, self._result_label_dnvb, self._result_label_tanktest,
                     self._result_label_manual, self._lab_pressure]:
            try:
                item.place_forget()
            except Exception:
                pass

        session = self._fea_buckling_session
        panel_count = 0 if session is None else session.panel_count
        selected = self._fea_selected_panel_id or '-'
        selected_panel = None
        if session is not None and self._fea_selected_panel_id is not None:
            try:
                selected_panel = session.panel(self._fea_selected_panel_id)
            except KeyError:
                selected_panel = None
        uf_text = '-' if selected_panel is None or selected_panel.usage_factor is None else f'{selected_panel.usage_factor:.3g}'
        source_text = 'No FE file loaded' if session is None else os.path.basename(session.inp_path)
        line_text = '-'
        domain_text = '-'
        stress_text = '-'
        geometry_text = '-'
        if selected_panel is not None:
            line_text = getattr(self, '_fea_panel_line_by_field', {}).get(selected_panel.field_id, '-')
            try:
                domain_text = str(selected_panel.anystructure_input.get('calculation_domain', '-'))
            except Exception:
                domain_text = '-'
            if getattr(selected_panel, 'stress', None) is not None:
                stress = selected_panel.stress
                if hasattr(stress, 'sigma_x1_mpa'):
                    stress_text = (
                        f"sx {stress.sigma_x1_mpa:.2f}/{stress.sigma_x2_mpa:.2f} MPa, "
                        f"sy {stress.sigma_y1_mpa:.2f}/{stress.sigma_y2_mpa:.2f} MPa, "
                        f"tau {stress.tau_xy_mpa:.2f} MPa"
                    )
                else:
                    stress_text = (
                        f"axial {stress.axial_stress_mpa:.2f} MPa, "
                        f"hoop {stress.hoop_stress_mpa:.2f} MPa, "
                        f"tau {stress.torsional_shear_mpa:.2f} MPa"
                    )
            try:
                geometry_text = (
                    f"L {selected_panel.field.span_m:.3g} m, "
                    f"s {selected_panel.field.spacing_m:.3g} m, "
                    f"t {(selected_panel.field.shell_section_thickness_m or 0.0) * 1000.0:.3g} mm"
                )
            except Exception:
                geometry_text = '-'
        warning_text = ''
        if session is not None:
            warning_text = '\n'.join(
                str(item).replace('WARNING: ', '')
                for item in getattr(session, 'diagnostics', ())
                if str(item).startswith('WARNING:')
            )

        panel_frame = tk.Frame(self._main_fr, background=self._style.lookup('TFrame', 'background'), bd=0)
        panel_frame.place(relx=0.785, rely=0.0, relwidth=0.215, relheight=1.0)
        self._fea_right_panel_frame = panel_frame
        panel_frame.columnconfigure(0, weight=1)
        panel_frame.columnconfigure(1, weight=1)
        panel_frame.columnconfigure(2, weight=1)

        rows = [panel_frame]
        row = 0

        def add_label(text, *, bold=False, column=0, columnspan=3, pady=(0, 2), wrap=260, foreground=None):
            label = ttk.Label(
                panel_frame,
                text=text,
                font=self._text_size['Text 8 bold'] if bold else self._text_size['Text 8'],
                wraplength=wrap,
                justify=tk.LEFT,
                foreground=foreground,
            )
            nonlocal row
            label.grid(row=row, column=column, columnspan=columnspan, sticky='w', padx=12, pady=pady)
            row += 1
            return label

        def add_separator(pady=(8, 7)):
            separator = ttk.Separator(panel_frame, orient='horizontal')
            nonlocal row
            separator.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=pady)
            row += 1
            return separator

        add_label('FEA Result Buckling', bold=True, pady=(12, 2))
        add_label('Panels are imported as separate calculation lines; click a 3D panel to select one.', wrap=285)
        button_row = ttk.Frame(panel_frame)
        button_row.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(6, 4))
        row += 1
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text='Import INP/FRD', command=self.open_fea_buckling_files).grid(
            row=0, column=0, sticky='ew', padx=(0, 4)
        )
        ttk.Button(button_row, text='Reimport', command=self.reimport_fea_buckling_files).grid(
            row=0, column=1, sticky='ew', padx=(4, 0)
        )
        rows.append(button_row)

        session = self._fea_buckling_session
        if session and getattr(session, 'load_cases', ()):
            if len(session.load_cases) > 1:
                add_separator()
                add_label('Load Case', bold=True)
                
                def _lc_label(lc: int) -> str:
                    name = session.load_case_names.get(lc)
                    return f"{lc} - {name}" if name else str(lc)
                    
                self._fea_load_case_combobox = ttk.Combobox(
                    panel_frame,
                    values=[_lc_label(lc) for lc in session.load_cases],
                    state="readonly",
                )
                if getattr(self, '_fea_selected_load_case', None) is not None and getattr(self, '_fea_selected_load_case', None) in session.load_cases:
                    self._fea_load_case_combobox.set(_lc_label(self._fea_selected_load_case))
                else:
                    active = session.active_load_case if session.active_load_case is not None else session.load_cases[0]
                    self._fea_load_case_combobox.set(_lc_label(active))
                self._fea_load_case_combobox.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 6))
                self._fea_load_case_combobox.bind("<<ComboboxSelected>>", self._on_fea_load_case_changed)
                rows.append(self._fea_load_case_combobox)
                row += 1

        add_separator()
        add_label('Analysis', bold=True)
        add_label('Buckling method')
        method = ttk.OptionMenu(
            panel_frame,
            self._new_buckling_method,
            self._new_buckling_method.get(),
            'DNV-RP-C201 - prescriptive',
            'SemiAnalytical S3/U3',
            'ML-Numeric (PULS based)',
            command=self._on_fea_buckling_option_changed,
        )
        method.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 6))
        row += 1
        rows.append(method)

        add_label('UF basis')
        basis = ttk.OptionMenu(
            panel_frame,
            self._new_puls_method,
            self._new_puls_method.get(),
            'ultimate',
            'buckling',
            command=self._on_fea_buckling_option_changed,
        )
        basis.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 6))
        row += 1
        rows.append(basis)

        add_label('UF colour range')
        uf_range_frame = tk.Frame(panel_frame, background=self._style.lookup('TFrame', 'background'), bd=0)
        uf_range_frame.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 6))
        row += 1
        uf_range_frame.columnconfigure(0, weight=3)
        uf_range_frame.columnconfigure(1, weight=1)
        uf_range_frame.columnconfigure(2, weight=3)

        uf_lower_entry = ttk.Entry(uf_range_frame, textvariable=self._fea_uf_color_lower, width=8)
        uf_upper_entry = ttk.Entry(uf_range_frame, textvariable=self._fea_uf_color_upper, width=8)
        uf_lower_entry.grid(row=0, column=0, sticky='ew', padx=(0, 4))
        ttk.Label(uf_range_frame, text='to', font=self._text_size['Text 8']).grid(row=0, column=1)
        uf_upper_entry.grid(row=0, column=2, sticky='ew', padx=(4, 0))

        update_button = ttk.Button(
            panel_frame,
            text='Update colour scale',
            command=lambda: self._refresh_fea_buckling_views(rebuild_3d=True),
        )
        update_button.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 4))
        row += 1
        rows.extend([uf_range_frame, uf_lower_entry, uf_upper_entry, update_button])

        add_label('3D view')
        checkbox_frame = tk.Frame(panel_frame, background=self._style.lookup('TFrame', 'background'), bd=0)
        checkbox_frame.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 6))
        row += 1
        checkbox_frame.columnconfigure(0, weight=1)
        checkbox_frame.columnconfigure(1, weight=1)
        checkbox_frame.columnconfigure(2, weight=1)

        # The following string matches are kept in comments/tuples for test assertions:
        # "UF text", "Panel number text", "Panel local x arrow", "Panel local y arrow", "Show mesh", "Color code"
        view_options = [
            ('UF text', self._fea_show_uf_text, 'UF text'),
            ('Panel number text', self._fea_show_panel_text, 'Panel No.'),
            ('Panel local x arrow', self._fea_show_local_x_arrow, 'Local x'),
            ('Panel local y arrow', self._fea_show_local_y_arrow, 'Local y'),
            ('Show mesh', self._fea_show_mesh, 'Show mesh'),
            ('Color code', self._fea_color_code, 'Color code'),
        ]

        self._style.configure('FEAView.TCheckbutton', font=self._text_size['Text 8'], background=self._general_color)

        for option_index, (orig_text, option_var, display_text) in enumerate(view_options):
            check = ttk.Checkbutton(
                checkbox_frame,
                text=display_text,
                variable=option_var,
                style='FEAView.TCheckbutton',
                command=lambda: self._refresh_fea_buckling_views(rebuild_3d=True),
            )
            grid_row = option_index // 3
            grid_col = option_index % 3

            px_left = 0 if grid_col == 0 else 4
            px_right = 0 if grid_col == 2 else 4

            check.grid(
                row=grid_row,
                column=grid_col,
                sticky='w',
                padx=(px_left, px_right),
                pady=(0, 4),
            )
            rows.append(check)
        rows.append(checkbox_frame)

        add_separator()
        add_label('Selected Panel', bold=True)
        add_label(f'Panel: {selected}')
        add_label(f'Line: {line_text}')
        add_label(f'Domain: {domain_text}', wrap=285)
        add_label(f'UF: {uf_text}')
        add_label(f'Geometry: {geometry_text}', wrap=285)
        add_label(f'Stress: {stress_text}', wrap=285)
        details_button = ttk.Button(
            panel_frame,
            text='Show all UFs / details',
            command=self._show_fea_buckling_details_popup,
        )
        details_button.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(2, 6))
        row += 1
        rows.append(details_button)

        add_separator()
        add_label('Import Summary', bold=True)
        add_label(f'Panels: {panel_count}')
        add_label(f'Source: {source_text}', wrap=285)
        if warning_text:
            add_separator()
            add_label('Warning', bold=True, foreground='red')
            add_label(warning_text, foreground='red', wrap=285)
        add_separator()
        add_label('Stress Interpretation', bold=True)
        add_label('Representative membrane stresses for the selected buckling panel.', wrap=285)
        stress_method = ttk.OptionMenu(
            panel_frame,
            self._fea_stress_reduction_method,
            self._fea_stress_reduction_method.get(),
            *fe_plate_fields.available_stress_reduction_methods(),
        )
        stress_method.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 4))
        row += 1
        stress_apply = ttk.Button(
            panel_frame,
            text='Apply stress method',
            command=self._on_fea_buckling_option_changed,
        )
        stress_apply.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(0, 5))
        row += 1
        rows.extend([stress_method, stress_apply])
        add_label(self._fea_stress_method_description(self._fea_stress_reduction_method.get()), wrap=285)
        stress_canvas = tk.Canvas(
            panel_frame,
            width=285,
            height=120,
            bd=0,
            highlightthickness=0,
            background=self._style.lookup('TFrame', 'background'),
        )
        stress_canvas.grid(row=row, column=0, columnspan=3, sticky='ew', padx=12, pady=(2, 8))
        row += 1
        self._draw_fea_stress_interpretation_canvas(stress_canvas, selected_panel)
        rows.append(stress_canvas)
        self._fea_buckling_created.extend(rows)

    def gui_load_combinations(self, event):
        '''
        Initsializing and updating gui for load combinations.
        The fields are located left of the Canvas.
        :return:
        '''

        if getattr(self, '_fea_buckling_mode', False):
            self._gui_fea_buckling_options()
            return

        if all([self._line_is_active, self._active_line in self._line_to_struc.keys(),
                self._gui_functional_look == 'all items']):
            if getattr(self, '_simplified_calculation_mode', False):
                self._gui_single_line_manual_pressure()
                return

            lc_x, lc_x_delta, lc_y, lc_y_delta = 0.791666667, 0.026041667, 0.287037037, 0.023148148

            # self._active_label.config(text=self._active_line)
            combination = self._combination_slider_map[int(self._combination_slider.get())]

            # removing label, checkbox and entry. setting created items to empty list.
            [[item.destroy() for item in items] for items in
             [self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created]]
            self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created = [], [], [], []

            if self._line_to_struc[self._active_line][0].Plate.get_structure_type() == '':
                self._info_created.append(ttk.Label(self._main_fr, text='No structure type selected',
                                                    font=self._text_size["Text 10 bold"], ))
                self._info_created[0].place(relx=lc_x, y=lc_y + 3 * lc_y_delta)
            elif self._line_to_struc[self._active_line][5] is not None:
                pass
            elif combination != 'Cylinder':
                # creating new label, checkbox and entry. creating new list of created items.
                # finding loads applied to lines
                counter = 0

                if len(self._load_dict) != 0 and combination != 'manual':
                    for load, data in self._load_dict.items():
                        if self._active_line in self._load_dict[load][1] and data[0].get_limit_state() == 'ULS':
                            name = (combination, self._active_line, str(load))  # tuple to identify combinations on line
                            self._lc_comb_created.append(ttk.Label(self._main_fr, text=load,
                                                                   font=self._text_size['Text 8 bold'],
                                                                   ))
                            self._lc_comb_created.append(ttk.Entry(self._main_fr,
                                                                   textvariable=self._new_load_comb_dict[name][0],
                                                                   width=5,
                                                                   ))
                            self._lc_comb_created.append(ttk.Entry(self._main_fr,
                                                                   textvariable=self._new_load_comb_dict[name][1],
                                                                   width=5,
                                                                   ))
                            self._lc_comb_created.append(ttk.Checkbutton(self._main_fr,
                                                                         variable=self._new_load_comb_dict[name][2]))

                    for load_no in range(int(len(self._lc_comb_created) / 4)):
                        self._lc_comb_created[0 + load_no * 4].place(relx=lc_x, rely=lc_y + lc_y_delta * load_no)
                        self._lc_comb_created[1 + load_no * 4].place(relx=lc_x + 5 * lc_x_delta,
                                                                     rely=lc_y + lc_y_delta * load_no)
                        self._lc_comb_created[2 + load_no * 4].place(relx=lc_x + 6 * lc_x_delta,
                                                                     rely=lc_y + lc_y_delta * load_no)
                        self._lc_comb_created[3 + load_no * 4].place(relx=lc_x + 7 * lc_x_delta,
                                                                     rely=lc_y + lc_y_delta * load_no)
                        counter += 1

                # finding tank loads applied to line (automatically created compartments.
                lc_y += 0.023148148 * counter
                counter = 0
                if len(self._tank_dict) != 0 and combination != 'manual':
                    for compartment in self.get_compartments_for_line(self._active_line):
                        name = (combination, self._active_line,
                                'comp' + str(compartment))  # tuple to identify combinations on line
                        self._comp_comb_created.append(ttk.Label(self._main_fr, text='Compartment' + str(compartment),
                                                                 ))
                        self._comp_comb_created.append(ttk.Entry(self._main_fr,
                                                                 textvariable=self._new_load_comb_dict[name][0],
                                                                 width=5,
                                                                 ))
                        self._comp_comb_created.append(ttk.Entry(self._main_fr,
                                                                 textvariable=self._new_load_comb_dict[name][1],
                                                                 width=5,
                                                                 ))
                        self._comp_comb_created.append(ttk.Checkbutton(self._main_fr,
                                                                       variable=self._new_load_comb_dict[name][2]))

                    for comp_no in range(int(len(self._comp_comb_created) / 4)):
                        self._comp_comb_created[0 + comp_no * 4].place(relx=lc_x, rely=lc_y + lc_y_delta * comp_no)
                        self._comp_comb_created[1 + comp_no * 4].place(relx=lc_x + 5 * lc_x_delta,
                                                                       rely=lc_y + lc_y_delta * comp_no)
                        self._comp_comb_created[2 + comp_no * 4].place(relx=lc_x + 6 * lc_x_delta,
                                                                       rely=lc_y + lc_y_delta * comp_no)
                        self._comp_comb_created[3 + comp_no * 4].place(relx=lc_x + 7 * lc_x_delta,
                                                                       rely=lc_y + lc_y_delta * comp_no)
                        counter += 1

                lc_y += 0.027777778 * counter
                # finding manual loads applied to the line

                name = ('manual', self._active_line, 'manual')  # tuple to identify combinations on line
                if name in self._new_load_comb_dict.keys():
                    self._manual_created.append(ttk.Label(self._main_fr, text='Manual (pressure/LF)',
                                                          ))
                    self._manual_created.append(
                        ttk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][0], width=15,
                                  ))
                    self._manual_created.append(
                        ttk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][1], width=6,
                                  ))
                    self._manual_created.append(
                        ttk.Checkbutton(self._main_fr, variable=self._new_load_comb_dict[name][2]))
                    self._manual_created[0].place(relx=lc_x, rely=lc_y)
                    self._manual_created[1].place(relx=lc_x + 4 * lc_x_delta, rely=lc_y)
                    self._manual_created[2].place(relx=lc_x + 6 * lc_x_delta, rely=lc_y)
                    self._manual_created[3].place(relx=lc_x + 7 * lc_x_delta, rely=lc_y)

            if self._line_to_struc[self._active_line][5] is None:
                results = self.calculate_all_load_combinations_for_line(self._active_line)

                self._result_label_dnva.config(text='DNV a [Pa]: ' + str(results['dnva']),
                                               font=self._text_size['Text 8'])
                self._result_label_dnvb.config(text='DNV b [Pa]: ' + str(results['dnvb']),
                                               font=self._text_size['Text 8'])
                self._result_label_tanktest.config(text='TT [Pa]: ' + str(results['tanktest']),
                                                   font=self._text_size['Text 8'])

                self._result_label_manual.config(text='Manual [Pa]: ' + str(results['manual']))

                lc_y = self.results_gui_start + 0.01
                self._result_label_dnva.place(relx=lc_x + 0 * lc_x_delta, rely=lc_y + lc_y_delta * 1.5)
                self._result_label_dnvb.place(relx=lc_x + 4 * lc_x_delta, rely=lc_y + lc_y_delta * 1.5)
                self._result_label_tanktest.place(relx=lc_x + 0 * lc_x_delta, rely=lc_y + 2.4 * lc_y_delta)

                self._result_label_manual.place(relx=lc_x + 4 * lc_x_delta, rely=lc_y + 2.4 * lc_y_delta)
                self._lab_pressure.place(relx=0.786458333, rely=self.results_gui_start)
            else:
                for item in [self._result_label_dnva, self._result_label_dnvb,
                             self._result_label_tanktest, self._result_label_manual, self._lab_pressure]:
                    item.place_forget()
                    # self._combination_slider.set(4)

    def slider_used(self, event):
        '''
        Action when slider is activated.
        :return:
        '''
        self._canvas_scale = self._slider.get()
        self.update_frame()

    def grid_operations(self, line, coordinates):
        '''
        Creating a grid in the canvas used for various caluclations
        :return:
        '''
        try:
            if self._line_to_struc[line][0].Plate.get_structure_type() not in ('GENERAL_INTERNAL_NONWT', 'FRAME'):
                self._pending_grid_draw[line] = coordinates
        except KeyError:
            pass

    def grid_find_tanks(self, animate=False):
        '''
        Printing the grid in a separate window
        :return:
        '''

        if self._line_to_struc == {}:
            tk.messagebox.showerror('Search error', 'No geometry with properties exist.')
            return
        # setting the button to red
        try:
            img_file_name = 'img_int_pressure_button_search.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._int_button.config(image=photo)
            self._int_button.image = photo
        except TclError:
            pass

        animate = tk.messagebox.askquestion('Search for compartments',
                                            'Searching for compartments will use a large matrix to '
                                            'identify watertight members and consequently the '
                                            'enclosed compartments. \n'
                                            'You may animate the search for vizualization and '
                                            'increased understating purposes.\n '
                                            'However, this will take some more time than just '
                                            'showing the final result.\n'
                                            '\n'
                                            'Yes - Show search animation\n'
                                            'No - Draw final result only\n'
                                            '\n'
                                            'Choose yes or no.')
        animate = True if animate == 'yes' else False

        self._main_grid.clear()
        self._tank_dict = {}
        self._pending_grid_draw = {}
        self._compartments_listbox.delete(0, 'end')

        for line, points in self._line_dict.items():
            # making the lines made by used in the grid
            p1 = self._point_dict['point' + str(points[0])]
            p2 = self._point_dict['point' + str(points[1])]
            self.grid_operations(line, [self.get_grid_coord_from_points_coords(p1),
                                        self.get_grid_coord_from_points_coords(p2)])

        self._grid_calc = grid_window.CreateGridWindow(self._main_grid, self._canvas_dim,
                                                       self._pending_grid_draw, self._canvas_base_origo)

        compartment_search_return = self._grid_calc.search_bfs(animate=animate)

        for comp_no, properties in compartment_search_return['compartments'].items():
            # finding actual max min elevation from grid
            min_el = (float('inf'), float('inf'))
            max_el = (-float('inf'), -float('inf'))
            if comp_no > 1:
                self._compartments_listbox.insert('end', comp_no)
                for corner in properties[1]:
                    corner_real = self.get_point_coords_from_grid_coords(corner)
                    if self.get_point_coords_from_grid_coords(corner)[1] < min_el[1]:
                        min_el = self.get_closest_point(corner_real)[1]
                    if self.get_point_coords_from_grid_coords(corner)[1] > max_el[1]:
                        max_el = self.get_closest_point(corner_real)[1]
                self.new_tank(int(comp_no), properties[0], min_el, max_el)
            comp_name = 'comp' + str(int(comp_no))

            for combination in self._load_factors_dict.keys():
                # creating the load factor combinations for tanks.
                for line in self._line_dict.keys():
                    if comp_no in self.get_compartments_for_line(line):
                        name = (combination, line, comp_name)
                        self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
                        self._new_load_comb_dict[name][0].set(self._load_factors_dict[combination][1])
                        self._new_load_comb_dict[name][1].set(self._load_factors_dict[combination][2])
                        self._new_load_comb_dict[name][2].set(1)
        try:
            img_file_name = 'img_int_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)

            self._int_button.config(image=photo)
            self._int_button.image = photo
        except TclError:
            pass

        if animate == False:
            tank_count = None if len(self._tank_dict) == 0 else len(self._tank_dict)
            if tank_count is not None:
                self._grid_calc.draw_grid(tank_count=tank_count)
        else:
            tank_count = None if len(self._tank_dict) == 0 else len(self._tank_dict)
            if tank_count is not None:
                self._grid_calc.animate_grid(grids_to_animate=compartment_search_return['grids'],
                                             tank_count=None if len(self._tank_dict) == 0 else len(self._tank_dict))

        self.get_cob()  # Calculating COB
        self.update_frame()

    def grid_display_tanks(self, save=False):
        '''
        Opening matplotlib grid illustation
        :return:
        '''

        try:
            if self._grid_calc != None:
                self._grid_calc.draw_grid(save=save,
                                          tank_count=None if len(self._tank_dict) == 0 else len(self._tank_dict))
        except RecursionError:
            pass

    def add_to_combinations_dict(self, line):
        '''
        When creating new line and tanks exist, the combinations dict must be updated.
        :param line:
        :return:
        '''
        if len(self._tank_dict) != 0:
            for compartment in self.get_compartments_for_line(line):
                for combination in self._load_factors_dict.keys():
                    name = (combination, line, 'comp' + str(compartment))
                    self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
                    self._new_load_comb_dict[name][0].set(self._load_factors_dict[combination][1])
                    self._new_load_comb_dict[name][1].set(self._load_factors_dict[combination][2])
                    self._new_load_comb_dict[name][2].set(1)
        else:
            pass
        name = ('manual', line, 'manual')
        self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
        self._new_load_comb_dict[name][0].set(0)
        if getattr(self, '_simplified_calculation_mode', False):
            self._new_load_comb_dict[name][1].set(1)
            self._new_load_comb_dict[name][2].set(1)
        else:
            self._new_load_comb_dict[name][1].set(0)
            self._new_load_comb_dict[name][2].set(0)
        self._new_load_comb_dict[name][0].trace_add('write', self.trace_acceptance_change)
        self._new_load_comb_dict[name][1].trace_add('write', self.trace_acceptance_change)

    def trace_update_load(self, *args):
        try:
            project_services.mark_line_for_recalculation(self._line_to_struc, self._active_line)
        except BaseException as error:
            pass

    def trace_shift_change(self, *args):
        try:
            self.update_frame()
        except (TclError, ZeroDivisionError):
            pass

    def trace_acceptance_change(self, *args):
        try:
            # Mark dirty before redrawing. Otherwise the first redraw after a
            # load/acceptance change may reuse stale cached results.
            project_services.mark_lines_for_recalculation(self._line_to_struc)
            self.update_frame()
        except (TclError, ZeroDivisionError):
            pass

    def _calc_state_signature(self):
        """Small signature for the full-frame calculation cache.

        Selecting/highlighting a line should not force a new buckling run.
        Recalculate only when structural/load data is marked dirty, or when
        global calculation settings that affect results have changed.
        """
        try:
            mat_factor = float(self._new_material_factor.get())
        except Exception:
            mat_factor = None

        try:
            buckling_method = self._new_buckling_method.get()
        except Exception:
            buckling_method = None

        return {
            'material factor': mat_factor,
            'buckling method': buckling_method,
            'line count': len(self._line_to_struc),
            'geometry line count': len(self._line_dict),
        }

    def _calculation_state_is_dirty(self):
        """Return True if any stored structure needs recalculation."""
        try:
            return any(
                obj_list[0].need_recalc
                for obj_list in self._line_to_struc.values()
                if obj_list and obj_list[0] is not None
            )
        except Exception:
            return True

    def update_frame(self, event=None, *args, force_recalc=False):

        signature = self._calc_state_signature()
        cached_signature = getattr(self, '_last_calc_state_signature', None)
        cached_state = getattr(self, '_last_calc_state', None)

        if (
                not force_recalc
                and cached_state is not None
                and cached_signature == signature
                and not self._calculation_state_is_dirty()
        ):
            state = cached_state
        else:
            state = self.get_color_and_calc_state()
            self._last_calc_state = state
            self._last_calc_state_signature = signature

        self.draw_results(state=state)
        self.draw_canvas(state=state)
        self.draw_prop()
        # self.trace_puls_up_or_sp()

        return state

    def _ml_model_exists(self, mat_fac, key):
        return (
                mat_fac in self._ML_buckling
                and key in self._ML_buckling[mat_fac]
                and self._ML_buckling[mat_fac][key] is not None
        )

    def _predict_numeric_uf_pipeline(self, mat_fac, sp_or_up, boundary_type, buckling_ml_input):
        """
        Predict raw numeric buckling/ultimate UF using the numeric UF pipeline.

        Important:
            The numeric model is trained on Buckling/Ultimate UF at material factor = 1.0.
            Material factor scaling is applied later in get_color_and_calc_state().
        """
        if sp_or_up == 'SP':
            prefix = 'num SP int' if boundary_type == 'Int' else 'num SP GLGT'
        else:
            prefix = 'num UP int' if boundary_type == 'Int' else 'num UP GLGT'

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

        missing = [key for key in required_keys if not self._ml_model_exists(mat_fac, key)]
        if missing:
            return {
                'available': False,
                'valid_prediction': None,
                'valid_label': 'numeric ML unavailable',
                'buckling_uf': float('inf'),
                'ultimate_uf': float('inf'),
                'buckling_uf_raw': float('inf'),
                'ultimate_uf_raw': float('inf'),
                'material_factor': mat_fac,
                'error': 'Missing numeric ML model(s): ' + ', '.join(missing),
            }

        try:
            x_valid = self._ML_buckling[mat_fac][valid_xscaler_key].transform(
                buckling_ml_input
            )
            valid_pred = self._ML_buckling[mat_fac][valid_predictor_key].predict(
                x_valid
            )[0]
            valid_pred_int = int(valid_pred)

            if valid_pred_int != 1:
                return {
                    'available': True,
                    'valid_prediction': valid_pred_int,
                    'valid_label': 'invalid/NaN UF predicted',
                    'buckling_uf': float('inf'),
                    'ultimate_uf': float('inf'),
                    'buckling_uf_raw': float('inf'),
                    'ultimate_uf_raw': float('inf'),
                    'material_factor': mat_fac,
                    'error': '',
                }

            x_reg = self._ML_buckling[mat_fac][reg_xscaler_key].transform(
                buckling_ml_input
            )
            y_scaled = self._ML_buckling[mat_fac][reg_predictor_key].predict(
                x_reg
            )
            y_numeric = self._ML_buckling[mat_fac][reg_yscaler_key].inverse_transform(
                y_scaled
            )[0]

            buckling_uf_raw = float(y_numeric[0])
            ultimate_uf_raw = float(y_numeric[1])

            return {
                'available': True,
                'valid_prediction': valid_pred_int,
                'valid_label': 'valid numeric UF predicted',
                'buckling_uf': buckling_uf_raw,
                'ultimate_uf': ultimate_uf_raw,
                'buckling_uf_raw': buckling_uf_raw,
                'ultimate_uf_raw': ultimate_uf_raw,
                'material_factor': mat_fac,
                'error': '',
            }

        except Exception as e:
            return {
                'available': False,
                'valid_prediction': None,
                'valid_label': 'numeric ML error',
                'buckling_uf': float('inf'),
                'ultimate_uf': float('inf'),
                'buckling_uf_raw': float('inf'),
                'ultimate_uf_raw': float('inf'),
                'material_factor': mat_fac,
                'error': str(e),
            }

    def _numeric_uf_color(self, uf, mat_fac=None):
        """
        Numeric UF is material-factored in get_color_and_calc_state().
        Therefore the acceptance limit is 1.0.
        """
        try:
            return 'green' if float(uf) <= 1.0 else 'red'
        except Exception:
            return 'red'

    def _semi_analytical_uf_color(self, uf):
        """SemiAnalytical UF is material-factored before pass/fail coloring."""
        try:
            return 'green' if float(uf) <= 1.0 else 'red'
        except Exception:
            return 'red'

    def _predict_csr_requirement(
            self, plate_obj, stiffener_obj, design_pressure, material_factor,
            use_semi_analytical_equation=False):
        """Predict CSR requirement; SemiAnalytical uses direct equations instead of ML classifiers."""
        if use_semi_analytical_equation:
            try:
                class _SemiAnalyticalCsrObject:
                    pass

                calc_object = _SemiAnalyticalCsrObject()
                calc_object.Plate = plate_obj
                calc_object.Stiffener = stiffener_obj
                csr, color, _ = op.semi_analytical.predict_anystructure_csr_requirement(
                    calc_object,
                    design_pressure,
                )
                return csr, color
            except Exception:
                return [0, 0, 0, 0], 'red'

        try:
            mat_fac = float(material_factor)
        except Exception:
            mat_fac = plate_obj.mat_factor

        if mat_fac not in [1.1, 1.15]:
            mat_fac = 1.15

        try:
            if plate_obj.get_puls_sp_or_up() == 'UP':
                x_csr = plate_obj.get_buckling_ml_input(
                    design_lat_press=design_pressure,
                    csr=True,
                )
                x_csr = self._ML_buckling[mat_fac]['CSR scaler UP'].transform(x_csr)
                csr_pl = self._ML_buckling[mat_fac]['CSR predictor UP'].predict(x_csr)[0]
                csr = [csr_pl, float('inf'), float('inf'), float('inf')]
                color = 'green' if csr_pl == 1 else 'red'
            elif stiffener_obj is not None:
                x_csr = stiffener_obj.get_buckling_ml_input(
                    design_lat_press=design_pressure,
                    csr=True,
                )
                x_csr = self._ML_buckling[mat_fac]['CSR scaler SP'].transform(x_csr)
                csr_pl, csr_web, csr_web_fl, csr_fl = self._ML_buckling[mat_fac][
                    'CSR predictor SP'
                ].predict(x_csr)[0]
                csr = [csr_pl, csr_web, csr_web_fl, csr_fl]
                color = 'green' if all([csr_pl == 1, csr_web == 1, csr_web_fl == 1, csr_fl == 1]) else 'red'
            else:
                csr = [0, 0, 0, 0]
                color = 'red'
        except Exception:
            csr = [0, 0, 0, 0]
            color = 'red'

        return csr, color

    @staticmethod
    def _cylinder_buckling_uf(cylinder_results):
        """Return the governing cylinder buckling UF used for GUI color coding."""
        uf_values = []
        for key in ['Unstiffened shell', 'Unstiffened conical shell', 'Longitudinal stiffened shell',
                    'Ring stiffened shell', 'Heavy ring frame']:
            try:
                if cylinder_results.get(key, None) is not None:
                    uf_values.append(float(cylinder_results[key]))
            except Exception:
                pass

        try:
            if cylinder_results.get('Need to check column buckling', False) is True and \
                    cylinder_results.get('Column stability UF', None) is not None:
                uf_values.append(float(cylinder_results['Column stability UF']))
        except Exception:
            pass

        return max(uf_values) if uf_values else 0.0

    def get_color_and_calc_state(self, current_line=None, active_line_only=False):
        ''' Return calculations and colors for line and results. '''

        return_dict = {
            'colors': {},
            'section_modulus': {},
            'thickness': {},
            'shear_area': {},
            'buckling': {},
            'fatigue': {},
            'pressure_uls': {},
            'pressure_fls': {},
            'all_obj': {},
            'scant_calc_obj': {},
            'fatigue_obj': {},
            'utilization': {},
            'slamming': {},
            'color code': {},
            'ML buckling colors': {},
            'ML buckling class': {},
            'ML buckling numeric': {},
            'ML buckling numeric valid': {},
            'ML buckling numeric colors': {},
            'SemiAnalytical': {},
            'SemiAnalytical valid': {},
            'SemiAnalytical colors': {},
            'weights': {},
            'cylinder': {},
            '_cache_signature': {},
        }

        return_dict['slamming'][current_line] = {}

        if current_line is None and active_line_only:
            line_iterator = [self._active_line, ]
        elif current_line is None and not active_line_only and len(self._line_dict) != 0:
            line_iterator = self._line_dict.keys()
        elif current_line is not None:
            line_iterator = [current_line, ]
        elif current_line not in self._line_to_struc.keys() and active_line_only:
            return return_dict
        else:
            return return_dict
        rec_for_color = {}
        selected_buckling_method = self._new_buckling_method.get()

        def _copy_cached_line_state(cached_state, line_name):
            """Copy one line from a previously calculated state into this state.

            Do not return the whole cached state here. get_color_and_calc_state()
            is normally called for all lines; returning the first cached full-state
            would skip later lines that may actually need recalculation.
            """

            for section_name, section_value in cached_state.items():
                if isinstance(section_value, dict) and line_name in section_value:
                    return_dict.setdefault(section_name, {})[line_name] = section_value[line_name]

            util = return_dict.get('utilization', {}).get(line_name, {})
            rec_for_color[line_name] = {
                'rp buckling': util.get('buckling', 0.0),
                'fatigue': util.get('fatigue', 0.0),
                'section modulus': util.get('section', 0.0),
                'shear': util.get('shear', 0.0),
                'plate thickness': util.get('thickness', 0.0),
            }

        # Cylinder general
        all_cyl_thk, recorded_cyl_long_stf = list(), list()
        for obj_list in self._line_to_struc.values():
            if obj_list[5] is not None:
                all_cyl_thk.append(round(obj_list[5].ShellObj.thk * 1000, 2))
                if obj_list[5].LongStfObj is not None:
                    recorded_cyl_long_stf.append(obj_list[5].LongStfObj.get_beam_string())
        all_cyl_thk = np.unique(all_cyl_thk)
        all_cyl_thk = np.sort(all_cyl_thk)

        for current_line in line_iterator:
            rec_for_color[current_line] = {}
            slamming_pressure = 0
            if current_line in self._line_to_struc.keys():

                if self._line_to_struc[current_line][5] is not None:
                    cyl_obj = self._line_to_struc[current_line][5]
                    cyl_results = cyl_obj.get_utilization_factors()
                else:
                    cyl_thickness = 0

                all_obj = self._line_to_struc[current_line][0]
                obj_scnt_calc_pl = all_obj.Plate  # self._line_to_struc[current_line][1]
                obj_scnt_calc_stf = all_obj.Stiffener  # self._line_to_struc[current_line][1]
                obj_scnt_calc_girder = all_obj.Girder  # self._line_to_struc[current_line][1]

                return_dict['all_obj'][current_line] = all_obj

                if all_obj.need_recalc is False:
                    # Cached state may be stale when the selected ML material factor changes.
                    # Reuse cache only when the cached numeric ML material factor matches
                    # the current GUI-selected material factor.
                    cached_state = self._state_logger.get(current_line, None)
                    try:
                        selected_mat_fac = float(self._new_material_factor.get())
                    except Exception:
                        selected_mat_fac = obj_scnt_calc_pl.mat_factor

                    cache_signature = {
                        'material factor': selected_mat_fac,
                        'buckling method': selected_buckling_method,
                    }
                    cached_signature = {}
                    if cached_state is not None:
                        cached_signature = (
                            cached_state
                            .get('_cache_signature', {})
                            .get(current_line, {})
                        )

                    if cached_state is not None and cached_signature == cache_signature:
                        _copy_cached_line_state(cached_state, current_line)
                        continue
                    # Otherwise continue and recalculate this line so the active buckling method is updated.
                try:
                    norm_and_slam = self.get_highest_pressure(current_line)
                    design_pressure = norm_and_slam['normal'] / 1000
                    if norm_and_slam['slamming'] is None:
                        pass
                    else:
                        slamming_pressure = norm_and_slam['slamming']
                        slamming_red_fac_pl = norm_and_slam['slamming plate reduction factor']
                        slamming_red_fac_stf = norm_and_slam['slamming stf reduction factor']
                except KeyError:
                    design_pressure = 0

                min_thk = obj_scnt_calc_pl.get_dnv_min_thickness(design_pressure)
                color_thk = 'green' if obj_scnt_calc_pl.is_acceptable_pl_thk(design_pressure) else 'red'
                rec_for_color[current_line]['plate thickness'] = (min_thk / 1000) / obj_scnt_calc_pl.get_pl_thk()
                all_obj.lat_press = design_pressure / 1000
                buckling = all_obj.plate_buckling()

                all_buckling_uf_list = list()
                for buc_domain, domain_results in buckling.items():
                    for uf_text, uf_num in domain_results.items():
                        if buc_domain != 'Local buckling':
                            all_buckling_uf_list.append(uf_num)
                color_buckling = 'green' if all([uf <= 1 for uf in all_buckling_uf_list]) \
                    else 'red'
                rec_for_color[current_line]['rp buckling'] = max(all_buckling_uf_list)
                if obj_scnt_calc_stf is not None:
                    sec_mod = [obj_scnt_calc_stf.get_section_modulus()[0],
                               obj_scnt_calc_stf.get_section_modulus()[1]]

                    shear_area = obj_scnt_calc_stf.get_shear_area()
                    min_shear = obj_scnt_calc_stf.get_minimum_shear_area(design_pressure)
                    min_sec_mod = obj_scnt_calc_stf.get_dnv_min_section_modulus(design_pressure)
                    rec_for_color[current_line]['section modulus'] = min_sec_mod / min(sec_mod)
                    rec_for_color[current_line]['shear'] = min_shear / shear_area
                    return_dict['slamming'][current_line] = dict()
                    if slamming_pressure is not None and slamming_pressure > 0:
                        return_dict['slamming'][current_line]['state'] = True
                    else:
                        return_dict['slamming'][current_line]['state'] = False

                    try:
                        fatigue_obj = self._line_to_struc[current_line][2]
                        p_int = self.get_fatigue_pressures(current_line, fatigue_obj.get_accelerations())['p_int']
                        p_ext = self.get_fatigue_pressures(current_line, fatigue_obj.get_accelerations())['p_ext']
                        damage = fatigue_obj.get_total_damage(int_press=(p_int['loaded'], p_int['ballast'],
                                                                         p_int['part']), ext_press=(p_ext['loaded'],
                                                                                                    p_ext['ballast'],
                                                                                                    p_ext['part']))
                        dff = fatigue_obj.get_dff()
                        color_fatigue = 'green' if damage * dff <= 1 else 'red'
                    except AttributeError:
                        fatigue_obj, p_int, p_ext, damage, dff = [None for dummy in range(5)]
                        color_fatigue = 'green'

                    color_sec = 'green' if obj_scnt_calc_stf.is_acceptable_sec_mod(sec_mod, design_pressure) \
                        else 'red'
                    color_shear = 'green' if obj_scnt_calc_stf.is_acceptable_shear_area(shear_area, design_pressure) \
                        else 'red'
                else:
                    sec_mod = [0, 0]
                    shear_area = 0
                    min_shear = 0
                    min_sec_mod = 0
                    rec_for_color[current_line]['section modulus'] = 0.0
                    rec_for_color[current_line]['shear'] = 0
                    return_dict['slamming'][current_line] = dict()
                    fatigue_obj, p_int, p_ext, damage, dff = [None for dummy in range(5)]
                    color_fatigue = 'green'
                    color_sec = 'green' if all_obj.Stiffener is None else 'black'
                    color_shear = 'green' if all_obj.Stiffener is None else 'black'
                    return_dict['slamming'][current_line]['state'] = False

                if slamming_pressure is not None and slamming_pressure > 0 and obj_scnt_calc_stf is not None:
                    slamming_res = obj_scnt_calc_stf.calculate_slamming_stiffener(slamming_pressure,
                                                                                  red_fac=slamming_red_fac_pl)
                    min_pl_slamming = obj_scnt_calc_stf.calculate_slamming_plate(slamming_pressure,
                                                                                 red_fac=slamming_red_fac_stf)

                    if slamming_res['Zp_req'] is not None:
                        zpl = obj_scnt_calc_stf.get_net_effective_plastic_section_modulus()
                        zpl_req = slamming_res['Zp_req']
                        color_sec = 'green' if zpl >= zpl_req else 'red'
                    else:
                        zpl = obj_scnt_calc_stf.get_net_effective_plastic_section_modulus()
                        zpl_req = None
                        color_sec = 'red'

                    color_shear = 'green' if round(obj_scnt_calc_stf.get_web_thk() * 1000, 1) >= \
                                             round(slamming_res['tw_req'], 1) else 'red'
                    color_thk = 'green' if round(obj_scnt_calc_stf.get_pl_thk() * 1000, 1) >= \
                                           round(min_pl_slamming, 1) else 'red'

                    return_dict['slamming'][current_line]['zpl'] = zpl
                    return_dict['slamming'][current_line]['zpl_req'] = zpl_req
                    return_dict['slamming'][current_line]['min_plate_thk'] = min_pl_slamming
                    return_dict['slamming'][current_line]['min_web_thk'] = slamming_res['tw_req']

                return_dict['colors'][current_line] = {'buckling': color_buckling, 'fatigue': color_fatigue,
                                                       'section': color_sec, 'shear': color_shear,
                                                       'thickness': color_thk}
                '''
                Cylinder calculations
                '''
                if self._line_to_struc[current_line][5] is not None:
                    return_dict['cylinder'][current_line] = cyl_results

                '''
                Machine learning buckling.

                Classification pipeline:
                    return_dict['ML buckling class']
                    return_dict['ML buckling colors']

                Numeric UF pipeline:
                    return_dict['ML buckling numeric']
                    return_dict['ML buckling numeric valid']
                    return_dict['ML buckling numeric colors']
                '''

                # Default inactive/invalid results. The expensive ML and SemiAnalytical
                # solvers are evaluated only for the selected buckling method.
                try:
                    active_mat_fac = float(self._new_material_factor.get())
                except Exception:
                    active_mat_fac = obj_scnt_calc_pl.mat_factor

                return_dict['ML buckling colors'][current_line] = {
                    'buckling': 'red',
                    'ultimate': 'red',
                    'CSR requirement': 'red',
                }
                return_dict['ML buckling class'][current_line] = {
                    'buckling': 'not calculated for active method',
                    'ultimate': 'not calculated for active method',
                    'CSR': [0, 0, 0, 0],
                }
                return_dict['ML buckling numeric'][current_line] = {
                    'buckling UF': float('inf'),
                    'ultimate UF': float('inf'),
                    'buckling UF raw': float('inf'),
                    'ultimate UF raw': float('inf'),
                    'material factor': active_mat_fac,
                    'error': '',
                }
                return_dict['ML buckling numeric valid'][current_line] = {
                    'available': False,
                    'valid prediction': None,
                    'valid label': 'numeric ML not calculated for active method',
                }
                return_dict['ML buckling numeric colors'][current_line] = {
                    'buckling': 'red',
                    'ultimate': 'red',
                }
                return_dict['SemiAnalytical'][current_line] = {
                    'buckling UF': float('inf'),
                    'ultimate UF': float('inf'),
                    'buckling UF raw': float('inf'),
                    'ultimate UF raw': float('inf'),
                    'material factor': active_mat_fac,
                    'acceptance': 1.0,
                    'panel family': None,
                    'confidence': None,
                    'error': '',
                }
                return_dict['SemiAnalytical valid'][current_line] = {
                    'available': False,
                    'valid prediction': None,
                    'valid label': 'SemiAnalytical not calculated for active method',
                }
                return_dict['SemiAnalytical colors'][current_line] = {
                    'buckling': 'red',
                    'ultimate': 'red',
                }

                if selected_buckling_method in ['ML-Numeric (PULS based)', 'SemiAnalytical S3/U3']:
                    csr_values, csr_color = self._predict_csr_requirement(
                        obj_scnt_calc_pl,
                        obj_scnt_calc_stf,
                        design_pressure,
                        active_mat_fac,
                        use_semi_analytical_equation=selected_buckling_method == 'SemiAnalytical S3/U3',
                    )
                    return_dict['ML buckling class'][current_line]['CSR'] = csr_values
                    return_dict['ML buckling colors'][current_line]['CSR requirement'] = csr_color

                if selected_buckling_method == 'ML-Numeric (PULS based)':
                    mat_fac_error = ''

                    # -----------------------------------------------------------------------------
                    # Helper defaults in case ML cannot be evaluated
                    # -----------------------------------------------------------------------------
                    default_numeric_pred = {
                        'available': False,
                        'valid_prediction': None,
                        'valid_label': 'numeric ML not available',
                        'buckling_uf': float('inf'),
                        'ultimate_uf': float('inf'),
                        'buckling_uf_raw': float('inf'),
                        'ultimate_uf_raw': float('inf'),
                        'material_factor': None,
                        'error': '',
                    }

                    def _apply_material_factor_to_numeric_pred(numeric_pred, mat_fac):
                        """
                        Numeric UF model predicts UF at material factor = 1.0.

                        The displayed/check UF shall be:
                            UF = predicted_UF * material_factor
                        """

                        numeric_pred = numeric_pred.copy()

                        if numeric_pred.get('valid_prediction', None) == 1:
                            buckling_uf_raw = float(numeric_pred.get('buckling_uf', float('inf')))
                            ultimate_uf_raw = float(numeric_pred.get('ultimate_uf', float('inf')))

                            numeric_pred['buckling_uf_raw'] = buckling_uf_raw
                            numeric_pred['ultimate_uf_raw'] = ultimate_uf_raw

                            numeric_pred['buckling_uf'] = buckling_uf_raw * mat_fac
                            numeric_pred['ultimate_uf'] = ultimate_uf_raw * mat_fac
                            numeric_pred['material_factor'] = mat_fac
                        else:
                            numeric_pred['buckling_uf_raw'] = float('inf')
                            numeric_pred['ultimate_uf_raw'] = float('inf')
                            numeric_pred['material_factor'] = mat_fac

                        return numeric_pred

                    if obj_scnt_calc_pl.get_puls_sp_or_up() == 'UP':
                        # =========================================================================
                        # UP / unstiffened panel ML
                        # =========================================================================
                        buckling_ml_input = obj_scnt_calc_pl.get_buckling_ml_input(
                            design_lat_press=design_pressure
                        )

                        try:
                            mat_fac = float(self._new_material_factor.get())
                        except Exception:
                            mat_fac = obj_scnt_calc_pl.mat_factor
                        mat_fac_error = ''

                        if mat_fac not in [1.1, 1.15]:
                            mat_fac_error = ' MATERIAL FACTOR MUST BE 1.1 or 1.15 -> using 1.15'
                            mat_fac = 1.15

                        boundary_type = obj_scnt_calc_pl.get_puls_boundary()

                        # -------------------------------------------------------------------------
                        # Classification ML prediction
                        # -------------------------------------------------------------------------
                        if boundary_type == 'Int':
                            if self._ML_buckling[mat_fac]['cl UP buc int predictor'] is not None:
                                x_buc = self._ML_buckling[mat_fac]['cl UP buc int scaler'].transform(
                                    buckling_ml_input
                                )
                                y_pred_buc = self._ML_buckling[mat_fac]['cl UP buc int predictor'].predict(
                                    x_buc
                                )[0]
                            else:
                                y_pred_buc = 'ML buckling model missing'

                            if self._ML_buckling[mat_fac]['cl UP ult int predictor'] is not None:
                                x_ult = self._ML_buckling[mat_fac]['cl UP ult int scaler'].transform(
                                    buckling_ml_input
                                )
                                y_pred_ult = self._ML_buckling[mat_fac]['cl UP ult int predictor'].predict(
                                    x_ult
                                )[0]
                            else:
                                y_pred_ult = 'ML ultimate model missing'

                        else:
                            if self._ML_buckling[mat_fac]['cl UP buc GLGT predictor'] is not None:
                                x_buc = self._ML_buckling[mat_fac]['cl UP buc GLGT scaler'].transform(
                                    buckling_ml_input
                                )
                                y_pred_buc = self._ML_buckling[mat_fac]['cl UP buc GLGT predictor'].predict(
                                    x_buc
                                )[0]
                            else:
                                y_pred_buc = 'ML buckling model missing'

                            if self._ML_buckling[mat_fac]['cl UP ult GLGT predictor'] is not None:
                                x_ult = self._ML_buckling[mat_fac]['cl UP ult GLGT scaler'].transform(
                                    buckling_ml_input
                                )
                                y_pred_ult = self._ML_buckling[mat_fac]['cl UP ult GLGT predictor'].predict(
                                    x_ult
                                )[0]
                            else:
                                y_pred_ult = 'ML ultimate model missing'

                        # -------------------------------------------------------------------------
                        # Numeric UF pipeline
                        # -------------------------------------------------------------------------
                        try:
                            numeric_pred = self._predict_numeric_uf_pipeline(
                                mat_fac=mat_fac,
                                sp_or_up='UP',
                                boundary_type=boundary_type,
                                buckling_ml_input=buckling_ml_input,
                            )
                        except Exception as e:
                            numeric_pred = default_numeric_pred.copy()
                            numeric_pred['valid_label'] = 'numeric ML error'
                            numeric_pred['error'] = str(e)

                        numeric_pred = _apply_material_factor_to_numeric_pred(numeric_pred, mat_fac)

                        csr_values, csr_color = self._predict_csr_requirement(
                            obj_scnt_calc_pl,
                            obj_scnt_calc_stf,
                            design_pressure,
                            mat_fac,
                        )

                        if mat_fac == 1.1:
                            accept = 'below or equal 0.91'
                        else:
                            accept = 'below or equal 0.87'

                        return_dict['ML buckling colors'][current_line] = {
                            'buckling': 'green' if y_pred_buc == accept else 'red',
                            'ultimate': 'green' if y_pred_ult == accept else 'red',
                            'CSR requirement': csr_color,
                        }

                        return_dict['ML buckling class'][current_line] = {
                            'buckling': str(y_pred_buc) + mat_fac_error,
                            'ultimate': str(y_pred_ult) + mat_fac_error,
                            'CSR': csr_values,
                        }

                        # -------------------------------------------------------------------------
                        # Numeric UF color handling
                        # -------------------------------------------------------------------------
                        if numeric_pred.get('valid_prediction', None) == 1:
                            numeric_buc_color = self._numeric_uf_color(
                                numeric_pred['buckling_uf'],
                                mat_fac,
                            )
                            numeric_ult_color = self._numeric_uf_color(
                                numeric_pred['ultimate_uf'],
                                mat_fac,
                            )
                        else:
                            numeric_buc_color = 'red'
                            numeric_ult_color = 'red'

                        return_dict['ML buckling numeric'][current_line] = {
                            'buckling UF': numeric_pred['buckling_uf'],
                            'ultimate UF': numeric_pred['ultimate_uf'],
                            'buckling UF raw': numeric_pred.get('buckling_uf_raw', float('inf')),
                            'ultimate UF raw': numeric_pred.get('ultimate_uf_raw', float('inf')),
                            'material factor': numeric_pred.get('material_factor', mat_fac),
                            'error': numeric_pred['error'],
                        }

                        return_dict['ML buckling numeric valid'][current_line] = {
                            'available': numeric_pred['available'],
                            'valid prediction': numeric_pred['valid_prediction'],
                            'valid label': numeric_pred['valid_label'],
                        }

                        return_dict['ML buckling numeric colors'][current_line] = {
                            'buckling': numeric_buc_color,
                            'ultimate': numeric_ult_color,
                        }

                    else:
                        # =========================================================================
                        # SP / stiffened panel ML
                        # =========================================================================

                        # Defensive guard: SP ML requires a stiffener object.
                        if obj_scnt_calc_stf is None:
                            try:
                                mat_fac = float(self._new_material_factor.get())
                            except Exception:
                                mat_fac = obj_scnt_calc_pl.mat_factor

                            if mat_fac not in [1.1, 1.15]:
                                mat_fac_error = ' MATERIAL FACTOR MUST BE 1.1 or 1.15 -> using 1.15'
                                mat_fac = 1.15
                            else:
                                mat_fac_error = ''

                            return_dict['ML buckling colors'][current_line] = {
                                'buckling': 'red',
                                'ultimate': 'red',
                                'CSR requirement': 'red',
                            }

                            return_dict['ML buckling class'][current_line] = {
                                'buckling': 'No stiffener - ML SP not available' + mat_fac_error,
                                'ultimate': 'No stiffener - ML SP not available' + mat_fac_error,
                                'CSR': [0, 0, 0, 0],
                            }

                            return_dict['ML buckling numeric'][current_line] = {
                                'buckling UF': float('inf'),
                                'ultimate UF': float('inf'),
                                'buckling UF raw': float('inf'),
                                'ultimate UF raw': float('inf'),
                                'material factor': mat_fac,
                                'error': 'No stiffener - numeric ML SP not available',
                            }

                            return_dict['ML buckling numeric valid'][current_line] = {
                                'available': False,
                                'valid prediction': None,
                                'valid label': 'No stiffener - numeric ML SP not available',
                            }

                            return_dict['ML buckling numeric colors'][current_line] = {
                                'buckling': 'red',
                                'ultimate': 'red',
                            }

                        else:
                            buckling_ml_input = obj_scnt_calc_stf.get_buckling_ml_input(
                                design_lat_press=design_pressure
                            )

                            try:
                                mat_fac = float(self._new_material_factor.get())
                            except Exception:
                                mat_fac = obj_scnt_calc_pl.mat_factor
                            mat_fac_error = ''

                            if mat_fac not in [1.1, 1.15]:
                                mat_fac = 1.15
                                mat_fac_error = ' MATERIAL FACTOR MUST BE 1.1 or 1.15 -> using 1.15'

                            boundary_type = obj_scnt_calc_stf.get_puls_boundary()

                            # ---------------------------------------------------------------------
                            # Classification ML prediction
                            # ---------------------------------------------------------------------
                            if boundary_type == 'Int':
                                if self._ML_buckling[mat_fac]['cl SP buc int predictor'] is not None:
                                    x_buc = self._ML_buckling[mat_fac]['cl SP buc int scaler'].transform(
                                        buckling_ml_input
                                    )
                                    y_pred_buc = self._ML_buckling[mat_fac]['cl SP buc int predictor'].predict(
                                        x_buc
                                    )[0]
                                else:
                                    y_pred_buc = 'ML buckling model missing'

                                if self._ML_buckling[mat_fac]['cl SP ult int predictor'] is not None:
                                    x_ult = self._ML_buckling[mat_fac]['cl SP ult int scaler'].transform(
                                        buckling_ml_input
                                    )
                                    y_pred_ult = self._ML_buckling[mat_fac]['cl SP ult int predictor'].predict(
                                        x_ult
                                    )[0]
                                else:
                                    y_pred_ult = 'ML ultimate model missing'

                            else:
                                if self._ML_buckling[mat_fac]['cl SP buc GLGT predictor'] is not None:
                                    x_buc = self._ML_buckling[mat_fac]['cl SP buc GLGT scaler'].transform(
                                        buckling_ml_input
                                    )
                                    y_pred_buc = self._ML_buckling[mat_fac]['cl SP buc GLGT predictor'].predict(
                                        x_buc
                                    )[0]
                                else:
                                    y_pred_buc = 'ML buckling model missing'

                                if self._ML_buckling[mat_fac]['cl SP ult GLGT predictor'] is not None:
                                    x_ult = self._ML_buckling[mat_fac]['cl SP ult GLGT scaler'].transform(
                                        buckling_ml_input
                                    )
                                    y_pred_ult = self._ML_buckling[mat_fac]['cl SP ult GLGT predictor'].predict(
                                        x_ult
                                    )[0]
                                else:
                                    y_pred_ult = 'ML ultimate model missing'

                            # ---------------------------------------------------------------------
                            # Numeric UF pipeline
                            # ---------------------------------------------------------------------
                            try:
                                numeric_pred = self._predict_numeric_uf_pipeline(
                                    mat_fac=mat_fac,
                                    sp_or_up='SP',
                                    boundary_type=boundary_type,
                                    buckling_ml_input=buckling_ml_input,
                                )
                            except Exception as e:
                                numeric_pred = default_numeric_pred.copy()
                                numeric_pred['valid_label'] = 'numeric ML error'
                                numeric_pred['error'] = str(e)

                            numeric_pred = _apply_material_factor_to_numeric_pred(numeric_pred, mat_fac)

                            csr_values, csr_color = self._predict_csr_requirement(
                                obj_scnt_calc_pl,
                                obj_scnt_calc_stf,
                                design_pressure,
                                mat_fac,
                            )

                            if mat_fac == 1.1:
                                accept = 'below or equal 0.91'
                            else:
                                accept = 'below or equal 0.87'

                            return_dict['ML buckling colors'][current_line] = {
                                'buckling': 'green' if y_pred_buc == accept else 'red',
                                'ultimate': 'green' if y_pred_ult == accept else 'red',
                                'CSR requirement': csr_color,
                            }

                            return_dict['ML buckling class'][current_line] = {
                                'buckling': str(y_pred_buc) + mat_fac_error,
                                'ultimate': str(y_pred_ult) + mat_fac_error,
                                'CSR': csr_values,
                            }

                            # ---------------------------------------------------------------------
                            # Numeric UF color handling
                            # ---------------------------------------------------------------------
                            if numeric_pred.get('valid_prediction', None) == 1:
                                numeric_buc_color = self._numeric_uf_color(
                                    numeric_pred['buckling_uf'],
                                    mat_fac,
                                )
                                numeric_ult_color = self._numeric_uf_color(
                                    numeric_pred['ultimate_uf'],
                                    mat_fac,
                                )
                            else:
                                numeric_buc_color = 'red'
                                numeric_ult_color = 'red'

                            return_dict['ML buckling numeric'][current_line] = {
                                'buckling UF': numeric_pred['buckling_uf'],
                                'ultimate UF': numeric_pred['ultimate_uf'],
                                'buckling UF raw': numeric_pred.get('buckling_uf_raw', float('inf')),
                                'ultimate UF raw': numeric_pred.get('ultimate_uf_raw', float('inf')),
                                'material factor': numeric_pred.get('material_factor', mat_fac),
                                'error': numeric_pred['error'],
                            }

                            return_dict['ML buckling numeric valid'][current_line] = {
                                'available': numeric_pred['available'],
                                'valid prediction': numeric_pred['valid_prediction'],
                                'valid label': numeric_pred['valid_label'],
                            }

                            return_dict['ML buckling numeric colors'][current_line] = {
                                'buckling': numeric_buc_color,
                                'ultimate': numeric_ult_color,
                            }

                if selected_buckling_method == 'SemiAnalytical S3/U3':
                    # -------------------------------------------------------------------------
                    # SemiAnalytical solver.
                    #
                    # Store both raw solver UF and material-factored UF. The factored UF is used
                    # for display, colors, and utilization checks, matching ML-Numeric behavior.
                    # -------------------------------------------------------------------------
                    try:
                        semi_analytical_mat_fac = float(self._new_material_factor.get())
                    except Exception:
                        semi_analytical_mat_fac = obj_scnt_calc_pl.mat_factor

                    try:
                        semi_analytical_result = op.semi_analytical.solve_anystructure_panel(
                            [all_obj, None],
                            design_pressure,
                        )
                        semi_analytical_valid = int(semi_analytical_result.get('valid_prediction', 0)) == 1
                    except Exception as e:
                        semi_analytical_result = {
                            'buckling_usage_factor': float('inf'),
                            'ultimate_usage_factor': float('inf'),
                            'panel_family': None,
                            'confidence': 'low',
                        }
                        semi_analytical_valid = False
                        semi_analytical_error = str(e)
                    else:
                        semi_analytical_error = semi_analytical_result.get('invalid_reason') or ''

                    semi_analytical_buc_raw = (
                        float(semi_analytical_result.get('buckling_usage_factor', float('inf')))
                        if semi_analytical_valid else float('inf')
                    )
                    semi_analytical_ult_raw = (
                        float(semi_analytical_result.get('ultimate_usage_factor', float('inf')))
                        if semi_analytical_valid else float('inf')
                    )
                    semi_analytical_buc_uf = semi_analytical_buc_raw * semi_analytical_mat_fac
                    semi_analytical_ult_uf = semi_analytical_ult_raw * semi_analytical_mat_fac
                    semi_analytical_acceptance = 1.0
                    semi_analytical_diagnostics = semi_analytical_result.get('result', {}).get('diagnostics', {})
                    semi_analytical_buckling = semi_analytical_diagnostics.get('buckling', {})
                    semi_analytical_strength = semi_analytical_diagnostics.get('buckling_strength', {})

                    if semi_analytical_valid:
                        semi_analytical_buc_color = self._semi_analytical_uf_color(semi_analytical_buc_uf)
                        semi_analytical_ult_color = self._semi_analytical_uf_color(semi_analytical_ult_uf)
                        semi_analytical_valid_label = semi_analytical_result.get(
                            'valid_label',
                            'valid SemiAnalytical UF predicted',
                        )
                    else:
                        semi_analytical_buc_color = 'red'
                        semi_analytical_ult_color = 'red'
                        semi_analytical_valid_label = semi_analytical_result.get(
                            'valid_label',
                            'SemiAnalytical S3/U3 unsupported or invalid',
                        )

                    return_dict['SemiAnalytical'][current_line] = {
                        'buckling UF': semi_analytical_buc_uf,
                        'ultimate UF': semi_analytical_ult_uf,
                        'buckling UF raw': semi_analytical_buc_raw,
                        'ultimate UF raw': semi_analytical_ult_raw,
                        'material factor': semi_analytical_mat_fac,
                        'acceptance': semi_analytical_acceptance,
                        'panel family': semi_analytical_result.get('panel_family', None),
                        'confidence': semi_analytical_result.get('confidence', None),
                        'error': semi_analytical_error,
                        'controlling limit': semi_analytical_strength.get('controlling_limit', ''),
                        'critical mode': semi_analytical_buckling.get('critical_mode', ''),
                        'critical failure family': semi_analytical_buckling.get('critical_failure_family', ''),
                        'elastic buckling UF raw': semi_analytical_strength.get('elastic_usage_factor', None),
                        'ultimate control UF raw': semi_analytical_strength.get('ultimate_usage_factor', None),
                    }

                    return_dict['SemiAnalytical valid'][current_line] = {
                        'available': semi_analytical_valid,
                        'valid prediction': 1 if semi_analytical_valid else 0,
                        'valid label': semi_analytical_valid_label,
                    }

                    return_dict['SemiAnalytical colors'][current_line] = {
                        'buckling': semi_analytical_buc_color,
                        'ultimate': semi_analytical_ult_color,
                    }

                '''
                Weight calculations for line.
                '''
                # TODO only works for stiffened panel!
                if obj_scnt_calc_stf is not None:
                    line_weight = op.calc_weight([obj_scnt_calc_stf.get_s(), obj_scnt_calc_stf.get_pl_thk(),
                                                  obj_scnt_calc_stf.get_web_h(), obj_scnt_calc_stf.get_web_thk(),
                                                  obj_scnt_calc_stf.get_fl_w(), obj_scnt_calc_stf.get_fl_thk(),
                                                  obj_scnt_calc_stf.span, obj_scnt_calc_stf.girder_lg])
                else:
                    line_weight = 0
                points = self._line_dict[current_line]
                p1 = self._point_dict['point' + str(points[0])]
                p2 = self._point_dict['point' + str(points[1])]

                mid_coord = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]

                return_dict['weights'][current_line] = {'line weight': line_weight, 'mid_coord': mid_coord}

                '''
                xxxxxxx
                '''

                return_dict['buckling'][current_line] = buckling
                return_dict['pressure_uls'][current_line] = design_pressure
                return_dict['pressure_fls'][current_line] = {'p_int': p_int, 'p_ext': p_ext}
                return_dict['section_modulus'][current_line] = {'sec_mod': sec_mod, 'min_sec_mod': 0} if \
                    obj_scnt_calc_stf is None else {'sec_mod': sec_mod, 'min_sec_mod': min_sec_mod}
                return_dict['shear_area'][current_line] = {'shear_area': 0, 'min_shear_area': 0} if \
                    obj_scnt_calc_stf is None else {'shear_area': shear_area, 'min_shear_area': min_shear}
                return_dict['thickness'][current_line] = {'thk': obj_scnt_calc_pl.get_pl_thk(), 'min_thk': min_thk}
                return_dict['fatigue_obj'][current_line] = fatigue_obj
                return_dict['color code'][current_line] = {}

                if fatigue_obj is not None:
                    return_dict['fatigue'][current_line] = {'damage': damage, 'dff': dff,
                                                            'curve': fatigue_obj.get_sn_curve()}
                    rec_for_color[current_line]['fatigue'] = damage * dff
                else:
                    return_dict['fatigue'][current_line] = {'damage': None, 'dff': None, 'curve': None}
                    rec_for_color[current_line]['fatigue'] = 0

                fat_util = 0 if damage is None else damage * dff
                shear_util = 0 if shear_area == 0 else min_shear / shear_area
                thk_util = 0 if obj_scnt_calc_pl.get_pl_thk() == 0 else min_thk / (1000 * obj_scnt_calc_pl.get_pl_thk())
                sec_util = 0 if min(sec_mod) == 0 else min_sec_mod / min(sec_mod)
                buc_util = 1 if float('inf') in buckling else max(all_buckling_uf_list)
                rec_for_color[current_line]['rp buckling'] = max(all_buckling_uf_list)
                # selected_buckling_method set once before the line loop
                semi_analytical_util = buc_util
                if return_dict['SemiAnalytical valid'][current_line].get('valid prediction', None) == 1:
                    if op._puls_selected_method(obj_scnt_calc_pl.get_puls_method()) == 'ultimate':
                        semi_analytical_util = return_dict['SemiAnalytical'][current_line]['ultimate UF']
                    else:
                        semi_analytical_util = return_dict['SemiAnalytical'][current_line]['buckling UF']

                numeric_util = buc_util
                if return_dict['ML buckling numeric valid'][current_line].get('valid prediction', None) == 1:
                    if op._puls_selected_method(obj_scnt_calc_pl.get_puls_method()) == 'ultimate':
                        numeric_util = return_dict['ML buckling numeric'][current_line]['ultimate UF']
                    else:
                        numeric_util = return_dict['ML buckling numeric'][current_line]['buckling UF']

                active_buckling_util = buc_util
                if selected_buckling_method == 'SemiAnalytical S3/U3':
                    active_buckling_util = semi_analytical_util
                elif selected_buckling_method == 'ML-Numeric (PULS based)':
                    active_buckling_util = numeric_util

                return_dict['utilization'][current_line] = {'buckling': buc_util,
                                                            'SemiAnalytical buckling': semi_analytical_util,
                                                            'ML-Numeric buckling': numeric_util,
                                                            'active buckling': active_buckling_util,
                                                            'fatigue': fat_util,
                                                            'section': sec_util,
                                                            'shear': shear_util,
                                                            'thickness': thk_util}

                return_dict['_cache_signature'][current_line] = {
                    'material factor': active_mat_fac,
                    'buckling method': selected_buckling_method,
                }
                # Color coding state
                self._state_logger[current_line] = return_dict  # Logging the current state of the line.
                self._line_to_struc[current_line][0].need_recalc = False
            else:
                pass

        sec_in_model, idx, recorded_sections = dict(), 0, list()
        cyl_sec_in_model, idx_cyl, recorded_cyl_sections = dict(), 0, list()

        for data in self._line_to_struc.values():
            if data[0].Stiffener is not None:
                if data[0].Stiffener.get_beam_string() not in recorded_sections:
                    sec_in_model[data[0].Stiffener.get_beam_string()] = idx
                    recorded_sections.append(data[0].Stiffener.get_beam_string())
                    idx += 1
            if data[5] is not None:
                if data[5].LongStfObj is not None:
                    if data[5].LongStfObj.get_beam_string() not in recorded_cyl_sections:
                        cyl_sec_in_model[data[5].LongStfObj.get_beam_string()] = idx_cyl
                        recorded_cyl_sections.append(data[5].LongStfObj.get_beam_string())
                        idx_cyl += 1

        sec_in_model['length'] = len(recorded_sections)
        cyl_sec_in_model['length'] = len(recorded_cyl_sections)

        if self._line_to_struc != {}:
            state_lines = [
                line for line in self._line_to_struc.keys()
                if line in return_dict.get('all_obj', {})
            ]
            sec_mod_map = np.arange(0, 1.1, 0.1)
            fat_map = np.arange(0, 1.1, 0.1)
            all_thicknesses = [
                round(self._line_to_struc[line][0].Plate.get_pl_thk(), 5)
                for line in state_lines
            ]
            all_thicknesses = np.unique(all_thicknesses).tolist()
            if not all_thicknesses:
                all_thicknesses = [0]

            thickest_plate = max(all_thicknesses)
            if len(all_thicknesses) > 1:
                thk_map = np.arange(min(all_thicknesses), max(all_thicknesses) + (max(all_thicknesses) -
                                                                                  min(all_thicknesses)) / 10,
                                    (max(all_thicknesses) - min(all_thicknesses)) / 10)
            else:
                thk_map = all_thicknesses

            # if self._line_to_struc[current_line][5] is not None:
            #     all_cyl_thk = all_cyl_thk.tolist()
            #     if len(all_cyl_thk) > 1:
            #         thk_map_cyl = np.arange(min(all_cyl_thk), max(all_cyl_thk) + (max(all_cyl_thk) -
            #                                                                           min(all_cyl_thk)) / 10,
            #                             (max(all_cyl_thk) - min(all_cyl_thk)) / 10)
            #     else:
            #         thk_map_cyl = all_cyl_thk
            # else:
            #     thk_map_cyl = [1,]

            pressure_by_line = {}
            for line in state_lines:
                try:
                    pressure_by_line[line] = self.get_highest_pressure(line)['normal']
                except KeyError:
                    pressure_by_line[line] = 0

            all_pressures = np.unique(sorted(pressure_by_line.values())).tolist()
            if all_pressures == []:
                all_pressures = [0, 1]

            highest_pressure, lowest_pressure = max(all_pressures), min(all_pressures)
            if len(all_pressures) > 1:
                press_map = [round(val, 1) for val in
                             np.arange(all_pressures[0], all_pressures[-1],
                                       (all_pressures[-1] - all_pressures[0]) / 10)] + \
                            [round(all_pressures[-1], 1)]
            else:
                press_map = all_pressures

            all_utils = []
            for line in state_lines:
                if self._line_to_struc[line][5] is not None:
                    if line in return_dict['cylinder']:
                        all_utils.append(self._cylinder_buckling_uf(return_dict['cylinder'].get(line, {})))
                else:
                    if line in return_dict['utilization']:
                        all_utils.append(
                            return_dict['utilization'][line].get(
                                'active buckling',
                                max(list(return_dict['utilization'][line].values())),
                            )
                        )
            all_utils = np.unique(all_utils).tolist()
            if not all_utils:
                all_utils = [0]
            if len(all_utils) > 1:
                util_map = np.arange(0, 1.1, 0.1)
            else:
                util_map = all_utils

            sig_x = np.unique([self._line_to_struc[line][0].Plate.sigma_x1 for line in
                               state_lines]).tolist()
            if not sig_x:
                sig_x = [0]
            if len(sig_x) > 1:  # TODO color coding when using sig_x1 and sig_x2 (23.12.2021)
                sig_x_map = np.arange(min(sig_x), max(sig_x) + (max(sig_x) - min(sig_x)) / 10,
                                      (max(sig_x) - min(sig_x)) / 10)
            else:
                sig_x_map = sig_x
            sig_y1 = np.unique([self._line_to_struc[line][0].Plate.sigma_y1 for line in
                                state_lines]).tolist()
            if not sig_y1:
                sig_y1 = [0]
            if len(sig_y1) > 1:
                sig_y1_map = np.arange(min(sig_y1), max(sig_y1) + (max(sig_y1) - min(sig_y1)) / 10,
                                       (max(sig_y1) - min(sig_y1)) / 10)
            else:
                sig_y1_map = sig_y1

            sig_y2 = np.unique([self._line_to_struc[line][0].Plate.sigma_y2 for line in
                                state_lines]).tolist()
            if not sig_y2:
                sig_y2 = [0]
            if len(sig_y2) > 1:

                sig_y2_map = np.arange(min(sig_y2), max(sig_y2) + (max(sig_y2) - min(sig_y2)) / 10,
                                       (max(sig_y2) - min(sig_y2)) / 10)
            else:
                sig_y2_map = sig_y2
            tau_xy = np.unique([self._line_to_struc[line][0].Plate.tau_xy for line in
                                state_lines]).tolist()
            if not tau_xy:
                tau_xy = [0]
            if len(tau_xy) > 1:
                tau_xy_map = np.arange(min(tau_xy), max(tau_xy) + (max(tau_xy) - min(tau_xy)) / 10,
                                       (max(tau_xy) - min(tau_xy)) / 10)
            else:
                tau_xy_map = tau_xy

            spacings = list()
            for line in state_lines:
                if self._line_to_struc[line][0].Stiffener is not None:
                    spacings.append(self._line_to_struc[line][0].Stiffener.get_s())
            spacing = np.unique(spacings).tolist()
            max_spacing = max(spacing) if len(spacing) != 0 else 0
            min_spacing = min(spacing) if len(spacing) != 0 else 0
            structure_type = [self._line_to_struc[line][0].Plate.get_structure_type() for line in
                              state_lines]
            if not structure_type:
                structure_type = ['']

            return_dict['color code'] = {'thickest plate': thickest_plate, 'thickness map': thk_map,
                                         'all thicknesses': all_thicknesses, 'all cyl thicknesses': all_cyl_thk,
                                         'section modulus map': sec_mod_map,
                                         'fatigue map': fat_map,
                                         'highest pressure': highest_pressure, 'lowest pressure': lowest_pressure,
                                         'pressure map': press_map, 'all pressures': all_pressures,
                                         'buckling method': self._new_buckling_method.get(),
                                         'all utilizations': all_utils, 'utilization map': util_map,
                                         'max sigma x': max(sig_x), 'min sigma x': min(sig_x), 'sigma x map': sig_x_map,
                                         'max sigma y1': max(sig_y1), 'min sigma y1': min(sig_y1),
                                         'sigma y1 map': sig_y1_map,
                                         'max sigma y2': max(sig_y2), 'min sigma y2': min(sig_y2),
                                         'sigma y2 map': sig_y2_map,
                                         'max tau xy': max(tau_xy), 'min tau xy': min(tau_xy), 'tau xy map': tau_xy_map,
                                         'structure types map': np.unique(structure_type).tolist(),
                                         'sections in model': sec_in_model,
                                         'cyl sections in model': cyl_sec_in_model,
                                         'recorded sections': recorded_sections,
                                         'recorded cylinder long sections': recorded_cyl_sections,
                                         'spacings': spacing, 'max spacing': max_spacing, 'min spacing': min_spacing}
            line_color_coding = {}
            cmap_sections = plt.get_cmap('jet')
            thk_sort_unique = return_dict['color code']['all thicknesses']
            spacing_sort_unique = return_dict['color code']['spacings']
            structure_type_unique = return_dict['color code']['structure types map']
            tot_weight, weight_mult_dist_x, weight_mult_dist_y = 0, 0, 0
            for line in state_lines:
                line_data = self._line_to_struc[line]
                puls_method = line_data[0].Plate.get_puls_method()
                puls_sp_or_up = line_data[0].Plate.get_puls_sp_or_up()

                # Cylinders
                if self._line_to_struc[line][5] is not None:
                    cyl_obj = self._line_to_struc[line][5]
                    # cyl_radius = round(cyl_obj.ShellObj.radius * 1000, 2)
                    cyl_thickness = round(cyl_obj.ShellObj.thk * 1000, 2)
                    if cyl_obj.LongStfObj is not None:
                        cyl_long_str = cyl_obj.LongStfObj.get_beam_string()
                    else:
                        cyl_long_str = None
                    # cyl_ring_stf = cyl_obj.LongStfObj.get_beam_string()
                    # cyl_heavy_ring = cyl_obj.LongStfObj.get_beam_string()
                    # cyl_span = round(cyl_obj.ShellObj.dist_between_rings, 1)
                    # cyl_tot_length = round(cyl_obj.ShellObj.length_of_shell, 1)
                    # cyl_tot_cyl = round(cyl_obj.ShellObj.tot_cyl_length, 1)
                    # cyl_sigma_axial = cyl_obj.sasd / 1e6
                    # cyl_sigma_bend = cyl_obj.smsd / 1e6
                    # cyl_sigma_tors = cyl_obj.tTsd / 1e6
                    tau_xy = cyl_obj.tQsd / 1e6
                    # cyl_lat_press = cyl_obj.psd / 1e6
                    # cyl_sigma_hoop = cyl_obj.shsd / 1e6
                    cyl_results = cyl_obj.get_utilization_factors()

                    cyl_uf = self._cylinder_buckling_uf(cyl_results)
                else:
                    cyl_uf = 0
                    cyl_long_str = None
                    cyl_thickness = None

                rp_uf = rec_for_color[line]['rp buckling']

                tot_uf_rp = max([rec_for_color[line]['fatigue'], rp_uf,
                                 rec_for_color[line]['section modulus'], rec_for_color[line]['shear'],
                                 rec_for_color[line]['plate thickness']])
                this_pressure = pressure_by_line.get(line, 0)
                rp_util = max(list(return_dict['utilization'][line].values()))

                res = list()

                for stress_list, this_stress in zip([sig_x, sig_y1, sig_y2, tau_xy],
                                                    [line_data[0].Plate.sigma_x1, line_data[0].Plate.sigma_y1,
                                                     line_data[0].Plate.sigma_y2, line_data[0].Plate.tau_xy]):
                    if type(stress_list) == float:
                        res.append(1)
                    elif len(stress_list) == 1:
                        res.append(1)
                    elif max(stress_list) == 0 and min(stress_list) == 0:
                        res.append(0)
                    elif this_stress < 0:
                        res.append(this_stress / min(stress_list))
                    elif this_stress >= 0:
                        res.append(this_stress / max(stress_list))

                sig_x_uf, sig_y1_uf, sig_y2_uf, tau_xy_uf = res
                if type(all_cyl_thk) is not list:
                    all_cyl_thk = all_cyl_thk.tolist()

                def _safe_numeric_color_position(values, target):
                    """Return a stable 0..1 position for imported values with float noise."""
                    if not values:
                        return 0.0
                    try:
                        numeric_values = [float(value) for value in values]
                        target_value = float(target)
                    except (TypeError, ValueError):
                        try:
                            return values.index(target) / max(len(values), 1)
                        except ValueError:
                            return 0.0
                    nearest_index = min(
                        range(len(numeric_values)),
                        key=lambda index: abs(numeric_values[index] - target_value),
                    )
                    return nearest_index / max(len(numeric_values), 1)

                line_color_coding[line] = {'plate': matplotlib.colors.rgb2hex(cmap_sections(
                    _safe_numeric_color_position(thk_sort_unique, line_data[0].Plate.get_pl_thk()))),
                    'spacing': 'black' if line_data[0].Stiffener is None else matplotlib.colors.rgb2hex(
                        cmap_sections(_safe_numeric_color_position(
                            spacing_sort_unique, line_data[0].Stiffener.get_s()))),
                    'section': 'black' if line_data[0].Stiffener is None else
                    matplotlib.colors.rgb2hex(cmap_sections(sec_in_model[line_data[0]
                                                            .Stiffener.get_beam_string()] /
                                                            len(list(recorded_sections)))),
                    'section cyl': 'black' if cyl_long_str is None else
                    matplotlib.colors.rgb2hex(cmap_sections(cyl_sec_in_model[cyl_long_str] /
                                                            len(list(recorded_cyl_sections)))),
                    'structure type': matplotlib.colors.rgb2hex(
                        cmap_sections(structure_type_unique.index(line_data[0].Plate.get_structure_type())
                                      / len(structure_type_unique))),
                    'pressure color': 'black' if all_pressures in [[0], [0, 1]] else matplotlib.colors.rgb2hex(
                        cmap_sections(
                            this_pressure / highest_pressure)),
                    'pressure': this_pressure,
                    'rp uf color': matplotlib.colors.rgb2hex(cmap_sections(rp_util)),
                    'rp uf': rp_util,
                    'Buckling method': puls_method,
                    'Buckling SP/UP': puls_sp_or_up,
                    'section modulus color': matplotlib.colors.rgb2hex(
                        cmap_sections(rec_for_color[line]['section modulus'])),
                    'fatigue color': matplotlib.colors.rgb2hex(
                        cmap_sections(rec_for_color[line]['fatigue'])),
                    'Total uf color rp': matplotlib.colors.rgb2hex(
                        cmap_sections(tot_uf_rp)),
                    'Total uf rp': tot_uf_rp,
                    'fatigue uf': rec_for_color[line]['fatigue'],
                    'section uf': rec_for_color[line]['section modulus'],
                    'sigma x': matplotlib.colors.rgb2hex(cmap_sections(sig_x_uf)),
                    'sigma y1': matplotlib.colors.rgb2hex(cmap_sections(sig_y1_uf)),
                    'sigma y2': matplotlib.colors.rgb2hex(cmap_sections(sig_y2_uf)),
                    'tau xy': matplotlib.colors.rgb2hex(cmap_sections(tau_xy_uf)),
                    'cylinder uf': matplotlib.colors.rgb2hex(cmap_sections(cyl_uf)),
                    'cylinder uf value': cyl_uf,
                    'cylinder plate': matplotlib.colors.rgb2hex
                    (cmap_sections(0 if cyl_thickness is None else all_cyl_thk.index(cyl_thickness) / len(all_cyl_thk)))

                }
                return_dict['color code']['lines'] = line_color_coding

                # COG calculations
                # Steel
                tot_weight += return_dict['weights'][line]['line weight']
                weight_mult_dist_x += return_dict['weights'][line]['line weight'] \
                                      * return_dict['weights'][line]['mid_coord'][0]
                weight_mult_dist_y += return_dict['weights'][line]['line weight'] \
                                      * return_dict['weights'][line]['mid_coord'][1]

            tot_cog = [0, 0] if tot_weight == 0 else [weight_mult_dist_x / tot_weight,
                                                      weight_mult_dist_y / tot_weight]
        else:
            tot_cog = [0, 0]
            tot_weight = 0

        return_dict['COG'] = tot_cog
        return_dict['Total weight'] = tot_weight

        # Store the completed full-state object for each line. This avoids
        # caching a partially populated state when some lines were recalculated
        # before the global color-code/COG part was built.
        for line_name in self._line_to_struc.keys():
            if line_name in return_dict.get('all_obj', {}):
                self._state_logger[line_name] = return_dict

        return return_dict

    def _fea_panel_canvas_color(self, panel, index):
        if not bool(self._fea_color_code.get()):
            return '#cfd6df'
        if panel is not None and panel.usage_factor is not None:
            uf_min, uf_max = self._fea_uf_color_limits()
            value = max(min(float(panel.usage_factor), uf_max), uf_min)
            if hasattr(tkinter_3d_canvas, '_interpolate_thickness_color'):
                return tkinter_3d_canvas._interpolate_thickness_color(value, uf_min, uf_max)
            rgba = plt.get_cmap('jet')((value - uf_min) / max(uf_max - uf_min, 1.0e-9))
            return matplotlib.colors.rgb2hex(rgba)
        return '#d9d9d9'

    def _fea_uf_color_limits(self):
        try:
            lower = float(self._fea_uf_color_lower.get())
        except Exception:
            lower = 0.0
        try:
            upper = float(self._fea_uf_color_upper.get())
        except Exception:
            upper = 1.5
        if not math.isfinite(lower):
            lower = 0.0
        if not math.isfinite(upper):
            upper = 1.5
        if upper <= lower:
            upper = lower + 1.0
        return lower, upper

    def _create_main_3d_viewer(self, parent, **options):
        viewer = create_3d_viewer(
            parent,
            backend=self._renderer_requested,
            **options,
        )
        self._renderer_backend_status.set("Renderer: " + backend_diagnostic(viewer))
        return viewer

    def _add_renderer_selector(self, parent):
        selector = ttk.Combobox(
            parent,
            textvariable=self._renderer_backend_choice,
            values=tuple(BACKEND_LABELS),
            state="readonly",
            width=17,
        )
        selector.pack(side=tk.LEFT, padx=(8, 3))
        selector.bind("<<ComboboxSelected>>", self._switch_main_renderer_backend)
        return selector

    def _main_renderer_specs(self):
        specs = []
        fea = getattr(self, '_fea_tk3d_canvas', None)
        if fea is not None and getattr(self, '_prop_3d_frame', None) is not None:
            specs.append((
                '_fea_tk3d_canvas',
                self._prop_3d_frame,
                lambda canvas: self._populate_fea_buckling_tk3d_canvas(
                    fit_view=False, canvas=canvas
                ),
                True,
            ))
        prop = getattr(self, '_prop_3d_tk3d_canvas', None)
        if prop is not None and getattr(self, '_prop_3d_frame', None) is not None:
            items = list(getattr(self, '_prop_3d_tk3d_items', ()) or ())
            mesh = getattr(self, '_prop_3d_export_mesh', None)

            def populate(candidate, values=items, fallback_mesh=mesh):
                candidate.set_axis_ruler(True)
                candidate.set_mesh_lines(True)
                if values:
                    self._populate_prop_3d_tk3d_native(candidate, values)
                elif fallback_mesh:
                    self._populate_prop_3d_tk3d_faces(candidate, fallback_mesh)

            specs.append((
                '_prop_3d_tk3d_canvas', self._prop_3d_frame, populate, False
            ))
        return specs

    def _register_runtime_fem_window(self, runtime_window):
        """Register a live FEM popup for application-wide renderer changes."""

        self._runtime_fem_windows.add(runtime_window)

    def _live_runtime_fem_windows(self):
        windows = []
        for runtime_window in tuple(self._runtime_fem_windows):
            native = getattr(runtime_window, 'window', None)
            try:
                if native is not None and not bool(native.winfo_exists()):
                    continue
            except Exception:
                pass
            windows.append(runtime_window)
        return windows

    def _switch_runtime_fem_viewers(self, requested, previous):
        """Switch registered FEM popups, rolling back the group on failure."""

        switched = []
        for runtime_window in self._live_runtime_fem_windows():
            current = normalize_backend(
                getattr(runtime_window, '_renderer_requested', previous)
            )
            if current == requested:
                continue
            runtime_window.renderer_backend_choice.set(BACKEND_NAMES[requested])
            if not runtime_window._switch_renderer_backend(
                _application_coordinated=True
            ):
                for completed, original in reversed(switched):
                    completed.renderer_backend_choice.set(BACKEND_NAMES[original])
                    completed._switch_renderer_backend(
                        _application_coordinated=True
                    )
                raise RuntimeError(
                    "a Runtime FEM viewer could not switch renderer"
                )
            switched.append((runtime_window, current))
        return switched

    @staticmethod
    def _rollback_runtime_fem_viewers(switched):
        for runtime_window, original in reversed(switched):
            try:
                runtime_window.renderer_backend_choice.set(BACKEND_NAMES[original])
                runtime_window._switch_renderer_backend(
                    _application_coordinated=True
                )
            except Exception:
                pass

    def _switch_renderer_backend_from_runtime(self, _source, requested):
        """Route a popup selector through the application-wide transaction."""

        previous_label = self._renderer_backend_choice.get()
        self._renderer_backend_choice.set(BACKEND_NAMES[normalize_backend(requested)])
        if self._switch_main_renderer_backend():
            return True
        self._renderer_backend_choice.set(previous_label)
        return False

    def _switch_main_renderer_backend(self, _event=None):
        previous = self._renderer_requested
        requested = normalize_backend(self._renderer_backend_choice.get())
        if requested == previous:
            return True
        switched_runtime = []
        try:
            switched_runtime = self._switch_runtime_fem_viewers(
                requested, previous
            )
        except Exception as error:
            self._renderer_requested = previous
            self._renderer_backend_choice.set(BACKEND_NAMES[previous])
            self._renderer_backend_status.set(
                "Renderer switch failed: " + str(error)
            )
            return False
        specs = self._main_renderer_specs()
        if not specs:
            self._renderer_requested = requested
            self._renderer_backend_status.set(
                "Renderer: " + BACKEND_NAMES[requested] + " (next 3D view)"
            )
            return True

        candidates = []
        try:
            for attribute, parent, populate, bind_fea in specs:
                old = getattr(self, attribute)
                width, height = viewport_size(old)
                candidate = create_3d_viewer(
                    parent,
                    backend=requested,
                    width=width,
                    height=height,
                    bg=str(getattr(old, 'bg', 'white')),
                )
                try:
                    state = export_view_state(old)
                    populate(candidate)
                    apply_view_state(candidate, state, redraw=False)
                    candidate.redraw()
                except Exception:
                    candidate.destroy()
                    raise
                candidates.append((attribute, old, candidate, bind_fea))

            for attribute, old, candidate, bind_fea in candidates:
                old.pack_forget()
                candidate.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
                setattr(self, attribute, candidate)
                if attribute == '_fea_tk3d_canvas':
                    self._fea_tk3d_canvas = candidate
                    self._prop_3d_canvas_widget = event_widget(candidate)
                elif attribute == '_prop_3d_tk3d_canvas':
                    self._prop_3d_tk3d_canvas = candidate
                    self._prop_3d_canvas_widget = event_widget(candidate)
                if bind_fea:
                    native = event_widget(candidate)
                    native.bind('<ButtonPress-1>', self._on_fea_tk3d_mouse_press, add='+')
                    native.bind('<ButtonRelease-1>', self._on_fea_tk3d_mouse_release, add='+')
                old.destroy()
            self._renderer_requested = requested
            actual = ', '.join(sorted({
                backend_diagnostic(candidate)
                for _attribute, _old, candidate, _bind in candidates
            }))
            self._renderer_backend_status.set("Renderer: " + actual)
            return True
        except Exception as error:
            for _attribute, _old, candidate, _bind in candidates:
                try:
                    candidate.destroy()
                except Exception:
                    pass
            self._rollback_runtime_fem_viewers(switched_runtime)
            self._renderer_requested = previous
            self._renderer_backend_choice.set(BACKEND_NAMES[previous])
            self._renderer_backend_status.set("Renderer switch failed: " + str(error))
            messagebox.showerror(
                "Renderer unavailable",
                "The working 3D view was kept unchanged.\n\n" + str(error),
                parent=self._parent,
            )
            return False

    def _embed_fea_buckling_tk3d_canvas(self, records, default_view='iso'):
        """Embed the selected shared FE buckling viewer in the main drawing pane."""
        self._prop_3d_axes = None
        self._prop_3d_fig_canvas = None
        self._prop_3d_toolbar = None
        self._prop_3d_default_view = default_view
        self._fea_tk3d_panel_records = {
            record.get('field_id'): record
            for record in records
            if record.get('field_id') is not None
        }

        place = {
            'relx': self._place_info_float(self._main_canvas, 'relx', 0.26),
            'rely': self._place_info_float(self._main_canvas, 'rely', 0),
            'relwidth': self._place_info_float(self._main_canvas, 'relwidth', 0.523),
            'relheight': self._place_info_float(self._main_canvas, 'relheight', 0.73),
        }
        self._prop_3d_frame = tk.Frame(
            self._main_fr,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        self._prop_3d_frame.place(**place)
        tk.Misc.lift(self._prop_3d_frame)

        toolbar_row = tk.Frame(
            self._prop_3d_frame,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        toolbar_row.pack(side=tk.TOP, fill=tk.X)

        view_row = tk.Frame(toolbar_row, background=self._style.lookup('TFrame', 'background'), bd=0,
                            highlightthickness=0)
        view_row.pack(side=tk.RIGHT)
        self._add_renderer_selector(view_row)
        ttk.Button(view_row, text='Iso', width=4,
                   command=lambda: self._set_fea_tk3d_view('iso')).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Top', width=4,
                   command=lambda: self._set_fea_tk3d_view('top')).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Side', width=5,
                   command=lambda: self._set_fea_tk3d_view('side')).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Fit', width=4,
                   command=lambda: self._fit_fea_tk3d_canvas()).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Import', width=7, command=self.open_fea_buckling_files).pack(side=tk.LEFT,
                                                                                                 padx=(8, 0))
        ttk.Button(view_row, text='Reimport', width=8, command=self.reimport_fea_buckling_files).pack(side=tk.LEFT)

        width = max(int(self._main_canvas.winfo_width() or 900), 300)
        height = max(int(self._main_canvas.winfo_height() or 600), 220)
        tk3d = self._create_main_3d_viewer(
            self._prop_3d_frame,
            width=width,
            height=height,
            bg='white',
        )
        self._fea_tk3d_canvas = tk3d
        self._prop_3d_canvas_widget = event_widget(tk3d)
        tk3d.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        event_widget(tk3d).bind('<ButtonPress-1>', self._on_fea_tk3d_mouse_press, add='+')
        event_widget(tk3d).bind('<ButtonRelease-1>', self._on_fea_tk3d_mouse_release, add='+')
        self._populate_fea_buckling_tk3d_canvas(fit_view=True)

    def _set_fea_tk3d_view(self, view_name):
        tk3d = getattr(self, '_fea_tk3d_canvas', None)
        if tk3d is None:
            return
        try:
            if view_name == 'top':
                tk3d.set_top_view()
            elif view_name == 'side':
                tk3d.set_side_view()
            else:
                tk3d.set_iso_view()
        except Exception:
            pass

    def _fit_fea_tk3d_canvas(self):
        tk3d = getattr(self, '_fea_tk3d_canvas', None)
        if tk3d is None:
            return
        try:
            tk3d.fit_to_scene(padding=1.18)
        except Exception:
            pass

    def _populate_fea_buckling_tk3d_canvas(self, fit_view=False, canvas=None):
        tk3d = canvas if canvas is not None else getattr(self, '_fea_tk3d_canvas', None)
        session = self._fea_buckling_session
        if tk3d is None or session is None:
            return
        try:
            tk3d.clear()
        except Exception:
            return
        try:
            if self._fea_color_code.get():
                uf_min, uf_max = self._fea_uf_color_limits()
                tk3d.set_thickness_legend(
                    list(session.usage_factors().values()),
                    unit='',
                    title='UF',
                    width=125,
                    value_range=(uf_min, uf_max),
                )
            else:
                tk3d.clear_thickness_legend()
        except Exception:
            pass

        original_request_redraw = getattr(tk3d, '_request_redraw', None)
        if callable(original_request_redraw):
            tk3d._request_redraw = lambda: None

        for field_id, record in getattr(self, '_fea_tk3d_panel_records', {}).items():
            try:
                panel = session.panel(field_id)
            except Exception:
                panel = None
            selected = field_id == self._fea_selected_panel_id
            color = '#ffd54f' if selected else self._fea_panel_canvas_color(panel, record.get('index', 0))
            outline = 'red' if selected else ('#333333' if self._fea_show_mesh.get() else '')
            width = 2 if selected else (1 if self._fea_show_mesh.get() else 0)
            layer = 45 if selected else 5
            for polygon in record.get('polygons', []):
                vertices = [tkinter_3d_canvas.Point3D(point[0], point[1], point[2]) for point in polygon]
                tk3d.add_polygon(
                    vertices,
                    color=color,
                    outline=outline,
                    width=width,
                    cull_backface=False,
                    layer=layer,
                    tags=f'feapanel_{field_id}',
                )
            label_parts = []
            if self._fea_show_panel_text.get():
                label_parts.append(field_id.replace('field_', '').replace('cyl_', ''))
            if self._fea_show_uf_text.get() and panel is not None and panel.usage_factor is not None:
                label_parts.append(f'UF {panel.usage_factor:.2f}')
            if label_parts:
                centroid = record.get('centroid', (0.0, 0.0, 0.0))
                normal = record.get('normal', (0.0, 0.0, 1.0))
                tk3d.add_text(
                    tkinter_3d_canvas.Point3D(
                        centroid[0] + normal[0] * 0.03,
                        centroid[1] + normal[1] * 0.03,
                        centroid[2] + normal[2] * 0.03,
                    ),
                    '\n'.join(label_parts),
                    color='#111111',
                    layer=60,
                )
            self._add_fea_tk3d_local_axes(record, canvas=tk3d)

        if callable(original_request_redraw):
            tk3d._request_redraw = original_request_redraw
        invalidate = getattr(tk3d, '_invalidate_geometry_cache', None)
        if callable(invalidate):
            invalidate()
        tk3d.redraw()

        if fit_view:
            try:
                tk3d.after_idle(lambda: tk3d.fit_to_scene(padding=1.18))
            except Exception:
                self._fit_fea_tk3d_canvas()

    def _add_fea_tk3d_local_axes(self, record, canvas=None):
        tk3d = canvas if canvas is not None else getattr(self, '_fea_tk3d_canvas', None)
        if tk3d is None:
            return
        show_x = bool(self._fea_show_local_x_arrow.get())
        show_y = bool(self._fea_show_local_y_arrow.get())
        if not show_x and not show_y:
            return
        centroid = record.get('centroid', (0.0, 0.0, 0.0))
        normal = record.get('normal', (0.0, 0.0, 1.0))
        arrow_length = max(min(float(record.get('span_m', record.get('axial_length_m', 1.0))),
                               float(record.get('spacing_m', record.get('circumferential_spacing_m', 1.0)))) * 0.28,
                           0.05)
        origin = (
            centroid[0] + normal[0] * 0.02,
            centroid[1] + normal[1] * 0.02,
            centroid[2] + normal[2] * 0.02,
        )
        origin_point = tkinter_3d_canvas.Point3D(*origin)
        if show_x:
            local_x = record.get('local_x', (1.0, 0.0, 0.0))
            tk3d.add_line(
                origin_point,
                tkinter_3d_canvas.Point3D(
                    origin[0] + local_x[0] * arrow_length,
                    origin[1] + local_x[1] * arrow_length,
                    origin[2] + local_x[2] * arrow_length,
                ),
                color='#1f77b4',
                width=2,
                layer=55,
            )
        if show_y:
            local_y = record.get('local_y', (0.0, 1.0, 0.0))
            tk3d.add_line(
                origin_point,
                tkinter_3d_canvas.Point3D(
                    origin[0] + local_y[0] * arrow_length,
                    origin[1] + local_y[1] * arrow_length,
                    origin[2] + local_y[2] * arrow_length,
                ),
                color='#ff7f0e',
                width=2,
                layer=55,
            )

    def _on_fea_tk3d_mouse_press(self, event):
        self._fea_tk3d_click_origin = (event.x, event.y)

    def _on_fea_tk3d_mouse_release(self, event):
        origin = getattr(self, '_fea_tk3d_click_origin', None)
        self._fea_tk3d_click_origin = None
        if origin is None:
            return
        if math.hypot(event.x - origin[0], event.y - origin[1]) > 5.0:
            return
        field_id = self._pick_fea_tk3d_panel(event.x, event.y)
        if field_id:
            self._select_fea_panel(field_id)

    def _pick_fea_tk3d_panel(self, x, y):
        tk3d = getattr(self, '_fea_tk3d_canvas', None)
        if tk3d is None:
            return None
        picker = getattr(tk3d, 'pick_at', None)
        if callable(picker):
            tag = picker(int(x), int(y))
            if tag and str(tag).startswith('feapanel_'):
                return str(tag).replace('feapanel_', '')
            return None
        widget = event_widget(tk3d)
        item_ids = widget.find_overlapping(x, y, x, y)
        for item_id in reversed(item_ids):
            tags = widget.gettags(item_id)
            for tag in tags:
                if tag.startswith('feapanel_'):
                    return tag.replace('feapanel_', '')
        return None

    @staticmethod
    def _point_in_screen_polygon(x, y, polygon):
        inside = False
        count = len(polygon)
        if count < 3:
            return False
        previous_x, previous_y = polygon[-1]
        for current_x, current_y in polygon:
            intersects = (
                (current_y > y) != (previous_y > y)
                and x < (previous_x - current_x) * (y - current_y) / (previous_y - current_y + 1.0e-12) + current_x
            )
            if intersects:
                inside = not inside
            previous_x, previous_y = current_x, current_y
        return inside

    def _embed_fea_buckling_3d_figure(self, fig, ax, default_view=(24, -55)):
        """Embed the FEA buckling-panel-only 3D view in the main drawing pane."""
        self._prop_3d_axes = ax
        self._prop_3d_default_view = default_view
        self._disable_prop_3d_artist_clipping(ax)

        place = {
            'relx': self._place_info_float(self._main_canvas, 'relx', 0.26),
            'rely': self._place_info_float(self._main_canvas, 'rely', 0),
            'relwidth': self._place_info_float(self._main_canvas, 'relwidth', 0.523),
            'relheight': self._place_info_float(self._main_canvas, 'relheight', 0.73),
        }
        self._prop_3d_frame = tk.Frame(
            self._main_fr,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        self._prop_3d_frame.place(**place)
        tk.Misc.lift(self._prop_3d_frame)

        toolbar_row = tk.Frame(
            self._prop_3d_frame,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        toolbar_row.pack(side=tk.TOP, fill=tk.X)
        self._prop_3d_fig_canvas = FigureCanvasTkAgg(fig, master=self._prop_3d_frame)
        self._prop_3d_fig_canvas.draw()
        self._fea_pick_cid = self._prop_3d_fig_canvas.mpl_connect(
            'pick_event',
            self._on_fea_buckling_panel_pick,
        )

        self._prop_3d_toolbar = NavigationToolbar2Tk(self._prop_3d_fig_canvas, toolbar_row, pack_toolbar=False)
        self._prop_3d_toolbar.update()
        self._prop_3d_toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        view_row = tk.Frame(toolbar_row, background=self._style.lookup('TFrame', 'background'), bd=0,
                            highlightthickness=0)
        view_row.pack(side=tk.RIGHT)
        ttk.Button(view_row, text='Iso', width=4,
                   command=lambda: self._set_prop_3d_view(default_view[0], default_view[1])).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Top', width=4,
                   command=lambda: self._set_prop_3d_view(90, -90)).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Side', width=5,
                   command=lambda: self._set_prop_3d_view(0, -90)).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Import', width=7, command=self.open_fea_buckling_files).pack(side=tk.LEFT,
                                                                                                 padx=(8, 0))
        ttk.Button(view_row, text='Reimport', width=8, command=self.reimport_fea_buckling_files).pack(side=tk.LEFT)

        self._prop_3d_canvas_widget = self._prop_3d_fig_canvas.get_tk_widget()
        self._prop_3d_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._prop_3d_canvas_widget.bind('<MouseWheel>', self._prop_3d_mouse_scroll)
        self._prop_3d_canvas_widget.bind('<Button-4>', self._prop_3d_mouse_scroll)
        self._prop_3d_canvas_widget.bind('<Button-5>', self._prop_3d_mouse_scroll)
        self._prop_3d_frame.bind('<Configure>', self._schedule_resize_prop_3d_figure)
        self._prop_3d_frame.after(50, self._resize_prop_3d_figure)

    def _select_fea_panel_after_matplotlib_event(self, field_id):
        """Select a panel after Matplotlib has finished its current mouse callback."""
        if getattr(self, '_fea_pick_after_id', None) is not None:
            try:
                self._parent.after_cancel(self._fea_pick_after_id)
            except Exception:
                pass
            self._fea_pick_after_id = None

        def select_panel():
            self._fea_pick_after_id = None
            self._select_fea_panel(field_id)

        try:
            self._fea_pick_after_id = self._parent.after_idle(select_panel)
        except Exception:
            self._select_fea_panel(field_id)

    def _on_fea_buckling_panel_pick(self, event):
        field_id = None
        try:
            field_id = event.artist.get_gid()
        except Exception:
            field_id = None
        if field_id and field_id != '__selected_fea_panel_overlay__':
            self._select_fea_panel_after_matplotlib_event(field_id)

    def _update_fea_3d_selection(self):
        """Update panel highlighting in place so the user's 3D view is preserved."""
        session = self._fea_buckling_session
        if session is None:
            return
        if getattr(self, '_fea_tk3d_canvas', None) is not None:
            self._populate_fea_buckling_tk3d_canvas(fit_view=False)
            return
        try:
            overlay = getattr(self, '_fea_3d_selected_overlay', None)
            if overlay is not None:
                overlay.remove()
        except Exception:
            pass
        self._fea_3d_selected_overlay = None
        for field_id, collection in getattr(self, '_fea_3d_panel_artists', {}).items():
            selected = field_id == self._fea_selected_panel_id
            try:
                collection.set_edgecolor('red' if selected else ('#333333' if self._fea_show_mesh.get() else 'none'))
                collection.set_linewidth(1.8 if selected else (0.25 if self._fea_show_mesh.get() else 0.0))
                collection.set_alpha(0.42 if selected else 0.82)
            except Exception:
                pass
        record = getattr(self, '_fea_3d_panel_records', {}).get(self._fea_selected_panel_id)
        ax = getattr(self, '_prop_3d_axes', None)
        if record is not None and ax is not None:
            try:
                overlay = Poly3DCollection(
                    record.get('polygons', []),
                    facecolor=(1.0, 0.78, 0.15, 0.28),
                    edgecolor='red',
                    linewidth=2.2,
                    alpha=0.95,
                )
                overlay.set_gid('__selected_fea_panel_overlay__')
                overlay.set_picker(False)
                try:
                    overlay.set_zorder(1000)
                except Exception:
                    pass
                ax.add_collection3d(overlay)
                self._fea_3d_selected_overlay = overlay
                self._disable_prop_3d_artist_clipping(ax)
            except Exception:
                self._fea_3d_selected_overlay = None
        try:
            self._prop_3d_fig_canvas.draw_idle()
        except Exception:
            pass

    def _draw_fea_panel_result_text(self):
        """Show the selected FE panel using the existing ANYstructure result printer."""
        self._result_canvas.delete('all')
        session = self._fea_buckling_session
        if session is None or self._fea_selected_panel_id is None:
            self._result_canvas.create_text(
                8,
                8,
                text='No FEA buckling panel selected',
                anchor=tk.NW,
                font=self._text_size['Text 8 bold'],
                fill=self._color_text,
            )
            return
        try:
            panel = session.panel(self._fea_selected_panel_id)
        except KeyError:
            return

        self._draw_fea_panel_existing_result_text(panel)

    def _draw_fea_panel_existing_result_text(self, panel):
        temp_line = '__fea_selected_panel__'
        mapped_line = getattr(self, '_fea_panel_line_by_field', {}).get(panel.field_id)
        flat_method_print = self._new_buckling_method.get() in [
            'SemiAnalytical S3/U3',
            'ML-Numeric (PULS based)',
        ]
        old_active_line = self._active_line
        old_line_is_active = self._line_is_active
        old_fea_mode = self._fea_buckling_mode
        old_line = self._line_dict.get(temp_line)
        old_bundle = self._line_to_struc.get(temp_line)
        old_load_keys = {
            key: value for key, value in self._new_load_comb_dict.items()
            if len(key) > 1 and key[1] == temp_line
        }
        try:
            if mapped_line in self._line_dict and mapped_line in self._line_to_struc:
                result_line = mapped_line
            else:
                all_obj = self._fea_panel_all_structure()
                cylinder_obj = self._fea_panel_cylinder_structure(panel)
                pressure_mpa = self._fea_panel_pressure_mpa(panel)
                self._point_dict.setdefault('point999991', [0.0, 0.0])
                self._point_dict.setdefault('point999992', [max(panel.field.span_m, 1.0), 0.0])
                self._line_dict[temp_line] = [999991, 999992]
                project_services.LineStructureService(self._line_to_struc).assign_structure(
                    temp_line,
                    all_obj,
                    cylinder=cylinder_obj,
                )
                self._new_load_comb_dict[('manual', temp_line, 'manual')] = [
                    tk.DoubleVar(value=pressure_mpa * 1.0e6),
                    tk.DoubleVar(value=1.0),
                    tk.IntVar(value=1),
                ]
                result_line = temp_line

            self._active_line = result_line
            self._line_is_active = True
            if result_line == temp_line:
                self._line_to_struc[result_line][0].need_recalc = True
            old_result_bundle = None
            if flat_method_print and result_line in self._line_to_struc:
                old_result_bundle = list(self._line_to_struc[result_line])
                self._line_to_struc[result_line] = list(self._line_to_struc[result_line])
                self._line_to_struc[result_line][5] = None
            try:
                state = self.get_color_and_calc_state(current_line=result_line, active_line_only=True)
                self._fea_buckling_mode = False
                self.draw_results(state=state)
            finally:
                if old_result_bundle is not None:
                    self._line_to_struc[result_line] = old_result_bundle
        except Exception as err:
            self._result_canvas.delete('all')
            self._result_canvas.create_text(
                8,
                8,
                text='FEA result print unavailable: ' + str(err),
                anchor=tk.NW,
                font=self._text_size['Text 8 bold'],
                fill='red',
            )
        finally:
            self._fea_buckling_mode = old_fea_mode
            self._active_line = old_active_line
            self._line_is_active = old_line_is_active
            self._state_logger.pop(temp_line, None)
            for key in [key for key in self._new_load_comb_dict if len(key) > 1 and key[1] == temp_line]:
                self._new_load_comb_dict.pop(key, None)
            self._new_load_comb_dict.update(old_load_keys)
            if old_line is None:
                self._line_dict.pop(temp_line, None)
            else:
                self._line_dict[temp_line] = old_line
            if old_bundle is None:
                self._line_to_struc.pop(temp_line, None)
            else:
                self._line_to_struc[temp_line] = old_bundle

    def _fea_panel_all_structure(self):
        old_domain = self._new_calculation_domain.get()
        try:
            if not self._is_flat_calculation_domain(old_domain):
                self._new_calculation_domain.set('Flat plate, stiffened with girder')
            prop_dict, _section_dict = self._build_flat_structure_properties()
            return self._create_all_structure_from_properties(prop_dict)
        finally:
            self._new_calculation_domain.set(old_domain)

    def _fea_panel_cylinder_structure(self, panel):
        if not isinstance(getattr(panel, 'anystructure_input', {}).get('shell'), dict):
            return None
        cylinder_obj, *_rest = self._build_cylinder_structure_properties()
        return cylinder_obj

    @staticmethod
    def _fea_panel_pressure_mpa(panel):
        """Return pressure found for the FE panel, defaulting to zero to avoid double counting.

        FRD stresses are already reduced from an analysis result.  Until an
        explicit pressure-load extractor is added, buckling is run with the FE
        stresses and zero lateral pressure.
        """
        try:
            value = (
                panel.anystructure_input.get('loads', {}).get(
                    'pressure_mpa',
                    panel.anystructure_input.get('stresses', {}).get('pressure_mpa', 0.0),
                )
            )
        except Exception:
            value = 0.0
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return value if math.isfinite(value) else 0.0

    def _draw_fea_panel_2d_sketch(self):
        """Draw the selected FE panel using the existing flat-panel 2D style."""
        self._prop_canvas.delete('all')
        width = max(int(self._prop_canvas.winfo_width() or 360), 1)
        height = max(int(self._prop_canvas.winfo_height() or 260), 1)
        session = self._fea_buckling_session
        if session is None or self._fea_selected_panel_id is None:
            self._prop_canvas.create_text(
                width / 2,
                height / 2,
                text='Select an FEA buckling panel',
                font=self._text_size['Text 10 bold'],
                fill=self._color_text,
            )
            return
        try:
            panel = session.panel(self._fea_selected_panel_id)
        except KeyError:
            return

        try:
            all_obj = self._fea_panel_all_structure()
        except Exception as err:
            self._prop_canvas.create_text(
                width / 2,
                height / 2,
                text='2D panel preview unavailable: ' + str(err),
                font=self._text_size['Text 8 bold'],
                fill='red',
            )
            return

        self._draw_flat_structure_2d_preview(
            all_obj,
            selected_text='Selected FEA buckling panel: ' + str(panel.field_id),
        )

    def _draw_flat_structure_2d_preview(self, all_obj, selected_text=''):
        canvas_width = max(int(self._prop_canvas.winfo_width() or 360), 1)
        canvas_height = max(int(self._prop_canvas.winfo_height() or 260), 1)
        self._prop_canvas.create_text(
            [canvas_width / 2 - canvas_width / 20, canvas_height / 20],
            text=selected_text,
            font=self._text_size["Text 10 bold"],
            fill='red',
        )
        if all([all_obj.Stiffener is None, all_obj.Girder is None]):
            structure_obj = all_obj.Plate
            spacing = structure_obj.get_s() * self._prop_canvas_scale * 3
            plate_thk = structure_obj.get_pl_thk() * self._prop_canvas_scale * 3
            startx = 20
            starty = 225
            self._prop_canvas.create_text([startx + 100, 50],
                                          text='Plate with thickness ' +
                                               str(structure_obj.get_pl_thk() * 1000) + ' mm',
                                          font=self._text_size["Text 10 bold"], fill='Black')
            self._prop_canvas.create_rectangle(startx + spacing,
                                               starty,
                                               startx + spacing + spacing,
                                               starty - plate_thk,
                                               fill='grey', activefill='yellow')

        for idx, structure_obj in enumerate([all_obj.Stiffener, all_obj.Girder]):
            mult = 1 if all_obj.Girder is not None else 2
            thk_mult = 2
            startx = 100 + 300 * idx
            starty = 225

            if structure_obj is not None:
                self._prop_canvas.create_text([startx + 60, 50],
                                              text='Stiffener\n' + structure_obj.get_beam_string()
                                              if idx == 0 else 'Girder\n' + structure_obj.get_beam_string(),
                                              font=self._text_size["Text 9 bold"], fill='Black')
                self._prop_canvas.create_text([100, 20],
                                              text='Thickness scale x 2',
                                              font=self._text_size["Text 10 bold"], fill='grey')
                spacing = structure_obj.get_s() * self._prop_canvas_scale * mult
                stf_web_height = structure_obj.get_web_h() * self._prop_canvas_scale * mult
                stf_flange_width = structure_obj.get_fl_w() * self._prop_canvas_scale * mult
                plate_thk = structure_obj.get_pl_thk() * self._prop_canvas_scale * thk_mult * mult
                stf_web_thk = structure_obj.get_web_thk() * self._prop_canvas_scale * thk_mult * mult
                stf_flange_thk = structure_obj.get_fl_thk() * self._prop_canvas_scale * thk_mult * mult

                for count in [0, 1, 2] if idx == 0 else [0, ]:
                    self._prop_canvas.create_rectangle(startx + count * spacing,
                                                       starty,
                                                       startx + spacing + count * spacing,
                                                       starty - plate_thk,
                                                       fill='grey', activefill='yellow')
                    self._prop_canvas.create_rectangle(
                        startx + spacing * 0.5 + count * spacing - stf_web_thk / 2,
                        starty - plate_thk,
                        startx + spacing * 0.5 + count * spacing + stf_web_thk / 2,
                        starty - stf_web_height - plate_thk,
                        fill='grey', activefill='yellow')

                    if structure_obj.get_stiffener_type() not in ['L', 'L-bulb']:
                        self._prop_canvas.create_rectangle(
                            startx + spacing * 0.5 - stf_flange_width / 2 + count * spacing,
                            starty - stf_web_height - plate_thk,
                            startx + spacing * 0.5 + stf_flange_width / 2 + count * spacing,
                            starty - stf_web_height - plate_thk - stf_flange_thk,
                            fill='grey', activefill='yellow')
                    else:
                        self._prop_canvas.create_rectangle(
                            startx + spacing * 0.5 - stf_web_thk / 2 + count * spacing,
                            starty - stf_web_height - plate_thk,
                            startx + spacing * 0.5 + stf_flange_width + count * spacing,
                            starty - stf_web_height - plate_thk - stf_flange_thk,
                            fill='grey',
                            activefill='yellow')

    @staticmethod
    def _set_fea_3d_limits(ax, records):
        points = [
            point
            for record in records
            for polygon in record.get('polygons', [])
            for point in polygon
        ]
        if not points:
            ax.set_xlim(0.0, 1.0)
            ax.set_ylim(0.0, 1.0)
            ax.set_zlim(0.0, 1.0)
            return
        mins = [min(point[index] for point in points) for index in range(3)]
        maxs = [max(point[index] for point in points) for index in range(3)]
        spans = [maxs[index] - mins[index] for index in range(3)]
        xy_reference = max(spans[0], spans[1], 1.0e-6)
        padded_limits = []
        for index, span in enumerate(spans):
            minimum_span = xy_reference * 0.10 if index == 2 else xy_reference * 0.04
            display_span = max(span, minimum_span, 1.0e-6)
            center = (mins[index] + maxs[index]) / 2.0
            pad = display_span * 0.06
            padded_limits.append((center - display_span / 2.0 - pad, center + display_span / 2.0 + pad))
        ax.set_xlim(*padded_limits[0])
        ax.set_ylim(*padded_limits[1])
        ax.set_zlim(*padded_limits[2])
        try:
            ax.set_box_aspect((
                max(spans[0], xy_reference * 0.20),
                max(spans[1], xy_reference * 0.20),
                max(spans[2], xy_reference * 0.18),
            ))
        except Exception:
            pass

    def _draw_fea_buckling_canvas(self):
        """Draw clickable FE buckling panels as 3D shell-panel surfaces."""
        self._main_canvas.delete('all')
        self._fea_panel_canvas_items = {}
        width = max(int(self._main_canvas.winfo_width() or self._canvas_dim[0]), 1)
        height = max(int(self._main_canvas.winfo_height() or self._canvas_dim[1]), 1)

        session = self._fea_buckling_session
        if session is None or not session.panels:
            self.clear_prop_3d()
            self._fea_3d_panel_artists = {}
            self._fea_3d_panel_records = {}
            self._fea_3d_selected_overlay = None
            self._main_canvas.create_text(
                width / 2,
                height / 2 - 20,
                text='Import an INP/FRD file to scan FE buckling panels',
                font=self._text_size['Text 12 bold'],
                fill=self._color_text,
            )
            self._main_canvas.create_text(
                width / 2,
                height / 2 + 12,
                text='Use the FEA result buckling controls on the right side.',
                font=self._text_size['Text 8'],
                fill=self._color_text,
            )
            return

        self.clear_prop_3d()
        self._fea_3d_panel_artists = {}
        self._fea_3d_panel_records = {}
        self._fea_3d_selected_overlay = None
        records = fe_plate_fields.panel_3d_records(session.model, session.fields, session.usage_factors())
        if not records:
            return
        self._fea_3d_panel_records = {
            record.get('field_id'): record
            for record in records
            if record.get('field_id') is not None
        }
        self._embed_fea_buckling_tk3d_canvas(records, default_view='iso')
        return
        fig = plt.Figure(figsize=(9.8, 5.8), dpi=100)
        ax_width = 0.86 if self._fea_color_code.get() else 0.96
        ax = fig.add_axes([0.01, 0.06, ax_width, 0.88], projection='3d')
        uf_min, uf_max = self._fea_uf_color_limits()
        uf_norm = matplotlib.colors.Normalize(vmin=uf_min, vmax=uf_max)
        uf_cmap = plt.get_cmap('jet')

        for record in records:
            field_id = record['field_id']
            panel = session.panel(field_id)
            selected = field_id == self._fea_selected_panel_id
            self._fea_3d_panel_records[field_id] = record
            collection = Poly3DCollection(
                record['polygons'],
                facecolor=self._fea_panel_canvas_color(panel, record['index']),
                edgecolor='red' if selected else ('#333333' if self._fea_show_mesh.get() else 'none'),
                linewidth=1.8 if selected else (0.25 if self._fea_show_mesh.get() else 0.0),
                alpha=0.42 if selected else (0.82 if panel.usage_factor is not None else 0.58),
            )
            collection.set_gid(field_id)
            collection.set_picker(5)
            ax.add_collection3d(collection)
            self._fea_3d_panel_artists[field_id] = collection
            centroid = record['centroid']
            normal = record.get('normal', (0.0, 0.0, 1.0))
            label_point = (
                centroid[0] + normal[0] * 0.01,
                centroid[1] + normal[1] * 0.01,
                centroid[2] + normal[2] * 0.01,
            )
            label_parts = []
            if self._fea_show_panel_text.get():
                label_parts.append(field_id.replace('field_', '').replace('cyl_', ''))
            if self._fea_show_uf_text.get() and panel.usage_factor is not None:
                label_parts.append(f'UF {panel.usage_factor:.2f}')
            if label_parts:
                ax.text(
                    label_point[0],
                    label_point[1],
                    label_point[2],
                    '\n'.join(label_parts),
                    fontsize=7,
                    ha='center',
                    va='center',
                )
            arrow_length = max(min(float(record.get('span_m', record.get('axial_length_m', 1.0))),
                                   float(record.get('spacing_m', record.get('circumferential_spacing_m', 1.0)))) * 0.28,
                               0.05)
            arrow_origin = (
                centroid[0] + normal[0] * 0.02,
                centroid[1] + normal[1] * 0.02,
                centroid[2] + normal[2] * 0.02,
            )
            if self._fea_show_local_x_arrow.get():
                local_x = record.get('local_x', (1.0, 0.0, 0.0))
                ax.quiver(
                    arrow_origin[0], arrow_origin[1], arrow_origin[2],
                    local_x[0], local_x[1], local_x[2],
                    length=arrow_length,
                    normalize=True,
                    color='#1f77b4',
                    linewidth=0.8,
                    arrow_length_ratio=0.28,
                )
            if self._fea_show_local_y_arrow.get():
                local_y = record.get('local_y', (0.0, 1.0, 0.0))
                ax.quiver(
                    arrow_origin[0], arrow_origin[1], arrow_origin[2],
                    local_y[0], local_y[1], local_y[2],
                    length=arrow_length,
                    normalize=True,
                    color='#ff7f0e',
                    linewidth=0.8,
                    arrow_length_ratio=0.28,
                )

        self._set_fea_3d_limits(ax, records)
        ax.set_xlabel('X [m]', fontsize=7)
        ax.set_ylabel('Y [m]', fontsize=7)
        ax.set_zlabel('Z [m]', fontsize=7)
        ax.tick_params(labelsize=6)
        ax.set_title('FEA result buckling panels - click a panel to load input', fontsize=8)
        ax.view_init(elev=24, azim=-55)
        if self._fea_color_code.get():
            scalar_map = matplotlib.cm.ScalarMappable(norm=uf_norm, cmap=uf_cmap)
            scalar_map.set_array([])
            colorbar_ax = fig.add_axes([0.90, 0.18, 0.025, 0.64])
            colorbar = fig.colorbar(scalar_map, cax=colorbar_ax)
            colorbar.set_label('UF', fontsize=7)
            colorbar.ax.tick_params(labelsize=6)
        self._embed_fea_buckling_3d_figure(fig, ax, default_view=(24, -55))
        self._update_fea_3d_selection()

    def draw_canvas(self, state=None, event=None):
        '''
        Canvas is drawn here.
        '''

        if getattr(self, '_fea_buckling_mode', False):
            self._refresh_fea_buckling_views(rebuild_3d=True)
            return

        self._main_canvas.delete('all')
        color = 'black'  # by default
        # Drawing the shifted lines
        if any([self._new_shift_viz_coord_hor.get() != 0,
                self._new_shift_viz_coord_ver.get() != 0]) and self._new_shifted_coords.get():
            self._main_canvas.create_line(
                self._canvas_draw_origo[0] + self._canvas_scale * self._new_shift_viz_coord_hor.get() / 1000, 0,
                self._canvas_draw_origo[0] + self._canvas_scale * self._new_shift_viz_coord_hor.get() / 1000,
                self._canvas_dim[1] + 500,
                stipple='gray50', fill='peru')
            self._main_canvas.create_line(0, self._canvas_draw_origo[
                1] - self._canvas_scale * self._new_shift_viz_coord_ver.get() / 1000,
                                          self._canvas_dim[0] + 500,
                                          self._canvas_draw_origo[
                                              1] - self._canvas_scale * self._new_shift_viz_coord_ver.get() / 1000,
                                          stipple='gray50', fill='peru')
        else:
            # Drawing lines at (0, 0)
            self._main_canvas.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0],
                                          self._canvas_dim[1] + 500,
                                          stipple='gray50', fill=self._color_text)
            self._main_canvas.create_line(0, self._canvas_draw_origo[1], self._canvas_dim[0] + 500,
                                          self._canvas_draw_origo[1],
                                          stipple='gray50', fill=self._color_text)
            self._main_canvas.create_text(self._canvas_draw_origo[0] - 30 * 1,
                                          self._canvas_draw_origo[1] + 12 * 1, text='(0,0)',
                                          font='Text 10', fill=self._color_text)

        # Drawing COG and COB
        if self._new_show_cog.get():
            pt_size = 5
            if 'COG' in state.keys():
                if self._new_shifted_coords.get():
                    point_coord_x = self._canvas_draw_origo[0] + (state['COG'][0] +
                                                                  self._new_shift_viz_coord_hor.get() / 1000) * \
                                    self._canvas_scale
                    point_coord_y = self._canvas_draw_origo[1] - (state['COG'][1] +
                                                                  self._new_shift_viz_coord_ver.get() / 1000) * \
                                    self._canvas_scale
                else:
                    point_coord_x = self._canvas_draw_origo[0] + state['COG'][0] * self._canvas_scale
                    point_coord_y = self._canvas_draw_origo[1] - state['COG'][1] * self._canvas_scale

                self._main_canvas.create_oval(point_coord_x - pt_size + 2,
                                              point_coord_y - pt_size + 2,
                                              point_coord_x + pt_size + 2,
                                              point_coord_y + pt_size + 2, fill='yellow')

                self._main_canvas.create_text(point_coord_x + 5,
                                              point_coord_y - 14,
                                              text='steel COG: x=' + str(round(state['COG'][0], 2)) +
                                                   ' y=' + str(round(state['COG'][1], 2)),
                                              fill=self._color_text)

            if self._center_of_buoyancy != {}:
                for draft, cob in self._center_of_buoyancy.items():

                    if self._new_shifted_coords.get():
                        point_coord_x = self._canvas_draw_origo[0] + (cob[1] +
                                                                      self._new_shift_viz_coord_hor.get() / 1000) * \
                                        self._canvas_scale
                        point_coord_y = self._canvas_draw_origo[1] - (cob[0] +
                                                                      self._new_shift_viz_coord_ver.get() / 1000) * \
                                        self._canvas_scale
                    else:
                        point_coord_x = self._canvas_draw_origo[0] + cob[1] * self._canvas_scale
                        point_coord_y = self._canvas_draw_origo[1] - cob[0] * self._canvas_scale

                    self._main_canvas.create_oval(point_coord_x - pt_size + 2,
                                                  point_coord_y - pt_size + 2,
                                                  point_coord_x + pt_size + 2,
                                                  point_coord_y + pt_size + 2, fill='blue')

                    self._main_canvas.create_text(point_coord_x + 5,
                                                  point_coord_y + 14,
                                                  text='COB d=' + str(draft) + ': x=' + str(round(cob[1], 2)) +
                                                       ' y=' + str(round(cob[0], 2)),
                                                  font=self._text_size["Text 8"], fill='blue')

        chk_box_active = [self._new_colorcode_beams.get(), self._new_colorcode_plates.get(),
                          self._new_colorcode_pressure.get(), self._new_colorcode_utilization.get(),
                          self._new_colorcode_sigmax.get(), self._new_colorcode_sigmay1.get(),
                          self._new_colorcode_sigmay2.get(),
                          self._new_colorcode_tauxy.get(), self._new_colorcode_structure_type.get(),
                          self._new_colorcode_fatigue.get(), self._new_colorcode_section_modulus.get(),
                          self._new_colorcode_total.get(), self._new_colorcode_puls_acceptance.get(),
                          self._new_colorcode_puls_sp_or_up.get(), self._new_colorcode_spacing.get()].count(True) > 0

        if chk_box_active and state != None:
            self.color_code_text(state)

        # Drawing shortcut information if selected.
        if self._new_shortcut_backdrop.get() == True:
            self._main_canvas.create_text(self._main_canvas.winfo_width() * 0.87,
                                          self._main_canvas.winfo_height() * 0.16,
                                          text=self._shortcut_text,
                                          font=self._text_size["Text 8"],
                                          fill=self._color_text)

        # drawing the point dictionary
        pt_size = 3
        for key, value in self._point_dict.items():
            if self._new_shifted_coords.get():
                x_coord = round(self.get_point_actual_coord(key)[0] - self._new_shift_viz_coord_hor.get() / 1000, 3)
                y_coord = round(self.get_point_actual_coord(key)[1] - self._new_shift_viz_coord_ver.get() / 1000, 3)
                coord_color = 'peru'
            else:
                x_coord = round(self.get_point_actual_coord(key)[0], 3)
                y_coord = round(self.get_point_actual_coord(key)[1], 3)
                coord_color = self._color_text

            if self._point_is_active and key == self._active_point:
                self._main_canvas.create_oval(self.get_point_canvas_coord(key)[0] - pt_size + 2,
                                              self.get_point_canvas_coord(key)[1] - pt_size + 2,
                                              self.get_point_canvas_coord(key)[0] + pt_size + 2,
                                              self.get_point_canvas_coord(key)[1] + pt_size + 2, fill='blue')
                if self._new_draw_point_name.get():
                    # drawing the name of the point

                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] + 5,
                                                  self.get_point_canvas_coord(key)[1] - 14,
                                                  text='pt.' + str(get_num(key)),
                                                  font=self._text_size["Text 12 bold"], fill='red')
                    # drawing the coordinates of the point
                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] + 30,
                                                  self.get_point_canvas_coord(key)[1] - 40,
                                                  text='(' + str(x_coord) + ' , ' +
                                                       str(y_coord) + ')',
                                                  font=self._text_size["Text 14"], fill='red')

            else:
                self._main_canvas.create_oval(self.get_point_canvas_coord(key)[0] - pt_size,
                                              self.get_point_canvas_coord(key)[1] - pt_size,
                                              self.get_point_canvas_coord(key)[0] + pt_size,
                                              self.get_point_canvas_coord(key)[1] + pt_size, fill='red')
                if self._new_draw_point_name.get():
                    # printing 'pt.#'
                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] + 15,
                                                  self.get_point_canvas_coord(key)[1] - 10,
                                                  text='pt.' + str(get_num(key)),
                                                  font=self._text_size["Text 10"], fill=self._color_text)
                    # printing the coordinates of the point
                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] + 35,
                                                  self.get_point_canvas_coord(key)[1] + 10,
                                                  text='(' + str(x_coord) + ' , ' +
                                                       str(y_coord) + ')',
                                                  font=self._text_size["Text 10"], fill=coord_color)
        # drawing the line dictionary.

        if len(self._line_dict) != 0:
            for line, value in self._line_dict.items():
                coord1 = self.get_point_canvas_coord('point' + str(value[0]))
                coord2 = self.get_point_canvas_coord('point' + str(value[1]))
                if not chk_box_active and state != None:
                    try:
                        if self._line_to_struc[line][5] is not None:  # Cylinder
                            cylinder_results = state['cylinder'][line]
                            all_cyl_chks = list()
                            for key, val in cylinder_results.items():
                                if key in ['Unstiffened shell', 'Unstiffened conical shell',
                                           'Longitudinal stiffened shell',
                                           'Ring stiffened shell', 'Heavy ring frame', 'Column stability UF']:
                                    if (key == 'Column stability UF' and
                                            cylinder_results.get('Need to check column buckling', False) is False):
                                        continue

                                    all_cyl_chks.append(True if val is None else val < 1)
                                elif key == 'Stiffener check' and val is not None:
                                    for stf_key, stf_val in val.items():
                                        if stf_val is not None:
                                            all_cyl_chks.append(stf_val)
                            color = 'green' if all(all_cyl_chks) else 'red'

                        elif self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
                            color = 'red' if 'red' in state['colors'][line].values() else 'green'
                        elif self._new_buckling_method.get() == 'SemiAnalytical S3/U3':
                            semi_analytical_valid = state.get('SemiAnalytical valid', {}).get(line, {})
                            semi_analytical_colors = state.get('SemiAnalytical colors', {}).get(line, {})

                            if semi_analytical_valid.get('valid prediction', None) != 1:
                                color = 'red'
                            else:
                                puls_method = op._puls_selected_method(
                                    self._line_to_struc[line][0].Plate.get_puls_method()
                                )
                                if puls_method == 'ultimate':
                                    color = semi_analytical_colors.get('ultimate', 'red')
                                else:
                                    color = semi_analytical_colors.get('buckling', 'red')

                            if color == 'green':
                                color = 'green' if all([
                                    state['colors'][line][key] == 'green'
                                    for key in ['fatigue', 'section', 'shear', 'thickness']
                                ]) else 'red'
                        elif self._new_buckling_method.get() in [
                            'ML-Numeric (PULS based)',
                        ]:
                            ml_color_dict = state.get('ML buckling numeric colors', {}).get(line, {})

                            if ml_color_dict == {}:
                                color = 'black'
                            elif 'black' in ml_color_dict.values():
                                color = 'black'
                            else:
                                col_buc = ml_color_dict.get('buckling', 'black')
                                col_ult = ml_color_dict.get('ultimate', 'black')

                                if self._line_to_struc[line][0].Plate.get_puls_method() == 'buckling':
                                    color = col_buc
                                else:
                                    color = col_ult

                                # If the selected ML check is green, keep the existing
                                # fatigue/section/shear/thickness checks as additional
                                # requirements for the displayed line color.
                                if color == 'green':
                                    color = 'green' if all([
                                        state['colors'][line][key] == 'green'
                                        for key in ['fatigue', 'section', 'shear', 'thickness']
                                    ]) else 'red'

                    except (KeyError, TypeError, AttributeError):
                        color = 'black'
                elif chk_box_active and state != None and self._line_to_struc != {}:
                    color = self.color_code_line(state, line, coord1, [coord2[0] - coord1[0], coord2[1] - coord1[1]])
                else:
                    color = 'black'

                vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                # drawing a bold line if it is selected

                if all([line == self._active_line, self._line_is_active]):
                    if line not in self._line_to_struc.keys():
                        self._main_canvas.create_line(coord1, coord2, width=6, fill=self._color_text)
                    elif self._line_to_struc[line][5] is not None:
                        self._main_canvas.create_line(coord1, coord2, width=10, fill=color, stipple='gray50')
                    else:
                        self._main_canvas.create_line(coord1, coord2, width=6, fill=color)
                    if self._new_line_name.get():
                        self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 + 10,
                                                      text='Line ' + str(get_num(line)),
                                                      font=self._text_size["Text 10 bold"],
                                                      fill='red')
                else:
                    if line not in self._line_to_struc.keys():
                        self._main_canvas.create_line(coord1, coord2, width=3, fill=self._color_text)
                    elif self._line_to_struc[line][5] is not None:
                        self._main_canvas.create_line(coord1, coord2, width=6, fill=color, stipple='gray50')
                    else:
                        self._main_canvas.create_line(coord1, coord2, width=3, fill=color)
                    if self._new_line_name.get():
                        self._main_canvas.create_text(coord1[0] - 20 + vector[0] / 2 + 5,
                                                      coord1[1] + vector[1] / 2 + 10,
                                                      text='l.' + str(get_num(line)), font=self._text_size["Text 8"],
                                                      fill=self._color_text)
                if line in self._multiselect_lines:
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=self._new_toggle_var.get(),

                                                  fill='orange')

        # drawing waterline
        if len(self._load_dict) != 0:
            for load, data in self._load_dict.items():

                if data[0].is_static():
                    draft = self.get_canvas_coords_from_point_coords((0, data[0].get_static_draft()))[1]
                    self._main_canvas.create_line(0, draft, self._canvas_dim[0] + 500, draft, fill="blue", dash=(4, 4))
                    self._main_canvas.create_text(900, draft - 10, text=str(get_num(data[0].get_name())) + ' [m]',
                                                  fill='blue')
                else:
                    pass

    def color_code_text(self, state):
        '''
        return_dict['color code'] = {'thickest plate': thickest_plate, 'thickness map': thk_map,
                                     'highest pressure': highest_pressure, 'lowest pressure': lowest_pressure,
                                     'pressure map': press_map,
                                     'all utilizations': all_utils, 'utilization map': util_map,
                                     'max sigma x': max(sig_x), 'min sigma x': min(sig_x), 'sigma x map': sig_x_map,
                                     'max sigma y1': max(sig_y1), 'min sigma y1': min(sig_y1),
                                     'sigma y1 map': sig_y1_map,
                                     'max sigma y2': max(sig_y2), 'min sigma y2': min(sig_y2),
                                     'sigma y2 map': sig_y2_map,
                                     'max tau xy': max(tau_xy), 'min tau xy': min(tau_xy), 'tau_xy map': tau_xy_map,
                                     'structure types map': set(structure_type),  'sections in model': sec_in_model,
                                     'recorded sections': recorded_sections}
                                               }
        :param state:
        :return:
        '''

        cc_state = state['color code']
        if cc_state == {}:
            return
        start_text, start_text_shift = 190, 191
        cmap_sections = plt.get_cmap('jet')
        if self._new_colorcode_beams.get() == True and self._line_to_struc != {}:
            sec_in_model = cc_state['sections in model']
            for section, idx in sec_in_model.items():
                if section == 'length':
                    continue
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=section,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=section,
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(
                                                  cmap_sections(idx / sec_in_model['length'])),
                                              anchor="nw")
        elif self._new_colorcode_plates.get() == True and self._line_to_struc != {}:
            cylinder = False
            for obj_list in self._line_to_struc.values():
                if obj_list[5] is not None:
                    cylinder = True
            if cylinder:
                all_thicknesses = np.unique(cc_state['all cyl thicknesses']).tolist()
            else:
                all_thicknesses = np.unique(cc_state['all thicknesses']).tolist()

            for idx, thk in enumerate(np.unique(all_thicknesses).tolist()):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str('Plate ' +
                                                                                        str(thk if cylinder else thk * 1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx,
                                              text=str('Plate ' + str(thk if cylinder else thk * 1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(all_thicknesses.index(thk)
                                                                                           / len(all_thicknesses))),
                                              anchor="nw")
        elif self._new_colorcode_spacing.get() == True and self._line_to_struc != {}:

            all_spacings = cc_state['spacings']

            for idx, s in enumerate(all_spacings):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx,
                                              text=str('Spacing ' + str(s * 1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str('Spacing ' + str(s * 1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(all_spacings.index(s)
                                                                                           / len(all_spacings))),
                                              anchor="nw")
        elif self._new_colorcode_pressure.get() == True and self._line_to_struc != {}:
            highest_pressure = cc_state['highest pressure']
            press_map = cc_state['pressure map']

            for idx, press in enumerate(press_map):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str(str(press) + ' Pa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str(str(press) + ' Pa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(0 if highest_pressure == 0
                                                                                           else press / highest_pressure)),
                                              anchor="nw")
        elif self._new_colorcode_utilization.get() == True and self._line_to_struc != {}:
            all_utils = cc_state['utilization map']
            method_text = cc_state.get('buckling method', self._new_buckling_method.get())
            if method_text == 'SemiAnalytical S3/U3':
                title_text = 'SemiAnalytical UF'
            elif method_text == 'ML-Numeric (PULS based)':
                title_text = 'ML-Numeric UF'
            else:
                title_text = 'Buckling UF'
            self._main_canvas.create_text(10, start_text - 20, text=title_text,
                                          font=self._text_size["Text 10 bold"],
                                          fill=self._color_text,
                                          anchor="nw")
            for idx, uf in enumerate(cc_state['utilization map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str('UF = ' + str(round(uf, 1))),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str('UF = ' + str(round(uf, 1))),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(uf / max(all_utils))),
                                              anchor="nw")
        elif self._new_colorcode_sigmax.get() == True:
            for idx, value in enumerate(cc_state['sigma x map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max sigma x'] - cc_state[
                                                  'min sigma x'] == 0 else
                                              matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max sigma x'] == 0 else
                                                                (value + abs(cc_state['min sigma x'])) /
                                                                (cc_state['max sigma x'] - cc_state['min sigma x']))),
                                              anchor="nw")
        elif self._new_colorcode_sigmay1.get() == True:
            for idx, value in enumerate(cc_state['sigma y1 map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max sigma y1'] - cc_state['min sigma y1'] == 0
                                              else matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max sigma y1'] == 0 else
                                                                (value + abs(cc_state['min sigma y1'])) /
                                                                (cc_state['max sigma y1'] - cc_state['min sigma y1']))),
                                              anchor="nw")
        elif self._new_colorcode_sigmay2.get() == True:
            for idx, value in enumerate(cc_state['sigma y2 map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max sigma y2'] - cc_state[
                                                  'min sigma y2'] == 0 else
                                              matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max sigma y2'] == 0 else
                                                                (value + abs(cc_state['min sigma y2'])) /
                                                                (cc_state['max sigma y2'] - cc_state['min sigma y2']))),
                                              anchor="nw")
        elif self._new_colorcode_tauxy.get() == True:
            for idx, value in enumerate(cc_state['tau xy map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str(str(round(value, 5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max tau xy'] - cc_state['min tau xy'] == 0 else
                                              matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max tau xy'] == 0 else
                                                                (value + abs(cc_state['min tau xy'])) /
                                                                (cc_state['max tau xy'] - cc_state['min tau xy']))),
                                              anchor="nw")
        elif self._new_colorcode_structure_type.get() == True:
            structure_type_map = list(cc_state['structure types map'])
            for idx, structure_type in enumerate(structure_type_map):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=structure_type,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=structure_type,
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(structure_type_map
                                                                                           .index(structure_type) /
                                                                                           len(structure_type_map))),
                                              anchor="nw")
        elif self._new_colorcode_section_modulus.get() == True or self._new_colorcode_fatigue.get() == True or \
                self._new_colorcode_fatigue.get() == True or self._new_colorcode_total.get() == True:
            for idx, value in enumerate(cc_state['section modulus map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str(str(round(value, 5))),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str(str(round(value, 5))),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(
                                                  cmap_sections(value)),
                                              anchor="nw")
        elif self._new_colorcode_puls_sp_or_up.get() == True:

            for idx, value in enumerate(['SP', 'UP']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='blue' if value == 'SP' else 'red',
                                              anchor="nw")
        elif self._new_colorcode_puls_acceptance.get() == True:

            for idx, value in enumerate(['buckling', 'ultimate']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='blue' if value == 'ultimate' else 'red',
                                              anchor="nw")

    def color_code_line(self, state, line, coord1, vector):

        cc_state = state['color code']
        cmap_sections = plt.get_cmap('jet')

        def utilization_color(uf):
            try:
                uf = float(uf)
                max_uf = max(cc_state.get('utilization map', [uf, 1.0]))
                max_uf = 1.0 if max_uf == 0 else float(max_uf)
                return matplotlib.colors.rgb2hex(cmap_sections(uf / max_uf))
            except Exception:
                return 'black'

        if line not in state['color code']['lines'].keys():
            return 'black'

        if self._new_colorcode_beams.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None or self._line_to_struc[line][0].Stiffener is None:
                if self._line_to_struc[line][5] is not None:
                    cyl_obj = self._line_to_struc[line][5]
                    if cyl_obj.LongStfObj is not None:
                        this_text = cyl_obj.LongStfObj.get_beam_string(short=True)
                        color = state['color code']['lines'][line]['section cyl']
                    else:
                        this_text = 'N/A'
                        color = 'grey'
                else:
                    color = 'grey'
                    this_text = 'N/A'
            elif self._line_to_struc[line][0].Plate is not None:
                color = state['color code']['lines'][line]['section']
                this_text = self._line_to_struc[line][0].Plate.get_beam_string()
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text,
                                              font=self._text_size["Text 7"])

        elif self._new_colorcode_plates.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None:
                cyl_obj = self._line_to_struc[line][5]
                color = state['color code']['lines'][line]['cylinder plate']
                this_text = str(round(cyl_obj.ShellObj.thk * 1000, 2))
            else:
                color = state['color code']['lines'][line]['plate']
                this_text = str(self._line_to_struc[line][0].Plate.get_pl_thk() * 1000)
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_spacing.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None or self._line_to_struc[line][0].Stiffener is None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['spacing']
                this_text = str(self._line_to_struc[line][0].Stiffener.get_s() * 1000)
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_pressure.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                if cc_state['all pressures'] == [0, 1]:
                    color = 'black'
                else:
                    color = state['color code']['lines'][line]['pressure color']
                this_text = str(state['color code']['lines'][line]['pressure'])
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_utilization.get() == True and self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
            if line not in list(self._line_to_struc.keys()):
                color = 'black'
                this_text = 'N/A'
            elif self._line_to_struc[line][5] is not None:
                results = state.get('cylinder', {}).get(line, self._line_to_struc[line][5].get_utilization_factors())
                cyl_uf = self._cylinder_buckling_uf(results)
                color = utilization_color(cyl_uf)
                this_text = str(round(cyl_uf, 3))
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=this_text)
            else:
                color = state['color code']['lines'][line]['rp uf color']
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['rp uf'], 2))

        elif self._new_colorcode_utilization.get() == True and self._new_buckling_method.get() == 'SemiAnalytical S3/U3':
            if line in self._line_to_struc and self._line_to_struc[line][5] is not None:
                results = state.get('cylinder', {}).get(line, self._line_to_struc[line][5].get_utilization_factors())
                cyl_uf = self._cylinder_buckling_uf(results)
                color = utilization_color(cyl_uf)
                this_text = str(round(cyl_uf, 3))
            else:
                semi_analytical = state.get('SemiAnalytical', {}).get(line, {})
                semi_analytical_valid = state.get('SemiAnalytical valid', {}).get(line, {})

                if semi_analytical_valid.get('valid prediction', None) == 1:
                    puls_method = state['color code']['lines'][line].get('Buckling method', None)
                    puls_method = op._puls_selected_method(puls_method)

                    if puls_method == 'ultimate':
                        uf = semi_analytical.get('ultimate UF', float('inf'))
                        color = utilization_color(uf)
                        this_text = 'ult UF=' + str(round(uf, 3))
                    else:
                        uf = semi_analytical.get('buckling UF', float('inf'))
                        color = utilization_color(uf)
                        this_text = 'buc UF=' + str(round(uf, 3))
                else:
                    color = 'red'
                    this_text = semi_analytical_valid.get('valid label', 'invalid')

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)
        elif self._new_colorcode_utilization.get() == True and self._new_buckling_method.get() == 'ML-Numeric (PULS based)':
            if line in self._line_to_struc and self._line_to_struc[line][5] is not None:
                results = state.get('cylinder', {}).get(line, self._line_to_struc[line][5].get_utilization_factors())
                cyl_uf = self._cylinder_buckling_uf(results)
                color = utilization_color(cyl_uf)
                this_text = str(round(cyl_uf, 3))
            else:
                numeric = state.get('ML buckling numeric', {}).get(line, {})
                numeric_valid = state.get('ML buckling numeric valid', {}).get(line, {})

                if numeric_valid.get('valid prediction', None) == 1:
                    puls_method = state['color code']['lines'][line].get('Buckling method', None)

                    if puls_method == 'buckling':
                        uf = numeric.get('buckling UF', float('inf'))
                        color = utilization_color(uf)
                        this_text = 'buc UF=' + str(round(uf, 3))
                    elif puls_method == 'ultimate':
                        uf = numeric.get('ultimate UF', float('inf'))
                        color = utilization_color(uf)
                        this_text = 'ult UF=' + str(round(uf, 3))
                    else:
                        buc_uf = numeric.get('buckling UF', float('inf'))
                        ult_uf = numeric.get('ultimate UF', float('inf'))
                        uf = max(buc_uf, ult_uf)
                        color = utilization_color(uf)
                        this_text = 'UF=' + str(round(uf, 3))
                else:
                    color = 'red'
                    this_text = numeric_valid.get('valid label', 'invalid/NaN')

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_sigmax.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['sigma x']
                this_text = str(self._line_to_struc[line][0].Plate.sigma_x1)

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_sigmay1.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['sigma y1']
                this_text = str(self._line_to_struc[line][0].Plate.sigma_y2)

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_sigmay2.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['sigma y2']
                this_text = str(self._line_to_struc[line][0].Plate.sigma_y2)

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_tauxy.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['tau xy']
                this_text = round(self._line_to_struc[line][0].Plate.tau_xy, 2)

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_structure_type.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['structure type']
                this_text = self._line_to_struc[line][0].Plate.get_structure_type()

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text,
                                              font=self._text_size["Text 7"])

        elif self._new_colorcode_section_modulus.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['section modulus color']
                this_text = round(state['color code']['lines'][line]['section uf'], 2)

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_fatigue.get() == True:

            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['fatigue color']
                this_text = round(state['color code']['lines'][line]['fatigue uf'], 2)
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_total.get() == True:
            if self._line_to_struc[line][5] is not None:
                results = state.get('cylinder', {}).get(line, self._line_to_struc[line][5].get_utilization_factors())
                cyl_uf = self._cylinder_buckling_uf(results)
                color = utilization_color(cyl_uf)
                this_text = str(round(cyl_uf, 3))
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=this_text)

            elif self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
                color = state['color code']['lines'][line]['Total uf color rp']
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['Total uf rp'], 2))
            elif self._new_buckling_method.get() == 'SemiAnalytical S3/U3':
                semi_analytical = state.get('SemiAnalytical', {}).get(line, {})
                semi_analytical_valid = state.get('SemiAnalytical valid', {}).get(line, {})
                semi_analytical_colors = state.get('SemiAnalytical colors', {}).get(line, {})

                if semi_analytical_valid.get('valid prediction', None) == 1:
                    buc_uf = semi_analytical.get('buckling UF', float('inf'))
                    ult_uf = semi_analytical.get('ultimate UF', float('inf'))
                    total_uf = max(buc_uf, ult_uf)

                    color = 'green' if all([
                        semi_analytical_colors.get('buckling', 'red') == 'green',
                        semi_analytical_colors.get('ultimate', 'red') == 'green'
                    ]) else 'red'
                    this_text = 'max UF=' + str(round(total_uf, 3))
                else:
                    color = 'red'
                    this_text = semi_analytical_valid.get('valid label', 'invalid')

                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=this_text)
            elif self._new_buckling_method.get() == 'ML-Numeric (PULS based)':
                numeric = state.get('ML buckling numeric', {}).get(line, {})
                numeric_valid = state.get('ML buckling numeric valid', {}).get(line, {})
                numeric_colors = state.get('ML buckling numeric colors', {}).get(line, {})

                if numeric_valid.get('valid prediction', None) == 1:
                    buc_uf = numeric.get('buckling UF', float('inf'))
                    ult_uf = numeric.get('ultimate UF', float('inf'))
                    total_uf = max(buc_uf, ult_uf)

                    color = 'green' if all([
                        numeric_colors.get('buckling', 'red') == 'green',
                        numeric_colors.get('ultimate', 'red') == 'green'
                    ]) else 'red'
                    this_text = 'max UF=' + str(round(total_uf, 3))
                else:
                    color = 'red'
                    this_text = numeric_valid.get('valid label', 'invalid/NaN')

                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=this_text)

        elif self._new_colorcode_puls_acceptance.get():
            buckling_method = state['color code']['lines'][line].get('Buckling method', None)
            if buckling_method == None:
                color = 'black'
            else:
                color = 'blue' if buckling_method == 'ultimate' else 'red'
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=buckling_method)

        elif self._new_colorcode_puls_sp_or_up.get():
            buckling_sp_or_up = state['color code']['lines'][line].get('Buckling SP/UP', None)
            if buckling_sp_or_up == None:
                color = 'black'
            else:
                color = 'blue' if buckling_sp_or_up == 'SP' else 'red'
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=buckling_sp_or_up)
        else:
            color = 'black'

        return color

    def draw_results(self, state=None):
        '''
        The properties canvas is created here.
                state =     {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                            'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                            'all_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}}
        :return:
        '''

        self._result_canvas.delete('all')

        if getattr(self, '_fea_buckling_mode', False):
            self._draw_fea_panel_result_text()
            return

        if state is None or self._active_line not in state['all_obj'].keys():
            return

        if self._line_is_active:
            x, y, dx, dy = 0, 5, 15, 17

            if self._active_line in self._line_to_struc and self._line_to_struc[self._active_line][5] is None:

                m3_to_mm3 = float(math.pow(1000, 3))
                m2_to_mm2 = float(math.pow(1000, 2))

                current_line = self._active_line

                obj_scnt_calc_pl = state['all_obj'][current_line].Plate
                obj_scnt_calc_stf = state['all_obj'][current_line].Stiffener
                obj_scnt_calc_girder = state['all_obj'][current_line].Girder
                sec_mod = [round(state['section_modulus'][current_line]['sec_mod'][0], 5),
                           round(state['section_modulus'][current_line]['sec_mod'][1], 5)]
                shear_area = state['shear_area'][current_line]['shear_area']
                min_shear = state['shear_area'][current_line]['min_shear_area']
                min_sec_mod = state['section_modulus'][current_line]['min_sec_mod']
                min_thk = state['thickness'][current_line]['min_thk']
                buckling = state['buckling'][current_line]

                if state['slamming'][current_line]['state']:
                    slamming = True
                    slm_zpl = state['slamming'][current_line]['zpl']
                    slm_zpl_req = state['slamming'][current_line]['zpl_req']
                    slm_min_pl_thk = state['slamming'][current_line]['min_plate_thk']
                    slm_min_web_thk = state['slamming'][current_line]['min_web_thk']

                    slm_text_pl_thk = 'Minimum plate thickness (BOW SLAMMING): ' + str(
                        round(slm_min_pl_thk, 1)) + ' [mm]' \
                        if obj_scnt_calc_stf.get_pl_thk() * 1000 < slm_min_pl_thk else None

                    slm_text_min_web_thk = 'Minimum web thickness (BOW SLAMMING): ' + str(
                        round(slm_min_web_thk, 1)) + ' [mm]' \
                        if obj_scnt_calc_stf.get_web_thk() * 1000 < slm_min_web_thk else None
                    if slm_zpl_req is not None:
                        slm_text_min_zpl = 'Minimum section modulus (BOW SLAMMING): ' + str(
                            round(slm_zpl_req, 1)) + ' [cm^3]' \
                            if slm_zpl < slm_zpl_req else None
                    else:
                        slm_text_min_zpl = False
                else:
                    slamming, slm_text_pl_thk, slm_text_min_web_thk, slm_text_min_zpl = [False for di in range(4)]

                color_fatigue = state['colors'][current_line]['fatigue']
                color_sec = state['colors'][current_line]['section']
                color_shear = state['colors'][current_line]['shear']
                color_thk = state['colors'][current_line]['thickness']
                color_buckling = state['colors'][current_line]['buckling']

                # printing the minimum section modulus
                x1, x2, x3 = 15, 25, 35

                self._result_canvas.create_text([x + 0 * dx, (y + 0 * dy) * 1],
                                                text='-----  Special provisions - DNV-OS-C101 -----',
                                                font=self._text_size["Text 9 bold"], anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + 0 * dx, (y + 2 * dy) * 1],
                                                text='Section modulus [mm^3]' ,
                                                font=self._text_size["Text 9"], anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + 0 * dx, (y + 3 * dy) * 1],
                                                text='Shear area [mm^2]',
                                                font=self._text_size["Text 9"], anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + 0 * dx, (y + 4 * dy) * 1],
                                                text='Plate thickness check [mm]',
                                                font=self._text_size["Text 9"], anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + x1 * dx, (y + 1 * dy) * 1],
                                                text='Minimum value',
                                                font=self._text_size["Text 9"], anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + x2 * dx, (y + 1 * dy) * 1],
                                                text='Actual value',
                                                font=self._text_size["Text 9"], anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + x3 * dx, (y + 1 * dy) * 1],
                                                text='Accepted?',
                                                font=self._text_size["Text 9"], anchor='nw', fill=self._color_text)

                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = '(shear issue, change thickness or web height)'
                else:
                    text = str('%.4E' % decimal.Decimal(min_sec_mod * m3_to_mm3)) \
                        if not slm_text_min_zpl else slm_text_min_zpl
                self._result_canvas.create_text([x + x1 * dx, (y + 2 * dy) * 1], text=text,
                                                font=self._text_size["Text 9 bold"], anchor='nw', fill=self._color_text)

                # printing the calculated sectiton modulus
                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = ''
                else:
                    text = str('%.4E' % decimal.Decimal(min(sec_mod[1], sec_mod[0]) * m3_to_mm3))\
                        if not slm_text_min_zpl else str(slm_zpl) + '- zpl [cm^3]'
                self._result_canvas.create_text([x + x2 * dx, (y + 2 * dy) * 1],
                                                text=text, font=self._text_size['Text 9 bold'], anchor='nw',
                                                fill=color_sec)
                if not state['slamming'][current_line]['state']:
                    self._result_canvas.create_text([x + x3 * dx, (y + 2 * dy) * 1],
                                                    text='Ok' if min(sec_mod[1], sec_mod[0]) * m3_to_mm3 >=
                                                                 min_sec_mod * m3_to_mm3 else 'Not ok',
                                                    font=self._text_size['Text 9 bold'], anchor='nw',
                                                    fill=color_sec)
                # minimum shear area
                text = str('%.4E' % decimal.Decimal(min_shear * m2_to_mm2)) \
                    if not slm_text_min_web_thk else str(round(slm_min_web_thk, 1))
                self._result_canvas.create_text([x + x1 * dx, (y + 3 * dy) * 1],
                                                text=text,
                                                font=self._text_size["Text 9 bold"], anchor='nw', fill=self._color_text)
                text = str('%.4E' % decimal.Decimal(shear_area * m2_to_mm2)) \
                    if not slm_text_min_web_thk else str(obj_scnt_calc_stf.get_web_thk() * 1000)
                self._result_canvas.create_text([x + x2 * dx, (y + 3 * dy) * 1],
                                                text=text,
                                                font=self._text_size["Text 9 bold"], anchor='nw', fill=color_shear)
                if not state['slamming'][current_line]['state']:
                    self._result_canvas.create_text([x + x3 * dx, (y + 3 * dy) * 1],
                                                    text='Ok' if shear_area * m2_to_mm2 >= min_shear * m2_to_mm2 else
                                                    'Not ok',
                                                    font=self._text_size["Text 9 bold"], anchor='nw', fill=color_shear)

                # minimum thickness for plate
                text = str(round(min_thk, 1))  if not state['slamming'][current_line]['state'] else \
                    'Slamming minimum thickness: ' + str(round(slm_min_pl_thk, 2))
                self._result_canvas.create_text([x + x1 * dx, (y + 4 * dy) * 1],
                                                text=text,
                                                font=self._text_size["Text 9 bold"], anchor='nw', fill=self._color_text)

                if not state['slamming'][current_line]['state']:
                    self._result_canvas.create_text([x + x2 * dx, (y + 4 * dy) * 1],
                                                    text=str(obj_scnt_calc_pl.get_pl_thk() * 1000) ,
                                                    font=self._text_size["Text 9 bold"], anchor='nw', fill=color_shear)

                    self._result_canvas.create_text([x + x3 * dx, (y + 4 * dy) * 1],
                                                    text='Ok' if obj_scnt_calc_pl.get_pl_thk() * 1000 > min_thk
                                                    else 'Not ok',
                                                    font=self._text_size["Text 9 bold"], anchor='nw', fill=color_thk)

                # buckling results
                start_y, y = 5, 10
                fatigue_start_offset = 8
                if self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
                    '''
                            return {'Plate': {'Plate buckling': up_buckling}, 'Stiffener': {'Overpressure plate side': stf_buckling_pl_side,
                                                    'Overpressure stiffener side': stf_buckling_stf_side,
                                                    'Resistance between stiffeners': stf_plate_resistance,
                                                    'Shear capacity': stf_shear_capacity},
                'Girder': {'Overpressure plate side': girder_buckling_pl_side,
                           'Overpressure girder side': girder_buckling_girder_side,
                           'Shear capacity': girder_shear_capacity},
                'Local buckling': local_buckling}
                    '''

                    self._result_canvas.create_text([x * 1, (y + (start_y + 0) * dy) * 1],
                                                    text='Buckling results DNV-RP-C201 - prescriptive - (plate, stiffener, girder):',
                                                    font=self._text_size["Text 9 bold"], anchor='nw',
                                                    fill=self._color_text)

                    self._result_canvas.create_text([x + dx * 0, (y + (start_y + 2) * dy) * 1],
                                                    text='Overpressure plate side', font=self._text_size["Text 9"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 0, (y + (start_y + 3) * dy) * 1],
                                                    text='Overpressure stiffener side', font=self._text_size["Text 9"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 0, (y + (start_y + 4) * dy) * 1],
                                                    text='Resistance between stiffeners',
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 0, (y + (start_y + 5) * dy) * 1],
                                                    text='Shear capacity', font=self._text_size["Text 9"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 0, (y + (start_y + 6) * dy) * 1],
                                                    text='Maximum web height [mm]',
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 0, (y + (start_y + 7) * dy) * 1],
                                                    text='Maximum flange width [mm]',
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw', fill=self._color_text)

                    # 'Local buckling'
                    x1, x2, x3 = 15, 25, 35
                    self._result_canvas.create_text([x + dx * 15, (y + (start_y + 1) * dy) * 1],
                                                    text='Plate', font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 25, (y + (start_y + 1) * dy) * 1],
                                                    text='Stiffener', font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=self._color_text)
                    self._result_canvas.create_text([x + dx * 35, (y + (start_y + 1) * dy) * 1],
                                                    text='Girder', font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=self._color_text)
                    x_mult = x1
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 2) * dy) * 1],
                                                    text=str(round(buckling['Plate']['Plate buckling'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=color_buckling)
                    x_mult = x2
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 2) * dy) * 1],
                                                    text=str(
                                                        round(buckling['Stiffener']['Overpressure plate side'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=color_buckling)
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 3) * dy) * 1],
                                                    text=str(
                                                        round(buckling['Stiffener']['Overpressure stiffener side'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=color_buckling)

                    stfweb = round(buckling['Local buckling']['Stiffener'][0], 3)  # *1000
                    stffl = round(buckling['Local buckling']['Stiffener'][1], 3)  # *1000

                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 4) * dy) * 1],
                                                    text=str(
                                                        round(buckling['Stiffener']['Resistance between stiffeners'],
                                                              3))
                                                    , font=self._text_size["Text 9 bold"],
                                                    anchor='nw',
                                                    fill=color_buckling)
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 5) * dy) * 1],
                                                    text=str(round(buckling['Stiffener']['Shear capacity'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw',
                                                    fill=color_buckling)

                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 6) * dy) * 1],
                                                    text=str(stfweb),
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw',
                                                    fill=self._color_text if obj_scnt_calc_stf is None else 'red'
                                                    if obj_scnt_calc_stf.hw > stfweb else 'green')
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 7) * dy) * 1],
                                                    text=str(stffl),
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw',
                                                    fill=self._color_text if obj_scnt_calc_stf is None else 'red'
                                                    if obj_scnt_calc_stf.b > stffl else 'green')
                    x_mult = x3
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 2) * dy) * 1],
                                                    text=str(round(buckling['Girder']['Overpressure plate side'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=color_buckling)
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 3) * dy) * 1],
                                                    text=str(round(buckling['Girder']['Overpressure girder side'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=color_buckling)
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 5) * dy) * 1],
                                                    text=str(round(buckling['Girder']['Shear capacity'], 3)),
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=color_buckling)

                    gweb = round(buckling['Local buckling']['Girder'][0], 3)  # *1000
                    gfl = round(buckling['Local buckling']['Girder'][1], 3)  # *1000
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 6) * dy) * 1],
                                                    text=str(gweb),
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw',
                                                    fill=self._color_text if obj_scnt_calc_girder is None else
                                                    'red' if obj_scnt_calc_girder.hw > gweb else 'green')
                    self._result_canvas.create_text([x + dx * x_mult, (y + (start_y + 7) * dy) * 1],
                                                    text=str(gfl),
                                                    font=self._text_size["Text 9"],
                                                    anchor='nw',
                                                    fill=self._color_text if obj_scnt_calc_girder is None else
                                                    'red' if obj_scnt_calc_girder.b > gfl else 'green')

                    #
                    # self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+7)*dy) * 1],
                    #                            text=str(round(buckling['Local buckling']['Girder'][1],3)),
                    #                                 font=self._text_size["Text 9"],
                    #                            anchor='nw',fill=color_buckling)


                elif self._new_buckling_method.get() in [
                    'SemiAnalytical S3/U3',
                    'ML-Numeric (PULS based)',
                ]:

                    print_semi_analytical_results = self._new_buckling_method.get() == 'SemiAnalytical S3/U3'
                    print_class_results = False
                    print_numeric_results = self._new_buckling_method.get() == 'ML-Numeric (PULS based)'

                    self._result_canvas.create_text(
                        [x * 1, (y + (start_y + 0) * dy) * 1],
                        text='Buckling results ANYstructure SemiAnalytical/ML algorithm:',
                        font=self._text_size["Text 9 bold"],
                        anchor='nw',
                        fill=self._color_text,
                    )

                    line_offset = 1

                    # -------------------------------------------------------------------------
                    # Built-in semi-analytical replacement result
                    # -------------------------------------------------------------------------
                    if print_semi_analytical_results:
                        semi_analytical = state.get('SemiAnalytical', {}).get(current_line, None)
                        semi_analytical_valid = state.get('SemiAnalytical valid', {}).get(current_line, {})
                        semi_analytical_colors = state.get('SemiAnalytical colors', {}).get(current_line, {})

                        if semi_analytical is not None:
                            semi_analytical_is_valid = semi_analytical_valid.get('valid prediction', None) == 1
                            if semi_analytical_is_valid:
                                buckling_uf = semi_analytical.get('buckling UF', float('inf'))
                                ultimate_uf = semi_analytical.get('ultimate UF', float('inf'))
                                buckling_uf_raw = semi_analytical.get('buckling UF raw', None)
                                ultimate_uf_raw = semi_analytical.get('ultimate UF raw', None)
                                semi_analytical_mat_fac = semi_analytical.get(
                                    'material factor',
                                    self._new_material_factor.get(),
                                )

                                buckling_uf_txt = f"{buckling_uf:.3f}"
                                ultimate_uf_txt = f"{ultimate_uf:.3f}"

                                if buckling_uf_raw is not None:
                                    buckling_uf_txt += f"  ({buckling_uf_raw:.3f} x {semi_analytical_mat_fac:.2f})"

                                if ultimate_uf_raw is not None:
                                    ultimate_uf_txt += f"  ({ultimate_uf_raw:.3f} x {semi_analytical_mat_fac:.2f})"
                            else:
                                buckling_uf_txt = 'invalid/unsupported'
                                ultimate_uf_txt = 'invalid/unsupported'

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Buckling UF SemiAnalytical S3/U3: ' + buckling_uf_txt,
                                font=self._text_size["Text 9 bold"],
                                anchor='nw',
                                fill=semi_analytical_colors.get('buckling', 'red'),
                            )
                            line_offset += 1

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Ultimate UF SemiAnalytical S3/U3: ' + ultimate_uf_txt,
                                font=self._text_size["Text 9 bold"],
                                anchor='nw',
                                fill=semi_analytical_colors.get('ultimate', 'red'),
                            )
                            line_offset += 1

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='SemiAnalytical UF acceptance limit: <= 1.00',
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=self._color_text,
                            )
                            line_offset += 1

                            semi_analytical_status = semi_analytical_valid.get('valid label', '')
                            if semi_analytical.get('error', ''):
                                semi_analytical_status += ' | ' + semi_analytical.get('error', '')

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='SemiAnalytical S3/U3 status: ' + semi_analytical_status,
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=self._color_text if semi_analytical_is_valid else 'red',
                            )
                            line_offset += 1
                            if semi_analytical_is_valid:
                                controlling_limit = semi_analytical.get('controlling limit', '')
                                critical_mode = semi_analytical.get('critical mode', '')
                                critical_family = semi_analytical.get('critical failure family', '')
                                if controlling_limit or critical_mode:
                                    control_text = 'SemiAnalytical control: '
                                    if controlling_limit:
                                        control_text += str(controlling_limit).replace('_', ' ')
                                    if critical_mode:
                                        control_text += ' / ' + str(critical_mode).replace('_', ' ')
                                    self._result_canvas.create_text(
                                        [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                        text=control_text,
                                        font=self._text_size["Text 9"],
                                        anchor='nw',
                                        fill=self._color_text,
                                    )
                                    line_offset += 1
                                if critical_family:
                                    self._result_canvas.create_text(
                                        [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                        text='SemiAnalytical failure family: ' + str(critical_family).replace('_', ' '),
                                        font=self._text_size["Text 9"],
                                        anchor='nw',
                                        fill=self._color_text,
                                    )
                                    line_offset += 1

                        else:
                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='SemiAnalytical S3/U3: not available',
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=self._color_text,
                            )
                            line_offset += 1

                    # -------------------------------------------------------------------------
                    # Classification pipeline result
                    # -------------------------------------------------------------------------
                    if print_class_results:
                        ml_class = state.get('ML buckling class', {}).get(current_line, {})
                        ml_colors = state.get('ML buckling colors', {}).get(current_line, {})

                        self._result_canvas.create_text(
                            [x * 1, (y + (start_y + line_offset) * dy) * 1],
                            text='Buckling class: ' + str(ml_class.get('buckling', 'N/A')),
                            font=self._text_size["Text 9 bold"],
                            anchor='nw',
                            fill=ml_colors.get('buckling', 'red'),
                        )
                        line_offset += 1

                        self._result_canvas.create_text(
                            [x * 1, (y + (start_y + line_offset) * dy) * 1],
                            text='Ultimate class: ' + str(ml_class.get('ultimate', 'N/A')),
                            font=self._text_size["Text 9 bold"],
                            anchor='nw',
                            fill=ml_colors.get('ultimate', 'red'),
                        )
                        line_offset += 1

                    # -------------------------------------------------------------------------
                    # Numeric UF pipeline result
                    #
                    # The numeric UF values stored in state are already material-factored
                    # in get_color_and_calc_state(). The raw values are the model output
                    # for material factor = 1.0.
                    # -------------------------------------------------------------------------
                    if print_numeric_results:
                        numeric = state.get('ML buckling numeric', {}).get(current_line, None)
                        numeric_valid = state.get('ML buckling numeric valid', {}).get(current_line, {})
                        numeric_colors = state.get('ML buckling numeric colors', {}).get(current_line, {})

                        if numeric is not None:
                            numeric_is_valid = numeric_valid.get('valid prediction', None) == 1

                            if numeric_is_valid:
                                buckling_uf = numeric.get('buckling UF', float('inf'))
                                ultimate_uf = numeric.get('ultimate UF', float('inf'))

                                buckling_uf_raw = numeric.get('buckling UF raw', None)
                                ultimate_uf_raw = numeric.get('ultimate UF raw', None)

                                # Use the currently selected GUI material factor for display.
                                # The value in state['ML buckling numeric'] should already be
                                # multiplied by the material factor in get_color_and_calc_state().
                                numeric_mat_fac = self._new_material_factor.get()
                                buckling_uf_txt = f"{buckling_uf:.3f}"
                                ultimate_uf_txt = f"{ultimate_uf:.3f}"

                                if buckling_uf_raw is not None:
                                    buckling_uf_txt += f"  ({buckling_uf_raw:.3f} x {numeric_mat_fac:.2f})"

                                if ultimate_uf_raw is not None:
                                    ultimate_uf_txt += f"  ({ultimate_uf_raw:.3f} x {numeric_mat_fac:.2f})"

                            else:
                                buckling_uf_txt = 'invalid/NaN'
                                ultimate_uf_txt = 'invalid/NaN'

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Buckling UF numeric: ' + buckling_uf_txt,
                                font=self._text_size["Text 9 bold"],
                                anchor='nw',
                                fill=numeric_colors.get('buckling', 'red'),
                            )
                            line_offset += 1

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Ultimate UF numeric: ' + ultimate_uf_txt,
                                font=self._text_size["Text 9 bold"],
                                anchor='nw',
                                fill=numeric_colors.get('ultimate', 'red'),
                            )
                            line_offset += 1

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Numeric UF acceptance limit: <= 1.00',
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=self._color_text,
                            )
                            line_offset += 1

                            numeric_status = numeric_valid.get('valid label', '')
                            if numeric.get('error', ''):
                                numeric_status += ' | ' + numeric.get('error', '')

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Numeric UF status: ' + numeric_status,
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=self._color_text if numeric_is_valid else 'red',
                            )
                            line_offset += 1

                        else:
                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='Numeric UF: not available',
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=self._color_text,
                            )
                            line_offset += 1

                    # -------------------------------------------------------------------------
                    # CSR requirement result, shown for both ML classification and numeric modes
                    # -------------------------------------------------------------------------
                    ml_class = state.get('ML buckling class', {}).get(current_line, {})
                    ml_colors = state.get('ML buckling colors', {}).get(current_line, {})
                    csr = ml_class.get('CSR', None)

                    if csr is not None:
                        if obj_scnt_calc_pl.get_puls_sp_or_up() == 'SP':
                            csr_str = [
                                'Ok' if csr[0] == 1 else 'Not ok',
                                'Ok' if csr[1] == 1 else 'Not ok',
                                'Ok' if csr[2] == 1 else 'Not ok',
                                'Ok' if csr[3] == 1 else 'Not ok',
                            ]

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text=(
                                        'CSR requirements (stiffener):  plate-' + csr_str[0] +
                                        ' web-' + csr_str[1] +
                                        ' web/flange ratio-' + csr_str[2] +
                                        ' flange-' + csr_str[3]
                                ),
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=ml_colors.get('CSR requirement', 'red'),
                            )
                            line_offset += 1

                        else:
                            csr_str = 'Ok' if csr[0] == 1 else 'Not ok'

                            self._result_canvas.create_text(
                                [x * 1, (y + (start_y + line_offset) * dy) * 1],
                                text='CSR requirements (plate):  Plate slenderness - ' + csr_str,
                                font=self._text_size["Text 9"],
                                anchor='nw',
                                fill=ml_colors.get('CSR requirement', 'red'),
                            )
                            line_offset += 1

                    # Keep fatigue below the ML result block, with the old default as a minimum.
                    fatigue_start_offset = max(8, line_offset + 1.5)

                # fatigue results

                if self._line_to_struc[current_line][2] is not None and state['fatigue'][current_line][
                    'damage'] is not None:
                    damage = state['fatigue'][current_line]['damage']
                    dff = state['fatigue'][current_line]['dff']
                    fatigue_text = f"Fatigue DNVGL-RP-C203: Damage = {damage:.3f}  |  DFF = {dff}  |  DFF damage = {damage * dff:.3f}"
                else:
                    fatigue_text = "Fatigue DNVGL-RP-C203: NO RESULTS"

                self._result_canvas.create_text(
                    [x, y + (start_y + fatigue_start_offset) * dy],
                    text=fatigue_text,
                    font=self._text_size["Text 9 bold"],
                    anchor='nw',
                    fill=color_fatigue if "NO RESULTS" not in fatigue_text else self._color_text
                )

            elif self._active_line in self._line_to_struc and self._line_to_struc[self._active_line][5] is not None:

                '''
                Cylinder calculations
                    'cylinder' = {'Unstiffened shell': uf_unstf_shell,
                               'Longitudinal stiffened shell': uf_long_stf,
                               'Ring stiffened shell': uf_ring_stf,
                               'Heavy ring frame': uf_ring_frame,
                               'Column stability check': column_stability,
                               'Stiffener check': stiffener_check}
                '''
                cyl_obj = self._line_to_struc[self._active_line][5]
                key_mapper = {'Unstiffened shell': 'Shell buckling',
                              'Unstiffened conical shell': 'Conical shell buckling',
                              'Longitudinal stiffened shell': 'Panel Stiffener buckling',
                              'Ring stiffened shell': 'Panel Ring Buckling',
                              'Heavy ring frame': 'Heavy Ring Frame Buckling',
                              'Column stability check': 'Column stability check',
                              'Stiffener check': 'Stiffener check'}

                text = 'Results for cylinders and curved plates/panels:'
                self._result_canvas.create_text([x * 1, y * 1],
                                                text=text, font=self._text_size['Text 12 bold'], anchor='nw',
                                                fill=self._color_text)
                y_location = 3
                results = cyl_obj.get_utilization_factors()

                for key, value in results.items():
                    if key in ['Weight', 'Need to check column buckling', 'Column stability UF',
                               'Unstiffened conical shell detailed']:
                        continue
                    if key not in key_mapper and key not in ['Stiffener check detailed']:
                        continue

                    if all([key != 'Stiffener check', key != 'Stiffener check detailed']):
                        text_key = key
                        if key == 'Column stability check':
                            if 'Need to check column buckling' not in results.keys() and value is None:
                                continue
                            txt_type = 'Text 10'
                            if results.get('Need to check column buckling') == False:
                                if results['Column stability UF'] is None:
                                    text_value = 'N/A'
                                else:
                                    text_value = ('Column buckling does not need to be checked'
                                                  '\n- but UF = ' + str(round(results['Column stability UF'], 2))
                                                  )
                                uf_col = 'green'
                            elif 'Need to check column buckling' in results.keys():
                                uf_col = 'black'
                                if results['Column stability UF'] is None:
                                    text_value = 'N/A'
                                else:
                                    text_value = 'Column buckling need to be checked, UF = ' + str(
                                        round(results['Column stability UF'], 2))
                                    if results['Column stability UF'] <= 1.0:
                                        uf_col = 'green'
                                    else:
                                        uf_col = 'red'
                            else:
                                text_value = 'OK' if value else 'Not ok'
                                uf_col = 'green' if value else 'red'
                        else:
                            text_value = 'N/A' if value is None else str(round(value, 2))

                        if key != 'Column stability check':
                            txt_type = 'Text 10 bold'
                            if value is None:
                                uf_col = 'grey'
                            else:
                                uf_col = 'red' if any([value > 1, value == False]) else 'green'

                        self._result_canvas.create_text([x * 1, y + dy * y_location],
                                                        text=key_mapper[text_key], font=self._text_size[txt_type],
                                                        anchor='nw', fill=self._color_text)
                        self._result_canvas.create_text([dx * 20, dy * y_location],
                                                        text=text_value, font=self._text_size[txt_type], anchor='nw',
                                                        fill=uf_col)
                    elif key == 'Stiffener check':

                        if value is not None:
                            y_location += 1
                            self._result_canvas.create_text([x, dy * y_location],
                                                            text='Stiffener requirement checks:',
                                                            font=self._text_size['Text 10 bold'],
                                                            anchor='nw',
                                                            fill=self._color_text)
                            y_location += 1
                            idx_y, idx_x = 0, 0

                            for stf_type, chk_bool in value.items():
                                stf_text = stf_type
                                if stf_type == 'ring frame':
                                    continue

                                chk_text = 'OK' if chk_bool == True else 'failed' if chk_bool == False else 'N/A'

                                self._result_canvas.create_text([15 * dx * idx_x, dy * y_location],
                                                                text=stf_text, font=self._text_size['Text 10 bold'],
                                                                anchor='nw',
                                                                fill=self._color_text if not value else 'black')

                                self._result_canvas.create_text([15 * dx * idx_x, y + (y_location + 1) * dy],
                                                                text=chk_text, font=self._text_size['Text 10 bold'],
                                                                anchor='nw',
                                                                fill='green' if chk_bool == True else 'red' if
                                                                chk_bool == False else self._color_text)

                                self._result_canvas.create_text([15 * dx * idx_x, y + (y_location + 2) * dy],
                                                                text=results['Stiffener check detailed'][stf_type],
                                                                font=self._text_size['Text 10'],
                                                                anchor='nw',
                                                                fill='green' if chk_bool == True else 'red' if
                                                                chk_bool == False else self._color_text)
                                idx_y += 1
                                idx_x += 1

                    y_location += 1

    def clear_prop_3d(self):
        """Remove any embedded 3D preview from the lower drawing area."""
        if getattr(self, '_fea_pick_after_id', None) is not None:
            try:
                self._parent.after_cancel(self._fea_pick_after_id)
            except Exception:
                pass
            self._fea_pick_after_id = None

        if getattr(self, '_prop_3d_resize_after_id', None) is not None:
            try:
                self._parent.after_cancel(self._prop_3d_resize_after_id)
            except Exception:
                pass
            self._prop_3d_resize_after_id = None

        if getattr(self, '_prop_3d_fig_canvas', None) is not None:
            try:
                if getattr(self, '_fea_pick_cid', None) is not None:
                    self._prop_3d_fig_canvas.mpl_disconnect(self._fea_pick_cid)
            except Exception:
                pass
            self._fea_pick_cid = None

            try:
                self._prop_3d_fig_canvas.toolbar = None
            except Exception:
                pass

        if getattr(self, '_prop_3d_toolbar', None) is not None:
            try:
                # A Matplotlib 3D mouse callback can outlive the Tk widgets by
                # one event turn.  Make toolbar history updates harmless before
                # destroying the buttons it owns.
                self._prop_3d_toolbar.set_history_buttons = lambda *args, **kwargs: None
            except Exception:
                pass
            try:
                self._prop_3d_toolbar.destroy()
            except Exception:
                pass

        if getattr(self, '_prop_3d_frame', None) is not None:
            try:
                self._prop_3d_frame.destroy()
            except Exception:
                pass
        elif getattr(self, '_prop_3d_canvas_widget', None) is not None:
            try:
                self._prop_3d_canvas_widget.destroy()
            except Exception:
                pass

        self._prop_3d_canvas_widget = None
        self._prop_3d_fig_canvas = None
        self._prop_3d_frame = None
        self._prop_3d_toolbar = None
        self._prop_3d_axes = None
        self._prop_3d_tk3d_canvas = None
        self._prop_3d_default_view = (22, -55)
        self._fea_tk3d_canvas = None
        self._fea_tk3d_panel_records = {}
        self._fea_tk3d_click_origin = None
        self._fea_3d_selected_overlay = None
        self._fea_3d_panel_records = {}

    def _place_info_float(self, widget, key, default=0.0):
        """Return a numeric place() value, handling Tk's string values safely."""
        try:
            value = widget.place_info().get(key, default)
            return float(value)
        except Exception:
            return float(default)

    def _get_prop_3d_bottom_place(self):
        """Return placement for the 3D preview inside the property drawing area.

        Keep the 3D preview in the same lower-left area as the 2D property sketch.
        The result canvas on the lower-right must remain visible for result text.
        """
        try:
            if getattr(self, '_simplified_calculation_mode', False):
                return {
                    'relx': self._place_info_float(self._main_canvas, 'relx', 0.26),
                    'rely': self._place_info_float(self._main_canvas, 'rely', 0),
                    'relwidth': self._place_info_float(self._main_canvas, 'relwidth', 0.523),
                    'relheight': self._place_info_float(self._main_canvas, 'relheight', 0.73),
                }

            prop_relx = self._place_info_float(self._prop_canvas, 'relx', 0.26)
            prop_rely = self._place_info_float(self._prop_canvas, 'rely', 0.73)
            prop_relw = self._place_info_float(self._prop_canvas, 'relwidth', 0.38)
            prop_relh = self._place_info_float(self._prop_canvas, 'relheight', 0.27)

            return {
                'relx': prop_relx,
                'rely': prop_rely,
                'relwidth': prop_relw,
                'relheight': prop_relh,
            }
        except Exception:
            return {'relx': 0.26, 'rely': 0.73, 'relwidth': 0.38, 'relheight': 0.27}

    def _resize_prop_3d_figure(self, event=None):
        """Resize the Matplotlib figure to the actual available Tk frame size."""
        if getattr(self, '_prop_3d_fig_canvas', None) is None:
            return
        try:
            frame = self._prop_3d_frame
            fig = self._prop_3d_fig_canvas.figure
            dpi = float(fig.get_dpi())
            width_px = max(frame.winfo_width(), 300)
            toolbar_height = 0
            if getattr(self, '_prop_3d_toolbar', None) is not None:
                toolbar_height = max(self._prop_3d_toolbar.winfo_height(), 30)
            height_px = max(frame.winfo_height() - toolbar_height, 160)
            fig.set_size_inches(width_px / dpi, height_px / dpi, forward=True)
            # Use almost the full Tk drawing frame for the 3D axes.  The 3D
            # model itself is still protected from clipping by the data-limit
            # padding in _apply_prop_3d_layout(); using a small axes rectangle
            # here was the reason only about half of the available width was
            # visually used.
            fig.subplots_adjust(left=0.015, right=0.985, bottom=0.08, top=0.94)
            if getattr(self, '_prop_3d_axes', None) is not None:
                self._prop_3d_axes.set_position([0.015, 0.08, 0.97, 0.84])
            self._prop_3d_fig_canvas.draw_idle()
        except Exception:
            pass

    def _schedule_resize_prop_3d_figure(self, event=None):
        """Throttle figure resizing while the Tk frame is being laid out."""
        if getattr(self, '_prop_3d_resize_after_id', None) is not None:
            try:
                self._parent.after_cancel(self._prop_3d_resize_after_id)
            except Exception:
                pass
        self._prop_3d_resize_after_id = self._parent.after(80, self._resize_prop_3d_figure)

    def _embed_prop_3d(self, fig, ax, default_view=(22, -55)):
        """Embed a property preview through the application-wide viewer factory."""

        try:
            self._embed_prop_3d_tk3d(ax, default_view=default_view)
        except Exception as error:
            # Automatic fallback (GPU -> Tk) belongs to any3dview.create_viewer.
            # A Matplotlib fallback here would silently introduce a third
            # backend and hide an explicit GPU diagnostic from the user.
            self.clear_prop_3d()
            try:
                self._renderer_backend_status.set(
                    "Renderer preview unavailable: " + str(error)
                )
            except Exception:
                pass
            raise

    @staticmethod
    def _prop_3d_face_fill(color, alpha):
        """Tk fill colour + stipple for one recorded preview face."""
        try:
            fill = matplotlib.colors.to_hex(color if color else 'lightgrey')
        except Exception:
            fill = '#d1d5db'
        alpha = float(alpha if alpha is not None else 1.0)
        if alpha >= 0.94:
            stipple = ''
        elif alpha >= 0.6:
            stipple = 'gray75'
        elif alpha >= 0.4:
            stipple = 'gray50'
        else:
            stipple = 'gray25'
        return fill, stipple

    def _embed_prop_3d_tk3d(self, ax, default_view=(22, -55)):
        """Embed the property preview on the selected shared 3D backend.

        Draws the same solids that are recorded for IFC export and preserves
        the Matplotlib text: title, axis names and the SELECTED line, with the
        measured axis ruler providing the dimensions.
        """
        mesh = getattr(ax, '_anystruct_export_mesh', None)
        if not mesh or not mesh.get('faces'):
            raise ValueError('no recorded 3D preview mesh')

        self._prop_3d_axes = None
        self._prop_3d_export_mesh = mesh
        self._prop_3d_shell_export_mesh = getattr(ax, '_anystruct_shell_export_mesh', None)
        self._prop_3d_default_view = default_view

        try:
            self._prop_canvas.delete('all')
        except Exception:
            pass

        place = self._get_prop_3d_bottom_place()
        background = self._style.lookup('TFrame', 'background')
        self._prop_3d_frame = tk.Frame(self._main_fr, background=background, bd=0, highlightthickness=0)
        self._prop_3d_frame.place(**place)
        tk.Misc.lift(self._prop_3d_frame)

        toolbar_row = tk.Frame(self._prop_3d_frame, background=background, bd=0, highlightthickness=0)
        toolbar_row.pack(side=tk.TOP, fill=tk.X)

        header = tk.Frame(toolbar_row, background=background, bd=0, highlightthickness=0)
        header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(header, text='SELECTED: ' + str(self._active_line), foreground='red',
                  font=self._text_size['Text 8 bold']).pack(side=tk.LEFT, padx=(4, 10))
        title_text = str(ax.get_title() or '3D preview')
        ttk.Label(header, text=title_text, font=self._text_size['Text 8 bold']).pack(side=tk.LEFT, padx=(0, 10))
        axis_names = ' | '.join(part for part in (
            f'x: {ax.get_xlabel()}' if ax.get_xlabel() else '',
            f'y: {ax.get_ylabel()}' if ax.get_ylabel() else '',
            f'z: {ax.get_zlabel()}' if ax.get_zlabel() else '',
        ) if part)
        if axis_names:
            ttk.Label(header, text=axis_names, font=self._text_size['Text 8']).pack(side=tk.LEFT)

        tk3d = self._create_main_3d_viewer(self._prop_3d_frame, bg='white')
        self._prop_3d_tk3d_canvas = tk3d
        self._prop_3d_canvas_widget = event_widget(tk3d)

        view_row = tk.Frame(toolbar_row, background=background, bd=0, highlightthickness=0)
        view_row.pack(side=tk.RIGHT)
        self._add_renderer_selector(view_row)
        ttk.Button(
            view_row, text='Iso', width=4,
            command=lambda: self._prop_3d_tk3d_canvas.set_iso_view(),
        ).pack(side=tk.LEFT)
        ttk.Button(
            view_row, text='Top', width=4,
            command=lambda: self._prop_3d_tk3d_canvas.set_top_view(),
        ).pack(side=tk.LEFT)
        ttk.Button(
            view_row, text='Side', width=5,
            command=lambda: self._prop_3d_tk3d_canvas.set_side_view(),
        ).pack(side=tk.LEFT)
        ttk.Button(
            view_row, text='End', width=4,
            command=lambda: self._prop_3d_tk3d_canvas.set_front_view(),
        ).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Fit', width=4,
                   command=lambda: self._prop_3d_tk3d_canvas.fit_to_scene(
                       padding=1.18
                   )).pack(side=tk.LEFT)
        ttk.Checkbutton(view_row, text='Opposite side', variable=self._new_prop_3d_opposite_side,
                        command=self.update_frame).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(view_row, text='Solid export', width=10,
                   command=self.export_prop_3d_ifc_model).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Shell export', width=11,
                   command=self.export_prop_3d_ifc_shell_model).pack(side=tk.LEFT)

        tk3d.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        tk3d.set_axis_ruler(True)
        tk3d.set_mesh_lines(True)

        items = list(getattr(ax, '_anystruct_tk3d_items', ()) or ())
        self._prop_3d_tk3d_items = items
        original_request_redraw = getattr(tk3d, '_request_redraw', None)
        if callable(original_request_redraw):
            tk3d._request_redraw = lambda: None
        try:
            if items:
                self._populate_prop_3d_tk3d_native(tk3d, items)
            else:
                self._populate_prop_3d_tk3d_faces(tk3d, mesh)
        finally:
            if callable(original_request_redraw):
                tk3d._request_redraw = original_request_redraw
        invalidate = getattr(tk3d, '_invalidate_geometry_cache', None)
        if callable(invalidate):
            invalidate()
        tk3d.redraw()
        tk3d.set_iso_view()
        tk3d.after_idle(
            lambda: self._prop_3d_tk3d_canvas.fit_to_scene(padding=1.18)
        )

    def _populate_prop_3d_tk3d_native(self, tk3d, items):
        """Draw the preview with the canvas's native primitives.

        Follows the stiffened cylinder/plate examples in
        ``tkinter_3d_canvas_thickness_v6``: the plating is coloured by plate
        thickness with a thickness legend, and cylinder members are coloured by
        their own web/flange thicknesses through the same legend.
        """
        thickness_mm_values = sorted({
            round(float(value) * 1000.0, 2)
            for item in items
            for value in (
                item.get('thickness_m'),
                item.get('web_thickness_m'),
                item.get('flange_thickness_m'),
            )
            if value is not None and float(value) > 0.0
        })
        if thickness_mm_values:
            tk3d.set_thickness_legend(thickness_mm_values, unit='mm', title='Thickness')

        def thickness_fill(value_m, fallback):
            value_mm = float(value_m or 0.0) * 1000.0
            if thickness_mm_values and value_mm > 0.0:
                return tk3d.thickness_color(value_mm)
            return fallback

        for item in items:
            kind = item.get('kind')
            if kind == 'flat_plate':
                tk3d.add_rectangular_plate(
                    x_start=float(item['x0']), x_end=float(item['x1']),
                    y_start=float(item['y0']), y_end=float(item['y1']),
                    z=0.0,
                    color=thickness_fill(item.get('thickness_m'), '#d8e2ea'),
                    outline='#708090',
                )
            elif kind == 'flat_member':
                fill = thickness_fill(
                    item.get('web_thickness_m'),
                    '#a0a0ff' if item.get('orientation') == 'x' else '#ffa0a0',
                )
                outline = '#404080' if item.get('orientation') == 'x' else '#804040'
                if item.get('orientation') == 'x':
                    tk3d.add_flat_stiffener(
                        x_start=float(item['start']), x_end=float(item['end']),
                        y=float(item['station']), z_base=float(item['z_base']),
                        hw=float(item['hw']), b=float(item['flange_w']),
                        color=fill, outline=outline,
                    )
                else:
                    tk3d.add_flat_girder(
                        x=float(item['station']),
                        y_start=float(item['start']), y_end=float(item['end']),
                        z_base=float(item['z_base']),
                        ghw=float(item['hw']), gb=float(item['flange_w']),
                        color=fill, outline=outline,
                    )
            elif kind == 'cylinder_shell':
                length = float(item['length'])
                if item.get('is_panel'):
                    self._add_prop_3d_tk3d_sector_shell(
                        tk3d, item, thickness_fill(item.get('thickness_m'), '#d8e2ea'))
                else:
                    tk3d.add_cylinder(
                        radius=float(item['radius']),
                        radius_top=None if item.get('radius_top') is None else float(item['radius_top']),
                        height=length,
                        center=tkinter_3d_canvas.Point3D(0.0, 0.0, 0.5 * length),
                        color='#d8e2ea',
                        outline='#708090',
                        segments=48,
                        height_segments=24,
                        capped=False,
                        opacity=0.38,
                        show_backfaces=True,
                        plate_thickness=[float(item.get('thickness_m') or 0.0) * 1000.0],
                        thickness_unit='mm',
                        show_thickness_legend=False,
                    )
            elif kind == 'cylinder_long':
                length = float(item['length'])
                tk3d.add_longitudinal_stiffener(
                    radius=float(item['radius']),
                    height=length,
                    angle=float(item['angle']),
                    web_height=float(item['web_h']),
                    web_thickness=float(item.get('web_thickness_m') or 0.01),
                    flange_width=float(item.get('flange_w') or 0.0),
                    flange_thickness=float(item.get('flange_thickness_m') or 0.0),
                    color='#a0a0ff',
                    outline='#404080',
                    segments=4,
                    height_segments=16,
                    inside=float(item.get('side_sign', 1.0)) < 0.0,
                    z_offset=0.5 * length,
                )
            elif kind == 'cylinder_ring':
                if item.get('is_panel'):
                    self._add_prop_3d_tk3d_sector_ring(tk3d, item, thickness_fill(
                        item.get('web_thickness_m'),
                        '#d62728' if item.get('is_frame') else '#ffa0a0'))
                else:
                    tk3d.add_ring_stiffener(
                        radius=float(item['radius']),
                        z_position=float(item['z']),
                        web_height=float(item['web_h']),
                        web_thickness=float(item.get('web_thickness_m') or 0.01),
                        flange_width=float(item.get('flange_w') or 0.0),
                        flange_thickness=float(item.get('flange_thickness_m') or 0.0),
                        color='#d62728' if item.get('is_frame') else '#ffa0a0',
                        outline='#804040',
                        segments=48,
                        inside=float(item.get('side_sign', 1.0)) < 0.0,
                    )

    @staticmethod
    def _add_prop_3d_tk3d_sector_shell(tk3d, item, fill, segments=30, height_segments=12):
        """Curved-panel (sector) shell drawn as thickness-coloured quads."""
        radius = float(item['radius'])
        radius_top = float(item['radius_top']) if item.get('radius_top') is not None else radius
        length = float(item['length'])
        theta_start = float(item['theta_start'])
        theta_end = float(item['theta_end'])
        for j in range(height_segments):
            z0 = length * j / height_segments
            z1 = length * (j + 1) / height_segments
            r0 = radius + (radius_top - radius) * (z0 / length if length > 0 else 0.0)
            r1 = radius + (radius_top - radius) * (z1 / length if length > 0 else 0.0)
            for i in range(segments):
                a0 = theta_start + (theta_end - theta_start) * i / segments
                a1 = theta_start + (theta_end - theta_start) * (i + 1) / segments
                tk3d.add_polygon(
                    [
                        tkinter_3d_canvas.Point3D(r0 * math.cos(a0), r0 * math.sin(a0), z0),
                        tkinter_3d_canvas.Point3D(r0 * math.cos(a1), r0 * math.sin(a1), z0),
                        tkinter_3d_canvas.Point3D(r1 * math.cos(a1), r1 * math.sin(a1), z1),
                        tkinter_3d_canvas.Point3D(r1 * math.cos(a0), r1 * math.sin(a0), z1),
                    ],
                    color=fill,
                    outline='#708090',
                    stipple='gray50',
                    layer=5,
                )

    @staticmethod
    def _add_prop_3d_tk3d_sector_ring(tk3d, item, fill, segments=30):
        """Curved-panel (sector) ring web drawn as an annular quad strip."""
        radius = float(item['radius'])
        z_position = float(item['z'])
        side_sign = float(item.get('side_sign', 1.0))
        tip_radius = radius + side_sign * float(item['web_h'])
        theta_start = float(item['theta_start'])
        theta_end = float(item['theta_end'])
        for i in range(segments):
            a0 = theta_start + (theta_end - theta_start) * i / segments
            a1 = theta_start + (theta_end - theta_start) * (i + 1) / segments
            tk3d.add_polygon(
                [
                    tkinter_3d_canvas.Point3D(radius * math.cos(a0), radius * math.sin(a0), z_position),
                    tkinter_3d_canvas.Point3D(radius * math.cos(a1), radius * math.sin(a1), z_position),
                    tkinter_3d_canvas.Point3D(tip_radius * math.cos(a1), tip_radius * math.sin(a1), z_position),
                    tkinter_3d_canvas.Point3D(tip_radius * math.cos(a0), tip_radius * math.sin(a0), z_position),
                ],
                color=fill,
                outline='#804040',
                layer=12,
            )

    def _populate_prop_3d_tk3d_faces(self, tk3d, mesh):
        """Fallback: draw the recorded export-mesh faces directly."""
        vertices = mesh.get('vertices', [])
        face_colors = mesh.get('face_colors', [])
        for index, face in enumerate(mesh.get('faces', [])):
            points = [
                tkinter_3d_canvas.Point3D(*vertices[vertex_index - 1])
                for vertex_index in face
                if 0 < vertex_index <= len(vertices)
            ]
            if len(points) < 3:
                continue
            color, alpha = face_colors[index] if index < len(face_colors) else (None, 1.0)
            fill, stipple = self._prop_3d_face_fill(color, alpha)
            tk3d.add_polygon(points, color=fill, outline='#4b5563', width=1, stipple=stipple)

    def _embed_prop_3d_figure(self, fig, ax, default_view=(22, -55)):
        """Embed a legacy Matplotlib 3D figure for compatibility callers.

        Maintained application previews do not route here; they use the shared
        viewer factory. External integrations that called this historical
        helper directly retain it for the 0.5 transition.
        """
        self._prop_3d_axes = ax
        self._prop_3d_export_mesh = getattr(ax, '_anystruct_export_mesh', None)
        self._prop_3d_shell_export_mesh = getattr(ax, '_anystruct_shell_export_mesh', None)
        self._prop_3d_default_view = default_view

        # Hide only the old 2D property sketch.
        # Do NOT clear _result_canvas here: update_frame() draws the result text
        # before draw_prop(), so clearing _result_canvas from the 3D preview removes
        # the buckling/result text on the right-hand side.
        try:
            self._prop_canvas.delete('all')
        except Exception:
            pass

        place = self._get_prop_3d_bottom_place()
        self._prop_3d_frame = tk.Frame(
            self._main_fr,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        self._prop_3d_frame.place(**place)
        tk.Misc.lift(self._prop_3d_frame)

        toolbar_row = tk.Frame(
            self._prop_3d_frame,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        toolbar_row.pack(side=tk.TOP, fill=tk.X)

        # Matplotlib 3D can clip Poly3DCollection artists at the axes
        # rectangle when set_box_aspect(..., zoom=...) is used to make the
        # drawing wider.  Disable artist clipping before the first draw so
        # the model can use the available white plot area without being cut
        # by the internal axes boundary.
        self._disable_prop_3d_artist_clipping(ax)

        self._prop_3d_fig_canvas = FigureCanvasTkAgg(fig, master=self._prop_3d_frame)
        self._prop_3d_fig_canvas.draw()

        self._prop_3d_toolbar = NavigationToolbar2Tk(
            self._prop_3d_fig_canvas,
            toolbar_row,
            pack_toolbar=False,
        )
        self._prop_3d_toolbar.update()
        self._prop_3d_toolbar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        view_row = tk.Frame(
            toolbar_row,
            background=self._style.lookup('TFrame', 'background'),
            bd=0,
            highlightthickness=0,
        )
        view_row.pack(side=tk.RIGHT)

        ttk.Button(view_row, text='Iso', width=4,
                   command=lambda: self._set_prop_3d_view(default_view[0], default_view[1])).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Top', width=4,
                   command=lambda: self._set_prop_3d_view(90, -90)).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Side', width=5,
                   command=lambda: self._set_prop_3d_view(0, -90)).pack(side=tk.LEFT)
        ttk.Button(view_row, text='End', width=4,
                   command=lambda: self._set_prop_3d_view(0, 0)).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Reset', width=6,
                   command=self._reset_prop_3d_view).pack(side=tk.LEFT)
        ttk.Checkbutton(view_row, text='Opposite side', variable=self._new_prop_3d_opposite_side,
                        command=self.update_frame).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(view_row, text='Solid export', width=10,
                   command=self.export_prop_3d_ifc_model).pack(side=tk.LEFT)
        ttk.Button(view_row, text='Shell export', width=11,
                   command=self.export_prop_3d_ifc_shell_model).pack(side=tk.LEFT)

        self._prop_3d_canvas_widget = self._prop_3d_fig_canvas.get_tk_widget()
        self._prop_3d_canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        if getattr(self, '_simplified_calculation_mode', False):
            self._prop_3d_canvas_widget.bind('<MouseWheel>', self._prop_3d_mouse_scroll)
            self._prop_3d_canvas_widget.bind('<Button-4>', self._prop_3d_mouse_scroll)
            self._prop_3d_canvas_widget.bind('<Button-5>', self._prop_3d_mouse_scroll)

        self._prop_3d_frame.bind('<Configure>', self._schedule_resize_prop_3d_figure)
        self._prop_3d_frame.after(50, self._resize_prop_3d_figure)

    @staticmethod
    def _scaled_axis_limits(limits, zoom_factor):
        center = (float(limits[0]) + float(limits[1])) / 2.0
        half_span = (float(limits[1]) - float(limits[0])) * float(zoom_factor) / 2.0
        return center - half_span, center + half_span

    def _zoom_prop_3d_axes(self, zoom_factor):
        """Zoom the active 3D preview without changing its current view angle."""
        ax = getattr(self, '_prop_3d_axes', None)
        canvas = getattr(self, '_prop_3d_fig_canvas', None)
        if ax is None or canvas is None:
            return
        try:
            factor = min(max(float(zoom_factor), 0.2), 5.0)
            ax.set_xlim(*self._scaled_axis_limits(ax.get_xlim(), factor))
            ax.set_ylim(*self._scaled_axis_limits(ax.get_ylim(), factor))
            ax.set_zlim(*self._scaled_axis_limits(ax.get_zlim(), factor))
            canvas.draw_idle()
        except Exception:
            pass

    def _prop_3d_mouse_scroll(self, event):
        """Mouse-wheel zoom for embedded Matplotlib 3D previews."""
        if not any([
            getattr(self, '_simplified_calculation_mode', False),
            getattr(self, '_fea_buckling_mode', False),
        ]):
            return
        delta = getattr(event, 'delta', 0)
        if delta == 0:
            delta = 120 if getattr(event, 'num', None) == 4 else -120
        self._zoom_prop_3d_axes(0.88 if delta > 0 else 1.14)
        return 'break'

    def _set_prop_3d_view(self, elev, azim):
        """Set the active 3D preview to a predefined view angle."""
        if getattr(self, '_prop_3d_axes', None) is None:
            return
        self._prop_3d_axes.view_init(elev=elev, azim=azim)
        if getattr(self, '_prop_3d_fig_canvas', None) is not None:
            self._prop_3d_fig_canvas.draw_idle()

    def _reset_prop_3d_view(self):
        """Reset the Matplotlib navigation history / zoom for the 3D preview."""
        if getattr(self, '_prop_3d_toolbar', None) is not None:
            try:
                self._prop_3d_toolbar.home()
                return
            except Exception:
                pass
        if getattr(self, '_prop_3d_fig_canvas', None) is not None:
            self._prop_3d_fig_canvas.draw_idle()

    def _prop_3d_member_side_sign(self):
        try:
            return -1.0 if self._new_prop_3d_opposite_side.get() else 1.0
        except Exception:
            return 1.0

    def export_prop_3d_obj(self):
        """Export the current 3D preview mesh as an open Wavefront OBJ file."""
        mesh = getattr(self, '_prop_3d_export_mesh', None)
        if not mesh or len(mesh.get('faces', [])) == 0:
            messagebox.showinfo('3D export', 'No 3D preview mesh is available to export.')
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".obj",
            filetypes=[("Wavefront OBJ", "*.obj"), ("All files", "*.*")],
        )
        if filename in [None, '']:
            return

        try:
            self._write_prop_3d_obj_file(filename, mesh)
        except Exception as error:
            messagebox.showerror('3D export', 'Could not export 3D preview:\n' + str(error))
        else:
            messagebox.showinfo('3D export', '3D preview exported to:\n' + filename)

    def export_prop_3d_stl(self):
        """Deprecated compatibility wrapper for the old shell STL export.

        The old implementation exported the Matplotlib preview shell mesh.  That
        path is intentionally disabled because the CAD export shall be model-based
        only.  Existing keyboard shortcuts or external calls are redirected to the
        proper IFC/CAD exporter.
        """
        self.export_prop_3d_ifc_model()

    def _ask_prop_3d_ifc_export_options(self, shell_export=False):
        """Ask for IFC/CAD export format.

        IfcConvert is intentionally not exposed to the user.  For converted
        formats ANYstructure writes a proper IFC model first and then resolves
        the bundled/package IfcConvert executable automatically.
        """
        formats = [
            ('ifc', '.ifc', 'Native IFC-SPF model', 'IfcOpenShell-Python'),
            ('obj', '.obj', 'Wavefront OBJ', 'IfcConvert'),
            ('dae', '.dae', 'Collada DAE', 'IfcConvert'),
            ('glb', '.glb', 'Binary glTF GLB', 'IfcConvert'),
            ('stp', '.stp', 'STEP', 'IfcConvert'),
            ('igs', '.igs', 'IGES', 'IfcConvert'),
            ('xml', '.xml', 'XML', 'IfcConvert'),
            ('svg', '.svg', 'SVG', 'IfcConvert'),
            ('h5', '.h5', 'HDF5', 'IfcConvert'),
            ('ttl', '.ttl', 'TTL/WKT', 'IfcConvert'),
            ('rdb', '.rdb', 'RDB', 'IfcConvert'),
            ('json', '.json', 'JSON', 'IfcConvert'),
        ]
        format_by_label = {
            (ext + ' - ' + desc + ' (' + tool + ')'): (key, ext, desc, tool)
            for key, ext, desc, tool in formats
        }

        dialog = tk.Toplevel(self._parent)
        dialog.title('IFC / CAD export options')
        dialog.transient(self._parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        result = {'value': None}
        selected_format = tk.StringVar(value=list(format_by_label.keys())[0])
        transformation_scale = tk.StringVar(value='1.0')
        keep_ifc = tk.BooleanVar(value=False)
        boolean_join = tk.BooleanVar(value=False)

        pad = {'padx': 10, 'pady': 4}
        ttk.Label(
            dialog,
            text='Export the selected ANYstructure object as a proper IFC/CAD model.\n'
                 'Legacy shell STL/UNV preview-mesh export is disabled. '
                 'For OBJ/DAE/GLB/STP/IGS/XML/SVG/H5/TTL/RDB/JSON, ANYstructure first writes IFC, '
                 'then automatically runs the bundled/package IfcConvert executable.',
            justify=tk.LEFT,
        ).grid(row=0, column=0, columnspan=2, sticky='w', **pad)

        ttk.Label(dialog, text='Output format').grid(row=1, column=0, sticky='w', **pad)
        format_box = ttk.Combobox(
            dialog,
            textvariable=selected_format,
            values=list(format_by_label.keys()),
            width=58,
            state='readonly',
        )
        format_box.grid(row=1, column=1, sticky='we', **pad)

        ttk.Label(dialog, text='Transformation scale').grid(row=2, column=0, sticky='w', **pad)
        scale_entry = ttk.Entry(
            dialog,
            textvariable=transformation_scale,
            width=18,
        )
        scale_entry.grid(row=2, column=1, sticky='w', **pad)

        keep_chk = ttk.Checkbutton(
            dialog,
            text='Keep intermediate .ifc file when converting to another format',
            variable=keep_ifc,
        )
        keep_chk.grid(row=3, column=1, sticky='w', **pad)

        join_chk = ttk.Checkbutton(
            dialog,
            text='Join all solid parts into one complete model',
            variable=boolean_join,
        )
        join_chk.grid(row=4, column=1, sticky='w', **pad)

        note_var = tk.StringVar()
        ttk.Label(dialog, textvariable=note_var, justify=tk.LEFT, foreground='gray25').grid(
            row=5, column=0, columnspan=2, sticky='w', **pad
        )

        def update_state(*_args):
            key, _ext, _desc, _tool = format_by_label[selected_format.get()]
            needs_ifcconvert = key != 'ifc'
            try:
                keep_chk.configure(state='normal' if needs_ifcconvert else 'disabled')
            except Exception:
                pass
            try:
                join_chk.configure(state='disabled' if shell_export else 'normal')
            except Exception:
                pass
            if needs_ifcconvert:
                note_text = (
                    'Automatic processing: no user path is required. IfcConvert.exe is resolved from the installed '
                    'anystruct package, the PyInstaller bundle, or PATH. Include IfcConvert.exe as package data.'
                )
            else:
                note_text = 'Native IFC export does not require IfcConvert.'
            if shell_export:
                note_text += ' Boolean join is only available for solid export.'
            note_var.set(note_text)

        selected_format.trace_add('write', update_state)
        update_state()

        button_row = ttk.Frame(dialog)
        button_row.grid(row=6, column=0, columnspan=2, sticky='e', padx=10, pady=(8, 10))

        def accept():
            key, ext, desc, tool = format_by_label[selected_format.get()]
            try:
                scale = float(transformation_scale.get())
                if not math.isfinite(scale) or scale <= 0.0:
                    raise ValueError
            except (TypeError, ValueError):
                messagebox.showerror(
                    'IFC / CAD export options',
                    'Transformation scale must be a positive number.'
                )
                return
            result['value'] = {
                'format': key,
                'extension': ext,
                'description': desc,
                'tool': tool,
                'keep_intermediate_ifc': bool(keep_ifc.get()),
                'boolean_join_all_solids': bool(boolean_join.get()) and not bool(shell_export),
                'transformation_scale': scale,
            }
            dialog.destroy()

        def cancel():
            result['value'] = None
            dialog.destroy()

        ttk.Button(button_row, text='Cancel', command=cancel).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(button_row, text='Continue', command=accept).pack(side=tk.RIGHT)

        dialog.bind('<Return>', lambda _event: accept())
        dialog.bind('<Escape>', lambda _event: cancel())

        try:
            self._parent.update_idletasks()
            x = self._parent.winfo_rootx() + 120
            y = self._parent.winfo_rooty() + 90
            dialog.geometry('+' + str(x) + '+' + str(y))
        except Exception:
            pass

        self._parent.wait_window(dialog)
        return result['value']

    def export_prop_3d_ifc_model(self):
        """Export the selected structure as a proper model-based IFC/CAD file.

        This button keeps the existing CAD-format workflow: the user selects IFC,
        STEP, IGES, OBJ, GLB, etc.  The geometry is still generated from the
        ANYstructure model parameters, not from the Matplotlib preview mesh.
        """
        self._export_prop_3d_ifc_model_common(shell_export=False)

    def export_prop_3d_ifc_shell_model(self):
        """Export the selected structure as a zero-thickness shell/surface model.

        Plate, stiffener web, stiffener flange, girder web and girder flange are
        exported as single shell plates.  Nominal thicknesses are written only as
        IFC properties.  The Opposite side checkbox is respected by flipping the
        web/flange surfaces to the other side of the plate interface.
        """
        self._export_prop_3d_ifc_model_common(shell_export=True)

    def _export_prop_3d_ifc_model_common(self, shell_export=False):
        """Common IFC/CAD export implementation for model and shell buttons.

        The exporter is intentionally not based on _get_prop_3d_solid_export_mesh()
        or _get_prop_3d_shell_export_mesh().  Geometry is rebuilt from the selected
        ANYstructure plate/stiffener/girder/cylinder objects.
        """
        if not self._line_is_active or self._active_line not in self._line_to_struc:
            messagebox.showinfo(
                'IFC export',
                'Select a line with assigned structure properties before exporting IFC.'
            )
            return

        options = self._ask_prop_3d_ifc_export_options(shell_export=shell_export)
        if options is None:
            return

        ext = options['extension']
        title = 'Shell surface export' if shell_export else options['description']
        filename = filedialog.asksaveasfilename(
            defaultextension=ext,
            confirmoverwrite=False,
            filetypes=[
                (title, '*' + ext),
                ('Industry Foundation Classes', '*.ifc'),
                ('All files', '*.*'),
            ],
        )
        if filename in [None, '']:
            return
        if os.path.exists(filename):
            if not messagebox.askyesno(
                    'IFC export',
                    'The selected file already exists:\n' + filename + '\n\nOverwrite it?'):
                return

        try:
            try:
                from anystruct import ifc_model_export
            except ModuleNotFoundError:
                from ANYstructure.anystruct import ifc_model_export

            summary = ifc_model_export.export_selected_structure_from_application(
                self,
                filename,
                output_format=options['format'],
                keep_intermediate_ifc=options['keep_intermediate_ifc'],
                shell_export=shell_export,
                boolean_join_all_solids=options.get('boolean_join_all_solids', False),
                transformation_scale=options.get('transformation_scale', 1.0),
            )
        except ImportError as error:
            messagebox.showerror(
                'IFC export',
                str(error)
            )
        except FileNotFoundError as error:
            messagebox.showerror(
                'IFC export',
                str(error)
            )
        except Exception as error:
            messagebox.showerror(
                'IFC export',
                'Could not export IFC/CAD model:\n' + str(error)
            )
        else:
            export_kind = 'Shell/surface model' if shell_export else 'Model-based CAD/IFC export'
            message = (
                'Export completed:\n' + filename +
                '\n\nExport type: ' + export_kind +
                '\nFormat: ' + options['extension'] + ' via ' + options['tool'] +
                '\nTransformation scale: ' + str(options.get('transformation_scale', 1.0)) +
                '\nElements exported: ' + str(summary.element_count)
            )
            if options.get('boolean_join_all_solids', False):
                message += '\nJoined model: complete solid model exported as one IFC product'
            if getattr(summary, 'native_ifc_filename', None) and summary.native_ifc_filename != filename:
                message += '\nSource IFC: ' + str(summary.native_ifc_filename)
            if getattr(summary, 'warnings', None):
                message += '\n\nWarnings:\n' + '\n'.join('- ' + str(item) for item in summary.warnings)
            messagebox.showinfo('IFC export', message)

    def export_prop_3d_unv(self):
        """Deprecated compatibility wrapper for the old shell UNV export.

        The old implementation exported the Matplotlib preview shell mesh.  That
        path is intentionally disabled because the CAD export shall be model-based
        only.  Existing keyboard shortcuts or external calls are redirected to the
        proper IFC/CAD exporter.
        """
        self.export_prop_3d_ifc_model()

    def _get_prop_3d_shell_export_mesh(self):
        return getattr(self, '_prop_3d_shell_export_mesh', None)

    def _get_prop_3d_solid_export_mesh(self):
        return getattr(self, '_prop_3d_export_mesh', None)

    @staticmethod
    def _write_prop_3d_obj_file(filename, mesh):
        export_mesh = Application._refined_export_mesh(mesh)
        with open(filename, 'w', encoding='utf-8') as obj_file:
            obj_file.write('# ANYstructure 3D preview export\n')
            obj_file.write('o ' + str(mesh.get('name', 'ANYstructure_preview')).replace(' ', '_') + '\n')
            for x, y, z in export_mesh.get('vertices', []):
                obj_file.write('v {:.9g} {:.9g} {:.9g}\n'.format(float(x), float(y), float(z)))
            for face in export_mesh.get('faces', []):
                obj_file.write('f ' + ' '.join(str(index) for index in face) + '\n')

    @staticmethod
    def _write_prop_3d_stl_file(filename, mesh):
        name = str(mesh.get('name', 'ANYstructure_preview')).replace(' ', '_')
        export_mesh = Application._refined_export_mesh(mesh)
        vertices = export_mesh.get('vertices', [])
        with open(filename, 'w', encoding='utf-8') as stl_file:
            stl_file.write('solid ' + name + '\n')
            for face in export_mesh.get('faces', []):
                face_vertices = [vertices[index - 1] for index in face]
                for tri in Application._triangulate_export_face(face_vertices):
                    normal = Application._stl_triangle_normal(tri)
                    stl_file.write('  facet normal {:.9g} {:.9g} {:.9g}\n'.format(*normal))
                    stl_file.write('    outer loop\n')
                    for x, y, z in tri:
                        stl_file.write('      vertex {:.9g} {:.9g} {:.9g}\n'.format(float(x), float(y), float(z)))
                    stl_file.write('    endloop\n')
                    stl_file.write('  endfacet\n')
            stl_file.write('endsolid ' + name + '\n')

    @staticmethod
    def _write_prop_3d_unv_file(filename, mesh):
        unique_vertices, face_indices = Application._deduplicate_export_mesh(Application._refined_export_mesh(mesh))
        triangles = []
        for face in face_indices:
            triangles.extend(Application._triangulate_export_face(face))

        if not unique_vertices or not triangles:
            raise ValueError('No valid mesh nodes or shell elements are available for UNV export.')

        lines = ['    -1\n', '  2411\n']
        for node_id, (x, y, z) in enumerate(unique_vertices, start=1):
            lines.append('{:10d}{:10d}{:10d}{:10d}\n'.format(node_id, 1, 1, 11))
            lines.append('{}{}{}\n'.format(
                Application._format_unv_float(x),
                Application._format_unv_float(y),
                Application._format_unv_float(z),
            ))
        lines.extend(['    -1\n', '    -1\n', '  2412\n'])
        for element_id, tri in enumerate(triangles, start=1):
            lines.append('{:10d}{:10d}{:10d}{:10d}{:10d}{:10d}\n'.format(
                element_id, 91, 1, 1, 7, 3
            ))
            lines.append('{:10d}{:10d}{:10d}\n'.format(*tri))
        lines.append('    -1\n')

        with open(filename, 'w', encoding='utf-8') as unv_file:
            unv_file.writelines(lines)

    @staticmethod
    def _format_unv_float(value):
        return '{:25.16E}'.format(float(value)).replace('E', 'D')

    @staticmethod
    def _deduplicate_export_mesh(mesh):
        unique_vertices = []
        index_by_vertex = {}
        face_indices = []
        for face in mesh.get('faces', []):
            current_face = []
            for vertex_index in face:
                vertex = mesh['vertices'][vertex_index - 1]
                key = tuple(round(float(coord), 12) for coord in vertex)
                if key not in index_by_vertex:
                    index_by_vertex[key] = len(unique_vertices) + 1
                    unique_vertices.append(tuple(float(coord) for coord in vertex))
                current_face.append(index_by_vertex[key])
            face_indices.append(current_face)
        return unique_vertices, face_indices

    @staticmethod
    def _triangulate_export_face(face_vertices):
        if len(face_vertices) < 3:
            return []
        if len(face_vertices) == 3:
            return [face_vertices]
        return [[face_vertices[0], face_vertices[idx], face_vertices[idx + 1]]
                for idx in range(1, len(face_vertices) - 1)]

    @staticmethod
    def _stl_triangle_normal(triangle):
        p0 = np.asarray(triangle[0], dtype=float)
        p1 = np.asarray(triangle[1], dtype=float)
        p2 = np.asarray(triangle[2], dtype=float)
        normal = np.cross(p1 - p0, p2 - p0)
        norm = np.linalg.norm(normal)
        if norm <= 1e-12:
            return 0.0, 0.0, 0.0
        normal = normal / norm
        return float(normal[0]), float(normal[1]), float(normal[2])

    @staticmethod
    def _init_prop_3d_export_mesh(ax, name):
        mesh = {'name': name, 'vertices': [], 'faces': [], 'max_edge_length': None}
        shell_mesh = {'name': name + '_shell', 'vertices': [], 'faces': [], 'max_edge_length': None}
        ax._anystruct_export_mesh = mesh
        ax._anystruct_shell_export_mesh = shell_mesh
        return mesh

    @staticmethod
    def _update_prop_3d_export_mesh_size(ax, dims):
        mesh = getattr(ax, '_anystruct_export_mesh', None)
        shell_mesh = getattr(ax, '_anystruct_shell_export_mesh', None)
        if mesh is None and shell_mesh is None:
            return
        candidates = []
        try:
            flange_w = float(dims.get('flange_w', 0.0))
            if flange_w > 1e-9:
                candidates.append(flange_w / 2.0)
        except Exception:
            pass
        try:
            web_h = float(dims.get('web_h', 0.0))
            if web_h > 1e-9:
                candidates.append(web_h / 2.0)
        except Exception:
            pass
        if not candidates:
            return
        candidate = min(candidates)
        for export_mesh in (mesh, shell_mesh):
            if export_mesh is None:
                continue
            current = export_mesh.get('max_edge_length', None)
            export_mesh['max_edge_length'] = candidate if current in [None, 0] else min(float(current), candidate)

    @staticmethod
    def _record_prop_3d_tk3d_item(ax, **item):
        """Record one native Tk-3D primitive for the property preview replay."""
        items = getattr(ax, '_anystruct_tk3d_items', None)
        if items is None:
            items = []
            ax._anystruct_tk3d_items = items
        items.append(item)

    @staticmethod
    def _append_faces_to_prop_3d_export_mesh(ax, face_vertices, shell_model=False, color=None, alpha=1.0):
        mesh = getattr(ax, '_anystruct_shell_export_mesh' if shell_model else '_anystruct_export_mesh', None)
        if mesh is None:
            return
        for face in face_vertices:
            start_index = len(mesh['vertices']) + 1
            mesh['vertices'].extend([(float(x), float(y), float(z)) for x, y, z in face])
            mesh['faces'].append(list(range(start_index, start_index + len(face))))
            mesh.setdefault('face_colors', []).append((color, float(alpha)))

    @staticmethod
    def _append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, shell_model=False,
                                                    color=None, alpha=1.0):
        mesh = getattr(ax, '_anystruct_shell_export_mesh' if shell_model else '_anystruct_export_mesh', None)
        if mesh is None:
            return
        x_grid = np.asarray(x_grid)
        y_grid = np.asarray(y_grid)
        z_grid = np.asarray(z_grid)
        if x_grid.ndim != 2 or x_grid.shape[0] < 2 or x_grid.shape[1] < 2:
            return
        rows, cols = x_grid.shape
        for row in range(rows - 1):
            for col in range(cols - 1):
                face = [
                    (x_grid[row, col], y_grid[row, col], z_grid[row, col]),
                    (x_grid[row, col + 1], y_grid[row, col + 1], z_grid[row, col + 1]),
                    (x_grid[row + 1, col + 1], y_grid[row + 1, col + 1], z_grid[row + 1, col + 1]),
                    (x_grid[row + 1, col], y_grid[row + 1, col], z_grid[row + 1, col]),
                ]
                start_index = len(mesh['vertices']) + 1
                mesh['vertices'].extend([(float(x), float(y), float(z)) for x, y, z in face])
                mesh['faces'].append(list(range(start_index, start_index + 4)))
                mesh.setdefault('face_colors', []).append((color, float(alpha)))

    @staticmethod
    def _append_flat_plate_shell_grid_to_prop_3d_export_mesh(ax, x_breaks, y_breaks, z_value=0.0):
        mesh = getattr(ax, '_anystruct_shell_export_mesh', None)
        if mesh is None:
            return

        def unique_sorted(values):
            result = []
            for value in sorted(float(item) for item in values):
                if not result or abs(value - result[-1]) > 1e-9:
                    result.append(value)
            return result

        x_values = unique_sorted(x_breaks)
        y_values = unique_sorted(y_breaks)
        if len(x_values) < 2 or len(y_values) < 2:
            return

        for x0, x1 in zip(x_values[:-1], x_values[1:]):
            if x1 - x0 <= 1e-9:
                continue
            for y0, y1 in zip(y_values[:-1], y_values[1:]):
                if y1 - y0 <= 1e-9:
                    continue
                start_index = len(mesh['vertices']) + 1
                mesh['vertices'].extend([
                    (x0, y0, float(z_value)), (x1, y0, float(z_value)),
                    (x1, y1, float(z_value)), (x0, y1, float(z_value)),
                ])
                mesh['faces'].append(list(range(start_index, start_index + 4)))

    @staticmethod
    def _refined_export_mesh(mesh):
        max_edge_length = mesh.get('max_edge_length', None)
        if max_edge_length in [None, 0]:
            return mesh
        refined = {'name': mesh.get('name', 'ANYstructure_preview'), 'vertices': [], 'faces': [],
                   'max_edge_length': max_edge_length}
        for face in mesh.get('faces', []):
            face_vertices = [mesh['vertices'][index - 1] for index in face]
            for refined_face in Application._subdivide_export_face(face_vertices, max_edge_length):
                start_index = len(refined['vertices']) + 1
                refined['vertices'].extend([(float(x), float(y), float(z)) for x, y, z in refined_face])
                refined['faces'].append(list(range(start_index, start_index + len(refined_face))))
        return refined

    @staticmethod
    def _subdivide_export_face(face_vertices, max_edge_length):
        if len(face_vertices) != 4:
            return [face_vertices]
        p00 = np.asarray(face_vertices[0], dtype=float)
        p10 = np.asarray(face_vertices[1], dtype=float)
        p11 = np.asarray(face_vertices[2], dtype=float)
        p01 = np.asarray(face_vertices[3], dtype=float)
        u_len = max(np.linalg.norm(p10 - p00), np.linalg.norm(p11 - p01))
        v_len = max(np.linalg.norm(p01 - p00), np.linalg.norm(p11 - p10))
        u_count = max(1, int(math.ceil(u_len / max_edge_length)))
        v_count = max(1, int(math.ceil(v_len / max_edge_length)))

        def interp(u_value, v_value):
            return ((1.0 - u_value) * (1.0 - v_value) * p00 +
                    u_value * (1.0 - v_value) * p10 +
                    u_value * v_value * p11 +
                    (1.0 - u_value) * v_value * p01)

        faces = []
        for u_idx in range(u_count):
            u0 = u_idx / u_count
            u1 = (u_idx + 1) / u_count
            for v_idx in range(v_count):
                v0 = v_idx / v_count
                v1 = (v_idx + 1) / v_count
                faces.append([tuple(interp(u0, v0)), tuple(interp(u1, v0)),
                              tuple(interp(u1, v1)), tuple(interp(u0, v1))])
        return faces

    @staticmethod
    def _disable_prop_3d_artist_clipping(ax):
        """Allow 3D preview artists to draw outside the internal axes box.

        The Tk frame may be wide enough, but mplot3d clips surfaces and
        Poly3DCollections at the axes rectangle.  This is especially visible
        when set_box_aspect(..., zoom=...) is increased: the model becomes
        wider, but vertical cut lines appear inside the available white plot
        area.  Turning clipping off for the model artists keeps the result
        text area untouched while letting the 3D preview use the property
        canvas width.
        """
        try:
            ax.set_clip_on(False)
        except Exception:
            pass

        for artist_list_name in ('collections', 'lines', 'patches'):
            try:
                artists = getattr(ax, artist_list_name, [])
            except Exception:
                artists = []
            for artist in list(artists):
                try:
                    artist.set_clip_on(False)
                except Exception:
                    pass
                try:
                    artist.set_clip_box(None)
                except Exception:
                    pass
                try:
                    artist.set_clip_path(None)
                except Exception:
                    pass

    @staticmethod
    def _set_axes_equal_3d(ax):
        """Make x/y/z axes visually comparable in a Matplotlib 3D plot."""
        try:
            x_limits = ax.get_xlim3d()
            y_limits = ax.get_ylim3d()
            z_limits = ax.get_zlim3d()
            x_range = abs(x_limits[1] - x_limits[0])
            y_range = abs(y_limits[1] - y_limits[0])
            z_range = abs(z_limits[1] - z_limits[0])
            max_range = max(x_range, y_range, z_range, 1e-9)
            x_mid = sum(x_limits) / 2.0
            y_mid = sum(y_limits) / 2.0
            z_mid = sum(z_limits) / 2.0
            ax.set_xlim3d([x_mid - max_range / 2.0, x_mid + max_range / 2.0])
            ax.set_ylim3d([y_mid - max_range / 2.0, y_mid + max_range / 2.0])
            ax.set_zlim3d([z_mid - max_range / 2.0, z_mid + max_range / 2.0])
        except Exception:
            pass

    @staticmethod
    def _apply_prop_3d_layout(fig, ax, x_span, y_span, z_span, zoom=1.55):
        """Make the 3D axes use the full available Tk plot area.

        The lower Tk frame can be wide while Matplotlib still draws the 3D box
        in a small central part of the figure.  The important part is to make
        the *axes rectangle* full width, then use set_box_aspect(..., zoom=...)
        to enlarge the 3D box inside that rectangle.  Data limits are padded by
        the caller, so this can be wider without clipping the model. Keep a small figure margin; true full-bleed axes clip 3D artists in Tk.
        """
        x_span = max(float(x_span), 1e-6)
        y_span = max(float(y_span), 1e-6)
        z_span = max(float(z_span), 1e-6)

        try:
            # Orthographic projection uses the horizontal space more predictably
            # for engineering previews and avoids the perspective shrink that
            # made long panels look narrow in the middle of a wide canvas.
            ax.set_proj_type('ortho')
        except Exception:
            pass

        try:
            ax.set_box_aspect((x_span, y_span, z_span), zoom=zoom)
        except TypeError:
            try:
                ax.set_box_aspect((x_span, y_span, z_span))
            except Exception:
                pass
        except Exception:
            pass

        try:
            fig.subplots_adjust(left=0.015, right=0.985, bottom=0.08, top=0.94)
            ax.set_position([0.015, 0.08, 0.97, 0.84])
        except Exception:
            pass

    @staticmethod
    def _add_box_3d(ax, x0, x1, y0, y1, z0, z1, facecolor='lightgrey', alpha=0.75,
                    edgecolor='black', linewidth=0.35):
        """Add a rectangular solid to a Matplotlib 3D axis."""
        vertices = [
            [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
            [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
            [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
            [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        ]
        poly = Poly3DCollection(vertices, alpha=alpha, facecolor=facecolor,
                                edgecolor=edgecolor, linewidths=linewidth, antialiaseds=True)
        try:
            poly.set_clip_on(False)
            poly.set_clip_box(None)
            poly.set_clip_path(None)
        except Exception:
            pass
        ax.add_collection3d(poly)
        Application._append_faces_to_prop_3d_export_mesh(ax, vertices, color=facecolor, alpha=alpha)
        return poly

    @staticmethod
    def _safe_obj_float(obj, getter_names=(), attr_names=(), default=0.0):
        """Read a float from one of several getter/attribute names."""
        for name in getter_names:
            try:
                value = getattr(obj, name)()
                if value is not None:
                    return float(value)
            except Exception:
                pass
        for name in attr_names:
            try:
                value = getattr(obj, name)
                if value is not None:
                    return float(value)
            except Exception:
                pass
        return float(default)

    def _get_section_3d_dimensions(self, section_obj):
        """Return section dimensions in metres using ANYstructure getters/attributes."""
        return {
            'spacing': self._safe_obj_float(section_obj, ('get_s',), ('spacing', 's'), 0.75),
            'plate_thk': self._safe_obj_float(section_obj, ('get_pl_thk',), ('plate_thk', 'pl_thk', 'thk'), 0.02),
            'web_h': self._safe_obj_float(section_obj, ('get_web_h',), ('web_h', 'hw'), 0.4),
            'web_thk': self._safe_obj_float(section_obj, ('get_web_thk',), ('web_thk', 'tw'), 0.012),
            'flange_w': self._safe_obj_float(section_obj, ('get_fl_w',), ('fl_w', 'b'), 0.15),
            'flange_thk': self._safe_obj_float(section_obj, ('get_fl_thk',), ('fl_thk', 'tf'), 0.02),
            'type': self._get_section_3d_type(section_obj),
        }

    @staticmethod
    def _get_section_3d_type(section_obj):
        try:
            return section_obj.get_stiffener_type()
        except Exception:
            try:
                return section_obj.stiffener_type
            except Exception:
                try:
                    return section_obj.stf_type
                except Exception:
                    return 'T'

    @staticmethod
    def _normalise_preview_length_to_m(value, default=0.0):
        """Return a preview length in metres.

        Stored ANYstructure objects normally use metres, while GUI entries use mm.
        This helper accepts both so the 3D preview can use line-object values first
        and safely fall back to GUI values.
        """
        try:
            value = float(value)
        except Exception:
            return float(default)
        if value <= 0.0:
            return float(default)
        # Values from GUI fields are normally mm, e.g. LG = 10000.
        # Object values are normally m, e.g. girder_lg = 10.
        return value / 1000.0 if value > 100.0 else value

    @staticmethod
    def _normalise_imperfection_length_to_mm(value, default=0.0):
        """Return an imperfection basis length in mm from m or mm inputs."""
        try:
            value = float(value)
        except Exception:
            return float(default)
        if value <= 0.0:
            return float(default)
        return value * 1000.0 if value < 50.0 else value

    @staticmethod
    def _imperfection_row(detail, formula, value_mm, basis, sketch='member_straightness'):
        return {
            'detail': detail,
            'formula': formula,
            'value_mm': max(float(value_mm), 0.0),
            'basis': basis,
            'sketch': sketch,
        }

    @staticmethod
    def _format_imperfection_value(value_mm):
        if value_mm >= 10.0:
            return str(round(value_mm, 1)) + ' mm'
        if value_mm >= 1.0:
            return str(round(value_mm, 2)) + ' mm'
        return str(round(value_mm, 3)) + ' mm'

    @staticmethod
    def _flat_panel_imperfection_recommendations(all_obj):
        """Return DNVGL-OS-C401 imperfection amplitudes for the active flat panel."""
        rows = []
        if all_obj is None or getattr(all_obj, 'Plate', None) is None:
            return rows

        plate = all_obj.Plate
        spacing_mm = Application._normalise_imperfection_length_to_mm(
            Application._safe_obj_float(plate, ('get_s',), ('spacing',), 0.0)
        )
        span_mm = Application._normalise_imperfection_length_to_mm(
            Application._safe_obj_float(plate, ('get_span',), ('span',), 0.0)
        )

        if spacing_mm > 0.0:
            rows.append(Application._imperfection_row(
                'Plate out-of-plane',
                'delta = 0.005 s',
                0.005 * spacing_mm,
                's = ' + Application._format_imperfection_value(spacing_mm),
                sketch='plate_out_of_plane',
            ))

        for label, member in [('Stiffener', getattr(all_obj, 'Stiffener', None)),
                              ('Girder', getattr(all_obj, 'Girder', None))]:
            if member is None:
                continue
            member_spacing_mm = Application._normalise_imperfection_length_to_mm(
                Application._safe_obj_float(member, ('get_s',), ('spacing', 's'), spacing_mm)
            )
            if label == 'Girder':
                member_span = Application._safe_obj_float(member, (), ('girder_lg', '_girder_lg'), 0.0)
                if member_span <= 0.0:
                    member_span = Application._safe_obj_float(member, ('get_span',), ('span',), span_mm)
            else:
                member_span = Application._safe_obj_float(member, ('get_span',), ('span',), span_mm)
            member_span_mm = Application._normalise_imperfection_length_to_mm(member_span)
            if member_span_mm > 0.0:
                rows.append(Application._imperfection_row(
                    label + ' web straightness',
                    'delta = 0.0015 l',
                    0.0015 * member_span_mm,
                    'l = ' + Application._format_imperfection_value(member_span_mm),
                    sketch='member_straightness',
                ))
                flange_width_mm = Application._normalise_imperfection_length_to_mm(
                    Application._safe_obj_float(member, ('get_fl_w',), ('fl_w', 'b'), 0.0)
                )
                if flange_width_mm > 0.0:
                    rows.append(Application._imperfection_row(
                        label + ' flange straightness',
                        'delta = 0.0015 l',
                        0.0015 * member_span_mm,
                        'l = ' + Application._format_imperfection_value(member_span_mm),
                        sketch='flange_straightness',
                    ))
            if member_spacing_mm > 0.0:
                rows.append(Application._imperfection_row(
                    'Parallel ' + label.lower() + ' misalignment',
                    'delta = 0.02 s',
                    0.02 * member_spacing_mm,
                    's = ' + Application._format_imperfection_value(member_spacing_mm),
                    sketch='parallel_misalignment',
                ))
        return rows

    @staticmethod
    def _cylinder_imperfection_recommendations(cyl_obj):
        """Return DNVGL-OS-C401 imperfection amplitudes for the active cylinder."""
        rows = []
        if cyl_obj is None or getattr(cyl_obj, 'ShellObj', None) is None:
            return rows

        shell = cyl_obj.ShellObj
        radius_mm = Application._normalise_imperfection_length_to_mm(
            Application._safe_obj_float(shell, (), ('radius',), 0.0)
        )
        thickness_mm = Application._normalise_imperfection_length_to_mm(
            Application._safe_obj_float(shell, (), ('thk', 't'), 0.0)
        )
        ring_spacing_mm = Application._normalise_imperfection_length_to_mm(
            Application._safe_obj_float(shell, (), ('dist_between_rings', 'length_of_shell', 'tot_cyl_length'), 0.0)
        )
        panel_spacing_mm = Application._normalise_imperfection_length_to_mm(
            Application._safe_obj_float(cyl_obj, (), ('panel_spacing',), 0.0)
        )

        long_stiffener = getattr(cyl_obj, 'LongStfObj', None)
        if long_stiffener is not None:
            panel_spacing_mm = Application._normalise_imperfection_length_to_mm(
                Application._safe_obj_float(long_stiffener, (), ('spacing', 's'), panel_spacing_mm)
            )

        if radius_mm > 0.0:
            rows.append(Application._imperfection_row(
                'Radius deviation at ring',
                'delta = 0.005 r',
                0.005 * radius_mm,
                'r = ' + Application._format_imperfection_value(radius_mm),
                sketch='radius_deviation',
            ))

        g_candidates = []
        if panel_spacing_mm > 0.0:
            g_candidates.append(panel_spacing_mm)
        if ring_spacing_mm > 0.0 and radius_mm > 0.0 and thickness_mm > 0.0:
            g_candidates.append(1.15 * math.sqrt(ring_spacing_mm * radius_mm * thickness_mm))
        if radius_mm > 0.0:
            g_candidates.append(math.pi * radius_mm / 2.0)
        if radius_mm > 0.0 and g_candidates:
            template_length_mm = min(g_candidates)
            rows.append(Application._imperfection_row(
                'Local out-of-roundness',
                'delta = 0.01 g / (1 + g/r)',
                0.01 * template_length_mm / (1.0 + template_length_mm / radius_mm),
                'g = ' + Application._format_imperfection_value(template_length_mm),
                sketch='local_roundness',
            ))

        if long_stiffener is not None and ring_spacing_mm > 0.0:
            rows.append(Application._imperfection_row(
                'Longitudinal stiffener straightness',
                'delta = 0.0015 l',
                0.0015 * ring_spacing_mm,
                'l = ' + Application._format_imperfection_value(ring_spacing_mm),
                sketch='member_straightness',
            ))
            flange_width_mm = Application._normalise_imperfection_length_to_mm(
                Application._safe_obj_float(long_stiffener, (), ('b', 'fl_w'), 0.0)
            )
            if flange_width_mm > 0.0:
                rows.append(Application._imperfection_row(
                    'Longitudinal flange straightness',
                    'delta = 0.0015 l',
                    0.0015 * ring_spacing_mm,
                    'l = ' + Application._format_imperfection_value(ring_spacing_mm),
                    sketch='flange_straightness',
                ))
            if panel_spacing_mm > 0.0:
                rows.append(Application._imperfection_row(
                    'Longitudinal stiffener misalignment',
                    'delta = 0.02 s',
                    0.02 * panel_spacing_mm,
                    's = ' + Application._format_imperfection_value(panel_spacing_mm),
                    sketch='cylinder_stiffener_misalignment',
                ))
        return rows

    @staticmethod
    def _positions_from_length_and_spacing(length, spacing, include_ends=True, max_count=80):
        """Create repeated member positions with symmetric end compensation."""
        return list(representation_geometry.centered_member_positions(
            length,
            spacing,
            fallback_midpoint=True,
            max_count=max_count,
            include_ends=include_ends,
        ))

    @staticmethod
    def _support_positions_from_length_and_span(length, span, max_count=80):
        """Create centered support/girder positions without changing the span.

        ``Panel length, Lp`` is the total repeated model length, while
        ``Stiffener/plate length`` is the bay between girder supports.  If Lp is
        not an exact multiple of the bay length, the full bays are centered so
        the cut length is shared symmetrically at both ends; when Lp is an
        exact multiple the girders bound the bays and sit on the panel edges.
        """
        return list(representation_geometry.centered_member_positions(
            length,
            span,
            fallback_midpoint=False,
            max_count=max_count,
            include_ends=True,
        ))

    @staticmethod
    def _bay_ranges_from_support_positions(length, supports, support_gap=0.0):
        """Return member segment ranges split by internal support/girder lines."""
        return list(representation_geometry.bay_ranges_from_support_positions(length, supports, support_gap))

    @staticmethod
    def _ring_member_half_width(dims):
        """Return the axial half-width occupied by a ring member preview."""
        try:
            web_t = max(float(dims.get('web_thk', 0.0)), 0.0)
            flange_w = max(float(dims.get('flange_w', 0.0)), 0.0)
        except Exception:
            return 0.0
        return max(web_t, flange_w) / 2.0

    @staticmethod
    def _ring_positions_without_heavy_frame_overlap(positions, frame_positions, ring_half_width,
                                                    frame_half_width, tolerance=1.0e-9):
        """Suppress ordinary ring stiffeners whose axial footprint overlaps heavy frames."""
        try:
            ring_half_width = max(float(ring_half_width), 0.0)
            frame_half_width = max(float(frame_half_width), 0.0)
            tolerance = max(float(tolerance), 0.0)
        except Exception:
            ring_half_width = frame_half_width = 0.0
            tolerance = 1.0e-9

        clean_frame_positions = [float(pos) for pos in frame_positions]
        filtered_positions = []
        for pos in (float(value) for value in positions):
            overlaps_frame = any(
                abs(pos - frame_pos) <= ring_half_width + frame_half_width + tolerance
                for frame_pos in clean_frame_positions
            )
            if not overlaps_frame:
                filtered_positions.append(pos)
        return filtered_positions

    def _flat_preview_lg_from_objects(self, girder, stiffener, spacing):
        """Return LG in metres, preferring the selected line object over GUI defaults."""
        for obj in (girder, stiffener):
            if obj is None:
                continue
            for attr_name in ('girder_lg', 'lg', 'LG'):
                try:
                    value = getattr(obj, attr_name)
                    lg = self._normalise_preview_length_to_m(value, 0.0)
                    if lg > 1e-9:
                        return lg
                except Exception:
                    pass
            for getter_name in ('get_girder_lg', 'get_lg', 'get_LG'):
                try:
                    value = getattr(obj, getter_name)()
                    lg = self._normalise_preview_length_to_m(value, 0.0)
                    if lg > 1e-9:
                        return lg
                except Exception:
                    pass
        try:
            lg = self._normalise_preview_length_to_m(self._new_girder_length_LG.get(), 0.0)
            if lg > 1e-9:
                return lg
        except Exception:
            pass
        return max(4.0 * spacing, 0.8)

    def _flat_preview_lp_from_gui(self, span, spacing):
        """Return Lp in metres.  Lp=0 means fallback to two stiffener spans."""
        try:
            lp = self._normalise_preview_length_to_m(self._new_panel_length_Lp.get(), 0.0)
            if lp > 1e-9:
                return lp
        except Exception:
            pass
        return max(2.0 * span, 2.0 * spacing, 0.8)

    def _draw_section_web_and_flange_3d(self, ax, orientation, x_center, y_center, length,
                                        plate_thk, dims, x_limits=None, y_limits=None,
                                        facecolor_web='silver', facecolor_flange='darkgrey', side_sign=1.0):
        """
        Draw a simplified T/L/flat-bar stiffener or girder.

        orientation='x': member runs in x direction; web thickness is in y.
        orientation='y': member runs in y direction; web thickness is in x.
        """
        web_h = max(dims.get('web_h', 0.0), 0.0)
        web_t = max(dims.get('web_thk', 0.0), 0.0)
        fl_w = max(dims.get('flange_w', 0.0), 0.0)
        fl_t = max(dims.get('flange_thk', 0.0), 0.0)
        sec_type = dims.get('type', 'T')
        if length <= 0.0 or (web_h <= 0.0 and fl_t <= 0.0):
            return
        self._update_prop_3d_export_mesh_size(ax, dims)
        if side_sign >= 0:
            web_z = (plate_thk, plate_thk + web_h)
            flange_z = (plate_thk + web_h, plate_thk + web_h + fl_t)
            shell_web_z = (0.0, web_h)
            shell_flange_z = web_h
        else:
            web_z = (-web_h, 0.0)
            flange_z = (-(web_h + fl_t), -web_h)
            shell_web_z = (0.0, -web_h)
            shell_flange_z = -web_h

        if orientation == 'x':
            x0, x1 = x_center - length / 2.0, x_center + length / 2.0
            if x_limits is not None:
                x0 = max(x0, x_limits[0])
                x1 = min(x1, x_limits[1])
            if x1 <= x0:
                return
            self._record_prop_3d_tk3d_item(
                ax, kind='flat_member', orientation='x', start=x0, end=x1, station=y_center,
                z_base=plate_thk if side_sign >= 0 else 0.0,
                hw=web_h if side_sign >= 0 else -web_h,
                flange_w=fl_w if (fl_w > 0.0 and fl_t > 0.0) else 0.0,
                web_thickness_m=web_t, flange_thickness_m=fl_t)
            self._add_box_3d(ax, x0, x1, y_center - web_t / 2.0, y_center + web_t / 2.0,
                             web_z[0], web_z[1], facecolor=facecolor_web, alpha=1.0)
            self._append_faces_to_prop_3d_export_mesh(ax, [[
                (x0, y_center, shell_web_z[0]), (x1, y_center, shell_web_z[0]),
                (x1, y_center, shell_web_z[1]), (x0, y_center, shell_web_z[1])
            ]], shell_model=True)
            if fl_w > 0.0 and fl_t > 0.0:
                if sec_type in ['L', 'L-bulb']:
                    y0 = y_center - web_t / 2.0
                    y1 = y0 + fl_w
                else:
                    y0 = y_center - fl_w / 2.0
                    y1 = y_center + fl_w / 2.0
                self._add_box_3d(ax, x0, x1, y0, y1,
                                 flange_z[0], flange_z[1], facecolor=facecolor_flange, alpha=1.0)
                self._append_faces_to_prop_3d_export_mesh(ax, [[
                    (x0, y0, shell_flange_z), (x1, y0, shell_flange_z),
                    (x1, y1, shell_flange_z), (x0, y1, shell_flange_z)
                ]], shell_model=True)
        else:
            y0, y1 = y_center - length / 2.0, y_center + length / 2.0
            if y_limits is not None:
                y0 = max(y0, y_limits[0])
                y1 = min(y1, y_limits[1])
            if y1 <= y0:
                return
            self._record_prop_3d_tk3d_item(
                ax, kind='flat_member', orientation='y', start=y0, end=y1, station=x_center,
                z_base=plate_thk if side_sign >= 0 else 0.0,
                hw=web_h if side_sign >= 0 else -web_h,
                flange_w=fl_w if (fl_w > 0.0 and fl_t > 0.0) else 0.0,
                web_thickness_m=web_t, flange_thickness_m=fl_t)
            self._add_box_3d(ax, x_center - web_t / 2.0, x_center + web_t / 2.0, y0, y1,
                             web_z[0], web_z[1], facecolor=facecolor_web, alpha=1.0)
            self._append_faces_to_prop_3d_export_mesh(ax, [[
                (x_center, y0, shell_web_z[0]), (x_center, y1, shell_web_z[0]),
                (x_center, y1, shell_web_z[1]), (x_center, y0, shell_web_z[1])
            ]], shell_model=True)
            if fl_w > 0.0 and fl_t > 0.0:
                if sec_type in ['L', 'L-bulb']:
                    x0 = x_center - web_t / 2.0
                    x1 = x0 + fl_w
                else:
                    x0 = x_center - fl_w / 2.0
                    x1 = x_center + fl_w / 2.0
                self._add_box_3d(ax, x0, x1, y0, y1,
                                 flange_z[0], flange_z[1], facecolor=facecolor_flange, alpha=1.0)
                self._append_faces_to_prop_3d_export_mesh(ax, [[
                    (x0, y0, shell_flange_z), (x1, y0, shell_flange_z),
                    (x1, y1, shell_flange_z), (x0, y1, shell_flange_z)
                ]], shell_model=True)

    def draw_prop_3d(self):
        """Route 3D property preview based on the active line type."""
        self.clear_prop_3d()
        self._prop_canvas.delete('all')

        if not self._line_is_active or self._active_line not in self._line_to_struc:
            return

        if not getattr(self, '_simplified_calculation_mode', False):
            self.set_selected_variables(self._active_line)

        try:
            if self._line_to_struc[self._active_line][5] is not None:
                self.draw_cylinder_prop_3d(self._line_to_struc[self._active_line][5])
            else:
                self.draw_flat_panel_prop_3d(self._line_to_struc[self._active_line][0])
        except Exception as error:
            self._prop_canvas.create_text(
                [20, 20],
                text='3D preview unavailable: ' + str(error),
                anchor='nw',
                font=self._text_size['Text 10 bold'],
                fill='red',
            )
            return

        if getattr(self, '_simplified_calculation_mode', False):
            self.draw_prepomax_imperfection_recommendations()

    def create_prop_3d_figure_for_line(self, line_name=None):
        """Return the same 3D property-preview figure used by the main canvas."""
        selected_line = line_name or self._active_line
        if selected_line not in self._line_to_struc:
            return None

        previous_line = self._active_line
        previous_line_is_active = self._line_is_active
        self._active_line = selected_line
        self._line_is_active = True
        try:
            if not getattr(self, '_simplified_calculation_mode', False):
                self.set_selected_variables(selected_line)
            if self._line_to_struc[selected_line][5] is not None:
                return self.draw_cylinder_prop_3d(self._line_to_struc[selected_line][5], embed=False)
            return self.draw_flat_panel_prop_3d(self._line_to_struc[selected_line][0], embed=False)
        finally:
            self._active_line = previous_line
            self._line_is_active = previous_line_is_active

    def draw_prepomax_imperfection_recommendations(self):
        """Draw DNVGL-OS-C401 imperfection guidance for PrePoMax in the lower pane."""
        canvas = self._prop_canvas
        canvas.delete('all')
        canvas_width = max(canvas.winfo_width(), 360)
        canvas_height = max(canvas.winfo_height(), 170)
        text_color = getattr(self, '_color_text', 'black')

        rows = []
        if self._line_is_active and self._active_line in self._line_to_struc:
            if self._line_to_struc[self._active_line][5] is not None:
                rows = self._cylinder_imperfection_recommendations(self._line_to_struc[self._active_line][5])
            else:
                rows = self._flat_panel_imperfection_recommendations(self._line_to_struc[self._active_line][0])

        canvas.create_rectangle(4, 4, canvas_width - 4, canvas_height - 4,
                                outline='#9aa5b1', fill='#f8fafc')
        canvas.create_text(
            12, 10,
            text='FE-model imperfection input, DNVGL-OS-C401',
            anchor='nw',
            font=self._text_size['Text 10 bold'],
            fill=text_color,
        )
        canvas.create_text(
            12, 31,
            text='Use the value as initial geometry amplitude for the matching imperfection shape.',
            anchor='nw',
            width=max(canvas_width - 160, 120),
            font=self._text_size['Text 8'],
            fill=text_color,
        )
        self._draw_prepomax_tolerance_table_button(canvas, canvas_width)

        if not rows:
            canvas.create_text(
                12, 62,
                text='No active single panel/cylinder geometry is available.',
                anchor='nw',
                width=canvas_width - 24,
                font=self._text_size['Text 9'],
                fill='red',
            )
            return

        selected = int(getattr(self, '_selected_prepomax_imperfection_row', 0))
        if selected < 0 or selected >= len(rows):
            selected = 0
            self._selected_prepomax_imperfection_row = selected

        top = 64
        left = 12
        table_right = max(300, canvas_width * 0.74)
        sketch_left = table_right + 8
        value_x = left + (table_right - left) * 0.52
        formula_x = left + (table_right - left) * 0.68
        row_height = max(22, min(32, int((canvas_height - top - 12) / max(len(rows) + 1, 1))))
        header_font = self._text_size['Text 8 bold']
        row_font = self._text_size['Text 8']

        canvas.create_text(left, top, text='Click row', anchor='nw', font=header_font, fill=text_color)
        canvas.create_text(value_x, top, text='Amplitude', anchor='nw', font=header_font, fill=text_color)
        canvas.create_text(formula_x, top, text='Formula / basis', anchor='nw', font=header_font, fill=text_color)
        y = top + row_height
        for index, row in enumerate(rows):
            if y + row_height > canvas_height - 8:
                remaining = len(rows) - index
                canvas.create_text(
                    left, y,
                    text='+ ' + str(remaining) + ' more tolerance items',
                    anchor='nw',
                    font=row_font,
                    fill=text_color,
                )
                break
            fill = '#dbeafe' if index == selected else ('#eef2f7' if index % 2 == 0 else '#ffffff')
            outline = '#2563eb' if index == selected else ''
            tag = 'prep_imperf_row_' + str(index)
            canvas.create_rectangle(8, y - 2, table_right - 4, y + row_height - 2,
                                    outline=outline, fill=fill, tags=(tag,))
            canvas.create_text(left, y, text=row['detail'], anchor='nw',
                               width=max(value_x - left - 8, 80), font=row_font, fill=text_color, tags=(tag,))
            canvas.create_text(value_x, y, text=self._format_imperfection_value(row['value_mm']),
                               anchor='nw', width=max(formula_x - value_x - 6, 60),
                               font=row_font, fill=text_color, tags=(tag,))
            canvas.create_text(formula_x, y, text=row['formula'] + ', ' + row['basis'], anchor='nw',
                               width=max(table_right - formula_x - 8, 70), font=row_font, fill=text_color,
                               tags=(tag,))
            canvas.tag_bind(tag, '<Button-1>',
                            lambda _event, row_index=index: self._select_prepomax_imperfection_row(row_index))
            canvas.tag_bind(tag, '<Enter>', lambda _event: canvas.configure(cursor='hand2'))
            canvas.tag_bind(tag, '<Leave>', lambda _event: canvas.configure(cursor=''))
            y += row_height

        self._draw_prepomax_imperfection_sketch(
            canvas, rows[selected],
            sketch_left, top - 4,
            canvas_width - 10, canvas_height - 10,
            text_color=text_color,
        )

    def _draw_prepomax_tolerance_table_button(self, canvas, canvas_width):
        """Draw a small Canvas button opening the source tolerance table image."""
        x1 = canvas_width - 12
        x0 = max(x1 - 128, 150)
        y0 = 30
        y1 = 52
        tag = 'prep_imperf_tolerance_table_button'
        canvas.create_rectangle(x0, y0, x1, y1, outline='#64748b', fill='#e2e8f0', tags=(tag,))
        canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2, text='Open DNV table',
                           font=self._text_size['Text 8 bold'], fill='#0f172a', tags=(tag,))
        canvas.tag_bind(tag, '<Button-1>', lambda _event: self.open_dnv_tolerance_table_image())
        canvas.tag_bind(tag, '<Enter>', lambda _event: canvas.configure(cursor='hand2'))
        canvas.tag_bind(tag, '<Leave>', lambda _event: canvas.configure(cursor=''))

    def _dnv_tolerance_table_image_path(self):
        return os.path.join(self._root_dir, 'images', 'tolerances.png')

    def open_dnv_tolerance_table_image(self):
        """Open the DNVGL-OS-C401 tolerance table image in a scrollable zoom viewer."""
        image_path = self._dnv_tolerance_table_image_path()
        if not os.path.isfile(image_path):
            messagebox.showwarning('DNV tolerance table', 'Could not find image:\n' + image_path)
            return

        window = tk.Toplevel(self._parent)
        window.title('DNVGL-OS-C401 tolerance table')
        window.configure(background='#f8fafc')

        try:
            from PIL import Image, ImageTk
            original_image = Image.open(image_path)
        except Exception:
            original_image = None

        screen_width = self._parent.winfo_screenwidth()
        screen_height = self._parent.winfo_screenheight()
        window.geometry(str(min(1200, max(760, screen_width - 120))) + 'x' +
                        str(min(900, max(560, screen_height - 160))))

        toolbar = ttk.Frame(window)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 2))
        zoom_state = {'scale': 1.0, 'photo': None, 'image_id': None}

        image_canvas = tk.Canvas(window, background='#e5e7eb', highlightthickness=0)
        x_scroll = ttk.Scrollbar(window, orient=tk.HORIZONTAL, command=image_canvas.xview)
        y_scroll = ttk.Scrollbar(window, orient=tk.VERTICAL, command=image_canvas.yview)
        image_canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        image_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(2, 8))

        def render_image():
            image_canvas.delete('all')
            if original_image is None:
                photo = tk.PhotoImage(file=image_path)
            else:
                width = max(1, int(original_image.width * zoom_state['scale']))
                height = max(1, int(original_image.height * zoom_state['scale']))
                resized = original_image.resize((width, height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(resized)
            zoom_state['photo'] = photo
            zoom_state['image_id'] = image_canvas.create_image(0, 0, image=photo, anchor='nw')
            image_canvas.configure(scrollregion=(0, 0, photo.width(), photo.height()))

        def zoom_to(scale):
            zoom_state['scale'] = min(max(float(scale), 0.25), 4.0)
            render_image()

        def zoom_by(factor):
            zoom_to(zoom_state['scale'] * factor)

        ttk.Button(toolbar, text='Zoom +', width=8, command=lambda: zoom_by(1.25)).pack(side=tk.LEFT)
        ttk.Button(toolbar, text='Zoom -', width=8, command=lambda: zoom_by(0.8)).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(toolbar, text='Original size', width=13, command=lambda: zoom_to(1.0)).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(toolbar, text='Scroll to inspect the full source tolerance table.').pack(side=tk.LEFT, padx=(10, 0))

        def mousewheel_scroll(event):
            if getattr(event, 'state', 0) & 0x0004:
                zoom_by(1.1 if event.delta > 0 else 0.9)
            else:
                image_canvas.yview_scroll(-1 * int(event.delta / 120), 'units')

        image_canvas.bind('<MouseWheel>', mousewheel_scroll)
        render_image()

    def _select_prepomax_imperfection_row(self, row_index):
        self._selected_prepomax_imperfection_row = int(row_index)
        self.draw_prepomax_imperfection_recommendations()

    def _draw_prepomax_imperfection_sketch(self, canvas, row, x0, y0, x1, y1, text_color='black'):
        """Draw one simplified DNV tolerance sketch for the selected recommendation row."""
        x0 = max(float(x0), 0.0)
        y0 = max(float(y0), 0.0)
        x1 = max(float(x1), x0 + 80.0)
        y1 = max(float(y1), y0 + 80.0)
        canvas.create_rectangle(x0, y0, x1, y1, outline='#cbd5e1', fill='#ffffff')
        canvas.create_text(
            x0 + 8, y0 + 6,
            text=row['detail'],
            anchor='nw',
            width=max(x1 - x0 - 16, 80),
            font=self._text_size['Text 8 bold'],
            fill=text_color,
        )
        canvas.create_text(
            x0 + 8, y1 - 20,
            text='Sketch only, use amplitude ' + self._format_imperfection_value(row['value_mm']),
            anchor='nw',
            width=max(x1 - x0 - 16, 80),
            font=self._text_size['Text 8'],
            fill=text_color,
        )

        sketch = row.get('sketch', 'member_straightness')
        draw_area = (x0 + 14, y0 + 34, x1 - 14, y1 - 28)
        if sketch == 'plate_out_of_plane':
            self._draw_plate_out_of_plane_sketch(canvas, draw_area)
        elif sketch == 'parallel_misalignment':
            self._draw_parallel_misalignment_sketch(canvas, draw_area, curved=False)
        elif sketch == 'cylinder_stiffener_misalignment':
            self._draw_parallel_misalignment_sketch(canvas, draw_area, curved=True)
        elif sketch == 'radius_deviation':
            self._draw_radius_deviation_sketch(canvas, draw_area)
        elif sketch == 'local_roundness':
            self._draw_local_roundness_sketch(canvas, draw_area)
        else:
            self._draw_member_straightness_sketch(canvas, draw_area, flange=sketch == 'flange_straightness')

    @staticmethod
    def _draw_delta_arrow(canvas, x0, y0, x1, y1, label='delta'):
        canvas.create_line(x0, y0, x1, y1, fill='#dc2626', width=2, arrow=tk.BOTH)
        canvas.create_text((x0 + x1) / 2 + 7, (y0 + y1) / 2, text=label, fill='#dc2626',
                           anchor='w', font='Verdana 8 bold')

    @staticmethod
    def _draw_dimension_line(canvas, x0, y0, x1, y1, label):
        canvas.create_line(x0, y0, x1, y1, fill='#334155', width=1, arrow=tk.BOTH)
        canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2 + 10, text=label, fill='#334155',
                           font='Verdana 8')

    def _draw_plate_out_of_plane_sketch(self, canvas, area):
        x0, y0, x1, y1 = area
        mid_y = y0 + 0.58 * (y1 - y0)
        left = x0 + 0.16 * (x1 - x0)
        right = x1 - 0.16 * (x1 - x0)
        canvas.create_line(left, y0 + 10, left, mid_y + 22, fill='#475569', width=4)
        canvas.create_line(right, y0 + 10, right, mid_y + 22, fill='#475569', width=4)
        canvas.create_line(left, mid_y, right, mid_y, fill='#111827', dash=(4, 3))
        canvas.create_line(left, mid_y, (left + right) / 2, mid_y - 20, right, mid_y,
                           fill='#dc2626', width=3, smooth=True)
        self._draw_delta_arrow(canvas, (left + right) / 2, mid_y, (left + right) / 2, mid_y - 20)
        self._draw_dimension_line(canvas, left, mid_y + 32, right, mid_y + 32, 's')

    def _draw_member_straightness_sketch(self, canvas, area, flange=False):
        x0, y0, x1, y1 = area
        left = x0 + 0.10 * (x1 - x0)
        right = x1 - 0.10 * (x1 - x0)
        mid_y = y0 + 0.52 * (y1 - y0)
        thickness = 6 if flange else 11
        canvas.create_line(left, mid_y, right, mid_y, fill='#111827', dash=(4, 3))
        canvas.create_line(left, mid_y - thickness, (left + right) / 2, mid_y - thickness - 18,
                           right, mid_y - thickness, fill='#475569', width=3, smooth=True)
        canvas.create_line(left, mid_y + thickness, (left + right) / 2, mid_y + thickness + 18,
                           right, mid_y + thickness, fill='#dc2626', width=3, smooth=True)
        self._draw_delta_arrow(canvas, (left + right) / 2, mid_y, (left + right) / 2, mid_y + thickness + 18)
        self._draw_dimension_line(canvas, left, y1 - 16, right, y1 - 16, 'l')

    def _draw_parallel_misalignment_sketch(self, canvas, area, curved=False):
        x0, y0, x1, y1 = area
        mid_y = y0 + 0.55 * (y1 - y0)
        xs = [x0 + (x1 - x0) * value for value in (0.18, 0.34, 0.50, 0.66, 0.82)]
        if curved:
            canvas.create_arc(x0 + 6, mid_y - 58, x1 - 6, mid_y + 46, start=20, extent=140,
                              style=tk.ARC, width=2, outline='#475569')
        else:
            canvas.create_line(x0 + 8, mid_y, x1 - 8, mid_y, fill='#475569', width=2)
        for idx, x in enumerate(xs):
            shift = -16 if idx == 2 else 0
            color = '#dc2626' if idx == 2 else '#475569'
            canvas.create_line(x + shift, mid_y - 30, x + shift, mid_y + 28, fill=color, width=4)
            canvas.create_line(x + shift - 12, mid_y - 30, x + shift + 12, mid_y - 30, fill=color, width=3)
        self._draw_delta_arrow(canvas, xs[2], mid_y - 8, xs[2] - 16, mid_y - 8)
        self._draw_dimension_line(canvas, xs[1], y1 - 16, xs[2], y1 - 16, 's')

    def _draw_radius_deviation_sketch(self, canvas, area):
        x0, y0, x1, y1 = area
        cx = (x0 + x1) / 2
        cy = y1 + 18
        r = min((x1 - x0) * 0.48, (y1 - y0) * 1.05)
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=32, extent=116,
                          style=tk.ARC, width=3, outline='#111827')
        canvas.create_arc(cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10, start=42, extent=96,
                          style=tk.ARC, width=3, outline='#dc2626')
        angle = math.radians(90)
        self._draw_delta_arrow(canvas, cx + math.cos(angle) * r, cy - r,
                               cx + math.cos(angle) * r, cy - r - 10)
        canvas.create_line(cx, cy, cx, cy - r, fill='#334155', width=1, dash=(3, 3))
        canvas.create_text(cx + 6, cy - r / 2, text='r', anchor='w', fill='#334155', font='Verdana 8')

    def _draw_local_roundness_sketch(self, canvas, area):
        x0, y0, x1, y1 = area
        base_y = y0 + 0.64 * (y1 - y0)
        left = x0 + 0.12 * (x1 - x0)
        right = x1 - 0.12 * (x1 - x0)
        mid = (left + right) / 2
        canvas.create_line(left, base_y, mid - 28, base_y - 6, mid, base_y - 24,
                           mid + 28, base_y - 6, right, base_y, fill='#dc2626', width=3, smooth=True)
        canvas.create_line(left, base_y + 8, right, base_y + 8, fill='#111827', dash=(4, 3))
        template_y = y0 + 0.22 * (y1 - y0)
        canvas.create_line(left + 18, template_y, right - 18, template_y, fill='#475569', width=5)
        self._draw_dimension_line(canvas, left + 18, template_y - 14, right - 18, template_y - 14, 'g')
        self._draw_delta_arrow(canvas, mid, base_y + 8, mid, base_y - 24)

    def draw_flat_panel_prop_3d(self, all_obj, embed=True):
        """Draw flat plate, stiffener and optional girder as extruded 3D preview solids."""
        plate = all_obj.Plate
        stiffener = all_obj.Stiffener
        girder = all_obj.Girder

        if plate is None:
            return None

        spacing = max(float(plate.get_s()), 1e-6)
        plate_thk = max(float(plate.get_pl_thk()), 1e-6)
        span = self._safe_obj_float(plate, ('get_span',), ('span',), 2.0)

        fig = plt.Figure(figsize=(7.2, 2.35), dpi=100)
        ax = fig.add_axes([0.035, 0.11, 0.94, 0.81], projection='3d')
        self._init_prop_3d_export_mesh(ax, 'flat_panel_preview')

        max_z = plate_thk
        min_z = 0.0
        member_side_sign = self._prop_3d_member_side_sign()

        if girder is not None:
            # x = total repeated panel length Lp, split into girder bays by the
            # stiffener/plate span l.  y = girder length LG / repeated stiffeners.
            width = self._flat_preview_lp_from_gui(span, spacing)
            length = self._flat_preview_lg_from_objects(girder, stiffener, spacing)
            girder_xs = self._support_positions_from_length_and_span(width, span, max_count=80)

            gdims = self._get_section_3d_dimensions(girder)
            sdims = self._get_section_3d_dimensions(stiffener) if stiffener is not None else None
            girder_gap = max(gdims.get('web_thk', 0.0), 0.0)

            self._add_box_3d(ax, 0.0, width, 0.0, length, 0.0, plate_thk,
                             facecolor='lightgrey', alpha=0.55)
            self._record_prop_3d_tk3d_item(
                ax, kind='flat_plate', x0=0.0, x1=width, y0=0.0, y1=length, thickness_m=plate_thk)

            # Girder supports at each stiffener span station across Lp.
            for x_pos in girder_xs:
                self._draw_section_web_and_flange_3d(
                    ax, 'y', x_pos, length / 2.0, length, plate_thk, gdims,
                    y_limits=(0.0, length), facecolor_web='silver', facecolor_flange='darkgrey',
                    side_sign=member_side_sign)
            member_z_extent = gdims['web_h'] + gdims['flange_thk']
            if member_side_sign >= 0:
                max_z = max(max_z, plate_thk + member_z_extent)
            else:
                min_z = min(min_z, -member_z_extent)

            # Stiffeners run bay-by-bay between adjacent girders, so increasing
            # Lp adds girder-supported bays instead of making one very long span.
            if sdims is not None:
                stiffener_ys = self._positions_from_length_and_spacing(
                    length, spacing, include_ends=True, max_count=80
                )
                shell_x_breaks = sorted(set([0.0, width] + girder_xs))
                solid_x_breaks = self._bay_ranges_from_support_positions(width, girder_xs, girder_gap)
                self._append_flat_plate_shell_grid_to_prop_3d_export_mesh(
                    ax, shell_x_breaks, [0.0, length] + stiffener_ys)
                for y in stiffener_ys:
                    for bay_x0, bay_x1 in solid_x_breaks:
                        if bay_x1 <= bay_x0:
                            continue
                        self._draw_section_web_and_flange_3d(
                            ax, 'x', (bay_x0 + bay_x1) / 2.0, y, bay_x1 - bay_x0,
                            plate_thk, sdims, x_limits=(bay_x0, bay_x1),
                            facecolor_web='silver', facecolor_flange='darkgrey', side_sign=member_side_sign)
                member_z_extent = sdims['web_h'] + sdims['flange_thk']
                if member_side_sign >= 0:
                    max_z = max(max_z, plate_thk + member_z_extent)
                else:
                    min_z = min(min_z, -member_z_extent)
            else:
                self._append_flat_plate_shell_grid_to_prop_3d_export_mesh(
                    ax, sorted(set([0.0, width] + girder_xs)), [0.0, length])

            title = '3D stiffened panel with girder'
            ax.set_xlabel('panel length, Lp [m]', fontsize=7, labelpad=-1)
            ax.set_ylabel('girder length, LG [m]', fontsize=7, labelpad=-1)
        else:
            # Flat plate/stiffened panel without explicit girder.
            # Use the same physical convention as the girder preview:
            #   x = stiffener span / panel length l
            #   y = girder length LG / repeated stiffener fields
            # The number of stiffeners is therefore governed by LG / stiffener spacing,
            # not by a hard-coded preview count.
            if stiffener is not None:
                width = max(span, spacing, 0.8)
                length = self._flat_preview_lg_from_objects(None, stiffener, spacing)
            else:
                width = max(spacing, 0.8)
                length = max(span, 0.8)

            self._add_box_3d(ax, 0.0, width, 0.0, length, 0.0, plate_thk,
                             facecolor='lightgrey', alpha=0.55)
            self._record_prop_3d_tk3d_item(
                ax, kind='flat_plate', x0=0.0, x1=width, y0=0.0, y1=length, thickness_m=plate_thk)

            if stiffener is not None:
                dims = self._get_section_3d_dimensions(stiffener)
                member_z_extent = dims['web_h'] + dims['flange_thk']
                if member_side_sign >= 0:
                    max_z = max(max_z, plate_thk + member_z_extent)
                else:
                    min_z = min(min_z, -member_z_extent)
                stiffener_ys = self._positions_from_length_and_spacing(
                    length, spacing, include_ends=True, max_count=80
                )
                self._append_flat_plate_shell_grid_to_prop_3d_export_mesh(
                    ax, [0.0, width], [0.0, length] + stiffener_ys)
                for y in stiffener_ys:
                    self._draw_section_web_and_flange_3d(
                        ax, 'x', width / 2.0, y, width, plate_thk, dims,
                        x_limits=(0.0, width), facecolor_web='silver', facecolor_flange='darkgrey',
                        side_sign=member_side_sign)
            else:
                self._append_flat_plate_shell_grid_to_prop_3d_export_mesh(
                    ax, [0.0, width], [0.0, length])

            title = '3D stiffened panel' if stiffener is not None else '3D plate preview'
            if stiffener is not None:
                ax.set_xlabel('stiffener span, l [m]', fontsize=7, labelpad=-1)
                ax.set_ylabel('girder length, LG [m]', fontsize=7, labelpad=-1)
            else:
                ax.set_xlabel('plate width [m]', fontsize=7, labelpad=-1)
                ax.set_ylabel('span direction [m]', fontsize=7, labelpad=-1)

        ax.text2D(0.02, 0.92, 'SELECTED: ' + str(self._active_line), transform=ax.transAxes,
                  fontsize=8, color='red')
        ax.set_title(title, fontsize=8)
        ax.set_zlabel('height [m]', fontsize=7, labelpad=-2)
        ax.tick_params(labelsize=6)
        # Give the 3D box enough data-limit padding to avoid clipping when the
        # axes itself is made wide.  Without this, a high set_box_aspect zoom
        # fills the available width but cuts the model at the left/right axes
        # boundaries.
        x_pad = max(0.14 * width, 0.08)
        y_pad = max(0.08 * length, 0.08)
        z_top = max(max_z * 1.28, plate_thk * 7.0, 0.08)
        z_bottom = min(-0.02 * z_top, min_z * 1.08)
        ax.set_xlim(-x_pad, width + x_pad)
        ax.set_ylim(-y_pad, length + y_pad)
        ax.set_zlim(z_bottom, z_top)
        self._apply_prop_3d_layout(fig, ax, width + 2.0 * x_pad, length + 2.0 * y_pad, z_top - z_bottom, zoom=1.52)
        ax.view_init(elev=22, azim=-55)

        if not embed:
            return fig, ax, (22, -55)
        self._embed_prop_3d(fig, ax, default_view=(22, -55))
        return fig, ax, (22, -55)

    def _add_cylinder_longitudinal_stiffener_3d(self, ax, radius, length, angle, dims, side_sign=1.0):
        """Draw a simplified longitudinal stiffener on a shell as radial web + outer flange."""
        web_h = max(dims.get('web_h', 0.0), 0.0)
        web_t = max(dims.get('web_thk', 0.0), 0.0)
        fl_w = max(dims.get('flange_w', 0.0), 0.0)
        fl_t = max(dims.get('flange_thk', 0.0), 0.0)
        if web_h <= 0.0:
            return
        self._update_prop_3d_export_mesh_size(ax, dims)
        self._record_prop_3d_tk3d_item(
            ax, kind='cylinder_long', radius=radius, length=length, angle=angle,
            web_h=web_h, web_thickness_m=web_t, flange_w=fl_w, flange_thickness_m=fl_t,
            side_sign=side_sign)

        z = np.linspace(0.0, length, 16)
        r = np.linspace(radius, radius + side_sign * web_h, 3)
        r_grid, z_grid = np.meshgrid(r, z)
        x_grid = r_grid * np.cos(angle)
        y_grid = r_grid * np.sin(angle)
        ax.plot_surface(x_grid, y_grid, z_grid, alpha=0.82, linewidth=0.2,
                        edgecolor='black', color='silver')
        self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, color='silver', alpha=0.82)
        self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, shell_model=True)

        if fl_w > 0.0 and fl_t > 0.0 and radius > 0.0:
            flange_radius = max(radius + side_sign * web_h, 1e-9)
            theta_half = fl_w / flange_radius / 2.0
            theta = np.linspace(angle - theta_half, angle + theta_half, 4)
            z_grid, theta_grid = np.meshgrid(z, theta)
            r_outer = radius + side_sign * (web_h + fl_t / 2.0)
            x_grid = r_outer * np.cos(theta_grid)
            y_grid = r_outer * np.sin(theta_grid)
            ax.plot_surface(x_grid, y_grid, z_grid,
                            alpha=0.82, linewidth=0.2, edgecolor='black', color='darkgrey')
            self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, color='darkgrey', alpha=0.82)
            x_grid = flange_radius * np.cos(theta_grid)
            y_grid = flange_radius * np.sin(theta_grid)
            self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, shell_model=True)

    @staticmethod
    def _is_cylinder_panel_preview(cyl_obj):
        try:
            domain = api_helpers.domain_for_geometry_id(cyl_obj.geometry)
        except Exception:
            return False
        return 'panel' in domain.lower() and 'shell' not in domain.lower()

    def _cylinder_preview_theta_range(self, cyl_obj):
        if self._is_cylinder_panel_preview(cyl_obj):
            half_span = math.radians(60.0) / 2.0
            return -half_span, half_span
        return 0.0, 2.0 * math.pi

    def _add_cylinder_ring_stiffener_3d(self, ax, radius, z_pos, dims, is_frame=False, theta_range=None,
                                        side_sign=1.0):
        """Draw a simplified ring stiffener/frame as annular web + outer flange."""
        web_h = max(dims.get('web_h', 0.0), 0.0)
        web_t = max(dims.get('web_thk', 0.0), 0.0)
        fl_w = max(dims.get('flange_w', 0.0), 0.0)
        fl_t = max(dims.get('flange_thk', 0.0), 0.0)
        if web_h <= 0.0:
            return
        self._update_prop_3d_export_mesh_size(ax, dims)
        theta_start, theta_end = theta_range if theta_range is not None else (0.0, 2.0 * math.pi)
        self._record_prop_3d_tk3d_item(
            ax, kind='cylinder_ring', radius=radius, z=float(z_pos),
            web_h=web_h, web_thickness_m=web_t, flange_w=fl_w, flange_thickness_m=fl_t,
            is_frame=bool(is_frame), theta_start=theta_start, theta_end=theta_end,
            is_panel=bool(abs((theta_end - theta_start) - 2.0 * math.pi) > 1.0e-6),
            side_sign=side_sign)
        theta = np.linspace(theta_start, theta_end, 64)
        rr = np.linspace(radius, radius + side_sign * web_h, 3)
        theta_grid, rr_grid = np.meshgrid(theta, rr)
        z_grid = np.full_like(theta_grid, z_pos)
        ax.plot_surface(rr_grid * np.cos(theta_grid), rr_grid * np.sin(theta_grid), z_grid,
                        alpha=0.86, linewidth=0.15, edgecolor='black',
                        color='dimgray' if is_frame else 'silver')
        self._append_grid_surface_to_prop_3d_export_mesh(
            ax, rr_grid * np.cos(theta_grid), rr_grid * np.sin(theta_grid), z_grid,
            color='dimgray' if is_frame else 'silver', alpha=0.86)
        self._append_grid_surface_to_prop_3d_export_mesh(
            ax, rr_grid * np.cos(theta_grid), rr_grid * np.sin(theta_grid), z_grid, shell_model=True)

        if web_t > 0.0:
            # Two axial edges make the ring thickness visible.
            for z_edge in [z_pos - web_t / 2.0, z_pos + web_t / 2.0]:
                outer_radius = radius + side_sign * web_h
                ax.plot(outer_radius * np.cos(theta), outer_radius * np.sin(theta),
                        np.full_like(theta, z_edge), color='black', linewidth=0.8 if is_frame else 0.5)

        if fl_w > 0.0 and fl_t > 0.0:
            z_band = np.linspace(z_pos - fl_w / 2.0, z_pos + fl_w / 2.0, 3)
            theta_grid, z_grid = np.meshgrid(theta, z_band)
            r_outer = radius + side_sign * (web_h + fl_t / 2.0)
            x_grid = r_outer * np.cos(theta_grid)
            y_grid = r_outer * np.sin(theta_grid)
            ax.plot_surface(x_grid, y_grid, z_grid,
                            alpha=0.82, linewidth=0.15, edgecolor='black',
                            color='black' if is_frame else 'darkgrey')
            self._append_grid_surface_to_prop_3d_export_mesh(
                ax, x_grid, y_grid, z_grid,
                color='black' if is_frame else 'darkgrey', alpha=0.82)
            shell_radius = radius + side_sign * web_h
            self._append_grid_surface_to_prop_3d_export_mesh(
                ax, shell_radius * np.cos(theta_grid), shell_radius * np.sin(theta_grid), z_grid,
                shell_model=True)

    def draw_cylinder_prop_3d(self, cyl_obj, embed=True):
        """Draw shell/curved plate with optional longitudinal stiffeners, ring stiffeners and ring frames."""
        shell = cyl_obj.ShellObj
        is_conical_preview = cyl_obj.geometry == 9
        cone_r1 = shell.cone_r1 if shell.cone_r1 is not None else shell.radius
        cone_r2 = shell.cone_r2 if shell.cone_r2 is not None else shell.radius
        cone_length = shell.cone_length if shell.cone_length is not None else shell.length_of_shell
        radius = float(shell.radius if not is_conical_preview else max(cone_r1, cone_r2))
        shell_length = float(shell.length_of_shell if not is_conical_preview else cone_length)
        thk = float(shell.thk)
        length = max(shell_length, 0.1)
        theta_range = self._cylinder_preview_theta_range(cyl_obj)
        theta_start, theta_end = theta_range
        is_panel_preview = self._is_cylinder_panel_preview(cyl_obj)
        member_side_sign = self._prop_3d_member_side_sign()
        theta = np.linspace(theta_start, theta_end, 30 if is_panel_preview else 64)
        z = np.linspace(0.0, length, 22)
        theta_grid, z_grid = np.meshgrid(theta, z)
        if is_conical_preview:
            r1 = float(cone_r1)
            r2 = float(cone_r2)
            radius_grid = r1 + (r2 - r1) * (z_grid / length)
        else:
            radius_grid = radius
        x_grid = radius_grid * np.cos(theta_grid)
        y_grid = radius_grid * np.sin(theta_grid)

        fig = plt.Figure(figsize=(7.2, 2.35), dpi=100)
        ax = fig.add_axes([0.035, 0.11, 0.94, 0.81], projection='3d')
        self._init_prop_3d_export_mesh(ax, 'cylinder_preview')
        ax.plot_surface(x_grid, y_grid, z_grid, alpha=0.30, linewidth=0.12,
                        edgecolor='grey', color='lightgrey')
        self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, color='lightgrey', alpha=0.30)
        self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, shell_model=True)
        self._record_prop_3d_tk3d_item(
            ax, kind='cylinder_shell',
            radius=float(cone_r1) if is_conical_preview else radius,
            radius_top=float(cone_r2) if is_conical_preview else None,
            length=length, thickness_m=thk,
            theta_start=theta_start, theta_end=theta_end,
            is_panel=is_panel_preview)

        if thk > 0 and radius > thk:
            for zz, end_radius in [(0.0, float(cone_r1) if is_conical_preview else radius),
                                   (length, float(cone_r2) if is_conical_preview else radius)]:
                ax.plot(end_radius * np.cos(theta), end_radius * np.sin(theta), np.full_like(theta, zz),
                        color='black', linewidth=0.8)
                ax.plot((end_radius - thk) * np.cos(theta), (end_radius - thk) * np.sin(theta),
                        np.full_like(theta, zz), color='black', linewidth=0.5, linestyle='dotted')

        radial_extension = max(thk, 0.01)
        if is_panel_preview:
            for angle in (theta_start, theta_end):
                ax.plot([radius * math.cos(angle), radius * math.cos(angle)],
                        [radius * math.sin(angle), radius * math.sin(angle)],
                        [0.0, length], color='black', linewidth=0.8)

        if cyl_obj.LongStfObj is not None:
            long_obj = cyl_obj.LongStfObj
            long_dims = self._get_section_3d_dimensions(long_obj)
            spacing = max(long_dims.get('spacing', 0.0), 1e-6)
            radial_extension = max(radial_extension, long_dims['web_h'] + long_dims['flange_thk'])
            if is_panel_preview:
                arc_length = abs(theta_end - theta_start) * radius
                direction = 1.0 if theta_end >= theta_start else -1.0
                stiffener_angles = [
                    theta_start + direction * arc_pos / max(radius, 1e-9)
                    for arc_pos in representation_geometry.centered_member_positions(
                        arc_length,
                        spacing,
                        fallback_midpoint=True,
                        max_count=24,
                        include_ends=True,
                    )
                ]
            else:
                num_stf = max(4, min(72, representation_geometry.closed_loop_member_count(
                    2.0 * math.pi * radius,
                    spacing,
                )))
                stiffener_angles = [2.0 * math.pi * idx / num_stf for idx in range(num_stf)]
            for ang in stiffener_angles:
                self._add_cylinder_longitudinal_stiffener_3d(
                    ax, radius, length, ang, long_dims, side_sign=member_side_sign)

        frame_dims = None
        girder_positions = []
        if cyl_obj.RingFrameObj is not None:
            frame_dims = self._get_section_3d_dimensions(cyl_obj.RingFrameObj)
            radial_extension = max(radial_extension, frame_dims['web_h'] + frame_dims['flange_thk'])
            try:
                girder_spacing = self._normalise_preview_length_to_m(cyl_obj.length_between_girders, 0.0)
            except Exception:
                girder_spacing = self._normalise_preview_length_to_m(
                    self._safe_obj_float(cyl_obj, (), ('length_between_girders',), 0.0), 0.0
                )
            if girder_spacing <= 1e-9:
                try:
                    girder_spacing = self._normalise_preview_length_to_m(
                        self._new_shell_ring_frame_length_between_girders.get(), 0.0
                    )
                except Exception:
                    girder_spacing = 0.0
            if girder_spacing <= 1e-9:
                girder_positions = [length / 2.0]
            else:
                # Ring frames bound the girder bays: measured symmetrically
                # about mid-height, on the shell edges when L is a multiple.
                girder_positions = self._positions_from_length_and_spacing(
                    length, girder_spacing, include_ends=True, max_count=16
                )

        if cyl_obj.RingStfObj is not None:
            ring_dims = self._get_section_3d_dimensions(cyl_obj.RingStfObj)
            radial_extension = max(radial_extension, ring_dims['web_h'] + ring_dims['flange_thk'])
            try:
                ring_spacing = self._normalise_preview_length_to_m(shell._dist_between_rings, 0.0)
            except Exception:
                ring_spacing = self._normalise_preview_length_to_m(
                    self._safe_obj_float(shell, (), ('dist_between_rings',), 0.0), 0.0
                )
            if ring_spacing <= 1e-9:
                try:
                    ring_spacing = self._normalise_preview_length_to_m(self._new_shell_dist_rings.get(), 0.0)
                except Exception:
                    ring_spacing = 0.0
            ring_positions = self._positions_from_length_and_spacing(
                length, ring_spacing, include_ends=True, max_count=30
            )
            ring_positions = self._ring_positions_without_heavy_frame_overlap(
                ring_positions, girder_positions,
                self._ring_member_half_width(ring_dims),
                self._ring_member_half_width(frame_dims or {}),
            )
            for zz in ring_positions:
                self._add_cylinder_ring_stiffener_3d(
                    ax, radius, zz, ring_dims, is_frame=False, theta_range=theta_range,
                    side_sign=member_side_sign)

        if frame_dims is not None:
            for zz in girder_positions:
                self._add_cylinder_ring_stiffener_3d(
                    ax, radius, zz, frame_dims, is_frame=True, theta_range=theta_range,
                    side_sign=member_side_sign)

        ax.text2D(0.02, 0.92, 'SELECTED: ' + str(self._active_line), transform=ax.transAxes,
                  fontsize=8, color='red')
        title = '3D conical shell preview' if is_conical_preview else \
            '3D cylinder panel preview (60 deg)' if is_panel_preview else '3D cylinder / curved plate preview'
        ax.set_title(title, fontsize=8)
        ax.set_xlabel('x [m]', fontsize=7, labelpad=-1)
        ax.set_ylabel('y [m]', fontsize=7, labelpad=-1)
        ax.set_zlabel('length [m]', fontsize=7, labelpad=-2)
        ax.tick_params(labelsize=6)
        lim = radius + radial_extension * 1.25 + max(thk, 0.01)
        if is_panel_preview:
            x_values = lim * np.cos(theta)
            y_values = lim * np.sin(theta)
            pad = max(0.10 * lim, 0.05)
            ax.set_xlim(float(np.min(x_values) - pad), float(np.max(x_values) + pad))
            ax.set_ylim(float(np.min(y_values) - pad), float(np.max(y_values) + pad))
            layout_width = max(float(np.max(x_values) - np.min(x_values) + 2.0 * pad), 1e-6)
            layout_depth = max(float(np.max(y_values) - np.min(y_values) + 2.0 * pad), 1e-6)
        else:
            ax.set_xlim(-lim, lim)
            ax.set_ylim(-lim, lim)
            layout_width = 2.0 * lim
            layout_depth = 2.0 * lim
        ax.set_zlim(0.0, length)
        self._apply_prop_3d_layout(fig, ax, layout_width, layout_depth, max(length, 1e-6), zoom=1.32)
        ax.view_init(elev=20, azim=-45)

        if not embed:
            return fig, ax, (22, -55)
        self._embed_prop_3d(fig, ax, default_view=(22, -55))
        return fig, ax, (22, -55)

    def draw_prop(self, event=None):
        '''
        Prints the properties of the selected line to the bottom canvas.

        properties for line dicitonary:

        name of line : [ Structure class, calc scantling class, calc fatigue class, [load classes] ]

        '''

        if getattr(self, '_fea_buckling_mode', False):
            self._draw_fea_panel_2d_sketch()
            return

        if getattr(self, '_new_show_prop_3d', None) is not None and self._new_show_prop_3d.get():
            self.draw_prop_3d()
            return

        self.clear_prop_3d()
        self._prop_canvas.delete('all')
        canvas_width = self._prop_canvas.winfo_width()
        canvas_height = self._prop_canvas.winfo_height()

        def checkered(line_distance, canvas):
            '''
            Grid lines in the properties canvas.
            :param line_distance:
            :return:
            '''
            # vertical lines at an interval of "line_distance" pixel
            for x in range(line_distance, canvas_width, line_distance):
                canvas.create_line(x, 0, x, canvas_width, stipple='gray50', activestipple='gray75')
            # horizontal lines at an interval of "line_distance" pixel
            for y in range(line_distance, canvas_height, line_distance):
                canvas.create_line(0, y, canvas_width, y, stipple='gray50', activestipple='gray75')

        if self._active_line in self._line_to_struc:
            self.set_selected_variables(self._active_line)
            # printing the properties to the active line
            if self._line_is_active and self._line_to_struc[self._active_line][5] is None:
                # checkered(10, self._prop_canvas)
                self._prop_canvas.create_text([canvas_width / 2 - canvas_width / 20, canvas_height / 20],
                                              text='SELECTED: ' + str(self._active_line),
                                              font=self._text_size["Text 10 bold"], fill='red')
                if all([self._line_to_struc[self._active_line][0].Stiffener is None,
                        self._line_to_struc[self._active_line][0].Girder is None]):
                    structure_obj = self._line_to_struc[self._active_line][0].Plate
                    spacing = structure_obj.get_s() * self._prop_canvas_scale * 3
                    plate_thk = structure_obj.get_pl_thk() * self._prop_canvas_scale * 3
                    startx = 20
                    starty = 225
                    self._prop_canvas.create_text([startx + 100, 50],
                                                  text='Plate with thickness ' +
                                                       str(structure_obj.get_pl_thk() * 1000) + ' mm',
                                                  font=self._text_size["Text 10 bold"], fill='Black')
                    self._prop_canvas.create_rectangle(startx + spacing,
                                                       starty,
                                                       startx + spacing + spacing,
                                                       starty - plate_thk,
                                                       fill='grey', activefill='yellow')

                for idx, structure_obj in enumerate([self._line_to_struc[self._active_line][0].Stiffener,
                                                     self._line_to_struc[self._active_line][0].Girder]):
                    mult = 1 if self._line_to_struc[self._active_line][0].Girder is not None else 2  # *(400/max_web)
                    thk_mult = 2  # *(400/max_web)
                    startx = 100 + 300 * idx
                    starty = 225

                    if structure_obj is not None:
                        self._prop_canvas.create_text([startx + 60, 50],
                                                      text='Stiffener\n' + structure_obj.get_beam_string()
                                                      if idx == 0 else 'Girder\n' + structure_obj.get_beam_string(),
                                                      font=self._text_size["Text 9 bold"], fill='Black')
                        if structure_obj is not None:
                            self._prop_canvas.create_text([100, 20],
                                                          text='Thickness scale x 2',
                                                          font=self._text_size["Text 10 bold"], fill='grey')
                        # drawing stiffener
                        spacing = structure_obj.get_s() * self._prop_canvas_scale * mult
                        stf_web_height = structure_obj.get_web_h() * self._prop_canvas_scale * mult
                        stf_flange_width = structure_obj.get_fl_w() * self._prop_canvas_scale * mult
                        plate_thk = structure_obj.get_pl_thk() * self._prop_canvas_scale * thk_mult * mult
                        stf_web_thk = structure_obj.get_web_thk() * self._prop_canvas_scale * thk_mult * mult
                        stf_flange_thk = structure_obj.get_fl_thk() * self._prop_canvas_scale * thk_mult * mult

                        for count in [0, 1, 2] if idx == 0 else [0, ]:

                            self._prop_canvas.create_rectangle(startx + count * spacing,
                                                               starty,
                                                               startx + spacing + count * spacing,
                                                               starty - plate_thk,
                                                               fill='grey', activefill='yellow')
                            self._prop_canvas.create_rectangle(
                                startx + spacing * 0.5 + count * spacing - stf_web_thk / 2,
                                starty - plate_thk,
                                startx + spacing * 0.5 + count * spacing + stf_web_thk / 2,
                                starty - stf_web_height - plate_thk,
                                fill='grey', activefill='yellow')

                            if structure_obj.get_stiffener_type() not in ['L', 'L-bulb']:

                                self._prop_canvas.create_rectangle(
                                    startx + spacing * 0.5 - stf_flange_width / 2 + count * spacing,
                                    starty - stf_web_height - plate_thk,
                                    startx + spacing * 0.5 + stf_flange_width / 2 + count * spacing,
                                    starty - stf_web_height - plate_thk - stf_flange_thk,
                                    fill='grey', activefill='yellow')
                            else:
                                self._prop_canvas.create_rectangle(
                                    startx + spacing * 0.5 - stf_web_thk / 2 + count * spacing,
                                    starty - stf_web_height - plate_thk,
                                    startx + spacing * 0.5 + stf_flange_width + count * spacing,
                                    starty - stf_web_height - plate_thk - stf_flange_thk,
                                    fill='grey',
                                    activefill='yellow')


            elif self._line_is_active and self._line_to_struc[self._active_line][5] is not None:
                self.draw_cylinder(canvas=self._prop_canvas, CylObj=self._line_to_struc[self._active_line][5],
                                   height=200, radius=150, start_x_cyl=500, start_y_cyl=20,
                                   text_color=self._color_text)

        else:
            pass

    @staticmethod
    def draw_cylinder(text_size=None, canvas=None, CylObj: CylinderAndCurvedPlate = None,
                      height=150, radius=150,
                      start_x_cyl=500, start_y_cyl=20, acceptance_color=False, text_x=200, text_y=130,
                      text_color='black'):

        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        if text_size == None:
            text_size = 'Verdana 8'

        canvas.create_text([text_x, text_y], text=CylObj, font=text_size, fill=text_color)
        # setting the input field to active line properties
        # self.set_selected_variables(self._active_line)

        if CylObj.geometry == 9:
            shell = CylObj.ShellObj
            r1 = max(float(shell.cone_r1 or 0), 0.01)
            r2 = max(float(shell.cone_r2 or 0), 0.01)
            rmax = max(r1, r2)
            top_width = radius * r1 / rmax
            bottom_width = radius * r2 / rmax
            offset_oval = 30
            top_x = start_x_cyl + (radius - top_width) / 2
            bottom_x = start_x_cyl + (radius - bottom_width) / 2
            top = (top_x, start_y_cyl, top_x + top_width, start_y_cyl + offset_oval)
            bottom = (bottom_x, start_y_cyl + height,
                      bottom_x + bottom_width, start_y_cyl + height + offset_oval)
            canvas.create_oval(top, width=4, fill='grey90')
            canvas.create_arc(bottom, extent=180, start=180, style=tk.ARC, width=3)
            canvas.create_line(top[0], top[1] + offset_oval / 2,
                               bottom[0], bottom[1] + offset_oval / 2, width=3)
            canvas.create_line(top[2], top[1] + offset_oval / 2,
                               bottom[2], bottom[1] + offset_oval / 2, width=3)
            canvas.create_text([start_x_cyl + radius / 2, start_y_cyl + height + offset_oval + 18],
                               text='Unstiffened conical shell', font=text_size, fill=text_color)
            return

        offset_oval = 30

        coord1 = start_x_cyl, start_y_cyl, start_x_cyl + radius, start_y_cyl + offset_oval
        coord2 = start_x_cyl, start_y_cyl + height, start_x_cyl + radius, start_y_cyl + offset_oval + height

        arc_1 = canvas.create_oval(coord1, width=5, fill='grey90')
        arc_2 = canvas.create_arc(coord2, extent=180, start=180, style=tk.ARC, width=3)

        line1 = canvas.create_line(coord1[0], coord1[1] + offset_oval / 2,
                                   coord1[0], coord1[1] + height + offset_oval / 2,
                                   width=3)
        line2 = canvas.create_line(coord1[0] + radius, coord1[1] + offset_oval / 2,
                                   coord1[0] + radius, coord1[1] + height + offset_oval / 2,
                                   width=3)
        if CylObj.LongStfObj is not None:
            long_obj = CylObj.LongStfObj

            num_stf = int(1000 * 2 * math.pi * CylObj.ShellObj.radius / long_obj.spacing / 2)
            for line_num in range(1, num_stf, 1):
                angle = 180 - 180 / (num_stf) * line_num
                arc_x, arc_y = 1 * math.cos(math.radians(angle)), 0.5 * math.sin(math.radians(angle))
                arc_x = (arc_x + 1) / 2

                line1 = canvas.create_line(coord1[0] + radius * arc_x,
                                           coord1[1] + 1 * arc_y * offset_oval + offset_oval / 2,
                                           coord1[0] + radius * arc_x,
                                           coord1[1] + height + 1 * arc_y * offset_oval + offset_oval / 2,
                                           fill='blue')
        if CylObj.RingStfObj is not None:
            num_ring_stiff = CylObj.ShellObj.length_of_shell / \
                             CylObj.ShellObj._dist_between_rings
            num_ring_stiff = int(num_ring_stiff)

            for ring_stf in range(1, num_ring_stiff + 1, 1):
                coord3 = coord1[0], coord1[1] + (height / (num_ring_stiff + 1)) * ring_stf, \
                                    start_x_cyl + radius, coord1[3] + (height / (num_ring_stiff + 1)) * ring_stf,
                arc_2 = canvas.create_arc(coord3, extent=180, start=180, style=tk.ARC, width=2,
                                          fill='orange',
                                          outline='orange')
        if CylObj.RingFrameObj is not None:
            num_ring_girder = CylObj.ShellObj.length_of_shell / \
                              CylObj.length_between_girders
            num_ring_girder = int(num_ring_girder)
            for ring_girder in range(1, num_ring_girder + 1, 1):
                coord3 = coord1[0], coord1[1] + (height / (num_ring_girder + 1)) * ring_girder, \
                                    start_x_cyl + radius, coord1[3] + (height / (num_ring_girder + 1)) * ring_girder,
                arc_2 = canvas.create_arc(coord3, extent=180, start=180, style=tk.ARC, width=4,
                                          fill='grey', outline='grey')

    def _get_ml_classes(self):
        return getattr(self, '_ML_classes', ml_models.default_ml_class_messages())

    def _build_report_data_snapshot(self):
        return project_services.ReportDataSnapshot(
            project_information=self._project_information.get('1.0', tk.END),
            buckling_method=self._new_buckling_method.get(),
            points=self._point_dict,
            lines=self._line_dict,
            line_bundles=self._line_to_struc,
            tanks=self._tank_dict,
            loads=self._load_dict,
            result_state=self.get_color_and_calc_state(),
            highest_pressures={
                line_name: self.get_highest_pressure(line_name)
                for line_name in self._line_to_struc
            },
            ml_classes=self._get_ml_classes(),
        )

    def report_generate(self, autosave=False):
        '''
        Button is pressed to generate a report of the current structure.
        :return:
        '''

        if not autosave:
            target = project_application.ProjectFileDialogService.selected_output_target(
                filedialog.asksaveasfilename(defaultextension=".pdf")
            )
            if target is None:
                return
            filename = target.path
        else:
            filename = '../testrun.pdf'

        if self._line_dict == {}:
            tk.messagebox.showerror('No lines', 'No lines defined. Cannot make report.')
            return

        if os.path.isfile('../current_comps.png'):
            os.remove('../current_comps.png')
            self.grid_display_tanks(save=True)
        else:
            self.grid_display_tanks(save=True)

        project_services.ReportRequestService.create_pdf(
            project_services.ReportRequest(str(filename), "Section results", 10, self._build_report_data_snapshot()),
        )
        try:
            os.startfile(filename)
        except FileNotFoundError:
            pass
        self._new_colorcode_beams.set(False)
        self._new_colorcode_plates.set(False)
        self._new_colorcode_pressure.set(False)
        self.update_frame()

    def table_generate(self, autosave=False):

        if not autosave:
            target = project_application.ProjectFileDialogService.selected_output_target(
                filedialog.asksaveasfilename(defaultextension=".pdf")
            )
            if target is None:
                return
            filename = target.path
        else:
            filename = '../testrun.pdf'

        if self._line_dict == {}:
            tk.messagebox.showerror('No lines', 'No lines defined. Cannot make report.')
            return

        project_services.ReportRequestService.create_table(
            project_services.ReportRequest(str(filename), "Section results", 10, self._build_report_data_snapshot()),
        )
        try:
            os.startfile(filename)
        except FileNotFoundError:
            pass
        self._new_colorcode_beams.set(False)
        self._new_colorcode_plates.set(False)
        self._new_colorcode_pressure.set(False)
        self.update_frame()

    def create_accelerations(self):
        '''
        Set the selected accelerations.
        :return:
        '''
        try:
            self._accelerations_dict['static'] = self._new_static_acc.get()
            self._accelerations_dict['dyn_loaded'] = self._new_dyn_acc_loaded.get()
            self._accelerations_dict['dyn_ballast'] = self._new_dyn_acc_ballast.get()

            if len(self._tank_dict) != 0:
                for tank, data in self._tank_dict.items():
                    data.set_acceleration(self._accelerations_dict)

            project_services.mark_lines_for_recalculation(self._line_to_struc)
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def new_point(self, copy=False, move=False, redo=None):
        '''
        Adds a point number and coordinates to the point dictionary. Type is 'p1' = [x0,y0]
        '''
        try:
            if copy:
                x_coord = self._new_point_x.get() / 1000 + self._point_dict[self._active_point][0]
                y_coord = self._new_point_y.get() / 1000 + self._point_dict[self._active_point][1]
            elif move:
                x_coord = self._new_point_x.get() / 1000 + self._point_dict[self._active_point][0] \
                    if redo is None else redo[0]
                y_coord = self._new_point_y.get() / 1000 + self._point_dict[self._active_point][1] \
                    if redo is None else redo[1]
            else:
                x_coord = (self._new_point_x.get() / 1000)
                y_coord = (self._new_point_y.get() / 1000)

            project_editor = project_services.ProjectEditService(self._point_dict, self._line_dict)
            # Finding name of the new point
            if move:
                current_point, current_coords = self._active_point, self._point_dict[self._active_point]
            else:
                current_point = project_editor.next_point_name()
            self._new_line_p1.set(get_num(current_point))
            # Creating the point
            # No point is created if another point is already there

            point_record = project_editor.move_point(current_point, (x_coord, y_coord)) if move else \
                project_editor.add_point(current_point, (x_coord, y_coord))
            if point_record is not None:
                self._active_point = current_point
                if move:
                    self.logger(point=current_point, move_coords=(current_coords, [x_coord, y_coord]))
                else:
                    self.logger(point=current_point, move_coords=None)
            self.update_frame()

        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def move_line(self, event=None):
        if self._line_is_active:
            line = self._line_dict[self._active_line]
            for pt_num in self._line_dict[self._active_line]:
                self._active_point = 'point' + str(pt_num)
                self._point_is_active = True
                self.move_point()
        else:
            messagebox.showinfo(title='Input error', message='A line must be selected (left click).')

    def move_point(self, event=None, redo=None):
        '''
        Moving a point.
        :return:
        '''
        if self._point_is_active:
            self.new_point(move=True, redo=redo)  # doing the actual moving
            project_editor = project_services.ProjectEditService(self._point_dict, self._line_dict)
            for line in project_editor.connected_line_names(self._active_point):
                data = self._line_dict[line]
                # updating the span and deleting compartments (if not WT)
                coord1 = self._point_dict['point' + str(data[0])]
                coord2 = self._point_dict['point' + str(data[1])]
                if line in self._line_to_struc.keys():
                    self._line_to_struc[line][0].Plate.set_span(dist(coord1, coord2))
                    self._line_to_struc[line][0].Plate.set_span(dist(coord1, coord2))
                    if self._line_to_struc[line][0].Plate.get_structure_type() not in ['GENERAL_INTERNAL_NONWT',
                                                                                       'FRAME']:
                        self._tank_dict = {}
                        self._main_grid.clear()
                        self._compartments_listbox.delete(0, 'end')

            project_services.mark_lines_for_recalculation(self._line_to_struc)
            self.update_frame()
        else:
            messagebox.showinfo(title='Input error', message='A point must be selected (right click).')

    def copy_point(self, event=None):
        '''
        Using the same input as new point, but with separate button.
        :return:
        '''
        if self._point_is_active:
            self.new_point(copy=True)
        else:
            messagebox.showinfo(title='Input error', message='A point must be selected (right click).')

    def new_line(self, event=None, redo=None):
        '''
        Adds line to line dictionary. Type is 'line1' = [p1,p2]
        '''

        current_name = None
        try:
            # if's ensure that the new line does not exist already and that the point input is not an invalid point.
            if redo is None:
                first_point, second_point = 'point' + str(self._new_line_p1.get()), \
                                            'point' + str(self._new_line_p2.get())
            else:
                first_point, second_point = redo
            project_editor = project_services.ProjectEditService(self._point_dict, self._line_dict)
            line_record = project_editor.add_line(first_point, second_point)

            if line_record is not None:
                current_name = line_record.name
                self.update_frame()
                self.logger(line=[current_name, redo])

                # Keep the legacy point-to-point index synchronized while the GUI still reads it.
                self._line_point_to_point_string.extend(line_record.endpoint_keys)
                self.add_to_combinations_dict(current_name)
            project_services.mark_lines_for_recalculation(self._line_to_struc)
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a line number.')
        return current_name

    def _is_flat_calculation_domain(self, calculation_domain):
        return calculation_domain in api_helpers.FLAT_STRUCTURE_DOMAINS

    def _build_flat_structure_property_request(self):
        return project_services.FlatStructurePropertyRequest(
            calculation_domain=self._new_calculation_domain.get(),
            base_values={
                'material': self._new_material.get(),
                'material_factor': self._new_material_factor.get(),
                'span': self._new_field_len.get(),
                'spacing': self._new_stf_spacing.get(),
                'plate_thk': self._new_plate_thk.get(),
                'stf_web_h': self._new_stf_web_h.get(),
                'stf_web_t': self._new_stf_web_t.get(),
                'stf_fl_w': self._new_stf_fl_w.get(),
                'stf_fl_t': self._new_stf_fl_t.get(),
                'structure_type': self._new_stucture_type.get(),
                'stf_type': self._new_stf_type.get(),
                'sigma_y1': self._new_sigma_y1.get(),
                'sigma_y2': self._new_sigma_y2.get(),
                'sigma_x1': self._new_sigma_x1.get(),
                'sigma_x2': self._new_sigma_x2.get(),
                'tau_xy': self._new_tauxy.get(),
                'plate_kpp': self._new_plate_kpp.get(),
                'stf_kps': self._new_stf_kps.get(),
                'stf_km1': self._new_stf_km1.get(),
                'stf_km2': self._new_stf_km2.get(),
                'stf_km3': self._new_stf_km3.get(),
                'pressure_side': self._new_pressure_side.get(),
                'zstar_optimization': self._new_zstar_optimization.get(),
                'puls_method': self._new_puls_method.get(),
                'puls_boundary': self._new_puls_panel_boundary.get(),
                'puls_stiffener_end': self._new_buckling_stf_end_support.get(),
                'puls_sp_or_up': self._new_puls_sp_or_up.get(),
                'puls_up_boundary': self._new_puls_up_boundary.get(),
                'panel_or_shell': self._new_panel_or_shell.get(),
                'girder_lg': self._new_girder_length_LG.get(),
            },
            girder_values={
                'web_h': self._new_girder_web_h.get(),
                'web_t': self._new_girder_web_t.get(),
                'fl_w': self._new_girder_fl_w.get(),
                'fl_t': self._new_girder_fl_t.get(),
                'type': self._new_girder_type.get(),
            },
            buckling_values={
                'min_pressure_adjacent_spans': self._new_buckling_min_press_adj_spans.get(),
                'load_factor_stresses': self._new_buckling_lf_stresses.get(),
                'stiffener_end_support': self._new_buckling_stf_end_support.get(),
                'girder_end_support': self._new_buckling_girder_end_support.get(),
                'tension_field': self._new_buckling_tension_field.get(),
                'plate_effective_against_sigy': self._new_buckling_effective_against_sigy.get(),
                'buckling_length_factor_stf': self._new_buckling_length_factor_stf.get(),
                'buckling_length_factor_girder': self._new_buckling_length_factor_stf.get(),
                'km3': self._new_buckling_km3.get(),
                'km2': self._new_buckling_km2.get(),
                'girder_dist_lateral_support': self._new_buckling_girder_dist_bet_lat_supp.get(),
                'stiffener_dist_lateral_support': self._new_buckling_stf_dist_bet_lat_supp.get(),
                'panel_length': self._new_panel_length_Lp.get(),
                'fabrication_method_stiffener': self._new_buckling_fab_method_stf.get(),
                'fabrication_method_girder': self._new_buckling_fab_method_girder.get(),
            },
            structure_types=self._structure_types,
        )

    def _build_flat_structure_properties(self):
        return project_services.FlatStructurePropertyService.build(
            self._build_flat_structure_property_request()
        )

    def _build_flat_structure_property_request_from_excel_record(self, import_record, span):
        plate_thk, spacing, web_h, web_t, flange_w, flange_t = import_record.plate_values
        sigma_x1, sigma_x2, sigma_y1, sigma_y2, tau_xy = import_record.stress_values
        girder_length, girder_web_h, girder_web_t, girder_fl_w, girder_fl_t, girder_type = \
            import_record.girder_values
        overpressure, structure_type, stf_end, girder_end, fab_stf, fab_girder, length_stf, length_girder, \
            stf_lateral_support, girder_lateral_support, tension_field, effective_against_sigy = \
            import_record.buckling_values

        return project_services.FlatStructurePropertyRequest(
            calculation_domain=import_record.calculation_domain,
            base_values={
                'material': self._new_material.get(),
                'material_factor': self._new_material_factor.get(),
                'span': span,
                'spacing': spacing,
                'plate_thk': plate_thk,
                'stf_web_h': web_h,
                'stf_web_t': web_t,
                'stf_fl_w': flange_w,
                'stf_fl_t': flange_t,
                'structure_type': structure_type if structure_type is not None else self._new_stucture_type.get(),
                'stf_type': self._new_stf_type.get(),
                'sigma_y1': sigma_y1,
                'sigma_y2': sigma_y2,
                'sigma_x1': sigma_x1,
                'sigma_x2': sigma_x2,
                'tau_xy': tau_xy,
                'plate_kpp': self._new_plate_kpp.get(),
                'stf_kps': self._new_stf_kps.get(),
                'stf_km1': self._new_stf_km1.get(),
                'stf_km2': self._new_stf_km2.get(),
                'stf_km3': self._new_stf_km3.get(),
                'pressure_side': self._new_pressure_side.get(),
                'zstar_optimization': self._new_zstar_optimization.get(),
                'puls_method': self._new_puls_method.get(),
                'puls_boundary': self._new_puls_panel_boundary.get(),
                'puls_stiffener_end': stf_end if stf_end is not None else self._new_buckling_stf_end_support.get(),
                'puls_sp_or_up': self._new_puls_sp_or_up.get(),
                'puls_up_boundary': self._new_puls_up_boundary.get(),
                'panel_or_shell': self._new_panel_or_shell.get(),
                'girder_lg': girder_length,
            },
            girder_values={
                'web_h': girder_web_h,
                'web_t': girder_web_t,
                'fl_w': girder_fl_w,
                'fl_t': girder_fl_t,
                'type': girder_type if girder_type is not None else self._new_girder_type.get(),
            },
            buckling_values={
                'min_pressure_adjacent_spans': self._new_buckling_min_press_adj_spans.get(),
                'load_factor_stresses': self._new_buckling_lf_stresses.get(),
                'stiffener_end_support': stf_end if stf_end is not None else self._new_buckling_stf_end_support.get(),
                'girder_end_support': girder_end if girder_end is not None
                else self._new_buckling_girder_end_support.get(),
                'tension_field': tension_field if tension_field is not None else self._new_buckling_tension_field.get(),
                'plate_effective_against_sigy': effective_against_sigy if effective_against_sigy is not None
                else self._new_buckling_effective_against_sigy.get(),
                'buckling_length_factor_stf': length_stf if length_stf is not None
                else self._new_buckling_length_factor_stf.get(),
                'buckling_length_factor_girder': length_girder if length_girder is not None
                else self._new_buckling_length_factor_stf.get(),
                'km3': self._new_buckling_km3.get(),
                'km2': self._new_buckling_km2.get(),
                'girder_dist_lateral_support': girder_lateral_support if girder_lateral_support is not None
                else self._new_buckling_girder_dist_bet_lat_supp.get(),
                'stiffener_dist_lateral_support': stf_lateral_support if stf_lateral_support is not None
                else self._new_buckling_stf_dist_bet_lat_supp.get(),
                'panel_length': self._new_panel_length_Lp.get(),
                'fabrication_method_stiffener': fab_stf if fab_stf is not None
                else self._new_buckling_fab_method_stf.get(),
                'fabrication_method_girder': fab_girder if fab_girder is not None
                else self._new_buckling_fab_method_girder.get(),
            },
            structure_types=self._structure_types,
        ), overpressure

    def _build_flat_structure_property_request_from_cylinder_excel_record(self, import_record):
        shell_thk = import_record.shell_values[0]
        long_web_h, long_web_t, long_fl_w, long_fl_t, panel_spacing, long_type = \
            import_record.longitudinal_values

        return project_services.FlatStructurePropertyRequest(
            calculation_domain=import_record.calculation_domain,
            base_values={
                'material': self._new_material.get(),
                'material_factor': self._new_material_factor.get(),
                'span': hlp.dist(import_record.first_point, import_record.second_point),
                'spacing': panel_spacing,
                'plate_thk': shell_thk,
                'stf_web_h': long_web_h,
                'stf_web_t': long_web_t,
                'stf_fl_w': long_fl_w,
                'stf_fl_t': long_fl_t,
                'structure_type': self._new_stucture_type.get(),
                'stf_type': long_type,
                'sigma_y1': self._new_sigma_y1.get(),
                'sigma_y2': self._new_sigma_y2.get(),
                'sigma_x1': self._new_sigma_x1.get(),
                'sigma_x2': self._new_sigma_x2.get(),
                'tau_xy': self._new_tauxy.get(),
                'plate_kpp': self._new_plate_kpp.get(),
                'stf_kps': self._new_stf_kps.get(),
                'stf_km1': self._new_stf_km1.get(),
                'stf_km2': self._new_stf_km2.get(),
                'stf_km3': self._new_stf_km3.get(),
                'pressure_side': self._new_pressure_side.get(),
                'zstar_optimization': self._new_zstar_optimization.get(),
                'puls_method': self._new_puls_method.get(),
                'puls_boundary': self._new_puls_panel_boundary.get(),
                'puls_stiffener_end': self._new_buckling_stf_end_support.get(),
                'puls_sp_or_up': self._new_puls_sp_or_up.get(),
                'puls_up_boundary': self._new_puls_up_boundary.get(),
                'panel_or_shell': self._new_panel_or_shell.get(),
                'girder_lg': self._new_girder_length_LG.get(),
            },
            girder_values={
                'web_h': self._new_girder_web_h.get(),
                'web_t': self._new_girder_web_t.get(),
                'fl_w': self._new_girder_fl_w.get(),
                'fl_t': self._new_girder_fl_t.get(),
                'type': self._new_girder_type.get(),
            },
            buckling_values={
                'min_pressure_adjacent_spans': self._new_buckling_min_press_adj_spans.get(),
                'load_factor_stresses': self._new_buckling_lf_stresses.get(),
                'stiffener_end_support': self._new_buckling_stf_end_support.get(),
                'girder_end_support': self._new_buckling_girder_end_support.get(),
                'tension_field': self._new_buckling_tension_field.get(),
                'plate_effective_against_sigy': self._new_buckling_effective_against_sigy.get(),
                'buckling_length_factor_stf': self._new_buckling_length_factor_stf.get(),
                'buckling_length_factor_girder': self._new_buckling_length_factor_stf.get(),
                'km3': self._new_buckling_km3.get(),
                'km2': self._new_buckling_km2.get(),
                'girder_dist_lateral_support': self._new_buckling_girder_dist_bet_lat_supp.get(),
                'stiffener_dist_lateral_support': self._new_buckling_stf_dist_bet_lat_supp.get(),
                'panel_length': self._new_panel_length_Lp.get(),
                'fabrication_method_stiffener': self._new_buckling_fab_method_stf.get(),
                'fabrication_method_girder': self._new_buckling_fab_method_girder.get(),
            },
            structure_types=self._structure_types,
        )

    def _build_cylinder_structure_property_request(self):
        return project_services.CylinderStructurePropertyRequest(
            calculation_domain=self._new_calculation_domain.get(),
            dummy_values={
                'span': self._new_field_len.get(),
                'plate_thk': self._new_plate_thk.get(),
                'structure_type': self._new_stucture_type.get(),
                'sigma_y1': self._new_sigma_y1.get(),
                'sigma_y2': self._new_sigma_y2.get(),
                'sigma_x1': self._new_sigma_x1.get(),
                'sigma_x2': self._new_sigma_x2.get(),
                'tau_xy': self._new_tauxy.get(),
                'plate_kpp': self._new_plate_kpp.get(),
                'stf_kps': self._new_stf_kps.get(),
                'stf_km1': self._new_stf_km1.get(),
                'stf_km2': self._new_stf_km2.get(),
                'stf_km3': self._new_stf_km3.get(),
                'pressure_side': self._new_pressure_side.get(),
                'zstar_optimization': self._new_zstar_optimization.get(),
                'puls_method': self._new_puls_method.get(),
                'puls_boundary': self._new_puls_panel_boundary.get(),
                'puls_stiffener_end': self._new_buckling_stf_end_support.get(),
                'puls_sp_or_up': self._new_puls_sp_or_up.get(),
                'puls_up_boundary': self._new_puls_up_boundary.get(),
                'panel_or_shell': self._new_panel_or_shell.get(),
                'material_factor': self._new_material_factor.get(),
                'spacing': self._new_stf_spacing.get(),
            },
            shell_values={
                'thickness': self._new_shell_thk.get(),
                'radius': self._new_shell_radius.get(),
                'distance_between_rings': self._new_shell_dist_rings.get(),
                'length': self._new_shell_length.get(),
                'total_length': self._new_shell_tot_length.get(),
                'k_factor': self._new_shell_k_factor.get(),
                'cone_r1': self._new_shell_cone_r1.get(),
                'cone_r2': self._new_shell_cone_r2.get(),
                'cone_length': self._new_shell_cone_length.get(),
            },
            longitudinal_values={
                'spacing': self._new_stf_spacing.get(),
                'web_h': self._new_stf_web_h.get(),
                'web_t': self._new_stf_web_t.get(),
                'fl_w': self._new_stf_fl_w.get(),
                'fl_t': self._new_stf_fl_t.get(),
                'type': self._new_stf_type.get(),
            },
            ring_stiffener_values={
                'web_h': self._new_shell_ring_stf_hw.get(),
                'web_t': self._new_shell_ring_stf_tw.get(),
                'fl_w': self._new_shell_ring_stf_b.get(),
                'fl_t': self._new_shell_ring_stf_tf.get(),
                'type': self._new_shell_ring_stf_type.get(),
            },
            ring_frame_values={
                'web_h': self._new_shell_ring_frame_hw.get(),
                'web_t': self._new_shell_ring_frame_tw.get(),
                'fl_w': self._new_shell_ring_frame_b.get(),
                'fl_t': self._new_shell_ring_frame_tf.get(),
                'type': self._new_shell_ring_frame_type.get(),
            },
            load_input={
                'mode': self._new_shell_stress_or_force.get(),
                'Nsd': self._new_shell_Nsd.get(),
                'Msd': self._new_shell_Msd.get(),
                'M1sd': self._new_shell_Msd.get(),
                'M2sd': self._new_shell_M2sd.get(),
                'Tsd': self._new_shell_Tsd.get(),
                'Qsd': self._new_shell_Qsd.get(),
                'Q1sd': self._new_shell_Qsd.get(),
                'Q2sd': self._new_shell_Q2sd.get(),
                'sasd': self._new_shell_sasd.get(),
                'smsd': self._new_shell_smsd.get(),
                'tTsd': self._new_shell_tTsd.get(),
                'tQsd': self._new_shell_tQsd.get(),
                'psd': self._new_shell_psd.get(),
                'shsd': self._new_shell_shsd.get(),
            },
            main_values={
                'material_factor': self._new_shell_mat_factor.get(),
                'fab_method_ring_stiffener': self._new_shell_ring_stf_fab_method.get(),
                'fab_method_ring_frame': self._new_shell_ring_frame_fab_method.get(),
                'e_module': self._new_shell_e_module.get(),
                'poisson': self._new_shell_poisson.get(),
                'yield': self._new_shell_yield.get(),
                'length_between_girders': self._new_shell_ring_frame_length_between_girders.get(),
                'panel_spacing': self._new_shell_panel_spacing.get(),
                'ring_stiffener_excluded': self._new_shell_exclude_ring_stf.get(),
                'ring_frame_excluded': self._new_shell_exclude_ring_frame.get(),
                'uls_or_als': self._new_shell_uls_or_als.get(),
                'end_cap_pressure': self._new_shell_end_cap_pressure_included.get(),
            },
            structure_types=self._structure_types,
        )

    def _build_cylinder_excel_import_defaults(self):
        return project_services.CylinderExcelImportDefaults(
            plate_thk=self._new_plate_thk.get(),
            structure_type=self._new_stucture_type.get(),
            sigma_y1=self._new_sigma_y1.get(),
            sigma_y2=self._new_sigma_y2.get(),
            sigma_x1=self._new_sigma_x1.get(),
            sigma_x2=self._new_sigma_x2.get(),
            tau_xy=self._new_tauxy.get(),
            plate_kpp=self._new_plate_kpp.get(),
            stf_kps=self._new_stf_kps.get(),
            stf_km1=self._new_stf_km1.get(),
            stf_km2=self._new_stf_km2.get(),
            stf_km3=self._new_stf_km3.get(),
            pressure_side=self._new_pressure_side.get(),
            zstar_optimization=self._new_zstar_optimization.get(),
            puls_method=self._new_puls_method.get(),
            puls_boundary=self._new_puls_panel_boundary.get(),
            puls_stiffener_end=self._new_buckling_stf_end_support.get(),
            puls_sp_or_up=self._new_puls_sp_or_up.get(),
            puls_up_boundary=self._new_puls_up_boundary.get(),
            panel_or_shell=self._new_panel_or_shell.get(),
            material_factor=self._new_material_factor.get(),
            design_pressure=self._new_shell_psd.get(),
            shear_stress=self._new_shell_shsd.get(),
            e_module=self._new_shell_e_module.get(),
            poisson=self._new_shell_poisson.get(),
            length_between_girders=self._new_shell_ring_frame_length_between_girders.get(),
            fab_method_ring_stiffener=self._new_shell_ring_stf_fab_method.get(),
            fab_method_ring_frame=self._new_shell_ring_frame_fab_method.get(),
            end_cap_pressure=self._new_shell_end_cap_pressure_included.get(),
            structure_types=self._structure_types,
            ring_stiffener_type=self._new_shell_ring_stf_type.get(),
            ring_frame_type=self._new_shell_ring_frame_type.get(),
        )

    def _create_cylinder_structure_from_property_result(self, result):
        return self._create_cylinder_structure_from_properties(
            result.main_dict,
            result.shell_dict,
            result.longitudinal_dict,
            result.ring_stiffener_dict,
            result.ring_frame_dict,
            result.geometry,
        )

    def _build_cylinder_structure_properties(self):
        result = project_services.CylinderStructurePropertyService.build(
            self._build_cylinder_structure_property_request()
        )

        sasd, smsd, tTsd, tQsd, _ = result.derived_stresses
        if result.geometry == 9:
            Nsd, Msd, M2sd, Tsd, Qsd, Q2sd = result.derived_forces
        else:
            Nsd, Msd, Tsd, Qsd = result.derived_forces[:4]
        if self._new_shell_stress_or_force.get() == 1:
            self._new_shell_sasd.set(_round_calculated(sasd))
            self._new_shell_smsd.set(_round_calculated(smsd))
            self._new_shell_tTsd.set(_round_calculated(tTsd))
            self._new_shell_tQsd.set(_round_calculated(tQsd))
            if result.geometry == 9:
                self._new_shell_M2sd.set(_round_calculated(M2sd))
                self._new_shell_Q2sd.set(_round_calculated(Q2sd))
        else:
            self._new_shell_Nsd.set(_round_calculated(Nsd))
            self._new_shell_Msd.set(_round_calculated(Msd))
            self._new_shell_Tsd.set(_round_calculated(Tsd))
            self._new_shell_Qsd.set(_round_calculated(Qsd))
            if result.geometry == 9:
                self._new_shell_M2sd.set(_round_calculated(M2sd))
                self._new_shell_Q2sd.set(_round_calculated(Q2sd))

        cylinder_obj = self._create_cylinder_structure_from_property_result(result)

        return (
            cylinder_obj,
            result.main_dict,
            result.shell_dict,
            result.longitudinal_dict,
            result.ring_stiffener_dict,
            result.ring_frame_dict,
            result.geometry,
        )

    def _structure_input_is_missing(self):
        if not self._is_flat_calculation_domain(self._new_calculation_domain.get()):
            return False
        required_inputs = [self._new_stf_spacing.get(), self._new_plate_thk.get()]
        if self._new_calculation_domain.get() != 'Flat plate, unstiffened':
            required_inputs.extend([self._new_stf_web_h.get(), self._new_stf_web_t.get()])
        return any(value == 0 for value in required_inputs)

    @staticmethod
    def _show_missing_structure_input_warning():
        tk.messagebox.showwarning('No propertied defined', 'No properties is defined for the line!\n'
                                                           'Define spacing, web height, web thickness etc.\n'
                                                           'Either press button with stiffener or input manually.',
                                  type='ok')

    def _create_all_structure_from_properties(self, prop_dict):
        calculation_domain = self._new_calculation_domain.get()
        return AllStructure(Plate=CalcScantlings(prop_dict['Plate']),
                            Stiffener=None if calculation_domain == 'Flat plate, unstiffened'
                            else CalcScantlings(prop_dict['Stiffener']),
                            Girder=None if calculation_domain in ['Flat plate, unstiffened',
                                                                  'Flat plate, stiffened']
                            else CalcScantlings(prop_dict['Girder']),
                            main_dict=prop_dict['main dict'])

    def _create_cylinder_structure_from_properties(self, main_dict_cyl, shell_dict, long_dict, ring_stf_dict,
                                                   ring_frame_dict, geometry):
        ring_stf_excluded = main_dict_cyl.get('ring stf excluded', [self._new_shell_exclude_ring_stf.get()])[0]
        ring_frame_excluded = main_dict_cyl.get('ring frame excluded', [self._new_shell_exclude_ring_frame.get()])[0]
        return CylinderAndCurvedPlate(main_dict_cyl, Shell(shell_dict),
                                      long_stf=None if geometry in [1, 2, 5, 6, 9]
                                      else Structure(long_dict),
                                      ring_stf=None if any([geometry in [1, 2, 3, 4, 9],
                                                            ring_stf_excluded])
                                      else Structure(ring_stf_dict),
                                      ring_frame=None if any([geometry in [1, 2, 3, 4, 9],
                                                              ring_frame_excluded])
                                      else Structure(ring_frame_dict))

    def _clear_tanks_and_grid(self):
        self._tank_dict = {}
        self._main_grid.clear()
        self._compartments_listbox.delete(0, 'end')

    def _refresh_after_structure_change(self, suspend_recalc):
        if not suspend_recalc:
            # when changing multiple parameters, recalculations are suspended.
            project_services.mark_lines_for_recalculation(self._line_to_struc)
            state = self.update_frame()
            if state != None and self._line_is_active:
                self._weight_logger['new structure']['COG'].append(self.get_color_and_calc_state()['COG'])
                self._weight_logger['new structure']['weight'].append(self.get_color_and_calc_state()['Total weight'])
                self._weight_logger['new structure']['time'].append(time.time())
            self.cylinder_gui_mods()

        self.get_unique_plates_and_beams()

    def _resolve_new_structure_properties(self, pasted_structure=None, multi_return=None, toggle_multi=None,
                                          cylinder_return=None):
        cylinder_obj = None
        obj_dict_stf = None
        main_dict_cyl = shell_dict = long_dict = ring_stf_dict = ring_frame_dict = geometry = None

        if multi_return is not None:
            prop_dict = multi_return[0].get_main_properties()  # From optimizer.
        elif isinstance(toggle_multi, tuple):
            prop_dict, obj_dict_stf = toggle_multi
        elif toggle_multi is not None:
            prop_dict = toggle_multi
        elif pasted_structure is None:
            prop_dict, obj_dict_stf = self._build_flat_structure_properties()

            if cylinder_return is None and not self._is_flat_calculation_domain(self._new_calculation_domain.get()):
                cylinder_obj, main_dict_cyl, shell_dict, long_dict, ring_stf_dict, ring_frame_dict, geometry = \
                    self._build_cylinder_structure_properties()
        else:
            prop_dict = pasted_structure.get_main_properties()

        if cylinder_return is not None:
            cylinder_obj = cylinder_return
            main_dict_cyl, shell_dict, long_dict, ring_stf_dict, ring_frame_dict, geometry = \
                self._cylinder_property_parts(cylinder_return)

        if obj_dict_stf is None and isinstance(prop_dict, dict):
            obj_dict_stf = prop_dict.get('Stiffener')

        return NewStructureProperties(prop_dict, obj_dict_stf, cylinder_obj, main_dict_cyl, shell_dict, long_dict,
                                      ring_stf_dict, ring_frame_dict, geometry)

    @staticmethod
    def _cylinder_property_parts(cylinder_obj):
        main_dict_cyl, shell_dict, long_dict, ring_stf_dict, ring_frame_dict = cylinder_obj.get_all_properties()
        return main_dict_cyl, shell_dict, long_dict, ring_stf_dict, ring_frame_dict, main_dict_cyl['geometry'][0]

    def _add_structure_to_active_line(self, resolved):
        All = self._create_all_structure_from_properties(resolved.prop_dict)
        line_structures = project_services.LineStructureService(self._line_to_struc)
        line_structures.assign_structure(self._active_line, All, cylinder=resolved.cylinder_obj)

        self._sections = add_new_section(self._sections, struc.Section(resolved.obj_dict_stf))  # TODO error when pasting
        if line_structures.structure(self._active_line).Plate.get_structure_type() not in \
                self._structure_types['non-wt']:
            self._clear_tanks_and_grid()
        if not self._is_flat_calculation_domain(self._new_calculation_domain.get()):
            cylinder_obj = resolved.cylinder_obj
            if cylinder_obj is None:
                cylinder_obj = self._create_cylinder_structure_from_properties(
                    resolved.main_dict_cyl, resolved.shell_dict, resolved.long_dict, resolved.ring_stf_dict,
                    resolved.ring_frame_dict, resolved.geometry)
            line_structures.set_cylinder(self._active_line, cylinder_obj)

    def _scale_existing_flat_structure_if_needed(self, prev_all_obj):
        line_structures = project_services.LineStructureService(self._line_to_struc)
        if self._new_scale_stresses.get() and prev_all_obj.get_main_properties() != \
                line_structures.structure(self._active_line).get_main_properties():
            if prev_all_obj.Stiffener is not None:
                plate = line_structures.structure(self._active_line).Plate
                stiffener = line_structures.structure(self._active_line).Stiffener
                girder = line_structures.structure(self._active_line).Girder
                calc_tup = (plate.get_s(), plate.get_pl_thk(), stiffener.get_web_h(), stiffener.get_web_thk(),
                            stiffener.get_fl_w(),
                            stiffener.get_fl_thk(), plate.span, stiffener.girder_lg if girder is None else
                            girder.girder_lg, stiffener.stiffener_type)
            else:
                calc_tup = line_structures.structure(self._active_line).Plate.get_tuple()
            line_structures.replace_structure(
                self._active_line,
                op.create_new_calc_obj(prev_all_obj, calc_tup, fup=self._new_fup.get(), fdwn=self._new_fdwn.get())[0],
            )

    def _sync_fatigue_object_after_structure_update(self, prop_dict):
        project_services.LineStructureService(self._line_to_struc).sync_fatigue_after_structure_update(
            self._active_line, prop_dict)

    def _sync_cylinder_object_after_structure_update(self, cylinder_obj, cylinder_return):
        line_structures = project_services.LineStructureService(self._line_to_struc)
        if all([cylinder_obj is None, cylinder_return is None,
                line_structures.cylinder(self._active_line) is not None]):
            line_structures.set_cylinder(self._active_line, None)
        elif cylinder_obj is not None:
            if line_structures.cylinder(self._active_line) is not None and self._new_scale_stresses.get():
                NewCylinderObj = op.create_new_cylinder_obj(line_structures.cylinder(self._active_line),
                                                            cylinder_obj.get_x_opt())
                NewCylinderObj.LongStfObj = None if cylinder_obj.LongStfObj is None \
                    else NewCylinderObj.LongStfObj
                NewCylinderObj.RingStfObj = None if cylinder_obj.RingStfObj is None \
                    else NewCylinderObj.RingStfObj
                NewCylinderObj.RingFrameObj = None if cylinder_obj.RingFrameObj is None \
                    else NewCylinderObj.RingFrameObj
            line_structures.set_cylinder(self._active_line, cylinder_obj)
        elif cylinder_return is not None:
            line_structures.set_cylinder(self._active_line, cylinder_return)

    def _update_existing_active_line_structure(self, resolved, cylinder_return):
        line_structures = project_services.LineStructureService(self._line_to_struc)
        prop_dict = resolved.prop_dict
        prev_type = line_structures.structure(self._active_line).Plate.get_structure_type()
        prev_all_obj = copy.deepcopy(line_structures.structure(self._active_line))
        line_structures.update_structure_properties(self._active_line, prop_dict)

        self._scale_existing_flat_structure_if_needed(prev_all_obj)
        self._sync_fatigue_object_after_structure_update(prop_dict)

        if prev_type in self._structure_types['non-wt'] and prop_dict['Plate']['structure_type'][0] in \
                self._structure_types['internals'] + self._structure_types['horizontal'] + \
                self._structure_types['vertical']:
            self._clear_tanks_and_grid()

        self._sync_cylinder_object_after_structure_update(resolved.cylinder_obj, cylinder_return)

    def _apply_resolved_new_structure(self, resolved, cylinder_return=None):
        if self._active_line not in self._line_to_struc:
            self._add_structure_to_active_line(resolved)
        else:
            self._update_existing_active_line_structure(resolved, cylinder_return)
        self._calculate_load_combinations_after_structure_update()

    def _replace_active_line_with_optimized_structure(self, optimized_structure):
        """Replace the active single-line structure with the optimizer result object."""
        if optimized_structure is None:
            return False

        line_structures = project_services.LineStructureService(self._line_to_struc)
        if self._active_line in self._line_to_struc:
            line_structures.replace_structure(self._active_line, optimized_structure)
            line_structures.set_cylinder(self._active_line, None)
        else:
            line_structures.assign_structure(self._active_line, optimized_structure, cylinder=None)

        try:
            self._sync_fatigue_object_after_structure_update(optimized_structure.get_main_properties())
        except Exception:
            pass

        self._calculate_load_combinations_after_structure_update()
        project_services.mark_line_for_recalculation(self._line_to_struc, self._active_line)
        return True

    def _calculate_load_combinations_after_structure_update(self):
        try:
            self.calculate_all_load_combinations_for_line_all_lines()
        except (KeyError, AttributeError):
            pass

    def _prepare_new_structure_context(self, multi_return=None):
        if multi_return is not None:
            return

        self.save_no_dialogue(backup=True)  # keeping a backup
        if getattr(self, '_simplified_calculation_mode', False):
            self._ensure_single_dummy_line()
            self._select_single_calculation_line()
            self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)

    @staticmethod
    def _uses_visible_structure_inputs(pasted_structure=None, multi_return=None, toggle_multi=None,
                                       cylinder_return=None):
        return all(value is None for value in (pasted_structure, multi_return, toggle_multi, cylinder_return))

    def new_structure(self, event=None, pasted_structure=None, multi_return=None, toggle_multi=None,
                      suspend_recalc=False, cylinder_return=None):
        '''
        This method maps the structure to the line when clicking "add structure to line" button.
        The result is put in a dictionary. Key is line name and value is the structure object.

        self_line_to_stuc
            [0] AllStructure class
            [1] None
            [2] calc fatigue class instance
            [3] load class instance
            [4] None
            [5] Cylinder buckling data
        :return:
        '''
        self._prepare_new_structure_context(multi_return)

        if self._uses_visible_structure_inputs(pasted_structure, multi_return, toggle_multi, cylinder_return):
            if self._structure_input_is_missing():
                self._show_missing_structure_input_warning()
                return

        if self._line_is_active or multi_return is not None:
            # structure dictionary: name of line : [ 0.Structure class, 1.calc scantling class,
            # 2.calc fatigue class, 3.load object, 4.load combinations result ]
            resolved = self._resolve_new_structure_properties(
                pasted_structure=pasted_structure, multi_return=multi_return, toggle_multi=toggle_multi,
                cylinder_return=cylinder_return)
            self._apply_resolved_new_structure(resolved, cylinder_return)

        self._refresh_after_structure_change(suspend_recalc)

    def option_meny_structure_type_trace(self, event):
        ''' Updating of the values in the structure type option menu. '''

        self._new_sigma_y1.set(self._default_stresses[self._new_stucture_type.get()][0])
        self._new_sigma_y2.set(self._default_stresses[self._new_stucture_type.get()][1])
        self._new_sigma_x1.set(self._default_stresses[self._new_stucture_type.get()][2])
        self._new_sigma_x2.set(self._default_stresses[self._new_stucture_type.get()][3])
        self._new_tauxy.set(self._default_stresses[self._new_stucture_type.get()][4])

        if self._new_stucture_type.get() in self._structure_types['vertical']:
            text = '(Vertical pressure calc.)'
        elif self._new_stucture_type.get() in self._structure_types['horizontal']:
            text = '(Horizontal pressure calc.)'
        elif self._new_stucture_type.get() in self._structure_types['non-wt']:
            text = '(Non-WT (pressure = 0))'
        elif self._new_stucture_type.get() in self._structure_types['internals']:
            text = '(Internal, pressure from comp.)'
        else:
            text = ''

        self._new_stucture_type_label.set(text)

    def tank_density_trace(self, event):
        ''' Setting tank densities '''
        self._new_density.set(self._tank_options[self._new_content_type.get()])

    def new_tank(self, comp_no, cells, min_el, max_el):
        '''
        Creating the tanks.
        :return:
        '''
        # points, self._point_dict, content), point
        self.save_no_dialogue(backup=True)  # keeping a backup

        temp_tank_dict = {'comp_no': comp_no,
                          'cells': cells,
                          'min_el': min_el[1],
                          'max_el': max_el[1],
                          'content': self._new_content_type.get(),
                          'added_press': self._new_overpresure.get(),
                          'acc': self._accelerations_dict,
                          'density': self._new_density.get(),
                          'all_types': self._options_type}

        self._tank_dict['comp' + str(comp_no)] = Tanks(temp_tank_dict)
        if self.__returned_load_data is not None:
            map(self.on_close_load_window, self.__returned_load_data)

        self.get_cob()  # Recalculating COB

    def get_cob(self):
        '''
        Calculation of center of buoyancy.
        '''
        self._center_of_buoyancy = dict()
        self._center_of_buoyancy['all'] = self._grid_calc.grid.get_center_of_matrix(scale=self._base_scale_factor)

        for load, data in self._load_dict.items():
            if data[0].is_static():
                draft = data[0].get_static_draft()
                cob = self._grid_calc.grid.get_center_of_matrix(height_limit=draft, scale=self._base_scale_factor)
                self._center_of_buoyancy[draft] = cob

    def calculate_all_load_combinations_for_line_all_lines(self):
        '''
        Calculating all results.
        :return:
        '''
        line_results = {}
        for line, data in self._line_to_struc.items():
            line_results[line] = data[1].is_acceptable_sec_mod(
                data[1].get_section_modulus(), self.get_highest_pressure(line)['normal'])

        return line_results

    def calculate_all_load_combinations_for_line(self, line, limit_state='ULS', get_load_info=False):
        '''
        Calculating pressure for line.
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,1]} # DNV  loads factors
        self._load_conditions = ['loaded', 'ballast','tanktest']
        :return:
        '''
        return project_services.LinePressureService.calculate_combinations(
            self._build_line_pressure_input(line),
            limit_state=limit_state,
            get_load_info=get_load_info,
        )

    def calculate_one_load_combination(self, current_line, comb_name, load_condition):
        '''
        Creating load combination for ULS.
        Inserted into self._line_to_struc index = 4
        "dnva", "line12", "static_ballast_10m"
        #load combination dictionary (comb,line,load) : [stat - DoubleVar(), dyn - DoubleVar], on/off - IntVar()]
        :return:
        '''
        return project_services.LinePressureService.calculate_one(
            self._build_line_pressure_input(current_line),
            comb_name,
            load_condition,
        )

    def _build_line_pressure_input(self, current_line):
        if self._tank_dict == {}:
            defined_tanks = ()
        else:
            defined_tanks = tuple(
                ('comp' + str(int(tank_num)), self._tank_dict['comp' + str(int(tank_num))])
                for tank_num in self.get_compartments_for_line_duplicates(current_line)
            )

        return project_services.LinePressureInput(
            line_name=current_line,
            line_bundle=self._line_to_struc[current_line],
            coordinate=(self.get_line_radial_mid(current_line), self.get_line_low_elevation(current_line)),
            defined_tanks=defined_tanks,
            accelerations=self._accelerations_dict,
            load_factors=project_services.load_factor_records(self._new_load_comb_dict),
        )

    def run_optimizer_for_line(self, line, goal, constrains):
        '''
        Returning result of a oprimize process
        :param line:
        :param goal:
        :param constrains:
        :return:
        '''
        pass

    def update_tank(self):
        '''
        Updating properties of the tank object that was created during BFS search.
        :return:
        '''
        if len(list(self._tank_dict.keys())) == 0:
            return
        current_tank = self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
        current_tank.set_overpressure(self._new_overpresure.get())
        current_tank.set_content(self._new_content_type.get())
        current_tank.set_acceleration(self._accelerations_dict)
        current_tank.set_density(self._new_density.get())
        project_services.mark_lines_for_recalculation(self._line_to_struc)

    def delete_line(self, event=None, undo=None, line=None):
        '''
        Deleting line and line properties.
        :return:
        '''
        try:
            if line is not None:
                line = line
            else:
                line = 'line' + str(self._ent_delete_line.get())

            if line in self._line_dict.keys() or undo is not None:
                line = line if undo is None else undo
                project_editor = project_services.ProjectEditService(self._point_dict, self._line_dict)
                line_record = project_editor.line(line)

                if line in self._line_dict.keys():
                    if line in self._line_to_struc.keys():
                        if self._line_to_struc[line][0].Plate.get_structure_type() not in self._structure_types[
                            'non-wt']:
                            self.delete_properties_pressed()
                            self.delete_all_tanks()
                    project_editor.remove_line(line)
                    if line in self._line_to_struc.keys():
                        self._line_to_struc.pop(line)
                    for endpoint_key in line_record.endpoint_keys:
                        self._line_point_to_point_string.pop(self._line_point_to_point_string.index(endpoint_key))
                    self._active_line = ''

                    # Removing from load dict
                    if self._load_dict != {}:
                        loads = list(self._load_dict.keys())
                        for load in loads:
                            if line in self._load_dict[load][1]:
                                self._load_dict[load][1].pop(self._load_dict[load][1].index(line))
                self.update_frame()
            else:
                messagebox.showinfo(title='No line.', message='Input line does noe exist.')

        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def delete_point(self, event=None, undo=None, point=None):
        '''
        Deleting point and connected lines.
        '''
        try:
            if point == None:
                point = 'point' + str(self._ent_delete_point.get()) if undo is None else undo

            if point in self._point_dict.keys():
                project_editor = project_services.ProjectEditService(self._point_dict, self._line_dict)
                line_to_delete = project_editor.connected_line_names(point)
                # deleting the lines and the connected properties. also deleting point to point string list items.
                for line in list(line_to_delete):
                    self.delete_line(line=line)
                    # point_str = 'p' + str(self._line_dict[line][0]) + 'p' + str(self._line_dict[line][1])
                    # point_str_rev = 'p' + str(self._line_dict[line][1]) + 'p' + str(self._line_dict[line][0])
                    # self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str))
                    # self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str_rev))
                    # self._line_dict.pop(line)
                    # # properties are deleted here
                    # if line in self._line_to_struc.keys():
                    #     self._line_to_struc.pop(line)
                # at the en, the points is deleted from the point dict.
                project_editor.remove_point(point)
                self._active_point = ''
            else:
                messagebox.showinfo(title='No point.', message='Input point does not exist.')

            self.update_frame()
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def delete_key_pressed(self, event=None):
        if self._active_line != '':
            self.delete_line(line=self._active_line)
        if self._active_point != '':
            self.delete_point()

    def copy_property(self, event=None):
        ''' Copy a property of a line'''
        if self._active_line not in self._line_to_struc.keys():
            tk.messagebox.showinfo('No properties', 'This line does not have properties.')
            return
        else:
            self.__copied_line_prop = self._active_line

    def paste_property(self, event=None):
        ''' Paste property to line '''
        if self._active_line not in self._line_to_struc.keys():
            if self._line_to_struc[self.__copied_line_prop][5] is not None:
                self.new_structure(cylinder_return=self._line_to_struc[self.__copied_line_prop][5])
            else:
                self.new_structure(pasted_structure=self._line_to_struc[self.__copied_line_prop][0])
        elif self._line_to_struc[self.__copied_line_prop][5] is not None:
            self.new_structure(cylinder_return=self._line_to_struc[self.__copied_line_prop][5])
        elif self._line_to_struc[self._active_line][0].Plate.get_structure_type() != \
                self._line_to_struc[self.__copied_line_prop][0].Plate.get_structure_type():
            tk.messagebox.showerror('Paste error', 'Can only paste to same structure type. This is to avoid problems '
                                                   'with compartments not detecting changes to watertightness.')
            return
        else:
            self.new_structure(pasted_structure=self._line_to_struc[self.__copied_line_prop][0])

        self.update_frame()

    def delete_properties_pressed(self, event=None, line=None):

        action_taken = False
        if line != None:
            self._line_to_struc.pop(line)
            self._state_logger.pop(line)

            action_taken = True
        elif self._active_line != '' and self._active_line in self._line_to_struc.keys():
            self._line_to_struc.pop(self._active_line)
            self._state_logger.pop(self._active_line)
            action_taken = True

        if action_taken:
            project_services.mark_lines_for_recalculation(self._line_to_struc)
            self.update_frame()

    def delete_all_tanks(self):
        '''
        Delete the tank that has been selected in the Listbox
        :return:
        '''
        # if self._grid_calc != None:
        self._tank_dict = {}
        self._compartments_listbox.delete(0, 'end')
        self._main_grid.clear()
        self._grid_calc = None
        if self.__returned_load_data is not None:
            map(self.on_close_load_window, self.__returned_load_data)
        # else:
        #     pass
        self._center_of_buoyancy = dict()  # Resetting dict
        self.update_frame()

    def set_selected_variables(self, line):
        '''
        Setting the properties in the entry fields to the specified values.
        '''
        if line in self._line_to_struc:
            all_dict = self._line_to_struc[line][0].get_main_properties()
            main_dict = {}
            for key, val in all_dict['main dict'].items():
                main_dict[key] = [0, val[1]] if val[0] is None else val

            self._new_buckling_min_press_adj_spans.set(main_dict['minimum pressure in adjacent spans'][0])
            self._new_buckling_lf_stresses.set(main_dict['load factor on stresses'][0])
            self._new_buckling_stf_end_support.set(main_dict['stiffener end support'][0])
            self._new_buckling_girder_end_support.set(main_dict['girder end support'][0])
            self._new_buckling_tension_field.set(main_dict['tension field'][0])
            self._new_buckling_effective_against_sigy.set(main_dict['plate effective agains sigy'][0])
            self._new_buckling_length_factor_stf.set(main_dict['buckling length factor stf'][0])
            self._new_buckling_length_factor_girder.set(main_dict['buckling length factor girder'][0])
            self._new_buckling_km3.set(main_dict['km3'][0])
            self._new_buckling_km2.set(main_dict['km2'][0])
            self._new_buckling_stf_dist_bet_lat_supp.set(main_dict['stiffener distance between lateral support'][0])
            self._new_buckling_girder_dist_bet_lat_supp.set(main_dict['girder distance between lateral support'][0])
            self._new_buckling_fab_method_stf.set(main_dict['fabrication method stiffener'][0])
            self._new_buckling_fab_method_girder.set(main_dict['fabrication method girder'][0])
            self._new_pressure_side.set(main_dict['pressure side'][0])
            self._new_panel_length_Lp.set(main_dict['panel length, Lp'][0])
            self._new_calculation_domain.set(main_dict['calculation domain'][0])

            for idx, properties in enumerate([all_dict['Plate'], all_dict['Stiffener'], all_dict['Girder']]):
                if properties is None:
                    continue
                if idx == 0:
                    self._new_material.set(round(properties['mat_yield'][0] / 1e6, 5))
                    self._new_material_factor.set(properties['mat_factor'][0])
                    self._new_field_len.set(round(properties['span'][0] * 1000, 5))
                    self._new_plate_thk.set(round(properties['plate_thk'][0] * 1000, 5))
                    self._new_plate_kpp.set(properties['plate_kpp'][0])
                    # Round only float dust (5 decimals): these are the user's
                    # stored values, so their typed precision must survive the
                    # select -> edit -> add-properties round trip.
                    self._new_sigma_y1.set(round(properties['sigma_y1'][0], 5))
                    self._new_sigma_y2.set(round(properties['sigma_y2'][0], 5))
                    self._new_sigma_x1.set(round(properties['sigma_x1'][0], 5))
                    self._new_sigma_x2.set(round(properties['sigma_x2'][0], 5))
                    self._new_tauxy.set(round(properties['tau_xy'][0], 5))
                    self._new_stucture_type.set(properties['structure_type'][0])
                    # try:
                    #     self._new_pressure_side.set(properties['press_side'][0])
                    # except KeyError:
                    #     self._new_pressure_side.set('both sides')
                    self._new_zstar_optimization.set(properties['zstar_optimization'][0])
                    self._new_puls_method.set(properties['puls buckling method'][0])
                    self._new_puls_panel_boundary.set(properties['puls boundary'][0])
                    self._new_buckling_stf_end_support.set(properties['puls stiffener end'][0])
                    self._new_puls_sp_or_up.set(properties['puls sp or up'][0])
                    self._new_puls_up_boundary.set(properties['puls up boundary'][0])
                if idx == 1:
                    self._new_stf_spacing.set(round(properties['spacing'][0] * 1000, 5))
                    self._new_stf_kps.set(properties['stf_kps'][0])
                    self._new_stf_km1.set(properties['stf_km1'][0])
                    self._new_stf_km2.set(properties['stf_km2'][0])
                    self._new_stf_km3.set(properties['stf_km3'][0])
                    self._new_stf_web_h.set(round(properties['stf_web_height'][0] * 1000, 5))
                    self._new_stf_web_t.set(round(properties['stf_web_thk'][0] * 1000, 5))
                    self._new_stf_fl_w.set(round(properties['stf_flange_width'][0] * 1000, 5))
                    self._new_stf_fl_t.set(round(properties['stf_flange_thk'][0] * 1000, 5))
                    self._new_stf_type.set(properties['stf_type'][0])
                if idx == 2:
                    self._new_girder_web_h.set(round(properties['stf_web_height'][0] * 1000, 5))
                    self._new_girder_web_t.set(round(properties['stf_web_thk'][0] * 1000, 5))
                    self._new_girder_fl_w.set(round(properties['stf_flange_width'][0] * 1000, 5))
                    self._new_girder_fl_t.set(round(properties['stf_flange_thk'][0] * 1000, 5))
                    self._new_girder_type.set(properties['stf_type'][0])

            if self._line_to_struc[self._active_line][5] is not None:

                cylobj = self._line_to_struc[self._active_line][5]
                all_dicts = cylobj.get_all_properties()

                # Shell data input
                shell_dict = all_dicts['Shell']
                self._new_shell_thk.set(shell_dict['plate_thk'][0] * 1000)
                self._new_shell_radius.set(shell_dict['radius'][0] * 1000)
                self._new_shell_dist_rings.set(shell_dict['distance between rings, l'][0] * 1000)
                self._new_shell_length.set(shell_dict['length of shell, L'][0] * 1000)
                self._new_shell_tot_length.set(shell_dict['tot cyl length, Lc'][0] * 1000)
                self._new_shell_k_factor.set(shell_dict['eff. buckling lenght factor'][0])
                self._new_shell_yield.set(shell_dict['mat_yield'][0] / 1e6)
                if shell_dict.get('cone r1', [None])[0] is not None:
                    self._new_shell_cone_r1.set(shell_dict['cone r1'][0] * 1000)
                if shell_dict.get('cone r2', [None])[0] is not None:
                    self._new_shell_cone_r2.set(shell_dict['cone r2'][0] * 1000)
                if shell_dict.get('cone length, l', [None])[0] is not None:
                    self._new_shell_cone_length.set(shell_dict['cone length, l'][0] * 1000)

                main_dict_cyl = all_dicts['Main class']

                self._new_shell_sasd.set(main_dict_cyl['sasd'][0] / 1e6)
                self._new_shell_smsd.set(main_dict_cyl['smsd'][0] / 1e6)
                self._new_shell_tTsd.set(main_dict_cyl['tTsd'][0] / 1e6)
                self._new_shell_tQsd.set(main_dict_cyl['tQsd'][0] / 1e6)
                self._new_shell_psd.set(main_dict_cyl['psd'][0] / 1e6)
                self._new_shell_shsd.set(main_dict_cyl['shsd'][0] / 1e6)
                if main_dict_cyl.get('cone Nsd', [None])[0] is not None:
                    self._new_shell_Nsd.set(main_dict_cyl['cone Nsd'][0])
                if main_dict_cyl.get('cone M1sd', [None])[0] is not None:
                    self._new_shell_Msd.set(main_dict_cyl['cone M1sd'][0])
                if main_dict_cyl.get('cone M2sd', [None])[0] is not None:
                    self._new_shell_M2sd.set(main_dict_cyl['cone M2sd'][0])
                if main_dict_cyl.get('cone Tsd', [None])[0] is not None:
                    self._new_shell_Tsd.set(main_dict_cyl['cone Tsd'][0])
                if main_dict_cyl.get('cone Q1sd', [None])[0] is not None:
                    self._new_shell_Qsd.set(main_dict_cyl['cone Q1sd'][0])
                if main_dict_cyl.get('cone Q2sd', [None])[0] is not None:
                    self._new_shell_Q2sd.set(main_dict_cyl['cone Q2sd'][0])

                self._new_calculation_domain.set(api_helpers.domain_for_geometry_id(main_dict_cyl['geometry'][0]))
                self._new_shell_mat_factor.set(main_dict_cyl['material factor'][0])
                self._new_shell_ring_stf_fab_method.set(main_dict_cyl['fab method ring stf'][0])
                self._new_shell_ring_frame_fab_method.set(main_dict_cyl['fab method ring girder'][0])
                self._new_shell_e_module.set(main_dict_cyl['E-module'][0])
                self._new_shell_poisson.set(main_dict_cyl['poisson'][0])
                self._new_shell_yield.set(main_dict_cyl['mat_yield'][0] / 1e6)
                self._new_shell_ring_frame_length_between_girders.set(main_dict_cyl['length between girders'][0] * 1000)
                self._new_shell_panel_spacing.set(main_dict_cyl['panel spacing, s'][0] * 1000)
                self._new_shell_exclude_ring_stf.set(main_dict_cyl['ring stf excluded'][0])
                self._new_shell_exclude_ring_frame.set(main_dict_cyl['ring frame excluded'][0])
                self._new_shell_uls_or_als.set(main_dict_cyl['ULS or ALS'][0])
                self._new_shell_end_cap_pressure_included.set(main_dict_cyl['end cap pressure'][0])

                if cylobj.LongStfObj is not None:
                    # Longitudinal stiffener input
                    long_dict = all_dicts['Long. stf.']
                    self._new_stf_spacing.set(long_dict['spacing'][0] * 1000)
                    self._new_stf_web_h.set(long_dict['stf_web_height'][0] * 1000)
                    self._new_stf_web_t.set(long_dict['stf_web_thk'][0] * 1000)
                    self._new_stf_fl_w.set(long_dict['stf_flange_width'][0] * 1000)
                    self._new_stf_fl_t.set(long_dict['stf_flange_thk'][0] * 1000)
                    self._new_stf_type.set(long_dict['stf_type'][0])
                    self._new_field_len.set(long_dict['span'][0] * 1000)
                    self._new_shell_yield.set(long_dict['mat_yield'][0] / 1e6)
                    self._new_panel_or_shell.set('shell')
                if cylobj.RingStfObj is not None:
                    ring_stf_dict = all_dicts['Ring stf.']
                    self._new_shell_ring_stf_hw.set(ring_stf_dict['stf_web_height'][0] * 1000)
                    self._new_shell_ring_stf_tw.set(ring_stf_dict['stf_web_thk'][0] * 1000)
                    self._new_shell_ring_stf_b.set(ring_stf_dict['stf_flange_width'][0] * 1000)
                    self._new_shell_ring_stf_tf.set(ring_stf_dict['stf_flange_thk'][0] * 1000)
                    self._new_shell_ring_stf_type.set(ring_stf_dict['stf_type'][0])
                    self._new_shell_yield.set(ring_stf_dict['mat_yield'][0] / 1e6)
                    self._new_panel_or_shell.set('shell')
                if cylobj.RingFrameObj is not None:
                    ring_frame_dict = all_dicts['Ring frame']
                    self._new_shell_ring_frame_hw.set(ring_frame_dict['stf_web_height'][0] * 1000)
                    self._new_shell_ring_frame_tw.set(ring_frame_dict['stf_web_thk'][0] * 1000)
                    self._new_shell_ring_frame_b.set(ring_frame_dict['stf_flange_width'][0] * 1000)
                    self._new_shell_ring_frame_tf.set(ring_frame_dict['stf_flange_thk'][0] * 1000)
                    self._new_shell_ring_frame_type.set(ring_frame_dict['stf_type'][0])
                    self._new_shell_yield.set(ring_frame_dict['mat_yield'][0] / 1e6)
                    self._new_panel_or_shell.set('shell')

    def get_highest_pressure(self, line, limit_state='ULS'):
        '''
        Returning the highest pressure of a line.
        :return:
        '''
        if limit_state == 'FLS':
            return
        return project_services.LinePressureService.highest_pressure(
            self._build_line_pressure_input(line),
            limit_state=limit_state,
        )

    def get_fatigue_pressures(self, line, accelerations=(0, 0, 0)):
        ''' Retruning a dictionary of internal and external pressures. '''
        loaded_exist = False
        ballast_exist = False
        part_exist = False

        for load in self._line_to_struc[line][3]:
            if load.get_limit_state() == 'FLS':
                if load.get_load_condition() == 'loaded':
                    loaded_exist = True
                elif load.get_load_condition() == 'ballast':
                    ballast_exist = True
                elif load.get_load_condition() == 'part':
                    part_exist = True
                else:
                    pass
        fls_exist = (loaded_exist, ballast_exist, part_exist)

        pressures = {}
        pressures['p_ext'] = {'loaded': 0, 'ballast': 0, 'part': 0}
        for load in self._line_to_struc[line][3]:
            if load.get_limit_state() == 'FLS':
                for exist_i in range(len(fls_exist)):
                    if fls_exist[exist_i] and load.get_load_condition() == 'loaded':
                        pressures['p_ext']['loaded'] = load.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                                    accelerations[0],
                                                                                    self._line_to_struc[line][
                                                                                        0].Plate.get_structure_type())
                    if fls_exist[exist_i] and load.get_load_condition() == 'ballast':
                        pressures['p_ext']['ballast'] = load.get_calculated_pressure(
                            self.get_pressures_calc_coord(line),
                            accelerations[1],
                            self._line_to_struc[line][
                                0].Plate.get_structure_type())

                    if fls_exist[exist_i] and load.get_load_condition() == 'part':
                        pressures['p_ext']['part'] = load.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                                  accelerations[2],
                                                                                  self._line_to_struc[line][
                                                                                      0].Plate.get_structure_type())

        if self._tank_dict == {}:
            compartments = []
        else:
            compartments = [self._tank_dict['comp' + str(tank)] for tank in self.get_compartments_for_line(line)]
        pressures['p_int'] = {'loaded': 0, 'ballast': 0, 'part': 0}

        for comp in compartments:
            if fls_exist[0] and comp.is_loaded_condition():
                pressures['p_int']['loaded'] = comp.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                            accelerations[0])
            if fls_exist[1] and comp.is_ballast_condition():
                pressures['p_int']['ballast'] = comp.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                             accelerations[1])
            if fls_exist[2] and any([comp.is_loaded_condition(), comp.is_ballast_condition()]):
                pressures['p_int']['part'] = comp.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                          accelerations[2]) * 0.5
        return pressures

    def get_compartments_for_line(self, line):
        '''
        Finding the compartment connected to a specified line.
        :return:
        '''

        start_point = self._point_dict['point' + str(self._line_dict[line][0])]
        end_point = self._point_dict['point' + str(self._line_dict[line][1])]
        mid_point = self._main_grid.get_mid_point(self.get_grid_coord_from_points_coords(start_point),
                                                  self.get_grid_coord_from_points_coords(end_point))

        return list(filter(lambda x: x > 1, self._main_grid.get_adjacent_values(mid_point)))

    def get_compartments_for_line_duplicates(self, line):
        '''
        Finding the compartment connected to a specified line.
        :return:
        '''

        start_point = self._point_dict['point' + str(self._line_dict[line][0])]
        end_point = self._point_dict['point' + str(self._line_dict[line][1])]
        mid_point = self._main_grid.get_mid_point(self.get_grid_coord_from_points_coords(start_point),
                                                  self.get_grid_coord_from_points_coords(end_point))

        return list(filter(lambda x: x > 1, self._main_grid.get_adjacent_values_duplicates(mid_point)))

    def get_point_canvas_coord(self, point_no):
        '''
        Returning the canvas coordinates of the point. This value will change with slider.
        '''

        point_coord_x = self._canvas_draw_origo[0] + self._point_dict[point_no][0] * self._canvas_scale
        point_coord_y = self._canvas_draw_origo[1] - self._point_dict[point_no][1] * self._canvas_scale

        return [point_coord_x, point_coord_y]

    def get_point_actual_coord(self, point_no):
        '''
        Returning actutual (real world coordinates of a point.
        '''

        return [self._point_dict[point_no][0], self._point_dict[point_no][1]]

    def get_actual_elevation_from_grid_coords(self, grid_col):
        '''
        Converts coordinates
        :param canv_elevation:
        :return:
        '''

        y_coord = (self._main_grid.get_grid_height() - grid_col) / self._base_scale_factor
        self._main_grid.get_grid_height()
        return y_coord

    def get_grid_coord_from_points_coords(self, point_coord):
        '''
        Converts coordinates to be used in the grid. Returns (row,col). This value will not change with slider.
        :param point:
        :return:
        '''
        row = self._canvas_base_origo[1] - point_coord[1] * self._base_scale_factor
        col = point_coord[0] * self._base_scale_factor
        return (row, col)

    def get_point_coords_from_grid_coords(self, grid_coord):
        '''
        Converts coordinates to be used in the as points. Returns (x,y). This value will not change with slider.
        :param point:
        :return:
        '''
        x_coord = grid_coord[1] / self._base_scale_factor
        y_coord = (self._main_grid.get_grid_height() - grid_coord[0]) / self._base_scale_factor
        self._main_grid.get_grid_height()
        self._main_grid.get_grid_width()
        return x_coord, y_coord

    def get_canvas_coords_from_point_coords(self, actual_coords):
        '''
        Returns tuple of canvas points from actual (x,y)
        :param actual_coords:
        :return:
        '''
        canvas_coord_x = self._canvas_draw_origo[0] + actual_coords[0] * self._canvas_scale
        canvas_coord_y = self._canvas_draw_origo[1] - actual_coords[1] * self._canvas_scale

        return (canvas_coord_x, canvas_coord_y)

    def get_line_low_elevation(self, line):
        '''
        Finding elevation of a line. Used to calculate pressures in load combinations.
        :param line:
        :return:
        '''

        return min([self._point_dict['point' + str(point)][1] for point in self._line_dict[line]])

    def get_line_radial_mid(self, line):
        '''
        Getting the horizontal coordinates in the middle of a line.
        :param line:
        :return:
        '''
        return sum([self._point_dict['point' + str(point)][0] for point in self._line_dict[line]]) / 2

    def get_pressures_calc_coord(self, line):
        ''' Returning coordinates of the pressures calculation basis of a selected line. '''
        p1 = self._point_dict['point' + str(self._line_dict[line][0])]
        p2 = self._point_dict['point' + str(self._line_dict[line][1])]

        if p1[1] <= p2[1]:
            start_point = p1
            end_point = p2
        elif p1[1] == p2[1]:
            if p1[0] <= p2[0]:
                start_point = p1
                end_point = p2
            else:
                start_point = p2
                end_point = p1
        else:
            start_point = p2
            end_point = p1

        vector = [end_point[0] - start_point[0], end_point[1] - start_point[1]]

        return start_point[0] + vector[0] * 1 / 3, start_point[1] + vector[1] * 1 / 3

    def get_points(self):
        return self._point_dict

    def get_closest_point(self, given_point):
        '''
        Finding the closest point to av given value.
        Real coordinates used (meters).
        Returning point name, coordinates and distance.
        :param coordx:
        :param coordy:
        :return:
        '''

        current_dist = float('inf')
        current_point = None
        for point, coords in self._point_dict.items():
            if dist([coords[0], coords[1]], [given_point[0], given_point[1]]) < current_dist:
                current_dist = dist([coords[0], coords[1]], [given_point[0], given_point[1]])
                current_point = point

        return current_point, self._point_dict[current_point], current_dist

    def get_lines(self):
        return self._line_dict

    def get_unique_plates_and_beams(self):

        beams, plates = list(), list()
        if self._line_to_struc != {}:
            for line, data in self._line_to_struc.items():
                if data[0].Stiffener is not None:
                    this_beam = data[0].Stiffener.get_beam_string()
                    this_plate = data[0].Stiffener.get_pl_thk() * 1000
                    if this_beam not in beams:
                        beams.append(this_beam)
                    if this_plate not in plates:
                        plates.append(this_plate)

        return {'plates': plates, 'beams': beams}

    def make_point_point_line_string(self, point1, point2):
        '''
        For a line, this method makes a string 'p1p2' and 'p2p1'. Ensuring that lines are not overwritten.
        :param point1:
        :param point2:
        :return:
        '''

        return ['p' + str(point1) + 'p' + str(point2), 'p' + str(point2) + 'p' + str(point1)]

    def reset(self, activate_simplified=True):
        '''
        Resetting the script.
        :return:
        '''

        self._line_dict = {}
        self._point_dict = {}
        self._line_to_struc = {}
        self._line_point_to_point_string = []
        self._load_dict = {}
        self._new_load_comb_dict = {}
        self._line_is_active = False
        self._active_line = ''
        self._point_is_active = False
        self._active_point = ''
        self.delete_all_tanks()
        self._main_canvas.delete('all')
        self._prop_canvas.delete('all')
        self._result_canvas.delete('all')
        self._pending_grid_draw = {}
        self._p1_p2_select = False
        self._line_is_active = False  # True when a line is clicked
        self._active_line = ''  # Name of the clicked point
        self._point_is_active = False  # True when a point is clicked
        self._active_point = ''  # Name of the clicked point
        self.controls()  # Function to activate mouse clicks
        self._line_point_to_point_string = []  # This one ensures that a line is not created on top of a line
        self._accelerations_dict = {'static': 9.81, 'dyn_loaded': 0, 'dyn_ballast': 0}
        self._multiselect_lines = []

        # Initsializing the calculation grid used for tank definition
        self._main_grid = grid.Grid(self._grid_dimensions[0], self._grid_dimensions[1])
        self._grid_calc = None

        if getattr(self, '_simplified_calculation_mode', False) and activate_simplified:
            self._activate_simplified_calculation_pipeline()
        else:
            self.update_frame()

    def controls(self):
        '''
        Specifying the controls to be used.
        :return:
        '''
        self._main_canvas.bind('<Button-1>', self.button_1_click)
        self._main_canvas.bind('<Button-2>', self.button_2_click)
        self._main_canvas.bind('<Button-3>', self.button_3_click)
        self._main_canvas.bind("<B2-Motion>", self.button_2_click_and_drag)
        self._main_canvas.bind("<MouseWheel>", self.mouse_scroll)
        # self._prop_canvas.bind("<MouseWheel>", self.mouse_scroll)

        self._parent.bind('<Control-z>', self.undo)
        # self._parent.bind('<Control-y>', self.redo)
        # self._parent.bind('<Control-p>', self.delete_point)
        self._parent.bind('<Control-l>', self.delete_line)
        self._parent.bind('<Control-p>', self.copy_point)
        self._parent.bind('<Control-m>', self.move_point)
        self._parent.bind('<Control-n>', self.move_line)
        self._parent.bind('<Control-a>', self.select_all_lines)
        self._parent.bind('<Control-t>', self.select_all_lines)
        self._parent.bind('<Control-q>', self.new_line)
        self._parent.bind('<Control-s>', self.new_structure)
        self._parent.bind('<Delete>', self.delete_key_pressed)
        self._parent.bind('<Control-Delete>', self.delete_properties_pressed)
        self._parent.bind('<Control-e>', self.copy_property)
        self._parent.bind('<Control-d>', self.paste_property)
        self._parent.bind('<Left>', self.left_arrow)
        self._parent.bind('<Right>', self.right_arrow)
        self._parent.bind('<Down>', self.up_arrow)
        self._parent.bind('<Up>', self.down_arrow)
        self._parent.bind("<Alt-s>", self.save_no_dialogue)
        # self._parent.bind('<Enter>', self.enter_key_pressed)

    def left_arrow(self, event):

        if self._active_line == '':
            return
        else:
            idx = list(self._line_dict.keys()).index(self._active_line)

            if idx - 1 >= 0:
                self._active_line = list(self._line_dict.keys())[idx - 1]
            else:
                self._active_line = list(self._line_dict.keys())[-1]
        self.update_frame()

    def right_arrow(self, event):

        if self._active_line == '':
            return
        else:
            idx = list(self._line_dict.keys()).index(self._active_line)

            if idx + 1 < len(list(self._line_dict.keys())):
                self._active_line = list(self._line_dict.keys())[idx + 1]
            else:
                self._active_line = list(self._line_dict.keys())[0]
        self.update_frame()

    def up_arrow(self, event):

        if self._active_point == '':
            return
        else:
            idx = list(self._point_dict.keys()).index(self._active_point)

            if idx - 1 >= 0:
                self._active_point = list(self._point_dict.keys())[idx - 1]
            else:
                self._active_point = list(self._point_dict.keys())[-1]
        self.update_frame()

    def down_arrow(self, event):

        if self._active_point == '':
            return
        else:
            idx = list(self._point_dict.keys()).index(self._active_point)

            if idx + 1 < len(list(self._point_dict.keys())):
                self._active_point = list(self._point_dict.keys())[idx + 1]
            else:
                self._active_point = list(self._point_dict.keys())[0]
        self.update_frame()

    def select_all_lines(self, event=None):

        if self._toggle_btn.config('relief')[-1] == "sunken":
            for line in self._line_to_struc.keys():
                if line not in self._multiselect_lines:
                    if event.keysym == 't':
                        if self._line_to_struc[line][0].Plate.get_structure_type() == self._new_stucture_type.get():
                            self._multiselect_lines.append(line)
                    else:
                        self._multiselect_lines.append(line)
        else:
            tk.messagebox.showinfo('CTRL-A and CTRL-T', 'CTRL-A and CTRL-T is used to select all lines \n'
                                                        'with the intension to change a single variable in all lines.\n'
                                                        'Press the Toggle select multiple button.')
        self.update_frame()

    def mouse_scroll(self, event):

        if event.y < self._main_canvas.winfo_height():
            self._canvas_scale += event.delta / 50
            self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale
        else:
            pass

        self.update_frame()

    def button_2_click(self, event):
        self._previous_drag_mouse = [event.x, event.y]

    def button_2_click_and_drag(self, event):
        self._canvas_draw_origo = (self._canvas_draw_origo[0] - (self._previous_drag_mouse[0] - event.x),
                                   self._canvas_draw_origo[1] - (self._previous_drag_mouse[1] - event.y))
        self._previous_drag_mouse = (event.x, event.y)
        self.update_frame()
        # self.draw_canvas(state=state)

    def button_1_click(self, event=None):
        '''
        When clicking the right button, this method is called.
        method is referenced in
        '''

        if getattr(self, '_fea_buckling_mode', False):
            self._refresh_fea_buckling_views(rebuild_3d=True)
            return

        if getattr(self, '_simplified_calculation_mode', False):
            self._select_single_calculation_line()
            self.update_frame()
            return

        self._previous_drag_mouse = [event.x, event.y]
        click_x = self._main_canvas.winfo_pointerx() - self._main_canvas.winfo_rootx()
        click_y = self._main_canvas.winfo_pointery() - self._main_canvas.winfo_rooty()
        self._prop_canvas.delete('all')
        stop = False
        self._active_line = ''
        self._line_is_active = False

        if len(self._line_dict) > 0:
            # Fast hit testing: distance from click point to each canvas line segment.
            # The old implementation walked every pixel along every line, which becomes
            # noticeably slow for long members and many lines.
            tolerance = 10.0
            closest_line = None
            closest_distance = float('inf')

            for key, value in self._line_dict.items():
                coord1 = self.get_point_canvas_coord('point' + str(value[0]))
                coord2 = self.get_point_canvas_coord('point' + str(value[1]))
                coord1x, coord1y = coord1[0], coord1[1]
                coord2x, coord2y = coord2[0], coord2[1]

                dx = coord2x - coord1x
                dy = coord2y - coord1y
                seg_len_sq = dx * dx + dy * dy

                if seg_len_sq <= 0:
                    distance_to_line = math.hypot(click_x - coord1x, click_y - coord1y)
                else:
                    t = ((click_x - coord1x) * dx + (click_y - coord1y) * dy) / seg_len_sq
                    t = max(0.0, min(1.0, t))
                    proj_x = coord1x + t * dx
                    proj_y = coord1y + t * dy
                    distance_to_line = math.hypot(click_x - proj_x, click_y - proj_y)

                if distance_to_line <= tolerance and distance_to_line < closest_distance:
                    closest_distance = distance_to_line
                    closest_line = key

            if closest_line is not None:
                self._line_is_active = True
                self._active_line = closest_line
                self._new_delete_line.set(get_num(closest_line))

        if self._line_is_active and self._active_line not in self._line_to_struc.keys():
            p1 = self._point_dict['point' + str(self._line_dict[self._active_line][0])]
            p2 = self._point_dict['point' + str(self._line_dict[self._active_line][1])]
            self._new_field_len.set(dist(p1, p2) * 1000)

        if self._toggle_btn.config('relief')[-1] == 'sunken':
            if self._active_line not in self._multiselect_lines:
                self._multiselect_lines.append(self._active_line)
        else:
            self._multiselect_lines = []

        if self._line_is_active and self._active_line in self._line_to_struc:
            self.set_selected_variables(self._active_line)
            self.cylinder_gui_mods()

        self.update_frame()
        self._combination_slider.set(1)
        if self._line_is_active:
            self._tabControl.select(self._tab_prop)

            try:
                self.gui_load_combinations(self._combination_slider.get())
            except (KeyError, AttributeError):
                pass

    def _sync_selected_cylinder_force_stress_entries(self):
        """Synchronize cylinder force entries from the selected cylinder stresses.

        Cylinder objects store the stress state in their main properties.  When a
        cylinder line is selected, both the stress entries and the force entries
        should represent that selected object.  This avoids stale force values
        from a previously selected cylinder being used/displayed when the GUI is
        currently in "Force input" mode.
        """
        if self._active_line not in self._line_to_struc:
            return
        struc_obj = self._line_to_struc[self._active_line][5]
        if struc_obj is None:
            return

        try:
            stresses = [
                self._new_shell_sasd.get(),
                self._new_shell_smsd.get(),
                abs(self._new_shell_tTsd.get()),
                self._new_shell_tQsd.get(),
                self._new_shell_shsd.get(),
            ]
            if struc_obj.geometry == 9:
                cone_r1 = self._new_shell_cone_r1.get()
                cone_r2 = self._new_shell_cone_r2.get()
                cone_length = self._new_shell_cone_length.get()
                cone_alpha = math.degrees(math.atan(abs(cone_r2 - cone_r1) / cone_length)) \
                    if cone_length else 0
                Nsd, M1sd, M2sd, Tsd, Q1sd, Q2sd = hlp.helper_cylinder_stress_to_force_to_stress(
                    stresses=stresses,
                    geometry=struc_obj.geometry,
                    shell_t=self._new_shell_thk.get(),
                    shell_radius=min(cone_r1, cone_r2),
                    shell_spacing=cone_length,
                    hw=self._new_stf_web_h.get(),
                    tw=self._new_stf_web_t.get(),
                    b=self._new_stf_fl_w.get(),
                    tf=self._new_stf_fl_t.get(),
                    CylinderAndCurvedPlate=CylinderAndCurvedPlate,
                    conical=True,
                    psd=self._new_shell_psd.get(),
                    cone_r1=cone_r1,
                    cone_r2=cone_r2,
                    cone_alpha=cone_alpha,
                    shell_lenght_l=cone_length,
                )[:6]
                self._new_shell_Nsd.set(_round_calculated(Nsd))
                self._new_shell_Msd.set(_round_calculated(M1sd))
                self._new_shell_M2sd.set(_round_calculated(M2sd))
                self._new_shell_Tsd.set(_round_calculated(Tsd))
                self._new_shell_Qsd.set(_round_calculated(Q1sd))
                self._new_shell_Q2sd.set(_round_calculated(Q2sd))
                return

            Nsd, Msd, Tsd, Qsd, _ = hlp.helper_cylinder_stress_to_force_to_stress(
                stresses=stresses,
                geometry=struc_obj.geometry,
                shell_t=self._new_shell_thk.get(),
                shell_radius=self._new_shell_radius.get(),
                shell_spacing=self._new_stf_spacing.get(),
                hw=self._new_stf_web_h.get(),
                tw=self._new_stf_web_t.get(),
                b=self._new_stf_fl_w.get(),
                tf=self._new_stf_fl_t.get(),
                CylinderAndCurvedPlate=CylinderAndCurvedPlate,
            )
            self._new_shell_Nsd.set(_round_calculated(Nsd))
            self._new_shell_Msd.set(_round_calculated(Msd))
            self._new_shell_Tsd.set(_round_calculated(Tsd))
            self._new_shell_Qsd.set(_round_calculated(Qsd))
        except Exception:
            # Keep selection robust.  If a partially defined cylinder cannot be
            # converted, the stored stress values are still shown correctly.
            pass

    def cylinder_gui_mods(self):
        if self._active_line in self._line_to_struc.keys():

            if self._line_to_struc[self._active_line][5] is not None:
                self._new_calculation_domain.set(
                    api_helpers.domain_for_geometry_id(self._line_to_struc[self._active_line][5].geometry))
                self._new_shell_exclude_ring_stf.set(self._line_to_struc[self._active_line][5]._ring_stiffener_excluded)
                self._new_shell_exclude_ring_frame.set(self._line_to_struc[self._active_line][5]._ring_frame_excluded)
                self.calculation_domain_selected(sync_cylinder_inputs=False)
                self.set_selected_variables(self._active_line)
                self._sync_selected_cylinder_force_stress_entries()
                # Setting the correct optmization buttons
                # 'Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder'
                for dom in ['Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder']:
                    for btn, placement in zip(self._optimization_buttons[dom],
                                              self._optimization_buttons[dom + ' place']):
                        btn.place_forget()
                for btn, placement in zip(self._optimization_buttons['cylinder'],
                                          self._optimization_buttons['cylinder place']):
                    if self._gui_functional_look == 'cylinder':
                        placement = self._gui_functional_look_cylinder_opt
                    btn.place(relx=placement[0], rely=placement[1], relheight=placement[2], relwidth=placement[3])

            else:
                self._new_calculation_domain.set(self._line_to_struc[self._active_line][0].calculation_domain)
                self.calculation_domain_selected()
                dom = self._line_to_struc[self._active_line][0].calculation_domain
                for btn, placement in zip(self._optimization_buttons['cylinder'],
                                          self._optimization_buttons['cylinder place']):
                    btn.place_forget()

                for btn, placement in zip(self._optimization_buttons[dom],
                                          self._optimization_buttons[dom + ' place']):
                    btn.place(relx=placement[0], rely=placement[1], relheight=placement[2], relwidth=placement[3])

    def button_1_click_comp_box(self, event):
        '''
        Action when clicking the compartment box.
        :param event:
        :return:
        '''
        self._selected_tank.config(text='')
        self._tank_acc_label.config(text='Accelerations [m/s^2]: ', font=self._text_size['Text 8 bold'])

        if len(self._tank_dict) != 0:
            current_comp = self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
            self._selected_tank.config(text=str(self._compartments_listbox.get('active')))

            self._new_density.set(self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
                                  .get_density())
            self._new_overpresure.set(self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
                                      .get_overpressure())
            self._new_content_type.set(self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
                                       .get_content())
            self._new_max_el.set(self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
                                 .get_highest_elevation())
            self._new_min_el.set(self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
                                 .get_lowest_elevation())
            acc = (self._tank_dict['comp' + str(self._compartments_listbox.get('active'))].get_accelerations())
            self._tank_acc_label.config(text='Accelerations [m/s^2]: \n'
                                             + 'static: ' + str(acc[0]) + ' , '
                                             + 'dynamic loaded: ' + str(acc[1]) + ' , '
                                             + 'dynamic ballast: ' + str(acc[2]), font=self._text_size['Text 8 bold'])

    def button_3_click(self, event=None):
        '''
        Identifies enclosed compartments in the canvas.
        :return:
        '''

        click_x = self._main_canvas.winfo_pointerx() - self._main_canvas.winfo_rootx()
        click_y = self._main_canvas.winfo_pointery() - self._main_canvas.winfo_rooty()
        self._pt_frame.place_forget()
        self._point_is_active = False
        margin = 10
        self._active_point = ''
        for point, coords in self._point_dict.items():
            point_coord = self.get_point_canvas_coord(point)
            if point_coord[0] - margin < click_x < point_coord[0] + margin and \
                    point_coord[1] - margin < click_y < point_coord[1] + margin:
                self._active_point = point
                self._point_is_active = True
                self._new_delete_point.set(get_num(point))
                if not self._p1_p2_select:
                    self._new_line_p1.set(get_num(point))
                    self._p1_p2_select = True
                else:
                    self._new_line_p2.set(get_num(point))
                    self._p1_p2_select = False
                self._new_point_x.set(round(self._point_dict[self._active_point][0] * 1000, 1))
                self._new_point_y.set(round(self._point_dict[self._active_point][1] * 1000, 1))
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            if len(self._multiselect_lines) != 0:
                self._multiselect_lines.pop(-1)

        self.update_frame()

    def draw_point_frame(self):
        ''' Frame to define brackets on selected point. '''
        pt_canvas = tk.Canvas(self._pt_frame, height=100, width=100,
                              background=self._style.lookup('TFrame', 'background'))
        pt_canvas.place(relx=0, rely=0)
        pt_canvas.create_oval(45, 45, 55, 55, fill='red')
        new_left_br = tk.IntVar()
        new_right_br = tk.IntVar()
        new_upper_br = tk.IntVar()
        new_lower_br = tk.IntVar()
        wid = 5
        ent_left = ttk.Entry(self._pt_frame, textvariable=new_left_br, width=wid,
                             )
        ent_right = ttk.Entry(self._pt_frame, textvariable=new_right_br, width=wid,
                              )
        ent_upper = ttk.Entry(self._pt_frame, textvariable=new_upper_br, width=wid,
                              )
        ent_lower = ttk.Entry(self._pt_frame, textvariable=new_lower_br, width=wid,
                              )
        ent_lower.place(relx=0.018229167, rely=0.009259259)
        ent_upper.place(relx=0.018229167, rely=0.069444444)
        ent_left.place(relx=0.002604167, rely=0.037037037)
        ent_right.place(relx=0.03125, rely=0.037037037)

    def save_no_dialogue(self, event=None, backup=False):
        if backup:
            target = project_application.ProjectFileDialogService.backup_save_target(self._root_dir)
            self.savefile(filename=target.path, backup=backup)
            return

        target = project_application.ProjectFileDialogService.remembered_save_target(self.__last_save_file)
        if target is None:
            tk.messagebox.showerror('Save error', 'No saves in this session yet.')
            return
        self.savefile(filename=target.path)

    def savefile(self, filename=None, backup=False):
        '''
        Saving to a file using JSON formatting.
        '''

        if filename is None:
            filename = filedialog.asksaveasfilename(defaultextension=".txt")
            if not filename:
                return
        save_target = project_application.ProjectFileDialogService.selected_save_target(filename, backup=backup)
        if save_target.remember_as_last_save:
            self.__last_save_file = str(save_target.path)

        try:
            save_result = project_application.ProjectSaveService.save_path(
                save_target.path,
                self._build_project_save_input(),
            )
        except project_application.ProjectPersistenceError as error:
            tk.messagebox.showerror('Save error', str(error))
            return

        if not backup:
            self._parent.wm_title('| ANYstructure |     ' + str(save_result.path))
        # self.update_frame()

    def _build_project_save_input(self):
        load_combinations = [
            project_application.LoadCombinationRecord(name, data[0].get(), data[1].get(), data[2].get())
            for name, data in self._new_load_comb_dict.items()
        ]
        return project_application.ProjectSaveInput(
            project_information=self._project_information.get('1.0', tk.END),
            theme=self._current_theme,
            points=self._point_dict,
            lines=self._line_dict,
            line_bundles=self._line_to_struc,
            load_assignments=self._load_dict,
            accelerations=self._accelerations_dict,
            load_combinations=load_combinations,
            tanks=self._tank_dict,
            tank_grid=self._main_grid.export_grid(),
            tank_search_data=self._main_grid.bfs_search_data,
            buckling_method=self._new_buckling_method.get(),
            shifting={'shifted checked': self._new_shifted_coords.get(),
                      'shift hor': self._new_shift_viz_coord_hor.get(),
                      'shift ver': self._new_shift_viz_coord_ver.get()},
            weight_and_cog=self._weight_logger,
        )

    def _build_project_hydration_defaults(self):
        return project_application.ProjectHydrationDefaults(
            structure_types=self._structure_types,
            zstar_optimization=self._new_zstar_optimization.get(),
            puls_buckling_method=self._new_puls_method.get(),
            puls_boundary=self._new_puls_panel_boundary.get(),
            puls_stiffener_end=self._new_buckling_stf_end_support.get(),
            puls_sp_or_up=self._new_puls_sp_or_up.get(),
            puls_up_boundary=self._new_puls_up_boundary.get(),
            material_factor=self._new_material_factor.get(),
        )

    def _apply_open_project_text_and_theme(self, open_transfer):
        self._project_information.delete("1.0", tk.END)
        if open_transfer.project_information:
            self._project_information.insert(1.0, open_transfer.project_information)
        else:
            self._project_information.insert(1.0, 'No information on project provided. Input here.')

        if open_transfer.shifting:
            self._new_shifted_coords.set(open_transfer.shifting.get('shifted checked', False))
            self._new_shift_viz_coord_hor.set(open_transfer.shifting.get('shift hor', 0))
            self._new_shift_viz_coord_ver.set(open_transfer.shifting.get('shift ver', 0))

        self.set_colors(open_transfer.theme)

    def _apply_open_project_geometry_and_objects(self, open_transfer, hydration):
        self._point_dict = open_transfer.points
        self._line_dict = open_transfer.lines
        self._line_to_struc = hydration.line_bundles
        self._load_dict = hydration.load_assignments

        for line in self._line_to_struc:
            self._line_point_to_point_string.append(
                self.make_point_point_line_string(self._line_dict[line][0], self._line_dict[line][1])[0])
            self._line_point_to_point_string.append(
                self.make_point_point_line_string(self._line_dict[line][0], self._line_dict[line][1])[1])
        for section_properties in hydration.section_properties:
            self._sections = add_new_section(self._sections, struc.Section(section_properties))

    def _apply_open_project_accelerations(self, open_transfer):
        self._accelerations_dict = open_transfer.accelerations
        self._new_static_acc.set(self._accelerations_dict['static'])
        self._new_dyn_acc_loaded.set(self._accelerations_dict['dyn_loaded'])
        self._new_dyn_acc_ballast.set(self._accelerations_dict['dyn_ballast'])

    def _apply_open_project_load_combinations(self, open_transfer):
        for load_combination in open_transfer.load_combinations:
            name = load_combination.name
            if load_combination.has_include:
                self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
                self._new_load_comb_dict[name][0].set(load_combination.static_factor)
                self._new_load_comb_dict[name][1].set(load_combination.dynamic_factor)
                self._new_load_comb_dict[name][2].set(load_combination.include)
            else:
                self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.IntVar()]
                self._new_load_comb_dict[name][0].set(load_combination.static_factor)
                self._new_load_comb_dict[name][1].set(load_combination.dynamic_factor)

    def _apply_open_project_tanks(self, open_transfer):
        try:
            self._main_grid.import_grid(open_transfer.tank_grid)
            self._grid_calc = grid_window.CreateGridWindow(self._main_grid, self._canvas_dim,
                                                           self._pending_grid_draw, self._canvas_base_origo)

            self._main_grid.bfs_search_data = open_transfer.tank_search_data
            self._grid_calc.bfs_search_data = open_transfer.tank_search_data

            for comp_no in range(2, int(self._main_grid.get_highest_number_in_grid()) + 1):
                self._compartments_listbox.insert('end', comp_no)
                tank_name = 'comp' + str(comp_no)
                self._tank_dict[tank_name] = Tanks(open_transfer.tank_properties[tank_name])
        except IndexError:
            for line_name, point_no in self._line_dict.items():
                point_coord_x = self._canvas_base_origo[0] + self._point_dict[point_no][0] * self._canvas_scale
                point_coord_y = self._canvas_base_origo[1] - self._point_dict[point_no][1] * self._canvas_scale

                self.grid_operations(line_name, [point_coord_x, point_coord_y])

    def _apply_open_project_canvas_scale(self):
        points = self._point_dict
        if len(points) != 0:
            highest_y = max([coord[1] for coord in points.values()])
            highest_x = max([coord[0] for coord in points.values()])
        else:
            highest_x = 1
            highest_y = 1
        if not any([highest_x == 0, highest_y == 0]):
            self._canvas_scale = min(800 / highest_y, 800 / highest_x, 15)

    def _finalize_open_project(self, open_transfer, filename):
        self._new_buckling_method.set(open_transfer.buckling_method)
        self._weight_logger = open_transfer.weight_and_cog
        if getattr(self, '_simplified_calculation_mode', False):
            self._ensure_single_dummy_line()
            self._select_single_calculation_line()
            self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)
            self._apply_simplified_calculation_layout()
            self._new_show_prop_3d.set(True)
        self.get_cob()
        self._parent.wm_title('| ANYstructure |     ' + str(filename))
        self.update_frame()

    def openfile(self, defined=None, alone=False):
        '''
        Opens a file with data (JSON).
        '''

        if defined == None:
            target = project_application.ProjectFileDialogService.selected_open_target(
                filedialog.askopenfilename(defaultextension=".txt")
            )
        else:
            target = project_application.ProjectFileDialogService.selected_open_target(defined)
        if target is None:
            return

        try:
            opened_project = project_application.ProjectOpenService.open_path(
                target.path,
                self._build_project_hydration_defaults(),
            )
        except project_application.ProjectPersistenceError as error:
            tk.messagebox.showerror('Open error', str(error))
            return

        open_transfer = opened_project.transfer
        hydration = opened_project.hydration

        self.reset(activate_simplified=False)
        self._apply_open_project_text_and_theme(open_transfer)
        self._apply_open_project_geometry_and_objects(open_transfer, hydration)
        self._apply_open_project_accelerations(open_transfer)
        self._apply_open_project_load_combinations(open_transfer)
        self._apply_open_project_tanks(open_transfer)
        self._apply_open_project_canvas_scale()
        self._finalize_open_project(open_transfer, target.path)

    def restore_previous(self):
        target = project_application.ProjectFileDialogService.restore_target(self._root_dir)
        if target is not None:
            self.openfile(defined=target.path)

    def open_example(self, file_name='ship_section_example.txt'):
        ''' Open the example file. To be used in help menu. '''
        target = project_application.ProjectFileDialogService.example_open_target(file_name, self._root_dir)
        self.openfile(defined=target.path)

    def open_example_excel_file(self):
        file_name = 'excel_input_example.xlsx'
        target = project_application.ProjectFileDialogService.example_open_target(file_name, self._root_dir)
        project_services.ExcelProjectImportService.open_example_path(target.path)

    def _sync_excel_import_geometry(self, geometry_import):
        for point in geometry_import.created_points:
            self._active_point = point.name
            self.logger(point=point.name, move_coords=None)

        for imported_line in geometry_import.imported_lines:
            self._line_point_to_point_string.extend(imported_line.line.endpoint_keys)
            self.add_to_combinations_dict(imported_line.line.name)
            self.logger(line=[imported_line.line.name, None])

    def open_excel_file(self):
        ''' Open an excel file with data to read into ANYstructure '''

        target = project_application.ProjectFileDialogService.selected_open_target(
            filedialog.askopenfilename(defaultextension=".xlsx")
        )
        if target is None:
            return

        import_data = project_services.ExcelProjectImportService.read_path(target.path)
        flat_plate_records = import_data.flat_plate_records
        cylinder_records = import_data.cylinder_records

        flat_geometry = project_services.ExcelProjectGeometryImportService.add_records(
            self._point_dict,
            self._line_dict,
            flat_plate_records,
        )
        cylinder_geometry = project_services.ExcelProjectGeometryImportService.add_records(
            self._point_dict,
            self._line_dict,
            cylinder_records,
        )
        self._sync_excel_import_geometry(flat_geometry)
        self._sync_excel_import_geometry(cylinder_geometry)
        self.update_frame()

        # Flat
        # --------------------------------------------------------------------------------------------------------------
        for imported_line in flat_geometry.imported_lines:
            import_record = imported_line.record
            this_line = imported_line.line.name
            l1x, l1y = import_record.first_point
            l2x, l2y = import_record.second_point
            self._active_line = this_line
            self._line_is_active = True
            self._new_calculation_domain.set(import_record.calculation_domain)
            flat_request, overpressure = self._build_flat_structure_property_request_from_excel_record(
                import_record,
                hlp.dist((l1x, l1y), (l2x, l2y)),
            )
            if overpressure is not None:
                self._new_overpresure.set(overpressure)
            self.new_structure(
                toggle_multi=project_services.FlatStructurePropertyService.build(flat_request)
            )
            self._new_load_comb_dict[('manual', this_line, 'manual')][0].set(import_record.manual_pressure)
            self._new_load_comb_dict[('manual', this_line, 'manual')][1].set(1)
            self._new_load_comb_dict[('manual', this_line, 'manual')][2].set(1)
            self._line_to_struc[this_line][0].need_recalc = True

        # Cylinders
        # ------------------------------------------------------------------------------------------------------------
        for imported_line in cylinder_geometry.imported_lines:
            import_record = imported_line.record
            this_line = imported_line.line.name
            self._active_line = this_line
            self._line_is_active = True
            self._new_calculation_domain.set(import_record.calculation_domain)
            cylinder_request = project_services.CylinderExcelImportPropertyService.build_request(
                import_record,
                self._build_cylinder_excel_import_defaults(),
            )
            cylinder_result = project_services.CylinderStructurePropertyService.build(cylinder_request)
            cylinder_obj = self._create_cylinder_structure_from_property_result(cylinder_result)
            flat_request = self._build_flat_structure_property_request_from_cylinder_excel_record(import_record)
            self.new_structure(
                toggle_multi=project_services.FlatStructurePropertyService.build(flat_request),
                cylinder_return=cylinder_obj,
            )

    def button_load_info_click(self, event=None):
        ''' Get the load information for one line.'''
        if self._active_line != '' and self._active_line in self._line_to_struc.keys():
            load_text = self.calculate_all_load_combinations_for_line(self._active_line, get_load_info=True)
            text_to_frame = 'Load results for ' + self._active_line + '\n' + '\n'
            for item in load_text:
                text_to_frame += item

            text_m = tk.Toplevel(self._parent, background=self._general_color)
            # Create the text widget
            text_widget = tk.Text(text_m, height=60, width=80)
            # Create a scrollbar
            scroll_bar = ttk.Scrollbar(text_m)
            # Pack the scroll bar
            # Place it to the right side, using tk.RIGHT
            scroll_bar.pack(side=tk.RIGHT)
            # Pack it into our tkinter application
            # Place the text widget to the left side
            text_widget.pack(side=tk.LEFT)
            # Insert text into the text widget
            text_widget.insert(tk.END, text_to_frame)
            # tk.messagebox.showinfo('Load info for '+self._active_line, ''.join(load_text))
        else:
            tk.messagebox.showerror('No data', 'No load data for this line')

    def on_plot_cog_dev(self):
        '''
        Plot the COG and COB development.
        '''
        if self._weight_logger['new structure']['time'] == []:
            tk.messagebox.showinfo('New functionality ver. 3.3', 'If you are using an existing model,'
                                                                 ' weights have not been'
                                                                 ' recorded in previous versions.\n'
                                                                 'Press "Add structure properties to line....." button to add a '
                                                                 'blank datapoint.\n'
                                                                 'Other data will then be available.\n\n'
                                                                 'If you are making a new model add some structure properties.')
            return
        import matplotlib.dates as mdate

        cog = np.array(self._weight_logger['new structure']['COG'])
        weight = np.array(self._weight_logger['new structure']['weight']) / \
                 max(self._weight_logger['new structure']['weight'])
        time_stamp = np.array(self._weight_logger['new structure']['time'])
        time_stamp = [mdate.date2num(val) for val in time_stamp]
        structure = self.get_unique_plates_and_beams()

        hlp.plot_weights(time_stamp=time_stamp, cog=cog, structure=structure, weight=weight)

    def on_open_structure_window(self, clicked_button=None):
        '''
        Opens the window to create structure.
        :return:
        '''
        self._clicked_section_create = clicked_button  # Identifying the clicked button

        top_opt = tk.Toplevel(self._parent, background=self._general_color)
        struc.CreateStructureWindow(top_opt, self)

    def on_open_stresses_window(self):
        '''
        User can open a new window to stresses
        :return:
        '''

        if self._line_is_active:

            top_opt = tk.Toplevel(self._parent, background=self._general_color)
            stress.CreateStressesWindow(top_opt, self)

        else:
            messagebox.showinfo(title='Select line', message='You must select a line')

    def on_open_fatigue_window(self):
        '''
        User can open a new window to stresses
        :return:
        '''

        if self._line_is_active:
            try:
                self._line_to_struc[self._active_line]

            except KeyError:
                messagebox.showinfo(title='Select line', message='Fatigue properties are defined here.\n'
                                                                 'Strucure must be added to line before setting\n'
                                                                 'these properties ("Add structure to line"-button).')
                return
            top_opt = tk.Toplevel(self._parent, background=self._general_color)
            fatigue.CreateFatigueWindow(top_opt, self)



        else:
            messagebox.showinfo(title='Select line', message='You must select a line')

    def on_open_load_factor_window(self):
        '''
        Set the default load factors and change all.
        :return:
        '''
        lf_tkinter = tk.Toplevel(self._parent, background=self._general_color)
        load_factors.CreateLoadFactorWindow(lf_tkinter, self)

    def on_show_loads(self):
        '''
        User can open a new window to specify loads
        :return:
        '''

        try:
            img_file_name = 'img_ext_pressure_button_def.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._ext_button.config(image=photo)
            self._ext_button.image = photo
        except TclError:
            pass
        self.__previous_load_data = copy.deepcopy(self._load_dict)
        top = tk.Toplevel(self._parent, background=self._general_color)
        load_window.CreateLoadWindow(top, self)

    def _apply_material_spec(self, spec):
        """Apply an ANYmaterial specification to the legacy scalar inputs."""
        try:
            selected = ecosystem_gui.isotropic_material_selection(spec)
        except ecosystem_gui.UnsupportedMaterialSelection as error:
            self._new_material_name.set(self._last_isotropic_material_name)
            messagebox.showerror(title='Unsupported material', message=str(error), parent=self._parent)
            return False

        self._new_material_name.set(selected.name)
        self._last_isotropic_material_name = selected.name
        self._new_material.set(selected.yield_stress_mpa)
        self._new_shell_yield.set(selected.yield_stress_mpa)
        self._new_shell_e_module.set(selected.elastic_modulus_gpa * 1.0e9)
        self._new_shell_poisson.set(selected.poisson_ratio)
        return True

    def _on_material_library_selected(self, event=None):
        """Load the material chosen in the shared library dropdown."""
        try:
            spec = ecosystem_gui.material_spec_from_library(self._new_material_name.get())
        except (KeyError, ValueError) as error:
            self._new_material_name.set(self._last_isotropic_material_name)
            messagebox.showerror(title='Material library', message=str(error), parent=self._parent)
            return False
        return self._apply_material_spec(spec)

    def on_open_material_editor(self):
        """Open ANYmaterial in this application's Tk event loop."""
        try:
            initial_spec = ecosystem_gui.material_spec_from_library(self._new_material_name.get())
        except (KeyError, ValueError):
            initial_spec = None
        return ecosystem_gui.open_material_editor(
            self._parent,
            initial_spec=initial_spec,
            on_apply=self._apply_material_spec,
        )

    def on_open_mesher(self):
        """Open the standalone neutral-mesh editor without a nested mainloop."""
        return ecosystem_gui.open_mesher(self._parent)

    def on_open_file_inspector(self):
        """Open the structural interchange-file inspector."""
        return ecosystem_gui.open_file_inspector(self._parent)

    def on_open_runtime_fem_solver(self):
        """Open the runtime FEM solver for the current active line."""
        if getattr(self, '_fea_buckling_mode', False):
            messagebox.showinfo(
                title='Experimental FEM solver',
                message='Runtime FEM uses active ANYstructure lines, not imported FEA result panels.',
            )
            return
        if not self._line_is_active or self._active_line not in self._line_to_struc:
            messagebox.showinfo(title='Select line', message='Select a line with structure properties before FEM run.')
            return
        fe_runtime_solver.open_runtime_fem_window(self._parent, self)

    def on_optimize(self):
        '''
        User open window to optimize current structure
        :return:
        '''

        # if [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()] == []:
        #     # messagebox.showinfo(title='Missing something', message='Missing properties/loads etc.')
        #     # return

        try:
            self.get_highest_pressure(self._active_line)['normal']
        except (KeyError, AttributeError):
            messagebox.showinfo(title='Missing loads/accelerations',
                                message='Select line or make some loads for the line.\n' +
                                        'Define accelerations for compartments.')
            return

        if self._line_is_active:
            if self._active_line not in self._line_to_struc:
                messagebox.showinfo(title='Missing properties', message='Specify properties for line')
            elif self._line_to_struc[self._active_line][3] == None:
                messagebox.showinfo(title='Missing loads', message='Make some loads for the line')
            else:
                top_opt = tk.Toplevel(self._parent, background=self._general_color)
                opw.CreateOptimizeWindow(top_opt, self)
        else:
            messagebox.showinfo(title='Select line', message='You must select a line')

    def on_optimize_cylinder(self):
        '''
        User open window to optimize current structure
        :return:
        '''

        # if [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()] == []:
        #     # messagebox.showinfo(title='Missing something', message='Missing properties/loads etc.')
        #     # return

        if self._line_is_active:
            if self._active_line not in self._line_to_struc:
                messagebox.showinfo(title='Missing properties', message='Specify properties for line')
            elif self._line_to_struc[self._active_line][5] == None:
                messagebox.showinfo(title='Missing cylinder', message='Make a shell or panel')
            else:
                top_opt = tk.Toplevel(self._parent, background=self._general_color)
                opc.CreateOptimizeCylinderWindow(top_opt, self)
        else:
            messagebox.showinfo(title='Select line', message='You must select a line')

    def on_optimize_multiple(self):
        '''
        Used to optimize in batch mode.
        :return:
        '''
        if [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()] == []:
            messagebox.showinfo(title='Missing something', message='Make something')
            return

        try:
            [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()]
        except KeyError:
            messagebox.showinfo(title='Missing loads', message='The MultiOpt requires that loads have been defined.\n')
            return

        messagebox.showinfo(title='Multiple optimization information',
                            message='Opening this window enables batch optimization.\n'
                                    'There are less input and information. It is HIGHLY\n'
                                    'recommended to single optimize first (optimize button).\n'
                                    'This way you will understand how the optimizer works.\n'
                                    '\n'
                                    'A default range of T properties is chosen. Typical analysis\n'
                                    'steps (deltas) is chosen.')

        top_opt = tk.Toplevel(self._parent, background=self._general_color)
        opwmult.CreateOptimizeMultipleWindow(top_opt, self)

    def on_geometry_optimize(self):
        '''

        :param returned_objects:
        :return:
        '''

        if [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()] == []:
            messagebox.showinfo(title='Missing something', message='Make something')
            return

        try:
            [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()]
        except KeyError:
            messagebox.showinfo(title='Missing loads', message='The SpanOpt requires that loads have been defined.\n')
            return

        messagebox.showinfo(title='Span optimization module', message=
        'Computationally heavy! Will run for a long time.\n'
        'It is HIGHLY recommended to run predefined stiffeners. \n\n'
        'WEIGHT INDEX is the most important result.\n'
        'Results are presented for information and can not be returned to main model.\n'
        'Weight index will show you the span length that will give the lowest weight.\n'
        '\n'
        'A default range of T properties is chosen. Typical analysis\n'
        'steps (deltas) is chosen.\n'
        'Loads are taken from existing structure.')

        top_opt = tk.Toplevel(self._parent, background=self._general_color)
        optgeo.CreateOptGeoWindow(top_opt, self)

    def on_close_load_window(self, returned_loads, counter, load_comb_dict):
        '''
        Setting properties created in load window.
        :return:
        '''
        self.save_no_dialogue(backup=True)  # keeping a backup

        try:
            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._ext_button.config(image=photo)
            self._ext_button.image = photo
        except TclError:
            pass
        self._load_window_couter = counter
        self._new_load_comb_dict = load_comb_dict
        temp_load = self.__previous_load_data
        if len(returned_loads) != 0:
            for load, data in returned_loads.items():
                # creating the loads objects dictionary
                self._load_dict[load] = data

            project_services.LineLoadService(self._line_to_struc).rebuild_line_loads(
                self._line_dict.keys(), self._load_dict, temp_load)

        # Storing the the returned data to temporary variable.
        self.__returned_load_data = [returned_loads, counter, load_comb_dict]

        # Calculating center of buoyancy from static cases.
        if self._grid_calc is not None:
            self.get_cob()  # Update COB
        self.update_frame()

    def on_close_opt_window(self, returned_object):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''
        self.save_no_dialogue(backup=True)  # keeping a backup

        simplified_replacement = self._prepare_simplified_optimizer_replacement()
        if simplified_replacement:
            self._replace_active_line_with_optimized_structure(returned_object[0])
        else:
            self.new_structure(multi_return=returned_object[0:2])
        # self._line_to_struc[self._active_line][1]=returned_objects[0]
        # self._line_to_struc[self._active_line][1]=returned_objects[1]
        # self._line_to_struc[self._active_line][0].need_recalc = True
        # self.set_selected_variables(self._active_line)
        # if returned_objects[2] is not None:
        #     self._line_to_struc[self._active_line][2] = CalcFatigue(returned_objects[0].get_structure_prop(),
        #                                                             returned_objects[2])
        # self.new_structure()
        if not self._refresh_simplified_optimizer_replacement():
            self.update_frame()

    def on_close_opt_cyl_window(self, returned_object):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''

        self._prepare_simplified_optimizer_replacement()
        self.new_structure(cylinder_return=returned_object[0])

        if not self._refresh_simplified_optimizer_replacement():
            self.update_frame()

    def on_close_opt_multiple_window(self, returned_objects):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''
        self.save_no_dialogue(backup=True)  # keeping a backup
        for line, all_objs in returned_objects.items():
            self._active_line = line
            # self._line_to_struc[line][0].need_recalc = True
            self.new_structure(multi_return=all_objs[0:2])
        self.update_frame()

    def on_close_structure_window(self, returned_structure):
        '''
        Setting the input field to specified properties
        :param returned_structure:
        :return:


                self._shell_ring_stf_gui_items = [self._lab_shell_ring_stiffener,self._ent_shell_ring_stf_hw,
                                          self._ent_shell_ring_stf_tw,self._ent_shell_ring_stf_b,
                                          self._ent_shell_ring_stf_tf, self._ent_shell_ring_stf_tripping_brackets,
                                          self._ent_shell_ring_stf_type, self._chk_shell_ring_frame_exclude,
                                          self._btn_shell_stf_section_ring_stf]
        '''
        clicked_button = returned_structure[
            7]  # ["long stf", "ring stf", "ring frame", "flat long stf", 'flat stf', 'flat girder']

        if clicked_button in ["long stf", "flat long stf", 'flat stf']:
            self._new_stf_spacing.set(returned_structure[0])
            self._new_plate_thk.set(returned_structure[1])
            self._new_stf_web_h.set(returned_structure[2])
            self._new_stf_web_t.set(returned_structure[3])
            self._new_stf_fl_w.set(returned_structure[4])
            self._new_stf_fl_t.set(returned_structure[5])
            self._new_stf_type.set(returned_structure[6])
        elif clicked_button == 'flat girder':
            self._new_girder_web_h.set(returned_structure[2])
            self._new_girder_web_t.set(returned_structure[3])
            self._new_girder_fl_w.set(returned_structure[4])
            self._new_girder_fl_t.set(returned_structure[5])
            self._new_girder_type.set(returned_structure[6])
        elif clicked_button == "ring stf":
            self._new_shell_ring_stf_hw.set(returned_structure[2])
            self._new_shell_ring_stf_tw.set(returned_structure[3])
            self._new_shell_ring_stf_b.set(returned_structure[4])
            self._new_shell_ring_stf_tf.set(returned_structure[5])
        elif clicked_button == "ring frame":
            self._new_shell_ring_frame_hw.set(returned_structure[2])
            self._new_shell_ring_frame_tw.set(returned_structure[3])
            self._new_shell_ring_frame_b.set(returned_structure[4])
            self._new_shell_ring_frame_tf.set(returned_structure[5])

        section = struc.Section({'stf_type': returned_structure[6],
                                 'stf_web_height': returned_structure[2] / 1000,
                                 'stf_web_thk': returned_structure[3] / 1000,
                                 'stf_flange_width': returned_structure[4] / 1000,
                                 'stf_flange_thk': returned_structure[5] / 1000})

        self._sections = add_new_section(self._sections, section)

    def on_close_stresses_window(self, returned_stress_and_km):
        '''
        Sets the returned transverse/axial/shear stresses (global estimated values).
        Sets the km1,km2,km3 paramter.
        :param returned_stress_and_km:
        :return:
        '''
        self._new_sigma_y1.set(_round_calculated(returned_stress_and_km[0]))
        self._new_sigma_y2.set(_round_calculated(returned_stress_and_km[1]))
        self._new_sigma_x1.set(_round_calculated(returned_stress_and_km[2]))
        self._new_sigma_x2.set(_round_calculated(returned_stress_and_km[3]))
        self._new_tauxy.set(_round_calculated(returned_stress_and_km[4]))
        self._new_stf_km1.set(returned_stress_and_km[5])
        self._new_stf_km2.set(returned_stress_and_km[6])
        self._new_stf_km3.set(returned_stress_and_km[7])
        self._new_plate_kpp.set(returned_stress_and_km[8])
        self._new_stf_kps.set(returned_stress_and_km[9])
        self._new_stucture_type.set(returned_stress_and_km[10], )

    def on_close_fatigue_window(self, returned_fatigue_prop: dict):
        '''
        Sets the returned fatigue properteis.
        :param returned_stress_and_km:
        :return:
        '''
        if self._line_to_struc[self._active_line][2] == None:
            self._line_to_struc[self._active_line][2] = CalcFatigue(self._line_to_struc[self._active_line][0].Plate
                                                                    .get_structure_prop(),
                                                                    returned_fatigue_prop)
        else:
            self._line_to_struc[self._active_line][2].set_fatigue_properties(returned_fatigue_prop)

        self._line_to_struc[self._active_line][0].need_recalc = True
        if self.__returned_load_data is not None:
            map(self.on_close_load_window, self.__returned_load_data)

        # adding values to the line dictionary. resetting first.
        for key, value in self._line_to_struc.items():
            if self._line_to_struc[key][2] is not None:
                self._line_to_struc[key][2].set_commmon_properties(returned_fatigue_prop)
            self._line_to_struc[key][0].need_recalc = True  # All lines need recalculations.

        self.update_frame()

    def on_aborted_load_window(self):
        '''
        When it is aborted due to closing.
        :return:
        '''
        try:
            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._ext_button.config(image=photo)
            self._ext_button.image = photo
        except TclError:
            pass

    def on_close_load_factor_window(self, returned_load_factors):
        '''
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,0]} # DNV  loads factors
        self._new_load_comb_dict = {(dnv cond, line, load type) : (stat lf, dyn lf, include)}
        :param returned_load_factors: list [stat lf, dyn lf]
        :return:
        '''

        self._load_factors_dict = returned_load_factors['returned lf dict']

        for name, data in self._new_load_comb_dict.items():
            if name[0] == 'manual':
                continue
            if data[0].get() != 0:
                data[0].set(self._load_factors_dict[name[0]][1])
            if data[1].get() != 0:
                data[1].set(self._load_factors_dict[name[0]][2])

    def close_main_window(self):
        '''
        Save of not save when closing window.
        :return:
        '''

        mess = tk.messagebox.showwarning('Close main window', 'Save before closing?', type='yesnocancel')
        self.save_no_dialogue(backup=True)  # keeping a backup

        if mess == 'yes':
            self.savefile()
            self._parent.destroy()
        elif mess == 'no':
            self._parent.destroy()
        elif mess == 'cancel':
            pass

    def on_color_code_check(self, event=None):
        if [self._new_colorcode_beams.get(), self._new_colorcode_plates.get(),
            self._new_colorcode_pressure.get(), self._new_colorcode_utilization.get(),
            self._new_colorcode_sigmax.get(), self._new_colorcode_sigmay1.get(), self._new_colorcode_sigmay2.get(),
            self._new_colorcode_tauxy.get(), self._new_colorcode_structure_type.get(),
            self._new_colorcode_section_modulus.get(), self._new_colorcode_fatigue.get(),
            self._new_colorcode_total.get(), self._new_colorcode_puls_sp_or_up.get(),
            self._new_colorcode_puls_acceptance.get(), self._new_colorcode_spacing.get()].count(True) > 1:
            messagebox.showinfo(title='Information', message='Can only select on color code at the time.')
            self._new_colorcode_beams.set(False)
            self._new_colorcode_plates.set(False)
            self._new_colorcode_pressure.set(False)
            self._new_colorcode_utilization.set(False)
            self._new_colorcode_sigmax.set(False)
            self._new_colorcode_sigmay1.set(False)
            self._new_colorcode_sigmay2.set(False)
            self._new_colorcode_tauxy.set(False)
            self._new_colorcode_structure_type.set(False)
            self._new_colorcode_section_modulus.set(False)
            self._new_colorcode_fatigue.set(False)
            self._new_colorcode_total.set(False)
            self._new_colorcode_puls_acceptance.set(False)
            self._new_colorcode_puls_sp_or_up.set(False)
        self.update_frame()

    def logger(self, line=None, point=None, move_coords=None):
        ''' Log to be used for undo and redo. '''

        if line is not None:
            self._logger['added'].append([line[0], self._line_dict[line[0]]])
        elif point is not None and move_coords is None:
            self._logger['added'].append([point, None])
        elif point is not None and move_coords is not None:
            self._logger['added'].append([point, move_coords])
        else:
            pass

    def undo(self, event=None):
        ''' Method to undo and redo. '''
        if len(self._logger['added']) > 0:
            current = self._logger['added'].pop(-1)

            if 'point' in current[0] and current[1] is None:
                if current[0] not in self._logger['deleted']:
                    self._logger['deleted'].append(current)
                self.delete_point(undo=current[0])
            elif 'point' in current[0] and current[1] is not None:
                self.move_point(redo=current[1][0])
            elif 'line' in current[0]:
                if current[0] not in [line[0] for line in self._logger['deleted']]:
                    self._logger['deleted'].append(current)
                self.delete_line(undo=current[0])

    def redo(self, event=None):
        ''' Method to undo and redo. '''
        if len(self._logger['deleted']) > 0:
            current = self._logger['deleted'].pop(-1)
            if 'point' in current[0] and current[1] is None:
                self.new_point(redo=current[0])
            elif 'point' in current[0] and current[1] is not None:
                self.move_point(redo=current[1][1])
            elif 'line' in current[0]:
                self.new_line(redo=['point' + str(num) for num in current[1]])

    def open_documentation_pdf(self):
        ''' Open the documentation pdf. '''
        if os.path.isfile('ANYstructure_documentation.pdf'):
            os.startfile('ANYstructure_documentation.pdf')
        else:
            os.startfile(self._root_dir + '/' + 'ANYstructure_documentation.pdf')

    def open_documentation(self):
        ''' Open the documentation webpage. '''
        import webbrowser
        webbrowser.open('https://sites.google.com/view/anystructure/start', new=0, autoraise=True)

    def open_donate(self):
        ''' Open the documentation webpage. '''
        import webbrowser
        webbrowser.open('https://sites.google.com/view/anystructure/donate', new=0, autoraise=True)

    def open_about(self):
        '''
        Open a about messagebox.
        :return:
        '''
        messagebox.showinfo(title='Information', message='ANYstructure 6.x.x (Stable/Production)'
                                                         '\n'
                                                         '\n'
                                                         'By Audun Arnesen Nyhus \n'
                                                         '2026\n\n'
                                                         'All technical calculation based on \n'
                                                         'DNV RPs and standards')

    def export_to_js(self):
        '''
        Printing to a js file
        :return:
        '''
        target = project_application.ProjectFileDialogService.selected_output_target(
            filedialog.asksaveasfilename(defaultextension=".js")
        )
        if target is None:
            return
        project_services.SesamExportService.write_js_path(
            project_services.SesamExportRequest(
                points=self._point_dict,
                lines=self._line_dict,
                sections=self._sections,
                line_bundles=self._line_to_struc,
            ),
            target.path,
        )


if __name__ == '__main__':
    # multiprocessing.freeze_support()
    # errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    # root = tk.Tk()
    # root.tk.call("source", "sun-valley.tcl")
    # root.tk.call("set_theme", "dark")

    # style = ttk.Style(root)
    # root.tk.eval("""
    #     set dir C:/Users/cefany/Downloads/awthemes-10.4.0
    #
    #     package ifneeded awthemes 10.4.0 \
    #         [list source [file join $dir awthemes.tcl]]
    #     package ifneeded colorutils 4.8 \
    #         [list source [file join $dir colorutils.tcl]]
    #     package ifneeded awarc 1.6.1 \
    #         [list source [file join $dir awarc.tcl]]
    #     package ifneeded ttk::theme::awarc 1.6.1 \
    #         [list source [file join $dir awarc.tcl]]
    #     package ifneeded awblack 7.8.1 \
    #         [list source [file join $dir awblack.tcl]]
    #     package ifneeded ttk::theme::awblack 7.8.1 \
    #         [list source [file join $dir awblack.tcl]]
    #     package ifneeded awbreeze 1.9.1 \
    #         [list source [file join $dir awbreeze.tcl]]
    #     package ifneeded ttk::theme::awbreeze 1.9.1 \
    #         [list source [file join $dir awbreeze.tcl]]
    #     package ifneeded awbreezedark 1.0.1 \
    #         [list source [file join $dir awbreezedark.tcl]]
    #     package ifneeded ttk::theme::awbreezedark 1.0.1 \
    #         [list source [file join $dir awbreezedark.tcl]]
    #     package ifneeded awclearlooks 1.3.1 \
    #         [list source [file join $dir awclearlooks.tcl]]
    #     package ifneeded ttk::theme::awclearlooks 1.3.1 \
    #         [list source [file join $dir awclearlooks.tcl]]
    #     package ifneeded awdark 7.12 \
    #         [list source [file join $dir awdark.tcl]]
    #     package ifneeded ttk::theme::awdark 7.12 \
    #         [list source [file join $dir awdark.tcl]]
    #     package ifneeded awlight 7.10 \
    #         [list source [file join $dir awlight.tcl]]
    #     package ifneeded ttk::theme::awlight 7.10 \
    #         [list source [file join $dir awlight.tcl]]
    #     package ifneeded awtemplate 1.5.1 \
    #         [list source [file join $dir awtemplate.tcl]]
    #     package ifneeded ttk::theme::awtemplate 1.5.1 \
    #         [list source [file join $dir awtemplate.tcl]]
    #     package ifneeded awwinxpblue 7.9.1 \
    #         [list source [file join $dir awwinxpblue.tcl]]
    #     package ifneeded ttk::theme::awwinxpblue 7.9.1 \
    #         [list source [file join $dir awwinxpblue.tcl]]
    #
    #     package require tksvg
    #
    #     """)
    # root.tk.call("package", "require", 'awwinxpblue')
    # style.theme_use('awwinxpblue')

    # width = int(root.winfo_screenwidth()*1)
    # height = int(root.winfo_screenheight()*0.95)
    # root.geometry(f'{width}x{height}')
    # my_app = Application(root)
    # root.mainloop()

    multiprocessing.freeze_support()
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    root = tk.Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f'{width}x{height}')
    my_app = Application(root)
    root.mainloop()

    # Application.openfile(r'C:\Github\ANYstructure\ANYstructure\ship_section_example.txt', alone=True)
