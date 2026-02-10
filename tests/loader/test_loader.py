# tests/loader/test_loader.py
"""
retro_core_tracer.loader.loaderモジュールの単体テスト。
Intel HEXファイルのロード機能とAssemblyLoaderのスタブを検証します。
"""
import pytest
from pathlib import Path

from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.loader.loader import IntelHexLoader, AssemblyLoader, SymbolMap

# @intent:test_suite コードローダー機能の検証。

class TestIntelHexLoader:
    """
    IntelHexLoaderの単体テスト。
    """

    @pytest.fixture
    def setup_loader(self, tmp_path):
        bus = Bus()
        ram = RAM(0x100000) # 1MB RAMに拡張
        bus.register_device(0x0000, 0xFFFFF, ram)
        loader = IntelHexLoader()
        return loader, bus, ram, tmp_path

    def test_load_simple_hex_data(self, setup_loader):
        loader, bus, ram, tmp_path = setup_loader
        hex_content = """
        :020000001234B8
        :02000200ABCD84
        :00000001FF
        """
        hex_file = tmp_path / "simple.hex"
        hex_file.write_text(hex_content)

        loader.load_intel_hex(str(hex_file), bus)

        assert ram.read(0x0000) == 0x12
        assert ram.read(0x0001) == 0x34
        assert ram.read(0x0002) == 0xAB
        assert ram.read(0x0003) == 0xCD

    def test_load_extended_linear_address_hex(self, setup_loader):
        loader, bus, ram, tmp_path = setup_loader
        hex_content = """
        :020000040001F9 ; Set ELA to 0x0001xxxx
        :021000001234A8
        :00000001FF
        """
        hex_file = tmp_path / "ela.hex"
        hex_file.write_text(hex_content)

        loader.load_intel_hex(str(hex_file), bus)

        assert ram.read(0x11000) == 0x12
        assert ram.read(0x11001) == 0x34

    def test_load_multiple_records(self, setup_loader):
        loader, bus, ram, tmp_path = setup_loader
        hex_content = """
        :03000000AABBCCCC
        :02000300DDEE30
        :00000001FF
        """
        hex_file = tmp_path / "multiple.hex"
        hex_file.write_text(hex_content)

        loader.load_intel_hex(str(hex_file), bus)

        assert ram.read(0x0000) == 0xAA
        assert ram.read(0x0001) == 0xBB
        assert ram.read(0x0002) == 0xCC
        assert ram.read(0x0003) == 0xDD
        assert ram.read(0x0004) == 0xEE

    def test_load_invalid_checksum(self, setup_loader):
        loader, bus, ram, tmp_path = setup_loader
        hex_content = """
        :020000001234B9 ; Checksum should be B8, but it's B9
        :00000001FF
        """
        hex_file = tmp_path / "invalid_checksum.hex"
        hex_file.write_text(hex_content)

        # メッセージが完全一致するか検証（正規表現ではないので注意）
        # loader.pyの実装: raise ValueError(f"Checksum mismatch on line {line_num}: Calculated {calculated_checksum:02X}, Expected {checksum_field:02X}")
        # Test expectation: match="Checksum mismatch on line 2: Calculated B8, Expected B9"
        # Note: loader.py implementation matches this exactly now.
        with pytest.raises(ValueError, match="Checksum mismatch on line 2: Calculated B8, Expected B9"):
            loader.load_intel_hex(str(hex_file), bus)

    def test_load_unknown_record_type(self, setup_loader):
        loader, bus, ram, tmp_path = setup_loader
        hex_content = """
        :020000061234B2 ; Record type 0x06 is unknown
        :00000001FF
        """
        hex_file = tmp_path / "unknown_record.hex"
        hex_file.write_text(hex_content)

        with pytest.raises(ValueError, match="Unknown Intel HEX record type 06 on line 2"):
            loader.load_intel_hex(str(hex_file), bus)

    def test_load_empty_hex_file(self, setup_loader):
        loader, bus, ram, tmp_path = setup_loader
        hex_file = tmp_path / "empty.hex"
        hex_file.write_text("") # 空ファイル

        loader.load_intel_hex(str(hex_file), bus)
        # 何も書き込まれていないことを確認（エラーが発生しないこと）
        assert ram.read(0x0000) == 0x00

class TestAssemblyLoader:
    """
    AssemblyLoaderの単体テスト。
    """
    def test_load_assembly_basic(self, tmp_path):
        bus = Bus()
        ram = RAM(0x1000)
        bus.register_device(0x0000, 0x0FFF, ram)
        
        asm_content = """
        ORG 0x100
        start:
            NOP
            DB 0x12, 0x34
        loop:
            LD A, 0xFF
            HALT
        """
        asm_file = tmp_path / "test.asm"
        asm_file.write_text(asm_content)

        loader = AssemblyLoader()
        symbol_map = loader.load_assembly(str(asm_file), bus)

        assert symbol_map == {"start": 0x100, "loop": 0x103}
        
        assert ram.read(0x100) == 0x00 # NOP
        assert ram.read(0x101) == 0x12 # DB
        assert ram.read(0x102) == 0x34 # DB
        assert ram.read(0x103) == 0x3E # LD A, n
        assert ram.read(0x104) == 0xFF # n
        assert ram.read(0x105) == 0x76 # HALT