# tests/arch/z80/test_cpu.py
"""
retro_core_tracer.arch.z80.cpuモジュールの単体テスト。
Z80Cpuの基本的なフェッチ、デコード、実行サイクルを検証します。
"""
import pytest

from retro_core_tracer.transport.bus import Bus, RAM
from retro_core_tracer.arch.z80.cpu import Z80Cpu
from retro_core_tracer.arch.z80.state import Z80CpuState
from retro_core_tracer.core.snapshot import Operation, Snapshot, Metadata

# @intent:test_suite Z80 CPUの基本機能（初期化、フェッチ、デコード、実行スタブ）を検証します。

class TestZ80Cpu:
    """
    Z80Cpuの単体テスト。
    """

    @pytest.fixture
    def setup_z80_cpu(self):
        bus = Bus()
        # 64KB RAMをバスに接続 (Z80のアドレス空間)
        ram = RAM(0x10000) # 0x0000 - 0xFFFF
        bus.register_device(0x0000, 0xFFFF, ram)
        cpu = Z80Cpu(bus)
        return cpu, bus, ram

    # @intent:test_case_init Z80CpuがZ80CpuStateで正しく初期化されることを検証します。
    def test_z80_cpu_init(self, setup_z80_cpu):
        cpu, _, _ = setup_z80_cpu
        state = cpu.get_state()
        assert isinstance(state, Z80CpuState)
        assert state.pc == 0x0000
        assert state.sp == 0x0000
        # Z80CpuStateの他のデフォルト値も確認できるが、test_state.pyで網羅済み

    # @intent:test_case_reset CPUがリセット時に初期状態に戻ることを検証します。
    def test_z80_cpu_reset(self, setup_z80_cpu):
        cpu, bus, ram = setup_z80_cpu
        # 状態を変更
        cpu.get_state().pc = 0x1234
        cpu.get_state().a = 0xFF
        cpu.get_state().flag_z = True

        cpu.reset()
        state = cpu.get_state()
        assert state.pc == 0x0000 # 初期値に戻る
        assert state.a == 0x00
        assert state.flag_z == False

    # @intent:test_case_fetch _fetchメソッドがRAMからオペコードを読み込み、PCをインクリメントすることを検証します。
    def test_z80_cpu_fetch(self, setup_z80_cpu):
        cpu, bus, ram = setup_z80_cpu
        initial_pc = 0x1000
        cpu.get_state().pc = initial_pc
        test_opcode = 0xCD # CALL instruction

        bus.write(initial_pc, test_opcode) # PCの位置にオペコードを書き込む

        fetched_opcode = cpu._fetch()

        assert fetched_opcode == test_opcode
        assert cpu.get_state().pc == initial_pc # _fetchはPCをインクリメントしない

    # @intent:test_case_decode _decodeメソッドがオペコードをOperationオブジェクトに変換することを検証します。
    def test_z80_cpu_decode(self, setup_z80_cpu):
        cpu, bus, _ = setup_z80_cpu
        pc_for_decode = 0x0010
        cpu.get_state().pc = pc_for_decode # PCはdecode_opcodeのオペランド読み込みに使用される

        # NOP (0x00)
        op_nop = cpu._decode(0x00)
        assert op_nop.opcode_hex == "00"
        assert op_nop.mnemonic == "NOP"
        assert op_nop.operands == []
        assert op_nop.cycle_count == 4
        assert op_nop.length == 1

        # HALT (0x76)
        op_halt = cpu._decode(0x76)
        assert op_halt.opcode_hex == "76"
        assert op_halt.mnemonic == "HALT"
        assert op_halt.operands == []
        assert op_halt.cycle_count == 4
        assert op_halt.length == 1

        # LD A,n (0x3E) - 2バイト命令
        n_value = 0x55
        bus.write(pc_for_decode + 1, n_value) # オペランドをバスに書き込む
        op_ld_a_n = cpu._decode(0x3E)
        assert op_ld_a_n.opcode_hex == "3E"
        assert op_ld_a_n.mnemonic == "LD A,n"
        assert op_ld_a_n.operands == [f"${n_value:02X}"]
        assert op_ld_a_n.cycle_count == 7
        assert op_ld_a_n.length == 2

        # LD HL,nn (0x21) - 3バイト命令
        nn_low = 0x34
        nn_high = 0x12
        bus.write(pc_for_decode + 1, nn_low)
        bus.write(pc_for_decode + 2, nn_high)
        op_ld_hl_nn = cpu._decode(0x21)
        assert op_ld_hl_nn.opcode_hex == "21"
        assert op_ld_hl_nn.mnemonic == "LD HL,nn"
        assert op_ld_hl_nn.operands == [f"${(nn_high << 8) | nn_low:04X}"]
        assert op_ld_hl_nn.cycle_count == 10
        assert op_ld_hl_nn.length == 3

        # Unknown opcode
        op_unknown = cpu._decode(0xFF)
        assert op_unknown.opcode_hex == "FF"
        assert op_unknown.mnemonic == "UNKNOWN"
        assert op_unknown.operands == ["$FF"]
        assert op_unknown.cycle_count == 4
        assert op_unknown.length == 1

    # @intent:test_case_execute _executeメソッドが現在はスタブであり、エラーなく実行されることを検証します。
    def test_z80_cpu_execute_ld_a_n(self, setup_z80_cpu):
        cpu, bus, _ = setup_z80_cpu
        n_value = 0xAA
        # operation.operand_bytesに値を設定するため、_decodeを通す必要がある
        bus.write(0x0001, n_value) # 読み取り用にバスに書き込む
        op_ld_a_n = cpu._decode(0x3E) # LD A,n

        cpu.get_state().a = 0x00 # 初期値を設定
        cpu._execute(op_ld_a_n) # 実行

        assert cpu.get_state().a == n_value # レジスタAが正しく設定されたことを確認

    # @intent:test_case_execute_ld_hl_nn _executeメソッドがLD HL,nn命令を正しく実行することを検証します。
    def test_z80_cpu_execute_ld_hl_nn(self, setup_z80_cpu):
        cpu, bus, _ = setup_z80_cpu
        nn_low = 0x34
        nn_high = 0x12
        # operation.operand_bytesに値を設定するため、_decodeを通す必要がある
        bus.write(0x0001, nn_low)
        bus.write(0x0002, nn_high)
        op_ld_hl_nn = cpu._decode(0x21) # LD HL,nn

        cpu.get_state().hl = 0x0000 # 初期値を設定
        cpu._execute(op_ld_hl_nn) # 実行

        assert cpu.get_state().hl == 0x1234 # レジスタHLが正しく設定されたことを確認

    # @intent:test_case_step stepメソッドがフェッチ、デコード、実行をオーケストレートし、Snapshotを返すことを検証します。
    def test_z80_cpu_step(self, setup_z80_cpu):
        cpu, bus, ram = setup_z80_cpu
        initial_pc = 0x2000
        cpu.get_state().pc = initial_pc

        # RAMにオペコードシーケンスを書き込む
        # NOP (1バイト)
        bus.write(initial_pc, 0x00)
        # HALT (1バイト)
        bus.write(initial_pc + 1, 0x76)
        # LD A,n (2バイト: 0x3E, 0xAA)
        bus.write(initial_pc + 2, 0x3E)
        bus.write(initial_pc + 3, 0xAA)
        # LD HL,nn (3バイト: 0x21, 0x34, 0x12)
        bus.write(initial_pc + 4, 0x21)
        bus.write(initial_pc + 5, 0x34)
        bus.write(initial_pc + 6, 0x12)
        # UNKNOWN (1バイト)
        bus.write(initial_pc + 7, 0xFF)


        # 1ステップ目: NOP
        snapshot1 = cpu.step()
        assert cpu.get_state().pc == initial_pc + 1 # PCは1バイト進む
        assert snapshot1.operation.mnemonic == "NOP"
        assert isinstance(snapshot1, Snapshot)
        assert snapshot1.state == cpu.get_state()
        assert snapshot1.metadata.symbol_info == "NOP"
        assert snapshot1.metadata.cycle_count == 4 # 累積: 4

        # 2ステップ目: HALT
        snapshot2 = cpu.step()
        assert cpu.get_state().pc == initial_pc + 2 # PCは1バイト進む
        assert snapshot2.operation.mnemonic == "HALT"
        assert isinstance(snapshot2, Snapshot)
        assert snapshot2.state == cpu.get_state()
        assert snapshot2.metadata.symbol_info == "HALT"
        assert snapshot2.metadata.cycle_count == 8 # 累積: 4 + 4 = 8

        # HALT状態を解除 (割り込み発生などをシミュレート)
        cpu.get_state().halted = False

        # 3ステップ目: LD A,n
        snapshot3 = cpu.step()
        assert cpu.get_state().pc == initial_pc + 4 # PCは2バイト進む
        assert snapshot3.operation.mnemonic == "LD A,n"
        assert snapshot3.operation.operands == ["$AA"]
        assert cpu.get_state().a == 0xAA # レジスタAが更新されていることを確認
        assert isinstance(snapshot3, Snapshot)
        assert snapshot3.state == cpu.get_state()
        assert snapshot3.metadata.symbol_info == "LD A,n $AA"
        assert snapshot3.metadata.cycle_count == 15 # 累積: 8 + 7 = 15

        # 4ステップ目: LD HL,nn
        snapshot4 = cpu.step()
        assert cpu.get_state().pc == initial_pc + 7 # PCは3バイト進む
        assert snapshot4.operation.mnemonic == "LD HL,nn"
        assert snapshot4.operation.operands == ["$1234"]
        assert cpu.get_state().hl == 0x1234 # レジスタHLが更新されていることを確認
        assert isinstance(snapshot4, Snapshot)
        assert snapshot4.state == cpu.get_state()
        assert snapshot4.metadata.symbol_info == "LD HL,nn $1234"
        assert snapshot4.metadata.cycle_count == 25 # 累積: 15 + 10 = 25

        # 5ステップ目: UNKNOWN
        snapshot5 = cpu.step()
        assert cpu.get_state().pc == initial_pc + 8 # PCは1バイト進む
        assert snapshot5.operation.mnemonic == "UNKNOWN"
        assert snapshot5.operation.operands == ["$FF"]
        assert isinstance(snapshot5, Snapshot)
        assert snapshot5.state == cpu.get_state()
        assert snapshot5.metadata.symbol_info == "UNKNOWN $FF"
        assert snapshot5.metadata.cycle_count == 29 # 累積: 25 + 4 = 29
