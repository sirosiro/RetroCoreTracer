from typing import Tuple
from retro_core_tracer.transport.bus import Bus, RAM, ROM
from retro_core_tracer.core.cpu import AbstractCpu
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from .models import SystemConfig, CpuInitialState

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
                device = ROM(size)
            else:
                print(f"Warning: Unknown device type '{region.type}' for range {region.start:04X}-{region.end:04X}, defaulting to RAM")
                device = RAM(size)
            
            if device:
                bus.register_device(region.start, region.end, device)
        
        for region in config.io_map:
            size = region.end - region.start + 1
            device = RAM(size)
            bus.register_io_device(region.start, region.end, device)

        if config.architecture == "Z80":
            cpu = Z80Cpu(bus)
        elif config.architecture == "MC6800":
            from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
            cpu = Mc6800Cpu(bus)
            if config.initial_state.use_reset_vector:
                cpu.set_use_reset_vector(True)
        elif config.architecture == "MOS6502":
            from retro_core_tracer.arch.mos6502.cpu import Mos6502Cpu
            cpu = Mos6502Cpu(bus)
        else:
            raise ValueError(f"Unsupported architecture: {config.architecture}")
            
        # 初期状態の適用
        self.apply_initial_state(cpu, config.initial_state)

        return cpu, bus

    # @intent:responsibility Configで定義された初期状態をCPUに適用します。
    # @intent:rationale 不変(Immutable)と可変(Mutable)の両方のState型に対応し、PC、SP、その他のレジスタを確実に設定します。
    def apply_initial_state(self, cpu: AbstractCpu, config_state: CpuInitialState):
        """
        CPUをリセットし、Configから指定された初期値を適用します。
        """
        cpu.reset()
        
        # 現在の状態を取得（補正コピーの場合があるため、設定には _state を直接操作するか、共通の手段を用いる）
        state = cpu.get_state()
        
        if config_state.use_reset_vector:
            # リセットベクトルを使用する場合はPCの上書きをスキップ（CPUのリセット処理で既に行われているはず）
            return

        # PC/SP設定
        if hasattr(state, 'replace'):
            # Immutable Pattern (MOS6502など)
            # get_state()が補正済みを返す可能性があるため、cpu._state を直接ベースにする
            new_state = cpu._state.replace(
                pc=config_state.pc,
                sp=config_state.sp & 0xFF
            )
            # その他のレジスタ
            for reg_name, value in config_state.registers.items():
                if hasattr(new_state, reg_name):
                    new_state = new_state.replace(**{reg_name: value})
            cpu._state = new_state
        else:
            # Mutable Pattern (Z80, MC6800など)
            cpu._state.pc = config_state.pc
            cpu._state.sp = config_state.sp
            for reg_name, value in config_state.registers.items():
                if hasattr(cpu._state, reg_name):
                    setattr(cpu._state, reg_name, value)