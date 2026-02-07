# tests/arch/z80/test_instructions_cb.py
import pytest
from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.z80.state import Z80CpuState

class TestCbInstructions:
    @pytest.fixture
    def setup_cpu(self):
        bus = Bus()
        ram = RAM(0x10000)
        bus.register_device(0x0000, 0xFFFF, ram)
        cpu = Z80Cpu(bus)
        return cpu, bus

    def test_bit_instruction(self, setup_cpu):
        cpu, bus = setup_cpu
        # BIT 0, A (0xCB 0x47)
        bus.write(0x0000, 0xCB)
        bus.write(0x0001, 0x47)
        
        # Case 1: Bit 0 is 0
        cpu.get_state().a = 0xFE # 1111 1110
        cpu.step()
        assert cpu.get_state().flag_z is True
        assert cpu.get_state().flag_h is True # BIT always sets H
        assert cpu.get_state().flag_n is False
        
        # Case 2: Bit 0 is 1
        cpu.get_state().pc = 0x0000
        cpu.get_state().a = 0x01 # 0000 0001
        cpu.step()
        assert cpu.get_state().flag_z is False

    def test_set_res_instruction(self, setup_cpu):
        cpu, bus = setup_cpu
        # SET 7, B (0xCB 0xF8)
        bus.write(0x0000, 0xCB)
        bus.write(0x0001, 0xF8)
        cpu.get_state().b = 0x00
        cpu.step()
        assert cpu.get_state().b == 0x80

        # RES 7, B (0xCB 0xB8)
        bus.write(0x0002, 0xCB)
        bus.write(0x0003, 0xB8)
        cpu.step()
        assert cpu.get_state().b == 0x00

    def test_rotate_rlc_a(self, setup_cpu):
        cpu, bus = setup_cpu
        # RLC A (0xCB 0x07)
        bus.write(0x0000, 0xCB)
        bus.write(0x0001, 0x07)
        
        # 1000 0001 -> 0000 0011, Carry=1
        cpu.get_state().a = 0x81
        cpu.step()
        assert cpu.get_state().a == 0x03
        assert cpu.get_state().flag_c is True
        assert cpu.get_state().flag_z is False

    def test_shift_sla_b(self, setup_cpu):
        cpu, bus = setup_cpu
        # SLA B (0xCB 0x20)
        bus.write(0x0000, 0xCB)
        bus.write(0x0001, 0x20)
        
        # 1000 0000 -> 0000 0000, Carry=1, Z=1
        cpu.get_state().b = 0x80
        cpu.step()
        assert cpu.get_state().b == 0x00
        assert cpu.get_state().flag_c is True
        assert cpu.get_state().flag_z is True

class TestEdInstructions:
    @pytest.fixture
    def setup_cpu(self):
        bus = Bus()
        ram = RAM(0x10000)
        bus.register_device(0x0000, 0xFFFF, ram)
        cpu = Z80Cpu(bus)
        return cpu, bus

    def test_ldi_instruction(self, setup_cpu):
        cpu, bus = setup_cpu
        # LDI (0xED 0xA0)
        bus.write(0x0000, 0xED)
        bus.write(0x0001, 0xA0)
        
        cpu.get_state().hl = 0x1000
        cpu.get_state().de = 0x2000
        cpu.get_state().bc = 0x0005
        bus.write(0x1000, 0xAA)
        
        cpu.step()
        
        assert bus.read(0x2000) == 0xAA
        assert cpu.get_state().hl == 0x1001
        assert cpu.get_state().de == 0x2001
        assert cpu.get_state().bc == 0x0004
        assert cpu.get_state().flag_pv is True # BC != 0

    def test_ldir_instruction(self, setup_cpu):
        cpu, bus = setup_cpu
        # LDIR (0xED 0xB0)
        bus.write(0x0000, 0xED)
        bus.write(0x0001, 0xB0)
        
        cpu.get_state().hl = 0x1000
        cpu.get_state().de = 0x2000
        cpu.get_state().bc = 0x0002 # 2 bytes to transfer
        bus.write(0x1000, 0x11)
        bus.write(0x1001, 0x22)
        
        # 1st step: transfer 0x11, PC goes back
        cpu.step()
        assert bus.read(0x2000) == 0x11
        assert cpu.get_state().pc == 0x0000 # Repeated
        assert cpu.get_state().bc == 0x0001
        
        # 2nd step: transfer 0x22, PC goes forward
        cpu.step()
        assert bus.read(0x2001) == 0x22
        assert cpu.get_state().pc == 0x0002 # Finished
        assert cpu.get_state().bc == 0x0000
        assert cpu.get_state().flag_pv is False # BC == 0

class TestIoInstructions:
    @pytest.fixture
    def setup_cpu(self):
        bus = Bus()
        ram = RAM(0x10000)
        bus.register_device(0x0000, 0xFFFF, ram)
        cpu = Z80Cpu(bus)
        return cpu, bus

    def test_in_out_instructions(self, setup_cpu):
        cpu, bus = setup_cpu
        from retro_core_tracer.transport.bus import BusAccessType

        # OUT (0x10), A (0xD3 0x10)
        bus.write(0x0000, 0xD3)
        bus.write(0x0001, 0x10)
        cpu.get_state().a = 0x55
        
        snapshot = cpu.step()
        
        # ログにIO_WRITEが記録されていることを確認
        found_io_write = False
        for access in snapshot.bus_activity:
            if access.access_type == BusAccessType.IO_WRITE and access.address == 0x5510: # (A << 8 | port)
                found_io_write = True
                break
        assert found_io_write

        # IN A, (0x20) (0xDB 0x20)
        bus.write(0x0002, 0xDB)
        bus.write(0x0003, 0x20)
        # Note: read_io currently returns 0x00
        cpu.step()
        assert cpu.get_state().a == 0x00

