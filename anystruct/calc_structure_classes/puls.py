from pydantic import BaseModel

class Puls(BaseModel):
    puls_method: int = 1
    puls_boundary: str = 'Int'
    puls_stf_end: str = 'C'
    puls_sp_or_up: str = 'SP'
    puls_up_boundary: str = 'SSSS'

    # def __init__(self, puls_method: int=1, 
    #                    puls_boundary: str='Int',
    #                    puls_stf_end: str='C',
    #                    puls_sp_or_up: str='SP',
    #                    puls_up_boundary: str='SSSS') -> None:
        
    #     self._puls_method: int = puls_method
    #     self._puls_boundary: str = puls_boundary
    #     self._puls_stf_end: str = puls_stf_end
    #     self._puls_sp_or_up: str = puls_sp_or_up
    #     self._puls_up_boundary: str = puls_up_boundary


    def get_puls_method(self):
        return self.puls_method


    def get_puls_boundary(self):
        return self.puls_boundary


    def get_puls_stf_end(self):
        return self.puls_stf_end


    def get_puls_sp_or_up(self):
        return self.puls_sp_or_up


    def get_puls_up_boundary(self):
        return self.puls_up_boundary
