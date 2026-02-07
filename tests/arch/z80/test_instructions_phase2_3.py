# tests/arch/z80/test_instructions_phase2_3.py
"""
Z80命令セット拡張（Phase 2 & 3）の単体テスト。
スタック操作、サブルーチンコール、および拡張演算命令を検証します。
"""
import pytest

from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.z80.state import Z80CpuState

class TestZ80InstructionsExtended:
    """
    Phase 2 (Stack/Call) & Phase 3 (Extended Arithmetic) のテストケース。
    """

    @pytest.fixture
    def setup_cpu(self):
        bus = Bus()
        ram = RAM(0x10000)
        bus.register_device(0x0000, 0xFFFF, ram)
        cpu = Z80Cpu(bus)
        # スタックポインタを安全な領域に初期化
        cpu.get_state().sp = 0xFFFE
        return cpu, bus

    # --- Phase 1: HALT ---
    def test_halt_execution(self, setup_cpu):
        cpu, bus = setup_cpu
        state = cpu.get_state()
        pc = 0x1000
        state.pc = pc
        
        # HALT (0x76)
        bus.write(pc, 0x76)
        
        # 1. Execute HALT
        snapshot = cpu.step()
        assert snapshot.operation.mnemonic == "HALT"
        assert state.halted is True
        assert state.pc == pc + 1  # PC should advance past HALT instruction

        # 2. Step while halted
        snapshot_suspended = cpu.step()
        assert snapshot_suspended.operation.mnemonic == "HALT (suspended)"
        assert state.pc == pc + 1  # PC should NOT advance
        assert len(snapshot_suspended.bus_activity) == 0

    # --- Phase 2: Stack & Call ---
    def test_push_pop_bc(self, setup_cpu):
        cpu, bus = setup_cpu
        state = cpu.get_state()
        pc = 0x1000
        state.pc = pc
        
        # PUSH BC (0xC5) -> POP DE (0xD1) to verify value transfer
        bus.write(pc, 0xC5)     # PUSH BC
        bus.write(pc + 1, 0xD1) # POP DE
        
        state.b = 0x12
        state.c = 0x34
        initial_sp = state.sp
        
        # Execute PUSH BC
        cpu.step()
        assert state.sp == initial_sp - 2
        assert bus.read(state.sp) == 0x34   # Low byte
        assert bus.read(state.sp + 1) == 0x12 # High byte
        
        # Execute POP DE
        cpu.step()
        assert state.sp == initial_sp
        assert state.d == 0x12
        assert state.e == 0x34

    def test_call_ret(self, setup_cpu):
        cpu, bus = setup_cpu
        state = cpu.get_state()
        pc = 0x1000
        subroutine = 0x2000
        
        state.pc = pc
        initial_sp = state.sp
        
        # CALL 0x2000 (0xCD 0x00 0x20)
        bus.write(pc, 0xCD)
        bus.write(pc + 1, 0x00)
        bus.write(pc + 2, 0x20)
        
        # At 0x2000: RET (0xC9)
        bus.write(subroutine, 0xC9)
        
        # 1. Execute CALL
        cpu.step()
        assert state.pc == subroutine
        assert state.sp == initial_sp - 2
        # Stack should contain return address (pc + 3)
        ret_addr = pc + 3
        assert bus.read(state.sp) == (ret_addr & 0xFF)
        assert bus.read(state.sp + 1) == (ret_addr >> 8)
        
        # 2. Execute RET
        cpu.step()
        assert state.pc == ret_addr
        assert state.sp == initial_sp

    # --- Phase 3: Arithmetic & Logic ---
    def test_and_or_xor(self, setup_cpu):
        cpu, bus = setup_cpu
        state = cpu.get_state()
        pc = 0x1000
        state.pc = pc
        
        # AND B (0xA0), OR C (0xB1), XOR D (0xAA)
        bus.write(pc, 0xA0)
        bus.write(pc + 1, 0xB1)
        bus.write(pc + 2, 0xAA)
        
        state.a = 0b11001100
        state.b = 0b10101010
        
        # AND B
        cpu.step()
        assert state.a == 0b10001000 # 0x88
        assert state.flag_h is True  # AND sets H
        assert state.flag_s is True  # Result is negative (bit 7 set)
        
        # OR C
        state.c = 0b00000001
        cpu.step()
        assert state.a == 0b10001001 # 0x89
        assert state.flag_h is False # OR resets H
        
        # XOR D
        state.d = 0b10001001
        cpu.step()
        assert state.a == 0x00
        assert state.flag_z is True  # Result is zero
        assert state.flag_pv is True  # Parity even (0 has even parity)

    def test_sub_adc_sbc(self, setup_cpu):
        cpu, bus = setup_cpu
        state = cpu.get_state()
        pc = 0x1000
        state.pc = pc
        
        # SUB B (0x90), ADC A,C (0x89), SBC A,D (0x9A)
        bus.write(pc, 0x90)
        bus.write(pc + 1, 0x89)
        bus.write(pc + 2, 0x9A)
        
        # SUB B
        state.a = 10
        state.b = 3
        cpu.step()
        assert state.a == 7
        assert state.flag_n is True
        
        # ADC A, C (with carry set)
        state.flag_c = True
        state.c = 2
        cpu.step()
        # 7 + 2 + 1(carry) = 10
        assert state.a == 10
        
        # SBC A, D (with carry set -> borrow)
        state.flag_c = True
        state.d = 4
        cpu.step()
        # 10 - 4 - 1(borrow) = 5
        assert state.a == 5

    def test_add_hl_ss(self, setup_cpu):
        cpu, bus = setup_cpu
        state = cpu.get_state()
        pc = 0x1000
        state.pc = pc
        
        # ADD HL, BC (0x09)
        bus.write(pc, 0x09)
        
        state.hl = 0x1000
        state.bc = 0x2000
        
        cpu.step()
        assert state.hl == 0x3000
        assert state.flag_n is False
        assert state.flag_c is False
        
        # Test Overflow (Carry)
        state.pc = pc # Rewind PC to execute same instruction
        state.hl = 0xFFFF
        state.bc = 0x0001
        
        cpu.step()
        assert state.hl == 0x0000
        assert state.flag_c is True
