#!/usr/bin/env python
"""
Very basic Tkinter test - just creates a window with a colored rectangle.
"""

import tkinter as tk

root = tk.Tk()
root.title("Basic Tkinter Test")
root.geometry("400x400")

# Create a simple canvas
canvas = tk.Canvas(root, width=400, height=400, bg='white')
canvas.pack()

# Draw a red rectangle
canvas.create_rectangle(50, 50, 350, 350, fill='red', outline='black')

# Add a label
label = tk.Label(root, text="If you see a red square, Tkinter is working!")
label.pack()

print("Window created. You should see a red square in a white canvas.")
root.mainloop()
