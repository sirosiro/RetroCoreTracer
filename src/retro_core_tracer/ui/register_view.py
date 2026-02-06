# src/retro_core_tracer/ui/register_view.py
"""
Z80 CPUのレジスタを表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLabel
from PySide6.QtCore import Qt

from retro_core_tracer.core.snapshot import Snapshot
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.ui.fonts import get_monospace_font_family

# @intent:responsibility Z80 CPUのレジスタ値を表示するUIウィジェットを提供します。
class RegisterView(QWidget):
    """
    Z80 CPUのレジスタ状態を表示するウィジェット。
    """
    # @intent:responsibility RegisterViewウィジェットを初期化し、レイアウトを設定します。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout(self)
        self.layout.setLabelAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        self._font_family = get_monospace_font_family()
        self._register_labels = {}
        self._setup_register_labels()

    # @intent:responsibility 表示する全てのレジスタラベルを作成し、レイアウトに配置します。
    def _setup_register_labels(self):
        # 16-bit registers
        self._create_register_row("PC", "Program Counter", 4)
        self._create_register_row("SP", "Stack Pointer", 4)
        self._create_register_row("AF", "Accumulator/Flags", 4)
        self._create_register_row("BC", "BC Register Pair", 4)
        self._create_register_row("DE", "DE Register Pair", 4)
        self._create_register_row("HL", "HL Register Pair", 4)
        self._create_register_row("IX", "Index X", 4)
        self._create_register_row("IY", "Index Y", 4)
        
        # 8-bit registers (individual) - mainly for completeness or debugging
        self.layout.addRow(QLabel(""), QLabel("")) # Spacer
        self._create_register_row("A", "Accumulator", 2)
        self._create_register_row("F", "Flags (8-bit)", 2)
        self._create_register_row("B", "B Register", 2)
        self._create_register_row("C", "C Register", 2)
        self._create_register_row("D", "D Register", 2)
        self._create_register_row("E", "E Register", 2)
        self._create_register_row("H", "H Register", 2)
        self._create_register_row("L", "L Register", 2)

        # Alternate registers
        self.layout.addRow(QLabel(""), QLabel("")) # Spacer
        self._create_register_row("AF'", "Alternate AF", 4)
        self._create_register_row("BC'", "Alternate BC", 4)
        self._create_register_row("DE'", "Alternate DE", 4)
        self._create_register_row("HL'", "Alternate HL", 4)
        
        # Special purpose
        self.layout.addRow(QLabel(""), QLabel("")) # Spacer
        self._create_register_row("I", "Interrupt Vector", 2)
        self._create_register_row("R", "Refresh Counter", 2)

    # @intent:responsibility 単一のレジスタ行（ラベルと値）を作成します。
    def _create_register_row(self, name: str, description: str, hex_width: int):
        label_name = QLabel(f"{name}:")
        label_name.setStyleSheet("font-weight: bold; color: #BBBBBB;")
        
        label_value = QLabel("0x" + "0" * hex_width)
        label_value.setStyleSheet(f"font-family: '{self._font_family}', monospace; color: #FFD700;") # Gold color
        label_value.setAlignment(Qt.AlignRight)
        
        self.layout.addRow(label_name, label_value)
        self._register_labels[name] = label_value

    # @intent:responsibility スナップショットに基づいてレジスタの表示値を更新します。
    def update_registers(self, snapshot: Snapshot):
        state: Z80CpuState = snapshot.state

        # Main registers
        self._update_label("PC", state.pc, 4)
        self._update_label("SP", state.sp, 4)
        self._update_label("AF", state.af, 4)
        self._update_label("BC", state.bc, 4)
        self._update_label("DE", state.de, 4)
        self._update_label("HL", state.hl, 4)
        self._update_label("IX", state.ix, 4)
        self._update_label("IY", state.iy, 4)
        
        self._update_label("A", state.a, 2)
        self._update_label("F", state.f, 2)
        self._update_label("B", state.b, 2)
        self._update_label("C", state.c, 2)
        self._update_label("D", state.d, 2)
        self._update_label("E", state.e, 2)
        self._update_label("H", state.h, 2)
        self._update_label("L", state.l, 2)

        # Alternate registers
        self._update_label("AF'", state.af_, 4)
        self._update_label("BC'", state.bc_, 4)
        self._update_label("DE'", state.de_, 4)
        self._update_label("HL'", state.hl_, 4)

        # Special purpose
        self._update_label("I", state.i, 2)
        self._update_label("R", state.r, 2)

    def _update_label(self, name: str, value: int, hex_width: int):
        if name in self._register_labels:
            self._register_labels[name].setText(f"0x{value:0{hex_width}X}")

# Minimal test code
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    from retro_core_tracer.transport.bus import Bus, RAM
    from retro_core_tracer.arch.z80.cpu import Z80Cpu
    from retro_core_tracer.debugger.debugger import Debugger

    app = QApplication([])
    
    # Setup dummy backend for testing
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)
    debugger = Debugger(cpu)

    # Create and show the widget
    view = RegisterView()
    view.setWindowTitle("Register View Test")
    view.show()

    # Simulate an update
    # You'd normally get this from debugger.step_instruction()
    # For a quick test, let's manually create a Z80CpuState and Snapshot
    test_state = Z80CpuState()
    test_state.pc = 0x1234
    test_state.sp = 0x5678
    test_state.a = 0xFF
    test_state.f = 0xCD # Example flags
    test_state.b = 0x11
    test_state.c = 0x22
    test_state.h = 0x33
    test_state.l = 0x44
    test_state.ix = 0xAABB
    test_state.iy = 0xCCDD
    test_state.i = 0x55
    test_state.r = 0xAA

    from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot
    dummy_operation = Operation(opcode_hex="00", mnemonic="NOP")
    dummy_metadata = Metadata(cycle_count=0)
    dummy_snapshot = Snapshot(state=test_state, operation=dummy_operation, metadata=dummy_metadata)

    view.update_registers(dummy_snapshot)

    sys.exit(app.exec())
