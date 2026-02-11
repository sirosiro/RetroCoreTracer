"""
Core Canvas モジュール。

CPUの内部構造とバスアクティビティを可視化するための
グラフィカルなキャンバスコンポーネントを提供します。
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

# @intent:responsibility バス上を移動するデータ信号（光の粒）のアニメーション状態を管理します。
class BusSignal:
    def __init__(self, start_pos: QPointF, end_pos: QPointF, color: QColor, data_label: str):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.current_pos = start_pos
        self.color = color
        self.data_label = data_label
        self.progress = 0.0 # 0.0 to 1.0

# @intent:responsibility CPUとメモリ、それらを繋ぐバスのグラフィカルな表現を管理します。
class CoreCanvas(QGraphicsView):
    """
    CPUブロック図とバスアニメーションを表示するキャンバス（ビュー部分）。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 描画品質の設定
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setBackgroundBrush(QBrush(QColor("#1E1E1E")))
        
        # ズームの設定
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._zoom_factor = 1.0
        
        # アニメーション用キューとタイマー
        self._animation_queue: Deque[BusAccess] = deque()
        self._active_signals: List[BusSignal] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_step)
        self._timer.start(16) # ~60 FPS
        
        self._cpu: Optional[AbstractCpu] = None
        
        # レイアウト定数（仮）
        self.CPU_RECT = (300, 100, 200, 200)
        self.MEM_RECT = (50, 400, 700, 100)
        
        self._setup_static_scene()

    # @intent:responsibility マウスホイールによるズームを処理します（スライダーと併用可能）。
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            # スライダーがある場合は親ウィジェットに通知してスライダーを動かすのが理想だが、
            # ここではシンプルに自身のズームだけ処理し、あとで連携を考える
            pass 
        super().wheelEvent(event)

    # @intent:responsibility 外部からズーム倍率を設定します。
    def set_zoom(self, scale_factor: float):
        # 現在のトランスフォームをリセットしてから新しいスケールを適用
        self.resetTransform()
        self.scale(scale_factor, scale_factor)
        self._zoom_factor = scale_factor

    # @intent:responsibility 静的なシーン要素（CPU箱、メモリ箱、バスライン）を描画します。
    def _setup_static_scene(self):
        self.scene.clear()
        
        # フォント設定
        font = QFont("monospace", 10)
        
        # CPU Box
        x, y, w, h = self.CPU_RECT
        cpu_item = self.scene.addRect(x, y, w, h, QPen(QColor("#00AAAA"), 2), QBrush(QColor("#252525")))
        text = self.scene.addText("CPU Core", font)
        text.setDefaultTextColor(QColor("#00AAAA"))
        text.setPos(x + 10, y + 10)
        
        # Memory Box
        mx, my, mw, mh = self.MEM_RECT
        mem_item = self.scene.addRect(mx, my, mw, mh, QPen(QColor("#00AA00"), 2), QBrush(QColor("#252525")))
        text = self.scene.addText("System Bus / Memory Space", font)
        text.setDefaultTextColor(QColor("#00AA00"))
        text.setPos(mx + 10, my + 10)
        
        # Address Bus Line (CPU -> Memory)
        self.scene.addLine(x + 50, y + h, x + 50, my, QPen(QColor("#AAAA00"), 3)) # Yellow
        
        # Data Bus Line (Bidirectional)
        self.scene.addLine(x + 150, y + h, x + 150, my, QPen(QColor("#00AAFF"), 3)) # Blue

    # @intent:responsibility 表示対象のCPUを設定します。
    def set_cpu(self, cpu: AbstractCpu):
        self._cpu = cpu

    # @intent:responsibility スナップショットを受け取り、バスアクセスをアニメーションキューに追加します。
    def update_view(self, snapshot: Snapshot):
        for access in snapshot.bus_activity:
            self._animation_queue.append(access)
    
    # @intent:responsibility アニメーションの1フレームを処理します。
    def _animate_step(self):
        if self._animation_queue and len(self._active_signals) < 5:
            access = self._animation_queue.popleft()
            self._spawn_signal(access)
            
        active_signals_next = []
        for signal in self._active_signals:
            signal.progress += 0.05
            if signal.progress >= 1.0:
                continue
            
            new_x = (1 - signal.progress) * signal.start_pos.x() + signal.progress * signal.end_pos.x()
            new_y = (1 - signal.progress) * signal.start_pos.y() + signal.progress * signal.end_pos.y()
            signal.current_pos = QPointF(new_x, new_y)
            active_signals_next.append(signal)
            
        self._active_signals = active_signals_next
        self._draw_dynamic_elements()

    # @intent:responsibility BusAccess情報に基づいて新しいBusSignalを生成します。
    def _spawn_signal(self, access: BusAccess):
        x, y, w, h = self.CPU_RECT
        mx, my, mw, mh = self.MEM_RECT
        
        cpu_data_port = QPointF(x + 150, y + h)
        mem_data_port = QPointF(x + 150, my)
        
        start_pos = QPointF(0, 0)
        end_pos = QPointF(0, 0)
        color = QColor("white")
        
        if access.access_type == BusAccessType.READ:
            start_pos = mem_data_port
            end_pos = cpu_data_port
            color = QColor("#00AAFF")
        elif access.access_type == BusAccessType.WRITE:
            start_pos = cpu_data_port
            end_pos = mem_data_port
            color = QColor("#FF5555")
            
        self._active_signals.append(BusSignal(start_pos, end_pos, color, f"{access.data:02X}"))

    # @intent:responsibility 動的なアニメーション要素（光の粒）を描画します。
    def _draw_dynamic_elements(self):
        for item in self.scene.items():
            if getattr(item, "is_dynamic", False):
                self.scene.removeItem(item)
                
        for signal in self._active_signals:
            radius = 5
            ellipse = self.scene.addEllipse(
                signal.current_pos.x() - radius, 
                signal.current_pos.y() - radius, 
                radius * 2, radius * 2,
                QPen(Qt.NoPen), QBrush(signal.color)
            )
            ellipse.is_dynamic = True
            
            text = self.scene.addSimpleText(signal.data_label)
            text.setBrush(QBrush(signal.color))
            text.setPos(signal.current_pos.x() + 10, signal.current_pos.y() - 10)
            text.is_dynamic = True

# @intent:responsibility CoreCanvasとズーム用スライダーを組み合わせたウィジェットを提供します。
class CoreCanvasWidget(QWidget):
    """
    CoreCanvasとズームコントロールを含むコンテナウィジェット。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Canvas
        self.canvas = CoreCanvas()
        self.layout.addWidget(self.canvas)
        
        # Control Bar
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        label = QLabel("Zoom:")
        label.setStyleSheet("color: #BBBBBB;")
        control_layout.addWidget(label)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 300) # 10% to 300%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(50)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        # スライダーのスタイル
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #333;
                height: 8px;
                background: #252525;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #00AAAA;
                border: 1px solid #00AAAA;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)
        control_layout.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #BBBBBB; min-width: 40px; text-align: right;")
        control_layout.addWidget(self.zoom_label)
        
        self.layout.addLayout(control_layout)
        
        # 最小サイズ設定（潰れ防止）
        self.setMinimumSize(400, 300)

    @Slot(int)
    def _on_zoom_changed(self, value: int):
        scale = value / 100.0
        self.canvas.set_zoom(scale)
        self.zoom_label.setText(f"{value}%")

    # Delegate methods to inner canvas
    def set_cpu(self, cpu: AbstractCpu):
        self.canvas.set_cpu(cpu)

    def update_view(self, snapshot: Snapshot):
        self.canvas.update_view(snapshot)
