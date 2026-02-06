"""
UIフォント管理モジュール。

クロスプラットフォーム（Windows/Mac/Linux）で最適な等幅フォントを選択する機能を提供します。
"""
from PySide6.QtGui import QFont, QFontDatabase

# @intent:responsibility 現在のシステムで利用可能な最適な等幅フォントファミリー名を返します。
def get_monospace_font_family() -> str:
    """
    現在のシステムで利用可能な、最適な等幅フォントのフォミリー名を返します。
    優先順位: Consolas -> Menlo -> Monaco -> Courier New -> Monospace
    """
    preferred_fonts = ["Consolas", "Menlo", "Monaco", "Courier New"]
    available_families = QFontDatabase.families()
    
    for font in preferred_fonts:
        if font in available_families:
            return font
            
    # Qtのシステムデフォルトの等幅フォントを使用
    return QFontDatabase.systemFont(QFontDatabase.FixedFont).family()

# @intent:responsibility 指定されたサイズを持つ最適な等幅フォントのQFontオブジェクトを生成して返します。
def get_monospace_font(size: int = 10) -> QFont:
    """
    最適な等幅フォントファミリーと指定されたサイズを持つQFontオブジェクトを返します。
    """
    family = get_monospace_font_family()
    return QFont(family, size)
