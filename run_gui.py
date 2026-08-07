#!/usr/bin/env python
"""Run the ANYstructure desktop application from this checkout."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence


_ROOT = Path(__file__).resolve().parent
_SOURCE_TREES = (
    _ROOT.parent / "ANYsolver" / "src",
    _ROOT.parent / "ANYmaterial" / "src",
    _ROOT.parent / "ANYmesh" / "src",
    _ROOT.parent / "ANYio" / "src",
    _ROOT.parent / "ANYbuckling" / "src",
    _ROOT.parent / "ANYtk3D" / "src",
)
for _source in reversed(_SOURCE_TREES):
    if _source.is_dir() and str(_source) not in sys.path:
        sys.path.insert(0, str(_source))


def main(args: Sequence[str] | None = None) -> None:
    """Launch the GUI using the package's maintained entry point."""

    from anystruct.__main__ import main as gui_main

    gui_main(args)


if __name__ == "__main__":
    main()
