#!/usr/bin/env python
"""
Simplest possible 3D canvas test - just draws a single line.
"""

import tkinter as tk

class Simple3DCanvas(tk.Frame):
    def __init__(self, master, width=800, height=600):
        super().__init__(master)
        
        # Create canvas
        self.canvas = tk.Canvas(self, width=width, height=height, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw a simple 2D line (no projection)
        self.canvas.create_line(100, 100, 700, 500, fill='red', width=5)
        
        # Draw a rectangle
        self.canvas.create_rectangle(200, 200, 600, 400, fill='blue', outline='black')
        
        # Add text
        self.canvas.create_text(400, 300, text="Test Canvas", font=('Arial', 24), fill='white')

# Test
root = tk.Tk()
root.title("Simple Line Test")
root.geometry("800x600")

canvas_3d = Simple3DCanvas(root)
canvas_3d.pack(fill=tk.BOTH, expand=True)

print("You should see a red line, blue rectangle, and white text")
root.mainloop()
