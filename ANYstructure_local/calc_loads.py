import numpy as np

class Loads():
    '''
    This Class calculates the load to be applied on the structure
    '''

    def __init__(self, main_load_dict):

        self.main_load_dict = main_load_dict
        self.static_draft = main_load_dict['static_draft']
        self.poly_third = main_load_dict['poly_third']
        self.poly_second = main_load_dict['poly_second']
        self.poly_first = main_load_dict['poly_first']
        self.poly_const = main_load_dict['poly_const']
        self.manual_press = main_load_dict['man_press']
        self.load_condition = main_load_dict['load_condition']
        if main_load_dict['load_condition'] == 'slamming':
            self.slamming_pl_reduction_factor = 1
            self.slamming_stf_reduction_factor = 1
        else:
            self.slamming_pl_reduction_factor = main_load_dict['slamming mult pl']
            self.slamming_stf_reduction_factor = main_load_dict['slamming mult stf']
        self.name_of_load = main_load_dict['name_of_load']
        try:
            self.limit_state = main_load_dict['limit_state']
        except KeyError:
            self.limit_state = 'ULS'
        try:
            self.horizontal_types = main_load_dict['structure_types']['horizontal']
            self.vertical_types = main_load_dict['structure_types']['vertical']
        except KeyError:
            self.horizontal_types = ['BOTTOM', 'BBT', 'HOPPER', 'MD']
            self.vertical_types = ['BBS', 'SIDE_SHELL', 'SSS']

        self.dynamic_pressure = 0
        self.static_pressure = 0
        self.is_external = True

    def __str__(self):
        string = str('Properties selected load is:'+
                     '\n----------------------------'+
                     '\n Name of load: ' + str(self.name_of_load) +
                     '\n Polynominal (x^3): '+  str(self.poly_third) +
                     '\n Polynominal (x^2): '+  str(self.poly_second) +
                     '\n Polynominal (x):   '+  str(self.poly_first) +
                     '\n Constant (C):      '+  str(self.poly_const) +
                     '\n Load condition:    '+  str(self.load_condition) +
                     '\n Limit state       ' +  str(self.limit_state) +
                     '\n Is external?       '+  str(self.is_external) +
                     '\n Static draft:      '+  str(self.static_draft))
        return string

    def get_calculated_pressure(self,varibale_value, acceleration, structure_type):
        '''
        Input variable is a tuple of (x,y). This method need one variable and the right one must be chosen.
        :param varibale_value:
        :return:
        '''
        #print('   pressure requested for var/acc: ', varibale_value,'/',acceleration, 'type is: ', structure_type)
        input_var = varibale_value

        if self.is_static():
            press = 1025 * acceleration * (self.static_draft - input_var[1])
        elif structure_type in self.horizontal_types:
            press = self.__calculate_poly_value(input_var[0])
        elif structure_type  in self.vertical_types:
            press = self.__calculate_poly_value(input_var[1])
        else:
            press = 0

        if self.load_condition == 'slamming':
            psl = self.__calculate_poly_value(0)
            return max(press, psl)
        else:
            return press

    def get_report_string(self):
        return [     'Name of load: ' + self.name_of_load,
                     'Polynominal (x^3): '+  str(self.poly_third) ,
                     'Polynominal (x^2): '+  str(self.poly_second) ,
                     'Polynominal (x):   '+  str(self.poly_first) ,
                     'Constant (C):      '+  str(self.poly_const) ,
                     'Load condition:    '+  str(self.load_condition) ,
                     'Limit state        ' +  str(self.limit_state) ,
                     'Is external?       '+  str(self.is_external) ,
                     'Static draft:      '+  str(self.static_draft)]

    def __calculate_poly_value(self, variable):
        '''
        Returning magnitude of load in the polynominal equation.
        :param variable:
        :return:
        '''

        return np.polyval( [self.poly_third, self.poly_second, self.poly_first, self.poly_const], variable)

    def get_load_condition(self):
        return self.load_condition

    def is_tank_test(self):
        return self.load_condition == 'tanktest'

    def get_load_parmeters(self):
        return self.poly_third, self.poly_second, self.poly_first, self.poly_const, self.load_condition, \
               None, self.manual_press, self.static_draft, self.name_of_load, self.limit_state, \
               self.slamming_pl_reduction_factor, self.slamming_stf_reduction_factor

    def get_name(self):
        return self.name_of_load

    def is_static(self):
        '''
        Checking if the load is static type.
        :return:
        '''
        return self.static_draft != None

    def get_static_draft(self):
        '''
        Return static draft if is_static
        :return:
        '''
        if self.is_static():
            return self.static_draft
        else:
            pass

    def get_limit_state(self):
        ''' Return ULS, FLS.... '''
        return self.limit_state

    def get_load_condition(self):
        ''' Getting loaded, ballast or part '''
        return self.load_condition

    def get_slamming_reduction_plate(self):
        return self.slamming_pl_reduction_factor

    def get_slamming_reduction_stf(self):
        return self.slamming_stf_reduction_factor

class Tanks():
    '''
    This class incorporates all tank definitions
        temp_tank_dict = {0  'comp_no' : comp_no,
                          1  'cells' : properties[0],
                          2  'min_el' :  properties[1],
                          3  'max_el' : properties[2],
                          4  'content' : '',
                          5  'added_press' : 0,
                          6  'acc' : {static:g,dyn_loaded:az,dyn_ballast:az}
                          7  'density' : 1025}

    '''

    def __init__(self, tank_dict):

        self.properties = tank_dict
        self.compartment_number = tank_dict['comp_no']
        self.cells = tank_dict['cells']
        self.min_elevation = tank_dict['min_el']
        self.max_elevation = tank_dict['max_el']
        self.content = tank_dict['content']
        self.added_pressure = tank_dict['added_press']
        self.density = tank_dict['density']
        self.acc_static = tank_dict['acc']['static']
        self.acc_dyn_loaded = tank_dict['acc']['dyn_loaded']
        self.acc_dyn_ballast = tank_dict['acc']['dyn_ballast']
        self.all_types = ['crude_oil', 'diesel', 'slop', 'fresh water', 'ballast']

    def __str__(self):
        '''
        Prints a string for the tank.
        :return:
        '''
        tank_string = str('--- Tank properties (selected tank) ---'+
                          '\n Minimum elevtaion:          ' + str(self.min_elevation) +
                          '\n Maximum elevation:          ' + str(self.max_elevation) +
                          '\n Content of tank:            ' + self.content +
                          '\n Defined density:            ' + str(self.density) +
                          '\n Defined acceleration:       ' + 'st = ' + str(self.acc_static) + ' , azl = ' +
                                                                str(self.acc_dyn_loaded) + ' , azb = ' +
                                                                str(self.acc_dyn_ballast) +
                          '\n Added pressure at tank top: ' + str(self.added_pressure) )

        return tank_string

    def set_overpressure(self, overpressure):
        '''
        Setter
        :param overpressure:
        :return:
        '''

        self.added_pressure = overpressure
        self.properties['added_press'] = overpressure

    def set_content(self, content):
        '''
        Setter
        :param overpressure:
        :return:
        '''
        self.properties['content'] = content
        self.content = content

    def set_acceleration(self, acc):
        '''
        Setter
        :param overpressure:
        :return:
        '''

        self.acc_static = acc['static']
        self.properties['static'] = acc['static']

        self.acc_dyn_loaded = acc['dyn_loaded']
        self.properties['dyn_loaded'] = acc['dyn_loaded']

        self.acc_dyn_ballast = acc['dyn_ballast']
        self.properties['dyn_ballast'] = acc['dyn_ballast']

    def set_density(self,density):
        '''
        Setter
        :param overpressure:
        :return:
        '''
        self.properties['density'] = density
        self.density = density

    def get_name(self):
        '''
        Returns the name of the compartmnet
        :return:
        '''
        return 'comp'+str(self.compartment_number)

    def get_highest_elevation(self):
        '''
        Find the top of the tank.
        :return:
        '''
        return self.max_elevation

    def get_lowest_elevation(self):
        '''
        Find the bottom of the tank.
        :return:
        '''
        return self.min_elevation

    def get_line_pressure_from_max_pressure(self, pressure, coordinates):
        '''
        Used when you have a maximum pressure and request the pressure at a specific coordinate.
        :param coordinates:
        :return:
        '''
        elevation = coordinates[1]
        return pressure *((self.get_highest_elevation()-elevation)/
                          (self.get_highest_elevation()-self.get_lowest_elevation()))

    def get_calculated_pressure(self, coordinates, acceleration):
        '''
        Get the pressure with specified variable.
        :param elevaiton:
        :return:
        '''

        elevation = coordinates[1]
        press = (self.get_highest_elevation()-elevation)*self.density*acceleration
        #print('   tank calculated pressure: ',str(self.get_highest_elevation()),'-', str(elevation),'*', str(self.density),'*',str(acceleration), ' = ', press)
        return press

    def get_bottom_pressure(self):
        '''
        Get pressure at bottom of tank.
        :return:
        '''

        return (self.get_highest_elevation() - self.get_lowest_elevation()) * self.density * self.acceleration + self.added_pressure

    def get_top_pressure(self):
        '''
        Get the pressure at the top of the tank.
        :return:
        '''

        return self.added_pressure

    def get_density(self):
        '''
        Get the tank density.
        :return:
        '''
        return self.density

    def get_content(self):
        '''
        Returnt the tank content type
        :return:
        '''
        return self.content

    def get_accelerations(self):
        '''
        Returns the defined accelerations
        :return:
        '''
        return (self.acc_static, self.acc_dyn_loaded,self.acc_dyn_ballast)

    def get_overpressure(self):
        '''
        Get the overpressure at tank top.
        :return:
        '''
        return self.added_pressure

    def get_parameters(self):
        '''
        Returns properties
        :return:
        '''
        # return_dict = {'comp_no':self.compartment_number, 'cells':self.cells, 'min_el':self.min_elevation,
        #                'max_el':self.max_elevation, 'content':self.content, 'added_press':self.added_pressure,
        #                'density':self.density, 'acc':{'static':self.acc_static, 'dyn_loaded':self.acc_dyn_loaded,
        #                                               'dyn_ballast':self.acc_dyn_ballast}}
        # return return_dict
        return self.properties

    def is_loaded_condition(self):
        '''
        Check to see if the tank shall be in cluded in loaded condition.
        self.tank_options = ['crude_oil', 'diesel', 'slop', 'ballast']
        :return:
        '''
        try: return self.content in self.all_types[0:4]
        except AttributeError: return False

    def is_ballast_condition(self):
        '''
        Check to see if the tank shall be in cluded in loaded condition.
        :return:
        '''
        try: return self.content == self.all_types[4]
        except AttributeError: return False

    def is_tank_test_condition(self):
        '''
        Check to see if the tank shall be in cluded in loaded condition.
        :return:
        '''
        try: return self.content == self.all_types
        except AttributeError: return False

    def get_condition(self):
        '''
        Returning the condition.
        self.load_conditions = ['loaded', 'ballast','tanktest']
        :return:
        '''
        try:
            if self.is_ballast_condition():
                return 'ballast'
            elif self.is_loaded_condition():
                return 'loaded'
            elif self.is_tank_test_condition():
                return 'tanktest'
        except AttributeError: return False

    def get_tank_dnv_minimum_pressure(self, lf_static, lf_enviromental):
        '''
        Calculating 4.3.7 and 4.3.8 and returning the highest of these pressures.
        :return:
        '''

        if self.is_loaded_condition():
            dyn_acc = self.acc_dyn_loaded
        elif self.is_ballast_condition():
            dyn_acc = self.acc_dyn_ballast
        else:
            dyn_acc = 0

        hop = self.get_highest_elevation()-self.get_lowest_elevation()

        #All tanks shall be designed for the following internal design pressure:
        p_4_3_7 = self.density * self.acc_static * hop *(lf_static+(dyn_acc/self.acc_static)*lf_enviromental)

        #For tanks where the air pipe may be filled during filling operations, the following additional internal
        #design pressure conditions shall be considered:

        p_4_3_8 = (self.density*self.acc_static*hop + self.get_overpressure())*lf_static

        return max(p_4_3_7, p_4_3_8)

class Combination():
    '''
    THIS CLASS IS CURRENTLY NOT USED. MAY NOT BE USED AT ALL. IT IS STUPID.
    This class cointaines the load combinations.   
    combination,self.active_line,compartment
    '''
    def __init__(self, object_line, comb_dict = None, tank_dict = None, load_dict = None):
        '''
        Input from main application is:
        line for this object
        tank_dict = {} #main tank dictionary (created when BFS search is executed for the grid) (comp# : TankObj)
        load_dict = {} #main load dictionary (created in separate load window (load# : [LoadObj, lines])
        comb_dict = {} #load combination dictionary (comb,line,load) : [DoubleVar(), DoubleVar], IntVar()]
        '''

        self.object_line = object_line

        self.comb_dict = comb_dict
        self.tank_dict = tank_dict
        self.load_dict = load_dict

        try: self.combination = comb_dict.keys()[0]
        except AttributeError : self.combination = None

        try: self.load_case = comb_dict.keys()[2]
        except AttributeError: self.load_case = None

        try: self.load_factor_static = comb_dict.values()[0]
        except AttributeError: self.load_factor_static = None

        try: self.load_factor_dynamic = comb_dict.values()[1]
        except AttributeError: self.load_factor_dynamic = None

        try: self.on_off = comb_dict.values()[2]
        except AttributeError: self.on_off = None

    def __str__(self):
        return 'NOT IMPLEMENTED'

    def get_load_factors(self):
        '''
        Get the tk.DoubleVar, tk.DoubleVar, tk.IntVar that is used in the load factor input and on/off.
        :return:
        '''
        return self.load_factor_static.get(), self.load_factor_dynamic.get(), self.on_off.get()

    def get_load_factor_static(self):
        '''
        Setting the the dynamic load factor.
        :return:
        '''
        return self.load_factor_static.get()

    def get_load_factor_dynamic(self):
        '''
        Setting the the dynamic load factor.
        :return:
        '''
        return self.load_factor_dynamic.get()

    def get_on_off(self, value):
        '''
        Setting the the dynamic load factor.
        :return:
        '''
        return self.on_off.get()

    def set_load_factor_static(self, value):
        '''
        Setting the the dynamic load factor.
        :return:
        '''
        self.load_factor_static = value

    def set_load_factor_dynamic(self, value):
        '''
        Setting the the dynamic load factor.
        :return:
        '''
        self.load_factor_dynamic = value

    def set_on_off(self, value):
        '''
        Setting the the dynamic load factor.
        :return:
        '''
        self.on_off= value

    def set_combination_dictionary(self, value):
        '''
        Setting the combination dictionary.
        :return:
        '''
        self.comb_dict = value

        assert tuple(value.keys())[0][1] == self.object_line, 'line is not correct!'
        assert len(tuple(value.keys())[0]) == 3 , 'length of key must be 3'
        assert len(tuple(value.values())[0]) == 3, 'length of values must be 3'

        try: self.set_load_factor_static(list(value.values())[0][0])
        except AttributeError: pass

        try: self.set_load_factor_dynamic(list(value.values())[0][1])
        except AttributeError: pass

        try: self.set_on_off(list(value.values())[0][2])
        except AttributeError: pass

    def set_load_dictionary(self, value):
        '''
        Setting the load dictionary.
        :return:
        '''
        self.load_dict = value

    def set_tank_dictionary(self, value):
        '''
        Setting the tank dictionary.
        :return:
        '''
        self.tank_dict = value

if __name__ == '__main__':
    import ANYstructure_local.example_data as ex

    for load, type in zip([Loads(ex.load_bottom), Loads(ex.load_side), Loads(ex.load_static), Loads(ex.load_slamming)],
                          ['BOTTOM', 'SIDE_SHELL', '', '']):
        print(load.get_calculated_pressure((10,10), 3, type))
