try:
    from anystruct.calc_structure import *
    from anystruct.calc_loads import *
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


class FlatStru():
    '''
    API class for all flat plates.\n
    Domains:\n
    1. 'Flat plate, unstiffened'\n
    2. 'Flat plate, stiffened'\n
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

        self._Plate = CalcScantlings()
        self._Stiffeners = CalcScantlings()
        self._Girder = CalcScantlings()
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
    @property
    def Plate(self):
        return self._Plate
    @Plate.setter
    def Plate(self, val):
        self._Plate = val
    @property
    def Stiffeners(self):
        return self._Stiffeners
    @Stiffeners.setter
    def Stiffeners(self, val):
        self._Stiffeners = val
    @property
    def Girder(self):
        return self._Girder
    @Girder.setter
    def Girder(self, val):
        self._Girder = val

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
        self._FlatStructure.mat_yield = mat_yield*1e6
        self._FlatStructure.E = emodule*1e6
        self._FlatStructure.v = poisson
        self._FlatStructure.mat_factor = material_factor

        for sub_cls in [self.Plate, self.Stiffeners, self.Girder]:
            if sub_cls is not None:
                sub_cls.mat_yield = mat_yield * 1e6
                sub_cls.E = emodule * 1e6
                sub_cls.v = poisson
                sub_cls.mat_factor = material_factor

    def set_fixation_parameters(self, kpp: float = 1, kps: float = 1,
                                km1: float = 12, km2: float = 24, km3: float = 12):
        '''

        :param kpp: fixation parameter for plate, 1.0 for clamped edges, 0.5 for simply supported edges
        :type kpp: float
        :param kps: fixation parameter for stiffeners, 1.0 if at least one end is clamped, 0.9 if both ends are simply supported
        :type kps:
        :param km1: Bending moment and shear force factors, see DNV standards or ANYstructure GUI
        :type km1: float
        :param km2: Bending moment and shear force factors, see DNV standards or ANYstructure GUI
        :type km2: float
        :param km3: Bending moment and shear force factors, see DNV standards or ANYstructure GUI
        :type km3: float
        :return:
        :rtype:
        '''
        for sub_cls in [self.Plate, self.Stiffeners, self.Girder]:
            if sub_cls is not None:
                sub_cls._plate_kpp = kpp
                sub_cls._stf_kps = kps
                sub_cls._km1 = km1
                sub_cls._km2 = km2
                sub_cls._km3 = km3




    def get_buckling_results(self):
        '''
        Return a dictionary of all buckling results. UF - Utilization Factor.\n
        Plate : {'Plate buckling': UF}\n
        Stiffener: {'Overpressure plate side': UF, 'Overpressure stiffener side': UF,\n
                    'Resistance between stiffeners': UF, 'Shear capacity': UF}\n
        Girder: {'Overpressure plate side': UF, 'Overpressure girder side': UF, 'Shear capacity': UF}\n
        Local buckling {'Stiffener': [UF web, UF flange], 'Girder': [UF web, UF flange]}\n
        :return: Results for plate, stiffener, girder and a separate local check for stiffeners/girders\n
        :rtype: dict
        '''
        return  self._FlatStructure.plate_buckling()

    def set_plate_geometry(self, spacing: float = 700, thickness: float = 20, span: float = 4000):

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
        self._FlatStructure.Plate.spacing = spacing
        self._FlatStructure.Plate.span = span/1000
        self._FlatStructure.Plate.girder_lg = 10 # placeholder value

    
    def set_stresses(self, pressure: float = 0, sigma_x1: float = 0,sigma_x2: float = 0, sigma_y1: float = 0,
                     sigma_y2: float = 0, tau_xy: float = 0):
        '''
        Set loads applied on the plate sides.\n
        x1 and y1 is on one side of the plate\n
        x2 and y2 is the other side\n
        tau_xy act uniformly on the plate field\n
        Stresses are in MPA.\n
        Use POSITIVE numbers for compression pressure, stresses and forces\n

        :param pressure: Lateral load / pressure: Psd [MPa]
        :type pressure: float
        :param sigma_x1: Longitudinal compr.: sx,sd [MPa]
        :type sigma_x1: float
        :param sigma_x2: Longitudinal compr.: sx2,sd [MPa]
        :type sigma_x2: float
        :param sigma_y1: Transverse compress.: sy,sd [MPa]
        :type sigma_y1: float
        :param sigma_y2: Transverse compress.: sy2,sd [MPa]
        :type sigma_y2: float
        :param tau_xy: Shear Stress: txy [MPa]
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

    def set_stiffener(self, hw: float = 260, tw: float = 12, bf: float = 49,
                      tf: float = 27.3, stf_type: str = 'bulb', spacing: float = 608):
        '''
        Sets the stiffener properties.

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
        self._FlatStructure.Stiffener.stiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._FlatStructure.Stiffener.spacing = spacing
        self._FlatStructure.Stiffener.girder_lg = 10
        self._FlatStructure.Stiffener.t = self._FlatStructure.Plate.t
        self._FlatStructure.Stiffener.span = self._FlatStructure.Plate.span
        self._FlatStructure.Stiffener.mat_yield = self._FlatStructure.Plate.mat_yield


    def set_girder(self, hw: float = 500, tw: float = 15, bf: float = 200,
                                   tf: float = 25, stf_type: str = 'T', spacing: float = 700):
        '''
        Sets the girder properties.

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
        Various buckling realted parameters are set here. For details, see\n
        DNV-RP-C201 Buckling strength of plated structures.\n

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

    def get_special_provisions_results(self):
        '''
        Special provisions for plating and stiffeners in steel structures.\n
        Return a dictionary:\n

        'Plate thickness' : The thickness of plates shall not be less than this check.\n
        'Stiffener section modulus' : The section modulus for longitudinals, beams, frames and other stiffeners\n
                                      subjected to lateral pressure shall not be less than this check.\n
        'Stiffener shear area' : The shear area of the plate/stiffener shall not be less than this ckeck.\n
        :return: minium dimensions and acutal dimensions for the current structure in mm/mm^2/mm^3
        :rtype: dict
        '''
        min_pl_thk = self.Plate.get_dnv_min_thickness(design_pressure_kpa=self._FlatStructure.lat_press * 1000)
        min_sec_mod = self.Stiffeners.get_dnv_min_section_modulus(
            design_pressure_kpa=self._FlatStructure.lat_press * 1000) * 1000**3
        min_area = self.Stiffeners.get_minimum_shear_area(pressure=self._FlatStructure.lat_press * 1000) * 1000**2

        this_pl_thk = self.Plate.t
        this_secmod = self.Stiffeners.get_section_modulus()
        this_area = self.Stiffeners.get_shear_area()* 1000**2
        return {'Plate thickness':{'minimum': min_pl_thk, 'actual': this_pl_thk},
                'Stiffener section modulus': {'minimum': min_sec_mod, 'actual': min(this_secmod)* 1000**3},
                'Stiffener shear area': {'minimum': min_area, 'actual': this_area}}



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

    # my_cyl = CylStru(calculation_domain='Orthogonally Stiffened shell')
    # my_cyl.set_stresses(sasd=-200, tQsd=5, shsd=-60)
    # my_cyl.set_material(mat_yield=355, emodule=210000, material_factor=1.15, poisson=0.3)
    # my_cyl.set_imperfection()
    # my_cyl.set_fabrication_method()
    # my_cyl.set_end_cap_pressure_included_in_stress()
    # my_cyl.set_uls_or_als()
    # my_cyl.set_exclude_ring_stiffener()
    # my_cyl.set_length_between_girder(val=3300)
    # my_cyl.set_panel_spacing(val=680)
    # my_cyl.set_shell_geometry(radius=6500,thickness=24, tot_length_of_shell=20000, distance_between_rings=3300)
    # my_cyl.set_longitudinal_stiffener(hw=260, tw=23, bf=49, tf=28, spacing=680)
    # my_cyl.set_ring_girder(hw=500, tw=15, bf=200, tf=25, stf_type='T', spacing=700)
    # my_cyl.set_shell_buckling_parmeters()
    # for key, val in my_cyl.get_buckling_results().items():
    #     print(key, val)
    #print(my_cyl.get_buckling_results())
    # #
    my_flat = FlatStru("Flat plate, stiffened with girder")
    my_flat.set_material(mat_yield=355, emodule=210000, material_factor=1.15, poisson=0.3)
    my_flat.set_plate_geometry()
    my_flat.set_stresses(sigma_x1=50, sigma_x2=50, sigma_y1=150, sigma_y2=150, pressure=0.3)
    my_flat.set_stiffener()
    my_flat.set_girder()
    my_flat.set_fixation_parameters()
    my_flat.set_buckling_parameters(calculation_method='DNV-RP-C201 - prescriptive', buckling_acceptance='buckling',
                                    stiffened_plate_effective_aginst_sigy=True)
    for key, val in my_flat.get_buckling_results().items():
        print(key, val)

    print(my_flat.get_special_provisions_results())









