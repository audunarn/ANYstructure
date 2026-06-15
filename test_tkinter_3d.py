#!/usr/bin/env python
"""
Test script for Tkinter 3D canvas module.
This script tests the core functionality without requiring a display.
"""

import sys
import math

# Mock tkinter for testing without display
class MockTk:
    def __init__(self):
        self.children = {}
        
    def pack(self, **kwargs):
        pass
        
    def create_rectangle(self, *args, **kwargs):
        return 1
        
    def create_line(self, *args, **kwargs):
        return 2
        
    def create_polygon(self, *args, **kwargs):
        return 3
        
    def delete(self, *args):
        pass
        
    def bind(self, *args):
        pass
        
    def after(self, *args):
        pass

class MockCanvas(MockTk):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.width = kwargs.get('width', 800)
        self.height = kwargs.get('height', 600)
        
    def get_tk_widget(self):
        return self

class MockTkinter:
    Tk = MockTk
    Canvas = MockCanvas
    Frame = MockTk
    Label = MockTk
    Button = MockTk
    Toplevel = MockTk
    
    class ttk:
        Button = MockTk
        Checkbutton = MockTk
        Label = MockTk

# Inject mock tkinter
sys.modules['tkinter'] = MockTkinter()
sys.modules['_tkinter'] = MockTkinter()

# Now import our module
from anystruct.tkinter_3d_canvas import Point3D, Camera3D, Tkinter3DCanvas

def test_point3d():
    """Test Point3D class."""
    print("Testing Point3D class...")
    
    # Test creation
    p1 = Point3D(1, 2, 3)
    assert p1.x == 1 and p1.y == 2 and p1.z == 3
    
    # Test operations
    p2 = Point3D(4, 5, 6)
    p3 = p1 + p2
    assert p3.x == 5 and p3.y == 7 and p3.z == 9
    
    p4 = p2 - p1
    assert p4.x == 3 and p4.y == 3 and p4.z == 3
    
    p5 = p1 * 2
    assert p5.x == 2 and p5.y == 4 and p5.z == 6
    
    p6 = p2 / 2
    assert p6.x == 2 and p6.y == 2.5 and p6.z == 3
    
    # Test length
    p7 = Point3D(3, 4, 0)
    assert abs(p7.length() - 5) < 1e-10
    
    # Test dot product
    p8 = Point3D(1, 0, 0)
    p9 = Point3D(0, 1, 0)
    assert p8.dot(p9) == 0
    
    # Test cross product
    p10 = Point3D(1, 0, 0)
    p11 = Point3D(0, 1, 0)
    p12 = p10.cross(p11)
    assert p12.x == 0 and p12.y == 0 and p12.z == 1
    
    # Test rotation
    p13 = Point3D(1, 0, 0)
    p14 = p13.rotate_y(math.pi / 2)
    assert abs(p14.x - 0) < 1e-10 and abs(p14.z - (-1)) < 1e-10
    
    print("✓ Point3D tests passed!")


def test_camera3d():
    """Test Camera3D class."""
    print("Testing Camera3D class...")
    
    # Test creation
    camera = Camera3D()
    assert camera.distance == 5.0
    assert abs(camera.azimuth - math.radians(-45)) < 1e-10
    assert abs(camera.elevation - math.radians(30)) < 1e-10
    
    # Test orbit
    camera.orbit(delta_azimuth=math.pi/4, delta_elevation=math.pi/6, delta_distance=1)
    assert camera.distance == 6.0
    
    # Test projection
    point = Point3D(0, 0, 0)
    projected = camera.project_point(point, 800, 600)
    assert projected is not None
    
    # Test with a point in front of camera
    point2 = Point3D(1, 1, 1)
    projected2 = camera.project_point(point2, 800, 600)
    assert projected2 is not None
    
    print("✓ Camera3D tests passed!")


def test_tkinter_3d_canvas():
    """Test Tkinter3DCanvas class (without actual drawing)."""
    print("Testing Tkinter3DCanvas class...")
    
    # Create a mock master
    master = MockTk()
    
    # Create canvas
    canvas_3d = Tkinter3DCanvas(master, width=800, height=600)
    
    # Test adding objects
    canvas_3d.add_line(Point3D(0, 0, 0), Point3D(1, 1, 1), color='red', width=2)
    assert len(canvas_3d.objects) == 1
    
    canvas_3d.add_cylinder(radius=1, height=2, center=Point3D(0, 0, 0))
    assert len(canvas_3d.objects) == 2
    
    canvas_3d.add_longitudinal_stiffener(
        radius=1, height=2, angle=0,
        web_height=0.1, web_thickness=0.01,
        flange_width=0.05, flange_thickness=0.01
    )
    assert len(canvas_3d.objects) == 3
    
    canvas_3d.add_ring_stiffener(
        radius=1, z_position=0,
        web_height=0.1, web_thickness=0.01,
        flange_width=0.05, flange_thickness=0.01
    )
    assert len(canvas_3d.objects) == 4
    
    # Test camera control
    canvas_3d.reset_camera()
    assert canvas_3d.camera.distance == 5.0
    
    print("✓ Tkinter3DCanvas tests passed!")


def test_stiffened_cylinder_creation():
    """Test the creation of a stiffened cylinder scene."""
    print("Testing stiffened cylinder creation...")
    
    master = MockTk()
    canvas_3d = Tkinter3DCanvas(master, width=1000, height=800)
    
    # Add cylinder
    cylinder_radius = 2.0
    cylinder_height = 4.0
    canvas_3d.add_cylinder(
        radius=cylinder_radius,
        height=cylinder_height,
        center=Point3D(0, 0, 0),
        color='#e0e0e0',
        outline='black',
        segments=64
    )
    
    # Add longitudinal stiffeners
    num_longitudinal = 8
    for i in range(num_longitudinal):
        angle = 2 * math.pi * i / num_longitudinal
        canvas_3d.add_longitudinal_stiffener(
            radius=cylinder_radius,
            height=cylinder_height,
            angle=angle,
            web_height=0.15,
            web_thickness=0.01,
            flange_width=0.1,
            flange_thickness=0.02,
            color='#a0a0ff',
            outline='black',
            segments=4
        )
    
    # Add ring stiffeners
    num_rings = 4
    for i in range(num_rings):
        z_position = -cylinder_height / 2 + (i + 1) * cylinder_height / (num_rings + 1)
        canvas_3d.add_ring_stiffener(
            radius=cylinder_radius,
            z_position=z_position,
            web_height=0.12,
            web_thickness=0.01,
            flange_width=0.08,
            flange_thickness=0.015,
            color='#ffa0a0',
            outline='black',
            segments=64
        )
    
    # Check that all objects were added
    assert len(canvas_3d.objects) == 1 + num_longitudinal + num_rings
    
    print("✓ Stiffened cylinder creation test passed!")
    print(f"  - Created 1 cylinder")
    print(f"  - Created {num_longitudinal} longitudinal stiffeners")
    print(f"  - Created {num_rings} ring stiffeners")
    print(f"  - Total objects: {len(canvas_3d.objects)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Tkinter 3D Canvas - Unit Tests")
    print("=" * 60)
    
    try:
        test_point3d()
        test_camera3d()
        test_tkinter_3d_canvas()
        test_stiffened_cylinder_creation()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nThe Tkinter 3D canvas module is working correctly.")
        print("To run the demo, execute:")
        print("  python anystruct/tkinter_3d_canvas.py")
        print("\nNote: This requires Tkinter to be installed and a display available.")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
