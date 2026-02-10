# src/retro_core_tracer/arch/mc6800/instructions/load.py
"""
転送・スタック操作命令の実装。
"""
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.state import Mc6800CpuState
from .base import read_word, write_word, get_operand_addr

# --- LDAA ---
# @intent:responsibility LDAA (Immediate) 命令をデコードします。
def decode_ldaa_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    val = bus.read((pc + 1) & 0xFFFF)
    return Operation("86", "LDAA", [f"#${val:02X}"], [val], 2, 2)

# @intent:responsibility LDAA (Immediate) 命令を実行し、フラグ(N, Z, V)を更新します。
def execute_ldaa_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    val = op.operand_bytes[0]
    state.a = val
    state.flag_n = (val & 0x80) != 0
    state.flag_z = (val == 0)
    state.flag_v = False

# @intent:responsibility LDAA (Direct) 命令をデコードします。
def decode_ldaa_dir(opcode: int, bus: Bus, pc: int) -> Operation:
    addr = bus.read((pc + 1) & 0xFFFF)
    return Operation("96", "LDAA", [f"${addr:02X}"], [addr], 3, 2)

# @intent:responsibility LDAA (Direct) 命令を実行します。
def execute_ldaa_dir(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    addr = op.operand_bytes[0]
    val = bus.read(addr)
    state.a = val
    state.flag_n = (val & 0x80) != 0
    state.flag_z = (val == 0)
    state.flag_v = False

# --- LDAB ---
# @intent:responsibility LDAB (Immediate) 命令をデコードします。
def decode_ldab_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    val = bus.read((pc + 1) & 0xFFFF)
    return Operation("C6", "LDAB", [f"#${val:02X}"], [val], 2, 2)

# @intent:responsibility LDAB (Immediate) 命令を実行します。
def execute_ldab_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    val = op.operand_bytes[0]
    state.b = val
    state.flag_n = (val & 0x80) != 0
    state.flag_z = (val == 0)
    state.flag_v = False

# --- LDX ---
# @intent:responsibility LDX (Immediate) 命令をデコードします。
def decode_ldx_imm(opcode: int, bus: Bus, pc: int) -> Operation:
    b1 = bus.read((pc + 1) & 0xFFFF)
    b2 = bus.read((pc + 2) & 0xFFFF)
    val = (b1 << 8) | b2
    return Operation("CE", "LDX", [f"#${val:04X}"], [b1, b2], 3, 3)

# @intent:responsibility LDX (Immediate) 命令を実行し、Xレジスタを更新します。
def execute_ldx_imm(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    val = (op.operand_bytes[0] << 8) | op.operand_bytes[1]
    state.x = val
    state.flag_n = (val & 0x8000) != 0
    state.flag_z = (val == 0)
    state.flag_v = False

# --- STAA ---
# @intent:responsibility STAA (Extended) 命令をデコードします。
def decode_staa_ext(opcode: int, bus: Bus, pc: int) -> Operation:
    b1 = bus.read((pc + 1) & 0xFFFF)
    b2 = bus.read((pc + 2) & 0xFFFF)
    addr = (b1 << 8) | b2
    return Operation("B7", "STAA", [f"${addr:04X}"], [b1, b2], 5, 3)

# @intent:responsibility STAA (Extended) 命令を実行し、Aの内容をメモリに書き込みます。
def execute_staa_ext(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    addr = (op.operand_bytes[0] << 8) | op.operand_bytes[1]
    bus.write(addr, state.a)
    state.flag_n = (state.a & 0x80) != 0
    state.flag_z = (state.a == 0)
    state.flag_v = False

# --- PSH/PUL ---
# @intent:responsibility PSHA命令をデコードします。
def decode_psha(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("36", "PSHA", [], [], 3, 1)

# @intent:responsibility PSHA命令を実行し、Aレジスタの内容をスタックにプッシュします。
def execute_psha(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    bus.write(state.sp, state.a)
    state.sp = (state.sp - 1) & 0xFFFF

# @intent:responsibility PULA命令をデコードします。
def decode_pula(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("32", "PULA", [], [], 4, 1)

# @intent:responsibility PULA命令を実行し、スタックからAレジスタへポップします。
def execute_pula(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    state.sp = (state.sp + 1) & 0xFFFF
    state.a = bus.read(state.sp)

# @intent:responsibility PSHB命令をデコードします。
def decode_pshb(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("37", "PSHB", [], [], 3, 1)

# @intent:responsibility PSHB命令を実行し、Bレジスタの内容をスタックにプッシュします。
def execute_pshb(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    bus.write(state.sp, state.b)
    state.sp = (state.sp - 1) & 0xFFFF

# @intent:responsibility PULB命令をデコードします。
def decode_pulb(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("33", "PULB", [], [], 4, 1)

# @intent:responsibility PULB命令を実行し、スタックからBレジスタへポップします。
def execute_pulb(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    state.sp = (state.sp + 1) & 0xFFFF
    state.b = bus.read(state.sp)
