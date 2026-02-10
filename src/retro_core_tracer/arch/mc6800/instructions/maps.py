# src/retro_core_tracer/arch/mc6800/instructions/maps.py
"""
オペコードと命令実装のマッピング定義。
"""
from . import load
from . import alu
from . import control

# @intent:map オペコード（整数）からデコード関数へのマッピングテーブル。
DECODE_MAP = {
    # Load/Store
    0x86: load.decode_ldaa_imm,
    0x96: load.decode_ldaa_dir,
    0xC6: load.decode_ldab_imm,
    0xCE: load.decode_ldx_imm,
    0xB7: load.decode_staa_ext,
    0x36: load.decode_psha,
    0x32: load.decode_pula,
    0x37: load.decode_pshb,
    0x33: load.decode_pulb,
    
    # ALU
    0x8B: alu.decode_adda_imm,
    0x84: alu.decode_anda_imm,
    0x5C: alu.decode_incb,
    0x80: alu.decode_suba_imm,
    0x81: alu.decode_cmpa_imm,
    
    # Control
    0x20: control.decode_bra,
    0x26: control.decode_bne,
    0x27: control.decode_beq,
    0x01: control.decode_nop,
    0xBD: control.decode_jsr_ext,
    0x39: control.decode_rts,
}

# @intent:map オペコード（整数）から実行関数へのマッピングテーブル。
EXECUTE_MAP = {
    # Load/Store
    0x86: load.execute_ldaa_imm,
    0x96: load.execute_ldaa_dir,
    0xC6: load.execute_ldab_imm,
    0xCE: load.execute_ldx_imm,
    0xB7: load.execute_staa_ext,
    0x36: load.execute_psha,
    0x32: load.execute_pula,
    0x37: load.execute_pshb,
    0x33: load.execute_pulb,
    
    # ALU
    0x8B: alu.execute_adda_imm,
    0x84: alu.execute_anda_imm,
    0x5C: alu.execute_incb,
    0x80: alu.execute_suba_imm,
    0x81: alu.execute_cmpa_imm,
    
    # Control
    0x20: control.execute_bra,
    0x26: control.execute_bne,
    0x27: control.execute_beq,
    0x01: control.execute_nop,
    0xBD: control.execute_jsr_ext,
    0x39: control.execute_rts,
}
