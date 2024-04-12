import math
from typing import List, Tuple

from pydantic import BaseModel
from scipy.special import gammaln
from scipy.stats import gamma as gammadist

from .stiffened_panel import StiffenedPanel

try:
    import anystruct.helper as hlp
    import anystruct.SN_curve_parameters as snc
except ModuleNotFoundError:
    import ANYstructure.anystruct.helper as hlp # type: ignore
    import ANYstructure.anystruct.SN_curve_parameters as snc # type: ignore


class FatigueInput(BaseModel):
    sn_curve: str
    k_factor: float # scf
    design_life: float
    no_of_cycles: float
    weibull: Tuple[float]
    period: Tuple[float]
    fraction: Tuple[float]
    corr_loc: Tuple[float]
    case_order: Tuple[str]
    acc: Tuple[float]
    dff: float = 2.0


class CalcFatigue(BaseModel):
    '''
    This Class does the calculations for the plate fields. 
    Input is a StiffenedPanel object and a FatigueInput object.
    '''

    panel: StiffenedPanel
    fatigue_data: FatigueInput


    def get_sn_curve(self):
        return self.fatigue_data.sn_curve


    def get_fatigue_properties(self):
        ''' Returning properties as a FatigueInput object.'''
        return self.fatigue_data


    def get_accelerations(self):
        ''' Returning tuple of accelerattions.'''
        return self.fatigue_data.acc


    def get_dff(self):
        return self.fatigue_data.dff


    def get_design_life(self):
        return self.fatigue_data.design_life


    def __get_sigma_ext(self, int_press):
        return -0.5 * int_press * ((self.panel.plate.spacing / (self.panel.plate.thickness))**2) * (self.fatigue_data.k_factor / 1000**2)


    def __get_sigma_int(self, ext_press):
        return 0.5 * ext_press*((self.panel.plate.spacing/(self.panel.plate.thickness))**2) * (self.fatigue_data.k_factor / 1000**2)


    def __get_range(self, idx, int_press, ext_press):
        return 2*math.sqrt(math.pow(self.__get_sigma_ext(ext_press), 2) +
                           math.pow(self.__get_sigma_int(int_press), 2) +
                           2 * self.fatigue_data.corr_loc[idx] * self.__get_sigma_ext(ext_press)
                            * self.__get_sigma_int(int_press))


    def __get_stress_fraction(self,idx, int_press, ext_press):
        return self.__get_range(idx, int_press, ext_press) / \
               math.pow(math.log(self.fatigue_data.no_of_cycles), 1 / self.fatigue_data.weibull[idx])


    def __get_gamma1(self,idx):
        return math.exp(gammaln(snc.get_paramter(self.fatigue_data.sn_curve,'m1') / self.fatigue_data.weibull[idx] + 1))


    def __get_gamma2(self,idx):
        return math.exp(gammaln(snc.get_paramter(self.fatigue_data.sn_curve, 'm2') / self.fatigue_data.weibull[idx] + 1))


    def get_damage_slope1(self, idx, curve, int_press=0, ext_press=0):
        m1: float = snc.get_paramter(curve,'m1')
        log_a1: float = snc.get_paramter(curve,'log a1')
        k: float = snc.get_paramter(curve,'k')
        slope: float = snc.get_paramter(curve,'slope')
        cycles: float = self.fatigue_data.design_life * 365 * 24 * 3600 / self.fatigue_data.period[idx]
        thk_eff = math.log10(max(1,self.panel.plate.thickness / 0.025)) * k
        slope_ch = math.exp( math.log( math.pow(10, log_a1 - m1 * thk_eff) / slope) / m1)
        gamma1 = self.__get_gamma1(idx)
        weibull = self.fatigue_data.weibull[idx]
        stress_frac = self.__get_stress_fraction(idx, int_press, ext_press)
        # print('Internal pressure: ', int_press)
        # print('External pressure: ', ext_press)
        # finding GAMMADIST
        if stress_frac == 0:
            return 0

        x, alpha = math.pow(slope_ch/stress_frac, weibull),1 + m1/weibull
        gamma_val = gammadist.cdf(x,alpha)
        return cycles / math.pow(10, log_a1-m1*thk_eff) * math.pow(stress_frac, m1)*gamma1*(1-gamma_val)\
               *self.fatigue_data.fraction[idx]


    def get_damage_slope2(self, idx, curve, int_press, ext_press):
        m2: float = snc.get_paramter(curve,'m2')
        log_m2: float = snc.get_paramter(curve,'log a2')
        k: float = snc.get_paramter(curve,'k')
        slope: float = snc.get_paramter(curve,'slope')
        cycles: float = self.fatigue_data.design_life * 365 * 24 * 3600 / self.fatigue_data.period[idx]
        # I updated the reference thickness to 0.025 instead of 25
        thk_eff = math.log10(max(1,self.panel.plate.thickness / 0.025)) * k
        slope_ch = math.exp( math.log( math.pow(10, log_m2 - m2 * thk_eff) / slope) / m2)
        gammm2 = self.__get_gamma2(idx)
        weibull = self.fatigue_data.weibull[idx]
        stress_frac = self.__get_stress_fraction(idx, int_press, ext_press)

        # finding GAMMADIST
        if stress_frac == 0:
            return 0
        x: float = math.pow(slope_ch/stress_frac, weibull)
        alpha: float = 1 + m2/weibull
        gamma_val = gammadist.cdf(x,alpha)

        return cycles / math.pow(10, log_m2-m2*thk_eff) * math.pow(stress_frac, m2) * gammm2 * (gamma_val) \
               * self.fatigue_data.fraction[idx]


    def get_total_damage(self, int_press=(0, 0, 0), ext_press=(0, 0, 0)):
        damage = 0

        for idx in range(3):
            if self.fatigue_data.fraction[idx] != 0 and self.fatigue_data.period[idx] != 0:
                damage += self.get_damage_slope1(idx,self.fatigue_data.sn_curve, int_press[idx], ext_press[idx]) + \
                          self.get_damage_slope2(idx,self.fatigue_data.sn_curve, int_press[idx], ext_press[idx])

        return damage
