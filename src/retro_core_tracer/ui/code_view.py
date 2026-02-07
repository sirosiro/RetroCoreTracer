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
        
        # 現在表示している逆アセンブルデータ [(addr, hex, mnemonic), ...]
        self.disassembled_data = []

    # @intent:responsibility 指定されたPC周辺のメモリを逆アセンブルして表示を更新します。
    def update_code(self, bus: Bus, pc: int):
        """
        現在のPC周辺のコードを逆アセンブルして表示します。
        PCが現在の表示範囲内にあれば、再描画せずにハイライト移動のみ行います。
        """
        # 現在のデータ内にPCが含まれているかチェック
        pc_in_range = False
        row_index = -1
        
        for i, (addr, _, _) in enumerate(self.disassembled_data):
            if addr == pc:
                pc_in_range = True
                row_index = i
                break
        
        # PCが範囲外、またはデータが空の場合は再逆アセンブル（リフレッシュ）
        if not pc_in_range:
            start_addr = pc
            length = 4096 # 表示範囲を4KBに拡大（約1000〜4000命令分）
            
            self.disassembled_data = disassemble(bus, start_addr, length)
            
            self.table.setRowCount(len(self.disassembled_data))
            
            for row, (addr, hex_dump, mnemonic) in enumerate(self.disassembled_data):
                addr_item = QTableWidgetItem(f"{addr:04X}")
                hex_item = QTableWidgetItem(hex_dump)
                mnemonic_item = QTableWidgetItem(mnemonic)
                
                self.table.setItem(row, 0, addr_item)
                self.table.setItem(row, 1, hex_item)
                self.table.setItem(row, 2, mnemonic_item)
                
                if addr == pc:
                    row_index = row

        # ハイライトの更新
        bg_color_highlight = QColor("#404000") # Dark Yellow
        bg_color_normal = QColor("#101010")    # Default Background
        
        for row in range(self.table.rowCount()):
            # 行のアイテムを取得
            addr_item = self.table.item(row, 0)
            hex_item = self.table.item(row, 1)
            mnemonic_item = self.table.item(row, 2)
            
            if row == row_index:
                addr_item.setBackground(bg_color_highlight)
                hex_item.setBackground(bg_color_highlight)
                mnemonic_item.setBackground(bg_color_highlight)
            else:
                addr_item.setBackground(bg_color_normal)
                hex_item.setBackground(bg_color_normal)
                mnemonic_item.setBackground(bg_color_normal)

        # スクロール制御
        if row_index != -1:
            scroll_margin = 5 # 常に下に確保したい行数
            row_count = self.table.rowCount()

            # 1. まず、現在の行（本命）を確実に見えるようにする
            current_item = self.table.item(row_index, 0)
            self.table.scrollToItem(current_item, QTableWidget.EnsureVisible)
            
            # 2. 次に、将来実行されるであろう「先（下）」の行が見えるようにリクエストする
            # これにより、ハイライト行が画面の下端ギリギリになるのを防ぎ、常に先が見える状態を作る
            look_ahead_index = min(row_index + scroll_margin, row_count - 1)
            
            if look_ahead_index > row_index:
                look_ahead_item = self.table.item(look_ahead_index, 0)
                self.table.scrollToItem(look_ahead_item, QTableWidget.EnsureVisible)

            # 補足: ジャンプなどで大きく戻った場合のために、上方向のマージンも考慮するとより親切だが、
            # 今回は「先が見えないのが怖い」という要望にフォーカスして下方向を優先する。

    # @intent:responsibility 内部キャッシュをクリアし、強制的な再描画を準備します。
    def reset_cache(self):
        """
        保持している逆アセンブルデータのキャッシュをクリアします。
        メモリ内容が外部で大幅に変更された場合（例：新しいファイルのロード）に呼び出してください。
        """
        self.disassembled_data = []
        self.table.setRowCount(0)
