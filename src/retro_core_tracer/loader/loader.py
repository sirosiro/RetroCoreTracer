# retro_core_tracer/loader/loader.py
"""
コードローダーモジュール。

Intel HEX形式のファイルやアセンブリソースコードを読み込み、
シミュレータのメモリ空間に配置する責務を負います。
"""
import re
from typing import Dict, Tuple, List

from retro_core_tracer.transport.bus import Bus

# @intent:data_structure シンボル名とアドレスをマッピングする辞書の型エイリアス。
SymbolMap = Dict[str, int]

# @intent:responsibility Intel HEX形式のファイルを解析し、メモリにロードします。
class IntelHexLoader:
    """
    Intel HEX形式のファイルを解析し、データをバスにロードするローダー。
    """

    # @intent:responsibility 指定されたIntel HEXファイルを読み込み、バスにデータを書き込みます。
    # @intent:pre-condition `file_path`は有効なIntel HEXファイルへのパスである必要があります。
    # @intent:pre-condition `bus`は有効なBusオブジェクトである必要があります。
    def load_intel_hex(self, file_path: str, bus: Bus) -> None:
        """
        Intel HEXファイルを読み込み、その内容をバスに書き込みます。
        各行は:DD AAAA TT DD...CC の形式に従います。
        """
        current_extended_linear_address = 0x0000

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or not line.startswith(':'):
                    continue # 空行または不正な行をスキップ

                # コメントを除去する
                comment_start = line.find(';')
                if comment_start != -1:
                    line = line[:comment_start].strip()

                if len(line) < 11: # 最低限のHEXレコード長 (:DD AAAA TT CC)
                    raise ValueError(f"Invalid Intel HEX record format on line {line_num}: Too short - {line}")

                try:
                    data_length = int(line[1:3], 16)
                    address_field = int(line[3:7], 16)
                    record_type = int(line[7:9], 16)
                    data_part_str = line[9:-2] # チェックサムを除くデータ部分
                    checksum_field = int(line[-2:], 16)

                    # データ部分の長さがdata_lengthと一致するか確認
                    if len(data_part_str) != data_length * 2:
                        raise ValueError(f"Data length mismatch on line {line_num}: Expected {data_length*2} hex chars, got {len(data_part_str)} - {line}")

                    # チェックサムの検証
                    # チェックサムは、データ長、アドレス、レコードタイプ、データバイトの合計の2の補数
                    checksum_sum = data_length + (address_field >> 8) + (address_field & 0xFF) + record_type
                    for i in range(data_length):
                        checksum_sum += int(data_part_str[i*2:(i*2)+2], 16)
                    
                    calculated_checksum = (~checksum_sum + 1) & 0xFF

                    if calculated_checksum != checksum_field:
                        raise ValueError(f"Checksum mismatch on line {line_num}: Calculated {calculated_checksum:02X}, Expected {checksum_field:02X} - {line}")

                    if record_type == 0x00: # データレコード
                        load_address = current_extended_linear_address + address_field
                        for i in range(data_length):
                            byte_data = int(data_part_str[i*2:(i*2)+2], 16)
                            bus.write(load_address + i, byte_data)
                    elif record_type == 0x01: # EOFレコード
                        break # ファイルの終わりに到達
                    elif record_type == 0x04: # 拡張リニアアドレスレコード
                        # upper 16 bits of the 20-bit or 32-bit linear address
                        current_extended_linear_address = int(data_part_str, 16) << 16
                    # その他のレコードタイプ (02, 05など) は現状無視するか、エラーとする
                    elif record_type == 0x02 or record_type == 0x05:
                        # 拡張セグメントアドレスレコード (0x02) や開始リニアアドレスレコード (0x05) は
                        # 現状のエミュレータでは直接使用しないため、警告または無視する
                        pass
                    else:
                        raise ValueError(f"Unknown Intel HEX record type {record_type:02X} on line {line_num}: {line}")

                except (ValueError, IndexError) as e:
                    raise ValueError(f"Error parsing Intel HEX line {line_num}: {line} - {e}")

# @intent:responsibility アセンブリソースコードをロードし、シンボルマップを生成します。
# @intent:rationale この機能はまだ実装されていませんが、将来的にアセンブリファイルを
#                   直接読み込み、デバッガでシンボル解決を行うために必要となります。
class AssemblyLoader:
    """
    アセンブリソースコードを解析し、シンボル情報を抽出し、
    バイナリに変換してバスにロードする（将来的には）。
    """
    def load_assembly(self, file_path: str, bus: Bus) -> SymbolMap:
        """
        アセンブリファイルを読み込み、解析し、シンボルマップを生成します。
        （現時点ではスタブ）
        """
        # TODO: アセンブリのパーサーとアセンブラを実装
        print(f"Loading assembly file (stub): {file_path}")
        return {"start": 0x0000, "main": 0x1000} # ダミーのシンボルマップ