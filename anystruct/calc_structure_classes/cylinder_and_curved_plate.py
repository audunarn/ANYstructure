import math
import logging
from typing import Optional, List, Dict, Union, Any
from enum import IntEnum

from pydantic import BaseModel, model_validator, field_validator, PrivateAttr, Field
import numpy as np

from .curved_panel import CurvedPanel
from .stiffener import Stiffener


# Create a custom logger
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# so not to create another handler if it has already been defined in another module
# doesn't seem to be working for file, but there the problem of multiple logs does not occur
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class ShellStressAndPressure(BaseModel):
    '''
    Tension positive, compression negative
    '''
    saSd: float = 0
    smSd: float = 0
    tTSd: float = 0
    tQSd: float = 0
    pSd: float = 0
    # what is this additional hoop stress?
    # Should pSd be removed as it is a force? Then shSd is simply the hoop stress.
    shSd_add: float = 0 # additional hoop stress

    # this is a pydantic feature that allows us to run some code after the initialization of the class
    def __post_init__(self):
        # tQsd is the shear stress and always positive
        self.tQSd = abs(self.tQSd)


    # chech that shear is positive
    # should always pass since we are taking the abs on ititialization
    @field_validator('tQSd')
    def check_shear(cls, value):
        if value < 0:
            raise ValueError('Shear stress must be positive')
        return value
    
    # to add the function to calculate stresses from corresponding forces
    # this is the code from the api:
    # def from_forces(self, NSd: float = 0, MSd: float = 0, TSd: float = 0, QSd: float = 0, pSd: float = 0):
    #     '''
    #     Forces applied to cylinder.
    #     Use negative numbers for compression pressure, stresses and forces.

    #     :param Nsd: Design Axial force, Nsd [kN]
    #     :param Msd: Design bending mom., Msd [kNm]
    #     :param Tsd: Design torsional mom., Tsd [kNm]
    #     :param Qsd: Design shear force, Qsd [kN]
    #     :param psd: Design lateral pressure, psd [N/mm2]

    #     :return:
    #     '''
    #     geomeries = {11: 'Flat plate, stiffened', 10: 'Flat plate, unstiffened',
    #                  12: 'Flat plate, stiffened with girder',
    #                  1: 'Unstiffened shell (Force input)', 2: 'Unstiffened panel (Stress input)',
    #                  3: 'Longitudinal Stiffened shell  (Force input)', 4: 'Longitudinal Stiffened panel (Stress input)',
    #                  5: 'Ring Stiffened shell (Force input)', 6: 'Ring Stiffened panel (Stress input)',
    #                  7: 'Orthogonally Stiffened shell (Force input)', 8: 'Orthogonally Stiffened panel (Stress input)'}
    #     geomeries_map = dict()
    #     for key, value in geomeries.items():
    #         geomeries_map[value] = key
    #     geometry = geomeries_map[self._calculation_domain]
    #     forces = [NSd, MSd, TSd, QSd]
    #     sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
    #         stresses=None, forces=forces, geometry=geometry, shell_t=self._CylinderMain.ShellObj.thk,
    #         shell_radius=self._CylinderMain.ShellObj.radius,
    #         shell_spacing= None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.s,
    #         hw=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.hw,
    #         tw=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.tw,
    #         b=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.b,
    #         tf=None if self._CylinderMain.LongStfObj is None else self._CylinderMain.LongStfObj.tf,
    #         CylinderAndCurvedPlate=CylinderAndCurvedPlate)

    #     self._CylinderMain.sasd = sasd
    #     self._CylinderMain.smsd = smsd
    #     self._CylinderMain.tTsd = abs(tTsd)
    #     self._CylinderMain.tQsd = abs(tQsd)
    #     self._CylinderMain.psd = pSd
    #     self._CylinderMain.shsd = shsd


class ShellType(IntEnum):
    # following the numbering in the standard
    UNSTIFFENED_PANEL = 3 # 3.3 Elastic buckling strength of unstiffened curved panels
    UNSTIFFENED_CYCLINDER = 4 # 3.4 Elastic buckling strength of unstiffened circular cylinders
    RING_STIFFENED_SHELL = 5 # 3.5 Ring stiffened shells
    LONGITUDINAL_STIFFENED_SHELL = 6 # 3.6 Longitudinal stiffened shells
    ORTHOGONALLY_STIFFENED_SHELL = 7 # 3.7 Orthogonally stiffened shells


class TorsionalProperties(BaseModel):
    '''
    Class for passing torsional properties of a stiffener.
    '''
    fET: float
    lambda_T: float
    fT: float


class CylindricalShell(BaseModel):
    '''
    Buckling of cylinders and curved plates.
    All input in SI units.
    '''
    curved_panel: CurvedPanel
    long_stf: Optional[Stiffener] = None
    # long_stf_spacing: Optional[float] # should this not be taken from 's' in the panel?
    ring_stf: Optional[Stiffener] = None
    # ring_stf_spacing: Optional[float] # should this not be taken from 'l' in the panel?
    ring_frame: Optional[Stiffener] = None
    ring_frame_spacing: Optional[float] = None # L: distance between effective supports (Figure 3-1)
    load: ShellStressAndPressure
    _geometry: ShellType = PrivateAttr(default=None) # It is determined from the given parameters
    tot_cyl_length: Optional[float] = None
    k_factor: Optional[float] = None
    delta0: Optional[float] = None # THIS IS THE VALUE INCLUDING RADIUS in line with (3.5.26)
    fab_method_ring_stf: Optional[str] = 'cold formed' # or 'fabricated' cold formed is conservative
    fab_method_ring_frame: Optional[str] = 'cold formed' # or 'fabricated' cold formed is conservative
    end_cap_pressure_included: bool = False # default is conservative
    uls_or_als: Optional[str] = 'ULS' # or 'ALS' ULS is conservative

    # Lots of checks to be done here
    # 1. If a ring stiffener is provided:
    #     - check that the spacing is provided -> done in validator
    #     - check that it matches the panel length
    #     - Check that the tot_cyl_length is given -> done in validator
    #     - Check that the geometry matches -> done in determining geometry
    # 2. If a longitundinal stiffener is provided:
    #     - check that the spacing is provided -> done in validator
    #     - check that it matches the panel s(spacing)
    #     - Check that the tot_cyl_length is given -> done in validator
    #     - Check that the geometry matches -> done in determining geometryvalidator
    # 3. If a ring frame is provided:
    #     - check that the spacing is provided -> done in validator
    #     - Check that the tot_cyl_length is given -> done in validator
    #     - Check that the geometry matches -> done in determining geometry
    # 4. Check possible values of cold formed/fabricated for ring stiffener and ring frame and set to lower case
    # 5. Check that uls_or_als is either ULS or ALS and set to upper case

    # Derive the StiffenedShellType from the given parameters.
    @model_validator(mode='after')
    def determine_geometry(self):
        if self.long_stf is None and self.ring_stf is None and self.ring_frame is None:
            # providing total cylinder length will determine if it is an unstiffened panel or cylinder
            if self.tot_cyl_length is None:
                self._geometry = ShellType.UNSTIFFENED_PANEL
            else:
                self._geometry = ShellType.UNSTIFFENED_CYCLINDER
        elif self.long_stf and self.ring_stf is None and self.ring_frame is None:
            # only longitudinal stiffener defined
            self._geometry = ShellType.LONGITUDINAL_STIFFENED_SHELL
        elif self.long_stf is None and (self.ring_stf or self.ring_frame):
            # no longitudinal stiffener but ring stiffener or ring frame
            self._geometry = ShellType.RING_STIFFENED_SHELL
        elif self.long_stf and (self.ring_stf or self.ring_frame):
            # both longitudinal stiffener and ring stiffener or ring frame
            self._geometry = ShellType.ORTHOGONALLY_STIFFENED_SHELL
        else:
            raise ValueError('Could not determine geometry from the given parameters')
        
        return self

    @model_validator(mode='after')
    def checks_if_tot_cyl_length_given(self):
        if self.tot_cyl_length: 
            if self.k_factor is None:
                raise ValueError('If tot_cyl_length is given, k_factor must also be given')
        return self

    @model_validator(mode='after')
    def checks_if_ring_stf_given(self):
        if self.ring_stf: 
            # if self.ring_stf_spacing is None:
            #     raise ValueError('If ring_stf is given, ring_stf_spacing must also be given')
            if self.tot_cyl_length is None:
                raise ValueError('If ring_stf is given, tot_cyl_length must also be given')
            if self.k_factor is None:
                raise ValueError('If ring_stf is given, k_factor must also be given')
            # if self.curved_panel.l != self.ring_stf_spacing:
            #     raise ValueError('Value s in spacing of the curved_panel and long_stf_spacing must match')
        return self

    @model_validator(mode='after')
    def checks_if_ring_frame_given(self):
        if self.ring_frame:
            if self.ring_frame_spacing is None:
                raise ValueError('If ring_frame is given, ring_frame_spacing must also be given')
            if self.tot_cyl_length is None:
                raise ValueError('If ring_frame is given, tot_cyl_length must also be given')
            if self.k_factor is None:
                raise ValueError('If ring_frame is given, k_factor must also be given')
        return self

    # @field_validator('delta0')
    @model_validator(mode='after')
    def check_delta0(self):
        if self.delta0 is None:
            self.delta0 = 0.005 * self.curved_panel.radius
        if self.delta0 < 0:
            raise ValueError('delta0 must be positive')
        return self


    def __str__(self):
        '''
        Returning all properties.
        '''

        long_string = 'N/A' if self.long_stf is None else self.long_stf.get_beam_string()
        ring_string = 'N/A' if self.ring_stf is None else self.ring_stf.get_beam_string()
        frame_string = 'N/A' if self.ring_frame is None else self.ring_frame.get_beam_string()
        # curved_panel.s holds the spacing of the panel, also for longitudinally stiffened panels
        # could update based on self.geometry
        s = max([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
            self.curved_panel.s

        if self.tot_cyl_length == None:
            length: str = 'N/A'
        else:
            length = str(self.tot_cyl_length * 1000) + ' mm'
        
        # what is the difference between distance betwen rings and the length of the shell?
        return \
            str(
            '\n Cylinder radius:               ' + str(round(self.curved_panel.radius,3)) + ' meters' +
            '\n Cylinder thickness:            ' + str(self.curved_panel.thickness * 1000)+' mm'+
            '\n Distance between rings, l:     ' + str(self.curved_panel.l * 1000)+' mm'+
            '\n Length of shell, L:            ' + length +
            '\n Total cylinder lenght:         ' + length +
            '\n Eff. Buckling length factor:   ' + str(self.k_factor)+
            '\n Material yield:                ' + str(self.curved_panel.material.strength / 1e6)+' MPa'+
            '\n Spacing/panel circ., s:        ' + str(s) + ' mm' +
            '\n Longitudinal stiffeners:       ' + long_string +
            '\n Ring stiffeners                ' + ring_string +
            '\n Ring frames/girders:           ' + frame_string +
            '\n Design axial stress/force:     ' + str(self.load.saSd/1e6)+' MPa'+
            '\n Design bending stress/moment:  ' + str(self.load.smSd/1e6)+' MPa'+
            '\n Design tosional stress/moment: ' + str(self.load.tTSd/1e6)+' MPa'+
            '\n Design shear stress/force:     ' + str(self.load.tQSd/1e6)+' MPa'+
            '\n Design lateral pressure        ' + str(self.load.pSd/1e6)+' MPa'+
            '\n Additional hoop stress         ' + str(self.load.shSd_add/1e6)+' MPa')


    def get_utilization_factors(self, optimizing = False, empty_result_dict = False) -> Dict[str, Any]:
        '''
        If optimizing running time must be reduced.
        '''
        # Local buckling of stiffeners

        results = {'Unstiffened shell': None,
                   'Longitudinal stiffened shell': None,
                   'Ring stiffened shell': None,
                   'Heavy ring frame': None,
                   'Column stability check': None,
                   'Column stability UF': None,
                   'Stiffener check': None,
                   'Stiffener check detailed': None,
                               'Weight': None}

        if empty_result_dict:
            return results
        data_shell_buckling = self.shell_buckling()
        shell_results, column_buckling_results = None, None
        
        # UF for unstiffened shell
        if self._geometry in [ShellType.UNSTIFFENED_CYCLINDER, ShellType.RING_STIFFENED_SHELL]:
            shell_results = self.shell_unstiffened_cylinder(shell_data=data_shell_buckling)
            uf_unstf_shell = shell_results['UF - Unstiffened circular cylinder']
            results['Unstiffened shell'] = uf_unstf_shell
        else:
            if self.curved_panel.l / self.curved_panel.s < 1:
                logger.info('Shell buckling performed according 3.4.2 because l/s < 1')
                shell_results = self.shell_unstiffened_cylinder(shell_data=data_shell_buckling)
                uf_unstf_shell = shell_results['UF - Unstiffened circular cylinder']
                results['Unstiffened shell'] = uf_unstf_shell
            else:
                shell_results = self.shell_curved_panel(shell_data=data_shell_buckling)
                uf_unstf_shell = shell_results['UF - Unstiffened curved panel']
                results['Unstiffened shell'] = uf_unstf_shell

        if optimizing:
            if uf_unstf_shell > 1:
                return False, 'UF unstiffened', results
        
        # column buckling for unstiffened cylinder
        if self._geometry == ShellType.UNSTIFFENED_CYCLINDER:
            column_buckling_results= self.column_buckling(unstf_shell_data=shell_results)

            results['Column stability check'] = column_buckling_results['Column stability check']
            results['Column stability UF']  = column_buckling_results['Column stability UF']
            results['Need to check column buckling'] = column_buckling_results['Need to check column buckling']
        

        # UF for longitudinal stiffener
        if self._geometry in [ShellType.LONGITUDINAL_STIFFENED_SHELL, ShellType.ORTHOGONALLY_STIFFENED_SHELL]:
            shell_results = self.shell_curved_panel(shell_data=data_shell_buckling)
            
            lightly_stiffened_check = self.curved_panel.s / self.curved_panel.thickness > 3 * math.sqrt(self.curved_panel.radius / self.curved_panel.thickness)
            if lightly_stiffened_check and not self._geometry == ShellType.ORTHOGONALLY_STIFFENED_SHELL:
                logger.warning('The structure is a lightly stiffened shell, thus calculated as an unstiffened cylinder')
                column_buckling_results= self.column_buckling(unstf_shell_data=shell_results)

                results['Column stability check'] = column_buckling_results['Column stability check']
                results['Column stability UF']  = column_buckling_results['Column stability UF']
                results['Need to check column buckling'] = column_buckling_results['Need to check column buckling']
                
                # Will optimisation work, if the stiffener check is not done?
                if optimizing:
                    if not results['Column stability check']:
                        return False, 'Column stability', results
                    raise ValueError('The structure is a lightly stiffened shell, thus calculated as an unstiffened shell\n \
                                     Update dimensions to avoid this, see section 3.6.1')

                return results
            
            # Heavy stiffened shell
            column_buckling_results= self.column_buckling(unstf_shell_data=shell_results)
            long_stf_shell_results = self.longitudinally_stiffened_shell(shell_curved_panel_results=shell_results)

            results['Column stability check'] = column_buckling_results['Column stability check']
            results['Column stability UF']  = column_buckling_results['Column stability UF']
            results['Need to check column buckling'] = column_buckling_results['Need to check column buckling']
            results['Longitudinal stiffened shell'] = long_stf_shell_results['UF - Longitudinal stiffener']

            if optimizing:
                if not results['Column stability check']:
                    return False, 'Column stability', results
                # elif False in results['Stiffener check'].values():
                #     return False, 'Stiffener check', results
                elif results['Longitudinal stiffened shell'] > 1:
                    return False, 'UF longitudinal stiffeners', results

        # UF for ring stiffener and/or ring frame
        if self._geometry in [ShellType.RING_STIFFENED_SHELL, ShellType.ORTHOGONALLY_STIFFENED_SHELL]:
            # UF for panel ring buckling
            ring_stf_shell_results = None
            column_buckling_results = self.column_buckling(unstf_shell_data=shell_results)
            ring_stf_shell_results = self.ring_stiffened_shell(data_shell_buckling=data_shell_buckling, unstf_shell_data=shell_results)

            results['Column stability check'] = column_buckling_results['Column stability check']
            results['Column stability UF'] = column_buckling_results['Column stability UF']
            results['Need to check column buckling'] = column_buckling_results['Need to check column buckling']
            results['Ring stiffened shell'] = ring_stf_shell_results[0]

            if optimizing:
                if not results['Column stability check']:
                    return False, 'Column stability', results
                # elif False in results['Stiffener check'].values():
                #     return False, 'Stiffener check', results
                elif results['Ring stiffened shell'] > 1:
                    return False, 'UF ring stiffeners', results

            # UF for ring frame
            if self.ring_frame is not None:
                results['Heavy ring frame'] = ring_stf_shell_results[1]

                if optimizing:
                    if results['Heavy ring frame'] > 1:
                        return False, 'UF ring frame', results

        if optimizing:
            return True, 'Check OK', results

        logger.debug(f'Results for geometry:')
        logger.debug(f'Shell type: {str(self._geometry.name)}')
        logger.debug(str(self))
        # logger.debug(results)

        return results


    def shell_buckling(self):
        # Should rename and create an object for the results iso a dict
        '''
        Preparation of the shell buckling calculations.
        '''
        stucture_objects = {'Unstiffened': self.curved_panel, 'Long Stiff.': self.long_stf, 'Ring Stiffeners': self.ring_stf,
                            'Heavy ring Frame': self.ring_frame}
        # stf_type = ['T', 'FB', 'T']
        # assertion is taken care of by Pyndatic in CurvedPanel
        # assert self._Shell.dist_between_rings is not None, 'Input missing: self._Shell.dist_between_rings'
        # assert self._Shell.radius is not None, 'Input missing: self._Shell.radius'
        # assert self._Shell.thk is not None, 'Input missing: self._Shell.thk'

        l = self.curved_panel.l * 1000
        r = self.curved_panel.radius * 1000
        t = self.curved_panel.thickness * 1000

        # in order not to have unbound variables
        A, sxSd_used = 0, 0
        alpha, beta, le0, zeta, rf, r0, zt = 0, 0, 0, 0, 0, 0, 0

        parameters, cross_sec_data = list(), list()
        for key, obj in stucture_objects.items():
            if obj is None:
                cross_sec_data.append([np.nan, np.nan, np.nan, np.nan, np.nan])
                if key not in ['Unstiffened', 'Long Stiff.']:
                    parameters.append([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])
                continue
            if key != 'Unstiffened':
                # distance from stiffener toe (connection between stiffener and plate) to the shear centre of the stiffener
                hs = obj.hw / 2 if obj.type == 'FB' else obj.hw + obj.tf / 2
                It = obj.get_torsional_moment_venant()
                se = self.curved_panel.get_effective_width_shell_plate()
                
                Ipo = obj.get_polar_moment()
                Iz = obj.get_Iz_moment_of_inertia()

                Iy = obj.get_moment_of_intertia(plate_thickness=t/1000, plate_width=se/1000) * 1000**4

                cross_sec_data.append([hs, It, Iz, Ipo, Iy])

                A = obj.get_cross_section_area() * math.pow(1000, 2)
                beta = l / (1.56 * math.sqrt(r * t))
                le0 = (l / beta) * ((math.cosh(2 * beta) - math.cos(2 * beta)) / (math.sinh(2 * beta) + math.sin(2 * beta)))

                # assertion is taken care of by Pyndatic in CylindricalShell
                # assert self._sasd is not None, 'Input missing: self._sasd'
                # assert self._smsd is not None, 'Input missing: self._smsd'

                worst_axial_comb = min(self.load.saSd / 1e6 - self.load.smSd / 1e6, self.load.saSd / 1e6 + self.load.smSd / 1e6)
                sxSd_used = worst_axial_comb

                if key == 'Long Stiff.':
                    zp = obj.get_cross_section_centroid() * 1000
                    h_tot = obj.hw + obj.tf
                    zt = h_tot - zp
                else:
                    se = self.curved_panel.get_effective_width_shell_plate()
                    zp = obj.get_cross_section_centroid(plate_thickness=t/1000, plate_width=se/1000) * 1000 # ch7.5.1 page 19
                    h_tot = t + obj.hw + obj.tf
                    zt = h_tot - zp

            if key not in ['Unstiffened', 'Long Stiff.']:  # Parameters
                alpha = A / (le0 * t)
                zeta = max([0, 2 * (math.sinh(beta) * math.cos(beta) + math.cosh(beta) * math.sin(beta))/
                            (math.sinh(2 * beta) + math.sin(2 * beta))])
                rf = r - t / 2 - (obj.hw + obj.tf)

                r0 = zt + rf
                parameters.append([alpha, beta, le0, zeta, rf, r0, zt])

        sxSd, shSd, shRSd, tSd = list(), list(), list(), list()

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # with pSd a force, is shSd then not just be the hoop stress?
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        for key, obj in stucture_objects.items():
            if obj is None:
                shRSd.append(np.nan)
                continue
            assert self.load.pSd is not None, 'Input missing: self._psd'

            if key == 'Unstiffened':
                shSd.append((self.load.pSd / 1e6) * r / t + self.load.shSd_add / 1e6)
                # why difference in calculation for sxSd?
                sxSd.append(self.load.saSd / 1e6 + self.load.smSd / 1e6 if self._geometry in [ShellType.UNSTIFFENED_PANEL, ShellType.RING_STIFFENED_SHELL] else
                            min([self.load.saSd / 1e6, self.load.saSd / 1e6 - self.load.smSd / 1e6, self.load.saSd / 1e6 + self.load.smSd / 1e6]))
                # whould this not be the sum of the absolute value of the two. There exists a point where these to add up.
                tSd.append(self.load.tTSd / 1e6 + self.load.tQSd / 1e6)
            elif key == 'Long Stiff.':
                # assertion is taken care of by Pydantic in CylindricalShell
                # assert +self._shsd is not None, 'Input missing: self._shsd'
                # assert +self._tTsd is not None, 'Input missing: self._tTsd'
                # assert +self._tQsd is not None, 'Input missing: self._tQsd'

                if stucture_objects['Ring Stiffeners'] == None:
                    shSd.append(shSd[0] + self.load.shSd_add / 1e6)
                else:
                    shSd_ring = ((self.load.pSd/1e6) * r / t)-parameters[0][0] * parameters[0][3] / (parameters[0][0] + 1) * \
                                ((self.load.pSd/1e6) * r / t - self.curved_panel.material.poisson * sxSd[0])
                    shSd.append(shSd_ring + self.load.shSd_add / 1e6)

                if self._geometry in [6, 7]:
                    sxSd.append(sxSd_used)
                else:
                    sxSd.append(sxSd[0])

                # whould this not be the sum of the absolute value of the two. There exists a point where these to add up.
                tSd.append(self.load.tTSd / 1e6 + self.load.tQSd / 1e6)

            elif key == 'Ring Stiffeners':
                rf = parameters[0][4]
                shSd_ring = ((self.load.pSd / 1e6) * r / t) - parameters[0][0] * parameters[0][3] / (parameters[0][0] + 1) * \
                            ((self.load.pSd / 1e6) * r / t - self.curved_panel.material.poisson * sxSd[0])
                shSd.append(np.nan if stucture_objects['Ring Stiffeners'] == None else shSd_ring)
                shRSd.append(((self.load.pSd / 1e6) * r / t - self.curved_panel.material.poisson * sxSd[0]) * (1 / (1 + parameters[0][0])) * (r / rf))
                if self._geometry not in [3, 4]:
                    sxSd.append(sxSd[0])
                    tSd.append(tSd[0])
                else:
                    sxSd.append(np.nan)
                    tSd.append(np.nan)

            else:
                rf = parameters[1][4]
                shSd.append(((self.load.pSd / 1e6) * r / t) - parameters[1][0] * parameters[1][3] / (parameters[1][0] + 1)*
                            ((self.load.pSd / 1e6) * r / t - self.curved_panel.material.poisson * self.load.saSd / 1e6))
                shRSd.append(((self.load.pSd / 1e6) * r / t - self.curved_panel.material.poisson * self.load.saSd / 1e6) * (1 / (1 + parameters[1][0])) * (r / rf))
                if self._geometry not in [3, 4]:
                    sxSd.append(sxSd[0])
                    tSd.append(tSd[0])
                else:
                    sxSd.append(np.nan)
                    tSd.append(np.nan)

        sxSd = np.array(sxSd)
        shSd = np.array(shSd)
        # Here the abs is taken, but probably earlier we should take the sum of the abolutes?
        tSd = np.array(np.abs(tSd))
        sjSd = np.sqrt(sxSd**2 - sxSd * shSd + shSd**2 + 3 * tSd**2)

        return {'sjSd': sjSd, 'parameters': parameters, 'cross section data': cross_sec_data,
                'shRSd': shRSd, 'shSd': shSd, 'sxSd': sxSd}


    def shell_curved_panel(self, conical=False, shell_data=None):
        # should implement the result as an object. Can definitely be shared with shell_unstiffened_cylinder

        # 3.3.2 if for:
        #  - ShellType.UNSTIFFENED_PANEL
        #  - ShellType.LONGITUDINAL_STIFFENED_SHELL
        #  - ShellType.ORTHOGONALLY_STIFFENED_SHELL
        # 3.4.2 is for:
        #  - ShellType.UNSTIFFENED_CYCLINDER
        #  - ShellType.RING_STIFFENED_SHELL

        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000

        s = self.curved_panel.s * 1000
        v = self.curved_panel.material.poisson
        r = self.curved_panel.radius * 1000
        # the original line seems not correct?
        # l = self._Shell.dist_between_rings * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6
        saSd = self.load.saSd / 1e6
        smSd = self.load.smSd / 1e6
        # Should this not be the sum of the abs values? There exists a point where these to add up.
        tSd = abs(self.load.tTSd / 1e6 + self.load.tQSd / 1e6)
        pSd = self.load.pSd / 1e6

        results = dict()
        if self.ring_stf is None:
            shSd = shell_data['shSd'][0] # type: ignore
            results['shSd'] = shSd # passing this on to the next function, as it's used in column buckling
        else:
            shSd = shell_data['shSd'][1] #type: ignore
            results['shSd'] = shSd # passing this on to the next function, as it's used in column buckling

        
        #   Pnt. 3.3 Unstifffed curved panel.
        # Is later used in:
        #  - ShellType.UNSTIFFENED_PANEL
        #  - ShellType.LONGITUDINAL_STIFFENED_SHELL
        #  - ShellType.ORTHOGONALLY_STIFFENED_SHELL
        geometry = self._geometry

        # why is sxSd not the most conservative in all cases?
        if geometry in [ShellType.UNSTIFFENED_PANEL, ShellType.RING_STIFFENED_SHELL]:
            sxSd = saSd + smSd
        else:
            sxSd = min(saSd, saSd + smSd, saSd - smSd)

        if smSd < 0:
            smSd = -smSd
            sm0sd = -smSd
        else:
            # should this not only be unstiffened? ring stiffend shell is according section 3.4.2
            if geometry in [ShellType.UNSTIFFENED_PANEL, ShellType.RING_STIFFENED_SHELL]:
                smSd = 0
                sm0sd = 0
            else:
                # results['gammaM curved panel'] = gammaM        smSd = smSd
                sm0sd = smSd

        sjSd = math.sqrt(math.pow(sxSd, 2) - sxSd * shSd + math.pow(shSd, 2) + 3 * math.pow(tSd, 2))  # (3.2.3)

        Zs = self.curved_panel.Zs # The curvature parameter Zs (3.3.3)
        logger.debug(f'Zs {Zs}')

        def table_3_1(chk):
            # ψ
            psi = {'Axial stress': 4,
                   'Shear stress': 5.34 + 4 * math.pow(s / l, 2),
                   'Circumferential compression': math.pow(1 + math.pow(s / l, 2), 2)}
            # ξ
            epsilon = {'Axial stress': 0.702 * Zs,
                       'Shear stress': 0.856 * math.sqrt(s / l) * math.pow(Zs, 3/4),
                       'Circumferential compression': 1.04 * (s / l) * math.sqrt(Zs)}
            # ρ
            rho = {'Axial stress': 0.5 * math.pow(1 + (r / (150 * t)), -0.5),
                   'Shear stress': 0.6,
                   'Circumferential compression': 0.6}
            return psi[chk], epsilon[chk], rho[chk]
        vals = list()

        for chk in ['Axial stress', 'Shear stress', 'Circumferential compression']:
            psi, epsilon, rho = table_3_1(chk=chk)
            C = psi * math.sqrt(1 + math.pow(rho * epsilon / psi, 2))  # (3.4.2) (3.6.4)
            fE = C * (math.pow(math.pi, 2) * E / (12 * (1 - math.pow(v, 2)))) * math.pow(t / s, 2)
            logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
            vals.append(fE)

        fEax, fEshear, fEcirc = vals
        logger.debug(f'fEax {fEax} fEshear {fEshear} fEcirc {fEcirc}')

        sa0Sd = -sxSd if sxSd < 0 else 0
        sh0Sd = -shSd if shSd < 0 else 0 # Maximium allowable stress from iteration.

        if any([val == 0 for val in vals]):
            lambda_s_pow = 0
        else:
            lambda_s_pow = (fy / sjSd) * (sa0Sd / fEax + sh0Sd / fEcirc + tSd / fEshear)

        lambda_s = math.sqrt(lambda_s_pow)
        fks = fy / math.sqrt(1 + math.pow(lambda_s, 4))

        results['fks - Unstiffened curved panel'] = fks
        if lambda_s < 0.5:
            gammaM = self.curved_panel.material.mat_factor
        else:
            # why is gammaM dependant the user provided mat_factor?
            if self.curved_panel.material.mat_factor == 1.1:
                if lambda_s > 1:
                    gammaM = 1.4
                else: 
                    gammaM = 0.8 + 0.6 * lambda_s
            elif self.curved_panel.material.mat_factor == 1.15:
                if lambda_s > 1:
                    gammaM = 1.45
                else:
                    gammaM = 0.85 + 0.6 * lambda_s
            else:
                if lambda_s > 1:
                    gammaM = 1.45 * (self.curved_panel.material.mat_factor / 1.15)
                else:
                    gammaM = 0.85 + 0.6 * lambda_s * (self.curved_panel.material.mat_factor / 1.15)
        
        if self.uls_or_als == 'ALS':
            gammaM = gammaM / self.curved_panel.material.mat_factor
        
        results['gammaM - Unstiffened curved panel'] = gammaM
        fksd = fks / gammaM
        results['fksd - Unstiffened curved panel'] = fksd
        uf = sjSd / fksd

        logger.debug(f'sjSd {sjSd} lambda_s {lambda_s} lambda_s_pow {lambda_s_pow} fks {fks} gammaM {gammaM} fksd {fksd} uf {uf}')

        results['UF - Unstiffened curved panel'] = uf
        # next was double
        # results['gammaM curved panel'] = gammaM
        
        # what is sjSd_max?
        sjSd_max = math.sqrt(math.pow(saSd + smSd, 2) - (saSd + smSd) * shSd + math.pow(shSd, 2) + 3 * math.pow(tSd, 2))
        uf_max =  self.curved_panel.material.mat_factor * sjSd_max / fy

        # No column buckling check for unstiffened panel, thus not need to calculate the max axial stress
        if self._geometry == ShellType.UNSTIFFENED_PANEL:
            return results
        
        # is iter_table_1 and iter_table_2 not the same?
        # could this be replaces with a scypy optimization function? Or newton-rhapson alternative?
        # could this be moved to a separate function?
        def iter_table_1():
            found, saSd_iter, count, this_val, history  = False, 0.001 if uf > 1 else saSd, 0, 0, list()

            while not found:
                # Iteration
                sigmSd_iter = smSd if geometry == ShellType.UNSTIFFENED_PANEL else min([-smSd, smSd])
                siga0Sd_iter = 0 if saSd_iter >= 0 else -saSd_iter  # (3.2.4)
                sigm0Sd_iter = 0 if sigmSd_iter >= 0 else -sigmSd_iter  # (3.2.5)
                sigh0Sd_iter = 0 if shSd >= 0 else -shSd  # (3.2.6)

                sjsd_iter = math.sqrt(math.pow(saSd_iter + sigmSd_iter, 2) - (saSd_iter + sigmSd_iter) * shSd + math.pow(shSd, 2)+
                                      3 * math.pow(tSd, 2)) #(3.2.3)
                lambdas_iter = math.sqrt((fy / sjsd_iter) * ((siga0Sd_iter + sigm0Sd_iter) / fEax + sigh0Sd_iter / fEcirc + tSd / fEshear)) # (3.2.2)

                gammaM_iter = 1  # As taken in the DNVGL sheets
                fks_iter = fy / math.sqrt(1 + math.pow(lambdas_iter, 4))
                fksd_iter = fks_iter / gammaM_iter
                logger.debug(f'sjSd {sjsd_iter} fksd {fksd_iter} fks {fks} gammaM {gammaM_iter} lambdas_iter {lambdas_iter}')
                this_val = sjsd_iter/fksd_iter
                history.append(0 if this_val > 1 else siga0Sd_iter)
                if this_val > 1.0 or count == 1e6:
                    found = True
                count += 1
                if this_val > 0.98:
                    saSd_iter -= 0.5
                elif this_val > 0.95:
                    saSd_iter -= 1
                elif this_val > 0.9:
                    saSd_iter -= 2
                elif this_val > 0.7:
                    saSd_iter -= 10
                else:
                    saSd_iter -= 20

                logger.debug(f'sasd_iter {saSd_iter} this_val {this_val}')

            # return 0 if len(history) == 1 else max(history[-2],0)
            # Should this not be absolute value? Othwerwise negative values become zero
            # The note in 3.8.2 mentions sa0Sd (saSd)
            return 0 if len(history) == 1 else abs(history[-2])

        results['max axial stress - 3.3 Unstiffened curved panel'] = iter_table_1()
        logger.debug(f"Max axial stress {results['max axial stress - 3.3 Unstiffened curved panel']}")
        
        return results


    def shell_unstiffened_cylinder(self, conical=False, shell_data=None):
        # should implement the result as an object. Can definitely be shared with shell_curved_panel

        results = dict()
        # 3.3.2 if for:
        #  - ShellType.UNSTIFFENED_PANEL
        #  - ShellType.LONGITUDINAL_STIFFENED_SHELL
        #  - ShellType.ORTHOGONALLY_STIFFENED_SHELL
        # 3.4.2 is for:
        #  - ShellType.UNSTIFFENED_CYCLINDER
        #  - ShellType.RING_STIFFENED_SHELL

        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000

        # get correct s
        # s is not used in the code, which makes sence as both the unstiffened cylinder and the ring stiffened shell
        # are a full ring, and thus fully determined by the radius and thickness
        v = self.curved_panel.material.poisson
        r = self.curved_panel.radius * 1000
        # the original line seems not correct?
        # l = self._Shell.dist_between_rings * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6
        saSd = self.load.saSd / 1e6
        smSd = self.load.smSd / 1e6
        # Should this not be the sum of the abs values? There exists a point where these to add up.
        tSd = abs(self.load.tTSd / 1e6 + self.load.tQSd / 1e6)
        pSd = self.load.pSd / 1e6

        if self.ring_stf is None:
            shSd = shell_data['shSd'][0] # type: ignore
            results['shSd'] = shSd # passing this on to the next function, as it's used in column buckling
        else:
            shSd = shell_data['shSd'][1] #type: ignore
            results['shSd'] = shSd # passing this on to the next function, as it's used in column buckling

        sxSd = min(saSd, saSd + smSd, saSd - smSd)

        # is this correct?
        if smSd < 0:
            smSd = -smSd
            sm0sd = -smSd
        else:
            sm0sd = smSd

        sjSd = math.sqrt(math.pow(sxSd, 2) - sxSd * shSd + math.pow(shSd, 2) + 3 * math.pow(tSd, 2))  # (3.2.3)


        # Pnt. 3.4 Unstifffed circular cylinders
        # Is later used in:
        #  - ShellType.UNSTIFFENED_CYCLINDER
        #  - ShellType.RING_STIFFENED_SHELL
        Zl = self.curved_panel.Zl # (3.4.3) (3.6.5)
        results['Zl'] = Zl
        logger.debug(f'Zl {Zl}')
        def table_3_2(chk):
            # ψ
            psi = {'Axial stress': 1,
                   'Bending': 1,
                   'Torsion and shear force': 5.34,
                   'Lateral pressure': 4, 
                   'Hydrostatic pressure': 2}
            # ξ
            epsilon= {'Axial stress': 0.702 * Zl,
                   'Bending': 0.702 * Zl,
                   'Torsion and shear force': 0.856 * math.pow(Zl, 3/4),
                   'Lateral pressure': 1.04 * math.sqrt(Zl),
                   'Hydrostatic pressure': 1.04 * math.sqrt(Zl)}
            # ρ
            rho = {'Axial stress': 0.5 * math.pow(1 + (r / (150 * t)), -0.5),
                   'Bending': 0.5 * math.pow(1 + (r / (300 * t)), -0.5),
                   'Torsion and shear force': 0.6,
                   'Lateral pressure': 0.6,
                   'Hydrostatic pressure': 0.6}
            return psi[chk], epsilon[chk], rho[chk]

        vals = list()
        for chk in ['Axial stress', 'Bending', 'Torsion and shear force',
                    'Lateral pressure','Hydrostatic pressure']:
            psi, epsilon, rho = table_3_2(chk=chk)
            C = psi * math.sqrt(1 + math.pow(rho * epsilon / psi, 2))  # (3.4.2) (3.6.4)
            fE = C * math.pow(math.pi, 2) * E / (12 * (1 - math.pow(v, 2))) * math.pow(t / l, 2)
            logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
            vals.append(fE)

        fEax, fEbend, fEtors, fElat, fEhyd = vals
        logger.debug(f'fEax {fEax} fEbend {fEbend} fEtors {fEtors} fElat {fElat} fEhyd {fEhyd}')

        results['fEax - Unstiffened circular cylinder'] = fEax

        test1 = 3.85 * math.sqrt(r / t)
        test2 = 2.25 * math.sqrt(r / t)
        test_l_div_r = l / r
        results['fEh - Unstiffened circular cylinder - Psi=4'] = 0.25 * E * math.pow(t / r, 2) if test_l_div_r > test2 else fElat
        if l / r > test1:
            fEt_used = 0.25 * E * math.pow(t / r, 3 / 2)  # (3.4.4)
        else:
            fEt_used = fEtors

        if l / r > test2:
            fEh_used = 0.25 * E * math.pow(t / r, 2)
        else:
            fEh_used = fElat if self.end_cap_pressure_included else fEhyd

        sjSd = math.sqrt(math.pow(sxSd,2) - sxSd*shSd + math.pow(shSd,2) + 3 * math.pow(tSd, 2))  # (3.2.3)

        sa0Sd = -saSd if saSd < 0 else 0
        sh0Sd = -shSd if shSd < 0 else 0


        if any([fEax == 0, fEbend == 0, fEt_used == 0, fEh_used == 0, sjSd == 0]):
            lambda_s_pow = 0
        else:
            lambda_s_pow = (fy / sjSd) * (sa0Sd / fEax + sm0sd / fEbend + sh0Sd / fEh_used + tSd / fEt_used)

        lambda_s = math.sqrt(lambda_s_pow)
        fks = fy / math.sqrt(1 + math.pow(lambda_s, 4))

        results['fks - Unstiffened circular cylinder'] = fks

        if lambda_s < 0.5:
            gammaM = self.curved_panel.material.mat_factor
        else:
            # why is gammaM dependanton the user provided mat_factor?
            if self.curved_panel.material.mat_factor == 1.1:
                if lambda_s > 1:
                    gammaM = 1.4
                else:
                    gammaM = 0.8+0.6*lambda_s
            elif self.curved_panel.material.mat_factor == 1.15:
                if lambda_s > 1:
                    gammaM = 1.45
                else:
                    gammaM = 0.85+0.6*lambda_s
            else:
                if lambda_s > 1:
                    gammaM = 1.45 * (self.curved_panel.material.mat_factor/1.15)
                else:
                    gammaM = 0.85+0.6*lambda_s * (self.curved_panel.material.mat_factor/1.15)
        
        if self.uls_or_als == 'ALS':
            gammaM = gammaM / self.curved_panel.material.mat_factor

        fksd = fks / gammaM
        results['fksd - Unstiffened circular cylinder'] = fksd
        uf = sjSd / fksd

        results['UF - Unstiffened circular cylinder'] = uf
        results['gammaM - Unstiffened circular cylinder'] = gammaM
        logger.debug(f'sjsd {sjSd} lambda_s {lambda_s} lambda_s_pow {lambda_s_pow} fks {fks} gammaM {gammaM} fksd {fksd} uf {uf}')
        
        # in this case we always end up with the requirement for a column buckling check
        # thus the determination of max axial stress is always required
        # but the check in column_buckling could still say it's not required
        # thus this should move to a separate function which only gets called
        # if the column buckling check is required

        def iter_table_2():
            found, sasd_iter, count, UF, history  = False, 0 if uf > 1 else saSd, 0, 0, list()
            while not found:
                # Iteration
                # why not always the negative value? Moment typically works in both directions
                # sigmsd_iter = smSd if geometry in [2, 6] else min([-smSd, smSd])
                sigmsd_iter = min([-smSd, smSd])
                siga0sd_iter = 0.00001 if sasd_iter >= 0 else -sasd_iter  # (3.2.4)
                sigm0sd_iter = 0.00001 if sigmsd_iter >= 0 else -sigmsd_iter  # (3.2.5)
                sigh0sd_iter = 0.00001 if shSd >= 0 else -shSd  # (3.2.6)
                sjsd_iter = math.sqrt(
                    math.pow(sasd_iter + sigmsd_iter, 2) - (sasd_iter + sigmsd_iter) * shSd + math.pow(shSd, 2) +
                    3 * math.pow(tSd, 2))  # (3.2.3)
                if sjsd_iter == 0:
                    sjsd_iter = 0.00001
                lambdas_iter = math.sqrt((fy/sjsd_iter) * (siga0sd_iter/fEax + sigm0sd_iter/fEbend +
                                                           sigh0sd_iter/fElat + tSd/fEtors))
                gammaM_iter = 1  # As taken in the DNVGL sheets
                fks_iter = fy / math.sqrt(1 + math.pow(lambdas_iter, 4))
                fksd_iter = fks_iter / gammaM_iter

                UF = sjsd_iter / fksd_iter
                history.append(sasd_iter)

                logger.debug(f'UF {UF} saSd {sasd_iter} sjSd {sjsd_iter} fksd {fksd_iter} fks {fks} gammaM {gammaM_iter} lambdas_iter {lambdas_iter}')

                if UF > 1.0 or count == 1e6:
                    found = True
                count += 1

                if UF >0.98:
                    sasd_iter -= 0.5
                elif UF > 0.95:
                    sasd_iter -= 1
                elif UF > 0.9:
                    sasd_iter -= 2
                elif UF > 0.7:
                    sasd_iter -= 10
                else:
                    sasd_iter -= 20

            # return 0 if len(history) == 1 else max(history[-2],0)
            # Should this not be absolute value? Othwerwise negative values become zero
            # The note in 3.8.2 mentions sa0Sd (saSd)
            return 0 if len(history) == 1 else abs(history[-2])

        results['max axial stress - 3.4.2 Shell buckling'] = iter_table_2()
        results['shSd'] = shSd
        logger.debug(f"Max axial stress {results['max axial stress - 3.4.2 Shell buckling']}")

        return results


    def ring_stiffened_shell(self, data_shell_buckling=None, unstf_shell_data=None):

        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000

        # get correct s
        # curved_panel.s holds the spacing of the panel, also for longitudinally stiffened panels
        # could update based on self.geometry
        s = max([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
            self.curved_panel.s
        v = self.curved_panel.material.poisson
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6

        # should the distinction be made between total cylinder length and LH (ring_frame_spacing)?
        L = self.tot_cyl_length * 1000 # type: ignore
        #LH = L
        LH = self.ring_frame_spacing * 1000 if self.ring_frame_spacing != None else 0 # input is checked for spacing if frame is defined

        # same as for the unstiffened shell
        saSd = self.load.saSd / 1e6
        smSd = self.load.smSd / 1e6
        # Should this not be the sum of the abs values? There exists a point where these to add up.
        tSd = abs(self.load.tTSd / 1e6 + self.load.tQSd / 1e6) # MAYBE MAYBE NOT.
        pSd = self.load.pSd / 1e6

        data_shell_buckling = self.shell_buckling() if data_shell_buckling == None else data_shell_buckling

        #Pnt. 3.5:  Ring stiffened shell

        # Pnt. 3.5.2.1   Requirement for cross-sectional area:
        #Zl = self._Shell.get_Zl()

        Zl = self.curved_panel.Zl
        Areq = (2 / math.pow(Zl, 2) + 0.06) * l * t
        Areq = np.array([Areq, Areq])
        Astf = np.nan if self.ring_stf is None else self.ring_stf.get_cross_section_area() * 1000**2
        Aframe = np.nan if self.ring_frame is None else \
            self.ring_frame.get_cross_section_area() * 1000**2
        A = np.array([Astf, Aframe])

        uf_cross_section = Areq / A

        #Pnt. 3.5.2.3   Effective width calculation of shell plate
        lef = 1.56 * math.sqrt(r * t) / (1 + 12 * t / r)
        # lef_used = np.array([min([lef, LH]), min([lef, LH])])

        #Pnt. 3.5.2.4   Required Ix for Shell subject to axial load
        A_long_stf = 0 if self.long_stf is None else self.long_stf.get_cross_section_area() * 1000**2
        alfaA = A_long_stf / (s * t)


        # What index is what? This is not clear from the code
        # looks like 0 is ring stiffner and 1 is ring frame
        # the index 5 is indeed r0
        r0 = np.array([data_shell_buckling['parameters'][0][5], data_shell_buckling['parameters'][1][5]])
        # the above returns nan if the ring is not defined. Replace with zero's if so.
        # this whould be tackled in data_shell_buckling code
        r0[np.isnan(r0)] = 0

        worst_ax_comp = min([saSd + smSd, saSd - smSd])

        Ixreq = np.array([abs(worst_ax_comp) * t * (1 + alfaA) * math.pow(r0[0], 4) / (500 * E * l),
                          abs(worst_ax_comp) * t * (1 + alfaA) * math.pow(r0[1], 4) / (500 * E * l)])

        # Pnt. 3.5.2.5   Required Ixh for shell subjected to torsion and/or shear:
        Ixhreq = np.array([math.pow(tSd / E, (8/5)) * math.pow(r0[0] / L, 1/5) * L * r0[0] * t * l,
                           math.pow(tSd / E, (8/5)) * math.pow(r0[1] / L, 1/5) * L * r0[1] * t * l])

        #Pnt. 3.5.2.6   Simplified calculation of Ih for shell subjected to external pressure
        zt = np.array([data_shell_buckling['parameters'][0][6], data_shell_buckling['parameters'][1][6]])
        rf = np.array([data_shell_buckling['parameters'][0][4], data_shell_buckling['parameters'][1][4]])

        # updated definition: delta0 is the value including the r, eg 0.005 * r
        #delta0 = r * self._delta0
        delta0 = self.delta0

        fb_ring_req_val = np.array([0 if self.ring_stf is None else 0.4 * self.ring_stf.tw * math.sqrt(E / fy),
                                    0 if self.ring_frame is None else 0.4 * self.ring_frame.tw * math.sqrt(E / fy)])

        flanged_rf_req_h_val = np.array([0 if self.ring_stf is None else 1.35 * self.ring_stf.tw * math.sqrt(E / fy),
                                         0 if self.ring_frame is None else 1.35 * self.ring_frame.tw * math.sqrt(E / fy)])

        flanged_rf_req_b_val = np.array([0 if self.ring_stf is None else 7 * self.ring_stf.hw / math.sqrt(10 + E * self.ring_stf.hw / (fy * r)),
                                         0 if self.ring_frame is None else 7 * self.ring_frame.hw / math.sqrt(10 + E * self.ring_frame.hw / (fy * r))])

        if self.ring_stf is not None:
            spf_stf = self.ring_stf.hw / fb_ring_req_val[0] if self.ring_stf.type == 'FB' \
                else max([flanged_rf_req_b_val[0] / self.ring_stf.b, self.ring_stf.hw / flanged_rf_req_h_val[0]])
        else:
            spf_stf = 0

        if self.ring_frame is not None:
            spf_frame = self.ring_frame.hw / fb_ring_req_val[1] if self.ring_frame.type == 'FB' \
                else max([flanged_rf_req_b_val[1] / self.ring_frame.b, self.ring_frame.hw / flanged_rf_req_h_val[1]])
        else:
            spf_frame = 0

        stocky_profile_factor = np.array([spf_stf, spf_frame])

        torsional_buckling_properties = self.torsional_buckling(shell_buckling_data=data_shell_buckling, unstf_shell_data=unstf_shell_data)
        fT = np.array([torsional_buckling_properties['Ring Stiff.'].fT if stocky_profile_factor[0] > 1 else fy,
                       torsional_buckling_properties['Ring Frame'].fT if stocky_profile_factor[1] > 1 else fy])

        fr_used = np.array([fT[0] if self.fab_method_ring_stf == 'fabricated' else 0.9 * fT[0],
                            fT[1] if self.fab_method_ring_frame == 'fabricated' else 0.9 * fT[1]])
        shRsd = [abs(val) for val in data_shell_buckling['shRSd']]

        # Neither E or r0 can be zero
        Ih = np.array([0 if (fr_used[idx] / 2 - abs(shRsd[idx])) == 0 else abs(pSd) * r * math.pow(r0[idx], 2) * l / (3 * E) *
                                                                        (1.5 + 3 * E * zt[idx] * delta0 / 
                                                                        (math.pow(r0[idx], 2) * (fr_used[idx] / 2 - shRsd[idx])))
                                                                        for idx in [0,1]])

        # Pnt. 3.5.2.2     Moment of inertia:
        IR = [Ih[idx] + Ixhreq[idx] + Ixreq[idx] if all([pSd <= 0, Ih[idx] > 0]) else Ixhreq[idx] + Ixreq[idx]
              for idx in [0,1]]
        Iy = [data_shell_buckling['cross section data'][idx+1][4] for idx in [0, 1]]

        uf_moment_of_inertia = list()
        for idx in [0,1]:
            if Iy[idx] > 0:
                # What is the check 'fr_used[idx] < 2 * shRsd[idx]' ?
                uf_moment_of_inertia.append(9.999 if fr_used[idx] < 2 * shRsd[idx] else IR[idx] / Iy[idx])
            else:
                uf_moment_of_inertia.append(0)

        # Pnt. 3.5.2.7   Refined calculation of external pressure
        # parameters.append([alpha, beta, leo, zeta, rf, r0, zt])
        I = Iy
        Ihmax = [max(0, I[idx] - Ixhreq[idx] - Ixreq[idx]) for idx in [0,1]]
        leo = [data_shell_buckling['parameters'][idx][2] for idx in [0, 1]]
        Ar = A
        ih2 = [0 if Ar[idx] + leo[idx] * t == 0 else Ihmax[idx] / (Ar[idx] + leo[idx] * t) for idx in [0,1]]
        alpha_B = [12 * (1 - math.pow(v, 2)) * Ihmax[idx] / l / math.pow(t, 3) for idx in [0,1]] # l or t are validated in CurvedPanel
        alpha = [data_shell_buckling['parameters'][idx][0] for idx in [0,1]]
        ZL = [math.pow(L, 2) / r / t * math.sqrt(1 - math.pow(v, 2)) for _ in [0,1]]

        C1 = [2 * (1 + alpha_B[idx]) / (1 + alpha[idx]) * (math.sqrt(1 + 0.27 * ZL[idx] / math.sqrt(1 + alpha_B[idx])) - alpha_B[idx] / (1 + alpha_B[idx]))
              for idx in [0,1]]
        C2 = [2 * math.sqrt(1 + 0.27 * ZL[idx]) for idx in [0,1]]

        mu = [0 if ih2[idx] * r * leo[idx] * C1[idx] == 0 else
              zt[idx] * delta0 * rf[idx] * l / ih2[idx] / r / leo[idx] * (1 - C2[idx] / C1[idx]) / (1 - v / 2) for idx in [0, 1]]

        fE = np.array([C1[idx] * math.pow(math.pi, 2) * E / (12 * (1 - math.pow(v, 2))) * (math.pow(t / L, 2)) if L > 0
                       else 0.1 for idx in [0,1]])

        # should the check be added to see if fr can be equal fy if the checks are met (3.5.17 till 3.5.19)?
        # not clear if the checks are met, if fy should be used or fr. Looks like stocky_profile_factor is used for this
        
        fr = np.array(fT)
        lambda_2 = fr / fE
        # lambda_ = np.sqrt(lambda_2)

        fk = [0 if lambda_2[idx] == 0 else fr[idx] * (1 + mu[idx] + lambda_2[idx] - math.sqrt(math.pow(1 + mu[idx] + lambda_2[idx], 2) -
                                                                                 4 * lambda_2[idx])) / (2 * lambda_2[idx]) for idx in [0,1]]
        gammaM = self.curved_panel.material.mat_factor # LRFD
        fkd = [fk[idx] / gammaM for idx in [0,1]]
        pSd = np.array([0.75 * fk[idx] * t * rf[idx] * (1 + alpha[idx]) / (gammaM * math.pow(r, 2) * (1 - v / 2)) for idx in [0,1]])

        uf_refined = abs((self.load.pSd / 1e6)) / pSd

        return np.max([uf_cross_section, uf_moment_of_inertia, uf_refined], axis=0)


    def longitudinally_stiffened_shell(self, shell_curved_panel_results=None):
        '''
        Calculates the utilization factor for a longitudinally stiffened shell according to DNVGL-RP-C202.

        Notes:
        ------
        Not for lightly stiffened shells, as will behave basically as an unstiffened shell 
        and can be calculated as an unstiffened shell.
        '''
        results = dict()
        # assert to get rid of the type: ignore
        assert self.long_stf is not None, 'Longitudinally stiffened shell is not defined'
        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000

        s = self.curved_panel.s
        v = self.curved_panel.material.poisson
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6

        # We are in a longitudinally stiffened shell, thus the total length is the length of the shell
        # LH has no meaning here.
        L = self.tot_cyl_length * 1000 # type: ignore

        # same as for the unstiffened shell
        saSd = self.load.saSd / 1e6
        smSd = self.load.smSd / 1e6
        # Should this not be the sum of the abs values? There exists a point where these to add up.
        tSd = abs(self.load.tTSd / 1e6 + self.load.tQSd / 1e6) # MAYBE MAYBE NOT.
        # pSd = self.load.pSd / 1e6

        shSd = shell_curved_panel_results['shSd'] # type: ignore

        hw = self.long_stf.web_height * 1000
        tw = self.long_stf.web_th * 1000
        bf = self.long_stf.flange_width * 1000
        tf = self.long_stf.flange_th * 1000
        h = t + hw + tf

        logger.debug(f'h {h} hw {hw} tw {tw} b {bf} tf {tf} s {s} r {r} l {l} L {L} saSd {saSd} smSd {smSd} shSd {shSd}')
        
        # if lightly stiffened, it's in essence checked as an unstiffened cylinder.
        # This check is performed in get_utilization_factors

        #   Pnt. 3.3 Unstifffed curved panel
        data = shell_curved_panel_results if shell_curved_panel_results is not None else self.shell_curved_panel()

        # if a shell is longitudinally stiffened then why this check for fks?
        # if geometry == 1:
        #     fks = data['fks - Unstifffed circular cylinders']
        # else:
        #     fks = data['fks - Unstifffed curved panel']
        
        # If lightly stiffened, it's in essence checked as an unstiffened cylinder and caught get_utilization_factors
        # Else, it should checked according 3.6.2 which is 3.3.2 which is unstiffened panel.
        fks = data['fks - Unstiffened curved panel']

        sxSd = min([saSd + smSd, saSd - smSd])

        sjSd  = math.sqrt(math.pow(sxSd, 2) - sxSd * shSd + math.pow(shSd, 2) + 3 * math.pow(tSd, 2))

        se = fks * abs(sxSd) / sjSd / fy * s

        # Moment of inertia
        As = self.long_stf.As # in mm^2

        num_stf = math.floor(2 * math.pi * r / s)

        e = (hw * tw * (hw / 2) + bf * tf * (hw + tf / 2)) / (hw * tw + bf * tw)
        Istf = h * math.pow(tw, 3) / 12 + tf * math.pow(bf, 3) / 12

        dist_stf = r - t / 2 - e
        Istf_tot = 0
        angle = 0
        for _ in range(num_stf):
            Istf_tot += Istf + As * math.pow(dist_stf * math.cos(angle), 2)
            angle += 2 * math.pi / num_stf

        Iy = self.long_stf.get_moment_of_intertia(plate_thickness=self.curved_panel.thickness, plate_width=se/1000) *1000**4

        alpha = 12 * (1 - math.pow(v, 2)) * Iy / s / math.pow(t, 3)
        Zl = self.curved_panel.Zl # unitless

        logger.debug(f'Zl {Zl}, alpha {alpha}, Isef {Iy}, Se {se}, sjsd {sjSd}, sxsd {sxSd}, fks {fks}, As {As}')
        # Table 3-3results

        def table_3_3(chk):
            # ψ
            psi = {'Axial stress':(1 + alpha) / (1 + As / se / t),
                   'Torsion and shear stress': 5.34 + 1.82 * math.pow(l / s, 4/3) * math.pow(alpha, 1/3),
                   'Lateral Pressure': 2 * (1 + math.sqrt(1 + alpha))}
            # ξ
            epsilon = {'Axial stress': 0.702 * Zl,
                       'Torsion and shear stress': 0.856 * math.pow(Zl, 3/4),
                       'Lateral Pressure': 1.04 * math.sqrt(Zl)}
            # ρ
            rho = {'Axial stress': 0.5,
                   'Torsion and shear stress': 0.6,
                   'Lateral Pressure': 0.6}
            return psi[chk], epsilon[chk], rho[chk]

        vals = list()
        for chk in ['Axial stress', 'Torsion and shear stress','Lateral Pressure']:
            psi, epsilon, rho = table_3_3(chk=chk)
            C = 0 if psi == 0 else psi * math.sqrt(1 + math.pow(rho * epsilon / psi, 2))  # (3.4.2) (3.6.4)
            fE = C * ((math.pow(math.pi, 2) * E) / (12 * (1 - math.pow(v, 2)))) * math.pow(t / l,2)
            vals.append(fE)
            logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
        fEax, fEtors, fElat = vals
        logger.debug(f'Longitudinal stiffener: fEax {fEax} fEtors {fEtors} fElat {fElat}')

        shell_buckling_data = self.shell_buckling()
        data_col_buc = self.torsional_buckling(shell_buckling_data=shell_buckling_data, unstf_shell_data=shell_curved_panel_results)
        # Torsional Buckling can be excluded as possible failure if:
        # for flanged longitudinal stiffeners:
        fy_used = fy if data_col_buc['Long Stiff.'].lambda_T <= 0.6 else data_col_buc['Long Stiff.'].fT # 3.6.2
        # for flat bar stiffeners:
        if self.long_stf.type == 'FB' and hw <= 0.4 * tw * math.sqrt(E / fy):
            fy_used = fy
        else:
            fy_used = data_col_buc['Long Stiff.'].fT
        
        # Scale the stresses:
        # 3.6.3.1 'It is necessary to base the strength assessment on effective shell area.'
        saSd = saSd * (As + s * t) / (As + se * t) if As + se * t > 0 else 0
        smSd = smSd * (As + s * t) / (As + se * t) if As + se * t > 0 else 0

        sa0Sd = -saSd if saSd < 0 else 0
        sm0Sd = -smSd if smSd < 0 else 0
        sh0Sd = -shSd if shSd < 0 else 0
        logger.debug(f'fy_used {fy_used}, sasd {saSd}, shsd {shSd}, tsd {tSd}')
        
        # Why distinct between panels and shells?
        # Looks like there was at some point the idea to have a stress and a force option, 
        # from which this is a reminiscence, but this did not get implemented.
        # if we are in this code, we know it's a longitudinally stiffened shell
        # we also know it's not lightly stiffened, as that would be caught in get_utilization_factors
        sjSd_panels = math.sqrt(math.pow(saSd + smSd, 2) - (saSd + smSd) * shSd + math.pow(shSd, 2)+ 3 * math.pow(tSd, 2))

        worst_axial_comb = min(saSd - smSd, saSd + smSd)
        sjSd_shells = math.sqrt(math.pow(worst_axial_comb, 2) - worst_axial_comb * shSd + math.pow(shSd, 2) + 3 * math.pow(tSd, 2))
        sxSd_used = worst_axial_comb
        results['sxSd_used'] = sxSd_used
        sjSd_used = sjSd_panels if self._geometry in [ShellType.UNSTIFFENED_PANEL, ShellType.RING_STIFFENED_SHELL] else sjSd_shells
        results['sjSd_used'] = sjSd_used

        lambda_s2_panel = fy_used / sjSd_panels * ((sa0Sd + sm0Sd) / fEax + sh0Sd / fElat + tSd / fEtors) if \
            sjSd_panels * fEax * fEtors * fElat > 0 else 0
        lambda_s2_shell = fy_used / sjSd_shells * (max(0, -worst_axial_comb) / fEax + sh0Sd / fElat + tSd / fEtors) if \
            sjSd_shells * fEax * fEtors * fElat > 0 else 0

        # what is shell_type?
        shell_type = 2 if self._geometry in [1,5] else 1
        lambda_s = math.sqrt(lambda_s2_panel) if shell_type == 1 else math.sqrt(lambda_s2_shell)

        fks = fy_used / math.sqrt(1 + math.pow(lambda_s, 4))
        logger.debug(f'tsd {tSd}, sasd {saSd}, sjsd panels {sjSd_panels}, fy_used {fy_used}, lambda_T {data_col_buc["Long Stiff."].lambda_T}')
        if lambda_s < 0.5:
            gammaM = self.curved_panel.material.mat_factor
        else:
            # why is gammaM dependanton the user provided mat_factor?
            if self.curved_panel.material.mat_factor == 1.1:
                if lambda_s > 1:
                    gammaM = 1.4
                else:
                    # is this 0.8 or should it be 0.85?
                    gammaM = 0.8 + 0.6 * lambda_s
            elif self.curved_panel.material.mat_factor == 1.15:
                if lambda_s > 1:
                    gammaM = 1.45
                else:
                    gammaM = 0.85 + 0.6 * lambda_s
            else:
                if lambda_s > 1:
                    gammaM = 1.45 * (self.curved_panel.material.mat_factor / 1.15)
                else:
                    gammaM = 0.85 + 0.6 * lambda_s * (self.curved_panel.material.mat_factor / 1.15)

        if self.uls_or_als == 'ALS':
            gammaM = gammaM / self.curved_panel.material.mat_factor

        # Design buckling strength:
        fksd = fks / gammaM
        uf = sjSd / fksd
        
        logger.debug(f'fksd {fksd}, fks {fks}, gammaM {gammaM}, lambda_s {lambda_s}, lambda_s^2 panel {lambda_s2_panel}, \
                     sjSd {sjSd_used}, worst_axial_comb {worst_axial_comb}, sm0sd {sm0Sd}')
        
        results['gammaM - Longitudinal stiffener'] = gammaM
        results['fksd - Longitudinal stiffener'] = fksd
        results['UF - Longitudinal stiffener'] = uf

        return results


    def column_buckling(self, unstf_shell_data):
        results = dict()

        E = self.curved_panel.material.young / 1e6
        v = self.curved_panel.material.poisson
        G = E / 2 / (1 + v)
        
        # get correct s
        # curved_panel.s holds the spacing of the panel, also for longitudinally stiffened panels
        # could update based on self.geometry
        s = max([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
            self.curved_panel.s
        t = self.curved_panel.thickness * 1000
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6

        # for column buckling, only total cylinder length is used
        # tot_cyl_length is not none as column buckling is not called for unstiffened panel
        Lc = self.tot_cyl_length * 1000 # type: ignore

        # same as for the unstiffened shell
        saSd = self.load.saSd / 1e6
        smSd = self.load.smSd / 1e6
        # Should this not be the sum of the abs values? There exists a point where these to add up.
        tSd = abs(self.load.tTSd / 1e6 + self.load.tQSd / 1e6) # MAYBE MAYBE NOT.
        pSd = self.load.pSd / 1e6

        # same as for the unstiffened shell
        saSd = self.load.saSd / 1e6
        smSd = self.load.smSd / 1e6
        pSd = self.load.pSd / 1e6
        shSd = unstf_shell_data['shSd'] # pSd * r / t

        hw = 0 if self.long_stf is None else self.long_stf.web_height * 1000
        tw = 0 if self.long_stf is None else self.long_stf.web_th * 1000
        b = 0 if self.long_stf is None else self.long_stf.flange_width * 1000
        tf = 0 if self.long_stf is None else self.long_stf.flange_th * 1000
        h = t + hw + tf
        logger.debug(f't {t}, h {h}, hw {hw}, tw {tw}, b {b}, tf {tf}, s {s}, r {r}, Lc {Lc}, saSd {saSd}, smSd {smSd}, tSd {tSd}, shSd {shSd}')
        
        # Moment of inertia longitudinal stiffener
        As = hw * tw + b * tf  # checked
        num_stf = math.floor(2 * math.pi * r / s)
        Atot = As * num_stf + 2 * math.pi * r * t

        if tw == 0: # if no web, then no stiffener
            e = 0
        else:
            e = (hw * tw * (hw/2) + b * tf * (hw + tf / 2)) / (hw * tw + b * tw)
        Istf = h*math.pow(tw,3)/12 + tf*math.pow(b, 3)/12

        dist_stf = r - t / 2 - e
        Istf_tot = 0.0
        angle = 0.0
        for _ in range(num_stf):
            Istf_tot += Istf + As*math.pow(dist_stf*math.cos(angle),2)
            angle += 2*math.pi/num_stf

        Ishell = (math.pi/4) * ( math.pow(r+t/2,4) - math.pow(r-t/2,4))
        Itot = Ishell + Istf_tot # Checked
        iC = math.sqrt(Itot / Atot)

        k_factor = self.k_factor
        col_test = math.pow(k_factor * Lc / iC, 2) >= 2.5 * E / fy # 3.8.1

        results['Need to check column buckling'] = col_test
        if not col_test:
            results['Column stability check'] = 'Not required'
            results['Column stability UF'] = 'N/A'
            logger.info('Column buckling not required to be checked')
            max_Lc = math.sqrt(2.5 * E / fy * iC**2 / self.k_factor**2) # type: ignore
            logger.debug(f'Length limit for column buckling [m]: {max_Lc / 1000}')
            return results

        # # Sec. 3.8.2   Column buckling strength:
        # fEa = unstf_shell_data['fEax - Unstiffened circular cylinder']
        # fEh = unstf_shell_data['fEh - Unstiffened circular cylinder - Psi=4']

        # 3.3.2 if for:
        #  - ShellType.UNSTIFFENED_PANEL = 3
        #  - ShellType.LONGITUDINAL_STIFFENED_SHELL = 6
        #  - ShellType.ORTHOGONALLY_STIFFENED_SHELL = 7
        # 3.4.2 is for:
        #  - ShellType.UNSTIFFENED_CYCLINDER = 4
        #  - ShellType.RING_STIFFENED_SHELL = 5
        if self._geometry in [ShellType.LONGITUDINAL_STIFFENED_SHELL, ShellType.ORTHOGONALLY_STIFFENED_SHELL]:
            fak = unstf_shell_data['max axial stress - 3.3 Unstiffened curved panel']
            gammaM = unstf_shell_data['gammaM - Unstiffened curved panel']
        elif self._geometry == ShellType.RING_STIFFENED_SHELL:
            fEa = unstf_shell_data['fEax - Unstiffened circular cylinder']
            fEh = unstf_shell_data['fEh - Unstiffened circular cylinder - Psi=4']
            fak = unstf_shell_data['max axial stress - 3.4.2 Shell buckling']
            gammaM = unstf_shell_data['gammaM - Unstiffened circular cylinder']
        elif self._geometry == ShellType.UNSTIFFENED_CYCLINDER:
            fEa = unstf_shell_data['fEax - Unstiffened circular cylinder']
            fEh = unstf_shell_data['fEh - Unstiffened circular cylinder - Psi=4']
            a = 1 + math.pow(fy, 2) / math.pow(fEa, 2) # 3.8.9
            b = ((2 * math.pow(fy, 2) / (fEa * fEh)) - 1) * shSd # 3.8.10
            c = math.pow(shSd, 2) + math.pow(fy, 2) * math.pow(shSd, 2) / math.pow(fEh, 2) - math.pow(fy, 2) # 3.8.11
            try:
                fak = (b + math.sqrt(math.pow(b, 2) - 4 * a * c)) / (2 * a) # 3.8.8
            except:
                logger.warning(f'Column buckling: Error calulating fak for the special case of unstiffened shell, setting fak as unstiffened circular cylinder')
                fak = unstf_shell_data['max axial stress - 3.4.2 Shell buckling']
            gammaM = unstf_shell_data['gammaM - Unstiffened circular cylinder']
        else:
            # note that ShellType.UNSTIFFENED_PANEL = 3 will raise this error.
            # as column buckling for an unstiffened panel does not make sense
            raise ValueError(f'Geometry {self._geometry} not implemented')

        
        # I believe this needed correction?
        # fE = 0.0001 if Lc * k_factor == 0 else E * math.sqrt(math.pi*iC  / (Lc * k_factor))
        fE = 0.0001 if Lc * k_factor == 0 else E * math.pow(math.pi * iC / Lc / k_factor, 2)
        Lambda_ = 0 if fE == 0 else math.sqrt(fak / fE) # 3.8.7
        # 3.8.5 and 3.8.6
        fkc = (1 - 0.28 * math.pow(Lambda_, 2)) * fak if Lambda_ <= 1.34 else 0.9 * fak / math.pow(Lambda_, 2)

        fakd = fak / gammaM
        fkcd = fkc / gammaM
        logger.debug(f'fakd {fakd}, fkcd {fkcd}, fak {fak}, fkc {fkc}, gammaM {gammaM}, fE {fE}, Lambda_ {Lambda_}')
        
        if fakd <= 0 or fkcd <= 0:
            logger.error(f'fakd {fakd}, fkcd {fkcd}')
            raise ValueError('fakd or fkcd is zero or negative')
        else:
            sa0sd = -saSd if saSd < 0 else 0
            stab_uf = sa0sd / fkcd + (abs(smSd) / (1 - sa0sd / fE)) / fakd
            stab_chk = stab_uf <= 1

        results['Column stability check'] = stab_chk
        results['Column stability UF'] = stab_uf

        return results


    def local_stiffener_buckling(self, shell_buckling_data):
        E = self.curved_panel.material.young / 1e6
        fy = self.curved_panel.material.strength / 1e6
        
        # 3.10 Local bucling of longitudinal stiffeners and ring/frame stiffeners
        # 3.10.1 and 3.10.6
        stf_req_h = list()
        for stf in [self.long_stf, self.ring_stf, self.ring_frame]:
            if stf is None:
                stf_req_h.append(np.nan)
            else:
                stf_req_h.append(0.4 * stf.tw * math.sqrt(E / fy) if stf.type == 'FB'
                                 else 1.35 * stf.tw * math.sqrt(E / fy))

        stf_req_h = np.array(stf_req_h)

        chk1 = stf_req_h > np.array([np.nan if self.long_stf is None else self.long_stf.hw,
                                  np.nan if self.ring_stf is None else self.ring_stf.hw,
                                  np.nan if self.ring_frame is None else self.ring_frame.hw])
        chk1 = [np.nan if np.isnan(val) else chk1[idx] for idx, val in enumerate(stf_req_h)]
        logger.debug(f"chk1 {chk1}")

        # 3.10.2 and 3.10.7
        stf_req_b = list()
        for stf in [self.long_stf, self.ring_stf, self.ring_frame]:
            if stf is None:
                stf_req_b.append(np.nan)
            else:
                stf_req_b.append(np.nan if stf.type == 'FB' else 0.4 * stf.tf * math.sqrt(E / fy))

        bf = list()
        for stf in [self.long_stf, self.ring_stf, self.ring_frame]:
            if stf is None:
                bf.append(np.nan)
            elif stf.type == 'FB':
                bf.append(stf.b)
            elif stf.type == 'T':
                bf.append((stf.b - stf.tw) / 2)
            else:
                bf.append(stf.b - stf.tw)
        bf = np.array(bf)

        chk2 = stf_req_b > bf
        chk2 = [np.nan if np.isnan(val) else chk2[idx] for idx, val in enumerate(stf_req_b)]
        logger.debug(f"chk2 {chk2}")

        # 3.10.4
        hw_div_tw = list()
        for stf in [self.ring_stf, self.ring_frame]:
            if stf is None:
                hw_div_tw.append(np.nan)
            else:
                hw_div_tw.append(stf.hw / stf.tw)
        hw_div_tw = np.array(hw_div_tw)


        req_hw_div_tw = list()
        for idx, stf in enumerate([self.ring_stf, self.ring_frame]):
            if stf is None:
                req_hw_div_tw.append(np.nan)
            else:
                logger.debug(f"rf {shell_buckling_data['parameters'][idx][4]}, tw {stf.tw}, hw {stf.hw}, E {E}, b {stf.b}, tf {stf.tf}, fy {fy}")
                to_append = np.nan if stf.b * stf.tf == 0 else 2/3 * math.sqrt(shell_buckling_data['parameters'][idx][4]
                                                                               * (stf.tw*stf.hw) * E /
                                                                               (stf.hw * stf.b * stf.tf * fy))
                req_hw_div_tw.append(to_append)
        req_hw_div_tw = np.array(req_hw_div_tw)

        chk3 = hw_div_tw < req_hw_div_tw
        chk3 = [np.nan if np.isnan(val) else chk3[idx] for idx, val in enumerate(req_hw_div_tw)]
        logger.debug(f"chk3 {chk3}")

        # 3.10.5
        # note that h is web height in these formulas
        ef_div_tw = list()
        for stf in [self.ring_stf, self.ring_frame]:
            if stf is None:
                ef_div_tw.append(np.nan)
            else:
                ef_div_tw.append(stf.get_flange_eccentricity())
        ef_div_tw = np.array(ef_div_tw)

        ef_div_tw_req = list()
        for idx, stf in enumerate([self.ring_stf, self.ring_frame]):
            if stf is None:
                ef_div_tw_req.append(np.nan)
            else:
                ef_div_tw_req.append(np.nan if stf.b * stf.tf == 0 else
                             1/3 * shell_buckling_data['parameters'][idx][4] * stf.hw * stf.tw / stf.hw / (stf.b * stf.tf))
        ef_div_tw_req = np.array(ef_div_tw_req)

        chk4 = ef_div_tw < ef_div_tw_req
        chk4 = [np.nan if np.isnan(val) else chk4[idx] for idx, val in enumerate(ef_div_tw_req)]
        logger.debug(f"chk4 {chk4}")
        
        return chk1, chk2, chk3, chk4


    def torsional_buckling(self, shell_buckling_data, unstf_shell_data) -> Dict[str, TorsionalProperties]:
        E = self.curved_panel.material.young / 1e6
        v = self.curved_panel.material.poisson
        G = E / 2 / (1 + v)
        fy = self.curved_panel.material.strength / 1e6

        t = self.curved_panel.thickness * 1000
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000

        chk1, chk2, chk3, chk4 = self.local_stiffener_buckling(shell_buckling_data)

        # Torsional buckling parameters
        idx = 1
        param_map = {'Ring Stiff.': 0, 'Ring Frame': 1}
        fT_dict = dict()
        for key, stf in {'Long Stiff.': self.long_stf, 'Ring Stiff.': self.ring_stf,
                         'Ring Frame': self.ring_frame}.items():
            if stf is None:
                idx += 1
                continue
            
            # 3.3.2 if for:
            #  - ShellType.UNSTIFFENED_PANEL = 3
            #  - ShellType.LONGITUDINAL_STIFFENED_SHELL = 6
            #  - ShellType.ORTHOGONALLY_STIFFENED_SHELL = 7
            # 3.4.2 is for:
            #  - ShellType.UNSTIFFENED_CYCLINDER = 4
            #  - ShellType.RING_STIFFENED_SHELL = 5
            if self._geometry in [3, 6, 7]:
                fksd = unstf_shell_data['fksd - Unstiffened curved panel']
                gammaM = unstf_shell_data['gammaM - Unstiffened curved panel']
            elif self._geometry in [4, 5]:
                fksd = unstf_shell_data['fksd - Unstiffened circular cylinder'] 
                gammaM = unstf_shell_data['gammaM - Unstiffened circular cylinder']
            else:
                raise ValueError(f'Geometry {self._geometry} not implemented')

            sjSd = shell_buckling_data['sjSd'][idx-1]

            fks = fksd * gammaM
            eta = sjSd / fks
            hw = stf.hw
            tw = stf.tw

            if key == 'Long Stiff.':
                s_or_le0 = self.curved_panel.s
                lT = l
            elif key in ['Ring Stiff.', 'Ring Frame']:
                s_or_le0 = shell_buckling_data['parameters'][param_map[key]][2]
                lT = math.pi * math.sqrt(r * hw)
            else:
                raise ValueError(f'Key {key} not implemented')

            # 3.9.10
            # If sjSd > fks, then eta > 1 and sqrt becomes negative.
            C = hw / s_or_le0 * math.pow(t / tw, 3) * math.sqrt(1 - min([1, eta])) if s_or_le0 * tw>0 else 0
            beta = (3 * C + 0.2) / (C + 0.2) 

            hs, It, Iz, Ipo, Iy = shell_buckling_data['cross section data'][idx - 1]
            
            if stf.type in ["L", "T"] and chk3[idx-1] and chk4[idx-1]:
                # 3.9.6 and 3.9.7
                logger.debug(f'Local buckling satisfied for {key}. Using special case for L and T stiffeners')
                Af = stf.tf * stf.b
                Aw = stf.hw * stf.tw
                ef = stf.get_flange_eccentricity() * 1000
                Iz = Af * math.pow(stf.b, 2) / 12 + math.pow(ef, 2) * Af / (1 + Af / Aw)
                fET = beta * (Aw + math.pow(stf.tf / stf.tw, 2) * Af) / (Aw + 3 * Af) * G * math.pow(stf.tw / hw,2) \
                    + math.pow(math.pi, 2) * E * Iz / ((Aw / 3 + Af) * math.pow(lT, 2))
            elif stf.type == 'FB':
                logger.debug(f'Calculating {key} as a FB stiffener')
                if key in ['Ring Stiff.', 'Ring Frame']:
                    # 3.9.8
                    fET = (beta + 0.2 * stf.hw / r) * G * math.pow(tw / hw, 2)
                else:
                    # 3.9.9
                    fET = (beta + 2 * math.pow(stf.hw / lT, 2)) * G * math.pow(tw / hw, 2)
            else:
                # the general case 3.9.5
                fET = beta * G * It / Ipo + math.pow(math.pi, 2) * E * math.pow(hs, 2) * Iz / (Ipo * math.pow(lT, 2))

            lambda_T = math.sqrt(fy / fET)

            mu = 0.35 * (lambda_T - 0.6)
            fT = (1 + mu + math.pow(lambda_T, 2) - math.sqrt(math.pow(1 + mu + math.pow(lambda_T, 2), 2) - 4 * math.pow(lambda_T, 2)))\
                 / (2 * math.pow(lambda_T, 2)) * fy if lambda_T > 0.6 else fy
            
            # store fET, lambda_T and fT
            fT_dict[key] = TorsionalProperties(fET=fET, lambda_T=lambda_T, fT=fT)

        return fT_dict


    def get_x_opt(self):
        '''
        shell       (0.02, 2.5, 5, 5, 10, nan, nan, nan),
        long        (0.875, nan, 0.3, 0.01, 0.1, 0.01, nan, stiffener_type)),
        ring        (nan, nan, 0.3, 0.01, 0.1, 0.01, nan, stiffener_type)),
        ring        (nan, nan, 0.7, 0.02, 0.2, 0.02, nan, stiffener_type))] 
        
        (self._spacing, self._plate_th, self._web_height, self._web_th, self._flange_width,
                self._flange_th, self._span, self._girder_lg, self._stiffener_type)
        '''
        shell = [self._Shell.thk, self._Shell.radius, self._Shell.dist_between_rings, self._Shell.length_of_shell, 
                 self._Shell.tot_cyl_length, np.nan, np.nan, np.nan]
        if self._LongStf is not None:
            long = [self._LongStf.spacing/1000, np.nan, self._LongStf.hw/1000, self._LongStf.tw/1000, self._LongStf.b/1000, 
                    self._LongStf.tf/1000, np.nan, self._LongStf.stiffener_type]
        else:
            long = [0 for dummy in range(8)]
        
        if self._RingStf is not None:
            ring_stf = [self._RingStf.s/1000, np.nan, self._RingStf.hw/1000, self._RingStf.tw/1000, self._RingStf.b/1000, 
                    self._RingStf.tf/1000, np.nan, self._RingStf.stiffener_type]
        else:
            ring_stf = [0 for dummy in range(8)]
        
        if self._RingFrame is not None:
            ring_fr = [self._RingFrame.s/1000, np.nan, self._RingFrame.hw/1000, self._RingFrame.tw/1000, self._RingFrame.b/1000, 
                    self._RingFrame.tf/1000, np.nan, self._RingFrame.stiffener_type]
        else:
            ring_fr = [0 for dummy in range(8)]

        return [shell, long, ring_stf, ring_fr]
