# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for OpenARDF-calc — Windows one-directory build.

プロジェクトルートから実行してください:
    pyinstaller OpenARDF-calc.spec

出力: dist\OpenARDF-calc\OpenARDF-calc.exe
"""
import glob
from pathlib import Path

# ── パス設定 ──────────────────────────────────────────────────
# このファイルは常にプロジェクトルートから実行する前提
SRC = Path('src')

# 翻訳ファイル (.qm)
# 事前に `python scripts/build_translations.py` でビルドしておくこと
_qm = glob.glob(str(SRC / 'translations' / '*.qm'))
_datas = [(qm, 'translations') for qm in _qm]

# ── Analysis ──────────────────────────────────────────────────
a = Analysis(
    [str(SRC / 'main.py')],
    # pathex に src を追加することで `import ui`, `import core` が解決される
    pathex=[str(SRC)],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # ── アプリケーション内パッケージ ──────────────────────
        'ui',
        'ui.main_window',
        'ui.competitors_window',
        'ui.results_window',
        'ui.dialogs',
        'ui.dialogs.absence_dialog',
        'ui.dialogs.competition_settings',
        'ui.dialogs.competitor_edit',
        'ui.dialogs.si_import_dialog',
        'core',
        'core.database',
        'core.competitor_dao',
        'core.ranking',
        'core.result_exporter',
        'core.si_result_dao',
        'core.si_reader',
        'core.si_reader.base',
        'core.si_reader.si_manager_csv',
        'models',
        # ── Qt モジュール（自動検出されない場合の補助） ─────────
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPrintSupport',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenARDF-calc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # GUI アプリ: コンソールウィンドウを表示しない
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # アイコンを設定する場合: icon='resources/icon.ico'
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OpenARDF-calc',
)
