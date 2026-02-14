"""
Z80 命令マッピング定義。
各命令モジュールから関数をインポートし、オペコードと関数の対応表を構築します。
"""
from .alu import (
    decode_add_hl_ss, decode_arith_r, decode_logic_r, decode_inc_dec8, decode_add_a_r, decode_fe,
    execute_add_hl_ss, execute_arith_r, execute_logic_r, execute_inc_dec8, execute_add_a_r, execute_fe
)
from .load import (
    decode_push_pop, decode_ld_ss_nn, decode_ld_r_n, decode_ld_r_r_prime, decode_ix_iy, decode_ed,
    decode_ld_a_nn, decode_ld_nn_a,
    execute_push_pop, execute_ld_ss_nn, execute_ld_r_n, execute_ld_r_r_prime, execute_ld_ix_iy_nn,
    execute_add_ix_iy_ss, execute_inc_ix_iy, execute_ex_sp_ix_iy, execute_ld_r_ix_iy_d, execute_ld_ix_iy_d_r,
    execute_ed, execute_ld_a_nn, execute_ld_nn_a
)
from .control import (
    decode_cd, decode_c9, decode_00, decode_76, decode_c3, decode_18, decode_10, decode_jr_cc_e,
    decode_cb, decode_fb, decode_f3, decode_08, decode_eb, decode_d9, decode_e3, decode_db, decode_d3,
    execute_cd, execute_c9, execute_00, execute_76, execute_c3, execute_18, execute_10, execute_jr_cc_e,
    execute_cb, execute_fb, execute_f3, execute_08, execute_eb, execute_d9, execute_e3, execute_db, execute_d3
)

DECODE_MAP = {
    0x00: decode_00,
    0x08: decode_08,
    0x10: decode_10,
    0x3A: decode_ld_a_nn,
    0x32: decode_ld_nn_a,
    0x76: decode_76,
    0xCB: decode_cb,
    0xDD: decode_ix_iy,
    0xED: decode_ed,
    0xFD: decode_ix_iy,
    0xC3: decode_c3,
    0xC9: decode_c9,
    0xCD: decode_cd,
    0xDB: decode_db,
    0xD3: decode_d3,
    0xD9: decode_d9,
    0xE3: decode_e3,
    0xEB: decode_eb,
    0xF3: decode_f3,
    0xFB: decode_fb,
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
    0x08: execute_08,
    0x10: execute_10,
    0x3A: execute_ld_a_nn,
    0x32: execute_ld_nn_a,
    0x76: execute_76,
    0xCB: execute_cb,
    0xED: execute_ed,
    0xC3: execute_c3,
    0xC9: execute_c9,
    0xCD: execute_cd,
    0xDB: execute_db,
    0xD3: execute_d3,
    0xD9: execute_d9,
    0xE3: execute_e3,
    0xEB: execute_eb,
    0xF3: execute_f3,
    0xFB: execute_fb,
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
    # IX/IY Instructions
    **{(0xDD00 | op): execute_ld_r_ix_iy_d for op in range(0x40, 0x70) if (op & 0xC7) == 0x46},
    **{(0xDD00 | op): execute_ld_r_ix_iy_d for op in [0x7E]},
    **{(0xDD00 | op): execute_ld_ix_iy_d_r for op in range(0x70, 0x78) if op != 0x76},
    0xDD21: execute_ld_ix_iy_nn,
    0xDD23: execute_inc_ix_iy,
    0xDDE3: execute_ex_sp_ix_iy,
    **{(0xDD00 | op): execute_add_ix_iy_ss for op in range(0x09, 0x40, 0x10)},
    
    **{(0xFD00 | op): execute_ld_r_ix_iy_d for op in range(0x40, 0x70) if (op & 0xC7) == 0x46},
    **{(0xFD00 | op): execute_ld_r_ix_iy_d for op in [0x7E]},
    **{(0xFD00 | op): execute_ld_ix_iy_d_r for op in range(0x70, 0x78) if op != 0x76},
    0xFD21: execute_ld_ix_iy_nn,
    0xFD23: execute_inc_ix_iy,
    0xFDE3: execute_ex_sp_ix_iy,
    **{(0xFD00 | op): execute_add_ix_iy_ss for op in range(0x09, 0x40, 0x10)},
}