from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
)

from core.competitor_dao import CompetitorDAO
from ui.dialogs.competitor_edit import CompetitorEditDialog

# (db_field, japanese_header) — order matches table columns
_COLS: tuple[tuple[str, str], ...] = (
    ("bib_number",  "ゼッケン"),
    ("call_sign",   "コールサイン"),
    ("name",        "氏名"),
    ("si_number",   "SIカードNo"),
    ("class_name",  "クラス"),
    ("division",    "区分"),
    ("start_order", "スタート順"),
    ("group_name",  "グループ名"),
    ("address1",    "住所"),
)


class CompetitorsWindow(QMainWindow):
    """参加者管理ウィンドウ。"""

    def __init__(
        self,
        db_path: Path,
        competition_name: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._dao = CompetitorDAO(db_path)
        self._competition_name = competition_name
        self._setup_ui()
        self._retranslate_ui()
        self._load_table()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumSize(900, 500)

        # Toolbar
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)

        self._action_add = QAction(self)
        self._action_delete = QAction(self)
        self._action_import = QAction(self)
        self._action_export = QAction(self)

        tb.addAction(self._action_add)
        tb.addAction(self._action_delete)
        tb.addSeparator()
        tb.addAction(self._action_import)
        tb.addAction(self._action_export)

        self._action_add.triggered.connect(self._on_add)
        self._action_delete.triggered.connect(self._on_delete)
        self._action_import.triggered.connect(self._on_import_csv)
        self._action_export.triggered.connect(self._on_export_csv)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLS))
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_clicked)
        self.setCentralWidget(self._table)

        # Status bar with count
        self._status_bar = QStatusBar()
        self._count_label = QLabel()
        self._status_bar.addPermanentWidget(self._count_label)
        self.setStatusBar(self._status_bar)

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        base = self.tr("参加者管理")
        self.setWindowTitle(
            f"{self._competition_name} — {base}" if self._competition_name else base
        )

        self._table.setHorizontalHeaderLabels(
            [self.tr(h) for _, h in _COLS]
        )

        self._action_add.setText(self.tr("追加"))
        self._action_delete.setText(self.tr("削除"))
        self._action_import.setText(self.tr("CSV読み込み"))
        self._action_export.setText(self.tr("CSV書き出し"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_table(self) -> None:
        self._table.setSortingEnabled(False)
        competitors = self._dao.get_all()
        self._table.setRowCount(len(competitors))

        for row, c in enumerate(competitors):
            for col, (field, _) in enumerate(_COLS):
                val = c.get(field)
                text = str(val) if val is not None else ""
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, c["id"])
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)
        n = len(competitors)
        self._count_label.setText(self.tr("登録数: ") + str(n) + self.tr(" 名"))

    def _selected_id(self) -> Optional[int]:
        items = self._table.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        dlg = CompetitorEditDialog(self._dao, parent=self)
        if dlg.exec():
            self._load_table()

    def _on_double_clicked(self, index) -> None:
        item = self._table.item(index.row(), 0)
        if item is None:
            return
        competitor_id = item.data(Qt.ItemDataRole.UserRole)
        dlg = CompetitorEditDialog(self._dao, competitor_id=competitor_id, parent=self)
        if dlg.exec():
            self._load_table()

    def _on_delete(self) -> None:
        competitor_id = self._selected_id()
        if competitor_id is None:
            QMessageBox.information(
                self,
                self.tr("削除"),
                self.tr("削除する参加者を選択してください。"),
            )
            return

        c = self._dao.get_by_id(competitor_id)
        label = (
            f"{c.get('bib_number', '')}  {c.get('name', '')}"
            if c
            else str(competitor_id)
        )

        reply = QMessageBox.question(
            self,
            self.tr("削除の確認"),
            self.tr("以下の参加者を削除しますか？\n\n") + label,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._dao.delete(competitor_id)
            self._load_table()

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("参加者CSVを開く"),
            str(Path.home()),
            self.tr("CSV ファイル (*.csv);;すべてのファイル (*)"),
        )
        if not path:
            return

        imported, errors = self._dao.import_csv(Path(path))

        msg = self.tr("読み込み完了: ") + str(imported) + self.tr(" 件")
        if errors:
            shown = errors[:10]
            msg += "\n\n" + self.tr("以下のエラーが発生しました:\n") + "\n".join(shown)
            if len(errors) > 10:
                msg += f"\n... 他 {len(errors) - 10} 件"
            QMessageBox.warning(self, self.tr("CSV読み込み"), msg)
        else:
            QMessageBox.information(self, self.tr("CSV読み込み"), msg)

        self._load_table()

    def _on_export_csv(self) -> None:
        default_name = (
            f"{self._competition_name}_参加者データ.csv"
            if self._competition_name
            else "参加者データ.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("参加者CSVを保存"),
            str(Path.home() / default_name),
            self.tr("CSV ファイル (*.csv);;すべてのファイル (*)"),
        )
        if not path:
            return

        exported = self._dao.export_csv(Path(path))
        QMessageBox.information(
            self,
            self.tr("CSV書き出し"),
            self.tr("書き出し完了: ") + str(exported) + self.tr(" 件"),
        )
