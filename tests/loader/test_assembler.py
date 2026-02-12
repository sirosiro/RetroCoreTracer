import unittest
from retro_core_tracer.loader.assembler import Z80Assembler, Mc6800Assembler

class TestAssembler(unittest.TestCase):
    def test_z80_assembler_basic(self):
        assembler = Z80Assembler()
        lines = [
            "  LD A, 0x10",
            "  NOP",
            "LABEL: HALT"
        ]
        symbol_map, binary = assembler.assemble(lines)
        
        self.assertIn("LABEL", symbol_map)
        self.assertEqual(symbol_map["LABEL"], 3) # LD(2) + NOP(1) = 3
        
        # LD A, 0x10 -> 3E 10
        self.assertEqual(binary[0], (0, 0x3E))
        self.assertEqual(binary[1], (1, 0x10))
        # NOP -> 00
        self.assertEqual(binary[2], (2, 0x00))
        # HALT -> 76
        self.assertEqual(binary[3], (3, 0x76))

    def test_mc6800_assembler_basic(self):
        assembler = Mc6800Assembler()
        lines = [
            "  LDAA #$10",
            "  NOP",
            "START: BRA START"
        ]
        symbol_map, binary = assembler.assemble(lines)
        
        self.assertIn("START", symbol_map)
        self.assertEqual(symbol_map["START"], 3) # LDAA(2) + NOP(1) = 3
        
        # LDAA #$10 -> 86 10
        self.assertEqual(binary[0], (0, 0x86))
        self.assertEqual(binary[1], (1, 0x10))
        # NOP -> 01
        self.assertEqual(binary[2], (2, 0x01))
        # BRA -2 (FE) -> 20 FE
        self.assertEqual(binary[3], (3, 0x20))
        self.assertEqual(binary[4], (4, 0xFE))

if __name__ == '__main__':
    unittest.main()
