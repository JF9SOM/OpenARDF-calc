from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QColor, QPalette, QPageLayout, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.ranking import RankedCompetitor, RankingEngine
from core.result_exporter import export_all

# Cell background colors
_COLOR_OT = QColor("#FFF3CD")   # overtime: amber tint
_COLOR_DSQ = QColor("#EBEBEB")  # absent / disqualified: gray

# (db_field_key, header) for the main results table
_RESULT_COLS = (
    ("rank",             "順位"),
    ("bib_number",       "ゼッケン"),
    ("call_sign",        "コールサイン"),
    ("name",             "氏名"),
    ("class_name",       "クラス"),
    ("punched_tx_count", "探索TX数"),
    ("elapsed_str",      "タイム"),
    ("remark",           "備考"),
)


class ResultsWindow(QMainWindow):
    """競技結果表示ウィンドウ。

    - Tab 0: 総合結果（全クラス）
    - Tab 1: クラス別（クラス選択）
    - Tab 2: ラップタイム（各TX時刻）
    """

    def __init__(self, db_path: Path, competition_name: str = "", parent=None):
        super().__init__(parent)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#E8EEF4"))
        self.setPalette(pal)
        self._db_path = db_path
        self._competition_name = competition_name
        self._engine = RankingEngine(db_path)
        self._ranked: list[RankedCompetitor] = []
        self._by_class: dict[str, list[RankedCompetitor]] = {}

        self._setup_ui()
        self._retranslate_ui()
        self._reload()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumSize(1000, 600)

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

        self._action_reload = QAction(self)
        self._action_print = QAction(self)
        self._action_export = QAction(self)
        tb.addAction(self._action_reload)
        tb.addSeparator()
        tb.addAction(self._action_print)
        tb.addAction(self._action_export)

        self._action_reload.triggered.connect(self._reload)
        self._action_print.triggered.connect(self._on_print)
        self._action_export.triggered.connect(self._on_export)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #E8EEF4; }
            QTabBar::tab {
                background: #D0DCE8; border: 1px solid #b0c4d8;
                padding: 5px 16px; margin-right: 2px;
            }
            QTabBar::tab:selected { background: #ffffff; border-bottom: none; }
        """)
        self.setCentralWidget(self._tabs)

        # Tab 0: 総合結果
        self._tab_general = QWidget()
        self._tbl_general = self._make_result_table(show_class=True)
        lay0 = QVBoxLayout(self._tab_general)
        lay0.setContentsMargins(0, 0, 0, 0)
        lay0.addWidget(self._tbl_general)
        self._tabs.addTab(self._tab_general, "")

        # Tab 1: クラス別
        self._tab_class = QWidget()
        lay1 = QVBoxLayout(self._tab_class)
        lay1.setContentsMargins(4, 4, 4, 4)
        lay1.setSpacing(4)
        selector_row = QHBoxLayout()
        self._lbl_class_sel = QLabel()
        self._combo_class = QComboBox()
        self._combo_class.setMinimumWidth(100)
        self._combo_class.currentIndexChanged.connect(self._on_class_changed)
        selector_row.addWidget(self._lbl_class_sel)
        selector_row.addWidget(self._combo_class)
        selector_row.addStretch()
        lay1.addLayout(selector_row)
        self._tbl_class = self._make_result_table(show_class=False)
        lay1.addWidget(self._tbl_class)
        self._tabs.addTab(self._tab_class, "")

        # Tab 2: ラップタイム
        self._tab_lap = QWidget()
        lay2 = QVBoxLayout(self._tab_lap)
        lay2.setContentsMargins(0, 0, 0, 0)
        self._tbl_lap = QTableWidget()
        self._tbl_lap.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl_lap.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl_lap.setAlternatingRowColors(True)
        self._tbl_lap.verticalHeader().setVisible(False)
        self._tbl_lap.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._tbl_lap.setStyleSheet(self._table_style())
        lay2.addWidget(self._tbl_lap)
        self._tabs.addTab(self._tab_lap, "")

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "QStatusBar { background-color: #D0DCE8; border-top: 1px solid #b0c4d8; }"
        )
        self._count_label = QLabel()
        self._status_bar.addPermanentWidget(self._count_label)
        self.setStatusBar(self._status_bar)

    @staticmethod
    def _table_style() -> str:
        return """
            QTableWidget {
                background: #ffffff; alternate-background-color: #f0f5fa;
                gridline-color: #d0dce8; border: none;
            }
            QHeaderView::section {
                background-color: #4a6fa0; color: white;
                border: none; border-right: 1px solid #3a5f90;
                border-bottom: 1px solid #3a5f90; padding: 4px 8px; font-weight: bold;
            }
        """

    def _make_result_table(self, show_class: bool) -> QTableWidget:
        cols = _RESULT_COLS if show_class else [c for c in _RESULT_COLS if c[0] != "class_name"]
        tbl = QTableWidget()
        tbl.setColumnCount(len(cols))
        tbl.setHorizontalHeaderLabels([h for _, h in cols])
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.setSortingEnabled(False)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.setStyleSheet(self._table_style())
        return tbl

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self) -> None:
        base = self.tr("競技結果")
        self.setWindowTitle(
            f"{self._competition_name} — {base}" if self._competition_name else base
        )
        self._action_reload.setText(self.tr("再計算"))
        self._action_print.setText(self.tr("印刷"))
        self._action_export.setText(self.tr("CSV出力"))
        self._tabs.setTabText(0, self.tr("総合結果"))
        self._tabs.setTabText(1, self.tr("クラス別"))
        self._tabs.setTabText(2, self.tr("ラップタイム"))
        self._lbl_class_sel.setText(self.tr("クラス:"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _reload(self) -> None:
        try:
            self._ranked = self._engine.compute()
            self._by_class = self._engine.compute_by_class()
        except Exception as exc:
            QMessageBox.critical(self, self.tr("エラー"), str(exc))
            return

        self._fill_general_table()
        self._fill_class_combo()
        self._fill_lap_table()

        total = len(self._ranked)
        ranked_count = sum(1 for r in self._ranked if r.rank is not None)
        self._count_label.setText(
            self.tr("登録数: ") + str(total) + self.tr(" 名　ランク: ") + str(ranked_count) + self.tr(" 名")
        )

    def _fill_general_table(self) -> None:
        self._fill_result_table(self._tbl_general, self._ranked, show_class=True)

    def _fill_class_combo(self) -> None:
        self._combo_class.blockSignals(True)
        current = self._combo_class.currentText()
        self._combo_class.clear()
        for cls in sorted(self._by_class.keys()):
            self._combo_class.addItem(cls)
        idx = self._combo_class.findText(current)
        self._combo_class.setCurrentIndex(max(0, idx))
        self._combo_class.blockSignals(False)
        self._on_class_changed()

    def _on_class_changed(self) -> None:
        cls = self._combo_class.currentText()
        self._fill_result_table(
            self._tbl_class,
            self._by_class.get(cls, []),
            show_class=False,
        )

    def _fill_result_table(
        self,
        tbl: QTableWidget,
        data: list[RankedCompetitor],
        show_class: bool,
    ) -> None:
        cols = _RESULT_COLS if show_class else [c for c in _RESULT_COLS if c[0] != "class_name"]
        tbl.setRowCount(len(data))

        prev_class = None
        for row, rc in enumerate(data):
            # Class separator: bold bib cell when class changes (general table only)
            if show_class and rc.class_name != prev_class:
                prev_class = rc.class_name

            for col, (key, _) in enumerate(cols):
                val = getattr(rc, key)
                if key == "punched_tx_count" and not rc.is_ranked:
                    val = ""
                elif key == "elapsed_str" and not rc.is_ranked:
                    val = ""
                elif key == "rank":
                    val = str(val) if val is not None else "—"
                else:
                    val = str(val) if val is not None else ""

                item = QTableWidgetItem(str(val))
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                    if key in ("rank", "punched_tx_count", "bib_number")
                    else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )

                if rc.absent or rc.disqualified:
                    item.setBackground(_COLOR_DSQ)
                elif rc.overtime:
                    item.setBackground(_COLOR_OT)

                tbl.setItem(row, col, item)

    def _fill_lap_table(self) -> None:
        max_tx = max(
            (max(rc.tx_punches.keys(), default=0) for rc in self._ranked),
            default=0,
        )
        tx_headers = [f"TX{i}" for i in range(1, max_tx + 1)]
        base_headers = ["ゼッケン", "コールサイン", "氏名", "クラス"]
        all_headers = base_headers + tx_headers + [self.tr("フィニッシュ")]

        self._tbl_lap.setColumnCount(len(all_headers))
        self._tbl_lap.setHorizontalHeaderLabels(all_headers)
        self._tbl_lap.setRowCount(len(self._ranked))

        for row, rc in enumerate(self._ranked):
            row_data = [rc.bib_number, rc.call_sign, rc.name, rc.class_name]
            row_data += [rc.tx_punches.get(i, "") for i in range(1, max_tx + 1)]
            row_data.append(rc.finish_time or "")

            for col, val in enumerate(row_data):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if rc.absent or rc.disqualified:
                    item.setBackground(_COLOR_DSQ)
                elif rc.overtime:
                    item.setBackground(_COLOR_OT)
                self._tbl_lap.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Print
    # ------------------------------------------------------------------

    def _on_print(self) -> None:
        if not self._ranked:
            QMessageBox.information(self, self.tr("印刷"), self.tr("印刷するデータがありません。"))
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return

        doc = QTextDocument()
        doc.setHtml(self._build_print_html())
        doc.print_(printer)

    def _build_print_html(self) -> str:
        css = """
        body { font-family: sans-serif; font-size: 9pt; margin: 0; }
        h2 { font-size: 12pt; color: #2a4f80; margin: 6px 0 4px; page-break-before: always; }
        h2.first { page-break-before: avoid; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 8px; }
        th { background: #4a6fa0; color: white; padding: 3px 6px;
             font-size: 8pt; text-align: center; }
        td { padding: 2px 5px; border-bottom: 1px solid #ddd; font-size: 8pt; }
        .center { text-align: center; }
        .ot  { background: #fff3cd; }
        .dsq { background: #ebebeb; color: #888; }
        """
        rows_html = []
        first_class = True
        for cls, competitors in sorted(self._by_class.items()):
            cls_class = "first" if first_class else ""
            first_class = False
            rows_html.append(f'<h2 class="{cls_class}">クラス: {cls}</h2>')
            rows_html.append(
                "<table><tr>"
                "<th>順位</th><th>ゼッケン</th><th>コールサイン</th>"
                "<th>氏名</th><th>探索TX数</th><th>タイム</th><th>備考</th>"
                "</tr>"
            )
            for rc in competitors:
                row_cls = "dsq" if (rc.absent or rc.disqualified) else ("ot" if rc.overtime else "")
                rank_str = str(rc.rank) if rc.rank else "—"
                tx_str = str(rc.punched_tx_count) if rc.is_ranked else ""
                time_str = rc.elapsed_str if rc.is_ranked else ""
                rows_html.append(
                    f'<tr class="{row_cls}">'
                    f'<td class="center">{rank_str}</td>'
                    f'<td class="center">{rc.bib_number}</td>'
                    f'<td>{rc.call_sign}</td>'
                    f'<td>{rc.name}</td>'
                    f'<td class="center">{tx_str}</td>'
                    f'<td class="center">{time_str}</td>'
                    f'<td>{rc.remark}</td>'
                    f"</tr>"
                )
            rows_html.append("</table>")

        content = "\n".join(rows_html)
        return f"<html><head><style>{css}</style></head><body>{content}</body></html>"

    # ------------------------------------------------------------------
    # CSV Export
    # ------------------------------------------------------------------

    def _on_export(self) -> None:
        if not self._ranked:
            QMessageBox.information(self, self.tr("CSV出力"), self.tr("出力するデータがありません。"))
            return

        out_dir = QFileDialog.getExistingDirectory(
            self,
            self.tr("CSV出力フォルダを選択"),
            str(Path.home()),
        )
        if not out_dir:
            return

        try:
            files = export_all(self._ranked, Path(out_dir))
        except Exception as exc:
            QMessageBox.critical(
                self, self.tr("出力エラー"),
                self.tr("CSV出力に失敗しました:\n") + str(exc),
            )
            return

        names = "\n".join(Path(f).name for f in files)
        QMessageBox.information(
            self, self.tr("CSV出力完了"),
            self.tr("以下のファイルを出力しました:\n\n") + names
            + "\n\n" + self.tr("保存先: ") + out_dir,
        )
