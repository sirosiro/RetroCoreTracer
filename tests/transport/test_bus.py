# tests/transport/test_bus.py
"""
retro_core_tracer.transport.busモジュールの単体テスト。
"""
import pytest
from retro_core_tracer.transport.bus import Bus, Device, RAM

# @intent:test_suite 共通バスとデバイスの基本的な機能とエラーハンドリングを検証します。

class TestRAM:
    """
    RAMデバイスの単体テスト。
    """
    # @intent:test_case_init RAMクラスが正しいサイズで初期化されることを検証します。
    def test_ram_init_valid_size(self):
        ram = RAM(16)
        assert ram.get_size() == 16
        assert all(b == 0 for b in ram._memory) # 全て0で初期化される

    # @intent:test_case_init 無効なサイズでRAMを初期化するとValueErrorが発生することを検証します。
    def test_ram_init_invalid_size(self):
        with pytest.raises(ValueError, match="RAM size must be a positive integer."):
            RAM(0)
        with pytest.raises(ValueError, match="RAM size must be a positive integer."):
            RAM(-1)
        with pytest.raises(ValueError, match="RAM size must be a positive integer."):
            RAM(1.5) # float

    # @intent:test_case_rw 境界内でRAMへの読み書きが正しく行われることを検証します。
    def test_ram_read_write_within_bounds(self):
        ram = RAM(4)
        ram.write(0, 0x12)
        ram.write(1, 0x34)
        ram.write(2, 0x56)
        ram.write(3, 0x78)
        assert ram.read(0) == 0x12
        assert ram.read(1) == 0x34
        assert ram.read(2) == 0x56
        assert ram.read(3) == 0x78

    # @intent:test_case_oob 境界外アドレスへのアクセス時にIndexErrorが発生することを検証します。
    def test_ram_read_write_out_of_bounds(self):
        ram = RAM(4)
        with pytest.raises(IndexError, match="Address 4 out of bounds for RAM of size 4."):
            ram.read(4)
        with pytest.raises(IndexError, match="Address -1 out of bounds for RAM of size 4."):
            ram.write(-1, 0x00)

    # @intent:test_case_data 無効なデータ（8bitを超過）を書き込もうとするとValueErrorが発生することを検証します。
    def test_ram_write_invalid_data(self):
        ram = RAM(1)
        with pytest.raises(ValueError, match="Data 256 is not an 8-bit value."):
            ram.write(0, 0x100)
        with pytest.raises(ValueError, match="Data -1 is not an 8-bit value."):
            ram.write(0, -1)

class TestBus:
    """
    Busの単体テスト。
    """
    # @intent:test_case_register デバイスがバスに正しく登録され、アクセスできることを検証します。
    def test_bus_register_and_access_device(self):
        bus = Bus()
        ram1 = RAM(16)
        ram2 = RAM(16)

        bus.register_device(0x0000, 0x000F, ram1) # 0-15
        bus.register_device(0x0010, 0x001F, ram2) # 16-31

        bus.write(0x0005, 0xAA)
        assert bus.read(0x0005) == 0xAA
        assert ram1.read(5) == 0xAA # 直接アクセスでも値が一致することを確認

        bus.write(0x001A, 0xBB)
        assert bus.read(0x001A) == 0xBB
        assert ram2.read(0x0A) == 0xBB # オフセット計算が正しいことを確認

    # @intent:test_case_unmapped マップされていないアドレスへのアクセス時にIndexErrorが発生することを検証します。
    def test_bus_access_unmapped_address(self):
        bus = Bus()
        ram = RAM(16)
        bus.register_device(0x100, 0x10F, ram)

        with pytest.raises(IndexError, match="Address 0x0000 not mapped to any device."):
            bus.read(0x0000)
        with pytest.raises(IndexError, match="Address 0x0110 not mapped to any device."):
            bus.write(0x0110, 0xCC)

    # @intent:test_case_overlapping アドレス範囲の重複登録は許容されることを検証します（重複チェックは行われない）。
    # @intent:rationale ARCHITECTURE_MANIFEST.md にて重複チェックは呼び出し元責務とされているため、
    #                ここではクラッシュしないことを確認するに留める。
    def test_bus_overlapping_address_ranges(self):
        bus = Bus()
        ram1 = RAM(16)
        ram2 = RAM(16)

        bus.register_device(0x0000, 0x000F, ram1)
        bus.register_device(0x0005, 0x0014, ram2) # ram1と一部重複

        # どちらのデバイスが応答するかは登録順または内部実装に依存するが、
        # ここではエラーなく登録・アクセスできることを確認。
        bus.write(0x0007, 0xDD)
        assert bus.read(0x0007) == 0xDD

    # @intent:test_case_invalid_range 無効なアドレス範囲でデバイスを登録しようとするとValueErrorが発生することを検証します。
    def test_bus_register_invalid_address_range(self):
        bus = Bus()
        ram = RAM(16)
        with pytest.raises(ValueError, match="Invalid address range: start_address must be <= end_address and non-negative."):
            bus.register_device(0x0010, 0x000F, ram)
        with pytest.raises(ValueError, match="Invalid address range: start_address must be <= end_address and non-negative."):
            bus.register_device(-1, 0x000F, ram)

    # @intent:test_case_mismatch_size RAMデバイスのサイズが登録範囲と一致しない場合にValueErrorが発生することを検証します。
    def test_bus_register_ram_size_mismatch(self):
        bus = Bus()
        ram = RAM(10) # 10バイトのRAM
        with pytest.raises(ValueError, match="Registered RAM device size \(10 bytes\) does not match the specified address range size \(16 bytes\)."):
            bus.register_device(0x0000, 0x000F, ram) # 16バイトの範囲

    # @intent:test_case_invalid_device 無効な型のオブジェクトをデバイスとして登録しようとするとTypeErrorが発生することを検証します。
    def test_bus_register_invalid_device_type(self):
        bus = Bus()
        class MyClass: pass # Deviceを継承していない
        with pytest.raises(TypeError, match="Device must be an instance of a class derived from Device."):
            bus.register_device(0x0000, 0x000F, MyClass())

    # @intent:test_case_read_write_multiple_devices 複数のデバイスにまたがる読み書きを検証します。
    def test_bus_read_write_multiple_devices(self):
        bus = Bus()
        ram_a = RAM(10)
        ram_b = RAM(10)
        bus.register_device(0x0000, 0x0009, ram_a)
        bus.register_device(0x0010, 0x0019, ram_b)

        bus.write(0x0005, 0xA5)
        bus.write(0x0015, 0x5A)

        assert bus.read(0x0005) == 0xA5
        assert bus.read(0x0015) == 0x5A

    # @intent:test_case_log バスのアクティビティログが操作順に記録され、取得時にクリアされることを検証します。
    def test_bus_activity_log_order_and_clear(self):
        from retro_core_tracer.transport.bus import BusAccessType
        
        bus = Bus()
        ram = RAM(16)
        bus.register_device(0x0000, 0x000F, ram)

        # 1. Write 0xAA to 0x0005
        bus.write(0x0005, 0xAA)
        # 2. Read from 0x0005 (expect 0xAA)
        val = bus.read(0x0005)
        # 3. Write 0xBB to 0x000A
        bus.write(0x000A, 0xBB)

        # ログを取得
        log = bus.get_and_clear_activity_log()

        # ログの件数と順序を確認
        assert len(log) == 3
        
        # 1. Write
        assert log[0].address == 0x0005
        assert log[0].data == 0xAA
        assert log[0].access_type == BusAccessType.WRITE
        
        # 2. Read
        assert log[1].address == 0x0005
        assert log[1].data == 0xAA
        assert log[1].access_type == BusAccessType.READ
        
        # 3. Write
        assert log[2].address == 0x000A
        assert log[2].data == 0xBB
        assert log[2].access_type == BusAccessType.WRITE

        # ログがクリアされていることを確認
        log_after = bus.get_and_clear_activity_log()
        assert len(log_after) == 0
