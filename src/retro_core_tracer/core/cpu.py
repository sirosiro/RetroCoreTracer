# retro_core_tracer/core/cpu.py
"""
Core Layer (抽象CPU)

このモジュールは、CPUの基本的な状態管理と命令サイクルの駆動に関する抽象化を提供します。
具体的な命令の振る舞いはInstruction Layerに移譲されます。
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Snapshot, Operation, Metadata
from retro_core_tracer.core.state import CpuState

# @intent:responsibility 抽象CPUの基本機能とインターフェースを定義します。
class AbstractCpu(ABC):
    """
    全てのCPUエミュレーションの基底となる抽象クラス。
    Busとのインターフェース、基本的な状態管理、命令サイクルの抽象化を提供します。
    """
    # @intent:responsibility CPUの状態とバスへの参照を初期化します。
    # @intent:pre-condition `bus`は有効なBusオブジェクトである必要があります。
    def __init__(self, bus: Bus):
        self._bus = bus
        self._state: CpuState = self._create_initial_state()
        self._cycle_count: int = 0
        # @intent:rationale Stateオブジェクトの直接操作を避けるため、protectedな命名規則を採用。
        #                  外部からのアクセスは`get_state()`メソッドを介して行う。

    # @intent:responsibility 初期状態のCpuStateオブジェクトを生成します。
    # @intent:rationale 各CPUアーキテクチャで初期状態が異なる可能性があるため、抽象メソッドとして定義します。
    @abstractmethod
    def _create_initial_state(self) -> CpuState:
        """
        CPUの初期状態を生成して返します。
        具体的なCPUアーキテクチャはこのメソッドを実装し、
        そのアーキテクチャに特化したCpuStateのサブクラスを返すことができます。
        """
        pass

    # @intent:responsibility CPUをリセットし、初期状態に戻します。
    def reset(self) -> None:
        """
        CPUのPCとSP、およびその他の状態を初期値にリセットします。
        """
        self._state = self._create_initial_state()
        # @intent:rationale resetは_create_initial_stateを再呼び出しすることで、
        #                  初期状態の生成ロジックを一元化し、状態の整合性を保ちます。

    # @intent:responsibility 現在のCPUの状態を返します。
    def get_state(self) -> CpuState:
        """
        現在のCPUの状態（レジスタ値など）を返します。
        """
        return self._state

    # @intent:responsibility メモリから次の命令（オペコード）をフェッチします。
    @abstractmethod
    def _fetch(self) -> int:
        """
        現在のPCからメモリの次の命令（オペコード）をフェッチし、その値を返します。
        フェッチ後、PCは次の命令の先頭を指すように更新されるべきです。
        """
        pass

    # @intent:responsibility フェッチしたオペコードを解析し、Operationオブジェクトに変換します。
    @abstractmethod
    def _decode(self, opcode: int) -> Operation:
        """
        与えられたオペコードを解析し、その命令のニーモニック、オペランドなどの詳細を
        Operationオブジェクトとして返します。
        """
        pass

    # @intent:responsibility デコードされた命令を実行し、CPUの状態を更新します。
    @abstractmethod
    def _execute(self, operation: Operation) -> None:
        """
        デコードされた命令を実行し、レジスタやフラグなどのCPUの状態を更新します。
        """
        pass

    # @intent:responsibility CPUを1命令サイクル進め、その結果のスナップショットを返します。
    # @intent:rationale このメソッドはフェッチ、デコード、実行のプロセスを内部で管理し、
    #                  その結果をUIやデバッガが利用可能な不変のSnapshotとして提供します。
    def step(self) -> Snapshot:
        """
        CPUを1命令サイクル進め、その時点でのCPUとバスの状態を含むSnapshotオブジェクトを返します。
        フェッチ -> デコード -> 実行の順序で処理を実行します。
        具体的な実装は派生クラスで行われますが、このメソッドがそれらをオーケストレーションします。
        """
        # 前サイクルまでの残存ログを破棄
        self._bus.get_and_clear_activity_log()

        initial_pc = self._state.pc # フェッチ前のPCを保存

        # フェッチ
        opcode = self._fetch()
        
        # デコード
        operation = self._decode(opcode)

        # 実行
        self._execute(operation)
        
        # このサイクルで発生したバスアクティビティを取得
        bus_activity = self._bus.get_and_clear_activity_log()

        # サイクルカウントを更新
        self._cycle_count += operation.cycle_count

        # @todo-intent: symbol_infoを正確に取得する

        # スナップショットの生成
        # TODO: metadata を正確に生成するようにする
        snapshot = Snapshot(
            state=self.get_state(), # 実行後の状態
            operation=operation,
            bus_activity=bus_activity,
            metadata=Metadata(cycle_count=self._cycle_count, symbol_info=f"PC: {initial_pc:#06x} -> {operation.mnemonic}")
        )
        return snapshot

