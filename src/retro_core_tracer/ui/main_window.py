# src/retro_core_tracer/ui/main_window.py
"""
メインウィンドウの実装。
アプリケーションの主要なUIコンポーネントを保持し、レイアウトを管理します。
"""
import sys

from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QDockWidget, QTabWidget, QToolBar, QLabel, QFileDialog, QMessageBox
from PySide6.QtGui import QPalette, QColor, QIcon, QAction, QCloseEvent

from retro_core_tracer.loader.loader import IntelHexLoader, AssemblyLoader
from retro_core_tracer.config.loader import ConfigLoader
from retro_core_tracer.config.builder import SystemBuilder
   
from PySide6.QtCore import Qt, QThread, Signal, Slot
from .register_view import RegisterView
from .flag_view import FlagView
from .hex_view import HexView
from .stack_view import StackView
from .breakpoint_view import BreakpointView
from .code_view import CodeView
from .memory_map_view import MemoryMapView
from .fonts import get_monospace_font_family

# Backend Imports
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.debugger.debugger import Debugger, BreakpointCondition # Import BreakpointCondition
from retro_core_tracer.core.snapshot import Snapshot

# @intent:responsibility デバッガのrunメソッドをバックグラウンドで実行します。
class DebuggerThread(QThread):
    """
    デバッガのrun()をノンブロッキングで実行するためのスレッド。
    """
    breakpoint_hit = Signal(Snapshot)

    def __init__(self, debugger: Debugger):
        super().__init__()
        self.debugger = debugger

    def run(self):
        # run()はブレークポイントで停止する
        self.debugger.run()
        # run()が終了した（ブレークポイントにヒットした）ことを通知
        # run()が終わった時点での最後のSnapshotを取得する
        last_snapshot = self.debugger.get_last_snapshot()
        if last_snapshot:
            self.breakpoint_hit.emit(last_snapshot)


# @intent:responsibility アプリケーションのメインウィンドウを定義し、UIの主要なコンポーネントを組み立てます。
class MainWindow(QMainWindow):
    """
    アプリケーションのメインウィンドウクラス。
    """
    # @intent:responsibility MainWindowを初期化し、UIコンポーネントを設定します。
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("Retro Core Tracer")
        self.setGeometry(100, 100, 1200, 800)
        self.setDockNestingEnabled(True)

        self._setup_backend()
        self._set_dark_theme()
        self._create_menus() # Create menu first to populate view menu
        self._create_toolbar()
        self._create_dock_widgets()
        
        # ステータスバーの初期化
        self.statusBar().showMessage("Ready")
        
        self._update_ui_state(False) # 初期状態は停止中

        # Connect BreakpointView signals (now that breakpoint_view exists)
        self.breakpoint_view.breakpoint_added.connect(self._add_breakpoint_to_debugger)
        self.breakpoint_view.breakpoint_removed.connect(self._remove_breakpoint_from_debugger)
        # Initial update of BreakpointView
        self.breakpoint_view.set_breakpoints(self.debugger.get_breakpoints())

    # @intent:responsibility メニューバーを作成し、ファイル操作（Intel HEXロード）アクションを追加します。
    def _create_menus(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        self.load_config_action = QAction("Load System Config...", self)
        self.load_config_action.triggered.connect(self._load_system_config)
        file_menu.addAction(self.load_config_action)

        self.load_hex_action = QAction("Load HEX...", self)
        self.load_hex_action.setShortcut("Ctrl+O")
        self.load_hex_action.triggered.connect(self._load_hex_file)
        file_menu.addAction(self.load_hex_action)

        self.load_asm_action = QAction("Load Assembly...", self)
        self.load_asm_action.triggered.connect(self._load_assembly_file)
        file_menu.addAction(self.load_asm_action)

        # View Menu will be populated in _create_dock_widgets
        self.view_menu = menu_bar.addMenu("View")


        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #101010;")
        self.setCentralWidget(central_widget)
        
        # HACK: 一時的に中央にラベルを配置して動作確認
        self.status_label = QLabel("Welcome to Retro Core Tracer", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.status_label)
        
        self.debugger_thread = DebuggerThread(self.debugger)
        self.debugger_thread.breakpoint_hit.connect(self._update_ui_from_snapshot)
        
        # NOTE: BreakpointView signals are connected in __init__ after _create_dock_widgets

    # @intent:responsibility デバッグ対象のバックエンドコンポーネントを初期化します。
    def _setup_backend(self):
        self.bus = Bus() # Make bus an instance variable
        ram = RAM(0x10000)
        self.bus.register_device(0x0000, 0xFFFF, ram)
        self.cpu = Z80Cpu(self.bus) # Make cpu an instance variable
        self.debugger = Debugger(self.cpu)
        
        # DebuggerThreadを新しいデバッガインスタンスで再作成
        # 注: 以前のスレッドが実行中の場合は停止する必要がありますが、
        # Load HEXは停止中に行われる前提です。
        self.debugger_thread = DebuggerThread(self.debugger)
        self.debugger_thread.breakpoint_hit.connect(self._update_ui_from_snapshot)

        # HACK: テスト用の一時的なコードをメモリに書き込む
        # ... (HACK code remains) ...

    # @intent:responsibility 実行制御用のツールバーを作成します。
    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # アクションの作成
        self.run_action = QAction("Run", self)
        self.run_action.triggered.connect(self._run_debugger)
        toolbar.addAction(self.run_action)

        self.stop_action = QAction("Stop", self)
        self.stop_action.triggered.connect(self._stop_debugger)
        toolbar.addAction(self.stop_action)
        
        self.step_action = QAction("Step", self)
        self.step_action.triggered.connect(self._step_debugger)
        toolbar.addAction(self.step_action)

    # @intent:responsibility 実行状態に応じてUIコンポーネントの有効/無効を切り替えます。
    def _update_ui_state(self, is_running: bool):
        self.load_hex_action.setEnabled(not is_running)
        self.load_asm_action.setEnabled(not is_running)
        self.run_action.setEnabled(not is_running)
        self.step_action.setEnabled(not is_running)
        self.stop_action.setEnabled(is_running)
        
        if is_running:
            self.statusBar().showMessage("Running...")
        else:
            self.statusBar().showMessage("Stopped")

    # @intent:responsibility デバッガの連続実行を開始します。
    @Slot()
    def _run_debugger(self):
        self._update_ui_state(True)
        self.debugger_thread.start()

    # @intent:responsibility デバッガの連続実行を停止します。
    @Slot()
    def _stop_debugger(self):
        self.statusBar().showMessage("Stopping...")
        self.debugger.stop()

    # @intent:responsibility デバッガを1ステップ実行します。
    @Slot()
    def _step_debugger(self):
        snapshot = self.debugger.step_instruction()
        self._update_ui_from_snapshot(snapshot)

    # @intent:responsibility スナップショットの情報に基づいてUIを更新します。
    @Slot(Snapshot)
    def _update_ui_from_snapshot(self, snapshot: Snapshot):
        self._update_ui_state(False) # 停止状態に戻す
        
        # ステータスバーにサイクル数を表示
        cycle_count = snapshot.metadata.cycle_count
        self.statusBar().showMessage(f"Stopped | T-States: {cycle_count}")
        
        self.register_view.update_registers(snapshot)
        self.flag_view.update_flags(snapshot)
        self.hex_view.update_memory(self.bus, snapshot.state.pc, 256, highlight_address=snapshot.state.pc)
        self.stack_view.update_stack(self.bus, snapshot.state.sp)
        self.code_view.update_code(self.bus, snapshot.state.pc)

    @Slot(BreakpointCondition)
    def _add_breakpoint_to_debugger(self, condition: BreakpointCondition):
        self.debugger.add_breakpoint(condition)
        self.breakpoint_view.set_breakpoints(self.debugger.get_breakpoints()) # Update view

    @Slot(BreakpointCondition)
    def _remove_breakpoint_from_debugger(self, condition: BreakpointCondition):
        self.debugger.remove_breakpoint(condition)
        self.breakpoint_view.set_breakpoints(self.debugger.get_breakpoints()) # Update view

    @Slot()
    def _load_assembly_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Assembly Source", "", "Assembly Files (*.asm *.s);;All Files (*)")
        if file_name:
            try:
                loader = AssemblyLoader()
                symbol_map = loader.load_assembly(file_name, self.bus)
                
                self.cpu.reset()
                self.cpu.set_symbol_map(symbol_map) # シンボルマップをCPUに設定
                
                self.code_view.reset_cache()

                # 初期状態を表示
                from retro_core_tracer.core.snapshot import Operation, Metadata
                dummy_op = Operation(opcode_hex="00", mnemonic="NOP", operands=[])
                # シンボルがあれば反映
                symbol_label = next((name for name, addr in symbol_map.items() if addr == self.cpu.get_state().pc), "")
                symbol_info = f"{symbol_label}: NOP" if symbol_label else "NOP"
                dummy_meta = Metadata(cycle_count=0, symbol_info=symbol_info)
                initial_snapshot = Snapshot(state=self.cpu.get_state(), operation=dummy_op, metadata=dummy_meta)
                self._update_ui_from_snapshot(initial_snapshot)

                QMessageBox.information(self, "Load Assembly", f"Successfully loaded {file_name} with {len(symbol_map)} symbols.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load Assembly file: {e}")

    @Slot()
    def _load_hex_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Intel HEX File", "", "Intel HEX Files (*.hex);;All Files (*)")
        if file_name:
            try:
                # Clear current memory and reset CPU before loading new program
                # Note: We keep the current bus configuration (RAM size etc.)
                # self._setup_backend() 
                
                loader = IntelHexLoader()
                loader.load_intel_hex(file_name, self.bus)
                self.cpu.reset() # Reset PC and other CPU state
                
                # キャッシュされた逆アセンブル内容をクリア（メモリ内容が変わったため）
                self.code_view.reset_cache()

                # 初期状態を表示（実行はしない）
                # ダミーのSnapshotを作成して表示更新
                from retro_core_tracer.core.snapshot import Operation, Metadata
                dummy_op = Operation(opcode_hex="00", mnemonic="NOP", operands=[]) # Dummy
                dummy_meta = Metadata(cycle_count=0)
                initial_snapshot = Snapshot(state=self.cpu.get_state(), operation=dummy_op, metadata=dummy_meta)
                self._update_ui_from_snapshot(initial_snapshot)

                QMessageBox.information(self, "Load HEX", f"Successfully loaded {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load HEX file: {e}")

    @Slot()
    def _load_system_config(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open System Config", "", "YAML Files (*.yaml *.yml);;All Files (*)")
        if file_name:
            try:
                loader = ConfigLoader()
                config = loader.load_from_file(file_name)
                
                builder = SystemBuilder()
                self.cpu, self.bus = builder.build_system(config)
                
                # Re-initialize Debugger with new CPU
                self.debugger = Debugger(self.cpu)
                self.debugger_thread = DebuggerThread(self.debugger)
                self.debugger_thread.breakpoint_hit.connect(self._update_ui_from_snapshot)
                
                # Clear Views
                self.code_view.reset_cache()
                
                # Update Memory Map View
                self.memory_map_view.update_map(config)
                
                # Initial UI update
                self.cpu.reset()
                from retro_core_tracer.core.snapshot import Operation, Metadata
                dummy_op = Operation(opcode_hex="00", mnemonic="NOP", operands=[])
                dummy_meta = Metadata(cycle_count=0)
                initial_snapshot = Snapshot(state=self.cpu.get_state(), operation=dummy_op, metadata=dummy_meta)
                self._update_ui_from_snapshot(initial_snapshot)
                
                QMessageBox.information(self, "System Config", f"Successfully loaded system config from {file_name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load system config: {e}")




    # @intent:responsibility 全てのドックウィジェットを作成し、初期レイアウトを設定します。
    def _create_dock_widgets(self):
        # --- Left Side Widgets ---
        
        # 1. Code View (Assembler)
        self.code_dock = QDockWidget("Assembler", self)
        self.code_dock.setObjectName("CodeDock") # For state saving
        self.code_view = CodeView()
        self.code_dock.setWidget(self.code_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.code_dock)
        self.view_menu.addAction(self.code_dock.toggleViewAction())

        # 2. HEX View
        self.hex_dock = QDockWidget("HEX View", self)
        self.hex_dock.setObjectName("HexDock")
        self.hex_view = HexView()
        self.hex_dock.setWidget(self.hex_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.hex_dock)
        self.view_menu.addAction(self.hex_dock.toggleViewAction())

        # 3. Breakpoints
        self.breakpoint_dock = QDockWidget("Breakpoints", self)
        self.breakpoint_dock.setObjectName("BreakpointDock")
        self.breakpoint_view = BreakpointView()
        self.breakpoint_dock.setWidget(self.breakpoint_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.breakpoint_dock)
        self.view_menu.addAction(self.breakpoint_dock.toggleViewAction())

        # 4. Memory Map
        self.memory_map_dock = QDockWidget("Memory Map", self)
        self.memory_map_dock.setObjectName("MemoryMapDock")
        self.memory_map_view = MemoryMapView()
        self.memory_map_dock.setWidget(self.memory_map_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.memory_map_dock)
        self.view_menu.addAction(self.memory_map_dock.toggleViewAction())

        # --- Right Side Widgets ---

        # 5. Registers
        self.register_dock = QDockWidget("Registers", self)
        self.register_dock.setObjectName("RegisterDock")
        self.register_view = RegisterView()
        self.register_dock.setWidget(self.register_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.register_dock)
        self.view_menu.addAction(self.register_dock.toggleViewAction())

        # 6. Flags
        self.flag_dock = QDockWidget("Flags", self)
        self.flag_dock.setObjectName("FlagDock")
        self.flag_view = FlagView()
        self.flag_dock.setWidget(self.flag_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.flag_dock)
        self.view_menu.addAction(self.flag_dock.toggleViewAction())

        # 7. Stack
        self.stack_dock = QDockWidget("Stack", self)
        self.stack_dock.setObjectName("StackDock")
        self.stack_view = StackView()
        self.stack_dock.setWidget(self.stack_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.stack_dock)
        self.view_menu.addAction(self.stack_dock.toggleViewAction())

        # --- Initial Layout Configuration ---
        
        # Left: Assembler on top, HEX View below it
        self.splitDockWidget(self.code_dock, self.hex_dock, Qt.Vertical)
        
        # Tabify Breakpoints and Memory Map with HEX View (bottom left)
        self.tabifyDockWidget(self.hex_dock, self.breakpoint_dock)
        self.tabifyDockWidget(self.hex_dock, self.memory_map_dock)
        self.hex_dock.raise_() # Bring Hex View to front

        # Right: Registers on top, Stack below it
        self.splitDockWidget(self.register_dock, self.stack_dock, Qt.Vertical)
        
        # Tabify Flags with Registers (top right)
        self.tabifyDockWidget(self.register_dock, self.flag_dock)
        self.register_dock.raise_()

    # @intent:responsibility アプリケーションにダークテーマのスタイルシートを適用します。
    def _set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(29, 29, 29))
        dark_palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(29, 29, 29))
        dark_palette.setColor(QPalette.ToolTipText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.Text, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        QApplication.setPalette(dark_palette)
        
        font_family = get_monospace_font_family()
        
        # MacOSでの表示崩れ（タブ文字の重なり）を防ぐため、paddingを調整
        self.setStyleSheet(f"""
            QWidget {{ font-family: '{font_family}', monospace; font-size: 10pt; }}
            QMainWindow, QToolBar {{ background-color: #1D1D1D; border: none; }}
            QDockWidget::title {{ text-align: left; background: #101010; padding: 4px; font-weight: bold; }}
            QTabWidget::pane {{ border-top: 2px solid #2A82DA; }}
            QTabWidget::tab-bar {{ left: 5px; }}
            QTabBar::tab {{ 
                background: #1E1E1E; 
                border: 1px solid #1E1E1E; 
                border-bottom-color: #2A82DA; 
                padding: 8px 12px; /* Increased padding for MacOS */
                min-width: 80px;   /* Ensure minimum width */
            }}
            QTabBar::tab:selected {{ background: #101010; border: 1px solid #2A82DA; border-bottom-color: #101010; }}
            QTabBar::tab:!selected {{ margin-top: 2px; }}
            QToolTip {{ border: 1px solid #E0E0E0; background-color: #1D1D1D; color: #E0E0E0; }}
        """)

    # @intent:responsibility アプリケーション終了時に呼ばれ、バックグラウンドスレッドを安全に停止します。
    def closeEvent(self, event: QCloseEvent):
        """
        ウィンドウが閉じられる際のイベントハンドラ。
        デバッガスレッドを安全に停止・待機してから終了します。
        """
        if self.debugger_thread.isRunning():
            # UI更新シグナルを切断して、デッドロック（メインスレッドのブロック中のシグナル待ち）を防ぐ
            try:
                self.debugger_thread.breakpoint_hit.disconnect(self._update_ui_from_snapshot)
            except RuntimeError:
                pass # 接続されていない場合は無視

            self.debugger.stop() # デバッガのループを停止
            self.debugger_thread.quit() # スレッドのイベントループを停止
            self.debugger_thread.wait() # スレッドの完全な終了を待機
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())