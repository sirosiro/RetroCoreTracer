# src/retro_core_tracer/arch/mos6502/instructions/base.py
"""
MOS 6502 アドレッシングモード解決ロジック。
"""
from typing import Tuple, List
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState

# @intent:responsibility アドレッシングモードの解決結果（アドレス、追加サイクル、オペランド文字列、バイト列）を返す型。
# address: 解決された実効アドレス (Immediateの場合はNone)
# value: Immediateの場合の値、それ以外はNone
# extra_cycles: ページ境界交差などによる追加サイクル数
# operand_str: 逆アセンブリ用のオペランド文字列表現
# operand_bytes: オペランドとしてフェッチされたバイト列
AddressingResult = Tuple[int, int, int, str, List[int]]

# @intent:responsibility ページ境界交差判定。
def is_page_crossed(addr1: int, addr2: int) -> bool:
    return (addr1 & 0xFF00) != (addr2 & 0xFF00)

# --- Addressing Modes ---

# @intent:responsibility Implied / Accumulator Mode
def addr_implied(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    return None, None, 0, "", []

# @intent:responsibility Immediate Mode (#$xx)
def addr_immediate(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    val = bus.read(pc + 1)
    return None, val, 0, f"#${val:02X}", [val]

# @intent:responsibility Zero Page Mode ($xx)
def addr_zeropage(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    addr = bus.read(pc + 1)
    return addr, None, 0, f"${addr:02X}", [addr]

# @intent:responsibility Zero Page, X Mode ($xx,X)
# @intent:note ラップアラウンドあり (0xFF + 1 -> 0x00)
def addr_zeropage_x(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    base = bus.read(pc + 1)
    addr = (base + state.x) & 0xFF
    return addr, None, 0, f"${base:02X},X", [base]

# @intent:responsibility Zero Page, Y Mode ($xx,Y) - LDX, STX only
# @intent:note ラップアラウンドあり
def addr_zeropage_y(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    base = bus.read(pc + 1)
    addr = (base + state.y) & 0xFF
    return addr, None, 0, f"${base:02X},Y", [base]

# @intent:responsibility Absolute Mode ($xxxx)
def addr_absolute(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    lo = bus.read(pc + 1)
    hi = bus.read(pc + 2)
    addr = (hi << 8) | lo
    return addr, None, 0, f"${addr:04X}", [lo, hi]

# @intent:responsibility Absolute, X Mode ($xxxx,X)
def addr_absolute_x(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    lo = bus.read(pc + 1)
    hi = bus.read(pc + 2)
    base_addr = (hi << 8) | lo
    addr = (base_addr + state.x) & 0xFFFF
    
    # Page boundary check (STA等は例外だが、それは命令側で制御するか、ここでは一般的なRead用サイクルを返す)
    # 多くの命令で、ページクロス時に+1サイクル。Write命令(STA等)は常に+1サイクル等のケースがあるが、
    # ここでは「交差したか」のみを返し、命令側でサイクルの扱いを決定する方が柔軟かもしれない。
    # いったん標準的な「交差したら+1」を返す。
    extra = 1 if is_page_crossed(base_addr, addr) else 0
    
    return addr, None, extra, f"${base_addr:04X},X", [lo, hi]

# @intent:responsibility Absolute, Y Mode ($xxxx,Y)
def addr_absolute_y(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    lo = bus.read(pc + 1)
    hi = bus.read(pc + 2)
    base_addr = (hi << 8) | lo
    addr = (base_addr + state.y) & 0xFFFF
    extra = 1 if is_page_crossed(base_addr, addr) else 0
    return addr, None, extra, f"${base_addr:04X},Y", [lo, hi]

# @intent:responsibility Indirect Mode ($xxxx) - JMP only
# @intent:note JMPバグの実装が必要だが、それはJMP命令の実装側で行うか？
# ここでは標準的なIndirect解決を行う。
def addr_indirect(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    ptr_lo = bus.read(pc + 1)
    ptr_hi = bus.read(pc + 2)
    ptr = (ptr_hi << 8) | ptr_lo
    
    # JMPバグ再現ロジックは命令実行側で持つべき（アドレス解決ロジックとしては正常系を返す）
    # ただし、JMP命令自体がこのモードを使う唯一の命令であるため、ここでバグを実装しても良い。
    # マニフェスト原則に従い、バグ再現を含める。
    
    eff_lo = bus.read(ptr)
    
    # ページ境界バグ: ptrが$xxFFの場合、次は$xx00から読む
    if (ptr & 0xFF) == 0xFF:
        eff_hi = bus.read(ptr & 0xFF00)
    else:
        eff_hi = bus.read(ptr + 1)
        
    addr = (eff_hi << 8) | eff_lo
    return addr, None, 0, f"(${ptr:04X})", [ptr_lo, ptr_hi]

# @intent:responsibility Indexed Indirect Mode ($xx,X) - "Pre-indexed"
# @intent:note ゼロページ内でXを加算(ラップアラウンド)し、そこにあるポインタを読む。
def addr_indexed_indirect(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    base = bus.read(pc + 1)
    ptr_addr = (base + state.x) & 0xFF # Zero page wrap
    
    lo = bus.read(ptr_addr)
    hi = bus.read((ptr_addr + 1) & 0xFF) # Zero page wrap for pointer high byte
    
    addr = (hi << 8) | lo
    return addr, None, 0, f"(${base:02X},X)", [base]

# @intent:responsibility Indirect Indexed Mode ($xx),Y - "Post-indexed"
# @intent:note ゼロページのポインタを読み、ベースアドレスを得てからYを加算。
def addr_indirect_indexed(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    ptr_addr = bus.read(pc + 1)
    
    lo = bus.read(ptr_addr)
    hi = bus.read((ptr_addr + 1) & 0xFF) # Zero page wrap
    base_addr = (hi << 8) | lo
    
    addr = (base_addr + state.y) & 0xFFFF
    extra = 1 if is_page_crossed(base_addr, addr) else 0
    
    return addr, None, extra, f"(${ptr_addr:02X}),Y", [ptr_addr]

# @intent:responsibility Relative Mode (Branch)
# @intent:note 戻り値のアドレスは「ジャンプ先の絶対アドレス」とする。
def addr_relative(pc: int, bus: Bus, state: Mos6502CpuState) -> AddressingResult:
    offset = bus.read(pc + 1)
    # 符号付き8bitとして解釈
    if offset >= 0x80:
        offset -= 0x100
    
    # 分岐先アドレス計算: PC + 2 (命令長) + offset
    dest_addr = (pc + 2 + offset) & 0xFFFF
    
    # ページクロス判定は分岐成立時に行われるため、ここでは情報として持たせるか？
    # 分岐命令の実装側で「分岐元のPCページ」と「分岐先のPCページ」を比較してサイクル加算する。
    # ここではextra_cyclesは0とする。
    
    return dest_addr, None, 0, f"${dest_addr:04X}", [offset & 0xFF]
