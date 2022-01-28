from ANYstructure_local import main_application
import multiprocessing, ctypes, os, pickle
import tkinter as tk


multiprocessing.freeze_support()
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
root = tk.Tk()
my_app = main_application.Application(root)
my_dict = my_app.__dict__

my_dict["_new_field_len"].set(4000)
my_dict["_new_stf_spacing"].set(700)
my_dict["_new_plate_thk"].set(20)
my_dict["_new_stf_web_h"].set(400)
my_dict["_new_stf_web_t"].set(20)
my_dict["_new_stf_fl_w"].set(150)
my_dict["_new_stf_fl_t"].set(15)
#my_dict['_new_stucture_type'].set('FRAME')


def run_cc_chks():
    for chks in ['_new_colorcode_beams',
                 '_new_colorcode_plates',
                 '_new_colorcode_pressure',
                 '_new_colorcode_utilization',
                 '_new_colorcode_sigmax',
                 '_new_colorcode_sigmay1',
                 '_new_colorcode_sigmay2',
                 '_new_colorcode_tauxy',
                 '_new_colorcode_structure_type']:
        my_dict[chks].set(True)
        my_app.on_color_code_check()
        my_dict[chks].set(False)


my_dict['_ML_buckling'] = dict()

for name, file_base in zip(['cl SP buc int predictor', 'cl SP buc int scaler',
                                    'cl SP ult int predictor', 'cl SP ult int scaler',
                                    'cl SP buc GLGT predictor', 'cl SP buc GLGT scaler',
                                    'cl SP ult GLGT predictor', 'cl SP ult GLGT scaler',
                                    'cl UP buc int predictor', 'cl UP buc int scaler',
                                    'cl UP ult int predictor', 'cl UP ult int scaler',
                                    'cl UP buc GLGT predictor', 'cl UP buc GLGT scaler',
                                    'cl UP ult GLGT predictor', 'cl UP ult GLGT scaler',
                                    'CSR predictor UP', 'CSR scaler UP',
                                    'CSR predictor SP', 'CSR scaler SP'
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
    my_dict['_ML_buckling'][name] = None

    if os.path.isfile('C:\\Github\\ANYstructure\\ANYstructure_local\\'+file_base + '.pickle'):

        file = open('C:\\Github\\ANYstructure\\ANYstructure_local\\'+file_base + '.pickle', 'rb')
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import StandardScaler

        my_dict['_ML_buckling'] [name] = pickle.load(file)
        file.close()

my_dict['_ML_classes'] = {0: 'N/A',
                    1: 'A negative utilisation factor is found.',
                    2: 'At least one of the in-plane loads must be non-zero.',
                    3: 'Division by zero',
                    4: 'Overflow',
                    5: 'The aspect ratio exceeds the PULS code limit',
                    6: 'The global slenderness exceeds 4. Please reduce stiffener span or increase stiffener height.',
                    7: 'The applied pressure is too high for this plate field.', 8: 'web-flange-ratio',
                    9: 'UF below or equal 0.87', 10: 'UF between 0.87 and 1.0', 11: 'UF above 1.0'}


for x,y in [[0,0],[3000,0],[6000,0],[8000,0],[0,2500],[3000,2500],[6000,2500],[8000,2500],[0,10000], [8000,10000]]:
    my_dict['_new_point_x'].set(x)
    my_dict['_new_point_y'].set(y)
    my_app.new_point()

print(my_dict['_point_dict'])
run_cc_chks()

for p1, p2 in [[1,2],[2,3],[3,4],[5,6],[6,7],[7,8], [1,5], [2,6], [3,7], [4, 8], [9,10], [5,9], [8,10]]:
    my_dict['_new_line_p1'].set(p1)
    my_dict['_new_line_p2'].set(p2)
    my_app.new_line()

print(my_dict['_line_dict'])
run_cc_chks()

for key in my_dict['_line_dict'].keys():
    my_dict['_active_line'] = key
    my_dict['_line_is_active'] = True
    my_app.new_structure()

run_cc_chks()
my_dict['_active_line'] = 'line3'
my_dict['_line_is_active'] = True
my_app.delete_line(line='line3')
my_dict['_new_line_p1'].set(3)
my_dict['_new_line_p2'].set(4)

print(my_dict['_line_dict'])

my_app.gui_load_combinations(None)
my_app.grid_find_tanks()
my_app.grid_display_tanks()
run_cc_chks()
print(my_dict['_tank_dict'])
my_app.on_show_loads()

