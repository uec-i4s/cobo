"""
ベクトル検索システムの共通ユーティリティモジュール

このモジュールは以下の機能を提供します:
- 埋め込みモデルの管理
- sqlite-vecデータベースの接続管理
- ベクトル検索の実行
- 設定管理
"""

import os
import sqlite3
import sqlite_vec
from typing import List, Dict, Any, Optional, Tuple
from transformers import AutoTokenizer, AutoModel
import torch
from dotenv import load_dotenv

# 設定の読み込み
load_dotenv()

# 定数定義
EMBEDDING_MODEL = "pfnet/plamo-embedding-1b"
SQLITE_DB_PATH = "search.db"
EMBEDDING_DIMENSION = 2048


class EmbeddingModelManager:
    """埋め込みモデルの管理クラス"""
    
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.device = None
        self._is_loaded = False
        self._embedding_cache = {}  # 埋め込みキャッシュ
    
    def load_model(self) -> Tuple[AutoTokenizer, AutoModel, str]:
        """埋め込みモデルをロードする"""
        if self._is_loaded:
            return self.tokenizer, self.model, self.device
        
        print(f"📦 モデルロード中: {EMBEDDING_MODEL}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            EMBEDDING_MODEL,
            trust_remote_code=True,
            revision="main"
        )
        self.model = AutoModel.from_pretrained(
            EMBEDDING_MODEL,
            trust_remote_code=True,
            revision="main"
        )
        
        # デバイス自動判定
        self.device = self._detect_device()
        self.model = self.model.to(self.device)
        
        # モデルを評価モードに設定（推論最適化）
        self.model.eval()
        
        print(f"✅ モデルロード完了: {self.device}")
        self._is_loaded = True
        
        return self.tokenizer, self.model, self.device
    
    def _detect_device(self) -> str:
        """最適なデバイスを自動判定する"""
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"🚀 GPU使用: {gpu_name} (CUDA {torch.version.cuda})")
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("🚀 GPU使用: Apple Metal Performance Shaders (MPS)")
            return "mps"
        else:
            print("⚠️  CPU使用: GPUが利用できません")
            return "cpu"
    
    def get_embedding(self, text: str) -> List[float]:
        """テキストの埋め込みベクトルを取得する（キャッシュ付き）"""
        # キャッシュチェック
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        if not self._is_loaded:
            self.load_model()
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True  # バッチ処理の最適化
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            # 推論最適化のためのコンテキスト
            if self.device == "cuda":
                with torch.cuda.amp.autocast():
                    outputs = self.model(**inputs)
            else:
                outputs = self.model(**inputs)
            
            embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().tolist()
        
        # キャッシュに保存（メモリ制限のため最大100件）
        if len(self._embedding_cache) < 100:
            self._embedding_cache[text] = embeddings
        
        return embeddings


class SqliteVecDatabase:
    """sqlite-vecデータベースの管理クラス"""
    
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        self.db_path = db_path
        self._connection = None
        self._connection_initialized = False
    
    def get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得する（接続プール付き）"""
        if not os.path.exists(self.db_path):
            raise RuntimeError(
                f"sqlite-vecデータベースが存在しません: {self.db_path}\n"
                "build_db.pyを実行してDBを構築してください。"
            )
        
        if not self._connection_initialized:
            self._connection = sqlite3.Connection(self.db_path)
            self._connection.enable_load_extension(True)
            sqlite_vec.load(self._connection)
            self._connection.enable_load_extension(False)
            
            # パフォーマンス最適化設定（sqlite-vecベンチマークに基づく）
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute("PRAGMA cache_size=20000")  # より大きなキャッシュ
            self._connection.execute("PRAGMA temp_store=MEMORY")
            self._connection.execute("PRAGMA page_size=4096")    # sqlite-vecベンチマークで使用
            self._connection.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
            self._connection.execute("PRAGMA optimize")  # クエリプランナー最適化
            
            self._connection_initialized = True
        
        return self._connection
    
    def get_database_info(self) -> Dict[str, Any]:
        """データベースの情報を取得する"""
        with self.get_connection() as conn:
            # sqlite-vecバージョン
            version = conn.execute("SELECT vec_version()").fetchone()[0]
            
            # テーブル一覧
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            # ドキュメント数
            doc_count = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            
            # メタデータ数
            meta_count = conn.execute("SELECT COUNT(*) FROM doc_metadata").fetchone()[0]
            
            # サンプルデータ
            sample = conn.execute(
                "SELECT file_name, source FROM doc_metadata LIMIT 3"
            ).fetchall()
            
            return {
                "version": version,
                "table_count": len(tables),
                "doc_count": doc_count,
                "meta_count": meta_count,
                "sample_files": sample
            }
    
    def search_vectors(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Tuple[str, str, str, str, float]]:
        """ベクトル検索を実行する（最適化版）"""
        query_blob = sqlite_vec.serialize_float32(query_embedding)
        
        conn = self.get_connection()
        cursor = conn.execute("""
            SELECT
                chunk_text,
                url,
                file_name,
                source,
                distance
            FROM docs
            WHERE embedding MATCH ?
              AND k = ?
            ORDER BY distance
        """, (query_blob, top_k))
        
        return cursor.fetchall()
    
    def close(self):
        """データベース接続を閉じる"""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._connection_initialized = False


class VectorSearchService:
    """ベクトル検索サービスクラス"""
    
    def __init__(self):
        self.model_manager = EmbeddingModelManager()
        self.database = SqliteVecDatabase()
        self._warmup_completed = False
    
    def _warmup(self):
        """初回検索の高速化のためのウォームアップ"""
        if not self._warmup_completed:
            print("🔥 検索エンジンウォームアップ中...")
            # モデルを事前ロード
            self.model_manager.load_model()
            # ダミー検索でキャッシュを準備
            dummy_embedding = self.model_manager.get_embedding("test")
            self.database.search_vectors(dummy_embedding, 1)
            self._warmup_completed = True
            print("✅ ウォームアップ完了")
    
    def search(self, query: str, top_k: int = 5, show_timing: bool = False) -> List[Dict[str, Any]]:
        """クエリに対してベクトル検索を実行する"""
        import time
        
        if not self._warmup_completed:
            self._warmup()
        
        start_time = time.time()
        
        # 埋め込みベクトルを生成
        embedding_start = time.time()
        query_embedding = self.model_manager.get_embedding(query)
        embedding_time = time.time() - embedding_start
        
        # ベクトル検索を実行
        search_start = time.time()
        results = self.database.search_vectors(query_embedding, top_k)
        search_time = time.time() - search_start
        
        total_time = time.time() - start_time
        
        if show_timing:
            cache_status = "HIT" if query in self.model_manager._embedding_cache else "MISS"
            print(f"⏱️  検索時間詳細:")
            print(f"   📦 埋め込み生成: {embedding_time:.3f}s (キャッシュ: {cache_status})")
            print(f"   🔍 DB検索: {search_time:.3f}s")
            print(f"   📊 合計: {total_time:.3f}s")
            print(f"   🎯 結果数: {len(results)}件")
            
            # パフォーマンス分析
            if embedding_time > 0.1:
                print(f"   ⚠️  埋め込み生成が遅い可能性があります ({embedding_time:.3f}s)")
            if search_time > 0.05:
                print(f"   ⚠️  DB検索が遅い可能性があります ({search_time:.3f}s)")
        
        # 結果を辞書形式に変換
        formatted_results = []
        for text, url, file_name, source, distance in results:
            formatted_results.append({
                "text": text,
                "url": url,
                "file": file_name,
                "source": source,
                "distance": distance
            })
        
        return formatted_results
    
    def get_database_info(self) -> Dict[str, Any]:
        """データベース情報を取得する"""
        return self.database.get_database_info()
    
    def analyze_performance(self) -> Dict[str, Any]:
        """パフォーマンス分析情報を取得する"""
        conn = self.database.get_connection()
        
        # SQLite統計情報を取得
        stats = {}
        
        # データベースサイズ
        stats['db_size_mb'] = os.path.getsize(self.database.db_path) / (1024 * 1024)
        
        # PRAGMA情報
        pragma_info = {}
        pragmas = [
            'journal_mode', 'synchronous', 'cache_size',
            'temp_store', 'page_size', 'mmap_size'
        ]
        
        for pragma in pragmas:
            result = conn.execute(f"PRAGMA {pragma}").fetchone()
            pragma_info[pragma] = result[0] if result else None
        
        stats['pragma_settings'] = pragma_info
        
        # キャッシュ統計
        stats['embedding_cache_size'] = len(self.model_manager._embedding_cache)
        stats['embedding_cache_limit'] = 100
        
        # モデル情報
        stats['model_loaded'] = self.model_manager._is_loaded
        stats['device'] = self.model_manager.device if self.model_manager._is_loaded else None
        
        return stats


class ConfigManager:
    """設定管理クラス"""
    
    @staticmethod
    def get_data_source_config() -> Dict[str, Any]:
        """データソース設定を取得する"""
        return {
            "use_ftp_source": os.getenv("USE_FTP_SOURCE", "true").lower() == "true",
            "ftp_host": os.getenv("FTP_HOST", "192.168.7.48"),
            "ftp_user": os.getenv("FTP_USER", "anonymous"),
            "ftp_pass": os.getenv("FTP_PASS", ""),
            "ftp_data_dir": os.getenv("FTP_DATA_DIR", "/data"),
            "local_dir": os.getenv("LOCAL_DIR", "./data")
        }


# グローバルインスタンス（シングルトンパターン）
_vector_search_service = None

def get_vector_search_service() -> VectorSearchService:
    """ベクトル検索サービスのシングルトンインスタンスを取得する"""
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service