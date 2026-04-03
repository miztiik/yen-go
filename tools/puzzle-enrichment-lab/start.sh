#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Puzzle Enrichment Lab — Start Server (Linux/macOS/Git Bash)
# ═══════════════════════════════════════════════════════════
#
#  Usage:
#    ./start.sh              — Start on default port 8999
#    ./start.sh 9000         — Start on custom port
#    ./start.sh restart      — Kill existing and restart
#    ./start.sh stop         — Stop the running server
# ═══════════════════════════════════════════════════════════

cd "$(dirname "$0")"

PORT="${1:-8999}"
PIDFILE=".bridge.pid"

# ── Stop command ──
stop_server() {
    # Method 1: PID file
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping server (PID $pid)..."
            kill "$pid" 2>/dev/null
            sleep 2
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
            echo "  Stopped."
        fi
        rm -f "$PIDFILE"
    fi

    # Method 2: Find by port (cross-platform)
    if command -v lsof &>/dev/null; then
        local pid=$(lsof -ti :${PORT} 2>/dev/null || true)
        if [ -n "$pid" ]; then
            echo "  Killing process on port $PORT (PID $pid)..."
            kill $pid 2>/dev/null
            sleep 2
        fi
    elif command -v netstat &>/dev/null; then
        # Windows Git Bash / MSYS2
        local pid=$(netstat -ano 2>/dev/null | grep ":${PORT} " | grep "LISTENING" | awk '{print $5}' | head -1)
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            echo "  Killing process on port $PORT (PID $pid)..."
            taskkill //PID "$pid" //F 2>/dev/null || kill -9 "$pid" 2>/dev/null
            sleep 2
        fi
    fi
}

# Handle stop/restart commands
if [ "$1" = "stop" ]; then
    stop_server
    echo "  Server stopped."
    exit 0
fi

if [ "$1" = "restart" ]; then
    stop_server
    PORT="${2:-8999}"
fi

# Handle numeric port argument
if [[ "$1" =~ ^[0-9]+$ ]]; then
    PORT="$1"
fi

echo ""
echo "  Puzzle Enrichment Lab"
echo "  Validate - Refute - Rate"
echo "  ========================"
echo ""

# Auto-create config.json from template if missing
if [ ! -f config.json ]; then
    if [ -f config.example.json ]; then
        cp config.example.json config.json
        echo "  [*] Created config.json from template."
    fi
fi

# Kill any existing process on our port
stop_server

echo "  Starting server on http://localhost:$PORT"
echo "  Press Ctrl+C to stop."
echo ""

# Start and record PID
PORT="$PORT" python bridge.py &
echo $! > "$PIDFILE"
wait $!
