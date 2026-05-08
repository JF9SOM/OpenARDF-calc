from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QDate, QEvent, QTime, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)


class CompetitionSettingsDialog(QDialog):
    """競技内容設定ダイアログ。

    「保存」ボタン押下時にファイル保存ダイアログを開き、
    選択した場所に .ardf SQLite ファイルを作成して設定を書き込む。
    """

    _CLASSES = ("W19", "W21", "W35", "W50", "M19", "M21", "M40", "M50", "M60")
    _DEFAULT_WINNERS: dict[str, int] = {"M60": 2}

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
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #b0c4d8;
                border-radius: 4px;
                margin-top: 16px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        self._db_path: Optional[Path] = None
        self._competition_id: Optional[int] = None
        self._setup_ui()
        self._retranslate_ui()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def db_path(self) -> Optional[Path]:
        return self._db_path

    @property
    def competition_id(self) -> Optional[int]:
        return self._competition_id

    @property
    def competition_name(self) -> str:
        return self._name_edit.text().strip()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setMinimumWidth(560)
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── カスタムタイトルバー ──────────────────────────────
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
        root.setSpacing(10)
        root.setContentsMargins(16, 12, 16, 12)
        outer.addLayout(root)

        # ── 基本設定フォーム ──────────────────────────────────
        form = QFormLayout()
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self._lbl_name = QLabel()
        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(40)
        form.addRow(self._lbl_name, self._name_edit)

        self._lbl_date = QLabel()
        self._date_edit = QDateEdit(QDate.currentDate())
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy/MM/dd")
        self._date_edit.setFixedWidth(120)
        form.addRow(self._lbl_date, self._date_edit)

        self._lbl_start_time = QLabel()
        self._start_time_edit = QTimeEdit(QTime(9, 30, 0))
        self._start_time_edit.setDisplayFormat("HH:mm:ss")
        self._start_time_edit.setFixedWidth(100)
        form.addRow(self._lbl_start_time, self._start_time_edit)

        bold = QFont()
        bold.setBold(True)

        self._lbl_si_base = QLabel()
        self._lbl_si_base.setFont(bold)
        self._si_base_edit = QTimeEdit(QTime(8, 0, 0))
        self._si_base_edit.setDisplayFormat("HH:mm:ss")
        self._si_base_edit.setFixedWidth(100)
        self._si_base_edit.setFont(bold)
        form.addRow(self._lbl_si_base, self._si_base_edit)

        self._lbl_group_count = QLabel()
        self._group_count_spin = QSpinBox()
        self._group_count_spin.setRange(1, 10)
        self._group_count_spin.setValue(3)
        self._group_count_spin.setFixedWidth(60)
        form.addRow(self._lbl_group_count, self._group_count_spin)

        root.addLayout(form)

        # ── TX探索設定 ────────────────────────────────────────
        self._tx_group = QGroupBox()
        tx_v = QVBoxLayout(self._tx_group)
        tx_v.setSpacing(4)

        self._chk_all_tx = QCheckBox()
        self._chk_w50_m60 = QCheckBox()
        self._chk_beacon = QCheckBox()
        for chk in (self._chk_all_tx, self._chk_w50_m60, self._chk_beacon):
            tx_v.addWidget(chk)

        root.addWidget(self._tx_group)

        # ── 入賞者数（クラス別） ──────────────────────────────
        self._winners_group = QGroupBox()
        grid = QGridLayout(self._winners_group)
        grid.setSpacing(6)

        self._winner_spins: dict[str, QSpinBox] = {}
        for col, cls in enumerate(self._CLASSES):
            lbl = QLabel(cls)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spin = QSpinBox()
            spin.setRange(0, 20)
            spin.setValue(self._DEFAULT_WINNERS.get(cls, 3))
            spin.setFixedWidth(52)
            grid.addWidget(lbl, 0, col)
            grid.addWidget(spin, 1, col)
            self._winner_spins[cls] = spin

        root.addWidget(self._winners_group)

        # ── フッター（ボタンエリア） ──────────────────────────
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
        self.setWindowTitle(self.tr("新規大会の設定"))
        self._header_label.setText(self.tr("新規大会の設定"))

        self._lbl_name.setText(self.tr("大会名称"))
        self._lbl_date.setText(self.tr("開催年月日"))
        self._lbl_start_time.setText(self.tr("1組スタート時間"))
        self._lbl_si_base.setText(self.tr("SI基準時間  ★重要★"))
        self._lbl_group_count.setText(self.tr("グループ成績対象人数"))

        self._tx_group.setTitle(self.tr("TX探索設定"))
        self._chk_all_tx.setText(self.tr("全TX探索する"))
        self._chk_w50_m60.setText(self.tr("W50・M60任意探索"))
        self._chk_beacon.setText(self.tr("ビーコンを探索する"))

        self._winners_group.setTitle(self.tr("入賞者数（クラス別）"))

        self._btn_save.setText(self.tr("保存"))
        self._btn_cancel.setText(self.tr("キャンセル"))

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Save handler
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                self.tr("入力エラー"),
                self.tr("大会名称を入力してください。"),
            )
            self._name_edit.setFocus()
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("大会ファイルの保存先を選択"),
            str(Path.home()),
            self.tr("大会ファイル (*.ardf);;すべてのファイル (*)"),
        )
        if not path:
            return  # ファイルダイアログをキャンセル → 設定ダイアログは閉じない

        db_path = Path(path)
        if not db_path.suffix:
            db_path = db_path.with_suffix(".ardf")

        if db_path.exists():
            db_path.unlink()

        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            _create_tables(conn)

            w = self._winner_spins
            cur = conn.execute(
                """
                INSERT INTO competition (
                    name, date, start_time_g1, si_base_time,
                    all_tx_search, w50_m60_optional, beacon_search,
                    group_score_count,
                    winners_w19, winners_w21, winners_w35, winners_w50,
                    winners_m19, winners_m21, winners_m40, winners_m50, winners_m60
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    name,
                    self._date_edit.date().toString("yyyy-MM-dd"),
                    self._start_time_edit.time().toString("HH:mm:ss"),
                    self._si_base_edit.time().toString("HH:mm:ss"),
                    int(self._chk_all_tx.isChecked()),
                    int(self._chk_w50_m60.isChecked()),
                    int(self._chk_beacon.isChecked()),
                    self._group_count_spin.value(),
                    w["W19"].value(), w["W21"].value(),
                    w["W35"].value(), w["W50"].value(),
                    w["M19"].value(), w["M21"].value(),
                    w["M40"].value(), w["M50"].value(),
                    w["M60"].value(),
                ),
            )
            conn.commit()
            self._competition_id = cur.lastrowid
            self._db_path = db_path
        except Exception as exc:
            QMessageBox.critical(
                self,
                self.tr("保存エラー"),
                self.tr("保存中にエラーが発生しました:\n") + str(exc),
            )
            return
        finally:
            conn.close()

        self.accept()


# ------------------------------------------------------------------
# Module-level helper — shared schema used by database.py too
# ------------------------------------------------------------------

def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS competition (
            id                  INTEGER PRIMARY KEY,
            name                TEXT    NOT NULL,
            date                TEXT,
            start_time_g1       TEXT,
            si_base_time        TEXT,
            all_tx_search       INTEGER NOT NULL DEFAULT 0,
            w50_m60_optional    INTEGER NOT NULL DEFAULT 0,
            beacon_search       INTEGER NOT NULL DEFAULT 0,
            group_score_count   INTEGER NOT NULL DEFAULT 3,
            winners_w19         INTEGER NOT NULL DEFAULT 3,
            winners_w21         INTEGER NOT NULL DEFAULT 3,
            winners_w35         INTEGER NOT NULL DEFAULT 3,
            winners_w50         INTEGER NOT NULL DEFAULT 3,
            winners_m19         INTEGER NOT NULL DEFAULT 3,
            winners_m21         INTEGER NOT NULL DEFAULT 3,
            winners_m40         INTEGER NOT NULL DEFAULT 3,
            winners_m50         INTEGER NOT NULL DEFAULT 3,
            winners_m60         INTEGER NOT NULL DEFAULT 2,
            created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS competitor (
            id                      INTEGER PRIMARY KEY,
            bib_number              TEXT,
            si_number               TEXT,
            call_sign               TEXT,
            name                    TEXT,
            class_name              TEXT,
            birthday                TEXT,
            division                TEXT,
            start_order             INTEGER,
            group_name              TEXT,
            address1                TEXT,
            address2                TEXT,
            tel                     TEXT,
            email                   TEXT,
            region                  TEXT,
            prefecture              TEXT,
            absent                  INTEGER NOT NULL DEFAULT 0,
            disqualified            INTEGER NOT NULL DEFAULT 0,
            disqualification_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS punch_record (
            id              INTEGER PRIMARY KEY,
            competitor_id   INTEGER REFERENCES competitor(id),
            control_code    TEXT,
            punch_time      TEXT
        );
        """
    )
