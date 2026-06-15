# Tkinter 3D Canvas Implementation

This document describes the new Tkinter-based 3D drawing implementation for ANYstructure, providing an alternative to matplotlib 3D drawing.

## Overview

A pure Tkinter implementation for 3D visualization has been created, specifically designed for visualizing stiffened cylinders and other structural elements without requiring external dependencies like matplotlib.

## Files Created

1. **`anystruct/tkinter_3d_canvas.py`** - Main implementation using numpy for matrix operations (faster)
2. **`anystruct/tkinter_3d_canvas_simple.py`** - Pure Python implementation without numpy dependency
3. **`test_tkinter_3d.py`** - Unit tests for the implementation

## Features

### Core Classes

- **`Point3D`**: Represents 3D points with vector operations (addition, subtraction, multiplication, division, dot product, cross product, normalization, rotation)

- **`Camera3D`**: Manages 3D camera with:
  - Position, target, and up vector
  - Field of view and clipping planes
  - Orbit controls (azimuth, elevation, distance)
  - Perspective projection
  - View matrix calculations

- **`Tkinter3DCanvas`**: Main canvas widget supporting:
  - 3D line drawing
  - 3D polygon drawing
  - 3D cylinder drawing
  - Longitudinal stiffener drawing
  - Ring stiffener drawing
  - Mouse interaction (rotation and zoom)
  - Camera controls

### Drawing Primitives

- **Lines**: Simple 3D line segments
- **Polygons**: 3D polygons with optional outlines
- **Cylinders**: Complete cylinders with configurable segments, colors, and outlines
- **Longitudinal Stiffeners**: Radial stiffeners with web and flange
- **Ring Stiffeners**: Annular stiffeners with web and flange

### Mouse Controls

- **Left-click and drag**: Rotate the camera around the target
- **Scroll wheel**: Zoom in/out
- **Reset View button**: Return to default camera position
- **Top/Side/Iso View buttons**: Predefined view angles

## Usage Example

```python
import tkinter as tk
from anystruct.tkinter_3d_canvas_simple import Point3D, Tkinter3DCanvas

# Create main window
root = tk.Tk()

# Create 3D canvas
canvas_3d = Tkinter3DCanvas(root, width=800, height=600)
canvas_3d.pack(fill=tk.BOTH, expand=True)

# Add a cylinder
canvas_3d.add_cylinder(
    radius=2.0,
    height=4.0,
    center=Point3D(0, 0, 0),
    color='#e0e0e0',
    outline='black',
    segments=64
)

# Add longitudinal stiffeners
for i in range(8):
    angle = 2 * math.pi * i / 8
    canvas_3d.add_longitudinal_stiffener(
        radius=2.0,
        height=4.0,
        angle=angle,
        web_height=0.15,
        web_thickness=0.01,
        flange_width=0.1,
        flange_thickness=0.02,
        color='#a0a0ff'
    )

# Add ring stiffeners
for i in range(4):
    z_position = -2.0 + (i + 1) * 4.0 / 5
    canvas_3d.add_ring_stiffener(
        radius=2.0,
        z_position=z_position,
        web_height=0.12,
        web_thickness=0.01,
        flange_width=0.08,
        flange_thickness=0.015,
        color='#ffa0a0'
    )

root.mainloop()
```

## Running the Demo

To see a complete stiffened cylinder demo:

```bash
python anystruct/tkinter_3d_canvas_simple.py
```

This will display:
- A cylinder with radius 2.0 and height 4.0
- 8 longitudinal stiffeners (blue)
- 4 ring stiffeners (red)
- Interactive controls for rotation and zoom

## Technical Details

### Projection Pipeline

1. **World to Camera Coordinates**: Uses a view matrix based on camera position, target, and up vector
2. **Perspective Projection**: Applies a projection matrix based on field of view and aspect ratio
3. **Perspective Divide**: Converts from clip coordinates to normalized device coordinates (NDC)
4. **Screen Mapping**: Converts NDC to screen pixel coordinates

### Performance Considerations

- The implementation uses triangle decomposition for all 3D objects
- Cylinders are divided into segments (default 32) for smooth appearance
- Stiffeners are drawn as combinations of polygons
- For better performance with numpy, use `tkinter_3d_canvas.py`
- For environments without numpy, use `tkinter_3d_canvas_simple.py`

### Limitations

- No hidden surface removal (objects are drawn in order)
- No lighting/shading (flat colors only)
- No texture mapping
- Alpha transparency is limited (Tkinter doesn't support alpha blending natively)

## Integration with ANYstructure

The implementation can be integrated with the existing ANYstructure code by:

1. Importing the module in `main_application.py`
2. Replacing matplotlib 3D drawing calls with Tkinter 3D canvas calls
3. Using the same geometry data (radius, height, stiffener dimensions)

Example integration:

```python
# In main_application.py
from anystruct.tkinter_3d_canvas_simple import Tkinter3DCanvas, Point3D

# Replace matplotlib figure with Tkinter canvas
self._prop_3d_canvas = Tkinter3DCanvas(self._prop_3d_frame, width=800, height=600)

# Draw cylinder
self._prop_3d_canvas.add_cylinder(
    radius=shell.radius,
    height=shell.length_of_shell,
    center=Point3D(0, 0, 0)
)

# Draw stiffeners
for stiffener in longitudinal_stiffeners:
    self._prop_3d_canvas.add_longitudinal_stiffener(
        radius=shell.radius,
        height=shell.length_of_shell,
        angle=stiffener.angle,
        web_height=stiffener.web_h,
        web_thickness=stiffener.web_thk,
        flange_width=stiffener.fl_w,
        flange_thickness=stiffener.fl_thk
    )
```

## Future Enhancements

Possible improvements for future development:

1. **Hidden Surface Removal**: Implement a simple painter's algorithm or z-buffer
2. **Lighting**: Add basic lighting calculations for shading
3. **Wireframe Mode**: Option to display only edges
4. **Selection**: Ability to select and highlight specific elements
5. **Export**: Export 3D scene to OBJ or other formats
6. **Performance**: Optimize drawing for large numbers of elements

## Dependencies

- **tkinter_3d_canvas.py**: Requires numpy
- **tkinter_3d_canvas_simple.py**: No external dependencies (pure Python)
- Both require: Python 3.x, Tkinter

## License

This code is part of the ANYstructure project and follows the same licensing terms.
