
import tkinter as tk
from _tkinter import TclError
from tkinter.ttk import Combobox
import ANYstructure_local.example_data as test
import os
import numpy as np
import ANYstructure_local.helper as hlp

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

            except KeyError:
                self._initial_structure_obj = None
            self._section_list = [section.__str__() for section in app._sections]
            self._section_objects = app._sections


        image_dir = os.path.dirname(__file__) + '\\images\\'
        self._opt_runned = False
        self._opt_resutls = ()
        self._draw_scale = 0.5
        self._canvas_dim = (500, 450)
        ent_w = 10
        start_x, start_y, dx, dy = 20, 70, 60, 33
        self._canvas_struc = tk.Canvas(self._frame, width=self._canvas_dim[0], height=self._canvas_dim[1],
                                       background='azure', relief='groove', borderwidth=2)
        self.structure_types = ['T','L', 'L-bulb','FB']
        self._canvas_struc.place(x=10, y=440)
        tk.Label(self._frame, text='-- Define structure properties here --', font='Verdana 15 bold').place(x=10, y=10)
        #
        # ### Adding matplotlib
        # fig, ax =  run_section_properties()# Figure(figsize=(4, 4), dpi=100)
        # t = np.arange(0, 3, .01)
        # #fig.add_subplot(111).plot(t, 2 * np.sin(2 * np.pi * t))
        #
        # canvas = FigureCanvasTkAgg(fig, master=master)  # A tk.DrawingArea.
        # canvas.draw()
        # canvas.get_tk_widget().place(x=start_x+17*dx, y=start_y+dy  )
        #
        # toolbar = NavigationToolbar2Tk(canvas, master)
        # toolbar.update()
        # canvas.get_tk_widget().place(x=start_x+17*dx, y=start_y+10*dy  )
        #
        # def on_key_press(event):
        #     print("you pressed {}".format(event.key))
        #     key_press_handler(event, canvas, toolbar)
        #
        # canvas.mpl_connect("key_press_event", on_key_press)
        
        self._new_spacing = tk.DoubleVar()
        self._new_pl_thk = tk.DoubleVar()
        self._new_web_h = tk.DoubleVar()
        self._new_web_thk = tk.DoubleVar()
        self._new_fl_w = tk.DoubleVar()
        self._new_fl_thk = tk.DoubleVar()
        self._new_stiffener_type = tk.StringVar()
        self._new_stiffener_filter = tk.StringVar()
        self._new_girder_length = tk.DoubleVar()
        self._new_section = tk.StringVar()


        self._ent_section_list = Combobox(self._frame, values = self._section_list, textvariable = self._new_section,
                                          width = 40)
        self._ent_section_list.bind("<<ComboboxSelected>>", self.section_choose)
        # self._ent_section_list = tk.OptionMenu(self._frame, self._new_section, command=self.section_choose,
        #                                        *['',] if self._section_list == [] else self._section_list)
        self._ent_structure_options = tk.OptionMenu(self._frame,self._new_stiffener_type,
                                                   command=self.option_choose,*self.structure_types)
        self._ent_filter_stf = tk.OptionMenu(self._frame,self._new_stiffener_filter,
                                                   command=self.regen_option_menu,*['No filter applied','L-bulb', 'L', 'FB', 'T'])

        self._ent_spacing = tk.Entry(self._frame, textvariable=self._new_spacing, width=ent_w)
        self._ent_pl_thk = tk.Entry(self._frame, textvariable=self._new_pl_thk, width=ent_w)
        self._ent_web_h = tk.Entry(self._frame, textvariable=self._new_web_h, width=ent_w)
        self._ent_web_thk = tk.Entry(self._frame, textvariable=self._new_web_thk, width=ent_w)
        self._ent_fl_w = tk.Entry(self._frame, textvariable=self._new_fl_w, width=ent_w)
        self._ent_fl_thk = tk.Entry(self._frame, textvariable=self._new_fl_thk, width=ent_w)
        self._ent_girder_length = tk.Entry(self._frame, textvariable=self._new_girder_length, width=ent_w)



        tk.Label(self._frame, text='Stiffener type:', font='Verdana 9 bold').place(x=start_x, y=start_y )
        tk.Label(self._frame, text='Girder length (Lg)', font='Verdana 9 bold').place(x=start_x+9*dx,
                                                                                     y=start_y + 15 * dy)
        tk.Label(self._frame, text='[m]', font='Verdana 9 bold').place(x=start_x + 14 * dx,y=start_y + 15 * dy)
        self._ent_girder_length.place(x=start_x + 12 * dx, y=start_y + 15 * dy)

        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y+dy  )
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 2*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x +3*dx, y=start_y + 3*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 4*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 5*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 6*dy)

        tk.Label(self._frame, text='Existing sections:', font='Verdana 9 bold').place(x=start_x+4*dx, y=start_y + 6*dy)
        tk.Label(self._frame, text='filter ->', font='Verdana 9 bold').place(x=start_x + 4 * dx,
                                                                                      y=start_y + 7 * dy)

        self._ent_section_list.place(x=start_x+7*dx, y=start_y + 6*dy)
        self._ent_filter_stf.place(x=start_x+5*dx, y=start_y + 7*dy)

        tk.Button(self._frame, text='Read section list from file', command=self.read_sections, font='Verdana 10 bold',
                  bg = 'blue', fg = 'yellow').place(x=start_x+12*dx, y=start_y + 6*dy)
        tk.Button(self._frame, text='Load built in sections', command=self.read_sections_built_in, font='Verdana 10 bold',
                  bg = 'azure', fg = 'black').place(x=start_x+12*dx, y=start_y + 7*dy)
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

        self._ent_structure_options.place(x=start_x + dx * 3, y=start_y)

        if self._new_spacing.get() != 0:
            tk.Label(self._frame, text='Spacing', font='Verdana 9').place(x=start_x, y=start_y + dy)
            self._ent_spacing.place(x=start_x + dx * 2, y=start_y+dy)
        if self._new_pl_thk.get() != 0:
            tk.Label(self._frame, text='Plate thk.', font='Verdana 9').place(x=start_x, y=start_y + 2 * dy)
            self._ent_pl_thk.place(x=start_x + dx * 2, y=start_y+2*dy)
        if self._new_web_h.get() != 0:
            tk.Label(self._frame, text='Web height', font='Verdana 9').place(x=start_x, y=start_y + 3 * dy)
            self._ent_web_h.place(x=start_x + dx * 2, y=start_y+3*dy)
        if self._new_web_thk.get() != 0:
            tk.Label(self._frame, text='Web thk.', font='Verdana 9').place(x=start_x, y=start_y + 4 * dy)
            self._ent_web_thk.place(x=start_x + dx * 2, y=start_y+4*dy)
        if self._new_fl_w.get() != 0:
            tk.Label(self._frame, text='Flange width', font='Verdana 9').place(x=start_x, y=start_y + 5 * dy)
            self._ent_fl_w.place(x=start_x + dx * 2, y=start_y+5*dy)
        if self._new_fl_thk.get() != 0:
            tk.Label(self._frame, text='Flange thk.', font='Verdana 9').place(x=start_x, y=start_y + 6 * dy)
            self._ent_fl_thk.place(x=start_x + dx * 2, y=start_y+6*dy)

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
            label = tk.Label(self._frame, image=photo)
            label.image = photo  # keep a reference!
            label.place(x=550, y=610)
        except TclError:
            pass
        try:
            img_file_name = 'img_T_L_FB.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path = 'images/' + img_file_name
            else:
                file_path = os.path.dirname(os.path.abspath(__file__)) + '/images/' + img_file_name
            photo_T_L_FB = tk.PhotoImage(file=file_path)
            label = tk.Label(self._frame, image=photo_T_L_FB )
            label.image = photo_T_L_FB   # keep a reference!
            label.place(x=270, y=50)
        except TclError:
            pass

        # Close and save depending on input
        # "long stf", "ring stf", "ring frame", "flat long stf"
        if self._clicked_button is not None:
            self.close_and_save = tk.Button(self._frame, text='Click to return section data to ' + self._clicked_button,
                                            command=self.save_and_close, bg='green',
                                            font='Verdana 10 bold', fg='yellow')
            self.close_and_save.place(x=start_x + dx * 9, y=start_y + dy * 12)



        self.draw_properties()

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
        start_x, start_y, dx, dy = 20, 70, 60, 33
        # self._ent_section_list = tk.OptionMenu(self._frame, self._new_section, command=self.section_choose,
        #                                        *sections)
        self._ent_section_list = Combobox(self._frame, values=sections, textvariable=self._new_section, width = 40)
        self._ent_section_list.bind("<<ComboboxSelected>>", self.section_choose)
        self._ent_section_list.place(x=start_x + 7 * dx, y=start_y + 6 * dy)

        pass

    def option_choose(self, event):
        '''
        Action when the option menu is changed.
        :param event:
        :return:
        '''
        start_x, start_y, dx, dy = 20, 70, 50, 33

        tk.Label(self._frame, text='Spacing', font='Verdana 9').place(x=start_x, y=start_y + dy)
        self._ent_spacing.place(x=start_x + dx * 2, y=start_y+dy)

        tk.Label(self._frame, text='Plate thk.', font='Verdana 9').place(x=start_x, y=start_y + 2 * dy)
        self._ent_pl_thk.place(x=start_x + dx * 2, y=start_y+2*dy)

        tk.Label(self._frame, text='Web height', font='Verdana 9').place(x=start_x, y=start_y + 3 * dy)
        self._ent_web_h.place(x=start_x + dx * 2, y=start_y+3*dy)

        tk.Label(self._frame, text='Web thk.', font='Verdana 9').place(x=start_x, y=start_y + 4 * dy)
        self._ent_web_thk.place(x=start_x + dx * 2, y=start_y+4*dy)

        if self._new_stiffener_type.get()!='FB':
            tk.Label(self._frame, text='Flange width', font='Verdana 9').place(x=start_x, y=start_y + 5 * dy)
            self._ent_fl_w.place(x=start_x + dx * 2, y=start_y+5*dy)
        else: self._ent_fl_w.place_forget()
        if self._new_stiffener_type.get()!='FB':
            tk.Label(self._frame, text='Flange thk.', font='Verdana 9').place(x=start_x, y=start_y + 6 * dy)
            self._ent_fl_thk.place(x=start_x + dx * 2, y=start_y+6*dy)
        else: self._ent_fl_thk.place_forget()
        if self._new_stiffener_type.get()=='FB':
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
        import ANYstructure_local.helper as hlp
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
        import ANYstructure_local.helper as hlp

        for section in hlp.helper_read_section_file('bulb_anglebar_tbar_flatbar.csv'):
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
