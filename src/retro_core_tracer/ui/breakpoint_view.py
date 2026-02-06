# src/retro_core_tracer/ui/breakpoint_view.py
"""
ブレークポイントの管理UIウィジェット。
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from typing import List, Optional

from retro_core_tracer.debugger.debugger import BreakpointCondition, BreakpointConditionType

# @intent:responsibility ブレークポイントの管理（追加、削除、一覧表示）を行うUIウィジェットを提供します。
class BreakpointView(QWidget):
    """
    ブレークポイントの追加、削除、一覧表示を行うUIウィジェット。
    """
    # ブレークポイントの追加/削除をMainWindowに通知するためのシグナル
    # (MainWindowがDebuggerインスタンスを保持しているため)
    breakpoint_added = Signal(BreakpointCondition)
    breakpoint_removed = Signal(BreakpointCondition)

    # @intent:responsibility BreakpointViewウィジェットを初期化し、入力フォームとリストウィジェットを配置します。
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # --------------------
        # ブレークポイント追加フォーム
        # --------------------
        add_form_layout = QHBoxLayout()

        # タイプ選択
        add_form_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        for bp_type in BreakpointConditionType:
            self.type_combo.addItem(bp_type.name, bp_type) # Store enum value as user data
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        add_form_layout.addWidget(self.type_combo)

        # 値/アドレス/レジスタ名入力
        add_form_layout.addWidget(QLabel("Value/Addr/Reg:"))
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("e.g., 0x1234 or A")
        add_form_layout.addWidget(self.value_input)
        
        # 追加ボタン
        self.add_button = QPushButton("Add Breakpoint")
        self.add_button.clicked.connect(self._add_breakpoint)
        add_form_layout.addWidget(self.add_button)

        self.layout.addLayout(add_form_layout)

        # --------------------
        # 既存ブレークポイント一覧
        # --------------------
        self.bp_list_widget = QListWidget()
        self.bp_list_widget.itemDoubleClicked.connect(self._remove_breakpoint_from_list)
        self.layout.addWidget(self.bp_list_widget)

        # 初期状態のUIを更新
        self._on_type_changed(self.type_combo.currentIndex())
    
    # @intent:responsibility 選択されたブレークポイントタイプに応じて、入力フィールドのプレースホルダーと有効状態を更新します。
    @Slot(int)
    def _on_type_changed(self, index: int):
        selected_type: BreakpointConditionType = self.type_combo.itemData(index)
        if selected_type in [BreakpointConditionType.PC_MATCH, BreakpointConditionType.REGISTER_VALUE, BreakpointConditionType.MEMORY_READ, BreakpointConditionType.MEMORY_WRITE]:
            self.value_input.setEnabled(True)
            if selected_type == BreakpointConditionType.REGISTER_VALUE:
                self.value_input.setPlaceholderText("e.g., A:0xAA or HL:0x1234")
            elif selected_type in [BreakpointConditionType.MEMORY_READ, BreakpointConditionType.MEMORY_WRITE]:
                self.value_input.setPlaceholderText("e.g., 0x1000")
            else: # PC_MATCH
                self.value_input.setPlaceholderText("e.g., 0x1234")
        elif selected_type == BreakpointConditionType.REGISTER_CHANGE:
            self.value_input.setEnabled(True)
            self.value_input.setPlaceholderText("e.g., A or HL")
        else: # 例えば、将来的に引数が不要なタイプが追加された場合
            self.value_input.setEnabled(False)
            self.value_input.clear()

    # @intent:responsibility ユーザー入力に基づいて新しいブレークポイント条件を作成し、シグナルを発行します。
    @Slot()
    def _add_breakpoint(self):
        bp_type: BreakpointConditionType = self.type_combo.currentData()
        value_str = self.value_input.text().strip()
        
        condition: Optional[BreakpointCondition] = None

        try:
            if bp_type == BreakpointConditionType.PC_MATCH:
                value = int(value_str, 16)
                condition = BreakpointCondition(condition_type=bp_type, value=value)
            elif bp_type == BreakpointConditionType.MEMORY_READ or bp_type == BreakpointConditionType.MEMORY_WRITE:
                address = int(value_str, 16)
                condition = BreakpointCondition(condition_type=bp_type, address=address)
            elif bp_type == BreakpointConditionType.REGISTER_VALUE:
                reg_name_str, reg_value_str = value_str.split(':')
                reg_name = reg_name_str.upper()
                reg_value = int(reg_value_str, 16)
                condition = BreakpointCondition(condition_type=bp_type, register_name=reg_name, value=reg_value)
            elif bp_type == BreakpointConditionType.REGISTER_CHANGE:
                reg_name = value_str.upper()
                condition = BreakpointCondition(condition_type=bp_type, register_name=reg_name)
            
            if condition:
                # 重複チェックはDebuggerクラスが担当するが、UIでも表示上の重複は避ける
                for i in range(self.bp_list_widget.count()):
                    item = self.bp_list_widget.item(i)
                    if item.data(Qt.UserRole) == condition:
                        QMessageBox.warning(self, "Duplicate Breakpoint", "This breakpoint already exists.")
                        return

                self.breakpoint_added.emit(condition) # MainWindowに通知
                self._update_list() # リスト更新はMainWindowからのコールバックでやる方がクリーン

        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid input for breakpoint: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
            
    def _update_list(self):
        """MainWindowから現在のDebuggerのブレークポイントリストを受け取り、表示を更新する。"""
        # このメソッドはMainWindow側で、Debuggerのget_breakpoints()を呼び出し、
        # その結果を引数として渡すコールバックとして実装される予定。
        # 今はダミーの実装。
        # self.bp_list_widget.clear()
        # for bp in self.debugger.get_breakpoints():
        #     item = QListWidgetItem(str(bp))
        #     item.setData(Qt.UserRole, bp) # ブレークポイントオブジェクトをUserRoleに保存
        #     self.bp_list_widget.addItem(item)
        pass # Placeholder for actual update logic


    # @intent:responsibility 選択されたブレークポイントの削除を確認し、削除シグナルを発行します。
    @Slot(QListWidgetItem)
    def _remove_breakpoint_from_list(self, item: QListWidgetItem):
        item_text = item.text() # Get text before item is potentially deleted
        reply = QMessageBox.question(self, "Remove Breakpoint", 
                                     f"Are you sure you want to remove breakpoint: {item_text}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            condition: BreakpointCondition = item.data(Qt.UserRole)
            if condition:
                self.breakpoint_removed.emit(condition) # MainWindowに通知
                # リストからの削除はMainWindowからのコールバックでやる方がクリーン
                # self.bp_list_widget.takeItem(self.bp_list_widget.row(item))
            # The list will refresh via MainWindow's slot, so no QMessageBox is needed here.
            # QMessageBox.information(self, "Breakpoint Removed", f"Breakpoint {item_text} removed (or notification sent).")

    # @intent:responsibility ブレークポイントリストの表示を更新します。
    def set_breakpoints(self, breakpoints: List[BreakpointCondition]):
        """
        MainWindowから現在のブレークポイントリストを受け取り、表示を更新する。
        """
        self.bp_list_widget.clear()
        for bp in breakpoints:
            item = QListWidgetItem(self._format_breakpoint_for_display(bp))
            item.setData(Qt.UserRole, bp) # ブレークポイントオブジェクトをUserRoleに保存
            self.bp_list_widget.addItem(item)

    # @intent:responsibility ブレークポイント条件を表示用文字列にフォーマットします。
    def _format_breakpoint_for_display(self, bp: BreakpointCondition) -> str:
        if bp.condition_type == BreakpointConditionType.PC_MATCH:
            return f"PC_MATCH: 0x{bp.value:04X}"
        elif bp.condition_type == BreakpointConditionType.MEMORY_READ:
            return f"MEM_READ: 0x{bp.address:04X}"
        elif bp.condition_type == BreakpointConditionType.MEMORY_WRITE:
            return f"MEM_WRITE: 0x{bp.address:04X}"
        elif bp.condition_type == BreakpointConditionType.REGISTER_VALUE:
            return f"REG_VALUE: {bp.register_name}={bp.value:02X}"
        elif bp.condition_type == BreakpointConditionType.REGISTER_CHANGE:
            return f"REG_CHANGE: {bp.register_name}"
        return str(bp)

# Minimal test code
if __name__ == '__main__':
    sys._excepthook = sys.excepthook 
    def exception_hook(exctype, value, traceback):
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
    from retro_core_tracer.debugger.debugger import Debugger # Dummy Debugger
    from retro_core_tracer.core.cpu import AbstractCpu
    from retro_core_tracer.core.snapshot import Snapshot
    from retro_core_tracer.transport.bus import Bus
    from retro_core_tracer.arch.z80.cpu import Z80CpuState

    class DummyCpu(AbstractCpu):
        def _create_initial_state(self) -> Z80CpuState:
            return Z80CpuState()
        def _fetch(self) -> int: return 0 # Dummy
        def _decode(self, opcode: int, bus: Bus, pc: int) -> Operation: return Operation("00", "NOP") # Dummy
        def _execute(self, operation: Operation, state: Z80CpuState, bus: Bus) -> None: pass # Dummy

    class DummyDebugger(Debugger):
        def __init__(self, cpu: AbstractCpu):
            super().__init__(cpu)
            # Add some dummy breakpoints
            self.add_breakpoint(BreakpointCondition(BreakpointConditionType.PC_MATCH, value=0x1000))
            self.add_breakpoint(BreakpointCondition(BreakpointConditionType.REGISTER_CHANGE, register_name="A"))

        def get_breakpoints(self) -> List[BreakpointCondition]:
            return self._breakpoints

    app = QApplication([])
    
    cpu = DummyCpu(Bus())
    debugger = DummyDebugger(cpu)

    main_win = QMainWindow()
    bp_view = BreakpointView()
    bp_view.setWindowTitle("Breakpoint View Test")
    main_win.setCentralWidget(bp_view) # For testing, put in central widget
    main_win.setGeometry(100, 100, 400, 300)
    main_win.show()

    # Simulate MainWindow updating the list
    bp_view.set_breakpoints(debugger.get_breakpoints())

    # Simulate adding/removing breakpoints via UI
    # This would normally connect to MainWindow's methods
    bp_view.breakpoint_added.connect(lambda bp: (debugger.add_breakpoint(bp), bp_view.set_breakpoints(debugger.get_breakpoints()), QMessageBox.information(main_win, "Added", str(bp))))
    bp_view.breakpoint_removed.connect(lambda bp: (debugger.remove_breakpoint(bp), bp_view.set_breakpoints(debugger.get_breakpoints()), QMessageBox.information(main_win, "Removed", str(bp))))


    sys.exit(app.exec())
