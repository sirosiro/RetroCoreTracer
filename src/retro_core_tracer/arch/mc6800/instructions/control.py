# src/retro_core_tracer/arch/mc6800/instructions/control.py
"""
制御命令（分岐、ジャンプ、サブルーチン）の実装。
"""
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.state import Mc6800CpuState

# --- BRA ---
# @intent:responsibility BRA (Branch Always) 命令をデコードします。
def decode_bra(opcode: int, bus: Bus, pc: int) -> Operation:
    offset = bus.read((pc + 1) & 0xFFFF)
    # Signed 8-bit offset
    rel_off = offset if offset < 128 else offset - 256
    target = (pc + 2 + rel_off) & 0xFFFF
    return Operation("20", "BRA", [f"${target:04X}"], [offset], 4, 2)

# @intent:responsibility BRA命令を実行し、PCを相対ジャンプさせます。
def execute_bra(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    offset = op.operand_bytes[0]
    rel_off = offset if offset < 128 else offset - 256
    state.pc = (state.pc + rel_off) & 0xFFFF

# --- BNE ---
# @intent:responsibility BNE (Branch if Not Equal) 命令をデコードします。
def decode_bne(opcode: int, bus: Bus, pc: int) -> Operation:
    offset = bus.read((pc + 1) & 0xFFFF)
    rel_off = offset if offset < 128 else offset - 256
    target = (pc + 2 + rel_off) & 0xFFFF
    return Operation("26", "BNE", [f"${target:04X}"], [offset], 4, 2)

# @intent:responsibility BNE命令を実行し、Zフラグがクリアされている場合に分岐します。
def execute_bne(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    if not state.flag_z:
        offset = op.operand_bytes[0]
        rel_off = offset if offset < 128 else offset - 256
        state.pc = (state.pc + rel_off) & 0xFFFF

# --- BEQ ---
# @intent:responsibility BEQ (Branch if Equal) 命令をデコードします。
def decode_beq(opcode: int, bus: Bus, pc: int) -> Operation:
    offset = bus.read((pc + 1) & 0xFFFF)
    rel_off = offset if offset < 128 else offset - 256
    target = (pc + 2 + rel_off) & 0xFFFF
    return Operation("27", "BEQ", [f"${target:04X}"], [offset], 4, 2)

# @intent:responsibility BEQ命令を実行し、Zフラグがセットされている場合に分岐します。
def execute_beq(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    if state.flag_z:
        offset = op.operand_bytes[0]
        rel_off = offset if offset < 128 else offset - 256
        state.pc = (state.pc + rel_off) & 0xFFFF

# --- JSR ---
# @intent:responsibility JSR (Jump to Subroutine, Extended) 命令をデコードします。
def decode_jsr_ext(opcode: int, bus: Bus, pc: int) -> Operation:
    b1 = bus.read((pc + 1) & 0xFFFF)
    b2 = bus.read((pc + 2) & 0xFFFF)
    addr = (b1 << 8) | b2
    return Operation("BD", "JSR", [f"${addr:04X}"], [b1, b2], 9, 3)

# @intent:responsibility JSR命令を実行し、戻りアドレスをスタックにプッシュしてからジャンプします。
def execute_jsr_ext(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    # Target Address
    target = (op.operand_bytes[0] << 8) | op.operand_bytes[1]
    
    # Return Address is Next Instruction
    # state.pc is currently pointing to the NEXT instruction because it was updated in CPU.step
    return_addr = state.pc
    
    bus.write(state.sp, return_addr & 0xFF) # Push Low
    state.sp = (state.sp - 1) & 0xFFFF
    bus.write(state.sp, (return_addr >> 8) & 0xFF) # Push High
    state.sp = (state.sp - 1) & 0xFFFF
    
    state.pc = target

# --- RTS ---
# @intent:responsibility RTS (Return from Subroutine) 命令をデコードします。
def decode_rts(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("39", "RTS", [], [], 5, 1)

# @intent:responsibility RTS命令を実行し、スタックから戻りアドレスをポップしてPCに設定します。
def execute_rts(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    state.sp = (state.sp + 1) & 0xFFFF
    high = bus.read(state.sp)
    state.sp = (state.sp + 1) & 0xFFFF
    low = bus.read(state.sp)
    state.pc = (high << 8) | low

# --- NOP ---
# @intent:responsibility NOP (No Operation) 命令をデコードします。
def decode_nop(opcode: int, bus: Bus, pc: int) -> Operation:
    return Operation("01", "NOP", [], [], 2, 1)

# @intent:responsibility NOP命令を実行します（何もしません）。
def execute_nop(state: Mc6800CpuState, bus: Bus, op: Operation) -> None:
    # Intentional: NOP (No Operation)
    pass