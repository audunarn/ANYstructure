'''
The FE window's Visualization tab exposes the 3D canvas display options.

These guard the wiring rather than the look: every control must have help
text, must reach every open canvas through the one shared apply helper, and
must map onto an ANYtk3D method that actually exists with that signature.
'''
import ast
import inspect
import pathlib

import pytest

from anystruct import fem_integration as fe
from anystruct import tkinter_3d_canvas_thickness_v6 as tk3d


VIEW_OPTION_KEYS = (
    "shading",
    "light_azimuth",
    "light_elevation",
    "light_ambient",
    "light_specular",
    "light_follow_camera",
    "show_axis_indicator",
    "occlude_lines",
    "interactive_detail",
    "animation_detail",
)

VIEW_OPTION_VARIABLES = (
    "shading_vis",
    "light_azimuth_vis",
    "light_elevation_vis",
    "light_ambient_vis",
    "light_specular_vis",
    "light_follow_camera_vis",
    "show_axis_indicator_vis",
    "occlude_lines_vis",
    "interactive_detail_vis",
    "animation_detail_vis",
)


@pytest.fixture(scope="module")
def source():
    return pathlib.Path(fe.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("key", VIEW_OPTION_KEYS)
def test_every_view_option_has_help_text(key):
    info = fe.FEM_OPTION_INFO.get(key)
    assert info, f"no help entry for {key!r}"
    for field in ("title", "purpose", "use", "output", "caution"):
        assert info.get(field), f"{key!r} help is missing {field!r}"


@pytest.mark.parametrize("name", VIEW_OPTION_VARIABLES)
def test_every_view_option_has_a_variable(name, source):
    assert f"self.{name} = tk." in source


@pytest.mark.parametrize("key", VIEW_OPTION_KEYS)
def test_every_view_option_is_placed_in_the_tab(key, source):
    assert f'"{key}"' in source, f"{key!r} is never added to a tab"


def test_canvas_options_go_through_one_apply_helper(source):
    # Nothing may configure a canvas display option directly; that is how the
    # result view, geometry preview and mesh preview drift apart.
    tree = ast.parse(source)
    direct = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in (
            "set_mesh_lines", "set_axis_ruler", "set_axis_indicator",
            "set_shading", "set_light", "set_occlude_lines", "set_interactive_detail",
        ):
            continue
        receiver = node.func.value
        name = receiver.id if isinstance(receiver, ast.Name) else getattr(receiver, "attr", "")
        if "canvas" in name.lower() or "tk3d" in name.lower():
            direct.append(f"line {node.lineno}: {name}.{node.func.attr}")
    assert not direct, "configure canvases via _apply_canvas_view_options: " + "; ".join(direct)


def test_apply_helper_targets_every_canvas(source):
    helper = source[source.index("def _canvas_view_targets"):source.index("def _apply_canvas_view_options")]
    for attribute in ("result_canvas", "geometry_preview_canvas", "mesh_preview_canvas"):
        assert attribute in helper


def _method_node(source, name):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def test_apply_helper_only_calls_real_canvas_methods(source):
    called = {
        node.args[0].value
        for node in ast.walk(_method_node(source, "_apply_canvas_view_options"))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "call"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert called, "the helper stopped using the guarded call() wrapper"
    for name in called:
        assert callable(getattr(tk3d.Tkinter3DCanvas, name, None)), f"canvas has no {name}()"
    # Every option variable the tab offers must actually be read here.
    read = {
        node.attr
        for node in ast.walk(_method_node(source, "_apply_canvas_view_options"))
        if isinstance(node, ast.Attribute)
    }
    for variable in VIEW_OPTION_VARIABLES:
        if variable == "animation_detail_vis":
            continue  # read at playback time, not when applying view options
        assert variable in read, f"_apply_canvas_view_options ignores {variable}"


def test_playback_detail_maps_onto_the_canvas_argument():
    window = fe.RuntimeFEMWindow.__new__(fe.RuntimeFEMWindow)
    signature = inspect.signature(tk3d.Tkinter3DCanvas.play_animation)
    assert "fast" in signature.parameters

    class _Choice:
        def __init__(self, value):
            self._value = value

        def get(self):
            return self._value

    for choice, expected in (("auto", None), ("full", False), ("fast", True), ("nonsense", None)):
        window.animation_detail_vis = _Choice(choice)
        assert fe.RuntimeFEMWindow._animation_playback_detail(window) is expected


def test_alpha_reaches_the_canvas_as_an_opacity(source):
    # Tk's four built-in stipples used to quantise the alpha entries; the
    # canvas now resolves an opacity itself, so the setting is proportional.
    assert "_alpha_to_stipple" not in source
    assert "opacity=plate_alpha" in source
    assert "opacity=member_alpha" in source
    assert "opacity" in inspect.signature(tk3d.Tkinter3DCanvas.add_faces).parameters
    for name in ("add_rectangular_plate", "add_flat_stiffener", "add_flat_girder"):
        method = getattr(tk3d.Tkinter3DCanvas, name)
        assert "opacity" in inspect.signature(method).parameters, name


def test_reset_restores_the_shipped_lighting(source):
    assigned = {
        node.attr
        for node in ast.walk(_method_node(source, "_reset_lighting_defaults"))
        if isinstance(node, ast.Attribute)
    }
    for name in VIEW_OPTION_VARIABLES:
        if name == "animation_detail_vis":
            continue
        assert name in assigned, f"reset does not restore {name}"


# ----------------------------------------------------------------------
# Colormap selection
# ----------------------------------------------------------------------

#: The values offered by the Visualization tab's colormap option menu.
COLORMAP_CHOICES = ("jet", "viridis", "plasma", "inferno", "coolwarm", "greys")


@pytest.fixture
def restored_colormap():
    reset = getattr(tk3d, "reset_color_stops", None)
    yield
    if callable(reset):
        reset()


def _scale_sample():
    return tuple(
        fe._interpolate_thickness_color(value, 0.0, 1.0)
        for value in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    )


def test_colormap_option_menu_offers_the_expected_names(source):
    assert str(COLORMAP_CHOICES) in source or all(
        f'"{name}"' in source for name in COLORMAP_CHOICES
    )


def test_every_colormap_choice_produces_a_distinct_scale(restored_colormap):
    # The scale is shared module state, so selecting a map has to actually
    # reach the interpolation the canvas and the legend both call.
    seen = {}
    for name in COLORMAP_CHOICES:
        fe._configure_tk_canvas_colormap(name)
        sample = _scale_sample()
        assert sample not in seen, f"{name!r} renders the same as {seen.get(sample)!r}"
        seen[sample] = name
    assert len(seen) == len(COLORMAP_CHOICES)


def test_colormap_lookup_ignores_case(restored_colormap):
    # Matplotlib names `Greys` with a capital G; the menu offers "greys".
    fe._configure_tk_canvas_colormap("greys")
    lowercase = _scale_sample()
    fe._configure_tk_canvas_colormap("Greys")
    assert _scale_sample() == lowercase

    fe._configure_tk_canvas_colormap("jet")
    assert _scale_sample() != lowercase


def test_unknown_colormap_falls_back_to_jet(restored_colormap):
    fe._configure_tk_canvas_colormap("jet")
    jet = _scale_sample()
    fe._configure_tk_canvas_colormap("no-such-colormap")
    assert _scale_sample() == jet


def test_colormap_reaches_the_canvas_through_its_public_api(restored_colormap):
    # Patching a private module constant is what silently stopped working
    # when the interpolation moved between modules.
    assert callable(getattr(tk3d, "set_color_stops", None))
    assert callable(getattr(tk3d, "get_color_stops", None))

    fe._configure_tk_canvas_colormap("viridis")
    stops = tk3d.get_color_stops()
    assert len(stops) >= 2
    assert stops[0][1].lower() == "#440154"  # viridis starts dark purple


def test_colormap_is_sampled_densely_enough_to_be_smooth():
    assert fe._CANVAS_COLORMAP_SAMPLES >= 9
