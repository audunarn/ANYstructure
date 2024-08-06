from pydantic import BaseModel, ConfigDict, Field

class Puls(BaseModel):
    puls_method: int = Field(default=1)
    puls_boundary: str = Field(default='Int') # still to add patterns for the other options
    puls_stf_end: str = Field(default='C') # still to add patterns for the other options
    puls_sp_or_up: str = Field(default='SP') # still to add patterns for the other options
    puls_up_boundary: str = Field(default='SSSS') # still to add patterns for the other options

    model_config = ConfigDict(extra='forbid')

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
