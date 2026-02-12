"""
Z80 制御命令（分岐、ビット操作、I/O、システム制御）の実装。
"""
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.arch.z80.alu import rotate_shift8
from .base import (
    get_register_name, get_register_value, set_register_value
)
from .load import execute_push_pop, decode_push_pop # execute_reti_retn uses execute_c9 (which is basically a POP) - Wait, execute_c9 is not push_pop.

# Need to forward declare or import internal helpers if needed.
# For RETI/RETN, it calls execute_c9. We should define execute_c9 here or in load.
# RET/CALL are control flow, so they belong here.

# --- Decoding Functions ---

# @intent:responsibility オペコード0xCD (CALL nn) をデコードします。
def decode_cd(opcode: int, bus: Bus, pc: int) -> Operation:
    """CALL nn命令をデコードします。"""
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex="CD",
        mnemonic="CALL nn",
        operands=[f"${nn:04X}"],
        cycle_count=17,
        length=3,
        operand_bytes=[nn_low, nn_high]
    )

# @intent:responsibility オペコード0xC9 (RET) をデコードします。
def decode_c9(opcode: int, bus: Bus, pc: int) -> Operation:
    """RET命令をデコードします。"""
    return Operation(
        opcode_hex="C9",
        mnemonic="RET",
        operands=[],
        cycle_count=10,
        length=1
    )

def decode_00(opcode: int, bus: Bus, pc: int) -> Operation:
    """NOP命令をデコードします。"""
    return Operation(opcode_hex="00", mnemonic="NOP", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0x76 (HALT)をデコードします。
def decode_76(opcode: int, bus: Bus, pc: int) -> Operation:
    """HALT命令をデコードします。"""
    return Operation(opcode_hex="76", mnemonic="HALT", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0xC3 (JP nn) をデコードします。
def decode_c3(opcode: int, bus: Bus, pc: int) -> Operation:
    """JP nn命令をデコードします。"""
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex="C3",
        mnemonic="JP nn",
        operands=[f"${nn:04X}"],
        cycle_count=10,
        length=3,
        operand_bytes=[nn_low, nn_high]
    )

# @intent:responsibility オペコード0x18 (JR e) をデコードします。
def decode_18(opcode: int, bus: Bus, pc: int) -> Operation:
    """JR e命令をデコードします。"""
    offset = bus.read(pc + 1)
    # Signed 8-bit offset
    if offset >= 128:
        offset -= 256
    target = (pc + 2 + offset) & 0xFFFF
    return Operation(
        opcode_hex="18",
        mnemonic="JR e",
        operands=[f"${target:04X}"],
        cycle_count=12,
        length=2,
        operand_bytes=[bus.read(pc + 1)]
    )

# @intent:responsibility オペコード0x10 (DJNZ e) をデコードします。
def decode_10(opcode: int, bus: Bus, pc: int) -> Operation:
    """DJNZ e命令をデコードします。"""
    offset = bus.read(pc + 1)
    if offset >= 128:
        offset -= 256
    target = (pc + 2 + offset) & 0xFFFF
    return Operation(
        opcode_hex="10",
        mnemonic="DJNZ e",
        operands=[f"${target:04X}"],
        cycle_count=13, # 13 if jump, 8 if no jump
        length=2,
        operand_bytes=[bus.read(pc + 1)]
    )

# @intent:responsibility JR cc,e 形式の命令をデコードします。
def decode_jr_cc_e(opcode: int, bus: Bus, pc: int) -> Operation:
    """条件付き相対ジャンプ命令をデコードします。"""
    cc_code = (opcode >> 3) & 0b11
    cc_map = {0: "NZ", 1: "Z", 2: "NC", 3: "C"}
    cc = cc_map[cc_code]
    offset = bus.read(pc + 1)
    if offset >= 128:
        offset -= 256
    target = (pc + 2 + offset) & 0xFFFF
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"JR {cc},e",
        operands=[f"${target:04X}"],
        cycle_count=12,
        length=2,
        operand_bytes=[bus.read(pc + 1)]
    )

# @intent:responsibility 0xCB プレフィックス命令（ビット操作、シフト、ローテート）をデコードします。
def decode_cb(opcode: int, bus: Bus, pc: int) -> Operation:
    """CBプレフィックス命令をデコードします。"""
    cb_opcode = bus.read(pc + 1)
    
    reg_code = cb_opcode & 0b111
    reg_name = get_register_name(reg_code)
    
    type_code = (cb_opcode >> 6) & 0b11
    bit_index = (cb_opcode >> 3) & 0b111
    
    if type_code == 0b01: # BIT b, r
        mnemonic = f"BIT {bit_index},{reg_name}"
        cycles = 8 if reg_name != "(HL)" else 12
    elif type_code == 0b10: # RES b, r
        mnemonic = f"RES {bit_index},{reg_name}"
        cycles = 8 if reg_name != "(HL)" else 15
    elif type_code == 0b11: # SET b, r
        mnemonic = f"SET {bit_index},{reg_name}"
        cycles = 8 if reg_name != "(HL)" else 15
    else: # 0b00: Shift/Rotate
        shift_ops = ["RLC", "RRC", "RL", "RR", "SLA", "SRA", "SLL", "SRL"]
        mnemonic = f"{shift_ops[bit_index]} {reg_name}"
        cycles = 8 if reg_name != "(HL)" else 15

    return Operation(
        opcode_hex="CB",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=cycles,
        length=2,
        operand_bytes=[cb_opcode]
    )

# @intent:responsibility オペコード0xFB (EI) をデコードします。
def decode_fb(opcode: int, bus: Bus, pc: int) -> Operation:
    """EI命令をデコードします。"""
    return Operation(opcode_hex="FB", mnemonic="EI", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0xF3 (DI) をデコードします。
def decode_f3(opcode: int, bus: Bus, pc: int) -> Operation:
    """DI命令をデコードします。"""
    return Operation(opcode_hex="F3", mnemonic="DI", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0x08 (EX AF,AF') をデコードします。
def decode_08(opcode: int, bus: Bus, pc: int) -> Operation:
    """EX AF,AF'命令をデコードします。"""
    return Operation(opcode_hex="08", mnemonic="EX AF,AF'", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0xEB (EX DE,HL) をデコードします。
def decode_eb(opcode: int, bus: Bus, pc: int) -> Operation:
    """EX DE,HL命令をデコードします。"""
    return Operation(opcode_hex="EB", mnemonic="EX DE,HL", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0xD9 (EXX) をデコードします。
def decode_d9(opcode: int, bus: Bus, pc: int) -> Operation:
    """EXX命令をデコードします。"""
    return Operation(opcode_hex="D9", mnemonic="EXX", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0xE3 (EX (SP),HL) をデコードします。
def decode_e3(opcode: int, bus: Bus, pc: int) -> Operation:
    """EX (SP),HL命令をデコードします。"""
    return Operation(opcode_hex="E3", mnemonic="EX (SP),HL", operands=[], cycle_count=19, length=1)

# @intent:responsibility オペコード0xDB (IN A,(n)) をデコードします。
def decode_db(opcode: int, bus: Bus, pc: int) -> Operation:
    """IN A,(n)命令をデコードします。"""
    n = bus.read(pc + 1)
    return Operation(
        opcode_hex="DB",
        mnemonic="IN A,(n)",
        operands=[f"(${n:02X})"],
        cycle_count=11,
        length=2,
        operand_bytes=[n]
    )

# @intent:responsibility オペコード0xD3 (OUT (n),A) をデコードします。
def decode_d3(opcode: int, bus: Bus, pc: int) -> Operation:
    """OUT (n),A命令をデコードします。"""
    n = bus.read(pc + 1)
    return Operation(
        opcode_hex="D3",
        mnemonic="OUT (n),A",
        operands=[f"(${n:02X})"],
        cycle_count=11,
        length=2,
        operand_bytes=[n]
    )

# --- Execution Functions ---

def execute_cd(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    # CALL nn: Push PC to stack, then jump
    # PC is already at the instruction AFTER CALL nn (since length=3 was added in step)
    high = (state.pc >> 8) & 0xFF
    low = state.pc & 0xFF
    state.sp = (state.sp - 1) & 0xFFFF
    bus.write(state.sp, high)
    state.sp = (state.sp - 1) & 0xFFFF
    bus.write(state.sp, low)
    
    # Target address from operands
    nn_low, nn_high = operation.operand_bytes
    state.pc = (nn_high << 8) | nn_low

def execute_c9(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    # RET: Pop PC from stack
    low = bus.read(state.sp)
    state.sp = (state.sp + 1) & 0xFFFF
    high = bus.read(state.sp)
    state.sp = (state.sp + 1) & 0xFFFF
    state.pc = (high << 8) | low

def execute_00(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    # Intentional: NOP (No Operation)
    pass

def execute_76(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    # @intent:responsibility CPUをHALT（停止）状態にします。割り込みが発生するまで停止し続けます。
    state.halted = True

def execute_c3(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    low, high = operation.operand_bytes
    state.pc = (high << 8) | low

def execute_18(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    offset = operation.operand_bytes[0]
    if offset >= 128:
        offset -= 256
    # Note: PC is already incremented by operation.length before execution in Z80Cpu.step
    state.pc = (state.pc + offset) & 0xFFFF

def execute_10(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    state.b = (state.b - 1) & 0xFF
    if state.b != 0:
        offset = operation.operand_bytes[0]
        if offset >= 128:
            offset -= 256
        state.pc = (state.pc + offset) & 0xFFFF

def execute_jr_cc_e(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    cc_code = (opcode >> 3) & 0b11
    
    condition = False
    if cc_code == 0: condition = not state.flag_z # NZ
    elif cc_code == 1: condition = state.flag_z     # Z
    elif cc_code == 2: condition = not state.flag_c # NC
    elif cc_code == 3: condition = state.flag_c     # C
    
    if condition:
        offset = operation.operand_bytes[0]
        if offset >= 128:
            offset -= 256
        state.pc = (state.pc + offset) & 0xFFFF

def execute_cb(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """CBプレフィックス命令を実行します。"""
    cb_opcode = operation.operand_bytes[0]
    
    reg_code = cb_opcode & 0b111
    reg_name = get_register_name(reg_code)
    
    type_code = (cb_opcode >> 6) & 0b11
    bit_index = (cb_opcode >> 3) & 0b111
    
    val = get_register_value(state, bus, reg_name)
    
    if type_code == 0b01: # BIT b, r
        # BIT命令のフラグ更新
        res = val & (1 << bit_index)
        state.flag_z = res == 0
        state.flag_h = True
        state.flag_n = False
        state.flag_s = (bit_index == 7) and (res != 0)
        # P/V is same as Z
        state.flag_pv = state.flag_z
    elif type_code == 0b10: # RES b, r
        val &= ~(1 << bit_index)
        set_register_value(state, bus, reg_name, val)
    elif type_code == 0b11: # SET b, r
        val |= (1 << bit_index)
        set_register_value(state, bus, reg_name, val)
    else: # 0b00: Shift/Rotate
        new_val = rotate_shift8(state, val, bit_index)
        set_register_value(state, bus, reg_name, new_val)

def execute_fb(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """EI命令を実行します。"""
    state.iff1 = True
    state.iff2 = True

def execute_f3(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """DI命令を実行します。"""
    state.iff1 = False
    state.iff2 = False

def execute_im(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """IM 0/1/2命令を実行します。"""
    ed_opcode = operation.operand_bytes[0]
    if ed_opcode == 0x46: state.im = 0
    elif ed_opcode == 0x56: state.im = 1
    elif ed_opcode == 0x5E: state.im = 2

def execute_reti_retn(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """RETI/RETN命令を実行します。"""
    # スタックから戻り先PCを復帰
    execute_c9(state, bus, operation)
    
    ed_opcode = operation.operand_bytes[0]
    if ed_opcode == 0x45: # RETN
        # IFF2をIFF1にコピー
        state.iff1 = state.iff2

def execute_08(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """EX AF,AF'命令を実行します。"""
    state.af, state.af_ = state.af_, state.af

def execute_eb(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """EX DE,HL命令を実行します。"""
    state.de, state.hl = state.hl, state.de

def execute_d9(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """EXX命令を実行します。"""
    state.bc, state.bc_ = state.bc_, state.bc
    state.de, state.de_ = state.de_, state.de
    state.hl, state.hl_ = state.hl_, state.hl

def execute_e3(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """EX (SP),HL命令を実行します。"""
    # Low byte
    low = bus.read(state.sp)
    bus.write(state.sp, state.l)
    state.l = low
    # High byte
    high = bus.read(state.sp + 1)
    bus.write(state.sp + 1, state.h)
    state.h = high

def execute_db(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """IN A,(n)命令を実行します。"""
    port = operation.operand_bytes[0]
    address = (state.a << 8) | port
    state.a = bus.read_io(address)

def execute_d3(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """OUT (n),A命令を実行します。"""
    port = operation.operand_bytes[0]
    address = (state.a << 8) | port
    bus.write_io(address, state.a)
