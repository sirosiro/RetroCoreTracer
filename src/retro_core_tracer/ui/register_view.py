# src/retro_core_tracer/ui/register_view.py
"""
CPUのレジスタを表示する汎用ウィジェット。
AbstractCpuのメタデータを利用して動的にUIを構築します。
"""
from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox
from PySide6.QtCore import Qt

from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.ui.fonts import get_monospace_font_family

# @intent:responsibility CPUのレジスタ値を表示する汎用UIウィジェットを提供します。
class RegisterView(QWidget):
    """
    CPUのレジスタ状態を表示するウィジェット。
    AbstractCpuから取得したレイアウト情報に基づいて動的にフィールドを生成します。
    """
    # @intent:responsibility RegisterViewウィジェットを初期化します。
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Apply dark theme
        self.setStyleSheet("background-color: #121212; color: #BBBBBB;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self._font_family = get_monospace_font_family()
        self._register_labels: Dict[str, QLabel] = {}
        self._register_widths: Dict[str, int] = {}
        self._cpu: Optional[AbstractCpu] = None

    # @intent:responsibility 表示対象のCPUを設定し、UIレイアウトを構築します。
    def set_cpu(self, cpu: AbstractCpu) -> None:
        self._cpu = cpu
        self._setup_ui()
    
    # @intent:responsibility CPUから取得したレイアウト情報に基づいてUIを構築します。
    def _setup_ui(self):
        # 既存のウィジェットをクリア
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._register_labels.clear()
        self._register_widths.clear()

        layout_info = self._cpu.get_register_layout()
        
        for group in layout_info:
            group_box = QGroupBox(group.group_name)
            # border: none にしつつ、タイトル分のスペースを確保
            group_box.setStyleSheet("""
                QGroupBox { 
                    font-weight: bold; 
                    border: 1px solid #222; 
                    border-radius: 4px;
                    margin-top: 20px; 
                    color: #EEE; 
                    background-color: #121212;
                } 
                QGroupBox::title { 
                    subcontrol-origin: margin; 
                    subcontrol-position: top left; 
                    padding: 0 5px; 
                    left: 10px;
                    color: #00AAAA;
                }
            """)
            group_layout = QFormLayout(group_box)
            group_layout.setLabelAlignment(Qt.AlignLeft)
            group_layout.setContentsMargins(10, 15, 10, 10)
            group_layout.setSpacing(5)
            
            for reg in group.registers:
                hex_width = (reg.width + 3) // 4 # 16bit -> 4chars, 8bit -> 2chars
                self._register_widths[reg.name] = hex_width
                
                label_name = QLabel(f"{reg.name}:")
                label_name.setStyleSheet("font-weight: bold; color: #BBBBBB;")
                
                label_value = QLabel(f"0x{'0'*hex_width}")
                label_value.setStyleSheet(f"font-family: '{self._font_family}', monospace; color: #FFD700;") # Gold color
                label_value.setAlignment(Qt.AlignRight)
                
                group_layout.addRow(label_name, label_value)
                self._register_labels[reg.name] = label_value
            
            self.layout.addWidget(group_box)
        
        self.layout.addStretch()

    # @intent:responsibility 現在のCPU状態を取得し、レジスタの表示値を更新します。
    def update_registers(self):
        if not self._cpu:
            return
        
        reg_map = self._cpu.get_register_map()
        for name, value in reg_map.items():
            if name in self._register_labels:
                width = self._register_widths[name]
                self._register_labels[name].setText(f"0x{value:0{width}X}")

# Minimal test code
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    from retro_core_tracer.transport.bus import Bus, RAM
    from retro_core_tracer.arch.z80.cpu import Z80Cpu
    
    app = QApplication([])
    
    # Setup dummy backend for testing
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)
    
    # Create and show the widget
    view = RegisterView()
    view.setWindowTitle("Generic Register View Test (Z80)")
    view.set_cpu(cpu)
    view.show()

    # Test update
    view.update_registers()

    sys.exit(app.exec())