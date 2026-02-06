# retro_core_tracer/core/state.py
"""
Core Layer (CPU状態)

このモジュールは、CPUの基本的な状態（レジスタ群）を保持するデータ構造を定義します。
"""
from dataclasses import dataclass

# @intent:responsibility CPUのレジスタ状態を保持します。アーキテクチャ固有のレジスタはこれを拡張します。
@dataclass
class CpuState:
    """
    CPUのレジスタ状態を保持するデータクラス。
    これは抽象的な基底状態であり、特定のCPUアーキテクチャに応じて拡張されます。
    """
    pc: int = 0x0000  # Program Counter
    sp: int = 0x0000  # Stack Pointer
    # 他のレジスタ（A, B, C, D, E, H, L, Fなど）は、具体的なCPUアーキテクチャの実装で追加されます。
    # 例: z80_state.py, m68k_state.py など
    # @intent:rationale 初期値は0x0000とする。これは多くのCPUでリセット時の一般的なPC/SPの初期値となるため。
    #                  具体的な初期値はCPUアーキテクチャの実装で上書きされる可能性がある。