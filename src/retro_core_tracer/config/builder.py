from typing import Tuple
from retro_core_tracer.transport.bus import Bus, RAM, ROM
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from .models import SystemConfig

# @intent:responsibility システム構成（Config）に基づいて、Bus、Device、CPUを生成・接続し、初期状態を適用します。
class SystemBuilder:
    def build_system(self, config: SystemConfig) -> Tuple[AbstractCpu, Bus]:
        bus = Bus()
        
        for region in config.memory_map:
            size = region.end - region.start + 1
            device = None
            
            if region.type == "RAM":
                device = RAM(size)
            elif region.type == "ROM":
                # @intent:feature ROMデバイスを使用します。
                device = ROM(size)
            else:
                # Fallback / Placeholder for other device types
                print(f"Warning: Unknown device type '{region.type}' for range {region.start:04X}-{region.end:04X}, defaulting to RAM")
                device = RAM(size)
            
            if device:
                bus.register_device(region.start, region.end, device)
        
        # @intent:feature I/Oマップに基づいてI/Oデバイスをバスに登録します。
        for region in config.io_map:
            size = region.end - region.start + 1
            # I/Oデバイスの具体的な型は現状RAMで代用します（将来的に専用クラスが必要になる可能性があります）。
            device = RAM(size)
            bus.register_io_device(region.start, region.end, device)

        if config.architecture == "Z80":
            cpu = Z80Cpu(bus)
        elif config.architecture == "MC6800":
            cpu = Mc6800Cpu(bus)
            # @intent:rationale MC6800の場合はリセットベクトルの使用可否を設定します。
            if config.initial_state.use_reset_vector:
                cpu.set_use_reset_vector(True)
        else:
            raise ValueError(f"Unsupported architecture: {config.architecture}")
            
        # Apply initial state
        # @intent:rationale リセットベクトルを使用する場合は、ここでのPC上書きをスキップし、
        #                  後の reset() 呼び出しでベクトルから読み込ませます。
        cpu.reset()
        state = cpu.get_state()
        
        if not config.initial_state.use_reset_vector:
            state.pc = config.initial_state.pc
            
        state.sp = config.initial_state.sp
        
        # Apply other registers if specified
        for reg_name, value in config.initial_state.registers.items():
            if hasattr(state, reg_name):
                setattr(state, reg_name, value)
            else:
                print(f"Warning: Unknown register '{reg_name}' in initial_state")

        return cpu, bus
