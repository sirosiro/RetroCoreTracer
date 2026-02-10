# src/retro_core_tracer/arch/mc6800/instructions/alu.py
"""
算術論理演算命令の実装。
"""
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.state import Mc6800CpuState

# @intent:utility_function 8ビット論理演算の結果に基づいてフラグ(N, Z, V)を更新します。
def update_flags_logic8(state: Mc6800CpuState, result: int) -> None:
    state.flag_n = (result & 0x80) != 0
    state.flag_z = (result == 0)
    state.flag_v = False

# @intent:utility_function 8ビット加算の結果に基づいてフラグ(N, Z, V, C, H)を更新します。
def update_flags_add8(state: Mc6800CpuState, v1: int, v2: int, res: int) -> None:
    state.flag_n = (res & 0x80) != 0
    state.flag_z = (res & 0xFF) == 0
    state.flag_v = ((v1 ^ res) & (v2 ^ res) & 0x80) != 0
    state.flag_c = (res > 0xFF)
    state.flag_h = ((v1 ^ v2 ^ res) & 0x10) != 0

# @intent:utility_function 8ビット減算の結果に基づいてフラグ(N, Z, V, C)を更新します。
def update_flags_sub8(state: Mc6800CpuState, v1: int, v2: int, res: int) -> None:
    state.flag_n = (res & 0x80) != 0
    state.flag_z = (res & 0xFF) == 0
    state.flag_v = ((v1 ^ v2) & (v1 ^ res) & 0x80) != 0
    state.flag_c = (v1 < v2) # Borrow

# --- ADDA ---
# @intent:responsibility ADDA (Immediate) 命令をデコードします。
def decode_adda_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    val = bus.read((pc + 1) & 0xFFFF)
    return Operation("8B", "ADDA", [f"#${val:02X}"], [val], 2, 2)

# @intent:responsibility ADDA (Immediate) 命令を実行し、結果をAレジスタに格納し、フラグを更新します。
def execute_adda_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    imm_val = op.operand_bytes[0]
    v1 = state.a
    res = v1 + imm_val
    state.a = res & 0xFF
    update_flags_add8(state, v1, imm_val, res)

# --- SUBA ---
# @intent:responsibility SUBA (Immediate) 命令をデコードします。
def decode_suba_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    val = bus.read((pc + 1) & 0xFFFF)
    return Operation("80", "SUBA", [f"#${val:02X}"], [val], 2, 2)

# @intent:responsibility SUBA (Immediate) 命令を実行し、結果をAレジスタに格納し、フラグを更新します。
def execute_suba_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    imm_val = op.operand_bytes[0]
    v1 = state.a
    res = v1 - imm_val
    state.a = res & 0xFF
    update_flags_sub8(state, v1, imm_val, res)

# --- CMPA ---
# @intent:responsibility CMPA (Immediate) 命令をデコードします。
def decode_cmpa_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    val = bus.read((pc + 1) & 0xFFFF)
    return Operation("81", "CMPA", [f"#${val:02X}"], [val], 2, 2)

# @intent:responsibility CMPA (Immediate) 命令を実行し、減算結果（保存しない）に基づいてフラグを更新します。
def execute_cmpa_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    imm_val = op.operand_bytes[0]
    v1 = state.a
    res = v1 - imm_val
    # Result is NOT stored
    update_flags_sub8(state, v1, imm_val, res)

# --- ANDA ---
# @intent:responsibility ANDA (Immediate) 命令をデコードします。
def decode_anda_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    val = bus.read((pc + 1) & 0xFFFF)
    return Operation("84", "ANDA", [f"#${val:02X}"], [val], 2, 2)

# @intent:responsibility ANDA (Immediate) 命令を実行し、結果をAレジスタに格納し、フラグを更新します。
def execute_anda_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    imm_val = op.operand_bytes[0]
    res = state.a & imm_val
    state.a = res
    update_flags_logic8(state, res)

# --- INCB ---
# @intent:responsibility INCB命令をデコードします。
def decode_incb(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("5C", "INCB", [], [], 2, 1)

# @intent:responsibility INCB命令を実行し、Bレジスタをインクリメントし、フラグを更新します。
def execute_incb(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    v1 = state.b
    res = (v1 + 1) & 0xFF
    state.b = res
    state.flag_n = (res & 0x80) != 0
    state.flag_z = (res == 0)
    state.flag_v = (v1 == 0x7F)
