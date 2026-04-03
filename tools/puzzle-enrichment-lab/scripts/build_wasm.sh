#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Build KataGo WASM — Compile KataGo C++ to WebAssembly
# ═══════════════════════════════════════════════════════════
#
#  This script compiles KataGo from source to WASM using Emscripten.
#  The resulting katago.js + katago.wasm can run in the browser
#  and load .bin.gz models directly — same format as local KataGo.
#
#  Prerequisites:
#    - Emscripten SDK (emsdk) installed and activated
#    - CMake 3.16+
#    - Git
#
#  Install Emscripten:
#    git clone https://github.com/emscripten-core/emsdk.git
#    cd emsdk
#    ./emsdk install latest
#    ./emsdk activate latest
#    source ./emsdk_env.sh
#
#  Usage:
#    ./scripts/build_wasm.sh              # Build with default settings
#    ./scripts/build_wasm.sh --clean      # Clean and rebuild
#
#  Output:
#    vendor/katago-wasm/katago.js          # Emscripten JS loader
#    vendor/katago-wasm/katago.wasm        # WASM binary
#    vendor/katago-wasm/katago.worker.js   # Web Worker (if threading enabled)
#
#  References:
#    - web-katrain builds KataGo to WASM similarly
#    - https://github.com/Sir-Teo/web-katrain
#    - https://emscripten.org/docs/compiling/Building-Projects.html
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$LAB_DIR/.wasm-build"
OUTPUT_DIR="$LAB_DIR/vendor/katago-wasm"
KATAGO_REPO="https://github.com/lightvector/KataGo.git"
KATAGO_VERSION="v1.16.2"

echo ""
echo "  KataGo WASM Build Pipeline"
echo "  ==========================="
echo ""

# ── Check prerequisites ──
check_prereq() {
    if ! command -v emcc &>/dev/null; then
        echo "  [ERROR] Emscripten (emcc) not found."
        echo ""
        echo "  Install Emscripten SDK:"
        echo "    git clone https://github.com/emscripten-core/emsdk.git"
        echo "    cd emsdk"
        echo "    ./emsdk install latest"
        echo "    ./emsdk activate latest"
        echo "    source ./emsdk_env.sh"
        echo ""
        exit 1
    fi

    if ! command -v cmake &>/dev/null; then
        echo "  [ERROR] CMake not found. Install CMake 3.16+"
        exit 1
    fi

    echo "  Emscripten: $(emcc --version | head -1)"
    echo "  CMake: $(cmake --version | head -1)"
    echo ""
}

# ── Clean ──
if [ "$1" = "--clean" ]; then
    echo "  Cleaning build directory..."
    rm -rf "$BUILD_DIR"
fi

# ── Clone KataGo source ──
clone_katago() {
    if [ -d "$BUILD_DIR/KataGo" ]; then
        echo "  [OK] KataGo source already cloned"
        return
    fi

    echo "  Cloning KataGo $KATAGO_VERSION..."
    mkdir -p "$BUILD_DIR"
    git clone --depth 1 --branch "$KATAGO_VERSION" "$KATAGO_REPO" "$BUILD_DIR/KataGo"
    echo "  [OK] Cloned"
}

# ── Build WASM ──
build_wasm() {
    echo "  Building KataGo WASM..."
    mkdir -p "$BUILD_DIR/build"
    cd "$BUILD_DIR/build"

    # Configure with Emscripten
    # Key settings:
    #   - EIGEN backend (CPU-based, works in WASM)
    #   - No CUDA/OpenCL (not available in browser)
    #   - Threading support via SharedArrayBuffer
    emcmake cmake "$BUILD_DIR/KataGo/cpp" \
        -DCMAKE_BUILD_TYPE=Release \
        -DUSE_BACKEND=EIGEN \
        -DBUILD_DISTRIBUTED=OFF \
        -DUSE_TCMALLOC=OFF \
        -DNO_GIT_REVISION=ON \
        -DCMAKE_EXE_LINKER_FLAGS="-s ALLOW_MEMORY_GROWTH=1 -s INITIAL_MEMORY=256MB -s MAXIMUM_MEMORY=2GB -s MODULARIZE=1 -s EXPORT_NAME='KataGoModule' -s EXPORTED_RUNTIME_METHODS=['FS','callMain'] -s FORCE_FILESYSTEM=1 -s ENVIRONMENT='web,worker' -s EXIT_RUNTIME=0 --embed-file /dev/null@/dev/null" \
        2>&1

    # Build
    emmake make -j$(nproc 2>/dev/null || echo 4) katago 2>&1

    echo "  [OK] Build complete"
}

# ── Copy output ──
copy_output() {
    echo "  Copying WASM artifacts..."
    mkdir -p "$OUTPUT_DIR"

    # The build produces katago.js and katago.wasm
    if [ -f "$BUILD_DIR/build/katago.js" ]; then
        cp "$BUILD_DIR/build/katago.js" "$OUTPUT_DIR/"
        cp "$BUILD_DIR/build/katago.wasm" "$OUTPUT_DIR/"
        [ -f "$BUILD_DIR/build/katago.worker.js" ] && cp "$BUILD_DIR/build/katago.worker.js" "$OUTPUT_DIR/"

        local wasm_size=$(du -m "$OUTPUT_DIR/katago.wasm" 2>/dev/null | cut -f1)
        echo "  [OK] Output:"
        echo "    $OUTPUT_DIR/katago.js"
        echo "    $OUTPUT_DIR/katago.wasm (${wasm_size}MB)"
    else
        echo "  [ERROR] Build did not produce katago.js"
        echo "  Check build output above for errors."
        exit 1
    fi
}

# ── Main ──
check_prereq
clone_katago
build_wasm
copy_output

echo ""
echo "  Build complete!"
echo "  WASM files are in: $OUTPUT_DIR"
echo ""
echo "  To use in browser, the WASM KataGo loads .bin.gz models directly."
echo "  Same models as local KataGo — no conversion needed."
echo ""
