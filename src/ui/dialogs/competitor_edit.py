from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.competitor_dao import CompetitorDAO

_CLASSES = ["", "W19", "W21", "W35", "W50", "M19", "M21", "M40", "M50", "M60"]


class CompetitorEditDialog(QDialog):
    """参加者の追加・編集ダイアログ。

    competitor_id=None のとき新規追加、整数のとき既存レコードを編集。
    """

    def __init__(
        self,
        dao: CompetitorDAO,
        competitor_id: Optional[int] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._dao = dao
        self._competitor_id = competitor_id
        self._setup_ui()
        self._retranslate_ui()
        if competitor_id is not None:
            self._load_data()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumWidth(400)
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 12, 16, 12)

        form = QFormLayout()
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._lbl_bib = QLabel()
        self._bib_edit = QLineEdit()
        self._bib_edit.setMaxLength(10)
        self._bib_edit.setFixedWidth(80)
        form.addRow(self._lbl_bib, self._bib_edit)

        self._lbl_callsign = QLabel()
        self._callsign_edit = QLineEdit()
        self._callsign_edit.setMaxLength(9)
        self._callsign_edit.setFixedWidth(120)
        form.addRow(self._lbl_callsign, self._callsign_edit)

        self._lbl_name = QLabel()
        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(12)
        form.addRow(self._lbl_name, self._name_edit)

        self._lbl_si = QLabel()
        self._si_edit = QLineEdit()
        self._si_edit.setMaxLength(10)
        self._si_edit.setFixedWidth(100)
        form.addRow(self._lbl_si, self._si_edit)

        self._lbl_class = QLabel()
        self._class_combo = QComboBox()
        self._class_combo.addItems(_CLASSES)
        self._class_combo.setFixedWidth(100)
        form.addRow(self._lbl_class, self._class_combo)

        self._lbl_division = QLabel()
        self._division_edit = QLineEdit()
        self._division_edit.setMaxLength(2)
        self._division_edit.setFixedWidth(60)
        form.addRow(self._lbl_division, self._division_edit)

        self._lbl_start_order = QLabel()
        self._start_order_spin = QSpinBox()
        self._start_order_spin.setRange(0, 9999)
        self._start_order_spin.setSpecialValueText("—")
        self._start_order_spin.setFixedWidth(80)
        form.addRow(self._lbl_start_order, self._start_order_spin)

        self._lbl_group = QLabel()
        self._group_edit = QLineEdit()
        self._group_edit.setMaxLength(8)
        form.addRow(self._lbl_group, self._group_edit)

        self._lbl_address = QLabel()
        self._address_edit = QLineEdit()
        self._address_edit.setMaxLength(14)
        form.addRow(self._lbl_address, self._address_edit)

        root.addLayout(form)

        btn_h = QHBoxLayout()
        btn_h.addStretch()
        self._btn_save = QPushButton()
        self._btn_save.setDefault(True)
        self._btn_save.setMinimumWidth(80)
        self._btn_cancel = QPushButton()
        self._btn_cancel.setMinimumWidth(80)
        self._btn_save.clicked.connect(self._on_save)
        self._btn_cancel.clicked.connect(self.reject)
        btn_h.addWidget(self._btn_save)
        btn_h.addWidget(self._btn_cancel)
        root.addLayout(btn_h)

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        if self._competitor_id is None:
            self.setWindowTitle(self.tr("参加者追加"))
        else:
            self.setWindowTitle(self.tr("参加者編集"))

        self._lbl_bib.setText(self.tr("ゼッケン ★"))
        self._lbl_callsign.setText(self.tr("コールサイン ★"))
        self._lbl_name.setText(self.tr("氏名 ★"))
        self._lbl_si.setText(self.tr("SIカードNo"))
        self._lbl_class.setText(self.tr("クラス"))
        self._lbl_division.setText(self.tr("区分"))
        self._lbl_start_order.setText(self.tr("スタート順"))
        self._lbl_group.setText(self.tr("グループ名"))
        self._lbl_address.setText(self.tr("住所"))

        self._btn_save.setText(self.tr("保存"))
        self._btn_cancel.setText(self.tr("キャンセル"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Data load (edit mode)
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        data = self._dao.get_by_id(self._competitor_id)
        if not data:
            return
        self._bib_edit.setText(data.get("bib_number") or "")
        self._callsign_edit.setText(data.get("call_sign") or "")
        self._name_edit.setText(data.get("name") or "")
        self._si_edit.setText(data.get("si_number") or "")
        cls = data.get("class_name") or ""
        idx = self._class_combo.findText(cls)
        self._class_combo.setCurrentIndex(max(0, idx))
        self._division_edit.setText(data.get("division") or "")
        self._start_order_spin.setValue(data.get("start_order") or 0)
        self._group_edit.setText(data.get("group_name") or "")
        self._address_edit.setText(data.get("address1") or "")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        bib = self._bib_edit.text().strip()
        callsign = self._callsign_edit.text().strip()
        name = self._name_edit.text().strip()
        si = self._si_edit.text().strip()

        # Required field check
        missing: list[str] = []
        if not bib:
            missing.append(self.tr("ゼッケン番号を入力してください。"))
        if not callsign:
            missing.append(self.tr("コールサインを入力してください。"))
        if not name:
            missing.append(self.tr("氏名を入力してください。"))
        if missing:
            QMessageBox.warning(self, self.tr("入力エラー"), "\n".join(missing))
            return

        # Duplicate checks
        ex = self._competitor_id
        if bib and self._dao.is_duplicate_bib(bib, exclude_id=ex):
            QMessageBox.warning(
                self,
                self.tr("重複エラー"),
                self.tr("ゼッケン番号 ") + bib + self.tr(" は既に使用されています。"),
            )
            return
        if callsign and self._dao.is_duplicate_callsign(callsign, exclude_id=ex):
            QMessageBox.warning(
                self,
                self.tr("重複エラー"),
                self.tr("コールサイン ") + callsign + self.tr(" は既に使用されています。"),
            )
            return
        if si and self._dao.is_duplicate_si(si, exclude_id=ex):
            QMessageBox.warning(
                self,
                self.tr("重複エラー"),
                self.tr("SIカードNo ") + si + self.tr(" は既に使用されています。"),
            )
            return

        data = {
            "bib_number":  bib,
            "call_sign":   callsign,
            "name":        name,
            "si_number":   si or None,
            "class_name":  self._class_combo.currentText() or None,
            "division":    self._division_edit.text().strip() or None,
            "start_order": self._start_order_spin.value() or None,
            "group_name":  self._group_edit.text().strip() or None,
            "address1":    self._address_edit.text().strip() or None,
        }

        if self._competitor_id is None:
            self._dao.insert(data)
        else:
            self._dao.update(self._competitor_id, data)

        self.accept()
