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
from retro_core_tracer.core.state import CpuState

# @intent:responsibility ブレークポイントの条件タイプを定義します。
class BreakpointConditionType(Enum):
    PC_MATCH = "PC_MATCH"               # プログラムカウンタが特定のアドレスに一致
    MEMORY_READ = "MEMORY_READ"         # 特定のアドレスが読み込まれた
    MEMORY_WRITE = "MEMORY_WRITE"       # 特定のアドレスに書き込まれた
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
        return snapshot

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

    def stop(self) -> None:
        self._running = False