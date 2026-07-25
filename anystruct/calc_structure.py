'''
Structural calculation classes.

The buckling calculation classes (Structure, CalcScantlings,
AllStructure, Shell, CylinderAndCurvedPlate, PULSpanel) are provided by
the standalone ANYbuckling package and re-exported here so existing
imports keep working. Only the fatigue calculation remains in this
module.
'''
from scipy.special import gammaln
from scipy.stats import gamma as gammadist
import numpy as np
import os, time, datetime, json, random, math
from scipy.optimize import minimize

from anybuckling.prescriptive.plates import AllStructure, CalcScantlings, Structure
from anybuckling.prescriptive.cylinders import CylinderAndCurvedPlate, Shell
from anybuckling.puls.panel import PULSpanel

try:
    import anystruct.helper as hlp
    import anystruct.SN_curve_parameters as snc
except ModuleNotFoundError:
    import ANYstructure.anystruct.helper as hlp
    import ANYstructure.anystruct.SN_curve_parameters as snc

class CalcFatigue(Structure):
    '''
    This Class does the calculations for the plate fields. 
    Input is a structure object (getters from the Structure Class)
    '''
    def __init__(self, main_dict: dict, fatigue_dict: dict=None):
        super(CalcFatigue, self).__init__(main_dict, fatigue_dict)
        if fatigue_dict is not None:
            self._sn_curve = fatigue_dict['SN-curve']
            self._acc = fatigue_dict['Accelerations']
            self._weibull = fatigue_dict['Weibull']
            self._period = fatigue_dict['Period']
            self._k_factor = fatigue_dict['SCF']
            self._corr_loc = fatigue_dict['CorrLoc']
            self._no_of_cycles = fatigue_dict['n0']
            self._design_life = fatigue_dict['Design life']
            self._fraction = fatigue_dict['Fraction']
            self._case_order = fatigue_dict['Order']
            try:
                self._dff = fatigue_dict['DFF']
            except KeyError:
                self._dff = 2

            self.fatigue_dict = fatigue_dict

    def get_sn_curve(self):
        return self._sn_curve

    def __get_sigma_ext(self, int_press):
        return -0.5*int_press* ((self._spacing / (self._plate_th))**2) * (self._k_factor/1000**2)

    def __get_sigma_int(self, ext_press):
        return 0.5*ext_press*((self._spacing/(self._plate_th))**2) * (self._k_factor/1000**2)

    def __get_range(self, idx, int_press, ext_press):
        return 2*math.sqrt(math.pow(self.__get_sigma_ext(ext_press), 2) +
                           math.pow(self.__get_sigma_int(int_press), 2) +
                           2*self._corr_loc[idx]*self.__get_sigma_ext(ext_press)
                           *self.__get_sigma_int(int_press))

    def __get_stress_fraction(self,idx, int_press, ext_press):
        return self.__get_range(idx, int_press, ext_press) / \
               math.pow(math.log(self._no_of_cycles), 1/self._weibull[idx])

    def __get_gamma1(self,idx):
        return math.exp(gammaln(snc.get_paramter(self._sn_curve,'m1')/self._weibull[idx] + 1))

    def __get_gamma2(self,idx):
        return math.exp(gammaln(snc.get_paramter(self._sn_curve, 'm2') / self._weibull[idx] + 1))

    def get_damage_slope1(self, idx, curve, int_press=0, ext_press=0):
        m1, log_a1, k, slope = snc.get_paramter(curve,'m1'), snc.get_paramter(curve,'log a1'),\
                               snc.get_paramter(curve,'k'), snc.get_paramter(curve,'slope')
        cycles = self._design_life*365*24*3600/self._period[idx]
        thk_eff = math.log10(max(1,self._plate_th/0.025)) * k
        slope_ch = math.exp( math.log( math.pow(10, log_a1-m1*thk_eff)/slope) / m1)
        gamma1 = self.__get_gamma1(idx)
        weibull = self._weibull[idx]
        stress_frac = self.__get_stress_fraction(idx, int_press, ext_press)
        # print('Internal pressure: ', int_press)
        # print('External pressure: ', ext_press)
        # finding GAMMADIST
        if stress_frac == 0:
            return 0

        x, alpha = math.pow(slope_ch/stress_frac, weibull),1 + m1/weibull
        gamma_val = gammadist.cdf(x,alpha)
        return cycles / math.pow(10, log_a1-m1*thk_eff) * math.pow(stress_frac, m1)*gamma1*(1-gamma_val)\
               *self._fraction[idx]

    def get_damage_slope2(self, idx, curve, int_press, ext_press):
        m2, log_m2, k, slope = snc.get_paramter(curve,'m2'), snc.get_paramter(curve,'log a2'),\
                               snc.get_paramter(curve,'k'), snc.get_paramter(curve,'slope')
        cycles = self._design_life*365*24*3600/self._period[idx]
        thk_eff = math.log10(max(1,self._plate_th/0.025)) * k
        slope_ch = math.exp( math.log( math.pow(10, log_m2-m2*thk_eff)/slope) / m2)
        gammm2 = self.__get_gamma2(idx)
        weibull = self._weibull[idx]
        stress_frac = self.__get_stress_fraction(idx, int_press, ext_press)

        # finding GAMMADIST
        if stress_frac == 0:
            return 0
        x, alpha = math.pow(slope_ch/stress_frac, weibull),1 + m2/weibull
        gamma_val = gammadist.cdf(x,alpha)

        return cycles / math.pow(10, log_m2-m2*thk_eff) * math.pow(stress_frac, m2)*gammm2*(gamma_val)\
               *self._fraction[idx]

    def get_total_damage(self, int_press=(0, 0, 0), ext_press=(0, 0, 0)):
        damage = 0

        for idx in range(3):
            if self._fraction[idx] != 0 and self._period[idx] != 0:
                damage += self.get_damage_slope1(idx,self._sn_curve, int_press[idx], ext_press[idx]) + \
                          self.get_damage_slope2(idx,self._sn_curve, int_press[idx], ext_press[idx])

        return damage

    def set_commmon_properties(self, fatigue_dict: dict):
        ''' Setting the fatiuge properties. '''
        #self._sn_curve, self.fatigue_dict['SN-curve'] = fatigue_dict['SN-curve'], fatigue_dict['SN-curve']
        self._acc, self.fatigue_dict['Accelerations'] = fatigue_dict['Accelerations'], fatigue_dict['Accelerations']
        #self._weibull, self.fatigue_dict['Weibull'] = fatigue_dict['Weibull'], fatigue_dict['Weibull']
        #self._period, self.fatigue_dict['Period'] = fatigue_dict['Period'], fatigue_dict['Period']
        #self._k_factor, self.fatigue_dict['SCF'] = fatigue_dict['SCF'], fatigue_dict['SCF']
        #self._corr_loc, self.fatigue_dict['CorrLoc'] = fatigue_dict['CorrLoc'], fatigue_dict['CorrLoc']
        self._no_of_cycles, self.fatigue_dict['n0'] = fatigue_dict['n0'], fatigue_dict['n0']
        self._design_life, self.fatigue_dict['Design life'] = fatigue_dict['Design life'], fatigue_dict['Design life']
        self._fraction, self.fatigue_dict['Fraction'] = fatigue_dict['Fraction'], fatigue_dict['Fraction']
        #self._case_order, self.fatigue_dict['Order'] = fatigue_dict['Order'], fatigue_dict['Order']
        self._dff, self.fatigue_dict['DFF'] = fatigue_dict['DFF'], fatigue_dict['DFF']


    def set_fatigue_properties(self, fatigue_dict: dict):
        ''' Setting the fatiuge properties. '''
        self._sn_curve, self.fatigue_dict['SN-curve'] = fatigue_dict['SN-curve'], fatigue_dict['SN-curve']
        self._acc, self.fatigue_dict['Accelerations'] = fatigue_dict['Accelerations'], fatigue_dict['Accelerations']
        self._weibull, self.fatigue_dict['Weibull'] = fatigue_dict['Weibull'], fatigue_dict['Weibull']
        self._period, self.fatigue_dict['Period'] = fatigue_dict['Period'], fatigue_dict['Period']
        self._k_factor, self.fatigue_dict['SCF'] = fatigue_dict['SCF'], fatigue_dict['SCF']
        self._corr_loc, self.fatigue_dict['CorrLoc'] = fatigue_dict['CorrLoc'], fatigue_dict['CorrLoc']
        self._no_of_cycles, self.fatigue_dict['n0'] = fatigue_dict['n0'], fatigue_dict['n0']
        self._design_life, self.fatigue_dict['Design life'] = fatigue_dict['Design life'], fatigue_dict['Design life']
        self._fraction, self.fatigue_dict['Fraction'] = fatigue_dict['Fraction'], fatigue_dict['Fraction']
        self._case_order, self.fatigue_dict['Order'] = fatigue_dict['Order'], fatigue_dict['Order']
        self._dff, self.fatigue_dict['DFF'] = fatigue_dict['DFF'], fatigue_dict['DFF']

    def get_fatigue_properties(self):
        ''' Returning properties as a dictionary '''
        return self.fatigue_dict

    def get_accelerations(self):
        ''' Returning tuple of accelerattions.'''
        return self._acc

    def get_dff(self):
        return self._dff

    def get_design_life(self):
        return self._design_life

