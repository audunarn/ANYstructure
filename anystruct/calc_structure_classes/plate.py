from pydantic import BaseModel, ConfigDict

from .material import Material


class Plate(BaseModel):
    spacing: float
    span: float
    thickness: float
    material: Material

    model_config = ConfigDict(extra='forbid')

    def __eq__(self, other):
        """
        Check equality between two Plate instances.
        
        Args:
            other: Another object to compare with
            
        Returns:
            bool: True if both objects are Plate instances with identical attributes
        """
        if not isinstance(other, Plate):
            return False
        
        return (
            self.spacing == other.spacing and
            self.span == other.span and
            self.thickness == other.thickness and
            self.material == other.material
        )

    def ToShortString(self) -> str:
        return 'lxb' + str(self.span) + 'x' + str(self.spacing)

    # Property decorators are used in buckling. IN mm!    
    @property # in mm
    def s(self):
        return self.spacing * 1000
    @s.setter # in mm
    def s(self, val):
        self.spacing = val / 1000

    @property # in mm
    def l(self):
        return self.span * 1000
    @l.setter # in mm
    def l(self, val):
        self.span = val / 1000

    @property # in mm
    def th(self):
        return self.thickness * 1000
    @th.setter # in mm
    def th(self, val):
        self.thickness = val / 1000
