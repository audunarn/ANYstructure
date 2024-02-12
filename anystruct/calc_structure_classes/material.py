from pydantic import BaseModel


class Material(BaseModel):
    young: float
    poisson: float
    strength: float
    mat_factor: float = 1.15
    density: float = 78550
    # def __init__(self, young: float, poisson: float, strength: float, mat_factor: float=1.15, density: float=7850):
    #     self._young: float = young
    #     self._poisson: float = poisson
    #     self._strength: float = strength
    #     self._mat_factor: float = mat_factor
    #     self._density: float = density


    def __str__(self) -> str:
        return 'Young\'s modulus: ' + str(self.young) + ' Poisson ratio: ' + str(self.poisson) + ' Yield strength: ' + str(self.strength)


    def ToShortString(self) -> str:
        return 'Y' + str(self.strength)


    def get_fy(self) -> float:
        '''
        Return material yield
        :return:
        '''
        return self.strength

