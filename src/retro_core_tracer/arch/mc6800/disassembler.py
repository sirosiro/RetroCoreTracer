# src/retro_core_tracer/arch/mc6800/disassembler.py
"""
MC6800 Disassembler

メモリ上のバイナリデータを解析し、MC6800のアセンブリ言語（ニーモニック）に変換します。
Instruction Layerのデコードロジックを再利用しますが、バスアクセスログを汚さないように
PeekBusラッパーを使用します。
"""
from typing import List, Tuple
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mc6800.instructions import decode_opcode

# @intent:utility_class バスへのアクセスをPeek（ログなし読み込み）に変換するラッパーです。
class PeekBus:
    """
    Busのラッパー。readメソッドをpeek（ログなし読み込み）にリダイレクトします。
    デコーダがバスアクセスログを生成するのを防ぐために使用します。
    """
    def __init__(self, bus: Bus):
        self._bus = bus

    def read(self, address: int) -> int:
        return self._bus.peek(address)

    def write(self, address: int, data: int) -> None:
        pass

# @intent:responsibility 指定されたメモリ範囲を逆アセンブルし、表示用データを生成します。
def disassemble(bus: Bus, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
    """
    指定された範囲のメモリを逆アセンブルします。
    
    Returns:
        List of (address, hex_bytes, mnemonic) tuples.
    """
    result = []
    current_addr = start_addr
    end_addr = start_addr + length
    peek_bus = PeekBus(bus)

    while current_addr < end_addr:
        # メモリ境界チェック
        if current_addr > 0xFFFF:
            break

        opcode = bus.peek(current_addr)
        
        # デコード実行 (PeekBusを使用)
        operation = decode_opcode(opcode, peek_bus, current_addr)
        
        # HEX表現の生成
        hex_bytes = f"{opcode:02X}"
        for b in operation.operand_bytes:
            hex_bytes += f" {b:02X}"
            
        # ニーモニックの生成
        mnemonic_str = operation.mnemonic
        if operation.operands:
            mnemonic_str += " " + ", ".join(operation.operands)
            
        result.append((current_addr, hex_bytes, mnemonic_str))
        
        # 次の命令へ
        if operation.length == 0:
             # 無限ループ回避（万が一length 0が返ってきた場合）
             current_addr += 1
        else:
             current_addr += operation.length
             
    return result