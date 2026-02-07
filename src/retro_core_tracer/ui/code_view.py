"""
逆アセンブルコードを表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.z80.disassembler import disassemble
from retro_core_tracer.ui.fonts import get_monospace_font

# @intent:responsibility 逆アセンブルされたコードを表形式で表示し、現在のPCをハイライトするUIウィジェットを提供します。
class CodeView(QWidget):
    """
    逆アセンブルコードを表示するウィジェット。
    """
    # @intent:responsibility CodeViewウィジェットを初期化し、テーブルを設定します。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Address", "Bytes", "Mnemonic"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Address
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Bytes
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)          # Mnemonic
        
        # フォント設定
        font = get_monospace_font(10)
        self.table.setFont(font)
        
        # 行ヘッダ（番号）を隠す
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("background-color: #101010; color: #BBBBBB; gridline-color: #303030;")
        
        self.layout.addWidget(self.table)
        
        self.current_pc = -1
        self.cache_start_addr = -1
        self.cache_range = 64 # 表示するバイト数の範囲（前後）

    # @intent:responsibility 指定されたPC周辺のメモリを逆アセンブルして表示を更新します。
    def update_code(self, bus: Bus, pc: int):
        """
        現在のPC周辺のコードを逆アセンブルして表示します。
        """
        # 簡易的な実装: PCが変わるたびに再描画するが、スクロール位置を維持したい
        # 今回はPCを中心に前後を表示する
        
        # 表示範囲の決定 (PCの少し前から)
        # 正確に「命令の区切り」で戻るのは難しいので、簡易的に PC から少し先までを表示し、
        # 必要に応じてスクロールさせる戦略をとる。
        # ここではシンプルに PC から 128バイト分を表示する。
        
        start_addr = pc
        length = 128
        
        disassembled_lines = disassemble(bus, start_addr, length)
        
        self.table.setRowCount(len(disassembled_lines))
        
        for row, (addr, hex_dump, mnemonic) in enumerate(disassembled_lines):
            addr_item = QTableWidgetItem(f"{addr:04X}")
            hex_item = QTableWidgetItem(hex_dump)
            mnemonic_item = QTableWidgetItem(mnemonic)
            
            # ハイライト (現在のPCの行)
            if addr == pc:
                bg_color = QColor("#404000") # Dark Yellow
                addr_item.setBackground(bg_color)
                hex_item.setBackground(bg_color)
                mnemonic_item.setBackground(bg_color)
            
            self.table.setItem(row, 0, addr_item)
            self.table.setItem(row, 1, hex_item)
            self.table.setItem(row, 2, mnemonic_item)
