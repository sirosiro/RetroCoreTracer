# src/retro_core_tracer/arch/mos6502/assembler.py
"""
MOS 6502 簡易アセンブラ。
"""
import re
from typing import List, Tuple, Dict, Optional
from retro_core_tracer.common.types import SymbolMap
from retro_core_tracer.loader.assembler import BaseAssembler
from retro_core_tracer.arch.mos6502.instructions.maps import OPCODE_MAP

class Mos6502Assembler(BaseAssembler):
    """
    MOS 6502 用の簡易アセンブラ。
    """
    def __init__(self):
        super().__init__()
        # ニーモニック -> オペコードエントリの逆引きマップを作成
        self._mnemonic_map = {}
        for opcode, entry in OPCODE_MAP.items():
            mnemonic = entry[0]
            if mnemonic not in self._mnemonic_map:
                self._mnemonic_map[mnemonic] = []
            self._mnemonic_map[mnemonic].append((opcode, entry))

    def _parse_operand(self, operand_str: str, symbols: Dict[str, int]) -> Tuple[str, int]:
        """
        オペランド文字列を解析し、アドレッシングモードと値を返す。
        戻り値: (mode_hint, value)
        mode_hint: 'IMMEDIATE', 'ZEROPAGE', 'ZEROPAGE_X', 'ABSOLUTE', 'ABSOLUTE_X', 'ABSOLUTE_Y', 'INDIRECT', 'INDEXED_INDIRECT', 'INDIRECT_INDEXED', 'RELATIVE', 'IMPLIED'
        """
        operand_str = operand_str.strip()
        
        # Immediate: #$12
        if operand_str.startswith('#'):
            val_str = operand_str[1:]
            return 'IMMEDIATE', self._parse_value(val_str, symbols)
        
        # Indirect: ($1234) - JMP only
        if operand_str.startswith('(') and operand_str.endswith(')'):
            inner = operand_str[1:-1]
            # Indirect Indexed: ($xx),Y
            if inner.endswith(',Y'): # これは ($xx),Y の形にならない。 ($xx),Y は operand_str="($xx),Y"
                pass # 下で処理
            
            # Indexed Indirect: ($xx,X)
            if ',' in inner:
                 base, reg = inner.split(',')
                 if reg.strip().upper() == 'X':
                     return 'INDEXED_INDIRECT', self._parse_value(base, symbols)

            # Plain Indirect: ($xxxx)
            return 'INDIRECT', self._parse_value(inner, symbols)

        # Indexed Indirect: ($xx,X) - regex needed?
        if operand_str.startswith('(') and operand_str.endswith(',X)'):
             base = operand_str[1:-3]
             return 'INDEXED_INDIRECT', self._parse_value(base, symbols)

        # Indirect Indexed: ($xx),Y
        if operand_str.startswith('(') and operand_str.endswith('),Y'):
             base = operand_str[1:-3]
             return 'INDIRECT_INDEXED', self._parse_value(base, symbols)

        # Indexed: $1234,X / $12,X
        if operand_str.endswith(',X'):
            base = operand_str[:-2]
            val = self._parse_value(base, symbols)
            if val <= 0xFF:
                return 'ZEROPAGE_X', val
            else:
                return 'ABSOLUTE_X', val

        # Indexed: $1234,Y / $12,Y
        if operand_str.endswith(',Y'):
            base = operand_str[:-2]
            val = self._parse_value(base, symbols)
            if val <= 0xFF:
                return 'ZEROPAGE_Y', val # STX, LDX only
            else:
                return 'ABSOLUTE_Y', val

        # Absolute / Zero Page / Relative
        if not operand_str:
             return 'IMPLIED', 0
             
        val = self._parse_value(operand_str, symbols)
        
        # Relative (Branch target) - handled by instruction type?
        # Assembler needs to know if instruction is branch.
        # Here we just return address/value.
        
        if val <= 0xFF:
            return 'ZEROPAGE', val
        else:
            return 'ABSOLUTE', val

    def _parse_value(self, val_str: str, symbols: Dict[str, int]) -> int:
        return self._parse_val(val_str, symbols)

    def assemble(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
        symbol_map = {}
        binary_data = []
        parsed_lines = []

        for line in lines:
            parsed_lines.append(self._parse_line(line))

        # First pass: Build symbol map
        temp_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if label:
                symbol_map[label] = temp_pc
            if not mnemonic:
                continue
            
            if mnemonic == "ORG":
                temp_pc = self._parse_value(operands, {})
                continue
            
            # 命令長計算
            # 仮のアセンブルを行い長さを取得
            try:
                op_bytes = self._assemble_line(mnemonic, operands or "", temp_pc, {}) # symbol map empty for 1st pass size calc?
                # しかし分岐命令はオフセット計算にPCが必要で、シンボルがまだない場合エラーになる可能性がある。
                # 相対ジャンプのオフセット計算はパス2でやるべき。
                # 6502の分岐命令は常に2バイト。
                if mnemonic in ['BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS']:
                    length = 2
                else:
                    op_bytes = self._assemble_line(mnemonic, operands or "", temp_pc, {}) # Pass empty dict, assume size doesn't change
                    length = len(op_bytes)
            except ValueError:
                # シンボル未解決などでエラーになる場合、オペランドの形式から長さを推測
                # これは簡易実装。本来はしっかりやるべき。
                length = self._guess_instruction_length(mnemonic, operands)
                
            temp_pc += length

        # Second pass: Generate binary
        current_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if not mnemonic:
                continue

            if mnemonic == "ORG":
                current_pc = self._parse_value(operands, {})
                continue
            
            # シンボルマップを渡して本番アセンブル
            op_bytes = self._assemble_line(mnemonic, operands or "", current_pc, symbol_map)
            
            for i, b in enumerate(op_bytes):
                binary_data.append((current_pc + i, b))
            
            current_pc += len(op_bytes)

        return symbol_map, binary_data

    def _guess_instruction_length(self, mnemonic: str, operands: str) -> int:
        if not operands: return 1
        if operands.startswith('#'): return 2
        # Indirect JMP ($xxxx)
        if mnemonic == 'JMP' and operands.startswith('('): return 3
        # Branch
        if mnemonic in ['BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS']: return 2
        
        # Absolute vs ZeroPage cannot be determined without symbol value.
        # Assume Absolute (3 bytes) for safety in 1st pass if unknown.
        # But if it turns out to be ZP later, addresses shift.
        # Simple assembler usually assumes Absolute unless known ZP.
        return 3

    def _assemble_line(self, mnemonic: str, operand_str: str, current_pc: int, symbols: Dict[str, int]) -> List[int]:
        if mnemonic not in self._mnemonic_map:
            raise ValueError(f"Unknown mnemonic: {mnemonic}")

        candidates = self._mnemonic_map[mnemonic]
        
        # オペランド解析でシンボル解決が必要
        # _parse_operand -> _parse_value -> symbols
        # パス1ではsymbolsが空で呼ばれるとエラーになる可能性がある。
        # _parse_operand内でエラーを捕捉してダミーを返す？
        try:
            mode, val = self._parse_operand(operand_str, symbols)
        except ValueError:
            # パス1のためのフォールバック（長さ計算用）
            # シンボルが見つからない場合は、とりあえずABSOLUTE扱いにするためのダミー値を返す
            if not symbols: 
                mode = 'ABSOLUTE'
                val = 0xFFFF
            else:
                raise

        # マッチするオペコードを探す
        # 注意: 6502は同じニーモニックでもアドレッシングモードでOpcodeが変わる
        
        # 分岐命令の特別扱い (Relative)
        if mnemonic in ['BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS']:
            # Relative mode
            # Calculate offset
            offset = val - (current_pc + 2)
            if not (-128 <= offset <= 127):
                if not symbols: # 1st pass fallback
                    offset = 0
                else:
                    raise ValueError(f"Branch target out of range: {offset}")
            
            # Find opcode for Relative mode
            # In maps.py, addr_relative is used.
            for opcode, entry in candidates:
                if entry[1].__name__ == 'addr_relative':
                     return [opcode, offset & 0xFF]
            raise ValueError(f"No relative opcode for {mnemonic}")

        # 一般的な命令のマッチング
        best_match = None
        
        for opcode, entry in candidates:
            addr_func_name = entry[1].__name__
            
            # Map parser mode to address function
            matched = False
            if mode == 'IMMEDIATE' and addr_func_name == 'addr_immediate': matched = True
            elif mode == 'ZEROPAGE' and addr_func_name == 'addr_zeropage': matched = True
            elif mode == 'ZEROPAGE_X' and addr_func_name == 'addr_zeropage_x': matched = True
            elif mode == 'ZEROPAGE_Y' and addr_func_name == 'addr_zeropage_y': matched = True
            elif mode == 'ABSOLUTE':
                 if addr_func_name == 'addr_absolute': matched = True
            elif mode == 'ABSOLUTE_X' and addr_func_name == 'addr_absolute_x': matched = True
            elif mode == 'ABSOLUTE_Y' and addr_func_name == 'addr_absolute_y': matched = True
            elif mode == 'INDIRECT' and addr_func_name == 'addr_indirect': matched = True
            elif mode == 'INDEXED_INDIRECT' and addr_func_name == 'addr_indexed_indirect': matched = True
            elif mode == 'INDIRECT_INDEXED' and addr_func_name == 'addr_indirect_indexed': matched = True
            elif mode == 'IMPLIED' and addr_func_name == 'addr_implied': matched = True
            
            if matched:
                best_match = (opcode, entry)
                break
        
        # Fallback for ZeroPage -> Absolute promotion if ZeroPage op doesn't exist
        if not best_match and mode == 'ZEROPAGE':
             for opcode, entry in candidates:
                 if entry[1].__name__ == 'addr_absolute':
                     best_match = (opcode, entry)
                     break
                     
        if not best_match:
            raise ValueError(f"No matching opcode for {mnemonic} with mode {mode}")
            
        opcode, entry = best_match
        addr_func_name = entry[1].__name__
        
        if addr_func_name == 'addr_implied':
            return [opcode]
        elif addr_func_name in ['addr_immediate', 'addr_zeropage', 'addr_zeropage_x', 'addr_zeropage_y', 'addr_indexed_indirect', 'addr_indirect_indexed']:
            return [opcode, val & 0xFF]
        elif addr_func_name in ['addr_absolute', 'addr_absolute_x', 'addr_absolute_y', 'addr_indirect']:
            return [opcode, val & 0xFF, (val >> 8) & 0xFF]
            
        return []

