#!/bin/bash
# =============================================================================
# Puzzle Manager CLI Wrapper (pm.sh)
# =============================================================================
#
# QUICK START:
#   ./pm.sh run ogs             # Run full pipeline (ingest → analyze → publish)
#   ./pm.sh run ogs 10          # Run full pipeline with batch size 10
#   ./pm.sh ingest ogs          # Run ingest stage only
#   ./pm.sh analyze ogs         # Run analyze stage only
#   ./pm.sh publish ogs         # Run publish stage only
#
# COMMANDS:
#   run <source> [batch]        Run full pipeline (all stages) in background
#   ingest <source> [batch]     Run ingest stage only in background
#   analyze <source> [batch]    Run analyze stage only in background
#   publish <source> [batch]    Run publish stage only in background
#   clean <target>              Clean logs|staging|state|all|retention
#   status                      Show current run status
#   help                        Show this help message
#
# MONITORING:
#   tail -f ./logs/<logfile>    Watch progress in real-time
#
# LOG FILES:
#   Script output  → ./logs/{source}_{timestamp}_{hash}.log
#   Python logs    → .pm-runtime/logs/ (puzzle manager internal)
#
# =============================================================================

set -e

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
DEFAULT_BATCH_SIZE=5

# --- Ensure log directory exists ---
mkdir -p "$LOG_DIR"

# --- Logging Functions ---
# Timestamp format: YYYY-MM-DD HH:MM:SS
timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log_info() {
    echo "$(timestamp) [INFO] $1"
}

log_action() {
    echo "$(timestamp) [ACTION] $1"
}

log_cmd() {
    echo "$(timestamp) [CMD] $1"
}

log_bg() {
    echo "$(timestamp) [BACKGROUND] $1"
}

log_done() {
    echo "$(timestamp) [DONE] $1"
}

log_error() {
    echo "$(timestamp) [ERROR] $1"
}

# --- Helper Functions ---
generate_log_file() {
    local prefix="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local random_hash=$(head -c 4 /dev/urandom | xxd -p)
    echo "$LOG_DIR/${timestamp}-${prefix}-${random_hash}.log"
}

show_help() {
    head -n 29 "$0" | tail -n 27
    exit 0
}

get_relative_path() {
    local target="$1"
    local current_dir=$(pwd)
    if [[ "$target" == "$current_dir"* ]]; then
        echo "${target#$current_dir/}"
    else
        echo "$target"
    fi
}

# --- Generic stage runner ---
run_stage() {
    local stage="$1"
    local source="$2"
    local batch_size="$3"
    local stage_label="$4"

    if [[ -z "$source" ]] || [[ "$source" == -* ]]; then
        log_error "Source is required for $stage"
        log_info "Usage: $0 $stage <source> [batch-size]"
        log_info "Examples:"
        log_info "  $0 $stage ogs           # Run $stage for OGS with default batch size"
        log_info "  $0 $stage ogs 10        # Run $stage for OGS with batch size 10"
        log_info "  $0 $stage sanderland 5  # Run $stage for sanderland with batch size 5"
        if [[ "$source" == -* ]]; then
             log_error "The argument '$source' starts with '-'. Sources must be specified as a positional argument (e.g. 'ogs'), not a flag."
        fi
        exit 1
    fi

    local log_file=$(generate_log_file "${source}-${stage}")
    local rel_log_file=$(get_relative_path "$log_file")

    log_action "Starting $stage_label"
    log_info "Source: $source"
    log_info "Batch size: $batch_size"
    log_info "Stage: $stage"
    log_info "Log file: $rel_log_file"

    cd "$PROJECT_ROOT"
    local cmd="python -m backend.puzzle_manager run --source $source --batch-size $batch_size --stage $stage"
    log_cmd "$cmd"
    log_bg "Running in background..."
    nohup $cmd > "$log_file" 2>&1 &

    local pid=$!
    log_bg "Process started (PID: $pid)"
    log_info "Monitor with: tail -f $rel_log_file"
}

# --- Command: run (full pipeline) ---
cmd_run() {
    local source="${1:-}"
    local batch_size="${2:-$DEFAULT_BATCH_SIZE}"

    if [[ -z "$source" ]] || [[ "$source" == -* ]]; then
        log_error "Source is required for run"
        log_info "Usage: $0 run <source> [batch-size]"
        log_info "Examples:"
        log_info "  $0 run ogs           # Run full pipeline for OGS"
        log_info "  $0 run ogs 10        # Run full pipeline with batch size 10"
        log_info "  $0 run sanderland 5  # Run full pipeline for sanderland"
        if [[ "$source" == -* ]]; then
             log_error "The argument '$source' starts with '-'. Sources must be specified as a positional argument (e.g. 'ogs'), not a flag."
        fi
        exit 1
    fi

    local log_file=$(generate_log_file "${source}-full")
    local rel_log_file=$(get_relative_path "$log_file")

    log_action "Starting full pipeline (ingest → analyze → publish)"
    log_info "Source: $source"
    log_info "Batch size: $batch_size"
    log_info "Log file: $rel_log_file"

    cd "$PROJECT_ROOT"
    local cmd="python -m backend.puzzle_manager run --source $source --batch-size $batch_size"
    log_cmd "$cmd"
    log_bg "Running in background..."
    nohup $cmd > "$log_file" 2>&1 &

    local pid=$!
    log_bg "Process started (PID: $pid)"
    log_info "Monitor with: tail -f $rel_log_file"
}

# --- Command: ingest ---
cmd_ingest() {
    run_stage "ingest" "${1:-}" "${2:-$DEFAULT_BATCH_SIZE}" "ingest stage (fetch → parse → validate)"
}

# --- Command: analyze ---
cmd_analyze() {
    run_stage "analyze" "${1:-}" "${2:-$DEFAULT_BATCH_SIZE}" "analyze stage (classify → tag → enrich)"
}

# --- Command: publish ---
cmd_publish() {
    run_stage "publish" "${1:-}" "${2:-$DEFAULT_BATCH_SIZE}" "publish stage (index → daily → output)"
}

# --- Command: clean ---
cmd_clean() {
    local target="${1:-}"

    if [[ -z "$target" ]]; then
        log_error "Target is required for clean"
        log_info "Usage: $0 clean <target>"
        log_info "Targets:"
        log_info "  logs      Clean log files"
        log_info "  staging   Clean staging directory"
        log_info "  state     Clean state directory"
        log_info "  all       Clean all three (state + staging + logs) immediately"
        log_info "  retention Clean using retention policy (45 days)"
        exit 1
    fi

    cd "$PROJECT_ROOT"
    case "$target" in
        logs)
            log_action "Cleaning log files"
            log_cmd "python -m backend.puzzle_manager clean --target logs"
            python -m backend.puzzle_manager clean --target logs
            log_done "Log files cleaned"
            ;;
        staging)
            log_action "Cleaning staging directory"
            log_cmd "python -m backend.puzzle_manager clean --target staging"
            python -m backend.puzzle_manager clean --target staging
            log_done "Staging directory cleaned"
            ;;
        state)
            log_action "Cleaning state directory"
            log_cmd "python -m backend.puzzle_manager clean --target state"
            python -m backend.puzzle_manager clean --target state
            log_done "State directory cleaned"
            ;;
        all)
            log_action "Cleaning all directories (state + staging + logs)"
            log_cmd "python -m backend.puzzle_manager clean --target state"
            python -m backend.puzzle_manager clean --target state
            log_done "State cleaned"
            log_cmd "python -m backend.puzzle_manager clean --target staging"
            python -m backend.puzzle_manager clean --target staging
            log_done "Staging cleaned"
            log_cmd "python -m backend.puzzle_manager clean --target logs"
            python -m backend.puzzle_manager clean --target logs
            log_done "Logs cleaned"
            log_done "All directories cleaned!"
            ;;
        retention)
            log_action "Cleaning with 45-day retention policy"
            log_cmd "python -m backend.puzzle_manager clean --retention-days 45"
            python -m backend.puzzle_manager clean --retention-days 45
            log_done "Retention-based cleanup complete"
            ;;
        *)
            log_error "Unknown clean target '$target'"
            exit 1
            ;;
    esac
}

# --- Command: status ---
cmd_status() {
    cd "$PROJECT_ROOT"
    log_action "Checking pipeline status"
    log_cmd "python -m backend.puzzle_manager status"
    python -m backend.puzzle_manager status
}

# --- Main ---
COMMAND="${1:-}"
shift 2>/dev/null || true

case "$COMMAND" in
    run)
        cmd_run "$@"
        ;;
    ingest)
        cmd_ingest "$@"
        ;;
    analyze)
        cmd_analyze "$@"
        ;;
    publish)
        cmd_publish "$@"
        ;;
    clean)
        cmd_clean "$@"
        ;;
    status)
        cmd_status
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        log_error "Unknown command '$COMMAND'"
        show_help
        ;;
esac
