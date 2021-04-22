from ANYstructure import main_application
import multiprocessing, ctypes
import tkinter as tk


multiprocessing.freeze_support()
errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
root = tk.Tk()
my_app = main_application.Application(root)

my_dict = my_app.__dict__
print(my_dict)
my_dict["_new_field_len"].set(4)
my_dict["_new_stf_spacing"].set(700)
my_dict["_new_plate_thk"].set(20)
my_dict["_new_stf_web_h"].set(400)
my_dict["_new_sft_web_t"].set(20)
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

my_app.new_line()

print(my_dict['_line_dict'])

my_app.grid_find_tanks()
my_app.grid_display_tanks()
run_cc_chks()
print(my_dict['_tank_dict'])
my_app.on_show_loads()

