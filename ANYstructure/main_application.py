# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import json
from ANYstructure.calc_loads import *
from ANYstructure.calc_structure import *
import ANYstructure.load_window as load_window
import ANYstructure.make_grid_numpy as grid
import ANYstructure.grid_window as grid_window
from ANYstructure.helper import *
import math, decimal
import ANYstructure.optimize_window as opw
import ANYstructure.optimize_multiple_window as opwmult
import ANYstructure.optimize_geometry as optgeo
import ANYstructure.pl_stf_window as struc
import ANYstructure.stresses_window as stress
import ANYstructure.fatigue_window as fatigue
from _tkinter import TclError
import multiprocessing
from ANYstructure.report_generator import LetterMaker
import os.path
import ctypes


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

        # If the resolution of the screen is below 2000, items are multiplied by global_shrink.
        if parent.winfo_screenwidth() < 2000:
            self._global_shrink = 0.96
        else:
            self._global_shrink = 1

        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        # Main frame for the application
        self._main_fr = tk.Frame(parent, height=int(990*self._global_shrink), width=int(1920*self._global_shrink))
        self._main_fr.pack()

        # Top open/save/new
        menu = tk.Menu(parent)
        parent.config(menu=menu)
        # menu, canvas, etc.
        sub_menu = tk.Menu(menu)
        menu.add_cascade(label='File', menu=sub_menu)
        sub_menu.add_command(label='New project', command=self.reset)
        sub_menu.add_command(label='Save project', command=self.savefile)
        sub_menu.add_command(label='Open project', command=self.openfile)

        undo_redo = tk.Menu(menu)
        menu.add_cascade(label='Geometry', menu=undo_redo)
        undo_redo.add_command(label='Undo geometry action (CTRL-Z)', command=self.undo)
        #undo_redo.add_command(label='Redo geometry action (CTRL-Y)', command=self.redo)
        undo_redo.add_command(label='Copy selected point (CTRL-C)', command=self.copy_point)
        undo_redo.add_command(label='Move selected point (CTRL-M)', command=self.move_point)
        undo_redo.add_command(label='New line (right click two points) (CTRL-Q)', command=self.new_line)
        undo_redo.add_command(label='Assign structure properties (from clicked line (CTRL-S)',
                              command=self.new_structure)
        sub_help = tk.Menu(menu)
        menu.add_cascade(label='Help', menu = sub_help)
        sub_help.add_command(label = 'Open documentation', command = self.open_documentation)
        sub_help.add_command(label = 'Open example file', command = self.open_example)
        sub_help.add_command(label='About ANYstructure', command=self.open_about)

        sub_report = tk.Menu(menu)
        menu.add_cascade(label = 'Reporting', menu = sub_report)
        sub_report.add_command(label = 'Generate PDF report', command = self.report_generate)

        base_canvas_dim = [1000,720]  #do not modify this, sets the "orignal" canvas dimensions.
        self._canvas_dim = [int(base_canvas_dim[0] *self._global_shrink),
                           int(base_canvas_dim[1] *self._global_shrink)]
        self._canvas_base_origo = [50, base_canvas_dim[1] - 50] # bottom left location of the canvas, (0,0)
        self._canvas_draw_origo = list(self._canvas_base_origo)
        self._previous_drag_mouse = list(self._canvas_draw_origo)

        # Setting the fonts for all items in the application.
        self._text_size = {'Text 14 bold':'Verdana '+str(int(14*self._global_shrink))+' bold',
                           'Text 16 bold': 'Verdana ' + str(int(16 * self._global_shrink)) + ' bold',
                           'Text 18 bold': 'Verdana ' + str(int(18 * self._global_shrink)) + ' bold',
                          'Text 12 bold': 'Verdana ' + str(int(12 * self._global_shrink)) + ' bold',
                          'Text 10 bold':'Verdana '+str(int(10*self._global_shrink))+' bold',
                          'Text 9 bold': 'Verdana ' + str(int(9 * self._global_shrink)) + ' bold',
                          'Text 8 bold': 'Verdana ' + str(int(8 * self._global_shrink)) + ' bold',
                          'Text 8': 'Verdana ' + str(int(8 * self._global_shrink)),
                          'Text 9': 'Verdana ' + str(int(8 * self._global_shrink)),
                          'Text 7': 'Verdana ' + str(int(7 * self._global_shrink)),
                          'Text 7 bold': 'Verdana ' + str(int(7 * self._global_shrink)) + ' bold'}

        self._canvas_scale = 20 # Used for slider and can change
        self._base_scale_factor = 10 # Used for grid and will not change

        # Creating the various canvas next.
        self._main_canvas = tk.Canvas(self._main_fr, height=self._canvas_dim[1], width=self._canvas_dim[0]
                                     , background='azure', relief = 'groove', borderwidth=2)
        self._prop_canvas = tk.Canvas(self._main_fr, height=int(230*self._global_shrink),
                                     width=int(self._canvas_dim[0]*0.72*(self._global_shrink+(1-self._global_shrink)/2)),
                                     background='DarkSeaGreen1', relief = 'groove', borderwidth=2)
        self._result_canvas = tk.Canvas(self._main_fr, height=int(230*self._global_shrink),
                                       width=int(self._canvas_dim[0]*0.68*(self._global_shrink+(1-self._global_shrink)/2)),
                                       background='DarkSeaGreen1', relief = 'groove', borderwidth=2)
        x_canvas_place = int(500*self._global_shrink) #
        self._main_canvas.place(x=x_canvas_place, y=20)
        self._prop_canvas.place(x=x_canvas_place, y=self._canvas_dim[1]+30)
        self._result_canvas.place(x=x_canvas_place+self._canvas_dim[0]*0.73*(self._global_shrink+(1-self._global_shrink)/2),
                                 y=self._canvas_dim[1]+30)

        # These frames are just visual separations in the GUI.
        fr_width = int(x_canvas_place * self._global_shrink)
        tk.Frame(self._main_fr, width=fr_width, height=5, bg="black", colormap="new")\
            .place(x=0, y=50* self._global_shrink)
        tk.Frame(self._main_fr, width=fr_width, height=5, bg="black", colormap="new")\
            .place(x=1505*self._global_shrink,y=50 * self._global_shrink)
        tk.Frame(self._main_fr, width=fr_width, height=5, bg="azure", colormap="new")\
            .place(x=0, y=160* self._global_shrink)
        tk.Frame(self._main_fr, width=fr_width, height=5, bg="azure", colormap="new")\
            .place(x=0, y=260* self._global_shrink)
        tk.Frame(self._main_fr, width=fr_width, height=5, bg="black", colormap="new")\
            .place(x=0, y=330* self._global_shrink)
        tk.Frame(self._main_fr, width=fr_width, height=5, bg="black", colormap="new")\
            .place(x=0, y=675* self._global_shrink)

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
        self._new_load_comb_dict = {} # Load combination dict.(comb,line,load) : [DoubleVar(), DoubleVar], IntVar()]
        #
        # -------------------------------------------------------------------------------------------------------------
        #
        self._pending_grid_draw = {}  # Saving lines that shall be transferred to the calculation grid
        # Load combinations definition used in method gui_load_combinations
        # These are created and destroyed and is not permanent in the application.
        self._lc_comb_created,self._comp_comb_created,self._manual_created, self._info_created = [],[],[], []
        self._state_logger = dict()

        # The next dictionaries feed various infomation to the application
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,0]} # DNV  loads factors
        self._accelerations_dict = {'static':9.81, 'dyn_loaded':0, 'dyn_ballast':0} # Vertical acclerations
        self._load_conditions = ['loaded','ballast','tanktest', 'part','slamming'] # Should not be modified. Load conditions.
        self._tank_options = ['crude_oil', 'diesel', 'slop', 'ballast'] # Should not be modified.
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

        self._p1_p2_select = False
        self._line_is_active = False # True when a line is clicked
        self._active_line = '' # Name of the clicked point
        self._point_is_active = False # True when a point is clicked
        self._active_point = '' # Name of the clicked point
        self.controls() # Function to activate mouse clicks
        self._line_point_to_point_string = [] # This one ensures that a line is not created on top of a line

        # Initsializing the calculation grid used for tank definition
        self._grid_dimensions = [self._canvas_base_origo[1] + 1, base_canvas_dim[0] - self._canvas_base_origo[0] + 1]
        self._main_grid  = grid.Grid(self._grid_dimensions[0], self._grid_dimensions[1])
        self._grid_calc = None

        # These sets the location where entries are placed.
        ent_x = 180*self._global_shrink
        delta_y = 25*self._global_shrink
        delta_x = 50*self._global_shrink

        # --- slider (used to zoom) ----
        tk.Label(self._main_fr, text='Slide to zoom (or use mouse wheel)').place(x=ent_x+delta_x*6.5, y=delta_y)
        self._slider = tk.Scale(self._main_fr,from_=60,to = 1, command=self.slider_used)
        self._slider.set(self._canvas_scale)
        self._slider.place(x=ent_x+delta_x*6.5, y= delta_y*2)

        # --- main header image ---
        try:
            img_file_name = 'img_title.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            label = tk.Label(self._main_fr,image=photo)
            label.image = photo  # keep a reference!
            label.place(x=2, y=10)
        except TclError: # If the image is not located in the folder
            label = tk.Label(self._main_fr, text='DNVGL-OS-C101 based calculations')
            label.place(x=10, y=10)


        # ----------------------INITIATION OF THE SMALLER PARTS OF THE GUI STARTS HERE--------------------------
        # --- point input/output ----
        self._new_point_x = tk.DoubleVar()
        self._new_point_y = tk.DoubleVar()
        self._new_point_fix = tk.StringVar()
        point_start = 100* self._global_shrink
        ent_width = 6  # width of entries

        tk.Label(self._main_fr, text='Input point coordinates [mm]', font=self._text_size['Text 9 bold'])\
            .place(x=10, y=point_start - 30*self._global_shrink)
        tk.Label(self._main_fr, text='Point x (horizontal) [mm]:',font="Text 9").place(x=10, y=point_start)
        tk.Label(self._main_fr, text='Point y (vertical)   [mm]:',font="Text 9").place(x=10, y=point_start + delta_y)

        tk.Entry(self._main_fr, textvariable=self._new_point_x, width = int(ent_width * self._global_shrink))\
            .place(x=ent_x, y=point_start)
        tk.Entry(self._main_fr, textvariable=self._new_point_y, width = int(ent_width * self._global_shrink))\
            .place(x=ent_x, y=point_start + delta_y)
        tk.Button(self._main_fr, text='Add point (coords)', command=self.new_point, width = 18,bg = 'green', fg = 'yellow',
                  font = self._text_size['Text 9 bold']).place(x=ent_x + 2 * delta_x, y=point_start-1.6*delta_y)
        tk.Button(self._main_fr, text='Copy point (relative)', command=self.copy_point, width = 18,bg = 'white', fg = 'black',
                  font = self._text_size['Text 9 bold']).place(x=ent_x + 2 * delta_x, y=point_start-0.3*delta_y)
        tk.Button(self._main_fr, text='Move point (relative)', command=self.move_point, width = 18,bg = 'white', fg = 'black',
                  font = self._text_size['Text 9 bold']).place(x=ent_x + 2 * delta_x, y=point_start+1*delta_y)

        # --- line input/output ---
        self._new_line_p1 = tk.IntVar()
        self._new_line_p2 = tk.IntVar()
        line_start = 200* self._global_shrink
        tk.Label(self._main_fr, text='Input line from "point number" to "point number"',
                 font=self._text_size['Text 9 bold']).place(x=10, y=line_start - 30*self._global_shrink)
        tk.Label(self._main_fr, text='From point number:',font="Text 9").place(x=10, y=line_start)
        tk.Label(self._main_fr, text='To point number:',font="Text 9").place(x=10, y=line_start + delta_y)

        tk.Entry(self._main_fr, textvariable=self._new_line_p1, width=int(ent_width * self._global_shrink))\
            .place(x=ent_x, y=line_start)
        tk.Entry(self._main_fr, textvariable=self._new_line_p2, width=int(ent_width * self._global_shrink))\
            .place(x=ent_x, y=line_start + delta_y)
        tk.Button(self._main_fr, text='Add line', command=self.new_line, width = 10,bg = 'green', fg = 'yellow',
                  font = self._text_size['Text 9 bold']).place(x=ent_x+2*delta_x, y=line_start)

        # --- delete points and lines ---
        self._new_delete_line = tk.IntVar()
        self._new_delete_point = tk.IntVar()
        del_start = 295* self._global_shrink
        tk.Label(self._main_fr, text='Delete lines and points (input line or point number)',
                 font=self._text_size['Text 9 bold']).place(x=10, y=del_start - 30*self._global_shrink)
        self._ent_delete_line = tk.Entry(self._main_fr, textvariable=self._new_delete_line,
                                        width=int(ent_width * self._global_shrink))
        self._ent_delete_line.place(x=10, y=del_start)
        self._ent_delete_point = tk.Entry(self._main_fr, textvariable=self._new_delete_point,
                                         width=int(ent_width * self._global_shrink))
        self._ent_delete_point.place(x=ent_x, y=del_start)

        tk.Button(self._main_fr, text='Delete line',bg='green', fg='yellow',
                                         font=self._text_size['Text 9 bold'],command=self.delete_line,
                                         width = int(9*self._global_shrink)).place(x=ent_x-delta_x*2, y=del_start)

        tk.Button(self._main_fr, text='Delete point',bg='green', fg='yellow',
                                          font=self._text_size['Text 9 bold'],command=self.delete_point,
                                          width = int(11*self._global_shrink)).place(x=ent_x+2*delta_x, y=del_start)

        # --- structure type information ---
        prop_vert_start = 370* self._global_shrink
        types_start = 10
        tk.Label(self._main_fr, text='Structural and calculation properties input below:',
                 font=self._text_size['Text 9 bold']).place(x=10, y=prop_vert_start-1.2*delta_y)
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
                                                               '\n General (WT) (90/90/40/5):           GENERAL_INTERNAL_WT'
                                                               '\n General (NONWT) (70/70/30/3):        GENERAL_INTERNAL_NONWT'
                                                               '\n Side shell slamming (100/100/50/20): SSS '
                                                               '\n Internal 1 MPa wt (1/1/1/1):         INTERNAL_1_MPA '
                                                               '\n Internal low stress wt (40/40/20/5): INTERNAL_LOW_STRESS_WT ')

        tk.Button(self._main_fr,text='Show structure types',command=show_message,bg='grey',
                                font=self._text_size['Text 8']).place(x=types_start,y=prop_vert_start+10*delta_y)

        tk.Label(self._main_fr, text='Select structure type ->', font=self._text_size['Text 8'])\
            .place(x=100, y=prop_vert_start + 8 * delta_y)
        self.add_stucture = tk.Button(self._main_fr, text='Add structure to line', command=self.new_structure,
                                      font = self._text_size['Text 8 bold'], fg = 'yellow', bg = 'green',
                                      width = 18, height = 2)
        self.add_stucture.place(x=types_start+6*delta_x, y=prop_vert_start+delta_y*10+10)

        # --- main variable to define the structural properties ---
        self._new_material = tk.DoubleVar()
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

        # Setting default values to tkinter variables
        self._new_sigma_y1.set(80)
        self._new_sigma_y2.set(80)
        self._new_sigma_x.set(50)
        self._new_stf_km1.set(12)
        self._new_stf_km2.set(24)
        self._new_stf_km3.set(12)
        self._new_stf_kps.set(1)
        self._new_plate_kpp.set(1)
        self._new_material.set(355)
        self._new_stucture_type.set('GENERAL_INTERNAL_WT')
        self.option_meny_structure_type_trace(event='GENERAL_INTERNAL_WT')
        self._new_stf_type.set('T')
        self._new_pressure_side.set('p')

        # --- main entries and labels to define the structural properties ---
        ent_width = 12 #width of entries
        tk.Label(self._main_fr, text='Material yield [MPa]', font = self._text_size['Text 8'])\
            .place(x=100, y=prop_vert_start+ 7 * delta_y)

        self._ent_mat = tk.Entry(self._main_fr, textvariable=self._new_material, width = int(ent_width*self._global_shrink))
        self._ent_field_len = tk.Entry(self._main_fr, textvariable=self._new_field_len,
                                      width = int(5*self._global_shrink))
        self._ent_stf_spacing = tk.Entry(self._main_fr, textvariable=self._new_stf_spacing,
                                        width = int(5*self._global_shrink))
        self._ent_plate_thk = tk.Entry(self._main_fr, textvariable=self._new_plate_thk,
                                      width = int(5*self._global_shrink))
        self._ent_stf_web_h = tk.Entry(self._main_fr, textvariable=self._new_stf_web_h,
                                      width = int(5*self._global_shrink))
        self._ent_stf_web_t = tk.Entry(self._main_fr, textvariable=self._new_sft_web_t,
                                      width = int(5*self._global_shrink))
        self._ent_stf_fl_w = tk.Entry(self._main_fr, textvariable=self._new_stf_fl_w,
                                     width = int(5*self._global_shrink))
        self._ent_str_fl_t = tk.Entry(self._main_fr, textvariable=self._new_stf_fl_t,
                                     width = int(5*self._global_shrink))

        tk.Label(self._main_fr,text='kpp').place(x=10+2*delta_x, y=prop_vert_start + 2.5 * delta_y)
        tk.Label(self._main_fr, text='kps').place(x=10 + 3 * delta_x, y=prop_vert_start + 2.5 * delta_y)
        tk.Label(self._main_fr, text='km1').place(x=10 + 4 * delta_x, y=prop_vert_start + 2.5 * delta_y)
        tk.Label(self._main_fr, text='km2').place(x=10 + 5 * delta_x, y=prop_vert_start + 2.5 * delta_y)
        tk.Label(self._main_fr, text='k3').place(x=10 + 6 * delta_x, y=prop_vert_start + 2.5 * delta_y)


        self._ent_plate_kpp = tk.Entry(self._main_fr, textvariable=self._new_plate_kpp, width = int(5*self._global_shrink))
        self._ent_plate_kps = tk.Entry(self._main_fr, textvariable=self._new_stf_kps, width = int(5*self._global_shrink))
        self._ent_stf_km1 = tk.Entry(self._main_fr, textvariable=self._new_stf_km1, width = int(5*self._global_shrink))
        self._ent_stf_km2 = tk.Entry(self._main_fr, textvariable=self._new_stf_km2, width = int(5*self._global_shrink))
        self._ent_stf_km3 = tk.Entry(self._main_fr, textvariable=self._new_stf_km3, width = int(5*self._global_shrink))
        self._ent_pressure_side = tk.Entry(self._main_fr, textvariable=self._new_pressure_side,
                                          width=int(5 * self._global_shrink))

        tk.Label(self._main_fr, text='sig_y1').place(x=10 + 2 * delta_x, y=prop_vert_start + 4.5 * delta_y)
        tk.Label(self._main_fr, text='sig_y2').place(x=10 + 3 * delta_x, y=prop_vert_start + 4.5 * delta_y)
        tk.Label(self._main_fr, text='sig_x').place(x=10 + 4 * delta_x, y=prop_vert_start + 4.5 * delta_y)
        tk.Label(self._main_fr, text='tau_y1').place(x=10 + 5 * delta_x, y=prop_vert_start + 4.5 * delta_y)
        tk.Label(self._main_fr, text='stf type').place(x=10 + 6 * delta_x, y=prop_vert_start + 4.5 * delta_y)
        tk.Label(self._main_fr, text='pressure side').place(x=10 + 7.5 * delta_x, y=prop_vert_start + 4.5 * delta_y)

        self._ent_sigma_y1= tk.Entry(self._main_fr, textvariable=self._new_sigma_y1, width = int(7*self._global_shrink))
        self._ent_sigma_y2 = tk.Entry(self._main_fr, textvariable=self._new_sigma_y2, width=int(7*self._global_shrink))
        self._ent_sigma_x = tk.Entry(self._main_fr, textvariable=self._new_sigma_x, width=int(7*self._global_shrink))
        self._ent_tauxy = tk.Entry(self._main_fr, textvariable=self._new_tauxy, width=int(7*self._global_shrink))
        self._ent_stf_type = tk.Entry(self._main_fr, textvariable=self._new_stf_type, width=int(7*self._global_shrink))
        self._ent_structure_type = tk.OptionMenu(self._main_fr, self._new_stucture_type,
                                                 command = self.option_meny_structure_type_trace, *self._options_type)


        loc_y = -0.2
        tk.Label(self._main_fr, text='span',).place(x=10 + 2 * delta_x, y=prop_vert_start +loc_y * delta_y)
        tk.Label(self._main_fr, text='s').place(x=10 + 3*delta_x, y=prop_vert_start+loc_y * delta_y)
        tk.Label(self._main_fr, text='pl_thk').place(x=10 + 4*delta_x, y=prop_vert_start +loc_y  * delta_y)
        tk.Label(self._main_fr, text='web_h').place(x=10 + 5*delta_x, y=prop_vert_start +loc_y * delta_y)
        tk.Label(self._main_fr, text='web_thk').place(x=10 + 6*delta_x, y=prop_vert_start+loc_y * delta_y)
        tk.Label(self._main_fr, text='fl_w').place(x=10 + 7*delta_x, y=prop_vert_start + loc_y  * delta_y)
        tk.Label(self._main_fr, text='fl_thk').place(x=10 + 8*delta_x, y=prop_vert_start + loc_y  * delta_y)

        loc_y = 0.8
        self._ent_field_len.place(x=10 + 2*delta_x, y=prop_vert_start + loc_y * delta_y)
        self._ent_stf_spacing.place(x=10 + 3*delta_x, y=prop_vert_start + loc_y  * delta_y)
        self._ent_plate_thk.place(x=10 + 4*delta_x, y=prop_vert_start + loc_y  * delta_y)
        self._ent_stf_web_h.place(x=10 + 5*delta_x, y=prop_vert_start + loc_y  * delta_y)
        self._ent_stf_web_t.place(x=10 + 6*delta_x, y=prop_vert_start + loc_y  * delta_y)
        self._ent_stf_fl_w.place(x=10 + 7*delta_x, y=prop_vert_start + loc_y  * delta_y)
        self._ent_str_fl_t.place(x=10 + 8*delta_x, y=prop_vert_start + loc_y  * delta_y)
        loc_y = 1.7
        tk.Label(self._main_fr, text='[m]').place(x=10 + 2 * delta_x, y=prop_vert_start + loc_y * delta_y)
        tk.Label(self._main_fr, text='[mm]').place(x=10 + 3*delta_x, y=prop_vert_start + loc_y * delta_y)
        tk.Label(self._main_fr, text='[mm]').place(x=10 + 4*delta_x, y=prop_vert_start + loc_y * delta_y)
        tk.Label(self._main_fr, text='[mm]').place(x=10 + 5*delta_x, y=prop_vert_start + loc_y * delta_y)
        tk.Label(self._main_fr, text='[mm]').place(x=10 + 6*delta_x, y=prop_vert_start + loc_y * delta_y)
        tk.Label(self._main_fr, text='[mm]').place(x=10 + 7*delta_x, y=prop_vert_start + loc_y * delta_y)
        tk.Label(self._main_fr, text='[mm]').place(x=10 + 8*delta_x, y=prop_vert_start + loc_y * delta_y)

        self._ent_mat.place(x=delta_x*6 , y=prop_vert_start + 7 * delta_y)
        self._ent_plate_kpp.place(x=10+2*delta_x, y=prop_vert_start + 3.5 * delta_y)
        self._ent_plate_kps.place(x=10+3*delta_x, y=prop_vert_start + 3.5 * delta_y)
        self._ent_stf_km1.place(x=10+4*delta_x, y=prop_vert_start + 3.5 * delta_y)
        self._ent_stf_km2.place(x=10+5*delta_x, y=prop_vert_start + 3.5 * delta_y)
        self._ent_stf_km3.place(x=10+6*delta_x, y=prop_vert_start + 3.5 * delta_y)
        self._ent_sigma_y1.place(x=10+2*delta_x, y=prop_vert_start + 5.5 * delta_y)
        self._ent_sigma_y2.place(x=10+3*delta_x, y=prop_vert_start + 5.5 * delta_y)
        self._ent_sigma_x.place(x=10+4*delta_x, y=prop_vert_start + 5.5 * delta_y)
        self._ent_tauxy.place(x=10+5*delta_x, y=prop_vert_start + 5.5 * delta_y)
        self._ent_stf_type.place(x=10+6*delta_x, y=prop_vert_start + 5.5 * delta_y)
        self._ent_structure_type.place(x=ent_x+delta_x*1.9, y=prop_vert_start +8*delta_y, width = ent_width*6)
        self._ent_structure_type.place_configure(width=int(210*self._global_shrink))

        self._structure_types_label = \
            tk.Label(textvariable = self._new_stucture_type_label, font = self._text_size['Text 8'], fg= 'red')\
                .place(x=ent_x+delta_x*1.9, y=prop_vert_start +9.4*delta_y)

        self._ent_pressure_side.place(x=10 + 7.6 * delta_x, y=prop_vert_start + 5.5 * delta_y)

        try:
            img_file_name = 'img_stf_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            stf_button = tk.Button(self._main_fr,image = photo,command=self.on_open_structure_window)
            stf_button.image = photo
            stf_button.place(x=10,y=prop_vert_start)
        except TclError:
            tk.Button(self._main_fr, text='STF.', command=self.on_open_structure_window).place(x=10,y=prop_vert_start)

        try:
            img_file_name = 'img_stress_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            stress_button = tk.Button(self._main_fr,image = photo,command=self.on_open_stresses_window)
            stress_button.image = photo
            stress_button.place(x=10,y=prop_vert_start+3*delta_y)
        except TclError:
            tk.Button(self._main_fr, text='STRESS', command=self.on_open_stresses_window)\
                .place(x=10,y=prop_vert_start+3*delta_y)

        try:
            img_file_name = 'fls_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            fls_button = tk.Button(self._main_fr,image = photo,command=self.on_open_fatigue_window)
            fls_button.image = photo
            fls_button.place(x=10,y=prop_vert_start+6*delta_y)
        except TclError:
            tk.Button(self._main_fr, text='FLS', command=self.on_open_fatigue_window)\
                .place(x=10,y=prop_vert_start+6*delta_y)

        # --- tank load input and information ---
        load_vert_start = 690* self._global_shrink
        tk.Label(self._main_fr,text = 'Comp. no.:', font=self._text_size['Text 8 bold'])\
            .place(x=10, y=load_vert_start + 3.5*delta_y)

        self._selected_tank = tk.Label(self._main_fr,text='',font = self._text_size['Text 12 bold'],fg='red')
        self._selected_tank.place(x=120, y=load_vert_start + 3.5*delta_y)

        self._compartments_listbox = tk.Listbox(self._main_fr, height = int(10 * self._global_shrink),
                                               width = int(5 * self._global_shrink),
                                               font=self._text_size["Text 10 bold"]
                                               ,bg = 'DarkSeaGreen1', selectmode = 'extended' )
        self._compartments_listbox.place(x=10, y=load_vert_start + 4.2*delta_y)
        self._compartments_listbox.bind('<<ListboxSelect>>', self.button_1_click_comp_box)


        tk.Button(self._main_fr, text="Set compartment\n""properties.",command = self.update_tank,
                                            font=self._text_size['Text 8 bold'], bg = 'white', fg = 'blue')\
            .place(x=ent_x+delta_x*3, y=load_vert_start + delta_y * 5)

        tk.Button(self._main_fr, text="Delete all tanks", command=self.delete_all_tanks,
                  font=self._text_size['Text 8 bold'], bg = 'white', fg = 'blue')\
            .place(x=ent_x+delta_x*3, y=load_vert_start + delta_y * 7)
        self._new_content_type = tk.StringVar()

        self._ent_content_type = tk.OptionMenu(self._main_fr, self._new_content_type, *self._tank_options)
        ent_width = 10
        self._new_overpresure = tk.DoubleVar()
        self._ent_overpressure = tk.Entry(self._main_fr, textvariable = self._new_overpresure,
                                         width = int(ent_width * self._global_shrink))
        self._new_overpresure.set(25000)
        self._new_density = tk.DoubleVar()
        self._ent_density = tk.Entry(self._main_fr, textvariable = self._new_density,
                                    width = int(ent_width * self._global_shrink))
        self._new_density.set(1025)
        self._new_max_el = tk.DoubleVar()
        self._ent_max_el = tk.Entry(self._main_fr, textvariable=self._new_max_el,
                                   width=int(ent_width * self._global_shrink),bg = 'grey')
        self._new_min_el = tk.DoubleVar()
        self._ent_min_el = tk.Entry(self._main_fr, textvariable=self._new_min_el,
                                   width=int(ent_width * self._global_shrink),bg = 'grey')
        tk.Label(self._main_fr, text = '', font = self._text_size["Text 12 bold"])\
            .place(x=100, y=load_vert_start + 3.4*delta_y)
        tk.Label(self._main_fr, text='Tank content :', font = self._text_size['Text 8'])\
            .place(x=ent_x-2*delta_x, y=load_vert_start + delta_y * 4.5)
        self._ent_content_type.place(x= ent_x+0.35*delta_x, y=load_vert_start + delta_y * 4.5)
        tk.Label(self._main_fr, text='Tank density :', font = self._text_size['Text 8'])\
            .place(x=ent_x-2*delta_x, y=load_vert_start + delta_y * 6)
        self._ent_density.place(x=ent_x+0.4*delta_x, y=load_vert_start + delta_y * 6)
        tk.Label(self._main_fr,text='[kg/m^3]', font = self._text_size['Text 8'])\
            .place(x= ent_x+delta_x*1.5, y=load_vert_start + delta_y * 6)
        tk.Label(self._main_fr, text='Overpressure :', font = self._text_size['Text 8'])\
            .place(x=ent_x-2*delta_x, y=load_vert_start + delta_y * 7)
        self._ent_overpressure.place(x=ent_x+0.4*delta_x, y=load_vert_start + delta_y * 7)
        tk.Label(self._main_fr,text='[Pa]', font = self._text_size['Text 8'])\
            .place(x= ent_x+delta_x*1.5, y=load_vert_start + delta_y * 7)
        tk.Label(self._main_fr, text='Max elevation :', font = self._text_size['Text 8'])\
            .place(x=ent_x-2*delta_x, y=load_vert_start + delta_y * 8)
        self._ent_max_el.place(x=ent_x+0.4*delta_x, y=load_vert_start + delta_y * 8)
        tk.Label(self._main_fr, text='Min elevation :', font = self._text_size['Text 8'])\
            .place(x=ent_x-2*delta_x, y=load_vert_start + delta_y * 9)
        self._ent_min_el.place(x=ent_x+0.4*delta_x, y=load_vert_start + delta_y * 9)
        self._tank_acc_label = tk.Label(self._main_fr, text = 'Acceleration [m/s^2]: ', font = self._text_size['Text 8'])
        self._tank_acc_label.place(x=ent_x-2*delta_x, y=load_vert_start + delta_y * 10)

        # --- button to create compartments and define external pressures ---

        try:
            img_file_name = 'img_int_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)

            self._int_button = tk.Button(self._main_fr,image = photo,command=self.grid_find_tanks)
            self._int_button.image = photo
            self._int_button.place(x=10, y=load_vert_start+0*delta_y)
        except TclError:
            tk.Button(self._main_fr, text='New tanks - start search \n'
                                  'to find compartments', command=self.grid_find_tanks,
                      bg='green', fg='yellow', font=self._text_size['Text 8 bold']) \
                .place(x=10, y=load_vert_start + 0 * delta_y)

        show_compartment = tk.Button(self._main_fr, text='Display current compartments', command=self.grid_display_tanks,
                                  bg = 'white', fg = 'blue', font=self._text_size['Text 8 bold'])
        show_compartment.place(x=10, y=load_vert_start+2*delta_y)

        try:

            img_file_name = 'img_ext_pressure_button.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)

            self._ext_button = tk.Button(self._main_fr,image=photo, command = self.on_show_loads)
            self._ext_button.image = photo
            self._ext_button.place(x=ent_x+delta_x*1.5, y=load_vert_start+0*delta_y)
        except TclError:
            tk.Button(self._main_fr, text='New external load window \nsea - static/dynamic',
                      command=self.on_show_loads, bg='green',fg='yellow', font=self._text_size['Text 8 bold'])\
                .place(x=ent_x+delta_x*2, y=load_vert_start+0*delta_y)

        lc_x, lc_x_delta, lc_y, lc_y_delta = 1510*self._global_shrink, 30*self._global_shrink, \
                                             190*self._global_shrink, 25*self._global_shrink

        # --- infomation on accelerations ----
        tk.Label(self._main_fr,text='Static and dynamic accelerations',
                 font = self._text_size["Text 9 bold"], fg = 'black').place(x=lc_x, y=lc_y - 5 * lc_y_delta)
        tk.Label(self._main_fr,text='Static acceleration [m/s^2]: ', font = self._text_size["Text 9"] )\
            .place(x=lc_x, y=lc_y - 4 * lc_y_delta)
        tk.Label(self._main_fr,text='Dyn. acc. loaded [m/s^2]:', font = self._text_size["Text 9"])\
            .place(x=lc_x, y=lc_y - 3 * lc_y_delta)
        tk.Label(self._main_fr,text='Dyn. acc. ballast [m/s^2]:', font = self._text_size["Text 9"])\
            .place(x=lc_x, y=lc_y - 2 * lc_y_delta)
        self._new_dyn_acc_loaded = tk.DoubleVar()
        self._new_dyn_acc_ballast = tk.DoubleVar()
        self._new_static_acc = tk.DoubleVar()
        self._new_static_acc.set(9.81), self._new_dyn_acc_loaded.set(0), self._new_dyn_acc_ballast.set(0)
        tk.Entry(self._main_fr, textvariable = self._new_static_acc,width = 10)\
            .place(x=lc_x + delta_x*4.2, y=lc_y - 4 * lc_y_delta)
        tk.Entry(self._main_fr, textvariable = self._new_dyn_acc_loaded,width = 10)\
            .place(x=lc_x + delta_x*4.2, y=lc_y - 3 * lc_y_delta)
        tk.Entry(self._main_fr, textvariable = self._new_dyn_acc_ballast,width = 10)\
            .place(x=lc_x + delta_x*4.2, y=lc_y - 2 * lc_y_delta)
        tk.Button(self._main_fr, text = 'Set\naccelerations', command = self.create_accelerations,
                  font = self._text_size['Text 8 bold'],
                  fg = 'yellow',bg = 'green').place(x=lc_x + delta_x*6, y=lc_y - 3 * lc_y_delta)

        # --- checkbuttons and labels ---
        self._dnv_a_chk,self._dnv_b_chk  = tk.IntVar(),tk.IntVar()
        self._tank_test_chk,self._manual_chk = tk.IntVar(),tk.IntVar()
        self._check_button_load_comb = [self._dnv_a_chk,self._dnv_b_chk, self._tank_test_chk, self._manual_chk]
        self._active_label = tk.Label(self._main_fr, text = '', font = self._text_size["Text 12 bold"], fg = 'blue')
        self._active_label.place(x=lc_x+lc_x_delta*10,y=lc_y-lc_y_delta*5)
        tk.Label(self._main_fr, text='Combination for line (select line). Change with slider.: ',
                 font=self._text_size["Text 8 bold"], fg='black').place(x=lc_x, y=lc_y + 2.5*delta_y)


        lc_y += 160*self._global_shrink

        self._combination_slider = tk.Scale(self._main_fr, from_=1, to=3, command=self.gui_load_combinations,length=400,
                                           orient = 'horizontal', bg = 'azure',
                                            label='OS-C101 Table 1    1: DNV a)    2: DNV b)    3: TankTest',
                                            relief='groove')

        self._combination_slider.place(x=lc_x +0*lc_x_delta, y=lc_y - 3*lc_y_delta)
        self._combination_slider_map = {1:'dnva',2:'dnvb',3:'tanktest'}
        tk.Label(self._main_fr, text='Name:', font = self._text_size['Text 7'])\
            .place(x=lc_x + 0 * lc_x_delta, y=lc_y)
        tk.Label(self._main_fr, text='Stat LF', font = self._text_size['Text 7'])\
            .place(x=lc_x + 8.5 * lc_x_delta, y=lc_y)
        tk.Label(self._main_fr, text='Dyn LF', font = self._text_size['Text 7'])\
            .place(x=lc_x + 10.2 * lc_x_delta, y=lc_y)
        tk.Label(self._main_fr, text='Include?',font = self._text_size['Text 7'])\
            .place(x=lc_x + 11.8 * lc_x_delta, y=lc_y)

        self._result_label_dnva = tk.Label(self._main_fr, text='DNV a [Pa]: ',font='Text 8')
        self._result_label_dnvb = tk.Label(self._main_fr, text='DNV b [Pa]: ',font=self._text_size["Text 8"])
        self._result_label_tanktest = tk.Label(self._main_fr, text='Tank test [Pa]: ',font=self._text_size["Text 8"])
        self._result_label_manual = tk.Label(self._main_fr, text='Manual [Pa]: ',font=self._text_size["Text 8"])
        self.results_gui_start = 650*self._global_shrink
        tk.Label(self._main_fr, text = 'Pressures for this line: \n(DNV a/b [loaded/ballast], tank test, manual)\n'
                               'Note that ch. 4.3.7 and 4.3.8 is accounted for.',font=self._text_size["Text 8"])\
            .place(x = lc_x, y = self.results_gui_start)

        # --- optimize button ---
        tk.Label(self._main_fr,text='Optimize selected line/structure (right click line):',
                 font = self._text_size['Text 9 bold'],fg='black').place(x=lc_x, y=lc_y - 7 * lc_y_delta)
        try:
            img_file_name = 'img_optimize.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            opt_button = tk.Button(self._main_fr,image=photo, command = self.on_optimize)
            opt_button.image = photo
            opt_button.place(x=lc_x, y=lc_y - 6 * lc_y_delta)
        except TclError:
            tk.Button(self._main_fr, text='Optimize', command=self.on_optimize_multiple)\
                .place(x=lc_x, y=lc_y - 6 * lc_y_delta)
        try:
            img_file_name = 'img_multi_opt.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = self._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            opt_button_mult = tk.Button(self._main_fr,image=photo, command = self.on_optimize_multiple)
            opt_button_mult.image = photo
            opt_button_mult.place(x=lc_x+delta_x*4, y=lc_y - 6 * lc_y_delta)
        except TclError:
            tk.Button(self._main_fr, text='MultiOpt', command=self.on_optimize_multiple).place(x=lc_x + delta_x*7,
                                                                                               y=lc_y - 6 * lc_y_delta)

        tk.Button(self._main_fr, text='SPAN', command=self.on_geometry_optimize,
                 font = self._text_size['Text 14 bold'], fg='green', height = 1, bg = 'white')\
           .place(x=lc_x + delta_x * 6.7,y=lc_y - 6 * lc_y_delta)
        # try:
        #     photo_report = tk.PhotoImage(file=self._root_dir + '\\images\\' +"img_generate_report.gif")
        #     report_button = tk.Button(self._main_fr,image=photo_report, command = self.report_generate)
        #     report_button.image = photo_report
        #     report_button.place(x=1600,y=0)
        # except TclError:
        #     tk.Button(self._main_fr, text='Generate report', command=self.report_generate).place(x=1600,y=0)

        #self.openfile(defined='general_section_slm.txt')

    def gui_load_combinations(self,event):
        '''
        Initsializing and updating gui for load combinations.
        The fields are located left of the Canvas.
        :return:
        '''

        if self._line_is_active and self._active_line in self._line_to_struc.keys():
            lc_x, lc_x_delta, lc_y, lc_y_delta = 1520*self._global_shrink, 50*self._global_shrink, \
                                                 380*self._global_shrink, 25*self._global_shrink
            self._active_label.config(text=self._active_line)
            combination = self._combination_slider_map[self._combination_slider.get()]

            # removing label, checkbox and entry. setting created items to empty list.
            [[item.destroy() for item in items] for items in
             [self._lc_comb_created,self._comp_comb_created,self._manual_created, self._info_created]]
            self._lc_comb_created, self._comp_comb_created, self._manual_created, self._info_created= [], [], [], []

            if self._line_to_struc[self._active_line][0].get_structure_type() == '':
                self._info_created.append(tk.Label(self._main_fr, text='No structure type selected',
                                               font=self._text_size["Text 10 bold"]))
                self._info_created[0].place(x=lc_x , y = lc_y + 3*lc_y_delta)

            else:
                # creating new label, checkbox and entry. creating new list of created items.
                # finding loads applied to lines
                counter = 0

                if len(self._load_dict) != 0 and combination !='manual':
                    for load, data in self._load_dict.items():
                        if self._active_line in self._load_dict[load][1] and data[0].get_limit_state() == 'ULS':
                            name = (combination,self._active_line,str(load)) #tuple to identify combinations on line
                            self._lc_comb_created.append(tk.Label(self._main_fr, text = load,
                                                                 font = self._text_size['Text 8 bold']))
                            self._lc_comb_created.append(tk.Entry(self._main_fr,
                                                                 textvariable =self._new_load_comb_dict[name][0],
                                                                 width = 5))
                            self._lc_comb_created.append(tk.Entry(self._main_fr,
                                                                 textvariable=self._new_load_comb_dict[name][1],
                                                                 width=5))
                            self._lc_comb_created.append(tk.Checkbutton(self._main_fr,
                                                                       variable =self._new_load_comb_dict[name][2]))

                    for load_no in range(int(len(self._lc_comb_created)/4)):
                            self._lc_comb_created[0+load_no*4].place(x=lc_x, y=lc_y+lc_y_delta*load_no)
                            self._lc_comb_created[1+load_no*4].place(x=lc_x+5*lc_x_delta, y=lc_y+lc_y_delta*load_no)
                            self._lc_comb_created[2+load_no*4].place(x=lc_x+6*lc_x_delta, y=lc_y+lc_y_delta*load_no)
                            self._lc_comb_created[3+load_no*4].place(x=lc_x+7*lc_x_delta, y=lc_y+lc_y_delta*load_no)
                            counter += 1

                # finding tank loads applied to line (automatically created compartments.
                lc_y += 25*counter*self._global_shrink
                counter = 0
                if len(self._tank_dict) != 0 and combination !='manual':
                    for compartment in self.get_compartments_for_line(self._active_line):
                        name = (combination,self._active_line,'comp' + str(compartment)) #tuple to identify combinations on line
                        self._comp_comb_created.append(tk.Label(self._main_fr, text='Compartment'+str(compartment),
                                                               font=self._text_size['Text 8 bold']))
                        self._comp_comb_created.append(tk.Entry(self._main_fr,
                                                               textvariable=self._new_load_comb_dict[name][0], width=5))
                        self._comp_comb_created.append(tk.Entry(self._main_fr,
                                                               textvariable=self._new_load_comb_dict[name][1], width=5))
                        self._comp_comb_created.append(tk.Checkbutton(self._main_fr,
                                                                     variable = self._new_load_comb_dict[name][2]))

                    for comp_no in range(int(len(self._comp_comb_created)/4)):
                            self._comp_comb_created[0+comp_no*4].place(x=lc_x, y=lc_y+lc_y_delta*comp_no)
                            self._comp_comb_created[1+comp_no*4].place(x=lc_x+5*lc_x_delta, y=lc_y+lc_y_delta*comp_no)
                            self._comp_comb_created[2+comp_no*4].place(x=lc_x+6*lc_x_delta, y=lc_y+lc_y_delta*comp_no)
                            self._comp_comb_created[3+comp_no*4].place(x=lc_x+7*lc_x_delta, y=lc_y+lc_y_delta*comp_no)
                            counter += 1

                lc_y += 30*counter*self._global_shrink
                # finding manual loads applied to the line

                name = ('manual', self._active_line, 'manual')  # tuple to identify combinations on line
                if name in self._new_load_comb_dict.keys():
                    self._manual_created.append(tk.Label(self._main_fr, text='Manual (pressure/LF)',
                                                        font=self._text_size['Text 8 bold']))
                    self._manual_created.append(
                        tk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][0], width=15))
                    self._manual_created.append(
                        tk.Entry(self._main_fr, textvariable=self._new_load_comb_dict[name][1], width=6))
                    self._manual_created.append(tk.Checkbutton(self._main_fr, variable=self._new_load_comb_dict[name][2]))
                    self._manual_created[0].place(x=lc_x, y=lc_y)
                    self._manual_created[1].place(x=lc_x + 4 * lc_x_delta, y=lc_y)
                    self._manual_created[2].place(x=lc_x + 6 * lc_x_delta, y=lc_y)
                    self._manual_created[3].place(x=lc_x + 7 * lc_x_delta, y=lc_y)

            #printing the results
            results = self.calculate_all_load_combinations_for_line(self._active_line)
            self._result_label_dnva.config(text = 'DNV a [Pa]: ' + str(results['dnva']),
                                          font = self._text_size['Text 7'])
            self._result_label_dnvb.config(text = 'DNV b [Pa]: ' + str(results['dnvb']),
                                          font = self._text_size['Text 7'])
            self._result_label_tanktest.config(text = 'TT [Pa]: ' + str(results['tanktest']),
                                              font = self._text_size['Text 7'])

            try:
                self._result_label_manual.config(text = 'Manual [Pa]: ' + str(results['manual']))
            except KeyError:
                pass
            lc_y = self.results_gui_start+20
            self._result_label_dnva.place(x = lc_x+0*lc_x_delta, y = lc_y+lc_y_delta*1.2)
            self._result_label_dnvb.place(x=lc_x+4*lc_x_delta, y=lc_y+lc_y_delta*1.2)
            self._result_label_tanktest.place(x=lc_x+0*lc_x_delta, y=lc_y+2*lc_y_delta)
            try:
                self._result_label_manual.place(x=lc_x+4*lc_x_delta, y=lc_y+2*lc_y_delta)
            except KeyError:
                pass

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

        if tk.messagebox.askquestion('Search for compartments','Searching for compartments will use a large matrix to '
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
                                                               'Choose yes or no.' ):
            animate = True
        else:
            animate = False

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

        if not animate:
            self._grid_calc.draw_grid(tank_count=None if len(self._tank_dict)==0 else len(self._tank_dict))
        else:
            self._grid_calc.animate_grid(grids_to_animate=compartment_search_return['grids'])

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

            name = ('manual', line,'manual')
            self._new_load_comb_dict[name] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
            self._new_load_comb_dict[name][0].set(0)
            self._new_load_comb_dict[name][1].set(0)
            self._new_load_comb_dict[name][2].set(0)
        else:
            pass

    def update_frame(self):
        state = self.get_color_and_calc_state()
        self.draw_canvas(state=state)
        self.draw_prop()

    def get_color_and_calc_state(self, current_line = None, active_line_only = False):
        ''' Return calculations and colors for line and results. '''

        return_dict = {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                       'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                       'struc_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}, 'utilization': {}, 'slamming': {}}
        line_iterator, slamming_pressure = [], None
        return_dict['slamming'][current_line] = {}

        if current_line is None and active_line_only:
            line_iterator = [self._active_line, ]
        elif current_line is None and not active_line_only and len(self._line_dict) != 0:
            line_iterator = self._line_dict.keys()
        elif current_line is not None:
            line_iterator = [current_line, ]
        elif current_line not in self._line_to_struc.keys() and active_line_only:
            return return_dict

        for current_line in line_iterator:
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
                        slamming_pressure = self.get_highest_pressure(current_line)['slamming']
                except KeyError:
                    design_pressure = 0

                sec_mod = [round(obj_structure.get_section_modulus()[0], 5),
                           round(obj_structure.get_section_modulus()[1], 5)]

                shear_area = obj_structure.get_shear_area()
                min_shear = obj_scnt_calc.get_minimum_shear_area(design_pressure)
                min_sec_mod = obj_scnt_calc.get_dnv_min_section_modulus(design_pressure)
                min_thk = obj_scnt_calc.get_dnv_min_thickness(design_pressure)
                buckling = [round(res, 2) for res in obj_scnt_calc.calculate_buckling_all(
                    design_lat_press=design_pressure,
                    checked_side=obj_structure.get_side())]

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
                    slamming_res = obj_scnt_calc.calculate_slamming_stiffener(slamming_pressure)
                    min_pl_slamming = obj_scnt_calc.calculate_slamming_plate(slamming_pressure)

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
                return_dict['buckling'][current_line] = buckling
                return_dict['pressure_uls'][current_line] = design_pressure
                return_dict['pressure_fls'][current_line] = {'p_int': p_int, 'p_ext': p_ext}
                return_dict['section_modulus'][current_line] = {'sec_mod': sec_mod, 'min_sec_mod': min_sec_mod}
                return_dict['shear_area'][current_line] = {'shear_area': shear_area, 'min_shear_area': min_shear}
                return_dict['thickness'][current_line] = {'thk': obj_structure.get_plate_thk(), 'min_thk': min_thk}
                return_dict['struc_obj'][current_line] = obj_structure
                return_dict['scant_calc_obj'][current_line] = obj_scnt_calc
                return_dict['fatigue_obj'][current_line] = fatigue_obj

                if fatigue_obj is not None:
                    return_dict['fatigue'][current_line] = {'damage': damage, 'dff': dff,
                                                            'curve': fatigue_obj.get_sn_curve()}
                else:
                    return_dict['fatigue'][current_line] = {'damage': None, 'dff': None, 'curve': None}

                fat_util = 0 if damage is None else damage * dff
                shear_util = 0 if shear_area == 0 else min_shear / shear_area
                thk_util = 0 if obj_structure.get_plate_thk() == 0 else min_thk / (1000 * obj_structure.get_plate_thk())
                sec_util = 0 if min(sec_mod) == 0 else min_sec_mod / min(sec_mod)
                buc_util = 1 if float('inf') in buckling else max(buckling)
                return_dict['utilization'][current_line] = {'buckling': buc_util,
                                                            'fatigue': fat_util,
                                                            'section': sec_util,
                                                            'shear': shear_util,
                                                            'thickness': thk_util}

                self._state_logger[current_line] = return_dict #  Logging the current state of the line.
                self._line_to_struc[current_line][1].need_recalc = False

            else:
                pass
        return return_dict

    def draw_canvas(self, state = None):
        '''
        Canvas is drawn here.
        '''


        self._main_canvas.delete('all')

        # grid for the canavs
        # print('***')
        # print('drawing canvas')

        self._main_canvas.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0], self._canvas_dim[1],
                                     stipple='gray50')
        self._main_canvas.create_line(0, self._canvas_draw_origo[1], self._canvas_dim[0], self._canvas_draw_origo[1],
                                     stipple='gray50')
        self._main_canvas.create_text(self._canvas_draw_origo[0] - 30*self._global_shrink,
                                     self._canvas_draw_origo[1] + 20* self._global_shrink, text='(0,0)',
                                     font = 'Text 10')
        self._main_canvas.create_text([880*self._global_shrink,20*self._global_shrink],
                                     text = 'Mouse left click:  select line\n'
                                                     'Mouse right click: select point',
                                     font = self._text_size['Text 8 bold'], fill='red')

        # drawing the point dictionary
        pt_size = 3
        for key, value in self._point_dict.items():
            if self._point_is_active and key == self._active_point :
                self._main_canvas.create_oval(self.get_point_canvas_coord(key)[0] - pt_size+2,
                                             self.get_point_canvas_coord(key)[1] - pt_size+2,
                                             self.get_point_canvas_coord(key)[0] + pt_size+2,
                                             self.get_point_canvas_coord(key)[1] + pt_size+2, fill='blue')
                #printing 'pt.#'
                self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                             self.get_point_canvas_coord(key)[1] - 14, text='pt.'+str(get_num(key)),
                                             font=self._text_size["Text 10 bold"], fill = 'red')
                #printing the coordinates of the point
                self._main_canvas.create_text(self.get_point_canvas_coord(key)[0],
                                              self.get_point_canvas_coord(key)[1] - 25,
                                             text='(' + str(round(self.get_point_actual_coord(key)[0],2)) + ' , ' +
                                                  str(round(self.get_point_actual_coord(key)[1],2)) + ')',
                                              font="Text 10", fill = 'red')

            else:
                self._main_canvas.create_oval(self.get_point_canvas_coord(key)[0] - pt_size,
                                             self.get_point_canvas_coord(key)[1] - pt_size,
                                             self.get_point_canvas_coord(key)[0] + pt_size,
                                             self.get_point_canvas_coord(key)[1] + pt_size, fill='red')
                #printing 'pt.#'
                self._main_canvas.create_text(self.get_point_canvas_coord(key)[0] - 5,
                                             self.get_point_canvas_coord(key)[1] - 14, text='pt.'+str(get_num(key)))
                #printing the coordinates of the point
                self._main_canvas.create_text(self.get_point_canvas_coord(key)[0]+20,
                                              self.get_point_canvas_coord(key)[1] - 25,
                                             text='(' + str(round(self.get_point_actual_coord(key)[0],2)) + ' , ' +
                                                  str(round(self.get_point_actual_coord(key)[1],2)) + ')',
                                              font="Text 6")

        # drawing the line dictionary.
        if len(self._line_dict) != 0:

            for line, value in self._line_dict.items():

                coord1 = self.get_point_canvas_coord('point' + str(value[0]))
                coord2 = self.get_point_canvas_coord('point' + str(value[1]))
                try:
                    color = 'red' if 'red' in state['colors'][line].values() else 'green'
                except (KeyError, TypeError):
                    color = 'black'

                vector = [coord2[0] - coord1[0], coord2[1] - coord1[1]]
                # drawing a bold line if it is selected
                if line == self._active_line and self._line_is_active:
                    self._main_canvas.create_line(coord1, coord2, width=6, fill = color)
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2+10,
                                                 text='Line ' + str(get_num(line)), font=self._text_size["Text 10 bold"],
                                                 fill = 'red')
                else:
                    self._main_canvas.create_line(coord1, coord2, width=3, fill = color)
                    self._main_canvas.create_text(coord1[0]-20 + vector[0] / 2 + 5, coord1[1] + vector[1] / 2+10,
                                                 text='l.' + str(get_num(line)), font="Text 8", fill = 'black')

        # drawing waterline
        if len(self._load_dict) != 0:
            for load, data in self._load_dict.items():

                if data[0].is_static():
                    draft = self.get_canvas_coords_from_point_coords((0,data[0].get_static_draft()))[1]
                    self._main_canvas.create_line(0,draft,self._canvas_dim[0],draft, fill="blue", dash=(4, 4))
                    self._main_canvas.create_text(930,draft-10,text=str(get_num(data[0].get_name()))+' [m]',fill ='blue')
                else:
                    pass

    def draw_prop(self):
        '''
        Prints the properties of the selected line to the bottom canvas.

        properties for line dicitonary:

        name of line : [ Structure class, calc scantling class, calc fatigue class, [load classes] ]

        '''
        self._prop_canvas.delete('all')
        # print('***')
        # print('drawing prop')
        if self._active_line in self._line_to_struc:

            # printing the properties to the active line
            if self._line_is_active:
                self._prop_canvas.create_text([175*self._global_shrink, 110*self._global_shrink],
                                             text=self._line_to_struc[self._active_line][0],
                                             font = self._text_size["Text 7"],justify=tk.LEFT)

                # setting the input field to active line properties
                self.set_selected_variables(self._active_line)

                # draw the plate and stiffener
                mult = 200*self._global_shrink
                thk_mult = 500*self._global_shrink
                startx = 540*self._global_shrink
                starty = 150*self._global_shrink
                structure_obj = self._line_to_struc[self._active_line][0]

                self._prop_canvas.create_text([330*self._global_shrink, 15*self._global_shrink],
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
                if structure_obj.get_stiffener_type() != 'L':
                    self._prop_canvas.create_line(startx+spacing*0.5-stf_flange_width/2,starty-stf_web_height,
                                             startx + spacing * 0.5 + stf_flange_width / 2, starty - stf_web_height,
                                             width=stf_flange_thk)
                else:
                    self._prop_canvas.create_line(startx+spacing*0.5-stf_web_thk/2,starty-stf_web_height,
                                             startx + spacing * 0.5 + stf_flange_width , starty - stf_web_height,
                                             width=stf_flange_thk)

                # load applied to this line
                deltax = 160*self._global_shrink
                stl_x = 500*self._global_shrink
                stl_y = 170*self._global_shrink
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
                self._prop_canvas.create_text([200*self._global_shrink, 50*self._global_shrink],
                                             text='No line is selected. Click on a line to show properies',
                                             font=self._text_size['Text 9 bold'])
        else:
            self._prop_canvas.create_text([160*self._global_shrink, 20*self._global_shrink],
                                         text='Properties displayed here (select line):',
                                         font=self._text_size['Text 9 bold'])

    def draw_results(self, state = None):
        '''
        The properties canvas is created here.
                state =     {'colors': {}, 'section_modulus': {}, 'thickness': {}, 'shear_area': {}, 'buckling': {},
                            'fatigue': {}, 'pressure_uls': {}, 'pressure_fls': {},
                            'struc_obj': {}, 'scant_calc_obj': {}, 'fatigue_obj': {}}
        :return:
        '''
        if state is None or self._active_line not in state['struc_obj'].keys():
            return

        self._result_canvas.delete('all')

        if self._line_is_active:

            if self._active_line in self._line_to_struc:
                x, y, dx, dy = 20, 15, 15, 14
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
                self._result_canvas.create_text([x*self._global_shrink, y*self._global_shrink],
                                               text=text,font=self._text_size['Text 9 bold'],anchor='nw')
                #printing the minimum section modulus
                if state['slamming'][current_line]['state'] and slm_text_min_zpl is False:
                    text = '(shear issue, change thickness or web height)'
                else:
                    text =  'Minimum section modulus: '+str('%.4E' % decimal.Decimal(min_sec_mod * m3_to_mm3)) +\
                            ' [mm^3] ' if not slm_text_min_zpl else slm_text_min_zpl
                self._result_canvas.create_text([x*self._global_shrink, (y+dy)*self._global_shrink], text= text,
                                                    font=self._text_size["Text 9 bold"],anchor='nw', fill=color_sec)

                #minimum shear area
                text = 'Shear area: '+str('%.4E' % decimal.Decimal(shear_area * m2_to_mm2 ))+' [mm^2]' \
                    if not slm_text_min_web_thk else 'Stiffener web thickness: '+str(obj_structure.get_web_thk()*1000)+' [mm]'
                self._result_canvas.create_text([x*self._global_shrink, (y+3*dy)*self._global_shrink],
                                               text= text,
                                               font=self._text_size["Text 9 bold"],anchor='nw')
                text = 'Minimum shear area: '+str('%.4E' % decimal.Decimal(min_shear * m2_to_mm2))+' [mm^2] ' \
                    if not slm_text_min_web_thk else 'Minimum stiffener web thickness due to SLAMMING: '+\
                                                     str(round(slm_min_web_thk,1))+' [mm]'
                self._result_canvas.create_text([x*self._global_shrink, (y+4*dy)*self._global_shrink],
                                               text = text,
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_shear)

                #minimum thickness for plate

                self._result_canvas.create_text([20*self._global_shrink, (y+6*dy)*self._global_shrink],
                                               text='Plate thickness: '
                                                    +str(obj_structure.get_plate_thk()*1000)+' [mm] ',
                                               font=self._text_size["Text 9 bold"],anchor='nw')
                text = 'Minimum plate thickness: '+str(round(min_thk,1)) + ' [mm]' if not slm_text_pl_thk \
                    else 'Minimum plate thickness due to SLAMMING'+str(slm_min_pl_thk)+' [mm]'
                self._result_canvas.create_text([20*self._global_shrink, (y+7*dy)*self._global_shrink],
                                               text=text,
                                               font=self._text_size["Text 9 bold"],anchor='nw', fill=color_thk)

                # buckling results

                self._result_canvas.create_text([x * self._global_shrink, (y+9*dy) * self._global_shrink],
                                               text='Buckling results DNV-RP-C201 (z* optimized):',
                                               font=self._text_size["Text 9 bold"], anchor='nw')
                if sum(buckling)==0:
                    self._result_canvas.create_text([x * self._global_shrink, (y+10*dy) * self._global_shrink],
                                                   text='No buckling results', font=self._text_size["Text 9 bold"],
                                                   anchor='nw', fill=color_buckling)
                else:
                    if buckling[0]==float('inf'):
                        res_text = 'Plate resistance not ok (equation 6.12). '
                    else:
                        if obj_structure.get_side() == 'p':
                            res_text = '|eq 7.19: '+str(buckling[0])+' |eq 7.50: '+str(buckling[1])+ ' |eq 7.51: '+ \
                                         str(buckling[2])+' |7.52: '+str(buckling[3])+ '|eq 7.53: '+str(buckling[4])+\
                                         ' |z*: '+str(buckling[5])
                        elif obj_structure.get_side() == 's':
                            res_text = '|eq 7.19: '+str(buckling[0])+' |eq 7.54: '+str(buckling[1])+' |eq 7.55: '+ \
                                         str(buckling[2])+' |7.56: '+str(buckling[3])+ '|eq 7.57: '+str(buckling[4])+ \
                                         ' |z*: '+str(buckling[5])
                    self._result_canvas.create_text([x * self._global_shrink, (y+10*dy) * self._global_shrink],
                                               text=res_text,font=self._text_size["Text 9 bold"],
                                               anchor='nw',fill=color_buckling)

                # fatigue results

                self._result_canvas.create_text([x * self._global_shrink, (y+12*dy) * self._global_shrink],
                                                text='Fatigue results (DNVGL-RP-C203): ',
                                                font=self._text_size["Text 9 bold"], anchor='nw')

                if self._line_to_struc[current_line][2] != None:
                    if state['fatigue'][current_line]['damage'] is not None:
                        damage = state['fatigue'][current_line]['damage']
                        dff = state['fatigue'][current_line]['dff']
                        self._result_canvas.create_text([x * self._global_shrink, (y + 13 * dy) * self._global_shrink],
                                                        text='Total damage (DFF not included): '+str(round(damage,3)) +
                                                             '  |  With DFF = '+str(dff)+' --> Damage: '+
                                                             str(round(damage*dff,3)),
                                                        font=self._text_size["Text 9 bold"], anchor='nw',
                                                        fill=color_fatigue)
                    else:
                        self._result_canvas.create_text([x * self._global_shrink, (y + 13 * dy) * self._global_shrink],
                                                        text='Total damage: NO RESULTS ',
                                                        font=self._text_size["Text 9 bold"],
                                                        anchor='nw')
                else:
                    self._result_canvas.create_text([x * self._global_shrink, (y + 13 * dy) * self._global_shrink],
                                                    text='Total damage: NO RESULTS ',
                                                    font=self._text_size["Text 9 bold"],
                                                    anchor='nw')
        else:
            self._result_canvas.create_text([200*self._global_shrink, 20*self._global_shrink],
                                           text='The results are shown here (select line):',
                                           font=self._text_size["Text 10 bold"])

    def report_generate(self):
        '''
        Button is pressed to generate a report of the current structure.
        :return:
        '''
        to_report_gen ={}
        # Compartments, make
        save_file = filedialog.asksaveasfile(mode="w", defaultextension=".pdf")
        if save_file is None:  # ask saveasfile return `None` if dialog closed with "cancel".
            return
        filename = save_file.name
        if self._line_dict == {}:
            tk.messagebox.showerror('No lines', 'No lines defined. Cannot make report.')
            return

        if os.path.isfile('current_comps.png'):
            os.remove('current_comps.png')
            self.grid_display_tanks(save = True)
        else:
            self.grid_display_tanks(save=True)

        # Results
        to_report_gen = self.get_color_and_calc_state()

        # Load objects
        to_report_gen['loads'] = {}
        for line in self._line_dict.keys():
            try:
                to_report_gen['loads'][line] = self._line_to_struc[line][3]
            except KeyError:
                pass

        # Comparments
        to_report_gen['compartments'] = {}
        if len(self._tank_dict) != 0:
            to_report_gen['compartments'] = self._tank_dict

        # Points
        to_report_gen['points'] = self._point_dict
        # Lines
        to_report_gen['lines'] = self._line_dict

        to_report_gen['path'] = self._root_dir

        doc = LetterMaker(filename, "Section results", 10, to_report_gen)
        doc.createDocument()
        doc.savePDF()
        try:
            os.startfile(filename)
        except FileNotFoundError:
            pass

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
                        if self._line_to_struc[line][0].get_structure_type() not in ['GENERAL_INTERNAL_NONWT',
                                                                                                'FRAME']:
                            self._tank_dict = {}
                            self._main_grid.clear()
                            self._compartments_listbox.delete(0, 'end')
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
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a line number.')

    def new_structure(self, event = None):
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
        if any([self._new_stf_spacing.get()==0, self._new_plate_thk.get()==0, self._new_stf_web_h.get()==0,
                self._new_sft_web_t.get()==0]):
            mess = tk.messagebox.showwarning('No propertied defined', 'No properties is defined for the line!\n'
                                                                      'Define spacing, web height, web thickness etc.\n'
                                                                      'Either press button with stiffener or input'
                                                                      'manually.', type='ok')
            return

        if self._line_is_active:
            # structure dictionary: name of line : [ 0.Structure class, 1.calc scantling class,
            # 2.calc fatigue class, 3.load object, 4.load combinations result ]

            obj_dict = {'mat_yield': [self._new_material.get()*1e6, 'Pa'],
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
                        'press_side': [self._new_pressure_side.get(), '']}

            if self._active_line not in self._line_to_struc.keys():
                self._line_to_struc[self._active_line] = [None, None, None, [None], {}]
                self._line_to_struc[self._active_line][0] = Structure(obj_dict)
                self._line_to_struc[self._active_line][1] = CalcScantlings(obj_dict)
                self._line_to_struc[self._active_line][2] = None
                if self._line_to_struc[self._active_line][0].get_structure_type() not in \
                        self._structure_types['non-wt']:
                    self._tank_dict = {}
                    self._main_grid.clear()
                    self._compartments_listbox.delete(0, 'end')

            else:
                prev_type = self._line_to_struc[self._active_line][0].get_structure_type()
                self._line_to_struc[self._active_line][0].set_main_properties(obj_dict)
                self._line_to_struc[self._active_line][1].set_main_properties(obj_dict)
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

        self.draw_prop()
        for line, obj in self._line_to_struc.items():
            obj[1].need_recalc = True

        state = self.get_color_and_calc_state()
        # except AttributeError:
        #     state = None

        self.draw_results(state=state)
        self.draw_canvas(state=state)

    def option_meny_structure_type_trace(self, event):
        ''' Updating of the values in the structure type option menu. '''

        self._new_sigma_y1.set(self._default_stresses[self._new_stucture_type.get()][0])
        self._new_sigma_y2.set(self._default_stresses[self._new_stucture_type.get()][1])
        self._new_sigma_x.set(self._default_stresses[self._new_stucture_type.get()][2])
        self._new_tauxy.set(self._default_stresses[self._new_stucture_type.get()][3])

        if self._new_stucture_type.get() in self._structure_types['vertical']:
            text = 'Vertical pressure calc.'
        elif self._new_stucture_type.get() in self._structure_types['horizontal']:
            text = 'Horizontal pressure calc.'
        elif self._new_stucture_type.get() in self._structure_types['non-wt']:
            text = text = 'Non-WT (pressure = 0)'
        elif self._new_stucture_type.get() in self._structure_types['internals']:
            text = 'Internal, pressure from comp.'
        else:
            text = ''


        self._new_stucture_type_label.set(text)

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

    def calculate_all_load_combinations_for_line(self, line, limit_state = 'ULS'):
        '''
        Calculating pressure for line.
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,1]} # DNV  loads factors
        self._load_conditions = ['loaded', 'ballast','tanktest']
        :return:
        '''
        if limit_state == 'FLS':
            return
        results = {} #dict - dnva/dnvb/tanktest/manual

        # calculating for DNV a and DNV b
        for dnv_ab in ['dnva', 'dnvb']: #, load_factors in self._load_factors_dict.items():
            results[dnv_ab] = []


            for load_condition in self._load_conditions[0:2]:
                returned = self.calculate_one_load_combination(line, dnv_ab, load_condition)
                if returned != None:
                    results[dnv_ab].append(returned)

        # calculating for tank test condition
        results['tanktest'] = []
        results['tanktest'].append(self.calculate_one_load_combination(line, "tanktest", 'tanktest'))

        # calculating for manual condition
        results['manual'] = []
        results['manual'].append(self.calculate_one_load_combination(line, 'manual', 'manual'))

        results['slamming'] = []
        results['slamming'].append(self.calculate_one_load_combination(line, 'slamming', 'slamming'))

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
            return 0
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

        current_tank = self._tank_dict['comp' + str(self._compartments_listbox.get('active'))]
        current_tank.set_overpressure(self._new_overpresure.get())
        current_tank.set_content(self._new_content_type.get())
        current_tank.set_acceleration(self._accelerations_dict)
        current_tank.set_density(self._new_density.get())

        for line, obj in self._line_to_struc.items():
            obj[1].need_recalc = True

    def delete_line(self, event = None, undo = None, line = None):
        '''
        Deleting line and line properties.
        :return:
        '''
        try:
            if line is not None:
                line = 'line'+str(line)
            else:
                line = 'line' + str(self._ent_delete_line.get())

            if line in self._line_dict.keys() or undo is not None:
                line = line if undo is None else undo
                point_str = 'p' + str(self._line_dict[line][0]) + 'p' + str(self._line_dict[line][1])
                point_str_rev = 'p' + str(self._line_dict[line][1]) + 'p' + str(self._line_dict[line][0])

                if line in self._line_dict.keys():
                    self._line_dict.pop(line)
                    if line in self._line_to_struc.keys():
                        self._line_to_struc.pop(line)
                    self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str))
                    self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str_rev))
                self.update_frame()
            else:
                messagebox.showinfo(title='No line.', message='Input line does noe exist.')

        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def delete_point(self, event = None, undo = None):
        '''
        Deleting point and connected lines.
        '''
        try:
            point = 'point' + str(self._ent_delete_point.get()) if undo is None else undo

            if point in self._point_dict.keys():
                line_to_delete = []
                # finding the lines that needs to be deleted
                for line, points in self._line_dict.items():
                    if int(self._ent_delete_point.get()) in points:
                        line_to_delete.append(line)
                # deleting the lines and the connected properties. also deleting point to point string list items.
                for line in list(line_to_delete):
                    point_str = 'p' + str(self._line_dict[line][0]) + 'p' + str(self._line_dict[line][1])
                    point_str_rev = 'p' + str(self._line_dict[line][1]) + 'p' + str(self._line_dict[line][0])
                    self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str))
                    self._line_point_to_point_string.pop(self._line_point_to_point_string.index(point_str_rev))
                    self._line_dict.pop(line)
                    # properties are deleted here
                    if line in self._line_to_struc.keys():
                        self._line_to_struc.pop(line)
                # at the en, the points is deleted from the point dict.
                self._point_dict.pop(point)
            else:
                messagebox.showinfo(title='No point.', message='Input point does not exist.')

            self.update_frame()
        except TclError:
            messagebox.showinfo(title='Input error', message='Input must be a number. Dots used not comma.')

    def delete_all_tanks(self):
        '''
        Delete the tank that has been selected in the Listbox
        :return:
        '''
        if self._grid_calc != None:
            self._tank_dict = {}
            self._compartments_listbox.delete(0,'end')
            self._main_grid.clear()
        else:
            pass

    def set_selected_variables(self, line):
        '''
        Setting the properties in the entry fields to the specified values.
        '''
        if line in self._line_to_struc:
            properties = self._line_to_struc[line][0].get_structure_prop()
            self._new_material.set(round(properties['mat_yield'][0]/1e6,5))
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

    def get_highest_pressure(self, line, limit_state = 'ULS'):
        '''
        Returning the highest pressure of a line.
        :return:
        '''
        all_press = list()
        if limit_state == 'ULS':
            pressures = self.calculate_all_load_combinations_for_line(line)
            for key, value in pressures.items():
                if key is not 'slamming':
                    all_press.append(max(value))
                else:
                    if value is not None:
                        psl = max(value)
                    else:
                        psl = 0
            return {'normal':max(all_press), 'slamming': psl}
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
        self.update_frame()
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
        self._parent.bind('<Control-p>', self.delete_point)
        self._parent.bind('<Control-l>', self.delete_line)
        self._parent.bind('<Control-c>', self.copy_point)
        self._parent.bind('<Control-m>', self.move_point)
        self._parent.bind('<Control-q>', self.new_line)
        self._parent.bind('<Control-s>', self.new_structure)

    def mouse_scroll(self,event):
        self._canvas_scale +=  event.delta/50
        self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale
        try:
            state = self.get_color_and_calc_state()
        except AttributeError:
            state = None
        self.draw_canvas(state=state)

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
        self.draw_canvas(state=state)

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

        try:
            state = self.get_color_and_calc_state()
        except AttributeError:
            state = None

        self.draw_canvas(state = state)
        self.draw_prop()
        self.draw_results(state = state)
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
                #self._pt_frame.place(x=point_coord[0] + 20, y=point_coord[1] - 120)
                #self.draw_point_frame(point_coord)
                self._new_delete_point.set(get_num(point))
                if not self._p1_p2_select:
                    self._new_line_p1.set(get_num(point))
                    self._p1_p2_select = True
                else:
                    self._new_line_p2.set(get_num(point))
                    self._p1_p2_select = False


        self.update_frame()

    def draw_point_frame(self):
        ''' Frame to define brackets on selected point. '''
        pt_canvas = tk.Canvas(self._pt_frame,height=100,width=100,background='gray60')
        pt_canvas.place(x=0, y=0)
        pt_canvas.create_oval(45,45,55,55,fill='red')
        new_left_br = tk.IntVar()
        new_right_br = tk.IntVar()
        new_upper_br = tk.IntVar()
        new_lower_br = tk.IntVar()
        wid = 5
        ent_left = tk.Entry(self._pt_frame,textvariable=new_left_br, width=wid)
        ent_right = tk.Entry(self._pt_frame, textvariable=new_right_br, width=wid)
        ent_upper = tk.Entry(self._pt_frame, textvariable=new_upper_br, width=wid)
        ent_lower = tk.Entry(self._pt_frame, textvariable=new_lower_br, width=wid)
        ent_lower.place(x=35, y=10)
        ent_upper.place(x=35, y=75)
        ent_left.place(x=5, y=40)
        ent_right.place(x=60, y=40)

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
        export_all['point_dict'] = self._point_dict
        export_all['line_dict'] = self._line_dict
        export_all['structure_properties'] = structure_properties
        export_all['load_properties'] = load_properties
        export_all['accelerations_dict'] = self._accelerations_dict
        export_all['load_combinations'] = load_combiantions
        export_all['tank_properties'] = tank_properties
        export_all['fatigue_properties'] = fatigue_properties
        json.dump(export_all, save_file)#, sort_keys=True, indent=4)
        save_file.close()

    def openfile(self, defined = None):
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

        self._point_dict = imported['point_dict']
        self._line_dict = imported['line_dict']
        struc_prop = imported['structure_properties']

        for line, lines_prop in struc_prop.items():
            self._line_to_struc[line] = [None, None, None, [], {}, [True, 'green']]
            self._line_point_to_point_string.append(
                self.make_point_point_line_string(self._line_dict[line][0], self._line_dict[line][1])[0])
            self._line_point_to_point_string.append(
                self.make_point_point_line_string(self._line_dict[line][0], self._line_dict[line][1])[1])
            self._line_to_struc[line][0] = Structure(lines_prop)
            self._line_to_struc[line][1] = CalcScantlings(lines_prop)
            if imported['fatigue_properties'][line] is not None:
                self._line_to_struc[line][2] = CalcFatigue(lines_prop, imported['fatigue_properties'][line])
            else:
                self._line_to_struc[line][2] = None

        # opening the loads
        variables = ['poly_third','poly_second', 'poly_first', 'poly_const', 'load_condition',
                     'structure_type', 'man_press', 'static_draft', 'name_of_load', 'limit_state']

        if len(imported['load_properties']) != 0:
            for load, data in imported['load_properties'].items():
                temp_dict = {}
                count_i = 0
                values = data[0]
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
                for key, value in imported['tank_properties']['search_data'].items():
                    tank_inp[int(key)] = value
                self._main_grid.bfs_search_data = tank_inp
                self._grid_calc.bfs_search_data = tank_inp
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

        imp_file.close()
        self.update_frame()

    def open_example(self):
        ''' Open the example file. To be used in help menu. '''
        if os.path.isfile('ship_section_example.txt') :
            self.openfile(defined = 'ship_section_example.txt')
        else:
            self.openfile(defined= self._root_dir + '/' + 'ship_section_example.txt')

    def on_open_structure_window(self):
        '''
        Opens the window to create structure.
        :return:
        '''
        if self._line_is_active:

            top_opt = tk.Toplevel(self._parent)
            struc.CreateStructureWindow(top_opt, self)

        else:
            messagebox.showinfo(title='Select line',message='You must select a line')

    def on_open_stresses_window(self):
        '''
        User can open a new window to stresses
        :return:
        '''

        if self._line_is_active:

            top_opt = tk.Toplevel(self._parent)
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
            top_opt = tk.Toplevel(self._parent)
            fatigue.CreateFatigueWindow(top_opt, self)


        else:
            messagebox.showinfo(title='Select line',message='You must select a line')

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

        top = tk.Toplevel(self._parent)
        load_window.CreateLoadWindow(top, self)

    def on_optimize(self):
        '''
        User open window to optimize current structure
        :return:
        '''
        if [self.get_highest_pressure(line)['normal'] for line in self._line_to_struc.keys()] == []:
            messagebox.showinfo(title='Missing something', message='Make something')
            return

        try:
            self.get_highest_pressure(self._active_line)['normal']
        except (KeyError, AttributeError):
            messagebox.showinfo(title='Missing loads/accelerations', message='Make some loads for the line.\n'+
                                                                             'Define accelerations for compartments.')
            return

        if self._line_is_active:
            if self._active_line not in self._line_to_struc:
                messagebox.showinfo(title='Missing properties', message='Specify properties for line')
            elif self._line_to_struc[self._active_line][3] == None:
                messagebox.showinfo(title='Missing loads', message='Make some loads for the line')
            else:
                top_opt = tk.Toplevel(self._parent)
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

        top_opt = tk.Toplevel(self._parent)
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
                                    'Computationally heavy! Will run for a long time.\n\n'
                                    'WEIGHT INDEX is the most important result.\n'
                                    'Results are presented for information and can not be returned to main model.\n'
                                    'Weight index will show you the span length that will give the lowest weight.\n'
                                    '\n'
                                    'A default range of T properties is chosen. Typical analysis\n'
                                    'steps (deltas) is chosen.\n'
                                    'Loads are taken from existing structure.')

        top_opt = tk.Toplevel(self._parent)
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

        if len(returned_loads) != 0:
            for load, data in returned_loads.items():
                #creating the loads objects dictionary
                self._load_dict[load] = data

            # adding values to the line dictionary. resetting first.
            for key, value in self._line_to_struc.items():
                self._line_to_struc[key][3] = []
                self._line_to_struc[key][1].need_recalc = True  # All lines need recalculations.

            for main_line in self._line_dict.keys():
                for object, load_line in self._load_dict.values():
                    if main_line in load_line:
                        self._line_to_struc[main_line][3].append(object)

        # Displaying the loads
        self.update_frame()
        # Storing the the returned data to temporary variable.
        self.__returned_load_data = [returned_loads, counter, load_comb_dict]

    def on_close_opt_window(self,returned_objects):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''
        #print(returned_objects)
        self._line_to_struc[self._active_line][0]=returned_objects[0]
        self._line_to_struc[self._active_line][1]=returned_objects[1]
        self._line_to_struc[self._active_line][1].need_recalc = True
        self.set_selected_variables(self._active_line)
        if returned_objects[2] is not None:
            self._line_to_struc[self._active_line][2] = CalcFatigue(returned_objects[0].get_structure_prop(),
                                                                    returned_objects[2])
        self.new_structure()
        self.update_frame()

    def on_close_opt_multiple_window(self, returned_objects):
        '''
        Sets the returned properties.
        :param returned_structure:
        :return:
        '''
        for line,objects in returned_objects.items():
            self._line_to_struc[line][0] = returned_objects[line][0]
            self._line_to_struc[line][0].need_recalc = True
            self._line_to_struc[line][1] = returned_objects[line][1]
            self.set_selected_variables(line)
            if returned_objects[line][2] is not None:
                self._line_to_struc[line][2] = CalcFatigue(returned_objects[line][0].get_structure_prop(),
                                                           returned_objects[line][2])
            self._active_line = line
            self.new_structure()
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
        messagebox.showinfo(title='Input error', message='ANYstructure 0.4.x'
                                                         '\n'
                                                         '\n'
                                                         'By Audun Arnesen Nyhus \n'
                                                         '2019')

if __name__ == '__main__':
    multiprocessing.freeze_support()
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    root = tk.Tk()
    my_app = Application(root)
    root.mainloop()