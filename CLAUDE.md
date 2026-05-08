# OpenARDF-calc — CLAUDE.md

## プロジェクト概要

ARDF（アマチュア無線方向探知競技）の競技成績集計ソフトウェア。
Python + PySide6 で実装し、SQLite をデータストアとして使用する。

## リポジトリ

https://github.com/JF9SOM/OpenARDF-calc.git

## 仕様参考資料

- **旧ソフト「ARDF SI」マニュアル（PDF）**:
  https://fdt.rdf.jp/si_system/doc/ardf_si_090801.pdf
  - 機能仕様の参考資料として使用する（このソフトの直接移植ではない）

## 技術スタック

| 項目 | 選択 |
|------|------|
| 言語 | Python 3.10+ |
| UI フレームワーク | PySide6 (Qt 6) |
| データ保存 | SQLite (`sqlite3` 標準ライブラリ) |
| インポート/エクスポート | CSV |
| 多言語対応 | Qt QTranslator (.ts / .qm 形式) |
| パッケージ管理 | requirements.txt |

## ディレクトリ構成

```
OpenARDF-calc/
├── src/
│   ├── main.py               # エントリーポイント
│   ├── ui/
│   │   ├── main_window.py    # メインウィンドウ
│   │   └── dialogs/          # 各種ダイアログ（将来追加）
│   ├── core/
│   │   ├── database.py       # SQLite 操作
│   │   └── si_reader/
│   │       ├── base.py       # 抽象基底クラス（差し替え可能な設計）
│   │       └── si_manager_csv.py  # SI Manager CSV 読み込み（Phase1）
│   ├── models/               # データモデル（将来追加）
│   └── translations/
│       ├── en.ts             # 英語翻訳ソース
│       └── en.qm             # コンパイル済み（.gitignore 対象外）
├── scripts/
│   └── build_translations.py # .ts → .qm ビルドスクリプト
├── resources/                # アイコン等（将来追加）
├── CLAUDE.md
├── LICENSE
├── README.md
├── README_ja.md
└── requirements.txt
```

## 多言語対応

- **デフォルト言語**: 日本語（ソースコード内の `tr()` 文字列が日本語）
- **英語**: `src/translations/en.ts` → `pyside6-lrelease` でコンパイル → `en.qm`
- UIの言語切り替えボタン（日本語 / English）でランタイム切り替え
- 将来言語追加は `src/translations/XX.ts` を追加し `build_translations.py` を実行

### 翻訳ファイルのビルド

```bash
python scripts/build_translations.py
# または
pyside6-lrelease src/translations/en.ts -qm src/translations/en.qm
```

## SI データ読み込み設計（フェーズ分割）

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | SI Manager CSV 読み込み | 実装対象 |
| Phase 2 | python-sportident で SIリーダーから直接読み込み | 将来実装 |

`SIReaderBase` 抽象クラスで読み込み層を分離し、Phase2 への差し替えを容易にする。

## メニュー構成

```
ファイル
  新規大会
  大会を開く
  参加者データ読み込み CSV
  SIデータ読み込み
    SI Manager CSV から読み込み    ← Phase1実装
    SIリーダーから直接読み込み    ← グレーアウト（Phase2）
  結果を出力
  終了

競技
  競技設定
  参加者管理
  欠席登録

結果
  順位集計
  結果表示
  結果印刷

ヘルプ
  このソフトについて
  マニュアル
```

## コーディング規約

- Python 3.10+ の型ヒントを使用
- PySide6 の命名規則に準拠（キャメルケース → Pythonスネークケースでラップ）
- UI の再翻訳は `changeEvent(QEvent.Type.LanguageChange)` で処理
- 新しいウィンドウ・ダイアログは `_retranslate_ui()` メソッドを持つ
