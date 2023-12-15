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

        tk.Label(self._frame, text='-- Global stresses and fixation parameter in plate/stiffener --',
                 font='Verdana 15 bold').place(x=10, y=10)

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

        self._ent_structure_type = tk.OptionMenu(self._frame,self._new_structure_type,command=self.change_option_menu,
                                                *self.default_stresses.keys())
        self._ent_trans_stress_high = tk.Entry(self._frame, textvariable=self._new_trans_stress_high, width=ent_w)
        self._ent_trans_stress_low = tk.Entry(self._frame, textvariable=self._new_trans_stress_low, width=ent_w)
        self._ent_axial_stress_1 = tk.Entry(self._frame, textvariable=self._new_axial_stress_1, width=ent_w)
        self._ent_axial_stress_2 = tk.Entry(self._frame, textvariable=self._new_axial_stress_2, width=ent_w)
        self._ent_shear_stress = tk.Entry(self._frame, textvariable=self._new_shear_stress, width=ent_w)
        self._ent_km1 = tk.Entry(self._frame, textvariable=self._new_km1, width=ent_w)
        self._ent_km2 = tk.Entry(self._frame, textvariable=self._new_km2, width=ent_w)
        self._ent_km3 = tk.Entry(self._frame, textvariable=self._new_km3, width=ent_w)
        self._ent_kpp = tk.Entry(self._frame, textvariable=self._new_kpp, width=ent_w)
        self._ent_kps = tk.Entry(self._frame, textvariable=self._new_kps, width=ent_w)
        self._ent_pressure_side = tk.OptionMenu(self._frame,self._new_max_pressure_side,*('p','s'))

        start_x,start_y,dx,dy = 20,100,100,35

        ###
        # tk.Label(self._frame, text='Input stresses and parameters:', font='Verdana 12 bold',fg='red') \
        #     .place(x=start_x , y=start_y + 9 * dy)

        tk.Label(self._frame, text='Select strucutre type:', font='Verdana 9',fg='red') \
            .place(x=start_x , y=start_y + 10 * dy)

        tk.Label(self._frame, text='Sigma,y1_Sd - large transversal stress', font='Verdana 9') \
            .place(x=start_x , y=start_y + 11 * dy)
        tk.Label(self._frame, text='[MPa]', font='Verdana 9 bold') \
            .place(x=start_x + dx * 4, y=start_y + 11 * dy)

        tk.Label(self._frame, text='Sigma,y2_Sd - small transversal stress', font='Verdana 9') \
            .place(x=start_x, y=start_y + 12* dy)
        tk.Label(self._frame, text='[MPa]', font='Verdana 9 bold') \
            .place(x=start_x + dx * 4, y=start_y + 12 * dy)

        tk.Label(self._frame, text='Sigma,x_Sd - axial stress 1', font='Verdana 9') \
            .place(x=start_x, y=start_y + 13 * dy)

        tk.Label(self._frame, text='[MPa]', font='Verdana 9 bold') \
            .place(x=start_x + dx * 4, y=start_y + 13 * dy)

        tk.Label(self._frame, text='Sigma,x_Sd - axial stress 2', font='Verdana 9') \
            .place(x=start_x, y=start_y + 14 * dy)

        tk.Label(self._frame, text='[MPa]', font='Verdana 9 bold') \
            .place(x=start_x + dx * 4, y=start_y + 14 * dy)

        tk.Label(self._frame, text='Tau,xy - shear stress', font='Verdana 9') \
            .place(x=start_x, y=start_y + 15 * dy)
        tk.Label(self._frame, text='[MPa]', font='Verdana 9 bold') \
            .place(x=start_x + dx * 4, y=start_y + 15 * dy)

        tk.Label(self._frame, text='km1, bending moment factor', font='Verdana 9') \
            .place(x=start_x, y=start_y + 16* dy)

        tk.Label(self._frame, text='km2, bending moment factor', font='Verdana 9') \
            .place(x=start_x, y=start_y + 17 * dy)

        tk.Label(self._frame, text='km3, bending moment factor', font='Verdana 9') \
            .place(x=start_x, y=start_y + 18 * dy)

        tk.Label(self._frame, text='kpp, fixation parameter plate', font='Verdana 9') \
            .place(x=start_x, y=start_y + 19 * dy)

        tk.Label(self._frame, text='kps, fixation parameter stiffener', font='Verdana 9') \
            .place(x=start_x, y=start_y + 20 * dy)

        tk.Label(self._frame, text='Max pressure side (plate of stiffener)', font='Verdana 9 bold') \
            .place(x=start_x+5*dx, y=start_y + 8 * dy)

        self._ent_structure_type.place(x=start_x + dx * 3, y=start_y + 10 * dy)
        self._ent_trans_stress_high.place(x=start_x + dx * 3, y=start_y + 11 * dy)
        self._ent_trans_stress_low.place(x=start_x + dx * 3, y=start_y + 12 * dy)
        self._ent_axial_stress_1.place(x=start_x + dx * 3, y=start_y + 13 * dy)
        self._ent_axial_stress_2.place(x=start_x + dx * 3, y=start_y + 14 * dy)
        self._ent_shear_stress.place(x=start_x + dx * 3, y=start_y + 15 * dy)
        self._ent_km1.place(x=start_x + dx * 3, y=start_y + 16 * dy)
        self._ent_km2.place(x=start_x + dx * 3, y=start_y + 17 * dy)
        self._ent_km3.place(x=start_x + dx * 3, y=start_y + 18 * dy)
        self._ent_kpp.place(x=start_x + dx * 3, y=start_y + 19 * dy)
        self._ent_kps.place(x=start_x + dx * 3, y=start_y + 20 * dy)
        self._ent_pressure_side.place(x=start_x+8*dx, y=start_y + 8 * dy)

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
        try:
            img_file_name = 'img_transverse_stress.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path ='images/' + img_file_name
            else:
                file_path = app._root_dir + '/images/' + img_file_name
            photo_transverse = tk.PhotoImage(file=file_path)
            label_trans = tk.Label(self._frame, image=photo_transverse)
            label_trans.image = photo_transverse  # keep a reference!
            label_trans.place(x=start_x, y=60)
        except TclError:
            pass

        try:
            img_file_name = "img_axial_stresses.gif"
            if os.path.isfile('images/' + img_file_name):
                file_path ='images/' + img_file_name
            else:
                file_path = app._root_dir + '/images/' + img_file_name
            photo_axial = tk.PhotoImage(file=file_path)
            label_axial = tk.Label(self._frame, image=photo_axial)
            label_axial.image = photo_axial  # keep a reference!
            label_axial.place(x=start_x+5*dx, y=60)
        except TclError:
            pass

        try:
            img_file_name = 'img_fixation_parameters.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path ='images/' + img_file_name
            else:
                file_path = app._root_dir + '/images/' + img_file_name
            photo = tk.PhotoImage(file=file_path)
            label_fix = tk.Label(self._frame, image=photo)
            label_fix.image = photo  # keep a reference!
            label_fix.place(x=start_x+9.5*dx, y=60)
        except TclError:
            pass

        tk.Label(self._frame,text='The stresses are global values and is estimated '
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
            .place(x=start_x+dx*4.5,y=start_y+dy*11)

        self._close_and_save = tk.Button(self._frame, text='Return and set stresses and fixation parameter',
                                        command=self.save_and_close, bg='green', font='Verdana 10', fg='yellow')
        self._close_and_save.place(x=start_x + dx * 4.5, y=start_y + dy * 19)

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