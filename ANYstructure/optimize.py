#Optimize structure
import numpy as np
import ANYstructure.calc_structure as calc
import itertools as it
import time
import random
import matplotlib.pyplot as plt
#from pyswarm import pso
import copy
import ANYstructure.helper as hlp
#from opt_problem import MyProblem
from multiprocessing import Pool, cpu_count
import ANYstructure.example_data as test
#import psopy
from math import ceil, floor
from matplotlib import pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import axes3d
from tkinter.filedialog import asksaveasfilename
import csv

def run_optmizataion(initial_structure_obj=None, min_var=None, max_var=None, lateral_pressure=None,
                     deltas=None, algorithm='anysmart', trials=30000, side='p',
                     const_chk = (True,True,True,True,True,True, True),
                     pso_options = (100,0.5,0.5,0.5,100,1e-8,1e-8), is_geometric=False, fatigue_obj = None ,
                     fat_press_ext_int = None,
                     min_max_span = (2,6), tot_len = None, frame_height = 2.5, frame_distance = None,
                     slamming_press = 0, predefined_stiffener_iter = None, processes = None, use_weight_filter = True,
                     load_pre = False, opt_girder_prop = None):
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

    if use_weight_filter:
        if is_geometric or algorithm is 'pso':

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
                                                    predefined_stiffener_iter = predefined_stiffener_iter)

    if algorithm == 'anysmart' and not is_geometric:
        to_return = any_smart_loop(min_var, max_var, deltas, initial_structure_obj, lateral_pressure,
                                   init_filter_weight, side=side, const_chk=const_chk, fat_dict=fat_dict,
                                   fat_press=fat_press_ext_int,slamming_press=slamming_press,
                                   predefiened_stiffener_iter=predefined_stiffener_iter)
        return to_return
    elif algorithm == 'anysmart' and is_geometric:
        return geometric_summary_search(min_var= min_var, max_var=max_var, deltas= deltas,
                                        initial_structure_obj= initial_structure_obj, lateral_pressure=lateral_pressure,
                                        init_filter= init_filter_weight, side= side, const_chk= const_chk,
                                        fat_obj=  fatigue_obj, fat_press= fat_press_ext_int, min_max_span= min_max_span,
                                        tot_len= tot_len, frame_distance = frame_distance,
                                        algorithm= 'anysmart', predefiened_stiffener_iter=predefined_stiffener_iter,
                                        slamming_press = slamming_press, load_pre = load_pre,
                                        opt_girder_prop = opt_girder_prop)
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
    elif algorithm == 'pso' and not is_geometric:
        return particle_search(min_var,max_var,deltas,initial_structure_obj,lateral_pressure,init_filter_weight,side,
                               const_chk,pso_options,fat_dict,fat_press_ext_int,slamming_press)
    elif algorithm == 'pso' and is_geometric:
        return geometric_summary_search(min_var,max_var,deltas, initial_structure_obj,lateral_pressure,
                                        init_filter_weight,side,const_chk,pso_options,fatigue_obj,fat_press_ext_int,
                                        min_max_span,tot_len,frame_height,frame_cross_a, 'pso')
    else:
        return None

def any_optimize_loop(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                      side='p',const_chk=(True,True,True,True,True), fat_dict = None, fat_press = None,
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
                   side='p',const_chk=(True,True,True,True,True,True,True), fat_dict = None, fat_press = None,
                   slamming_press = 0, predefiened_stiffener_iter = None, processes = None):
    '''
    Trying to be smart
    :param min_var:
    :param max_var:
    :param initial_structure:
    :return:
    '''

    # if predefiened_stiffener_iter is None:
    #     structure_to_check = any_get_all_combs(min_var, max_var, deltas, init_weight=init_filter)
    # else:
    #     #structure_to_check = [obj.get_tuple() for obj in predefiened_stiffener_iter]
    #     structure_to_check = any_get_all_combs(min_var, max_var, deltas, init_weight=init_filter,
    #                                            predef_stiffeners=predefiened_stiffener_iter)
    #     init_filter = get_initial_weight(initial_structure_obj, lateral_pressure, min_var, max_var, deltas, 10000,
    #                                      fat_dict, fat_press, predefiened_stiffener_iter)

    if predefiened_stiffener_iter is None:
        structure_to_check = any_get_all_combs(min_var, max_var, deltas)
    else:
        structure_to_check = any_get_all_combs(min_var, max_var, deltas,predef_stiffeners=[item.get_tuple() for item
                                                                                           in predefiened_stiffener_iter])

    main_result = get_filtered_results(structure_to_check, initial_structure_obj,lateral_pressure,
                                       init_filter_weight=init_filter, side=side,chk=const_chk, fat_dict=fat_dict,
                                       fat_press=fat_press, slamming_press=slamming_press, processes=processes)

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

    new_struc_obj = create_new_structure_obj(initial_structure_obj,[item for item in ass_var])
    new_calc_obj = create_new_calc_obj(initial_structure_obj,[item for item in ass_var])[0]

    return new_struc_obj, new_calc_obj, fat_dict, True, main_fail

def any_smart_loop_geometric(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                             side='p',const_chk=(True,True,True,True,True,True), fat_obj = None, fat_press = None,
                             slamming_press = None, predefiened_stiffener_iter=None, processes = None):
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
                                 predefiened_stiffener_iter=this_predefiened_objects, processes=processes)
        # TODO-any set check if not solution acceptable.
        all_obj.append(opt_obj)
        idx += 1

    return all_obj

def particle_search(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                    side='p',const_chk=(True,True,True,True),
                    pso_options=(10000,0.5,0.5,0.5,100,1e-8,1e-8), fat_dict = None, fat_press = None,
                    slamming_press = 0):
    '''
    Searchin using Particle Swarm Search (http://pythonhosted.org/pyswarm/)

    :param min_var:
    :param max_var:
    :param deltas:
    :param initial_structure_obj:
    :param lateral_pressure:
    :param side:
    :param const_chk:
        :param pso_options:
    :return:
    '''

    args = (initial_structure_obj,lateral_pressure,init_filter,side,const_chk,min_var[6],min_var[7],
            fat_dict,fat_press, slamming_press)
    # Multiprocessing is not efficient if the swarm size is below 500 (approximatly).
    if pso_options[0] < 500:
        xopt, fopt = pso(calc_weight_pso, min_var[0:6], max_var[0:6],
                         f_ieqcons=any_constraints_all_number,swarmsize=pso_options[0],
                         omega=pso_options[1], phip=pso_options[2],phig=pso_options[3],
                         maxiter=pso_options[4], minstep=pso_options[5], minfunc=pso_options[6],
                         args=args)
    else:
        xopt, fopt = pso(calc_weight_pso, min_var[0:6], max_var[0:6],
                         f_ieqcons=any_constraints_all_number,swarmsize=pso_options[0],
                         omega=pso_options[1], phip=pso_options[2],phig=pso_options[3],
                         maxiter=pso_options[4], minstep=pso_options[5], minfunc=pso_options[6],
                         args=args)

    ass_var = xopt
    np.append(ass_var,[args[5],args[6]])
    new_structure_obj = create_new_structure_obj(initial_structure_obj,[round(item,5) for item in ass_var])
    new_calc_obj = create_new_calc_obj(initial_structure_obj,[round(item,5) for item in ass_var])[0]
    args = list(args)
    args[0] = new_structure_obj

    return new_structure_obj, new_calc_obj, fat_dict, True if any_constraints_all_number(xopt, *args) == 0 else False

def particle_search_geometric(min_var=None,max_var=None,deltas = None, initial_structure_obj=None,lateral_pressure=None,
                              init_filter = float('inf'),side='p',const_chk=(True,True,True,True, True, True),
                              pso_options=(100,0.5,0.5,0.5,100,1e-8,1e-8), fat_obj = None, fat_press = None):
    '''
    Searching using Particle Swarm Search (http://pythonhosted.org/pyswarm/) for a given section.
    '''

    all_obj = []

    for struc_obj, lat_press in zip(initial_structure_obj, lateral_pressure):

        opt_obj = particle_search(min_var=min_var, max_var=max_var,initial_structure_obj=struc_obj,
                                  lateral_pressure=lat_press,
                                  side=side, const_chk=const_chk, pso_options=pso_options, deltas=deltas)
        # TODO-any set check if not solution acceptable.
        all_obj.append(opt_obj)

    return all_obj

def geometric_summary_search(min_var=None,max_var=None,deltas = None, initial_structure_obj=None,lateral_pressure=None,
                             init_filter = float('inf'),side='p',const_chk=(True,True,True,True, True, True),
                             pso_options=(100,0.5,0.5,0.5,100,1e-8,1e-8), fat_obj = None, fat_press = None,
                             min_max_span = (2,6), tot_len = None, frame_distance = None,
                             algorithm = 'anysmart', predefiened_stiffener_iter=None, reiterate = True,
                             processes = None, slamming_press = None, load_pre = False, opt_girder_prop = None):

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
            while similar_count != no_of_fractions*2:
                if similar_count > no_of_fractions*2:
                    for var_dict in [working_objects, working_lateral, working_fatigue,
                                     working_fatigue_press, working_slamming]:

                        var_dict[no_of_fractions].pop(0)
                        var_dict[no_of_fractions].pop(int(floor(len(working_objects[no_of_fractions]) / 2)))
                    # working_objects[no_of_fractions].pop(0)
                    # working_objects[no_of_fractions].pop(floor(int(len(working_objects)/2)))
                    # working_lateral[no_of_fractions].pop(0)
                    # working_lateral[no_of_fractions].pop(floor(int(len(working_objects)/2)))
                    similar_count -= 2
                else:
                    #print(no_of_fractions, int(ceil(len(working_objects[no_of_fractions])/2)))
                    obj_start, obj_stop = copy.deepcopy(working_objects[no_of_fractions][0]),\
                                          copy.deepcopy(working_objects[no_of_fractions]
                                                        [int(ceil(len(working_objects[no_of_fractions])/2))])
                    fat_obj_start, fat_obj_stop = copy.deepcopy(working_fatigue[no_of_fractions][0]), \
                                                  copy.deepcopy(working_fatigue[no_of_fractions]
                                                                [int(ceil(len(working_objects[no_of_fractions])/2))])

                    lat_start, lat_stop = working_lateral[no_of_fractions][0], \
                                          working_lateral[no_of_fractions][int(ceil(
                                              len(working_objects[no_of_fractions])/2))]

                    fat_press_start, fat_press_stop = working_fatigue_press[no_of_fractions][0], \
                                                      working_fatigue_press[no_of_fractions][
                                                          int(ceil(len(working_objects[no_of_fractions])/2))]
                    slam_start, slam_stop = working_slamming[no_of_fractions][0], \
                                            working_slamming[no_of_fractions][
                                                int(ceil(len(working_objects[no_of_fractions])/2))]

                    for work, work_input in zip([working_objects[no_of_fractions], working_lateral[no_of_fractions],
                                                 working_fatigue[no_of_fractions],
                                                 working_fatigue_press[no_of_fractions],
                                                 working_slamming[no_of_fractions]],
                                                [(obj_start, obj_stop), (lat_start, lat_stop),
                                                 (fat_obj_start, fat_obj_stop), (fat_press_start, fat_press_stop),
                                                 (slam_start, slam_stop)]):

                        work.insert(0, work_input[0])
                        work.insert(int(ceil(len(working_objects[no_of_fractions]) / 2)), work_input[1])

                    # working_objects[no_of_fractions].insert(0,obj_start)
                    # working_objects[no_of_fractions].insert(int(ceil(len(working_objects)/2)), obj_stop)
                    # working_lateral[no_of_fractions].insert(0,lat_start)
                    # working_lateral[no_of_fractions].insert(int(ceil(len(working_objects)/2)), lat_stop)
                    # working_fatigue[no_of_fractions].insert(0,fat_obj_start)
                    # working_fatigue[no_of_fractions].insert(int(ceil(len(working_objects)/2)), fat_obj_stop)
                    # working_fatigue_press[no_of_fractions].insert(0,fat_press_start)
                    # working_fatigue_press[no_of_fractions].insert(int(ceil(len(working_objects)/2)), fat_press_stop)
                    # working_slamming[no_of_fractions].insert(0,slam_start)
                    # working_slamming[no_of_fractions].insert(int(ceil(len(working_objects)/2)), slam_stop)
                    similar_count += 2
        for no_of_fractions, struc_objects in working_objects.items():
            for struc_obj in struc_objects:
                struc_obj.set_span(tot_len/no_of_fractions)

        solution_found, iterations = False, 0

        while not solution_found:
            iterations += 1
            if iterations != 1:
                min_var[0:6] += deltas/2
                max_var[0:6] -= deltas/2

            if algorithm is 'pso':
                opt_objects = particle_search_geometric(min_var=min_var,max_var=max_var,deltas=deltas,
                                                        initial_structure_obj=working_objects[no_of_fractions],
                                                        lateral_pressure=working_lateral[no_of_fractions],
                                                        init_filter = init_filter,side=side,const_chk=const_chk,
                                                        pso_options=pso_options, fat_obj = fat_obj,
                                                        fat_press = fat_press)
            elif algorithm is 'anysmart':
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
                                                           predefiened_stiffener_iter = predefiened_stiffener_iter)
                # TODO fatigue and slamming implemetation

            # Finding weight of this solution.

            tot_weight, frame_spacings, valid, width = 0, [None for dummy in range(len(opt_objects))], True, 10
            #print('Weight for', no_of_fractions)
            for count, opt in enumerate(opt_objects):
                obj = opt[0]

                if opt[3]:
                    weigth_to_add = calc_weight((obj.get_s(),obj.get_pl_thk(),obj.get_web_h(),obj.get_web_thk(),
                                               obj.get_fl_w(),obj.get_fl_thk(),obj.get_span(),width), prt=False)
                    tot_weight += weigth_to_add
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
            elif iterations == 2:
                solution_found = True  # Only iterate once.

            if predefiened_stiffener_iter is not None or not reiterate:
                solution_found = True  # Noe solution may be found, but in this case no more iteations.

        results[no_of_fractions] = tot_weight, opt_objects
    return results

def any_find_min_weight_var(var):
    '''
    Find the minimum weight of the inpu
    :param min:
    :param max:
    :return:
    '''

    return min(map(calc_weight))


def any_constraints_all(x,obj,lat_press,init_weight,side='p',chk=(True,True,True,True, True, True, True),
                        fat_dict = None, fat_press = None, slamming_press = 0, print_result = False):
    '''
    Checking all constraints defined.
    :param x:
    :return:
    '''
    all_checks = [0,0,0,0,0,0,0,0]
    this_weight = calc_weight(x)
    if this_weight > init_weight:
        weigt_frac = this_weight / init_weight
        if print_result:
            pass
            # print('Weights', calc_weight(x), ' > ', init_weight,
            #       calc_object[0].get_one_line_string(), init_weight, False)
        all_checks[0] = weigt_frac
        return False, 'Weight filter', x, all_checks

    calc_object = create_new_calc_obj(obj, x, fat_dict)

    # Section modulus
    if chk[0]:
        section_modulus = min(calc_object[0].get_section_modulus())
        min_section_modulus = calc_object[0].get_dnv_min_section_modulus(lat_press)
        section_frac = min_section_modulus / section_modulus
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
        buckling_results = calc_object[0].calculate_buckling_all(design_lat_press=lat_press, checked_side=side)
        all_checks[3] = max(buckling_results)
        if not all([uf<=1 for uf in buckling_results]):
            if print_result:
                print('Buckling',calc_object[0].get_one_line_string(), False)
            return False, 'Buckling', x, all_checks

    # Minimum plate thickness
    if chk[1]:
        act_pl_thk = calc_object[0].get_plate_thk()
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
    if chk[4] and fat_dict is not None:
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

def any_constraints_all_number(x,*args):
    '''
    Checking all constraints defined.
    :param x:
    :return:
    '''

    # if calc_weight_pso(x) > init_weight:
    #     return -1

    obj, lat_press, init_weight, side, chk = args[0:5]
    fat_dict, fat_press = args[7], args[8]
    calc_object = create_new_calc_obj(obj, x, fat_dict)
    slamming_press = args[9]

    # Section modulus
    if chk[0]:
        if not min(calc_object[0].get_section_modulus()) > calc_object[0].get_dnv_min_section_modulus(lat_press) :
            return -1

    # Local stiffener buckling
    if not calc_object[0].buckling_local_stiffener():
        return -1
    # Buckling
    if chk[3]:
        if not all([uf<=1 for uf in calc_object[0].calculate_buckling_all(design_lat_press=lat_press,
                                                                          checked_side=side)]):
            return -1
    #Minimum plate thickeness
    if chk[1]:
        if not calc_object[0].get_plate_thk()>calc_object[0].get_dnv_min_thickness(lat_press)/1000:
            return -1
    # Shear area
    if chk[2]:
        if not calc_object[0].get_shear_area()>calc_object[0].get_minimum_shear_area(lat_press):
            return -1

    # Fatigue
    try:
        if chk[4] and fat_dict is not None:
            if calc_object[1].get_total_damage(ext_press=fat_press[0], int_press=fat_press[1]) * \
                    calc_object[1].get_dff() > 1:
                return -1
    except IndexError:
        pass

    # Slamming
    if chk[5] and slamming_press != 0:
        if not calc_object[0].check_all_slamming(slamming_press):
            return -1
    #print('OK')
    return 0

def constraint_geometric(fractions, *args):
    return sum(fractions) == 1

def pso_constraint_geometric(x,*args):
    ''' The sum of the fractions must be 1.'''
    return 1-sum(x)

def create_new_calc_obj(init_obj,x, fat_dict=None):
    '''
    Returns a new calculation object to be used in optimization
    :param init_obj:
    :return:
    '''
    x_old = [init_obj.get_s(), init_obj.get_plate_thk(), init_obj.get_web_h() , init_obj.get_web_thk(),
             init_obj.get_fl_w() ,init_obj.get_fl_thk(), init_obj.get_span(), init_obj.get_lg()]

    sigma_y1_new = stress_scaling(init_obj.get_sigma_y1(), init_obj.get_plate_thk(), x[1])
    sigma_y2_new = stress_scaling(init_obj.get_sigma_y2(), init_obj.get_plate_thk(), x[1])
    tau_xy_new = stress_scaling(init_obj.get_tau_xy(), init_obj.get_plate_thk(), x[1])
    sigma_x_new = stress_scaling_area(init_obj.get_sigma_x(),
                                      sum(get_field_tot_area(x_old)),
                                      sum(get_field_tot_area(x)))

    try:
        stf_type = x[8]
    except IndexError:
        stf_type = init_obj.get_stiffener_type()

    main_dict = {'mat_yield': [init_obj.get_fy(), 'Pa'],'span': [init_obj.get_span(), 'm'],
                                'spacing': [x[0], 'm'],'plate_thk': [x[1], 'm'],'stf_web_height':[ x[2], 'm'],
                                'stf_web_thk': [x[3], 'm'],'stf_flange_width': [x[4], 'm'],
                                'stf_flange_thk': [x[5], 'm'],'structure_type': [init_obj.get_structure_type(), ''],
                                'stf_type': [stf_type, ''],'sigma_y1': [sigma_y1_new, 'MPa'],
                                'sigma_y2': [sigma_y2_new, 'MPa'],'sigma_x': [sigma_x_new, 'MPa'],
                                'tau_xy': [tau_xy_new, 'MPa'],'plate_kpp': [init_obj.get_kpp(), ''],
                                'stf_kps': [init_obj.get_kps(), ''],'stf_km1': [init_obj.get_km1(), ''],
                                'stf_km2': [init_obj.get_km2(), ''],'stf_km3': [init_obj.get_km3(), '']}
    if fat_dict == None:
        return calc.CalcScantlings(main_dict), None
    else:
        return calc.CalcScantlings(main_dict), calc.CalcFatigue(main_dict, fat_dict)

def create_new_structure_obj(init_obj, x, fat_dict=None):
    '''
    Returns a new calculation object to be used in optimization
    :param init_obj:
    :return:
    '''
    x_old = [init_obj.get_s(), init_obj.get_plate_thk(), init_obj.get_web_h() , init_obj.get_web_thk(),
             init_obj.get_fl_w() ,init_obj.get_fl_thk(), init_obj.get_span(), init_obj.get_lg()]

    sigma_y1_new = stress_scaling(init_obj.get_sigma_y1(), init_obj.get_plate_thk(), x[1])
    sigma_y2_new = stress_scaling(init_obj.get_sigma_y2(), init_obj.get_plate_thk(), x[1])
    tau_xy_new = stress_scaling(init_obj.get_tau_xy(), init_obj.get_plate_thk(), x[1])
    sigma_x_new = stress_scaling_area(init_obj.get_sigma_x(),sum(get_field_tot_area(x_old)),sum(get_field_tot_area(x)))

    try:
        stf_type = x[8]
    except IndexError:
        stf_type = init_obj.get_stiffener_type()

    main_dict = {'mat_yield': [init_obj.get_fy(), 'Pa'], 'span': [init_obj.get_span(), 'm'],
                               'spacing': [x[0], 'm'], 'plate_thk': [x[1], 'm'], 'stf_web_height': [x[2], 'm'],
                               'stf_web_thk': [x[3], 'm'], 'stf_flange_width': [x[4], 'm'],
                               'stf_flange_thk': [x[5], 'm'], 'structure_type': [init_obj.get_structure_type(), ''],
                               'stf_type': [stf_type, ''], 'sigma_y1': [sigma_y1_new, 'MPa'],
                               'sigma_y2': [sigma_y2_new, 'MPa'], 'sigma_x': [sigma_x_new, 'MPa'],
                               'tau_xy': [tau_xy_new, 'MPa'], 'plate_kpp': [init_obj.get_kpp(), ''],
                               'stf_kps': [init_obj.get_kps(), ''], 'stf_km1': [init_obj.get_km1(), ''],
                               'stf_km2': [init_obj.get_km2(), ''], 'stf_km3': [init_obj.get_km3(), '']}
    if fat_dict == None:
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

def stress_scaling(sigma_old,t_old,t_new):
    if t_new <= t_old: #decreasing the thickness
        sigma_new = sigma_old*(t_old/(t_old-abs((t_old-t_new))))
        assert sigma_new >= sigma_old, 'ERROR no stress increase: \n' \
                                      't_old '+str(t_old)+' sigma_old '+str(sigma_old)+ \
                                      '\nt_new '+str(t_new)+' sigma_new '+str(sigma_new)

    else: #increasing the thickness
        sigma_new = sigma_old*(t_old/(t_old+0.5*abs((t_old-t_new))))
        assert sigma_new <= sigma_old, 'ERROR no stress reduction: \n' \
                                      't_old '+str(t_old)+' sigma_old '+str(sigma_old)+ \
                                      '\nt_new '+str(t_new)+' sigma_new '+str(sigma_new)
    return sigma_new

def stress_scaling_area(sigma_old,a_old,a_new):
    ''' Scale stresses using input area '''

    if a_new <= a_old: #decreasing the thickness
        sigma_new = sigma_old*(a_old/(a_old-abs((a_old-a_new))))
        assert sigma_new >= sigma_old, 'ERROR no stress increase: \n' \
                                      't_old '+str(a_old)+' sigma_old '+str(sigma_old)+ \
                                      '\nt_new '+str(a_new)+' sigma_new '+str(sigma_new)
    else: #increasing the thickness
        sigma_new = sigma_old*(a_old/(a_old+0.5*abs((a_old-a_new))))
        assert sigma_new <= sigma_old, 'ERROR no stress reduction: \n' \
                                      't_old '+str(a_old)+' sigma_old '+str(sigma_old)+ \
                                      '\nt_new '+str(a_new)+' sigma_new '+str(sigma_new)
    #print('a_old', a_old, 'sigma_old', sigma_old, '|', 'a_new', a_new, 'sigma_new',sigma_new)
    return sigma_new

def get_filtered_results(iterable_all,init_stuc_obj,lat_press,init_filter_weight,side='p',
                         chk=(True,True,True,True,True,True,True),fat_dict = None, fat_press = None,
                         slamming_press=None, processes = None):
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
    #print('Init filter weigh', init_filter_weight)

    iter_var = ((item,init_stuc_obj,lat_press,init_filter_weight,side,chk,fat_dict,fat_press,slamming_press)
                for item in iterable_all)
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

def any_get_all_combs(min_var, max_var,deltas, init_weight = float('inf'), predef_stiffeners = None):
    '''
    Calulating initial values.
    :param min:
    :param max:
    :return:
    '''

    spacing_array = (np.arange(min_var[0], max_var[0]+ deltas[0], deltas[0])) if min_var[0] != max_var[0] \
        else np.array([min_var[0]])
    spacing_array = spacing_array[spacing_array <= max_var[0]]

    pl_thk_array = (np.arange(min_var[1], max_var[1]+ deltas[1], deltas[1])) if min_var[1] != max_var[1] \
        else np.array([min_var[1]])
    pl_thk_array = pl_thk_array[pl_thk_array <= max_var[1]]

    if predef_stiffeners is not None:
        predef_iterable = list()
        for pre_str in predef_stiffeners:
            for spacing in spacing_array: #TODO not getting the stiffener types
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

    flange_thk_array = (np.arange(min_var[5], max_var[5]+ deltas[5], deltas[5])) if min_var[5] != max_var[5] \
        else np.array([min_var[5]])
    flange_thk_array = flange_thk_array[flange_thk_array <= max_var[5]]

    span_array = (np.arange(min_var[6], max_var[6], deltas[4])) if min_var[6] != max_var[6] \
        else np.array([min_var[6]])

    girder_array = (np.arange(min_var[7], max_var[7], deltas[7])) if min_var[7] != max_var[7] \
        else np.array([min_var[7]])

    comb = it.product(spacing_array, pl_thk_array, web_h_array, web_thk_array, flange_w_array, flange_thk_array,
                      span_array,girder_array)

    # comb = product_any(spacing_array, pl_thk_array, web_h_array, web_thk_array, flange_w_array, flange_thk_array,
    #                   span_array,girder_array,weight=init_weight)

    return comb

def get_initial_weight(obj,lat_press,min_var,max_var,deltas,trials,fat_dict,fat_press, predefined_stiffener_iter):
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
                               fat_dict=fat_dict,fat_press = fat_press)[0]:
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
    import ANYstructure.example_data as ex
    obj_dict = ex.obj_dict
    fat_obj = ex.get_fatigue_object()
    fp = ex.get_fatigue_pressures()
    fat_press = ((fp['p_ext']['loaded'],fp['p_ext']['ballast'],fp['p_ext']['part']),
                 (fp['p_int']['loaded'],fp['p_int']['ballast'],fp['p_int']['part']))
    x0 = [obj_dict['spacing'][0], obj_dict['plate_thk'][0], obj_dict['stf_web_height'][0], obj_dict['stf_web_thk'][0],
          obj_dict['stf_flange_width'][0], obj_dict['stf_flange_thk'][0], obj_dict['span'][0], 10]

    obj = calc.Structure(obj_dict)
    lat_press = 271.124
    calc_object = calc.CalcScantlings(obj_dict)
    lower_bounds = np.array([0.6, 0.01, 0.3, 0.01, 0.1, 0.01, 3.5, 10])
    upper_bounds = np.array([0.8, 0.02, 0.5, 0.02, 0.22, 0.03, 3.5, 10])
    deltas = np.array([0.025, 0.0025, 0.025, 0.0025, 0.025, 0.0025])


    t1 = time.time()
    #
    results = run_optmizataion(obj, lower_bounds,upper_bounds, lat_press, deltas, algorithm='anysmart',
                               fatigue_obj=fat_obj, fat_press_ext_int=fat_press, use_weight_filter=True,
                               predefined_stiffener_iter=hlp.helper_read_section_file('sections.csv', obj=obj))
    # print(results)

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
    fat_press_ext_int = list()
    for pressure in ex.get_geo_opt_fat_press():
        fat_press_ext_int.append(((pressure['p_ext']['loaded'], pressure['p_ext']['ballast'],
                                   pressure['p_ext']['part']),
                                  (pressure['p_int']['loaded'], pressure['p_int']['ballast'],
                                   pressure['p_int']['part'])))

    opt_girder_prop = (0.018, 0.25,0.015, 0,0, 1.1,0.9)

    # results = run_optmizataion(ex.get_geo_opt_object(), lower_bounds, upper_bounds, ex.get_geo_opt_presure(), deltas,
    #                            is_geometric=True, fatigue_obj=ex.get_geo_opt_fatigue(),
    #                            fat_press_ext_int=fat_press_ext_int,
    #                            slamming_press=ex.get_geo_opt_slamming_none(), load_pre=False,
    #                            opt_girder_prop= opt_girder_prop,
    #                            predefined_stiffener_iter=hlp.helper_read_section_file('sections.csv', obj=),
    #                            min_max_span=(1,12), tot_len=12)

    # import pickle
    # with open('geo_opt_2.pickle', 'rb') as file:
    #     geo_results = pickle.load(file)
    #
    # print(geo_results.keys())
    # print(geo_results[1][0])
    # for val in range(6):
    #     plot_optimization_results(geo_results[3][1][val])





