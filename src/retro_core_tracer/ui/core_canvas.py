"""
Core Canvas モジュール。

CPUの内部構造、周辺機器、およびそれらを結ぶバス配線を動的に可視化し、
パストレースアニメーションを提供します。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, 
    QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsLineItem,
    QSlider, QLabel
)
from PySide6.QtCore import Qt, QTimer, QPointF, Slot
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QWheelEvent

from typing import Optional, List, Deque, Tuple
from collections import deque

from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.core.snapshot import Snapshot, BusAccess, BusAccessType
from retro_core_tracer.config.models import SystemConfig

# --- 色定義 ---
COLOR_BG = "#1E1E1E"
COLOR_CPU = "#00AAAA"
COLOR_MEM_TITLE = "#EEEEEE" # 明るくして視認性向上
COLOR_LABEL_GRAY = "#AAAAAA"

COLOR_RAM_BG = "#004400"
COLOR_RAM_TEXT = "#99FF99" # 明るい緑
COLOR_ROM_BG = "#440000"
COLOR_ROM_TEXT = "#FF9999" # 明るい赤
COLOR_MMIO_BG = "#444400"
COLOR_MMIO_TEXT = "#FFFF99" # 明るい黄色

COLOR_BUS_MEM = "#00AAFF"
COLOR_BUS_IO = "#FFAA00"
COLOR_BUS_WRITE = "#FF5555"

# @intent:responsibility 複数の経由地（Waypoints）を持つバス配線上をトレースする信号。
class BusSignal:
    def __init__(self, path: List[QPointF], color: QColor, data_label: str):
        self.path = path  # 経由地のリスト
        self.color = color
        self.data_label = data_label
        self.progress = 0.0  # 0.0 to 1.0 (全経路に対する進捗)
        self.current_pos = path[0] if path else QPointF(0, 0)

    # @intent:responsibility 進捗(0.0-1.0)に基づいて、折れ線パス上の現在位置を算出します。
    def update_position(self, progress: float):
        self.progress = progress
        if not self.path or len(self.path) < 2:
            return

        # セグメントごとの移動
        num_segments = len(self.path) - 1
        seg_progress = progress * num_segments
        seg_idx = int(seg_progress)
        if seg_idx >= num_segments:
            self.current_pos = self.path[-1]
            return

        t = seg_progress - seg_idx
        p1 = self.path[seg_idx]
        p2 = self.path[seg_idx + 1]
        
        self.current_pos = QPointF(
            (1 - t) * p1.x() + t * p2.x(),
            (1 - t) * p1.y() + t * p2.y()
        )

class CoreCanvas(QGraphicsView):
    """
    動的レイアウトとパストレースアニメーションを表示するキャンバス。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor(COLOR_BG)))
        
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        self._animation_queue: Deque[BusAccess] = deque()
        self._active_signals: List[BusSignal] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_step)
        self._timer.start(16)
        
        self._cpu: Optional[AbstractCpu] = None
        self._config: Optional[SystemConfig] = None

        # 固定レイアウト（基準点）
        self.CPU_RECT = (300, 50, 200, 150)
        self.MEM_AREA = (50, 450, 400, 80)
        self.IO_AREA = (500, 450, 250, 80)
        
        # 動的に計算されるパス情報
        self._mem_path_points: List[QPointF] = []
        self._io_path_points: List[QPointF] = []
        self._is_pmio_arch = True # デフォルトはZ80等の分離型を想定

        self._setup_static_scene()

    def set_cpu(self, cpu: AbstractCpu):
        self._cpu = cpu
        self._setup_static_scene()

    def set_config(self, config: SystemConfig):
        self._config = config
        # アーキテクチャに基づいてI/O空間の有無を判定
        # @intent:rationale Z80等の分離I/O空間(PMIO)を持つアーキテクチャのみIOブロックを表示します。
        self._is_pmio_arch = (config.architecture.upper() == "Z80")
        self._setup_static_scene()

    def set_zoom(self, scale_factor: float):
        self.resetTransform()
        self.scale(scale_factor, scale_factor)

    # @intent:responsibility システム構成に基づいて、CPUから各デバイスへの幾何学的なパスを算出・描画します。
    def _setup_static_scene(self):
        self.scene.clear()
        font_large = QFont("monospace", 12, QFont.Bold)
        font_small = QFont("monospace", 8)
        font_title = QFont("monospace", 9, QFont.Bold)
        
        # --- CPU ---
        cx, cy, cw, ch = self.CPU_RECT
        self.scene.addRect(cx, cy, cw, ch, QPen(QColor(COLOR_CPU), 2), QBrush(QColor("#252525")))
        cpu_name = f"{self._config.architecture} Core" if self._config else "Generic CPU"
        t = self.scene.addText(cpu_name, font_large)
        t.setDefaultTextColor(QColor(COLOR_CPU))
        t.setPos(cx + 10, cy + 10)

        # データバス・ポート位置（CPU下部中央）
        cpu_port = QPointF(cx + cw/2, cy + ch)

        # --- Memory Map ---
        mx, my, mw, mh = self.MEM_AREA
        self.scene.addRect(mx, my, mw, mh, QPen(QColor("#444"), 1), QBrush(QColor("#111")))
        title = self.scene.addSimpleText("Memory Space (0000-FFFF)", font_title)
        title.setBrush(QBrush(QColor(COLOR_MEM_TITLE)))
        title.setPos(mx, my - 20)
        
        if self._config:
            for r in self._config.memory_map:
                rel_x = (r.start / 0x10000) * mw
                rel_w = ((r.end - r.start + 1) / 0x10000) * mw
                
                # 領域タイプに応じた色分け
                color_bg = "#444"
                color_text = "#FFF"
                if r.type == "RAM":
                    color_bg, color_text = COLOR_RAM_BG, COLOR_RAM_TEXT
                elif r.type == "ROM":
                    color_bg, color_text = COLOR_ROM_BG, COLOR_ROM_TEXT
                elif r.type == "MMIO":
                    color_bg, color_text = COLOR_MMIO_BG, COLOR_MMIO_TEXT
                
                self.scene.addRect(mx + rel_x, my, rel_w, mh, QPen(Qt.NoPen), QBrush(QColor(color_bg)))
                
                # 領域内のラベル表示
                # @intent:rationale 領域のタイプとアドレス範囲を表示します。
                if rel_w > 40:
                    label_text = f"{r.type} (0x{r.start:04X}-0x{r.end:04X})"
                    l = self.scene.addSimpleText(label_text, font_small)
                    
                    # ラベルが矩形からはみ出す場合は、タイプ名のみにする
                    if l.boundingRect().width() > rel_w - 4:
                        self.scene.removeItem(l)
                        l = self.scene.addSimpleText(r.type, font_small)
                        
                    l.setBrush(QBrush(QColor(color_text)))
                    l.setPos(mx + rel_x + (rel_w - l.boundingRect().width())/2, my + mh/2 - 5)

        # 中継点の高さ
        mid_y = cy + ch + (my - (cy + ch)) / 2

        # Memory Path (CPU -> MidY -> MemX -> MemY)
        mem_top_center = QPointF(mx + mw/2, my)
        self._mem_path_points = [
            cpu_port,
            QPointF(cpu_port.x(), mid_y),
            QPointF(mem_top_center.x(), mid_y),
            mem_top_center
        ]
        self._draw_path(self._mem_path_points, QColor(COLOR_BUS_MEM))

        # --- IO Map (Conditional) ---
        if self._is_pmio_arch:
            ix, iy, iw, ih = self.IO_AREA
            self.scene.addRect(ix, iy, iw, ih, QPen(QColor("#444"), 1), QBrush(QColor("#111")))
            io_title = self.scene.addSimpleText("I/O Ports", font_title)
            io_title.setBrush(QBrush(QColor(COLOR_MEM_TITLE)))
            io_title.setPos(ix, iy - 20)
            
            if self._config and self._config.io_map:
                num_io = len(self._config.io_map)
                for idx, r in enumerate(self._config.io_map):
                    entry_w = iw / max(num_io, 4)
                    self.scene.addRect(ix + idx * entry_w, iy, entry_w - 2, ih, QPen(Qt.NoPen), QBrush(QColor(COLOR_MMIO_BG)))
                    io_label = self.scene.addSimpleText(r.label or f"{r.start:02X}", font_small)
                    io_label.setBrush(QBrush(QColor(COLOR_MMIO_TEXT)))
                    io_label.setPos(ix + idx * entry_w + 2, iy + ih/2 - 5)

            # IO Path
            io_top_center = QPointF(ix + iw/2, iy)
            self._io_path_points = [
                cpu_port,
                QPointF(cpu_port.x(), mid_y),
                QPointF(io_top_center.x(), mid_y),
                io_top_center
            ]
            self._draw_path(self._io_path_points, QColor(COLOR_BUS_IO))
        else:
            self._io_path_points = [] # MMIOアーキテクチャでは空にする

    def _draw_path(self, points: List[QPointF], color: QColor):
        pen = QPen(color, 2, Qt.DashLine)
        for i in range(len(points) - 1):
            self.scene.addLine(points[i].x(), points[i].y(), points[i+1].x(), points[i+1].y(), pen)

    def update_view(self, snapshot: Snapshot):
        for access in snapshot.bus_activity:
            self._animation_queue.append(access)

    def _animate_step(self):
        if self._animation_queue and len(self._active_signals) < 10:
            self._spawn_signal(self._animation_queue.popleft())
            
        active_next = []
        for s in self._active_signals:
            s.update_position(s.progress + 0.03)
            if s.progress < 1.0:
                active_next.append(s)
        self._active_signals = active_next
        self._draw_dynamic_elements()

    # @intent:responsibility アクセスタイプに応じた動的なアニメーションパスを生成します。
    def _spawn_signal(self, access: BusAccess):
        # 経路の選択
        # @intent:rationale 独立I/O空間(PMIO)をサポートする場合のみI/Oパスを使用します。
        is_io_access = access.access_type in (BusAccessType.IO_READ, BusAccessType.IO_WRITE)
        use_io_path = is_io_access and self._is_pmio_arch
        
        base_path = self._io_path_points if use_io_path else self._mem_path_points
        
        if use_io_path:
            ix, iy, iw, ih = self.IO_AREA
            target_x = ix + ((access.address & 0xFF) / 256) * iw
            target_pos = QPointF(target_x, iy)
        else:
            mx, my, mw, mh = self.MEM_AREA
            target_x = mx + (access.address / 0x10000) * mw
            target_pos = QPointF(target_x, my)
            
        full_path = list(base_path)
        full_path.append(target_pos)
        
        is_read = access.access_type in (BusAccessType.READ, BusAccessType.IO_READ)
        if is_read:
            full_path.reverse()
            
        color = QColor(COLOR_BUS_MEM) if not use_io_path else QColor(COLOR_BUS_IO)
        if access.access_type in (BusAccessType.WRITE, BusAccessType.IO_WRITE):
            color = QColor(COLOR_BUS_WRITE)
            
        self._active_signals.append(BusSignal(full_path, color, f"{access.data:02X}"))

    def _draw_dynamic_elements(self):
        for item in self.scene.items():
            if getattr(item, "is_dynamic", False):
                self.scene.removeItem(item)
                
        for s in self._active_signals:
            r = 6
            e = self.scene.addEllipse(s.current_pos.x()-r, s.current_pos.y()-r, r*2, r*2, QPen(Qt.NoPen), QBrush(s.color))
            e.is_dynamic = True
            t = self.scene.addSimpleText(s.data_label, QFont("monospace", 8))
            t.setBrush(QBrush(s.color))
            t.setPos(s.current_pos.x() + 8, s.current_pos.y() - 12)
            t.is_dynamic = True

class CoreCanvasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.canvas = CoreCanvas()
        self.layout.addWidget(self.canvas)
        
        control_layout = QHBoxLayout()
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        control_layout.addWidget(QLabel("Zoom:"))
        control_layout.addWidget(self.zoom_slider)
        self.layout.addLayout(control_layout)

    @Slot(int)
    def _on_zoom_changed(self, value: int):
        self.canvas.set_zoom(value / 100.0)

    def set_cpu(self, cpu: AbstractCpu): self.canvas.set_cpu(cpu)
    def set_config(self, config: SystemConfig): self.canvas.set_config(config)
    def update_view(self, snapshot: Snapshot): self.canvas.update_view(snapshot)
