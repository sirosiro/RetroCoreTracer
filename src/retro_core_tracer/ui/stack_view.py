# src/retro_core_tracer/ui/stack_view.py
"""
CPUのスタックの内容を表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor, QTextOption
from typing import Optional

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.ui.fonts import get_monospace_font

# @intent:responsibility スタックメモリの内容を可視化するUIウィジェットを提供します。
class StackView(QWidget):
    """
    CPUのスタックの内容をHEXダンプ形式で表示するウィジェット。
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
        self.editor.setStyleSheet("background-color: #121212; color: #BBBBBB;")
        self.layout.addWidget(self.editor)
        
        self._cpu: Optional[AbstractCpu] = None
        self._bus: Optional[Bus] = None

    # @intent:responsibility 表示対象のCPUとバスを設定します。
    def set_cpu(self, cpu: AbstractCpu, bus: Bus):
        self._cpu = cpu
        self._bus = bus
        self.update_view()

    # @intent:responsibility 現在のスタックポインタ(SP)周辺のメモリを読み込み、表示を更新します。
    def update_view(self):
        """
        現在のSP周辺のスタックを表示します。
        """
        if not self._cpu or not self._bus:
            return
            
        sp_address = self._cpu.get_state().sp
        
        stack_dump_text = []
        bytes_per_row = 16
        display_rows = 16
        display_bytes = bytes_per_row * display_rows
        
        # SPを中心に表示範囲を決定
        display_start_address = sp_address - (bytes_per_row * (display_rows // 2))
        display_start_address = max(0, display_start_address - (display_start_address % bytes_per_row))
        display_end_address = display_start_address + display_bytes

        current_address = display_start_address
        while current_address < display_end_address:
            hex_part = []
            ascii_part = []
            
            for i in range(bytes_per_row):
                addr = current_address + i
                if addr > 0xFFFF or addr < 0:
                    hex_part.append("XX")
                    ascii_part.append(".")
                else:
                    try:
                        byte_val = self._bus.peek(addr)
                        hex_part.append(f"{byte_val:02X}")
                        ascii_part.append(chr(byte_val) if 32 <= byte_val <= 126 else '.')
                    except IndexError:
                        hex_part.append("XX")
                        ascii_part.append(".")
            
            line = f"{current_address:04X}: {" ".join(hex_part).ljust(bytes_per_row * 3 - 1)} {("".join(ascii_part)).ljust(bytes_per_row)}"
            stack_dump_text.append(line)
            current_address += bytes_per_row

        self.editor.setPlainText("\n".join(stack_dump_text))

        # SPの行をハイライト
        cursor = self.editor.textCursor()
        line_to_highlight = (sp_address - display_start_address) // bytes_per_row
        
        if 0 <= line_to_highlight < len(stack_dump_text):
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_to_highlight)
            cursor.select(QTextCursor.BlockUnderCursor)
            
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#404000")) 
            cursor.mergeCharFormat(fmt)

            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()