from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.competitor_dao import CompetitorDAO
from ui.dialogs.manual_result_dialog import ManualResultDialog

# Table columns: (db_field, header)
_COLS = (
    ("bib_number", "ゼッケン"),
    ("call_sign", "コールサイン"),
    ("name", "氏名"),
    ("class_name", "クラス"),
    ("state", "状態"),  # Special: computed, not from DB
)


class ManualResultsWindow(QMainWindow):
    """棄権・失格登録ウィンドウ。

    未入力の選手（結果・欠席・失格がまだ登録されていない選手）を
    一覧表示し、個別に結果を手動入力する。
    """

    def __init__(
        self,
        db_path: Path,
        competition_name: str = "",
        parent=None,
    ):
        super().__init__(parent)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#E8EEF4"))
        self.setPalette(pal)
        self._db_path = db_path
        self._competition_name = competition_name
        self._dao = CompetitorDAO(db_path)
        self._show_unregistered_only = True

        self._setup_ui()
        self._retranslate_ui()
        self._load_data()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumSize(900, 500)

        # Toolbar
        tb = QToolBar()
        tb.setMovable(False)
        tb.setStyleSheet("""
            QToolBar {
                background-color: #E8EEF4;
                border-bottom: 1px solid #b0c4d8;
                spacing: 4px; padding: 2px;
            }
            QToolButton {
                border: 1px solid transparent; border-radius: 3px; padding: 3px 8px;
            }
            QToolButton:hover { background-color: #d0dce8; border-color: #b0c4d8; }
            QToolButton:pressed { background-color: #b8ccd8; }
        """)
        self.addToolBar(tb)

        self._chk_unregistered_only = QCheckBox()
        self._chk_unregistered_only.setChecked(True)
        self._chk_unregistered_only.stateChanged.connect(self._on_filter_changed)
        tb.addWidget(self._chk_unregistered_only)

        tb.addSeparator()
        self._action_edit = QAction(self)
        self._action_edit.setEnabled(False)
        self._action_edit.triggered.connect(self._on_edit_clicked)
        tb.addAction(self._action_edit)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLS))
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._on_double_clicked)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f0f5fa;
                gridline-color: #d0dce8;
                border: none;
            }
            QHeaderView::section {
                background-color: #dce6f0;
                border: none;
                border-right: 1px solid #b0c4d8;
                border-bottom: 1px solid #b0c4d8;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
        self.setCentralWidget(self._table)

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "QStatusBar { background-color: #D0DCE8; border-top: 1px solid #b0c4d8; }"
        )
        self._count_label = QLabel()
        self._status_bar.addPermanentWidget(self._count_label)
        self.setStatusBar(self._status_bar)

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        base = self.tr("棄権・失格登録")
        self.setWindowTitle(
            f"{self._competition_name} — {base}" if self._competition_name else base
        )

        self._table.setHorizontalHeaderLabels([self.tr(h) for _, h in _COLS])
        self._chk_unregistered_only.setText(self.tr("未入力者のみ表示"))
        self._action_edit.setText(self.tr("編集"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        self._table.setSortingEnabled(False)

        # Fetch all competitors with their states
        all_competitors = self._get_competitors_with_states()

        # Filter
        if self._show_unregistered_only:
            competitors = [c for c in all_competitors if c["state"] == self.tr("未入力")]
        else:
            competitors = all_competitors

        # Fill table
        self._table.setRowCount(len(competitors))
        for row, c in enumerate(competitors):
            for col, (field, _) in enumerate(_COLS):
                val = c.get(field, "")
                text = str(val) if val is not None else ""
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, c["id"])  # Store competitor_id
                if field == "name":
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)

        self._table.setSortingEnabled(True)

        # Update status bar
        unregistered_count = len([c for c in all_competitors if c["state"] == self.tr("未入力")])
        total_count = len(all_competitors)
        self._count_label.setText(
            self.tr("未入力: ") + str(unregistered_count) + self.tr(" / 全: ") + str(total_count)
        )

    def _get_competitors_with_states(self) -> list[dict]:
        """Get all competitors with their registration state."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        with conn:
            rows = conn.execute("""
                SELECT
                    c.id, c.bib_number, c.call_sign, c.name, c.class_name,
                    COALESCE(c.absent, 0) AS absent,
                    COALESCE(c.disqualified, 0) AS disqualified,
                    c.disqualification_reason,
                    (SELECT COUNT(*) FROM results r WHERE r.competitor_id = c.id) AS has_result
                FROM competitor c
                ORDER BY CAST(c.bib_number AS INTEGER), c.bib_number
            """).fetchall()

        result = []
        for row in rows:
            competitor = dict(row)
            # Determine state
            if competitor["absent"]:
                state = self.tr("欠席")
            elif competitor["disqualified"]:
                state = self.tr("失格")
            elif competitor["has_result"]:
                state = self.tr("登録済み")
            else:
                state = self.tr("未入力")
            competitor["state"] = state
            result.append(competitor)
        return result

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_filter_changed(self) -> None:
        self._show_unregistered_only = self._chk_unregistered_only.isChecked()
        self._load_data()

    def _on_selection_changed(self) -> None:
        self._action_edit.setEnabled(bool(self._table.selectedItems()))

    def _on_double_clicked(self, index) -> None:
        item = self._table.item(index.row(), 0)
        if item is None:
            return
        competitor_id = item.data(Qt.ItemDataRole.UserRole)
        competitor = self._dao.get_by_id(competitor_id)
        if competitor is None:
            return
        dlg = ManualResultDialog(self._db_path, competitor, parent=self)
        if dlg.exec():
            self._load_data()

    def _on_edit_clicked(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        item = self._table.item(rows[0].row(), 0)
        if item is None:
            return
        competitor_id = item.data(Qt.ItemDataRole.UserRole)
        competitor = self._dao.get_by_id(competitor_id)
        if competitor is None:
            return
        dlg = ManualResultDialog(self._db_path, competitor, parent=self)
        if dlg.exec():
            self._load_data()
