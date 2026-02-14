# tests/arch/mos6502/test_cpu.py
import pytest
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.mos6502.cpu import Mos6502Cpu
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState

@pytest.fixture
def cpu():
    bus = Bus()
    bus.register_device(0x0000, 0xFFFF, RAM(0x10000))
    cpu = Mos6502Cpu(bus)
    return cpu

def test_lda_immediate(cpu):
    # LDA #$55 (0xA9 0x55)
    cpu._bus.write(0x0200, 0xA9)
    cpu._bus.write(0x0201, 0x55)
    cpu._state = cpu._state.replace(pc=0x0200)
    
    cpu.step()
    
    state = cpu.get_state()
    assert state.a == 0x55
    assert not state.flag_z
    assert not state.flag_n
    assert state.pc == 0x0202

def test_ldx_zeropage(cpu):
    # LDX $10 (0xA6 0x10)
    # Memory[$10] = $80
    cpu._bus.write(0x0200, 0xA6)
    cpu._bus.write(0x0201, 0x10)
    cpu._bus.write(0x0010, 0x80)
    cpu._state = cpu._state.replace(pc=0x0200)
    
    cpu.step()
    
    state = cpu.get_state()
    assert state.x == 0x80
    assert not state.flag_z
    assert state.flag_n # $80 has bit 7 set
    assert state.pc == 0x0202

def test_adc_binary(cpu):
    # CLC (0x18), LDA #$10 (0xA9 0x10), ADC #$20 (0x69 0x20)
    cpu._bus.write(0x0200, 0x18)
    cpu._bus.write(0x0201, 0xA9)
    cpu._bus.write(0x0202, 0x10)
    cpu._bus.write(0x0203, 0x69)
    cpu._bus.write(0x0204, 0x20)
    cpu._state = cpu._state.replace(pc=0x0200)
    
    cpu.step() # CLC
    cpu.step() # LDA
    cpu.step() # ADC
    
    state = cpu.get_state()
    assert state.a == 0x30
    assert not state.flag_c
    assert not state.flag_z

def test_adc_bcd(cpu):
    # SED (0xF8), CLC (0x18), LDA #$09 (0xA9 0x09), ADC #$01 (0x69 0x01)
    # 09 + 01 = 10 (BCD)
    cpu._bus.write(0x0200, 0xF8)
    cpu._bus.write(0x0201, 0x18)
    cpu._bus.write(0x0202, 0xA9)
    cpu._bus.write(0x0203, 0x09)
    cpu._bus.write(0x0204, 0x69)
    cpu._bus.write(0x0205, 0x01)
    cpu._state = cpu._state.replace(pc=0x0200)
    
    cpu.step() # SED
    cpu.step() # CLC
    cpu.step() # LDA
    cpu.step() # ADC
    
    state = cpu.get_state()
    assert state.flag_d
    assert state.a == 0x10 # BCD result
    assert not state.flag_c

def test_branch_taken(cpu):
    # SEC (0x38), BCS +2 (0xB0 0x02)
    cpu._bus.write(0x0200, 0x38)
    cpu._bus.write(0x0201, 0xB0)
    cpu._bus.write(0x0202, 0x02)
    # Next op at 0x0203 + 2 = 0x0205
    cpu._state = cpu._state.replace(pc=0x0200)
    
    cpu.step() # SEC
    cpu.step() # BCS
    
    state = cpu.get_state()
    assert state.pc == 0x0205

def test_branch_not_taken(cpu):
    # CLC (0x18), BCS +2 (0xB0 0x02)
    cpu._bus.write(0x0200, 0x18)
    cpu._bus.write(0x0201, 0xB0)
    cpu._bus.write(0x0202, 0x02)
    # Next op at 0x0203 (Fallthrough)
    cpu._state = cpu._state.replace(pc=0x0200)
    
    cpu.step() # CLC
    cpu.step() # BCS
    
    state = cpu.get_state()
    assert state.pc == 0x0203

def test_stack_pointer_view(cpu):
    # Internal SP is 8-bit (e.g. 0xFD)
    # External State SP should be 0x01FD
    
    internal_state = cpu._state
    assert internal_state.sp == 0xFD
    
    external_state = cpu.get_state()
    assert external_state.sp == 0x01FD
