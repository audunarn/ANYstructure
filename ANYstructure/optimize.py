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


def run_optmizataion(initial_structure_obj=None, min_var=None,max_var=None,lateral_pressure=None,
                     deltas=None,algorithm='anysmart',trials=30000,side='p',
                     const_chk = (True,True,True,True,True,True, True),
                     pso_options = (100,0.5,0.5,0.5,100,1e-8,1e-8),is_geometric=False, fatigue_obj = None ,
                     fat_press_ext_int = None,
                     min_max_span = (2,6), tot_len = 12, frame_height = 2.5, frame_distance = None,
                     slamming_press = 0, predefined_stiffener_iter = None, processes = None):
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

    # init_filter_weight = get_initial_weight(obj=initial_structure_obj,lat_press=lateral_pressure,min_var=min_var,
    #                                         max_var=max_var,deltas=deltas,trials=30000,
    #                                         fat_dict=fatigue_obj.get_fatigue_properties(),
    #                                         fat_press=fat_press_ext_int) \
    #     if algorithm != 'pso' else float('inf')

    init_filter_weight = float('inf')

    if fatigue_obj == None and not is_geometric:
        fat_dict = None
        init_filter_weight = get_initial_weight(obj=initial_structure_obj, lat_press=lateral_pressure, min_var=min_var,
                                                max_var=max_var, deltas=deltas, trials=30000,
                                                fat_dict=None, fat_press=None)  \
            if algorithm != 'pso' else float('inf')
    elif not is_geometric:
        fat_dict = fatigue_obj.get_fatigue_properties()
        if predefined_stiffener_iter is None:
            init_filter_weight = get_initial_weight(obj=initial_structure_obj, lat_press=lateral_pressure,
                                                    min_var=min_var, max_var=max_var, deltas=deltas, trials=30000,
                                                    fat_dict=fatigue_obj.get_fatigue_properties(),
                                                    fat_press=fat_press_ext_int) if algorithm != 'pso' else float('inf')
        else:
            init_filter_weight = float('inf')

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
                                        slamming_press = slamming_press)
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
    elif algorithm == 'pygmo_alg' and not is_geometric:
        return algorithmic_search(min_var,max_var,deltas,initial_structure_obj,lateral_pressure,init_filter_weight,side,
                                  const_chk,pso_options)
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
    for spacing in np.arange(min_var[0],max_var[0]+deltas[0],deltas[0]):
        for plate_thk in np.arange(min_var[1],max_var[1]+deltas[1],deltas[1]):
            for stf_web_h in np.arange(min_var[2],max_var[2]+deltas[2],deltas[2]):
                for stf_web_thk in np.arange(min_var[3],max_var[3]+deltas[3],deltas[3]):
                    for stf_flange_width in np.arange(min_var[4],max_var[4]+deltas[4],deltas[4]):
                        for stf_flange_thk in np.arange(min_var[5],max_var[5]+deltas[5],deltas[5]):
                            var_x = np.array([spacing, plate_thk, stf_web_h, stf_web_thk, stf_flange_width,
                                              stf_flange_thk,min_var[6],min_var[7]])
                            if any_constraints_all(var_x,initial_structure_obj,lat_press=lateral_pressure,
                                                   init_weight=min_weight,side=side,chk=const_chk,
                                                   fat_dict = fat_dict, fat_press = fat_press,
                                                   slamming_press=slamming_press) is not False:
                                current_weight = calc_weight(var_x)
                                if current_weight < min_weight:
                                    iter_count+=1
                                    min_weight = current_weight
                                    ass_var = var_x
                                    plot_x.append(iter_count)
                                    plot_y.append(min_weight)
    plt.plot(plot_x,plot_y)
    plt.show()
    return create_new_structure_obj(initial_structure_obj,[round(item,5) for item in ass_var]),\
           create_new_calc_obj(initial_structure_obj,[round(item,5) for item in ass_var])[0], \
           fat_dict

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
    print(min_var, max_var, deltas)
    if predefiened_stiffener_iter is None:
        structure_to_check = any_get_all_combs(min_var, max_var, deltas, init_weight=init_filter)
    else:
        structure_to_check = [obj.get_tuple() for obj in predefiened_stiffener_iter]
        structure_to_check = any_get_all_combs(min_var, max_var, deltas, init_weight=init_filter,
                                               predef_stiffeners=structure_to_check)

    main_iter = get_filtered_results(structure_to_check, initial_structure_obj,lateral_pressure
                                     ,init_filter_weight=init_filter, side=side,chk=const_chk, fat_dict=fat_dict,
                                     fat_press=fat_press, slamming_press=slamming_press)

    ass_var=None
    current_weight = float('inf')
    for item in main_iter:
        item_weight = calc_weight(item)
        if item_weight < current_weight:
            ass_var = item
            current_weight = item_weight

    if ass_var == None:
        return ass_var

    new_struc_obj = create_new_structure_obj(initial_structure_obj,[item for item in ass_var])
    new_calc_obj = create_new_calc_obj(initial_structure_obj,[item for item in ass_var])[0]

    return new_struc_obj, new_calc_obj, fat_dict, \
           True if any_constraints_all(ass_var, new_struc_obj, lateral_pressure, current_weight,side,
                                       const_chk,fat_dict,fat_press,slamming_press) is not False else False

def any_smart_loop_geometric(min_var,max_var,deltas,initial_structure_obj,lateral_pressure, init_filter = float('inf'),
                             side='p',const_chk=(True,True,True,True,True,True), fat_obj = None, fat_press = None,
                             slamming_press = None, predefiened_stiffener_iter=None, processes = None):
    ''' Searching multiple sections using the smart loop. '''

    all_obj = []
    idx = 0

    for struc_obj, lat_press, fatigue_obj, fatigue_press, slam_press in zip(initial_structure_obj, lateral_pressure,
                                                                            fat_obj, fat_press, slamming_press):

        if predefiened_stiffener_iter is not None:
            this_predefiened_stiffener_iter = any_get_all_combs(min_var=min_var, max_var=max_var,deltas=deltas,
                                                                predef_stiffeners=predefiened_stiffener_iter)
            temp_predef = list()
            for x in predefiened_stiffener_iter:
                xvar = list(x)
                xvar.append(struc_obj.get_span())
                xvar.append(struc_obj.get_lg())
                temp_predef.append(tuple(xvar))

            this_predefiened_stiffener_iter = [create_new_structure_obj(struc_obj, xtup) for xtup in
                                               this_predefiened_stiffener_iter]
        else:
            this_predefiened_stiffener_iter = None

        opt_obj = any_smart_loop(min_var = min_var,max_var = max_var,deltas = deltas,initial_structure_obj = struc_obj,
                                 lateral_pressure = lat_press, init_filter = init_filter, side=side,
                                 const_chk=const_chk, fat_dict = fatigue_obj.get_fatigue_properties(),
                                 fat_press = fatigue_press, slamming_press = slam_press,
                                 predefiened_stiffener_iter=this_predefiened_stiffener_iter)
        # TODO-any set check if not solution acceptable.
        all_obj.append(opt_obj)

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
                             min_max_span = (2,6), tot_len = 12, frame_distance = None,
                             algorithm = 'anysmart', predefiened_stiffener_iter=None, reiterate = True,
                             processes = None, slamming_press = None):

    '''Geometric optimization of all relevant sections. '''
    # Checking the number of initial objects and adding if number of fraction is to be changed.

    found_max, found_min = False, False
    for frames in range(1,100):
        frame_count = frames
        if tot_len/frames <= min_max_span[1] and found_min is False:
            min_frame_count = frame_count
            found_min = True
        if tot_len/frames <= min_max_span[0] and found_max is False:
            max_frame_cont = frame_count - 1
            found_max = True
        if found_min and found_max:
            break
    results = {}
    # print('Frame count min/max: ', min_frame_count, max_frame_cont)
    # print('Initial objects: ', [print(type(obj)) for obj in initial_structure_obj])
    # print('Initial lateral: ', lateral_pressure)
    working_objects = {}
    working_lateral = {}
    working_fatigue = {}
    working_fatigue_press = {}
    working_slamming = {}

    for no_of_fractions in range(min_frame_count, max_frame_cont+1):
        # Create fraction varables
        frac_var,min_frac,max_frac = [],[],[]

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
                        var_dict[no_of_fractions].pop(int(floor(len(working_objects) / 2)))
                    # working_objects[no_of_fractions].pop(0)
                    # working_objects[no_of_fractions].pop(floor(int(len(working_objects)/2)))
                    # working_lateral[no_of_fractions].pop(0)
                    # working_lateral[no_of_fractions].pop(floor(int(len(working_objects)/2)))
                    similar_count -= 2
                else:
                    obj_start, obj_stop = copy.deepcopy(working_objects[no_of_fractions][0]),\
                                          copy.deepcopy(working_objects[no_of_fractions][int(len(working_objects)/2)])
                    fat_obj_start, fat_obj_stop = copy.deepcopy(fat_obj[no_of_fractions][0]), \
                                                  copy.deepcopy(fat_obj[no_of_fractions][int(len(working_objects)/2)])
                    lat_start, lat_stop = working_lateral[no_of_fractions][0], \
                                          working_lateral[no_of_fractions][int(ceil(len(working_objects)/2))]
                    fat_press_start, fat_press_stop = working_fatigue_press[no_of_fractions][0], \
                                                      working_fatigue_press[no_of_fractions][
                                                          int(ceil(len(working_objects)/2))]
                    slam_start, slam_stop = working_slamming[no_of_fractions][0], \
                                            working_slamming[no_of_fractions][int(ceil(len(working_objects)/2))]

                    for work, work_input in zip([working_objects[no_of_fractions], working_lateral[no_of_fractions],
                                                 working_fatigue[no_of_fractions],
                                                 working_fatigue_press[no_of_fractions],
                                                 working_slamming[no_of_fractions]],
                                                [(obj_start, obj_stop), (lat_start, lat_stop),
                                                 (fat_obj_start, fat_obj_stop), (fat_press_start, fat_press_stop),
                                                 (slam_start, slam_stop)]):

                        work[no_of_fractions].insert(0, work_input[0])
                        work[no_of_fractions].insert(int(ceil(len(working_objects) / 2)), work_input[1])


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

            for count, opt in enumerate(opt_objects):
                obj = opt[0]
                if opt[3]:
                    tot_weight += calc_weight((obj.get_s(),obj.get_pl_thk(),obj.get_web_h(),obj.get_web_thk(),
                                               obj.get_fl_w(),obj.get_fl_thk(),obj.get_span(),width), prt=False)
                    if frame_spacings[count // 2] is None:
                        frame_spacings[count // 2] = obj.get_s()
                else:
                    # In this case there are no applicable solutions found in the specified dimension ranges.
                    tot_weight += float('inf')
                    valid = False
            if valid:
                #print(frame_distance)
                for frame in range(int(count/2)):
                    frame_height = 2.5 if frame_distance is None else frame_distance['start_dist'] + \
                                                                      (frame_distance['stop_dist']-
                                                                       frame_distance['start_dist']) * \
                                                                      ((frame+1)/no_of_fractions)
                    pl_area, stf_area = 0.018 * width, 0.25 * 0.015 * (10//frame_spacings[frame])
                    tot_weight += (pl_area + stf_area) * frame_height * 7850
                    solution_found = True
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
    #calc_object = create_new_calc_obj(obj, x, fat_dict)

    if calc_weight(x) > init_weight:
        if print_result:
            pass
            # print('Weights', calc_weight(x), ' > ', init_weight,
            #       calc_object[0].get_one_line_string(), init_weight, False)
        return False

    calc_object = create_new_calc_obj(obj, x, fat_dict)

    # Section modulus
    if chk[0]:
        if not min(calc_object[0].get_section_modulus()) > calc_object[0].get_dnv_min_section_modulus(lat_press):
            if print_result:
                print('Section modulus',calc_object[0].get_one_line_string(), False)
            return False

    # Local stiffener buckling
    if chk[6]:
        if not calc_object[0].buckling_local_stiffener():
            if print_result:
                print('Local stiffener buckling',calc_object[0].get_one_line_string(), False)
            return False

    # Buckling
    if chk[3]:
        if not all([uf<=1 for uf in calc_object[0].calculate_buckling_all(design_lat_press=lat_press,
                                                                          checked_side=side)]):
            if print_result:
                print('Buckling',calc_object[0].get_one_line_string(), False)
            return False
    # Minimum plate thickeness
    if chk[1]:
        if not calc_object[0].get_plate_thk()>calc_object[0].get_dnv_min_thickness(lat_press)/1000:
            if print_result:
                print('Minimum plate thickeness',calc_object[0].get_one_line_string(), False)
            return False
    # Shear area
    if chk[2]:
        if not calc_object[0].get_shear_area()>calc_object[0].get_minimum_shear_area(lat_press):
            if print_result:
                print('Shear area',calc_object[0].get_one_line_string(), False)
            return False

    # Fatigue
    if chk[4] and fat_dict is not None:
        print(fat_press)
        if calc_object[1].get_total_damage(ext_press=fat_press[0], int_press=fat_press[1])*calc_object[1].get_dff() > 1:
            if print_result:
                print('Fatigue',calc_object[0].get_one_line_string(), False)
            return False

    # Slamming
    if chk[5] and slamming_press != 0:
        if calc_object[0].check_all_slamming(slamming_press) is False:
            if print_result:
                print('Slamming',calc_object[0].get_one_line_string(), False)
            return False
    if print_result:
        print('OK Section', calc_object[0].get_one_line_string(), True)
    return x

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

    iter_var = ((item,init_stuc_obj,lat_press,init_filter_weight,side,chk,fat_dict,fat_press,slamming_press)
                for item in iterable_all)

    #res_pre = it.starmap(any_constraints_all, iter_var)
    if processes is None:
        processes = max(cpu_count()-1,1)

    with Pool(processes) as my_process:
        # res_pre = my_process.starmap_async(any_constraints_all, iter_var).get()
        # print('Done calculating')
        res_pre = my_process.starmap(any_constraints_all, iter_var)

    return list(filter(lambda x: x is not False, res_pre))

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
            if type(pre_str) == dict:
                pre_str = (None, None, pre_str['stf_web_height'][0], pre_str['stf_web_thk'][0],
                           pre_str['stf_flange_width'][0], pre_str['stf_flange_thk'][0])
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

def get_initial_weight(obj,lat_press,min_var,max_var,deltas,trials,fat_dict,fat_press):
    '''
    Return a guess of the initial weight used to filter the constraints.
    Only aim is to reduce running time of the algorithm.
    '''
    min_weight = float('inf')
    combs = any_get_all_combs(min_var, max_var, deltas)
    trial_selection = random_product(combs,repeat=trials)
    for x in trial_selection:
        if any_constraints_all(x=x,obj=obj,lat_press=lat_press,init_weight=min_weight,
                               fat_dict=fat_dict,fat_press = fat_press):
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
                               fat_dict = fat_dict, fat_press = fat_press):
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
                               fat_dict = fat_dict, fat_press = fat_press):
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

if __name__ == '__main__':
    import ANYstructure.example_data as ex
    # obj_dict = ex.obj_dict
    # fat_obj = ex.get_fatigue_object()
    # fp = ex.get_fatigue_pressures()
    # fat_press = ((fp['p_ext']['loaded'],fp['p_ext']['ballast'],fp['p_ext']['part']),
    #              (fp['p_int']['loaded'],fp['p_int']['ballast'],fp['p_int']['part']))
    # x0 = [obj_dict['spacing'][0], obj_dict['plate_thk'][0], obj_dict['stf_web_height'][0], obj_dict['stf_web_thk'][0],
    #       obj_dict['stf_flange_width'][0], obj_dict['stf_flange_thk'][0], obj_dict['span'][0], 10]
    # obj = calc.Structure(obj_dict)
    # lat_press = 271.124
    # calc_object = calc.CalcScantlings(obj_dict)
    lower_bounds = np.array([0.6, 0.01, 0.3, 0.01, 0.1, 0.01, 3.5, 10])
    upper_bounds = np.array([0.8, 0.02, 0.5, 0.02, 0.22, 0.03, 3.5, 10])
    deltas = np.array([0.05, 0.005, 0.05, 0.005, 0.05, 0.005])
    #
    # results = run_optmizataion(obj, upper_bounds, lower_bounds, lat_press, deltas, algorithm='anysmart',
    #                            fatigue_obj=fat_obj, fat_press_ext_int=fat_press)
    # print(results[0].get_structure_prop())

    # for swarm_size in [100, 1000, 10000, 100000, 1000000]:
    #     t1 = time.time()
    #
    #     pso_options = (swarm_size, 0.5, 0.5, 0.5, 100, 1e-8, 1e-8)
    #     results = run_optmizataion(obj, upper_bounds, lower_bounds, lat_press, deltas, algorithm='anysmart',
    #                            fatigue_obj=fat_obj, fat_press_ext_int=fat_press, pso_options=pso_options)[0]
    #     print('Swarm size', swarm_size, 'running time', time.time()-t1, results.get_one_line_string())

    results = run_optmizataion(ex.get_geo_opt_object(), lower_bounds, upper_bounds, ex.get_geo_opt_presure(), deltas,
                               is_geometric=True, fatigue_obj=ex.get_geo_opt_fatigue(),
                               fat_press_ext_int=ex.get_geo_opt_fat_press(),
                               slamming_press=ex.get_geo_opt_slamming_none())
