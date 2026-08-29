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
    QCheckBox, QProgressBar, QTextEdit, QGroupBox, QHeaderView,
    QMessageBox, QSplitter, QFrame, QAbstractItemView, QStyle
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QColor

from backend.app.etabs.e2k_parser import E2KParser
from backend.app.floor_extractor.extractor import FloorExtractor
from backend.app.models.intermediate import BuildingModel, FloorModel, ExtractionMode
from backend.app.ram_concept.exporter import RAMConceptExporter
from backend.app.ram_concept.ram_detector import RAMConceptDetector


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

            # Read primary file if text format
            if not self.file_path.lower().endswith(".edb"):
                with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content_str = f.read()

            # Read companion file if provided
            if self.companion_path and os.path.exists(self.companion_path):
                with open(self.companion_path, "r", encoding="utf-8", errors="ignore") as f:
                    companion_text = f.read()

            parser = E2KParser()

            # Parse primary text if available
            b_model = None
            if content_str:
                b_model = parser.parse_string(content_str)
            elif companion_text:
                b_model = parser.parse_string(companion_text)

            if not b_model or not b_model.stories:
                # If EDB or parsing failed, try direct EDB parser
                from backend.app.etabs.edb_parser import EDBParser
                edb_p = EDBParser()
                b_model = edb_p.parse(self.file_path)

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
        success_count = 0
        total = len(self.selected_stories)

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
                if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0:
                    size_mb = os.path.getsize(cpt_path) / (1024 * 1024)
                    self.progress_signal.emit(f"✓ Native .CPT / .CPF model generated for {story_name} ({size_mb:.2f} MB) in '{floor_folder}'")
                else:
                    self.progress_signal.emit(f"✓ DXF exchange model & Python automation macro generated for {story_name} in '{floor_folder}'")
                
                self.item_complete_signal.emit(story_name, cpt_path if cpt_path and os.path.exists(cpt_path) and os.path.getsize(cpt_path) > 0 else "")
                success_count += 1
            except Exception as e:
                self.progress_signal.emit(f"✗ Failed to export story {story_name}: {str(e)}")

        self.finished_signal.emit(success_count, total)


class RAMExporterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETABS to RAM Concept Floor Exporter")
        self.resize(1100, 780)
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
        story_layout.addWidget(self.table_stories)

        splitter.addWidget(story_box)

        # Right Column: Export Settings & Logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        export_opts_box = QGroupBox("3. RAM Concept Export Settings")
        opts_layout = QVBoxLayout(export_opts_box)

        # Format Checkboxes (.CPT/.CPF and .DXF only per user requirement)
        self.chk_cpt = QCheckBox("Bentley RAM Concept Model File (.CPT / .CPF)")
        self.chk_cpt.setChecked(True)
        self.chk_dxf = QCheckBox("CAD Structural Exchange Drawing (.DXF)")
        self.chk_dxf.setChecked(True)
        self.chk_py = QCheckBox("Python RAM Concept COM Macro Script (.PY)")
        self.chk_py.setChecked(False)
        self.chk_py.setVisible(False)
        self.chk_json = QCheckBox("Intermediate Structural Model Schema (.JSON)")
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
        splitter.setSizes([550, 450])
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
            self.ram_status_label.setText(
                "⚠ RAM Concept Installation Not Found in Standard Directories.\n"
                "Models can still be exported to DXF exchange format + Python COM macro scripts."
            )
            self.ram_status_label.setStyleSheet("color: #fbbf24; font-weight: bold;")
            self.log("RAM Concept Auto-Detection: RAM Concept executable not found.")

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

        # Populate story table
        self.table_stories.setRowCount(0)
        for row_idx, story in enumerate(stories):
            self.table_stories.insertRow(row_idx)

            # Checkbox
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            self.table_stories.setItem(row_idx, 0, chk_item)

            # Name
            self.table_stories.setItem(row_idx, 1, QTableWidgetItem(story.name))
            # Elevation
            self.table_stories.setItem(row_idx, 2, QTableWidgetItem(f"{story.elevation:.2f}"))
            # Height
            self.table_stories.setItem(row_idx, 3, QTableWidgetItem(f"{story.height:.2f}"))
            # Status
            self.table_stories.setItem(row_idx, 4, QTableWidgetItem("Ready for Export"))

        self.btn_export.setEnabled(True)

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
        QMessageBox.information(
            self,
            "Export Complete",
            f"Export process completed!\n\n"
            f"Successfully exported {success_count} of {total_count} selected floor(s).\n"
            f"Saved to: {self.output_dir}"
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ETABS to RAM Concept Exporter")
    window = RAMExporterMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
