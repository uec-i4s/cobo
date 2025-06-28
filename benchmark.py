#!/usr/bin/env python3
"""
ベクトル検索パフォーマンス測定プログラム

使用方法:
    python benchmark.py                      # 基本ベンチマーク
    python benchmark.py --detailed           # 詳細分析
    python benchmark.py --queries "クエリ1" "クエリ2"  # カスタムクエリ
"""

import sys
import time
import statistics
from typing import List
from lib.vector_utils import get_vector_search_service


# デフォルトテストクエリ
DEFAULT_QUERIES = [
    "大学", "授業", "履修", "成績", "卒業",
    "学生証", "図書館", "研究室", "試験", "単位"
]


def measure_search_time(service, query: str, runs: int = 3) -> dict:
    """検索時間を測定"""
    times = []
    
    for _ in range(runs):
        start = time.time()
        results = service.search(query, top_k=5)
        end = time.time()
        times.append(end - start)
    
    return {
        'query': query,
        'times': times,
        'avg': statistics.mean(times),
        'min': min(times),
        'max': max(times),
        'results_count': len(results) if 'results' in locals() else 0
    }


def run_basic_benchmark():
    """基本ベンチマークを実行"""
    print("🚀 基本ベンチマーク開始")
    print("=" * 50)
    
    service = get_vector_search_service()
    
    # ウォームアップ
    print("🔥 ウォームアップ中...")
    service.search("test", top_k=1)
    
    # ベンチマーク実行
    results = []
    for query in DEFAULT_QUERIES[:5]:  # 最初の5つのクエリ
        print(f"📊 測定中: {query}")
        result = measure_search_time(service, query)
        results.append(result)
    
    # 結果表示
    print("\n📈 結果:")
    print("-" * 50)
    total_times = []
    
    for result in results:
        print(f"{result['query']:8} | {result['avg']:.3f}s (±{result['max']-result['min']:.3f}s)")
        total_times.extend(result['times'])
    
    print("-" * 50)
    print(f"平均時間: {statistics.mean(total_times):.3f}s")
    print(f"最速時間: {min(total_times):.3f}s")
    print(f"最遅時間: {max(total_times):.3f}s")


def run_detailed_analysis():
    """詳細分析を実行"""
    print("🔬 詳細パフォーマンス分析")
    print("=" * 50)
    
    service = get_vector_search_service()
    
    # システム情報
    stats = service.analyze_performance()
    print(f"💾 DBサイズ: {stats['db_size_mb']:.1f}MB")
    print(f"🖥️  デバイス: {stats.get('device', 'Unknown')}")
    print(f"🗄️  キャッシュ: {stats['embedding_cache_size']}/{stats['embedding_cache_limit']}")
    
    # SQLite設定
    print(f"\n⚙️  SQLite設定:")
    for key, value in stats['pragma_settings'].items():
        print(f"   {key}: {value}")
    
    # パフォーマンステスト
    print(f"\n📊 パフォーマンステスト:")
    
    # 初回検索（コールドスタート）
    start = time.time()
    service.search("初回テスト", top_k=5)
    cold_time = time.time() - start
    print(f"   コールドスタート: {cold_time:.3f}s")
    
    # 同じクエリ（キャッシュヒット）
    start = time.time()
    service.search("初回テスト", top_k=5)
    cache_time = time.time() - start
    print(f"   キャッシュヒット: {cache_time:.3f}s")
    
    # 異なるクエリ（新規）
    start = time.time()
    service.search("新規テスト", top_k=5)
    new_time = time.time() - start
    print(f"   新規クエリ: {new_time:.3f}s")
    
    # パフォーマンス評価
    print(f"\n💡 評価:")
    if cold_time < 0.2:
        print("   ✅ 初回検索速度: 良好")
    else:
        print("   ⚠️  初回検索速度: 改善の余地あり")
    
    if cache_time < 0.05:
        print("   ✅ キャッシュ効果: 良好")
    else:
        print("   ⚠️  キャッシュ効果: 改善の余地あり")


def run_custom_queries(queries: List[str]):
    """カスタムクエリでベンチマーク"""
    print(f"🎯 カスタムクエリベンチマーク ({len(queries)}件)")
    print("=" * 50)
    
    service = get_vector_search_service()
    
    for query in queries:
        result = measure_search_time(service, query, runs=1)
        print(f"{query:15} | {result['avg']:.3f}s | {result['results_count']}件")


def main():
    if len(sys.argv) == 1:
        run_basic_benchmark()
    elif "--detailed" in sys.argv:
        run_detailed_analysis()
    elif "--queries" in sys.argv:
        idx = sys.argv.index("--queries")
        queries = sys.argv[idx+1:]
        if queries:
            run_custom_queries(queries)
        else:
            print("❌ --queriesの後にクエリを指定してください")
    else:
        print("❌ 不明なオプション")
        print("使用方法: python benchmark.py [--detailed] [--queries クエリ1 クエリ2 ...]")


if __name__ == "__main__":
    main()