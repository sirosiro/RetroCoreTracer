import sys
import os

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from retro_core_tracer.transport.bus import Bus, RAM

def test_mc6800_execution():
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Mc6800Cpu(bus)
    
    # Initialize SP
    state = cpu.get_state()
    state.sp = 0x01FF 

    # Program: 
    # 0000: 86 10 (LDAA #$10)
    # 0002: 8B 20 (ADDA #$20)
    # 0004: B7 10 00 (STAA $1000)
    # 0007: BD 00 20 (JSR $0020) -> Call subroutine
    # 000A: 81 30 (CMPA #$30)
    # 000C: 27 02 (BEQ +2) -> Jump to 0010
    # 000E: 01 (NOP) -> Skipped
    # 000F: 01 (NOP) -> Skipped
    # 0010: 7E 00 10 (JMP $0010) -> Infinite loop (Wait, JMP not impl yet? Let's use BRA)
    # 0010: 20 FE (BRA *) -> Infinite loop
    
    # Subroutine at $0020
    # 0020: 36 (PSHA)
    # 0021: 86 FF (LDAA #$FF)
    # 0023: 32 (PULA) -> A should be back to 0x30
    # 0024: 39 (RTS)

    # 0000: 86 10
    bus.write(0x0000, 0x86); bus.write(0x0001, 0x10)
    # 0002: 8B 20
    bus.write(0x0002, 0x8B); bus.write(0x0003, 0x20)
    # 0004: B7 10 00
    bus.write(0x0004, 0xB7); bus.write(0x0005, 0x10); bus.write(0x0006, 0x00)
    # 0007: BD 00 20
    bus.write(0x0007, 0xBD); bus.write(0x0008, 0x00); bus.write(0x0009, 0x20)
    # 000A: 81 30
    bus.write(0x000A, 0x81); bus.write(0x000B, 0x30)
    # 000C: 27 02
    bus.write(0x000C, 0x27); bus.write(0x000D, 0x02)
    # 000E: 01
    bus.write(0x000E, 0x01)
    # 000F: 01
    bus.write(0x000F, 0x01)
    # 0010: 20 FE
    bus.write(0x0010, 0x20); bus.write(0x0011, 0xFE)

    # Subroutine
    # 0020: 36
    bus.write(0x0020, 0x36)
    # 0021: 86 FF
    bus.write(0x0021, 0x86); bus.write(0x0022, 0xFF)
    # 0023: 32
    bus.write(0x0023, 0x32)
    # 0024: 39
    bus.write(0x0024, 0x39)

    print("--- Step 1: LDAA #$10 ---")
    snap = cpu.step()
    assert snap.state.a == 0x10
    
    print("--- Step 2: ADDA #$20 ---")
    snap = cpu.step()
    assert snap.state.a == 0x30
    
    print("--- Step 3: STAA $1000 ---")
    snap = cpu.step()
    assert bus.read(0x1000) == 0x30
    
    print("--- Step 4: JSR $0020 ---")
    snap = cpu.step()
    print(f"PC: {snap.state.pc:04X} (Expected 0020)")
    assert snap.state.pc == 0x0020
    # Stack check (Return addr should be 000A)
    # SP was 01FF. Pushed Low (0A), then High (00).
    # SP is now 01FD.
    # 01FF: 0A
    # 01FE: 00
    assert bus.read(0x01FF) == 0x0A
    assert bus.read(0x01FE) == 0x00
    assert snap.state.sp == 0x01FD

    print("--- Subroutine Step 1: PSHA ---")
    snap = cpu.step()
    # Pushed A (0x30). SP -> 01FC.
    assert bus.read(0x01FD) == 0x30
    assert snap.state.sp == 0x01FC

    print("--- Subroutine Step 2: LDAA #$FF ---")
    snap = cpu.step()
    assert snap.state.a == 0xFF

    print("--- Subroutine Step 3: PULA ---")
    snap = cpu.step()
    # Pulled A. SP -> 01FD.
    assert snap.state.a == 0x30
    assert snap.state.sp == 0x01FD

    print("--- Subroutine Step 4: RTS ---")
    snap = cpu.step()
    print(f"PC: {snap.state.pc:04X} (Expected 000A)")
    assert snap.state.pc == 0x000A
    assert snap.state.sp == 0x01FF

    print("--- Step 5: CMPA #$30 ---")
    snap = cpu.step()
    # 0x30 - 0x30 = 0. Z flag set.
    assert snap.state.flag_z == True

    print("--- Step 6: BEQ +2 ---")
    snap = cpu.step()
    print(f"PC: {snap.state.pc:04X} (Expected 0010)")
    assert snap.state.pc == 0x0010

    print("--- Step 7: BRA * (Loop) ---")
    snap = cpu.step()
    assert snap.state.pc == 0x0010

if __name__ == "__main__":
    try:
        test_mc6800_execution()
        print("\nExtended Integration Test PASSED")
    except Exception as e:
        print(f"\nIntegration Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
