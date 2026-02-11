from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from typing import Optional
from retro_core_tracer.config.models import SystemConfig
from retro_core_tracer.transport.bus import Bus
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
        self.table.setStyleSheet("QTableWidget { background-color: #121212; color: #BBBBBB; gridline-color: #303030; } QHeaderView::section { background-color: #252525; color: #BBBBBB; }")
        
        self.layout.addWidget(self.table)
        self._config: Optional[SystemConfig] = None
        self._bus: Optional[Bus] = None

    def set_config(self, config: SystemConfig, bus: Bus):
        """
        SystemConfigとBusを設定し、表示を更新します。
        """
        self._config = config
        self._bus = bus
        self.update_view()

    def update_view(self):
        """
        現在の設定に基づいてメモリマップ表示を更新します。
        """
        if not self._config:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(self._config.memory_map))
        
        # アドレス順にソートして表示
        sorted_map = sorted(self._config.memory_map, key=lambda x: x.start)
        
        for row, region in enumerate(sorted_map):
            range_str = f"{region.start:04X} - {region.end:04X}"
            
            self.table.setItem(row, 0, QTableWidgetItem(range_str))
            self.table.setItem(row, 1, QTableWidgetItem(region.type))
            self.table.setItem(row, 2, QTableWidgetItem(region.permissions))
            self.table.setItem(row, 3, QTableWidgetItem(region.label))

    def update_map(self, config: SystemConfig):
        """
        互換性のために残された旧メソッド。
        """
        self.set_config(config, self._bus)