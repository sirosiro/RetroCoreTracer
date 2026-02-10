import sys
import os

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from retro_core_tracer.transport.bus import Bus

def test_mc6800_metadata():
    bus = Bus()
    cpu = Mc6800Cpu(bus)
    
    # Test Register Layout
    layout = cpu.get_register_layout()
    print("--- Register Layout ---")
    for group in layout:
        print(f"Group: {group.group_name}")
        for reg in group.registers:
            print(f"  - {reg.name} ({reg.width} bits)")
            
    assert len(layout) == 2
    assert layout[0].group_name == "Accumulators/Flags"
    assert layout[1].group_name == "Index/Pointers"
    
    # Test Register Map
    reg_map = cpu.get_register_map()
    print("\n--- Register Map ---")
    for name, value in reg_map.items():
        print(f"{name}: {value}")
    
    assert "A" in reg_map
    assert "B" in reg_map
    assert "X" in reg_map
    assert "CC" in reg_map
    
    # Test Flag State
    flags = cpu.get_flag_state()
    print("\n--- Flag State ---")
    for name, value in flags.items():
        print(f"{name}: {value}")
    
    assert "H" in flags
    assert "I" in flags
    assert "N" in flags
    assert "Z" in flags
    assert "V" in flags
    assert "C" in flags

if __name__ == "__main__":
    try:
        test_mc6800_metadata()
        print("\nLogic Verification PASSED")
    except Exception as e:
        print(f"\nLogic Verification FAILED: {e}")
        sys.exit(1)