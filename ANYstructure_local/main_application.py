 # -*- coding: utf-8 -*-
import copy
import time, datetime
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from ANYstructure_local.calc_loads import *
from ANYstructure_local.calc_structure import *
import ANYstructure_local.load_window as load_window
import ANYstructure_local.make_grid_numpy as grid
import ANYstructure_local.grid_window as grid_window
from ANYstructure_local.helper import *
import math, decimal
import ANYstructure_local.optimize as op
import ANYstructure_local.optimize_window as opw
import ANYstructure_local.optimize_cylinder as opc
import ANYstructure_local.optimize_multiple_window as opwmult
import ANYstructure_local.optimize_geometry as optgeo
import ANYstructure_local.pl_stf_window as struc
import ANYstructure_local.stresses_window as stress
import ANYstructure_local.fatigue_window as fatigue
import ANYstructure_local.load_factor_window as load_factors
from _tkinter import TclError
import multiprocessing
from ANYstructure_local.report_generator import LetterMaker
import os.path, os, pickle
import ctypes
import ANYstructure_local.sesam_interface as sesam
from matplotlib import pyplot as plt
import matplotlib

class Application():
    '''
    The Application class sets up the GUI using Tkinter.
    It is the main part of the code and calls up all other classes etc.
    '''
    def __init__(self, parent):
        '''
        Initaiting the tkinter frame.
        The GUI is general initiated in the method gui_init.
        :param parent:
        '''

        super(Application, self).__init__()
        parent.wm_title('| ANYstructure |')
        self._parent = parent
        parent.protocol("WM_DELETE_WINDOW", self.close_main_window)
        parent.bind("<Configure>", self.resize)

        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        # Main frame for the application
        self._main_fr = ttk.Frame(parent)
        self._main_fr.place(in_=parent, relwidth=1, relheight = 0.99)

        # Definng general colors
        self._general_color = 'alice blue'#"'azure2'  # Color for backgrounds.
        self._entry_color = 'white'  # Entry fields color.
        self._entry_text_color = 'black'  # Entry field tex color
        self._button_bg_color = 'LightBlue1'
        self._button_fg_color = 'black'
        self._color_text = 'white'

        ''' Setting the style of ttk'''
        #
        self._style = ttk.Style(parent)
        self._style.theme_use('vista')
        self._style.layout("TNotebook", [])
        self._style.configure("TNotebook", tabmargins=0)

        # tabbed frames
        self._tabControl = ttk.Notebook(parent)
        self._tab_geo = ttk.Frame(self._tabControl, relief = 'flat')
        self._tab_prop = ttk.Frame(self._tabControl, relief = 'flat')
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

        self._tabControl.place(relwidth=0.2585, relheight = 0.99)
        #self._tabControl.select(self._tab2)


        # Top open/save/new
        menu = tk.Menu(parent)
        parent.config(menu=menu)
        # menu, canvas, etc.
        sub_menu = tk.Menu(menu)
        menu.add_cascade(label='File', menu=sub_menu)
        sub_menu.add_command(label='New project', command=self.reset)
        sub_menu.add_command(label='Save project', command=self.savefile)
        sub_menu.add_command(label='Open project', command=self.openfile)
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
        #undo_redo.add_command(label='Redo geometry action (CTRL-Y)', command=self.redo)
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
        menu.add_cascade(label = 'Reporting', menu = sub_report)
        sub_report.add_command(label = 'Stiffened flat plate - Generate PDF report', command = self.report_generate)
        sub_report.add_command(label='Stiffened flat plate - Generate PDF result table', command=self.table_generate)
        sub_report.add_command(label='Stiffened flat plate - Weight development, plates and beams', command=self.on_plot_cog_dev)

        sub_sesam = tk.Menu(menu)
        menu.add_cascade(label = 'SESAM interface', menu = sub_sesam)
        sub_sesam.add_command(label = 'Export geometry to JS', command = self.export_to_js)

        sub_help = tk.Menu(menu)
        menu.add_cascade(label='Help', menu = sub_help)
        sub_help.add_command(label = 'Open website (documentation etc.)', command = self.open_documentation)
        sub_help.add_command(label='Open documentation pdf', command=self.open_documentation_pdf)
        sub_help.add_command(label='Donate!', command=self.open_donate)
        sub_help.add_command(label = 'Open example file', command = self.open_example)
        sub_help.add_command(label='About ANYstructure', command=self.open_about)

        sub_colors = tk.Menu(menu)
        menu.add_cascade(label='GUI', menu = sub_colors)
        sub_colors.add_command(label='Colors - Default', command=lambda id="default": self.set_colors(id))
        sub_colors.add_command(label = 'Colors - Light', command = lambda id = "light": self.set_colors(id))
        sub_colors.add_command(label='Colors - Grey', command = lambda id = "grey": self.set_colors(id))
        sub_colors.add_command(label='Colors - Dark', command = lambda id = "dark": self.set_colors(id))
        sub_colors.add_command(label='Colors - Unicorn', command=lambda id="pink": self.set_colors(id))
        sub_colors.add_command(label='Functional - All items', command=lambda id="all items": self.set_colors(id))
        sub_colors.add_command(label='Functional - Modelling', command=lambda id="modelling": self.set_colors(id))

        #base_mult = 1.2
        #base_canvas_dim = [int(1000 * base_mult),int(720*base_mult)]  #do not modify this, sets the "orignal" canvas dimensions.
        base_canvas_dim = [1000,720]  #do not modify this, sets the "orignal" canvas dimensions.

        self._canvas_dim = [int(base_canvas_dim[0] *1),
                           int(base_canvas_dim[1] *1)]
        self._canvas_base_origo = [50, base_canvas_dim[1] - 50] # 50 bottom left location of the canvas, (0,0)

        self._canvas_draw_origo = [self._canvas_base_origo[0], self._canvas_base_origo[1]+10]
        self._previous_drag_mouse = list(self._canvas_draw_origo)

        # Setting the fonts for all items in the application.

        self.text_scale = 1
        self._text_size = {'Text 14 bold': 'Verdana '+str(int(14*self.text_scale))+' bold',
                           'Text 16 bold': 'Verdana ' + str(int(16 * self.text_scale)) + ' bold',
                           'Text 18 bold': 'Verdana ' + str(int(18 * self.text_scale)) + ' bold',
                           'Text 12 bold': 'Verdana ' + str(int(12 * self.text_scale)) + ' bold',
                           'Text 10 bold': 'Verdana '+str(int(10*self.text_scale))+' bold',
                           'Text 9 bold': 'Verdana ' + str(int(9 * self.text_scale)) + ' bold',
                           'Text 8 bold': 'Verdana ' + str(int(8 * self.text_scale)) + ' bold',
                           'Text 8': 'Verdana ' + str(int(8 * self.text_scale)),
                           'Text 9': 'Verdana ' + str(int(8 * self.text_scale)),
                           'Text 7': 'Verdana ' + str(int(7 * self.text_scale)),
                           'Text 10': 'Verdana ' + str(int(10 * self.text_scale)),
                           'Text 7 bold': 'Verdana ' + str(int(7 * self.text_scale)) + ' bold',
                           'Text 6 bold': 'Verdana ' + str(int(6 * self.text_scale)) + ' bold'}

        self._canvas_scale = 20 # Used for slider and can change
        self._base_scale_factor = 10 # Used for grid and will not change, 10 is default
        self._prop_canvas_scale = 100 # Scrolling for property canvas
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
        self._main_canvas.place(relx=x_canvas_place, rely=0,relwidth=0.523, relheight = 0.73)
        self._prop_canvas.place(relx=x_canvas_place, rely=0.73, relwidth=0.38, relheight = 0.27)
        self._result_canvas.place(relx=x_canvas_place+0.38, rely=0.73, relwidth=0.36, relheight = 0.27)



        # Point frame
        self._pt_frame = tk.Frame(self._main_canvas, width=100, height=100, bg="black", relief='raised')

        #
        # -------------------------------------------------------------------------------------------------------------
        #
        # The dictionaries below are the main deictionaries used to define this application.
        self._point_dict = {} # Main point dictionary (point:coords) - see method new_point
        self._line_dict = {} # Main line dictionary (line:point,point) - see method new_line
        self._line_to_struc = {} # Main line assosiations (line:various objects) - see method new_structure
                                # The dictionary is widely used and includes all classes in the program
                                # Example:
                                # 'line1':[Structure,CalcScantlings,Fatigue,Load,Combinations]
        self._tank_dict = {} # Main tank dictionary (created when BFS search is executed for the grid) (comp# : TankObj)
        self._load_dict = {} # Main load dictionary (created in separate load window (load# : [LoadObj, lines])
        self._new_load_comb_dict = {} # Load combination dict.(comb,line,load) : [DoubleVar(), DoubleVar(), IntVar()]
                                      # Example ('dnva', 'line25', 'comp3'),  ('dnvb', 'line14', 'comp4'),
                                      # ('manual', 'line74', 'manual'), ('tanktest', 'line76', 'comp3')
        self._sections = list()  #  A list containing section property objects.
        #
        # -------------------------------------------------------------------------------------------------------------
        #
        self._pending_grid_draw = {}  # Saving lines that shall be transferred to the calculation grid
        # Load combinations definition used in method gui_load_combinations
        # These are created and destroyed and is not permanent in the application.
        self._lc_comb_created,self._comp_comb_created,self._manual_created, self._info_created = [],[],[], []
        self._state_logger = dict()  # Used to see if recalculation is needed.
        self._weight_logger = {'new structure': {'COG': list(), 'weight': list(), 'time': list()}}  # Recording of weight development

        # The next dictionaries feed various infomation to the application
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.2], 'tanktest':[1,1,0]} # DNV  loads factors
        self._accelerations_dict = {'static':9.81, 'dyn_loaded':0, 'dyn_ballast':0} # Vertical acclerations
        self._load_conditions = ['loaded','ballast','tanktest', 'part','slamming'] # Should not be modified. Load conditions.
        self._tank_options = {'ballast': 1025, 'crude_oil': 900, 'diesel': 850 , 'slop': 1050, 'fresh water': 1000} # Should not be modified.
        self._default_stresses = {'BOTTOM':(100,100,50,50,5), 'BBS':(70,70,30,30,3), 'BBT':(80,80,30,3), 'HOPPER':(70,70,50,50,3),
                                 'SIDE_SHELL':(100,100,40,40,3),'INNER_SIDE':(80,80,40,40,5), 'FRAME':(70,70,60,0,10),
                                 'FRAME_WT':(70,70,60,0,10),'SSS':(100,100,50,50,20), 'MD':(70,70,4,40,3),
                                 'GENERAL_INTERNAL_WT':(90,90,40,40,5),'GENERAL_INTERNAL_NONWT':(70,70,30,30,3),
                                  'INTERNAL_1_MPA':(1,1,1,1,1), 'INTERNAL_LOW_STRESS_WT':(40,40,20,20,5)}
                                # The default stresses are used for buckling calculations.
        self._structure_types = {'vertical':['BBS', 'SIDE_SHELL', 'SSS'],
                                 'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD'],
                                 'non-wt': ['FRAME', 'GENERAL_INTERNAL_NONWT'],
                                 'internals': ['INNER_SIDE', 'FRAME_WT', 'GENERAL_INTERNAL_WT',
                                               'INTERNAL_ZERO_STRESS_WT', 'INTERNAL_LOW_STRESS_WT']}
        self._options_type = [op_typ for op_typ in self._default_stresses.keys()]
        self._point_options= ['fixed','free']
        self._load_window_couter = 1 # this is used to create the naming of the tanks in the load window
        self._logger = {'added': list(), 'deleted': list()}  # used to log operations for geometry operations, to be used for undo/redo
        self.__returned_load_data = None # Temporary data for returned loads from the load window.
        self.__copied_line_prop = None  # Used to copy line properties to another.
        self._PULS_results = None # If a puls run is avaliable, it is stored here.
        self._center_of_buoyancy = dict()   # Center of buoyancy for all and for carious static drafts
                                            # Example {8: (5,20), 22: (12,20), 'all': (16,20)}

        self._ML_buckling = dict()  # Buckling machine learning algorithm
        for name, file_base in zip(['cl SP buc int predictor', 'cl SP buc int scaler',
                                    'cl SP ult int predictor', 'cl SP ult int scaler',
                                    'cl SP buc GLGT predictor', 'cl SP buc GLGT scaler',
                                    'cl SP ult GLGT predictor', 'cl SP ult GLGT scaler',
                                    'cl UP buc int predictor', 'cl UP buc int scaler',
                                    'cl UP ult int predictor', 'cl UP ult int scaler',
                                    'cl UP buc GLGT predictor', 'cl UP buc GLGT scaler',
                                    'cl UP ult GLGT predictor', 'cl UP ult GLGT scaler',
                                    'CSR predictor UP', 'CSR scaler UP',
                                    'CSR predictor SP', 'CSR scaler SP'
                                    ],
                                   ["CL_output_cl_buc_predictor_In-plane_support_cl_1_SP",
                                    "CL_output_cl_buc_scaler_In-plane_support_cl_1_SP",
                                    "CL_output_cl_ult_predictor_In-plane_support_cl_1_SP",
                                    "CL_output_cl_ult_scaler_In-plane_support_cl_1_SP",
                                    "CL_output_cl_buc_predictor_In-plane_support_cl_2,_3_SP",
                                    "CL_output_cl_buc_scaler_In-plane_support_cl_2,_3_SP",
                                    "CL_output_cl_ult_predictor_In-plane_support_cl_2,_3_SP",
                                    "CL_output_cl_ult_scaler_In-plane_support_cl_2,_3_SP",
                                    "CL_output_cl_buc_predictor_In-plane_support_cl_1_UP",
                                    "CL_output_cl_buc_scaler_In-plane_support_cl_1_UP",
                                    "CL_output_cl_ult_predictor_In-plane_support_cl_1_UP",
                                    "CL_output_cl_ult_scaler_In-plane_support_cl_1_UP",
                                    "CL_output_cl_buc_predictor_In-plane_support_cl_2,_3_UP",
                                    "CL_output_cl_buc_scaler_In-plane_support_cl_2,_3_UP",
                                    "CL_output_cl_ult_predictor_In-plane_support_cl_2,_3_UP",
                                    "CL_output_cl_ult_scaler_In-plane_support_cl_2,_3_UP",
                                    "CL_CSR-Tank_req_cl_predictor",
                                    "CL_CSR-Tank_req_cl_UP_scaler",
                                    "CL_CSR_plate_cl,_CSR_web_cl,_CSR_web_flange_cl,_CSR_flange_cl_predictor",
                                    "CL_CSR_plate_cl,_CSR_web_cl,_CSR_web_flange_cl,_CSR_flange_cl_SP_scaler"]):
            self._ML_buckling[name] = None

            if os.path.isfile(file_base + '.pickle'):
                file = open(file_base + '.pickle', 'rb')
                from sklearn.neural_network import MLPClassifier
                from sklearn.preprocessing import StandardScaler
                self._ML_buckling[name] = pickle.load(file)
                file.close()
            else:
                file = open(self._root_dir +'\\' + file_base + '.pickle', 'rb')
                from sklearn.neural_network import MLPClassifier
                from sklearn.preprocessing import StandardScaler
                self._ML_buckling[name] = pickle.load(file)
                file.close()

        self._ML_classes ={0: 'N/A',
                           1: 'A negative utilisation factor is found.',
                           2: 'At least one of the in-plane loads must be non-zero.',
                           3: 'Division by zero',
                           4: 'Overflow',
                           5: 'The aspect ratio exceeds the PULS code limit',
                           6: 'The global slenderness exceeds 4. Please reduce stiffener span or increase stiffener height.',
                           7: 'The applied pressure is too high for this plate field.', 8: 'web-flange-ratio',
                           9:  'UF below or equal 0.87', 10: 'UF between 0.87 and 1.0', 11: 'UF above 1.0'}

        # Used to select parameter
        self._stuctural_definition = ['mat_yield','mat_factor', 'span', 'spacing', 'plate_thk', 'stf_web_height',
                                      'stf_web_thk',
                                       'stf_flange_width', 'stf_flange_thk', 'structure_type', 'stf_type',
                                       'sigma_y1', 'sigma_y2', 'sigma_x1','sigma_x2', 'tau_xy', 'plate_kpp', 'stf_kps','stf_km1',
                                       'stf_km2', 'stf_km3', 'press_side', 'zstar_optimization',
                                      'puls buckling method', 'puls boundary', 'puls stiffener end', 'puls sp or up',
                                      'puls up boundary']
        self._p1_p2_select = False
        self._line_is_active = False # True when a line is clicked
        self._active_line = '' # Name of the clicked point
        self._point_is_active = False # True when a point is clicked
        self._active_point = '' # Name of the clicked point
        self.controls() # Function to activate mouse clicks
        self._line_point_to_point_string = [] # This one ensures that a line is not created on top of a line
        self._multiselect_lines = []  # A list used to select many lines. Used to set properties.

        # Initsializing the calculation grid used for tank definition
        self._grid_dimensions = [self._canvas_base_origo[1] + 1, base_canvas_dim[0] - self._canvas_base_origo[0] + 1]


        #self._grid_dimensions = [self._canvas_base_origo[1], base_canvas_dim[0] - self._canvas_base_origo[0] + 1]

        self._main_grid  = grid.Grid(self._grid_dimensions[0], self._grid_dimensions[1])
        self._grid_calc = None
        self.text_widget = None
        self._clicked_section_create= None # Identifiation of the button clicked. Sections.
        self._gui_functional_look = 'all items' # used to change size and location of frames, canvas etc.

        # These sets the location where entries are placed.
        ent_x = 0.4
        delta_y = 0.025
        delta_x = 0.1
        point_x_start, point_start = 0.005208333, 0.13

        # ----------------------INITIATION OF THE SMALLER PARTS OF THE GUI STARTS HERE--------------------------
        # --- point input/output ----
        self._new_point_x = tk.DoubleVar()
        self._new_point_y = tk.DoubleVar()
        self._new_point_fix = tk.StringVar()
        self._new_zstar_optimization = tk.BooleanVar()
        self._new_zstar_optimization.set(True)
        ent_width = 6  # width of entries

        self._project_information = tk.Text(self._tab_geo, wrap = tk.WORD, relief = tk.FLAT)
        self._project_information.place(relx=0.005, rely=0.005, relwidth = 0.95, relheight = 0.1)

        self._project_information.insert(1.0, 'No information on project provided. Input here.')

        ttk.Label(self._tab_geo, text='Input point coordinates [mm]', font=self._text_size['Text 9 bold'],
                 )\
            .place(rely=point_start, relx=point_x_start, anchor = tk.NW)
        ttk.Label(self._tab_geo, text='Point x (horizontal) [mm]:',font="Text 9", )\
            .place(relx=point_x_start, rely=point_start+ delta_y,)
        ttk.Label(self._tab_geo, text='Point y (vertical)   [mm]:',font="Text 9", )\
            .place(relx=point_x_start, rely=point_start + delta_y*2)

        ttk.Entry(self._tab_geo, textvariable=self._new_point_x, width = int(ent_width * 1.5))\
            .place(relx=ent_x, rely=point_start+ delta_y)
        ttk.Entry(self._tab_geo, textvariable=self._new_point_y, width = int(ent_width * 1.5))\
            .place(relx=ent_x, rely=point_start + delta_y*2)

        ttk.Button(self._tab_geo, text='Add point (coords)', command=self.new_point,style = "Bold.TButton")\
            .place(relx=ent_x + 2 * delta_x, rely=point_start+1*delta_y, relwidth = 0.3)
        ttk.Button(self._tab_geo, text='Copy point (relative)', command=self.copy_point,style = "Bold.TButton")\
            .place(relx=ent_x + 2 * delta_x, rely=point_start+2*delta_y,relwidth = 0.3)
        ttk.Button(self._tab_geo, text='Move point', command=self.move_point,style = "Bold.TButton")\
            .place(relx=ent_x + 2 * delta_x, rely=point_start+3*delta_y, relwidth = 0.3)
        ttk.Button(self._tab_geo, text='Move line', command=self.move_line,style = "Bold.TButton")\
            .place(relx=ent_x + 2 * delta_x,rely=point_start+4*delta_y, relwidth = 0.3)

        self._new_draw_point_name = tk.BooleanVar()
        self._new_draw_point_name.set(False)
        ttk.Label(self._tab_geo, text='Show point names in GUI', font="Text 9")\
            .place(relx=point_x_start, rely=point_start+3*delta_y)
        ttk.Checkbutton(self._tab_geo, variable = self._new_draw_point_name, command = self.on_color_code_check)\
            .place(relx=ent_x, rely=point_start+3*delta_y)

        line_start, line_x = point_start+0.2, 0.0055
        ttk.Label(self._tab_geo, text='Input line from "point number" to "point number"',
                 font=self._text_size['Text 9 bold'], )\
            .place(rely=line_start, relx=line_x, anchor = tk.NW)
        ttk.Label(self._tab_geo, text='Line from point:',font="Text 9", )\
            .place(relx=line_x, rely=line_start+delta_y)
        ttk.Label(self._tab_geo, text='Line to point:',font="Text 9", )\
            .place(relx=line_x, rely=line_start+2*delta_y)


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
        self._new_line_name = tk.BooleanVar()
        self._new_line_name.set(False)
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
        self._new_colorcode_puls_sp_or_up= tk.BooleanVar()
        self._new_colorcode_puls_sp_or_up.set(False)
        self._new_colorcode_puls_acceptance= tk.BooleanVar()
        self._new_colorcode_puls_acceptance.set(False)
        self._new_colorcode_total= tk.BooleanVar()
        self._new_colorcode_total.set(False)
        self._new_colorcode_spacing= tk.BooleanVar()
        self._new_colorcode_spacing.set(False)
        self._new_toggle_var = tk.StringVar()
        self._new_toggle_select_multiple = tk.BooleanVar()
        self._new_toggle_puls = tk.BooleanVar()
        self._new_toggle_puls.set(False)
        self._new_puls_uf = tk.DoubleVar()
        self._new_puls_uf.set(0.87)
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

        line_start, line_x = point_start+0.2, 0.0055

        ttk.Spinbox(self._tab_geo, textvariable=self._new_line_p1, width=int(ent_width * 1), from_ = 0,
                    to = float('inf')).place(relx=ent_x, rely=line_start+1*delta_y)
        ttk.Spinbox(self._tab_geo, textvariable=self._new_line_p2, width=int(ent_width * 1),
                    from_ = 0, to = float('inf')).place(relx=ent_x, rely=line_start+2*delta_y)

        ttk.Button(self._tab_geo, text='Add line', command=self.new_line,style = "Bold.TButton")\
            .place(relx=ent_x + 2 * delta_x, rely=line_start+delta_y, relwidth = 0.3)

        # --- delete points and lines ---
        self._new_delete_line = tk.IntVar()
        self._new_delete_point = tk.IntVar()
        del_start, del_x = line_start + 0.2,0.005208333
        ttk.Label(self._tab_geo, text='Delete lines and points (or left/right click and use "Delete key")',
                 font=self._text_size['Text 9 bold'], )\
            .place(rely=del_start - 0.02,relx=del_x, anchor = tk.NW)
        self._ent_delete_line = ttk.Spinbox(self._tab_geo, textvariable=self._new_delete_line,
                                            from_ = 0, to = float('inf'),
                                        width=int(ent_width * 1))
        self._ent_delete_line.place(relx=ent_x, rely=del_start + delta_y)

        self._ent_delete_point = ttk.Spinbox(self._tab_geo, textvariable=self._new_delete_point,
                                             from_ = 0, to = float('inf'),
                                         width=int(ent_width * 1))
        self._ent_delete_point.place(relx=ent_x, rely=del_start + delta_y*2)

        ttk.Label(self._tab_geo, text='Line number (left click):',font="Text 9")\
            .place(relx=del_x, rely=del_start+ delta_y)
        ttk.Label(self._tab_geo, text='Point number (right click):',font="Text 9", )\
            .place(relx=del_x, rely=del_start+ delta_y*2)

        ttk.Button(self._tab_geo, text='Delete line',command=self.delete_line,style = "Bold.TButton"
                                         ).place(relx=ent_x+delta_x*2, rely=del_start + delta_y,
                                                                                    relwidth = 0.3)
        ttk.Button(self._tab_geo, text='Delete prop.',command=self.delete_properties_pressed,style = "Bold.TButton"
                                         ).place(relx=ent_x+delta_x*2, rely=del_start + delta_y*2,
                                                                                    relwidth = 0.3)

        ttk.Button(self._tab_geo, text='Delete point',command=self.delete_point,style = "Bold.TButton"
                                          ).place(relx=ent_x+2*delta_x, rely=del_start + delta_y*3,
                                                                                     relwidth = 0.3)
        
        # Shifing of coordinate display
        shift_x = del_x
        shift_y = del_start+0.2
        ttk.Label(self._tab_geo, text='Shift coordinate labeling [mm]: ', font = self._text_size['Text 8 bold'])\
            .place(relx=shift_x, rely=shift_y - delta_y*0.5)
        ttk.Label(self._tab_geo, text='Used if you want a different origin of the repoted coordinates. \n'
                                   'Does not affect loads.', font = self._text_size['Text 8'])\
            .place(relx=shift_x, rely=shift_y + delta_y*0.5)

        ttk.Label(self._tab_geo, text='y shift', font = self._text_size['Text 8'],
                 ).place(relx=shift_x, rely=shift_y + delta_y * 2)
        ttk.Label(self._tab_geo, text='x shift ', font = self._text_size['Text 8'],
                 ).place(relx=shift_x, rely=shift_y + delta_y * 3)

        self._ent_shift_hor = ttk.Entry(self._tab_geo, textvariable = self._new_shift_viz_coord_hor,
                                       width = ent_width )

        self._ent_shift_hor.bind('<FocusOut>', self.trace_shift_change)
        self._ent_shift_ver = ttk.Entry(self._tab_geo, textvariable = self._new_shift_viz_coord_ver,
                                       width = ent_width,
                                       )
        self._ent_shift_ver.bind('<FocusOut>', self.trace_shift_change)
        #self._ent_shift_ver.trace('w', self.trace_shift_change)
        self._ent_shift_hor.place(relx=ent_x, rely=shift_y + delta_y * 2)
        self._ent_shift_ver.place(relx=ent_x, rely=shift_y + delta_y * 3)

        ttk.Label(self._tab_geo, text='Use shifted coordinates', font="Text 9")\
            .place(relx=shift_x, rely=shift_y + delta_y * 4)
        ttk.Checkbutton(self._tab_geo, variable = self._new_shifted_coords, command = self.update_frame)\
            .place(relx=ent_x, rely=shift_y + delta_y * 4)

        # --- structure type information ---

        def show_message():
            messagebox.showinfo(title='Structure type',message='Types - sets default stresses (sigy1/sigy2/sigx/tauxy)'
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
                                             '3. Press Change parameters button', font=self._text_size['Text 9'])\
            .place(relx = hor_start, rely=vert_start-1*delta_y)
        self._toggle_btn = tk.Button(self._tab_prop_tools, text="Toggle select\nmultiple", relief="raised",
                                     command=self.toggle_select_multiple, bg = '#E1E1E1', activebackground = '#E5F1FB' )
        self._toggle_change_param = ttk.Button(self._tab_prop_tools, text="Change parameters",
                                     command=self.toggle_set_variable)
        self._toggle_param_to_change = None
        self._toggle_btn.place(relx=hor_start, rely=vert_start+2*delta_y, relwidth = 0.2, relheight = 0.06)

        self._toggle_change_param.place(relx=hor_start+ delta_x*6, rely=vert_start+2*delta_y, relwidth = 0.25)

        self._toggle_choose = ttk.OptionMenu(self._tab_prop_tools, self._new_toggle_var,self._stuctural_definition[0],
                                             *self._stuctural_definition,
                                            command = self.update_frame)
        self._toggle_choose.place(relx=hor_start+ delta_x*3, rely=vert_start+2*delta_y, relwidth = 0.25)

        ttk.Label(self._tab_prop_tools, text='Scale stresses when changing properties', font=self._text_size['Text 9'])\
            .place(relx = hor_start + delta_x*1, rely=vert_start+6*delta_y)

        ttk.Checkbutton(self._tab_prop_tools, variable = self._new_scale_stresses, command = self.on_color_code_check)\
            .place(relx = hor_start + delta_x*0, rely=vert_start+6*delta_y)

        ttk.Label(self._tab_prop_tools, text='Factor when scaling stresses up, fup', font=self._text_size['Text 8']).place(relx =hor_start + delta_x,
                                                                                          rely=vert_start+7*delta_y)
        ttk.Label(self._tab_prop_tools, text='Factor when scaling stresses down, fdown', font=self._text_size['Text 8']).place(relx =hor_start + delta_x,
                                                                                  rely=vert_start+8*delta_y)

        ent_fup = ttk.Entry(self._tab_prop_tools, textvariable=self._new_fup)
        ent_fup.place(relx =hor_start, rely=vert_start+7*delta_y, relwidth = 0.1)

        ent_fdwn = ttk.Entry(self._tab_prop_tools, textvariable=self._new_fdwn)
        ent_fdwn.place(relx =hor_start, rely=vert_start+8*delta_y, relwidth = 0.1)



        # --- main variable to define the structural properties ---
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
        #self._new_calculation_domain.set('Stiffened panel, flat')
        self._new_calculation_domain.set('Flat plate, stiffened')

        #self._new_material_factor.trace('w', self.trace_material_factor)
        # --- main entries and labels to define the structural properties ---
        ent_width = 12 #width of entries

        '''
        Flat plate input
        '''

        self._flat_gui_headlines = [ttk.Label(self._tab_prop, text='Plate input',
                                              font = self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Stiffener',
                                              font = self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Girder',
                                              font = self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Load/stresses input',
                                              font = self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Special provitions input',
                                              font = self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Buckling input',
                                              font = self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Stiffener',
                                              font=self._text_size['Text 8 bold']),
                                    ttk.Label(self._tab_prop, text='Girder',
                                              font=self._text_size['Text 8 bold']),
                                    ]

        self._ent_field_len = ttk.Entry(self._tab_prop, textvariable=self._new_field_len, width = int(10))
        self._ent_stf_spacing = ttk.Entry(self._tab_prop, textvariable=self._new_stf_spacing, width = int(10))
        self._ent_plate_thk = ttk.Entry(self._tab_prop, textvariable=self._new_plate_thk, width = int(10))
        self._ent_girder_length = ttk.Entry(self._tab_prop, textvariable=self._new_girder_length_LG, width = int(10))
        self._ent_panel_length = ttk.Entry(self._tab_prop, textvariable=self._new_panel_length_Lp, width = int(10))

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
                                                    command= lambda id= "flat stf": self.on_open_structure_window(id))
        self._ent_stf_type = ttk.OptionMenu(self._tab_prop, self._new_stf_type, 'T', *['T', 'FB', 'L', 'L-bulb'])
        self._ent_stf_web_h = ttk.Entry(self._tab_prop, textvariable=self._new_stf_web_h, width = int(10))
        self._ent_stf_web_t = ttk.Entry(self._tab_prop, textvariable=self._new_stf_web_t, width = int(10))
        self._ent_stf_fl_w = ttk.Entry(self._tab_prop, textvariable=self._new_stf_fl_w, width = int(10))
        self._ent_str_fl_t = ttk.Entry(self._tab_prop, textvariable=self._new_stf_fl_t, width = int(10))

        self._lab_stf_section = ttk.Label(self._tab_prop, text='')
        self._lab_stf_type = ttk.Label(self._tab_prop, text='Stiffener/girder type')
        self._lab_web_h = ttk.Label(self._tab_prop, text='Web height, hw', )
        self._lab_web_thk = ttk.Label(self._tab_prop, text='Web thickness, tw', )
        self._lab_fl_w= ttk.Label(self._tab_prop, text='Flange width, b', )
        self._lab_fl_thk = ttk.Label(self._tab_prop, text='Flange thickeness, tf', )

        self._flat_gui_stf = [self._btn_flat_stf_section, self._ent_stf_type, self._ent_stf_web_h, self._ent_stf_web_t,
                              self._ent_stf_fl_w,self._ent_str_fl_t]
        self._flat_gui_lab_stf = [self._lab_stf_section,self._lab_stf_type,self._lab_web_h,self._lab_web_thk,
                                  self._lab_fl_w, self._lab_fl_thk]

        self._btn_flat_girder_section = ttk.Button(self._tab_prop, text='Girder',
                                                    command= lambda id= "flat girder": self.on_open_structure_window(id))
        self._ent_girder_type = ttk.OptionMenu(self._tab_prop, self._new_girder_type, 'T', *['T', 'FB', 'L', 'L-bulb'])
        self._ent_girder_web_h = ttk.Entry(self._tab_prop, textvariable=self._new_girder_web_h, width = int(10))
        self._ent_girder_web_t = ttk.Entry(self._tab_prop, textvariable=self._new_girder_web_t, width = int(10))
        self._ent_girder_fl_w = ttk.Entry(self._tab_prop, textvariable=self._new_girder_fl_w, width = int(10))
        self._ent_girder_fl_t = ttk.Entry(self._tab_prop, textvariable=self._new_girder_fl_t, width = int(10))
        self._flat_gui_girder = [self._btn_flat_girder_section, self._ent_girder_type, self._ent_girder_web_h,
                                 self._ent_girder_web_t,
                              self._ent_girder_fl_w,self._ent_girder_fl_t]

        self._ent_plate_kpp = ttk.Entry(self._tab_prop, textvariable=self._new_plate_kpp, width = int(5*1))
        self._ent_plate_kps = ttk.Entry(self._tab_prop, textvariable=self._new_stf_kps, width = int(5*1))
        self._ent_stf_km1 = ttk.Entry(self._tab_prop, textvariable=self._new_stf_km1, width = int(5*1))
        self._ent_stf_km2 = ttk.Entry(self._tab_prop, textvariable=self._new_stf_km2,width = int(5*1))
        self._ent_stf_km3 = ttk.Entry(self._tab_prop, textvariable=self._new_stf_km3, width = int(5*1))
        self._lab_kpp = ttk.Label(self._tab_prop,text='kpp', )
        self._lab_kps = ttk.Label(self._tab_prop, text='kps', )
        self._lab_km1 = ttk.Label(self._tab_prop, text='km1', )
        self._lab_km2 = ttk.Label(self._tab_prop, text='km2', )
        self._lab_km3 = ttk.Label(self._tab_prop, text='km3', )
        self._flat_gui_os_c101_provisions = [self._ent_plate_kpp, self._ent_plate_kps, self._ent_stf_km1,
                                             self._ent_stf_km2, self._ent_stf_km3]
        self._flat_gui_lab_os_c101_provisions = [self._lab_kpp, self._lab_kps, self._lab_km1,self._lab_km2,
                                                 self._lab_km3]

        self._ent_pressure_side = ttk.OptionMenu(self._tab_prop,self._new_pressure_side,('both sides','plate side',
                                                                                         'stiffener side')[0],
                                                 *('both sides','plate side','stiffener side'))
        self._ent_sigma_y1= ttk.Entry(self._tab_prop, textvariable=self._new_sigma_y1,  width = int(10))
        self._ent_sigma_y2 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_y2, width=int(10))
        self._ent_sigma_x1 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_x1, width=int(10))
        self._ent_sigma_x2 = ttk.Entry(self._tab_prop, textvariable=self._new_sigma_x2, width=int(10))
        self._ent_tauxy = ttk.Entry(self._tab_prop, textvariable=self._new_tauxy, width=int(10))
        self._ent_mat = ttk.Entry(self._tab_prop, textvariable=self._new_material, width = int(10))
        self._ent_mat_factor = ttk.Entry(self._tab_prop, textvariable=self._new_material_factor, width = int(10))
        self._ent_structure_type = ttk.OptionMenu(self._tab_prop, self._new_stucture_type, self._options_type[0],
                                                  *self._options_type,command = self.option_meny_structure_type_trace)


        self._lab_press_side = ttk.Label(self._tab_prop, text='Overpressure side')
        self._lab_sig_y1 = ttk.Label(self._tab_prop, text='Longitudinal compr. ,sig_y1')
        self._lab_sig_y2 = ttk.Label(self._tab_prop, text='Longitudinal compr. ,sig_y2')
        self._lab_sig_x1 = ttk.Label(self._tab_prop, text='Transverse compress.,sig_x1')
        self._lab_sig_x2 = ttk.Label(self._tab_prop, text='Transverse compress.,sig_x2')
        self._lab_tau_y1 = ttk.Label(self._tab_prop, text='Shear Stres,tau_y1')
        self._lab_yield = ttk.Label(self._tab_prop, text='Yield [MPa]:', font = self._text_size['Text 9'])
        self._lab_mat_fac = ttk.Label(self._tab_prop, text='Mat. factor', font = self._text_size['Text 9'])
        self._lab_structure_type = ttk.Label(self._tab_prop, text='Select structure type:',
                                             font=self._text_size['Text 9'])

        self._flat_gui_lab_loads = [self._lab_press_side ,self._lab_sig_y1, self._lab_sig_y2,self._lab_sig_x1,
                                    self._lab_sig_x2, self._lab_tau_y1, self._lab_yield, self._lab_mat_fac,
                                    self._lab_structure_type]
        self._flat_gui_loads = [self._ent_pressure_side, self._ent_sigma_y1, self._ent_sigma_y2, self._ent_sigma_x1,
                                self._ent_sigma_x2, self._ent_tauxy, self._ent_mat, self._ent_mat_factor,
                                self._ent_structure_type]


        self._new_buckling_method = tk.StringVar()
        options = ['DNV-RP-C201 - prescriptive','DNV PULS','ML-CL (PULS based)']
        self._lab_buckling_method = ttk.Label(self._tab_prop, text='Set buckling method')
        self._buckling_method = ttk.OptionMenu(self._tab_prop, self._new_buckling_method, options[0], *options,
                                               command=self.update_frame)

        # PULS interface
        self._puls_run_all = ttk.Button(self._tab_prop, text='Run PULS -\nupdate results',
                                     command=self.puls_run_all_lines)
        self._ent_puls_uf = ttk.Entry(self._tab_prop, textvariable=self._new_puls_uf, width=int(ent_width * 1))
        self._new_puls_uf.trace('w', self.trace_acceptance_change)

        self._ent_puls_sp_or_up= ttk.OptionMenu(self._tab_prop, self._new_puls_sp_or_up, 'SP', *['SP', 'UP'],
                                                command = self.trace_puls_up_or_sp,)
        self._ent_puls_method = ttk.OptionMenu(self._tab_prop, self._new_puls_method,'buckling',
                                               *['buckling', 'ultimate'])
        self._ent_puls_panel_boundary = ttk.OptionMenu(self._tab_prop, self._new_puls_panel_boundary,'Int',
                                                      *['Int', 'GL', 'GT'])
        #self._ent_puls_stf_end_type = ttk.OptionMenu(self._tab_prop, self._new_buckling_stf_end_support,'C',*['C', 'S'])
        self._ent_puls_stf_end_type = ttk.OptionMenu(self._tab_prop, self._new_buckling_stf_end_support, 'Continuous',
                                                     *['Continuous', 'Sniped'])
        self._ent_puls_up_boundary = ttk.Entry(self._tab_prop, textvariable=self._new_puls_up_boundary, width=int(7*1))
        self._zstar_chk = ttk.Checkbutton(self._tab_prop, variable=self._new_zstar_optimization)

        self._lab_puls_input =  ttk.Label(self._tab_prop, text='Buckling paramenters input',
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
                                                ,width=int(ent_width * 1)),
                                      ttk.OptionMenu(self._tab_prop, self._new_buckling_tension_field,
                                                     'not allowed', *['allowed', 'not allowed'])]
        self._flat_gui_buc_girder_opt = [ttk.OptionMenu(self._tab_prop, self._new_buckling_girder_end_support,
                                                        'Continuous', *['Continuous', 'Sniped']),
                                         ttk.OptionMenu(self._tab_prop, self._new_buckling_fab_method_girder,
                                                        'welded',*['welded', 'rolled']),
                                         ttk.Entry(self._tab_prop, textvariable=self._new_buckling_length_factor_girder
                                                   ,width=int(ent_width * 1)),
                                         ttk.Entry(self._tab_prop,
                                                   textvariable=self._new_buckling_girder_dist_bet_lat_supp,
                                                   width=int(ent_width * 1)),
                                         ttk.OptionMenu(self._tab_prop, self._new_buckling_effective_against_sigy,
                                                        'Stf. pl. effective against sigma y',
                                                        *['Stf. pl. effective against sigma y',
                                                          'All sigma y to girder'])]
        self._flat_gui_girder_moment_factor = [ ttk.Label(self._tab_prop, text='Girder moment factor at support/midspan'),
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

        self._lab_puls_acceptance=  ttk.Label(self._tab_prop, text='PULS acceptance')
        self._lab_puls_uf =  ttk.Label(self._tab_prop, text='PULS utilization factor:')
        self._lab_puls_int_gt =  ttk.Label(self._tab_prop, text='PULS Int-integrated GL-free left/right GT-free top/bottom')
        self._lab_puls_cont_sniped =  ttk.Label(self._tab_prop, text='Continous or Sniped',
                                                font = self._text_size['Text 8'])
        self._lab_puls_up_supp =  ttk.Label(self._tab_prop, text='PULS UP support - left,right,upper,lower',
                                           font = self._text_size['Text 8'])
        # self._zstar_label = ttk.Label(self._tab_prop, text='z* optimization (buckling RP-C201)',
        #                               font=self._text_size['Text 8'])

        self._flat_gui_buckling = [self._ent_puls_method, self._ent_puls_uf,
                                   self._ent_puls_panel_boundary,
                                   self._ent_puls_up_boundary]#, self._zstar_chk]

        self._flat_gui_lab_buckling = [self._lab_puls_acceptance,  self._lab_puls_uf,
                                       self._lab_puls_int_gt,
                                       self._lab_puls_up_supp]#, self._zstar_label]

        self._button_str_type = ttk.Button(self._tab_prop, text='Show structure types', command=show_message)
        self._structure_types_label =  ttk.Label(textvariable = self._new_stucture_type_label,
                                                font = self._text_size['Text 8'], )

        #-------------Color coding-------------------
        self._chk_cc_spacing = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_spacing,
                                              command = self.on_color_code_check)
        self._chk_button_sigmax1 = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_sigmax,
                                                 command = self.on_color_code_check)
        self._chk_button_sigmax2 = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_sigmax,
                                                 command = self.on_color_code_check)
        self._chk_button_sigmay1 = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_sigmay1,
                                                  command = self.on_color_code_check)
        self._chk_button_sigmay2 = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_sigmay2,
                                                  command = self.on_color_code_check)
        self._chk_button_tauxy = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_tauxy,
                                                command = self.on_color_code_check)
        self._chk_button_structure_type = ttk.Checkbutton(self._tab_information, variable = self._new_colorcode_structure_type,
                                                         command = self.on_color_code_check)

        self._chk_button_puls_spup = ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_puls_sp_or_up,
                                                    command=self.on_color_code_check)
        self._chk_button_puls_acceptance =ttk.Checkbutton(self._tab_information, variable=self._new_colorcode_puls_acceptance,
                                                         command=self.on_color_code_check)


        chk_deltax = 0.1
        chk_deltay = 0.025
        self._information_gui_chk_structure = [ttk.Checkbutton(self._tab_information, variable = self._new_line_name,
                                                               command = self.on_color_code_check),
                                               ttk.Checkbutton(self._tab_information,
                                                              variable = self._new_label_color_coding,
                                                              command = self.on_color_code_check),
                                              ttk.Checkbutton(self._tab_information,
                                                              variable = self._new_show_cog,
                                                              command = self.update_frame),
                                              ttk.Checkbutton(self._tab_information,
                                                                     variable = self._new_shortcut_backdrop,
                                                                     command = self.update_frame),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_beams,
                                                                command = self.on_color_code_check),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_plates,
                                                                command = self.on_color_code_check),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_pressure,
                                                                command = self.on_color_code_check),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_utilization,
                                                                command = self.on_color_code_check),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_section_modulus,
                                                                command = self.on_color_code_check),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_fatigue,
                                                                command = self.on_color_code_check),
                                                ttk.Checkbutton(self._tab_information,
                                                                variable = self._new_colorcode_total,
                                                                command = self.on_color_code_check),
                                                    self._chk_cc_spacing, self._chk_button_sigmax1,
                                                     self._chk_button_sigmax2,
                                               self._chk_button_sigmay1, self._chk_button_sigmay2,
                                               self._chk_button_tauxy,self._chk_button_structure_type ,
                                               self._chk_button_puls_spup,
                                               self._chk_button_puls_acceptance]

        self._information_gui_lab_chk_structure = [ttk.Label(self._tab_information, text='Show line names in GUI', font="Text 9"),
                                                   ttk.Label(self._tab_information, text='Label color code', font="Text 9"),
                                                   ttk.Label(self._tab_information, text='Show COG/COB', font="Text 9"),
                                                   ttk.Label(self._tab_information, text='Check to see avaliable shortcuts', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Beam prop.', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Plate thk.', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Pressure', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Buckling UF', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Sec. mod. UF', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Fatigue UF', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Total UF', font="Text 9"),
                                                    ttk.Label(self._tab_information, text='Stiffener spacing'),
                                                   ttk.Label(self._tab_information, text='Stresses, sigma x1'),
                                                   ttk.Label(self._tab_information, text='Stresses, sigma x2'),
                                                   ttk.Label(self._tab_information, text='Stresses, sigma y1'),
                                                   ttk.Label(self._tab_information, text='Stresses, sigma y2'),
                                                   ttk.Label(self._tab_information, text='Stresses, sigma tauxy'),
                                                   ttk.Label(self._tab_information, text='Structure type'),
                                                   ttk.Label(self._tab_information, text='Buckling - SP or UP'),
                                                   ttk.Label(self._tab_information, text='Buckling acceptance criteria')]
        idx = 2
        for lab, ent in zip(self._information_gui_chk_structure, self._information_gui_lab_chk_structure):
            lab.place(relx=0.02, rely=idx*chk_deltay)
            ent.place(relx=0.02 + chk_deltax, rely=idx*chk_deltay)
            idx += 1
            
        try:
            img_file_name = 'img_stf_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._stf_button = tk.Button(self._tab_prop, image=photo,
                                         command= self.on_open_structure_window)
            self._stf_button.image = photo

        except TclError:
            self._stf_button = tk.Button(self._tab_prop, text='STF.',
                                         command= self.on_open_structure_window,
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
                                       style = "Bold.TButton")


        ''' Start shell input '''


        ''' 
        Shell input
        '''
        self._new_shell_thk = tk.DoubleVar()
        self._new_shell_radius = tk.DoubleVar()
        self._new_shell_dist_rings = tk.DoubleVar()
        self._new_shell_length = tk.DoubleVar()
        self._new_shell_tot_length= tk.DoubleVar()
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
        self._lab_shell =  ttk.Label(self._tab_prop, text='Shell and curved plate input [mm]')
        self._ent_shell_plate_thk = ttk.Entry(self._tab_prop, textvariable=self._new_shell_thk)

        self._ent_shell_radius = ttk.Entry(self._tab_prop, textvariable=self._new_shell_radius)
        self._ent_shell_dist_rings = ttk.Entry(self._tab_prop, textvariable=self._new_shell_dist_rings)
        self._ent_shell_length = ttk.Entry(self._tab_prop, textvariable=self._new_shell_length,width = int(5*1))
        self._ent_shell_tot_length = ttk.Entry(self._tab_prop, textvariable=self._new_shell_tot_length,

                                       )
        self._ent_shell_k_factor= ttk.Entry(self._tab_prop, textvariable=self._new_shell_k_factor,
                                      )
        self._ent_shell_material_factor= ttk.Entry(self._tab_prop, textvariable=self._new_shell_mat_factor)

        self._shell_gui_items = [self._lab_shell, self._ent_shell_plate_thk, self._ent_shell_radius,
                                 self._ent_shell_dist_rings,
                                 self._ent_shell_length,self._ent_shell_tot_length,self._ent_shell_k_factor,
                                 self._ent_shell_material_factor]

        '''
        Shell, lognitudinal stiffeners
        '''
        # USING stiffeners for flat plates
        self._lab_shell_long_stiffener =  ttk.Label(self._tab_prop, text='Longitudinal stiffener properties [mm]',

                                      )
        self._btn_shell_stf_section_long_stf = ttk.Button(self._tab_prop, text='STF',
                                                          command= lambda id= "long stf": self.on_open_structure_window(id))

        self._shell_long_stf_gui_items = [self._lab_shell_long_stiffener ,self._ent_stf_web_h, self._ent_stf_web_t,
                                          self._ent_stf_fl_w, self._ent_str_fl_t, self._ent_stf_spacing,
                                          self._ent_stf_type,self._btn_shell_stf_section_long_stf]

        '''
        Shell, ring stiffener
        '''
        self._lab_shell_ring_stiffener =  ttk.Label(self._tab_prop, text='Ring stiffener properties [mm]')
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
                                      width = int(5*1), )
        self._ent_shell_ring_stf_tw = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_tw,
                                               )
        self._ent_shell_ring_stf_b = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_b,
                                              )
        self._ent_shell_ring_stf_tf = ttk.Entry(self._tab_prop, textvariable=self._new_shell_ring_stf_tf,
                                               )
        self._ent_shell_ring_stf_tripping_brackets = ttk.Entry(self._tab_prop,
                                                              textvariable=self._new_shell_ring_stf_tripping_brackets,
                                               )

        self._ent_shell_ring_stf_type = ttk.OptionMenu(self._tab_prop, self._new_shell_ring_stf_type,'T',
                                                      *['T', 'FB', 'L', 'L-bulb'])

        self._chk_shell_ring_frame_exclude = ttk.Checkbutton(self._tab_prop,
                                                            variable = self._new_shell_exclude_ring_stf,
                                                            command = self.calculation_domain_selected)
        self._btn_shell_stf_section_ring_stf = ttk.Button(self._tab_prop,text = 'STF',
                                                          command= lambda id= "ring stf":
                                                          self.on_open_structure_window(id))
        self._shell_ring_stf_gui_items = [self._lab_shell_ring_stiffener,self._ent_shell_ring_stf_hw,
                                          self._ent_shell_ring_stf_tw,self._ent_shell_ring_stf_b,
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
        self._ent_shell_ring_stf_type = ttk.OptionMenu(self._tab_prop, self._new_shell_ring_frame_type,'T',
                                                      *['T', 'FB', 'L', 'L-bulb'])
        self._chk_shell_ring_frame_exclude = ttk.Checkbutton(self._tab_prop,
                                                            variable = self._new_shell_exclude_ring_frame,
                                                            command = self.calculation_domain_selected)
        self._btn_shell_stf_section_ring_frame = ttk.Button(self._tab_prop, text='STF',command= lambda id= "ring frame": self.on_open_structure_window(id))
        self._shell_ring_frame_gui_items = [self._lab_shell_ring_stiffener, self._ent_shell_ring_frame_hw,
                                          self._ent_shell_ring_frame_tw, self._ent_shell_ring_frame_b,
                                          self._ent_shell_ring_frame_tf, self._ent_shell_ring_frame_tripping_brackets,
                                            self._ent_shell_ring_frame_l_between_girders,
                                            self._ent_shell_ring_stf_type, self._chk_shell_ring_frame_exclude,
                                            self._btn_shell_stf_section_ring_frame]

        '''
        Shell/panel load data
        '''

        self._lab_shell_loads =  ttk.Label(self._tab_prop, text='Load data, compression pressure,\n stresses and '
                                                              'forces negative.',
                                                   )
        self._new_shell_stress_or_force = tk.IntVar()
        self._new_shell_stress_or_force.set(1)

        self._ent_shell_force_input = ttk.Radiobutton(self._tab_prop, text="Force input",
                                                     variable=self._new_shell_stress_or_force, value=1,
                                                     command = self.calculation_domain_selected)
        self._ent_shell_stress_input = ttk.Radiobutton(self._tab_prop, text="Stress input",
                                                      variable=self._new_shell_stress_or_force, value=2,
                                                      command = self.calculation_domain_selected)

        self._new_shell_Nsd = tk.DoubleVar()
        self._new_shell_Msd = tk.DoubleVar()
        self._new_shell_Tsd = tk.DoubleVar()
        self._new_shell_Qsd = tk.DoubleVar()
        self._new_shell_psd = tk.DoubleVar()
        self._new_shell_Nsd.set(500000)
        self._new_shell_Msd.set(500000)
        self._new_shell_Tsd.set(40000)
        self._new_shell_Qsd.set(1500)
        self._new_shell_psd.set(-0.2)

        self._new_shell_uls_or_als = tk.StringVar()
        self._new_shell_end_cap_pressure_included = tk.StringVar()
        self._new_shell_fab_ring_stf = tk.StringVar()
        self._new_shell_fab_ring_frame = tk.StringVar()
        self._new_shell_uls_or_als.set('ULS')
        self._new_shell_end_cap_pressure_included.set('not included in axial force')

        self._new_shell_fab_ring_stf.set('Fabricated')
        self._new_shell_fab_ring_frame.set('Cold formed')

        self._lab_shell_limit_state =  ttk.Label(self._tab_prop, text='Limit state:', font=self._text_size['Text 9 bold'],
                                                )
        self._lab_shell_en_cap_pressure =  ttk.Label(self._tab_prop, text='End cap pressure is', font=self._text_size['Text 8'],
                                                )
        self._lab_shell_fab_stf =  ttk.Label(self._tab_prop, text='Fab. method ring stf.:', font=self._text_size['Text 8'],
                                                )
        self._lab_shell_fab_frame =  ttk.Label(self._tab_prop, text='Fab. method ring gird.:', font=self._text_size['Text 8'],
                                                )

        self._new_shell_sasd = tk.DoubleVar()
        self._new_shell_smsd = tk.DoubleVar()
        self._new_shell_tTsd = tk.DoubleVar()
        self._new_shell_tQsd = tk.DoubleVar()
        self._new_shell_shsd = tk.DoubleVar()

        self._ent_shell_uls_or_als = ttk.OptionMenu(self._tab_prop, self._new_shell_uls_or_als,'ULS', *['ULS', 'ALS'])
        self._ent_shell_end_cap_pressure_included = ttk.OptionMenu(self._tab_prop,
                                                                  self._new_shell_end_cap_pressure_included,
                                                                   'included in axial force',
                                                                  *['not included in axial force',
                                                                    'included in axial force'])
        self._ent_shell_fab_ring_stf = ttk.OptionMenu(self._tab_prop, self._new_shell_fab_ring_stf,'Fabricated',
                                                     *['Fabricated', 'Cold formed'])
        self._ent_shell_fab_ring_frame = ttk.OptionMenu(self._tab_prop, self._new_shell_fab_ring_frame,'Fabricated',
                                                       *['Fabricated', 'Cold formed'])
        self._ent_shell_yield = ttk.Entry(self._tab_prop, textvariable=self._new_shell_yield,
                                               )

        self._ent_shell_Nsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Nsd,
                                               width=int(5 * 1), )
        self._ent_shell_Msd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Msd,
                                               width=int(5 * 1), )
        self._ent_shell_Tsd  = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Tsd,
                                               width=int(5 * 1), )
        self._ent_shell_Qsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_Qsd,
                                               width=int(5 * 1), )
        self._ent_shell_psd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_psd,
                                               width=int(5 * 1), )

        self._ent_shell_sasd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_sasd,
                                               width=int(5 * 1), )
        self._ent_shell_smsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_smsd,
                                               width=int(5 * 1), )
        self._ent_shell_tTsd  = ttk.Entry(self._tab_prop, textvariable=self._new_shell_tTsd,
                                               width=int(5 * 1), )
        self._ent_shell_tQsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_tQsd,
                                               width=int(5 * 1), )
        self._new_shell_psd = self._new_shell_psd
        self._ent_shell_shsd = ttk.Entry(self._tab_prop, textvariable=self._new_shell_shsd,
                                               width=int(5 * 1), )

        self._shell_loads_other_gui_items = [self._lab_shell_loads, self._ent_shell_force_input,
                                              self._ent_shell_stress_input]
        self._shell_loads_forces_gui_items = [self._ent_shell_Nsd, self._ent_shell_Msd,
                                              self._ent_shell_Tsd, self._ent_shell_Qsd, self._ent_shell_psd]
        self._shell_loads_stress_gui_items = [self._ent_shell_sasd, self._ent_shell_smsd,self._ent_shell_tTsd,
                                              self._ent_shell_tQsd, self._ent_shell_psd,self._ent_shell_shsd]
        self._shell_other_gui_items = [self._ent_shell_end_cap_pressure_included, self._ent_shell_uls_or_als,
                                       self._ent_shell_fab_ring_stf, self._ent_shell_fab_ring_frame,
                                       self._lab_shell_limit_state,
                                       self._lab_shell_en_cap_pressure,self._lab_shell_fab_stf,
                                       self._lab_shell_fab_frame,self._ent_shell_yield,self._lab_yield]

        self._shell_exclude_ring_stf = tk.Frame(self._tab_prop, height=10, bg="black", colormap="new", )
        self._shell_exclude_ring_frame = tk.Frame(self._tab_prop, height=10, bg="black", colormap="new")

        ''' END shell input '''


        prop_vert_start = 0.01
        types_start = 0.005208333

        options = list(CylinderAndCurvedPlate.geomeries.values()) # Shell geometry selection [string]
        self._shell_geometries_map = CylinderAndCurvedPlate.geomeries_map  # Shell geometry selection string : int
        self._current_calculation_domain = 'Flat plate, stiffened'
        self._unit_informations_dimensions = list()

        self._ent_calculation_domain = ttk.OptionMenu(self._tab_prop, self._new_calculation_domain,options[0], *options,
                                                     command=self.calculation_domain_selected)

        ttk.Label(self._tab_prop, text='Structural and calculation properties input below:',
                 font=self._text_size['Text 9 bold'],
                  ).place(rely=prop_vert_start-delta_y*2.1,relx=types_start,
                                                  anchor = tk.NW)
        ttk.Label(self._tab_prop, text='Select calculation domain ->',
                 font=self._text_size['Text 10 bold'],
                 ).place(rely=prop_vert_start, relx=types_start,
                                               anchor=tk.NW)
        self._ent_calculation_domain.place(rely=prop_vert_start, relx=types_start + delta_x*5)



        # --- Compartment/tank load input and information ---
        load_vert_start = 0.05#frame_horizontal -0.03

        ttk.Label(self._tab_comp,text = 'Selected compartment from box below:',  )\
            .place(relx=types_start, rely=load_vert_start + 8*delta_y)

        self._selected_tank = ttk.Label(self._tab_comp,text='', font = 'Verdana 20 bold')
        self._selected_tank.place(relx=0.3, rely=load_vert_start + 10*delta_y)

        self._compartments_listbox = tk.Listbox(self._tab_comp, height = int(10 * 1),
                                               width = int(5 * 1),
                                               font=self._text_size["Text 10 bold"]
                                               ,
                                                selectmode = 'extended' )
        self._compartments_listbox.place(relx=types_start, rely=load_vert_start + 10*delta_y)
        self._compartments_listbox.bind('<<ListboxSelect>>', self.button_1_click_comp_box)


        ttk.Button(self._tab_comp, text="Set compartment\n""properties.",command = self.update_tank,
                  style = "Bold.TButton")\
            .place(relx=types_start + delta_x*4, rely=load_vert_start + delta_y * 10, relwidth = 0.3)

        ttk.Button(self._tab_comp, text="Delete all tanks", command=self.delete_all_tanks,
                  style = "Bold.TButton").place(relx=types_start + delta_x*4, rely=load_vert_start + delta_y * 12,
                                                relwidth = 0.3)


        self._ent_content_type = ttk.OptionMenu(self._tab_comp, self._new_content_type, list(self._tank_options.keys())[0],*list(self._tank_options.keys()),
                                               command=self.tank_density_trace)
        ent_width = 10

        self._ent_overpressure = ttk.Entry(self._tab_comp, textvariable = self._new_overpresure,
                                         width = int(ent_width * 1),
                                          )

        self._ent_density = ttk.Entry(self._tab_comp, textvariable = self._new_density,
                                    width = int(ent_width * 1),
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
        ttk.Label(self._tab_comp, text = '',  )\
            .place(relx=0.052083333, rely=comp_ent_y + 3.4*comp_dy)
        ttk.Label(self._tab_comp, text='Tank content :', font = self._text_size['Text 8'], )\
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 4.5)
        self._ent_content_type.place(relx= comp_ent_x+0.35*comp_dx, rely=comp_ent_y + comp_dy * 4.5)
        ttk.Label(self._tab_comp, text='Tank density [kg/m^3]:', font = self._text_size['Text 8'], )\
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 6)
        self._ent_density.place(relx=comp_ent_x+0.4*comp_dx, rely=comp_ent_y + comp_dy * 6)
        ttk.Label(self._tab_comp, text='Overpressure [Pa]:', font = self._text_size['Text 8'], )\
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 7)
        self._ent_overpressure.place(relx=comp_ent_x+0.4*comp_dx, rely=comp_ent_y + comp_dy * 7)
        ttk.Label(self._tab_comp, text='Max elevation [m]:', font = self._text_size['Text 8'], )\
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 8)
        self._ent_max_el.place(relx=comp_ent_x+0.4*comp_dx, rely=comp_ent_y + comp_dy * 8)
        ttk.Label(self._tab_comp, text='Min elevation [m]:', font = self._text_size['Text 8'], )\
            .place(relx=hor_start, rely=comp_ent_y + comp_dy * 9)
        self._ent_min_el.place(relx=comp_ent_x+0.4*comp_dx, rely=comp_ent_y + comp_dy * 9)
        self._tank_acc_label = ttk.Label(self._tab_comp, text = 'Acceleration [m/s^2]: ',
                                        font = self._text_size['Text 8'], )
        self._tank_acc_label.place(relx=hor_start, rely=comp_ent_y + comp_dy * 10)


        # --- button to create compartments and define external pressures ---

        try:
            img_file_name = 'img_int_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._int_button = tk.Button(self._tab_comp,image = photo,command=self.grid_find_tanks, bg = 'white')
            self._int_button.image = photo
            self._int_button.place(relx=types_start  +delta_x, rely=load_vert_start + delta_y*3,
                                   relheight = 0.07, relwidth = 0.6)
        except TclError:
            tk.Button(self._tab_comp, text='New tanks - start search \n'
                                  'to find compartments', command=self.grid_find_tanks,
                      bg = self._button_bg_color, fg = self._button_fg_color, ) \
                .place(relx=types_start, rely=load_vert_start + 1.55 * delta_y,
                       relheight=0.044, relwidth=0.3)

        show_compartment = ttk.Button(self._tab_comp, text='Display current\n compartments',
                                     command=self.grid_display_tanks,
                                  style = "Bold.TButton")
        show_compartment.place(relx=types_start + delta_x*4, rely=load_vert_start + delta_y * 14, relwidth = 0.3)

        try:
            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)

            self._ext_button = tk.Button(self._tab_comp,image=photo, command = self.on_show_loads,
                                         bg = 'white')
            self._ext_button.image = photo
            self._ext_button.place(relx=types_start + delta_x, rely=load_vert_start,
                                   relheight = 0.07, relwidth = 0.6)
        except TclError:
            tk.Button(self._tab_comp, text='New external load window \nsea - static/dynamic',
                      command=self.on_show_loads
                      )\
                .place(relx=ent_x+delta_x*1.5, rely=load_vert_start+1.55*delta_y,
                                   relheight = 0.044, relwidth = 0.11)

        lc_x, lc_x_delta, lc_y, lc_y_delta = 0.786458333, 0.015625, 0.12037037, 0.023148148

        # --- infomation on accelerations ----
        ttk.Label(self._main_fr,text='Static and dynamic accelerations',
                  )\
            .place(relx=lc_x, rely=lc_y - 5 * lc_y_delta)
        ttk.Label(self._main_fr,text='Static acceleration [m/s^2]: ',
                  )\
            .place(relx=lc_x, rely=lc_y - 4 * lc_y_delta)
        ttk.Label(self._main_fr,text='Dyn. acc. loaded [m/s^2]:',
                 )\
            .place(relx=lc_x, rely=lc_y - 3 * lc_y_delta)
        ttk.Label(self._main_fr,text='Dyn. acc. ballast [m/s^2]:',
                 )\
            .place(relx=lc_x, rely=lc_y - 2 * lc_y_delta)
        self._new_dyn_acc_loaded = tk.DoubleVar()
        self._new_dyn_acc_ballast = tk.DoubleVar()
        self._new_static_acc = tk.DoubleVar()
        self._new_static_acc.set(9.81), self._new_dyn_acc_loaded.set(0), self._new_dyn_acc_ballast.set(0)
        shift_x_acc = 0.08
        ttk.Entry(self._main_fr, textvariable = self._new_static_acc,width = 10,
                 )\
            .place(relx=lc_x+shift_x_acc, rely=lc_y - 4 * lc_y_delta)
        ttk.Entry(self._main_fr, textvariable = self._new_dyn_acc_loaded,width = 10,
                 )\
            .place(relx=lc_x+shift_x_acc , rely=lc_y - 3 * lc_y_delta)
        ttk.Entry(self._main_fr, textvariable = self._new_dyn_acc_ballast,width = 10,
                 )\
            .place(relx=lc_x+shift_x_acc , rely=lc_y - 2 * lc_y_delta)
        ttk.Button(self._main_fr, text = 'Set\naccelerations', command = self.create_accelerations,
                   style = "Bold.TButton")\
            .place(relx=lc_x +shift_x_acc*1.5, rely=lc_y - 4 * lc_y_delta)

        # --- checkbuttons and labels ---
        self._dnv_a_chk,self._dnv_b_chk  = tk.IntVar(),tk.IntVar()
        self._tank_test_chk,self._manual_chk = tk.IntVar(),tk.IntVar()
        self._check_button_load_comb = [self._dnv_a_chk,self._dnv_b_chk, self._tank_test_chk, self._manual_chk]
        self._active_label = ttk.Label(self._main_fr, text = '',
                                      )
        self._active_label.place(relx=lc_x+lc_x_delta*10,rely=lc_y-lc_y_delta*5)
        ttk.Label(self._main_fr, text='Combination for line (select line). Change with slider.: ',
                   )\
            .place(relx=lc_x, rely=lc_y + 2.5*delta_y)

        lc_y += 0.148148148
        self._combination_slider = ttk.Scale(self._main_fr, from_=1, to=4, command=self.gui_load_combinations,length=400,
                                           orient = 'horizontal')
        ttk.Label(self._main_fr, text='1: DNV a)                    2: DNV b)                    3: TankTest        '
                                      '            4: Cylinder')\
            .place(relx=lc_x +0*lc_x_delta, rely=lc_y - 2*lc_y_delta)

        self._combination_slider.place(relx=lc_x +0*lc_x_delta, rely=lc_y - 3*lc_y_delta)
        self._combination_slider_map = {1:'dnva',2:'dnvb',3:'tanktest', 4: 'Cylinder'}
        ttk.Label(self._main_fr, text='Name:', )\
            .place(relx=lc_x + 0 * lc_x_delta, rely=lc_y)
        ttk.Label(self._main_fr, text='Stat LF', )\
            .place(relx=lc_x + 8.5 * lc_x_delta, rely=lc_y)
        ttk.Label(self._main_fr, text='Dyn LF', )\
            .place(relx=lc_x + 10.2 * lc_x_delta, rely=lc_y)
        ttk.Label(self._main_fr, text='Include?',font = self._text_size['Text 7'], )\
            .place(relx=lc_x + 11.8 * lc_x_delta, rely=lc_y)

        self._result_label_dnva = ttk.Label(self._main_fr, text='DNV a [Pa]: ',font='Text 8', )
        self._result_label_dnvb = ttk.Label(self._main_fr, text='DNV b [Pa]: ',font=self._text_size["Text 8"],
                                           )
        self._result_label_tanktest = ttk.Label(self._main_fr, text='Tank test [Pa]: ',font=self._text_size["Text 8"],
                                               )
        self._result_label_manual = ttk.Label(self._main_fr, text='Manual [Pa]: ',font=self._text_size["Text 8"],
                                             )
        self.results_gui_start = 0.6
        self._lab_pressure = ttk.Label(self._main_fr, text = 'Pressures for this line: \n(DNV a/b [loaded/ballast], tank test, manual)\n'
                               'Note that ch. 4.3.7 and 4.3.8 is accounted for.',font=self._text_size["Text 10"],
                 )
        self._lab_pressure.place(relx= 0.786458333, rely= self.results_gui_start)

        # --- optimize button ---
        ttk.Label(self._main_fr,text='Optimize selected line/structure (right click line):',
                 font = self._text_size['Text 9 bold'], )\
            .place(relx=lc_x, rely=lc_y - 7 * lc_y_delta)
        try:
            img_file_name = 'img_optimize.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._opt_button = tk.Button(self._main_fr,image=photo, command = self.on_optimize,
                                   bg = 'white', fg = self._button_fg_color)
            self._opt_button.image = photo
            self._opt_button.place(relx=lc_x, rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.098)
        except TclError:
            self._opt_button =tk.Button(self._main_fr, text='Optimize', command=self.on_optimize,
                      bg = self._button_bg_color, fg = self._button_fg_color)
            self._opt_button.place(relx=lc_x, rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.098)
        try:
            img_file_name = 'img_multi_opt.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._opt_button_mult = tk.Button(self._main_fr,image=photo, command = self.on_optimize_multiple,
                                        bg = self._button_bg_color, fg = self._button_fg_color)
            self._opt_button_mult.image = photo
            self._opt_button_mult.place(relx=lc_x+0.1, rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.065)
        except TclError:
            self._opt_button_mult= tk.Button(self._main_fr, text='MultiOpt', command=self.on_optimize_multiple,
                      bg = self._button_bg_color, fg = self._button_fg_color)
            self._opt_button_mult.place(relx=lc_x+0.1, rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.065)


        try:
            img_file_name = 'cylinder_opt.png'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._opt_cylinder = tk.Button(self._main_fr,image=photo, command = self.on_optimize_cylinder,
                                        bg = 'white', fg = 'white')
            self._opt_cylinder.image = photo
        except TclError:
            self._opt_cylinder = tk.Button(self._main_fr, text='Cylinder optimization',
                                           command=self.on_optimize_cylinder,
                      bg = self._button_bg_color, fg = self._button_fg_color)


        self._opt_button_span = ttk.Button(self._main_fr, text='SPAN', command=self.on_geometry_optimize,
                                           style = "Bold.TButton")
        self._opt_button_span.place(relx=lc_x + 0.167,rely=lc_y - 6 * lc_y_delta, relheight = 0.04,
                                    relwidth = 0.04)


        self._optimization_buttons = {'Flat plate, stiffened': [self._opt_button, self._opt_button_mult,
                                                                self._opt_button_span],
                                      'Flat plate, stiffened place': [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.098],
                                                   [lc_x+0.1, lc_y - 6 * lc_y_delta, 0.04, 0.065],
                                                   [lc_x + 0.167, lc_y - 6 * lc_y_delta, 0.04, 0.04]],
                                      'Flat plate, unstiffened': [],
                                      'Flat plate, unstiffened place': [],
                                      'Flat plate, stiffened with girder': [],
                                      'Flat plate, stiffened with girder place': [],

                                   'cylinder': [self._opt_cylinder],
                                   'cylinder place' : [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.175]]}

        # Load information button
        ttk.Button(self._main_fr, text='Load info', command=self.button_load_info_click,style = "Bold.TButton")\
           .place(relx=0.78,rely=0.7, relwidth = 0.04)

        # Load information button
        ttk.Button(self._main_fr, text='Load factors', command=self.on_open_load_factor_window,style = "Bold.TButton")\
           .place(relx=0.8225,rely=0.7, relwidth = 0.05)

        # PULS result information
        self._puls_information_button = ttk.Button(self._main_fr, text='PULS results for line',
                                                  command=self.on_puls_results_for_line,style = "Bold.TButton")
        self._puls_information_button.place(relx=0.875,rely=0.7, relwidth = 0.075)

        # Wight developement plot
        self._weight_button = ttk.Button(self._main_fr, text='Weights',
                                                  command=self.on_plot_cog_dev,style = "Bold.TButton")
        self._weight_button.place(relx=0.9525,rely=0.7, relwidth = 0.038)
        self.gui_structural_properties()  # Initiating the flat panel structural properties
        self.set_colors('default')  # Setting colors theme
        self._current_theme = 'default'

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
            #relx=x_canvas_place, rely=0,relwidth=0.523, relheight = 0.73
        elif theme == 'modelling':
            self._main_canvas.place_forget()
            x_canvas_place = 0.26
            self._main_canvas.place(relx=x_canvas_place, rely=0,relwidth=0.74, relheight = 0.99)
            tk.Misc.lift(self._main_canvas)
            self._gui_functional_look = 'modelling'
        elif theme == 'all items':
            self._gui_functional_look = 'all items'
            self._main_canvas.place_forget()
            x_canvas_place = 0.26
            self._main_canvas.place(relx=x_canvas_place, rely=0, relwidth=0.523, relheight=0.73)

        if theme not in ['modelling', 'all items']:
            self._style.configure("Bold.TButton", font=('Sans', '10', 'bold'))
            self._style.configure('TCheckbutton', background=self._general_color)
            self._style.configure('TFrame', background=self._general_color)
            self._style.configure('TLabel', background=self._general_color, foreground = self._color_text)
            self._style.configure('TScale', background=self._general_color)
            self._style.configure('TEntry', background=ent_bg)
            self._style.configure('TOptionMenu', background=ent_bg)
            self._style.configure("TMenubutton", background=ent_bg)
            self._style.configure('TRadiobutton', background=self._general_color, foreground='black')

            self._prop_canvas.configure(bg = self._general_color)
            self._main_canvas.configure(bg = self._general_color)
            self._result_canvas.configure(bg = self._general_color)

        # self._frame_viz_hor.configure(bg =self._color_text)
        # self._frame_viz_ver.configure(bg=self._color_text)

        self.update_frame()

    def gui_structural_properties(self, flat_panel_stf_girder = False, flat_unstf = False, flat_stf = True,
                                  shell = False, long_stf = False, ring_stf = False,
                                  ring_frame = False, force_input = False, stress_input = False):
        vert_start = 0.04
        hor_start = 0.02

        delta_y = 0.024
        delta_x = 0.13

        ent_relx = hor_start + 6*delta_x

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
            self._stf_button.place(relx=hor_start, rely=vert_start+ top_button_shift * delta_y)
            self._stress_button.place(relx=hor_start + delta_x*1.5, rely=vert_start+ top_button_shift * delta_y)
            self._fls_button.place(relx=hor_start + delta_x*3, rely=vert_start+ top_button_shift * delta_y)
            self.add_stucture.place(relx=hor_start + delta_x*4.5, rely=vert_start+ top_button_shift * delta_y,
                                    relheight = 0.065, relwidth = 0.39)

            # Input fields
            if any([shell, long_stf, ring_stf, ring_frame, force_input, stress_input]):
                return

            self._flat_gui_headlines[0].place(relx=hor_start, rely=vert_start + 3 * delta_y)

            idx = 4
            for pl_lab, pl_ent in zip(self._flat_gui_lab_plate, self._flat_gui_plate):
                pl_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                pl_ent.place(relx=hor_start + 3*delta_x, rely=vert_start + idx * delta_y)
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
                load_ent.place(relx=hor_start + 3*delta_x, rely=vert_start + idx * delta_y)
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

            idx = idx_now
            self._flat_gui_headlines[5].place(relx=hor_start + 0 * delta_x, rely=vert_start + idx * delta_y)
            idx += 1
            self._lab_buckling_method.place(relx=hor_start + 0 * delta_x, rely=vert_start + idx * delta_y)
            self._buckling_method.place(relx=hor_start + 4 * delta_x, rely=vert_start + idx * delta_y)
            idx += 1
            if flat_panel_stf_girder:
                self._flat_gui_headlines[7].place(relx=hor_start + 6 * delta_x, rely=vert_start + idx * delta_y)
            if flat_stf:
                self._flat_gui_headlines[6].place(relx=hor_start + 4*delta_x, rely=vert_start + idx * delta_y)
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
                self._flat_gui_girder_moment_factor[0].place(relx=hor_start + 0 * delta_x, rely=vert_start + idx * delta_y)
                self._flat_gui_girder_moment_factor[1].place(relx=hor_start + 6 * delta_x, rely=vert_start + idx * delta_y,
                                                             relwidth = 0.08)
                self._flat_gui_girder_moment_factor[2].place(relx=hor_start + 7 * delta_x, rely=vert_start + idx * delta_y,
                                                             relwidth = 0.08)
                idx += 1

            for buckling_lab, buckling_ent in zip(self._flat_gui_buc_lab_common, self._flat_gui_buc_common_opt):
                buckling_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                buckling_ent.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1
            for buckling_lab, buckling_ent in zip(self._flat_gui_lab_buckling, self._flat_gui_buckling):
                buckling_lab.place(relx=hor_start, rely=vert_start + idx * delta_y)
                buckling_ent.place(relx=hor_start + 5 * delta_x, rely=vert_start + idx * delta_y)
                idx += 1

            self._puls_run_all.place(relx=hor_start + 6 * delta_x, rely=vert_start + (idx-2) * delta_y)

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
            ent_geo_y -= delta_y
            self._lab_shell.place(relx=hor_start, rely=ent_geo_y+ delta_y)

            tmp_unit_info = list()
            for lab in ['Thickness, t', 'Radius, r', 'Ring dist., l', 'Shell len., L', 'Tot len., Lc', 'k-factor, k',
                        'Material factor']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):
                lab.place(relx=hor_start + idx * delta_x,rely=ent_geo_y+ delta_y*2)
                self._unit_informations_dimensions.append(lab)

            for idx, entry in enumerate(self._shell_gui_items[1:]):

                entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y*3, relwidth=geo_ent_width)

            ent_geo_y += delta_y*3

        if long_stf:

            self._lab_shell_long_stiffener.place(relx=hor_start, rely=ent_geo_y+ delta_y)

            tmp_unit_info = list()
            for lab in ['Web, hw', 'Web, tw', 'Flange b', 'Flange, tw', 'Spacing, s', 'Stf. type', 'Load section']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):
                lab.place(relx=hor_start + idx * delta_x,rely=ent_geo_y+ delta_y*2)
                self._unit_informations_dimensions.append(lab)

            for idx, entry in enumerate(self._shell_long_stf_gui_items[1:]):
                entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y+ delta_y*3, relwidth=geo_ent_width)

            self._unit_informations_dimensions.append(self._lab_shell_long_stiffener)
            ent_geo_y += delta_y*3

        if ring_stf:
            self._lab_shell_ring_stiffener.place(relx=hor_start, rely=ent_geo_y+ delta_y*1)
            tmp_unit_info = list()
            for lab in ['Web, hw', 'Web, tw', 'Flange, b', 'Flange, tw','tr. br. dist', 'Stf. type',
                        'Exclude', 'Load section prop.']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):

                if idx in [6,7]:
                    lab.place(relx=hor_start + (idx-6) * delta_x*3, rely=ent_geo_y + delta_y * 4)
                else:
                    lab.place(relx=hor_start + idx * delta_x,rely=ent_geo_y+ delta_y*2)
                self._unit_informations_dimensions.append(lab)
            self._unit_informations_dimensions.append(self._lab_shell_ring_stiffener)

            for idx, entry in enumerate(self._shell_ring_stf_gui_items[1:]):
                if idx in [6,7]:
                    entry.place(relx=hor_start + (idx-6) * delta_x*4 + delta_x, rely=ent_geo_y+ delta_y*4, relwidth=geo_ent_width)
                else:
                    entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y+ delta_y*3, relwidth=geo_ent_width)

            if self._new_shell_exclude_ring_stf.get():
                self._shell_exclude_ring_stf.place(relx=0.005, rely=ent_geo_y+ delta_y*3.15, relwidth=0.9)
                self._unit_informations_dimensions.append(self._shell_exclude_ring_stf)

            ent_geo_y += delta_y*4

        if ring_frame:
            self._lab_shell_ring_frame.place(relx=hor_start, rely=ent_geo_y+ delta_y*1)

            for idx, entry in enumerate(self._shell_ring_frame_gui_items[1:]):
                if idx in [7, 8]:
                    entry.place(relx=hor_start + (idx - 7) * delta_x * 4 + delta_x, rely=ent_geo_y + delta_y * 4,
                                relwidth=geo_ent_width)
                else:
                    entry.place(relx=hor_start + idx * delta_x, rely=ent_geo_y + delta_y * 3, relwidth=geo_ent_width)

            tmp_unit_info = list()
            for lab in ['Web, hw', 'Web, tw', 'Flange, b', 'Flange, tw', 'tr. br. dist', 'L bet. Gird.',
                        'Stf. type', 'Exclude', 'Load section prop.']:
                tmp_unit_info.append(ttk.Label(self._tab_prop, text=lab))

            for lab, idx in zip(tmp_unit_info, range(len(tmp_unit_info))):
                if idx in [7,8]:
                    lab.place(relx=hor_start + (idx-7) * delta_x*3, rely=ent_geo_y + delta_y * 4)
                else:
                    lab.place(relx=hor_start + idx * delta_x,rely=ent_geo_y+ delta_y*2)

                self._unit_informations_dimensions.append(lab)
            self._unit_informations_dimensions.append(self._lab_shell_ring_frame)
            if self._new_shell_exclude_ring_frame.get():
                self._shell_exclude_ring_frame.place(relx=0.005, rely=ent_geo_y+ delta_y*3.15, relwidth=0.9)
                self._unit_informations_dimensions.append(self._shell_exclude_ring_frame)

            ent_geo_y += delta_y*3

        if not any([flat_panel_stf_girder, flat_stf, flat_unstf]):
            # Other data
            '''
                self._shell_other_gui_items = [self._ent_shell_end_cap_pressure_included, self._ent_shell_uls_or_als,
                                   self._ent_shell_fab_ring_stf, self._ent_shell_fab_ring_frame]
            '''
            other_count = 2
            other_dy = 1.25
            other_x = 5.8
            other_text_shift = 2.5
            self._lab_shell_limit_state.place(relx=hor_start,
                                             rely=ent_geo_y + delta_y*2.2)
            self._ent_shell_uls_or_als.place(relx=hor_start+ 1.6  * delta_x,
                                             rely=ent_geo_y + delta_y*2.2,
                                             relwidth=geo_ent_width*2)

            self._lab_yield.place(relx=hor_start + 4  * delta_x,
                                             rely=ent_geo_y + delta_y*3)
            self._ent_shell_yield.place(relx=hor_start+ 6  * delta_x,
                                             rely=ent_geo_y + delta_y*3, relwidth=geo_ent_width)
            other_count+= 1
            if ring_stf:
                self._lab_shell_fab_stf.place(relx=hor_start + 4  * delta_x,
                                                   rely=ent_geo_y + delta_y*4)
                self._ent_shell_fab_ring_stf.place(relx = hor_start + 6  * delta_x,
                                                   rely=ent_geo_y + delta_y*4, relwidth=geo_ent_width*1.9)
                other_count += 1

            if ring_frame:
                self._lab_shell_fab_frame.place(relx=hor_start + 4  * delta_x,
                                                   rely=ent_geo_y + delta_y*5)
                self._ent_shell_fab_ring_frame.place(relx=hor_start + 6  * delta_x,
                                                   rely=ent_geo_y + delta_y*5, relwidth=geo_ent_width*1.9)
                other_count += 1

            if self._shell_geometries_map[self._new_calculation_domain.get()] in [1,5]:
                other_count += 1
                self._lab_shell_en_cap_pressure.place(relx=hor_start+ 5.5  * delta_x- delta_x*other_text_shift,
                                                                rely= ent_geo_y + delta_y*other_count*other_dy,
                                                                relwidth=0.09)
                self._ent_shell_end_cap_pressure_included.place(relx=hor_start+ other_x  * delta_x,
                                                                rely= ent_geo_y + delta_y*other_count*other_dy,
                                                                relwidth=0.09)

            # Load data
            ent_geo_y += 3.3 * delta_y
            #self._lab_shell_loads.place(relx=hor_start, rely=ent_geo_y - delta_y*1.5)
            self._ent_shell_stress_input.place(relx=hor_start, rely=ent_geo_y)
            if 'shell' in self._new_calculation_domain.get():
                self._ent_shell_force_input.place(relx=hor_start + 2 * delta_x, rely=ent_geo_y)
            else:
                self._new_shell_stress_or_force.set(2)

            lab_force = ['Axial', 'Bending', 'Torsional','Shear', 'Lateral']
            lab_force_unit = ['kN', 'kNm', 'kNm', 'kN', 'N/mm2']
            lab_stress = ['Axial', 'Bending', 'Torsional', 'Shear',
                          'Lateral', 'Add hoop']
            lab_stress_unit = ['N/mm2', 'N/mm2', 'N/mm2', 'N/mm2', 'N/mm2', 'N/mm2']
            to_use = self._shell_loads_forces_gui_items if self._new_shell_stress_or_force.get() == 1 \
                else self._shell_loads_stress_gui_items

            lab_to_use =  [lab_force, lab_force_unit] if self._new_shell_stress_or_force.get() == 1\
                else [lab_stress, lab_stress_unit]

            tmp_unit_info = list()
            tmp_unit_info_unit = list()
            [tmp_unit_info.append(ttk.Label(self._tab_prop, text=val))
             for val in lab_to_use[0]]
            [tmp_unit_info_unit.append(ttk.Label(self._tab_prop, text=val))
             for val in lab_to_use[1]]

            for idx,lab in enumerate(tmp_unit_info):
                lab.place(relx=hor_start, rely=ent_geo_y + (idx+1)*delta_y)
                self._unit_informations_dimensions.append(lab)

            for idx, entry in enumerate(to_use):
                entry.place(relx=hor_start + 1.5*delta_x,
                            rely=ent_geo_y + (idx+1)*delta_y, relwidth=geo_ent_width)

            for idx, lab in enumerate(tmp_unit_info_unit):
                lab.place(relx=hor_start + 2.5*delta_x,
                          rely=ent_geo_y + (idx+1)*delta_y)
                self._unit_informations_dimensions.append(lab)

            for dom in ['Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder']:
                for btn, placement in zip(self._optimization_buttons[dom],
                                          self._optimization_buttons[dom + ' place']):
                    btn.place_forget()

            for btn, placement in zip(self._optimization_buttons['cylinder'],
                                      self._optimization_buttons['cylinder' + ' place']):
                btn.place(relx=placement[0], rely=placement[1], relheight=placement[2], relwidth=placement[3])


    def calculation_domain_selected(self, event = None):
        '''
        ['Stiffened panel, flat', 'Unstiffened shell (Force input)', 'Unstiffened panel (Stress input)',
        'Longitudinal Stiffened shell  (Force input)', 'Longitudinal Stiffened panel (Stress input)',
        'Ring Stiffened shell (Force input)', 'Ring Stiffened panel (Stress input)',
        'Orthogonally Stiffened shell (Force input)', 'Orthogonally Stiffened panel (Stress input)']
        '''

        to_process = [self._puls_run_all, self._lab_buckling_method,
                      self._buckling_method, self._lab_yield,
                      self._lab_mat_fac,self._structure_types_label, self._button_str_type, self._ent_structure_type,
                      self._lab_structure_type, self._lab_kpp, self._lab_kps, self._lab_km1, self._lab_km2,
                      self._lab_stf_type, self._lab_press_side, self._ent_pressure_side,
                      self._lab_puls_input, self._lab_puls_up_supp, self._lab_puls_acceptance,
                      self._lab_puls_uf, self._lab_puls_int_gt, self._lab_puls_cont_sniped, self._lab_span, self._lab_s,
                      self._ent_puls_sp_or_up, self._ent_puls_method, self._ent_puls_uf, self._ent_puls_panel_boundary,
                      self._ent_puls_stf_end_type,
                      self._stf_button, self._stress_button,self._fls_button]

        to_process = to_process+self._shell_gui_items+self._shell_long_stf_gui_items+self._shell_ring_stf_gui_items+\
                     self._shell_ring_frame_gui_items+self._shell_loads_other_gui_items+\
                     self._shell_loads_forces_gui_items+self._shell_loads_stress_gui_items+\
                     self._unit_informations_dimensions + self._shell_other_gui_items+ self._flat_gui_plate + \
                     self._flat_gui_lab_plate + self._flat_gui_lab_stf+self._flat_gui_stf + self._flat_gui_girder + \
                     self._flat_gui_lab_loads + self._flat_gui_loads  + self._flat_gui_lab_os_c101_provisions + \
                     self._flat_gui_os_c101_provisions + \
                     self._flat_gui_lab_buckling + self._flat_gui_buckling + self._flat_gui_headlines + \
                     self._flat_gui_buc_lab_common+ self._flat_gui_buc_common_opt+ self._flat_gui_buc_girder_opt+\
                     self._flat_gui_buc_lab_stf_girder+ self._flat_gui_buc_stf_opt+ self._flat_gui_girder_moment_factor
        for item in to_process:
            item.place_forget()

        if event is not None:
            self._new_shell_exclude_ring_stf.set(False)
            self._new_shell_exclude_ring_frame.set(False)
        '''
            geomeries = {1:'Unstiffened shell (Force input)', 
                    2:'Unstiffened panel (Stress input)',
                    3:'Longitudinal Stiffened shell  (Force input)',
                    4:'Longitudinal Stiffened panel (Stress input)',
                    5:'Ring Stiffened shell (Force input)',
                    6:'Ring Stiffened panel (Stress input)',
                    7:'Orthogonally Stiffened shell (Force input)',
                    8:'Orthogonally Stiffened panel (Stress input)'}
        '''
        if self._new_calculation_domain.get() == 'Flat plate, unstiffened':
            self._new_puls_sp_or_up.set('UP')
            self.gui_structural_properties(flat_unstf = True, flat_stf = False)

        elif self._new_calculation_domain.get() == 'Flat plate, stiffened':
            self._new_puls_sp_or_up.set('SP')
            self.gui_structural_properties(flat_stf = True)

        elif self._new_calculation_domain.get() == 'Flat plate, stiffened with girder':
            self._new_puls_sp_or_up.set('SP')
            self.gui_structural_properties(flat_panel_stf_girder = True, flat_stf = True)

        elif self._new_calculation_domain.get() in ['Unstiffened shell (Force input)',
                                                    'Unstiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf = False, flat_panel_stf_girder = False,
                                           shell=True, long_stf=False, ring_stf=False, ring_frame=False)
        elif self._new_calculation_domain.get() in ['Longitudinal Stiffened shell  (Force input)',
                                                    'Longitudinal Stiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf = False, flat_panel_stf_girder = False,
                                           shell=True, long_stf=True, ring_stf=False, ring_frame=False)
        elif self._new_calculation_domain.get() in ['Ring Stiffened shell (Force input)',
                                                    'Ring Stiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf = False, flat_panel_stf_girder = False,
                                           shell=True, long_stf=False, ring_stf=True, ring_frame=True)
        elif self._new_calculation_domain.get() in ['Orthogonally Stiffened shell (Force input)',
                                                    'Orthogonally Stiffened panel (Stress input)']:
            self.gui_structural_properties(flat_unstf=False, flat_stf = False, flat_panel_stf_girder = False,
                                           shell=True, long_stf=True, ring_stf=True, ring_frame=True)

        if self._line_is_active and self._active_line in self._line_to_struc.keys():
            if event == None and self._line_to_struc[self._active_line][5] is not None:
                mapper ={1: 'Force', 2: 'Stress'}
                load = mapper[self._new_shell_stress_or_force.get()]
                struc_obj = self._line_to_struc[self._active_line][5]
                if self._new_shell_stress_or_force.get() == 1:
                    forces = [self._new_shell_Nsd.get(), self._new_shell_Msd.get(), \
                              self._new_shell_Tsd.get(), self._new_shell_Qsd.get()]
                    sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                        stresses=None, forces=forces, geometry=struc_obj.geometry, shell_t=self._new_shell_thk.get(),
                        shell_radius=self._new_shell_radius.get(), shell_spacing=self._new_stf_spacing.get(),
                        hw=self._new_stf_web_h.get(), tw=self._new_stf_web_t.get(), b=self._new_stf_fl_w.get(),
                        tf=self._new_stf_fl_t.get(), CylinderAndCurvedPlate=CylinderAndCurvedPlate)
                    self._new_shell_sasd.set(sasd)
                    self._new_shell_smsd.set(smsd)
                    self._new_shell_tTsd.set(tTsd)
                    self._new_shell_tQsd.set(tQsd)
                    # self._new_shell_shsd.set(0)
                else:
                    stresses = [self._new_shell_sasd.get(), self._new_shell_smsd.get(), self._new_shell_tTsd.get(),
                                self._new_shell_tQsd.get(), self._new_shell_shsd.get()]
                    sasd, smsd, tTsd, tQsd, shsd = stresses
                    Nsd, Msd, Tsd, Qsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                        stresses=stresses, geometry=struc_obj.geometry, shell_t=self._new_shell_thk.get(),
                        shell_radius=self._new_shell_radius.get(), shell_spacing=self._new_stf_spacing.get(),
                        hw=self._new_stf_web_h.get(), tw=self._new_stf_web_t.get(), b=self._new_stf_fl_w.get(),
                        tf=self._new_stf_fl_t.get(), CylinderAndCurvedPlate=CylinderAndCurvedPlate)
                    self._new_shell_Nsd.set(Nsd)
                    self._new_shell_Msd.set(Msd)
                    self._new_shell_Tsd.set(Tsd)
                    self._new_shell_Qsd.set(Qsd)

        self._current_calculation_domain = self._new_calculation_domain.get()
        # Setting the correct optmization buttons

    def puls_run_all_lines(self, line_given = None):
        progress = ttk.Progressbar(self._tab_prop, mode='indeterminate')
        progress.place(relx = 0.85, rely = 0.9, relwidth = 0.1)
        progress.start()
        if self._PULS_results is None:
            self._PULS_results = PULSpanel()
        if self._PULS_results.puls_sheet_location is None or not os.path.isfile(self._PULS_results.puls_sheet_location):
            tk.messagebox.showerror('No PULS excel sheet located', 'Set location of PULS excel sheet.\n'
                                                                            'Note that PULS excel may require 32 bit '
                                                                            'office.\n\n'
                                                                         'A sheet may be provided but does not exist'
                                                                            ' in :\n'
                                                                         + str(self._PULS_results.puls_sheet_location) +
                                    '\n\n A file dialogue will pop up after this message.')
            self._PULS_results.puls_sheet_location= \
                tk.filedialog.askopenfilename(parent=self._main_fr,title='Set location of PULS excel sheet.')
        if self._PULS_results.puls_sheet_location == '':
            tk.messagebox.showerror('No valid PULS sheet', 'No excel sheet was provided. Cannot run PULS.\n'
                                                           'Note that PULS excel may require 32 bit office.')
            return

        dict_to_run = {}
        result_lines = list(self._PULS_results.get_run_results().keys())

        if line_given == None:
            current_button = self._puls_run_all
            for line, data in self._line_to_struc.items():
                if line not in result_lines:
                    data[0].Plate.hw = data[0].Stiffener.hw
                    data[0].Plate.tw = data[0].Stiffener.tw
                    data[0].Plate.tw = data[0].Stiffener.b
                    data[0].Plate.tw = data[0].Stiffener.tf
                    dict_to_run[line] = data[0].Plate.get_puls_input()
                    dict_to_run[line]['Identification'] = line
                    dict_to_run[line]['Pressure (fixed)'] = self.get_highest_pressure(line)['normal']/1e6
        else:
            current_button = self._puls_run_one
            if line_given == '':
                return
            if line_given not in result_lines:
                dict_to_run[line_given] = self._line_to_struc[line_given][0].Plate.get_puls_input()
                dict_to_run[line_given]['Identification'] = line_given
                dict_to_run[line_given]['Pressure (fixed)'] = self.get_highest_pressure(line_given)['normal'] / 1e6


        if len(dict_to_run) > 0:

            #current_button.config(relief = 'sunken')
            self._PULS_results.set_all_to_run(dict_to_run)
            self._PULS_results.run_all()
            #current_button.config(relief='raised')
            current_button.config(text='PULS run or\nupdate all lines' if line_given == None else 'PULS\nRun one line')
            #current_button.config(bg=self._button_bg_color)
            for key, value in self._line_to_struc.items():
                value[0].need_recalc = True
        else:
            tk.messagebox.showinfo('Results avaliable', 'PULS results is already avaliable for this line or no '
                                                        'lines need update.')

        progress.stop()
        progress.destroy()
        self.update_frame()

    def trace_puls_uf(self, *args):
        if self._PULS_results is not None:
            pass

    def trace_material_factor(self, *args):
        try:
            self._new_puls_uf.set(1/self._new_material_factor.get())
        except (TclError, ZeroDivisionError):
            pass

    def trace_puls_up_or_sp(self, event = None):
        if self._new_puls_sp_or_up.get() == 'UP':
            vert_start = 0.1
            hor_start = 0.02
            delta_y = 0.04
            delta_x = 0.13
            ent_relx = hor_start + 6 * delta_x
            geo_ent_width = 0.05
            ent_geo_y = vert_start
            opt_width = 0.2
            shift_x = delta_x * 4
            lab_place = delta_y * 13

            self._ent_puls_up_boundary.place(relx=hor_start + shift_x, rely=vert_start + lab_place+ 2*delta_y,
                                        relwidth=opt_width)
        else:
            self._ent_puls_up_boundary.place_forget()

    def puls_run_one_line(self):
        self.puls_run_all_lines(self._active_line)
        self.update_frame()

    def resize(self, event):
        self.text_scale = 1#self._main_fr.winfo_width()/1920
        self._text_size = {'Text 14 bold': 'Verdana '+str(int(14*self.text_scale))+' bold',
                           'Text 16 bold': 'Verdana ' + str(int(16 * self.text_scale)) + ' bold',
                           'Text 18 bold': 'Verdana ' + str(int(18 * self.text_scale)) + ' bold',
                           'Text 12 bold': 'Verdana ' + str(int(12 * self.text_scale)) + ' bold',
                           'Text 10 bold': 'Verdana '+str(int(10*self.text_scale))+' bold',
                           'Text 9 bold': 'Verdana ' + str(int(9 * self.text_scale)) + ' bold',
                           'Text 8 bold': 'Verdana ' + str(int(8 * self.text_scale)) + ' bold',
                           'Text 8': 'Verdana ' + str(int(8 * self.text_scale)),
                           'Text 9': 'Verdana ' + str(int(8 * self.text_scale)),
                           'Text 7': 'Verdana ' + str(int(7 * self.text_scale)),
                           'Text 10': 'Verdana ' + str(int(10 * self.text_scale)),
                           'Text 7 bold': 'Verdana ' + str(int(7 * self.text_scale)) + ' bold'}
        #self.update_frame()

    def toggle_select_multiple(self, event = None):
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg='#E1E1E1')
            self._multiselect_lines = []
            self._toggle_btn.config(text='Toggle select\n'
                                         'multiple')
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg=self._general_color)
            self._toggle_btn.config(text = 'select lines')
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
                    #'structure_types': self._structure_types,
                    'zstar_optimization': self._new_zstar_optimization.get,
                    'puls buckling method': self._new_puls_method.get,
                    'puls boundary': self._new_puls_panel_boundary.get,
                    'puls stiffener end': self._new_buckling_stf_end_support.get,
                    'puls sp or up': self._new_puls_sp_or_up.get,
                    'puls up boundary': self._new_puls_up_boundary.get}


        set_var = obj_dict[var_to_set]()
        if var_to_set == 'mat_yield':
            set_var = set_var* 1e6
        elif var_to_set in ['spacing','plate_thk','stf_web_height','stf_web_thk',
                            'stf_flange_width','stf_flange_thk', 'span']:
            set_var = set_var/1000
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

                #dict[var_to_set][0] = set_var
                self.new_structure(toggle_multi=prop_dict, suspend_recalc=True if (idx+1) != no_of_lines else False)

    def gui_load_combinations(self,event):
        '''
        Initsializing and updating gui for load combinations.
        The fields are located left of the Canvas.
        :return:
        '''

        if all([self._line_is_active,self._active_line in self._line_to_struc.keys(),
                self._gui_functional_look == 'all items']):
            lc_x, lc_x_delta, lc_y, lc_y_delta = 0.791666667, 0.026041667, 0.287037037, 0.023148148

            #self._active_label.config(text=self._active_line)
            combination = self._combination_slider_map[int(self._combination_slider.get())]

            # removing label, checkbox and entry. setting created items to empty list.
            [[item.destroy() for item in items] for items in
             [self._lc_comb_created,self._comp_comb_created,self._manual_created, self._info_created]]
            self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created= [], [], [], []

            if self._line_to_struc[self._active_line][0].Plate.get_structure_type() == '':
                self._info_created.append(ttk.Label(self._main_fr, text='No structure type selected',
                                               font=self._text_size["Text 10 bold"], ))
                self._info_created[0].place(relx=lc_x , y = lc_y + 3*lc_y_delta)
            elif self._line_to_struc[self._active_line][5] is not None:
                pass
            elif combination != 'Cylinder':
                # creating new label, checkbox and entry. creating new list of created items.
                # finding loads applied to lines
                counter = 0

                if len(self._load_dict) != 0 and combination !='manual':
                    for load, data in self._load_dict.items():
                        if self._active_line in self._load_dict[load][1] and data[0].get_limit_state() == 'ULS':
                            name = (combination,self._active_line,str(load)) #tuple to identify combinations on line
                            self._lc_comb_created.append(ttk.Label(self._main_fr, text = load,
                                                                 font = self._text_size['Text 8 bold'],
                                                                  ))
                            self._lc_comb_created.append(ttk.Entry(self._main_fr,
                                                                 textvariable =self._new_load_comb_dict[name][0],
                                                                  width=5,
                                                                  ))
                            self._lc_comb_created.append(ttk.Entry(self._main_fr,
                                                                 textvariable=self._new_load_comb_dict[name][1],
                                                                 width=5,
                                                                  ))
                            self._lc_comb_created.append(ttk.Checkbutton(self._main_fr,
                                                                       variable =self._new_load_comb_dict[name][2]))

                    for load_no in range(int(len(self._lc_comb_created)/4)):
                            self._lc_comb_created[0+load_no*4].place(relx=lc_x, rely=lc_y+lc_y_delta*load_no)
                            self._lc_comb_created[1+load_no*4].place(relx=lc_x+5*lc_x_delta, rely=lc_y+lc_y_delta*load_no)
                            self._lc_comb_created[2+load_no*4].place(relx=lc_x+6*lc_x_delta, rely=lc_y+lc_y_delta*load_no)
                            self._lc_comb_created[3+load_no*4].place(relx=lc_x+7*lc_x_delta, rely=lc_y+lc_y_delta*load_no)
                            counter += 1

                # finding tank loads applied to line (automatically created compartments.
                lc_y += 0.023148148*counter
                counter = 0
                if len(self._tank_dict) != 0 and combination !='manual':
                    for compartment in self.get_compartments_for_line(self._active_line):
                        name = (combination,self._active_line,'comp' + str(compartment)) #tuple to identify combinations on line
                        self._comp_comb_created.append(ttk.Label(self._main_fr, text='Compartment'+str(compartment),
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
                                                                     variable = self._new_load_comb_dict[name][2]))

                    for comp_no in range(int(len(self._comp_comb_created)/4)):
                            self._comp_comb_created[0+comp_no*4].place(relx=lc_x, rely=lc_y+lc_y_delta*comp_no)
                            self._comp_comb_created[1+comp_no*4].place(relx=lc_x+5*lc_x_delta, rely=lc_y+lc_y_delta*comp_no)
                            self._comp_comb_created[2+comp_no*4].place(relx=lc_x+6*lc_x_delta, rely=lc_y+lc_y_delta*comp_no)
                            self._comp_comb_created[3+comp_no*4].place(relx=lc_x+7*lc_x_delta, rely=lc_y+lc_y_delta*comp_no)
                            counter += 1

                lc_y += 0.027777778*counter
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
                    self._manual_created.append(ttk.Checkbutton(self._main_fr, variable=self._new_load_comb_dict[name][2]))
                    self._manual_created[0].place(relx=lc_x, rely=lc_y)
                    self._manual_created[1].place(relx=lc_x + 4 * lc_x_delta, rely=lc_y)
                    self._manual_created[2].place(relx=lc_x + 6 * lc_x_delta, rely=lc_y)
                    self._manual_created[3].place(relx=lc_x + 7 * lc_x_delta, rely=lc_y)

            if self._line_to_struc[self._active_line][5] is None:
                results = self.calculate_all_load_combinations_for_line(self._active_line)

                self._result_label_dnva.config(text = 'DNV a [Pa]: ' + str(results['dnva']),
                                              font = self._text_size['Text 8'])
                self._result_label_dnvb.config(text = 'DNV b [Pa]: ' + str(results['dnvb']),
                                              font = self._text_size['Text 8'])
                self._result_label_tanktest.config(text = 'TT [Pa]: ' + str(results['tanktest']),
                                                  font = self._text_size['Text 8'])

                self._result_label_manual.config(text = 'Manual [Pa]: ' + str(results['manual']))

                lc_y = self.results_gui_start+0.018518519
                self._result_label_dnva.place(relx = lc_x+0*lc_x_delta, rely = lc_y+lc_y_delta*1.5)
                self._result_label_dnvb.place(relx=lc_x+4*lc_x_delta, rely=lc_y+lc_y_delta*1.5)
                self._result_label_tanktest.place(relx=lc_x+0*lc_x_delta, rely=lc_y+2.4*lc_y_delta)

                self._result_label_manual.place(relx=lc_x+4*lc_x_delta, rely=lc_y+2.4*lc_y_delta)
                self._lab_pressure.place(relx=0.786458333, rely=self.results_gui_start)
            else:
                for item in [self._result_label_dnva,self._result_label_dnvb,
                             self._result_label_tanktest,self._result_label_manual,self._lab_pressure ]:
                    item.place_forget()
                    #self._combination_slider.set(4)

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
            if self._line_to_struc[line][0].Plate.get_structure_type() not in ('GENERAL_INTERNAL_NONWT','FRAME'):
                self._pending_grid_draw[line] = coordinates
        except KeyError:
            pass

    def grid_find_tanks(self, animate = False):
        '''
        Printing the grid in a separate window
        :return:
        '''

        if self._line_to_struc == {}:
            tk.messagebox.showerror('Search error','No geometry with properties exist.')
            return
        #setting the button to red
        try:
            img_file_name = 'img_int_pressure_button_search.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._int_button.config(image = photo)
            self._int_button.image = photo
        except TclError:
            pass


        animate = tk.messagebox.askquestion('Search for compartments','Searching for compartments will use a large matrix to '
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
                                                               'Choose yes or no.' )
        animate = True if animate == 'yes' else False

        self._main_grid.clear()
        self._tank_dict = {}
        self._pending_grid_draw={}
        self._compartments_listbox.delete(0,'end')

        for line, points in self._line_dict.items():
            # making the lines made by used in the grid
            p1 =  self._point_dict['point'+str(points[0])]
            p2 =  self._point_dict['point'+str(points[1])]
            self.grid_operations(line, [self.get_grid_coord_from_points_coords(p1),
                                        self.get_grid_coord_from_points_coords(p2)])

        self._grid_calc = grid_window.CreateGridWindow(self._main_grid,self._canvas_dim,
                                                       self._pending_grid_draw,self._canvas_base_origo)


        compartment_search_return = self._grid_calc.search_bfs(animate=animate)


        for comp_no, properties in compartment_search_return['compartments'].items():
            # finding actual max min elevation from grid
            min_el = (float('inf'), float('inf'))
            max_el = (-float('inf'),-float('inf'))
            if comp_no > 1:
                self._compartments_listbox.insert('end', comp_no)
                for corner in properties[1]:
                    corner_real = self.get_point_coords_from_grid_coords(corner)
                    if self.get_point_coords_from_grid_coords(corner)[1] < min_el[1]:
                        min_el = self.get_closest_point(corner_real)[1]
                    if self.get_point_coords_from_grid_coords(corner)[1] > max_el[1]:
                        max_el = self.get_closest_point(corner_real)[1]
                self.new_tank(int(comp_no),properties[0], min_el, max_el)
            comp_name = 'comp'+str(int(comp_no))

            for combination in self._load_factors_dict.keys():
                #creating the load factor combinations for tanks.
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

            self._int_button.config(image = photo)
            self._int_button.image = photo
        except TclError:
            pass

        if animate == False:
            tank_count = None if len(self._tank_dict)==0 else len(self._tank_dict)
            if tank_count is not None:
                self._grid_calc.draw_grid(tank_count=tank_count)
        else:
            tank_count = None if len(self._tank_dict) == 0 else len(self._tank_dict)
            if tank_count is not None:
                self._grid_calc.animate_grid(grids_to_animate=compartment_search_return['grids'],
                                             tank_count = None if len(self._tank_dict)==0 else len(self._tank_dict))

        self.get_cob()  # Calculating COB
        self.update_frame()

    def grid_display_tanks(self, save = False):
        '''
        Opening matplotlib grid illustation
        :return:
        '''

        try:
            if self._grid_calc != None:
                self._grid_calc.draw_grid(save = save,
                                          tank_count=None if len(self._tank_dict)==0 else len(self._tank_dict) )
        except RecursionError:
            pass

    def add_to_combinations_dict(self,line):
        '''
        When creating new line and tanks exist, the combinations dict must be updated.
        :param line:
        :return:
        '''
        if len(self._tank_dict) != 0:
            for compartment in self.get_compartments_for_line(line):
                for combination in self._load_factors_dict.keys():
                    name = (combination, line, 'comp'+str(compartment))
                    self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
                    self._new_load_comb_dict[name][0].set(self._load_factors_dict[combination][1])
                    self._new_load_comb_dict[name][1].set(self._load_factors_dict[combination][2])
                    self._new_load_comb_dict[name][2].set(1)
        else:
            pass

        name = ('manual', line, 'manual')
        self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
        self._new_load_comb_dict[name][0].set(0)
        self._new_load_comb_dict[name][1].set(0)
        self._new_load_comb_dict[name][2].set(0)

    def trace_shift_change(self, *args):
        try:
            self.update_frame()
        except (TclError, ZeroDivisionError):
            pass

    def trace_acceptance_change(self, *args):
        try:
            self.update_frame()
            for key, val in self._line_to_struc.items():
                val[0].need_recalc = True
        except (TclError, ZeroDivisionError):
            pass

    def update_frame(self, event = None, *args):

        state = self.get_color_and_calc_state()
        self.draw_results(state=state)
        self.draw_canvas(state=state)
        self.draw_prop()
        #self.trace_puls_up_or_sp()

        return state

    def get_color_and_calc_state(self, current_line = None, active_line_only = False):
        ''' Return calculations and colors for line and results. '''

        return_dict = {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                       'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                       'all_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}, 'utilization': {}, 'slamming': {},
                       'color code': {}, 'PULS colors': {}, 'ML buckling colors' : {}, 'ML buckling class' : {},
                       'weights': {}, 'cylinder': {}}

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
        for current_line in line_iterator:
            rec_for_color[current_line]  = {}
            slamming_pressure = 0
            if current_line in self._line_to_struc.keys():
                all_obj = self._line_to_struc[current_line][0]

                obj_scnt_calc_pl = all_obj.Plate #self._line_to_struc[current_line][1]
                obj_scnt_calc_stf = all_obj.Stiffener  # self._line_to_struc[current_line][1]
                obj_scnt_calc_girder = all_obj.Girder  # self._line_to_struc[current_line][1]

                return_dict['all_obj'][current_line] = all_obj

                if all_obj.need_recalc is False:
                    return self._state_logger[current_line]
                try:
                    norm_and_slam = self.get_highest_pressure(current_line)
                    design_pressure = norm_and_slam['normal'] / 1000
                    if norm_and_slam['slamming'] is None:
                        pass
                    else:
                        slamming_dict = self.get_highest_pressure(current_line)
                        slamming_pressure = slamming_dict['slamming']
                        slamming_red_fac_pl = slamming_dict['slamming plate reduction factor']
                        slamming_red_fac_stf = slamming_dict['slamming stf reduction factor']
                except KeyError:
                    design_pressure = 0

                min_thk = obj_scnt_calc_pl.get_dnv_min_thickness(design_pressure)
                color_thk = 'green' if obj_scnt_calc_pl.is_acceptable_pl_thk(design_pressure) else 'red'
                rec_for_color[current_line]['plate thickness'] = (min_thk / 1000) / obj_scnt_calc_pl.get_pl_thk()
                all_obj.lat_press = design_pressure/1000
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
                               obj_scnt_calc_stf.get_section_modulus ()[1]]

                    shear_area = obj_scnt_calc_stf.get_shear_area()
                    min_shear = obj_scnt_calc_stf.get_minimum_shear_area(design_pressure)
                    min_sec_mod = obj_scnt_calc_stf.get_dnv_min_section_modulus(design_pressure)
                    rec_for_color[current_line]['section modulus'] = min_sec_mod / min(sec_mod)
                    rec_for_color[current_line]['shear'] = min_shear/shear_area
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

                    color_sec = 'green' if obj_scnt_calc_stf.is_acceptable_sec_mod(sec_mod, design_pressure) else 'red'
                    color_shear = 'green' if obj_scnt_calc_stf.is_acceptable_shear_area(shear_area, design_pressure) else 'red'
                else:
                    sec_mod = [0,0]
                    rec_for_color[current_line]['section modulus'] = 0.0
                    rec_for_color[current_line]['shear'] = 0
                    return_dict['slamming'][current_line] = dict()
                    fatigue_obj, p_int, p_ext, damage, dff = [None for dummy in range(5)]
                    color_sec = 'black'
                    color_shear = 'black'
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

                    color_shear = 'green' if round(obj_scnt_calc_stf.get_web_thk()* 1000,1)  >= \
                                             round(slamming_res['tw_req'],1) else 'red'
                    color_thk = 'green' if round(obj_scnt_calc_stf.get_pl_thk() * 1000,1) >= \
                                           round(min_pl_slamming,1) else 'red'

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
                    cylinder_results = self._line_to_struc[current_line][5].get_utilization_factors()
                    return_dict['cylinder'][current_line] = cylinder_results


                '''
                PULS calculations
                '''
                if self._PULS_results != None:
                    res = self._PULS_results.get_puls_line_results(current_line)
                    if res is not None:
                        geo_problem = False
                        if type(res['Ultimate capacity']['Actual usage Factor'][0]) != str:
                            ufnum = res['Ultimate capacity']['Actual usage Factor'][0] / self._new_puls_uf.get()
                            rec_for_color[current_line]['PULS ultimate']=ufnum
                            col_ult = 'green' if ufnum < 1 else 'red'
                        else:
                            geo_problem = True
                            col_ult = 'red'
                        if res['Buckling strength']['Actual usage Factor'][0] is not None:
                            bnum = res['Buckling strength']['Actual usage Factor'][0] / self._new_puls_uf.get()
                            rec_for_color[current_line]['PULS buckling'] = bnum
                            col_buc = 'green' if bnum < 1 else 'red'
                        else:
                            col_buc = 'red'
                        if geo_problem:
                            loc_geom = 'red'
                        else:
                            if obj_scnt_calc_stf is None:
                                loc_label = 'Geom. Req (PULS validity limits)'
                            else:
                                loc_label = 'Local geom req (PULS validity limits)' if \
                                    obj_scnt_calc_stf.get_puls_sp_or_up() == 'SP' else 'Geom. Req (PULS validity limits)'
                            loc_geom = 'green' if all([val[0] == 'Ok' for val in res[loc_label].values()]) else 'red'
                        if obj_scnt_calc_stf is None:
                            csr_label = 'CSR-Tank req'
                        else:
                            csr_label = 'CSR-Tank requirements (primary stiffeners)' if \
                                obj_scnt_calc_stf.get_puls_sp_or_up() == 'SP' else'CSR-Tank req'

                        csr_geom = 'green' if all([val[0] in ['Ok', '-'] for val in res[csr_label].values()]) else 'red'
                        return_dict['PULS colors'][current_line] = {'ultimate': col_ult, 'buckling': col_buc,
                                                                    'local geometry': loc_geom, 'csr': csr_geom}
                    else:
                        return_dict['PULS colors'][current_line] = {'ultimate': 'black', 'buckling': 'black',
                                                                    'local geometry': 'black', 'csr': 'black'}
                else:
                    return_dict['PULS colors'][current_line] = {'ultimate': 'black', 'buckling': 'black',
                                                                'local geometry': 'black', 'csr': 'black'}

                '''
                Machine learning buckling 
                        ['cl SP buc int predictor', 'cl SP buc int scaler',
                        'cl SP ult int predictor', 'cl SP ult int scaler',
                        'cl SP buc GLGT predictor', 'cl SP buc GLGT scaler',
                        'cl SP ult GLGT predictor', 'cl SP ult GLGT scaler']
                '''

                if obj_scnt_calc_pl.get_puls_sp_or_up() == 'UP':
                    buckling_ml_input = obj_scnt_calc_pl.get_buckling_ml_input(design_lat_press=design_pressure)

                    if obj_scnt_calc_pl.get_puls_boundary() == 'Int':
                        if self._ML_buckling['cl UP buc int predictor'] != None:
                            x_buc = self._ML_buckling['cl UP buc int scaler'].transform(buckling_ml_input)
                            y_pred_buc = self._ML_buckling['cl UP buc int predictor'].predict(x_buc)[0]
                        else:
                            y_pred_buc = 0
                        if self._ML_buckling['cl UP ult int predictor'] != None:
                            x_ult = self._ML_buckling['cl UP ult int scaler'].transform(buckling_ml_input)
                            y_pred_ult = self._ML_buckling['cl UP ult int predictor'].predict(x_ult)[0]
                        else:
                            y_pred_ult = 0
                    else:
                        if self._ML_buckling['cl UP buc GLGT predictor'] != None:
                            x_buc = self._ML_buckling['cl UP buc GLGT scaler'].transform(buckling_ml_input)
                            y_pred_buc = self._ML_buckling['cl UP buc GLGT predictor'].predict(x_buc)[0]
                        else:
                            y_pred_buc = 0
                        if self._ML_buckling['cl UP ult GLGT predictor'] != None:
                            x_ult = self._ML_buckling['cl UP ult GLGT scaler'].transform(buckling_ml_input)
                            y_pred_ult = self._ML_buckling['cl UP ult GLGT predictor'].predict(x_ult)[0]
                        else:
                            y_pred_ult = 0

                    x_csr = obj_scnt_calc_pl.get_buckling_ml_input(design_lat_press=design_pressure, csr = True)
                    x_csr = self._ML_buckling['CSR scaler UP'].transform(x_csr)
                    csr_pl = self._ML_buckling['CSR predictor UP'].predict(x_csr)[0]

                    return_dict['ML buckling colors'][current_line] = \
                        {'buckling': 'green' if int(y_pred_buc) == 9 else 'red',
                         'ultimate': 'green' if int(y_pred_ult) == 9 else 'red',
                         'CSR requirement': 'green' if csr_pl == 1 else 'red'}

                    return_dict['ML buckling class'][current_line] = {'buckling': int(y_pred_buc),
                                                                      'ultimate': int(y_pred_ult),
                                                                      'CSR': [csr_pl, float('inf'),
                                                                              float('inf'), float('inf')]}
                else:
                    buckling_ml_input = obj_scnt_calc_stf.get_buckling_ml_input(design_lat_press=design_pressure)
                    if obj_scnt_calc_stf.get_puls_boundary() == 'Int':
                        if self._ML_buckling['cl SP buc int predictor'] != None:
                            x_buc = self._ML_buckling['cl SP buc int scaler'].transform(buckling_ml_input)
                            y_pred_buc = self._ML_buckling['cl SP buc int predictor'].predict(x_buc)[0]
                        else:
                            y_pred_buc = 0
                        if self._ML_buckling['cl SP ult int predictor'] != None:
                            x_ult = self._ML_buckling['cl SP ult int scaler'].transform(buckling_ml_input)
                            y_pred_ult = self._ML_buckling['cl SP ult int predictor'].predict(x_ult)[0]
                        else:
                            y_pred_ult = 0
                    else:
                        if self._ML_buckling['cl SP buc GLGT predictor'] != None:
                            x_buc = self._ML_buckling['cl SP buc GLGT scaler'].transform(buckling_ml_input)
                            y_pred_buc = self._ML_buckling['cl SP buc GLGT predictor'].predict(x_buc)[0]
                        else:
                            y_pred_buc = 0
                        if self._ML_buckling['cl SP ult GLGT predictor'] != None:
                            x_ult = self._ML_buckling['cl SP ult GLGT scaler'].transform(buckling_ml_input)
                            y_pred_ult = self._ML_buckling['cl SP ult GLGT predictor'].predict(x_ult)[0]
                        else:
                            y_pred_ult = 0

                    x_csr = obj_scnt_calc_stf.get_buckling_ml_input(design_lat_press=design_pressure, csr = True)

                    x_csr = self._ML_buckling['CSR scaler SP'].transform(x_csr)
                    csr_pl, csr_web, csr_web_fl, csr_fl = self._ML_buckling['CSR predictor SP'].predict(x_csr)[0]

                    return_dict['ML buckling colors'][current_line] = \
                        {'buckling': 'green' if int(y_pred_buc) == 9 else 'red',
                         'ultimate': 'green' if int(y_pred_ult) == 9 else 'red',
                         'CSR requirement': 'green' if
                         all([csr_pl == 1, csr_web == 1, csr_web_fl == 1, csr_fl == 1]) else 'red'}
                    return_dict['ML buckling class'][current_line] = {'buckling': int(y_pred_buc),
                                                                      'ultimate': int(y_pred_ult),
                                                                      'CSR': [csr_pl, csr_web, csr_web_fl, csr_fl]}

                '''
                Weight calculations for line.
                '''
                # TODO only works for stiffened panel!
                if obj_scnt_calc_stf is not None:
                    line_weight = op.calc_weight([obj_scnt_calc_stf.get_s(), obj_scnt_calc_stf.get_pl_thk(),
                                                  obj_scnt_calc_stf.get_web_h(), obj_scnt_calc_stf.get_web_thk(),
                                                  obj_scnt_calc_stf.get_fl_w(), obj_scnt_calc_stf.get_fl_thk(),
                                                  obj_scnt_calc_stf.get_span(), obj_scnt_calc_stf.get_lg()])
                else:
                    line_weight = 0
                points = self._line_dict[current_line]
                p1 = self._point_dict['point' + str(points[0])]
                p2 = self._point_dict['point' + str(points[1])]

                mid_coord = [(p1[0]+p2[0])/2, (p1[1]+p2[1])/2]

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
                    obj_scnt_calc_stf is None else{'shear_area': shear_area, 'min_shear_area': min_shear}
                return_dict['thickness'][current_line] = {'thk': obj_scnt_calc_pl.get_pl_thk(), 'min_thk': min_thk}
                return_dict['fatigue_obj'][current_line] = fatigue_obj
                return_dict['color code'][current_line] = {}

                if fatigue_obj is not None:
                    return_dict['fatigue'][current_line] = {'damage': damage, 'dff': dff,
                                                            'curve': fatigue_obj.get_sn_curve()}
                    rec_for_color[current_line]['fatigue'] = damage*dff
                else:
                    return_dict['fatigue'][current_line] = {'damage': None, 'dff': None, 'curve': None}
                    rec_for_color[current_line]['fatigue'] = 0

                fat_util = 0 if damage is None else damage * dff
                shear_util = 0 if shear_area == 0 else min_shear / shear_area
                thk_util = 0 if obj_scnt_calc_pl.get_pl_thk() == 0 else min_thk / (1000 * obj_scnt_calc_pl.get_pl_thk())
                sec_util = 0 if min(sec_mod) == 0 else min_sec_mod / min(sec_mod)
                buc_util = 1 if float('inf') in buckling else max(all_buckling_uf_list)
                rec_for_color[current_line]['rp buckling'] = max(all_buckling_uf_list)
                return_dict['utilization'][current_line] = {'buckling': buc_util,
                                                            'PULS buckling': buc_util,
                                                            'fatigue': fat_util,
                                                            'section': sec_util,
                                                            'shear': shear_util,
                                                            'thickness': thk_util}

                # Color coding state
                self._state_logger[current_line] = return_dict #  Logging the current state of the line.
                self._line_to_struc[current_line][0].need_recalc = False
            else:
                pass

        sec_in_model, idx, recorded_sections = dict(), 0, list()
        for data in self._line_to_struc.values():
            if data[0].Stiffener is not None:
                if data[0].Stiffener.get_beam_string() not in recorded_sections:
                    sec_in_model[data[0].Stiffener.get_beam_string()] = idx
                    recorded_sections.append(data[0].Stiffener.get_beam_string())
                    idx += 1
        sec_in_model['length'] = len(recorded_sections)

        if self._line_to_struc != {}:
            sec_mod_map = np.arange(0,1.1,0.1)
            fat_map = np.arange(0,1.1,0.1)
            all_thicknesses = [round(objs[0].Plate.get_pl_thk(), 5) for objs in self._line_to_struc.values()]
            all_thicknesses = np.unique(all_thicknesses).tolist()
            thickest_plate = max(all_thicknesses)
            if len(all_thicknesses) > 1:
                thk_map = np.arange(min(all_thicknesses), max(all_thicknesses) + (max(all_thicknesses) -
                                                                                  min(all_thicknesses)) / 10,
                                     (max(all_thicknesses) - min(all_thicknesses)) / 10)
            else:
                thk_map = all_thicknesses

            try:
                all_pressures = sorted([self.get_highest_pressure(line)['normal']
                                        for line in list(self._line_dict.keys())])
            except KeyError:
                all_pressures = [0, 1]

            all_pressures = np.unique(all_pressures).tolist()

            highest_pressure, lowest_pressure = max(all_pressures), min(all_pressures)
            if len(all_pressures) > 1:
                press_map = [round(val, 1) for val in
                             np.arange(all_pressures[0], all_pressures[-1],
                                       (all_pressures[-1] - all_pressures[0]) / 10)] + \
                            [round(all_pressures[-1], 1)]
            else:
                press_map = all_pressures

            all_utils = [max(list(return_dict['utilization'][line].values()))
                         for line in self._line_to_struc.keys()]
            all_utils = np.unique(all_utils).tolist()
            if len(all_utils) >1:
                util_map =  np.arange(0, 1.1, 0.1)
            else:
                util_map = all_utils

            if self._PULS_results is not None:
                #puls_util_map = self._PULS_results.all_uf
                puls_util_map = list()
                for key, val in self._line_to_struc.items():
                    puls_util_map.append(self._PULS_results.get_utilization(key, val[0].Plate.get_puls_method(),
                                                                            acceptance = self._new_puls_uf.get()))
                puls_util_map  = np.arange(0, 1.1, 0.1)
            else:
                puls_util_map = None

            sig_x = np.unique([self._line_to_struc[line][0].Plate.get_sigma_x1() for line in
                               self._line_to_struc.keys()]).tolist()
            if len(sig_x) > 1: # TODO color coding when using sig_x1 and sig_x2 (23.12.2021)
                sig_x_map = np.arange(min(sig_x), max(sig_x) + (max(sig_x) - min(sig_x)) / 10,
                                      (max(sig_x) - min(sig_x)) / 10)
            else:
                sig_x_map = sig_x
            sig_y1 = np.unique([self._line_to_struc[line][0].Plate.get_sigma_y1() for line in
                                self._line_to_struc.keys()]).tolist()
            if len(sig_y1) > 1:
                sig_y1_map = np.arange(min(sig_y1), max(sig_y1) + (max(sig_y1) - min(sig_y1)) / 10,
                                       (max(sig_y1) - min(sig_y1)) / 10)
            else:
                sig_y1_map = sig_y1

            sig_y2 = np.unique([self._line_to_struc[line][0].Plate.get_sigma_y2() for line in
                                self._line_to_struc.keys()]).tolist()
            if len(sig_y2) > 1:

                sig_y2_map = np.arange(min(sig_y2), max(sig_y2) + (max(sig_y2) - min(sig_y2)) / 10,
                                       (max(sig_y2) - min(sig_y2)) / 10)
            else:
                sig_y2_map = sig_y2
            tau_xy = np.unique([self._line_to_struc[line][0].Plate.get_tau_xy() for line in
                                self._line_to_struc.keys()]).tolist()
            if len(tau_xy) > 1:
                tau_xy_map = np.arange(min(tau_xy), max(tau_xy) + (max(tau_xy) - min(tau_xy)) / 10,
                                       (max(tau_xy) - min(tau_xy)) / 10)
            else:
                tau_xy_map = tau_xy

            spacings = list()
            for line in self._line_to_struc.keys():
                if self._line_to_struc[line][0].Stiffener is not None:
                    spacings.append(self._line_to_struc[line][0].Stiffener.get_s())
            spacing = np.unique(spacings).tolist()
            structure_type = [self._line_to_struc[line][0].Plate.get_structure_type() for line in
                              self._line_to_struc.keys()]

            return_dict['color code'] = {'thickest plate': thickest_plate, 'thickness map': thk_map,
                                         'all thicknesses': all_thicknesses,
                                         'section modulus map': sec_mod_map,
                                         'fatigue map': fat_map,
                                         'highest pressure': highest_pressure, 'lowest pressure': lowest_pressure,
                                         'pressure map': press_map, 'all pressures':all_pressures,
                                         'all utilizations': all_utils, 'utilization map': util_map,
                                         'PULS utilization map': puls_util_map,
                                         'max sigma x': max(sig_x), 'min sigma x': min(sig_x), 'sigma x map': sig_x_map,
                                         'max sigma y1': max(sig_y1), 'min sigma y1': min(sig_y1),
                                         'sigma y1 map': sig_y1_map,
                                         'max sigma y2': max(sig_y2), 'min sigma y2': min(sig_y2),
                                         'sigma y2 map': sig_y2_map,
                                         'max tau xy': max(tau_xy), 'min tau xy': min(tau_xy), 'tau xy map': tau_xy_map,
                                         'structure types map': np.unique(structure_type).tolist(),
                                         'sections in model': sec_in_model,
                                         'recorded sections': recorded_sections,
                                         'spacings': spacing, 'max spacing': max(spacing), 'min spacing': min(spacing)}
            line_color_coding, puls_method_map, puls_sp_or_up_map = \
                {}, {None: 0, 'buckling': 0.5, 'ultimate': 1}, {None:0, 'SP': 0.5, 'UP': 1}
            cmap_sections = plt.get_cmap('jet')
            thk_sort_unique = return_dict['color code']['all thicknesses']
            spacing_sort_unique = return_dict['color code']['spacings']
            structure_type_unique = return_dict['color code']['structure types map']
            tot_weight, weight_mult_dist_x, weight_mult_dist_y = 0, 0,0
            for line, line_data in self._line_to_struc.items():
                if self._PULS_results is None:
                    puls_color, buc_uf, puls_uf, puls_method, puls_sp_or_up = 'black', 0, 0, None, None
                elif self._PULS_results.get_utilization(line, self._line_to_struc[line][0].Plate.get_puls_method(),
                                                        self._new_puls_uf.get()) == None:
                    puls_color, buc_uf, puls_uf, puls_method, puls_sp_or_up = 'black', 0,0, None, None
                else:
                    puls_method = self._line_to_struc[line][0].Plate.get_puls_method()
                    puls_uf = self._PULS_results.get_utilization(
                                                   line, puls_method,
                                                   self._new_puls_uf.get())
                    puls_color = matplotlib.colors.rgb2hex(cmap_sections(puls_uf))
                    puls_sp_or_up = self._line_to_struc[line][0].Plate.get_puls_sp_or_up()

                rp_uf = rec_for_color[line]['rp buckling']

                tot_uf_rp = max([rec_for_color[line]['fatigue'], rp_uf,
                                 rec_for_color[line]['section modulus'], rec_for_color[line]['shear'],
                                 rec_for_color[line]['plate thickness']])
                tot_uf_puls = max([rec_for_color[line]['fatigue'], puls_uf,
                                 rec_for_color[line]['section modulus'], rec_for_color[line]['shear'],
                                 rec_for_color[line]['plate thickness']])
                try:
                    this_pressure = self.get_highest_pressure(line)['normal']
                except KeyError:
                    this_pressure = 0
                rp_util = max(list(return_dict['utilization'][line].values()))

                res = list()
                for stress_list, this_stress in zip([sig_x, sig_y1, sig_y2, tau_xy],
                                                     [line_data[0].Plate.get_sigma_x1(), line_data[0].Plate.get_sigma_y1(),
                                                      line_data[0].Plate.get_sigma_y2(), line_data[0].Plate.get_tau_xy()]):
                    if len(stress_list) == 1:
                        res.append(1)
                    elif max(stress_list) == 0 and min(stress_list) == 0:
                        res.append(0)
                    elif this_stress < 0:
                        res.append(this_stress /min(stress_list))
                    elif this_stress >= 0:
                        res.append(this_stress/ max(stress_list))

                sig_x_uf, sig_y1_uf, sig_y2_uf , tau_xy_uf = res


                line_color_coding[line] = {'plate': matplotlib.colors.rgb2hex(cmap_sections(
                    thk_sort_unique.index(round(line_data[0].Plate.get_pl_thk(),10))/len(thk_sort_unique))),
                                           'spacing': 'black' if line_data[0].Stiffener is None else matplotlib.colors.rgb2hex(
                                               cmap_sections(spacing_sort_unique.index(round(line_data[0].Stiffener
                                                                                         .get_s(), 10)) / len(
                                                   spacing_sort_unique))),
                                           'section': 'black' if line_data[0].Stiffener is None else
                                           matplotlib.colors.rgb2hex(cmap_sections(sec_in_model[line_data[0]
                                                                                   .Stiffener.get_beam_string()]/
                                                                                   len(list(recorded_sections)))),
                                           'structure type': matplotlib.colors.rgb2hex(
                                               cmap_sections(structure_type_unique.index(line_data[0].Plate.get_structure_type())
                                                             /len(structure_type_unique))),
                                           'pressure color': 'black' if all_pressures in [[0],[0,1]] else matplotlib.colors.rgb2hex(cmap_sections(
                                               this_pressure/highest_pressure)),
                                           'pressure': this_pressure,
                                           'rp uf color': matplotlib.colors.rgb2hex(cmap_sections(rp_util)),
                                           'rp uf': rp_util,
                                           'PULS method': puls_method,
                                           'PULS sp or up':puls_sp_or_up,
                                           'section modulus color': matplotlib.colors.rgb2hex(
                                               cmap_sections(rec_for_color[line]['section modulus'])),
                                           'fatigue color': matplotlib.colors.rgb2hex(
                                               cmap_sections(rec_for_color[line]['fatigue'])),
                                           'Total uf color rp' : matplotlib.colors.rgb2hex(
                                               cmap_sections(tot_uf_rp)),
                                           'Total uf rp': tot_uf_rp,
                                           'Total uf color puls': matplotlib.colors.rgb2hex(
                                               cmap_sections(tot_uf_puls)),
                                           'Total uf puls': tot_uf_puls,
                                           'PULS uf': round(puls_uf,2),
                                           'PULS uf color': puls_color,
                                           'fatigue uf' : rec_for_color[line]['fatigue'],
                                           'section uf' : rec_for_color[line]['section modulus'],
                                           'sigma x': matplotlib.colors.rgb2hex(cmap_sections(sig_x_uf)),
                                           'sigma y1': matplotlib.colors.rgb2hex(cmap_sections(sig_y1_uf)),
                                           'sigma y2': matplotlib.colors.rgb2hex(cmap_sections(sig_y2_uf)),
                                           'tau xy':matplotlib.colors.rgb2hex(cmap_sections(tau_xy_uf)),
                                           }
                return_dict['color code']['lines'] = line_color_coding

                # COG calculations
                # Steel
                tot_weight += return_dict['weights'][line]['line weight']
                weight_mult_dist_x += return_dict['weights'][line]['line weight']\
                                      *return_dict['weights'][line]['mid_coord'][0]
                weight_mult_dist_y += return_dict['weights'][line]['line weight']\
                                      *return_dict['weights'][line]['mid_coord'][1]

            tot_cog = [weight_mult_dist_x/tot_weight, weight_mult_dist_y/tot_weight]
        else:
            tot_cog = [0,0]
            tot_weight = 0

        return_dict['COG'] = tot_cog
        return_dict['Total weight'] = tot_weight

        return return_dict

    def draw_canvas(self, state = None, event = None):
        '''
        Canvas is drawn here.
        '''

        self._main_canvas.delete('all')
        color = 'black' #by default
        # Drawing the shifted lines
        if any([self._new_shift_viz_coord_hor.get()!=0, self._new_shift_viz_coord_ver.get()!= 0]) and self._new_shifted_coords.get():
            self._main_canvas.create_line(self._canvas_draw_origo[0]+self._canvas_scale*self._new_shift_viz_coord_hor.get()/1000, 0,
                                          self._canvas_draw_origo[0]+self._canvas_scale*self._new_shift_viz_coord_hor.get()/1000,
                                          self._canvas_dim[1] + 500,
                                          stipple='gray50', fill = 'peru')
            self._main_canvas.create_line(0, self._canvas_draw_origo[1]-self._canvas_scale*self._new_shift_viz_coord_ver.get()/1000,
                                          self._canvas_dim[0] + 500,
                                          self._canvas_draw_origo[1]-self._canvas_scale*self._new_shift_viz_coord_ver.get()/1000,
                                          stipple='gray50', fill = 'peru')
        else:
            # Drawing lines at (0, 0)
            self._main_canvas.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0], self._canvas_dim[1]+500,
                                         stipple= 'gray50', fill=self._color_text)
            self._main_canvas.create_line(0, self._canvas_draw_origo[1], self._canvas_dim[0] +500, self._canvas_draw_origo[1],
                                         stipple='gray50', fill=self._color_text)
            self._main_canvas.create_text(self._canvas_draw_origo[0] - 30 * 1,
                                          self._canvas_draw_origo[1] + 12 * 1, text='(0,0)',
                                          font='Text 10', fill = self._color_text)

        # Drawing COG and COB
        if self._new_show_cog.get():
            pt_size = 5
            if 'COG' in state.keys():
                if self._new_shifted_coords.get():
                    point_coord_x = self._canvas_draw_origo[0] + (state['COG'][0] +
                                                                  self._new_shift_viz_coord_hor.get()/1000) * \
                                    self._canvas_scale
                    point_coord_y = self._canvas_draw_origo[1] - (state['COG'][1] +
                                                                  self._new_shift_viz_coord_ver.get()/1000) * \
                                    self._canvas_scale
                else:
                    point_coord_x = self._canvas_draw_origo[0] + state['COG'][0]*self._canvas_scale
                    point_coord_y = self._canvas_draw_origo[1] - state['COG'][1]*self._canvas_scale

                self._main_canvas.create_oval(point_coord_x - pt_size + 2,
                                              point_coord_y - pt_size + 2,
                                              point_coord_x  + pt_size + 2,
                                              point_coord_y + pt_size + 2, fill='yellow')

                self._main_canvas.create_text(point_coord_x  + 5,
                                              point_coord_y - 14, text='steel COG: x=' + str(round(state['COG'][0], 2)) +
                                                                       ' y=' +str(round(state['COG'][1],2)),
                                            fill = self._color_text)

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
                                                  text='COB d='+str(draft) +': x=' + str(round(cob[1], 2)) +
                                                       ' y=' + str(round(cob[0], 2)),
                                                  font=self._text_size["Text 8"], fill='blue')

        chk_box_active = [self._new_colorcode_beams.get(), self._new_colorcode_plates.get(),
            self._new_colorcode_pressure.get(), self._new_colorcode_utilization.get(),
            self._new_colorcode_sigmax.get(), self._new_colorcode_sigmay1.get(), self._new_colorcode_sigmay2.get(),
            self._new_colorcode_tauxy.get(), self._new_colorcode_structure_type.get(),
                           self._new_colorcode_fatigue.get(), self._new_colorcode_section_modulus.get(),
                          self._new_colorcode_total.get(), self._new_colorcode_puls_acceptance.get(),
                          self._new_colorcode_puls_sp_or_up.get(), self._new_colorcode_spacing.get()].count(True)> 0

        if chk_box_active and state != None:
            self.color_code_text(state)

        # Drawing shortcut information if selected.
        if self._new_shortcut_backdrop.get() == True:
            self._main_canvas.create_text(self._main_canvas.winfo_width()*0.87, self._main_canvas.winfo_height()*0.16,
                                          text = self._shortcut_text,
                                          font=self._text_size["Text 8"],
                                          fill = self._color_text)

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

            if self._point_is_active and key == self._active_point :
                self._main_canvas.create_oval(self.get_point_canvas_coord(key)[0] - pt_size+2,
                                             self.get_point_canvas_coord(key)[1] - pt_size+2,
                                             self.get_point_canvas_coord(key)[0] + pt_size+2,
                                             self.get_point_canvas_coord(key)[1] + pt_size+2, fill='blue')
                if self._new_draw_point_name.get():
                    # drawing the name of the point

                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] + 5,
                                                 self.get_point_canvas_coord(key)[1] - 14, text='pt.'+str(get_num(key)),
                                                 font=self._text_size["Text 12 bold"], fill = 'red')
                    # drawing the coordinates of the point
                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0]+30,
                                                  self.get_point_canvas_coord(key)[1]-40,
                                                 text='(' + str(x_coord) + ' , ' +
                                                      str(y_coord) + ')',
                                                  font="Text 14", fill = 'red')

            else:
                self._main_canvas.create_oval(self.get_point_canvas_coord(key)[0] - pt_size,
                                             self.get_point_canvas_coord(key)[1] - pt_size,
                                             self.get_point_canvas_coord(key)[0] + pt_size,
                                             self.get_point_canvas_coord(key)[1] + pt_size, fill='red')
                if self._new_draw_point_name.get():
                    #printing 'pt.#'
                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] + 15,
                                                 self.get_point_canvas_coord(key)[1] - 10, text='pt.'+str(get_num(key)),
                                                  font="Text 10", fill = self._color_text)
                    #printing the coordinates of the point
                    self._main_canvas.create_text(self.get_point_canvas_coord(key)[0]+35,
                                                  self.get_point_canvas_coord(key)[1]+10 ,
                                                 text='(' + str(x_coord) + ' , ' +
                                                      str(y_coord) + ')',
                                                  font="Text 10", fill = coord_color)
        # drawing the line dictionary.

        if len(self._line_dict) != 0:
            for line, value in self._line_dict.items():
                coord1 = self.get_point_canvas_coord('point' + str(value[0]))
                coord2 = self.get_point_canvas_coord('point' + str(value[1]))
                if not chk_box_active and state != None:
                    try:
                        if self._line_to_struc[line][5] is not None: # Cylinder
                            cylinder_results = state['cylinder'][line]
                            all_cyl_chks = list()
                            for key, val in cylinder_results.items():
                                if key in ['Unstiffened shell', 'Longitudinal stiffened shell',
                                           'Ring stiffened shell', 'Heavy ring frame']:

                                    all_cyl_chks.append(True if val is None else val < 1)
                                elif key == 'Stiffener check' and val is not None:
                                    for stf_key, stf_val in val.items():
                                        if stf_val is not None:
                                            all_cyl_chks.append(stf_val)
                            color = 'green' if all(all_cyl_chks) else 'red'

                        elif self._new_buckling_method.get() == 'DNV PULS':
                            if 'black' in state['PULS colors'][line].values():
                                color = 'black'
                            else:
                                col1, col2 = state['PULS colors'][line]['buckling'], \
                                             state['PULS colors'][line]['ultimate']

                                if self._line_to_struc[line][0].Plate.get_puls_method() == 'buckling':
                                    color = 'red' if any([col1 == 'red', col2 == 'red']) else 'green'
                                else:
                                    color = col2

                                if color == 'green':
                                    color = 'green' if all([state['colors'][line][key] == 'green' for key in
                                                            ['fatigue', 'section', 'shear','thickness']]) else 'red'
                        elif self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
                            color = 'red' if 'red' in state['colors'][line].values() else 'green'
                        elif self._new_buckling_method.get() == 'ML-CL (PULS based)':
                            if 'black' in state['ML buckling colors'][line].values():
                                color = 'black'
                            else:
                                col1, col2 = state['ML buckling colors'][line]['buckling'], \
                                             state['ML buckling colors'][line]['ultimate']

                                if self._line_to_struc[line][0].Plate.get_puls_method() == 'buckling':
                                    color = col1
                                else:
                                    color = col2

                                if color == 'green':
                                    color = 'green' if all([state['colors'][line][key] == 'green' for key in
                                                            ['fatigue', 'section', 'shear','thickness']]) else 'red'

                    except (KeyError, TypeError):
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
                        self._main_canvas.create_line(coord1, coord2, width=10, fill = color, stipple = 'gray50')
                    else:
                        self._main_canvas.create_line(coord1, coord2, width=6, fill=color)
                    if self._new_line_name.get():
                        self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2+10,
                                                     text='Line ' + str(get_num(line)),
                                                      font=self._text_size["Text 10 bold"],
                                                     fill = 'red')
                else:
                    if line not in self._line_to_struc.keys():
                        self._main_canvas.create_line(coord1, coord2, width=3, fill=self._color_text)
                    elif self._line_to_struc[line][5] is not None:
                        self._main_canvas.create_line(coord1, coord2, width=6, fill = color, stipple = 'gray50')
                    else:
                        self._main_canvas.create_line(coord1, coord2, width=3, fill = color)
                    if self._new_line_name.get():
                        self._main_canvas.create_text(coord1[0]-20 + vector[0] / 2 + 5, coord1[1] + vector[1] / 2+10,
                                                     text='l.' + str(get_num(line)), font="Text 8",
                                                      fill = self._color_text)
                if line in self._multiselect_lines:
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 +5, coord1[1] + vector[1] / 2 -10,
                                                  text=self._new_toggle_var.get(),

                                                  fill='orange')

        # drawing waterline
        if len(self._load_dict) != 0:
            for load, data in self._load_dict.items():

                if data[0].is_static():
                    draft = self.get_canvas_coords_from_point_coords((0,data[0].get_static_draft()))[1]
                    self._main_canvas.create_line(0,draft,self._canvas_dim[0]+500,draft, fill="blue", dash=(4, 4))
                    self._main_canvas.create_text(900,draft-10,text=str(get_num(data[0].get_name()))+' [m]',fill ='blue')
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
        start_text, start_text_shift = 190,191
        cmap_sections = plt.get_cmap('jet')
        if self._new_colorcode_beams.get() == True and self._line_to_struc != {}:
            sec_in_model = cc_state['sections in model']
            for section, idx in sec_in_model.items():
                if section =='length':
                    continue
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=section,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=section,
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(idx/sec_in_model['length'])),
                                              anchor="nw")
        elif self._new_colorcode_plates.get() == True and self._line_to_struc != {}:

            all_thicknesses = np.unique(cc_state['all thicknesses']).tolist()

            for idx, thk in enumerate(np.unique(all_thicknesses).tolist()):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str('Plate '+ str(thk*1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str('Plate '+ str(thk*1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(all_thicknesses.index(thk)
                                                                                           /len(all_thicknesses))),
                                              anchor="nw")
        elif self._new_colorcode_spacing.get() == True and self._line_to_struc != {}:

            all_spacings = cc_state['spacings']

            for idx, s in enumerate(all_spacings):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str('Spacing '+ str(s*1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str('Spacing '+ str(s*1000) + ' mm'),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(all_spacings.index(s)
                                                                                           /len(all_spacings))),
                                              anchor="nw")
        elif self._new_colorcode_pressure.get() == True and self._line_to_struc != {}:
            highest_pressure = cc_state['highest pressure']
            press_map = cc_state['pressure map']

            for idx, press in enumerate(press_map):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str(str(press) + ' Pa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str(str(press) + ' Pa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(0 if highest_pressure == 0
                                                                                           else press/highest_pressure)),
                                              anchor="nw")
        elif all([self._new_colorcode_utilization.get() == True,
                  self._line_to_struc != {}, self._new_buckling_method.get() != 'DNV PULS']):
            all_utils = cc_state['utilization map']
            for idx, uf in enumerate(cc_state['utilization map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str('UF = ' +str(round(uf,1))),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str('UF = ' +str(round(uf,1))),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(uf/max(all_utils))),
                                              anchor="nw")
        elif all([self._new_colorcode_utilization.get() == True,
                  self._line_to_struc != {}, self._new_buckling_method == 'DNV PULS']):
            all_utils = cc_state['PULS utilization map']
            for idx, uf in enumerate(cc_state['utilization map']):
                self._main_canvas.create_text(11, start_text_shift + 20 * idx, text=str('UF = ' +str(round(uf,1))),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text + 20 * idx, text=str('UF = ' +str(round(uf,1))),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(uf/max(all_utils))),
                                              anchor="nw")
        elif self._new_colorcode_sigmax.get() == True:
            for idx, value in enumerate(cc_state['sigma x map']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max sigma x']-cc_state['min sigma x'] == 0 else
                                              matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max sigma x'] == 0 else
                                                                (value+ abs(cc_state['min sigma x'])) /
                                                                (cc_state['max sigma x']-cc_state['min sigma x']))),
                                              anchor="nw")
        elif self._new_colorcode_sigmay1.get() == True:
            for idx, value in enumerate(cc_state['sigma y1 map']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max sigma y1']-cc_state['min sigma y1'] == 0
                                              else matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max sigma y1'] == 0 else
                                                                (value+ abs(cc_state['min sigma y1'])) /
                                                                (cc_state['max sigma y1']-cc_state['min sigma y1']))),
                                              anchor="nw")
        elif self._new_colorcode_sigmay2.get() == True:
            for idx, value in enumerate(cc_state['sigma y2 map']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max sigma y2']-cc_state['min sigma y2'] == 0 else
                                              matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max sigma y2'] == 0 else
                                                                (value+ abs(cc_state['min sigma y2'])) /
                                                                (cc_state['max sigma y2']-cc_state['min sigma y2']))),
                                              anchor="nw")
        elif self._new_colorcode_tauxy.get() == True:
            for idx, value in enumerate(cc_state['tau xy map']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str(str(round(value,5)) + ' MPa'),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black' if cc_state['max tau xy']-cc_state['min tau xy'] == 0 else
                                              matplotlib.colors.rgb2hex(
                                                  cmap_sections(0 if cc_state['max tau xy'] == 0 else
                                                                (value+ abs(cc_state['min tau xy'])) /
                                                                (cc_state['max tau xy']-cc_state['min tau xy']))),
                                              anchor="nw")
        elif self._new_colorcode_structure_type.get() == True:
            structure_type_map = list(cc_state['structure types map'])
            for idx, structure_type in enumerate(structure_type_map):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=structure_type,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=structure_type,
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(cmap_sections(structure_type_map
                                                                                           .index(structure_type)/
                                                                             len(structure_type_map))),
                                              anchor="nw")
        elif self._new_colorcode_section_modulus.get() == True or self._new_colorcode_fatigue.get() == True or \
                self._new_colorcode_fatigue.get() == True or self._new_colorcode_total.get() == True:
            for idx, value in enumerate(cc_state['section modulus map']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=str(str(round(value,5))),
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=str(str(round(value,5))),
                                              font=self._text_size["Text 10 bold"],
                                              fill=matplotlib.colors.rgb2hex(
                                                  cmap_sections(value)),
                                              anchor="nw")
        elif self._new_colorcode_puls_sp_or_up.get() == True:

            for idx, value in enumerate(['SP', 'UP']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='blue' if value == 'SP' else 'red',
                                              anchor="nw")
        elif self._new_colorcode_puls_acceptance.get() == True:

            for idx, value in enumerate(['buckling', 'ultimate']):
                self._main_canvas.create_text(11, start_text_shift+20*idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='black',
                                              anchor="nw")
                self._main_canvas.create_text(10, start_text+20*idx, text=value,
                                              font=self._text_size["Text 10 bold"],
                                              fill='blue' if value == 'ultimate' else 'red',
                                              anchor="nw")

    def color_code_line(self, state, line, coord1, vector):

        cc_state = state['color code']
        if line not in state['color code']['lines'].keys():
            return 'black'
        if self._new_colorcode_beams.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None or self._line_to_struc[line][0].Stiffener is None:
                color = 'grey'
                this_text = 'N/A'
            elif self._line_to_struc[line][0].Plate is not None:
                color = state['color code']['lines'][line]['section']
                this_text = self._line_to_struc[line][0].Plate.get_beam_string()
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text ,
                                              font=self._text_size["Text 7"])

        elif self._new_colorcode_plates.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['plate']
                this_text = str(self._line_to_struc[line][0].Plate.get_pl_thk()*1000)
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_spacing.get() == True and line in list(self._line_to_struc.keys()):
            if self._line_to_struc[line][5] is not None or self._line_to_struc[line][0].Stiffener is None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['spacing']
                this_text = str(self._line_to_struc[line][0].Stiffener.get_s()*1000)
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
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['rp uf color']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=round(state['color code']['lines'][line]['rp uf'],2))

        elif self._new_colorcode_utilization.get() == True and self._new_buckling_method.get() == 'DNV PULS':
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['PULS uf color']
                this_text = round(state['color code']['lines'][line]['PULS uf'],2)
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)
        elif self._new_colorcode_utilization.get() == True and self._new_buckling_method.get() == 'ML-CL (PULS based)':
            color = 'black'
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text='N/A')

        elif self._new_colorcode_sigmax.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['sigma x']
                this_text = str(self._line_to_struc[line][0].Plate.get_sigma_x1())

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_sigmay1.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['sigma y1']
                this_text = str(self._line_to_struc[line][0].Plate.get_sigma_y2())

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_sigmay2.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['sigma y2']
                this_text = str(self._line_to_struc[line][0].Plate.get_sigma_y2())

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_tauxy.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['tau xy']
                this_text =round(self._line_to_struc[line][0].Plate.get_tau_xy(),2)

            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_structure_type.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['structure type']
                this_text =self._line_to_struc[line][0].Plate.get_structure_type()

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
                this_text = round(state['color code']['lines'][line]['section uf'],2)

            if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=this_text)

        elif self._new_colorcode_fatigue.get() == True:


            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
            else:
                color = state['color code']['lines'][line]['fatigue color']
                this_text = round(state['color code']['lines'][line]['fatigue uf'],2)
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=this_text)

        elif self._new_colorcode_total.get() == True:
            if self._line_to_struc[line][5] is not None:
                color = 'grey'
                this_text = 'N/A'
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=this_text)

            elif self._new_buckling_method.get() == 'DNV PULS':
                color = state['color code']['lines'][line]['Total uf color rp']
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['Total uf puls'],2))
            elif self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
                color = state['color code']['lines'][line]['Total uf color puls']
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['Total uf rp'],2))
            elif self._new_buckling_method.get() == 'ML-CL (PULS based)':
                color = 'black'
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text='N/A')
        elif self._new_colorcode_puls_acceptance.get():
            if state['color code']['lines'][line]['PULS method'] == None:
                color = 'black'
            else:
                color = 'blue' if state['color code']['lines'][line]['PULS method'] == 'ultimate' else 'red'
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=state['color code']['lines'][line]['PULS method'])
        elif self._new_colorcode_puls_sp_or_up.get():
            if state['color code']['lines'][line]['PULS sp or up'] == None:
                color = 'black'
            else:
                color = 'blue' if state['color code']['lines'][line]['PULS sp or up'] == 'SP' else 'red'
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=state['color code']['lines'][line]['PULS sp or up'])
        else:
            color = 'black'

        return color

    def draw_prop(self, event = None):
        '''
        Prints the properties of the selected line to the bottom canvas.

        properties for line dicitonary:

        name of line : [ Structure class, calc scantling class, calc fatigue class, [load classes] ]

        '''

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

            # printing the properties to the active line
            if self._line_is_active and self._line_to_struc[self._active_line][5] is None:
                #checkered(10, self._prop_canvas)
                self.set_selected_variables(self._active_line)

                self._prop_canvas.create_text([canvas_width/2-canvas_width/20, canvas_height/20],
                                             text ='SELECTED: '+str(self._active_line),
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
                                                       str(structure_obj.get_pl_thk()*1000) + ' mm' ,
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
                        self._prop_canvas.create_text([startx +40, 50],
                                                      text='Stiffener' if idx == 0 else 'Girder',
                                                      font=self._text_size["Text 10 bold"], fill='Black')
                        if structure_obj is not None:
                            self._prop_canvas.create_text([100, 20],
                                                          text='Thickness scale x 2' if idx == 0 else 'Girder',
                                                          font=self._text_size["Text 10 bold"], fill='grey')
                        # drawing stiffener
                        spacing = structure_obj.get_s()*self._prop_canvas_scale * mult
                        stf_web_height = structure_obj.get_web_h()*self._prop_canvas_scale * mult
                        stf_flange_width = structure_obj.get_fl_w() *self._prop_canvas_scale * mult
                        plate_thk = structure_obj.get_pl_thk()*self._prop_canvas_scale*thk_mult * mult
                        stf_web_thk = structure_obj.get_web_thk()*self._prop_canvas_scale*thk_mult * mult
                        stf_flange_thk = structure_obj.get_fl_thk()*self._prop_canvas_scale*thk_mult * mult

                        for count in [0,1,2] if idx == 0 else [0,]:

                            self._prop_canvas.create_rectangle(startx + count*spacing,
                                                               starty,
                                                               startx+spacing+ count*spacing,
                                                               starty- plate_thk ,
                                                               fill = 'grey', activefill = 'yellow')
                            self._prop_canvas.create_rectangle(startx+spacing*0.5+ count*spacing - stf_web_thk/2,
                                                               starty - plate_thk,
                                                               startx+spacing*0.5+ count*spacing + stf_web_thk/2,
                                                               starty - stf_web_height - plate_thk,
                                                               fill = 'grey', activefill = 'yellow')

                            if structure_obj.get_stiffener_type() not in ['L', 'L-bulb']:

                                self._prop_canvas.create_rectangle(startx+spacing*0.5-stf_flange_width/2+ count*spacing,
                                                                   starty - stf_web_height - plate_thk,
                                                                   startx + spacing * 0.5 + stf_flange_width / 2+ count*spacing,
                                                                   starty - stf_web_height - plate_thk- stf_flange_thk,
                                                                   fill = 'grey', activefill = 'yellow')
                            else:
                                self._prop_canvas.create_rectangle(startx+spacing*0.5-stf_web_thk/2+ count*spacing,
                                                                   starty-stf_web_height - plate_thk,
                                                                   startx + spacing * 0.5 + stf_flange_width + count*spacing,
                                                                   starty - stf_web_height - plate_thk - stf_flange_thk,
                                                                   fill = 'grey',
                                                                   activefill = 'yellow')


            elif self._line_is_active and self._line_to_struc[self._active_line][5] is not None:
                self.draw_cylinder(canvas = self._prop_canvas,CylObj = self._line_to_struc[self._active_line][5],
                                   height = 200, radius = 150, start_x_cyl = 500,start_y_cyl = 20,
                                   text_color= self._color_text)

        else:
            pass

    @staticmethod
    def draw_cylinder(text_size = None, canvas = None, CylObj: CylinderAndCurvedPlate = None,
                      height = 150, radius = 150,
                      start_x_cyl = 500,start_y_cyl = 20, acceptance_color = False, text_x = 180, text_y = 130,
                      text_color = 'black'):

        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        if text_size == None:
            text_size = 'Verdana 8'

        canvas.create_text([text_x, text_y], text=CylObj, font=text_size,fill = text_color)
        # setting the input field to active line properties
        #self.set_selected_variables(self._active_line)

        offset_oval = 30

        coord1 = start_x_cyl, start_y_cyl, start_x_cyl + radius, start_y_cyl+offset_oval
        coord2 = start_x_cyl, start_y_cyl + height, start_x_cyl + radius,start_y_cyl+ offset_oval + height

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

            num_stf = int(1000 * 2*math.pi*CylObj.ShellObj.radius / long_obj.s / 2)
            for line_num in range(1, num_stf, 1):
                angle = 180 - 180 / (num_stf) * line_num
                arc_x, arc_y = 1 * math.cos(math.radians(angle)), 0.5 * math.sin(math.radians(angle))
                arc_x = (arc_x + 1) / 2

                line1 = canvas.create_line(coord1[0] + radius * arc_x,
                                                      coord1[1] + 1 * arc_y * offset_oval+offset_oval/2,
                                                      coord1[0] + radius * arc_x,
                                                      coord1[1] + height + 1 * arc_y * offset_oval+offset_oval/2,
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

    def draw_results(self, state = None):
        '''
        The properties canvas is created here.
                state =     {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                            'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                            'all_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}}
        :return:
        '''

        self._result_canvas.delete('all')

        if state is None or self._active_line not in state['all_obj'].keys():
            return

        if self._line_is_active:
            x, y, dx, dy = 0, 5, 15, 17

            if self._active_line in self._line_to_struc and self._line_to_struc[self._active_line][5] is None:

                m3_to_mm3 = float(math.pow(1000,3))
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

                    slm_text_pl_thk = 'Minimum plate thickness (BOW SLAMMING): '+str(round(slm_min_pl_thk,1))+' [mm]' \
                        if obj_scnt_calc_stf.get_pl_thk() * 1000 < slm_min_pl_thk else None

                    slm_text_min_web_thk = 'Minimum web thickness (BOW SLAMMING): '+str(round(slm_min_web_thk,1))+' [mm]' \
                        if obj_scnt_calc_stf.get_web_thk()*1000 < slm_min_web_thk else None
                    if slm_zpl_req is not None:
                        slm_text_min_zpl = 'Minimum section modulus (BOW SLAMMING): '+str(round(slm_zpl_req,1))+' [cm^3]' \
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


                #printing the minimum section modulus
                x1, x2, x3 = 15,25,35

                self._result_canvas.create_text([x+0*dx, (y+0*dy)*1],
                                                text= 'Special provisions - DNV-OS-C101 - checks for section, '
                                                      'web thickness and plate thickness.',
                                                font=self._text_size["Text 9 bold"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x+0*dx, (y+2*dy)*1],
                                                text= 'Section modulus check',
                                                font=self._text_size["Text 9"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x+0*dx, (y+3*dy)*1],
                                                text= 'Shear area check',
                                                font=self._text_size["Text 9"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x+0*dx, (y+4*dy)*1],
                                                text= 'Plate thickness check',
                                                font=self._text_size["Text 9"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + x1*dx, (y+1*dy)*1],
                                                text= 'Minimum value',
                                                font=self._text_size["Text 9"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x+ x2*dx, (y+1*dy)*1],
                                                text= 'Actual value',
                                                font=self._text_size["Text 9"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x+ x3*dx, (y+1*dy)*1],
                                                text= 'Accepted?',
                                                font=self._text_size["Text 9"],anchor='nw', fill=self._color_text)

                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = '(shear issue, change thickness or web height)'
                else:
                    text =  str('%.4E' % decimal.Decimal(min_sec_mod * m3_to_mm3)) +\
                            ' [mm^3] ' if not slm_text_min_zpl else slm_text_min_zpl
                self._result_canvas.create_text([x + x1*dx, (y+2*dy)*1], text= text,
                                                font=self._text_size["Text 9 bold"],anchor='nw', fill=self._color_text)

                # printing the calculated sectiton modulus
                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = 'tw issue - slamming'
                else:
                    text = str('%.4E' % decimal.Decimal(min(sec_mod[1], sec_mod[0])*m3_to_mm3))+ ' [mm^3]' \
                        if not slm_text_min_zpl else str(slm_zpl)+'- zpl [cm^3]'
                self._result_canvas.create_text([x + x2*dx, (y+2*dy)*1],
                                               text=text,font=self._text_size['Text 9 bold'],anchor='nw',
                                                fill = color_sec)

                self._result_canvas.create_text([x + x3*dx, (y+2*dy)*1],
                                               text='Ok' if min(sec_mod[1], sec_mod[0])*m3_to_mm3 >
                                                            min_sec_mod * m3_to_mm3 else 'Not ok',
                                                font=self._text_size['Text 9 bold'],anchor='nw',
                                                fill=color_sec)

                #minimum shear area
                text = str('%.4E' % decimal.Decimal(min_shear * m2_to_mm2))+' [mm^2] ' \
                    if not slm_text_min_web_thk else str(round(slm_min_web_thk,1))+' [mm]'
                self._result_canvas.create_text([x + x1*dx, (y+3*dy)*1],
                                               text = text,
                                               font=self._text_size["Text 9 bold"],anchor='nw',fill=self._color_text)
                text = str('%.4E' % decimal.Decimal(shear_area * m2_to_mm2 ))+' [mm^2]' \
                    if not slm_text_min_web_thk else str(obj_scnt_calc_stf.get_web_thk()*1000)+' [mm]'
                self._result_canvas.create_text([x + x2*dx, (y+3*dy)*1],
                                               text= text,
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_shear)
                self._result_canvas.create_text([x + x3*dx, (y+3*dy)*1],
                                               text= 'Ok' if shear_area * m2_to_mm2 > min_shear * m2_to_mm2 else 'Not ok',
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_shear)

                #minimum thickness for plate
                text = str(round(min_thk,1)) + ' [mm]' if not slm_text_pl_thk \
                    else 'SLAMMING'+str(slm_min_pl_thk)+' [mm]'
                self._result_canvas.create_text([x + x1*dx, (y+4*dy)*1],
                                               text=text,
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=self._color_text)
                self._result_canvas.create_text([x + x2*dx, (y+4*dy)*1],
                                               text=str(obj_scnt_calc_pl.get_pl_thk()*1000)+' [mm] ',
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_shear)
                self._result_canvas.create_text([x + x3*dx, (y+4*dy)*1],
                                               text='Ok' if obj_scnt_calc_pl.get_pl_thk()*1000 > min_thk else 'Not ok',
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_shear)


                # buckling results
                start_y, y = 5, 10
                if self._PULS_results != None and self._new_buckling_method.get() == 'DNV PULS':
                    line_results = state['PULS colors'][self._active_line]
                    puls_res = self._PULS_results.get_puls_line_results(self._active_line)
                    if puls_res != None:
                        geo_problem = False
                        if type(puls_res['Ultimate capacity']['Actual usage Factor'][0]) != str:
                            ult_text = 'Ultimate capacity usage factor:  ' + str(puls_res['Ultimate capacity']
                                                                                 ['Actual usage Factor'][
                                                                                     0] / self._new_puls_uf.get())
                        else:
                            geo_problem = True
                            ult_text = puls_res['Ultimate capacity']['Actual usage Factor'][0]
                        if puls_res['Buckling strength']['Actual usage Factor'][0] != None:
                            buc_text = 'Buckling capacity usage factor:  ' + str(puls_res['Buckling strength']
                                                                                 ['Actual usage Factor'][
                                                                                     0] / self._new_puls_uf.get())
                        else:
                            buc_text = 'Buckling capacity usage factor:  None - geometric issue'

                        loc_label = 'Local geom req (PULS validity limits)' if \
                            obj_scnt_calc_stf.get_puls_sp_or_up() == 'SP' else 'Geom. Req (PULS validity limits)'
                        csr_label = 'CSR-Tank requirements (primary stiffeners)' if \
                            obj_scnt_calc_stf.get_puls_sp_or_up() == 'SP' else 'CSR-Tank req'
                        if geo_problem:
                            loc_geom = 'Not ok: '
                            for key, value in puls_res[loc_label].items():
                                if value[0] == 'Not ok':
                                    loc_geom += key + ' '
                        else:
                            loc_geom = 'Ok' if all(
                                [val[0] == 'Ok' for val in puls_res[loc_label]
                                .values()]) else 'Not ok'
                        csr_geom = 'Ok' if all(
                            [val[0] in ['Ok', '-'] for val in puls_res[csr_label]
                            .values()]) else 'Not ok'
                        loc_geom = loc_label + ':   ' + loc_geom
                        csr_geom = csr_label+':   ' + csr_geom
                        self._result_canvas.create_text([x * 1, y + (start_y+0) * dy], text='PULS results',
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill = self._color_text)
                        self._result_canvas.create_text([x * 1, y + (start_y+1) * dy], text=buc_text,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['buckling'])
                        self._result_canvas.create_text([x * 1, y + (start_y+2) * dy], text=ult_text,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['ultimate'])
                        self._result_canvas.create_text([x * 1, y + (start_y+3) * dy], text=loc_geom,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['local geometry'])
                        self._result_canvas.create_text([x * 1, y + (start_y+4) * dy], text=csr_geom,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['csr'])
                    else:
                        self._result_canvas.create_text([x * 1, y + (start_y+0) * dy],
                                                        text='PULS results not avaliable for this line.\n'
                                                             'Run or update lines.',
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill='Orange')
                elif self._new_buckling_method.get() == 'DNV-RP-C201 - prescriptive':
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

                    self._result_canvas.create_text([x * 1, (y+(start_y+0)*dy) * 1],
                                                   text='Buckling results DNV-RP-C201 - prescriptive - (plate, stiffener, girder):',
                                                   font=self._text_size["Text 9 bold"], anchor='nw',
                                                    fill = self._color_text)

                    self._result_canvas.create_text([x + dx*0, (y+(start_y+2)*dy) * 1],
                                               text='Overpressure plate side',font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*0, (y+(start_y+3)*dy) * 1],
                                               text='Overpressure stiffener side',font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*0, (y+(start_y+4)*dy) * 1],
                                               text='Resistance between stiffeners',font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*0, (y+(start_y+5)*dy) * 1],
                                               text='Shear capacity',font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*0, (y+(start_y+6)*dy) * 1],
                                               text='Maximum web height [mm]',
                                                    font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*0, (y+(start_y+7)*dy) * 1],
                                               text='Maximum flange width [mm]',
                                                    font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text)

                    #'Local buckling'
                    x1, x2, x3 = 15,25,35
                    self._result_canvas.create_text([x + dx*15, (y+(start_y+1)*dy) * 1],
                                               text='Plate',font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*25, (y+(start_y+1)*dy) * 1],
                                               text='Stiffener',font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=self._color_text)
                    self._result_canvas.create_text([x + dx*35, (y+(start_y+1)*dy) * 1],
                                               text='Girder',font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=self._color_text)
                    x_mult = x1
                    self._result_canvas.create_text([x + dx*x_mult , (y+(start_y+2)*dy) * 1],
                                               text=str(round(buckling['Plate']['Plate buckling'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)
                    x_mult = x2
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+2)*dy) * 1],
                                               text=str(round(buckling['Stiffener']['Overpressure plate side'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+3)*dy) * 1],
                                               text=str(round(buckling['Stiffener']['Overpressure stiffener side'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)

                    stfweb = round(buckling['Local buckling']['Stiffener'][0],3)*1000
                    stffl = round(buckling['Local buckling']['Stiffener'][1],3)*1000

                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+4)*dy) * 1],
                                               text=str(round(buckling['Stiffener']['Resistance between stiffeners'],3))
                                                    ,font=self._text_size["Text 9 bold"],
                                               anchor='nw',
                                                    fill= color_buckling)
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+5)*dy) * 1],
                                               text=str(round(buckling['Stiffener']['Shear capacity'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',
                                                    fill=color_buckling)


                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+6)*dy) * 1],
                                               text=str(stfweb),
                                                    font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text if obj_scnt_calc_stf is None else 'red'
                                                    if obj_scnt_calc_stf.hw > stfweb else 'green')
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+7)*dy) * 1],
                                               text=str(stffl),
                                                    font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text if obj_scnt_calc_stf is None else 'red'
                                                    if obj_scnt_calc_stf.b > stffl else 'green')
                    x_mult = x3
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+2)*dy) * 1],
                                               text=str(round(buckling['Girder']['Overpressure plate side'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+3)*dy) * 1],
                                               text=str(round(buckling['Girder']['Overpressure girder side'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+4)*dy) * 1],
                                               text=str(round(buckling['Girder']['Shear capacity'],3)),
                                                    font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)

                    gweb = round(buckling['Local buckling']['Girder'][0],3)*1000
                    gfl = round(buckling['Local buckling']['Girder'][1],3)*1000
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+6)*dy) * 1],
                                               text=str(gweb),
                                                    font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text if obj_scnt_calc_girder is None else
                        'red' if obj_scnt_calc_girder.hw > gweb else 'green')
                    self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+7)*dy) * 1],
                                               text=str(gfl),
                                                    font=self._text_size["Text 9"],
                                               anchor='nw',fill=self._color_text if obj_scnt_calc_girder is None else
                        'red' if obj_scnt_calc_girder.b > gfl else 'green')

                    #
                    # self._result_canvas.create_text([x + dx*x_mult, (y+(start_y+7)*dy) * 1],
                    #                            text=str(round(buckling['Local buckling']['Girder'][1],3)),
                    #                                 font=self._text_size["Text 9"],
                    #                            anchor='nw',fill=color_buckling)


                elif self._new_buckling_method.get() == 'ML-CL (PULS based)':

                    self._result_canvas.create_text([x * 1, (y+(start_y+0)*dy) * 1],
                                                    text='Buckling results ANYstructure ML algorithm:',
                                                    font=self._text_size["Text 9 bold"], anchor='nw',
                                                    fill = self._color_text)
                    self._result_canvas.create_text([x * 1, (y+(start_y+1)*dy) * 1],
                                                    text='Buckling: ' + self._ML_classes[state['ML buckling class'][current_line]['buckling']],
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=state['ML buckling colors'][current_line]['buckling'])
                    self._result_canvas.create_text([x * 1, (y+(start_y+2)*dy) * 1],
                                                    text='Ultimate: ' +self._ML_classes[state['ML buckling class'][current_line]['ultimate']],
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=state['ML buckling colors'][current_line]['ultimate'])
                    if obj_scnt_calc_pl.get_puls_sp_or_up() == 'SP':
                        csr = state['ML buckling class'][current_line]['CSR']
                        csr_str = ['Ok' if csr[0] == 1 else 'Not ok', 'Ok' if csr[1] == 1 else 'Not ok',
                                   'Ok' if csr[2] == 1 else 'Not ok', 'Ok' if csr[3] == 1 else 'Not ok']
                        self._result_canvas.create_text([x * 1, (y+(start_y+3)*dy) * 1],
                                                        text='CSR requirements (stiffener):  plate-'+ csr_str[0]+ ' web-'+
                                                             csr_str[1] + ' web/flange ratio-'+ csr_str[2] +
                                                             ' flange-'+ csr_str[3] ,
                                                        font=self._text_size["Text 9"],
                                                        anchor='nw',
                                                        fill=state['ML buckling colors'][current_line]['CSR requirement'])
                    else:
                        csr = state['ML buckling class'][current_line]['CSR']
                        csr_str = 'Ok' if csr[0] == 1 else 'Not ok'
                        self._result_canvas.create_text([x * 1, (y+(start_y+3)*dy) * 1],
                                                        text='CSR requirements (stiffener):  Plate slenderness -'+
                                                             csr_str,
                                                        font=self._text_size["Text 9"],
                                                        anchor='nw',
                                                        fill=state['ML buckling colors'][current_line]['CSR requirement'])


                # fatigue results

                self._result_canvas.create_text([x * 1, (y+(start_y+8)*dy) * 1],
                                                text='Fatigue results (DNVGL-RP-C203): ',
                                                font=self._text_size["Text 9 bold"], anchor='nw', fill = self._color_text)

                if self._line_to_struc[current_line][2] != None:
                    if state['fatigue'][current_line]['damage'] is not None:
                        damage = state['fatigue'][current_line]['damage']
                        dff = state['fatigue'][current_line]['dff']
                        self._result_canvas.create_text([x * 1, (y + (start_y+9) * dy) * 1],
                                                        text='Total damage (DFF not included): '+str(round(damage,3)) +
                                                             '  |  With DFF = '+str(dff)+' --> Damage: '+
                                                             str(round(damage*dff,3)),
                                                        font=self._text_size["Text 9 bold"], anchor='nw',
                                                        fill=color_fatigue)
                    else:
                        self._result_canvas.create_text([x * 1, (y + (start_y+9) * dy) * 1],
                                                        text='Total damage: NO RESULTS ',
                                                        font=self._text_size["Text 9 bold"],
                                                        anchor='nw', fill = self._color_text)
                else:
                    self._result_canvas.create_text([x * 1, (y + (start_y+9) * dy) * 1],
                                                    text='Total damage: NO RESULTS ',
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill = self._color_text)

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

                text = 'Results for cylinders and curved plates/panels:'
                self._result_canvas.create_text([x * 1, y * 1],
                                                text=text, font=self._text_size['Text 12 bold'], anchor='nw',
                                                fill = self._color_text)
                y_location = 3
                results = cyl_obj.get_utilization_factors()
                for key, value in results.items():
                    if key in ['Weight', 'Need to check column buckling']:
                        continue

                    if key != 'Stiffener check':
                        text_key = key
                        if key == 'Column stability check':
                            if results['Need to check column buckling'] == False:
                                continue
                            text_value = 'N/A' if value is None else 'OK' if value else 'Not ok'
                        else:
                            text_value = 'N/A' if value is None else str(round(value, 2))

                        if value is None:
                            uf_col = 'grey'
                        else:
                            uf_col = 'red' if any([value > 1, value == False]) else 'green'
                        self._result_canvas.create_text([x*1, y+dy*y_location],
                                                       text=text_key,font=self._text_size['Text 10 bold'],anchor='nw',
                                                    fill = self._color_text)
                        self._result_canvas.create_text([dx*20, dy*y_location],
                                                       text=text_value,font=self._text_size['Text 10 bold'],anchor='nw',
                                                        fill=uf_col)
                    else:

                        if value is not None:
                            y_location +=1
                            self._result_canvas.create_text([x, dy*y_location],
                                                            text='Stiffener requirement checks:',
                                                            font=self._text_size['Text 10 bold'],
                                                            anchor='nw',
                                                            fill = self._color_text)
                            y_location += 1
                            idx_y, idx_x = 0, 0

                            for stf_type, chk_bool in value.items():
                                stf_text = stf_type

                                chk_text = 'OK' if chk_bool == True else 'Not OK' if chk_bool == False else 'N/A'

                                self._result_canvas.create_text([10*dx*idx_x, dy*y_location],
                                                                text=stf_text, font=self._text_size['Text 10 bold'],
                                                                anchor='nw',
                                                                fill=self._color_text if not value else 'green')

                                self._result_canvas.create_text([10*dx*idx_x, y + (y_location+1)*dy],
                                                                text=chk_text, font=self._text_size['Text 10 bold'],
                                                                anchor='nw',
                                                                fill='green' if chk_bool == True else 'red' if
                                                                chk_bool == False else self._color_text)
                                idx_y += 1
                                idx_x += 1


                    y_location += 1

    def report_generate(self, autosave = False):
        '''
        Button is pressed to generate a report of the current structure.
        :return:
        '''

        if not autosave:
            save_file = filedialog.asksaveasfile(mode="w", defaultextension=".pdf")
            filename = save_file.name
            if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
                return
        else:
            filename = 'testrun.pdf'

        if self._line_dict == {}:
            tk.messagebox.showerror('No lines', 'No lines defined. Cannot make report.')
            return

        if os.path.isfile('current_comps.png'):
            os.remove('current_comps.png')
            self.grid_display_tanks(save = True)
        else:
            self.grid_display_tanks(save=True)

        doc = LetterMaker(filename, "Section results", 10, self)
        doc.createDocument()
        doc.savePDF()
        try:
            os.startfile(filename)
        except FileNotFoundError:
            pass
        self._new_colorcode_beams.set(False)
        self._new_colorcode_plates.set(False)
        self._new_colorcode_pressure.set(False)
        self.update_frame()

    def table_generate(self, autosave = False):

        if not autosave:
            save_file = filedialog.asksaveasfile(mode="w", defaultextension=".pdf")
            filename = save_file.name
            if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
                return
        else:
            filename = 'testrun.pdf'

        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate

        if self._line_dict == {}:
            tk.messagebox.showerror('No lines', 'No lines defined. Cannot make report.')
            return

        doc_dat = LetterMaker(filename, "Section results", 10, self)
        doc = SimpleDocTemplate(filename, pagesize=landscape(letter))
        elements = doc_dat.createTable()
        doc.build(elements)
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

            for line, obj in self._line_to_struc.items():
                obj[0].need_recalc = True
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def new_point(self,copy=False,move=False, redo = None):
        '''
        Adds a point number and coordinates to the point dictionary. Type is 'p1' = [x0,y0]
        '''

        try:
            if copy:
                x_coord = self._new_point_x.get()/1000 + self._point_dict[self._active_point][0]
                y_coord = self._new_point_y.get()/1000 + self._point_dict[self._active_point][1]
            elif move:
                x_coord = self._new_point_x.get()/1000 + self._point_dict[self._active_point][0] \
                    if redo is None else redo[0]
                y_coord = self._new_point_y.get()/1000 + self._point_dict[self._active_point][1]\
                    if redo is None else redo[1]
            else:
                x_coord = (self._new_point_x.get() / 1000)
                y_coord = (self._new_point_y.get() / 1000)

            # Finding name of the new point
            current_point = ''
            if move:
                current_point, current_coords = self._active_point, self._point_dict[self._active_point]
            else:
                found_name = False
                if len(self._point_dict) == 0:
                    current_point = 'point1'
                    found_name = True
                else:
                    counter = 1
                    while not found_name:
                        current_point = 'point'+str(counter)
                        if current_point not in self._point_dict.keys():
                            found_name = True
                        else:
                            counter += 1
            self._new_line_p1.set(get_num(current_point))
            # Creating the point
            # No point is created if another point is already there

            if [x_coord,y_coord] not in self._point_dict.values():
                self._point_dict[current_point] = [x_coord, y_coord]
                self._active_point = current_point
                if move:
                    self.logger(point=current_point, move_coords=(current_coords,[x_coord, y_coord]))
                else:
                    self.logger(point=current_point, move_coords=None)

            self.update_frame()
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def move_line(self,event = None):
        if self._line_is_active:
            line = self._line_dict[self._active_line]
            for pt_num in self._line_dict[self._active_line]:
                self._active_point = 'point'+str(pt_num)
                self._point_is_active = True
                self.move_point()
        else:
            messagebox.showinfo(title='Input error', message='A line must be selected (left click).')

    def move_point(self, event = None, redo = None):
        '''
        Moving a point.
        :return:
        '''
        if self._point_is_active:
            self.new_point(move=True, redo=redo) # doing the actual moving
            for line,data in self._line_dict.items():
                # updating the span and deleting compartments (if not WT)
                if get_num(self._active_point) in data:
                    coord1 = self._point_dict['point'+str(data[0])]
                    coord2 = self._point_dict['point'+str(data[1])]
                    if line in self._line_to_struc.keys():
                        self._line_to_struc[line][0].Plate.set_span(dist(coord1,coord2))
                        self._line_to_struc[line][0].Plate.set_span(dist(coord1, coord2))
                        self._PULS_results.result_changed(line)
                        if self._line_to_struc[line][0].Plate.get_structure_type() not in ['GENERAL_INTERNAL_NONWT',
                                                                                                'FRAME']:
                            self._tank_dict = {}
                            self._main_grid.clear()
                            self._compartments_listbox.delete(0, 'end')

            for line, obj in self._line_to_struc.items():
                obj[0].need_recalc = True
            self.update_frame()
        else:
            messagebox.showinfo(title='Input error', message='A point must be selected (right click).')

    def copy_point(self, event = None):
        '''
        Using the same input as new point, but with separate button.
        :return:
        '''
        if self._point_is_active:
            self.new_point(copy=True)
        else:
            messagebox.showinfo(title='Input error', message='A point must be selected (right click).')

    def new_line(self, event = None, redo = None):
        '''
        Adds line to line dictionary. Type is 'line1' = [p1,p2]
        '''

        try:
            # if's ensure that the new line does not exist already and that the point input is not an invalid point.
            if redo is None:
                first_point, second_point = 'point' + str(self._new_line_p1.get()), \
                                            'point' + str(self._new_line_p2.get())
            else:
                first_point, second_point = redo
            first_point_num, second_point_num = get_num(first_point), get_num(second_point)

            if first_point in self._point_dict.keys() and second_point in self._point_dict.keys() \
                    and first_point != second_point:
                line_str, line_str_rev  = self.make_point_point_line_string(first_point_num, second_point_num)

                if line_str and line_str_rev not in self._line_point_to_point_string:
                    name = False
                    counter = 1
                    while not name:
                        current_name = 'line' + str(counter)
                        if current_name not in self._line_dict.keys():
                            name = True
                        counter += 1

                    self._line_dict[current_name] = [first_point_num, second_point_num]

                    self.update_frame()
                    self.logger(line=[current_name, redo])

                    # making stings from two points difining the lines, e.g. for line 1 string could be 'p1p2' and 'p2p1'
                    self._line_point_to_point_string.append(line_str)
                    self._line_point_to_point_string.append(line_str_rev)

                    self.add_to_combinations_dict(current_name)
            for line, obj in self._line_to_struc.items():
                obj[0].need_recalc = True
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a line number.')

    def new_structure(self, event = None, pasted_structure = None, multi_return = None, toggle_multi = None,
                      suspend_recalc = False, cylinder_return = None):
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

        if all([pasted_structure == None, multi_return == None]):
            if any([self._new_stf_spacing.get()==0, self._new_plate_thk.get()==0, self._new_stf_web_h.get()==0,
                    self._new_stf_web_t.get()==0]):
                mess = tk.messagebox.showwarning('No propertied defined', 'No properties is defined for the line!\n'
                                                                          'Define spacing, web height, web thickness etc.\n'
                                                                          'Either press button with stiffener or input'
                                                                          'manually.', type='ok')
                return

        if self._line_is_active or multi_return != None:
            # structure dictionary: name of line : [ 0.Structure class, 1.calc scantling class,
            # 2.calc fatigue class, 3.load object, 4.load combinations result ]
            CylinderObj = None
            if multi_return is not None:
                prop_dict = multi_return[0].get_main_properties() # From optimizer.
            elif toggle_multi is not None:
                prop_dict = toggle_multi
            elif pasted_structure is None:
                calc_dom = self._new_calculation_domain.get()
                obj_dict = {'mat_yield': [self._new_material.get()*1e6, 'Pa'],
                            'mat_factor': [self._new_material_factor.get(), ''],
                            'span': [self._new_field_len.get()/1000, 'm'],
                            'spacing': [self._new_stf_spacing.get()/1000, 'm'],
                            'plate_thk': [self._new_plate_thk.get()/1000, 'm'],
                            'stf_web_height': [self._new_stf_web_h.get()/1000, 'm'],
                            'stf_web_thk': [self._new_stf_web_t.get()/1000, 'm'],
                            'stf_flange_width': [self._new_stf_fl_w.get()/1000, 'm'],
                            'stf_flange_thk': [self._new_stf_fl_t.get()/1000, 'm'],
                            'structure_type': [self._new_stucture_type.get(), ''],
                            'stf_type': [self._new_stf_type.get(), ''],
                            'sigma_y1': [self._new_sigma_y1.get(), 'MPa'],
                            'sigma_y2': [self._new_sigma_y2.get(), 'MPa'],
                            'sigma_x1': [self._new_sigma_x1.get(), 'MPa'],
                            'sigma_x2': [self._new_sigma_x2.get(), 'MPa'],
                            'tau_xy': [self._new_tauxy.get(), 'MPa'],
                            'plate_kpp': [self._new_plate_kpp.get(), ''],
                            'stf_kps': [self._new_stf_kps.get(), ''],
                            'stf_km1': [self._new_stf_km1.get(), ''],
                            'stf_km2': [self._new_stf_km2.get(), ''],
                            'stf_km3': [self._new_stf_km3.get(), ''],
                            'press_side': [self._new_pressure_side.get(), ''],
                            'structure_types':[self._structure_types, ''],
                            'zstar_optimization': [self._new_zstar_optimization.get(), ''],
                            'puls buckling method': [self._new_puls_method.get(), ''],
                            'puls boundary': [self._new_puls_panel_boundary.get(), ''],
                            'puls stiffener end': [self._new_buckling_stf_end_support.get(), ''],
                            'puls sp or up':  [self._new_puls_sp_or_up.get(), ''],
                            'puls up boundary': [self._new_puls_up_boundary.get(), ''],
                            'panel or shell': [self._new_panel_or_shell.get(), '']}

                obj_dict_pl = copy.copy(obj_dict)
                obj_dict_stf = copy.copy(obj_dict)
                obj_dict_girder = copy.copy(obj_dict)

                obj_dict_girder['stf_web_height'] =  [self._new_girder_web_h.get()/1000, 'm']
                obj_dict_girder['stf_web_thk'] = [self._new_girder_web_t.get() / 1000, 'm']
                obj_dict_girder['stf_flange_width'] = [self._new_girder_fl_w.get() / 1000, 'm']
                obj_dict_girder['stf_flange_thk'] =  [self._new_girder_fl_t.get() / 1000, 'm']
                obj_dict_girder['stf_type'] = [self._new_girder_type.get(), '']
                
                main_dict = dict()
                main_dict['minimum pressure in adjacent spans'] = [self._new_buckling_min_press_adj_spans.get(), '']
                main_dict['material yield'] = [self._new_material.get()*1e6, 'Pa']
                main_dict['load factor on stresses'] = [self._new_buckling_lf_stresses.get(), '']
                main_dict['load factor on pressure'] = [1, '']
                main_dict['buckling method'] = [self._new_puls_method.get(), '']
                main_dict['stiffener end support'] =[self._new_buckling_stf_end_support.get(), '']  # 'Continuous'
                main_dict['girder end support'] = [self._new_buckling_girder_end_support.get(), '']  # 'Continuous'
                main_dict['tension field'] = [self._new_buckling_tension_field.get(), '']  # 'not allowed'
                main_dict['plate effective agains sigy'] = [self._new_buckling_effective_against_sigy.get(), '']  # True
                main_dict['buckling length factor stf'] = [self._new_buckling_length_factor_stf.get(), '']
                main_dict['buckling length factor girder'] = [self._new_buckling_length_factor_stf.get(), '']
                main_dict['km3'] = [self._new_buckling_km3.get(), '']  # 12
                main_dict['km2'] = [self._new_buckling_km2.get(), '']  # 24
                main_dict['girder distance between lateral support'] = [self._new_buckling_girder_dist_bet_lat_supp, '']
                main_dict['stiffener distance between lateral support'] = [self._new_buckling_stf_dist_bet_lat_supp, '']
                main_dict['panel length, Lp'] = [self._new_panel_length_Lp.get(), '']
                main_dict['pressure side'] = [self._new_pressure_side.get(), '']  # either 'stiffener', 'plate', 'both'
                main_dict['fabrication method stiffener'] = [self._new_buckling_fab_method_stf.get(), '']
                main_dict['fabrication method girder'] = [self._new_buckling_fab_method_girder.get(), '']
                main_dict['calculation domain'] = [self._new_calculation_domain.get(), '']

                prop_dict = {'main dict': main_dict,
                             'Plate': obj_dict_pl,
                             'Stiffener': None if calc_dom == 'Flat plate, unstiffened' else obj_dict_stf,
                             'Girder': None if calc_dom in ['Flat plate, unstiffened', 'Flat plate, stiffened']
                             else obj_dict_girder}

                if self._new_calculation_domain.get() not in ['Flat plate, stiffened','Flat plate, unstiffened',
                                                  'Flat plate, stiffened with girder'] and cylinder_return is None:
                    '''
                    Shell structure.
                     0:'Stiffened panel, flat', 1:'Unstiffened shell (Force input)', 2:'Unstiffened panel (Stress input)',
                     3:'Longitudinal Stiffened shell  (Force input)', 4:'Longitudinal Stiffened panel (Stress input)',
                     5:'Ring Stiffened shell (Force input)', 6:'Ring Stiffened panel (Stress input)',
                     7:'Orthogonally Stiffened shell (Force input)', 8:'Orthogonally Stiffened panel (Stress input)'
                    '''
                    domain_string = self._new_calculation_domain.get()
                    domain_int = self._shell_geometries_map[domain_string]

                    dummy_data = {'span': [self._new_field_len.get()/1000, 'm'],
                                  'plate_thk': [self._new_plate_thk.get()/1000, 'm'],
                                  'structure_type': [self._new_stucture_type.get(), ''],
                                  'sigma_y1': [self._new_sigma_y1.get(), 'MPa'],
                                  'sigma_y2': [self._new_sigma_y2.get(), 'MPa'],
                                  'sigma_x1': [self._new_sigma_x1.get(), 'MPa'],
                                  'sigma_x2': [self._new_sigma_x2.get(), 'MPa'],
                                  'tau_xy': [self._new_tauxy.get(), 'MPa'],
                                  'plate_kpp': [self._new_plate_kpp.get(), ''],
                                  'stf_kps': [self._new_stf_kps.get(), ''],
                                  'stf_km1': [self._new_stf_km1.get(), ''],
                                  'stf_km2': [self._new_stf_km2.get(), ''],
                                  'stf_km3': [self._new_stf_km3.get(), ''],
                                  'press_side': [self._new_pressure_side.get(), ''],
                                  'structure_types':[self._structure_types, ''],
                                  'zstar_optimization': [self._new_zstar_optimization.get(), ''],
                                  'puls buckling method': [self._new_puls_method.get(), ''],
                                  'puls boundary': [self._new_puls_panel_boundary.get(), ''],
                                  'puls stiffener end': [self._new_buckling_stf_end_support.get(), ''],
                                  'puls sp or up':  [self._new_puls_sp_or_up.get(), ''],
                                  'puls up boundary': [self._new_puls_up_boundary.get(), ''],
                                  'panel or shell': [self._new_panel_or_shell.get(), ''],
                                  'mat_factor': [self._new_material_factor.get(), '',],
                                  'spacing': [self._new_stf_spacing.get()/1000, 'm'],}

                    # Main class input

                    # Shell data input
                    shell_dict = {'plate_thk': [self._new_shell_thk.get() / 1000, 'm'],
                                  'radius': [self._new_shell_radius.get() / 1000, 'm'],
                                  'distance between rings, l': [self._new_shell_dist_rings.get() / 1000, 'm'],
                                  'length of shell, L': [self._new_shell_length.get() / 1000, 'm'],
                                  'tot cyl length, Lc': [self._new_shell_tot_length.get() / 1000, 'm'],
                                  'eff. buckling lenght factor': [self._new_shell_k_factor.get(), ''],
                                  'mat_yield': [self._new_shell_yield.get() * 1e6, 'Pa'],
                                  }
                    # Longitudinal stiffener input
                    long_dict = {'spacing': [self._new_stf_spacing.get() / 1000, 'm'],
                                 'stf_web_height': [self._new_stf_web_h.get() / 1000, 'm'],
                                 'stf_web_thk': [self._new_stf_web_t.get() / 1000, 'm'],
                                 'stf_flange_width': [self._new_stf_fl_w.get() / 1000, 'm'],
                                 'stf_flange_thk': [self._new_stf_fl_t.get() / 1000, 'm'],
                                 'stf_type': [self._new_stf_type.get(), ''],
                                 'span': [self._new_field_len.get()/1000, 'm'],
                                 'mat_yield': [self._new_shell_yield.get() * 1e6, 'Pa'],
                                 'panel or shell': ['shell', '']}
                    ring_stf_dict = {'stf_web_height': [self._new_shell_ring_stf_hw.get() / 1000, 'm'],
                                     'stf_web_thk': [self._new_shell_ring_stf_tw.get() / 1000, 'm'],
                                     'stf_flange_width': [self._new_shell_ring_stf_b.get() / 1000, 'm'],
                                     'stf_flange_thk': [self._new_shell_ring_stf_tf.get() / 1000, 'm'],
                                     'stf_type': [self._new_shell_ring_stf_type.get(), ''],
                                     'mat_yield': [self._new_shell_yield.get() * 1e6, 'Pa'],
                                     'panel or shell': ['shell', '']}
                    ring_frame_dict = {'stf_web_height': [self._new_shell_ring_frame_hw.get() / 1000, 'm'],
                                       'stf_web_thk': [self._new_shell_ring_frame_tw.get() / 1000, 'm'],
                                       'stf_flange_width': [self._new_shell_ring_frame_b.get() / 1000, 'm'],
                                       'stf_flange_thk': [self._new_shell_ring_frame_tf.get() / 1000, 'm'],
                                       'stf_type': [self._new_shell_ring_frame_type.get(), ''],
                                       'span': [self._new_field_len.get()/1000, 'm'],
                                       'mat_yield': [self._new_shell_yield.get() * 1e6, 'Pa'],
                                       'panel or shell': ['shell', '']}

                    geometry = self._shell_geometries_map[self._new_calculation_domain.get()]

                    if self._new_shell_stress_or_force.get() == 1:
                        forces = [self._new_shell_Nsd.get(), self._new_shell_Msd.get(), \
                                 self._new_shell_Tsd.get(), self._new_shell_Qsd.get()]
                        sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                            stresses=None, forces=forces,  geometry=geometry, shell_t=self._new_shell_thk.get(),
                            shell_radius=self._new_shell_radius.get(), shell_spacing=self._new_stf_spacing.get(),
                            hw=self._new_stf_web_h.get(), tw=self._new_stf_web_t.get(), b=self._new_stf_fl_w.get(),
                            tf=self._new_stf_fl_t.get(), CylinderAndCurvedPlate=CylinderAndCurvedPlate)
                        self._new_shell_sasd.set(sasd)
                        self._new_shell_smsd.set(smsd)
                        self._new_shell_tTsd.set(tTsd)
                        self._new_shell_tQsd.set(tQsd)
                        #self._new_shell_shsd.set(0)
                    else:
                        stresses = [self._new_shell_sasd.get(), self._new_shell_smsd.get(), self._new_shell_tTsd.get(),
                                    self._new_shell_tQsd.get(), self._new_shell_shsd.get()]
                        sasd, smsd, tTsd, tQsd, shsd = stresses
                        Nsd, Msd, Tsd, Qsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
                            stresses=stresses, geometry=geometry, shell_t=self._new_shell_thk.get(),
                            shell_radius=self._new_shell_radius.get(), shell_spacing=self._new_stf_spacing.get(),
                            hw=self._new_stf_web_h.get(), tw=self._new_stf_web_t.get(), b=self._new_stf_fl_w.get(),
                            tf=self._new_stf_fl_t.get(), CylinderAndCurvedPlate=CylinderAndCurvedPlate)
                        self._new_shell_Nsd.set(Nsd)
                        self._new_shell_Msd.set(Msd)
                        self._new_shell_Tsd.set(Tsd)
                        self._new_shell_Qsd.set(Qsd)

                    main_dict_cyl = {'sasd': [sasd*1e6, 'Pa'],
                                 'smsd': [smsd*1e6, 'Pa'],
                                 'tTsd': [tTsd*1e6, 'Pa'],
                                 'tQsd': [tQsd*1e6, 'Pa'],
                                 'psd': [self._new_shell_psd.get() *1e6, 'Pa'],
                                 'shsd': [shsd *1e6, 'Pa'],
                                 'geometry': [self._shell_geometries_map[self._new_calculation_domain.get()], ''],
                                 'material factor':  [self._new_shell_mat_factor.get(), ''],
                                 'delta0': [0.005, ''],
                                 'fab method ring stf':  [self._new_shell_ring_stf_fab_method.get(), ''],
                                 'fab method ring girder':  [self._new_shell_ring_frame_fab_method.get(), ''],
                                 'E-module':  [self._new_shell_e_module.get(), 'Pa'],
                                 'poisson':  [self._new_shell_poisson.get(), ''],
                                 'mat_yield': [self._new_shell_yield.get() *1e6, 'Pa'],
                                 'length between girders': [self._new_shell_ring_frame_length_between_girders.get()/1000, 'm'],
                                 'panel spacing, s': [self._new_shell_panel_spacing.get()/1000, 'm'],
                                 'ring stf excluded': [self._new_shell_exclude_ring_stf.get(), ''],
                                 'ring frame excluded': [self._new_shell_exclude_ring_frame.get(), '',],
                                     'ULS or ALS': [self._new_shell_uls_or_als.get(), '',],
                                     'end cap pressure': [self._new_shell_end_cap_pressure_included.get(), '']
                    }

                    for key, value in dummy_data.items():
                        if key not in long_dict.keys():
                            long_dict[key] = value
                        if key not in ring_stf_dict.keys():
                            ring_stf_dict[key] = value
                        if key not in ring_frame_dict.keys():
                            ring_frame_dict[key] = value

                    CylinderObj = CylinderAndCurvedPlate(main_dict_cyl, Shell(shell_dict),
                                                         long_stf=None if geometry in [1,2,5,6]
                                                         else Structure(long_dict),
                                                          ring_stf=None if any([geometry in [1,2,3,4],
                                                                                self._new_shell_exclude_ring_stf.get()])
                                                          else Structure(ring_stf_dict),
                                                          ring_frame=None if any([geometry in [1,2,3,4],
                                                                                  self._new_shell_exclude_ring_frame.get()])
                                                          else Structure(ring_frame_dict))
                elif cylinder_return is not None:

                    main_dict_cyl, shell_dict, long_dict, ring_stf_dict, ring_frame_dict = \
                        cylinder_return.get_all_properties()
            else:
                prop_dict = pasted_structure.get_main_properties()


            if self._active_line not in self._line_to_struc.keys() :
                self._line_to_struc[self._active_line] = [None, None, None, [None], {}, None]
                # First entry
                # Flat plate domains: 'Flat plate, stiffened with girder', 'Flat plate, stiffened', Flat plate, unstiffened'
                cdom = self._new_calculation_domain.get()
                All = AllStructure(Plate=CalcScantlings(prop_dict['Plate']),
                                   Stiffener=None if cdom == 'Flat plate, unstiffened'
                                   else CalcScantlings(prop_dict['Stiffener']),
                                   Girder=None if cdom in ['Flat plate, unstiffened', 'Flat plate, stiffened']
                                   else CalcScantlings(prop_dict['Girder']),
                                   main_dict=prop_dict['main dict'])

                self._sections = add_new_section(self._sections, struc.Section(obj_dict_stf))
                self._line_to_struc[self._active_line][0] = All
                self._line_to_struc[self._active_line][5] = CylinderObj
                if self._line_to_struc[self._active_line][0].Plate.get_structure_type() not in \
                        self._structure_types['non-wt']:
                    self._tank_dict = {}
                    self._main_grid.clear()
                    self._compartments_listbox.delete(0, 'end')
                if self._new_calculation_domain.get() not in ['Flat plate, stiffened','Flat plate, unstiffened',
                                                  'Flat plate, stiffened with girder']:
                    CylinderObj = CylinderAndCurvedPlate(main_dict_cyl, Shell(shell_dict),
                                                         long_stf=None if geometry in [1,2,5,6]
                                                         else Structure(long_dict),
                                                          ring_stf=None if any([geometry in [1,2,3,4],
                                                                                self._new_shell_exclude_ring_stf.get()])
                                                          else Structure(ring_stf_dict),
                                                          ring_frame=None if any([geometry in [1,2,3,4],
                                                                                  self._new_shell_exclude_ring_frame.get()])
                                                          else Structure(ring_frame_dict))

                    self._line_to_struc[self._active_line][5] = CylinderObj

            else:
                prev_type = self._line_to_struc[self._active_line][0].Plate.get_structure_type()
                #cdom = self._line_to_struc[self._active_line][0].calculation_domain
                #prev_calc_obj = copy.deepcopy(self._line_to_struc[self._active_line][1])
                prev_all_obj = copy.deepcopy(self._line_to_struc[self._active_line][0])
                self._line_to_struc[self._active_line][0].set_main_properties(prop_dict)

                if self._new_scale_stresses.get() and prev_all_obj.Plate.get_tuple() != \
                        self._line_to_struc[self._active_line][0].Plate.get_tuple():
                    self._line_to_struc[self._active_line][0].Plate = \
                        op.create_new_calc_obj(prev_all_obj.Plate,
                                               self._line_to_struc[self._active_line][0].Plate.get_tuple(),
                                               fup=self._new_fup.get(), fdwn=self._new_fdwn.get())[0]


                self._line_to_struc[self._active_line][0].need_recalc = True

                if self._line_to_struc[self._active_line][2] is not None:
                    calc_dom = self._line_to_struc[self._active_line][0].calculation_domain
                    if calc_dom == 'Flat plate, unstiffened':
                        self._line_to_struc[self._active_line][2] = None
                    else:
                        self._line_to_struc[self._active_line][2].set_main_properties(prop_dict['Stiffener'])

                if prev_type in self._structure_types['non-wt'] and prop_dict['Plate']['structure_type'][0] in \
                                        self._structure_types['internals'] + self._structure_types['horizontal'] + \
                                self._structure_types['vertical']:
                    self._tank_dict = {}
                    self._main_grid.clear()
                    self._compartments_listbox.delete(0, 'end')

                if  None and all([CylinderObj is None, cylinder_return is None,
                                  self._line_to_struc[self._active_line][5] is not None]):
                    self._line_to_struc[self._active_line][5] = None
                elif CylinderObj is not None:
                    if self._line_to_struc[self._active_line][5] is not None and self._new_scale_stresses.get():
                        NewCylinderObj = op.create_new_cylinder_obj(self._line_to_struc[self._active_line][5],
                                                                 CylinderObj.get_x_opt())
                        NewCylinderObj.LongStfObj = None if CylinderObj.LongStfObj is None \
                            else NewCylinderObj.LongStfObj
                        NewCylinderObj.RingStfObj = None if CylinderObj.RingStfObj is None \
                            else NewCylinderObj.RingStfObj
                        NewCylinderObj.RingFrameObj = None if CylinderObj.RingFrameObj is None \
                            else NewCylinderObj.RingFrameObj
                    self._line_to_struc[self._active_line][5] = CylinderObj
                elif cylinder_return is not None:
                    self._line_to_struc[self._active_line][5] = cylinder_return
            try:
                self.calculate_all_load_combinations_for_line_all_lines()
            except (KeyError, AttributeError):
                pass

        else:
            pass

        if self._PULS_results != None:
            self._PULS_results.result_changed(self._active_line)

        if not suspend_recalc:
            # when changing multiple parameters, recalculations are suspended.
            for line, obj in self._line_to_struc.items():
                obj[0].need_recalc = True
            state = self.update_frame()
            if state != None and self._line_is_active:
                self._weight_logger['new structure']['COG'].append(self.get_color_and_calc_state()['COG'])
                self._weight_logger['new structure']['weight'].append(self.get_color_and_calc_state()['Total weight'])
                self._weight_logger['new structure']['time'].append(time.time())
            self.cylinder_gui_mods()

        self.get_unique_plates_and_beams()

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

    def new_tank(self,comp_no,cells, min_el, max_el):
        '''
        Creating the tanks.
        :return:
        '''
        # points, self._point_dict, content), point

        temp_tank_dict = {  'comp_no' : comp_no,
                            'cells' : cells,
                            'min_el' : min_el[1],
                            'max_el' : max_el[1],
                            'content' : self._new_content_type.get(),
                            'added_press' : self._new_overpresure.get(),
                            'acc' : self._accelerations_dict,
                            'density' : self._new_density.get(),
                            'all_types' : self._options_type}

        self._tank_dict['comp' + str(comp_no)] =  Tanks(temp_tank_dict)
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

    def calculate_all_load_combinations_for_line(self, line, limit_state = 'ULS', get_load_info = False):
        '''
        Calculating pressure for line.
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,1]} # DNV  loads factors
        self._load_conditions = ['loaded', 'ballast','tanktest']
        :return:
        '''
        if limit_state == 'FLS':
            return
        results = {} #dict - dnva/dnvb/tanktest/manual
        load_info = []
        # calculating for DNV a and DNV b


        for dnv_ab in ['dnva', 'dnvb']: #, load_factors in self._load_factors_dict.items():
            results[dnv_ab] = []
            for load_condition in self._load_conditions[0:2]:
                returned = self.calculate_one_load_combination(line, dnv_ab, load_condition)
                if returned != None:
                    results[dnv_ab].append(returned[0])
                    [load_info.append(val) for val in returned[1]]

        # calculating for tank test condition
        results['tanktest'] = []
        res_val = self.calculate_one_load_combination(line, "tanktest", 'tanktest')
        results['tanktest'].append(res_val[0])
        [load_info.append(val) for val in res_val[1]]


        # calculating for manual condition
        results['manual'] = []
        res_val = self.calculate_one_load_combination(line, 'manual', 'manual')
        results['manual'].append(res_val[0])
        [load_info.append(val) for val in res_val[1]]

        results['slamming'] = []
        res_val = self.calculate_one_load_combination(line, 'slamming', 'slamming')
        results['slamming'].append(res_val[0])
        [load_info.append(val) for val in res_val[1]]

        if get_load_info:
            return load_info
        return results

    def calculate_one_load_combination(self, current_line, comb_name, load_condition):
        '''
        Creating load combination for ULS.
        Inserted into self._line_to_struc index = 4
        "dnva", "line12", "static_ballast_10m"
        #load combination dictionary (comb,line,load) : [stat - DoubleVar(), dyn - DoubleVar], on/off - IntVar()]
        :return:
        '''

        defined_loads = []
        for load_obj in self._line_to_struc[current_line][3]:
            if load_obj is not None:
                if load_obj.get_limit_state() != 'FLS':
                    defined_loads.append(load_obj)
        if self._tank_dict == {}:
            defined_tanks =  []
        else:
            defined_tanks = [['comp'+str(int(tank_num)), self._tank_dict['comp'+str(int(tank_num))]]
                     for tank_num in self.get_compartments_for_line_duplicates(current_line)]

        coord = (self.get_line_radial_mid(current_line), self.get_line_low_elevation(current_line))

        if load_condition not in ['tanktest','manual','slamming']:
            acc = (self._accelerations_dict['static'], self._accelerations_dict['dyn_'+str(load_condition)])
        else:
            acc = (self._accelerations_dict['static'], 0)

        load_factors_all = self._new_load_comb_dict

        current_line_obj = [current_line, self._line_to_struc[current_line][0].Plate]

        if self._line_to_struc[current_line][0].Plate.get_structure_type() in ['', 'FRAME','GENERAL_INTERNAL_NONWT']:
            return [0, '']
        else:
            return_value = one_load_combination(current_line_obj, coord, defined_loads, load_condition,
                                                defined_tanks, comb_name, acc, load_factors_all)

            return return_value

    def run_optimizer_for_line(self,line,goal,constrains):
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
        for line, obj in self._line_to_struc.items():
            obj[0].need_recalc = True
            if  self._compartments_listbox.get('active') in self.get_compartments_for_line(line):
                self._PULS_results.result_changed(line)

    def delete_line(self, event = None, undo = None, line = None):
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
                point_str = 'p' + str(self._line_dict[line][0]) + 'p' + str(self._line_dict[line][1])
                point_str_rev = 'p' + str(self._line_dict[line][1]) + 'p' + str(self._line_dict[line][0])

                if line in self._line_dict.keys():
                    if line in self._line_to_struc.keys():
                        if self._line_to_struc[line][0].Plate.get_structure_type() not in self._structure_types['non-wt']:
                            self.delete_properties_pressed()
                            self.delete_all_tanks()
                    self._line_dict.pop(line)
                    if line in self._line_to_struc.keys():
                        self._line_to_struc.pop(line)
                    self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str))
                    self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str_rev))
                    self._active_line = ''

                    # Removing from load dict
                    if self._load_dict != {}:
                        loads = list(self._load_dict.keys())
                        for load in loads:
                            if line in self._load_dict[load][1]:
                                self._load_dict[load][1].pop(self._load_dict[load][1].index(line))
                    # Removing from puls results
                    if self._PULS_results is not None:
                        self._PULS_results.result_changed(line)

                self.update_frame()
            else:
                messagebox.showinfo(title='No line.', message='Input line does noe exist.')

        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def delete_point(self, event = None, undo = None, point = None):
        '''
        Deleting point and connected lines.
        '''
        try:
            if point == None:
                point = 'point' + str(self._ent_delete_point.get()) if undo is None else undo

            if point in self._point_dict.keys():
                line_to_delete = []
                # finding the lines that needs to be deleted
                for line, points in self._line_dict.items():
                    if int(self._ent_delete_point.get()) in points:
                        line_to_delete.append(line)
                # deleting the lines and the connected properties. also deleting point to point string list items.
                for line in list(line_to_delete):
                    self.delete_line(line = line)
                    # point_str = 'p' + str(self._line_dict[line][0]) + 'p' + str(self._line_dict[line][1])
                    # point_str_rev = 'p' + str(self._line_dict[line][1]) + 'p' + str(self._line_dict[line][0])
                    # self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str))
                    # self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str_rev))
                    # self._line_dict.pop(line)
                    # # properties are deleted here
                    # if line in self._line_to_struc.keys():
                    #     self._line_to_struc.pop(line)
                # at the en, the points is deleted from the point dict.
                self._point_dict.pop(point)
                self._active_point = ''
            else:
                messagebox.showinfo(title='No point.', message='Input point does not exist.')

            self.update_frame()
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def delete_key_pressed(self, event = None):
        if self._active_line != '':
            self.delete_line(line = self._active_line)
        if self._active_point != '':
            self.delete_point()

    def copy_property(self, event = None):
        ''' Copy a property of a line'''
        if self._active_line not in self._line_to_struc.keys():
            tk.messagebox.showinfo('No properties', 'This line does not have properties.')
            return
        else:
            self.__copied_line_prop = self._active_line

    def paste_property(self, event = None):
        ''' Paste property to line '''
        if self._active_line not in self._line_to_struc.keys():
            if self._line_to_struc[self.__copied_line_prop][5] is not None:
                self.new_structure(cylinder_return=self._line_to_struc[self.__copied_line_prop][5])
            else:
                self.new_structure(pasted_structure=self._line_to_struc[self.__copied_line_prop][0])
        elif self._line_to_struc[self.__copied_line_prop][5] is not None:
            self.new_structure(cylinder_return=self._line_to_struc[self.__copied_line_prop][5])
        elif self._line_to_struc[self._active_line][0].Plate.get_structure_type() !=\
                self._line_to_struc[self.__copied_line_prop][0].Plate.get_structure_type():
            tk.messagebox.showerror('Paste error', 'Can only paste to same structure type. This is to avoid problems '
                                                   'with compartments not detecting changes to watertightness.')
            return
        else:
            self.new_structure(pasted_structure = self._line_to_struc[self.__copied_line_prop][0])

        self.update_frame()

    def delete_properties_pressed(self, event = None, line = None):

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
            for line, obj in self._line_to_struc.items():
                obj[0].need_recalc = True
            self.update_frame()

    def delete_all_tanks(self):
        '''
        Delete the tank that has been selected in the Listbox
        :return:
        '''
        #if self._grid_calc != None:
        self._tank_dict = {}
        self._compartments_listbox.delete(0,'end')
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
                    self._new_material.set(round(properties['mat_yield'][0]/1e6,5))
                    self._new_material_factor.set(properties['mat_factor'][0])
                    self._new_field_len.set(round(properties['span'][0]*1000,5))
                    self._new_plate_thk.set(round(properties['plate_thk'][0]*1000,5))
                    self._new_plate_kpp.set(properties['plate_kpp'][0])
                    self._new_sigma_y1.set(round(properties['sigma_y1'][0],1))
                    self._new_sigma_y2.set(round(properties['sigma_y2'][0],1))
                    self._new_sigma_x1.set(round(properties['sigma_x1'][0],1))
                    self._new_sigma_x2.set(round(properties['sigma_x2'][0], 1))
                    self._new_tauxy.set(round(properties['tau_xy'][0],1))
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
                    self._new_stf_web_h.set(round(properties['stf_web_height'][0]*1000,5))
                    self._new_stf_web_t.set(round(properties['stf_web_thk'][0]*1000,5))
                    self._new_stf_fl_w.set(round(properties['stf_flange_width'][0]*1000,5))
                    self._new_stf_fl_t.set(round(properties['stf_flange_thk'][0]*1000,5))
                    self._new_stf_type.set(properties['stf_type'][0])
                if idx == 2:
                    self._new_girder_web_h.set(round(properties['stf_web_height'][0]*1000,5))
                    self._new_girder_web_t.set(round(properties['stf_web_thk'][0]*1000,5))
                    self._new_girder_fl_w.set(round(properties['stf_flange_width'][0]*1000,5))
                    self._new_girder_fl_t.set(round(properties['stf_flange_thk'][0]*1000,5))
                    self._new_girder_type.set(properties['stf_type'][0])

    def get_highest_pressure(self, line, limit_state = 'ULS'):
        '''
        Returning the highest pressure of a line.
        :return:
        '''
        all_press = list()
        if limit_state == 'ULS':
            pressures = self.calculate_all_load_combinations_for_line(line)
            slm_red, psl, slm_red_pl, slm_red_stf = 1, 0, 1, 1
            for key, value in pressures.items():
                if key != 'slamming':
                    all_press.append(max(value))
                else:
                    if value is not None:
                        for load in self._line_to_struc[line][3]:
                            if load is not None:
                                if load.get_load_condition() == 'slamming':
                                    slm_red_pl = load.get_slamming_reduction_plate()
                                    slm_red_stf = load.get_slamming_reduction_stf()
                        psl = max(value)


            return {'normal':max(all_press), 'slamming': psl, 'slamming plate reduction factor': slm_red_pl,
                    'slamming stf reduction factor': slm_red_stf}
        elif limit_state == 'FLS':
            pass
        else:
            return {'normal':0, 'slamming': 0}

    def get_fatigue_pressures(self, line, accelerations = (0, 0, 0)):
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
                    if fls_exist[exist_i] and load.get_load_condition()=='loaded':
                        pressures['p_ext']['loaded'] = load.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                                    accelerations[0],
                                                                                    self._line_to_struc[line][
                                                                                        0].Plate.get_structure_type())
                    if fls_exist[exist_i] and load.get_load_condition() == 'ballast':
                        pressures['p_ext']['ballast'] = load.get_calculated_pressure(self.get_pressures_calc_coord(line),
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
            compartments = [self._tank_dict['comp'+str(tank)] for tank in self.get_compartments_for_line(line)]
        pressures['p_int'] = {'loaded':0, 'ballast':0, 'part':0}

        for comp in compartments:
            if fls_exist[0] and comp.is_loaded_condition():
                pressures['p_int']['loaded'] = comp.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                            accelerations[0])
            if fls_exist[1] and comp.is_ballast_condition():
                pressures['p_int']['ballast'] = comp.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                            accelerations[1])
            if fls_exist[2] and any([comp.is_loaded_condition(),comp.is_ballast_condition()]):
                pressures['p_int']['part'] = comp.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                            accelerations[2])*0.5
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

    def get_compartments_for_line_duplicates(self,  line):
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

    def get_actual_elevation_from_grid_coords(self,grid_col):
        '''
        Converts coordinates
        :param canv_elevation:
        :return:
        '''

        y_coord = (self._main_grid.get_grid_height() - grid_col)/self._base_scale_factor
        self._main_grid.get_grid_height()
        return y_coord

    def get_grid_coord_from_points_coords(self, point_coord):
        '''
        Converts coordinates to be used in the grid. Returns (row,col). This value will not change with slider.
        :param point:
        :return:
        '''
        row = self._canvas_base_origo[1] - point_coord[1]*self._base_scale_factor
        col = point_coord[0]*self._base_scale_factor
        return (row,col)

    def get_point_coords_from_grid_coords(self, grid_coord):
        '''
        Converts coordinates to be used in the as points. Returns (x,y). This value will not change with slider.
        :param point:
        :return:
        '''
        x_coord = grid_coord[1]/self._base_scale_factor
        y_coord = (self._main_grid.get_grid_height() - grid_coord[0])/self._base_scale_factor
        self._main_grid.get_grid_height()
        self._main_grid.get_grid_width()
        return x_coord,y_coord

    def get_canvas_coords_from_point_coords(self, actual_coords):
        '''
        Returns tuple of canvas points from actual (x,y)
        :param actual_coords:
        :return:
        '''
        canvas_coord_x = self._canvas_draw_origo[0] + actual_coords[0] * self._canvas_scale
        canvas_coord_y = self._canvas_draw_origo[1] - actual_coords[1] * self._canvas_scale

        return (canvas_coord_x, canvas_coord_y)

    def get_line_low_elevation(self,line):
        '''
        Finding elevation of a line. Used to calculate pressures in load combinations.
        :param line:
        :return:
        '''

        return min([self._point_dict['point'+str(point)][1] for point in self._line_dict[line]])

    def get_line_radial_mid(self,line):
        '''
        Getting the horizontal coordinates in the middle of a line.
        :param line:
        :return:
        '''
        return sum([self._point_dict['point' + str(point)][0] for point in self._line_dict[line]])/2

    def get_pressures_calc_coord(self, line):
        ''' Returning coordinates of the pressures calculation basis of a selected line. '''
        p1 = self._point_dict['point'+str(self._line_dict[line][0])]
        p2 = self._point_dict['point'+str(self._line_dict[line][1])]

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

        vector = [end_point[0]-start_point[0], end_point[1]-start_point[1]]

        return start_point[0]+vector[0]*1/3, start_point[1]+vector[1]*1/3

    def get_points(self):
        return self._point_dict

    def get_closest_point(self,given_point):
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
        for point,coords in self._point_dict.items():
            if dist([coords[0],coords[1]], [given_point[0],given_point[1]]) < current_dist:
                current_dist = dist([coords[0],coords[1]], [given_point[0],given_point[1]])
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
                    this_plate = data[0].Stiffener.get_pl_thk()*1000
                    if this_beam not in beams:
                        beams.append(this_beam)
                    if this_plate not in plates:
                        plates.append(this_plate)

        return {'plates':plates, 'beams': beams}

    def make_point_point_line_string(self, point1, point2):
        '''
        For a line, this method makes a string 'p1p2' and 'p2p1'. Ensuring that lines are not overwritten.
        :param point1:
        :param point2:
        :return:
        '''

        return ['p' + str(point1) + 'p' + str(point2), 'p' + str(point2) + 'p' + str(point1)]

    def reset(self):
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
        self._line_is_active = False # True when a line is clicked
        self._active_line = '' # Name of the clicked point
        self._point_is_active = False # True when a point is clicked
        self._active_point = '' # Name of the clicked point
        self.controls() # Function to activate mouse clicks
        self._line_point_to_point_string = [] # This one ensures that a line is not created on top of a line
        self._accelerations_dict = {'static':9.81, 'dyn_loaded':0, 'dyn_ballast':0}
        self._multiselect_lines = []
        self._PULS_results = None
        self.update_frame()

        # Initsializing the calculation grid used for tank definition
        self._main_grid  = grid.Grid(self._grid_dimensions[0], self._grid_dimensions[1])
        self._grid_calc = None

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
        #self._prop_canvas.bind("<MouseWheel>", self.mouse_scroll)

        self._parent.bind('<Control-z>', self.undo)
        #self._parent.bind('<Control-y>', self.redo)
        #self._parent.bind('<Control-p>', self.delete_point)
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
        #self._parent.bind('<Enter>', self.enter_key_pressed)

    def left_arrow(self, event):

        if self._active_line == '':
            return
        else:
            idx = list(self._line_dict.keys()).index(self._active_line)

            if idx -1 >= 0:
                self._active_line =list(self._line_dict.keys())[idx-1]
            else:
                self._active_line = list(self._line_dict.keys())[-1]
        self.update_frame()

    def right_arrow(self, event):

        if self._active_line == '':
            return
        else:
            idx = list(self._line_dict.keys()).index(self._active_line)

            if idx + 1 < len(list(self._line_dict.keys())):
                self._active_line = list(self._line_dict.keys())[idx+1]
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

    def mouse_scroll(self,event):

        if event.y < self._main_canvas.winfo_height():
            self._canvas_scale +=  event.delta/50
            self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale
        else:
            pass

        try:
            state = self.get_color_and_calc_state()
        except AttributeError:
            state = None

        self.update_frame()

    def button_2_click(self, event):
        self._previous_drag_mouse = [event.x, event.y]

    def button_2_click_and_drag(self,event):
        self._canvas_draw_origo = (self._canvas_draw_origo[0]-(self._previous_drag_mouse[0]-event.x),
                                  self._canvas_draw_origo[1]-(self._previous_drag_mouse[1]-event.y))
        self._previous_drag_mouse = (event.x,event.y)
        try:
            state = self.get_color_and_calc_state()
        except AttributeError:
            state = None
        self.update_frame()
        #self.draw_canvas(state=state)

    def button_1_click(self, event = None):
        '''
        When clicking the right button, this method is called.
        method is referenced in
        '''

        self._previous_drag_mouse = [event.x, event.y]
        click_x = self._main_canvas.winfo_pointerx() - self._main_canvas.winfo_rootx()
        click_y = self._main_canvas.winfo_pointery() - self._main_canvas.winfo_rooty()
        self._prop_canvas.delete('all')
        stop = False
        self._active_line = ''
        self._line_is_active = False

        if len(self._line_dict) > 0:
            for key, value in self._line_dict.items():
                if stop:
                    break

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
                        self._line_is_active = True
                        self._active_line = key
                        stop = True
                        break
                    self._new_delete_line.set(get_num(key))

        if self._line_is_active and self._active_line not in self._line_to_struc.keys():
            p1 = self._point_dict['point'+str(self._line_dict[self._active_line][0])]
            p2 = self._point_dict['point'+str(self._line_dict[self._active_line][1])]
            self._new_field_len.set(dist(p1,p2))

        if self._toggle_btn.config('relief')[-1] == 'sunken':
            if self._active_line not in self._multiselect_lines:
                self._multiselect_lines.append(self._active_line)
        else:
            self._multiselect_lines = []

        try:
            state = self.get_color_and_calc_state()
        except AttributeError:
            state = None

        self.update_frame()
        self._combination_slider.set(1)
        if self._line_is_active:
            self._tabControl.select(self._tab_prop)

            try:
                self.gui_load_combinations(self._combination_slider.get())
            except (KeyError, AttributeError):
                pass

        self.cylinder_gui_mods()

    def cylinder_gui_mods(self):
        if self._active_line in self._line_to_struc.keys():

            if self._line_to_struc[self._active_line][5] is not None:
                self._new_calculation_domain.set(CylinderAndCurvedPlate
                                                 .geomeries[self._line_to_struc[self._active_line][5].geometry])
                self._new_shell_exclude_ring_stf.set(self._line_to_struc[self._active_line][5]._ring_stiffener_excluded)
                self._new_shell_exclude_ring_frame.set(self._line_to_struc[self._active_line][5]._ring_frame_excluded)
                self.calculation_domain_selected()
                # Setting the correct optmization buttons
                #'Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder'
                for dom in ['Flat plate, unstiffened', 'Flat plate, stiffened', 'Flat plate, stiffened with girder']:
                    for btn, placement in zip(self._optimization_buttons[dom],
                                              self._optimization_buttons[dom + ' place']):
                        btn.place_forget()
                for btn, placement in zip(self._optimization_buttons['cylinder'],
                                          self._optimization_buttons['cylinder place']):

                    btn.place(relx = placement[0], rely= placement[1],relheight = placement[2], relwidth = placement[3])

            else:
                self._new_calculation_domain.set(self._line_to_struc[self._active_line][0].calculation_domain)
                self.calculation_domain_selected()
                dom = self._line_to_struc[self._active_line][0].calculation_domain
                for btn, placement in zip(self._optimization_buttons['cylinder'],
                                          self._optimization_buttons['cylinder place']):
                    btn.place_forget()

                for btn, placement in zip(self._optimization_buttons[dom],
                                          self._optimization_buttons[dom + ' place']):
                    btn.place(relx = placement[0], rely= placement[1],relheight = placement[2], relwidth = placement[3] )

    def button_1_click_comp_box(self,event):
        '''
        Action when clicking the compartment box.
        :param event:
        :return:
        '''
        self._selected_tank.config(text='')
        self._tank_acc_label.config(text='Accelerations [m/s^2]: ',font = self._text_size['Text 8 bold'])

        if len(self._tank_dict)!=0:

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
                                            +'static: ' + str(acc[0])+' , '
                                            +'dynamic loaded: ' + str(acc[1])+' , '
                                            +'dynamic ballast: ' + str(acc[2]), font = self._text_size['Text 8 bold'])

    def button_3_click(self, event = None):
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
            if point_coord[0]-margin < click_x < point_coord[0]+margin and\
                point_coord[1]-margin < click_y < point_coord[1]+margin:
                self._active_point = point
                self._point_is_active = True
                self._new_delete_point.set(get_num(point))
                if not self._p1_p2_select:
                    self._new_line_p1.set(get_num(point))
                    self._p1_p2_select = True
                else:
                    self._new_line_p2.set(get_num(point))
                    self._p1_p2_select = False
                self._new_point_x.set(round(self._point_dict[self._active_point][0]*1000, 1))
                self._new_point_y.set(round(self._point_dict[self._active_point][1]*1000, 1))
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            if len(self._multiselect_lines) != 0:
                self._multiselect_lines.pop(-1)


        self.update_frame()

    def draw_point_frame(self):
        ''' Frame to define brackets on selected point. '''
        pt_canvas = tk.Canvas(self._pt_frame,height=100,width=100,background=self._style.lookup('TFrame', 'background'))
        pt_canvas.place(relx=0, rely=0)
        pt_canvas.create_oval(45,45,55,55,fill='red')
        new_left_br = tk.IntVar()
        new_right_br = tk.IntVar()
        new_upper_br = tk.IntVar()
        new_lower_br = tk.IntVar()
        wid = 5
        ent_left = ttk.Entry(self._pt_frame,textvariable=new_left_br, width=wid,
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

    def savefile(self):
        '''
        Saving to a file using JSON formatting.
        '''
        save_file = filedialog.asksaveasfile(mode="w", defaultextension=".txt")
        if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
            return

        structure_properties = {}
        shell_structure_properties = {}
        for key, value in self._line_to_struc.items():
            structure_properties[key] = value[0].get_main_properties()
            shell_structure_properties[key] = None if value[5] is None else value[5].get_all_properties()

        fatigue_properties = {}
        for key, value in self._line_to_struc.items():
            if value[2] != None:
                try:
                    fatigue_properties[key] = value[2].get_fatigue_properties()
                except AttributeError:
                    fatigue_properties[key] = None
            else:
                fatigue_properties[key] = None

        load_properties = {}
        for load, data in self._load_dict.items():
            load_properties[load] = [data[0].get_load_parmeters(), data[1]]

        tank_properties = {}
        tank_properties['grid'] = self._main_grid.export_grid()
        tank_properties['search_data'] = self._main_grid.bfs_search_data
        for tank,data in self._tank_dict.items():
            tank_properties[tank] = data.get_parameters()

        load_combiantions = {}
        counter = 0
        for name, data in self._new_load_comb_dict.items():
            load_combiantions[counter] = [name,data[0].get(),data[1].get(),data[2].get()]
            counter+=1

        export_all = {}

        export_all['project information'] = self._project_information.get('1.0', tk.END)
        export_all['theme'] = self._current_theme
        export_all['point_dict'] = self._point_dict
        export_all['line_dict'] = self._line_dict
        export_all['structure_properties'] = structure_properties
        export_all['shell structure properties'] = shell_structure_properties
        export_all['load_properties'] = load_properties
        export_all['accelerations_dict'] = self._accelerations_dict
        export_all['load_combinations'] = load_combiantions
        export_all['tank_properties'] = tank_properties
        export_all['fatigue_properties'] = fatigue_properties
        #export_all['buckling type'] = self._new_buckling_slider.get()

        if self._PULS_results is not None:
            export_all['PULS results'] = self._PULS_results.get_run_results()
            export_all['PULS results']['sheet location'] = self._PULS_results.puls_sheet_location
        export_all['shifting'] = {'shifted checked': self._new_shifted_coords.get(),
                                  'shift hor': self._new_shift_viz_coord_hor.get(),
                                  'shift ver': self._new_shift_viz_coord_ver.get()}

        export_all['Weight and COG'] = self._weight_logger



        json.dump(export_all, save_file)#, sort_keys=True, indent=4)
        save_file.close()
        self._parent.wm_title('| ANYstructure |     ' + save_file.name)
        self.update_frame()

    def openfile(self, defined = None, alone = False):
        '''
        Opens a file with data (JSON).
        '''

        if defined == None:
            imp_file = filedialog.askopenfile(mode='r', defaultextension=".txt")
            if imp_file is None:  # asksaveasfile return `None` if dialog closed with "cancel".
                return
        else:
            imp_file = open(defined,'r')

        imported = json.load(imp_file)

        self.reset()
        if 'project information' in imported.keys():
            self._project_information.delete("1.0", tk.END)
            self._project_information.insert(1.0, imported['project information'])
        else:
            self._project_information.delete("1.0", tk.END)
            self._project_information.insert(1.0, 'No information on project provided. Input here.')

        if 'shifting' in imported.keys():
            self._new_shifted_coords.set(imported['shifting']['shifted checked'])
            self._new_shift_viz_coord_hor.set(imported['shifting']['shift hor'])
            self._new_shift_viz_coord_ver.set(imported['shifting']['shift ver'])
        else:
            pass

        if 'theme' in imported.keys():
            self.set_colors(imported['theme'])

        self._point_dict = imported['point_dict']
        self._line_dict = imported['line_dict']
        struc_prop = imported['structure_properties']
        old_save_file = False

        for line, lines_prop in struc_prop.items():

            if len(lines_prop) > 10:
                # Loading a file (pre 3.4)
                old_save_file = True

            self._line_to_struc[line] = [None, None, None, [], {}, None]
            self._line_point_to_point_string.append(
                self.make_point_point_line_string(self._line_dict[line][0], self._line_dict[line][1])[0])
            self._line_point_to_point_string.append(
                self.make_point_point_line_string(self._line_dict[line][0], self._line_dict[line][1])[1])

            if 'structure_types' not in lines_prop.keys():
                lines_prop['structure_types'] = [self._structure_types, ' ']
            if 'zstar_optimization' not in lines_prop.keys():
                lines_prop['zstar_optimization'] = [self._new_zstar_optimization.get(), '']
            if 'puls buckling method' not in lines_prop.keys():
                lines_prop['puls buckling method'] = [self._new_puls_method.get(), '']
            if 'puls boundary' not in lines_prop.keys():
                lines_prop['puls boundary'] = [self._new_puls_panel_boundary.get(), '']
            if 'puls stiffener end' not in lines_prop.keys():
                lines_prop['puls stiffener end'] = [self._new_buckling_stf_end_support.get(), '']
            if 'puls sp or up' not in lines_prop.keys():
                lines_prop['puls sp or up'] = [self._new_puls_sp_or_up.get(), '']
            if 'puls up boundary' not in lines_prop.keys():
                lines_prop['puls up boundary'] = [self._new_puls_up_boundary.get(), '']
            if 'mat_factor' not in lines_prop.keys():
                lines_prop['mat_factor'] = [self._new_material_factor.get(), '']

            # Sigma x1/x2 is missing before 3.4
            if 'sigma_x' in lines_prop.keys():
                lines_prop['sigma_x1'] = lines_prop['sigma_x']
                lines_prop['sigma_x2'] = lines_prop['sigma_x']
                lines_prop.pop('sigma_x')

            if old_save_file: #need to get some basic information
                import ANYstructure_local.example_data as ex
                main_dict = ex.prescriptive_main_dict
                map_end = {'C': 'Continuous', 'S': 'Sniped'}
                lines_prop['puls stiffener end'] = [map_end[lines_prop['puls stiffener end'][0]],
                                                    lines_prop['puls stiffener end'][1]]
                main_dict['material yield'] = [355e6, 'Pa']
                main_dict['load factor on stresses'] = [1, '']
                main_dict['load factor on pressure'] = [1, '']
                main_dict['buckling method'] = [lines_prop['puls buckling method'], '']
                main_dict['stiffener end support'] = lines_prop['puls stiffener end']  # 'Continuous'
                main_dict['girder end support'] = ['Continuous', '']  # 'Continuous'
                dom = 'Flat plate, stiffened' if lines_prop['puls sp or up'][0] == 'SP' else 'Flat plate, unstiffened'

                main_dict['calculation domain'] = [dom, '']
                map_side = {'p': 'plate side', 's': 'stiffener side'}
                if 'press_side' in lines_prop.keys():
                    lines_prop['press_side'] = [map_side[lines_prop['press_side'][0]], '']
                else:
                    lines_prop['press_side'] = 'both sides'
                lines_prop['panel or shell'] = 'panel'
                #lines_prop['tension field'] = 'allowed'
                self._line_to_struc[line][0] = AllStructure(Plate=CalcScantlings(lines_prop),
                                                            Stiffener=None if dom == 'Flat plate, unstiffened'
                                                            else CalcScantlings(lines_prop),
                                                            Girder=None, main_dict=main_dict)

                if imported['fatigue_properties'][line] is not None:
                    self._line_to_struc[line][2] = CalcFatigue(lines_prop,
                                                               imported['fatigue_properties'][line])
                else:
                    self._line_to_struc[line][2] = None
                #  Recording sections.
                self._sections = add_new_section(self._sections, struc.Section(lines_prop))

            else:
                self._line_to_struc[line][0] = AllStructure(Plate=None if lines_prop['Plate'] is None
                                                            else CalcScantlings(lines_prop['Plate']),
                                                            Stiffener=None if lines_prop['Stiffener'] is None
                                                            else CalcScantlings(lines_prop['Stiffener']),
                                                            Girder=None if lines_prop['Girder'] is None
                                                            else CalcScantlings(lines_prop['Girder']),
                                                            main_dict=lines_prop['main dict'])

                if imported['fatigue_properties'][line] is not None:
                    self._line_to_struc[line][2] = CalcFatigue(lines_prop['Stiffener'],
                                                               imported['fatigue_properties'][line])
                else:
                    self._line_to_struc[line][2] = None
                #  Recording sections.
                self._sections = add_new_section(self._sections, struc.Section(lines_prop['Stiffener']))

            if 'shell structure properties' in imported.keys():
                if imported['shell structure properties'][line] is not None:
                    # need to correct the calcuation domain.
                    #self._new_calculation_domain.set(imported_dict['Main class'][CylinderAndCurvedPlate.geomeries])
                    imported_dict = imported['shell structure properties'][line]
                    '''
                    all_data = {'Main class': self.get_main_properties(),
                                'Shell': self._Shell.get_main_properties(),
                                'Long. stf.': self._LongStf.get_structure_prop(),
                                'Ring stf.': self.RingStfObj.get_structure_prop(),
                                'Ring frame': self._RingFrame.get_structure_prop()}
                    '''
                    for stuc_type in ['Long. stf.', 'Ring stf.', 'Ring frame']:
                        if imported_dict[stuc_type] is not None:
                            if 'sigma_x' in imported_dict[stuc_type].keys():
                                imported_dict[stuc_type]['sigma_x1'] = imported_dict[stuc_type]['sigma_x']
                                imported_dict[stuc_type]['sigma_x2'] = imported_dict[stuc_type]['sigma_x']
                                imported_dict[stuc_type].pop('sigma_x')
                    self._line_to_struc[line][5] = \
                        CylinderAndCurvedPlate(imported_dict['Main class'], shell=None if imported_dict['Shell'] is None
                        else Shell(imported_dict['Shell']), long_stf=None if imported_dict['Long. stf.'] is None
                        else Structure(imported_dict['Long. stf.']), ring_stf=None if imported_dict['Ring stf.'] is None
                        else Structure(imported_dict['Ring stf.']), ring_frame=None if imported_dict['Ring frame']
                                                                                       is None
                        else Structure(imported_dict['Ring frame']))

        # opening the loads
        variables = ['poly_third','poly_second', 'poly_first', 'poly_const', 'load_condition',
                     'structure_type', 'man_press', 'static_draft', 'name_of_load', 'limit_state',
                     'slamming mult pl', 'slamming mult stf']

        if len(imported['load_properties']) != 0:
            for load, data in imported['load_properties'].items():
                temp_dict = {}
                count_i = 0
                values = data[0]
                if len(values) != len(variables):
                    # Adding slamming multiplication factors
                    values.append(1)
                    values.append(1)
                for value in values:
                    temp_dict[variables[count_i]]= value
                    count_i += 1
                self._load_dict[load] = [Loads(temp_dict), data[1]]

                if len(data[1]) != 0:
                    for main_line in self._line_dict.keys():
                        if main_line in data[1]:
                            self._line_to_struc[main_line][3].append(self._load_dict[load][0])

        try:
            self._accelerations_dict = imported['accelerations_dict']
        except IndexError:
            self._accelerations_dict = {'static':9.81, 'dyn_loaded':0, 'dyn_ballast':0}

        self._new_static_acc.set(self._accelerations_dict['static'])
        self._new_dyn_acc_loaded.set(self._accelerations_dict['dyn_loaded'])
        self._new_dyn_acc_ballast.set(self._accelerations_dict['dyn_ballast'])

        try:
            for data in imported['load_combinations'].values():
                name = tuple(data[0])
                self._new_load_comb_dict[name] = [tk.DoubleVar(),tk.DoubleVar(),tk.IntVar()]
                self._new_load_comb_dict[name][0].set(data[1]), self._new_load_comb_dict[name][1].set(data[2])
                self._new_load_comb_dict[name][2].set(data[3])
        except IndexError:
            for data in imported['load_combinations'].values():
                name = tuple(data[0])
                self._new_load_comb_dict[name] = [tk.DoubleVar(),tk.IntVar()]
                self._new_load_comb_dict[name][0].set(data[1]), self._new_load_comb_dict[name][1].set(data[2])

        try:
            self._main_grid.import_grid(imported['tank_properties']['grid'])
            self._grid_calc = grid_window.CreateGridWindow(self._main_grid, self._canvas_dim,
                                                           self._pending_grid_draw, self._canvas_base_origo)

            tank_inp = dict()
            if 'search_data' in imported['tank_properties'].keys():
                try:
                    for key, value in imported['tank_properties']['search_data'].items():
                        tank_inp[int(key)] = value
                    self._main_grid.bfs_search_data = tank_inp
                    self._grid_calc.bfs_search_data = tank_inp
                except AttributeError:
                    self._main_grid.bfs_search_data = None
                    self._grid_calc.bfs_search_data = None
            else:
                self._main_grid.bfs_search_data = None
                self._grid_calc.bfs_search_data = None

            for comp_no in range(2, int(self._main_grid.get_highest_number_in_grid())+1):
                self._compartments_listbox.insert('end',comp_no)
                self._tank_dict['comp' + str(comp_no)] = Tanks(imported['tank_properties']['comp' + str(comp_no)])
        except IndexError:
            for line_name, point_no in self._line_dict.items():
                point_coord_x = self._canvas_base_origo[0] + self._point_dict[point_no][0] * self._canvas_scale
                point_coord_y = self._canvas_base_origo[1] - self._point_dict[point_no][1] * self._canvas_scale

                self.grid_operations(line_name, [point_coord_x,point_coord_y])

        if 'PULS results' in list(imported.keys()):
            self._PULS_results = PULSpanel()
            if 'sheet location' in imported['PULS results'].keys():
                self._PULS_results.puls_sheet_location = imported['PULS results']['sheet location']
                imported['PULS results'].pop('sheet location')
            self._PULS_results.set_run_results(imported['PULS results'])

        # Setting the scale of the canvas
        points = self._point_dict
        highest_y = max([coord[1] for coord in points.values()])
        highest_x = max([coord[0] for coord in points.values()])
        self._canvas_scale = min(800 / highest_y, 800 / highest_x, 15)

        # if 'buckling type' in imported.keys():
        #     self._new_buckling_slider.set(imported['buckling type'])
        #     self._buckling_slider.set(imported['buckling type'])

        if 'Weight and COG' in imported.keys():
            self._weight_logger = imported['Weight and COG']

        self.get_cob()
        imp_file.close()
        self._parent.wm_title('| ANYstructure |     ' + imp_file.name)
        self.update_frame()

    def open_example(self, file_name = 'ship_section_example.txt'):
        ''' Open the example file. To be used in help menu. '''
        if os.path.isfile(file_name) :
            self.openfile(defined = file_name)
        else:
            self.openfile(defined= self._root_dir + '/' + file_name)

    def button_load_info_click(self, event = None):
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
            #tk.messagebox.showinfo('Load info for '+self._active_line, ''.join(load_text))
        else:
            tk.messagebox.showerror('No data', 'No load data for this line')

    def on_plot_cog_dev(self):
        '''
        Plot the COG and COB development.
        '''
        if self._weight_logger['new structure']['time'] == []:
            tk.messagebox.showinfo('New functionality ver. 3.3', 'If you are using and existing model,'
                                                                 ' weights have not been'
                                                        ' recorded in previous versions.\n'
                                                        'Press "Add structure properties to line....." button to add a '
                                                        'blank datapoint.\n'
                                                        'Other data will then be avaliable.\n\n'
                                                        'If you are making a new model add some structure properties.')
            return
        import matplotlib.dates as mdate

        cog = np.array(self._weight_logger['new structure']['COG'])
        weight = np.array(self._weight_logger['new structure']['weight'])/\
                 max(self._weight_logger['new structure']['weight'])
        time_stamp = np.array(self._weight_logger['new structure']['time'])
        time_stamp = [mdate.epoch2num(val) for val in time_stamp]
        structure = self.get_unique_plates_and_beams()

        hlp.plot_weights(time_stamp=time_stamp, cog=cog,structure=structure,weight=weight)

    def on_open_structure_window(self, clicked_button = None):
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
            messagebox.showinfo(title='Select line',message='You must select a line')

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
            messagebox.showinfo(title='Select line',message='You must select a line')

    def on_open_load_factor_window(self):
        '''
        Set the default load factors and change all.
        :return:
        '''
        lf_tkinter = tk.Toplevel(self._parent, background=self._general_color)
        load_factors.CreateLoadFactorWindow(lf_tkinter, self)

    def on_puls_results_for_line(self):
        if not self._line_is_active:
            return
        if self._PULS_results is None:
            return
        elif self._PULS_results.get_puls_line_results(self._active_line) is None:
            return
        # if self._puls_information_button.config('relief')[-1] == 'sunken':
        #     self.text_widget.forget()
        #     self._puls_information_button.config(relief='raised')
        this_result = self._PULS_results.get_puls_line_results(self._active_line)
        this_string = ''
        for key, value in this_result.items():
            if type(value) == list:
                this_string += key + ' : ' + str(value[0]) + ' ' + str(value[1]) + '\n'
            elif type(value) == str:
                this_string += key + ' : ' + value + '\n'
            elif type(value) == dict:
                this_string += key + '\n'
                for subk, subv in value.items():
                    this_string += '   ' + subk + ' : ' + str(subv[0]) + ' ' + str(subv[1] if subv[1] != None else '') + '\n'

        text_m = tk.Toplevel(self._parent, background=self._general_color)
        # Create the text widget
        text_widget = tk.Text(text_m , height=60, width=100)
        # Create a scrollbar
        scroll_bar = ttk.Scrollbar(text_m)
        # Pack the scroll bar
        # Place it to the right side, using tk.RIGHT
        scroll_bar.pack(side=tk.RIGHT)
        # Pack it into our tkinter application
        # Place the text widget to the left side
        text_widget.pack(side=tk.LEFT)
        long_text = this_string
        # Insert text into the text widget
        text_widget.insert(tk.END, long_text)

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
            self._ext_button.config(image = photo)
            self._ext_button.image = photo
        except TclError:
            pass

        top = tk.Toplevel(self._parent, background=self._general_color)
        load_window.CreateLoadWindow(top, self)

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
                                message='Select line or make some loads for the line.\n'+
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
            messagebox.showinfo(title='Select line',message='You must select a line')

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
            messagebox.showinfo(title='Select line',message='You must select a line')

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
        opwmult.CreateOptimizeMultipleWindow(top_opt,self)

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

        messagebox.showinfo(title='Span optimization module', message =
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
        optgeo.CreateOptGeoWindow(top_opt,self)

    def on_close_load_window(self, returned_loads, counter, load_comb_dict):
        '''
        Setting properties created in load window.
        :return:
        '''

        try:
            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._ext_button.config(image = photo)
            self._ext_button.image = photo
        except TclError:
            pass
        self._load_window_couter = counter
        self._new_load_comb_dict = load_comb_dict
        temp_load = copy.deepcopy(self._load_dict)
        if len(returned_loads) != 0:
            need_to_recalc_puls = {}
            for load, data in returned_loads.items():
                #creating the loads objects dictionary
                self._load_dict[load] = data

            # adding values to the line dictionary. resetting first.
            for key, value in self._line_to_struc.items():
                self._line_to_struc[key][3] = []
                self._line_to_struc[key][0].need_recalc = True  # All lines need recalculations.

            for main_line in self._line_dict.keys():
                for load_obj, load_line in self._load_dict.values():
                    if main_line in self._line_to_struc.keys():
                        if returned_loads:
                            if load_obj.__str__() != temp_load[load_obj.get_name()][0].__str__() and main_line in \
                                    load_line+temp_load[load_obj.get_name()][1]:
                                # The load has changed for this line.
                                if self._PULS_results is not None:
                                    self._PULS_results.result_changed(main_line)
                    if main_line in load_line and main_line in self._line_to_struc.keys():
                        self._line_to_struc[main_line][3].append(load_obj)

        # Storing the the returned data to temporary variable.
        self.__returned_load_data = [returned_loads, counter, load_comb_dict]

       # Calculating center of buoyancy from static cases.

        self.get_cob() # Update COB
        self.update_frame()

    def on_close_opt_window(self,returned_object):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''

        self.new_structure(multi_return = returned_object[0:2])
        # self._line_to_struc[self._active_line][1]=returned_objects[0]
        # self._line_to_struc[self._active_line][1]=returned_objects[1]
        # self._line_to_struc[self._active_line][0].need_recalc = True
        # self.set_selected_variables(self._active_line)
        # if returned_objects[2] is not None:
        #     self._line_to_struc[self._active_line][2] = CalcFatigue(returned_objects[0].get_structure_prop(),
        #                                                             returned_objects[2])
        # self.new_structure()
        self.update_frame()

    def on_close_opt_cyl_window(self,returned_object):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''

        self.new_structure(cylinder_return = returned_object[0])

        self.update_frame()

    def on_close_opt_multiple_window(self, returned_objects):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''

        for line,all_objs in returned_objects.items():
            self._active_line = line
            #self._line_to_struc[line][0].need_recalc = True
            self.new_structure(multi_return= all_objs[0:2])
        self.update_frame()

    def on_close_structure_window(self,returned_structure):
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
        clicked_button = returned_structure[7] #["long stf", "ring stf", "ring frame", "flat long stf", 'flat stf', 'flat girder']


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
                                 'stf_web_height': returned_structure[2]/1000,
                                 'stf_web_thk': returned_structure[3]/1000,
                                 'stf_flange_width': returned_structure[4]/1000,
                                 'stf_flange_thk': returned_structure[5]/1000})

        self._sections = add_new_section(self._sections, section)

    def on_close_stresses_window(self,returned_stress_and_km):
        '''
        Sets the returned transverse/axial/shear stresses (global estimated values).
        Sets the km1,km2,km3 paramter.
        :param returned_stress_and_km:
        :return:
        '''
        self._new_sigma_y1.set(returned_stress_and_km[0])
        self._new_sigma_y2.set(returned_stress_and_km[1])
        self._new_sigma_x1.set(returned_stress_and_km[2])
        self._new_sigma_x2.set(returned_stress_and_km[3])
        self._new_tauxy.set(returned_stress_and_km[4])
        self._new_stf_km1.set(returned_stress_and_km[5])
        self._new_stf_km1.set(returned_stress_and_km[6])
        self._new_stf_km1.set(returned_stress_and_km[7])
        self._new_plate_kpp.set(returned_stress_and_km[8])
        self._new_stf_kps.set(returned_stress_and_km[9])
        self._new_stucture_type.set(returned_stress_and_km[10],)

    def on_close_fatigue_window(self,returned_fatigue_prop: dict):
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
            self._ext_button.config(image = photo)
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

        mess = tk.messagebox.showwarning('Close main window', 'Save before closing?',type = 'yesnocancel')

        if mess == 'yes':
            self.savefile()
            self._parent.destroy()
        elif mess == 'no':
            self._parent.destroy()
        elif mess == 'cancel':
            pass

    def on_color_code_check(self, event = None):
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

    def logger(self, line = None, point = None, move_coords = None):
        ''' Log to be used for undo and redo. '''

        if line is not None:
            self._logger['added'].append([line[0], self._line_dict[line[0]]])
        elif point is not None and move_coords is None:
            self._logger['added'].append([point, None])
        elif point is not None and move_coords is not None:
            self._logger['added'].append([point, move_coords])
        else:
            pass

    def undo(self, event = None):
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

    def redo(self, event = None):
        ''' Method to undo and redo. '''
        if len(self._logger['deleted']) > 0:
            current = self._logger['deleted'].pop(-1)
            if 'point' in current[0] and current[1] is None:
                self.new_point(redo=current[0])
            elif 'point' in current[0] and current[1] is not None:
                self.move_point(redo=current[1][1])
            elif 'line' in current[0]:
                self.new_line(redo=['point'+str(num) for num in current[1]])

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
        messagebox.showinfo(title='Information', message='ANYstructure 3.x (Stable/Production)'
                                                         '\n'
                                                         '\n'
                                                         'By Audun Arnesen Nyhus \n'
                                                         '2021\n\n'
                                                         'All technical calculation based on:'
                                                         '- DNVGL-OS-C101'
                                                         '- Supporting DNVGL RPs and standards')

    def export_to_js(self):
        '''
        Printing to a js file
        :return:
        '''
        save_file = filedialog.asksaveasfile(mode="w", defaultextension=".js")
        if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
            return
        # Setting up interface class.
        JS = sesam.JSfile(self._point_dict, self._line_dict, self._sections, self._line_to_struc)

        JS.write_points()
        JS.write_lines()
        JS.write_sections()
        JS.write_beams()

        save_file.writelines(JS.output_lines)
        save_file.close()

if __name__ == '__main__':

    multiprocessing.freeze_support()
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    root = tk.Tk()
    # root.tk.call("source", "sun-valley.tcl")
    # root.tk.call("set_theme", "light")
    width = int(root.winfo_screenwidth()*1)
    height = int(root.winfo_screenheight()*0.95)
    root.geometry(f'{width}x{height}')
    my_app = Application(root)
    root.mainloop()
    #Application(None).openfile(r'C:\Github\ANYstructure\ANYstructure\ship_section_example.txt', alone=True)