# retro_core_tracer/loader/loader.py
"""
コードローダーモジュール。
Intel HEX および Motorola S-Record 形式のロードをサポートします。
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
                        raise ValueError(f"Checksum mismatch on line {line_num}: Calculated {calculated_checksum:02X}, Expected {checksum_field:02X}")

                    if record_type == 0x00:
                        load_address = (current_extended_linear_address + address_field) & 0xFFFFFFFF
                        for i in range(data_length):
                            byte_data = int(data_part_str[i*2:(i*2)+2], 16)
                            bus.write(load_address + i, byte_data)
                    elif record_type == 0x01:
                        break
                    elif record_type == 0x04:
                        current_extended_linear_address = int(data_part_str, 16) << 16
                    elif record_type == 0x02:
                        current_extended_linear_address = int(data_part_str, 16) << 4
                    elif record_type == 0x03 or record_type == 0x05:
                        pass
                    else:
                        raise ValueError(f"Unknown Intel HEX record type {record_type:02X} on line {line_num}")

                except (ValueError, IndexError) as e:
                    if isinstance(e, ValueError) and ("Checksum mismatch" in str(e) or "Unknown Intel HEX record type" in str(e)):
                        raise e
                    raise ValueError(f"Error parsing Intel HEX line {line_num}: {line} - {e}")

class SRecordLoader:
    """
    Motorola S-Record (S19, S28, S37) 形式のファイルを解析し、データをバスにロードするローダー。
    """
    def load_srecord(self, file_path: str, bus: Bus) -> None:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or not line.startswith('S'):
                    continue
                
                try:
                    record_type = line[1]
                    count = int(line[2:4], 16)
                    
                    checksum_sum = count
                    for i in range(1, count):
                        checksum_sum += int(line[i*2+2:i*2+4], 16)
                    
                    calculated_checksum = (~checksum_sum) & 0xFF
                    actual_checksum = int(line[count*2+2:count*2+4], 16)
                    
                    if calculated_checksum != actual_checksum:
                        raise ValueError(f"S-Record checksum mismatch on line {line_num}")

                    addr_len = 0
                    if record_type == '1': addr_len = 4 # 16-bit
                    elif record_type == '2': addr_len = 6 # 24-bit
                    elif record_type == '3': addr_len = 8 # 32-bit
                    
                    if addr_len > 0:
                        address = int(line[4:4+addr_len], 16)
                        data_str = line[4+addr_len:-2]
                        for i in range(len(data_str) // 2):
                            byte_data = int(data_str[i*2:(i*2)+2], 16)
                            bus.write(address + i, byte_data)
                    
                except (ValueError, IndexError) as e:
                    raise ValueError(f"Error parsing S-Record line {line_num}: {e}")

class AssemblyLoader:
    """
    アセンブリソースコードを解析し、シンボル情報を抽出し、
    バイナリに変換してバスにロードする簡易ローダー。
    """
    def load_assembly(self, file_path: str, bus: Bus, architecture: str = "Z80") -> SymbolMap:
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
        # @intent:utility_function 多様な数値表現（$, 0x, h）およびラベル名を安全に数値に変換します。
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

    def _assemble_z80(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
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

    def _assemble_mc6800(self, lines: List[str]) -> Tuple[SymbolMap, List[Tuple[int, int]]]:
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