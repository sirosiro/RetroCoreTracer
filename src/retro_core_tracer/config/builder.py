from typing import Tuple
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from .models import SystemConfig

class SystemBuilder:
    def build_system(self, config: SystemConfig) -> Tuple[AbstractCpu, Bus]:
        bus = Bus()
        
        for region in config.memory_map:
            size = region.end - region.start + 1
            if region.type == "RAM" or region.type == "ROM":
                # Currently ROM is treated as RAM (writable for loading)
                # Future: Implement actual ReadOnlyMemory device
                device = RAM(size)
                bus.register_device(region.start, region.end, device)
            else:
                # Placeholder for other device types
                print(f"Warning: Unknown device type '{region.type}' for range {region.start:04X}-{region.end:04X}")
        
        if config.architecture == "Z80":
            cpu = Z80Cpu(bus)
        elif config.architecture == "MC6800":
            cpu = Mc6800Cpu(bus)
        else:
            raise ValueError(f"Unsupported architecture: {config.architecture}")
            
        # Apply initial state
        state = cpu.get_state()
        state.pc = config.initial_state.pc
        state.sp = config.initial_state.sp
        
        # Apply other registers if specified
        for reg_name, value in config.initial_state.registers.items():
            if hasattr(state, reg_name):
                setattr(state, reg_name, value)
            else:
                print(f"Warning: Unknown register '{reg_name}' in initial_state")

        return cpu, bus