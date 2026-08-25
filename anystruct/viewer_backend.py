"""Backend-neutral construction helpers for ANYstructure 3D viewers.

The historic :mod:`anystruct.tkinter_3d_canvas_thickness_v6` module remains a
literal ANYtk3D compatibility alias.  New application code comes through this
module so a running desktop can choose the ModernGL or software renderer
without teaching the structural model about either implementation.
"""

from __future__ import annotations

from typing import Any


BACKEND_LABELS = {
    "Automatic": "auto",
    "GPU (ModernGL)": "gpu",
    "Tk (software)": "software",
}
BACKEND_NAMES = {value: label for label, value in BACKEND_LABELS.items()}


def normalize_backend(value: object) -> str:
    """Return the factory value for a UI label or backend identifier."""

    rendered = str(value or "auto").strip()
    if rendered in BACKEND_LABELS:
        return BACKEND_LABELS[rendered]
    lowered = rendered.casefold()
    aliases = {
        "automatic": "auto",
        "auto": "auto",
        "gpu": "gpu",
        "gpu (moderngl)": "gpu",
        "tk": "software",
        "software": "software",
        "tk (software)": "software",
    }
    try:
        return aliases[lowered]
    except KeyError as error:
        raise ValueError("renderer must be Automatic, GPU, or Tk") from error


def create_3d_viewer(
    parent: object,
    *,
    backend: object = "auto",
    **options: Any,
) -> object:
    """Lazily construct an ANY3dView backend.

    Keeping this import inside the function preserves import-time behaviour
    for documentation tools and headless engineering workflows.
    """

    from any3dview import create_viewer

    return create_viewer(parent, backend=normalize_backend(backend), **options)


def event_widget(viewer: object) -> object:
    """Return the native widget used for pointer/key bindings."""

    native = getattr(viewer, "event_widget", None)
    return native if native is not None else getattr(viewer, "canvas", viewer)


def viewport_size(
    viewer: object,
    default: tuple[int, int] = (800, 600),
) -> tuple[int, int]:
    """Return the shared drawable size, with compatibility fallbacks."""

    size = getattr(viewer, "viewport_size", None)
    if callable(size):
        size = size()
    candidates = (
        size,
        (getattr(viewer, "width", None), getattr(viewer, "height", None)),
    )
    for candidate in candidates:
        try:
            width, height = candidate
            return max(1, int(width)), max(1, int(height))
        except (TypeError, ValueError):
            pass
    native = event_widget(viewer)
    try:
        return (
            max(1, int(native.winfo_width())),
            max(1, int(native.winfo_height())),
        )
    except Exception:
        return max(1, int(default[0])), max(1, int(default[1]))


def active_backend(viewer: object) -> str:
    """Return ``gpu`` or ``software`` for a live viewer."""

    name = str(getattr(viewer, "backend_name", "")).casefold()
    if name in {"gpu", "software"}:
        return name
    capabilities = getattr(viewer, "capabilities", None)
    return "gpu" if bool(getattr(capabilities, "gpu", False)) else "software"


def export_view_state(viewer: object) -> object | None:
    exporter = getattr(viewer, "export_view_state", None)
    if callable(exporter):
        return exporter()
    return None


def apply_view_state(
    viewer: object,
    state: object | None,
    *,
    redraw: bool = True,
) -> None:
    if state is None:
        return
    importer = getattr(viewer, "apply_view_state", None)
    if callable(importer):
        importer(state, redraw=redraw)


def backend_diagnostic(viewer: object) -> str:
    """Human-readable actual backend and automatic-fallback diagnostics."""

    actual = "ModernGL GPU" if active_backend(viewer) == "gpu" else "Tk software"
    diagnostics = "; ".join(
        str(value) for value in getattr(viewer, "backend_diagnostics", ()) if value
    )
    return actual + (f" (fallback: {diagnostics})" if diagnostics else "")


__all__ = [
    "BACKEND_LABELS",
    "BACKEND_NAMES",
    "active_backend",
    "apply_view_state",
    "backend_diagnostic",
    "create_3d_viewer",
    "event_widget",
    "export_view_state",
    "normalize_backend",
    "viewport_size",
]
