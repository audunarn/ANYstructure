from scipy.special import gammaln
from scipy.stats import gamma as gammadist
import numpy as np
import ANYstructure_local.helper as hlp
import os, time, datetime, json, random, math
import ANYstructure_local.SN_curve_parameters as snc

class Structure():
    '''
    Setting the properties for the plate and the stiffener. Takes a dictionary as argument.
    '''
    def __init__(self, main_dict, *args, **kwargs):
        super(Structure,self).__init__()
        self._main_dict = main_dict
        if 'panel or shell' not in main_dict.keys():
            self._panel_or_shell = 'panel'
        else:
            self._panel_or_shell = main_dict['panel or shell'][0]
        self._plate_th = main_dict['plate_thk'][0]
        self._web_height = main_dict['stf_web_height'][0]
        self._web_th = main_dict['stf_web_thk'][0]
        self._flange_width = main_dict['stf_flange_width'][0]
        self._flange_th = main_dict['stf_flange_thk'][0]
        self._mat_yield = main_dict['mat_yield'][0]
        self._mat_factor = main_dict['mat_factor'][0]
        self._span = main_dict['span'][0]
        self._spacing = main_dict['spacing'][0]
        self._structure_type = main_dict['structure_type'][0]
        self._sigma_y1=main_dict['sigma_y1'][0]
        self._sigma_y2=main_dict['sigma_y2'][0]
        self._sigma_x=main_dict['sigma_x'][0]
        self._tauxy=main_dict['tau_xy'][0]
        self._plate_kpp = main_dict['plate_kpp'][0]
        self._stf_kps = main_dict['stf_kps'][0]
        self._km1 = main_dict['stf_km1'][0]
        self._km2 = main_dict['stf_km2'][0]
        self._km3 = main_dict['stf_km3'][0]
        self._stiffener_type=main_dict['stf_type'][0]
        self._structure_types = main_dict['structure_types'][0]
        self._dynamic_variable_orientation = None
        if self._structure_type in self._structure_types['vertical']:
            self._dynamic_variable_orientation = 'z - vertical'
        elif self._structure_type in self._structure_types['horizontal']:
            self._dynamic_variable_orientation = 'x - horizontal'
        self._puls_method = main_dict['puls buckling method'][0]
        self._puls_boundary = main_dict['puls boundary'][0]
        self._puls_stf_end = main_dict['puls stiffener end'][0]
        self._puls_sp_or_up = main_dict['puls sp or up'][0]
        self._puls_up_boundary = main_dict['puls up boundary'][0]

        self._zstar_optimization = main_dict['zstar_optimization'][0]
        try:
            self._girder_lg=main_dict['girder_lg'][0]
        except KeyError:
            self._girder_lg = 10
        try:
            self._pressure_side = main_dict['press_side'][0]
        except KeyError:
            self._pressure_side = 'p'

    # Property decorators are used in buckling of shells. IN mm!
    @property # in mm
    def hw(self):
        return self._web_height * 1000
    @hw.setter # in mm
    def hw(self, val):
        self._web_height = val / 1000
    @property # in mm
    def tw(self):
        return self._web_th * 1000
    @tw.setter # in mm
    def tw(self, val):
        self._web_th = val / 1000
    @property # in mm
    def b(self):
        return self._flange_width * 1000
    @b.setter # in mm
    def b(self, val):
        self._flange_width = val / 1000
    @property # in mm
    def tf(self):
        return self._flange_th * 1000
    @tf.setter # in mm
    def tf(self, val):
        self._flange_th = val / 1000
    @property  # in mm
    def s(self):
        return self._spacing* 1000
    @s.setter  # in mm
    def s(self, val):
        self._spacing = val / 1000
    @property  # in mm
    def t(self):
        return self._plate_th* 1000
    @t.setter  # in mm
    def t(self, val):
        self._plate_th = val / 1000
    @property  # in mm
    def panel_or_shell(self):
        return self._panel_or_shell
    @panel_or_shell.setter  # in mm
    def panel_or_shell(self, val):
        self._panel_or_shell = val

    def __str__(self):
        '''
        Returning all properties.
        '''
        return \
            str(
            '\n Plate field span:              ' + str(round(self._span,3)) + ' meters' +
            '\n Stiffener spacing:             ' + str(self._spacing*1000)+' mm'+
            '\n Plate thickness:               ' + str(self._plate_th*1000)+' mm'+
            '\n Stiffener web height:          ' + str(self._web_height*1000)+' mm'+
            '\n Stiffener web thickness:       ' + str(self._web_th*1000)+' mm'+
            '\n Stiffener flange width:        ' + str(self._flange_width*1000)+' mm'+
            '\n Stiffener flange thickness:    ' + str(self._flange_th*1000)+' mm'+
            '\n Material yield:                ' + str(self._mat_yield/1e6)+' MPa'+
            '\n Structure/stiffener type:      ' + str(self._structure_type)+'/'+(self._stiffener_type)+
            '\n Dynamic load varible_          ' + str(self._dynamic_variable_orientation)+
            '\n Plate fixation paramter,kpp:   ' + str(self._plate_kpp) + ' ' +
            '\n Stf. fixation paramter,kps:    ' + str(self._stf_kps) + ' ' +
            '\n Global stress, sig_y1/sig_y2:  ' + str(round(self._sigma_y1,3))+'/'+str(round(self._sigma_y2,3))+ ' MPa' +
            '\n Global stress, sig_x:          ' + str(round(self._sigma_x,3)) + ' MPa' +
            '\n Global shear, tau_xy:          ' + str(round(self._tauxy,3)) + ' MPa' +
            '\n km1,km2,km3:                   ' + str(self._km1)+'/'+str(self._km2)+'/'+str(self._km3)+
            '\n Pressure side (p-plate/s-stf): ' + str(self._pressure_side) + ' ')

    def get_beam_string(self):
        ''' Returning a string. '''
        base_name = self._stiffener_type+ '_' + str(round(self._web_height*1000, 0)) + 'x' + \
                   str(round(self._web_th*1000, 0))
        if self._stiffener_type == 'FB':
            ret_str = base_name
        else:
            ret_str = base_name + '__' + str(round(self._flange_width*1000, 0)) + 'x' + \
                      str(round(self._flange_th*1000, 0))

        ret_str = ret_str.replace('.', '_')

        return ret_str

    def get_structure_types(self):
        return self._structure_types

    def get_z_opt(self):
        return self._zstar_optimization

    def get_puls_method(self):
        return self._puls_method

    def get_puls_boundary(self):
        return self._puls_boundary

    def get_puls_stf_end(self):
        return self._puls_stf_end

    def get_puls_sp_or_up(self):
        return self._puls_sp_or_up

    def get_puls_up_boundary(self):
        return self._puls_up_boundary

    def get_one_line_string(self):
        ''' Returning a one line string. '''
        return 'pl_'+str(round(self._spacing*1000, 1))+'x'+str(round(self._plate_th*1000,1))+' stf_'+self._stiffener_type+\
               str(round(self._web_height*1000,1))+'x'+str(round(self._web_th*1000,1))+'+'\
               +str(round(self._flange_width*1000,1))+'x'+\
               str(round(self._flange_th*1000,1))

    def get_report_stresses(self):
        'Return the stresses to the report'
        return 'sigma_y1: '+str(round(self._sigma_y1,1))+' sigma_y2: '+str(round(self._sigma_y2,1))+ \
               ' sigma_x: ' + str(round(self._sigma_x,1))+' tauxy: '+ str(round(self._tauxy,1))

    def get_extended_string(self):
        ''' Some more information returned. '''
        return 'span: '+str(round(self._span,4))+' structure type: '+ self._structure_type + ' stf. type: ' + \
               self._stiffener_type + ' pressure side: ' + self._pressure_side
    
    def get_sigma_y1(self):
        '''
        Return sigma_y1
        :return:
        '''
        return self._sigma_y1
    def get_sigma_y2(self):
        '''
        Return sigma_y2
        :return:
        '''
        return self._sigma_y2
    def get_sigma_x(self):
        '''
        Return sigma_x
        :return:
        '''
        return self._sigma_x
    def get_tau_xy(self):
        '''
        Return tau_xy
        :return:
        '''
        return self._tauxy
    def get_s(self):
        '''
        Return the spacing
        :return:
        '''
        return self._spacing
    def get_pl_thk(self):
        '''
        Return the plate thickness
        :return:
        '''
        return self._plate_th
    def get_web_h(self):
        '''
        Return the web heigh
        :return:
        '''
        return self._web_height
    def get_web_thk(self):
        '''
        Return the spacing
        :return:
        '''
        return self._web_th
    def get_fl_w(self):
        '''
        Return the flange width
        :return:
        '''
        return self._flange_width
    def get_fl_thk(self):
        '''
        Return the flange thickness
        :return:
        '''
        return self._flange_th
    def get_fy(self):
        '''
        Return material yield
        :return:
        '''
        return self._mat_yield
    def get_mat_factor(self):
        return self._mat_factor
    def get_span(self):
        '''
        Return the span
        :return:
        '''
        return self._span
    def get_lg(self):
        '''
        Return the girder length
        :return:
        '''
        return self._girder_lg
    def get_kpp(self):
        '''
        Return var
        :return:
        '''
        return self._plate_kpp
    def get_kps(self):
        '''
        Return var
        :return:
        '''
        return self._stf_kps
    def get_km1(self):
        '''
        Return var
        :return:
        '''
        return self._km1
    def get_km2(self):
        '''
        Return var
        :return:
        '''
        return self._km2
    def get_km3(self):
        '''
        Return var
        :return:
        '''
        return self._km3
    def get_side(self):
        '''
        Return the checked pressure side.
        :return: 
        '''
        return self._pressure_side
    def get_tuple(self):
        ''' Return a tuple of the plate stiffener'''
        return (self._spacing, self._plate_th, self._web_height, self._web_th, self._flange_width,
                self._flange_th, self._span, self._girder_lg, self._stiffener_type)

    def get_section_modulus(self, efficient_se = None, dnv_table = False):
        '''
        Returns the section modulus.
        :param efficient_se: 
        :return: 
        '''
        #Plate. When using DNV table, default values are used for the plate
        b1 = self._spacing if efficient_se==None else efficient_se
        tf1 = self._plate_th

        #Stiffener
        tf2 = self._flange_th
        b2 = self._flange_width
        h = self._flange_th+self._web_height+self._plate_th
        tw = self._web_th
        hw = self._web_height

        # cross section area
        Ax = tf1 * b1 + tf2 * b2 + hw * tw

        assert Ax != 0, 'Ax cannot be 0'
        # distance to center of gravity in z-direction
        ez = (tf1 * b1 * tf1 / 2 + hw * tw * (tf1 + hw / 2) + tf2 * b2 * (tf1 + hw + tf2 / 2)) / Ax

        #ez = (tf1 * b1 * (h - tf1 / 2) + hw * tw * (tf2 + hw / 2) + tf2 * b2 * (tf2 / 2)) / Ax
        # moment of inertia in y-direction (c is centroid)

        Iyc = (1 / 12) * (b1 * math.pow(tf1, 3) + b2 * math.pow(tf2, 3) + tw * math.pow(hw, 3))
        Iy = Iyc + (tf1 * b1 * math.pow(tf1 / 2, 2) + tw * hw * math.pow(tf1+hw / 2, 2) +
             tf2 * b2 * math.pow(tf1+hw+tf2 / 2, 2)) - Ax * math.pow(ez, 2)

        # elastic section moduluses y-axis
        Wey1 = Iy / (h - ez)
        Wey2 = Iy / ez

        return Wey1, Wey2
    def get_plasic_section_modulus(self):
        '''
        Returns the plastic section modulus
        :return:
        '''
        tf1 = self._plate_th
        tf2 = self._flange_th
        b1 = self._spacing
        b2 = self._flange_width
        h = self._flange_th+self._web_height+self._plate_th
        tw = self._web_th
        hw = self._web_height

        Ax = tf1 * b1 + tf2 * b2 + (h-tf1-tf2) * tw

        ezpl = (Ax/2-b1*tf1)/tw+tf1

        az1 = h-ezpl-tf1
        az2 = ezpl-tf2

        Wy1 = b1*tf1*(az1+tf1/2) + (tw/2)*math.pow(az1,2)
        Wy2 = b2*tf2*(az2+tf2/2)+(tw/2)*math.pow(az2,2)

        return Wy1+Wy2
    def get_shear_center(self):
        '''
        Returning the shear center
        :return:
        '''
        tf1 = self._plate_th
        tf2 = self._flange_th
        b1 = self._spacing
        b2 = self._flange_width
        h = self._flange_th+self._web_height+self._plate_th
        tw = self._web_th
        hw = self._web_height
        Ax = tf1 * b1 + tf2 * b2 + (h-tf1-tf2) * tw
        # distance to center of gravity in z-direction
        ez = (b2*tf2*tf2/2 + tw*hw*(tf2+hw/2)+tf1*b1*(tf2+hw+tf1/2)) / Ax

        # Shear center:
        # moment of inertia, z-axis
        Iz1 = tf1 * math.pow(b1, 3)
        Iz2 = tf2 * math.pow(b2, 3)
        ht = h - tf1 / 2 - tf2 / 2
        return (Iz1 * ht) / (Iz1 + Iz2) + tf2 / 2 - ez

    def get_moment_of_intertia(self, efficent_se=None, only_stf = False, tf1 = None):
        '''
        Returning moment of intertia.
        :return:
        '''
        if only_stf:
            tf1 = 0
            b1 = 0
        else:
            tf1 = self._plate_th if tf1 == None else tf1
            b1 = self._spacing if efficent_se==None else efficent_se

        h = self._flange_th+self._web_height+tf1
        tw = self._web_th
        hw = self._web_height
        tf2 = self._flange_th
        b2 = self._flange_width

        Ax = tf1 * b1 + tf2 * b2 + hw * tw
        Iyc = (1 / 12) * (b1 * math.pow(tf1, 3) + b2 * math.pow(tf2, 3) + tw * math.pow(hw, 3))
        ez = (tf1 * b1 * (h - tf1 / 2) + hw * tw * (tf2 + hw / 2) + tf2 * b2 * (tf2 / 2)) / Ax
        Iy = Iyc + (tf1 * b1 * math.pow(tf2 + hw + tf1 / 2, 2) + tw * hw * math.pow(tf2 + hw / 2, 2) +
             tf2 * b2 * math.pow(tf2 / 2, 2)) - Ax * math.pow(ez, 2)

        return Iy

    def get_Iz_moment_of_inertia(self):
        tw = self._web_th * 1000
        hw = self._web_height * 1000
        tf2 = self._flange_th * 1000
        b2 = self._flange_width * 1000

        Af = b2*tf2
        Aw = tw*hw
        if self._stiffener_type == 'FB':
            Iz = math.pow(tw,3)*hw/12
        else:
            Iz = (Af*math.pow(b2,2)/12) + math.pow(self.get_flange_eccentricity(),2) * (Af/(1+Af/Aw))
        return Iz

    def get_moment_of_interia_iacs(self, efficent_se=None, only_stf = False, tf1 = None):
        if only_stf:
            tf1 = 0
            b1 = 0
        else:
            tf1 = self._plate_th if tf1 == None else tf1
            b1 = self._spacing if efficent_se==None else efficent_se
        h = self._flange_th+self._web_height+tf1
        tw = self._web_th
        hw = self._web_height
        tf2 = self._flange_th
        b2 = self._flange_width

        Af = b2*tf2
        Aw = hw*tw

        ef = hw + tf2/2

        Iy = (Af*math.pow(ef,2)*math.pow(b2,2)/12) * ( (Af+2.6*Aw) / (Af+Aw))
        return Iy

    def get_torsional_moment_venant(self):
        ef = self.get_ef_iacs()*1000
        tf = self._flange_th*1000
        tw = self._web_th*1000
        bf = self._flange_width*1000
        hw = self._web_height*1000

        if self._stiffener_type == 'FB':
            It = ((hw*math.pow(tw,3)/3e4) * (1-0.63*(tw/hw)) )
        else:
            It = ((((ef-0.5*tf)*math.pow(tw,3))/3e4) * (1-0.63*(tw/(ef-0.5*tf))) + ((bf*math.pow(tf,3))/3e4)
                  * (1-0.63*(tf/bf)) )
        # G = 80769.2
        # It2 = (2/3) * (math.pow(tw,3)*hw + bf*math.pow(tf, 3)) *(hw+tf/2)
        # print(It, It2*G)

        return It * 1e4

    def get_polar_moment(self):
        tf = self._flange_th*1000
        tw = self._web_th*1000
        ef = self.get_flange_eccentricity()
        hw = self._web_height*1000
        b = self._flange_width*1000
        
        #Ipo = (A|w*(ef-0.5*tf)**2/3+Af*ef**2)*10e-4 #polar moment of interia in cm^4
        Ipo = (tw/3)*math.pow(hw, 3) + tf*(math.pow(hw+tf/2,2)*b)+(tf/3)*(math.pow(ef+b/2,3)-math.pow(ef-b/2,3))
        return Ipo

    def get_flange_eccentricity(self):
        ecc = 0 if self._stiffener_type in ['FB', 'T'] else self._flange_width / 2 - self._web_th / 2
        return ecc

    def get_ef_iacs(self):

        if self._stiffener_type == 'FB':
            ef = self._web_height
        # elif self._stiffener_type == 'L-bulb':
        #     ef = self._web_height-0.5*self._flange_th
        elif self._stiffener_type in ['L', 'T', 'L-bulb', 'HP-profile', 'HP', 'HP-bulb']:
            ef = self._web_height + 0.5*self._flange_th
        return ef

    def get_stf_cog_eccentricity(self):
        e = (self._web_height * self._web_th * (self._web_height / 2) + self._flange_width * self._flange_th *
             (self._web_height + self._web_th / 2)) / (self._web_height * self._web_th + self._flange_width * self._flange_th)
        return e

    def get_structure_prop(self):
        return self._main_dict

    def get_structure_type(self):
        return self._structure_type

    def get_stiffener_type(self):
        return self._stiffener_type

    def get_shear_area(self):
        '''
        Returning the shear area in [m^2]
        :return:
        '''
        return ((self._flange_th*self._web_th) + (self._web_th*self._plate_th) + (self._web_height*self._web_th))

    def set_main_properties(self, main_dict):
        '''
        Resettting all properties
        :param input_dictionary:
        :return:
        '''

        self._main_dict = main_dict
        self._plate_th = main_dict['plate_thk'][0]
        self._web_height = main_dict['stf_web_height'][0]
        self._web_th = main_dict['stf_web_thk'][0]
        self._flange_width = main_dict['stf_flange_width'][0]
        self._flange_th = main_dict['stf_flange_thk'][0]
        self._mat_yield = main_dict['mat_yield'][0]
        self._mat_factor = main_dict['mat_factor'][0]
        self._span = main_dict['span'][0]
        self._spacing = main_dict['spacing'][0]
        self._structure_type = main_dict['structure_type'][0]
        self._sigma_y1=main_dict['sigma_y1'][0]
        self._sigma_y2=main_dict['sigma_y2'][0]
        self._sigma_x=main_dict['sigma_x'][0]
        self._tauxy=main_dict['tau_xy'][0]
        self._plate_kpp = main_dict['plate_kpp'][0]
        self._stf_kps = main_dict['stf_kps'][0]
        self._km1 = main_dict['stf_km1'][0]
        self._km2 = main_dict['stf_km2'][0]
        self._km3 = main_dict['stf_km3'][0]
        self._stiffener_type=main_dict['stf_type'][0]
        try:
            self._girder_lg=main_dict['girder_lg'][0]
        except KeyError:
            self._girder_lg = 10
        try:
            self._pressure_side = main_dict['press_side'][0]
        except KeyError:
            self._pressure_side = 'p'
        self._zstar_optimization = main_dict['zstar_optimization'][0]
        self._puls_method = main_dict['puls buckling method'][0]
        self._puls_boundary = main_dict['puls boundary'][0]
        self._puls_stf_end  = main_dict['puls stiffener end'][0]
        self._puls_sp_or_up = main_dict['puls sp or up'][0]
        self._puls_up_boundary = main_dict['puls up boundary'][0]
        self._panel_or_shell = main_dict['panel or shell'][0]

    def set_stresses(self,sigy1,sigy2,sigx,tauxy):
        '''
        Setting the global stresses.
        :param sigy1:
        :param sigy2:
        :param sigx:
        :param tauxy:
        :return:
        '''
        self._main_dict['sigma_y1'][0]= sigy1
        self._sigma_y1 = sigy1

        self._main_dict['sigma_y2'][0]= sigy2
        self._sigma_y2  = sigy2

        self._main_dict['sigma_x'][0]= sigx
        self._sigma_x = sigx

        self._main_dict['tau_xy'][0]= tauxy
        self._tauxy  = tauxy

    def get_cross_section_area(self, efficient_se = None, include_plate = True):
        '''
        Returns the cross section area.
        :return:
        '''
        tf1 = self._plate_th if include_plate else 0
        tf2 = self._flange_th
        if include_plate:
            b1 = self._spacing if efficient_se==None else efficient_se
        else:
            b1 = 0
        b2 = self._flange_width
        #h = self._flange_th+self._web_height+self._plate_th
        h = self._web_height
        tw = self._web_th
        #print('Plate: thk', tf1, 's', b1, 'Flange: thk', tf2, 'width', b2, 'Web: thk', tw, 'h', h)
        return tf1 * b1 + tf2 * b2 + h * tw

    def get_cross_section_centroid_with_effective_plate(self, se = None, tf1 = None, include_plate = True):
        '''
        Returns cross section centroid
        :return:
        '''
        # checked with example
        if include_plate:
            tf1 = self._plate_th if tf1 == None else tf1
            b1 = self._spacing if se == None else se
        else:
            tf1 = 0
            b1 = 0
        tf2 = self._flange_th
        b2 = self._flange_width
        tw = self._web_th
        hw = self._web_height
        Ax = tf1 * b1 + tf2 * b2 + hw * tw

        return (tf1 * b1 * tf1/2 + hw * tw * (tf1 + hw / 2) + tf2 * b2 * (tf1+hw+tf2/2)) / Ax

    def get_weight(self):
        '''
        Return the weight.
        :return:
        '''
        return 7850*self._span*(self._spacing*self._plate_th+self._web_height*self._web_th+self._flange_width*self._flange_th)

    def get_weight_width_lg(self):
        '''
        Return the weight including Lg
        :return:
        '''
        pl_area = self._girder_lg*self._plate_th
        stf_area = (self._web_height*self._web_th+self._flange_width*self._flange_th)*(self._girder_lg//self._spacing)
        return (pl_area+stf_area)*7850*self._span

    def set_span(self,span):
        '''
        Setting the span. Used when moving a point.
        :return: 
        '''
        self._span = span
        self._main_dict['span'][0] = span

    def get_puls_input(self, run_type: str = 'SP'):
        if self._stiffener_type == 'FB':
            stf_type = 'F'
        else:
            stf_type = self._stiffener_type
        if self._puls_sp_or_up == 'SP':
            return_dict = {'Identification': None, 'Length of panel': self._span*1000, 'Stiffener spacing': self._spacing*1000,
                            'Plate thickness': self._plate_th*1000,
                          'Number of primary stiffeners': 10,
                           'Stiffener type (L,T,F)': stf_type,
                            'Stiffener boundary': self._puls_stf_end,
                          'Stiff. Height': self._web_height*1000, 'Web thick.': self._web_th*1000,
                           'Flange width': self._flange_width*1000,
                            'Flange thick.': self._flange_th*1000, 'Tilt angle': 0,
                          'Number of sec. stiffeners': 0, 'Modulus of elasticity': 2.1e11/1e6, "Poisson's ratio": 0.3,
                          'Yield stress plate': self._mat_yield/1e6, 'Yield stress stiffener': self._mat_yield/1e6,
                            'Axial stress': 0 if self._puls_boundary == 'GT' else self._sigma_x,
                           'Trans. stress 1': 0 if self._puls_boundary == 'GL' else self._sigma_y1,
                          'Trans. stress 2': 0 if self._puls_boundary == 'GL' else self._sigma_y2,
                           'Shear stress': self._tauxy,
                            'Pressure (fixed)': None, 'In-plane support': self._puls_boundary,
                           'sp or up': self._puls_sp_or_up}
        else:
            boundary = self._puls_up_boundary
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

            return_dict = {'Identification': None, 'Length of plate': self._span*1000, 'Width of c': self._spacing*1000,
                           'Plate thickness': self._plate_th*1000,
                         'Modulus of elasticity': 2.1e11/1e6, "Poisson's ratio": 0.3,
                          'Yield stress plate': self._mat_yield/1e6,
                         'Axial stress 1': 0 if self._puls_boundary == 'GT' else self._sigma_x,
                           'Axial stress 2': 0 if self._puls_boundary == 'GT' else self._sigma_x,
                           'Trans. stress 1': 0 if self._puls_boundary == 'GL' else self._sigma_y1,
                         'Trans. stress 2': 0 if self._puls_boundary == 'GL' else self._sigma_y2,
                           'Shear stress': self._tauxy, 'Pressure (fixed)': None, 'In-plane support': self._puls_boundary,
                         'Rot left': blist[0], 'Rot right': blist[1], 'Rot upper': blist[2], 'Rot lower': blist[3],
                           'sp or up': self._puls_sp_or_up}
        return return_dict

    def get_buckling_ml_input(self, design_lat_press: float = 0, sp_or_up: str = 'SP', alone = True, csr = False):
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

        if self._puls_sp_or_up == 'SP':
            if csr == False:
                this_field =  [self._span * 1000, self._spacing * 1000, self._plate_th * 1000, self._web_height * 1000,
                               self._web_th * 1000, self._flange_width * 1000, self._flange_th * 1000, self._mat_yield / 1e6,
                               self._mat_yield / 1e6,  self._sigma_x, self._sigma_y1, self._sigma_y2, self._tauxy,
                               design_lat_press/1000, stf_type[self._stiffener_type], stf_end[self._puls_stf_end]]
            else:
                this_field =  [self._span * 1000, self._spacing * 1000, self._plate_th * 1000, self._web_height * 1000,
                               self._web_th * 1000, self._flange_width * 1000, self._flange_th * 1000, self._mat_yield / 1e6,
                               self._mat_yield / 1e6,  self._sigma_x, self._sigma_y1, self._sigma_y2, self._tauxy,
                               design_lat_press/1000, stf_type[self._stiffener_type], stf_end[self._puls_stf_end],
                               field_type[self._puls_boundary]]
        else:
            ss_cl_list = list()
            for letter_i in self._puls_up_boundary:
                if letter_i == 'S':
                    ss_cl_list.append(up_boundary['SS'])
                else:
                    ss_cl_list.append(up_boundary['CL'])
            b1, b2, b3, b4 = ss_cl_list
            if csr == False:
                this_field =  [self._span * 1000, self._spacing * 1000, self._plate_th * 1000, self._mat_yield / 1e6,
                               self._sigma_x, self._sigma_y1, self._sigma_y2, self._tauxy, design_lat_press/1000,
                               b1, b2, b3, b4]
            else:
                this_field =  [self._span * 1000, self._spacing * 1000, self._plate_th * 1000, self._mat_yield / 1e6,
                               self._sigma_x, self._sigma_y1, self._sigma_y2, self._tauxy, design_lat_press/1000,
                               field_type[self._puls_boundary], b1, b2, b3, b4]
        if alone:
            return [this_field,]
        else:
            return this_field

class CalcScantlings(Structure):
    '''
    This Class does the calculations for the plate fields. 
    Input is a structure object, same as for the structure class.
    The class inherits from Structure class.
    '''
    def __init__(self, main_dict, lat_press = True, category = 'secondary'):
        super(CalcScantlings,self).__init__(main_dict=main_dict)
        self.lat_press = lat_press
        self.category = category
        self._need_recalc = True

    @property
    def need_recalc(self):
        return self._need_recalc

    @need_recalc.setter
    def need_recalc(self, val):
        self._need_recalc = val

    def get_results_for_report(self,lat_press=0):
        '''
        Returns a string for the report.
        :return:
        '''
        buc = [round(res,1) for res in self.calculate_buckling_all(design_lat_press=lat_press)]

        return 'Minimum section modulus:'\
               +str(int(self.get_dnv_min_section_modulus(design_pressure_kpa=lat_press)*1000**3))\
               +'mm^3 '+' Minium plate thickness: '\
               +str(round(self.get_dnv_min_thickness(design_pressure_kpa=lat_press),1))+\
               ' Buckling results: eq7_19: '+str(buc[0])+' eq7_50: '+str(buc[1])+ ' eq7_51: '\
               +str(buc[2])+ ' eq7_52: '+str(buc[3])+ ' eq7_53: '+str(buc[4])

    def calculate_slamming_plate(self, slamming_pressure, red_fac = 1):
        ''' Slamming pressure input is Pa '''
        ka1 = 1.1
        ka2 = min(max(0.4, self._spacing / self._span), 1)

        ka = math.pow(ka1 - 0.25*ka2,2)
        sigmaf = self._mat_yield/1e6  # MPa

        psl = red_fac * slamming_pressure/1000  # kPa
        Cd = 1.5

        return 0.0158*ka*self._spacing*1000*math.sqrt(psl/(Cd*sigmaf))

    def calculate_slamming_stiffener(self, slamming_pressure, angle = 90, red_fac = 1):
        tk = 0
        psl = slamming_pressure / 1000  # kPa
        Pst = psl * red_fac  # Currently DNV does not use psl/2 for slamming.
        sigmaf = self._mat_yield / 1e6  # MPa
        hw, twa, tp, tf, bf, s = [(val - tk) * 1000 for val in [self._web_height, self._web_th, self._plate_th,
                                                                self._flange_th, self._flange_width, self._spacing]]
        ns = 2
        tau_eH = sigmaf/math.sqrt(3)
        h_stf = (self._web_height+self._flange_th)*1000
        f_shr = 0.7
        lbdg = self._span
        lshr = self._span - self._spacing/4000
        dshr = h_stf + tp if 75 <= angle <= 90 else (h_stf + tp)*math.sin(math.radians(angle))
        tw = (f_shr*Pst*s*lshr)/(dshr*tau_eH)

        if self._web_th*1000 < tw:
            return {'tw_req': tw, 'Zp_req':None}
        fpl = 8* (1+(ns/2))
        Zp_req = (1.2*Pst*s*math.pow(lbdg,2)/(fpl*sigmaf)) + \
                  (ns*(1-math.sqrt(1-math.pow(tw/twa,2)))*hw*tw*(hw+tp))/8000

        return {'tw_req': tw, 'Zp_req':Zp_req}

    def check_all_slamming(self, slamming_pressure, stf_red_fact = 1, pl_red_fact = 1):
        ''' A summary check of slamming '''

        pl_chk = self.calculate_slamming_plate(slamming_pressure, red_fac= pl_red_fact)
        if self._plate_th*1000 < pl_chk:
            chk1 = pl_chk / self._plate_th*1000
            return False, chk1

        stf_res = self.calculate_slamming_stiffener(slamming_pressure, red_fac = stf_red_fact)
        #print('Slamming checked')
        if self._web_th*1000 < stf_res['tw_req']:
            chk2 = stf_res['tw_req'] / self._web_th*1000
            return False, chk2

        if stf_res['Zp_req'] is not None:
            eff_pl_sec_mod = self.get_net_effective_plastic_section_modulus()
            if eff_pl_sec_mod < stf_res['Zp_req']:
                chk3 = stf_res['Zp_req']/eff_pl_sec_mod
                return False, chk3

        return True, None

    def get_net_effective_plastic_section_modulus(self, angle = 90):
        ''' Calculated according to Rules for classification: Ships — DNVGL-RU-SHIP Pt.3 Ch.3. Edition July 2017,
            page 83 '''
        tk = 0
        angle_rad = math.radians(angle)
        hw, tw, tp, tf, bf = [(val - tk) * 1000 for val in [self._web_height, self._web_th, self._plate_th, self._flange_th,
                                                            self._flange_width]]
        h_stf = (self._web_height+self._flange_th)*1000
        de_gr = 0
        tw_gr = self._web_th*1000
        hf_ctr = h_stf-0.5*tf if self.get_stiffener_type() not in ['L','L-bulb'] else h_stf - de_gr - 0.5*tf
        bf_ctr = 0 if self.get_stiffener_type() == 'T' else 0.5*(tf - tw_gr)
        beta = 0.5
        gamma = (1 + math.sqrt(3+12*beta))/4

        Af = 0 if self.get_stiffener_type() == 'FB' else bf*tf

        if 75 <= angle <= 90:
            zpl = (hw*tw*(hw+tp)/2000) + ( (2*gamma-1) * Af * ((hf_ctr + tp/2)) / 1000)
        elif angle < 75:
            zpl = (hw*tw*(hw+tp)/2000)+\
                  ( (2*gamma-1) * Af * ((hf_ctr + tp/2) * math.sin(angle_rad) - bf_ctr*math.cos(angle_rad)) / 1000)

        return zpl

    def get_dnv_min_section_modulus(self, design_pressure_kpa, printit = False):
        ''' Section modulus according to DNV rules '''

        design_pressure = design_pressure_kpa
        fy = self._mat_yield / 1e6
        fyd = fy/self._mat_factor

        sigma_y = self._sigma_y2 + (self._sigma_y1-self._sigma_y2)\
                                       *(min(0.25*self._span,0.5*self._spacing)/self._span)

        sigma_jd = math.sqrt(math.pow(self._sigma_x,2)+math.pow(sigma_y,2)-
                             self._sigma_x*sigma_y+3*math.pow(self._tauxy,2))

        sigma_pd2 = fyd-sigma_jd  # design_bending_stress_mpa

        kps = self._stf_kps  # 1 is clamped, 0.9 is simply supported.
        km_sides = min(self._km1,self._km3)  # see table 3 in DNVGL-OS-C101 (page 62)
        km_middle = self._km2  # see table 3 in DNVGL-OS-C101 (page 62)

        Zs = ((math.pow(self._span, 2) * self._spacing * design_pressure) /
              (min(km_middle, km_sides) * (sigma_pd2) * kps)) * math.pow(10, 6)
        if printit:
            print('Sigma y1', self._sigma_y1, 'Sigma y2', self._sigma_y2, 'Sigma x', self._sigma_x, 'Pressure', design_pressure)
        return max(math.pow(15, 3) / math.pow(1000, 3), Zs / math.pow(1000, 3))

    def get_dnv_min_thickness(self, design_pressure_kpa):
        '''
        Return minimum thickness in mm
        :param design_pressure_kpa:
        :return:
        '''

        design_pressure = design_pressure_kpa
        #print(self._sigma_x)
        sigma_y = self._sigma_y2 + (self._sigma_y1-self._sigma_y2)\
                                       *(min(0.25*self._span,0.5*self._spacing)/self._span)
        sigma_jd = math.sqrt(math.pow(self._sigma_x,2)+math.pow(sigma_y,2)-
                             self._sigma_x*sigma_y+3*math.pow(self._tauxy,2))
        fy = self._mat_yield / 1000000
        fyd = fy/self._mat_factor
        sigma_pd1 = min(1.3*(fyd-sigma_jd), fyd)
        sigma_pd1 = abs(sigma_pd1)
        #print(fyd, sigma_jd, fyd)
        if self.category == 'secondary':
            t0 = 5
        else:
            t0 = 7

        t_min = (14.3 * t0) / math.sqrt(fyd)

        ka = math.pow(1.1 - 0.25  * self._spacing/self._span, 2)

        if ka > 1:
            ka =1
        elif ka<0.72:
            ka = 0.72

        assert sigma_pd1 > 0, 'sigma_pd1 must be negative | current value is: ' + str(sigma_pd1)
        t_min_bend = (15.8 * ka * self._spacing * math.sqrt(design_pressure)) / \
                     math.sqrt(sigma_pd1 *self._plate_kpp)

        if self.lat_press:
            return max(t_min, t_min_bend)
        else:
            return t_min

    def get_minimum_shear_area(self, pressure):
        '''
        Calculating minimum section area according to ch 6.4.4.

        Return [m^2]
        :return:
        '''
        #print('SIGMA_X ', self._sigma_x)
        l = self._span
        s = self._spacing
        fy = self._mat_yield

        fyd = (fy/self._mat_factor)/1e6 #yield strength
        sigxd = self._sigma_x #design membrane stresses, x-dir

        taupds = 0.577*math.sqrt(math.pow(fyd, 2) - math.pow(sigxd, 2))

        As = ((l*s*pressure)/(2*taupds)) * math.pow(10,3)

        return As/math.pow(1000,2)

    def is_acceptable_sec_mod(self, section_module, pressure):
        '''
        Checking if the result is accepable.
        :param section_module:
        :param pressure:
        :return:
        '''

        return min(section_module) >= self.get_dnv_min_section_modulus(pressure)

    def is_acceptable_shear_area(self, shear_area, pressure):
        '''
        Returning if the shear area is ok.
        :param shear_area:
        :param pressure:
        :return:
        '''

        return shear_area >= self.get_minimum_shear_area(pressure)

    def get_plate_efficent_b(self,design_lat_press=0,axial_stress=50,
                                 trans_stress_small=100,trans_stress_large=100):
        '''
        Simple buckling calculations according to DNV-RP-C201
        :return:
        '''

        #7.2 Forces in the idealised stiffened plate

        s = self._spacing #ok
        t = self._plate_th #ok
        l = self._span #ok

        E = 2.1e11 #ok

        pSd = design_lat_press*1000
        sigy1Sd =trans_stress_large*1e6
        sigy2Sd =trans_stress_small*1e6
        sigxSd = axial_stress*1e6

        fy = self._mat_yield #ok

        #7.3 Effective plate width
        alphap=0.525*(s/t)*math.sqrt(fy/E) # reduced plate slenderness, checked not calculated with ex
        alphac = 1.1*(s/t)*math.sqrt(fy/E) # checked not calculated with example
        mu6_9 = 0.21*(alphac-0.2)

        if alphac<=0.2: kappa = 1 # eq6.7, all kappa checked not calculated with example
        elif 0.2<alphac<2: kappa = (1/(2*math.pow(alphac,2)))*(1+mu6_9+math.pow(alphac,2)
                                                               -math.sqrt(math.pow(1+mu6_9+math.pow(alphac,2),2)
                                                                          -4*math.pow(alphac,2))) # ok
        else: kappa=(1/(2*math.pow(alphac,2)))+0.07 # ok

        ha = 0.05*(s/t)-0.75
        assert ha>= 0,'ha must be larger than 0'
        kp = 1 if pSd<=2*((t/s)**2)*fy else 1-ha*((pSd/fy)-2*(t/s)**2)

        sigyR=( (1.3*t/l)*math.sqrt(E/fy)+kappa*(1-(1.3*t/l)*math.sqrt(E/fy)))*fy*kp # checked not calculated with example
        l1 = min(0.25*l,0.5*s)

        sig_min, sig_max = min(sigy1Sd,sigy2Sd),max(sigy1Sd,sigy2Sd) # self-made
        sigySd = sig_min+(sig_max-sig_min)*(1-l1/l) # see 6.8, page 15

        ci = 1-s/(120*t) if (s/t)<=120 else 0 # checked not calculated with example

        Cxs = (alphap-0.22)/math.pow(alphap,2) if alphap > 0.673 else 1 # reduction factor longitudinal
        # eq7.16, reduction factor transverse, compression (positive) else tension

        Cys = math.sqrt(1-math.pow(sigySd/sigyR,2) + ci*((sigxSd*sigySd)/(Cxs*fy*sigyR))) if sigySd >= 0 \
            else min(0.5*(math.sqrt(4-3*math.pow(sigySd/fy,2))+sigySd/fy),1) #ok, checked

        #7.7.3 Resistance parameters for stiffeners
        return s * Cxs * Cys # 7.3, eq7.13, che

    def calculate_buckling_all(self,design_lat_press=0.0, checked_side = 'p'):
        '''
        Simple buckling calculations according to DNV-RP-C201
        :return:
        '''
        #7.2 Forces in the idealised stiffened plate
        As = self._web_height*self._web_th+self._flange_width*self._flange_th #checked
        s = self._spacing #ok
        t = self._plate_th #ok
        l = self._span #ok
        tf = self._flange_th
        tw = self._web_th
        hw = self._web_height
        bf = self._flange_width
        fy = self._mat_yield  # ok
        stf_type = self.get_stiffener_type()
        zstar = self._zstar_optimization  # simplification as per 7.7.1 Continuous stiffeners

        E = 2.1e11 #ok
        Lg = 10 #girder length, ok
        mc = 13.3  # assume continous stiffeners

        pSd = design_lat_press*1000
        tauSd = self._tauxy*1e6
        sigy1Sd =self._sigma_y1*1e6
        sigy2Sd =self._sigma_y2*1e6
        sigxSd = self._sigma_x*1e6


        #7.3 Effective plate width
        alphap=0.525*(s/t)*math.sqrt(fy/E) # reduced plate slenderness, checked not calculated with ex
        alphac = 1.1*(s/t)*math.sqrt(fy/E) # eq 6.8 checked not calculated with example
        mu6_9 = 0.21*(alphac-0.2)

        #kappa chapter 6.3
        if alphac<=0.2: kappa = 1 # eq6.7, all kappa checked not calculated with example
        elif 0.2<alphac<2: kappa = (1/(2*math.pow(alphac,2))) * (1+mu6_9+math.pow(alphac,2)
                                                                 - math.sqrt(math.pow(1+mu6_9+math.pow(alphac,2),2)
                                                                             -4*math.pow(alphac,2))) # ok
        else: kappa=(1/(2*math.pow(alphac,2)))+0.07 # ok
        #end kappa

        ha = 0.05*(s/t)-0.75 #eq 6.11 - checked, ok

        #assert ha>= 0,'ha must be larger than 0'
        if ha < 0:
            return [0, float('inf'), 0, 0, 0, 0]

        kp = 1 if pSd<=2*math.pow(t/s,2)*fy else max(1-ha*((pSd/fy)-2*math.pow(t/s,2)),0) #eq 6.10, checked

        sigyR=( (1.3*t/l)*math.sqrt(E/fy)+kappa*(1-(1.3*t/l)*math.sqrt(E/fy)))*fy*kp # eq 6.6 checked

        sigyRd = sigyR / self._mat_factor #eq 6.5 checked, ok


        # plate resistance check
        ksp = math.sqrt(1-3*math.pow(tauSd/(fy/1),2)) #eq7.20 ch7.4, checked ok

        l1 = min(0.25*l,0.5*s)
        sig_min, sig_max = min(sigy1Sd,sigy2Sd),max(sigy1Sd,sigy2Sd) # self-made
        sigySd = sig_min+(sig_max-sig_min)*(1-l1/l) # see 6.8, page 15

        if not sigySd <= sigyRd:
            return [float('inf'),0,0,0,0,0]

        try:
            psi = sigy2Sd/sigy1Sd # eq. 7.11 checked, if input is 0, the psi is set to 1
        except ZeroDivisionError:
            psi = 1

        Is = self.get_moment_of_intertia()  # moment of intertia full plate width
        Ip = math.pow(t,3)*s/10.9 # checked not calculated with example

        kc = 2*(1+math.sqrt(1+(10.9*Is)/(math.pow(t,3)*s))) # checked not calculated with example
        kg = 5.34+4*math.pow((l/Lg),2) if l<=Lg else 5.34*math.pow(l/Lg,2)+4 # eq 7.5 checked not calculated with example
        kl = 5.34+4*math.pow((s/l),2) if l>=s else 5.34*math.pow(s/l,2)+4 # eq7.7 checked not calculated with example

        taucrg = kg*0.904*E*math.pow(t/l,2) # 7.2 critical shear stress, checked not calculated with example
        taucrl = kl*0.904*E*math.pow(t/s,2) # 7.2 critical chear stress, checked not calculated with example
        tautf = (tauSd - taucrg) if  tauSd>taucrl/self._mat_factor else 0 # checked not calculated with example

        #7.6 Resistance of stiffened panels to shear stresses (page 20)
        taucrs = (36*E/(s*t*math.pow(l,2)))*((Ip*math.pow(Is,3))**0.25) # checked not calculated with example
        tauRd = min(fy/(math.sqrt(3)*self._mat_factor), taucrl/self._mat_factor,taucrs/self._mat_factor)# checked not calculated with example

        ci = 1-s/(120*t) if (s/t)<=120 else 0 # checked ok
        Cxs = (alphap-0.22)/math.pow(alphap,2) if alphap>0.673 else 1 # reduction factor longitudinal, ok

        # eq7.16, reduction factor transverse, compression (positive) else tension

        Cys = math.sqrt(1-math.pow(sigySd/sigyR,2)+ci*((sigxSd*sigySd)/(Cxs*fy*sigyR))) if sigySd >= 0 \
            else min(0.5*(math.sqrt(4-3*math.pow(sigySd/fy,2))+sigySd/fy),1) #eq 7.16, ok, checked
        #7.7.3 Resistance parameters for stiffeners

        se = s * Cxs * Cys # 7.3, eq7.13, checked
        zp = self.get_cross_section_centroid_with_effective_plate(se) - t / 2  # ch7.5.1 page 19
        zt = (t / 2 + hw + tf) - zp  # ch 7.5.1 page 19

        Ie = self.get_moment_of_intertia(efficent_se=se) #ch7.5.1 effective moment of inertia.
        Wep = Ie/zp #as def in eq7.71
        Wes = Ie/zt #as def in eq7.71

        C0 = (Wes * fy * mc) / (kc * E * math.pow(t, 2) * s)  # 7.2 checked not calculated with example
        p0 = (0.6+0.4*psi)*C0*sigy1Sd if psi>-1.5 else 0 # 7.2 checked not calculated with example

        qSd = (pSd + p0) * s  # checked not calculated with example

        Ae = As+se*t #ch7.7.3 checked, ok

        W = min(Wes,Wep) #eq7.75 text, checked
        pf = (12*W/(math.pow(l,2)*s))*(fy/self._mat_factor) #checked, ok

        lk = l*(1-0.5*abs(pSd/pf)) #eq7.74, buckling length, checked

        ie = math.sqrt(Ie/Ae) #ch 7.5.1. checked
        fE = math.pow(math.pi,2)*E*math.pow(ie/lk,2) #e7.24, checked

        sigjSD = math.sqrt(math.pow(sigxSd,2)+math.pow(sigySd,2)-sigxSd*sigySd+3*math.pow(tauSd,2)) # eq 7.38, ok
        fEpx = 3.62*E*math.pow(t/s,2) # eq 7.42, checked, ok
        fEpy = 0.9*E*math.pow(t/s,2) # eq 7.43, checked, ok
        fEpt = 5.0*E*math.pow(t/s,2) # eq 7.44, checked, ok
        c = 2-(s/l) # eq 7.41, checked, ok
        try:
            alphae = math.sqrt( (fy/sigjSD) * math.pow(math.pow(abs(sigxSd)/fEpx, c)+
                                                       math.pow(abs(sigySd)/fEpy, c)+
                                                       math.pow(abs(tauSd)/fEpt, c), 1/c)) # eq 7.40, checed, ok.
        except OverflowError:
            import tkinter as tk
            tk.messagebox.showerror('Error', 'There is an issue with your input. \n'
                                             'Maybe a dimension is nor correct w.r.t.\n'
                                             'm and mm. Check it!\n\n'
                                             'A plate resistance error will be shown\n'
                                             'for buckling. This is not correct but is\n'
                                             'due to the input error.')
            return [float('inf'),0,0,0,0,0]
        fep = fy / math.sqrt(1+math.pow(alphae,4)) # eq 7.39, checked, ok.
        eta = min(sigjSD/fep, 1) # eq. 7.37, chekced

        C = (hw / s) * math.pow(t / tw, 3) * math.sqrt((1 - eta)) # e 7.36, checked ok

        beta = (3*C+0.2)/(C+0.2) # eq 7.35, checked, ok

        Af = self._flange_width*self._flange_th #flange area, ok
        Aw = self._web_height*self._web_th #web area, ok

        ef = 0 if stf_type in ['FB','T'] else self._flange_width/2-self._web_th/2
        #Ipo = (Aw*(ef-0.5*tf)**2/3+Af*ef**2)*10e-4 #polar moment of interia in cm^4
        #It = (((ef-0.5*tf)*tw**3)/3e4)*(1-0.63*(tw/(ef-0.5*tf)))+( (bf*tf)/3e4*(1-0.63*(tf/bf)))/(100**4) #torsonal moment of interia cm^4


        Iz = (1/12)*Af*math.pow(bf,2)+math.pow(ef,2)*(Af/(1+(Af/Aw))) #moment of inertia about z-axis, checked

        G = E/(2*(1+0.3)) #rules for ships Pt.8 Ch.1, page 334
        lT = self._span # Calculated further down
        #print('Aw ',Aw,'Af ', Af,'tf ', tf,'tw ', tw,'G ', G,'E ', E,'Iz ', Iz,'lt ', lT)

        def get_some_data(lT):
            if stf_type in ['T', 'L', 'L-bulb']:
                fET = beta*(((Aw + Af * math.pow(tf/tw,2)) / (Aw + 3*Af)) * G*math.pow(tw/hw,2))+\
                      (math.pow(math.pi, 2) * E * Iz) / ((Aw/3 + Af)*math.pow(lT,2)) \
                    if bf != 0 \
                    else (beta+2*math.pow(hw/lT,2))*G*math.pow(tw/hw,2) # eq7.32 checked, no example
            else:
                fET = (beta + 2*math.pow(hw/lT,2))*G*math.pow(tw/hw,2) # eq7.34 checked, no example

            alphaT = math.sqrt(fy/fET) #eq7.30. checked

            mu7_29 = 0.35 * (alphaT - 0.6) # eq 7.29. checked

            fr = fy if alphaT<=0.6 else ((1+mu7_29+math.pow(alphaT,2)-math.sqrt( math.pow(1+mu7_29+math.pow(alphaT,2),2)-
                                                                                 4*math.pow(alphaT,2))) /
                                         (2*math.pow(alphaT,2))) * fy
            alpha = math.sqrt(fr / fE) #e7.23, checked.

            mu_tors = 0.35*(alphaT-0.6)
            fT = fy if alphaT <= 0.6 else fy * (1+mu_tors+math.pow(alphaT,2)-math.sqrt(math.pow(1+mu_tors+math.pow(alphaT,2),2)-
                                                                                     4*math.pow(alphaT,2)))/\
                                           (2*math.pow(alphaT,2))

            mu_pl = (0.34 + 0.08 * (zp / ie)) * (alpha - 0.2)
            mu_stf = (0.34 + 0.08 * (zt / ie)) * (alpha - 0.2)
            frp = fy
            frs = fy if alphaT <= 0.6 else fT
            fyp,fys = fy,fy
            #fyps = (fyp*se*t+fys*As)/(se*t+As)
            fks = fr if alpha <= 0.2 else frs * (1+mu_stf+math.pow(alpha,2)-math.sqrt(math.pow(1+mu_stf+math.pow(alpha,2),2)-
                                                                                     4*math.pow(alpha,2)))/\
                                          (2*math.pow(alpha,2))
            #fr = fyps
            fkp = fyp if alpha <= 0.2 else frp * (1+mu_pl+math.pow(alpha,2)-math.sqrt(math.pow(1+mu_pl+math.pow(alpha,2),2)-
                                                                                     4*math.pow(alpha,2)))/\
                                           (2*math.pow(alpha,2))

            return fr, fks, fkp

        u = math.pow(tauSd / tauRd, 2)  # eq7.58. checked.
        fr, fks, fkp = get_some_data(lT=lT*0.4)
        Ms1Rd = Wes*(fr/self._mat_factor) #ok, assuming fr calculated with lT=span * 0.4
        NksRd = Ae * (fks / self._mat_factor) #eq7.66, page 22 - fk according to equation 7.26, sec 7.5,
        NkpRd = Ae * (fkp / self._mat_factor)  # checked ok, no ex

        M1Sd = abs((qSd*math.pow(l,2))/12) #ch7.7.1, checked ok

        M2Sd = abs((qSd*l**2)/24) #ch7.7.1, checked ok

        Ne = ((math.pow(math.pi,2))*E*Ae)/(math.pow(lk/ie,2))# eq7.72 , checked ok

        Nrd = Ae * (fy / self._mat_factor) #eq7.65, checked ok

        Nsd = sigxSd * (As + s*t) + tautf * s *t #  Equation 7.1, section 7.2, checked ok


        MstRd = Wes*(fy/self._mat_factor) #eq7.70 checked ok, no ex
        MpRd = Wep*(fy/self._mat_factor) #eq7.71 checked ok, no ex

        fr, fks, fkp = get_some_data(lT = lT * 0.8)
        Ms2Rd = Wes*(fr/self._mat_factor) #eq7.69 checked ok, no ex
        # print('Nksrd', NksRd, 'Nkprd', NkpRd, 'Ae is', Ae, 'fks is', fks, 'fkp is', fkp,
        #       'alphas are', mu_pl, mu_stf, 'lk', lk, 'lt', lT)

        #print('CENTROID ', 'zp', 'zt', self.get_cross_section_centroid_with_effective_plate(se)*1000,zp,zt)

        eq7_19 = sigySd/(ksp*sigyRd) #checked ok
        if self._zstar_optimization:
            zstar_range = np.arange(-zt/2,zp,0.002)
        else:
            zstar_range = [0]
        # Lateral pressure on plate side:
        if checked_side == 'p':
            # print('eq7_50 = ',Nsd ,'/', NksRd,'+' ,M1Sd,'-' , Nsd ,'*', zstar, '/' ,Ms1Rd,'*',1,'-', Nsd ,'/', Ne,'+', u)
            # print('eq7_51 = ',Nsd,' / ',NkpRd,' - 2 * ',Nsd, '/' ,Nrd,' + ',M1Sd,' - ,',Nsd,' * ',zstar,' / ',MpRd,' * ','1 - ',Nsd,' / ',Ne,' + ',u)
            #print('eq7_52 = ',Nsd,'/', NksRd,'-', 2, '*',Nsd,'/', Nrd,'+',M2Sd,'-', Nsd,'*', zstar,'/',MstRd,'*',1, '-',Nsd,'/', Ne,'+', u)
            max_lfs = []
            ufs = []
            for zstar in zstar_range:
                eq7_50 = (Nsd / NksRd) + (M1Sd - Nsd * zstar) / (Ms1Rd * (1 - Nsd / Ne)) + u
                eq7_51 = (Nsd / NkpRd) - 2 * (Nsd / Nrd) + ((M1Sd - Nsd * zstar) / (MpRd * (1 - (Nsd / Ne)))) + u
                eq7_52 = (Nsd / NksRd) - 2 * (Nsd / Nrd) + ((M2Sd + Nsd * zstar) / (MstRd * (1 - (Nsd / Ne)))) + u
                eq7_53 = (Nsd / NkpRd) + (M2Sd + Nsd * zstar) / (MpRd * (1 - Nsd / Ne))
                max_lfs.append(max(eq7_50, eq7_51, eq7_52, eq7_53))
                ufs.append([eq7_19, eq7_50, eq7_51, eq7_52, eq7_53,zstar])
                #print(zstar, eq7_50, eq7_51, eq7_52, eq7_53, 'MAX LF is: ', max(eq7_50, eq7_51, eq7_52, eq7_53))
            min_of_max_ufs_idx = max_lfs.index(min(max_lfs))
            return ufs[min_of_max_ufs_idx]
        # Lateral pressure on stiffener side:
        else:
            max_lfs = []
            ufs = []
            for zstar in zstar_range:
                eq7_54 = (Nsd / NksRd) - 2 * (Nsd / Nrd) + ((M1Sd + Nsd * zstar) / (MstRd * (1 - (Nsd / Ne)))) + u
                eq7_55 = (Nsd / NkpRd) + ((M1Sd + Nsd * zstar) / (MpRd * (1 - (Nsd / Ne)))) + u
                eq7_56 = (Nsd / NksRd) + ((M2Sd - Nsd * zstar) / (Ms2Rd * (1 - (Nsd / Ne)))) + u
                eq7_57 = (Nsd / NkpRd) - 2 * (Nsd / Nrd) + ((M2Sd - Nsd * zstar) / (MpRd * (1 - (Nsd / Ne)))) + u
                max_lfs.append(max(eq7_54, eq7_55, eq7_56, eq7_57))
                ufs.append([eq7_19, eq7_54, eq7_55, eq7_56, eq7_57, zstar])
                #print('eq7_19, eq7_54, eq7_55, eq7_56, eq7_57')
            min_of_max_ufs_idx = max_lfs.index(min(max_lfs))
            return ufs[min_of_max_ufs_idx]

    def calculate_buckling_plate(self,design_lat_press,axial_stress=20,
                                 trans_stress_small=100,trans_stress_large=100,
                                 design_shear_stress = 10):
        '''
        Simple buckling calculations according to DNV-RP-C201
        This method is currently not used.
        :return:
        '''

        #7.2 Forces in the idealised stiffened plate

        s = self._spacing
        t = self._plate_th
        l = self._span
        E = 2.1e11

        pSd = design_lat_press*1000
        tauSd = design_shear_stress*1e6
        sigy2Sd =trans_stress_small*1e6
        fy = self._mat_yield

        #7.3 Effective plate width
        alphac = 1.1*(s/t)*math.sqrt(fy/E)
        gamma = 0.21*(alphac-0.2)

        if alphac<=0.2: kappa = 1
        elif 0.2<alphac<2: kappa = (1/(2*(alphac**2)))*(1-+gamma+alphac**2-math.sqrt((1+gamma+alphac**2)**2-4*alphac**2))
        else: kappa=(1/(2*alphac**2))+0.7

        ha = 0.05*(s/t)-0.75
        assert ha>= 0,'ha must be larger than 0'
        kp = 1 if pSd<=2*((t/s)**2)*fy else 1-ha*((pSd/fy)-2*(t/s)**2)

        sigyR=( (1.3*t/l)*math.sqrt(E/fy)+kappa*(1-(1.3*t/l)*math.sqrt(E/fy)))*fy*kp
        sigyRd = sigyR / self._mat_factor

        # plate resistance check
        ksp = math.sqrt(1-3*(tauSd/(fy/1))**2)
        eq7_19 = ksp*sigyRd/sigy2Sd
        return eq7_19

    def buckling_local_stiffener(self):
        '''
        Local requirements for stiffeners. Chapter 9.11.
        :return:
        '''

        epsilon = math.sqrt(235 / (self._mat_yield / 1e6))

        if self._stiffener_type in ['L', 'L-bulb']:
            c = self._flange_width - self._web_th/2
        elif self._stiffener_type == 'T':
            c = self._flange_width/2 - self._web_th/2
        elif self._stiffener_type == 'FB':
            return self._web_height <= 42 * self._web_th * epsilon, self._web_height/(42 * self._web_th * epsilon)

        # print(self._web_height, self._web_th, self._flange_width ,self._flange_th )
        # print('c:',c, 14 * self._flange_th * epsilon, ' | ',  self._web_height, 42 * self._web_th * epsilon)
        # print(c <= (14  * self._flange_th * epsilon) and self._web_height <= 42 * self._web_th * epsilon)
        # print(c/(14  * self._flange_th * epsilon), self._web_height / (42 * self._web_th * epsilon))
        # print('')

        return c <= (14  * self._flange_th * epsilon) and self._web_height <= 42 * self._web_th * epsilon, \
               max(c/(14  * self._flange_th * epsilon), self._web_height / (42 * self._web_th * epsilon))

    def is_acceptable_pl_thk(self, design_pressure):
        '''
        Checking if the thickness is acceptable.
        :return:
        '''
        return self.get_dnv_min_thickness(design_pressure) <= self._plate_th*1000

class Shell():
    '''
    Small class to contain shell properties.
    '''
    def __init__(self, main_dict):
        super(Shell, self).__init__()
        '''
                            shell_dict = {'plate_thk': [self._new_shell_thk.get() / 1000, 'm'],
                                  'radius': [self._new_shell_radius.get() / 1000, 'm'],
                                  'distance between rings, l': [self._new_shell_dist_rings.get() / 1000, 'm'],
                                  'length of shell, L': [self._new_shell_length.get() / 1000, 'm'],
                                  'tot cyl length, Lc': [self._new_shell_tot_length.get() / 1000, 'm'],
                                  'eff. buckling lenght factor': [self._new_shell_k_factor.get() / 1000, 'm'],
                                  'mat_yield': [self._new_shell_yield.get() *1e6, 'Pa']}
        '''
        self._thk = main_dict['plate_thk'][0]
        self._yield = main_dict['mat_yield'][0]
        self._radius = main_dict['radius'][0]
        self._dist_between_rings = main_dict['distance between rings, l'][0]
        self._length_of_shell = main_dict['length of shell, L'][0]
        self._tot_cyl_length = main_dict['tot cyl length, Lc'][0]
        self._k_factor = main_dict['eff. buckling lenght factor'][0]

        # For conical
        self._cone_r1 = None
        self._cone_r2 = None
        self._cone_alpha = None


    @property
    def Lc(self):
        return self._tot_cyl_length
    @Lc.setter
    def Lc(self, val):
        self._tot_cyl_length = val
    @property
    def thk(self):
        return self._thk
    @thk.setter
    def thk(self, val):
        self._thk = val
    @property
    def radius(self):
        return self._radius
    @radius.setter
    def radius(self, val):
        self._radius = val
    @property
    def dist_between_rings(self):
        return self._dist_between_rings
    @dist_between_rings.setter
    def dist_between_rings(self, val):
        self._dist_between_rings = val
    @property
    def length_of_shell(self):
        return self._length_of_shell
    @length_of_shell.setter
    def length_of_shell(self, val):
        self._length_of_shell = val
    @property
    def tot_cyl_length(self):
        return self._tot_cyl_length
    @tot_cyl_length.setter
    def tot_cyl_length(self, val):
        self._tot_cyl_length = val
    @property
    def k_factor(self):
        return self._k_factor
    @k_factor.setter
    def k_factor(self, val):
        self._k_factor = val
    def get_Zl(self):
        L = self.tot_cyl_length*1000
        Zl = math.pow(L,2)*math.sqrt(1-math.pow(0.3,2))/(self._radius*1000 * self._thk*1000) if self._thk*self._radius else 0
        return Zl

    def get_effective_width_shell_plate(self):
        return 1.56*math.sqrt(self._radius * self._thk)/(1+12*self.thk/self._radius)

    def get_main_properties(self):
        main_data = {'plate_thk': [self._thk, 'm'],
                                  'radius': [self._radius, 'm'],
                                  'distance between rings, l': [self._dist_between_rings, 'm'],
                                  'length of shell, L': [self._length_of_shell, 'm'],
                                  'tot cyl length, Lc': [self._tot_cyl_length, 'm'],
                                  'eff. buckling lenght factor': [self._k_factor, 'm'],
                                  'mat_yield': [self._yield, 'Pa']}
        return main_data

    def set_main_properties(self, main_dict):

        self._thk = main_dict['plate_thk'][0]
        self._yield = main_dict['mat_yield'][0]
        self._radius = main_dict['radius'][0]
        self._dist_between_rings = main_dict['distance between rings, l'][0]
        self._length_of_shell = main_dict['length of shell, L'][0]
        self._tot_cyl_length = main_dict['tot cyl length, Lc'][0]
        self._k_factor = main_dict['eff. buckling lenght factor'][0]

class CylinderAndCurvedPlate():
    '''
    Buckling of cylinders and curved plates.
    Geomeries
    	Selections for: Type of Structure Geometry:
    geomeries = {1:'Unstiffened shell (Force input)', 2:'Unstiffened panel (Stress input)',
                    3:'Longitudinal Stiffened shell  (Force input)',
                    4:'Longitudinal Stiffened panel (Stress input)',
                    5:'Ring Stiffened shell (Force input)',
                    6:'Ring Stiffened panel (Stress input)',
                    7:'Orthogonally Stiffened shell (Force input)',
                    8:'Orthogonally Stiffened panel (Stress input)'}

    '''

    geomeries = {0:'Stiffened panel, flat', 1:'Unstiffened shell (Force input)', 2:'Unstiffened panel (Stress input)',
                 3:'Longitudinal Stiffened shell  (Force input)', 4:'Longitudinal Stiffened panel (Stress input)',
                 5:'Ring Stiffened shell (Force input)', 6:'Ring Stiffened panel (Stress input)',
                 7:'Orthogonally Stiffened shell (Force input)', 8:'Orthogonally Stiffened panel (Stress input)'}
    geomeries_map = dict()
    for key, value in geomeries.items():
        geomeries_map[value] = key

    def __init__(self, main_dict = None, shell: Shell = None, long_stf: Structure = None, ring_stf: Structure = None,
                 ring_frame: Structure = None):
        super(CylinderAndCurvedPlate, self).__init__()

        # main_dict = {'sasd': 100, 'smsd': 100, 'tTsd': 50, 'tQsd':10, 'psd': -0.3, 'shsd': 0, 'geometry': 7,
        #              'material factor': 1.15, 'lT': 0, 'delta0': 0.005, 'fab method ring stf': 1,
        #              'fab method ring girder': 2, 'E-module':2.1e11, 'poisson': 0.3, 'yield': 355e6}

        #if main_dict['geometry'][0] in [1,3,5,7]: # Need to convert from forces to stresses.
        self._sasd = main_dict['sasd'][0]
        self._smsd = main_dict['smsd'][0]
        self._tTsd = main_dict['tTsd'][0]
        self._tQsd= main_dict['tQsd'][0]
        self._psd = main_dict['psd'][0]
        self._shsd = main_dict['shsd'][0]
        self._geometry = main_dict['geometry'][0]
        self._mat_factor = main_dict['material factor'][0]
        self._delta0 = main_dict['delta0'][0]
        self._fab_method_ring_stf = main_dict['fab method ring stf'][0]
        self._fab_method_ring_girder = main_dict['fab method ring girder'][0]
        self._E = main_dict['E-module'][0]
        self._v = main_dict['poisson'][0]
        self._yield = main_dict['mat_yield'][0]

        self._Shell = shell
        self._LongStf = long_stf
        self._RingStf = ring_stf
        self._RingFrame = ring_frame

        self._length_between_girders = main_dict['length between girders'][0]
        self._panel_spacing = main_dict['panel spacing, s'][0]
        self.__ring_stiffener_excluded = main_dict['ring stf excluded'][0]
        self.__ring_frame_excluded = main_dict['ring frame excluded'][0]

        self._end_cap_pressure_included = main_dict['end cap pressure'][0]
        self._uls_or_als =  main_dict['ULS or ALS'][0]

    def __str__(self):
        '''
        Returning all properties.
        '''

        long_string = 'N/A' if self._LongStf is None else self._LongStf.get_beam_string()
        ring_string = 'N/A' if self._RingStf is None else self._RingStf.get_beam_string()
        frame_string = 'N/A' if self._RingFrame is None else self._RingFrame.get_beam_string()
        return \
            str(
            '\n Cylinder radius:               ' + str(round(self._Shell.radius,3)) + ' meters' +
            '\n Cylinder thickness:            ' + str(self._Shell.thk*1000)+' mm'+
            '\n Distance between rings, l:     ' + str(self._Shell.dist_between_rings*1000)+' mm'+
            '\n Length of shell, L:            ' + str(self._Shell.length_of_shell*1000)+' mm'+
            '\n Total cylinder lenght:         ' + str(self._Shell.tot_cyl_length*1000)+' mm'+
            '\n Eff. Buckling length factor:   ' + str(self._Shell.k_factor)+
            '\n Material yield:                ' + str(self._yield/1e6)+' MPa'+
            '\n Longitudinal stiffeners:       ' + long_string+
            '\n Ring stiffeners                ' + ring_string+
            '\n Ring frames/girders:           ' + frame_string+
            '\n Design axial stress/force:     ' + str(self._sasd/1e6)+' MPa'+
            '\n Design bending stress/moment:  ' + str(self._smsd/1e6)+' MPa'+
            '\n Design tosional stress/moment: ' + str(self._tTsd/1e6)+' MPa'+
            '\n Design shear stress/force:     ' + str(self._tQsd/1e6)+' MPa'+
            '\n Design lateral pressure        ' + str(self._psd/1e6)+' MPa'+
            '\n Additional hoop stress         ' + str(self._shsd/1e6)+' MPa')
    
    @property
    def sasd(self):
        return self._sasd
    @sasd.setter
    def sasd(self, val):
        self._sasd = val
    @property
    def smsd(self):
        return self._smsd
    @smsd.setter
    def smsd(self, val):
        self._smsd = val
    @property
    def tTsd(self):
        return self._tTsd
    @tTsd.setter
    def tTsd(self, val):
        self._tTsd = val
    @property
    def tQsd(self):
        return self._tQsd
    @tQsd.setter
    def tQsd(self, val):
        self._tQsd = val
    @property
    def psd(self):
        return self._psd
    @psd.setter
    def psd(self, val):
        self._psd = val
    @property
    def shsd(self):
        return self._shsd
    @shsd.setter
    def shsd(self, val):
        self._shsd = val
    @property
    def panel_spacing(self):
        return self._panel_spacing
    @panel_spacing.setter
    def panel_spacing(self, val):
        self._panel_spacing = val
        
    @property
    def ShellObj(self):
        return self._Shell
    @ShellObj.setter
    def ShellObj(self, val):
        self._Shell = val
    @property
    def LongStfObj(self):
        return self._LongStf
    @LongStfObj.setter
    def LongStfObj(self, val):
        self._LongStf = val
    @property
    def RingStfObj(self):
        return self._RingStf
    @RingStfObj.setter
    def RingStfObj(self, val):
        self._RingStf = val
    @property
    def RingFrameObj(self):
        return self._RingFrame
    @RingFrameObj.setter
    def RingFrameObj(self, val):
        self._RingFrame = val

    @property
    def geometry(self):
        return self._geometry
    @geometry.setter
    def geometry(self, val):
        self._geometry = val
    @property
    def length_between_girders(self):
        return self._length_between_girders
    @length_between_girders.setter
    def length_between_girders(self, val):
        self._length_between_girders = val
    @property
    def _ring_stiffener_excluded(self):
        return self.__ring_stiffener_excluded
    @_ring_stiffener_excluded.setter
    def _ring_stiffener_excluded(self, val):
        self.__ring_stiffener_excluded = val
    @property
    def _ring_frame_excluded(self):
        return self.__ring_frame_excluded
    @_ring_frame_excluded.setter
    def _ring_frame_excluded(self, val):
        self.__ring_frame_excluded = val

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
                   'Stiffener check': None,
                   'Weight': None}

        if empty_result_dict:
            return results

        unstiffend_shell, column_buckling_data, data_shell_buckling = None, None, None
        # UF for unstiffened shell
        unstiffend_shell = self.unstiffened_shell()

        s = self._panel_spacing*1000 if self._LongStf is None else self._LongStf.s

        if any([self._geometry in [1, 5], s > self._Shell.dist_between_rings*1000]):
            uf_unstf_shell = unstiffend_shell['UF unstiffened circular cylinder']
            results['Unstiffened shell'] = uf_unstf_shell
        else:
            uf_unstf_shell = unstiffend_shell['UF unstiffened curved panel']
            results['Unstiffened shell'] = uf_unstf_shell

        if optimizing:
            if uf_unstf_shell > 1:
                return False, 'UF unstiffened', results

        # UF for longitudinal stiffened shell

        if self._geometry in [3,4,7,8]:
            if self._LongStf is not None:
                data_shell_buckling = self.shell_buckling(unstiffened_cylinder=unstiffend_shell)
                column_buckling_data= self.column_buckling(unstf_shell_data=unstiffend_shell,
                                                          shell_bukcling_data=data_shell_buckling)
                long_stf_shell = self.longitudinally_stiffened_shell(column_buckling_data=column_buckling_data,
                                                                     unstiffened_shell=unstiffend_shell)

                results['Column stability check'] = column_buckling_data['Column stability check']
                results['Stiffener check'] = column_buckling_data['stiffener check']
                if self._geometry in [3,4,7,8] and long_stf_shell['fksd'] > 0:
                    results['Longitudinal stiffened shell'] = long_stf_shell['sjsd_used']/long_stf_shell['fksd']\
                        if self._geometry in [3,4,7,8] else 0

                if optimizing:
                    if not results['Column stability check']:
                        return False, 'Column stability', results
                    elif False in results['Stiffener check'].values():
                        return False, 'Stiffener check', results
                    elif results['Longitudinal stiffened shell'] > 1:
                        return False, 'UF longitudinal stiffeners', results


        if self._geometry in [5,6,7,8]:
            # UF for panel ring buckling
            ring_stf_shell = None
            if self._RingStf is not None:
                data_shell_buckling = data_shell_buckling if data_shell_buckling is not None \
                    else self.shell_buckling(unstiffened_cylinder=unstiffend_shell)
                column_buckling_data = column_buckling_data if column_buckling_data is not None  \
                    else self.column_buckling( unstf_shell_data=unstiffend_shell,
                                               shell_bukcling_data=data_shell_buckling)
                ring_stf_shell = self.ring_stiffened_shell(data_shell_buckling=data_shell_buckling,
                                                           column_buckling_data=column_buckling_data)
                results['Column stability check'] = column_buckling_data['Column stability check']
                results['Stiffener check'] = column_buckling_data['stiffener check']
                results['Ring stiffened shell'] = ring_stf_shell[0]

                if optimizing:
                    if not results['Column stability check']:
                        return False, 'Column stability', results
                    elif False in results['Stiffener check'].values():
                        return False, 'Stiffener check', results
                    elif results['Ring stiffened shell'] > 1:
                        return False, 'UF ring stiffeners', results

        # UF for ring frame
        if self._geometry in [5, 6, 7, 8]:
            if self._RingFrame is not None:
                data_shell_buckling = data_shell_buckling if data_shell_buckling is not None \
                    else self.shell_buckling(unstiffened_cylinder=unstiffend_shell)
                column_buckling_data = column_buckling_data if column_buckling_data is not None  \
                    else self.column_buckling( unstf_shell_data=unstiffend_shell,
                                               shell_bukcling_data=data_shell_buckling)
                ring_stf_shell = ring_stf_shell if ring_stf_shell is not None else\
                    self.ring_stiffened_shell(data_shell_buckling=data_shell_buckling,
                                              column_buckling_data=column_buckling_data)
                results['Column stability check'] = column_buckling_data['Column stability check']
                results['Stiffener check'] = column_buckling_data['stiffener check']
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

    def set_main_properties(self, main_dict):
        self._sasd = main_dict['sasd']
        self._smsd = main_dict['smsd']
        self._tTsd = main_dict['tTsd']
        self._tQsd = main_dict['tQsd']
        self._psd = main_dict['psd']
        self._shsd = main_dict['shsd']
        self._geometry = main_dict['geometry']
        self._mat_factor = main_dict['material factor']
        self._delta0 = main_dict['delta0']
        self._fab_method_ring_stf = main_dict['fab method ring stf']
        self._fab_method_ring_girder = main_dict['fab method ring girder']
        self._E = main_dict['E-module']
        self._v = main_dict['poisson']
        self._yield = main_dict['mat_yield']

    def shell_buckling(self,unstiffened_cylinder = None):
        '''
        Main sheet to calculate cylinder buckling.
        '''
        stucture_objects = {'Unstiffened':self._Shell, 'Long Stiff.': self._LongStf, 'Ring Stiffeners': self._RingStf,
                            'Heavy ring Frame': self._RingFrame}
        stf_type = ['T', 'FB', 'T']
        l = self._Shell.dist_between_rings*1000
        r = self._Shell.radius*1000
        t = self._Shell.thk*1000

        parameters, cross_sec_data = list(), list()
        for idx, obj in stucture_objects.items():
            if obj is None:
                cross_sec_data.append([np.nan, np.nan, np.nan, np.nan, np.nan])
                if idx not in ['Unstiffened', 'Long Stiff.']:
                    parameters.append([np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan])
                continue
            if idx != 'Unstiffened':
                hs = obj.hw/2 if stf_type =='FB' else obj.hw + obj.tf/2
                It = obj.get_torsional_moment_venant()
                Ipo = obj.get_polar_moment()
                Iz = obj.get_Iz_moment_of_inertia()
                se = self._Shell.get_effective_width_shell_plate()
                Iy = obj.get_moment_of_intertia(efficent_se=se, tf1=self._Shell.thk)*1000**4

                cross_sec_data.append([hs, It, Iz, Ipo, Iy])

                A = obj.get_cross_section_area(include_plate=False)*math.pow(1000,2)
                beta = l/(1.56*math.sqrt(r*t))
                leo = (l/beta) *  ((math.cosh(2*beta)-math.cos(2*beta))/(math.sinh(2*beta)+math.sin(2*beta)))

                worst_axial_comb = min(self._sasd/1e6 - self._smsd/1e6, self._sasd/1e6 + self._smsd/1e6)
                sxsd_used = worst_axial_comb

                if idx == 'Long Stiff.':
                    zp = obj.get_cross_section_centroid_with_effective_plate(include_plate=False) * 1000
                    h_tot = obj.hw + obj.tf
                    zt = h_tot -zp # TODO NOT 100# correct
                else:
                    se = self._Shell.get_effective_width_shell_plate()
                    zp = obj.get_cross_section_centroid_with_effective_plate(se=se, tf1=self._Shell.thk) * 1000 # ch7.5.1 page 19
                    h_tot = self._Shell.thk*1000 + obj.hw + obj.tf
                    zt = h_tot -zp

            if idx not in ['Unstiffened', 'Long Stiff.']:  # Parameters
                alpha = A/(leo*t)
                zeta = max([0, 2*(math.sinh(beta)*math.cos(beta)+math.cosh(beta)*math.sin(beta))/
                            (math.sinh(2*beta)+math.sin(2*beta))])
                rf = r - t / 2 - (obj.hw + obj.tf)

                r0 = zt + rf
                parameters.append([alpha, beta, leo, zeta, rf, r0, zt])

        sxsd, shsd, shRsd, tsd = list(), list(), list(), list()

        for idx, obj in stucture_objects.items():
            if obj is None:
                shRsd.append(np.nan)
                continue
            if idx == 'Unstiffened':
                shsd.append((self._psd/1e6)*r/t+self._shsd/1e6)
                sxsd.append(self._sasd/1e6+self._smsd/1e6 if self._geometry in [2,6] else
                            min([self._sasd/1e6, self._sasd/1e6-self._smsd/1e6, self._sasd/1e6+self._smsd/1e6]))
                tsd.append(self._tTsd/1e6 + self._tQsd/1e6)
            elif idx == 'Long Stiff.':
                if stucture_objects['Ring Stiffeners'] == None:
                    shsd.append(shsd[0]+self._shsd/1e6)
                else:
                    shsd_ring = ((self._psd/1e6)*r/t)-parameters[0][0]*parameters[0][3]/(parameters[0][0]+1)*\
                                ((self._psd/1e6)*r/t-0.3*sxsd[0])
                    shsd.append(shsd_ring + self._shsd/1e6)
                if self._geometry in [3,4,7,8]:
                    sxsd.append(sxsd_used)
                else:
                    sxsd.append(sxsd[0])

                tsd.append(self._tTsd/1e6 + self._tQsd/1e6)

            elif idx == 'Ring Stiffeners':
                rf = parameters[0][4]
                shsd_ring = ((self._psd / 1e6) * r / t) - parameters[0][0] * parameters[0][3] / (parameters[0][0] + 1) * \
                            ((self._psd / 1e6) * r / t - 0.3 * sxsd[0]) #TODO check
                shsd.append(np.nan if stucture_objects['Ring Stiffeners'] == None else shsd_ring)
                shRsd.append(((self._psd/1e6)*r/t-0.3*sxsd[0])*(1/(1+parameters[0][0]))*(r/rf))
                if self._geometry > 4:
                    sxsd.append(sxsd[0])
                    tsd.append(tsd[0])
                else:
                    sxsd.append(np.nan)
                    tsd.append(np.nan)

            else:
                rf = parameters[1][4]
                shsd.append(((self._psd/1e6)*r/t)-parameters[1][0]*parameters[1][3]/(parameters[1][0]+1)*
                            ((self._psd/1e6)*r/t-0.3*self._sasd/1e6))
                shRsd.append(((self._psd/1e6)*r/t-0.3*self._sasd/1e6)*(1/(1+parameters[1][0]))*(r/rf))
                if self._geometry > 4:
                    sxsd.append(sxsd[0])
                    tsd.append(tsd[0])
                else:
                    sxsd.append(np.nan)
                    tsd.append(np.nan)

        sxsd = np.array(sxsd)
        shsd = np.array(shsd)
        tsd = np.array(tsd)
        sjsd = np.sqrt(sxsd**2 - sxsd*shsd + shsd**2+3*tsd**2)

        return {'sjsd': sjsd, 'parameters': parameters, 'cross section data': cross_sec_data, 'shRsd': shRsd}

    def unstiffened_shell(self, conical = False):

        E = self._E/1e6
        t = self._Shell.thk*1000

        # get correct s

        s = max([self._Shell.dist_between_rings, 2*math.pi*self._Shell.radius])*1000 if self._LongStf == None else \
            self._LongStf.s
        v = self._v
        r = self._Shell.radius*1000
        l = self._Shell.dist_between_rings * 1000
        fy = self._yield/1e6

        sasd = self._sasd/1e6
        smsd = self._smsd/1e6
        tsd = self._tTsd/1e6+self._tQsd/1e6
        psd = self._psd/1e6
        shsd = psd*r/t


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
        geometry = self._geometry

        if geometry in [2,6]:
            sxsd = sasd+smsd
        else:
            sxsd = min(sasd, sasd+smsd, smsd-smsd)

        if smsd < 0:
            smsd = -smsd
        else:
            if geometry in [2, 6]:
                smsd = 0
            else:
                smsd = smsd

        sjsd = math.sqrt(math.pow(sxsd,2) - sxsd*shsd + math.pow(shsd,2) + 3 * math.pow(tsd, 2))  # (3.2.3)

        Zs = (math.pow(s, 2) / (r * t)) * math.sqrt(1 - math.pow(v, 2))  # The curvature parameter Zs (3.3.3)

        def table_3_1(chk):
            psi = {'Axial stress': 4, 'Shear stress': 5.34+4*math.pow(s/l, 2),
                   'Circumferential compression': math.pow(1+math.pow(s/l, 2), 2)}                      # ψ
            epsilon = {'Axial stress': 0.702*Zs, 'Shear stress': 0.856*math.sqrt(s/l)*math.pow(Zs, 3/4),
                   'Circumferential compression': 1.04*(s/l)*math.sqrt(Zs)}                             # ξ
            rho = {'Axial stress': 0.5*math.pow(1+(r/(150*t)), -0.5), 'Shear stress': 0.6,
                   'Circumferential compression': 0.6}
            return psi[chk], epsilon[chk], rho[chk]
        vals = list()

        for chk in ['Axial stress', 'Shear stress', 'Circumferential compression']:
            psi, epsilon, rho = table_3_1(chk=chk)
            C = psi * math.sqrt(1 + math.pow(rho * epsilon / psi, 2))  # (3.4.2) (3.6.4)
            fE = C*(math.pow(math.pi, 2)*E/(12*(1-math.pow(v,2)))) *math.pow(t/s,2)
            #print(chk, 'C', C, 'psi', psi,'epsilon', epsilon,'rho' ,rho, 'fE', fE)
            vals.append(fE)

        fEax, fEshear, fEcirc = vals
        sa0sd = -sxsd if sxsd < 0 else 0
        sh0sd = -shsd if shsd < 0 else 0 # Maximium allowable stress from iteration.

        if any([val == 0 for val in vals]):
            lambda_s_pow = 0
        else:
            lambda_s_pow = (fy/sjsd) * (sa0sd/fEax + sh0sd/fEcirc + tsd/fEshear)

        lambda_s = math.sqrt(lambda_s_pow)
        fks = fy/math.sqrt(1+math.pow(lambda_s,4 ))

        provide_data['fks - Unstifffed curved panel'] = fks
        if lambda_s < 0.5:
            gammaM = self._mat_factor
        else:
            if lambda_s > 1:
                gammaM = 1.45
            else:
                gammaM = 0.85+0.6*lambda_s
        if self._uls_or_als == 'ALS':
            gammaM = gammaM/1.15
        provide_data['gammaM Unstifffed panel'] = gammaM
        fksd = fks/gammaM
        provide_data['fksd - Unstifffed curved panel'] = fksd
        uf = sjsd/fksd

        provide_data['UF unstiffened curved panel'] = uf
        provide_data['gammaM curved panel'] = gammaM
        sjsd_max = math.sqrt(math.pow(sasd+smsd,2)-(sasd+smsd)*shsd+math.pow(shsd,2)+3*math.pow(tsd,2))

        uf_max =  self._mat_factor* sjsd_max/fy
        # print('Unstifffed curved panel', 'UF', uf, 'UFmax', uf_max, 'sigjsd', sjsd, 'Zs', Zs, 'lambda_s', lambda_s,
        #       'fks', fks, 'gammaM', gammaM, 'sjsd_max', sjsd_max)

        def iter_table_1():
            found, sasd_iter, count, this_val, logger  = False, 0 if uf > 1 else sasd, 0, 0, list()

            while not found:
                # Iteration
                sigmsd_iter = smsd if geometry in [2,6] else min([-smsd, smsd])
                siga0sd_iter = 0 if sasd_iter >= 0 else -sasd_iter  # (3.2.4)
                sigm0sd_iter = 0 if sigmsd_iter >= 0 else -sigmsd_iter  # (3.2.5)
                sigh0sd_iter = 0 if shsd>= 0 else -shsd  # (3.2.6)

                sjsd_iter = math.sqrt(math.pow(sasd_iter+sigmsd_iter, 2) - (sasd_iter+sigmsd_iter)*shsd + math.pow(shsd, 2)+
                                      3*math.pow(tsd, 2)) #(3.2.3)

                lambdas_iter = math.sqrt((fy / sjsd_iter) * ((siga0sd_iter+sigm0sd_iter)/fEax+ sigh0sd_iter/fEcirc+tsd/fEshear)) # (3.2.2)

                gammaM_iter = 1  # As taken in the DNVGL sheets
                fks_iter = fy / math.sqrt(1 + math.pow(lambdas_iter,4))
                fksd_iter = fks_iter / gammaM_iter
                #print('sjsd', sjsd_iter, 'fksd', fksd_iter, 'fks', fks, 'gammaM', gammaM_iter, 'lambdas_iter', lambdas_iter)
                this_val = sjsd_iter/fksd_iter
                logger.append(0 if this_val > 1 else siga0sd_iter)
                if this_val > 1.0 or count == 1e6:
                    found = True
                count += 1
                if this_val >0.98:
                    sasd_iter -= 0.5
                elif this_val > 0.95:
                    sasd_iter -= 1
                elif this_val > 0.9:
                    sasd_iter -= 2
                elif this_val > 0.7:
                    sasd_iter -= 10
                else:
                    sasd_iter -= 20

                #print(sasd_iter, this_val)

            return 0 if len(logger) == 1 else logger[-2]


        provide_data['max axial stress - 3.3 Unstifffed curved panel'] = iter_table_1()


        # Pnt. 3.4 Unstifffed circular cylinders
        Zl = (math.pow(l, 2)/(r*t)) * math.sqrt(1 - math.pow(v, 2)) #(3.4.3) (3.6.5)

        def table_3_2(chk):
            psi = {'Axial stress': 1, 'Bending': 1,
                   'Torsion and shear force': 5.34,
                   'Lateral pressure': 4, 'Hydrostatic pressure': 2}                      # ψ

            zeta= {'Axial stress': 0.702*Zl, 'Bending': 0.702*Zl,
                   'Torsion and shear force': 0.856* math.pow(Zl, 3/4),'Lateral pressure': 1.04*math.sqrt(Zl),
                   'Hydrostatic pressure': 1.04*math.sqrt(Zl)} # ξ

            rho = {'Axial stress': 0.5*math.pow(1+(r/(150*t)), -0.5), 'Bending': 0.5*math.pow(1+(r/(300*t)), -0.5),
                   'Torsion and shear force': 0.6,
                   'Lateral pressure': 0.6, 'Hydrostatic pressure': 0.6}
            return psi[chk], zeta[chk], rho[chk]

        vals = list()
        for chk in ['Axial stress', 'Bending', 'Torsion and shear force',
                    'Lateral pressure','Hydrostatic pressure']:
            psi, zeta, rho = table_3_2(chk=chk)
            C = psi * math.sqrt(1 + math.pow(rho * zeta / psi, 2))  # (3.4.2) (3.6.4)
            fE = C*math.pow(math.pi,2)*E / (12*(1-math.pow(v,2))) * math.pow(t/l,2)
            #print(chk, 'C', C, 'psi', psi,'epsilon', epsilon,'rho' ,rho, 'fE', fE)
            vals.append(fE)



        fEax, fEbend,  fEtors, fElat, fEhyd = vals

        provide_data['fEax - Unstifffed circular cylinders'] = fEax

        test1 = 3.85 * math.sqrt(r / t)
        test2 = 2.25 * math.sqrt(r / t)
        test_l_div_r = l/r
        provide_data['fEh - Unstifffed circular cylinders  - Psi=4'] = 0.25*E*math.pow(t/r,2) if test_l_div_r > test2 else fElat
        if l / r > test1:
            fEt_used = 0.25 * E * math.pow(t / r, 3 / 2)  # (3.4.4)
        else:
            fEt_used = fEtors

        if l / r > test2:
            fEh_used = 0.25 * E * math.pow(t / r, 2)
        else:
            fEh_used = fElat if not self._end_cap_pressure_included else fEhyd
        #
        # if geometry in [2,6]:
        #     sxsd = self._sasd+smsd
        # else:
        #     sxsd = min(self._sasd, self._sasd+smsd, smsd-smsd)


        sjsd = math.sqrt(math.pow(sxsd,2) - sxsd*shsd + math.pow(shsd,2) + 3 * math.pow(tsd, 2))  # (3.2.3)

        sa0sd = -sasd if sasd < 0 else 0
        sh0sd = -shsd if shsd < 0 else 0

        if smsd < 0:
            sm0sd = -smsd
        else:

            if geometry in [2,6]:
                sm0sd = 0
            else:
                sm0sd = smsd

        if any([fEax == 0, fEbend == 0, fEt_used == 0, fEh_used == 0, sjsd == 0]):
            lambda_s_pow = 0
        else:
            lambda_s_pow = (fy/sjsd) * (sa0sd/fEax + sm0sd/fEbend + sh0sd/fEh_used + tsd/fEt_used)


        lambda_s = math.sqrt(lambda_s_pow)
        fks = fy/math.sqrt(1+math.pow(lambda_s,4 ))

        provide_data['fks - Unstifffed circular cylinders'] = fks

        if lambda_s < 0.5:
            gammaM = self._mat_factor
        else:
            if lambda_s > 1:
                gammaM = 1.45
            else:
                gammaM = 0.85+0.6*lambda_s
        if self._uls_or_als == 'ALS':
            gammaM = gammaM/1.15

        fksd = fks/gammaM
        provide_data['fksd - Unstifffed circular cylinders'] = fksd
        uf = sjsd/fksd

        provide_data['UF unstiffened circular cylinder'] = uf
        provide_data['gammaM circular cylinder'] = gammaM
        #print('UF', uf, 'Unstifffed circular cylinders')
        def iter_table_2():

            found, sasd_iter, count, this_val, logger  = False, 0 if uf > 1 else sasd, 0, 0, list()

            while not found:
                # Iteration
                sigmsd_iter = smsd if geometry in [2, 6] else min([-smsd, smsd])
                siga0sd_iter = 0 if sasd_iter >= 0 else -sasd_iter  # (3.2.4)
                sigm0sd_iter = 0 if sigmsd_iter >= 0 else -sigmsd_iter  # (3.2.5)
                sigh0sd_iter = 0 if shsd >= 0 else -shsd  # (3.2.6)

                sjsd_iter = math.sqrt(
                    math.pow(sasd_iter + sigmsd_iter, 2) - (sasd_iter + sigmsd_iter) * shsd + math.pow(shsd, 2) +
                    3 * math.pow(tsd, 2))  # (3.2.3)

                lambdas_iter = math.sqrt((fy/sjsd_iter) * (siga0sd_iter/fEax + sigm0sd_iter/fEbend +
                                                           sigh0sd_iter/fElat + tsd/fEtors))

                gammaM_iter = 1  # As taken in the DNVGL sheets
                fks_iter = fy / math.sqrt(1 + math.pow(lambdas_iter, 4))
                fksd_iter = fks_iter / gammaM_iter
                # print('sjsd', sjsd_iter, 'fksd', fksd_iter, 'fks', fks, 'gammaM', gammaM_iter, 'lambdas_iter', lambdas_iter)

                this_val = sjsd_iter / fksd_iter
                logger.append(sasd_iter)

                if this_val > 1.0 or count == 1e6:
                    found = True
                count += 1

                if this_val >0.98:
                    sasd_iter -= 0.5
                elif this_val > 0.95:
                    sasd_iter -= 1
                elif this_val > 0.9:
                    sasd_iter -= 2
                elif this_val > 0.7:
                    sasd_iter -= 10
                else:
                    sasd_iter -= 20

            return 0 if len(logger) == 1 else logger[-2]

        provide_data['max axial stress - 3.4.2 Shell buckling'] = iter_table_2()
        return provide_data

    def ring_stiffened_shell(self, data_shell_buckling = None, column_buckling_data = None):

        E = self._E/1e6
        t = self._Shell.thk*1000
        s = max([self._Shell.dist_between_rings, 2*math.pi*self._Shell.radius])*1000 if self._LongStf == None else \
            self._LongStf.s

        r = self._Shell.radius*1000
        l = self._Shell.dist_between_rings * 1000
        fy = self._yield/1e6

        L = self._Shell.tot_cyl_length*1000
        LH = L
        sasd = self._sasd/1e6
        smsd = self._smsd/1e6
        tsd = self._tTsd/1e6 + self._tQsd/1e6
        psd = self._psd/1e6

        data_shell_buckling = self.shell_buckling() if data_shell_buckling == None else data_shell_buckling

        #Pnt. 3.5:  Ring stiffened shell

        # Pnt. 3.5.2.1   Requirement for cross-sectional area:
        Zl = self._Shell.get_Zl()
        Areq = np.nan if Zl == 0 else (2/math.pow(Zl,2)+0.06)*l*t
        Areq = np.array([Areq, Areq])
        Astf = np.nan if self._RingStf is None else self._RingStf.get_cross_section_area(include_plate=False)*1000**2
        Aframe = np.nan if self._RingFrame is None else \
            self._RingFrame.get_cross_section_area(include_plate=False) * 1000 ** 2
        A = np.array([Astf, Aframe])

        uf_cross_section = Areq/A

        #Pnt. 3.5.2.3   Effective width calculation of shell plate
        lef = 1.56*math.sqrt(r*t)/(1+12*t/r)
        lef_used = np.array([min([lef, LH]), min([lef, LH])])

        #Pnt. 3.5.2.4   Required Ix for Shell subject to axial load
        A_long_stf = 0 if self._LongStf is None else self._LongStf.get_cross_section_area(include_plate=False)*1000**2
        alfaA = 0 if s*t <= 0 else A_long_stf/(s*t)


        r0 = np.array([data_shell_buckling['parameters'][0][5], data_shell_buckling['parameters'][1][5]])

        worst_ax_comp = min([sasd+smsd, sasd-smsd])

        Ixreq = np.array([abs(worst_ax_comp) * t * (1 + alfaA) * math.pow(r0[0], 4) / (500 * E * l),
                          abs(worst_ax_comp) * t * (1 + alfaA) * math.pow(r0[1], 4) / (500 * E * l)])

        #Pnt. 3.5.2.5   Required Ixh for shell subjected to torsion and/or shear:
        Ixhreq = np.array([math.pow(tsd / E, (8 / 5)) * math.pow(r0[0] / L, 1 / 5) * L * r0[0] * t * l,
                           math.pow(tsd / E, (8 / 5)) * math.pow(r0[1] / L, 1 / 5) * L * r0[1] * t * l])


        #Pnt. 3.5.2.6   Simplified calculation of Ih for shell subjected to external pressure
        zt = np.array([data_shell_buckling['parameters'][0][6],data_shell_buckling['parameters'][1][6]])
        rf = np.array([data_shell_buckling['parameters'][0][4], data_shell_buckling['parameters'][1][4]])

        delta0 = r*self._delta0

        fb_ring_req_val = np.array([0 if self._RingStf is None else 0.4*self._RingStf.tw*math.sqrt(E/fy),
                                    0 if self._RingFrame is None else 0.4*self._RingFrame.tw*math.sqrt(E/fy)])
        # if self._RingStf.get_stiffener_type() == 'FB':
        #     fb_ring_req = fb_ring_req_val[0] > self._RingStf.hw
        # else:
        #     fb_ring_req = np.NaN

        flanged_rf_req_h_val = np.array([0 if self._RingStf is None else 1.35*self._RingStf.tw*math.sqrt(E/fy),
                                         0 if self._RingFrame is None else 1.35*self._RingFrame.tw*math.sqrt(E/fy)])
        # if self._RingFrame.get_stiffener_type() != 'FB':
        #     flanged_rf_req_h = flanged_rf_req_h_val[1] > self._RingFrame.hw
        # else:
        #     flanged_rf_req_h = np.NaN

        flanged_rf_req_b_val = np.array([0 if self._RingStf is None else 7*self._RingStf.hw/math.sqrt(10+E*self._RingStf.hw/(fy*r)),
                                         0 if self._RingFrame is None else 7*self._RingFrame.hw/math.sqrt(10+E*self._RingFrame.hw/(fy*r))])
        # if self._RingFrame.get_stiffener_type() != 'FB':
        #     flanged_rf_req_b = flanged_rf_req_b_val[1] > self._RingFrame.b
        # else:
        #     flanged_rf_req_b = np.NaN

        if self._RingStf is not None:
            spf_stf = self._RingStf.hw/fb_ring_req_val[0] if self._RingStf.get_stiffener_type() == 'FB' \
                else max([flanged_rf_req_b_val[0]/self._RingStf.b, self._RingStf.hw/flanged_rf_req_h_val[0]])
        else:
            spf_stf = 0

        if self._RingFrame is not None:
            spf_frame = self._RingFrame.hw / fb_ring_req_val[1]if self._RingFrame.get_stiffener_type() == 'FB' \
                else max([flanged_rf_req_b_val[1] / self._RingFrame.b,self._RingFrame.hw / flanged_rf_req_h_val[1]])
        else:
            spf_frame = 0

        Stocky_profile_factor = np.array([spf_stf, spf_frame])

        fT = column_buckling_data['fT_dict']
        fT = np.array([fT['Ring Stiff.'] if Stocky_profile_factor[0] > 1 else fy,
                       fT['Ring Girder'] if Stocky_profile_factor[1] > 1 else fy])

        fr_used = np.array([fT[0] if self._fab_method_ring_stf == 1 else 0.9 * fT[0],
                            fT[1] if self._fab_method_ring_girder == 1 else 0.9 * fT[1]])
        shRsd = [abs(val) for val in data_shell_buckling['shRsd']]

        Ih = np.array([0 if E*r0[idx]*(fr_used[idx]/2-shRsd[idx]) == 0 else abs(psd)*r*math.pow(r0[idx],2)*l/(3*E)*
                                                                        (1.5+3*E*zt[idx]*delta0/(math.pow(r0[idx],2)
                                                                         *(fr_used[idx]/2-shRsd[idx])))
              for idx in [0,1]])

        # Pnt. 3.5.2.2     Moment of inertia:
        IR = [Ih[idx] + Ixhreq[idx] + Ixreq[idx] if all([psd <= 0, Ih[idx] > 0]) else Ixhreq[idx] + Ixreq[idx]
              for idx in [0,1]]
        Iy = [data_shell_buckling['cross section data'][idx+1][4] for idx in [0,1]]

        uf_moment_of_inertia = list()
        for idx in [0,1]:

            if Iy[idx] > 0:
                uf_moment_of_inertia.append(9.999 if fr_used[idx] < 2*shRsd[idx] else IR[idx]/Iy[idx])
            else:
                uf_moment_of_inertia.append(0)

        # Pnt. 3.5.2.7   Refined calculation of external pressure
        # parameters.append([alpha, beta, leo, zeta, rf, r0, zt])
        I = Iy
        Ihmax = [max(0, I[idx]-Ixhreq[idx]-Ixreq[idx]) for idx in [0,1]]
        leo = [data_shell_buckling['parameters'][idx][2] for idx in [0,1]]
        Ar = A
        ih2 = [0 if Ar[idx]+leo[idx]*t == 0 else Ihmax[idx]/(Ar[idx]+leo[idx]*t) for idx in [0,1]]
        alfa = [0 if l*t == 0 else 12*(1-math.pow(0.3,2))*Ihmax[idx]/(l*math.pow(t,3)) for idx in [0,1]]
        betta = [data_shell_buckling['parameters'][idx][0] for idx in [0,1]]
        ZL = [math.pow(L,2)/r/t*math.sqrt(1-math.pow(0.3,2)) for idx in [0,1]]

        C1 = [2*(1+alfa[idx])/(1+betta[idx])*(math.sqrt(1+0.27*ZL[idx]/math.sqrt(1+alfa[idx]))-alfa[idx]/(1+alfa[idx]))
              for idx in [0,1]]

        C2 = [2*math.sqrt(1+0.27*ZL[idx]) for idx in [0,1]]

        my = [0 if ih2[idx]*r*leo[idx]*C1[idx] == 0 else
              zt[idx]*delta0*rf[idx]*l/(ih2[idx]*r*leo[idx])*(1-C2[idx]/C1[idx])*1/(1-0.3/2) for idx in [0,1]]

        fE = np.array([C1[idx]*math.pow(math.pi,2)*E/(12*(1-math.pow(0.3,2)))*(math.pow(t/L,2)) if L > 0
                       else 0.1 for idx in [0,1]])

        fr = np.array(fT)
        lambda_2 = fr/fE
        lambda_ = np.sqrt(lambda_2)

        fk = [0 if lambda_2[idx] == 0 else fr[idx]*(1+my[idx]+lambda_2[idx]-math.sqrt(math.pow(1+my[idx]+lambda_2[idx],2)-
                                                                                 4*lambda_2[idx]))/(2*lambda_2[idx])
              for idx in [0,1]]
        gammaM = 1.15 # LRFD
        fkd = [fk[idx]/gammaM for idx in [0,1]]
        psd = np.array([0.75*fk[idx]*t*rf[idx]*(1+betta[idx])/(gammaM*math.pow(r,2)*(1-0.3/2)) for idx in [0,1]])

        uf_refined = abs((self._psd/1e6))/psd

        return np.max([uf_cross_section, uf_moment_of_inertia, uf_refined], axis=0)

    def longitudinally_stiffened_shell(self, column_buckling_data = None, unstiffened_shell = None):

        h = self._Shell.thk*1000 + self._LongStf.hw + self._LongStf.tf

        hw = self._LongStf.hw
        tw = self._LongStf.tw
        b = self._LongStf.b
        tf = self._LongStf.tf

        E = self._E/1e6
        t = self._Shell.thk*1000
        s = max([self._Shell.dist_between_rings, 2*math.pi*self._Shell.radius])*1000 if self._LongStf == None else \
            self._LongStf.s
        v = self._v
        r = self._Shell.radius*1000
        l = self._Shell.dist_between_rings * 1000
        fy = self._yield/1e6

        L = self._Shell.tot_cyl_length*1000
        LH = L
        sasd = self._sasd/1e6
        smsd = self._smsd/1e6
        tsd = self._tTsd/1e6 + self._tQsd/1e6
        psd = self._psd/1e6
        shsd = psd * r / t

        lightly_stf = s/t > math.sqrt(r/t)
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
        geometry = self._geometry
        data = unstiffened_shell if unstiffened_shell is not None else self.unstiffened_shell()

        if geometry == 1:
            fks = data['fks - Unstifffed circular cylinders']
        else:
            fks = data['fks - Unstifffed curved panel']

        sxSd  =min([sasd+smsd, sasd-smsd])


        sjsd  = math.sqrt(math.pow(sxSd,2) - sxSd*shsd + math.pow(shsd,2) + 3 * math.pow(tsd, 2))

        Se = (fks*abs(sxSd) / (sjsd*fy))*s

        # Moment of inertia
        As = A = hw*tw + b*tf  # checked

        num_stf = math.floor(2*math.pi*r/s)

        e= (hw*tw*(hw/2) + b*tf*(hw+tf/2)) / (hw*tw+b*tw)
        Istf = h*math.pow(tw,3)/12 + tf*math.pow(b, 3)/12

        dist_stf = r - t / 2 - e
        Istf_tot = 0
        angle = 0
        for stf_no in range(num_stf):
            Istf_tot += Istf + As*math.pow(dist_stf*math.cos(angle),2)
            angle += 2*math.pi/num_stf
        # Ishell = (math.pi/4) * ( math.pow(r+t/2,4) - math.pow(r-t/2,4))
        # Itot = Ishell + Istf_tot # Checked

        Iy = self._LongStf.get_moment_of_intertia(efficent_se=Se/1000, tf1=self._Shell.thk)*1000**4 # TODO small difference here (Hp-bulb).

        alpha = 12*(1-math.pow(v,2))*Iy/(s*math.pow(t,3))
        Zl = (math.pow(l, 2)/(r*t)) * math.sqrt(1-math.pow(v,2))

        #print('Zl', Zl, 'alpha', alpha, 'Isef', Iy, 'Se', Se, 'sjsd', sjsd, 'sxsd', sxSd, 'fks', fks, 'As', As)
        # Table 3-3

        def table_3_3(chk):
            psi = {'Axial stress': 0 if Se == 0 else (1+alpha) / (1+A/(Se*t)),
                   'Torsion and shear stress': 5.54+1.82*math.pow(l/s, 4/3) * math.pow(alpha, 1/3),
                   'Lateral Pressure': 2*(1+math.sqrt(1+alpha))}                      # ψ
            epsilon = {'Axial stress': 0.702*Zl,
                   'Torsion and shear stress': 0.856*math.pow(Zl, 3/4),
                   'Lateral Pressure': 1.04*math.sqrt(Zl)}                             # ξ
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
            #print(chk, 'C', C, 'psi', psi,'epsilon', epsilon,'rho' ,rho, 'fE', fE)
        fEax, fEtors, fElat = vals

        #Torsional Buckling can be excluded as possible failure if:
        if self._LongStf._stiffener_type == 'FB':
            chk_fb = hw <= 0.4*tw*math.sqrt(E/fy)

        data_col_buc = column_buckling_data

        fy_used = fy if data_col_buc['lambda_T'] <= 0.6 else data_col_buc['fT']

        sasd = sasd*(A+s*t)/(A+Se*t) if A+Se*t>0 else 0
        smsd = smsd * (A + s * t) / (A + Se * t) if A + Se * t > 0 else 0

        sa0sd = -sasd if sasd < 0 else 0
        sm0sd = -smsd if smsd < 0 else 0
        sh0sd = -shsd if shsd < 0 else 0

        sjsd_panels = math.sqrt(math.pow(sasd+smsd,2)-(sasd+smsd)*shsd + math.pow(shsd,2)+  3*math.pow(tsd,2))

        worst_axial_comb = min(sasd-smsd,sasd+smsd)
        sjsd_shells = math.sqrt(math.pow(worst_axial_comb,2)-worst_axial_comb*shsd +math.pow(shsd,2)+3*math.pow(tsd,2))
        sxsd_used = worst_axial_comb
        provide_data['sxsd_used'] = sxsd_used
        sjsd_used = sjsd_panels if self._geometry in [2,6] else sjsd_shells
        provide_data['sjsd_used'] = sjsd_used
        lambda_s2_panel = fy_used/sjsd_panels*((sa0sd+sm0sd)/fEax+sh0sd/fElat+tsd/fEtors) if\
            sjsd_panels*fEax*fEtors*fElat>0 else 0

        lambda_s2_shell = fy_used/sjsd_shells*(max(0,-worst_axial_comb)/fEax+sh0sd/fElat+tsd/fEtors) if\
            sjsd_shells*fEax*fEtors*fElat>0 else 0

        shell_type = 2 if self._geometry in [1,5] else 1
        lambda_s = math.sqrt(lambda_s2_panel) if shell_type == 1 else math.sqrt(lambda_s2_shell)

        fks = fy_used/math.sqrt(1+math.pow(lambda_s,4))

        if lambda_s < 0.5:
            gammaM = self._mat_factor
        else:
            if lambda_s > 1:
                gammaM = 1.45
            else:
                gammaM = 0.85+0.6*lambda_s
        if self._uls_or_als == 'ALS':
            gammaM = gammaM/1.15

        # Design buckling strength:
        fksd = fks/gammaM
        provide_data['fksd'] = fksd
        #print('fksd', fksd, 'fks', fks, 'gammaM', gammaM, 'lambda_s', lambda_s, 'lambda_s^2 panel', lambda_s2_panel, 'sjsd', sjsd_used, 'worst_axial_comb',worst_axial_comb, 'sm0sd',sm0sd)

        return provide_data

    @staticmethod
    def get_Itot(hw, tw, b, tf, r, s, t):

        h = t+hw+tf
        As = hw*tw + b*tf  # checked
        if As != 0:

            num_stf = math.floor(2*math.pi*r/s)
            e= (hw*tw*(hw/2) + b*tf*(hw+tf/2)) / (hw*tw+b*tw)
            Istf = h*math.pow(tw,3)/12 + tf*math.pow(b, 3)/12
            dist_stf = r - t / 2 - e
            Istf_tot = 0
            angle = 0
            for stf_no in range(num_stf):
                Istf_tot += Istf + As*math.pow(dist_stf*math.cos(angle),2)
                angle += 2*math.pi/num_stf
        else:
            Istf_tot = 0
        Ishell = (math.pi/4) * ( math.pow(r+t/2,4) - math.pow(r-t/2,4))
        Itot = Ishell + Istf_tot # Checked

        return Itot

    def column_buckling(self,shell_bukcling_data = None, unstf_shell_data = None):

        geometry = self._geometry
        provide_data = dict()
        G = 80769.2

        if self._LongStf is None:
            h = self._Shell.thk*1000
        else:
            h = self._Shell.thk*1000 + self._LongStf.hw + self._LongStf.tf

        hw = 0 if self._LongStf is None else self._LongStf.hw
        tw = 0 if self._LongStf is None else self._LongStf.tw
        b = 0 if self._LongStf is None else self._LongStf.b
        tf = 0 if self._LongStf is None else self._LongStf.tf

        E = self._E/1e6
        t = self._Shell.thk*1000
        s = max([self._Shell.dist_between_rings, 2*math.pi*self._Shell.radius])*1000 if self._LongStf == None else \
            self._LongStf.s
        v = self._v
        r = self._Shell.radius*1000
        l = self._Shell.dist_between_rings * 1000
        fy = self._yield/1e6

        L = self._Shell.tot_cyl_length*1000
        LH = L
        Lc = max([L, LH])

        sasd = self._sasd/1e6
        smsd = self._smsd/1e6
        tsd = self._tTsd/1e6 + self._tQsd/1e6
        psd = self._psd/1e6
        shsd = psd * r / t

        shell_buckling_data = self.shell_buckling(unstiffened_cylinder=unstf_shell_data) if\
            shell_bukcling_data is None else shell_bukcling_data
        data = self.unstiffened_shell() if unstf_shell_data is None else unstf_shell_data

        idx = 1
        param_map = {'Ring Stiff.': 0,'Ring Girder': 1}
        fT_dict = dict()
        for key, obj in {'Longitudinal stiff.': self._LongStf, 'Ring Stiff.': self._RingStf,
                         'Ring Girder': self._RingFrame}.items():
            if obj is None:
                continue
            gammaM = data['gammaM circular cylinder'] if self._geometry > 2 else \
                data['gammaM curved panel']
            sjsd = shell_buckling_data['sjsd'][idx]

            this_s = 0 if self._LongStf is None else self._LongStf.s
            if any([self._geometry in [1, 5], this_s > (self._Shell.dist_between_rings * 1000)]):
                fksd = data['fksd - Unstifffed circular cylinders']
            else:
                fksd = data['fksd - Unstifffed curved panel']

            fks = fksd * gammaM
            eta = sjsd/fks
            hw = obj.hw
            tw = obj.tw

            if key == 'Longitudinal stiff.':
                s_or_leo = obj.s
                lT = l
            else:
                s_or_leo = shell_buckling_data['parameters'][param_map[key]][2]

                lT = math.pi*math.sqrt(r*hw)

            C = hw/s_or_leo*math.pow(t/tw,3)*math.sqrt(1-min([1,eta])) if s_or_leo*tw>0 else 0

            beta = (3*C+0.2)/(C+0.2)

            #parameters.append([alpha, beta, leo, zeta])
            hs, It, Iz, Ipo, Iy = shell_buckling_data['cross section data'][idx - 1]
            if obj.get_stiffener_type() == 'FB':
                Af = obj.tf * obj.b
                Aw = obj.hw * obj.tw
                fEt = beta * (Aw + math.pow(obj.tf / obj.tw, 2) * Af) / (Aw + 3 * Af) * G * math.pow(obj.tw / hw,
                                                                                                     2) + math.pow(
                    math.pi, 2) \
                      * E * Iz / ((Aw / 3 + Af) * math.pow(lT, 2))
            else:
                hs, It, Iz, Ipo, Iy = shell_buckling_data['cross section data'][idx-1]
                fEt = beta * G * It / Ipo + math.pow(math.pi, 2) * E * math.pow(hs, 2) * Iz / (Ipo * math.pow(lT, 2))

            lambdaT = math.sqrt(fy/fEt)

            mu = 0.35*(lambdaT-0.6)
            fT = (1+mu+math.pow(lambdaT,2)-math.sqrt(math.pow(1+mu+math.pow(lambdaT,2),2)-4*math.pow(lambdaT,2)))\
                 /(2*math.pow(lambdaT,2))*fy if lambdaT > 0.6 else fy

            # General

            if key == 'Longitudinal stiff.':
                provide_data['lambda_T'] = lambdaT
                provide_data['fT'] = fT

            fT_dict[key] = fT
            idx += 1
        provide_data['fT_dict'] = fT_dict

        # Moment of inertia
        As = A = hw*tw + b*tf  # checked

        num_stf = math.floor(2*math.pi*r/s)

        Atot = As*num_stf + 2*math.pi*r*t

        e= (hw*tw*(hw/2) + b*tf*(hw+tf/2)) / (hw*tw+b*tw)
        Istf = h*math.pow(tw,3)/12 + tf*math.pow(b, 3)/12

        dist_stf = r - t / 2 - e
        Istf_tot = 0
        angle = 0
        for stf_no in range(num_stf):
            Istf_tot += Istf + As*math.pow(dist_stf*math.cos(angle),2)
            angle += 2*math.pi/num_stf

        Ishell = (math.pi/4) * ( math.pow(r+t/2,4) - math.pow(r-t/2,4))
        Itot = Ishell + Istf_tot # Checked

        k_factor = self._Shell.k_factor
        col_test =math.pow(k_factor*Lc/math.sqrt(Itot/Atot),2) >= 2.5*E/fy
        # print("Column buckling should be assessed") if col_test else \
        #     print("Column buckling does not need to be checked")


        #Sec. 3.8.2   Column buckling strength:

        fEa = data['fEax - Unstifffed circular cylinders']
        #fEa = any([geometry in [1,5], s > l])
        fEh = data['fEh - Unstifffed circular cylinders  - Psi=4']

        #   Special case:  calculation of fak for unstiffened shell:


        #   General case:

        use_fac = 1 if geometry < 3 else 2

        if use_fac == 1:
            a = 1 + math.pow(fy, 2) / math.pow(fEa, 2)
            b = ((2 * math.pow(fy, 2) / (fEa * fEh)) - 1) * shsd
            c = math.pow(shsd, 2) + math.pow(fy, 2) * math.pow(shsd, 2) / math.pow(fEh, 2) - math.pow(fy, 2)
            fak = (b + math.sqrt(math.pow(b, 2) - 4 * a * c)) / (2 * a)
        elif any([geometry in [1,5], s > l]):
            fak = data['max axial stress - 3.4.2 Shell buckling']
        else:
            fak = data['max axial stress - 3.3 Unstifffed curved panel']

        i = Itot/Atot
        fE = E*math.sqrt(math.pi*i  / (Lc * k_factor))
        Lambda_ = math.sqrt(fak/fE)

        fkc = (1-0-28*math.pow(Lambda_,2))*fak if Lambda_ <= 1.34 else fak/math.pow(Lambda_,2)
        gammaM = data['gammaM curved panel'] #self._mat_factor  # Check TODO need to fix this

        # if lambda_s < 0.5:
        #     gammaM = self._mat_factor
        # else:
        #     if lambda_s > 1:
        #         gammaM = 1.45
        #     else:
        #         gammaM = 0.85+0.6*lambda_s
        # if self._uls_or_als == 'ALS':
        #     gammaM = gammaM/1.15


        fakd = fak/gammaM
        fkcd = fkc/gammaM

        sa0sd = -sasd if sasd<0 else 0

        if fakd*fkcd > 0:
            stab_chk = sa0sd/fkcd + (abs(smsd) / (1-sa0sd/fE))/fakd <= 1
        else:
            stab_chk = True

        #print("Stability requirement satisfied") if stab_chk else print("Not acceptable")
        # Sec. 3.9   Torsional buckling:  moved to the top

        # Stiffener check

        stf_req_h = list()
        for idx, obj in enumerate([self._LongStf, self._RingStf, self._RingFrame]):
            if obj is None:
                stf_req_h.append(np.nan)
            else:
                stf_req_h.append(0.4*obj.tw*math.sqrt(E/fy) if obj.get_stiffener_type() == 'FB'
                                 else 1.35*obj.tw*math.sqrt(E/fy))

        stf_req_h = np.array(stf_req_h)

        stf_req_b = list()
        for idx, obj in enumerate([self._LongStf, self._RingStf, self._RingFrame]):
            if obj is None:
                stf_req_b.append(np.nan)
            else:
                stf_req_b.append(np.nan if obj.get_stiffener_type() == 'FB' else 0.4*obj.tf*math.sqrt(E/fy))

        bf = list()
        for idx, obj in enumerate([self._LongStf, self._RingStf, self._RingFrame]):
            if obj is None:
                bf.append(np.nan)
            elif obj.get_stiffener_type() == 'FB':
                bf.append(obj.b)
            elif obj.get_stiffener_type() == 'T':
                bf.append((obj.b-obj.tw)/2)
            else:
                bf.append(obj.b-obj.tw)
        bf = np.array(bf)

        hw_div_tw = list()
        for idx, obj in enumerate([self._RingStf, self._RingFrame]):
            if obj is None:
                hw_div_tw.append(np.nan)
            else:
                hw_div_tw.append(obj.hw/obj.tw)
        hw_div_tw = np.array(hw_div_tw)

        #parameters - [alpha, beta, leo, zeta, rf, r0, zt]
        req_hw_div_tw = list()
        for idx, obj in enumerate([self._RingStf, self._RingFrame]):
            if obj is None:
                req_hw_div_tw.append(np.nan)
            else:
                to_append = np.nan if obj.b*obj.tf == 0 else 2/3*math.sqrt(shell_buckling_data['parameters'][idx][4]
                                                                               *(obj.tw*obj.hw)*E/
                                                                               (obj.hw*obj.b*obj.tf*fy))
                req_hw_div_tw.append(to_append)
        req_hw_div_tw = np.array(req_hw_div_tw)

        ef_div_tw = list()
        for idx, obj in enumerate([self._RingStf, self._RingFrame]):
            if obj is None:
                ef_div_tw.append(np.nan)
            else:
                ef_div_tw.append(obj.get_flange_eccentricity())
        ef_div_tw = np.array(ef_div_tw)

        ef_div_tw_req = list()
        for idx, obj in enumerate([self._RingStf, self._RingFrame]):
            if obj is None:
                ef_div_tw_req.append(np.nan)
            else:
                ef_div_tw_req.append(np.nan if obj.b*obj.tf == 0 else
                             1/3*shell_buckling_data['parameters'][idx][4]/obj.hw*obj.hw*obj.tw/(obj.b*obj.tf))
        ef_div_tw_req = np.array(ef_div_tw_req)

        #
        # print(stf_req_h , '>', np.array([np.nan if self._LongStf is None else self._LongStf.hw,
        #                                  np.nan if self._RingStf is None else self._RingStf.hw,
        #                                  np.nan if self._RingFrame is None else self._RingFrame.hw]))
        # print(stf_req_b , '>', bf)
        # print(hw_div_tw , '<', req_hw_div_tw)
        # print(ef_div_tw , '<', ef_div_tw_req)

        chk1 = stf_req_h>np.array([np.nan if self._LongStf is None else self._LongStf.hw,
                                  np.nan if self._RingStf is None else self._RingStf.hw,
                                  np.nan if self._RingFrame is None else self._RingFrame.hw])
        chk1 = [np.nan if np.isnan(val) else chk1[idx] for idx, val in enumerate(stf_req_h)]

        chk2 = stf_req_b > bf
        chk2 = [np.nan if np.isnan(val) else chk2[idx] for idx, val in enumerate(stf_req_b)]

        chk3= hw_div_tw < req_hw_div_tw
        chk3 = [np.nan if np.isnan(val) else chk3[idx] for idx, val in enumerate(req_hw_div_tw)]

        chk4 = ef_div_tw < ef_div_tw_req
        chk4 = [np.nan if np.isnan(val) else chk4[idx] for idx, val in enumerate(ef_div_tw_req)]

        provide_data['stiffener check'] = {'longitudinal':all([chk1[0], chk2[0]]),
                                           'ring stiffener': None if self._RingStf is None else all([chk1[1],chk2[1],chk3[0],chk4[0]]),
                                           'ring frame': None if self._RingStf is None else all([chk1[2],chk2[2],chk3[1],chk4[1]])}
        provide_data['Column stability check'] = stab_chk

        return provide_data

    def get_all_properties(self):
        all_data = {'Main class': self.get_main_properties(),
                    'Shell': self._Shell.get_main_properties(),
                    'Long. stf.': None if self._LongStf is None else self._LongStf.get_structure_prop(),
                    'Ring stf.': None if self._RingStf is None else self.RingStfObj.get_structure_prop(),
                    'Ring frame': None if self._RingFrame is None else self._RingFrame.get_structure_prop()}
        return all_data

    def get_main_properties(self):
        main_dict = {'sasd': [self._sasd, 'Pa'],
                     'smsd': [self._smsd, 'Pa'],
                     'tTsd': [self._tTsd, 'Pa'],
                     'tQsd': [self._tQsd, 'Pa'],
                     'psd': [self._psd, 'Pa'],
                     'shsd': [self._shsd, 'Pa'],
                     'geometry': [self._geometry, ''],
                     'material factor': [self._mat_factor, ''],
                     'delta0': [self._delta0, ''],
                     'fab method ring stf': [self._fab_method_ring_stf, '-'],
                     'fab method ring girder': [self._fab_method_ring_girder, '-'],
                     'E-module': [self._E, 'Pa'],
                     'poisson': [self._v, '-'],
                     'mat_yield': [self._yield, 'Pa'],
                     'length between girders': [self._length_between_girders, 'm'],
                     'panel spacing, s':  [self._panel_spacing, 'm'],
                     'ring stf excluded': [self.__ring_stiffener_excluded, ''],
                     'ring frame excluded': [self.__ring_frame_excluded, '']}
        return main_dict

    def set_main_properties(self, main_dict):
        self._sasd = main_dict['sasd'][0]
        self._smsd = main_dict['smsd'][0]
        self._tTsd = main_dict['tTsd'][0]
        self._tQsd= main_dict['tQsd'][0]
        self._psd = main_dict['psd'][0]
        self._shsd = main_dict['shsd'][0]
        self._geometry = main_dict['geometry'][0]
        self._mat_factor = main_dict['material factor'][0]
        self._delta0 = main_dict['delta0'][0]
        self._fab_method_ring_stf = main_dict['fab method ring stf'][0]
        self._fab_method_ring_girder = main_dict['fab method ring girder'][0]
        self._E = main_dict['E-module'][0]
        self._v = main_dict['poisson'][0]
        self._yield = main_dict['mat_yield'][0]
        self._length_between_girders = main_dict['length between girders'][0]
        self._panel_spacing = main_dict['panel spacing, s'][0]
        self.__ring_stiffener_excluded = main_dict['ring stf excluded'][0]
        self.__ring_frame_excluded = main_dict['ring frame excluded'][0]
        
    def set_stresses_and_pressure(self, val):
        self._sasd = val['sasd']
        self._smsd = val['smsd']
        self._tTsd = val['tTsd']
        self._tQsd= val['tQsd']
        self._psd = val['psd']
        self._shsd = val['shsd']
        
    def get_x_opt(self):
        '''
        shell       (0.02, 2.5, 5, 5, 10, nan, nan, nan),
        long        (0.875, nan, 0.3, 0.01, 0.1, 0.01, nan, nan),
        ring        (nan, nan, 0.3, 0.01, 0.1, 0.01, nan, nan),
        ring        (nan, nan, 0.7, 0.02, 0.2, 0.02, nan, nan)] 
        '''
        shell = [self._Shell.thk, self._Shell.radius, self._Shell.dist_between_rings, self._Shell.length_of_shell, 
                 self._Shell.tot_cyl_length, np.nan, np.nan, np.nan]
        if self._LongStf is not None:
            long = [self._LongStf.s/1000, np.nan, self._LongStf.hw/1000, self._LongStf.tw/1000, self._LongStf.b/1000, 
                    self._LongStf.tf/1000, np.nan, np.nan]
        else:
            long = [0 for dummy in range(8)]
        
        if self._RingStf is not None:
            ring_stf = [self._RingStf.s/1000, np.nan, self._RingStf.hw/1000, self._RingStf.tw/1000, self._RingStf.b/1000, 
                    self._RingStf.tf/1000, np.nan, np.nan]
        else:
            ring_stf = [0 for dummy in range(8)]
        
        if self._RingFrame is not None:
            ring_fr = [self._RingFrame.s/1000, np.nan, self._RingFrame.hw/1000, self._RingFrame.tw/1000, self._RingFrame.b/1000, 
                    self._RingFrame.tf/1000, np.nan, np.nan]
        else:
            ring_fr = [0 for dummy in range(8)]

        return [shell, long, ring_stf, ring_fr]

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
        thk_eff = math.log10(max(1,self._plate_th/25)) * k
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

class PULSpanel():
    '''
    Takes care of puls runs
    '''
    def __init__(self, run_dict: dict = {}, puls_acceptance: float = 0.87, puls_sheet_location: str = None):
        super(PULSpanel, self).__init__()

        self._all_to_run = run_dict
        self._run_results = {}
        self._puls_acceptance = puls_acceptance
        self._puls_sheet_location = puls_sheet_location
        self._all_uf = {'buckling': list(), 'ultimate': list()}

    @property
    def all_uf(self):
        return self._all_uf

    @property
    def puls_acceptance(self):
        return self._puls_acceptance

    @puls_acceptance.setter
    def puls_acceptance(self, val):
        self._puls_acceptance = val

    @property
    def puls_sheet_location(self):
        return self._puls_sheet_location

    @puls_sheet_location.setter
    def puls_sheet_location(self, val):
        self._puls_sheet_location = val

    def set_all_to_run(self, val):
        self._all_to_run = val

    def get_all_to_run(self):
        return self._all_to_run

    def get_run_results(self):
        return self._run_results

    def set_run_results(self, val):
        self._run_results = val
        for key in self._run_results.keys():
            if any([key == 'sheet location',type(self._run_results[key]['Buckling strength']) != dict,
                    type(self._run_results[key]['Ultimate capacity']) != dict]): # TODO CHECK
                continue

            if all([type(self._run_results[key]['Buckling strength']['Actual usage Factor'][0]) == float,
                    type(self._run_results[key]['Ultimate capacity']['Actual usage Factor'][0]) == float]):
                self._all_uf['buckling'].append(self._run_results[key]['Buckling strength']['Actual usage Factor'][0])
                self._all_uf['ultimate'].append(self._run_results[key]['Ultimate capacity']['Actual usage Factor'][0])
        self._all_uf['buckling'] = np.unique(self._all_uf['buckling']).tolist()
        self._all_uf['ultimate'] = np.unique(self._all_uf['ultimate']).tolist()

    def run_all(self, store_results = False):
        '''
        Returning following results.:

        Identification:  name of line/run
        Plate geometry:       dict_keys(['Length of panel', 'Stiffener spacing', 'Plate thick.'])
        Primary stiffeners: dict_keys(['Number of stiffeners', 'Stiffener type', 'Stiffener boundary', 'Stiff. Height',
                            'Web thick.', 'Flange width', 'Flange thick.', 'Flange ecc.', 'Tilt angle'])
        Secondary stiffeners. dict_keys(['Number of sec. stiffeners', 'Secondary stiffener type', 'Stiffener boundary',
                            'Stiff. Height', 'Web thick.', 'Flange width', 'Flange thick.'])
        Model imperfections. dict_keys(['Imp. level', 'Plate', 'Stiffener', 'Stiffener tilt'])
        Material: dict_keys(['Modulus of elasticity', "Poisson's ratio", 'Yield stress plate', 'Yield stress stiffener'])
        Aluminium prop: dict_keys(['HAZ pattern', 'HAZ red. factor'])
        Applied loads: dict_keys(['Axial stress', 'Trans. stress', 'Shear stress', 'Pressure (fixed)'])
        Bound cond.: dict_keys(['In-plane support'])
        Global elastic buckling: dict_keys(['Axial stress', 'Trans. Stress', 'Trans. stress', 'Shear stress'])
        Local elastic buckling: dict_keys(['Axial stress', 'Trans. Stress', 'Trans. stress', 'Shear stress'])
        Ultimate capacity: dict_keys(['Actual usage Factor', 'Allowable usage factor', 'Status'])
        Failure modes: dict_keys(['Plate buckling', 'Global stiffener buckling', 'Torsional stiffener buckling',
                            'Web stiffener buckling'])
        Buckling strength: dict_keys(['Actual usage Factor', 'Allowable usage factor', 'Status'])
        Local geom req (PULS validity limits): dict_keys(['Plate slenderness', 'Web slend', 'Web flange ratio',
                            'Flange slend ', 'Aspect ratio'])
        CSR-Tank requirements (primary stiffeners): dict_keys(['Plating', 'Web', 'Web-flange', 'Flange', 'stiffness'])

        :return:
        '''
        import ANYstructure_local.excel_inteface as pulsxl

        iterator = self._all_to_run

        newfile = self._puls_sheet_location

        my_puls = pulsxl.PulsExcel(newfile, visible=False)
        #my_puls.set_multiple_rows(20, iterator)
        run_sp, run_up = my_puls.set_multiple_rows_batch(iterator)
        my_puls.calculate_panels(sp=run_sp, up=run_up)
        #all_results = my_puls.get_all_results()
        all_results = my_puls.get_all_results_batch(sp = run_sp, up=run_up)

        for id, data in all_results.items():
            self._run_results[id] = data

        my_puls.close_book(save=False)

        self._all_uf = {'buckling': list(), 'ultimate': list()}
        for key in self._run_results.keys():
            try:
                if all([type(self._run_results[key]['Buckling strength']['Actual usage Factor'][0]) == float,
                        type(self._run_results[key]['Ultimate capacity']['Actual usage Factor'][0]) == float]):
                    self._all_uf['buckling'].append(self._run_results[key]['Buckling strength']
                                                    ['Actual usage Factor'][0])
                    self._all_uf['ultimate'].append(self._run_results[key]['Ultimate capacity']
                                                    ['Actual usage Factor'][0])
            except TypeError:
                print('Got a type error. Life will go on. Key for PULS run results was', key)
                print(self._run_results[key])
        self._all_uf['buckling'] = np.unique(self._all_uf['buckling']).tolist()
        self._all_uf['ultimate'] = np.unique(self._all_uf['ultimate']).tolist()
        if store_results:
            store_path = os.path.dirname(os.path.abspath(__file__))+'\\PULS\\Result storage\\'
            with open(store_path+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")+'_UP.json', 'w') as file:
                file.write(json.dumps(all_results, ensure_ascii=False))
        return all_results

    def get_utilization(self, line, method, acceptance = 0.87):
        if line in self._run_results.keys():
            if method == 'buckling':
                if type(self._run_results[line]['Buckling strength']['Actual usage Factor'][0]) == str or \
                        self._run_results[line]['Buckling strength']['Actual usage Factor'][0] is None:
                    return None
                return self._run_results[line]['Buckling strength']['Actual usage Factor'][0]/acceptance
            else:
                if type(self._run_results[line]['Ultimate capacity']['Actual usage Factor'][0]) == str or \
                        self._run_results[line]['Buckling strength']['Actual usage Factor'][0] is None:
                    return None
                return self._run_results[line]['Ultimate capacity']['Actual usage Factor'][0]/acceptance
        else:
            return None

    # def run_all_multi(self):
    #
    #     tasks = []
    #
    #     if len(self._all_to_run) > 20:
    #         processes = 10#max(cpu_count() - 1, 1)
    #
    #         def chunks(data, SIZE=10000):
    #             it = iter(data)
    #             for i in range(0, len(data), SIZE):
    #                 yield {k: data[k] for k in islice(it, SIZE)}
    #
    #         # Sample run:
    #
    #         for item in chunks({key: value for key, value in ex.run_dict.items()}, int(len(self._all_to_run)/processes)):
    #             tasks.append(item)
    #     else:
    #         tasks.append(self._all_to_run)
    #     # [print(task) for task in tasks]
    #     # print(self._all_to_run)
    #     # quit()
    #     queue = multiprocessing.SimpleQueue()
    #
    #     for idx, name in enumerate(tasks):
    #         p = Process(target=self.run_all_multi_sub, args=(name, queue, idx+1))
    #         p.start()
    #     p.join()
    #     for task in tasks:
    #         print(queue.get())

    # def run_all_multi_sub(self, iterator, queue = None, idx = 0):
    #     '''
    #     Returning following results.:
    #
    #     Identification:  name of line/run
    #     Plate geometry:       dict_keys(['Length of panel', 'Stiffener spacing', 'Plate thick.'])
    #     Primary stiffeners: dict_keys(['Number of stiffeners', 'Stiffener type', 'Stiffener boundary', 'Stiff. Height',
    #                         'Web thick.', 'Flange width', 'Flange thick.', 'Flange ecc.', 'Tilt angle'])
    #     Secondary stiffeners. dict_keys(['Number of sec. stiffeners', 'Secondary stiffener type', 'Stiffener boundary',
    #                         'Stiff. Height', 'Web thick.', 'Flange width', 'Flange thick.'])
    #     Model imperfections. dict_keys(['Imp. level', 'Plate', 'Stiffener', 'Stiffener tilt'])
    #     Material: dict_keys(['Modulus of elasticity', "Poisson's ratio", 'Yield stress plate', 'Yield stress stiffener'])
    #     Aluminium prop: dict_keys(['HAZ pattern', 'HAZ red. factor'])
    #     Applied loads: dict_keys(['Axial stress', 'Trans. stress', 'Shear stress', 'Pressure (fixed)'])
    #     Bound cond.: dict_keys(['In-plane support'])
    #     Global elastic buckling: dict_keys(['Axial stress', 'Trans. Stress', 'Trans. stress', 'Shear stress'])
    #     Local elastic buckling: dict_keys(['Axial stress', 'Trans. Stress', 'Trans. stress', 'Shear stress'])
    #     Ultimate capacity: dict_keys(['Actual usage Factor', 'Allowable usage factor', 'Status'])
    #     Failure modes: dict_keys(['Plate buckling', 'Global stiffener buckling', 'Torsional stiffener buckling',
    #                         'Web stiffener buckling'])
    #     Buckling strength: dict_keys(['Actual usage Factor', 'Allowable usage factor', 'Status'])
    #     Local geom req (PULS validity limits): dict_keys(['Plate slenderness', 'Web slend', 'Web flange ratio',
    #                         'Flange slend ', 'Aspect ratio'])
    #     CSR-Tank requirements (primary stiffeners): dict_keys(['Plating', 'Web', 'Web-flange', 'Flange', 'stiffness'])
    #
    #     :return:
    #     '''
    #     old_file = os.path.dirname(os.path.abspath(__file__))+'\\PULS\\PulsExcel_new - Copy (1).xlsm'
    #     new_file = os.path.dirname(os.path.abspath(__file__))+'\\PULS\\PulsExcel_new - Copy multi ('+str(idx)+').xlsm'
    #     shutil.copy(old_file, new_file)
    #     #time.sleep(idx*5)
    #     pythoncom.CoInitialize()
    #
    #     my_puls = pulsxl.PulsExcel(new_file, visible=False)
    #     try:
    #         my_puls.set_multiple_rows_batch(20, iterator)
    #         my_puls.calculate_panels()
    #         all_results = my_puls.get_all_results_batch()
    #         my_puls.close_book(save=True)
    #         queue.put(all_results)
    #         os.remove(new_file)
    #     except (BaseException, AttributeError):
    #         my_puls.close_book(save=False)
    #         queue.put(None)

    def get_puls_line_results(self, line):
        if line not in self._run_results.keys():
            return None
        else:
            return self._run_results[line]

    def get_string(self, line, uf = 0.87):
        '''
        :param line:
        :return:
        '''

        results = self._run_results[line]
        loc_geom = 'Ok' if all([val[0] == 'Ok' for val in results['Local geom req (PULS validity limits)']
                              .values()]) else 'Not ok'
        csr_geom = 'Ok' if all([val[0] == 'Ok' for val in results['CSR-Tank requirements (primary stiffeners)']
                              .values()]) else 'Not ok'

        ret_str = 'PULS results\n\n' +\
                  'Ultimate capacity usage factor:  ' + str(results['Ultimate capacity']['Actual usage Factor'][0]/uf)+'\n'+\
                  'Buckling strength usage factor:  ' + str(results['Buckling strength']['Actual usage Factor'][0]/uf)+'\n'+\
                  'Local geom req (PULS validity limits):   ' + loc_geom + '\n'+\
                  'CSR-Tank requirements (primary stiffeners):   ' + csr_geom
        return ret_str

    def result_changed(self, id):
        if id in self._run_results.keys():
            self._run_results.pop(id)

    def generate_random_results(self, batch_size: int = 1000, stf_type: str = None):
        '''
        Genrate random results based on user input.
        :return:
        '''

        '''
        Running iterator:
        run_dict_one = {'line3': {'Identification': 'line3', 'Length of panel': 4000.0, 'Stiffener spacing': 700.0,
                          'Plate thickness': 18.0, 'Number of primary stiffeners': 10, 'Stiffener type (L,T,F)': 'T',
                          'Stiffener boundary': 'C', 'Stiff. Height': 400.0, 'Web thick.': 12.0, 'Flange width': 200.0,
                          'Flange thick.': 20.0, 'Tilt angle': 0, 'Number of sec. stiffeners': 0,
                          'Modulus of elasticity': 210000.0, "Poisson's ratio": 0.3, 'Yield stress plate': 355.0,
                          'Yield stress stiffener': 355.0, 'Axial stress': 101.7, 'Trans. stress 1': 100.0,
                          'Trans. stress 2': 100.0, 'Shear stress': 5.0, 'Pressure (fixed)': 0.41261,
                          'In-plane support': 'Int'}}
        '''
        run_dict = {}

        profiles = hlp.helper_read_section_file('bulb_anglebar_tbar_flatbar.csv')
        if stf_type is not None:
            new_profiles = list()
            for stf in profiles:
                if stf['stf_type'][0] == stf_type:
                    new_profiles.append(stf)
            profiles = new_profiles
        lengths = np.arange(2000,6000,100)
        spacings = np.arange(500,900,10)
        thks = np.arange(10,25,1)
        axstress =transsress1 = transsress2 = shearstress = np.arange(-200,210,10) #np.concatenate((np.arange(-400,-200,10), np.arange(210,410,10)))

        pressures =  np.arange(0,0.45,0.01)
        now = time.time()
        yields = np.array([235,265,315,355,355,355,355,390,420,460])
        for idx in range(batch_size):
            ''' Adding 'Stiffener type (L,T,F)': self.stf_type,  'Stiffener boundary': 'C',
                'Stiff. Height': self.stf_web_height*1000, 'Web thick.': self.stf_web_thk*1000, 
                'Flange width': self.stf_flange_width*1000, 'Flange thick.': self.stf_flange_thk*1000}'''

            this_id = 'run_' + str(idx) + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            this_stf = random.choice(profiles)

            if random.choice([True, False]):
                boundary = 'Int'
            else:
                boundary = random.choice(['GL', 'GT'])
            if random.choice([True, True, True, False]):
                stf_boundary = 'C'
            else:
                stf_boundary = 'S'
            #boundary = 'Int'
            #stf_boundary = 'C'


            yieldstress = np.random.choice(yields)
            if random.choice([True, True, True, False]):
                transstress1 = np.random.choice(transsress1)  # Using same value for trans1 and trans 2
                transstress2 = transstress1
            else:
                transstress1 = np.random.choice(transsress1)
                transstress2 = np.random.choice(transsress2)

            # run_dict[this_id] = {'Identification': this_id, 'Length of panel': np.random.choice(lengths),
            #                      'Stiffener spacing': np.random.choice(spacings),
            #                      'Plate thickness': np.random.choice(thks), 'Number of primary stiffeners': 10,
            #                      'Stiffener type (L,T,F)': 'F' if this_stf['stf_type'][0] == 'FB' else this_stf['stf_type'][0],
            #                      'Stiffener boundary': stf_boundary,
            #                      'Stiff. Height': this_stf['stf_web_height'][0]*1000,
            #                      'Web thick.': this_stf['stf_web_thk'][0]*1000,
            #                      'Flange width': 0 if this_stf['stf_type'][0] == 'F'
            #                      else this_stf['stf_flange_width'][0]*1000,
            #                      'Flange thick.': 0 if  this_stf['stf_type'][0] == 'F'
            #                      else this_stf['stf_flange_thk'][0]*1000,
            #                      'Tilt angle': 0, 'Number of sec. stiffeners': 0,
            #                      'Modulus of elasticity': 210000, "Poisson's ratio": 0.3,
            #                      'Yield stress plate':yieldstress, 'Yield stress stiffener': yieldstress,
            #                      'Axial stress': 0 if boundary == 'GT' else np.random.choice(axstress),
            #                      'Trans. stress 1': 0 if boundary == 'GL' else transstress1,
            #                      'Trans. stress 2': 0 if boundary == 'GL' else transstress2,
            #                      'Shear stress': np.random.choice(shearstress),
            #                      'Pressure (fixed)': 0 if stf_boundary == 'S' else np.random.choice(pressures),
            #                      'In-plane support': boundary, 'sp or up': 'SP'}

            same_ax = np.random.choice(axstress)
            lengths = np.arange(100, 6000, 100)
            spacings = np.arange(100, 26000, 100)
            thks = np.arange(10, 50, 1)
            boundary = random.choice(['GL', 'GT'])

            if np.random.choice([True,False,False,False]):
                support = ['SS','SS','SS','SS']
            elif np.random.choice([True,False,False,False]):
                support = ['CL','CL','CL','CL']
            else:
                support = [np.random.choice(['SS', 'CL']),np.random.choice(['SS', 'CL']),
                           np.random.choice(['SS', 'CL']),np.random.choice(['SS', 'CL'])]
            if np.random.choice([True,False]):
                press = 0
            else:
                press = np.random.choice(pressures)
            run_dict[this_id] = {'Identification': this_id, 'Length of plate': np.random.choice(lengths),
                                 'Width of c': np.random.choice(spacings),
                           'Plate thickness': np.random.choice(thks),
                         'Modulus of elasticity': 210000, "Poisson's ratio": 0.3,
                                 'Yield stress plate':yieldstress,
                         'Axial stress 1': 0 if boundary == 'GT' else same_ax,
                           'Axial stress 2': 0 if boundary == 'GT' else same_ax,
                           'Trans. stress 1': 0 if boundary == 'GL' else transstress1,
                         'Trans. stress 2': 0 if boundary == 'GL' else transstress2,
                           'Shear stress': np.random.choice(shearstress), 'Pressure (fixed)': press,
                                 'In-plane support': boundary,
                         'Rot left': support[0], 'Rot right': support[1],
                                 'Rot upper': support[2], 'Rot lower': support[3],
                           'sp or up': 'UP'}

        self._all_to_run = run_dict
        self.run_all(store_results=True)
        print('Time to run', batch_size, 'batches:', time.time() - now)

def f(name, queue):
    import time
    #print('hello', name)
    time.sleep(2)
    queue.put(name)


if __name__ == '__main__':
    import ANYstructure_local.example_data as ex
    # PULS = PULSpanel(ex.run_dict, puls_sheet_location=r'C:\Github\ANYstructure\ANYstructure\PULS\PulsExcel_new - Copy (1).xlsm')
    # PULS.run_all_multi()
    # PULS = PULSpanel(puls_sheet_location=r'C:\Github\ANYstructure\ANYstructure_local\PULS\PulsExcel_new - generator.xlsm')
    # for dummy in range(100):
    #     PULS.generate_random_results(batch_size=10000)
    # import ANYstructure_local.example_data as test
    # from multiprocessing import Process
    #
    # queue = multiprocessing.SimpleQueue()
    # tasks = ['a', 'b', 'c']
    # for name in tasks:
    #     p = Process(target=f, args=(name,queue))
    #     p.start()
    #
    # for task in tasks:
    #     print(queue.get())


    # print('Fatigue test: ')
    # my_test = CalcFatigue(test.obj_dict, test.fat_obj_dict)
    # print('Total damage: ',my_test.get_total_damage(int_press=(0,0,0), ext_press=(50000, 60000,0)))
    # print('')
    # print('Buckling test: ')
    #
    # my_buc = test.get_structure_calc_object()
    #
    # #print(my_buc.calculate_buckling_all(design_lat_press=100))
    # print(my_buc.calculate_slamming_plate(1000000))
    # print(my_buc.calculate_slamming_stiffener(1000000))
    # print(my_buc.get_net_effective_plastic_section_modulus())

    #my_test.get_total_damage(int_press=(0, 0, 0), ext_press=(0, 40000, 0))
    import ANYstructure_local.example_data as ex
    for example in [CalcScantlings(ex.obj_dict)]:#, CalcScantlings(ex.obj_dict2), CalcScantlings(ex.obj_dict_L)]:
        my_test = example
        #my_test = CalcScantlings(example)
        #my_test = CalcFatigue(example, ex.fat_obj_dict2)
        #my_test.get_total_damage(int_press=(0, 0, 0), ext_press=(0, 40000, 0))
        #print('Total damage: ', my_test.get_total_damage(int_press=(0, 0, 0), ext_press=(0, 40000, 0)))
        #print(my_test.get_fatigue_properties())
        pressure = 200
        # print(my_test.buckling_local_stiffener())
        # print('SHEAR CENTER: ',my_test.get_shear_center())
        # print('SECTION MOD: ',my_test.get_section_modulus())
        # print('SECTION MOD FLANGE: ', my_test.get_section_modulus()[0])
        # print('SHEAR AREA: ', my_test.get_shear_area())
        # print('PLASTIC SECTION MOD: ',my_test.get_plasic_section_modulus())
        # print('MOMENT OF INTERTIA: ',my_test.get_moment_of_intertia())
        # print('WEIGHT', my_test.get_weight())
        # print('PROPERTIES', my_test.get_structure_prop())
        # print('CROSS AREA', my_test.get_cross_section_area())
        # print()
        #
        # print('EFFICIENT MOMENT OF INTERTIA: ',my_test.get_moment_of_intertia(efficent_se=my_test.get_plate_efficent_b(
        #     design_lat_press=pressure)))
        # print('Se: ',my_test.calculate_buckling_all(design_lat_press=pressure,checked_side='s'))
        # print('Se: ', my_test.calculate_buckling_all(design_lat_press=pressure, checked_side='p'))
        # print('MINIMUM PLATE THICKNESS',my_test.get_dnv_min_thickness(pressure))
        # print('MINIMUM SECTION MOD.', my_test.get_dnv_min_section_modulus(pressure))
        print()
        #my_test.cyl_buckling_long_sft_shell()


    #Structure(ex.obj_dict_cyl_ring)
    #Structure(ex.obj_dict_cyl_heavy_ring)
    my_cyl = CylinderAndCurvedPlate(main_dict = ex.shell_main_dict2, shell= Shell(ex.shell_dict),
                                    long_stf= Structure(ex.obj_dict_cyl_long2),
                                    ring_stf = None,# Structure(ex.obj_dict_cyl_ring2),
                                    ring_frame= Structure(ex.obj_dict_cyl_heavy_ring2))
    print(my_cyl.get_utilization_factors())
