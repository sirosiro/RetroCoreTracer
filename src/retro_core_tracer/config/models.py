from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MemoryRegion:
    start: int
    end: int
    type: str  # "RAM", "ROM", "MMIO"
    label: str = ""
    permissions: str = "RW"  # "RW", "RO"
    initial_value: int = 0x00

@dataclass
class IoRegion:
    start: int
    end: int
    label: str = ""
    type: str = "IO" # "IO", "UART", etc.

@dataclass
class CpuInitialState:
    pc: int = 0x0000
    sp: int = 0x0000
    use_reset_vector: bool = False # 追加: リセットベクトルを使用するかどうか
    registers: dict = field(default_factory=dict)

@dataclass
class SystemConfig:
    architecture: str
    memory_map: List[MemoryRegion] = field(default_factory=list)
    io_map: List[IoRegion] = field(default_factory=list)
    initial_state: CpuInitialState = field(default_factory=CpuInitialState)
