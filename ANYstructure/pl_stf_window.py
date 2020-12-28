
import tkinter as tk
from _tkinter import TclError
import ANYstructure.example_data as test
import os

class CreateStructureWindow():
    '''
    This is the tkinter GUI for defining plate/stiffener properties.
    '''
    def __init__(self, master, app):
        super(CreateStructureWindow, self).__init__()
        self._frame = master
        self._frame.wm_title("Define structure properties")
        self._frame.geometry('1000x800')
        self._frame.grab_set()
        if __name__ == '__main__':
            self._initial_structure_obj = test.get_structure_calc_object()
            self._initial_calc_obj = test.get_structure_calc_object()
            self._section_objects = test.get_section_list()
            self._section_list = [section.__str__() for section in test.get_section_list()]
        else:
            self.app = app
            try:
                self._initial_structure_obj =  self.app._line_to_struc[app._active_line][0]
            except KeyError:
                self._initial_structure_obj = None
            self._section_list = [section.__str__() for section in app._sections]
            self._section_objects = app._sections
        image_dir = os.path.dirname(__file__) + '\\images\\'
        self._opt_runned = False
        self._opt_resutls = ()
        self._draw_scale = 0.5
        self._canvas_dim = (500, 450)
        self._canvas_struc = tk.Canvas(self._frame, width=self._canvas_dim[0], height=self._canvas_dim[1],
                                       background='azure', relief='groove', borderwidth=2)
        self.structure_types = ['T','L','FB']
        self._canvas_struc.place(x=10, y=300)
        tk.Label(self._frame, text='-- Define structure properties here --', font='Verdana 15 bold').place(x=10, y=10)
        
        self._new_spacing = tk.DoubleVar()
        self._new_pl_thk = tk.DoubleVar()
        self._new_web_h = tk.DoubleVar()
        self._new_web_thk = tk.DoubleVar()
        self._new_fl_w = tk.DoubleVar()
        self._new_fl_thk = tk.DoubleVar()
        self._new_stiffener_type = tk.StringVar()
        self._new_girder_length = tk.DoubleVar()
        self._new_section = tk.StringVar()

        # TODO this may cause error when there is no list.
        self._ent_section_list = tk.OptionMenu(self._frame, self._new_section, command=self.section_choose,
                                               *['',] if self._section_list == [] else self._section_list)
        self._ent_structure_options = tk.OptionMenu(self._frame,self._new_stiffener_type,
                                                   command=self.option_choose,*self.structure_types)
        ent_w = 10
        self._ent_spacing = tk.Entry(self._frame, textvariable=self._new_spacing, width=ent_w)
        self._ent_pl_thk = tk.Entry(self._frame, textvariable=self._new_pl_thk, width=ent_w)
        self._ent_web_h = tk.Entry(self._frame, textvariable=self._new_web_h, width=ent_w)
        self._ent_web_thk = tk.Entry(self._frame, textvariable=self._new_web_thk, width=ent_w)
        self._ent_fl_w = tk.Entry(self._frame, textvariable=self._new_fl_w, width=ent_w)
        self._ent_fl_thk = tk.Entry(self._frame, textvariable=self._new_fl_thk, width=ent_w)
        self._ent_girder_length = tk.Entry(self._frame, textvariable=self._new_girder_length, width=ent_w)

        start_x,start_y,dx,dy = 20,70,60,33

        tk.Label(self._frame, text='Stiffener type:', font='Verdana 9 bold').place(x=start_x, y=start_y )
        tk.Label(self._frame, text='Girder length (Lg)', font='Verdana 9 bold').place(x=start_x+11*dx,
                                                                                     y=start_y + 16 * dy)
        tk.Label(self._frame, text='[m]', font='Verdana 9 bold').place(x=start_x + 17 * dx,y=start_y + 16 * dy)

        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y+dy  )
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 2*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x +3*dx, y=start_y + 3*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 4*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 5*dy)
        tk.Label(self._frame, text='[mm]', font='Verdana 9 bold').place(x=start_x+3*dx, y=start_y + 6*dy)

        tk.Label(self._frame, text='Existing sections:', font='Verdana 9 bold').place(x=start_x+4*dx, y=start_y + 6*dy)

        self._ent_section_list.place(x=start_x+7*dx, y=start_y + 6*dy)

        tk.Button(self._frame, text='Read section list', command=self.read_sections, font='Verdana 10 bold',
                  bg = 'blue', fg = 'yellow').place(x=start_x+12*dx, y=start_y + 6*dy)
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

        self._ent_girder_length.place(x=start_x+15*dx, y=start_y + 16 * dy)

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
            label.place(x=550, y=300)
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

        self.close_and_save = tk.Button(self._frame, text='Save and return structure',
                                        command=self.save_and_close, bg='green', font='Verdana 10 bold', fg='yellow')
        self.close_and_save.place(x=start_x + dx * 12, y=start_y + dy * 20)



        self.draw_properties()

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
        if self._new_stiffener_type.get()=='L':
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

        self.app.on_close_structure_window([self._new_spacing.get(),self._new_pl_thk.get(),
                                                                 self._new_web_h.get(),
                                            self._new_web_thk.get(),self._new_fl_w.get(),self._new_fl_thk.get(),
                                            self._new_stiffener_type.get()])
        self._frame.destroy()

    def section_choose(self, event = None):
        ''' Choosing a section. '''
        chosen_section = self._new_section.get()
        # TODO en feil her.AttributeError: 'NoneType' object has no attribute 'name'. Seksjoner vises ikke riktig i neddroppsmeny.
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
        import ANYstructure.helper as hlp
        from pathlib import Path

        file = filedialog.askopenfile('r')
        file = Path(file.name)
        m = self._ent_section_list.children['menu']

        for section in hlp.helper_read_section_file(file.name):
            SecObj = Section(section)
            self._section_list = hlp.add_new_section(self._section_list, SecObj)
            self._section_objects.append(SecObj)
            m.add_command(label=SecObj.__str__(), command=self.section_choose)

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


if __name__ == '__main__':

    # sec1 = Section({'stf_type': 'T', 'stf_web_height': 0.35, 'stf_web_thk': 0.02, 'stf_flange_width': 0.15,
    #                 'stf_flange_thk': 0.015})
    #
    # sec_list = [sec1, Section({'stf_type': 'FB', 'stf_web_height': 0.35, 'stf_web_thk': 0.02, 'stf_flange_width': 0,
    #                 'stf_flange_thk': 0}), Section({'stf_type': 'T', 'stf_web_height': 0.4, 'stf_web_thk': 0.02,
    #                                                     'stf_flange_width': 0.15, 'stf_flange_thk': 0.02})]
    #
    # hlp.add_new_section(sec_list, sec1)

    root = tk.Tk()
    my_app = CreateStructureWindow(root, app=None)
    root.mainloop()
