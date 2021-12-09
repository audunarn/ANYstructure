# This is where the optimization is done.
import tkinter as tk
from _tkinter import TclError

import ANYstructure_local.main_application
import ANYstructure_local.optimize as op
import numpy as np
import time, os, datetime
from tkinter import messagebox
import ANYstructure_local.example_data as test
import ANYstructure_local.helper as hlp
import ANYstructure_local.calc_structure as calc
from tkinter.filedialog import askopenfilenames
from multiprocessing import cpu_count

class CreateOptimizeCylinderWindow():
    '''
    This class initiates the single optimization window.
    '''

    def __init__(self,master,app=None):
        super(CreateOptimizeCylinderWindow,self).__init__()
        if __name__ == '__main__':
            import pickle
            self._initial_structure_obj = test.get_structure_calc_object(heavy=True)
            self._initial_calc_obj = test.get_structure_calc_object(heavy=True)
            self._lateral_pressure = -0.2e6
            self._fatigue_object = test.get_fatigue_object()
            self._fatigue_pressure = test.get_fatigue_pressures()
            self._slamming_pressure = test.get_slamming_pressure()
            image_dir = os.path.dirname(__file__)+'\\images\\'
            self._PULS_object = None
            self._puls_acceptance = 0.87

            self._initial_cylinder_obj = calc.CylinderAndCurvedPlate(main_dict=test.shell_main_dict,
                                                                     shell=calc.Shell(test.shell_dict),
                                            long_stf=calc.Structure(test.obj_dict_cyl_long2),
                                            ring_stf=None,#calc.Structure(test.obj_dict_cyl_ring2),
                                            ring_frame=None)#calc.Structure(test.obj_dict_cyl_heavy_ring2))

            self._ML_buckling = dict()  # Buckling machine learning algorithm
            for name, file_base in zip(['cl SP buc int predictor', 'cl SP buc int scaler',
                                        'cl SP ult int predictor', 'cl SP ult int scaler',
                                        'cl SP buc GLGT predictor', 'cl SP buc GLGT scaler',
                                        'cl SP ult GLGT predictor', 'cl SP ult GLGT scaler',
                                        'cl UP buc int predictor', 'cl UP buc int scaler',
                                        'cl UP ult int predictor', 'cl UP ult int scaler',
                                        'cl UP buc GLGT predictor', 'cl UP buc GLGT scaler',
                                        'cl UP ult GLGT predictor', 'cl UP ult GLGT scaler'
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

            self._ML_classes = {0: 'N/A',
                                1: 'A negative utilisation factor is found.',
                                2: 'At least one of the in-plane loads must be non-zero.',
                                3: 'Division by zero',
                                4: 'Overflow',
                                5: 'The aspect ratio exceeds the PULS code limit',
                                6: 'The global slenderness exceeds 4. Please reduce stiffener span or increase stiffener height.',
                                7: 'The applied pressure is too high for this plate field.', 8: 'web-flange-ratio',
                                9: 'UF below or equal 0.87', 10: 'UF between 0.87 and 1.0', 11: 'UF above 1.0'}
        else:
            self.app = app
            self._initial_structure_obj = app._line_to_struc[app._active_line][0]
            self._initial_calc_obj = app._line_to_struc[app._active_line][1]
            self._initial_cylinder_obj = app._line_to_struc[app._active_line][5]
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
            self._root_dir = app._root_dir
            self._PULS_object = app._PULS_results
            self._puls_acceptance = self.app._new_puls_uf.get()

            self._ML_buckling = app._ML_buckling



        self._frame = master
        self._frame.wm_title("Optimize structure")
        self._frame.geometry('1600x900')
        self._frame.grab_set()

        '''
            shell_upper_bounds = np.array( [0.03, 3, 5, 5, 10, None, None, None])
            shell_deltas = np.array(       [0.005, 0.5, 1, 0.1,1, None, None, None])
            shell_lower_bounds = np.array( [0.02, 2.5, 5, 5, 10, None, None, None])
        
            long_upper_bounds = np.array(   [0.8, None, 0.5, 0.02, 0.2, 0.03, None, None])
            long_deltas = np.array(         [0.1, None, 0.1, 0.01, 0.1, 0.01, None, None])
            long_lower_bounds = np.array(   [0.7, None, 0.3,  0.01, 0.1, 0.01, None, None])
        
            ring_stf_upper_bounds = np.array(   [None, None, 0.5, 0.018, 0.2, 0.03, None, None])
            ring_stf_deltas = np.array(         [None, None, 0.1, 0.004, 0.1, 0.01, None, None])
            ring_stf_lower_bounds = np.array(   [None, None, 0.3,  0.010, 0.1, 0.010, None, None])
        
            ring_frame_upper_bounds = np.array( [None, None, 0.9, 0.04, 0.3, 0.04, None, None])
            ring_frame_deltas = np.array(       [None, None, 0.2, 0.01, 0.1, 0.01, None, None])
            ring_frame_lower_bounds = np.array( [None, None, 0.7,  0.02, 0.2, 0.02, None, None])
        '''
        ent_w = 10

        default_shell_upper_bounds = np.array([0.03, 3, 5, 5, 10, None, None, None])
        default_shell_deltas = np.array([0.005, 0.5, 1, 0.1, 1, None, None, None])
        default_shell_lower_bounds = np.array([0.02, 2.5, 5, 5, 10, None, None, None])

        default_long_upper_bounds = np.array([0.8, None, 0.5, 0.02, 0.2, 0.03, None, None])
        default_long_deltas = np.array([0.1, None, 0.1, 0.01, 0.1, 0.01, None, None])
        default_long_lower_bounds = np.array([0.7, None, 0.3, 0.01, 0.1, 0.01, None, None])

        default_ring_stf_upper_bounds = np.array([None, None, 0.5, 0.018, 0.2, 0.03, None, None])
        default_ring_stf_deltas = np.array([None, None, 0.1, 0.004, 0.1, 0.01, None, None])
        default_ring_stf_lower_bounds = np.array([None, None, 0.3, 0.010, 0.1, 0.010, None, None])

        default_ring_frame_upper_bounds = np.array([None, None, 0.9, 0.04, 0.3, 0.04, None, None])
        default_ring_frame_deltas = np.array([None, None, 0.2, 0.01, 0.1, 0.01, None, None])
        default_ring_frame_lower_bounds = np.array([None, None, 0.7, 0.02, 0.2, 0.02, None, None])
        
        self._default_data =  [[default_shell_upper_bounds,default_shell_deltas, default_shell_lower_bounds],
                              [default_long_upper_bounds, default_long_deltas, default_long_lower_bounds],
                              [default_ring_stf_upper_bounds, default_ring_stf_deltas, default_ring_stf_lower_bounds],
                              [default_ring_frame_upper_bounds, default_ring_frame_deltas,
                               default_ring_frame_lower_bounds]]

        shell_example = [0.03, 3, 5, 5, 10, None, None, None]
        long_example = ring_stf_example = ring_frame_example =  [0.8, None, 0.5, 0.02, 0.2, 0.03, None, None]

        shell_upper_bounds = [tk.DoubleVar() for dummy in shell_example]
        shell_deltas = [tk.DoubleVar() for dummy in shell_example]
        shell_lower_bounds = [tk.DoubleVar() for dummy in shell_example]
        
        long_upper_bounds = [tk.DoubleVar() for dummy in long_example]
        long_deltas = [tk.DoubleVar() for dummy in long_example]
        long_lower_bounds = [tk.DoubleVar() for dummy in long_example]
        
        ring_stf_upper_bounds = [tk.DoubleVar() for dummy in ring_stf_example]
        ring_stf_deltas = [tk.DoubleVar() for dummy in ring_stf_example]
        ring_stf_lower_bounds = [tk.DoubleVar() for dummy in ring_stf_example]
        
        ring_frame_upper_bounds = [tk.DoubleVar() for dummy in ring_frame_example]
        ring_frame_deltas = [tk.DoubleVar() for dummy in ring_frame_example]
        ring_frame_lower_bounds = [tk.DoubleVar() for dummy in ring_frame_example]
        self._new_geo_data = list()

        self._new_geo_data =  [[shell_upper_bounds,shell_deltas, shell_lower_bounds],
                              [long_upper_bounds, long_deltas, long_lower_bounds],
                              [ring_stf_upper_bounds, ring_stf_deltas, ring_stf_lower_bounds],
                              [ring_frame_upper_bounds, ring_frame_deltas, ring_frame_lower_bounds]]

        self._new_entries = list()
        map_type = {'shell':0, 'long':1, 'ring stf': 2, 'ring heavy':3}
        map_type_idx = {0: True, 1: self._initial_cylinder_obj.LongStfObj is not None,
                        2: self._initial_cylinder_obj.RingStfObj is not None,
                        3: self._initial_cylinder_obj.RingFrameObj is not None}

        for idx_1, geo_i in enumerate(self._new_geo_data):
            all_geos = list()
            if map_type_idx[idx_1] == False:
                continue
            for idx_2, entries in enumerate(geo_i):
                these_ents = list()
                for idx_3, ent_i in enumerate(entries):
                    self._new_geo_data[idx_1][idx_2][idx_3].trace('w', self.update_running_time)
                    these_ents.append(tk.Entry(self._frame,
                                               textvariable = self._new_geo_data[idx_1][idx_2][idx_3], width = ent_w))
                    self._new_geo_data[idx_1][idx_2][idx_3].set(0 if self._default_data[idx_1][idx_2][idx_3] is None
                                                                else self._default_data[idx_1][idx_2][idx_3]*1000)
                all_geos.append(these_ents)
            self._new_entries.append(all_geos)
        
        self._predefined_stiffener_iter = None

        self._opt_runned = False
        self._opt_results = ()
        self._opt_actual_running_time = tk.Label(self._frame,text='',font='Verdana 12 bold')


        self._draw_scale = 600
        self._canvas_dim = (550, 500)
        self._canvas_opt = tk.Canvas(self._frame,width=self._canvas_dim[0], height=self._canvas_dim[1], 
                                     background='azure',relief = 'groove', borderwidth=2)


        # tk.Frame(self._frame,width=770,height=5, bg="grey", colormap="new").place(x=20,y=127)
        # tk.Frame(self._frame, width=770, height=5, bg="grey", colormap="new").place(x=20, y=167)

        self._canvas_opt.place(x=1000,y=350)

        algorithms = ('anysmart cylinder','random','random_no_delta')

        tk.Label(self._frame,text='-- Cylinder optimizer --',font='Verdana 15 bold').place(x=10,y=10)


        # upper and lower bounds for optimization
        #[0.6, 0.012, 0.3, 0.01, 0.1, 0.01]

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



        # stresses in plate and stiffener

        self._new_sasd = tk.DoubleVar()
        self._new_smsd = tk.DoubleVar()
        self._new_tTsd = tk.DoubleVar()
        self._new_tQsd = tk.DoubleVar()
        self._new_design_pressure = tk.DoubleVar()
        self._new_shsd = tk.DoubleVar()


        self._ent_sasd = tk.Entry(self._frame, textvariable=self._new_sasd, width=ent_w)
        self._ent_smsd = tk.Entry(self._frame, textvariable=self._new_smsd, width=ent_w)
        self._ent_tTsd = tk.Entry(self._frame, textvariable=self._new_tTsd, width=ent_w)
        self._ent_tQsd = tk.Entry(self._frame, textvariable=self._new_tQsd, width=ent_w)
        self._ent_design_pressure = tk.Entry(self._frame, textvariable=self._new_design_pressure, width=ent_w)
        self._ent_shsd = tk.Entry(self._frame, textvariable=self._new_shsd, width=ent_w)


        start_x,start_y,dx,dy = 20,100,100,40

        self._new_processes = tk.IntVar()
        self._new_processes.set(max(cpu_count() - 1, 1))
        tk.Label(self._frame, text='Processes\n (CPUs)', font='Verdana 9 bold', bg = 'silver')\
            .place(x=start_x + 10 * dx, y=start_y - 1.1 * dy)
        tk.Entry(self._frame, textvariable=self._new_processes, width = 12, bg = 'silver')\
            .place(x=start_x + 10 * dx, y=start_y - 0.3 * dy)




        self._runnig_time_label = tk.Label(self._frame, text='',font='Verdana 12 bold', fg = 'red')
        self._runnig_time_label.place(x=start_x+4.3*dx, y=start_y + 2.8 * dy)
        #tk.Label(self._frame, text='seconds ',font='Verdana 9 bold').place(x=start_x+6*dx, y=start_y + 2.8 * dy)
        self._result_label = tk.Label(self._frame, text = '',font = 'Verdana 9 bold' )
        self._result_label.place(x=start_x, y=start_y + 4.2 * dy)

        '''
                self._new_geo_data =  [[shell_upper_bounds,shell_deltas, shell_lower_bounds],
                              [long_upper_bounds, long_deltas, long_lower_bounds],
                              [ring_stf_upper_bounds, ring_stf_deltas, ring_stf_lower_bounds],
                              [ring_frame_upper_bounds, ring_frame_deltas, ring_frame_lower_bounds]]
        '''
        shell = ['Shell thk. [mm]', 'Shell radius [mm]', 'l rings [mm]', 'L shell [mm]', 'L tot. [mm]', 'N/A - future',
                 'N/A - future', 'N/A - future']
        stf_long = ['Spacing [mm]', 'N/A', 'Web height [mm]', 'Web thk. [mm]', 'Flange width [mm]',
                    'Flange thk. [mm]', 'N/A - future', 'N/A - future']
        stf_ring = ['N/A', 'N/A', 'Web height [mm]', 'Web thk. [mm]', 'Flange width [mm]',
                    'Flange thk. [mm]', 'N/A - future', 'N/A - future']
        all_label = [shell, stf_long, stf_ring, stf_ring]
        text_i = ['Upper bounds [mm]', 'Iteration delta [mm]','Lower bounds [mm]']
        kind = ['Shell or panel', 'Longitudinal stiffener', 'Ring stiffener', 'Ring frame/girder']
        for idx_1, member in enumerate(self._new_entries):
            if map_type_idx[idx_1] == False:
                continue
            for idx_2, bounds in enumerate(member):
                tk.Label(self._frame, text=text_i[idx_2], font='Verdana 9').place(x=start_x,
                                                                                  y=start_y + dy * idx_1 * 4 + dy * idx_2)
                if idx_2 == 0:
                    tk.Label(self._frame, text=kind[idx_1], font='Verdana 10 bold') \
                        .place(x=start_x, y=start_y + dy * idx_1 * 4 + dy * idx_2 - dy * 0.5)
                for idx_3, entry_i in enumerate(bounds):
                    if idx_2 == 0:
                        tk.Label(self._frame, text=all_label[idx_1][idx_3], font='Verdana 7 bold')\
                            .place(x = start_x+dx*2 + idx_3*dx, y = start_y+dy*idx_1*4 + dy*idx_2 -dy*0.5)

                    entry_i.place(x = start_x+dx*2 + idx_3*dx, y = start_y+dy*idx_1*4 + dy*idx_2)
                    if 'N/A' in all_label[idx_1][idx_3]:
                        entry_i.configure(bg = 'grey')


        
        ###
        
        #Labels for the pso
 
        self._lb_swarm_size = tk.Label(self._frame,text='swarm size')
        self._lb_omega  = tk.Label(self._frame,text='omega')
        self._lb_phip  = tk.Label(self._frame,text='phip')
        self._lb_phig  = tk.Label(self._frame,text='phig')
        self._lb_maxiter = tk.Label(self._frame,text='maxiter')
        self._lb_minstep  = tk.Label(self._frame,text='minstep')
        self._lb_minfunc  = tk.Label(self._frame,text='minfunc')

        ###
        dys = 0.9*dy
        tk.Label(self._frame, text='Design axial stress,          sa,sd', font='Verdana 9')\
            .place(x=start_x+10*dx,y=start_y+1*dys)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*14,y=start_y+1*dys)

        tk.Label(self._frame, text='Design bending stress,   sm,sd', font='Verdana 9')\
            .place(x=start_x+10*dx,y=start_y+2*dys)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*14,y=start_y+2*dys)

        tk.Label(self._frame, text='Design torsional stress,   tT,sd', font='Verdana 9')\
            .place(x=start_x+10*dx,y=start_y+3*dys)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*14,y=start_y+3*dys)

        tk.Label(self._frame, text='Design shear stress,        tQ,sd', font='Verdana 9')\
            .place(x=start_x+10*dx,y=start_y+4*dys)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*14,y=start_y+4*dys)

        tk.Label(self._frame, text='Design lateral pressure,    psd', font='Verdana 9 bold')\
            .place(x=start_x+10*dx,y=start_y+5*dys)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*14,y=start_y+5*dys)
        
        tk.Label(self._frame, text='Additional hoop stress, sh,sd,    psd', font='Verdana 9 bold')\
            .place(x=start_x+10*dx,y=start_y+6*dys)
        tk.Label(self._frame, text='MPa', font='Verdana 9')\
            .place(x=start_x+dx*14,y=start_y+6*dys)
        
        self._ent_sasd.place(x=start_x+dx*13,y=start_y+1*dys)
        self._ent_smsd.place(x=start_x+dx*13,y=start_y+2*dys)
        self._ent_tTsd.place(x=start_x+dx*13,y=start_y+3*dys)
        self._ent_tQsd.place(x=start_x + dx * 13, y=start_y + 4 * dys)
        self._ent_design_pressure.place(x=start_x + dx * 13, y=start_y + 5 * dys)
        self._ent_shsd.place(x=start_x + dx * 13, y=start_y +6 * dys)
        

        if self._fatigue_pressure is not None:
            tk.Label(self._frame, text='Fatigue pressure: internal= '+str(self._fatigue_pressure['p_int'])+ ' external= '
                                       +str(self._fatigue_pressure['p_ext']), font='Verdana 7') \
                .place(x=start_x + dx * 5, y=start_y + 19.3 * dy)
        else:
            tk.Label(self._frame, text='Fatigue pressure: internal= '+str(0)+ ' external= '
                                       +str(0), font='Verdana 7') \
                .place(x=start_x + dx * 5, y=start_y + 19.3 * dy)




        #setting default values
        init_dim = float(10) #mm
        init_thk = float(1) #mm

        self._new_design_pressure.set(self._lateral_pressure)
        self._new_slamming_pressure.set(self._slamming_pressure)
        if self._fatigue_pressure is None:
            self._new_fatigue_ext_press.set(0), self._new_fatigue_int_press.set(0)
        else:
            self._new_fatigue_int_press.set(self._fatigue_pressure['p_int']), \
            self._new_fatigue_ext_press.set(self._fatigue_pressure['p_ext'])

        self._new_algorithm.set('anysmart cylinder')
        self._new_algorithm_random_trials.set(100000)
        self._new_swarm_size.set(100)
        self._new_omega.set(0.5)
        self._new_phip.set(0.5)
        self._new_phig.set(0.5)
        self._new_maxiter.set(100)
        self._new_minstep.set(1e-8)
        self._new_minfunc.set(1e-8)

        self._new_algorithm_random_trials.trace('w',self.update_running_time)
        self._new_algorithm.trace('w',self.update_running_time)


        # self.running_time_per_item = {'PULS':0.2489626556016598, 'RP': 1.009943181818182e-5}
        # self.initial_weight = op.calc_weight([self._spacing,self._pl_thk,self._stf_web_h,self._stf_web_thk,
        #                                       self._fl_w,self._fl_thk,self._new_span.get(),self._new_width_lg.get()])

        # img_file_name = 'img_plate_and_stiffener.gif'
        # if os.path.isfile('images/' + img_file_name):
        #     file_path = 'images/' + img_file_name
        # else:
        #     file_path = self._root_dir + '/images/' + img_file_name
        # photo = tk.PhotoImage(file=file_path)
        # label = tk.Label(self._frame,image=photo)
        # label.image = photo  # keep a reference!
        # label.place(x=550, y=300)


        # tk.Label(self._frame,text='Select algorithm', font = 'Verdana 8 bold').place(x=start_x+dx*11, y=start_y+7*dy)
        # self._ent_algorithm.place(x=start_x+dx*11, y=start_y+dy*8)
        self.algorithm_random_label = tk.Label(self._frame, text='Number of trials')

        # tk.Button(self._frame,text='algorith information',command=self.algorithm_info,bg='white')\
        #     .place(x=start_x+dx*12.5, y=start_y+dy*7)
        self.run_button = tk.Button(self._frame,text='RUN OPTIMIZATION!', command=self.run_optimizaion, bg='red',
                                    font='Verdana 10 bold',fg='Yellow', relief="raised")
        self.run_button.place(x=start_x+dx*11.5, y=start_y-dy, relwidth = 0.15)
        # self.run_results = tk.Button(self._frame,text='show calculated', command=self.plot_results, bg='white',
        #                             font='Verdana 10',fg='black')
        # self.run_results.place(x=start_x+dx*8, y=start_y+dy*1.5)
        self._opt_actual_running_time.place(x=start_x+dx*11, y=start_y)

        self.close_and_save =tk.Button(self._frame,text='Return and replace initial structure with optimized',
                                       command=self.save_and_close,bg='green',font='Verdana 10',fg='yellow')
        self.close_and_save.place(x=start_x+dx*5,y=10)

        tk.Button(self._frame, text='Open predefined stiffeners example',
                  command=self.open_example_file, bg='white', font='Verdana 10')\
            .place(x=start_x+dx*10,y=10)


        # Stress scaling
        self._new_fup = tk.DoubleVar()
        self._new_fup.set(0.5)
        self._new_fdwn = tk.DoubleVar()
        self._new_fdwn.set(1)

        tk.Label(self._frame, text='Factor when scaling stresses up, fup')\
            .place(x=start_x, y=start_y + 16 * dy)
        ent_fup = tk.Entry(self._frame, textvariable=self._new_fup, width = 10)
        ent_fup.place(x=start_x + dx * 3, y=start_y + 16 * dy)
        tk.Label(self._frame, text='Factor when scaling stresses up, fdown')\
            .place(x=start_x, y=start_y + 17 * dy)
        ent_fdwn = tk.Entry(self._frame, textvariable=self._new_fdwn, width = 10)
        ent_fdwn.place(x=start_x + dx * 3, y=start_y + 17 * dy)

        # tk.Button(self._frame,text='Iterate predefiened stiffeners',command=self.open_multiple_files ,bg='yellow')\
        #     .place(x=start_x, y=start_y - dy * 2)
        self._toggle_btn = tk.Button(self._frame, text="Iterate predefiened stiffeners", relief="raised",
                                     command=self.toggle, bg = 'salmon')
        self._toggle_btn.place(x= + 3*dx, y=start_y - dy * 2)
        self._toggle_object, self._filez = self._initial_structure_obj, None
        self.draw_properties()
        self.update_running_time()

        ANYstructure_local.main_application.Application.draw_cylinder(text_size='Verdana 8 bold',
                                                                      canvas = self._canvas_opt,
                                                                      CylObj=self._initial_cylinder_obj,
                                                                      start_x_cyl=350, start_y_cyl=300, text_x=230,
                                                                      text_y=120)

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

        self.run_button.config(bg = 'white')
        self.run_button.config(fg='red')
        self.run_button.config(text='RUNNING OPTIMIZATION')
        self.run_button.config(relief="sunken")
        self._opt_actual_running_time.config(text='Run started ' + datetime.datetime.now().strftime("%H:%M:%S"))
        self._opt_actual_running_time.update()
        t_start = time.time()
        self._opt_results, self._opt_runned = (), False

        self.pso_parameters = (self._new_swarm_size.get(),self._new_omega.get(),self._new_phip.get(),
                               self._new_phig.get(),
                               self._new_maxiter.get(),self._new_minstep.get(),self._new_minfunc.get())


        if self._fatigue_pressure is not None:

            fat_press = ((self._fatigue_pressure['p_ext']['loaded'],self._fatigue_pressure['p_ext']['ballast'],
                          self._fatigue_pressure['p_ext']['part']),
                         (self._fatigue_pressure['p_int']['loaded'],self._fatigue_pressure['p_int']['ballast'],
                          self._fatigue_pressure['p_int']['part']))
        else:
            fat_press = None

        self._opt_results= op.run_optmizataion(initial_structure_obj= self._initial_cylinder_obj,
                                               min_var= self.get_lower_bounds(),
                                               max_var=self.get_upper_bounds(),lateral_pressure=
                                               self._new_design_pressure.get(),
                                               deltas= self.get_deltas(),algorithm=self._new_algorithm.get(),
                                               trials=self._new_algorithm_random_trials.get(),
                                               fatigue_obj=self._fatigue_object,
                                               fat_press_ext_int=fat_press,
                                               slamming_press = self._new_slamming_pressure.get(),
                                               predefined_stiffener_iter=self._predefined_stiffener_iter,
                                               processes=self._new_processes.get(),
                                               use_weight_filter = True,
                                               fdwn = self._new_fdwn.get(), fup = self._new_fdwn.get(),
                                               cylinder = True)

        if self._opt_results is not None and self._opt_results[0] is not None:
            self._opt_actual_running_time.config(text='Actual running time: \n'
                                                     +str(round((time.time()-t_start)/60,4))+' min')
            self._opt_actual_running_time.update()
            self._opt_runned = True
            #self._result_label.config(text=self._opt_results[0].__str__)
            self._canvas_opt.delete('all')
            ANYstructure_local.main_application.Application.draw_cylinder(text_size='Verdana 8 bold',
                                                                          canvas = self._canvas_opt,
                                                                          CylObj=self._opt_results[0],
                                                                          start_x_cyl=350, start_y_cyl=300, text_x=230,
                                                                          text_y=120)
            #self.draw_properties()
        else:
            messagebox.showinfo(title='Nothing found', message='No better alternatives found. Modify input.\n'
                                                               'There may be no alternative that is acceptable.\n')

        self.run_button.config(bg='green')
        self.run_button.config(fg='yellow')
        self.run_button.config(text='RUN OPTIMIZATION')
        self.run_button.config(relief="raised")

    def get_running_time(self):
        '''
        Estimate the running time of the algorithm.
        :return:
        '''

        pass

    def get_deltas(self):
        '''
        Return a numpy array of the deltas.
        :return:
        '''
        all_deltas = list()
        for idx_1, geo_i in enumerate(self._new_geo_data):
            these_deltas = list()
            for idx_3, val in enumerate(geo_i[1]):
                these_deltas.append(val.get()/1000)
            all_deltas.append(these_deltas)
        return all_deltas

    def update_running_time(self,*args):
        '''
        Estimate the running time of the algorithm.
        :return:
        '''

        pass
    
    def get_upper_bounds(self):
        '''
        Return an numpy array of upper bounds.
        :return: 
        '''
        all_upper = list()
        for idx_1, geo_i in enumerate(self._new_geo_data):
            these_upper = list()
            for idx_3, val in enumerate(geo_i[0]):
                these_upper.append(val.get()/1000)
            all_upper.append(these_upper)
        return all_upper

        
    def get_lower_bounds(self):
        '''
        Return an numpy array of lower bounds.
        :return: 
        '''
        all_lower = list()
        for idx_1, geo_i in enumerate(self._new_geo_data):
            these_lower = list()
            for idx_3, val in enumerate(geo_i[2]):
                these_lower.append(val.get()/1000)
            all_lower.append(these_lower)
        return all_lower

    def get_sigmas(self):
        '''
        Returns the stressess.
        :return:
        '''
        return np.array([self._new_sasd.get(),self._new_smsd.get(),
                         self._new_tTsd.get(),self._new_tQsd.get(),
                         self._new_design_pressure.get(),self._new_shsd.get()])

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
        #self.checkered(10)
        ctr_x = self._canvas_dim[0]/2
        ctr_y = self._canvas_dim[1]/2+200
        m = self._draw_scale
        init_color,init_stipple = 'blue','gray12'
        opt_color,opt_stippe = 'red','gray12'
        # self._canvas_opt.create_rectangle(0,0,self._canvas_dim[0]+10,80,fill='white')
        # self._canvas_opt.create_line(10,10,30,10,fill = init_color,width=5)


        if self._opt_runned:

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_s() / 2, ctr_y,
                                             ctr_x + m * self._opt_results[0].get_s()  / 2,
                                             ctr_y - m * self._opt_results[0].get_pl_thk(), fill=opt_color,
                                             stipple=opt_stippe)

            self._canvas_opt.create_rectangle(ctr_x - m * self._opt_results[0].get_web_thk() / 2, ctr_y -
                                             m * self._opt_results[0].get_pl_thk(),
                                             ctr_x + m * self._opt_results[0].get_web_thk() / 2,
                                             ctr_y - m * (self._opt_results[0].get_web_h() + self._opt_results[0].get_pl_thk())
                                             , fill=opt_color, stipple=opt_stippe)
            if self._opt_results[0].get_stiffener_type() not in ['L', 'L-bulb']:
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
            self._canvas_opt.create_text(270,50,text='Optimized - Pl.: '+str(round(self._opt_results[0].get_s()*1000,1))
                                                     +'x'+ str(round(self._opt_results[0].get_pl_thk()*1000,1))+
                                                     ' Stf.: '+str(round(self._opt_results[0].get_web_h()*1000,1))+
                                                    'x'+str(round(self._opt_results[0].get_web_thk()*1000,1))+'+'+
                                                            str(round(self._opt_results[0].get_fl_w()*1000,1))+
                                                    'x'+str(round(self._opt_results[0].get_fl_thk()*1000,1)),
                                        font = 'Verdana 8',fill = opt_color)


    def save_and_close(self):
        '''
        Save and close
        :return:
        '''

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

    def toggle(self):
        if self._toggle_btn.config('relief')[-1] == 'sunken':
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg = 'salmon')

            predefined_stiffener_iter  = []
        else:
            self._toggle_btn.config(relief="sunken")
            self._toggle_btn.config(bg = 'salmon')
            self._toggle_btn.config(bg='lightgreen')


            open_files = askopenfilenames(parent=self._frame, title='Choose files to open')
            predefined_stiffener_iter = hlp.helper_read_section_file(files=list(open_files),
                                                                     obj=self._initial_structure_obj)



        if predefined_stiffener_iter == []:
            self._toggle_btn.config(relief="raised")
            self._toggle_btn.config(bg = 'salmon')

            self._predefined_stiffener_iter  = None
        else:
            self._predefined_stiffener_iter = predefined_stiffener_iter
        self.update_running_time()

    def open_example_file(self):
        import os
        if os.path.isfile('sections.csv'):
            os.startfile('sections.csv')
        else:
            os.startfile(self._root_dir + '/' + 'sections.csv')

    def show_calculated(self):
        ''' '''
        pass

    def plot_results(self):
        if len(self._opt_results) != 0:
            op.plot_optimization_results(self._opt_results)

    def write_result_csv(self):
        if len(self._opt_results) != 0:
            print(self._opt_results)


def receive_progress_info():
    '''
    Get progress info from optimization algorithm.
    :return:
    '''
    print('hi')



if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateOptimizeCylinderWindow(master=root)
    root.mainloop()




