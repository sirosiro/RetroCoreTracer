# retro_core_tracer/debugger/debugger.py
"""
デバッガモジュール。

コアエンジンの実行を制御し、ユーザーが指定した条件（ブレークポイント）で
実行を中断させる責務を負います。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from dataclasses import replace
import time

from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.core.snapshot import Snapshot, BusAccessType, BusAccess
from retro_core_tracer.core.state import CpuState # Import CpuState

# @intent:responsibility ブレークポイントの条件タイプを定義します。
class BreakpointConditionType(Enum):
    PC_MATCH = "PC_MATCH"               # プログラムカウンタが特定のアドレスに一致
    MEMORY_READ = "MEMORY_READ"         # 特定のアドレスが読み込まれた
    MEMORY_WRITE = "MEMORY_WRITE"       # 特定のアドレスに書き込まれた
    REGISTER_VALUE = "REGISTER_VALUE"   # 特定のレジスタが特定の値になった
    REGISTER_CHANGE = "REGISTER_CHANGE" # 特定のレジスタの値が変化した (実装は複雑)

# @intent:responsibility ブレークポイントをトリガーする条件を定義します。
@dataclass(frozen=True)
class BreakpointCondition:
    """
    ブレークポイントがヒットするための条件を定義するデータクラス。
    """
    condition_type: BreakpointConditionType
    value: Optional[int] = None           # PC_MATCH, REGISTER_VALUEで使用
    address: Optional[int] = None         # MEMORY_READ, MEMORY_WRITEで使用
    register_name: Optional[str] = None   # REGISTER_VALUE, REGISTER_CHANGEで使用

    # @intent:rationale ブレークポイント条件は、一度設定したら変更されないため、不変にします（frozen=True）。

# @intent:responsibility コアエンジンの実行制御とブレークポイント管理を行います。
class Debugger:
    """
    CPUの実行を制御し、ブレークポイントの管理を行うクラス。
    """
    # @intent:responsibility デバッガを初期化し、制御するCPUへの参照を保持します。
    # @intent:pre-condition `cpu`は有効なAbstractCpuオブジェクトである必要があります。
    def __init__(self, cpu: AbstractCpu):
        self._cpu = cpu
        self._breakpoints: List[BreakpointCondition] = []
        self._running: bool = False # 連続実行中かどうか
        # REGISTER_CHANGEのため、前回のCPU状態を保持する必要がある
        self._previous_state = self._cpu.get_state() 
        self._last_snapshot: Optional[Snapshot] = None # 最後に実行したSnapshotを保持

    # @intent:responsibility ブレークポイントを追加します。
    def add_breakpoint(self, condition: BreakpointCondition) -> None:
        """
        ブレークポイント条件を追加します。
        """
        if condition not in self._breakpoints:
            self._breakpoints.append(condition)

    # @intent:responsibility ブレークポイントを削除します。
    def remove_breakpoint(self, condition: BreakpointCondition) -> None:
        """
        ブレークポイント条件を削除します。
        """
        if condition in self._breakpoints:
            self._breakpoints.remove(condition)

    def get_breakpoints(self) -> List[BreakpointCondition]:
        """
        現在設定されている全てのブレークポイントのリストを返します。
        """
        return list(self._breakpoints) # リストのコピーを返す

    # @intent:responsibility 現在のスナップショットに対してPC以外のブレークポイントがヒットしたかをチェックします。
    # @intent:rationale このメソッドはstep()やrun()の内部で呼び出され、実行を中断するかどうかを決定します。
    #                   PC_MATCHブレークポイントはrun()メソッド内でstep()呼び出し前にチェックされます。
    def _check_other_breakpoints(self, snapshot: Snapshot) -> bool:
        """
        与えられたSnapshotに基づいて、設定されているPC_MATCH以外のブレークポイントに
        ヒットしたかどうかをチェックします。
        """
        current_state = snapshot.state

        for bp in self._breakpoints:
            if bp.condition_type == BreakpointConditionType.MEMORY_READ:
                for access in snapshot.bus_activity:
                    if access.access_type == BusAccessType.READ and access.address == bp.address:
                        return True
            elif bp.condition_type == BreakpointConditionType.MEMORY_WRITE:
                for access in snapshot.bus_activity:
                    if access.access_type == BusAccessType.WRITE and access.address == bp.address:
                        return True
            elif bp.condition_type == BreakpointConditionType.REGISTER_VALUE:
                if bp.register_name:
                    if hasattr(current_state, bp.register_name):
                        if getattr(current_state, bp.register_name) == bp.value:
                            return True
            elif bp.condition_type == BreakpointConditionType.REGISTER_CHANGE:
                if bp.register_name and self._previous_state:
                    if hasattr(current_state, bp.register_name) and hasattr(self._previous_state, bp.register_name):
                        if getattr(current_state, bp.register_name) != getattr(self._previous_state, bp.register_name):
                            return True

        return False

    # _check_register_change_breakpointは_check_other_breakpointsに統合されたため削除可能ですが、
    # 外部から呼ばれる可能性を考慮して残すか削除するか検討が必要です。
    # ここでは、よりクリーンな実装のために内部的な統合を優先します。

    # @intent:responsibility CPUの実行を1命令分進めます。
    def step_instruction(self) -> Snapshot:
        """
        CPUを1命令分実行し、その結果のSnapshotを返します。
        """
        # _previous_stateは、今回の命令実行前の状態を保持する
        self._previous_state = replace(self._cpu.get_state()) # 命令実行前の状態をコピー
        
        snapshot = self._cpu.step() # 命令を実行し、その結果のSnapshotを取得
        self._last_snapshot = snapshot
        
        return snapshot

    def get_last_snapshot(self) -> Optional[Snapshot]:
        """
        最後に実行されたステップのSnapshotを返します。
        """
        return self._last_snapshot

    # @intent:responsibility ブレークポイントにヒットするか、停止するまでCPUの実行を継続します。
    # @intent:rationale PC_MATCHブレークポイントは命令実行前にチェックされ、
    #                   その他のブレークポイントは命令実行後にチェックされます。
    def run(self) -> None:
        """
        CPUの実行を継続し、ブレークポイントにヒットするか、
        stop()が呼び出されるまで繰り返します。
        """
        self._running = True
        print("Debugger: Run loop started") # DEBUG

        # 現在のPC位置にブレークポイントがある場合、そこから抜け出すために1ステップ実行する
        current_pc = self._cpu.get_state().pc
        for bp in self._breakpoints:
            if bp.condition_type == BreakpointConditionType.PC_MATCH and bp.value == current_pc:
                print(f"Debugger: Stepping over breakpoint at {current_pc:#04x}")
                self.step_instruction()
                # HALTチェックなどをここでもやるべきだが、とりあえずループ内でキャッチされる
                break

        while self._running:
            # PythonのGIL(Global Interpreter Lock)を一時的に解放し、
            # メインスレッド（GUI）が停止要求(stop)を処理したり、イベントを処理したりする時間を確保する。
            # time.sleep(0)はOSに対してタイムスライスを譲る動作となる。
            time.sleep(0)
            
            # print(f"Debugger: Looping... running={self._running}, PC={self._cpu.get_state().pc:04X}") # DEBUG (Too verbose, enable if needed)

            # PC_MATCHブレークポイントを命令実行前にチェック
            current_pc = self._cpu.get_state().pc
            for bp in self._breakpoints:
                if bp.condition_type == BreakpointConditionType.PC_MATCH:
                    # print(f"Checking BP: PC={current_pc:#04x} BP={bp.value:#04x}") # DEBUG
                    if bp.value == current_pc:
                        self._running = False
                        print(f"Breakpoint hit at PC: {current_pc:#06x}")
                        return # ブレークポイントヒットで停止

            snapshot = self.step_instruction()

            # HALT命令が実行されたら停止する
            if snapshot.operation.mnemonic == "HALT":
                self._running = False
                print("Debugger: HALT instruction executed. Stopping.")
                return

            # PC_MATCH以外のブレークポイントをチェック
            if self._check_other_breakpoints(snapshot):
                self._running = False # ブレークポイントヒットで停止
                print(f"Breakpoint hit at PC: {snapshot.state.pc:#06x}")
            # TODO: 最大実行ステップ数などの制限も考慮

    # @intent:responsibility 連続実行を停止するように指示します。
    def stop(self) -> None:
        """
        CPUの連続実行を停止します。run()メソッド内でチェックされます。
        """
        print("Debugger: Stop requested") # DEBUG
        self._running = False
