from pydantic import BaseModel


class Material(BaseModel):
    """
    Represents a material with its properties used in the calculations.

    Attributes:
        young (float): Young's modulus of the material in Pa
        poisson (float): Poisson's ratio of the material.
        strength (float): Yield strength of the material in Pa.
        mat_factor (float, optional): Material factor. Defaults to 1.15.
        density (float, optional): Density of the material. Defaults to 78550 for steel.
    """

    young: float
    poisson: float
    strength: float
    mat_factor: float = 1.15
    density: float = 78550


    def __str__(self) -> str:
        return 'Young\'s modulus: ' + str(self.young) + ' Poisson ratio: ' + str(self.poisson) + ' Yield strength: ' + str(self.strength)


    def ToShortString(self) -> str:
        return 'Y' + str(self.strength)
