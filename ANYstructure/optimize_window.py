# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError
import ANYstructure.optimize as op
import numpy as np
import time, os
from tkinter import messagebox
import ANYstructure.example_data as test

class CreateOptimizeWindow():
    '''
    This class initiates the single optimization window.
    '''

    def __init__(self,master,app=None):
        super(CreateOptimizeWindow,self).__init__()
        if __name__ == '__main__':
            self._initial_structure_obj = test.get_structure_calc_object()
            self._initial_calc_obj = test.get_structure_calc_object()
            self._lateral_pressure = 200
            self._fatigue_object = test.get_fatigue_object()
            self._fatigue_pressure = test.get_fatigue_pressures()
            self._slamming_pressure = test.get_slamming_pressure()
            image_dir = os.path.dirname(__file__)+'\\images\\'
        else:
            self.app = app
            self._initial_structure_obj = app._line_to_struc[app._active_line][0]
            self._initial_calc_obj = app._line_to_struc[app._active_line][1]
            self._fatigue_object = app._line_to_struc[app._active_line][2]
            try:
                self._fatigue_pressure = app.get_fatigue_pressures(app._active_line,
                                                                   self._fatigue_object.get_accelerations())
            except AttributeError:
                self._fatigue_pressure = None
            try:
                self._lateral_pressure = self.app.get_highest_pressure(self.app._active_line)['normal'] / 1000
            except KeyError:
                self._lateral_pressure = 0
            try:

                if self.app.get_highest_pressure(self.app._active_line)['slamming'] is None:
                    self._slamming_pressure = 0
                else:
                    self._slamming_pressure = self.app.get_highest_pressure(self.app._active_line)['slamming']
            except KeyError:
                self._slamming_pressure = 0
            image_dir = app._root_dir +'\\images\\'

        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1400x900')
        self._frame.grab_set()

        self._opt_runned = False
        self._opt_results = ()
        self._opt_actual_running_time = tk.Label(self._frame,text='')

        self._draw_scale = 500
        self._canvas_dim = (500, 450)
        self._canvas_opt = tk.Canvas(self._frame,width=self._canvas_dim[0], height=self._canvas_dim[1], 
                                     background='azure',relief = 'groove', borderwidth=2)

        tk.Frame(self._frame,width=770,height=5, bg="grey", colormap="new").place(x=20,y=127)
        tk.Frame(self._frame, width=770, height=5, bg="grey", colormap="new").place(x=20, y=167)

        self._canvas_opt.place(x=10,y=300)

        algorithms = ('anysmart','random','random_no_delta','anydetail','pso')

        tk.Label(self._frame,text='-- Structural optimizer --',font='Verdana 15 bold').place(x=10,y=10)

        self._spacing = self._initial_structure_obj.get_s()
        self._pl_thk = self._initial_structure_obj.get_pl_thk()
        self._stf_web_h = self._initial_structure_obj.get_web_h()
        self._stf_web_thk =self._initial_structure_obj.get_web_thk()
        self._fl_w = self._initial_structure_obj.get_fl_w()
        self._fl_thk =self._initial_structure_obj.get_fl_thk()

        # upper and lower bounds for optimization
        #[0.6, 0.012, 0.3, 0.01, 0.1, 0.01]
        self._new_spacing_upper = tk.DoubleVar()
        self._new_spacing_lower = tk.DoubleVar()
        self._new_pl_thk_upper = tk.DoubleVar()
        self._new_pl_thk_lower = tk.DoubleVar()
        self._new_web_h_upper = tk.DoubleVar()
        self._new_web_h_lower = tk.DoubleVar()
        self._new_web_thk_upper = tk.DoubleVar()
        self._new_web_thk_lower = tk.DoubleVar()
        self._new_fl_w_upper = tk.DoubleVar()
        self._new_fl_w_lower = tk.DoubleVar()
        self._new_fl_thk_upper = tk.DoubleVar()
        self._new_fl_thk_lower = tk.DoubleVar()
        self._new_span = tk.DoubleVar()
        self._new_width_lg = tk.DoubleVar()
        self._new_algorithm = tk.StringVar()
        self._new_algorithm_random_trials = tk.IntVar()
        self._new_swarm_size = tk.IntVar()
        self._new_omega  = tk.DoubleVar()
        self._new_phip  = tk.DoubleVar()
        self._new_phig  = tk.DoubleVar()
        self._new_maxiter = tk.IntVar()
        self._new_minstep  = tk.DoubleVar()
        self._new_minfunc  = tk.DoubleVar()
        self._new_slamming_pressure = tk.DoubleVar()
        self._new_fatigue_int_press = tk.DoubleVar()
        self._new_fatigue_ext_press = tk.DoubleVar()
        

        ent_w = 10
        self._ent_spacing_upper = tk.Entry(self._frame, textvariable = self._new_spacing_upper, width = ent_w)
        self._ent_spacing_lower = tk.Entry(self._frame, textvariable=self._new_spacing_lower, width=ent_w)

        self._ent_pl_thk_upper= tk.Entry(self._frame, textvariable=self._new_pl_thk_upper, width=ent_w)
        self._ent_pl_thk_lower= tk.Entry(self._frame, textvariable=self._new_pl_thk_lower, width=ent_w)

        self._ent_web_h_upper = tk.Entry(self._frame, textvariable=self._new_web_h_upper, width=ent_w)
        self._ent_web_h_lower = tk.Entry(self._frame, textvariable=self._new_web_h_lower, width=ent_w)

        self._ent_web_thk_upper = tk.Entry(self._frame, textvariable=self._new_web_thk_upper, width=ent_w)
        self._ent_web_thk_lower = tk.Entry(self._frame, textvariable=self._new_web_thk_lower, width=ent_w)

        self._ent_fl_w_upper = tk.Entry(self._frame, textvariable=self._new_fl_w_upper, width=ent_w)
        self._ent_fl_w_lower = tk.Entry(self._frame, textvariable=self._new_fl_w_lower, width=ent_w)

        self._ent_fl_thk_upper = tk.Entry(self._frame, textvariable=self._new_fl_thk_upper, width=ent_w)
        self._ent_fl_thk_lower = tk.Entry(self._frame, textvariable=self._new_fl_thk_lower, width=ent_w)

        self._ent_span = tk.Entry(self._frame, textvariable=self._new_span, width=ent_w)
        self._ent_width_lg = tk.Entry(self._frame, textvariable=self._new_width_lg, width=ent_w)
        self._ent_slamming_pressure = tk.Entry(self._frame, textvariable=self._new_slamming_pressure, width=ent_w)
        
        #additional choices for the random and pso algorithm
        self._ent_algorithm = tk.OptionMenu(self._frame,self._new_algorithm,command=self.selected_algorithm,*algorithms)
        self._ent_random_trials = tk.Entry(self._frame,textvariable=self._new_algorithm_random_trials)

        pso_width = 10
        self._ent_swarm_size = tk.Entry(self._frame,textvariable=self._new_swarm_size, width = pso_width)
        self._ent_omega = tk.Entry(self._frame,textvariable=self._new_omega, width = pso_width)
        self._ent_phip = tk.Entry(self._frame,textvariable=self._new_phip, width = pso_width)
        self._ent_phig = tk.Entry(self._frame,textvariable=self._new_phig, width = pso_width)
        self._ent_maxiter = tk.Entry(self._frame,textvariable=self._new_maxiter, width = pso_width)
        self._ent_minstep = tk.Entry(self._frame,textvariable=self._new_minstep, width = pso_width)
        self._ent_minfunc = tk.Entry(self._frame,textvariable=self._new_minfunc, width = pso_width)

        self._new_delta_spacing = tk.DoubleVar()
        self._new_delta_pl_thk = tk.DoubleVar()
        self._new_delta_web_h = tk.DoubleVar()
        self._new_delta_web_thk = tk.DoubleVar()
        self._new_delta_fl_w = tk.DoubleVar()
        self._new_delta_fl_thk = tk.DoubleVar()
        
        self._new_opt_spacing = tk.DoubleVar()
        self._new_opt_pl_thk = tk.DoubleVar()
        self._new_opt_web_h = tk.DoubleVar()
        self._new_opt_web_thk = tk.DoubleVar()
        self._new_opt_fl_w = tk.DoubleVar()
        self._new_opt_fl_thk = tk.DoubleVar()

        self._ent_delta_spacing = tk.Entry(self._frame, textvariable = self._new_delta_spacing, width = ent_w)
        self._ent_delta_pl_thk = tk.Entry(self._frame, textvariable = self._new_delta_pl_thk, width = ent_w)
        self._ent_delta_web_h = tk.Entry(self._frame, textvariable = self._new_delta_web_h, width = ent_w)
        self._ent_delta_web_thk = tk.Entry(self._frame, textvariable = self._new_delta_web_thk, width = ent_w)
        self._ent_delta_fl_w = tk.Entry(self._frame, textvariable = self._new_delta_fl_w, width = ent_w)
        self._ent_delta_fl_thk = tk.Entry(self._frame, textvariable = self._new_delta_fl_thk, width = ent_w)

        bg_col = 'pink'
        self._ent_opt_spacing = tk.Entry(self._frame, textvariable=self._new_opt_spacing, width=ent_w,bg=bg_col)
        self._ent_opt_pl_thk = tk.Entry(self._frame, textvariable=self._new_opt_pl_thk, width=ent_w,bg=bg_col)
        self._ent_opt_web_h = tk.Entry(self._frame, textvariable=self._new_opt_web_h, width=ent_w,bg=bg_col)
        self._ent_opt_web_thk = tk.Entry(self._frame, textvariable=self._new_opt_web_thk, width=ent_w,bg=bg_col)
        self._ent_opt_fl_w = tk.Entry(self._frame, textvariable=self._new_opt_fl_w, width=ent_w,bg=bg_col)
        self._ent_opt_fl_thk = tk.Entry(self._frame, textvariable=self._new_opt_fl_thk, width=ent_w,bg=bg_col)
        
        # stresses in plate and stiffener

        self._new_trans_stress_high = tk.DoubleVar()
        self._new_trans_stress_low = tk.DoubleVar()
        self._new_axial_stress = tk.DoubleVar()
        self._new_shear_stress = tk.DoubleVar()
        self._new_design_pressure = tk.DoubleVar()
        self._new_pressure_side = tk.StringVar()


        self._ent_trans_stress_high = tk.Entry(self._frame, textvariable=self._new_trans_stress_high, width=ent_w)
        self._ent_trans_stress_low = tk.Entry(self._frame, textvariable=self._new_trans_stress_low, width=ent_w)
        self._ent_axial_stress = tk.Entry(self._frame, textvariable=self._new_axial_stress, width=ent_w)
        self._ent_design_pressure = tk.Entry(self._frame, textvariable=self._new_design_pressure, width=ent_w)
        self._ent_design_pressure_side = tk.OptionMenu(self._frame,self._new_pressure_side,*('p','s'))
        self._ent_shear_stress = tk.Entry(self._frame, textvariable=self._new_shear_stress, width=ent_w)

        start_x,start_y,dx,dy = 20,100,100,40


        tk.Label(self._frame,text='Upper bounds [mm]',font='Verdana 9').place(x=start_x,y=start_y)
        tk.Label(self._frame, text='Iteration delta [mm]',font='Verdana 9').place(x=start_x, y=start_y+dy)
        tk.Label(self._frame, text='Lower bounds [mm]',font='Verdana 9').place(x=start_x, y=start_y+2*dy)
        tk.Label(self._frame, text='Spacing [mm]', font='Verdana 7 bold').place(x=start_x + 1.97 * dx, y=start_y-0.6*dy)
        tk.Label(self._frame, text='Plate thk. [mm]', font='Verdana 7 bold').place(x=start_x + 2.97 * dx, y=start_y-0.6*dy)
        tk.Label(self._frame, text='Web height [mm]', font='Verdana 7 bold').place(x=start_x + 3.97 * dx, y=start_y-0.6*dy)
        tk.Label(self._frame, text='Web thk. [mm]', font='Verdana 7 bold').place(x=start_x + 4.97 * dx, y=start_y-0.6*dy)
        tk.Label(self._frame, text='Flange width [mm]', font='Verdana 7 bold').place(x=start_x + 5.97 * dx, y=start_y-0.6*dy)
        tk.Label(self._frame, text='Flange thk. [mm]', font='Verdana 7 bold').place(x=start_x + 6.97 * dx, y=start_y-0.6*dy)
        tk.Label(self._frame, text='Estimated running time for algorithm: ',
                 font='Verdana 9 bold').place(x=start_x, y=start_y + 2.8 * dy)
        self._runnig_time_label = tk.Label(self._frame, text='',font='Verdana 9 bold')
        self._runnig_time_label.place(x=start_x+2.7*dx, y=start_y + 2.8 * dy)
        tk.Label(self._frame, text='seconds ',font='Verdana 9 bold').place(x=start_x+3.3*dx, y=start_y + 2.8 * dy)
        self._result_label = tk.Label(self._frame, text = '',font = 'Verdana 9 bold' )
        self._result_label.place(x=start_x, y=start_y + 3.4 * dy)

        self._ent_spacing_upper.place(x=start_x+dx*2,y=start_y)
        self._ent_delta_spacing.place(x=start_x+dx*2,y=start_y+dy)
        self._ent_spacing_lower.place(x=start_x+dx*2,y=start_y+2*dy)

        self._ent_pl_thk_upper.place(x=start_x+dx*3,y=start_y)
        self._ent_delta_pl_thk.place(x=start_x+dx*3,y=start_y+dy)
        self._ent_pl_thk_lower.place(x=start_x+dx*3,y=start_y+2*dy)

        self._ent_web_h_upper.place(x=start_x+dx*4,y=start_y)
        self._ent_delta_web_h.place(x=start_x+dx*4,y=start_y+dy)
        self._ent_web_h_lower.place(x=start_x+dx*4,y=start_y+2*dy)

        self._ent_web_thk_upper.place(x=start_x+dx*5,y=start_y)
        self._ent_delta_web_thk.place(x=start_x+dx*5,y=start_y+dy)
        self._ent_web_thk_lower.place(x=start_x+dx*5,y=start_y+2*dy)

        self._ent_fl_w_upper.place(x=start_x+dx*6,y=start_y)
        self._ent_delta_fl_w.place(x=start_x+dx*6,y=start_y+dy)
        self._ent_fl_w_lower.place(x=start_x+dx*6,y=start_y+2*dy)

        self._ent_fl_thk_upper.place(x=start_x+dx*7,y=start_y)
        self._ent_delta_fl_thk.place(x=start_x+dx*7,y=start_y+dy)
        self._ent_fl_thk_lower.place(x=start_x+dx*7,y=start_y+2*dy)
        
        ###

        # tk.Label(self._frame,text='Optimized result:\n')\
        #     .place(x=start_x,y=start_y+ver_mult*dy*0.9)
        dx_mult = 0.7
        tk.Label(self._frame,text='Optimized values').place(x=start_x,y=start_y+17*dy)

        tk.Label(self._frame, text='s').place(x=start_x, y=start_y + 18 * dy)
        tk.Label(self._frame, text='pl_thk').place(x=start_x, y=start_y + 19 * dy)
        self._ent_opt_spacing.place(x=start_x+dx_mult*dx,y=start_y+18*dy)
        self._ent_opt_pl_thk.place(x=start_x+dx_mult*dx,y=start_y+19*dy)

        tk.Label(self._frame, text='web_h').place(x=start_x+2*dx_mult*dx, y=start_y + 18 * dy)
        tk.Label(self._frame, text='web_htk').place(x=start_x+2*dx_mult*dx, y=start_y + 19 * dy)
        self._ent_opt_web_h.place(x=start_x+3*dx_mult*dx,y=start_y+18*dy)
        self._ent_opt_web_thk.place(x=start_x+3*dx_mult*dx,y=start_y+19*dy)

        tk.Label(self._frame, text='fl_thk').place(x=start_x+4*dx_mult*dx, y=start_y + 18 * dy)
        tk.Label(self._frame, text='fl_ttk.').place(x=start_x+4*dx_mult*dx, y=start_y + 19 * dy)
        self._ent_opt_fl_w.place(x=start_x+5*dx_mult*dx,y=start_y+18*dy)
        self._ent_opt_fl_thk.place(x=start_x+5*dx_mult*dx,y=start_y+19*dy)
        
        #Labels for the pso
 
        self._lb_swarm_size = tk.Label(self._frame,text='swarm size')
        self._lb_omega  = tk.Label(self._frame,text='omega')
        self._lb_phip  = tk.Label(self._frame,text='phip')
        self._lb_phig  = tk.Label(self._frame,text='phig')
        self._lb_maxiter = tk.Label(self._frame,text='maxiter')
        self._lb_minstep  = tk.Label(self._frame,text='minstep')
        self._lb_minfunc  = tk.Label(self._frame,text='minfunc')

        ###

        tk.Label(self._frame, text='Sigma,y1_Sd - large transversal stress', font='Verdana 9')\
            .place(x=start_x+dx*5,y=start_y+11.5*dy)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+11.5*dy)

        tk.Label(self._frame, text='Sigma,y2_Sd - small transversal stress', font='Verdana 9')\
            .place(x=start_x+dx*5,y=start_y+12.5*dy)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+12.5*dy)

        tk.Label(self._frame, text='Sigma,x_Sd - axial stress', font='Verdana 9')\
            .place(x=start_x+dx*5,y=start_y+13.5*dy)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+13.5*dy)

        tk.Label(self._frame, text='Tau,xy - shear stress', font='Verdana 9')\
            .place(x=start_x+dx*5,y=start_y+14.5*dy)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+14.5*dy)

        tk.Label(self._frame, text='Applied pressure ', font='Verdana 9 bold')\
            .place(x=start_x+dx*5,y=start_y+15.5*dy)
        tk.Label(self._frame, text='kPa', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+15.5*dy)
        tk.Label(self._frame, text='Plate or stiffener side (p/s): ', font='Verdana 9 bold')\
            .place(x=start_x+dx*9.5,y=start_y+15.5*dy)

        tk.Label(self._frame, text='Span: ', font='Verdana 9') \
            .place(x=start_x + dx * 5, y=start_y + 16.5 * dy)
        tk.Label(self._frame, text='m', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+16.5*dy)

        tk.Label(self._frame, text='Girder length,Lg: ', font='Verdana 9') \
            .place(x=start_x + dx * 5, y=start_y + 17.5 * dy)
        tk.Label(self._frame, text='m', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+17.5*dy)

        tk.Label(self._frame, text='Slamming pressure ', font='Verdana 9') \
            .place(x=start_x + dx * 5, y=start_y + 18.5 * dy)
        tk.Label(self._frame, text='Pa', font='Verdana 9')\
            .place(x=start_x+dx*9,y=start_y+18.5*dy)

        if self._fatigue_pressure is not None:
            tk.Label(self._frame, text='Fatigue pressure: internal= '+str(self._fatigue_pressure['p_int'])+ ' external= '
                                       +str(self._fatigue_pressure['p_ext']), font='Verdana 7') \
                .place(x=start_x + dx * 5, y=start_y + 19.3 * dy)
        else:
            tk.Label(self._frame, text='Fatigue pressure: internal= '+str(0)+ ' external= '
                                       +str(0), font='Verdana 7') \
                .place(x=start_x + dx * 5, y=start_y + 19.3 * dy)


        self._ent_trans_stress_high.place(x=start_x+dx*8,y=start_y+11.5*dy)
        self._ent_trans_stress_low.place(x=start_x+dx*8,y=start_y+12.5*dy)
        self._ent_axial_stress.place(x=start_x+dx*8,y=start_y+13.5*dy)
        self._ent_shear_stress.place(x=start_x + dx * 8, y=start_y + 14.5 * dy)
        self._ent_design_pressure.place(x=start_x + dx * 8, y=start_y + 15.5 * dy)
        self._ent_design_pressure_side.place(x=start_x + dx * 12, y=start_y + 15.5 * dy)
        self._ent_span.place(x=start_x + dx * 8, y=start_y + 16.5 * dy)
        self._ent_width_lg.place(x=start_x + dx * 8, y=start_y + 17.5 * dy)
        self._ent_slamming_pressure.place(x=start_x + dx * 8, y=start_y + 18.5 * dy)

        #setting default values
        init_dim = float(50) #mm
        init_thk = float(2) #mm
        self._new_delta_spacing.set(init_dim)
        self._new_delta_pl_thk.set(init_thk)
        self._new_delta_web_h.set(init_dim)
        self._new_delta_web_thk.set(init_thk)
        self._new_delta_fl_w.set(init_dim)
        self._new_delta_fl_thk.set(init_thk)
        self._new_trans_stress_high.set(self._initial_structure_obj.get_sigma_y1())
        self._new_trans_stress_low.set(self._initial_structure_obj.get_sigma_y2())
        self._new_axial_stress.set(self._initial_structure_obj.get_sigma_x())
        self._new_shear_stress.set(self._initial_structure_obj.get_tau_xy())

        self._new_design_pressure.set(self._lateral_pressure)
        self._new_slamming_pressure.set(self._slamming_pressure)
        if self._fatigue_pressure is None:
            self._new_fatigue_ext_press.set(0), self._new_fatigue_int_press.set(0)
        else:
            self._new_fatigue_int_press.set(self._fatigue_pressure['p_int']), \
            self._new_fatigue_ext_press.set(self._fatigue_pressure['p_ext'])

        self._new_spacing_upper.set(round(self._spacing*1000+100,5))
        self._new_spacing_lower.set(round(max(self._spacing*1000-100,0),5))
        self._new_pl_thk_upper.set(round(self._pl_thk*1000+10,5))
        self._new_pl_thk_lower.set(round(max(self._pl_thk*1000-10,float(10)),5))
        self._new_web_h_upper.set(round(self._stf_web_h*1000+100,5))
        self._new_web_h_lower.set(round(max(self._stf_web_h*1000-100,0),5))
        self._new_web_thk_upper.set(round(self._stf_web_thk*1000+10,5))
        self._new_web_thk_lower.set(round(max(self._stf_web_thk*1000-10,float(10)),5))
        if self._initial_structure_obj.get_stiffener_type() != 'FB':
            self._new_fl_w_upper.set(round(self._fl_w*1000+100,5))
            self._new_fl_w_lower.set(round(max(self._fl_w*1000-100,0),5))
            self._new_fl_thk_upper.set(round(self._fl_thk*1000+10,5))
            self._new_fl_thk_lower.set(round(max(self._fl_thk*1000-10,10),5))
        else:
            self._new_fl_w_upper.set(0)
            self._new_fl_w_lower.set(0)
            self._new_fl_thk_upper.set(0)
            self._new_fl_thk_lower.set(0)

        self._new_pressure_side.set('p')
        self._new_width_lg.set(10)
        self._new_span.set(round(self._initial_structure_obj.get_span(),5))
        self._new_algorithm.set('anysmart')
        self._new_algorithm_random_trials.set(100000)
        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)
        
        self._new_delta_spacing.trace('w',self.update_running_time)
        self._new_delta_pl_thk.trace('w',self.update_running_time)
        self._new_delta_web_h.trace('w',self.update_running_time)
        self._new_delta_web_thk.trace('w',self.update_running_time)
        self._new_delta_fl_w.trace('w',self.update_running_time)
        self._new_delta_fl_thk.trace('w',self.update_running_time)
        self._new_spacing_upper.trace('w',self.update_running_time)
        self._new_spacing_lower.trace('w',self.update_running_time)
        self._new_pl_thk_upper.trace('w',self.update_running_time)
        self._new_pl_thk_lower.trace('w',self.update_running_time)
        self._new_web_h_upper.trace('w',self.update_running_time)
        self._new_web_h_lower.trace('w',self.update_running_time)
        self._new_web_thk_upper.trace('w',self.update_running_time)
        self._new_web_thk_lower.trace('w',self.update_running_time)
        self._new_fl_w_upper.trace('w',self.update_running_time)
        self._new_fl_w_lower.trace('w',self.update_running_time)
        self._new_fl_thk_upper.trace('w',self.update_running_time)
        self._new_fl_thk_lower.trace('w',self.update_running_time)
        self._new_algorithm_random_trials.trace('w',self.update_running_time)
        self._new_algorithm.trace('w',self.update_running_time)

        self.running_time_per_item = 4e-05*4
        self.initial_weight = op.calc_weight([self._spacing,self._pl_thk,self._stf_web_h,self._stf_web_thk,
                                              self._fl_w,self._fl_thk,self._new_span.get(),self._new_width_lg.get()])

        photo = tk.PhotoImage(file=image_dir+"img_plate_and_stiffener.gif")
        label = tk.Label(self._frame,image=photo)
        label.image = photo  # keep a reference!
        label.place(x=550, y=300)

        self._runnig_time_label.config(text=str(self.get_running_time()[0]))

        tk.Label(self._frame,text='Select algorithm', font = 'Verdana 8 bold').place(x=start_x+dx*11, y=start_y+0.5*dy)
        self._ent_algorithm.place(x=start_x+dx*11, y=start_y+dy)
        self.algorithm_random_label = tk.Label(self._frame, text='Number of trials')

        tk.Button(self._frame,text='algorith information',command=self.algorithm_info,bg='white')\
            .place(x=start_x+dx*11, y=start_y+dy*2)
        self.run_button = tk.Button(self._frame,text='RUN OPTIMIZATION!', command=self.run_optimizaion, bg='red',
                                    font='Verdana 10',fg='Yellow')
        self.run_button.place(x=start_x+dx*8, y=start_y+dy*0.5)
        self._opt_actual_running_time.place(x=start_x+dx*8, y=start_y+dy*1.5)

        self.close_and_save =tk.Button(self._frame,text='Return and replace initial strucutre with optimized',
                                       command=self.save_and_close,bg='green',font='Verdana 10',fg='yellow')
        self.close_and_save.place(x=start_x+dx*5,y=10)

        # Selection of constraints
        self._new_check_sec_mod = tk.BooleanVar()
        self._new_check_min_pl_thk = tk.BooleanVar()
        self._new_check_shear_area = tk.BooleanVar()
        self._new_check_buckling = tk.BooleanVar()
        self._new_check_fatigue = tk.BooleanVar()
        self._new_check_slamming = tk.BooleanVar()
        self._new_check_sec_mod.set(True)
        self._new_check_min_pl_thk.set(True)
        self._new_check_shear_area.set(True)
        self._new_check_buckling.set(True)
        self._new_check_fatigue.set(True)
        self._new_check_slamming.set(True)
        start_y = 140
        tk.Label(self._frame,text='Check for minimum section modulus').place(x=start_x+dx*9.7,y=start_y+4*dy)
        tk.Label(self._frame, text='Check for minimum plate thk.').place(x=start_x+dx*9.7,y=start_y+5*dy)
        tk.Label(self._frame, text='Check for minimum shear area').place(x=start_x+dx*9.7,y=start_y+6*dy)
        tk.Label(self._frame, text='Check for buckling (RP-C201)').place(x=start_x+dx*9.7,y=start_y+7*dy)
        tk.Label(self._frame, text='Check for fatigue (RP-C203)').place(x=start_x + dx * 9.7, y=start_y + 8 * dy)
        tk.Label(self._frame, text='Check for bow slamming').place(x=start_x + dx * 9.7, y=start_y + 9 * dy)

        tk.Checkbutton(self._frame,variable=self._new_check_sec_mod).place(x=start_x+dx*12,y=start_y+4*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_min_pl_thk).place(x=start_x+dx*12,y=start_y+5*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_shear_area).place(x=start_x+dx*12,y=start_y+6*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_buckling).place(x=start_x+dx*12,y=start_y+7*dy)
        tk.Checkbutton(self._frame, variable=self._new_check_fatigue).place(x=start_x + dx * 12, y=start_y + 8 * dy)
        tk.Checkbutton(self._frame, variable=self._new_check_slamming).place(x=start_x + dx * 12, y=start_y + 9 * dy)

        self.draw_properties()

    def selected_algorithm(self,event):
        '''
        Action when selecting an algorithm.
        :return:
        '''
        start_x, start_y, dx, dy = 20, 100, 100, 40
        if self._new_algorithm.get()=='random' or self._new_algorithm.get()=='random_no_delta':
            self._ent_random_trials.place_forget()
            self.algorithm_random_label.place_forget()
            self._lb_swarm_size.place_forget()
            self._lb_omega.place_forget()
            self._lb_phip.place_forget()
            self._lb_phig.place_forget()
            self._lb_maxiter.place_forget()
            self._lb_minstep.place_forget()
            self._lb_minfunc.place_forget()
            self._ent_swarm_size.place_forget()
            self._ent_omega.place_forget()
            self._ent_phip.place_forget()
            self._ent_phig.place_forget()
            self._ent_maxiter.place_forget()
            self._ent_minstep.place_forget()
            self._ent_minfunc.place_forget()
            self._ent_random_trials.place(x=start_x+dx*11.3, y=start_y+1.2*dy)
            self.algorithm_random_label.place(x=start_x+dx*11.3, y=start_y+0.5*dy)
        elif self._new_algorithm.get()=='anysmart' or self._new_algorithm.get()=='anydetail':
            self._ent_random_trials.place_forget()
            self.algorithm_random_label.place_forget()
            self._lb_swarm_size.place_forget()
            self._lb_omega.place_forget()
            self._lb_phip.place_forget()
            self._lb_phig.place_forget()
            self._lb_maxiter.place_forget()
            self._lb_minstep.place_forget()
            self._lb_minfunc.place_forget()
            self._ent_swarm_size.place_forget()
            self._ent_omega.place_forget()
            self._ent_phip.place_forget()
            self._ent_phig.place_forget()
            self._ent_maxiter.place_forget()
            self._ent_minstep.place_forget()
            self._ent_minfunc.place_forget()

        elif self._new_algorithm.get()=='pso':
            y_place_label =11.2
            y_place = 12.2
            self._ent_random_trials.place_forget()
            
            self._lb_swarm_size.place(x=start_x+dx*y_place_label, y=start_y-2*dy)
            self._lb_omega.place(x=start_x+dx*y_place_label, y=start_y-1*dy)
            self._lb_phip.place(x=start_x+dx*y_place_label, y=start_y-0*dy)
            self._lb_phig.place(x=start_x+dx*y_place_label, y=start_y+1*dy)
            self._lb_maxiter.place(x=start_x+dx*y_place_label, y=start_y+2*dy)
            self._lb_minstep.place(x=start_x+dx*y_place_label, y=start_y+3*dy)
            self._lb_minfunc.place(x=start_x+dx*y_place_label, y=start_y+4*dy)
            
            self._ent_swarm_size.place(x=start_x+dx*y_place, y=start_y-2*dy)
            self._ent_omega.place(x=start_x+dx*y_place, y=start_y-1*dy)
            self._ent_phip.place(x=start_x+dx*y_place, y=start_y+0*dy)
            self._ent_phig.place(x=start_x+dx*y_place, y=start_y+1*dy)
            self._ent_maxiter.place(x=start_x+dx*y_place, y=start_y+2*dy)
            self._ent_minstep.place(x=start_x+dx*y_place, y=start_y+3*dy)
            self._ent_minfunc.place(x=start_x+dx*y_place, y=start_y+4*dy)

    def modify_structure_object(self):
        ''' Chaning parameters in the structure object before running. '''
        pass

    def run_optimizaion(self):
        '''
        function for button
        :return:
        '''
        t_start = time.time()
        self._opt_actual_running_time.config(text='')
        self.pso_parameters = (self._new_swarm_size.get(),self._new_omega.get(),self._new_phip.get(),self._new_phig.get(),
                               self._new_maxiter.get(),self._new_minstep.get(),self._new_minfunc.get())

        contraints = (self._new_check_sec_mod.get(),self._new_check_min_pl_thk.get(),
                      self._new_check_shear_area.get(), self._new_check_buckling.get(),
                      self._new_check_fatigue.get(), self._new_check_slamming.get())
        self._initial_structure_obj.set_span(self._new_span.get())

        if self._fatigue_pressure is not None:

            fat_press = ((self._fatigue_pressure['p_ext']['loaded'],self._fatigue_pressure['p_ext']['ballast'],
                          self._fatigue_pressure['p_ext']['part']),
                         (self._fatigue_pressure['p_int']['loaded'],self._fatigue_pressure['p_int']['ballast'],
                          self._fatigue_pressure['p_int']['part']))
        else:
            fat_press = None


        self._opt_results= op.run_optmizataion(self._initial_structure_obj,self.get_lower_bounds(),
                                               self.get_upper_bounds(),self._new_design_pressure.get(),
                                               self.get_deltas(),algorithm=self._new_algorithm.get(),
                                               trials=self._new_algorithm_random_trials.get(),
                                               side=self._new_pressure_side.get(),
                                               const_chk=contraints,pso_options = self.pso_parameters,
                                               fatigue_obj=self._fatigue_object,
                                               fat_press_ext_int=fat_press,
                                               slamming_press = self._new_slamming_pressure.get())

        if self._opt_results is not None:
            self._opt_actual_running_time.config(text='Actual running time: \n'
                                                     +str(time.time()-t_start)+' sec')
            self._opt_runned = True
            self._result_label.config(text='Optimization result | Spacing: '+str(self._opt_results[0].get_s()*1000)+
                                          ' Plate thickness: '+str(self._opt_results[0].get_plate_thk()*1000)+
                                          ' Stiffener - T'+str(self._opt_results[0].get_web_h()*1000)+'x'
                                          +str(self._opt_results[0].get_web_thk()*1000)+
                                          '+'+str(self._opt_results[0].get_fl_w()*1000)+'x'
                                          +str(self._opt_results[0].get_fl_thk()*1000))

            self._new_opt_spacing.set(round(self._opt_results[0].get_s(),5))
            self._new_opt_pl_thk.set(round(self._opt_results[0].get_plate_thk(),5))
            self._new_opt_web_h.set(round(self._opt_results[0].get_web_h(),5))
            self._new_opt_web_thk.set(round(self._opt_results[0].get_web_thk(),5))
            self._new_opt_fl_w.set(round(self._opt_results[0].get_fl_w(),5))
            self._new_opt_fl_thk.set(round(self._opt_results[0].get_fl_thk(),5))
            self.draw_properties()
        else:
            messagebox.showinfo(title='Nothing found', message='No better alternatives found. Modify input.\n'
                                                               'There may be no alternative that is acceptable.\n')

    def get_running_time(self):
        '''
        Estimate the running time of the algorithm.
        :return:
        '''

        if self._new_algorithm.get() in ['anysmart','anydetail']:
            try:
                number_of_combinations = \
                max((self._new_spacing_upper.get()-self._new_spacing_lower.get())/self._new_delta_spacing.get(),1)* \
                max((self._new_pl_thk_upper.get()-self._new_pl_thk_lower.get())/self._new_delta_pl_thk.get(),1)*\
                max((self._new_web_h_upper.get()-self._new_web_h_lower.get())/self._new_delta_web_h.get(),1)*\
                max((self._new_web_thk_upper.get()-self._new_web_thk_lower.get())/self._new_delta_web_thk.get(),1)*\
                max((self._new_fl_w_upper.get()-self._new_fl_w_lower.get())/self._new_delta_fl_w.get(),1)*\
                max((self._new_fl_thk_upper.get()-self._new_fl_thk_lower.get())/self._new_delta_fl_thk.get(),1)
                return int(number_of_combinations*self.running_time_per_item),number_of_combinations
            except TclError:
                return 0,0
        elif self._new_algorithm.get() in ['pso','random','random_no_delta']:
            try:
                number_of_combinations = \
                max((self._new_spacing_upper.get()-self._new_spacing_lower.get())/self._new_delta_spacing.get(),1)* \
                max((self._new_pl_thk_upper.get()-self._new_pl_thk_lower.get())/self._new_delta_pl_thk.get(),1)*\
                max((self._new_web_h_upper.get()-self._new_web_h_lower.get())/self._new_delta_web_h.get(),1)*\
                max((self._new_web_thk_upper.get()-self._new_web_thk_lower.get())/self._new_delta_web_thk.get(),1)*\
                max((self._new_fl_w_upper.get()-self._new_fl_w_lower.get())/self._new_delta_fl_w.get(),1)*\
                max((self._new_fl_thk_upper.get()-self._new_fl_thk_lower.get())/self._new_delta_fl_thk.get(),1)
                return int(number_of_combinations*self.running_time_per_item/4),number_of_combinations
            except TclError:
                return 0,0
        else:
            try:
                return int(self._new_algorithm_random_trials.get() * self.running_time_per_item),\
                       self._new_algorithm_random_trials.get()
            except TclError:
                return 0,0

    def get_deltas(self):
        '''
        Return a numpy array of the deltas.
        :return:
        '''
        return np.array([float(self._ent_delta_spacing.get())/1000,float(self._new_delta_pl_thk.get())/1000,
                         float(self._new_delta_web_h.get())/1000,float(self._new_delta_web_thk.get())/1000,
                         float(self._new_delta_fl_w.get())/1000,float(self._new_delta_fl_thk.get())/1000])

    def update_running_time(self,*args):
        '''
        Estimate the running time of the algorithm.
        :return:
        '''

        try:
            self._runnig_time_label.config(text=str(self.get_running_time()[0]))
        except ZeroDivisionError:
            pass# _tkinter.TclError: pass
    
    def get_upper_bounds(self):
        '''
        Return an numpy array of upper bounds.
        :return: 
        '''
        return np.array([self._new_spacing_upper.get()/1000,self._new_pl_thk_upper.get()/1000,
                         self._new_web_h_upper.get()/1000,self._new_web_thk_upper.get()/1000,
                         self._new_fl_w_upper.get()/1000,self._new_fl_thk_upper.get()/1000,
                         self._new_span.get(),self._new_width_lg.get()])
        
    def get_lower_bounds(self):
        '''
        Return an numpy array of lower bounds.
        :return: 
        '''
        return np.array([self._new_spacing_lower.get()/1000,self._new_pl_thk_lower.get()/1000,
                         self._new_web_h_lower.get()/1000,self._new_web_thk_lower.get()/1000,
                         self._new_fl_w_lower.get()/1000,self._new_fl_thk_lower.get()/1000,
                         self._new_span.get(), self._new_width_lg.get()])

    def get_sigmas(self):
        '''
        Returns the stressess.
        :return:
        '''
        return np.array([self._new_trans_stress_high.get(),self._new_trans_stress_low.get(),
                         self._new_axial_stress.get(),self._new_shear_stress.get()])

    def checkered(self,line_distance):
        # vertical lines at an interval of "line_distance" pixel
        for x in range(line_distance, self._canvas_dim[0], line_distance):
            self._canvas_opt.create_line(x, 0, x, self._canvas_dim[0], fill="grey",stipple='gray50')
        # horizontal lines at an interval of "line_distance" pixel
        for y in range(line_distance, self._canvas_dim[1], line_distance):
            self._canvas_opt.create_line(0, y, self._canvas_dim[0], y, fill="grey",stipple='gray50')

    def draw_properties(self):
        '''
        Drawing properties in the canvas.
        :return:
        '''
        self._canvas_opt.delete('all')
        self.checkered(10)
        ctr_x = self._canvas_dim[0]/2
        ctr_y = self._canvas_dim[1]/2+200
        m = self._draw_scale
        init_color,init_stipple = 'blue','gray12'
        opt_color,opt_stippe = 'red','gray12'
        self._canvas_opt.create_rectangle(0,0,self._canvas_dim[0]+10,80,fill='white')
        self._canvas_opt.create_line(10,10,30,10,fill = init_color,width=5)
        self._canvas_opt.create_text(270,10,text='Initial    - Pl.: '+str(self._spacing*1000) +'x'+str(self._pl_thk*1000)+
                                               ' Stf.: '+str(self._stf_web_h*1000)+'x'+str(self._stf_web_thk*1000)+'+'+
                                               str(self._fl_w*1000)+'x'+str(self._fl_thk*1000), font = 'Verdana 8',
                                    fill = init_color)
        self._canvas_opt.create_text(120,30,text='Weight (per Lg width): '+str(int(self.initial_weight)),
                                    font = 'Verdana 8',fill = init_color)

        self._canvas_opt.create_rectangle(ctr_x-m*self._spacing/2, ctr_y,ctr_x+m*self._spacing/2,
                                         ctr_y-m*self._pl_thk, fill=init_color, stipple=init_stipple )
        self._canvas_opt.create_rectangle(ctr_x - m * self._stf_web_thk / 2, ctr_y-m* self._pl_thk,
                                         ctr_x + m * self._stf_web_thk / 2, ctr_y - m *(self._stf_web_h+self._pl_thk)
                                         , fill=init_color, stipple=init_stipple )
        if self._initial_structure_obj.get_stiffener_type() != 'L':
            self._canvas_opt.create_rectangle(ctr_x-m*self._fl_w/2, ctr_y-m*(self._pl_thk+self._stf_web_h),
                                             ctr_x+m*self._fl_w/2, ctr_y-m*(self._pl_thk+self._stf_web_h+self._fl_thk),
                                             fill=init_color, stipple=init_stipple)
        else:
            self._canvas_opt.create_rectangle(ctr_x-m*self._stf_web_thk/2, ctr_y-m*(self._pl_thk+self._stf_web_h),
                                             ctr_x+m*self._fl_w, ctr_y-m*(self._pl_thk+self._stf_web_h+self._fl_thk),
                                             fill=init_color, stipple=init_stipple)



        if self._opt_runned:
            # [0.6, 0.012, 0.25, 0.01, 0.1, 0.01]
            #print(self._opt_results)
            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_s() / 2, ctr_y,
                                             ctr_x + m * self._opt_results[0].get_s()  / 2,
                                             ctr_y - m * self._opt_results[0].get_pl_thk(), fill=opt_color,
                                             stipple=opt_stippe)

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_web_thk() / 2, ctr_y -
                                             m * self._opt_results[0].get_pl_thk(),
                                             ctr_x + m * self._opt_results[0].get_web_thk() / 2,
                                             ctr_y - m * (self._opt_results[0].get_web_h() + self._opt_results[0].get_pl_thk())
                                             , fill=opt_color, stipple=opt_stippe)
            if self._initial_structure_obj.get_stiffener_type() != 'L':
                self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_fl_w() / 2, ctr_y
                                                 - m * (self._opt_results[0].get_pl_thk()+ self._opt_results[0].get_web_h()),
                                                 ctr_x + m * self._opt_results[0].get_fl_w() / 2,ctr_y -
                                                 m * (self._opt_results[0].get_pl_thk() + self._opt_results[0].get_web_h() +
                                                      self._opt_results[0].get_fl_thk()),
                                                 fill=opt_color, stipple=opt_stippe)
            else:
                self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_web_thk() / 2, ctr_y
                                                 - m * (self._opt_results[0].get_pl_thk()+ self._opt_results[0].get_web_h()),
                                                 ctr_x + m * self._opt_results[0].get_fl_w() ,ctr_y -
                                                 m * (self._opt_results[0].get_pl_thk() + self._opt_results[0].get_web_h() +
                                                      self._opt_results[0].get_fl_thk()),
                                                 fill=opt_color, stipple=opt_stippe)

            self._canvas_opt.create_line(10, 50, 30, 50, fill=opt_color, width=5)
            self._canvas_opt.create_text(270,50,text='Optimized - Pl.: '+str(self._opt_results[0].get_s()*1000) +'x'+
                                                    str(self._opt_results[0].get_pl_thk()*1000)+' Stf.: '
                                                    +str(self._opt_results[0].get_web_h()*1000)+
                                                    'x'+str(self._opt_results[0].get_web_thk()*1000)+'+'+
                                                            str(self._opt_results[0].get_fl_w()*1000)+
                                                    'x'+str(self._opt_results[0].get_fl_thk()*1000),
                                        font = 'Verdana 8',fill = opt_color)
            self._canvas_opt.create_text(120, 70, text='Weight (per Lg width): '
                                                      + str(int(op.calc_weight([self._opt_results[0].get_s(),
                                                                                self._opt_results[0].get_pl_thk(),
                                                                                self._opt_results[0].get_web_h(),
                                                                                self._opt_results[0].get_web_thk(),
                                                                                self._opt_results[0].get_fl_w(),
                                                                                self._opt_results[0].get_fl_thk(),
                                                                                self._new_span.get(),
                                                                                self._new_width_lg.get()]))),
                                        font='Verdana 8', fill=opt_color)

    def save_and_close(self):
        '''
        Save and close
        :return:
        '''
        print(self._opt_results)
        if __name__ == '__main__':
            self._frame.destroy()
            return

        try:
            self.app.on_close_opt_window(self._opt_results)
        except (IndexError, TypeError):
            messagebox.showinfo(title='Nothing to return',message='No results to return.')
            return
        self._frame.destroy()

    def algorithm_info(self):
        ''' When button is clicked, info is displayed.'''

        messagebox.showinfo(title='Algorith information',
                            message='The algorithms currently included is:\n'
                                    'ANYSMART:  \n'
                                    '           Calculates all alternatives using upper and lower bounds.\n'
                                    '           The step used inside the bounds is defined in deltas.\n'
                                    '           This algoritm uses MULTIPROCESSING and will be faster.\n\n'
                                    'RANDOM:    \n'
                                    '           Uses the same bounds and deltas as in ANYSMART.\n'
                                    '           Number of combinations calculated is defined in "trials",\n'
                                    '           which selects withing the bounds and deltas defined.\n\n'
                                    'RANDOM_NO_BOUNDS:\n'
                                    '           Same as RANDOM, but does not use the defined deltas.\n'
                                    '           The deltas is set to 1 mm for all dimensions/thicknesses.\n\n'
                                    'ANYDETAIL:\n'
                                    '           Same as for ANYSMART, but will take some more time and\n'
                                    '           provide a chart of weight development during execution.\n\n'
                                    'PSO - Particle Swarm Search:\n'
                                    '           The information can be found on \n'
                                    '           http://pythonhosted.org/pyswarm/ \n'
                                    '           For further information google it!\n'
                                    '           Parameters:\n'
                                    '           swarmsize : The number of particles in the swarm (Default: 100)\n'
                                    '           omega : Particle velocity scaling factor (Default: 0.5)\n'
                                    '           phip : Scaling factor to search away from the particle’s \n'
                                    '                           best known position (Default: 0.5)\n'
                                    '           phig : Scaling factor to search away from the swarm’s best \n'
                                    '                           known position (Default: 0.5)\n'
                                    '           maxiter : The maximum number of iterations for the swarm \n'
                                    '                           to search (Default: 100)\n'
                                    '           minstep : The minimum stepsize of swarm’s best position \n'
                                    '                           before the search terminates (Default: 1e-8)\n'
                                    '           minfunc : The minimum change of swarm’s best objective value\n'
                                    '                           before the search terminates (Default: 1e-8)\n\n'
                            
                                    '\n'
                                    'All algorithms calculates local scantling and buckling requirements')

def receive_progress_info():
    '''
    Get progress info from optimization algorithm.
    :return:
    '''
    print('hi')

if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateOptimizeWindow(master=root)
    root.mainloop()




