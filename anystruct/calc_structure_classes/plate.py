from pydantic import BaseModel

from .material import Material


class Plate(BaseModel):
    spacing: float
    span: float
    thickness: float
    material: Material
    # def __init__(self, spacing: float, span: float, thickness:float=0, material: Material=Material(206e9, 0.3, 235e6)):
    #     self._spacing: float = spacing
    #     self._span: float = span
    #     self._thickness: float = thickness
    #     self._material: Material = material


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
