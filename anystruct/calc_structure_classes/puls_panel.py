import os
import time
import datetime
import json
import random
from typing import Optional, Dict

import excel_inteface as pulsxl
import numpy as np
from pydantic import BaseModel

try:
    import anystruct.helper as hlp
    import anystruct.SN_curve_parameters as snc
except ModuleNotFoundError:
    import ANYstructure.anystruct.helper as hlp # type: ignore
    import ANYstructure.anystruct.SN_curve_parameters as snc # type: ignore

class PULSpanel(BaseModel):
    '''
    Takes care of puls runs
    '''

    all_to_run: dict = {}
    run_results: dict = {} 
    puls_acceptance: float = 0.87
    puls_sheet_location: Optional[str] = None
    all_uf: dict = {'buckling': list(), 'ultimate': list()}
    # def __init__(self, run_dict: dict = {}, puls_acceptance: float = 0.87, puls_sheet_location: str = None):
    #     super(PULSpanel, self).__init__()

    #     self._all_to_run = run_dict
    #     self._run_results = {}
    #     self._puls_acceptance = puls_acceptance
    #     self._puls_sheet_location = puls_sheet_location
    #     self._all_uf = {'buckling': list(), 'ultimate': list()}

    # @property
    # def all_uf(self):
    #     return self._all_uf

    # @property
    # def puls_acceptance(self):
    #     return self._puls_acceptance

    # @puls_acceptance.setter
    # def puls_acceptance(self, val):
    #     self._puls_acceptance = val

    # @property
    # def puls_sheet_location(self):
    #     return self._puls_sheet_location

    # @puls_sheet_location.setter
    # def puls_sheet_location(self, val):
    #     self._puls_sheet_location = val

    # def set_all_to_run(self, val):
    #     self._all_to_run = val

    # def get_all_to_run(self):
    #     return self._all_to_run

    # def get_run_results(self):
    #     return self._run_results

    def set_run_results(self, val):
        self.run_results = val
        for key in self.run_results.keys():
            if any([key == 'sheet location',type(self.run_results[key]['Buckling strength']) != dict,
                    type(self.run_results[key]['Ultimate capacity']) != dict]):
                continue

            if all([type(self.run_results[key]['Buckling strength']['Actual usage Factor'][0]) == float,
                    type(self.run_results[key]['Ultimate capacity']['Actual usage Factor'][0]) == float]):
                self.all_uf['buckling'].append(self.run_results[key]['Buckling strength']['Actual usage Factor'][0])
                self.all_uf['ultimate'].append(self.run_results[key]['Ultimate capacity']['Actual usage Factor'][0])
        self.all_uf['buckling'] = np.unique(self.all_uf['buckling']).tolist()
        self.all_uf['ultimate'] = np.unique(self.all_uf['ultimate']).tolist()


    def run_all(self, store_results: bool = False):
        '''
        Returning following results.:

        Identification:  name of line/run
        Plate geometry:       dict_keys(['Length of panel', 'Stiffener spacing', 'Plate thick.'])
        Primary stiffeners: dict_keys(['Number of stiffeners', 'Stiffener type', 'Stiffener boundary', 'Stiff. Height',
                            'Web thick.', 'Flange width', 'Flange thick.', 'Flange ecc.', 'Tilt angle'])
        Secondary stiffeners. dict_keys(['Number of sec. stiffeners', 'Secondary stiffener type', 'Stiffener boundary',
                            'Stiff. Height', 'Web thick.', 'Flange width', 'Flange thick.'])
        Model imperfections. dict_keys(['Imp. level', 'Plate', 'Stiffener', 'Stiffener tilt'])
        Material: dict_keys(['Modulus of elasticity', "Poisson's ratio", 'Yield stress plate', 'Yield stress stiffener'])
        Aluminium prop: dict_keys(['HAZ pattern', 'HAZ red. factor'])
        Applied loads: dict_keys(['Axial stress', 'Trans. stress', 'Shear stress', 'Pressure (fixed)'])
        Bound cond.: dict_keys(['In-plane support'])
        Global elastic buckling: dict_keys(['Axial stress', 'Trans. Stress', 'Trans. stress', 'Shear stress'])
        Local elastic buckling: dict_keys(['Axial stress', 'Trans. Stress', 'Trans. stress', 'Shear stress'])
        Ultimate capacity: dict_keys(['Actual usage Factor', 'Allowable usage factor', 'Status'])
        Failure modes: dict_keys(['Plate buckling', 'Global stiffener buckling', 'Torsional stiffener buckling',
                            'Web stiffener buckling'])
        Buckling strength: dict_keys(['Actual usage Factor', 'Allowable usage factor', 'Status'])
        Local geom req (PULS validity limits): dict_keys(['Plate slenderness', 'Web slend', 'Web flange ratio',
                            'Flange slend ', 'Aspect ratio'])
        CSR-Tank requirements (primary stiffeners): dict_keys(['Plating', 'Web', 'Web-flange', 'Flange', 'stiffness'])

        :return:
        '''
        

        iterator = self.all_to_run
        newfile = self.puls_sheet_location
        my_puls = pulsxl.PulsExcel(newfile, visible=False) # type: ignore
        #my_puls.set_multiple_rows(20, iterator)
        run_sp, run_up = my_puls.set_multiple_rows_batch(iterator)
        my_puls.calculate_panels(sp=run_sp, up=run_up)
        #all_results = my_puls.get_all_results()
        # ideally this gets updated not to return a dictionary but an object
        all_results: Dict[int, Dict] = my_puls.get_all_results_batch(sp=run_sp, up=run_up)

        for id, data in all_results.items():
            self.run_results[id] = data

        my_puls.close_book(save=False)

        self.all_uf = {'buckling': list(), 'ultimate': list()}
        for key in self.run_results.keys():
            try:
                if all([type(self.run_results[key]['Buckling strength']['Actual usage Factor'][0]) == float,
                        type(self.run_results[key]['Ultimate capacity']['Actual usage Factor'][0]) == float]):
                    self.all_uf['buckling'].append(self.run_results[key]['Buckling strength']
                                                    ['Actual usage Factor'][0])
                    self.all_uf['ultimate'].append(self.run_results[key]['Ultimate capacity']
                                                    ['Actual usage Factor'][0])
            except TypeError:
                print('Got a type error. Life will go on. Key for PULS run results was', key)
                print(self.run_results[key])
        
        self.all_uf['buckling'] = np.unique(self.all_uf['buckling']).tolist()
        self.all_uf['ultimate'] = np.unique(self.all_uf['ultimate']).tolist()
        
        if store_results:
            store_path = os.path.dirname(os.path.abspath(__file__))+'\\PULS\\Result storage\\'
            with open(store_path + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")+'_UP.json', 'w') as file:
                file.write(json.dumps(all_results, ensure_ascii=False))
        
        return all_results


    def get_utilization(self, line, method, acceptance = 0.87):
        if line in self.run_results.keys():
            if method == 'buckling':
                if type(self.run_results[line]['Buckling strength']['Actual usage Factor'][0]) == str or \
                        self.run_results[line]['Buckling strength']['Actual usage Factor'][0] is None:
                    return None
                return self.run_results[line]['Buckling strength']['Actual usage Factor'][0]/acceptance
            else:
                if type(self.run_results[line]['Ultimate capacity']['Actual usage Factor'][0]) == str or \
                        self.run_results[line]['Buckling strength']['Actual usage Factor'][0] is None:
                    return None
                return self.run_results[line]['Ultimate capacity']['Actual usage Factor'][0]/acceptance
        else:
            return None


    def get_puls_line_results(self, line):
        if line not in self.run_results.keys():
            return None
        else:
            return self.run_results[line]


    def get_string(self, line, uf = 0.87):
        '''
        :param line:
        :return:
        '''

        results = self.run_results[line]
        loc_geom = 'Ok' if all([val[0] == 'Ok' for val in results['Local geom req (PULS validity limits)']
                              .values()]) else 'Not ok'
        csr_geom = 'Ok' if all([val[0] == 'Ok' for val in results['CSR-Tank requirements (primary stiffeners)']
                              .values()]) else 'Not ok'

        ret_str = 'PULS results\n\n' +\
                  'Ultimate capacity usage factor:  ' + str(results['Ultimate capacity']['Actual usage Factor'][0]/uf)+'\n'+\
                  'Buckling strength usage factor:  ' + str(results['Buckling strength']['Actual usage Factor'][0]/uf)+'\n'+\
                  'Local geom req (PULS validity limits):   ' + loc_geom + '\n'+\
                  'CSR-Tank requirements (primary stiffeners):   ' + csr_geom
        
        return ret_str


    def result_changed(self, id):
        if id in self.run_results.keys():
            self.run_results.pop(id)


    def generate_random_results(self, batch_size: int = 1000, stf_type: str = None): # type: ignore
        '''
        Genrate random results based on user input.
        :return:
        '''

        '''
        Running iterator:
        run_dict_one = {'line3': {'Identification': 'line3', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0,
                          'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T',
                          'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 200.0,
                          'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0,
                          'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0,
                          'Yield stress stiffener': 355.0, 'Axial stress': 101.7, 'Trans. stress 1': 100.0,
                          'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.41261,
                          'In-plane support': 'Int'}}
        '''
        run_dict = {}

        profiles = hlp.helper_read_section_file('bulb_anglebar_tbar_flatbar.csv')
        if stf_type is not None:
            new_profiles = list()
            for stf in profiles:
                if stf['stf_type'][0] == stf_type:
                    new_profiles.append(stf)
            profiles = new_profiles
        
        lengths = np.arange(2000,6000,100)
        spacings = np.arange(500,900,10)
        thks = np.arange(10,25,1)
        axstress =transsress1 = transsress2 = shearstress = np.arange(-200,210,10) #np.concatenate((np.arange(-400,-200,10), np.arange(210,410,10)))

        pressures =  np.arange(0,0.45,0.01)
        now = time.time()
        yields = np.array([235,265,315,355,355,355,355,390,420,460])
        for idx in range(batch_size):
            ''' Adding 'Stiffener type (L,T,F)': self.stf_type,  'Stiffener boundary': 'C',
                'Stiff. Height': self.stf_web_height*1000, 'Web thick.': self.stf_web_thk*1000, 
                'Flange width': self.stf_flange_width*1000, 'Flange thick.': self.stf_flange_thk*1000}'''

            this_id = 'run_' + str(idx) + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            this_stf = random.choice(profiles)

            if random.choice([True, False]):
                boundary = 'Int'
            else:
                boundary = random.choice(['GL', 'GT'])
            if random.choice([True, True, True, False]):
                stf_boundary = 'C'
            else:
                stf_boundary = 'S'
            #boundary = 'Int'
            #stf_boundary = 'C'


            yieldstress = np.random.choice(yields)
            if random.choice([True, True, True, False]):
                transstress1 = np.random.choice(transsress1)  # Using same value for trans1 and trans 2
                transstress2 = transstress1
            else:
                transstress1 = np.random.choice(transsress1)
                transstress2 = np.random.choice(transsress2)

            # run_dict[this_id] = {'Identification': this_id, 'Length of panel': np.random.choice(lengths),
            #                      'Stiffener spacing': np.random.choice(spacings),
            #                      'Plate thickness': np.random.choice(thks), 'Number of primary stiffeners': 10,
            #                      'Stiffener type (L,T,F)': 'F' if this_stf['stf_type'][0] == 'FB' else this_stf['stf_type'][0],
            #                      'Stiffener boundary': stf_boundary,
            #                      'Stiff. Height': this_stf['stf_web_height'][0]*1000,
            #                      'Web thick.': this_stf['stf_web_thk'][0]*1000,
            #                      'Flange width': 0 if this_stf['stf_type'][0] == 'F'
            #                      else this_stf['stf_flange_width'][0]*1000,
            #                      'Flange thick.': 0 if  this_stf['stf_type'][0] == 'F'
            #                      else this_stf['stf_flange_thk'][0]*1000,
            #                      'Tilt angle': 0, 'Number of sec. stiffeners': 0,
            #                      'Modulus of elasticity': 210000, "Poisson's ratio": 0.3,
            #                      'Yield stress plate':yieldstress, 'Yield stress stiffener': yieldstress,
            #                      'Axial stress': 0 if boundary == 'GT' else np.random.choice(axstress),
            #                      'Trans. stress 1': 0 if boundary == 'GL' else transstress1,
            #                      'Trans. stress 2': 0 if boundary == 'GL' else transstress2,
            #                      'Shear stress': np.random.choice(shearstress),
            #                      'Pressure (fixed)': 0 if stf_boundary == 'S' else np.random.choice(pressures),
            #                      'In-plane support': boundary, 'sp or up': 'SP'}

            same_ax = np.random.choice(axstress)
            lengths = np.arange(100, 6000, 100)
            spacings = np.arange(100, 26000, 100)
            thks = np.arange(10, 50, 1)
            boundary = random.choice(['GL', 'GT'])

            if np.random.choice([True,False,False,False]):
                support = ['SS','SS','SS','SS']
            elif np.random.choice([True,False,False,False]):
                support = ['CL','CL','CL','CL']
            else:
                support = [np.random.choice(['SS', 'CL']),np.random.choice(['SS', 'CL']),
                           np.random.choice(['SS', 'CL']),np.random.choice(['SS', 'CL'])]
            if np.random.choice([True,False]):
                press = 0
            else:
                press = np.random.choice(pressures)
            run_dict[this_id] = {'Identification': this_id, 'Length of plate': np.random.choice(lengths),
                                 'Width of c': np.random.choice(spacings),
                           'Plate thickness': np.random.choice(thks),
                         'Modulus of elasticity': 210000, "Poisson's ratio": 0.3,
                                 'Yield stress plate':yieldstress,
                         'Axial stress 1': 0 if boundary == 'GT' else same_ax,
                           'Axial stress 2': 0 if boundary == 'GT' else same_ax,
                           'Trans. stress 1': 0 if boundary == 'GL' else transstress1,
                         'Trans. stress 2': 0 if boundary == 'GL' else transstress2,
                           'Shear stress': np.random.choice(shearstress), 'Pressure (fixed)': press,
                                 'In-plane support': boundary,
                         'Rot left': support[0], 'Rot right': support[1],
                                 'Rot upper': support[2], 'Rot lower': support[3],
                           'sp or up': 'UP'}

        self._all_to_run = run_dict
        self.run_all(store_results=True)
        
        print('Time to run', batch_size, 'batches:', time.time() - now)