#!/bin/bash
#===============================================================================
# EidoGo Problem Downloader v2.0
# 
# Downloads Go/Tsumego problems from EidoGo.com with robust status tracking,
# HTTP response code handling, and automatic retry with backoff.
# 
# Available Collections:
#   qjzm    - Qi Jing Zhong Miao / Gokyo Shumyo (520 problems)
#   xuanlan - Xuanlan / Genran (61 problems)
#   xxqj    - Xuan Xuan Qi Jing / Gengen Gokyo (347 problems)
#
# Status Tracking Files (in output_dir/collection/):
#   .status.log        - Full status log (problem|status|http_code|timestamp|error)
#   .completed         - List of successfully downloaded problem numbers
#   .failed_problems   - List of failed problems (problem|http_code|error)
#   .download_state    - Last successfully downloaded problem number
#   .rate_limit_state  - Current delay multiplier after rate limits
#
#===============================================================================

# Default configuration
BASE_OUTPUT_DIR="./eidogo_puzzles"
BASE_DELAY=10
JITTER=5
COLLECTION=""
START_NUM=""
END_NUM=""
SINGLE_NUM=""
RESUME=false
RETRY_FAILED=false
SHOW_STATUS=false
QUIET=false
MAX_RETRIES=3
RATE_LIMIT_MULTIPLIER=1

# Collection metadata
declare -A COLLECTION_MAX=(
    ["qjzm"]=520
    ["xuanlan"]=61
    ["xxqj"]=347
)

declare -A COLLECTION_NAMES=(
    ["qjzm"]="Qi Jing Zhong Miao / Gokyo Shumyo"
    ["xuanlan"]="Xuanlan / Genran"
    ["xxqj"]="Xuan Xuan Qi Jing / Gengen Gokyo"
)

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

#===============================================================================
# Help and Info Functions
#===============================================================================

show_help() {
    cat << 'EOF'
EidoGo Problem Downloader v2.0
==============================

Available Collections:
  qjzm    - Qi Jing Zhong Miao / Gokyo Shumyo (520 problems)
  xuanlan - Xuanlan / Genran (61 problems)
  xxqj    - Xuan Xuan Qi Jing / Gengen Gokyo (347 problems)
  --------------------------------------------------------
  Total: 928 problems across all collections

Usage:
  ./eidogo_downloader.sh -c <collection> [options]

Options:
  -c, --collection NAME   Collection to download (qjzm|xuanlan|xxqj|all)
                          REQUIRED - must specify which collection

  -s, --start NUM         Starting problem number (default: 1)
                          Use to begin downloading from a specific problem

  -e, --end NUM           Ending problem number (default: max for collection)
                          Use to limit how many problems to download
                          Example: -e 100 downloads only first 100 problems

  -n, --single NUM        Download only ONE specific problem by number

  -o, --output DIR        Base output directory (default: ./eidogo_puzzles)
                          Files saved to: <output>/<collection>/

  -d, --delay SECS        Base delay between requests in seconds (default: 10)
                          This is the MINIMUM wait time between downloads
                          Increase this to be gentler on the server

  -j, --jitter SECS       Random jitter ADDED to delay (default: 5)
                          Final delay = base + random(0 to jitter)
                          Example: -d 20 -j 25 = wait 20-45 seconds each time

  -r, --resume            Resume from last downloaded problem
                          Reads .download_state file to continue where stopped

  -f, --retry-failed      Retry only previously failed downloads
                          Reads .failed_problems file and retries those URLs

  -t, --status            Show download status/progress for collection

  -l, --list              List available collections and exit

  -q, --quiet             Suppress console output (still writes to log file)

  -h, --help              Show this help message

Examples:

  # Download first 100 problems from qjzm with 20-45 second delays
  ./eidogo_downloader.sh -c qjzm -e 100 -d 20 -j 25

  # Download problems 50-100 from qjzm
  ./eidogo_downloader.sh -c qjzm -s 50 -e 100 -d 20 -j 25

  # Resume an interrupted download (run in background with &)
  ./eidogo_downloader.sh -c qjzm -d 20 -j 25 -r &

  # Download in batches for long-running jobs
  ./eidogo_downloader.sh -c qjzm -s 1 -e 100 -d 20 -j 25    # Batch 1
  ./eidogo_downloader.sh -c qjzm -s 101 -e 200 -d 20 -j 25  # Batch 2

  # Check how many are done
  ./eidogo_downloader.sh -c qjzm -t

  # Retry any that failed
  ./eidogo_downloader.sh -c qjzm -f -d 30 -j 30

  # Download single problem #5 for testing
  ./eidogo_downloader.sh -c xxqj -n 5

  # Download all collections (928 problems total - very long!)
  ./eidogo_downloader.sh -c all -d 20 -j 25

Delay Calculation:
  total_wait = (base_delay + random(0..jitter)) * rate_limit_multiplier

  Normal:      -d 20 -j 25  =>  20 + (0-25) = 20-45 seconds
  Rate limited (2x):        =>  (20 + 0-25) * 2 = 40-90 seconds

  Time estimate for 100 problems at -d 20 -j 25:
    ~32.5 sec avg * 100 = ~54 minutes

Status Tracking Files (in output/<collection>/):
  .status.log      - Full audit trail of all download attempts
  .completed       - List of successfully downloaded problem numbers
  .failed_problems - Failed downloads with HTTP codes and errors
  .download_state  - Last successful problem (for -r resume)
  .rate_limit_state - Current delay multiplier if rate limited

HTTP Response Handling:
  200 - Success, file saved
  429 - Rate limited: auto-doubles delay multiplier (max 8x)
  503 - Service unavailable: auto-doubles delay multiplier
  000 - Network error: logged, will retry
EOF
    exit 0
}

list_collections() {
    echo ""
    echo "Available EidoGo Collections:"
    echo "=============================="
    for col in "${!COLLECTION_NAMES[@]}"; do
        printf "  %-10s %s (%d problems)\n" "$col" "${COLLECTION_NAMES[$col]}" "${COLLECTION_MAX[$col]}"
    done
    echo ""
    exit 0
}

#===============================================================================
# Logging Functions
#===============================================================================

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_line="[$timestamp] [$level] $message"
    
    # Always write to log file
    if [ -n "$LOG_FILE" ]; then
        echo "$log_line" >> "$LOG_FILE"
    fi
    
    # Print to console unless quiet mode
    if [ "$QUIET" = false ]; then
        case $level in
            INFO)    echo -e "${BLUE}[INFO]${NC} $message" ;;
            SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
            WARN)    echo -e "${YELLOW}[WARN]${NC} $message" ;;
            ERROR)   echo -e "${RED}[ERROR]${NC} $message" ;;
            PROG)    echo -e "${CYAN}[PROGRESS]${NC} $message" ;;
            HTTP)    echo -e "${MAGENTA}[HTTP]${NC} $message" ;;
            *)       echo "$message" ;;
        esac
    fi
}

progress_bar() {
    local current=$1
    local total=$2
    local width=40
    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "  Progress: ["
    printf "%${filled}s" | tr ' ' '#'
    printf "%${empty}s" | tr ' ' '-'
    printf "] %3d%% (%d/%d)\n" "$percent" "$current" "$total"
}

#===============================================================================
# Status Tracking Functions
#===============================================================================

init_status_tracking() {
    local output_dir=$1
    
    # Ensure tracking files exist
    touch "${output_dir}/.status.log"
    touch "${output_dir}/.completed"
}

update_status() {
    local output_dir=$1
    local problem_num=$2
    local status=$3          # "success", "failed", "rate_limited"
    local http_code=$4
    local error_msg=${5:-""}
    
    local timestamp=$(date '+%Y-%m-%dT%H:%M:%S')
    
    # Append to status log
    echo "${problem_num}|${status}|${http_code}|${timestamp}|${error_msg}" >> "${output_dir}/.status.log"
    
    # Update tracking files based on status
    case $status in
        success)
            # Add to completed list (if not already there)
            if ! grep -q "^${problem_num}$" "${output_dir}/.completed" 2>/dev/null; then
                echo "$problem_num" >> "${output_dir}/.completed"
            fi
            # Remove from failed if it was there
            if [ -f "${output_dir}/.failed_problems" ]; then
                grep -v "^${problem_num}|" "${output_dir}/.failed_problems" > "${output_dir}/.failed_problems.tmp" 2>/dev/null || true
                mv "${output_dir}/.failed_problems.tmp" "${output_dir}/.failed_problems" 2>/dev/null || true
            fi
            ;;
        failed|rate_limited)
            # Add/update in failed list
            if [ -f "${output_dir}/.failed_problems" ]; then
                grep -v "^${problem_num}|" "${output_dir}/.failed_problems" > "${output_dir}/.failed_problems.tmp" 2>/dev/null || true
                mv "${output_dir}/.failed_problems.tmp" "${output_dir}/.failed_problems" 2>/dev/null || true
            fi
            echo "${problem_num}|${http_code}|${error_msg}" >> "${output_dir}/.failed_problems"
            ;;
    esac
}

is_completed() {
    local output_dir=$1
    local problem_num=$2
    
    if [ -f "${output_dir}/.completed" ]; then
        grep -q "^${problem_num}$" "${output_dir}/.completed" 2>/dev/null
        return $?
    fi
    return 1
}

show_status() {
    local collection=$1
    local output_dir="${BASE_OUTPUT_DIR}/${collection}"
    local max=${COLLECTION_MAX[$collection]}
    
    echo ""
    echo "Status for collection: $collection (${COLLECTION_NAMES[$collection]})"
    echo "========================================"
    
    if [ ! -d "$output_dir" ]; then
        echo "  No downloads attempted yet."
        echo ""
        return
    fi
    
    local completed_count=0
    local failed_count=0
    
    if [ -f "${output_dir}/.completed" ]; then
        completed_count=$(sort -n "${output_dir}/.completed" 2>/dev/null | uniq | wc -l)
    fi
    
    if [ -f "${output_dir}/.failed_problems" ]; then
        failed_count=$(wc -l < "${output_dir}/.failed_problems" 2>/dev/null || echo 0)
    fi
    
    local remaining=$((max - completed_count))
    
    echo "  Total problems:    $max"
    echo "  Completed:         $completed_count"
    echo "  Failed:            $failed_count"
    echo "  Remaining:         $remaining"
    echo ""
    
    if [ $failed_count -gt 0 ] && [ -f "${output_dir}/.failed_problems" ]; then
        echo "  Failed problems (problem_num|http_code|error):"
        echo "  ------------------------------------------------"
        head -20 "${output_dir}/.failed_problems" | while read line; do
            echo "    $line"
        done
        if [ $failed_count -gt 20 ]; then
            echo "    ... and $((failed_count - 20)) more (see .failed_problems)"
        fi
        echo ""
    fi
    
    # Show rate limit state if exists
    if [ -f "${output_dir}/.rate_limit_state" ]; then
        local multiplier=$(cat "${output_dir}/.rate_limit_state")
        echo "  Current delay multiplier: ${multiplier}x (due to rate limiting)"
        echo ""
    fi
    
    # Show last few status entries
    if [ -f "${output_dir}/.status.log" ]; then
        echo "  Recent activity (last 10 entries):"
        echo "  -----------------------------------"
        tail -10 "${output_dir}/.status.log" | while read line; do
            echo "    $line"
        done
        echo ""
    fi
}

#===============================================================================
# Rate Limit Handling
#===============================================================================

get_rate_limit_multiplier() {
    local output_dir=$1
    local state_file="${output_dir}/.rate_limit_state"
    
    if [ -f "$state_file" ]; then
        cat "$state_file"
    else
        echo 1
    fi
}

increase_rate_limit() {
    local output_dir=$1
    local state_file="${output_dir}/.rate_limit_state"
    
    local current=$(get_rate_limit_multiplier "$output_dir")
    local new_multiplier=$((current * 2))
    
    # Cap at 8x
    if [ $new_multiplier -gt 8 ]; then
        new_multiplier=8
    fi
    
    echo $new_multiplier > "$state_file"
    log WARN "Rate limit detected! Increasing delay multiplier to ${new_multiplier}x"
}

reset_rate_limit() {
    local output_dir=$1
    local state_file="${output_dir}/.rate_limit_state"
    
    # Gradually decrease multiplier after successful requests
    if [ -f "$state_file" ]; then
        local current=$(cat "$state_file")
        if [ $current -gt 1 ]; then
            local new_multiplier=$((current - 1))
            echo $new_multiplier > "$state_file"
            log INFO "Decreased delay multiplier to ${new_multiplier}x after success"
        else
            rm -f "$state_file"
        fi
    fi
}

random_delay() {
    local base=$1
    local jitter=$2
    local multiplier=${3:-1}
    
    # Generate random jitter between 0 and jitter seconds
    local random_add=$((RANDOM % (jitter + 1)))
    local total_delay=$(( (base + random_add) * multiplier ))
    echo $total_delay
}

#===============================================================================
# Download Functions
#===============================================================================

download_single_problem() {
    local collection=$1
    local problem_num=$2
    local output_dir=$3
    local retry_count=${4:-0}
    
    local page_url="http://eidogo.com/problems/${collection}/${problem_num}"
    
    # Fetch page with HTTP code
    local tmp_file=$(mktemp)
    local page_http_code=$(curl -s -w "%{http_code}" -o "$tmp_file" "$page_url" 2>/dev/null)
    local page_content=$(cat "$tmp_file")
    rm -f "$tmp_file"
    
    log HTTP "Page request: $page_url -> HTTP $page_http_code"
    
    # Handle HTTP errors on page fetch
    case $page_http_code in
        200)
            # Success, continue
            ;;
        429|503)
            log WARN "Rate limited on page fetch (HTTP $page_http_code)"
            increase_rate_limit "$output_dir"
            update_status "$output_dir" "$problem_num" "rate_limited" "$page_http_code" "Page fetch rate limited"
            return 2  # Special return code for rate limit
            ;;
        000)
            log ERROR "Network error fetching page for problem $problem_num"
            update_status "$output_dir" "$problem_num" "failed" "000" "Network error"
            return 1
            ;;
        *)
            log ERROR "HTTP $page_http_code fetching page for problem $problem_num"
            update_status "$output_dir" "$problem_num" "failed" "$page_http_code" "Page fetch failed"
            return 1
            ;;
    esac
    
    # Extract SGF path
    local sgf_path=$(echo "$page_content" | grep -oP 'sgf="/sgf/[^"]+\.sgf"' | sed 's/sgf="//;s/"//' | head -1)
    
    if [ -z "$sgf_path" ]; then
        log ERROR "Could not find SGF path for problem $problem_num (page may have changed)"
        update_status "$output_dir" "$problem_num" "failed" "$page_http_code" "SGF path not found in page"
        return 1
    fi
    
    local sgf_url="http://eidogo.com${sgf_path}"
    local output_file="${output_dir}/${collection}_problem$(printf '%04d' $problem_num).sgf"
    
    # Download SGF with HTTP code
    local sgf_http_code=$(curl -s -w "%{http_code}" -o "$output_file" "$sgf_url" 2>/dev/null)
    
    log HTTP "SGF request: $sgf_url -> HTTP $sgf_http_code"
    
    # Handle SGF download result
    case $sgf_http_code in
        200)
            if [ -f "$output_file" ] && [ -s "$output_file" ]; then
                local file_size=$(wc -c < "$output_file")
                log SUCCESS "Downloaded problem $problem_num -> $(basename $output_file) (${file_size} bytes)"
                update_status "$output_dir" "$problem_num" "success" "$sgf_http_code" ""
                reset_rate_limit "$output_dir"
                return 0
            else
                log ERROR "Downloaded file is empty for problem $problem_num"
                rm -f "$output_file"
                update_status "$output_dir" "$problem_num" "failed" "$sgf_http_code" "Empty file"
                return 1
            fi
            ;;
        429|503)
            log WARN "Rate limited on SGF download (HTTP $sgf_http_code)"
            rm -f "$output_file"
            increase_rate_limit "$output_dir"
            update_status "$output_dir" "$problem_num" "rate_limited" "$sgf_http_code" "SGF download rate limited"
            return 2
            ;;
        *)
            log ERROR "HTTP $sgf_http_code downloading SGF for problem $problem_num"
            rm -f "$output_file"
            update_status "$output_dir" "$problem_num" "failed" "$sgf_http_code" "SGF download failed"
            return 1
            ;;
    esac
}

download_with_retry() {
    local collection=$1
    local problem_num=$2
    local output_dir=$3
    
    local attempt=1
    local result=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        download_single_problem "$collection" "$problem_num" "$output_dir" "$attempt"
        result=$?
        
        if [ $result -eq 0 ]; then
            # Success
            return 0
        elif [ $result -eq 2 ]; then
            # Rate limited - wait longer and retry
            local multiplier=$(get_rate_limit_multiplier "$output_dir")
            local backoff_delay=$((BASE_DELAY * multiplier * 2))
            log WARN "Rate limited. Backing off for ${backoff_delay}s before retry (attempt $attempt/$MAX_RETRIES)"
            sleep $backoff_delay
        else
            # Other failure
            if [ $attempt -lt $MAX_RETRIES ]; then
                log WARN "Attempt $attempt failed, retrying in 5s..."
                sleep 5
            fi
        fi
        
        ((attempt++))
    done
    
    log ERROR "Failed to download problem $problem_num after $MAX_RETRIES attempts"
    return 1
}

download_collection() {
    local collection=$1
    local start=$2
    local end=$3
    
    local collection_name="${COLLECTION_NAMES[$collection]}"
    local output_dir="${BASE_OUTPUT_DIR}/${collection}"
    
    # Create output directory and initialize tracking
    mkdir -p "$output_dir"
    init_status_tracking "$output_dir"
    
    # Get rate limit state
    local multiplier=$(get_rate_limit_multiplier "$output_dir")
    
    log INFO "=========================================="
    log INFO "Downloading: $collection_name"
    log INFO "Collection ID: $collection"
    log INFO "Problems: $start to $end ($(( end - start + 1 )) total)"
    log INFO "Output directory: $output_dir"
    log INFO "Delay: ${BASE_DELAY}s base + 0-${JITTER}s jitter (x${multiplier} multiplier)"
    log INFO "Max retries per problem: $MAX_RETRIES"
    log INFO "=========================================="
    
    local success_count=0
    local fail_count=0
    local skip_count=0
    local total=$((end - start + 1))
    
    for ((i = start; i <= end; i++)); do
        local current=$((i - start + 1))
        
        # Check if already completed (for resume)
        if is_completed "$output_dir" "$i"; then
            log INFO "Skipping problem $i (already completed)"
            ((skip_count++))
            continue
        fi
        
        # Progress update
        if [ "$QUIET" = false ]; then
            progress_bar $current $total
        fi
        
        log PROG "Processing problem $i of $end (batch: $current/$total, success: $success_count, fail: $fail_count, skip: $skip_count)"
        
        if download_with_retry "$collection" "$i" "$output_dir"; then
            ((success_count++))
            # Save state after each success
            echo "$i" > "${output_dir}/.download_state"
        else
            ((fail_count++))
        fi
        
        # Delay before next request (unless last problem)
        if [ $i -lt $end ]; then
            multiplier=$(get_rate_limit_multiplier "$output_dir")
            local delay=$(random_delay $BASE_DELAY $JITTER $multiplier)
            log INFO "Waiting ${delay}s before next request..."
            sleep $delay
        fi
    done
    
    echo ""
    log INFO "=========================================="
    log INFO "Collection '$collection' complete!"
    log SUCCESS "Successfully downloaded: $success_count"
    log INFO "Skipped (already done): $skip_count"
    if [ $fail_count -gt 0 ]; then
        log WARN "Failed downloads: $fail_count"
        log INFO "To retry failed: ./eidogo_downloader.sh -c $collection -f"
    fi
    log INFO "=========================================="
}

retry_failed() {
    local collection=$1
    local output_dir="${BASE_OUTPUT_DIR}/${collection}"
    local failed_file="${output_dir}/.failed_problems"
    
    if [ ! -f "$failed_file" ] || [ ! -s "$failed_file" ]; then
        log INFO "No failed downloads to retry for collection '$collection'"
        return 0
    fi
    
    # Get unique failed problem numbers
    local failed_problems=$(cut -d'|' -f1 "$failed_file" | sort -n | uniq)
    local fail_count=$(echo "$failed_problems" | grep -c .)
    
    log INFO "=========================================="
    log INFO "Retrying $fail_count failed downloads for '$collection'"
    log INFO "=========================================="
    
    # Clear failed list (will be repopulated with still-failing)
    > "$failed_file"
    
    local success_count=0
    local still_failed=0
    local current=0
    
    for problem_num in $failed_problems; do
        ((current++))
        
        if [ "$QUIET" = false ]; then
            progress_bar $current $fail_count
        fi
        
        log PROG "Retrying problem $problem_num ($current/$fail_count)"
        
        if download_with_retry "$collection" "$problem_num" "$output_dir"; then
            ((success_count++))
        else
            ((still_failed++))
        fi
        
        # Delay between retries
        if [ $current -lt $fail_count ]; then
            local multiplier=$(get_rate_limit_multiplier "$output_dir")
            local delay=$(random_delay $BASE_DELAY $JITTER $multiplier)
            log INFO "Waiting ${delay}s before next retry..."
            sleep $delay
        fi
    done
    
    echo ""
    log INFO "=========================================="
    log INFO "Retry complete!"
    log SUCCESS "Successfully recovered: $success_count"
    if [ $still_failed -gt 0 ]; then
        log WARN "Still failing: $still_failed"
    fi
    log INFO "=========================================="
}

#===============================================================================
# Argument Parsing
#===============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--collection)
                COLLECTION="$2"
                shift 2
                ;;
            -s|--start)
                START_NUM="$2"
                shift 2
                ;;
            -e|--end)
                END_NUM="$2"
                shift 2
                ;;
            -n|--single)
                SINGLE_NUM="$2"
                shift 2
                ;;
            -o|--output)
                BASE_OUTPUT_DIR="$2"
                shift 2
                ;;
            -d|--delay)
                BASE_DELAY="$2"
                shift 2
                ;;
            -j|--jitter)
                JITTER="$2"
                shift 2
                ;;
            -r|--resume)
                RESUME=true
                shift
                ;;
            -f|--retry-failed)
                RETRY_FAILED=true
                shift
                ;;
            -t|--status)
                SHOW_STATUS=true
                shift
                ;;
            -l|--list)
                list_collections
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use -h or --help for usage information"
                exit 1
                ;;
        esac
    done
}

validate_args() {
    if [ -z "$COLLECTION" ]; then
        echo "Error: Collection is required. Use -c to specify."
        echo "Available collections: qjzm, xuanlan, xxqj, all"
        exit 1
    fi
    
    if [ "$COLLECTION" != "all" ] && [ -z "${COLLECTION_MAX[$COLLECTION]}" ]; then
        echo "Error: Unknown collection '$COLLECTION'"
        echo "Available collections: qjzm, xuanlan, xxqj, all"
        exit 1
    fi
}

#===============================================================================
# Main Entry Point
#===============================================================================

main() {
    parse_args "$@"
    validate_args
    
    # Create base output directory and log file
    mkdir -p "$BASE_OUTPUT_DIR"
    LOG_FILE="${BASE_OUTPUT_DIR}/download_$(date '+%Y%m%d_%H%M%S').log"
    
    log INFO "EidoGo Downloader v2.0 started"
    log INFO "Log file: $LOG_FILE"
    
    # Handle status display
    if [ "$SHOW_STATUS" = true ]; then
        if [ "$COLLECTION" = "all" ]; then
            for col in qjzm xuanlan xxqj; do
                show_status "$col"
            done
        else
            show_status "$COLLECTION"
        fi
        exit 0
    fi
    
    # Handle retry failed
    if [ "$RETRY_FAILED" = true ]; then
        if [ "$COLLECTION" = "all" ]; then
            for col in qjzm xuanlan xxqj; do
                retry_failed "$col"
                sleep 10
            done
        else
            retry_failed "$COLLECTION"
        fi
        exit 0
    fi
    
    # Handle 'all' collection
    if [ "$COLLECTION" = "all" ]; then
        for col in qjzm xuanlan xxqj; do
            local max=${COLLECTION_MAX[$col]}
            local start=${START_NUM:-1}
            local end=${END_NUM:-$max}
            
            if [ "$RESUME" = true ]; then
                local output_dir="${BASE_OUTPUT_DIR}/${col}"
                if [ -f "${output_dir}/.download_state" ]; then
                    start=$(($(cat "${output_dir}/.download_state") + 1))
                    log INFO "Resuming '$col' from problem $start"
                fi
            fi
            
            download_collection "$col" "$start" "$end"
            
            # Delay between collections
            if [ "$col" != "xxqj" ]; then
                log INFO "Pausing 30s before next collection..."
                sleep 30
            fi
        done
    else
        # Single collection
        local max=${COLLECTION_MAX[$COLLECTION]}
        local output_dir="${BASE_OUTPUT_DIR}/${COLLECTION}"
        
        if [ -n "$SINGLE_NUM" ]; then
            # Download single problem
            mkdir -p "$output_dir"
            init_status_tracking "$output_dir"
            download_with_retry "$COLLECTION" "$SINGLE_NUM" "$output_dir"
        else
            # Download range
            local start=${START_NUM:-1}
            local end=${END_NUM:-$max}
            
            if [ "$RESUME" = true ]; then
                if [ -f "${output_dir}/.download_state" ]; then
                    start=$(($(cat "${output_dir}/.download_state") + 1))
                    log INFO "Resuming from problem $start"
                fi
            fi
            
            # Validate range
            if [ $start -lt 1 ]; then start=1; fi
            if [ $end -gt $max ]; then end=$max; fi
            
            download_collection "$COLLECTION" "$start" "$end"
        fi
    fi
    
    log INFO "=========================================="
    log INFO "All downloads complete!"
    log INFO "Output location: $BASE_OUTPUT_DIR"
    log INFO "Full log: $LOG_FILE"
    log INFO "To check status: ./eidogo_downloader.sh -c $COLLECTION -t"
    log INFO "=========================================="
}

# Run main function
main "$@"
