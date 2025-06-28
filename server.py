#!/usr/bin/env python3
"""
sqlite-vecベクトル検索MCPサーバー

このサーバーは以下の機能を提供します:
- FastMCPを使用したMCPツールサーバー
- sqlite-vecによるベクトル検索API
- JSON形式での検索結果返却

使用方法:
    python search_server.py [オプション]
    
オプション:
    --port: HTTPポート番号（デフォルト: 8080）
    --transport: トランスポート種別（stdio/streamable-http）
    --host: バインドホスト（デフォルト: 0.0.0.0）
    --stateless: ステートレスモードで実行
"""

import json
from typing import Optional

import anyio
import click
import mcp.types as types
from mcp.server.fastmcp import FastMCP, Context

from lib.vector_utils import get_vector_search_service


class SearchServer:
    """検索サーバークラス"""
    
    def __init__(self, host: str, port: int, stateless: bool = False):
        self.host = host
        self.port = port
        self.stateless = stateless
        self.vector_service = get_vector_search_service()
        
        # FastMCPサーバーを作成
        self.app = FastMCP(
            name="Search Server",
            instructions="sqlite-vecを使用したベクトル検索サーバーです。",
            host=host,
            port=port,
            stateless_http=stateless
        )
        
        # ツールを登録
        self._register_tools()
    
    def _register_tools(self):
        """MCPツールを登録する"""
        
        @self.app.tool(description="sqlite-vecによるベクトル検索を行い、結果を返します。")
        async def search(query: str, top_k: int = 5, ctx: Context = None) -> str:
            """
            ベクトル検索を実行します。
            
            Args:
                query: 検索クエリ
                top_k: 返す件数（デフォルト: 5）
                ctx: コンテキスト（自動注入）
            
            Returns:
                検索結果のJSON文字列
            """
            if ctx:
                await ctx.info(f"検索クエリ: {query}, 件数: {top_k}")
            
            try:
                # ベクトル検索を実行
                results = self.vector_service.search(query, top_k)
                
                if ctx:
                    await ctx.info(f"検索完了: {len(results)}件の結果")
                
                return json.dumps(
                    {"results": results}, 
                    ensure_ascii=False, 
                    indent=2
                )
                
            except Exception as e:
                error_msg = f"検索エラー: {str(e)}"
                if ctx:
                    await ctx.error(error_msg)
                return json.dumps(
                    {"error": error_msg, "results": []}, 
                    ensure_ascii=False
                )
    
    def run(self, transport: str = "stdio"):
        """サーバーを実行する"""
        if transport == "streamable-http":
            self.app.run(transport="streamable-http")
        else:
            self.app.run(transport="stdio")


@click.command()
@click.option("--port", default=8080, help="Port to listen on for HTTP")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "streamable-http"]),
    default="stdio",
    help="Transport type",
)
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--stateless", is_flag=True, help="Run in stateless mode")
def main(port: int, transport: str, host: str, stateless: bool) -> int:
    """メイン関数"""
    try:
        server = SearchServer(host, port, stateless)
        server.run(transport)
        return 0
    except KeyboardInterrupt:
        print("\n👋 サーバーを停止します")
        return 0
    except Exception as e:
        print(f"❌ サーバーエラー: {e}")
        return 1


if __name__ == "__main__":
    main()