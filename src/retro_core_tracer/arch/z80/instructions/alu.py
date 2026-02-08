"""
Z80 算術論理演算 (ALU) 命令の実装。
"""
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from retro_core_tracer.arch.z80.alu import (
    update_flags_add8, update_flags_sub8, update_flags_logic8, 
    update_flags_inc_dec8, update_flags_add16, rotate_shift8
)
from .base import (
    get_register_name, get_register_value, set_register_value, get_ss_reg_name
)

# --- Decoding Functions ---

# @intent:responsibility ADD HL,ss 形式の命令をデコードします。
def decode_add_hl_ss(opcode: int, bus: Bus, pc: int) -> Operation:
    """ADD HL,ss命令をデコードします。"""
    ss_code = (opcode >> 4) & 0b11
    ss_name = get_ss_reg_name(ss_code)
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
    src_reg_name = get_register_name(src_reg_code)
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
    src_reg_name = get_register_name(src_reg_code)
    op_type_code = (opcode >> 3) & 0b11
    op_name = {0b100: "AND", 0b110: "OR", 0b101: "XOR"}.get((opcode >> 3) & 0b111)
    
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"{op_name} A,{src_reg_name}",
        operands=[],
        cycle_count=4 if src_reg_name != "(HL)" else 7,
        length=1
    )

# @intent:responsibility INC r / DEC r 形式の命令をデコードします。
def decode_inc_dec8(opcode: int, bus: Bus, pc: int) -> Operation:
    """8ビットのINC/DEC命令をデコードします。"""
    reg_code = (opcode >> 3) & 0b111
    reg_name = get_register_name(reg_code)
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
    src_reg_name = get_register_name(src_reg_code)
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

# --- Execution Functions ---

def execute_add_hl_ss(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    ss_code = (opcode >> 4) & 0b11
    ss_name = get_ss_reg_name(ss_code).lower()
    val = getattr(state, ss_name)
    result = state.hl + val
    update_flags_add16(state, state.hl, val, result)
    state.hl = result & 0xFFFF

def execute_arith_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    src_reg_code = opcode & 0b111
    src_reg_name = get_register_name(src_reg_code)
    val = get_register_value(state, bus, src_reg_name)
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
    src_reg_name = get_register_name(src_reg_code)
    val = get_register_value(state, bus, src_name := src_reg_name)
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

def execute_inc_dec8(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    reg_name = get_register_name((opcode >> 3) & 0b111)
    is_inc = (opcode & 1) == 0
    val = get_register_value(state, bus, reg_name)
    result = (val + 1) if is_inc else (val - 1)
    update_flags_inc_dec8(state, val, result, is_inc)
    set_register_value(state, bus, reg_name, result & 0xFF)

def execute_add_a_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    src_name = get_register_name(opcode & 0b111)
    val = get_register_value(state, bus, src_name)
    result = state.a + val
    update_flags_add8(state, state.a, val, result)
    state.a = result & 0xFF

def execute_fe(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    n = operation.operand_bytes[0]
    result = state.a - n
    update_flags_sub8(state, state.a, n, result)
    # CP does not store the result
