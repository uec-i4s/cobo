"""
データ処理とデータベース構築のためのモジュール

このモジュールは以下の機能を提供します:
- Markdownファイルの解析
- テキストのチャンク化
- FTPとローカルファイルシステムからのデータ取得
- sqlite-vecデータベースの初期化と構築
"""

import os
import glob
import yaml
import sqlite3
import sqlite_vec
import tempfile
from typing import List, Dict, Tuple, Iterator
from ftplib import FTP, error_perm
from tqdm import tqdm

from .vector_utils import (
    EmbeddingModelManager, 
    SqliteVecDatabase, 
    ConfigManager,
    SQLITE_DB_PATH,
    EMBEDDING_DIMENSION
)


class MarkdownParser:
    """Markdownファイルの解析クラス"""
    
    @staticmethod
    def parse_markdown_with_url(filepath: str) -> Tuple[str, str]:
        """
        Markdownファイルを解析してURLと本文を取得する
        
        Args:
            filepath: Markdownファイルのパス
            
        Returns:
            (url, body): URLと本文のタプル
        """
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                header = content[3:end]
                body = content[end+3:].strip()
                try:
                    meta = yaml.safe_load(header)
                    url = meta.get("url", "") if meta else ""
                    return url, body
                except yaml.YAMLError:
                    pass
        
        return "", content


class TextChunker:
    """テキストのチャンク化クラス"""
    
    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size
    
    def chunk_text(self, text: str) -> List[str]:
        """
        テキストを指定されたサイズでチャンク化する
        
        Args:
            text: チャンク化するテキスト
            
        Returns:
            チャンク化されたテキストのリスト
        """
        import re
        
        sentences = re.split(r"(?<=[。．！？!?\n])", text)
        chunks = []
        current = ""
        
        for sentence in sentences:
            if len(current) + len(sentence) > self.chunk_size and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current += sentence
        
        if current.strip():
            chunks.append(current.strip())
        
        return [chunk for chunk in chunks if chunk]


class FTPDataSource:
    """FTPデータソースクラス"""
    
    def __init__(self, host: str, user: str = "anonymous", password: str = ""):
        self.host = host
        self.user = user
        self.password = password
    
    def list_md_files(self, path: str) -> List[str]:
        """FTPサーバー上のMarkdownファイルを再帰的に取得する"""
        md_files = []
        
        with FTP(self.host) as ftp:
            ftp.login(user=self.user, passwd=self.password)
            md_files = self._list_md_files_recursive(ftp, path)
        
        return md_files
    
    def _list_md_files_recursive(self, ftp: FTP, path: str) -> List[str]:
        """FTPサーバー上のMarkdownファイルを再帰的に取得する（内部メソッド）"""
        md_files = []
        
        try:
            ftp.cwd(path)
            items = ftp.nlst()
        except error_perm:
            return []
        
        for item in items:
            if item in ('.', '..'):
                continue
            
            sub_path = path.rstrip('/') + '/' + item
            
            try:
                ftp.cwd(sub_path)
                # ディレクトリなら再帰
                md_files.extend(self._list_md_files_recursive(ftp, sub_path))
                ftp.cwd('..')
            except error_perm:
                # ファイルなら拡張子チェック
                if item.lower().endswith('.md'):
                    md_files.append(sub_path)
        
        return md_files
    
    def download_file(self, remote_path: str, local_path: str):
        """FTPサーバーからファイルをダウンロードする"""
        with FTP(self.host) as ftp:
            ftp.login(user=self.user, passwd=self.password)
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
    
    def get_markdown_files(self, data_dir: str) -> Iterator[Tuple[str, str, str]]:
        """
        FTPサーバーからMarkdownファイルを取得する
        
        Yields:
            (url, body, filename): URL、本文、ファイル名のタプル
        """
        md_files = self.list_md_files(data_dir)
        print(f"📁 FTPから{len(md_files)}個のMarkdownファイルを発見")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            for remote_path in md_files:
                local_path = os.path.join(tmpdir, os.path.basename(remote_path))
                self.download_file(remote_path, local_path)
                
                url, body = MarkdownParser.parse_markdown_with_url(local_path)
                filename = os.path.basename(remote_path)
                
                yield url, body, filename


class LocalDataSource:
    """ローカルデータソースクラス"""
    
    def __init__(self, directory: str):
        self.directory = directory
    
    def list_md_files(self) -> List[str]:
        """ローカルディレクトリ配下のMarkdownファイルを再帰的に取得する"""
        md_files = []
        
        if not os.path.exists(self.directory):
            print(f"⚠️  ローカルディレクトリが存在しません: {self.directory}")
            return md_files
        
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
        
        return md_files
    
    def get_markdown_files(self) -> Iterator[Tuple[str, str, str]]:
        """
        ローカルディレクトリからMarkdownファイルを取得する
        
        Yields:
            (url, body, filename): URL、本文、ファイル名のタプル
        """
        md_files = self.list_md_files()
        print(f"📁 ローカルから{len(md_files)}個のMarkdownファイルを発見")
        
        for file_path in md_files:
            try:
                url, body = MarkdownParser.parse_markdown_with_url(file_path)
                filename = os.path.basename(file_path)
                yield url, body, filename
            except Exception as e:
                print(f"⚠️  ファイル読み込みエラー ({file_path}): {e}")
                continue


class DatabaseBuilder:
    """データベース構築クラス"""
    
    def __init__(self, db_path: str = SQLITE_DB_PATH):
        self.db_path = db_path
        self.model_manager = EmbeddingModelManager()
        self.chunker = TextChunker()
    
    def initialize_database(self) -> sqlite3.Connection:
        """sqlite-vecデータベースを初期化する"""
        # 既存のDBファイルがあれば削除
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # SQLiteデータベースに接続
        conn = sqlite3.connect(self.db_path)
        
        # 拡張機能の読み込みを有効化
        conn.enable_load_extension(True)
        
        # sqlite-vec拡張を読み込み
        sqlite_vec.load(conn)
        
        # 拡張機能の読み込みを無効化（セキュリティのため）
        conn.enable_load_extension(False)
        
        # vec0仮想テーブルを作成
        conn.execute(f"""
            CREATE VIRTUAL TABLE docs USING vec0(
                embedding float[{EMBEDDING_DIMENSION}],
                chunk_text TEXT,
                url TEXT,
                file_name TEXT,
                source TEXT
            )
        """)
        
        # メタデータ用のテーブルも作成
        conn.execute("""
            CREATE TABLE doc_metadata (
                id INTEGER PRIMARY KEY,
                url TEXT,
                file_name TEXT,
                source TEXT,
                chunk_text TEXT
            )
        """)
        
        conn.commit()
        return conn
    
    def build_database(self):
        """データベースを構築する"""
        config = ConfigManager.get_data_source_config()
        
        print("📋 データソース設定:")
        print(f"  使用するソース: {'FTP' if config['use_ftp_source'] else 'ローカル'}")
        
        if config['use_ftp_source']:
            print(f"  FTPホスト: {config['ftp_host']}")
            print(f"  FTPディレクトリ: {config['ftp_data_dir']}")
            data_source = FTPDataSource(
                config['ftp_host'], 
                config['ftp_user'], 
                config['ftp_pass']
            )
            markdown_files = data_source.get_markdown_files(config['ftp_data_dir'])
            source_type = "ftp"
        else:
            print(f"  ローカルディレクトリ: {config['local_dir']}")
            data_source = LocalDataSource(config['local_dir'])
            markdown_files = data_source.get_markdown_files()
            source_type = "local"
        
        # データベースを初期化
        conn = self.initialize_database()
        
        # データを収集
        texts = []
        metadatas = []
        
        try:
            for url, body, filename in markdown_files:
                chunks = self.chunker.chunk_text(body)
                for chunk in chunks:
                    texts.append(chunk)
                    metadatas.append({
                        "url": url,
                        "file_name": filename,
                        "source": source_type
                    })
        except Exception as e:
            print(f"⚠️  データ取得エラー: {e}")
            conn.close()
            return
        
        if not texts:
            print("⚠️  処理するテキストが見つかりませんでした")
            conn.close()
            return
        
        print(f"🔄 {len(texts)}個のチャンクの埋め込みを生成中...")
        
        # バッチ処理でデータベースに挿入
        for i, (text, metadata) in enumerate(tqdm(
            zip(texts, metadatas),
            total=len(texts),
            desc="埋め込み生成・挿入",
            unit="チャンク",
            ncols=80
        )):
            # 埋め込みベクトルを生成
            embedding = self.model_manager.get_embedding(text)
            
            # sqlite-vecのserialize_float32を使用してベクトルをシリアライズ
            embedding_blob = sqlite_vec.serialize_float32(embedding)
            
            # vec0仮想テーブルに挿入
            conn.execute("""
                INSERT INTO docs (embedding, chunk_text, url, file_name, source)
                VALUES (?, ?, ?, ?, ?)
            """, (
                embedding_blob, 
                text, 
                metadata["url"], 
                metadata["file_name"], 
                metadata["source"]
            ))
            
            # メタデータテーブルにも挿入
            conn.execute("""
                INSERT INTO doc_metadata (url, file_name, source, chunk_text)
                VALUES (?, ?, ?, ?)
            """, (
                metadata["url"], 
                metadata["file_name"], 
                metadata["source"], 
                text
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ sqlite-vec構築完了: {len(texts)}件のチャンクを追加しました。")