from pydantic import BaseModel
import math
from typing import Optional
import logging

from .stress import Stress, DerivedStressValues
from .stiffener import Stiffener
from .stiffened_panel import StiffenedPanel, Stiffened_panel_calc_props
from .puls import Puls


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


class BucklingInput(BaseModel):
    # The material factor is part of the material definition. But could also be part of the calculation_properties or even here
    panel: StiffenedPanel
    pressure: float
    pressure_side: str='both sides'
    stress: Stress=Stress(sigma_x1=0, sigma_x2=0, sigma_y1=0, sigma_y2=0, tauxy=0)
    tension_field_action: str = "not allowed"
    stifplate_effective_against_sigy: bool = True
    min_lat_press_adj_span: Optional[float] = None
    calc_props: Stiffened_panel_calc_props = Stiffened_panel_calc_props()
    puls_input: Puls = Puls()
    # def __init__(self, 
    #              panel: StiffenedPanel, 
    #              pressure: float, 
    #              pressure_side: str='both sides', 
    #              stress: Stress=Stress(0, 0, 0, 0, 0), 
    #              tension_field_action: str="not allowed", 
    #              stiffenedplate_effective_aginst_sigy: bool=True,
    #              min_lat_press_adj_span: float=None, # type: ignore
    #              calc_props: Stiffened_panel_calc_props=Stiffened_panel_calc_props(), 
    #              puls_input: Puls=Puls()):

    # @property # in mm
    # def stiffenedplate_effective_aginst_sigy_enum(self) -> GirderOpt:
    #     if self.stifplate_effective_aginst_sigy == True:
    #         return GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y
    #     else:
    #         return GirderOpt.ALL_SIMGA_Y_TOgirder
    # @stiffenedplate_effective_aginst_sigy_enum.setter # in mm
    # def stiffenedplate_effective_aginst_sigy_enum(self, val: GirderOpt):
    #     if val == GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y:
    #         self.stifplate_effective_aginst_sigy = True
    #     else:
    #         self.stifplate_effective_aginst_sigy = False


    def __str__(self):
        assert self.panel.stiffener is not None
        '''
        Returning all properties.
        '''
        return \
            str(
            '\n Plate field span:              ' + str(round(self.panel.plate.span * 1000)) + ' mm' +
            '\n Stiffener spacing:             ' + str(self.panel.plate.spacing * 1000)+' mm'+
            '\n Plate thickness:               ' + str(self.panel.plate.thickness * 1000)+' mm'+
            '\n Stiffener web height:          ' + str(self.panel.stiffener.web_height * 1000)+' mm'+
            '\n Stiffener web thickness:       ' + str(self.panel.stiffener.web_th * 1000)+' mm'+
            '\n Stiffener flange width:        ' + str(self.panel.stiffener.flange_width * 1000)+' mm'+
            '\n Stiffener flange thickness:    ' + str(self.panel.stiffener.flange_th * 1000)+' mm'+
            '\n Plate material yield:          ' + str(self.panel.plate.material.strength / 1e6)+' MPa'+
            '\n Stiffener material yield:       ' + str(self.panel.stiffener.material.strength / 1e6)+' MPa'+
            '\n Structure/stiffener type:      ' + str(self.calc_props.structure_type)+'/'+(self.panel.stiffener.type)+
            # '\n Dynamic load varible_          ' + str(self._dynamic_variable_orientation)+
            '\n Plate fixation paramter,kpp:   ' + str(self.calc_props.plate_kpp) + ' ' +
            '\n Stf. fixation paramter,kps:    ' + str(self.calc_props.stf_kps) + ' ' +
            '\n Global stress, sig_y1/sig_y2:  ' + str(round(self.stress.sigma_y1,3))+'/'+str(round(self.stress.sigma_y2,3))+ ' MPa' +
            '\n Global stress, sig_x1/sig_x2:   ' + str(round(self.stress.sigma_x1,3))+'/'+str(round(self.stress.sigma_x2,3))+ ' MPa' +
            '\n Global shear, tau_xy:          ' + str(round(self.stress.tauxy,3)) + ' MPa' +
            '\n km1,km2,km3:                   ' + str(self.calc_props.km1)+'/'+str(self.calc_props.km2)+'/'+str(self.calc_props.km3)+
            '\n Pressure side (p-plate/s-stf): ' + str(self.pressure_side) + ' ')


    def get_extended_string(self):
        ''' Some more information returned. '''
        assert self.panel.stiffener is not None
        return 'span: ' + str(round(self.panel.plate.span, 4)) + ' structure type: ' + self.calc_props.structure_type + ' stf. type: ' + \
               self.panel.stiffener.type + ' pressure side: ' + self.pressure_side


    def getplate_mat_factor(self):
        return self.panel.plate.material.mat_factor


    def getstiffener_mat_factor(self):
        assert self.panel.stiffener is not None
        return self.panel.stiffener.material.mat_factor


    def getgirder_mat_factor(self):
        if self.panel.girder is not None:
            return self.panel.girder.material.mat_factor
        else:
            raise ValueError("The girder is not defined.")


    def get_side(self):
        '''
        Return the checked pressure side.
        :return: 
        '''
        return self.pressure_side


    def get_puls_input(self, run_type: str='SP'):
        """
        Modulus of elasticity and poison are the minimum of plat or stiffener
        """
        assert self.panel.stiffener is not None
        if self.panel.stiffener.type == 'FB':
            stf_type = 'F'
        else:
            stf_type = self.panel.stiffener.type
        map_boundary = {'Continuous': 'C', 'Sniped': 'S'}
        sig_x1 = self.stress.sigma_x1
        sig_x2 = self.stress.sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd = max(sig_x1, sig_x2)
        
        elasticity: float = min(self.panel.plate.material.young, self.panel.stiffener.material.young) / 1e6
        poison: float = min(self.panel.plate.material.poisson, self.panel.stiffener.material.poisson)
        
        if self.puls_input.puls_sp_or_up == 'SP':
            return_dict = {'Identification': None, 'Length of panel': self.panel.plate.span * 1000, 'Stiffener spacing': self.panel.plate.spacing * 1000,
                            'Plate thickness': self.panel.plate.thickness * 1000,
                          'Number of primary stiffeners': 10,
                           'Stiffener type (L,T,F)': stf_type,
                            'Stiffener boundary': map_boundary[self.puls_input.puls_stf_end]
                            if map_boundary[self.puls_input.puls_stf_end] in ['C', 'S']
                            else 'C' if self.puls_input.puls_stf_end == 'Continuous' else 'S',
                          'Stiff. Height': self.panel.stiffener.web_height * 1000, 'Web thick.': self.panel.stiffener.web_th*1000,
                           'Flange width': self.panel.stiffener.flange_width * 1000,
                            'Flange thick.': self.panel.stiffener.flange_th * 1000, 'Tilt angle': 0,
                          'Number of sec. stiffeners': 0, 
                         'Modulus of elasticity': elasticity, 
                         "Poisson's ratio": poison,
                          'Yield stress plate': self.panel.plate.material.strength / 1e6, 'Yield stress stiffener': self.panel.stiffener.material.strength / 1e6,
                            'Axial stress': 0 if self.puls_input.puls_boundary == 'GT' else sigxd,
                           'Trans. stress 1': 0 if self.puls_input.puls_boundary == 'GL' else self.stress.sigma_y1,
                          'Trans. stress 2': 0 if self.puls_input.puls_boundary == 'GL' else self.stress.sigma_y2,
                           'Shear stress': self.stress.tauxy,
                            'Pressure (fixed)': None, 'In-plane support': self.puls_input.puls_boundary,
                           'sp or up': self.puls_input.puls_sp_or_up}
        else:
            boundary = self.puls_input.puls_up_boundary
            blist = list()
            if len(boundary) != 4:
                blist = ['SS', 'SS', 'SS', 'SS']
            else:
                for letter in boundary:
                    if letter.upper() == 'S':
                        blist.append('SS')
                    elif letter.upper() == 'C':
                        blist.append('CL')
                    else:
                        blist.append('SS')

            return_dict = {'Identification': None, 'Length of plate': self.panel.plate.span * 1000, 'Width of c': self.panel.plate.spacing * 1000,
                           'Plate thickness': self.panel.plate.thickness * 1000,
                         'Modulus of elasticity': elasticity, 
                         "Poisson's ratio": poison,
                          'Yield stress plate': self.panel.plate.material.strength / 1e6,
                         'Axial stress 1': 0 if self.puls_input.puls_boundary == 'GT' else sigxd,
                           'Axial stress 2': 0 if self.puls_input.puls_boundary == 'GT' else sigxd,
                           'Trans. stress 1': 0 if self.puls_input.puls_boundary == 'GL' else self.stress.sigma_y1,
                         'Trans. stress 2': 0 if self.puls_input.puls_boundary == 'GL' else self.stress.sigma_y2,
                           'Shear stress': self.stress.tauxy, 'Pressure (fixed)': None, 'In-plane support': self.puls_input.puls_boundary,
                         'Rot left': blist[0], 'Rot right': blist[1], 'Rot upper': blist[2], 'Rot lower': blist[3],
                           'sp or up': self.puls_input.puls_sp_or_up}
        return return_dict


    def get_buckling_ml_input(self, design_lat_press: float=0, sp_or_up: str='SP', alone=True, csr=False):
        assert self.panel.stiffener is not None
        '''
        Classes in data from ML

        {'negative utilisation': 1, 'non-zero': 2, 'Division by zero': 3, 'Overflow': 4, 'aspect ratio': 5,
        'global slenderness': 6, 'pressure': 7, 'web-flange-ratio': 8,  'below 0.87': 9,
                  'between 0.87 and 1': 10, 'above 1': 11}
        '''
        stf_type = {'T-bar': 1,'T': 1,  'L-bulb': 2, 'Angle': 3, 'Flatbar': 4, 'FB': 4, 'L': 3}
        stf_end = {'Cont': 1, 'C':1 , 'Sniped': 2, 'S': 2}
        field_type = {'Integrated': 1,'Int': 1, 'Girder - long': 2,'GL': 2, 'Girder - trans': 3,  'GT': 3}
        up_boundary = {'SS': 1, 'CL': 2}
        map_boundary = {'Continuous': 'C', 'Sniped': 'S'}
        sig_x1 = self.stress.sigma_x1
        sig_x2 = self.stress.sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd = max(sig_x1, sig_x2)
        
        strength: float = min(self.panel.plate.material.strength, self.panel.stiffener.material.strength) / 1e6
        
        if self.puls_input.puls_sp_or_up == 'SP':

            if csr == False:

                this_field =  [self.panel.plate.span * 1000, self.panel.plate.spacing * 1000, self.panel.plate.thickness * 1000, self.panel.stiffener.web_height * 1000,
                               self.panel.stiffener.web_th * 1000, self.panel.stiffener.flange_width * 1000, self.panel.stiffener.flange_th * 1000, strength,
                               strength, sigxd, self.stress.sigma_y1, self.stress.sigma_y2, self.stress.tauxy,
                               design_lat_press/1000, stf_type[self.panel.stiffener.type],
                               stf_end[map_boundary[self.puls_input.puls_stf_end]]]
            else:
                this_field =  [self.panel.plate.span * 1000, self.panel.plate.spacing * 1000, self.panel.plate.thickness * 1000, self.panel.stiffener.web_height * 1000,
                               self.panel.stiffener.web_th * 1000, self.panel.stiffener.flange_width * 1000, self.panel.stiffener.flange_th * 1000, strength,
                               strength,  sigxd, self.stress.sigma_y1, self.stress.sigma_y2, self.stress.tauxy,
                               design_lat_press/1000, stf_type[self.panel.stiffener.type],
                               stf_end[map_boundary[self.puls_input.puls_stf_end]],
                               field_type[self.puls_input.puls_boundary]]
        else:
            ss_cl_list = list()
            for letter_i in self.puls_input.puls_up_boundary:
                if letter_i == 'S':
                    ss_cl_list.append(up_boundary['SS'])
                else:
                    ss_cl_list.append(up_boundary['CL'])
            b1, b2, b3, b4 = ss_cl_list
            if csr == False:
                this_field =  [self.panel.plate.span * 1000, self.panel.plate.spacing * 1000, self.panel.plate.thickness * 1000, strength,
                               sigxd, self.stress.sigma_y1, self.stress.sigma_y2, self.stress.tauxy, design_lat_press/1000,
                               b1, b2, b3, b4]
            else:
                this_field =  [self.panel.plate.span * 1000, self.panel.plate.spacing * 1000, self.panel.plate.thickness * 1000, strength,
                               sigxd, self.stress.sigma_y1, self.stress.sigma_y2, self.stress.tauxy, design_lat_press/1000,
                               field_type[self.puls_input.puls_boundary], b1, b2, b3, b4]
        if alone:
            return [this_field,]
        else:
            return this_field


    def calculate_derived_stress_values(self) -> DerivedStressValues:
        # calculated values in MPa
        derived_stress_values: DerivedStressValues = DerivedStressValues()

        E = self.panel.plate.material.young / 1e6
        fy = self.panel.plate.material.strength / 1e6
        # gammaM = self.panel.plate._material._mat_factor
        thickness = self.panel.plate.th # mm
        spacing = self.panel.plate.s # mm
        length = self.panel.plate.l # mm

        tsd = self.stress.tauxy * self.calc_props.stress_load_factor / 1e6
        psd = self.pressure * self.calc_props.lat_load_factor

        sig_x1 = self.stress.sigma_x1 * self.calc_props.stress_load_factor / 1e6
        sig_x2 = self.stress.sigma_x2 * self.calc_props.stress_load_factor / 1e6

        sig_y1 = self.stress.sigma_y1 * self.calc_props.stress_load_factor / 1e6
        sig_y2 = self.stress.sigma_y2 * self.calc_props.stress_load_factor / 1e6

        if sig_x1 * sig_x2 >= 0:
            Use_Smax_x = sxsd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            Use_Smax_x = sxsd =max(sig_x1 , sig_x2)

        if sig_y1 * sig_y2 >= 0:
            Use_Smax_y = sy1sd = sig_y1 if abs(sig_y1) > abs(sig_y2) else sig_y2
        else:
            Use_Smax_y = sy1sd = max(sig_y1 , sig_y2)

        if sig_y1 * sig_y2 >= 0:
            Use_Smax_y = sy1sd = sig_y1 if abs(sig_y1) > abs(sig_y2) else sig_y2
        else:
            Use_Smax_y = sy1sd = max(sig_y1 , sig_y2)

        if sig_x1 * sig_x2 >= 0:
            Use_Smin_x = sig_x2 if abs(sig_x1) > abs(sig_x2) else sig_x1
        else:
            Use_Smin_x = min(sig_x1 , sig_x2)

        if sig_y1 * sig_y2 >= 0:
            Use_Smin_y = sig_y2 if abs(sig_y1) > abs(sig_y2) else sig_y1
        else:
            Use_Smin_y = min(sig_y1 , sig_y2)

        stress_ratio_long = 1 if Use_Smax_x == 0 else Use_Smin_x / Use_Smax_x
        stress_ratio_trans = 1 if Use_Smax_y == 0 else Use_Smin_y / Use_Smax_y
        derived_stress_values.stress_ratio_long = stress_ratio_long
        derived_stress_values.stress_ratio_trans = stress_ratio_trans
        
        max_vonMises_x = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        derived_stress_values.max_vonMises_x = max_vonMises_x

        derived_stress_values.sxsd = sxsd
        derived_stress_values.sy1sd = sy1sd

        l1 = min(length / 4, spacing / 2)
        if length == 0:
            sig_trans_l1 = Use_Smax_y
        else:
            sig_trans_l1 = Use_Smax_y * (stress_ratio_trans + (1 - stress_ratio_trans) * (length - l1) / length)


        sysd = 0.75 * Use_Smax_y if abs(0.75 * Use_Smax_y) > abs(Use_Smax_y) else sig_trans_l1
        derived_stress_values.sysd = sysd

        l1 = min(length / 4, spacing / 2)
        if length == 0:
            sig_trans_l1 = Use_Smax_y
        else:
            sig_trans_l1 = Use_Smax_y * (stress_ratio_trans + (1 - stress_ratio_trans) * (length - l1) / length)

        #5  Lateral loaded plates
        sjsd =math.sqrt(math.pow(max_vonMises_x, 2) + math.pow(sysd, 2) - max_vonMises_x * sysd + 3 * math.pow(tsd, 2))
        derived_stress_values.sjsd = sjsd

        #6.3 & 6.8 Transverse stresses:
        ha = 0 if thickness == 0 else max([0, 0.05 * spacing / thickness - 0.75])
        condition = 0 if spacing == 0 else 2 * math.pow(thickness / spacing, 2) * fy
        # Should the condition that kp >=0 not be added?
        kp = 1 - ha * (psd / fy - 2 * math.pow(thickness / spacing, 2)) if psd > condition else 1

        lambda_c = 0 if thickness*E == 0 else 1.1 * spacing / thickness * math.sqrt(fy / E)
        mu = 0.21*(lambda_c-0.2)

        if lambda_c <= 0.2:
            kappa = 1
        elif 0.2 < lambda_c < 2:
            kappa = 0 if lambda_c == 0 else 1 / (2 * math.pow(lambda_c, 2)) * (1 + mu + math.pow(lambda_c, 2) -
                                                                      math.sqrt(math.pow(1 + mu + math.pow(lambda_c, 2), 2)-
                                                                                4 * math.pow(lambda_c, 2)))
        else: # lambda_c >= 2:
            kappa = 0 if lambda_c == 0 else 1 / (2 * math.pow(lambda_c, 2)) + 0.07

        syR = 0 if length * fy == 0 else (1.3 * thickness / length * math.sqrt(E / fy) + kappa * (1 - 1.3 * thickness / length * math.sqrt(E / fy))) * fy * kp
        derived_stress_values.syR = syR

        #logger.debug("sxsd: %s sysd: %s sy1sd: %s sjsd: %s max_vonMises_x: %s syR: %s shear_ratio_long: %s shear_ratio_trans: %s",sxsd, sysd, sy1sd, sjsd, max_vonMises_x, syR, shear_ratio_long, shear_ratio_trans)

        return derived_stress_values


    def effectiveplate_width(self) -> float:
        E = self.panel.plate.material.young / 1e6
        fy = self.panel.plate.material.strength / 1e6
        thickness = self.panel.plate.th # mm
        spacing = self.panel.plate.s # mm
        
        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        
        # 7.3 Effective plate width
        syR = derived_stress_values.syR
        sysd = derived_stress_values.sysd
        sxsd = derived_stress_values.sxsd

        Cys = 0.5 * (math.sqrt(4 - 3 * math.pow(sysd / fy, 2)) + sysd / fy)

        lambda_p = 0 if thickness*E == 0 else 0.525 * (spacing / thickness) * math.sqrt(fy / E)  # reduced plate slenderness, checked not calculated with ex
        Cxs = (lambda_p - 0.22) / math.pow(lambda_p, 2) if lambda_p > 0.673 else 1

        if sysd < 0:
            Cys = min(Cys, 1)
        else:
            if spacing / thickness <= 120:
                ci = 0 if thickness == 0 else 1-spacing / 120 / thickness
            else:
                ci = 0

            cys_chk = 1 - math.pow(sysd / syR, 2) + ci * ((sxsd * sysd) / (Cxs * fy * syR))
            Cys =0 if cys_chk < 0 else math.sqrt(cys_chk)

        se_div_s = Cxs * Cys
        se = spacing * se_div_s

        # logger.debug("effective plate width: %s", se)
        return se


    def red_prop(self, stiffener_or_girder: str) -> dict:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        # TODO: update dict to object
        fy = member.material.strength / 1e6
        gammaM = member.material.mat_factor
        thickness = self.panel.plate.th # mm
        spacing = self.panel.plate.s # mm
        length = self.panel.plate.l # mm

        psd = self.pressure * self.calc_props.lat_load_factor

        #Pnt.7:  Buckling of stiffened plates
        Vsd = psd * spacing * length / 2
        Anet = (member.hw + member.tf) * member.tw # only vertical takes shear (eg. not the flange)
        Vrd = Anet * fy / (gammaM * math.sqrt(3))
        Vsd_div_Vrd = Vsd / Vrd

        As = member.tw * member.hw + member.b * member.tf
        se = self.effectiveplate_width()
        
        tw_red =max(0, member.tw * (1 - Vsd_div_Vrd))
        
        Atot_red  = As + se * thickness - member.hw * (member.tw - tw_red )
        gammaM = self.panel.plate.material.mat_factor
        It_red  = member.get_torsional_moment_venant(reduced_tw=tw_red)
        Ipo_red  = member.get_polar_moment(reduced_tw=tw_red )

        Iy_red = member.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000, reduced_tw=tw_red) * 1000**4
        zp_red  = member.get_cross_section_centroid_with_effectiveplate(plate_thickness=thickness/1000, plate_width=se/1000, reduced_tw=tw_red ) \
                    * 1000 - thickness / 2  # ch7.5.1 page 19
        zt_red  = (member.hw + member.tf) - zp_red + thickness / 2  # ch 7.5.1 page 19
        Wes_red  = 0.0001 if zt_red == 0 else Iy_red / zt_red
        Wep_red  = 0.0001 if zp_red == 0 else Iy_red / zp_red
        return {'tw':tw_red , 'Atot': Atot_red , 'It': It_red , 'Ipo': Ipo_red , 'zp': zp_red ,
                'zt': zt_red , 'Wes': Wes_red , 'Wep': Wep_red, 'Iy': Iy_red}


    def fET(self, lT, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        #7.5.2 Lateral torsional buckling
        E = member.material.young / 1e6
        v = member.material.poisson
        G = E / (2 * (1 + v))
        fy = member.material.strength / 1e6
        thickness = self.panel.plate.th # mm
        spacing = self.panel.plate.s # mm
        length = self.panel.plate.l # mm

        taud_Sd = self.stress.tauxy * self.calc_props.stress_load_factor / 1e6

        #7.5  Characteristic buckling strength of stiffeners
        fEpx = 0 if spacing == 0 else 3.62 * E * math.pow(thickness / spacing, 2) # eq 7.42, checked, ok
        fEpy = 0 if spacing == 0 else 0.9 * E * math.pow(thickness / spacing, 2) # eq 7.43, checked, ok
        fEpt = 0 if spacing == 0 else 5.0 * E * math.pow(thickness / spacing, 2) # eq 7.44, checked, ok
        c = 0 if length == 0 else 2 - (spacing / length) # eq 7.41, checked, ok

        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        sysd = derived_stress_values.sysd
        sxsd = derived_stress_values.sxsd
        # This sjSd is different from the one used in unstiffened plate: sigmax and sigmay can be set to zero for tension.
        # Question is if this is only for the calculation of lambda_e or also for the vonMises?
        sjSd = math.sqrt(
            math.pow(max([sxsd, 0]), 2) + math.pow(max([sysd, 0]), 2) - max([sxsd, 0]) * max([sysd, 0]) +
            3 * math.pow(taud_Sd, 2))  # eq 7.38, ok
        
        lambda_e = math.sqrt((fy / sjSd) * math.pow(math.pow(max([sxsd, 0]) / fEpx, c) +
                                                   math.pow(max([sysd, 0]) / fEpy, c) +
                                                   math.pow(abs(taud_Sd) / fEpt, c), 1 / c)) # eq 7.40

        fep = fy / math.sqrt(1 + math.pow(lambda_e, 4)) # eq 7.39
        eta = min(sjSd / fep, 1) # eq. 7.377

        C = 0 if member.tw == 0 else (member.hw / spacing) * math.pow(thickness / member.tw, 3) * \
                                              math.sqrt((1 - eta)) # e 7.36, checked ok

        beta = (3 * C + 0.2) / (C + 0.2) # eq 7.35
        It = member.get_torsional_moment_venant()
        Ipo = member.get_polar_moment()
        Iz = member.get_Iz_moment_of_inertia()

        hs = member.hw / 2 if member.type == 'FB' else \
            member.hw + member.tf / 2

        if Ipo * lT > 0:
            fET = beta * G * It / Ipo + math.pow(math.pi, 2) * E * math.pow(hs, 2) * Iz / (Ipo * math.pow(lT, 2)) #NOTE, beta was missed from above, added. 23.08.2022
        else:
            fET = 0.001

        logger.debug("7.5 Characteristic buckling")
        logger.debug("fEpt: %s fEpy: %s fEpx: %s c: %s sxsd: %s sysd: %s sjSd: %s tsd: %s", fEpt, fEpy, fEpx, c, sxsd, sysd, sjSd, taud_Sd)
        logger.debug("lambda_e: %s fep: %s eta: %s C: %s beta: %s lT: %s fET: %s", lambda_e, fep, eta, C, beta, lT, fET)
        return fET


    def fT(self, lT, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        fy = member.material.strength / 1e6
        fET: float = self.fET(lT, stiffener_or_girder)
        lambda_T = 0 if fET == 0 else math.sqrt(fy / fET)
        mu = 0.35 * (lambda_T - 0.6)
        fT_div_fy = (1 + mu + math.pow(lambda_T, 2) - \
                     math.sqrt(math.pow(1 + mu + math.pow(lambda_T, 2), 2) - 4 * math.pow(lambda_T, 2))) / \
                        (2 * math.pow(lambda_T, 2))
        fT = fy * fT_div_fy if lambda_T > 0.6 else fy

        logger.debug("lambda_T: %s mu: %s fT: %s", lambda_T, mu, fT)
        return fT


    def fr(self, lT, side: str, stiffener_or_girder: str=None) -> float: # type: ignore
        fy = self.panel.plate.material.strength / 1e6

        if side.strip().lower() == "plate":
            return fy
        if side.strip().lower() == "stiffener":
            assert stiffener_or_girder is not None, "stiffener_orgirder needs to be provided for a 'stiffener side' check"
            fET: float = self.fET(lT, stiffener_or_girder)
            lambda_T = math.sqrt(fy / fET)
            fT: float = self.fT(lT, stiffener_or_girder)
            fr = fT if lambda_T > 0.6 else fy
            return fr
        else:
            raise ValueError(f"The value {side} for 'side' is invalid in fr(lT, side)")

        
    def VRd(self, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        fy = self.panel.plate.material.strength / 1e6
        gammaM = self.panel.plate.material.mat_factor
        # should the following not be either 1. only the web area, or 2.n the full stiffener area?
        Anet = (member.hw + member.tf) * member.tw# + self.stiffener.b*self.stiffener.tf
        VRd = Anet * fy / (gammaM * math.sqrt(3))
        
        return VRd


    def lk(self, VSd: float, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        fy = self.panel.plate.material.strength / 1e6
        gammaM = self.panel.plate.material.mat_factor
        thickness = self.panel.plate.th # mm
        spacing = self.panel.plate.s # mm
        length = self.panel.plate.l # mm

        psd = self.pressure * self.calc_props.lat_load_factor
        psd_min_adj = psd if self.min_lat_press_adj_span is None else\
            self.min_lat_press_adj_span*self.calc_props.lat_load_factor

        As = member.As
        se = self.effectiveplate_width()
        zp = member.get_cross_section_centroid_with_effectiveplate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        zt = (member.hw + member.tf) - zp + thickness / 2
        Iy = member.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000) * 1000**4
        
        if VSd / self.VRd(stiffener_or_girder) < 0.5:
            Wes = 0.0001 if zt == 0 else Iy / zt
            Wep = 0.0001 if zp == 0 else Iy / zp
        else:
            red_param = self.red_prop(stiffener_or_girder)
            Wes = red_param['Wes']
            Wep = red_param['Wep']

        Wmin = min([Wes, Wep])
        pf = 0.0001 if length * spacing * gammaM == 0 else 12 * Wmin * fy / (math.pow(length, 2) * spacing * gammaM)

        if self.calc_props.buckling_length_factor_stf is None:
            if stiffener_or_girder.strip().lower() == "stiffener":
                member_end_support = self.panel.stiffener_end_support
            else:
                member_end_support = self.panel.girder_end_support
            if member_end_support == "continuous":
                lk = length * (1 - 0.5 * abs(psd_min_adj / pf))

            else:
                lk = length
        else:
            lk = self.calc_props.buckling_length_factor_stf * length
        
        # logger.debug("lk: %s", lk)
        return lk


    def fkstiffener_side(self, lT, VSd: float, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")
        
        E = member.material.young / 1e6
        thickness = self.panel.plate.th # mm
        As = member.As
        se = self.effectiveplate_width()
        zp = member.get_cross_section_centroid_with_effectiveplate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        zt  = (member.hw + member.tf) - zp + thickness / 2  # ch 7.5.1 page 19
        Iy = member.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000) * 1000**4
        ie = 0.0001 if As + se * thickness == 0 else math.sqrt(Iy / (As + se * thickness))
        lk = self.lk(VSd, stiffener_or_girder)
        fE = 0.0001 if lk == 0 else math.pow(math.pi, 2) * E * math.pow(ie / lk, 2)
        fr = self.fr(lT, "stiffener", stiffener_or_girder)

        lambda_ = math.sqrt(fr / fE)
        mu = 0 if ie == 0 else (0.34 + 0.08 * zt  / ie) * (lambda_ - 0.2)
        
        fk_div_fr = (1 + mu + math.pow(lambda_, 2) - math.sqrt(
            math.pow(1 + mu + math.pow(lambda_, 2), 2) - 4 * math.pow(lambda_, 2))) / (2 * math.pow(lambda_, 2))
        fk = fk_div_fr * fr if lambda_ > 0.2 else fr

        # logger.debug("fk stiffener side: %s", fk)
        return fk


    def fkplate(self, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            assert self.panel.stiffener is not None
            member: Stiffener = self.panel.stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            assert self.panel.girder is not None
            member: Stiffener = self.panel.girder
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        E = member.material.young / 1e6
        thickness = self.panel.plate.th # mm
        length = self.panel.plate.l # mm
        As = member.As
        se = self.effectiveplate_width()
        zp = member.get_cross_section_centroid_with_effectiveplate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        Iy = member.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000) * 1000**4
        ie = 0.0001 if As + se * thickness == 0 else math.sqrt(Iy / (As + se * thickness))
        lk = length
        fE = 0.0001 if lk == 0 else math.pow(math.pi, 2) * E * math.pow(ie / lk, 2)
        fr = self.fr(length, "plate", stiffener_or_girder)

        lambda_ = math.sqrt(fr / fE)
        mu = 0 if ie == 0 else (0.34 + 0.08 * zp  / ie) * (lambda_ - 0.2)
        
        fk_div_fr = (1 + mu + math.pow(lambda_, 2) - math.sqrt(
            math.pow(1 + mu + math.pow(lambda_, 2), 2) - 4 * math.pow(lambda_, 2))) / (2 * math.pow(lambda_, 2))
        fk = fk_div_fr * fr if lambda_ > 0.2 else fr

        # logger.debug("fk plate side: %s", fk)
        return fk
