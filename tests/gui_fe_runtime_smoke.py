"""Automated live Tk smoke test for the ANYstructure FE popup."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox

os.environ.setdefault("ANYSTRUCTURE_FE_SOLVER_WARMUP", "0")

from anystruct import fem_integration


def main() -> None:
    messagebox.showerror = lambda *args, **kwargs: "ok"
    messagebox.showinfo = lambda *args, **kwargs: "ok"
    messagebox.showwarning = lambda *args, **kwargs: "ok"

    root = tk.Tk()
    root.geometry("1280x820+20+20")
    runtime_app = fem_integration.example_runtime_app()
    requested_backend = os.environ.get("ANYSTRUCTURE_VIEWER_BACKEND", "auto")
    runtime_app._renderer_requested = requested_backend
    window = fem_integration.RuntimeFEMWindow(
        root,
        runtime_app,
        use_parent_as_window=True,
    )
    root.update_idletasks()
    root.update()

    viewers = [
        getattr(window, attribute)
        for attribute, _parent, _populate, _fit in window._renderer_switch_specs()
    ]
    if not viewers:
        raise RuntimeError("Runtime FEM smoke did not create a shared 3D viewer")
    expected_backend = os.environ.get("ANYSTRUCTURE_EXPECT_BACKEND")
    active_backends = {
        str(getattr(viewer, "backend_name", "")).casefold() for viewer in viewers
    }
    if expected_backend and active_backends != {expected_backend.casefold()}:
        raise RuntimeError(
            f"expected {expected_backend!r} viewer, got {sorted(active_backends)!r}"
        )

    if str(window.body_panes.cget("orient")) != "horizontal":
        raise RuntimeError("FE body panes are not horizontally resizable")
    if int(window.body_panes.cget("sashwidth")) < 6:
        raise RuntimeError("FE body pane divider is too narrow")
    if int(window.body_panes.cget("sashpad")) < 2:
        raise RuntimeError("FE body pane divider hit area is too narrow")
    if str(window.body_panes.cget("sashrelief")) != "flat":
        raise RuntimeError("FE body pane divider does not use the flat visual style")
    if str(window.result_panes.cget("orient")) != "vertical":
        raise RuntimeError("FE result text/canvas panes are not vertically resizable")
    if int(window.result_panes.cget("sashwidth")) < 6:
        raise RuntimeError("FE result pane divider is too narrow")

    sash_x, sash_y = window.result_panes.sash_coord(0)
    pane_height = max(int(window.result_panes.winfo_height()), 1)
    target_y = min(max(int(pane_height * 0.45), 140), max(pane_height - 280, 140))
    if abs(target_y - sash_y) < 12:
        target_y = min(max(sash_y + 48, 140), max(pane_height - 280, 140))
    window.result_panes.sash_place(0, sash_x, target_y)
    root.update_idletasks()
    root.update()
    moved_y = window.result_panes.sash_coord(0)[1]
    if abs(moved_y - sash_y) < 5:
        raise RuntimeError("FE result text/canvas divider did not move vertically")

    print(
        "gui_fe_runtime_smoke: passed "
        f"(backend {','.join(sorted(active_backends))}; "
        f"vertical sash {sash_y}->{moved_y}, height {pane_height})",
        flush=True,
    )
    root.destroy()


if __name__ == "__main__":
    main()
