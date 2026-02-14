# src/retro_core_tracer/arch/mos6502/state.py
"""
MOS 6502 CPUの状態定義。
"""
from dataclasses import dataclass, field
from retro_core_tracer.core.state import CpuState

# @intent:responsibility MOS 6502 CPUの状態（レジスタ、フラグ）を保持する。
@dataclass
class Mos6502CpuState(CpuState):
    """
    MOS 6502 CPUのレジスタ状態。
    """
    a: int = 0
    x: int = 0
    y: int = 0
    p: int = 0x24  # Initial status flags (Reserved bit is 1, Interrupt Disable is 1)

    # Flag bit masks
    C_FLAG = 0x01  # Carry
    Z_FLAG = 0x02  # Zero
    I_FLAG = 0x04  # Interrupt Disable
    D_FLAG = 0x08  # Decimal Mode
    B_FLAG = 0x10  # Break Command
    R_FLAG = 0x20  # Reserved (Always 1)
    V_FLAG = 0x40  # Overflow
    N_FLAG = 0x80  # Negative

    # @intent:responsibility フラグの状態を取得するヘルパープロパティ。
    @property
    def flag_c(self) -> bool: return bool(self.p & self.C_FLAG)
    @property
    def flag_z(self) -> bool: return bool(self.p & self.Z_FLAG)
    @property
    def flag_i(self) -> bool: return bool(self.p & self.I_FLAG)
    @property
    def flag_d(self) -> bool: return bool(self.p & self.D_FLAG)
    @property
    def flag_b(self) -> bool: return bool(self.p & self.B_FLAG)
    @property
    def flag_v(self) -> bool: return bool(self.p & self.V_FLAG)
    @property
    def flag_n(self) -> bool: return bool(self.p & self.N_FLAG)

    # @intent:responsibility 状態を変更した新しいインスタンスを返す（不変性の維持）。
    def update_flags(self, **kwargs) -> 'Mos6502CpuState':
        new_p = self.p
        for flag_name, value in kwargs.items():
            mask = getattr(self, f"{flag_name.upper()}_FLAG", 0)
            if mask:
                if value:
                    new_p |= mask
                else:
                    new_p &= ~mask
        return self.replace(p=new_p)
    
    # @intent:responsibility dataclasses.replaceのラッパー。
    def replace(self, **changes) -> 'Mos6502CpuState':
        from dataclasses import replace
        return replace(self, **changes)
