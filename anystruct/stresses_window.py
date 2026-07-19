# This is where the optimization is done.
import tkinter as tk

from _tkinter import TclError
import os
try:
    import anystruct.example_data as test
except ModuleNotFoundError:
    import ANYstructure.anystruct.example_data as test


class CreateStressesWindow():
    '''
    This class initiates the GUI used to define stresses for the selected structure.
    '''
    def __init__(self, master, app=None):
        super(CreateStressesWindow, self).__init__()
        if __name__ == '__main__':
            self._initial_structure_obj = test.get_structure_object()
            self.default_stresses = test.get_default_stresses()
            image_dir = os.path.dirname(__file__) + '\\images\\'
        else:
            self.app = app
            try:
                self._initial_structure_obj = app._line_to_struc[app._active_line][0]
            except KeyError:
                self._initial_structure_obj = None
            self.default_stresses = app._default_stresses
            image_dir = app._root_dir + '\\images\\'

        self._frame = master
        self._frame.wm_title("Specify strucutre - returned to input field in main window")
        self._frame.geometry('1500x900')
        self._frame.grab_set()

        self._opt_runned = False
        self._opt_resutls = ()

        self._draw_scale = 500
        self._canvas_dim = (500, 450)

        # Gridded layout: title, reference images, pressure-side row, then the
        # input form on the left with guidance text and the save button on the
        # right.  Same visual order as the old fixed-pixel layout.
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(3, weight=1)

        tk.Label(self._frame, text='-- Global stresses and fixation parameter in plate/stiffener --',
                 font='Verdana 15 bold').grid(row=0, column=0, sticky=tk.W, padx=10, pady=(10, 4))

        self._images_row = tk.Frame(self._frame)
        self._images_row.grid(row=1, column=0, sticky=tk.W, padx=10, pady=(0, 4))
        pressure_row = tk.Frame(self._frame)
        pressure_row.grid(row=2, column=0, sticky=tk.W, padx=10, pady=(0, 4))
        content = tk.Frame(self._frame)
        content.grid(row=3, column=0, sticky=tk.NSEW, padx=10, pady=(0, 10))
        content.columnconfigure(3, weight=1)

        ent_w = 10
        # stresses in plate and stiffener

        self._new_structure_type = tk.StringVar()
        self._new_trans_stress_high = tk.DoubleVar()
        self._new_trans_stress_low = tk.DoubleVar()
        self._new_axial_stress_1 = tk.DoubleVar()
        self._new_axial_stress_2 = tk.DoubleVar()
        self._new_shear_stress = tk.DoubleVar()
        self._new_km1 = tk.DoubleVar()
        self._new_km2 = tk.DoubleVar()
        self._new_km3 = tk.DoubleVar()
        self._new_kpp = tk.DoubleVar()
        self._new_kps = tk.DoubleVar()
        self._new_max_pressure_side = tk.StringVar()

        self._ent_structure_type = tk.OptionMenu(content,self._new_structure_type,command=self.change_option_menu,
                                                *self.default_stresses.keys())
        self._ent_trans_stress_high = tk.Entry(content, textvariable=self._new_trans_stress_high, width=ent_w)
        self._ent_trans_stress_low = tk.Entry(content, textvariable=self._new_trans_stress_low, width=ent_w)
        self._ent_axial_stress_1 = tk.Entry(content, textvariable=self._new_axial_stress_1, width=ent_w)
        self._ent_axial_stress_2 = tk.Entry(content, textvariable=self._new_axial_stress_2, width=ent_w)
        self._ent_shear_stress = tk.Entry(content, textvariable=self._new_shear_stress, width=ent_w)
        self._ent_km1 = tk.Entry(content, textvariable=self._new_km1, width=ent_w)
        self._ent_km2 = tk.Entry(content, textvariable=self._new_km2, width=ent_w)
        self._ent_km3 = tk.Entry(content, textvariable=self._new_km3, width=ent_w)
        self._ent_kpp = tk.Entry(content, textvariable=self._new_kpp, width=ent_w)
        self._ent_kps = tk.Entry(content, textvariable=self._new_kps, width=ent_w)
        self._ent_pressure_side = tk.OptionMenu(pressure_row,self._new_max_pressure_side,*('p','s'))

        tk.Label(pressure_row, text='Max pressure side (plate of stiffener)', font='Verdana 9 bold') \
            .grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self._ent_pressure_side.grid(row=0, column=1, sticky=tk.W)

        form_rows = (
            ('Select strucutre type:', self._ent_structure_type, '', 'Verdana 9', 'red'),
            ('Sigma,y1_Sd - large transversal stress', self._ent_trans_stress_high, '[MPa]', 'Verdana 9', None),
            ('Sigma,y2_Sd - small transversal stress', self._ent_trans_stress_low, '[MPa]', 'Verdana 9', None),
            ('Sigma,x_Sd - axial stress 1', self._ent_axial_stress_1, '[MPa]', 'Verdana 9', None),
            ('Sigma,x_Sd - axial stress 2', self._ent_axial_stress_2, '[MPa]', 'Verdana 9', None),
            ('Tau,xy - shear stress', self._ent_shear_stress, '[MPa]', 'Verdana 9', None),
            ('km1, bending moment factor', self._ent_km1, '', 'Verdana 9', None),
            ('km2, bending moment factor', self._ent_km2, '', 'Verdana 9', None),
            ('km3, bending moment factor', self._ent_km3, '', 'Verdana 9', None),
            ('kpp, fixation parameter plate', self._ent_kpp, '', 'Verdana 9', None),
            ('kps, fixation parameter stiffener', self._ent_kps, '', 'Verdana 9', None),
        )
        for row, (label, widget, unit, font, colour) in enumerate(form_rows):
            options = {'font': font}
            if colour:
                options['fg'] = colour
            tk.Label(content, text=label, **options).grid(row=row, column=0, sticky=tk.W, pady=2)
            widget.grid(row=row, column=1, sticky=tk.W, padx=(12, 4), pady=2)
            if unit:
                tk.Label(content, text=unit, font='Verdana 9 bold').grid(row=row, column=2, sticky=tk.W, pady=2)

        # setting default values
        init_dim = 0.05
        init_thk = 0.002

        if self._initial_structure_obj != None:
            self._new_trans_stress_high.set(self._initial_structure_obj.Plate.sigma_y1)
            self._new_trans_stress_low.set(self._initial_structure_obj.Plate.sigma_y2)
            self._new_axial_stress_1.set(self._initial_structure_obj.Plate.sigma_x1)
            self._new_axial_stress_2.set(self._initial_structure_obj.Plate.sigma_x2)
            self._new_shear_stress.set(self._initial_structure_obj.Plate.tau_xy)
            self._new_km1.set(self._initial_structure_obj.Plate.get_km1())
            self._new_km2.set(self._initial_structure_obj.Plate.get_km2())
            self._new_km3.set(self._initial_structure_obj.Plate.get_km3())
            self._new_kpp.set(self._initial_structure_obj.Plate.get_kpp())
            self._new_kps.set(self._initial_structure_obj.Plate.get_kps())
            self._new_structure_type.set(self._initial_structure_obj.Plate.get_structure_type())

        else:
            self._new_structure_type.set('GENERAL_INTERNAL_WT')
            self._new_trans_stress_high.set(self.default_stresses[self._new_structure_type.get()][0])
            self._new_trans_stress_low.set(self.default_stresses[self._new_structure_type.get()][1])
            self._new_axial_stress_1.set(self.default_stresses[self._new_structure_type.get()][2])
            self._new_axial_stress_1.set(self.default_stresses[self._new_structure_type.get()][3])
            self._new_shear_stress.set(self.default_stresses[self._new_structure_type.get()][4])
            self._new_km1.set(12)
            self._new_km2.set(24)
            self._new_km3.set(12)
            self._new_kpp.set(1)
            self._new_kps.set(1)
            self._new_max_pressure_side.set('p')
        for image_column, img_file_name in enumerate(
                ('img_transverse_stress.gif', 'img_axial_stresses.gif', 'img_fixation_parameters.gif')):
            try:
                if os.path.isfile('images/' + img_file_name):
                    file_path = 'images/' + img_file_name
                else:
                    file_path = app._root_dir + '/images/' + img_file_name
                photo = tk.PhotoImage(file=file_path)
                image_label = tk.Label(self._images_row, image=photo)
                image_label.image = photo  # keep a reference!
                image_label.grid(row=0, column=image_column, sticky=tk.NW, padx=(0, 12))
            except TclError:
                pass

        side_panel = tk.Frame(content)
        side_panel.grid(row=0, column=3, rowspan=len(form_rows), sticky=tk.NW, padx=(30, 0))
        tk.Label(side_panel,text='The stresses are global values and is estimated '
                                 '\nby user.\n'
                                 'Alterntively read out stresses from FE-model.\n'
                                 'Suggestions for input:\n'
                                 'Transverse stresses (Sigma,y_Sd is calculated):\n'
                                 '   - conservative - about 100 MPa \n'
                                 '   - non-conservative - about 60 MPa\n'
                                 'Axial stresses: \n'
                                 '   - about 60 MPa\n'
                                 '   - non-conservative - about 40 MPa\n'
                                 'Shear stresses: \n'
                                 '   - about 20 MPa\n'
                                 '   - non-conservative - about 1 MPa', justify=tk.LEFT,
                 font = 'Verdana 10', fg = 'blue',bg='white')\
            .grid(row=0, column=0, sticky=tk.NW)

        self._close_and_save = tk.Button(side_panel, text='Return and set stresses and fixation parameter',
                                        command=self.save_and_close, bg='green', font='Verdana 10', fg='yellow')
        self._close_and_save.grid(row=1, column=0, sticky=tk.W, pady=(14, 0))

    def change_option_menu(self,event):
        '''
        Action when changing the structure type
        :return:
        '''
        self._new_trans_stress_high.set(self.default_stresses[self._new_structure_type.get()][0])
        self._new_trans_stress_low.set(self.default_stresses[self._new_structure_type.get()][1])
        self._new_axial_stress_1.set(self.default_stresses[self._new_structure_type.get()][2])
        self._new_axial_stress_1.set(self.default_stresses[self._new_structure_type.get()][3])
        self._new_shear_stress.set(self.default_stresses[self._new_structure_type.get()][4])

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''
        if __name__ == '__main__':
            self._frame.destroy()
            return

        self.app.on_close_stresses_window([self._new_trans_stress_high.get(),
                                           self._new_trans_stress_low.get(),
                                           self._new_axial_stress_1.get(),
                                           self._new_axial_stress_2.get(),
                                           self._new_shear_stress.get(),
                                           self._new_km1.get(),
                                           self._new_km2.get(),
                                           self._new_km3.get(),
                                           self._new_kpp.get(),
                                           self._new_kps.get(),
                                           self._new_structure_type.get(),
                                           self._new_max_pressure_side.get()])
        self._frame.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateStressesWindow(root,app=None)
    root.mainloop()