import math
from typing import Optional

from pydantic import BaseModel, field_validator, Field

from .material import Material

class Stiffener(BaseModel):
    type: str
    web_height: float
    web_th: float
    flange_width: float
    flange_th: float
    dist_between_lateral_supp: Optional[float] = Field(default=None)
    fabrication_method: str = Field(default='welded', pattern='(?i)^(welded|rolled)$')
    # flange_eccentricity: float = 0
    material: Material


    class Config:
        # Pydantic configuration, such that no extra fields (eg attributes) are allowed
        extra = 'forbid'


    @field_validator('type')
    def check_type(cls, value):
        if value.upper() not in ['FB', 'T', 'L', 'BULB', 'HP', 'HP-BULB', 'HP-PROFILE', 'L-BULB']:
            raise ValueError('Invalid stiffener type. Should be either "FB", "T", "L", "BULB", "HP", "HP-BULB", "HP-PROFILE", or "L-BULB"')
        return value.upper()


    # Property decorators are used in buckling. IN mm!    
    @property # in mm
    def hw(self):
        return self.web_height * 1000
    @hw.setter # in mm
    def hw(self, val):
        self.web_height = val / 1000

    @property # in mm
    def tw(self):
        return self.web_th * 1000
    @tw.setter # in mm
    def tw(self, val):
        self.web_th = val / 1000

    @property # in mm
    def b(self):
        return self.flange_width * 1000
    @b.setter # in mm
    def b(self, val):
        self.flange_width = val / 1000

    @property # in mm
    def tf(self):
        return self.flange_th * 1000
    @tf.setter # in mm
    def tf(self, val):
        self.flange_th = val / 1000


    @property  # in mm
    def dist_between_lateral_supp_mm(self):
        if self.dist_between_lateral_supp == None:
            return None
        return self.dist_between_lateral_supp * 1000
    @dist_between_lateral_supp_mm.setter  # in mm
    def dist_between_lateral_supp_mm(self, val):
        if self.dist_between_lateral_supp == None:
            return None
        self.dist_between_lateral_supp = val / 1000 

    @property  # in mm
    def As(self):
        return self.tw * self.hw + self.b * self.tf


    def ToShortString(self) -> str:
        return 'wHxwTxfWxfT' + str(round(self.web_height, 3)) + 'x' + str(round(self.web_th, 3)) + 'x' + str(round(self.flange_width, 3)) + 'x' + str(round(self.flange_th, 3))


    def get_beam_string(self) -> str:
        ''' Returning a string. '''
        if type(self.type) != str:
            print('error')

        base_name = self.type+ '_' + str(round(self.web_height*1000, 0)) + 'x' + \
                   str(round(self.web_th*1000, 0))
        if self.type == 'FB':
            ret_str = base_name
        elif self.type in ['L-bulb', 'bulb', 'hp']:
            ret_str = 'Bulb'+str(int(self.web_height*1000 + self.flange_th*1000))+'x'+\
                      str(round(self.web_th*1000, 0))+ '_(' +str(round(self.web_height*1000, 0)) + 'x' + \
                   str(round(self.web_th*1000, 0))+'_'+ str(round(self.flange_width*1000, 0)) + 'x' + \
                      str(round(self.flange_th*1000, 0))+')'
        else:
            ret_str = base_name + '__' + str(round(self.flange_width*1000, 0)) + 'x' + \
                      str(round(self.flange_th*1000, 0))

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
        tf = self.flange_th * 1000
        tw = self.web_th * 1000 if reduced_tw is None else reduced_tw
        bf = self.flange_width * 1000
        hw = self.web_height * 1000

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
        ecc = 0 if self.type in ['FB', 'T'] else self.flange_width / 2 - self.web_th / 2
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
        tf = self.flange_th * 1000
        tw = self.web_th * 1000 if reduced_tw is None else reduced_tw
        ef = self.get_flange_eccentricity() * 1000
        hw = self.web_height * 1000
        b = self.flange_width * 1000

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
        if self.type == 'FB':
            ef = self.web_height
        elif self.type in ['L', 'T', 'L-bulb', 'HP-profile', 'HP', 'HP-bulb']:
            ef = self.web_height + 0.5 * self.flange_th
        else:
            raise TypeError("Stiffener of type " + self.type + " not implemented in get_ef_iacs")
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
        e = (self.web_height * self.web_th * (self.web_height / 2) + self.flange_width * self.flange_th *
             (self.web_height + self.web_th / 2)) / (self.web_height * self.web_th + self.flange_width * self.flange_th)
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
            assert plate_width >= 0, "If plate thickness is provided, also the width must be provided and positive."

        tf1 = plate_thickness
        b1 = plate_width

        h = self.flange_th + self.web_height + tf1
        tw = self.web_th if reduced_tw == None else reduced_tw
        hw = self.web_height
        tf2 = self.flange_th
        b2 = self.flange_width

        Ax = tf1 * b1 + tf2 * b2 + hw * tw
        Iyc = (1 / 12) * (b1 * math.pow(tf1, 3) + b2 * math.pow(tf2, 3) + tw * math.pow(hw, 3))
        ez = (tf1 * b1 * (h - tf1 / 2) + hw * tw * (tf2 + hw / 2) + tf2 * b2 * (tf2 / 2)) / Ax
        Iy = Iyc + (tf1 * b1 * math.pow(tf2 + hw + tf1 / 2, 2) + tw * hw * math.pow(tf2 + hw / 2, 2) +
             tf2 * b2 * math.pow(tf2 / 2, 2)) - Ax * math.pow(ez, 2)

        return Iy


    def get_cross_section_area(self,  plate_thickness: float=0, plate_width: float=0) -> float:
        """
        Calculate and return the cross-sectional area.

        Parameters:
        -----------
        plate_thickness : float, optional
            Plate thickness to be included in the cross-sectional area. Default is 0.
        plate_width : bool, optional
            Plate width to be included in the cross-sectional area. Default is 0.

        Returns:
        --------
        float
            Cross-sectional area.
        """
        return plate_width * plate_thickness + self.flange_width * self.flange_th + self.web_height * self.web_th


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
        tw = self.web_th * 1000 if reduced_tw is None else reduced_tw
        hw = self.web_height * 1000
        tf2 = self.flange_th * 1000
        b2 = self.flange_width * 1000

        if self.type == 'FB':
            Iz = math.pow(tw, 3) * hw / 12
        elif self.type == 'T':
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
        tw = self.web_th
        hw = self.web_height
        tf2 = self.flange_th
        b2 = self.flange_width

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
        tf2 = self.flange_th
        b2 = self.flange_width
        h = self.flange_th + self.web_height + tf1
        tw = self.web_th
        hw = self.web_height

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


    def get_cross_section_centroid(self, plate_thickness: float=0, plate_width: float=0, reduced_tw=None) -> float:
        """
        Calculate and return the cross-sectional centroid.
        Optionally with effective plate.

        Parameters:
        -----------
        Parameters:
        -----------
        plate_thickness : float, optional
            Thickness of the plate to used in the calculation of stiffener with plate, in meter. Default is 0 (without plate)
        plate_width : float, optional
            Width of the plate to used in the calculation of stiffener with plate, in meter. Default is 0 (without plate)
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

        tf2 = self.flange_th
        b2 = self.flange_width
        tw = self.web_th if reduced_tw == None else reduced_tw / 1000
        hw = self.web_height
        Ax = tf1 * b1 + tf2 * b2 + hw * tw
        effana = (tf1 * b1 * tf1 / 2 + hw * tw * (tf1 + hw / 2) + tf2 * b2 * (tf1 + hw + tf2 / 2)) / Ax

        return effana


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
        return ((self.flange_th * self.web_th) + \
                (self.web_height * self.web_th))
