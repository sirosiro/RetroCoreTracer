# retro_core_tracer/arch/z80/instructions.py
"""
Z80命令セットの定義と実行ロジック。

このモジュールはZ80 CPUの各命令のデコード方法と、
CPUの状態をどのように変更するかを定義します。
"""
from typing import List, Tuple, Callable

from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from .alu import update_flags_add8, update_flags_sub8, update_flags_logic8, update_flags_inc_dec8, update_flags_add16, rotate_shift8

# Helper functions for register mapping
REGISTER_CODES = {
    0b000: "B", 0b001: "C", 0b010: "D", 0b011: "E",
    0b100: "H", 0b101: "L", 0b110: "(HL)", 0b111: "A"
}

# @intent:utility_function 指定されたコードに対応するレジスタ名を返します。
def _get_register_name(code: int) -> str:
    return REGISTER_CODES.get(code, "UNKNOWN_REG")

# @intent:utility_function レジスタ名（または(HL)）に基づいて現在の値を取得します。
def _get_register_value(state: Z80CpuState, bus: Bus, reg_name: str) -> int:
    if reg_name == "(HL)":
        return bus.read(state.hl)
    return getattr(state, reg_name.lower())

# @intent:utility_function レジスタ名（または(HL)）に値を設定します。
def _set_register_value(state: Z80CpuState, bus: Bus, reg_name: str, value: int) -> None:
    if reg_name == "(HL)":
        bus.write(state.hl, value & 0xFF)
    else:
        setattr(state, reg_name.lower(), value & 0xFF)

# @intent:utility_function PUSH/POP命令で使用されるレジスタペア名を返します。
def _get_push_pop_reg_name(code: int) -> str:
    return {0b00: "BC", 0b01: "DE", 0b10: "HL", 0b11: "AF"}.get(code, "UNKNOWN")

# @intent:utility_function 16ビット演算で使用されるレジスタペア名(ss)を返します。
def _get_ss_reg_name(code: int) -> str:
    return {0b00: "BC", 0b01: "DE", 0b10: "HL", 0b11: "SP"}.get(code, "UNKNOWN")

# --- Decoding Functions ---

# @intent:responsibility ADD HL,ss 形式の命令をデコードします。
def decode_add_hl_ss(opcode: int, bus: Bus, pc: int) -> Operation:
    """ADD HL,ss命令をデコードします。"""
    ss_code = (opcode >> 4) & 0b11
    ss_name = _get_ss_reg_name(ss_code)
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"ADD HL,{ss_name}",
        operands=[],
        cycle_count=11,
        length=1
    )

# @intent:responsibility SUB/ADC/SBC/CP r 形式の命令をデコードします。
def decode_arith_r(opcode: int, bus: Bus, pc: int) -> Operation:
    """SUB/ADC/SBC r命令をデコードします。"""
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    op_type = (opcode >> 3) & 0b111 # 001: ADC, 010: SUB, 011: SBC
    op_name = {0b001: "ADC A,", 0b010: "SUB ", 0b011: "SBC A,"}.get(op_type)
    
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"{op_name}{src_reg_name}",
        operands=[],
        cycle_count=4 if src_reg_name != "(HL)" else 7,
        length=1
    )

# @intent:responsibility AND/OR/XOR r 形式の命令をデコードします。
def decode_logic_r(opcode: int, bus: Bus, pc: int) -> Operation:
    """AND/OR/XOR r命令をデコードします。"""
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    op_type_code = (opcode >> 3) & 0b11
    op_name = {0b100: "AND", 0b110: "OR", 0b101: "XOR"}.get((opcode >> 3) & 0b111)
    
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"{op_name} A,{src_reg_name}",
        operands=[],
        cycle_count=4 if src_reg_name != "(HL)" else 7,
        length=1
    )

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

def decode_push_pop(opcode: int, bus: Bus, pc: int) -> Operation:
    """PUSH/POP命令をデコードします。"""
    reg_code = (opcode >> 4) & 0b11
    reg_name = _get_push_pop_reg_name(reg_code)
    is_push = (opcode & 0x0F) == 0x05
    mnemonic = f"{'PUSH' if is_push else 'POP'} {reg_name}"
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=11 if is_push else 10,
        length=1
    )

def decode_00(opcode: int, bus: Bus, pc: int) -> Operation:
    """NOP命令をデコードします。"""
    return Operation(opcode_hex="00", mnemonic="NOP", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0x76 (HALT)をデコードします。
def decode_76(opcode: int, bus: Bus, pc: int) -> Operation:
    """HALT命令をデコードします。"""
    return Operation(opcode_hex="76", mnemonic="HALT", operands=[], cycle_count=4, length=1)

# @intent:responsibility LD ss,nn 形式の命令をデコードします。
def decode_ld_ss_nn(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD ss,nn命令をデコードします。"""
    ss_code = (opcode >> 4) & 0b11
    ss_name = _get_ss_reg_name(ss_code)
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    operand_nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"LD {ss_name},nn",
        operands=[f"${operand_nn:04X}"],
        cycle_count=10,
        length=3,
        operand_bytes=[nn_low, nn_high]
    )

# @intent:responsibility LD r,n 形式の命令をデコードします。
def decode_ld_r_n(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD r,n命令をデコードします。"""
    reg_code = (opcode >> 3) & 0b111
    reg_name = _get_register_name(reg_code)
    operand_n = bus.read(pc + 1)
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"LD {reg_name},n",
        operands=[f"${operand_n:02X}"],
        cycle_count=7 if reg_name != "(HL)" else 10,
        length=2,
        operand_bytes=[operand_n]
    )

# @intent:responsibility オペコード0x21 (LD HL,nn)をデコードします。
def decode_21(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD HL,nn命令をデコードします。"""
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    operand_nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex="21",
        mnemonic="LD HL,nn",
        operands=[f"${operand_nn:04X}"],
        cycle_count=10,
        length=3,
        operand_bytes=[nn_low, nn_high]
    )

# @intent:responsibility LD r,r'形式の命令をデコードします。
def decode_ld_r_r_prime(opcode: int, bus: Bus, pc: int) -> Operation:
    """汎用的なLD r,r'命令をデコードします。"""
    dest_reg_code = (opcode >> 3) & 0b111
    src_reg_code = opcode & 0b111
    dest_reg_name = _get_register_name(dest_reg_code)
    src_reg_name = _get_register_name(src_reg_code)
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"LD {dest_reg_name},{src_reg_name}",
        operands=[],
        cycle_count=4 if "(HL)" not in [dest_reg_name, src_reg_name] else 7,
        length=1
    )

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

# @intent:responsibility INC r / DEC r 形式の命令をデコードします。
def decode_inc_dec8(opcode: int, bus: Bus, pc: int) -> Operation:
    """8ビットのINC/DEC命令をデコードします。"""
    reg_code = (opcode >> 3) & 0b111
    reg_name = _get_register_name(reg_code)
    is_inc = (opcode & 1) == 0
    mnemonic = f"{'INC' if is_inc else 'DEC'} {reg_name}"
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=4 if reg_name != "(HL)" else 11,
        length=1
    )

# @intent:responsibility ADD A,r 形式の命令をデコードします。
def decode_add_a_r(opcode: int, bus: Bus, pc: int) -> Operation:
    """ADD A,r命令をデコードします。"""
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"ADD A,{src_reg_name}",
        operands=[],
        cycle_count=4 if src_reg_name != "(HL)" else 7,
        length=1
    )

# @intent:responsibility オペコード0xFE (CP n) をデコードします。
def decode_fe(opcode: int, bus: Bus, pc: int) -> Operation:
    """CP n命令をデコードします。"""
    n = bus.read(pc + 1)
    return Operation(
        opcode_hex="FE",
        mnemonic="CP n",
        operands=[f"${n:02X}"],
        cycle_count=7,
        length=2,
        operand_bytes=[n]
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
    reg_name = _get_register_name(reg_code)
    
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

# @intent:responsibility 0xED プレフィックス命令（ブロック転送、拡張命令）をデコードします。
def decode_ed(opcode: int, bus: Bus, pc: int) -> Operation:
    """EDプレフィックス命令をデコードします。"""
    ed_opcode = bus.read(pc + 1)
    
    # ブロック転送命令
    if ed_opcode == 0xA0: mnemonic = "LDI"
    elif ed_opcode == 0xB0: mnemonic = "LDIR"
    elif ed_opcode == 0xA8: mnemonic = "LDD"
    elif ed_opcode == 0xB8: mnemonic = "LDDR"
    else: mnemonic = f"ED {ed_opcode:02X}"

    # サイクル数: LDI/LDDは16, LDIR/LDDRはBC!=0なら21, BC=0なら16
    cycles = 16
    if mnemonic in ["LDIR", "LDDR"]:
        # ここでは基本の21としておき、execute内で調整が必要なら行う（あるいは可視化のため1回分とする）
        cycles = 21

    return Operation(
        opcode_hex="ED",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=cycles,
        length=2,
        operand_bytes=[ed_opcode]
    )

# --- Execution Functions ---

def execute_ed(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """EDプレフィックス命令を実行します。"""
    ed_opcode = operation.operand_bytes[0]
    
    if ed_opcode in [0xA0, 0xB0, 0xA8, 0xB8]:
        # Block Transfer
        is_repeat = (ed_opcode & 0x10) != 0
        is_decrement = (ed_opcode & 0x08) != 0
        
        # 1 byte transfer
        data = bus.read(state.hl)
        bus.write(state.de, data)
        
        if is_decrement:
            state.hl = (state.hl - 1) & 0xFFFF
            state.de = (state.de - 1) & 0xFFFF
        else:
            state.hl = (state.hl + 1) & 0xFFFF
            state.de = (state.de + 1) & 0xFFFF
            
        state.bc = (state.bc - 1) & 0xFFFF
        
        # Flags
        state.flag_n = False
        state.flag_h = False
        state.flag_pv = state.bc != 0
        # S, Z, C are preserved (no change)
        
        if is_repeat and state.bc != 0:
            # PCをこの命令の先頭に戻すことで、次のstepで再び実行されるようにする
            # Z80Cpu.step 内で既に length=2 分進んでいるため、-2 する
            state.pc = (state.pc - 2) & 0xFFFF
            # 繰り返し時のサイクル数は21 (通常16 + 5)
            # ここではoperation.cycle_countは既に返されているので、累積に影響させるには工夫が必要
            # 今回は簡易的にそのまま進める

def execute_cb(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """CBプレフィックス命令を実行します。"""
    cb_opcode = operation.operand_bytes[0]
    
    reg_code = cb_opcode & 0b111
    reg_name = _get_register_name(reg_code)
    
    type_code = (cb_opcode >> 6) & 0b11
    bit_index = (cb_opcode >> 3) & 0b111
    
    val = _get_register_value(state, bus, reg_name)
    
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
        _set_register_value(state, bus, reg_name, val)
    elif type_code == 0b11: # SET b, r
        val |= (1 << bit_index)
        _set_register_value(state, bus, reg_name, val)
    else: # 0b00: Shift/Rotate
        new_val = rotate_shift8(state, val, bit_index)
        _set_register_value(state, bus, reg_name, new_val)

def execute_add_hl_ss(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    ss_code = (opcode >> 4) & 0b11
    ss_name = _get_ss_reg_name(ss_code).lower()
    val = getattr(state, ss_name)
    result = state.hl + val
    update_flags_add16(state, state.hl, val, result)
    state.hl = result & 0xFFFF

def execute_arith_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    val = _get_register_value(state, bus, src_reg_name)
    op_type = (opcode >> 3) & 0b111 # 001: ADC, 010: SUB, 011: SBC
    
    if op_type == 0b001: # ADC A, r
        carry = 1 if state.flag_c else 0
        result = state.a + val + carry
        update_flags_add8(state, state.a, val, result, carry_in=carry)
        state.a = result & 0xFF
    elif op_type == 0b010: # SUB r
        result = state.a - val
        update_flags_sub8(state, state.a, val, result)
        state.a = result & 0xFF
    elif op_type == 0b011: # SBC A, r
        borrow = 1 if state.flag_c else 0
        result = state.a - val - borrow
        update_flags_sub8(state, state.a, val, result, borrow_in=borrow)
        state.a = result & 0xFF

def execute_logic_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    val = _get_register_value(state, bus, src_name := src_reg_name)
    op_type = (opcode >> 3) & 0b111 # 100: AND, 101: XOR, 110: OR
    
    if op_type == 0b100: # AND
        state.a &= val
        update_flags_logic8(state, state.a, h_flag=True)
    elif op_type == 0b101: # XOR
        state.a ^= val
        update_flags_logic8(state, state.a, h_flag=False)
    elif op_type == 0b110: # OR
        state.a |= val
        update_flags_logic8(state, state.a, h_flag=False)

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

def execute_push_pop(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    reg_code = (opcode >> 4) & 0b11
    reg_name = _get_push_pop_reg_name(reg_code).lower()
    is_push = (opcode & 0x0F) == 0x05

    if is_push:
        # PUSH: SP <- SP - 1, (SP) <- high; SP <- SP - 1, (SP) <- low
        val = getattr(state, reg_name)
        high = (val >> 8) & 0xFF
        low = val & 0xFF
        state.sp = (state.sp - 1) & 0xFFFF
        bus.write(state.sp, high)
        state.sp = (state.sp - 1) & 0xFFFF
        bus.write(state.sp, low)
    else:
        # POP: low <- (SP), SP <- SP + 1; high <- (SP), SP <- SP + 1
        low = bus.read(state.sp)
        state.sp = (state.sp + 1) & 0xFFFF
        high = bus.read(state.sp)
        state.sp = (state.sp + 1) & 0xFFFF
        setattr(state, reg_name, (high << 8) | low)

def execute_00(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    pass

def execute_76(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    # @intent:responsibility CPUをHALT（停止）状態にします。割り込みが発生するまで停止し続けます。
    state.halted = True

def execute_ld_ss_nn(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    ss_code = (opcode >> 4) & 0b11
    ss_name = _get_ss_reg_name(ss_code).lower()
    nn_low, nn_high = operation.operand_bytes
    value = (nn_high << 8) | nn_low
    setattr(state, ss_name, value)

def execute_ld_r_n(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    reg_name = _get_register_name((opcode >> 3) & 0b111)
    value = operation.operand_bytes[0]
    _set_register_value(state, bus, reg_name, value)

def execute_21(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    low, high = operation.operand_bytes
    state.hl = (high << 8) | low

def execute_ld_r_r_prime(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    dest_name = _get_register_name((opcode >> 3) & 0b111)
    src_name = _get_register_name(opcode & 0b111)
    val = _get_register_value(state, bus, src_name)
    _set_register_value(state, bus, dest_name, val)

def execute_c3(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    low, high = operation.operand_bytes
    state.pc = (high << 8) | low

def execute_18(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    offset = operation.operand_bytes[0]
    if offset >= 128:
        offset -= 256
    # Note: PC is already incremented by operation.length before execution in Z80Cpu.step
    state.pc = (state.pc + offset) & 0xFFFF

def execute_inc_dec8(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    reg_name = _get_register_name((opcode >> 3) & 0b111)
    is_inc = (opcode & 1) == 0
    val = _get_register_value(state, bus, reg_name)
    result = (val + 1) if is_inc else (val - 1)
    update_flags_inc_dec8(state, val, result, is_inc)
    _set_register_value(state, bus, reg_name, result & 0xFF)

def execute_add_a_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    src_name = _get_register_name(opcode & 0b111)
    val = _get_register_value(state, bus, src_name)
    result = state.a + val
    update_flags_add8(state, state.a, val, result)
    state.a = result & 0xFF

def execute_fe(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    n = operation.operand_bytes[0]
    result = state.a - n
    update_flags_sub8(state, state.a, n, result)
    # CP does not store the result

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

def execute_db(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """IN A,(n)命令を実行します。"""
    port = operation.operand_bytes[0]
    # Z80では上位8ビットにAレジスタの値が出力される
    address = (state.a << 8) | port
    state.a = bus.read_io(address)

def execute_d3(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """OUT (n),A命令を実行します。"""
    port = operation.operand_bytes[0]
    address = (state.a << 8) | port
    bus.write_io(address, state.a)

# --- Tables ---

DECODE_MAP = {
    0x00: decode_00,
    0x10: decode_10,
    0x76: decode_76,
    0xCB: decode_cb,
    0xED: decode_ed,
    0xC3: decode_c3,
    0xC9: decode_c9,
    0xCD: decode_cd,
    0xDB: decode_db,
    0xD3: decode_d3,
    0x18: decode_18,
    0xFE: decode_fe,
    **{op: decode_ld_ss_nn for op in range(0x01, 0x40, 0x10)}, # LD BC/DE/HL/SP, nn
    **{op: decode_add_hl_ss for op in range(0x09, 0x40, 0x10)}, # ADD HL,ss
    **{op: decode_ld_r_n for op in range(0x06, 0x40, 0x08)}, # LD r,n
    **{op: decode_jr_cc_e for op in range(0x20, 0x40, 0x08)},
    **{op: decode_ld_r_r_prime for op in range(0x40, 0x80) if op != 0x76},
    **{op: decode_inc_dec8 for op in range(0x04, 0x40, 0x08)}, # INC r
    **{op: decode_inc_dec8 for op in range(0x05, 0x40, 0x08)}, # DEC r
    **{op: decode_add_a_r for op in range(0x80, 0x88)},
    **{op: decode_arith_r for op in range(0x88, 0xA0)}, # ADC, SUB, SBC r
    **{op: decode_arith_r for op in range(0xB8, 0xC0)}, # CP r
    **{op: decode_logic_r for op in range(0xA0, 0xB8)}, # AND, XOR, OR r
    **{op: decode_push_pop for op in range(0xC5, 0x100, 0x10)}, # PUSH qq
    **{op: decode_push_pop for op in range(0xC1, 0x100, 0x10)}, # POP qq
}

EXECUTE_MAP = {
    0x00: execute_00,
    0x10: execute_10,
    0x76: execute_76,
    0xCB: execute_cb,
    0xED: execute_ed,
    0xC3: execute_c3,
    0xC9: execute_c9,
    0xCD: execute_cd,
    0xDB: execute_db,
    0xD3: execute_d3,
    0x18: execute_18,
    0xFE: execute_fe,
    **{op: execute_ld_ss_nn for op in range(0x01, 0x40, 0x10)},
    **{op: execute_add_hl_ss for op in range(0x09, 0x40, 0x10)},
    **{op: execute_ld_r_n for op in range(0x06, 0x40, 0x08)},
    **{op: execute_jr_cc_e for op in range(0x20, 0x40, 0x08)},
    **{op: execute_ld_r_r_prime for op in range(0x40, 0x80) if op != 0x76},
    **{op: execute_inc_dec8 for op in range(0x04, 0x40, 0x08)},
    **{op: execute_inc_dec8 for op in range(0x05, 0x40, 0x08)},
    **{op: execute_add_a_r for op in range(0x80, 0x88)},
    **{op: execute_arith_r for op in range(0x88, 0xA0)},
    **{op: execute_arith_r for op in range(0xB8, 0xC0)},
    **{op: execute_logic_r for op in range(0xA0, 0xB8)},
    **{op: execute_push_pop for op in range(0xC5, 0x100, 0x10)},
    **{op: execute_push_pop for op in range(0xC1, 0x100, 0x10)},
}

# @intent:responsibility 与えられたオペコードをZ80の命令としてデコードします。
# @intent:pre-condition `pc`はデコードするオペコードの先頭アドレスを指している必要があります。
def decode_opcode(opcode: int, bus: Bus, pc: int) -> Operation:
    """
    Z80のオペコードをデコードし、Operationオブジェクトを返します。
    未知のオペコードの場合は"UNKNOWN"を返します。
    """
    decoder = DECODE_MAP.get(opcode)
    if decoder:
        return decoder(opcode, bus, pc)
    return Operation(opcode_hex=f"{opcode:02X}", mnemonic="UNKNOWN", operands=[f"${opcode:02X}"], cycle_count=4, length=1)

# @intent:responsibility デコードされたZ80命令を実行し、CPUの状態を変更します。
# @intent:pre-condition `operation`は有効なOperationオブジェクトである必要があります。
def execute_instruction(operation: Operation, state: Z80CpuState, bus: Bus) -> None:
    """
    デコードされたZ80命令を実行し、CPUの状態を変更します。
    """
    executor = EXECUTE_MAP.get(int(operation.opcode_hex, 16))
    if executor:
        executor(state, bus, operation)
