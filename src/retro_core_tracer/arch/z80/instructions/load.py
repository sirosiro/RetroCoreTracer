"""
Z80 データ転送命令の実装。
"""
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Operation
from .base import (
    get_register_name, get_register_value, set_register_value,
    get_push_pop_reg_name, get_ss_reg_name
)
from retro_core_tracer.arch.z80.alu import update_flags_add16

# --- Decoding Functions ---

def decode_push_pop(opcode: int, bus: Bus, pc: int) -> Operation:
    """PUSH/POP命令をデコードします。"""
    reg_code = (opcode >> 4) & 0b11
    reg_name = get_push_pop_reg_name(reg_code)
    is_push = (opcode & 0x0F) == 0x05
    mnemonic = f"{'PUSH' if is_push else 'POP'} {reg_name}"
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=mnemonic,
        operands=[],
        cycle_count=11 if is_push else 10,
        length=1
    )

# @intent:responsibility LD ss,nn 形式の命令をデコードします。
def decode_ld_ss_nn(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD ss,nn命令をデコードします。"""
    ss_code = (opcode >> 4) & 0b11
    ss_name = get_ss_reg_name(ss_code)
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
    reg_name = get_register_name(reg_code)
    operand_n = bus.read(pc + 1)
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"LD {reg_name},n",
        operands=[f"${operand_n:02X}"],
        cycle_count=7 if reg_name != "(HL)" else 10,
        length=2,
        operand_bytes=[operand_n]
    )

# @intent:responsibility LD r,r'形式の命令をデコードします。
def decode_ld_r_r_prime(opcode: int, bus: Bus, pc: int) -> Operation:
    """汎用的なLD r,r'命令をデコードします。"""
    dest_reg_code = (opcode >> 3) & 0b111
    src_reg_code = opcode & 0b111
    dest_reg_name = get_register_name(dest_reg_code)
    src_reg_name = get_register_name(src_reg_code)
    return Operation(
        opcode_hex=f"{opcode:02X}",
        mnemonic=f"LD {dest_reg_name},{src_reg_name}",
        operands=[],
        cycle_count=4 if "(HL)" not in [dest_reg_name, src_reg_name] else 7,
        length=1
    )

def decode_ld_a_nn(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD A,(nn) 命令をデコードします。"""
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex="3A",
        mnemonic="LD A,(nn)",
        operands=[f"(${nn:04X})"],
        cycle_count=13,
        length=3,
        operand_bytes=[nn_low, nn_high]
    )

def decode_ld_nn_a(opcode: int, bus: Bus, pc: int) -> Operation:
    """LD (nn),A 命令をデコードします。"""
    nn_low = bus.read(pc + 1)
    nn_high = bus.read(pc + 2)
    nn = (nn_high << 8) | nn_low
    return Operation(
        opcode_hex="32",
        mnemonic="LD (nn),A",
        operands=[f"(${nn:04X})"],
        cycle_count=13,
        length=3,
        operand_bytes=[nn_low, nn_high]
    )

# @intent:responsibility オペコード0xDD / 0xFD (IX/IY プレフィックス) をデコードします。
def decode_ix_iy(opcode: int, bus: Bus, pc: int) -> Operation:
    """IX/IY プレフィックス命令をデコードします。"""
    prefix = opcode
    reg_name = "IX" if prefix == 0xDD else "IY"
    next_opcode = bus.read(pc + 1)
    
    # 0x21: LD IX/IY, nn
    if next_opcode == 0x21:
        nn_low = bus.read(pc + 2)
        nn_high = bus.read(pc + 3)
        nn = (nn_high << 8) | nn_low
        return Operation(
            opcode_hex=f"{prefix:02X}21",
            mnemonic=f"LD {reg_name},nn",
            operands=[f"${nn:04X}"],
            cycle_count=14,
            length=4,
            operand_bytes=[nn_low, nn_high]
        )
    
    # 0x09, 0x19, 0x29, 0x39: ADD IX/IY, ss
    if (next_opcode & 0xCF) == 0x09:
        ss_code = (next_opcode >> 4) & 0b11
        ss_name = get_ss_reg_name(ss_code)
        if ss_name == "HL": ss_name = reg_name
        return Operation(
            opcode_hex=f"{prefix:02X}{next_opcode:02X}",
            mnemonic=f"ADD {reg_name},{ss_name}",
            operands=[],
            cycle_count=15,
            length=2
        )

    # 0x23: INC IX/IY
    if next_opcode == 0x23:
        return Operation(
            opcode_hex=f"{prefix:02X}23",
            mnemonic=f"INC {reg_name}",
            operands=[],
            cycle_count=10,
            length=2
        )

    # 0xE3: EX (SP), IX/IY
    if next_opcode == 0xE3:
        return Operation(
            opcode_hex=f"{prefix:02X}E3",
            mnemonic=f"EX (SP),{reg_name}",
            operands=[],
            cycle_count=23,
            length=2
        )

    # (IX+d) 系の命令 (一部のみ実装)
    # LD r, (IX+d) -> 0xDD 0x46, 0x4E, 0x56, 0x5E, 0x66, 0x6E, 0x7E
    if (next_opcode & 0xC7) == 0x46 and next_opcode != 0x76:
        dest_reg_code = (next_opcode >> 3) & 0b111
        dest_reg_name = get_register_name(dest_reg_code)
        d = bus.read(pc + 2)
        return Operation(
            opcode_hex=f"{prefix:02X}{next_opcode:02X}",
            mnemonic=f"LD {dest_reg_name},({reg_name}+{d:02X}H)",
            operands=[],
            cycle_count=19,
            length=3,
            operand_bytes=[d]
        )
    
    # LD (IX+d), r -> 0xDD 0x70-0x77 (except 0x76)
    if (next_opcode & 0xF8) == 0x70 and next_opcode != 0x76:
        src_reg_code = next_opcode & 0b111
        src_reg_name = get_register_name(src_reg_code)
        d = bus.read(pc + 2)
        return Operation(
            opcode_hex=f"{prefix:02X}{next_opcode:02X}",
            mnemonic=f"LD ({reg_name}+{d:02X}H),{src_reg_name}",
            operands=[],
            cycle_count=19,
            length=3,
            operand_bytes=[d]
        )

    return Operation(opcode_hex=f"{prefix:02X}", mnemonic=f"{reg_name} prefix", operands=[], cycle_count=4, length=1)

# @intent:responsibility 0xED プレフィックス命令（ブロック転送、拡張命令）をデコードします。
def decode_ed(opcode: int, bus: Bus, pc: int) -> Operation:
    """EDプレフィックス命令をデコードします。"""
    ed_opcode = bus.read(pc + 1)
    
    # ブロック転送命令
    if ed_opcode == 0xA0: mnemonic = "LDI"
    elif ed_opcode == 0xB0: mnemonic = "LDIR"
    elif ed_opcode == 0xA8: mnemonic = "LDD"
    elif ed_opcode == 0xB8: mnemonic = "LDDR"
    # 割り込み関連
    elif ed_opcode == 0x46: mnemonic = "IM 0"
    elif ed_opcode == 0x56: mnemonic = "IM 1"
    elif ed_opcode == 0x5E: mnemonic = "IM 2"
    elif ed_opcode == 0x4D: mnemonic = "RETI"
    elif ed_opcode == 0x45: mnemonic = "RETN"
    else: mnemonic = f"ED {ed_opcode:02X}"

    # サイクル数
    if mnemonic in ["LDIR", "LDDR"]: cycles = 21
    elif mnemonic in ["RETI", "RETN"]: cycles = 14
    elif mnemonic.startswith("IM "): cycles = 8
    else: cycles = 16

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
            
    # Note: IM and RETI/RETN are handled in control.py or here?
    # Ideally control instructions should be in control.py, but execute_ed dispatches them.
    # We will keep them here for now to avoid circular imports or complex dispatching,
    # or better, import execute functions from control.py inside execute_ed.
    # For this refactoring, we'll keep execute_ed as the dispatcher.
    from .control import execute_im, execute_reti_retn
    if ed_opcode in [0x46, 0x56, 0x5E]:
        execute_im(state, bus, operation)
    elif ed_opcode in [0x4D, 0x45]:
        execute_reti_retn(state, bus, operation)

def execute_push_pop(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    reg_code = (opcode >> 4) & 0b11
    reg_name = get_push_pop_reg_name(reg_code).lower()
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

def execute_ld_ss_nn(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    ss_code = (opcode >> 4) & 0b11
    ss_name = get_ss_reg_name(ss_code).lower()
    nn_low, nn_high = operation.operand_bytes
    value = (nn_high << 8) | nn_low
    setattr(state, ss_name, value)

def execute_ld_r_n(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    reg_name = get_register_name((opcode >> 3) & 0b111)
    value = operation.operand_bytes[0]
    set_register_value(state, bus, reg_name, value)

def execute_ld_r_r_prime(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    opcode = int(operation.opcode_hex, 16)
    dest_name = get_register_name((opcode >> 3) & 0b111)
    src_name = get_register_name(opcode & 0b111)
    val = get_register_value(state, bus, src_name)
    set_register_value(state, bus, dest_name, val)

def execute_ld_a_nn(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """LD A,(nn)を実行します。"""
    nn_low, nn_high = operation.operand_bytes
    addr = (nn_high << 8) | nn_low
    val = bus.read(addr)
    state.a = val

def execute_ld_nn_a(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    """LD (nn),Aを実行します。"""
    nn_low, nn_high = operation.operand_bytes
    addr = (nn_high << 8) | nn_low
    bus.write(addr, state.a)

def execute_ld_ix_iy_nn(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    prefix = int(operation.opcode_hex[:2], 16)
    nn_low, nn_high = operation.operand_bytes
    val = (nn_high << 8) | nn_low
    if prefix == 0xDD: state.ix = val
    else: state.iy = val

def execute_add_ix_iy_ss(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    prefix = int(operation.opcode_hex[:2], 16)
    next_opcode = int(operation.opcode_hex[2:], 16)
    ss_code = (next_opcode >> 4) & 0b11
    ss_name = get_ss_reg_name(ss_code).lower()
    
    base_val = state.ix if prefix == 0xDD else state.iy
    
    if ss_name == "hl": # ADD IX, IX / ADD IY, IY
        add_val = base_val
    else:
        add_val = getattr(state, ss_name)
    
    result = base_val + add_val
    # 16ビット加算のフラグ更新 (ADD HL,ssと同様だがHLをbase_valに読み替える)
    update_flags_add16(state, base_val, add_val, result)
    
    if prefix == 0xDD: state.ix = result & 0xFFFF
    else: state.iy = result & 0xFFFF

def execute_inc_ix_iy(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    prefix = int(operation.opcode_hex[:2], 16)
    if prefix == 0xDD: state.ix = (state.ix + 1) & 0xFFFF
    else: state.iy = (state.iy + 1) & 0xFFFF

def execute_ex_sp_ix_iy(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    prefix = int(operation.opcode_hex[:2], 16)
    # Low byte
    low = bus.read(state.sp)
    if prefix == 0xDD:
        bus.write(state.sp, state.ix & 0xFF)
        state.ix = (state.ix & 0xFF00) | low
    else:
        bus.write(state.sp, state.iy & 0xFF)
        state.iy = (state.iy & 0xFF00) | low
    # High byte
    high = bus.read(state.sp + 1)
    if prefix == 0xDD:
        bus.write(state.sp + 1, (state.ix >> 8) & 0xFF)
        state.ix = (state.ix & 0x00FF) | (high << 8)
    else:
        bus.write(state.sp + 1, (state.iy >> 8) & 0xFF)
        state.iy = (state.iy & 0x00FF) | (high << 8)

def execute_ld_r_ix_iy_d(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    prefix = int(operation.opcode_hex[:2], 16)
    next_opcode = int(operation.opcode_hex[2:], 16)
    dest_reg_code = (next_opcode >> 3) & 0b111
    dest_reg_name = get_register_name(dest_reg_code)
    d = operation.operand_bytes[0]
    if d >= 128: d -= 256
    
    base_val = state.ix if prefix == 0xDD else state.iy
    addr = (base_val + d) & 0xFFFF
    val = bus.read(addr)
    set_register_value(state, bus, dest_reg_name, val)

def execute_ld_ix_iy_d_r(state: Z80CpuState, bus: Bus, operation: Operation) -> None:
    prefix = int(operation.opcode_hex[:2], 16)
    next_opcode = int(operation.opcode_hex[2:], 16)
    src_reg_code = next_opcode & 0b111
    src_reg_name = get_register_name(src_reg_code)
    d = operation.operand_bytes[0]
    if d >= 128: d -= 256
    
    base_val = state.ix if prefix == 0xDD else state.iy
    addr = (base_val + d) & 0xFFFF
    val = get_register_value(state, bus, src_reg_name)
    bus.write(addr, val)