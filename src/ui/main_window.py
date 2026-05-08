import sqlite3
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, Qt, QTranslator
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.competitor_dao import CompetitorDAO
from ui.competitors_window import CompetitorsWindow
from ui.dialogs.absence_dialog import AbsenceDialog
from ui.dialogs.competition_settings import CompetitionSettingsDialog
from ui.dialogs.si_import_dialog import SIImportDialog

TRANSLATIONS_DIR = Path(__file__).parent.parent / "translations"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._translator = QTranslator()
        self._current_lang = "ja"
        self._current_competition_name: str = ""
        self._current_db_path: Optional[Path] = None
        self._competitors_window: Optional[CompetitorsWindow] = None
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumSize(900, 600)
        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()
        self._retranslate_ui()

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _create_menu_bar(self):
        mb = self.menuBar()

        # --- File ---
        self._menu_file = mb.addMenu("")

        self._action_new = QAction(self)
        self._action_open = QAction(self)
        self._action_import_csv = QAction(self)
        self._action_import_csv.setEnabled(False)

        self._menu_si = self._menu_file.addMenu("")
        self._action_import_si_manager = QAction(self)
        self._action_import_si_manager.setEnabled(False)
        self._action_import_si_direct = QAction(self)
        self._action_import_si_direct.setEnabled(False)
        self._menu_si.addAction(self._action_import_si_manager)
        self._menu_si.addAction(self._action_import_si_direct)

        self._action_export = QAction(self)
        self._action_export.setEnabled(False)
        self._action_exit = QAction(self)

        self._menu_file.addAction(self._action_new)
        self._menu_file.addAction(self._action_open)
        self._menu_file.addSeparator()
        self._menu_file.addAction(self._action_import_csv)
        self._menu_file.addMenu(self._menu_si)
        self._menu_file.addSeparator()
        self._menu_file.addAction(self._action_export)
        self._menu_file.addSeparator()
        self._menu_file.addAction(self._action_exit)

        # --- Competition ---
        self._menu_competition = mb.addMenu("")
        self._action_comp_settings = QAction(self)
        self._action_comp_settings.setEnabled(False)
        self._action_competitors = QAction(self)
        self._action_absences = QAction(self)
        self._menu_competition.addAction(self._action_comp_settings)
        self._menu_competition.addAction(self._action_competitors)
        self._menu_competition.addAction(self._action_absences)
        # Disabled until a competition is open
        self._action_competitors.setEnabled(False)
        self._action_absences.setEnabled(False)

        # --- Results ---
        self._menu_results = mb.addMenu("")
        self._action_calc_rankings = QAction(self)
        self._action_view_results = QAction(self)
        self._action_print_results = QAction(self)
        self._menu_results.addAction(self._action_calc_rankings)
        self._menu_results.addAction(self._action_view_results)
        self._menu_results.addAction(self._action_print_results)

        # --- Help ---
        self._menu_help = mb.addMenu("")
        self._action_about = QAction(self)
        self._action_manual = QAction(self)
        self._menu_help.addAction(self._action_about)
        self._menu_help.addAction(self._action_manual)

        # Connections
        self._action_new.triggered.connect(self._on_new_competition)
        self._action_open.triggered.connect(self._on_open_competition)
        self._action_import_csv.triggered.connect(self._on_import_participant_csv)
        self._action_import_si_manager.triggered.connect(self._on_import_si_manager)
        self._action_exit.triggered.connect(self.close)
        self._action_comp_settings.triggered.connect(self._on_comp_settings)
        self._action_competitors.triggered.connect(self._on_competitors)
        self._action_absences.triggered.connect(self._on_absences)
        self._action_about.triggered.connect(self._on_about)

    # ------------------------------------------------------------------
    # Central widget
    # ------------------------------------------------------------------

    def _create_central_widget(self):
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 8, 12, 8)

        # Language switch bar (top-right)
        lang_bar = QHBoxLayout()
        lang_bar.addStretch()

        self._btn_ja = QPushButton("日本語")
        self._btn_en = QPushButton("English")
        self._btn_ja.setCheckable(True)
        self._btn_en.setCheckable(True)
        self._btn_ja.setChecked(True)
        self._btn_ja.setFixedWidth(80)
        self._btn_en.setFixedWidth(80)

        self._btn_ja.clicked.connect(lambda: self._switch_language("ja"))
        self._btn_en.clicked.connect(lambda: self._switch_language("en"))

        lang_bar.addWidget(self._btn_ja)
        lang_bar.addWidget(self._btn_en)
        root_layout.addLayout(lang_bar)

        # Welcome / current competition area
        self._label_welcome = QLabel()
        self._label_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._label_welcome.font()
        font.setPointSize(14)
        self._label_welcome.setFont(font)
        root_layout.addWidget(self._label_welcome, stretch=1)

        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _create_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    # ------------------------------------------------------------------
    # Retranslation
    # ------------------------------------------------------------------

    def _retranslate_ui(self):
        base_title = self.tr("OpenARDF-calc - ARDF競技集計ソフト")
        if self._current_competition_name:
            self.setWindowTitle(f"{self._current_competition_name} — {base_title}")
        else:
            self.setWindowTitle(base_title)

        self._menu_file.setTitle(self.tr("ファイル"))
        self._action_new.setText(self.tr("新規大会"))
        self._action_open.setText(self.tr("大会を開く"))
        self._action_import_csv.setText(self.tr("参加者データ読み込み CSV"))
        self._menu_si.setTitle(self.tr("SIデータ読み込み"))
        self._action_import_si_manager.setText(self.tr("SI Manager CSV から読み込み"))
        self._action_import_si_direct.setText(self.tr("SIリーダーから直接読み込み"))
        self._action_export.setText(self.tr("結果を出力"))
        self._action_exit.setText(self.tr("終了"))

        self._menu_competition.setTitle(self.tr("競技"))
        self._action_comp_settings.setText(self.tr("競技設定"))
        self._action_competitors.setText(self.tr("参加者管理"))
        self._action_absences.setText(self.tr("欠席登録"))

        self._menu_results.setTitle(self.tr("結果"))
        self._action_calc_rankings.setText(self.tr("順位集計"))
        self._action_view_results.setText(self.tr("結果表示"))
        self._action_print_results.setText(self.tr("結果印刷"))

        self._menu_help.setTitle(self.tr("ヘルプ"))
        self._action_about.setText(self.tr("このソフトについて"))
        self._action_manual.setText(self.tr("マニュアル"))

        if self._current_competition_name:
            self._label_welcome.setText(
                self.tr("開催中の大会: ") + self._current_competition_name
            )
        else:
            self._label_welcome.setText(
                self.tr(
                    "OpenARDF-calc へようこそ\n\n"
                    "大会を作成するか、既存の大会を開いてください。"
                )
            )

        if not self._current_competition_name:
            self._status_bar.showMessage(self.tr("準備完了"))

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Language switching
    # ------------------------------------------------------------------

    def _switch_language(self, lang: str):
        if lang == self._current_lang:
            self._btn_ja.setChecked(lang == "ja")
            self._btn_en.setChecked(lang == "en")
            return

        app = QApplication.instance()

        if self._current_lang != "ja":
            app.removeTranslator(self._translator)

        if lang == "en":
            qm_path = TRANSLATIONS_DIR / "en.qm"
            if not qm_path.exists():
                QMessageBox.warning(
                    self,
                    "Warning",
                    (
                        f"Translation file not found:\n{qm_path}\n\n"
                        "Run:  python scripts/build_translations.py"
                    ),
                )
                self._btn_ja.setChecked(True)
                self._btn_en.setChecked(False)
                return
            self._translator.load(str(qm_path))
            app.installTranslator(self._translator)

        self._current_lang = lang
        self._btn_ja.setChecked(lang == "ja")
        self._btn_en.setChecked(lang == "en")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_new_competition(self):
        dlg = CompetitionSettingsDialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._set_current_competition(dlg.competition_name, dlg.db_path)

    def _set_current_competition(self, name: str, db_path: Path, opened: bool = False) -> None:
        self._current_competition_name = name
        self._current_db_path = db_path
        base_title = self.tr("OpenARDF-calc - ARDF競技集計ソフト")
        self.setWindowTitle(f"{name} — {base_title}")
        self._label_welcome.setText(self.tr("開催中の大会: ") + name)
        msg = self.tr("大会を開きました: ") if opened else self.tr("大会を作成しました: ")
        self._status_bar.showMessage(msg + name)
        # Enable competition-specific menu actions
        self._action_competitors.setEnabled(True)
        self._action_absences.setEnabled(True)
        self._action_import_csv.setEnabled(True)
        self._action_import_si_manager.setEnabled(True)
        self._action_export.setEnabled(True)
        self._action_comp_settings.setEnabled(True)

    def _on_competitors(self) -> None:
        if self._current_db_path is None:
            return
        # Bring existing window to front if already open
        if self._competitors_window is not None:
            self._competitors_window.raise_()
            self._competitors_window.activateWindow()
            return
        self._competitors_window = CompetitorsWindow(
            self._current_db_path,
            competition_name=self._current_competition_name,
            parent=None,  # independent window
        )
        self._competitors_window.destroyed.connect(
            lambda: setattr(self, "_competitors_window", None)
        )
        self._competitors_window.show()

    def _on_open_competition(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("大会ファイルを開く"),
            str(Path.home()),
            self.tr("大会ファイル (*.ardf);;すべてのファイル (*)"),
        )
        if not path:
            return
        db_path = Path(path)
        try:
            conn = sqlite3.connect(str(db_path))
            row = conn.execute("SELECT name FROM competition LIMIT 1").fetchone()
            conn.close()
        except Exception as exc:
            QMessageBox.critical(
                self, self.tr("エラー"),
                self.tr("大会ファイルを開けませんでした:\n") + str(exc),
            )
            return
        if row is None:
            QMessageBox.warning(
                self, self.tr("エラー"),
                self.tr("有効な大会ファイルではありません。"),
            )
            return
        self._set_current_competition(row[0], db_path, opened=True)

    def _on_import_participant_csv(self) -> None:
        if self._current_db_path is None:
            QMessageBox.information(
                self, self.tr("CSV読み込み"),
                self.tr("先に大会を作成または開いてください。"),
            )
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("参加者CSVを開く"),
            str(Path.home()),
            self.tr("CSV ファイル (*.csv);;すべてのファイル (*)"),
        )
        if not path:
            return
        dao = CompetitorDAO(self._current_db_path)
        imported, errors = dao.import_csv(Path(path))
        msg = self.tr("読み込み完了: ") + str(imported) + self.tr(" 件")
        if errors:
            shown = errors[:10]
            msg += "\n\n" + self.tr("以下のエラーが発生しました:\n") + "\n".join(shown)
            if len(errors) > 10:
                msg += f"\n... 他 {len(errors) - 10} 件"
            QMessageBox.warning(self, self.tr("CSV読み込み"), msg)
        else:
            QMessageBox.information(self, self.tr("CSV読み込み"), msg)

    def _on_import_si_manager(self) -> None:
        if self._current_db_path is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("SI Manager CSV を選択"),
            str(Path.home()),
            self.tr("CSV ファイル (*.csv);;すべてのファイル (*)"),
        )
        if not path:
            return
        dlg = SIImportDialog(self._current_db_path, parent=self)
        dlg._run_import(Path(path))
        dlg.exec()

    def _on_comp_settings(self) -> None:
        if self._current_db_path is None:
            QMessageBox.information(
                self, self.tr("競技設定"),
                self.tr("先に大会を作成または開いてください。"),
            )
            return
        try:
            conn = sqlite3.connect(str(self._current_db_path))
            row = conn.execute("SELECT * FROM competition LIMIT 1").fetchone()
            conn.close()
        except Exception:
            return
        if row is None:
            return
        keys = [
            "name", "date", "start_time_g1", "si_base_time",
            "group_score_count",
        ]
        info = "\n".join(
            f"{k}: {row[k]}" for k in keys if row[k] is not None
        )
        QMessageBox.information(
            self, self.tr("競技設定"),
            self.tr("現在の大会設定:\n\n") + info,
        )

    def _on_absences(self) -> None:
        if self._current_db_path is None:
            return
        dlg = AbsenceDialog(self._current_db_path, parent=self)
        dlg.exec()

    def _on_about(self):
        QMessageBox.about(
            self,
            self.tr("OpenARDF-calc について"),
            self.tr(
                "OpenARDF-calc\n\n"
                "ARDF競技集計ソフトウェア\n\n"
                "バージョン: 0.1.0\n"
                "ライセンス: MIT\n"
                "著作者: JF9SOM"
            ),
        )
