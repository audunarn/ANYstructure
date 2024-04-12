import math
import logging
from typing import Optional, List, Dict
from enum import IntEnum

from pydantic import BaseModel, model_validator, field_validator, PrivateAttr
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


class ShellBucklingResult(BaseModel):
    fEax: float = 0
    fEshear: float = 0
    fEcirc: float = 0
    fEbend: float = 0
    fEtors: float = 0
    fElat: float = 0
    fEhyd: float = 0


class StiffenedShellType(IntEnum):
    # following the numbering in the standard
    UNSTIFFENED_PANEL = 3 # 3.3 Elastic buckling strength of unstiffened curved panels
    UNSTIFFENED_CYCLINDER = 4 # 3.4 Elastic buckling strength of unstiffened circular cylinders
    RING_STIFFENED_SHELL = 5 # 3.5 Ring stiffened shells
    LONGITUDINAL_STIFFENED_SHELL = 6 # 3.6 Longitudinal stiffened shells
    ORTHOGONALLY_STIFFENED_SHELL = 7 # 3.7 Orthogonally stiffened shells


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
    shSd_add: float = 0 # additional hoop stress

    # this is a pydantic feature that allows us to run some code after the initialization of the class
    def __post_init__(self):
        # tQsd is the shear stress and always positive
        self.tQSd = abs(self.tQSd)


    # chech that shear is positive
    # should always pass since we are taking the abs on ititialization
    @field_validator('tQsd')
    def check_shear(cls, value):
        if value < 0:
            raise ValueError('Shear stress must be positive')
        return value


class StiffenerProperties(BaseModel):
    '''
    Class holding the stiffener properties, used throughout the calculations.
    This avoids passing the properties around as a dictionary
    '''
    alpha: float = 0
    beta: float = 0
    le0: float = 0
    eta: float = 0
    rf: float = 0
    r0: float = 0
    zt: float = 0
    hs: float = 0
    It: float = 0
    Iz: float = 0
    Ipo: float = 0
    Iy: float = 0


class ShellDerivedStressValues(BaseModel):
    '''
    Class representing derived stress values used in the shell buckling calculations.
    This class is used for returning stress values instead of a tuple.

    Attributes:
        sxsd (float): The value of sxsd.
        tSd (float): The value of tSd.
        shsd (float): The value of shsd.
        shRsd (float): The value of shsd.
        sjsd (float): The value of sjsd.
    '''
    sxSd: float = 0
    tSd: float = 0 
    shSd: float = 0
    shRSd: float = 0
    sjSd: float = 0
    sa0Sd: float = 0
    sm0Sd: float = 0
    sh0Sd: float = 0


class CylindricalShell(BaseModel):
    '''
    Buckling of cylinders and curved plates.
    '''
    curved_panel: CurvedPanel
    long_stf: Optional[Stiffener] = None
    # long_stf_spacing: Optional[float] # should this not be taken from 's' in the panel?
    ring_stf: Optional[Stiffener] = None
    # ring_stf_spacing: Optional[float] # should this not be taken from 'l' in the panel?
    ring_frame: Optional[Stiffener] = None
    ring_frame_spacing: Optional[float] # L: distance between effective supports (Figure 3-1)
    load: ShellStressAndPressure
    geometry: StiffenedShellType = PrivateAttr(default=None) # It is determined from the given parameters
    tot_cyl_length: Optional[float] = None
    k_factor: Optional[float] = None
    delta0: Optional[float] = None # THIS IS THE VALUE INCLUDING RADIUS in line with (3.5.26)
    fab_method_ring_stf: Optional[str] = 'rolled' # or 'welded' rolled is conservative
    fab_method_ring_frame: Optional[str] = 'rolled' # or 'welded' rolled is conservative
    ring_stiffener_excluded: bool # default is conservative
    ring_frame_excluded: bool # default is conservative
    end_cap_pressure_included: bool = False # default is conservative
    uls_or_als: str = 'ULS' # or 'ALS' ULS is conservative

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
    # 4. Check possible values of rolled/welded for ring stiffener and ring frame and set to lower case
    # 5. Check that uls_or_als is either ULS or ALS and set to upper case

    # Derive the StiffenedShellType from the given parameters.
    def __post_init__(self):
        user_type = self.geometry
        if self.long_stf is None and self.ring_stf is None and self.ring_frame is None:
            # providing total cylinder length will determine if it is an unstiffened panel or cylinder
            if self.tot_cyl_length is None:
                self.geometry = StiffenedShellType.UNSTIFFENED_PANEL
                # If panel.l / panel.s < 1 it is calculated as an unstiffened cylinder
                if self.curved_panel.l / self.curved_panel.s < 1:
                    self.geometry = StiffenedShellType.UNSTIFFENED_CYCLINDER
                    self.tot_cyl_length = self.curved_panel.l
            else:
                self.geometry = StiffenedShellType.UNSTIFFENED_CYCLINDER
        elif self.long_stf and self.ring_stf is None and self.ring_frame is None:
            # only longitudinal stiffener defined
            self.geometry = StiffenedShellType.LONGITUDINAL_STIFFENED_SHELL
        elif self.long_stf is None and (self.ring_stf or self.ring_frame):
            # no longitudinal stiffener but ring stiffener or ring frame
            self.geometry = StiffenedShellType.RING_STIFFENED_SHELL
        elif self.long_stf and (self.ring_stf or self.ring_frame):
            # both longitudinal stiffener and ring stiffener or ring frame
            self.geometry = StiffenedShellType.ORTHOGONALLY_STIFFENED_SHELL
        else:
            raise ValueError('Could not determine geometry from the given parameters')
        
        if user_type != self.geometry:
            raise ValueError(f'User provided geometry {user_type} does not match the derived geometry {self.geometry}')

    # @model_validator(mode='after')
    # def checks_if_long_stf_given(self):
    #     if self.long_stf:
    #         if self.long_stf_spacing is None:
    #             raise ValueError('If long_stf is given, long_stf_spacing must also be given')
    #         if self.tot_cyl_length is None:
    #             raise ValueError('If long_stf is given, tot_cyl_length must also be given')
            # if self.k_factor is None:
            #     raise ValueError('If ring_stf is given, k_factor must also be given')
    #         if self.curved_panel.s != self.long_stf_spacing:
    #             raise ValueError('Value s in spacing of the curved_panel and long_stf_spacing must match')
    #     return self

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

    @field_validator('delta0')
    def check_delta0(cls, value):
        if value is None:
            return 0.005 * cls.curved_panel.radius
        if value < 0:
            raise ValueError('delta0 must be positive')
        return value


    def __str__(self):
        '''
        Returning all properties.
        '''

        long_string = 'N/A' if self.long_stf is None else self.long_stf.get_beam_string()
        ring_string = 'N/A' if self.ring_stf is None else self.ring_stf.get_beam_string()
        frame_string = 'N/A' if self.ring_frame is None else self.ring_frame.get_beam_string()
        L_string = 'N/A' if self.ring_frame_spacing is None else self.ring_frame_spacing * 1000
        Cyl_length_string = 'N/A' if self.tot_cyl_length is None else self.tot_cyl_length * 1000
        s = self.curved_panel.s * 1000

        return \
            str(
            '\n Cylinder radius:               ' + str(round(self.curved_panel.radius, 3)) + ' meters' +
            '\n Cylinder thickness:            ' + str(self.curved_panel.thickness * 1000)+' mm'+
            '\n Distance between rings, l:     ' + str(self.curved_panel.l * 1000)+' mm'+
            '\n Distance between frames, L:    ' + str(L_string)+' mm'+
            '\n Total cylinder lenght:         ' + str(Cyl_length_string)+' mm'+
            '\n Eff. Buckling length factor:   ' + str(self.k_factor)+
            '\n Material yield:                ' + str(self.curved_panel.material.strength / 1e6)+' MPa'+
            '\n Spacing/panel circ., s:        ' + str(s) + '  mm' +
            '\n Longitudinal stiffeners:       ' + long_string +
            '\n Ring stiffeners                ' + ring_string +
            '\n Ring frames/girders:           ' + frame_string +
            '\n Design axial stress/force:     ' + str(self.load.saSd / 1e6)+' MPa'+
            '\n Design bending stress/moment:  ' + str(self.load.smSd / 1e6)+' MPa'+
            '\n Design torsional stress/moment: ' + str(self.load.tTSd / 1e6)+' MPa'+
            '\n Design shear stress/force:     ' + str(self.load.tQSd / 1e6)+' MPa'+
            '\n Design lateral pressure        ' + str(self.load.pSd / 1e6)+' MPa'+
            '\n Additional hoop stress         ' + str(self.load.shSd_add / 1e6)+' MPa')


    def elastic_buckling_strength(self, C, s_or_l):
        """
        Calculate the elastic buckling strength of a curved panel.

        Parameters
        ----------
        C : float
            A constant factor that depends on the specific conditions of the panel.
        s_or_l : float
            The characteristic length of the panel (either short or long dimension).

        Returns
        -------
        float
            The elastic buckling strength of the panel.

        Notes
        -----
        The calculation is based on the material properties (Young's modulus and Poisson's ratio),
        the thickness of the panel, and the provided constant factor and characteristic length.
        """
        E = self.curved_panel.material.young / 1e6
        v = self.curved_panel.material.poisson
        t = self.curved_panel.thickness * 1000
        
        # (3.3.1) (3.4.1) (3.6.3)
        f_E = C * (math.pow(math.pi, 2) * E / (12 * (1 - math.pow(v, 2)))) * math.pow(t / s_or_l, 2)
        return f_E


    def reduced_buckling_coefficient(self, psi, epsilon, rho):
        """
        Calculate the reduced buckling coefficient of a curved panel,
        for a given set of parameters which correspond to a specific stress component.

        Parameters
        ----------
        psi : float
            The factor from the table for the given stress component.
        epsilon : float
            The factor from the table for the given stress component.
        rho : float
            The factor from the table for the given stress component.

        Returns
        -------
        float
            The reduced buckling coefficient of the panel for the given stress component
        """
        C = psi * math.sqrt(1 + math.pow(rho * epsilon / psi, 2))  # (3.3.2) (3.4.2) (3.6.4)
        return C
    

    def get_utilization_factors(self, optimizing = False, empty_result_dict = False):
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
        unstiffend_shell, column_buckling_data = None, None
        
        # UF for unstiffened shell
        unstiffend_shell = self.unstiffened_shell(shell_data=data_shell_buckling)

        s = self.panel_spacing * 1000 if self.long_stf is None else self.long_stf.spacing

        if any([self.geometry in [1, 5], s > self.curved_panel.s * 1000]):
            uf_unstf_shell = unstiffend_shell['UF unstiffened circular cylinder']
            results['Unstiffened shell'] = uf_unstf_shell
        else:
            uf_unstf_shell = unstiffend_shell['UF unstiffened curved panel']
            results['Unstiffened shell'] = uf_unstf_shell

        if optimizing:
            if uf_unstf_shell > 1:
                return False, 'UF unstiffened', results

        # UF for longitudinal stiffened shell
        if self.geometry in [3,4,7,8]:
            if self.long_stf is not None:
                column_buckling_data= self.column_buckling(unstf_shell_data=unstiffend_shell,
                                                          shell_bukcling_data=data_shell_buckling)
                long_stf_shell = self.longitudinally_stiffened_shell(column_buckling_data=column_buckling_data,
                                                                     unstiffened_shell=unstiffend_shell)

                results['Column stability check'] = column_buckling_data['Column stability check']
                results['Column stability UF']  = column_buckling_data['Column stability UF']
                results['Need to check column buckling'] = column_buckling_data['Need to check column buckling']
                results['Stiffener check'] = column_buckling_data['stiffener check']
                results['Stiffener check detailed'] = column_buckling_data['stiffener check detailed']
                if self.geometry in [3,4,7,8] and long_stf_shell['fksd'] > 0:
                    results['Longitudinal stiffened shell'] = long_stf_shell['sjsd_used'] / long_stf_shell['fksd'] \
                        if self.geometry in [3,4,7,8] else 0

                if optimizing:
                    if not results['Column stability check']:
                        return False, 'Column stability', results
                    elif False in results['Stiffener check'].values():
                        return False, 'Stiffener check', results
                    elif results['Longitudinal stiffened shell'] > 1:
                        return False, 'UF longitudinal stiffeners', results

        if self.geometry in [5,6,7,8]:
            # UF for panel ring buckling
            ring_stf_shell = None
            if self.ring_stf is not None:
                column_buckling_data = column_buckling_data if column_buckling_data is not None  \
                    else self.column_buckling( unstf_shell_data=unstiffend_shell,
                                               shell_bukcling_data=data_shell_buckling)
                ring_stf_shell = self.ring_stiffened_shell(data_shell_buckling=data_shell_buckling,
                                                           column_buckling_data=column_buckling_data)
                results['Column stability check'] = column_buckling_data['Column stability check']
                results['Column stability UF'] = column_buckling_data['Column stability UF']
                results['Need to check column buckling'] = column_buckling_data['Need to check column buckling']
                results['Stiffener check'] = column_buckling_data['stiffener check']
                results['Stiffener check detailed'] = column_buckling_data['stiffener check detailed']
                results['Ring stiffened shell'] = ring_stf_shell[0]



                if optimizing:
                    if not results['Column stability check']:
                        return False, 'Column stability', results
                    elif False in results['Stiffener check'].values():
                        return False, 'Stiffener check', results
                    elif results['Ring stiffened shell'] > 1:
                        return False, 'UF ring stiffeners', results

        # UF for ring frame
        if self.geometry in [5, 6, 7, 8]:
            if self.ring_frame is not None:
                column_buckling_data = column_buckling_data if column_buckling_data is not None  \
                    else self.column_buckling( unstf_shell_data=unstiffend_shell,
                                               shell_bukcling_data=data_shell_buckling)
                ring_stf_shell = ring_stf_shell if ring_stf_shell is not None else \
                    self.ring_stiffened_shell(data_shell_buckling=data_shell_buckling,
                                              column_buckling_data=column_buckling_data)
                results['Column stability check'] = column_buckling_data['Column stability check']
                results['Column stability UF'] = column_buckling_data['Column stability UF']
                results['Need to check column buckling'] = column_buckling_data['Need to check column buckling']
                results['Stiffener check'] = column_buckling_data['stiffener check']
                results['Stiffener check detailed'] = column_buckling_data['stiffener check detailed']
                results['Heavy ring frame'] = ring_stf_shell[1]

                if optimizing:
                    if not results['Column stability check']:
                        return False, 'Column stability', results
                    elif False in results['Stiffener check'].values():
                        return False, 'Stiffener check', results
                    elif results['Heavy ring frame'] > 1:
                        return False, 'UF ring frame', results

        if optimizing:
            return True, 'Check OK', results

        # print('Results for geometry', self._geometry)
        # print('UF',uf_unstf_shell, uf_long_stf, uf_ring_stf, uf_ring_frame)
        # print('Stiffeners', stiffener_check)

        return results


    def get_shell_stiffener_properties(self, stf_type: str) -> StiffenerProperties:
        '''
        Calculate the properties of the ring and frame stiffener.

        Parameters
        ----------
        stf_type : str
            The type of stiffener to calculate the properties for. Can be 'long', 'ring' or 'frame'.
        '''
        if not stf_type.lower().strip() in ['long', 'ring', 'frame']:
            raise ValueError('stf_type must be either "long", "ring" or "frame"')
        
        # initialize the properties at 0
        stiff_properties = StiffenerProperties()
        # long_stiff_properties = StiffenerProperties()
        # ring_stiff_properties = StiffenerProperties()
        # ring_frame_properties = StiffenerProperties()

        stiffener: Stiffener = None
        if stf_type.lower().strip() == 'long':
            assert self.long_stf is not None, 'Longitudinal stiffener not defined'
            stiffener = self.long_stf
        elif stf_type.lower().strip() == 'ring':
            assert self.ring_stf is not None, 'Ring stiffener not defined'
            stiffener = self.ring_stf
        elif stf_type.lower().strip() == 'frame':
            assert self.ring_frame is not None, 'Ring frame not defined'
            stiffener = self.ring_frame

        stiff_properties.hs = stiffener.hw / 2 if stiffener.type =='FB' else stiffener.hw + stiffener.tf / 2
        stiff_properties.It = stiffener.get_torsional_moment_venant()
        se = self.curved_panel.get_effective_width_shell_plate()

        stiff_properties.Ipo = stiffener.get_polar_moment()
        stiff_properties.Iz = stiffener.get_Iz_moment_of_inertia()

        stiff_properties.Iy = stiffener.get_moment_of_intertia(plate_thickness=self.curved_panel.thickness, plate_width=se) * 1000**4

        # A = self.long_stf.get_cross_section_area(plate_thickness=0, plate_width=0) * math.pow(1000,2)
        beta = self.curved_panel.l / (1.56 * math.sqrt(self.curved_panel.radius * self.curved_panel.thickness))
        stiff_properties.le0 = (self.curved_panel.l / beta) * ((math.cosh(2 * beta) - math.cos(2 * beta)) / (math.sinh(2 * beta) + math.sin(2 * beta)))

        if stf_type.lower().strip() == 'long':
            zp = stiffener.get_cross_section_centroid() * 1000
            h_tot = stiffener.hw + stiffener.tf
            stiff_properties.zt = h_tot - zp
        else:
            se = self.curved_panel.get_effective_width_shell_plate()
            zp = stiffener.get_cross_section_centroid(plate_thickness=self.curved_panel.thickness, plate_width=se) * 1000 # ch7.5.1 page 19
            h_tot = self.curved_panel.thickness * 1000 + stiffener.hw + stiffener.tf
            stiff_properties.zt = h_tot - zp
        
        return stiff_properties


    def get_shell_calculation_stress(self):
        '''
        Section 2.2, 2.2.6 not implemented
        Calculate the stresses for the shell buckling.
        '''
        # initialize the properties at 0
        stress_calculation_values = ShellDerivedStressValues()
        
        # 2.2.2: Longitudinal membrane stress
        worst_axial_comb = min(self.load.saSd / 1e6 - self.load.smSd / 1e6, self.load.saSd / 1e6 + self.load.smSd / 1e6)
        stress_calculation_values.sxSd = worst_axial_comb

        # 2.2.3: Shear stress
        # "Circumferential and longitudinal stiffeners are normally not considered to affect tSd"
        # For a panel, there is no distinction between shear and torsion.
        # For a cylinder, the shear stress is calculated as the sum of the shear stress and the torsion stress,
        # and taken as the sum of the absolute values of the two,
        # since in a cilinder there is a point where they are opposite and a point in the same direction. 
        stress_calculation_values.tSd = abs(self.load.tTSd / 1e6) + abs(self.load.tQSd / 1e6)

        # 2.2.4 circumferential membrane stress & 2.2.5 Circumferential stress in a ring frame
        if self.geometry in [StiffenedShellType.UNSTIFFENED_PANEL, StiffenedShellType.UNSTIFFENED_CYCLINDER]:
            # why is shSd_add  added?
            stress_calculation_values.shSd = (self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness + self.load.shSd_add / 1e6
            # why is this not saSd +abs(smSd) eg. sxsd_used?
            stress_calculation_values.sxSd = self.load.saSd / 1e6 + self.load.smSd / 1e6 if self.geometry in [2,6] else \
                        min([self.load.saSd / 1e6, self.load.saSd / 1e6 - self.load.smSd / 1e6, self.load.saSd / 1e6 + self.load.smSd / 1e6])
        
        if self.geometry == StiffenedShellType.LONGITUDINAL_STIFFENED_SHELL:
            # shsd is not an input, but a derived value. Should this not be 2.2.8?
            # why is shSd_add added?
            stress_calculation_values.shSd = (self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness + self.load.shSd_add / 1e6
            return stress_calculation_values
        
        if self.geometry == StiffenedShellType.RING_STIFFENED_SHELL:
            ring_stiff_properties = self.get_shell_stiffener_properties('ring')
            stress_calculation_values.shSd = ((self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness) \
                    - ring_stiff_properties.alpha * ring_stiff_properties.eta / (ring_stiff_properties.alpha + 1) \
                    * ((self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness - self.curved_panel.material.poisson * stress_calculation_values.sxSd) \
                    + self.load.shSd_add / 1e6

            if self.ring_frame is not None:
                ring_frame_properties = self.get_shell_stiffener_properties('frame')
                rf = ring_frame_properties.rf
                stress_calculation_values.shRSd = ((self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness \
                                                - self.curved_panel.material.poisson * stress_calculation_values.sxSd / 1e6) \
                                                * (1 / (1 + ring_frame_properties.alpha)) * (self.curved_panel.radius / rf) \
                                                + self.load.shSd_add / 1e6 

        if self.geometry == StiffenedShellType.ORTHOGONALLY_STIFFENED_SHELL:
            ring_stiff_properties = self.get_shell_stiffener_properties('ring')
            stress_calculation_values.shSd = ((self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness) \
                    - ring_stiff_properties.alpha * ring_stiff_properties.eta / (ring_stiff_properties.alpha + 1) \
                    * ((self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness - self.curved_panel.material.poisson * stress_calculation_values.sxSd) \
                    + self.load.shSd_add / 1e6

            if self.ring_frame is not None:
                ring_frame_properties = self.get_shell_stiffener_properties('frame')
                rf = ring_frame_properties.rf
                stress_calculation_values.shRSd = ((self.load.pSd / 1e6) * self.curved_panel.radius / self.curved_panel.thickness \
                                                - self.curved_panel.material.poisson * stress_calculation_values.sxSd / 1e6) \
                                                * (1 / (1 + ring_frame_properties.alpha)) * (self.curved_panel.radius / rf) \
                                                + self.load.shSd_add / 1e6

        stress_calculation_values.sjSd = math.sqrt(stress_calculation_values.sxSd**2 \
                                                    - stress_calculation_values.sxSd * stress_calculation_values.shSd \
                                                    + stress_calculation_values.shSd**2 \
                                                    + 3 * stress_calculation_values.tSd**2)
        
        # 3.2.4 / 3.2.5 / 3.2.6
        stress_calculation_values.sa0Sd = -self.load.saSd if self.load.saSd < 0 else 0
        stress_calculation_values.sm0Sd = -self.load.smSd if self.load.smSd < 0 else 0
        stress_calculation_values.sh0Sd = -stress_calculation_values.shSd if stress_calculation_values.shSd < 0 else 0
        return stress_calculation_values


    def unstiffened_panel(self, conical = False):
        # TODO: Add conical shell buckling
        '''
        3.3 Elastic buckling strength of unstiffened curved panels
        '''
        t = self.curved_panel.thickness * 1000

        # s is either panel s (unstiffened panel) or distance between longitudinal stiffeners (unstiffened cylinder)
        # s is not used in the case of an unstiffened cylinder
        s = self.curved_panel.s * 1000
        
        v = self.curved_panel.material.poisson
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6

        # stresses
        stresses = self.get_shell_calculation_stress(None, None)
        sjSd = stresses.sjSd
        sa0Sd = stresses.sa0Sd
        sm0Sd = stresses.sm0Sd
        sh0Sd = stresses.sh0Sd
        tSd = stresses.tSd

        Zs = self.curved_panel.Zs  # The curvature parameter Zs (3.3.3)

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

        # should update to use ShellBucklingResult class
        for chk in ['Axial stress', 'Shear stress', 'Circumferential compression']:
            psi, epsilon, rho = table_3_1(chk=chk)
            C = self.reduced_buckling_coefficient(psi, epsilon, rho)
            fE = self.elastic_buckling_strength(C, s)
            logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
            vals.append(fE)

        fEax, fEshear, fEcirc = vals

        if any([val == 0 for val in vals]):
            lambda_s_pow = 0
        else:
            lambda_s_pow = (fy / sjSd) * (sa0Sd / fEax + sh0Sd / fEcirc + tSd / fEshear)

        lambda_s = math.sqrt(lambda_s_pow)
        fks = fy / math.sqrt(1 + math.pow(lambda_s, 4))

        results: dict = dict()
        results['fks - Unstifffed curved panel'] = fks
        # why is gammaM dependanton the user provided mat_factor?
        if lambda_s < 0.5:
            gammaM = self.curved_panel.material.mat_factor
        else:
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
        results['gammaM Unstifffed panel'] = gammaM
        fksd = fks / gammaM
        results['fksd - Unstifffed curved panel'] = fksd
        uf = sjSd / fksd

        results['UF unstiffened curved panel'] = uf
        results['gammaM curved panel'] = gammaM

        # Why is sjsd_max used here?
        sjSd_max = math.sqrt(math.pow(self.load.saSd + self.load.smSd, 2) - (self.load.saSd + self.load.smSd) * stresses.shSd + math.pow(stresses.shSd, 2) + 3 * math.pow(stresses.tSd, 2))

        uf_max =  self.curved_panel.material.mat_factor * sjSd_max / fy


        # Used in column buckling only
        # Can iter_table_1 and iter_table_2 be one function?
        def iter_table_1():
            found, sasd_iter, count, this_val, intermediate_values  = False, 0.001 if uf > 1 else self.load.saSd, 0, 0, list()

            while not found:
                # Iteration
                sigmsd_iter = self.load.smSd if self.geometry in [2,6] else min([-self.load.smSd, self.load.smSd])
                siga0sd_iter = 0 if sasd_iter >= 0 else -sasd_iter  # (3.2.4)
                sigm0sd_iter = 0 if sigmsd_iter >= 0 else -sigmsd_iter  # (3.2.5)
                sigh0sd_iter = 0 if stresses.shSd >= 0 else -stresses.shSd  # (3.2.6)

                sjsd_iter = math.sqrt(math.pow(sasd_iter + sigmsd_iter, 2) - (sasd_iter + sigmsd_iter) * stresses.shSd + math.pow(stresses.shSd, 2) +
                                      3 * math.pow(stresses.tSd, 2)) #(3.2.3)
                lambda_s_iter = math.sqrt((fy / sjsd_iter) * ((siga0sd_iter + sigm0sd_iter) / fEax + sigh0sd_iter / fEcirc + stresses.tSd / fEshear)) # (3.2.2)

                gamma_M_iter = 1  # As taken in the DNVGL sheets
                fks_iter = fy / math.sqrt(1 + math.pow(lambda_s_iter, 4))
                fksd_iter = fks_iter / gamma_M_iter
                logger.debug(f'Iteration {count} sjsd {sjsd_iter} fksd {fksd_iter} fks {fks_iter} gammaM {gamma_M_iter} lambdas_iter {lambda_s_iter}')
                this_val = sjsd_iter / fksd_iter
                intermediate_values.append(0 if this_val > 1 else siga0sd_iter)
                if this_val > 1.0 or count == 1e6:
                    found = True
                count += 1
                if this_val > 0.98:
                    sasd_iter -= 0.5
                elif this_val > 0.95:
                    sasd_iter -= 1
                elif this_val > 0.9:
                    sasd_iter -= 2
                elif this_val > 0.7:
                    sasd_iter -= 10
                else:
                    sasd_iter -= 20

                logger.debug(f'Iteration {count} sasd_iter {sasd_iter} this_val {this_val}')

            return 0 if len(intermediate_values) == 1 else max([intermediate_values[-2],0])

        results['max axial stress - 3.3 Unstifffed curved panel'] = iter_table_1()


    def unstiffened_cylinder_shell(self, stresses: ShellDerivedStressValues, conical = False):
        # TODO: Add conical shell buckling
        '''
        3.4.2 Elastic buckling strength of unstiffened circular cylinders
        '''
        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000

        # s is either panel s (unstiffened panel) or distance between longitudinal stiffeners (unstiffened cylinder)
        # s is not used in the case of an unstiffened cylinder
        s = self.curved_panel.s * 1000
        
        v = self.curved_panel.material.poisson
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6

        # stresses
        sjSd = stresses.sjSd
        sa0Sd = stresses.sa0Sd
        sm0Sd = stresses.sm0Sd
        sh0Sd = stresses.sh0Sd
        tSd = stresses.tSd

        results = dict()

        Zl = (math.pow(l, 2) / (r * t)) * math.sqrt(1 - math.pow(v, 2)) #(3.4.3) (3.6.5)
        results['Zl'] = Zl
        def table_3_2(chk):
            # ψ
            psi = {'Axial stress': 1, 
                   'Bending': 1,
                   'Torsion and shear force': 5.34,
                   'Lateral pressure': 4, 
                   'Hydrostatic pressure': 2} 
            # ξ
            epsilon = {'Axial stress': 0.702 * Zl,
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
            C = self.reduced_buckling_coefficient(psi, epsilon, rho) # (3.4.2) (3.6.4)
            fE = self.elastic_buckling_strength(C, l) # (3.4.1) (3.6.3)
            logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
            vals.append(fE)


        fEax, fEbend, fEtors, fElat, fEhyd = vals

        results['fEax - Unstifffed circular cylinders'] = fEax

        test1 = 3.85 * math.sqrt(r / t)
        test2 = 2.25 * math.sqrt(r / t)
        test_l_div_r = l / r
        results['fEh - Unstifffed circular cylinders  - Psi=4'] = 0.25 * E * math.pow(t / r, 2) if test_l_div_r > test2 else fElat
        if l / r > test1:
            fEt_used = 0.25 * E * math.pow(t / r, 3/2)  # (3.4.4)
        else:
            fEt_used = fEtors

        if l / r > test2:
            fEh_used = 0.25 * E * math.pow(t / r, 2)
        else:
            fEh_used = fElat if self.end_cap_pressure_included == 'not included in axial stresses' else fEhyd

        sjsd = math.sqrt(math.pow(stresses.sxSd, 2) - stresses.sxSd * stresses.shSd + math.pow(stresses.shSd, 2) + 3 * math.pow(stresses.tSd, 2))  # (3.2.3)

        if any([fEax == 0, fEbend == 0, fEt_used == 0, fEh_used == 0, sjsd == 0]):
            # ok if sjsd is 0, but should this not rais an error if any of the buckling strength is 0?
            lambda_s_pow = 0
        else:
            lambda_s_pow = (fy / sjsd) * (sa0Sd/fEax + sm0Sd/fEbend + sh0Sd/fEh_used + tSd/fEt_used)


        lambda_s = math.sqrt(lambda_s_pow)
        fks = fy / math.sqrt(1 + math.pow(lambda_s, 4))

        results['fks - Unstifffed circular cylinders'] = fks

        if lambda_s < 0.5:
            gammaM = self.curved_panel.material.mat_factor
        else:
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

        fksd = fks / gammaM
        results['fksd - Unstifffed circular cylinders'] = fksd
        uf = sjsd / fksd

        results['UF unstiffened circular cylinder'] = uf
        results['gammaM circular cylinder'] = gammaM
        logger.debug(f'UF {uf} Unstifffed circular cylinders')

        # Used in column buckling only
        # Can iter_table_1 and iter_table_2 be one function?
        # could it be replaced with a scipy.optimize minimize_scalar
        def iter_table_2():
            found, sasd_iter, count, this_val, intermediate_values  = False, 0 if uf > 1 else self.load.saSd, 0, 0, list()
            while not found:
                # Iteration
                sigmsd_iter = self.load.smSd if self.geometry in [2, 6] else min([-self.load.smSd, self.load.smSd])
                siga0sd_iter = 0.00001 if sasd_iter >= 0 else -sasd_iter  # (3.2.4)
                sigm0sd_iter = 0.00001 if sigmsd_iter >= 0 else -sigmsd_iter  # (3.2.5)
                sigh0sd_iter = 0.00001 if stresses.shSd >= 0 else -stresses.shSd  # (3.2.6)
                sjsd_iter = math.sqrt(
                    math.pow(sasd_iter + sigmsd_iter, 2) - (sasd_iter + sigmsd_iter) * stresses.shSd + math.pow(stresses.shSd, 2) +
                    3 * math.pow(stresses.tSd, 2))  # (3.2.3)
                if sjsd_iter == 0:
                    sjsd_iter = 0.00001
                lambdas_iter = math.sqrt((fy / sjsd_iter) * (siga0sd_iter/fEax + sigm0sd_iter/fEbend +
                                                           sigh0sd_iter/fElat + stresses.tSd/fEtors))
                gammaM_iter = 1  # As taken in the DNVGL sheets
                fks_iter = fy / math.sqrt(1 + math.pow(lambdas_iter, 4))
                fksd_iter = fks_iter / gammaM_iter
                logger.debug(f'Iteration {count} sjsd {sjsd_iter} fksd {fksd_iter} fks {fks_iter} gammaM {gammaM_iter} lambdas_iter {lambdas_iter}')

                this_val = sjsd_iter / fksd_iter
                intermediate_values.append(sasd_iter)

                if this_val > 1.0 or count == 1e6:
                    found = True
                count += 1

                if this_val > 0.98:
                    sasd_iter -= 0.5
                elif this_val > 0.95:
                    sasd_iter -= 1
                elif this_val > 0.9:
                    sasd_iter -= 2
                elif this_val > 0.7:
                    sasd_iter -= 10
                else:
                    sasd_iter -= 20

            return 0 if len(intermediate_values) == 1 else max(intermediate_values[-2],0)

        results['max axial stress - 3.4.2 Shell buckling'] = iter_table_2()
        results['shsd'] = stresses.shSd
        return results


    def ring_stiffened_shell(self, data_shell_buckling = None, column_buckling_data = None):

        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000
        s = min([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
            self.long_stf_spacing
        assert s is not None, 'Input missing: s cannot be determined from curved_panel of long_stf_spacing'

        r = self.curved_panel.radius * 1000
        l = self.curved_panel.s * 1000
        fy = self.curved_panel.material.strength / 1e6

        assert self.tot_cyl_length is not None, 'Input missing: tot_cyl_length'
        # should this not be distance between frames (according figure 3.1)?
        L = self.tot_cyl_length * 1000
        # LH = L
        sasd = self.load.saSd / 1e6
        smsd = self.load.smSd / 1e6
        tsd = abs(self.load.tTSd / 1e6 + self.load.tQSd / 1e6) # MAYBE MAYBE NOT.
        psd = self.load.pSd / 1e6

        data_shell_buckling = self.unstiffened_cylinder_shell() if data_shell_buckling == None else data_shell_buckling

        #Pnt. 3.5:  Ring stiffened shell

        # Pnt. 3.5.2.1   Requirement for cross-sectional area:
        #Zl = self._Shell.get_Zl()

        Zl = self.curved_panel.Zl if r * t > 0 else 0
        Areq = np.nan if Zl == 0 else (2 / math.pow(Zl, 2) + 0.06) * l * t
        Areq = np.array([Areq, Areq])
        Astf = np.nan if self.ring_stf is None else self.ring_stf.get_cross_section_area(include_plate=False) * 1000**2
        Aframe = np.nan if self.ring_frame is None else \
            self.ring_frame.get_cross_section_area(include_plate=False) * 1000**2
        A = np.array([Astf, Aframe])

        uf_cross_section = Areq / A

        #Pnt. 3.5.2.3   Effective width calculation of shell plate
        lef = 1.56 * math.sqrt(r * t) / (1 + 12 * t / r)
        # lef_used = np.array([min([lef, LH]), min([lef, LH])])

        #Pnt. 3.5.2.4   Required Ix for Shell subject to axial load
        A_long_stf = 0 if self.long_stf is None else self.long_stf.get_cross_section_area(include_plate=False)*1000**2
        alfaA = 0 if s * t <= 0 else A_long_stf / (s * t)


        r0 = np.array([data_shell_buckling['parameters'][0][5], data_shell_buckling['parameters'][1][5]])

        worst_ax_comp = min([sasd + smsd, sasd - smsd])

        Ixreq = np.array([abs(worst_ax_comp) * t * (1 + alfaA) * math.pow(r0[0], 4) / (500 * E * l),
                          abs(worst_ax_comp) * t * (1 + alfaA) * math.pow(r0[1], 4) / (500 * E * l)])

        #Pnt. 3.5.2.5   Required Ixh for shell subjected to torsion and/or shear:
        Ixhreq = np.array([math.pow(tsd / E, (8/5)) * math.pow(r0[0] / L, 1/5) * L * r0[0] * t * l,
                           math.pow(tsd / E, (8/5)) * math.pow(r0[1] / L, 1/5) * L * r0[1] * t * l])

        #Pnt. 3.5.2.6   Simplified calculation of Ih for shell subjected to external pressure
        zt = np.array([data_shell_buckling['parameters'][0][6],data_shell_buckling['parameters'][1][6]])
        rf = np.array([data_shell_buckling['parameters'][0][4], data_shell_buckling['parameters'][1][4]])

        #delta0 = r * self.delta0

        # (3.5.17)
        fb_ring_req_val = np.array([0 if self.ring_stf is None else 0.4 * self.ring_stf.tw * math.sqrt(E / fy),
                                    0 if self.ring_frame is None else 0.4 * self.ring_frame.tw * math.sqrt(E / fy)])
        # if self._RingStf.get_stiffener_type() == 'FB':
        #     fb_ring_req = fb_ring_req_val[0] > self._RingStf.hw
        # else:
        #     fb_ring_req = np.NaN

        # (3.5.18)
        flanged_rf_req_h_val = np.array([0 if self.ring_stf is None else 1.35 * self.ring_stf.tw * math.sqrt(E / fy),
                                         0 if self.ring_frame is None else 1.35 * self.ring_frame.tw * math.sqrt(E / fy)])
        # if self._RingFrame.get_stiffener_type() != 'FB':
        #     flanged_rf_req_h = flanged_rf_req_h_val[1] > self._RingFrame.hw
        # else:
        #     flanged_rf_req_h = np.NaN

        # (3.5.19)
        flanged_rf_req_b_val = np.array([0 if self.ring_stf is None else 7 * self.ring_stf.hw / math.sqrt(10 + E * self.ring_stf.hw / (fy * r)),
                                         0 if self.ring_frame is None else 7 * self.ring_frame.hw / math.sqrt(10 + E * self.ring_frame.hw / (fy * r))])
        # if self._RingFrame.get_stiffener_type() != 'FB':
        #     flanged_rf_req_b = flanged_rf_req_b_val[1] > self._RingFrame.b
        # else:
        #     flanged_rf_req_b = np.NaN

        if self.ring_stf is not None:
            spf_stf = self.ring_stf.hw / fb_ring_req_val[0] if self.ring_stf.type.lower().strip() == 'fb' \
                else max([flanged_rf_req_b_val[0] / self.ring_stf.b, self.ring_stf.hw / flanged_rf_req_h_val[0]])
        else:
            spf_stf = 0

        if self.ring_frame is not None:
            spf_frame = self.ring_frame.hw / fb_ring_req_val[1] if self.ring_frame.type.lower().strip() == 'fb' \
                else max([flanged_rf_req_b_val[1] / self.ring_frame.b,self.ring_frame.hw / flanged_rf_req_h_val[1]])
        else:
            spf_frame = 0

        Stocky_profile_factor = np.array([spf_stf, spf_frame])

        fT = column_buckling_data['fT_dict']
        fT = np.array([fT['Ring Stiff.'] if Stocky_profile_factor[0] > 1 else fy,
                       fT['Ring Girder'] if Stocky_profile_factor[1] > 1 else fy])

        fr_used = np.array([fT[0] if self.fab_method_ring_stf == 1 else 0.9 * fT[0],
                            fT[1] if self.fab_method_ring_frame == 1 else 0.9 * fT[1]])
        shRsd = [abs(val) for val in data_shell_buckling['shRsd']]

        Ih = np.array([0 if E * r0[idx] * (fr_used[idx] / 2 - shRsd[idx]) == 0 else abs(psd) * r * math.pow(r0[idx], 2) * l / (3 * E) *
                                                                        (1.5 + 3 * E * zt[idx] * self.delta0 / (math.pow(r0[idx], 2)
                                                                         * (fr_used[idx] / 2 - shRsd[idx])))
              for idx in [0,1]])

        # Pnt. 3.5.2.2     Moment of inertia:
        IR = [Ih[idx] + Ixhreq[idx] + Ixreq[idx] if all([psd <= 0, Ih[idx] > 0]) else Ixhreq[idx] + Ixreq[idx]
              for idx in [0,1]]
        Iy = [data_shell_buckling['cross section data'][idx + 1][4] for idx in [0,1]]

        uf_moment_of_inertia = list()
        for idx in [0,1]:
            if Iy[idx] > 0:
                uf_moment_of_inertia.append(9.999 if fr_used[idx] < 2 * shRsd[idx] else IR[idx] / Iy[idx])
            else:
                uf_moment_of_inertia.append(0)

        # Pnt. 3.5.2.7   Refined calculation of external pressure
        # parameters.append([alpha, beta, leo, zeta, rf, r0, zt])
        I = Iy
        Ihmax = [max(0, I[idx] - Ixhreq[idx] - Ixreq[idx]) for idx in [0,1]]
        leo = [data_shell_buckling['parameters'][idx][2] for idx in [0,1]]
        Ar = A
        ih2 = [0 if Ar[idx] + leo[idx] * t == 0 else Ihmax[idx] / (Ar[idx] + leo[idx] * t) for idx in [0,1]]
        alpha_B = [0 if l*t == 0 else 12 * (1 - math.pow(self.curved_panel.material.poisson, 2)) * Ihmax[idx] / (l * math.pow(t, 3)) for idx in [0,1]]
        alpha = [data_shell_buckling['parameters'][idx][0] for idx in [0,1]]
        ZL = [math.pow(L, 2) / r / t * math.sqrt(1 - math.pow(self.curved_panel.material.poisson, 2)) for _ in [0,1]]

        C1 = [2 * (1 + alpha_B[idx]) / (1 + alpha[idx]) * (math.sqrt(1 + 0.27 * ZL[idx] / math.sqrt(1 + alpha_B[idx])) - alpha_B[idx] / (1 + alpha_B[idx]))
              for idx in [0,1]]

        C2 = [2 * math.sqrt(1 + 0.27 * ZL[idx]) for idx in [0,1]]

        mu = [0 if ih2[idx] * r * leo[idx] * C1[idx] == 0 else
              zt[idx] * delta0 * rf[idx] * l / (ih2[idx] * r * leo[idx]) * (1 - C2[idx] / C1[idx]) * 1 / (1 - self.curved_panel.material.poisson / 2) for idx in [0,1]]

        # fE = np.array([C1[idx] * math.pow(math.pi, 2) * E / (12 * (1 - math.pow(0.3, 2))) * (math.pow(t / L, 2)) if L > 0
        #                else 0.1 for idx in [0,1]])
        fE = np.array([self.elastic_buckling_strength(C1[idx], L) if L > 0
                       else 0.1 for idx in [0,1]])

        fr = np.array(fT)
        lambda_2 = fr / fE

        fk = [0 if lambda_2[idx] == 0 else fr[idx] * (1 + mu[idx] + lambda_2[idx] - math.sqrt(math.pow(1 + mu[idx] + lambda_2[idx], 2)-
                                                                                 4 * lambda_2[idx])) / (2 * lambda_2[idx])
              for idx in [0,1]]
        gammaM = self.curved_panel.material.mat_factor # LRFD
        fkd = [fk[idx] / gammaM for idx in [0,1]]
        psd = np.array([0.75 * fk[idx] * t * rf[idx] * (1 + alpha[idx]) / (gammaM * math.pow(r, 2) * (1 - 0.3 / 2)) for idx in [0,1]])

        uf_refined = abs((self.load.pSd / 1e6)) / psd

        return np.max([uf_cross_section, uf_moment_of_inertia, uf_refined], axis=0)


    def longitudinally_stiffened_shell(self, column_buckling_data = None, unstiffened_shell = None):

        h = self.curved_panel.thickness * 1000 + self.long_stf.hw + self.long_stf.tf

        hw = self.long_stf.hw
        tw = self.long_stf.tw
        b = self.long_stf.b
        tf = self.long_stf.tf

        E = self.material.young / 1e6
        t = self.curved_panel.thickness * 1000
        s = max([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
            self.long_stf.spacing
        v = self.material.poisson
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.s * 1000
        fy = self.material.strength / 1e6

        L = self.curved_panel.tot_cyl_length * 1000
        LH = L
        sasd = self.load.saSd / 1e6
        smsd = self.load.smSd / 1e6
        tsd = abs(self._tTsd / 1e6 + self._tQsd / 1e6)
        psd = self._psd / 1e6
        shsd = unstiffened_shell['shsd']

        #print(h, hw, tw, b, tf, s, r, l, L, sasd, smsd, shsd)
        lightly_stf = s/t > math.sqrt(r / t)
        provide_data = dict()

        '''
        	Selections for: Type of Structure Geometry:
        1	Unstiffened shell (Force input)
        2	Unstiffened panel (Stress input)
        3	Longitudinal Stiffened shell  (Force input)
        4	Longitudinal Stiffened panel (Stress input)
        5	Ring Stiffened shell (Force input)
        6	Ring Stiffened panel (Stress input)
        7	Orthogonally Stiffened shell (Force input)
        8	Orthogonally Stiffened panel (Stress input)
        Selected:	
        3	Longitudinal Stiffened shell  (Force input)
        '''
        #   Pnt. 3.3 Unstifffed curved panel
        data = unstiffened_shell if unstiffened_shell is not None else self.unstiffened_shell()

        if self.geometry == 1:
            fks = data['fks - Unstifffed circular cylinders']
        else:
            fks = data['fks - Unstifffed curved panel']

        sxSd = min([sasd + smsd, sasd - smsd])

        sjsd  = math.sqrt(math.pow(sxSd, 2) - sxSd * shsd + math.pow(shsd, 2) + 3 * math.pow(tsd, 2))

        Se = (fks*abs(sxSd) / (sjsd * fy)) * s

        # Moment of inertia
        As = A = hw*tw + b*tf  # checked

        num_stf = math.floor(2 * math.pi * r / s)

        e = (hw * tw * (hw / 2) + b * tf * (hw + tf / 2)) / (hw * tw + b * tw)
        Istf = h * math.pow(tw, 3) / 12 + tf * math.pow(b, 3) / 12

        dist_stf = r - t / 2 - e
        Istf_tot = 0
        angle = 0
        for _ in range(num_stf):
            Istf_tot += Istf + As * math.pow(dist_stf * math.cos(angle), 2)
            angle += 2 * math.pi / num_stf
        # Ishell = (math.pi/4) * ( math.pow(r+t/2,4) - math.pow(r-t/2,4))
        # Itot = Ishell + Istf_tot # Checked

        Iy = self.long_stf.get_moment_of_intertia(plate_width=Se/1000, plate_thickness=self.curved_panel.thickness) * 1000**4

        alpha = 12 * (1 - math.pow(v, 2)) * Iy / (s * math.pow(t, 3))
        Zl = (math.pow(l, 2) / (r * t)) * math.sqrt(1 - math.pow(v, 2))

        logger.debug(f'Zl {Zl} alpha {alpha} Iy {Iy} Se {Se} sjsd {sjsd} sxSd {sxSd} fks {fks} As {As}')

        # Table 3-3
        def table_3_3(chk):
            psi = {'Axial stress': 0 if Se == 0 else (1 + alpha) / (1 + A / (Se * t)),
                   'Torsion and shear stress': 5.54 + 1.82 * math.pow(l / s, 4/3) * math.pow(alpha, 1/3),
                   'Lateral Pressure': 2 * (1 + math.sqrt(1 + alpha))} # ψ
            epsilon = {'Axial stress': 0.702 * Zl,
                   'Torsion and shear stress': 0.856 * math.pow(Zl, 3/4),
                   'Lateral Pressure': 1.04 * math.sqrt(Zl)} # ξ
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

        #Torsional Buckling can be excluded as possible failure if:
        if self.long_stf.type.lower() == 'fb':
            chk_fb = hw <= 0.4 * tw * math.sqrt(E / fy)

        data_col_buc = column_buckling_data

        fy_used = fy if data_col_buc['lambda_T'] <= 0.6 else data_col_buc['fT']

        sasd = self.load.saSd * (A + s * t) / (A + Se * t) if A + Se * t >0 else 0
        smsd = self.load.smSd * (A + s * t) / (A + Se * t) if A + Se * t > 0 else 0

        sa0sd = -sasd if sasd < 0 else 0
        sm0sd = -smsd if smsd < 0 else 0
        sh0sd = -shsd if shsd < 0 else 0
        logger.debug(f'fy_used {fy_used} sasd {sasd} shsd {shsd} tsd {tsd}')

        sjsd_panels = math.sqrt(math.pow(sasd + smsd, 2) - (sasd + smsd) * shsd + math.pow(shsd, 2) + 3 * math.pow(tsd, 2))

        worst_axial_comb = min(sasd - smsd, sasd + smsd)
        sjsd_shells = math.sqrt(math.pow(worst_axial_comb, 2) - worst_axial_comb * shsd + math.pow(shsd, 2) + 3 * math.pow(tsd, 2))
        sxsd_used = worst_axial_comb
        provide_data['sxsd_used'] = sxsd_used
        sjsd_used = sjsd_panels if self.geometry in [2,6] else sjsd_shells
        provide_data['sjsd_used'] = sjsd_used
        lambda_s2_panel = fy_used / sjsd_panels * ((sa0sd + sm0sd) / fEax + sh0sd / fElat + tsd / fEtors) if\
            sjsd_panels * fEax * fEtors * fElat >0 else 0

        lambda_s2_shell = fy_used / sjsd_shells * (max(0, -worst_axial_comb) / fEax + sh0sd / fElat + tsd / fEtors) if\
            sjsd_shells * fEax * fEtors * fElat > 0 else 0

        shell_type = 2 if self.geometry in [1,5] else 1
        lambda_s = math.sqrt(lambda_s2_panel) if shell_type == 1 else math.sqrt(lambda_s2_shell)

        fks = fy_used / math.sqrt(1 + math.pow(lambda_s, 4))
        logger.debug(f'tsd {tsd} sasd {sasd} sjsd panels {sjsd_panels} fy_used {fy_used} lambda_T {data_col_buc['lambda_T']}')

        if lambda_s < 0.5:
            gammaM = self.material.mat_factor
        else:
            if self.material.mat_factor == 1.1:
                if lambda_s > 1:
                    gammaM = 1.4
                else:
                    gammaM = 0.8 + 0.6 * lambda_s
            elif self.material.mat_factor == 1.15:
                if lambda_s > 1:
                    gammaM = 1.45
                else:
                    gammaM = 0.85 + 0.6 * lambda_s
            else:
                if lambda_s > 1:
                    gammaM = 1.45 * (self.material.mat_factor / 1.15)
                else:
                    gammaM = 0.85 + 0.6 * lambda_s * (self.material.mat_factor / 1.15)

        if self.uls_or_als == 'ALS':
            gammaM = gammaM/self.material.mat_factor

        # Design buckling strength:
        fksd = fks / gammaM
        provide_data['fksd'] = fksd
        logger.debug(f'fksd {fksd} fks {fks} gammaM {gammaM} lambda_s {lambda_s} lambda_s^2 panel {lambda_s2_panel} sjsd {sjsd_used} worst_axial_comb {worst_axial_comb} sm0sd {sm0sd}')

        return provide_data


    def get_Itot(self, stf_type: str) -> float:
        stiffener: Stiffener = None
        if stf_type.lower().strip() == 'long':
            assert self.long_stf is not None, 'Longitudinal stiffener not defined'
            stiffener = self.long_stf
        elif stf_type.lower().strip() == 'ring':
            assert self.ring_stf is not None, 'Ring stiffener not defined'
            stiffener = self.ring_stf
        elif stf_type.lower().strip() == 'frame':
            assert self.ring_frame is not None, 'Ring frame not defined'
            stiffener = self.ring_frame

        r = self.curved_panel.radius * 1000
        s = self.curved_panel.s * 1000
        t = self.curved_panel.thickness * 1000
        hw = stiffener.web_height * 1000
        tw = stiffener.web_th * 1000
        b = stiffener.flange_width * 1000
        tf = stiffener.flange_th * 1000

        h = t + hw + tf
        As = hw*tw + b*tf  # checked
        if As != 0:
            num_stf = math.floor(2 * math.pi * r / s)
            e = (hw * tw * (hw / 2) + b * tf * (hw + tf / 2)) / (hw * tw + b * tw)
            Istf = h * math.pow(tw, 3) / 12 + tf * math.pow(b, 3) / 12
            dist_stf = r - t / 2 - e
            Istf_tot = 0
            angle = 0
            for _ in range(num_stf):
                Istf_tot += Istf + As * math.pow(dist_stf * math.cos(angle), 2)
                angle += 2 * math.pi / num_stf
        else:
            Istf_tot = 0
        Ishell = (math.pi / 4) * (math.pow(r + t/2, 4) - math.pow(r - t/2, 4))
        Itot = Ishell + Istf_tot # Checked

        return Itot


    def torsional_buckling(self, stresses, stf_type: str):
        results = dict()

        stiffener: Stiffener = None
        if stf_type.lower().strip() == 'long':
            assert self.long_stf is not None, 'Longitudinal stiffener not defined'
            stiffener = self.long_stf
        elif stf_type.lower().strip() == 'ring':
            assert self.ring_stf is not None, 'Ring stiffener not defined'
            stiffener = self.ring_stf
        elif stf_type.lower().strip() == 'frame':
            assert self.ring_frame is not None, 'Ring frame not defined'
            stiffener = self.ring_frame

        r = self.curved_panel.radius * 1000
        s = self.curved_panel.s * 1000
        t = self.curved_panel.thickness * 1000
        hw = stiffener.web_height * 1000
        tw = stiffener.web_th * 1000
        b = stiffener.flange_width * 1000
        tf = stiffener.flange_th * 1000


        G = self.curved_panel.material.young / 2 / (1 + self.curved_panel.material.poisson)

        if self.long_stf is None:
            h = self.curved_panel.thickness * 1000
        else:
            h = self.curved_panel.thickness * 1000 + self.long_stf.hw + self.long_stf.tf

        hw = 0 if self.long_stf is None else self.long_stf.hw
        tw = 0 if self.long_stf is None else self.long_stf.tw
        b = 0 if self.long_stf is None else self.long_stf.b
        tf = 0 if self.long_stf is None else self.long_stf.tf

        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000
        # s = max([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
        #     self.long_stf.spacing
        r = self.curved_panel.radius * 1000
        s = self.curved_panel.s * 1000
        fy = self.curved_panel.material.strength / 1e6

        L = self.tot_cyl_length * 1000 # type: ignore
        LH = self.ring_frame_spacing * 1000 # type: ignore
        Lc = max([L, LH])

        logger.debug(f't {t} h {h} hw {hw} tw {tw} b {b} tf {tf} s {s} r {r} l {l}')

        shell_buckling_data = self.shell_buckling()
        data = self.unstiffened_shell()

        idx = 1
        param_map = {'Ring Stiff.': 0,'Ring Girder': 1}
        fT_dict = dict()
        for key, obj in {'Longitudinal stiff.': self.long_stf, 'Ring Stiff.': self.ring_stf,
                         'Ring Girder': self.ring_frame}.items():
            if obj is None:
                idx += 1
                continue
            gammaM = data['gammaM circular cylinder'] if self.geometry > 2 else \
                data['gammaM curved panel']
            sjsd = shell_buckling_data['sjsd'][idx - 1]

            this_s = 0 if self.long_stf is None else self.long_stf.spacing
            if any([self.geometry in [1, 5], this_s > (self.curved_panel.s * 1000)]):
                fksd = data['fksd - Unstifffed circular cylinders']
            else:
                fksd = data['fksd - Unstifffed curved panel']

            fks = fksd * gammaM
            eta = sjsd / fks
            hw = obj.hw
            tw = obj.tw

            if key == 'Longitudinal stiff.':
                s_or_leo = self.curved_panel.s
                lT = self.curved_panel.l * 1000
            else:
                s_or_leo = shell_buckling_data['parameters'][param_map[key]][2]
                lT = math.pi * math.sqrt(r * hw)

            C = hw / s_or_leo * math.pow(t / tw, 3) * math.sqrt(1 - min([1, eta])) if s_or_leo * tw > 0 else 0
            beta = (3 * C + 0.2) / (C + 0.2)

            hs, It, Iz, Ipo, Iy = shell_buckling_data['cross section data'][idx - 1]
            if obj.type.lower().strip() == 'fb':
                Af = obj.tf * obj.b
                Aw = obj.hw * obj.tw
                fEt = beta * (Aw + math.pow(obj.tf / obj.tw, 2) * Af) / (Aw + 3 * Af) * G * math.pow(obj.tw / hw, 2) + \
                math.pow(math.pi, 2) * E * Iz / ((Aw / 3 + Af) * math.pow(lT, 2))
            else:
                hs, It, Iz, Ipo, Iy = shell_buckling_data['cross section data'][idx - 1]
                fEt = beta * G * It / Ipo + math.pow(math.pi, 2) * E * math.pow(hs, 2) * Iz / (Ipo * math.pow(lT, 2))

            lambdaT = math.sqrt(fy / fEt)

            mu = 0.35 * (lambdaT - 0.6)
            fT = (1 + mu + math.pow(lambdaT, 2) - math.sqrt(math.pow(1 + mu + math.pow(lambdaT, 2), 2) - 4 * math.pow(lambdaT, 2)))\
                 / (2 * math.pow(lambdaT, 2)) * fy if lambdaT > 0.6 else fy

            # General
            if key == 'Longitudinal stiff.':
                logger.debug(f'Column buckling', 'fET', fEt, 'mu', mu, 'lambdaT', lambdaT, 'hs', hs, 'It', It, 'Iz', Iz ,'Ipo', Ipo)
                results['lambda_T'] = lambdaT
                results['fT'] = fT
            fT_dict[key] = fT
            idx += 1
            # if key == 'Ring Stiff.':
            #     print(hs, It, Iz, Ipo, Iy)
            #     print('hello')
        results['fT_dict'] = fT_dict


    def column_buckling(self, stresses, data) -> Dict:
        results = dict()
        hw = 0 if self.long_stf is None else self.long_stf.hw
        tw = 0 if self.long_stf is None else self.long_stf.tw
        b = 0 if self.long_stf is None else self.long_stf.b
        tf = 0 if self.long_stf is None else self.long_stf.tf
        if self.long_stf is None:
            h = self.curved_panel.thickness * 1000
        else:
            h = self.curved_panel.thickness * 1000 + self.long_stf.hw + self.long_stf.tf

        E = self.curved_panel.material.young / 1e6
        t = self.curved_panel.thickness * 1000
        # s = max([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
        #     self.long_stf.spacing
        r = self.curved_panel.radius * 1000
        l = self.curved_panel.l * 1000
        fy = self.curved_panel.material.strength / 1e6

        L = self.tot_cyl_length * 1000 # type: ignore
        LH = self.ring_frame_spacing * 1000 # type: ignore
        Lc = max([L, LH])

        # Moment of inertia
        As = hw*tw + b*tf  # checked
        num_stf = math.floor(2 * math.pi * r / s)
        Atot = As * num_stf + 2 * math.pi * r * t
        e = (hw * tw *(hw / 2) + b * tf * (hw + tf / 2)) / (hw*tw + b*tw)
        Istf = h * math.pow(tw, 3) / 12 + tf * math.pow(b, 3) / 12

        dist_stf = r - t / 2 - e
        Istf_tot = 0
        angle = 0
        for _ in range(num_stf):
            Istf_tot += Istf + As * math.pow(dist_stf * math.cos(angle), 2)
            angle += 2 * math.pi / num_stf

        Ishell = (math.pi / 4) * ( math.pow(r + t/2, 4) - math.pow(r - t/2, 4))
        Itot = Ishell + Istf_tot # Checked

        k_factor = self.k_factor
        col_test = math.pow(k_factor * Lc / math.sqrt(Itot / Atot), 2) >= 2.5 * E / fy # 3.8.1

        results['Need to check column buckling'] = col_test
        logger.debug(f'Need to check column buckling: {col_test}')


        #Sec. 3.8.2   Column buckling strength:
        fEa = data['fEax - Unstifffed circular cylinders']
        #fEa = any([geometry in [1,5], s > l])
        fEh = data['fEh - Unstifffed circular cylinders  - Psi=4']

        #   Special case:  calculation of fak for unstiffened shell:

        #   General case:

        use_fac = 1 if self.geometry < 3 else 2

        if use_fac == 1:
            a = 1 + math.pow(fy, 2) / math.pow(fEa, 2)
            b = ((2 * math.pow(fy, 2) / (fEa * fEh)) - 1) * stresses.shSd
            c = math.pow(stresses.shSd, 2) + math.pow(fy, 2) * math.pow(stresses.shSd, 2) / math.pow(fEh, 2) - math.pow(fy, 2)
            fak = 0 if b == 0 else (b + math.sqrt(math.pow(b, 2) - 4 * a * c)) / (2 * a)
        elif any([self.geometry in [StiffenedShellType.UNSTIFFENED_CYCLINDER, StiffenedShellType.UNSTIFFENED_PANEL], self.curved_panel.s > self.curved_panel.l]):
            fak = data['max axial stress - 3.4.2 Shell buckling']
        else:
            fak = data['max axial stress - 3.3 Unstifffed curved panel']

        i = Itot / Atot
        fE = 0.0001 if Lc * k_factor == 0 else E * math.sqrt(math.pi * i / (Lc * k_factor))

        lambda_ = 0 if fE == 0 else math.sqrt(fak / fE)

        fkc = (1 - 0.28 * math.pow(lambda_, 2)) * fak if lambda_ <= 1.34 else 0.9 * fak / math.pow(lambda_, 2) # added 0.9
        gammaM = data['gammaM curved panel'] #self._mat_factor  # Check

        fakd = fak / gammaM
        fkcd = fkc / gammaM

        sa0sd = stresses.sa0Sd

        if fakd * fkcd > 0:
            stab_uf = sa0sd / fkcd + (abs(self.load.smSd) / (1 - sa0sd / fE))/fakd
            stab_chk = stab_uf <= 1
        else:
            stab_uf = 10
            stab_chk = True

        #print("Stability requirement satisfied") if stab_chk else print("Not acceptable")
        # Sec. 3.9   Torsional buckling:  moved to the top

        # Stiffener check

        stf_req_h = list()
        for idx, obj in enumerate([self.long_stf, self.ring_stf, self.ring_frame]):
            if obj is None:
                stf_req_h.append(np.nan)
            else:
                stf_req_h.append(0.4 * obj.tw * math.sqrt(E / fy) if obj.type.lower().strip() == 'fb'
                                 else 1.35 * obj.tw * math.sqrt(E / fy))

        stf_req_h = np.array(stf_req_h)

        stf_req_b = list()
        for idx, obj in enumerate([self.long_stf, self.ring_stf, self.ring_frame]):
            if obj is None:
                stf_req_b.append(np.nan)
            else:
                stf_req_b.append(np.nan if obj.type.lower().strip() == 'fb' else 0.4 * obj.tf * math.sqrt(E / fy))

        bf = list()
        for idx, obj in enumerate([self.long_stf, self.ring_stf, self.ring_frame]):
            if obj is None:
                bf.append(np.nan)
            elif obj.type.lower().strip() == 'fb':
                bf.append(obj.b)
            elif obj.type.lower().strip() == 't':
                bf.append((obj.b - obj.tw) / 2)
            else:
                bf.append(obj.b - obj.tw)
        bf = np.array(bf)

        hw_div_tw = list()
        for idx, obj in enumerate([self.ring_stf, self.ring_frame]):
            if obj is None:
                hw_div_tw.append(np.nan)
            else:
                hw_div_tw.append(obj.hw / obj.tw)
        hw_div_tw = np.array(hw_div_tw)

        #parameters - [alpha, beta, leo, zeta, rf, r0, zt]

        req_hw_div_tw = list()
        for idx, obj in enumerate([self.ring_stf, self.ring_frame]):
            if obj is None:
                req_hw_div_tw.append(np.nan)
            else:
                #print(shell_buckling_data['parameters'][idx][4],obj.tw, obj.hw, E, obj.hw, obj.b, obj.tf, fy)
                to_append = np.nan if obj.b * obj.tf == 0 else 2/3 * math.sqrt(shell_buckling_data['parameters'][idx][4]
                                                                               * (obj.tw * obj.hw) * E /
                                                                               (obj.hw * obj.b * obj.tf * fy))
                req_hw_div_tw.append(to_append)
        req_hw_div_tw = np.array(req_hw_div_tw)

        ef_div_tw = list()
        for idx, obj in enumerate([self.ring_stf, self.ring_frame]):
            if obj is None:
                ef_div_tw.append(np.nan)
            else:
                ef_div_tw.append(obj.get_flange_eccentricity())
        ef_div_tw = np.array(ef_div_tw)

        ef_div_tw_req = list()
        for idx, obj in enumerate([self.ring_stf, self.ring_frame]):
            if obj is None:
                ef_div_tw_req.append(np.nan)
            else:
                ef_div_tw_req.append(np.nan if obj.b * obj.tf == 0 else
                             1/3 * shell_buckling_data['parameters'][idx][4] * obj.hw * obj.tw / obj.hw / (obj.b * obj.tf))
        ef_div_tw_req = np.array(ef_div_tw_req)

        #
        # print(stf_req_h , '>', np.array([np.nan if self._LongStf is None else self._LongStf.hw,
        #                                  np.nan if self._RingStf is None else self._RingStf.hw,
        #                                  np.nan if self._RingFrame is None else self._RingFrame.hw]))
        # print(stf_req_b , '>', bf)
        # print(hw_div_tw , '<', req_hw_div_tw)
        # print(ef_div_tw , '<', ef_div_tw_req)

        chk1 = stf_req_h>np.array([np.nan if self.long_stf is None else self.long_stf.hw,
                                  np.nan if self.ring_stf is None else self.ring_stf.hw,
                                  np.nan if self.ring_frame is None else self.ring_frame.hw])
        chk1 = [np.nan if np.isnan(val) else chk1[idx] for idx, val in enumerate(stf_req_h)]

        chk2 = stf_req_b > bf
        chk2 = [np.nan if np.isnan(val) else chk2[idx] for idx, val in enumerate(stf_req_b)]

        chk3= hw_div_tw < req_hw_div_tw
        chk3 = [np.nan if np.isnan(val) else chk3[idx] for idx, val in enumerate(req_hw_div_tw)]

        chk4 = ef_div_tw < ef_div_tw_req
        chk4 = [np.nan if np.isnan(val) else chk4[idx] for idx, val in enumerate(ef_div_tw_req)]

        results['stiffener check'] = {'longitudinal':all([chk1[0], chk2[0]]),
                                           'ring stiffener': None if self.ring_stf is None else
                                           all([chk1[1],chk2[1],chk3[0],chk4[0]]),
                                           'ring frame': None if self.ring_frame is None else
                                           True}
                                           #all([chk1[2],chk2[2],chk3[1],chk4[1]])} SKIP check for girders
        results['stiffener check detailed'] = {'longitudinal': 'Web height < ' + str(round(stf_req_h[0], 1)) if not chk1[0]
        else '' + ' ' + 'flange width < ' + str(round(stf_req_b[0], 1)) if not chk2[0] else ' ',
                                                   'ring stiffener': None if self.ring_stf is None
                                                   else 'Web height < ' + str(round(stf_req_h[1], 1)) if not chk1[1]
                                                   else '' + ' ' + 'flange width < ' + str(round(stf_req_b[1], 1)) if not chk2[1]
                                                   else ' '  + ' ' + 'hw/tw >= ' + str(round(req_hw_div_tw[0], 1))
                                                   if not chk3[0]
                                                   else '' + ' ' + 'ef/tw >= ' + str(round(ef_div_tw_req[0], 1))
                                                   if not chk4[0]
                                                   else '',
                                                   'ring frame': None if self.ring_frame is None
                                                   else 'Web height < ' + str(round(stf_req_h[2], 1)) if not chk1[2]
                                                   else '' + ' ' + 'flange width < ' +str(round(stf_req_b[2], 1)) if not chk2[2]
                                                   else ' '  + ' ' + 'hw/tw >= ' + str(round(req_hw_div_tw[1], 1))
                                                   if not chk3[1]
                                                   else '' + ' ' + 'ef/tw >= ' + str(round(ef_div_tw_req[1], 1))
                                                   if not chk4[1]
                                                   else ''}

        results['Column stability check'] = stab_chk
        results['Column stability UF'] = stab_uf

        return results


    def get_all_properties(self):
        return self.__dict__


    def set_all_properties(self, all_prop_dict): # TODO ensure that this is set when optimizing and saving.
        '''
        This can be achieved using CylindricalShell(**all_prop_dict) where all_prop_dict is a dictionary of all properties.
        '''
        pass


    def get_main_properties(self):
        main_dict = {'sasd': [self.load.saSd, 'Pa'],
                     'smsd': [self.load.smSd, 'Pa'],
                     'tTsd': [abs(self.load.tTSd), 'Pa'],
                     'tQsd': [self.load.tQSd, 'Pa'],
                     'psd': [self.load.pSd, 'Pa'],
                     'shsd': [self.load.shSd, 'Pa'],
                     'geometry': [self.geometry, ''],
                     'material factor': [self.curved_panel.material.mat_factor, ''],
                     'delta0': [self.delta0, ''],
                     'fab method ring stf': [self.fab_method_ring_stf, '-'],
                     'fab method ring girder': [self.fab_method_ring_frame, '-'],
                     'E-module': [self.curved_panel.material.young, 'Pa'],
                     'poisson': [self.curved_panel.material.poisson, '-'],
                     'mat_yield': [self.curved_panel.material.strength, 'Pa'],
                     'length between girders': [self.ring_frame_spacing, 'm'],
                     'panel spacing, s':  [self.ring_stf_spacing, 'm'],
                     'ring stf excluded': [self.ring_stiffener_excluded, ''],
                     'ring frame excluded': [self.ring_frame_excluded, ''],
                     'end cap pressure': [self.end_cap_pressure_included, ''],
                     'ULS or ALS':[self.uls_or_als, '']}

        return main_dict
        
        
    def get_x_opt(self):
        '''
        shell       (0.02, 2.5, 5, 5, 10, nan, nan, nan),
        long        (0.875, nan, 0.3, 0.01, 0.1, 0.01, nan, stiffener_type)),
        ring        (nan, nan, 0.3, 0.01, 0.1, 0.01, nan, stiffener_type)),
        ring        (nan, nan, 0.7, 0.02, 0.2, 0.02, nan, stiffener_type))] 
        
        (self._spacing, self._plate_th, self._web_height, self._web_th, self._flange_width,
                self._flange_th, self._span, self._girder_lg, self._stiffener_type)
        '''
        shell = [self.curved_panel.thickness, self.curved_panel.radius, self.curved_panel.s, self.curved_panel.l, 
                 self.tot_cyl_length, np.nan, np.nan, np.nan]
        if self.long_stf is not None:
            long = [self.long_stf_spacing / 1000, np.nan, self.long_stf.hw / 1000, self.long_stf.tw / 1000, self.long_stf.b / 1000, 
                    self.long_stf.tf / 1000, np.nan, self.long_stf.type]
        else:
            long = [0 for dummy in range(8)]
        
        if self.ring_stf is not None:
            ring_stf = [self.ring_stf_spacing / 1000, np.nan, self.ring_stf.hw / 1000, self.ring_stf.tw / 1000, self.ring_stf.b / 1000, 
                    self.ring_stf.tf / 1000, np.nan, self.ring_stf.type]
        else:
            ring_stf = [0 for dummy in range(8)]
        
        if self.ring_frame is not None:
            ring_fr = [self.ring_frame_spacing / 1000, np.nan, self.ring_frame.hw / 1000, self.ring_frame.tw / 1000, self.ring_frame.b / 1000, 
                    self.ring_frame.tf / 1000, np.nan, self.ring_frame.type]
        else:
            ring_fr = [0 for dummy in range(8)]

        return [shell, long, ring_stf, ring_fr]







    # def shell_buckling_curved_panel(self) -> ShellBucklingResult:
    #     result: ShellBucklingResult = ShellBucklingResult()

    #     t = self.curved_panel.thickness * 1000
    #     l = self.curved_panel.l * 1000
    #     s = self.curved_panel.s * 1000
    #     r = self.curved_panel.radius * 1000

    #     Zs = self.curved_panel.Zs  # The curvature parameter Zs (3.3.3)

    #     def table_3_1(chk):
    #         # ψ
    #         psi = {'fEax': 4, 
    #                'fEshear': 5.34 + 4 * math.pow(s / l, 2),
    #                'fEcirc': math.pow(1 + math.pow(s / l, 2), 2)}
    #         # ξ
    #         epsilon = {'fEax': 0.702 * Zs,
    #                    'fEshear': 0.856 * math.sqrt(s / l) * math.pow(Zs, 3/4),
    #                    'fEcirc': 1.04 * (s / l) * math.sqrt(Zs)}
    #         # ρ
    #         rho = {'fEax': 0.5 * math.pow(1 + (r / (150 * t)), -0.5),
    #                'fEshear': 0.6,
    #                'fEcirc': 0.6}
    #         return psi[chk], epsilon[chk], rho[chk]

    #     for chk in ['fEax', 'fEshear', 'fEcirc']:
    #         psi, epsilon, rho = table_3_1(chk=chk)
    #         C = self.reduced_buckling_coefficient(psi, epsilon, rho)  # (3.4.2) (3.6.4)
    #         fE = self.elastic_buckling_strength(C, s)  # (3.3.1) (3.4.1) (3.6.3)
    #         logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
    #         result.__setattr__(chk, fE)
        
    #     return result
        

    # def shell_buckling_unstiffened_cylinder(self) -> ShellBucklingResult:
    #     result: ShellBucklingResult = ShellBucklingResult()

    #     t = self.curved_panel.thickness * 1000
    #     l = self.curved_panel.l * 1000
    #     s = self.curved_panel.s * 1000
    #     r = self.curved_panel.radius * 1000

    #     Zl = self.curved_panel.Zl #(3.4.3) (3.6.5)

    #     def table_3_2(chk):
    #         # ψ
    #         psi = {'fEax': 1,
    #                'fEbend': 1,
    #                'fEtors': 5.34,
    #                'fElat': 4,
    #                'fEhyd': 2}
    #         # ξ
    #         epsilon = {'fEax': 0.702 * Zl,
    #                    'fEbend': 0.702 * Zl,
    #                    'fEtors': 0.856 * math.pow(Zl, 3/4),
    #                    'fElat': 1.04 * math.sqrt(Zl),
    #                    'fEhyd': 1.04 * math.sqrt(Zl)}
    #         # ρ
    #         rho = {'fEax': 0.5 * math.pow(1 + (r / (150 * t)), -0.5),
    #                'fEbend': 0.5 * math.pow(1 + (r / (300 * t)), -0.5),
    #                'fEtors': 0.6,
    #                'fElat': 0.6,
    #                'fEhyd': 0.6}
    #         return psi[chk], epsilon[chk], rho[chk]

    #     for chk in ['fEax', 'fEbend', 'fEtors', 'fElat', 'fEhyd']:
    #         psi, epsilon, rho = table_3_2(chk=chk)
    #         C = self.reduced_buckling_coefficient(psi, epsilon, rho)  # (3.4.2) (3.6.4)
    #         fE = self.elastic_buckling_strength(C, s)  # (3.3.1) (3.4.1) (3.6.3)
    #         logger.debug(f'{chk} C {C} psi {psi} epsilon {epsilon} rho {rho} fE {fE}')
    #         result.__setattr__(chk, fE)
        
    #     # (3.4.4) and (3.4.5)
    #     if l / r > 3.85 * math.sqrt(r / t):
    #         result.fEtors = 0.25 * self.curved_panel.material.young * math.pow(t / r, 3 / 2)

    #     if l / r > 2.25 * math.sqrt(r / t):
    #         result.fEhyd = 0.25 * self.curved_panel.material.young * math.pow(t / r, 2)
    #     else:
    #         result.fEhyd = result.fElat if self.end_cap_pressure_included  else result.fEhyd

    #     return result

    # def panel_ring_buckling(self):
    #     # asserts only for intellisense/code completion
    #     # checks are performed at init using pydantic definitions and field_validator
    #     assert self.ring_stf is not None, 'Input missing: ring_stf'
    #     assert self.ring_stf_spacing is not None, 'Input missing: ring_stf_spacing'
        
    #     E = self.ring_stf.material.young / 1e6
    #     v = self.ring_stf.material.poisson
    #     fy = self.ring_stf.material.strength / 1e6
        
    #     # curved_panel.s and long_stf_spacing are verified to match using pydantic definitions and field_validator
    #     # but does not hurt to still implement the following
    #     s = min([self.curved_panel.s, 2 * math.pi * self.curved_panel.radius]) * 1000 if self.long_stf == None else \
    #         self.long_stf_spacing
    #     assert s is not None, 'Input missing: s cannot be determined from curved_panel of long_stf_spacing'

    #     l = self.ring_stf_spacing * 1000
    #     r = self.curved_panel.radius * 1000
    #     t = self.curved_panel.thickness * 1000

    #     # an array of length 2 is used to store the results for both the stiffener and the frame
    #     # first element in the array is for the stiffener and the second element is for the frame

    #     # Pnt. 3.5:  Ring stiffened shell
    #     # Pnt. 3.5.2.1   Requirement for cross-sectional area:
    #     Zl = self.curved_panel.Zl if r * t > 0 else 0
    #     Areq = np.nan if Zl == 0 else (2 / math.pow(Zl, 2) + 0.06) * l * t
    #     Areq = np.array([Areq, Areq])
        
    #     Astf = self.ring_stf.get_cross_section_area() * 1000**2
    #     Aframe = np.nan if self.ring_frame is None else self.ring_frame.get_cross_section_area() * 1000**2
        
    #     A = np.array([Astf, Aframe])

    #     uf_cross_section = Areq / A

    #     #Pnt. 3.5.2.3   Effective width calculation of shell plate
    #     lef = 1.56 * math.sqrt(r * t) / (1 + 12 * t / r)
    #     # lef_used = np.array([min([lef, LH]), min([lef, LH])])

    #     #Pnt. 3.5.2.4   Required Ix for Shell subject to axial load
    #     A_long_stf = 0 if self.long_stf is None else self.long_stf.get_cross_section_area() * 1000**2
    #     alfa_A = 0 if s * t == 0 else A_long_stf / (s * t)

    #     ring_stiffener_properties = self.get_ring_properties('stiffener')
    #     ring_frame_properties = self.get_ring_properties('stiffener')
    #     r0 = [ring_stiffener_properties['r0'], ring_frame_properties['r0']]

    #     worst_ax_comp = min([self.load.saSd + self.load.smSd, self.load.saSd - self.load.smSd])

    #     Ixreq = np.array([abs(worst_ax_comp) * t * (1 + alfa_A) * math.pow(r0[0], 4) / (500 * E * l),
    #                       abs(worst_ax_comp) * t * (1 + alfa_A) * math.pow(r0[1], 4) / (500 * E * l)])

    #     #Pnt. 3.5.2.5   Required Ixh for shell subjected to torsion and/or shear:
    #     Ixhreq = np.array([math.pow(tsd / E, (8/5)) * math.pow(r0[0] / L, 1/5) * L * r0[0] * t * l,
    #                        math.pow(tsd / E, (8/5)) * math.pow(r0[1] / L, 1/5) * L * r0[1] * t * l])

    #     #Pnt. 3.5.2.6   Simplified calculation of Ih for shell subjected to external pressure
    #     zt = np.array([ring_stiffener_properties['zt'], ring_frame_properties['zt']])
    #     # rf = np.array([data_shell_buckling['parameters'][0][4], data_shell_buckling['parameters'][1][4]])

    #     # (3.5.9)
    #     fb_ring_req_val = np.array([0 if self.ring_stf is None else 0.4 * self.ring_stf.tw * math.sqrt(E / fy),
    #                                 0 if self.ring_frame is None else 0.4 * self.ring_frame.tw * math.sqrt(E / fy)])

    #     # (3.5.10)
    #     flanged_rf_req_h_val = np.array([0 if self.ring_stf is None else 1.35 * self.ring_stf.tw * math.sqrt(E / fy),
    #                                      0 if self.ring_frame is None else 1.35 * self.ring_frame.tw * math.sqrt(E / fy)])

    #     # (3.5.11)
    #     flanged_rf_req_b_val = np.array([0 if self.ring_stf is None else 7 * self.ring_stf.hw / math.sqrt(10 + E * self.ring_stf.hw / (fy * r)),
    #                                      0 if self.ring_frame is None else 7 * self.ring_frame.hw / math.sqrt(10 + E * self.ring_frame.hw / (fy * r))])

    #     if self.ring_stf is not None:
    #         spf_stf = self.ring_stf.hw / fb_ring_req_val[0] if self.ring_stf.type.lower().strip() == 'fb' \
    #             else max([flanged_rf_req_b_val[0] / self.ring_stf.b, self.ring_stf.hw / flanged_rf_req_h_val[0]])
    #     else:
    #         spf_stf = 0

    #     if self.ring_frame is not None:
    #         spf_frame = self.ring_frame.hw / fb_ring_req_val[1] if self.ring_frame.type.lower().strip() == 'fb' \
    #             else max([flanged_rf_req_b_val[1] / self.ring_frame.b,self.ring_frame.hw / flanged_rf_req_h_val[1]])
    #     else:
    #         spf_frame = 0

    #     stocky_profile_factor = np.array([spf_stf, spf_frame])

    #     fT = column_buckling_data['fT_dict']
    #     fT = np.array([fT['Ring Stiff.'] if stocky_profile_factor[0] > 1 else fy,
    #                    fT['Ring Girder'] if stocky_profile_factor[1] > 1 else fy])

    #     fr_used = np.array([fT[0] if self.fab_method_ring_stf == 'welded' else 0.9 * fT[0],
    #                         fT[1] if self.fab_method_ring_frame == 'welded' else 0.9 * fT[1]])
    #     shRsd = [abs(val) for val in data_shell_buckling['shRsd']]

    #     Ih = np.array([0 if E * r0[idx] * (fr_used[idx] / 2 - shRsd[idx]) == 0 else abs(psd) * r * math.pow(r0[idx], 2) * l / (3 * E) *
    #                                                                     (1.5 + 3 * E * zt[idx] * self.delta0 / (math.pow(r0[idx], 2)
    #                                                                      * (fr_used[idx] / 2 - shRsd[idx])))
    #           for idx in [0,1]])

    #     # Pnt. 3.5.2.2     Moment of inertia:
    #     IR = [Ih[idx] + Ixhreq[idx] + Ixreq[idx] if all([psd <= 0, Ih[idx] > 0]) else Ixhreq[idx] + Ixreq[idx]
    #           for idx in [0,1]]
    #     Iy = [data_shell_buckling['cross section data'][idx + 1][4] for idx in [0,1]]

    #     uf_moment_of_inertia = list()
    #     for idx in [0,1]:
    #         if Iy[idx] > 0:
    #             uf_moment_of_inertia.append(9.999 if fr_used[idx] < 2 * shRsd[idx] else IR[idx] / Iy[idx])
    #         else:
    #             uf_moment_of_inertia.append(0)

    #     # Pnt. 3.5.2.7   Refined calculation of external pressure
    #     # parameters.append([alpha, beta, leo, zeta, rf, r0, zt])
    #     I = Iy
    #     Ihmax = [max(0, I[idx] - Ixhreq[idx] - Ixreq[idx]) for idx in [0,1]]
    #     leo = [data_shell_buckling['parameters'][idx][2] for idx in [0,1]]
    #     Ar = A
    #     ih2 = [0 if Ar[idx] + leo[idx] * t == 0 else Ihmax[idx] / (Ar[idx] + leo[idx] * t) for idx in [0,1]]
    #     alpha_B = [0 if l*t == 0 else 12 * (1 - math.pow(self.curved_panel.material.poisson, 2)) * Ihmax[idx] / (l * math.pow(t, 3)) for idx in [0,1]]
    #     alpha = [data_shell_buckling['parameters'][idx][0] for idx in [0,1]]
    #     ZL = [math.pow(L, 2) / r / t * math.sqrt(1 - math.pow(self.curved_panel.material.poisson, 2)) for _ in [0,1]]

    #     C1 = [2 * (1 + alpha_B[idx]) / (1 + alpha[idx]) * (math.sqrt(1 + 0.27 * ZL[idx] / math.sqrt(1 + alpha_B[idx])) - alpha_B[idx] / (1 + alpha_B[idx]))
    #           for idx in [0,1]]

    #     C2 = [2 * math.sqrt(1 + 0.27 * ZL[idx]) for idx in [0,1]]

    #     mu = [0 if ih2[idx] * r * leo[idx] * C1[idx] == 0 else
    #           zt[idx] * delta0 * rf[idx] * l / (ih2[idx] * r * leo[idx]) * (1 - C2[idx] / C1[idx]) * 1 / (1 - self.curved_panel.material.poisson / 2) for idx in [0,1]]

    #     # fE = np.array([C1[idx] * math.pow(math.pi, 2) * E / (12 * (1 - math.pow(0.3, 2))) * (math.pow(t / L, 2)) if L > 0
    #     #                else 0.1 for idx in [0,1]])
    #     fE = np.array([self.elastic_buckling_strength(C1[idx], L) if L > 0
    #                    else 0.1 for idx in [0,1]])

    #     fr = np.array(fT)
    #     lambda_2 = fr / fE

    #     fk = [0 if lambda_2[idx] == 0 else fr[idx] * (1 + mu[idx] + lambda_2[idx] - math.sqrt(math.pow(1 + mu[idx] + lambda_2[idx], 2)-
    #                                                                              4 * lambda_2[idx])) / (2 * lambda_2[idx])
    #           for idx in [0,1]]
    #     gammaM = self.curved_panel.material.mat_factor # LRFD
    #     fkd = [fk[idx] / gammaM for idx in [0,1]]
    #     psd = np.array([0.75 * fk[idx] * t * rf[idx] * (1 + alpha[idx]) / (gammaM * math.pow(r, 2) * (1 - 0.3 / 2)) for idx in [0,1]])

    #     uf_refined = abs((self.load.pSd / 1e6)) / psd

    #     return np.max([uf_cross_section, uf_moment_of_inertia, uf_refined], axis=0)
