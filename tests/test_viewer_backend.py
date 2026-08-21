from __future__ import annotations

import math
import sys
from types import SimpleNamespace

import pytest

from anystruct import fem_integration, viewer_backend


class _ValueProbe:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _WindowProbe:
    def __init__(self):
        self.cancelled = []
        self.scheduled = []

    def after_cancel(self, identifier):
        self.cancelled.append(identifier)

    def after(self, interval, callback):
        self.scheduled.append((interval, callback))
        return "resumed-animation"


class _CanvasProbe:
    backend_name = "gpu"
    backend_diagnostics = ()
    viewport_size = (640, 480)
    bg = "white"
    is_playing_animation = False
    animation_frames = 0
    animation_frame_index = 0

    def __init__(self):
        self.stopped = 0
        self.forgotten = 0
        self.packed = 0
        self.destroyed = 0
        self.redrawn = 0

    def stop_animation(self):
        self.stopped += 1

    def pack_forget(self):
        self.forgotten += 1

    def pack(self, **_options):
        self.packed += 1

    def destroy(self):
        self.destroyed += 1

    def redraw(self):
        self.redrawn += 1


def _runtime_switch_probe(old_canvas, *, populate):
    runtime = fem_integration.RuntimeFEMWindow.__new__(
        fem_integration.RuntimeFEMWindow
    )
    runtime._renderer_switching = False
    runtime._renderer_requested = "software"
    runtime.renderer_backend_choice = _ValueProbe("GPU (ModernGL)")
    runtime.renderer_backend_status = _ValueProbe("")
    runtime.app = None
    runtime.window = _WindowProbe()
    runtime.result_canvas = old_canvas
    runtime.animation_fast_mode = _ValueProbe(False)
    runtime.animation_speed_multiplier = _ValueProbe(1.0)
    runtime.animation_interval_ms = _ValueProbe(80)
    runtime.result_case_labels = {
        "Time t=0 s": "time:0",
        "Time t=1 s": "time:1",
        "Time t=2 s": "time:2",
    }
    runtime.result_case_choice = _ValueProbe("Time t=1 s")
    runtime._animation_running = True
    runtime._animation_index = 2
    runtime._animation_cache_origin = 0
    runtime._animation_after_id = "old-animation"
    runtime._time_slider_syncing = False
    runtime._sync_time_slider = lambda index=None: None
    runtime._write_status = lambda *_args, **_kwargs: None
    runtime._bind_custom_load_canvas_selection = lambda _canvas: None
    runtime._renderer_switch_specs = lambda: [
        ("result_canvas", object(), populate, True)
    ]
    return runtime


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Automatic", "auto"),
        ("auto", "auto"),
        ("GPU (ModernGL)", "gpu"),
        ("gpu", "gpu"),
        ("Tk (software)", "software"),
        ("tk", "software"),
    ],
)
def test_normalize_backend_accepts_ui_and_factory_names(value, expected):
    assert viewer_backend.normalize_backend(value) == expected


def test_create_3d_viewer_lazily_forwards_backend(monkeypatch):
    calls = []

    def create(parent, *, backend, **options):
        calls.append((parent, backend, options))
        return "viewer"

    monkeypatch.setitem(sys.modules, "any3dview", SimpleNamespace(create_viewer=create))

    assert viewer_backend.create_3d_viewer("parent", backend="GPU", width=640) == "viewer"
    assert calls == [("parent", "gpu", {"width": 640})]


def test_event_widget_and_backend_diagnostics_are_backend_neutral():
    native = object()
    viewer = SimpleNamespace(
        event_widget=native,
        backend_name="gpu",
        backend_diagnostics=("driver note",),
    )

    assert viewer_backend.event_widget(viewer) is native
    assert viewer_backend.active_backend(viewer) == "gpu"
    assert viewer_backend.backend_diagnostic(viewer) == (
        "ModernGL GPU (fallback: driver note)"
    )


def test_state_helpers_degrade_for_older_software_viewers():
    viewer = SimpleNamespace(canvas="native")

    assert viewer_backend.event_widget(viewer) == "native"
    assert viewer_backend.export_view_state(viewer) is None
    assert viewer_backend.apply_view_state(viewer, object()) is None


def test_viewport_size_prefers_shared_contract_over_unmapped_native_widget():
    native = SimpleNamespace(winfo_width=lambda: 1, winfo_height=lambda: 1)
    viewer = SimpleNamespace(event_widget=native, viewport_size=(960, 540))

    assert viewer_backend.viewport_size(viewer) == (960, 540)


def test_apply_view_state_forwards_redraw_policy():
    calls = []
    viewer = SimpleNamespace(
        apply_view_state=lambda state, *, redraw=True: calls.append((state, redraw))
    )
    state = object()

    viewer_backend.apply_view_state(viewer, state, redraw=False)

    assert calls == [(state, False)]


def test_runtime_projection_fallback_uses_shared_viewport_size():
    point_type = fem_integration.Point3D
    camera = SimpleNamespace(
        position=point_type(0.0, 0.0, 0.0),
        fov=math.pi / 2.0,
        near=0.1,
        far=100.0,
        basis=lambda: (
            point_type(1.0, 0.0, 0.0),
            point_type(0.0, 1.0, 0.0),
            point_type(0.0, 0.0, 1.0),
        ),
    )
    canvas = SimpleNamespace(viewport_size=(400, 200), camera=camera)

    projected = fem_integration.RuntimeFEMWindow._project_custom_load_points(
        object(), canvas, [point_type(0.0, 0.0, 5.0)]
    )

    assert projected == pytest.approx([(200.0, 100.0, 5.0)])


def test_runtime_renderer_switch_resumes_animation_at_same_index(monkeypatch):
    old = _CanvasProbe()
    candidate = _CanvasProbe()
    runtime = _runtime_switch_probe(old, populate=lambda _candidate: None)
    monkeypatch.setattr(
        fem_integration, "create_3d_viewer", lambda *_args, **_kwargs: candidate
    )

    assert runtime._switch_renderer_backend(_application_coordinated=True)

    assert runtime.result_canvas is candidate
    assert old.stopped == 1
    assert old.destroyed == 1
    assert candidate.destroyed == 0
    assert runtime._animation_running
    assert runtime._animation_index == 2
    assert runtime.result_case_choice.get() == "Time t=1 s"
    assert runtime.window.cancelled == ["old-animation"]
    assert runtime.window.scheduled[0][0] == 80


def test_failed_runtime_renderer_switch_resumes_original_animation(monkeypatch):
    old = _CanvasProbe()
    candidate = _CanvasProbe()

    def fail_population(_candidate):
        raise RuntimeError("population failed")

    runtime = _runtime_switch_probe(old, populate=fail_population)
    monkeypatch.setattr(
        fem_integration, "create_3d_viewer", lambda *_args, **_kwargs: candidate
    )
    monkeypatch.setattr(fem_integration.messagebox, "showerror", lambda *_a, **_k: None)

    assert not runtime._switch_renderer_backend(_application_coordinated=True)

    assert runtime.result_canvas is old
    assert old.stopped == 1
    assert old.destroyed == 0
    assert candidate.destroyed == 1
    assert runtime._animation_running
    assert runtime._animation_index == 2
    assert runtime.result_case_choice.get() == "Time t=1 s"
    assert runtime.window.cancelled == ["old-animation"]
    assert runtime.window.scheduled[0][0] == 80


def test_fast_animation_switch_preserves_logical_cached_frame():
    old = _CanvasProbe()
    old.is_playing_animation = True
    old.animation_frames = 3
    old.animation_frame_index = 2
    runtime = _runtime_switch_probe(old, populate=lambda _candidate: None)
    runtime.animation_fast_mode.set(True)
    runtime._animation_cache_origin = 1
    resumed = []
    runtime._play_animation = lambda *, start_index=None: resumed.append(start_index)

    state = runtime._pause_animation_for_renderer_switch()

    assert state["current_index"] == 2
    assert state["next_index"] == 0
    assert runtime.result_case_choice.get() == "Time t=2 s"
    assert old.stopped == 1

    runtime._resume_animation_after_renderer_switch(state)

    assert resumed == [2]
    assert runtime._animation_index == 0
