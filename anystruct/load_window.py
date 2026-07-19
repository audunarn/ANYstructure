import anystruct.example_data as test
from anystruct.calc_loads import *
from anystruct.helper import *

# try:
#     import anystruct.example_data as test
#     from anystruct.calc_loads import *
#     from anystruct.helper import *
# except ModuleNotFoundError:
#     import ANYstructure.anystruct.example_data as test
#     from ANYstructure.anystruct.calc_loads import *
#     from ANYstructure.anystruct.helper import *

import tkinter as tk
from tkinter import messagebox



class CreateLoadWindow():
    '''
    This class defines the external pressures on the hull (static and dynamic).
    '''
    @staticmethod
    def return_dummy_manual(line):
        load = 'manual'
        combination = 'manual'
        load_comb_dict = {}
        load_comb_dict[(combination, line, load)] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
        load_comb_dict[(combination, line, load)][0].set(0)
        load_comb_dict[(combination, line, load)][1].set(1)
        load_comb_dict[(combination, line, load)][2].set(1)
        return load_comb_dict

    def __init__(self, master,app=None):

        super(CreateLoadWindow, self).__init__()

        limit_states = ['ULS', 'FLS']
        if __name__ == '__main__':
            options_cond = ['loaded', 'ballast', 'tanktest', 'part', 'slamming']
            self._load_factors_dict = {'dnva': [1.3, 1.2, 0.7], 'dnvb': [1, 1, 1.3], 'tanktest': [1, 1, 0]}
            self._load_objects = {}
            self._load_comb_dict = {}
            self._line_dict = test.get_line_dict()
            self._load_count = 0
            self._slamming_load_count = 0
            self._point_dict = test.get_point_dict()
            self._canvas_scale = 20
            self._structure_types = {'vertical': ['BBS', 'SIDE_SHELL', 'SSS'],
                                     'horizontal': ['BOTTOM', 'BBT', 'HOPPER', 'MD']}

        else:
            self.app = app
            self._load_factors_dict = app._load_factors_dict
            options_cond = app._load_conditions
            self._load_objects = app._load_dict
            self._load_comb_dict = app._new_load_comb_dict
            self._line_dict = app._line_dict
            self._load_count = 0
            self._point_dict = app._point_dict
            self._canvas_scale = app._canvas_scale
            self._structure_types = app._structure_types
            self._slamming_load_count = 0

        self._point_is_active = False
        self._active_point = ''
        self._point_is_active = False
        self._active_lines = []
        self._add_to_lines = True
        self._lines_add_to_load = []

        listbox_select = 'extended'
        frame_dim = (1500,980)
        self._canvas_origo = (50,720-50)
        self._canvas_dim = (1000,720)

        self._frame = master
        self._frame.wm_title("Load properties")
        self._frame.geometry(str(frame_dim[0])+'x'+str(frame_dim[1]))
        self._frame.grab_set()

        self._frame.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Gridded layout: left column holds the dynamic-load form, created
        # loads and the load-property canvas; the right column holds the
        # static/slamming/save row on top, then the line-association row and
        # the main line canvas with its zoom slider.  Frame borders replace
        # the old hand-placed black divider strips.
        options_cond = tuple(options_cond)
        self._frame.columnconfigure(1, weight=1)
        self._frame.rowconfigure(2, weight=1)

        left_top = tk.Frame(self._frame, relief='groove', borderwidth=1)
        left_top.grid(row=0, column=0, rowspan=2, sticky=tk.NSEW, padx=(8, 4), pady=(8, 4))
        left_loads = tk.Frame(self._frame, relief='groove', borderwidth=1)
        left_loads.grid(row=2, column=0, sticky=tk.NSEW, padx=(8, 4), pady=4)
        left_props = tk.Frame(self._frame)
        left_props.grid(row=3, column=0, sticky=tk.NW, padx=(8, 4), pady=(4, 8))

        top_right = tk.Frame(self._frame)
        top_right.grid(row=0, column=1, sticky=tk.NW, padx=(4, 8), pady=(8, 4))
        assoc_row = tk.Frame(self._frame)
        assoc_row.grid(row=1, column=1, sticky=tk.EW, padx=(4, 8), pady=2)
        canvas_area = tk.Frame(self._frame)
        canvas_area.grid(row=2, column=1, rowspan=2, sticky=tk.NSEW, padx=(4, 8), pady=(2, 8))

        static_frame = tk.Frame(top_right, relief='groove', borderwidth=1)
        static_frame.grid(row=0, column=0, sticky=tk.NW, padx=(0, 8))
        slamming_frame = tk.Frame(top_right, relief='groove', borderwidth=1)
        slamming_frame.grid(row=0, column=1, sticky=tk.NW, padx=8)

        # Main canvas creation
        self._main_canvas = tk.Canvas(canvas_area,width=self._canvas_dim[0], height=self._canvas_dim[1],
                                     background='azure', relief = 'groove', borderwidth=2)
        self._global_shrink = 1
        base_canvas_dim = [1000, 720]  # do not modify this, sets the "orignal" canvas dimensions.
        self._canvas_dim = [int(base_canvas_dim[0] *self._global_shrink),
                           int(base_canvas_dim[1] *self._global_shrink)]
        self._canvas_base_origo = [50, base_canvas_dim[1] - 50] # 50 bottom left location of the canvas, (0,0)
        self._canvas_draw_origo = list(self._canvas_base_origo)
        self._previous_drag_mouse = list(self._canvas_draw_origo)

        # --- slider (used to zoom) ----
        self._slider = tk.Scale(canvas_area,from_=60,to = 1, command = self.slider_used,
                               background='azure', relief = 'groove', borderwidth=2)
        self._slider.set(self._canvas_scale)
        self._slider.grid(row=0, column=0, sticky=tk.NS, padx=(0, 4))
        self._main_canvas.grid(row=0, column=1, sticky=tk.NSEW)
        canvas_area.columnconfigure(1, weight=1)
        canvas_area.rowconfigure(0, weight=1)

        # --- Dynamic load input ---
        tk.Label(left_top, text='1. Dynamic loads', font='Verdana 10 bold', fg = 'red')\
            .grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=6, pady=(6, 0))
        tk.Label(left_top, text='Define dynamic loads as an polynominal curve.\n'
                                  'Can be third degree, second degree, linear or constant \n'
,
                 font="Verdana 8 bold",justify = tk.LEFT).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=6)

        tk.Button(left_top, text='Create dynamic load',  command=self.create_dynamic_load_object,
                  font='Verdana 9 bold', fg='yellow', bg = 'green' )\
            .grid(row=9, column=1, sticky=tk.W, padx=6, pady=(4, 6))

        self.close_window= tk.Button(top_right, text='Press this to: \n'
                                                      'Save loads and \n'
                                                      'close the load window. ',font="Verdana 9 bold",
                                     command=self.save_and_close, bg = 'green', fg = 'yellow')
        self.close_window.grid(row=0, column=2, sticky=tk.NW, padx=8)

        self._new_dynamic_load_name = tk.StringVar()
        self._new_dynamic_load_name.set('load' + str(self._load_count))
        self._new_load_poly_third = tk.DoubleVar()
        self._new_load_poly_second = tk.DoubleVar()
        self._new_load_poly_first = tk.DoubleVar()
        self._new_load_poly_const = tk.DoubleVar()
        self._new_load_manual_pressure = tk.DoubleVar()
        self._new_dyn_load_condition = tk.StringVar()
        self._new_limit_state = tk.StringVar()
        self._new_limit_state.set('ULS')
        self._new_slamming_pressure = tk.DoubleVar()
        self._new_slamming_pressure_name = tk.StringVar()
        self._new_slamming_pressure_name.set('slamming')
        self._new_slamming_pl_mult = tk.DoubleVar()
        self._new_slamming_stf_mult = tk.DoubleVar()
        self._new_slamming_pl_mult.set(1.0)
        self._new_slamming_stf_mult.set(1.0)

        ent_w = 15
        ent_dyn_load_name = tk.Entry(left_top, textvariable=self._new_dynamic_load_name, width=ent_w*2)
        ent_load_poly_third = tk.Entry(left_top, textvariable=self._new_load_poly_third, width=ent_w)
        ent_load_poly_second = tk.Entry(left_top, textvariable=self._new_load_poly_second, width=ent_w)
        ent_load_poly_first = tk.Entry(left_top, textvariable=self._new_load_poly_first,width=ent_w)
        ent_load_poly_constant = tk.Entry(left_top, textvariable=self._new_load_poly_const,width=ent_w)
        ent_load_condition = tk.OptionMenu(left_top, self._new_dyn_load_condition, *options_cond)
        ent_limit_state = tk.OptionMenu(left_top, self._new_limit_state, *limit_states)

        for offset, (text, widget) in enumerate((
                ('Input load name:', ent_dyn_load_name),
                ('Third degree poly [x^3]', ent_load_poly_third),
                ('Second degree poly [x^2]', ent_load_poly_second),
                ('First degree poly [x]', ent_load_poly_first),
                ('Constant [C]', ent_load_poly_constant),
                ('Load condition', ent_load_condition),
                ('Limit state', ent_limit_state),
        )):
            tk.Label(left_top, text=text).grid(row=2 + offset, column=0, sticky=tk.W, padx=6, pady=1)
            widget.grid(row=2 + offset, column=1, sticky=tk.W, padx=(4, 6), pady=1)

        # Slamming pressures
        tk.Label(slamming_frame, text='3. Slamming pressure', font='Verdana 10 bold', fg = 'red') \
            .grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=6, pady=(6, 2))
        ent_slamming_pressure = tk.Entry(slamming_frame, textvariable=self._new_slamming_pressure, width=ent_w)
        ent_slamming_pl_mult = tk.Entry(slamming_frame, textvariable=self._new_slamming_pl_mult, width=7)
        ent_slamming_stf_mult = tk.Entry(slamming_frame, textvariable=self._new_slamming_stf_mult, width=7)
        ent_slamming_pressure_name = tk.Entry(slamming_frame, textvariable=self._new_slamming_pressure_name,
                                              width=ent_w)
        for offset, (text, widget) in enumerate((
                ('Load name:', ent_slamming_pressure_name),
                ('Pressure [Pa]:', ent_slamming_pressure),
                ('Plate multiplier, Ppl', ent_slamming_pl_mult),
                ('Stiffener multiplier, Pst:', ent_slamming_stf_mult),
        )):
            tk.Label(slamming_frame, text=text).grid(row=1 + offset, column=0, sticky=tk.W, padx=6, pady=1)
            widget.grid(row=1 + offset, column=1, sticky=tk.W, padx=(4, 6), pady=1)
        tk.Button(slamming_frame, text = 'Create slamming load', command = self.create_slamming_load,
                  font='Verdana 9 bold', fg='yellow', bg = 'green' ) \
            .grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=6, pady=(4, 6))

        # --- Static load input ---
        tk.Label(static_frame, text='2. Static loads', font='Verdana 10 bold', fg = 'red') \
            .grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=6, pady=(6, 2))
        tk.Label(static_frame, text = 'Hydrostatic loads defined by draft.',
                 font="Verdana 8 bold").grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=6)

        self._new_static_load_name = tk.StringVar()
        self._new_static_draft = tk.DoubleVar()
        self._new_static_condition = tk.StringVar()
        self._new_static_load_name.set('static'+str(self._load_count))

        tk.Label(static_frame, text='Define name of static load:').grid(row=2, column=0, sticky=tk.W, padx=6, pady=1)
        tk.Entry(static_frame, textvariable = self._new_static_load_name,width=ent_w)\
            .grid(row=2, column=1, sticky=tk.W, padx=(4, 6), pady=1)
        tk.Label(static_frame, text = 'Define static draft from sea [m]:')\
            .grid(row=3, column=0, sticky=tk.W, padx=6, pady=1)
        tk.Entry(static_frame, textvariable = self._new_static_draft,width=ent_w)\
            .grid(row=3, column=1, sticky=tk.W, padx=(4, 6), pady=1)
        tk.Label(static_frame, text='Select load condition:').grid(row=4, column=0, sticky=tk.W, padx=6, pady=1)
        tk.OptionMenu(static_frame, self._new_static_condition, *options_cond)\
            .grid(row=4, column=1, sticky=tk.W, padx=(4, 6), pady=1)
        tk.Button(static_frame, text = 'Create static load', command = self.create_static_load_object,
                  font='Verdana 9 bold', fg='yellow', bg = 'green' )\
            .grid(row=2, column=2, rowspan=2, sticky=tk.NW, padx=6, pady=1)

        # --- showing created loads ---
        tk.Label(left_loads, text='3. Created loads are seen below\n'
                                   '(scroll if not all is shown.)\n'
                                   'DOUBLE CLICK load to see assosiated lines.:',
                 font="Verdana 10 bold", fg='red', justify=tk.LEFT)\
            .grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=6, pady=(6, 2))
        tk.Label(left_loads, text = 'Select to see assosiated lines: ')\
            .grid(row=1, column=0, columnspan=4, sticky=tk.W, padx=6)
        self._load_obj_box = tk.Listbox(left_loads, height = 15, selectmode = listbox_select, bg='azure',
                                       relief = 'groove', borderwidth=2)
        self._load_obj_box.grid(row=2, column=0, sticky=tk.NSEW, padx=(6, 0), pady=2)
        self._load_obj_box.bind('<<ListboxSelect>>', self.left_click_load_box)
        loads_scrollbar = tk.Scrollbar(left_loads)
        loads_scrollbar.config(command = self._load_obj_box.yview)
        loads_scrollbar.grid(row=2, column=1, sticky=tk.NS, pady=2)
        self._load_obj_box.config(yscrollcommand=loads_scrollbar.set)

        # --- showing the lines applied to the load above ---
        self._load_obj_lines_box = tk.Listbox(left_loads, height = 15, selectmode = listbox_select, bg = 'azure',
                                             relief = 'groove', borderwidth=2)
        lines_scrollbar = tk.Scrollbar(left_loads)
        lines_scrollbar.config(command = self._load_obj_lines_box.yview)
        self._load_obj_lines_box.config(yscrollcommand=lines_scrollbar.set)
        self._load_obj_lines_box.grid(row=2, column=2, sticky=tk.NSEW, padx=(12, 0), pady=2)
        lines_scrollbar.grid(row=2, column=3, sticky=tk.NS, pady=2)
        self._load_obj_lines_box.bind('<<ListboxSelect>>', self.left_click_load_box)

        # --- dropdown meny to choose load to assosiate with lines ---
        self._load_options = ['']
        self._new_assisiate_load = tk.StringVar()
        self._assoc_dropdown_holder = assoc_row
        self._ent_assosiate_load = tk.OptionMenu(assoc_row, self._new_assisiate_load, *tuple(self._load_options))
        self._ent_assosiate_load.grid(row=0, column=2, sticky=tk.W, padx=8)

        # --- Button to assosiate selecte lines to load
        tk.Button(assoc_row, text = 'Press to add selected lines to selected load',
                  command=self.append_line_to_load, fg = 'yellow', bg='green',font='Verdana 9 bold')\
            .grid(row=0, column=0, sticky=tk.W)
        tk.Label(assoc_row,text='Select a load in "3." and then choose lines to apply to load\n '
                                 '(select by clicking lines). Alternatively define manually ------>')\
            .grid(row=0, column=1, sticky=tk.W, padx=12)

        # --- delete a created load ---
        tk.Button(left_loads, text="Delete selected load",command=self.delete_load,
                  font='Verdana 9 bold', fg='yellow', bg = 'red' )\
            .grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=6, pady=(4, 6))

        # --- updating the imported loads from main window ---
        if len(self._load_objects) > 0:
            self.import_update()

        # --- properties canvas to show variables for load ---
        self._canvas_properties = tk.Canvas(left_props, height=200, width=350,
                                           background='azure', relief = 'groove', borderwidth=2)
        self._canvas_properties.grid(row=0, column=0, sticky=tk.NW)

        self.controls()
        self.draw_canvas()

    def delete_load(self):
        self._load_objects.pop(self._load_obj_box.get('active'))
        self._load_obj_box.delete('active')

    def slider_used(self, event):
        '''
        Action when slider is activated.
        :return:
        '''
        self._canvas_scale = self._slider.get()
        self.draw_canvas()

    def draw_canvas(self, load_selected=False):
        '''
        Making the line canvas
        :return:
        '''
        self._main_canvas.delete('all')

        # grid for the canavs

        self._main_canvas.create_line(self._canvas_draw_origo[0], 0, self._canvas_draw_origo[0], self._canvas_dim[1],
                                     stipple='gray50')
        self._main_canvas.create_line(0, self._canvas_draw_origo[1], self._canvas_dim[0], self._canvas_draw_origo[1],
                                     stipple='gray50')
        self._main_canvas.create_text(self._canvas_draw_origo[0] - 30 ,
                                     self._canvas_draw_origo[1] + 20 , text='(0,0)',
                                     font='Text 10')
        self._main_canvas.create_text([800 ,50],
                                     text='Mouse left click:  select lines to loads\n'
                                          'Mouse right click: clear all selection\n'
                                          'Shift key press: add selected line\n'
                                          'Control key press: remove selected line', font='Verdana 8 bold',
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
                    self._main_canvas.create_line(coord1, coord2, width=6, fill='orange')
                    self._main_canvas.create_text(coord1[0] + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 + 10,
                                                 text='Line ' + str(get_num(line)), font='Verdand 10 bold',
                                                 fill='red')
                else:
                    self._main_canvas.create_line(coord1, coord2, width=3, fill=color)
                    self._main_canvas.create_text(coord1[0] - 20 + vector[0] / 2 + 5, coord1[1] + vector[1] / 2 + 10,
                                                 text='line' + str(get_num(line)), font="Text 8", fill='black')

    def button_2_click_and_drag(self,event):

        self._canvas_draw_origo = (self._canvas_draw_origo[0]-(self._previous_drag_mouse[0]-event.x),
                                  self._canvas_draw_origo[1]-(self._previous_drag_mouse[1]-event.y))

        self._previous_drag_mouse = (event.x,event.y)
        self.draw_canvas()

    def mouse_scroll(self,event):
        self._canvas_scale +=  event.delta/50
        self._canvas_scale = 0 if self._canvas_scale < 0 else self._canvas_scale

        self.draw_canvas()

    def get_loads(self):
        '''
        Returning loads
        :return:
        '''
        return self._load_objects

    def make_load_comb_dict(self, line, load):
        '''
        Making the load comb dict
        (comb,line,load) : [DoubleVar(),DoubleVar(), IntVar()] #
        # {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,1]} # DNV  loads factors
        :return:
        '''

        for combination in self._load_factors_dict.keys():
            factors =self._load_factors_dict[combination]
            if load != 'manual':# and (combination, line, load) not in self._load_comb_dict.keys():
                #print(combination, line, load)
                self._load_comb_dict[(combination, line, load)] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
                if combination != 'tanktest':
                    if self._load_objects[load][0].is_static():
                        if self._load_objects[load][0].get_limit_state() == 'FLS':
                            self._load_comb_dict[(combination, line, load)][0].set(0)
                        elif self._load_objects[load][0].is_tank_test():
                            self._load_comb_dict[(combination, line, load)][0].set(0)
                            self._load_comb_dict[(combination, line, load)][2].set(0)
                        else:
                            self._load_comb_dict[(combination, line, load)][0].set(factors[0])
                            self._load_comb_dict[(combination, line, load)][2].set(1)
                        self._load_comb_dict[(combination, line, load)][1].set(0)

                    else:
                        self._load_comb_dict[(combination, line, load)][0].set(0)
                        if self._load_objects[load][0].get_limit_state() == 'FLS':
                            self._load_comb_dict[(combination, line, load)][1].set(1)
                        else:
                            self._load_comb_dict[(combination, line, load)][1].set(factors[2])
                        self._load_comb_dict[(combination, line, load)][2].set(1)
                else:
                    if self._load_objects[load][0].is_tank_test():
                        self._load_comb_dict[(combination, line, load)][0].set(1)
                        self._load_comb_dict[(combination, line, load)][1].set(0)
                        self._load_comb_dict[(combination, line, load)][2].set(1)
                    else:
                        self._load_comb_dict[(combination, line, load)][0].set(0)
                        self._load_comb_dict[(combination, line, load)][1].set(0)
                        self._load_comb_dict[(combination, line, load)][2].set(0)
            else:
                combination = 'manual'
                self._load_comb_dict[(combination, line, load)] = [tk.DoubleVar(), tk.DoubleVar(), tk.IntVar()]
                self._load_comb_dict[(combination, line, load)][0].set(0)
                self._load_comb_dict[(combination, line, load)][1].set(1)
                self._load_comb_dict[(combination, line, load)][2].set(1)

    def create_dynamic_load_object(self, slamming_load = False):
        '''
        Creating load object for the selected lines.
        '(poly_third = None,poly_second = None, poly_first = None, poly_const = None
        , load_condition = None, structure_type = None, man_press = None, static_draft = None)'
        :return:
        '''

        variables = ['poly_third','poly_second', 'poly_first', 'poly_const', 'load_condition',
                     'man_press', 'static_draft', 'name_of_load', 'limit_state', 'structure_types',
                     'slamming mult pl', 'slamming mult stf']
        existing_load = None
        if not slamming_load:
            name_of_load = self._new_dynamic_load_name.get()
            if name_of_load in self._load_objects.keys():
                # Existing load
                existing_load = copy.deepcopy(self._load_objects[name_of_load])
                self._load_objects.pop(name_of_load)
                self._load_obj_box.delete(0,'end')
                for load in self._load_objects.keys():
                    self._load_obj_box.insert('end', load)

            values = [self._new_load_poly_third.get(),self._new_load_poly_second.get(),
                      self._new_load_poly_first.get(),self._new_load_poly_const.get(),
                      self._new_dyn_load_condition.get(), None, None, name_of_load,
                      self._new_limit_state.get(), self._structure_types, 1, 1]
        else:
            name_of_load = self._new_slamming_pressure_name.get()
            if name_of_load in self._load_objects.keys():
                existing_load = copy.deepcopy(self._load_objects[name_of_load])
                self._load_objects.pop(name_of_load)
                self._load_obj_box.delete(0, 'end')
                for load in self._load_objects.keys():
                    self._load_obj_box.insert('end', load)

            values = [0, 0, 0, self._new_slamming_pressure.get(),
                      'slamming', None, None, name_of_load,
                      None, self._structure_types,
                      self._new_slamming_pl_mult.get(),
                      self._new_slamming_stf_mult.get()]

        count_i = 0
        current_load_dict = {}
        for item in variables:
            current_load_dict[item] = values[count_i]
            count_i += 1

        self._load_objects[name_of_load] = [Loads(current_load_dict),[] if existing_load is None else existing_load[1]]
        self._load_options.append(name_of_load)
        self._ent_assosiate_load.destroy()
        self._ent_assosiate_load = tk.OptionMenu(self._assoc_dropdown_holder, self._new_assisiate_load,
                                                 *tuple(self._load_options))
        self._ent_assosiate_load.grid(row=0, column=2, sticky=tk.W, padx=8)
        self._load_obj_box.insert('end',name_of_load)
        if not slamming_load:
            self._load_count += 1
            self._new_dynamic_load_name.set('load'+str(self._load_count))
        else:
            self._new_slamming_pressure_name.set('slamming' + str(self._slamming_load_count))
            self._slamming_load_count += 1

    def create_slamming_load(self):
        ''' Creates a slamming load object. '''
        self.create_dynamic_load_object(slamming_load=True)

    def create_static_load_object(self):
        '''
        Creating static loads.
        '(poly_third = None,poly_second = None, poly_first = None, poly_const = None
        , load_condition = None, structure_type = None, man_press = None, static_draft = None)'
        :return:
        '''
        variables = ['poly_third','poly_second', 'poly_first', 'poly_const', 'load_condition',
                     'structure_type', 'man_press', 'static_draft','name_of_load']

        name_of_load = self._new_static_load_name.get()
        existing_load = None

        if name_of_load in self._load_objects.keys():
            existing_load = copy.deepcopy(self._load_objects[name_of_load])
            self._load_objects.pop(name_of_load)
            self._load_obj_box.delete(0,'end')
            for load in self._load_objects.keys():
                self._load_obj_box.insert('end', load)

        values = [None,None,None,None,self._new_static_condition.get(),None,None,
                  self._new_static_draft.get(), name_of_load]

        count_i = 0
        current_load_dict = {}

        for item in variables:
            current_load_dict[item] = values[count_i]
            count_i += 1

        self._load_objects[name_of_load] = [Loads(current_load_dict),[] if existing_load is None else existing_load[1]]

        self._load_options.append(name_of_load)
        self._ent_assosiate_load.destroy()
        self._ent_assosiate_load = tk.OptionMenu(self._assoc_dropdown_holder, self._new_assisiate_load,
                                                 *tuple(self._load_options))
        self._ent_assosiate_load.grid(row=0, column=2, sticky=tk.W, padx=8)

        self._load_obj_box.insert('end', name_of_load)
        self._load_count += 1
        self._new_static_load_name.set('static' + str(self._load_count))

    def append_line_to_load(self):
        '''
        Specifying lines for the load
        :return:
        '''

        current_load = self._new_assisiate_load.get()
        if current_load != '':
            self._load_objects[current_load][1] = []
            for line in self._active_lines:
                #if line not in self._load_objects[current_load][1]:
                self._load_objects[current_load][1].append(line)
        else:
            mess = tk.messagebox.showwarning('Select load',message='Select a load to apply to the selected lines.',
                                             type='ok')

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''
        if __name__ == '__main__':
            self._frame.destroy()
            return

        for load, data in self._load_objects.items():
            for line in data[1]:
                self.make_load_comb_dict(line,load)

        for line in self.app._line_dict.keys():
            self.make_load_comb_dict(line,'manual')
        if self._load_objects is not None:

            self.app.on_close_load_window(self._load_objects, self._load_count, self._load_comb_dict)
        self._frame.destroy()

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
        '''

        point_coord_x = self._canvas_draw_origo[0] + self._point_dict[point_no][0] * self._canvas_scale
        point_coord_y = self._canvas_draw_origo[1] - self._point_dict[point_no][1] * self._canvas_scale

        return [point_coord_x, point_coord_y]

    def controls(self):
        '''
        Specifying the controls to be used.
        :return:
        '''
        self._main_canvas.bind('<Button-1>', self.left_click)
        self._main_canvas.bind('<Button-2>', self.button_2_click)
        self._main_canvas.bind('<Button-3>', self.right_click)
        self._load_obj_box.bind('<Button-1>', self.left_click_load_box)
        self._frame.bind('<Shift_L>', self.shift_pressed)
        self._frame.bind('<Shift_R>', self.shift_pressed)
        self._frame.bind('<Control_L>', self.ctrl_pressed)
        self._frame.bind('<Control_R>', self.ctrl_pressed)
        self._main_canvas.bind("<MouseWheel>", self.mouse_scroll)
        self._main_canvas.bind("<B2-Motion>", self.button_2_click_and_drag)

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

    def button_2_click(self, event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
        self._previous_drag_mouse = [event.x, event.y]

    def left_click(self, event):
        '''
        When clicking the right button, this method is called.
        method is referenced in
        '''
        self._previous_drag_mouse = [event.x, event.y]
        click_x = self._main_canvas.winfo_pointerx() - self._main_canvas.winfo_rootx()
        click_y = self._main_canvas.winfo_pointery() - self._main_canvas.winfo_rooty()
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
                            self._active_lines.append(key)
                        elif self._add_to_lines== False:
                            if key in self._active_lines:
                                self._active_lines.remove(key)
                        self._main_canvas.delete('all')
                        break
        self.draw_canvas()

    def right_click(self,event):
        '''
        Event when right click.
        :param evnet:
        :return:
        '''
        self._previous_drag_mouse = [event.x, event.y]
        self._active_lines = []
        self._main_canvas.delete('all')
        self.draw_canvas()

    def left_click_load_box(self, *event):
        '''
        Load boxes consist of self._load_obj_box (active/non-active) and self._load_obj_lines_box (listing assosiated
         lines). Both is tkinter ListBox objects.
        :param events:
        :return:
        '''
        self._load_obj_lines_box.delete(0,'end')
        self._active_lines = []

        if len(self._load_objects)!=0:
            self._canvas_properties.delete('all')
            current_selection = self._load_obj_box.get('active')
            current_object = self._load_objects[current_selection][0]
            current_lines = self._load_objects[current_selection][1]
            self._new_assisiate_load.set(current_selection)

            # drawing properties in the canvas
            self._canvas_properties.create_text([140, 100], text=self._load_objects[current_selection][0])

            for line in sorted([get_num(line) for line in current_lines]):
                self._load_obj_lines_box.insert('end','line'+str(line))
                self._active_lines.append('line'+str(line))

            if current_object.is_static():
                self._new_static_load_name.set(current_object.get_load_parmeters()[8])
                self._new_static_draft.set(current_object.get_load_parmeters()[7])
                self._new_static_condition.set(current_object.get_load_parmeters()[4])
            else:
                self._new_dynamic_load_name.set(current_object.get_load_parmeters()[8])
                self._new_load_poly_third.set(current_object.get_load_parmeters()[0])
                self._new_load_poly_second.set(current_object.get_load_parmeters()[1])
                self._new_load_poly_first.set(current_object.get_load_parmeters()[2])
                self._new_load_poly_const.set(current_object.get_load_parmeters()[3])
                self._new_load_manual_pressure.set(current_object.get_load_parmeters()[6])
                self._new_dyn_load_condition.set(current_object.get_load_parmeters()[4])
                self._new_limit_state.set(current_object.get_load_parmeters()[9])

            if current_object.get_load_parmeters()[4] == 'slamming':
                self._new_slamming_pressure.set(current_object.get_load_parmeters()[3])
                self._new_slamming_pressure_name.set(current_object.get_load_parmeters()[8])
                self._new_slamming_pl_mult.set(current_object.get_load_parmeters()[10])
                self._new_slamming_stf_mult.set(current_object.get_load_parmeters()[11])

            self._load_obj_box.update()
            self._ent_assosiate_load.update_idletasks()
            self.draw_canvas(load_selected=True)

    def import_update(self):

        for load, data in self._load_objects.items():
            self._load_obj_box.insert('end', load)
            self._load_options.append(load)

        self._ent_assosiate_load.destroy()
        self._ent_assosiate_load = tk.OptionMenu(self._assoc_dropdown_holder, self._new_assisiate_load,
                                                 *tuple(self._load_options))
        self._ent_assosiate_load.grid(row=0, column=2, sticky=tk.W, padx=8)

if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateLoadWindow(master=root)
    root.mainloop()