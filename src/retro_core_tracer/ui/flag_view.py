# src/retro_core_tracer/ui/flag_view.py
"""
CPUのフラグを表示する汎用ウィジェット。
AbstractCpuのインターフェースを利用して動的にUIを構築します。
"""
from typing import Dict, Optional
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.ui.fonts import get_monospace_font_family

# @intent:responsibility CPUのフラグ状態を表示する汎用UIウィジェットを提供します。
class FlagView(QWidget):
    """
    CPUのフラグ状態を表示するウィジェット。
    AbstractCpuから取得した情報に基づいて動的にフィールドを生成します。
    """
    # @intent:responsibility FlagViewウィジェットを初期化します。
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Apply dark theme
        self.setStyleSheet("background-color: #121212; color: #BBBBBB;")
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        self._font_family = get_monospace_font_family()
        self._flag_labels: Dict[str, QLabel] = {}
        self._cpu: Optional[AbstractCpu] = None
        
        self.layout.addStretch(1) 

    # @intent:responsibility 表示対象のCPUを設定し、フラグレイアウトを初期化します。
    def set_cpu(self, cpu: AbstractCpu) -> None:
        self._cpu = cpu
        self._setup_flag_labels()
        
    # @intent:responsibility CPUから取得したフラグ情報に基づいてラベルを作成します。
    def _setup_flag_labels(self):
        # 既存のウィジェットをクリア
        while self.layout.count():
             item = self.layout.takeAt(0)
             if item.widget():
                 item.widget().deleteLater()

        self._flag_labels.clear()
        
        # フラグの初期状態を取得して、どのようなフラグが存在するかを把握する
        # 注: get_flag_stateは全てのフラグをキーとして含む辞書を返すことを想定
        flag_state = self._cpu.get_flag_state()
        
        for flag_name in flag_state.keys():
            label_name = QLabel(f"{flag_name}:")
            label_name.setStyleSheet("font-weight: bold; color: #BBBBBB;")
            
            label_value = QLabel("0")
            label_value.setStyleSheet(f"font-family: '{self._font_family}', monospace; color: #FFD700;")
            label_value.setFixedWidth(15)
            label_value.setAlignment(Qt.AlignCenter)
            
            self.layout.addWidget(label_name)
            self.layout.addWidget(label_value)
            self._flag_labels[flag_name] = label_value
            
        self.layout.addStretch(1)

    # @intent:responsibility 現在のCPU状態を取得し、フラグの表示を更新します。
    def update_flags(self):
        if not self._cpu:
            return

        flag_state = self._cpu.get_flag_state()
        for name, is_set in flag_state.items():
            if name in self._flag_labels:
                self._flag_labels[name].setText("1" if is_set else "0")

# Minimal test code
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    from retro_core_tracer.transport.bus import Bus, RAM
    from retro_core_tracer.arch.z80.cpu import Z80Cpu

    app = QApplication([])
    
    # Setup dummy backend for testing
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)

    # Create and show the widget in a dummy window
    main_win = QMainWindow()
    flag_view = FlagView()
    flag_view.set_cpu(cpu)
    
    main_win.setCentralWidget(flag_view)
    main_win.setWindowTitle("Generic Flag View Test (Z80)")
    main_win.show()

    # Simulate an update
    flag_view.update_flags()
    
    sys.exit(app.exec())