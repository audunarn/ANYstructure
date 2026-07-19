from pathlib import Path

import anystruct.optimize_geometry as optimize_geometry


def test_span_optimizer_reads_pressure_side_from_line_structure_bundle():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    assert "def _line_overpressure_side(self, line):" in source
    assert "return self._line_structure(line).overpressure_side" in source
    assert "pressure_side = self._line_overpressure_side(closet_line)" in source
    assert "self._line_to_struc[closet_line][0].overpressure_side" not in source
    assert "self._line_to_struc[closet_line].overpressure_side" not in source


def test_span_optimizer_reads_predefined_sections_from_stiffener_component():
    optimize_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize.py"
    source = optimize_source.read_text(encoding="utf-8")

    assert "hlp.helper_read_section_file(predefiened_stiffener_iter, struc_obj.Stiffener)" in source
    assert "hlp.helper_read_section_file(predefiened_stiffener_iter, struc_obj)" not in source


def test_span_optimizer_uses_helpers_for_line_structure_bundle_access():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    assert "def _line_structure_bundle(self, line):" in source
    assert "def _line_structure(self, line):" in source
    assert "def _copy_line_structure_bundle(self, line):" in source
    assert "_line_to_struc[key][0]" not in source
    assert "_line_to_struc[line][0]" not in source
    assert "_line_to_struc[closet_line][0]" not in source


def test_span_optimizer_uses_imported_allstructure_type_in_result_drawing():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    assert "isinstance(stuc_info, AllStructure)" in source
    assert "calc_structure.AllStructure" not in source


def test_span_optimizer_non_axis_aligned_midpoint_uses_both_y_coordinates():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    assert "min(p2[1], p1[1]) + abs((p2[1] - p1[1]) * 0.5)" in source
    assert "min(p2[1] - p1[1])" not in source


def test_span_result_drawing_accepts_allstructure_instances(monkeypatch):
    class FakeCanvas:
        def __init__(self):
            self.texts = []

        def delete(self, *args, **kwargs):
            pass

        def create_text(self, *args, **kwargs):
            self.texts.append(kwargs.get("text", ""))

    class FakeAllStructure:
        def get_one_line_string_mixed(self):
            return "fake structure"

    monkeypatch.setattr(optimize_geometry, "AllStructure", FakeAllStructure)
    window = optimize_geometry.CreateOptGeoWindow.__new__(optimize_geometry.CreateOptGeoWindow)
    window._canvas_select = FakeCanvas()

    opt_results = {
        1: [
            123.4,
            [[FakeAllStructure(), None, True, True]],
            {"objects": [100.0], "frames": [23.4], "scales": [1.0]},
        ]
    }

    window.draw_select_canvas(opt_results=opt_results)

    assert any("fake structure" in text for text in window._canvas_select.texts)


def test_span_optimizer_weld_objective_wiring_is_explicit():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    assert "weld_bias=self._get_weld_bias_for_optimization()" in source
    assert "builtup_stiffener=self._new_include_builtup_weld.get()" in source
    assert "weld_metric=self._get_weld_metric_for_optimization()" in source
    assert "def _get_weld_metric_for_optimization(self):" in source
    assert "'Weld length'" in source
    assert "mixed weight/weld combination disables the initial filter" in source
    assert "Pure weld objective: span optimizer uses ' + self._get_weld_metric_text()" in source
    assert "Objective index" in source


def test_geometric_optimizer_forwards_process_count():
    optimize_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize.py"
    source = optimize_source.read_text(encoding="utf-8")

    assert "opt_girder_prop=opt_girder_prop, processes=processes, ml_algo=ml_algo" in source
    assert "processes=processes,\n                                                           ml_algo=ml_algo" in source


def test_geometric_optimizer_has_scipy_de_algorithm_option():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    assert "'scipy_de'" in source
    assert "algorithm=self._new_algorithm.get()" in source
    assert "trials=self._new_algorithm_random_trials.get()" in source
    assert "self.algorithm_random_label.config(text='Max evaluations')" in source
    assert "SCIPY_DE" in source


def test_geometric_optimizer_header_layout_keeps_objective_and_canvas_separate():
    optimize_geometry_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize_geometry.py"
    source = optimize_geometry_source.read_text(encoding="utf-8")

    # The gridded layout keeps the status labels, the objective block and the
    # canvases in separate rows/holders, so they cannot overlap by design.
    assert "self._running_time_info_label.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(6, 0))" in source
    assert "self._result_label.grid(row=4, column=4, columnspan=3, sticky=tk.W, pady=(6, 0))" in source
    assert "self._canvas_select.grid(row=0, column=0, sticky=tk.NW)" in source
    assert "self._canvas_opt.grid(row=0, column=0, sticky=tk.NW)" in source
    assert "self._objective_frame.grid(row=2, column=0, sticky=tk.NW, padx=10, pady=(6, 0))" in source
    assert "self._select_canvas_holder.grid(row=3, column=0, sticky=tk.NW, padx=10, pady=(8, 8))" in source
    assert "start_y + 5.0 * dy" not in source
    assert "obj_x, obj_y = 20, 175" not in source


def test_geometric_optimizer_routes_scipy_de_to_flat_sampler():
    optimize_source = Path(__file__).resolve().parents[1] / "anystruct" / "optimize.py"
    source = optimize_source.read_text(encoding="utf-8")

    assert "algorithm in ('anysmart', 'scipy_de') and is_geometric" in source
    assert "algorithm=algorithm, predefiened_stiffener_iter=predefined_stiffener_iter" in source
    assert "if algorithm == 'scipy_de':" in source
    assert "opt_obj = scipy_de_loop_flat(" in source
