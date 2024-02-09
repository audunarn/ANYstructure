# units are SI units, unless noted otherwise in local funcions
# still to find a better way to calculate section 7.5 on a stiffener object, so it works on both stiffener and girder
import logging
import math
from typing import Union, Dict, Any
from enum import Enum


# Create a custom logger
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# so not to create another handler if it has already been defined in another module
# doesn't seem to be working for file, but there the problem of multiple logs does not occur
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class Material:

    def __init__(self, young: float, poisson: float, strength: float, mat_factor: float=1.15, density: float=7850):
        self._young: float = young
        self._poisson: float = poisson
        self._strength: float = strength
        self._mat_factor: float = mat_factor
        self._density: float = density


    def __str__(self) -> str:
        return 'Young\'s modulus: ' + str(self._young) + ' Poisson ratio: ' + str(self._poisson) + ' Yield strength: ' + str(self._strength)


    def ToShortString(self) -> str:
        return 'Y' + str(self._strength)


    def get_fy(self) -> float:
        '''
        Return material yield
        :return:
        '''
        return self._strength


class Plate:

    def __init__(self, spacing: float, span: float, thickness:float=0, material: Material=Material(206e9, 0.3, 235e6, 7850)):
        self._spacing: float = spacing
        self._span: float = span
        self._thickness: float = thickness
        self._material: Material = material


    def ToShortString(self) -> str:
        return 'lxb' + str(self._span) + 'x' + str(self._spacing)


    # Property decorators are used in buckling. IN mm!    
    @property # in mm
    def s(self):
        return self._spacing * 1000
    @s.setter # in mm
    def s(self, val):
        self._spacing = val / 1000

    @property # in mm
    def l(self):
        return self._span * 1000
    @l.setter # in mm
    def l(self, val):
        self._span = val / 1000

    @property # in mm
    def th(self):
        return self._thickness * 1000
    @th.setter # in mm
    def th(self, val):
        self._thickness = val / 1000


class Stiffener:

    def __init__(self, type: str, web_height: float, web_thickness: float, flange_width: float, flange_thickness: float, dist_between_lateral_supp: float=None, fabrication_method: str = 'welded', flange_eccentricity: float = 0, material: Material = Material(206e9, 0.3, 235e6, 7850)): # type: ignore
        self._stiffener_type: str = type
        self._web_height: float = web_height
        self._web_th: float = web_thickness
        self._flange_width: float = flange_width
        self._flange_th: float = flange_thickness
        self._dist_between_lateral_supp: float = dist_between_lateral_supp
        self._fabrication_method: str = fabrication_method
        self._flange_eccentricity: float = flange_eccentricity
        self._material: Material = material

    def ToShortString(self) -> str:
        return 'wHxwTxfWxfT' + str(round(self._web_height, 3)) + 'x' + str(round(self._web_th, 3)) + 'x' + str(round(self._flange_width, 3)) + 'x' + str(round(self._flange_th, 3))

    # Property decorators are used in buckling. IN mm!    
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
        return self._spacing * 1000
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
    def dist_between_lateral_supp(self):
        if self._dist_between_lateral_supp == None:
            return None
        return self._dist_between_lateral_supp* 1000
    @dist_between_lateral_supp.setter  # in mm
    def dist_between_lateral_supp(self, val):
        if self._dist_between_lateral_supp == None:
            return None
        self._dist_between_lateral_supp = val / 1000 

    @property
    def stiffener_type(self):
        return self._stiffener_type
    @stiffener_type.setter
    def stiffener_type(self, val):
        self._stiffener_type = val

    @property  # in mm
    def As(self):
        return self.tw * self.hw + self.b * self.tf


    def get_beam_string(self) -> str:
        ''' Returning a string. '''
        if type(self._stiffener_type) != str:
            print('error')

        base_name = self._stiffener_type+ '_' + str(round(self._web_height*1000, 0)) + 'x' + \
                   str(round(self._web_th*1000, 0))
        if self._stiffener_type == 'FB':
            ret_str = base_name
        elif self._stiffener_type in ['L-bulb', 'bulb', 'hp']:
            ret_str = 'Bulb'+str(int(self._web_height*1000 + self._flange_th*1000))+'x'+\
                      str(round(self._web_th*1000, 0))+ '_(' +str(round(self._web_height*1000, 0)) + 'x' + \
                   str(round(self._web_th*1000, 0))+'_'+ str(round(self._flange_width*1000, 0)) + 'x' + \
                      str(round(self._flange_th*1000, 0))+')'
        else:
            ret_str = base_name + '__' + str(round(self._flange_width*1000, 0)) + 'x' + \
                      str(round(self._flange_th*1000, 0))

        ret_str = ret_str.replace('.', '_')

        return ret_str


    def get_torsional_moment_venant(self, reduced_tw=None) -> float:
        """
        Calculate and return the torsional moment of inertia based on Venant's theorem.

        Parameters:
        -----------
        reduced_tw : float, optional
            Reduced web thickness. If not provided, the original web thickness is used.

        Returns:
        --------
        float
            Torsional moment of inertia based on Venant's theorem.

        Notes:
        ------
        The torsional moment of inertia is computed based on the dimensions and properties of the structure,
        using Venant's theorem for thin-walled open sections.
        """
        tf = self._flange_th * 1000
        tw = self._web_th * 1000 if reduced_tw is None else reduced_tw
        bf = self._flange_width * 1000
        hw = self._web_height * 1000

        I_t1 = 1.0 / 3.0 * math.pow(tw , 3) * hw + 1.0 / 3.0 * math.pow(tf, 3) * bf

        return I_t1


    def get_flange_eccentricity(self) -> float:
        """
        Calculate and return the flange eccentricity.

        Returns:
        --------
        float
            Flange eccentricity.

        Notes:
        ------
        The flange eccentricity is determined based on the type of stiffener in the structure.
        For 'FB' or 'T' type stiffeners, the eccentricity is set to 0. For other types, it is calculated as the distance
        between the center of the flange width and the center of the web thickness.
        """
        ecc = 0 if self._stiffener_type in ['FB', 'T'] else self._flange_width / 2 - self._web_th / 2
        return ecc


    def get_polar_moment(self, reduced_tw=None) -> float:
        """
        Calculate and return the polar moment of inertia.

        Parameters:
        -----------
        reduced_tw : float, optional
            Reduced web thickness. If not provided, the original web thickness is used.

        Returns:
        --------
        float
            Polar moment of inertia.

        Notes:
        ------
        The polar moment of inertia is computed based on the dimensions and properties of the structure.
        If reduced_tw is provided, it is used as the reduced web thickness; otherwise, the original web thickness is used.
        """
        tf = self._flange_th * 1000
        tw = self._web_th * 1000 if reduced_tw is None else reduced_tw
        ef = self.get_flange_eccentricity() * 1000
        hw = self._web_height * 1000
        b = self._flange_width * 1000

        Ipo = tw / 3 * math.pow(hw, 3) + tf * (math.pow(hw + tf /2, 2) * b) + tf / 3 * (math.pow(ef + b / 2, 3) - math.pow(ef - b / 2, 3)) + \
              (b * math.pow(tf, 3)) / 12 + (hw * math.pow(tw, 3)) / 12

        return Ipo


    def get_ef_iacs(self) -> float:
        """
        Calculate and return the effective flange height (ef) based on IACS rules.

        Returns:
        --------
        float
            Effective flange height (ef).

        Notes:
        ------
        The effective flange height is determined based on the type of stiffener in the structure according to IACS rules.
        For 'FB' type stiffeners, ef is equal to the web height. For other types ('L', 'T', 'L-bulb', 'HP-profile', 'HP', 'HP-bulb'),
        ef is calculated as the sum of the web height and half of the flange thickness.
        """
        if self._stiffener_type == 'FB':
            ef = self._web_height
        elif self._stiffener_type in ['L', 'T', 'L-bulb', 'HP-profile', 'HP', 'HP-bulb']:
            ef = self._web_height + 0.5 * self._flange_th
        else:
            raise TypeError("Stiffener of type " + self._stiffener_type + " not implemented in get_ef_iacs")
        return ef


    def get_stf_cog_eccentricity(self) -> float:
        """
        Calculate and return the centroidal axis eccentricity of the stiffener.

        Returns:
        --------
        float
            Centroidal axis eccentricity of the stiffener.

        Notes:
        ------
        The centroidal axis eccentricity is computed based on the dimensions and properties of the stiffener,
        taking into account the web height, web thickness, flange width, and flange thickness.
        """
        e = (self._web_height * self._web_th * (self._web_height / 2) + self._flange_width * self._flange_th *
             (self._web_height + self._web_th / 2)) / (self._web_height * self._web_th + self._flange_width * self._flange_th)
        return e


    def get_moment_of_intertia(self, plate_thickness: float=0, plate_width: float=0, reduced_tw=None) -> float:
        """
        Calculate the moment of inertia (Iy) for a stiffener.

        Parameters:
        -----------
        plate_thickness : float, optional
            Thickness of the plate to used in the calculation of stiffener with plate, in meter
        plate_width : bool, optional
            Width of the plate to used in the calculation of stiffener with plate, in meter
        reduced_tw : float, optional
            Reduced web thickness for the stiffener, in meter. If not provided, the original web thickness is used.

        Returns:
        --------
        float
            Moment of inertia (Iy) of the structure with or without the plate depending if plate parameters are provided

        Notes:
        ------
        If no parameters are provided the value is of stiffener without plate
        If plate thickness and width are provided, the value is of stiffener with plate
        If reduced_tw is provided, this value is used instead of the web thickness.
        """
        if plate_thickness != 0:
            assert plate_thickness > 0, "Cannot have a negative plate thickness"
            assert plate_width > 0, "If plate thickness is provided, also the width must be provided and positive."

        tf1 = plate_thickness
        b1 = plate_width

        h = self._flange_th + self._web_height + tf1
        tw = self._web_th if reduced_tw == None else reduced_tw / 1000
        hw = self._web_height
        tf2 = self._flange_th
        b2 = self._flange_width

        Ax = tf1 * b1 + tf2 * b2 + hw * tw
        Iyc = (1 / 12) * (b1 * math.pow(tf1, 3) + b2 * math.pow(tf2, 3) + tw * math.pow(hw, 3))
        ez = (tf1 * b1 * (h - tf1 / 2) + hw * tw * (tf2 + hw / 2) + tf2 * b2 * (tf2 / 2)) / Ax
        Iy = Iyc + (tf1 * b1 * math.pow(tf2 + hw + tf1 / 2, 2) + tw * hw * math.pow(tf2 + hw / 2, 2) +
             tf2 * b2 * math.pow(tf2 / 2, 2)) - Ax * math.pow(ez, 2)

        return Iy


    def get_Iz_moment_of_inertia(self, reduced_tw=None) -> float:
        """
        Calculate the moment of inertia (Iz) for a stiffener based on its type.

        Parameters:
        ----------
        reduced_tw : float, optional
            Reduced web thickness. If not provided, the original web thickness is used.

        Returns:
        -------
        float
            Moment of inertia (Iz) of the stiffener.

        Notes:
        ------
        This method calculates the moment of inertia based on the type of stiffener:
        - For 'FB' type, Iz = tw^3 * hw / 12
        - For 'T' type, Iz = (hw * tw^3 / 12) + (tf2 * b2^3 / 12)
        - For other types, a more complex calculation involving centroid and individual moments of inertia is performed.

        """
        tw = self._web_th * 1000 if reduced_tw is None else reduced_tw
        hw = self._web_height * 1000
        tf2 = self._flange_th * 1000
        b2 = self._flange_width * 1000

        if self._stiffener_type == 'FB':
            Iz = math.pow(tw, 3) * hw / 12
        elif self._stiffener_type == 'T':
            Iz = hw * math.pow(tw, 3) / 12 + tf2 * math.pow(b2, 3) / 12
        else:
            Czver = tw / 2
            Czhor = b2 / 2
            Aver = hw * tw
            Ahor = b2 * tf2
            Atot = Aver + Ahor

            Czoverall = Aver * Czver / Atot + Ahor * Czhor / Atot
            dz = Czver - Czoverall

            Iver = (1 / 12) * hw * math.pow(tw, 3) + Aver * math.pow(dz, 2)

            dz = Czhor - Czoverall
            Ihor = (1 / 12) * tf2 * math.pow(b2, 3) + Ahor * math.pow(dz, 2)

            Iz = Iver + Ihor

        return Iz
    

    def get_moment_of_interia_iacs(self):
        """
        Calculate and return the moment of inertia based on IACS rules.

        Parameters:
        -----------
        efficient_se : float, optional
            Efficient spacing for the plate. If not provided, default values are used.
        only_stf : bool, optional
            If True, considers only the stiffener and ignores plate contributions. Default is False.

        Returns:
        --------
        float
            Moment of inertia based on IACS rules.

        Notes:
        ------
        The moment of inertia is computed based on the dimensions and properties of the plate and stiffener elements in the structure,
        following the International Association of Classification Societies (IACS) rules.
        """
        tw = self._web_th
        hw = self._web_height
        tf2 = self._flange_th
        b2 = self._flange_width

        Af = b2 * tf2
        Aw = hw * tw

        ef = hw + tf2 / 2

        Iy = (Af * math.pow(ef, 2) * math.pow(b2, 2) / 12) * ( (Af + 2.6 * Aw) / (Af + Aw))
        
        return Iy


    def get_section_modulus(self, plate_thickness: float=0, plate_width: float=0) -> tuple[float, float]:
        """
        Calculate and return the section moduluses in the y-axis.

        Parameters:
        -----------
        plate_thickness : float, optional
            Thickness of the plate to used in the calculation of stiffener with plate, in meter
        plate_width : bool, optional
            Width of the plate to used in the calculation of stiffener with plate, in meter

        Returns:
        --------
        Tuple[float, float]
            Section moduluses Wey1 and Wey2 in the y-axis.

        Notes:
        ------
        If no parameters are provided the value is of stiffener without plate
        If plate thickness and width are provided, the value is of stiffener with plate
        """
        #Plate. When using DNV table, default values are used for the plate
        b1 = plate_width
        tf1 = plate_thickness

        #Stiffener
        tf2 = self._flange_th
        b2 = self._flange_width
        h = self._flange_th + self._web_height + tf1
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


    def get_cross_section_centroid_with_effective_plate(self, plate_thickness: float, plate_width: float, reduced_tw=None) -> float:
        """
        Calculate and return the cross-sectional centroid with effective plate.

        Parameters:
        -----------
        Parameters:
        -----------
        plate_thickness : float
            Thickness of the plate to used in the calculation of stiffener with plate, in meter
        plate_width : bool
            Width of the plate to used in the calculation of stiffener with plate, in meter
        reduced_tw : float, optional
            Reduced web thickness for the stiffener. If not provided, the original web thickness is used.

        Returns:
        --------
        float
            Cross-sectional centroid with effective plate.

        Notes:
        ------
        The cross-sectional centroid is computed based on the dimensions and properties of the stiffener and the provided plate thickness and width.
        """

        tf1 = plate_thickness
        b1 = plate_width

        tf2 = self._flange_th
        b2 = self._flange_width
        tw = self._web_th if reduced_tw == None else reduced_tw / 1000
        hw = self._web_height
        Ax = tf1 * b1 + tf2 * b2 + hw * tw
        effana = (tf1 * b1 * tf1 / 2 + hw * tw * (tf1 + hw / 2) + tf2 * b2 * (tf1 + hw + tf2 / 2)) / Ax

        return effana


class Stress:

    def __init__(self, sigma_x1: float, sigma_x2: float, sigma_y1: float, sigma_y2: float, tauxy: float):
        self._sigma_x1: float = sigma_x1
        self._sigma_x2: float = sigma_x2
        self._sigma_y1: float = sigma_y1
        self._sigma_y2: float = sigma_y2
        self._tauxy: float = tauxy


    def get_sigma_y1(self) -> float:
        '''
        Return sigma_y1
        :return:
        '''
        return self._sigma_y1
    
    
    def get_sigma_y2(self) -> float:
        '''
        Return sigma_y2
        :return:
        '''
        return self._sigma_y2
    
    
    def get_sigma_x1(self) -> float:
        '''
        Return sigma_x
        :return:
        '''
        return self._sigma_x1
    
    
    def get_sigma_x2(self) -> float:
        '''
        Return sigma_x
        :return:
        '''
        return self._sigma_x2
    

    def get_tau_xy(self) -> float:
        '''
        Return tau_xy
        :return:
        '''
        return self._tauxy


    def get_report_stresses(self) -> str:
        'Return the stresses to the report'
        return 'sigma_y1: ' + str(round(self._sigma_y1, 1)) + ' sigma_y2: ' + str(round(self._sigma_y2, 1)) + \
               ' sigma_x1: ' + str(round(self._sigma_x1, 1)) +' sigma_x2: ' + str(round(self._sigma_x2, 1)) + \
               ' tauxy: ' + str(round(self._tauxy, 1))


    def set_stresses(self, sigy1: float, sigy2: float, sigx1: float, sigx2: float, tauxy: float) -> None:
        '''
        Setting the global stresses.
        :param sigy1:
        :param sigy2:
        :param sigx:
        :param tauxy:
        :return:
        '''
        self._sigma_y1 = sigy1
        self._sigma_y2  = sigy2
        self._sigma_x1 = sigx1
        self._sigma_x2 = sigx2
        self._tauxy  = tauxy


class StiffenedPanel:
    # internally stiffener/girder end support is an enum. Makes life easier.
    # the user provides "continuous" or "sniped", which gets translated internally.
    def __init__(self, 
                 plate: Plate, 
                 stiffener: Stiffener=None, # type: ignore
                 stiffener_end_support: str=None, # type: ignore
                 girder: Stiffener=None, # type: ignore
                 girder_end_support: str=None, # type: ignore
                 girder_length: float=None, # type: ignore
                 girder_panel_length: float=None): # type: ignore
        
        self._plate: Plate = plate
        self._stiffener: Stiffener = stiffener
        if self._stiffener is not None:
            assert stiffener_end_support is not None, "When a stiffener is defined, also the end support needs to be defined as 'continuous' or 'sniped'"
            
            if stiffener_end_support.strip().lower() == "continuous":
                self._stiffener_end_support: Enum = EndSupport.CONTINUOUS
            elif stiffener_end_support.strip().lower() == "sniped":
                self._stiffener_end_support: Enum = EndSupport.SNIPED
            else:
                raise ValueError(f"Type {stiffener_end_support} is not a valid input. only 'continuous' or 'sniped'.")
            assert girder_length is not None, "When a stiffener is defined, also the girder length needs to be defined"
            self._girder_lg = girder_length

        self._girder: Union[Stiffener, None] = girder
        if self._girder is not None:
            assert self._stiffener is not None, "When a girder is defined, also the stiffener needs to be defined"
            assert girder_end_support is not None, "When a girder is defined, also the end support needs to be defined as 'continuous' or 'sniped'"
            if girder_end_support.strip().lower() == "continuous":
                self._girder_end_support: Enum = EndSupport.CONTINUOUS
            elif girder_end_support.strip().lower() == "sniped":
                self._girder_end_support: Enum = EndSupport.SNIPED
            else:
                raise ValueError(f"Type {girder_end_support} is not a valid input. only 'continuous' or 'sniped'.")
            
            assert girder_length is not None, "When a girder is defined, also the girder length needs to be defined"
            self._girder_lg: float = girder_length
            assert girder_panel_length is not None, "When a girder is defined, also the panel length needs to be defined"
            self._girder_Lp: float = girder_panel_length


    @property
    def stiffener_end_support(self):
        if self._stiffener_end_support == EndSupport.CONTINUOUS:
            return "continuous"
        elif self._stiffener_end_support == EndSupport.SNIPED:
            return "sniped"
    @stiffener_end_support.setter
    def stiffener_end_support(self, val: str):
        if val.strip().lower() == "continuous":
            self._stiffener_end_support: Enum = EndSupport.CONTINUOUS
        elif val.strip().lower() == "sniped":
            self._stiffener_end_support: Enum = EndSupport.SNIPED
        else:
            raise ValueError(f"Type {val} is not a valid input. only 'continuous' or 'sniped'.")

    @property
    def girder_end_support(self):
        if self._girder_end_support == EndSupport.CONTINUOUS:
            return "continuous"
        elif self._girder_end_support == EndSupport.SNIPED:
            return "sniped"
    @girder_end_support.setter
    def girder_end_support(self, val: str):
        if val.strip().lower() == "continuous":
            self._girder_end_support: Enum = EndSupport.CONTINUOUS
        elif val.strip().lower() == "sniped":
            self._girder_end_support: Enum = EndSupport.SNIPED
        else:
            raise ValueError(f"Type {val} is not a valid input. only 'continuous' or 'sniped'.")


    def ToShortString(self) -> str:
        end_supp: str = self.stiffener_end_support[0:4] if self.stiffener_end_support != None else "None"
        return self._plate._material.ToShortString() + self._plate.ToShortString() + self._stiffener._material.ToShortString() + self._stiffener.ToShortString() + end_supp


    def get_one_line_string(self) -> str:
        ''' Returning a one line string. '''
        return 'pl_' + str(round(self._plate._spacing * 1000, 1)) + 'x' + str(round(self._plate._thickness * 1000, 1)) + \
               ' stf_' + self._stiffener.stiffener_type + \
               str(round(self._stiffener._web_height * 1000, 1)) + 'x' + str(round(self._stiffener._web_th * 1000, 1)) + '+' + \
               str(round(self._stiffener._flange_width * 1000, 1)) + 'x' + str(round(self._stiffener._flange_th * 1000, 1))


    def get_lg(self) -> float:
        '''
        Return the girder length
        :return:
        '''
        return self._girder_lg


    def get_plasic_section_modulus(self) -> float:
        """
        Calculate and return the plastic section modulus of the structure.

        Returns:
        --------
        float
            Plastic section modulus.

        Notes:
        ------
        The plastic section modulus is computed based on the dimensions and properties of the plate and stiffener elements in the structure.
        """
        tf1 = self._plate._thickness
        tf2 = self._stiffener._flange_th
        b1 = self._stiffener._spacing
        b2 = self._stiffener._flange_width
        h = self._stiffener._flange_th + self._stiffener._web_height + self._plate._thickness
        tw = self._stiffener._web_th

        Ax = tf1 * b1 + tf2 * b2 + (h - tf1 - tf2) * tw

        ezpl = (Ax / 2 - b1 * tf1) / tw + tf1

        az1 = h - ezpl - tf1
        az2 = ezpl - tf2

        Wy1 = b1 * tf1 * (az1 + tf1 / 2) + (tw / 2) * math.pow(az1, 2)
        Wy2 = b2 * tf2 * (az2 + tf2 / 2) + (tw / 2) * math.pow(az2, 2)

        return Wy1 + Wy2


    def get_shear_center(self) -> float:
        """
        Calculate and return the shear center of the structure.

        Returns:
        --------
        float
            Shear center location along the z-axis.

        Notes:
        ------
        The shear center is determined based on the dimensions and properties of the plate and stiffener elements in the structure.
        """
        tf1 = self._plate._thickness
        tf2 = self._stiffener._flange_th
        b1 = self._stiffener._spacing
        b2 = self._stiffener._flange_width
        h = self._stiffener._flange_th + self._stiffener._web_height + self._plate._thickness
        tw = self._stiffener._web_th
        hw = self._stiffener._web_height
        Ax = tf1 * b1 + tf2 * b2 + (h - tf1 - tf2) * tw
        # distance to center of gravity in z-direction
        ez = (b2 * tf2 * tf2 / 2 + tw * hw * (tf2 + hw / 2) + tf1 * b1 * (tf2 + hw + tf1 / 2)) / Ax

        # Shear center:
        # moment of inertia, z-axis
        Iz1 = tf1 * math.pow(b1, 3)
        Iz2 = tf2 * math.pow(b2, 3)
        ht = h - tf1 / 2 - tf2 / 2
        return (Iz1 * ht) / (Iz1 + Iz2) + tf2 / 2 - ez


    def get_shear_area(self) -> float:
        """
        Calculate and return the shear area in square meters.

        Returns:
        --------
        float
            Shear area in square meters.

        Notes:
        ------
        The shear area is computed based on the dimensions and properties of the plate and stiffener elements in the structure.
        """
        return ((self._stiffener._flange_th * self._stiffener._web_th) + \
                (self._stiffener._web_th * self._plate._thickness) + \
                (self._stiffener._web_height * self._stiffener._web_th))


    def get_cross_section_area(self, efficient_se=None, include_plate=True) -> float:
        """
        Calculate and return the cross-sectional area.

        Parameters:
        -----------
        efficient_se : float, optional
            Efficient spacing for the plate. If not provided, plate spacing is used
        include_plate : bool, optional
            If True, includes the plate contribution in the cross-sectional area. Default is True.

        Returns:
        --------
        float
            Cross-sectional area.

        Notes:
        ------
        The cross-sectional area is computed based on the dimensions and properties of the plate and stiffener elements in the structure.
        """
        tf1 = self._plate._thickness if include_plate else 0
        tf2 = self._stiffener._flange_th
        if include_plate:
            b1 = self._plate._spacing if efficient_se == None else efficient_se
        else:
            b1 = 0
        
        b2 = self._stiffener._flange_width
        h = self._stiffener._web_height
        tw = self._stiffener._web_th
        #print('Plate: thk', tf1, 's', b1, 'Flange: thk', tf2, 'width', b2, 'Web: thk', tw, 'h', h)
        return tf1 * b1 + tf2 * b2 + h * tw


    def get_weight(self, panel_width: float=0, density: Union[float, None]=None):
        """
        Calclate the mass of the panel.

        Parameters:
        -----------
        panel_width : float, optional if girder present
            Required for panel, since only the spacing is in the definition of a stiffened_panel
        density : float, optional
            Density in kg/m3 to be used in the calculations. Individual material properties (plate, stiffener, girder) are used if not provided.

        Returns:
        --------
        float
            Mass of the stiffened panel in kg

        Notes:
        ------
        If no density is provided, and also no desity has been provided in the definition of plate/stiffener/girder, then 7850kg/m3 for steel is assumed.
        """
        plate_density: float = density if density is not None else self._plate._material._density
        stiffener_density: float = density if density is not None else self._plate._material._density
        girder_density: float = density if density is not None else self._plate._material._density

        if self._girder is None:
            assert panel_width >= 2 * self._plate._spacing
            number_of_stiffeners: float = panel_width / self._plate._spacing
            return plate_density * self._plate._span  * self._plate._thickness * panel_width + \
                    number_of_stiffeners * stiffener_density * (self._stiffener._web_height * self._stiffener._web_th + self._stiffener._flange_width * self._stiffener._flange_th)
        else:
            number_of_stiffeners: float = self._girder_lg / self._plate._spacing
            number_of_girders: float = self._girder_Lp / self._plate._span
            return plate_density * self._plate._thickness * self._girder_lg * self._girder_Lp + \
                    number_of_stiffeners * stiffener_density * self._girder_Lp * (self._stiffener._web_height * self._stiffener._web_th + self._stiffener._flange_width * self._stiffener._flange_th) + \
                    number_of_girders * girder_density * self._girder_Lp * (self._girder._web_height * self._girder._web_th + self._girder._flange_width * self._girder._flange_th)


class Stiffened_panel_calc_props:
    # looks like these are parameters for both scantlings and buckling.
    # Maybe can split up in props for scantling calculations and props for buckling calculations
    def __init__(self, zstar_optimization: bool = True, 
                        plate_kpp: float = 1,
                        stf_kps: float =1 ,
                        km1: float = 12,
                        km2: float = 24,
                        km3: float = 12,
                        structure_type: str = 'BOTTOM',
                        structure_types: str = 'structure_types',
                        lat_load_factor: float=1,
                        stress_load_factor: float=1,
                        buckling_length_factor_stf: Union[float, None]=None,
                        buckling_length_factor_girder: Union[float, None]=None) -> None:
        
        self._zstar_optimization: bool = zstar_optimization
        self._plate_kpp: float = plate_kpp
        self._stf_kps: float = stf_kps
        self._km1: float = km1
        self._km2: float = km2
        self._km3: float = km3
        self._structure_type: str = structure_type
        self._structure_types: str = structure_types
        self._lat_load_factor: float = lat_load_factor
        self._stress_load_factor: float = stress_load_factor
        self._buckling_length_factor_stf: Union[float, None] = buckling_length_factor_stf
        self._buckling_length_factor_girder: Union[float, None] = buckling_length_factor_girder
        # self._dynamic_variable_orientation: float
        # if self.structure_type in self.structure_types['vertical']:
        #     self._dynamic_variable_orientation = 'z - vertical'
        # elif self.structure_type in self.structure_types['horizontal']:
        #     self._dynamic_variable_orientation = 'x - horizontal'


    def get_structure_types(self):
        return self._structure_types


    def get_structure_type(self):
        return self._structure_type


    def get_z_opt(self):
        return self._zstar_optimization


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


class Puls:

    def __init__(self, puls_method: int=1, 
                       puls_boundary: str='Int',
                       puls_stf_end: str='C',
                       puls_sp_or_up: str='SP',
                       puls_up_boundary: str='SSSS') -> None:
        
        self._puls_method: int = puls_method
        self._puls_boundary: str = puls_boundary
        self._puls_stf_end: str = puls_stf_end
        self._puls_sp_or_up: str = puls_sp_or_up
        self._puls_up_boundary: str = puls_up_boundary


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


class DerivedStressValues():
    # used for returning values istead of a tuple
    def __init__(self):
        self._sxsd: float = 0
        self._sysd: float = 0
        self._sy1sd: float = 0
        self._syR: float = 0
        self._sjsd: float = 0
        self._max_vonMises_x: float = 0
        self._stress_ratio_long: float = 0
        self._stress_ratio_trans: float = 0


class BucklingInput():
    # The material factor is part of the material definition. But could also be part of the calculation_properties or even here
    def __init__(self, 
                 panel: StiffenedPanel, 
                 pressure: float, 
                 pressure_side: str='both sides', 
                 stress: Stress=Stress(0, 0, 0, 0, 0), 
                 tension_field_action: str="not allowed", 
                 stiffened_plate_effective_aginst_sigy: bool=True,
                 min_lat_press_adj_span: float=None, # type: ignore
                 calc_props: Stiffened_panel_calc_props=Stiffened_panel_calc_props(), 
                 puls_input: Puls=Puls()):

        self._panel: StiffenedPanel = panel
        self._pressure: float = pressure
        self._pressure_side: str = pressure_side
        self._stress: Stress = stress
        self._tension_field_action: str = tension_field_action # default "not allowed"
        if stiffened_plate_effective_aginst_sigy == True:
            self._stiffened_plate_effective_aginst_sigy: GirderOpt = GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y
        elif stiffened_plate_effective_aginst_sigy == False:
            self._stiffened_plate_effective_aginst_sigy: GirderOpt = GirderOpt.ALL_SIMGA_Y_TO_GIRDER
        else:
            raise ValueError(f"{stiffened_plate_effective_aginst_sigy} is not a valid input for stiffened_plate_effective_aginst_sigy. Only 'True' or 'False'.")

        self._min_lat_press_adj_span: float = min_lat_press_adj_span # type: ignore
        self._stiffened_panel_calc_props: Stiffened_panel_calc_props = calc_props
        self._puls: Puls = puls_input
        
    @property
    def stiffened_plate_effective_aginst_sigy(self) -> bool:
        if self._stiffened_plate_effective_aginst_sigy == GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y:
            return True
        else:
            return False
    @stiffened_plate_effective_aginst_sigy.setter
    def stiffened_plate_effective_aginst_sigy(self, val: bool):
        if val == True:
            self._stiffened_plate_effective_aginst_sigy = GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y
        elif val == False:
            self._stiffened_plate_effective_aginst_sigy = GirderOpt.ALL_SIMGA_Y_TO_GIRDER
        else:
            raise ValueError(f"Type {val} is not a valid input. only 'continuous' or 'sniped'.")


    def __str__(self):
        '''
        Returning all properties.
        '''
        return \
            str(
            '\n Plate field span:              ' + str(round(self._panel._plate._span * 1000)) + ' mm' +
            '\n Stiffener spacing:             ' + str(self._panel._plate._spacing * 1000)+' mm'+
            '\n Plate thickness:               ' + str(self._panel._plate._thickness * 1000)+' mm'+
            '\n Stiffener web height:          ' + str(self._panel._stiffener._web_height * 1000)+' mm'+
            '\n Stiffener web thickness:       ' + str(self._panel._stiffener._web_th * 1000)+' mm'+
            '\n Stiffener flange width:        ' + str(self._panel._stiffener._flange_width * 1000)+' mm'+
            '\n Stiffener flange thickness:    ' + str(self._panel._stiffener._flange_th * 1000)+' mm'+
            '\n Plate material yield:          ' + str(self._panel._plate._material._strength / 1e6)+' MPa'+
            '\n Stiffener material yield:       ' + str(self._panel._stiffener._material._strength / 1e6)+' MPa'+
            '\n Structure/stiffener type:      ' + str(self._stiffened_panel_calc_props._structure_type)+'/'+(self._panel._stiffener.stiffener_type)+
            # '\n Dynamic load varible_          ' + str(self._dynamic_variable_orientation)+
            '\n Plate fixation paramter,kpp:   ' + str(self._stiffened_panel_calc_props._plate_kpp) + ' ' +
            '\n Stf. fixation paramter,kps:    ' + str(self._stiffened_panel_calc_props._stf_kps) + ' ' +
            '\n Global stress, sig_y1/sig_y2:  ' + str(round(self._stress._sigma_y1,3))+'/'+str(round(self._stress._sigma_y2,3))+ ' MPa' +
            '\n Global stress, sig_x1/sig_x2:   ' + str(round(self._stress._sigma_x1,3))+'/'+str(round(self._stress._sigma_x2,3))+ ' MPa' +
            '\n Global shear, tau_xy:          ' + str(round(self._stress._tauxy,3)) + ' MPa' +
            '\n km1,km2,km3:                   ' + str(self._stiffened_panel_calc_props._km1)+'/'+str(self._stiffened_panel_calc_props._km2)+'/'+str(self._stiffened_panel_calc_props._km3)+
            '\n Pressure side (p-plate/s-stf): ' + str(self._pressure_side) + ' ')


    def get_extended_string(self):
        ''' Some more information returned. '''
        return 'span: ' + str(round(self._panel._plate._span, 4)) + ' structure type: ' + self._stiffened_panel_calc_props._structure_type + ' stf. type: ' + \
               self._panel._stiffener.stiffener_type + ' pressure side: ' + self._pressure_side


    def get_plate_mat_factor(self):
        return self._panel._plate._material._mat_factor


    def get_stiffener_mat_factor(self):
        return self._panel._stiffener._material._mat_factor


    def get_girder_mat_factor(self):
        if self._panel._girder is not None:
            return self._panel._girder._material._mat_factor
        else:
            raise ValueError("The girder is not defined.")


    def get_side(self):
        '''
        Return the checked pressure side.
        :return: 
        '''
        return self._pressure_side


    def get_puls_input(self, run_type: str='SP'):
        """
        Modulus of elasticity and poison are the minimum of plat or stiffener
        """
        if self._panel._stiffener._stiffener_type == 'FB':
            stf_type = 'F'
        else:
            stf_type = self._panel._stiffener._stiffener_type
        map_boundary = {'Continuous': 'C', 'Sniped': 'S'}
        sig_x1 = self._stress._sigma_x1
        sig_x2 = self._stress._sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd = max(sig_x1, sig_x2)
        
        elasticity: float = min(self._panel._plate._material._young, self._panel._stiffener._material._young) / 1e6
        poison: float = min(self._panel._plate._material._poisson, self._panel._stiffener._material._poisson)
        
        if self._puls._puls_sp_or_up == 'SP':
            return_dict = {'Identification': None, 'Length of panel': self._panel._plate._span * 1000, 'Stiffener spacing': self._panel._plate._spacing * 1000,
                            'Plate thickness': self._panel._plate._thickness * 1000,
                          'Number of primary stiffeners': 10,
                           'Stiffener type (L,T,F)': stf_type,
                            'Stiffener boundary': map_boundary[self._puls._puls_stf_end]
                            if map_boundary[self._puls._puls_stf_end] in ['C', 'S']
                            else 'C' if self._puls._puls_stf_end == 'Continuous' else 'S',
                          'Stiff. Height': self._panel._stiffener._web_height * 1000, 'Web thick.': self._panel._stiffener._web_th*1000,
                           'Flange width': self._panel._stiffener._flange_width * 1000,
                            'Flange thick.': self._panel._stiffener._flange_th * 1000, 'Tilt angle': 0,
                          'Number of sec. stiffeners': 0, 
                         'Modulus of elasticity': elasticity, 
                         "Poisson's ratio": poison,
                          'Yield stress plate': self._panel._plate._material._strength / 1e6, 'Yield stress stiffener': self._panel._stiffener._material._strength / 1e6,
                            'Axial stress': 0 if self._puls._puls_boundary == 'GT' else sigxd,
                           'Trans. stress 1': 0 if self._puls._puls_boundary == 'GL' else self._stress._sigma_y1,
                          'Trans. stress 2': 0 if self._puls._puls_boundary == 'GL' else self._stress._sigma_y2,
                           'Shear stress': self._stress._tauxy,
                            'Pressure (fixed)': None, 'In-plane support': self._puls._puls_boundary,
                           'sp or up': self._puls._puls_sp_or_up}
        else:
            boundary = self._puls._puls_up_boundary
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

            return_dict = {'Identification': None, 'Length of plate': self._panel._plate._span * 1000, 'Width of c': self._panel._plate._spacing * 1000,
                           'Plate thickness': self._panel._plate._thickness * 1000,
                         'Modulus of elasticity': elasticity, 
                         "Poisson's ratio": poison,
                          'Yield stress plate': self._panel._plate._material._strength / 1e6,
                         'Axial stress 1': 0 if self._puls._puls_boundary == 'GT' else sigxd,
                           'Axial stress 2': 0 if self._puls._puls_boundary == 'GT' else sigxd,
                           'Trans. stress 1': 0 if self._puls._puls_boundary == 'GL' else self._stress._sigma_y1,
                         'Trans. stress 2': 0 if self._puls._puls_boundary == 'GL' else self._stress._sigma_y2,
                           'Shear stress': self._stress._tauxy, 'Pressure (fixed)': None, 'In-plane support': self._puls._puls_boundary,
                         'Rot left': blist[0], 'Rot right': blist[1], 'Rot upper': blist[2], 'Rot lower': blist[3],
                           'sp or up': self._puls._puls_sp_or_up}
        return return_dict


    def get_buckling_ml_input(self, design_lat_press: float=0, sp_or_up: str='SP', alone=True, csr=False):
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
        sig_x1 = self._stress._sigma_x1
        sig_x2 = self._stress._sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd = max(sig_x1, sig_x2)
        
        strength: float = min(self._panel._plate._material._strength, self._panel._stiffener._material._strength) / 1e6
        
        if self._puls._puls_sp_or_up == 'SP':

            if csr == False:

                this_field =  [self._panel._plate._span * 1000, self._panel._plate._spacing * 1000, self._panel._plate._thickness * 1000, self._panel._stiffener._web_height * 1000,
                               self._panel._stiffener._web_th * 1000, self._panel._stiffener._flange_width * 1000, self._panel._stiffener._flange_th * 1000, strength,
                               strength, sigxd, self._stress._sigma_y1, self._stress._sigma_y2, self._stress._tauxy,
                               design_lat_press/1000, stf_type[self._panel._stiffener._stiffener_type],
                               stf_end[map_boundary[self._puls._puls_stf_end]]]
            else:
                this_field =  [self._panel._plate._span * 1000, self._panel._plate._spacing * 1000, self._panel._plate._thickness * 1000, self._panel._stiffener._web_height * 1000,
                               self._panel._stiffener._web_th * 1000, self._panel._stiffener._flange_width * 1000, self._panel._stiffener._flange_th * 1000, strength,
                               strength,  sigxd, self._stress._sigma_y1, self._stress._sigma_y2, self._stress._tauxy,
                               design_lat_press/1000, stf_type[self._panel._stiffener._stiffener_type],
                               stf_end[map_boundary[self._puls._puls_stf_end]],
                               field_type[self._puls._puls_boundary]]
        else:
            ss_cl_list = list()
            for letter_i in self._puls._puls_up_boundary:
                if letter_i == 'S':
                    ss_cl_list.append(up_boundary['SS'])
                else:
                    ss_cl_list.append(up_boundary['CL'])
            b1, b2, b3, b4 = ss_cl_list
            if csr == False:
                this_field =  [self._panel._plate._span * 1000, self._panel._plate._spacing * 1000, self._panel._plate._thickness * 1000, strength,
                               sigxd, self._stress._sigma_y1, self._stress._sigma_y2, self._stress._tauxy, design_lat_press/1000,
                               b1, b2, b3, b4]
            else:
                this_field =  [self._panel._plate._span * 1000, self._panel._plate._spacing * 1000, self._panel._plate._thickness * 1000, strength,
                               sigxd, self._stress._sigma_y1, self._stress._sigma_y2, self._stress._tauxy, design_lat_press/1000,
                               field_type[self._puls._puls_boundary], b1, b2, b3, b4]
        if alone:
            return [this_field,]
        else:
            return this_field


    def calculate_derived_stress_values(self) -> DerivedStressValues:
        # calculated values in MPa
        derived_stress_values: DerivedStressValues = DerivedStressValues()

        E = self._panel._plate._material._young / 1e6
        fy = self._panel._plate._material._strength / 1e6
        # gammaM = self._panel._plate._material._mat_factor
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        tsd = self._stress._tauxy * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        psd = self._pressure * self._stiffened_panel_calc_props._lat_load_factor

        sig_x1 = self._stress._sigma_x1 * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        sig_x2 = self._stress._sigma_x2 * self._stiffened_panel_calc_props._stress_load_factor / 1e6

        sig_y1 = self._stress._sigma_y1 * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        sig_y2 = self._stress._sigma_y2 * self._stiffened_panel_calc_props._stress_load_factor / 1e6

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
        derived_stress_values._stress_ratio_long = stress_ratio_long
        derived_stress_values._stress_ratio_trans = stress_ratio_trans
        
        max_vonMises_x = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        derived_stress_values._max_vonMises_x = max_vonMises_x

        derived_stress_values._sxsd = sxsd
        derived_stress_values._sy1sd = sy1sd

        l1 = min(length / 4, spacing / 2)
        if length == 0:
            sig_trans_l1 = Use_Smax_y
        else:
            sig_trans_l1 = Use_Smax_y * (stress_ratio_trans + (1 - stress_ratio_trans) * (length - l1) / length)


        sysd = 0.75 * Use_Smax_y if abs(0.75 * Use_Smax_y) > abs(Use_Smax_y) else sig_trans_l1
        derived_stress_values._sysd = sysd

        l1 = min(length / 4, spacing / 2)
        if length == 0:
            sig_trans_l1 = Use_Smax_y
        else:
            sig_trans_l1 = Use_Smax_y * (stress_ratio_trans + (1 - stress_ratio_trans) * (length - l1) / length)

        #5  Lateral loaded plates
        sjsd =math.sqrt(math.pow(max_vonMises_x, 2) + math.pow(sysd, 2) - max_vonMises_x * sysd + 3 * math.pow(tsd, 2))
        derived_stress_values._sjsd = sjsd

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
        derived_stress_values._syR = syR

        #logger.debug("sxsd: %s sysd: %s sy1sd: %s sjsd: %s max_vonMises_x: %s syR: %s shear_ratio_long: %s shear_ratio_trans: %s",sxsd, sysd, sy1sd, sjsd, max_vonMises_x, syR, shear_ratio_long, shear_ratio_trans)

        return derived_stress_values


    def effective_plate_width(self) -> float:
        E = self._panel._plate._material._young / 1e6
        fy = self._panel._plate._material._strength / 1e6
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        
        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        
        # 7.3 Effective plate width
        syR = derived_stress_values._syR
        sysd = derived_stress_values._sysd
        sxsd = derived_stress_values._sxsd

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
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        # TODO: update dict to object
        fy = member._material._strength / 1e6
        gammaM = member._material._mat_factor
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        psd = self._pressure * self._stiffened_panel_calc_props._lat_load_factor

        #Pnt.7:  Buckling of stiffened plates
        Vsd = psd * spacing * length / 2
        Anet = (member.hw + member.tf) * member.tw # only vertical takes shear (eg. not the flange)
        Vrd = Anet * fy / (gammaM * math.sqrt(3))
        Vsd_div_Vrd = Vsd / Vrd

        As = member.tw * member.hw + member.b * member.tf
        se = self.effective_plate_width()
        
        tw_red =max(0, member.tw * (1 - Vsd_div_Vrd))
        
        Atot_red  = As + se * thickness - member.hw * (member.tw - tw_red )
        gammaM = self._panel._plate._material._mat_factor
        It_red  = member.get_torsional_moment_venant(reduced_tw=tw_red)
        Ipo_red  = member.get_polar_moment(reduced_tw=tw_red )

        Iy_red = member.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000, reduced_tw=tw_red) * 1000**4
        zp_red  = member.get_cross_section_centroid_with_effective_plate(plate_thickness=thickness/1000, plate_width=se/1000, reduced_tw=tw_red ) \
                    * 1000 - thickness / 2  # ch7.5.1 page 19
        zt_red  = (member.hw + member.tf) - zp_red + thickness / 2  # ch 7.5.1 page 19
        Wes_red  = 0.0001 if zt_red == 0 else Iy_red / zt_red
        Wep_red  = 0.0001 if zp_red == 0 else Iy_red / zp_red
        return {'tw':tw_red , 'Atot': Atot_red , 'It': It_red , 'Ipo': Ipo_red , 'zp': zp_red ,
                'zt': zt_red , 'Wes': Wes_red , 'Wep': Wep_red, 'Iy': Iy_red}


    def fET(self, lT, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        #7.5.2 Lateral torsional buckling
        E = member._material._young / 1e6
        v = member._material._poisson
        G = E / (2 * (1 + v))
        fy = member._material._strength / 1e6
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        taud_Sd = self._stress._tauxy * self._stiffened_panel_calc_props._stress_load_factor / 1e6

        #7.5  Characteristic buckling strength of stiffeners
        fEpx = 0 if spacing == 0 else 3.62 * E * math.pow(thickness / spacing, 2) # eq 7.42, checked, ok
        fEpy = 0 if spacing == 0 else 0.9 * E * math.pow(thickness / spacing, 2) # eq 7.43, checked, ok
        fEpt = 0 if spacing == 0 else 5.0 * E * math.pow(thickness / spacing, 2) # eq 7.44, checked, ok
        c = 0 if length == 0 else 2 - (spacing / length) # eq 7.41, checked, ok

        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        sysd = derived_stress_values._sysd
        sxsd = derived_stress_values._sxsd
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

        hs = member.hw / 2 if member.stiffener_type == 'FB' else \
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
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        fy = member._material._strength / 1e6
        fET: float = self.fET(lT, stiffener_or_girder)
        lambda_T = 0 if fET == 0 else math.sqrt(fy / fET)
        mu = 0.35 * (lambda_T - 0.6)
        fT_div_fy = (1 + mu + math.pow(lambda_T, 2) - \
                     math.sqrt(math.pow(1 + mu + math.pow(lambda_T, 2), 2) - 4 * math.pow(lambda_T, 2))) / \
                        (2 * math.pow(lambda_T, 2))
        fT = fy * fT_div_fy if lambda_T > 0.6 else fy

        # logger.debug("fT: %s", fT)
        return fT


    def fr(self, lT, side: str, stiffener_or_girder: str=None) -> float: # type: ignore
        fy = self._panel._plate._material._strength / 1e6

        if side.strip().lower() == "plate":
            return fy
        if side.strip().lower() == "stiffener":
            assert stiffener_or_girder is not None, "stiffener_or_girder needs to be provided for a 'stiffener side' check"
            fET: float = self.fET(lT, stiffener_or_girder)
            lambda_T = math.sqrt(fy / fET)
            fT: float = self.fT(lT, stiffener_or_girder)
            fr = fT if lambda_T > 0.6 else fy
            return fr
        else:
            raise ValueError(f"The value {side} for 'side' is invalid in fr(lT, side)")

        
    def VRd(self, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        fy = self._panel._plate._material._strength / 1e6
        gammaM = self._panel._plate._material._mat_factor
        # should the following not be either 1. only the web area, or 2.n the full stiffener area?
        Anet = (member.hw + member.tf) * member.tw# + self._Stiffener.b*self._Stiffener.tf
        VRd = Anet * fy / (gammaM * math.sqrt(3))
        
        return VRd


    def lk(self, VSd: float, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        fy = self._panel._plate._material._strength / 1e6
        gammaM = self._panel._plate._material._mat_factor
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        psd = self._pressure * self._stiffened_panel_calc_props._lat_load_factor
        psd_min_adj = psd if self._min_lat_press_adj_span is None else\
            self._min_lat_press_adj_span*self._stiffened_panel_calc_props._lat_load_factor

        As = member.As
        se = self.effective_plate_width()
        zp = member.get_cross_section_centroid_with_effective_plate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
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

        if self._stiffened_panel_calc_props._buckling_length_factor_stf is None:
            if stiffener_or_girder.strip().lower() == "stiffener":
                member_end_support = self._panel._stiffener_end_support
            else:
                member_end_support = self._panel._girder_end_support
            if member_end_support == EndSupport.CONTINUOUS:
                lk = length * (1 - 0.5 * abs(psd_min_adj / pf))

            else:
                lk = length
        else:
            lk = self._stiffened_panel_calc_props._buckling_length_factor_stf * length
        
        # logger.debug("lk: %s", lk)
        return lk


    def fk_stiffener_side(self, lT, VSd: float, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")
        
        E = member._material._young / 1e6
        thickness = self._panel._plate.th # mm
        As = member.As
        se = self.effective_plate_width()
        zp = member.get_cross_section_centroid_with_effective_plate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
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


    def fk_plate(self, stiffener_or_girder: str) -> float:
        if stiffener_or_girder.strip().lower() == "stiffener":
            member: Stiffener = self._panel._stiffener
        elif stiffener_or_girder.strip().lower() == "girder":
            member: Stiffener = self._panel._girder # type: ignore
        else:
            raise ValueError(f"stiffener_or_girder is {stiffener_or_girder} but should be either 'stiffener' or 'girder'")

        E = member._material._young / 1e6
        thickness = self._panel._plate.th # mm
        length = self._panel._plate.l # mm
        As = member.As
        se = self.effective_plate_width()
        zp = member.get_cross_section_centroid_with_effective_plate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
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


class CalcScantlings(BucklingInput):
    '''
    This Class does the calculations for the plate fields. 
    Input is a BucklingInput object, same as for the structure class.
    The class inherits from BucklingInput class.
    '''
    def __init__(self, buckling_input: BucklingInput, lat_press: bool=True, category: str='secondary'):
        super(CalcScantlings, self).__init__(buckling_input._panel, 
                                             buckling_input._pressure, 
                                             buckling_input._pressure_side, 
                                             buckling_input._stress, 
                                             buckling_input._tension_field_action,
                                             buckling_input.stiffened_plate_effective_aginst_sigy,
                                             buckling_input._min_lat_press_adj_span,
                                             buckling_input._stiffened_panel_calc_props, 
                                             buckling_input._puls)
        # pressure is defined as a property, but doesn't seem to be using in the functions, where a parameter is passed.
        self.lat_press: bool = lat_press
        self.category: str = category
        self._need_recalc: bool = True


    @property
    def need_recalc(self):
        return self._need_recalc


    @need_recalc.setter
    def need_recalc(self, val):
        self._need_recalc = val


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
        buckling_input: BucklingInput = BucklingInput(self._panel, 
                                                        self._pressure, 
                                                        self._pressure_side, 
                                                        self._stress, 
                                                        self._tension_field_action, 
                                                        self.stiffened_plate_effective_aginst_sigy, # note wihout the underscore
                                                        self._min_lat_press_adj_span,
                                                        self._stiffened_panel_calc_props, 
                                                        self._puls)
        dnv_buckling: DNVBuckling = DNVBuckling(buckling_input)
        buc = [round(res, 1) for res in dnv_buckling.stiffened_panel().values()]

        return 'Minimum section modulus:'\
               +str(int(self.get_dnv_min_section_modulus(design_pressure_kpa = lat_press) * 1000 ** 3))\
               +'mm^3 '+' Minium plate thickness: '\
               +str(round(self.get_dnv_min_thickness(design_pressure_kpa = lat_press), 1)) + \
               ' Buckling results: eq7_19: ' + str(buc[0]) + ' eq7_50: ' + str(buc[1]) + ' eq7_51: '\
               +str(buc[2]) + ' eq7_52: ' + str(buc[3]) + ' eq7_53: ' + str(buc[4])


    def calculate_slamming_plate(self, slamming_pressure: float, red_fac: float=1) -> float:
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
        ka2 = min(max(0.4, self._panel._plate._spacing / self._panel._plate._span), 1)

        ka = math.pow(ka1 - 0.25 * ka2, 2)
        sigmaf = self._panel._plate._material._strength / 1e6  # MPa

        psl = red_fac * slamming_pressure / 1000  # kPa
        Cd = 1.5

        return 0.0158 * ka * self._panel._plate._spacing * 1000 * math.sqrt(psl / (Cd * sigmaf))


    def calculate_slamming_stiffener(self, slamming_pressure: float, angle: float=90, red_fac: float=1) -> dict[str, Union[float, None]]:
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

        tk = 0
        psl = slamming_pressure / 1000  # kPa
        Pst = psl * red_fac  # Currently DNV does not use psl/2 for slamming.
        sigmaf = self._panel._stiffener._material._strength / 1e6  # MPa
        hw, twa, tp, tf, bf, s = [(val - tk) * 1000 for val in [self._panel._stiffener._web_height, self._panel._stiffener._web_th, self._panel._plate._thickness,
                                                                self._panel._stiffener._flange_th, self._panel._stiffener._flange_width, self._panel._plate._spacing]]
        ns = 2
        tau_eH = sigmaf / math.sqrt(3)
        h_stf = (self._panel._stiffener._web_height+self._panel._stiffener._flange_th) * 1000
        f_shr = 0.7
        lbdg = self._panel._plate._span
        lshr = self._panel._plate._span - self._panel._plate._spacing / 4000
        dshr = h_stf + tp if 75 <= angle <= 90 else (h_stf + tp) * math.sin(math.radians(angle))
        tw = (f_shr * Pst * s * lshr) / (dshr * tau_eH)

        if self._panel._stiffener._web_th * 1000 < tw:
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
        pl_chk = self.calculate_slamming_plate(slamming_pressure, red_fac=pl_red_fact)
        if self._panel._plate._thickness * 1000 < pl_chk:
            chk1 = pl_chk / self._panel._plate._thickness * 1000
            return False, chk1

        stf_res = self.calculate_slamming_stiffener(slamming_pressure, angle=angle, red_fac=stf_red_fact)
        if stf_res['tw_req'] is not None: # this is always the case though
            if self._panel._stiffener._web_th * 1000 < stf_res['tw_req']:
                chk2 = stf_res['tw_req'] / self._panel._stiffener._web_th * 1000
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
        tk = 0
        angle_rad = math.radians(angle)
        hw, tw, tp, tf, bf = [(val - tk) * 1000 for val in [self._panel._stiffener._web_height, self._panel._stiffener._web_th, self._panel._plate._thickness, self._panel._stiffener._flange_th,
                                                            self._panel._stiffener._flange_width]]
        h_stf = (self._panel._stiffener._web_height+self._panel._stiffener._flange_th)*1000
        de_gr = 0
        tw_gr = self._panel._stiffener._web_th * 1000
        hf_ctr = h_stf-0.5*tf if self._panel._stiffener.stiffener_type not in ['L','L-bulb'] else h_stf - de_gr - 0.5 * tf
        bf_ctr = 0 if self._panel._stiffener.stiffener_type == 'T' else 0.5 * (tf - tw_gr)
        beta = 0.5
        gamma = (1 + math.sqrt(3 + 12 * beta)) / 4

        Af = 0 if self._panel._stiffener.stiffener_type == 'FB' else bf * tf

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
        fy = self._panel._plate._material._strength / 1e6
        fyd = fy / self._panel._plate._material._mat_factor

        sigma_y = self._stress._sigma_y2 + (self._stress._sigma_y1 - self._stress._sigma_y2)\
                                       *(min(0.25 * self._panel._plate._span, 0.5 * self._panel._plate._spacing) / self._panel._plate._span)
        sig_x1 = self._stress._sigma_x1
        sig_x2 = self._stress._sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd =max(sig_x1 , sig_x2)

        sigma_jd = math.sqrt(math.pow(sigxd, 2) + math.pow(sigma_y, 2) -
                             sigxd * sigma_y + 3 * math.pow(self._stress._tauxy, 2))

        sigma_pd2 = fyd - sigma_jd  # design_bending_stress_mpa

        kps = self._stiffened_panel_calc_props._stf_kps  # 1 is clamped, 0.9 is simply supported.
        km_sides = min(self._stiffened_panel_calc_props._km1, self._stiffened_panel_calc_props._km3)  # see table 3 in DNVGL-OS-C101 (page 62)
        km_middle = self._stiffened_panel_calc_props._km2  # see table 3 in DNVGL-OS-C101 (page 62)

        Zs = ((math.pow(self._panel._plate._span, 2) * self._panel._plate._spacing * design_pressure) /
              (min(km_middle, km_sides) * (sigma_pd2) * kps)) * math.pow(10, 6)
        
        if printit:
            print('Sigma y1', self._stress._sigma_y1, 'Sigma y2', self._stress._sigma_y2, 'Sigma x', self._stress._sigma_x1,
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
        self._panel._plate._span
        sigma_y = self._stress._sigma_y2 + (self._stress._sigma_y1 - self._stress._sigma_y2) \
                                       *(min(0.25*self._panel._plate._span, 0.5 * self._panel._plate._spacing) / self._panel._plate._span)

        sig_x1 = self._stress._sigma_x1
        sig_x2 = self._stress._sigma_x2
        if sig_x1 * sig_x2 >= 0:
            sigxd = sig_x1 if abs(sig_x1) > abs(sig_x2) else sig_x2
        else:
            sigxd =max(sig_x1 , sig_x2)

        sigma_jd = math.sqrt(math.pow(sigxd, 2) + math.pow(sigma_y, 2) -
                             sigxd * sigma_y + 3 * math.pow(self._stress._tauxy, 2))

        fy = self._panel._plate._material._strength / 1e6
        fyd = fy / self._panel._plate._material._mat_factor
        sigma_pd1 = min(1.3 * (fyd - sigma_jd), fyd)
        sigma_pd1 = abs(sigma_pd1)

        if self.category == 'secondary':
            t0 = 5
        else:
            t0 = 7

        t_min = (14.3 * t0) / math.sqrt(fyd)

        ka = math.pow(1.1 - 0.25  * self._panel._plate._spacing / self._panel._plate._span, 2)

        if ka > 1:
            ka = 1
        elif ka < 0.72:
            ka = 0.72

        assert sigma_pd1 > 0, 'sigma_pd1 must be negative | current value is: ' + str(sigma_pd1)
        assert self._stiffened_panel_calc_props._plate_kpp is not None, 'Fixation parameters must be set.'
        t_min_bend = (15.8 * ka * self._panel._plate._spacing * math.sqrt(design_pressure)) / \
                     math.sqrt(sigma_pd1 *self._stiffened_panel_calc_props._plate_kpp)

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
        l = self._panel._plate._span
        s = self._panel._plate._spacing
        fy = self._panel._plate._material._strength

        fyd = (fy / self._panel._plate._material._mat_factor) / 1e6 # yield strength
        sig_x1 = self._stress._sigma_x1
        sig_x2 = self._stress._sigma_x2
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

        return self.get_dnv_min_thickness(design_pressure) <= self._panel._plate._thickness * 1000


    def get_plate_efficent_b(self,design_lat_press=0,axial_stress=50,
                                 trans_stress_small=100,trans_stress_large=100):
        '''
        Simple buckling calculations according to DNV-RP-C201
        :return:
        '''
        raise NotImplementedError("Not implemented for scantling. Use the buckling functionality instead")


    def buckling_local_stiffener(self):
        '''
        Local requirements for stiffeners. Chapter 9.11.
        :return:
        '''
        raise NotImplementedError("Not implemented for scantling. Use the buckling functionality instead")


class GirderOpt(Enum):
    STF_PL_EFFECTIVE_AGAINST_SIGMA_Y = 1
    ALL_SIMGA_Y_TO_GIRDER = 2


class EndSupport(Enum):
    CONTINUOUS = 1
    SNIPED = 2


class DNVBuckling(BucklingInput): 
    def __init__(self, buckling_input: BucklingInput, calculation_domain: Union[str, None]=None):
        super(DNVBuckling, self).__init__(buckling_input._panel, 
                                          buckling_input._pressure,
                                          buckling_input._pressure_side, 
                                          buckling_input._stress, 
                                          calc_props=buckling_input._stiffened_panel_calc_props, 
                                          puls_input=buckling_input._puls)
        
        self._calculation_domain:  Union[str, None] = calculation_domain


    def get_method(self) -> Enum:
        if self.stiffened_plate_effective_aginst_sigy == True:
            self._stiffened_plate_effective_aginst_sigy = GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y
        elif self.stiffened_plate_effective_aginst_sigy == False:
            self._stiffened_plate_effective_aginst_sigy = GirderOpt.ALL_SIMGA_Y_TO_GIRDER

        if self._calculation_domain == "Flat plate, stiffened with girder":
            if self._stiffened_plate_effective_aginst_sigy == GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y:
                return GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y
            else:
                return GirderOpt.ALL_SIMGA_Y_TO_GIRDER
        else:
            return GirderOpt.STF_PL_EFFECTIVE_AGAINST_SIGMA_Y


    def plated_structures_buckling(self, optimizing: bool=False) -> dict:
        '''
        Summary
        '''
        return_dummy = {'Plate': {'Plate buckling': 0},
                        'Stiffener': {'Overpressure plate side': 0, 'Overpressure stiffener side': 0,
                                      'Resistance between stiffeners': 0, 'Shear capacity': 0},
                        'Girder': {'Overpressure plate side': 0, 'Overpressure girder side': 0, 'Shear capacity': 0},
                        'Local buckling': 0}

        unstf_pl = self.unstiffened_plate_buckling(optimizing = optimizing)
        up_buckling = max([unstf_pl['UF Pnt. 5  Lateral loaded plates'], unstf_pl['UF sjsd'],
                           max([unstf_pl['UF Longitudinal stress'],  unstf_pl['UF transverse stresses'],
                                unstf_pl['UF Shear stresses'], unstf_pl['UF Combined stresses']])
                           if all([self._panel._girder is None, self._panel._stiffener is None]) else 0])
        if optimizing and up_buckling > 1:
            return_dummy['Plate']['Plate buckling'] = up_buckling
            return return_dummy

        local_buckling = self.local_buckling(optimizing=optimizing)

        stf_pla: dict = {}
        if self._panel._stiffener is not None:
            stf_pla = self.stiffened_panel(optimizing=optimizing)
            if all([optimizing, type(stf_pla) == list]):
                return_dummy['Stiffener'][stf_pla[0]] = stf_pla[1]
                return return_dummy

            stf_buckling_pl_side = stf_pla['UF Plate side'] if self._panel._stiffener_end_support == EndSupport.CONTINUOUS else \
                stf_pla['UF simply supported plate side']
            stf_buckling_stf_side = stf_pla['UF Stiffener side'] if self._panel._stiffener_end_support == EndSupport.CONTINUOUS else \
                stf_pla['UF simply supported stf side']
            stf_plate_resistance = stf_pla['UF Plate resistance']
            stf_shear_capacity = stf_pla['UF Shear force']
        else:
            stf_buckling_pl_side, stf_buckling_pl_side, stf_buckling_stf_side, stf_plate_resistance, \
            stf_shear_capacity = 0, 0, 0, 0, 0

        # no girder if stiffener not present
        if self._panel._girder is not None and self._panel._stiffener is not None:
            girder = self.girder_buckling(optmizing=optimizing)
            if all([optimizing, type(girder) == list]):
                return_dummy['Girder'][stf_pla[0]] = stf_pla[1]
                return return_dummy

            girder_buckling_pl_side = girder['UF Cont. plate side'] if self._panel._girder_end_support == EndSupport.CONTINUOUS else \
                stf_pla['UF Simplified plate side']
            girder_buckling_girder_side = girder['UF Cont. girder side'] if self._panel._girder_end_support == EndSupport.CONTINUOUS \
                else \
                stf_pla['UF Simplified girder side']
            girder_shear_capacity = girder['UF shear force']
        else:
            girder_buckling_pl_side, girder_buckling_girder_side, girder_shear_capacity = 0, 0, 0
        
        return {'Plate': {'Plate buckling': up_buckling},
                'Stiffener': {'Overpressure plate side': stf_buckling_pl_side,
                                                    'Overpressure stiffener side': stf_buckling_stf_side, 
                                                    'Resistance between stiffeners': stf_plate_resistance,
                                                    'Shear capacity': stf_shear_capacity},
                'Girder': {'Overpressure plate side': girder_buckling_pl_side,
                           'Overpressure girder side': girder_buckling_girder_side,
                           'Shear capacity': girder_shear_capacity},
                'Local buckling': 0 if optimizing else local_buckling}


    def unstiffened_plate_buckling(self, optimizing: bool=False) -> dict:
        # internal calculations are in mm (millimeter) and MPa (mega pascal)
        unstf_pl_data = dict()

        E = self._panel._plate._material._young / 1e6
        fy = self._panel._plate._material._strength / 1e6
        gammaM = self._panel._plate._material._mat_factor
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        tsd = self._stress._tauxy * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        psd = self._pressure * self._stiffened_panel_calc_props._lat_load_factor

        sig_x1 = self._stress._sigma_x1 * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        sig_x2 = self._stress._sigma_x2 * self._stiffened_panel_calc_props._stress_load_factor / 1e6

        sig_y1 = self._stress._sigma_y1 * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        sig_y2 = self._stress._sigma_y2 * self._stiffened_panel_calc_props._stress_load_factor / 1e6

        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        sxsd: float = derived_stress_values._sxsd
        sysd: float = derived_stress_values._sysd
        sy1sd: float = derived_stress_values._sy1sd
        max_vonMises_x: float = derived_stress_values._max_vonMises_x
        shear_ratio_long: float = derived_stress_values._stress_ratio_long
        sjsd: float = derived_stress_values._sjsd

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
        # What to do with possible difference in material between plate/stiffener/girder
        # now the plate is taken
        logger.debug("---------------------------------------------------------")
        logger.debug("stiffened panel check")
        logger.debug("---------------------------------------------------------")
        E = self._panel._plate._material._young / 1e6
        v = self._panel._plate._material._poisson
        fy = self._panel._plate._material._strength / 1e6
        gammaM = self._panel._plate._material._mat_factor
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        tsd = self._stress._tauxy * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        psd = self._pressure * self._stiffened_panel_calc_props._lat_load_factor
        # sig_x1 = self._stress._sigma_x1 * self._stiffened_panel_calc_props._stress_load_factor
        # sig_x2 = self._stress._sigma_x2 * self._stiffened_panel_calc_props._stress_load_factor
        sig_y1 = self._stress._sigma_y1 * self._stiffened_panel_calc_props._stress_load_factor / 1e6
        sig_y2 = self._stress._sigma_y2 * self._stiffened_panel_calc_props._stress_load_factor / 1e6

        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        sxsd: float = derived_stress_values._sxsd
        sysd: float = derived_stress_values._sysd
        sy1sd: float = derived_stress_values._sy1sd
        stress_ratio_trans = derived_stress_values._stress_ratio_trans

        Lg = self._panel._girder_lg * 1000

        stf_pnl_data = dict()

        sy1sd = 0 if self.get_method() == 2 else sy1sd
        sysd = 0 if self.get_method() == 2 else sysd

        # psd_min_adj = psd if self._min_lat_press_adj_span is None else\
        #     self._min_lat_press_adj_span * self._stiffened_panel_calc_props._lat_load_factor
        

        #Pnt.7:  Buckling of stiffened plates
        # 7.2  Forces in idealised stiffened plate
        se = self.effective_plate_width()
        Iy = Is = self._panel._stiffener.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=se/1000) * 1000**4

        kc = 0 if thickness * spacing == 0 else 2 * (1 + math.sqrt(1 + 10.9 * Is / (math.pow(thickness, 3) * spacing)))
        mc = 13.3 if self._panel._stiffener_end_support == EndSupport.CONTINUOUS else 8.9

        zp = self._panel._stiffener.get_cross_section_centroid_with_effective_plate(plate_thickness=thickness/1000, plate_width=se/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        zt = (self._panel._stiffener.hw + self._panel._stiffener.tf) - zp + thickness / 2

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

        qsd_plate_side = qsd_opposite if self._pressure_side == 'stiffener side' else qsd_press
        qsd_stf_side = qsd_opposite if self._pressure_side == 'plate side' else qsd_press
        
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

        if self._tension_field_action == 'allowed' and tsd > (tau_crl / gammaM):
            ttf = tsd - tau_crg
        else:
            ttf = 0

        As = self._panel._stiffener.tw*self._panel._stiffener.hw + self._panel._stiffener.b * self._panel._stiffener.tf
        NSd = sxsd * (As + spacing * thickness) + ttf * spacing * thickness

        #7.4  Resistance of plate between stiffeners
        ksp = math.sqrt(1 - 3 * math.pow(tsd / fy, 2)) if tsd < (fy / math.sqrt(3)) else 0
        syRd = derived_stress_values._syR if not all([sig_y1 < 0, sig_y2 < 0]) else fy
        syrd_unstf = syRd / gammaM * ksp
        tau_sd_7_4 = fy / (math.sqrt(3) * gammaM)
        uf_stf_panel_res_bet_plate = max([sysd / syrd_unstf if all([syrd_unstf > 0, sysd > 0]) else 0, tsd / tau_sd_7_4])
        stf_pnl_data['UF Plate resistance'] = uf_stf_panel_res_bet_plate
        if optimizing and uf_stf_panel_res_bet_plate > 1:
            # return ['UF Plate resistance', uf_stf_panel_res_bet_plate]
            return stf_pnl_data

        # 7.8 Check for shear force 
        Vsd = psd * spacing * length / 2
        Vsd_div_Vrd = Vsd / self.VRd("stiffener")

        stf_pnl_data['UF Shear force'] = Vsd_div_Vrd
        if optimizing and Vsd_div_Vrd > 1:
            #return ['UF Shear force', Vsd_div_Vrd]
            return stf_pnl_data

        #7.5  Characteristic buckling strength of stiffeners
        # Is in the functions fk_stiffener(), fk_plate(), lk()

        #7.7.3  Resistance parameters for stiffeners
        # properties depend on check for shear force, section 7.8
        reduced_properties_used: bool = False # for debugging message
        if Vsd_div_Vrd < 0.5:
            Wes = 0.0001 if zt == 0 else Iy / zt
            Wep = 0.0001 if zp == 0 else Iy / zp
            Ae = As + se * thickness
        else:
            red_param = self.red_prop("stiffener")
            Wes = red_param['Wes']
            Wep = red_param['Wep']
            Ae = red_param['Atot']
            reduced_properties_used = True

        NRd = 0.0001 if gammaM == 0 else Ae * (fy / gammaM)  # 7.65
        NksRd = Ae * (self.fk_stiffener_side(length if self._panel._stiffener.dist_between_lateral_supp is None else self._panel._stiffener.dist_between_lateral_supp * 1000, Vsd, "stiffener") / gammaM) #eq7.66
        NkpRd = Ae * (self.fk_plate("stiffener") / gammaM)

        logger.debug("self._panel._stiffener.dist_between_lateral_supp: %s", self._panel._stiffener.dist_between_lateral_supp)
        Ms1Rd = Wes * (self.fr(0.4 * length if self._panel._stiffener.dist_between_lateral_supp is None else
                                   self._panel._stiffener.dist_between_lateral_supp * 1000, "stiffener", "stiffener") / gammaM)  # 7.68
        Ms2Rd = Wes * (self.fr(0.8 * length if self._panel._stiffener.dist_between_lateral_supp is None else
                                   self._panel._stiffener.dist_between_lateral_supp * 1000, "stiffener", "stiffener") / gammaM)  # 7.69

        MstRd = Wes * (fy / gammaM) # 7.70 checked ok
        MpRd = Wep * (fy / gammaM) # 7.71 checked ok

        lk = self.lk(Vsd, "stiffener")
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
        logger.debug("Area stiffener: %s", self._panel._stiffener.As)
        logger.debug("zp: %s Zt: %s Iy: %s Wes %s Wep: %s Reduced properties used: %s", zp, zt, Iy, Wes, Wep, reduced_properties_used)

        logger.debug("7.2 Forces in the idealised stiffened plate")
        logger.debug("kc: %s mc: %s Wes: %s stress_ratio_trans %s C0: %s P0: %s", kc, mc, Wes, stress_ratio_trans, Co, Po)
        logger.debug("qsd_plate_side %s qsd_stf_side: %s kl: %s tau_crl: %s kg: %s tau_crg: %s", qsd_plate_side, qsd_stf_side, kl, tau_crl, kg, tau_crg)
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
        u = 0 if all([tsd>(tau_crl/gammaM), self._tension_field_action == 'allowed']) else math.pow(tsd/tau_Rd, 2)
        zstar = zp
        if self._panel._stiffener_end_support == EndSupport.SNIPED:
            #Lateral pressure on plate side:
            #7.7.2 Simple supported stiffener (sniped stiffeners)

            #Lateral pressure on plate side:
            stf_pnl_data['UF Stiffener side'] = 0
            stf_pnl_data['UF Plate side'] = 0
            uf_7_58 = NSd / NksRd - 2 * NSd / NRd + ((qsd_plate_side * math.pow(length, 2) / 8) + NSd * zstar) / (MstRd * (1 - NSd / Ne)) + u
            uf_7_59 = NSd / NkpRd + ((qsd_plate_side * math.pow(length, 2) / 8) + NSd * zstar) / (MpRd * (1 - NSd / Ne)) + u
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
            logger.debug("uf_7_59: %s uf_7_60: %s uf_7_61: %s uf_7_62 %s uf_7_63: %s uf_7_64: %s z*: %s", uf_7_58, uf_7_59, uf_7_60, uf_7_61, uf_7_62, uf_7_63, zstar)
        else:
            stf_pnl_data['UF simply supported stf side'] = 0
            stf_pnl_data['UF simply supported plate side'] = 0
            
            #7.7.1 Continuous stiffeners
            M1Sd_pl = abs(qsd_plate_side) * math.pow(length, 2) / self._stiffened_panel_calc_props._km3
            M2Sd_pl = abs(qsd_plate_side) * math.pow(length, 2) / self._stiffened_panel_calc_props._km2
            M1Sd_stf = abs(qsd_stf_side) * math.pow(length, 2) / self._stiffened_panel_calc_props._km3
            M2Sd_stf = abs(qsd_stf_side) * math.pow(length, 2) / self._stiffened_panel_calc_props._km2

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
            res_iter_pl = minimize_scalar(iteration_min_uf_pl_side, method="Bounded", bounds=(-zt+self._panel._stiffener.tf/2,zp), options={'xatol': tolerance})

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

            res_iter_stf = minimize_scalar(iteration_min_uf_stf_side, method="Bounded", bounds=(-zt+self._panel._stiffener.tf/2,zp), options={'xatol': tolerance})
            if type(res_iter_stf.fun) == list:
                stf_pnl_data['UF Stiffener side'] = res_iter_stf.fun[0]
            else:
                stf_pnl_data['UF Stiffener side'] = res_iter_stf.fun
            
            iteration_min_uf_pl_side(res_iter_pl.x, True)
            iteration_min_uf_stf_side(res_iter_stf.x, True)
        return stf_pnl_data


    def girder_buckling(self, optmizing = False) -> dict:
        '''
        Buckling of girder.
        '''

        girder_data = dict()

        # the next line pure for pylance in vscode
        assert self._panel._girder is not None, "Data cannot be None"

        E = self._panel._girder._material._young / 1e6
        v = self._panel._girder._material._poisson
        fy = self._panel._girder._material._strength / 1e6
        gammaM = self._panel._girder._material._mat_factor
        thickness = self._panel._plate.th # mm
        spacing = self._panel._plate.s # mm
        length = self._panel._plate.l # mm

        tsd = self._stress._tauxy * self._stiffened_panel_calc_props._stress_load_factor
        psd = self._pressure * self._stiffened_panel_calc_props._lat_load_factor

        derived_stress_values: DerivedStressValues = self.calculate_derived_stress_values()
        sxsd: float = derived_stress_values._sxsd
        sysd: float = derived_stress_values._sysd
        sy1sd: float = derived_stress_values._sy1sd

        # psd_min_adj = psd if self._min_lat_press_adj_span is None else\
        #     self._min_lat_press_adj_span * self._stiffened_panel_calc_props._lat_load_factor

        Lg = self._panel._girder_lg * 1000 # internal variables are in meter, this calculation is in mm

        Ltg = Lg if self._panel._girder.dist_between_lateral_supp == None else self._panel._girder.dist_between_lateral_supp
        Lp = 0 if self._panel._girder_Lp is None else self._panel._girder_Lp
        
        #Pnt.8:  Buckling of Girders
        #7.8  Check for shear force
        Vsd = psd * length * Lg / 2
        Anet = self._panel._girder.hw * self._panel._girder.tw + self._panel._girder.tw * self._panel._girder.tf
        Vrd = Anet * fy / (gammaM * math.sqrt(3))

        Vsd_div_Vrd = Vsd / Vrd
        girder_data['UF shear force'] = Vsd_div_Vrd
        if optmizing and Vsd_div_Vrd > 1:
            # return ['UF shear force', Vsd_div_Vrd]
            return girder_data

        #8.2  Girder forces
        As = self._panel._stiffener.As
        Ag = self._panel._girder.As

        #sysd = 0 if self.get_method() == 2 else unstf_pl_data['sysd']
        NySd = sysd * (Ag + length * thickness)

        Is = self._panel._stiffener.get_moment_of_intertia() * 1000**4

        tau_cel = 18 * E / (thickness * math.pow(length, 2)) * math.pow(thickness * Is / spacing, 0.75)
        tau_ceg = 0 if Lp == 0 else tau_cel * math.pow(length, 2) / math.pow(Lp, 2)

        lambda_t1 = 0 if Lp == 0 else math.sqrt(0.6 * fy / tau_ceg)
        lambda_t2 = math.sqrt(0.6 * fy / tau_cel)

        tcrg = 0.6 * fy / math.pow(lambda_t1, 2) if lambda_t1 > 1 else 0.6 * fy
        tcrl = 0.6 * fy / math.pow(lambda_t2, 2) if lambda_t2 > 1 else 0.6 * fy

        tcrg = tcrg if self._panel._stiffener_end_support == EndSupport.CONTINUOUS else 0

        #8.4 Effective width of girders
        #Method 1:
        # calculation of Cxs and Cys according 7.14 and 7.16
        syR = derived_stress_values._syR
        sysd = derived_stress_values._sysd
        sxsd = derived_stress_values._sxsd

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

        lim_sniped_or_cont = 0.3 * Lg if self._panel._girder_end_support == EndSupport.CONTINUOUS else 0.4 * Lg
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

        Iy = self._panel._girder.get_moment_of_intertia(plate_thickness=thickness/1000, plate_width=le/1000) * 1000 ** 4
        zp = self._panel._girder.get_cross_section_centroid_with_effective_plate(plate_thickness=thickness/1000, plate_width=le/1000) * 1000 - thickness / 2  # ch7.5.1 page 19
        zt = (thickness / 2 + self._panel._girder.hw + self._panel._girder.tf) - zp  # ch 7.5.1 page 19

        if Vsd_div_Vrd < 0.5:
            WeG = 0.0001 if zt == 0 else Iy / zt
            Wep = 0.0001 if zp == 0 else Iy / zp
            AeG = Ag + eff_width_other_calc * thickness
        else:
            red_param = self.red_prop("girder")
            WeG = red_param['WeG']
            Wep = red_param['Wep']
            AeG = red_param['Atot']

        # #from: 7.7.3  Resistance parameters for stiffeners
        Wmin = min([WeG, Wep])
        # pf = 0.0001 if length * spacing * gammaM == 0 else 12 * Wmin * fy / (math.pow(length, 2) * spacing * gammaM)

        lk = Lg
        LGk = lk if self._stiffened_panel_calc_props._buckling_length_factor_girder is None else lk * self._stiffened_panel_calc_props._buckling_length_factor_girder

        ie = math.sqrt(Iy / AtotG)
        fE = 0 if LGk == 0 else math.pow(math.pi, 2) * E * math.pow(ie / LGk, 2)

        # 8.2  Girder forces, cont
        lambda_G = 0 if fE == 0 else math.sqrt(fy / fE)
        Q = 0 if lambda_G - 0.2 < 0 else min([1, lambda_G - 0.2])
        C_for_tsd_trg = Q * (7 - 5 * math.pow(spacing / length, 2)) * math.pow((tsd - tcrg) / tcrl, 2)
        C = C_for_tsd_trg if tsd > tcrg else 0
        p0lim = 0.02 * (thickness + As / spacing) / length * (sxsd + C * tsd)
        p0calc = 0 if spacing * self._panel._girder.hw * Lg * E * length == 0 else \
                 0.4 * (thickness + As / spacing) / (self._panel._girder.hw * (1 - spacing / Lg)) * fy / E * math.pow(Lg / length, 2) * (sxsd + C * tsd)
        p0_compression = max([p0lim, p0calc])
        p0_tension = 0 if spacing * Lg * self._panel._girder.hw * E * length == 0 else \
                     0.4 * (thickness + As / spacing) / (self._panel._girder.hw * (length - spacing / Lg)) * gammaM / E * math.pow(Lg / length, 2) * (C * tsd)
        p0 = p0_tension if sxsd < 0 else p0_compression

        qSd_pressure = (psd + p0_tension) * length if sxsd < 0 else (psd + p0_compression) * length
        qsd_oppsite = p0 * length if psd < p0 else 0
        qSd_plate_side = qsd_oppsite if self._pressure_side == 'stiffener side' else qSd_pressure
        qSd_girder_side = qsd_oppsite if self._pressure_side == 'plate side' else qSd_pressure

        #8.5  Torsional buckling of girders
        
        Af = self._panel._girder.tf * self._panel._girder.b
        Aw = self._panel._girder.hw * self._panel._girder.tw

        b = max([self._panel._girder.b, self._panel._girder.tw])
        C = 0.55 if self._panel._girder.stiffener_type in ['T', 'FB'] else 1.1
        LGT0 = b * C * math.sqrt(E * Af / (fy * (Af + Aw / 3))) #TODO can add a automatic check/message if torsional buckling shall be considered
        girder_data['Torsional buckling'] = 'Torsional buckling to be considered' if Ltg > LGT0 else \
            "Torsional buckling need not to be considered"

        # #7.7.3  Resistance parameters for stiffeners

        NRd = 0.0001 if gammaM == 0 else AeG * (fy / gammaM)  # eq7.65, checked ok

        NksRd = AeG * (self.fk_stiffener_side(Ltg, Vsd, "girder") / gammaM) #eq7.66
        NkpRd = AeG * (self.fk_plate('girder') / gammaM)  # checked ok
        # MsRd = WeG * self.fr(Ltg, "stiffener", "girder") / gammaM # 'stiffener side' for a girder
        Ms1Rd = WeG * (self.fr(0.4 * Lg, "stiffener", "girder") / gammaM)  # ok
        Ms2Rd = WeG * (self.fr(0.8 * Lg, "stiffener", "girder") / gammaM)  # eq7.69 checked ok

        MstRd = WeG * (fy / gammaM) #eq7.70 checked ok
        MpRd = Wep * (fy / gammaM) #eq7.71 checked ok

        NE = ((math.pow(math.pi, 2)) * E * AeG) / (math.pow(LGk / ie, 2))# eq7.72 , checked ok

        #7.7  Interaction formulas for axial compression and lateral pressure
        #7.7.2 Simple supported girder (sniped girders)
        if self._panel._girder_end_support == EndSupport.SNIPED: 
            u = 0
            zstar = zp
            girder_data['UF Cont. plate side'] = 0
            girder_data['UF Cont. girder side'] = 0

            # Lateral pressure on plate side:
            uf_7_58 = NySd / NksRd - 2 * NySd / NRd +((qSd_plate_side * math.pow(Lg, 2) / 8) + NySd * zstar) / (MstRd * (1 - NySd / NE)) + u
            uf_7_59 = NySd / NkpRd + ((qSd_plate_side * math.pow(Lg, 2) / 8) + NySd * zstar) / (MpRd * (1 - NySd / NE)) + u

            max_uf_simp_plate = max([0,uf_7_58, uf_7_59])
            girder_data['UF Simplified plate side'] = max_uf_simp_plate

            #Lateral pressure on girder side:
            uf_7_60 = NySd / NksRd + ((qSd_girder_side * math.pow(Lg, 2) / 8) - NySd * zstar) / (Ms2Rd * (1 - NySd / NE)) + u
            uf_7_61 = NySd / NkpRd - 2 * NySd / NRd + ((qSd_girder_side * math.pow(Lg, 2) / 8) - NySd * zstar) / (MpRd * (1 - NySd / NE)) + u

            CHK_qSd_NSd = qSd_girder_side * math.pow(Lg, 2) / 8 < NySd * zstar

            uf_7_62 = NySd / NksRd - 2 * NySd / NRd + (NySd * zstar - (qSd_girder_side * math.pow(Lg, 2) / 8)) / (MstRd * (1 - NySd / NE)) + u
            uf_7_63 = NySd / NkpRd + (NySd * zstar - (qSd_girder_side * math.pow(Lg, 2) / 8)) / (MpRd * (1 - NySd / NE)) + u

            max_uf_simp_stiffener = max([0, uf_7_60, uf_7_61]) if CHK_qSd_NSd else max([0, uf_7_60, uf_7_61, uf_7_62, uf_7_63])
            girder_data['UF Simplified girder side'] = max_uf_simp_stiffener
        else:
            u = 0
            girder_data['UF Simplified girder side'] = 0
            girder_data['UF Simplified plate side'] = 0
            #7.7.1 Continuous stiffeners
            M1Sd_pl = abs(qSd_plate_side) * math.pow(Lg, 2) / 12
            M2Sd_pl = abs(qSd_plate_side) * math.pow(Lg, 2) / 24

            M1Sd_stf = abs(qSd_girder_side) * math.pow(Lg, 2) / 12
            M2Sd_stf = abs(qSd_girder_side) * math.pow(Lg, 2) / 24
            # #Lateral pressure on plate side:
            def iter_plate(zstar):
                uf_7_48 = NySd / NksRd + (M1Sd_pl - NySd * zstar) / (Ms1Rd * (1 - NySd / NE)) + u
                uf_7_49 = NySd / NkpRd - 2 * NySd / NRd + (M1Sd_pl - NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                uf_7_50 = NySd / NksRd - 2 * NySd / NRd + (M2Sd_pl + NySd * zstar) / (MstRd * (1 - NySd / NE)) + u
                uf_7_51 = NySd / NkpRd + (M2Sd_pl + NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                return max([uf_7_48, uf_7_49, uf_7_50, uf_7_51])

            from scipy.optimize import minimize_scalar
            tolerance: float = (zp + zt) / 1000
            res_iter_pl = minimize_scalar(iter_plate, method="Bounded", bounds=(-zt + self._panel._girder.tf / 2, zp), options={'xatol': tolerance})

            if type(res_iter_pl.fun) == list:
                girder_data['UF Cont. plate side'] = res_iter_pl.fun[0]
            else:
                girder_data['UF Cont. plate side'] = res_iter_pl.fun
            #     Lateral pressure on girder side:
            def iter_girder(zstar):
                uf_7_52 = NySd / NksRd - 2 * NySd / NRd + (M1Sd_stf + NySd * zstar) / (MstRd * (1 - NySd / NE)) + u
                uf_7_53 = NySd / NkpRd + (M1Sd_stf + NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                uf_7_54 = NySd / NksRd + (M2Sd_stf - NySd * zstar) / (Ms2Rd * (1 - NySd / NE)) + u
                uf_7_55 = NySd / NkpRd - 2 * NySd / NRd + (M2Sd_stf - NySd * zstar) / (MpRd * (1 - NySd / NE)) + u
                return max([uf_7_52, uf_7_53 ,uf_7_54 ,uf_7_55])

            res_iter_girder = minimize_scalar(iter_girder, method="Bounded", bounds=(-zt + self._panel._girder.tf / 2, zp), options={'xatol': tolerance})

            if type(res_iter_girder.fun) == list:
                girder_data['UF Cont. girder side'] = res_iter_girder.fun[0]
            else:
                girder_data['UF Cont. girder side'] = res_iter_girder.fun

        return girder_data


    def local_buckling(self, optimizing: bool=False):
        '''
        Checks for girders and stiffeners
        '''
        
        if self._panel._stiffener is not None:
            fy = self._panel._stiffener._material._strength
            max_web_stf = 42 * self._panel._stiffener.tw * math.sqrt(235 / fy) if self._panel._stiffener.stiffener_type != 'FB' else 0
            max_flange_stf = (14 if self._panel._stiffener._fabrication_method == 'welded' else 15) * self._panel._stiffener.tf * math.sqrt(235 / fy)
        else:
            max_web_stf = 0
            max_flange_stf = 0

        if self._panel._girder is not None:
            fy = self._panel._girder._material._strength
            max_web_girder = 42 * self._panel._girder.tw * math.sqrt(235 / fy) if self._panel._girder.stiffener_type != 'FB' else 0
            max_flange_girder = (14 if self._panel._girder._fabrication_method == 'welded' else 15) * self._panel._girder.tf * math.sqrt(235 / fy)
        else:
            max_web_girder = 0
            max_flange_girder = 0

        return {'Stiffener': [max_web_stf, max_flange_stf], 'Girder': [max_web_girder, max_flange_girder]}


    def get_one_line_string_mixed(self):
        ''' Returning a one line string. '''
        return 'pl_' + str(round(self._panel._plate.s, 1)) + 'x' + str(round(self._panel._plate.th, 1)) + ' stf_' + \
               self._panel._stiffener.stiffener_type + \
               str(round(self._panel._stiffener.hw, 1)) + 'x' + str(round(self._panel._stiffener.tw, 1)) + '+' + \
               str(round(self._panel._stiffener.b, 1)) + 'x' + \
               str(round(self._panel._stiffener.tf, 1))


    def get_extended_string_mixed(self):
        ''' Some more information returned. '''
        return 'span: '+str(round(self._panel._plate.s, 4)) + ' stf. type: ' + \
               self._panel._stiffener.stiffener_type + ' pressure side: ' + self._pressure_side


# still to add Shell()
# still to add CylinderAndCurvedPlate()
# still to add CalcFatigue()
# still to add PULSpanel()

def main():
    # Create a custom logger
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    #logger = logging.getLogger("anystruct")
    logger = logging.getLogger("anystruct")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # so not to create another handler if it has already been defined in another module
    # doesn't seem to be working for file, but there the problem of multiple logs does not occur
    if not logger.hasHandlers():
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    mat_steel_355: Material = Material(206000e6, 0.3, 355e6)
    plate: Plate = Plate(0.32, 8.5, 0.020, mat_steel_355)
    stiffener: Stiffener = Stiffener("L", 0.200, 0.010, 0.100, 0.010, material=mat_steel_355)    
    stiffened_panel: StiffenedPanel = StiffenedPanel(plate, stiffener, "continuous", girder_length=5)
    stress: Stress = Stress(130e6, 130e6, 0, 0, 10e6)

    buckling_input: BucklingInput = BucklingInput(stiffened_panel, 0, "both sides", stress)

    dNVBuckling: DNVBuckling = DNVBuckling(buckling_input, None)

    results: Dict[str, Any] = dNVBuckling.plated_structures_buckling()
    for key, value in results.items():
        print(key, value)


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)
    main()