#Optimize structure
import numpy as np
import ANYstructure_local.calc_structure as calc
import itertools as it
import time
import random
import copy
import ANYstructure_local.helper as hlp
from multiprocessing import Pool, cpu_count
import math
from math import floor
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from tkinter.filedialog import asksaveasfilename
import csv

def run_optmizataion(initial_structure_obj=None, min_var=None, max_var=None, lateral_pressure=None,
                     deltas=None, algorithm='anysmart', trials=30000, side='p',
                     const_chk = (True,True,True,True,True,True, True, False, False, False),
                     pso_options = (100,0.5,0.5,0.5,100,1e-8,1e-8), is_geometric=False, fatigue_obj = None ,
                     fat_press_ext_int = None,
                     min_max_span = (2,6), tot_len = None, frame_height = 2.5, frame_distance = None,
                     slamming_press = 0, predefined_stiffener_iter = None, processes = None, use_weight_filter = True,
                     load_pre = False, opt_girder_prop = None, puls_sheet = None, puls_acceptance = 0.87,
                     fdwn = 1, fup = 0.5, ml_algo = None, cylinder = False):
    '''
    The optimazation is initiated here. It is called from optimize_window.
    :param initial_structure_obj:
    :param min_var:
    :param max_var:
    :param lateral_pressure:
    :param deltas:
    :param algorithm:
    :param init_weigth:
    :param pso_options:
    :return:
    '''
    init_filter_weight = float('inf')

    if is_geometric:
        fat_dict = [None if this_fat is None else this_fat.get_fatigue_properties() for this_fat in fatigue_obj]
    else:
        fat_dict = None if fatigue_obj is None else fatigue_obj.get_fatigue_properties()

    if use_weight_filter and not cylinder:

        if is_geometric or algorithm == 'pso':
            init_filter_weight = float('inf')
        else:
            predefined_stiffener_iter = None if predefined_stiffener_iter is None else predefined_stiffener_iter

            init_filter_weight = get_initial_weight(obj=initial_structure_obj,
                                                    lat_press=lateral_pressure,
                                                    min_var=min_var, max_var=max_var, deltas=deltas,
                                                    trials= 30000 if predefined_stiffener_iter is None else
                                                    len(predefined_stiffener_iter),
                                                    fat_dict=fat_dict,
                                                    fat_press=None if fat_press_ext_int is None else fat_press_ext_int,
                                                    predefined_stiffener_iter = predefined_stiffener_iter,
                                                    slamming_press=slamming_press, fdwn = fdwn, fup = fup,
                                                    ml_algo = ml_algo)

    if cylinder:
        to_return = any_smart_loop_cylinder(min_var=min_var, max_var=max_var, deltas=deltas,
                                            initial_structure_obj=initial_structure_obj,
                                            use_weight_filter = use_weight_filter)
        return to_return

    elif algorithm == 'anysmart' and not is_geometric:
        to_return = any_smart_loop(min_var, max_var, deltas, initial_structure_obj, lateral_pressure,
                                   init_filter_weight, side=side, const_chk=const_chk, fat_dict=fat_dict,
                                   fat_press=fat_press_ext_int,slamming_press=slamming_press,
                                   predefiened_stiffener_iter=predefined_stiffener_iter, puls_sheet = puls_sheet,
                                   puls_acceptance = puls_acceptance, fdwn = fdwn, fup = fup, ml_algo=ml_algo)
        return to_return
    elif algorithm == 'anysmart' and is_geometric:
        return geometric_summary_search(min_var= min_var, max_var=max_var, deltas= deltas,
                                        initial_structure_obj= initial_structure_obj, lateral_pressure=lateral_pressure,
                                        init_filter= init_filter_weight, side= side, const_chk= const_chk,
                                        fat_obj=  fatigue_obj, fat_press= fat_press_ext_int, min_max_span= min_max_span,
                                        tot_len= tot_len, frame_distance = frame_distance,
                                        algorithm= 'anysmart', predefiened_stiffener_iter=predefined_stiffener_iter,
                                        slamming_press = slamming_press, load_pre = load_pre,
                                        opt_girder_prop = opt_girder_prop, ml_algo=ml_algo)
    elif algorithm == 'anydetail' and not is_geometric:
        return any_optimize_loop(min_var, max_var, deltas, initial_structure_obj, lateral_pressure,init_filter_weight,
                                 side=side, const_chk=const_chk, fat_dict=fat_dict, fat_press=fat_press_ext_int,
                                 slamming_press=slamming_press)
    elif algorithm == 'random' and not is_geometric:
        return get_random_result(initial_structure_obj,lateral_pressure,min_var,max_var,deltas,trials=trials,
                                 side=side, const_chk=const_chk, fat_dict=fat_dict,fat_press=fat_press_ext_int)
    elif algorithm == 'random_no_delta' and not is_geometric:
        return get_random_result_no_bounds(initial_structure_obj, lateral_pressure, min_var, max_var, trials=trials,
                                           side=side, const_chk=const_chk)

    # elif algorithm == 'pso' and is_geometric:
    #     return geometric_summary_search(min_var,max_var,deltas, initial_structure_obj,lateral_pressure,
    #                                     init_filter_weight,side,const_chk,pso_options,fatigue_obj,fat_press_ext_int,
    #                                     min_max_span,tot_len,frame_height,frame_cross_a, 'pso')
    else:
        return None

def any_optimize_loop(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                      side='p',const_chk=(True,True,True,True,True,False), fat_dict = None, fat_press = None,
                      slamming_press = 0):
    '''
    Calulating initial values.
    :param min:
    :param max:
    :return:
    '''
    ass_var = []
    plot_x,plot_y = [],[]
    plt.xlabel('#')
    plt.ylabel('weigth [kg]')
    plt.title('ANYdetail brute force results')
    plt.grid(True)
    plt.draw()
    iter_count = 0
    min_weight = init_filter
    main_fail = list()
    for spacing in np.arange(min_var[0],max_var[0]+deltas[0],deltas[0]):
        for plate_thk in np.arange(min_var[1],max_var[1]+deltas[1],deltas[1]):
            for stf_web_h in np.arange(min_var[2],max_var[2]+deltas[2],deltas[2]):
                for stf_web_thk in np.arange(min_var[3],max_var[3]+deltas[3],deltas[3]):
                    for stf_flange_width in np.arange(min_var[4],max_var[4]+deltas[4],deltas[4]):
                        for stf_flange_thk in np.arange(min_var[5],max_var[5]+deltas[5],deltas[5]):
                            var_x = np.array([spacing, plate_thk, stf_web_h, stf_web_thk, stf_flange_width,
                                              stf_flange_thk,min_var[6],min_var[7]])
                            check = any_constraints_all(var_x,initial_structure_obj,lat_press=lateral_pressure,
                                                        init_weight=min_weight,side=side,chk=const_chk,
                                                        fat_dict = fat_dict, fat_press = fat_press,
                                                        slamming_press=slamming_press)
                            if check[0] is not False:
                                current_weight = calc_weight(var_x)
                                if current_weight <= min_weight:
                                    iter_count+=1
                                    min_weight = current_weight
                                    ass_var = var_x
                                main_fail.append(check)
                            else:
                                main_fail.append(check)
    if ass_var is None:
        return None, None, None, False, main_fail

    new_struc_obj = create_new_structure_obj(initial_structure_obj,[item for item in ass_var])
    new_calc_obj = create_new_calc_obj(initial_structure_obj,[item for item in ass_var])[0]

    return new_struc_obj, new_calc_obj, fat_dict, True, main_fail

def any_smart_loop(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                   side='p',const_chk=(True,True,True,True,True,True,True, False, False,False), fat_dict = None,
                   fat_press = None,
                   slamming_press = 0, predefiened_stiffener_iter = None, processes = None,
                   puls_sheet = None, puls_acceptance = 0.87, fdwn = 1, fup = 0.5, ml_algo = None):
    '''
    Trying to be smart
    :param min_var:
    :param max_var:
    :param initial_structure:
    :return:
    '''


    if predefiened_stiffener_iter is None:
        structure_to_check = any_get_all_combs(min_var, max_var, deltas)
    else:
        structure_to_check = any_get_all_combs(min_var, max_var, deltas,predef_stiffeners=[item.get_tuple() for item
                                                                                           in predefiened_stiffener_iter])

    main_result = get_filtered_results(structure_to_check, initial_structure_obj,lateral_pressure,
                                       init_filter_weight=init_filter, side=side,chk=const_chk, fat_dict=fat_dict,
                                       fat_press=fat_press, slamming_press=slamming_press, processes=processes,
                                       puls_sheet = puls_sheet, puls_acceptance = puls_acceptance, ml_algo=ml_algo)

    main_iter = main_result[0]
    main_fail = main_result[1]

    ass_var=None
    current_weight = float('inf')
    for item in main_iter:
        main_fail.append(item)
        item_weight = calc_weight(item[2])
        if item_weight < current_weight:
            ass_var = item[2]
            current_weight = item_weight

    if ass_var == None:
        return None, None, None, False, main_fail

    if len(ass_var) == 8:
        ass_var = [round(item, 10) for item in ass_var[0:8]]
    else:
        ass_var = [round(item, 10) for item in ass_var[0:8]] + [ass_var[8]]

    new_struc_obj = create_new_structure_obj(initial_structure_obj,ass_var, fdwn = fdwn, fup = fup)
    new_calc_obj = create_new_calc_obj(initial_structure_obj,ass_var, fdwn = fdwn, fup = fup)[0]

    return new_struc_obj, new_calc_obj, fat_dict, True, main_fail

def any_smart_loop_cylinder(min_var,max_var,deltas,initial_structure_obj,lateral_pressure = None, init_filter = float('inf'),
                   side='p',const_chk=(True,True,True,True,True,True,True, False, False,False), fat_dict = None,
                   fat_press = None, slamming_press = 0, predefiened_stiffener_iter = None, processes = None,
                   fdwn = 1, fup = 0.5, ml_algo = None, use_weight_filter = True):

    combs = list()

    # Creating the individual combinations for Shell, LongStf, RingStf and RingFrame

    for idx, str_type in enumerate(range(len(min_var))):

        if predefiened_stiffener_iter is None:
            structure_to_check = any_get_all_combs(min_var[idx], max_var[idx], deltas[idx])

        else:
            structure_to_check = any_get_all_combs(min_var[idx], max_var[idx], deltas[idx],
                                                   predef_stiffeners= [item.get_tuple() for item in predefiened_stiffener_iter])
        combs.append(structure_to_check)


    # Combining the individual components.

    final_comb, iter_vals = list(), list()
    for shell in combs[0]:
        for long in combs[1]:
            for ring_stf in combs[2]:
                for ring_frame in combs[3]:
                    final_comb.append([[shell, long, ring_stf, ring_frame], initial_structure_obj])

    # Weight filter
    min_weight = float('inf')
    if use_weight_filter:
        to_check = [random.choice(final_comb) + [float('inf')] for dummy in range(10000)]
        with Pool(processes=max(cpu_count() - 1, 1)) as my_process:
            res_pre = my_process.starmap(any_constraints_cylinder, to_check)
        for chk_res in res_pre :
            if chk_res[0]:
                current_weight = calc_weight_cylinder(chk_res[2])
                if current_weight < min_weight:
                    min_weight = current_weight
    else:
        min_weight = False

    final_comb_inc_weight = list()
    for val in final_comb:
        final_comb_inc_weight.append(val + [min_weight])

    t1 = time.time()
    with Pool(processes = max(cpu_count()-1,1)) as my_process:
        res_pre = my_process.starmap(any_constraints_cylinder, final_comb_inc_weight)

    check_ok, check_not_ok = list(), list()
    for item in res_pre:
        if item[0] is False:
            check_not_ok.append(item)
        else:
            check_ok.append(item)

    main_iter = check_ok
    main_fail = check_not_ok

    ass_var = None
    current_weight = float('inf')
    for item in main_iter:
        main_fail.append(item)
        item_weight = calc_weight_cylinder(item[2])
        if item_weight < current_weight:
            ass_var = item[2]
            current_weight = item_weight

    if ass_var == None:
        return None, None, None, False, main_fail

    new_cylinder_obj = create_new_cylinder_obj(initial_structure_obj, ass_var)

    #return new_struc_obj, new_calc_obj, fat_dict, True, main_fail
    return new_cylinder_obj, main_fail


def any_smart_loop_geometric(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                             side='p',const_chk=(True,True,True,True,True,True), fat_obj = None, fat_press = None,
                             slamming_press = None, predefiened_stiffener_iter=None, processes = None, ml_algo = None):
    ''' Searching multiple sections using the smart loop. '''

    all_obj = []
    idx = 0
    for struc_obj, lat_press, fatigue_obj, fatigue_press, slam_press in zip(initial_structure_obj, lateral_pressure,
                                                                            fat_obj, fat_press, slamming_press):
        #print(predefiened_stiffener_iter)
        if predefiened_stiffener_iter is not None:
            this_predefiened_objects = hlp.helper_read_section_file(predefiened_stiffener_iter, struc_obj)
        else:
            this_predefiened_objects = None

        opt_obj = any_smart_loop(min_var = min_var,max_var = max_var,deltas = deltas,initial_structure_obj = struc_obj,
                                 lateral_pressure = lat_press, init_filter = init_filter, side=side,
                                 const_chk=const_chk,
                                 fat_dict = None if fatigue_obj is None else fatigue_obj.get_fatigue_properties(),
                                 fat_press = None if fatigue_press is None else fatigue_press,
                                 slamming_press = 0 if slam_press is None else slam_press,
                                 predefiened_stiffener_iter=this_predefiened_objects, processes=processes,
                                 ml_algo=ml_algo)

        all_obj.append(opt_obj)
        idx += 1

    return all_obj

def geometric_summary_search(min_var=None,max_var=None,deltas = None, initial_structure_obj=None,lateral_pressure=None,
                             init_filter = float('inf'),side='p',const_chk=(True,True,True,True, True, True),
                             pso_options=(100,0.5,0.5,0.5,100,1e-8,1e-8), fat_obj = None, fat_press = None,
                             min_max_span = (2,6), tot_len = None, frame_distance = None,
                             algorithm = 'anysmart', predefiened_stiffener_iter=None, reiterate = True,
                             processes = None, slamming_press = None, load_pre = False, opt_girder_prop = None,
                             ml_algo = None):

    '''Geometric optimization of all relevant sections. '''
    # Checking the number of initial objects and adding if number of fraction is to be changed.
    # print('Min/max span is', min_max_span)
    found_max, found_min = False, False
    for frames in range(1,100):
        frame_count = frames
        if tot_len/frames <= min_max_span[1] and found_min is False:
            min_frame_count = frame_count - 1
            found_min = True
        if tot_len/frames <= min_max_span[0] and found_max is False:
            max_frame_count = frame_count - 1
            found_max = True
        if found_min and found_max:
            break

    results = {}
    # print('Frame count min/max: ', min_frame_count, max_frame_count)
    # print('Initial objects: ', [print(type(obj)) for obj in initial_structure_obj])
    # print('Initial lateral: ', lateral_pressure)
    working_objects = {}
    working_lateral = {}
    working_fatigue = {}
    working_fatigue_press = {}
    working_slamming = {}

    for no_of_fractions in range(min_frame_count+1, max_frame_count+1):
        # Create fraction varables
        frac_var,min_frac,max_frac = [], [], []

        for var in range(no_of_fractions):
            # Frame height is a interpolation between height at start and end.
            frac_var.append(1/no_of_fractions)
            working_objects[no_of_fractions] = list(initial_structure_obj)
            working_lateral[no_of_fractions] = list(lateral_pressure)
            working_fatigue[no_of_fractions] = list(fat_obj)
            working_fatigue_press[no_of_fractions] = list(fat_press)
            working_slamming[no_of_fractions] = list(slamming_press)
            similar_count = len(working_objects[no_of_fractions])
            tick_tock = True

            while similar_count != no_of_fractions*2:

                if similar_count > no_of_fractions*2:
                    for var_dict in [working_objects, working_lateral, working_fatigue,
                                     working_fatigue_press, working_slamming]:
                        if tick_tock:
                            lower_idx = 0
                            upper_idx = int(floor(len(working_objects[no_of_fractions]) / 2))
                            tick_tock = False
                        else:
                            lower_idx = int(len(working_objects[no_of_fractions]) / 2) - 1
                            upper_idx = -1
                            tick_tock = True

                        var_dict[no_of_fractions].pop(lower_idx)
                        var_dict[no_of_fractions].pop(upper_idx)
                    similar_count -= 2
                else:
                    if tick_tock:
                        lower_idx = 0
                        upper_idx = int(len(working_objects[no_of_fractions])/2)
                        tick_tock = False
                    else:
                        lower_idx = int(len(working_objects[no_of_fractions])/2) - 1
                        upper_idx = -1
                        tick_tock = True
                    #print(no_of_fractions, int(ceil(len(working_objects[no_of_fractions])/2)))

                    obj_start, obj_stop = copy.deepcopy(working_objects[no_of_fractions][lower_idx]),\
                                          copy.deepcopy(working_objects[no_of_fractions][upper_idx])

                    fat_obj_start, fat_obj_stop = copy.deepcopy(working_fatigue[no_of_fractions][lower_idx]), \
                                                  copy.deepcopy(working_fatigue[no_of_fractions][upper_idx])
                    lat_start, lat_stop = working_lateral[no_of_fractions][lower_idx], \
                                          working_lateral[no_of_fractions][upper_idx]
                    fat_press_start, fat_press_stop = working_fatigue_press[no_of_fractions][lower_idx], \
                                                      working_fatigue_press[no_of_fractions][upper_idx]
                    slam_start, slam_stop = working_slamming[no_of_fractions][lower_idx], \
                                            working_slamming[no_of_fractions][upper_idx]
                    # if no_of_fractions == 11:
                    #     print('Tick/tock', tick_tock, 'lower/opper idx', lower_idx, upper_idx)

                    for work, work_input in zip([working_objects[no_of_fractions], working_lateral[no_of_fractions],
                                                 working_fatigue[no_of_fractions],
                                                 working_fatigue_press[no_of_fractions],
                                                 working_slamming[no_of_fractions]],
                                                [(obj_start, obj_stop), (lat_start, lat_stop),
                                                 (fat_obj_start, fat_obj_stop), (fat_press_start, fat_press_stop),
                                                 (slam_start, slam_stop)]):
                        # First iteration tick_tock true, second tick_tock false
                        if not tick_tock:
                            lower_idx = lower_idx
                            upper_idx = upper_idx + 1
                        else:
                            lower_idx = lower_idx + 1
                            upper_idx = -1
                        work.insert(lower_idx, work_input[0])
                        work.insert(upper_idx, work_input[1])
                    similar_count += 2
                # if no_of_fractions == 11:
                #     [print(item.get_structure_type()) for item in working_objects[no_of_fractions]]
                #     print('')
        for no_of_fractions, struc_objects in working_objects.items():
            for struc_obj in struc_objects:
                struc_obj.set_span(tot_len/no_of_fractions)

        solution_found, iterations = False, 0

        while not solution_found:
            iterations += 1
            if iterations != 1:
                min_var[0:6] += deltas/2
                max_var[0:6] -= deltas/2

            if algorithm == 'anysmart':
                if load_pre:
                    import pickle
                    with open('geo_opt_2.pickle', 'rb') as file:
                        opt_objects = pickle.load(file)[no_of_fractions][1]
                else:

                    opt_objects = any_smart_loop_geometric(min_var=min_var,max_var=max_var,deltas=deltas,
                                                           initial_structure_obj=working_objects[no_of_fractions],
                                                           lateral_pressure=working_lateral[no_of_fractions],
                                                           init_filter = init_filter,side=side,const_chk=const_chk,
                                                           fat_obj = working_fatigue[no_of_fractions],
                                                           slamming_press = working_slamming[no_of_fractions],
                                                           fat_press=working_fatigue_press[no_of_fractions],
                                                           predefiened_stiffener_iter = predefiened_stiffener_iter,
                                                           ml_algo=ml_algo)


            # Finding weight of this solution.

            tot_weight, frame_spacings, valid, width, weight_details = 0, [None for dummy in range(len(opt_objects))], \
                                                                       True, 10, {'frames': list(), 'objects': list(),
                                                                                  'scales': list()}

            #print('Weight for', no_of_fractions)
            for count, opt in enumerate(opt_objects):
                obj = opt[0]

                if opt[3]:
                    weigth_to_add = calc_weight((obj.get_s(),obj.get_pl_thk(),obj.get_web_h(),obj.get_web_thk(),
                                               obj.get_fl_w(),obj.get_fl_thk(),obj.get_span(),width), prt=False)
                    tot_weight += weigth_to_add
                    weight_details['objects'].append(weigth_to_add)
                    if frame_spacings[count // 2] is None:
                        frame_spacings[count // 2] = obj.get_s()
                    #print('added normal weight', weigth_to_add)

                else:
                    # In this case there are no applicable solutions found in the specified dimension ranges.
                    tot_weight += float('inf')
                    valid = False
            if valid:
                #print(frame_distance)
                for frame in range(no_of_fractions-1):
                    frame_height = 2.5 if frame_distance is None else frame_distance['start_dist'] + \
                                                                      (frame_distance['stop_dist']-
                                                                       frame_distance['start_dist']) * \
                                                                      ((frame+1)/no_of_fractions)

                    #pl_area, stf_area = 0.018 * width, 0.25 * 0.015 * (width//frame_spacings[frame])
                    this_x = (frame_spacings[frame], opt_girder_prop[0], opt_girder_prop[1], opt_girder_prop[2],
                              opt_girder_prop[3], opt_girder_prop[4], None, width)
                    this_weight = sum(get_field_tot_area(this_x))* frame_height * 7850
                    scale_max, scale_min = opt_girder_prop[5], opt_girder_prop[6]

                    this_scale = scale_min + (scale_max-scale_min) * (abs((max_frame_count-(count+1)/2))/
                                                                      (max_frame_count-min_frame_count))
                    #print('Number of fractions', no_of_fractions, 'Scale', this_scale)
                    tot_weight += this_weight * this_scale
                    solution_found = True
                    #print('added frame weight', this_weight * this_scale)
                    weight_details['frames'].append(this_weight * this_scale)
                    weight_details['scales'].append(this_scale)
            elif iterations == 2:
                solution_found = True  # Only iterate once.

            if predefiened_stiffener_iter is not None or not reiterate:
                solution_found = True  # Noe solution may be found, but in this case no more iteations.

        results[no_of_fractions] = tot_weight, opt_objects, weight_details
    return results

def any_find_min_weight_var(var):
    '''
    Find the minimum weight of the inpu
    :param min:
    :param max:
    :return:
    '''

    return min(map(calc_weight))

def any_constraints_cylinder(x,obj: calc.CylinderAndCurvedPlate,init_weight, lat_press = None,side='p',
                             chk=(True,True,True,True, True, True, True, False, False, False),
                             fat_dict = None, fat_press = None, slamming_press = 0,fdwn = 1, fup = 0.5,
                             ml_results = None):
    '''
    Checking all constraints defined.

        iter_var = ((item,init_stuc_obj,lat_press,init_filter_weight,side,chk,fat_dict,fat_press,slamming_press, PULSrun)
                for item in iterable_all)
    :param x:
    :return:
    '''

    all_checks = [0,0,0,0,0,0,0,0]
    check_map = {'weight': 0, 'UF unstiffened': 1, 'Column stability': 2, 'UF longitudinal stiffeners':3,
                 'Stiffener check': 4, 'UF ring stiffeners':5, 'UF ring frame': 6, 'Check OK': 7}
    calc_obj = create_new_cylinder_obj(obj, x)

    # Weigth
    if init_weight != False:
        this_weight = calc_weight_cylinder(x)
        if this_weight > init_weight:
            results = calc_obj.get_utilization_factors(optimizing=True, empty_result_dict = True)
            results['Weight'] = this_weight
            all_checks[0] += 1
            return False, 'Weight filter', x, all_checks, calc_obj

    if chk[0]:
        results = calc_obj.get_utilization_factors(optimizing = True)
        if results[0]:
            all_checks[check_map[results[1]]] += 1
            return True, results[1], x, all_checks, calc_obj
        else:
            all_checks[check_map[results[1]]] += 1
            return False, results[1], x, all_checks, calc_obj


def any_constraints_all(x,obj,lat_press,init_weight,side='p',chk=(True,True,True,True, True, True, True, False,
                                                                  False, False),
                        fat_dict = None, fat_press = None, slamming_press = 0, PULSrun: calc.PULSpanel = None,
                        print_result = False, fdwn = 1, fup = 0.5, ml_results = None):
    '''
    Checking all constraints defined.

        iter_var = ((item,init_stuc_obj,lat_press,init_filter_weight,side,chk,fat_dict,fat_press,slamming_press, PULSrun)
                for item in iterable_all)
    :param x:
    :return:
    '''

    all_checks = [0,0,0,0,0,0,0,0,0,0,0]
    print_result = False
    calc_object = create_new_calc_obj(obj, x, fat_dict, fdwn = fdwn, fup = fup)

    # PULS buckling check
    if chk[7] and PULSrun is not None:
        x_id = x_to_string(x)
        if calc_object[0].get_puls_method() == 'buckling':
            puls_uf = PULSrun.get_puls_line_results(x_id)["Buckling strength"]["Actual usage Factor"][0]
        elif calc_object[0].get_puls_method() == 'ultimate':
            puls_uf = PULSrun.get_puls_line_results(x_id)["Ultimate capacity"]["Actual usage Factor"][0]
        if type(puls_uf) == str:
            return False, 'PULS', x, all_checks
        all_checks[8] = puls_uf/PULSrun.puls_acceptance
        if puls_uf/PULSrun.puls_acceptance >= 1:
            if print_result:
                print('PULS', calc_object[0].get_one_line_string(), False)
            return False, 'PULS', x, all_checks

    # Buckling ml-cl
    if chk[8]:
        if any([calc_object[0].get_puls_method() == 'buckling' and ml_results[0] != 9,
                calc_object[0].get_puls_method() == 'ultimate' and ml_results[1] != 9]):
            if print_result:
                print('Buckling ML-CL', calc_object[0].get_one_line_string(), False)
            return False, 'Buckling ML-CL', x, all_checks

    # Buckling ml-reg
    if chk[9]:
        pass

    this_weight = calc_weight(x)


    if this_weight > init_weight:
        weigt_frac = this_weight / init_weight
        if print_result:
            pass
            # print('Weights', calc_weight(x), ' > ', init_weight,
            #       calc_object[0].get_one_line_string(), init_weight, False)
        all_checks[0] = weigt_frac
        return False, 'Weight filter', x, all_checks

    # Section modulus
    if chk[0]:
        section_modulus = min(calc_object[0].get_section_modulus())
        min_section_modulus = calc_object[0].get_dnv_min_section_modulus(lat_press)
        section_frac = section_modulus / min_section_modulus
        all_checks[1] = section_frac
        if not section_modulus > min_section_modulus :
            if print_result:
                print('Section modulus',calc_object[0].get_one_line_string(), False)
            return False, 'Section modulus', x, all_checks


    # Local stiffener buckling
    if chk[6]:
        buckling_local =  calc_object[0].buckling_local_stiffener()
        all_checks[2] = buckling_local[1]
        if not buckling_local[0]:
            if print_result:
                print('Local stiffener buckling',calc_object[0].get_one_line_string(), False)
            return False, 'Local stiffener buckling', x, all_checks

    # Buckling
    if chk[3]:
        buckling_results = calc_object[0].calculate_buckling_all(design_lat_press=lat_press, checked_side=side)[0:5]
        all_checks[3] = max(buckling_results)
        if not all([uf<=1 for uf in buckling_results]):
            if print_result:
                print('Buckling',calc_object[0].get_one_line_string(), False)
            return False, 'Buckling', x, all_checks


    # Minimum plate thickness
    if chk[1]:
        act_pl_thk = calc_object[0].get_pl_thk()
        min_pl_thk = calc_object[0].get_dnv_min_thickness(lat_press)/1000
        plate_frac = min_pl_thk / act_pl_thk
        all_checks[4] = plate_frac
        if not act_pl_thk > min_pl_thk:
            if print_result:
                print('Minimum plate thickeness',calc_object[0].get_one_line_string(), False)
            return False, 'Minimum plate thickness', x, all_checks

    # Shear area
    if chk[2]:
        calc_shear_area = calc_object[0].get_shear_area()
        min_shear_area = calc_object[0].get_minimum_shear_area(lat_press)
        shear_frac = min_shear_area / calc_shear_area
        all_checks[5] = shear_frac
        if not calc_shear_area > min_shear_area:
            if print_result:
                print('Shear area',calc_object[0].get_one_line_string(), False)
            return False, 'Shear area', x,  all_checks

    # Fatigue
    if chk[4] and fat_dict is not None and fat_press is not None:

        fatigue_uf = calc_object[1].get_total_damage(ext_press=fat_press[0],
                                                     int_press=fat_press[1])*calc_object[1].get_dff()
        all_checks[6] = fatigue_uf
        if fatigue_uf > 1:
            if print_result:
                print('Fatigue',calc_object[0].get_one_line_string(), False)
            return False, 'Fatigue', x, all_checks

    # Slamming

    if chk[5] and slamming_press != 0:
        slam_check = calc_object[0].check_all_slamming(slamming_press)
        all_checks[7] = slam_check[1]
        if slam_check[0] is False:
            if print_result:
                print('Slamming',calc_object[0].get_one_line_string(), False)
            return False, 'Slamming', x, all_checks

    if print_result:
        print('OK Section', calc_object[0].get_one_line_string(), True)
    return True, 'Check OK', x, all_checks

def constraint_geometric(fractions, *args):
    return sum(fractions) == 1

def pso_constraint_geometric(x,*args):
    ''' The sum of the fractions must be 1.'''
    return 1-sum(x)

def create_new_cylinder_obj(init_obj, x_new):
    '''
    shell       (0.02, 2.5, 5, 5, 10, nan, nan, nan),
    long        (0.875, nan, 0.3, 0.01, 0.1, 0.01, nan, nan),
    ring        (nan, nan, 0.3, 0.01, 0.1, 0.01, nan, nan),
    ring        (nan, nan, 0.7, 0.02, 0.2, 0.02, nan, nan)]
    '''
    stress_press = [init_obj.sasd, init_obj.smsd, init_obj.tTsd, init_obj.tQsd, init_obj.shsd]
    shell_obj = init_obj.ShellObj
    long_obj = init_obj.LongStfObj
    '''
    t1, r1, s1, hw1, tw1, b1, tf1 = x1
    t1, r1, s2, hw2, tw2, b2, tf2 = x2
    '''

    x_old = shell_obj.thk, shell_obj.radius,  \
            init_obj.panel_spacing if long_obj is None else long_obj.s/1000, \
            0 if long_obj is None else long_obj.hw/1000, \
            0 if long_obj is None else long_obj.tw/1000,\
            0 if long_obj is None else long_obj.b/1000,\
            0 if long_obj is None else long_obj.tf/1000,

    x_new_stress_scaling = x_new[0][0] if not np.isnan(x_new[0][0]) else shell_obj.thk, \
                           x_new[0][1] if not np.isnan(x_new[0][1]) else shell_obj.radius,\
                           x_new[0][5] if long_obj is None else x_new[1][0], \
                           0 if long_obj is None else x_new[1][2], \
                           0 if long_obj is None else x_new[1][3],\
                           0 if long_obj is None else x_new[1][4],\
                           0 if long_obj is None else x_new[1][5]

    new_stresses = stress_scaling_cylinder(x_old, x_new_stress_scaling, stress_press)
    new_obj = copy.deepcopy(init_obj)
    new_obj.sasd, new_obj.smsd, new_obj.tTsd, new_obj.tQsd, new_obj.shsd = new_stresses
    new_obj.ShellObj.radius = x_new[0][1]
    new_obj.ShellObj.thk = x_new[0][0]
    if long_obj is None:
        new_obj.panel_spacing = x_new[0][5]
    else:
        new_obj.LongStfObj.s = x_new[1][0]*1000
        new_obj.LongStfObj.hw = x_new[1][2]*1000
        new_obj.LongStfObj.tw = x_new[1][3]*1000
        new_obj.LongStfObj.b = x_new[1][4]*1000
        new_obj.LongStfObj.tf = x_new[1][5]*1000

    return new_obj

def create_new_calc_obj(init_obj,x, fat_dict=None, fdwn = 1, fup = 0.5):
    '''
    Returns a new calculation object to be used in optimization
    :param init_obj:
    :return:
    '''

    x_old = [init_obj.get_s(), init_obj.get_pl_thk(), init_obj.get_web_h() , init_obj.get_web_thk(),
             init_obj.get_fl_w(),init_obj.get_fl_thk(), init_obj.get_span(), init_obj.get_lg()]

    sigma_y1_new = stress_scaling(init_obj.get_sigma_y1(), init_obj.get_pl_thk(), x[1], fdwn = fdwn, fup = fup)
    sigma_y2_new = stress_scaling(init_obj.get_sigma_y2(), init_obj.get_pl_thk(), x[1], fdwn = fdwn, fup = fup)
    tau_xy_new = stress_scaling(init_obj.get_tau_xy(), init_obj.get_pl_thk(), x[1], fdwn = fdwn, fup = fup)
    sigma_x1_new = stress_scaling_area(init_obj.get_sigma_x1(),
                                      sum(get_field_tot_area(x_old)),
                                      sum(get_field_tot_area(x)), fdwn = fdwn, fup = fup)
    sigma_x2_new = stress_scaling_area(init_obj.get_sigma_x2(),
                                      sum(get_field_tot_area(x_old)),
                                      sum(get_field_tot_area(x)), fdwn = fdwn, fup = fup)

    try:
        stf_type = x[8]
    except IndexError:
        stf_type = init_obj.get_stiffener_type()

    main_dict = {'mat_yield': [init_obj.get_fy(), 'Pa'],'mat_factor': [init_obj.get_mat_factor(), 'Pa'],
                 'span': [init_obj.get_span(), 'm'],
                 'spacing': [x[0], 'm'],'plate_thk': [x[1], 'm'],'stf_web_height':[ x[2], 'm'],
                 'stf_web_thk': [x[3], 'm'],'stf_flange_width': [x[4], 'm'],
                 'stf_flange_thk': [x[5], 'm'],'structure_type': [init_obj.get_structure_type(), ''],
                 'stf_type': [stf_type, ''],'sigma_y1': [sigma_y1_new, 'MPa'],
                 'sigma_y2': [sigma_y2_new, 'MPa'],'sigma_x1': [sigma_x1_new, 'MPa'],'sigma_x2': [sigma_x2_new, 'MPa'],
                 'tau_xy': [tau_xy_new, 'MPa'],'plate_kpp': [init_obj.get_kpp(), ''],
                 'stf_kps': [init_obj.get_kps(), ''],'stf_km1': [init_obj.get_km1(), ''],
                 'stf_km2': [init_obj.get_km2(), ''],'stf_km3': [init_obj.get_km3(), ''],
                 'structure_types':[init_obj.get_structure_types(), ''],
                 'zstar_optimization': [init_obj.get_z_opt(), ''],
                 'puls buckling method':[init_obj.get_puls_method(),''],
                 'puls boundary':[init_obj.get_puls_boundary(),''],
                 'puls stiffener end':[init_obj.get_puls_stf_end(),''],
                 'puls sp or up':[init_obj.get_puls_sp_or_up(),''],
                 'puls up boundary':[init_obj.get_puls_up_boundary(),'']}
    if fat_dict == None:
        return calc.CalcScantlings(main_dict), None
    else:
        return calc.CalcScantlings(main_dict), calc.CalcFatigue(main_dict, fat_dict)

def create_new_structure_obj(init_obj, x, fat_dict=None, fdwn = 1, fup = 0.5):
    '''
    Returns a new calculation object to be used in optimization
    :param init_obj:
    :return:
    '''
    x_old = [init_obj.get_s(), init_obj.get_pl_thk(), init_obj.get_web_h() , init_obj.get_web_thk(),
             init_obj.get_fl_w() ,init_obj.get_fl_thk(), init_obj.get_span(), init_obj.get_lg()]

    sigma_y1_new = stress_scaling(init_obj.get_sigma_y1(), init_obj.get_pl_thk(), x[1], fdwn = fdwn, fup = fup)
    sigma_y2_new = stress_scaling(init_obj.get_sigma_y2(), init_obj.get_pl_thk(), x[1], fdwn = fdwn, fup = fup)
    tau_xy_new = stress_scaling(init_obj.get_tau_xy(), init_obj.get_pl_thk(), x[1],fdwn = fdwn, fup = fup)
    sigma_x1_new = stress_scaling_area(init_obj.get_sigma_x1(),sum(get_field_tot_area(x_old)),sum(get_field_tot_area(x)),
                                      fdwn = fdwn, fup = fup)
    sigma_x2_new = stress_scaling_area(init_obj.get_sigma_x2(),sum(get_field_tot_area(x_old)),sum(get_field_tot_area(x)),
                                      fdwn = fdwn, fup = fup)

    try:
        stf_type = x[8]
    except IndexError:
        stf_type = init_obj.get_stiffener_type()

    main_dict = {'mat_yield': [init_obj.get_fy(), 'Pa'], 'span': [init_obj.get_span(), 'm'],
                 'mat_factor': [init_obj.get_mat_factor(), 'Pa'],
                   'spacing': [x[0], 'm'], 'plate_thk': [x[1], 'm'], 'stf_web_height': [x[2], 'm'],
                   'stf_web_thk': [x[3], 'm'], 'stf_flange_width': [x[4], 'm'],
                   'stf_flange_thk': [x[5], 'm'], 'structure_type': [init_obj.get_structure_type(), ''],
                   'stf_type': [stf_type, ''], 'sigma_y1': [sigma_y1_new, 'MPa'],
                   'sigma_y2': [sigma_y2_new, 'MPa'], 'sigma_x1': [sigma_x1_new, 'MPa'],'sigma_x2': [sigma_x2_new, 'MPa'],
                   'tau_xy': [tau_xy_new, 'MPa'], 'plate_kpp': [init_obj.get_kpp(), ''],
                   'stf_kps': [init_obj.get_kps(), ''], 'stf_km1': [init_obj.get_km1(), ''],
                   'stf_km2': [init_obj.get_km2(), ''], 'stf_km3': [init_obj.get_km3(), ''],
                 'structure_types': [init_obj.get_structure_types(), ''],
                 'zstar_optimization': [init_obj.get_z_opt(), ''],
                 'puls buckling method': [init_obj.get_puls_method(), ''],
                 'puls boundary': [init_obj.get_puls_boundary(), ''],
                 'puls stiffener end': [init_obj.get_puls_stf_end(), ''],
                 'puls sp or up': [init_obj.get_puls_sp_or_up(), ''],
                 'puls up boundary': [init_obj.get_puls_up_boundary(), ''],
                 }

    #if fat_dict == None:
    return calc.Structure(main_dict)

def get_field_tot_area(x):
    ''' Total area of a plate field. '''

    if len(x) == 6:
        width = 10
    else:
        width = x[7]
    plate_area = width*x[1]
    stiff_area = (x[2] * x[3]+ x[4] * x[5]) * (width//x[0])

    return plate_area, stiff_area

def calc_weight(x, prt = False):
    '''
    Calculating the current weight
    :param current_dict:
    :return:
    '''
    span = x[6]
    plate_area, stiff_area = get_field_tot_area(x)

    if prt:
        print('x is', x, 'plate area', plate_area, 'stiff area', stiff_area, 'weight',
              span * 7850 * (plate_area + stiff_area))
    return span * 7850 * (plate_area + stiff_area)

def calc_weight_pso(x,*args):
    '''
    Calculating the current weight
    :param current_dict:
    :return:
    '''

    width = args[5]
    span = args[6]

    plate_area = width*x[1]
    stiff_area = (x[2] * x[3]+ x[4] * x[5]) * (width//x[0])
    return span * 7850 * (plate_area + stiff_area)

def calc_weight_pso_section(x,*args):
    '''
    Calculating the weight of a complete section.
    :param x: 
    :param args: 
    :return: 
    '''
    stru_objects = args[1]
    tot_length = args[2]
    frame_height = args[3]
    frame_section_area = args[4]

    tot_weight = 0

    for dummy_i in range(len(stru_objects)):
        tot_weight += frame_section_area*frame_height*7850

    count = 0
    for stru_object in stru_objects:
        span = tot_length*x[count]
        stru_object.set_span(span)
        tot_weight += stru_object.get_weight_width_lg()

    return tot_weight

def calc_weight_cylinder(x):
    '''
    Calculation of total weigth.

    shell       (0.02, 2.5, 5, 5, 10, nan, nan, nan),
    long        (0.875, nan, 0.3, 0.01, 0.1, 0.01, nan, nan),
    ring        (nan, nan, 0.3, 0.01, 0.1, 0.01, nan, nan),
    ring        (nan, nan, 0.7, 0.02, 0.2, 0.02, nan, nan)]
    '''

    num_long_stf = 2*math.pi*x[0][1]/x[1][0]
    long_stf_area = x[1][2]*x[1][3]+x[1][4]*x[1][5]
    long_stf_volume = long_stf_area * x[0][4] * num_long_stf

    num_ring_stf = x[0][4] / x[0][2]

    ring_stf_volume = math.pi*(math.pow(x[0][1],2)-math.pow(x[0][1]-x[2][2],2))*x[2][3] + \
                      2*math.pi*(x[0][1]-x[2][2]) * x[2][4] * x[2][5]
    ring_stf_tot_vol = ring_stf_volume * num_ring_stf

    num_ring_girder = x[0][4] / x[0][3]
    ring_frame_volume = math.pi*(math.pow(x[0][1],2)-math.pow(x[0][1]-x[3][2],2))*x[3][3] + \
                      2*math.pi*(x[0][1]-x[3][2])*x[3][4]*x[3][5]
    tot_ring_frame_vol = ring_frame_volume*num_ring_girder

    shell_volume = 2 * math.pi * x[0][1] * x[0][0] * x[0][4]

    return (long_stf_volume+ring_stf_tot_vol+tot_ring_frame_vol+shell_volume)*7850

def stress_scaling_cylinder(x1, x2, stress1):
    '''
    Scale stresses of a stiffened cylinder.

    To scale:

    Design axial stress,          sa,sd =
    Design bending stress,   sm,sd =
    Design torsional stress,   tT,sd=
    Design shear stress,        tQ,sd=
    Additional hoop stress, sh,sd =

    '''

    t1, r1, s1, hw1, tw1, b1, tf1 = x1
    t2, r2, s2, hw2, tw2, b2, tf2 = x2
    
    sasd1, smsd1, tTsd1, tQsd1, shsd1 = stress1

    A1 = hw1 * tw1 + b1 * tf1
    A2 = hw2 * tw2 + b2 * tf2
    # Axial stress changes by equivalent thickness

    thk_eq1 = t1 + 0 if s1 == 0 else A1 / s1
    thk_eq2 = t2 + 0 if s2 == 0 else A2 / s2

    # Moment stress changes by difference in moment of inertia

    Itot1 = calc.CylinderAndCurvedPlate.get_Itot(hw=hw1, tw=tw1, b=b1, tf=tf1, r=r1, s=s1, t=t1)
    Itot2 = calc.CylinderAndCurvedPlate.get_Itot(hw=hw2, tw=tw2, b=b2, tf=tf2, r=r2, s=s2, t=t2)

    # Torsional, shear and hoop changes by cylinder thickness.

    return sasd1*(thk_eq1/thk_eq2), smsd1*(Itot1/Itot2), tTsd1*(t1/t2), tQsd1*(t1/t2), shsd1*(t1/t2)

def stress_scaling(sigma_old,t_old,t_new, fdwn = 1, fup = 0.5):

    if t_new <= t_old: #decreasing the thickness
        sigma_new = sigma_old*(t_old/(t_old-fdwn*abs((t_old-t_new))))
        assert sigma_new >= sigma_old, 'ERROR no stress increase: \n' \
                                      't_old '+str(t_old)+' sigma_old '+str(sigma_old)+ \
                                      '\nt_new '+str(t_new)+' sigma_new '+str(sigma_new)

    else: #increasing the thickness

        sigma_new = sigma_old*(t_old/(t_old+fup*abs((t_old-t_new))))
        assert sigma_new <= sigma_old, 'ERROR no stress reduction: \n' \
                                      't_old '+str(t_old)+' sigma_old '+str(sigma_old)+ \
                                      '\nt_new '+str(t_new)+' sigma_new '+str(sigma_new)
    return sigma_new

def stress_scaling_area(sigma_old,a_old,a_new, fdwn = 1, fup = 0.5):
    ''' Scale stresses using input area '''

    if a_new <= a_old: #decreasing the thickness
        sigma_new = sigma_old*(a_old/(a_old-fdwn*abs((a_old-a_new))))
        # assert sigma_new >= sigma_old, 'ERROR no stress increase: \n' \
        #                               't_old '+str(a_old)+' sigma_old '+str(sigma_old)+ \
        #                               '\nt_new '+str(a_new)+' sigma_new '+str(sigma_new)
    else: #increasing the thickness
        sigma_new = sigma_old*(a_old/(a_old+fup*abs((a_old-a_new))))
        # assert sigma_new <= sigma_old, 'ERROR no stress reduction: \n' \
        #                               't_old '+str(a_old)+' sigma_old '+str(sigma_old)+ \
        #                               '\nt_new '+str(a_new)+' sigma_new '+str(sigma_new)
    #print('a_old', a_old, 'sigma_old', sigma_old, '|', 'a_new', a_new, 'sigma_new',sigma_new)
    return sigma_new

def x_to_string(x):
    ret = ''
    for val in x:
        ret += str(val) + '_'
    return ret

def get_filtered_results(iterable_all,init_stuc_obj,lat_press,init_filter_weight,side='p',
                         chk=(True,True,True,True,True,True,True, False),fat_dict = None, fat_press = None,
                         slamming_press=None, processes = None, puls_sheet = None, puls_acceptance = 0.87,
                         fdwn = 1, fup = 0.5, ml_algo = None):
    '''
    Using multiprocessing to return list of applicable results.

    :param iterable_all:
    :param init_stuc_obj:
    :param lat_press:
    :param init_filter_weight:
    :param side:
    :param chk:
    :return:
    '''
    #print('Init filter weight', init_filter_weight)
    '''
    x,obj,lat_press,init_weight,side='p',chk=(True,True,True,True, True, True, True, False),
                        fat_dict = None, fat_press = None, slamming_press = 0, , puls_results = None, print_result = False
    '''

    if chk[7]:
        # PULS to be used.
        #calc.PULSpanel
        '''
        dict_to_run[line_given] = self._line_to_struc[line_given][1].get_puls_input()
        dict_to_run[line_given]['Identification'] = line_given
        dict_to_run[line_given]['Pressure (fixed)'] = self.get_highest_pressure(line_given)['normal'] / 1e6
        '''

        dict_to_run = {}
        for x in iterable_all:
            x_id = x_to_string(x)
            calc_object = create_new_calc_obj(init_stuc_obj, x, fat_dict, fdwn = fdwn, fup = fup)
            dict_to_run[x_id] = calc_object[0].get_puls_input()
            dict_to_run[x_id]['Identification'] = x_id
            dict_to_run[x_id]['Pressure (fixed)'] = lat_press/1000 # PULS sheet to have pressure in MPa

        PULSrun = calc.PULSpanel(dict_to_run, puls_sheet_location=puls_sheet, puls_acceptance=puls_acceptance)
        PULSrun.run_all()
        sort_again = None
    elif chk[8]:

        # ML-CL to be used.
        # Buckling ml-cl
        sp_int, sp_gl_gt, up_int, up_gl_gt, \
        sp_int_idx, sp_gl_gt_idx, up_int_idx, up_gl_gt_idx   = \
            list(), list(), list(),list(),list(), list(), list(),list()
        
        # Create iterator
        idx_count = 0
        for idx, x in enumerate(iterable_all):
            idx_count += 1
            calc_object = create_new_calc_obj(init_stuc_obj, x, fat_dict, fdwn=fdwn, fup=fup)
            if calc_object[0].get_puls_sp_or_up() == 'UP':
                if calc_object[0].get_puls_boundary() == 'Int':
                    up_int.append(calc_object[0].get_buckling_ml_input(lat_press, alone = False))
                    up_int_idx.append(idx)
                else:
                    up_gl_gt.append(calc_object[0].get_buckling_ml_input(lat_press, alone = False))
                    up_gl_gt_idx.append(idx)
            else:
                if calc_object[0].get_puls_boundary() == 'Int':
                    sp_int.append(calc_object[0].get_buckling_ml_input(lat_press, alone = False))
                    sp_int_idx.append(idx)
                else:
                    sp_gl_gt.append(calc_object[0].get_buckling_ml_input(lat_press, alone = False))
                    sp_gl_gt_idx.append(idx)

        # Predict
        sort_again = np.zeros([len(iterable_all),2])

        if len(sp_int) != 0:
            sp_int_res = [ml_algo['cl SP buc int predictor'].predict(ml_algo['cl SP buc int scaler']
                                                                     .transform(sp_int)),
                          ml_algo['cl SP ult int predictor'].predict(ml_algo['cl SP buc int scaler']
                                                                     .transform(sp_int))]
            for idx, res_buc, res_ult in zip(sp_int_idx, sp_int_res[0],sp_int_res[1]):
                sort_again[idx] = [res_buc, res_ult]

        if len(sp_gl_gt) != 0:
            sp_gl_gt_res = [ml_algo['cl SP buc GLGT predictor'].predict(ml_algo['cl SP buc GLGT scaler']
                                                                        .transform(sp_gl_gt)),
                          ml_algo['cl SP buc GLGT predictor'].predict(ml_algo['cl SP buc GLGT scaler']
                                                                      .transform(sp_gl_gt))]
            for idx, res_buc, res_ult in zip(sp_gl_gt_idx, sp_gl_gt_res[0],sp_gl_gt_res[1]):
                sort_again[idx] = [res_buc, res_ult]
        if len(up_int) != 0:
            up_int_res = [ml_algo['cl UP buc int predictor'].predict(ml_algo['cl UP buc int scaler']
                                                                     .transform(up_int)),
                          ml_algo['cl UP ult int predictor'].predict(ml_algo['cl UP buc int scaler']
                                                                     .transform(up_int))]
            for idx, res_buc, res_ult in zip(up_int_idx, up_int_res[0],up_int_res[1]):
                sort_again[idx] = [res_buc, res_ult]
        if len(up_gl_gt) != 0:
            up_gl_gt_res  =[ml_algo['cl UP buc GLGT predictor'].predict(ml_algo['cl UP buc GLGT scaler']
                                                                        .transform(up_gl_gt)),
                          ml_algo['cl UP buc GLGT predictor'].predict(ml_algo['cl UP buc GLGT scaler']
                                                                      .transform(up_gl_gt))]
            for idx, res_buc, res_ult in zip(up_gl_gt_idx, up_gl_gt_res[0],up_gl_gt_res[1]):
                sort_again[idx] = [res_buc, res_ult]
        PULSrun = None
    else:
        PULSrun = None
        idx_count = 0
        for x in iterable_all:
            idx_count += 1
        sort_again = None

    iter_var = list()
    for idx,item in enumerate(iterable_all):
        iter_var.append((item,init_stuc_obj,lat_press,init_filter_weight,side,chk,fat_dict,fat_press,slamming_press,
                         PULSrun, False,fdwn, fup, sort_again[idx] if chk[8] == True else None))

    iter_var = tuple(iter_var)

    #res_pre = it.starmap(any_constraints_all, iter_var)
    if processes is None:
        processes = max(cpu_count()-1,1)

    with Pool(processes) as my_process:
        # res_pre = my_process.starmap_async(any_constraints_all, iter_var).get()
        # print('Done calculating')
        res_pre = my_process.starmap(any_constraints_all, iter_var)

    check_ok, check_not_ok = list(), list()
    for item in res_pre:
        if item[0] is False:
            check_not_ok.append(item)
        else:
            check_ok.append(item)

    return check_ok, check_not_ok

def any_get_all_combs(min_var, max_var,deltas, init_weight = float('inf'), predef_stiffeners = None, cylinder = False):
    '''
    Calulating initial values.
    :param min:
    :param max:
    :return:
    '''
    '''
    shell_upper_bounds = np.array( [0.03, 2.5, 5, 0.8, 6, 6])
    shell_deltas = np.array(       [0.01, 2.5, 1, 0.1, 1, 1])
    shell_lower_bounds = np.array( [0.02, 2.5, 5, 0.6, 4, 4])

    long_upper_bounds = np.array(   [0.875, None, 0.5, 0.018, 0.2, 0.03])
    long_deltas = np.array(         [0.025, None, 0.1, 0.004, 0.05, 0.005])
    long_lower_bounds = np.array(   [0.875, None, 0.3,  0.010, 0.1, 0.010])

    ring_stf_upper_bounds = np.array(   [None, None, 0.5, 0.018, 0.2, 0.03])
    ring_stf_deltas = np.array(         [None, None, 0.1, 0.004, 0.05, 0.005])
    ring_stf_lower_bounds = np.array(   [None, None, 0.3,  0.010, 0.1, 0.010])

    ring_frame_upper_bounds = np.array( [None, None, 0.9, 0.04, 0.3, 0.04])
    ring_frame_deltas = np.array(       [None, None, 0.2, 0.01, 0.1, 0.01])
    ring_frame_lower_bounds = np.array( [None, None, 0.5,  0.02, 0.2, 0.020])
    '''
    if min_var[0] is not None:
        spacing_array = (np.arange(min_var[0], max_var[0]+ deltas[0], deltas[0])) if min_var[0] != max_var[0] \
            else np.array([min_var[0]])
        spacing_array = spacing_array[spacing_array <= max_var[0]]
    else:
        spacing_array = np.array([np.nan])

    if min_var[1] is not None:
        pl_thk_array = (np.arange(min_var[1], max_var[1]+ deltas[1], deltas[1])) if min_var[1] != max_var[1] \
            else np.array([min_var[1]])
        pl_thk_array = pl_thk_array[pl_thk_array <= max_var[1]]
    else:
        pl_thk_array = np.array([np.nan])

    if predef_stiffeners is not None:
        predef_iterable = list()
        for pre_str in predef_stiffeners:
            for spacing in spacing_array:
                for pl_thk in pl_thk_array:
                    new_field = list(pre_str)
                    new_field[0] = spacing
                    new_field[1] = pl_thk
                    predef_iterable.append(tuple(new_field))
        return predef_iterable


    web_h_array = (np.arange(min_var[2], max_var[2]+ deltas[2], deltas[2])) if min_var[2] != max_var[2] \
        else np.array([min_var[2]])
    web_h_array = web_h_array[web_h_array <= max_var[2]]

    web_thk_array = (np.arange(min_var[3], max_var[3]+ deltas[3], deltas[3])) if min_var[3] != max_var[3] \
        else np.array([min_var[3]])
    web_thk_array = web_thk_array[web_thk_array <= max_var[3]]

    flange_w_array = (np.arange(min_var[4], max_var[4]+ deltas[4], deltas[4])) if min_var[4] != max_var[4] \
        else np.array([min_var[4]])
    flange_w_array = flange_w_array[flange_w_array <= max_var[4]]

    if min_var[5] is not None:
        flange_thk_array = (np.arange(min_var[5], max_var[5]+ deltas[5], deltas[5])) if min_var[5] != max_var[5] \
            else np.array([min_var[5]])
        flange_thk_array = flange_thk_array[flange_thk_array <= max_var[5]]
    else:
        flange_thk_array = np.array([np.nan])

    if min_var[6] is not None:
        span_array = (np.arange(min_var[6], max_var[6], deltas[4])) if min_var[6] != max_var[6] \
            else np.array([min_var[6]])
    else:
        span_array = np.array([np.nan])

    if min_var[7] is not None:
        girder_array = (np.arange(min_var[7], max_var[7], deltas[7])) if min_var[7] != max_var[7] \
            else np.array([min_var[7]])
    else:
        girder_array = np.array([np.nan])

    comb = it.product(spacing_array, pl_thk_array, web_h_array, web_thk_array, flange_w_array, flange_thk_array,
                      span_array,girder_array)

    return list(comb)

def get_initial_weight(obj,lat_press,min_var,max_var,deltas,trials,fat_dict,fat_press, predefined_stiffener_iter,
                       slamming_press, fdwn = 1, fup = 0.5, ml_algo = None):
    '''
    Return a guess of the initial weight used to filter the constraints.
    Only aim is to reduce running time of the algorithm.
    '''

    min_weight = float('inf')
    if predefined_stiffener_iter is None:
        combs = any_get_all_combs(min_var, max_var, deltas)
    else:
        combs = any_get_all_combs(min_var, max_var, deltas,predef_stiffeners=[item.get_tuple() for item in
                                                                              predefined_stiffener_iter])

    trial_selection = random_product(combs, repeat=trials)

    for x in trial_selection:
        if any_constraints_all(x=x,obj=obj,lat_press=lat_press,init_weight=min_weight,
                               fat_dict=fat_dict,fat_press = fat_press,slamming_press=slamming_press,
                               fdwn = fdwn, fup = fup)[0]:
            current_weight = calc_weight(x)
            if current_weight < min_weight:
                min_weight = current_weight
    return min_weight

def get_random_result(obj,lat_press,min_var,max_var,deltas,trials=10000,side='p',const_chk=(True,True,True,True,True),
                      fat_dict=None, fat_press=None):
    '''
    Return random results
    '''
    min_weight = float('inf')
    ass_var = None
    combs = any_get_all_combs(min_var, max_var, deltas)
    trial_selection = random_product(combs,repeat=trials)
    for x in trial_selection:
        if any_constraints_all(x=x,obj=obj,lat_press=lat_press,init_weight=min_weight,side=side,chk=const_chk,
                               fat_dict = fat_dict, fat_press = fat_press)[0] is not False:
            current_weight = calc_weight(x)
            if current_weight < min_weight:
                min_weight = current_weight
                ass_var = x
    if ass_var == None:
        return ass_var
    return create_new_structure_obj(obj, [round(item, 5) for item in ass_var]), \
           create_new_calc_obj(obj, [round(item, 5) for item in ass_var])[0]

def get_random_result_no_bounds(obj,lat_press,min_var,max_var,trials=10000,side='p',const_chk=(True,True,True,True,True)
                                , fat_dict=None, fat_press=None):
    '''
    Return random results, ignoring the deltas
    '''
    min_weight = float('inf')
    ass_var = None
    for trial in range(trials):
        spacing = random.randrange(int(min_var[0]*1000),int(max_var[0]*1000),1)/1000
        pl_thk = random.randrange(int(min_var[1]*1000),int(max_var[1]*1000),1)/1000
        web_h = random.randrange(int(min_var[2]*1000),int(max_var[2]*1000),1)/1000
        web_thk = random.randrange(int(min_var[3]*1000),int(max_var[3]*1000),1)/1000
        fl_w = random.randrange(int(min_var[4]*1000),int(max_var[4]*1000),1)/1000
        fl_thk = random.randrange(int(min_var[5]*1000),int(max_var[5]*1000),1)/1000
        x = (spacing,pl_thk,web_h,web_thk,fl_w,fl_thk,min_var[6],min_var[7])
        if any_constraints_all(x=x,obj=obj,lat_press=lat_press,init_weight=min_weight,side=side,chk=const_chk,
                               fat_dict = fat_dict, fat_press = fat_press)[0]:
            current_weight = calc_weight(x)
            if current_weight < min_weight:
                min_weight = current_weight
                ass_var = x
    if ass_var == None:
        return ass_var
    return create_new_structure_obj(obj, [round(item, 5) for item in ass_var]), \
           create_new_calc_obj(obj, [round(item, 5) for item in ass_var])[0]

def random_product(*args, repeat=1):
    "Random selection from itertools.product(*args, **kwds)"
    pools = [tuple(pool) for pool in args] * repeat
    return tuple(random.choice(pool) for pool in pools)

def product_any(*args, repeat=1,weight=float('inf')):
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = [tuple(pool) for pool in args] * repeat
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        if calc_weight(prod) < weight:
            yield tuple(prod)

def plot_optimization_results(results, multiple = False):

    check_ok_array, check_array, section_array = list(), list(), list()
    save_to_csv = asksaveasfilename()

    if save_to_csv != '':
        csv_file = open(save_to_csv,'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Is OK', 'Check info', 'pl b', 'pl thk', 'web h', 'web thk', 'fl b', 'fl thk', 'span',
                             'girder width', 'stiffener type', 'uf weight', 'uf sec mod', 'uf loc stf buc',
                             'uf buckling', 'uf min pl', 'uf shear', 'uf fatigue', 'uf slamming'])

    for check_ok, check, section, ufres in results[4]:
        check_ok_array.append(check_ok)
        check_array.append(check)
        section_array.append(section)
        if save_to_csv != '':
            to_write = list()
            to_write.append(check_ok)
            to_write.append(check)
            [to_write.append(item) for item in section]
            if(len(section) == 8):
                to_write.append('T')
            [to_write.append(item) for item in ufres]
            csv_writer.writerow(to_write)

    if save_to_csv != '':
        csv_file.close()

    check_ok_array, check_array, section_array = np.array(check_ok_array), \
                                                 np.array(check_array), \
                                                 np.array(section_array)

    x_label = np.unique(check_array)
    y = [np.count_nonzero(check_array == item) for item in np.unique(check_array)]

    fig, axs = plt.subplots(2, 1)
    clust_data = np.append(np.array(x_label).reshape(len(x_label), 1), np.array(y).reshape(len(y), 1), axis=1)
    collabel = ('Check fail type or OK', 'Number of occurences')
    axs[0].axis('tight')
    axs[0].axis('off')
    the_table = axs[0].table(cellText=clust_data, colLabels=collabel, loc='center')
    axs[1].pie(y, labels=x_label, autopct='%1.1f%%', explode=[0.1 for dummy in range(len(x_label))])

    plt.show()

if __name__ == '__main__':
    import ANYstructure_local.example_data as ex
    from calc_structure import CylinderAndCurvedPlate, Structure, Shell

    shell_main_dict = ex.shell_main_dict
    shell_main_dict['geometry'] = [7, '']
    #Structure(ex.obj_dict_cyl_ring)
    #Structure(ex.obj_dict_cyl_heavy_ring)
    # my_cyl = CylinderAndCurvedPlate(main_dict = ex.shell_main_dict, shell= Shell(ex.shell_dict),
    #                                 long_stf= Structure(ex.obj_dict_cyl_long2),
    #                                 ring_stf = Structure(ex.obj_dict_cyl_ring2),
    #                                 ring_frame= Structure(ex.obj_dict_cyl_heavy_ring2))
    my_cyl = CylinderAndCurvedPlate(main_dict = ex.shell_main_dict, shell= Shell(ex.shell_dict),
                                    long_stf= Structure(ex.obj_dict_cyl_long2),
                                    ring_stf = None,# Structure(ex.obj_dict_cyl_ring2),
                                    ring_frame= None)#Structure(ex.obj_dict_cyl_heavy_ring2))

    shell_upper_bounds = np.array( [0.03, 5, 5, 5, 10, None, None, None])
    shell_deltas = np.array(       [0.005, 0.5, 1, 0.1,1, None, None, None])
    shell_lower_bounds = np.array( [0.02, 5, 5, 5, 10, None, None, None])

    long_upper_bounds = np.array(   [0.8, None, 0.5, 0.02, 0.2, 0.03, None, None])
    long_deltas = np.array(         [0.1, None, 0.1, 0.01, 0.1, 0.01, None, None])
    long_lower_bounds = np.array(   [0.7, None, 0.3,  0.01, 0.1, 0.01, None, None])

    ring_stf_upper_bounds = np.array(   [None, None, 0.5, 0.018, 0.2, 0.03, None, None])
    ring_stf_deltas = np.array(         [None, None, 0.1, 0.004, 0.1, 0.01, None, None])
    ring_stf_lower_bounds = np.array(   [None, None, 0.3,  0.010, 0.1, 0.010, None, None])

    ring_frame_upper_bounds = np.array( [None, None, 0.9, 0.04, 0.3, 0.04, None, None])
    ring_frame_deltas = np.array(       [None, None, 0.2, 0.01, 0.1, 0.01, None, None])
    ring_frame_lower_bounds = np.array( [None, None, 0.7,  0.02, 0.2, 0.02, None, None])

    max_var = [shell_upper_bounds, long_upper_bounds, ring_stf_upper_bounds, ring_frame_upper_bounds]
    deltas = [shell_deltas, long_deltas, ring_stf_deltas, ring_frame_deltas]
    min_var = [shell_lower_bounds, long_lower_bounds, ring_stf_lower_bounds, ring_frame_lower_bounds]

    results = run_optmizataion(initial_structure_obj=my_cyl, min_var=min_var, max_var=max_var, deltas=deltas,
                               cylinder=True, use_weight_filter=True)
    shell = ['Shell thk. [mm]', 'Shell radius [mm]' , 'l rings [mm]', 'L shell [mm]', 'L tot. [mm]', 'N/A - future', 'N/A - future', 'N/A - future']
    stf_long = ['Spacing [mm]', 'Plate thk. [mm]', 'Web height [mm]', 'Web thk. [mm]', 'Flange width [mm]', 'Flange thk. [mm]', 'N/A - future', 'N/A - future']
    stf_ring = ['N/A', 'Plate thk. [mm]', 'Web height [mm]', 'Web thk. [mm]', 'Flange width [mm]', 'Flange thk. [mm]', 'N/A - future', 'N/A - future']

    # obj_dict = ex.obj_dict_sec_error
    # fat_obj = ex.get_fatigue_object_problematic()
    # fp = ex.get_fatigue_pressures_problematic()
    # fat_press = ((fp['p_ext']['loaded'],fp['p_ext']['ballast'],fp['p_ext']['part']),
    #              (fp['p_int']['loaded'],fp['p_int']['ballast'],fp['p_int']['part']))
    # x0 = [obj_dict['spacing'][0], obj_dict['plate_thk'][0], obj_dict['stf_web_height'][0], obj_dict['stf_web_thk'][0],
    #       obj_dict['stf_flange_width'][0], obj_dict['stf_flange_thk'][0], obj_dict['span'][0], 10]
    #
    # obj = calc.Structure(obj_dict)
    # lat_press = 427.235
    # calc_object = calc.CalcScantlings(obj_dict)
    # lower_bounds = np.array([0.875, 0.012, 0.3, 0.012, 0.1, 0.012, 3.5, 10])
    # upper_bounds = np.array([0.875, 0.025, 0.5, 0.018, 0.2, 0.03, 3.5, 10])
    # deltas = np.array([0.025, 0.001, 0.01, 0.001, 0.01, 0.001])
    #
    #
    # t1 = time.time()
    # #
    # results = run_optmizataion(obj, lower_bounds,upper_bounds, lat_press, deltas, algorithm='anysmart',
    #                            fatigue_obj=fat_obj, fat_press_ext_int=fat_press, use_weight_filter=True)
    #
    # print(results[1])
    # print(results[1].get_dnv_min_section_modulus(lat_press))
    # print(min([round(results[1].get_section_modulus()[0], 5), round(results[1].get_section_modulus()[1], 5)]))

    # t1 = time.time()
    # check_ok_array, check_array, section_array = list(), list(), list()
    #
    # for check_ok, check, section in results[4]:
    #     check_ok_array.append(check_ok)
    #     check_array.append(check)
    #     section_array.append(section)
    # check_ok_array, check_array, section_array = np.array(check_ok_array),\
    #                                              np.array(check_array),\
    #                                              np.array(section_array)
    #
    # x_label = np.unique(check_array)
    # y = [np.count_nonzero(check_array == item) for item in np.unique(check_array)]
    #
    # fig, axs = plt.subplots(2, 1)
    # clust_data = np.append(np.array(x_label).reshape(len(x_label),1), np.array(y).reshape(len(y),1), axis=1)
    # collabel = ('Check fail type or OK', 'Number of occurences')
    # axs[0].axis('tight')
    # axs[0].axis('off')
    # the_table = axs[0].table(cellText=clust_data, colLabels=collabel, loc='center')
    # axs[1].pie(y, labels = x_label, autopct='%1.1f%%', explode=[0.1 for dummy in range(len(x_label))])
    # plt.show()
    #
    # cmap = plt.cm.get_cmap(plt.cm.viridis, len(x_label))
    #

    # Create data
    # N = 60
    # x = section_array[:,0] * section_array[:,1]
    # y = section_array[:,2] * section_array[:,3]
    # z = section_array[:,4] * section_array[:,5]
    #
    # #data = (g1, g2, g3)
    #
    # groups = x_label
    # colors = "bgrcmykw"
    # color_dict = dict()
    # for idx, group in enumerate(groups):
    #     color_dict[group] = colors[idx]
    #
    # # Create plot
    # fig = plt.figure()
    # #ax = fig.add_subplot(1, 1, 1)
    # ax = fig.gca(projection='3d')
    #
    # for xdata, ydata, zdata, group in zip(x, y, z, groups):
    #     if group == 'Check OK':
    #         ax.scatter(x, y, z, alpha= 0.6 if group != 'Weight filter' else 0.2,
    #                    c=color_dict[group], edgecolors='none', s=5, label=group)
    #
    # plt.title('Matplot 3d scatter plot')
    # plt.legend(loc=2)
    # plt.show()



    # for swarm_size in [100, 1000, 10000, 100000, 1000000]:
    #     t1 = time.time()
    #
    #     pso_options = (swarm_size, 0.5, 0.5, 0.5, 100, 1e-8, 1e-8)
    #     results = run_optmizataion(obj, upper_bounds, lower_bounds, lat_press, deltas, algorithm='anysmart',
    #                            fatigue_obj=fat_obj, fat_press_ext_int=fat_press, pso_options=pso_options)[0]
    #     print('Swarm size', swarm_size, 'running time', time.time()-t1, results.get_one_line_string())
    # fat_press_ext_int = list()
    # for pressure in ex.get_geo_opt_fat_press():
    #     fat_press_ext_int.append(((pressure['p_ext']['loaded'], pressure['p_ext']['ballast'],
    #                                pressure['p_ext']['part']),
    #                               (pressure['p_int']['loaded'], pressure['p_int']['ballast'],
    #                                pressure['p_int']['part'])))
    #
    # opt_girder_prop = (0.018, 0.25,0.015, 0,0, 1.1,0.9)
    #
    # results = run_optmizataion(ex.get_geo_opt_object(), lower_bounds, upper_bounds, ex.get_geo_opt_presure(), deltas,
    #                            is_geometric=True, fatigue_obj=ex.get_geo_opt_fatigue(),
    #                            fat_press_ext_int=fat_press_ext_int,
    #                            slamming_press=ex.get_geo_opt_slamming_none(), load_pre=False,
    #                            opt_girder_prop= opt_girder_prop,
    #                            min_max_span=(1,12), tot_len=12)

    # import pickle
    # with open('geo_opt_2.pickle', 'rb') as file:
    #     geo_results = pickle.load(file)
    #
    # print(geo_results.keys())
    # print(geo_results[1][0])
    # for val in range(6):
    #     plot_optimization_results(geo_results[3][1][val])





