 # -*- coding: utf-8 -*-
import time, datetime
import tkinter as tk
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

        # Definng general colors
        self._general_color = 'azure2'  # Color for backgrounds.
        self._entry_color = 'white'  # Entry fields color.
        self._entry_text_color = 'black'  # Entry field tex color
        self._button_bg_color = 'LightBlue1'
        self._button_fg_color = 'black'

        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        # Main frame for the application
        self._main_fr = tk.Frame(parent,
                                 background=self._general_color)
        self._main_fr.place(in_=parent, relwidth=1, relheight = 0.99)
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
        sub_report.add_command(label = 'Generate PDF report', command = self.report_generate)
        sub_report.add_command(label='Generate PDF result table', command=self.table_generate)
        sub_report.add_command(label='Weight development, plates and beams', command=self.on_plot_cog_dev)

        sub_sesam = tk.Menu(menu)
        menu.add_cascade(label = 'SESAM interface', menu = sub_sesam)
        sub_sesam.add_command(label = 'Export geometry to JS', command = self.export_to_js)

        sub_help = tk.Menu(menu)
        menu.add_cascade(label='Help', menu = sub_help)
        sub_help.add_command(label = 'Open documentation', command = self.open_documentation)
        sub_help.add_command(label = 'Open example file', command = self.open_example)
        sub_help.add_command(label='About ANYstructure', command=self.open_about)
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

        # Creating the various canvas next.
        self._main_canvas = tk.Canvas(self._main_fr,
                                      background=self._general_color, bd=0, highlightthickness=0, relief='ridge')
        self._prop_canvas = tk.Canvas(self._main_fr,
                                     background=self._general_color, bd=0, highlightthickness=0, relief='ridge')
        self._result_canvas = tk.Canvas(self._main_fr,
                                       background=self._general_color, bd=0, highlightthickness=0, relief='ridge')
        x_canvas_place = 0.26
        self._main_canvas.place(relx=x_canvas_place, rely=0,relwidth=0.523, relheight = 0.73)
        self._prop_canvas.place(relx=x_canvas_place, rely=0.73, relwidth=0.38, relheight = 0.27)
        self._result_canvas.place(relx=x_canvas_place+0.38, rely=0.73, relwidth=0.36, relheight = 0.27)

        # These frames are just visual separations in the GUI.
        frame_horizontal, frame_vertical = 0.73, 0.258
        tk.Frame(self._main_fr, height=3, bg="black", colormap="new")\
            .place(relx=0, rely=frame_horizontal, relwidth=1)
        tk.Frame(self._main_fr, width=3, bg="black", colormap="new")\
            .place(relx=frame_vertical,rely=0 * 1, relheight=1)

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
        self._tank_options = {'crude_oil': 900, 'diesel': 850 , 'slop': 1050, 'ballast': 1025, 'fresh water': 1000} # Should not be modified.
        self._default_stresses = {'BOTTOM':(100,100,50,5), 'BBS':(70,70,30,3), 'BBT':(80,80,30,3), 'HOPPER':(70,70,50,3),
                                 'SIDE_SHELL':(100,100,40,3),'INNER_SIDE':(80,80,40,5), 'FRAME':(70,70,60,10),
                                 'FRAME_WT':(70,70,60,10),'SSS':(100,100,50,20), 'MD':(70,70,40,3),
                                 'GENERAL_INTERNAL_WT':(90,90,40,5),'GENERAL_INTERNAL_NONWT':(70,70,30,3),
                                  'INTERNAL_1_MPA':(1,1,1,1), 'INTERNAL_LOW_STRESS_WT':(40,40,20,5)}
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
        print(self._ML_buckling)
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
                                       'sigma_y1', 'sigma_y2', 'sigma_x', 'tau_xy', 'plate_kpp', 'stf_kps','stf_km1',
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

        # These sets the location where entries are placed.
        ent_x = 0.09375
        delta_y = 0.022
        delta_x = 0.026041667

        # ----------------------INITIATION OF THE SMALLER PARTS OF THE GUI STARTS HERE--------------------------
        # --- point input/output ----
        self._new_point_x = tk.DoubleVar()
        self._new_point_y = tk.DoubleVar()
        self._new_point_fix = tk.StringVar()
        self._new_zstar_optimization = tk.BooleanVar()
        self._new_zstar_optimization.set(True)
        self._new_project_infomation = tk.StringVar()
        self._new_project_infomation.set('No information on project provided. Input here.')
        point_x_start, point_start = 0.005208333, 0.055
        ent_width = 6  # width of entries

        tk.Entry(self._main_fr, textvariable=self._new_project_infomation,
                 bg = self._button_bg_color, fg = self._entry_text_color)\
            .place(relx=0.005, rely=0.005, relwidth = 0.25)

        tk.Label(self._main_fr, text='Input point coordinates [mm]', font=self._text_size['Text 9 bold'],
                 bg = self._general_color)\
            .place(rely=point_start - 0.027777778, relx=point_x_start, anchor = tk.NW)
        tk.Label(self._main_fr, text='Point x (horizontal) [mm]:',font="Text 9", bg = self._general_color)\
            .place(relx=point_x_start, rely=point_start)
        tk.Label(self._main_fr, text='Point y (vertical)   [mm]:',font="Text 9", bg = self._general_color)\
            .place(relx=point_x_start, rely=point_start + delta_y)

        tk.Entry(self._main_fr, textvariable=self._new_point_x, width = int(ent_width * 1.5),
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=ent_x, rely=point_start)
        tk.Entry(self._main_fr, textvariable=self._new_point_y, width = int(ent_width * 1.5),
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=ent_x, rely=point_start + delta_y)
        tk.Button(self._main_fr, text='Add point (coords)', command=self.new_point,
                  bg = self._button_bg_color, fg = self._button_fg_color,
                  font = self._text_size['Text 9 bold']).place(relx=ent_x + 2 * delta_x, rely=point_start-1*delta_y,
                                                               relwidth = 0.08)
        tk.Button(self._main_fr, text='Copy point (relative)', command=self.copy_point,
                  bg = self._button_bg_color, fg = self._button_fg_color,
                  font = self._text_size['Text 9 bold']).place(relx=ent_x + 2 * delta_x, rely=point_start+0.1*delta_y,
                                                               relwidth = 0.08)
        tk.Button(self._main_fr, text='Move point', command=self.move_point,
                  bg = self._button_bg_color, fg = self._button_fg_color,
                  font = self._text_size['Text 9 bold']).place(relx=ent_x + 2 * delta_x, rely=point_start+1.2*delta_y,
                                                               relwidth = 0.04)
        tk.Button(self._main_fr, text='Move line', command=self.move_line,
                  bg = self._button_bg_color, fg = self._button_fg_color,
                  font = self._text_size['Text 9 bold']).place(relx=ent_x + 3.55 * delta_x, rely=point_start+1.2*delta_y,
                                                               relwidth = 0.04)

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
        self._new_draw_point_name = tk.BooleanVar()
        self._new_draw_point_name.set(False)
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
        self._new_buckling_slider = tk.IntVar()
        self._new_buckling_slider.set(1)
        self._new_show_cog = tk.BooleanVar()
        self._new_show_cog.set(False)
        self._new_content_type = tk.StringVar()
        self._new_content_type.set('ballast')

        line_start, line_x = point_start+0.08, 0.005208333
        tk.Label(self._main_fr, text='Input line from "point number" to "point number"',
                 font=self._text_size['Text 9 bold'], bg = self._general_color)\
            .place(rely=line_start - 0.025, relx=line_x, anchor = tk.NW)
        tk.Label(self._main_fr, text='From point number:',font="Text 9", bg = self._general_color)\
            .place(relx=line_x, rely=line_start)
        tk.Label(self._main_fr, text='To point number:',font="Text 9", bg = self._general_color)\
            .place(relx=line_x, rely=line_start + delta_y)
        tk.Checkbutton(self._main_fr, variable = self._new_shortcut_backdrop, command = self.update_frame)\
            .place(relx = 0.26, y=0)
        tk.Label(self._main_fr, text='Color coding',font="Text 9", bg = self._general_color)\
            .place(relx = 0.26, y=20)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_beams, command = self.on_color_code_check)\
            .place(relx = 0.26, y=40)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_plates, command = self.on_color_code_check)\
            .place(relx = 0.26, y=60)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_pressure, command = self.on_color_code_check)\
            .place(relx = 0.26, y=80)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_utilization, command = self.on_color_code_check)\
            .place(relx = 0.26, y=100)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_section_modulus, command = self.on_color_code_check)\
            .place(relx = 0.26, y=120)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_fatigue, command = self.on_color_code_check)\
            .place(relx = 0.26, y=140)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_total, command = self.on_color_code_check)\
            .place(relx = 0.26, y=160)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_spacing, command = self.on_color_code_check)\
            .place(relx = 0.095, rely=0.29)


        tk.Label(self._main_fr, text='Check to see avaliable shortcuts', font="Text 9").place(relx = 0.27, y=0)
        tk.Label(self._main_fr, text='Beam prop.', font="Text 9").place(relx = 0.27, y=40)
        tk.Label(self._main_fr, text='Plate thk.', font="Text 9").place(relx = 0.27, y=60)
        tk.Label(self._main_fr, text='Pressure', font="Text 9").place(relx = 0.27, y=80)
        tk.Label(self._main_fr, text='Buckling UF', font="Text 9").place(relx = 0.27, y=100)
        tk.Label(self._main_fr, text='Sec. mod. UF', font="Text 9").place(relx=0.27, y=120)
        tk.Label(self._main_fr, text='Fatigue UF', font="Text 9").place(relx=0.27, y=140)
        tk.Label(self._main_fr, text='Total UF', font="Text 9").place(relx=0.27, y=160)

        tk.Entry(self._main_fr, textvariable=self._new_line_p1, width=int(ent_width * 1),
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=ent_x, rely=line_start)
        tk.Entry(self._main_fr, textvariable=self._new_line_p2, width=int(ent_width * 1),
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=ent_x, rely=line_start + delta_y)
        tk.Button(self._main_fr, text='Add line', command=self.new_line,
                  bg = self._button_bg_color, fg = self._button_fg_color,
                  font = self._text_size['Text 9 bold']).place(relx=ent_x+2*delta_x, rely=line_start-delta_y*0.05,
                                                               relwidth = 0.05)
        # tk.Button(self._main_fr, text='Move line', command=self.new_line,
        #           bg = self._button_bg_color, fg = self._button_fg_color,
        #           font = self._text_size['Text 9 bold']).place(relx=ent_x+2*delta_x, rely=line_start+delta_y*1.05,
        #                                                        relwidth = 0.05)

        # --- delete points and lines ---
        self._new_delete_line = tk.IntVar()
        self._new_delete_point = tk.IntVar()
        del_start, del_x = line_start + 0.075,0.005208333
        tk.Label(self._main_fr, text='Delete lines and points (or left/right click and use "Delete key")',
                 font=self._text_size['Text 9 bold'], bg = self._general_color)\
            .place(rely=del_start - 0.027777778*1,relx=del_x, anchor = tk.NW)
        self._ent_delete_line = tk.Entry(self._main_fr, textvariable=self._new_delete_line,
                                        width=int(ent_width * 1),
                                         bg = self._entry_color, fg = self._entry_text_color)
        self._ent_delete_line.place(relx=ent_x, rely=del_start)

        self._ent_delete_point = tk.Entry(self._main_fr, textvariable=self._new_delete_point,
                                         width=int(ent_width * 1),
                                          bg = self._entry_color, fg = self._entry_text_color)
        self._ent_delete_point.place(relx=ent_x, rely=del_start + delta_y)

        tk.Label(self._main_fr, text='Line number (left click):',font="Text 9", bg = self._general_color)\
            .place(relx=del_x, rely=del_start)
        tk.Label(self._main_fr, text='Point number (right click):',font="Text 9", bg = self._general_color)\
            .place(relx=del_x, rely=del_start+ delta_y)

        tk.Button(self._main_fr, text='Delete line',bg = self._button_bg_color, fg = self._button_fg_color,
                                         font=self._text_size['Text 9 bold'],command=self.delete_line,
                                         ).place(relx=ent_x+delta_x*2, rely=del_start-0.002,
                                                                                    relwidth = 0.05)
        tk.Button(self._main_fr, text='Delete prop.',bg = self._button_bg_color, fg = self._button_fg_color,
                                         font=self._text_size['Text 9 bold'],command=self.delete_properties_pressed,
                                         ).place(relx=ent_x+delta_x*4, rely=del_start-0.002,
                                                                                    relwidth = 0.05)

        tk.Button(self._main_fr, text='Delete point',bg = self._button_bg_color, fg = self._button_fg_color,
                                          font=self._text_size['Text 9 bold'],command=self.delete_point,
                                          ).place(relx=ent_x+2*delta_x, rely=del_start + delta_y +0.004-0.002,
                                                                                     relwidth = 0.05)

        # --- structure type information ---
        prop_vert_start = 0.29
        types_start = 0.005208333
        tk.Label(self._main_fr, text='Structural and calculation properties input below:',
                 font=self._text_size['Text 9 bold'],
                 bg = self._general_color ).place(rely=prop_vert_start-delta_y,relx=types_start,
                                                  anchor = tk.NW)
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



        tk.Label(self._main_fr, text='Show line names in GUI', font="Text 9")\
            .place(relx=0.38, rely=0)
        tk.Label(self._main_fr, text='Show point names in GUI', font="Text 9")\
            .place(relx=0.47, rely=0)
        tk.Label(self._main_fr, text='Label color code', font="Text 9")\
            .place(relx=0.565, rely=0)
        tk.Label(self._main_fr, text='Use shifted coordinates', font="Text 9")\
            .place(relx=0.635, rely=0)
        tk.Label(self._main_fr, text='Show COG/COB', font="Text 9")\
            .place(relx=0.733, rely=0)
        tk.Checkbutton(self._main_fr, variable = self._new_line_name, command = self.on_color_code_check)\
            .place(relx=0.366, rely=0)
        tk.Checkbutton(self._main_fr, variable = self._new_draw_point_name, command = self.on_color_code_check)\
            .place(relx=0.455, rely=0)
        tk.Checkbutton(self._main_fr, variable = self._new_label_color_coding, command = self.on_color_code_check)\
            .place(relx=0.55, rely=0)
        tk.Checkbutton(self._main_fr, variable = self._new_shifted_coords, command = self.update_frame)\
            .place(relx=0.62, rely=0)
        tk.Checkbutton(self._main_fr, variable = self._new_show_cog, command = self.update_frame)\
            .place(relx=0.72, rely=0)



        self.add_stucture = tk.Button(self._main_fr, text='Add structure/properties to line \n'
                                                          '-- new or replace existing --', command=self.new_structure,
                                      font = self._text_size['Text 10 bold'],
                                      bg = self._button_bg_color, fg = self._button_fg_color)
        self.add_stucture.place(relx=types_start+ delta_x*4.2, rely=prop_vert_start+18*delta_y, relwidth = 0.14,
                                relheight = 0.04)


        tk.Checkbutton(self._main_fr, variable = self._new_scale_stresses, command = self.on_color_code_check)\
            .place(relx = types_start+ delta_x*4.3, rely=prop_vert_start+16.9*delta_y)
        tk.Label(self._main_fr, text='Scale stresses when\n changing prop.', font=self._text_size['Text 9'],
                 bg = self._general_color)\
            .place(relx = types_start+ delta_x*4.7, rely=prop_vert_start+16.6*delta_y, relwidth = 0.065)
        tk.Label(self._main_fr, text='fup', font=self._text_size['Text 8'],
                 bg = self._general_color)\
            .place(relx = types_start+ delta_x*7.3, rely=prop_vert_start+17*delta_y)
        ent_fup = tk.Entry(self._main_fr, textvariable=self._new_fup,
                                         bg = self._entry_color, fg = self._entry_text_color)
        ent_fup.place(relx = types_start+ delta_x*7.8, rely=prop_vert_start+17*delta_y, relwidth = 0.01)
        tk.Label(self._main_fr, text='fdown', font=self._text_size['Text 8'],
                 bg = self._general_color)\
            .place(relx = types_start+ delta_x*8.3, rely=prop_vert_start+17*delta_y)
        ent_fdwn = tk.Entry(self._main_fr, textvariable=self._new_fdwn,
                                         bg = self._entry_color, fg = self._entry_text_color)
        ent_fdwn.place(relx = types_start+ delta_x*9.1, rely=prop_vert_start+17*delta_y, relwidth = 0.01)
        # Toggle buttons
        self._toggle_btn = tk.Button(self._main_fr, text="Toggle select\nmultiple", relief="raised",
                                     command=self.toggle_select_multiple, bg = self._button_bg_color)
        self._toggle_change_param = tk.Button(self._main_fr, text="Change multi.\nparameter", relief="raised",
                                     command=self.toggle_set_variable, bg = self._button_bg_color)
        self._toggle_param_to_change = None
        self._toggle_btn.place(relx=types_start+ delta_x*4.2, rely=prop_vert_start+15*delta_y, relwidth = 0.045,
                                relheight = 0.035)
        self._toggle_change_param.place(relx=types_start+ delta_x*6, rely=prop_vert_start+15*delta_y, relwidth = 0.045,
                                relheight = 0.035)

        self._toggle_choose = tk.OptionMenu(self._main_fr, self._new_toggle_var, *self._stuctural_definition,
                                            command = self.update_frame)
        self._toggle_choose.place(relx=types_start+ delta_x*7.8, rely=prop_vert_start+15*delta_y, relwidth = 0.047,
                                relheight = 0.035)

        # PULS interface
        self._toggle_btn_puls = tk.Button(self._main_fr, text="Use PULS\n"
                                                              "results", relief="raised",
                                     command=self.toggle_puls_run, bg = self._button_bg_color)
        self._puls_run_all = tk.Button(self._main_fr, text='Run PULS\nupdate results', relief="raised",
                                     command=self.puls_run_all_lines, bg = self._button_bg_color)
        # self._puls_run_one = tk.Button(self._main_fr, text="PULS\nRun one line", relief="raised",
        #                              command=self.puls_run_one_line, bg = self._button_bg_color)
        self._ent_puls_uf = tk.Entry(self._main_fr, textvariable=self._new_puls_uf,
                                        width=int(ent_width * 1),
                                         bg = self._entry_color, fg = self._entry_text_color)
        self._new_puls_uf.trace('w', self.trace_acceptance_change)

        # self._toggle_btn_puls.place(relx=types_start, rely=prop_vert_start+18*delta_y, relwidth = 0.043,
        #                         relheight = 0.035)

        self._puls_run_all.place(relx=types_start +0.065, rely=prop_vert_start+18*delta_y, relwidth = 0.045,
                                relheight = 0.035)

        # Buckling slider
        self._buckling_slider = tk.Scale(self._main_fr, from_=1, to=3, command=self.slider_buckling_used,length=200,
                                           orient = 'horizontal', background=self._general_color,
                                            label='RP-C201 | PULS | ML', #font=self._text_size['Text 7 bold'],
                                            relief='groove')
        self._buckling_slider.place(relx=types_start, rely=prop_vert_start+17.5*delta_y, relwidth = 0.065,
                                    relheight = 0.055)


        # --- main variable to define the structural properties ---
        self._new_material = tk.DoubleVar()
        self._new_material_factor = tk.DoubleVar()
        self._new_field_len = tk.DoubleVar()
        self._new_stf_spacing = tk.DoubleVar()
        self._new_plate_thk = tk.DoubleVar()
        self._new_stf_web_h = tk.DoubleVar()
        self._new_sft_web_t = tk.DoubleVar()
        self._new_stf_fl_w = tk.DoubleVar()
        self._new_stf_fl_t = tk.DoubleVar()
        self._new_stucture_type = tk.StringVar()
        self._new_stucture_type_label = tk.StringVar()
        self._new_sigma_y1 = tk.DoubleVar()
        self._new_sigma_y2 = tk.DoubleVar()
        self._new_sigma_x = tk.DoubleVar()
        self._new_tauxy = tk.DoubleVar()
        self._new_stf_km1 = tk.DoubleVar()
        self._new_stf_km2 = tk.DoubleVar()
        self._new_stf_km3 = tk.DoubleVar()
        self._new_stf_kps = tk.DoubleVar()
        self._new_plate_kpp = tk.DoubleVar()
        self._new_stf_type = tk.StringVar()
        self._new_pressure_side = tk.StringVar()
        self._new_puls_method = tk.StringVar()
        self._new_puls_panel_boundary = tk.StringVar()
        self._new_puls_stf_end_type = tk.StringVar()
        self._new_puls_sp_or_up = tk.StringVar()
        self._new_puls_up_boundary = tk.StringVar()
        self._new_shift_viz_coord_hor = tk.DoubleVar()
        self._new_shift_viz_coord_ver = tk.DoubleVar()


        # Setting default values to tkinter variables
        self._new_material.set(355)
        self._new_field_len.set(4)
        self._new_stf_spacing.set(750)
        self._new_plate_thk.set(18)
        self._new_stf_web_h.set(400)
        self._new_sft_web_t.set(12)
        self._new_stf_fl_w.set(150)
        self._new_stf_fl_t.set(20)
        self._new_sigma_y1.set(80)
        self._new_sigma_y2.set(80)
        self._new_sigma_x.set(50)
        self._new_stf_km1.set(12)
        self._new_stf_km2.set(24)
        self._new_stf_km3.set(12)
        self._new_stf_kps.set(1)
        self._new_plate_kpp.set(1)
        self._new_material_factor.set(1.15)
        self._new_shift_viz_coord_hor.set(0)
        self._new_shift_viz_coord_ver.set(0)

        self._new_overpresure = tk.DoubleVar()
        self._new_overpresure.set(25000)
        self._new_density = tk.DoubleVar()
        self._new_density.set(1025)
        self._new_max_el = tk.DoubleVar()
        self._new_min_el = tk.DoubleVar()

        self._new_stucture_type.set('GENERAL_INTERNAL_WT')
        self.option_meny_structure_type_trace(event='GENERAL_INTERNAL_WT')
        self._new_stf_type.set('T')
        self._new_pressure_side.set('p')
        self._new_puls_method.set('ultimate')
        self._new_puls_panel_boundary.set('Int')
        self._new_puls_stf_end_type.set('C')
        self._new_puls_sp_or_up.set('SP')
        self._new_puls_up_boundary.set('SSSS')

        #self._new_material_factor.trace('w', self.trace_material_factor)
        # --- main entries and labels to define the structural properties ---
        ent_width = 12 #width of entries
        tk.Label(self._main_fr, text='Yield [MPa]:', font = self._text_size['Text 9'],
                 bg = self._general_color)\
            .place(relx=0.185, rely=prop_vert_start + 2.6 * delta_y)
        tk.Label(self._main_fr, text='Mat. factor', font = self._text_size['Text 9'],
                 bg = self._general_color)\
            .place(relx=0.221, rely=prop_vert_start + 2.6 * delta_y)

        self._ent_mat = tk.Entry(self._main_fr, textvariable=self._new_material, bg = self._entry_color,
                                 fg = self._entry_text_color)
        self._ent_mat_factor = tk.Entry(self._main_fr, textvariable=self._new_material_factor, bg = self._entry_color,
                                 fg = self._entry_text_color)
        self._ent_field_len = tk.Entry(self._main_fr, textvariable=self._new_field_len, bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_stf_spacing = tk.Entry(self._main_fr, textvariable=self._new_stf_spacing, bg = self._entry_color,
                                         fg = self._entry_text_color)
        self._ent_plate_thk = tk.Entry(self._main_fr, textvariable=self._new_plate_thk, bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_stf_web_h = tk.Entry(self._main_fr, textvariable=self._new_stf_web_h,
                                      width = int(5*1), bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_stf_web_t = tk.Entry(self._main_fr, textvariable=self._new_sft_web_t, bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_stf_fl_w = tk.Entry(self._main_fr, textvariable=self._new_stf_fl_w, bg = self._entry_color,
                                      fg = self._entry_text_color)
        self._ent_str_fl_t = tk.Entry(self._main_fr, textvariable=self._new_stf_fl_t, bg = self._entry_color,
                                      fg = self._entry_text_color)


        self._ent_plate_kpp = tk.Entry(self._main_fr, textvariable=self._new_plate_kpp,
                                       width = int(5*1), bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_plate_kps = tk.Entry(self._main_fr, textvariable=self._new_stf_kps,
                                       width = int(5*1), bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_stf_km1 = tk.Entry(self._main_fr, textvariable=self._new_stf_km1,
                                     width = int(5*1), bg = self._entry_color,
                                     fg = self._entry_text_color)
        self._ent_stf_km2 = tk.Entry(self._main_fr, textvariable=self._new_stf_km2,
                                     width = int(5*1), bg = self._entry_color,
                                     fg = self._entry_text_color)
        self._ent_stf_km3 = tk.Entry(self._main_fr, textvariable=self._new_stf_km3,
                                     width = int(5*1), bg = self._entry_color,
                                     fg = self._entry_text_color)

        self._ent_pressure_side = tk.OptionMenu(self._main_fr, self._new_pressure_side, *('p', 's'))
        self._ent_sigma_y1= tk.Entry(self._main_fr, textvariable=self._new_sigma_y1, width = int(7*1),
                                     bg = self._entry_color, fg = self._entry_text_color)
        self._ent_sigma_y2 = tk.Entry(self._main_fr, textvariable=self._new_sigma_y2, width=int(7*1),
                                      bg = self._entry_color, fg = self._entry_text_color)
        self._ent_sigma_x = tk.Entry(self._main_fr, textvariable=self._new_sigma_x, width=int(7*1),
                                     bg = self._entry_color, fg = self._entry_text_color)
        self._ent_tauxy = tk.Entry(self._main_fr, textvariable=self._new_tauxy, width=int(7*1),
                                   bg = self._entry_color, fg = self._entry_text_color)
        # self._ent_stf_type = tk.Entry(self._main_fr, textvariable=self._new_stf_type, width=int(7*1),
        #                               bg = self._entry_color, fg = self._entry_text_color)
        self._ent_stf_type = tk.OptionMenu(self._main_fr, self._new_stf_type, *['T', 'FB', 'L', 'L-bulb'])
        self._ent_structure_type = tk.OptionMenu(self._main_fr, self._new_stucture_type,
                                                 command = self.option_meny_structure_type_trace, *self._options_type)
        self._ent_puls_sp_or_up= tk.OptionMenu(self._main_fr, self._new_puls_sp_or_up,
                                               command = self.trace_puls_up_or_sp, *['SP', 'UP'])
        self._ent_puls_method = tk.OptionMenu(self._main_fr, self._new_puls_method, *['buckling', 'ultimate'])
        self._ent_puls_panel_boundary = tk.OptionMenu(self._main_fr, self._new_puls_panel_boundary,
                                                      *['Int', 'GL', 'GT'])
        self._ent_puls_stf_end_type = tk.OptionMenu(self._main_fr, self._new_puls_stf_end_type,
                                                      *['C', 'S'])
        self._ent_puls_up_boundary = tk.Entry(self._main_fr, textvariable=self._new_puls_up_boundary, width=int(7*1),
                                   bg = self._entry_color, fg = self._entry_text_color)

        loc_y = -0.000185185


        ent_rely, ent_relx, drelx = prop_vert_start + 0.082, 0.059, 0.026
        ent_geo_y, loc_y = ent_rely-0.06, 0.000740741
        geo_ent_width, geo_dx = 0.026, 0.028
        drely = 0.05

        self._ent_structure_type.place(relx=types_start + 3 * delta_x, rely=ent_rely + 2.3 * drely, relwidth=0.10)
        tk.Label(self._main_fr, text='Select structure type:', font=self._text_size['Text 9 bold'],
                 bg = self._general_color)\
            .place(relx=types_start, rely=ent_rely + 2.5 * drely)
        tk.Button(self._main_fr,text='Show structure types',command=show_message,
                  bg = self._button_bg_color, fg = self._button_fg_color, font=self._text_size['Text 8'])\
            .place(relx=types_start + 3 * delta_x+0.1, rely=ent_rely + 2.3 * drely,relwidth = 0.07)
        self._structure_types_label = \
            tk.Label(textvariable = self._new_stucture_type_label, font = self._text_size['Text 8'],
                     bg = self._general_color)\
                .place(relx=types_start + 2.8 * delta_x, rely=ent_rely + 2.8 * drely, relwidth = 0.11, relheight = 0.02)

        tk.Label(self._main_fr,text='kpp', bg = self._general_color).place(relx=ent_relx + 0*geo_dx,
                                                                           rely=ent_rely-delta_y)
        tk.Label(self._main_fr, text='kps', bg = self._general_color).place(relx=ent_relx + 1*geo_dx,
                                                                            rely=ent_rely-delta_y)
        tk.Label(self._main_fr, text='km1', bg = self._general_color).place(relx=ent_relx + 2*geo_dx,
                                                                            rely=ent_rely-delta_y)
        tk.Label(self._main_fr, text='km2', bg = self._general_color).place(relx=ent_relx + 3*geo_dx,
                                                                            rely=ent_rely-delta_y)
        tk.Label(self._main_fr, text='k3', bg = self._general_color).place(relx=ent_relx + 4*geo_dx,
                                                                           rely=ent_rely-delta_y)
        tk.Label(self._main_fr, text='sig_y1', bg=self._general_color).place(relx=ent_relx + 0*geo_dx,
                                                                             rely=ent_rely+delta_y)
        tk.Label(self._main_fr, text='sig_y2', bg=self._general_color).place(relx=ent_relx + 1*geo_dx,
                                                                             rely=ent_rely+delta_y)
        tk.Label(self._main_fr, text='sig_x', bg=self._general_color).place(relx=ent_relx + 2*geo_dx,
                                                                            rely=ent_rely+delta_y)
        tk.Label(self._main_fr, text='tau_y1', bg=self._general_color).place(relx=ent_relx + 3*geo_dx,
                                                                             rely=ent_rely+delta_y)
        tk.Label(self._main_fr, text='stiffener type', bg=self._general_color).place(relx=ent_relx + 4*geo_dx,
                                                                               rely=ent_rely+delta_y)


        self._zstar_chk = tk.Checkbutton(self._main_fr, variable=self._new_zstar_optimization)\
            .place(relx=types_start+delta_x*9,rely=prop_vert_start+11.5*delta_y)
        tk.Label(self._main_fr, text='z* optimization (RP-C201)\n'
                                     'for buckling \ncalculations', font=self._text_size['Text 8'],
                 bg = self._general_color)\
            .place(relx=types_start + 5.9*delta_x,rely=prop_vert_start+11.3*delta_y)
        tk.Label(self._main_fr, text='Pressure side (p-plate, s-stf.):', bg=self._general_color) \
            .place(relx=types_start + 5.4*delta_x,rely=prop_vert_start+13.2*delta_y, relheight = 0.025)
        self._ent_pressure_side.place(relx=types_start+delta_x*8.5,rely=prop_vert_start+13.2*delta_y)


        tk.Label(self._main_fr, text='PULS input', bg=self._general_color, font=self._text_size['Text 8']) \
            .place(relx=types_start, rely=prop_vert_start + 10.4 * delta_y)
        tk.Label(self._main_fr, text='Siffened: SP Unstf. pl.: UP', bg=self._general_color, font=self._text_size['Text 7']) \
            .place(relx=types_start, rely=prop_vert_start + 11.2 * delta_y)
        tk.Label(self._main_fr, text='UP sup.left,right,upper,lower', bg=self._general_color, font=self._text_size['Text 7']) \
            .place(relx=types_start, rely=prop_vert_start + 11.8 * delta_y)
        tk.Label(self._main_fr, text='PULS acceptance', bg=self._general_color, font = self._text_size['Text 7'])\
            .place(relx=types_start, rely=prop_vert_start + 13 * delta_y)
        tk.Label(self._main_fr, text='PULS utilization factor:', font=self._text_size['Text 7'],
                 bg = self._general_color).place(relx=types_start, rely=prop_vert_start + 14 * delta_y)
        tk.Label(self._main_fr, text='Int-integrated GL-free left\n/right GT-free top/bottom',
                 bg=self._general_color, font = self._text_size['Text 7'])\
            .place(relx=types_start, rely=prop_vert_start + 15 * delta_y)
        tk.Label(self._main_fr, text='Continous or Sniped', bg=self._general_color,
                 font = self._text_size['Text 7'])\
            .place(relx=types_start, rely=prop_vert_start + 16.5 * delta_y)


        tk.Label(self._main_fr, text='span', bg = self._general_color).place(relx=ent_relx + 0*geo_dx,
                                                                             rely=ent_geo_y-delta_y)
        tk.Label(self._main_fr, text='s', bg = self._general_color).place(relx=ent_relx + 1*geo_dx,
                                                                          rely=ent_geo_y-delta_y)
        tk.Label(self._main_fr, text='pl_thk', bg = self._general_color).place(relx=ent_relx + 2*geo_dx,
                                                                               rely=ent_geo_y-delta_y)
        tk.Label(self._main_fr, text='web_h', bg = self._general_color).place(relx=ent_relx + 3*geo_dx,
                                                                              rely=ent_geo_y-delta_y)
        tk.Label(self._main_fr, text='web_thk', bg = self._general_color).place(relx=ent_relx + 4*geo_dx,
                                                                                rely=ent_geo_y-delta_y)
        tk.Label(self._main_fr, text='fl_w', bg = self._general_color).place(relx=ent_relx + 5*geo_dx,
                                                                             rely=ent_geo_y-delta_y)
        tk.Label(self._main_fr, text='fl_thk', bg = self._general_color).place(relx=ent_relx + 6*geo_dx,
                                                                               rely=ent_geo_y-delta_y)

        self._ent_field_len.place(relx=ent_relx + 0*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)
        self._ent_stf_spacing.place(relx=ent_relx + 1*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)
        self._ent_plate_thk.place(relx=ent_relx + 2*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)
        self._ent_stf_web_h.place(relx=ent_relx + 3*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)
        self._ent_stf_web_t.place(relx=ent_relx + 4*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)
        self._ent_stf_fl_w.place(relx=ent_relx + 5*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)
        self._ent_str_fl_t.place(relx=ent_relx + 6*geo_dx, rely=ent_geo_y, relwidth = geo_ent_width)

        y_red = 0.8
        tk.Label(self._main_fr, text='[m]', bg = self._general_color).place(relx=types_start + 2 * delta_x,
                                                                            rely=ent_geo_y+delta_y*y_red)
        tk.Label(self._main_fr, text='[mm]', bg = self._general_color).place(relx=types_start + 3*delta_x,
                                                                             rely=ent_geo_y+delta_y*y_red)
        tk.Label(self._main_fr, text='[mm]', bg = self._general_color).place(relx=types_start + 4*delta_x,
                                                                             rely=ent_geo_y+delta_y*y_red)
        tk.Label(self._main_fr, text='[mm]', bg = self._general_color).place(relx=types_start + 5*delta_x,
                                                                             rely=ent_geo_y+delta_y*y_red)
        tk.Label(self._main_fr, text='[mm]', bg = self._general_color).place(relx=types_start + 6*delta_x,
                                                                             rely=ent_geo_y+delta_y*y_red)
        tk.Label(self._main_fr, text='[mm]', bg = self._general_color).place(relx=types_start + 7*delta_x,
                                                                             rely=ent_geo_y+delta_y*y_red)
        tk.Label(self._main_fr, text='[mm]', bg = self._general_color).place(relx=types_start + 8*delta_x,
                                                                             rely=ent_geo_y+delta_y*y_red)

        self._ent_mat.place(relx=0.195, rely=ent_rely, relwidth = 0.025)
        self._ent_mat_factor.place(relx=0.23, rely=ent_rely, relwidth=0.025)
        self._ent_plate_kpp.place(relx = ent_relx , rely=ent_rely)
        self._ent_plate_kps.place(relx=ent_relx + geo_dx, rely=ent_rely)
        self._ent_stf_km1.place(relx=ent_relx + 2*geo_dx, rely=ent_rely)
        self._ent_stf_km2.place(relx=ent_relx + 3*geo_dx, rely=ent_rely)
        self._ent_stf_km3.place(relx=ent_relx + 4*geo_dx, rely=ent_rely)
        
        self._ent_sigma_y1.place(relx = ent_relx, rely=ent_rely+drely)
        self._ent_sigma_y2.place(relx=ent_relx + geo_dx, rely=ent_rely+drely)
        self._ent_sigma_x.place(relx=ent_relx + 2*geo_dx, rely=ent_rely+drely)
        self._ent_tauxy.place(relx=ent_relx + 3*geo_dx, rely=ent_rely+drely)
        self._ent_stf_type.place(relx=ent_relx + 4*geo_dx, rely=ent_rely+drely*0.8)

        # Entries below goemetry and stress input.
        shift_x = 2.9
        self._ent_puls_sp_or_up.place(relx=types_start + shift_x  * delta_x, rely=prop_vert_start + 11.2 * delta_y,
                                    relwidth=0.041)
        tk.Checkbutton(self._main_fr, variable=self._new_colorcode_puls_sp_or_up, command=self.on_color_code_check)\
            .place(relx=types_start + shift_x  * delta_x + 0.041, rely=prop_vert_start + 11.2 * delta_y)

        self._ent_puls_method.place(relx=types_start+ shift_x *delta_x, rely=prop_vert_start + 12.5 * delta_y, relwidth = 0.041)
        tk.Checkbutton(self._main_fr, variable=self._new_colorcode_puls_acceptance, command=self.on_color_code_check)\
            .place(relx=types_start+ shift_x *delta_x + 0.041, rely=prop_vert_start + 12.5 * delta_y)

        self._ent_puls_uf.place(relx=types_start+ shift_x *delta_x, rely=prop_vert_start + 13.9 * delta_y, relwidth = 0.02,
                                relheight = 0.025)
        self._ent_puls_panel_boundary.place(relx=types_start+ shift_x *delta_x,
                                            rely=prop_vert_start + 15.2 * delta_y, relwidth = 0.025)
        self._ent_puls_stf_end_type.place(relx=types_start+ shift_x *delta_x,
                                          rely=prop_vert_start + 16.5 * delta_y, relwidth = 0.025)


        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_sigmax, command = self.on_color_code_check)\
            .place(relx=ent_relx + 2*geo_dx, rely=ent_rely+1.7*drely)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_sigmay1, command = self.on_color_code_check)\
            .place(relx=ent_relx + 0*geo_dx, rely=ent_rely+1.7*drely)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_sigmay2, command = self.on_color_code_check)\
            .place(relx=ent_relx + 1*geo_dx, rely=ent_rely+1.7*drely)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_tauxy, command = self.on_color_code_check)\
            .place(relx=ent_relx + 3*geo_dx, rely=ent_rely+1.7*drely)
        tk.Checkbutton(self._main_fr, variable = self._new_colorcode_structure_type, command = self.on_color_code_check)\
            .place(relx=ent_relx + 4*geo_dx, rely=ent_rely+1.7*drely)
        # tk.Label(text='|    |   |   |   |', font=self._text_size['Text 7'],
        #          bg=self._general_color).place(relx=ent_relx + 0*geo_dx, rely=ent_rely+1.46*drely, relwidth = 0.06,
        #                                        relheight = 0.03)
        tk.Label(text='<-- Color coding', font=self._text_size['Text 9'],
                 bg=self._general_color).place(relx=ent_relx + 4.5*geo_dx, rely=ent_rely+1.46*drely, relwidth = 0.06,
                                               relheight = 0.03)

        try:
            img_file_name = 'img_stf_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            stf_button = tk.Button(self._main_fr,image = photo,command=self.on_open_structure_window,
                                   bg = 'white', fg = self._button_fg_color,)
            stf_button.image = photo
            stf_button.place(relx=types_start,rely=prop_vert_start,relheight = 0.062, relwidth = 0.042)
        except TclError:
            tk.Button(self._main_fr, text='STF.', command=self.on_open_structure_window,
                      bg = self._button_bg_color, fg = self._button_fg_color)\
                .place(relx=types_start,rely=prop_vert_start,relheight = 0.062, relwidth = 0.042)

        try:
            img_file_name = 'img_stress_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            stress_button = tk.Button(self._main_fr,image = photo,command=self.on_open_stresses_window,
                                       fg = self._button_fg_color,  bg = 'white')
            stress_button.image = photo
            stress_button.place(relx=types_start,rely=prop_vert_start+3*delta_y,relheight = 0.062, relwidth = 0.042)
        except TclError:
            tk.Button(self._main_fr, text='STRESS', command=self.on_open_stresses_window,
                      bg = self._button_bg_color, fg = self._button_fg_color)\
                .place(relx=types_start,rely=prop_vert_start+3*delta_y,relheight = 0.062, relwidth = 0.042)

        try:
            img_file_name = 'fls_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            fls_button = tk.Button(self._main_fr,image = photo,command=self.on_open_fatigue_window,
                                   bg = self._button_bg_color)
            fls_button.image = photo
            fls_button.place(relx=types_start,rely=prop_vert_start+6*delta_y,relheight = 0.062, relwidth = 0.042)
        except TclError:
            tk.Button(self._main_fr, text='FLS', command=self.on_open_fatigue_window,
                      bg = self._button_bg_color, fg = self._button_fg_color,)\
                .place(relx=types_start,rely=prop_vert_start+6*delta_y,relheight = 0.062, relwidth = 0.042)

        # --- tank load input and information ---
        load_vert_start = frame_horizontal -0.03

        tk.Label(self._main_fr,text = 'Comp. no.:', font=self._text_size['Text 8 bold'], bg = self._general_color)\
            .place(relx=types_start, rely=load_vert_start + 3.5*delta_y)

        self._selected_tank = tk.Label(self._main_fr,text='',font = self._text_size['Text 12 bold'],fg='red',
                                       bg = self._general_color)
        self._selected_tank.place(relx=0.0625, rely=load_vert_start + 3.5*delta_y)

        self._compartments_listbox = tk.Listbox(self._main_fr, height = int(10 * 1),
                                               width = int(5 * 1),
                                               font=self._text_size["Text 10 bold"]
                                               ,background=self._general_color, selectmode = 'extended' )
        self._compartments_listbox.place(relx=types_start, rely=load_vert_start + 4.2*delta_y)
        self._compartments_listbox.bind('<<ListboxSelect>>', self.button_1_click_comp_box)


        tk.Button(self._main_fr, text="Set compartment\n""properties.",command = self.update_tank,
                                            font=self._text_size['Text 9 bold'],
                  bg = self._button_bg_color, fg = self._button_fg_color)\
            .place(relx=ent_x+delta_x*3, rely=load_vert_start + delta_y * 6.5, relwidth = 0.08)

        tk.Button(self._main_fr, text="Delete all tanks", command=self.delete_all_tanks,
                  font=self._text_size['Text 9 bold'],bg = self._button_bg_color, fg = self._button_fg_color
                  ).place(relx=ent_x+delta_x*3, rely=load_vert_start + delta_y * 8.5, relwidth = 0.08)


        self._ent_content_type = tk.OptionMenu(self._main_fr, self._new_content_type, *list(self._tank_options.keys()),
                                               command=self.tank_density_trace)
        ent_width = 10

        self._ent_overpressure = tk.Entry(self._main_fr, textvariable = self._new_overpresure,
                                         width = int(ent_width * 1),
                                          bg = self._entry_color, fg = self._entry_text_color)

        self._ent_density = tk.Entry(self._main_fr, textvariable = self._new_density,
                                    width = int(ent_width * 1),
                                     bg = self._entry_color, fg = self._entry_text_color)

        self._ent_max_el = tk.Entry(self._main_fr, textvariable=self._new_max_el,
                                   width=int(ent_width * 1),
                                    bg = self._entry_color, fg = self._entry_text_color)

        self._ent_min_el = tk.Entry(self._main_fr, textvariable=self._new_min_el,
                                   width=int(ent_width * 1),
                                    bg = self._entry_color, fg = self._entry_text_color)
        tk.Label(self._main_fr, text = '', font = self._text_size["Text 12 bold"], bg = self._general_color)\
            .place(relx=0.052083333, rely=load_vert_start + 3.4*delta_y)
        tk.Label(self._main_fr, text='Tank content :', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx=ent_x-2*delta_x, rely=load_vert_start + delta_y * 4.5)
        self._ent_content_type.place(relx= ent_x+0.35*delta_x, rely=load_vert_start + delta_y * 4.5)
        tk.Label(self._main_fr, text='Tank density :', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx=ent_x-2*delta_x, rely=load_vert_start + delta_y * 6)
        self._ent_density.place(relx=ent_x+0.4*delta_x, rely=load_vert_start + delta_y * 6)
        tk.Label(self._main_fr,text='[kg/m^3]', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx= ent_x+delta_x*1.5, rely=load_vert_start + delta_y * 6)
        tk.Label(self._main_fr, text='Overpressure :', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx=ent_x-2*delta_x, rely=load_vert_start + delta_y * 7)
        self._ent_overpressure.place(relx=ent_x+0.4*delta_x, rely=load_vert_start + delta_y * 7)
        tk.Label(self._main_fr,text='[Pa]', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx= ent_x+delta_x*1.5, rely=load_vert_start + delta_y * 7)
        tk.Label(self._main_fr, text='Max elevation :', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx=ent_x-2*delta_x, rely=load_vert_start + delta_y * 8)
        self._ent_max_el.place(relx=ent_x+0.4*delta_x, rely=load_vert_start + delta_y * 8)
        tk.Label(self._main_fr, text='Min elevation :', font = self._text_size['Text 8'], bg = self._general_color)\
            .place(relx=ent_x-2*delta_x, rely=load_vert_start + delta_y * 9)
        self._ent_min_el.place(relx=ent_x+0.4*delta_x, rely=load_vert_start + delta_y * 9)
        self._tank_acc_label = tk.Label(self._main_fr, text = 'Acceleration [m/s^2]: ',
                                        font = self._text_size['Text 8'], bg = self._general_color)
        self._tank_acc_label.place(relx=ent_x-2*delta_x, rely=load_vert_start + delta_y * 10)

        # Shifing of coordinate display
        tk.Label(self._main_fr, text='Shift coordinate labeling [mm]:', font = self._text_size['Text 8'],
                 bg = self._general_color).place(relx=types_start, rely=load_vert_start + delta_y * 12.5)
        tk.Label(self._main_fr, text='y - ', font = self._text_size['Text 8'],
                 bg = self._general_color).place(relx=types_start+ delta_x*5.5, rely=load_vert_start + delta_y * 12.5)
        tk.Label(self._main_fr, text='x - ', font = self._text_size['Text 8'],
                 bg = self._general_color).place(relx=types_start+ delta_x*4, rely=load_vert_start + delta_y * 12.5)

        self._ent_shift_hor = tk.Entry(self._main_fr, textvariable = self._new_shift_viz_coord_hor,
                                       width = int(ent_width * 0.6), bg = self._entry_color, fg = self._entry_text_color)

        self._ent_shift_hor.bind('<FocusOut>', self.trace_shift_change)
        self._ent_shift_ver = tk.Entry(self._main_fr, textvariable = self._new_shift_viz_coord_ver,
                                       width = int(ent_width * 0.6), bg = self._entry_color,
                                       fg = self._entry_text_color)
        self._ent_shift_ver.bind('<FocusOut>', self.trace_shift_change)
        #self._ent_shift_ver.trace('w', self.trace_shift_change)
        self._ent_shift_hor.place(relx=types_start+delta_x*4.5, rely=load_vert_start + delta_y * 12.5)
        self._ent_shift_ver.place(relx=types_start+ delta_x*6, rely=load_vert_start + delta_y * 12.5)

        # --- button to create compartments and define external pressures ---

        try:
            img_file_name = 'img_int_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            self._int_button = tk.Button(self._main_fr,image = photo,command=self.grid_find_tanks, bg = 'white')
            self._int_button.image = photo
            self._int_button.place(relx=types_start, rely=load_vert_start+1.5*delta_y,
                                   relheight = 0.044, relwidth = 0.12)
        except TclError:
            tk.Button(self._main_fr, text='New tanks - start search \n'
                                  'to find compartments', command=self.grid_find_tanks,
                      bg = self._button_bg_color, fg = self._button_fg_color, font=self._text_size['Text 8 bold']) \
                .place(relx=types_start, rely=load_vert_start + 0 * delta_y, relheight = 0.044, relwidth = 0.12)

        show_compartment = tk.Button(self._main_fr, text='Display current\n compartments', command=self.grid_display_tanks,
                                  bg = self._button_bg_color, fg = self._button_fg_color,
                                     font=self._text_size['Text 9 bold'])
        show_compartment.place(relx=ent_x+delta_x*3, rely=load_vert_start + delta_y * 4.5, relwidth = 0.08)

        try:
            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)

            self._ext_button = tk.Button(self._main_fr,image=photo, command = self.on_show_loads,
                                         bg = 'white')
            self._ext_button.image = photo
            self._ext_button.place(relx=ent_x+delta_x*1.5, rely=load_vert_start+1.5*delta_y,
                                   relheight = 0.044, relwidth = 0.11)
        except TclError:
            tk.Button(self._main_fr, text='New external load window \nsea - static/dynamic',
                      command=self.on_show_loads, bg = self._button_bg_color, fg = self._button_fg_color,
                      font=self._text_size['Text 8 bold'])\
                .place(relx=ent_x+delta_x*2, rely=load_vert_start+0*delta_y, relheight = 0.044, relwidth = 0.11)

        lc_x, lc_x_delta, lc_y, lc_y_delta = 0.786458333, 0.015625, 0.12037037, 0.023148148

        # --- infomation on accelerations ----
        tk.Label(self._main_fr,text='Static and dynamic accelerations',
                 font = self._text_size["Text 9 bold"], fg = 'black', bg = self._general_color)\
            .place(relx=lc_x, rely=lc_y - 5 * lc_y_delta)
        tk.Label(self._main_fr,text='Static acceleration [m/s^2]: ', font = self._text_size["Text 9"],
                 bg = self._general_color )\
            .place(relx=lc_x, rely=lc_y - 4 * lc_y_delta)
        tk.Label(self._main_fr,text='Dyn. acc. loaded [m/s^2]:', font = self._text_size["Text 9"],
                 bg = self._general_color)\
            .place(relx=lc_x, rely=lc_y - 3 * lc_y_delta)
        tk.Label(self._main_fr,text='Dyn. acc. ballast [m/s^2]:', font = self._text_size["Text 9"],
                 bg = self._general_color)\
            .place(relx=lc_x, rely=lc_y - 2 * lc_y_delta)
        self._new_dyn_acc_loaded = tk.DoubleVar()
        self._new_dyn_acc_ballast = tk.DoubleVar()
        self._new_static_acc = tk.DoubleVar()
        self._new_static_acc.set(9.81), self._new_dyn_acc_loaded.set(0), self._new_dyn_acc_ballast.set(0)
        tk.Entry(self._main_fr, textvariable = self._new_static_acc,width = 10,
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=lc_x + delta_x*4.2, rely=lc_y - 4 * lc_y_delta)
        tk.Entry(self._main_fr, textvariable = self._new_dyn_acc_loaded,width = 10,
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=lc_x + delta_x*4.2, rely=lc_y - 3 * lc_y_delta)
        tk.Entry(self._main_fr, textvariable = self._new_dyn_acc_ballast,width = 10,
                 bg = self._entry_color, fg = self._entry_text_color)\
            .place(relx=lc_x + delta_x*4.2, rely=lc_y - 2 * lc_y_delta)
        tk.Button(self._main_fr, text = 'Set\naccelerations', command = self.create_accelerations,
                  font = self._text_size['Text 8 bold'],
                  bg = self._button_bg_color, fg = self._button_fg_color)\
            .place(relx=lc_x + delta_x*6, rely=lc_y - 3 * lc_y_delta)

        # --- checkbuttons and labels ---
        self._dnv_a_chk,self._dnv_b_chk  = tk.IntVar(),tk.IntVar()
        self._tank_test_chk,self._manual_chk = tk.IntVar(),tk.IntVar()
        self._check_button_load_comb = [self._dnv_a_chk,self._dnv_b_chk, self._tank_test_chk, self._manual_chk]
        self._active_label = tk.Label(self._main_fr, text = '', font = self._text_size["Text 12 bold"], fg = 'blue',
                                      bg = self._general_color)
        self._active_label.place(relx=lc_x+lc_x_delta*10,rely=lc_y-lc_y_delta*5)
        tk.Label(self._main_fr, text='Combination for line (select line). Change with slider.: ',
                 font=self._text_size["Text 8 bold"], fg='black', bg = self._general_color)\
            .place(relx=lc_x, rely=lc_y + 2.5*delta_y)

        lc_y += 0.148148148
        self._combination_slider = tk.Scale(self._main_fr, from_=1, to=3, command=self.gui_load_combinations,length=400,
                                           orient = 'horizontal', background=self._general_color,
                                            label='OS-C101 Table 1    1: DNV a)    2: DNV b)    3: TankTest',
                                            relief='groove')



        self._combination_slider.place(relx=lc_x +0*lc_x_delta, rely=lc_y - 3*lc_y_delta)
        self._combination_slider_map = {1:'dnva',2:'dnvb',3:'tanktest'}
        tk.Label(self._main_fr, text='Name:', font = self._text_size['Text 7'], bg = self._general_color)\
            .place(relx=lc_x + 0 * lc_x_delta, rely=lc_y)
        tk.Label(self._main_fr, text='Stat LF', font = self._text_size['Text 7'], bg = self._general_color)\
            .place(relx=lc_x + 8.5 * lc_x_delta, rely=lc_y)
        tk.Label(self._main_fr, text='Dyn LF', font = self._text_size['Text 7'], bg = self._general_color)\
            .place(relx=lc_x + 10.2 * lc_x_delta, rely=lc_y)
        tk.Label(self._main_fr, text='Include?',font = self._text_size['Text 7'], bg = self._general_color)\
            .place(relx=lc_x + 11.8 * lc_x_delta, rely=lc_y)

        self._result_label_dnva = tk.Label(self._main_fr, text='DNV a [Pa]: ',font='Text 8', bg = self._general_color)
        self._result_label_dnvb = tk.Label(self._main_fr, text='DNV b [Pa]: ',font=self._text_size["Text 8"],
                                           bg = self._general_color)
        self._result_label_tanktest = tk.Label(self._main_fr, text='Tank test [Pa]: ',font=self._text_size["Text 8"],
                                               bg = self._general_color)
        self._result_label_manual = tk.Label(self._main_fr, text='Manual [Pa]: ',font=self._text_size["Text 8"],
                                             bg = self._general_color)
        self.results_gui_start = 0.6
        tk.Label(self._main_fr, text = 'Pressures for this line: \n(DNV a/b [loaded/ballast], tank test, manual)\n'
                               'Note that ch. 4.3.7 and 4.3.8 is accounted for.',font=self._text_size["Text 10"],
                 bg = self._general_color)\
            .place(relx= lc_x, rely= self.results_gui_start)

        # --- optimize button ---
        tk.Label(self._main_fr,text='Optimize selected line/structure (right click line):',
                 font = self._text_size['Text 9 bold'],fg='black', bg = self._general_color)\
            .place(relx=lc_x, rely=lc_y - 7 * lc_y_delta)
        try:
            img_file_name = 'img_optimize.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            opt_button = tk.Button(self._main_fr,image=photo, command = self.on_optimize,
                                   bg = 'white', fg = self._button_fg_color)
            opt_button.image = photo
            opt_button.place(relx=lc_x, rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.098)
        except TclError:
            tk.Button(self._main_fr, text='Optimize', command=self.on_optimize_multiple,
                      bg = self._button_bg_color, fg = self._button_fg_color)\
                .place(relx=lc_x, rely=lc_y - 6 * lc_y_delta)
        try:
            img_file_name = 'img_multi_opt.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            opt_button_mult = tk.Button(self._main_fr,image=photo, command = self.on_optimize_multiple,
                                        bg = self._button_bg_color, fg = self._button_fg_color)
            opt_button_mult.image = photo
            opt_button_mult.place(relx=lc_x+delta_x*3.8, rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.065)
        except TclError:
            tk.Button(self._main_fr, text='MultiOpt', command=self.on_optimize_multiple,
                      bg = self._button_bg_color, fg = self._button_fg_color).place(relx=lc_x + delta_x*7,
                                                                                               rely=lc_y - 6 * lc_y_delta)

        tk.Button(self._main_fr, text='SPAN', command=self.on_geometry_optimize,
                 font = self._text_size['Text 14 bold'],
                  bg = self._button_bg_color, fg = self._button_fg_color)\
           .place(relx=lc_x + delta_x * 6.4,rely=lc_y - 6 * lc_y_delta, relheight = 0.04, relwidth = 0.04)

        # Load information button
        tk.Button(self._main_fr, text='Load info', command=self.button_load_info_click,
                 font = self._text_size['Text 9 bold'], height = 1,
                  bg = self._button_bg_color, fg = self._button_fg_color)\
           .place(relx=lc_x + delta_x * 6.4,rely=lc_y + delta_y*19.5, relwidth = 0.04)

        # Load information button
        tk.Button(self._main_fr, text='Load factors', command=self.on_open_load_factor_window,
                 font = self._text_size['Text 9 bold'], height = 1,
                  bg = self._button_bg_color, fg = self._button_fg_color)\
           .place(relx=lc_x + delta_x * 4.4,rely=lc_y + delta_y*19.5, relwidth = 0.05)

        # PULS result information
        self._puls_information_button = tk.Button(self._main_fr, text='PULS results for line',
                                                  command=self.on_puls_results_for_line,
                 font = self._text_size['Text 9 bold'], height = 1,
                  bg = self._button_bg_color, fg = self._button_fg_color)
        self._puls_information_button.place(relx=lc_x + delta_x * 0,rely=lc_y + delta_y*19.5, relwidth = 0.075)

        # Wight developement plot
        self._weight_button = tk.Button(self._main_fr, text='Weights',
                                                  command=self.on_plot_cog_dev,
                 font = self._text_size['Text 9 bold'], height = 1,
                  bg = self._button_bg_color, fg = self._button_fg_color)
        self._weight_button.place(relx=lc_x + delta_x * 2.9,rely=lc_y + delta_y*19.5, relwidth = 0.038)

        self.update_frame()

    def toggle_puls_run(self):
        if self._toggle_btn_puls.config('relief')[-1] == 'sunken':
            self._toggle_btn_puls.config(relief="raised")
            self._toggle_btn_puls.config(bg=self._button_bg_color)
            self._toggle_btn_puls.config(text='Use PULS\n'
                                         'results')
            self._new_toggle_puls.set(False)
        else:
            self._toggle_btn_puls.config(relief="sunken")
            self._toggle_btn_puls.config(bg='orange')
            self._toggle_btn_puls.config(text = 'PULS result\n'
                                           'override set')
            self._new_toggle_puls.set(True)

        self.update_frame()

    def puls_run_all_lines(self, line_given = None):

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
                    dict_to_run[line] = data[1].get_puls_input()
                    dict_to_run[line]['Identification'] = line
                    dict_to_run[line]['Pressure (fixed)'] = self.get_highest_pressure(line)['normal']/1e6
        else:
            current_button = self._puls_run_one
            if line_given == '':
                return
            if line_given not in result_lines:
                dict_to_run[line_given] = self._line_to_struc[line_given][1].get_puls_input()
                dict_to_run[line_given]['Identification'] = line_given
                dict_to_run[line_given]['Pressure (fixed)'] = self.get_highest_pressure(line_given)['normal'] / 1e6


        if len(dict_to_run) > 0:

            current_button.config(relief = 'sunken')
            self._PULS_results.set_all_to_run(dict_to_run)
            self._PULS_results.run_all()
            current_button.config(relief='raised')
            current_button.config(text='PULS run or\nupdate all lines' if line_given == None else 'PULS\nRun one line')
            current_button.config(bg=self._button_bg_color)
            for key, value in self._line_to_struc.items():
                value[1].need_recalc = True
        else:
            tk.messagebox.showinfo('Results avaliable', 'PULS results is already avaliable for this line or no '
                                                        'lines need update.')

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
            delta_y = 0.022
            delta_x = 0.026041667
            prop_vert_start = 0.29
            types_start = 0.005208333
            self._ent_puls_up_boundary.place(relx=types_start + 5.05 * delta_x, rely=prop_vert_start + 11.4 * delta_y,
                                         relwidth=0.02)
        else:
            self._ent_puls_up_boundary.place_forget()

    def puls_run_one_line(self):
        self.puls_run_all_lines(self._active_line)
        self.update_frame()

    def resize(self, event):
        self.text_scale = self._main_fr.winfo_width()/1920
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
            self._toggle_btn.config(bg=self._button_bg_color)
            self._multiselect_lines = []
            self._toggle_btn.config(text='Toggle select\n'
                                         'multiple')
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg='orange')
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
                    'stf_web_thk': self._new_sft_web_t.get,
                    'stf_flange_width': self._new_stf_fl_w.get,
                    'stf_flange_thk': self._new_stf_fl_t.get,
                    'structure_type': self._new_stucture_type.get,
                    'stf_type': self._new_stf_type.get,
                    'sigma_y1': self._new_sigma_y1.get,
                    'sigma_y2': self._new_sigma_y2.get,
                    'sigma_x': self._new_sigma_x.get,
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
                    'puls stiffener end': self._new_puls_stf_end_type.get,
                    'puls sp or up': self._new_puls_sp_or_up.get,
                    'puls up boundary': self._new_puls_up_boundary.get}


        set_var = obj_dict[var_to_set]()
        if var_to_set == 'mat_yield':
            set_var = set_var* 1e6
        elif var_to_set in ['spacing','plate_thk','stf_web_height','stf_web_thk',
                            'stf_flange_width','stf_flange_thk']:
            set_var = set_var/1000
        no_of_lines = len(self._multiselect_lines)
        for idx, line in enumerate(self._multiselect_lines):
            self._active_line = line
            self._line_is_active = True
            if self._active_line in self._line_to_struc.keys():
                dict = self._line_to_struc[self._active_line][1].get_structure_prop()
                dict[var_to_set][0] = set_var

                self.new_structure(toggle_multi=dict, suspend_recalc=True if (idx+1) != no_of_lines else False)

    def slider_buckling_used(self, event):

        if self._buckling_slider.get() == 1:
            self._new_buckling_slider.set(1)
            self._ent_puls_uf.config(bg = 'white')
        elif self._buckling_slider.get() == 2:
            self._new_buckling_slider.set(2)
            self._ent_puls_uf.config(bg='white')
        elif self._buckling_slider.get() == 3:
            self._new_buckling_slider.set(3)
            self._ent_puls_uf.config(bg = 'red')
        else:
            pass
        self.update_frame()

    def gui_load_combinations(self,event):
        '''
        Initsializing and updating gui for load combinations.
        The fields are located left of the Canvas.
        :return:
        '''

        if self._line_is_active and self._active_line in self._line_to_struc.keys():
            lc_x, lc_x_delta, lc_y, lc_y_delta = 0.791666667, 0.026041667, 0.287037037, 0.023148148

            self._active_label.config(text=self._active_line)
            combination = self._combination_slider_map[self._combination_slider.get()]

            # removing label, checkbox and entry. setting created items to empty list.
            [[item.destroy() for item in items] for items in
             [self._lc_comb_created,self._comp_comb_created,self._manual_created, self._info_created]]
            self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created= [], [], [], []

            if self._line_to_struc[self._active_line][0].get_structure_type() == '':
                self._info_created.append(tk.Label(self._main_fr, text='No structure type selected',
                                               font=self._text_size["Text 10 bold"], bg = self._general_color))
                self._info_created[0].place(relx=lc_x , y = lc_y + 3*lc_y_delta)

            else:
                # creating new label, checkbox and entry. creating new list of created items.
                # finding loads applied to lines
                counter = 0

                if len(self._load_dict) != 0 and combination !='manual':
                    for load, data in self._load_dict.items():
                        if self._active_line in self._load_dict[load][1] and data[0].get_limit_state() == 'ULS':
                            name = (combination,self._active_line,str(load)) #tuple to identify combinations on line
                            self._lc_comb_created.append(tk.Label(self._main_fr, text = load,
                                                                 font = self._text_size['Text 8 bold'],
                                                                  bg = self._general_color))
                            self._lc_comb_created.append(tk.Entry(self._main_fr,
                                                                 textvariable =self._new_load_comb_dict[name][0],
                                                                  width=5, bg = self._entry_color,
                                                                  fg = self._entry_text_color))
                            self._lc_comb_created.append(tk.Entry(self._main_fr,
                                                                 textvariable=self._new_load_comb_dict[name][1],
                                                                 width=5, bg = self._entry_color,
                                                                  fg = self._entry_text_color))
                            self._lc_comb_created.append(tk.Checkbutton(self._main_fr,
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
                        self._comp_comb_created.append(tk.Label(self._main_fr, text='Compartment'+str(compartment),
                                                               font=self._text_size['Text 8 bold']))
                        self._comp_comb_created.append(tk.Entry(self._main_fr,
                                                               textvariable=self._new_load_comb_dict[name][0],
                                                                width=5, bg = self._entry_color,
                                                                fg = self._entry_text_color))
                        self._comp_comb_created.append(tk.Entry(self._main_fr,
                                                               textvariable=self._new_load_comb_dict[name][1],
                                                                width=5, bg = self._entry_color,
                                                                fg = self._entry_text_color))
                        self._comp_comb_created.append(tk.Checkbutton(self._main_fr,
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
                    self._manual_created.append(tk.Label(self._main_fr, text='Manual (pressure/LF)',
                                                        font=self._text_size['Text 8 bold'],
                                                         bg = self._general_color))
                    self._manual_created.append(
                        tk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][0], width=15,
                                 bg = self._entry_color, fg = self._entry_text_color))
                    self._manual_created.append(
                        tk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][1], width=6,
                                 bg = self._entry_color, fg = self._entry_text_color))
                    self._manual_created.append(tk.Checkbutton(self._main_fr, variable=self._new_load_comb_dict[name][2]))
                    self._manual_created[0].place(relx=lc_x, rely=lc_y)
                    self._manual_created[1].place(relx=lc_x + 4 * lc_x_delta, rely=lc_y)
                    self._manual_created[2].place(relx=lc_x + 6 * lc_x_delta, rely=lc_y)
                    self._manual_created[3].place(relx=lc_x + 7 * lc_x_delta, rely=lc_y)

            #printing the results

            #try:
            # TODO the reason manual does not show is because it others do noe exist in line_comb_dict. FIX.
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
            # except KeyError:
            #     pass

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
            if self._line_to_struc[line][0].get_structure_type() not in ('GENERAL_INTERNAL_NONWT','FRAME'):
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
                val[1].need_recalc = True
        except (TclError, ZeroDivisionError):
            pass

    def update_frame(self, event = None, *args):

        state = self.get_color_and_calc_state()
        self.draw_results(state=state)
        self.draw_canvas(state=state)
        self.draw_prop()
        self.trace_puls_up_or_sp()

        return state

    def get_color_and_calc_state(self, current_line = None, active_line_only = False):
        ''' Return calculations and colors for line and results. '''

        return_dict = {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                       'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                       'struc_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}, 'utilization': {}, 'slamming': {},
                       'color code': {}, 'PULS colors': {}, 'ML buckling colors' : {}, 'ML buckling class' : {},
                       'weights': {}}

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
                obj_structure = self._line_to_struc[current_line][0]
                obj_scnt_calc = self._line_to_struc[current_line][1]
                if obj_scnt_calc.need_recalc is False:
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

                sec_mod = [obj_scnt_calc.get_section_modulus()[0],
                           obj_scnt_calc.get_section_modulus()[1]]

                shear_area = obj_scnt_calc.get_shear_area()
                min_shear = obj_scnt_calc.get_minimum_shear_area(design_pressure)
                min_sec_mod = obj_scnt_calc.get_dnv_min_section_modulus(design_pressure)
                min_thk = obj_scnt_calc.get_dnv_min_thickness(design_pressure)
                buckling = [round(res, 2) for res in obj_scnt_calc.calculate_buckling_all(
                    design_lat_press=design_pressure,
                    checked_side=obj_scnt_calc.get_side())]

                rec_for_color[current_line]['section modulus'] = min_sec_mod/min(sec_mod)

                rec_for_color[current_line]['plate thickness'] = (min_thk/1000)/obj_scnt_calc.get_pl_thk()
                rec_for_color[current_line]['rp buckling'] = max(buckling)

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

                color_sec = 'green' if obj_scnt_calc.is_acceptable_sec_mod(sec_mod, design_pressure) else 'red'
                color_shear = 'green' if obj_scnt_calc.is_acceptable_shear_area(shear_area, design_pressure) else 'red'
                color_thk = 'green' if obj_scnt_calc.is_acceptable_pl_thk(design_pressure) else 'red'
                color_buckling = 'green' if all([uf <= 1 for uf in buckling]) \
                    else 'red'

                if slamming_pressure is not None and slamming_pressure > 0:
                    slamming_res = obj_scnt_calc.calculate_slamming_stiffener(slamming_pressure,
                                                                              red_fac=slamming_red_fac_pl)
                    min_pl_slamming = obj_scnt_calc.calculate_slamming_plate(slamming_pressure,
                                                                             red_fac=slamming_red_fac_stf)

                    if slamming_res['Zp_req'] is not None:
                        zpl = obj_scnt_calc.get_net_effective_plastic_section_modulus()
                        zpl_req = slamming_res['Zp_req']
                        color_sec = 'green' if zpl >= zpl_req else 'red'
                    else:
                        zpl = obj_scnt_calc.get_net_effective_plastic_section_modulus()
                        zpl_req = None
                        color_sec = 'red'

                    color_shear = 'green' if round(obj_scnt_calc.get_web_thk()* 1000,1)  >= \
                                             round(slamming_res['tw_req'],1) else 'red'
                    color_thk = 'green' if round(obj_scnt_calc.get_pl_thk() * 1000,1) >= \
                                           round(min_pl_slamming,1) else 'red'

                    return_dict['slamming'][current_line]['zpl'] = zpl
                    return_dict['slamming'][current_line]['zpl_req'] = zpl_req
                    return_dict['slamming'][current_line]['min_plate_thk'] = min_pl_slamming
                    return_dict['slamming'][current_line]['min_web_thk'] = slamming_res['tw_req']

                return_dict['colors'][current_line] = {'buckling': color_buckling, 'fatigue': color_fatigue,
                                                       'section': color_sec, 'shear': color_shear,
                                                       'thickness': color_thk}
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
                            loc_label = 'Local geom req (PULS validity limits)' if \
                                obj_scnt_calc.get_puls_sp_or_up() == 'SP' else 'Geom. Req (PULS validity limits)'
                            loc_geom = 'green' if all([val[0] == 'Ok' for val in res[loc_label].values()]) else 'red'
                        csr_label = 'CSR-Tank requirements (primary stiffeners)' if \
                            obj_scnt_calc.get_puls_sp_or_up() == 'SP' else'CSR-Tank req'

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

                if obj_scnt_calc.get_puls_sp_or_up() == 'UP':
                    buckling_ml_input = obj_scnt_calc.get_buckling_ml_input(design_lat_press=design_pressure)

                    if obj_scnt_calc.get_puls_boundary() == 'Int':
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

                    x_csr = obj_scnt_calc.get_buckling_ml_input(design_lat_press=design_pressure, csr = True)
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
                    buckling_ml_input = obj_scnt_calc.get_buckling_ml_input(design_lat_press=design_pressure)
                    if obj_scnt_calc.get_puls_boundary() == 'Int':
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

                    x_csr = obj_scnt_calc.get_buckling_ml_input(design_lat_press=design_pressure, csr = True)
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
                line_weight = op.calc_weight([obj_scnt_calc.get_s(), obj_scnt_calc.get_pl_thk(),
                                              obj_scnt_calc.get_web_h(), obj_scnt_calc.get_web_thk(),
                                              obj_scnt_calc.get_fl_w(), obj_scnt_calc.get_fl_thk(),
                                              obj_scnt_calc.get_span(), obj_scnt_calc.get_lg()])
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
                return_dict['section_modulus'][current_line] = {'sec_mod': sec_mod, 'min_sec_mod': min_sec_mod}
                return_dict['shear_area'][current_line] = {'shear_area': shear_area, 'min_shear_area': min_shear}
                return_dict['thickness'][current_line] = {'thk': obj_scnt_calc.get_plate_thk(), 'min_thk': min_thk}
                return_dict['struc_obj'][current_line] = obj_structure
                return_dict['scant_calc_obj'][current_line] = obj_scnt_calc
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
                thk_util = 0 if obj_structure.get_plate_thk() == 0 else min_thk / (1000 * obj_structure.get_plate_thk())
                sec_util = 0 if min(sec_mod) == 0 else min_sec_mod / min(sec_mod)
                buc_util = 1 if float('inf') in buckling else max(buckling[0:5])
                rec_for_color[current_line]['rp buckling'] = max(buckling[0:5])
                return_dict['utilization'][current_line] = {'buckling': buc_util,
                                                            'PULS buckling': buc_util, # TODO double check
                                                            'fatigue': fat_util,
                                                            'section': sec_util,
                                                            'shear': shear_util,
                                                            'thickness': thk_util}

                # Color coding state

                self._state_logger[current_line] = return_dict #  Logging the current state of the line.
                self._line_to_struc[current_line][1].need_recalc = False
            else:
                pass

        sec_in_model, idx, recorded_sections = dict(), 0, list()
        for data in self._line_to_struc.values():
            if data[1].get_beam_string() not in recorded_sections:
                sec_in_model[data[1].get_beam_string()] = idx
                recorded_sections.append(data[1].get_beam_string())
                idx += 1
        sec_in_model['length'] = len(recorded_sections)

        if self._line_to_struc != {}:
            sec_mod_map = np.arange(0,1.1,0.1)
            fat_map = np.arange(0,1.1,0.1)
            all_thicknesses = [round(objs[0].get_pl_thk(), 5) for objs in self._line_to_struc.values()]
            all_thicknesses = np.unique(all_thicknesses).tolist()
            thickest_plate = max(all_thicknesses)
            if len(all_thicknesses) > 1:
                thk_map = np.arange(min(all_thicknesses), max(all_thicknesses) + (max(all_thicknesses) - min(all_thicknesses)) / 10,
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
                # util_map = np.arange(min(all_utils), max(all_utils) + (max(all_utils) - min(all_utils)) / 10,
                #                      (max(all_utils) - min(all_utils)) / 10)
                util_map =  np.arange(0, 1.1, 0.1)

            else:
                util_map = all_utils

            if self._PULS_results is not None:
                #puls_util_map = self._PULS_results.all_uf
                puls_util_map = list()
                for key, val in self._line_to_struc.items():
                    puls_util_map.append(self._PULS_results.get_utilization(key, val[0].get_puls_method(),
                                                                            acceptance = self._new_puls_uf.get()))
                # puls_util_map  = np.arange(min(puls_util_map), max(puls_util_map) + (max(puls_util_map) -
                #                                                                      min(puls_util_map)) / 10,
                #                      (max(puls_util_map) - min(puls_util_map)) / 10)
                puls_util_map  = np.arange(0, 1.1, 0.1)
            else:
                puls_util_map = None

            sig_x = np.unique([self._line_to_struc[line][1].get_sigma_x() for line in self._line_to_struc.keys()]).tolist()
            if len(sig_x) > 1:
                sig_x_map = np.arange(min(sig_x), max(sig_x) + (max(sig_x) - min(sig_x)) / 10,
                                      (max(sig_x) - min(sig_x)) / 10)
            else:
                sig_x_map = sig_x
            sig_y1 = np.unique([self._line_to_struc[line][1].get_sigma_y1() for line in self._line_to_struc.keys()]).tolist()
            if len(sig_y1) > 1:
                sig_y1_map = np.arange(min(sig_y1), max(sig_y1) + (max(sig_y1) - min(sig_y1)) / 10,
                                       (max(sig_y1) - min(sig_y1)) / 10)
            else:
                sig_y1_map = sig_y1

            sig_y2 = np.unique([self._line_to_struc[line][1].get_sigma_y2() for line in self._line_to_struc.keys()]).tolist()
            if len(sig_y2) > 1:

                sig_y2_map = np.arange(min(sig_y2), max(sig_y2) + (max(sig_y2) - min(sig_y2)) / 10,
                                       (max(sig_y2) - min(sig_y2)) / 10)
            else:
                sig_y2_map = sig_y2
            tau_xy = np.unique([self._line_to_struc[line][1].get_tau_xy() for line in self._line_to_struc.keys()]).tolist()
            if len(tau_xy) > 1:
                tau_xy_map = np.arange(min(tau_xy), max(tau_xy) + (max(tau_xy) - min(tau_xy)) / 10,
                                       (max(tau_xy) - min(tau_xy)) / 10)
            else:
                tau_xy_map = tau_xy

            spacing = np.unique([self._line_to_struc[line][1].get_s() for line in self._line_to_struc.keys()]).tolist()
            structure_type = [self._line_to_struc[line][1].get_structure_type() for line in
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
                elif self._PULS_results.get_utilization(line, self._line_to_struc[line][1].get_puls_method(),
                                                        self._new_puls_uf.get()) == None:
                    puls_color, buc_uf, puls_uf, puls_method, puls_sp_or_up = 'black', 0,0, None, None
                else:
                    puls_method = self._line_to_struc[line][1].get_puls_method()
                    puls_uf = self._PULS_results.get_utilization(
                                                   line, puls_method,
                                                   self._new_puls_uf.get())
                    puls_color = matplotlib.colors.rgb2hex(cmap_sections(puls_uf))
                    puls_sp_or_up = self._line_to_struc[line][1].get_puls_sp_or_up()

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
                                                     [line_data[1].get_sigma_x(), line_data[1].get_sigma_y1(),
                                                      line_data[1].get_sigma_y2(), line_data[1].get_tau_xy()]):
                    if len(stress_list) == 1:
                        res.append(1)
                    elif max(stress_list) == 0 and min(stress_list) == 0:
                        res.append(0)
                    elif this_stress < 0:
                        res.append(this_stress /min(stress_list))
                    elif this_stress >= 0:
                        res.append(this_stress/ max(stress_list))

                sig_x_uf, sig_y1_uf, sig_y2_uf , tau_xy_uf = res


                line_color_coding[line] = {'plate': matplotlib.colors.rgb2hex(cmap_sections(thk_sort_unique.index(round(line_data[1]
                                                                              .get_pl_thk(),10))/len(thk_sort_unique))),
                                           'spacing': matplotlib.colors.rgb2hex(
                                               cmap_sections(spacing_sort_unique.index(round(line_data[1]
                                                                                         .get_s(), 10)) / len(
                                                   spacing_sort_unique))),
                                           'section': matplotlib.colors.rgb2hex(cmap_sections(sec_in_model[line_data[1]
                                                                                .get_beam_string()]
                                                      /len(list(recorded_sections)))),
                                           'structure type': matplotlib.colors.rgb2hex(
                                               cmap_sections(structure_type_unique.index(line_data[1].get_structure_type())
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
                                         stipple= 'gray50')
            self._main_canvas.create_line(0, self._canvas_draw_origo[1], self._canvas_dim[0] +500, self._canvas_draw_origo[1],
                                         stipple='gray50')
            self._main_canvas.create_text(self._canvas_draw_origo[0] - 30 * 1,
                                          self._canvas_draw_origo[1] + 12 * 1, text='(0,0)',
                                          font='Text 10')

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
                                              font=self._text_size["Text 8 bold"], fill='black')

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
                                          fill = 'black')

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
                coord_color = 'black'

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
                                                  font="Text 10")
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
                        if self._new_buckling_slider.get() == 2:
                            if 'black' in state['PULS colors'][line].values():
                                color = 'black'
                            else:
                                col1, col2 = state['PULS colors'][line]['buckling'], \
                                             state['PULS colors'][line]['ultimate']

                                if self._line_to_struc[line][1].get_puls_method() == 'buckling':
                                    color = 'red' if any([col1 == 'red', col2 == 'red']) else 'green'
                                else:
                                    color = col2

                                if color == 'green':
                                    color = 'green' if all([state['colors'][line][key] == 'green' for key in
                                                            ['fatigue', 'section', 'shear','thickness']]) else 'red'
                        elif self._new_buckling_slider.get() == 1:
                            color = 'red' if 'red' in state['colors'][line].values() else 'green'
                        elif self._new_buckling_slider.get() == 3:
                            if 'black' in state['ML buckling colors'][line].values():
                                color = 'black'
                            else:
                                col1, col2 = state['ML buckling colors'][line]['buckling'], \
                                             state['ML buckling colors'][line]['ultimate']

                                if self._line_to_struc[line][1].get_puls_method() == 'buckling':
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
                if line == self._active_line and self._line_is_active:
                    self._main_canvas.create_line(coord1, coord2, width=6, fill = color)
                    if self._new_line_name.get():
                        self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2+10,
                                                     text='Line ' + str(get_num(line)),
                                                      font=self._text_size["Text 10 bold"],
                                                     fill = 'red')
                else:
                    self._main_canvas.create_line(coord1, coord2, width=3, fill = color)
                    if self._new_line_name.get():
                        self._main_canvas.create_text(coord1[0]-20 + vector[0] / 2 + 5, coord1[1] + vector[1] / 2+10,
                                                     text='l.' + str(get_num(line)), font="Text 8", fill = 'black')
                if line in self._multiselect_lines:
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 +5, coord1[1] + vector[1] / 2 -10,
                                                  text=self._new_toggle_var.get(),
                                                  font=self._text_size["Text 8 bold"],
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
                  self._line_to_struc != {}, self._new_buckling_slider.get() != 2]):
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
                  self._line_to_struc != {}, self._new_buckling_slider.get() == 2]):
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
            color = state['color code']['lines'][line]['section']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=self._line_to_struc[line][1].get_beam_string() ,
                                              font=self._text_size["Text 7"])

        elif self._new_colorcode_plates.get() == True and line in list(self._line_to_struc.keys()):
            color = state['color code']['lines'][line]['plate']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=str(self._line_to_struc[line][1].get_pl_thk()*1000))
        elif self._new_colorcode_spacing.get() == True and line in list(self._line_to_struc.keys()):
            color = state['color code']['lines'][line]['spacing']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=str(self._line_to_struc[line][1].get_s()*1000))

        elif self._new_colorcode_pressure.get() == True and line in list(self._line_to_struc.keys()):
            if cc_state['all pressures'] == [0, 1]:
                color = 'black'
            else:
                color = state['color code']['lines'][line]['pressure color']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=str(state['color code']['lines'][line]['pressure']))

        elif self._new_colorcode_utilization.get() == True and self._new_buckling_slider.get() == 1:
            color = state['color code']['lines'][line]['rp uf color']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=round(state['color code']['lines'][line]['rp uf'],2))

        elif self._new_colorcode_utilization.get() == True and self._new_buckling_slider.get() == 2:
            color = state['color code']['lines'][line]['PULS uf color']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=round(state['color code']['lines'][line]['PULS uf'],2))
        elif self._new_colorcode_utilization.get() == True and self._new_buckling_slider.get() == 3:
            color = 'black'
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text='N/A')

        elif self._new_colorcode_sigmax.get() == True:
            color = state['color code']['lines'][line]['sigma x']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=str(self._line_to_struc[line][1].get_sigma_x()))

        elif self._new_colorcode_sigmay1.get() == True:
            color = state['color code']['lines'][line]['sigma y1']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=str(self._line_to_struc[line][1].get_sigma_y2()))

        elif self._new_colorcode_sigmay2.get() == True:
            color = state['color code']['lines'][line]['sigma y2']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=str(self._line_to_struc[line][1].get_sigma_y2()))

        elif self._new_colorcode_tauxy.get() == True:
            color = state['color code']['lines'][line]['tau xy']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=round(self._line_to_struc[line][1].get_tau_xy(),2))

        elif self._new_colorcode_structure_type.get() == True:
            color = state['color code']['lines'][line]['structure type']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=self._line_to_struc[line][1].get_structure_type(),
                                              font=self._text_size["Text 7"])

        elif self._new_colorcode_section_modulus.get() == True:
            color = state['color code']['lines'][line]['section modulus color']
            if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['section uf'],2))

        elif self._new_colorcode_fatigue.get() == True:
            color = state['color code']['lines'][line]['fatigue color']
            if self._new_label_color_coding.get():
                self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                              text=round(state['color code']['lines'][line]['fatigue uf'],2))

        elif self._new_colorcode_total.get() == True:
            if self._new_buckling_slider.get() == 2:
                color = state['color code']['lines'][line]['Total uf color rp']
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['Total uf puls'],2))
            elif self._new_buckling_slider.get() == 1:
                color = state['color code']['lines'][line]['Total uf color puls']
                if self._new_label_color_coding.get():
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 - 10,
                                                  text=round(state['color code']['lines'][line]['Total uf rp'],2))
            elif self._new_buckling_slider.get() == 3:
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

    def draw_prop(self):
        '''
        Prints the properties of the selected line to the bottom canvas.

        properties for line dicitonary:

        name of line : [ Structure class, calc scantling class, calc fatigue class, [load classes] ]

        '''
        self._prop_canvas.delete('all')
        canvas_width = self._prop_canvas.winfo_width()
        canvas_height = self._prop_canvas.winfo_height()
        if self._active_line in self._line_to_struc:

            # printing the properties to the active line
            if self._line_is_active:
                self._prop_canvas.create_text([canvas_width*0.239726027, canvas_height*0.446096654],
                                             text=self._line_to_struc[self._active_line][0],
                                             font = self._text_size["Text 9"])

                # setting the input field to active line properties
                self.set_selected_variables(self._active_line)

                # draw the plate and stiffener
                mult = 200*1
                thk_mult = 500*1
                startx = 540*1
                starty = 150*1
                structure_obj = self._line_to_struc[self._active_line][0]

                self._prop_canvas.create_text([canvas_width/2-canvas_width/20, canvas_height/20],
                                             text ='SELECTED: '+str(self._active_line),
                                             font=self._text_size["Text 10 bold"], fill='red')
                spacing = structure_obj.get_s()*mult
                stf_web_height = structure_obj.get_web_h()*mult
                stf_flange_width = structure_obj.get_fl_w() * mult
                plate_thk = structure_obj.get_pl_thk()*thk_mult
                stf_web_thk = structure_obj.get_web_thk()*thk_mult
                stf_flange_thk = structure_obj.get_fl_thk()*thk_mult

                self._prop_canvas.create_line(startx,starty,startx+spacing,starty, width = plate_thk)
                self._prop_canvas.create_line(startx+spacing*0.5,starty,startx+spacing*0.5,starty-stf_web_height,
                                             width=stf_web_thk )
                if structure_obj.get_stiffener_type() not in ['L', 'L-bulb']:
                    self._prop_canvas.create_line(startx+spacing*0.5-stf_flange_width/2,starty-stf_web_height,
                                             startx + spacing * 0.5 + stf_flange_width / 2, starty - stf_web_height,
                                             width=stf_flange_thk)
                else:
                    self._prop_canvas.create_line(startx+spacing*0.5-stf_web_thk/2,starty-stf_web_height,
                                             startx + spacing * 0.5 + stf_flange_width , starty - stf_web_height,
                                             width=stf_flange_thk)

                # load applied to this line
                deltax = 160*1
                stl_x = canvas_width*0.684931507
                stl_y = canvas_height*0.63197026

                self._prop_canvas.create_text([stl_x,stl_y], text='Applied static/dynamic loads:',
                                             font=self._text_size["Text 7 bold"])
                count = 0
                for load, data in self._load_dict.items():
                    if self._active_line in data[1]:
                        self._prop_canvas.create_text([stl_x+deltax, stl_y+count], text = load,
                                                     font=self._text_size['Text 7'])
                        count += 10

                # printing the tanks applied to this line
                stt_x = stl_x
                stt_y = 10

                if len(self._tank_dict) != 0:
                    self._prop_canvas.create_text([stt_x, stt_y], text='Applied compartments: ',
                                                 font=self._text_size["Text 7 bold"])
                    count = 0
                    for comp in self.get_compartments_for_line(self._active_line):
                        self._prop_canvas.create_text([stt_x+deltax, stt_y+count], text = 'Compartment ' + str(comp),
                                                     font=self._text_size["Text 7"])
                        count += 10
            else:
                self._prop_canvas.create_text([canvas_width*0.4, height*0.185873606],
                                             text='No line is selected. Click on a line to show properies',
                                             font=self._text_size['Text 9 bold'])
        else:
            pass

    def draw_results(self, state = None):
        '''
        The properties canvas is created here.
                state =     {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                            'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                            'struc_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}}
        :return:
        '''

        self._result_canvas.delete('all')

        if state is None or self._active_line not in state['struc_obj'].keys():
            return

        if self._line_is_active:
            x, y, dx, dy = 0, 15, 15, 14

            if self._active_line in self._line_to_struc:

                m3_to_mm3 = float(math.pow(1000,3))
                m2_to_mm2 = float(math.pow(1000, 2))

                current_line = self._active_line

                obj_structure = state['struc_obj'][current_line]
                sec_mod = [round(state['section_modulus'][current_line]['sec_mod'][0], 5),
                           round(state['section_modulus'][current_line]['sec_mod'][1], 5)]
                shear_area = state['shear_area'][current_line]['shear_area']
                min_shear = state['shear_area'][current_line]['min_shear_area']
                min_sec_mod = state['section_modulus'][current_line]['min_sec_mod']
                min_thk = state['thickness'][current_line]['min_thk']
                buckling = [round(res, 2) for res in state['buckling'][current_line]]

                if state['slamming'][current_line]['state']:
                    slamming = True
                    slm_zpl = state['slamming'][current_line]['zpl']
                    slm_zpl_req = state['slamming'][current_line]['zpl_req']
                    slm_min_pl_thk = state['slamming'][current_line]['min_plate_thk']
                    slm_min_web_thk = state['slamming'][current_line]['min_web_thk']

                    slm_text_pl_thk = 'Minimum plate thickness (BOW SLAMMING): '+str(round(slm_min_pl_thk,1))+' [mm]' \
                        if obj_structure.get_plate_thk() * 1000 < slm_min_pl_thk else None

                    slm_text_min_web_thk = 'Minimum web thickness (BOW SLAMMING): '+str(round(slm_min_web_thk,1))+' [mm]' \
                        if obj_structure.get_web_thk()*1000 < slm_min_web_thk else None
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

                # printing the calculated sectiton modulus
                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = 'Slamming strength violation for web thickness.'
                else:
                    text = 'Section moduluses: ' + \
                           'Wey1: '+ str('%.4E' % decimal.Decimal(sec_mod[1]*m3_to_mm3))+ ' [mm^3], '+\
                           ' Wey2: ' + str('%.4E' % decimal.Decimal(sec_mod[0]*m3_to_mm3)) + ' [mm^3] ' \
                        if not slm_text_min_zpl else 'Net effective plastic section modulus: ' +str(slm_zpl)+' [cm^3]'
                self._result_canvas.create_text([x*1, y*1],
                                               text=text,font=self._text_size['Text 9 bold'],anchor='nw')
                #printing the minimum section modulus
                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = '(shear issue, change thickness or web height)'
                else:
                    text =  'Minimum section modulus: '+str('%.4E' % decimal.Decimal(min_sec_mod * m3_to_mm3)) +\
                            ' [mm^3] ' if not slm_text_min_zpl else slm_text_min_zpl
                self._result_canvas.create_text([x*1, (y+dy)*1], text= text,
                                                    font=self._text_size["Text 9 bold"],anchor='nw', fill=color_sec)

                #minimum shear area
                text = 'Shear area: '+str('%.4E' % decimal.Decimal(shear_area * m2_to_mm2 ))+' [mm^2]' \
                    if not slm_text_min_web_thk else 'Stiffener web thickness: '+str(obj_structure.get_web_thk()*1000)+' [mm]'
                self._result_canvas.create_text([x*1, (y+3*dy)*1],
                                               text= text,
                                               font=self._text_size["Text 9 bold"],anchor='nw')
                text = 'Minimum shear area: '+str('%.4E' % decimal.Decimal(min_shear * m2_to_mm2))+' [mm^2] ' \
                    if not slm_text_min_web_thk else 'Minimum stiffener web thickness due to SLAMMING: '+\
                                                     str(round(slm_min_web_thk,1))+' [mm]'
                self._result_canvas.create_text([x*1, (y+4*dy)*1],
                                               text = text,
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_shear)

                #minimum thickness for plate

                self._result_canvas.create_text([x*1, (y+6*dy)*1],
                                               text='Plate thickness: '
                                                    +str(obj_structure.get_plate_thk()*1000)+' [mm] ',
                                               font=self._text_size["Text 9 bold"],anchor='nw')
                text = 'Minimum plate thickness: '+str(round(min_thk,1)) + ' [mm]' if not slm_text_pl_thk \
                    else 'Minimum plate thickness due to SLAMMING'+str(slm_min_pl_thk)+' [mm]'
                self._result_canvas.create_text([x*1, (y+7*dy)*1],
                                               text=text,
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_thk)

                # buckling results

                if self._PULS_results != None and self._new_buckling_slider.get() == 2:
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
                            obj_structure.get_puls_sp_or_up() == 'SP' else 'Geom. Req (PULS validity limits)'
                        csr_label = 'CSR-Tank requirements (primary stiffeners)' if \
                            obj_structure.get_puls_sp_or_up() == 'SP' else 'CSR-Tank req'
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
                        self._result_canvas.create_text([x * 1, y + 8.5 * dy], text='PULS results',
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill='black')
                        self._result_canvas.create_text([x * 1, y + 9.5 * dy], text=buc_text,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['buckling'])
                        self._result_canvas.create_text([x * 1, y + 10.5 * dy], text=ult_text,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['ultimate'])
                        self._result_canvas.create_text([x * 1, y + 11.5 * dy], text=loc_geom,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['local geometry'])
                        self._result_canvas.create_text([x * 1, y + 12.5 * dy], text=csr_geom,
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill=line_results['csr'])
                    else:
                        self._result_canvas.create_text([x * 1, y + 9 * dy],
                                                        text='PULS results not avaliable for this line.\n'
                                                             'Run or update lines.',
                                                        font=self._text_size['Text 9 bold'],
                                                        anchor='nw',
                                                        fill='Orange')
                elif self._new_buckling_slider.get() == 1:
                    self._result_canvas.create_text([x * 1, (y+9*dy) * 1],
                                                   text='Buckling results DNV-RP-C201:',
                                                   font=self._text_size["Text 9 bold"], anchor='nw')
                    if sum(buckling)==0:
                        self._result_canvas.create_text([x * 1, (y+10*dy) * 1],
                                                       text='No buckling results', font=self._text_size["Text 9 bold"],
                                                       anchor='nw', fill=color_buckling)
                    else:
                        if buckling[0]==float('inf'):
                            res_text = 'Plate resistance not ok (equation 6.12). '
                        elif buckling[1] == float('inf'):
                            res_text = 'Spacing/thickness aspect ratio error (equation eq 6.11 - ha < 0). '
                        else:
                            if obj_structure.get_side() == 'p':
                                res_text = '|eq 7.19: '+str(buckling[0])+' |eq 7.50: '+str(buckling[1])+ ' |eq 7.51: '+ \
                                             str(buckling[2])+' |7.52: '+str(buckling[3])+ '|eq 7.53: '+str(buckling[4])+\
                                             ' |z*: '+str(buckling[5])
                            elif obj_structure.get_side() == 's':
                                res_text = '|eq 7.19: '+str(buckling[0])+' |eq 7.54: '+str(buckling[1])+' |eq 7.55: '+ \
                                             str(buckling[2])+' |7.56: '+str(buckling[3])+ '|eq 7.57: '+str(buckling[4])+ \
                                             ' |z*: '+str(buckling[5])
                        self._result_canvas.create_text([x * 1, (y+10*dy) * 1],
                                                   text=res_text,font=self._text_size["Text 9 bold"],
                                                   anchor='nw',fill=color_buckling)
                elif self._new_buckling_slider.get() == 3:

                    self._result_canvas.create_text([x * 1, (y + 9 * dy) * 1],
                                                    text='Buckling results ANYstructure ML algorithm:',
                                                    font=self._text_size["Text 9 bold"], anchor='nw')
                    self._result_canvas.create_text([x * 1, (y + 10 * dy) * 1],
                                                    text='Buckling: ' + self._ML_classes[state['ML buckling class'][current_line]['buckling']],
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=state['ML buckling colors'][current_line]['buckling'])
                    self._result_canvas.create_text([x * 1, (y + 11 * dy) * 1],
                                                    text='Ultimate: ' +self._ML_classes[state['ML buckling class'][current_line]['ultimate']],
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw', fill=state['ML buckling colors'][current_line]['ultimate'])
                    if obj_structure.get_puls_sp_or_up() == 'SP':
                        csr = state['ML buckling class'][current_line]['CSR']
                        csr_str = ['Ok' if csr[0] == 1 else 'Not ok', 'Ok' if csr[1] == 1 else 'Not ok',
                                   'Ok' if csr[2] == 1 else 'Not ok', 'Ok' if csr[3] == 1 else 'Not ok']
                        self._result_canvas.create_text([x * 1, (y + 12.5 * dy) * 1],
                                                        text='CSR requirements (stiffener):  plate-'+ csr_str[0]+ ' web-'+
                                                             csr_str[1] + ' web/flange ratio-'+ csr_str[2] +
                                                             ' flange-'+ csr_str[3] ,
                                                        font=self._text_size["Text 9"],
                                                        anchor='nw',
                                                        fill=state['ML buckling colors'][current_line]['CSR requirement'])
                    else:
                        csr = state['ML buckling class'][current_line]['CSR']
                        csr_str = 'Ok' if csr[0] == 1 else 'Not ok'
                        self._result_canvas.create_text([x * 1, (y + 12.5 * dy) * 1],
                                                        text='CSR requirements (stiffener):  Plate slenderness -'+
                                                             csr_str,
                                                        font=self._text_size["Text 9"],
                                                        anchor='nw',
                                                        fill=state['ML buckling colors'][current_line]['CSR requirement'])


                # fatigue results

                self._result_canvas.create_text([x * 1, (y+14*dy) * 1],
                                                text='Fatigue results (DNVGL-RP-C203): ',
                                                font=self._text_size["Text 9 bold"], anchor='nw')

                if self._line_to_struc[current_line][2] != None:
                    if state['fatigue'][current_line]['damage'] is not None:
                        damage = state['fatigue'][current_line]['damage']
                        dff = state['fatigue'][current_line]['dff']
                        self._result_canvas.create_text([x * 1, (y + 15 * dy) * 1],
                                                        text='Total damage (DFF not included): '+str(round(damage,3)) +
                                                             '  |  With DFF = '+str(dff)+' --> Damage: '+
                                                             str(round(damage*dff,3)),
                                                        font=self._text_size["Text 9 bold"], anchor='nw',
                                                        fill=color_fatigue)
                    else:
                        self._result_canvas.create_text([x * 1, (y + 15 * dy) * 1],
                                                        text='Total damage: NO RESULTS ',
                                                        font=self._text_size["Text 9 bold"],
                                                        anchor='nw')
                else:
                    self._result_canvas.create_text([x * 1, (y + 15 * dy) * 1],
                                                    text='Total damage: NO RESULTS ',
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw')

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
                obj[1].need_recalc = True
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
                    self.logger(point=current_point, move_coords=(current_coords,[x_coord, y_coord])) #TODO
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
                        self._line_to_struc[line][0].set_span(dist(coord1,coord2))
                        self._line_to_struc[line][1].set_span(dist(coord1, coord2))
                        self._PULS_results.result_changed(line)
                        if self._line_to_struc[line][0].get_structure_type() not in ['GENERAL_INTERNAL_NONWT',
                                                                                                'FRAME']:
                            self._tank_dict = {}
                            self._main_grid.clear()
                            self._compartments_listbox.delete(0, 'end')

            for line, obj in self._line_to_struc.items():
                obj[1].need_recalc = True
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
                obj[1].need_recalc = True
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a line number.')

    def new_structure(self, event = None, pasted_structure = None, multi_return = None, toggle_multi = None,
                      suspend_recalc = False):
        '''
        This method maps the structure to the line when clicking "add structure to line" button.
        The result is put in a dictionary. Key is line name and value is the structure object.

        self_line_to_stuc
            [0] Structure class
            [1] calc scantling class instance
            [2] calc fatigue class instance
            [3] load class instance
            [4] load combinations result (currently not used)
        :return:
        '''

        if all([pasted_structure == None, multi_return == None]):
            if any([self._new_stf_spacing.get()==0, self._new_plate_thk.get()==0, self._new_stf_web_h.get()==0,
                    self._new_sft_web_t.get()==0]):
                mess = tk.messagebox.showwarning('No propertied defined', 'No properties is defined for the line!\n'
                                                                          'Define spacing, web height, web thickness etc.\n'
                                                                          'Either press button with stiffener or input'
                                                                          'manually.', type='ok')
                return

        if self._line_is_active or multi_return != None:
            # structure dictionary: name of line : [ 0.Structure class, 1.calc scantling class,
            # 2.calc fatigue class, 3.load object, 4.load combinations result ]
            if multi_return is not None:
                obj_dict = multi_return[1].get_structure_prop()
            elif toggle_multi is not None:
                obj_dict = toggle_multi
            elif pasted_structure == None:
                obj_dict = {'mat_yield': [self._new_material.get()*1e6, 'Pa'],
                            'mat_factor': [self._new_material_factor.get(), ''],
                            'span': [self._new_field_len.get(), 'm'],
                            'spacing': [self._new_stf_spacing.get()/1000, 'm'],
                            'plate_thk': [self._new_plate_thk.get()/1000, 'm'],
                            'stf_web_height': [self._new_stf_web_h.get()/1000, 'm'],
                            'stf_web_thk': [self._new_sft_web_t.get()/1000, 'm'],
                            'stf_flange_width': [self._new_stf_fl_w.get()/1000, 'm'],
                            'stf_flange_thk': [self._new_stf_fl_t.get()/1000, 'm'],
                            'structure_type': [self._new_stucture_type.get(), ''],
                            'stf_type': [self._new_stf_type.get(), ''],
                            'sigma_y1': [self._new_sigma_y1.get(), 'MPa'],
                            'sigma_y2': [self._new_sigma_y2.get(), 'MPa'],
                            'sigma_x': [self._new_sigma_x.get(), 'MPa'],
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
                            'puls stiffener end': [self._new_puls_stf_end_type.get(), ''],
                            'puls sp or up':  [self._new_puls_sp_or_up.get(), ''],
                            'puls up boundary': [self._new_puls_up_boundary.get(), ''],}
            else:
                obj_dict = pasted_structure.get_structure_prop()

            if self._active_line not in self._line_to_struc.keys():
                self._line_to_struc[self._active_line] = [None, None, None, [None], {}]
                self._line_to_struc[self._active_line][0] = Structure(obj_dict)
                self._sections = add_new_section(self._sections, struc.Section(obj_dict))
                self._line_to_struc[self._active_line][1] = CalcScantlings(obj_dict)
                self._line_to_struc[self._active_line][2] = None
                if self._line_to_struc[self._active_line][0].get_structure_type() not in \
                        self._structure_types['non-wt']:
                    self._tank_dict = {}
                    self._main_grid.clear()
                    self._compartments_listbox.delete(0, 'end')
            else:
                prev_type = self._line_to_struc[self._active_line][0].get_structure_type()
                prev_str_obj, prev_calc_obj = copy.deepcopy(self._line_to_struc[self._active_line][0]),\
                                              copy.deepcopy(self._line_to_struc[self._active_line][1])

                self._line_to_struc[self._active_line][0].set_main_properties(obj_dict)
                self._line_to_struc[self._active_line][1].set_main_properties(obj_dict)

                if self._new_scale_stresses.get() and prev_str_obj.get_tuple() != \
                        self._line_to_struc[self._active_line][0].get_tuple():
                    self._line_to_struc[self._active_line][0] = \
                        op.create_new_structure_obj(prev_str_obj, self._line_to_struc[self._active_line][0].get_tuple(),
                                                    fup=self._new_fup.get(), fdwn=self._new_fdwn.get())
                    self._line_to_struc[self._active_line][1] = \
                        op.create_new_calc_obj(prev_calc_obj,self._line_to_struc[self._active_line][1].get_tuple(),
                                               fup=self._new_fup.get(), fdwn=self._new_fdwn.get())[0]
                self._line_to_struc[self._active_line][1].need_recalc = True
                if self._line_to_struc[self._active_line][2] is not None:
                    self._line_to_struc[self._active_line][2].set_main_properties(obj_dict)
                if prev_type in self._structure_types['non-wt'] and obj_dict['structure_type'][0] in \
                                        self._structure_types['internals'] + self._structure_types['horizontal'] + \
                                self._structure_types['vertical']:
                    self._tank_dict = {}
                    self._main_grid.clear()
                    self._compartments_listbox.delete(0, 'end')
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
                obj[1].need_recalc = True
            state = self.update_frame()
            if state != None:
                self._weight_logger['new structure']['COG'].append(self.get_color_and_calc_state()['COG'])
                self._weight_logger['new structure']['weight'].append(self.get_color_and_calc_state()['Total weight'])
                self._weight_logger['new structure']['time'].append(time.time())
        self.get_unique_plates_and_beams()

    def option_meny_structure_type_trace(self, event):
        ''' Updating of the values in the structure type option menu. '''

        self._new_sigma_y1.set(self._default_stresses[self._new_stucture_type.get()][0])
        self._new_sigma_y2.set(self._default_stresses[self._new_stucture_type.get()][1])
        self._new_sigma_x.set(self._default_stresses[self._new_stucture_type.get()][2])
        self._new_tauxy.set(self._default_stresses[self._new_stucture_type.get()][3])

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
                data[0].get_section_modulus(), self.get_highest_pressure(line)['normal'])

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

    def calculate_one_load_combination(self, line_name, comb_name, load_condition):
        '''
        Creating load combination for ULS.
        Inserted into self._line_to_struc index = 4
        "dnva", "line12", "static_ballast_10m"
        #load combination dictionary (comb,line,load) : [stat - DoubleVar(), dyn - DoubleVar], on/off - IntVar()]
        :return:
        '''

        defined_loads = []
        for load_obj in self._line_to_struc[line_name][3]:
            if load_obj is not None:
                if load_obj.get_limit_state() != 'FLS':
                    defined_loads.append(load_obj)
        if self._tank_dict == {}:
            defined_tanks =  []
        else:
            defined_tanks = [['comp'+str(int(tank_num)), self._tank_dict['comp'+str(int(tank_num))]]
                     for tank_num in self.get_compartments_for_line_duplicates(line_name)]

        coord = (self.get_line_radial_mid(line_name), self.get_line_low_elevation(line_name))

        if load_condition not in ['tanktest','manual','slamming']:
            acc = (self._accelerations_dict['static'], self._accelerations_dict['dyn_'+str(load_condition)])
        else:
            acc = (self._accelerations_dict['static'], 0)

        load_factors_all = self._new_load_comb_dict

        line_name_obj = [line_name, self._line_to_struc[line_name][0]]

        if self._line_to_struc[line_name][0].get_structure_type() in ['', 'FRAME','GENERAL_INTERNAL_NONWT']:
            return [0, '']
        else:
            return_value = one_load_combination(line_name_obj, coord, defined_loads, load_condition,
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
            obj[1].need_recalc = True
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
                        if self._line_to_struc[line][0].get_structure_type() not in self._structure_types['non-wt']:
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
            self.new_structure(pasted_structure=self._line_to_struc[self.__copied_line_prop][0])

        if self._line_to_struc[self._active_line][0].get_structure_type() !=\
                self._line_to_struc[self.__copied_line_prop][0].get_structure_type():
            tk.messagebox.showerror('Paste error', 'Can only paste to same structure type. This is to avoid problems '
                                                   'with compartments not detecting changes to watertightness.')
            return
        else:
            self.new_structure(pasted_structure= self._line_to_struc[self.__copied_line_prop][0])

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
                obj[1].need_recalc = True
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
            properties = self._line_to_struc[line][0].get_structure_prop()
            self._new_material.set(round(properties['mat_yield'][0]/1e6,5))
            self._new_material_factor.set(properties['mat_factor'][0])
            self._new_field_len.set(round(properties['span'][0],5))
            self._new_stf_spacing.set(round(properties['spacing'][0]*1000,5))
            self._new_plate_thk.set(round(properties['plate_thk'][0]*1000,5))
            self._new_stf_web_h.set(round(properties['stf_web_height'][0]*1000,5))
            self._new_sft_web_t.set(round(properties['stf_web_thk'][0]*1000,5))
            self._new_stf_fl_w.set(round(properties['stf_flange_width'][0]*1000,5))
            self._new_stf_fl_t.set(round(properties['stf_flange_thk'][0]*1000,5))
            self._new_plate_kpp.set(properties['plate_kpp'][0])
            self._new_stf_kps.set(properties['stf_kps'][0])
            self._new_sigma_y1.set(round(properties['sigma_y1'][0],1))
            self._new_sigma_y2.set(round(properties['sigma_y2'][0],1))
            self._new_sigma_x.set(round(properties['sigma_x'][0],1))
            self._new_tauxy.set(round(properties['tau_xy'][0],1))
            self._new_stucture_type.set(properties['structure_type'][0])
            self._new_stf_type.set(properties['stf_type'][0])
            self._new_stf_km1.set(properties['stf_km1'][0])
            self._new_stf_km2.set(properties['stf_km2'][0])
            self._new_stf_km3.set(properties['stf_km3'][0])
            try:
                self._new_pressure_side.set(properties['press_side'][0])
            except KeyError:
                self._new_pressure_side.set('p')
            self._new_zstar_optimization.set(properties['zstar_optimization'][0])
            self._new_puls_method.set(properties['puls buckling method'][0])
            self._new_puls_panel_boundary.set(properties['puls boundary'][0])
            self._new_puls_stf_end_type.set(properties['puls stiffener end'][0])
            self._new_puls_sp_or_up.set(properties['puls sp or up'][0])
            self._new_puls_up_boundary.set(properties['puls up boundary'][0])

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
                                                                                        0].get_structure_type())
                    if fls_exist[exist_i] and load.get_load_condition() == 'ballast':
                        pressures['p_ext']['ballast'] = load.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                                    accelerations[1],
                                                                                    self._line_to_struc[line][
                                                                                        0].get_structure_type())

                    if fls_exist[exist_i] and load.get_load_condition() == 'part':
                        pressures['p_ext']['part'] = load.get_calculated_pressure(self.get_pressures_calc_coord(line),
                                                                                    accelerations[2],
                                                                                    self._line_to_struc[line][
                                                                                        0].get_structure_type())

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
                this_beam = data[0].get_beam_string()
                this_plate = data[0].get_pl_thk()*1000
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
                        if self._line_to_struc[line][1].get_structure_type() == self._new_stucture_type.get():
                            self._multiselect_lines.append(line)
                    else:
                        self._multiselect_lines.append(line)
        else:
            tk.messagebox.showinfo('CTRL-A and CTRL-T', 'CTRL-A and CTRL-T is used to select all lines \n' 
                                                        'with the intension to change a single variable in all lines.\n'
                                                        'Press the Toggle select multiple button.')
        self.update_frame()

    def mouse_scroll(self,event):
        self._canvas_scale +=  event.delta/50
        self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale
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
            try:
                self.gui_load_combinations(self._combination_slider.get())
            except (KeyError, AttributeError):
                pass

    def button_1_click_comp_box(self,event):
        '''
        Action when clicking the compartment box.
        :param event:
        :return:
        '''
        self._selected_tank.config(text='',font = self._text_size['Text 12 bold'],fg='red')
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
        pt_canvas = tk.Canvas(self._pt_frame,height=100,width=100,background='gray60')
        pt_canvas.place(relx=0, rely=0)
        pt_canvas.create_oval(45,45,55,55,fill='red')
        new_left_br = tk.IntVar()
        new_right_br = tk.IntVar()
        new_upper_br = tk.IntVar()
        new_lower_br = tk.IntVar()
        wid = 5
        ent_left = tk.Entry(self._pt_frame,textvariable=new_left_br, width=wid, bg = self._entry_color,
                            fg = self._entry_text_color)
        ent_right = tk.Entry(self._pt_frame, textvariable=new_right_br, width=wid, bg = self._entry_color,
                             fg = self._entry_text_color)
        ent_upper = tk.Entry(self._pt_frame, textvariable=new_upper_br, width=wid, bg = self._entry_color,
                             fg = self._entry_text_color)
        ent_lower = tk.Entry(self._pt_frame, textvariable=new_lower_br, width=wid, bg = self._entry_color,
                             fg = self._entry_text_color)
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
        for key, value in self._line_to_struc.items():
            structure_properties[key] = value[0].get_structure_prop()

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
        export_all['project information'] = self._new_project_infomation.get()
        export_all['point_dict'] = self._point_dict
        export_all['line_dict'] = self._line_dict
        export_all['structure_properties'] = structure_properties
        export_all['load_properties'] = load_properties
        export_all['accelerations_dict'] = self._accelerations_dict
        export_all['load_combinations'] = load_combiantions
        export_all['tank_properties'] = tank_properties
        export_all['fatigue_properties'] = fatigue_properties
        export_all['buckling type'] = self._new_buckling_slider.get()

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
            self._new_project_infomation.set(imported['project information'])
        else:
            self._new_project_infomation.set('No project information provided. Input here.')

        if 'shifting' in imported.keys():
            self._new_shifted_coords.set(imported['shifting']['shifted checked'])
            self._new_shift_viz_coord_hor.set(imported['shifting']['shift hor'])
            self._new_shift_viz_coord_ver.set(imported['shifting']['shift ver'])
        else:
            pass

        self._point_dict = imported['point_dict']
        self._line_dict = imported['line_dict']
        struc_prop = imported['structure_properties']

        for line, lines_prop in struc_prop.items():

            self._line_to_struc[line] = [None, None, None, [], {}, [True, 'green']]
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
                lines_prop['puls stiffener end'] = [self._new_puls_stf_end_type.get(), '']
            if 'puls sp or up' not in lines_prop.keys():
                lines_prop['puls sp or up'] = [self._new_puls_sp_or_up.get(), '']
            if 'puls up boundary' not in lines_prop.keys():
                lines_prop['puls up boundary'] = [self._new_puls_up_boundary.get(), '']
            if 'mat_factor' not in lines_prop.keys():
                lines_prop['mat_factor'] = [self._new_material_factor.get(), '']

            self._line_to_struc[line][0] = Structure(lines_prop)
            self._line_to_struc[line][1] = CalcScantlings(lines_prop)
            if imported['fatigue_properties'][line] is not None:
                self._line_to_struc[line][2] = CalcFatigue(lines_prop, imported['fatigue_properties'][line])
            else:
                self._line_to_struc[line][2] = None

            #  Recording sections.
            self._sections = add_new_section(self._sections, struc.Section(lines_prop))

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
            self.toggle_puls_run()

        # Setting the scale of the canvas
        points = self._point_dict
        highest_y = max([coord[1] for coord in points.values()])
        highest_x = max([coord[0] for coord in points.values()])
        self._canvas_scale = min(800 / highest_y, 800 / highest_x, 15)

        if 'buckling type' in imported.keys():
            self._new_buckling_slider.set(imported['buckling type'])
            self._buckling_slider.set(imported['buckling type'])

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
            scroll_bar = tk.Scrollbar(text_m)
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

    def on_open_structure_window(self):
        '''
        Opens the window to create structure.
        :return:
        '''
        if self._line_is_active:

            top_opt = tk.Toplevel(self._parent, background=self._general_color)
            struc.CreateStructureWindow(top_opt, self)

        else:
            messagebox.showinfo(title='Select line',message='You must select a line')

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
        if self._puls_information_button.config('relief')[-1] == 'sunken':
            self.text_widget.forget()
            self._puls_information_button.config(relief='raised')
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
        scroll_bar = tk.Scrollbar(text_m)
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
                self._line_to_struc[key][1].need_recalc = True  # All lines need recalculations.

            for main_line in self._line_dict.keys():
                for load_obj, load_line in self._load_dict.values():
                    if main_line in self._line_to_struc.keys():
                        if returned_loads:
                            if load_obj.__str__() != temp_load[load_obj.get_name()][0].__str__() and main_line in \
                                    load_line+temp_load[load_obj.get_name()][1]:
                                # The load has changed for this line.
                                # TODO double check this.
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

        self.new_structure(multi_return = returned_object[0:3])
        # self._line_to_struc[self._active_line][0]=returned_objects[0]
        # self._line_to_struc[self._active_line][1]=returned_objects[1]
        # self._line_to_struc[self._active_line][1].need_recalc = True
        # self.set_selected_variables(self._active_line)
        # if returned_objects[2] is not None:
        #     self._line_to_struc[self._active_line][2] = CalcFatigue(returned_objects[0].get_structure_prop(),
        #                                                             returned_objects[2])
        # self.new_structure()
        self.update_frame()

    def on_close_opt_multiple_window(self, returned_objects):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''

        for line,all_objs in returned_objects.items():
            self._active_line = line
            #self._line_to_struc[line][1].need_recalc = True
            self.new_structure(multi_return= all_objs[0:3])
        self.update_frame()

    def on_close_structure_window(self,returned_structure):
        '''
        Setting the input field to specified properties
        :param returned_structure:
        :return:
        '''
        self._new_stf_spacing.set(returned_structure[0])
        self._new_plate_thk.set(returned_structure[1])
        self._new_stf_web_h.set(returned_structure[2])
        self._new_sft_web_t.set(returned_structure[3])
        self._new_stf_fl_w.set(returned_structure[4])
        self._new_stf_fl_t.set(returned_structure[5])
        self._new_stf_type.set(returned_structure[6])

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
        self._new_sigma_x.set(returned_stress_and_km[2])
        self._new_tauxy.set(returned_stress_and_km[3])
        self._new_stf_km1.set(returned_stress_and_km[4])
        self._new_stf_km1.set(returned_stress_and_km[5])
        self._new_stf_km1.set(returned_stress_and_km[6])
        self._new_plate_kpp.set(returned_stress_and_km[7])
        self._new_stf_kps.set(returned_stress_and_km[8])
        self._new_stucture_type.set(returned_stress_and_km[9],)

    def on_close_fatigue_window(self,returned_fatigue_prop: dict):
        '''
        Sets the returned fatigue properteis.
        :param returned_stress_and_km:
        :return:
        '''
        if self._line_to_struc[self._active_line][2] == None:
            self._line_to_struc[self._active_line][2] = CalcFatigue(self._line_to_struc[self._active_line][1]
                                                                    .get_structure_prop(),
                                                                         returned_fatigue_prop)
        else:
            self._line_to_struc[self._active_line][2].set_fatigue_properties(returned_fatigue_prop)

        self._line_to_struc[self._active_line][1].need_recalc = True
        if self.__returned_load_data is not None:
            map(self.on_close_load_window, self.__returned_load_data)

        # adding values to the line dictionary. resetting first.
        for key, value in self._line_to_struc.items():
            if self._line_to_struc[key][2] is not None:
                self._line_to_struc[key][2].set_commmon_properties(returned_fatigue_prop)
            self._line_to_struc[key][1].need_recalc = True  # All lines need recalculations.

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

    def open_documentation(self):
        ''' Open the documentation pdf. '''
        if os.path.isfile('ANYstructure_documentation.pdf'):
            os.startfile('ANYstructure_documentation.pdf')
        else:
            os.startfile(self._root_dir + '/' + 'ANYstructure_documentation.pdf')

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
    width = int(root.winfo_screenwidth()*1)
    height = int(root.winfo_screenheight()*1)
    root.geometry(f'{width}x{height}')
    my_app = Application(root)
    root.mainloop()
    #Application(None).openfile(r'C:\Github\ANYstructure\ANYstructure\ship_section_example.txt', alone=True)