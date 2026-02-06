# tests/core/test_cpu.py
"""
retro_core_tracer.core.cpuモジュールの単体テスト。
"""
import pytest
from dataclasses import dataclass

from retro_core_tracer.core.state import CpuState
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.core.snapshot import Snapshot, Operation, Metadata
from retro_core_tracer.transport.bus import Bus, RAM, Device

# @intent:test_suite CPUの状態管理と抽象CPUの基本的な動作を検証します。

# テスト用の具体的なCPU実装
# @intent:test_helper AbstractCpuのテストのために、最小限の機能を持つ具象CPUクラスを定義します。
class TestCpu(AbstractCpu):
    def __init__(self, bus: Bus, initial_pc: int = 0x0000, initial_sp: int = 0x0000):
        self._initial_pc = initial_pc
        self._initial_sp = initial_sp
        super().__init__(bus)
        self._mock_opcode = 0x00 # Default NOP opcode for testing
        self._decoded_operation = Operation(opcode_hex="00", mnemonic="NOP")

    # @intent:responsibility TestCpuの初期状態を作成します。
    def _create_initial_state(self) -> CpuState:
        return CpuState(pc=self._initial_pc, sp=self._initial_sp)

    # @intent:responsibility テスト目的で常に固定のオペコードをフェッチし、PCをインクリメントします。
    def _fetch(self) -> int:
        opcode = self._bus.read(self._state.pc) # Read from bus at current PC
        self._state.pc += 1 # Increment PC after fetch
        return opcode

    # @intent:responsibility テスト目的で固定のOperationオブジェクトを返します。
    def _decode(self, opcode: int) -> Operation:
        # Simple decode: always return a NOP operation for testing
        # Can be made more complex if needed for specific test cases
        if opcode == 0x00:
            return Operation(opcode_hex=f"{opcode:02X}", mnemonic="NOP")
        else:
            return Operation(opcode_hex=f"{opcode:02X}", mnemonic="UNKNOWN")

    # @intent:responsibility テスト目的で何もしません（実行ロジックは具体的なCPUで実装）。
    def _execute(self, operation: Operation) -> None:
        # This TestCpu does not perform actual execution logic
        pass

    # @intent:test_helper テストでフェッチされるオペコードを設定します。
    def set_mock_opcode(self, opcode: int):
        self._mock_opcode = opcode

class TestCpuState:
    """
    CpuStateの単体テスト。
    """
    # @intent:test_case_init デフォルト値でCpuStateが正しく初期化されることを検証します。
    def test_cpu_state_init_default(self):
        state = CpuState()
        assert state.pc == 0x0000
        assert state.sp == 0x0000

    # @intent:test_case_init 指定された値でCpuStateが正しく初期化されることを検証します。
    def test_cpu_state_init_with_values(self):
        state = CpuState(pc=0x1234, sp=0xABCD)
        assert state.pc == 0x1234
        assert state.sp == 0xABCD

    # @intent:test_case_mutability CpuStateの属性が変更可能であることを検証します。
    def test_cpu_state_mutability(self):
        state = CpuState()
        state.pc = 0x1000
        state.sp = 0x2000
        assert state.pc == 0x1000
        assert state.sp == 0x2000

class TestAbstractCpu:
    """
    AbstractCpuの抽象メソッドと具象メソッドのテスト。
    """
    # 各テストケースの前に新しいBusとTestCpuのインスタンスを作成します。
    @pytest.fixture
    def setup_cpu(self):
        bus = Bus()
        # テスト用に小さなRAMをバスに接続
        ram = RAM(256) # 0x00 - 0xFF
        bus.register_device(0x0000, 0x00FF, ram)
        cpu = TestCpu(bus, initial_pc=0x0010, initial_sp=0x00F0) # Adjust initial PC for bus read
        return cpu, bus, ram

    # @intent:test_case_init TestCpuがAbstractCpuとして正しく初期化されることを検証します。
    def test_abstract_cpu_init(self, setup_cpu):
        cpu, _, _ = setup_cpu
        state = cpu.get_state()
        assert state.pc == 0x0010
        assert state.sp == 0x00F0
        assert isinstance(state, CpuState)

    # @intent:test_case_reset CPUがリセット時に初期状態に戻ることを検証します。
    def test_abstract_cpu_reset(self, setup_cpu):
        cpu, _, _ = setup_cpu
        # 状態を変更
        cpu.get_state().pc = 0xAAAA
        cpu.get_state().sp = 0xBBBB
        assert cpu.get_state().pc == 0xAAAA

        cpu.reset()
        state = cpu.get_state()
        assert state.pc == 0x0010 # 初期値に戻る
        assert state.sp == 0x00F0 # 初期値に戻る

    # @intent:test_case_get_state get_stateが現在のCPU状態を返すことを検証します。
    def test_abstract_cpu_get_state(self, setup_cpu):
        cpu, _, _ = setup_cpu
        state = cpu.get_state()
        assert state.pc == 0x0010
        state.pc = 0x3333 # 取得した状態を変更
        assert cpu.get_state().pc == 0x3333 # CPUの内部状態も変更されていることを確認

    # @intent:test_case_step stepメソッドがフェッチ、デコード、実行をオーケストレートし、Snapshotを返すことを検証します。
    def test_abstract_cpu_step(self, setup_cpu):
        cpu, bus, ram = setup_cpu
        initial_pc = cpu.get_state().pc
        initial_sp = cpu.get_state().sp # SP is not changed by TestCpu step

        # Busにテスト用のオペコードを書き込む
        test_opcode = 0x12 # Example opcode
        bus.write(initial_pc, test_opcode)

        # 1ステップ実行
        snapshot = cpu.step()

        # PCが1インクリメントされていることを確認 (fetchで)
        assert cpu.get_state().pc == initial_pc + 1
        assert cpu.get_state().sp == initial_sp

        # Snapshotの内容を検証
        assert isinstance(snapshot, Snapshot)
        assert snapshot.state == cpu.get_state() # 実行後の状態
        assert snapshot.operation.opcode_hex == f"{test_opcode:02X}"
        assert snapshot.operation.mnemonic == "UNKNOWN" # _decodeでUNKNOWNを返すため
        assert snapshot.metadata.cycle_count == 0 # 現状はダミー
        assert snapshot.metadata.symbol_info == f"PC: {initial_pc:#06x} -> UNKNOWN"
        assert snapshot.bus_activity == [] # 現状は空リスト
