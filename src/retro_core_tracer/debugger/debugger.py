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
import copy

from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.core.snapshot import Snapshot, BusAccessType, BusAccess
from retro_core_tracer.core.state import CpuState

# @intent:responsibility ブレークポイントの条件タイプを定義します。
class BreakpointConditionType(Enum):
    PC_MATCH = "PC_MATCH"               # プログラムカウンタが特定のアドレスに一致
    MEMORY_READ = "MEMORY_READ"         # 特定のアドレスが読み込まれた
    MEMORY_WRITE = "MEMORY_WRITE"       # 特定のアドレスに書き込まれた
    IO_READ = "IO_READ"                 # 特定のI/Oポートが読み込まれた
    IO_WRITE = "IO_WRITE"               # 特定のI/Oポートに書き込まれた
    REGISTER_VALUE = "REGISTER_VALUE"   # 特定のレジスタが特定の値になった
    REGISTER_CHANGE = "REGISTER_CHANGE" # 特定のレジスタの値が変化した

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
    enabled: bool = True                  # 有効/無効状態

    # @intent:rationale ブレークポイント条件は、一度設定したら変更されないため、不変にします（frozen=True）。

# @intent:responsibility コアエンジンの実行制御とブレークポイント管理を行います。
class Debugger:
    """
    CPUの実行を制御し、ブレークポイントの管理を行うクラス。
    """
    def __init__(self, cpu: AbstractCpu):
        self._cpu = cpu
        self._breakpoints: List[BreakpointCondition] = []
        self._running: bool = False
        self._previous_state = self._cpu.get_state() 
        self._last_snapshot: Optional[Snapshot] = None
        # @intent:responsibility 実行履歴を保持し、タイムトラベルデバッグをサポートします。
        self._history: List[Snapshot] = []
        # @intent:responsibility 履歴が尽きた時に戻るための初期状態を保持します。
        self._initial_state: CpuState = self._cpu.get_state()

    def add_breakpoint(self, condition: BreakpointCondition) -> None:
        """
        ブレークポイント条件を追加します。
        """
        if condition not in self._breakpoints:
            self._breakpoints.append(condition)

    def update_breakpoint(self, old_condition: BreakpointCondition, new_condition: BreakpointCondition) -> None:
        """
        既存のブレークポイントを更新します。
        """
        if old_condition in self._breakpoints:
            idx = self._breakpoints.index(old_condition)
            self._breakpoints[idx] = new_condition

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
        return list(self._breakpoints)

    def get_history(self) -> List[Snapshot]:
        """
        現在の実行履歴を返します。
        """
        return list(self._history)

    def _check_other_breakpoints(self, snapshot: Snapshot) -> bool:
        """
        Snapshotに基づいてPC_MATCH以外のブレークポイントをチェックします。
        """
        current_state = snapshot.state

        for bp in self._breakpoints:
            if not bp.enabled:
                continue

            if bp.condition_type == BreakpointConditionType.MEMORY_READ:
                for access in snapshot.bus_activity:
                    if access.access_type == BusAccessType.READ and access.address == bp.address:
                        return True
            elif bp.condition_type == BreakpointConditionType.MEMORY_WRITE:
                for access in snapshot.bus_activity:
                    if access.access_type == BusAccessType.WRITE and access.address == bp.address:
                        return True
            elif bp.condition_type == BreakpointConditionType.IO_READ:
                for access in snapshot.bus_activity:
                    if access.access_type == BusAccessType.IO_READ and access.address == bp.address:
                        return True
            elif bp.condition_type == BreakpointConditionType.IO_WRITE:
                for access in snapshot.bus_activity:
                    if access.access_type == BusAccessType.IO_WRITE and access.address == bp.address:
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

    def step_instruction(self) -> Snapshot:
        """
        CPUを1命令分実行し、その結果のSnapshotを返します。
        """
        self._previous_state = replace(self._cpu.get_state())
        snapshot = self._cpu.step()
        self._last_snapshot = snapshot
        
        # 履歴に追加
        self._history.append(snapshot)
        
        return snapshot

    def step_back(self) -> Optional[Snapshot]:
        """
        実行履歴を1つ戻り、CPUとメモリの状態を復元します。
        """
        if not self._history:
            return None

        # 1. 履歴から最新のスナップショットを取り出し、削除する
        snapshot_to_revert = self._history.pop()

        # 2. メモリ書き込みの取り消し (Undo)
        # バスへの参照を取得 (protected member access allowed here)
        bus = self._cpu._bus 

        # バスアクティビティを逆順にスキャンし、書き込み操作があれば元に戻す
        for access in reversed(snapshot_to_revert.bus_activity):
            if access.access_type == BusAccessType.WRITE:
                if access.previous_data is not None:
                    # bus.load を使用してメモリを書き戻す（ROMも可）
                    # これはログに残るため、直後にログをクリアする
                    bus.load(access.address, access.previous_data)
                    bus.get_and_clear_activity_log()

        # 3. CPU状態の復元
        if self._history:
            # 1つ前のスナップショットがあれば、その時点の状態に復元
            previous_snapshot = self._history[-1]
            self._cpu.restore_state(previous_snapshot.state)
            self._last_snapshot = previous_snapshot
            return previous_snapshot
        else:
            # 履歴が尽きた場合は初期状態に復元
            self._cpu.restore_state(self._initial_state)
            self._last_snapshot = None
            return None

    def get_last_snapshot(self) -> Optional[Snapshot]:
        return self._last_snapshot

    def run(self) -> None:
        """
        CPUの実行を継続します。
        """
        self._running = True
        
        # Breakpoint at current PC check
        current_pc = self._cpu.get_state().pc
        for bp in self._breakpoints:
            if bp.enabled and bp.condition_type == BreakpointConditionType.PC_MATCH and bp.value == current_pc:
                self.step_instruction()
                break

        while self._running:
            time.sleep(0)
            
            current_pc = self._cpu.get_state().pc
            for bp in self._breakpoints:
                if bp.enabled and bp.condition_type == BreakpointConditionType.PC_MATCH:
                    if bp.value == current_pc:
                        self._running = False
                        print(f"Breakpoint hit at PC: {current_pc:#06x}")
                        return

            snapshot = self.step_instruction()

            if snapshot.operation.mnemonic == "HALT":
                self._running = False
                return

            if self._check_other_breakpoints(snapshot):
                self._running = False
                print(f"Breakpoint hit at PC: {snapshot.state.pc:#06x}")

    def run_back(self) -> None:
        """
        CPUの実行を逆方向（過去）へ連続的に戻します。
        """
        self._running = True
        
        while self._running:
            time.sleep(0)
            
            # 1ステップ戻る
            snapshot = self.step_back()
            
            # 履歴が尽きたら停止
            if snapshot is None:
                self._running = False
                print("Reached start of history.")
                return

            # 復元された状態に対してブレークポイントをチェック
            
            # PC Breakpoint
            current_pc = snapshot.state.pc
            for bp in self._breakpoints:
                if bp.enabled and bp.condition_type == BreakpointConditionType.PC_MATCH:
                    if bp.value == current_pc:
                        self._running = False
                        print(f"Reverse Breakpoint hit at PC: {current_pc:#06x}")
                        return

            # Other Breakpoints (Memory/Register)
            # 戻った時点のSnapshot（＝その命令実行直後の状態）で評価する
            if self._check_other_breakpoints(snapshot):
                self._running = False
                print(f"Reverse Breakpoint hit at PC: {snapshot.state.pc:#06x}")

    def stop(self) -> None:
        self._running = False
