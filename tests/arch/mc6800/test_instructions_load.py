import unittest
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from retro_core_tracer.arch.mc6800.instructions import decode_opcode, execute_instruction

class TestMc6800LoadInstructions(unittest.TestCase):
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
        # Advance PC before execution as per step() logic
        self.state.pc += op.length 
        execute_instruction(op, self.state, self.bus)

    def test_ldaa_imm(self):
        # LDAA #$55 (Negative=0, Zero=0)
        self._execute(0x86, [0x55])
        self.assertEqual(self.state.a, 0x55)
        self.assertFalse(self.state.flag_n)
        self.assertFalse(self.state.flag_z)
        self.assertFalse(self.state.flag_v)

        # LDAA #$00 (Zero=1)
        self._execute(0x86, [0x00])
        self.assertEqual(self.state.a, 0x00)
        self.assertTrue(self.state.flag_z)
        self.assertFalse(self.state.flag_n)

        # LDAA #$80 (Negative=1)
        self._execute(0x86, [0x80])
        self.assertEqual(self.state.a, 0x80)
        self.assertTrue(self.state.flag_n)
        self.assertFalse(self.state.flag_z)

    def test_ldaa_extended(self):
        # Memory setup
        self.bus.write(0x2000, 0xAA)
        
        # LDAA $2000
        self._execute(0xB6, [0x20, 0x00])
        self.assertEqual(self.state.a, 0xAA)
        self.assertTrue(self.state.flag_n)

    def test_ldab_imm(self):
        # LDAB #$CC
        self._execute(0xC6, [0xCC])
        self.assertEqual(self.state.b, 0xCC)
        self.assertTrue(self.state.flag_n)

    def test_staa_extended(self):
        self.state.a = 0x77
        # STAA $3000
        self._execute(0xB7, [0x30, 0x00])
        self.assertEqual(self.bus.read(0x3000), 0x77)
        self.assertFalse(self.state.flag_n)
        self.assertFalse(self.state.flag_z)
        self.assertFalse(self.state.flag_v)

    def test_ldx_imm(self):
        # LDX #$1234
        self._execute(0xCE, [0x12, 0x34])
        self.assertEqual(self.state.x, 0x1234)
        self.assertFalse(self.state.flag_z)
        self.assertFalse(self.state.flag_n) # 0x1234 is positive as 16bit signed

        # LDX #$0000
        self._execute(0xCE, [0x00, 0x00])
        self.assertEqual(self.state.x, 0x0000)
        self.assertTrue(self.state.flag_z)

    def test_push_pull_a(self):
        self.state.sp = 0x01FF
        self.state.a = 0x42
        
        # PSHA
        self._execute(0x36, [])
        self.assertEqual(self.bus.read(0x01FF), 0x42)
        self.assertEqual(self.state.sp, 0x01FE)
        
        self.state.a = 0x00
        # PULA
        self._execute(0x32, [])
        self.assertEqual(self.state.a, 0x42)
        self.assertEqual(self.state.sp, 0x01FF)

if __name__ == '__main__':
    unittest.main()
