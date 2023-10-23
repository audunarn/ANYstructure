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
    '''
    def __init__(self):
        super().__init__()
        pass

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

    shell_main_dict = {'sasd': [-10e6, 'Pa'],
                     'smsd': [-10e6, 'Pa'],
                     'tTsd': [40* 1e6, 'Pa'],
                     'tQsd': [40* 1e6, 'Pa'],
                     'psd': [-0.1e6, 'Pa'],
                     'shsd': [0, 'Pa'],
                     'geometry': [3, '-'],
                     'material factor': [1.15, ''],
                     'delta0': [0.005, ''],
                     'fab method ring stf': [1, ''],
                     'fab method ring girder': [1, ''],
                     'E-module': [2.1e11, 'Pa'],
                     'poisson': [0.3, '-'],
                     'mat_yield': [355 * 1e6, 'Pa'],
                   'length between girders' : [None, 'm'],
                   'panel spacing, s' : [2, 'm'],
                   'ring stf excluded' : [False, ''],
                   'ring frame excluded' : [True, ''],
                   'end cap pressure': ['not included in axial stresses', ''],
                   'ULS or ALS': ['ULS', '']}

     '''

    geotypes = ['Unstiffened shell', 'Unstiffened panel',
                'Longitudinal Stiffened shell', 'Longitudinal Stiffened panel',
                'Ring Stiffened shell', 'Ring Stiffened panel',
                'Orthogonally Stiffened shell', 'Orthogonally Stiffened panel']
    def __init__(self, geometry_type: str = 'Unstiffened shell'):
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
                self._sasd= None
                self._smsd= None
                self._tTsd= None
                self._tQsd= None
                self._psd = None
                self._shsd= None
        '''
        self._CylinderMain.sasd = sasd
        self._CylinderMain.smsd = smsd
        self._CylinderMain.tTsd = abs(tTsd)
        self._CylinderMain.tQsd = abs(tQsd)
        self._CylinderMain.psd = psd
        self._CylinderMain.shsd = shsd

    def set_material(self, mat_yield = 355e6, emodule = 2.1e11, material_factor = 1.15, poisson = 0.3):
        self._CylinderMain.mat_yield = mat_yield
        self._CylinderMain.E = emodule
        self._CylinderMain.v = poisson
        self._CylinderMain.mat_factor = material_factor
    def set_imperfection(self, delta_0 = 0.005):
        self._CylinderMain.delta0 = delta_0
    def set_fabrication_method(self, stiffener: str =  'Fabricated', girder: str = 'Fabricated'):
        options = ['Fabricated', 'Cold formed']
        assert stiffener in options, 'Method must be either of: ' + str(options)
        self._CylinderMain.fab_method_ring_stf = stiffener
        self._CylinderMain.fab_method_ring_girder = girder
    def set_end_cap_pressure_included_in_stress(self, is_included: bool = True):
        self._CylinderMain.end_cap_pressure_included = is_included
    def set_uls_or_als(self, kind = 'ULS'):
        assert kind in ['ULS', 'ALS'], 'Must be either of: ' + str(kind)
        self._CylinderMain.uls_or_als = kind
    def set_exclude_ring_stiffener(self, is_excluded: bool = True):
        self._CylinderMain._ring_stiffener_excluded = is_excluded
    def set_exclude_ring_frame(self, is_excluded: bool = True):
        self._CylinderMain._ring_frame_excluded= is_excluded
    def set_length_between_girder(self, val: float = 0):
        self._CylinderMain.length_between_girders = val
    def set_panel_spacing(self, val: float = 0):
        self._CylinderMain.panel_spacing = val

    def set_shell_geometry(self, radius: float = 0, thickness: float = 0,distance_between_rings: float = 0,
                           tot_length_of_shell: float = 0):

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
        self._CylinderMain.ShellObj.k_factor = eff_buckling_length_factor

    def set_longitudinal_stiffener(self, hw: float = 0.26*1000, tw: float = 0.012*1000, bf: float = 0.049*1000,
                                   tf: float = 0.027330027*1000, stf_type: str = 'bulb', spacing:float = 0.608*1000):

        self._CylinderMain.LongStfObj.hw = hw
        self._CylinderMain.LongStfObj.tw = tw
        self._CylinderMain.LongStfObj.b = bf
        self._CylinderMain.LongStfObj.tf = tf
        self._CylinderMain.LongStfObj.stiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._CylinderMain.LongStfObj.s = spacing
        self._CylinderMain.LongStfObj.t = self._CylinderMain.ShellObj.thk

    def set_ring_girder(self, hw: float = 500, tw: float = 15, bf: float = 200,
                                   tf: float = 25, stf_type: str = 'T', spacing:float = 700):

        self._CylinderMain.RingFrameObj.hw = hw
        self._CylinderMain.RingFrameObj.tw = tw
        self._CylinderMain.RingFrameObj.b = bf
        self._CylinderMain.RingFrameObj.tf = tf
        self._CylinderMain.RingFrameObj.stiffener_type = 'L-bulb' if stf_type in ['hp HP HP-bulb bulb'] else stf_type
        self._CylinderMain.RingFrameObj.s = spacing
        self._CylinderMain.RingFrameObj.t = self._CylinderMain.ShellObj.thk

    def get_buckling_results(self):
        return self._CylinderMain.get_utilization_factors()




if __name__ == '__main__':
    my_cyl = CylStru(geometry_type='Orthogonally Stiffened shell')
    my_cyl.set_stresses(sasd=-200e6)
    my_cyl.set_material()
    my_cyl.set_imperfection()
    my_cyl.set_fabrication_method()
    my_cyl.set_end_cap_pressure_included_in_stress()
    my_cyl.set_uls_or_als()
    my_cyl.set_exclude_ring_stiffener()
    my_cyl.set_length_between_girder(val=3300)
    my_cyl.set_panel_spacing(val=608)
    my_cyl.set_shell_geometry(radius=6500,thickness=20, tot_length_of_shell=20000, distance_between_rings=3300)
    my_cyl.set_longitudinal_stiffener()
    my_cyl.set_ring_girder()
    my_cyl.set_shell_buckling_parmeters()

    print(my_cyl.get_buckling_results())






