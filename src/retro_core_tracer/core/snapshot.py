# retro_core_tracer/core/snapshot.py
"""
実行状態の不変スナップショット

このモジュールは、CPUとバスの完全な状態を記録した不変のデータ構造を定義します。
UIへの情報提供と、デバッグ時の状態記録に用いる責務を負います。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from retro_core_tracer.core.state import CpuState # CpuStateはstate.pyからインポート
from retro_core_tracer.transport.bus import BusAccessType, BusAccess



# @intent:responsibility 実行された命令の詳細を記録します。
@dataclass(frozen=True) # 不変データ構造
class Operation:
    """
    実行された命令の詳細（HEX、ニーモニック、オペランド）を記録するデータクラス。
    """
    opcode_hex: str # 例: "C3"
    mnemonic: str # 例: "JP"
    operands: List[str] = field(default_factory=list) # 例: ["$1234"]
    operand_bytes: List[int] = field(default_factory=list) # 生のオペランドバイト
    cycle_count: int = 0 # 命令実行に必要なクロックサイクル数
    length: int = 1 # 命令のバイト長

# @intent:responsibility 実行に関するメタデータを記録します。
@dataclass(frozen=True) # 不変データ構造
class Metadata:
    """
    実行に関するメタデータ（累計サイクル数、シンボル情報など）を記録するデータクラス。
    """
    cycle_count: int
    symbol_info: Optional[str] = None # 例: "main_loop: JP $1234"

# @intent:responsibility ある一時点におけるCPUとバスの完全な状態を不変に記録します。
@dataclass(frozen=True) # 不変データ構造
class Snapshot:
    """
    ある一時点における、CPUとバスの完全な状態を記録した不変のデータ構造。
    UIへの情報提供と、デバッグ時の状態記録に用います。
    """
    state: CpuState
    operation: Operation
    metadata: Metadata # 順序を変更
    bus_activity: List[BusAccess] = field(default_factory=list)

    # @intent:rationale Snapshotは不変であるべきという原則に従い、frozen=Trueを設定。
    #                  リストなどのミュータブルなフィールドはdefault_factoryを使用し、
    #                  インスタンスごとに新しいリストが生成されるようにする。
