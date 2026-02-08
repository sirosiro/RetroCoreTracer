import pytest
import os
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.loader.loader import AssemblyLoader

def test_symbol_integration(tmp_path):
    # 1. 簡易アセンブリファイルの作成
    asm_file = tmp_path / "test.asm"
    asm_file.write_text("""
ORG $1000
START:
    NOP
    LD A, 5
LOOP:
    HALT
""")

    # 2. システムのセットアップ
    bus = Bus()
    ram = RAM(0x10000)
    bus.register_device(0x0000, 0xFFFF, ram)
    cpu = Z80Cpu(bus)
    loader = AssemblyLoader()

    # 3. アセンブリのロード
    symbol_map = loader.load_assembly(str(asm_file), bus)
    cpu.set_symbol_map(symbol_map)
    cpu.get_state().pc = 0x1000 # エントリポイント設定

    # 4. 実行とシンボル情報の検証
    # Step 1: START (NOP)
    snapshot = cpu.step()
    assert "START: NOP" in snapshot.metadata.symbol_info
    
    # Step 2: LD A, 5
    snapshot = cpu.step()
    assert "LD A,n $05" in snapshot.metadata.symbol_info
    
    # Step 3: LOOP (HALT)
    snapshot = cpu.step()
    assert "LOOP: HALT" in snapshot.metadata.symbol_info

    # シンボルマップ自体の内容確認
    assert symbol_map["START"] == 0x1000
    assert symbol_map["LOOP"] == 0x1003