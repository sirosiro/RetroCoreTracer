# src/retro_core_tracer/arch/mc6800/state.py
"""
MC6800 CPU固有の状態定義。
"""
from dataclasses import dataclass
from retro_core_tracer.core.state import CpuState

# MC6800 コンディションコード (CC) ビットマスク
# @intent:constant MC6800のコンディションコードレジスタ内の各フラグビットの位置を定義します。
H_FLAG = 0b00100000  # Half Carry
I_FLAG = 0b00010000  # Interrupt Mask
N_FLAG = 0b00001000  # Negative
Z_FLAG = 0b00000100  # Zero
V_FLAG = 0b00000010  # Overflow
C_FLAG = 0b00000001  # Carry

# @intent:responsibility MC6800 CPUの全てのレジスタ（A, B, X, PC, SP, CC）とフラグの状態を保持します。
@dataclass
class Mc6800CpuState(CpuState):
    """
    MC6800 CPUのレジスタ状態を保持するデータクラス。
    """
    a: int = 0x00      # Accumulator A
    b: int = 0x00      # Accumulator B
    x: int = 0x0000    # Index Register X
    cc: int = 0b11000000 # Condition Code Register (Bits 7,6 are always 1)

    # @intent:accessor コンディションコード(CC)レジスタの各フラグビットにアクセスするためのプロパティを提供します。
    # @intent:rationale フラグ操作の可読性を高め、CCレジスタへのビット操作を隠蔽するためにプロパティを使用します。

    @property
    def flag_h(self) -> bool:
        return (self.cc & H_FLAG) != 0

    @flag_h.setter
    def flag_h(self, value: bool) -> None:
        if value: self.cc |= H_FLAG
        else: self.cc &= ~H_FLAG

    @property
    def flag_i(self) -> bool:
        return (self.cc & I_FLAG) != 0

    @flag_i.setter
    def flag_i(self, value: bool) -> None:
        if value: self.cc |= I_FLAG
        else: self.cc &= ~I_FLAG

    @property
    def flag_n(self) -> bool:
        return (self.cc & N_FLAG) != 0

    @flag_n.setter
    def flag_n(self, value: bool) -> None:
        if value: self.cc |= N_FLAG
        else: self.cc &= ~N_FLAG

    @property
    def flag_z(self) -> bool:
        return (self.cc & Z_FLAG) != 0

    @flag_z.setter
    def flag_z(self, value: bool) -> None:
        if value: self.cc |= Z_FLAG
        else: self.cc &= ~Z_FLAG

    @property
    def flag_v(self) -> bool:
        return (self.cc & V_FLAG) != 0

    @flag_v.setter
    def flag_v(self, value: bool) -> None:
        if value: self.cc |= V_FLAG
        else: self.cc &= ~V_FLAG

    @property
    def flag_c(self) -> bool:
        return (self.cc & C_FLAG) != 0

    @flag_c.setter
    def flag_c(self, value: bool) -> None:
        if value: self.cc |= C_FLAG
        else: self.cc &= ~C_FLAG