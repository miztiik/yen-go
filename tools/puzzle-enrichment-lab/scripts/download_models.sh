#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Puzzle Enrichment Lab — Download KataGo Model
# ═══════════════════════════════════════════════════════════
#
#  Downloads a single KataGo model (.bin.gz) used for both:
#    - Local engine (KataGo subprocess reads .bin.gz directly)
#    - Browser engine (needs TF.js conversion, separate step)
#
#  The .bin.gz format is the same for both use cases.
#
#  Usage:
#    ./scripts/download_models.sh                    # Default: b15c192 (~40MB)
#    ./scripts/download_models.sh b10c128            # Smaller: ~15MB
#    ./scripts/download_models.sh b18c384            # Larger:  ~160MB
#    ./scripts/download_models.sh b28c512            # Strongest: ~450MB
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$LAB_DIR/models-data"

# ── Model catalog ──
# Primary URLs: katagotraining.org (may block automated downloads)
# Fallback URLs: GitHub raw (smaller models only, always works)
declare -A MODEL_URLS
MODEL_URLS[b6c96]="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b6c96-s175395328-d26788732.bin.gz"
MODEL_URLS[b10c128]="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b10c128-s1141046784-d204142634.bin.gz"
MODEL_URLS[b15c192]="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b15c192-s1672170752-d466197061.bin.gz"
MODEL_URLS[b18c384]="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"
MODEL_URLS[b28c512]="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b28c512nbt-s12192929536-d5655876072.bin.gz"

# Fallback URLs from GitHub (no auth required, always works)
declare -A MODEL_FALLBACK_URLS
MODEL_FALLBACK_URLS[b6c96]="https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170-b6c96-s175395328-d26788732.bin.gz"

declare -A MODEL_SIZES
MODEL_SIZES[b6c96]="~4MB, ~9900 Elo"
MODEL_SIZES[b10c128]="~15MB, ~11500 Elo"
MODEL_SIZES[b15c192]="~40MB, ~12200 Elo"
MODEL_SIZES[b18c384]="~160MB, ~13600 Elo"
MODEL_SIZES[b28c512]="~450MB, ~14090 Elo"

# Also offer a quick "browser" alias that grabs the small model from GitHub
MODEL_URLS[browser]="${MODEL_FALLBACK_URLS[b6c96]}"
MODEL_SIZES[browser]="~4MB (b6c96 from GitHub, always works)"

# Default model
MODEL="${1:-b15c192}"

if [ -z "${MODEL_URLS[$MODEL]}" ]; then
    echo "  Unknown model: $MODEL"
    echo "  Available: b6c96, b10c128, b15c192, b18c384, b28c512"
    exit 1
fi

URL="${MODEL_URLS[$MODEL]}"
FILENAME=$(basename "$URL")
DEST="$MODELS_DIR/$FILENAME"

echo ""
echo "  Puzzle Enrichment Lab - Model Downloader"
echo "  ========================================="
echo "  Model:       $MODEL (${MODEL_SIZES[$MODEL]})"
echo "  File:        $FILENAME"
echo "  Destination: $MODELS_DIR/"
echo ""

mkdir -p "$MODELS_DIR"

# Check if already downloaded
if [ -f "$DEST" ]; then
    file_size=$(wc -c < "$DEST" 2>/dev/null || echo 0)
    if [ "$file_size" -gt 1000000 ]; then
        size_mb=$((file_size / 1048576))
        echo "  [OK] Already exists: $FILENAME (${size_mb}MB)"
        echo ""
        exit 0
    else
        echo "  [WARN] Existing file is too small, re-downloading..."
        rm -f "$DEST"
    fi
fi

echo "  Downloading..."

# Full browser-like headers
if curl -L -o "$DEST" \
    -# \
    --fail \
    --retry 3 \
    --retry-delay 5 \
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36" \
    -H "Accept: application/octet-stream,application/gzip,*/*;q=0.9" \
    -H "Accept-Language: en-US,en;q=0.9" \
    -H "Accept-Encoding: identity" \
    -H "Referer: https://katagotraining.org/networks/" \
    -H "Origin: https://katagotraining.org" \
    -H "DNT: 1" \
    -H "Connection: keep-alive" \
    -H "Sec-Fetch-Dest: document" \
    -H "Sec-Fetch-Mode: navigate" \
    -H "Sec-Fetch-Site: same-site" \
    "$URL" 2>/dev/null; then

    # Validate downloaded file
    file_size=$(wc -c < "$DEST" 2>/dev/null || echo 0)

    if [ "$file_size" -lt 1000000 ]; then
        # Likely an error page
        if head -c 200 "$DEST" 2>/dev/null | grep -qi "error\|denied\|forbidden\|xml"; then
            echo "  [FAIL] Server returned error page instead of model."
            rm -f "$DEST"
        else
            echo "  [WARN] File is unexpectedly small (${file_size} bytes)."
        fi
    else
        size_mb=$((file_size / 1048576))
        echo "  [OK] Downloaded: $FILENAME (${size_mb}MB)"
        echo ""
        echo "  To use this model, set in config.json:"
        echo "    \"model_path\": \"models-data/$FILENAME\""
        echo ""
        exit 0
    fi
fi

# Try fallback URL if available
FALLBACK="${MODEL_FALLBACK_URLS[$MODEL]:-}"
if [ -n "$FALLBACK" ] && [ "$FALLBACK" != "$URL" ]; then
    FALLBACK_FILE=$(basename "$FALLBACK")
    FALLBACK_DEST="$MODELS_DIR/$FALLBACK_FILE"
    echo "  Trying fallback URL (GitHub)..."
    echo "  URL: $FALLBACK"

    if curl -L -o "$FALLBACK_DEST" \
        -# \
        --fail \
        "$FALLBACK" 2>/dev/null; then

        file_size=$(wc -c < "$FALLBACK_DEST" 2>/dev/null || echo 0)
        if [ "$file_size" -gt 1000000 ]; then
            size_mb=$((file_size / 1048576))
            echo "  [OK] Downloaded from GitHub: $FALLBACK_FILE (${size_mb}MB)"
            echo ""
            echo "  To use this model, set in config.json:"
            echo "    \"model_path\": \"models-data/$FALLBACK_FILE\""
            echo ""
            exit 0
        else
            rm -f "$FALLBACK_DEST"
        fi
    fi
fi

# Download failed — show manual instructions
echo ""
echo "  +----------------------------------------------------------"
echo "  | MANUAL DOWNLOAD REQUIRED"
echo "  |"
echo "  | The server blocks automated downloads. Please:"
echo "  |"
echo "  | 1. Open in your browser:"
echo "  |    $URL"
echo "  |"
echo "  | 2. Save to:"
echo "  |    $MODELS_DIR/$FILENAME"
echo "  |"
echo "  | 3. Update config.json:"
echo "  |    \"model_path\": \"models-data/$FILENAME\""
echo "  |"
echo "  | Or browse all models at:"
echo "  |    https://katagotraining.org/networks/"
echo "  +----------------------------------------------------------"
echo ""
[ -f "$DEST" ] && rm -f "$DEST"
exit 1
