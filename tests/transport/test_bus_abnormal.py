import unittest
from retro_core_tracer.transport.bus import Bus, RAM

class TestBusAbnormal(unittest.TestCase):
    def setUp(self):
        self.bus = Bus()
        self.bus.register_device(0x0000, 0x0FFF, RAM(0x1000)) # 4KB RAM

    def test_read_out_of_bounds(self):
        # Access unmapped memory (0x2000)
        with self.assertRaises(IndexError):
            self.bus.read(0x2000)

    def test_write_out_of_bounds(self):
        with self.assertRaises(IndexError):
            self.bus.write(0x2000, 0xFF)

    def test_ram_invalid_init(self):
        with self.assertRaises(ValueError):
            RAM(-1)
        with self.assertRaises(ValueError):
            RAM(0)

    def test_register_device_invalid_range(self):
        # Start > End
        with self.assertRaises(ValueError):
            self.bus.register_device(0x2000, 0x1000, RAM(0x100))
        
        # Negative address
        with self.assertRaises(ValueError):
            self.bus.register_device(-1, 0x100, RAM(0x100))

    def test_register_device_size_mismatch(self):
        # Range size 0x100 (256), but RAM size 0x200 (512)
        with self.assertRaises(ValueError):
            self.bus.register_device(0x1000, 0x10FF, RAM(0x200))

if __name__ == '__main__':
    unittest.main()
