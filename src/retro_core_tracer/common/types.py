"""
共通の型定義を提供するモジュール。
プロジェクト全体で使用される汎用的な型エイリアスなどを定義します。
"""
from typing import Dict

# @intent:data_structure シンボル名とアドレスをマッピングする辞書の型エイリアス。
# Loader, CPU, UIなど複数のレイヤーで共通して使用されます。
SymbolMap = Dict[str, int]
