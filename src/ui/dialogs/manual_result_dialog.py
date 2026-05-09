from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from core.competitor_dao import CompetitorDAO
from core.si_result_dao import SIResultDAO

# Status options (displayed in dropdown)
_STATUS_LABELS = [
    "正常完走",
    "棄権",
    "タイムオーバー",
    "失格（その他）",
    "欠席",
]

# Mapping status label to database values
_STATUS_MAP = {
    "正常完走": ("normal", False, False),    # (reason, absent, disqualified)
    "棄権": ("withdrawal", False, True),
    "タイムオーバー": ("overtime", False, False),  # Can be marked with overtime=1 in results
    "失格（その他）": ("disqualified", False, True),
    "欠席": ("absent", True, False),
}


class ManualResultDialog(QDialog):
    """手動結果入力ダイアログ。

    未入力の選手に対して、以下を手動入力する：
    - ステータス（正常完走/棄権/OT/失格/欠席）
    - 失格理由（テキスト）
    - フィニッシュタイム（任意）
    - 探索TX数（任意）
    - 備考（任意）
    """

    def __init__(
        self,
        db_path: Path,
        competitor: dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)
        self._db_path = db_path
        self._competitor = competitor
        self._competitor_dao = CompetitorDAO(db_path)
        self._si_result_dao = SIResultDAO(db_path)

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
        self._load_current_data()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumWidth(480)
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── ヘッダー ──────────────────────────────────────
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

        # ── 競技者情報（読み取り専用） ──────────────────────
        root = QVBoxLayout()
        root.setSpacing(8)
        root.setContentsMargins(16, 12, 16, 8)
        outer.addLayout(root)

        info_layout = QFormLayout()
        info_layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        info_layout.setHorizontalSpacing(12)
        info_layout.setVerticalSpacing(6)

        self._lbl_bib = QLabel()
        self._info_bib = QLineEdit()
        self._info_bib.setReadOnly(True)
        self._info_bib.setFixedWidth(80)
        info_layout.addRow(self._lbl_bib, self._info_bib)

        self._lbl_callsign = QLabel()
        self._info_callsign = QLineEdit()
        self._info_callsign.setReadOnly(True)
        info_layout.addRow(self._lbl_callsign, self._info_callsign)

        self._lbl_name = QLabel()
        self._info_name = QLineEdit()
        self._info_name.setReadOnly(True)
        info_layout.addRow(self._lbl_name, self._info_name)

        self._lbl_class = QLabel()
        self._info_class = QLineEdit()
        self._info_class.setReadOnly(True)
        self._info_class.setFixedWidth(80)
        info_layout.addRow(self._lbl_class, self._info_class)

        root.addLayout(info_layout)

        # ── 結果入力フォーム ──────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._lbl_status = QLabel()
        self._combo_status = QComboBox()
        self._combo_status.addItems(_STATUS_LABELS)
        self._combo_status.currentIndexChanged.connect(self._on_status_changed)
        form.addRow(self._lbl_status, self._combo_status)

        self._lbl_reason = QLabel()
        self._text_reason = QLineEdit()
        self._text_reason.setPlaceholderText(self.tr("例: 道に迷った、無線故障"))
        form.addRow(self._lbl_reason, self._text_reason)

        self._lbl_finish_time = QLabel()
        self._edit_finish_time = QLineEdit()
        self._edit_finish_time.setPlaceholderText(self.tr("HH:MM:SS または MM:SS"))
        self._edit_finish_time.setFixedWidth(100)
        form.addRow(self._lbl_finish_time, self._edit_finish_time)

        self._lbl_tx_count = QLabel()
        self._spin_tx_count = QSpinBox()
        self._spin_tx_count.setRange(0, 99)
        self._spin_tx_count.setFixedWidth(60)
        self._spin_tx_count.setSpecialValueText(self.tr("—"))
        form.addRow(self._lbl_tx_count, self._spin_tx_count)

        self._lbl_remarks = QLabel()
        self._text_remarks = QTextEdit()
        self._text_remarks.setFixedHeight(80)
        form.addRow(self._lbl_remarks, self._text_remarks)

        root.addLayout(form)

        # ── フッター（ボタンエリア） ──────────────────────
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

        self._on_status_changed()  # Initialize field visibility

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        c = self._competitor
        bib = c.get("bib_number") or ""
        name = c.get("name") or ""
        suffix = f"  —  {bib}  {name}".rstrip() if (bib or name) else ""
        self.setWindowTitle(self.tr("結果を手動入力") + suffix)
        self._header_label.setText(self.tr("結果を手動入力"))

        self._lbl_bib.setText(self.tr("ゼッケン"))
        self._lbl_callsign.setText(self.tr("コールサイン"))
        self._lbl_name.setText(self.tr("氏名"))
        self._lbl_class.setText(self.tr("クラス"))

        self._lbl_status.setText(self.tr("ステータス"))
        self._lbl_reason.setText(self.tr("失格理由"))
        self._lbl_finish_time.setText(self.tr("フィニッシュタイム"))
        self._lbl_tx_count.setText(self.tr("探索TX数"))
        self._lbl_remarks.setText(self.tr("備考"))

        self._btn_save.setText(self.tr("保存"))
        self._btn_cancel.setText(self.tr("キャンセル"))

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_current_data(self) -> None:
        c = self._competitor
        self._info_bib.setText(c.get("bib_number") or "")
        self._info_callsign.setText(c.get("call_sign") or "")
        self._info_name.setText(c.get("name") or "")
        self._info_class.setText(c.get("class_name") or "")

        # Pre-populate existing registration data for editing
        if c.get("absent"):
            self._combo_status.setCurrentText("欠席")
        elif c.get("disqualified"):
            reason = c.get("disqualification_reason") or ""
            if reason == "棄権":
                self._combo_status.setCurrentText("棄権")
            else:
                self._combo_status.setCurrentText("失格（その他）")
                self._text_reason.setText(reason)
        else:
            result = self._si_result_dao.get_by_competitor_id(c["id"])
            if result:
                if result.get("overtime"):
                    self._combo_status.setCurrentText("タイムオーバー")
                    rs = result.get("raw_status") or ""
                    if rs and rs != "タイムオーバー":
                        self._text_remarks.setPlainText(rs)
                else:
                    self._combo_status.setCurrentText("正常完走")
                    if result.get("raw_status"):
                        self._text_remarks.setPlainText(result["raw_status"])
                if result.get("finish_time"):
                    self._edit_finish_time.setText(result["finish_time"])
                tx = result.get("punched_tx_count") or 0
                if tx > 0:
                    self._spin_tx_count.setValue(tx)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_status_changed(self) -> None:
        status = self._combo_status.currentText()
        # Show/hide fields based on status
        if status == "正常完走":
            self._text_reason.setEnabled(False)
            self._text_reason.clear()
            self._edit_finish_time.setEnabled(True)
            self._spin_tx_count.setEnabled(True)
        elif status == "棄権":
            self._text_reason.setEnabled(False)
            self._text_reason.setText("棄権")
            self._edit_finish_time.setEnabled(False)
            self._edit_finish_time.clear()
            self._spin_tx_count.setEnabled(False)
            self._spin_tx_count.setValue(0)
        elif status == "タイムオーバー":
            self._text_reason.setEnabled(False)
            self._text_reason.setText("タイムオーバー")
            self._edit_finish_time.setEnabled(True)
            self._spin_tx_count.setEnabled(True)
        elif status == "失格（その他）":
            self._text_reason.setEnabled(True)
            self._text_reason.clear()
            self._edit_finish_time.setEnabled(False)
            self._edit_finish_time.clear()
            self._spin_tx_count.setEnabled(False)
            self._spin_tx_count.setValue(0)
        elif status == "欠席":
            self._text_reason.setEnabled(False)
            self._text_reason.clear()
            self._edit_finish_time.setEnabled(False)
            self._edit_finish_time.clear()
            self._spin_tx_count.setEnabled(False)
            self._spin_tx_count.setValue(0)

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        status = self._combo_status.currentText()
        finish_time = self._edit_finish_time.text().strip()
        tx_count = self._spin_tx_count.value()
        remarks = self._text_remarks.toPlainText().strip()

        # Validate finish_time format if provided
        if finish_time and not self._is_valid_time(finish_time):
            QMessageBox.warning(
                self,
                self.tr("入力エラー"),
                self.tr("フィニッシュタイムの形式が不正です。HH:MM:SS または MM:SS で入力してください。"),
            )
            return

        # Convert finish_time to standard format if provided
        if finish_time:
            finish_time = self._normalize_time(finish_time)

        try:
            self._save_to_db(status, finish_time, tx_count, remarks)
        except Exception as exc:
            QMessageBox.critical(
                self, self.tr("保存エラー"),
                self.tr("保存中にエラーが発生しました:\n") + str(exc),
            )
            return

        self.accept()

    def _is_valid_time(self, s: str) -> bool:
        return bool(re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', s))

    def _normalize_time(self, s: str) -> str:
        parts = s.split(':')
        if len(parts) == 2:
            return f"00:{parts[0]}:{parts[1]}"
        return s  # Already HH:MM:SS

    def _save_to_db(self, status: str, finish_time: Optional[str], tx_count: int, remarks: str) -> None:
        competitor_id = self._competitor["id"]
        reason, set_absent, set_disqualified = _STATUS_MAP[status]

        if status == "正常完走":
            # Create/update results entry
            elapsed: Optional[int] = None
            if finish_time:
                si_base_time = self._get_si_base_time()
                if si_base_time:
                    try:
                        from core.si_result_dao import _hms_to_seconds
                        elapsed = _hms_to_seconds(finish_time) - _hms_to_seconds(si_base_time)
                        if elapsed < 0:
                            elapsed += 86400
                    except:
                        pass
            self._si_result_dao.upsert(
                competitor_id=competitor_id,
                finish_time=finish_time,
                elapsed_seconds=elapsed,
                punched_tx_count=tx_count,
                overtime=0,
                raw_status=remarks if remarks else None,
                tx_punches={},
            )
            # Clear disqualified/absent flags
            self._competitor_dao.update(competitor_id, {"absent": 0, "disqualified": 0})

        elif status == "タイムオーバー":
            # Create results entry with overtime flag
            elapsed: Optional[int] = None
            if finish_time:
                si_base_time = self._get_si_base_time()
                if si_base_time:
                    try:
                        from core.si_result_dao import _hms_to_seconds
                        elapsed = _hms_to_seconds(finish_time) - _hms_to_seconds(si_base_time)
                        if elapsed < 0:
                            elapsed += 86400
                    except:
                        pass
            self._si_result_dao.upsert(
                competitor_id=competitor_id,
                finish_time=finish_time,
                elapsed_seconds=elapsed,
                punched_tx_count=tx_count,
                overtime=1,
                raw_status=remarks if remarks else "タイムオーバー",
                tx_punches={},
            )
            # Clear disqualified/absent flags
            self._competitor_dao.update(competitor_id, {"absent": 0, "disqualified": 0})

        elif status == "棄権":
            # Mark as disqualified
            self._competitor_dao.update(
                competitor_id,
                {"disqualified": 1, "disqualification_reason": "棄権", "absent": 0},
            )

        elif status == "失格（その他）":
            # Mark as disqualified with custom reason
            reason_text = self._text_reason.text().strip()
            self._competitor_dao.update(
                competitor_id,
                {"disqualified": 1, "disqualification_reason": reason_text or "失格", "absent": 0},
            )

        elif status == "欠席":
            # Mark as absent
            self._competitor_dao.update(
                competitor_id,
                {"absent": 1, "disqualified": 0},
            )

    def _get_si_base_time(self) -> Optional[str]:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute("SELECT si_base_time FROM competition LIMIT 1").fetchone()
            return row[0] if row else None
