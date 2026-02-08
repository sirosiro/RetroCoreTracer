
import pytest
import os
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.loader.loader import AssemblyLoader

def test_symbol_integration():
    bus = Bus()
    ram = RAM(1024)
    bus.register_device(0, 1023, ram)
    cpu = Z80Cpu(bus)
    
    # Create a temporary assembly file
    asm_content = """
ORG $0000
START:
    NOP
    LD A, $AA
LOOP:
    HALT
    """
    with open("temp.asm", "w") as f:
        f.write(asm_content)
    
    try:
        loader = AssemblyLoader()
        symbols = loader.load_assembly("temp.asm", bus)
        cpu.set_symbol_map(symbols)
        
        assert symbols["START"] == 0x0000
        assert symbols["LOOP"] == 0x0003 # START(0)+NOP(1)+LD A,n(2) = 3
        
        # Step START
        snap = cpu.step()
        assert "START: NOP" in snap.metadata.symbol_info
        
        # Step LD A, $AA
        snap = cpu.step()
        # Z80InstructionSet returns "LD A,n" for 0x3E
        assert "LD A,n" in snap.metadata.symbol_info
        
        # Step LOOP
        snap = cpu.step()
        assert "LOOP: HALT" in snap.metadata.symbol_info
    finally:
        if os.path.exists("temp.asm"):
            os.remove("temp.asm")
