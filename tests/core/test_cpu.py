# tests/core/test_cpu.py
"""
retro_core_tracer.core.cpuモジュールの単体テスト。
"""
import pytest
from dataclasses import dataclass
from typing import Dict, List, Tuple

from retro_core_tracer.core.state import CpuState
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.core.snapshot import Snapshot, Operation, Metadata
from retro_core_tracer.transport.bus import Bus, RAM, Device
from retro_core_tracer.common.types import RegisterLayoutInfo, RegisterInfo

# @intent:test_suite CPUの状態管理と抽象CPUの基本的な動作を検証します。

class TestCpu(AbstractCpu):
    def __init__(self, bus: Bus, initial_pc: int = 0x0000, initial_sp: int = 0x0000):
        self._initial_pc = initial_pc
        self._initial_sp = initial_sp
        super().__init__(bus)
        self._mock_opcode = 0x00 
        self._decoded_operation = Operation(opcode_hex="00", mnemonic="NOP")

    # @intent:responsibility I/O空間のサポート有無を返します。テスト用はFalse固定。
    @property
    def has_io_port(self) -> bool:
        return False

    def _create_initial_state(self) -> CpuState:
        return CpuState(pc=self._initial_pc, sp=self._initial_sp)

    def _fetch(self) -> int:
        opcode = self._bus.read(self._state.pc) 
        self._state.pc += 1 
        return opcode

    def _decode(self, opcode: int) -> Operation:
        if opcode == 0x00:
            return Operation(opcode_hex=f"{opcode:02X}", mnemonic="NOP")
        else:
            return Operation(opcode_hex=f"{opcode:02X}", mnemonic="UNKNOWN")

    def _execute(self, operation: Operation) -> None:
        self._bus.write(0x0020, 0xFF)

    def set_mock_opcode(self, opcode: int):
        self._mock_opcode = opcode

    # --- UI向けAPIの実装 ---
    def get_register_map(self) -> Dict[str, int]:
        """テスト用CPUのレジスタ状態を返します。"""
        return {"PC": self._state.pc, "SP": self._state.sp}

    def get_register_layout(self) -> List[RegisterLayoutInfo]:
        """テスト用CPUのレジスタレイアウトを定義します。"""
        return [
            RegisterLayoutInfo("Test Group", [
                RegisterInfo("PC", 16),
                RegisterInfo("SP", 16)
            ])
        ]

    def get_flag_state(self) -> Dict[str, bool]:
        """テスト用CPUのフラグ状態（ダミー）を返します。"""
        return {"Z": False}

    def disassemble(self, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
        """テスト用CPUの逆アセンブル結果（ダミー）を返します。"""
        result = []
        for i in range(length):
            addr = start_addr + i
            result.append((addr, "00", "NOP"))
        return result

class TestCpuState:
    """
    CpuStateの単体テスト。
    """
    def test_cpu_state_init_default(self):
        state = CpuState()
        assert state.pc == 0x0000
        assert state.sp == 0x0000

    def test_cpu_state_init_with_values(self):
        state = CpuState(pc=0x1234, sp=0xABCD)
        assert state.pc == 0x1234
        assert state.sp == 0xABCD

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
    @pytest.fixture
    def setup_cpu(self):
        bus = Bus()
        ram = RAM(256) 
        bus.register_device(0x0000, 0x00FF, ram)
        cpu = TestCpu(bus, initial_pc=0x0010, initial_sp=0x00F0) 
        return cpu, bus, ram

    def test_abstract_cpu_init(self, setup_cpu):
        cpu, _, _ = setup_cpu
        state = cpu.get_state()
        assert state.pc == 0x0010
        assert state.sp == 0x00F0
        assert isinstance(state, CpuState)

    def test_abstract_cpu_reset(self, setup_cpu):
        cpu, _, _ = setup_cpu
        cpu.get_state().pc = 0xAAAA
        cpu.get_state().sp = 0xBBBB
        assert cpu.get_state().pc == 0xAAAA

        cpu.reset()
        state = cpu.get_state()
        assert state.pc == 0x0010 
        assert state.sp == 0x00F0 

    def test_abstract_cpu_get_state(self, setup_cpu):
        cpu, _, _ = setup_cpu
        state = cpu.get_state()
        assert state.pc == 0x0010
        state.pc = 0x3333 
        assert cpu.get_state().pc == 0x3333 

    def test_abstract_cpu_step(self, setup_cpu):
        from retro_core_tracer.transport.bus import BusAccessType

        cpu, bus, ram = setup_cpu
        initial_pc = cpu.get_state().pc
        initial_sp = cpu.get_state().sp 

        test_opcode = 0x12 
        bus.write(initial_pc, test_opcode)
        
        bus.get_and_clear_activity_log()

        snapshot = cpu.step()

        assert cpu.get_state().pc == initial_pc + 1
        assert cpu.get_state().sp == initial_sp

        assert isinstance(snapshot, Snapshot)
        assert snapshot.state == cpu.get_state() 
        assert snapshot.operation.opcode_hex == f"{test_opcode:02X}"
        assert snapshot.operation.mnemonic == "UNKNOWN" 
        
        assert isinstance(snapshot.metadata.cycle_count, int)
        assert snapshot.metadata.symbol_info == "UNKNOWN"
        assert len(snapshot.bus_activity) == 2
        
        assert snapshot.bus_activity[0].address == initial_pc
        assert snapshot.bus_activity[0].data == test_opcode
        assert snapshot.bus_activity[0].access_type == BusAccessType.READ
        
        assert snapshot.bus_activity[1].address == 0x0020
        assert snapshot.bus_activity[1].data == 0xFF
        assert snapshot.bus_activity[1].access_type == BusAccessType.WRITE

    # --- UI向けAPIのテストを追加 ---
    def test_ui_api_integration(self, setup_cpu):
        cpu, _, _ = setup_cpu
        
        # Register Map
        reg_map = cpu.get_register_map()
        assert reg_map["PC"] == 0x0010
        assert reg_map["SP"] == 0x00F0
        
        # Register Layout
        layout = cpu.get_register_layout()
        assert len(layout) == 1
        assert layout[0].group_name == "Test Group"
        assert len(layout[0].registers) == 2
        
        # Flags
        flags = cpu.get_flag_state()
        assert flags["Z"] is False
        
        # Disassemble
        asm = cpu.disassemble(0x0000, 2)
        assert len(asm) == 2
        assert asm[0] == (0x0000, "00", "NOP")