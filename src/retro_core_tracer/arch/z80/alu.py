"""
Z80 ALU (算術論理演算ユニット) およびフラグ操作ユーティリティ。

演算結果に基づいた正確なフラグ（S, Z, H, P/V, N, C）の計算と更新を担当します。
"""
from retro_core_tracer.arch.z80.state import Z80CpuState

# @intent:responsibility 指定されたバイト値のパリティ（ビット1の数が偶数ならTrue）を計算します。
def calculate_parity(val: int) -> bool:
    """8ビット値のパリティ（偶数ならTrue）を計算します。"""
    val ^= val >> 4
    val ^= val >> 2
    val ^= val >> 1
    return (val & 1) == 0

# @intent:responsibility 8ビット加算の結果に基づいて全フラグを更新します。
def update_flags_add8(state: Z80CpuState, val1: int, val2: int, result: int, carry_in: int = 0) -> None:
    """ADD/ADC命令のフラグを更新します。"""
    res8 = result & 0xFF
    
    state.flag_s = (res8 & 0x80) != 0
    state.flag_z = res8 == 0
    # Half Carry: (val1 & 0x0F) + (val2 & 0x0F) + carry_in > 0x0F
    state.flag_h = ((val1 & 0x0F) + (val2 & 0x0F) + carry_in) > 0x0F
    
    # Overflow: 同符号の加算で結果の符号が変わった場合
    # (val1 ^ result) & (val2 ^ result) & 0x80
    state.flag_pv = ((val1 ^ res8) & (val2 ^ res8) & 0x80) != 0
    
    state.flag_n = False
    state.flag_c = result > 0xFF

# @intent:responsibility 8ビット減算の結果に基づいて全フラグを更新します。
def update_flags_sub8(state: Z80CpuState, val1: int, val2: int, result: int, borrow_in: int = 0) -> None:
    """SUB/SBC/CP命令のフラグを更新します。"""
    res8 = result & 0xFF
    
    state.flag_s = (res8 & 0x80) != 0
    state.flag_z = res8 == 0
    # Half Carry (Borrow): (val1 & 0x0F) - (val2 & 0x0F) - borrow_in < 0
    state.flag_h = ((val1 & 0x0F) - (val2 & 0x0F) - borrow_in) < 0
    
    # Overflow: 異符号の減算で結果の符号が第一オペランドと異なる場合
    # (val1 ^ val2) & (val1 ^ result) & 0x80
    state.flag_pv = ((val1 ^ val2) & (val1 ^ res8) & 0x80) != 0
    
    state.flag_n = True
    state.flag_c = result < 0

# @intent:responsibility 8ビット論理演算の結果に基づいてフラグを更新します。
def update_flags_logic8(state: Z80CpuState, result: int, h_flag: bool = False) -> None:
    """AND/OR/XOR命令のフラグを更新します。"""
    res8 = result & 0xFF
    
    state.flag_s = (res8 & 0x80) != 0
    state.flag_z = res8 == 0
    state.flag_h = h_flag # ANDならTrue, OR/XORならFalse
    state.flag_pv = calculate_parity(res8)
    state.flag_n = False
    state.flag_c = False

# @intent:responsibility インクリメント/デクリメント命令のフラグを更新します（Cフラグは変化しません）。
def update_flags_inc_dec8(state: Z80CpuState, val: int, result: int, is_inc: bool) -> None:
    """INC/DEC命令のフラグを更新します。Cフラグは保持されます。"""
    res8 = result & 0xFF
    
    state.flag_s = (res8 & 0x80) != 0
    state.flag_z = res8 == 0
    
    if is_inc:
        state.flag_h = (val & 0x0F) == 0x0F
        state.flag_pv = val == 0x7F # 127 -> -128
        state.flag_n = False
    else:
        state.flag_h = (val & 0x0F) == 0x00
        state.flag_pv = val == 0x80 # -128 -> 127
        state.flag_n = True

# @intent:responsibility 16ビット加算の結果に基づいてフラグ（H, N, C）を更新します。
# @intent:rationale Z, S, P/Vフラグは影響を受けないことに注意してください。
def update_flags_add16(state: Z80CpuState, val1: int, val2: int, result: int) -> None:
    """ADD HL,ss命令のフラグを更新します。"""
    # Half Carry: Bit 11から12へのキャリー
    state.flag_h = ((val1 & 0x0FFF) + (val2 & 0x0FFF)) > 0x0FFF
    state.flag_n = False
    state.flag_c = result > 0xFFFF
