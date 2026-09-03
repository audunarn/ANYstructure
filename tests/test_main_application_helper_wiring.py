from pathlib import Path
import math
import re
import weakref
from types import SimpleNamespace
import pytest
from anysolver import runtime as fe_solver
from anystruct import representation_geometry
from anystruct.main_application import Application


class _FullscreenRootProbe:
    def __init__(self, fail_state=False, fail_attributes=False):
        self.fail_state = fail_state
        self.fail_attributes = fail_attributes
        self.calls = []

    def state(self, value):
        self.calls.append(("state", value))
        if self.fail_state:
            raise RuntimeError("state unavailable")

    def attributes(self, key, value):
        self.calls.append(("attributes", key, value))
        if self.fail_attributes:
            raise RuntimeError("attribute unavailable")

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def geometry(self, value):
        self.calls.append(("geometry", value))


class _ValueProbe:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _RuntimeRendererProbe:
    def __init__(self, *, fail_gpu=False):
        self.window = SimpleNamespace(winfo_exists=lambda: 1)
        self._renderer_requested = "auto"
        self.renderer_backend_choice = _ValueProbe("Automatic")
        self.fail_gpu = fail_gpu
        self.calls = []

    def _switch_renderer_backend(self, *, _application_coordinated=False):
        requested = {
            "Automatic": "auto",
            "GPU (ModernGL)": "gpu",
            "Tk (software)": "software",
        }[self.renderer_backend_choice.get()]
        self.calls.append((requested, _application_coordinated))
        if requested == "gpu" and self.fail_gpu:
            return False
        self._renderer_requested = requested
        return True


def test_main_application_uses_shared_geometry_menu_helpers():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "api_helpers.CYLINDER_STRUCTURE_DOMAINS_WITH_INPUT" in source
    assert "api_helpers.FLAT_GEOMETRY_IDS" in source
    assert "api_helpers.CYLINDER_GEOMETRY_IDS" in source
    assert "CylinderAndCurvedPlate.geomeries.values()" not in source
    assert "CylinderAndCurvedPlate.geomeries_map" not in source
    assert "Longitudinal Stiffened shell  (Force input)" not in source


def test_application_starts_root_fullscreen_from_init():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    init_source = source[
        source.index("def __init__(self, parent):"):
        source.index("parent.protocol(\"WM_DELETE_WINDOW\"")
    ]

    assert "def _start_root_fullscreen(parent):" in source
    assert "parent.state('zoomed')" in source
    assert "parent.attributes('-zoomed', True)" in source
    assert "parent.geometry(f'{parent.winfo_screenwidth()}x{parent.winfo_screenheight()}+0+0')" in source
    assert "self._start_root_fullscreen(parent)" in init_source


def test_start_root_fullscreen_prefers_zoomed_state_with_fallbacks():
    root = _FullscreenRootProbe()
    Application._start_root_fullscreen(root)
    assert root.calls == [("state", "zoomed")]

    root = _FullscreenRootProbe(fail_state=True)
    Application._start_root_fullscreen(root)
    assert root.calls == [("state", "zoomed"), ("attributes", "-zoomed", True)]

    root = _FullscreenRootProbe(fail_state=True, fail_attributes=True)
    Application._start_root_fullscreen(root)
    assert root.calls == [
        ("state", "zoomed"),
        ("attributes", "-zoomed", True),
        ("geometry", "1920x1080+0+0"),
    ]


def test_application_renderer_choice_updates_registered_runtime_viewers():
    app = Application.__new__(Application)
    app._renderer_requested = "auto"
    app._renderer_backend_choice = _ValueProbe("GPU (ModernGL)")
    app._renderer_backend_status = _ValueProbe("")
    runtime = _RuntimeRendererProbe()
    app._runtime_fem_windows = weakref.WeakSet((runtime,))
    app._main_renderer_specs = lambda: []

    assert app._switch_main_renderer_backend()
    assert app._renderer_requested == "gpu"
    assert runtime._renderer_requested == "gpu"
    assert runtime.calls == [("gpu", True)]


def test_application_renderer_choice_rolls_back_runtime_group_on_failure():
    app = Application.__new__(Application)
    app._renderer_requested = "auto"
    app._renderer_backend_choice = _ValueProbe("GPU (ModernGL)")
    app._renderer_backend_status = _ValueProbe("")
    first = _RuntimeRendererProbe()
    failing = _RuntimeRendererProbe(fail_gpu=True)
    app._runtime_fem_windows = weakref.WeakSet((first, failing))
    app._main_renderer_specs = lambda: []

    assert not app._switch_main_renderer_backend()
    assert app._renderer_requested == "auto"
    assert app._renderer_backend_choice.get() == "Automatic"
    assert first._renderer_requested == "auto"


def test_file_menu_exposes_export_options():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    file_menu_block = source[
        source.index("menu.add_cascade(label='File', menu=sub_menu)"):
        source.index("self._shortcut_text =")
    ]

    assert "sub_menu.add_cascade(label='Export', menu=file_export_menu)" in file_menu_block
    assert "Geometry to SESAM GeniE JS..." in file_menu_block
    assert "command=self.export_to_js" in file_menu_block
    assert "Selected structure IFC/CAD solid model..." in file_menu_block
    assert "command=self.export_prop_3d_ifc_model" in file_menu_block
    assert "Selected structure IFC/CAD shell/surface model..." in file_menu_block
    assert "command=self.export_prop_3d_ifc_shell_model" in file_menu_block
    assert "Open FEA result buckling files..." in file_menu_block


def test_conical_shell_uses_single_domain_and_existing_force_stress_toggle():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    conical_branch = source[
        source.index("elif self._new_calculation_domain.get() == 'Unstiffened conical shell (Force input)'"):
        source.index("elif self._new_calculation_domain.get() in ['Longitudinal Stiffened shell (Force input)'")
    ]
    cylinder_sync_block = source[
        source.index("if struc_obj.geometry == 9:"):
        source.index("elif self._new_shell_stress_or_force.get() == 1:")
    ]

    assert "Unstiffened conical shell (Stress input)" not in source
    assert "_new_shell_M1sd" not in source
    assert "self._new_shell_Msd.get()" in cylinder_sync_block
    # Calculated conversions are rounded before being shown in the entries.
    assert "self._new_shell_Msd.set(_round_calculated(M1sd))" in cylinder_sync_block
    assert "conical=True" in conical_branch
    assert "_new_shell_stress_or_force.set" not in conical_branch
    assert "helper_cylinder_stress_to_force_to_stress(" in cylinder_sync_block
    assert "self._new_shell_M2sd.set(_round_calculated(M2sd))" in cylinder_sync_block
    assert "self._new_shell_Q2sd.set(_round_calculated(Q2sd))" in cylinder_sync_block
    assert "if 'Need to check column buckling' not in results.keys() and value is None:" in source


def test_calculated_gui_values_are_rounded_and_km_fields_wired():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    # Calculated stress/force conversions are rounded (3 decimals) before they
    # are written into the entries; user-typed values are never rounded.
    assert "def _round_calculated(value, decimals: int = 3):" in source
    assert "self._new_shell_sasd.set(_round_calculated(sasd))" in source
    assert "self._new_shell_Nsd.set(_round_calculated(Nsd))" in source
    assert "self._new_shell_Qsd.set(_round_calculated(Qsd))" in source

    # The stress-estimation window handler stores km2/km3 into their own
    # fields (a copy-paste bug wrote all three km values into km1).
    assert "self._new_stf_km2.set(returned_stress_and_km[6])" in source
    assert "self._new_stf_km3.set(returned_stress_and_km[7])" in source
    assert source.count("self._new_stf_km1.set(returned_stress_and_km") == 1

    # Stored plate stresses keep the user's precision on line selection.
    assert "self._new_sigma_y1.set(round(properties['sigma_y1'][0], 5))" in source
    assert "round(properties['sigma_y1'][0], 1)" not in source

    # User-facing label fixes.
    assert "Fabrication method ring stiffener:" in source
    assert "Fabrication method ring girder:" in source
    assert "Fabrictaion" not in source
    assert "avaliable" not in source
    assert "memebrane" not in source

    from anystruct.main_application import _round_calculated

    assert _round_calculated(523.5359969639133) == 523.536
    assert _round_calculated(-0.2) == -0.2
    assert _round_calculated("not a number") == "not a number"


def test_release_package_metadata_uses_current_markdown_readme():
    setup_source = Path(__file__).resolve().parents[1] / "setup.py"
    source = setup_source.read_text(encoding="utf-8")

    assert "version='6.4.0'" in source
    assert "README.md" in source[source.index("def readme"):source.index("core_requires")]
    assert "README.rst" not in source
    assert "long_description_content_type='text/markdown'" in source


def test_functional_modes_keep_3d_section_checkbox_visible():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "def _place_3d_section_view_checkbox(self):" in source
    assert "def create_prop_3d_figure_for_line(self, line_name=None):" in source
    assert "self.draw_cylinder_prop_3d(self._line_to_struc[selected_line][5], embed=False)" in source
    assert "self.draw_flat_panel_prop_3d(self._line_to_struc[selected_line][0], embed=False)" in source
    assert "self._chk_show_prop_3d.place(relx=0.637, rely=0.705)" in source
    assert "self._chk_show_prop_3d.lift()" in source
    assert source.count("self._place_3d_section_view_checkbox()") >= 3
    single_mode_source = source[source.index("def switch_to_single_calculation_mode"):source.index("def switch_to_multiple_calculation_mode")]
    multiple_mode_source = source[source.index("def switch_to_multiple_calculation_mode"):source.index("def switch_to_fea_result_buckling_mode")]
    assert "self._place_3d_section_view_checkbox()" in single_mode_source
    assert "self._place_3d_section_view_checkbox()" in multiple_mode_source


def test_help_tab_includes_cylinder_panel_buckling_image():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    shell_image_index = source.index("Buckling_Strength_of_Shells.png")
    panel_heading_index = source.index("Buckling cylinder panels")
    panel_image_index = source.index("buckling_cylinder_panel.png")

    assert shell_image_index < panel_heading_index < panel_image_index


def test_main_application_uses_tcl9_compatible_variable_traces():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert ".trace('w', self.trace_acceptance_change)" not in source
    assert ".trace_add('write', self.trace_acceptance_change)" in source


def test_resize_state_is_initialized_before_configure_binding():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    init_source = source[
        source.index("def __init__(self, parent):"):
        source.index("self._root_dir =")
    ]

    assert init_source.index("self._last_resize_size = (0, 0)") < init_source.index('parent.bind("<Configure>"')
    assert init_source.index("self._resize_after_id = None") < init_source.index('parent.bind("<Configure>"')


def test_main_gui_prompts_for_simplified_single_line_mode_with_standard_default():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "self._simplified_calculation_mode = False" in source
    assert "self._single_line_name = 'line1'" in source
    assert "def _prompt_startup_calculation_mode(self):" in source
    assert "from importlib import metadata as importlib_metadata" in source
    assert "def _get_application_version_from_metadata():" in source
    assert "importlib_metadata.version(package_name)" in source
    assert "__version__" not in source[source.index("def _show_startup_calculation_mode_dialog"):source.index("def switch_to_single_calculation_mode")]
    assert "def _show_startup_calculation_mode_dialog(self):" in source
    assert "tk.Toplevel(self._parent, background='#f5f7fb')" in source
    assert "ANYstructure_logo.jpg" in source
    assert "from PIL import Image, ImageTk" in source
    assert "ImageTk.PhotoImage(logo_image)" in source
    assert "logo_image.thumbnail((132, 76), Image.LANCZOS)" in source
    assert "Version ' + app_version" in source
    assert "Choose calculation workflow" in source
    assert "Multiple panels" in source
    assert "subtitle='Default'" in source
    assert "Recommended default" not in source
    assert "Single panel/cylinder" in source
    assert "FEA result buckling" in source
    assert "dialog.bind('<Return>', lambda _event: choose('multiple'))" in source
    assert "dialog.bind('<Escape>', lambda _event: choose('multiple'))" in source
    assert "self._parent.wait_window(dialog)" in source
    assert "Mode - Single panel/cylinder" in source
    assert "Mode - Multiple panels" in source
    assert "Mode - FEA result buckling" in source
    gui_menu_block = source[
        source.index("menu.add_cascade(label='GUI', menu=sub_colors)"):
        source.index("# base_mult = 1.2")
    ]
    assert "Mode - FEA result buckling" in gui_menu_block
    assert "def switch_to_single_calculation_mode(self):" in source
    assert "def switch_to_multiple_calculation_mode(self):" in source
    assert "def switch_to_fea_result_buckling_mode(self):" in source
    assert "self._single_line_name = selected_line" in source
    assert "self._activate_simplified_calculation_pipeline()" in source
    assert "def _ensure_single_dummy_line(self):" in source
    assert "self._line_dict[self._single_line_name] = [1, 2]" in source
    assert "def _ensure_manual_pressure_combination(self, line, default_enabled=False):" in source
    assert "def _gui_single_line_manual_pressure(self):" in source
    assert "Manual pressure [Pa]" in source
    assert "if self._line_to_struc[self._active_line][5] is not None:" in source
    assert "self._result_label_manual, self._lab_pressure" in source
    assert "def _sync_simplified_domain_selection(self):" in source
    assert "self._sync_simplified_domain_selection()" in source
    assert "if not getattr(self, '_simplified_calculation_mode', False):\n            self.set_selected_variables(self._active_line)" in source
    assert "self._tabControl.hide(self._tab_geo)" in source
    assert "self._tabControl.hide(self._tab_comp)" in source
    assert "def _show_standard_calculation_layout(self):" in source
    assert "self._tabControl.add(self._tab_geo, text='Geometry')" in source
    assert "self._tabControl.add(self._tab_comp, text='Compartments and loads')" in source
    assert "self.gui_load_combinations(self._combination_slider.get())" in source


def test_fea_result_buckling_mode_has_import_canvas_and_pressure_free_controls():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "import anystruct.fe_plate_fields as fe_plate_fields" in source
    assert "self._fea_buckling_mode = False" in source
    assert "self._fea_buckling_session = None" in source
    assert "Open FEA result buckling files..." in source
    assert "def open_fea_buckling_files(self):" in source
    assert "def reimport_fea_buckling_files(self):" in source
    assert "def import_fea_buckling_files(self, inp_path, frd_path=None, forced_geometry_type=None):" in source
    assert "fe_plate_fields.create_fea_buckling_session(" in source
    assert "SESAM FEM/SIF" in source
    assert "has_result_source = bool(frd_path) or input_lower.endswith('.sif')" in source
    # SESAM .FEM is geometry only: never imported for buckling, routed to FE-solver.
    assert "def _launch_fe_solver_with_fem_geometry(self, inp_path):" in source
    assert "self._launch_fe_solver_with_fem_geometry(inp_path)" in source
    assert "self._launch_fe_solver_with_fem_geometry(input_text)" in source
    assert "\"Launch FE-solver?\"" in source
    assert "imported_fem_model=model, imported_path=inp_path" in source
    assert "ml_algo=getattr(self, '_ML_buckling', None)" in source
    assert "messagebox.showwarning('FEA buckling method warning'" in source
    assert "def _draw_fea_buckling_canvas(self):" in source
    assert "fe_plate_fields.panel_3d_records(session.model, session.fields, session.usage_factors())" in source
    assert "Poly3DCollection(" in source
    assert "self._fea_3d_panel_artists = {}" in source
    assert "self._fea_3d_panel_artists[field_id] = collection" in source
    assert "def _update_fea_3d_selection(self):" in source
    assert "def _ensure_fea_lower_panes_visible(self):" in source
    assert "def _refresh_fea_buckling_views(self, rebuild_3d=False):" in source
    assert "def _draw_fea_panel_result_text(self):" in source
    assert "def _draw_fea_panel_existing_result_text(self, panel):" in source
    assert "def _draw_fea_panel_2d_sketch(self):" in source
    assert "def _draw_flat_structure_2d_preview(self, all_obj, selected_text=''):" in source
    assert "self._fea_uf_color_lower = tk.DoubleVar()" in source
    assert "self._fea_uf_color_upper = tk.DoubleVar()" in source
    assert "self._fea_stress_reduction_method = tk.StringVar()" in source
    assert "fe_plate_fields.available_stress_reduction_methods()[0]" in source
    assert "self._fea_show_uf_text = tk.BooleanVar(value=False)" in source
    assert "self._fea_show_panel_text = tk.BooleanVar(value=False)" in source
    assert "self._fea_show_local_x_arrow = tk.BooleanVar(value=False)" in source
    assert "self._fea_show_local_y_arrow = tk.BooleanVar(value=False)" in source
    assert "self._fea_show_mesh = tk.BooleanVar(value=False)" in source
    assert "self._fea_color_code = tk.BooleanVar(value=True)" in source
    assert "self._fea_panel_line_by_field = {}" in source
    assert "self._fea_imported_line_names = []" in source
    assert "def _rebuild_fea_panel_line_model(self):" in source
    assert "line_name = 'fea_panel_' + str(line_number).zfill(3)" in source
    assert "horizontal_gap_m = 0.5" in source
    assert "row_gap_m = 0.5" in source
    assert "panel_frame.place(relx=0.785, rely=0.0, relwidth=0.215, relheight=1.0)" in source
    assert "Selected Panel" in source
    assert "Import Summary" in source
    assert "def _fea_uf_color_limits(self):" in source
    assert "UF colour range" in source
    assert "textvariable=self._fea_uf_color_lower" in source
    assert "textvariable=self._fea_uf_color_upper" in source
    assert "text='Update colour scale'" in source
    assert "uf_min, uf_max = self._fea_uf_color_limits()" in source
    assert "matplotlib.colors.Normalize(vmin=uf_min, vmax=uf_max)" in source
    assert "rgba = plt.get_cmap('jet')" in source
    assert "uf_cmap = plt.get_cmap('jet')" in source
    assert "colorbar_ax = fig.add_axes([0.90, 0.18, 0.025, 0.64])" in source
    assert "fig.colorbar(scalar_map, cax=colorbar_ax)" in source
    assert "colorbar.set_label('UF'" in source
    assert "ax_width = 0.86 if self._fea_color_code.get() else 0.96" in source
    assert "if self._fea_show_panel_text.get():" in source
    assert "if self._fea_show_uf_text.get() and panel.usage_factor is not None:" in source
    assert "if self._fea_show_local_x_arrow.get():" in source
    assert "if self._fea_show_local_y_arrow.get():" in source
    assert "if self._fea_color_code.get():" in source
    assert "ax.quiver(" in source
    assert "self._build_flat_structure_properties()" in source
    assert "def _apply_selected_fea_cylinder_panel_to_inputs(self, data):" in source
    assert "api_helpers.cylinder_domain_with_input_mode(domain)" in source
    assert "self._new_shell_stress_or_force.set(2)" in source
    assert "def _fea_panel_cylinder_structure(self, panel):" in source
    assert "cylinder=cylinder_obj" in source
    assert "self._create_all_structure_from_properties(prop_dict)" in source
    assert "self._fea_buckling_mode = False" in source
    assert "self.draw_results(state=state)" in source
    assert "mapped_line = getattr(self, '_fea_panel_line_by_field', {}).get(panel.field_id)" in source
    assert "flat_method_print = self._new_buckling_method.get() in [" in source
    assert "self._line_to_struc[result_line][5] = None" in source
    assert "if old_result_bundle is not None:" in source
    assert "self.get_color_and_calc_state(current_line=result_line, active_line_only=True)" in source
    assert "def _fea_stress_method_description(method):" in source
    assert "def _draw_fea_stress_interpretation_canvas(self, canvas, panel):" in source
    assert "Stress Interpretation" in source
    assert "Apply stress method" in source
    assert "stress_reduction_method=self._fea_stress_reduction_method.get()" in source
    assert "pressure_mpa * 1.0e6" in source
    assert "panel.anystructure_input.get('stresses', {}).get('pressure_mpa', 0.0)" in source
    assert "edgecolor='red' if selected else ('#333333' if self._fea_show_mesh.get() else 'none')" in source
    assert "linewidth=1.8 if selected else (0.25 if self._fea_show_mesh.get() else 0.0)" in source
    assert "collection.set_gid(field_id)" in source
    assert "collection.set_picker(5)" in source
    assert "self._fea_pick_cid = self._prop_3d_fig_canvas.mpl_connect(" in source
    assert "def _on_fea_buckling_panel_pick(self, event):" in source
    assert "def _select_fea_panel_after_matplotlib_event(self, field_id):" in source
    assert "self._fea_pick_after_id = self._parent.after_idle(select_panel)" in source
    assert "self._prop_3d_fig_canvas.toolbar = None" in source
    assert "self._prop_3d_toolbar.set_history_buttons = lambda *args, **kwargs: None" in source
    assert "def _apply_selected_fea_panel_to_inputs(self):" in source
    assert "self._new_plate_thk.set(round(float(geometry.get('plate_thickness_mm', 0.0)), 5))" in source
    assert "self._new_sigma_x1.set(round(float(stresses.get('sigma_x1_mpa', 0.0)), 5))" in source

    select_block = source[source.index("def _select_fea_panel(self, field_id):"):source.index("def _single_mode_active_line_candidate")]
    assert "self._refresh_fea_buckling_views(rebuild_3d=False)" in select_block
    assert "self._draw_fea_buckling_canvas()" not in select_block
    assert "panel.buckling_error" not in source
    assert "getattr(self, '_fea_buckling_mode', False)" in source[source.index("def _prop_3d_mouse_scroll"):source.index("def _set_prop_3d_view")]
    assert "if getattr(self, '_fea_buckling_mode', False):\n            self._draw_fea_panel_result_text()" in source
    assert "if getattr(self, '_fea_buckling_mode', False):\n            self._draw_fea_panel_2d_sketch()" in source

    load_block = source[source.index("def _gui_fea_buckling_options"):source.index("def gui_load_combinations")]
    assert "Manual pressure [Pa]" not in load_block
    assert "self._lab_pressure" in load_block
    assert "item.place_forget()" in load_block
    assert "Import INP/FRD" in load_block
    assert "Reimport" in load_block
    assert "Analyse file" not in load_block
    assert "Static and dynamic accelerations" not in load_block
    assert "Load info" not in load_block
    assert "Load factors" not in load_block
    assert "Weights" not in load_block
    assert "Buckling method" in load_block
    assert "DNV-RP-C201 - prescriptive" in load_block
    assert "SemiAnalytical S3/U3" in load_block
    assert "ML-Numeric (PULS based)" in load_block
    assert "UF basis" in load_block
    assert "command=self._on_fea_buckling_option_changed" in load_block
    assert "3D view" in load_block
    assert "UF text" in load_block
    assert "Panel number text" in load_block
    assert "Panel local x arrow" in load_block
    assert "Panel local y arrow" in load_block
    assert "Show mesh" in load_block
    assert "Color code" in load_block
    assert "Show all UFs / details" in load_block
    assert "command=self._show_fea_buckling_details_popup" in load_block

    assert "def _show_fea_buckling_details_popup(self):" in source
    assert "fe_plate_fields.format_panel_buckling_details" in source

    # The live shared 3D viewer must honour the UF/panel text options; the
    # legacy matplotlib block is unreachable and must not be the only place
    # the options are read.
    populate_block = source[
        source.index("def _populate_fea_buckling_tk3d_canvas"):
        source.index("def _add_fea_tk3d_local_axes")
    ]
    assert "self._fea_show_uf_text.get()" in populate_block
    assert "self._fea_show_panel_text.get()" in populate_block
    assert "tk3d.add_text(" in populate_block


def test_prop_3d_preview_uses_shared_viewer_without_matplotlib_fallback():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "def _embed_prop_3d(self, fig, ax, default_view=(22, -55)):" in source
    dispatcher = source[
        source.index("def _embed_prop_3d(self, fig, ax, default_view=(22, -55)):"):
        source.index("def _prop_3d_face_fill")
    ]
    assert "self._embed_prop_3d_tk3d(ax, default_view=default_view)" in dispatcher
    assert "self._embed_prop_3d_figure(" not in dispatcher
    assert "Renderer preview unavailable:" in dispatcher
    assert "def _embed_prop_3d_figure(" in source
    assert "text='3D preview unavailable: ' + str(error)" in source
    # Both single-object previews (flat panel and cylinder) go through the
    # dispatcher so the selected shared backend is the only live renderer.
    assert source.count("self._embed_prop_3d(fig, ax, default_view=(22, -55))") == 2

    embed_block = source[
        source.index("def _embed_prop_3d_tk3d"):
        source.index("def _embed_prop_3d_figure")
    ]
    # Text and dimensions from the Matplotlib version are preserved.
    assert "ax.get_title()" in embed_block
    assert "ax.get_xlabel()" in embed_block
    assert "ax.get_ylabel()" in embed_block
    assert "ax.get_zlabel()" in embed_block
    assert "'SELECTED: ' + str(self._active_line)" in embed_block
    assert "tk3d.set_axis_ruler(True)" in embed_block
    assert "face_colors" in embed_block
    assert "export_prop_3d_ifc_model" in embed_block
    assert "export_prop_3d_ifc_shell_model" in embed_block


def test_prop_3d_initial_renderer_failure_cleans_partial_view_and_surfaces_status():
    app = SimpleNamespace()
    app._renderer_backend_status = _ValueProbe("")
    app.cleared = 0
    app.clear_prop_3d = lambda: setattr(app, "cleared", app.cleared + 1)
    app._embed_prop_3d_tk3d = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("OpenGL 3.3 is unavailable")
    )

    with pytest.raises(RuntimeError, match="OpenGL 3.3"):
        Application._embed_prop_3d(app, object(), object())

    assert app.cleared == 1
    assert app._renderer_backend_status.get() == (
        "Renderer preview unavailable: OpenGL 3.3 is unavailable"
    )


def test_prop_3d_tk3d_uses_native_thickness_primitives():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    # The preview records native primitive specs while drawing...
    assert "def _record_prop_3d_tk3d_item(ax, **item):" in source
    assert source.count("kind='flat_plate'") == 2
    assert source.count("kind='flat_member'") == 2
    assert "kind='cylinder_shell'" in source
    assert "kind='cylinder_long'" in source
    assert "kind='cylinder_ring'" in source

    # ...and replays them with the canvas's native example-style primitives.
    native_block = source[
        source.index("def _populate_prop_3d_tk3d_native"):
        source.index("def _populate_prop_3d_tk3d_faces")
    ]
    assert "set_thickness_legend" in native_block
    assert "thickness_color" in native_block
    assert "add_rectangular_plate" in native_block
    assert "add_flat_stiffener" in native_block
    assert "add_flat_girder" in native_block
    assert "add_cylinder(" in native_block
    assert "add_longitudinal_stiffener(" in native_block
    assert "add_ring_stiffener(" in native_block
    assert "plate_thickness=" in native_block


def test_prop_3d_native_replay_builds_thickness_styled_scene():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import math
    import tkinter as tk
    from matplotlib.figure import Figure

    from anystruct.main_application import Application
    from anystruct import tkinter_3d_canvas_thickness_v6 as t3d

    try:
        root = tk.Tk()
    except tk.TclError:
        import pytest as _pytest

        _pytest.skip("no display available for tkinter")
    root.withdraw()

    fig = Figure()
    ax = fig.add_subplot(111, projection="3d")
    Application._init_prop_3d_export_mesh(ax, "check")
    Application._record_prop_3d_tk3d_item(
        ax, kind="flat_plate", x0=0.0, x1=4.0, y0=0.0, y1=3.5, thickness_m=0.018
    )
    dims = {"web_h": 0.4, "web_thk": 0.012, "flange_w": 0.15, "flange_thk": 0.02, "type": "T"}
    Application._draw_section_web_and_flange_3d(Application, ax, "x", 2.0, 0.75, 4.0, 0.018, dims)
    Application._draw_section_web_and_flange_3d(Application, ax, "y", 2.0, 1.75, 3.5, 0.018, dims)

    items = ax._anystruct_tk3d_items
    assert [item["kind"] for item in items] == ["flat_plate", "flat_member", "flat_member"]
    assert items[1]["orientation"] == "x"
    assert items[2]["orientation"] == "y"
    assert items[1]["z_base"] == 0.018
    assert items[1]["hw"] == 0.4

    canvas = t3d.Tkinter3DCanvas(root, width=800, height=500, bg="white")
    Application._populate_prop_3d_tk3d_native(Application, canvas, items)
    legend = canvas._thickness_legend
    assert legend is not None and legend["unit"] == "mm"
    # Plate, web and flange thicknesses are all part of the legend.
    assert {12.0, 18.0, 20.0} <= set(legend["values"])
    assert sum(1 for obj in canvas.objects if obj.get("type") == "polygon") > 100

    cylinder_items = [
        {"kind": "cylinder_shell", "radius": 2.0, "radius_top": None, "length": 4.0,
         "thickness_m": 0.016, "theta_start": 0.0, "theta_end": 2.0 * math.pi, "is_panel": False},
        {"kind": "cylinder_long", "radius": 2.0, "length": 4.0, "angle": 0.5, "web_h": 0.15,
         "web_thickness_m": 0.01, "flange_w": 0.1, "flange_thickness_m": 0.02, "side_sign": -1.0},
        {"kind": "cylinder_ring", "radius": 2.0, "z": 2.0, "web_h": 0.12, "web_thickness_m": 0.02,
         "flange_w": 0.08, "flange_thickness_m": 0.015, "is_frame": True,
         "theta_start": 0.0, "theta_end": 2.0 * math.pi, "is_panel": False, "side_sign": -1.0},
    ]
    cylinder_canvas = t3d.Tkinter3DCanvas(root, width=800, height=500, bg="white")
    Application._populate_prop_3d_tk3d_native(Application, cylinder_canvas, cylinder_items)
    object_types = {obj.get("type") for obj in cylinder_canvas.objects}
    assert "cylinder" in object_types
    stiffener_kinds = sorted(
        obj.get("stiffener_type") for obj in cylinder_canvas.objects if obj.get("type") == "stiffener"
    )
    assert stiffener_kinds == ["longitudinal", "ring"]
    assert 16.0 in cylinder_canvas._thickness_legend["values"]
    root.destroy()


def test_prop_3d_export_mesh_records_face_colors_for_tk3d():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import numpy as np
    from matplotlib.figure import Figure

    from anystruct.main_application import Application

    fig = Figure()
    ax = fig.add_subplot(111, projection="3d")
    Application._init_prop_3d_export_mesh(ax, "test_preview")
    Application._add_box_3d(ax, 0.0, 1.0, 0.0, 2.0, 0.0, 0.02, facecolor="lightgrey", alpha=0.55)

    mesh = ax._anystruct_export_mesh
    assert len(mesh["faces"]) == 6
    assert mesh["face_colors"] == [("lightgrey", 0.55)] * 6

    grid = np.linspace(0.0, 1.0, 3)
    x_grid, y_grid = np.meshgrid(grid, grid)
    Application._append_grid_surface_to_prop_3d_export_mesh(
        ax, x_grid, y_grid, np.zeros_like(x_grid), color="silver", alpha=0.82
    )
    assert len(mesh["faces"]) == 10
    assert len(mesh["face_colors"]) == len(mesh["faces"])
    assert mesh["face_colors"][-1] == ("silver", 0.82)


def test_prop_3d_face_fill_maps_colors_and_alpha_to_tk():
    from anystruct.main_application import Application

    fill, stipple = Application._prop_3d_face_fill("lightgrey", 1.0)
    assert fill.startswith("#")
    assert stipple == ""
    _fill, stipple = Application._prop_3d_face_fill("silver", 0.82)
    assert stipple == "gray75"
    _fill, stipple = Application._prop_3d_face_fill("lightgrey", 0.30)
    assert stipple == "gray25"
    fill, _stipple = Application._prop_3d_face_fill(None, 1.0)
    assert fill.startswith("#")
    fill, _stipple = Application._prop_3d_face_fill("not-a-colour", 1.0)
    assert fill == "#d1d5db"


def test_initial_property_layout_uses_domain_selection_after_root_geometry_is_realized():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    init_tail = source[
        source.index("self._chk_show_prop_3d.place(relx=0.637, rely=0.705)"):
        source.index("# self._current_theme = 'default'")
    ]

    assert "parent.minsize(1200, 750)" in init_tail
    assert "parent.update_idletasks()" in init_tail
    assert "self.calculation_domain_selected(sync_cylinder_inputs=False)" in init_tail
    assert "self.gui_structural_properties()  # Initiating the flat panel structural properties" not in init_tail
    assert init_tail.index("parent.update_idletasks()") < init_tail.index(
        "self.calculation_domain_selected(sync_cylinder_inputs=False)"
    )


def test_single_line_optimizer_return_refreshes_hidden_line():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "def _prepare_simplified_optimizer_replacement(self):" in source
    assert "def _refresh_simplified_optimizer_replacement(self):" in source
    assert "def _replace_active_line_with_optimized_structure(self, optimized_structure):" in source
    assert "self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)" in source
    assert "self.set_selected_variables(self._active_line)" in source

    flat_close = source[
        source.index("def on_close_opt_window"):
        source.index("def on_close_opt_cyl_window")
    ]
    cylinder_close = source[
        source.index("def on_close_opt_cyl_window"):
        source.index("def on_close_opt_multiple_window")
    ]

    assert "self._prepare_simplified_optimizer_replacement()" in flat_close
    assert "self._replace_active_line_with_optimized_structure(returned_object[0])" in flat_close
    assert "else:\n            self.new_structure(multi_return=returned_object[0:2])" in flat_close
    assert "if not self._refresh_simplified_optimizer_replacement():" in flat_close
    assert "self._prepare_simplified_optimizer_replacement()" in cylinder_close
    assert "self.new_structure(cylinder_return=returned_object[0])" in cylinder_close
    assert "if not self._refresh_simplified_optimizer_replacement():" in cylinder_close


def test_single_line_mode_keeps_active_line_on_selected_or_dummy_line():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "def _single_mode_active_line_candidate(self):" in source
    selector_block = source[
        source.index("def _single_mode_active_line_candidate"):
        source.index("def _ensure_single_dummy_line")
    ]
    select_block = source[
        source.index("def _select_single_calculation_line"):
        source.index("def _ensure_manual_pressure_combination")
    ]

    assert "if self._active_line in self._line_dict:" in selector_block
    assert "return self._active_line" in selector_block
    assert "if self._single_line_name in self._line_dict:" in selector_block
    assert "return self._single_line_name" in selector_block
    assert "return sorted(self._line_dict.keys(), key=get_num)[0]" in selector_block
    assert "self._single_line_name = self._single_mode_active_line_candidate()" in select_block
    assert "self._active_line = self._single_line_name" in select_block


def test_cylinder_optimizer_return_bypasses_missing_flat_input_guard():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    new_structure = source[
        source.index("def new_structure"):
        source.index("def option_meny_structure_type_trace")
    ]
    visible_input_guard = source[
        source.index("def _uses_visible_structure_inputs"):
        source.index("def new_structure")
    ]

    assert "cylinder_return" in visible_input_guard
    assert "all(value is None" in visible_input_guard
    assert "self._uses_visible_structure_inputs(" in new_structure
    assert "self._show_missing_structure_input_warning()" in new_structure


def test_simplified_3d_preview_uses_main_canvas_place():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    placement_block = source[
        source.index("def _get_prop_3d_bottom_place"):
        source.index("def _resize_prop_3d_figure")
    ]

    assert "getattr(self, '_simplified_calculation_mode', False)" in placement_block
    assert "self._place_info_float(self._main_canvas, 'relx', 0.26)" in placement_block
    assert "self._place_info_float(self._main_canvas, 'relheight', 0.73)" in placement_block


def test_single_mode_mousewheel_zooms_embedded_3d_preview():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    embed_block = source[
        source.index("def _embed_prop_3d_figure"):
        source.index("def _set_prop_3d_view")
    ]
    main_wheel_block = source[
        source.index("def mouse_scroll(self, event):"):
        source.index("def button_2_click")
    ]

    assert "if getattr(self, '_simplified_calculation_mode', False):" in embed_block
    assert "self._prop_3d_canvas_widget.bind('<MouseWheel>', self._prop_3d_mouse_scroll)" in embed_block
    assert "self._prop_3d_canvas_widget.bind('<Button-4>', self._prop_3d_mouse_scroll)" in embed_block
    assert "self._prop_3d_canvas_widget.bind('<Button-5>', self._prop_3d_mouse_scroll)" in embed_block
    assert "def _prop_3d_mouse_scroll(self, event):" in embed_block
    assert "self._zoom_prop_3d_axes(0.88 if delta > 0 else 1.14)" in embed_block
    assert "return 'break'" in embed_block
    assert "self._canvas_scale += event.delta / 50" in main_wheel_block


def test_3d_preview_axis_zoom_scales_around_center():
    assert Application._scaled_axis_limits((0, 10), 0.5) == (2.5, 7.5)
    assert Application._scaled_axis_limits((-2, 2), 1.5) == (-3.0, 3.0)


def test_simplified_mode_draws_prepomax_imperfection_guidance_in_lower_pane():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "def draw_prepomax_imperfection_recommendations(self):" in source
    assert "FE-model imperfection input, DNVGL-OS-C401" in source
    assert "Use the value as initial geometry amplitude" in source
    assert "self.draw_prepomax_imperfection_recommendations()" in source
    assert "def _select_prepomax_imperfection_row(self, row_index):" in source
    assert "def _draw_prepomax_imperfection_sketch(self, canvas, row, x0, y0, x1, y1" in source
    assert "canvas.tag_bind(tag, '<Button-1>'" in source
    assert "self._selected_prepomax_imperfection_row = 0" in source
    assert "def _draw_prepomax_tolerance_table_button(self, canvas, canvas_width):" in source
    assert "text='Open DNV table'" in source
    assert "self.open_dnv_tolerance_table_image()" in source
    assert "def _dnv_tolerance_table_image_path(self):" in source
    assert "tolerances.png" in source
    assert "def open_dnv_tolerance_table_image(self):" in source
    assert "ImageTk.PhotoImage(resized)" in source
    assert "table_right = max(300, canvas_width * 0.74)" in source
    assert "row_height = max(22, min(32" in source
    assert "image_canvas = tk.Canvas(window" in source
    assert "x_scroll = ttk.Scrollbar(window, orient=tk.HORIZONTAL" in source
    assert "y_scroll = ttk.Scrollbar(window, orient=tk.VERTICAL" in source
    assert "def zoom_to(scale):" in source
    assert "def zoom_by(factor):" in source
    assert "text='Original size'" in source
    assert "image_canvas.configure(scrollregion=(0, 0, photo.width(), photo.height()))" in source
    assert "delta = 0.005 s" in source
    assert "delta = 0.0015 l" in source
    assert "delta = 0.02 s" in source
    assert "delta = 0.005 r" in source
    assert "delta = 0.01 g / (1 + g/r)" in source
    assert "sketch='plate_out_of_plane'" in source
    assert "sketch='parallel_misalignment'" in source
    assert "sketch='cylinder_stiffener_misalignment'" in source
    assert "sketch='local_roundness'" in source


def test_flat_panel_imperfection_recommendations_follow_dnvgl_os_c401():
    plate = SimpleNamespace(get_s=lambda: 0.7, get_span=lambda: 4.0)
    stiffener = SimpleNamespace(get_s=lambda: 0.7, get_span=lambda: 4.0, get_fl_w=lambda: 0.12)
    girder = SimpleNamespace(spacing=2.5, girder_lg=10.0, b=0.2)
    all_obj = SimpleNamespace(Plate=plate, Stiffener=stiffener, Girder=girder)

    rows = Application._flat_panel_imperfection_recommendations(all_obj)
    values = {row["detail"]: row["value_mm"] for row in rows}

    assert values["Plate out-of-plane"] == 3.5
    assert values["Stiffener web straightness"] == 6.0
    assert values["Stiffener flange straightness"] == 6.0
    assert values["Parallel stiffener misalignment"] == 14.0
    assert values["Girder web straightness"] == 15.0
    assert values["Parallel girder misalignment"] == 50.0
    sketches = {row["detail"]: row["sketch"] for row in rows}
    assert sketches["Plate out-of-plane"] == "plate_out_of_plane"
    assert sketches["Parallel stiffener misalignment"] == "parallel_misalignment"


def test_cylinder_imperfection_recommendations_follow_dnvgl_os_c401():
    shell = SimpleNamespace(radius=6.5, thk=0.019, dist_between_rings=3.3, length_of_shell=20.0)
    long_stiffener = SimpleNamespace(spacing=680.0, b=49.0)
    cylinder = SimpleNamespace(ShellObj=shell, LongStfObj=long_stiffener, panel_spacing=0.68)

    rows = Application._cylinder_imperfection_recommendations(cylinder)
    values = {row["detail"]: row["value_mm"] for row in rows}
    local_g = min(680.0, 1.15 * math.sqrt(3300.0 * 6500.0 * 19.0), math.pi * 6500.0 / 2.0)

    assert values["Radius deviation at ring"] == 32.5
    assert abs(values["Local out-of-roundness"] - (0.01 * local_g / (1.0 + local_g / 6500.0))) < 1e-12
    assert values["Longitudinal stiffener straightness"] == 4.95
    assert values["Longitudinal flange straightness"] == 4.95
    assert values["Longitudinal stiffener misalignment"] == 13.6
    sketches = {row["detail"]: row["sketch"] for row in rows}
    assert sketches["Local out-of-roundness"] == "local_roundness"
    assert sketches["Longitudinal stiffener misalignment"] == "cylinder_stiffener_misalignment"


def test_flat_panel_3d_preview_keeps_physical_aspect_and_uses_opaque_stiffeners():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    flat_3d_block = source[
        source.index("def draw_flat_panel_prop_3d"):
        source.index("def _add_cylinder_longitudinal_stiffener_3d")
    ]
    section_block = source[
        source.index("def _draw_section_web_and_flange_3d"):
        source.index("def draw_prop_3d")
    ]

    assert "alpha=1.0" in section_block
    assert "section_base_z" not in flat_3d_block
    assert "visual_z_span" not in flat_3d_block
    assert "self._apply_prop_3d_layout(fig, ax, width + 2.0 * x_pad, length + 2.0 * y_pad, z_top - z_bottom, zoom=1.52)" in flat_3d_block
    assert "ax.view_init(elev=22, azim=-55)" in flat_3d_block
    assert "self._embed_prop_3d(fig, ax, default_view=(22, -55))" in flat_3d_block


def test_3d_preview_can_export_prepomax_stl_mesh():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "import anystruct.solid_export as solid_export" in source
    assert "import anystruct.fem_integration as fe_runtime_solver" in source
    assert "ttk.Button(view_row, text='Solid export'" in source
    assert "ttk.Button(view_row, text='Shell export'" in source
    assert "ttk.Button(view_row, text='FE buckling'" not in source
    assert "text='FEM run'" in source
    assert "def on_open_runtime_fem_solver(self):" in source
    assert "fe_runtime_solver.open_runtime_fem_window(self._parent, self)" in source
    assert "def import_runtime_fem_buckling_result(self, runtime_result):" in source
    assert "fe_plate_fields.create_runtime_fea_buckling_session(" in source
    assert "self._fea_last_runtime_result" in source
    assert "def _place_runtime_fem_button(self):" in source
    assert "run_prop_3d_opensees_buckling" not in source
    assert "ttk.Button(view_row, text='STL solid'" not in source
    assert "ttk.Button(view_row, text='Mesh solid'" not in source
    assert "ttk.Button(view_row, text='STL shell'" not in source
    assert "ttk.Button(view_row, text='UNV shell'" not in source
    assert "ttk.Button(view_row, text='UNV solid'" not in source
    assert "def export_prop_3d_ifc_model(self):" in source
    assert "def export_prop_3d_ifc_shell_model(self):" in source
    assert "def _export_prop_3d_ifc_model_common(self, shell_export=False):" in source
    assert "def _ask_prop_3d_ifc_export_options(self, shell_export=False):" in source
    assert "transformation_scale = tk.StringVar(value='1.0')" in source
    assert "keep_ifc = tk.BooleanVar(value=False)" in source
    assert "ttk.Label(dialog, text='Transformation scale')" in source
    assert "'transformation_scale': scale" in source
    assert "text='Join all solid parts into one complete model'" in source
    assert "join_chk.configure(state='disabled' if shell_export else 'normal')" in source
    assert "'boolean_join_all_solids': bool(boolean_join.get()) and not bool(shell_export)" in source
    assert "confirmoverwrite=False" in source
    assert "if os.path.exists(filename):" in source
    assert "messagebox.askyesno(" in source
    assert "ifc_model_export.export_selected_structure_from_application" in source
    assert "shell_export=shell_export" in source
    assert "boolean_join_all_solids=options.get('boolean_join_all_solids', False)" in source
    assert "transformation_scale=options.get('transformation_scale', 1.0)" in source
    assert "'\\nTransformation scale: ' + str(options.get('transformation_scale', 1.0))" in source
    assert "def export_prop_3d_unv(self):" in source
    assert "self.export_prop_3d_ifc_model()" in source
    assert "def _get_prop_3d_shell_export_mesh(self):" in source
    assert "def _get_prop_3d_solid_export_mesh(self):" in source
    assert "def _write_prop_3d_stl_file(filename, mesh):" in source
    assert "def _write_prop_3d_unv_file(filename, mesh):" in source
    assert "stl_file.write('solid ' + name + '\\n')" in source
    assert "stl_file.write('      vertex {:.9g} {:.9g} {:.9g}\\n'.format(float(x), float(y), float(z)))" in source
    assert "'  2411\\n'" in source
    assert "'  2412\\n'" in source
    assert "unv_file.writelines(lines)" in source
    assert "element_id, 91, 1, 1, 7, 3" in source
    assert "VERTEX_POINT" not in source
    assert "def _deduplicate_export_mesh(mesh):" in source
    assert "def _format_unv_float(value):" in source
    assert "def _refined_export_mesh(mesh):" in source
    assert "def _subdivide_export_face(face_vertices, max_edge_length):" in source
    assert "def _update_prop_3d_export_mesh_size(ax, dims):" in source
    assert "flange_w / 2.0" in source
    assert "def _triangulate_export_face(face_vertices):" in source
    assert "def _stl_triangle_normal(triangle):" in source
    assert "def _init_prop_3d_export_mesh(ax, name):" in source
    assert "ax._anystruct_shell_export_mesh = shell_mesh" in source
    assert "self._prop_3d_shell_export_mesh" in source
    assert "_anystruct_shell_export_mesh' if shell_model else '_anystruct_export_mesh" in source
    assert (
        "def _append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, shell_model=False,\n"
        "                                                    color=None, alpha=1.0):"
    ) in source
    assert "Application._append_faces_to_prop_3d_export_mesh(ax, vertices, color=facecolor, alpha=alpha)" in source
    assert "self._init_prop_3d_export_mesh(ax, 'flat_panel_preview')" in source
    assert "self._init_prop_3d_export_mesh(ax, 'cylinder_preview')" in source
    assert "self._append_grid_surface_to_prop_3d_export_mesh(ax, x_grid, y_grid, z_grid, shell_model=True)" in source


def test_ifc_solid_and_shell_exports_use_separate_geometry_paths():
    ifc_source = Path(__file__).resolve().parents[1] / "anystruct" / "ifc_model_export.py"
    source = ifc_source.read_text(encoding="utf-8")

    assert "@functools.lru_cache(maxsize=1)\ndef _resource_ifcconvert_candidates" in source
    assert "@functools.lru_cache(maxsize=8)\ndef _ifcconvert_candidate_paths" in source
    assert "def _product_shape_from_closed_faces" in source
    assert "ctx.model.createIfcFacetedBrep" in source
    assert "def _temporary_filename_near" in source
    assert "def _write_ifc_atomic" in source
    assert "def _convert_ifc_atomic" in source
    assert "boolean_join_all_solids: bool = False" in source
    assert 'length_unit: str = "m"' in source
    assert "def _normalise_export_length_unit" in source
    assert "return \"mm\", 1000.0, \"MILLI\"" in source
    assert "length_unit_obj = model.createIfcSIUnit(None, \"LENGTHUNIT\", si_prefix, \"METRE\")" in source
    assert "length_scale: float = 1.0" in source
    assert "transformation_scale: float = 1.0" in source
    assert "def _normalise_transformation_scale" in source
    assert "Transformation scale must be a positive finite number." in source
    assert "def _scale_value" in source
    assert "solid_operands: list[Any] = field(default_factory=list)" in source
    assert "def _track_solid_operand" in source
    assert "def _replace_solid_parts_with_single_product" in source
    assert '"SolidModel"' in source
    assert '"model_type": "single_product_complete_model"' in source
    assert "os.replace(temp_filename, target_filename)" in source
    assert "timeout=timeout_seconds" in source
    assert "def _add_cylindrical_wall_solid" in source
    assert "def _add_plate_box" in source and "shell_export: bool = True" in source
    assert "if not shell_export:\n        props = {" in source
    assert '"model_type": "swept_solid"' in source
    assert '"model_type": "hollow_swept_solid"' in source
    assert 'base_r = radius if shell_export else max(radius + sign * shell_thk, EPS)' in source
    assert 'base_radius = radius if shell_export else max(radius + sign * max(shell_thk, 0.0), EPS)' in source
    assert "_add_cylinder_structure(ctx, app, cylinder_obj, active_line, side_sign, shell_export=shell_export)" in source
    assert "_add_flat_structure(ctx, app, all_obj, active_line, side_sign, shell_export=shell_export)" in source
    assert "_replace_solid_parts_with_single_product(ctx, active_line)" in source
    assert "_convert_ifc_with_ifcconvert(native_ifc_filename, requested_filename" not in source
    assert "_convert_ifc_atomic(native_ifc_filename, requested_filename" in source
    assert "_write_ifc_atomic(ctx.model, native_ifc_filename)" in source
    assert '"thickness_exported_as_geometry": not bool(shell_export)' in source
    assert '"boolean_join_all_solids": bool(ctx.boolean_join_all_solids)' in source
    assert '"export_length_unit": ctx.length_unit' in source
    assert '"export_length_scale_from_m": ctx.length_scale' in source
    assert '"transformation_scale": ctx.transformation_scale' in source
    assert 'predefined_type="RING"' not in source
    assert "This exporter currently uses zero-thickness shell/surface" not in source


def test_shell_export_mesh_is_separate_from_solid_preview_mesh():
    ax = SimpleNamespace()
    Application._init_prop_3d_export_mesh(ax, "preview")

    Application._append_faces_to_prop_3d_export_mesh(ax, [[
        (0.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
    ]], shell_model=True)

    assert ax._anystruct_export_mesh["faces"] == []
    assert len(ax._anystruct_shell_export_mesh["faces"]) == 1
    assert ax._anystruct_shell_export_mesh["name"] == "preview_shell"


def test_flat_shell_plate_export_is_split_on_member_attachment_lines():
    ax = SimpleNamespace()
    Application._init_prop_3d_export_mesh(ax, "plate")

    Application._append_flat_plate_shell_grid_to_prop_3d_export_mesh(
        ax, x_breaks=[0.0, 2.0], y_breaks=[0.0, 0.75, 1.5, 2.0])

    faces = ax._anystruct_shell_export_mesh["faces"]
    vertices = ax._anystruct_shell_export_mesh["vertices"]
    assert len(faces) == 3
    face_edges = []
    for face in faces:
        face_vertices = [vertices[index - 1] for index in face]
        face_edges.append((face_vertices[0][1], face_vertices[2][1]))
    assert face_edges == [(0.0, 0.75), (0.75, 1.5), (1.5, 2.0)]


def test_3d_export_box_geometry_uses_exact_extents():
    class FakeAxis(SimpleNamespace):
        def add_collection3d(self, collection):
            self.collections.append(collection)

    ax = FakeAxis(collections=[])
    Application._init_prop_3d_export_mesh(ax, "box")

    Application._add_box_3d(ax, 1.25, 3.75, -0.4, 2.6, 0.015, 0.047)

    xs = [vertex[0] for vertex in ax._anystruct_export_mesh["vertices"]]
    ys = [vertex[1] for vertex in ax._anystruct_export_mesh["vertices"]]
    zs = [vertex[2] for vertex in ax._anystruct_export_mesh["vertices"]]
    assert abs(min(xs) - 1.25) < 1e-12
    assert abs(max(xs) - 3.75) < 1e-12
    assert abs(min(ys) + 0.4) < 1e-12
    assert abs(max(ys) - 2.6) < 1e-12
    assert abs(min(zs) - 0.015) < 1e-12
    assert abs(max(zs) - 0.047) < 1e-12
    assert abs((max(zs) - min(zs)) - 0.032) < 1e-12


def test_3d_flat_section_geometry_uses_exact_web_and_flange_dimensions():
    class FakeAxis(SimpleNamespace):
        def add_collection3d(self, collection):
            self.collections.append(collection)

    app = object.__new__(Application)
    ax = FakeAxis(collections=[])
    Application._init_prop_3d_export_mesh(ax, "section")
    dims = {
        "web_h": 0.42,
        "web_thk": 0.014,
        "flange_w": 0.18,
        "flange_thk": 0.025,
        "type": "L",
    }

    app._draw_section_web_and_flange_3d(
        ax, "x", x_center=5.0, y_center=2.0, length=3.0,
        plate_thk=0.016, dims=dims, side_sign=1.0,
    )

    solid_vertices = ax._anystruct_export_mesh["vertices"]
    solid_ys = sorted({round(vertex[1], 12) for vertex in solid_vertices})
    solid_zs = sorted({round(vertex[2], 12) for vertex in solid_vertices})
    assert 1.993 in solid_ys
    assert 2.007 in solid_ys
    assert round(1.993 + 0.18, 12) in solid_ys
    assert 0.016 in solid_zs
    assert round(0.016 + 0.42, 12) in solid_zs
    assert round(0.016 + 0.42 + 0.025, 12) in solid_zs

    shell_faces = ax._anystruct_shell_export_mesh["faces"]
    shell_vertices = ax._anystruct_shell_export_mesh["vertices"]
    web_face = [shell_vertices[index - 1] for index in shell_faces[0]]
    flange_face = [shell_vertices[index - 1] for index in shell_faces[1]]
    assert {round(vertex[1], 12) for vertex in web_face} == {2.0}
    assert {round(vertex[2], 12) for vertex in web_face} == {0.0, 0.42}
    assert {round(vertex[2], 12) for vertex in flange_face} == {0.42}
    flange_ys = [vertex[1] for vertex in flange_face]
    assert abs((max(flange_ys) - min(flange_ys)) - 0.18) < 1e-12


def test_3d_member_positions_keep_exact_spacing_and_symmetric_remainder():
    positions = Application._positions_from_length_and_spacing(10.0, 3.0, include_ends=True)
    assert positions == [0.5, 3.5, 6.5, 9.5]
    gaps = [round(positions[idx + 1] - positions[idx], 12) for idx in range(len(positions) - 1)]
    assert gaps == [3.0, 3.0, 3.0]
    assert positions[0] == 10.0 - positions[-1]

    internal_positions = Application._positions_from_length_and_spacing(10.0, 3.0, include_ends=False)
    assert internal_positions == positions

    # Exact multiples put the bounding members on the model edges so every
    # bay keeps the exact spacing; growth stays symmetric about the centre.
    regular_end_positions = Application._positions_from_length_and_spacing(12.0, 3.0, include_ends=True)
    assert regular_end_positions == [0.0, 3.0, 6.0, 9.0, 12.0]
    assert Application._positions_from_length_and_spacing(12.0, 3.0, include_ends=False) == [3.0, 6.0, 9.0]

    dense_end_positions = Application._positions_from_length_and_spacing(10.0, 0.75, include_ends=True)
    dense_gaps = [dense_end_positions[idx + 1] - dense_end_positions[idx]
                  for idx in range(len(dense_end_positions) - 1)]
    assert round(max(dense_gaps) - min(dense_gaps), 12) == 0.0
    assert max(dense_gaps) == 0.75
    assert dense_end_positions[0] == 10.0 - dense_end_positions[-1]


def test_shared_representation_positions_are_used_by_preview_and_fe_solver():
    expected = list(representation_geometry.centered_member_positions(10.0, 0.75, fallback_midpoint=True))

    assert Application._positions_from_length_and_spacing(10.0, 0.75, include_ends=True) == expected
    assert list(fe_solver._centered_member_positions(10.0, 0.75, fallback_midpoint=True)) == expected
    assert expected[0] == 10.0 - expected[-1]


def test_panel_length_expansion_keeps_stiffener_span_as_girder_bay():
    # Lp equal to the stiffener span puts the girders on the panel edges;
    # longer panels add full bays symmetrically about the centre.
    assert Application._support_positions_from_length_and_span(4.0, 4.0) == [0.0, 4.0]
    assert Application._support_positions_from_length_and_span(12.0, 4.0) == [0.0, 4.0, 8.0, 12.0]
    assert Application._support_positions_from_length_and_span(10.0, 4.0) == [1.0, 5.0, 9.0]
    assert Application._support_positions_from_length_and_span(3.0, 4.0) == []
    assert Application._bay_ranges_from_support_positions(10.0, [1.0, 5.0, 9.0]) == [
        (0.0, 1.0),
        (1.0, 5.0),
        (5.0, 9.0),
        (9.0, 10.0),
    ]

    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    main_text = main_source.read_text(encoding="utf-8")
    flat_3d_block = main_text[
        main_text.index("def draw_flat_panel_prop_3d"):
        main_text.index("def _add_cylinder_longitudinal_stiffener_3d")
    ]
    assert "girder_xs = self._support_positions_from_length_and_span(width, span, max_count=80)" in flat_3d_block
    assert "for x_pos in girder_xs:" in flat_3d_block
    assert "for bay_x0, bay_x1 in solid_x_breaks:" in flat_3d_block

    ifc_source = Path(__file__).resolve().parents[1] / "anystruct" / "ifc_model_export.py"
    ifc_text = ifc_source.read_text(encoding="utf-8")
    assert "import anystruct.representation_geometry as representation_geometry" in main_text
    assert "from anystruct import representation_geometry" in ifc_text
    assert "def _support_positions_from_length_and_span(length: float, span: float, max_count: int = 80)" in ifc_text
    assert "representation_geometry.centered_member_positions(" in ifc_text
    assert "def _bay_ranges_from_support_positions(" in ifc_text
    flat_export_block = ifc_text[
        ifc_text.index("def _add_flat_structure"):
        ifc_text.index("def _is_cylinder_panel")
    ]
    assert "girder_xs = _support_positions_from_length_and_span(width, span, max_count=80)" in flat_export_block
    assert "for index, x_pos in enumerate(girder_xs, start=1):" in flat_export_block
    assert "bay_ranges = _bay_ranges_from_support_positions(width, girder_xs, girder_gap)" in flat_export_block
    assert "for bay_index, (bay_x0, bay_x1) in enumerate(bay_ranges, start=1):" in flat_export_block


def test_cylinder_ring_frames_suppress_overlapping_ring_stiffeners():
    assert Application._ring_member_half_width({"web_thk": 0.02, "flange_w": 0.16}) == 0.08
    assert Application._ring_positions_without_heavy_frame_overlap(
        [2.5, 4.86, 5.0, 5.14, 7.5],
        [5.0],
        ring_half_width=0.05,
        frame_half_width=0.10,
    ) == [2.5, 7.5]
    assert Application._ring_positions_without_heavy_frame_overlap(
        [4.86, 5.14],
        [],
        ring_half_width=0.05,
        frame_half_width=0.10,
    ) == [4.86, 5.14]

    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    main_text = main_source.read_text(encoding="utf-8")
    cylinder_block = main_text[
        main_text.index("def draw_cylinder_prop_3d"):
        main_text.index("def draw_prop", main_text.index("def draw_cylinder_prop_3d"))
    ]
    assert "frame_dims = None" in cylinder_block
    assert "girder_positions = []" in cylinder_block
    assert "ring_positions = self._ring_positions_without_heavy_frame_overlap(" in cylinder_block
    assert cylinder_block.index("ring_positions = self._ring_positions_without_heavy_frame_overlap(") < \
        cylinder_block.index("if frame_dims is not None:")

    ifc_source = Path(__file__).resolve().parents[1] / "anystruct" / "ifc_model_export.py"
    ifc_text = ifc_source.read_text(encoding="utf-8")
    assert "def _ring_positions_without_heavy_frame_overlap(" in ifc_text
    cylinder_export_block = ifc_text[
        ifc_text.index("def _add_cylinder_structure"):
        ifc_text.index("def export_selected_structure_from_application")
    ]
    assert "frame_positions: list[float] = []" in cylinder_export_block
    assert "ring_positions = _ring_positions_without_heavy_frame_overlap(" in cylinder_export_block
    assert cylinder_export_block.index("ring_positions = _ring_positions_without_heavy_frame_overlap(") < \
        cylinder_export_block.index("if frame_dims is not None:")


def test_ifc_shell_ring_webs_are_not_faceted_into_many_panels():
    ifc_source = Path(__file__).resolve().parents[1] / "anystruct" / "ifc_model_export.py"
    ifc_text = ifc_source.read_text(encoding="utf-8")

    assert "def _ring_web_shell_faces(" in ifc_text
    helper_block = ifc_text[
        ifc_text.index("def _ring_web_shell_faces("):
        ifc_text.index("def _conical_wall_solid_faces")
    ]
    assert "face_count = 2 if is_full_circle else 1" in helper_block
    assert "outer = [" in helper_block
    assert "inner = [" in helper_block
    assert "faces.append(outer + inner)" in helper_block

    ring_block = ifc_text[
        ifc_text.index("def _add_ring_set"):
        ifc_text.index("def _add_cylinder_structure")
    ]
    assert "_ring_web_shell_faces(r0, r1, z_pos, theta_start, theta_end)" in ring_block
    assert "_annular_radial_faces(r0, r1, z_pos, theta_start, theta_end, segments)" not in ring_block


def test_unv_export_writes_nodes_and_elements(tmp_path):
    mesh = {
        "name": "unv_smoke",
        "vertices": [
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
        ],
        "faces": [[1, 2, 3, 4]],
        "max_edge_length": None,
    }
    filename = tmp_path / "preview.unv"

    Application._write_prop_3d_unv_file(filename, mesh)

    content = filename.read_text(encoding="utf-8")
    assert "  2411\n" in content
    assert "  2412\n" in content
    assert "         1         1         1        11\n" in content
    assert "         1        91         1         1         7         3\n" in content
    assert len(content.splitlines()) > 8


def test_3d_preview_can_swap_flat_and_cylinder_member_side():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    flat_3d_block = source[
        source.index("def draw_flat_panel_prop_3d"):
        source.index("def _add_cylinder_longitudinal_stiffener_3d")
    ]
    section_block = source[
        source.index("def _draw_section_web_and_flange_3d"):
        source.index("def draw_prop_3d")
    ]
    cylinder_block = source[
        source.index("def _add_cylinder_longitudinal_stiffener_3d"):
        source.index("def draw_prop", source.index("def draw_cylinder_prop_3d"))
    ]

    assert "self._new_prop_3d_opposite_side = tk.BooleanVar()" in source
    assert "ttk.Checkbutton(view_row, text='Opposite side'" in source
    assert "def _prop_3d_member_side_sign(self):" in source
    assert "side_sign=1.0" in section_block
    assert "web_z = (-web_h, 0.0)" in section_block
    assert "flange_z = (-(web_h + fl_t), -web_h)" in section_block
    assert "member_side_sign = self._prop_3d_member_side_sign()" in flat_3d_block
    assert "side_sign=member_side_sign" in flat_3d_block
    assert "z_bottom = min(-0.02 * z_top, min_z * 1.08)" in flat_3d_block
    assert "side_sign=1.0" in cylinder_block
    assert "radius + side_sign * web_h" in cylinder_block
    assert "member_side_sign = self._prop_3d_member_side_sign()" in cylinder_block
    assert "side_sign=member_side_sign" in cylinder_block


def test_cylinder_panel_domains_render_as_angular_sector_preview():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "def _is_cylinder_panel_preview(cyl_obj):" in source
    assert "api_helpers.domain_for_geometry_id(cyl_obj.geometry)" in source
    assert "return 'panel' in domain.lower() and 'shell' not in domain.lower()" in source
    assert "def _cylinder_preview_theta_range(self, cyl_obj):" in source
    assert "math.radians(60.0)" in source
    assert "theta_range=theta_range" in source
    assert "3D cylinder panel preview (60 deg)" in source
    assert "arc_length = abs(theta_end - theta_start) * radius" in source


def test_unstiffened_flat_plate_input_check_does_not_require_stiffener_dimensions():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    missing_input_block = source[
        source.index("def _structure_input_is_missing"):
        source.index("def _show_missing_structure_input_warning")
    ]

    assert "required_inputs = [self._new_stf_spacing.get(), self._new_plate_thk.get()]" in missing_input_block
    assert "if self._new_calculation_domain.get() != 'Flat plate, unstiffened':" in missing_input_block
    assert "required_inputs.extend([self._new_stf_web_h.get(), self._new_stf_web_t.get()])" in missing_input_block
    assert "self._new_stf_web_h.get() == 0" not in missing_input_block


def test_unstiffened_flat_plate_color_state_initializes_fatigue_color():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    no_stiffener_start = source.index("else:\n                    sec_mod = [0, 0]")
    no_stiffener_block = source[
        no_stiffener_start:
        source.index("if slamming_pressure is not None and slamming_pressure > 0 and obj_scnt_calc_stf is not None:")
    ]

    assert "color_fatigue = 'green'" in no_stiffener_block
    assert "shear_area = 0" in no_stiffener_block
    assert "min_shear = 0" in no_stiffener_block
    assert "min_sec_mod = 0" in no_stiffener_block
    assert no_stiffener_start + no_stiffener_block.index("color_fatigue = 'green'") < source.index(
        "return_dict['colors'][current_line] = {'buckling': color_buckling, 'fatigue': color_fatigue,"
    )


def test_color_code_summary_handles_models_without_stiffener_spacing():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    color_code_block = source[
        source.index("spacings = list()"):
        source.index("line_color_coding = {}")
    ]

    assert "max_spacing = max(spacing) if len(spacing) != 0 else 0" in color_code_block
    assert "min_spacing = min(spacing) if len(spacing) != 0 else 0" in color_code_block
    assert "'max spacing': max(spacing)" not in color_code_block
    assert "'min spacing': min(spacing)" not in color_code_block


def test_color_state_cog_handles_zero_weight_lines():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "tot_cog = [0, 0] if tot_weight == 0 else [weight_mult_dist_x / tot_weight," in source


def test_main_application_uses_geometry_helpers_for_active_lookups():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "api_helpers.geometry_id_for_domain(self._new_calculation_domain.get())" in source
    assert "api_helpers.domain_for_geometry_id(main_dict_cyl['geometry'][0])" in source
    assert "api_helpers.domain_for_geometry_id(self._line_to_struc[self._active_line][5].geometry)" in source
    assert "self._shell_geometries_map[self._new_calculation_domain.get()]" not in source
    assert "CylinderAndCurvedPlate.geomeries[main_dict_cyl['geometry'][0]]" not in source
    assert "CylinderAndCurvedPlate\n                                                 .geomeries[" not in source


def test_main_application_uses_helpers_for_structure_property_unit_conversions():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    services_source = (Path(__file__).resolve().parents[1] / "anystruct" / "project_services.py").read_text(
        encoding="utf-8"
    )
    source = main_source.read_text(encoding="utf-8")
    flat_builder = source[
        source.index("def _build_flat_structure_properties"):
        source.index("def _build_cylinder_structure_property_request")
    ]
    cylinder_builder = source[
        source.index("def _build_cylinder_structure_properties"):
        source.index("def new_structure")
    ]
    property_block = flat_builder + cylinder_builder

    assert "FlatStructurePropertyService.build(" in flat_builder
    assert "CylinderStructurePropertyService.build(" in cylinder_builder
    assert "api_helpers.mpa_to_pa" in services_source
    assert "api_helpers.mm_to_m" in services_source
    assert "helper_cylinder_stress_to_force_to_stress(" in services_source
    assert "api_helpers.mpa_to_pa" not in property_block
    assert "api_helpers.mm_to_m" not in property_block
    assert "helper_cylinder_stress_to_force_to_stress(" not in property_block
    assert not re.search(r"[\w.)\]]\s*\*\s*1e6", property_block)
    assert not re.search(r"[\w.)\]]\s*/\s*1000", property_block)


def test_main_application_uses_shared_ml_model_loader():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    ml_loader_block = source[
        source.index("self._ML_buckling ="):
        source.index("# Used to select parameter")
    ]

    assert "ml_models.load_buckling_models((self._root_dir,))" in ml_loader_block
    assert "pickle.load(" not in ml_loader_block


def test_single_flat_domains_display_single_optimizer_button():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    map_start = source.index("self._optimization_buttons =")
    optimization_map = source[
        map_start:
        source.index("# Load information button", map_start)
    ]

    assert "'Flat plate, unstiffened': [self._opt_button]" in optimization_map
    assert "'Flat plate, unstiffened place': [[lc_x, lc_y - 6 * lc_y_delta, 0.04, 0.098]]" in optimization_map
    assert "'Flat plate, stiffened with girder': [self._opt_button]" in optimization_map
    assert "'Flat plate, stiffened with girder place':" in optimization_map


def test_flat_optimizer_default_ranges_are_dimension_specific():
    opt_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_window.py"
    source = opt_source.read_text(encoding="utf-8")
    defaults = source[
        source.index("# setting default values"):
        source.index("self._new_algorithm.set('anysmart')")
    ]
    girder_bounds = source[
        source.index("def _set_girder_iteration_bounds"):
        source.index("def _disable_stiffener_only_constraints")
    ]

    for expected in (
        "self._new_pl_thk_upper.set(30)",
        "self._new_pl_thk_lower.set(10)",
        "self._new_web_h_upper.set(500)",
        "self._new_web_h_lower.set(200)",
        "self._new_web_thk_upper.set(30)",
        "self._new_web_thk_lower.set(10)",
        "self._new_fl_w_upper.set(300)",
        "self._new_fl_w_lower.set(100)",
        "self._new_fl_thk_upper.set(30)",
        "self._new_fl_thk_lower.set(10)",
    ):
        assert expected in defaults

    for expected in (
        "self._new_girder_web_h_upper.set(1000)",
        "self._new_girder_web_h_lower.set(500)",
        "self._new_girder_web_thk_upper.set(30)",
        "self._new_girder_web_thk_lower.set(10)",
        "self._new_girder_fl_w_upper.set(300)",
        "self._new_girder_fl_w_lower.set(100)",
        "self._new_girder_fl_thk_upper.set(30)",
        "self._new_girder_fl_thk_lower.set(10)",
    ):
        assert expected in girder_bounds

    for expected in (
        "self._new_delta_spacing.set(5)",
        "self._new_delta_pl_thk.set(init_thk)",
        "self._new_delta_web_h.set(init_dim)",
        "self._new_delta_web_thk.set(init_thk)",
        "self._new_delta_fl_w.set(init_dim)",
        "self._new_delta_fl_thk.set(init_thk)",
        "self._new_delta_girder_web_h.set(100)",
        "self._new_delta_girder_web_thk.set(init_thk)",
        "self._new_delta_girder_fl_w.set(init_dim)",
        "self._new_delta_girder_fl_thk.set(init_thk)",
    ):
        assert expected in defaults


def test_other_optimizer_default_ranges_are_dimension_specific():
    root = Path(__file__).resolve().parents[1] / "anystruct"

    for filename in ("optimize_multiple_window.py", "optimize_geometry.py"):
        source = (root / filename).read_text(encoding="utf-8")
        defaults = source[
            source.index("# setting default values"):
            source.index("self._new_algorithm.set('anysmart')")
        ]

        for expected in (
            "self._new_pl_thk_upper.set(round(30, 5))",
            "self._new_pl_thk_lower.set(round(10, 5))",
            "self._new_web_h_upper.set(round(500, 5))",
            "self._new_web_h_lower.set(round(200, 5))",
            "self._new_web_thk_upper.set(round(30, 5))",
            "self._new_web_thk_lower.set(round(10, 5))",
            "self._new_fl_w_upper.set(round(300, 5))",
            "self._new_fl_w_lower.set(round(100, 5))",
            "self._new_fl_thk_upper.set(round(30, 5))",
            "self._new_fl_thk_lower.set(round(10, 5))",
            "self._new_delta_web_h.set(init_dim)",
            "self._new_delta_fl_w.set(init_dim)",
            "self._new_delta_web_thk.set(init_thk)",
            "self._new_delta_fl_thk.set(init_thk)",
        ):
            assert expected in defaults

    cylinder_source = (root / "optimize_cylinder.py").read_text(encoding="utf-8")
    cylinder_defaults = cylinder_source[
        cylinder_source.index("default_shell_upper_bounds ="):
        cylinder_source.index("self._default_data =")
    ]

    for expected in (
        "default_shell_upper_bounds = np.array([0.03, 3, 5, 5, 10, None, None, None])",
        "default_shell_lower_bounds = np.array([0.01, 2.5, 5, 5, 10, None, None, None])",
        "default_long_upper_bounds = np.array([0.8, None, 0.5, 0.03, 0.3, 0.03, None, None])",
        "default_long_lower_bounds = np.array([0.7, None, 0.2, 0.01, 0.1, 0.01, None, None])",
        "default_ring_stf_upper_bounds = np.array([None, None, 0.5, 0.03, 0.3, 0.03, None, None])",
        "default_ring_stf_lower_bounds = np.array([None, None, 0.2, 0.010, 0.1, 0.010, None, None])",
        "default_ring_frame_upper_bounds = np.array([None, None, 1.0, 0.03, 0.3, 0.03, None, None])",
        "default_ring_frame_deltas = np.array([None, None, 0.1, 0.005, 0.05, 0.005, None, None])",
        "default_ring_frame_lower_bounds = np.array([None, None, 0.5, 0.01, 0.1, 0.01, None, None])",
    ):
        assert expected in cylinder_defaults


def test_new_structure_delegates_property_building():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    new_structure = source[
        source.index("def new_structure"):
        source.index("def option_meny_structure_type_trace")
    ]
    resolver = source[
        source.index("def _resolve_new_structure_properties"):
        source.index("def _add_structure_to_active_line")
    ]
    flat_builder = source[
        source.index("def _build_flat_structure_property_request"):
        source.index("def _build_cylinder_structure_property_request")
    ]
    cylinder_builder = source[
        source.index("def _build_cylinder_structure_property_request"):
        source.index("def _structure_input_is_missing")
    ]
    add_structure = source[
        source.index("def _add_structure_to_active_line"):
        source.index("def _scale_existing_flat_structure_if_needed")
    ]
    update_structure = source[
        source.index("def _update_existing_active_line_structure"):
        source.index("def _replace_active_line_with_optimized_structure")
    ]
    apply_structure = source[
        source.index("def _apply_resolved_new_structure"):
        source.index("def _replace_active_line_with_optimized_structure")
    ]
    new_structure_context = source[
        source.index("def _prepare_new_structure_context"):
        source.index("def new_structure")
    ]

    assert "class NewStructureProperties" in source
    assert "self._build_flat_structure_properties()" in resolver
    assert "elif isinstance(toggle_multi, tuple):" in resolver
    assert "prop_dict, obj_dict_stf = toggle_multi" in resolver
    assert "if cylinder_return is not None:" in resolver
    assert "cylinder_obj = cylinder_return" in resolver
    assert "self._cylinder_property_parts(cylinder_return)" in resolver
    assert "NewStructureProperties(" in resolver
    assert "FlatStructurePropertyRequest(" in flat_builder
    assert "FlatStructurePropertyService.build(" in flat_builder
    assert "api_helpers.mpa_to_pa" not in flat_builder
    assert "api_helpers.mm_to_m" not in flat_builder
    assert "CylinderStructurePropertyRequest(" in cylinder_builder
    assert "CylinderStructurePropertyService.build(" in cylinder_builder
    assert "helper_cylinder_stress_to_force_to_stress(" not in cylinder_builder
    assert "api_helpers.mpa_to_pa" not in cylinder_builder
    assert "api_helpers.mm_to_m" not in cylinder_builder
    assert "self._build_cylinder_structure_properties()" in resolver
    assert "self.save_no_dialogue(backup=True)" in new_structure_context
    assert "self._ensure_single_dummy_line()" in new_structure_context
    assert "self._ensure_manual_pressure_combination(self._active_line, default_enabled=True)" in new_structure_context
    assert "self._structure_input_is_missing()" in new_structure
    assert "self._create_all_structure_from_properties(resolved.prop_dict)" in add_structure
    assert "self._create_cylinder_structure_from_properties(" in add_structure
    assert "self._clear_tanks_and_grid()" in add_structure
    assert "self._clear_tanks_and_grid()" in update_structure
    assert "self._refresh_after_structure_change(suspend_recalc)" in new_structure
    assert "self._resolve_new_structure_properties(" in new_structure
    assert "self._apply_resolved_new_structure(resolved, cylinder_return)" in new_structure
    assert "self._add_structure_to_active_line(resolved)" in apply_structure
    assert "self._update_existing_active_line_structure(resolved, cylinder_return)" in apply_structure
    assert "self._calculate_load_combinations_after_structure_update()" in apply_structure
    assert "self._add_structure_to_active_line(" not in new_structure
    assert "self._update_existing_active_line_structure(" not in new_structure
    assert "self._calculate_load_combinations_after_structure_update()" not in new_structure
    assert "obj_dict = {" not in new_structure
    assert "shell_dict = {" not in new_structure
    assert "AllStructure(" not in new_structure
    assert "CylinderAndCurvedPlate(" not in new_structure
    assert "self._tank_dict = {}" not in new_structure
    assert "self.update_frame()" not in new_structure
    assert "set_main_properties(prop_dict)" not in new_structure
    assert "calculate_all_load_combinations_for_line_all_lines()" not in new_structure


def test_savefile_delegates_save_command_assembly_and_persistence():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    save_no_dialogue = source[
        source.index("def save_no_dialogue"):
        source.index("def savefile")
    ]
    savefile = source[
        source.index("def savefile"):
        source.index("def _build_project_save_input")
    ]
    save_input_builder = source[
        source.index("def _build_project_save_input"):
        source.index("def openfile")
    ]

    assert "ProjectFileDialogService.backup_save_target(" in save_no_dialogue
    assert "ProjectFileDialogService.remembered_save_target(" in save_no_dialogue
    assert "ProjectSaveService.save_path(" in savefile
    assert "ProjectFileDialogService.selected_save_target(" in savefile
    assert "self._build_project_save_input()" in savefile
    assert "ProjectSnapshotService.create_state(" not in savefile
    assert "save_state_to_path(" not in savefile
    assert "ProjectSaveInput(" in save_input_builder


def test_openfile_delegates_project_open_application_steps():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    openfile = source[
        source.index("def openfile"):
        source.index("def restore_previous")
    ]

    assert "ProjectOpenService.open_path(" in openfile
    assert "ProjectFileDialogService.selected_open_target(" in openfile
    assert "self._build_project_hydration_defaults()" in openfile
    assert "self._apply_open_project_text_and_theme(open_transfer)" in openfile
    assert "self._apply_open_project_geometry_and_objects(open_transfer, hydration)" in openfile
    assert "self._apply_open_project_accelerations(open_transfer)" in openfile
    assert "self._apply_open_project_load_combinations(open_transfer)" in openfile
    assert "self._apply_open_project_tanks(open_transfer)" in openfile
    assert "self._apply_open_project_canvas_scale()" in openfile
    assert "self._finalize_open_project(open_transfer, target.path)" in openfile
    assert "ProjectHydrationDefaults(" not in openfile
    assert "load_state_from_path(" not in source
    assert "json.load(" not in source


def test_restore_and_example_open_delegate_file_target_resolution():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    restore_block = source[
        source.index("def restore_previous"):
        source.index("def open_example")
    ]
    example_block = source[
        source.index("def open_example"):
        source.index("def open_example_excel_file")
    ]

    assert "ProjectFileDialogService.restore_target(" in restore_block
    assert "ProjectPersistenceService.backup_exists(" not in restore_block
    assert "ProjectPersistenceService.backup_path(" not in restore_block
    assert "ProjectFileDialogService.example_open_target(" in example_block
    assert "os.path.isfile(file_name)" not in example_block
    assert "self._root_dir + '/' + file_name" not in example_block


def test_example_excel_open_delegates_file_target_resolution():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    example_excel_block = source[
        source.index("def open_example_excel_file"):
        source.index("def _sync_excel_import_geometry")
    ]

    assert "ProjectFileDialogService.example_open_target(" in example_excel_block
    assert "ExcelProjectImportService.open_example_path(target.path)" in example_excel_block
    assert "os.path.isfile(file_name)" not in example_excel_block
    assert "self._root_dir + '/' + file_name" not in example_excel_block


def test_line_pressure_calculation_delegates_to_project_service():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    calculation_block = source[
        source.index("def calculate_all_load_combinations_for_line"):
        source.index("def run_optimizer_for_line")
    ]
    pressure_block = source[
        source.index("def get_highest_pressure"):
        source.index("def get_fatigue_pressures")
    ]

    assert "LinePressureService.calculate_combinations(" in calculation_block
    assert "LinePressureService.calculate_one(" in calculation_block
    assert "LinePressureInput(" in calculation_block
    assert not re.search(r"\bone_load_combination\(", calculation_block)
    assert "LinePressureService.highest_pressure(" in pressure_block


def test_report_and_sesam_callbacks_delegate_request_orchestration():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    report_block = source[
        source.index("def _build_report_data_snapshot"):
        source.index("def create_accelerations")
    ]
    export_block = source[
        source.index("def export_to_js"):
        source.index("if __name__ == '__main__':")
    ]

    assert "ReportRequestService.create_pdf(" in report_block
    assert "ReportRequestService.create_table(" in report_block
    assert "def _build_report_data_snapshot" in report_block
    assert "def _get_ml_classes" in source
    assert "ReportDataSnapshot(" in report_block
    assert "self._build_report_data_snapshot()" in report_block
    assert "ml_classes=self._get_ml_classes()" in report_block
    assert "ml_classes=self._ML_classes" not in report_block
    assert 'ReportRequest(filename, "Section results", 10, self)' not in report_block
    assert "LetterMaker" not in source
    assert "SimpleDocTemplate" not in source
    assert "reportlab" not in source
    assert "ProjectFileDialogService.selected_output_target(" in report_block
    assert "filedialog.asksaveasfilename(defaultextension=\".pdf\")" in report_block
    assert not re.search(r"filedialog\.asksaveasfile\(", report_block)
    assert "SesamExportService.write_js_path(" in export_block
    assert "sesam.JSfile(" not in export_block
    assert "save_file.writelines(" not in export_block
    assert not re.search(r"filedialog\.asksaveasfile\(", export_block)
    assert "ProjectFileDialogService.selected_output_target(" in export_block


def test_excel_callbacks_delegate_workbook_adapter_access():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    excel_block = source[
        source.index("def open_example_excel_file"):
        source.index("def on_open_structure_window")
    ]

    assert "ExcelProjectImportService.open_example_path(" in excel_block
    assert "ExcelProjectImportService.read_path(" in excel_block
    assert "ProjectFileDialogService.selected_open_target(" in excel_block
    assert "ExcelProjectGeometryImportService.add_records(" in excel_block
    assert "def _sync_excel_import_geometry" in excel_block
    assert "def _build_flat_structure_property_request_from_excel_record" in source
    assert "def _build_flat_structure_property_request_from_cylinder_excel_record" in source
    assert "def _build_cylinder_excel_import_defaults" in source
    assert "FlatStructurePropertyService.build(flat_request)" in excel_block
    assert "CylinderExcelImportPropertyService.build_request(" in excel_block
    assert "CylinderStructurePropertyService.build(cylinder_request)" in excel_block
    assert "cylinder_return=cylinder_obj" in excel_block
    assert "flat_plate_records" in excel_block
    assert "cylinder_records" in excel_block
    assert "row_data[" not in excel_block
    assert "self.new_point()" not in excel_block
    assert "this_line = self.new_line()" not in excel_block
    assert "ExcelInterface(" not in source
    assert "excel_inteface" not in source

    flat_import_block = excel_block[
        excel_block.index("# Flat"):
        excel_block.index("# Cylinders")
    ]
    assert "_new_plate_thk.set(" not in flat_import_block
    assert "_new_sigma_x1.set(" not in flat_import_block
    assert "_new_girder_web_h.set(" not in flat_import_block

    cylinder_import_block = excel_block[
        excel_block.index("# Cylinders"):
        excel_block.index("def button_load_info_click")
    ]
    assert "_new_shell_thk.set(" not in cylinder_import_block
    assert "_new_shell_radius.set(" not in cylinder_import_block
    assert "_new_shell_Nsd.set(" not in cylinder_import_block
    assert "_new_shell_end_cap_pressure_included.set(shell_yield)" not in cylinder_import_block


def test_csr_requirement_is_shared_by_numeric_and_semianalytical_methods():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")

    assert "use_semi_analytical_equation=False" in source
    assert "selected_buckling_method in ['ML-Numeric (PULS based)', 'SemiAnalytical S3/U3']" in source
    assert "use_semi_analytical_equation=selected_buckling_method == 'SemiAnalytical S3/U3'" in source
    assert "return_dict['ML buckling class'][current_line]['CSR'] = csr_values" in source
    assert "return_dict['ML buckling colors'][current_line]['CSR requirement'] = csr_color" in source


def test_semianalytical_csr_helper_uses_equation_predictor(monkeypatch):
    from anystruct import main_application
    from anystruct.main_application import Application

    calls = {}

    def fake_predict(calc_object, design_pressure):
        calls["plate"] = calc_object.Plate
        calls["stiffener"] = calc_object.Stiffener
        calls["design_pressure"] = design_pressure
        return [1, 0, 1, 1], "red", {"source": "equation"}

    monkeypatch.setattr(
        main_application.op.semi_analytical,
        "predict_anystructure_csr_requirement",
        fake_predict,
    )

    app = object.__new__(Application)
    plate = SimpleNamespace(mat_factor=1.15)
    stiffener = SimpleNamespace()

    csr, color = app._predict_csr_requirement(
        plate,
        stiffener,
        design_pressure=123.0,
        material_factor=1.15,
        use_semi_analytical_equation=True,
    )

    assert csr == [1, 0, 1, 1]
    assert color == "red"
    assert calls == {
        "plate": plate,
        "stiffener": stiffener,
        "design_pressure": 123.0,
    }


def test_support_boundary_inputs_are_limited_to_semianalytical_and_numeric_methods():
    main_source = Path(__file__).resolve().parents[1] / "anystruct" / "main_application.py"
    source = main_source.read_text(encoding="utf-8")
    layout_block = source[
        source.index("for buckling_lab, buckling_ent in zip(self._flat_gui_lab_buckling, self._flat_gui_buckling):"):
        source.index("# optimize buttons")
    ]
    method_trace_block = source[
        source.index("def trace_buckling_method"):
        source.index("def trace_puls_up_or_sp")
    ]
    trace_block = source[
        source.index("def trace_puls_up_or_sp"):
        source.index("def resize")
    ]

    assert "command=self.trace_buckling_method" in source
    assert "self.calculation_domain_selected(sync_cylinder_inputs=False)" in method_trace_block
    assert "self.update_frame(event)" in method_trace_block
    assert "self._flat_gui_lab_buckling, self._flat_gui_buckling" in layout_block
    assert "buckling_lab.place_forget()" in layout_block
    assert "buckling_ent.place_forget()" in layout_block
    assert "self._flat_gui_lab_buckling[:2]" in layout_block
    assert "self._flat_gui_buckling[:2]" in layout_block
    assert "if self._new_puls_sp_or_up.get() == 'UP':" in layout_block
    assert "self._lab_puls_up_supp.place(" in layout_block
    assert "self._new_buckling_method.get() in ['ML-Numeric (PULS based)', 'SemiAnalytical S3/U3']" in trace_block
    assert "self._lab_puls_up_supp.place_forget()" in trace_block
