"""Routing tests for SESAM .FEM imports.

.FEM files carry geometry only (no stresses), so they must never be imported
for FEA-result buckling. When the geometry parses sufficiently the user is
offered the FE-solver (FE-GUI); otherwise an explanatory error is shown.
"""

from __future__ import annotations

import types

import anystruct.main_application as ma


class _StubMesh:
    def __init__(self, num_nodes, num_elements):
        self.num_nodes = num_nodes
        self.num_elements = num_elements


class _StubModel:
    def __init__(self, mesh):
        self.mesh = mesh


class _StubImportResult:
    def __init__(self, model):
        self.model = model


class _StubApp:
    """Minimal stand-in carrying only what the routed method touches."""

    def __init__(self):
        self._parent = None


def _make_app():
    app = _StubApp()
    app._launch_fe_solver_with_fem_geometry = types.MethodType(
        ma.Application._launch_fe_solver_with_fem_geometry, app
    )
    return app


class _Recorder:
    def __init__(self, askyesno_return=True):
        self.errors = []
        self.asked = []
        self.launched = []
        self._askyesno_return = askyesno_return

    def showerror(self, title, message, **kwargs):
        self.errors.append((title, message))

    def askyesno(self, title, message, **kwargs):
        self.asked.append((title, message))
        return self._askyesno_return


def _patch(monkeypatch, model, recorder):
    monkeypatch.setattr(
        "anystruct.api.import_sesam_fem_model",
        lambda path, **kwargs: _StubImportResult(model),
    )
    monkeypatch.setattr(ma, "messagebox", recorder, raising=False)
    monkeypatch.setattr(
        "anystruct.fem_integration.open_runtime_fem_window",
        lambda parent, app, imported_fem_model=None, imported_path=None: recorder.launched.append(
            (imported_fem_model, imported_path)
        ),
    )


def test_fem_geometry_offers_fe_solver_and_launches_on_yes(monkeypatch):
    model = _StubModel(_StubMesh(689, 852))
    recorder = _Recorder(askyesno_return=True)
    _patch(monkeypatch, model, recorder)

    app = _make_app()
    app._launch_fe_solver_with_fem_geometry("model.FEM")

    assert recorder.asked, "user should be asked whether to launch the FE-solver"
    assert "Launch FE-solver?" == recorder.asked[0][0]
    assert recorder.launched == [(model, "model.FEM")]
    assert not recorder.errors


def test_fem_geometry_does_not_launch_on_no(monkeypatch):
    model = _StubModel(_StubMesh(689, 852))
    recorder = _Recorder(askyesno_return=False)
    _patch(monkeypatch, model, recorder)

    app = _make_app()
    app._launch_fe_solver_with_fem_geometry("model.FEM")

    assert recorder.asked, "user should still be asked"
    assert recorder.launched == [], "declining must not launch the FE-solver"


def test_fem_geometry_insufficient_shows_error_and_does_not_ask(monkeypatch):
    # Empty mesh -> not parsed sufficiently.
    model = _StubModel(_StubMesh(0, 0))
    recorder = _Recorder(askyesno_return=True)
    _patch(monkeypatch, model, recorder)

    app = _make_app()
    app._launch_fe_solver_with_fem_geometry("broken.FEM")

    assert recorder.errors, "insufficient geometry should raise an explanatory error"
    assert not recorder.asked, "no launch prompt when geometry is insufficient"
    assert recorder.launched == []


def test_fem_geometry_missing_model_shows_error(monkeypatch):
    recorder = _Recorder(askyesno_return=True)
    _patch(monkeypatch, None, recorder)

    app = _make_app()
    app._launch_fe_solver_with_fem_geometry("empty.FEM")

    assert recorder.errors
    assert recorder.launched == []
