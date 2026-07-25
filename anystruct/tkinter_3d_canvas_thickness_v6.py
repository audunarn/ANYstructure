'''
Deprecated shim - the Tkinter 3D canvas now lives in the standalone
ANYtk3D package (anytk3d.canvas).

This module aliases the ANYtk3D canvas module so that every existing
import (public and private names alike) keeps working:

    import anystruct.tkinter_3d_canvas_thickness_v6 as tkinter_3d_canvas
'''
import sys as _sys

from anytk3d import canvas as _canvas

_sys.modules[__name__] = _canvas

if __name__ == "__main__":
    _canvas.main()
