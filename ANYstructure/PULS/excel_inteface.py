'''
This file open up excel PULS file
1. read and write to the file.
2. run macros.
3. get the results.
'''

import xlwings as xw

class PulsExcel():
    ''' This class open a PulsExcel work.
        Input and output structure data and results.
        Running macros.
    '''
    def __init__(self, path_and_file_to_book: str = None, visible = True):
        '''
        :param path_and_file_to_book:  Path and file name or just filename in base directory.
        :param visible: If excel shall open in windows or run in the background.
        '''
        super(PulsExcel, self).__init__()
        self.app = xw.App(visible=visible)
        self.book = xw.Book(path_and_file_to_book)

        self.names = {'Identification': 1, 'Length of panel': 3, 'Stiffener spacing': 4, 'Plate thickness': 5,
                      'Number of primary stiffeners': 6, 'Stiffener type (L,T,F)': 7, 'Stiffener boundary': 8,
                      'Stiff. Height': 9, 'Web thick.': 10,'Flange width': 11, 'Flange thick.': 12, 'Tilt angle': 13,
                      'Number of sec. stiffeners': 14, 'Modulus of elasticity': 21, "Poisson's ratio": 22,
                      'Yield stress plate': 23, 'Yield stress stiffener': 24, 'Axial stress': 25, 'Trans. stress 1': 26,
                      'Trans. stress 2': 27, 'Shear stress': 28, 'Pressure (fixed)': 29, 'In-plane support': 30}

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

    def set_cell_value(self, row_number: int = 1, column_number: int = 1, cell_value = None):
        '''
        Set values of a cell.
        :param row_number:
        :param column_number:
        :param cell_value:
        :return:
        '''
        #print('Row', row_number, 'Col', column_number, 'Cell', cell_value)
        self.book.sheets[1].range((row_number, column_number)).value = cell_value

    def set_one_row(self, row_number: int = 20, data_dict: dict = None):
        '''
        Set one row of values
        :param row_number: The row to set.
        :param data_dict: Data for one panel.
        :return:
        '''
        for name, col_num in self.names.items():
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

    def calculate_panels(self):
        ''' Calculate the panels in the sheet. '''
        run_macro = self.app.macro('Sheet1.cmdCalculatePanels_Click')
        run_macro()

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

if __name__ == '__main__':
    my_puls = PulsExcel('PulsExcel.xls', visible=False)
    # my_puls.set_multiple_rows(20, [ex.ex1, ex.ex2, ex.ex3, ex.ex4, ex.ex5, ex.ex6])
    # my_puls.calculate_panels()
    #my_puls.set_one_row(data_dict=ex.ex1['line1'])
    [print(key, value) for key, value in my_puls.get_all_results().items()]
    my_puls.close_book()


