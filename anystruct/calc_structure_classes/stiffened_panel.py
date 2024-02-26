from pydantic import BaseModel, field_validator
import math
from typing import Optional, Union

from .plate import Plate
from .stiffener import Stiffener


class StiffenedPanel(BaseModel):
    plate: Plate
    stiffener: Optional[Stiffener] = None
    stiffener_end_support: Optional[str] = None
    girder: Optional[Stiffener] = None
    girder_end_support: Optional[str] = None
    girder_length: Optional[float] = None
    girder_panel_length: Optional[float] = None
    # def __init__(self, **kwargs):
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
    
    @field_validator('stiffener_end_support')
    def prevent_stf_end_supp(cls, v):
        if v is not None:
            assert v.lower() in ["continuous", "sniped"], 'stiffener_end_support should be either "continuous" or "sniped"'
        return v
    @field_validator('girder_end_support')
    def prevent_grd_end_supp(cls, v):
        if v is not None:
            assert v.lower() in ["continuous", "sniped"], 'girder_end_support should be either "continuous" or "sniped"'
        return v


    def ToShortString(self) -> str:
        assert self.stiffener is not None
        end_supp: str = self.stiffener_end_support[0:4] if self.stiffener_end_support != None else "None"
        return self.plate.material.ToShortString() + self.plate.ToShortString() + self.stiffener.material.ToShortString() + self.stiffener.ToShortString() + end_supp


    def get_one_line_string(self) -> str:
        ''' Returning a one line string. '''
        assert self.stiffener is not None
        return 'pl_' + str(round(self.plate.spacing * 1000, 1)) + 'x' + str(round(self.plate.thickness * 1000, 1)) + \
               ' stf_' + self.stiffener.type + \
               str(round(self.stiffener.web_height * 1000, 1)) + 'x' + str(round(self.stiffener.web_th * 1000, 1)) + '+' + \
               str(round(self.stiffener.flange_width * 1000, 1)) + 'x' + str(round(self.stiffener.flange_th * 1000, 1))


    def get_lg(self) -> float:
        '''
        Return the girder length
        :return:
        '''
        return self.girder_length # type: ignore


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
        assert self.stiffener is not None
        tf1 = self.plate.thickness
        tf2 = self.stiffener.flange_th
        b1 = self.plate.spacing
        b2 = self.stiffener.flange_width
        h = self.stiffener.flange_th + self.stiffener.web_height + self.plate.thickness
        tw = self.stiffener.web_th

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
        assert self.stiffener is not None
        tf1 = self.plate.thickness
        tf2 = self.stiffener.flange_th
        b1 = self.plate.spacing
        b2 = self.stiffener.flange_width
        h = self.stiffener.flange_th + self.stiffener.web_height + self.plate.thickness
        tw = self.stiffener.web_th
        hw = self.stiffener.web_height
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
        assert self.stiffener is not None
        return ((self.stiffener.flange_th * self.stiffener.web_th) + \
                (self.stiffener.web_th * self.plate.thickness) + \
                (self.stiffener.web_height * self.stiffener.web_th))


    def get_cross_section_area(self, efficient_se=None, includeplate=True) -> float:
        """
        Calculate and return the cross-sectional area.

        Parameters:
        -----------
        efficient_se : float, optional
            Efficient spacing for the plate. If not provided, plate spacing is used
        includeplate : bool, optional
            If True, includes the plate contribution in the cross-sectional area. Default is True.

        Returns:
        --------
        float
            Cross-sectional area.

        Notes:
        ------
        The cross-sectional area is computed based on the dimensions and properties of the plate and stiffener elements in the structure.
        """
        assert self.stiffener is not None
        tf1 = self.plate.thickness if includeplate else 0
        tf2 = self.stiffener.flange_th
        if includeplate:
            b1 = self.plate.spacing if efficient_se == None else efficient_se
        else:
            b1 = 0
        
        b2 = self.stiffener.flange_width
        h = self.stiffener.web_height
        tw = self.stiffener.web_th
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
        plate_density: float = density if density is not None else self.plate.material.density
        
        

        if self.stiffener is None and self.girder is None:
            return plate_density * self.plate.span  * self.plate.thickness * panel_width
        elif self.girder is None and self.stiffener is not None:
            stiffener_density: float = density if density is not None else self.stiffener.material.density
            assert panel_width >= 2 * self.plate.spacing
            number_ofstiffeners: float = panel_width / self.plate.spacing
            return plate_density * self.plate.span  * self.plate.thickness * panel_width + \
                    number_ofstiffeners * stiffener_density * (self.stiffener.web_height * self.stiffener.web_th + self.stiffener.flange_width * self.stiffener.flange_th)
        else:
            assert self.girder is not None and self.stiffener is not None and self.girder_length is not None and self.girder_length is not None and self.girder_panel_length is not None
            stiffener_density: float = density if density is not None else self.stiffener.material.density
            girder_density: float = density if density is not None else self.girder.material.density
            number_ofstiffeners: float = self.girder_length / self.plate.spacing
            number_ofgirders: float = self.girder_length / self.plate.span
            return plate_density * self.plate.thickness * self.girder_length * self.girder_panel_length + \
                    number_ofstiffeners * stiffener_density * self.girder_panel_length * (self.stiffener.web_height * self.stiffener.web_th + self.stiffener.flange_width * self.stiffener.flange_th) + \
                    number_ofgirders * girder_density * self.girder_panel_length * (self.girder.web_height * self.girder.web_th + self.girder.flange_width * self.girder.flange_th)



class Stiffened_panel_calc_props(BaseModel):
    # looks like these are parameters for both scantlings and buckling.
    # Maybe can split up in props for scantling calculations and props for buckling calculations
    zstar_optimization: bool = True
    plate_kpp: float = 1
    stf_kps: float = 1
    km1: float = 12
    km2: float = 24
    km3: float = 12
    structure_type: str = 'BOTTOM'
    structure_types: str = 'structure_types'
    lat_load_factor: float = 1
    stress_load_factor: float = 1
    buckling_length_factor_stf: float = 1
    buckling_length_factor_girder: float = 1
    # def __init__(self, zstar_optimization: bool = True, 
    #                     plate_kpp: float = 1,
    #                     stf_kps: float =1 ,
    #                     km1: float = 12,
    #                     km2: float = 24,
    #                     km3: float = 12,
    #                     structure_type: str = 'BOTTOM',
    #                     structure_types: str = 'structure_types',
    #                     lat_load_factor: float=1,
    #                     stress_load_factor: float=1,
    #                     buckling_length_factor_stf: Union[float, None]=None,
    #                     buckling_length_factorgirder: Union[float, None]=None) -> None:
        
        # self._zstar_optimization: bool = zstar_optimization
        # self.plate_kpp: float = plate_kpp
        # self._stf_kps: float = stf_kps
        # self._km1: float = km1
        # self._km2: float = km2
        # self._km3: float = km3
        # self._structure_type: str = structure_type
        # self._structure_types: str = structure_types
        # self._lat_load_factor: float = lat_load_factor
        # self._stress_load_factor: float = stress_load_factor
        # self._buckling_length_factor_stf: Union[float, None] = buckling_length_factor_stf
        # self._buckling_length_factorgirder: Union[float, None] = buckling_length_factorgirder
        # self._dynamic_variable_orientation: float
        # if self.structure_type in self.structure_types['vertical']:
        #     self._dynamic_variable_orientation = 'z - vertical'
        # elif self.structure_type in self.structure_types['horizontal']:
        #     self._dynamic_variable_orientation = 'x - horizontal'


    def get_structure_types(self):
        return self.structure_types


    def get_structure_type(self):
        return self.structure_type


    def get_z_opt(self):
        return self.zstar_optimization


    def get_kpp(self):
        '''
        Return var
        :return:
        '''
        return self.plate_kpp
    
    
    def get_kps(self):
        '''
        Return var
        :return:
        '''
        return self.stf_kps
    
    
    def get_km1(self):
        '''
        Return var
        :return:
        '''
        return self.km1
    
    
    def get_km2(self):
        '''
        Return var
        :return:
        '''
        return self.km2
    
    
    def get_km3(self):
        '''
        Return var
        :return:
        '''
        return self.km3
