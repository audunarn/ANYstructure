# for this file to work in the Example directory as a developer:
# make sure to have a local environment with the package installed in editable mode
# pip install -e .


# import anystruct.calc_structure_classes as csc
# from anystruct.calc_structure_classes import Material, Stiffener, CurvedPanel, ShellStressAndPressure, CylindricalShell
from anystruct.calc_structure_classes import *
from typing import Dict

if __name__ == '__main__':
    # DNV RP-C201
    my_material: Material = Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
    my_plate: Plate = Plate(spacing=0.700, thickness=0.020, span=4, material=my_material)
    my_stiffener: Stiffener = Stiffener(type='L-bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.0273, material=my_material)
    my_stress: Stress = Stress(sigma_x1=50, sigma_x2=50, sigma_y1=150, sigma_y2=150, tauxy=0.3)
    my_stiffened_panel: StiffenedPanel = StiffenedPanel(plate=my_plate, stiffener=my_stiffener, stiffener_end_support='continuous', girder_length=5)
    # set the calculation properties if different from default
    my_stiffened_panel_calc_props: Stiffened_panel_calc_props = Stiffened_panel_calc_props(plate_kpp=1, stf_kps=1, km1=12, km2=24, km3=12)
    my_buckling_input: BucklingInput = BucklingInput(panel=my_stiffened_panel, pressure=0, pressure_side='both sides', stress=my_stress)
    dnv_bucklng: DNVBuckling = DNVBuckling(buckling_input=my_buckling_input, calculation_domain = '')
    
    result = dnv_bucklng.plated_structures_buckling()
    
    for key, val in result.items():
        print(key, val)
    
    my_calc_scantlings: CalcScantlings = CalcScantlings(buckling_input=my_buckling_input, lat_press=True, category='???', need_recalc=False)
    print(my_calc_scantlings.get_special_provisions_results())

    # DNV RP-C202
    cyl_material: Material = Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
    cyl_stresses: ShellStressAndPressure = ShellStressAndPressure(saSd=-200e6, tQSd=50e6, shSd_add=-60e6)
    curved_panel: CurvedPanel = CurvedPanel(thickness=0.024, radius=1, s=0.68, l=3.3, material=cyl_material)
    long_stiff: Stiffener = Stiffener(type='bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.028, material=cyl_material)
    ring_stiff: Stiffener = Stiffener(type='bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.028, material=cyl_material)
    ring_frame: Stiffener = Stiffener(type='T', web_height=0.500, web_th=0.015, flange_width=0.200, flange_th=0.025, material=cyl_material)
    
    unstiffened_shell: CylindricalShell = CylindricalShell(curved_panel=curved_panel, load=cyl_stresses)
    
    unstiffened_cylinder: CylindricalShell = CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=30)

    long_stiffened_cylinder: CylindricalShell = CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      long_stf=long_stiff,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=100)
    
    ring_stiffened_cylinder: CylindricalShell = CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      ring_stf=ring_stiff,
                                                                      k_factor=1.0,
                                                                      tot_cyl_length=100)

    ring_and_frame_stiffened_cylinder: CylindricalShell = CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      ring_stf=ring_stiff,
                                                                      k_factor=1.0,
                                                                      ring_frame=ring_frame,
                                                                      ring_frame_spacing=10,
                                                                      tot_cyl_length=100)

    orth_stiffened_cylinder: CylindricalShell = CylindricalShell(curved_panel=curved_panel,
                                                                      load=cyl_stresses,
                                                                      long_stf=long_stiff,
                                                                      ring_stf=ring_stiff,
                                                                      k_factor=1.0,
                                                                      ring_frame=ring_frame,
                                                                      ring_frame_spacing=10,
                                                                      tot_cyl_length=100)


    # checked with Excel file
    results: Dict = unstiffened_shell.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)

    # checked with Excel file
    results: Dict = unstiffened_cylinder.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)

    results: Dict = long_stiffened_cylinder.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)

    results: Dict = ring_stiffened_cylinder.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)

    results: Dict = ring_and_frame_stiffened_cylinder.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)

    results: Dict = orth_stiffened_cylinder.get_utilization_factors()
    for key, val in results.items():
        print(key + ':', val)
