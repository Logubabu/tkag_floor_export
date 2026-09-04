import sys
import os
import traceback
from typing import List, Dict, Any, Optional

# Ensure project root is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
backend_dir = os.path.join(project_root, "backend")

for p in [project_root, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QCheckBox, QRadioButton, QButtonGroup, QProgressBar, QTextEdit, QGroupBox, QHeaderView,
    QMessageBox, QSplitter, QFrame, QAbstractItemView, QStyle
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QColor

from backend.app.etabs.e2k_parser import E2KParser
from backend.app.etabs.com_adapter import ETABSCOMAdapter
from backend.app.etabs.version_detector import ETABSVersionDetector
from backend.app.floor_extractor.extractor import FloorExtractor
from backend.app.models.intermediate import BuildingModel, FloorModel, ExtractionMode
from backend.app.ram_concept.exporter import RAMConceptExporter
from backend.app.ram_concept.ram_detector import RAMConceptDetector
from backend.app.reports.report_generator import ReportGenerator
from gui.model_viewer import ModelViewerWidget


class ParsingThread(QThread):
    finished_signal = Signal(object, str, str)  # (BuildingModel, filename, companion_text)
    error_signal = Signal(str)

    def __init__(self, file_path: str, companion_path: Optional[str] = None):
        super().__init__()
        self.file_path = file_path
        self.companion_path = companion_path

    def run(self):
        try:
            filename = os.path.basename(self.file_path)
            content_str = None
            companion_text = None

            parser = E2KParser()
            b_model = parser.parse_file(self.file_path)

            if not b_model or not b_model.stories:
                raise ValueError(f"Could not parse valid ETABS structural story data from '{filename}'.")

            self.finished_signal.emit(b_model, filename, companion_text)
        except Exception as e:
            self.error_signal.emit(f"Error parsing model file: {str(e)}\n{traceback.format_exc()}")


class ExportThread(QThread):
    progress_signal = Signal(str)
    item_complete_signal = Signal(str, str) # (story_name, cpt_file_path)
    finished_signal = Signal(int, int) # (success_count, total_count)

    def __init__(self, b_model: BuildingModel, selected_stories: List[str], output_dir: str, formats: Dict[str, bool]):
        super().__init__()
        self.b_model = b_model
        self.selected_stories = selected_stories
        self.output_dir = output_dir
        self.formats = formats

    def run(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        success_count = 0
        total = len(self.selected_stories)

        try:
            for idx, story_name in enumerate(self.selected_stories, 1):
                try:
                    self.progress_signal.emit(f"[{idx}/{total}] Extracting floor geometry for story: {story_name}...")
                    floor_model = FloorExtractor.extract_floor(
                        self.b_model, story_name, ExtractionMode.SLAB_AND_SUPPORTS
                    )

                    self.progress_signal.emit(f"[{idx}/{total}] Exporting RAM Concept model for story: {story_name}...")
                    exporter = RAMConceptExporter(floor_model)

                    clean_story = "".join(c for c in story_name if c.isalnum() or c in ['_', '-'])
                    floor_folder = os.path.join(self.output_dir, f"Floor_{clean_story}")
                    res = exporter.generate_output(floor_folder)

                    cpt_path = res.get("cpt_file", "")
                    py_path = res.get("automation_script", "")

                    # Generate Report & Import Instructions text file
                    conv_sum = {
                        "source_slabs": len(floor_model.slabs), "converted_slabs": len(floor_model.slabs),
                        "source_openings": len(floor_model.openings), "converted_openings": len(floor_model.openings),
                        "source_beams": len(floor_model.beams), "converted_beams": len(floor_model.beams),
                        "source_columns": len(floor_model.columns_above) + len(floor_model.columns_below), "converted_columns": len(floor_model.columns_above) + len(floor_model.columns_below),
                        "source_walls": len(floor_model.walls_above) + len(floor_model.walls_below), "converted_walls": len(floor_model.walls_above) + len(floor_model.walls_below),
                    }
                    ReportGenerator.generate_report(clean_story, conv_sum, {}, res, floor_folder)

                    if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0:
                        size_mb = os.path.getsize(cpt_path) / (1024 * 1024)
                        self.progress_signal.emit(f"✓ Native .CPT model generated for {story_name} ({size_mb:.2f} MB) in '{floor_folder}'")
                    else:
                        self.progress_signal.emit(f"✓ DXF exchange model generated for {story_name} in '{floor_folder}'")
                    
                    self.item_complete_signal.emit(story_name, cpt_path if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0 else "")
                    success_count += 1
                except Exception as e:
                    self.progress_signal.emit(f"✗ Failed to export story {story_name}: {str(e)}")

            self.finished_signal.emit(success_count, total)
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass


class RAMExporterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETABS to RAM Concept Floor Exporter")
        self.resize(1280, 820)
        self.building_model: Optional[BuildingModel] = None
        self.current_file_path: Optional[str] = None
        self.output_dir: str = os.path.expanduser("~/Documents")

        self._setup_ui()
        self._apply_theme()
        self.run_ram_detection()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Header & RAM Concept Detection Banner
        header_box = QGroupBox("System Status & RAM Concept Integration")
        header_layout = QHBoxLayout(header_box)

        self.ram_status_label = QLabel("Detecting RAM Concept installation...")
        self.ram_status_label.setWordWrap(True)
        self.ram_status_label.setStyleSheet("font-weight: bold; font-size: 13px;")

        self.btn_redetect = QPushButton("Re-Detect RAM Concept")
        self.btn_redetect.setFixedWidth(160)
        self.btn_redetect.clicked.connect(self.run_ram_detection)

        header_layout.addWidget(self.ram_status_label, stretch=1)
        header_layout.addWidget(self.btn_redetect)
        main_layout.addWidget(header_box)

        # 1b. ETABS Live API Connection & Processing Mode Panel
        etabs_box = QGroupBox("ETABS Live COM Connection & Processing Mode")
        etabs_layout = QHBoxLayout(etabs_box)

        mode_layout = QHBoxLayout()
        self.radio_mode_auto = QRadioButton("AUTO (Live COM if available)")
        self.radio_mode_live = QRadioButton("LIVE ETABS COM API")
        self.radio_mode_offline = QRadioButton("OFFLINE PARSER")
        self.radio_mode_auto.setChecked(True)

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_mode_auto)
        self.mode_group.addButton(self.radio_mode_live)
        self.mode_group.addButton(self.radio_mode_offline)

        mode_layout.addWidget(self.radio_mode_auto)
        mode_layout.addWidget(self.radio_mode_live)
        mode_layout.addWidget(self.radio_mode_offline)

        self.btn_connect_etabs = QPushButton("Connect to Active ETABS")
        self.btn_connect_etabs.setStyleSheet("font-weight: bold; background-color: #059669; color: white;")
        self.btn_connect_etabs.clicked.connect(self.connect_live_etabs)

        self.btn_detect_etabs = QPushButton("Detect Installed ETABS")
        self.btn_detect_etabs.clicked.connect(self.detect_etabs_installations)

        self.lbl_etabs_status = QLabel("ETABS Status: Standby (Click 'Connect' or Browse Model)")
        self.lbl_etabs_status.setStyleSheet("color: #38bdf8; font-weight: bold;")

        etabs_layout.addLayout(mode_layout)
        etabs_layout.addWidget(self.btn_connect_etabs)
        etabs_layout.addWidget(self.btn_detect_etabs)
        etabs_layout.addWidget(self.lbl_etabs_status, stretch=1)
        main_layout.addWidget(etabs_box)

        # 2. File Selection Panel
        file_box = QGroupBox("1. Select ETABS Model File")
        file_layout = QHBoxLayout(file_box)

        self.lbl_file_path = QLabel("No file loaded. Select a .$ET, .E2K, or .EDB file:")
        self.lbl_file_path.setStyleSheet("color: #aaa;")

        self.btn_browse = QPushButton("Browse ETABS File...")
        self.btn_browse.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_browse.clicked.connect(self.browse_file)

        self.btn_parse = QPushButton("Parse & Extract")
        self.btn_parse.setEnabled(False)
        self.btn_parse.setStyleSheet("font-weight: bold; background-color: #2563eb; color: white;")
        self.btn_parse.clicked.connect(self.start_parsing)

        file_layout.addWidget(self.lbl_file_path, stretch=1)
        file_layout.addWidget(self.btn_browse)
        file_layout.addWidget(self.btn_parse)
        main_layout.addWidget(file_box)

        # 3. Main Content Splitter (Story Selection + Export Settings)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Story Tree & Selection
        story_box = QGroupBox("2. Select Stories / Floors to Export")
        story_layout = QVBoxLayout(story_box)

        # Select All / Deselect All Bar
        sel_btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_select_all.clicked.connect(self.select_all_stories)
        self.btn_deselect_all.clicked.connect(self.deselect_all_stories)
        sel_btn_layout.addWidget(self.btn_select_all)
        sel_btn_layout.addWidget(self.btn_deselect_all)
        sel_btn_layout.addStretch()
        story_layout.addLayout(sel_btn_layout)

        self.table_stories = QTableWidget(0, 5)
        self.table_stories.setHorizontalHeaderLabels(["Export", "Story Name", "Elevation (m)", "Height (m)", "Status"])
        self.table_stories.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_stories.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_stories.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_stories.itemSelectionChanged.connect(self.on_story_selection_changed)
        self.table_stories.itemClicked.connect(self.on_story_table_item_clicked)
        story_layout.addWidget(self.table_stories)

        splitter.addWidget(story_box)

        # Center Column: 2D/3D Model Viewer
        viewer_box = QGroupBox("Model Viewer (2D Floor Plan / 3D Isometric)")
        viewer_layout = QVBoxLayout(viewer_box)

        # Viewer toolbar
        view_tools = QHBoxLayout()
        self.btn_view_2d = QPushButton("2D Floor Plan")
        self.btn_view_3d = QPushButton("3D Isometric")
        self.btn_fit_screen = QPushButton("Fit to Screen")

        self.btn_view_2d.setCheckable(True)
        self.btn_view_2d.setChecked(True)
        self.btn_view_3d.setCheckable(True)

        self.btn_view_2d.clicked.connect(self.set_2d_mode)
        self.btn_view_3d.clicked.connect(self.set_3d_mode)
        self.btn_fit_screen.clicked.connect(lambda: self.model_viewer.fit_to_screen())

        view_tools.addWidget(self.btn_view_2d)
        view_tools.addWidget(self.btn_view_3d)
        view_tools.addWidget(self.btn_fit_screen)
        view_tools.addStretch()
        viewer_layout.addLayout(view_tools)

        # Layer visibility toggle toolbar
        layer_tools = QHBoxLayout()
        layer_tools.addWidget(QLabel("Layers:"))
        self.chk_layer_slabs = QCheckBox("Slabs")
        self.chk_layer_beams = QCheckBox("Beams")
        self.chk_layer_columns = QCheckBox("Columns")
        self.chk_layer_walls = QCheckBox("Walls")
        self.chk_layer_openings = QCheckBox("Openings")
        self.chk_layer_nodes = QCheckBox("Nodes")
        self.chk_layer_labels = QCheckBox("Show/Hide Names")

        for chk in [self.chk_layer_slabs, self.chk_layer_beams, self.chk_layer_columns, self.chk_layer_walls, self.chk_layer_openings, self.chk_layer_nodes, self.chk_layer_labels]:
            chk.setChecked(True)
            layer_tools.addWidget(chk)

        self.chk_layer_slabs.toggled.connect(self.on_toggle_slabs)
        self.chk_layer_beams.toggled.connect(self.on_toggle_beams)
        self.chk_layer_columns.toggled.connect(self.on_toggle_columns)
        self.chk_layer_walls.toggled.connect(self.on_toggle_walls)
        self.chk_layer_openings.toggled.connect(self.on_toggle_openings)
        self.chk_layer_nodes.toggled.connect(self.on_toggle_nodes)
        self.chk_layer_labels.toggled.connect(self.on_toggle_labels)

        layer_tools.addStretch()
        viewer_layout.addLayout(layer_tools)

        self.model_viewer = ModelViewerWidget()
        viewer_layout.addWidget(self.model_viewer)
        splitter.addWidget(viewer_box)

        # Right Column: Export Settings & Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        export_opts_box = QGroupBox("3. RAM Concept Export Settings")
        opts_layout = QVBoxLayout(export_opts_box)

        # Format Checkboxes (.CPT and .DXF only per user requirement)
        self.chk_cpt = QCheckBox("Bentley RAM Concept Model File (.CPT)")
        self.chk_cpt.setChecked(True)
        self.chk_dxf = QCheckBox("CAD Structural Exchange Drawing (.DXF)")
        self.chk_dxf.setChecked(True)
        self.chk_py = QCheckBox("Python Automation Macro (.PY)")
        self.chk_py.setChecked(False)
        self.chk_py.setVisible(False)
        self.chk_json = QCheckBox("Structural Schema (.JSON)")
        self.chk_json.setChecked(False)
        self.chk_json.setVisible(False)

        opts_layout.addWidget(self.chk_cpt)
        opts_layout.addWidget(self.chk_dxf)
        opts_layout.addWidget(self.chk_py)
        opts_layout.addWidget(self.chk_json)

        # Output Folder Selection
        out_folder_layout = QHBoxLayout()
        self.lbl_out_dir = QLabel(f"Output Directory: {self.output_dir}")
        self.lbl_out_dir.setWordWrap(True)
        self.btn_change_out_dir = QPushButton("Change Folder...")
        self.btn_change_out_dir.clicked.connect(self.change_output_dir)
        self.btn_open_out_dir = QPushButton("Open Folder 📁")
        self.btn_open_out_dir.clicked.connect(self.open_output_dir)
        out_folder_layout.addWidget(self.lbl_out_dir, stretch=1)
        out_folder_layout.addWidget(self.btn_change_out_dir)
        out_folder_layout.addWidget(self.btn_open_out_dir)
        opts_layout.addLayout(out_folder_layout)

        # Big Export Button
        self.btn_export = QPushButton("EXPORT SELECTED FLOORS TO RAM CONCEPT (.CPT)")
        self.btn_export.setFixedHeight(45)
        self.btn_export.setEnabled(False)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #10b981;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #9ca3af;
            }
        """)
        self.btn_export.clicked.connect(self.start_export)
        opts_layout.addWidget(self.btn_export)

        right_layout.addWidget(export_opts_box)

        # Progress & Log Box
        log_box = QGroupBox("Activity Log & Status")
        log_layout = QVBoxLayout(log_box)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        log_layout.addWidget(self.progress_bar)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("font-family: Consolas, monospace; font-size: 11px; background-color: #111827; color: #e5e7eb;")
        log_layout.addWidget(self.txt_log)

        right_layout.addWidget(log_box)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 450, 350])
        main_layout.addWidget(splitter, stretch=1)

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1f2937;
                color: #f3f4f6;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #374151;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #60a5fa;
            }
            QPushButton {
                background-color: #374151;
                color: #f3f4f6;
                border: 1px solid #4b5563;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QTableWidget {
                background-color: #111827;
                border: 1px solid #374151;
                gridline-color: #374151;
            }
            QHeaderView::section {
                background-color: #1f2937;
                color: #9ca3af;
                padding: 4px;
                border: 1px solid #374151;
            }
            QCheckBox {
                color: #e5e7eb;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #60a5fa;
                background-color: #111827;
            }
            QCheckBox::indicator:checked {
                border-color: #2563eb;
                background-color: #2563eb;
            }
            QRadioButton {
                color: #f3f4f6;
                font-weight: bold;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 9px;
                border: 2px solid #60a5fa;
                background-color: #111827;
            }
            QRadioButton::indicator:hover {
                border-color: #93c5fd;
                background-color: #374151;
            }
            QRadioButton::indicator:checked {
                border: 3px solid #60a5fa;
                background-color: #2563eb;
            }
            QRadioButton:checked {
                color: #60a5fa;
                font-weight: bold;
            }
        """)

    def log(self, text: str):
        self.txt_log.append(text)

    def run_ram_detection(self):
        detection = RAMConceptDetector.detect_all()
        if detection["installed"]:
            self.ram_status_label.setText(
                f"✓ Detected RAM Concept: {detection['version']}\n"
                f"Executable Path: {detection['executable_path']}\n"
                f"COM Automation Available: {'Yes' if detection['com_available'] else 'No'} | "
                f"Python API Available: {'Yes' if detection['python_api_available'] else 'No'}"
            )
            self.ram_status_label.setStyleSheet("color: #34d399; font-weight: bold;")
            self.log(f"RAM Concept Auto-Detection: {detection['status_summary']}")
        else:
            self.ram_status_label.setText("⚠ RAM Concept not detected in standard system paths.\n"
                                          "CAD .DXF exchange package & Python macro scripts will be generated automatically.")
            self.ram_status_label.setStyleSheet("color: #fbbf24; font-weight: bold;")
            self.log("RAM Concept Auto-Detection: Not installed. Operating in Drawing Exchange Mode.")

    def detect_etabs_installations(self):
        installs = ETABSVersionDetector.detect_installations()
        if installs:
            ver_strs = [f"{i['version']}" for i in installs]
            msg = f"✓ ETABS Detected: {', '.join(ver_strs)}"
            self.lbl_etabs_status.setText(msg)
            self.lbl_etabs_status.setStyleSheet("color: #34d399; font-weight: bold;")
            self.log(msg)
        else:
            self.lbl_etabs_status.setText("⚠ No installed ETABS found in standard paths. Use Offline Parser.")
            self.lbl_etabs_status.setStyleSheet("color: #fbbf24; font-weight: bold;")
            self.log("ETABS Detection: No installed ETABS versions found.")

    def connect_live_etabs(self):
        self.radio_mode_live.setChecked(True)
        self.log("Attempting to connect to active running ETABS instance via COM OAPI...")
        adapter = ETABSCOMAdapter()
        success, msg = adapter.connect_running_instance()
        if success:
            self.lbl_etabs_status.setText(f"✓ {msg}")
            self.lbl_etabs_status.setStyleSheet("color: #34d399; font-weight: bold;")
            self.log(f"ETABS COM Connection Success: {msg}")
            
            try:
                self.log("Extracting structural model directly from connected ETABS session...")
                b_model = adapter.extract_building_model()
                if b_model and b_model.stories:
                    self.building_model = b_model
                    self.lbl_file_path.setText(f"Live Connected ETABS Model: {b_model.project_name}")
                    self.populate_stories(b_model.stories)
                    self.log(f"Successfully extracted {len(b_model.stories)} stories and structural elements from Live ETABS session!")
                    QMessageBox.information(self, "Live ETABS Connected", f"Successfully connected to active ETABS session and extracted {len(b_model.stories)} stories!")
            except Exception as e:
                self.log(f"Notice during live ETABS extraction: {e}")
                QMessageBox.warning(self, "Live ETABS Extraction Notice", f"Connected to ETABS COM API: {msg}")
        else:
            self.lbl_etabs_status.setText(f"⚠ {msg}")
            self.lbl_etabs_status.setStyleSheet("color: #f87171; font-weight: bold;")
            self.log(f"ETABS COM Connection Status: {msg}")
            QMessageBox.warning(
                self,
                "ETABS Live COM Connection",
                f"Could not connect to an active ETABS session:\n\n{msg}\n\n"
                "Please ensure ETABS is open with a model loaded, or use 'Browse ETABS File...' to parse .E2K / $ET / .ET files offline."
            )

    def browse_file(self):
        file_filter = "ETABS Files (*.$et *.e2k *.edb);;All Files (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ETABS Model File", "", file_filter)
        if file_path:
            self.current_file_path = file_path
            self.lbl_file_path.setText(f"Selected: {os.path.basename(file_path)}")
            self.lbl_file_path.setStyleSheet("color: #60a5fa; font-weight: bold;")
            self.btn_parse.setEnabled(True)
            self.log(f"Loaded file selection: {file_path}")

    def change_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_dir)
        if dir_path:
            self.output_dir = dir_path
            self.lbl_out_dir.setText(f"Output Directory: {self.output_dir}")

    def open_output_dir(self):
        if os.path.exists(self.output_dir):
            os.startfile(self.output_dir)
            self.log(f"Opened output directory in Windows Explorer: {self.output_dir}")

    def start_parsing(self):
        if not self.current_file_path:
            return

        self.btn_parse.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.log(f"Started parsing model: {os.path.basename(self.current_file_path)}...")

        self.parse_thread = ParsingThread(self.current_file_path)
        self.parse_thread.finished_signal.connect(self.on_parsing_finished)
        self.parse_thread.error_signal.connect(self.on_parsing_error)
        self.parse_thread.start()

    def on_parsing_finished(self, b_model: BuildingModel, filename: str, companion_text: Optional[str]):
        self.building_model = b_model
        self.btn_parse.setEnabled(True)
        self.btn_browse.setEnabled(True)

        stories = b_model.stories
        self.log(f"Successfully parsed building model '{filename}' with {len(stories)} stories.")

    def populate_stories(self, stories):
        self.table_stories.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_stories.setRowCount(0)
        for row_idx, story in enumerate(stories):
            self.table_stories.insertRow(row_idx)

            # Checkbox Column
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            self.table_stories.setItem(row_idx, 0, chk_item)

            # Story Name Column (Read-Only)
            item_name = QTableWidgetItem(str(story.name))
            item_name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table_stories.setItem(row_idx, 1, item_name)

            # Elevation Column (Read-Only)
            item_elev = QTableWidgetItem(f"{story.elevation:.2f}")
            item_elev.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table_stories.setItem(row_idx, 2, item_elev)

            # Height Column (Read-Only)
            item_height = QTableWidgetItem(f"{story.height:.2f}")
            item_height.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table_stories.setItem(row_idx, 3, item_height)

            # Status Column (Read-Only)
            item_status = QTableWidgetItem("Ready for Export")
            item_status.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table_stories.setItem(row_idx, 4, item_status)

        self.btn_export.setEnabled(True)

        if stories:
            self.table_stories.selectRow(0)
            self.on_story_selection_changed()

    def on_parsing_finished(self, b_model: BuildingModel, filename: str, companion_text: Optional[str]):
        self.building_model = b_model
        self.btn_parse.setEnabled(True)
        self.btn_browse.setEnabled(True)

        stories = b_model.stories
        self.log(f"Successfully parsed building model '{filename}' with {len(stories)} stories.")
        self.populate_stories(stories)

    def set_2d_mode(self):
        self.btn_view_2d.setChecked(True)
        self.btn_view_3d.setChecked(False)
        self.model_viewer.set_2d_mode()

    def set_3d_mode(self):
        self.btn_view_2d.setChecked(False)
        self.btn_view_3d.setChecked(True)
        self.model_viewer.set_3d_mode()

    def on_toggle_slabs(self, checked: bool):
        self.model_viewer.show_slabs = checked
        self.model_viewer.update()

    def on_toggle_beams(self, checked: bool):
        self.model_viewer.show_beams = checked
        self.model_viewer.update()

    def on_toggle_columns(self, checked: bool):
        self.model_viewer.show_columns = checked
        self.model_viewer.update()

    def on_toggle_walls(self, checked: bool):
        self.model_viewer.show_walls = checked
        self.model_viewer.update()

    def on_toggle_openings(self, checked: bool):
        self.model_viewer.show_openings = checked
        self.model_viewer.update()

    def on_toggle_nodes(self, checked: bool):
        self.model_viewer.show_nodes = checked
        self.model_viewer.update()

    def on_toggle_labels(self, checked: bool):
        self.model_viewer.show_labels = checked
        self.model_viewer.update()

    def on_story_selection_changed(self):
        if not self.building_model:
            return
        selected_rows = self.table_stories.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        name_item = self.table_stories.item(row, 1)
        if name_item:
            story_name = name_item.text()
            # Extract single selected floor model exclusively
            floor_model = FloorExtractor.extract_floor(self.building_model, story_name)
            self.model_viewer.set_floor_model(floor_model)
            self.log(f"Displaying extracted floor geometry for selected story: '{story_name}'")

    def on_story_table_item_clicked(self, item: QTableWidgetItem):
        if not self.building_model or not item:
            return
        row = item.row()
        name_item = self.table_stories.item(row, 1)
        if name_item:
            story_name = name_item.text()
            # Extract single selected floor model exclusively
            floor_model = FloorExtractor.extract_floor(self.building_model, story_name)
            self.model_viewer.set_floor_model(floor_model)
            self.log(f"Displaying extracted floor geometry for clicked story: '{story_name}'")

    def on_parsing_error(self, err_msg: str):
        self.btn_parse.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.log(f"Parsing failed: {err_msg}")
        QMessageBox.critical(self, "Parsing Error", f"Failed to parse ETABS model:\n\n{err_msg}")

    def select_all_stories(self):
        for r in range(self.table_stories.rowCount()):
            item = self.table_stories.item(r, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def deselect_all_stories(self):
        for r in range(self.table_stories.rowCount()):
            item = self.table_stories.item(r, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def get_selected_stories(self) -> List[str]:
        selected = []
        for r in range(self.table_stories.rowCount()):
            chk_item = self.table_stories.item(r, 0)
            name_item = self.table_stories.item(r, 1)
            if chk_item and chk_item.checkState() == Qt.Checked and name_item:
                selected.append(name_item.text())
        return selected

    def start_export(self):
        if not self.building_model:
            return

        selected_stories = self.get_selected_stories()
        if not selected_stories:
            QMessageBox.warning(self, "No Stories Selected", "Please select at least one story/floor to export.")
            return

        formats = {
            "cpt": self.chk_cpt.isChecked(),
            "dxf": self.chk_dxf.isChecked(),
            "py": False,
            "json": False
        }

        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected_stories))

        self.log(f"Starting batch export for {len(selected_stories)} selected floor(s) to '{self.output_dir}'...")

        self.export_thread = ExportThread(self.building_model, selected_stories, self.output_dir, formats)
        self.export_thread.progress_signal.connect(self.log)
        self.export_thread.item_complete_signal.connect(self.on_story_exported)
        self.export_thread.finished_signal.connect(self.on_export_finished)
        self.export_thread.start()

    def on_story_exported(self, story_name: str, cpt_path: str):
        val = self.progress_bar.value() + 1
        self.progress_bar.setValue(val)

        # Update table status column
        for r in range(self.table_stories.rowCount()):
            name_item = self.table_stories.item(r, 1)
            if name_item and name_item.text() == story_name:
                if cpt_path and os.path.exists(cpt_path):
                    status_item = QTableWidgetItem("✓ Exported .CPT")
                    status_item.setForeground(QColor("#34d399"))
                else:
                    status_item = QTableWidgetItem("✓ Exported DXF/Macro")
                    status_item.setForeground(QColor("#60a5fa"))
                self.table_stories.setItem(r, 4, status_item)

    def on_export_finished(self, success_count: int, total_count: int):
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log(f"=== Batch Export Completed: {success_count}/{total_count} floors exported successfully ===")
        self.show_import_instructions(success_count, total_count)

    def show_import_instructions(self, success_count: int = 1, total_count: int = 1):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("RAM Concept Model Opening & Import Guide")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText(f"Export Completed Successfully ({success_count}/{total_count} floors exported)\nOutput Folder: {self.output_dir}")
        msg_box.setInformativeText(
            "HOW TO VIEW / IMPORT YOUR MODEL IN BENTLEY RAM CONCEPT:\n\n"
            "1. OPENING NATIVE MODEL (.CPT):\n"
            "   • Launch Bentley RAM Concept.\n"
            "   • Click File -> Open... and select the exported .cpt file (e.g. Floor_Floor5.cpt).\n"
            "   • In the left Layer Tree, double-click: Structure Layer -> Slab Area Plan.\n"
            "   • All Slabs, Beams, Columns, Walls, and Openings render in full 3D/2D layout.\n\n"
            "2. IMPORTING CAD DRAWING / STRUCTURAL EXCHANGE (.DXF / .CPF):\n"
            "   • Launch Bentley RAM Concept and create a new document (File -> New).\n"
            "   • Go to File -> Import -> Drawing File... (or CAD File...).\n"
            "   • Select the exported .dxf or .cpf file.\n"
            "   • Ensure Import Units match Model Units (Meters / Millimeters).\n"
            "   • Map drawing layers (SLAB_OUTLINE, BEAMS, COLUMNS_BELOW, WALLS_BELOW, OPENINGS) onto Structure Plan.\n\n"
            "3. AUTOMATED PYTHON API SCRIPT:\n"
            "   • Open Command Prompt in the export folder and run:\n"
            "     python <story_name>_RAMConcept_Automation.py\n\n"
            "Note: A copy of these instructions (RAM_CONCEPT_IMPORT_INSTRUCTIONS.txt) has been saved in your output folder."
        )
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ETABS to RAM Concept Exporter")
    window = RAMExporterMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
