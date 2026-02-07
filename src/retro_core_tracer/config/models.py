from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class MemoryRegion:
    start: int
    end: int
    type: str  # "RAM", "ROM"
    label: str = ""
    permissions: str = "RW"  # "RW", "RO"
    initial_value: int = 0x00

@dataclass
class CpuInitialState:
    pc: int = 0x0000
    sp: int = 0x0000
    registers: dict = field(default_factory=dict)

@dataclass
class SystemConfig:
    architecture: str
    memory_map: List[MemoryRegion] = field(default_factory=list)
    initial_state: CpuInitialState = field(default_factory=CpuInitialState)
    # io_map will be added later
