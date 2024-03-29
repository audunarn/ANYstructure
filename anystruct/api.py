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




class CylStru():
    ''' API class for all cylinder options.\n
     Calculation domains are:\n
    1.  'Unstiffened shell'\n
    2.  'Unstiffened panel'\n
    3.  'Longitudinal Stiffened shell'\n
    4.  'Longitudinal Stiffened panel'\n
    5.  'Ring Stiffened shell'\n
    6.  'Ring Stiffened panel'\n
    7.  'Orthogonally Stiffened shell'\n
    8.  'Orthogonally Stiffened panel'\n
     '''

    geotypes = ['Unstiffened shell', 'Unstiffened panel',
                'Longitudinal Stiffened shell', 'Longitudinal Stiffened panel',
                'Ring Stiffened shell', 'Ring Stiffened panel',
                'Orthogonally Stiffened shell', 'Orthogonally Stiffened panel']
    def __init__(self, calculation_domain: str = 'Unstiffened shell'):
        '''
        :param calculation_domain:   calculation domain, 'Unstiffened shell', 'Unstiffened panel',
                                'Longitudinal Stiffened shell', 'Longitudinal Stiffened panel', 'Ring Stiffened shell',
                                'Ring Stiffened panel', 'Orthogonally Stiffened shell', 'Orthogonally Stiffened panel'
        :type calculation_domain: str
        '''
        super().__init__()
        assert calculation_domain in self.geotypes, 'Geometry type must be either of: '+ str(self.geotypes)
        self._load_type = 'Stress' if 'panel' in calculation_domain else 'Force'
        self._calculation_domain = calculation_domain + ' (' + self._load_type + ' input)'
        self._CylinderMain = CylinderAndCurvedPlate()
        self._CylinderMain.geometry = CylinderAndCurvedPlate.geomeries_map_no_input_spec[calculation_domain]
        self._CylinderMain.ShellObj = Shell()
        if  calculation_domain in ['Unstiffened shell', 'Unstiffened panel']:
            self._CylinderMain.LongStfObj = None
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = None
        elif calculation_domain in ['Longitudinal Stiffened shell', 'Longitudinal Stiffened panel']:
            self._CylinderMain.LongStfObj = Structure()
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = None
        elif calculation_domain in ['Ring Stiffened shell', 'Ring Stiffened panel']:
            self._CylinderMain.LongStfObj = None
            self._CylinderMain.RingStfObj = Structure()
            self._CylinderMain.RingFrameObj = None
        elif calculation_domain in ['Orthogonally Stiffened shell', 'Orthogonally Stiffened panel']:
            self._CylinderMain.LongStfObj = Structure()
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = Structure()

    def set_stresses(self, sasd = 0, smsd = 0, tTsd = 0, tQsd = 0, psd = 0, shsd = 0):
        '''
        Cylinder stresses.
        Use negative numbers for compression pressure, stresses and forces.

        :param sasd: Design axial stress, sa,sd [MPa]
        :type sasd: float
        :param smsd: Design bending stress, sm,sd [MPa]
        :type smsd: float
        :param tTsd: Design torsional stress, tT,sd [MPa]
        :type tTsd: float
        :param tQsd: Design shear stress, tQ,sd [MPa]
        :type tQsd: float
        :param psd: Design lateral pressure, psd [MPa]
        :type psd: float
        :param shsd: Additional hoop stress, sh,sd [MPa]
        :type shsd: float
        :return:
        :rtype:
        '''

        self._CylinderMain.sasd = sasd*1e6
        self._CylinderMain.smsd = smsd*1e6
        self._CylinderMain.tTsd = abs(tTsd*1e6)
        self._CylinderMain.tQsd = abs(tQsd*1e6)
        self._CylinderMain.psd = psd*1e6
        self._CylinderMain.shsd = shsd*1e6

    def set_forces(self, Nsd: float = 0, Msd: float = 0, Tsd: float = 0, Qsd: float = 0, psd: float = 0):
        '''
        Forces applied to cylinder.
        Use negative numbers for compression pressure, stresses and forces.

        :param Nsd: Design Axial force, Nsd [kN]
        :param Msd: Design bending mom., Msd [kNm]
        :param Tsd: Design torsional mom., Tsd [kNm]
        :param Qsd: Design shear force, Qsd [kN]
        :param psd: Design lateral pressure, psd [N/mm2]

        :return:
        '''
        geomeries = {11: 'Flat plate, stiffened', 10: 'Flat plate, unstiffened',
                     12: 'Flat plate, stiffened with girder',
                     1: 'Unstiffened shell (Force input)', 2: 'Unstiffened panel (Stress input)',
                     3: 'Longitudinal Stiffened shell  (Force input)', 4: 'Longitudinal Stiffened panel (Stress input)',
                     5: 'Ring Stiffened shell (Force input)', 6: 'Ring Stiffened panel (Stress input)',
                     7: 'Orthogonally Stiffened shell (Force input)', 8: 'Orthogonally Stiffened panel (Stress input)'}
        geomeries_map = dict()
        for key, value in geomeries.items():
            geomeries_map[value] = key
        geometry = geomeries_map[self._calculation_domain]
        forces = [Nsd, Msd, Tsd, Qsd]
        sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
            stresses=None, forces=forces, geometry=geometry, shell_t=self._CylinderMain.ShellObj.thk,
            shell_radius=self._CylinderMain.ShellObj.radius,
            shell_spacing= None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.s,
            hw=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.hw,
            tw=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.tw,
            b=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.b,
            tf=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.tf,
            CylinderAndCurvedPlate=CylinderAndCurvedPlate)

        self._CylinderMain.sasd = sasd
        self._CylinderMain.smsd = smsd
        self._CylinderMain.tTsd = abs(tTsd)
        self._CylinderMain.tQsd = abs(tQsd)
        self._CylinderMain.psd = psd
        self._CylinderMain.shsd = shsd


    def set_material(self, mat_yield = 355, emodule = 210000, material_factor = 1.15, poisson = 0.3):
        '''
        Set the material properties for all structure.

        :param mat_yield: material yield, fy,  given in MPa
        :type mat_yield: float
        :param emodule: elastic module, E, given in MPa
        :type emodule: float
        :param material_factor: material factor, typically 1.15 or 1.1
        :type material_factor: float
        :param poisson: poisson number of matieral
        :type poisson: float
        :return:
        :rtype:
        '''
        self._CylinderMain.mat_yield = mat_yield*1e6
        self._CylinderMain.E = emodule*1e6
        self._CylinderMain.v = poisson
        self._CylinderMain.mat_factor = material_factor
    def set_imperfection(self, delta_0 = 0.005):
        '''
        Initial out of roundness of stiffener: delta_0 * r
        Typical value is set as default.

        :param delta_0: Initial out of roundness of stiffener
        :type delta_0: float
        :return:
        :rtype:
        '''
        self._CylinderMain.delta0 = delta_0

    def set_fabrication_method(self, stiffener: str =  'Fabricated', girder: str = 'Fabricated'):
        '''
        Fabrication method for stiffener and girder. Either 'Fabricated' or 'Cold formed'

        :param stiffener: set fabrication method of stiffeners, either 'Fabricated' or 'Cold formed'
        :type stiffener: str
        :param girder: set fabrication method of girder, either 'Fabricated' or 'Cold formed'
        :type girder: str
        :return:
        :rtype:
        '''
        options = ['Fabricated', 'Cold formed']
        assert stiffener in options, 'Method must be either of: ' + str(options)
        self._CylinderMain.fab_method_ring_stf = stiffener
        self._CylinderMain.fab_method_ring_girder = girder
    def set_end_cap_pressure_included_in_stress(self, is_included: bool = True):
        '''
        Cylinder may or may not have and end cap. If there is an end cap, and the stresses from pressure on this
        is not included, ste this values to True.

        :param is_included: if this is not set, stresses due to end cap pressure for clyinder is set
        :type is_included: bool
        :return:
        :rtype:
        '''
        self._CylinderMain.end_cap_pressure_included = is_included
    def set_uls_or_als(self, kind = 'ULS'):
        '''
        This is used to calculate th resulting material factor.
        ALS is Accidental Limit State
        ULS is Ultimate Limit State

        :param kind: set load condition, either 'ULS' or 'ALS'
        :type kind: str
        :return:
        :rtype:
        '''
        assert kind in ['ULS', 'ALS'], 'Must be either of: ' + str(kind)
        self._CylinderMain.uls_or_als = kind
    def set_exclude_ring_stiffener(self, is_excluded: bool = True):
        '''
        If for example orthogonally stiffened cylinder is selected and there are no ring stiffeners, set this to True.
        In this case only ring girders are included.

        :param is_excluded: set no ring stiffeners
        :type is_excluded: bool
        :return:
        :rtype:
        '''
        self._CylinderMain._ring_stiffener_excluded = is_excluded
    def set_exclude_ring_frame(self, is_excluded: bool = True):
        '''
        If for example orthogonally stiffened cylinder is selected and there are no ring girder, set this to True.
        The resulting structure will then be only longitudinal and ring stiffeners.

        :param is_excluded: set no ring girders
        :type is_excluded: bool
        :return:
        :rtype:
        '''
        self._CylinderMain._ring_frame_excluded= is_excluded

    def set_length_between_girder(self, val: float = 0):
        '''
        Distance between the girders along the cylinder.

        :param val: length/span between girders
        :type val: float
        :return:
        :rtype:
        '''
        self._CylinderMain.length_between_girders = val
    def set_panel_spacing(self, val: float = 0):
        '''
        In case a curved panel is selected, not a complete cylinder, this value sets the width of the panel.

        :param val: spacing between stiffeners
        :type val: float
        :return:
        :rtype:
        '''
        self._CylinderMain.panel_spacing = val/1000

    def set_shell_geometry(self, radius: float = 0, thickness: float = 0,distance_between_rings: float = 0,
                           tot_length_of_shell: float = 0):
        '''
        Sets the baic parameters for the cylinder.

        :param radius: radius of cylinder
        :type radius: float
        :param thickness: thickness of cylinder
        :type thickness: float
        :param distance_between_rings: distance between girders
        :type distance_between_rings: float
        :param tot_length_of_shell: total length of the cylinder
        :type tot_length_of_shell: float
        :return:
        :rtype:
        '''

        self._CylinderMain.ShellObj.radius = radius/1000
        self._CylinderMain.ShellObj.thk = thickness/1000
        self._CylinderMain.ShellObj.dist_between_rings = distance_between_rings/1000
        if tot_length_of_shell == 0:
            # Setting a default.
            self._CylinderMain.ShellObj.length_of_shell = distance_between_rings * 10/1000
            self._CylinderMain.ShellObj.tot_cyl_length = distance_between_rings * 10/1000
        else:
            self._CylinderMain.ShellObj.tot_cyl_length = tot_length_of_shell/1000

    def set_shell_buckling_parmeters(self, eff_buckling_length_factor: float = 1.0):
        '''
        Sets the buckling length paramenter of the cylinder. Used for global column buckling calculations.

        :param eff_buckling_length_factor: effective length factor, column buckling
        :type eff_buckling_length_factor: float
        :return:
        :rtype:
        '''
        self._CylinderMain.ShellObj.k_factor = eff_buckling_length_factor

    def set_longitudinal_stiffener(self, hw: float = 260, tw: float = 12, bf: float = 49,
                                   tf: float = 28, stf_type: str = 'bulb', spacing: float = 680):
        '''
        Sets the longitudinal stiffener dimensions. May be excluded.

        :param hw: web height
        :type hw: float
        :param tw: web thickness
        :type tw: float
        :param bf: flange width
        :type bf: float
        :param tf: flange thickness
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: distance between stiffeners
        :type spacing: float

        '''
        self._CylinderMain.LongStfObj.hw = hw
        self._CylinderMain.LongStfObj.tw = tw
        self._CylinderMain.LongStfObj.b = bf
        self._CylinderMain.LongStfObj.tf = tf
        self._CylinderMain.LongStfObj.stiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._CylinderMain.LongStfObj.s = spacing
        self._CylinderMain.LongStfObj.t = self._CylinderMain.ShellObj.thk

    def set_ring_stiffener(self, hw: float = 260, tw: float = 12, bf: float = 49,
                                   tf: float = 28, stf_type: str = 'bulb', spacing: float = 680):
        '''
        Sets the ring stiffener dimensions. May be excluded.

        :param hw: web height
        :type hw: float
        :param tw: web thickness
        :type tw: float
        :param bf: flange width
        :type bf: float
        :param tf: flange thickness
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: distance between stiffeners
        :type spacing: float
        :return:
        :rtype:
        '''


        self._CylinderMain.RingStfObj.hw = hw
        self._CylinderMain.RingStfObj.tw = tw
        self._CylinderMain.RingStfObj.b = bf
        self._CylinderMain.RingStfObj.tf = tf
        self._CylinderMain.RingStfObj.stiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._CylinderMain.RingStfObj.s = spacing
        self._CylinderMain.RingStfObj.t = self._CylinderMain.ShellObj.thk

    def set_ring_girder(self, hw: float = 500, tw: float = 15, bf: float = 200,
                                   tf: float = 25, stf_type: str = 'T', spacing: float = 700):
        '''
        Sets the ring girder dimensions. May be excluded.

        :param hw: web height
        :type hw: float
        :param tw: web thickness
        :type tw: float
        :param bf: flange width
        :type bf: float
        :param tf: flange thickness
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: distance between stiffeners
        :type spacing: float
        :return:
        :rtype:
        '''

        self._CylinderMain.RingFrameObj.hw = hw
        self._CylinderMain.RingFrameObj.tw = tw
        self._CylinderMain.RingFrameObj.b = bf
        self._CylinderMain.RingFrameObj.tf = tf
        self._CylinderMain.RingFrameObj.stiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._CylinderMain.RingFrameObj.s = spacing
        self._CylinderMain.RingFrameObj.t = self._CylinderMain.ShellObj.thk


    def get_buckling_results(self):
        '''
        Return a dict including all buckling results
        :return:
        :rtype:
        '''
        return self._CylinderMain.get_utilization_factors()

if __name__ == '__main__':

    my_cyl = CylStru(calculation_domain='Orthogonally Stiffened shell')
    my_cyl.set_stresses(sasd=-200, tQsd=5, shsd=-60)
    my_cyl.set_material(mat_yield=355, emodule=210000, material_factor=1.15, poisson=0.3)
    my_cyl.set_imperfection()
    my_cyl.set_fabrication_method()
    my_cyl.set_end_cap_pressure_included_in_stress()
    my_cyl.set_uls_or_als()
    my_cyl.set_exclude_ring_stiffener()
    my_cyl.set_length_between_girder(val=3300)
    my_cyl.set_panel_spacing(val=680)
    my_cyl.set_shell_geometry(radius=6500,thickness=24, tot_length_of_shell=20000, distance_between_rings=3300)
    my_cyl.set_longitudinal_stiffener(hw=260, tw=23, bf=49, tf=28, spacing=680)
    my_cyl.set_ring_girder(hw=500, tw=15, bf=200, tf=25, stf_type='T', spacing=700)
    my_cyl.set_shell_buckling_parmeters()
    for key, val in my_cyl.get_buckling_results().items():
        print(key, val)
    print(my_cyl.get_buckling_results())
    # #

    my_material: clc.Material = clc.Material(young=206800e6, poisson=0.3, strength=355e6, mat_factor=1.15)
    my_plate: clc.Plate = clc.Plate(spacing=0.700, thickness=0.020, span=4, material=my_material)
    my_stiffener: clc.Stiffener = clc.Stiffener(type='L-bulb', web_height=0.260, web_th=0.012, flange_width=0.049, flange_th=0.0273, material=my_material)
    my_stress: clc.Stress = clc.Stress(sigma_x1=50, sigma_x2=50, sigma_y1=150, sigma_y2=150, tauxy=0.3)
    my_stiffened_panel: clc.StiffenedPanel = clc.StiffenedPanel(plate=my_plate, stiffener=my_stiffener, stiffener_end_support='Continuous', girder_length=5)
    # set the calculation properties if different from default
    my_stiffened_panel_calc_props: clc.Stiffened_panel_calc_props = clc.Stiffened_panel_calc_props(plate_kpp=1, stf_kps=1, km1=12, km2=24, km3=12)
    my_buckling_input: clc.BucklingInput = clc.BucklingInput(panel=my_stiffened_panel, pressure=0, pressure_side='both sides', stress=my_stress)
    dnv_bucklng: clc.DNVBuckling = clc.DNVBuckling(buckling_input=my_buckling_input, calculation_domain = '')
    
    result = dnv_bucklng.plated_structures_buckling()
    
    for key, val in result.items():
        print(key, val)
    
    my_calc_scantlings: clc.CalcScantlings = clc.CalcScantlings(buckling_input=my_buckling_input, lat_press=True, category='???', need_recalc=False)
    print(my_calc_scantlings.get_special_provisions_results())








