"""Basic Qt widgets that demonstrate initialisation of ANYstructure objects.

The long term goal is to replace the legacy Tk based user interface with a
feature complete Qt application.  As a first iteration we keep the user
interface intentionally small: a single window capable of building the same
``CalcScantlings`` object that ``anystruct/testCalc.py`` utilises for smoke
tests.  Showing the intermediate results in a text widget confirms that the
calculation back-end can be driven from the Qt layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .calc_structure_classes import (
    BucklingInput,
    CalcScantlings,
    Material,
    Plate,
    Puls,
    Stress,
    StiffenedPanel,
    StiffenedPanelCalcProps,
    Stiffener,
)


@dataclass(frozen=True)
class DemoInput:
    """Container for the numerical values used when instantiating the model."""

    mat_yield: float = 355e6
    mat_factor: float = 1.15
    span: float = 3.7
    spacing: float = 0.75
    plate_thk: float = 0.018
    stf_web_height: float = 0.4
    stf_web_thk: float = 0.012
    stf_flange_width: float = 0.25
    stf_flange_thk: float = 0.014
    structure_type: str = "BOTTOM"
    plate_kpp: float = 1
    stf_kps: float = 1
    stf_km1: float = 12
    stf_km2: float = 24
    stf_km3: float = 12
    sigma_y1: float = 100
    sigma_y2: float = 100
    sigma_x2: float = 102.7
    sigma_x1: float = 102.7
    tau_xy: float = 5
    stf_type: str = "T"
    zstar_optimization: bool = True
    puls_buckling_method: int = 1
    puls_boundary: str = "Int"
    puls_stiffener_end: str = "C"
    puls_sp_or_up: str = "SP"
    puls_up_boundary: str = "SSSS"
    panel_or_shell: str = "panel"
    pressure_side: str = "both sides"
    girder_lg: float = 5.0


STRUCTURE_TYPES: Dict[str, list[str]] = {
    "vertical": ["BBS", "SIDE_SHELL", "SSS"],
    "horizontal": ["BOTTOM", "BBT", "HOPPER", "MD"],
    "non-wt": ["FRAME", "GENERAL_INTERNAL_NONWT"],
    "internals": [
        "INNER_SIDE",
        "FRAME_WT",
        "GENERAL_INTERNAL_WT",
        "INTERNAL_ZERO_STRESS_WT",
        "INTERNAL_LOW_STRESS_WT",
    ],
}


def build_demo_calc_scantlings(input_data: DemoInput | None = None) -> CalcScantlings:
    """Create the ``CalcScantlings`` instance used by the demo window."""

    data = input_data or DemoInput()

    material = Material(
        young=206_800e6,
        poisson=0.3,
        strength=data.mat_yield,
        mat_factor=data.mat_factor,
    )
    plate = Plate(
        spacing=data.spacing,
        span=data.span,
        thickness=data.plate_thk,
        material=material,
    )
    stiffener = Stiffener(
        type=data.stf_type,
        web_height=data.stf_web_height,
        web_th=data.stf_web_thk,
        flange_width=data.stf_flange_width,
        flange_th=data.stf_flange_thk,
        material=material,
        fabrication_method="welded",
    )

    calc_props = StiffenedPanelCalcProps(
        plate_kpp=data.plate_kpp,
        stf_kps=data.stf_kps,
        km1=data.stf_km1,
        km2=data.stf_km2,
        km3=data.stf_km3,
        structure_type=data.structure_type,
        structure_types=STRUCTURE_TYPES,
        zstar_optimization=data.zstar_optimization,
    )

    panel = StiffenedPanel(
        plate=plate,
        stiffener=stiffener,
        stiffener_end_support="continuous",
        girder_length=data.girder_lg,
    )

    stress = Stress(
        sigma_x1=data.sigma_x1,
        sigma_x2=data.sigma_x2,
        sigma_y1=data.sigma_y1,
        sigma_y2=data.sigma_y2,
        tauxy=data.tau_xy,
    )

    puls = Puls(
        puls_method=data.puls_buckling_method,
        puls_boundary=data.puls_boundary,
        puls_stf_end=data.puls_stiffener_end,
        puls_sp_or_up=data.puls_sp_or_up,
        puls_up_boundary=data.puls_up_boundary,
    )

    buckling_input = BucklingInput(
        panel=panel,
        pressure=0.0,
        pressure_side=data.pressure_side,
        stress=stress,
        calc_props=calc_props,
        puls_input=puls,
    )

    return CalcScantlings(
        buckling_input=buckling_input,
        lat_press=False,
        category=data.panel_or_shell,
        need_recalc=False,
    )


class DemoWindow(QMainWindow):
    """Minimal Qt window that showcases a calculation run."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ANYstructure – Qt demo")
        self.resize(760, 480)

        self._info_label = QLabel(
            "The demo instantiates the CalcScantlings object used in testCalc\n"
            "and prints a short summary alongside the report string."
        )
        self._info_label.setWordWrap(True)

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setFontFamily("monospace")

        self._recalc_btn = QPushButton("Recalculate demo input")
        self._recalc_btn.clicked.connect(self.update_results)  # type: ignore[arg-type]

        layout = QVBoxLayout()
        layout.addWidget(self._info_label)
        layout.addWidget(self._recalc_btn, alignment=Qt.AlignLeft)
        layout.addWidget(self._results)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.update_results()

    def update_results(self) -> None:
        """Rebuild the model and show the resulting text."""

        try:
            scantlings = build_demo_calc_scantlings()
            report = scantlings.get_results_for_report()
            summary = str(scantlings.buckling_input)
        except Exception as exc:  # pragma: no cover - UI diagnostic message
            self._results.setPlainText(f"Failed to evaluate demo input:\n{exc}")
            return

        output = (
            "=== Buckling input summary ===\n"
            f"{summary}\n\n"
            "=== Report string ===\n"
            f"{report}\n"
        )
        self._results.setPlainText(output)
