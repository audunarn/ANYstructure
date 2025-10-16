"""Qt based entry point for the ANYstructure GUI.

This module replaces the previous Tkinter implementation with a
light‑weight PySide6 window.  The window focuses on demonstrating how the
existing calculation engine can be initialised by reusing the data that is
employed in ``anystruct/testCalc.py``.  The example is intentionally kept
compact so the wider port to Qt can evolve iteratively.
"""

from __future__ import annotations

import sys
from typing import Sequence

from PySide6.QtWidgets import QApplication

from .qt_application import DemoWindow


def main(args: Sequence[str] | None = None) -> int:
    """Launch the Qt demonstration window."""

    argv = list(sys.argv if args is None else [sys.argv[0], *args])
    app = QApplication(argv)
    window = DemoWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual execution only
    raise SystemExit(main())
