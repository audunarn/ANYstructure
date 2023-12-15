import sys, multiprocessing, ctypes, os
import tkinter as tk
from anystruct.main_application import Application

def main(args=None):
    """The main routine."""

    if args is None:
        args = sys.argv[1:]

    multiprocessing.freeze_support()
    errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
    root = tk.Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f'{width}x{height}')
    my_app = Application(root)
    root.mainloop()

    # Do argument parsing here (eg. with argparse) and anything else
    # you want your project to do.

if __name__ == "__main__":
    main()
