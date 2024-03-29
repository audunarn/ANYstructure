from pydantic import BaseModel
import math
from typing import Union

from .buckling_input import BucklingInput
from .dnv_buckling import DNVBuckling


class CalcScantlings(BaseModel):

    '''
    This Class does the calculations for the plate fields. 
    Input is a BucklingInput object, same as for the structure class.
    The class inherits from BucklingInput class.
    '''
    buckling_input: BucklingInput
    lat_press: bool
    category: str
    need_recalc: bool
    # def __init__(self, buckling_input: BucklingInput, lat_press: bool=True, category: str='secondary'):
    #     super(CalcScantlings, self).__init__(buckling_input.panel, 
    #                                          buckling_input.pressure, 
    #                                          buckling_input.pressure_side, 
    #                                          buckling_input.stress, 
    #                                          buckling_input.tension_field_action,
    #                                          buckling_input.stiffenedplate_effective_aginst_sigy,
    #                                          buckling_input.min_lat_press_adj_span,
    #                                          buckling_input.stiffened_panel_calc_props, 
    #                                          buckling_input.puls)
    #     # pressure is defined as a property, but doesn't seem to be using in the functions, where a parameter is passed.
    #     self.lat_press: bool = lat_press
    #     self.category: str = category
    #     self._need_recalc: bool = True



    def get_results_for_report(self, lat_press: float=0) -> str:
        """
        Returns a string for the report.
        Parameters:
        -----------
        lat_press : float, optional
            Lateral pressure in kPa?? default is 0

        Returns:
        --------
        String
            Returns a string for the report.
        """
        dnv_buckling: DNVBuckling = DNVBuckling(buckling_input=self.buckling_input, calculation_domain=None)
        buc = [round(res, 1) for res in dnv_buckling.stiffened_panel().values()]

        return 'Minimum section modulus:'\
               +str(int(self.get_dnv_min_section_modulus(design_pressure_kpa = lat_press) * 1000 ** 3))\
               +'mm^3 '+' Minium plate thickness: '\
               +str(round(self.get_dnv_min_thickness(design_pressure_kpa = lat_press), 1)) + \
               ' Buckling results: eq7_19: ' + str(buc[0]) + ' eq7_50: ' + str(buc[1]) + ' eq7_51: '\
               +str(buc[2]) + ' eq7_52: ' + str(buc[3]) + ' eq7_53: ' + str(buc[4])


    def calculate_slammingplate(self, slamming_pressure: float, red_fac: float=1) -> float:
        """
        Plate slamming according DNV
        Parameters:
        -----------
        slamming_pressure : float
            Slamming pressure in kPa
        red_fac : float, optional
            Reduction factor. Default is 1

        Returns:
        --------
        Float
            Result of the calculation according ???
        """
        ka1 = 1.1
        ka2 = min(max(0.4, self.buckling_input.panel.plate.spacing / self.buckling_input.panel.plate.span), 1)

        ka = math.pow(ka1 - 0.25 * ka2, 2)
        sigmaf = self.buckling_input.panel.plate.material.strength / 1e6  # MPa

        psl = red_fac * slamming_pressure / 1000  # kPa
        Cd = 1.5

        return 0.0158 * ka * self.buckling_input.panel.plate.spacing * 1000 * math.sqrt(psl / (Cd * sigmaf))


    def calculate_slammingstiffener(self, slamming_pressure: float, angle: float=90, red_fac: float=1) -> dict[str, Union[float, None]]:
        """
        Stiffener slamming according DNV
        Parameters:
        -----------
        slamming_pressure : float
            Slamming pressure in kPa
        angle : float, optional
            Stiffener angle. Default is 90deg
        red_fac : float, optional
            Reduction factor. Default is 1

        Returns:
        --------
        dict[str, Union[float, None]]
            'tw_req' is the required web thickness
            'Zp_req': required if web thickness smaller than required, None if required web thickness is sufficient.
        """

        # should replace with either object or tuple
        assert self.buckling_input.panel.stiffener is not None
        tk = 0
        psl = slamming_pressure / 1000  # kPa
        Pst = psl * red_fac  # Currently DNV does not use psl/2 for slamming.
        sigmaf = self.buckling_input.panel.stiffener.material.strength / 1e6  # MPa
        hw, twa, tp, tf, bf, s = [(val - tk) * 1000 for val in [self.buckling_input.panel.stiffener.web_height, self.buckling_input.panel.stiffener.web_th, self.buckling_input.panel.plate.thickness,
                                                                self.buckling_input.panel.stiffener.flange_th, self.buckling_input.panel.stiffener.flange_width, self.buckling_input.panel.plate.spacing]]
        ns = 2
        tau_eH = sigmaf / math.sqrt(3)
        h_stf = (self.buckling_input.panel.stiffener.web_height+self.buckling_input.panel.stiffener.flange_th) * 1000
        f_shr = 0.7
        lbdg = self.buckling_input.panel.plate.span
        lshr = self.buckling_input.panel.plate.span - self.buckling_input.panel.plate.spacing / 4000
        dshr = h_stf + tp if 75 <= angle <= 90 else (h_stf + tp) * math.sin(math.radians(angle))
        tw = (f_shr * Pst * s * lshr) / (dshr * tau_eH)

        if self.buckling_input.panel.stiffener.web_th * 1000 < tw:
            return {'tw_req': tw, 'Zp_req': None}
        fpl = 8* (1 + (ns / 2))
        Zp_req = (1.2 * Pst * s * math.pow(lbdg, 2) / (fpl * sigmaf)) + \
                  (ns * (1 - math.sqrt(1 - math.pow(tw / twa, 2))) * hw * tw * (hw + tp)) / 8000

        return {'tw_req': tw, 'Zp_req': Zp_req}


    def check_all_slamming(self, slamming_pressure: float, stf_red_fact: float=1, pl_red_fact: float=1, angle: float=90) -> tuple[bool, Union[float, None]]:
        """
        Summary check of slamming
        Parameters:
        -----------
        slamming_pressure : float
            Slamming pressure in kPa
        stf_red_fact : float, optional
            Stiffener reduction factor. Default is 1
        pl_red_fact : float, optional
            Plate reduction factor. Default is 1
        angle : float, optional
            Stiffener angle. Default is 90deg

        Returns:
        --------
        tuple[bool, Union[float, None]]
            The bool is false if check is not ok
            The float is the check value if the check is not ok, None otherwise.
        """
        assert self.buckling_input.panel.stiffener is not None
        pl_chk = self.calculate_slammingplate(slamming_pressure, red_fac=pl_red_fact)
        if self.buckling_input.panel.plate.thickness * 1000 < pl_chk:
            chk1 = pl_chk / self.buckling_input.panel.plate.thickness * 1000
            return False, chk1

        stf_res = self.calculate_slammingstiffener(slamming_pressure, angle=angle, red_fac=stf_red_fact)
        if stf_res['tw_req'] is not None: # this is always the case though
            if self.buckling_input.panel.stiffener.web_th * 1000 < stf_res['tw_req']:
                chk2 = stf_res['tw_req'] / self.buckling_input.panel.stiffener.web_th * 1000
                return False, chk2

        if stf_res['Zp_req'] is not None:
            eff_pl_sec_mod = self.get_net_effective_plastic_section_modulus()
            if eff_pl_sec_mod < stf_res['Zp_req']:
                chk3 = stf_res['Zp_req'] / eff_pl_sec_mod
                return False, chk3

        return True, None


    def get_net_effective_plastic_section_modulus(self, angle: float=90) -> float:
        """
        Calculated according to Rules for classification: Ships — DNVGL-RU-SHIP Pt.3 Ch.3. Edition July 2017,
            page 83
        Parameters:
        -----------
        angle : float, optional
            Stiffener angle. Default is 90deg

        Returns:
        --------
        Float
            The net effective plastic section modulus
        """
        assert self.buckling_input.panel.stiffener is not None
        tk = 0
        angle_rad = math.radians(angle)
        hw, tw, tp, tf, bf = [(val - tk) * 1000 for val in [self.buckling_input.panel.stiffener.web_height, self.buckling_input.panel.stiffener.web_th, self.buckling_input.panel.plate.thickness, self.buckling_input.panel.stiffener.flange_th,
                                                            self.buckling_input.panel.stiffener.flange_width]]
        h_stf = (self.buckling_input.panel.stiffener.web_height+self.buckling_input.panel.stiffener.flange_th)*1000
        de_gr = 0
        tw_gr = self.buckling_input.panel.stiffener.web_th * 1000
        hf_ctr = h_stf-0.5*tf if self.buckling_input.panel.stiffener.type not in ['L','L-bulb'] else h_stf - de_gr - 0.5 * tf
        bf_ctr = 0 if self.buckling_input.panel.stiffener.type == 'T' else 0.5 * (tf - tw_gr)
        beta = 0.5
        gamma = (1 + math.sqrt(3 + 12 * beta)) / 4

        Af = 0 if self.buckling_input.panel.stiffener.type == 'FB' else bf * tf

        if 75 <= angle <= 90:
            zpl = (hw * tw * (hw + tp) / 2000) + ((2 * gamma - 1) * Af * ((hf_ctr + tp / 2)) / 1000)
        elif angle < 75:
            zpl = (hw * tw * (hw + tp) / 2000)+\
                  ((2 * gamma - 1) * Af * ((hf_ctr + tp / 2) * math.sin(angle_rad) - bf_ctr * math.cos(angle_rad)) / 1000)
        else:
            raise ValueError(f"The value of the angle {str(angle)} should be between 0deg and 90deg.")

        return zpl


    def get_dnv_min_section_modulus(self, design_pressure_kpa: float, printit: bool=False) -> float:
        """
        Section modulus according to DNV rules
        Parameters:
        -----------
        design_pressure_kpa : float
            Design pressure in kPa
        printit : float, optional
            Print the values to the console

        Returns:
        --------
        float
            The minimum required section modulus
        """
        design_pressure = design_pressure_kpa
        fy = self.buckling_input.panel.plate.material.strength / 1e6
        fyd = fy / self.buckling_input.panel.plate.material.mat_factor

        sigma_y = self.buckling_input.stress.sigma_y2 + (self.buckling_input.stress.sigma_y1 - self.buckling_input.stress.sigma_y2)\
                                       *(min(0.25 * self.buckling_input.panel.plate.span, 0.5 * self.buckling_input.panel.plate.spacing) / self.buckling_input.panel.plate.span)
        sig_x1 = self.buckling_input.stress.sigma_x1
        sig_x2 = self.buckling_input.stress.sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd =max(sig_x1 , sig_x2)

        sigma_jd = math.sqrt(math.pow(sigxd, 2) + math.pow(sigma_y, 2) -
                             sigxd * sigma_y + 3 * math.pow(self.buckling_input.stress.tauxy, 2))

        sigma_pd2 = fyd - sigma_jd  # design_bending_stress_mpa

        kps = self.buckling_input.calc_props.stf_kps  # 1 is clamped, 0.9 is simply supported.
        km_sides = min(self.buckling_input.calc_props.km1, self.buckling_input.calc_props.km3)  # see table 3 in DNVGL-OS-C101 (page 62)
        km_middle = self.buckling_input.calc_props.km2  # see table 3 in DNVGL-OS-C101 (page 62)

        Zs = ((math.pow(self.buckling_input.panel.plate.span, 2) * self.buckling_input.panel.plate.spacing * design_pressure) /
              (min(km_middle, km_sides) * (sigma_pd2) * kps)) * math.pow(10, 6)
        
        if printit:
            print('Sigma y1', self.buckling_input.stress.sigma_y1, 'Sigma y2', self.buckling_input.stress.sigma_y2, 'Sigma x', self.buckling_input.stress.sigma_x1,
                  'Pressure', design_pressure, 'fy', fy,
                  'Section mod', max(math.pow(15, 3) / math.pow(1000, 3), Zs / math.pow(1000, 3)))
        
        return max(math.pow(15, 3) / math.pow(1000, 3), Zs / math.pow(1000, 3))


    def get_dnv_min_thickness(self, design_pressure_kpa: float) -> float:
        """
        Section modulus according to DNV rules
        Parameters:
        -----------
        design_pressure_kpa : float
            Design pressure in kPa

        Returns:
        --------
        float
            The minimum required thickness in mm
        """
        design_pressure = design_pressure_kpa
        self.buckling_input.panel.plate.span
        sigma_y = self.buckling_input.stress.sigma_y2 + (self.buckling_input.stress.sigma_y1 - self.buckling_input.stress.sigma_y2) \
                                       *(min(0.25*self.buckling_input.panel.plate.span, 0.5 * self.buckling_input.panel.plate.spacing) / self.buckling_input.panel.plate.span)

        sig_x1 = self.buckling_input.stress.sigma_x1
        sig_x2 = self.buckling_input.stress.sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd =max(sig_x1 , sig_x2)

        sigma_jd = math.sqrt(math.pow(sigxd, 2) + math.pow(sigma_y, 2) -
                             sigxd * sigma_y + 3 * math.pow(self.buckling_input.stress.tauxy, 2))

        fy = self.buckling_input.panel.plate.material.strength / 1e6
        fyd = fy / self.buckling_input.panel.plate.material.mat_factor
        sigma_pd1 = min(1.3 * (fyd - sigma_jd), fyd)
        sigma_pd1 = abs(sigma_pd1)

        if self.category == 'secondary':
            t0 = 5
        else:
            t0 = 7

        t_min = (14.3 * t0) / math.sqrt(fyd)

        ka = math.pow(1.1 - 0.25  * self.buckling_input.panel.plate.spacing / self.buckling_input.panel.plate.span, 2)

        if ka > 1:
            ka = 1
        elif ka < 0.72:
            ka = 0.72

        assert sigma_pd1 > 0, 'sigma_pd1 must be negative | current value is: ' + str(sigma_pd1)
        assert self.buckling_input.calc_props.plate_kpp is not None, 'Fixation parameters must be set.'
        t_min_bend = (15.8 * ka * self.buckling_input.panel.plate.spacing * math.sqrt(design_pressure)) / \
                     math.sqrt(sigma_pd1 *self.buckling_input.calc_props.plate_kpp)

        if self.lat_press:
            return max(t_min, t_min_bend)
        else:
            return t_min


    def get_minimum_shear_area(self, pressure: float) -> float:
        """
        Calculating minimum section area according to ch 6.4.4.
        Parameters:
        -----------
        pressure : float
            Design pressure in kPa

        Returns:
        --------
        float
            The minimum required shear area in m^2
        """
        #print('SIGMA_X ', self._sigma_x1)
        l = self.buckling_input.panel.plate.span
        s = self.buckling_input.panel.plate.spacing
        fy = self.buckling_input.panel.plate.material.strength

        fyd = (fy / self.buckling_input.panel.plate.material.mat_factor) / 1e6 # yield strength
        sig_x1 = self.buckling_input.stress.sigma_x1
        sig_x2 = self.buckling_input.stress.sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd =max(sig_x1 , sig_x2)

        taupds = 0.577 * math.sqrt(math.pow(fyd, 2) - math.pow(sigxd, 2))

        As = ((l * s * pressure) / (2 * taupds)) * math.pow(10, 3)

        return As / math.pow(1000, 2)


    def is_acceptable_sec_mod(self, section_moduli: list[float], pressure: float) -> bool:
        """
        Checking if the result is accepable.
        Parameters:
        -----------
        section_moduli : list[float]
            A list of section modulus in mm^4????
        pressure : floatsection_module
            Design pressure in kPa

        Returns:
        --------
        bool
            True if the provided section modulus satisfies the DNV requirements.
        """

        # ideally the section modulus is calculated in this function and compared.
        return min(section_moduli) >= self.get_dnv_min_section_modulus(pressure)


    def is_acceptable_shear_area(self, shear_area: float, pressure: float) -> bool:
        """
        Checking if the shear area is acceptable according DNV.
        Parameters:
        -----------
        shear_area : float
            Shear area in m^2
        pressure : floatsection_module
            Design pressure in kPa

        Returns:
        --------
        bool
            True if the provided shear area satisfies the DNV requirements.
        """

        return shear_area >= self.get_minimum_shear_area(pressure)


    def is_acceptable_pl_thk(self, design_pressure: float) -> float:
        """
        Checking if the plate thickness is acceptable according DNV.
        Parameters:
        -----------
        design_pressure : floatsection_module
            Design pressure in kPa

        Returns:
        --------
        bool
            True if the plate thickness satisfies the DNV requirements.
        """

        return self.get_dnv_min_thickness(design_pressure) <= self.buckling_input.panel.plate.thickness * 1000


    def getplate_efficent_b(self,design_lat_press=0,axial_stress=50,
                                 trans_stress_small=100,trans_stress_large=100):
        '''
        Simple buckling calculations according to DNV-RP-C201
        :return:
        '''
        raise NotImplementedError("Not implemented for scantling. Use the buckling functionality instead")


    def buckling_localstiffener(self):
        '''
        Local requirements for stiffeners. Chapter 9.11.
        :return:
        '''
        raise NotImplementedError("Not implemented for scantling. Use the buckling functionality instead")


    def get_special_provisions_results(self):
        '''
        Special provisions for plating and stiffeners in steel structures.\n
        Return a dictionary:\n
        \n
        'Plate thickness' : The thickness of plates shall not be less than this check.\n
        'Stiffener section modulus' : The section modulus for longitudinals, beams, frames and other stiffeners\n
                                      subjected to lateral pressure shall not be less than this check.\n
        'Stiffener shear area' : The shear area of the plate/stiffener shall not be less than this ckeck.\n
        :return: minium dimensions and actual dimensions for the current structure in mm/mm^2/mm^3
        :rtype: dict
        '''
        min_pl_thk = self.get_dnv_min_thickness(design_pressure_kpa=self.buckling_input.pressure * 1000)
        min_sec_mod = self.get_dnv_min_section_modulus(design_pressure_kpa=self.buckling_input.pressure * 1000, printit=False) * 1000**3
        min_area = self.get_minimum_shear_area(pressure=self.buckling_input.pressure * 1000) * 1000**2  

        this_pl_thk = self.buckling_input.panel.plate.thickness
        if self.buckling_input.panel.stiffener is not None:
            this_secmod = self.buckling_input.panel.stiffener.get_section_modulus()
            this_area = self.buckling_input.panel.stiffener.get_shear_area() * 1000**2
            return {'Plate thickness':{'minimum': min_pl_thk, 'actual': this_pl_thk},
                    'Stiffener section modulus': {'minimum': min_sec_mod, 'actual': min(this_secmod)* 1000**3},
                    'Stiffener shear area': {'minimum': min_area, 'actual': this_area}}
        else:
            return {'Plate thickness':{'minimum': min_pl_thk, 'actual': this_pl_thk}}
