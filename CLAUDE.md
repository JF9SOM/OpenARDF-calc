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

## 起動方法

```bash
cd /home/sadatoshi/OpenARDF-calc
source .venv/bin/activate
python src/main.py
```

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
│   │   └── dialogs/
│   │       ├── competition_settings.py  # 競技設定・新規大会ダイアログ
│   │       ├── si_import_dialog.py      # SIデータ読み込みダイアログ
│   │       ├── competitor_edit.py       # 参加者編集ダイアログ
│   │       ├── absence_dialog.py        # 欠席登録ダイアログ
│   │       └── manual_result_dialog.py  # 手動結果入力ダイアログ
│   ├── core/
│   │   ├── database.py          # SQLite 接続・マイグレーション
│   │   ├── competitor_dao.py    # 参加者CRUD + CSV import/export
│   │   ├── si_result_dao.py     # SI結果CRUD + 照合ロジック
│   │   ├── ranking.py           # 順位計算エンジン
│   │   ├── result_exporter.py   # CSV出力
│   │   └── si_reader/
│   │       ├── base.py                # 抽象基底クラス
│   │       ├── si_manager_csv.py      # SI Manager ヘッダ付きCSV読み込み
│   │       └── ardf_si_raw_csv.py     # ARDF SI ヘッダなしCSV読み込み
│   ├── models/
│   └── translations/
│       ├── en.ts             # 英語翻訳ソース
│       └── en.qm             # コンパイル済み
├── scripts/
│   └── build_translations.py
├── test-data/                # テスト用大会データ（.gitignore済み・個人情報含む）
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

### 翻訳ファイルのビルド

```bash
python scripts/build_translations.py
# または
pyside6-lrelease src/translations/en.ts -qm src/translations/en.qm
```

## SI データ読み込み設計

### フォーマット自動判別

`SIImportDialog` が2種類のリーダーをフォーマット自動判別で使い分ける。

| リーダークラス | ファイル | 対象フォーマット |
|---|---|---|
| `SIManagerCSVReader` | `si_manager_csv.py` | ヘッダ付きCSV（TX1/TX2…列あり） |
| `ARDFSIRawCSVReader` | `ardf_si_raw_csv.py` | ヘッダなしCSV（ARDF SI software出力） |

判別方法：先頭行が数字で始まる → ヘッダなし形式（`_is_raw_format()`）

### ヘッダなし形式（`ardf_si_raw_csv.py`）の列構造

| 列 | 内容 |
|----|------|
| 0 | SI カード番号（5桁） |
| 1 | SI カード番号（prefix付き） |
| 2 | 読み取り日時 |
| 3 | 絶対スタート時刻（空の場合あり） |
| 4 | SI基準時刻からのスタート経過 |
| 5 | 未使用 |
| 6 | SI基準時刻からのフィニッシュ経過（**公式タイム計算に使用**） |
| 7〜9 | 氏名フィールド（無視） |
| 10〜 | コントロール番号・通過時刻のペア繰り返し |

- フィニッシュコントロール（col6に最も近い時刻のパンチ）は `tx_punches` から除外
- 出力レコードに `"time_format": "si_relative"` フラグを付与

### フェーズ分割

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | SI Manager CSV 読み込み（2形式対応） | **実装済み** |
| Phase 2 | python-sportident で SIリーダーから直接読み込み | 将来実装 |

## 参加者 CSV インポート（`competitor_dao.py`）

- 文字コード自動検出（UTF-8-BOM / UTF-8 / CP932）
- ヘッダ列名は全角・半角カタカナ両対応（`_CSV_TO_DB` マッピング）
- ゼッケン番号をキーに upsert（重複時は上書き）
- ファイル選択ダイアログで `*.csv *.CSV` の両拡張子を表示

## 経過時間計算（`si_result_dao.py`）

**時差スタート対応の計算式：**

```
経過時間 = (SI基準時刻 + SIデータcol6) − 選手のグループスタート時刻
グループスタート時刻 = 1組スタート時刻 + (start_order − 1) × 組間隔
```

- `time_format == "si_relative"` のレコードにこの計算を適用
- ヘッダ付きCSV（`SIManagerCSVReader`）は従来の `finish - si_base_time` を使用
- 時超（overtime）は `elapsed > time_limit_min × 60` で自動判定

## 競技設定（`competition` テーブル）

| カラム | 型 | 内容 |
|---|---|---|
| `name` | TEXT | 大会名称 |
| `date` | TEXT | 開催年月日（yyyy-MM-dd） |
| `start_time_g1` | TEXT | 1組スタート時刻（HH:mm:ss） |
| `si_base_time` | TEXT | SI基準時刻（HH:mm:ss）★重要★ |
| `group_interval_min` | INTEGER | 組間隔（分、default 5） |
| `time_limit_min` | INTEGER | 制限時間（分、default 120） |
| `regional_prefectures` | TEXT | 地域結果対象県（カンマ区切り例: 石川県,富山県,福井県） |
| `all_tx_search` | INTEGER | 全TX探索フラグ |
| `w50_m60_optional` | INTEGER | W50・M60任意探索フラグ |
| `beacon_search` | INTEGER | ビーコン探索フラグ |
| `group_score_count` | INTEGER | グループ成績対象人数 |
| `winners_*` | INTEGER | 各クラス入賞者数 |

## 参加者テーブル（`competitor`）の主要カラム

| カラム | 内容 |
|---|---|
| `si_number` | SI No（参加者CSVの `SI No` 列、1〜46等の連番） |
| `start_order` | スタート組番号（経過時間計算に必須） |
| `address1` | 住所1（地域結果判定に使用） |

### SI番号の照合ルール

参加者CSV の `SI No`（例: `3`）= SIデータのカード番号下2桁（例: `38503` → `3`）

## 順位計算（`ranking.py`）

### ランキング規則

1. 発見TX数が多い選手が上位
2. 同TX数は経過時間が短い選手が上位
3. **時超（overtime）選手は非時超選手の後に配置（`**` 表示・順位番号なし）**
4. 欠席・失格選手は最後尾

### 地域結果

`RankingEngine.compute_regional(prefectures)` で `address1` の前方一致フィルタを適用し、地域内選手のみで再順位付けを行う。

## 結果ウィンドウ（`results_window.py`）

タブ構成：

| タブ | 内容 |
|---|---|
| 地域結果 | `regional_prefectures` の県に住所が一致する選手のみ。未設定時は「(未設定)」 |
| 総合結果 | 全選手 |
| クラス別 | クラス選択コンボボックスで切り替え |
| ラップタイム | 各TX通過時刻一覧 |

## DBマイグレーション（`database.py`）

既存の `.ardf` ファイルを開く都度 `_migrate()` を実行し、不足列を追加する。
新しい列を追加する場合は `_add_column()` を使用（列が既存でも例外を出さない）。

## メニュー構成

```
ファイル
  新規大会
  大会を開く
  参加者データ読み込み CSV
  SIデータ読み込み
    SI Manager CSV から読み込み    ← Phase1実装（2形式自動判別）
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
- DBスキーマ変更は `_create_tables`（新規）と `_migrate` / `_add_column`（既存）の両方に追加する
