from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt
from retro_core_tracer.config.models import SystemConfig, MemoryRegion
from retro_core_tracer.ui.fonts import get_monospace_font

class MemoryMapView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Range", "Type", "Permissions", "Label"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Range
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Type
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Perms
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)          # Label
        
        font = get_monospace_font(10)
        self.table.setFont(font)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("background-color: #101010; color: #BBBBBB; gridline-color: #303030;")
        
        self.layout.addWidget(self.table)

    def update_map(self, config: SystemConfig):
        """
        SystemConfigに基づいてメモリマップ表示を更新します。
        """
        self.table.setRowCount(len(config.memory_map))
        
        # Sort by start address
        sorted_map = sorted(config.memory_map, key=lambda x: x.start)
        
        for row, region in enumerate(sorted_map):
            range_str = f"{region.start:04X} - {region.end:04X}"
            
            self.table.setItem(row, 0, QTableWidgetItem(range_str))
            self.table.setItem(row, 1, QTableWidgetItem(region.type))
            self.table.setItem(row, 2, QTableWidgetItem(region.permissions))
            self.table.setItem(row, 3, QTableWidgetItem(region.label))
