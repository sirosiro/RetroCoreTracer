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
        self._use_reset_vector = False

    # @intent:responsibility I/O空間（Port I/O）のサポートを宣言します。MC6800はMMIOを使用するため、Port I/Oはサポートしません。
    @property
    def has_io_port(self) -> bool:
        return False

    # @intent:responsibility リセットベクトルを使用するかどうかを設定します。
    def set_use_reset_vector(self, use: bool) -> None:
        self._use_reset_vector = use

    # @intent:responsibility MC6800の初期状態を生成します。
    def _create_initial_state(self) -> Mc6800CpuState:
        return Mc6800CpuState()

    # @intent:responsibility CPUをリセットします。MC6800の場合、オプションでリセットベクトルを読み込みます。
    def reset(self) -> None:
        """
        CPUをリセットします。
        use_reset_vector が True の場合、$FFFE-$FFFF から開始アドレスを読み込みます。
        """
        super().reset() # _state を初期化
        
        if self._use_reset_vector:
            # @intent:rationale MC6800の実機仕様に基づき、リセット時に $FFFE-$FFFF からPCを読み込みます。
            # バス経由で直接読み込むため、メモリが正しくロードされている必要があります。
            try:
                hi = self._bus.peek(0xFFFE)
                lo = self._bus.peek(0xFFFF)
                self._state.pc = (hi << 8) | lo
            except IndexError:
                # ベクタ領域がマップされていない場合は、デフォルト(0x0000)のままにするか警告
                pass

    # @intent:responsibility メモリから次のオペコードをフェッチします。
    def _fetch(self) -> int:
        return self._bus.read(self._state.pc)

    # @intent:responsibility オペコードをデコードし、Operationオブジェクトを返します。
    def _decode(self, opcode: int) -> Operation:
        return decode_opcode(opcode, self._bus, self._state.pc)

    # @intent:responsibility Operationを実行し、状態を更新します。
    def _execute(self, operation: Operation) -> None:
        execute_instruction(operation, self._state, self._bus)



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