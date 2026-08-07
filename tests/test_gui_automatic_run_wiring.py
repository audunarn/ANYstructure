from pathlib import Path


def test_gui_automatic_run_resolves_ml_files_without_github_path():
    gui_source = Path(__file__).resolve().parent / "gui_automatic_run.py"
    source = gui_source.read_text(encoding="utf-8")

    assert "ANYSTRUCTURE_ML_FILES" in source
    assert r"C:\python_projects\ANYstructure\anystruct\ml_files" in source
    assert "REPO_ROOT / \"anystruct\" / \"ml_files\"" in source
    assert "ml_models.load_buckling_models(get_ml_file_directories())" in source
    assert r"C:\Github\ANYstructure" not in source


def test_gui_automatic_run_patches_dialogs_for_unattended_execution():
    gui_source = Path(__file__).resolve().parent / "gui_automatic_run.py"
    source = gui_source.read_text(encoding="utf-8")

    assert "configure_noninteractive_dialogs()" in source
    assert "messagebox.askquestion = lambda *args, **kwargs: \"no\"" in source
    assert "messagebox.showwarning = lambda *args, **kwargs: \"ok\"" in source
    assert (
        'main_application.Application._show_startup_calculation_mode_dialog = lambda _self: "multiple"'
        in source
    )
    assert "root.destroy()" in source


def test_gui_automatic_run_suppresses_plot_windows():
    gui_source = Path(__file__).resolve().parent / "gui_automatic_run.py"
    source = gui_source.read_text(encoding="utf-8")

    assert "configure_noninteractive_plots()" in source
    assert "plt.show = lambda *args, **kwargs: None" in source
    assert "plt.close(\"all\")" in source


def test_gui_automatic_run_exercises_optimizer_windows_noninteractively():
    gui_source = Path(__file__).resolve().parent / "gui_automatic_run.py"
    source = gui_source.read_text(encoding="utf-8")

    assert "def assert_window_opens(action, name):" in source
    assert "def close_child_windows():" in source
    assert "def exercise_optimizer_windows():" in source
    assert "my_app.on_optimize" in source
    assert "my_app.on_optimize_cylinder" in source
    assert "my_app.on_optimize_multiple" in source
    assert "my_app.on_geometry_optimize" in source
    assert "make_smoke_cylinder()" in source
    assert "exercise_optimizer_windows()" in source


def test_gui_automatic_run_opens_fixture_project_noninteractively():
    gui_source = Path(__file__).resolve().parent / "gui_automatic_run.py"
    source = gui_source.read_text(encoding="utf-8")

    assert "my_app.open_example()" in source
    assert 'checkpoint("example project opened")' in source
