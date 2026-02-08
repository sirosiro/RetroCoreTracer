"""
Z80命令セット実装のための共通ヘルパー関数と定数。
"""
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus

# Helper functions for register mapping
REGISTER_CODES = {
    0b000: "B", 0b001: "C", 0b010: "D", 0b011: "E",
    0b100: "H", 0b101: "L", 0b110: "(HL)", 0b111: "A"
}

# @intent:utility_function 指定されたコードに対応するレジスタ名を返します。
def get_register_name(code: int) -> str:
    return REGISTER_CODES.get(code, "UNKNOWN_REG")

# @intent:utility_function レジスタ名（または(HL)）に基づいて現在の値を取得します。
def get_register_value(state: Z80CpuState, bus: Bus, reg_name: str) -> int:
    if reg_name == "(HL)":
        return bus.read(state.hl)
    return getattr(state, reg_name.lower())

# @intent:utility_function レジスタ名（または(HL)）に値を設定します。
def set_register_value(state: Z80CpuState, bus: Bus, reg_name: str, value: int) -> None:
    if reg_name == "(HL)":
        bus.write(state.hl, value & 0xFF)
    else:
        setattr(state, reg_name.lower(), value & 0xFF)

# @intent:utility_function PUSH/POP命令で使用されるレジスタペア名を返します。
def get_push_pop_reg_name(code: int) -> str:
    return {0b00: "BC", 0b01: "DE", 0b10: "HL", 0b11: "AF"}.get(code, "UNKNOWN")

# @intent:utility_function 16ビット演算で使用されるレジスタペア名(ss)を返します。
def get_ss_reg_name(code: int) -> str:
    return {0b00: "BC", 0b01: "DE", 0b10: "HL", 0b11: "SP"}.get(code, "UNKNOWN")
