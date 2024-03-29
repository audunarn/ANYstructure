from pydantic import BaseModel
from pydantic import BaseModel


class Stress(BaseModel):
    """
    Class representing stress values.
    All stresses in the class are in Pa.

    Attributes:
        sigma_x1 (float): Larger design stress in the longitudinal direction, with tensile stresses taken as negative.
        sigma_x2 (float): Smaller design stress in the longitudinal direction, with tensile stresses taken as negative.
        sigma_y1 (float): Larger design stress in the transverse direction, with tensile stresses taken as negative.
        sigma_y2 (float): Smaller design stress in the transverse direction, with tensile stresses taken as negative.
        tauxy (float): Shear stress value.

    Methods:
        get_sigma_y1() -> float:
            Return the larger design stress in the transverse direction, with tensile stresses taken as negative.
        get_sigma_y2() -> float:
            Return the smaller design stress in the transverse direction, with tensile stresses taken as negative.
        get_sigma_x1() -> float:
            Return the larger design stress in the transverse direction, with tensile stresses taken as negative.
        get_sigma_x2() -> float:
            Return the smaller design stress in the transverse direction, with tensile stresses taken as negative.
        get_tau_xy() -> float:
            Return the shear stress value.
        get_report_stresses() -> str:
            Return a formatted string of all stress values.
        set_stresses(sigy1: float, sigy2: float, sigx1: float, sigx2: float, tauxy: float) -> None:
            Set the stress values. Not the order of the arguments.

    """
    sigma_x1: float
    sigma_x2: float
    sigma_y1: float
    sigma_y2: float
    tauxy: float

    def get_sigma_y1(self) -> float:
        """
        Return the larger design stress in the transverse direction, with tensile stresses taken as negative.

        Returns:
            float: The larger design stress in the transverse direction, with tensile stresses taken as negative.
        """
        return self.sigma_y1

    def get_sigma_y2(self) -> float:
        """
        Return the smaller design stress in the transverse direction, with tensile stresses taken as negative.

        Returns:
            float: The smaller design stress in the transverse direction, with tensile stresses taken as negative.
        """
        return self.sigma_y2

    def get_sigma_x1(self) -> float:
        """
        Return the larger design stress in the transverse direction, with tensile stresses taken as negative.

        Returns:
            float: The larger design stress in the transverse direction, with tensile stresses taken as negative.
        """
        return self.sigma_x1

    def get_sigma_x2(self) -> float:
        """
        Return the smaller design stress in the transverse direction, with tensile stresses taken as negative.

        Returns:
            float: The smaller design stress in the transverse direction, with tensile stresses taken as negative.
        """
        return self.sigma_x2

    def get_tau_xy(self) -> float:
        """
        Return the shear stress value.

        Returns:
            float: The shear stress value.
        """
        return self.tauxy

    def get_report_stresses(self) -> str:
        """
        Return a formatted string of all stress values.

        Returns:
            str: A formatted string of all stress values.
        """
        return (
            "sigma_y1: "
            + str(round(self.sigma_y1, 1))
            + " sigma_y2: "
            + str(round(self.sigma_y2, 1))
            + " sigma_x1: "
            + str(round(self.sigma_x1, 1))
            + " sigma_x2: "
            + str(round(self.sigma_x2, 1))
            + " tauxy: "
            + str(round(self.tauxy, 1))
        )

    def set_stresses(self, sigy1: float, sigy2: float, sigx1: float, sigx2: float, tauxy: float) -> None:
        """
        Set the stress values.

        Args:
            sigy1 (float): Larger design stress in the transverse direction, with tensile stresses taken as negative.
            sigy2 (float): Smaller design stress in the transverse direction, with tensile stresses taken as negative.
            sigx1 (float): Larger design stress in the longitudinal direction, with tensile stresses taken as negative.
            sigx2 (float): Smaller design stress in the longitudinal direction, with tensile stresses taken as negative.
            tauxy (float): Shear stress value.

        Returns:
            None
        """
        self.sigma_y1 = sigy1
        self.sigma_y2 = sigy2
        self.sigma_x1 = sigx1
        self.sigma_x2 = sigx2
        self.tauxy = tauxy


class DerivedStressValues(BaseModel):
    """
    Class representing derived stress values.

    This class is used for returning stress values instead of a tuple.

    Attributes:
        sxsd (float): The value of sxsd.
        sysd (float): The value of sysd.
        sy1sd (float): The value of sy1sd.
        syR (float): The value of syR.
        sjsd (float): The value of sjsd.
        max_vonMises_x (float): The value of max_vonMises_x.
        stress_ratio_long (float): The value of stress_ratio_long.
        stress_ratio_trans (float): The value of stress_ratio_trans.
    """

    sxsd: float = 0
    sysd: float = 0
    sy1sd: float = 0
    syR: float = 0
    sjsd: float = 0
    max_vonMises_x: float = 0
    stress_ratio_long: float = 0
    stress_ratio_trans: float = 0

    # def __init__(self):
    #     self.sxsd: float = 0
    #     self.sysd: float = 0
    #     self.sy1sd: float = 0
    #     self.syR: float = 0
    #     self.sjsd: float = 0
    #     self.max_vonMises_x: float = 0
    #     self.stress_ratio_long: float = 0
    #     self.stress_ratio_trans: float = 0
