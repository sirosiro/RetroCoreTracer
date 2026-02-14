# src/retro_core_tracer/arch/mos6502/instructions/control.py
"""
MOS 6502 制御系命令 (Branch, Jump, Stack, Flags, NOP)。
"""
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState
from retro_core_tracer.arch.mos6502.instructions.base import AddressingResult, is_page_crossed

# --- Branch Instructions ---

def _branch(state: Mos6502CpuState, addr_res: AddressingResult, condition: bool) -> Mos6502CpuState:
    target_addr, _, _, _, _ = addr_res
    
    if condition:
        # サイクル計算用のメタデータ更新が必要だが、現在のアーキテクチャでは
        # Cpu.step() で Snapshot を作る際に cycle_count を見ているか？
        # Operationオブジェクトのcycle_countはデコード時に決定される静的なもの。
        # 動的なサイクル加算（分岐成立 +1, ページクロス +2）は、ここで待機するか、
        # あるいは Operation オブジェクトを修正して返す仕組みが必要。
        # しかし execute_instruction は State を返すのみ。
        # 現時点ではサイクル精度の完全なエミュレーション（動的待機）はスコープ外とし、
        # PCの更新のみを行う。
        return state.replace(pc=target_addr)
    else:
        return state # PCは自動的に次の命令へ進む（呼び出し元で処理済みのPCではなく、命令長分加算はAbstractCpuが行う... 
        # 待て、AbstractCpu.step() は _update_pc() を呼ぶ。デフォルトは operation.length 加算。
        # 分岐命令の場合、分岐成立なら PC を書き換える。
        # 不成立なら書き換えない（デフォルトの加算が有効になる）。
        # しかし、addr_resのtarget_addrは「分岐先」の絶対アドレス。
        # 相対アドレス解決済み。

# @intent:note 分岐命令の実装について
# AbstractCpu.step() のフロー:
# 1. Fetch
# 2. Decode -> Operation (length=2)
# 3. Update PC (PC += 2)
# 4. Execute -> ここで PC を書き換えると、それが次の Fetch アドレスになる。
# つまり、不成立時は何もしなくて良い（PC+=2 済み）。
# 成立時は PC = target_addr とする。

def bcc(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, not state.flag_c)

def bcs(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, state.flag_c)

def beq(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, state.flag_z)

def bne(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, not state.flag_z)

def bmi(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, state.flag_n)

def bpl(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, not state.flag_n)

def bvc(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, not state.flag_v)

def bvs(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return _branch(state, addr_res, state.flag_v)

# --- Jump Instructions ---

def jmp(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    return state.replace(pc=addr)

def jsr(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    addr, _, _, _, _ = addr_res
    
    # Push PC + 2 (return address minus one)
    # 現在のPCは、AbstractCpuによって既に「次の命令の先頭」に進められているか？
    # AbstractCpu.step(): decode -> update_pc (PC+=3) -> execute
    # JSRは3バイト命令。PCは既にJSRの次の命令を指している。
    # しかし6502の仕様では、スタックに積むのは「JSR命令の最後のバイトのアドレス」。
    # つまり、現在のPC - 1。
    
    # 待て、AbstractCpuの仕様確認。
    # _update_pc はデフォルトで operation.length 加算。
    # JSR実行時点での state.pc は「次の命令のアドレス」。
    # 戻りアドレスは PC - 1。
    
    ret_addr = state.pc - 1
    hi = (ret_addr >> 8) & 0xFF
    lo = ret_addr & 0xFF
    
    sp = state.sp
    # Push Hi, then Lo
    bus.write(0x0100 | sp, hi)
    sp = (sp - 1) & 0xFF
    bus.write(0x0100 | sp, lo)
    sp = (sp - 1) & 0xFF
    
    return state.replace(sp=sp, pc=addr)

def rts(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    sp = state.sp
    
    # Pull Lo, then Hi
    sp = (sp + 1) & 0xFF
    lo = bus.read(0x0100 | sp)
    sp = (sp + 1) & 0xFF
    hi = bus.read(0x0100 | sp)
    
    # Return address pulled is "last byte of JSR". So we need to add 1 to get next opcode.
    ret_addr = ((hi << 8) | lo) + 1
    
    return state.replace(sp=sp, pc=ret_addr)

# --- Stack Operations (PHA, PHP, PLA, PLP) ---

def pha(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    sp = state.sp
    bus.write(0x0100 | sp, state.a)
    return state.replace(sp=(sp - 1) & 0xFF)

def php(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    sp = state.sp
    # PHP pushes status with Break(B) and Reserved(R) flags set to 1.
    p_val = state.p | state.B_FLAG | state.R_FLAG
    bus.write(0x0100 | sp, p_val)
    return state.replace(sp=(sp - 1) & 0xFF)

def pla(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    sp = (state.sp + 1) & 0xFF
    val = bus.read(0x0100 | sp)
    new_state = state.replace(sp=sp, a=val)
    return new_state.update_flags(n=(val&0x80)!=0, z=(val==0))

def plp(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    sp = (state.sp + 1) & 0xFF
    val = bus.read(0x0100 | sp)
    # Ignore B flag from stack, and keep Reserved bit set?
    # Usually B flag is discarded, R is ignored.
    # state.p update logic handles this if we just replace p?
    # B flag in register doesn't physically exist, it's only on stack.
    # So we should mask out B? Or just let it be 0.
    # Mask: Keep bit 5 (R) as 1, bit 4 (B) depends on implementation but usually 0 in register.
    new_p = (val & ~state.B_FLAG) | state.R_FLAG
    return state.replace(sp=sp, p=new_p)

# --- Flag Operations (CLC, SEC, etc) ---

def clc(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(c=False)

def sec(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(c=True)

def cli(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(i=False)

def sei(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(i=True)

def clv(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(v=False)

def cld(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(d=False)

def sed(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state.update_flags(d=True)

# --- System / Other ---

def nop(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    return state

def brk(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    # BRK is a software interrupt.
    # PC + 2 is pushed (BRK is 1 byte, but padding byte is skipped)
    # Actually BRK is 2 byte instruction effectively? No, it's 1 byte, but return addr is PC+2.
    # AbstractCpu has updated PC by 1. We need PC+1 more.
    
    ret_addr = state.pc + 1 
    hi = (ret_addr >> 8) & 0xFF
    lo = ret_addr & 0xFF
    
    sp = state.sp
    bus.write(0x0100 | sp, hi)
    sp = (sp - 1) & 0xFF
    bus.write(0x0100 | sp, lo)
    sp = (sp - 1) & 0xFF
    
    # Push P with B flag set
    p_val = state.p | state.B_FLAG | state.R_FLAG
    bus.write(0x0100 | sp, p_val)
    sp = (sp - 1) & 0xFF
    
    # Set I flag
    new_state = state.update_flags(i=True)
    
    # Jump to IRQ/BRK vector ($FFFE)
    vec_lo = bus.read(0xFFFE)
    vec_hi = bus.read(0xFFFF)
    target = (vec_hi << 8) | vec_lo
    
    return new_state.replace(sp=sp, pc=target)

def rti(state: Mos6502CpuState, bus: Bus, addr_res: AddressingResult) -> Mos6502CpuState:
    sp = (state.sp + 1) & 0xFF
    p_val = bus.read(0x0100 | sp)
    new_p = (p_val & ~state.B_FLAG) | state.R_FLAG
    
    sp = (sp + 1) & 0xFF
    lo = bus.read(0x0100 | sp)
    sp = (sp + 1) & 0xFF
    hi = bus.read(0x0100 | sp)
    
    ret_addr = (hi << 8) | lo
    
    return state.replace(sp=sp, p=new_p, pc=ret_addr)
