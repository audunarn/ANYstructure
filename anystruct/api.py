# temp fix for debugging
import sys
sys.path.insert(0,'/home/frederik/theScriptingEngineer/Python/ANYstructure/')

try:
    from anystruct.calc_structure import *
    #from anystruct.calc_structure_classes import Material, Plate, Stiffener, StiffenedPanel, Stress, Puls, BucklingInput, Stiffened_panel_calc_props, DNVBuckling
    import anystruct.calc_structure_classes as clc
    import anystruct.load_window as load_window
    import anystruct.make_grid_numpy as grid
    import anystruct.grid_window as grid_window
    from anystruct.helper import *
    import anystruct.optimize as op
    import anystruct.optimize_window as opw
    import anystruct.optimize_cylinder as opc
    import anystruct.optimize_multiple_window as opwmult
    import anystruct.optimize_geometry as optgeo
    import anystruct.pl_stf_window as struc
    import anystruct.stresses_window as stress
    import anystruct.fatigue_window as fatigue
    import anystruct.load_factor_window as load_factors
    from anystruct.report_generator import LetterMaker
    import anystruct.sesam_interface as sesam
except ModuleNotFoundError:
    # This is due to pyinstaller issues.
    from ANYstructure.anystruct.calc_structure import *
    # from ANYstructure.calc_structure_classes import Material, Plate, Stiffener, StiffenedPanel, Stress, Puls, BucklingInput, Stiffened_panel_calc_props, DNVBuckling
    import ANYstructure.calc_structure_classes as clc
    from ANYstructure.anystruct.calc_loads import *
    import ANYstructure.anystruct.load_window as load_window
    import ANYstructure.anystruct.make_grid_numpy as grid
    import ANYstructure.anystruct.grid_window as grid_window
    from ANYstructure.anystruct.helper import *
    import ANYstructure.anystruct.optimize as op
    import ANYstructure.anystruct.optimize_window as opw
    import ANYstructure.anystruct.optimize_cylinder as opc
    import ANYstructure.anystruct.optimize_multiple_window as opwmult
    import ANYstructure.anystruct.optimize_geometry as optgeo
    import ANYstructure.anystruct.pl_stf_window as struc
    import ANYstructure.anystruct.stresses_window as stress
    import ANYstructure.anystruct.fatigue_window as fatigue
    import ANYstructure.anystruct.load_factor_window as load_factors
    from ANYstructure.anystruct.report_generator import LetterMaker
    import ANYstructure.anystruct.sesam_interface as sesam


if __name__ == '__main__':
    # # DNV RP-C201
    # my_material: clc.Material = clc.Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
    # my_plate: clc.Plate = clc.Plate(spacing=0.700, thickness=0.020, span=4, material=my_material)
    # my_stiffener: clc.Stiffener = clc.Stiffener(type='L-bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.0273, material=my_material)
    # my_stress: clc.Stress = clc.Stress(sigma_x1=50, sigma_x2=50, sigma_y1=150, sigma_y2=150, tauxy=0.3)
    # my_stiffened_panel: clc.StiffenedPanel = clc.StiffenedPanel(plate=my_plate, stiffener=my_stiffener, stiffener_end_support='continuous', girder_length=5)
    # # set the calculation properties if different from default
    # my_stiffened_panel_calc_props: clc.Stiffened_panel_calc_props = clc.Stiffened_panel_calc_props(plate_kpp=1, stf_kps=1, km1=12, km2=24, km3=12)
    # my_buckling_input: clc.BucklingInput = clc.BucklingInput(panel=my_stiffened_panel, pressure=0, pressure_side='both sides', stress=my_stress)
    # dnv_bucklng: clc.DNVBuckling = clc.DNVBuckling(buckling_input=my_buckling_input, calculation_domain = '')
    
    # result = dnv_bucklng.plated_structures_buckling()
    
    # for key, val in result.items():
    #     print(key, val)
    
    # my_calc_scantlings: clc.CalcScantlings = clc.CalcScantlings(buckling_input=my_buckling_input, lat_press=True, category='???', need_recalc=False)
    # print(my_calc_scantlings.get_special_provisions_results())

    # DNV RP-C202
    cyl_material: clc.Material = clc.Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
    cyl_stresses: clc.ShellStressAndPressure = clc.ShellStressAndPressure(saSd=-200e6, tQSd=50e6, shSd_add=-60e6)
    curved_panel: clc.CurvedPanel = clc.CurvedPanel(thickness=0.024, radius=1, s=0.68, l=3.3, material=cyl_material)
    long_stiff: clc.Stiffener = clc.Stiffener(type='bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.028, material=cyl_material)
    ring_stiff: clc.Stiffener = clc.Stiffener(type='bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.028, material=cyl_material)
    ring_frame: clc.Stiffener = clc.Stiffener(type='T', web_height=0.500, web_th=0.015, flange_width=0.200, flange_th=0.025, material=cyl_material)
    
    unstiffened_shell: clc.CylindricalShell = clc.CylindricalShell(curved_panel=curved_panel, load=cyl_stresses)
    
    unstiffened_cylinder: clc.CylindricalShell = clc.CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=30)

    long_stiffened_cylinder: clc.CylindricalShell = clc.CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      long_stf=long_stiff,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=100)
    
    ring_stiffened_cylinder: clc.CylindricalShell = clc.CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      ring_stf=ring_stiff,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=100)

    ring_and_frame_stiffened_cylinder: clc.CylindricalShell = clc.CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      ring_stf=ring_stiff,
                                                                      k_factor=1.0,
                                                                      ring_frame=ring_frame,
                                                                      ring_frame_spacing=10,
                                                                      tot_cyl_length=100)

    orth_stiffened_cylinder: clc.CylindricalShell = clc.CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      long_stf=long_stiff,
                                                                      ring_stf=ring_stiff,
                                                                      k_factor=1.0,
                                                                      ring_frame=ring_frame,
                                                                      ring_frame_spacing=10,
                                                                      tot_cyl_length=100)


    # # checked with Excel file
    # results = unstiffened_shell.get_utilization_factors()
    # for key, val in results.items():
    #     print(key + ':', val)

    # checked with Excel file
    results = unstiffened_cylinder.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)

    # results = long_stiffened_cylinder.get_utilization_factors()
    # for key, val in results.items():
    #     print(key + ':', val)

    # results = ring_stiffened_cylinder.get_utilization_factors()
    # for key, val in results.items():
    #     print(key + ':', val)

    # results = ring_and_frame_stiffened_cylinder.get_utilization_factors()
    # for key, val in results.items():
    #     print(key + ':', val)

    # results = orth_stiffened_cylinder.get_utilization_factors()
    # for key, val in results.items():
    #     print(key + ':', val)
