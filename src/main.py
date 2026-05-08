import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

# アプリ全体のスタイル設定
_APP_STYLESHEET = """
    /* 入力ウィジェット: グレーの枠線 + フォーカス時に青グレー */
    QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QDateEdit, QTimeEdit,
    QTextEdit, QPlainTextEdit {
        border: 1px solid #a0a8b0;
        border-radius: 3px;
        padding: 2px 4px;
        background-color: #ffffff;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QComboBox:focus, QDateEdit:focus, QTimeEdit:focus,
    QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #5b7fa3;
    }
    QLineEdit:disabled, QSpinBox:disabled,
    QComboBox:disabled, QDateEdit:disabled, QTimeEdit:disabled {
        background-color: #f0f0f0;
        color: #808080;
    }

    /* スクロールバー */
    QScrollBar:vertical {
        background: #f0f2f4;
        width: 12px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #b0bcc8;
        border-radius: 4px;
        min-height: 24px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover { background: #8090a0; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

    QScrollBar:horizontal {
        background: #f0f2f4;
        height: 12px;
        margin: 0;
    }
    QScrollBar::handle:horizontal {
        background: #b0bcc8;
        border-radius: 4px;
        min-width: 24px;
        margin: 2px;
    }
    QScrollBar::handle:horizontal:hover { background: #8090a0; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")          # グレー系の一貫した枠線を全ウィジェットに適用
    app.setStyleSheet(_APP_STYLESHEET)
    app.setApplicationName("OpenARDF-calc")
    app.setOrganizationName("JF9SOM")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
