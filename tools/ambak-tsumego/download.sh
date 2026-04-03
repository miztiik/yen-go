#!/bin/bash
# =============================================================================
# Ambak Tsumego Download Script
# =============================================================================
# Downloads SGF puzzle files from https://github.com/ambak/tsumego-bot
# and places them in external-sources/ambak-tsumego/problems/
#
# This is a ONE-TIME IMPORT script. The SGF files are downloaded and stored
# locally for use with the LocalAdapter in the puzzle manager pipeline.
#
# Usage:
#   bash tools/ambak-tsumego/download.sh
#
# Output structure:
#   external-sources/ambak-tsumego/
#   └── problems/
#       ├── elementary/
#       ├── intermediate/
#       └── advanced/
# =============================================================================

set -e  # Exit on error

# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_URL="https://github.com/ambak/tsumego-bot/archive/refs/heads/master.zip"
REPO_NAME="tsumego-bot-master"
OUTPUT_DIR="$PROJECT_ROOT/external-sources/ambak-tsumego/problems"
TEMP_DIR="$SCRIPT_DIR/.tmp"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/download_$(date +%Y%m%d_%H%M%S).log"

# =============================================================================
# Logging Functions
# =============================================================================
setup_logging() {
    mkdir -p "$LOG_DIR"
    # Start logging to both console and file
    exec > >(tee -a "$LOG_FILE") 2>&1
    echo "=============================================="
    echo "Ambak Tsumego Download Script"
    echo "Started: $(date)"
    echo "Log file: $LOG_FILE"
    echo "=============================================="
}

log_info() {
    echo "[INFO] $(date +%H:%M:%S) $1"
}

log_success() {
    echo "[SUCCESS] $(date +%H:%M:%S) $1"
}

log_error() {
    echo "[ERROR] $(date +%H:%M:%S) $1" >&2
}

log_warn() {
    echo "[WARN] $(date +%H:%M:%S) $1"
}

# =============================================================================
# Cleanup Function
# =============================================================================
cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
        log_info "Cleanup complete"
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# =============================================================================
# Main Functions
# =============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for required commands
    local missing_cmds=()
    for cmd in curl unzip; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_cmds+=("$cmd")
        fi
    done
    
    if [[ ${#missing_cmds[@]} -gt 0 ]]; then
        log_error "Missing required commands: ${missing_cmds[*]}"
        log_error "Please install them and try again."
        exit 1
    fi
    
    log_success "All prerequisites met"
}

check_existing_files() {
    if [[ -d "$OUTPUT_DIR" ]]; then
        local existing_count=$(find "$OUTPUT_DIR" -name "*.sgf" 2>/dev/null | wc -l)
        if [[ $existing_count -gt 0 ]]; then
            log_warn "Output directory already exists with $existing_count SGF files"
            log_warn "Directory: $OUTPUT_DIR"
            echo ""
            read -p "Do you want to overwrite? (y/N): " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Aborted by user"
                exit 0
            fi
            log_info "Removing existing files..."
            rm -rf "$OUTPUT_DIR"
        fi
    fi
}

download_repo() {
    log_info "Creating temporary directory..."
    mkdir -p "$TEMP_DIR"
    
    local zip_file="$TEMP_DIR/repo.zip"
    
    log_info "Downloading repository archive from GitHub..."
    log_info "URL: $REPO_URL"
    
    if curl -L -f -o "$zip_file" "$REPO_URL" --progress-bar; then
        log_success "Download complete"
    else
        log_error "Failed to download repository"
        exit 1
    fi
    
    log_info "Extracting archive..."
    if unzip -q "$zip_file" -d "$TEMP_DIR"; then
        log_success "Extraction complete"
    else
        log_error "Failed to extract archive"
        exit 1
    fi
}

copy_sgf_files() {
    local source_dir="$TEMP_DIR/$REPO_NAME/tsumego"
    
    if [[ ! -d "$source_dir" ]]; then
        log_error "Source directory not found: $source_dir"
        exit 1
    fi
    
    log_info "Creating output directory structure..."
    mkdir -p "$OUTPUT_DIR"
    
    local total_files=0
    local folders=("elementary" "intermediate" "advanced")
    
    echo ""
    echo "=============================================="
    echo "Copying SGF files by category"
    echo "=============================================="
    
    for folder in "${folders[@]}"; do
        local src="$source_dir/$folder"
        local dst="$OUTPUT_DIR/$folder"
        
        if [[ -d "$src" ]]; then
            mkdir -p "$dst"
            
            # Count files
            local file_count=$(find "$src" -name "*.sgf" | wc -l)
            
            log_info "Copying $folder: $file_count files..."
            
            # Copy SGF files only
            find "$src" -name "*.sgf" -exec cp {} "$dst/" \;
            
            # Verify copy
            local copied_count=$(find "$dst" -name "*.sgf" | wc -l)
            
            if [[ $copied_count -eq $file_count ]]; then
                log_success "$folder: $copied_count files copied"
            else
                log_warn "$folder: Expected $file_count, copied $copied_count"
            fi
            
            total_files=$((total_files + copied_count))
        else
            log_warn "Folder not found: $folder"
        fi
    done
    
    echo ""
    echo "=============================================="
    log_success "Total SGF files copied: $total_files"
    echo "=============================================="
}

generate_summary() {
    echo ""
    echo "=============================================="
    echo "Download Summary"
    echo "=============================================="
    echo "Output directory: $OUTPUT_DIR"
    echo ""
    echo "Files by category:"
    
    for folder in elementary intermediate advanced; do
        local dir="$OUTPUT_DIR/$folder"
        if [[ -d "$dir" ]]; then
            local count=$(find "$dir" -name "*.sgf" | wc -l)
            printf "  %-15s %5d files\n" "$folder:" "$count"
        fi
    done
    
    local total=$(find "$OUTPUT_DIR" -name "*.sgf" | wc -l)
    echo ""
    echo "  Total:          $total files"
    echo ""
    echo "=============================================="
    echo "Completed: $(date)"
    echo "Log file: $LOG_FILE"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "  1. Configure a source in the puzzle manager to use these files"
    echo "  2. Run the pipeline: python -m backend.puzzle_manager run --source ambak-tsumego"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================
main() {
    setup_logging
    check_prerequisites
    check_existing_files
    download_repo
    copy_sgf_files
    generate_summary
    
    log_success "Download script completed successfully!"
}

main "$@"
