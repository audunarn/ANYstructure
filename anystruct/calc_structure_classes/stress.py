from pydantic import BaseModel

class Stress(BaseModel):
    sigma_x1: float
    sigma_x2: float
    sigma_y1: float
    sigma_y2: float
    tauxy: float
    # def __init__(self, sigma_x1: float, sigma_x2: float, sigma_y1: float, sigma_y2: float, tauxy: float):
    #     self._sigma_x1: float = sigma_x1
    #     self._sigma_x2: float = sigma_x2
    #     self._sigma_y1: float = sigma_y1
    #     self._sigma_y2: float = sigma_y2
    #     self._tauxy: float = tauxy


    def get_sigma_y1(self) -> float:
        '''
        Return sigma_y1
        :return:
        '''
        return self.sigma_y1
    
    
    def get_sigma_y2(self) -> float:
        '''
        Return sigma_y2
        :return:
        '''
        return self.sigma_y2
    
    
    def get_sigma_x1(self) -> float:
        '''
        Return sigma_x
        :return:
        '''
        return self.sigma_x1
    
    
    def get_sigma_x2(self) -> float:
        '''
        Return sigma_x
        :return:
        '''
        return self.sigma_x2
    

    def get_tau_xy(self) -> float:
        '''
        Return tau_xy
        :return:
        '''
        return self.tauxy


    def get_report_stresses(self) -> str:
        'Return the stresses to the report'
        return 'sigma_y1: ' + str(round(self.sigma_y1, 1)) + ' sigma_y2: ' + str(round(self.sigma_y2, 1)) + \
               ' sigma_x1: ' + str(round(self.sigma_x1, 1)) +' sigma_x2: ' + str(round(self.sigma_x2, 1)) + \
               ' tauxy: ' + str(round(self.tauxy, 1))


    def set_stresses(self, sigy1: float, sigy2: float, sigx1: float, sigx2: float, tauxy: float) -> None:
        '''
        Setting the global stresses.
        :param sigy1:
        :param sigy2:
        :param sigx:
        :param tauxy:
        :return:
        '''
        self.sigma_y1 = sigy1
        self.sigma_y2  = sigy2
        self.sigma_x1 = sigx1
        self.sigma_x2 = sigx2
        self.tauxy  = tauxy


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