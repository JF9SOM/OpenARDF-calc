from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_VERSION = "0.1.0"
_GITHUB_URL = "https://github.com/JF9SOM/OpenARDF-calc"
_MANUAL_URL = "https://fdt.rdf.jp/si_system/doc/ardf_si_090801.pdf"
_ACCENT = "#4a6fa0"
_ACCENT_DARK = "#2a4f7a"
_ACCENT_MID = "#5a7a9a"


class _SignalIcon(QWidget):
    """無線信号を模したカスタムアイコン（アンテナ＋放射弧）。"""

    def __init__(self, size: int = 72, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx = w // 2
        base_y = h - 10  # アンテナ基点

        color = QColor(_ACCENT)

        # アンテナ縦線
        pen = QPen(color, 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(cx, base_y, cx, base_y - h // 3)

        # アンテナ基点ドット
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(cx - 4, base_y - 4, 8, 8)

        # 放射弧（3本、上向き）
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i, r in enumerate([h // 5, h // 3, int(h * 0.46)]):
            alpha = 240 - i * 60
            arc_pen = QPen(QColor(74, 111, 160, alpha), 2.8 - i * 0.4)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            # 40°〜140° の上半分弧（Qt角度: 0°=3時、正=反時計回り）
            painter.drawArc(cx - r, base_y - r, r * 2, r * 2, 40 * 16, 100 * 16)


class AboutDialog(QDialog):
    """「このソフトについて」ダイアログ。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#E8EEF4"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self._setup_ui()
        self._retranslate_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumWidth(460)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )

        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── ヘッダー ──────────────────────────────────────────────
        self._header_frame = QFrame()
        self._header_frame.setObjectName("dlgHeader")
        self._header_frame.setFixedHeight(36)
        self._header_frame.setStyleSheet(
            f"QFrame#dlgHeader {{ background-color: {_ACCENT}; border: none; }}"
        )
        hdr = QHBoxLayout(self._header_frame)
        hdr.setContentsMargins(12, 0, 12, 0)
        self._header_label = QLabel()
        self._header_label.setStyleSheet(
            "color: white; font-weight: bold; background: transparent; border: none;"
        )
        hdr.addWidget(self._header_label)
        outer.addWidget(self._header_frame)

        # ── メインコンテンツ ──────────────────────────────────────
        content = QVBoxLayout()
        content.setSpacing(14)
        content.setContentsMargins(24, 20, 24, 16)
        outer.addLayout(content)

        # タイトル行（アイコン＋テキスト）
        title_row = QHBoxLayout()
        title_row.setSpacing(18)
        title_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._icon = _SignalIcon(size=72)
        title_row.addWidget(self._icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        self._lbl_title = QLabel("OpenARDF-calc")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        self._lbl_title.setFont(title_font)
        self._lbl_title.setStyleSheet(f"color: {_ACCENT_DARK};")
        title_col.addWidget(self._lbl_title)

        self._lbl_subtitle = QLabel()
        sub_font = QFont()
        sub_font.setPointSize(10)
        self._lbl_subtitle.setFont(sub_font)
        self._lbl_subtitle.setStyleSheet(f"color: {_ACCENT_MID};")
        title_col.addWidget(self._lbl_subtitle)

        self._lbl_version = QLabel()
        ver_font = QFont()
        ver_font.setPointSize(9)
        self._lbl_version.setFont(ver_font)
        self._lbl_version.setStyleSheet(f"color: {_ACCENT};")
        title_col.addWidget(self._lbl_version)
        title_col.addStretch()

        title_row.addLayout(title_col)
        title_row.addStretch()
        content.addLayout(title_row)

        content.addWidget(self._make_separator())

        # 情報グリッド（開発者・ライセンス・使用技術）
        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnMinimumWidth(0, 90)

        self._lbl_dev_key = QLabel()
        self._lbl_dev_key.setStyleSheet(
            f"color: {_ACCENT_MID}; font-weight: bold;"
        )
        self._lbl_dev_val = QLabel("JF9SOM")
        grid.addWidget(self._lbl_dev_key, 0, 0)
        grid.addWidget(self._lbl_dev_val, 0, 1)

        self._lbl_license_key = QLabel()
        self._lbl_license_key.setStyleSheet(
            f"color: {_ACCENT_MID}; font-weight: bold;"
        )
        self._lbl_license_val = QLabel("MIT License")
        grid.addWidget(self._lbl_license_key, 1, 0)
        grid.addWidget(self._lbl_license_val, 1, 1)

        self._lbl_tech_key = QLabel()
        self._lbl_tech_key.setStyleSheet(
            f"color: {_ACCENT_MID}; font-weight: bold;"
        )
        self._lbl_tech_val = QLabel("Python  ·  PySide6  ·  SQLite")
        grid.addWidget(self._lbl_tech_key, 2, 0)
        grid.addWidget(self._lbl_tech_val, 2, 1)

        content.addLayout(grid)
        content.addWidget(self._make_separator())

        # リンク
        links = QVBoxLayout()
        links.setSpacing(6)

        self._lbl_github_key = QLabel()
        self._lbl_github_key.setStyleSheet(
            f"color: {_ACCENT_MID}; font-weight: bold;"
        )
        links.addWidget(self._lbl_github_key)

        self._lbl_github_link = QLabel(
            f'<a href="{_GITHUB_URL}" style="color:#2a6fba;">{_GITHUB_URL}</a>'
        )
        self._lbl_github_link.setOpenExternalLinks(True)
        self._lbl_github_link.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        links.addWidget(self._lbl_github_link)

        self._lbl_manual_key = QLabel()
        self._lbl_manual_key.setStyleSheet(
            f"color: {_ACCENT_MID}; font-weight: bold;"
        )
        links.addWidget(self._lbl_manual_key)

        self._lbl_manual_link = QLabel(
            f'<a href="{_MANUAL_URL}" style="color:#2a6fba;">{_MANUAL_URL}</a>'
        )
        self._lbl_manual_link.setOpenExternalLinks(True)
        self._lbl_manual_link.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        self._lbl_manual_link.setWordWrap(True)
        links.addWidget(self._lbl_manual_link)

        content.addLayout(links)

        # ── フッター ──────────────────────────────────────────────
        self._footer_frame = QFrame()
        self._footer_frame.setObjectName("dlgFooter")
        self._footer_frame.setStyleSheet(
            "QFrame#dlgFooter { background-color: #D0DCE8; border: none;"
            " border-top: 1px solid #b0c4d8; }"
        )
        footer = QHBoxLayout(self._footer_frame)
        footer.setContentsMargins(12, 8, 12, 8)
        footer.addStretch()
        self._btn_ok = QPushButton()
        self._btn_ok.setDefault(True)
        self._btn_ok.setMinimumWidth(80)
        self._btn_ok.clicked.connect(self.accept)
        footer.addWidget(self._btn_ok)
        outer.addWidget(self._footer_frame)

    @staticmethod
    def _make_separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #b0c4d8; max-height: 1px; border: none;")
        return sep

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("OpenARDF-calc について"))
        self._header_label.setText(self.tr("このソフトについて"))

        self._lbl_subtitle.setText(self.tr("ARDF競技用集計ソフト"))
        self._lbl_version.setText(self.tr("バージョン ") + _VERSION)

        self._lbl_dev_key.setText(self.tr("開発者"))
        self._lbl_license_key.setText(self.tr("ライセンス"))
        self._lbl_tech_key.setText(self.tr("使用技術"))

        self._lbl_github_key.setText(self.tr("GitHub リポジトリ"))
        self._lbl_manual_key.setText(self.tr("参考マニュアル (ARDF SI)"))

        self._btn_ok.setText(self.tr("OK"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)
