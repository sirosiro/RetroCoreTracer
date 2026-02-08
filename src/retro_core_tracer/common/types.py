"""
共通の型定義を提供するモジュール。
プロジェクト全体で使用される汎用的な型エイリアスなどを定義します。
"""
from typing import Dict, List, NamedTuple

# @intent:data_structure シンボル名とアドレスをマッピングする辞書の型エイリアス。
# Loader, CPU, UIなど複数のレイヤーで共通して使用されます。
SymbolMap = Dict[str, int]

# @intent:data_structure 単一のレジスタの表示定義。UIが動的にフィールドを生成するために使用される。
class RegisterInfo(NamedTuple):
    name: str
    width: int  # ビット幅 (8 or 16)

# @intent:data_structure レジスタグループの表示定義。関連するレジスタ（例: "Main", "Index"）をまとめる。
class RegisterLayoutInfo(NamedTuple):
    group_name: str
    registers: List[RegisterInfo]