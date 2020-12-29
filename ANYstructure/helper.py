'''
Helper funations to be used.
'''

import math, copy, csv
print_it = False

def print_helper(properties, prop_text, units):
    '''
    Used to print out the properties
    '''
    dummy_i = 0
    print(' \n ')
    for prop_i in prop_text:
        print(str(prop_i) + ' ' + str(properties[dummy_i]) + ' ' + str(units[dummy_i]) )
        dummy_i += 1

def dist(p, q):
    return math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)

def get_num(x):
    try:
        return int(''.join(ele for ele in x if ele.isdigit() or ele == '.'))
    except ValueError:
        return x

def list_2_string(list):
    new_string = ''
    for item in list[0:-1]:
        new_string += str(item)
        new_string += ' , '
    new_string += str(list[-1])
    return new_string

def one_load_combination(line_name_obj, coord, defined_loads, load_condition,
                         defined_tanks, comb_name, acc, load_factors_all):
    '''
    Creating load combination.
    Inserted into self.line_to_struc index = 4
    "dnva", "line12", "static_ballast_10m"
    #load combination dictionary (comb,line,load) : [stat - DoubleVar(), dyn - DoubleVar], on/off - IntVar()]
    :return:
    '''

    if load_condition not in ['tanktest','manual', 'slamming']:
        return helper_dnva_dnvb(line_name_obj, coord, defined_loads, load_condition,
                                defined_tanks, comb_name, acc, load_factors_all)
    elif load_condition ==  'tanktest' and comb_name == 'tanktest':
        return helper_tank_test(line_name_obj, coord, defined_loads, load_condition,
                                defined_tanks, comb_name, acc, load_factors_all)
    elif load_condition == 'manual':
        return helper_manual(line_name_obj, comb_name,load_factors_all)
    elif load_condition == 'slamming':
        return helper_slamming(defined_loads)
    else:
        return [None, ' ']

def helper_dnva_dnvb(line_name_obj, coord, defined_loads, load_condition,
                         defined_tanks, comb_name, acc, load_factors_all, print_to_file = False):

    # calculate the defined loads
    calc_load, load_print = [], ['',]
    line_name = line_name_obj[0]
    structure_type = line_name_obj[1].get_structure_type()
    if print_it:
        load_print.append('Load calculation for '+line_name_obj[0] + ' ' + comb_name+ ' ' + load_condition)
    static_pressure,dynamic_pressure = 0,0

    if len(defined_loads) !=  0:
        for load in defined_loads :
            if load != None:
                if print_it:
                    load_print.append('LOAD NAME: '+' '+ comb_name+ ' '+ line_name+' '+ load.get_name())
                load_factors = load_factors_all[(comb_name, line_name, load.get_name())]
                # USE GET() (static,dyn, on/off)
                if load_condition == load.get_load_condition():
                    static_pressure = (load_factors[2].get())*(load_factors[0].get())\
                                      *load.get_calculated_pressure(coord, acc[0],structure_type)
                    dynamic_pressure = (load_factors[2].get())*(load_factors[1].get())\
                                       *load.get_calculated_pressure(coord, acc[1],structure_type)
                    if print_it:
                        load_print.append('load (NON-TANK) calculation for load condition:' + load_condition + ' - Load is: '+ \
                             load.get_name() + ' - Type is: ')
                        load_print.append('static with acc:'+ str(acc[0])+ ' is: '+str(load_factors[2].get())+'*'+\
                             str(load_factors[0].get())+'*'+\
                             str(load.get_calculated_pressure(coord, acc[0],structure_type))+ ' = '+ \
                             str(static_pressure))

                        load_print.append('dynamic with acc:'+ str(acc[1])+' is: '+str(load_factors[2].get())+'*'+\
                             str(load_factors[1].get())+'*'+\
                             str(load.get_calculated_pressure(coord, acc[1],structure_type))+ ' = '+ \
                             str(dynamic_pressure))
                    calc_load.append(static_pressure+dynamic_pressure)

    # calculate the tank loads

    if len(defined_tanks) != 0:
        temp_tank = {}

        for tank_name_obj in defined_tanks:
            temp_tank[tank_name_obj[0]] = 0

            load_factors = load_factors_all[(comb_name, line_name, tank_name_obj[0])]
            overpress_lf = [1.3,0]# if load_factors[0].get()==1.2 else [1,1.3]

            if load_condition == tank_name_obj[1].get_condition():
                # USE GET() (static,dyn, on/off)
                static_pressure = load_factors[2].get()*(load_factors[0].get())\
                                  *tank_name_obj[1].get_calculated_pressure(coord,acc[0])\
                                  +tank_name_obj[1].get_overpressure()*overpress_lf[0]
                dynamic_pressure = load_factors[2].get()*load_factors[1].get()\
                                   *tank_name_obj[1].get_calculated_pressure(coord,acc[1])\
                                   +tank_name_obj[1].get_overpressure()*overpress_lf[1]

                temp_tank[tank_name_obj[0]] = static_pressure + dynamic_pressure# .append((static_pressure + dynamic_pressure))
                if print_it:
                    load_print.append('load (TANK) calculation for load condition:'+ load_condition+ ' - Tank is: '+ tank_name_obj[0])
                    load_print.append('load factors : '+ str(load_factors[0].get())+str(load_factors[1].get())+str(load_factors[2].get()))
                    load_print.append('static: '+ str(load_factors[2].get())+ '*'+ str(load_factors[0].get()) + '*'+\
                          str(tank_name_obj[1].get_calculated_pressure(coord,acc[0]))+' + '+\
                          str(tank_name_obj[1].get_overpressure())+ '*'+str(overpress_lf[0])+ ' = '+str(static_pressure))
                    load_print.append('dynamic: '+str(load_factors[2].get())+ '*'+ str(load_factors[1].get())+  '*'+\
                          str(tank_name_obj[1].get_calculated_pressure(coord, acc[1]))+' + '+\
                          str(tank_name_obj[1].get_overpressure())+ '*'+str(overpress_lf[1])+' = '+ str(dynamic_pressure))
            # choosing the tank with the highest pressures

        if len(defined_loads) == 0:
            line_tank_pressure_calc = max([pressure for pressure in temp_tank.values()])
            highest_dnv_tank_pressure  = tank_name_obj[1].get_tank_dnv_minimum_pressure(load_factors[0].get(),
                                                                                        load_factors[1].get())
            line_dnv_tank_pressure = tank_name_obj[1].get_line_pressure_from_max_pressure(highest_dnv_tank_pressure,
                                                                                          coord)
            # if line_name_obj[0] == 'line29':
            #     print('Tank load to append is max( ',highest_tank_pressure_calc,highest_dnv_tank_pressure,')')
            highest_tank_pressure = max(line_tank_pressure_calc,line_dnv_tank_pressure)
            calc_load.append(-highest_tank_pressure if highest_tank_pressure else 0)
        else:
            pass
    if print_it:
        load_print.append('-----LOAD CALCULATION END, RESULT IS: ' + str(calc_load) +'-----')

    return [int(abs(sum(calc_load))), load_print]

def helper_slamming(defined_loads):

    # calculate the defined loads
    calc_load, load_print = [], ['',]
    if len(defined_loads) != 0:
        for load in defined_loads:
            if load != None and load.get_load_condition() == 'slamming':
                return [load.get_calculated_pressure(0, 0, 'slamming'), load_print]
    return [None, ' ']


def helper_tank_test(line_name_obj, coord, defined_loads, load_condition,
                                defined_tanks, comb_name, acc, load_factors_all):
    # calculate the defined loads
    calc_load, load_print = [], ['',]
    static_pressure, dynamic_pressure = 0, 0
    line_name = line_name_obj[0]
    structure_type = line_name_obj[1].get_structure_type()

    if len(defined_loads) != 0:
        for load in defined_loads:
            if load != None:
                load_factors = load_factors_all[(comb_name, line_name, load.get_name())]
                # USE GET() (static,dyn, on/off)
                if load_condition == load.get_load_condition():
                    static_pressure = (load_factors[2].get()) * (load_factors[0].get()) \
                                      * load.get_calculated_pressure(coord, acc[0], structure_type)
                    dynamic_pressure = (load_factors[2].get()) * (load_factors[1].get()) \
                                       * load.get_calculated_pressure(coord, acc[1], structure_type)
                    calc_load.append(static_pressure + dynamic_pressure)

    # calculate the tank loads
    temp_tank={}
    if len(defined_tanks) != 0:

        for tank_name_obj in defined_tanks:
            temp_tank[tank_name_obj[0]] = []

        for tank_name_obj in defined_tanks:
            load_factors = load_factors_all[(comb_name, line_name, tank_name_obj[0])]
            if print_it:
                load_print.append('tank test LF: '+ str(load_factors[0])+' '+str(load_factors[1])+' '+
                                  str(load_factors[2]))
                # USE GET() (static,dyn, on/off)
            overpress_lf = [1.3, 0] if load_factors[0].get() == 1.2 else [1, 0]
            static_pressure = (load_factors[2].get()) * (load_factors[0].get())\
                              * tank_name_obj[1].get_calculated_pressure(coord, acc[0])\
                              +tank_name_obj[1].get_overpressure()*overpress_lf[0]
            dynamic_pressure = (load_factors[2].get()) * (load_factors[1].get())\
                               * tank_name_obj[1].get_calculated_pressure(coord, acc[1])\
                               +tank_name_obj[1].get_overpressure()*overpress_lf[1]

            temp_tank[tank_name_obj[0]].append((static_pressure + dynamic_pressure))
        # choosing the tank with the highest pressures
        if len(defined_tanks) != 0:
            highest_tank_pressure = max([temp_tank[tank[0]] for tank in defined_tanks])
            calc_load.append(-highest_tank_pressure[0] if len(highest_tank_pressure) > 0 else 0)
        else:
            pass
    return [int(abs(sum(calc_load))), load_print]

def helper_manual(line_name, comb_name,load_factors_all):
    calc_load, load_print = [], ['',]
    load_factors = load_factors_all[(comb_name, line_name[0], 'manual')]
    if print_it:
        load_print.append('Manual pressure')
    return [load_factors[0].get() * load_factors[1].get() * load_factors[2].get(), load_print]

def helper_read_section_file(files, obj = None, to_json = False, to_csv = False):
    ''' Read a xml file. '''
    import json
    from xml.dom import minidom
    to_return_final, to_return, return_csv = list(),  dict(), list()
    if type(files) != list:
        files = [files,]
    for file in files:
        if file.endswith('xml'):
            xmldoc = minidom.parse(file)
            sectionlist = xmldoc.getElementsByTagName('section')
            sec_types = ('unsymmetrical_i_section', 'l_section', 'bar_section')

            for idx, sec_type in enumerate(sec_types):
                sec_type_get = xmldoc.getElementsByTagName(sec_type)
                if sec_types == []:
                    continue
                for item, itemdata in zip(sectionlist, sec_type_get):
                    if sec_type == sec_types[0]:
                        stf_web_h, stf_web_thk = 'h', 'tw'
                        stf_flange_width, stf_flange_thk  = 'bfbot', 'tfbot'
                        stiffener_type = 'T'
                        mult = 1/1000
                    elif sec_type == sec_types[1]:
                        stf_web_h, stf_web_thk = 'h', 'tw'
                        stf_flange_width, stf_flange_thk  = 'b', 'tf'
                        stiffener_type = 'L'
                        mult = 1/1000
                    elif sec_type == sec_types[2]:
                        stf_web_h, stf_web_thk = 'h', 'b'
                        stf_flange_width, stf_flange_thk  = None, None
                        stiffener_type = 'FB'
                        mult = 1 / 1000
                    section_name = item.getAttribute('name')
                    to_return[section_name] = {'stf_web_height': [float(itemdata.getAttribute(stf_web_h)) *mult, 'm'],
                                               'stf_web_thk': [float(itemdata.getAttribute(stf_web_thk)) *mult,'m'],
                                               'stf_flange_width': [0 if stf_flange_width is None else
                                               float(itemdata.getAttribute(stf_flange_width)) *mult,'m'],
                                               'stf_flange_thk': [0 if stf_flange_thk is None else
                                               float(itemdata.getAttribute(stf_flange_thk)) *mult, 'm'],
                                               'stf_type': [stiffener_type, '']}

                    return_csv.append([to_return[section_name][var][0] for var in ['stf_web_height', 'stf_web_thk',
                                                                                   'stf_flange_width', 'stf_flange_thk',
                                                                                   'stf_type']])
            if to_json:
                with open('sections.json', 'w') as file:
                    json.dump(to_return, file)
            if to_csv:
                with open('sections.csv', 'w', newline='') as file:
                    section_writer = csv.writer(file)
                    for line in return_csv:
                        section_writer.writerow(line)

        elif file.endswith('json'):
            with open(file, 'r') as json_file:
                to_return = json.load(json_file)

        elif file.endswith('csv'):
            with open(file, 'r') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                for idx, section in enumerate(csv_reader):


                    to_return[str(idx)] = {'stf_web_height': [float(section[0]), 'm'],
                                           'stf_web_thk': [float(section[1]),'m'],
                                           'stf_flange_width': [float(section[2]),'m'],
                                           'stf_flange_thk': [float(section[3]), 'm'],
                                           'stf_type': [section[4], '']}

    if to_json:
        with open('sections.json', 'w') as file:
            json.dump(to_return, file)

    if to_csv:
        with open('sections.csv', 'w', newline = '') as file:
            section_writer = csv.writer(file)
            for line in return_csv:
                section_writer.writerow(line)
    if obj is not None:  # This will return a modified object.
        if type(obj) is not list:
            obj = [obj, ]
            append_list = [[],]
        else:
            append_list = [list() for dummy in obj]
    else:
        append_list = list()

    for key, value in to_return.items():
        if obj is not None:  # This will return a modified object.
            for idx, iter_obj in enumerate(obj):
                new_obj = copy.deepcopy(iter_obj)
                new_obj_prop = new_obj.get_structure_prop()
                for prop_name, prop_val in value.items():
                    new_obj_prop[prop_name] = prop_val
                new_obj.set_main_properties(new_obj_prop)
                append_list[idx].append(new_obj)
        else:
            to_return_final.append(value)
    if len(append_list) == 1:
        to_return_final = append_list[0]
    elif len(append_list) == 0:
        pass
    elif len(append_list) > 1:
        to_return_final = append_list

    return to_return_final

def open_example_file(root_path = None):
    import os

    if os.path.isfile('sections.csv'):
        os.startfile('sections.csv')
    else:
        os.startfile(root_path + '/' + 'sections.csv')

def add_new_section(section_list, new_section):
    ''' Checking if a section is already in the list. '''
    existing_section = False

    for section in section_list:

        if section.__str__() == new_section.__str__():
            existing_section = True

    if existing_section == False:
        # print('The new section', new_section)
        # print('The section list', section_list)
        section_list.append(new_section)

    return section_list


if __name__ == '__main__':
    import ANYstructure.example_data as ex
    from pathlib import Path
    file = Path('C:/Users/nmm000756/Documents/GitHub/ANYstructure/ANYstructure/sections.json')
    all_returned = helper_read_section_file(file.name)

    import random
    print(random.choice(all_returned))
