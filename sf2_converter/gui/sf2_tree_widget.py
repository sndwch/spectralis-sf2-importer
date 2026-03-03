"""Flat instrument list widget with checkboxes and per-row category/subcategory."""

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal

from ..utils.naming import CATEGORIES, get_subcategory_names

_CATEGORY_NAMES = list(CATEGORIES.keys())


class SF2TreeWidget(QTableWidget):
    """Flat table of SF2 instruments with checkboxes and optional category combos."""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Name", "Zones", "Category", "Subcategory"])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.setColumnWidth(2, 110)
        self.setColumnWidth(3, 120)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)

        self.itemChanged.connect(self._on_item_changed)
        self._updating = False
        self._category_combos = []
        self._subcategory_combos = []
        self._sort_order = {}  # column -> Qt.AscendingOrder or Qt.DescendingOrder

    def load_sf2(self, instruments: list[dict]):
        """Populate table from instrument data."""
        self._updating = True
        self.setRowCount(0)
        self._category_combos = []
        self._subcategory_combos = []

        for row, info in enumerate(instruments):
            self.insertRow(row)

            # Name with checkbox
            name_item = QTableWidgetItem(info["name"])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            name_item.setCheckState(Qt.Unchecked)
            name_item.setData(Qt.UserRole, {"type": "instrument", "data": info})
            self.setItem(row, 0, name_item)

            # Zones (read-only)
            zones_item = QTableWidgetItem(str(info["zones"]))
            zones_item.setTextAlignment(Qt.AlignCenter)
            zones_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.setItem(row, 1, zones_item)

            # Category combo
            cat_combo = QComboBox()
            cat_combo.addItems(_CATEGORY_NAMES)
            cat_combo.setCurrentText("Dsynth")
            self.setCellWidget(row, 2, cat_combo)
            self._category_combos.append(cat_combo)

            # Subcategory combo
            sub_combo = QComboBox()
            sub_combo.addItems(get_subcategory_names("Dsynth"))
            if "Other" in get_subcategory_names("Dsynth"):
                sub_combo.setCurrentText("Other")
            self.setCellWidget(row, 3, sub_combo)
            self._subcategory_combos.append(sub_combo)

            cat_combo.currentTextChanged.connect(
                lambda cat, sc=sub_combo: self._update_subcategory_combo(cat, sc)
            )

        self._updating = False
        # Default sort by name A→Z
        self._on_header_clicked(0)

    def set_categories_visible(self, visible: bool):
        """Show or hide the per-instrument category and subcategory columns."""
        self.setColumnHidden(2, not visible)
        self.setColumnHidden(3, not visible)

    def _on_item_changed(self, item: QTableWidgetItem):
        """Handle checkbox state changes."""
        if self._updating:
            return
        if item.column() == 0:
            self.selection_changed.emit()

    def get_selected_instrument_indices(self) -> list[int]:
        """Return sorted list of selected instrument indices."""
        indices = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                data = item.data(Qt.UserRole)
                if data and data["type"] == "instrument":
                    indices.append(data["data"]["index"])
        return sorted(indices)

    @staticmethod
    def _update_subcategory_combo(category: str, sub_combo: QComboBox):
        """Repopulate a subcategory combo when its paired category changes."""
        sub_combo.clear()
        names = get_subcategory_names(category)
        if names:
            sub_combo.addItems(names)
            if "Other" in names:
                sub_combo.setCurrentText("Other")

    def get_category_map(self) -> tuple[dict[int, str], dict[int, str]]:
        """Return mappings of instrument index -> category and index -> subcategory."""
        cat_map = {}
        subcat_map = {}
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if not item:
                continue
            data = item.data(Qt.UserRole)
            if not data or data["type"] != "instrument":
                continue
            idx = data["data"]["index"]
            cat_combo = self.cellWidget(row, 2)
            sub_combo = self.cellWidget(row, 3)
            if cat_combo:
                cat_map[idx] = cat_combo.currentText()
            if sub_combo:
                subcat_map[idx] = sub_combo.currentText()
        return cat_map, subcat_map

    def get_selected_info(self) -> list[dict]:
        """Return info dicts for all selected instruments."""
        result = []
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                data = item.data(Qt.UserRole)
                if data and data["type"] == "instrument":
                    result.append(data["data"])
        return result

    def select_all(self):
        self._updating = True
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)
        self._updating = False
        self.selection_changed.emit()

    def select_none(self):
        self._updating = True
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)
        self._updating = False
        self.selection_changed.emit()

    def _on_header_clicked(self, column: int):
        """Sort rows when Name (0) or Zones (1) header is clicked."""
        if column > 1:
            return

        # Toggle sort order
        if column in self._sort_order:
            prev = self._sort_order[column]
            order = Qt.DescendingOrder if prev == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
        self._sort_order[column] = order
        self.horizontalHeader().setSortIndicator(column, order)

        # Gather all row data
        rows = []
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            if not name_item:
                continue
            cat_combo = self.cellWidget(row, 2)
            sub_combo = self.cellWidget(row, 3)
            rows.append({
                "name": name_item.text(),
                "check": name_item.checkState(),
                "user_data": name_item.data(Qt.UserRole),
                "zones": self.item(row, 1).text(),
                "category": cat_combo.currentText() if cat_combo else "Dsynth",
                "subcategory": sub_combo.currentText() if sub_combo else "Other",
            })

        # Sort
        reverse = order == Qt.DescendingOrder
        if column == 0:
            rows.sort(key=lambda r: r["name"].lower(), reverse=reverse)
        else:
            rows.sort(key=lambda r: int(r["zones"]) if r["zones"].isdigit() else 0, reverse=reverse)

        # Repopulate
        self._updating = True
        self._category_combos.clear()
        self._subcategory_combos.clear()

        for row, data in enumerate(rows):
            name_item = QTableWidgetItem(data["name"])
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            name_item.setCheckState(data["check"])
            name_item.setData(Qt.UserRole, data["user_data"])
            self.setItem(row, 0, name_item)

            zones_item = QTableWidgetItem(data["zones"])
            zones_item.setTextAlignment(Qt.AlignCenter)
            zones_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.setItem(row, 1, zones_item)

            cat_combo = QComboBox()
            cat_combo.addItems(_CATEGORY_NAMES)
            cat_combo.setCurrentText(data["category"])
            self.setCellWidget(row, 2, cat_combo)
            self._category_combos.append(cat_combo)

            sub_combo = QComboBox()
            sub_names = get_subcategory_names(data["category"])
            if sub_names:
                sub_combo.addItems(sub_names)
                sub_combo.setCurrentText(data["subcategory"])
            self.setCellWidget(row, 3, sub_combo)
            self._subcategory_combos.append(sub_combo)

            cat_combo.currentTextChanged.connect(
                lambda cat, sc=sub_combo: self._update_subcategory_combo(cat, sc)
            )

        self._updating = False
