# src/retro_core_tracer/ui/hex_view.py
"""
メモリの内容を16進数とASCIIで表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QColor, QTextOption
from PySide6.QtCore import Qt
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
        self.layout.setContentsMargins(0, 0, 0, 0) # No margins
        self.editor = QPlainTextEdit(self)
        self.editor.setFont(get_monospace_font(10))
        self.editor.setReadOnly(True)
        self.editor.setWordWrapMode(QTextOption.NoWrap) # Disable word wrap
        self.editor.setStyleSheet("background-color: #101010; color: #BBBBBB;")
        self.layout.addWidget(self.editor)

    # @intent:responsibility 指定されたメモリ範囲を読み込み、表示を更新します。特定のアドレスをハイライトすることも可能です。
    def update_memory(self, bus: Bus, start_address: int, length: int, highlight_address: Optional[int] = None):
        """
        指定されたアドレス範囲のメモリ内容を読み込み、16進数とASCIIで表示します。
        highlight_addressが指定された場合、そのアドレスに対応する行をハイライトします。
        """
        hex_dump_text = []
        bytes_per_row = 16

        # 表示範囲を広げる（例: 全64KBを表示してスクロール可能にする）
        # ただし、パフォーマンスのため、一度に全て読み込むのではなく、表示を維持しつつ更新する工夫が必要
        # ここではまず、要件である 0x1000 が見えるように表示範囲を 0x2000 (8KB) まで広げます。
        display_start_address = 0x0000
        display_end_address = 0x2000 # 暫定的に 8KB 分を表示

        current_address = display_start_address
        while current_address < display_end_address:
            # 1行分のデータを取得
            hex_part = []
            ascii_part = []
            
            for i in range(bytes_per_row):
                addr = current_address + i
                if addr >= 0xFFFF + 1: # Z80 64KB address space
                    break
                try:
                    # ログを汚さないようにpeekを使用
                    byte_val = bus.peek(addr)
                    hex_part.append(f"{byte_val:02X}")
                    ascii_part.append(chr(byte_val) if 32 <= byte_val <= 126 else '.')
                except IndexError:
                    hex_part.append("XX")
                    ascii_part.append(".")
            
            # 1行のテキストを生成
            line = f"{current_address:04X}: {' '.join(hex_part).ljust(bytes_per_row * 3 - 1)} {(''.join(ascii_part)).ljust(bytes_per_row)}"
            hex_dump_text.append(line)
            current_address += bytes_per_row

        self.editor.setPlainText("\n".join(hex_dump_text))

        # PC位置のハイライトとスクロール制御
        if highlight_address is not None:
            cursor = self.editor.textCursor()
            line_to_highlight = (highlight_address - display_start_address) // bytes_per_row
            
            if 0 <= line_to_highlight < len(hex_dump_text):
                cursor.movePosition(QTextCursor.Start)
                cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_to_highlight)
                
                # ハイライトの適用
                fmt = QTextCharFormat()
                fmt.setBackground(QColor("#404000")) 
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.mergeCharFormat(fmt)

                # 表示位置の調整
                # ユーザーが自由にスクロールしている最中にPCが変わっても、
                # 強制的にジャンプさせすぎないように editor.ensureCursorVisible() を使用。
                self.editor.setTextCursor(cursor)
                self.editor.ensureCursorVisible()
# Minimal test code
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    from retro_core_tracer.transport.bus import Bus, RAM
    from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot
    from retro_core_tracer.arch.z80.cpu import Z80CpuState # For dummy snapshot

    app = QApplication([])
    
    # Setup dummy bus for testing
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    
    # Write some test data
    for i in range(256):
        bus.write(0x100 + i, i % 256)
    bus.write(0x110, ord('H'))
    bus.write(0x111, ord('e'))
    bus.write(0x112, ord('l'))
    bus.write(0x113, ord('l'))
    bus.write(0x114, ord('o'))
    bus.write(0x115, ord(' '))
    bus.write(0x116, ord('W'))
    bus.write(0x117, ord('o'))
    bus.write(0x118, ord('r'))
    bus.write(0x119, ord('l'))
    bus.write(0x11A, ord('d'))


    # Create and show the widget in a dummy window
    main_win = QMainWindow()
    hex_view = HexView()
    main_win.setCentralWidget(hex_view)
    main_win.setWindowTitle("Hex View Test")
    main_win.setGeometry(100, 100, 800, 600)
    main_win.show()

    # Initial update
    hex_view.update_memory(bus, 0x0000, 512, highlight_address=0x100) # Highlight address 0x100
    
    # Simulate a PC move after a few seconds
    # from PySide6.QtCore import QTimer
    # QTimer.singleShot(2000, lambda: hex_view.update_memory(bus, 0x0000, 512, highlight_address=0x150))

    sys.exit(app.exec())
