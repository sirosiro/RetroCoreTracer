import unittest
from retro_core_tracer.transport.bus import ROM

class TestROM(unittest.TestCase):
    def test_rom_read(self):
        rom = ROM(1024)
        rom.load_data(0, 0xAA)
        self.assertEqual(rom.read(0), 0xAA)

    def test_rom_write_ignored(self):
        rom = ROM(1024)
        rom.load_data(0, 0xAA)
        
        # Write should be ignored (or warn, but not raise exception in current implementation)
        rom.write(0, 0xBB)
        
        # Value should remain 0xAA
        self.assertEqual(rom.read(0), 0xAA)

    def test_rom_load_data(self):
        rom = ROM(1024)
        rom.load_data(100, 0x55)
        self.assertEqual(rom.read(100), 0x55)

if __name__ == '__main__':
    unittest.main()
