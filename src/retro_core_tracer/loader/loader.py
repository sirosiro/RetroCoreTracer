# retro_core_tracer/loader/loader.py
"""
コードローダーモジュール。
Intel HEX および Motorola S-Record 形式のロードをサポートします。
"""
import re
import os
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Any

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.common.types import SymbolMap
from retro_core_tracer.loader.assembler import Z80Assembler, Mc6800Assembler

# @intent:responsibility 全てのローダーの共通インターフェースを定義します。
class BaseLoader(ABC):
    @abstractmethod
    def load(self, file_path: str, bus: Bus, **kwargs) -> Optional[SymbolMap]:
        """
        ファイルをロードし、バスにデータを書き込みます。
        シンボル情報がある場合は返します。
        """
        pass

class IntelHexLoader(BaseLoader):
    """
    Intel HEX形式のファイルを解析し、データをバスにロードするローダー。
    """
    # @intent:responsibility 共通インターフェースの実装。
    def load(self, file_path: str, bus: Bus, **kwargs) -> Optional[SymbolMap]:
        self.load_intel_hex(file_path, bus)
        return None

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
                            bus.load(load_address + i, byte_data)
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

class SRecordLoader(BaseLoader):
    """
    Motorola S-Record (S19, S28, S37) 形式のファイルを解析し、データをバスにロードするローダー。
    """
    # @intent:responsibility 共通インターフェースの実装。
    def load(self, file_path: str, bus: Bus, **kwargs) -> Optional[SymbolMap]:
        self.load_srecord(file_path, bus)
        return None

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
                            bus.load(address + i, byte_data)
                    
                except (ValueError, IndexError) as e:
                    raise ValueError(f"Error parsing S-Record line {line_num}: {e}")

class AssemblyLoader(BaseLoader):
    """
    アセンブリソースコードを解析し、シンボル情報を抽出し、
    バイナリに変換してバスにロードする簡易ローダー。
    """
    # @intent:responsibility 共通インターフェースの実装。アーキテクチャ指定を受け取ります。
    def load(self, file_path: str, bus: Bus, **kwargs) -> Optional[SymbolMap]:
        architecture = kwargs.get("architecture", "Z80")
        return self.load_assembly(file_path, bus, architecture)

    def load_assembly(self, file_path: str, bus: Bus, architecture: str = "Z80") -> SymbolMap:
        symbol_map: SymbolMap = {}
        binary_data: List[Tuple[int, int]] = []
        
        with open(file_path, 'r', encoding="utf-8") as f:
            lines = f.readlines()

        if architecture == "Z80":
            assembler = Z80Assembler()
            symbol_map, binary_data = assembler.assemble(lines)
        elif architecture == "MC6800":
            assembler = Mc6800Assembler()
            symbol_map, binary_data = assembler.assemble(lines)
        else:
            raise ValueError(f"Unsupported architecture for assembly loading: {architecture}")

        for addr, data in binary_data:
            bus.load(addr, data)

        return symbol_map

# @intent:responsibility ファイル拡張子に基づいて適切なローダーを生成します。
class LoaderFactory:
    @staticmethod
    def create_loader(file_path: str) -> BaseLoader:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.hex']:
            return IntelHexLoader()
        elif ext in ['.s19', '.s28', '.s37', '.srec']:
            return SRecordLoader()
        elif ext in ['.asm']:
            return AssemblyLoader()
        else:
            raise ValueError(f"Unsupported file extension: {ext}")