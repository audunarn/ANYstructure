from anystruct import calc_structure, example_data, main_application, ml_models
import multiprocessing, ctypes, os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from matplotlib import pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL_ML_FILES = Path(r"C:\python_projects\ANYstructure\anystruct\ml_files")


def get_ml_file_directories():
    directories = []
    env_dir = os.environ.get("ANYSTRUCTURE_ML_FILES")
    if env_dir:
        directories.append(Path(env_dir))
    directories.extend([REPO_ROOT / "anystruct" / "ml_files", DEFAULT_EXTERNAL_ML_FILES])
    return directories


def configure_noninteractive_dialogs():
    tk.messagebox = messagebox
    messagebox.askquestion = lambda *args, **kwargs: "no"
    messagebox.showerror = lambda *args, **kwargs: "ok"
    messagebox.showinfo = lambda *args, **kwargs: "ok"
    messagebox.showwarning = lambda *args, **kwargs: "ok"
    main_application.Application._show_startup_calculation_mode_dialog = lambda _self: "multiple"


def configure_noninteractive_plots():
    plt.show = lambda *args, **kwargs: None


def checkpoint(name):
    print(f"gui_automatic_run: {name}", flush=True)


def close_child_windows():
    root.update_idletasks()
    for child in list(root.winfo_children()):
        if isinstance(child, tk.Toplevel):
            child.destroy()
    root.update_idletasks()
    plt.close("all")


def assert_window_opens(action, name):
    before = len([child for child in root.winfo_children() if isinstance(child, tk.Toplevel)])
    action()
    root.update_idletasks()
    after = len([child for child in root.winfo_children() if isinstance(child, tk.Toplevel)])
    if after <= before:
        raise RuntimeError(f"{name} did not open a Toplevel window")
    checkpoint(f"{name} opened")
    close_child_windows()


def make_smoke_cylinder():
    return calc_structure.CylinderAndCurvedPlate(
        main_dict=example_data.shell_main_dict,
        shell=calc_structure.Shell(example_data.shell_dict),
        long_stf=calc_structure.Structure(example_data.obj_dict_cyl_long2),
        ring_stf=None,
        ring_frame=None)


def exercise_optimizer_windows():
    my_dict["_active_line"] = "line1"
    my_dict["_line_is_active"] = True
    assert_window_opens(my_app.on_optimize, "single optimizer")

    my_dict["_active_line"] = "line2"
    my_dict["_line_is_active"] = True
    my_dict["_line_to_struc"]["line2"][5] = make_smoke_cylinder()
    assert_window_opens(my_app.on_optimize_cylinder, "cylinder optimizer")
    my_dict["_line_to_struc"]["line2"][5] = None

    my_dict["_multiselect_lines"] = ["line1", "line2"]
    assert_window_opens(my_app.on_optimize_multiple, "multiple optimizer")
    assert_window_opens(my_app.on_geometry_optimize, "span optimizer")


multiprocessing.freeze_support()
configure_noninteractive_dialogs()
configure_noninteractive_plots()
if os.name == "nt":
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
root = tk.Tk()
checkpoint("root created")
my_app = main_application.Application(root)
checkpoint("application created")
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


my_dict['_ML_buckling'] = ml_models.load_buckling_models(get_ml_file_directories())


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

checkpoint("points created")
print(my_dict['_point_dict'])
run_cc_chks()
checkpoint("point color checks run")

for p1, p2 in [[1,2],[2,3],[3,4],[5,6],[6,7],[7,8], [1,5], [2,6], [3,7], [4, 8], [9,10], [5,9], [8,10]]:
    my_dict['_new_line_p1'].set(p1)
    my_dict['_new_line_p2'].set(p2)
    my_app.new_line()

checkpoint("lines created")
print(my_dict['_line_dict'])
run_cc_chks()
checkpoint("line color checks run")

for key in my_dict['_line_dict'].keys():
    my_dict['_active_line'] = key
    my_dict['_line_is_active'] = True
    my_app.new_structure()

checkpoint("structures created")
run_cc_chks()
checkpoint("structure color checks run")
my_dict['_active_line'] = 'line3'
my_dict['_line_is_active'] = True
my_app.delete_line(line='line3')
my_dict['_new_line_p1'].set(3)
my_dict['_new_line_p2'].set(4)

checkpoint("line deleted")
print(my_dict['_line_dict'])

my_app.gui_load_combinations(None)
checkpoint("load combinations opened")
my_app.grid_find_tanks()
checkpoint("tank search complete")
my_app.grid_display_tanks()
plt.close("all")
checkpoint("tanks displayed")
run_cc_chks()
print(my_dict['_tank_dict'])
my_app.on_show_loads()
checkpoint("loads shown")
exercise_optimizer_windows()
checkpoint("optimizer windows exercised")
my_app.open_example()
checkpoint("example project opened")
root.update_idletasks()
root.destroy()
checkpoint("root destroyed")

