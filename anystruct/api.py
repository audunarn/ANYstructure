import math

try:
    from anystruct.calc_structure import *
    from anystruct.calc_loads import *
    import anystruct.helper as hlp
    from anystruct.helper import *
    import anystruct.api_helpers as api_helpers
    from anystruct.project_application import (
        ProjectFileCodec,
        ProjectHydrationDefaults,
        ProjectOpenService,
        ProjectPersistenceService,
        ProjectSaveInput,
        ProjectSaveService,
    )
    from anystruct.project_state import ProjectState
    from anystruct.report_generator import LetterMaker
    import anystruct.fe_plate_fields as fe_plate_fields
except ModuleNotFoundError:
    # This is due to pyinstaller issues.
    from ANYstructure.anystruct.calc_structure import *
    from ANYstructure.anystruct.calc_loads import *
    import ANYstructure.anystruct.helper as hlp
    from ANYstructure.anystruct.helper import *
    import ANYstructure.anystruct.api_helpers as api_helpers
    from ANYstructure.anystruct.project_application import (
        ProjectFileCodec,
        ProjectHydrationDefaults,
        ProjectOpenService,
        ProjectPersistenceService,
        ProjectSaveInput,
        ProjectSaveService,
    )
    from ANYstructure.anystruct.project_state import ProjectState
    from ANYstructure.anystruct.report_generator import LetterMaker
    import ANYstructure.anystruct.fe_plate_fields as fe_plate_fields


def _optimize_module():
    try:
        import anystruct.optimize as optimize_module
    except ModuleNotFoundError:
        import ANYstructure.anystruct.optimize as optimize_module
    return optimize_module


def _semi_analytical_module():
    try:
        import anystruct.calculate_semianalytical as semi_analytical_module
    except ModuleNotFoundError:
        import ANYstructure.anystruct.calculate_semianalytical as semi_analytical_module
    return semi_analytical_module


def load_project_state(path):
    """Load an ANYstructure project file into canonical project state."""
    return ProjectPersistenceService.load_state_from_path(path)


def save_project_state(project_state, path):
    """Save canonical project state using the supported project-file codec."""
    return ProjectPersistenceService.save_state_to_path(project_state, path)


def open_project(path, hydration_defaults=None):
    """Load and hydrate an ANYstructure project through the application service facade."""
    if hydration_defaults is None:
        hydration_defaults = ProjectHydrationDefaults()
    return ProjectOpenService.open_path(path, hydration_defaults)


def save_project(path, save_input):
    """Create and save project state from a public project save input."""
    return ProjectSaveService.save_path(path, save_input)


def create_fea_result_buckling_session(inp_path, frd_path=None, **kwargs):
    """Scan FE geometry/results and return selectable ANYstructure buckling panels.

    The returned session contains one panel record per discovered buckling field.
    Each panel includes inferred geometry, material defaults, reduced FE stresses,
    optional buckling results, and 2D plot bounds for GUI rendering.
    """

    return fe_plate_fields.create_fea_buckling_session(inp_path, frd_path, **kwargs)


def available_fea_stress_reduction_methods():
    """Return supported FE stress-to-panel interpretation methods."""

    return fe_plate_fields.available_stress_reduction_methods()


def analyze_fea_result_buckling(inp_path, frd_path, **kwargs):
    """Read INP/FRD, infer panels, reduce stresses, and return a serializable summary."""

    return create_fea_result_buckling_session(inp_path, frd_path, **kwargs).summary()


def create_runtime_fea_result_buckling_session(runtime_result, **kwargs):
    """Scan a runtime FEM result and return selectable ANYstructure buckling panels."""

    return fe_plate_fields.create_runtime_fea_buckling_session(runtime_result, **kwargs)


def analyze_runtime_fea_result_buckling(runtime_result, **kwargs):
    """Reduce runtime FEM stresses panel by panel and return a serializable summary."""

    return create_runtime_fea_result_buckling_session(runtime_result, **kwargs).summary()


def import_sesam_fem_model(path, **kwargs):
    """Import a SESAM FEM model through ANYsolver."""

    from anysolver.sesam_fem.importer import import_sesam_fem

    return import_sesam_fem(path, **kwargs)


def run_sesam_fem_static(path, **kwargs):
    """Import a SESAM FEM model and run the linear FE solver."""

    from anysolver import solve_linear
    from anysolver.sesam_fem.importer import import_sesam_fem

    imported = import_sesam_fem(path, **kwargs)
    if imported.model is None:
        raise RuntimeError("No model was generated from the FEM file.")

    displacements, solver_info = solve_linear(
        imported.model,
        load_case=None,
        solver_type=kwargs.get("solver_type", "direct"),
        constraint_mode=kwargs.get("constraint_mode", "auto"),
    )

    class _DummySesamStaticRun:
        def __init__(self, sp, ir, disp, si):
            self.source_path = sp
            self.import_result = ir
            self.displacements = disp
            self.solver_info = si

    return _DummySesamStaticRun(str(path), imported, displacements, solver_info)


class FlatStru():
    '''
    API class for all flat plates.\n
    Domains:\n
    1. 'Flat plate, unstiffened'\n
    2. 'Flat plate, stiffened'\n
    '''
    def __init__(self, calculation_domain: str = None):
        '''

        :param calculation_domain:  "Flat plate, unstiffened", "Flat plate, stiffened",
                                    "Flat plate, stiffened with girder"
        :type calculation_domain: str
        '''
        super().__init__()
        api_helpers.assert_choice(calculation_domain, api_helpers.FLAT_STRUCTURE_DOMAINS, 'calculation_domain')

        self._Plate = CalcScantlings()
        self._Stiffeners = CalcScantlings()
        self._Girder = CalcScantlings()
        self._calculation_domain = calculation_domain
        self._FlatStructure = AllStructure(Plate=self._Plate,
                           Stiffener=None if calculation_domain == 'Flat plate, unstiffened' else self._Stiffeners,
                           Girder=None if calculation_domain in ['Flat plate, unstiffened', 'Flat plate, stiffened']
                           else self._Girder, calculation_domain=calculation_domain)
        self._buckling_method = "DNV-RP-C201 - prescriptive"
        self._buckling_acceptance = "ultimate"
        self._ml_buckling_model = None

    @property
    def calculation_domain(self):
        return self._calculation_domain
    @calculation_domain.setter
    def calculation_domain(self, val):
        self._calculation_domain = val
    @property
    def Plate(self):
        return self._Plate
    @Plate.setter
    def Plate(self, val):
        self._Plate = val
    @property
    def Stiffeners(self):
        return self._Stiffeners
    @Stiffeners.setter
    def Stiffeners(self, val):
        self._Stiffeners = val
    @property
    def Girder(self):
        return self._Girder
    @Girder.setter
    def Girder(self, val):
        self._Girder = val

    def set_material(self, mat_yield = 355, emodule = 210000, material_factor = 1.15, poisson = 0.3):
        '''
        Set the material properties for all structure.

        :param mat_yield: material yield, fy,  given in MPa
        :type mat_yield: float
        :param emodule: elastic module, E, given in MPa
        :type emodule: float
        :param material_factor: material factor, typically 1.15 or 1.1
        :type material_factor: float
        :param poisson: poisson number of matieral
        :type poisson: float
        :return:
        :rtype:
        '''
        self._FlatStructure.mat_yield = api_helpers.mpa_to_pa(mat_yield)
        self._FlatStructure.E = api_helpers.mpa_to_pa(emodule)
        self._FlatStructure.v = poisson
        self._FlatStructure.mat_factor = material_factor

        for sub_cls in [self.Plate, self.Stiffeners, self.Girder]:
            if sub_cls is not None:
                sub_cls.mat_yield = api_helpers.mpa_to_pa(mat_yield)
                sub_cls.E = api_helpers.mpa_to_pa(emodule)
                sub_cls.v = poisson
                sub_cls.mat_factor = material_factor

    def set_fixation_parameters(self, kpp: float = 1, kps: float = 1,
                                km1: float = 12, km2: float = 24, km3: float = 12):
        '''
        Used for calculation of special provisions for plating and stiffeners in steel structures.

        :param kpp: fixation parameter for plate, 1.0 for clamped edges, 0.5 for simply supported edges
        :type kpp: float
        :param kps: fixation parameter for stiffeners, 1.0 if at least one end is clamped, 0.9 if both ends are simply supported
        :type kps:
        :param km1: Bending moment and shear force factors, see DNV standards or ANYstructure GUI
        :type km1: float
        :param km2: Bending moment and shear force factors, see DNV standards or ANYstructure GUI
        :type km2: float
        :param km3: Bending moment and shear force factors, see DNV standards or ANYstructure GUI
        :type km3: float
        :return:
        :rtype:
        '''
        for sub_cls in [self.Plate, self.Stiffeners, self.Girder]:
            if sub_cls is not None:
                sub_cls._plate_kpp = kpp
                sub_cls._stf_kps = kps
                sub_cls._km1 = km1
                sub_cls._km2 = km2
                sub_cls._km3 = km3

    def _active_flat_objects(self):
        return [
            sub_cls for sub_cls in [
                self._FlatStructure.Plate,
                self._FlatStructure.Stiffener,
                self._FlatStructure.Girder,
            ] if sub_cls is not None
        ]

    def _default_puls_panel_type(self):
        return "UP" if self._FlatStructure.Stiffener is None else "SP"

    def _set_puls_field(self, field_name, value):
        for sub_cls in self._active_flat_objects():
            setattr(sub_cls, field_name, value)

    def _ensure_puls_defaults(self):
        plate = self._FlatStructure.Plate
        if plate.get_puls_sp_or_up() not in api_helpers.PULS_PANEL_TYPES:
            self._set_puls_field("_puls_sp_or_up", self._default_puls_panel_type())
        if plate.get_puls_boundary() not in ("Int", "GL", "GT"):
            self._set_puls_field("_puls_boundary", "Int")
        if plate.get_puls_stf_end() not in api_helpers.SUPPORT_TYPES:
            self._set_puls_field("_puls_stf_end", "Continuous")
        if plate.get_puls_up_boundary() in (None, ""):
            self._set_puls_field("_puls_up_boundary", "SSSS")
        if plate.get_puls_method() not in api_helpers.BUCKLING_ACCEPTANCE_TYPES:
            self._set_puls_field("_puls_method", self._buckling_acceptance)

    def _design_pressure_kpa(self):
        return self._FlatStructure.lat_press * 1000

    def _selected_buckling_uf(self, results):
        if self._buckling_acceptance == "ultimate":
            return results.get("ultimate UF", float("inf"))
        return results.get("buckling UF", float("inf"))

    def _semi_analytical_buckling_results(self):
        self._ensure_puls_defaults()
        mat_fac = float(self._FlatStructure.Plate.mat_factor)
        semi_analytical = _semi_analytical_module()
        try:
            result = semi_analytical.solve_anystructure_panel(
                self._FlatStructure,
                self._design_pressure_kpa(),
            )
            valid_prediction = int(result.get("valid_prediction", 0)) == 1
        except Exception as err:
            result = {
                "buckling_usage_factor": float("inf"),
                "ultimate_usage_factor": float("inf"),
                "panel_family": None,
                "confidence": "low",
                "valid_label": "SemiAnalytical S3/U3 error",
                "invalid_reason": str(err),
                "csr_vector": [0, 0, 0, 0],
                "csr_color": "red",
                "csr_requirement": {},
            }
            valid_prediction = False

        buckling_raw = float(result.get("buckling_usage_factor", float("inf"))) if valid_prediction else float("inf")
        ultimate_raw = float(result.get("ultimate_usage_factor", float("inf"))) if valid_prediction else float("inf")
        diagnostics = result.get("result", {}).get("diagnostics", {})
        buckling_diagnostics = diagnostics.get("buckling", {}) if isinstance(diagnostics, dict) else {}
        strength_diagnostics = diagnostics.get("buckling_strength", {}) if isinstance(diagnostics, dict) else {}
        api_result = {
            "method": "SemiAnalytical S3/U3",
            "buckling UF": buckling_raw * mat_fac,
            "ultimate UF": ultimate_raw * mat_fac,
            "buckling UF raw": buckling_raw,
            "ultimate UF raw": ultimate_raw,
            "material factor": mat_fac,
            "acceptance": 1.0,
            "panel family": result.get("panel_family", None),
            "confidence": result.get("confidence", None),
            "error": result.get("invalid_reason") or "",
            "available": valid_prediction,
            "valid prediction": 1 if valid_prediction else 0,
            "valid label": result.get("valid_label", "SemiAnalytical S3/U3 unsupported or invalid"),
            "CSR": result.get("csr_vector", [0, 0, 0, 0]),
            "CSR color": result.get("csr_color", "red"),
            "CSR requirement": result.get("csr_requirement", {}),
            "controlling limit": strength_diagnostics.get("controlling_limit", ""),
            "critical mode": buckling_diagnostics.get("critical_mode", ""),
            "critical failure family": buckling_diagnostics.get("critical_failure_family", ""),
            "elastic buckling UF raw": strength_diagnostics.get("elastic_usage_factor", None),
            "ultimate control UF raw": strength_diagnostics.get("ultimate_usage_factor", None),
        }
        api_result["selected UF"] = self._selected_buckling_uf(api_result)
        return api_result

    def _numeric_ml_required_keys(self, prefix):
        return [
            f"{prefix} validity predictor",
            f"{prefix} validity xscaler",
            f"{prefix} UF reg predictor",
            f"{prefix} UF reg xscaler",
            f"{prefix} UF reg yscaler",
        ]

    def _numeric_ml_buckling_results(self, ml_algo=None):
        self._ensure_puls_defaults()
        op = _optimize_module()
        ml_algo = self._ml_buckling_model if ml_algo is None else ml_algo
        mat_fac = float(self._FlatStructure.Plate.mat_factor)
        prefix = op._get_numeric_pipeline_prefix(self._FlatStructure)
        input_row = op._get_ml_input_for_optimization(self._FlatStructure, self._design_pressure_kpa())
        required_keys = self._numeric_ml_required_keys(prefix)
        missing = [key for key in required_keys if ml_algo is None or key not in ml_algo or ml_algo[key] is None]

        if missing:
            return {
                "method": "ML-Numeric (PULS based)",
                "buckling UF": float("inf"),
                "ultimate UF": float("inf"),
                "buckling UF raw": float("inf"),
                "ultimate UF raw": float("inf"),
                "material factor": mat_fac,
                "pipeline prefix": prefix,
                "input": input_row,
                "error": "Missing numeric ML model(s): " + ", ".join(missing),
                "available": False,
                "valid prediction": None,
                "valid label": "numeric ML unavailable",
                "selected UF": float("inf"),
            }

        try:
            numeric_result = op._predict_numeric_uf_group(
                ml_algo=ml_algo,
                input_rows=[input_row],
                prefix=prefix,
                mat_fac=mat_fac,
            )[0]
            buckling_uf = float(numeric_result[0])
            ultimate_uf = float(numeric_result[1])
            valid_prediction = int(numeric_result[2])
        except Exception as err:
            return {
                "method": "ML-Numeric (PULS based)",
                "buckling UF": float("inf"),
                "ultimate UF": float("inf"),
                "buckling UF raw": float("inf"),
                "ultimate UF raw": float("inf"),
                "material factor": mat_fac,
                "pipeline prefix": prefix,
                "input": input_row,
                "error": str(err),
                "available": False,
                "valid prediction": None,
                "valid label": "numeric ML error",
                "selected UF": float("inf"),
            }

        valid_result = valid_prediction == 1 and math.isfinite(buckling_uf) and math.isfinite(ultimate_uf)
        api_result = {
            "method": "ML-Numeric (PULS based)",
            "buckling UF": buckling_uf if valid_result else float("inf"),
            "ultimate UF": ultimate_uf if valid_result else float("inf"),
            "buckling UF raw": buckling_uf / mat_fac if valid_result else float("inf"),
            "ultimate UF raw": ultimate_uf / mat_fac if valid_result else float("inf"),
            "material factor": mat_fac,
            "pipeline prefix": prefix,
            "input": input_row,
            "error": "",
            "available": True,
            "valid prediction": valid_prediction,
            "valid label": "valid numeric UF predicted" if valid_result else "invalid/NaN UF predicted",
        }
        api_result["selected UF"] = self._selected_buckling_uf(api_result)
        return api_result

    def set_ml_buckling_model(self, ml_algo):
        """
        Set the numeric ML model/scaler bundle used by the ``ML-Numeric (PULS based)`` method.
        """
        self._ml_buckling_model = ml_algo

    def get_available_buckling_methods(self):
        return api_helpers.BUCKLING_CALCULATION_METHODS

    def get_buckling_results(self, calculation_method: str = None, ml_algo=None):
        '''
        Return buckling results for the active calculation method. UF - Utilization Factor.\n
        DNV-RP-C201 returns the legacy result dictionary:\n
        Plate : {'Plate buckling': UF}\n
        Stiffener: {'Overpressure plate side': UF, 'Overpressure stiffener side': UF,\n
                    'Resistance between stiffeners': UF, 'Shear capacity': UF}\n
        Girder: {'Overpressure plate side': UF, 'Overpressure girder side': UF, 'Shear capacity': UF}\n
        Local buckling {'Stiffener': [UF web, UF flange], 'Girder': [UF web, UF flange]}\n
        SemiAnalytical and ML-Numeric return a method result dictionary with buckling/ultimate UF,\n
        raw UF, validity, and selected UF fields.\n
        :return: Buckling results for the selected method\n
        :rtype: dict
        '''
        calculation_method = self._buckling_method if calculation_method is None else calculation_method
        api_helpers.assert_choice(calculation_method, api_helpers.BUCKLING_CALCULATION_METHODS, 'calculation_method')

        if calculation_method == "DNV-RP-C201 - prescriptive":
            return  self._FlatStructure.plate_buckling()
        if calculation_method == "SemiAnalytical S3/U3":
            return self._semi_analytical_buckling_results()
        return self._numeric_ml_buckling_results(ml_algo=ml_algo)

    def set_plate_geometry(self, spacing: float = 700, thickness: float = 20, span: float = 4000):

        '''
        Set the properties of plate. If the plate is stiffened, spacing is between the stiffeners. If the plate
        is not unstiffened, the spacing is the width of the considered plate.

        :param spacing: stiffener spacing
        :type spacing: float
        :param thickness: plate thickness
        :type thickness: float
        :param span: span of plate field
        :type span: float

        :return:
        :rtype:
        '''

        self._FlatStructure.Plate.t = thickness
        self._FlatStructure.Plate.spacing = spacing
        self._FlatStructure.Plate.span = api_helpers.mm_to_m(span)
        self._FlatStructure.Plate.girder_lg = 10 # placeholder value
        for sub_cls in [self._FlatStructure.Stiffener, self._FlatStructure.Girder]:
            if sub_cls is not None:
                sub_cls.t = thickness
                sub_cls.span = self._FlatStructure.Plate.span


    def set_stresses(self, pressure: float = 0, sigma_x1: float = 0,sigma_x2: float = 0, sigma_y1: float = 0,
                     sigma_y2: float = 0, tau_xy: float = 0):
        '''
        Set loads applied on the plate sides.\n
        x1 and y1 is on one side of the plate\n
        x2 and y2 is the other side\n
        tau_xy act uniformly on the plate field\n
        Stresses are in MPA.\n
        Use POSITIVE numbers for compression pressure, stresses and forces\n

        :param pressure: Lateral load / pressure: Psd [MPa]
        :type pressure: float
        :param sigma_x1: Longitudinal compr.: sx,sd [MPa]
        :type sigma_x1: float
        :param sigma_x2: Longitudinal compr.: sx2,sd [MPa]
        :type sigma_x2: float
        :param sigma_y1: Transverse compress.: sy,sd [MPa]
        :type sigma_y1: float
        :param sigma_y2: Transverse compress.: sy2,sd [MPa]
        :type sigma_y2: float
        :param tau_xy: Shear Stress: txy [MPa]
        :type tau_xy: float
        :return:
        :rtype:
        '''
        self._FlatStructure.Plate.tau_xy = tau_xy
        self._FlatStructure.Plate.sigma_x1 = sigma_x1
        self._FlatStructure.Plate.sigma_x2 = sigma_x2
        self._FlatStructure.Plate.sigma_y1 = sigma_y1
        self._FlatStructure.Plate.sigma_y2 = sigma_y2
        for sub_cls in [self._FlatStructure.Stiffener, self._FlatStructure.Girder]:
            if sub_cls is not None:
                sub_cls.tau_xy = tau_xy
                sub_cls.sigma_x1 = sigma_x1
                sub_cls.sigma_x2 = sigma_x2
                sub_cls.sigma_y1 = sigma_y1
                sub_cls.sigma_y2 = sigma_y2
        self._FlatStructure.lat_press = pressure

    def set_stiffener(self, hw: float = 260, tw: float = 12, bf: float = 49,
                      tf: float = 27.3, stf_type: str = 'bulb', spacing: float = 608):
        '''
        Sets the stiffener properties.

        :param hw: stiffer web height, mm
        :type hw: float
        :param tw: stiffener web thickness, mm
        :type tw: float
        :param bf: stiffener flange width, mm
        :type bf: float
        :param tf: stiffener flange thickness, mm
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: spacing between stiffeners
        :type spacing: float
        :return:
        :rtype:
        '''
        self._FlatStructure.Stiffener.hw = hw
        self._FlatStructure.Stiffener.tw = tw
        self._FlatStructure.Stiffener.b = bf
        self._FlatStructure.Stiffener.tf = tf
        self._FlatStructure.Stiffener.stiffener_type = api_helpers.normalize_bulb_stiffener_type(stf_type)
        self._FlatStructure.Stiffener.spacing = spacing
        self._FlatStructure.Stiffener.girder_lg = 10
        self._FlatStructure.Stiffener.t = self._FlatStructure.Plate.t
        self._FlatStructure.Stiffener.span = self._FlatStructure.Plate.span
        self._FlatStructure.Stiffener.mat_yield = self._FlatStructure.Plate.mat_yield
        self._FlatStructure.Stiffener.E = self._FlatStructure.Plate.E
        self._FlatStructure.Stiffener.v = self._FlatStructure.Plate.v
        self._FlatStructure.Stiffener.mat_factor = self._FlatStructure.Plate.mat_factor
        self._FlatStructure.Stiffener.tau_xy = self._FlatStructure.Plate.tau_xy
        self._FlatStructure.Stiffener.sigma_x1 = self._FlatStructure.Plate.sigma_x1
        self._FlatStructure.Stiffener.sigma_x2 = self._FlatStructure.Plate.sigma_x2
        self._FlatStructure.Stiffener.sigma_y1 = self._FlatStructure.Plate.sigma_y1
        self._FlatStructure.Stiffener.sigma_y2 = self._FlatStructure.Plate.sigma_y2


    def set_girder(self, hw: float = 500, tw: float = 15, bf: float = 200,
                                   tf: float = 25, stf_type: str = 'T', spacing: float = 700):
        '''
        Sets the girder properties.

        :param hw: stiffer web height, mm
        :type hw: float
        :param tw: girder web thickness, mm
        :type tw: float
        :param bf: girder flange width, mm
        :type bf: float
        :param tf: girder flange thickness, mm
        :type tf: float
        :param stf_type: girder type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: spacing between girders
        :type spacing: float
        :return:
        :rtype:
        '''
        self._FlatStructure.Girder.hw = hw
        self._FlatStructure.Girder.tw = tw
        self._FlatStructure.Girder.b = bf
        self._FlatStructure.Girder.tf = tf
        self._FlatStructure.Girder.stiffener_type = api_helpers.normalize_bulb_stiffener_type(stf_type)
        self._FlatStructure.Girder.spacing = spacing
        self._FlatStructure.Girder.girder_lg = 10
        self._FlatStructure.Girder.t = self._FlatStructure.Plate.t
        self._FlatStructure.Girder.span = self._FlatStructure.Plate.span
        self._FlatStructure.Girder.mat_yield = self._FlatStructure.Plate.mat_yield
        self._FlatStructure.Girder.E = self._FlatStructure.Plate.E
        self._FlatStructure.Girder.v = self._FlatStructure.Plate.v
        self._FlatStructure.Girder.mat_factor = self._FlatStructure.Plate.mat_factor
        self._FlatStructure.Girder.tau_xy = self._FlatStructure.Plate.tau_xy
        self._FlatStructure.Girder.sigma_x1 = self._FlatStructure.Plate.sigma_x1
        self._FlatStructure.Girder.sigma_x2 = self._FlatStructure.Plate.sigma_x2
        self._FlatStructure.Girder.sigma_y1 = self._FlatStructure.Plate.sigma_y1
        self._FlatStructure.Girder.sigma_y2 = self._FlatStructure.Plate.sigma_y2

    def set_puls_parameters(self, sp_or_up: str = None, puls_boundary: str = "Int",
                            stiffener_end: str = "Continuous", up_boundary: str = "SSSS"):
        """
        Set the PULS-style panel metadata used by SemiAnalytical and ML-Numeric buckling methods.
        """
        if sp_or_up is None:
            sp_or_up = self._default_puls_panel_type()
        sp_or_up = str(sp_or_up).strip().upper()
        api_helpers.assert_choice(sp_or_up, api_helpers.PULS_PANEL_TYPES, 'sp_or_up')
        api_helpers.assert_choice(puls_boundary, api_helpers.PULS_BOUNDARY_TYPES, 'puls_boundary')

        puls_boundary = api_helpers.normalize_puls_boundary(puls_boundary)
        stiffener_end = api_helpers.normalize_puls_stiffener_end(stiffener_end)
        api_helpers.assert_choice(stiffener_end, api_helpers.SUPPORT_TYPES, 'stiffener_end')

        up_boundary = str(up_boundary).strip().upper()
        assert len(up_boundary) == 4 and set(up_boundary).issubset({"S", "C"}), \
            "up_boundary must contain four S/C support letters, for example 'SSSS' or 'SCSC'"

        self._set_puls_field("_puls_sp_or_up", sp_or_up)
        self._set_puls_field("_puls_boundary", puls_boundary)
        self._set_puls_field("_puls_stf_end", stiffener_end)
        self._set_puls_field("_puls_up_boundary", up_boundary)
        self._set_puls_field("_puls_method", self._buckling_acceptance)

    def set_buckling_parameters(self, calculation_method: str= None, buckling_acceptance: str = None,
                                stiffened_plate_effective_aginst_sigy = True,
                                min_lat_press_adj_span: float = None, buckling_length_factor_stf: float = None,
                                buckling_length_factor_girder: float = None,
                                stf_dist_between_lateral_supp: float = None,
                                girder_dist_between_lateral_supp: float = None,
                                panel_length_Lp: float = None, stiffener_support: str = 'Continuous',
                                girder_support: str = 'Continuous',
                                pressure_side: str = 'both sides',
                                load_factor_stresses: float = 1.0,
                                load_factor_pressure: float = 1.0,
                                fabrication_method_stiffener: str = 'welded',
                                fabrication_method_girder: str = 'welded',
                                ml_algo=None):
        '''
        Various buckling realted parameters are set here. For details, see\n
        DNV-RP-C201 Buckling strength of plated structures.\n

        :param calculation_method: 'DNV-RP-C201 - prescriptive', 'SemiAnalytical S3/U3',
            or 'ML-Numeric (PULS based)'
        :type calculation_method: str
        :param buckling_acceptance: selected UF family, either 'buckling' or 'ultimate'
        :type buckling_acceptance: str
        :param stiffened_plate_effective_aginst_sigy:
        :type stiffened_plate_effective_aginst_sigy:
        :param min_lat_press_adj_span: relative pressure applied on adjacent spans
        :type min_lat_press_adj_span: float
        :param buckling_length_factor_stf:  Buckling length factor: , kstiff
        :type buckling_length_factor_stf: float
        :param buckling_length_factor_girder: Buckling length factor:  kstiff
        :type buckling_length_factor_girder: float
        :param stf_dist_between_lateral_supp:  Distance between tripping brackets: lT
        :type stf_dist_between_lateral_supp: float
        :param girder_dist_between_lateral_supp: Dist.betw.lateral supp.: Ltg
        :type girder_dist_between_lateral_supp: float
        :param panel_length_Lp: Panel length (max.no stiff spans*l): Lp
        :type panel_length_Lp: float
        :param stiffener_support: continuous or sniped at ends
        :type stiffener_support: str
        :param girder_support: continuous or sniped at ends
        :type girder_support: str
        :param pressure_side: side receiving overpressure, 'plate side', 'stiffener side' or 'both sides'
        :type pressure_side: str
        :param load_factor_stresses: load factor applied to in-plane stresses
        :type load_factor_stresses: float
        :param load_factor_pressure: load factor applied to lateral pressure
        :type load_factor_pressure: float
        :param fabrication_method_stiffener: flat stiffener fabrication method, 'welded' or 'cold formed'
        :type fabrication_method_stiffener: str
        :param fabrication_method_girder: flat girder fabrication method, 'welded' or 'cold formed'
        :type fabrication_method_girder: str
        :param ml_algo: optional numeric ML model/scaler bundle for 'ML-Numeric (PULS based)'
        :type ml_algo: dict
        :return:
        :rtype:
        '''
        calculation_method = self._buckling_method if calculation_method is None else calculation_method
        buckling_acceptance = self._buckling_acceptance if buckling_acceptance is None else buckling_acceptance
        api_helpers.assert_choice(calculation_method, api_helpers.BUCKLING_CALCULATION_METHODS, 'calculation_method')
        api_helpers.assert_choice(buckling_acceptance, api_helpers.BUCKLING_ACCEPTANCE_TYPES, 'buckling_acceptance')
        api_helpers.assert_choice(stiffener_support, api_helpers.SUPPORT_TYPES, 'stiffener_support')
        api_helpers.assert_choice(girder_support, api_helpers.SUPPORT_TYPES, 'girder_support')
        api_helpers.assert_choice(pressure_side, api_helpers.FLAT_PRESSURE_SIDES, 'pressure_side')
        api_helpers.assert_choice(
            fabrication_method_stiffener,
            api_helpers.FLAT_FABRICATION_METHODS,
            'fabrication_method_stiffener',
        )
        api_helpers.assert_choice(
            fabrication_method_girder,
            api_helpers.FLAT_FABRICATION_METHODS,
            'fabrication_method_girder',
        )
        sigy_mapper = {True: 'Stf. pl. effective against sigma y', False:'All sigma y to girder'}
        self._buckling_method = calculation_method
        self._buckling_acceptance = buckling_acceptance
        if ml_algo is not None:
            self._ml_buckling_model = ml_algo
        self._FlatStructure._stiffened_plate_effective_aginst_sigy = sigy_mapper[stiffened_plate_effective_aginst_sigy]
        self._FlatStructure.method = buckling_acceptance
        self._FlatStructure._overpressure_side = pressure_side
        self._FlatStructure._stress_load_factor = load_factor_stresses
        self._FlatStructure._lat_load_factor = load_factor_pressure
        self._FlatStructure._fab_method_stiffener = api_helpers.normalize_flat_fabrication_method(
            fabrication_method_stiffener
        )
        self._FlatStructure._fab_method_girder = api_helpers.normalize_flat_fabrication_method(
            fabrication_method_girder
        )
        self._FlatStructure._min_lat_press_adj_span = min_lat_press_adj_span
        self._FlatStructure._buckling_length_factor_stf = buckling_length_factor_stf
        self._FlatStructure._buckling_length_factor_girder = buckling_length_factor_girder
        self._FlatStructure._girder_dist_between_lateral_supp = girder_dist_between_lateral_supp
        self._FlatStructure._stf_dist_between_lateral_supp= stf_dist_between_lateral_supp
        self._FlatStructure._panel_length_Lp = panel_length_Lp
        self._FlatStructure._stf_end_support = stiffener_support
        self._FlatStructure._girder_end_support = girder_support
        self._set_puls_field("_puls_method", buckling_acceptance)
        self._ensure_puls_defaults()

    def get_special_provisions_results(self):
        '''
        Special provisions for plating and stiffeners in steel structures.\n
        Return a dictionary:\n
        \n
        'Plate thickness' : The thickness of plates shall not be less than this check.\n
        'Stiffener section modulus' : The section modulus for longitudinals, beams, frames and other stiffeners\n
                                      subjected to lateral pressure shall not be less than this check.\n
        'Stiffener shear area' : The shear area of the plate/stiffener shall not be less than this ckeck.\n
        :return: minium dimensions and actual dimensions for the current structure in mm/mm^2/mm^3
        :rtype: dict
        '''
        min_pl_thk = self.Plate.get_dnv_min_thickness(design_pressure_kpa=self._FlatStructure.lat_press * 1000)
        min_sec_mod = self.Stiffeners.get_dnv_min_section_modulus(
            design_pressure_kpa=self._FlatStructure.lat_press * 1000) * 1000**3
        min_area = self.Stiffeners.get_minimum_shear_area(pressure=self._FlatStructure.lat_press * 1000) * 1000**2

        this_pl_thk = self.Plate.t
        this_secmod = self.Stiffeners.get_section_modulus()
        this_area = self.Stiffeners.get_shear_area()* 1000**2
        return {'Plate thickness':{'minimum': min_pl_thk, 'actual': this_pl_thk},
                'Stiffener section modulus': {'minimum': min_sec_mod, 'actual': min(this_secmod)* 1000**3},
                'Stiffener shear area': {'minimum': min_area, 'actual': this_area}}



class CylStru():
    ''' API class for all cylinder options.\n
     Calculation domains are:\n
    1.  'Unstiffened shell'\n
    2.  'Unstiffened panel'\n
    3.  'Longitudinal Stiffened shell'\n
    4.  'Longitudinal Stiffened panel'\n
    5.  'Ring Stiffened shell'\n
    6.  'Ring Stiffened panel'\n
    7.  'Orthogonally Stiffened shell'\n
    8.  'Orthogonally Stiffened panel'\n
    9.  'Unstiffened conical shell'\n
     '''

    geotypes = api_helpers.CYLINDER_STRUCTURE_DOMAINS
    def __init__(self, calculation_domain: str = 'Unstiffened shell'):
        '''
        :param calculation_domain:   calculation domain, 'Unstiffened shell', 'Unstiffened panel',
                                'Longitudinal Stiffened shell', 'Longitudinal Stiffened panel', 'Ring Stiffened shell',
                                'Ring Stiffened panel', 'Orthogonally Stiffened shell', 'Orthogonally Stiffened panel'
        :type calculation_domain: str
        '''
        super().__init__()
        calculation_domain = api_helpers.normalize_domain_string(calculation_domain)
        geometry = api_helpers.geometry_id_for_domain(calculation_domain)
        self._load_type = api_helpers.cylinder_input_mode(calculation_domain)

        self._calculation_domain = api_helpers.cylinder_domain_with_input_mode(calculation_domain) \
            if calculation_domain in api_helpers.CYLINDER_STRUCTURE_DOMAINS else api_helpers.domain_for_geometry_id(geometry)
        self._CylinderMain = CylinderAndCurvedPlate()
        self._CylinderMain.geometry = geometry
        self._CylinderMain.ShellObj = Shell()
        if geometry in [1, 2, 9]:
            self._CylinderMain.LongStfObj = None
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = None
        elif geometry in [3, 4]:
            self._CylinderMain.LongStfObj = Structure()
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = None
        elif geometry in [5, 6]:
            self._CylinderMain.LongStfObj = None
            self._CylinderMain.RingStfObj = Structure()
            self._CylinderMain.RingFrameObj = None
        elif geometry in [7, 8]:
            self._CylinderMain.LongStfObj = Structure()
            self._CylinderMain.RingStfObj = None
            self._CylinderMain.RingFrameObj = Structure()

    def set_stresses(self, sasd = 0, smsd = 0, tTsd = 0, tQsd = 0, psd = 0, shsd = 0):
        '''
        Cylinder stresses.
        Use negative numbers for compression pressure, stresses and forces.

        :param sasd: Design axial stress, sa,sd [MPa]
        :type sasd: float
        :param smsd: Design bending stress, sm,sd [MPa]
        :type smsd: float
        :param tTsd: Design torsional stress, tT,sd [MPa]
        :type tTsd: float
        :param tQsd: Design shear stress, tQ,sd [MPa]
        :type tQsd: float
        :param psd: Design lateral pressure, psd [MPa]
        :type psd: float
        :param shsd: Additional hoop stress, sh,sd [MPa]
        :type shsd: float
        :return:
        :rtype:
        '''

        if self._CylinderMain.geometry == 9:
            self.set_conical_stresses(sasd=sasd, smsd=smsd, tTsd=tTsd, tQsd=tQsd, psd=psd, shsd=shsd)
            return

        self._CylinderMain.sasd = api_helpers.mpa_to_pa(sasd)
        self._CylinderMain.smsd = api_helpers.mpa_to_pa(smsd)
        self._CylinderMain.tTsd = abs(api_helpers.mpa_to_pa(tTsd))
        self._CylinderMain.tQsd = abs(api_helpers.mpa_to_pa(tQsd))
        self._CylinderMain.psd = api_helpers.mpa_to_pa(psd)
        self._CylinderMain.shsd = api_helpers.mpa_to_pa(shsd)

    def set_forces(self, Nsd: float = 0, Msd: float = 0, Tsd: float = 0, Qsd: float = 0, psd: float = 0):
        '''
        Forces applied to cylinder.
        Use negative numbers for compression pressure, stresses and forces.

        :param Nsd: Design Axial force, Nsd [kN]
        :param Msd: Design bending mom., Msd [kNm]
        :param Tsd: Design torsional mom., Tsd [kNm]
        :param Qsd: Design shear force, Qsd [kN]
        :param psd: Design lateral pressure, psd [N/mm2]

        :return:
        '''
        geometry = api_helpers.geometry_id_for_domain(self._calculation_domain)
        if geometry == 9:
            self.set_conical_forces(Nsd=Nsd, M1sd=Msd, M2sd=0, Tsd=Tsd, Q1sd=Qsd, Q2sd=0, psd=psd)
            return
        forces = [Nsd, Msd, Tsd, Qsd]
        longitudinal_stiffener = self._CylinderMain.LongStfObj
        sasd, smsd, tTsd, tQsd, shsd = hlp.helper_cylinder_stress_to_force_to_stress(
            stresses=None, forces=forces, geometry=geometry, shell_t=self._CylinderMain.ShellObj.thk,
            shell_radius=self._CylinderMain.ShellObj.radius,
            shell_spacing=None if longitudinal_stiffener is None else longitudinal_stiffener.spacing / 1000,
            hw=None if longitudinal_stiffener is None else longitudinal_stiffener.hw / 1000,
            tw=None if longitudinal_stiffener is None else longitudinal_stiffener.tw / 1000,
            b=None if longitudinal_stiffener is None else longitudinal_stiffener.b / 1000,
            tf=None if longitudinal_stiffener is None else longitudinal_stiffener.tf / 1000,
            CylinderAndCurvedPlate=CylinderAndCurvedPlate)

        self._CylinderMain.sasd = sasd
        self._CylinderMain.smsd = smsd
        self._CylinderMain.tTsd = abs(tTsd)
        self._CylinderMain.tQsd = abs(tQsd)
        self._CylinderMain.psd = api_helpers.mpa_to_pa(psd)
        self._CylinderMain.shsd = shsd

    def set_conical_shell_geometry(self, r1: float = 0, r2: float = 0, length: float = 0, thickness: float = 0):
        '''
        Set unstiffened conical shell geometry.

        :param r1: radius at one end of cone [mm]
        :param r2: radius at the other end of cone [mm]
        :param length: axial cone length, l [mm]
        :param thickness: nominal shell thickness [mm]
        '''
        shell = self._CylinderMain.ShellObj
        shell.thk = api_helpers.mm_to_m(thickness)
        shell.set_conical_geometry(
            api_helpers.mm_to_m(r1),
            api_helpers.mm_to_m(r2),
            api_helpers.mm_to_m(length),
        )
        self._CylinderMain.panel_spacing = shell.cone_equivalent_length()

    def set_conical_forces(self, Nsd: float = 0, M1sd: float = 0, M2sd: float = 0,
                           Tsd: float = 0, Q1sd: float = 0, Q2sd: float = 0, psd: float = 0):
        '''
        Set DNV-RP-C202 Sec. 4.2 conical shell force input.

        :param Nsd: design axial force [kN]
        :param M1sd: design bending moment about principal axis 1 [kNm]
        :param M2sd: design bending moment about principal axis 2 [kNm]
        :param Tsd: design torsional moment [kNm]
        :param Q1sd: design shear force parallel to principal axis 1 [kN]
        :param Q2sd: design shear force parallel to principal axis 2 [kN]
        :param psd: design lateral pressure [N/mm2]
        '''
        shell = self._CylinderMain.ShellObj
        self._CylinderMain._cone_Nsd = Nsd
        self._CylinderMain._cone_M1sd = M1sd
        self._CylinderMain._cone_M2sd = M2sd
        self._CylinderMain._cone_Tsd = Tsd
        self._CylinderMain._cone_Q1sd = Q1sd
        self._CylinderMain._cone_Q2sd = Q2sd
        self._CylinderMain.psd = api_helpers.mpa_to_pa(psd)
        governing = self._CylinderMain.conical_stress_state(
            min(val for val in [shell.cone_r1, shell.cone_r2] if val is not None)
        )
        self._CylinderMain.sasd = governing['sasd']
        self._CylinderMain.smsd = governing['smsd']
        self._CylinderMain.tTsd = abs(governing['tTsd'])
        self._CylinderMain.tQsd = abs(governing['tQsd'])
        self._CylinderMain.shsd = governing['shsd']

    def set_conical_stresses(self, sasd: float = 0, smsd: float = 0, tTsd: float = 0,
                             tQsd: float = 0, psd: float = 0, shsd: float = 0):
        '''
        Set conical shell stress input and derive equivalent directional forces.

        Scalar bending and shear stresses are mapped to principal axis 1:
        ``M2sd = 0`` and ``Q2sd = 0``.
        '''
        shell = self._CylinderMain.ShellObj
        radius = min(val for val in [shell.cone_r1, shell.cone_r2] if val is not None)
        forces_with_shsd = hlp.helper_cylinder_stress_to_force_to_stress(
            stresses=(
                api_helpers.mpa_to_pa(sasd),
                api_helpers.mpa_to_pa(smsd),
                abs(api_helpers.mpa_to_pa(tTsd)),
                abs(api_helpers.mpa_to_pa(tQsd)),
                api_helpers.mpa_to_pa(shsd),
            ),
            geometry=self._CylinderMain.geometry,
            shell_t=shell.thk,
            shell_radius=radius,
            shell_spacing=shell.cone_equivalent_length(),
            CylinderAndCurvedPlate=CylinderAndCurvedPlate,
            conical=True,
            psd=psd,
            cone_r1=shell.cone_r1,
            cone_r2=shell.cone_r2,
            cone_alpha=shell.cone_alpha,
            shell_lenght_l=shell.cone_length,
        )
        Nsd, M1sd, M2sd, Tsd, Q1sd, Q2sd = forces_with_shsd[:6]
        self.set_conical_forces(Nsd=Nsd, M1sd=M1sd, M2sd=M2sd, Tsd=Tsd, Q1sd=Q1sd, Q2sd=Q2sd, psd=psd)
        self._CylinderMain.sasd = api_helpers.mpa_to_pa(sasd)
        self._CylinderMain.smsd = api_helpers.mpa_to_pa(smsd)
        self._CylinderMain.tTsd = abs(api_helpers.mpa_to_pa(tTsd))
        self._CylinderMain.tQsd = abs(api_helpers.mpa_to_pa(tQsd))
        self._CylinderMain.shsd = api_helpers.mpa_to_pa(shsd)

    def set_material(self, mat_yield = 355, emodule = 210000, material_factor = 1.15, poisson = 0.3):
        '''
        Set the material properties for all structure.

        :param mat_yield: material yield, fy,  given in MPa
        :type mat_yield: float
        :param emodule: elastic module, E, given in MPa
        :type emodule: float
        :param material_factor: material factor, typically 1.15 or 1.1
        :type material_factor: float
        :param poisson: poisson number of matieral
        :type poisson: float
        :return:
        :rtype:
        '''
        self._CylinderMain.mat_yield = api_helpers.mpa_to_pa(mat_yield)
        self._CylinderMain.E = api_helpers.mpa_to_pa(emodule)
        self._CylinderMain.v = poisson
        self._CylinderMain.mat_factor = material_factor
    def set_imperfection(self, delta_0 = 0.005):
        '''
        Initial out of roundness of stiffener: delta_0 * r
        Typical value is set as default.

        :param delta_0: Initial out of roundness of stiffener
        :type delta_0: float
        :return:
        :rtype:
        '''
        self._CylinderMain.delta0 = delta_0

    def set_fabrication_method(self, stiffener: str =  'Fabricated', girder: str = 'Fabricated'):
        '''
        Fabrication method for stiffener and girder. Either 'Fabricated' or 'Cold formed'

        :param stiffener: set fabrication method of stiffeners, either 'Fabricated' or 'Cold formed'
        :type stiffener: str
        :param girder: set fabrication method of girder, either 'Fabricated' or 'Cold formed'
        :type girder: str
        :return:
        :rtype:
        '''
        api_helpers.assert_choice(stiffener, api_helpers.FABRICATION_METHODS, 'stiffener fabrication method')
        api_helpers.assert_choice(girder, api_helpers.FABRICATION_METHODS, 'girder fabrication method')
        self._CylinderMain.fab_method_ring_stf = stiffener
        self._CylinderMain.fab_method_ring_girder = girder
    def set_end_cap_pressure_included_in_stress(self, is_included: bool = True):
        '''
        Cylinder may or may not have and end cap. If there is an end cap, and the stresses from pressure on this
        is not included, ste this values to True.

        :param is_included: if this is not set, stresses due to end cap pressure for clyinder is set
        :type is_included: bool
        :return:
        :rtype:
        '''
        self._CylinderMain.end_cap_pressure_included = is_included
    def set_uls_or_als(self, kind = 'ULS'):
        '''
        This is used to calculate th resulting material factor.
        ALS is Accidental Limit State
        ULS is Ultimate Limit State

        :param kind: set load condition, either 'ULS' or 'ALS'
        :type kind: str
        :return:
        :rtype:
        '''
        api_helpers.assert_choice(kind, api_helpers.LIMIT_STATE_TYPES, 'limit state')
        self._CylinderMain.uls_or_als = kind
    def set_exclude_ring_stiffener(self, is_excluded: bool = True):
        '''
        If for example orthogonally stiffened cylinder is selected and there are no ring stiffeners, set this to True.
        In this case only ring girders are included.

        :param is_excluded: set no ring stiffeners
        :type is_excluded: bool
        :return:
        :rtype:
        '''
        self._CylinderMain._ring_stiffener_excluded = is_excluded
    def set_exclude_ring_frame(self, is_excluded: bool = True):
        '''
        If for example orthogonally stiffened cylinder is selected and there are no ring girder, set this to True.
        The resulting structure will then be only longitudinal and ring stiffeners.

        :param is_excluded: set no ring girders
        :type is_excluded: bool
        :return:
        :rtype:
        '''
        self._CylinderMain._ring_frame_excluded= is_excluded

    def set_length_between_girder(self, val: float = 0):
        '''
        Distance between the girders along the cylinder.

        :param val: length/span between girders
        :type val: float
        :return:
        :rtype:
        '''
        self._CylinderMain.length_between_girders = val
    def set_panel_spacing(self, val: float = 0):
        '''
        In case a curved panel is selected, not a complete cylinder, this value sets the width of the panel.

        :param val: spacing between stiffeners
        :type val: float
        :return:
        :rtype:
        '''
        self._CylinderMain.panel_spacing = api_helpers.mm_to_m(val)

    def set_shell_geometry(self, radius: float = 0, thickness: float = 0,distance_between_rings: float = 0,
                           tot_length_of_shell: float = 0):
        '''
        Sets the baic parameters for the cylinder.

        :param radius: radius of cylinder
        :type radius: float
        :param thickness: thickness of cylinder
        :type thickness: float
        :param distance_between_rings: distance between girders
        :type distance_between_rings: float
        :param tot_length_of_shell: total length of the cylinder
        :type tot_length_of_shell: float
        :return:
        :rtype:
        '''

        self._CylinderMain.ShellObj.radius = api_helpers.mm_to_m(radius)
        self._CylinderMain.ShellObj.thk = api_helpers.mm_to_m(thickness)
        self._CylinderMain.ShellObj.dist_between_rings = api_helpers.mm_to_m(distance_between_rings)
        if tot_length_of_shell == 0:
            # Setting a default.
            self._CylinderMain.ShellObj.length_of_shell = api_helpers.mm_to_m(distance_between_rings * 10)
            self._CylinderMain.ShellObj.tot_cyl_length = api_helpers.mm_to_m(distance_between_rings * 10)
        else:
            self._CylinderMain.ShellObj.tot_cyl_length = api_helpers.mm_to_m(tot_length_of_shell)

    def set_shell_buckling_parmeters(self, eff_buckling_length_factor: float = 1.0):
        '''
        Sets the buckling length paramenter of the cylinder. Used for global column buckling calculations.

        :param eff_buckling_length_factor: effective length factor, column buckling
        :type eff_buckling_length_factor: float
        :return:
        :rtype:
        '''
        self._CylinderMain.ShellObj.k_factor = eff_buckling_length_factor

    def set_longitudinal_stiffener(self, hw: float = 260, tw: float = 12, bf: float = 49,
                                   tf: float = 28, stf_type: str = 'bulb', spacing: float = 680):
        '''
        Sets the longitudinal stiffener dimensions. May be excluded.

        :param hw: web height
        :type hw: float
        :param tw: web thickness
        :type tw: float
        :param bf: flange width
        :type bf: float
        :param tf: flange thickness
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: distance between stiffeners
        :type spacing: float

        '''
        self._CylinderMain.LongStfObj.hw = hw
        self._CylinderMain.LongStfObj.tw = tw
        self._CylinderMain.LongStfObj.b = bf
        self._CylinderMain.LongStfObj.tf = tf
        self._CylinderMain.LongStfObj.stiffener_type = api_helpers.normalize_bulb_stiffener_type(stf_type)
        self._CylinderMain.LongStfObj.spacing = spacing
        self._CylinderMain.LongStfObj.t = self._CylinderMain.ShellObj.thk

    def set_ring_stiffener(self, hw: float = 260, tw: float = 12, bf: float = 49,
                                   tf: float = 28, stf_type: str = 'bulb', spacing: float = 680):
        '''
        Sets the ring stiffener dimensions. May be excluded.

        :param hw: web height
        :type hw: float
        :param tw: web thickness
        :type tw: float
        :param bf: flange width
        :type bf: float
        :param tf: flange thickness
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: distance between stiffeners
        :type spacing: float
        :return:
        :rtype:
        '''


        self._CylinderMain.RingStfObj.hw = hw
        self._CylinderMain.RingStfObj.tw = tw
        self._CylinderMain.RingStfObj.b = bf
        self._CylinderMain.RingStfObj.tf = tf
        self._CylinderMain.RingStfObj.stiffener_type = api_helpers.normalize_bulb_stiffener_type(stf_type)
        self._CylinderMain.RingStfObj.s = spacing
        self._CylinderMain.RingStfObj.t = self._CylinderMain.ShellObj.thk

    def set_ring_girder(self, hw: float = 500, tw: float = 15, bf: float = 200,
                                   tf: float = 25, stf_type: str = 'T', spacing: float = 700):
        '''
        Sets the ring girder dimensions. May be excluded.

        :param hw: web height
        :type hw: float
        :param tw: web thickness
        :type tw: float
        :param bf: flange width
        :type bf: float
        :param tf: flange thickness
        :type tf: float
        :param stf_type: stiffener type, either T, FB, L or L-bulb
        :type stf_type: str
        :param spacing: distance between stiffeners
        :type spacing: float
        :return:
        :rtype:
        '''

        self._CylinderMain.RingFrameObj.hw = hw
        self._CylinderMain.RingFrameObj.tw = tw
        self._CylinderMain.RingFrameObj.b = bf
        self._CylinderMain.RingFrameObj.tf = tf
        self._CylinderMain.RingFrameObj.stiffener_type = api_helpers.normalize_bulb_stiffener_type(stf_type)
        self._CylinderMain.RingFrameObj.s = spacing
        self._CylinderMain.RingFrameObj.t = self._CylinderMain.ShellObj.thk


    def get_buckling_results(self):
        '''
        Return a dict including all buckling results
        :return:
        :rtype:
        '''
        return self._CylinderMain.get_utilization_factors()

if __name__ == '__main__':

    my_cyl = CylStru(calculation_domain='Orthogonally Stiffened shell')
    my_cyl.set_stresses(sasd=-137.557, tQsd=78.2986, shsd=-3.8934)
    my_cyl.set_material(mat_yield=355, emodule=210000, material_factor=1.15, poisson=0.3)
    my_cyl.set_imperfection()
    my_cyl.set_fabrication_method()
    my_cyl.set_end_cap_pressure_included_in_stress()
    my_cyl.set_uls_or_als()
    my_cyl.set_exclude_ring_stiffener()
    my_cyl.set_length_between_girder(val=3300)
    my_cyl.set_panel_spacing(val=680)
    my_cyl.set_shell_geometry(radius=6500,thickness=19, tot_length_of_shell=20000, distance_between_rings=3300)
    my_cyl.set_longitudinal_stiffener(hw=260-28, tw=12, bf=49, tf=28, spacing=680.367)
    my_cyl.set_ring_girder(hw=500, tw=15, bf=200, tf=25, stf_type='T', spacing=3300)
    my_cyl.set_shell_buckling_parmeters()
    for key, val in my_cyl.get_buckling_results().items():
        print(key, val)
    print(my_cyl.get_buckling_results())
    # #
    # my_flat = FlatStru("Flat plate, stiffened with girder")
    # my_flat.set_material(mat_yield=355, emodule=210000, material_factor=1.15, poisson=0.3)
    # my_flat.set_plate_geometry()
    # my_flat.set_stresses(sigma_x1=50, sigma_x2=50, sigma_y1=150, sigma_y2=150, pressure=0.3)
    # my_flat.set_stiffener()
    # my_flat.set_girder()
    # my_flat.set_fixation_parameters()
    my_flat.set_buckling_parameters(calculation_method='DNV-RP-C201 - prescriptive', buckling_acceptance='buckling',
                                    stiffened_plate_effective_aginst_sigy=True)
    # for key, val in my_flat.get_buckling_results().items():
    #     print(key, val)
    #
    # print(my_flat.get_special_provisions_results())






