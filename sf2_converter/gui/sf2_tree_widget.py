"""Tree widget for displaying SF2 SoundFont contents with checkboxes."""

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QComboBox
from PySide6.QtCore import Qt, Signal

from ..utils.naming import CATEGORIES

_CATEGORY_NAMES = list(CATEGORIES.keys())


class SF2TreeWidget(QTreeWidget):
    """Displays SF2 presets/instruments/samples in a tree with checkboxes."""

    selection_changed = Signal()  # Emitted when checked items change

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Name", "Zones", "Category"])
        self.setColumnWidth(0, 280)
        self.setColumnWidth(1, 50)
        self.setColumnWidth(2, 90)
        self.itemChanged.connect(self._on_item_changed)
        self._updating = False
        self._category_combos = []  # Track all combo boxes for show/hide

    def load_sf2(self, presets: list[dict], instruments: list[dict]):
        """Populate tree from SF2 reader data."""
        self._updating = True
        self.clear()
        self._category_combos = []

        # Build instrument lookup
        inst_by_name = {}
        for info in instruments:
            inst_by_name[info["name"]] = info

        # Add presets with their instruments (deduplicated)
        used_instruments = set()
        for preset in presets:
            preset_item = QTreeWidgetItem(self)
            preset_item.setText(0, f"[{preset['bank']:03d}:{preset['program']:03d}] {preset['name']}")
            preset_item.setFlags(preset_item.flags() | Qt.ItemIsUserCheckable)
            preset_item.setCheckState(0, Qt.Unchecked)
            preset_item.setData(0, Qt.UserRole, {"type": "preset", "data": preset})

            # Add category combo for this preset
            combo = QComboBox()
            combo.addItems(_CATEGORY_NAMES)
            combo.setCurrentText("Dsynth")
            self.setItemWidget(preset_item, 2, combo)
            self._category_combos.append(combo)

            # Deduplicate instruments within this preset
            seen_in_preset = set()
            for inst_name in preset["instruments"]:
                if inst_name in inst_by_name and inst_name not in seen_in_preset:
                    seen_in_preset.add(inst_name)
                    info = inst_by_name[inst_name]
                    used_instruments.add(inst_name)
                    inst_item = QTreeWidgetItem(preset_item)
                    inst_item.setText(0, info["name"])
                    inst_item.setText(1, str(info["zones"]))
                    inst_item.setFlags(inst_item.flags() | Qt.ItemIsUserCheckable)
                    inst_item.setCheckState(0, Qt.Unchecked)
                    inst_item.setData(0, Qt.UserRole, {"type": "instrument", "data": info})

        # Add any instruments not referenced by presets
        unreferenced = [i for i in instruments if i["name"] not in used_instruments]
        if unreferenced:
            other_item = QTreeWidgetItem(self)
            other_item.setText(0, "(Unreferenced Instruments)")
            other_item.setFlags(other_item.flags() | Qt.ItemIsUserCheckable)
            other_item.setCheckState(0, Qt.Unchecked)

            combo = QComboBox()
            combo.addItems(_CATEGORY_NAMES)
            combo.setCurrentText("Dsynth")
            self.setItemWidget(other_item, 2, combo)
            self._category_combos.append(combo)

            for info in unreferenced:
                inst_item = QTreeWidgetItem(other_item)
                inst_item.setText(0, info["name"])
                inst_item.setText(1, str(info["zones"]))
                inst_item.setFlags(inst_item.flags() | Qt.ItemIsUserCheckable)
                inst_item.setCheckState(0, Qt.Unchecked)
                inst_item.setData(0, Qt.UserRole, {"type": "instrument", "data": info})

        self.expandAll()
        self._updating = False

    def set_categories_visible(self, visible: bool):
        """Show or hide the per-preset category selectors."""
        for combo in self._category_combos:
            combo.setVisible(visible)
        if visible:
            self.setColumnWidth(2, 90)
        else:
            self.setColumnWidth(2, 0)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle checkbox state changes - propagate to children."""
        if self._updating or column != 0:
            return

        self._updating = True
        state = item.checkState(0)

        # Propagate to children
        for i in range(item.childCount()):
            item.child(i).setCheckState(0, state)

        # Update parent state based on children
        parent = item.parent()
        if parent is not None:
            checked = sum(
                1 for i in range(parent.childCount())
                if parent.child(i).checkState(0) == Qt.Checked
            )
            if checked == 0:
                parent.setCheckState(0, Qt.Unchecked)
            elif checked == parent.childCount():
                parent.setCheckState(0, Qt.Checked)
            else:
                parent.setCheckState(0, Qt.PartiallyChecked)

        self._updating = False
        self.selection_changed.emit()

    def get_selected_instrument_indices(self) -> list[int]:
        """Return sorted list of selected instrument indices."""
        indices = set()
        self._collect_checked_indices(self.invisibleRootItem(), indices)
        return sorted(indices)

    def _collect_checked_indices(self, item: QTreeWidgetItem, indices: set):
        """Recursively collect checked instrument indices."""
        for i in range(item.childCount()):
            child = item.child(i)
            data = child.data(0, Qt.UserRole)
            if data and data["type"] == "instrument":
                if child.checkState(0) == Qt.Checked:
                    indices.add(data["data"]["index"])
            self._collect_checked_indices(child, indices)

    def get_category_map(self) -> dict[int, str]:
        """Return a mapping of instrument index -> category from the combo boxes.

        Each instrument inherits the category from its parent preset item.
        """
        cat_map = {}
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            combo = self.itemWidget(parent, 2)
            if combo is None:
                continue
            category = combo.currentText()
            # Apply to all child instruments
            for j in range(parent.childCount()):
                child = parent.child(j)
                data = child.data(0, Qt.UserRole)
                if data and data["type"] == "instrument":
                    cat_map[data["data"]["index"]] = category
        return cat_map

    def get_selected_info(self) -> list[dict]:
        """Return info dicts for all selected instruments."""
        result = []
        indices = self.get_selected_instrument_indices()
        self._collect_checked_info(self.invisibleRootItem(), indices, result)
        return result

    def _collect_checked_info(self, item: QTreeWidgetItem, indices: set, result: list):
        for i in range(item.childCount()):
            child = item.child(i)
            data = child.data(0, Qt.UserRole)
            if data and data["type"] == "instrument" and data["data"]["index"] in indices:
                if data["data"] not in result:
                    result.append(data["data"])
            self._collect_checked_info(child, indices, result)

    def select_all(self):
        self._updating = True
        self._set_all_checked(self.invisibleRootItem(), Qt.Checked)
        self._updating = False
        self.selection_changed.emit()

    def select_none(self):
        self._updating = True
        self._set_all_checked(self.invisibleRootItem(), Qt.Unchecked)
        self._updating = False
        self.selection_changed.emit()

    def _set_all_checked(self, item: QTreeWidgetItem, state):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_all_checked(child, state)
