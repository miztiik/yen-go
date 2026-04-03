# Building KataGo for WebAssembly (WASM)

**A step-by-step guide to compiling KataGo C++ into a browser-ready WASM binary that reads `.bin.gz` models directly — no TF.js, no model conversion.**

*Last Updated: 2026-02-26*

---

## Why WASM?

KataGo compiled to WASM runs **the same code as native KataGo** — full MCTS search, ownership head, analysis protocol — but inside a web browser. The `.bin.gz` model files from [katagotraining.org](https://katagotraining.org/networks/) work without any conversion. This is the same approach used by [web-katrain](https://sir-teo.github.io/web-katrain/).

| | Native KataGo | WASM KataGo | TF.js (not recommended) |
|---|---|---|---|
| Model format | `.bin.gz` | `.bin.gz` (same!) | `model.json` (converted) |
| MCTS search | Yes | Yes | No |
| Backend | GPU (OpenCL/CUDA) | EIGEN (CPU) | WebGL/WebGPU |
| Install required | Yes (binary) | No (runs in browser) | No |
| Speed | Fast (GPU) | Slower (CPU via WASM) | Fast eval, no search |

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| **Emscripten SDK** | Latest | `git clone https://github.com/emscripten-core/emsdk.git` |
| **CMake** | 3.16+ | `pip install cmake` |
| **Ninja** | Any | `pip install ninja` |
| **Git** | Any | Pre-installed |

### Install Emscripten

```bash
git clone https://github.com/emscripten-core/emsdk.git .emsdk
cd .emsdk
./emsdk install latest      # Windows: emsdk.bat install latest
./emsdk activate latest     # Windows: emsdk.bat activate latest
source ./emsdk_env.sh       # Windows: emsdk_env.bat (or use full paths)
```

### Install CMake + Ninja (if not on PATH)

```bash
pip install cmake ninja
```

---

## Build Steps

### 1. Clone KataGo Source + Eigen3

```bash
# KataGo source
git clone --depth 1 --branch v1.16.2 https://github.com/lightvector/KataGo.git KataGo

# Eigen3 (header-only linear algebra library)
git clone --depth 1 --branch 3.4.0 https://gitlab.com/libeigen/eigen.git eigen3
```

### 2. Patch CMakeLists.txt

KataGo's `CMakeLists.txt` needs three patches for WASM compatibility:

**Patch 1: Eigen3 detection** — Add before the `find_package(Eigen3)` block in the EIGEN backend section (~line 422):

```cmake
# Before: if(NOT (MSVC OR MINGW))
# After:
if(EIGEN3_INCLUDE_DIRS)
  message(STATUS "EIGEN3_INCLUDE_DIRS is set to ${EIGEN3_INCLUDE_DIRS}")
  include_directories(SYSTEM ${EIGEN3_INCLUDE_DIRS})
elseif(NOT (MSVC OR MINGW))
```

**Patch 2: Zlib** — Add Emscripten zlib port support (~line 455):

```cmake
# Before: else()  (the zlib not found error block)
# After:
elseif(EMSCRIPTEN)
  message(STATUS "Using Emscripten's built-in zlib port")
  target_compile_options(katago PRIVATE -sUSE_ZLIB=1)
  target_link_options(katago PRIVATE -sUSE_ZLIB=1)
else()
```

**Patch 3: CPU flags** — WASM doesn't support x86 SSE/AVX or libatomic (~line 530):

```cmake
# Before: if(NOT (${CMAKE_SYSTEM_PROCESSOR} MATCHES "(arm|aarch32|aarch64)"))
# After:
if(EMSCRIPTEN)
  message(STATUS "Emscripten/WASM build: skipping SSE/AVX, setting BYTE_ORDER")
  target_compile_definitions(katago PRIVATE BYTE_ORDER=1234 LITTLE_ENDIAN=1234 BIG_ENDIAN=4321)
elseif(NOT (${CMAKE_SYSTEM_PROCESSOR} MATCHES "(arm|aarch32|aarch64)"))
```

And for libatomic (~line 565):

```cmake
# Before: target_link_libraries(katago "atomic")
# After:
if(NOT EMSCRIPTEN)
  target_link_libraries(katago "atomic")
endif()
```

### 3. Configure with Emscripten

```bash
mkdir build && cd build

emcmake cmake ../KataGo/cpp \
  -G Ninja \
  -DCMAKE_MAKE_PROGRAM=$(which ninja) \
  -DCMAKE_BUILD_TYPE=Release \
  -DUSE_BACKEND=EIGEN \
  -DBUILD_DISTRIBUTED=OFF \
  -DUSE_TCMALLOC=OFF \
  -DNO_GIT_REVISION=ON \
  -DEIGEN3_INCLUDE_DIRS=$(pwd)/../eigen3
```

**On Windows (PowerShell):**

```powershell
$emsdk = "path\to\.emsdk"
& "$emsdk\upstream\emscripten\emcmake.bat" cmake ..\KataGo\cpp `
  -G Ninja `
  "-DCMAKE_MAKE_PROGRAM=path\to\ninja.exe" `
  -DCMAKE_BUILD_TYPE=Release `
  -DUSE_BACKEND=EIGEN `
  -DBUILD_DISTRIBUTED=OFF `
  -DUSE_TCMALLOC=OFF `
  -DNO_GIT_REVISION=ON `
  "-DEIGEN3_INCLUDE_DIRS=path\to\eigen3"
```

### 4. Build

```bash
emmake cmake --build . --target katago -j 4
```

**Expected output:** `katago.js` (~100KB) + `katago.wasm` (~47MB)

### 5. Deploy

Copy the build artifacts to your web server:

```bash
cp katago.js katago.wasm /path/to/your/web/app/vendor/katago-wasm/
```

---

## Using in the Browser

### Serving Requirements

The server must send COOP/COEP headers for `SharedArrayBuffer` (threading):

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

### Loading the WASM Binary

```javascript
// Load the Emscripten-generated JS module
const KataGo = await KataGoModule({
  locateFile: (path) => `vendor/katago-wasm/${path}`,
  // Virtual filesystem for the model
  preRun: [(module) => {
    module.FS.createPreloadedFile('/', 'model.bin.gz', 'models-data/g170e-b10c128.bin.gz', true, false);
  }]
});

// Run analysis mode
KataGo.callMain(['analysis', '-model', '/model.bin.gz', '-config', '/analysis.cfg']);
```

### Model Selection for Browser

| Model | Size | Download Time (50Mbps) | Recommended |
|-------|------|----------------------|-------------|
| b6c96 | 4MB | <1s | Quick tests |
| **b10c128** | **11MB** | **~2s** | **Best for browser** |
| b15c192 | 35MB | ~6s | Strong but slow download |

Models larger than b15c192 are impractical for browser download.

**Download models from GitHub (no auth required):**

```bash
# b10c128 (recommended)
curl -L -o model.bin.gz https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170e-b10c128-s1141046784-d204142634.bin.gz

# b6c96 (smallest)
curl -L -o model.bin.gz https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170-b6c96-s175395328-d26788732.bin.gz
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `unknown FP unit 'sse'` | x86 SSE flag in WASM build | Patch 3: guard with `if(EMSCRIPTEN)` |
| `Define BYTE_ORDER` | Missing endianness defines | Patch 3: add `BYTE_ORDER=1234` |
| `unable to find library -latomic` | libatomic not in Emscripten | Patch 3: skip with `if(NOT EMSCRIPTEN)` |
| `zlib was not found` | CMake can't find zlib | Patch 2: use `-sUSE_ZLIB=1` |
| `Eigen3 was not found` | CMake can't find Eigen | Patch 1: set `EIGEN3_INCLUDE_DIRS` |
| `cmake executable not found` | CMake not on PATH | `pip install cmake` |
| `no compatible cmake generator` | Ninja not found | `pip install ninja` |

---

## Build Summary

```
KataGo v1.16.2 C++ source
  + Eigen3 3.4.0 (header-only)
  + Emscripten SDK (latest)
  + 4 CMakeLists.txt patches
  ────────────────────────
  emcmake cmake → emmake cmake --build
  ────────────────────────
  → katago.js   (~139KB)  Emscripten loader
  → katago.wasm (~47MB)   WASM binary
  ────────────────────────
  + any .bin.gz model     Same format as local KataGo
  = Full KataGo in browser (in theory)
```

---

## Lessons Learned (2026-02-26)

### What Worked
- **Compilation succeeded.** KataGo C++ compiles to WASM with 4 CMakeLists.txt patches.
- **The .bin.gz format is universal.** Same model file for native and WASM — no conversion.
- **Emscripten SDK installs easily** via `emsdk install latest` (even on Windows).

### What Didn't Work
- **JS integration is the hard part, not compilation.** Compiling took ~5 minutes. Wiring the WASM binary into a browser page took hours and still doesn't work reliably.
- **stdin/stdout emulation is fragile.** KataGo's analysis mode uses stdin for queries and stdout for responses. Emscripten's stdin/stdout redirection via `Module.print`/`Module.stdin` is tricky — the non-modularized build uses a global `Module` object that must be configured *before* the script loads, and stdin blocking semantics don't map cleanly to the async browser environment.
- **30-second timeout on initialization.** Loading the 47MB WASM binary + 11MB model + KataGo startup (OpenCL probe, NN warmup) exceeds typical browser timeouts.
- **Non-modularized build.** We compiled without `-s MODULARIZE=1`, so the WASM exports as a global `Module` rather than a callable factory function. This makes it harder to instantiate cleanly.

### How web-katrain Solves This
web-katrain's approach is fundamentally different from our naive "compile and load" strategy:

1. **Custom engine wrapper (~2000+ LOC TypeScript)** — They don't use KataGo's stdin/stdout analysis mode. Instead, they reimplemented the MCTS search, board logic, and NN evaluation in TypeScript, using the WASM module only for the neural network forward pass.
2. **Web Worker isolation** — All computation runs in a dedicated Web Worker, preventing the main thread from blocking.
3. **Chunked model loading** — The model is loaded in chunks with progress callbacks, not as a single blocking fetch.
4. **No callMain()** — They never call KataGo's `main()`. They use the WASM module as a library, calling individual functions for NN evaluation.

### Recommendation for Next Steps

**Option A: Fork web-katrain's engine** (recommended)
- Copy their `src/engine/` TypeScript files (~5 files, ~3000 LOC)
- Adapt to our analysis protocol
- Use their pre-built WASM module or build our own
- Effort: ~2-3 days for a working prototype

**Option B: Rebuild with MODULARIZE and threading**
- Recompile with `-s MODULARIZE=1 -s EXPORT_NAME='KataGoModule' -s USE_PTHREADS=1`
- Implement proper async stdin/stdout via a SharedArrayBuffer message queue
- Run KataGo's `main()` in a Web Worker with proper I/O redirection
- Effort: ~3-5 days, requires deep Emscripten knowledge

**Option C: Use the local engine exclusively** (current working state)
- The local KataGo engine works perfectly for puzzle enrichment
- Browser engine is a "nice to have" for interactive demos
- Focus engineering effort on the enrichment pipeline (Phase A tasks)
- Effort: 0 days (already working)

### Build Artifacts Status

| Artifact | Status | Size | Location |
|----------|--------|------|----------|
| `katago.js` | Built, served | 139KB | `vendor/katago-wasm/katago.js` |
| `katago.wasm` | Built, served | 47MB | `vendor/katago-wasm/katago.wasm` |
| JS integration | **Broken** — stdin/stdout redirection fails, initialization times out | — | `js/browser-engine.js` |
| b10c128 model | Downloaded | 11MB | `models-data/g170e-b10c128.bin.gz` |

---

> **See also:**
> - [Puzzle Enrichment Lab README](../../tools/puzzle-enrichment-lab/README.md)
> - [Research: Browser & Local KataGo](001-research-browser-and-local-katago-for-tsumego.md)
> - [web-katrain](https://github.com/Sir-Teo/web-katrain) — Reference implementation (working browser KataGo)
> - [web-katrain engine source](https://github.com/Sir-Teo/web-katrain/tree/main/src/engine) — The JS/TS code that actually works
> - [KataGo](https://github.com/lightvector/KataGo) — Source code
> - [Emscripten](https://emscripten.org/) — C++ to WASM compiler
