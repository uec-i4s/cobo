#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

PID_FILE="search_server.pid"

# デフォルト設定
DEFAULT_TRANSPORT="streamable-http"
DEFAULT_PORT="8080"
DEFAULT_HOST="0.0.0.0"

# 設定ファイルから読み込み（存在する場合）
CONFIG_FILE=".server_config"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# 環境変数またはデフォルト値を使用
TRANSPORT=${TRANSPORT:-$DEFAULT_TRANSPORT}
PORT=${PORT:-$DEFAULT_PORT}
HOST=${HOST:-$DEFAULT_HOST}
STATELESS=${STATELESS:-false}

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "サーバーはすでに起動しています (PID: $PID)"
            exit 0
        else
            echo "古いPIDファイルを削除します"
            rm -f "$PID_FILE"
        fi
    fi
    
    # コマンドライン引数を構築
    CMD_ARGS="--transport $TRANSPORT"
    
    if [ "$TRANSPORT" = "streamable-http" ]; then
        CMD_ARGS="$CMD_ARGS --port $PORT --host $HOST"
        if [ "$STATELESS" = "true" ]; then
            CMD_ARGS="$CMD_ARGS --stateless"
        fi
        echo "StreamableHTTPサーバーを起動中..."
        echo "URL: http://$HOST:$PORT"
        echo "モード: $([ "$STATELESS" = "true" ] && echo "Stateless" || echo "Stateful")"
    else
        echo "STDIOサーバーを起動中..."
    fi
    
    uv run server.py $CMD_ARGS &
    PID=$!
    echo $PID > "$PID_FILE"
    echo "サーバーを起動しました (PID: $PID)"
    echo "設定: Transport=$TRANSPORT, Port=$PORT, Host=$HOST, Stateless=$STATELESS"
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "PIDファイルが存在しません。サーバーは起動していない可能性があります。"
        exit 0
    fi
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "サーバー (PID: $PID) を停止しました。"
    else
        echo "プロセス (PID: $PID) はすでに存在しません。"
    fi
    rm -f "$PID_FILE"
}

status_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "サーバーは起動していません。"
        exit 0
    fi
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "サーバーは起動中です (PID: $PID)"
        echo "設定: Transport=$TRANSPORT, Port=$PORT, Host=$HOST, Stateless=$STATELESS"
        if [ "$TRANSPORT" = "streamable-http" ]; then
            echo "URL: http://$HOST:$PORT"
        fi
    else
        echo "PIDファイルは存在しますが、プロセス (PID: $PID) は実行されていません。"
        rm -f "$PID_FILE"
    fi
}

show_config() {
    echo "現在の設定:"
    echo "  Transport: $TRANSPORT"
    echo "  Port: $PORT"
    echo "  Host: $HOST"
    echo "  Stateless: $STATELESS"
    echo ""
    echo "設定を変更するには、環境変数を設定するか、.server_configファイルを作成してください。"
    echo "例:"
    echo "  export TRANSPORT=stdio"
    echo "  export PORT=9000"
    echo "  export STATELESS=true"
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        status_server
        ;;
    config)
        show_config
        ;;
    restart)
        stop_server
        sleep 2
        start_server
        ;;
    *)
        echo "使い方: $0 {start|stop|status|config|restart}"
        echo ""
        echo "コマンド:"
        echo "  start   - サーバーを起動"
        echo "  stop    - サーバーを停止"
        echo "  status  - サーバーの状態を確認"
        echo "  config  - 現在の設定を表示"
        echo "  restart - サーバーを再起動"
        exit 1
        ;;
esac