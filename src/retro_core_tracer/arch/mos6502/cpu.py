# src/retro_core_tracer/arch/mos6502/cpu.py
"""
MOS 6502 CPUエミュレーションの中心モジュール。
"""
from typing import Dict, List, Tuple, Optional
from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot
from retro_core_tracer.common.types import RegisterLayoutInfo, RegisterInfo
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.core.state import CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState
# from retro_core_tracer.arch.mos6502.instructions import decode_opcode, execute_instruction (Phase 3で実装)

# @intent:responsibility MOS 6502 CPUの具体的なエミュレーションロジックを提供する。
class Mos6502Cpu(AbstractCpu):
    """
    MOS 6502 CPUをエミュレートするクラス。
    """
    def __init__(self, bus: Bus):
        super().__init__(bus)

    # @intent:responsibility メモリマップドI/Oを使用するためFalseを返す。
    @property
    def has_io_port(self) -> bool:
        return False

    # @intent:responsibility MOS 6502の初期状態を生成する。
    def _create_initial_state(self) -> Mos6502CpuState:
        # P register initial value: 0x24 (R=1, I=1)
        # SP initial value: 0xFD (Power-on default varies, but 0xFD is common)
        # PC initial value: Loaded from Reset Vector ($FFFC/$FFFD) in actual hardware, but here we start at 0.
        return Mos6502CpuState(sp=0xFD)

    # @intent:responsibility 外部公開用のStateを取得する際、SPを物理アドレスに補正する。
    # @intent:rationale マニフェスト原則「スタックポインタの可視化において、物理アドレスへのマッピング補正をCore層で行う」に基づく実装。
    def get_state(self) -> Mos6502CpuState:
        # 内部のSPは8bitだが、外部（UI/Debugger）には物理アドレス（$0100 + SP）として見せる。
        # 注意: ここで補正した新しいStateを返すが、_stateそのものは変更しない。
        internal_state = self._state
        if isinstance(internal_state, Mos6502CpuState):
             # 0xFFとのANDは念のため（内部ロジックで保証すべきだが）
            corrected_sp = 0x0100 | (internal_state.sp & 0xFF)
            return internal_state.replace(sp=corrected_sp)
        return internal_state

    # @intent:responsibility 命令フェッチ。
    def _fetch(self) -> int:
        return self._bus.read(self._state.pc)

    # @intent:responsibility 命令デコード
    def _decode(self, opcode: int) -> Operation:
        from retro_core_tracer.arch.mos6502.instructions.maps import decode_opcode
        return decode_opcode(opcode, self._bus, self._state.pc, self._state)

    # @intent:responsibility 命令実行
    def _execute(self, operation: Operation) -> None:
        from retro_core_tracer.arch.mos6502.instructions.maps import execute_instruction
        
        # @intent:rationale AbstractCpu.step()のフローでは、_execute呼び出し時点で既にPCが
        #                  命令長分進められている（update_pc済み）。
        #                  しかし、6502の命令実行ロジック（execute_instruction内でアドレッシングを再解決する設計）では、
        #                  オペランド読み出しのために「命令の先頭アドレス」が必要となる。
        #                  そのため、ここで一時的にPCを巻き戻したStateを作成して渡す。
        #                  将来的にはAbstractCpuが_executeにinitial_pcを渡すようにリファクタリングすることが望ましい。
        
        # PCを巻き戻した一時的なStateを作成（Stateは不変ではないが、ここでコピー相当の動きをする）
        # 現在のState実装はfrozenではないが、replaceは新しいインスタンスを返す。
        # ただし、実行結果として返ってくるStateは「新しいPC（分岐などで書き換わったもの）」または「実行後の状態」であるべき。
        
        execution_context_state = self._state.replace(pc=(self._state.pc - operation.length) & 0xFFFF)
        
        # 実行。戻り値は更新されたState（分岐していればPCはそのターゲット、していなければ巻き戻ったPCのまま...ではない！）
        # execute_instruction内で「PCの更新」は分岐以外では明示的に行われない。
        # したがって、分岐しなかった場合、result_state.pc は execution_context_state.pc（巻き戻った値）のままになる可能性がある。
        
        result_state = execute_instruction(operation, execution_context_state, self._bus)
        
        # ここで整合性を取る必要がある。
        # Case A: 分岐なし、通常命令
        #   result_state.pc は (initial_pc) のまま。
        #   しかし self._state.pc は (initial_pc + length) になっている。
        #   我々が欲しいのは (initial_pc + length)。
        
        # Case B: 分岐あり (JMP, Branch Taken)
        #   result_state.pc は (target_addr) になっている。
        #   self._state.pc は (initial_pc + length)。
        #   我々が欲しいのは (target_addr)。
        
        # 判定: result_state.pc が execution_context_state.pc と異なれば、PCが操作された（分岐した）とみなす。
        
        if result_state.pc != execution_context_state.pc:
            # 分岐発生。result_stateのPCを採用。
            self._state = result_state
        else:
            # 分岐なし。PC以外の状態（A, X, Y, Flags...）のみを self._state に反映させる必要がある。
            # self._state (PC進み済み) に result_state (PC古い) のレジスタをコピー。
            self._state = result_state.replace(pc=self._state.pc)

    # @intent:responsibility レジスタマップ（UI表示用）を返す。
    def get_register_map(self) -> Dict[str, int]:
        state = self.get_state() # 補正済みSPを取得
        return {
            "A": state.a,
            "X": state.x,
            "Y": state.y,
            "PC": state.pc,
            "S": state.sp, # $01xx
            "P": state.p
        }

    # @intent:responsibility フラグ状態（UI表示用）を返す。
    def get_flag_state(self) -> Dict[str, bool]:
        state = self.get_state()
        return {
            "N": state.flag_n,
            "V": state.flag_v,
            "B": state.flag_b,
            "D": state.flag_d,
            "I": state.flag_i,
            "Z": state.flag_z,
            "C": state.flag_c
        }

    # @intent:responsibility レジスタレイアウト定義を返す。
    def get_register_layout(self) -> List[RegisterLayoutInfo]:
        return [
            RegisterLayoutInfo("Registers", [
                RegisterInfo("A", 8),
                RegisterInfo("X", 8),
                RegisterInfo("Y", 8),
                RegisterInfo("P", 8)
            ]),
            RegisterLayoutInfo("Pointers", [
                RegisterInfo("PC", 16),
                RegisterInfo("S", 16) # Display as 16-bit address
            ])
        ]
    
    # @intent:responsibility 指定範囲の逆アセンブル結果を返す。
    def disassemble(self, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
        from retro_core_tracer.arch.mos6502 import disassembler
        return disassembler.disassemble(self._bus, start_addr, length)

    # @intent:responsibility リセット処理。
    def reset(self) -> None:
        # TODO: Implement Reset Vector loading logic like MC6800
        super().reset()
