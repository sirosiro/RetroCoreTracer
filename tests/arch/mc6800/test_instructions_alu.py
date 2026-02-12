import unittest
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from retro_core_tracer.arch.mc6800.instructions import decode_opcode, execute_instruction

class TestMc6800AluInstructions(unittest.TestCase):
    def setUp(self):
        self.bus = Bus()
        self.bus.register_device(0x0000, 0xFFFF, RAM(0x10000))
        self.cpu = Mc6800Cpu(self.bus)
        self.cpu.reset()
        self.state = self.cpu.get_state()

    def _execute(self, opcode, operands):
        self.bus.write(0x0000, opcode)
        for i, b in enumerate(operands):
            self.bus.write(0x0001 + i, b)
        self.state.pc = 0x0000
        
        op = decode_opcode(opcode, self.bus, 0x0000)
        self.state.pc += op.length 
        execute_instruction(op, self.state, self.bus)

    def test_adda_imm(self):
        self.state.a = 0x10
        # ADDA #$20
        self._execute(0x8B, [0x20])
        self.assertEqual(self.state.a, 0x30)
        self.assertFalse(self.state.flag_n)
        self.assertFalse(self.state.flag_z)
        self.assertFalse(self.state.flag_v)
        self.assertFalse(self.state.flag_c)
        self.assertFalse(self.state.flag_h)

    def test_adda_overflow(self):
        self.state.a = 0x7F # +127
        # ADDA #$01 -> 0x80 (-128) -> Overflow!
        self._execute(0x8B, [0x01])
        self.assertEqual(self.state.a, 0x80)
        self.assertTrue(self.state.flag_n)
        self.assertTrue(self.state.flag_v) # Signed overflow
        self.assertFalse(self.state.flag_c) # No unsigned carry
        self.assertTrue(self.state.flag_h) # 0x7F(01111111) + 0x01(00000001) -> Half carry at bit 3

    def test_suba_imm(self):
        self.state.a = 0x10
        # SUBA #$05
        self._execute(0x80, [0x05])
        self.assertEqual(self.state.a, 0x0B)
        self.assertFalse(self.state.flag_n)
        self.assertFalse(self.state.flag_z)

    def test_suba_negative(self):
        self.state.a = 0x05
        # SUBA #$10 -> 0xF5 (-11)
        self._execute(0x80, [0x10])
        self.assertEqual(self.state.a, 0xF5)
        self.assertTrue(self.state.flag_n)
        self.assertTrue(self.state.flag_c) # Borrow

    def test_anda_imm(self):
        self.state.a = 0xAA # 10101010
        # ANDA #$0F
        self._execute(0x84, [0x0F])
        self.assertEqual(self.state.a, 0x0A) # 00001010
        self.assertFalse(self.state.flag_n)
        self.assertFalse(self.state.flag_z)
        self.assertFalse(self.state.flag_v)

    def test_cmpa_imm(self):
        self.state.a = 0x10
        # CMPA #$10
        self._execute(0x81, [0x10])
        self.assertEqual(self.state.a, 0x10) # A should not change
        self.assertTrue(self.state.flag_z)
        self.assertFalse(self.state.flag_n)

    def test_incb(self):
        self.state.b = 0x00
        # INCB
        self._execute(0x5C, [])
        self.assertEqual(self.state.b, 0x01)
        self.assertFalse(self.state.flag_z)
        self.assertFalse(self.state.flag_v)

        self.state.b = 0x7F
        self._execute(0x5C, [])
        self.assertEqual(self.state.b, 0x80)
        self.assertTrue(self.state.flag_n)
        self.assertTrue(self.state.flag_v) # Overflow

if __name__ == '__main__':
    unittest.main()
