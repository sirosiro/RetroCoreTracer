# retro_core_tracer/core/cpu.py
"""
Core Layer (抽象CPU)

このモジュールは、CPUの基本的な状態管理と命令サイクルの駆動に関する抽象化を提供します。
具体的な命令の振る舞いはInstruction Layerに移譲されます。
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Tuple

from retro_core_tracer.transport.bus import Bus
from retro_core_tracer.core.snapshot import Snapshot, Operation, Metadata
from retro_core_tracer.core.state import CpuState
from retro_core_tracer.common.types import SymbolMap, RegisterLayoutInfo

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
        self._symbol_map: SymbolMap = {}
        self._reverse_symbol_map: Dict[int, str] = {}
        # @intent:rationale Stateオブジェクトの直接操作を避けるため、protectedな命名規則を採用。
        #                  外部からのアクセスは`get_state()`メソッドを介して行う。

    # @intent:responsibility I/O空間（Port I/O）をサポートするかどうかを返します。
    # @intent:rationale UI層などがアーキテクチャ名（文字列）に依存せず、機能ベースでレイアウトを決定できるようにします。
    @property
    @abstractmethod
    def has_io_port(self) -> bool:
        """
        このCPUが独立したI/O空間（ポート入出力）をサポートしているか返します。
        Trueの場合、UIはI/Oマップやバスを表示すべきです。
        """
        # Intentional: Abstract property, must be implemented by subclasses.
        pass

    # @intent:responsibility シンボルマップを設定します。
    def set_symbol_map(self, symbol_map: SymbolMap) -> None:
        """
        シンボルマップ（名前とアドレスの対応表）を設定します。
        """
        self._symbol_map = symbol_map
        # 逆引きマップを作成して、アドレスからラベルを素早く引けるようにする
        self._reverse_symbol_map = {addr: name for name, addr in symbol_map.items()}

    def get_symbol_map(self) -> SymbolMap:
        """
        現在設定されているシンボルマップを返します。
        """
        return self._symbol_map

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
    # @intent:rationale Template Methodパターンを採用し、共通の実行フロー（ログクリア→フェッチ→デコード→PC更新→実行→Snapshot生成）を定義します。
    #                  アーキテクチャ固有の振る舞い（HALT処理など）はフックメソッドで対応します。
    def step(self) -> Snapshot:
        """
        CPUを1命令サイクル進め、その時点でのCPUとバスの状態を含むSnapshotオブジェクトを返します。
        """
        # 1. 前処理: 前サイクルまでの残存ログを破棄
        self._bus.get_and_clear_activity_log()
        initial_pc = self._state.pc

        # 2. HALT判定 (Hook)
        halt_snapshot = self._handle_halt(initial_pc)
        if halt_snapshot:
            return halt_snapshot

        # 3. フェッチ
        opcode = self._fetch()

        # 4. デコード
        operation = self._decode(opcode)

        # 5. PC更新 (Hook)
        # 多くのCPUではデコード後、実行前にPCを命令長分進める
        self._update_pc(operation)

        # 6. 実行
        self._execute(operation)
        
        # 7. 後処理 & Snapshot生成
        return self._create_snapshot(initial_pc, operation)

    # @intent:responsibility HALT状態の場合の処理を行います。
    # @intent:return HALT中であればその状態のSnapshot、そうでなければNone。
    def _handle_halt(self, current_pc: int) -> Optional[Snapshot]:
        """
        HALT状態の場合の処理。デフォルトは何もしない（Noneを返す）。
        オーバーライドしてHALT時の挙動（NOP扱いなど）を実装する。
        """
        return None

    # @intent:responsibility 命令実行前にPCを更新します。
    def _update_pc(self, operation: Operation) -> None:
        """
        命令実行前のPC更新。デフォルトは命令長分進める。
        """
        self._state.pc = (self._state.pc + operation.length) & 0xFFFF

    # @intent:responsibility スナップショットを生成します。
    def _create_snapshot(self, initial_pc: int, operation: Operation) -> Snapshot:
        """
        実行結果からSnapshotオブジェクトを生成する共通ロジック。
        """
        # このサイクルで発生したバスアクティビティを取得
        bus_activity = self._bus.get_and_clear_activity_log()

        # サイクルカウントを更新
        self._cycle_count += operation.cycle_count

        # シンボル情報の取得
        symbol_label = self._reverse_symbol_map.get(initial_pc, "")
        symbol_info = f"{symbol_label}: " if symbol_label else ""
        symbol_info += f"{operation.mnemonic}"
        if operation.operands:
            symbol_info += " " + ", ".join(operation.operands)

        # スナップショットの生成
        return Snapshot(
            state=self.get_state(), # 実行後の状態（コピーではないが、Snapshot生成時にイミュータブル化されることを期待）
            # 注: Pythonのdataclassはデフォルトでは浅いコピーもしないので、
            # stateが可変オブジェクトの場合、Snapshot内のstateも変化してしまうリスクがある。
            # ただし、現在の実装ではCpuStateはデータクラスであり、Snapshot生成時に
            # copy.deepcopyなどをするか、あるいはCpuState自体を毎回作り直す設計にする必要がある。
            # 現状のコードベースではSnapshot作成時にstateのコピーを行っていないように見えるため、
            # 将来的な課題として残るが、ここでは既存ロジックを踏襲する。
            operation=operation,
            metadata=Metadata(cycle_count=self._cycle_count, symbol_info=symbol_info),
            bus_activity=bus_activity
        )

    @abstractmethod
    def get_register_map(self) -> Dict[str, int]:
        """
        現在のレジスタ値を辞書形式で返す。
        UIがCPUの内部構造を知らなくても値を表示できるようにするために使用される。
        """
        pass

    @abstractmethod
    def get_register_layout(self) -> List[RegisterLayoutInfo]:
        """
        レジスタをUI上でどのように配置・グループ化すべきかの定義を返す。
        """
        pass

    @abstractmethod
    def get_flag_state(self) -> Dict[str, bool]:
        """
        現在のフラグ（ステータスレジスタ）の各ビットの状態を辞書形式で返す。
        """
        pass

    @abstractmethod
    def disassemble(self, start_addr: int, length: int) -> List[Tuple[int, str, str]]:
        """
        指定されたメモリ範囲を逆アセンブルし、(address, hex_bytes, mnemonic) のタプルリストを返す。
        """
        pass