# src/retro_core_tracer/arch/mos6502/instructions/alu.py
"""
MOS 6502 算術論理演算命令 (ALU)。
BCDサポートを含む。
"""
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState
from retro_core_tracer.arch.mos6502.instructions.base import AddressingResult

# @intent:responsibility N, Z フラグ更新ヘルパー
def update_nz(state: Mos6502CpuState, value: int) -> Mos6502CpuState:
    return state.update_flags(n=(value & 0x80) != 0, z=(value == 0))

# --- Logical Operations (AND, ORA, EOR, BIT) ---

def and_(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    
    res = state.a & val
    new_state = state.replace(a=res)
    return update_nz(new_state, res)

def ora(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    
    res = state.a | val
    new_state = state.replace(a=res)
    return update_nz(new_state, res)

def eor(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    
    res = state.a ^ val
    new_state = state.replace(a=res)
    return update_nz(new_state, res)

# @intent:note BIT命令はメモリの値のビット6, 7をそれぞれV, Nフラグにコピーし、A & Mの結果でZフラグを設定する。
def bit(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    
    z = (state.a & val) == 0
    v = (val & 0x40) != 0
    n = (val & 0x80) != 0
    
    return state.update_flags(z=z, v=v, n=n)

# --- Arithmetic Operations (ADC, SBC) ---

# @intent:responsibility BCD加算ロジック
def _adc_bcd(state: Mos6502CpuState, val: int) -> Mos6502CpuState:
    # Note: 6502 BCD implementation has quirks. This is a simplified logic aiming for standard behavior.
    # Flags N, V, Z are often invalid or behave differently in BCD mode on NMOS 6502.
    # CMOS 6502 fixes them. We will emulate the more predictable behavior or standard algorithm.
    # Here we implement a common emulation logic.
    
    a = state.a
    c = 1 if state.flag_c else 0
    
    lo = (a & 0x0F) + (val & 0x0F) + c
    hi = (a >> 4) + (val >> 4)
    
    if lo > 9:
        lo -= 10
        hi += 1
        
    if hi > 9:
        hi -= 10
        c_out = 1
    else:
        c_out = 0
        
    res = (hi << 4) | lo
    
    # Flags N, Z, V are technically undefined/invalid in NMOS 6502 decimal mode, 
    # but some emulators update them based on the binary result.
    # We will update them based on the binary result for transparency, or keep them useful?
    # Let's update N, Z based on result, C based on decimal carry.
    
    new_state = state.replace(a=res & 0xFF)
    return new_state.update_flags(c=bool(c_out), z=(res==0), n=(res & 0x80)!=0)

# @intent:responsibility 標準バイナリ加算ロジック
def _adc_binary(state: Mos6502CpuState, val: int) -> Mos6502CpuState:
    a = state.a
    c = 1 if state.flag_c else 0
    
    res_wide = a + val + c
    res = res_wide & 0xFF
    
    c_out = res_wide > 0xFF
    z = (res == 0)
    n = (res & 0x80) != 0
    # Overflow: (M^R) & (N^R) & 0x80 ? No, standard formula:
    # V is set if the sign of the result differs from the sign of both operands.
    # ~(A ^ val) & (A ^ res) & 0x80
    v = (~(a ^ val) & (a ^ res) & 0x80) != 0
    
    new_state = state.replace(a=res)
    return new_state.update_flags(c=c_out, z=z, n=n, v=v)

def adc(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    
    if state.flag_d:
        return _adc_bcd(state, val)
    else:
        return _adc_binary(state, val)

def sbc(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    
    # SBC is equivalent to ADC with the bitwise inverse of the value.
    # SBC A, M => ADC A, ~M
    # In Decimal mode, it's more complex (10's complement logic).
    
    if state.flag_d:
        # Simplified BCD SBC (Often emulated by converting to decimal, subtracting, converting back)
        # Or using the binary ADC logic with adjusted value? 
        # For simplicity/robustness, let's implement BCD subtraction logic directly.
        
        a = state.a
        c = 1 if state.flag_c else 0 # Borrow is !C
        
        # Calculate in decimal
        # Convert A and Val to int (0-99)
        def bcd_to_int(b): return (b >> 4) * 10 + (b & 0x0F)
        def int_to_bcd(i): return ((i // 10) << 4) | (i % 10)
        
        dec_a = bcd_to_int(a)
        dec_val = bcd_to_int(val)
        
        # SBC logic: A - M - (1-C)
        diff = dec_a - dec_val - (1 - c)
        
        if diff < 0:
            diff += 100
            c_out = 0 # Borrow occurred
        else:
            c_out = 1 # No borrow
            
        res = int_to_bcd(diff)
        
        new_state = state.replace(a=res)
        return new_state.update_flags(c=bool(c_out), z=(res==0), n=(res & 0x80)!=0)
    else:
        # Binary SBC: ADC (val ^ 0xFF)
        return _adc_binary(state, val ^ 0xFF)

# --- Compare Operations (CMP, CPX, CPY) ---
# @intent:note Compare is effectively subtraction without storing result.
# Updates N, Z, C. C is set if Reg >= Val (No borrow).

def _compare(state: Mos6502CpuState, reg_val: int, mem_val: int) -> Mos6502CpuState:
    diff = reg_val - mem_val
    c = diff >= 0
    res = diff & 0xFF
    z = (res == 0)
    n = (res & 0x80) != 0
    return state.update_flags(c=c, z=z, n=n)

def cmp(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    return _compare(state, state.a, val)

def cpx(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    return _compare(state, state.x, val)

def cpy(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    _, val, _, _, _ = addr_res
    if val is None: val = bus.read(addr_res[0])
    return _compare(state, state.y, val)

# --- Shift / Rotate Operations (ASL, LSR, ROL, ROR) ---
# @intent:note Accumulator mode or Memory mode.

def asl(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    is_acc = (addr is None) and (val is None) # Implied/Accumulator
    
    if is_acc:
        val = state.a
    elif val is None:
        val = bus.read(addr)
        
    c = (val & 0x80) != 0
    res = (val << 1) & 0xFF
    
    new_state = state.update_flags(c=c, z=(res==0), n=(res&0x80)!=0)
    
    if is_acc:
        return new_state.replace(a=res)
    else:
        bus.write(addr, res)
        return new_state

def lsr(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    is_acc = (addr is None) and (val is None)
    
    if is_acc:
        val = state.a
    elif val is None:
        val = bus.read(addr)
        
    c = (val & 0x01) != 0
    res = (val >> 1)
    
    new_state = state.update_flags(c=c, z=(res==0), n=False) # N is always 0 for LSR
    
    if is_acc:
        return new_state.replace(a=res)
    else:
        bus.write(addr, res)
        return new_state

def rol(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    is_acc = (addr is None) and (val is None)
    
    if is_acc:
        val = state.a
    elif val is None:
        val = bus.read(addr)
    
    old_c = 1 if state.flag_c else 0
    new_c = (val & 0x80) != 0
    res = ((val << 1) | old_c) & 0xFF
    
    new_state = state.update_flags(c=new_c, z=(res==0), n=(res&0x80)!=0)
    
    if is_acc:
        return new_state.replace(a=res)
    else:
        bus.write(addr, res)
        return new_state

def ror(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    is_acc = (addr is None) and (val is None)
    
    if is_acc:
        val = state.a
    elif val is None:
        val = bus.read(addr)
    
    old_c = 1 if state.flag_c else 0
    new_c = (val & 0x01) != 0
    res = (val >> 1) | (old_c << 7)
    
    new_state = state.update_flags(c=new_c, z=(res==0), n=(res&0x80)!=0)
    
    if is_acc:
        return new_state.replace(a=res)
    else:
        bus.write(addr, res)
        return new_state

# --- Increment / Decrement (INC, DEC, INX, DEX, INY, DEY) ---

def inc(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    val = bus.read(addr)
    res = (val + 1) & 0xFF
    bus.write(addr, res)
    return update_nz(state, res)

def dec(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    val = bus.read(addr)
    res = (val - 1) & 0xFF
    bus.write(addr, res)
    return update_nz(state, res)

def inx(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    res = (state.x + 1) & 0xFF
    return update_nz(state.replace(x=res), res)

def dex(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    res = (state.x - 1) & 0xFF
    return update_nz(state.replace(x=res), res)

def iny(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    res = (state.y + 1) & 0xFF
    return update_nz(state.replace(y=res), res)

def dey(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    res = (state.y - 1) & 0xFF
    return update_nz(state.replace(y=res), res)
