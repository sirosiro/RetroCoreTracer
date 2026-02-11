# src/retro_core_tracer/ui/hex_view.py
"""
メモリの内容を16進数とASCIIで表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtGui import QTextCharFormat, QTextCursor, QColor, QTextOption
from typing import Optional

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.ui.fonts import get_monospace_font

# @intent:responsibility メモリの内容を16進数とASCII形式で表示するUIウィジェットを提供します。
class HexView(QWidget):
    """
    メモリの内容を16進数とASCIIで表示するウィジェット。
    """
    # @intent:responsibility HexViewウィジェットを初期化し、テキストエディタを設定します。
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
        
        self._bus: Optional[Bus] = None
        self._last_pc: Optional[int] = None

    # @intent:responsibility 表示対象のバスを設定します。
    def set_bus(self, bus: Bus):
        self._bus = bus
        self.update_view()

    # @intent:responsibility 現在のバスの状態に基づいて表示を更新します。
    def update_view(self, highlight_address: Optional[int] = None):
        """
        全メモリ範囲（現状は簡易的に0x0000-0x2000）を読み込み、表示を更新します。
        highlight_addressが指定されていない場合は、前回のハイライト位置または先頭を表示します。
        """
        if not self._bus:
            return

        if highlight_address is not None:
            self._last_pc = highlight_address
        
        hex_dump_text = []
        bytes_per_row = 16
        
        # 将来的にはスクロール位置に応じた遅延ロードが必要だが、
        # 現在は固定範囲を表示
        display_start_address = 0x0000
        display_end_address = 0x2000 

        current_address = display_start_address
        while current_address < display_end_address:
            hex_part = []
            ascii_part = []
            
            for i in range(bytes_per_row):
                addr = current_address + i
                if addr > 0xFFFF:
                    break
                try:
                    byte_val = self._bus.peek(addr)
                    hex_part.append(f"{byte_val:02X}")
                    ascii_part.append(chr(byte_val) if 32 <= byte_val <= 126 else '.')
                except IndexError:
                    hex_part.append("XX")
                    ascii_part.append(".")
            
            line = f"{current_address:04X}: {' '.join(hex_part).ljust(bytes_per_row * 3 - 1)} {(''.join(ascii_part)).ljust(bytes_per_row)}"
            hex_dump_text.append(line)
            current_address += bytes_per_row

        self.editor.setPlainText("\n".join(hex_dump_text))

        # ハイライトとスクロール
        target_pc = self._last_pc if self._last_pc is not None else 0x0000
        
        cursor = self.editor.textCursor()
        line_to_highlight = (target_pc - display_start_address) // bytes_per_row
        
        if 0 <= line_to_highlight < len(hex_dump_text):
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_to_highlight)
            
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#404000")) 
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.mergeCharFormat(fmt)

            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()