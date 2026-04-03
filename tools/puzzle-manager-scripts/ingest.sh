#!/bin/bash
# Puzzle Manager Ingest Script
# Usage: ./ingest.sh <source> [batch-size]
# Example: ./ingest.sh ogs 5
# 
# Runs the puzzle manager ingest command in the background
# Logs are written to ./logs/ with unique timestamp-based filenames

set -e

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
DEFAULT_BATCH_SIZE=5

# --- Parse Arguments ---
SOURCE="${1:-}"
BATCH_SIZE="${2:-$DEFAULT_BATCH_SIZE}"

# --- Validation ---
if [[ -z "$SOURCE" ]]; then
    echo "Error: Source is required"
    echo ""
    echo "Usage: $0 <source> [batch-size]"
    echo ""
    echo "Arguments:"
    echo "  source      Required. The puzzle source (e.g., ogs, sanderland, goproblems)"
    echo "  batch-size  Optional. Number of puzzles per batch (default: $DEFAULT_BATCH_SIZE)"
    echo ""
    echo "Examples:"
    echo "  $0 ogs           # Ingest from OGS with default batch size"
    echo "  $0 ogs 10        # Ingest from OGS with batch size 10"
    echo "  $0 sanderland 5  # Ingest from sanderland with batch size 5"
    echo ""
    exit 1
fi

# --- Ensure log directory exists ---
mkdir -p "$LOG_DIR"

# --- Generate unique log filename ---
# Format: YYYYMMDD_HHMMSS_<random_hash>.log
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RANDOM_HASH=$(head -c 4 /dev/urandom | xxd -p)
LOG_FILE="$LOG_DIR/${SOURCE}_${TIMESTAMP}_${RANDOM_HASH}.log"

# --- Run ingest in background ---
echo "Starting ingest pipeline..."
echo "  Source:     $SOURCE"
echo "  Batch size: $BATCH_SIZE"
echo "  Log file:   $LOG_FILE"
echo ""

cd "$PROJECT_ROOT"

# Run the command in background, redirect both stdout and stderr to log file
nohup python -m backend.puzzle_manager run --source "$SOURCE" --batch-size "$BATCH_SIZE" > "$LOG_FILE" 2>&1 &

PID=$!
echo "Process started in background (PID: $PID)"
echo "Monitor with: tail -f $LOG_FILE"
echo ""
