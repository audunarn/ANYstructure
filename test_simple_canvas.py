#!/usr/bin/env python
"""
Simple test to verify Tkinter canvas drawing works.
"""

import tkinter as tk

# Test 1: Basic Tkinter canvas
root = tk.Tk()
root.title("Basic Canvas Test")
root.geometry("400x400")

canvas = tk.Canvas(root, width=400, height=400, bg='white')
canvas.pack(fill=tk.BOTH, expand=True)

# Draw a simple rectangle
canvas.create_rectangle(100, 100, 300, 300, fill='blue', outline='black')

# Draw a line
canvas.create_line(50, 50, 350, 350, fill='red', width=2)

# Draw a polygon
canvas.create_polygon(150, 150, 250, 150, 200, 250, fill='green', outline='black')

print("Basic canvas test - you should see a blue rectangle, red line, and green triangle")
root.mainloop()
