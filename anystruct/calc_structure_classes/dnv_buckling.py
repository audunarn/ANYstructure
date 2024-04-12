from pydantic import BaseModel
import math
from typing import Optional, Dict, Any
import logging

from .stress import DerivedStressValues
from .buckling_input import BucklingInput


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


class DNVBuckling(BaseModel):
    buckling_input: BucklingInput
    calculation_domain: Optional[str]


    def get_method(self):
        gird_opt = ['Stf. pl. effective against sigma y', 'All sigma y to girder']
        #stf_opt = ['allowed', 'not allowed']
        # if self.calculation_domain == "Flat plate, stiffened with girder":

        if self.buckling_input.stifplate_effective_against_sigy == True:
            self.buckling_input.stifplate_effective_against_sigy = gird_opt[0] # type: ignore
        elif self.buckling_input.stifplate_effective_against_sigy == False:
            self.buckling_input.stifplate_effective_against_sigy = gird_opt[1] # type: ignore

        if self.calculation_domain == "Flat plate, stiffened with girder":
            if self.buckling_input.stifplate_effective_against_sigy == gird_opt[0]:
                return 1
            else:
                return 2
        else:
            return 1


    def plated_structures_buckling(self, optimizing: bool=False) -> dict:
        '''
        Summary
        '''
        return_dummy = {'Plate': {'Plate buckling': 0},
                        'Stiffener': {'Overpressure plate side': 0, 'Overpressure stiffener side': 0,
                                      'Resistance between stiffeners': 0, 'Shear capacity': 0},
                        'Girder': {'Overpressure plate side': 0, 'Overpressure girder side': 0, 'Shear capacity': 0},
                        'Local buckling': 0}

        unstf_pl = self.unstiffenedplate_buckling(optimizing = optimizing)
        up_buckling = max([unstf_pl['UF Pnt. 5  Lateral loaded plates'], unstf_pl['UF sjsd'],
                           max([unstf_pl['UF Longitudinal stress'],  unstf_pl['UF transverse stresses'],
                                unstf_pl['UF Shear stresses'], unstf_pl['UF Combined stresses']])
                           if all([self.buckling_input.panel.girder is None, self.buckling_input.panel.stiffener is None]) else 0])
        if optimizing and up_buckling > 1:
            return_dummy['Plate']['Plate buckling'] = up_buckling
            return return_dummy

        local_buckling = self.local_buckling(optimizing=optimizing)

        stf_pla: dict = {}
        if self.buckling_input.panel.stiffener is not None:
            stf_pla = self.stiffened_panel(optimizing=optimizing)
            if all([optimizing, type(stf_pla) == list]):
                return_dummy['Stiffener'][stf_pla[0]] = stf_pla[1]
                return return_dummy

            stf_buckling_pl_side = stf_pla['UF Plate side'] if self.buckling_input.panel.stiffener_end_support == "continuous" else \
                stf_pla['UF simply supported plate side']
            stf_buckling_stf_side = stf_pla['UF Stiffener side'] if self.buckling_input.panel.stiffener_end_support == "continuous" else \
                stf_pla['UF simply supported stf side']
            stfplate_resistance = stf_pla['UF Plate resistance']
            stf_shear_capacity = stf_pla['UF Shear force']
        else:
            stf_buckling_pl_side, stf_buckling_pl_side, stf_buckling_stf_side, stfplate_resistance, \
            stf_shear_capacity = 0, 0, 0, 0, 0

        # no girder if stiffener not present
        if self.buckling_input.panel.girder is not None and self.buckling_input.panel.stiffener is not None:
            girder = self.girder_buckling(optmizing=optimizing)
            if all([optimizing, type(girder) == list]):
                return_dummy['Girder'][stf_pla[0]] = stf_pla[1]
                return return_dummy

            girder_buckling_pl_side = girder['UF Cont. plate side'] if self.buckling_input.panel.girder_end_support == "continuous" else \
                stf_pla['UF Simplified plate side']
            girder_bucklinggirder_side = girder['UF Cont. girder side'] if self.buckling_input.panel.girder_end_support == "continuous" \
                else \
                stf_pla['UF Simplified girder side']
            girder_shear_capacity = girder['UF shear force']
        else:
            girder_buckling_pl_side, girder_bucklinggirder_side, girder_shear_capacity = 0, 0, 0
        
        return {'Plate': {'Plate buckling': up_buckling},
                'Stiffener': {'Overpressure plate side': stf_buckling_pl_side,
                                                    'Overpressure stiffener side': stf_buckling_stf_side, 
                                                    'Resistance between stiffeners': stfplate_resistance,
                                                    'Shear capacity': stf_shear_capacity},
                'Girder': {'Overpressure plate side': girder_buckling_pl_side,
                           'Overpressure girder side': girder_bucklinggirder_side,
                           'Shear capacity': girder_shear_capacity},
                'Local buckling': 0 if optimizing else local_buckling}


    def unstiffenedplate_buckling(self, optimizing: bool=False) -> dict:
        # internal calculations are in mm (millimeter) and MPa (mega pascal)
        unstf_pl_data = dict()

        E = self.buckling_input.panel.plate.material.young / 1e6
        fy = self.buckling_input.panel.plate.material.strength / 1e6
        gammaM = self.buckling_input.panel.plate.material.mat_factor
        thickness = self.buckling_input.panel.plate.th # mm
        spacing = self.buckling_input.panel.plate.s # mm
        length = self.buckling_input.panel.plate.l # mm

        tsd = self.buckling_input.stress.tauxy * self.buckling_input.calc_props.stress_load_factor / 1e6
        psd = self.buckling_input.pressure * self.buckling_input.calc_props.lat_load_factor

        sig_x1 = self.buckling_input.stress.sigma_x1 * self.buckling_input.calc_props.stress_load_factor / 1e6
        sig_x2 = self.buckling_input.stress.sigma_x2 * self.buckling_input.calc_props.stress_load_factor / 1e6

        sig_y1 = self.buckling_input.stress.sigma_y1 * self.buckling_input.calc_props.stress_load_factor / 1e6
        sig_y2 = self.buckling_input.stress.sigma_y2 * self.buckling_input.calc_props.stress_load_factor / 1e6

        derived_stress_values: DerivedStressValues = self.buckling_input.calculate_derived_stress_values()
        sxsd: float = derived_stress_values.sxsd
        sysd: float = derived_stress_values.sysd
        sy1sd: float = derived_stress_values.sy1sd
        max_vonMises_x: float = derived_stress_values.max_vonMises_x
        shear_ratio_long: float = derived_stress_values.stress_ratio_long
        sjsd: float = derived_stress_values.sjsd

        #Pnt. 5  Lateral loaded plates
        sjsd =math.sqrt(math.pow(max_vonMises_x, 2) + math.pow(sysd, 2) - max_vonMises_x * sysd + 3 * math.pow(tsd, 2))

        uf_sjsd = sjsd / fy * gammaM
        unstf_pl_data['UF sjsd'] = uf_sjsd

        psi_x =max([0, (1 - math.pow(sjsd / fy, 2)) / math.sqrt(1 - 3/4 * math.pow(sysd / fy, 2) - 3 * math.pow(tsd / fy, 2))]) \
            if 1 -3/4 * math.pow(sysd / fy, 2) - 3 * math.pow(tsd / fy, 2) > 0 else 0
        psi_x_chk = (1 -3/4 * math.pow(sy1sd / fy, 2) - 3 * math.pow(tsd / fy, 2))>0

        psi_y = max([0, (1 - math.pow(sjsd / fy, 2)) / math.sqrt(1 - 3/4 * math.pow(sxsd / fy, 2) - 3 * math.pow(tsd / fy, 2))]) \
            if 1 - 3/4 * math.pow(sxsd / fy, 2) - 3 * math.pow(tsd / fy, 2) > 0 else 0
        psi_y_chk = (1 - 3 / 4 * math.pow(sxsd / fy, 2) - 3 * math.pow(tsd / fy, 2)) > 0

        # why is there a hidden check for zero gamma/span/length?
        if gammaM * spacing * length == 0:
            psd_max_press = 0
        else:
            if all([psi_x_chk, psi_y_chk]):
                psd_max_press = (4 * fy / gammaM * math.pow(thickness / spacing,2) * (psi_y + math.pow(spacing / length, 2) * psi_x))
            else:
                psd_max_press = -1

        # why is 9 returned if psd_max_press is negative?
        if psd_max_press == 0:
            uf_lat_load_pl_press = 0
        else:
            uf_lat_load_pl_press = 9 if psd_max_press < 0 else abs(psd / psd_max_press)

        logger.debug("psi_x: %s psi_y: %s sjsd: %s psd: %s", psi_x, psi_y, sjsd, psd)
        logger.debug("uf_lat_load_pl_press: %s", uf_lat_load_pl_press)

        unstf_pl_data['UF Pnt. 5  Lateral loaded plates'] = uf_lat_load_pl_press

        #6.2 & 6.6 Longitudinal stress
        if 0 <= shear_ratio_long <= 1:
            ksigma = 8.2 / (1.05 + shear_ratio_long)
        elif shear_ratio_long <= -1:
            ksigma = 7.81 - 6.29 * shear_ratio_long + 9.78 * math.pow(shear_ratio_long, 2)
        elif -2 < shear_ratio_long < -1:
            ksigma = 5.98 * math.pow(1 - shear_ratio_long, 2)
        else: # shear_ratio_long <= -2:
            ksigma = "Unknown"

        # why a check for zero thickness or zero E modulus? Should be caught in the constuctor a plate and material
        if thickness * E == 0:
            lambda_p = 0
        elif ksigma == "Unknown":
            lambda_p = 1.05 * spacing / thickness * math.sqrt(fy / E)
        else:
            lambda_p = spacing / thickness / (28.4 *math.sqrt(ksigma * 235 / fy))

        Cx =(lambda_p - 0.055 * (3 + max([-2, shear_ratio_long]))) / math.pow(lambda_p, 2)

        # Formulas of 6.2 and 6.6 are mixed. Is this correct?

        sxRd = Cx * fy / gammaM if not all([sig_x1 < 0, sig_x2 < 0]) else 1 * fy / gammaM # Corrected 07.08.2023, issue 126

        uf_unstf_pl_long_stress = 0 if sxRd == 0 else abs(sxsd / sxRd)
        unstf_pl_data['UF Longitudinal stress'] = uf_unstf_pl_long_stress
        
        logger.debug("Section 6.2 & 6.6: sigma2/sigma1: %s ksigma: %s lambda_p: %s Cx: %s sxRd: %s", shear_ratio_long, ksigma, lambda_p, Cx, sxRd)
        logger.debug("uf_unstf_pl_long_stress: %s", uf_unstf_pl_long_stress)

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
        syRd = syR if not all([sig_y1 < 0, sig_y2 < 0]) else fy
        syRd = syRd / gammaM
        uf_unstf_pl_trans_stress = 0 if syRd == 0 else abs(sysd)/syRd

        unstf_pl_data['UF transverse stresses'] = uf_unstf_pl_trans_stress
        
        logger.debug("Section 6.3: ha: %s kp: %s lambda_c: %s mu: %s kappa: %s", ha, kp, lambda_c, mu, kappa)
        logger.debug("uf_unstf_pl_trans_stress: %s", uf_unstf_pl_trans_stress)

        #6.4  Shear stress
        if length >= spacing:
            kl = 0 if length == 0 else 5.34 + 4 * math.pow(spacing / length, 2)
        else:
            kl = 0 if length == 0 else 5.34 * math.pow(spacing / length, 2) + 4
        unstf_pl_data['kl'] = kl
        lambda_w = 0 if thickness * E * kl == 0 else 0.795 * spacing / thickness * math.sqrt(fy / E / kl)
        if lambda_w <= 0.8:
            Ctau = 1
        elif 0.8 < lambda_w < 1.25:
            Ctau = 1 - 0.675 * (lambda_w - 0.8)
        else:
            Ctau = 0 if lambda_w == 0 else 0.9 / lambda_w

        tauRd = Ctau * fy / gammaM / math.sqrt(3)
        uf_unstf_pl_shear_stress = 0 if tauRd == 0 else tsd / tauRd
        unstf_pl_data['UF Shear stresses'] = uf_unstf_pl_shear_stress
        
        logger.debug("Section 6.4: kl: %s lambda_w: %s Ctau: %s tauRd: %s", kl, lambda_w, Ctau, tauRd)
        logger.debug("uf_unstf_pl_shear_stress: %s", uf_unstf_pl_shear_stress)

        #6.5  Combined stresses
        if lambda_w <= 0.8:
            Ctaue = 1
        elif 0.8 < lambda_w < 1.25:
            Ctaue = 1 - 0.8 * (lambda_w - 0.8)
        else:
            Ctaue = 0 if lambda_w == 0 else 1 / math.pow(lambda_w, 2)

        tauRd_comb = Ctaue * fy / gammaM / math.sqrt(3)
        tauRd_comb = tauRd if sysd > 0 else tauRd

        if spacing / thickness <= 120:
            ci = 0 if thickness == 0 else 1 - spacing / 120 / thickness
        elif spacing / thickness > 120:
            ci  = 0
        else:
            ci = 1

        sxRd_comb = fy / gammaM if all([sig_x1<0, sig_x2<0]) else sxRd
        syRd_comb = syRd

        sxsd_div_sxrd = 0 if sxRd_comb == 0 else sxsd / sxRd_comb
        sysd_div_syrd = 0 if syRd_comb == 0 else sysd / syRd_comb
        tausd_div_taurd = 0 if tauRd_comb == 0 else tsd / tauRd_comb

        comb_req = math.pow(sxsd_div_sxrd, 2) + math.pow(sysd_div_syrd, 2) - ci * sxsd_div_sxrd * sysd_div_syrd +\
                   math.pow(tausd_div_taurd, 2)
        uf_unstf_pl_comb_stress = comb_req
        unstf_pl_data['UF Combined stresses'] = uf_unstf_pl_comb_stress
        
        logger.debug("Section 6.5: lambda_w: %s Ctaue: %s tauRd_comb: %s ci: %s syRd_comb: %s", lambda_w, Ctaue, tauRd_comb, ci, syRd_comb)
        logger.debug("uf_unstf_pl_comb_stress: %s", uf_unstf_pl_comb_stress)

        return unstf_pl_data


    def stiffened_panel(self, optimizing: bool=False) -> Dict[str, Any]:
        assert self.buckling_input.panel.stiffener is not None and self.buckling_input.panel.girder_length is not None
        # What to do with possible difference in material between plate/stiffener/girder
        # now the plate is taken
        logger.debug("---------------------------------------------------------")
        logger.debug("stiffened panel check")
        logger.debug("---------------------------------------------------------")
        E = self.buckling_input.panel.plate.material.young / 1e6
        fy = self.buckling_input.panel.plate.material.strength / 1e6
        gammaM = self.buckling_input.panel.plate.material.mat_factor
        thickness = self.buckling_input.panel.plate.th # mm
        spacing = self.buckling_input.panel.plate.s # mm
        length = self.buckling_input.panel.plate.l # mm

        tsd = self.buckling_input.stress.tauxy * self.buckling_input.calc_props.stress_load_factor / 1e6
        psd = self.buckling_input.pressure * self.buckling_input.calc_props.lat_load_factor
        # sig_x1 = self.buckling_input.stress._sigma_x1 * self.calc_props._stress_load_factor
        # sig_x2 = self.buckling_input.stress._sigma_x2 * self.calc_props._stress_load_factor
        sig_y1 = self.buckling_input.stress.sigma_y1 * self.buckling_input.calc_props.stress_load_factor / 1e6
        sig_y2 = self.buckling_input.stress.sigma_y2 * self.buckling_input.calc_props.stress_load_factor / 1e6

        derived_stress_values: DerivedStressValues = self.buckling_input.calculate_derived_stress_values()
        sxsd: float = derived_stress_values.sxsd
        sysd: float = derived_stress_values.sysd
        sy1sd: float = derived_stress_values.sy1sd
        stress_ratio_trans = derived_stress_values.stress_ratio_trans

        Lg = self.buckling_input.panel.girder_length * 1000

        stf_pnl_data = dict()

        sy1sd = 0 if self.get_method() == 2 else sy1sd
        sysd = 0 if self.get_method() == 2 else sysd

        # psd_min_adj = psd if self._min_lat_press_adj_span is None else\
        #     self._min_lat_press_adj_span * self.calc_props._lat_load_factor
        

        #Pnt.7:  Buckling of stiffened plates
        # 7.2  Forces in idealised stiffened plate
        se = self.buckling_input.effectiveplate_width()
        Iy = Is = self.buckling_input.panel.stiffener.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000) * 1000**4

        kc = 0 if thickness * spacing == 0 else 2 * (1 + math.sqrt(1 + 10.9 * Is / (math.pow(thickness, 3) * spacing)))
        mc = 13.3 if self.buckling_input.panel.stiffener_end_support == "continuous" else 8.9

        zp = self.buckling_input.panel.stiffener.get_cross_section_centroid(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        zt = (self.buckling_input.panel.stiffener.hw + self.buckling_input.panel.stiffener.tf) - zp + thickness / 2

        Weff = 0.0001 if zt == 0 else Iy / zt
        Co = 0 if kc * E * thickness * spacing == 0 else Weff * fy * mc / (kc * E * math.pow(thickness, 2) * spacing)
        Po = 0 if all([sig_y1 < 0, sig_y2 < 0]) else (0.6 + 0.4 * stress_ratio_trans) * Co * sy1sd \
            if stress_ratio_trans > -1.5 else 0

        qsd_press = (psd + abs(Po)) * spacing
        qsd_opposite = abs(Po) * spacing if psd < Po else 0

        '''
        1	Overpressure on Stiffener Side
        2	Overpressure on Plate Side
        3	Overpr. may occur on both sides
        '''

        qsdplate_side = qsd_opposite if self.buckling_input.pressure_side == 'stiffener side' else qsd_press
        qsd_stf_side = qsd_opposite if self.buckling_input.pressure_side == 'plate side' else qsd_press
        
        # calculation of kl accoring section 7.2
        if length >= spacing:
            kl = 0 if length == 0 else 5.34 + 4 * math.pow(spacing / length, 2)
        else:
            kl = 0 if length == 0 else 5.34 * math.pow(spacing / length, 2) + 4

        tau_crl = 0 if spacing == 0 else kl * 0.904 * E * math.pow(thickness / spacing, 2)

        if length <= Lg:
            kg = 0 if Lg == 0 else 5.34 + 4 * math.pow(length / Lg, 2)
        else:
            kg = 0 if Lg == 0 else 5.34 * math.pow(length / Lg, 2) + 4

        tau_crg = 0 if length == 0 else kg * 0.904 * E * math.pow(thickness / length, 2) # (7.4)

        if self.buckling_input.tension_field_action == 'allowed' and tsd > (tau_crl / gammaM):
            ttf = tsd - tau_crg
        else:
            ttf = 0

        As = self.buckling_input.panel.stiffener.tw*self.buckling_input.panel.stiffener.hw + self.buckling_input.panel.stiffener.b * self.buckling_input.panel.stiffener.tf
        NSd = sxsd * (As + spacing * thickness) + ttf * spacing * thickness

        #7.4  Resistance of plate between stiffeners
        ksp = math.sqrt(1 - 3 * math.pow(tsd / fy, 2)) if tsd < (fy / math.sqrt(3)) else 0
        syRd = derived_stress_values.syR if not all([sig_y1 < 0, sig_y2 < 0]) else fy
        syrd_unstf = syRd / gammaM * ksp
        tau_sd_7_4 = fy / (math.sqrt(3) * gammaM)
        uf_stf_panel_res_betplate = max([sysd / syrd_unstf if all([syrd_unstf > 0, sysd > 0]) else 0, tsd / tau_sd_7_4])
        stf_pnl_data['UF Plate resistance'] = uf_stf_panel_res_betplate
        if optimizing and uf_stf_panel_res_betplate > 1:
            # return ['UF Plate resistance', uf_stf_panel_res_betplate]
            return stf_pnl_data

        # 7.8 Check for shear force 
        Vsd = psd * spacing * length / 2
        Vsd_div_Vrd = Vsd / self.buckling_input.VRd("stiffener")

        stf_pnl_data['UF Shear force'] = Vsd_div_Vrd
        if optimizing and Vsd_div_Vrd > 1:
            #return ['UF Shear force', Vsd_div_Vrd]
            return stf_pnl_data

        #7.5  Characteristic buckling strength of stiffeners
        # Is in the functions fkstiffener(), fkplate(), lk()

        #7.7.3  Resistance parameters for stiffeners
        # properties depend on check for shear force, section 7.8
        reduced_properties_used: bool = False # for debugging message
        if Vsd_div_Vrd < 0.5:
            Wes = 0.0001 if zt == 0 else Iy / zt
            Wep = 0.0001 if zp == 0 else Iy / zp
            Ae = As + se * thickness
        else:
            red_param = self.buckling_input.red_prop("stiffener")
            Wes = red_param['Wes']
            Wep = red_param['Wep']
            Ae = red_param['Atot']
            reduced_properties_used = True

        NRd = 0.0001 if gammaM == 0 else Ae * (fy / gammaM)  # 7.65
        NksRd = Ae * (self.buckling_input.fkstiffener_side(length if self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm is None else self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm, Vsd, "stiffener") / gammaM) #eq7.66
        NkpRd = Ae * (self.buckling_input.fkplate("stiffener") / gammaM)

        logger.debug("self.buckling_input.panel.stiffener.dist_between_lateral_supp: %s", self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm)
        Ms1Rd = Wes * (self.buckling_input.fr(0.4 * length if self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm is None else
                                   self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm, "stiffener", "stiffener") / gammaM)  # 7.68
        Ms2Rd = Wes * (self.buckling_input.fr(0.8 * length if self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm is None else
                                   self.buckling_input.panel.stiffener.dist_between_lateral_supp_mm, "stiffener", "stiffener") / gammaM)  # 7.69

        MstRd = Wes * (fy / gammaM) # 7.70 checked ok
        MpRd = Wep * (fy / gammaM) # 7.71 checked ok

        lk = self.buckling_input.lk(Vsd, "stiffener")
        ie = 0.0001 if As + se * thickness == 0 else math.sqrt(Iy / (As + se * thickness))
        Ne = ((math.pow(math.pi, 2)) * E * Ae) / (math.pow(lk / ie, 2))# eq7.72 , checked ok

        #7.6  Resistance of stiffened panels to shear stresses
        Ip = math.pow(thickness, 3) * spacing / 10.9
        tau_crs = (36 * E / (spacing * thickness * math.pow(length, 2))) * ((Ip * math.pow(Is, 3))**0.25)
        tau_Rdy = fy /math.sqrt(3) / gammaM
        tau_Rdl = tau_crl / gammaM
        tau_Rds = tau_crs / gammaM
        tau_Rd = min([tau_Rdy,tau_Rdl,tau_Rds])

        logger.debug("Stiffener properties")
        logger.debug("Area stiffener: %s", self.buckling_input.panel.stiffener.As)
        logger.debug("zp: %s Zt: %s Iy: %s Wes %s Wep: %s Reduced properties used: %s", zp, zt, Iy, Wes, Wep, reduced_properties_used)

        logger.debug("7.2 Forces in the idealised stiffened plate")
        logger.debug("kc: %s mc: %s Wes: %s stress_ratio_trans %s C0: %s P0: %s", kc, mc, Wes, stress_ratio_trans, Co, Po)
        logger.debug("qsdplate_side %s qsd_stf_side: %s kl: %s tau_crl: %s kg: %s tau_crg: %s", qsdplate_side, qsd_stf_side, kl, tau_crl, kg, tau_crg)
        logger.debug("NSd: %s", NSd)

        logger.debug("7.3 Effective plate width")
        logger.debug("se: %s", se)

        logger.debug("7.4 Resistance between stiffeners")
        logger.debug("ksp: %s tau_Rd: %s", ksp, tau_Rd)

        logger.debug("7.6 Resistance of stiffened panels to shear stresses")
        logger.debug("Ip: %s tau_crs: %s tau_Rds: %s tau_Rdy: %s", Ip, tau_crs, tau_Rds, tau_Rdy)

        logger.debug("sxsd: %s sysd: %s sy1sd: %s tau_sd_7_4 %s shear_ratio_trans: %s", sxsd, sysd, sy1sd, tau_sd_7_4, stress_ratio_trans)
        logger.debug("ie %s Ae %s", ie, Ae)
        logger.debug("Ne: %s MpRd: %s MstRd: %s Ms1Rd: %s Ms2Rd: %s NkpRd: %s NksRd: %s NRd: %s", Ne, MpRd, MstRd, Ms1Rd, Ms2Rd, NkpRd, NksRd, NRd)

        # 7.7 Interaction formulas for axial compression and lateral pressure
        u = 0 if all([tsd > (tau_crl / gammaM), self.buckling_input.tension_field_action == 'allowed']) else math.pow(tsd / tau_Rd, 2)
        zstar = zp
        if self.buckling_input.panel.stiffener_end_support == "sniped":
            #Lateral pressure on plate side:
            #7.7.2 Simple supported stiffener (sniped stiffeners)

            #Lateral pressure on plate side:
            stf_pnl_data['UF Stiffener side'] = 0
            stf_pnl_data['UF Plate side'] = 0
            uf_7_58 = NSd / NksRd - 2 * NSd / NRd + ((qsdplate_side * math.pow(length, 2) / 8) + NSd * zstar) / (MstRd * (1 - NSd / Ne)) + u
            uf_7_59 = NSd / NkpRd + ((qsdplate_side * math.pow(length, 2) / 8) + NSd * zstar) / (MpRd * (1 - NSd / Ne)) + u
            uf_max_simp_pl = max([uf_7_58, uf_7_59])
            stf_pnl_data['UF simply supported plate side'] = uf_max_simp_pl

            #Lateral pressure on stiffener side:

            uf_7_60 = NSd / NksRd + ((qsd_stf_side * math.pow(length, 2) / 8) - NSd * zstar) / (Ms2Rd * (1 - NSd / Ne)) + u
            uf_7_61 = NSd / NkpRd - 2 * NSd / NRd + ((qsd_stf_side * math.pow(length, 2) / 8) - NSd * zstar) / (MpRd * (1 - NSd / Ne)) + u

            test_qsd_l = qsd_stf_side * math.pow(length, 2) / 8 >= NSd * zstar
            uf_7_62 = NSd / NksRd - 2 * NSd / NRd + (NSd * zstar - (qsd_stf_side * math.pow(length, 2) / 8)) / (MstRd * (1 - NSd / Ne)) + u
            uf_7_63 = NSd / NkpRd + (NSd * zstar - (qsd_stf_side * math.pow(length, 2) / 8)) / (MpRd * (1 - NSd / Ne)) + u

            uf_max_simp_stf = max([0, uf_7_62, uf_7_63]) if not test_qsd_l else max([0, uf_7_60, uf_7_61])
            stf_pnl_data['UF simply supported stf side'] = uf_max_simp_stf
            logger.debug("uf_7_59: %s uf_7_60: %s uf_7_61: %s uf_7_62 %s uf_7_63: %s uf_7_64: %s u: %s z*: %s", uf_7_58, uf_7_59, uf_7_60, uf_7_61, uf_7_62, uf_7_63, u, zstar)
        elif self.buckling_input.panel.stiffener_end_support == "continuous":
            stf_pnl_data['UF simply supported stf side'] = 0
            stf_pnl_data['UF simply supported plate side'] = 0
            
            #7.7.1 Continuous stiffeners
            M1Sd_pl = abs(qsdplate_side) * math.pow(length, 2) / self.buckling_input.calc_props.km3
            M2Sd_pl = abs(qsdplate_side) * math.pow(length, 2) / self.buckling_input.calc_props.km2
            M1Sd_stf = abs(qsd_stf_side) * math.pow(length, 2) / self.buckling_input.calc_props.km3
            M2Sd_stf = abs(qsd_stf_side) * math.pow(length, 2) / self.buckling_input.calc_props.km2

            logger.debug("M1Sd_pl: %s M2Sd_pl: %s M1Sd_stf: %s M2Sd_stf %s", M1Sd_pl, M2Sd_pl, M1Sd_stf, M2Sd_stf)

            from scipy.optimize import minimize_scalar
            tolerance: float = (zp + zt) / 1000
            # Lateral pressure on plate side:
            def iteration_min_uf_pl_side(x, debug: bool=False):
                eq7_50 = NSd / NksRd + (M1Sd_pl - NSd * x) / (Ms1Rd * (1 - NSd / Ne)) + u
                eq7_51 = NSd / NkpRd - 2 * NSd / NRd +(M1Sd_pl - NSd * x) / (MpRd * (1 - NSd / Ne)) + u
                eq7_52 = NSd / NksRd - 2 * NSd / NRd + (M2Sd_pl + NSd * x) / (MstRd * (1 - NSd / Ne)) + u
                eq7_53 = NSd / NkpRd + (M2Sd_pl + NSd * x) / (MpRd * (1 - NSd / Ne)) + u
                if debug: logger.debug("eq7_50: %s eq7_51: %s eq7_52: %s eq7_53 %s z*: %s", eq7_50, eq7_51, eq7_52, eq7_53, x)
                return max(eq7_50, eq7_51, eq7_52, eq7_53)
            res_iter_pl = minimize_scalar(iteration_min_uf_pl_side, method="Bounded", bounds=(-zt+self.buckling_input.panel.stiffener.tf/2,zp), options={'xatol': tolerance})

            if type(res_iter_pl.fun) == list:
                stf_pnl_data['UF Plate side'] = res_iter_pl.fun[0]
            else:
                stf_pnl_data['UF Plate side'] = res_iter_pl.fun

            # Lateral pressure   on stiffener side:
            def iteration_min_uf_stf_side(x, debug: bool=False):
                eq7_54 = NSd / NksRd - 2 * NSd / NRd + (M1Sd_stf + NSd * x) / (MstRd * (1 - NSd / Ne)) + u
                eq7_55 = NSd / NkpRd + (M1Sd_stf + NSd * x) / (MpRd * (1 - NSd / Ne)) + u
                eq7_56 = NSd / NksRd + (M2Sd_stf - NSd * x) / (Ms2Rd * (1 - NSd / Ne)) + u
                eq7_57 = NSd / NkpRd - 2 * NSd / NRd + (M2Sd_stf - NSd * x) / (MpRd * (1 - NSd / Ne)) + u
                if debug: logger.debug("eq7_54: %s eq7_55: %s eq7_56: %s eq7_57 %s z*: %s", eq7_54, eq7_55, eq7_56, eq7_57, x)
                return max(eq7_54, eq7_55, eq7_56, eq7_57)

            res_iter_stf = minimize_scalar(iteration_min_uf_stf_side, method="Bounded", bounds=(-zt+self.buckling_input.panel.stiffener.tf/2,zp), options={'xatol': tolerance})
            if type(res_iter_stf.fun) == list:
                stf_pnl_data['UF Stiffener side'] = res_iter_stf.fun[0]
            else:
                stf_pnl_data['UF Stiffener side'] = res_iter_stf.fun
            
            # for debugging
            iteration_min_uf_pl_side(res_iter_pl.x, True)
            iteration_min_uf_stf_side(res_iter_stf.x, True)
        else:
            raise ValueError(f"{self.buckling_input.panel.stiffener_end_support} is not a valid value. Should be either 'continuous' or 'sniped'")
        
        return stf_pnl_data


    def girder_buckling(self, optmizing = False) -> dict:
        assert self.buckling_input.panel.girder is not None and self.buckling_input.panel.stiffener is not None and self.buckling_input.panel.girder_length is not None
        '''
        Buckling of girder.
        '''

        girder_data = dict()

        # the next line pure for pylance in vscode
        assert self.buckling_input.panel.girder is not None, "Data cannot be None"

        E = self.buckling_input.panel.girder.material.young / 1e6
        fy = self.buckling_input.panel.girder.material.strength / 1e6
        gammaM = self.buckling_input.panel.girder.material.mat_factor
        thickness = self.buckling_input.panel.plate.th # mm
        spacing = self.buckling_input.panel.plate.s # mm
        length = self.buckling_input.panel.plate.l # mm

        tsd = self.buckling_input.stress.tauxy * self.buckling_input.calc_props.stress_load_factor
        psd = self.buckling_input.pressure * self.buckling_input.calc_props.lat_load_factor

        derived_stress_values: DerivedStressValues = self.buckling_input.calculate_derived_stress_values()
        sxsd: float = derived_stress_values.sxsd
        sysd: float = derived_stress_values.sysd
        sy1sd: float = derived_stress_values.sy1sd

        # psd_min_adj = psd if self._min_lat_press_adj_span is None else\
        #     self._min_lat_press_adj_span * self.calc_props._lat_load_factor

        Lg = self.buckling_input.panel.girder_length * 1000 # internal variables are in meter, this calculation is in mm

        Ltg = Lg if self.buckling_input.panel.girder.dist_between_lateral_supp_mm == None else self.buckling_input.panel.girder.dist_between_lateral_supp_mm
        Lp = 0 if self.buckling_input.panel.girder_panel_length is None else self.buckling_input.panel.girder_panel_length
        
        #Pnt.8:  Buckling of Girders
        #7.8  Check for shear force
        Vsd = psd * length * Lg / 2
        Anet = self.buckling_input.panel.girder.hw * self.buckling_input.panel.girder.tw + self.buckling_input.panel.girder.tw * self.buckling_input.panel.girder.tf
        Vrd = Anet * fy / (gammaM * math.sqrt(3))

        Vsd_div_Vrd = Vsd / Vrd
        girder_data['UF shear force'] = Vsd_div_Vrd
        if optmizing and Vsd_div_Vrd > 1:
            # return ['UF shear force', Vsd_div_Vrd]
            return girder_data

        #8.2  Girder forces
        As = self.buckling_input.panel.stiffener.As
        Ag = self.buckling_input.panel.girder.As

        #sysd = 0 if self.get_method() == 2 else unstf_pl_data['sysd']
        NySd = sysd * (Ag + length * thickness)

        Is = self.buckling_input.panel.stiffener.get_moment_of_intertia() * 1000**4

        tau_cel = 18 * E / (thickness * math.pow(length, 2)) * math.pow(thickness * Is / spacing, 0.75)
        tau_ceg = 0 if Lp == 0 else tau_cel * math.pow(length, 2) / math.pow(Lp, 2)

        lambda_t1 = 0 if Lp == 0 else math.sqrt(0.6 * fy / tau_ceg)
        lambda_t2 = math.sqrt(0.6 * fy / tau_cel)

        tcrg = 0.6 * fy / math.pow(lambda_t1, 2) if lambda_t1 > 1 else 0.6 * fy
        tcrl = 0.6 * fy / math.pow(lambda_t2, 2) if lambda_t2 > 1 else 0.6 * fy

        tcrg = tcrg if self.buckling_input.panel.stiffener_end_support == "continuous" else 0

        #8.4 Effective width of girders
        #Method 1:
        # calculation of Cxs and Cys according 7.14 and 7.16
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
                ci = 0 if thickness == 0 else 1 - spacing / 120 / thickness
            else:
                ci = 0

            cys_chk = 1 - math.pow(sysd / syR, 2) + ci * ((sxsd * sysd) / (Cxs * fy * syR))
            Cys =0 if cys_chk < 0 else math.sqrt(cys_chk)

        #Method 1 cont'd
        fkx = Cxs * fy
        CxG = math.sqrt(1 - math.pow(sxsd / fkx, 2)) if sxsd < fkx else 0
        if 4 - math.pow(Lg / length, 2) != 0:
            CyG_tens = 1 if Lg > 2 * length else Lg / (length * math.sqrt(4 - math.pow(Lg / length, 2)))
        else:
            CyG_tens = 1
        CyG_comp  = 0 if length * lambda_p == 0 else Cys
        CyG = min([1, CyG_tens]) if sy1sd < 0 else min([1, CyG_comp])
        CtG = math.sqrt(1 - 3 * math.pow(tsd / fy, 2)) if tsd < fy / math.sqrt(3) else 0
        le_method1 = length * CxG * CyG * CtG

        lim_sniped_or_cont = 0.3 * Lg if self.buckling_input.panel.girder_end_support == "continuous" else 0.4 * Lg
        tot_min_lim = min([le_method1, lim_sniped_or_cont])

        #Method 2:
        CxG = math.sqrt(1 - math.pow(sxsd / fy,2))
        lambda_G = 0 if E * thickness == 0 else 0.525 * length / thickness * math.sqrt(fy / E)
        CyG = (lambda_G - 0.22) / math.pow(lambda_G, 2) if lambda_G > 0.673 else 1
        CtG = math.sqrt(1 - 3 * math.pow(tsd / fy, 2)) if tsd < fy / math.sqrt(3) else 0
        le_method2 = length * CxG * CyG * CtG

        eff_width_sec_mod = tot_min_lim if self.get_method() == 1 else le_method2
        eff_width_other_calc = le_method1 if self.get_method() == 1 else le_method2

        le = eff_width_other_calc

        AtotG = Ag + le * thickness

        Iy = self.buckling_input.panel.girder.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=le/1000) * 1000 ** 4
        zp = self.buckling_input.panel.girder.get_cross_section_centroid(plate_thickness=thickness/1000, plate_width=le/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        zt = (thickness / 2 + self.buckling_input.panel.girder.hw + self.buckling_input.panel.girder.tf) - zp  # ch 7.5.1 page 19

        if Vsd_div_Vrd < 0.5:
            WeG = 0.0001 if zt == 0 else Iy / zt
            Wep = 0.0001 if zp == 0 else Iy / zp
            AeG = Ag + eff_width_other_calc * thickness
        else:
            red_param = self.buckling_input.red_prop("girder")
            WeG = red_param['WeG']
            Wep = red_param['Wep']
            AeG = red_param['Atot']

        # #from: 7.7.3  Resistance parameters for stiffeners
        Wmin = min([WeG, Wep])
        # pf = 0.0001 if length * spacing * gammaM == 0 else 12 * Wmin * fy / (math.pow(length, 2) * spacing * gammaM)

        lk = Lg
        LGk = lk if self.buckling_input.calc_props.buckling_length_factor_girder is None else lk * self.buckling_input.calc_props.buckling_length_factor_girder

        ie = math.sqrt(Iy / AtotG)
        fE = 0 if LGk == 0 else math.pow(math.pi, 2) * E * math.pow(ie / LGk, 2)

        # 8.2  Girder forces, cont
        lambda_G = 0 if fE == 0 else math.sqrt(fy / fE)
        Q = 0 if lambda_G - 0.2 < 0 else min([1, lambda_G - 0.2])
        C_for_tsd_trg = Q * (7 - 5 * math.pow(spacing / length, 2)) * math.pow((tsd - tcrg) / tcrl, 2)
        C = C_for_tsd_trg if tsd > tcrg else 0
        p0lim = 0.02 * (thickness + As / spacing) / length * (sxsd + C * tsd)
        p0calc = 0 if spacing * self.buckling_input.panel.girder.hw * Lg * E * length == 0 else \
                 0.4 * (thickness + As / spacing) / (self.buckling_input.panel.girder.hw * (1 - spacing / Lg)) * fy / E * math.pow(Lg / length, 2) * (sxsd + C * tsd)
        p0_compression = max([p0lim, p0calc])
        p0_tension = 0 if spacing * Lg * self.buckling_input.panel.girder.hw * E * length == 0 else \
                     0.4 * (thickness + As / spacing) / (self.buckling_input.panel.girder.hw * (length - spacing / Lg)) * gammaM / E * math.pow(Lg / length, 2) * (C * tsd)
        p0 = p0_tension if sxsd < 0 else p0_compression

        qSd_pressure = (psd + p0_tension) * length if sxsd < 0 else (psd + p0_compression) * length
        qsd_oppsite = p0 * length if psd < p0 else 0
        qSdplate_side = qsd_oppsite if self.buckling_input.pressure_side == 'stiffener side' else qSd_pressure
        qSdgirder_side = qsd_oppsite if self.buckling_input.pressure_side == 'plate side' else qSd_pressure

        #8.5  Torsional buckling of girders
        
        Af = self.buckling_input.panel.girder.tf * self.buckling_input.panel.girder.b
        Aw = self.buckling_input.panel.girder.hw * self.buckling_input.panel.girder.tw

        b = max([self.buckling_input.panel.girder.b, self.buckling_input.panel.girder.tw])
        C = 0.55 if self.buckling_input.panel.girder.type in ['T', 'FB'] else 1.1
        LGT0 = b * C * math.sqrt(E * Af / (fy * (Af + Aw / 3))) #TODO can add a automatic check/message if torsional buckling shall be considered
        girder_data['Torsional buckling'] = 'Torsional buckling to be considered' if Ltg > LGT0 else \
            "Torsional buckling need not to be considered"

        # #7.7.3  Resistance parameters for stiffeners

        NRd = 0.0001 if gammaM == 0 else AeG * (fy / gammaM)  # eq7.65, checked ok

        NksRd = AeG * (self.buckling_input.fkstiffener_side(Ltg, Vsd, "girder") / gammaM) #eq7.66
        NkpRd = AeG * (self.buckling_input.fkplate('girder') / gammaM)  # checked ok
        # MsRd = WeG * self.fr(Ltg, "stiffener", "girder") / gammaM # 'stiffener side' for a girder
        Ms1Rd = WeG * (self.buckling_input.fr(0.4 * Lg, "stiffener", "girder") / gammaM)  # ok
        Ms2Rd = WeG * (self.buckling_input.fr(0.8 * Lg, "stiffener", "girder") / gammaM)  # eq7.69 checked ok

        MstRd = WeG * (fy / gammaM) #eq7.70 checked ok
        MpRd = Wep * (fy / gammaM) #eq7.71 checked ok

        NE = ((math.pow(math.pi, 2)) * E * AeG) / (math.pow(LGk / ie, 2))# eq7.72 , checked ok

        #7.7  Interaction formulas for axial compression and lateral pressure
        #7.7.2 Simple supported girder (sniped girders)
        if self.buckling_input.panel.girder_end_support == "sniped": 
            u = 0
            zstar = zp
            girder_data['UF Cont. plate side'] = 0
            girder_data['UF Cont. girder side'] = 0

            # Lateral pressure on plate side:    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #     if self.stiffener is not None: # type: ignore -> somehow pydantic makes this a tuple...
    #         assert self.stiffener_end_support is not None, "When a stiffener is defined, also the end support needs to be defined as 'continuous' or 'sniped'"
    #         if not self.stiffener_end_support.strip().lower() in ["continuous", "sniped"]: raise ValueError(f"Type {self.stiffener_end_support} is not a valid input. only 'continuous' or 'sniped'.")
    #         assert self.girder_length is not None, "When a stiffener is defined, also the girder length needs to be defined"

    #     if self.girder is not None: # type: ignore -> somehow pydantic makes this a tuple...
    #         assert self.stiffener is not None, "When a girder is defined, also the stiffener needs to be defined"
    #         assert self.girder_end_support is not None, "When a girder is defined, also the end support needs to be defined as 'continuous' or 'sniped'"
    #         if not self.girder_end_support.strip().lower() in ["continuous", "sniped"]: raise ValueError(f"Type {self.girder_end_support} is not a valid input. only 'continuous' or 'sniped'.")            
    #         assert self.girder_length is not None, "When a girder is defined, also the girder length needs to be defined"
    #         assert self.girder_panel_length is not None, "When a girder is defined, also the panel length needs to be defined"
            uf_7_58 = NySd / NksRd - 2 * NySd / NRd +((qSdplate_side * math.pow(Lg, 2) / 8) + NySd * zstar) / (MstRd * (1 - NySd / NE)) + u
            uf_7_59 = NySd / NkpRd + ((qSdplate_side * math.pow(Lg, 2) / 8) + NySd * zstar) / (MpRd * (1 - NySd / NE)) + u

            max_uf_simpplate = max([0,uf_7_58, uf_7_59])
            girder_data['UF Simplified plate side'] = max_uf_simpplate

            #Lateral pressure on girder side:
            uf_7_60 = NySd / NksRd + ((qSdgirder_side * math.pow(Lg, 2) / 8) - NySd * zstar) / (Ms2Rd * (1 - NySd / NE)) + u
            uf_7_61 = NySd / NkpRd - 2 * NySd / NRd + ((qSdgirder_side * math.pow(Lg, 2) / 8) - NySd * zstar) / (MpRd * (1 - NySd / NE)) + u

            CHK_qSd_NSd = qSdgirder_side * math.pow(Lg, 2) / 8 < NySd * zstar

            uf_7_62 = NySd / NksRd - 2 * NySd / NRd + (NySd * zstar - (qSdgirder_side * math.pow(Lg, 2) / 8)) / (MstRd * (1 - NySd / NE)) + u
            uf_7_63 = NySd / NkpRd + (NySd * zstar - (qSdgirder_side * math.pow(Lg, 2) / 8)) / (MpRd * (1 - NySd / NE)) + u

            max_uf_simpstiffener = max([0, uf_7_60, uf_7_61]) if CHK_qSd_NSd else max([0, uf_7_60, uf_7_61, uf_7_62, uf_7_63])
            girder_data['UF Simplified girder side'] = max_uf_simpstiffener
        else:
            u = 0
            girder_data['UF Simplified girder side'] = 0
            girder_data['UF Simplified plate side'] = 0
            #7.7.1 Continuous stiffeners
            M1Sd_pl = abs(qSdplate_side) * math.pow(Lg, 2) / 12
            M2Sd_pl = abs(qSdplate_side) * math.pow(Lg, 2) / 24

            M1Sd_stf = abs(qSdgirder_side) * math.pow(Lg, 2) / 12
            M2Sd_stf = abs(qSdgirder_side) * math.pow(Lg, 2) / 24
            # #Lateral pressure on plate side:
            def iterplate(zstar):
                uf_7_48 = NySd / NksRd + (M1Sd_pl - NySd * zstar) / (Ms1Rd * (1 - NySd / NE)) + u
                uf_7_49 = NySd / NkpRd - 2 * NySd / NRd + (M1Sd_pl - NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                uf_7_50 = NySd / NksRd - 2 * NySd / NRd + (M2Sd_pl + NySd * zstar) / (MstRd * (1 - NySd / NE)) + u
                uf_7_51 = NySd / NkpRd + (M2Sd_pl + NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                return max([uf_7_48, uf_7_49, uf_7_50, uf_7_51])

            from scipy.optimize import minimize_scalar
            tolerance: float = (zp + zt) / 1000
            res_iter_pl = minimize_scalar(iterplate, method="Bounded", bounds=(-zt + self.buckling_input.panel.girder.tf / 2, zp), options={'xatol': tolerance})

            if type(res_iter_pl.fun) == list:
                girder_data['UF Cont. plate side'] = res_iter_pl.fun[0]
            else:
                girder_data['UF Cont. plate side'] = res_iter_pl.fun
            #     Lateral pressure on girder side:
            def itergirder(zstar):
                uf_7_52 = NySd / NksRd - 2 * NySd / NRd + (M1Sd_stf + NySd * zstar) / (MstRd * (1 - NySd / NE)) + u
                uf_7_53 = NySd / NkpRd + (M1Sd_stf + NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                uf_7_54 = NySd / NksRd + (M2Sd_stf - NySd * zstar) / (Ms2Rd * (1 - NySd / NE)) + u
                uf_7_55 = NySd / NkpRd - 2 * NySd / NRd + (M2Sd_stf - NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                return max([uf_7_52, uf_7_53 ,uf_7_54 ,uf_7_55])

            res_itergirder = minimize_scalar(itergirder, method="Bounded", bounds=(-zt + self.buckling_input.panel.girder.tf / 2, zp), options={'xatol': tolerance})

            if type(res_itergirder.fun) == list:
                girder_data['UF Cont. girder side'] = res_itergirder.fun[0]
            else:
                girder_data['UF Cont. girder side'] = res_itergirder.fun

        return girder_data


    def local_buckling(self, optimizing: bool=False):
        '''
        Checks for girders and stiffeners
        '''
        
        if self.buckling_input.panel.stiffener is not None:
            fy = self.buckling_input.panel.stiffener.material.strength
            max_web_stf = 42 * self.buckling_input.panel.stiffener.tw * math.sqrt(235 / fy) if self.buckling_input.panel.stiffener.type != 'FB' else 0
            max_flange_stf = (14 if self.buckling_input.panel.stiffener.fabrication_method == 'welded' else 15) * self.buckling_input.panel.stiffener.tf * math.sqrt(235 / fy)
        else:
            max_web_stf = 0
            max_flange_stf = 0

        if self.buckling_input.panel.girder is not None:
            fy = self.buckling_input.panel.girder.material.strength
            max_webgirder = 42 * self.buckling_input.panel.girder.tw * math.sqrt(235 / fy) if self.buckling_input.panel.girder.type != 'FB' else 0
            max_flangegirder = (14 if self.buckling_input.panel.girder.fabrication_method == 'welded' else 15) * self.buckling_input.panel.girder.tf * math.sqrt(235 / fy)
        else:
            max_webgirder = 0
            max_flangegirder = 0

        return {'Stiffener': [max_web_stf, max_flange_stf], 'Girder': [max_webgirder, max_flangegirder]}


    def get_one_line_string_mixed(self):
        assert self.buckling_input.panel.stiffener is not None
        ''' Returning a one line string. '''
        return 'pl_' + str(round(self.buckling_input.panel.plate.s, 1)) + 'x' + str(round(self.buckling_input.panel.plate.th, 1)) + ' stf_' + \
               self.buckling_input.panel.stiffener.type + \
               str(round(self.buckling_input.panel.stiffener.hw, 1)) + 'x' + str(round(self.buckling_input.panel.stiffener.tw, 1)) + '+' + \
               str(round(self.buckling_input.panel.stiffener.b, 1)) + 'x' + \
               str(round(self.buckling_input.panel.stiffener.tf, 1))


    def get_extended_string_mixed(self):
        assert self.buckling_input.panel.stiffener is not None
        ''' Some more information returned. '''
        return 'span: '+str(round(self.buckling_input.panel.plate.s, 4)) + ' stf. type: ' + \
               self.buckling_input.panel.stiffener.type + ' pressure side: ' + self.buckling_input.pressure_side
