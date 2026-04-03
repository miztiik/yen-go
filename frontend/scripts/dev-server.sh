#!/bin/bash
# Dev server management script for troubleshooting

PIDFILE="/tmp/vite-dev-server.pid"
LOGFILE="/tmp/vite-dev-server.log"
FRONTEND_DIR="$(dirname "$0")/.."

kill_all_dev_servers() {
    echo "Killing all existing Vite/node dev servers..."
    # Kill any process with 'vite' in the command line
    pkill -f "vite" 2>/dev/null || true
    # Kill any node processes running on common dev ports
    for port in 5173 5174 5175 5176 3000 3001 4173; do
        local pid
        pid=$(lsof -ti :$port 2>/dev/null) || pid=""
        if [ -n "$pid" ]; then
            echo "  Killing PID $pid on port $port"
            kill -9 $pid 2>/dev/null || true
        fi
    done
    rm -f "$PIDFILE"
    sleep 1
}

start_server() {
    kill_all_dev_servers

    cd "$FRONTEND_DIR"
    echo "Starting Vite dev server from $FRONTEND_DIR..."
    nohup npm run dev > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"

    # Poll until Vite prints the port (up to 30 s)
    PORT=""
    for i in $(seq 1 30); do
        PORT=$(grep -o 'localhost:[0-9]*' "$LOGFILE" 2>/dev/null | head -1 | sed 's/localhost://')
        [ -n "$PORT" ] && break
        sleep 1
    done

    if kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Server started with PID $(cat $PIDFILE)"
        echo "Server running on port: ${PORT:-unknown (check log)}"
        tail -10 "$LOGFILE"
    else
        echo "Failed to start server. Log:"
        cat "$LOGFILE"
        return 1
    fi
}

stop_server() {
    kill_all_dev_servers
    echo "All dev servers stopped"
}

restart_server() {
    start_server
}

status_server() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Server running with PID $(cat $PIDFILE)"
        echo "Recent log:"
        tail -20 "$LOGFILE" 2>/dev/null
    else
        echo "Server not running"
    fi
}

test_endpoint() {
    local URL="$1"
    echo "Testing: $URL"
    echo "---"
    curl -v "$URL" 2>&1 | head -40
    echo "---"
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    test)
        test_endpoint "${2:-http://localhost:5173/yengo-puzzle-collections/views/by-level/index.json}"
        ;;
    log)
        cat "$LOGFILE" 2>/dev/null || echo "No log file"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|test [url]|log}"
        exit 1
        ;;
esac
