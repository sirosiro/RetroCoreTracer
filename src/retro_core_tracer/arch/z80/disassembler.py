"""
Z80逆アセンブラモジュール。

メモリ上のバイナリデータを解析し、Z80アセンブリ言語のニーモニック形式に変換します。
"""
from typing import List, Tuple
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.z80.instructions import decode_opcode

# @intent:responsibility 指定されたメモリ範囲のバイナリデータを解析し、アドレスとニーモニックのリストを返します。
def disassemble(bus: Bus, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
    """
    メモリ上のデータを読み取り、(アドレス, 16進ダンプ, ニーモニック) のタプルのリストを返します。
    """
    result = []
    current_addr = start_addr
    end_addr = start_addr + length

    while current_addr < end_addr:
        # バス範囲外チェック
        if current_addr > 0xFFFF:
            break

        try:
            # 現在のアドレスのオペコードを読み取る
            # ログを汚さないためにpeekを使用
            opcode = bus.peek(current_addr)
            mnemonic = "UNKNOWN"
            length = 1
            
            # デコード（decode_opcodeはオペランド読み取りのためにbusアクセスを行う）
            # 副作用はないはずだが、読み取り位置がずれないように注意
            operation = decode_opcode(opcode, bus, current_addr)
            
            # 16進ダンプ文字列の生成 (Opcode + Operands)
            hex_bytes = [f"{opcode:02X}"]
            for b in operation.operand_bytes:
                hex_bytes.append(f"{b:02X}")
            hex_dump = " ".join(hex_bytes)

            # ニーモニックの生成
            # オペランドがプレースホルダー ($XX) のままになっている場合、実際の値を埋め込む
            # decode_opcodeが返すOperationは既にフォーマット済みの場合が多いが確認
            mnemonic = operation.mnemonic
            if operation.operands:
                mnemonic += " " + ",".join(operation.operands)

            result.append((current_addr, hex_dump, mnemonic))

            # 次の命令へ
            current_addr += operation.length

        except IndexError:
            # メモリ範囲外エラーなどの場合
            result.append((current_addr, "??", "ERR"))
            current_addr += 1
            
    return result
