# retro_core_tracer/arch/z80/instructions.py
"""
Z80命令セットの定義と実行ロジック。

このモジュールはZ80 CPUの各命令のデコード方法と、
CPUの状態をどのように変更するかを定義します。
"""
from typing import List, Tuple

from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation

# Helper functions for register mapping
REGISTER_CODES = {
    0b000: "B", 0b001: "C", 0b010: "D", 0b011: "E",
    0b100: "H", 0b101: "L", 0b110: "(HL)", 0b111: "A"
}

REGISTER_MAP = {
    "B": lambda state: state.b, "C": lambda state: state.c,
    "D": lambda state: state.d, "E": lambda state: state.e,
    "H": lambda state: state.h, "L": lambda state: state.l,
    "A": lambda state: state.a,
}

REGISTER_SET_MAP = {
    "B": lambda state, value: setattr(state, 'b', value),
    "C": lambda state, value: setattr(state, 'c', value),
    "D": lambda state, value: setattr(state, 'd', value),
    "E": lambda state, value: setattr(state, 'e', value),
    "H": lambda state, value: setattr(state, 'h', value),
    "L": lambda state, value: setattr(state, 'l', value),
    "A": lambda state, value: setattr(state, 'a', value),
}

def _get_register_name(code: int) -> str:
    return REGISTER_CODES.get(code, "UNKNOWN_REG")

def _get_register_value(state: Z80CpuState, bus: Bus, reg_name: str) -> int:
    if reg_name == "(HL)":
        return bus.read(state.hl)
    return REGISTER_MAP[reg_name](state)

def _set_register_value(state: Z80CpuState, bus: Bus, reg_name: str, value: int) -> None:
    if reg_name == "(HL)":
        bus.write(state.hl, value)
    else:
        REGISTER_SET_MAP[reg_name](state, value)

# @intent:utility_function Z80のS (Sign) と Z (Zero) フラグを設定します。
def _set_sz_flags(state: Z80CpuState, value: int) -> None:
    state.flag_s = (value & 0x80) != 0  # Bit 7 (MSB) determines sign
    state.flag_z = (value == 0)

# @intent:utility_function Z80のPV (Parity/Overflow) フラグをパリティに基づいて設定します。
def _set_pv_flag_parity(state: Z80CpuState, value: int) -> None:
    # Parity is set if the number of set bits is even
    # Z80 PV flag is Parity for logical operations, Overflow for arithmetic
    # For ADD/SUB, it's Overflow, for AND/OR/XOR, it's Parity
    # For ADD A,r it's Overflow. But for now, let's use parity as a placeholder for simpler instructions.
    # We will refine this for overflow later.
    parity = 0
    for i in range(8):
        if (value >> i) & 1:
            parity += 1
    state.flag_pv = (parity % 2) == 0 # Even parity


# @intent:responsibility オペコード0x00 (NOP)をデコードします。
def decode_00(opcode: int, bus: Bus, pc: int) -> Operation:
    """NOP命令をデコードします。"""
    # NOPは1バイト命令でオペランドなし
    return Operation(opcode_hex="00", mnemonic="NOP", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0x76 (HALT)をデコードします。
def decode_76(opcode: int, bus: Bus, pc: int) -> Operation:
    """HALT命令をデコードします。"""
    # HALTは1バイト命令でオペランドなし
    return Operation(opcode_hex="76", mnemonic="HALT", operands=[], cycle_count=4, length=1)

# @intent:responsibility オペコード0x3E (LD A,n)をデコードします。
def decode_3e(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD A,n命令をデコードします。"""
    # LD A,nは2バイト命令 (0x3E, n)。nは直後のバイト
    operand_n = bus.read(pc + 1)
    return Operation(
        opcode_hex="3E",
        mnemonic="LD A,n",
        operands=[f"${operand_n:02X}"],
        cycle_count=7, # 仮のサイクル数
        length=2, # 1バイトオペコード + 1バイトオペランド
        operand_bytes=[operand_n]
    )

# @intent:responsibility オペコード0x21 (LD HL,nn)をデコードします。
def decode_21(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD HL,nn命令をデコードします。"""
    # LD HL,nnは3バイト命令 (0x21, nn_low, nn_high)。nnは直後2バイトのリトルエンディアン
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    operand_nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex="21",
        mnemonic="LD HL,nn",
        operands=[f"${operand_nn:04X}"],
        cycle_count=10, # 仮のサイクル数
        length=3, # 1バイトオペコード + 2バイトオペランド
        operand_bytes=[nn_low, nn_high]
    )


# @intent:responsibility オペコード0x77 (LD (HL),A)をデコードします。
def decode_77(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD (HL),A命令をデコードします。"""
    return Operation(opcode_hex="77", mnemonic="LD (HL),A", operands=[], cycle_count=7, length=1)

# @intent:responsibility オペコード0x7E (LD A,(HL))をデコードします。
def decode_7e(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD A,(HL)命令をデコードします。"""
    return Operation(opcode_hex="7E", mnemonic="LD A,(HL)", operands=[], cycle_count=7, length=1)

# @intent:responsibility LD r,r'形式の命令をデコードします。
def decode_ld_r_r_prime(opcode: int, bus: Bus, pc: int) -> Operation:
    """汎用的なLD r,r' (Load Register to Register)命令をデコードします。"""
    dest_reg_code = (opcode >> 3) & 0b111
    src_reg_code = opcode & 0b111
    
    dest_reg_name = _get_register_name(dest_reg_code)
    src_reg_name = _get_register_name(src_reg_code)

    mnemonic = f"LD {dest_reg_name},{src_reg_name}"
    
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=4 if "(HL)" not in [dest_reg_name, src_reg_name] else 7, # 汎用的なサイクル数
        length=1
    )

# @intent:responsibility ADD A,r形式の命令をデコードします。
def decode_add_a_r(opcode: int, bus: Bus, pc: int) -> Operation:
    """汎用的なADD A,r (Add Register to Accumulator)命令をデコードします。"""
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    
    mnemonic = f"ADD A,{src_reg_name}"
    
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=4 if src_reg_name != "(HL)" else 7, # 汎用的なサイクル数
        length=1
    )

# Z80の主要なデコード関数へのマッピング
# @intent:data_structure Z80のオペコードとデコード関数をマッピングするテーブル。
DECODE_MAP = {
    # ADD A,r instructions (0x80 to 0x87)
    **{op: decode_add_a_r for op in range(0x80, 0x88)},
    # LD r,r' instructions (0x40 to 0x7F)
    # Filter out 0x76 (HALT)
    **{op: decode_ld_r_r_prime for op in range(0x40, 0x80) if op != 0x76},
    0x00: decode_00, # NOP
    0x76: decode_76, # HALT (overwrites generic if in range)
    0x3E: decode_3e, # LD A,n
    0x21: decode_21, # LD HL,nn
    0x77: decode_77, # LD (HL),A (overwrites generic if in range)
    0x7E: decode_7e, # LD A,(HL) (overwrites generic if in range)
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
        return decoder(opcode, bus, pc) # Pass opcode to decoder
    else:
        # 未知のオペコードの場合、それ自体をオペランドとして扱い、1バイト命令とする
        return Operation(opcode_hex=f"{opcode:02X}", mnemonic="UNKNOWN", operands=[f"${opcode:02X}"], cycle_count=4, length=1)


# @intent:responsibility オペコード0x00 (NOP)を実行します。
def execute_00(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """NOP命令を実行します。何もしません。"""
    pass # NOPは何もしない

# @intent:responsibility オペコード0x76 (HALT)を実行します。
def execute_76(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """HALT命令を実行します。"""
    # TODO: CPUをHALT状態にするロジックを実装
    pass

# @intent:responsibility オペコード0x3E (LD A,n)を実行します。
def execute_3e(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """LD A,n命令を実行します。"""
    if not operation.operand_bytes:
        raise ValueError("LD A,n instruction requires an operand byte.")
    value_n = operation.operand_bytes[0]
    state.a = value_n

# @intent:responsibility オペコード0x21 (LD HL,nn)を実行します。
def execute_21(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """LD HL,nn命令を実行します。"""
    if not operation.operand_bytes or len(operation.operand_bytes) < 2:
        raise ValueError("LD HL,nn instruction requires two operand bytes.")
    nn_low = operation.operand_bytes[0]
    nn_high = operation.operand_bytes[1]
    value_nn = (nn_high << 8) | nn_low
    state.hl = value_nn


# @intent:responsibility オペコード0x77 (LD (HL),A)を実行します。
def execute_77(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """LD (HL),A命令を実行します。Aレジスタの値をHLレジスタが指すアドレスに書き込みます。"""
    bus.write(state.hl, state.a)

# @intent:responsibility オペコード0x7E (LD A,(HL))を実行します。
def execute_7e(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """LD A,(HL)命令を実行します。HLレジスタが指すアドレスから値を読み込み、Aレジスタに格納します。"""
    state.a = bus.read(state.hl)

# @intent:responsibility LD r,r'形式の命令を実行します。
def execute_ld_r_r_prime(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """汎用的なLD r,r' (Load Register to Register)命令を実行します。"""
    opcode = int(operation.opcode_hex, 16)
    dest_reg_code = (opcode >> 3) & 0b111
    src_reg_code = opcode & 0b111
    
    dest_reg_name = _get_register_name(dest_reg_code)
    src_reg_name = _get_register_name(src_reg_code)

    value = _get_register_value(state, bus, src_reg_name)
    _set_register_value(state, bus, dest_reg_name, value)

# @intent:responsibility ADD A,r形式の命令を実行します。
def execute_add_a_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """汎用的なADD A,r (Add Register to Accumulator)命令を実行します。"""
    opcode = int(operation.opcode_hex, 16)
    src_reg_code = opcode & 0b111
    src_reg_name = _get_register_name(src_reg_code)
    
    operand_value = _get_register_value(state, bus, src_reg_name)
    
    # Perform 8-bit addition
    result = state.a + operand_value
    
    # Update flags
    _set_sz_flags(state, result & 0xFF) # S, Z flags
    _set_pv_flag_parity(state, result & 0xFF) # PV flag (parity for now, will refine for overflow)
    state.flag_h = ((state.a & 0x0F) + (operand_value & 0x0F)) > 0x0F # Half-carry
    state.flag_n = False # N flag is reset for ADD
    state.flag_c = result > 0xFF # Carry flag
    
    state.a = result & 0xFF # Store 8-bit result in A


# Z80の主要な実行関数へのマッピング
# @intent:data_structure Z80のオペコードと実行関数をマッピングするテーブル。
EXECUTE_MAP = {
    # ADD A,r instructions (0x80 to 0x87)
    **{op: execute_add_a_r for op in range(0x80, 0x88)},
    # LD r,r' instructions (0x40 to 0x7F)
    # Filter out 0x76 (HALT)
    **{op: execute_ld_r_r_prime for op in range(0x40, 0x80) if op != 0x76},
    0x00: execute_00,
    0x76: execute_76, # HALT (overwrites generic if in range)
    0x3E: execute_3e,
    0x21: execute_21,
    0x77: execute_77, # LD (HL),A (overwrites generic if in range)
    0x7E: execute_7e, # LD A,(HL) (overwrites generic if in range)
}

# @intent:responsibility デコードされたZ80命令を実行し、CPUの状態を変更します。
# @intent:pre-condition `operation`は有効なOperationオブジェクトである必要があります。
def execute_instruction(operation: Operation, state: Z80CpuState, bus: Bus) -> None:
    """
    デコードされたZ80命令を実行し、CPUの状態を変更します。
    """
    executor = EXECUTE_MAP.get(int(operation.opcode_hex, 16)) # オペコードHEXをintに変換
    if executor:
        executor(state, bus, operation)
    else:
        # 未知のオペコードの場合、何もしない（既にUNKNOWNとしてデコード済みのため）
        pass
