# retro_core_tracer/loader/loader.py
"""
コードローダーモジュール。
"""
import re
from typing import Dict, Tuple, List, Optional

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.common.types import SymbolMap

class IntelHexLoader:
    """
    Intel HEX形式のファイルを解析し、データをバスにロードするローダー。
    """
    def load_intel_hex(self, file_path: str, bus: Bus) -> None:
        current_extended_linear_address = 0x0000

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or not line.startswith(':'):
                    continue

                comment_start = line.find(';')
                if comment_start != -1:
                    line = line[:comment_start].strip()

                if len(line) < 11:
                    raise ValueError(f"Invalid Intel HEX record format on line {line_num}: Too short - {line}")

                try:
                    data_length = int(line[1:3], 16)
                    address_field = int(line[3:7], 16)
                    record_type = int(line[7:9], 16)
                    data_part_str = line[9:-2]
                    checksum_field = int(line[-2:], 16)

                    if len(data_part_str) != data_length * 2:
                        raise ValueError(f"Data length mismatch on line {line_num}")

                    checksum_sum = data_length + (address_field >> 8) + (address_field & 0xFF) + record_type
                    for i in range(data_length):
                        checksum_sum += int(data_part_str[i*2:(i*2)+2], 16)
                    
                    calculated_checksum = (~checksum_sum + 1) & 0xFF

                    if calculated_checksum != checksum_field:
                        # テストコードの期待に合わせてメッセージを構築
                        raise ValueError(f"Checksum mismatch on line {line_num}: Calculated {calculated_checksum:02X}, Expected {checksum_field:02X}")

                    if record_type == 0x00:
                        load_address = current_extended_linear_address + address_field
                        for i in range(data_length):
                            byte_data = int(data_part_str[i*2:(i*2)+2], 16)
                            bus.write(load_address + i, byte_data)
                    elif record_type == 0x01:
                        break
                    elif record_type == 0x04:
                        current_extended_linear_address = int(data_part_str, 16) << 16
                    elif record_type == 0x02 or record_type == 0x05:
                        pass
                    else:
                        raise ValueError(f"Unknown Intel HEX record type {record_type:02X} on line {line_num}")

                except (ValueError, IndexError) as e:
                    # 既に ValueError ならそのまま上に投げる（二重ラップを避ける）
                    if isinstance(e, ValueError) and ("Checksum mismatch" in str(e) or "Unknown Intel HEX record type" in str(e)):
                        raise e
                    raise ValueError(f"Error parsing Intel HEX line {line_num}: {line} - {e}")

class AssemblyLoader:
    """
    アセンブリソースコードを解析し、シンボル情報を抽出し、
    バイナリに変換してバスにロードする簡易ローダー。
    """
    def load_assembly(self, file_path: str, bus: Bus, architecture: str = "Z80") -> SymbolMap:
        """
        指定されたアーキテクチャに基づいてアセンブリファイルをロードします。
        """
        symbol_map: SymbolMap = {}
        binary_data: List[Tuple[int, int]] = []
        
        with open(file_path, 'r', encoding="utf-8") as f:
            lines = f.readlines()

        if architecture == "Z80":
            symbol_map, binary_data = self._assemble_z80(lines)
        elif architecture == "MC6800":
            symbol_map, binary_data = self._assemble_mc6800(lines)
        else:
            raise ValueError(f"Unsupported architecture for assembly loading: {architecture}")

        for addr, data in binary_data:
            bus.write(addr, data)

        return symbol_map

    def _parse_line(self, line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """行を (label, mnemonic, operands) に分解する共通ヘルパー"""
        line = line.strip()
        if not line or line.startswith(';'):
            return None, None, None
        
        # コメント除去
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

    def _assemble_z80(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
        symbol_map = {}
        binary_data = []
        current_pc = 0x0000

        for line in lines:
            label, mnemonic, operands = self._parse_line(line)
            if label:
                symbol_map[label] = current_pc
            if not mnemonic:
                continue

            if mnemonic == "ORG":
                current_pc = int(operands.replace('$', '0x').replace('H', ''), 0)
            elif mnemonic == "DB":
                for val_str in operands.split(','):
                    val = int(val_str.strip().replace('$', '0x').replace('H', ''), 0)
                    binary_data.append((current_pc, val & 0xFF))
                    current_pc += 1
            elif mnemonic == "NOP":
                binary_data.append((current_pc, 0x00))
                current_pc += 1
            elif mnemonic == "HALT":
                binary_data.append((current_pc, 0x76))
                current_pc += 1
            elif mnemonic == "EI":
                binary_data.append((current_pc, 0xFB))
                current_pc += 1
            elif mnemonic == "DI":
                binary_data.append((current_pc, 0xF3))
                current_pc += 1
            elif mnemonic == "EXX":
                binary_data.append((current_pc, 0xD9))
                current_pc += 1
            elif mnemonic == "EX":
                ops = operands.upper().replace(" ", "")
                if ops == "DE,HL":
                    binary_data.append((current_pc, 0xEB))
                    current_pc += 1
                elif ops == "AF,AF'":
                    binary_data.append((current_pc, 0x08))
                    current_pc += 1
                elif ops == "(SP),HL":
                    binary_data.append((current_pc, 0xE3))
                    current_pc += 1
            elif mnemonic == "LD":
                if operands.upper().startswith("A,"):
                    n_str = operands.split(',')[1].strip()
                    n = int(n_str.replace('$', '0x').replace('H', ''), 0)
                    binary_data.append((current_pc, 0x3E))
                    binary_data.append((current_pc + 1, n & 0xFF))
                    current_pc += 2

        return symbol_map, binary_data

    def _assemble_mc6800(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
        symbol_map = {}
        binary_data = []
        parsed_lines = []

        for line in lines:
            parsed_lines.append(self._parse_line(line))

        temp_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if label:
                symbol_map[label] = temp_pc
            if not mnemonic:
                continue
            
            length = 0
            if mnemonic == "ORG":
                temp_pc = int(operands.replace('$', '0x').replace('H', ''), 0)
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

        current_pc = 0
        for label, mnemonic, operands in parsed_lines:
            if not mnemonic:
                continue

            if mnemonic == "ORG":
                current_pc = int(operands.replace('$', '0x').replace('H', ''), 0)
                continue

            opcode = None
            operand_bytes = []
            
            if mnemonic == "NOP":
                opcode = 0x01
            elif mnemonic == "LDAA":
                if operands.startswith('#'):
                    opcode = 0x86
                    val = self._parse_imm8(operands)
                    operand_bytes = [val]
                elif self._is_direct_heuristic(operands):
                    opcode = 0x96
                    addr = self._parse_addr(operands, symbol_map)
                    operand_bytes = [addr]
                else:
                    opcode = 0xB6
                    addr = self._parse_addr(operands, symbol_map)
                    operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "ADDA":
                if operands.startswith('#'):
                    opcode = 0x8B
                    val = self._parse_imm8(operands)
                    operand_bytes = [val]
            elif mnemonic == "STAA":
                opcode = 0xB7
                addr = self._parse_addr(operands, symbol_map)
                operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "BRA":
                opcode = 0x20
                target = self._parse_addr(operands, symbol_map)
                offset = target - (current_pc + 2)
                operand_bytes = [offset & 0xFF]
            elif mnemonic == "BNE":
                opcode = 0x26
                target = self._parse_addr(operands, symbol_map)
                offset = target - (current_pc + 2)
                operand_bytes = [offset & 0xFF]
            elif mnemonic == "BEQ":
                opcode = 0x27
                target = self._parse_addr(operands, symbol_map)
                offset = target - (current_pc + 2)
                operand_bytes = [offset & 0xFF]
            elif mnemonic == "JSR":
                opcode = 0xBD
                addr = self._parse_addr(operands, symbol_map)
                operand_bytes = [(addr >> 8) & 0xFF, addr & 0xFF]
            elif mnemonic == "RTS":
                opcode = 0x39
            
            if opcode is not None:
                bus_ops = [opcode] + operand_bytes
                for i, b in enumerate(bus_ops):
                    binary_data.append((current_pc + i, b))
                current_pc += len(bus_ops)

        return symbol_map, binary_data

    def _parse_imm8(self, operand: str) -> int:
        return int(operand.replace('#', '').replace('$', '0x'), 0) & 0xFF

    def _parse_addr(self, operand: str, symbols: SymbolMap) -> int:
        operand = operand.strip()
        if operand in symbols:
            return symbols[operand]
        return int(operand.replace('$', '0x'), 0) & 0xFFFF

    def _is_direct_heuristic(self, operand: str) -> bool:
        if operand.startswith('$') and len(operand) <= 3: return True
        return False
