#!/usr/bin/env python
"""
Minimal 3D test - just draws a simple cylinder without any complex setup.
"""

import tkinter as tk
import math

class Point3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class Simple3DCanvas(tk.Frame):
    def __init__(self, master, width=800, height=600):
        super().__init__(master)
        self.width = width
        self.height = height
        
        self.canvas = tk.Canvas(self, width=width, height=height, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw a simple 2D representation of a cylinder
        self.draw_simple_cylinder()
    
    def draw_simple_cylinder(self):
        # Draw a simple ellipse (top of cylinder)
        self.canvas.create_oval(100, 100, 300, 200, outline='black', width=2)
        
        # Draw two vertical lines (sides)
        self.canvas.create_line(100, 150, 100, 350, fill='black', width=2)
        self.canvas.create_line(300, 150, 300, 350, fill='black', width=2)
        
        # Draw bottom ellipse
        self.canvas.create_oval(100, 300, 300, 400, outline='black', width=2)
        
        # Label
        self.canvas.create_text(200, 200, text="Cylinder", font=('Arial', 16))

# Test
root = tk.Tk()
root.title("Minimal 3D Test")
root.geometry("800x600")

canvas_3d = Simple3DCanvas(root)
canvas_3d.pack(fill=tk.BOTH, expand=True)

print("Minimal 3D test - you should see a simple cylinder wireframe")
root.mainloop()
