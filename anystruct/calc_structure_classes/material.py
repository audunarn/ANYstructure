from pydantic import BaseModel, ConfigDict, Field


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
    mat_factor: float = Field(default=1.15)
    density: float = Field(default=78550)

    model_config = ConfigDict(extra='forbid')

    def __eq__(self, other) -> bool:
        """
        Check equality between two Material instances.
        
        Args:
            other: Another object to compare with
            
        Returns:
            bool: True if both objects are Material instances with identical attributes
        """
        if not isinstance(other, Material):
            return False
        
        return (
            self.young == other.young and
            self.poisson == other.poisson and
            self.strength == other.strength and
            self.mat_factor == other.mat_factor and
            self.density == other.density
        )


    def __str__(self) -> str:
        return 'Young\'s modulus: ' + str(self.young) + ' Poisson ratio: ' + str(self.poisson) + ' Yield strength: ' + str(self.strength)


    def ToShortString(self) -> str:
        return 'Y' + str(self.strength)
