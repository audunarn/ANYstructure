import sys, multiprocessing
import tkinter as tk
from ANYstructure.main_application import Application

def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    multiprocessing.freeze_support()
    root = tk.Tk()
    my_app = Application(root)
    root.mainloop()

    # Do argument parsing here (eg. with argparse) and anything else
    # you want your project to do.


def get_version():
    return 2.2

if __name__ == "__main__":
    main()