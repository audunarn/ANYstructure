# This is fatigue properties are defined.
import tkinter as tk

try:
    import any_files.example_data as test
    import any_files.SN_curve_parameters as sn
except ModuleNotFoundError:
    import ANYstructure.any_files.example_data as test
    import ANYstructure.any_files.SN_curve_parameters as sn


class CreateFatigueWindow():
    '''
    This class initiates the GUI used to define stresses for the selected structure.
    '''
    def __init__(self, master, app=None):
        super(CreateFatigueWindow, self).__init__()
        if __name__ == '__main__':
            self._initial_structure_obj = test.get_structure_object()
            self.load_objects = [test.get_loa_fls_load(),test.get_loa_uls_load(),
                                 test.get_bal_fls_load(), test.get_bal_uls_load()]
            self.active_line = 'line1'
            points = test.line_dict['line1']
            coords = (test.point_dict['point'+str(points[0])], test.point_dict['point'+str(points[1])])
            self.pressure_coords = self.get_pressure_point_coord_from_two_points(coords[0],coords[1])
            self.comp_objects = [test.get_tank_object()]
            self._initial_fatigue_obj = test.get_fatigue_object()

        else:
            if app._line_to_struc[app._active_line][0] is None:
                return
            elif app._line_to_struc[app._active_line][0].Stiffener is None:
                return
            self.app = app
            self.active_line = app._active_line
            points = app._line_dict[self.active_line]
            coords = (app._point_dict['point'+str(points[0])], app._point_dict['point'+str(points[1])])
            self.pressure_coords = self.get_pressure_point_coord_from_two_points(coords[0], coords[1])
            self._initial_structure_obj = app._line_to_struc[app._active_line][0].Stiffener
            self.load_objects = app._line_to_struc[app._active_line][3]

            self.comp_objects = [app._tank_dict['comp'+str(comp_i)] for comp_i in
                                 app.get_compartments_for_line(app._active_line)]
            self._initial_fatigue_obj = app._line_to_struc[self.active_line][2]


        self._frame = master
        self._frame.wm_title("Specify fatigue properties here.")
        self._frame.geometry('1300x810')
        self._frame.grab_set()

        tk.Label(self._frame, text='-- Fatigue calculation for plates according to DNVGL-RP-C203, '
                                   'Section 5 Simplified fatigue analysis --',
                 font='Verdana 15 bold').place(x=10, y=10)

        ent_w = 10

        self.new_sn_curve = tk.StringVar()
        self.new_k_factor = tk.DoubleVar()
        self.new_no_of_cycles = tk.DoubleVar()
        self.new_design_life = tk.DoubleVar()
        self.new_dff = tk.DoubleVar()

        self.new_weibull_loa = tk.DoubleVar()
        self.new_weibull_bal = tk.DoubleVar()
        self.new_weibull_prt = tk.DoubleVar()

        self.new_period_loa = tk.DoubleVar()
        self.new_period_bal = tk.DoubleVar()
        self.new_period_prt = tk.DoubleVar()

        self.new_corr_loc_loa = tk.DoubleVar()
        self.new_corr_loc_bal = tk.DoubleVar()
        self.new_corr_loc_prt = tk.DoubleVar()

        self.new_fraction_loa = tk.DoubleVar()
        self.new_fraction_bal = tk.DoubleVar()
        self.new_fraction_prt = tk.DoubleVar()

        self.new_az_loa = tk.DoubleVar()
        self.new_az_bal = tk.DoubleVar()
        self.new_az_prt = tk.DoubleVar()


        sn_curves = sn.get_all_curves()

        self.ent_sn_curve = tk.OptionMenu(self._frame, self.new_sn_curve, command=self.change_sn_curve,*sn_curves)
        self.ent_dff = tk.Entry(self._frame, textvariable=self.new_dff, width=ent_w)
        self.ent_k_factor = tk.Entry(self._frame, textvariable=self.new_k_factor, width=ent_w)
        self.ent_no_of_cycles = tk.Entry(self._frame, textvariable=self.new_no_of_cycles, width=ent_w)
        self.ent_new_design_life = tk.Entry(self._frame, textvariable=self.new_design_life, width=ent_w)

        self.ent_weibull_loa = tk.Entry(self._frame, textvariable=self.new_weibull_loa, width=ent_w)
        self.ent_weibull_bal = tk.Entry(self._frame, textvariable=self.new_weibull_bal, width=ent_w)
        self.ent_weibull_prt = tk.Entry(self._frame, textvariable=self.new_weibull_prt, width=ent_w)

        self.ent_period_loa = tk.Entry(self._frame, textvariable=self.new_period_loa, width=ent_w)
        self.ent_period_bal = tk.Entry(self._frame, textvariable=self.new_period_bal, width=ent_w)
        self.ent_period_prt = tk.Entry(self._frame, textvariable=self.new_period_prt, width=ent_w)

        self.ent_corr_loc_loa = tk.Entry(self._frame, textvariable=self.new_corr_loc_loa, width=ent_w)
        self.ent_corr_loc_bal = tk.Entry(self._frame, textvariable=self.new_corr_loc_bal, width=ent_w)
        self.ent_corr_loc_prt = tk.Entry(self._frame, textvariable=self.new_corr_loc_prt, width=ent_w)

        self.ent_fraction_loa = tk.Entry(self._frame, textvariable=self.new_fraction_loa, width=ent_w)
        self.ent_fraction_bal = tk.Entry(self._frame, textvariable=self.new_fraction_bal, width=ent_w)
        self.ent_fraction_prt = tk.Entry(self._frame, textvariable=self.new_fraction_prt, width=ent_w)

        self.ent_acc_loa = tk.Entry(self._frame, textvariable=self.new_az_loa, width=ent_w)
        self.ent_acc_bal = tk.Entry(self._frame, textvariable=self.new_az_bal, width=ent_w)
        self.ent_acc_prt = tk.Entry(self._frame, textvariable=self.new_az_prt, width=ent_w)

        start_x, start_y, dx, dy = 20, 100, 150, 35

        loaded_exist = False
        ballast_exist = False
        part_exist = False
        fls_exist = (loaded_exist, ballast_exist, part_exist)

        # Frames to hide loaded, ballast or part
        loa_fr = tk.Frame(self._frame, width=100, height=170, bg="gray25", colormap="new")
        bal_fr = tk.Frame(self._frame, width=100, height=170, bg="gray25", colormap="new")
        prt_fr = tk.Frame(self._frame, width=100, height=170, bg="gray25", colormap="new")

        for load in self.load_objects:
            if load != None:
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


        if self._initial_fatigue_obj == None:
            self.new_sn_curve.set('Ec')
            self.new_k_factor.set(1)
            self.new_no_of_cycles.set(10000)
            self.new_design_life.set(20)
            self.new_dff.set(2)
            if any(fls_exist):
                if loaded_exist:
                    self.new_fraction_loa.set(1 / fls_exist.count(True))
                    self.new_weibull_loa.set(0.8)
                    self.new_period_loa.set(8)
                    self.new_corr_loc_loa.set(0.5)
                    self.new_az_loa.set(0.5)
                if ballast_exist:
                    self.new_fraction_bal.set(1 / fls_exist.count(True))
                    self.new_weibull_bal.set(0.8)
                    self.new_period_bal.set(8)
                    self.new_corr_loc_bal.set(0.5)
                    self.new_az_bal.set(0.5)
                if part_exist:
                    self.new_fraction_prt.set(1 / fls_exist.count(True))
                    self.new_weibull_prt.set(0.8)
                    self.new_period_prt.set(8)
                    self.new_corr_loc_prt.set(0.5)
                    self.new_az_prt.set(0.5)
        else:
            fat_prop = self._initial_fatigue_obj.get_fatigue_properties()
            self.new_sn_curve.set(fat_prop['SN-curve'])
            self.new_k_factor.set(fat_prop['SCF'])
            self.new_no_of_cycles.set(fat_prop['n0'])
            self.new_design_life.set(fat_prop['Design life'])
            self.new_dff.set(fat_prop['DFF'])
            if any(fls_exist):
                if loaded_exist:
                    self.new_fraction_loa.set(fat_prop['Fraction'][0])
                    self.new_weibull_loa.set(fat_prop['Weibull'][0])
                    self.new_period_loa.set(fat_prop['Period'][0])
                    self.new_corr_loc_loa.set(fat_prop['CorrLoc'][0])
                    self.new_az_loa.set(fat_prop['Accelerations'][0])
                if ballast_exist:
                    self.new_fraction_bal.set(fat_prop['Fraction'][1])
                    self.new_weibull_bal.set(fat_prop['Weibull'][1])
                    self.new_period_bal.set(fat_prop['Period'][1])
                    self.new_corr_loc_bal.set(fat_prop['CorrLoc'][1])
                    self.new_az_bal.set(fat_prop['Accelerations'][1])
                if part_exist:
                    self.new_fraction_prt.set(fat_prop['Fraction'][2])
                    self.new_weibull_prt.set(fat_prop['Weibull'][2])
                    self.new_period_prt.set(fat_prop['Period'][2])
                    self.new_corr_loc_prt.set(fat_prop['CorrLoc'][2])
                    self.new_az_prt.set(fat_prop['Accelerations'][2])

        all_acc = (self.new_az_loa.get(), self.new_az_bal.get(), self.new_az_prt.get())

        count = 1
        for load in self.load_objects:
            if load == None:
                continue
            press = []
            if load.get_limit_state() == 'FLS':
                tk.Label(self._frame, text=str(count)+'. '+load.get_name(), font='Verdana 8')\
                    .place(x=start_x + 5 * dx, y=start_y + (5+count) * dy)
                idx = 0
                for exist in fls_exist:
                    if exist:
                        press.append(round(load.get_calculated_pressure(self.pressure_coords,all_acc[idx],
                                                                        self._initial_structure_obj.
                                                                        get_structure_type()), 1))
                        idx += 1

                tk.Label(self._frame, text=press, font='Verdana 8') \
                    .place(x=start_x + 6.5 * dx, y=start_y + (5 + count) * dy)
                count += 1
        press = []
        for comp in self.comp_objects:
            if comp == None:
                continue
            tk.Label(self._frame, text=str(count) + '. ' +str(comp.get_name()), font='Verdana 8') \
                .place(x=start_x + 5 * dx, y=start_y + (5 + count) * dy)

            idx = 0

            if fls_exist[0] and comp.is_loaded_condition():
                press.append(round(comp.get_calculated_pressure(self.pressure_coords, all_acc[0]), 1))
            if fls_exist[1] and comp.is_ballast_condition():
                press.append(round(comp.get_calculated_pressure(self.pressure_coords, all_acc[1]), 1))
            if fls_exist[2] and any([comp.is_loaded_condition(),comp.is_ballast_condition()]):
                press.append(round(comp.get_calculated_pressure(self.pressure_coords, all_acc[2]), 1))

            tk.Label(self._frame, text=press, font='Verdana 8') \
                .place(x=start_x + 6.5 * dx, y=start_y + (5 + count) * dy)

            count += 1

        tk.Label(self._frame, text='Design life:', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 0*dy)
        tk.Label(self._frame, text='Design Fatigue Factor (DFF):', font='Verdana 8 bold') \
            .place(x=start_x+ 3*dx , y=start_y + 0*dy)
        tk.Label(self._frame, text='SN-curve:', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 1*dy)
        tk.Label(self._frame, text='Cycles in return period, n0', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 2*dy)
        tk.Label(self._frame, text='Stress Concentration Factor, SCF', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 3*dy)

        tk.Label(self._frame, text='Loaded', font='Verdana 8 bold') \
            .place(x=start_x+2*dx , y=start_y + 5*dy)
        tk.Label(self._frame, text='Ballast', font='Verdana 8 bold') \
            .place(x=start_x+3*dx , y=start_y + 5*dy)
        tk.Label(self._frame, text='Part', font='Verdana 8 bold') \
            .place(x=start_x+4*dx , y=start_y + 5*dy)
        tk.Label(self._frame, text='Defined loads', font='Verdana 8 bold') \
            .place(x=start_x+5*dx , y=start_y + 5*dy)
        tk.Label(self._frame, text='Resulting pressures', font='Verdana 8 bold') \
            .place(x=start_x+6.5*dx , y=start_y + 5*dy)

        tk.Label(self._frame, text='Fraction (sum of bal/part/loa is 1)', font='Verdana 8 bold') \
            .place(x=start_x, y=start_y + 6 * dy)
        tk.Label(self._frame, text='Weibull', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 7*dy)
        tk.Label(self._frame, text='Period', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 8*dy)
        tk.Label(self._frame, text='Corr. loc.', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 9*dy)
        tk.Label(self._frame, text='Accelerations', font='Verdana 8 bold') \
            .place(x=start_x , y=start_y + 10*dy)

        self.ent_new_design_life.place(x=start_x+2*dx, y=start_y + 0 * dy)
        self.ent_dff.place(x=start_x + 5 * dx, y=start_y + 0 * dy)
        self.ent_sn_curve.place(x=start_x+2*dx , y=start_y + 1*dy)
        self.ent_no_of_cycles .place(x=start_x+2*dx , y=start_y + 2*dy)
        self.ent_k_factor.place(x=start_x+2*dx , y=start_y + 3*dy)

        self.ent_fraction_loa.place(x=start_x + 2 * dx, y=start_y + 6 * dy)
        self.ent_fraction_bal.place(x=start_x+3*dx , y=start_y + 6*dy)
        self.ent_fraction_prt.place(x=start_x+4*dx , y=start_y + 6*dy)

        self.ent_weibull_loa.place(x=start_x + 2 * dx, y=start_y + 7 * dy)
        self.ent_weibull_bal.place(x=start_x+3*dx , y=start_y + 7*dy)
        self.ent_weibull_prt.place(x=start_x+4*dx , y=start_y + 7*dy)

        self.ent_period_loa.place(x=start_x + 2 * dx, y=start_y + 8 * dy)
        self.ent_period_bal.place(x=start_x+3*dx, y=start_y + 8*dy)
        self.ent_period_prt.place(x=start_x+4*dx, y=start_y + 8*dy)

        self.ent_corr_loc_loa.place(x=start_x + 2 * dx, y=start_y + 9 * dy)
        self.ent_corr_loc_bal.place(x=start_x+3*dx, y=start_y + 9*dy)
        self.ent_corr_loc_prt.place(x=start_x+4*dx, y=start_y + 9*dy)

        self.ent_acc_loa.place(x=start_x + 2 * dx, y=start_y + 10 * dy)
        self.ent_acc_bal.place(x=start_x + 3 * dx, y=start_y + 10 * dy)
        self.ent_acc_prt.place(x=start_x + 4 * dx, y=start_y + 10 * dy)

        # if not loaded_exist:
        #     loa_fr.place(x=start_x + 2 * dx, y=start_y + 6 * dy)
        # elif not ballast_exist:
        #     bal_fr.place(x=start_x + 3 * dx, y=start_y + 6 * dy)
        # elif not part_exist:
        #     prt_fr.place(x=start_x + 4 * dx, y=start_y + 6 * dy)

        self._close_and_save = tk.Button(self._frame, text='Return fatigue parameters',
                                        command=self.save_and_close, bg='green', font='Verdana 15', fg='yellow')
        self._close_and_save.place(x=start_x + dx, y=start_y + dy * 15)

    def get_pressure_point_coord_from_two_points(self,p1,p2):
        ''' Finding the coordinates to use in pressure calculations '''

        if p1[1] <= p2[1]:
            start_point = p1
            end_point = p2
        else:
            start_point = p2
            end_point = p1

        vector = [end_point[0]-start_point[0], end_point[1]-start_point[1]]

        return start_point[0]+vector[0]*1/3, start_point[1]+vector[1]*1/3

    def change_sn_curve(self,event):
        '''
        Action when changing the structure type
        :return:
        '''
        self.new_sn_curve.set(event)

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''
        if __name__ == '__main__':
            self._frame.destroy()
            return
        # order of return is (Loaded,Ballast,Part)
        temp_dict = {'SN-curve':self.new_sn_curve.get(),
                     'SCF':self.new_k_factor.get(),
                     'Design life':self.new_design_life.get(),
                     'n0':self.new_no_of_cycles.get(),
                     'Weibull':(self.new_weibull_loa.get(),self.new_weibull_bal.get(),self.new_weibull_prt.get()),
                     'Period':(self.new_period_loa.get(),self.new_period_bal.get(),self.new_period_prt.get()),
                     'Fraction':(self.new_fraction_loa.get(),self.new_fraction_bal.get(),self.new_fraction_prt.get()),
                     'CorrLoc':(self.new_corr_loc_loa.get(),self.new_corr_loc_bal.get(),self.new_corr_loc_prt.get()),
                     'Order':('Loaded','Ballast','Part'),
                     'Accelerations':(self.new_az_loa.get(),self.new_az_bal.get(),self.new_az_prt.get()),
                     'DFF': self.new_dff.get()}

        self.app.on_close_fatigue_window(temp_dict)
        self._frame.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateFatigueWindow(root,app=None)
    root.mainloop()