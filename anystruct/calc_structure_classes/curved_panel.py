import math
from typing import Optional

from pydantic import BaseModel, field_validator

from .material import Material

class CurvedPanel(BaseModel):
    '''
    Curved panel class

    Attributes
    ----------
    thickness: float
        plate thickness
    radius: float
        radius of the cylinder
    s: float
        panel s, or distance between longitudinal stiffeners
    l: float
        panel l, or unstiffened cylinder length or distance between ring stiffeners
    material: Material
        material of the panel
    cone_r1: Optional[float]
        cone r1, or radius of the small end of the cone
    cone_r2: Optional[float]
        cone r2, or radius of the large end of the cone
    cone_alpha: Optional[float]
        Cone angle in degrees
    '''

    thickness: float
    radius: float
    s: float
    l: float
    material: Material
    cone_r1: Optional[float] = None
    cone_r2: Optional[float] = None
    cone_alpha: Optional[float] = None

    # check that the thickness is not zero and positive
    @field_validator('thickness')
    def check_thickness(cls, value):
        if value <= 0:
            raise ValueError('thickness must be positive')
        return value
    
    @field_validator('radius')
    def check_radius(cls, value):
        if value <= 0:
            raise ValueError('radius must be positive')
        return value


    @property
    def Zs(self):
        # note that the formula is unitless
        Zs = (math.pow(self.s, 2) / \
              (self.radius * self.thickness)) * \
                math.sqrt(1 - math.pow(self.material.poisson, 2))  # The curvature parameter Zs (3.3.3)
        
        return Zs
    
    
    @ property
    def Zl(self):
        # note that the formula is unitless
        Zl = math.pow(self.l, 2) * math.sqrt(1 - math.pow(self.material.poisson, 2)) / (self.radius * self.thickness)
        return Zl


    def get_effective_width_shell_plate(self):
        return 1.56 * math.sqrt(self.radius * self.thickness) / (1 + 12 * self.thickness / self.radius)



