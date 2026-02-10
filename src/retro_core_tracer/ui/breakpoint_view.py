# src/retro_core_tracer/ui/breakpoint_view.py
"""
ブレークポイントの管理UIウィジェット。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QMessageBox, QMenu
)
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt, Signal, Slot
from typing import List, Optional, Dict

from retro_core_tracer.debugger.debugger import BreakpointCondition, BreakpointConditionType
from retro_core_tracer.core.cpu import AbstractCpu

class BreakpointView(QWidget):
    """
    ブレークポイントの追加、削除、一覧表示を行うUIウィジェット。
    """
    breakpoint_added = Signal(BreakpointCondition)
    breakpoint_removed = Signal(BreakpointCondition)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.symbol_map: Dict[str, int] = {}
        self._cpu: Optional[AbstractCpu] = None

        add_form_layout = QGridLayout()
        add_form_layout.addWidget(QLabel("Type:"), 0, 0)
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(120)
        for bp_type in BreakpointConditionType:
            self.type_combo.addItem(bp_type.name, bp_type)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        add_form_layout.addWidget(self.type_combo, 0, 1)

        add_form_layout.addWidget(QLabel("Value/Addr/Reg:"), 0, 2)
        self.value_input = QLineEdit()
        add_form_layout.addWidget(self.value_input, 0, 3)
        
        self.add_button = QPushButton("Add Breakpoint")
        self.add_button.clicked.connect(self._add_breakpoint)
        add_form_layout.addWidget(self.add_button, 1, 0, 1, 4)

        self.layout.addLayout(add_form_layout)

        self.bp_list_widget = QListWidget()
        self.bp_list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.layout.addWidget(self.bp_list_widget)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._remove_selected_breakpoint)
        self.layout.addWidget(self.remove_button)

        self._on_type_changed(self.type_combo.currentIndex())
    
    def set_cpu(self, cpu: AbstractCpu):
        """MainWindowからの呼び出しに対応するためのメソッド"""
        self._cpu = cpu

    def set_symbol_map(self, symbol_map: Dict[str, int]):
        self.symbol_map = symbol_map

    @Slot(int)
    def _on_type_changed(self, index: int):
        selected_type = self.type_combo.itemData(index)
        self.value_input.setEnabled(True)
        self.value_input.setPlaceholderText(f"Enter {selected_type.name} criteria")

    def _resolve_value(self, value_str: str) -> Optional[int]:
        try:
            return int(value_str, 16) if value_str.startswith('0x') else int(value_str)
        except ValueError:
            return self.symbol_map.get(value_str)

    @Slot()
    def _add_breakpoint(self):
        bp_type = self.type_combo.currentData()
        value_str = self.value_input.text().strip()
        try:
            condition = None
            if bp_type == BreakpointConditionType.PC_MATCH:
                val = self._resolve_value(value_str)
                if val is not None: condition = BreakpointCondition(bp_type, value=val)
            elif bp_type == BreakpointConditionType.REGISTER_CHANGE:
                condition = BreakpointCondition(bp_type, register_name=value_str.upper())
            
            if condition:
                self.breakpoint_added.emit(condition)
                self.value_input.clear()
                # 簡易的にリストに追加（本来はDebuggerから通知を受けるべき）
                item = QListWidgetItem(str(condition))
                item.setData(Qt.UserRole, condition)
                self.bp_list_widget.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    @Slot()
    def _on_selection_changed(self):
        self.remove_button.setEnabled(len(self.bp_list_widget.selectedItems()) > 0)

    @Slot()
    def _remove_selected_breakpoint(self):
        items = self.bp_list_widget.selectedItems()
        if items:
            item = items[0]
            condition = item.data(Qt.UserRole)
            self.breakpoint_removed.emit(condition)
            self.bp_list_widget.takeItem(self.bp_list_widget.row(item))