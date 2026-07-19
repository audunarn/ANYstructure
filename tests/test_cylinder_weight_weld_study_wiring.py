from pathlib import Path


def read_optimize_cylinder_source():
    return (Path(__file__).resolve().parents[1] / "anystruct" / "optimize_cylinder.py").read_text(
        encoding="utf-8"
    )


def test_cylinder_optimizer_has_weight_weld_study_button():
    source = read_optimize_cylinder_source()

    assert "text='weight/weld study'" in source
    assert "command=self.run_weight_weld_study" in source
    assert "def run_weight_weld_study(self):" in source
    assert "self._new_weld_study_delta" in source
    assert "self._new_weld_study_delta.set(0.1)" in source
    assert "self._ent_weld_study_delta" in source
    assert "text='show previous study'" in source
    assert "command=self.show_previous_weight_weld_study" in source
    assert "def show_previous_weight_weld_study(self):" in source
    assert "self._last_weight_weld_study_rows" in source


def test_cylinder_weight_weld_study_shows_table_and_plot():
    source = read_optimize_cylinder_source()

    assert "ttk.Treeview" in source
    assert "FigureCanvasTkAgg" in source
    assert "Cylinder weight/weld study" in source


def test_cylinder_weight_weld_study_uses_delta_input():
    source = read_optimize_cylinder_source()

    assert "delta = float(self._new_weld_study_delta.get())" in source
    assert "Weight/weld study delta must be larger than 0" in source


def test_cylinder_running_time_warns_for_weight_weld_combination():
    source = read_optimize_cylinder_source()

    assert "mixed weight/weld combination disables the initial filter" in source
    assert "Estimate uses no-filter runtime" in source
    assert "self.running_time_no_filter_factor" in source
    assert "Pure weld objective: initial filter uses ' + self._get_weld_metric_text()" in source


def test_cylinder_optimizer_layout_reserves_space_for_runtime_warning():
    source = read_optimize_cylinder_source()

    # The gridded layout structurally reserves space: the runtime warning has
    # its own objective-frame row and the canvas its own holder frame, so they
    # can never overlap regardless of text length.
    assert "self._canvas_dim = (550, 490)" in source
    assert "self._canvas_opt.grid(row=0, column=0, sticky=tk.NW)" in source
    assert "self._runnig_time_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(8, 0))" in source
    assert "self._result_label.grid(row=1, column=0, sticky=tk.W, pady=(4, 0))" in source


def test_cylinder_optimizer_has_weld_metric_selector():
    source = read_optimize_cylinder_source()

    assert "self._new_weld_metric" in source
    assert "'Weld consumables'" in source
    assert "'Weld length'" in source
    assert "def _get_weld_metric_for_optimization(self):" in source
    assert "weld_metric=self._get_weld_metric_for_optimization()" in source
    assert "op.calc_weld_objective_cylinder(" in source


def test_cylinder_optimizer_has_cost_study_button_and_dialog():
    source = read_optimize_cylinder_source()

    assert "text='cost study'" in source
    assert "command=self.open_cost_study_window" in source
    assert "def open_cost_study_window(self):" in source
    assert "Steel cost per kg" in source
    assert "'Weld cost per ' + self._get_weld_metric_unit()" in source
    assert "def run_cost_study(self, cost_factors):" in source
    assert "cost_factors=cost_factors" in source
    assert "Cost optimization result" in source
    assert "def _build_cost_study_report(self, cost_factors" in source
    assert "def _show_cost_study_report(self, report):" in source
    assert "Cylinder cost optimization report" in source
    assert "Steel contribution" in source
    assert "Weld contribution" in source
    assert "Optimized geometry" in source
    assert "Optimization field size" in source
    assert "Cylinder radius used [m]" in source
    assert "Distance between rings used [mm]" in source
    assert "Total cylinder length used [mm]" in source
    assert "Design lateral pressure used [Pa]" in source
    assert "self._last_cost_study_report = report" in source
    assert "self._last_study_type = 'cost'" in source
    assert "self._show_cost_study_report(self._last_cost_study_report)" in source


def test_cylinder_optimizer_has_scipy_de_algorithm_option():
    source = read_optimize_cylinder_source()

    assert "'scipy_de cylinder'" in source
    assert "self.algorithm_random_label.config(text='Max evaluations')" in source
    assert "SCIPY_DE CYLINDER" in source
    assert "def _get_optimizer_count_label(self):" in source
    assert "Estimated max evaluations" in source
