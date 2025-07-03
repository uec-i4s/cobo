# 日本語ベクトル検索システム

sqlite-vecを使用した日本語ベクトル検索システムです。

## 特徴

- 高速検索: sqlite-vecによる最適化されたベクトル検索
- 日本語対応: pfnet/plamo-embedding-1bモデルを使用
- 軽量: SQLiteベースで依存関係が少ない
- MCP対応: Model Context Protocolツールサーバー
- パフォーマンス最適化: キャッシュ、接続プール、PRAGMA最適化

## プロジェクト構成

```
.
├── lib/                    # コアライブラリ
│   ├── vector_utils.py     # ベクトル検索ユーティリティ
│   └── data_processing.py  # データ処理・DB構築
├── test_search.py          # シンプルな検索テスト
├── benchmark.py            # パフォーマンス測定
├── build_db.py             # データベース構築スクリプト
├── server.py               # MCPサーバー
├── srv.sh                  # サーバー起動スクリプト
└── README.md
```

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. データベース構築

```bash
uv run build_db.py
```

### 3. 動作確認

```bash
uv run test_search.py info
```

## 使用方法

### 基本的な検索テスト

```bash
# データベース情報表示
uv run test_search.py info

# 単発検索
uv run test_search.py "大学"

# インタラクティブモード
uv run test_search.py
```

### パフォーマンス測定

```bash
# 基本ベンチマーク
uv run benchmark.py

# 詳細分析
uv run benchmark.py --detailed

# カスタムクエリ
uv run benchmark.py --queries "大学" "授業" "履修"
```

### MCPサーバー

```bash
# サーバー起動
./srv.sh start

# サーバー状態確認
./srv.sh status

# サーバー停止
./srv.sh stop
```

## パフォーマンス最適化

### 実装済み最適化

- 埋め込みキャッシュ: 同一クエリの高速化
- 接続プール: データベース接続の再利用
- PRAGMA最適化: SQLite設定の最適化
  - WALモード
  - 大容量キャッシュ (20,000ページ)
  - メモリ一時ストレージ
  - 4KBページサイズ
  - 256MB mmap

### パフォーマンス結果

- 初回検索: ~0.1秒
- キャッシュヒット: ~0.05秒
- DB検索: ~0.007秒

## 設定

### データソース設定

`.env`ファイルで設定可能：

```bash
# FTPソース使用
USE_FTP_SOURCE=true
FTP_HOST=192.168.7.48
FTP_USER=anonymous
FTP_PASS=
FTP_DATA_DIR=/data

# ローカルソース使用
USE_FTP_SOURCE=false
LOCAL_DIR=./data
```

### サーバー設定

`.server_config`ファイルで設定可能：

```bash
TRANSPORT=streamable-http
PORT=8080
HOST=0.0.0.0
STATELESS=false
```

## システム要件

- Python 3.12以上
- 2GB以上のRAM（モデル読み込み用）
- Apple Silicon推奨（MPS対応）

## 技術詳細

### 使用技術

- ベクトルDB: sqlite-vec v0.1.6
- 埋め込みモデル: pfnet/plamo-embedding-1b (2048次元)
- MCPフレームワーク: FastMCP
- 言語: Python 3.12

### アーキテクチャ

1. データ処理: Markdownファイルの解析・チャンク化
2. ベクトル化: 日本語テキストの埋め込み生成
3. インデックス: sqlite-vecによる高速検索インデックス
4. 検索: KNN検索による類似文書取得

## トラブルシューティング

### よくある問題

1. モデル読み込みエラー
   ```bash
   # キャッシュクリア
   rm -rf ~/.cache/huggingface/
   ```

2. データベースエラー
   ```bash
   # DB再構築
   rm search.db*
   uv run python build_db.py
   ```

3. パフォーマンス問題
   ```bash
   # 詳細分析実行
   uv run benchmark.py --detailed
   ```

## ライセンス

MIT License