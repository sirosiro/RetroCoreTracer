# src/retro_core_tracer/ui/stack_view.py
"""
Z80 CPUのスタックの内容を表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor, QTextOption
from PySide6.QtCore import Qt
from typing import Optional

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.ui.fonts import get_monospace_font

# @intent:responsibility スタックメモリの内容を可視化するUIウィジェットを提供します。
class StackView(QWidget):
    """
    Z80 CPUのスタックの内容をHEXダンプ形式で表示するウィジェット。
    """
    # @intent:responsibility StackViewウィジェットを初期化します。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QPlainTextEdit(self)
        self.editor.setFont(get_monospace_font(10))
        self.editor.setReadOnly(True)
        self.editor.setWordWrapMode(QTextOption.NoWrap)
        self.editor.setStyleSheet("background-color: #101010; color: #BBBBBB;")
        self.layout.addWidget(self.editor)

    # @intent:responsibility 現在のスタックポインタ(SP)周辺のメモリを読み込み、表示を更新します。
    def update_stack(self, bus: Bus, sp_address: int):
        """
        指定されたスタックポインタ(SP)のアドレスを中心に、スタックの内容を表示します。
        """
        stack_dump_text = []
        bytes_per_row = 16
        # Display 8 rows above and 8 rows below SP, for a total of 16 rows (256 bytes)
        display_rows = 16
        display_bytes = bytes_per_row * display_rows
        
        # Calculate start address for display, aligning to row boundary
        # Ensure SP is roughly in the middle of the display
        display_start_address = sp_address - (bytes_per_row * (display_rows // 2))
        display_start_address = max(0, display_start_address - (display_start_address % bytes_per_row))
        display_end_address = display_start_address + display_bytes


        current_address = display_start_address
        while current_address < display_end_address:
            hex_part = []
            ascii_part = []
            
            for i in range(bytes_per_row):
                addr = current_address + i
                if addr >= 0xFFFF + 1 or addr < 0: # Z80 64KB address space
                    hex_part.append("XX")
                    ascii_part.append(".")
                else:
                    try:
                        # ログを汚さないようにpeekを使用
                        byte_val = bus.peek(addr)
                        hex_part.append(f"{byte_val:02X}")
                        ascii_part.append(chr(byte_val) if 32 <= byte_val <= 126 else '.')
                    except IndexError: # If bus.peek goes out of bounds
                        hex_part.append("XX")
                        ascii_part.append(".")
            
            line = f"{current_address:04X}: {' '.join(hex_part).ljust(bytes_per_row * 3 - 1)} {(''.join(ascii_part)).ljust(bytes_per_row)}"
            stack_dump_text.append(line)
            current_address += bytes_per_row

        self.editor.setPlainText("\n".join(stack_dump_text))

        # Highlight the line containing the SP address
        if sp_address is not None:
            cursor = self.editor.textCursor()
            line_to_highlight = (sp_address - display_start_address) // bytes_per_row
            
            if 0 <= line_to_highlight < len(stack_dump_text):
                cursor.movePosition(QTextCursor.Start)
                cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_to_highlight)
                cursor.select(QTextCursor.BlockUnderCursor)
                
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#404000")) # Dark yellow/gold background
                cursor.mergeCharFormat(fmt)

                self.editor.setTextCursor(cursor)
                self.editor.ensureCursorVisible() # Ensure the highlighted line is visible

# Minimal test code
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    from retro_core_tracer.transport.bus import Bus, RAM
    from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot
    from retro_core_tracer.arch.z80.cpu import Z80CpuState

    app = QApplication([])
    
    # Setup dummy bus for testing
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    
    # Write some test data to simulate stack
    for i in range(0xFF00, 0xFF10):
        bus.write(i, i % 256)

    sp = 0xFF08 # Simulate stack pointer
    
    # Create and show the widget in a dummy window
    main_win = QMainWindow()
    stack_view = StackView()
    main_win.setCentralWidget(stack_view)
    main_win.setWindowTitle("Stack View Test")
    main_win.setGeometry(100, 100, 800, 600)
    main_win.show()

    # Initial update
    stack_view.update_stack(bus, sp) 
    
    sys.exit(app.exec())
