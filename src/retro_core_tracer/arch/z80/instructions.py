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
from .alu import update_flags_add8, update_flags_sub8, update_flags_logic8, update_flags_inc_dec8

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

# --- Decoding Functions ---

# @intent:responsibility オペコード0x00 (NOP)をデコードします。
def decode_00(opcode: int, bus: Bus, pc: int) -> Operation:
    """NOP命令をデコードします。"""
    return Operation(opcode_hex="00", mnemonic="NOP", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0x76 (HALT)をデコードします。
def decode_76(opcode: int, bus: Bus, pc: int) -> Operation:
    """HALT命令をデコードします。"""
    return Operation(opcode_hex="76", mnemonic="HALT", operands=[], cycle_count=4, length=1)

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

# --- Execution Functions ---

def execute_00(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    pass

def execute_76(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    # TODO: Implement HALT state
    pass

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

# --- Tables ---

DECODE_MAP = {
    0x00: decode_00,
    0x10: decode_10,
    0x76: decode_76,
    0x21: decode_21,
    0xC3: decode_c3,
    0x18: decode_18,
    0xFE: decode_fe,
    **{op: decode_ld_r_n for op in range(0x06, 0x40, 0x08)}, # LD r,n
    **{op: decode_jr_cc_e for op in range(0x20, 0x40, 0x08)},
    **{op: decode_ld_r_r_prime for op in range(0x40, 0x80) if op != 0x76},
    **{op: decode_inc_dec8 for op in range(0x04, 0x40, 0x08)}, # INC r
    **{op: decode_inc_dec8 for op in range(0x05, 0x40, 0x08)}, # DEC r
    **{op: decode_add_a_r for op in range(0x80, 0x88)},
}

EXECUTE_MAP = {
    0x00: execute_00,
    0x10: execute_10,
    0x76: execute_76,
    0x21: execute_21,
    0xC3: execute_c3,
    0x18: execute_18,
    0xFE: execute_fe,
    **{op: execute_ld_r_n for op in range(0x06, 0x40, 0x08)},
    **{op: execute_jr_cc_e for op in range(0x20, 0x40, 0x08)},
    **{op: execute_ld_r_r_prime for op in range(0x40, 0x80) if op != 0x76},
    **{op: execute_inc_dec8 for op in range(0x04, 0x40, 0x08)},
    **{op: execute_inc_dec8 for op in range(0x05, 0x40, 0x08)},
    **{op: execute_add_a_r for op in range(0x80, 0x88)},
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
