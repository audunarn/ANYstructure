"""Basic Qt widgets that demonstrate initialisation of ANYstructure objects.

The long term goal is to replace the legacy Tk based user interface with a
feature complete Qt application.  As a first iteration we keep the user
interface intentionally small: a single window capable of building the same
``CalcScantlings`` object that ``anystruct/testCalc.py`` utilises for smoke
tests.  Showing the intermediate results in a text widget confirms that the
calculation back-end can be driven from the Qt layer.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PySide6.QtCore import QByteArray, QDataStream, QMimeData, QPointF, QSize, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from shapely.geometry import LineString, Point

from anystruct.calc_structure_classes import (
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

    include_flat_plate: bool = True
    include_cylinder: bool = False
    include_stiffener: bool = True
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

    if data.include_flat_plate and data.include_cylinder:
        raise ValueError("A line cannot be both a flat plate and a cylinder.")

    if not data.include_flat_plate and not data.include_cylinder:
        raise ValueError("Select either flat plate or cylinder properties for the line.")

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
    stiffener = None
    if data.include_stiffener:
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
        stiffener_end_support="continuous" if stiffener else None,
        girder_length=data.girder_lg if stiffener else None,
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

    category = data.panel_or_shell
    if data.include_cylinder:
        category = "shell"
    elif data.include_flat_plate:
        category = "panel"

    return CalcScantlings(
        buckling_input=buckling_input,
        lat_press=False,
        category=category,
        need_recalc=False,
    )


class GeometryCanvas(QWidget):
    """Simple canvas that renders the modelling geometries."""

    line_selected = Signal(str)
    point_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._points: Dict[str, Point] = {}
        self._lines: Dict[str, ModelLine] = {}
        self._selected_point_name: str | None = None
        self._selected_line_name: str | None = None
        self._transform_data: tuple[Tuple[float, float, float, float], float, float, float] | None = None

    def set_geometries(
        self, points: Dict[str, Point], lines: Dict[str, ModelLine]
    ) -> None:
        self._points = dict(points)
        self._lines = dict(lines)
        if self._selected_point_name not in self._points:
            self._selected_point_name = None
        if self._selected_line_name not in self._lines:
            self._selected_line_name = None
        self.update()

    def set_selected_point(self, name: str | None) -> None:
        self._selected_point_name = name if name in self._points else None
        self.update()

    def set_selected_line(self, name: str | None) -> None:
        self._selected_line_name = name if name in self._lines else None
        self.update()

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(320, 240)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(480, 360)

    def _bounding_box(self) -> Tuple[float, float, float, float] | None:
        xs: List[float] = []
        ys: List[float] = []

        for point in self._points.values():
            xs.append(point.x)
            ys.append(point.y)

        for line in self._lines.values():
            line_xs, line_ys = line.geometry.xy
            xs.extend(line_xs)
            ys.extend(line_ys)

        if not xs or not ys:
            return None

        return min(xs), min(ys), max(xs), max(ys)

    def _compute_transform(
        self, bounds: Tuple[float, float, float, float]
    ) -> tuple[float, float, float]:
        min_x, min_y, max_x, max_y = bounds
        width = max_x - min_x or 1.0
        height = max_y - min_y or 1.0

        canvas_width = max(self.width() - 20, 1)
        canvas_height = max(self.height() - 20, 1)
        scale = min(canvas_width / width, canvas_height / height)

        offset_x = (self.width() - width * scale) / 2.0
        offset_y = (self.height() - height * scale) / 2.0

        return scale, offset_x, offset_y

    def _transform_point(self, x: float, y: float) -> QPointF:
        if self._transform_data is None:
            return QPointF()

        bounds, scale, offset_x, offset_y = self._transform_data
        min_x, min_y, _, _ = bounds

        mapped_x = offset_x + (x - min_x) * scale
        mapped_y = self.height() - (offset_y + (y - min_y) * scale)
        return QPointF(mapped_x, mapped_y)

    def _map_to_world(self, pos: QPointF) -> Tuple[float, float] | None:
        if self._transform_data is None:
            return None

        bounds, scale, offset_x, offset_y = self._transform_data
        if scale == 0:
            return None

        min_x, min_y, _, _ = bounds
        world_x = (pos.x() - offset_x) / scale + min_x
        world_y = ((self.height() - pos.y()) - offset_y) / scale + min_y
        return world_x, world_y

    def paintEvent(self, event) -> None:  # type: ignore[override]
        from PySide6.QtGui import QBrush, QColor, QPainter, QPen

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))
        painter.setRenderHint(QPainter.Antialiasing)

        bounds = self._bounding_box()
        if bounds is None:
            painter.setPen(QPen(QColor("#888")))
            painter.drawText(self.rect(), Qt.AlignCenter, "No geometry defined")
            self._transform_data = None
            return

        scale, offset_x, offset_y = self._compute_transform(bounds)
        self._transform_data = (bounds, scale, offset_x, offset_y)

        # Draw lines first
        for name, line in self._lines.items():
            width = 4 if name == self._selected_line_name else 2
            line_pen = QPen(QColor("#4cc9f0"), width)
            painter.setPen(line_pen)
            xs, ys = line.geometry.xy
            points = [self._transform_point(x, y) for x, y in zip(xs, ys)]
            for start, end in zip(points[:-1], points[1:]):
                painter.drawLine(start, end)

        # Draw points on top
        point_brush = QBrush(QColor("#f72585"))
        painter.setBrush(point_brush)
        painter.setPen(QPen(QColor("#000")))
        for name, point in self._points.items():
            radius = 8 if name == self._selected_point_name else 5
            mapped_point = self._transform_point(point.x, point.y)
            painter.drawEllipse(mapped_point, radius, radius)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._transform_data is None:
            return

        world_point = self._map_to_world(event.position())
        if world_point is None:
            return

        click_point = Point(world_point)
        _, scale, _, _ = self._transform_data
        pixel_tolerance = 8.0
        world_tolerance = pixel_tolerance / scale if scale else float("inf")

        if event.button() == Qt.LeftButton:
            selected_name: str | None = None
            min_distance = world_tolerance
            for name, line in self._lines.items():
                distance = line.geometry.distance(click_point)
                if distance <= min_distance:
                    min_distance = distance
                    selected_name = name

            if selected_name:
                self._selected_line_name = selected_name
                self.line_selected.emit(selected_name)
                self.update()
        elif event.button() == Qt.RightButton:
            selected_point: str | None = None
            min_distance = world_tolerance
            for name, point in self._points.items():
                distance = point.distance(click_point)
                if distance <= min_distance:
                    min_distance = distance
                    selected_point = name

            if selected_point:
                self._selected_point_name = selected_point
                self.point_selected.emit(selected_point)
                self.update()

        super().mousePressEvent(event)


class WidgetWorkspace(QWidget):
    """Droppable area that activates widgets dragged from the palette."""

    widgetDropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(12)

        self._selected_line_label = QLabel("Selected line: None")
        self._selected_line_label.setObjectName("selectedLineLabel")
        self._layout.addWidget(self._selected_line_label)

        self._assigned_widget_label = QLabel("Assigned widget: None")
        self._assigned_widget_label.setObjectName("assignedWidgetLabel")
        self._layout.addWidget(self._assigned_widget_label)

        self._drop_zone = QLabel("Drag a widget from the palette onto this area.")
        self._drop_zone.setAlignment(Qt.AlignCenter)
        self._drop_zone.setStyleSheet(
            "border: 2px dashed #5a5a5a; border-radius: 6px; color: #cccccc; padding: 40px;"
        )
        self._drop_zone.setObjectName("lineDropZone")
        self._layout.addWidget(self._drop_zone, stretch=1)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if self._extract_widget_name(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:  # type: ignore[override]
        if self._extract_widget_name(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        widget_name = self._extract_widget_name(event.mimeData())
        if widget_name:
            self.widgetDropped.emit(widget_name)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def set_selected_line(self, line_name: str | None) -> None:
        label = line_name if line_name else "None"
        self._selected_line_label.setText(f"Selected line: {label}")

    def set_assigned_widget_name(self, widget_name: str | None) -> None:
        label = widget_name if widget_name else "None"
        self._assigned_widget_label.setText(f"Assigned widget: {label}")

    def clear_assignment(self) -> None:
        self.set_assigned_widget_name(None)

    def _extract_widget_name(self, mime_data: QMimeData) -> str | None:
        text = mime_data.text().strip() if mime_data.hasText() else ""
        if text:
            return text.splitlines()[0]

        mime_format = "application/x-qabstractitemmodeldatalist"
        if not mime_data.hasFormat(mime_format):
            return None

        raw_data = mime_data.data(mime_format)
        if not isinstance(raw_data, QByteArray):
            raw_data = QByteArray(raw_data)

        stream = QDataStream(raw_data)
        while not stream.atEnd():
            _row = stream.readInt32()
            _column = stream.readInt32()
            map_items = stream.readInt32()
            for _ in range(map_items):
                role = stream.readInt32()
                value = stream.readQVariant()
                if role == Qt.DisplayRole and isinstance(value, str):
                    return value
        return None

@dataclass
class ModelLine:
    """Representation of a line connecting two points with structural data."""

    name: str
    start_point: str
    end_point: str
    geometry: LineString
    properties: DemoInput


class DemoWindow(QMainWindow):
    """Minimal Qt window that showcases a calculation run."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ANYstructure – Qt demo")
        self.resize(1080, 720)
        self.setDockOptions(
            QMainWindow.AnimatedDocks
            | QMainWindow.AllowTabbedDocks
            | QMainWindow.AllowNestedDocks
        )

        self._input_widgets: Dict[str, QWidget] = {}
        self._dock_registry: Dict[str, QDockWidget] = {}
        self._overview_list: QListWidget | None = None
        self._flat_plate_checkbox: QCheckBox | None = None
        self._cylinder_checkbox: QCheckBox | None = None
        self._stiffener_checkbox: QCheckBox | None = None
        self._stiffener_field_widgets: list[QWidget] = []
        self._updating_overview: bool = False
        self._section_definitions: Dict[str, list[str]] = {
            "Flat Plate Input": ["include_flat_plate", "span", "spacing", "plate_thk"],
            "Stiffener Input": [
                "include_stiffener",
                "stf_type",
                "stf_web_height",
                "stf_web_thk",
                "stf_flange_width",
                "stf_flange_thk",
                "girder_lg",
            ],
            "Material Input": ["mat_yield", "mat_factor"],
            "Buckling Parameters Input": [
                "plate_kpp",
                "stf_kps",
                "stf_km1",
                "stf_km2",
                "stf_km3",
                "structure_type",
                "zstar_optimization",
                "puls_buckling_method",
                "puls_boundary",
                "puls_stiffener_end",
                "puls_sp_or_up",
                "puls_up_boundary",
                "sigma_y1",
                "sigma_y2",
                "sigma_x2",
                "sigma_x1",
                "tau_xy",
                "pressure_side",
            ],
            "Cylinder Input": ["include_cylinder", "panel_or_shell"],
        }
        self._section_widgets: Dict[str, QWidget] = {}
        self._section_docks: Dict[str, QDockWidget] = {}
        self._line_widget_assignments: Dict[str, str] = {}
        self._dock_palette_entries: Dict[str, str] = {
            "Drop Zone": "Line Properties",
            "Drawing Canvas": "Drawing Canvas",
            "Results": "Results",
        }
        self._widget_palette: QListWidget | None = None
        self._widget_workspace: WidgetWorkspace | None = None

        self._info_label = QLabel(
            "The demo instantiates the CalcScantlings object used in testCalc\n"
            "and prints a short summary alongside the report string."
        )
        self._default_info_text = self._info_label.text()
        self._info_label.setWordWrap(True)

        self._results = QTextEdit()
        self._results.setReadOnly(True)
        self._results.setFontFamily("monospace")

        self._canvas = GeometryCanvas()
        self._point_name_counter = 1
        self._points: Dict[str, Point] = {}
        self._lines: Dict[str, ModelLine] = {}
        self._latest_properties = DemoInput()
        self._selected_point_name: str | None = None
        self._selected_line_name: str | None = None
        self._next_line_combo_target = "start"
        self._last_loaded_file: Path | None = None

        self._initialise_section_widgets()
        self._initialise_default_geometry()

        self._recalc_btn = QPushButton("Recalculate Demo Input")
        self._recalc_btn.clicked.connect(self._handle_manual_recalc)  # type: ignore[arg-type]
        self._load_input_btn = QPushButton("Load Input From File…")
        self._load_input_btn.clicked.connect(self._handle_load_input)  # type: ignore[arg-type]
        self._load_status_label = QLabel(
            "Load inputs from a JSON file or recalculate the current configuration."
        )
        self._load_status_label.setWordWrap(True)

        self._canvas.line_selected.connect(self._handle_canvas_line_selected)  # type: ignore[arg-type]
        self._canvas.point_selected.connect(self._handle_canvas_point_selected)  # type: ignore[arg-type]

        central_placeholder = QWidget()
        self.setCentralWidget(central_placeholder)

        palette_widget = self._build_widget_palette()
        overview_widget = self._build_overview_widget()
        properties_widget = self._build_properties_widget()
        model_widget = self._build_model_widget()
        results_widget = self._build_results_widget()
        load_widget = self._build_load_widget()

        palette_dock = self._create_dock("Widget Palette", palette_widget)
        overview_dock = self._create_dock("Widget Overview", overview_widget)
        properties_dock = self._create_dock("Line Properties", properties_widget)
        model_dock = self._create_dock("Drawing Canvas", model_widget)
        results_dock = self._create_dock("Results", results_widget)
        load_dock = self._create_dock("Load Input", load_widget)

        self.addDockWidget(Qt.LeftDockWidgetArea, palette_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, overview_dock)
        self.addDockWidget(Qt.LeftDockWidgetArea, properties_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, model_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, results_dock)
        self.addDockWidget(Qt.TopDockWidgetArea, load_dock)
        self.splitDockWidget(model_dock, results_dock, Qt.Vertical)
        self.resizeDocks(
            [palette_dock, overview_dock, properties_dock, model_dock],
            [180, 200, 260, 780],
            Qt.Horizontal,
        )

        for title, dock in (
            ("Widget Palette", palette_dock),
            ("Widget Overview", overview_dock),
            ("Line Properties", properties_dock),
            ("Drawing Canvas", model_dock),
            ("Results", results_dock),
            ("Load Input", load_dock),
        ):
            self._register_dock_for_overview(title, dock)

        self.update_results()

    def _create_dock(self, title: str, widget: QWidget) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setObjectName(title.replace(" ", "_"))
        dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        dock.setAllowedAreas(
            Qt.LeftDockWidgetArea
            | Qt.RightDockWidgetArea
            | Qt.TopDockWidgetArea
            | Qt.BottomDockWidgetArea
        )
        return dock

    def _register_dock_for_overview(self, title: str, dock: QDockWidget) -> None:
        self._dock_registry[title] = dock

        if self._overview_list is not None:
            self._updating_overview = True
            try:
                matches = self._overview_list.findItems(title, Qt.MatchExactly)
                if not matches:
                    item = QListWidgetItem(title)
                    item.setFlags(
                        item.flags()
                        | Qt.ItemIsUserCheckable
                        | Qt.ItemIsSelectable
                        | Qt.ItemIsEnabled
                    )
                    item.setCheckState(Qt.Checked if dock.isVisible() else Qt.Unchecked)
                    self._overview_list.addItem(item)
                else:
                    self._update_overview_item_state(title, dock.isVisible())
            finally:
                self._updating_overview = False

        dock.visibilityChanged.connect(  # type: ignore[arg-type]
            lambda visible, name=title: self._update_overview_item_state(name, visible)
        )

    def _update_overview_item_state(self, title: str, visible: bool) -> None:
        if self._overview_list is None:
            return

        self._updating_overview = True
        try:
            for item in self._overview_list.findItems(title, Qt.MatchExactly):
                item.setCheckState(Qt.Checked if visible else Qt.Unchecked)
        finally:
            self._updating_overview = False

    def _handle_overview_item_changed(self, item: QListWidgetItem) -> None:
        if self._updating_overview:
            return

        dock = self._dock_registry.get(item.text())
        if dock is None:
            return

        should_show = item.checkState() == Qt.Checked
        dock.setVisible(should_show)
        if should_show:
            dock.raise_()

    def _handle_overview_item_activated(self, item: QListWidgetItem) -> None:
        dock = self._dock_registry.get(item.text())
        if dock is None:
            return

        if not dock.isVisible():
            dock.show()
        dock.raise_()

    def _build_overview_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        overview_label = QLabel("Available Widgets")
        overview_label.setWordWrap(True)
        layout.addWidget(overview_label)

        self._overview_list = QListWidget()
        self._overview_list.itemActivated.connect(self._handle_overview_item_activated)  # type: ignore[arg-type]
        self._overview_list.itemClicked.connect(self._handle_overview_item_activated)  # type: ignore[arg-type]
        self._overview_list.itemChanged.connect(self._handle_overview_item_changed)  # type: ignore[arg-type]
        layout.addWidget(self._overview_list)
        layout.addStretch(1)
        return widget

    def _build_properties_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._info_label)
        self._widget_workspace = WidgetWorkspace()
        self._widget_workspace.widgetDropped.connect(self._handle_workspace_drop)  # type: ignore[arg-type]
        self._widget_workspace.set_selected_line(self._selected_line_name)
        layout.addWidget(self._widget_workspace, stretch=1)
        return widget

    def _build_widget_palette(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("Available Widgets"))

        palette = QListWidget()
        palette.setDragEnabled(True)
        palette.setSelectionMode(QListWidget.SingleSelection)
        palette.setDefaultDropAction(Qt.CopyAction)

        for name in self._section_definitions:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            palette.addItem(item)

        for name in self._dock_palette_entries:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            palette.addItem(item)

        palette.itemDoubleClicked.connect(  # type: ignore[arg-type]
            lambda item: self._handle_widget_palette_activation(item.text())
        )

        self._widget_palette = palette
        layout.addWidget(palette)
        layout.addStretch(1)
        return widget

    def _build_model_widget(self) -> QWidget:
        """Build the canvas and modelling controls."""

        from PySide6.QtWidgets import QGroupBox

        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        canvas_group = QGroupBox("Drawing Canvas")
        canvas_layout = QVBoxLayout()
        canvas_layout.addWidget(self._canvas)
        canvas_group.setLayout(canvas_layout)

        controls_group = QGroupBox("Geometry Input")
        controls_layout = QVBoxLayout()
        controls_layout.addLayout(self._build_point_controls())
        controls_layout.addLayout(self._build_line_controls())
        controls_group.setLayout(controls_layout)

        main_layout = QHBoxLayout()
        main_layout.addWidget(controls_group, stretch=1)
        main_layout.addWidget(canvas_group, stretch=2)

        outer_layout.addLayout(main_layout)
        return widget

    def _build_results_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._results)
        return widget

    def _build_load_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        button_row = QHBoxLayout()
        button_row.addWidget(self._load_input_btn)
        button_row.addWidget(self._recalc_btn)
        button_row.addStretch(1)
        layout.addLayout(button_row)
        layout.addWidget(self._load_status_label)
        return widget

    def _build_point_controls(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Add Point"))

        coord_layout = QHBoxLayout()
        self._point_x_input = QLineEdit()
        self._point_x_input.setPlaceholderText("X coordinate")
        self._point_y_input = QLineEdit()
        self._point_y_input.setPlaceholderText("Y coordinate")
        coord_layout.addWidget(self._point_x_input)
        coord_layout.addWidget(self._point_y_input)
        layout.addLayout(coord_layout)

        self._add_point_btn = QPushButton("Add Point")
        self._add_point_btn.clicked.connect(self._handle_add_point)  # type: ignore[arg-type]
        layout.addWidget(self._add_point_btn)

        self._point_list = QListWidget()
        layout.addWidget(self._point_list)

        return layout

    def _build_line_controls(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Add Line"))

        selector_layout = QHBoxLayout()
        self._line_start_combo = QComboBox()
        self._line_end_combo = QComboBox()
        selector_layout.addWidget(self._line_start_combo)
        selector_layout.addWidget(self._line_end_combo)
        layout.addLayout(selector_layout)

        self._add_line_btn = QPushButton("Add Line With Current Properties")
        self._add_line_btn.clicked.connect(self._handle_add_line)  # type: ignore[arg-type]
        layout.addWidget(self._add_line_btn)

        self._line_list = QListWidget()
        layout.addWidget(self._line_list)

        return layout

    def _update_geometry_display(self) -> None:
        self._canvas.set_geometries(self._points, self._lines)
        for line_name in list(self._line_widget_assignments):
            if line_name not in self._lines:
                self._line_widget_assignments.pop(line_name, None)
        self._point_list.clear()
        for name, point in self._points.items():
            self._point_list.addItem(f"{name}: ({point.x:.2f}, {point.y:.2f})")

        self._select_point_in_list(self._selected_point_name)

        self._line_list.clear()
        for name, line in self._lines.items():
            start_coords = self._points.get(line.start_point)
            end_coords = self._points.get(line.end_point)
            if start_coords and end_coords:
                self._line_list.addItem(
                    f"{name}: {line.start_point} ({start_coords.x:.2f}, {start_coords.y:.2f}) -> "
                    f"{line.end_point} ({end_coords.x:.2f}, {end_coords.y:.2f}) | type={line.properties.structure_type}"
                )
            else:
                self._line_list.addItem(
                    f"{name}: {line.start_point} -> {line.end_point} | type={line.properties.structure_type}"
                )

        self._select_line_in_list(self._selected_line_name)

        current_start = self._line_start_combo.currentText()
        current_end = self._line_end_combo.currentText()
        self._line_start_combo.clear()
        self._line_end_combo.clear()
        for name in self._points:
            self._line_start_combo.addItem(name)
            self._line_end_combo.addItem(name)

        if self._selected_line_name:
            line = self._lines.get(self._selected_line_name)
            if line:
                self._set_combo_to_point(self._line_start_combo, line.start_point)
                self._set_combo_to_point(self._line_end_combo, line.end_point)
        else:
            self._set_combo_to_point(self._line_start_combo, current_start)
            self._set_combo_to_point(self._line_end_combo, current_end)

        if self._widget_workspace is not None:
            self._widget_workspace.set_selected_line(self._selected_line_name)
            assigned_widget = None
            if self._selected_line_name:
                candidate = self._line_widget_assignments.get(self._selected_line_name)
                if candidate in self._section_widgets:
                    assigned_widget = candidate

            if assigned_widget:
                self._widget_workspace.set_assigned_widget_name(assigned_widget)
            else:
                self._widget_workspace.clear_assignment()

    def _set_combo_to_point(self, combo: QComboBox, point_name: str | None) -> None:
        if not point_name:
            return
        index = combo.findText(point_name)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _select_line_in_list(self, line_name: str | None) -> None:
        if not line_name:
            self._line_list.clearSelection()
            return
        for row in range(self._line_list.count()):
            item = self._line_list.item(row)
            if item.text().startswith(f"{line_name}:"):
                self._line_list.setCurrentRow(row)
                return
        self._line_list.clearSelection()

    def _select_point_in_list(self, point_name: str | None) -> None:
        if not point_name:
            self._point_list.clearSelection()
            return
        for row in range(self._point_list.count()):
            item = self._point_list.item(row)
            if item.text().startswith(f"{point_name}:"):
                self._point_list.setCurrentRow(row)
                return
        self._point_list.clearSelection()

    def _handle_widget_palette_activation(self, widget_name: str) -> None:
        self._activate_widget(widget_name)

    def _handle_workspace_drop(self, widget_name: str) -> None:
        self._assign_widget_to_selected_line(widget_name)

    def _activate_widget(self, widget_name: str) -> None:
        dock_title = self._dock_palette_entries.get(widget_name)
        if dock_title is not None:
            dock = self._dock_registry.get(dock_title)
            if dock is None:
                self._info_label.setText(f"Widget '{widget_name}' is not available.")
                return

            if dock_title == "Line Properties":
                self._ensure_drop_zone_visible()
                if self._selected_line_name:
                    self._restore_workspace_for_line(self._selected_line_name)
                else:
                    if self._widget_workspace is not None:
                        self._widget_workspace.clear_assignment()
                    self._info_label.setText(self._default_info_text)
            else:
                if not dock.isVisible():
                    dock.show()
                dock.raise_()
                self._info_label.setText(f"Restored {dock_title}.")
            return

        if widget_name not in self._section_widgets:
            self._info_label.setText(f"Widget '{widget_name}' is not available.")
            return

        if self._widget_palette is not None:
            matches = self._widget_palette.findItems(widget_name, Qt.MatchExactly)
            if matches:
                self._widget_palette.setCurrentItem(matches[0])

        self._show_section_dock(widget_name)

        if self._selected_line_name and self._line_widget_assignments.get(
            self._selected_line_name
        ) == widget_name:
            self._info_label.setText(
                f"Editing {widget_name}. Adjust the values and press 'Apply To Selected Line'."
            )
        else:
            self._info_label.setText(
                f"Opened {widget_name}. Drag it to the drop zone to assign it to a line."
            )

    def _ensure_drop_zone_visible(self) -> None:
        dock = self._dock_registry.get("Line Properties")
        if dock is None:
            return

        if not dock.isVisible():
            dock.show()
        dock.raise_()

    def _restore_workspace_for_line(self, line_name: str) -> None:
        if self._widget_workspace is None:
            return

        widget_name = self._line_widget_assignments.get(line_name)
        if not widget_name:
            self._line_widget_assignments.pop(line_name, None)
            self._widget_workspace.clear_assignment()
            self._info_label.setText(self._default_info_text)
            return

        if widget_name not in self._section_widgets:
            self._line_widget_assignments.pop(line_name, None)
            self._widget_workspace.clear_assignment()
            self._info_label.setText(self._default_info_text)
            return

        self._widget_workspace.set_assigned_widget_name(widget_name)
        if self._widget_palette is not None:
            matches = self._widget_palette.findItems(widget_name, Qt.MatchExactly)
            if matches:
                self._widget_palette.setCurrentItem(matches[0])
        self._show_section_dock(widget_name)
        self._info_label.setText(
            f"Editing {widget_name}. Adjust the values and press 'Apply To Selected Line'."
        )

    def _assign_widget_to_selected_line(self, widget_name: str) -> None:
        if widget_name not in self._section_widgets:
            self._info_label.setText(
                f"Widget '{widget_name}' cannot be assigned to a line."
            )
            return

        if not self._selected_line_name:
            self._info_label.setText("Select a line before dropping a widget.")
            return

        self._line_widget_assignments[self._selected_line_name] = widget_name
        if self._widget_workspace is not None:
            self._widget_workspace.set_assigned_widget_name(widget_name)

        if self._widget_palette is not None:
            matches = self._widget_palette.findItems(widget_name, Qt.MatchExactly)
            if matches:
                self._widget_palette.setCurrentItem(matches[0])

        self._show_section_dock(widget_name)

        self._info_label.setText(
            f"Assigned {widget_name} to {self._selected_line_name}."
        )

    def _show_section_dock(self, widget_name: str) -> None:
        dock = self._section_docks.get(widget_name)
        if dock is None:
            widget = self._section_widgets.get(widget_name)
            if widget is None:
                return
            dock = self._create_dock(widget_name, widget)
            self._section_docks[widget_name] = dock
            self.addDockWidget(Qt.RightDockWidgetArea, dock)
            self._register_dock_for_overview(widget_name, dock)

        if not dock.isVisible():
            dock.show()
        dock.raise_()

    def _initialise_section_widgets(self) -> None:
        """Create the individual widgets that can be activated from the palette."""

        from PySide6.QtWidgets import QGroupBox

        defaults = DemoInput()
        field_lookup = {field.name: field for field in fields(DemoInput)}

        self._input_widgets.clear()
        self._section_widgets.clear()
        self._flat_plate_checkbox = None
        self._cylinder_checkbox = None
        self._stiffener_checkbox = None
        self._stiffener_field_widgets = []

        for section_title, field_names in self._section_definitions.items():
            group = QGroupBox(section_title)
            group_layout = QFormLayout()
            for field_name in field_names:
                field = field_lookup[field_name]
                default_value = getattr(defaults, field_name)
                widget = self._create_input_widget(field_name, field.type, default_value)
                self._input_widgets[field_name] = widget

                if isinstance(widget, QCheckBox):
                    group_layout.addRow(widget)
                else:
                    group_layout.addRow(self._format_label(field_name), widget)

                if section_title == "Stiffener Input" and field_name != "include_stiffener":
                    self._stiffener_field_widgets.append(widget)

            apply_button = QPushButton("Apply To Selected Line")
            apply_button.clicked.connect(  # type: ignore[arg-type]
                lambda _checked=False, name=section_title: self._handle_apply_to_selected_line(name)
            )
            group_layout.addRow(apply_button)

            group.setLayout(group_layout)
            self._section_widgets[section_title] = group

        self._update_stiffener_fields_enabled()
        self._enforce_geometry_selection()

    def _initialise_default_geometry(self) -> None:
        self._points = {
            "P1": Point(0.0, 0.0),
            "P2": Point(10.0, 0.0),
            "P3": Point(0.0, 10.0),
            "P4": Point(10.0, 10.0),
        }
        self._point_name_counter = len(self._points) + 1

        properties = self._latest_properties
        self._lines.clear()
        self._line_widget_assignments.clear()

        def build_line(name: str, start: str, end: str) -> None:
            start_point = self._points[start]
            end_point = self._points[end]
            geometry = LineString([(start_point.x, start_point.y), (end_point.x, end_point.y)])
            self._lines[name] = ModelLine(
                name=name,
                start_point=start,
                end_point=end,
                geometry=geometry,
                properties=properties,
            )

        build_line("L1", "P1", "P2")
        build_line("L2", "P2", "P4")
        build_line("L3", "P4", "P3")
        build_line("L4", "P3", "P1")

    def _handle_apply_to_selected_line(self, section_name: str) -> None:
        if not self._selected_line_name:
            self._info_label.setText("Select a line before applying widget changes.")
            return

        line = self._lines.get(self._selected_line_name)
        if line is None:
            self._info_label.setText("Selected line is no longer available. Please select another line.")
            return

        updated_properties = self._gather_input_data()
        line.properties = updated_properties

        self.update_results()

        self._info_label.setText(
            f"Applied {section_name} to {self._selected_line_name}."
        )

    @staticmethod
    def _format_label(name: str) -> str:
        """Create a human readable label from a dataclass field name."""

        return name.replace("_", " ").title()

    @staticmethod
    def _set_checkbox_state(checkbox: QCheckBox | None, value: bool) -> None:
        if checkbox is None:
            return

        was_blocked = checkbox.blockSignals(True)
        checkbox.setChecked(value)
        checkbox.blockSignals(was_blocked)

    def _create_input_widget(
        self, field_name: str, field_type: type[Any], default_value: Any
    ) -> QWidget:
        """Return an appropriate widget for the given field type."""

        if field_type is bool:
            checkbox = QCheckBox(self._format_label(field_name))
            checkbox.setChecked(bool(default_value))

            if field_name == "include_flat_plate":
                self._flat_plate_checkbox = checkbox
                checkbox.stateChanged.connect(self._handle_flat_plate_toggled)  # type: ignore[arg-type]
            elif field_name == "include_cylinder":
                self._cylinder_checkbox = checkbox
                checkbox.stateChanged.connect(self._handle_cylinder_toggled)  # type: ignore[arg-type]
            elif field_name == "include_stiffener":
                self._stiffener_checkbox = checkbox
                checkbox.stateChanged.connect(self._handle_stiffener_toggled)  # type: ignore[arg-type]

            return checkbox

        line_edit = QLineEdit()
        line_edit.setText(str(default_value))
        return line_edit

    def _handle_flat_plate_toggled(self, state: int) -> None:
        checked = state == Qt.Checked
        if checked and self._cylinder_checkbox and self._cylinder_checkbox.isChecked():
            self._set_checkbox_state(self._cylinder_checkbox, False)

        self._enforce_geometry_selection("flat" if checked else "cylinder")

        self._info_label.setText(self._default_info_text)

    def _handle_cylinder_toggled(self, state: int) -> None:
        checked = state == Qt.Checked
        if checked and self._flat_plate_checkbox and self._flat_plate_checkbox.isChecked():
            self._set_checkbox_state(self._flat_plate_checkbox, False)

        self._enforce_geometry_selection("cylinder" if checked else "flat")

        self._info_label.setText(self._default_info_text)

    def _handle_stiffener_toggled(self, _state: int) -> None:
        self._update_stiffener_fields_enabled()
        self._info_label.setText(self._default_info_text)

    def _update_stiffener_fields_enabled(self) -> None:
        enabled = True
        if self._stiffener_checkbox is not None:
            enabled = self._stiffener_checkbox.isChecked()

        for widget in self._stiffener_field_widgets:
            widget.setEnabled(enabled)

    def _enforce_geometry_selection(self, preferred: str | None = None) -> None:
        flat_checked = self._flat_plate_checkbox.isChecked() if self._flat_plate_checkbox else False
        cylinder_checked = self._cylinder_checkbox.isChecked() if self._cylinder_checkbox else False

        if flat_checked and cylinder_checked:
            if preferred == "cylinder":
                self._set_checkbox_state(self._flat_plate_checkbox, False)
                flat_checked = False
            else:
                self._set_checkbox_state(self._cylinder_checkbox, False)
                cylinder_checked = False

        if not flat_checked and not cylinder_checked:
            if preferred == "cylinder" and self._cylinder_checkbox is not None:
                self._set_checkbox_state(self._cylinder_checkbox, True)
            elif self._flat_plate_checkbox is not None:
                self._set_checkbox_state(self._flat_plate_checkbox, True)
            elif self._cylinder_checkbox is not None:
                self._set_checkbox_state(self._cylinder_checkbox, True)

    def _gather_input_data(self) -> DemoInput:
        """Collect the data from the widgets and convert them to ``DemoInput``."""

        defaults = DemoInput()
        kwargs: Dict[str, Any] = {}

        for field in fields(DemoInput):
            widget = self._input_widgets[field.name]
            default_value = getattr(defaults, field.name)
            field_type = field.type

            if field_type is bool and isinstance(widget, QCheckBox):
                kwargs[field.name] = widget.isChecked()
                continue

            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
            else:  # Fallback to default if widget type is unexpected
                kwargs[field.name] = default_value
                continue

            if not text:
                kwargs[field.name] = default_value
                continue

            try:
                if field_type is float:
                    kwargs[field.name] = float(text)
                elif field_type is int:
                    kwargs[field.name] = int(text)
                elif field_type is str:
                    kwargs[field.name] = text
                else:
                    kwargs[field.name] = default_value
            except ValueError:
                kwargs[field.name] = default_value

        return DemoInput(**kwargs)

    def update_results(self) -> None:
        """Rebuild the model and show the resulting text."""

        try:
            input_data = self._gather_input_data()
            scantlings = build_demo_calc_scantlings(input_data)
            report = scantlings.get_results_for_report()
            summary = str(scantlings.buckling_input)
            self._latest_properties = input_data
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
        self._update_geometry_display()
        self._info_label.setText(self._default_info_text)
        if self._last_loaded_file:
            self._load_status_label.setText(
                f"Loaded inputs from {self._last_loaded_file.name}. Recalculation complete."
            )
        else:
            self._load_status_label.setText(
                "Using current in-memory configuration. Recalculation complete."
            )

    def _handle_add_point(self) -> None:
        try:
            x = float(self._point_x_input.text())
            y = float(self._point_y_input.text())
        except ValueError:
            self._info_label.setText("Invalid point coordinates. Please enter numeric values.")
            return

        name = f"P{self._point_name_counter}"
        self._point_name_counter += 1
        self._points[name] = Point(x, y)
        self._point_x_input.clear()
        self._point_y_input.clear()
        self._info_label.setText(self._default_info_text)
        self._update_geometry_display()

    def _handle_add_line(self) -> None:
        if self._line_start_combo.count() < 2:
            self._info_label.setText("Create at least two points before adding a line.")
            return

        start_name = self._line_start_combo.currentText()
        end_name = self._line_end_combo.currentText()

        if start_name == end_name:
            self._info_label.setText("Select two different points for a valid line.")
            return

        start_point = self._points.get(start_name)
        end_point = self._points.get(end_name)
        if not start_point or not end_point:
            self._info_label.setText("Selected points are not available. Please refresh and try again.")
            return

        geometry = LineString([(start_point.x, start_point.y), (end_point.x, end_point.y)])
        line_name = f"L{len(self._lines) + 1}"
        properties = getattr(self, "_latest_properties", DemoInput())
        self._lines[line_name] = ModelLine(
            name=line_name,
            start_point=start_name,
            end_point=end_name,
            geometry=geometry,
            properties=properties,
        )
        self._info_label.setText(self._default_info_text)
        self._update_geometry_display()

    def _handle_canvas_line_selected(self, line_name: str) -> None:
        line = self._lines.get(line_name)
        if not line:
            return

        self._selected_line_name = line_name
        self._canvas.set_selected_line(line_name)
        self._set_combo_to_point(self._line_start_combo, line.start_point)
        self._set_combo_to_point(self._line_end_combo, line.end_point)
        self._next_line_combo_target = "start"
        self._select_line_in_list(line_name)
        if self._widget_workspace is not None:
            self._widget_workspace.set_selected_line(line_name)
        self._ensure_drop_zone_visible()
        self._restore_workspace_for_line(line_name)

    def _handle_canvas_point_selected(self, point_name: str) -> None:
        if point_name not in self._points:
            return

        self._selected_point_name = point_name
        self._canvas.set_selected_point(point_name)
        self._select_point_in_list(point_name)

        if self._next_line_combo_target == "start":
            self._set_combo_to_point(self._line_start_combo, point_name)
            self._next_line_combo_target = "end"
        else:
            self._set_combo_to_point(self._line_end_combo, point_name)
            self._next_line_combo_target = "start"

    def _handle_load_input(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Demo Input",
            str(Path.cwd()),
            "JSON Files (*.json);;All Files (*)",
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Load Failed", f"Could not load input file:\n{exc}")
            return

        updated = False
        for field in fields(DemoInput):
            if field.name not in payload:
                continue
            widget = self._input_widgets[field.name]
            value = payload[field.name]
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
                updated = True
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))
                updated = True

        if not updated:
            QMessageBox.information(
                self,
                "No Changes Applied",
                "The selected file did not contain any recognised fields.",
            )
            return

        self._update_stiffener_fields_enabled()
        self._enforce_geometry_selection()

        self._last_loaded_file = Path(filename)
        self._load_status_label.setText(
            f"Loaded inputs from {self._last_loaded_file.name}. Recalculating…"
        )
        self.update_results()

    def _handle_manual_recalc(self) -> None:
        self._last_loaded_file = None
        self._load_status_label.setText("Recalculating current configuration…")
        self.update_results()


def main() -> int:
    """Launch the demo Qt application."""

    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
