'''
Helper funations to be used.
'''

import math, copy, csv

import numpy as np

print_it = True

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
                         defined_tanks, comb_name, acc, load_factors_all):

    # calculate the defined loads
    calc_load, load_print, prt_conditions = [], ['',], []
    line_name = line_name_obj[0]
    structure_type = line_name_obj[1].get_structure_type()
    if print_it:
        #load_print.append('Load calculation for '+line_name_obj[0] + ' ' + comb_name+ ' ' + load_condition)
        pass

    # if print_line != None and line_name == print_line:
    #     print('Load calculation for '+line_name_obj[0] + ' ' + comb_name+ ' ' + load_condition)

    if len(defined_loads) !=  0:
        for load in defined_loads :
            if comb_name+load_condition not in prt_conditions:
                load_print.append("Loads for condition: " + load_condition + ' - ' + comb_name +' ' + '\n')
                prt_conditions.append(comb_name+load_condition)
            if load != None:

                load_factors = load_factors_all[(comb_name, line_name, load.get_name())]
                # if print_it:
                #     if load_factors[0].get() != 0:
                #         load_print.append('LOAD NAME: '+' '+ comb_name+ ' '+ line_name+' '+ load.get_name()+'\n')
                # if load_factors[1].get() != 0:
                #     if load_factors[0].get() != 0:
                #         load_print.append('LOAD NAME: '+' '+ comb_name+ ' '+ line_name+' '+ load.get_name()+'\n')
                # USE GET() (static,dyn, on/off)

                if load_condition == load.get_load_condition():
                    static_pressure = (load_factors[2].get())*(load_factors[0].get())\
                                      *load.get_calculated_pressure(coord, acc[0],structure_type)
                    dynamic_pressure = (load_factors[2].get())*(load_factors[1].get())\
                                       *load.get_calculated_pressure(coord, acc[1],structure_type)
                    if print_it:
                        # load_print.append('load (NON-TANK) calculation for load condition:' + load_condition + ' - Load is: '+ \
                        #      load.get_name() + ' - Type is: \n')
                        if load_factors[0].get() != 0:
                            load_print.append(' static with acceleration: '+ str(acc[0])+ ' is: \n '+
                                              str(load_factors[2].get())+'*'+\
                                 str(load_factors[0].get())+'*'+\
                                 str(round(load.get_calculated_pressure(coord, acc[0],structure_type),1))+ ' = '+ \
                                 str(round(static_pressure,1))+'\n')
                        if load_factors[1].get() != 0:
                            load_print.append(' dynamic with acceleration: '+ str(acc[1])+' is: \n '+
                                              str(load_factors[2].get())+'*'+\
                                 str(load_factors[1].get())+'*'+\
                                 str(round(load.get_calculated_pressure(coord, acc[1],structure_type),1))+ ' = '+ \
                                 str(round(dynamic_pressure,1))+'\n')

                    calc_load.append(static_pressure+dynamic_pressure)

    # calculate the tank loads

    if len(defined_tanks) != 0:
        temp_tank = {}
        if comb_name + load_condition not in prt_conditions:
            load_print.append("Loads for condition: " + load_condition + ' - ' + comb_name + ' ' + '\n')
            prt_conditions.append(comb_name + load_condition)
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
                if print_it and tank_name_obj[0]+load_condition not in prt_conditions:
                    prt_conditions.append(tank_name_obj[0]+load_condition)
                    #load_print.append('load (TANK) calculation for load condition:'+ load_condition+ ' - Tank is: '+ tank_name_obj[0]+'\n')
                    #load_print.append('load factors : '+ str(load_factors[0].get())+str(load_factors[1].get())+str(load_factors[2].get())+'\n')
                    load_print.append('\n' + tank_name_obj[0] + ' - static: '+ str(load_factors[2].get())+ '*'+ str(load_factors[0].get()) + '*'+\
                          str(tank_name_obj[1].get_calculated_pressure(coord,acc[0]))+' + '+\
                          str(tank_name_obj[1].get_overpressure())+ '*'+str(overpress_lf[0])+ ' = '+str(static_pressure)+'\n')
                    load_print.append(tank_name_obj[0] + ' - dynamic: '+str(load_factors[2].get())+ '*'+ str(load_factors[1].get())+  '*'+\
                          str(tank_name_obj[1].get_calculated_pressure(coord, acc[1]))+' + '+\
                          str(tank_name_obj[1].get_overpressure())+ '*'+str(overpress_lf[1])+' = '+ str(dynamic_pressure)+'\n')
            # choosing the tank with the highest pressures

        if len(defined_loads) == 0:
            line_tank_pressure_calc = max([pressure for pressure in temp_tank.values()])

            #print('line_tank_pressure_calc', line_tank_pressure_calc)
            highest_dnv_tank_pressure  = tank_name_obj[1].get_tank_dnv_minimum_pressure(load_factors[0].get(),
                                                                                        load_factors[1].get())
            #print('highest_dnv_tank_pressure', highest_dnv_tank_pressure)
            line_dnv_tank_pressure = tank_name_obj[1].get_line_pressure_from_max_pressure(highest_dnv_tank_pressure,
                                                                                          coord)
            #print('line_dnv_tank_pressure', line_dnv_tank_pressure)
            # if line_name_obj[0] == 'line29':
            #     print('Tank load to append is max( ',highest_tank_pressure_calc,highest_dnv_tank_pressure,')')
            highest_tank_pressure = max(line_tank_pressure_calc,line_dnv_tank_pressure)
            calc_load.append(-highest_tank_pressure if highest_tank_pressure else 0)
            load_print.append('\nDNVGL-OS-C101 4.3.7 and 4.3.8 (Tank pressures) = '+ str(highest_tank_pressure)+'\n')
        else:
            pass
    if print_it:
        if len(calc_load) == 2:
            load_print.append('\nRESULT: ' + str(round(calc_load[0], 1)) +' + '+
                              str(round(calc_load[1])) + ' = ' + str(round(sum(calc_load),1)) +'\n')
        elif len(calc_load) == 1:
            load_print.append(
                '\nRESULT: ' + str(round(calc_load[0],1))+'\n')
        else:
            pass

        load_print.append('------------------------------------------------------------------\n')
    return [int(abs(sum(calc_load))), load_print]

def helper_slamming(defined_loads):

    # calculate the defined loads
    calc_load, load_print = [], ['',]
    if len(defined_loads) != 0:
        for load in defined_loads:
            if load != None and load.get_load_condition() == 'slamming':
                load_print.append('Slamming pressure: \n'+ str(load.get_calculated_pressure(0, 0, 'slamming'))+ ' Pa \n')
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
                    if print_it:
                        load_print.append(
                            'Tank test for: ' + load_condition[0] + '\n' + str(load_factors[2].get())+' * '+
                            str(load_factors[0].get()) +' * '+
                            str(round(load.get_calculated_pressure(coord, acc[0], structure_type),1)) + ' + ' +
                            str(round(dynamic_pressure)) + ' = ' + str(round(dynamic_pressure + static_pressure))+'\n')


    # calculate the tank loads
    temp_tank={}
    if len(defined_tanks) != 0:

        for tank_name_obj in defined_tanks:
            temp_tank[tank_name_obj[0]] = []

        for tank_name_obj in defined_tanks:
            load_factors = load_factors_all[(comb_name, line_name, tank_name_obj[0])]
            # if print_it:
            #     load_print.append('Tank test LF: '+ str(load_factors[0].get())+' '+str(load_factors[1].get())+' '+
            #                       str(load_factors[2].get())+'\n')
                # USE GET() (static,dyn, on/off)
            overpress_lf = [1.3, 0] if load_factors[0].get() == 1.2 else [1, 0]
            static_pressure = (load_factors[2].get()) * (load_factors[0].get())\
                              * tank_name_obj[1].get_calculated_pressure(coord, acc[0])\
                              +tank_name_obj[1].get_overpressure()*overpress_lf[0]
            dynamic_pressure = (load_factors[2].get()) * (load_factors[1].get())\
                               * tank_name_obj[1].get_calculated_pressure(coord, acc[1])\
                               +tank_name_obj[1].get_overpressure()*overpress_lf[1]

            temp_tank[tank_name_obj[0]].append((static_pressure + dynamic_pressure))
            if print_it:
                load_print.append(
                    'Tank test for: ' + tank_name_obj[0] + '\n' + str(load_factors[2].get()) + ' * ' +
                    str(load_factors[0].get()) + ' * ' +
                    str(round(tank_name_obj[1].get_calculated_pressure(coord, acc[0]), 1)) + ' + ' +
                    str(tank_name_obj[1].get_overpressure()) +' * ' + str(overpress_lf[0]) +
                    ' = ' + str(round(dynamic_pressure + static_pressure)) + '\n')
        # choosing the tank with the highest pressures
        if len(defined_tanks) != 0:
            highest_tank_pressure = max([temp_tank[tank[0]] for tank in defined_tanks])
            calc_load.append(-highest_tank_pressure[0] if len(highest_tank_pressure) > 0 else 0)
        else:
            pass
    return [int(abs(sum(calc_load))), load_print]

def helper_manual(line_name, comb_name,load_factors_all):
    calc_load, load_print = [], ['',]
    if (comb_name, line_name[0], 'manual') not in load_factors_all.keys():
        return [0, 'Manual pressure: 0']
    load_factors = load_factors_all[(comb_name, line_name[0], 'manual')]
    man_press = load_factors[0].get() * load_factors[1].get() * load_factors[2].get()
    if print_it:
        load_print.append('Manual pressure:\n'+ str(load_factors[0].get())+' * '+ str(load_factors[1].get())+' * '+
                          str(load_factors[2].get()) + ' = '+ str(man_press) +'\n')
    return [man_press, load_print]

def helper_read_section_file(files, obj = None, to_json = False, to_csv = None):
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
                    if section[4] in ['L-bulb', 'bulb', 'hp']:
                        to_return[str(idx)] = {'stf_web_height': [float(section[0]) - float(section[3]), 'm'],
                                               'stf_web_thk': [float(section[1]),'m'],
                                               'stf_flange_width': [float(section[2]),'m'],
                                               'stf_flange_thk': [float(section[3]), 'm'],
                                               'stf_type': [section[4], '']}
                    else:
                        to_return[str(idx)] = {'stf_web_height': [float(section[0]), 'm'],
                                               'stf_web_thk': [float(section[1]),'m'],
                                               'stf_flange_width': [float(section[2]),'m'],
                                               'stf_flange_thk': [float(section[3]), 'm'],
                                               'stf_type': [section[4], '']}

    if to_json:
        with open('sections.json', 'w') as file:
            json.dump(to_return, file)

    if to_csv is not None:
        with open(to_csv, 'w', newline = '') as file:
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

def plot_weights(time_stamp = None, cog = None, structure = None, weight = None):
    if __name__ == '__main__':
        cog = [[22.15329254, 12.24742235],
               [22.1937807, 12.1975691],
               [22.24684556, 12.15423614],
               [22.27489223, 12.09378247],
               [22.29086617, 12.03458725],
               [22.29559601, 11.97667798],
               [22.58758899, 11.739118],
               [22.34550004, 11.936077],
               [22.39332625, 11.96360235],
               [22.43016887, 11.99128875],
               [22.29320631, 12.02004097],
               [22.2458229, 11.99243978],
               [22.20984338, 11.96499817]]
        cog = np.array(cog)
        structure = {'plates': [18.0, 25.0, 12.0, 20.0, 14.0, 30.0, 15.0],
                     'beams': ['T_400_0x12_0__200_0x20_0', 'T_400_0x12_0__250_0x14_0', 'T_400_0x12_0__250_0x12_0',
                               'T_400_0x12_0__200_0x18_0', 'T_400_0x12_0__150_0x20_0', 'T_500_0x12_0__150_0x20_0',
                               'T_340_0x12_0__200_0x20_0', 'T_340_0x12_0__150_0x16_0', 'T_250_0x12_0__150_0x14_0',
                               'T_450_0x12_0__150_0x20_0', 'T_375_0x12_0__150_0x18_0', 'T_500_0x12_0__150_0x25_0',
                               'T_325_0x12_0__150_0x16_0', 'FB_250_0x18_0', 'FB_400_0x18_0',
                               'T_350_0x12_0__150_0x20_0', 'T_320_0x12_0__150_0x20_0', 'T_300_0x12_0__150_0x20_0']}

        time_stamp = [18920.477643045164, 18920.477684256162, 18920.477721255855, 18920.477761896746, 18920.477798285963,
                      18920.477841150896, 18920.4778763735, 18920.477939357952, 18920.47800752034, 18920.47808087777,
                      18920.478203353003, 18920.478237156338, 18920.47826686926]
        weight = [0.97156037, 0.97553128, 0.979408, 0.97625964, 0.97319636, 0.97021818,
                  1., 0.97518182, 0.97234545, 0.96950909, 0.97546545, 0.97830182,
                  0.98113818]

    import matplotlib.dates as mdate
    from matplotlib import pyplot as plt
    from matplotlib.gridspec import GridSpec

    pl_and_bm = [['', ''] for dummy in range(max(len(list(structure.values())[0]), len(list(structure.values())[1])))]

    for key, value in structure.items():
        for idx, val in enumerate(value):
            if key == 'plates':
                pl_and_bm[idx][0] = str(val) + ' mm'
            else:
                pl_and_bm[idx][1] = val

    fig = plt.figure(figsize=(14, 8))
    gs = GridSpec(2, 3, figure=fig)

    time_stamp = [mdate.epoch2num(val) for val in time_stamp]

    ax3 = plt.subplot(gs[1, 0:2])
    plt.plot(time_stamp, weight, 'tab:green')

    ax1 = plt.subplot(gs[0, 0], sharex=ax3)
    plt.plot(time_stamp, cog[:, 0])

    ax2 = plt.subplot(gs[0, 1], sharex=ax3)
    plt.plot(time_stamp, cog[:, 1], 'tab:orange')

    ax4 = plt.subplot(gs[0:2, 2])
    ax4.set_axis_off()
    table1 = plt.table(cellText=pl_and_bm, colLabels = ['Plates in model', 'Beams in model'],loc='center')
    table1.auto_set_column_width((0,1))
    table1.scale(1,1.5)
    # ax5 = plt.subplot(gs[0:2, 3])
    # ax5.set_axis_off()
    # table2 = plt.table(cellText=structure['beams'], colLabels = ['Beams in model'],loc='center')
    # table2.scale(1,1.5)
    # table2.auto_set_column_width(0)
    # Choose your xtick format string
    date_fmt = '%d-%m-%y %H:%M:%S'

    # Use a DateFormatter to set the data to the correct format.
    date_formatter = mdate.DateFormatter(date_fmt)
    ax1.xaxis.set_major_formatter(date_formatter)
    ax2.xaxis.set_major_formatter(date_formatter)
    ax3.xaxis.set_major_formatter(date_formatter)
    ax1.set_title('COG X')
    ax2.set_title('COG Y')
    ax3.set_title('Total weight / max(total weight)')

    fig.suptitle('Developement of weight and COG')

    # Sets the tick labels diagonal so they fit easier.
    fig.autofmt_xdate()

    plt.tight_layout()
    plt.show()

def helper_cylinder_stress_to_force_to_stress(stresses = None, forces = None, geometry = None, shell_t = 0,
                                              shell_radius = 0, shell_spacing = 0,
                                              hw = 0, tw = 0, b = 0, tf = 0, CylinderAndCurvedPlate = None,
                                              conical = False, psd = 0, cone_r1 = 0, cone_r2 = 0, cone_alpha = 0,
                                              shell_lenght_l = 0):
    
    
    A = 0 if geometry in [1, 2] else hw * tw + b * tf
    eq_thk = shell_t if geometry in [1, 2] else shell_t + A/shell_spacing

    Itot = CylinderAndCurvedPlate.get_Itot(hw=0 if geometry in [1, 2] else hw,
                                           tw=0 if geometry in [1, 2] else tw,
                                           b=0 if geometry in [1, 2] else b,
                                           tf=0 if geometry in [1, 2] else tf,
                                           r=shell_radius,
                                           s=shell_spacing,
                                           t=shell_t)

    if forces is not None and stresses is None:
        if not conical:
            Nsd, Msd, Tsd, Qsd = forces
            sasd = (Nsd / 2) / (math.pi * shell_radius * eq_thk) * 1000
            smsd = (Msd/ Itot) * \
                   (shell_radius + shell_t / 2) * 1000000
            tTsd = (Tsd* 10 ** 6) / (2 * math.pi * shell_t * math.pow(shell_radius, 2))
            tQsd = Qsd / (math.pi * shell_radius * shell_t) * 1000
            shsd = 0
            return sasd, smsd, tTsd, tQsd, shsd
        else:
            Nsd, M1sd, M2sd, Tsd, Q1sd, Q2sd = forces
            re = (cone_r1+cone_r2) / (2*math.cos(math.radians(cone_alpha)))
            le = shell_lenght_l / math.cos(math.radians(cone_alpha))
            te = shell_t *math.cos(math.radians(cone_alpha))
            sasd = psd*re/2*te + Nsd/(2*math.pi*re*te) * 1000
            smsd = ((M1sd*math.sin(math.radians(cone_alpha)) / (math.pi*math.pow(re,2)*te)) + \
                   (M2sd*math.cos(math.radians(cone_alpha)) / (math.pi*math.pow(re,2)*te))) * 1000000
            shsd = psd*re/te
            tTsd = Tsd/(2*math.pi*math.pow(re,2)*te)
            tQsd = -(Q1sd*math.cos(math.radians(cone_alpha)) / (math.pi*re*te)) + \
                   (Q2sd*math.sin(math.radians(cone_alpha)) / (math.pi*re*te))
            return sasd, smsd, tTsd, tQsd, shsd

    else:
        if not conical:
            sasd, smsd, tTsd, tQsd, shsd = stresses
            Nsd = (sasd * 2 * math.pi * shell_radius * eq_thk) / 1000
            Msd = (smsd / (shell_radius * shell_t / 2)) * Itot / 1000000
            Tsd = tTsd * 2 * math.pi * shell_t * math.pow(shell_radius, 2) / 1000000
            Qsd = tQsd * math.pi * shell_radius * shell_t / 1000
        else:
            re = (cone_r1+cone_r2) / (2*math.cos(math.radians(cone_alpha)))
            le = shell_lenght_l / math.cos(math.radians(cone_alpha))
            te = shell_t *math.cos(math.radians(cone_alpha))
            Itot = CylinderAndCurvedPlate.get_Itot(hw=0,
                                                   tw=0 ,
                                                   b=0 ,
                                                   tf=0,
                                                   r=re,
                                                   s=shell_spacing,
                                                   t=te)
            sasd, smsd, tTsd, tQsd, shsd = stresses
            Nsd = (sasd * 2 * math.pi * re * te) / 1000
            Msd = (smsd / (re * te / 2)) * Itot / 1000000
            Tsd = tTsd * 2 * math.pi * te * math.pow(re, 2) / 1000000
            Qsd = tQsd * math.pi * re * te/ 1000

        return Nsd, Msd, Tsd, Qsd, shsd


if __name__ == '__main__':
    from tkinter import *



    class AllTkinterWidgets:
        def __init__(self, master):
            frame = Frame(master, width=500, height=400, bd=1)
            frame.pack()

            iframe5 = Frame(frame, bd=2, relief=RAISED)
            iframe5.pack(expand=1, fill=X, pady=10, padx=5)
            c = Canvas(iframe5, bg='white', width=340, height=200)
            c.pack()

            height = 150
            radius = 150
            offset_oval = 30
            start_x_cyl = 150
            start_y_cyl = 20
            coord1 = start_x_cyl, start_y_cyl, start_x_cyl + radius, offset_oval
            coord2 = start_x_cyl, start_y_cyl + height, start_x_cyl + radius, offset_oval+ height

            arc_1 = c.create_oval(coord1, width = 5, fill = 'grey90')
            arc_2 = c.create_arc(coord2, extent = 180, start = 180,style=ARC, width = 3)

            line1 = c.create_line(coord1[0], coord1[1]+offset_oval/4,
                                  coord1[0], coord1[1]+height+offset_oval/4,
                                  width = 3)
            line2 = c.create_line(coord1[0]+radius, coord1[1]+offset_oval/4,
                                  coord1[0]+radius, coord1[1]+height+offset_oval/4,
                                  width = 3)
            num_stf = 10
            for line_num in range(1,num_stf,1):
                angle = 180 - 180/(num_stf) *line_num
                arc_x, arc_y = 1*math.cos(math.radians(angle)), 0.5*math.sin(math.radians(angle))
                arc_x = (arc_x + 1)/2

                line1 = c.create_line(coord1[0] + radius*arc_x,
                                      coord1[1] +2*arc_y*offset_oval/3,
                                      coord1[0] + radius*arc_x,
                                      coord1[1] + height +2*arc_y*offset_oval/3,fill = 'blue')
            num_ring_stiff = 5
            for ring_stf in range(1,num_ring_stiff+1,1):
                coord3 = coord1[0], coord1[1]+(height/(num_ring_stiff+1))*ring_stf,  \
                         start_x_cyl +radius, coord1[3]+ (height/(num_ring_stiff+1))*ring_stf,
                arc_2 = c.create_arc(coord3, extent=180, start=180, style=ARC, width=2,fill = 'orange', outline = 'orange')

            num_ring_girder = 1
            for ring_girder in range(1, num_ring_girder+1,1):
                coord3 = coord1[0], coord1[1]+(height/(num_ring_girder+1))*ring_girder,  \
                         start_x_cyl+ radius, coord1[3]+ (height/(num_ring_girder+1))*ring_girder,
                arc_2 = c.create_arc(coord3, extent=180, start=180, style=ARC, width=4, fill = 'grey', outline = 'grey')

            iframe5.pack(expand=1, fill=X, pady=10, padx=5)


    root = Tk()
    # root.option_add('*font', ('verdana', 10, 'bold'))
    all = AllTkinterWidgets(root)
    root.title('Tkinter Widgets')
    root.mainloop()
