try:
    from any_files.calc_structure import *
    from any_files.calc_loads import *
    import any_files.load_window as load_window
    import any_files.make_grid_numpy as grid
    import any_files.grid_window as grid_window
    from any_files.helper import *
    import any_files.optimize as op
    import any_files.optimize_window as opw
    import any_files.optimize_cylinder as opc
    import any_files.optimize_multiple_window as opwmult
    import any_files.optimize_geometry as optgeo
    import any_files.pl_stf_window as struc
    import any_files.stresses_window as stress
    import any_files.fatigue_window as fatigue
    import any_files.load_factor_window as load_factors
    from any_files.report_generator import LetterMaker
    import any_files.sesam_interface as sesam
except ModuleNotFoundError:
    # This is due to pyinstaller issues.
    from ANYstructure.any_files.calc_structure import *
    from ANYstructure.any_files.calc_loads import *
    import ANYstructure.any_files.load_window as load_window
    import ANYstructure.any_files.make_grid_numpy as grid
    import ANYstructure.any_files.grid_window as grid_window
    from ANYstructure.any_files.helper import *
    import ANYstructure.any_files.optimize as op
    import ANYstructure.any_files.optimize_window as opw
    import ANYstructure.any_files.optimize_cylinder as opc
    import ANYstructure.any_files.optimize_multiple_window as opwmult
    import ANYstructure.any_files.optimize_geometry as optgeo
    import ANYstructure.any_files.pl_stf_window as struc
    import ANYstructure.any_files.stresses_window as stress
    import ANYstructure.any_files.fatigue_window as fatigue
    import ANYstructure.any_files.load_factor_window as load_factors
    from ANYstructure.any_files.report_generator import LetterMaker
    import ANYstructure.any_files.sesam_interface as sesam


class FlatStru():
    '''
    API class for all flat plates.
    Domains:
    1. 'Flat plate, unstiffened'
    2. 'Flat plate, stiffened'
    '''
    def __init__(self, calculation_domain: str = None):
        '''

        :param calculation_domain:  "Flat plate, unstiffened", "Flat plate, stiffened",
                                    "Flat plate, stiffened with girder"
        :type calculation_domain: str
        '''
        super().__init__()
        assert calculation_domain in ["Flat plate, unstiffened", "Flat plate, stiffened",
                                      "Flat plate, stiffened with girder"], ('Calculation domain missing!\n '
                                                'Alternatives:'
                                                '\n    "Flat plate, unstiffened"'
                                                '\n    "Flat plate, stiffened"'
                                                '\n    "Flat plate, stiffened with girder"')

        self._Plate = Structure()
        self._Stiffeners = Structure()
        self._Girder = Structure()
        self._calculation_domain = calculation_domain
        self._FlatStructure = AllStructure(Plate=self._Plate,
                           Stiffener=None if calculation_domain == 'Flat plate, unstiffened' else self._Stiffeners,
                           Girder=None if calculation_domain in ['Flat plate, unstiffened', 'Flat plate, stiffened']
                           else self._Girder, calculation_domain=calculation_domain)
    
    @property
    def calculation_domain(self):
        return self._calculation_domain
    @calculation_domain.setter
    def calculation_domain(self, val):
        self._calculation_domain = val

    def set_material(self, mat_yield = 355e6, emodule = 2.1e11, material_factor = 1.15, poisson = 0.3):
        '''
        Set the material properties for all structure.

        :param mat_yield: material yield, given in Pa
        :type mat_yield: float
        :param emodule: elastic module, E
        :type emodule: float
        :param material_factor: material factor, typically 1.15 or 1.1
        :type material_factor: float
        :param poisson: poisson number of matieral
        :type poisson: float
        :return:
        :rtype:
        '''
        self._FlatStructure.mat_yield = mat_yield
        self._FlatStructure.E = emodule
        self._FlatStructure.v = poisson
        self._FlatStructure.mat_factor = material_factor
        self._Plate.mat_factor = material_factor

    def get_buckling_results(self):
        print(self._FlatStructure.plate_buckling())

    def set_plate_geometry(self, spacing: float = 0.7, thickness: float = 0.02, span: float = 4.0):
        '''
        Set the properties of plate. If the plate is stiffened, spacing is between the stiffeners. If the plate
        is not unstiffened, the spacing is the width of the considered plate.

        :param spacing: stiffener spacing
        :type spacing: float
        :param thickness: plate thickness
        :type thickness: float
        :param span: span of plate field
        :type span: float
        :return:
        :rtype:
        '''
        self._FlatStructure.Plate.t = thickness
        self._FlatStructure.Plate.s = spacing
        self._FlatStructure.Plate.span = span
        self._FlatStructure.Plate.girder_lg = 10
    
    def set_loads(self, pressure: float = 0, sigma_x1: float = 0,sigma_x2: float = 0, sigma_y1: float = 0,
                  sigma_y2: float = 0, tau_xy: float = 0):
        '''

        :param pressure: Lateral load / pressure: Psd
        :type pressure: float
        :param sigma_x1: Longitudinal compr.: sx,sd
        :type sigma_x1: float
        :param sigma_x2: Longitudinal compr.: sx2,sd
        :type sigma_x2: float
        :param sigma_y1: Transverse compress.: sy,sd
        :type sigma_y1: float
        :param sigma_y2: Transverse compress.: sy2,sd
        :type sigma_y2: float
        :param tau_xy: Shear Stress: txy
        :type tau_xy: float
        :return:
        :rtype:
        '''
        self._FlatStructure.Plate.tau_xy = tau_xy
        self._FlatStructure.Plate.sigma_x1 = sigma_x1
        self._FlatStructure.Plate.sigma_x2 = sigma_x2
        self._FlatStructure.Plate.sigma_y1 = sigma_y1
        self._FlatStructure.Plate.sigma_y2 = sigma_y2
        self._FlatStructure.Stiffener.tau_xy = tau_xy
        self._FlatStructure.Stiffener.sigma_x1 = sigma_x1
        self._FlatStructure.Stiffener.sigma_x2 = sigma_x2
        self._FlatStructure.Stiffener.sigma_y1 = sigma_y1
        self._FlatStructure.Stiffener.sigma_y2 = sigma_y2
        self._FlatStructure.lat_press = pressure
        
    def set_stiffener(self, hw: float = 0.26*1000, tw: float = 0.012*1000, bf: float = 0.049*1000,
                                   tf: float = 0.027330027*1000, stf_type: str = 'bulb', spacing: float = 0.608*1000):
        '''
        
        :param hw: stiffer web height, mm
        :type hw: float
        :param tw: stiffener web thickness, mm
        :type tw: float
        :param bf: stiffener flange width, mm
        :type bf: float
        :param tf: stiffener flange thickness, mm
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: spacing between stiffeners
        :type spacing: float
        :return: 
        :rtype: 
        '''
        self._FlatStructure.Stiffener.hw = hw
        self._FlatStructure.Stiffener.tw = tw
        self._FlatStructure.Stiffener.b = bf
        self._FlatStructure.Stiffener.tf = tf
        self._FlatStructure.Stiffenerstiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._FlatStructure.Stiffener.s = spacing
        self._FlatStructure.Stiffener.girder_lg = 10
        self._FlatStructure.Stiffener.t = self._FlatStructure.Plate.t


    def set_girder(self, hw: float = 500, tw: float = 15, bf: float = 200,
                                   tf: float = 25, stf_type: str = 'T', spacing: float = 700):
        '''
        
        :param hw: stiffer web height, mm
        :type hw: float
        :param tw: girder web thickness, mm
        :type tw: float
        :param bf: girder flange width, mm
        :type bf: float
        :param tf: girder flange thickness, mm
        :type tf: float
        :param stf_type: girder type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: spacing between girders
        :type spacing: float
        :return: 
        :rtype: 
        '''
        self._FlatStructure.Girder.hw = hw
        self._FlatStructure.Girder.tw = tw
        self._FlatStructure.Girder.b = bf
        self._FlatStructure.Girder.tf = tf
        self._FlatStructure.Girder.girder_lg = 10
        self._FlatStructure.Girder.t = self._FlatStructure.Plate.t

    def set_buckling_parameters(self, calculation_method: str= None, buckling_acceptance: str = None,
                                stiffened_plate_effective_aginst_sigy = True,
                                min_lat_press_adj_span: float = None, buckling_length_factor_stf: float = None,
                                buckling_length_factor_girder: float = None,
                                stf_dist_between_lateral_supp: float = None,
                                girder_dist_between_lateral_supp: float = None,
                                panel_length_Lp: float = None, stiffener_support: str = 'Continuous',
                                girder_support: str = 'Continuous'):
        '''

        :param calculation_method: 'DNV-RP-C201 - prescriptive', 'ML-CL (PULS based)'
        :type calculation_method: str
        :param buckling_acceptance: for ML-CL calculations, either 'buckling' or 'ultimate'
        :type buckling_acceptance: str
        :param stiffened_plate_effective_aginst_sigy:
        :type stiffened_plate_effective_aginst_sigy:
        :param min_lat_press_adj_span: relative pressure applied on adjacent spans
        :type min_lat_press_adj_span: float
        :param buckling_length_factor_stf:  Buckling length factor: , kstiff
        :type buckling_length_factor_stf: float
        :param buckling_length_factor_girder: Buckling length factor:  kstiff
        :type buckling_length_factor_girder: float
        :param stf_dist_between_lateral_supp:  Distance between tripping brackets: lT
        :type stf_dist_between_lateral_supp: float
        :param girder_dist_between_lateral_supp: Dist.betw.lateral supp.: Ltg
        :type girder_dist_between_lateral_supp: float
        :param panel_length_Lp: Panel length (max.no stiff spans*l): Lp
        :type panel_length_Lp: float
        :param stiffener_support: continuous or sniped at ends
        :type stiffener_support: str
        :param girder_support: continuous or sniped at ends
        :type girder_support: str
        :return:
        :rtype:
        '''
        assert calculation_method in ['DNV-RP-C201 - prescriptive', 'ML-CL (PULS based)']
        assert buckling_acceptance in ['buckling', 'ultimate']
        assert stiffener_support in ['Continuous', 'Sniped']
        assert girder_support in ['Continuous', 'Sniped']
        if calculation_method == 'ML-CL (PULS based)':
            raise NotImplementedError('ML-CL (PULS based) not yet implemented')
        sigy_mapper = {True: 'Stf. pl. effective against sigma y', False:'All sigma y to girder'}
        self._FlatStructure._stiffened_plate_effective_aginst_sigy = sigy_mapper[stiffened_plate_effective_aginst_sigy]
        self._FlatStructure.method = buckling_acceptance
        self._FlatStructure._min_lat_press_adj_span = min_lat_press_adj_span
        self._FlatStructure._buckling_length_factor_stf = buckling_length_factor_stf
        self._FlatStructure._buckling_length_factor_girder = buckling_length_factor_girder
        self._FlatStructure._girder_dist_between_lateral_supp = girder_dist_between_lateral_supp
        self._FlatStructure._stf_dist_between_lateral_supp= stf_dist_between_lateral_supp
        self._FlatStructure._panel_length_Lp = panel_length_Lp
        self._FlatStructure._stf_end_support = stiffener_support
        self._FlatStructure._girder_end_support = girder_support




class CylStru():
    ''' API class for all cylinder options.
     Geometries are:
    'Unstiffened shell'
    'Unstiffened panel'
    'Longitudinal Stiffened shell'
    'Longitudinal Stiffened panel'
    'Ring Stiffened shell'
    'Ring Stiffened panel'
    'Orthogonally Stiffened shell'
    'Orthogonally Stiffened panel'
     '''

    geotypes = ['Unstiffened shell', 'Unstiffened panel',
                'Longitudinal Stiffened shell', 'Longitudinal Stiffened panel',
                'Ring Stiffened shell', 'Ring Stiffened panel',
                'Orthogonally Stiffened shell', 'Orthogonally Stiffened panel']
    def __init__(self, geometry_type: str = 'Unstiffened shell'):
        '''
        :param geometry_type:   calculation domain, 'Unstiffened shell', 'Unstiffened panel',
                                'Longitudinal Stiffened shell', 'Longitudinal Stiffened panel', 'Ring Stiffened shell',
                                'Ring Stiffened panel', 'Orthogonally Stiffened shell', 'Orthogonally Stiffened panel'
        :type geometry_type: str
        '''
        super().__init__()
        assert geometry_type in self.geotypes, 'Geometry type must be either of: '+ str(self.geotypes)
        self._load_type = 'Stress' if 'panel' in geometry_type else 'Force'
        self._geometry_type = geometry_type + ' (' + self._load_type + ' input)'
        self._CylinderMain = CylinderAndCurvedPlate()
        self._CylinderMain.geometry = CylinderAndCurvedPlate.geomeries_map_no_input_spec[geometry_type]
        self._CylinderMain.ShellObj = Shell()
        if  geometry_type in ['Unstiffened shell', 'Unstiffened panel']:
            self._CylinderMain.LongStfObj = None
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = None
        elif geometry_type in ['Longitudinal Stiffened shell', 'Longitudinal Stiffened panel']:
            self._CylinderMain.LongStfObj = Structure()
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = None
        elif geometry_type in ['Ring Stiffened shell', 'Ring Stiffened panel']:
            self._CylinderMain.LongStfObj = None
            self._CylinderMain.RingStfObj = Structure()
            self._CylinderMain.RingFrameObj = None
        elif geometry_type in ['Orthogonally Stiffened shell', 'Orthogonally Stiffened panel']:
            self._CylinderMain.LongStfObj = Structure()
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = Structure()

    def set_stresses(self, sasd = 0, smsd = 0, tTsd = 0, tQsd = 0, psd = 0, shsd = 0):
        '''

        :param sasd: Design axial stress, sa,sd
        :type sasd: float
        :param smsd: Design bending stress, sm,sd
        :type smsd: float
        :param tTsd: Design torsional stress, tT,sd
        :type tTsd: float
        :param tQsd: Design shear stress, tQ,sd
        :type tQsd: float
        :param psd: Design lateral pressure, psd
        :type psd: float
        :param shsd: Additional hoop stress, sh,sd
        :type shsd: float
        :return:
        :rtype:
        '''

        self._CylinderMain.sasd = sasd
        self._CylinderMain.smsd = smsd
        self._CylinderMain.tTsd = abs(tTsd)
        self._CylinderMain.tQsd = abs(tQsd)
        self._CylinderMain.psd = psd
        self._CylinderMain.shsd = shsd

    def set_material(self, mat_yield = 355e6, emodule = 2.1e11, material_factor = 1.15, poisson = 0.3):
        '''

        :param mat_yield: material yield, given in Pa
        :type mat_yield: float
        :param emodule: elastic module, E
        :type emodule: float
        :param material_factor: material factor, typically 1.15 or 1.1
        :type material_factor: float
        :param poisson: poisson number of matieral
        :type poisson: float
        :return:
        :rtype:
        '''
        self._CylinderMain.mat_yield = mat_yield
        self._CylinderMain.E = emodule
        self._CylinderMain.v = poisson
        self._CylinderMain.mat_factor = material_factor
    def set_imperfection(self, delta_0 = 0.005):
        '''

        :param delta_0: Initial out of roundness of stiffener
        :type delta_0: float
        :return:
        :rtype:
        '''
        self._CylinderMain.delta0 = delta_0

    def set_fabrication_method(self, stiffener: str =  'Fabricated', girder: str = 'Fabricated'):
        '''

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

        :param is_included: if this is not set, stresses due to end cap pressure for clyinder is set
        :type is_included: bool
        :return:
        :rtype:
        '''
        self._CylinderMain.end_cap_pressure_included = is_included
    def set_uls_or_als(self, kind = 'ULS'):
        '''

        :param kind: set load condition, either 'ULS' or 'ALS'
        :type kind: str
        :return:
        :rtype:
        '''
        assert kind in ['ULS', 'ALS'], 'Must be either of: ' + str(kind)
        self._CylinderMain.uls_or_als = kind
    def set_exclude_ring_stiffener(self, is_excluded: bool = True):
        '''

        :param is_excluded: set no ring stiffeners
        :type is_excluded: bool
        :return:
        :rtype:
        '''
        self._CylinderMain._ring_stiffener_excluded = is_excluded
    def set_exclude_ring_frame(self, is_excluded: bool = True):
        '''

        :param is_excluded: set no ring girders
        :type is_excluded: bool
        :return:
        :rtype:
        '''
        self._CylinderMain._ring_frame_excluded= is_excluded

    def set_length_between_girder(self, val: float = 0):
        '''

        :param val: length/span between girders
        :type val: float
        :return:
        :rtype:
        '''
        self._CylinderMain.length_between_girders = val
    def set_panel_spacing(self, val: float = 0):
        '''
        :param val: spacing between stiffeners
        :type val: float
        :return:
        :rtype:
        '''
        self._CylinderMain.panel_spacing = val

    def set_shell_geometry(self, radius: float = 0, thickness: float = 0,distance_between_rings: float = 0,
                           tot_length_of_shell: float = 0):
        '''

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

        self._CylinderMain.ShellObj.radius = radius
        self._CylinderMain.ShellObj.thk = thickness
        self._CylinderMain.ShellObj.dist_between_rings = distance_between_rings
        if tot_length_of_shell == 0:
            # Setting a default.
            self._CylinderMain.ShellObj.length_of_shell = distance_between_rings * 10
            self._CylinderMain.ShellObj.tot_cyl_length = distance_between_rings * 10
        else:
            self._CylinderMain.ShellObj.tot_cyl_length = tot_length_of_shell

    def set_shell_buckling_parmeters(self, eff_buckling_length_factor: float = 1.0):
        '''
        :param eff_buckling_length_factor: effective length factor, column buckling
        :type eff_buckling_length_factor: float
        :return:
        :rtype:
        '''
        self._CylinderMain.ShellObj.k_factor = eff_buckling_length_factor

    def set_longitudinal_stiffener(self, hw: float = 0.26*1000, tw: float = 0.012*1000, bf: float = 0.049*1000,
                                   tf: float = 0.027330027*1000, stf_type: str = 'bulb', spacing: float = 0.608*1000):
        '''
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

    def set_ring_stiffener(self, hw: float = 0.26*1000, tw: float = 0.012*1000, bf: float = 0.049*1000,
                                   tf: float = 0.027330027*1000, stf_type: str = 'bulb', spacing: float = 0.608*1000):
        '''

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
        ''''''
        return self._CylinderMain.get_utilization_factors()

if __name__ == '__main__':
    pass
    # my_cyl = CylStru(geometry_type='Orthogonally Stiffened shell')
    # my_cyl.set_stresses(sasd=-271354000, tQsd=4788630, shsd=-11228200)
    # my_cyl.set_material()
    # my_cyl.set_imperfection()
    # my_cyl.set_fabrication_method()
    # my_cyl.set_end_cap_pressure_included_in_stress()
    # my_cyl.set_uls_or_als()
    # my_cyl.set_exclude_ring_stiffener()
    # my_cyl.set_length_between_girder(val=3.300)
    # my_cyl.set_panel_spacing(val=0.680)
    # my_cyl.set_shell_geometry(radius=6.500,thickness=0.024, tot_length_of_shell=20.000, distance_between_rings=3.300)
    # my_cyl.get_buckling_results()
    # my_cyl.set_longitudinal_stiffener()
    # my_cyl.set_ring_girder()
    # my_cyl.set_shell_buckling_parmeters()
    # my_cyl.get_buckling_results()
    #
    # my_flat = FlatStru("Flat plate, stiffened with girder")
    # my_flat.set_material()
    # my_flat.set_plate_geometry()
    # my_flat.set_loads(sigma_x1=50, sigma_x2=50, sigma_y1=50, sigma_y2=50, pressure=0.01)
    # my_flat.set_stiffener()
    # my_flat.set_girder()
    # my_flat.set_buckling_parameters(calculation_method='DNV-RP-C201 - prescriptive', buckling_acceptance='buckling',
    #                                 stiffened_plate_effective_aginst_sigy=True)
    # my_flat.get_buckling_results()









