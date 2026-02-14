# src/retro_core_tracer/arch/mos6502/instructions/load.py
"""
MOS 6502 転送系命令 (Load/Store/Transfer)。
"""
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState
from retro_core_tracer.arch.mos6502.instructions.base import AddressingResult

# @intent:responsibility フラグ更新ヘルパー (N, Z)
def update_nz(state: Mos6502CpuState, value: int) -> Mos6502CpuState:
    return state.update_flags(n=(value & 0x80) != 0, z=(value == 0))

# --- LDA (Load Accumulator) ---
# @intent:responsibility メモリからAレジスタへロードし、N, Zフラグを更新。
def lda(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    if val is None: # Not Immediate
        val = bus.read(addr)
    
    new_state = state.replace(a=val)
    return update_nz(new_state, val)

# --- LDX (Load X Register) ---
def ldx(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    if val is None:
        val = bus.read(addr)
    new_state = state.replace(x=val)
    return update_nz(new_state, val)

# --- LDY (Load Y Register) ---
def ldy(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, val, _, _, _ = addr_res
    if val is None:
        val = bus.read(addr)
    new_state = state.replace(y=val)
    return update_nz(new_state, val)

# --- STA (Store Accumulator) ---
# @intent:responsibility Aレジスタの内容をメモリへストア。フラグ変化なし。
def sta(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    bus.write(addr, state.a)
    return state

# --- STX (Store X Register) ---
def stx(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    bus.write(addr, state.x)
    return state

# --- STY (Store Y Register) ---
def sty(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    bus.write(addr, state.y)
    return state

# --- Register Transfers (TAX, TAY, TXA, TYA, TSX, TXS) ---

def tax(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    val = state.a
    new_state = state.replace(x=val)
    return update_nz(new_state, val)

def tay(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    val = state.a
    new_state = state.replace(y=val)
    return update_nz(new_state, val)

def txa(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    val = state.x
    new_state = state.replace(a=val)
    return update_nz(new_state, val)

def tya(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    val = state.y
    new_state = state.replace(a=val)
    return update_nz(new_state, val)

# @intent:note TSXはSPからXへ転送。SPは8ビット値として扱う。N, Z更新あり。
def tsx(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    val = state.sp
    new_state = state.replace(x=val)
    return update_nz(new_state, val)

# @intent:note TXSはXからSPへ転送。N, Zフラグは更新 *されない* という特異な挙動がある。
def txs(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    val = state.x
    return state.replace(sp=val)
