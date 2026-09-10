"""Runtime adjustments needed only by the frozen ANYstructure application."""

from __future__ import annotations

import sys


if getattr(sys, "frozen", False):
    # Numba's file-backed cache cannot locate source files inside a PyInstaller
    # bundle.  Keep JIT compilation enabled, but disable its persistent cache.
    import numba
    from numba.core import decorators

    _original_jit = decorators.jit

    def _frozen_jit(*args, **kwargs):
        kwargs["cache"] = False
        return _original_jit(*args, **kwargs)

    decorators.jit = _frozen_jit
    numba.jit = _frozen_jit
