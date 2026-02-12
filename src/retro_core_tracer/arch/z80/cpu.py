# retro_core_tracer/arch/z80/cpu.py
"""
Z80 CPUエミュレーションの中心モジュール。

このモジュールはZ80 CPUの具体的な実装を提供し、
AbstractCpuインターフェースを実装します。
"""
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation, Metadata, Snapshot # Snapshotも必要
from retro_core_tracer.arch.z80.instructions import decode_opcode, execute_instruction
from retro_core_tracer.arch.z80 import disassembler
from typing import Dict, List, Tuple
from retro_core_tracer.common.types import RegisterLayoutInfo, RegisterInfo

# @intent:responsibility Z80 CPUの具体的なエミュレーションロジックを提供します。
class Z80Cpu(AbstractCpu):
    """
    Z80 CPUをエミュレートするクラス。
    AbstractCpuを継承し、Z80固有の動作を実装します。
    """
    # @intent:responsibility Z80Cpuの初期化を行います。
    # @intent:pre-condition `bus`は有効なBusオブジェクトである必要があります。
    def __init__(self, bus: Bus):
        super().__init__(bus)

    # @intent:responsibility I/O空間（Port I/O）のサポートを宣言します。Z80は独立したI/O空間を持ちます。
    @property
    def has_io_port(self) -> bool:
        return True

    # @intent:responsibility Z80 CPUの初期状態（Z80CpuState）を生成します。
    def _create_initial_state(self) -> Z80CpuState:
        # Z80のリセット時の初期値は通常0だが、エミュレータによっては異なる設定も可能。
        # ここではデフォルトのZ80CpuStateインスタンスを返す。
        return Z80CpuState()

    # @intent:responsibility 現在のPCからオペコードをフェッチします。PCのインクリメントはこの時点では行わず、
    #                  stepメソッド内で命令長に応じて更新します。
    def _fetch(self) -> int:
        # フェッチ時のバスアクセス（読み込み）はBusクラスによって自動的に記録されます。
        return self._bus.read(self._state.pc)

    # @intent:responsibility フェッチしたオペコードをデコードし、Operationオブジェクトを返します。
    # @intent:rationale 実際のデコードロジックは`instructions.py`に委譲します。
    def _decode(self, opcode: int) -> Operation:
        # pcをdecode_opcodeに渡すのは、マルチバイト命令のオペランド読み込みのため
        return decode_opcode(opcode, self._bus, self._state.pc)

    # @intent:responsibility デコードされた命令を実行し、Z80の状態を更新します。
    # @intent:rationale 実際の実行ロジックは`instructions.py`に委譲します。
    def _execute(self, operation: Operation) -> None:
        # _executeにbusを渡すのは、メモリ操作を伴う命令があるため
        execute_instruction(operation, self._state, self._bus)

    # @intent:responsibility CPUを1命令サイクル進め、その結果のスナップショットを返します。
    # @intent:rationale このメソッドはフェッチ、デコード、実行のプロセスを内部で管理し、
    #                  その結果をUIやデバッガが利用可能な不変のSnapshotとして提供します。
    def step(self) -> Snapshot:
        initial_pc = self._state.pc # フェッチ前のPCを保存

        # 各命令実行前のバスアクティビティログをクリア
        self._bus.get_and_clear_activity_log()

        if self._state.halted:
            # @intent:responsibility CPUがHALT状態の場合、NOP命令として振る舞い、PCを維持します。
            # HALT中はバスアクティビティは発生しません（メモリ読み込みは行わない）。
            operation = Operation(opcode_hex="76", mnemonic="HALT (suspended)", cycle_count=4, length=0)
            self._cycle_count += operation.cycle_count
            bus_activity = []
            snapshot = Snapshot(
                state=self.get_state(),
                operation=operation,
                metadata=Metadata(cycle_count=self._cycle_count, symbol_info=f"PC: {initial_pc:#06x} -> HALT (suspended)"),
                bus_activity=bus_activity,
            )
            return snapshot

        # フェッチ
        opcode = self._fetch() # fetch_opcode_byte from current PC and log in bus

        # デコード
        operation = self._decode(opcode)

        # PCを命令長分進める
        self._state.pc = (self._state.pc + operation.length) & 0xFFFF

        # 実行
        self._execute(operation) # execute_instruction will use self._bus and log its activities

        # この命令サイクルで発生したすべてのバスアクティビティを取得
        bus_activity = self._bus.get_and_clear_activity_log()

        # サイクルカウントを更新
        self._cycle_count += operation.cycle_count

        # シンボル情報の取得
        symbol_label = self._reverse_symbol_map.get(initial_pc, "")
        symbol_info = f"{symbol_label}: " if symbol_label else ""
        symbol_info += f"{operation.mnemonic}"
        if operation.operands:
            symbol_info += " " + ", ".join(operation.operands)

        # スナップショットの生成
        snapshot = Snapshot(
            state=self.get_state(), # 実行後の状態
            operation=operation,
            metadata=Metadata(cycle_count=self._cycle_count, symbol_info=symbol_info),
            bus_activity=bus_activity, # Actual bus activity
        )
        return snapshot

    def get_register_map(self) -> Dict[str, int]:
        s = self._state
        return {
            "A": s.a, "F": s.f, "B": s.b, "C": s.c, "D": s.d, "E": s.e, "H": s.h, "L": s.l,
            "A'": s.a_, "F'": s.f_, "B'": s.b_, "C'": s.c_, "D'": s.d_, "E'": s.e_, "H'": s.h_, "L'": s.l_,
            "IX": s.ix, "IY": s.iy, "SP": s.sp, "PC": s.pc,
            "I": s.i, "R": s.r,
            "AF": s.af, "BC": s.bc, "DE": s.de, "HL": s.hl,
            "AF'": s.af_, "BC'": s.bc_, "DE'": s.de_, "HL'": s.hl_,
            "IM": s.im
        }

    def get_register_layout(self) -> List[RegisterLayoutInfo]:
        return [
            RegisterLayoutInfo("Main Registers", [
                RegisterInfo("AF", 16), RegisterInfo("BC", 16), RegisterInfo("DE", 16), RegisterInfo("HL", 16)
            ]),
            RegisterLayoutInfo("Alternate Registers", [
                RegisterInfo("AF'", 16), RegisterInfo("BC'", 16), RegisterInfo("DE'", 16), RegisterInfo("HL'", 16)
            ]),
            RegisterLayoutInfo("Index & Control", [
                RegisterInfo("IX", 16), RegisterInfo("IY", 16), RegisterInfo("SP", 16), RegisterInfo("PC", 16)
            ]),
            RegisterLayoutInfo("Special", [
                RegisterInfo("I", 8), RegisterInfo("R", 8), RegisterInfo("IM", 8)
            ])
        ]

    def get_flag_state(self) -> Dict[str, bool]:
        s = self._state
        return {
            "S": s.flag_s,
            "Z": s.flag_z,
            "H": s.flag_h,
            "PV": s.flag_pv,
            "N": s.flag_n,
            "C": s.flag_c
        }

    def disassemble(self, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
        return disassembler.disassemble(self._bus, start_addr, length)