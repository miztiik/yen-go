# Research Brief: 101weiqi.com Bulk Download Strategy — CAPTCHA Bypass Approaches

**Initiative ID**: `20260413-research-101weiqi-bulk-download-strategy`
**Date**: 2026-04-13
**Research Question**: What is the most effective strategy to download ~40,000+ Go puzzles from 101weiqi.com given Tencent CAPTCHA blocking after 5-10 automated requests, while keeping costs local (no cloud API)?

---

## 1. Research Boundaries

**In scope**: Browser automation frameworks, userscript/extension capture, keyboard macro approaches, local LLM-driven browser agents, hybrid human+script strategies, throughput estimates, checkpoint/resume integration with existing `tools/weiqi101/` infrastructure.

**Out of scope**: CAPTCHA solving services (2Captcha, etc.), proxy rotation networks, account creation automation, any approach requiring ongoing cloud API costs. Ethically, we are extracting publicly accessible puzzle data from pages we can view manually — the goal is to scale human browsing, not defeat security.

**Constraints**:
- Must work on Windows
- Must look like human browsing (real browser, real mouse/keyboard)
- Must extract `var qqdata = {...}` JavaScript object from each page
- Must checkpoint progress for resume on interruption
- Budget: local hardware only, no recurring cloud API costs
- One-time bulk activity (~40K pages)

---

## 2. Internal Code Evidence

### 2.1 Existing Download Infrastructure (`tools/weiqi101/`)

| R-ID | File | Finding |
|------|------|---------|
| R-1 | `tools/weiqi101/client.py` | httpx-based client with User-Agent spoofing, exponential backoff, retry logic. Gets blocked by Tencent CAPTCHA after 2-3 rapid requests per config comment. |
| R-2 | `tools/weiqi101/config.py` | `DEFAULT_PUZZLE_DELAY = 60.0` seconds between requests. `COOLDOWN_INTERVAL = 20` downloads between pauses. Even at 60s delays, CAPTCHA still triggers. |
| R-3 | `tools/weiqi101/extractor.py` | `extract_qqdata()` — regex + brace-matching parser for `var qqdata = {...}` from raw HTML. `is_rate_limited_page()` detects CAPTCHA via "TCaptcha.js" / "turing.captcha.qcloud.com" markers. |
| R-4 | `tools/weiqi101/converter.py` | `qqdata` → SGF conversion pipeline using `SgfBuilder`. Fully functional. |
| R-5 | `tools/weiqi101/storage.py` | SGF file saving with batch dirs, index management. Fully functional. |
| R-6 | `tools/weiqi101/checkpoint.py` | Resume state: tracks `last_puzzle_id`, `puzzles_downloaded`, `source_mode`. Per-output-dir isolation. |
| R-7 | `tools/weiqi101/orchestrator.py` | Main download loop with SIGINT handling, graceful checkpoint save, dedup via `sgf-index.txt`. |
| R-8 | `tools/weiqi101/models.py` | `PuzzleData.from_qqdata()` — fully parses qqdata JSON into typed dataclass (puzzle_id, stones, solution tree, level, type, bookinfos). |
| R-9 | `tools/weiqi101/discover.py` | Book/tag/category discovery. `discovery-catalog.json` contains 201 books, 83,119 puzzles across books, 181,165 total active puzzles. |

**Key insight**: The entire downstream pipeline (extract → validate → convert → save → checkpoint) is **complete and working**. The only bottleneck is HTTP fetching. Any approach that delivers raw HTML (or just the `qqdata` JSON) can plug directly into the existing `extractor.py` → `converter.py` → `storage.py` chain.

### 2.2 Current Download Progress

| R-ID | Metric | Value |
|------|--------|-------|
| R-10 | Main dir SGFs | 6 files |
| R-11 | book-6 SGFs | 29 files |
| R-12 | book-28507 SGFs | 22 files |
| R-13 | **Total downloaded** | **~57 SGFs** out of 83,119 book puzzles (0.07%) |
| R-14 | Discovery catalog | Complete (201 books cataloged, 7 categories with pagination data) |

### 2.3 Data Loading Mechanism

| R-ID | Finding |
|------|---------|
| R-15 | `qqdata` is embedded **inline in HTML** as `var qqdata = {...}` — it is NOT loaded via XHR/fetch. This means any approach must load the full page HTML. |
| R-16 | The `qqdata` object is also available as `window.qqdata` in the browser's JavaScript context after page load — a global variable accessible from userscripts, extensions, or devtools. |
| R-17 | Book pages (`/book{id}/{chapter_id}/?page=N`) contain puzzle ID lists in HTML, not in `qqdata`. Puzzle IDs are in `div.timus.card-wrapper span span` elements (per 101books project). |

---

## 3. External Evidence

### 3.1 Browser Automation Frameworks (LLM-Driven)

| R-ID | Framework | Stars | Local LLM Support | Windows | License | Key Limitation |
|------|-----------|-------|-------------------|---------|---------|----------------|
| X-1 | **browser-use** | 87.6K | ✅ Ollama (`ChatOllama`), LiteLLM, any OpenAI-compatible endpoint | ✅ (Playwright) | MIT | Requires LLM for every action decision. Slow for repetitive tasks. VRAM needed for quality local models. |
| X-2 | **Anthropic computer-use** | ~4K | ❌ Requires Anthropic API (cloud) | ❌ Linux Docker only | Apache 2.0 | Cloud API dependency. Linux-only container. Not suitable for constraint set. |
| X-3 | **LaVague** | 6.3K | Partial (via custom config) | ✅ (Selenium/Playwright) | Apache 2.0 | Last updated 2 years ago. Defaults to OpenAI. Limited maintenance. |
| X-4 | **OpenAdapt** | 1.8K | Partial | ✅ | MIT | Focused on RPA recording/replay, not web scraping. Overkill for this use case. |
| X-5 | **Skyvern** | 12K | ❌ Cloud API required | ✅ | AGPL-3.0 | Cloud-dependent. AGPL license concern. |

### 3.2 Non-LLM Automation Approaches

| R-ID | Approach | Complexity | Detection Risk | Throughput Potential | Windows |
|------|----------|-----------|----------------|---------------------|---------|
| X-6 | **Tampermonkey userscript** (passive capture + auto-nav) | Low | **Very Low** (runs inside real browser session) | 10-20 pages/min with human-like delays | ✅ |
| X-7 | **Chrome extension** (background service worker + content script) | Medium | **Very Low** (same as real browser) | 10-20 pages/min | ✅ |
| X-8 | **AutoHotKey macro** + JS console | Medium | Low (real mouse/keyboard) | 5-10 pages/min | ✅ |
| X-9 | **Playwright persistent context** (CDP attach to existing Chrome) | Medium | Medium (Playwright adds detectable markers) | 15-30 pages/min, but risks detection at scale |  ✅ |
| X-10 | **Selenium undetected-chromedriver** | Medium | Medium-High (cat-and-mouse with detection) | 10-20 pages/min, brittle | ✅ |
| X-11 | **Human browse + passive background capture** | Very Low | **Effectively Zero** | 2-4 pages/min (human speed) | ✅ |

### 3.3 Throughput Estimates at Scale

| R-ID | Approach | Pages/Hour | Hours for 40K | Hours for 83K | Notes |
|------|----------|-----------|---------------|---------------|-------|
| T-1 | Manual browsing only | 120-240 | 167-333 hrs | 346-692 hrs | Not viable |
| T-2 | Tampermonkey auto-nav (5s delay) | 720 | 56 hrs | 115 hrs | ~7-14 days at 8hr/day sessions |
| T-3 | Tampermonkey auto-nav (3s delay) | 1,200 | 33 hrs | 69 hrs | ~4-9 days at 8hr/day. Aggressive. |
| T-4 | Chrome extension auto-nav (5s delay) | 720 | 56 hrs | 115 hrs | Same as T-2, more robust storage |
| T-5 | browser-use + local LLM (10s/action) | 360 | 111 hrs | 231 hrs | LLM decision overhead per page |
| T-6 | AHK macro (8s cycle) | 450 | 89 hrs | 185 hrs | Click-wait-extract cycle |
| T-7 | Hybrid: human nav + background capture | 120-240 | 167-333 hrs | 346-692 hrs | Same as T-1, just with auto-capture |

### 3.4 Local LLM Requirements for Browser Automation

| R-ID | Model | VRAM | Quality for Web Nav | Speed (tok/s local) | Viable? |
|------|-------|------|--------------------|--------------------|---------|
| L-1 | Llama 3.1 8B (Q4) | 6GB | Poor — struggles with complex DOM understanding | 30-60 tok/s on RTX 3060+ | Marginal |
| L-2 | Qwen2-VL-7B (Q4) | 8GB | Moderate — vision model, understands screenshots | 20-40 tok/s | Better, but slow per decision |
| L-3 | Llama 3.1 70B (Q4) | 40GB+ | Good | 5-15 tok/s | Requires high-end hardware |
| L-4 | Qwen2.5-72B (Q4) | 40GB+ | Good | 5-15 tok/s | Requires high-end hardware |
| L-5 | **Not needed** | 0 | N/A | N/A | For repetitive page-click-extract, deterministic scripts outperform LLMs |

---

## 4. Candidate Adaptations for Yen-Go

### Approach A: Tampermonkey Userscript (⭐ RECOMMENDED PRIMARY)

**Concept**: Install Tampermonkey in your normal Chrome/Firefox. The userscript runs on every `101weiqi.com/q/*` page, captures `window.qqdata`, saves it to IndexedDB, and auto-navigates to the next puzzle ID.

| ID | Aspect | Detail |
|----|--------|--------|
| A-1 | Detection risk | **Near zero** — script runs inside your real, logged-in browser session with your real cookies, IP, and browsing fingerprint. No programmatic browser markers. |
| A-2 | Implementation | ~100-150 lines of JavaScript. `@match https://www.101weiqi.com/q/*`. On page load: read `window.qqdata`, store in IndexedDB or post to `localhost:PORT`. Wait random 3-8s. Navigate to `/q/{next_id}/`. |
| A-3 | Storage | Option 1: IndexedDB (browser-local, export as JSON later). Option 2: POST to a tiny local Python server that feeds into existing `storage.py`. |
| A-4 | Checkpoint/Resume | Store `last_processed_id` in `localStorage`. On script start, read it and skip to resume point. |
| A-5 | Integration | The local Python receiver calls `extractor.py` (or directly `models.py` `PuzzleData.from_qqdata()`) → `converter.py` → `storage.py`. All existing infra reused. |
| A-6 | Book navigation | For book pages: separate `@match` for `/book*` URLs. Extract puzzle IDs from page HTML, store them, then iterate through puzzle pages. |
| A-7 | Throughput | 720-1,200 pages/hour (3-5s delay). **40K puzzles in 33-56 hours** (~4-7 days at 8hr/day). |
| A-8 | Failure handling | On CAPTCHA detection (no `qqdata` on page), pause and alert user. User solves CAPTCHA manually, script resumes. |
| A-9 | Effort | **2-4 hours** to build userscript + local receiver. |

### Approach B: Chrome Extension (RECOMMENDED FALLBACK)

**Concept**: Chrome extension with content script that captures `qqdata` and background service worker that manages queue + navigation.

| ID | Aspect | Detail |
|----|--------|--------|
| B-1 | Detection risk | **Near zero** — same as Tampermonkey, runs in real browser. |
| B-2 | Implementation | ~300-400 lines across manifest.json, content.js, background.js, popup.html. More structured than userscript. |
| B-3 | Storage | `chrome.storage.local` (up to 10MB) or IndexedDB. Export button in popup UI. Better than Tampermonkey for large datasets. |
| B-4 | Advantages over A | Better storage management, popup UI for progress monitoring, can run in background tab, `chrome.storage.local` persists across browser restarts. |
| B-5 | Disadvantages vs A | More code, requires loading unpacked extension, slightly more setup. |
| B-6 | Throughput | Same as Approach A: 720-1,200 pages/hour. |
| B-7 | Effort | **4-8 hours** to build. |

### Approach C: AutoHotKey Macro + Console Extraction

**Concept**: AHK script that: opens puzzle URL → waits for load → sends F12 to open devtools → types `JSON.stringify(qqdata)` in console → copies output → saves to file → navigates to next.

| ID | Aspect | Detail |
|----|--------|--------|
| C-1 | Detection risk | **Low** — real mouse/keyboard events. But devtools usage is detectable in theory. |
| C-2 | Implementation | ~200 lines AHK. Fragile: depends on pixel positions, timing, window focus. |
| C-3 | Throughput | 450 pages/hour (8s cycle). **40K in ~89 hours**. |
| C-4 | Failure modes | Window focus loss, devtools position changes, resolution dependency, timing races. |
| C-5 | Effort | **4-6 hours** to build and debug. |
| C-6 | Verdict | **Not recommended** — too fragile for a 40K page run. Tampermonkey does the same thing more reliably. |

### Approach D: browser-use + Local Ollama

**Concept**: Use `browser-use` Python framework with a local Ollama model to navigate pages and extract data.

| ID | Aspect | Detail |
|----|--------|--------|
| D-1 | Detection risk | **Medium** — Playwright under the hood adds detectable markers (`navigator.webdriver`, automation flags). browser-use cloud offers stealth mode, but that's paid. |
| D-2 | LLM overhead | Each page navigation requires LLM inference (~2-5s per decision with 8B model). For a simple "click next, read qqdata" workflow, this is pure overhead. |
| D-3 | VRAM requirement | 6-8GB minimum for a usable 7B-8B model. Quality degrades significantly below 7B for DOM understanding. |
| D-4 | Throughput | ~360 pages/hour. **40K in ~111 hours**. Half the speed of Tampermonkey for more complexity. |
| D-5 | Failure modes | LLM hallucinations (clicking wrong elements), OOM on long sessions, Playwright detection, model quality issues with Chinese page content. |
| D-6 | When it makes sense | Complex multi-step workflows where navigation varies per page. Not this case — our navigation is completely deterministic (sequential puzzle IDs). |
| D-7 | Effort | **8-16 hours** (setup Ollama, write agent script, debug LLM failures). |
| D-8 | Verdict | **Overkill and counterproductive** for this use case. An LLM adds latency and unreliability to what is a trivial deterministic navigation pattern. |

### Approach E: Playwright CDP Attach to Real Browser

**Concept**: Launch Chrome normally (manually), then attach Playwright via Chrome DevTools Protocol (CDP) to control it programmatically while keeping the real browser session.

| ID | Aspect | Detail |
|----|--------|--------|
| E-1 | Detection risk | **Medium** — the browser itself is real, but CDP attachment can be detected by advanced fingerprinting (though Tencent CAPTCHA may not check for it). |
| E-2 | Implementation | Launch Chrome with `--remote-debugging-port=9222`. Python script attaches via `playwright.chromium.connect_over_cdp()`. Navigate pages, extract `qqdata` via `page.evaluate("window.qqdata")`. |
| E-3 | Advantage | Direct integration with existing Python tooling. Can call `extractor.py`/`converter.py`/`storage.py` inline. |
| E-4 | Risk | If the site fingerprints CDP connections, this gets blocked same as automated requests. |
| E-5 | Throughput | 900-1,800 pages/hour if not detected. Drops to zero if detected. |
| E-6 | Effort | **4-6 hours**. |
| E-7 | Verdict | **Good secondary option** — try it first as it's closest to existing Python workflow. Fall back to Tampermonkey if CDP is detected. |

### Approach F: Hybrid Human Browse + Passive Capture

**Concept**: Human navigates manually; a Tampermonkey script passively captures every `qqdata` encountered without auto-navigation.

| ID | Aspect | Detail |
|----|--------|--------|
| F-1 | Detection risk | **Effectively zero** — truly human browsing. |
| F-2 | Throughput | 2-4 pages/min (human click speed). **40K in 167-333 hours**. |
| F-3 | Verdict | Only viable as seed data / initial testing. Not scalable to 40K+ pages. Could work for the most valuable ~1,000 puzzles from specific books. |

---

## 5. Risks, License/Compliance, and Rejection Reasons

### Risks

| R-ID | Risk | Probability | Impact | Mitigation |
|------|------|-------------|--------|-----------|
| RK-1 | Tencent CAPTCHA adapts to detect auto-navigation patterns even within real browser | Low | High — blocks all automated approaches (A, B, C, E) | Vary delays with wide jitter (3-15s), add random scroll/hover events, split into small sessions |
| RK-2 | 101weiqi changes page structure / removes inline `qqdata` | Very Low | High — breaks extraction | Monitor first 100 pages; `qqdata` is core to their puzzle player, unlikely to change |
| RK-3 | IP ban after sustained high-volume access | Medium | Medium — temporary lockout | Distribute across multiple sessions/days, keep under 1 req/3s average |
| RK-4 | Browser storage overflow (IndexedDB limits) | Low | Low — data loss if not exported | Export every 1,000 puzzles to filesystem via local server |
| RK-5 | Authentication wall for some puzzles | Medium | Low — skip and log | Some puzzles may require login; the checkpoint system already handles skips |

### License / Compliance

| R-ID | Item | Status |
|------|------|--------|
| LC-1 | browser-use | MIT — permissive, no concern |
| LC-2 | Tampermonkey | Proprietary (free for personal use). Violentmonkey is MIT alternative. |
| LC-3 | AutoHotKey | GPL v2 — fine for local tooling, not distributed |
| LC-4 | 101weiqi.com ToS | Puzzles are publicly viewable. No robots.txt blocking `/q/` paths (verified in prior research R-1). Standard web scraping ethics apply — we're scaling manual browsing, not bypassing access controls. |

### Rejection Reasons

| R-ID | Approach | Reason for Rejection / Demotion |
|------|----------|---------------------------------|
| RJ-1 | Anthropic Computer Use (X-2) | Requires cloud API ($$$), Linux Docker only. Violates "local-only, Windows" constraint. |
| RJ-2 | LaVague (X-3) | Abandoned (2 years inactive), defaults to OpenAI API. |
| RJ-3 | Skyvern (X-5) | AGPL license, cloud-dependent. |
| RJ-4 | browser-use + LLM (D) | Adds latency, unreliability, and VRAM cost for zero benefit — navigation is deterministic. |
| RJ-5 | AHK macro (C) | Too fragile for 40K-page sustained run. Tampermonkey solves same problem more robustly. |
| RJ-6 | Pure manual (F) | Not scalable beyond ~1K puzzles. |
| RJ-7 | CAPTCHA solving services | Out of scope (cloud cost, ethical boundary). |
| RJ-8 | Proxy rotation | Out of scope (cloud cost, complexity). |

---

## 6. Planner Recommendations

### Recommendation 1 (PRIMARY): Tampermonkey Userscript + Local Python Receiver

Build a two-component system:
1. **Tampermonkey userscript** (`101weiqi-capture.user.js`): Runs on `101weiqi.com/q/*`. Reads `window.qqdata`, POSTs JSON to `localhost:8101`. Auto-navigates to next puzzle ID with 3-8s randomized delay. Pause/resume via GM_setValue. CAPTCHA detection pauses and alerts user.
2. **Local Python server** (`tools/weiqi101/receiver.py`): Tiny Flask/FastAPI endpoint on port 8101. Receives `qqdata` JSON, calls existing `PuzzleData.from_qqdata()` → `converter.py` → `storage.py`. Updates checkpoint. Already-downloaded IDs skipped via `sgf-index.txt` dedup.

**Why**: Lowest detection risk, highest throughput (720-1200/hr), reuses 90% of existing code, 2-4 hours to build, simplest architecture.

### Recommendation 2 (PARALLEL PROBE): Playwright CDP Attach

Before building the userscript, spend 30 minutes testing whether Playwright CDP attach to a real Chrome session works without triggering CAPTCHA:
1. Launch Chrome with `--remote-debugging-port=9222`
2. Log in to 101weiqi manually
3. Attach Playwright, navigate to 10 puzzle pages with 5s delays
4. If no CAPTCHA: this becomes the primary approach (simpler Python-only tooling, direct pipeline integration)
5. If CAPTCHA triggers: fall back to Recommendation 1

### Recommendation 3: Book Discovery First

Before bulk downloading, complete the book puzzle-ID discovery phase:
1. Iterate through `discovery-catalog.json`'s 201 books
2. For each book, scrape chapter pages to get ordered puzzle IDs (book pages are lighter — less CAPTCHA pressure since they don't load `qqdata`)
3. Store as `book-ids.jsonl` (already partially exists at `external-sources/101weiqi/book-ids.jsonl`)
4. This gives precise download targets with collection/chapter metadata for `YL[]` assignment

### Recommendation 4: Session Discipline

Whatever approach is used, enforce these operational parameters:
- **Max 8-hour sessions** with 30-min cooldown between sessions
- **Randomized delays**: 3-8s between pages within a session, with occasional 30-60s "reading" pauses every 50-100 pages
- **Progress export**: Every 500 puzzles, export a snapshot from IndexedDB/receiver to `external-sources/101weiqi/books/book-N/`
- **Multiple concurrent books**: Run 2-3 browser tabs on different books to distribute access patterns

---

## 7. Architecture Integration Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Real Browser (Chrome/Firefox)                          │
│  ┌────────────────────────────────────────┐             │
│  │  Tampermonkey Userscript               │             │
│  │  @match 101weiqi.com/q/*              │             │
│  │                                        │             │
│  │  1. Read window.qqdata                 │             │
│  │  2. POST to localhost:8101             │             │
│  │  3. Wait 3-8s (randomized)            │             │
│  │  4. Navigate to /q/{next_id}/         │             │
│  │  5. If CAPTCHA → pause + alert        │             │
│  └──────────────┬─────────────────────────┘             │
│                 │ HTTP POST (qqdata JSON)                │
└─────────────────┼───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Local Python Receiver (localhost:8101)                  │
│                                                         │
│  POST /puzzle  ──►  PuzzleData.from_qqdata()           │
│                      │                                  │
│                      ▼                                  │
│                 validate_puzzle()                        │
│                      │                                  │
│                      ▼                                  │
│                 converter.py (qqdata → SGF)             │
│                      │                                  │
│                      ▼                                  │
│                 storage.py (batch dirs, index)          │
│                      │                                  │
│                      ▼                                  │
│                 checkpoint.py (resume state)            │
│                                                         │
│  Output: external-sources/101weiqi/books/book-N/sgf/   │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Answer to Specific Questions

| Q-ID | Question | Answer |
|------|----------|--------|
| Q1 | Which local computer-use frameworks exist? | browser-use (87K⭐, MIT, Ollama support), LaVague (6K⭐, stale), Anthropic CU (cloud-only), Skyvern (cloud-only). See X-1 through X-5. |
| Q2 | Which local LLMs can drive them? | Llama 3.1 8B (6GB VRAM, marginal quality), Qwen2-VL-7B (8GB, moderate). See L-1 through L-4. **But LLMs are unnecessary for this deterministic task.** |
| Q3 | Realistic throughput? | Tampermonkey: 720-1200/hr. browser-use+LLM: 360/hr. AHK: 450/hr. See T-1 through T-7. |
| Q4 | Failure modes and recovery? | CAPTCHA detection (pause+alert), IP ban (session cool-off), page structure change (monitor first 100), storage overflow (periodic export). See RK-1 through RK-5. |
| Q5 | Can a simpler non-LLM approach work? | **Yes, absolutely.** Tampermonkey userscript is simpler, faster, more reliable, and less detectable than any LLM-driven approach. The navigation pattern is 100% deterministic — LLMs add cost with zero benefit. |
| Q6 | Hybrid approach viable for 40K pages? | Pure manual (F) is not viable (167-333 hrs). But human-initiated sessions + auto-navigation (A) is viable: 33-56 hours over 4-7 days. Human only needs to start the session, solve occasional CAPTCHAs, and monitor. |
| Q7 | Is qqdata loaded via XHR? | No — inline `var qqdata = {...}` in HTML (R-15). Also available as `window.qqdata` global (R-16). Not interceptable via XHR hooks alone. |

---

## 9. Confidence and Risk Assessment

| Metric | Value | Rationale |
|--------|-------|-----------|
| **Post-research confidence** | **85/100** | Tampermonkey approach is well-understood, low-risk, and proven to work in similar scenarios. Uncertainty is around Tencent CAPTCHA sensitivity thresholds at sustained volume. |
| **Post-research risk level** | **Low-Medium** | Primary risk is CAPTCHA triggering more aggressively at scale. Mitigated by session discipline and the CDP probe fallback. |
