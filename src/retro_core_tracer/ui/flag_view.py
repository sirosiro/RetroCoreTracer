# src/retro_core_tracer/ui/flag_view.py
"""
Z80 CPUのフラグを表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from retro_core_tracer.core.snapshot import Snapshot
from retro_core_tracer.arch.z80.state import Z80CpuState, S_FLAG, Z_FLAG, H_FLAG, PV_FLAG, N_FLAG, C_FLAG
from retro_core_tracer.ui.fonts import get_monospace_font_family

# @intent:responsibility Z80 CPUのフラグ状態を表示するUIウィジェットを提供します。
class FlagView(QWidget):
    """
    Z80 CPUのフラグ状態を表示するウィジェット。
    """
    # @intent:responsibility FlagViewウィジェットを初期化し、レイアウトを設定します。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15) # Increased spacing for better readability

        self._font_family = get_monospace_font_family()
        self._flag_labels = {}
        self._setup_flag_labels()
        
        # Add a spacer to push flags to the left
        self.layout.addStretch(1) 

    # @intent:responsibility フラグラベルを作成し、レイアウトに配置します。
    def _setup_flag_labels(self):
        # Z80 flags and their corresponding bit masks/properties
        flags_info = [
            ("S", "Sign", S_FLAG),
            ("Z", "Zero", Z_FLAG),
            ("H", "Half Carry", H_FLAG),
            ("PV", "Parity/Overflow", PV_FLAG),
            ("N", "Add/Subtract", N_FLAG),
            ("C", "Carry", C_FLAG),
        ]

        for flag_name, flag_description, _ in flags_info:
            label_name = QLabel(f"{flag_name}:")
            label_name.setStyleSheet("font-weight: bold; color: #BBBBBB;")
            
            label_value = QLabel("0") # Initial value
            label_value.setStyleSheet(f"font-family: '{self._font_family}', monospace; color: #FFD700;")
            label_value.setFixedWidth(15) # Make it small
            label_value.setAlignment(Qt.AlignCenter)
            
            self.layout.addWidget(label_name)
            self.layout.addWidget(label_value)
            self._flag_labels[flag_name] = label_value

    # @intent:responsibility スナップショットに基づいてフラグの表示状態を更新します。
    def update_flags(self, snapshot: Snapshot):
        state: Z80CpuState = snapshot.state

        self._flag_labels["S"].setText("1" if state.flag_s else "0")
        self._flag_labels["Z"].setText("1" if state.flag_z else "0")
        self._flag_labels["H"].setText("1" if state.flag_h else "0")
        self._flag_labels["PV"].setText("1" if state.flag_pv else "0")
        self._flag_labels["N"].setText("1" if state.flag_n else "0")
        self._flag_labels["C"].setText("1" if state.flag_c else "0")

# Minimal test code
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    from retro_core_tracer.transport.bus import Bus, RAM
    from retro_core_tracer.arch.z80.cpu import Z80Cpu
    from retro_core_tracer.debugger.debugger import Debugger
    from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot

    app = QApplication([])
    
    # Setup dummy backend for testing
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)
    debugger = Debugger(cpu)

    # Create and show the widget in a dummy window
    main_win = QMainWindow()
    flag_view = FlagView()
    main_win.setCentralWidget(flag_view)
    main_win.setWindowTitle("Flag View Test")
    main_win.show()

    # Simulate an update with some flags set
    test_state_1 = Z80CpuState()
    test_state_1.f = S_FLAG | Z_FLAG | C_FLAG # S, Z, C flags set
    dummy_operation = Operation(opcode_hex="00", mnemonic="NOP")
    dummy_metadata = Metadata(cycle_count=0)
    dummy_snapshot_1 = Snapshot(state=test_state_1, operation=dummy_operation, metadata=dummy_metadata)
    flag_view.update_flags(dummy_snapshot_1)

    # Simulate another update after a few seconds
    def update_test():
        test_state_2 = Z80CpuState()
        test_state_2.f = H_FLAG | PV_FLAG | N_FLAG # H, PV, N flags set
        dummy_snapshot_2 = Snapshot(state=test_state_2, operation=dummy_operation, metadata=dummy_metadata)
        flag_view.update_flags(dummy_snapshot_2)
    
    from PySide6.QtCore import QTimer
    QTimer.singleShot(2000, update_test) # Update after 2 seconds

    sys.exit(app.exec())
