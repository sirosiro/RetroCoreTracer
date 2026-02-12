import unittest
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.mc6800.cpu import Mc6800Cpu
from retro_core_tracer.arch.mc6800.instructions import decode_opcode, execute_instruction

class TestMc6800ControlInstructions(unittest.TestCase):
    def setUp(self):
        self.bus = Bus()
        self.bus.register_device(0x0000, 0xFFFF, RAM(0x10000))
        self.cpu = Mc6800Cpu(self.bus)
        self.cpu.reset()
        self.state = self.cpu.get_state()

    def _execute(self, opcode, operands, current_pc=0x1000):
        self.bus.write(current_pc, opcode)
        for i, b in enumerate(operands):
            self.bus.write(current_pc + 1 + i, b)
        self.state.pc = current_pc
        
        op = decode_opcode(opcode, self.bus, current_pc)
        # Advance PC (Control instructions often calculate target relative to NEXT instruction)
        self.state.pc = (self.state.pc + op.length) & 0xFFFF
        execute_instruction(op, self.state, self.bus)

    def test_bra_forward(self):
        # BRA +$04
        # PC: 1000 -> Op(20), 1001 -> Rel(04)
        # Next PC: 1002
        # Target: 1002 + 04 = 1006
        self._execute(0x20, [0x04], current_pc=0x1000)
        self.assertEqual(self.state.pc, 0x1006)

    def test_bra_backward(self):
        # BRA -$02 (FE)
        # PC: 1000 -> Op(20), 1001 -> Rel(FE)
        # Next PC: 1002
        # Target: 1002 - 2 = 1000 (Infinite Loop)
        self._execute(0x20, [0xFE], current_pc=0x1000)
        self.assertEqual(self.state.pc, 0x1000)

    def test_bne_taken(self):
        self.state.flag_z = False
        # BNE +$04
        self._execute(0x26, [0x04], current_pc=0x1000)
        self.assertEqual(self.state.pc, 0x1006)

    def test_bne_not_taken(self):
        self.state.flag_z = True
        # BNE +$04 (Should not branch)
        self._execute(0x26, [0x04], current_pc=0x1000)
        self.assertEqual(self.state.pc, 0x1002) # Just next instruction

    def test_jsr_rts(self):
        self.state.sp = 0x01FF
        
        # JSR $2000
        # PC: 1000 (BD 20 00) -> Length 3 -> Next 1003
        self._execute(0xBD, [0x20, 0x00], current_pc=0x1000)
        
        self.assertEqual(self.state.pc, 0x2000)
        
        # Check Stack (Should contain return address 0x1003)
        # Pushed: Low then High (Wait, M6800 pushes Low, then High? Or High then Low?)
        # Let's check implementation: 
        # write(sp, low); sp--; write(sp, high); sp--
        # So SP+1 is High, SP+2 is Low.
        
        high = self.bus.read((self.state.sp + 1) & 0xFFFF)
        low = self.bus.read((self.state.sp + 2) & 0xFFFF)
        return_addr = (high << 8) | low
        self.assertEqual(return_addr, 0x1003)

        # RTS
        self._execute(0x39, [], current_pc=0x2000)
        self.assertEqual(self.state.pc, 0x1003)
        self.assertEqual(self.state.sp, 0x01FF)

    def test_nop(self):
        self._execute(0x01, [], current_pc=0x1000)
        self.assertEqual(self.state.pc, 0x1001)

if __name__ == '__main__':
    unittest.main()
