from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
)

from core.si_reader.si_manager_csv import SIManagerCSVReader
from core.si_result_dao import SIResultDAO


class SIImportDialog(QDialog):
    """SI Manager CSV 読み込み結果表示ダイアログ。

    ファイルダイアログ → 読み込み → 照合 → 結果表示 の流れを一括処理する。
    読み込みは何度でもやり直し可能。
    """

    def __init__(self, db_path: Path, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._dao = SIResultDAO(db_path)
        self._reader = SIManagerCSVReader()

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
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumSize(540, 460)

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

        root = QVBoxLayout()
        root.setSpacing(8)
        root.setContentsMargins(16, 12, 16, 8)
        outer.addLayout(root)

        # summary label
        self._lbl_summary = QLabel()
        self._lbl_summary.setWordWrap(True)
        root.addWidget(self._lbl_summary)

        # unmatched list
        self._lbl_unmatched = QLabel()
        root.addWidget(self._lbl_unmatched)
        self._list_unmatched = QListWidget()
        self._list_unmatched.setMaximumHeight(120)
        self._list_unmatched.setStyleSheet(
            "QListWidget { background: #fff; border: 1px solid #b0c4d8; border-radius: 3px; }"
        )
        root.addWidget(self._list_unmatched)

        # warnings / errors
        self._lbl_warnings = QLabel()
        root.addWidget(self._lbl_warnings)
        self._txt_warnings = QTextEdit()
        self._txt_warnings.setReadOnly(True)
        self._txt_warnings.setMaximumHeight(100)
        self._txt_warnings.setStyleSheet(
            "QTextEdit { background: #fff8f0; border: 1px solid #d8c0b0; border-radius: 3px; }"
        )
        root.addWidget(self._txt_warnings)
        root.addStretch()

        # footer
        self._footer_frame = QFrame()
        self._footer_frame.setObjectName("dlgFooter")
        self._footer_frame.setStyleSheet(
            "QFrame#dlgFooter { background-color: #D0DCE8; border: none;"
            " border-top: 1px solid #b0c4d8; }"
        )
        footer_layout = QHBoxLayout(self._footer_frame)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        self._btn_reload = QPushButton()
        self._btn_reload.setMinimumWidth(120)
        footer_layout.addWidget(self._btn_reload)
        footer_layout.addStretch()
        self._btn_close = QPushButton()
        self._btn_close.setMinimumWidth(80)
        self._btn_close.setDefault(True)
        footer_layout.addWidget(self._btn_close)
        outer.addWidget(self._footer_frame)

        self._btn_reload.clicked.connect(self._on_reload)
        self._btn_close.clicked.connect(self.accept)

        self._set_empty_state()

    def _set_empty_state(self) -> None:
        self._lbl_summary.setText(
            self.tr("「別ファイルから読み込み」ボタンでCSVファイルを選択してください。")
        )
        self._list_unmatched.setVisible(False)
        self._lbl_unmatched.setVisible(False)
        self._txt_warnings.setVisible(False)
        self._lbl_warnings.setVisible(False)

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("SIデータ読み込み"))
        self._header_label.setText(self.tr("SI Manager CSV 読み込み"))
        self._lbl_unmatched.setText(self.tr("照合できなかった SIカードNo:"))
        self._lbl_warnings.setText(self.tr("警告・エラー:"))
        self._btn_reload.setText(self.tr("別ファイルから読み込み"))
        self._btn_close.setText(self.tr("閉じる"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Import flow
    # ------------------------------------------------------------------

    def _on_reload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("SI Manager CSV を選択"),
            str(Path.home()),
            self.tr("CSV ファイル (*.csv);;すべてのファイル (*)"),
        )
        if not path:
            return
        self._run_import(Path(path))

    def _run_import(self, path: Path) -> None:
        try:
            records = self._reader.read(path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                self.tr("読み込みエラー"),
                self.tr("CSVの読み込みに失敗しました:\n") + str(exc),
            )
            return

        if not records:
            QMessageBox.warning(
                self,
                self.tr("データなし"),
                self.tr("有効な SIデータが見つかりませんでした。\n"
                        "CSVのフォーマットを確認してください。"),
            )
            return

        comp = self._dao.get_competition()
        si_base_time: Optional[str] = comp.get("si_base_time") if comp else None

        matched, unmatched, warnings = self._dao.import_records(records, si_base_time)

        self._show_results(len(records), matched, unmatched, warnings, path.name)

    def _show_results(
        self,
        total: int,
        matched: int,
        unmatched: list[str],
        warnings: list[str],
        filename: str,
    ) -> None:
        summary = (
            f"{self.tr('ファイル: ')}{filename}\n"
            f"{self.tr('読み込み件数: ')}{total} {self.tr('件')}\n"
            f"{self.tr('照合成功: ')}{matched} {self.tr('名')}\n"
            f"{self.tr('照合失敗: ')}{len(unmatched)} {self.tr('件')}"
        )
        self._lbl_summary.setText(summary)

        self._list_unmatched.clear()
        if unmatched:
            self._list_unmatched.addItems(unmatched)
            self._lbl_unmatched.setVisible(True)
            self._list_unmatched.setVisible(True)
        else:
            self._lbl_unmatched.setVisible(False)
            self._list_unmatched.setVisible(False)

        if warnings:
            self._txt_warnings.setPlainText("\n".join(warnings))
            self._lbl_warnings.setVisible(True)
            self._txt_warnings.setVisible(True)
        else:
            self._txt_warnings.setVisible(False)
            self._lbl_warnings.setVisible(False)
