"""
逆アセンブルコードを表示するウィジェット。
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from typing import Dict, Optional, Tuple, List

from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.ui.fonts import get_monospace_font

# @intent:responsibility 逆アセンブルされたコードを表形式で表示し、現在のPCをハイライトする汎用UIウィジェットを提供します。
class CodeView(QWidget):
    """
    逆アセンブルコードを表示するウィジェット。
    AbstractCpuのdisassembleメソッドを利用します。
    """
    # @intent:responsibility CodeViewウィジェットを初期化し、テーブルを設定します。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Address", "Bytes", "Label", "Mnemonic"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Address
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Bytes
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents) # Label
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)          # Mnemonic
        
        # フォント設定
        font = get_monospace_font(10)
        self.table.setFont(font)
        
        # 行ヘッダ（番号）を隠す
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setStyleSheet("QTableWidget { background-color: #121212; color: #BBBBBB; gridline-color: #303030; } QHeaderView::section { background-color: #252525; color: #BBBBBB; }")
        
        self.layout.addWidget(self.table)
        
        self._cpu: Optional[AbstractCpu] = None
        
        # 現在表示している逆アセンブルデータ [(addr, hex, mnemonic), ...]
        self.disassembled_data: List[Tuple[int, str, str]] = []
        
        # シンボルマップ (Label -> Address) の逆引き用 (Address -> Label)
        self.reverse_symbol_map: Dict[int, str] = {}

    # @intent:responsibility 表示対象のCPUを設定します。
    def set_cpu(self, cpu: AbstractCpu):
        self._cpu = cpu
        self.reset_cache()

    # @intent:responsibility 表示に使用するシンボルマップを設定します。
    def set_symbol_map(self, symbol_map: Dict[str, int]):
        """
        シンボルマップを設定します。
        """
        # アドレスから名前を引けるように逆変換
        self.reverse_symbol_map = {addr: name for name, addr in symbol_map.items()}
        self.reset_cache() # 表示更新のためにキャッシュをクリア

    # @intent:responsibility 指定されたPC周辺のメモリを逆アセンブルして表示を更新します。
    def update_code(self, pc: int):
        """
        現在のPC周辺のコードを逆アセンブルして表示します。
        PCが現在の表示範囲内にあれば、再描画せずにハイライト移動のみ行います。
        """
        if not self._cpu:
            return

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
            
            # AbstractCpu.disassemble を使用して逆アセンブル
            self.disassembled_data = self._cpu.disassemble(start_addr, length)
            
            self.table.setRowCount(len(self.disassembled_data))
            
            for row, (addr, hex_dump, mnemonic) in enumerate(self.disassembled_data):
                addr_item = QTableWidgetItem(f"{addr:04X}")
                hex_item = QTableWidgetItem(hex_dump)
                
                # @intent:utility_function アドレスに対応するシンボル（ラベル）がある場合は表示用のカラムに設定します。
                # ラベルがあれば取得、なければ空文字
                label_text = self.reverse_symbol_map.get(addr, "")
                if label_text:
                    label_text += ":"
                label_item = QTableWidgetItem(label_text)
                label_item.setForeground(QColor("#00AAAA")) # Cyan color for labels
                
                mnemonic_item = QTableWidgetItem(mnemonic)
                
                self.table.setItem(row, 0, addr_item)
                self.table.setItem(row, 1, hex_item)
                self.table.setItem(row, 2, label_item)
                self.table.setItem(row, 3, mnemonic_item)
                
                if addr == pc:
                    row_index = row

        # ハイライトの更新
        bg_color_highlight = QColor("#404000") # Dark Yellow
        bg_color_normal = QColor("#121212")    # Default Background
        
        for row in range(self.table.rowCount()):
            # 行のアイテムを取得
            addr_item = self.table.item(row, 0)
            hex_item = self.table.item(row, 1)
            label_item = self.table.item(row, 2)
            mnemonic_item = self.table.item(row, 3)
            
            if row == row_index:
                addr_item.setBackground(bg_color_highlight)
                hex_item.setBackground(bg_color_highlight)
                label_item.setBackground(bg_color_highlight)
                mnemonic_item.setBackground(bg_color_highlight)
            else:
                addr_item.setBackground(bg_color_normal)
                hex_item.setBackground(bg_color_normal)
                label_item.setBackground(bg_color_normal)
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