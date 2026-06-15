#!/usr/bin/env python
"""
Debug 3D test - draws a cylinder at a known visible position.
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
        self.position = Point3D(0, 0, 10)  # Camera at (0,0,10)
        self.target = Point3D(0, 0, 0)    # Looking at origin
        self.up = Point3D(0, 1, 0)
        self.fov = math.radians(60)
        self.near = 0.1
        self.far = 100.0
    
    def project_point(self, point, width, height):
        # Simple orthographic projection for testing
        # Just ignore z and scale x,y
        scale = 100
        screen_x = (point.x + 2) * scale + width / 2
        screen_y = (point.y + 2) * scale + height / 2
        return (screen_x, screen_y)

class Debug3DCanvas(tk.Frame):
    def __init__(self, master, width=800, height=600):
        super().__init__(master)
        self.width = width
        self.height = height
        self.camera = Camera3D()
        
        self.canvas = tk.Canvas(self, width=width, height=height, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw a cylinder using simple projection
        self.draw_cylinder()
    
    def draw_cylinder(self):
        radius = 2.0
        height = 4.0
        segments = 16
        
        # Draw top circle
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments
            
            x1 = radius * math.cos(angle1)
            y1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            y2 = radius * math.sin(angle2)
            
            p1 = Point3D(x1, y1, height/2)
            p2 = Point3D(x2, y2, height/2)
            
            s1 = self.camera.project_point(p1, self.width, self.height)
            s2 = self.camera.project_point(p2, self.width, self.height)
            
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='blue', width=2)
        
        # Draw bottom circle
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments
            
            x1 = radius * math.cos(angle1)
            y1 = radius * math.sin(angle1)
            x2 = radius * math.cos(angle2)
            y2 = radius * math.sin(angle2)
            
            p1 = Point3D(x1, y1, -height/2)
            p2 = Point3D(x2, y2, -height/2)
            
            s1 = self.camera.project_point(p1, self.width, self.height)
            s2 = self.camera.project_point(p2, self.width, self.height)
            
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='blue', width=2)
        
        # Draw vertical lines
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            p1 = Point3D(x, y, height/2)
            p2 = Point3D(x, y, -height/2)
            
            s1 = self.camera.project_point(p1, self.width, self.height)
            s2 = self.camera.project_point(p2, self.width, self.height)
            
            if s1 and s2:
                self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='black', width=1)
        
        # Draw center lines
        p1 = Point3D(0, 0, height/2)
        p2 = Point3D(0, 0, -height/2)
        s1 = self.camera.project_point(p1, self.width, self.height)
        s2 = self.camera.project_point(p2, self.width, self.height)
        if s1 and s2:
            self.canvas.create_line(s1[0], s1[1], s2[0], s2[1], fill='red', width=3)

# Test
root = tk.Tk()
root.title("Debug 3D Test")
root.geometry("800x600")

canvas_3d = Debug3DCanvas(root)
canvas_3d.pack(fill=tk.BOTH, expand=True)

print("Debug 3D test - you should see a cylinder wireframe")
root.mainloop()
