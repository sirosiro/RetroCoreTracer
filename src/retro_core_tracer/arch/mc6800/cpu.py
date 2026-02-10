# src/retro_core_tracer/arch/mc6800/cpu.py
"""
MC6800 CPUエミュレーションの中心モジュール。
"""
from typing import Dict, List, Tuple
from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot
from retro_core_tracer.common.types import RegisterLayoutInfo, RegisterInfo
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.arch.mc6800.state import Mc6800CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.instructions import decode_opcode, execute_instruction
from retro_core_tracer.arch.mc6800 import disassembler

# @intent:responsibility MC6800 CPUの具体的なエミュレーションロジック（フェッチ、デコード、実行）を提供します。
class Mc6800Cpu(AbstractCpu):
    """
    MC6800 CPUをエミュレートするクラス。
    """
    # @intent:responsibility Mc6800Cpuを初期化します。
    def __init__(self, bus: Bus):
        super().__init__(bus)

    # @intent:responsibility MC6800の初期状態を生成します。
    def _create_initial_state(self) -> Mc6800CpuState:
        return Mc6800CpuState()

    # @intent:responsibility メモリから次のオペコードをフェッチします。
    def _fetch(self) -> int:
        return self._bus.read(self._state.pc)

    # @intent:responsibility オペコードをデコードし、Operationオブジェクトを返します。
    def _decode(self, opcode: int) -> Operation:
        return decode_opcode(opcode, self._bus, self._state.pc)

    # @intent:responsibility Operationを実行し、状態を更新します。
    def _execute(self, operation: Operation) -> None:
        execute_instruction(operation, self._state, self._bus)

    # @intent:responsibility 1命令サイクルを実行し、その結果のスナップショットを生成して返します。
    # @intent:flow フェッチ -> デコード -> PC更新 -> 実行 -> スナップショット生成 の順序で処理を行います。
    def step(self) -> Snapshot:
        initial_pc = self._state.pc
        self._bus.get_and_clear_activity_log()

        opcode = self._fetch()
        operation = self._decode(opcode)
        
        # MC6800では命令実行前にPCを次の命令へ進めるのが一般的
        self._state.pc = (self._state.pc + operation.length) & 0xFFFF
        
        self._execute(operation)
        
        bus_activity = self._bus.get_and_clear_activity_log()
        self._cycle_count += operation.cycle_count

        symbol_label = self._reverse_symbol_map.get(initial_pc, "")
        symbol_info = f"{symbol_label}: " if symbol_label else ""
        symbol_info += f"{operation.mnemonic}"
        if operation.operands:
            symbol_info += " " + ", ".join(operation.operands)

        return Snapshot(
            state=self.get_state(),
            operation=operation,
            metadata=Metadata(cycle_count=self._cycle_count, symbol_info=symbol_info),
            bus_activity=bus_activity
        )

    # @intent:responsibility UI表示用に、現在のレジスタ値を辞書形式で提供します。
    def get_register_map(self) -> Dict[str, int]:
        s = self._state
        return {
            "A": s.a, "B": s.b, "X": s.x, "SP": s.sp, "PC": s.pc, "CC": s.cc
        }

    # @intent:responsibility UIのレジスタ表示レイアウト（グループ化）を定義します。
    def get_register_layout(self) -> List[RegisterLayoutInfo]:
        return [
            RegisterLayoutInfo("Accumulators/Flags", [
                RegisterInfo("A", 8), RegisterInfo("B", 8), RegisterInfo("CC", 8)
            ]),
            RegisterLayoutInfo("Index/Pointers", [
                RegisterInfo("X", 16), RegisterInfo("SP", 16), RegisterInfo("PC", 16)
            ])
        ]

    # @intent:responsibility UI表示用に、現在のフラグ状態を辞書形式で提供します。
    def get_flag_state(self) -> Dict[str, bool]:
        s = self._state
        return {
            "H": s.flag_h, "I": s.flag_i, "N": s.flag_n, "Z": s.flag_z, "V": s.flag_v, "C": s.flag_c
        }

    # @intent:responsibility 指定範囲のメモリを逆アセンブルします。
    def disassemble(self, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
        return disassembler.disassemble(self._bus, start_addr, length)
