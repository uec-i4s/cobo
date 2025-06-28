#!/usr/bin/env python3
"""
sqlite-vecデータベース構築スクリプト

このスクリプトは以下の処理を行います:
1. 設定に基づいてデータソース（FTPまたはローカル）からMarkdownファイルを取得
2. テキストをチャンク化
3. 埋め込みベクトルを生成
4. sqlite-vecデータベースに格納

使用方法:
    python build_db.py
"""

from lib.data_processing import DatabaseBuilder


def main():
    """メイン関数"""
    try:
        builder = DatabaseBuilder()
        builder.build_database()
    except KeyboardInterrupt:
        print("\n⚠️  処理が中断されました")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    main()