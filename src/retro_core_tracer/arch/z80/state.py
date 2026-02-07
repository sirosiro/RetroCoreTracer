# retro_core_tracer/arch/z80/state.py
"""
Z80 CPU固有の状態定義。

このモジュールは、Z80 CPUのレジスタ、フラグ、およびその他の状態を保持するデータ構造を定義します。
"""
from dataclasses import dataclass, field

from retro_core_tracer.core.state import CpuState

# Z80フラグビットマスク
# @intent:constant Z80フラグレジスタ内の各フラグビットの位置を定義します。
S_FLAG = 0b10000000  # Sign (符号)
Z_FLAG = 0b01000000  # Zero (ゼロ)
# 0b00100000 # Unused (HフラグとNフラグの間に未使用ビット)
H_FLAG = 0b00010000  # Half Carry (ハーフキャリー)
# 0b00001000 # Unused (P/VフラグとNフラグの間に未使用ビット)
PV_FLAG = 0b00000100 # Parity/Overflow (パリティ/オーバーフロー)
N_FLAG = 0b00000010  # Add/Subtract (加減算)
C_FLAG = 0b00000001  # Carry (キャリー)


# @intent:responsibility Z80 CPUの全てのレジスタとフラグの状態を保持します。
@dataclass
class Z80CpuState(CpuState):
    """
    Z80 CPUのレジスタ状態を保持するデータクラス。
    CpuStateを拡張し、Z80固有のレジスタを含みます。
    """
    # Main registers
    a: int = 0x00
    b: int = 0x00
    c: int = 0x00
    d: int = 0x00
    e: int = 0x00
    h: int = 0x00
    l: int = 0x00
    f: int = 0x00  # Flag register

    # Alternate registers
    a_: int = 0x00
    b_: int = 0x00
    c_: int = 0x00
    d_: int = 0x00
    e_: int = 0x00
    h_: int = 0x00
    l_: int = 0x00
    f_: int = 0x00

    # Index registers
    ix: int = 0x0000
    iy: int = 0x0000

    # Special purpose registers
    i: int = 0x00  # Interrupt Vector
    r: int = 0x00  # Refresh Register

    halted: bool = False # CPU stop state flag

    # @intent:accessor Z80のFレジスタの各フラグビットにアクセスするためのプロパティを提供します。
    # @intent:rationale フラグを直接ビット操作する代わりに、分かりやすいプロパティとして提供することで、コードの可読性と保守性を高めます。
    #                   ゲッターとセッターを通じてFレジスタの対応するビットを操作します。

    @property
    def flag_s(self) -> bool:
        return (self.f & S_FLAG) != 0

    @flag_s.setter
    def flag_s(self, value: bool) -> None:
        if value:
            self.f |= S_FLAG
        else:
            self.f &= ~S_FLAG

    @property
    def flag_z(self) -> bool:
        return (self.f & Z_FLAG) != 0

    @flag_z.setter
    def flag_z(self, value: bool) -> None:
        if value:
            self.f |= Z_FLAG
        else:
            self.f &= ~Z_FLAG

    @property
    def flag_h(self) -> bool:
        return (self.f & H_FLAG) != 0

    @flag_h.setter
    def flag_h(self, value: bool) -> None:
        if value:
            self.f |= H_FLAG
        else:
            self.f &= ~H_FLAG

    @property
    def flag_pv(self) -> bool:
        return (self.f & PV_FLAG) != 0

    @flag_pv.setter
    def flag_pv(self, value: bool) -> None:
        if value:
            self.f |= PV_FLAG
        else:
            self.f &= ~PV_FLAG

    @property
    def flag_n(self) -> bool:
        return (self.f & N_FLAG) != 0

    @flag_n.setter
    def flag_n(self, value: bool) -> None:
        if value:
            self.f |= N_FLAG
        else:
            self.f &= ~N_FLAG

    @property
    def flag_c(self) -> bool:
        return (self.f & C_FLAG) != 0

    @flag_c.setter
    def flag_c(self, value: bool) -> None:
        if value:
            self.f |= C_FLAG
        else:
            self.f &= ~C_FLAG

    # 16-bit register pairs
    @property
    def af(self) -> int:
        return (self.a << 8) | self.f

    @af.setter
    def af(self, value: int) -> None:
        self.a = (value >> 8) & 0xFF
        self.f = value & 0xFF

    @property
    def bc(self) -> int:
        return (self.b << 8) | self.c

    @bc.setter
    def bc(self, value: int) -> None:
        self.b = (value >> 8) & 0xFF
        self.c = value & 0xFF

    @property
    def de(self) -> int:
        return (self.d << 8) | self.e

    @de.setter
    def de(self, value: int) -> None:
        self.d = (value >> 8) & 0xFF
        self.e = value & 0xFF

    @property
    def hl(self) -> int:
        return (self.h << 8) | self.l

    @hl.setter
    def hl(self, value: int) -> None:
        self.h = (value >> 8) & 0xFF
        self.l = value & 0xFF

    @property
    def af_(self) -> int:
        return (self.a_ << 8) | self.f_

    @af_.setter
    def af_(self, value: int) -> None:
        self.a_ = (value >> 8) & 0xFF
        self.f_ = value & 0xFF

    @property
    def bc_(self) -> int:
        return (self.b_ << 8) | self.c_

    @bc_.setter
    def bc_(self, value: int) -> None:
        self.b_ = (value >> 8) & 0xFF
        self.c_ = value & 0xFF

    @property
    def de_(self) -> int:
        return (self.d_ << 8) | self.e_

    @de_.setter
    def de_(self, value: int) -> None:
        self.d_ = (value >> 8) & 0xFF
        self.e_ = value & 0xFF

    @property
    def hl_(self) -> int:
        return (self.h_ << 8) | self.l_

    @hl_.setter
    def hl_(self, value: int) -> None:
        self.h_ = (value >> 8) & 0xFF
        self.l_ = value & 0xFF