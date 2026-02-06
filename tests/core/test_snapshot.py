# tests/core/test_snapshot.py
"""
retro_core_tracer.core.snapshotモジュールの単体テスト。
"""
import pytest
from retro_core_tracer.core.cpu import CpuState
from retro_core_tracer.core.snapshot import (
    BusAccessType,
    BusAccess,
    Operation,
    Metadata,
    Snapshot,
)

# @intent:test_suite CPUとバスの状態を記録する不変スナップショットデータ構造の検証。

class TestBusAccessType:
    """
    BusAccessType enumの単体テスト。
    """
    # @intent:test_case_enum BusAccessTypeのメンバーが正しく定義されていることを検証します。
    def test_bus_access_type_members(self):
        assert BusAccessType.READ.value == "READ"
        assert BusAccessType.WRITE.value == "WRITE"

class TestBusAccess:
    """
    BusAccessデータクラスの単体テスト。
    """
    # @intent:test_case_init BusAccessが正しく初期化されることを検証します。
    def test_bus_access_init(self):
        access = BusAccess(address=0x1000, data=0xAA, access_type=BusAccessType.READ)
        assert access.address == 0x1000
        assert access.data == 0xAA
        assert access.access_type == BusAccessType.READ

    # @intent:test_case_immutability BusAccessが不変であることを検証します。
    def test_bus_access_immutability(self):
        access = BusAccess(address=0x1000, data=0xAA, access_type=BusAccessType.READ)
        with pytest.raises(AttributeError):
            access.address = 0x2000

class TestOperation:
    """
    Operationデータクラスの単体テスト。
    """
    # @intent:test_case_init_with_operands Operationがオペランド付きで正しく初期化されることを検証します。
    def test_operation_init_with_operands(self):
        op = Operation(opcode_hex="C3", mnemonic="JP", operands=["$1234"])
        assert op.opcode_hex == "C3"
        assert op.mnemonic == "JP"
        assert op.operands == ["$1234"]

    # @intent:test_case_init_no_operands Operationがオペランドなしで正しく初期化されることを検証します。
    def test_operation_init_no_operands(self):
        op = Operation(opcode_hex="NOP", mnemonic="NOP")
        assert op.opcode_hex == "NOP"
        assert op.mnemonic == "NOP"
        assert op.operands == [] # デフォルトで空リスト

    # @intent:test_case_immutability Operationが不変であることを検証します。
    def test_operation_immutability(self):
        op = Operation(opcode_hex="C3", mnemonic="JP")
        with pytest.raises(AttributeError):
            op.mnemonic = "CALL"
        # リスト自体は不変ではないので、中身の変更は可能だがdataclassのfrozen=Trueで保護されるべき
        # Python 3.7+のdataclasses.frozen=Trueは、フィールドがリスト型の場合、リストそのものの変更は防がない。
        # ただし、フィールドへの再代入は防ぐ。
        # このテストは再代入不可を検証。リスト内容の不変性は別途考慮が必要（field(default_factory=list, repr=False, hash=False)などで対応可能だが、今回はそこまで厳密にしない）
        op.operands.append("$5678") # これはエラーにならないが、frozenの意図とは異なる振る舞い。
        assert op.operands == ["$5678"] # 確認のため

class TestMetadata:
    """
    Metadataデータクラスの単体テスト。
    """
    # @intent:test_case_init_with_symbol Metadataがシンボル情報付きで正しく初期化されることを検証します。
    def test_metadata_init_with_symbol(self):
        meta = Metadata(cycle_count=10, symbol_info="main_loop")
        assert meta.cycle_count == 10
        assert meta.symbol_info == "main_loop"

    # @intent:test_case_init_no_symbol Metadataがシンボル情報なしで正しく初期化されることを検証します。
    def test_metadata_init_no_symbol(self):
        meta = Metadata(cycle_count=100)
        assert meta.cycle_count == 100
        assert meta.symbol_info is None # デフォルトでNone

    # @intent:test_case_immutability Metadataが不変であることを検証します。
    def test_metadata_immutability(self):
        meta = Metadata(cycle_count=10)
        with pytest.raises(AttributeError):
            meta.cycle_count = 20

class TestSnapshot:
    """
    Snapshotデータクラスの単体テスト。
    """
    # 共通のテストフィクスチャ
    @pytest.fixture
    def sample_data(self):
        state = CpuState(pc=0x100, sp=0xFF)
        operation = Operation(opcode_hex="76", mnemonic="HALT")
        bus_activity = [
            BusAccess(address=0x100, data=0x76, access_type=BusAccessType.READ),
        ]
        metadata = Metadata(cycle_count=4, symbol_info="start_halt")
        return state, operation, bus_activity, metadata

    # @intent:test_case_init Snapshotが正しく初期化されることを検証します。
    def test_snapshot_init(self, sample_data):
        state, operation, bus_activity, metadata = sample_data
        snapshot = Snapshot(state=state, operation=operation, bus_activity=bus_activity, metadata=metadata)

        assert snapshot.state == state
        assert snapshot.operation == operation
        assert snapshot.bus_activity == bus_activity
        assert snapshot.metadata == metadata

    # @intent:test_case_immutability Snapshotが不変であることを検証します。
    def test_snapshot_immutability(self, sample_data):
        state, operation, bus_activity, metadata = sample_data
        snapshot = Snapshot(state=state, operation=operation, bus_activity=bus_activity, metadata=metadata)

        with pytest.raises(AttributeError):
            snapshot.state = CpuState(pc=0x200, sp=0xEE)

        # bus_activityリスト自体はfrozen=Trueで再代入不可だが、リストの中身は変更可能（Pythonのdataclassesの仕様）
        # ただし、bus_activityの要素（BusAccess）自体はfrozen=Trueなので不変
        # このテストはSnapshotのフィールドへの再代入不可を検証。
        with pytest.raises(AttributeError):
            snapshot.bus_activity = []

    # @intent:test_case_default_factory_bus_activity default_factoryが正しく機能し、独立したリストインスタンスが生成されることを検証します。
    def test_snapshot_default_factory_bus_activity(self):
        state = CpuState()
        operation = Operation(opcode_hex="NOP", mnemonic="NOP")
        metadata = Metadata(cycle_count=1)

        snapshot1 = Snapshot(state=state, operation=operation, metadata=metadata)
        snapshot2 = Snapshot(state=state, operation=operation, metadata=metadata)

        # 異なるSnapshotインスタンスは、bus_activityの独立したリストインスタンスを持つべき
        assert snapshot1.bus_activity is not snapshot2.bus_activity
        assert snapshot1.bus_activity == []
        assert snapshot2.bus_activity == []

        # 一方のリストを変更しても、もう一方に影響を与えないこと
        snapshot1.bus_activity.append(BusAccess(address=0x0001, data=0x01, access_type=BusAccessType.READ))
        assert len(snapshot1.bus_activity) == 1
        assert len(snapshot2.bus_activity) == 0
