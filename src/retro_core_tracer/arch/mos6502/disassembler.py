# src/retro_core_tracer/arch/mos6502/disassembler.py
"""
MOS 6502 逆アセンブラ。
"""
from typing import List, Tuple
from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.arch.mos6502.instructions.maps import OPCODE_MAP
from retro_core_tracer.arch.mos6502.state import Mos6502CpuState

# @intent:responsibility 指定されたメモリ範囲を逆アセンブルする。
def disassemble(bus: Bus, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
    """
    メモリを解析し、(アドレス, HEX, ニーモニック) のリストを返す。
    """
    results = []
    current_addr = start_addr
    end_addr = start_addr + length
    
    # 逆アセンブル時にはレジスタ状態が不明なため、アドレッシングモード解決関数は使わず、
    # 簡易的にオペコードマップからニーモニックと長さを取得する。
    
    while current_addr < end_addr:
        addr = current_addr & 0xFFFF
        opcode = bus.read(addr)
        entry = OPCODE_MAP.get(opcode)
        
        if not entry:
            results.append((addr, f"{opcode:02X}", f"DB ${opcode:02X}"))
            current_addr += 1
            continue
            
        mnemonic, addr_func, _, _ = entry
        
        # オペランド長を取得するためにダミーの状態を渡してaddr_funcを呼ぶ
        # base.py の addr_func は bus.read を行う。
        dummy_state = Mos6502CpuState()
        _, _, _, op_str, op_bytes = addr_func(addr, bus, dummy_state)
        
        instr_len = 1 + len(op_bytes)
        hex_str = " ".join([f"{bus.read((addr + i) & 0xFFFF):02X}" for i in range(instr_len)])
        mnemonic_full = f"{mnemonic} {op_str}".strip()
        
        results.append((addr, hex_str, mnemonic_full))
        current_addr += instr_len
        
    return results
