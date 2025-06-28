#!/usr/bin/env python3
"""
シンプルなベクトル検索テストプログラム

使用方法:
    python simple_test.py                    # インタラクティブモード
    python simple_test.py info               # データベース情報表示
    python simple_test.py "検索クエリ"        # 単発検索
"""

import sys
from lib.vector_utils import get_vector_search_service


def show_database_info():
    """データベース情報を表示"""
    service = get_vector_search_service()
    info = service.get_database_info()
    
    print("📊 データベース情報:")
    print("=" * 40)
    print(f"   sqlite-vec: {info['version']}")
    print(f"   ドキュメント数: {info['doc_count']}")
    print(f"   メタデータ数: {info['meta_count']}")


def search_and_display(query: str):
    """検索を実行して結果を表示"""
    service = get_vector_search_service()
    results = service.search(query, top_k=3)
    
    print(f"\n🔍 検索: '{query}'")
    print("=" * 40)
    
    if not results:
        print("❌ 結果が見つかりませんでした")
        return
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['file']}")
        print(f"   距離: {result['distance']:.4f}")
        print(f"   内容: {result['text'][:100]}...")


def interactive_mode():
    """インタラクティブモード"""
    print("🔍 ベクトル検索テスト")
    print("終了: quit")
    print("-" * 30)
    
    while True:
        try:
            query = input("\n検索クエリ: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 終了")
                break
            
            if not query:
                continue
            
            search_and_display(query)
            
        except KeyboardInterrupt:
            print("\n👋 終了")
            break


def main():
    if len(sys.argv) == 1:
        # インタラクティブモード
        show_database_info()
        interactive_mode()
    elif sys.argv[1] == "info":
        # 情報表示のみ
        show_database_info()
    else:
        # 単発検索
        query = " ".join(sys.argv[1:])
        show_database_info()
        search_and_display(query)


if __name__ == "__main__":
    main()