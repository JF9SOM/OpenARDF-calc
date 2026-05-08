# OpenARDF-calc

ARDF（アマチュア無線方向探知競技）の競技成績集計ソフトウェアです。

[English README](README.md)

## 機能

- ARDF大会の競技管理
- 参加者データのCSVインポート
- SI Manager CSVからSIパンチデータを読み込み
- 順位集計と結果出力
- 日本語 / 英語 UI切り替え

## 動作要件

- Python 3.10以上
- PySide6 6.6以上

## インストール

```bash
git clone https://github.com/JF9SOM/OpenARDF-calc.git
cd OpenARDF-calc
pip install -r requirements.txt
```

## 翻訳ファイルのビルド

英語UIを使用する場合は事前に実行してください：

```bash
python scripts/build_translations.py
```

## 起動方法

```bash
python src/main.py
```

## プロジェクト構成

```
src/
  main.py               エントリーポイント
  ui/
    main_window.py      メインウィンドウ
  core/
    database.py         SQLiteデータベース層
    si_reader/          SIデータ読み込み（差し替え可能な設計）
      base.py           抽象基底クラス
      si_manager_csv.py SI Manager CSV読み込み（Phase 1）
  translations/
    en.ts               英語翻訳ソースファイル
```

## SIデータ読み込みについて

**Phase 1（実装済み）：** SI ManagerがエクスポートしたCSVファイルから読み込みます。  
**Phase 2（将来実装）：** `python-sportident` を使用してSIリーダーから直接読み込みます。

---

## Windows 実行ファイルのビルド（PyInstaller）

### 前提条件

- Python 3.10 以上（[python.org](https://www.python.org/) からインストール）
- PowerShell（Windows に標準搭載）

### 手順

**1. 依存パッケージのインストール**

```powershell
cd OpenARDF-calc
pip install -r requirements.txt
pip install pyinstaller
```

**2. 翻訳ファイルのビルド**（英語 UI を使用する場合）

```powershell
python scripts/build_translations.py
```

**3. PyInstaller でビルド**

プロジェクトルート（`OpenARDF-calc.spec` があるフォルダ）で実行します：

```powershell
pyinstaller OpenARDF-calc.spec
```

**4. 実行ファイルの場所**

```
dist\
  OpenARDF-calc\
    OpenARDF-calc.exe   ← 起動ファイル
    _internal\          ← Qt DLL・翻訳ファイル等（削除不可）
```

`dist\OpenARDF-calc` フォルダごと配布してください。

### トラブルシューティング

| 症状 | 対処 |
|------|------|
| `ModuleNotFoundError: No module named 'ui'` | `pyinstaller OpenARDF-calc.spec` をプロジェクトルートから実行しているか確認 |
| 英語 UI が表示されない | ビルド前に `python scripts/build_translations.py` を実行して `en.qm` を生成する |
| `upx` 関連の警告 | [UPX](https://upx.github.io/) 未インストールの場合は無視して問題なし（圧縮が省略されるだけ） |
| Windows Defender の警告 | PyInstaller 製の exe は誤検知されることがある。ウイルス対策ソフトの除外設定を行うか、ソースから直接実行する |

### 仮想環境を使う場合（推奨）

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
python scripts/build_translations.py
pyinstaller OpenARDF-calc.spec
```

---

## ライセンス

MIT — Copyright (c) 2026 JF9SOM
