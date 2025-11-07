# e-Stat API Adaptor

## 概要
e-Stat API Adaptorは、日本の政府統計ポータル「e-Stat」のAPIを使いやすくするためのPythonライブラリです。

## License
* MIT
    * see License.txt

## 重要な変更点 (Python 3対応版)

このバージョンでは以下の大きな変更が行われています:

### セキュリティとモダナイゼーション
- **Python 3.7以上に対応** (Python 2はサポート終了)
- **urllib2からrequestsライブラリへ移行** - より安全で使いやすいHTTP通信
- **コマンドインジェクション脆弱性を修正** - `shell=True`を削除し、安全なファイル操作へ移行
- **入力検証の強化** - 統計IDとクエリのバリデーション機能を追加
- **エラーハンドリングの改善** - 詳細なログ出力と適切な例外処理
- **自動ディレクトリ作成** - 必要なディレクトリを自動的に作成

## 必要な環境

### Python バージョン
- **Python 3.7以上** (Python 2はサポートされていません)

## インストール

### 1. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
```

### 必要なライブラリ
- requests >= 2.31.0 (HTTP通信用)
- pandas >= 1.3.0 (データ処理用)
- numpy >= 1.21.0 (数値計算用)
- Flask >= 2.0.0 (Webサーバー用)


## ディレクトリ及びファイル構成

```
.
├── data-cache/          # キャッシュ用ディレクトリ(CSV形式でデータを保存)
├── dictionary/          # 辞書用ディレクトリ(検索用のインデックスファイル)
│   └── detail/         # 詳細検索用インデックス(N-gram)
├── tmp/                # 一時ダウンロード用ディレクトリ(JSON形式)
├── python/             # Pythonライブラリ用ディレクトリ
│   ├── e_Stat_API_Adaptor.py  # メインライブラリ
│   └── examples.py     # 使用例
├── www/                # Web公開用ディレクトリ
│   └── run.py          # Flask Webサーバー
├── requirements.txt    # 依存ライブラリリスト
└── README.md           # このファイル
```

**注意**: 必要なディレクトリは初回実行時に自動的に作成されます。

## クイックスタート

### 1. e-Stat APIキーの取得
[e-Stat API](https://www.e-stat.go.jp/)のサイトでアカウントを作成し、appIDを取得してください。

### 2. インスタンスの生成例

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('./python')
import e_Stat_API_Adaptor

eStatAPI = e_Stat_API_Adaptor.e_Stat_API_Adaptor({
    # 取得したappId
    'appId': 'your_app_id_here',
    # データをダウンロード時に一度に取得するデータ件数
    'limit': '10000',
    # next_keyに対応するか否か
    # True: 全データをダウンロード、False: limit件数のみ
    'next_key': True,
    # ライブラリの設置ディレクトリ(絶対パス推奨)
    'directory': './',
    # e-Stat APIのバージョン
    'ver': '2.0'
})
```

### 3. 初回セットアップ

統計IDを検索するために必要なインデックスを生成します。

```python
# 全ての統計表IDをローカルにダウンロード
eStatAPI.load_all_ids()

# ダウンロードした統計表IDからインデックスを作成
eStatAPI.build_statid_index()

# (オプション) STATISTICS_NAMEとTITLEから詳細検索用インデックスを作成(N-gram形式)
eStatAPI.build_detailed_index()
```

## 主な機能

### 1. 統計IDの検索

#### 基本検索
```python
# インデックスリストを検索
result = eStatAPI.search_id('法人', eStatAPI.path['dictionary-index'])
print(result)

# 全件表示
all_data = eStatAPI.search_id('index', eStatAPI.path['dictionary-index'])
```

#### ユーザーカスタムインデックス
```python
# ユーザー作成型インデックスを検索
user_result = eStatAPI.search_id('法人', eStatAPI.path['dictionary-user'], 'user')

# 詳細検索からユーザーインデックスを作成
eStatAPI.create_user_index_from_detailed_index('法人')
```

#### N-gram検索（詳細検索）
```python
# 部分一致での検索
results = eStatAPI.search_detailed_index('家計')
print(results)
```

### 2. データのダウンロードと表示

#### データのダウンロード
```python
# 統計データをダウンロード（自動的にdata-cache/にCSV保存）
csv_data = eStatAPI.get_csv('get', '0000030002')
print(csv_data)
```

**CSVフォーマット:**
```csv
"$","全国都道府県030001","男女Ａ030001","年齢各歳階級Ｂ030003","全域・集中の別030002","時間軸(年次)","unit"
"$","area","cat02","cat03","cat01","time","unit"
"117060396","全国","男女総数","総数","全域","1980年","人"
```
- **1行目**: 人間が読める列名
- **2行目**: APIキー（内部処理用、出力時は除外）
- **3行目以降**: データ本体

#### データの一部表示
```python
# 最初の5行を表示
head_data = eStatAPI.get_csv('head', '0000030001')
print(head_data)

# 最後の5行を表示
tail_data = eStatAPI.get_csv('tail', '0000030001')
print(tail_data)
```

### 3. データ形式の変換

#### CSV → JSON変換
```python
# 行指向JSON (rjson)
row_json = eStatAPI.get_output(
    eStatAPI.get_csv('get', '0000030001'),
    'rjson'
)
# 出力例: [{"全域・集中の別030002": "全域", "全国都道府県030001": "全国", ...}, ...]

# 列指向JSON (cjson)
col_json = eStatAPI.get_output(
    eStatAPI.get_csv('get', '0000030001'),
    'cjson'
)
# 出力例: {"$": [117060396, 89187409, ...], "unit": ["人", "人", ...], ...}

# CSV形式のまま
csv_output = eStatAPI.get_output(
    eStatAPI.get_csv('get', '0000030001'),
    'csv'
)
```

### 4. データの集約とマージ

複数の統計表を結合して、pandasの集約関数で分析できます。

```python
# 2つの統計表をマージ
merged_data = eStatAPI.merge_data(
    '0000030001,0000030002',  # カンマ区切りで統計ID指定
    'area',                    # グループ化するカラム（area, time, cat01, cat02等）
    'mean'                     # 集約方法
)
print(merged_data)
```

#### 利用可能な集約方法

| 関数 | 説明 | パラメータ |
|------|------|-----------|
| `sum` | 合計値 | `'sum'` |
| `mean` | 平均値 | `'mean'` |
| `min` | 最小値 | `'min'` |
| `max` | 最大値 | `'max'` |
| `median` | 中央値 | `'median'` |
| `count` | 件数 | `'count'` |
| `var` | 分散 | `'var'` |
| `std` | 標準偏差 | `'std'` |

**例:**
```python
# 都道府県別の平均値を計算
avg_by_area = eStatAPI.merge_data('0000030001,0000030002', 'area', 'mean')

# 全データをマージ（集約なし）
all_merged = eStatAPI.merge_data('0000030001,0000030002', 'all', '')
```



### 5. Web API（Flask REST API）

FlaskサーバーでHTTP経由でデータにアクセスできます。

#### サーバーの起動
```bash
# www/run.pyでappIdとdirectoryを設定してから実行
python www/run.py
```

サーバーは `http://localhost:5000` で起動します。

#### エンドポイント

##### データ取得
```
GET /<appId>/<cmd>/<id>.<ext>
```

**パラメータ:**
- `<appId>`: e-Stat APIのアプリケーションID
- `<cmd>`: `get`（全体）, `head`（先頭5行）, `tail`（末尾5行）
- `<id>`: 統計表ID（例: `0000030001`）
- `<ext>`: 出力形式（`csv`, `rjson`, `cjson`）
- クエリ: `?dl=true` でダウンロード

**例:**
```bash
# CSV形式で表示
curl http://localhost:5000/your_app_id/get/0000030001.csv

# JSON形式でダウンロード
curl "http://localhost:5000/your_app_id/get/0000030001.rjson?dl=true" -O
```

##### データのマージと集約
```
GET /<appId>/merge/<ids>/<group_by>.<ext>
```

**パラメータ:**
- `<appId>`: e-Stat APIのアプリケーションID
- `<ids>`: カンマ区切りの統計表ID（例: `0000030001,0000030002`）
- `<group_by>`: グループ化するカラム（`area`, `time`, `cat01`, `all`等）
- `<ext>`: 出力形式（`csv`, `rjson`, `cjson`）
- クエリ:
  - `?aggregate=<method>` - 集約方法（`sum`, `mean`, `min`, `max`, `median`, `count`, `var`, `std`）
  - `?dl=true` - ダウンロード

**例:**
```bash
# 2つの統計表をマージ
curl http://localhost:5000/your_app_id/merge/0000030001,0000030002/all.csv

# areaでグループ化してマージ
curl http://localhost:5000/your_app_id/merge/0000030001,0000030002/area.csv

# areaの平均値を計算
curl "http://localhost:5000/your_app_id/merge/0000030001,0000030002/area.csv?aggregate=mean"
```

##### 統計表の検索
```
GET /<appId>/search/<q>.<ext>
```

**パラメータ:**
- `<appId>`: e-Stat APIのアプリケーションID
- `<q>`: 検索キーワード（`index`で全件表示）
- `<ext>`: 出力形式（`csv`, `rjson`, `cjson`）
- クエリ: `?dl=true` でダウンロード

**例:**
```bash
# 「法人」を含む統計表を検索
curl http://localhost:5000/your_app_id/search/法人.csv

# JSON形式で検索結果をダウンロード
curl "http://localhost:5000/your_app_id/search/法人.rjson?dl=true" -O

# 全統計表リストを取得
curl http://localhost:5000/your_app_id/search/index.csv
```

## 出力形式

すべての出力はUTF-8エンコーディングです。

| 形式 | 拡張子 | 説明 | 用途 |
|------|--------|------|------|
| **CSV** | `.csv` | カンマ区切り形式 | Excel、スプレッドシート |
| **行指向JSON** | `.rjson` | `[{col1: val1, col2: val2}, ...]` | 一般的なJSON処理 |
| **列指向JSON** | `.cjson` | `{col1: [val1, val2], col2: [...]}` | データ分析、可視化 |

**CSV例:**
```csv
"全域・集中の別030002","男女Ａ030001","年齢５歳階級Ａ030002","全国都道府県030001","時間軸(年次)","unit","$"
"全域","男女総数","総数","全国","1980年","人","117060396"
"全域","男女総数","総数","全国市部","1980年","人","89187409"
```

**行指向JSON (rjson):**
```json
[
  {"全域・集中の別030002": "全域", "全国都道府県030001": "全国", "男女Ａ030001": "男女総数", ...},
  {"全域・集中の別030002": "全域", "全国都道府県030001": "全国市部", "男女Ａ030001": "男女総数", ...}
]
```

**列指向JSON (cjson):**
```json
{
  "$": [117060396, 89187409, ...],
  "unit": ["人", "人", ...],
  "全国都道府県030001": ["全国", "全国市部", ...]
}
```

## 注意事項

### キャッシュ管理
- データは `data-cache/` ディレクトリにCSVでキャッシュされます
- e-Stat側でデータが更新された場合、該当CSVファイルを手動削除してください
- キャッシュクリア: `rm data-cache/*.csv`

### セキュリティ
- **本番環境ではFlaskのデバッグモードを無効化してください**
- Web公開時はuWSGIやGunicornなどのプロダクション用WSGIサーバーを使用
- appIdは環境変数で管理することを推奨

### パフォーマンス
- 大規模データセット（100万行以上）はメモリ消費に注意
- `next_key=True`で全データダウンロード、`False`で制限

## トラブルシューティング

### よくある問題

**Q: `ModuleNotFoundError: No module named 'requests'`**
A: `pip install -r requirements.txt` を実行してください

**Q: データがダウンロードできない**
A: e-Stat APIキー（appId）が正しいか確認してください

**Q: メモリエラーが発生する**
A: `limit`を小さくするか、`next_key=False`に設定してください

## ライセンス

MIT License - 詳細は [License.txt](License.txt) を参照

## 関連ドキュメント

- [MIGRATION.md](MIGRATION.md) - Python 2から3への移行ガイド
- [CLAUDE.md](CLAUDE.md) - 開発者向けガイド
- [e-Stat API公式ドキュメント](https://www.e-stat.go.jp/api/)

## コントリビューション

バグ報告や機能リクエストは、GitHubのIssuesでお願いします。
