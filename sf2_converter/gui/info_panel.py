"""Info panel widget for displaying selected instrument details."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel,
    QRadioButton, QButtonGroup, QPushButton, QProgressBar,
    QFileDialog, QLineEdit, QHBoxLayout, QComboBox, QCheckBox,
)
from PySide6.QtCore import Signal

from ..utils.naming import CATEGORIES


class InfoPanel(QWidget):
    """Right-side panel with format selection, info display, and convert button."""

    convert_requested = Signal(str, str, str, bool)  # format, output_path, category, auto_categorize
    auto_categorize_changed = Signal(bool)  # emitted when checkbox toggles

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Output format selection
        format_group = QGroupBox("Output Format")
        format_layout = QVBoxLayout()
        self._format_group = QButtonGroup(self)
        self._sli_radio = QRadioButton("SLI (multi-zone instrument)")
        self._slc_radio = QRadioButton("SLC (sample collection)")
        self._sli_radio.setChecked(True)
        self._format_group.addButton(self._sli_radio, 0)
        self._format_group.addButton(self._slc_radio, 1)
        format_layout.addWidget(self._sli_radio)
        format_layout.addWidget(self._slc_radio)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # When format changes, update the output path hint and default category
        self._sli_radio.toggled.connect(self._on_format_changed)

        # Category selection
        cat_group = QGroupBox("Spectralis Category")
        cat_layout = QVBoxLayout()
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Default:"))
        self._category_combo = QComboBox()
        for name in CATEGORIES:
            self._category_combo.addItem(name)
        self._category_combo.setCurrentText("Dsynth")  # Default for SLI
        cat_row.addWidget(self._category_combo)
        cat_layout.addLayout(cat_row)
        self._auto_cat_checkbox = QCheckBox("Auto-categorize by name")
        self._auto_cat_checkbox.setToolTip(
            "Detect categories from sample names (e.g. 'kick' -> Kick).\n"
            "Unrecognized names use the default category above."
        )
        self._auto_cat_checkbox.setChecked(True)
        self._auto_cat_checkbox.toggled.connect(self.auto_categorize_changed.emit)
        cat_layout.addWidget(self._auto_cat_checkbox)
        cat_group.setLayout(cat_layout)
        layout.addWidget(cat_group)

        # Selected info display
        info_group = QGroupBox("Selected Info")
        info_layout = QFormLayout()
        self._name_label = QLabel("-")
        self._zones_label = QLabel("-")
        self._selected_label = QLabel("0 instruments selected")
        info_layout.addRow("Name:", self._name_label)
        info_layout.addRow("Zones:", self._zones_label)
        info_layout.addRow("Selected:", self._selected_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Output path
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout()
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("Output directory for .SLI files...")
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self._output_edit)
        output_layout.addWidget(self._browse_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Convert button
        self._convert_btn = QPushButton("Convert Selected")
        self._convert_btn.setMinimumHeight(40)
        self._convert_btn.setEnabled(False)
        self._convert_btn.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; }"
        )
        self._convert_btn.clicked.connect(self._on_convert)
        layout.addWidget(self._convert_btn)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # Status label
        self._status_label = QLabel("")
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _on_format_changed(self, sli_checked: bool):
        """Update placeholder text and default category when format changes."""
        if sli_checked:
            self._output_edit.setPlaceholderText("Output directory for .SLI files...")
            self._category_combo.setCurrentText("Dsynth")
        else:
            self._output_edit.setPlaceholderText("Output .SLC file path...")
            self._category_combo.setCurrentText("Percsn")

    def update_selection(self, selected_info: list[dict]):
        """Update display based on current selection."""
        count = len(selected_info)
        self._selected_label.setText(f"{count} instrument(s) selected")
        self._convert_btn.setEnabled(count > 0)

        if count == 1:
            info = selected_info[0]
            self._name_label.setText(info["name"])
            self._zones_label.setText(str(info["zones"]))
        elif count > 1:
            total_zones = sum(i["zones"] for i in selected_info)
            self._name_label.setText(f"({count} instruments)")
            self._zones_label.setText(str(total_zones))
        else:
            self._name_label.setText("-")
            self._zones_label.setText("-")

    def _browse_output(self):
        current = self._output_edit.text()
        if self._slc_radio.isChecked():
            path, _ = QFileDialog.getSaveFileName(
                self, "Save SLC File", current, "SLC Files (*.SLC)"
            )
            if path:
                path = self._ensure_extension(path, ".SLC")
                self._output_edit.setText(path)
        else:
            # Use save dialog for SLI too — the macOS directory picker is confusing.
            # User picks a .SLI filename; we use its parent directory as the output.
            path, _ = QFileDialog.getSaveFileName(
                self, "Save SLI Files To...", current, "SLI Files (*.SLI)"
            )
            if path:
                path = self._ensure_extension(path, ".SLI")
                # Use parent directory — each instrument will be its own .SLI file
                self._output_edit.setText(str(Path(path).parent))

    @staticmethod
    def _ensure_extension(path: str, ext: str) -> str:
        """Ensure path has the correct extension, replacing any wrong one."""
        p = Path(path)
        if p.suffix.upper() == ext.upper():
            return path
        if p.suffix.lower() in (".sli", ".slc"):
            return str(p.with_suffix(ext))
        if not p.suffix:
            return path + ext
        return path + ext

    def _on_convert(self):
        fmt = "slc" if self._slc_radio.isChecked() else "sli"
        output = self._output_edit.text()
        category = self._category_combo.currentText()
        auto_cat = self._auto_cat_checkbox.isChecked()
        self.convert_requested.emit(fmt, output, category, auto_cat)

    def set_progress(self, message: str, percent: int):
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(percent)
        self._status_label.setText(message)

    def set_converting(self, converting: bool):
        self._convert_btn.setEnabled(not converting)
        self._progress_bar.setVisible(converting)
        if not converting:
            self._progress_bar.setValue(0)

    @property
    def output_path(self) -> str:
        return self._output_edit.text()

    @output_path.setter
    def output_path(self, value: str):
        self._output_edit.setText(value)
