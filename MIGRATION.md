# Python 2からPython 3への移行ガイド

## 概要
このドキュメントでは、Python 2版からPython 3版への移行に関する重要な変更点を説明します。

## 主な変更点

### 1. Python バージョン
- **必須**: Python 3.7以上
- Python 2はサポートされていません

### 2. 依存ライブラリの変更

#### 削除されたライブラリ
- `urllib2` → `requests`に置き換え
- `StringIO` → `io.StringIO`に置き換え

#### 新しい依存ライブラリ
```bash
pip install -r requirements.txt
```

### 3. コードの変更点

#### print文からprint関数へ
```python
# Python 2
print "Hello"
print eStatAPI.load_all_ids()

# Python 3
print("Hello")
print(eStatAPI.load_all_ids())
```

#### 文字列とエンコーディング
- Python 3ではすべての文字列がUnicodeです
- ファイル操作時に`encoding='utf-8'`を明示的に指定

#### 辞書のメソッド
```python
# Python 2
hash.values()[0]

# Python 3
list(hash.values())[0]
```

### 4. セキュリティの改善

#### コマンド実行の安全性
Python 2版では`shell=True`を使用していましたが、これはコマンドインジェクションの脆弱性があります。
Python 3版では以下のように改善されています:

```python
# Python 2版 (脆弱)
subprocess.check_output(cmd, shell=True)

# Python 3版 (安全)
# 外部コマンド呼び出しを極力削減し、Pythonネイティブな方法を使用
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
```

#### 入力検証
統計IDとクエリに対する検証が追加されました:

```python
# 統計IDは数字のみ
def _validate_stats_id(self, stats_id):
    if not re.match(r'^\d+$', stats_id):
        raise ValueError('Invalid statistics data ID')

# クエリの危険な文字をチェック
def _validate_query(self, query):
    if re.search(r'[;&|`$\n\r]', query):
        raise ValueError('Invalid query string')
```

### 5. エラーハンドリング

Python 3版では、より詳細なエラーメッセージとログ出力が提供されます:

```python
import logging
logger = logging.getLogger(__name__)

try:
    # 処理
except requests.RequestException as e:
    logger.error(f"API request failed: {e}")
    raise
```

### 6. 一時ファイルの管理

Python 3版では`tempfile`モジュールを使用して安全に一時ファイルを管理します:

```python
import tempfile

with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
    tmp_path = tmp_file.name
    data.to_csv(tmp_file)
```

### 7. 自動ディレクトリ作成

Python 3版では必要なディレクトリが自動的に作成されます:

```python
from pathlib import Path

def _ensure_directories(self):
    directories = [self.path['tmp'], self.path['csv'], ...]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
```

## 移行手順

### ステップ 1: Python 3のインストール
```bash
# システムにPython 3.7以上がインストールされているか確認
python3 --version
```

### ステップ 2: 依存ライブラリのインストール
```bash
pip3 install -r requirements.txt
```

### ステップ 3: 既存のコードの更新
- すべての`print`文を`print()`関数に変更
- インポート文を確認(特に`urllib2`を使っている場合)

### ステップ 4: テスト
```python
# 基本的な動作確認
import sys
sys.path.append('./python')
import e_Stat_API_Adaptor

eStatAPI = e_Stat_API_Adaptor.e_Stat_API_Adaptor({
    'appId': 'your_app_id',
    'limit': '10000',
    'next_key': True,
    'directory': './',
    'ver': '2.0'
})

# インデックスの作成テスト
eStatAPI.load_all_ids()
eStatAPI.build_statid_index()
```

## トラブルシューティング

### よくある問題

#### 1. `ModuleNotFoundError: No module named 'urllib2'`
**解決策**: Python 3版を使用していることを確認してください。urllib2は使用されていません。

#### 2. `SyntaxError: invalid syntax` (print文)
**解決策**: すべての`print`文を`print()`関数に変更してください。

#### 3. `UnicodeDecodeError`
**解決策**: ファイルを開く際に`encoding='utf-8'`を指定してください。

#### 4. パーミッションエラー
**解決策**: ディレクトリの書き込み権限を確認してください。

## 互換性のない変更

以下の内部メソッドは削除または変更されています:

- `cmd_line()` - 一部の機能でPythonネイティブな方法に置き換え
- `build_cmd()` - 使用を最小限に抑制

これらのメソッドに直接依存している場合は、コードの修正が必要です。

## サポート

問題が発生した場合は、GitHubのIssuesセクションで報告してください。

## バックアップ

移行前に、元のPython 2版のコードをバックアップすることを強く推奨します:

```bash
# バックアップファイルが自動作成されています
ls -la python/*.bak
ls -la www/*.bak
```
