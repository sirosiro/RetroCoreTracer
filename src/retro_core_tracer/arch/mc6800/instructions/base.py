# src/retro_core_tracer/arch/mc6800/instructions/base.py
"""
MC6800命令実装用の共通ユーティリティ。
"""
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.state import Mc6800CpuState

# @intent:utility_function バスから16ビットワードをビッグエンディアン形式で読み込みます。
def read_word(bus: Bus, addr: int) -> int:
    """Big-endian 16-bit read."""
    return (bus.read(addr) << 8) | bus.read((addr + 1) & 0xFFFF)

# @intent:utility_function バスへ16ビットワードをビッグエンディアン形式で書き込みます。
def write_word(bus: Bus, addr: int, val: int) -> None:
    """Big-endian 16-bit write."""
    bus.write(addr, (val >> 8) & 0xFF)
    bus.write((addr + 1) & 0xFFFF, val & 0xFF)

# @intent:utility_function アドレッシングモードに基づいてオペランドのアドレスを計算します。
# @intent:rationale 現在は使用されていませんが、将来的に命令実装のリファクタリングで共通化する場合のために残しています。
def get_operand_addr(state: Mc6800CpuState, bus: Bus, mode: str, pc: int) -> int:
    """アドレッシングモードに基づいてオペランドのアドレスを取得する。"""
    if mode == "immediate":
        return (pc + 1) & 0xFFFF
    elif mode == "direct":
        return bus.read((pc + 1) & 0xFFFF)
    elif mode == "extended":
        return read_word(bus, (pc + 1) & 0xFFFF)
    elif mode == "indexed":
        offset = bus.read((pc + 1) & 0xFFFF)
        return (state.x + offset) & 0xFFFF
    elif mode == "relative":
        offset = bus.read((pc + 1) & 0xFFFF)
        if offset & 0x80: offset -= 0x100
        return (pc + 2 + offset) & 0xFFFF
    return 0