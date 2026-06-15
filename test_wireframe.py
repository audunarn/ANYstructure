#!/usr/bin/env python
"""
Wireframe test - draws cylinder using lines only to verify projection.
"""

import tkinter as tk
import math

class Point3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Camera3D:
    def __init__(self):
        self.position = Point3D(0, 0, 10)
        self.target = Point3D(0, 0, 0)
        self.up = Point3D(0, 1, 0)
        self.fov = math.radians(60)
        self.near = 1.0
        self.far = 100.0
        self.azimuth = math.radians(-45)
        self.elevation = math.radians(30)
        self.distance = 10.0
        self._update_view_matrix()
    
    def _update_view_matrix(self):
        self.position = Point3D(
            self.distance * math.cos(self.elevation) * math.cos(self.azimuth),
            self.distance * math.sin(self.elevation),
            self.distance * math.cos(self.elevation) * math.sin(self.azimuth)
        )
    
    def get_view_matrix(self):
        forward = (self.target - self.position)
        length = math.sqrt(forward.x**2 + forward.y**2 + forward.z**2)
        if length > 0:
            forward = Point3D(forward.x/length, forward.y/length, forward.z/length)
        
        right = Point3D(
            forward.y * self.up.z - forward.z * self.up.y,
            forward.z * self.up.x - forward.x * self.up.z,
            forward.x * self.up.y - forward.y * self.up.x
        )
        
        new_up = Point3D(
            right.y * forward.z - right.z * forward.y,
            right.z * forward.x - right.x * forward.z,
            right.x * forward.y - right.y * forward.x
        )
        
        view_matrix = [
            [right.x, right.y, right.z, -right.x*self.position.x - right.y*self.position.y - right.z*self.position.z],
            [new_up.x, new_up.y, new_up.z, -new_up.x*self.position.x - new_up.y*self.position.y - new_up.z*self.position.z],
            [-forward.x, -forward.y, -forward.z, forward.x*self.position.x + forward.y*self.position.y + forward.z*self.position.z],
            [0, 0, 0, 1]
        ]
        return view_matrix
    
    def get_projection_matrix(self, width, height):
        aspect = width / height
        f = 1.0 / math.tan(self.fov / 2)
        return [
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (self.far + self.near) / (self.near - self.far), -1],
            [0, 0, (2 * self.far * self.near) / (self.near - self.far), 0]
        ]
    
    def project_point(self, point, width, height):
        view_matrix = self.get_view_matrix()
        x, y, z, w = point.x, point.y, point.z, 1
        cam_x = view_matrix[0][0]*x + view_matrix[0][1]*y + view_matrix[0][2]*z + view_matrix[0][3]*w
        cam_y = view_matrix[1][0]*x + view_matrix[1][1]*y + view_matrix[1][2]*z + view_matrix[1][3]*w
        cam_z = view_matrix[2][0]*x + view_matrix[2][1]*y + view_matrix[2][2]*z + view_matrix[2][3]*w
        cam_w = view_matrix[3][0]*x + view_matrix[3][1]*y + view_matrix[3][2]*z + view_matrix[3][3]*w
        
        # In camera space, camera looks down -z, so points in front have NEGATIVE z
        if cam_z >= -self.near:
            return None
        
        proj_matrix = self.get_projection_matrix(width, height)
        clip_x = proj_matrix[0][0]*cam_x + proj_matrix[0][1]*cam_y + proj_matrix[0][2]*cam_z + proj_matrix[0][3]*cam_w
        clip_y = proj_matrix[1][0]*cam_x + proj_matrix[1][1]*cam_y + proj_matrix[1][2]*cam_z + proj_matrix[1][3]*cam_w
        clip_z = proj_matrix[2][0]*cam_x + proj_matrix[2][1]*cam_y + proj_matrix[2][2]*cam_z + proj_matrix[2][3]*cam_w
        clip_w = proj_matrix[3][0]*cam_x + proj_matrix[3][1]*cam_y + proj_matrix[3][2]*cam_z + proj_matrix[3][3]*cam_w
        
        if clip_w == 0:
            return None
        
        ndc_x = clip_x / clip_w
        ndc_y = clip_y / clip_w
        ndc_z = clip_z / clip_w
        
        screen_x = (ndc_x + 1) * width / 2
        screen_y = (1 - ndc_y) * height / 2
        
        return (screen_x, screen_y)

class WireframeCanvas(tk.Frame):
    def __init__(self, master, width=800, height=600):
        super().__init__(master, bg='white')
        self.width = width
        self.height = height
        self.camera = Camera3D()
        
        self.canvas = tk.Canvas(self, width=width, height=height, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw wireframe cylinder
        self.draw_wireframe_cylinder()
    
    def draw_wireframe_cylinder(self):
        radius = 2.0
        height = 4.0
        segments = 16
        
        # Top circle
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments
            
            x1 = radius * math.cos(angle1)
            y1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            y2 = radius * math.sin(angle2)
            
            # Top circle line
            p1 = Point3D(x1, y1, height/2)
            p2 = Point3D(x2, y2, height/2)
            s1 = self.camera.project_point(p1, self.width, self.height)
            s2 = self.camera.project_point(p2, self.width, self.height)
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='blue', width=2)
            
            # Bottom circle line
            p1 = Point3D(x1, y1, -height/2)
            p2 = Point3D(x2, y2, -height/2)
            s1 = self.camera.project_point(p1, self.width, self.height)
            s2 = self.camera.project_point(p2, self.width, self.height)
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='blue', width=2)
            
            # Vertical line
            p1 = Point3D(x1, y1, height/2)
            p2 = Point3D(x1, y1, -height/2)
            s1 = self.camera.project_point(p1, self.width, self.height)
            s2 = self.camera.project_point(p2, self.width, self.height)
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='black', width=1)

# Test
root = tk.Tk()
root.title("Wireframe Test")
root.geometry("800x600")

canvas_3d = WireframeCanvas(root)
canvas_3d.pack(fill=tk.BOTH, expand=True)

print("You should see a wireframe cylinder (blue circles, black vertical lines)")
root.mainloop()
