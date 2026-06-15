"""
Tkinter 3D Canvas - Pure Tkinter implementation for 3D drawing.

This module provides a Tkinter-only alternative to matplotlib 3D drawing,
specifically designed for visualizing stiffened cylinders and other
structural elements without external dependencies.

Author: Vibe Code
Date: 2024
"""

import tkinter as tk
import math
import numpy as np
from typing import List, Tuple, Optional, Dict, Any


class Point3D:
    """Represents a 3D point with x, y, z coordinates."""
    
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def __add__(self, other):
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float):
        return Point3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __truediv__(self, scalar: float):
        return Point3D(self.x / scalar, self.y / scalar, self.z / scalar)
    
    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalized(self):
        length = self.length()
        if length == 0:
            return Point3D(0, 0, 0)
        return self / length
    
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other):
        return Point3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def rotate_x(self, angle: float):
        """Rotate point around x-axis by angle (in radians)."""
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return Point3D(
            self.x,
            self.y * cos_a - self.z * sin_a,
            self.y * sin_a + self.z * cos_a
        )
    
    def rotate_y(self, angle: float):
        """Rotate point around y-axis by angle (in radians)."""
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return Point3D(
            self.x * cos_a + self.z * sin_a,
            self.y,
            -self.x * sin_a + self.z * cos_a
        )
    
    def rotate_z(self, angle: float):
        """Rotate point around z-axis by angle (in radians)."""
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return Point3D(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a,
            self.z
        )


class Camera3D:
    """Represents a 3D camera with position, target, and projection parameters."""
    
    def __init__(self):
        self.position = Point3D(0, 0, 5)  # Camera position
        self.target = Point3D(0, 0, 0)    # Look-at target
        self.up = Point3D(0, 1, 0)        # Up vector
        self.fov = math.radians(60)      # Field of view in radians
        self.near = 0.1                   # Near clipping plane
        self.far = 100.0                  # Far clipping plane
        
        # Rotation angles for orbit control
        self.azimuth = math.radians(-45)  # Rotation around y-axis
        self.elevation = math.radians(30) # Rotation around x-axis
        self.distance = 5.0               # Distance from target
        
        self._update_view_matrix()
    
    def _update_view_matrix(self):
        """Update the view matrix based on current parameters."""
        # Calculate camera position using spherical coordinates
        self.position = Point3D(
            self.distance * math.cos(self.elevation) * math.cos(self.azimuth),
            self.distance * math.sin(self.elevation),
            self.distance * math.cos(self.elevation) * math.sin(self.azimuth)
        )
    
    def orbit(self, delta_azimuth: float = 0, delta_elevation: float = 0, delta_distance: float = 0):
        """Orbit the camera around the target."""
        self.azimuth += delta_azimuth
        self.elevation += delta_elevation
        self.distance = max(0.1, self.distance + delta_distance)
        self._update_view_matrix()
    
    def get_view_matrix(self) -> np.ndarray:
        """Get the view matrix for transforming world coordinates to camera coordinates."""
        # Forward vector
        forward = (self.target - self.position).normalized()
        
        # Right vector (cross product of forward and up)
        right = forward.cross(self.up).normalized()
        
        # Recalculate up vector to ensure orthogonality
        new_up = right.cross(forward).normalized()
        
        # Create view matrix
        view_matrix = np.array([
            [right.x, right.y, right.z, -right.dot(self.position)],
            [new_up.x, new_up.y, new_up.z, -new_up.dot(self.position)],
            [-forward.x, -forward.y, -forward.z, forward.dot(self.position)],
            [0, 0, 0, 1]
        ])
        
        return view_matrix
    
    def get_projection_matrix(self, width: int, height: int) -> np.ndarray:
        """Get the projection matrix for perspective projection."""
        aspect = width / height
        f = 1.0 / math.tan(self.fov / 2)
        
        projection_matrix = np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (self.far + self.near) / (self.near - self.far), -1],
            [0, 0, (2 * self.far * self.near) / (self.near - self.far), 0]
        ])
        
        return projection_matrix
    
    def project_point(self, point: Point3D, width: int, height: int) -> Optional[Tuple[float, float]]:
        """Project a 3D point to 2D screen coordinates."""
        # World to camera coordinates
        view_matrix = self.get_view_matrix()
        camera_coords = np.dot(view_matrix, np.array([point.x, point.y, point.z, 1]))
        
        # Check if point is behind camera
        if camera_coords[2] <= self.near:
            return None
        
        # Perspective projection
        projection_matrix = self.get_projection_matrix(width, height)
        clip_coords = np.dot(projection_matrix, camera_coords)
        
        # Perspective divide
        if clip_coords[3] == 0:
            return None
        
        ndc_coords = clip_coords[:3] / clip_coords[3]
        
        # Convert from NDC to screen coordinates
        screen_x = (ndc_coords[0] + 1) * width / 2
        screen_y = (1 - ndc_coords[1]) * height / 2
        
        return (screen_x, screen_y)


class Tkinter3DCanvas(tk.Frame):
    """A Tkinter canvas that supports 3D drawing primitives."""
    
    def __init__(self, master: tk.Widget, width: int = 800, height: int = 600,
                 bg: str = 'white', **kwargs):
        """
        Initialize the 3D canvas.
        
        Args:
            master: Parent Tkinter widget
            width: Canvas width in pixels
            height: Canvas height in pixels
            bg: Background color
            **kwargs: Additional canvas arguments
        """
        super().__init__(master)
        self.master = master
        self.width = width
        self.height = height
        self.bg = bg
        
        # Create the canvas
        self.canvas = tk.Canvas(self, width=width, height=height, bg=bg, **kwargs)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Camera
        self.camera = Camera3D()
        
        # Store drawn objects for redrawing
        self.objects: List[Dict[str, Any]] = []
        
        # Mouse interaction state
        self._last_mouse_x = 0
        self._last_mouse_y = 0
        self._is_dragging = False
        
        # Bind mouse events
        self.canvas.bind('<Button-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<Button-4>', self._on_mouse_wheel)  # Linux scroll up
        self.canvas.bind('<Button-5>', self._on_mouse_wheel)  # Linux scroll down
        self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)  # Windows scroll
        
        # Bind keyboard events for debugging
        self.canvas.bind('<Configure>', self._on_resize)
        
        # Bind to the Frame's Configure event as well
        self.bind('<Configure>', self._on_frame_configure)
        
        # Initial draw
        self.clear()
        
        # Force initial update
        self.after(100, self.redraw)
    
    def _on_resize(self, event):
        """Handle canvas resize."""
        self.width = event.width
        self.height = event.height
        self.redraw()
    
    def _on_frame_configure(self, event):
        """Handle frame resize."""
        # Update the canvas size to match the frame
        self.canvas.configure(width=event.width, height=event.height)
        self.width = event.width
        self.height = event.height
        self.redraw()
    
    def _on_mouse_down(self, event):
        """Handle mouse button down."""
        self._last_mouse_x = event.x
        self._last_mouse_y = event.y
        self._is_dragging = True
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag for camera rotation."""
        if not self._is_dragging:
            return
        
        dx = event.x - self._last_mouse_x
        dy = event.y - self._last_mouse_y
        
        # Rotate camera based on mouse movement
        rotation_speed = 0.01
        self.camera.orbit(
            delta_azimuth=-dx * rotation_speed,
            delta_elevation=dy * rotation_speed
        )
        
        self._last_mouse_x = event.x
        self._last_mouse_y = event.y
        
        self.redraw()
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel for zoom."""
        # Get delta - different for different platforms
        delta = 0
        if event.num == 4 or event.delta > 0:  # Scroll up
            delta = -0.5
        elif event.num == 5 or event.delta < 0:  # Scroll down
            delta = 0.5
        
        self.camera.orbit(delta_distance=delta)
        self.redraw()
        
        return 'break'  # Prevent further processing
    
    def clear(self):
        """Clear all objects from the canvas."""
        self.canvas.delete('all')
        self.objects = []
        
        # Draw background
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill=self.bg, outline='')
    
    def redraw(self):
        """Redraw all objects on the canvas."""
        self.clear()
        
        # Redraw all objects
        for obj in self.objects:
            self._draw_object(obj)
    
    def _draw_object(self, obj: Dict[str, Any]):
        """Draw a single object."""
        obj_type = obj.get('type')
        
        if obj_type == 'line':
            self._draw_3d_line(obj)
        elif obj_type == 'polygon':
            self._draw_3d_polygon(obj)
        elif obj_type == 'cylinder':
            self._draw_3d_cylinder(obj)
        elif obj_type == 'stiffener':
            self._draw_3d_stiffener(obj)
    
    def _draw_3d_line(self, obj: Dict[str, Any]):
        """Draw a 3D line."""
        start = obj.get('start', Point3D(0, 0, 0))
        end = obj.get('end', Point3D(0, 0, 0))
        color = obj.get('color', 'black')
        width = obj.get('width', 1)
        
        start_2d = self.camera.project_point(start, self.width, self.height)
        end_2d = self.camera.project_point(end, self.width, self.height)
        
        if start_2d and end_2d:
            self.canvas.create_line(
                start_2d[0], start_2d[1], end_2d[0], end_2d[1],
                fill=color, width=width
            )
    
    def _draw_3d_polygon(self, obj: Dict[str, Any]):
        """Draw a 3D polygon."""
        vertices = obj.get('vertices', [])
        color = obj.get('color', 'gray')
        outline = obj.get('outline', 'black')
        width = obj.get('width', 1)
        alpha = obj.get('alpha', 1.0)
        
        # Project all vertices
        projected_vertices = []
        for vertex in vertices:
            point_2d = self.camera.project_point(vertex, self.width, self.height)
            if point_2d:
                projected_vertices.append(point_2d)
        
        if len(projected_vertices) >= 3:
            # Create polygon
            coords = []
            for x, y in projected_vertices:
                coords.extend([x, y])
            
            polygon_id = self.canvas.create_polygon(
                *coords, fill=color, outline=outline, width=width
            )
            
            # Adjust alpha if needed (Tkinter doesn't support alpha directly)
            if alpha < 1.0:
                # For alpha, we can use a lighter color or implement alpha blending
                # This is a simplified approach
                pass
    
    def _draw_3d_cylinder(self, obj: Dict[str, Any]):
        """Draw a 3D cylinder."""
        radius = obj.get('radius', 1.0)
        height = obj.get('height', 1.0)
        center = obj.get('center', Point3D(0, 0, 0))
        color = obj.get('color', 'lightgray')
        outline = obj.get('outline', 'black')
        segments = obj.get('segments', 32)
        
        # Generate cylinder vertices
        vertices = []
        
        # Top and bottom circles
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            # Bottom vertex
            bottom_vertex = Point3D(center.x + x, center.y + y, center.z - height / 2)
            vertices.append(bottom_vertex)
            
            # Top vertex
            top_vertex = Point3D(center.x + x, center.y + y, center.z + height / 2)
            vertices.append(top_vertex)
        
        # Draw side faces (quads between adjacent vertices)
        for i in range(segments):
            next_i = (i + 1) % segments
            
            # Bottom vertices
            v0 = vertices[i * 2]
            v1 = vertices[next_i * 2]
            
            # Top vertices
            v2 = vertices[i * 2 + 1]
            v3 = vertices[next_i * 2 + 1]
            
            # Draw the quad as two triangles
            self._draw_3d_polygon({
                'vertices': [v0, v1, v2],
                'color': color,
                'outline': outline,
                'width': 1
            })
            
            self._draw_3d_polygon({
                'vertices': [v1, v3, v2],
                'color': color,
                'outline': outline,
                'width': 1
            })
        
        # Draw top and bottom caps
        top_center = Point3D(center.x, center.y, center.z + height / 2)
        bottom_center = Point3D(center.x, center.y, center.z - height / 2)
        
        # Top cap
        top_cap_vertices = [top_center]
        for i in range(segments):
            top_cap_vertices.append(vertices[i * 2 + 1])
        
        self._draw_3d_polygon({
            'vertices': top_cap_vertices,
            'color': color,
            'outline': outline,
            'width': 1
        })
        
        # Bottom cap
        bottom_cap_vertices = [bottom_center]
        for i in range(segments):
            bottom_cap_vertices.append(vertices[i * 2])
        
        self._draw_3d_polygon({
            'vertices': bottom_cap_vertices,
            'color': color,
            'outline': outline,
            'width': 1
        })
    
    def _draw_3d_stiffener(self, obj: Dict[str, Any]):
        """Draw a 3D stiffener (longitudinal or ring)."""
        stiffener_type = obj.get('type', 'longitudinal')  # 'longitudinal' or 'ring'
        
        if stiffener_type == 'longitudinal':
            self._draw_longitudinal_stiffener(obj)
        elif stiffener_type == 'ring':
            self._draw_ring_stiffener(obj)
    
    def _draw_longitudinal_stiffener(self, obj: Dict[str, Any]):
        """Draw a longitudinal stiffener."""
        radius = obj.get('radius', 1.0)
        height = obj.get('height', 1.0)
        angle = obj.get('angle', 0.0)  # Angle in radians
        web_height = obj.get('web_height', 0.1)
        web_thickness = obj.get('web_thickness', 0.01)
        flange_width = obj.get('flange_width', 0.05)
        flange_thickness = obj.get('flange_thickness', 0.01)
        color = obj.get('color', 'silver')
        outline = obj.get('outline', 'black')
        segments = obj.get('segments', 4)
        
        # Web vertices
        web_vertices = []
        for z in [0, height]:
            for dr in [0, web_height]:
                x = (radius + dr) * math.cos(angle)
                y = (radius + dr) * math.sin(angle)
                web_vertices.append(Point3D(x, y, z - height / 2))
        
        # Draw web as a quad
        self._draw_3d_polygon({
            'vertices': web_vertices,
            'color': color,
            'outline': outline,
            'width': 1
        })
        
        # Flange vertices (if flange exists)
        if flange_width > 0 and flange_thickness > 0:
            outer_radius = radius + web_height + flange_thickness / 2
            flange_vertices = []
            
            # Create flange as a curved surface
            for z in [0, height]:
                for i in range(segments):
                    flange_angle = angle + (i / (segments - 1) - 0.5) * flange_width / outer_radius
                    x = outer_radius * math.cos(flange_angle)
                    y = outer_radius * math.sin(flange_angle)
                    flange_vertices.append(Point3D(x, y, z - height / 2))
            
            # Draw flange as a series of quads
            for i in range(segments - 1):
                # Bottom vertices
                v0 = flange_vertices[i]
                v1 = flange_vertices[i + 1]
                
                # Top vertices
                v2 = flange_vertices[i + segments]
                v3 = flange_vertices[i + segments + 1]
                
                # Draw the quad as two triangles
                self._draw_3d_polygon({
                    'vertices': [v0, v1, v2],
                    'color': color,
                    'outline': outline,
                    'width': 1
                })
                
                self._draw_3d_polygon({
                    'vertices': [v1, v3, v2],
                    'color': color,
                    'outline': outline,
                    'width': 1
                })
    
    def _draw_ring_stiffener(self, obj: Dict[str, Any]):
        """Draw a ring stiffener."""
        radius = obj.get('radius', 1.0)
        z_position = obj.get('z_position', 0.0)
        web_height = obj.get('web_height', 0.1)
        web_thickness = obj.get('web_thickness', 0.01)
        flange_width = obj.get('flange_width', 0.05)
        flange_thickness = obj.get('flange_thickness', 0.01)
        color = obj.get('color', 'dimgray')
        outline = obj.get('outline', 'black')
        segments = obj.get('segments', 32)
        
        # Web vertices (annular ring)
        inner_radius = radius
        outer_radius = radius + web_height
        
        web_vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            
            # Inner edge
            x_inner = inner_radius * math.cos(angle)
            y_inner = inner_radius * math.sin(angle)
            web_vertices.append(Point3D(x_inner, y_inner, z_position - web_thickness / 2))
            
            # Outer edge
            x_outer = outer_radius * math.cos(angle)
            y_outer = outer_radius * math.sin(angle)
            web_vertices.append(Point3D(x_outer, y_outer, z_position - web_thickness / 2))
        
        # Draw web as a series of quads
        for i in range(segments):
            next_i = (i + 1) % segments
            
            # Bottom vertices
            v0 = web_vertices[i * 2]
            v1 = web_vertices[next_i * 2]
            v2 = web_vertices[i * 2 + 1]
            v3 = web_vertices[next_i * 2 + 1]
            
            # Draw the quad as two triangles
            self._draw_3d_polygon({
                'vertices': [v0, v1, v2],
                'color': color,
                'outline': outline,
                'width': 1
            })
            
            self._draw_3d_polygon({
                'vertices': [v1, v3, v2],
                'color': color,
                'outline': outline,
                'width': 1
            })
        
        # Flange vertices (if flange exists)
        if flange_width > 0 and flange_thickness > 0:
            flange_outer_radius = outer_radius + flange_thickness / 2
            flange_vertices = []
            
            for dz in [-flange_width / 2, flange_width / 2]:
                for i in range(segments):
                    angle = 2 * math.pi * i / segments
                    x = flange_outer_radius * math.cos(angle)
                    y = flange_outer_radius * math.sin(angle)
                    flange_vertices.append(Point3D(x, y, z_position + dz))
            
            # Draw flange as a series of quads
            for i in range(segments):
                next_i = (i + 1) % segments
                
                # Bottom vertices
                v0 = flange_vertices[i]
                v1 = flange_vertices[next_i]
                v2 = flange_vertices[i + segments]
                v3 = flange_vertices[next_i + segments]
                
                # Draw the quad as two triangles
                self._draw_3d_polygon({
                    'vertices': [v0, v1, v2],
                    'color': color,
                    'outline': outline,
                    'width': 1
                })
                
                self._draw_3d_polygon({
                    'vertices': [v1, v3, v2],
                    'color': color,
                    'outline': outline,
                    'width': 1
                })
    
    def add_line(self, start: Point3D, end: Point3D, color: str = 'black', width: int = 1):
        """Add a 3D line to the canvas."""
        obj = {
            'type': 'line',
            'start': start,
            'end': end,
            'color': color,
            'width': width
        }
        self.objects.append(obj)
        self._draw_object(obj)
    
    def add_cylinder(self, radius: float, height: float, center: Point3D = Point3D(0, 0, 0),
                     color: str = 'lightgray', outline: str = 'black', segments: int = 32):
        """Add a 3D cylinder to the canvas."""
        obj = {
            'type': 'cylinder',
            'radius': radius,
            'height': height,
            'center': center,
            'color': color,
            'outline': outline,
            'segments': segments
        }
        self.objects.append(obj)
        self._draw_object(obj)
    
    def add_longitudinal_stiffener(self, radius: float, height: float, angle: float,
                                   web_height: float = 0.1, web_thickness: float = 0.01,
                                   flange_width: float = 0.05, flange_thickness: float = 0.01,
                                   color: str = 'silver', outline: str = 'black', segments: int = 4):
        """Add a longitudinal stiffener to the canvas."""
        obj = {
            'type': 'stiffener',
            'stiffener_type': 'longitudinal',
            'radius': radius,
            'height': height,
            'angle': angle,
            'web_height': web_height,
            'web_thickness': web_thickness,
            'flange_width': flange_width,
            'flange_thickness': flange_thickness,
            'color': color,
            'outline': outline,
            'segments': segments
        }
        self.objects.append(obj)
        self._draw_object(obj)
    
    def add_ring_stiffener(self, radius: float, z_position: float,
                          web_height: float = 0.1, web_thickness: float = 0.01,
                          flange_width: float = 0.05, flange_thickness: float = 0.01,
                          color: str = 'dimgray', outline: str = 'black', segments: int = 32):
        """Add a ring stiffener to the canvas."""
        obj = {
            'type': 'stiffener',
            'stiffener_type': 'ring',
            'radius': radius,
            'z_position': z_position,
            'web_height': web_height,
            'web_thickness': web_thickness,
            'flange_width': flange_width,
            'flange_thickness': flange_thickness,
            'color': color,
            'outline': outline,
            'segments': segments
        }
        self.objects.append(obj)
        self._draw_object(obj)
    
    def set_camera_position(self, position: Point3D):
        """Set the camera position."""
        self.camera.position = position
        self.redraw()
    
    def set_camera_target(self, target: Point3D):
        """Set the camera target."""
        self.camera.target = target
        self.redraw()
    
    def reset_camera(self):
        """Reset the camera to default position."""
        self.camera = Camera3D()
        self.redraw()


def create_stiffened_cylinder_demo(root: tk.Tk):
    """Create a demo window with a stiffened cylinder using Tkinter 3D canvas."""
    
    # Create main window
    demo_window = tk.Toplevel(root)
    demo_window.title("Tkinter 3D - Stiffened Cylinder Demo")
    demo_window.geometry("1000x800")
    
    # Create 3D canvas
    canvas_3d = Tkinter3DCanvas(demo_window, width=1000, height=800, bg='white')
    canvas_3d.pack(fill=tk.BOTH, expand=True)
    
    # Add a cylinder
    cylinder_radius = 2.0
    cylinder_height = 4.0
    cylinder_center = Point3D(0, 0, 0)
    
    canvas_3d.add_cylinder(
        radius=cylinder_radius,
        height=cylinder_height,
        center=cylinder_center,
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
    
    # Add control buttons
    control_frame = tk.Frame(demo_window)
    control_frame.pack(fill=tk.X, padx=10, pady=10)
    
    tk.Button(control_frame, text="Reset View", 
              command=canvas_3d.reset_camera).pack(side=tk.LEFT, padx=5)
    tk.Button(control_frame, text="Top View", 
              command=lambda: canvas_3d.camera.orbit(0, math.radians(90), 0) or canvas_3d.redraw()).pack(side=tk.LEFT, padx=5)
    tk.Button(control_frame, text="Side View", 
              command=lambda: canvas_3d.camera.orbit(math.radians(90), 0, 0) or canvas_3d.redraw()).pack(side=tk.LEFT, padx=5)
    tk.Button(control_frame, text="Iso View", 
              command=lambda: canvas_3d.camera.orbit(math.radians(-45), math.radians(30), 0) or canvas_3d.redraw()).pack(side=tk.LEFT, padx=5)
    
    return demo_window


if __name__ == "__main__":
    # Test the Tkinter 3D canvas with a stiffened cylinder
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    demo_window = create_stiffened_cylinder_demo(root)
    
    # Add some instructions
    info_frame = tk.Frame(demo_window)
    info_frame.pack(fill=tk.X, padx=10, pady=5)
    tk.Label(info_frame, text="Mouse: Left-click and drag to rotate, Scroll to zoom").pack()
    
    root.mainloop()
