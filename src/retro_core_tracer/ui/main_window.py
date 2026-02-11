# src/retro_core_tracer/ui/main_window.py
"""
メインウィンドウモジュール。
アプリケーションの全体的なレイアウトと、各コンポーネント間の連携を管理します。
"""
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QVBoxLayout, QWidget,
    QFileDialog, QMessageBox, QToolBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon

from retro_core_tracer.config.loader import ConfigLoader
from retro_core_tracer.config.builder import SystemBuilder
from retro_core_tracer.loader.loader import IntelHexLoader, AssemblyLoader
from retro_core_tracer.debugger.debugger import Debugger, BreakpointCondition, BreakpointConditionType
from retro_core_tracer.ui.register_view import RegisterView
from retro_core_tracer.ui.flag_view import FlagView
from retro_core_tracer.ui.code_view import CodeView
from retro_core_tracer.ui.hex_view import HexView
from retro_core_tracer.ui.stack_view import StackView
from retro_core_tracer.ui.memory_map_view import MemoryMapView
from retro_core_tracer.ui.breakpoint_view import BreakpointView
from retro_core_tracer.ui.core_canvas import CoreCanvas

class MainWindow(QMainWindow):
    """
    エミュレータのメインウィンドウクラス。
    ドッキングウィンドウを使用して各ビューを配置します。
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Retro Core Tracer")
        self.resize(1200, 800)

        # コアコンポーネント
        self.bus = None
        self.cpu = None
        self.debugger = None
        self.config = None
        
        # 実行制御用タイマー
        self.run_timer = QTimer()
        self.run_timer.timeout.connect(self._run_step)

        # UIのセットアップ
        self._setup_menus()
        self._setup_toolbar()
        self._setup_docks()
        
        self.statusBar().showMessage("Ready")

    def _setup_menus(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        load_config_action = QAction("&Load Config...", self)
        load_config_action.triggered.connect(self._load_config)
        file_menu.addAction(load_config_action)
        
        file_menu.addSeparator()
        
        load_hex_action = QAction("Load &HEX...", self)
        load_hex_action.triggered.connect(self._load_hex_file)
        file_menu.addAction(load_hex_action)
        
        self.load_asm_action = QAction("Load &Assembly...", self)
        self.load_asm_action.triggered.connect(self._load_assembly_file)
        file_menu.addAction(self.load_asm_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_toolbar(self):
        toolbar = QToolBar("Execution Control")
        self.addToolBar(toolbar)
        
        self.step_action = QAction("Step", self)
        self.step_action.triggered.connect(self._step)
        self.step_action.setEnabled(False)
        toolbar.addAction(self.step_action)
        
        self.run_action = QAction("Run", self)
        self.run_action.triggered.connect(self._run)
        self.run_action.setEnabled(False)
        toolbar.addAction(self.run_action)
        
        self.stop_action = QAction("Stop", self)
        self.stop_action.triggered.connect(self._stop)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)
        
        toolbar.addSeparator()
        
        reset_action = QAction("Reset", self)
        reset_action.triggered.connect(self._reset_cpu)
        toolbar.addAction(reset_action)

    def _setup_docks(self):
        # Core Canvas (Main Center)
        self.core_canvas = CoreCanvas()
        self.setCentralWidget(self.core_canvas)

        # Code View
        self.code_dock = QDockWidget("Code", self)
        self.code_view = CodeView()
        self.code_dock.setWidget(self.code_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.code_dock)

        # Register View
        self.reg_dock = QDockWidget("Registers", self)
        self.register_view = RegisterView()
        self.reg_dock.setWidget(self.register_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.reg_dock)

        # Flag View
        self.flag_dock = QDockWidget("Flags", self)
        self.flag_view = FlagView()
        self.flag_dock.setWidget(self.flag_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.flag_dock)

        # Hex View
        self.hex_dock = QDockWidget("Memory (HEX)", self)
        self.hex_view = HexView()
        self.hex_dock.setWidget(self.hex_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.hex_dock)

        # Stack View
        self.stack_dock = QDockWidget("Stack", self)
        self.stack_view = StackView()
        self.stack_dock.setWidget(self.stack_view)
        self.addDockWidget(Qt.RightDockWidgetArea, self.stack_dock)
        
        # Memory Map View
        self.mmap_dock = QDockWidget("Memory Map", self)
        self.memory_map_view = MemoryMapView()
        self.mmap_dock.setWidget(self.memory_map_view)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.mmap_dock)

        # Breakpoint View
        self.bp_dock = QDockWidget("Breakpoints", self)
        self.breakpoint_view = BreakpointView()
        self.bp_dock.setWidget(self.breakpoint_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.bp_dock)
        
        # Connect signals
        self.breakpoint_view.breakpoint_added.connect(self._add_breakpoint)
        self.breakpoint_view.breakpoint_removed.connect(self._remove_breakpoint)

    def _load_config(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Config File", "", "YAML Files (*.yaml);;All Files (*)")
        if file_name:
            try:
                loader = ConfigLoader()
                self.config = loader.load_from_file(file_name)
                
                builder = SystemBuilder()
                self.cpu, self.bus = builder.build_system(self.config)
                self.debugger = Debugger(self.cpu)
                
                # Update Views
                self.register_view.set_cpu(self.cpu)
                self.flag_view.set_cpu(self.cpu)
                self.code_view.set_cpu(self.cpu)
                self.hex_view.set_bus(self.bus)
                self.stack_view.set_cpu(self.cpu, self.bus)
                self.memory_map_view.set_config(self.config, self.bus)
                self.breakpoint_view.set_cpu(self.cpu)
                self.core_canvas.set_cpu(self.cpu)
                
                self._update_all_views()
                
                # Enable actions
                self.step_action.setEnabled(True)
                self.run_action.setEnabled(True)
                
                self.statusBar().showMessage(f"Loaded config: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load config: {str(e)}")

    def _load_hex_file(self):
        if not self.bus:
            QMessageBox.warning(self, "Warning", "Please load a config file first.")
            return
            
        file_name, _ = QFileDialog.getOpenFileName(self, "Open HEX File", "", "HEX Files (*.hex);;All Files (*)")
        if file_name:
            try:
                loader = IntelHexLoader()
                loader.load_intel_hex(file_name, self.bus)
                self._update_all_views()
                self.statusBar().showMessage(f"Loaded HEX: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load HEX: {str(e)}")

    def _load_assembly_file(self):
        if not self.bus:
            QMessageBox.warning(self, "Warning", "Please load a config file first.")
            return
            
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Assembly File", "", "Assembly Files (*.asm);;All Files (*)")
        if file_name:
            try:
                # Determine current architecture
                arch = self.config.architecture if self.config else "Z80"
                
                loader = AssemblyLoader()
                # @intent:responsibility 現在のアーキテクチャ情報を渡してアセンブルを実行します。
                symbol_map = loader.load_assembly(file_name, self.bus, architecture=arch)
                self.cpu.set_symbol_map(symbol_map)
                
                # Refresh views
                self.code_view.set_symbol_map(symbol_map)
                self._update_all_views()
                self.statusBar().showMessage(f"Loaded assembly: {file_name} ({arch})")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load assembly: {str(e)}")

    def _step(self):
        if self.debugger:
            snapshot = self.debugger.step_instruction()
            self._update_all_views()
            self.statusBar().showMessage(f"Executed: {snapshot.operation.mnemonic}")

    def _run(self):
        self.run_action.setEnabled(False)
        self.step_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self.run_timer.start(10) # 10ms interval (approx 100Hz instruction execution)

    def _run_step(self):
        if self.debugger:
            # Check for PC breakpoints before execution
            current_pc = self.cpu.get_state().pc
            for bp in self.debugger.get_breakpoints():
                if bp.condition_type == BreakpointConditionType.PC_MATCH and bp.value == current_pc:
                    self._stop()
                    self.statusBar().showMessage(f"Breakpoint hit at {current_pc:04X}")
                    return

            snapshot = self.debugger.step_instruction()
            
            # Check for other breakpoints after execution
            hit = False
            # (Note: Debugger.run() has more complex logic, here we do a simple check)
            
            self._update_all_views()
            
    def _stop(self):
        self.run_timer.stop()
        self.run_action.setEnabled(True)
        self.step_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.statusBar().showMessage("Stopped")

    def _reset_cpu(self):
        if self.cpu:
            self.cpu.reset()
            self._update_all_views()
            self.statusBar().showMessage("CPU Reset")

    def _add_breakpoint(self, condition: BreakpointCondition):
        if self.debugger:
            self.debugger.add_breakpoint(condition)

    def _remove_breakpoint(self, condition: BreakpointCondition):
        if self.debugger:
            self.debugger.remove_breakpoint(condition)

    def _update_all_views(self):
        if not self.cpu:
            return
            
        pc = self.cpu.get_state().pc
        self.register_view.update_registers()
        self.flag_view.update_flags()
        self.code_view.update_code(pc)
        self.hex_view.update_view()
        self.stack_view.update_view()
        self.memory_map_view.update_view()

        if self.debugger:
            snapshot = self.debugger.get_last_snapshot()
            if snapshot:
                self.core_canvas.update_view(snapshot)
