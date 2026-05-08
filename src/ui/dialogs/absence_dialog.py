from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.competitor_dao import CompetitorDAO


class AbsenceDialog(QDialog):
    """欠席者登録ダイアログ。

    参加者一覧をチェックボックスで表示し、欠席にチェックを入れて保存する。
    """

    def __init__(self, db_path: Path, parent=None):
        super().__init__(parent)
        self._dao = CompetitorDAO(db_path)

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

        self._checkboxes: list[tuple[int, QCheckBox]] = []  # (competitor_id, checkbox)

        self._setup_ui()
        self._retranslate_ui()
        self._load_competitors()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumSize(420, 500)

        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # header
        self._header_frame = QFrame()
        self._header_frame.setObjectName("dlgHeader")
        self._header_frame.setFixedHeight(36)
        self._header_frame.setStyleSheet(
            "QFrame#dlgHeader { background-color: #4a6fa0; border: none; }"
        )
        hdr_layout = QHBoxLayout(self._header_frame)
        hdr_layout.setContentsMargins(12, 0, 12, 0)
        self._header_label = QLabel()
        self._header_label.setStyleSheet(
            "color: white; font-weight: bold; background: transparent; border: none;"
        )
        hdr_layout.addWidget(self._header_label)
        outer.addWidget(self._header_frame)

        # hint label
        self._lbl_hint = QLabel()
        self._lbl_hint.setContentsMargins(16, 8, 16, 4)
        self._lbl_hint.setWordWrap(True)
        outer.addWidget(self._lbl_hint)

        # scroll area for checkboxes
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: #E8EEF4; }"
        )
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll_layout.setSpacing(2)
        self._scroll_layout.setContentsMargins(16, 4, 16, 4)
        self._scroll.setWidget(self._scroll_widget)
        outer.addWidget(self._scroll, stretch=1)

        # footer
        self._footer_frame = QFrame()
        self._footer_frame.setObjectName("dlgFooter")
        self._footer_frame.setStyleSheet(
            "QFrame#dlgFooter { background-color: #D0DCE8; border: none;"
            " border-top: 1px solid #b0c4d8; }"
        )
        footer_layout = QHBoxLayout(self._footer_frame)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.addStretch()
        self._btn_save = QPushButton()
        self._btn_save.setDefault(True)
        self._btn_save.setMinimumWidth(80)
        self._btn_cancel = QPushButton()
        self._btn_cancel.setMinimumWidth(80)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(self._btn_save)
        footer_layout.addWidget(self._btn_cancel)
        outer.addWidget(self._footer_frame)

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("欠席登録"))
        self._header_label.setText(self.tr("欠席登録"))
        self._lbl_hint.setText(
            self.tr("欠席する参加者にチェックを入れて「保存」を押してください。")
        )
        self._btn_save.setText(self.tr("保存"))
        self._btn_cancel.setText(self.tr("キャンセル"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_competitors(self) -> None:
        for _, chk in self._checkboxes:
            chk.deleteLater()
        self._checkboxes.clear()

        competitors: list[dict[str, Any]] = self._dao.get_all()
        for c in competitors:
            bib = c.get("bib_number") or ""
            name = c.get("name") or ""
            cls = c.get("class_name") or ""
            label = f"{bib}  {name}  ({cls})" if cls else f"{bib}  {name}"
            chk = QCheckBox(label)
            chk.setChecked(bool(c.get("absent", 0)))
            self._scroll_layout.addWidget(chk)
            self._checkboxes.append((c["id"], chk))

        if not competitors:
            empty = QLabel(self.tr("参加者が登録されていません。"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._scroll_layout.addWidget(empty)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        errors: list[str] = []
        for competitor_id, chk in self._checkboxes:
            try:
                self._dao.update(competitor_id, {"absent": int(chk.isChecked())})
            except Exception as exc:
                errors.append(str(exc))

        if errors:
            QMessageBox.warning(
                self,
                self.tr("保存エラー"),
                self.tr("一部の保存に失敗しました:\n") + "\n".join(errors),
            )
        else:
            self.accept()
