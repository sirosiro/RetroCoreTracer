# retro_core_tracer/loader/assembler.py
"""
アーキテクチャごとのアセンブラ実装。
AssemblyLoaderから利用されます。
"""
import re
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Dict
from retro_core_tracer.common.types import SymbolMap

# @intent:responsibility アセンブラの共通インターフェースを定義します。
class BaseAssembler(ABC):
    @abstractmethod
    def assemble(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
        """
        アセンブリソースを行単位で解析し、シンボルマップとバイナリデータを返します。
        """
        pass

    def _parse_line(self, line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        line = line.strip()
        if not line or line.startswith(';'):
            return None, None, None
        
        line = line.split(';')[0].strip()
        
        label = None
        if ':' in line:
            label, rest = line.split(':', 1)
            label = label.strip()
            line = rest.strip()
        
        if not line:
            return label, None, None

        parts = re.split(r'\s+', line, maxsplit=1)
        mnemonic = parts[0].upper()
        operands = parts[1] if len(parts) > 1 else ""
        
        return label, mnemonic, operands

    def _parse_val(self, val_str: str, symbol_map: SymbolMap) -> int:
        val_str = val_str.strip().replace('$', '0x')
        val_str = re.sub(r'[hH]$', '', val_str) 
        if val_str.startswith('0x'):
            return int(val_str, 16)
        try:
            return int(val_str)
        except ValueError:
            if val_str in symbol_map:
                return symbol_map[val_str]
            raise ValueError(f"Undefined symbol or invalid value: {val_str}")

# @intent:responsibility Z80用のアセンブラ実装。
class Z80Assembler(BaseAssembler):
    def assemble(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
        symbol_map = {}
        binary_data = []
        parsed_lines = []

        for line in lines:
            parsed_lines.append(self._parse_line(line))

        # First pass: Build symbol map and calculate current_pc for labels
        temp_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if label:
                symbol_map[label] = temp_pc
            if not mnemonic:
                continue

            if mnemonic == "ORG":
                temp_pc = self._parse_val(operands, {}) 
                continue
            
            length = 0
            if mnemonic == "DB":
                length = len(operands.split(','))
            elif mnemonic in ["NOP", "HALT", "DI", "EI", "EXX", "RET", "RETI", "RETN"]:
                length = 1
            elif mnemonic == "EX":
                length = 1
            elif mnemonic == "LD":
                if operands.upper().startswith("A,"): length = 2
                elif operands.upper().startswith("BC,") or operands.upper().startswith("DE,") or operands.upper().startswith("HL,") or operands.upper().startswith("SP,"):
                    length = 3
                else: length = 2
            elif mnemonic in ["JP", "CALL"]: length = 3
            elif mnemonic in ["JR", "DJNZ"]: length = 2
            elif mnemonic in ["INC", "DEC"]: length = 1
            
            temp_pc += length

        # Second pass: Generate binary
        current_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if not mnemonic:
                continue

            if mnemonic == "ORG":
                current_pc = self._parse_val(operands, {})
                continue

            opcode = None
            operand_bytes = []
            
            if mnemonic == "DB":
                for val_str in operands.split(','):
                    val = self._parse_val(val_str, symbol_map)
                    binary_data.append((current_pc, val & 0xFF))
                    current_pc += 1
                continue

            if mnemonic == "NOP": opcode = 0x00
            elif mnemonic == "HALT": opcode = 0x76
            elif mnemonic == "DI": opcode = 0xF3
            elif mnemonic == "EI": opcode = 0xFB
            elif mnemonic == "EXX": opcode = 0xD9
            elif mnemonic == "RET": opcode = 0xC9
            elif mnemonic == "EX":
                ops = operands.upper().replace(" ", "")
                if ops == "DE,HL": opcode = 0xEB
                elif ops == "AF,AF'": opcode = 0x08
                elif ops == "(SP),HL": opcode = 0xE3
            elif mnemonic == "LD":
                ops = operands.upper().replace(" ", "")
                if ops.startswith("A,"):
                    opcode = 0x3E
                    val = self._parse_val(operands.split(',')[1], symbol_map)
                    operand_bytes = [val & 0xFF]
                elif ops.startswith("BC,"):
                    opcode = 0x01
                    val = self._parse_val(operands.split(',')[1], symbol_map)
                    operand_bytes = [val & 0xFF, (val >> 8) & 0xFF]
                elif ops.startswith("DE,"):
                    opcode = 0x11
                    val = self._parse_val(operands.split(',')[1], symbol_map)
                    operand_bytes = [val & 0xFF, (val >> 8) & 0xFF]
                elif ops.startswith("HL,"):
                    opcode = 0x21
                    val = self._parse_val(operands.split(',')[1], symbol_map)
                    operand_bytes = [val & 0xFF, (val >> 8) & 0xFF]
                elif ops.startswith("SP,"):
                    opcode = 0x31
                    val = self._parse_val(operands.split(',')[1], symbol_map)
                    operand_bytes = [val & 0xFF, (val >> 8) & 0xFF]
            elif mnemonic == "JP":
                opcode = 0xC3
                val = self._parse_val(operands, symbol_map)
                operand_bytes = [val & 0xFF, (val >> 8) & 0xFF]
            elif mnemonic == "CALL":
                opcode = 0xCD
                val = self._parse_val(operands, symbol_map)
                operand_bytes = [val & 0xFF, (val >> 8) & 0xFF]
            elif mnemonic == "JR":
                opcode = 0x18
                target = self._parse_val(operands, symbol_map)
                offset = (target - (current_pc + 2)) & 0xFF
                operand_bytes = [offset]
            elif mnemonic == "DJNZ":
                opcode = 0x10
                target = self._parse_val(operands, symbol_map)
                offset = (target - (current_pc + 2)) & 0xFF
                operand_bytes = [offset]

            if opcode is not None:
                binary_data.append((current_pc, opcode))
                for i, b in enumerate(operand_bytes):
                    binary_data.append((current_pc + 1 + i, b))
                current_pc += 1 + len(operand_bytes)

        return symbol_map, binary_data

# @intent:responsibility MC6800用のアセンブラ実装。
class Mc6800Assembler(BaseAssembler):
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
            
            length = 0
            if mnemonic == "ORG":
                temp_pc = self._parse_val(operands, {})
                continue
            elif mnemonic == "DB":
                length = len(operands.split(','))
            elif mnemonic in ["NOP", "CLRA", "CLRB", "INCA", "INCB", "DECA", "DECB", "RTS", "RTI", "WAI"]:
                length = 1
            elif mnemonic in ["LDAA", "LDAB", "ADDA", "ADDB", "SUBA", "SUBB", "ANDA", "ANDB", "ORAA", "ORAB", "CMPA", "CMPB"]:
                if operands.startswith('#'): length = 2
                else: length = 3
            elif mnemonic in ["STAA", "STAB"]:
                 if ',' in operands and 'X' in operands.upper(): length = 2
                 elif len(operands.replace('$','').replace('0x','')) <= 2: length = 2
                 else: length = 3
            elif mnemonic in ["LDX", "STX", "CPX"]:
                if operands.startswith('#'): length = 3
                else: length = 3
            elif mnemonic in ["BRA", "BNE", "BEQ", "BPL", "BMI", "BVC", "BVS", "BCC", "BCS", "BHI", "BLS", "BGE", "BLT", "BGT", "BLE", "BSR"]:
                length = 2
            elif mnemonic in ["JMP", "JSR"]:
                length = 3
            
            temp_pc += length

        # Second pass: Generate binary
        current_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if not mnemonic:
                continue

            if mnemonic == "ORG":
                current_pc = self._parse_val(operands, {})
                continue

            opcode = None
            operand_bytes = []
            
            if mnemonic == "DB":
                for val_str in operands.split(','):
                    try:
                        val = self._parse_val(val_str, symbol_map)
                        binary_data.append((current_pc, val & 0xFF))
                        current_pc += 1
                    except ValueError:
                        if val_str.strip() in symbol_map:
                            val = symbol_map[val_str.strip()]
                            binary_data.append((current_pc, (val >> 8) & 0xFF))
                            binary_data.append((current_pc + 1, val & 0xFF))
                            current_pc += 2
                continue

            if mnemonic == "NOP":
                opcode = 0x01
            elif mnemonic == "LDAA":
                if operands.startswith('#'):
                    opcode = 0x86
                    val = self._parse_val(operands.replace('#', ''), symbol_map)
                    operand_bytes = [val & 0xFF]
                elif self._is_direct_heuristic(operands):
                    opcode = 0x96
                    addr = self._parse_val(operands, symbol_map)
                    operand_bytes = [addr & 0xFF]
                else:
                    opcode = 0xB6
                    addr = self._parse_val(operands, symbol_map)
                    operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "LDAB":
                if operands.startswith('#'):
                    opcode = 0xC6
                    val = self._parse_val(operands.replace('#', ''), symbol_map)
                    operand_bytes = [val & 0xFF]
                elif self._is_direct_heuristic(operands):
                    opcode = 0xD6
                    addr = self._parse_val(operands, symbol_map)
                    operand_bytes = [addr & 0xFF]
                else:
                    opcode = 0xF6
                    addr = self._parse_val(operands, symbol_map)
                    operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "ADDA":
                if operands.startswith('#'):
                    opcode = 0x8B
                    val = self._parse_val(operands.replace('#', ''), symbol_map)
                    operand_bytes = [val & 0xFF]
            elif mnemonic == "STAA":
                opcode = 0xB7
                addr = self._parse_val(operands, symbol_map)
                operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "BRA":
                opcode = 0x20
                target = self._parse_val(operands, symbol_map)
                offset = (target - (current_pc + 2)) & 0xFF
                operand_bytes = [offset]
            elif mnemonic == "BNE":
                opcode = 0x26
                target = self._parse_val(operands, symbol_map)
                offset = (target - (current_pc + 2)) & 0xFF
                operand_bytes = [offset]
            elif mnemonic == "BEQ":
                opcode = 0x27
                target = self._parse_val(operands, symbol_map)
                offset = (target - (current_pc + 2)) & 0xFF
                operand_bytes = [offset]
            elif mnemonic == "JSR":
                opcode = 0xBD
                addr = self._parse_val(operands, symbol_map)
                operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "RTS":
                opcode = 0x39
            
            if opcode is not None:
                bus_ops = [opcode] + operand_bytes
                for i, b in enumerate(bus_ops):
                    binary_data.append((current_pc + i, b))
                current_pc += len(bus_ops)

        return symbol_map, binary_data

    def _is_direct_heuristic(self, operand: str) -> bool:
        if operand.startswith('$') and len(operand) <= 3: return True
        return False
