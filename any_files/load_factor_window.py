# Audun

import tkinter as tk
import os
from _tkinter import TclError

class CreateLoadFactorWindow:
    '''
    self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,0]} # DNV  loads factors
    '''

    def __init__(self,master, app=None):
        super(CreateLoadFactorWindow, self).__init__()
        self._frame = master
        self._frame.wm_title("Load factor modifications here.")
        self._frame.geometry('800x800')
        self._frame.grab_set()
        self._app = app
        if __name__ == '__main__':
            self._load_factors_dict = {'dnva': [1.3, 1.2, 0.7], 'dnvb': [1, 1, 1.3],
                                       'tanktest': [1, 1, 0]}  # DNV  loads factors


        else:
            self._load_factors_dict = app._load_factors_dict

        self.new_conda_lff1 = tk.DoubleVar()
        self.new_conda_lff2 = tk.DoubleVar()
        self.new_conda_lff3 = tk.DoubleVar()
        self.new_condb_lff1 = tk.DoubleVar()
        self.new_condb_lff2 = tk.DoubleVar()
        self.new_condb_lff3 = tk.DoubleVar()
        self.new_condtt_lff1 = tk.DoubleVar()
        self.new_condtt_lff2 = tk.DoubleVar()
        self.new_condtt_lff3 = tk.DoubleVar()

        self.new_change_default = tk.BooleanVar()
        self.new_change_existing = tk.BooleanVar()

        self.new_conda_lff1.set(self._load_factors_dict['dnva'][0])
        self.new_conda_lff2.set(self._load_factors_dict['dnva'][1])
        self.new_conda_lff3.set(self._load_factors_dict['dnva'][2])
        self.new_condb_lff1.set(self._load_factors_dict['dnvb'][0])
        self.new_condb_lff2.set(self._load_factors_dict['dnvb'][1])
        self.new_condb_lff3.set(self._load_factors_dict['dnvb'][2])
        self.new_condtt_lff1.set(self._load_factors_dict['tanktest'][0])
        self.new_condtt_lff2.set(self._load_factors_dict['tanktest'][1])
        self.new_condtt_lff3.set(self._load_factors_dict['tanktest'][2])

        ent_w = 20
        tk.Label(self._frame, text='Static and dynamic load factors is specified here', font='Verdana 15 bold')\
            .grid(row = 1, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Note that DNV is used as reference, '
                                   'but the load factors can be any other rule set such as ISO.', font='Verdana 8 bold')\
            .grid(row = 2, column = 1, sticky = tk.W)

        tk.Label(self._frame, text=' ', font='Verdana 8 bold')\
            .grid(row = 3, column = 1, sticky = tk.W)

        tk.Label(self._frame, text='Condition a) - Static load factor "unknown loads"', font='Verdana 8 bold')\
            .grid(row = 4, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Condition a) - Static load factor well defined loads', font='Verdana 8 bold')\
            .grid(row = 5, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Condition a) - Dynamic load factor', font='Verdana 8 bold')\
            .grid(row = 6, column = 1, sticky = tk.W)
        self.ent_conda_lf1 = tk.Entry(self._frame, textvariable=self.new_conda_lff1, width=ent_w)
        self.ent_conda_lf2 = tk.Entry(self._frame, textvariable=self.new_conda_lff2, width=ent_w)
        self.ent_conda_lf3 = tk.Entry(self._frame, textvariable=self.new_conda_lff3, width=ent_w)
        self.ent_conda_lf1.grid(row=4, column=2)
        self.ent_conda_lf2.grid(row=5, column=2)
        self.ent_conda_lf3.grid(row=6, column=2)
        


        tk.Label(self._frame, text=' ', font='Verdana 8 bold')\
            .grid(row = 7, column = 1, sticky = tk.W)

        tk.Label(self._frame, text='Condition b) - Static load factor "unknown loads"', font='Verdana 8 bold')\
            .grid(row = 8, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Condition b) - Static load factor well defined loads', font='Verdana 8 bold')\
            .grid(row = 9, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Condition b) - Dynamic load factor', font='Verdana 8 bold')\
            .grid(row = 10, column = 1, sticky = tk.W)
        self.ent_condb_lf1 = tk.Entry(self._frame, textvariable=self.new_condb_lff1, width=ent_w)
        self.ent_condb_lf2 = tk.Entry(self._frame, textvariable=self.new_condb_lff2, width=ent_w)
        self.ent_condb_lf3 = tk.Entry(self._frame, textvariable=self.new_condb_lff3, width=ent_w)
        self.ent_condb_lf1.grid(row=8, column=2)
        self.ent_condb_lf2.grid(row=9, column=2)
        self.ent_condb_lf3.grid(row=10, column=2)

        tk.Label(self._frame, text=' ', font='Verdana 8 bold')\
            .grid(row = 11, column = 1, sticky = tk.W)

        tk.Label(self._frame, text='Tank test) - Static load factor "unknown loads"', font='Verdana 8 bold')\
            .grid(row = 12, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Tank test)  - Static load factor well defined loads', font='Verdana 8 bold')\
            .grid(row = 13, column = 1, sticky = tk.W)
        tk.Label(self._frame, text='Tank test)  - Dynamic load factor', font='Verdana 8 bold')\
            .grid(row = 14, column = 1, sticky = tk.W)
        self.ent_condtt_lf1 = tk.Entry(self._frame, textvariable=self.new_condtt_lff1, width=ent_w)
        self.ent_condtt_lf2 = tk.Entry(self._frame, textvariable=self.new_condtt_lff2, width=ent_w)
        self.ent_condtt_lf3 = tk.Entry(self._frame, textvariable=self.new_condtt_lff3, width=ent_w)
        self.ent_condtt_lf1.grid(row=12, column=2)
        self.ent_condtt_lf2.grid(row=13, column=2)
        self.ent_condtt_lf3.grid(row=14, column=2)

        tk.Label(self._frame, text=' ', font='Verdana 8 bold')\
            .grid(row = 15, column = 1, sticky = tk.W)
        # tk.Label(self._frame, text='Change all current load factors', font='Verdana 8 bold')\
        #     .grid(row = 16, column = 1, sticky = tk.W)
        # tk.Checkbutton(self._frame, variable=self.new_change_existing)\
        #     .grid(row=17, column=1, sticky = tk.W)
        # tk.Label(self._frame, text='Change default load factors', font='Verdana 8 bold')\
        #     .grid(row = 18, column = 1, sticky = tk.W)
        # tk.Checkbutton(self._frame, variable=self.new_change_default)\
        #     .grid(row=19, column=1, sticky=tk.W)
        #
        tk.Label(self._frame, text=' ', font='Verdana 8 bold')\
            .grid(row = 16, column = 1, sticky = tk.W)

        destroy_and_return = tk.Button(self._frame, text='Return specified load factors and change existing',
                                        command=self.return_load_factors, bg='green', font='Verdana 12', fg='yellow')
        destroy_and_return.grid(row = 17, column = 1)

        tk.Label(self._frame, text=' ', font='Verdana 8 bold')\
            .grid(row = 18, column = 1)

        try:
            img_file_name = 'img_dnv_load_combinations.gif'
            if os.path.isfile('images/' + img_file_name):
                file_path ='images/' + img_file_name
            else:
                file_path = app._root_dir + '/images/' + img_file_name
            photo_transverse = tk.PhotoImage(file=file_path)
            label_trans = tk.Label(self._frame, image=photo_transverse)
            label_trans.image = photo_transverse  # keep a reference!
            label_trans.grid(row = 19, column = 1, columnspan = 2)
        except TclError:
            pass

    def return_load_factors(self):
        '''
        self._load_factors_dict = {'dnva':[1.3,1.2,0.7], 'dnvb':[1,1,1.3], 'tanktest':[1,1,0]} # DNV  loads factors
        :return:
        '''
        self._load_factors_dict['dnva'] = [self.new_conda_lff1.get(), self.new_conda_lff2.get(),
                                           self.new_conda_lff3.get()]
        self._load_factors_dict['dnvb'] = [self.new_condb_lff1.get(), self.new_condb_lff2.get(),
                                           self.new_condb_lff3.get()]
        self._load_factors_dict['tanktest'] = [self.new_condtt_lff1.get(), self.new_condtt_lff2.get(),
                                           self.new_condtt_lff3.get()]
        if __name__ == '__main__':
            self._frame.destroy()
            print({'returned lf dict': self._load_factors_dict,
                                               'change exisiting': self.new_change_existing.get(),
                                               'change default': self.new_change_default.get()})
            return

        self._app.on_close_load_factor_window({'returned lf dict': self._load_factors_dict,
                                               'change exisiting': self.new_change_existing.get(),
                                               'change default': self.new_change_default.get()})
        self._frame.destroy()
if __name__ == '__main__':
    root = tk.Tk()
    my_app = CreateLoadFactorWindow(root,app=None)
    root.mainloop()