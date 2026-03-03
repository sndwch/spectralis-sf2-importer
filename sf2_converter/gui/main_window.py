"""Main application window."""

from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QSplitter, QLabel,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject

from .sf2_tree_widget import SF2TreeWidget
from .info_panel import InfoPanel
from ..core.sf2_reader import SF2Reader
from ..core.converter import convert_to_sli, convert_to_slc, MAX_SLI_ZONES


class ConvertWorker(QObject):
    """Worker for running conversion in a background thread."""
    progress = Signal(str, int)
    finished = Signal(bool, str)

    def __init__(self, sf2_path, indices, fmt, output_path, category,
                 subcategory, auto_categorize, category_map=None,
                 subcategory_map=None):
        super().__init__()
        self.sf2_path = sf2_path
        self.indices = indices
        self.fmt = fmt
        self.output_path = output_path
        self.category = category
        self.subcategory = subcategory
        self.auto_categorize = auto_categorize
        self.category_map = category_map  # dict[int, str] or None
        self.subcategory_map = subcategory_map  # dict[int, str] or None

    def run(self):
        try:
            def on_progress(msg, pct):
                self.progress.emit(msg, pct)

            if self.fmt == "sli":
                paths = convert_to_sli(
                    self.sf2_path, self.indices, self.output_path, on_progress,
                    category=self.category, subcategory=self.subcategory,
                    auto_categorize=self.auto_categorize,
                    category_map=self.category_map,
                    subcategory_map=self.subcategory_map,
                )
                self.finished.emit(True, f"Created {len(paths)} SLI file(s)")
            else:
                convert_to_slc(
                    self.sf2_path, self.indices, self.output_path, on_progress,
                    category=self.category, subcategory=self.subcategory,
                    auto_categorize=self.auto_categorize,
                    category_map=self.category_map,
                    subcategory_map=self.subcategory_map,
                )
                self.finished.emit(True, f"Created SLC file: {self.output_path}")
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """Main application window for SF2 to SLI/SLC converter."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SF2 to SLI/SLC Converter - Spectralis 2")
        self.setMinimumSize(900, 500)
        self.resize(1100, 600)
        self._sf2_path = None
        self._worker = None
        self._thread = None
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top bar
        top_bar = QHBoxLayout()
        self._open_btn = QPushButton("Open SF2...")
        self._open_btn.clicked.connect(self._open_sf2)
        self._file_label = QLabel("No file loaded")
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(lambda: self._tree.select_all())
        self._select_all_btn.setEnabled(False)
        self._select_none_btn = QPushButton("Select None")
        self._select_none_btn.clicked.connect(lambda: self._tree.select_none())
        self._select_none_btn.setEnabled(False)
        top_bar.addWidget(self._open_btn)
        top_bar.addWidget(self._file_label, 1)
        top_bar.addWidget(self._select_all_btn)
        top_bar.addWidget(self._select_none_btn)
        main_layout.addLayout(top_bar)

        # Main content: splitter with tree (left) and info panel (right)
        splitter = QSplitter(Qt.Horizontal)

        self._tree = SF2TreeWidget()
        self._tree.selection_changed.connect(self._on_selection_changed)
        self._tree.set_categories_visible(False)  # Hidden by default (auto-categorize is on)
        splitter.addWidget(self._tree)

        self._info_panel = InfoPanel()
        self._info_panel.convert_requested.connect(self._start_convert)
        self._info_panel.auto_categorize_changed.connect(self._on_auto_cat_changed)
        splitter.addWidget(self._info_panel)

        splitter.setSizes([700, 400])
        main_layout.addWidget(splitter)

    def _open_sf2(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open SF2 SoundFont", "", "SoundFont Files (*.sf2);;All Files (*)"
        )
        if not path:
            return

        self._sf2_path = Path(path)
        self._file_label.setText(str(self._sf2_path))

        try:
            with SF2Reader(self._sf2_path) as reader:
                instruments = reader.list_instruments()
                self._tree.load_sf2(instruments)
                self._select_all_btn.setEnabled(True)
                self._select_none_btn.setEnabled(True)

                # Default output to same directory as input
                self._info_panel.output_path = str(self._sf2_path.parent)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open SF2 file:\n{e}")

    def _on_selection_changed(self):
        info = self._tree.get_selected_info()
        self._info_panel.update_selection(info)

    def _on_auto_cat_changed(self, auto: bool):
        """Show/hide per-preset category selectors based on auto-categorize."""
        self._tree.set_categories_visible(not auto)

    def _start_convert(self, fmt: str, output_path: str, category: str = "Percsn",
                       subcategory: str = "Other", auto_categorize: bool = False):
        if self._sf2_path is None:
            QMessageBox.warning(self, "No File", "Please open an SF2 file first.")
            return

        indices = self._tree.get_selected_instrument_indices()
        if not indices:
            QMessageBox.warning(self, "No Selection", "Please select at least one instrument.")
            return

        # Warn about instruments with excessive zone counts (SLI only)
        if fmt == "sli":
            selected_info = self._tree.get_selected_info()
            big = [(i["name"], i["zones"]) for i in selected_info if i["zones"] > MAX_SLI_ZONES]
            if big:
                names = "\n".join(f"  {name} ({z} zones)" for name, z in big)
                reply = QMessageBox.warning(
                    self, "High Zone Count",
                    f"The following instrument(s) exceed {MAX_SLI_ZONES} zones and "
                    f"may not load on the Spectralis 2:\n\n{names}\n\n"
                    f"Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return

        if not output_path:
            output_path = str(self._sf2_path.parent)

        out = Path(output_path)
        if fmt == "slc":
            if out.is_dir():
                output_path = str(out / f"{self._sf2_path.stem}.SLC")
            elif out.suffix.lower() != ".slc":
                output_path = str(out.with_suffix(".SLC"))
        else:
            if not out.is_dir() and out.suffix.lower() in (".sli", ".slc"):
                output_path = str(out.parent)

        # Get per-instrument category/subcategory maps from tree combos
        category_map = None
        subcategory_map = None
        if not auto_categorize:
            category_map, subcategory_map = self._tree.get_category_map()

        self._info_panel.set_converting(True)

        # Run conversion in background thread
        self._thread = QThread()
        self._worker = ConvertWorker(
            str(self._sf2_path), indices, fmt, output_path, category,
            subcategory, auto_categorize, category_map, subcategory_map,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._info_panel.set_progress)
        self._worker.finished.connect(self._on_convert_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def _on_convert_finished(self, success: bool, message: str):
        self._info_panel.set_converting(False)
        if success:
            self._info_panel.set_progress(message, 100)
            QMessageBox.information(self, "Success", message)
        else:
            self._info_panel.set_progress(f"Error: {message}", 0)
            QMessageBox.critical(self, "Conversion Error", message)

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        event.accept()
