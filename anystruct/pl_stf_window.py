import pathlib
import tkinter as tk
from _tkinter import TclError
from tkinter.ttk import Combobox
import os

try:
    import anystruct.example_data as test
    import anystruct.helper as hlp
except ModuleNotFoundError:
    import ANYstructure.anystruct.example_data as test
    import ANYstructure.anystruct.helper as hlp


from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

class CreateStructureWindow():
    '''
    This is the tkinter GUI for defining plate/stiffener properties.
    '''
    def __init__(self, master, app):
        super(CreateStructureWindow, self).__init__()
        self._frame = master
        self._frame.wm_title("Define structure properties")
        self._frame.geometry('1800x900')
        self._frame.grab_set()
        self._root_dir = os.path.dirname(os.path.abspath(__file__))
        if __name__ == '__main__':
            self._initial_structure_obj = test.get_structure_calc_object()
            self._initial_calc_obj = test.get_structure_calc_object()

            self._section_list = []
            self._section_objects = []
            for section in hlp.helper_read_section_file('bulb_anglebar_tbar_flatbar.csv'):
                SecObj = Section(section)
                self._section_list = hlp.add_new_section(self._section_list, SecObj)
                self._section_objects.append(SecObj)
                # m = self._ent_section_list.children['menu']
                # m.add_command(label=SecObj.__str__(), command=self.section_choose)

            self._clicked_button = ["long stf", "ring stf", "ring frame", "flat long stf", 'flat stf', 'flat girder'][0]
        else:
            self.app = app
            self._clicked_button = app._clicked_section_create# if app._line_is_active else None
            try:
                if self._clicked_button in ['flat stf', "flat long stf"]:
                    self._initial_structure_obj =  self.app._line_to_struc[app._active_line][0].Stiffener
                elif self._clicked_button == 'flat girder':
                    self._initial_structure_obj = self.app._line_to_struc[app._active_line][5].Girder
                elif self._clicked_button in ["long stf"]:
                    self._initial_structure_obj =  self.app._line_to_struc[app._active_line][5].LongStfObj
                elif self._clicked_button == "ring stf":
                    self._initial_structure_obj = self.app._line_to_struc[app._active_line][5].RingStfObj
                elif self._clicked_button == "ring frame":
                    self._initial_structure_obj = self.app._line_to_struc[app._active_line][0].RingFrameObj
                else:
                    self._initial_structure_obj = None

            except (KeyError, AttributeError) as error:
                self._initial_structure_obj = None
            self._section_list = [section.__str__() for section in app._sections]
            self._section_objects = app._sections


        image_dir = os.path.dirname(__file__) + '\\images\\'
        self._opt_runned = False
        self._opt_resutls = ()
        self._draw_scale = 0.5
        self._canvas_dim = (500, 450)
        ent_w = 10
        self.structure_types = ['T','L', 'L-bulb','FB']

        # Gridded layout: title, then a content row with the dimension form on
        # the left, the section-type image in the middle and the section
        # library controls on the right.  The property canvas and panel image
        # fill the bottom row.  Same visual order as the old pixel layout.
        self._frame.columnconfigure(2, weight=1)
        self._frame.rowconfigure(3, weight=1)

        tk.Label(self._frame, text='-- Define structure properties here --', font='Verdana 15 bold') \
            .grid(row=0, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(10, 6))

        self._form_frame = tk.Frame(self._frame)
        self._form_frame.grid(row=1, column=0, sticky=tk.NW, padx=(10, 20))
        self._image_holder = tk.Frame(self._frame)
        self._image_holder.grid(row=1, column=1, sticky=tk.NW, padx=(0, 20))
        self._sections_frame = tk.Frame(self._frame)
        self._sections_frame.grid(row=1, column=2, sticky=tk.NW)

        actions_frame = tk.Frame(self._frame)
        actions_frame.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=10, pady=8)

        self._canvas_struc = tk.Canvas(self._frame, width=self._canvas_dim[0], height=self._canvas_dim[1],
                                       background='azure', relief='groove', borderwidth=2)
        self._canvas_struc.grid(row=3, column=0, columnspan=2, sticky=tk.NW, padx=10, pady=(0, 10))
        self._panel_image_holder = tk.Frame(self._frame)
        self._panel_image_holder.grid(row=3, column=2, sticky=tk.NW, pady=(0, 10))

        self._new_spacing = tk.DoubleVar()
        self._new_pl_thk = tk.DoubleVar()
        self._new_web_h = tk.DoubleVar()
        self._new_web_thk = tk.DoubleVar()
        self._new_fl_w = tk.DoubleVar()
        self._new_fl_thk = tk.DoubleVar()
        self._new_stiffener_type = tk.StringVar()
        self._new_stiffener_filter = tk.StringVar()
        self._new_stiffener_filter.set('No filter applied')
        self._new_girder_length = tk.DoubleVar()
        self._new_section = tk.StringVar()


        self._ent_section_list = Combobox(self._sections_frame, values = self._section_list,
                                          textvariable = self._new_section, width = 40)
        self._ent_section_list.bind("<<ComboboxSelected>>", self.section_choose)
        self._ent_structure_options = tk.OptionMenu(self._form_frame,self._new_stiffener_type,
                                                   command=self.option_choose,*self.structure_types)
        self._ent_filter_stf = tk.OptionMenu(self._sections_frame,self._new_stiffener_filter,
                                                   command=self.regen_option_menu,*['No filter applied','L-bulb', 'L', 'FB', 'T'])

        self._ent_spacing = tk.Entry(self._form_frame, textvariable=self._new_spacing, width=ent_w)
        self._ent_pl_thk = tk.Entry(self._form_frame, textvariable=self._new_pl_thk, width=ent_w)
        self._ent_web_h = tk.Entry(self._form_frame, textvariable=self._new_web_h, width=ent_w)
        self._ent_web_thk = tk.Entry(self._form_frame, textvariable=self._new_web_thk, width=ent_w)
        self._ent_fl_w = tk.Entry(self._form_frame, textvariable=self._new_fl_w, width=ent_w)
        self._ent_fl_thk = tk.Entry(self._form_frame, textvariable=self._new_fl_thk, width=ent_w)
        self._ent_girder_length = tk.Entry(actions_frame, textvariable=self._new_girder_length, width=ent_w)

        tk.Label(self._form_frame, text='Stiffener type:', font='Verdana 9 bold') \
            .grid(row=0, column=0, sticky=tk.W, pady=2)
        self._ent_structure_options.grid(row=0, column=1, sticky=tk.W, padx=(8, 4), pady=2)

        # Dimension rows are created once and toggled with grid/grid_remove
        # (the old code re-created labels on every type change, which left
        # stale flange labels visible for flat bars).
        self._dim_rows = {}
        for offset, (key, text, entry) in enumerate((
                ('spacing', 'Spacing', self._ent_spacing),
                ('pl_thk', 'Plate thk.', self._ent_pl_thk),
                ('web_h', 'Web height', self._ent_web_h),
                ('web_thk', 'Web thk.', self._ent_web_thk),
                ('fl_w', 'Flange width', self._ent_fl_w),
                ('fl_thk', 'Flange thk.', self._ent_fl_thk),
        )):
            label = tk.Label(self._form_frame, text=text, font='Verdana 9')
            label.grid(row=1 + offset, column=0, sticky=tk.W, pady=2)
            entry.grid(row=1 + offset, column=1, sticky=tk.W, padx=(8, 4), pady=2)
            unit = tk.Label(self._form_frame, text='[mm]', font='Verdana 9 bold')
            unit.grid(row=1 + offset, column=2, sticky=tk.W, pady=2)
            self._dim_rows[key] = (label, entry, unit)

        tk.Label(self._sections_frame, text='Existing sections:', font='Verdana 9 bold') \
            .grid(row=0, column=0, sticky=tk.W, pady=2)
        self._ent_section_list.grid(row=0, column=1, sticky=tk.W, padx=8, pady=2)
        tk.Label(self._sections_frame, text='filter ->', font='Verdana 9 bold') \
            .grid(row=1, column=0, sticky=tk.E, pady=2)
        self._ent_filter_stf.grid(row=1, column=1, sticky=tk.W, padx=8, pady=2)

        tk.Button(self._sections_frame, text='Read section list from file', command=self.read_sections,
                  font='Verdana 10 bold', bg = 'blue', fg = 'yellow').grid(row=0, column=2, sticky=tk.EW, padx=8, pady=2)
        tk.Button(self._sections_frame, text='Load built in sections', command=self.read_sections_built_in,
                  font='Verdana 10 bold', bg = 'azure', fg = 'black').grid(row=1, column=2, sticky=tk.EW, padx=8, pady=2)

        tk.Label(actions_frame, text='Girder length (Lg)', font='Verdana 9 bold').grid(row=0, column=0, sticky=tk.W)
        self._ent_girder_length.grid(row=0, column=1, sticky=tk.W, padx=8)
        tk.Label(actions_frame, text='[m]', font='Verdana 9 bold').grid(row=0, column=2, sticky=tk.W)
        # setting default values
        init_dim,init_thk = 0.05,0.002

        if self._initial_structure_obj != None:
            self._new_stiffener_type.set(self._initial_structure_obj.get_stiffener_type())
            self._new_spacing.set(self._initial_structure_obj.get_s()*1000)
            self._new_pl_thk.set(self._initial_structure_obj.get_pl_thk()*1000)
            self._new_web_h.set(self._initial_structure_obj.get_web_h()*1000)
            self._new_web_thk.set(self._initial_structure_obj.get_web_thk()*1000)
            self._new_fl_w.set(self._initial_structure_obj.get_fl_w()*1000)
            self._new_fl_thk.set(self._initial_structure_obj.get_fl_thk()*1000)
        else:
            self._new_spacing.set(0)
            self._new_pl_thk.set(0)
            self._new_web_h.set(0)
            self._new_web_thk.set(0)
            self._new_fl_w.set(0)
            self._new_fl_thk.set(0)

        self._new_girder_length.set(10)

        # Only dimension rows with a value are shown initially, mirroring the
        # old behaviour; choosing a stiffener type shows the relevant rows.
        self._set_dim_row_visible('spacing', self._new_spacing.get() != 0)
        self._set_dim_row_visible('pl_thk', self._new_pl_thk.get() != 0)
        self._set_dim_row_visible('web_h', self._new_web_h.get() != 0)
        self._set_dim_row_visible('web_thk', self._new_web_thk.get() != 0)
        self._set_dim_row_visible('fl_w', self._new_fl_w.get() != 0)
        self._set_dim_row_visible('fl_thk', self._new_fl_thk.get() != 0)

        self._new_spacing.trace('w',self.draw_trace)
        self._new_pl_thk.trace('w',self.draw_trace)
        self._new_web_h.trace('w',self.draw_trace)
        self._new_web_thk.trace('w',self.draw_trace)
        self._new_fl_w.trace('w',self.draw_trace)
        self._new_fl_thk.trace('w',self.draw_trace)
        try:
            img_file_name = 'img_stiffened_plate_panel.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            label = tk.Label(self._panel_image_holder, image=photo)
            label.image = photo  # keep a reference!
            label.grid(row=0, column=0, sticky=tk.NW)
        except TclError:
            pass
        try:
            img_file_name = 'img_T_L_FB.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            photo_T_L_FB = tk.PhotoImage(file=file_path)
            label = tk.Label(self._image_holder, image=photo_T_L_FB )
            label.image = photo_T_L_FB   # keep a reference!
            label.grid(row=0, column=0, sticky=tk.NW)
        except TclError:
            pass

        # Close and save depending on input
        # "long stf", "ring stf", "ring frame", "flat long stf"
        if self._clicked_button is not None:
            self.close_and_save = tk.Button(actions_frame, text='Click to return section data to ' + self._clicked_button,
                                            command=self.save_and_close, bg='green',
                                            font='Verdana 10 bold', fg='yellow')
            self.close_and_save.grid(row=0, column=3, sticky=tk.W, padx=(30, 0))



        self.draw_properties()

    def _set_dim_row_visible(self, key, visible):
        '''Show or hide one dimension row (label, entry, unit) in the form grid.'''
        for widget in self._dim_rows[key]:
            if visible:
                widget.grid()
            else:
                widget.grid_remove()

    def regen_option_menu(self, event = None):
        self._ent_section_list.destroy()
        sections =  []
        if self._section_list == []:
            sections = ['',]
        elif self._new_stiffener_filter.get() == 'No filter applied':
            sections = self._section_list
        else:
            for sec_obj in self._section_objects:
                if sec_obj.stf_type == self._new_stiffener_filter.get():
                    sections.append(sec_obj.__str__())
        self._ent_section_list = Combobox(self._sections_frame, values=sections, textvariable=self._new_section,
                                          width = 40)
        self._ent_section_list.bind("<<ComboboxSelected>>", self.section_choose)
        self._ent_section_list.grid(row=0, column=1, sticky=tk.W, padx=8, pady=2)

    def option_choose(self, event):
        '''
        Action when the option menu is changed.
        :param event:
        :return:
        '''
        for key in ('spacing', 'pl_thk', 'web_h', 'web_thk'):
            self._set_dim_row_visible(key, True)
        has_flange = self._new_stiffener_type.get() != 'FB'
        self._set_dim_row_visible('fl_w', has_flange)
        self._set_dim_row_visible('fl_thk', has_flange)
        if not has_flange:
            self._new_fl_w.set(0)
            self._new_fl_thk.set(0)
        self.draw_properties()

    def checkered(self, line_distance):
        '''
        Grid lines in the properties canvas.
        :param line_distance: 
        :return: 
        '''
        # vertical lines at an interval of "line_distance" pixel
        for x in range(line_distance, self._canvas_dim[0], line_distance):
            self._canvas_struc.create_line(x, 0, x, self._canvas_dim[0], fill="grey", stipple='gray50')
        # horizontal lines at an interval of "line_distance" pixel
        for y in range(line_distance, self._canvas_dim[1], line_distance):
            self._canvas_struc.create_line(0, y, self._canvas_dim[0], y, fill="grey", stipple='gray50')

    def draw_properties(self):
        '''
        Drawing properties in the canvas.
        :return:
        '''
        self._canvas_struc.delete('all')
        self.checkered(10)
        ctr_x = self._canvas_dim[0] / 2
        ctr_y = self._canvas_dim[1] / 2 + 200
        m = self._draw_scale
        init_color, init_stipple = 'blue', 'gray50'

        try: spacing = self._new_spacing.get() 
        except TclError: spacing = 0
        try: pl_thk = self._new_pl_thk.get() 
        except TclError: pl_thk = 0        
        try: web_h = self._new_web_h.get()
        except TclError: web_h = 0
        try: web_thk = self._new_web_thk.get()
        except TclError: web_thk = 0
        try: fl_w = self._new_fl_w.get() 
        except TclError: fl_w = 0
        try: fl_thk = self._new_fl_thk.get()
        except TclError: fl_thk = 0

        self._canvas_struc.create_rectangle(0, 0, self._canvas_dim[0] + 10, 70, fill='white')

        self._canvas_struc.create_text(250, 15, text='Plate: ' + str(spacing ) + 'x' +
                                                    str(pl_thk ),font='Verdana 10 bold',fill='black')
        self._canvas_struc.create_rectangle(ctr_x - m * spacing / 2, ctr_y,ctr_x + m * spacing / 2,
                                           ctr_y - m * pl_thk, fill='black', stipple=init_stipple)

        self._canvas_struc.create_text(250, 35, text='Web: ' + str(web_h ) + 'x'+ str(web_thk )
                                  ,font='Verdana 10 bold',fill='blue')
        self._canvas_struc.create_rectangle(ctr_x - m * web_thk / 2,ctr_y - m * pl_thk,ctr_x + m * web_thk / 2,
                                           ctr_y - m * (web_h+ pl_thk), fill='blue', stipple=init_stipple)

        self._canvas_struc.create_text(250, 55, text='Flange: '+ str(fl_w ) + 'x'+ str(fl_thk ),
                                  font='Verdana 10 bold',fill='red')
        if self._new_stiffener_type.get() in ['L', 'L-bulb']:
            self._canvas_struc.create_rectangle(ctr_x - m * web_thk / 2, ctr_y- m * (pl_thk + web_h),ctr_x + m * fl_w,
                                               ctr_y - m * (pl_thk + web_h + fl_thk),fill='red', stipple=init_stipple)
        else:
            self._canvas_struc.create_rectangle(ctr_x - m * fl_w / 2, ctr_y- m * (pl_thk + web_h),ctr_x + m * fl_w / 2,
                                               ctr_y - m * (pl_thk + web_h + fl_thk),fill='red', stipple=init_stipple)

    def draw_trace(self,*args):
        '''
        Updating when values in entered
        :param event:
        :return:
        '''
        self.draw_properties()

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''
        if __name__ == '__main__':
            self._frame.destroy()
            return

        self.app.on_close_structure_window([float(num) for num in [self._new_spacing.get(),self._new_pl_thk.get(),
                                                                   self._new_web_h.get(),self._new_web_thk.get(),
                                                                   self._new_fl_w.get(),self._new_fl_thk.get()]] +
                                           [self._new_stiffener_type.get(), self._clicked_button])
        self._frame.destroy()

    def section_choose(self, event = None):
        ''' Choosing a section. '''
        #chosen_section = self._new_section.get()
        chosen_section = event.widget.get()
        for section in self._section_objects:
            if chosen_section == section.__str__():
                self._new_web_h.set(section.stf_web_height*1000)
                self._new_web_thk.set(section.stf_web_thk*1000)
                self._new_fl_w.set(section.stf_flange_width*1000)
                self._new_fl_thk.set(section.stf_flange_thk*1000)
                self._new_stiffener_type.set(section.stf_type)
        self.option_choose(None)

    def read_sections(self):
        '''
        Read a list.
        '''
        from tkinter import filedialog
        import anystruct.helper as hlp
        from pathlib import Path

        file = filedialog.askopenfile('r')
        file = Path(file.name)
        #m = self._ent_section_list.children['menu']

        for section in hlp.helper_read_section_file(file.name):
            SecObj = Section(section)
            self._section_list = hlp.add_new_section(self._section_list, SecObj)
            self._section_objects.append(SecObj)
            #m.add_command(label=SecObj.__str__(), command=self.section_choose)

    def read_sections_built_in(self):
        '''
        Read a list.
        '''
        import anystruct.helper as hlp
        if pathlib.Path('bulb_anglebar_tbar_flatbar.csv').exists():
            libfile = 'bulb_anglebar_tbar_flatbar.csv'
        else:
            libfile = 'bulb_anglebar_tbar_flatbar.csv'
            libfile = self._root_dir + '/' + libfile
        for section in hlp.helper_read_section_file(libfile):
            SecObj = Section(section)
            self._section_list = hlp.add_new_section(self._section_list, SecObj)
            self._section_objects.append(SecObj)
            #m.add_command(label=SecObj.__str__(), command=self.section_choose)

        self.regen_option_menu()

class Section:
    '''
    Creates a section property.
    'stf_type': [self._new_stf_type.get(), ''],
    'stf_web_height': [self._new_stf_web_h.get()/1000, 'm'],
    'stf_web_thk': [self._new_sft_web_t.get()/1000, 'm'],
    'stf_flange_width': [self._new_stf_fl_w.get()/1000, 'm'],
    'stf_flange_thk': [self._new_stf_fl_t.get()/1000, 'm'],
    '''
    def __init__(self, input_dict):
        super(Section, self).__init__()
        self._stf_type = input_dict['stf_type'] if type(input_dict['stf_type']) != list \
            else input_dict['stf_type'][0]
        self._stf_web_height = input_dict['stf_web_height']if type(input_dict['stf_web_height']) != list \
            else input_dict['stf_web_height'][0]
        self._stf_web_thk = input_dict['stf_web_thk']if type(input_dict['stf_web_thk']) != list \
            else input_dict['stf_web_thk'][0]
        self._stf_flange_width = input_dict['stf_flange_width']if type(input_dict['stf_flange_width']) != list \
            else input_dict['stf_flange_width'][0]
        self._stf_flange_thk = input_dict['stf_flange_thk']if type(input_dict['stf_flange_thk']) != list \
            else input_dict['stf_flange_thk'][0]

    def __str__(self):
        ''' Returning a string. '''
        base_name = self.stf_type+ '_' + str(round(self.stf_web_height*1000, 0)) + 'x' + \
                   str(round(self.stf_web_thk*1000, 0))
        if self._stf_type == 'FB':
            ret_str = base_name
        elif self._stf_type in ['L-bulb', 'bulb', 'hp']:
            ret_str = 'Bulb'+str(int(self.stf_web_height*1000 + self.stf_flange_thk*1000))+'x'+\
                      str(round(self.stf_web_thk*1000, 0))+ '__' +str(round(self.stf_web_height*1000, 0)) + 'x' + \
                   str(round(self.stf_web_thk*1000, 0))+ str(round(self.stf_flange_width*1000, 0)) + 'x' + \
                      str(round(self.stf_flange_thk*1000, 0))
        else:
            ret_str = base_name + '__' + str(round(self.stf_flange_width*1000, 0)) + 'x' + \
                      str(round(self.stf_flange_thk*1000, 0))

        ret_str = ret_str.replace('.', '_')

        return ret_str


    @property
    def stf_type(self):
        return self._stf_type

    @stf_type.setter
    def stf_type(self, value):
        self._stf_type = value

    @property
    def stf_web_height(self):
        return self._stf_web_height

    @stf_web_height.setter
    def stf_web_height(self, value):
        self._stf_web_height = value

    @property
    def stf_web_thk(self):
        return self._stf_web_thk

    @stf_web_thk.setter
    def stf_web_thk(self, value):
        self._stf_web_thk = value

    @property
    def stf_flange_width(self):
        return self._stf_flange_width

    @stf_flange_width.setter
    def stf_flange_width(self, value):
        self._stf_flange_width = value

    @property
    def stf_flange_thk(self):
        return self._stf_flange_thk

    @stf_flange_thk.setter
    def stf_flange_thk(self, value):
        self._stf_flange_thk = value

    def return_puls_input(self):
        '''
        Returns as input good for PULS
        :return:
        '''
        return {'Stiffener type (L,T,F)': self.stf_type,  'Stiffener boundary': 'C',
                'Stiff. Height': self.stf_web_height*1000,
                   'Web thick.': self.stf_web_thk*1000, 'Flange width': self.stf_flange_width*1000,
                          'Flange thick.': self.stf_flange_thk*1000}

# def run_section_properties(pl_s = 0.75, pl_t = 0.015, hw = 0.4, tw = 0.018, bf = 0.15, tf = 0.02):
#     import sectionproperties.pre.sections as sections
#     from sectionproperties.analysis.cross_section import CrossSection
#     from matplotlib import pyplot as plt
#
#     # create a 50 diameter circle discretised by 64 points
#     geometry = sections.MonoISection(
#         d=(pl_t+hw+tf)*1000, b_t=bf*1000, b_b=pl_s*1000, t_ft=tf*1000, t_fb=pl_t*1000, t_w=tw*1000, r=8, n_r=16
#     )
#     mesh = geometry.create_mesh(mesh_sizes=[3.0])
#     section = CrossSection(geometry, mesh)  # create a CrossSection object
#     mesh_nodes = section.mesh_nodes
#     mesh_elements = section.mesh_elements
#     # plot the mesh
#     (fig, ax) = plt.subplots(figsize=(4, 4), dpi=100)
#     ax.triplot(mesh_nodes[:, 0], mesh_nodes[:, 1], mesh_elements[:, 0:3], lw=0.5)
#     # #section.display_mesh_info()  # display the mesh information
#     # ax = section.plot_mesh(pause=True)  # plot the generated mesh
#     #
#     # # perform a geometric, warping and plastic analysis, displaying the time info
#     # section.calculate_geometric_properties(time_info=True)
#     # section.calculate_warping_properties(time_info=True)
#     # section.calculate_plastic_properties(time_info=True)
#     #
#     # # print the results to the terminal
#     # section.display_results()
#     #
#     # # get the second moments of area and the torsion constant
#     # (ixx_c, iyy_c, ixy_c) = section.get_ic()
#     # j = section.get_j()
#     #
#     # # print the sum of the second moments of area and the torsion constant
#     # print("Ixx + Iyy = {0:.3f}".format(ixx_c + iyy_c))
#     # print("J = {0:.3f}".format(j))
#     return fig, ax
#
#



if __name__ == '__main__':

    # sec1 = Section({'stf_type': 'T', 'stf_web_height': 0.35, 'stf_web_thk': 0.02, 'stf_flange_width': 0.15,
    #                 'stf_flange_thk': 0.015})
    #
    # sec_list = [sec1, Section({'stf_type': 'FB', 'stf_web_height': 0.35, 'stf_web_thk': 0.02, 'stf_flange_width': 0,
    #                 'stf_flange_thk': 0}), Section({'stf_type': 'T', 'stf_web_height': 0.4, 'stf_web_thk': 0.02,
    #                                                     'stf_flange_width': 0.15, 'stf_flange_thk': 0.02})]
    #
    # hlp.add_new_section(sec_list, sec1)
    # run_section_properties()
    root = tk.Tk()
    my_app = CreateStructureWindow(root, app=None)
    root.mainloop()
