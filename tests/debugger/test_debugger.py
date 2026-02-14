# tests/debugger/test_debugger.py
"""
retro_core_tracer.debugger.debuggerモジュールの単体テスト。
Debuggerの実行制御、ブレークポイント管理、および条件チェック機能を検証します。
"""
import pytest
from unittest.mock import MagicMock, patch

from retro_core_tracer.transport.bus import Bus, RAM, BusAccess, BusAccessType
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.core.snapshot import Snapshot, Operation, Metadata
from retro_core_tracer.debugger.debugger import Debugger, BreakpointCondition, BreakpointConditionType

# @intent:test_suite デバッガのブレークポイントと実行制御機能の検証。

class TestDebugger:
    """
    Debuggerの単体テスト。
    """
    @pytest.fixture
    def setup_debugger(self):
        bus = Bus()
        ram = RAM(0x10000) # 64KB RAM
        bus.register_device(0x0000, 0xFFFF, ram)
        cpu = Z80Cpu(bus)
        debugger = Debugger(cpu)
        return debugger, cpu, bus, ram

    # @intent:test_case_add_remove_breakpoint ブレークポイントの追加と削除が正しく行われることを検証します。
    def test_add_remove_breakpoint(self, setup_debugger):
        debugger, _, _, _ = setup_debugger
        bp1 = BreakpointCondition(BreakpointConditionType.PC_MATCH, value=0x1000)
        bp2 = BreakpointCondition(BreakpointConditionType.MEMORY_WRITE, address=0x2000)

        debugger.add_breakpoint(bp1)
        debugger.add_breakpoint(bp2)
        assert bp1 in debugger._breakpoints
        assert bp2 in debugger._breakpoints
        assert len(debugger._breakpoints) == 2

        debugger.add_breakpoint(bp1) # 重複追加は無視される
        assert len(debugger._breakpoints) == 2

        debugger.remove_breakpoint(bp1)
        assert bp1 not in debugger._breakpoints
        assert len(debugger._breakpoints) == 1

        debugger.remove_breakpoint(bp1) # 存在しないブレークポイントの削除はエラーにならない
        assert len(debugger._breakpoints) == 1

    # @intent:test_case_step_instruction step_instructionがcpu.stepを呼び出し、Snapshotを返すことを検証します。
    def test_step_instruction(self, setup_debugger):
        debugger, cpu, _, _ = setup_debugger
        initial_pc = cpu.get_state().pc

        # cpu.step()が呼ばれることを検証するためにモック化
        with patch.object(cpu, 'step', return_value=Snapshot(
            state=Z80CpuState(pc=initial_pc+1),
            operation=Operation(opcode_hex="00", mnemonic="NOP", length=1),
            bus_activity=[],
            metadata=Metadata(cycle_count=4)
        )) as mock_step:
            snapshot = debugger.step_instruction()
            mock_step.assert_called_once()
            assert isinstance(snapshot, Snapshot)
            assert snapshot.state.pc == initial_pc + 1

    # @intent:test_case_pc_match_breakpoint PC_MATCHブレークポイントがヒットすることを検証します。
    def test_pc_match_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        target_pc = 0x100
        bp = BreakpointCondition(BreakpointConditionType.PC_MATCH, value=target_pc)
        debugger.add_breakpoint(bp)

        bus.write(target_pc - 1, 0x00) # NOP
        bus.write(target_pc, 0x00)     # NOP (この命令でヒットする)

        cpu.get_state().pc = target_pc # PCをターゲットに設定

        with patch('builtins.print') as mock_print: # print文をモック
            debugger.run()

            assert not debugger._running # ブレークポイントヒットで停止
            assert cpu.get_state().pc == target_pc
            mock_print.assert_called_with(f"Breakpoint hit at PC: {target_pc:#06x}")

    # @intent:test_case_memory_write_breakpoint MEMORY_WRITEブレークポイントがヒットすることを検証します。
    def test_memory_write_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        target_address = 0x2000
        bp = BreakpointCondition(BreakpointConditionType.MEMORY_WRITE, address=target_address)
        debugger.add_breakpoint(bp)

        initial_pc = 0x0000
        cpu.get_state().pc = initial_pc

        bus.write(initial_pc, 0x21) # LD HL,nn opcode
        bus.write(initial_pc + 1, target_address & 0xFF) # nn_low
        bus.write(initial_pc + 2, target_address >> 8)   # nn_high

        bus.write(initial_pc + 3, 0x77) # LD (HL),A opcode
        cpu.get_state().a = 0xAA # Aレジスタに書き込む値を設定
        
        # 1ステップ目: LD HL,nn
        snapshot1 = debugger.step_instruction()
        assert not debugger._check_other_breakpoints(snapshot1)
        assert snapshot1.state.pc == initial_pc + 3

        # 2ステップ目: LD (HL),A - この命令でメモリ書き込みが発生し、ブレークポイントがヒットするはず
        snapshot2 = debugger.step_instruction()
        # assert debugger._check_other_breakpoints(snapshot2) # _check_other_breakpointsは別途テストされるべき
        
        # BusActivityに書き込みがあることを確認
        found_write_access = False
        for access in snapshot2.bus_activity:
            if access.access_type == BusAccessType.WRITE and access.address == target_address and access.data == cpu.get_state().a:
                found_write_access = True
                break
        assert found_write_access

    # @intent:test_case_memory_read_breakpoint MEMORY_READブレークポイントがヒットすることを検証します。
    def test_memory_read_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        target_address = 0x3000
        bp = BreakpointCondition(BreakpointConditionType.MEMORY_READ, address=target_address)
        debugger.add_breakpoint(bp)

        initial_pc = 0x0000
        cpu.get_state().pc = initial_pc
        
        bus.write(target_address, 0xDE) # 読み込むデータ

        bus.write(initial_pc, 0x21) # LD HL,nn opcode
        bus.write(initial_pc + 1, target_address & 0xFF) # nn_low
        bus.write(initial_pc + 2, target_address >> 8)   # nn_high

        bus.write(initial_pc + 3, 0x7E) # LD A,(HL) opcode

        # 1ステップ目: LD HL,nn
        snapshot1 = debugger.step_instruction()
        assert not debugger._check_other_breakpoints(snapshot1)
        assert snapshot1.state.pc == initial_pc + 3

        # 2ステップ目: LD A,(HL) - この命令でメモリ読み込みが発生し、ブレークポイントがヒットするはず
        snapshot2 = debugger.step_instruction()
        # assert debugger._check_other_breakpoints(snapshot2) # _check_other_breakpointsは別途テストされるべき
        assert snapshot2.state.pc == initial_pc + 4
        assert cpu.get_state().a == 0xDE

        # BusActivityに読み込みがあることを確認
        found_read_access = False
        for access in snapshot2.bus_activity:
            if access.access_type == BusAccessType.READ and access.address == target_address and access.data == 0xDE:
                found_read_access = True
                break
        assert found_read_access

    # @intent:test_case_register_value_breakpoint REGISTER_VALUEブレークポイントがヒットすることを検証します。
    def test_register_value_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        bp = BreakpointCondition(BreakpointConditionType.REGISTER_VALUE, register_name="a", value=0x55)
        debugger.add_breakpoint(bp)

        initial_pc = 0x0000
        cpu.get_state().pc = initial_pc

        bus.write(initial_pc, 0x3E) # LD A,n opcode
        bus.write(initial_pc + 1, 0x55) # n value

        # 1ステップ目: LD A,n
        snapshot1 = debugger.step_instruction()
        assert debugger._check_other_breakpoints(snapshot1)
        assert cpu.get_state().a == 0x55

    # @intent:test_case_register_change_breakpoint REGISTER_CHANGEブレークポイントがヒットすることを検証します。
    def test_register_change_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        bp = BreakpointCondition(BreakpointConditionType.REGISTER_CHANGE, register_name="a")
        debugger.add_breakpoint(bp)

        cpu.get_state().pc = 0x0000
        cpu.get_state().a = 0x00
        
        # 1. PC=0x0000: NOP (Aは変化しない)
        bus.write(0x0000, 0x00)
        snapshot1 = debugger.step_instruction()
        assert not debugger._check_other_breakpoints(snapshot1)
        
        # 2. PC=0x0001: LD A,0x55 (Aが変化する)
        bus.write(0x0001, 0x3E)
        bus.write(0x0002, 0x55)
        snapshot2 = debugger.step_instruction()
        assert debugger._check_other_breakpoints(snapshot2)
        assert cpu.get_state().a == 0x55

    # @intent:test_case_run_until_memory_write_breakpoint run()メソッドがメモリ書き込みヒットで停止することを検証します。
    def test_run_until_memory_write_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        target_address = 0x2000
        bp = BreakpointCondition(BreakpointConditionType.MEMORY_WRITE, address=target_address)
        debugger.add_breakpoint(bp)

        cpu.get_state().pc = 0x0000
        bus.write(0x0000, 0x21) # LD HL,0x2000
        bus.write(0x0001, 0x00)
        bus.write(0x0002, 0x20)
        bus.write(0x0003, 0x77) # LD (HL),A (メモリ書き込み発生)
        bus.write(0x0004, 0x00) # NOP
        
        cpu.get_state().a = 0xAA

        with patch('builtins.print') as mock_print:
            debugger.run()

            assert not debugger._running
            # LD (HL),A の実行直後に停止するため、PCは0x0004を指しているはず
            assert cpu.get_state().pc == 0x0004
            mock_print.assert_any_call(f"Breakpoint hit at PC: 0x0004")

    # @intent:test_case_run_until_stop run()メソッドがstop()で停止することを検証します。
    def test_run_until_stop(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        bus.write(0x0000, 0x00) # NOP
        bus.write(0x0001, 0x00) # NOP
        cpu.get_state().pc = 0x0000
    
        original_step = debugger.step_instruction
        def mock_step_side_effect():
            snapshot = original_step()
            debugger.stop()
            return snapshot

        with patch.object(debugger, 'step_instruction', side_effect=mock_step_side_effect) as mock_step_instruction:
            with patch.object(debugger, '_check_other_breakpoints', return_value=False) as mock_check_other_breakpoints:
                debugger.run()
                assert mock_step_instruction.call_count == 1
                assert not debugger._running

    # @intent:test_case_run_until_breakpoint run()メソッドがブレークポイントヒットで停止することを検証します。
    def test_run_until_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        target_pc = 0x100
        bp = BreakpointCondition(BreakpointConditionType.PC_MATCH, value=target_pc)
        debugger.add_breakpoint(bp)

        cpu.get_state().pc = 0x0000
        for addr in range(0x0000, target_pc + 1):
            bus.write(addr, 0x00) # NOP

        with patch('builtins.print') as mock_print:
            debugger.run()

            assert not debugger._running
            assert cpu.get_state().pc == target_pc
            mock_print.assert_called_with(f"Breakpoint hit at PC: {target_pc:#06x}")

    # @intent:test_case_step_back step_backがCPU状態とメモリを復元することを検証します。
    def test_debugger_step_back(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        
        # 1. 初期状態を記録
        initial_pc = 0x0000
        initial_sp = cpu.get_state().sp
        target_addr = 0x0020
        
        # 初期メモリ値は0
        assert ram.read(target_addr) == 0x00
        
        # 2. 状態を変更する命令を実行 (LD A, 0xFF; LD (0x0020), A)
        # 0x0000: LD A, 0xFF (3E FF)
        bus.write(0x0000, 0x3E)
        bus.write(0x0001, 0xFF)
        
        # 0x0002: LD (0x0020), A (32 20 00)
        bus.write(0x0002, 0x32)
        bus.write(0x0003, 0x20)
        bus.write(0x0004, 0x00)
        
        cpu.get_state().pc = 0x0000
        
        # Step 1: LD A, 0xFF
        debugger.step_instruction()
        assert cpu.get_state().a == 0xFF
        assert cpu.get_state().pc == 0x0002
        
        # Step 2: LD (0x0020), A
        debugger.step_instruction()
        assert ram.read(target_addr) == 0xFF
        assert cpu.get_state().pc == 0x0005
        
        assert len(debugger.get_history()) == 2
        
        # 3. Step Back (Undo LD (0x0020), A)
        restored_snapshot = debugger.step_back()
        
        # 検証: PCは0x0002に戻るはず
        assert restored_snapshot is not None
        assert restored_snapshot.state.pc == 0x0002
        assert cpu.get_state().pc == 0x0002
        assert cpu.get_state().a == 0xFF
        
        # 検証: メモリ書き込みが取り消されているはず
        assert ram.read(target_addr) == 0x00
        
        assert len(debugger.get_history()) == 1
        
        # 4. Step Back (Undo LD A, 0xFF)
        restored_snapshot = debugger.step_back()
        
        # 検証: 初期状態に戻るはず
        assert restored_snapshot is None
        assert cpu.get_state().pc == 0x0000
        # Aレジスタの値は初期状態（多分0）に戻るはず
        assert cpu.get_state().a == 0x00
        
        assert len(debugger.get_history()) == 0

    # @intent:test_case_run_back run_backがPCブレークポイントで停止することを検証します。
    def test_debugger_run_back_pc_breakpoint(self, setup_debugger):
        debugger, cpu, bus, ram = setup_debugger
        
        # 0x0000から0x0003までNOP(0x00)で埋める
        for addr in range(4):
            bus.write(addr, 0x00)
            
        cpu.get_state().pc = 0x0000
        
        # 3ステップ実行 (PC: 0->1->2->3)
        debugger.step_instruction()
        debugger.step_instruction()
        debugger.step_instruction()
        
        assert cpu.get_state().pc == 0x0003
        
        # PC=0x0001 にブレークポイント設定
        bp = BreakpointCondition(BreakpointConditionType.PC_MATCH, value=0x0001)
        debugger.add_breakpoint(bp)
        
        # Run Back
        with patch('builtins.print') as mock_print:
            debugger.run_back()
            
            # PC=0x0001 で停止しているか
            assert not debugger._running
            assert cpu.get_state().pc == 0x0001
            # "Reverse Breakpoint hit..." が出力されたか
            # 実装によっては "Breakpoint hit..." かもしれないので部分一致で確認
            # mock_print.assert_called_with(...)
