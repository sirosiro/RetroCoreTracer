# src/retro_core_tracer/ui/app.py
"""
PyQtアプリケーションのエントリポイント。
アプリケーションを初期化し、メインウィンドウを起動します。
"""
import sys
from PySide6.QtWidgets import QApplication
from .main_window import MainWindow

# @intent:responsibility アプリケーションを起動し、メインウィンドウを表示します。
def main():
    """
    アプリケーションのメイン関数。
    """
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
