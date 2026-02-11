# src/retro_core_tracer/ui/breakpoint_view.py
"""
ブレークポイントの管理UIウィジェット。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, Signal, Slot
from typing import List, Optional, Dict
from dataclasses import replace

from retro_core_tracer.debugger.debugger import BreakpointCondition, BreakpointConditionType
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.ui.fonts import get_monospace_font

class BreakpointView(QWidget):
    """
    ブレークポイントの追加、削除、一覧表示を行うUIウィジェット。
    """
    breakpoint_added = Signal(BreakpointCondition)
    breakpoint_removed = Signal(BreakpointCondition)
    breakpoint_updated = Signal(BreakpointCondition, BreakpointCondition) # old, new

    def __init__(self, parent=None):
        super().__init__(parent)
        # 背景色をアプリケーション全体の黒(#121212)に合わせる
        self.setStyleSheet("background-color: #121212; color: #BBBBBB;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.symbol_map: Dict[str, int] = {}
        self.reverse_symbol_map: Dict[int, str] = {}
        self._cpu: Optional[AbstractCpu] = None

        # Input Area
        add_form_layout = QGridLayout()
        add_form_layout.addWidget(QLabel("Type:"), 0, 0)
        self.type_combo = QComboBox()
        self.type_combo.setMinimumWidth(120)
        self.type_combo.setStyleSheet("background-color: #252525; color: #EEE; border: 1px solid #444;")
        for bp_type in BreakpointConditionType:
            self.type_combo.addItem(bp_type.name, bp_type)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        add_form_layout.addWidget(self.type_combo, 0, 1)

        add_form_layout.addWidget(QLabel("Value/Addr/Reg:"), 0, 2)
        self.value_input = QLineEdit()
        self.value_input.setStyleSheet("background-color: #252525; color: #EEE; border: 1px solid #444;")
        add_form_layout.addWidget(self.value_input, 0, 3)
        
        self.add_button = QPushButton("Add Breakpoint")
        self.add_button.setStyleSheet("background-color: #333; color: #EEE; border: 1px solid #444; padding: 4px;")
        self.add_button.clicked.connect(self._add_breakpoint)
        add_form_layout.addWidget(self.add_button, 1, 0, 1, 4)

        self.layout.addLayout(add_form_layout)

        # Breakpoint List (Table)
        self.bp_table = QTableWidget()
        self.bp_table.setColumnCount(3)
        self.bp_table.setHorizontalHeaderLabels(["Type", "Condition", "Status"])
        self.bp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.bp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.bp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.bp_table.verticalHeader().setVisible(False)
        self.bp_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bp_table.setFont(get_monospace_font(10))
        # テーブル内背景も #121212 に
        self.bp_table.setStyleSheet("""
            QTableWidget { 
                background-color: #121212; 
                color: #BBBBBB; 
                gridline-color: #303030; 
                border: none;
            } 
            QHeaderView::section { 
                background-color: #252525; 
                color: #BBBBBB; 
                border: 1px solid #333;
            }
        """)
        
        self.bp_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.bp_table.cellDoubleClicked.connect(self._toggle_breakpoint)
        self.layout.addWidget(self.bp_table)

        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setStyleSheet("background-color: #333; color: #EEE; border: 1px solid #444; padding: 4px;")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._remove_selected_breakpoint)
        self.layout.addWidget(self.remove_button)

        self._on_type_changed(self.type_combo.currentIndex())
    
    def set_cpu(self, cpu: AbstractCpu):
        self._cpu = cpu
        if self._cpu:
            self.set_symbol_map(self._cpu.get_symbol_map())

    def set_symbol_map(self, symbol_map: Dict[str, int]):
        self.symbol_map = symbol_map
        self.reverse_symbol_map = {addr: name for name, addr in symbol_map.items()}
        print(f"DEBUG: BreakpointView symbol map updated with {len(symbol_map)} symbols.")

    @Slot(int)
    def _on_type_changed(self, index: int):
        selected_type = self.type_combo.itemData(index)
        self.value_input.setEnabled(True)
        self.value_input.setPlaceholderText(f"Enter criteria for {selected_type.name}")

    def _resolve_value(self, value_str: str) -> Optional[int]:
        value_str = value_str.strip()
        try:
            return int(value_str, 16) if value_str.lower().startswith('0x') or value_str.lower().startswith('$') else int(value_str)
        except ValueError:
            pass
        
        if value_str in self.symbol_map:
            return self.symbol_map[value_str]

        for name, addr in self.symbol_map.items():
            if name.lower() == value_str.lower():
                return addr

        if '*' in value_str or '?' in value_str:
            import re
            pattern = value_str.replace('*', '.*').replace('?', '.')
            try:
                regex = re.compile(f"^{pattern}$", re.IGNORECASE)
                for name, addr in self.symbol_map.items():
                    if regex.match(name):
                        return addr
            except re.error:
                pass
        return None

    @Slot()
    def _add_breakpoint(self):
        bp_type = self.type_combo.currentData()
        value_str = self.value_input.text().strip()
        if not value_str: return

        try:
            condition = None
            if bp_type == BreakpointConditionType.PC_MATCH:
                val = self._resolve_value(value_str)
                if val is not None: condition = BreakpointCondition(bp_type, value=val)
                else: raise ValueError(f"Undefined symbol: '{value_str}'")
            elif bp_type in [BreakpointConditionType.MEMORY_READ, BreakpointConditionType.MEMORY_WRITE]:
                val = self._resolve_value(value_str)
                if val is not None: condition = BreakpointCondition(bp_type, address=val)
                else: raise ValueError(f"Undefined symbol: '{value_str}'")
            elif bp_type == BreakpointConditionType.REGISTER_VALUE:
                if '=' in value_str:
                    reg, val_s = value_str.split('=', 1)
                    val = self._resolve_value(val_s)
                    if val is not None: condition = BreakpointCondition(bp_type, register_name=reg.strip().upper(), value=val)
                    else: raise ValueError(f"Invalid value: {val_s}")
                else: raise ValueError("Format must be REG=VAL")
            elif bp_type == BreakpointConditionType.REGISTER_CHANGE:
                condition = BreakpointCondition(bp_type, register_name=value_str.upper())
            
            if condition:
                self.breakpoint_added.emit(condition)
                self.value_input.clear()
                self._add_to_table(condition)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _add_to_table(self, condition: BreakpointCondition):
        row = self.bp_table.rowCount()
        self.bp_table.insertRow(row)
        
        type_item = QTableWidgetItem(condition.condition_type.name)
        
        details = ""
        if condition.value is not None:
            if condition.register_name:
                 details = f"{condition.register_name} == 0x{condition.value:X}"
            else:
                 sym = self.reverse_symbol_map.get(condition.value, "")
                 details = f"== 0x{condition.value:04X}" + (f" ({sym})" if sym else "")
        elif condition.address is not None:
            sym = self.reverse_symbol_map.get(condition.address, "")
            details = f"@ 0x{condition.address:04X}" + (f" ({sym})" if sym else "")
        elif condition.register_name:
            details = f"{condition.register_name} changed"
            
        details_item = QTableWidgetItem(details)
        status_item = QTableWidgetItem("Active" if condition.enabled else "Disabled")
        status_item.setForeground(Qt.green if condition.enabled else Qt.gray)
        
        type_item.setData(Qt.UserRole, condition)
        self.bp_table.setItem(row, 0, type_item)
        self.bp_table.setItem(row, 1, details_item)
        self.bp_table.setItem(row, 2, status_item)

    @Slot(int, int)
    def _toggle_breakpoint(self, row: int, col: int):
        item = self.bp_table.item(row, 0)
        old_condition = item.data(Qt.UserRole)
        new_condition = replace(old_condition, enabled=not old_condition.enabled)
        
        self.breakpoint_updated.emit(old_condition, new_condition)
        
        item.setData(Qt.UserRole, new_condition)
        status_item = self.bp_table.item(row, 2)
        status_item.setText("Active" if new_condition.enabled else "Disabled")
        status_item.setForeground(Qt.green if new_condition.enabled else Qt.gray)

    @Slot()
    def _on_selection_changed(self):
        self.remove_button.setEnabled(len(self.bp_table.selectedItems()) > 0)

    @Slot()
    def _remove_selected_breakpoint(self):
        rows = sorted(set(item.row() for item in self.bp_table.selectedItems()), reverse=True)
        for row in rows:
            item = self.bp_table.item(row, 0)
            condition = item.data(Qt.UserRole)
            self.breakpoint_removed.emit(condition)
            self.bp_table.removeRow(row)