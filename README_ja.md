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

## ライセンス

MIT — Copyright (c) 2026 JF9SOM
