
import pytest
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus, RAM

def setup_cpu():
    bus = Bus()
    ram = RAM(65536)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)
    return cpu, bus

def test_ex_instructions():
    cpu, bus = setup_cpu()
    state = cpu._state
    
    # EX DE,HL
    state.de = 0x1234
    state.hl = 0xABCD
    bus._memory_map[0][2].write(0, 0xEB) # EX DE,HL
    cpu.step()
    assert state.de == 0xABCD
    assert state.hl == 0x1234
    
    # EX AF,AF'
    state.af = 0x1122
    state.af_ = 0x3344
    bus._memory_map[0][2].write(1, 0x08) # EX AF,AF'
    cpu.step()
    assert state.af == 0x3344
    assert state.af_ == 0x1122
    
    # EXX
    state.bc, state.de, state.hl = 0x1111, 0x2222, 0x3333
    state.bc_, state.de_, state.hl_ = 0xAAAA, 0xBBBB, 0xCCCC
    bus._memory_map[0][2].write(2, 0xD9) # EXX
    cpu.step()
    assert state.bc == 0xAAAA and state.de == 0xBBBB and state.hl == 0xCCCC
    assert state.bc_ == 0x1111 and state.de_ == 0x2222 and state.hl_ == 0x3333

def test_ix_iy_instructions():
    cpu, bus = setup_cpu()
    state = cpu._state
    
    # LD IX, nn
    bus._memory_map[0][2].write(0, 0xDD)
    bus._memory_map[0][2].write(1, 0x21)
    bus._memory_map[0][2].write(2, 0x34)
    bus._memory_map[0][2].write(3, 0x12) # LD IX, $1234
    cpu.step()
    assert state.ix == 0x1234
    
    # LD A, (IX+d)
    state.ix = 0x2000
    bus._memory_map[0][2].write(0x2005, 0x55)
    bus._memory_map[0][2].write(4, 0xDD)
    bus._memory_map[0][2].write(5, 0x7E)
    bus._memory_map[0][2].write(6, 0x05) # LD A, (IX+5)
    cpu.step()
    assert state.a == 0x55

def test_interrupt_instructions():
    cpu, bus = setup_cpu()
    state = cpu._state
    
    # DI
    state.iff1 = True
    bus._memory_map[0][2].write(0, 0xF3) # DI
    cpu.step()
    assert state.iff1 == False
    
    # EI
    bus._memory_map[0][2].write(1, 0xFB) # EI
    cpu.step()
    assert state.iff1 == True
    
    # IM 2
    bus._memory_map[0][2].write(2, 0xED)
    bus._memory_map[0][2].write(3, 0x5E) # IM 2
    cpu.step()
    assert state.im == 2
