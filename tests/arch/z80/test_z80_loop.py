from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.loader.loader import IntelHexLoader
from retro_core_tracer.debugger.debugger import Debugger

def test_loop():
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)
    debugger = Debugger(cpu)
    
    loader = IntelHexLoader()
    loader.load_intel_hex("examples/z80_loop_test.hex", bus)
    
    print("Starting loop test...")
    for _ in range(20): # Should halt within 20 steps
        snapshot = debugger.step_instruction()
        state = snapshot.state
        print(f"PC: {state.pc:04X}, A: {state.a:02X}, B: {state.b:02X}, Op: {snapshot.operation.mnemonic}")
        if snapshot.operation.mnemonic == "HALT":
            print("Halted.")
            break
    
    if state.a == 5:
        print("Test Passed: A is 5.")
    else:
        print(f"Test Failed: A is {state.a} (expected 5).")

if __name__ == "__main__":
    test_loop()
