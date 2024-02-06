'''
This file open up excel PULS file
1. read and write to the file.
2. run macros.
3. get the results.
'''

import numpy as np
from xlwings import App, Book

class ExcelInterface():
    ''' This class open a ExcelInterface work.
        Input and output structure data and results.
        Running macros.
    '''
    def __init__(self, path_and_file_to_book: str = None, visible = True):
        '''
        :param path_and_file_to_book:  Path and file name or just filename in base directory.
        :param visible: If excel shall open in windows or run in the background.
        '''
        super(ExcelInterface, self).__init__()
        self.app = App(visible=visible)
        self.book = Book(path_and_file_to_book)

        self.names_sp = {'Identification': 1, 'Length of panel': 3, 'Stiffener spacing': 4, 'Plate thickness': 5,
                      'Number of primary stiffeners': 6, 'Stiffener type (L,T,F)': 7, 'Stiffener boundary': 8,
                      'Stiff. Height': 9, 'Web thick.': 10,'Flange width': 11, 'Flange thick.': 12, 'Tilt angle': 13,
                      'Number of sec. stiffeners': 14, 'Modulus of elasticity': 21, "Poisson's ratio": 22,
                      'Yield stress plate': 23, 'Yield stress stiffener': 24, 'Axial stress': 25, 'Trans. stress 1': 26,
                      'Trans. stress 2': 27, 'Shear stress': 28, 'Pressure (fixed)': 29, 'In-plane support': 30}

        self.names_up = {'Identification': 1, 'Length of plate': 3, 'Width of c': 4, 'Plate thickness': 5,
                         'Modulus of elasticity': 6, "Poisson's ratio":7, 'Yield stress plate': 8,
                         'Axial stress 1': 9, 'Axial stress 2': 10,'Trans. stress 1': 11,
                         'Trans. stress 2': 12, 'Shear stress': 13, 'Pressure (fixed)': 14, 'In-plane support': 15,
                         'Rot left': 16, 'Rot right': 17, 'Rot upper': 18, 'Rot lower': 19}

    def close_book(self, save = False):
        ''' Closing ass and book. '''
        if save:
            self.book.save()
        self.book.close()
        self.app.kill()

    def read_data(self, row_number: int = 1, column_number: int = 1):
        ''' Read one cell in the sheet
            Row and columns starts at 1 (not 0 as in python general)
        '''
        return self.book.sheets[1].range((row_number, column_number)).value

    def set_cell_value(self, row_number: int = 1, column_number: int = 1, cell_value = None, sheet_num = 1):
        '''
        Set values of a cell.
        :param row_number:
        :param column_number:
        :param cell_value:
        :return:
        '''
        #print('Row', row_number, 'Col', column_number, 'Cell', cell_value)
        self.book.sheets[sheet_num].range((row_number, column_number)).value = cell_value

    def set_one_row(self, row_number: int = 20, data_dict: dict = None):
        '''
        Set one row of values
        :param row_number: The row to set.
        :param data_dict: Data for one panel.
        :return:
        '''
        for name, col_num in self.names_sp.items():
            self.set_cell_value(row_number, col_num, data_dict[name])

    def set_multiple_rows(self, start_row:int = 20, data_dict: dict = None):
        '''

        :param start_row: First row to input.
        :param list_of_dicts: The data to be set.
        :return:
        '''

        row_number = start_row
        for id, data in data_dict.items():
            self.set_one_row(row_number, data)
            row_number += 1

    def set_multiple_rows_batch(self, data_dict: dict = None):
        '''

        :param start_row: First row to input.
        :param list_of_dicts: The data to be set.
        :return:
        '''

        sp_dict, up_dict = dict(), dict()
        for key, val in data_dict.items():
            if val['sp or up'] == 'SP':
                sp_dict[key] = val
            else:
                up_dict[key] = val
        if len(sp_dict)>0:
            for name, col_num in self.names_sp.items():
                start_row = 20
                self.book.sheets[1].range((start_row, col_num)).options(expand='table', transpose=True).value = \
                    [val[name] for val in sp_dict.values()]
        if len(up_dict) > 0:
            for name, col_num in self.names_up.items():
                start_row = 21
                self.book.sheets[4].range((start_row, col_num)).options(expand='table', transpose=True).value = \
                    [val[name] for val in up_dict.values()]

        return len(sp_dict)>0, len(up_dict)>0

    def calculate_panels(self, sp = True, up = False):
        ''' Calculate the panels in the sheet. '''
        if sp:
            run_macro_sp = self.app.macro('Sheet1.cmdCalculatePanels_Click')
            run_macro_sp()
        if up:
            run_macro_up = self.app.macro('Sheet3.CalculatePanelsU3')
            run_macro_up()

    def get_results_one_cell(self, row_number: int = 1, column_number: int = 1):
        ''' Return the results in one cell of a calculated panel. '''
        return self.book.sheets[2].range((row_number, column_number)).value

    def get_results_one_row(self, row_number: int = 15):
        '''
        Return one row.
        :param row_number:
        :return: dict : [value, unit] e.g. [3000, 'mm']
        '''
        return_dict = dict()
        return_dict['Identification'] = self.get_results_one_cell(row_number, column_number=1)
        # print('start')
        # for idx in range(3,74):
        #     if self.get_results_one_cell(11, column_number=idx) != None:
        #         return_dict[self.get_results_one_cell(11, column_number=idx)] = {}
        # print('stop')
        current_top_row = ''
        for idx in range(3,74):
            if self.get_results_one_cell(11, column_number=idx) != None:
                current_top_row = self.get_results_one_cell(11, column_number=idx)
                return_dict[current_top_row] = {}

            return_dict[current_top_row][self.get_results_one_cell(12, column_number=idx)] = \
                [self.get_results_one_cell(row_number, column_number=idx),
                 self.get_results_one_cell(14, column_number=idx)]
        return return_dict

    def get_all_results_batch(self, sp = True, up = False):

        spup = {(True, True) : ['SP', 'UP'], (True, False) : ['SP'], (False, True) : ['UP']}

        return_dict = {}
        for run in spup[(sp, up)]:
            all_ids  = self.book.sheets[2 if run == 'SP' else 5].range('A15').expand().value
            if type(all_ids) != list:
                all_ids = [all_ids]
            all_data = np.array(self.book.sheets[2 if run == 'SP' else 5].range('C12').expand().value)
            all_top_names = np.array(self.book.sheets[2 if run == 'SP' else 5].range('C11:BU11' if run == 'SP' else 'C11:AS11').value)
            all_names = all_data[0]
            all_data = all_data[3:]
            all_units = np.array(self.book.sheets[2 if run == 'SP' else 5].range('C14:BU14'if run == 'SP' else 'C14:AS14').value)
            current_top_row = ''

            for data_idx, id in enumerate(all_ids):
                return_dict[id] = {}
                return_dict[id]['Identification'] = id
                same, same_idx = False, 2
                for top_name, name, data, unit in zip(all_top_names, all_names, all_data[data_idx], all_units):
                    if top_name != None:
                        current_top_row = top_name
                        return_dict[id][current_top_row] = {}
                    if name in return_dict[id][current_top_row].keys():
                        same = True
                        name = name + ' ' +str(same_idx)
                        same_idx += 1
                    elif same == True and name not in return_dict[id][current_top_row].keys():
                        same = False
                        same_idx = 2
                    return_dict[id][current_top_row][name] = [data, unit]
                if run == 'UP':
                    return_dict[id]['Ultimate capacity']['Actual usage Factor'] = \
                        return_dict[id]['Ultimate capacity']['Usage factor']
                    return_dict[id]['Ultimate capacity']['Allowable usage factor'] = \
                        return_dict[id]['Ultimate capacity']['Alowable usage']
                    return_dict[id]['Buckling strength']['Actual usage Factor'] = \
                        return_dict[id]['Buckling strength']['Usage factor']
                    return_dict[id]['Buckling strength']['Allowable usage factor'] = \
                        return_dict[id]['Buckling strength']['Alowable usage']

                    return_dict[id]['Ultimate capacity'].pop('Usage factor')
                    return_dict[id]['Ultimate capacity'].pop('Alowable usage')
                    return_dict[id]['Buckling strength'].pop('Usage factor')
                    return_dict[id]['Buckling strength'].pop('Alowable usage')
        return return_dict

    def get_all_results(self):
        '''
        Return all results in run.
        :return:
        '''

        return_dict, found_last, row_number = dict(), False, 15
        while found_last is False:
            this_row = self.get_results_one_row(row_number)
            if this_row['Identification'] is not None:
                return_dict[row_number] = this_row
                row_number += 1
            else:
                found_last = True

        return return_dict

    def get_sheet_data(self, sheet = 'excel_input'):
        this_sheet = self.book.sheets[sheet]
        return this_sheet.used_range.value

if __name__ == '__main__':
    # ex1 = {'line25': {'Identification': 'line25', 'Length of plate': 3, 'Width of c': 800.0, 'Plate thickness': 20.0,
    #                   'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0,
    #                   'Axial stress 1': 60.0, 'Axial stress 2': 60.0, 'Trans. stress 1': 0, 'Trans. stress 2': 0,
    #                   'Shear stress': 10.0, 'Pressure (fixed)': 0.0, 'In-plane support': 'GL', 'Rot left': 'SS',
    #                   'Rot right': 'SS', 'Rot upper': 'SS', 'Rot lower': 'SS', 'sp or up': 'UP'}}
    # my_puls = ExcelInterface(r'C:\Github\ANYstructure\ANYstructure\PULS\PulsExcel_new - Copy.xlsm',
    #                     visible=True)
    # my_puls.set_multiple_rows_batch(ex1)
    # my_puls.set_multiple_rows(20, [ex.ex1, ex.ex2, ex.ex3, ex.ex4, ex.ex5, ex.ex6])
    # my_puls.calculate_panels()
    #my_puls.set_one_row(data_dict=ex.ex1['line1'])
    # [print(key, value) for key, value in my_puls.get_all_results().items()]
    # my_puls.close_book()
    my_input = ExcelInterface(r'C:\Github\ANYstructure\anystruct\excel_input_example.xlsx',
                              visible=False)
    data = my_input.get_sheet_data()

    for dom, l1x, l1y, l2x, l2y, pl_t, pl_s, web_h, web_th, fl_b, fl_th, sig_x1, sig_x2, sig_y1, sig_y2, tau_xy in data[1:]:
        print(dom, l1x, l1y, l2x, l2y, pl_t, pl_s, web_h, web_th, fl_b, fl_th, sig_x1, sig_x2, sig_y1, sig_y2, tau_xy)



