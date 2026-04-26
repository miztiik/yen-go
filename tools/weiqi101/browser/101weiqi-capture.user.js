// ==UserScript==
// @name         101weiqi Puzzle Capture for YenGo
// @namespace    https://github.com/yengo
// @version      5.38.0
// @description  Auto-captures puzzle data from 101weiqi.com and sends to local YenGo receiver. Start server, browse any puzzle page, it just works.
// @match        *://www.101weiqi.com/q/*
// @match        *://www.101weiqi.com/chessmanual/*
// @match        *://www.101weiqi.com/qday/*
// @match        *://www.101weiqi.com/book/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        GM_xmlhttpRequest
// @grant        GM_notification
// @grant        unsafeWindow
// @connect      127.0.0.1
// @connect      localhost
// @run-at       document-idle
// ==/UserScript==

(function () {
  "use strict";

  // Idempotent install guard. Tampermonkey re-evaluates the IIFE on
  // every page load, but it can ALSO re-evaluate within the same
  // document (e.g. SPA navigations that flip document.readyState).
  // Without this guard we accumulate setInterval timers and duplicate
  // status bars. We mark a flag on unsafeWindow (survives the sandbox
  // boundary) so the second invocation early-exits.
  try {
    if (unsafeWindow.__yengo_installed__) {
      console.log("[YenGo] script already installed in this document; skipping re-init");
      return;
    }
    unsafeWindow.__yengo_installed__ = true;
  } catch (e) {
    // unsafeWindow unavailable (older Tampermonkey?) — fall through
    // and accept potential duplication rather than not run at all.
    console.warn("[YenGo] install-guard skipped:", e && e.message);
  }

  // ╔══════════════════════════════════════════════════════════════════╗
  // ║                    TABLE OF CONTENTS                             ║
  // ╠══════════════════════════════════════════════════════════════════╣
  // ║  1. CORE INFRA       — config, state, logging, content decoding  ║
  // ║  2. UI               — status bar, overlays, picker              ║
  // ║  3. INFRA HELPERS    — HTTP, delays, wake lock, tab ownership    ║
  // ║  4. QDAY SWEEP       — daily-puzzle sweep mode                   ║
  // ║  5. BOOK DISCOVERY   — chapter scrape + manifest build           ║
  // ║  6. BOOK CAPTURE     — chapter-mode capture loop                ║
  // ║  7. NAVIGATION       — goNext, triggerSiteNext, autoStart        ║
  // ║  8. CAPTURE LOOP     — capture(), navigation watcher             ║
  // ║  9. MENU COMMANDS    — Tampermonkey GM_registerMenuCommand entries║
  // ╚══════════════════════════════════════════════════════════════════╝
  //
  // Folding: VS Code recognises //#region / //#endregion pairs.
  // Use "Fold All Regions" (Ctrl+K Ctrl+8) for a quick map.

  //#region 1. CORE INFRA
  // -- Config -----------------------------------------------------
  const RECEIVER = "http://127.0.0.1:8101";
  const DEFAULT_BASE_DELAY_MS = 4500;
  const MIN_BASE_DELAY_MS = 1500;
  const MAX_BASE_DELAY_MS = 15000;
  const DELAY_STEP_MS = 500;
  const JITTER_RATIO = 0.45; // +/- 45% around base delay
  const BURST_COOLDOWN_EVERY = 12;
  const BURST_COOLDOWN_MIN_MS = 5000;
  const BURST_COOLDOWN_MAX_MS = 11000;
  const ERROR_BACKOFF_STEP_MS = 7000;
  const ERROR_BACKOFF_MAX_MS = 9000;
  // Per-endpoint HTTP timeouts. Manifest scans can be slow on big books
  // (hundreds of files); /capture should fail fast so the loop can
  // retry. Default applies to anything not in HTTP_TIMEOUT_MAP.
  const HTTP_TIMEOUT_MS = 15000;
  const HTTP_TIMEOUT_MAP = Object.freeze({
    "/book/manifest": 60000,
    "/book/discovery": 60000,
    "/capture": 15000,
    "/queue": 30000,
  });
  // HTTP retry policy for transient errors (network down, slow disk).
  // Only the network/timeout class retries — receiver-level errors
  // (4xx/5xx with parsed JSON) bubble up immediately so capture()
  // can decide based on the response payload.
  const HTTP_RETRY_MAX = 3;
  const HTTP_RETRY_BASE_MS = 800;
  const QQDATA_POLL_MS = 1000;
  const QQDATA_MAX_WAIT = 10000;
  const DAILY_MIN_NUM = 1;
  const DAILY_MAX_NUM = 8;

  // -- Frozen enums (replace magic strings; opt-in adoption) -------
  // These exist so future code paths can reference Status.Ok instead
  // of the literal "ok". Existing equality checks were left as-is to
  // keep this refactor zero-risk; new code should use the enums.
  const Status = Object.freeze({ Ok: "ok", Skipped: "skipped", Done: "done", Error: "error" });
  const CaptureMode = Object.freeze({ Chapter: "chapter", Book: "book", Qday: "qday" });
  const SortOrder = Object.freeze({ Asc: "asc", Desc: "desc" });
  const DateDirection = Object.freeze({ Forward: "forward", Backward: "backward" });

  // -- Anti-blocking: human-like behavior -------------------------
  // NOTE: SESSION_BREAK_MIN/MAX_MS are short (1.2-1.8s) despite the
  // "long break" comment in older code. The actual long break is the
  // chapter-mode session break below. Naming kept for compat.
  const THINK_TIME_MIN_MS = 300; // Simulated "reading" time
  const THINK_TIME_MAX_MS = 8000;
  const SESSION_BREAK_EVERY = 35; // Trigger frequency (puzzles)
  const SESSION_BREAK_MIN_MS = 1200;
  const SESSION_BREAK_MAX_MS = 1800;
  const SCROLL_NOISE_CHANCE = 0.3; // 30% chance of random scroll
  const GOTOPIC_TIMEOUT_MS = 12000; // Max wait for AJAX puzzle change

  // Chapter-mode pacing: single consistent interval per puzzle.
  // Final wait = max(3s, target - elapsed) — see goNext() chapter branch.
  const CHAPTER_INTERVAL_MIN_MS = 1000;
  const CHAPTER_INTERVAL_MAX_MS = 15000;
  const CHAPTER_SESSION_BREAK_EVERY = 40;
  const CHAPTER_SESSION_BREAK_MIN_MS = 1800;
  const CHAPTER_SESSION_BREAK_MAX_MS = 4200;

  // Timestamp tracking for interval-based pacing
  let captureStartedAt = 0;

  // Recovery state for the *current* puzzle. Set when a readiness-gate
  // retry succeeds; consumed by the next /capture POST so the receiver
  // can flag the [SAVED] line with `recovered=true`. Cleared on every
  // capture entry to ensure it's a per-puzzle signal.
  let _pendingRecoveryAttempts = 0;

  // -- State ------------------------------------------------------
  const KEY_RUNNING = "yengo_running";
  const KEY_STATS = "yengo_stats";
  const KEY_QDAY_PLAN = "yengo_qday_plan";
  const KEY_BASE_DELAY = "yengo_base_delay";
  const KEY_WAKE_LOCK = "yengo_wake_lock";
  const KEY_OWNER_TAB = "yengo_owner_tab";
  const KEY_OWNER_HEARTBEAT = "yengo_owner_hb";
  const KEY_BOOK_DISCOVERY = "yengo_book_discovery";
  const KEY_BOOK_PLAN = "yengo_book_plan";
  // v5.37.0: explicit user-pause flag. Set by [Control] Pause / [Control] Stop
  // (functionally equivalent — both preserve plan, halt loop, and require a
  // manual [Control] Resume to continue). Also gates auto-resume across
  // tabs: any tab that boots while this flag is true will display
  // "Paused" and refuse to auto-claim ownership / restart capture, even
  // if a bookPlan / discovery / qday plan is still active. Cleared by
  // startRunning() (which is now only called from explicit user actions).
  const KEY_USER_PAUSED = "yengo_user_paused";

  const HEARTBEAT_INTERVAL_MS = 5000; // 10s
  const OWNER_STALE_MS = 30000; // 30s before declaring owner dead

  // Stable tab ID that survives same-tab navigations (location.href).
  // sessionStorage can be unreliable in Tampermonkey's sandbox across
  // navigations, so we also persist the ID in window.name (which is
  // guaranteed per-spec to survive same-tab navigations).
  // Uses crypto.randomUUID() (8 hex chars from it) for ~32-bit entropy
  // — the previous Math.random().toString(36).slice(2,8) gave only
  // ~31 bits and could collide once a user opened ~50 capture tabs.
  const TAB_ID = (() => {
    // 1. Try sessionStorage first (fastest, usually works)
    let id = sessionStorage.getItem("yengo_tab_id");
    if (id) return id;
    // 2. Fallback: window.name persists across navigations per spec
    const m = (window.name || "").match(/yengo_tab=([a-z0-9]+)/);
    if (m) {
      id = m[1];
      try { sessionStorage.setItem("yengo_tab_id", id); } catch (e) {
        console.warn("[YenGo] sessionStorage write failed:", e.message);
      }
      return id;
    }
    // 3. New tab — generate fresh ID using crypto if available.
    try {
      if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        id = crypto.randomUUID().replace(/-/g, "").slice(0, 8);
      } else {
        id = Math.random().toString(36).slice(2, 10);
      }
    } catch (_) {
      id = Math.random().toString(36).slice(2, 10);
    }
    try { sessionStorage.setItem("yengo_tab_id", id); } catch (e) {
      console.warn("[YenGo] sessionStorage write failed:", e.message);
    }
    try { window.name = ((window.name || "") + " yengo_tab=" + id).trim(); } catch (e) {
      console.warn("[YenGo] window.name write failed:", e.message);
    }
    return id;
  })();

  // -- Safe integer parser ----------------------------------------
  // Replaces bare parseInt(x, 10) at every URL/DOM-derived ID call
  // site. Returns null for NaN/non-finite input so downstream `if (id)`
  // checks behave correctly (parseInt returns NaN which is truthy in
  // some comparisons but fails Number.isFinite).
  function parseId(v) {
    if (v == null) return null;
    const n = Number.parseInt(v, 10);
    return Number.isFinite(n) ? n : null;
  }

  const DEFAULT_STATS = Object.freeze({
    ok: 0, skipped: 0, error: 0, captcha: 0, notfound: 0,
  });

  let running = GM_getValue(KEY_RUNNING, false);
  let qdayPlan = GM_getValue(KEY_QDAY_PLAN, null);
  let bookDiscovery = GM_getValue(KEY_BOOK_DISCOVERY, null);
  let bookPlan = GM_getValue(KEY_BOOK_PLAN, null);
  let issueStreak = 0;

  // -- Abort plumbing (v5.32.0) ------------------------------------
  // A single AbortController per session: rotated on startRunning()
  // and again on stopRunning() (after abort) so post-stop cleanup
  // calls (e.g. http("GET", "/queue/stop")) get a fresh, non-aborted
  // signal. In-flight HTTP, waitMs() sleeps, and polling helpers all
  // observe currentSignal() and bail out within ~50ms of abort().
  let _abortCtrl = new AbortController();
  function currentSignal() { return _abortCtrl.signal; }
  function rotateAbortCtrl(reason) {
    try { _abortCtrl.abort(reason || "rotated"); } catch (_) {}
    _abortCtrl = new AbortController();
  }
  // Lightweight AbortError factory — keeps name === 'AbortError' so
  // catch blocks can recognise it the same way as fetch() does.
  function makeAbortError(reason) {
    const e = new Error("Aborted: " + (reason || "user stopped"));
    e.name = "AbortError";
    e.kind = "abort";
    return e;
  }
  let stats = { ...DEFAULT_STATS, ...GM_getValue(KEY_STATS, {}), session_start: new Date().toISOString() };
  let wakeLockEnabled = GM_getValue(KEY_WAKE_LOCK, false);
  let wakeLockSentinel = null;
  // Drift detection: how many consecutive captures landed on a *different*
  // book than the active capture target. 3-in-a-row triggers an ERR log
  // (capture continues — see reconcileAttribution / drift_from_active).
  let driftBookStreak = 0;

  // -- Logging ----------------------------------------------------
  // Phase icons for console clarity:
  //   ⏳ WAIT  — throttle delay before next navigation
  //   🔄 LOAD  — page loaded, waiting for puzzle data
  //   📥 GRAB  — cloning/decoding puzzle data
  //   📤 SEND  — posting to backend
  //   ✅ DONE  — saved successfully
  //   ⏭️ NEXT  — navigating to next puzzle
  //   ⏩ SKIP  — duplicate, skipped
  //   ⚠️ WARN  — non-fatal issue
  //   ❌ ERR   — fatal error, sweep may stop
  //   🏁 END   — sweep/queue complete

  const _PHASE_ICONS = Object.freeze({
    WAIT: "\u23F3", LOAD: "\uD83D\uDD04", GRAB: "\uD83D\uDCE5",
    SEND: "\uD83D\uDCE4", DONE: "\u2705", NEXT: "\u23ED\uFE0F",
    SKIP: "\u23E9", WARN: "\u26A0\uFE0F", ERR: "\u274C",
    END: "\uD83C\uDFC1",
  });

  // Log to the sandbox console (does NOT touch unsafeWindow, so no
  // focus-stealing).  Phase logs are mirrored to the status bar's
  // built-in log trail instead of devtools.
  const _LOG_TRAIL_MAX = 50;
  const _logTrail = [];

  function log(lvl, msg, data) {
    const entry = `${new Date().toISOString()} [YenGo] [${lvl}] ${msg}`;
    console[lvl === "ERROR" ? "error" : lvl === "WARN" ? "warn" : "log"](
      entry, data !== undefined ? data : ""
    );
    // Also push WARN/ERROR into the in-page log trail so the status
    // bar's expandable panel surfaces them — previously only plog()
    // entries appeared there, which hid HTTP/wake-lock failures.
    if (lvl === "WARN" || lvl === "ERROR") {
      try {
        const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
        const icon = lvl === "ERROR" ? "\u274C" : "\u26A0\uFE0F";
        _logTrail.push(`${icon} ${ts} [${lvl}] ${msg}`);
        if (_logTrail.length > _LOG_TRAIL_MAX) _logTrail.shift();
        if (typeof _renderLogTrail === "function") _renderLogTrail();
      } catch (e) {
        // _renderLogTrail not yet initialized during early boot — fine.
      }
    }
  }

  // Phase-aware structured log for the capture/navigate lifecycle.
  // Kept in-memory only — no GM_setValue, no unsafeWindow, no focus
  // side-effects.  Trail resets on navigation but is rendered in the
  // status bar's expandable log panel for the current page.
  function plog(phase, msg) {
    const icon = _PHASE_ICONS[phase] || "\u2139\uFE0F";
    const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
    const line = `${icon} ${ts} [${phase}] ${msg}`;
    console.log(line);
    _logTrail.push(line);
    if (_logTrail.length > _LOG_TRAIL_MAX) _logTrail.shift();
    _renderLogTrail();
  }

  // -- Content field decoder --------------------------------------
  // Mirrors the site's production JS (ca3b6e99...js):
  //   test123(qqdata) -> test202(encoded, key)
  //
  // Decode chain:
  //   1. Derive XOR key from qqdata.ru:
  //        base = atob("MTAx") = "101"
  //        suffix = ru + 1  (2 for ru=1, 3 for ru=2)
  //        key = "101" + suffix + suffix + suffix  ("101222" or "101333")
  //   2. base64-decode the encoded string
  //   3. XOR each byte with the key (cycling)
  //   4. JSON.parse the result -> [[black_coords], [white_coords]]
  //
  // Fields decoded by test123: content, ok_answers, change_answers,
  //   fail_answers, clone_pos, clone_prepos
  // Fields NOT encoded: andata (solution tree), prepos (partial stones)

  function xorDecode(encoded, key) {
    const raw = atob(encoded);
    let result = "";
    for (let i = 0, k = 0; i < raw.length; i++) {
      result += String.fromCharCode(raw.charCodeAt(i) ^ key.charCodeAt(k));
      k = (k + 1) % key.length;
    }
    return result;
  }

  function deriveXorKey(ru) {
    // "101" + str(ru+1) repeated 3 times
    const suffix = String(ru + 1);
    return "101" + suffix + suffix + suffix;
  }

  function decodeContentField(qq) {
    // If the site's JS (test123) already ran, content is an array
    if (Array.isArray(qq.content) && qq.content.length >= 2) {
      return qq.content;
    }
    // Otherwise decode the encoded string ourselves
    if (typeof qq.content === "string" && qq.content.length > 10) {
      const ru = qq.ru || 1;
      const key = deriveXorKey(ru);
      try {
        const decoded = JSON.parse(xorDecode(qq.content, key));
        if (Array.isArray(decoded) && decoded.length >= 2) {
          return decoded;
        }
      } catch (e) {
        log("WARN", `Content decode failed (ru=${ru}): ${e.message}`);
      }
    }
    return null;
  }

  // Decode all fields that test123 encodes.  Works on a dict in-place.
  // Skips fields already decoded (non-string) or absent.
  const ENCODED_FIELDS = Object.freeze([
    "content", "ok_answers", "change_answers",
    "fail_answers", "clone_pos", "clone_prepos",
  ]);

  function decodeEncodedFields(obj) {
    const ru = obj && obj.ru;
    if (ru !== 1 && ru !== 2) return obj;
    const key = deriveXorKey(ru);
    for (const field of ENCODED_FIELDS) {
      if (typeof obj[field] === "string" && obj[field].length > 10) {
        try {
          obj[field] = JSON.parse(xorDecode(obj[field], key));
        } catch (e) {
          // Leave as-is if decode fails — receiver may handle the raw
          // string. Log at DEBUG with field name for forensics.
          log("DEBUG", `decodeEncodedFields: ${field} decode failed (ru=${ru}): ${e.message}`);
        }
      }
    }
    return obj;
  }

  //#endregion 1. CORE INFRA

  //#region 2. UI
  // -- Status bar (create once, update dynamic spans) -------------
  let _barMsgEl = null;
  let _barDelayEl = null;
  let _barMinusBtn = null;
  let _barPlusBtn = null;
  let _barWakeLockEl = null;
  let _barStatsEl = null;
  let _barLogEl = null;
  let _barLogToggle = null;
  let _logExpanded = false;

  function createStatusBar() {
    const bar = document.createElement("div");
    bar.id = "yengo-status";
    bar.style.cssText =
      "position:fixed;bottom:0;left:0;right:0;z-index:999999;" +
      "background:#1a1a2ecc;color:#e0e0e0;padding:4px 12px;" +
      "font:12px/1.3 monospace;display:flex;gap:12px;align-items:center;flex-wrap:wrap;";

    // [YenGo] label
    const label = document.createElement("span");
    label.style.color = "#4fc3f7";
    label.textContent = "[YenGo]";
    bar.appendChild(label);

    // Message span (receives status color)
    _barMsgEl = document.createElement("span");
    bar.appendChild(_barMsgEl);

    // Delay controls group
    const delayGroup = document.createElement("span");
    delayGroup.style.cssText = "color:#aaa;display:flex;align-items:center;gap:4px;";

    const timerIcon = document.createTextNode("\u23F1 ");
    delayGroup.appendChild(timerIcon);

    _barDelayEl = document.createElement("span");
    _barDelayEl.style.minWidth = "38px";
    delayGroup.appendChild(_barDelayEl);

    const btnStyle =
      "background:#333;color:#e0e0e0;border:1px solid #555;padding:6px 12px;" +
      "cursor:pointer;font:13px monospace;border-radius:3px;line-height:1;";

    _barMinusBtn = document.createElement("button");
    _barMinusBtn.textContent = "\u2212";
    _barMinusBtn.style.cssText = btnStyle;
    _barMinusBtn.onclick = () => adjustDelay(-DELAY_STEP_MS);
    delayGroup.appendChild(_barMinusBtn);

    _barPlusBtn = document.createElement("button");
    _barPlusBtn.textContent = "+";
    _barPlusBtn.style.cssText = btnStyle;
    _barPlusBtn.onclick = () => adjustDelay(DELAY_STEP_MS);
    delayGroup.appendChild(_barPlusBtn);

    bar.appendChild(delayGroup);

    // Wake lock indicator
    _barWakeLockEl = document.createElement("span");
    bar.appendChild(_barWakeLockEl);

    // Stats (right-aligned)
    _barStatsEl = document.createElement("span");
    _barStatsEl.style.cssText = "margin-left:auto;color:#888;";
    bar.appendChild(_barStatsEl);

    // Log trail toggle button
    _barLogToggle = document.createElement("button");
    _barLogToggle.textContent = "\u25B2 Log";
    _barLogToggle.style.cssText =
      "background:#333;color:#aaa;border:1px solid #555;padding:2px 8px;" +
      "cursor:pointer;font:11px monospace;border-radius:3px;line-height:1;";
    _barLogToggle.onclick = () => {
      _logExpanded = !_logExpanded;
      _barLogEl.style.display = _logExpanded ? "block" : "none";
      _barLogToggle.textContent = _logExpanded ? "\u25BC Log" : "\u25B2 Log";
      if (_logExpanded) _barLogEl.scrollTop = _barLogEl.scrollHeight;
    };
    bar.appendChild(_barLogToggle);

    // Scrollable log trail (hidden by default, above the status bar)
    _barLogEl = document.createElement("pre");
    _barLogEl.style.cssText =
      "display:none;position:fixed;bottom:28px;left:0;right:0;z-index:999998;" +
      "background:#0d0d1acc;color:#c0c0c0;margin:0;padding:6px 12px;" +
      "font:11px/1.4 monospace;max-height:180px;overflow-y:auto;" +
      "border-top:1px solid #333;";
    document.body.appendChild(_barLogEl);

    document.body.appendChild(bar);
  }

  function _renderLogTrail() {
    if (!_barLogEl) return;
    _barLogEl.textContent = _logTrail.join("\n");
    if (_logExpanded) _barLogEl.scrollTop = _barLogEl.scrollHeight;
  }

  function adjustDelay(delta) {
    const newDelay = setBaseDelay(getBaseDelay() + delta);
    const atLimit = (delta < 0 && newDelay <= MIN_BASE_DELAY_MS) ||
                    (delta > 0 && newDelay >= MAX_BASE_DELAY_MS);
    if (_barDelayEl) {
      if (atLimit) {
        _barDelayEl.textContent = delta < 0 ? "MIN" : "MAX";
        _barDelayEl.style.color = "#f44336";
      } else {
        _barDelayEl.textContent = (newDelay / 1000).toFixed(1) + "s";
        _barDelayEl.style.color = "#4fc3f7";
      }
      setTimeout(() => {
        if (_barDelayEl) {
          _barDelayEl.textContent = (getBaseDelay() / 1000).toFixed(1) + "s";
          _barDelayEl.style.color = "";
        }
      }, 500);
    }
    updateDelayButtons();
    log("INFO", `Base delay: ${newDelay}ms`);
  }

  function updateDelayButtons() {
    const current = getBaseDelay();
    if (_barMinusBtn) {
      const atMin = current <= MIN_BASE_DELAY_MS;
      _barMinusBtn.disabled = atMin;
      _barMinusBtn.style.opacity = atMin ? "0.4" : "1";
      _barMinusBtn.style.cursor = atMin ? "not-allowed" : "pointer";
    }
    if (_barPlusBtn) {
      const atMax = current >= MAX_BASE_DELAY_MS;
      _barPlusBtn.disabled = atMax;
      _barPlusBtn.style.opacity = atMax ? "0.4" : "1";
      _barPlusBtn.style.cursor = atMax ? "not-allowed" : "pointer";
    }
  }

  function updateStatus(msg, color) {
    if (!_barMsgEl) createStatusBar();

    // Update message
    _barMsgEl.textContent = msg;
    _barMsgEl.style.color = color || "#e0e0e0";

    // Update delay display
    if (_barDelayEl) {
      _barDelayEl.textContent = (getBaseDelay() / 1000).toFixed(1) + "s";
      _barDelayEl.style.color = "";
    }
    updateDelayButtons();

    // Update wake lock indicator
    if (_barWakeLockEl) {
      const active = !!wakeLockSentinel;
      _barWakeLockEl.textContent = active ? "\u{1F512} AWAKE" : "\u{1F4A4} SLEEP OK";
      _barWakeLockEl.style.color = active ? "#4caf50" : "#888";
    }

    // Update stats
    if (_barStatsEl) {
      const t = stats.ok + stats.skipped + stats.error;
      const mode = isQdaySweepActive() ? "QDAY"
        : isBookDiscoveryActive() ? "BOOK:DISCOVER"
        : isBookCaptureActive() ? "BOOK:CAPTURE"
        : "QUEUE";
      _barStatsEl.textContent =
        `OK:${stats.ok} Skip:${stats.skipped} Err:${stats.error} ` +
        `CAPTCHA:${stats.captcha||0} 404:${stats.notfound||0} Total:${t}` +
        ` | ${running ? `RUNNING:${mode}` : "IDLE"}`;
    }
  }

  //#endregion 2. UI

  //#region 3. INFRA HELPERS
  // -- HTTP helpers -----------------------------------------------

  // Resolve per-endpoint timeout. Matches by longest path prefix in
  // HTTP_TIMEOUT_MAP; falls back to HTTP_TIMEOUT_MS.
  function _httpTimeoutFor(path) {
    let best = HTTP_TIMEOUT_MS;
    let bestLen = 0;
    for (const prefix of Object.keys(HTTP_TIMEOUT_MAP)) {
      if (path.startsWith(prefix) && prefix.length > bestLen) {
        best = HTTP_TIMEOUT_MAP[prefix];
        bestLen = prefix.length;
      }
    }
    return best;
  }

  // Single HTTP attempt — wraps GM_xmlhttpRequest in a Promise.
  // Resolves with parsed JSON on 2xx; rejects with a tagged error
  // (`{kind:'network'|'timeout'|'parse'|'abort', message}`) so the
  // retry wrapper can decide whether the failure is transient.
  // The optional `signal` parameter (v5.32.0) hooks the caller's
  // AbortSignal so stopRunning() can cancel in-flight requests.
  function _httpOnce(method, path, body, timeoutMs, signal) {
    return new Promise((resolve, reject) => {
      if (signal && signal.aborted) {
        return reject(makeAbortError(signal.reason));
      }
      let req = null;
      let onAbort = null;
      const cleanup = () => {
        if (signal && onAbort) {
          try { signal.removeEventListener("abort", onAbort); } catch (_) {}
        }
      };
      const opts = {
        method,
        url: RECEIVER + path,
        timeout: timeoutMs,
        onload: (r) => {
          cleanup();
          try { resolve(JSON.parse(r.responseText)); }
          catch (e) {
            const err = new Error("Bad response: " + path + " (" + e.message + ")");
            err.kind = "parse";
            reject(err);
          }
        },
        onerror: () => {
          cleanup();
          // If we're already aborted, prefer the abort label —
          // GM_xmlhttpRequest fires onerror when .abort() is called.
          if (signal && signal.aborted) return reject(makeAbortError(signal.reason));
          const err = new Error("Server unreachable: " + path);
          err.kind = "network";
          reject(err);
        },
        ontimeout: () => {
          cleanup();
          const err = new Error("Server timeout: " + path);
          err.kind = "timeout";
          reject(err);
        },
      };
      if (body) {
        opts.headers = { "Content-Type": "application/json" };
        opts.data = JSON.stringify(body);
      }
      req = GM_xmlhttpRequest(opts);
      if (signal) {
        onAbort = () => {
          try { req && req.abort && req.abort(); } catch (_) {}
          cleanup();
          reject(makeAbortError(signal.reason));
        };
        signal.addEventListener("abort", onAbort, { once: true });
      }
    });
  }

  // Retry only for transient kinds (network/timeout). Receiver-level
  // errors (parse, 4xx/5xx with JSON body) bubble out of _httpOnce as
  // resolved values — retry would just re-execute a real failure.
  // Aborts (kind=abort, name=AbortError) propagate immediately and
  // never retry.
  async function http(method, path, body) {
    const timeoutMs = _httpTimeoutFor(path);
    const signal = currentSignal();
    let lastErr = null;
    for (let attempt = 1; attempt <= HTTP_RETRY_MAX; attempt++) {
      try {
        return await _httpOnce(method, path, body, timeoutMs, signal);
      } catch (e) {
        lastErr = e;
        if (e && (e.kind === "abort" || e.name === "AbortError")) throw e;
        const transient = e && (e.kind === "network" || e.kind === "timeout");
        if (!transient || attempt === HTTP_RETRY_MAX) break;
        const backoff = HTTP_RETRY_BASE_MS * Math.pow(2, attempt - 1);
        log("WARN", `http ${method} ${path} attempt ${attempt}/${HTTP_RETRY_MAX} failed (${e.kind}); retrying in ${backoff}ms`);
        // Abort-aware backoff: bail out of the retry loop instantly if
        // the user pauses/stops during the wait.
        const slept = await waitMs(backoff);
        if (slept === "aborted") throw makeAbortError("stopped during http retry backoff");
      }
    }
    throw lastErr || new Error("http: unknown failure for " + path);
  }

  // ════════════════════════════════════════════════════════════════
  // PUZZLE IDENTITY — ONE RULE
  //
  //   `qqdata.publicid` (= "Q-NNN" displayed under each puzzle =
  //   manifest `pid` in book.json = saved filename) is the SINGLE
  //   canonical puzzle identity, end to end.
  //
  //   URL pid (in /q/{X}/ or /book/B/C/{X}/) is a ROUTING TOKEN.
  //   For most books URL pid == publicid by coincidence; for some
  //   (e.g. book 25369) it equals the site's internal `qid`, a
  //   DIFFERENT namespace (qid 295990 -> publicid 261436). URL pid
  //   must NEVER be compared to identity. Use it only for "did the
  //   route change?" detection or building navigation URLs.
  //
  //   `qid` (from `pagedata.qs[].qid` on chapter listings) is the
  //   value the site's <a href> uses. Used ONLY by
  //   clickPuzzleInChapterListing to build the click selector.
  //
  // Two helpers — never combine them again:
  //   getPublicId()       — canonical identity (qqdata.publicid).
  //                         null until qqdata loads/settles.
  //   getUrlRouteToken()  — opaque integer in the URL path.
  //                         Useful only for navigation/route-change
  //                         detection. Not identity.
  // ════════════════════════════════════════════════════════════════

  /**
   * Canonical puzzle identity. Reads `qqdata.publicid` from the live
   * Alpine store (or window.qqdata fallback for /qday/). Returns null
   * if qqdata is not yet loaded. NEVER reads from the URL.
   */
  function getPublicId() {
    try {
      const qipan = unsafeWindow.Alpine && unsafeWindow.Alpine.store("qipan");
      if (qipan && qipan.qqdata && qipan.qqdata.publicid) {
        return parseInt(qipan.qqdata.publicid, 10);
      }
    } catch (_) {}
    if (typeof unsafeWindow.qqdata !== "undefined" && unsafeWindow.qqdata && unsafeWindow.qqdata.publicid) {
      return parseInt(unsafeWindow.qqdata.publicid, 10);
    }
    return null;
  }

  /**
   * URL-derived route token. Returns the integer in /q/{X}/,
   * /chessmanual/{X}/, or /book/B/C/{X}/. May be qid (≠ publicid)
   * for some books. Use ONLY for "did the URL change?" detection
   * or telemetry. NEVER compare to identity.
   */
  function getUrlRouteToken() {
    const m = location.pathname.match(/\/(?:q|chessmanual)\/(\d+)/);
    if (m) return parseInt(m[1], 10);
    const bm = location.pathname.match(/^\/book\/\d+\/\d+\/(\d+)\/?$/);
    if (bm) return parseInt(bm[1], 10);
    return null;
  }

  function randomBetween(min, max) {
    return min + Math.random() * (max - min);
  }

  function waitMs(ms) {
    // Pause-aware sleep (v5.32.0 rewrite): resolves with "aborted" the
    // moment currentSignal() fires, otherwise with "done" after `ms`.
    // Backed by a single setTimeout + abort listener — no polling
    // tick — so cancellation latency is ~0ms instead of up to 250ms.
    return new Promise((resolve) => {
      const signal = currentSignal();
      if (signal.aborted) return resolve("aborted");
      let timer = null;
      const onAbort = () => {
        if (timer) clearTimeout(timer);
        resolve("aborted");
      };
      timer = setTimeout(() => {
        try { signal.removeEventListener("abort", onAbort); } catch (_) {}
        resolve("done");
      }, ms);
      signal.addEventListener("abort", onAbort, { once: true });
    });
  }

  function getBaseDelay() {
    return GM_getValue(KEY_BASE_DELAY, DEFAULT_BASE_DELAY_MS);
  }

  function setBaseDelay(ms) {
    const clamped = Math.max(MIN_BASE_DELAY_MS, Math.min(MAX_BASE_DELAY_MS, ms));
    GM_setValue(KEY_BASE_DELAY, clamped);
    return clamped;
  }

  function computeAdaptiveDelayMs() {
    const baseDelay = getBaseDelay();
    const processed = stats.ok + stats.skipped + stats.error + (stats.notfound || 0);
    const jitterSpan = baseDelay * JITTER_RATIO;
    let delayMs = baseDelay + randomBetween(-jitterSpan, jitterSpan);

    if (issueStreak > 0) {
      delayMs += Math.min(issueStreak * ERROR_BACKOFF_STEP_MS, ERROR_BACKOFF_MAX_MS);
    }

    if (processed > 0 && processed % BURST_COOLDOWN_EVERY === 0) {
      delayMs += randomBetween(BURST_COOLDOWN_MIN_MS, BURST_COOLDOWN_MAX_MS);
    }

    return Math.max(1200, Math.round(delayMs));
  }

  // -- Anti-blocking: human-like behavior -------------------------

  /**
   * Trigger the site's own Next button via Alpine.js dispatch.
   * The site uses: @click="$dispatch('gotopic', 1)"
   * which fetches nextUrl from $store.qipan and loads the next puzzle via AJAX.
   * Returns true if the puzzle changed, false if it didn't (fallback needed).
   */
  async function triggerSiteNext() {
    // We poll qqdata.publicid for change (the AJAX gotopic swap
    // updates qqdata; URL may not flip on chapter pages). IDENTITY.
    const oldId = getPublicId();
    try {
      const store = unsafeWindow.Alpine && unsafeWindow.Alpine.store("qipan");
      if (!store || !store.nextUrl) {
        plog("WARN", "No Alpine nextUrl — site Next unavailable");
        return false;
      }
      // Mark game as finished so Next button is rendered. Some site
      // versions define `gameFinished` as a read-only/computed property
      // on the Alpine store proxy — assignment then throws and would
      // abort the whole dispatch. Swallow the failure: the gotopic
      // event below is what actually drives navigation.
      try {
        store.gameFinished = true;
      } catch (e) {
        plog("DEBUG", `Site Next: cannot set gameFinished (${e.message}) — proceeding with gotopic dispatch anyway`);
      }

      // Dispatch the gotopic event (same as clicking Next button)
      const topicEl = document.querySelector('[x-data]');
      if (topicEl) {
        topicEl.dispatchEvent(new CustomEvent("gotopic", {
          detail: 1,
          bubbles: true,
        }));
      } else {
        // Fallback: directly call the Alpine dispatch mechanism
        unsafeWindow.dispatchEvent(new CustomEvent("gotopic", {
          detail: 1,
          bubbles: true,
        }));
      }

      // Wait for the puzzle to change (Alpine store qqdata.publicid)
      const changed = await waitForPuzzleChange(oldId, GOTOPIC_TIMEOUT_MS);
      if (changed) {
        // DEBUG only — goNext() emits the user-facing [NEXT] line right
        // after this with the full chapter/position/pid context. Two
        // back-to-back [NEXT] lines for the same transition were noise.
        plog("DEBUG", `triggerSiteNext: AJAX swap landed (publicid=${getPublicId()})`);
        return true;
      }
      plog("WARN", `Site Next dispatched but puzzle didn't change (was ${oldId})`);
      return false;
    } catch (err) {
      plog("WARN", `Site Next failed: ${err.message}`);
      return false;
    }
  }

  /**
   * Wait for the Alpine store puzzle ID to change from oldId.
   * Returns true if changed within timeout, false otherwise.
   */
  function waitForPuzzleChange(oldId, timeoutMs) {
    return new Promise((resolve) => {
      const signal = currentSignal();
      if (signal.aborted) return resolve(false);
      let elapsed = 0;
      const interval = 500;
      const iv = setInterval(() => {
        if (signal.aborted) {
          clearInterval(iv);
          return resolve(false);
        }
        elapsed += interval;
        // Poll publicid (qqdata identity), not URL — gotopic AJAX
        // swaps qqdata; URL may not flip on chapter pages.
        const currentId = getPublicId();
        if (currentId && currentId !== oldId) {
          clearInterval(iv);
          resolve(true);
        } else if (elapsed >= timeoutMs) {
          clearInterval(iv);
          resolve(false);
        }
      }, interval);
    });
  }

  /**
   * Simulate human-like page interaction:
   * - Random scroll (30% chance)
   * - "Think time" delay (3-8s)
   * - Session break every N puzzles (2-6 min)
   */
  async function simulateHumanBehavior() {
    const totalCaptures = stats.ok + stats.skipped;

    // Session break
    if (totalCaptures > 0 && totalCaptures % SESSION_BREAK_EVERY === 0) {
      const breakMs = randomBetween(SESSION_BREAK_MIN_MS, SESSION_BREAK_MAX_MS);
      const breakMin = (breakMs / 60000).toFixed(1);
      plog("WAIT", `Session break: ${breakMin} min pause (${totalCaptures} puzzles done)`);
      updateStatus(`Taking a break... ${breakMin} min (${totalCaptures} done)`, "#888");
      if (await waitMs(breakMs) === "aborted") return;
    }

    // Think time
    const thinkMs = randomBetween(THINK_TIME_MIN_MS, THINK_TIME_MAX_MS);
    if (await waitMs(thinkMs) === "aborted") return;

    // Random scroll noise
    if (Math.random() < SCROLL_NOISE_CHANCE) {
      try {
        const scrollY = Math.floor(randomBetween(50, 300));
        unsafeWindow.scrollBy({ top: scrollY, behavior: "smooth" });
        if (await waitMs(randomBetween(800, 2000)) === "aborted") return;
        unsafeWindow.scrollBy({ top: -scrollY, behavior: "smooth" });
      } catch (_) {}
    }
  }

  // -- Wake Lock (sleep prevention) --------------------------------
  // Note: navigator.wakeLock.request() rejects when the document is
  // hidden. We swallow that case quietly and rely on the
  // visibilitychange listener at the bottom of the file to re-acquire
  // when the tab is foregrounded.
  async function acquireWakeLock() {
    if (!wakeLockEnabled) return;
    if (!("wakeLock" in navigator)) {
      log("WARN", "Wake Lock API not available in this browser");
      return;
    }
    if (typeof document !== "undefined" && document.visibilityState !== "visible") {
      log("DEBUG", "acquireWakeLock: tab hidden — deferring until visibilitychange");
      return;
    }
    try {
      wakeLockSentinel = await navigator.wakeLock.request("screen");
      wakeLockSentinel.addEventListener("release", () => {
        log("INFO", "Wake lock released");
        wakeLockSentinel = null;
      });
      log("INFO", "Wake lock acquired");
    } catch (err) {
      log("WARN", "Wake lock request failed: " + err.message);
      wakeLockSentinel = null;
    }
  }

  async function releaseWakeLock() {
    if (wakeLockSentinel) {
      try {
        await wakeLockSentinel.release();
      } catch (_) {}
      wakeLockSentinel = null;
    }
  }

  // -- Tab ownership -----------------------------------------------
  // Only one tab may drive the sweep.  Other tabs observe silently.
  let _heartbeatIv = null;

  function isOwnerTab() {
    return GM_getValue(KEY_OWNER_TAB, null) === TAB_ID;
  }

  function isOwnerStale() {
    return Date.now() - GM_getValue(KEY_OWNER_HEARTBEAT, 0) > OWNER_STALE_MS;
  }

  function _writeHeartbeat() {
    // Guard: only write if we are still the owner.  Another tab may have
    // force-claimed ownership (e.g. via startBook / startQdaySweep).
    // Without this check, an orphaned heartbeat keeps the stale owner
    // looking alive indefinitely.
    if (GM_getValue(KEY_OWNER_TAB, null) !== TAB_ID) {
      stopHeartbeat();
      return;
    }
    GM_setValue(KEY_OWNER_HEARTBEAT, Date.now());
  }

  function startHeartbeat() {
    stopHeartbeat();
    _writeHeartbeat();
    _heartbeatIv = setInterval(_writeHeartbeat, HEARTBEAT_INTERVAL_MS);
  }

  function stopHeartbeat() {
    if (_heartbeatIv) { clearInterval(_heartbeatIv); _heartbeatIv = null; }
  }

  function claimOwnership() {
    GM_setValue(KEY_OWNER_TAB, TAB_ID);
    startHeartbeat();
  }

  function releaseOwnership() {
    if (isOwnerTab()) {
      GM_setValue(KEY_OWNER_TAB, null);
      GM_setValue(KEY_OWNER_HEARTBEAT, 0);
    }
    stopHeartbeat();
  }

  // v5.37.0: read the explicit user-pause flag. autoStart() and the boot
  // path consult this to refuse auto-resume after a user-initiated stop.
  function isUserPaused() {
    return !!GM_getValue(KEY_USER_PAUSED, false);
  }

  function setUserPaused(paused) {
    GM_setValue(KEY_USER_PAUSED, !!paused);
  }

  // -- Centralized state transitions (with tab ownership) ----------
  // startRunning() is the ONLY path that flips running=true. It is now
  // called solely from explicit user actions ([Control] Resume,
  // [Control] Take Ownership, [Book] Start / Resume, startBook,
  // startQdaySweep, etc.). autoStart() never calls it on its own \u2014
  // see v5.37.0 notes in autoStart().
  function startRunning() {
    const currentOwner = GM_getValue(KEY_OWNER_TAB, null);
    if (currentOwner && currentOwner !== TAB_ID && !isOwnerStale()) {
      log("WARN", `Another tab (${currentOwner}) is already running`);
      updateStatus(`Observing \u2014 another tab is running the sweep`, "#888");
      return false;
    }
    // Defensive rotation: if a previous session left an aborted
    // controller in place, replace it so currentSignal() is fresh.
    if (_abortCtrl.signal.aborted) {
      _abortCtrl = new AbortController();
    }
    // Any explicit start clears the user-pause flag \u2014 the user has
    // consciously asked the loop to run again.
    setUserPaused(false);
    running = true;
    GM_setValue(KEY_RUNNING, true);
    claimOwnership();
    if (wakeLockEnabled) acquireWakeLock();
    return true;
  }

  function stopRunning(reason) {
    // Order matters: abort BEFORE flipping `running` so that any
    // promise observing both sees abort first (cleaner unwind in
    // try/catch), then rotate to a fresh controller so post-stop
    // cleanup HTTP calls (/queue/stop, etc.) aren't auto-aborted.
    rotateAbortCtrl(reason || "user stopped");
    running = false;
    GM_setValue(KEY_RUNNING, false);
    releaseOwnership();
    releaseWakeLock();
    // Cancel any pending CAPTCHA poll — otherwise it can fire after
    // stop and silently re-enter capture(). See _captchaPoll comment
    // in capture().
    if (_captchaPoll) {
      try { clearInterval(_captchaPoll); } catch (e) { log("DEBUG", "clearInterval(captchaPoll) failed: " + e.message); }
      _captchaPoll = null;
    }
    if (reason) log("INFO", `Stopped: ${reason}`);
  }

  // ------------------------------------------------------------------
  // failAndAdvance: shared error-tail used throughout capture() and
  // its async helpers. Replaces the ~15 copy-pasted blocks of:
  //   issueStreak += 1; stats.<key>++; GM_setValue(KEY_STATS, stats);
  //   plog(phase, msg); updateStatus(text, color); if (running) goNext();
  // Drift in any one of those lines silently lost telemetry; this
  // helper is the single point of writes.
  // ------------------------------------------------------------------
  function failAndAdvance({ phase = "WARN", logMsg, statusText, statusColor = "#ff9800",
                            statKey = "error", advance = true } = {}) {
    issueStreak += 1;
    if (statKey && Object.prototype.hasOwnProperty.call(stats, statKey)) {
      stats[statKey] = (stats[statKey] || 0) + 1;
    }
    GM_setValue(KEY_STATS, stats);
    if (logMsg) plog(phase, logMsg);
    if (statusText) updateStatus(statusText, statusColor);
    if (advance && running) goNext();
  }

  // ------------------------------------------------------------------
  // Unified puzzle-event label.
  //   `book=<id> Ch.<n> pos.<n> pid=<n> (<idx>/<total>)`
  // Mirrored on the receiver side (see _puzzle_prefix in receiver.py).
  // Use for every plog line that scopes to a single puzzle so the
  // browser console and server log share the same scannable shape.
  // Returns "" when no book context is active.
  // ------------------------------------------------------------------
  function puzzleLabel({ pid = null, chapter_number = null, chapter_position = null,
                          progress = null } = {}) {
    if (!isBookCaptureActive()) return "";
    const parts = [`book=${bookPlan && bookPlan.book_id}`];
    if (chapter_number != null) parts.push(`Ch.${chapter_number}`);
    if (chapter_position != null) parts.push(`pos.${chapter_position}`);
    if (pid != null) parts.push(`pid=${pid}`);
    if (progress) parts.push(`(${progress})`);
    return parts.join(" ");
  }

  // Look up the chapter cursor entry the gate is *expecting* to see.
  // Pure read; returns null outside chapter mode.
  function currentChapterEntry() {
    if (!(isBookCaptureActive() && isChapterMode() && bookPlan
          && Array.isArray(bookPlan.chapter_seq))) return null;
    return bookPlan.chapter_seq[bookPlan.current_seq_idx || 0] || null;
  }

  // Module-level handle for the CAPTCHA wait-poll (see capture()).
  // Without this, repeated CAPTCHAs stacked multiple intervals all
  // calling capture() concurrently — a re-entrancy bug compounded by
  // the lack of an in-flight guard on capture() itself.
  let _captchaPoll = null;

  //#endregion 3. INFRA HELPERS

  //#region 4. QDAY SWEEP
  // -- Qday sweep helpers -----------------------------------------
  function isQdaySweepActive() {
    return !!(qdayPlan && qdayPlan.active);
  }

  function saveQdayPlan(plan) {
    qdayPlan = plan;
    GM_setValue(KEY_QDAY_PLAN, plan);
  }

  function clearQdayPlan() {
    qdayPlan = null;
    GM_setValue(KEY_QDAY_PLAN, null);
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function isoDate(y, m, d) {
    return `${y}-${pad2(m)}-${pad2(d)}`;
  }

  function compareIsoDates(a, b) {
    if (a === b) return 0;
    return a < b ? -1 : 1;
  }

  function parseIsoDate(iso) {
    const [y, m, d] = iso.split("-").map((v) => parseInt(v, 10));
    return new Date(Date.UTC(y, m - 1, d));
  }

  function shiftIsoDate(iso, deltaDays) {
    const dt = parseIsoDate(iso);
    dt.setUTCDate(dt.getUTCDate() + deltaDays);
    return isoDate(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate());
  }

  function todayIsoDate() {
    const dt = new Date();
    return isoDate(dt.getFullYear(), dt.getMonth() + 1, dt.getDate());
  }

  function parseQdayPath(pathname = location.pathname) {
    const detail = pathname.match(/^\/qday\/(\d{4})\/(\d{1,2})\/(\d{1,2})\/(\d{1,2})\/?$/);
    if (detail) {
      return {
        date: isoDate(parseInt(detail[1], 10), parseInt(detail[2], 10), parseInt(detail[3], 10)),
        num: parseInt(detail[4], 10),
      };
    }

    const day = pathname.match(/^\/qday\/(\d{4})\/(\d{1,2})\/(\d{1,2})\/?$/);
    if (day) {
      return {
        date: isoDate(parseInt(day[1], 10), parseInt(day[2], 10), parseInt(day[3], 10)),
        num: null,
      };
    }

    return null;
  }

  function buildQdayUrl(dateIso, num) {
    const [y, m, d] = dateIso.split("-").map((v) => parseInt(v, 10));
    return `https://www.101weiqi.com/qday/${y}/${m}/${d}/${num}/`;
  }

  function syncQdayPlanFromPage() {
    if (!isQdaySweepActive()) return;
    const current = parseQdayPath();
    if (!current || current.num === null) return;
    if (qdayPlan.currentDate === current.date && qdayPlan.currentNum === current.num) return;
    saveQdayPlan({
      ...qdayPlan,
      currentDate: current.date,
      currentNum: current.num,
    });
  }

  function computeNextQdayPlan(plan) {
    let nextDate = plan.currentDate;
    let nextNum = plan.currentNum;
    const dateDelta = plan.dateDirection === "forward" ? 1 : -1;

    if (plan.order === "desc") {
      if (nextNum > DAILY_MIN_NUM) {
        nextNum -= 1;
      } else {
        nextNum = DAILY_MAX_NUM;
        nextDate = shiftIsoDate(nextDate, dateDelta);
      }
    } else {
      if (nextNum < DAILY_MAX_NUM) {
        nextNum += 1;
      } else {
        nextNum = DAILY_MIN_NUM;
        nextDate = shiftIsoDate(nextDate, dateDelta);
      }
    }

    const cmp = compareIsoDates(nextDate, plan.targetDate);
    if ((plan.dateDirection === "forward" && cmp > 0) || (plan.dateDirection === "backward" && cmp < 0)) {
      return null;
    }

    return {
      ...plan,
      currentDate: nextDate,
      currentNum: nextNum,
    };
  }

  function startQdaySweep(order) {
    clearBookDiscovery();
    clearBookPlan();
    const current = parseQdayPath();
    if (!current) {
      alert("Open a qday page first (for example: /qday/2015/7/13/1/).");
      return;
    }

    const targetDate = todayIsoDate();
    const startDate = current.date;
    const dateDirection = compareIsoDates(startDate, targetDate) <= 0 ? "forward" : "backward";
    const startNum = current.num !== null
      ? current.num
      : (order === "desc" ? DAILY_MAX_NUM : DAILY_MIN_NUM);

    const plan = {
      active: true,
      source: "qday-local",
      order,
      dateDirection,
      currentDate: startDate,
      currentNum: startNum,
      targetDate,
      started_at: new Date().toISOString(),
    };

    saveQdayPlan(plan);
    claimOwnership(); // Explicit user action — force-claim this tab
    startRunning();

    const nextUrl = buildQdayUrl(plan.currentDate, plan.currentNum);
    log("INFO", `Qday sweep started: ${plan.currentDate} #${plan.currentNum} -> ${plan.targetDate} (${plan.order}, ${plan.dateDirection})`);
    plog("NEXT", `Qday sweep: ${plan.currentDate} #${plan.currentNum} -> ${plan.targetDate} (${plan.order === "desc" ? "8->1" : "1->8"}, ${plan.dateDirection})`);
    updateStatus(
      `Qday sweep started (${order === "desc" ? "8->1" : "1->8"}) ${plan.currentDate} -> ${plan.targetDate}`,
      "#4fc3f7"
    );

    if (location.href !== nextUrl) {
      location.href = nextUrl;
      return;
    }
    capture();
  }

  //#endregion 4. QDAY SWEEP

  //#region 5. BOOK DISCOVERY
  // -- Book sweep: URL parsing & DOM extraction ----------------------

  function parseBookPath(pathname = location.pathname) {
    // /book/5121/8973/12345/           → { book_id, chapter_id, puzzle_id, type: "puzzle" }
    // /book/5121/8973/                 → { book_id, chapter_id, type: "chapter" }
    // /book/5121/8973/?page=2          → { book_id, chapter_id, page: 2, type: "chapter" }
    // /book/5121/                      → { book_id, type: "book" }

    // 3-segment puzzle-on-chapter URL takes precedence over chapter listing.
    const pz = pathname.match(/^\/book\/(\d+)\/(\d+)\/(\d+)\/?$/);
    if (pz) {
      return {
        book_id: parseInt(pz[1], 10),
        chapter_id: parseInt(pz[2], 10),
        puzzle_id: parseInt(pz[3], 10),
        type: "puzzle",
      };
    }

    const ch = pathname.match(/^\/book\/(\d+)\/(\d+)/);
    if (ch) {
      const params = new URLSearchParams(location.search);
      return {
        book_id: parseInt(ch[1], 10),
        chapter_id: parseInt(ch[2], 10),
        page: parseInt(params.get("page") || "1", 10),
        type: "chapter",
      };
    }

    const bk = pathname.match(/^\/book\/(\d+)\/?$/);
    if (bk) return { book_id: parseInt(bk[1], 10), type: "book" };

    return null;
  }

  function isBookPage() {
    return location.pathname.startsWith("/book/");
  }

  // Access embedded JS variables directly via unsafeWindow (no HTML parsing)
  function extractPagedata() {
    try {
      if (unsafeWindow.pagedata) return unsafeWindow.pagedata;
      if (unsafeWindow.nodedata && unsafeWindow.nodedata.pagedata)
        return unsafeWindow.nodedata.pagedata;
      if (unsafeWindow.bookdata) return unsafeWindow.bookdata;
    } catch (_) {}
    return null;
  }

  function extractChaptersFromDom() {
    const pd = extractPagedata();
    if (!pd) return [];
    const chapters = pd.chapters || pd.zjlist;
    if (!Array.isArray(chapters)) return [];
    return chapters
      .filter((e) => e && (e.id || e.zjid))
      .map((e) => {
        // Site-declared puzzle count for the chapter. The book root
        // page exposes this on each zjlist entry as `nodecount`. Some
        // older payloads use `qcount`/`qnum`. Falling back to qids.length
        // covers both shapes; 0 means the chapter listing already told
        // us it has no puzzles, so we should skip it without ever
        // navigating in (see init code that sets skip_status="declared_empty").
        const declaredCount =
          (typeof e.nodecount === "number" ? e.nodecount : null)
          ?? (typeof e.qcount === "number" ? e.qcount : null)
          ?? (typeof e.qnum === "number" ? e.qnum : null)
          ?? (Array.isArray(e.qids) ? e.qids.length : 0);
        return {
          chapter_id: parseInt(e.id || e.zjid, 10),
          name: e.name || "",
          declared_count: declaredCount | 0,
        };
      });
  }

  /**
   * Extract puzzle entries with their positional index from pagedata.
   * Returns [{id, qindex}] where qindex is:
   *   - Global position on level-order pages (e.g. 61 on page 2)
   *   - Per-chapter position on chapter pages (e.g. 1-38)
   *
   * ID FIELD CHOICE: prefer `publicid` (the "Q-NNN" number shown to users
   * and stamped on `qqdata.publicid` at capture time). Some books expose a
   * separate `qid` field which is a *different ID space* — visiting
   * `/q/{qid}/` redirects to a page whose `qqdata.publicid` differs (e.g.
   * book 25369 ch1: qid 295990 -> publicid 261436). If discovery stores the
   * qid, the capture-time identity gate refuses every puzzle as
   * url_data_mismatch. We must store the same field the gate compares
   * against. See memory: "weiqi101: discovery vs capture id-space drift".
   */
  function extractPuzzleEntriesFromDom() {
    const pd = extractPagedata();
    if (!pd) return [];
    const qs = pd.qs;
    if (!Array.isArray(qs)) return [];
    // `id` is the canonical identity (publicid) — matches qqdata.publicid,
    // the capture-time identity gate, and stored manifest pids.
    // `anchorId` is the value the chapter-listing <a href> actually uses;
    // for some books (e.g. 25369) qid != publicid, so the anchor lives
    // at /book/{book}/{chapter}/{qid}/ even though the puzzle's logical
    // identity is publicid. clickPuzzleInChapterListing needs anchorId.
    return qs
      .map((e) => {
        const publicid = parseInt(e.publicid, 10);
        const qid = parseInt(e.qid, 10);
        const fallback = parseInt(e.id, 10);
        const id = !isNaN(publicid) ? publicid : (!isNaN(qid) ? qid : fallback);
        const anchorId = !isNaN(qid) ? qid : id;
        return {
          id,
          anchorId,
          qindex: parseInt(e.qindex, 10) || 0,
        };
      })
      .filter((e) => !isNaN(e.id));
  }

  function extractMaxPage() {
    const pd = extractPagedata();
    if (!pd) return 1;
    return pd.maxpage || 1;
  }

  function extractBookName() {
    const pd = extractPagedata();
    if (!pd) return "";
    return String(pd.bookname || pd.name || "").trim();
  }

  function extractBookDifficulty() {
    const pd = extractPagedata();
    if (!pd) return "";
    return String(pd.qlevelname || pd.difficulty || "").trim();
  }

  function extractChapterNumber() {
    const pd = extractPagedata();
    if (!pd) return 0;
    return parseInt(pd.number, 10) || 0;
  }

  function buildChapterUrl(bookId, chapterId, page) {
    // ALWAYS include explicit ?page=N (even for page 1). When the URL omits
    // ?page=, 101weiqi sometimes lands on the last page instead of page 1,
    // which corrupts the scrape order. Explicit page eliminates that.
    const base = `https://www.101weiqi.com/book/${bookId}/${chapterId}/`;
    const p = page && page >= 1 ? page : 1;
    return `${base}?page=${p}`;
  }

  /**
   * Infer the actually-rendered chapter page from puzzle qindex values.
   * 101weiqi assigns each puzzle a per-chapter qindex (1, 2, 3, ...).
   * The first qindex on a page tells us which page slice we're viewing,
   * regardless of what the URL or our requested page says.
   *
   * Returns the inferred page number in [1, maxPage], or null if no qindex
   * data is available (caller should fall back to URL/state).
   */
  function inferRenderedPage(entries, maxPage, defaultPerPage = 25) {
    if (!Array.isArray(entries) || entries.length === 0) return null;
    const qidxs = entries.map((e) => e.qindex).filter((q) => q > 0);
    if (qidxs.length === 0) return null;
    const firstQ = Math.min(...qidxs);
    const lastQ = Math.max(...qidxs);
    // perPage estimate: trust this page's span if it looks "full",
    // otherwise assume the site's standard 25/page (last page may be short).
    const localPerPage = lastQ - firstQ + 1;
    const perPage = localPerPage >= defaultPerPage ? localPerPage : defaultPerPage;
    const inferred = Math.floor((firstQ - 1) / perPage) + 1;
    return Math.max(1, Math.min(inferred, Math.max(1, maxPage || 1)));
  }

  /**
   * Pick the next page to visit given the set of pages already scraped and
   * the current rendered page. Prefer the nearest unscraped page going
   * forward; if none, fall back to the nearest unscraped page going backward.
   * Returns null if every page in [1..maxPage] has been scraped.
   */
  function pickNextChapterPage(scrapedPages, maxPage, currentPage) {
    const scraped = new Set((scrapedPages || []).map(Number));
    const remaining = [];
    for (let p = 1; p <= maxPage; p++) {
      if (!scraped.has(p)) remaining.push(p);
    }
    if (remaining.length === 0) return null;
    const forward = remaining.find((p) => p > currentPage);
    if (forward != null) return forward;
    // No forward page missing — go backward, nearest first.
    const backward = remaining.filter((p) => p < currentPage).sort((a, b) => b - a);
    return backward[0] != null ? backward[0] : remaining[0];
  }

  // 101weiqi serves chapter listings at a fixed page size (observed: 60
  // puzzles per page on book 75592 across all chapters). We use this to
  // jump straight to the listing page that contains a target puzzle
  // instead of always landing on page 1 and paginating forward — which
  // wasted up to N-1 page loads (and N-1 anti-bot delays) per puzzle on
  // chapters with multiple pages.
  //
  // The default below is the conservative baseline. The actual per-page
  // count is re-learned from the live DOM on every chapter-listing
  // visit (see `recordObservedPerPage`) and persisted in
  // `bookPlan.observed_per_page` so it survives navigation reloads. If
  // the page math is wrong (no expected pids visible), the per-chapter
  // fallback flag forces sequential page-1 → page-2 → … pagination for
  // the rest of that chapter.
  const CHAPTER_PUZZLES_PER_PAGE = 60;

  function effectivePerPage() {
    const fromPlan = bookPlan && Number(bookPlan.observed_per_page);
    if (Number.isFinite(fromPlan) && fromPlan > 0) return fromPlan;
    return CHAPTER_PUZZLES_PER_PAGE;
  }

  function recordObservedPerPage(visibleCount, currentPage, maxPage) {
    if (!bookPlan) return;
    if (!Number.isFinite(visibleCount) || visibleCount < 1) return;
    const prev = Number(bookPlan.observed_per_page) || 0;
    // Only trust full pages (currentPage < maxPage). The last page is
    // typically partial and would shrink the estimate. Allow upward
    // revisions from the last page only (visibleCount > prev).
    const isFullPage = Number(currentPage) > 0 && Number(maxPage) > 0
      && Number(currentPage) < Number(maxPage);
    let next = prev;
    if (isFullPage) {
      next = visibleCount;
    } else if (visibleCount > prev) {
      next = visibleCount;
    }
    if (next !== prev && next > 0) {
      bookPlan.observed_per_page = next;
      saveBookPlan(bookPlan);
      plog("INFO", `chapter listing page size learned: ${next}/page (was ${prev || "default"})`);
    }
  }

  function chapterUsesFallbackPagination(chapterId) {
    if (!bookPlan || !chapterId) return false;
    const list = bookPlan.fallback_paginate_chapters;
    return Array.isArray(list) && list.includes(chapterId);
  }

  function markChapterFallbackPagination(chapterId) {
    if (!bookPlan || !chapterId) return;
    if (!Array.isArray(bookPlan.fallback_paginate_chapters)) {
      bookPlan.fallback_paginate_chapters = [];
    }
    if (!bookPlan.fallback_paginate_chapters.includes(chapterId)) {
      bookPlan.fallback_paginate_chapters.push(chapterId);
      saveBookPlan(bookPlan);
    }
  }

  function chapterPageForPosition(posInChapter, perPage) {
    const pp = perPage && perPage > 0 ? perPage : effectivePerPage();
    const n = Number(posInChapter);
    if (!Number.isFinite(n) || n < 1) return 1;
    return Math.floor((n - 1) / pp) + 1;
  }

  /**
   * Compute the chapter-listing page for a chapter_seq entry. Falls back
   * to page 1 if the entry has no per-chapter position recorded.
   */
  function targetChapterPageForEntry(entry) {
    if (!entry) return 1;
    return chapterPageForPosition(entry.pos_in_chapter || 0);
  }

  function isChapterMode() {
    return !!(bookPlan && bookPlan.active && bookPlan.mode === "chapter");
  }

  function chapterPlanCurrentEntry(plan) {
    if (!plan || !Array.isArray(plan.chapter_seq)) return null;
    return plan.chapter_seq[plan.current_seq_idx] || null;
  }

  // -- Book sweep: Discovery state management ------------------------

  function isBookDiscoveryActive() {
    return !!(bookDiscovery && bookDiscovery.phase && bookDiscovery.phase !== "done");
  }

  function saveBookDiscovery(disc) {
    bookDiscovery = disc;
    GM_setValue(KEY_BOOK_DISCOVERY, disc);
  }

  function clearBookDiscovery() {
    bookDiscovery = null;
    GM_setValue(KEY_BOOK_DISCOVERY, null);
  }

  // -- Book sweep: Capture state management --------------------------

  function isBookCaptureActive() {
    return !!(bookPlan && bookPlan.active);
  }

  function saveBookPlan(plan) {
    bookPlan = plan;
    GM_setValue(KEY_BOOK_PLAN, plan);
  }

  function clearBookPlan() {
    bookPlan = null;
    GM_setValue(KEY_BOOK_PLAN, null);
  }

  // -- Book sweep: Discovery telemetry & checkpoint --------------------

  /**
   * Merge a skip-state echo from the receiver into the in-memory
   * bookDiscovery.chapters list. The receiver flips skip_status when
   * a chapter has had too many empty page-1 renders (auto_empty) or
   * when the user runs the `skip-chapter` CLI (manual). The userscript
   * has no other channel to learn about these flips within a session,
   * so every progress response carries the current state.
   */
  function applySkipStateMerge(states) {
    if (!Array.isArray(states) || !bookDiscovery || !bookDiscovery.chapters) {
      return false;
    }
    let dirty = false;
    const byId = new Map();
    for (const s of states) {
      if (s && s.chapter_id != null) byId.set(s.chapter_id, s);
    }
    for (const ch of bookDiscovery.chapters) {
      const s = byId.get(ch.chapter_id);
      if (!s) continue;
      if (ch.skip_status !== s.skip_status) {
        ch.skip_status = s.skip_status || null;
        ch.skip_reason = s.skip_reason || null;
        dirty = true;
      }
      const ea = s.empty_attempts || 0;
      if ((ch.empty_attempts || 0) !== ea) {
        ch.empty_attempts = ea;
        dirty = true;
      }
    }
    if (dirty) saveBookDiscovery(bookDiscovery);
    return dirty;
  }

  /**
   * Report discovery progress to backend for JSONL telemetry logging.
   * Also sends current discovery_state for checkpoint persistence.
   * The receiver may echo `chapter_skip_states` so we can react to
   * server-side skip flips (auto-empty threshold or manual CLI override)
   * within the same session.
   */
  async function reportDiscoveryProgress(phase, step, detail) {
    try {
      const resp = await http("POST", "/book/discovery/progress", {
        book_id: bookDiscovery ? bookDiscovery.book_id : null,
        phase,
        step,
        detail: detail || {},
        discovery_state: bookDiscovery,
      });
      if (resp && resp.chapter_skip_states) {
        applySkipStateMerge(resp.chapter_skip_states);
      }
      return resp;
    } catch (_) {
      // Non-critical — don't block discovery if backend is temporarily unreachable
      plog("WARN", `Discovery telemetry failed for ${phase}/${step}`);
      return null;
    }
  }

  /**
   * Emit a capture-mode lifecycle event (paused, resumed, jumped,
   * chapter_skipped, session_break) into the per-book capture-log.jsonl.
   * Best-effort: failures are logged to console only; never block the
   * main loop. Falls back gracefully when no book is active.
   */
  async function reportBookEvent(eventType, detail) {
    const bookId = (bookPlan && bookPlan.book_id)
      || (bookDiscovery && bookDiscovery.book_id)
      || null;
    const bookName = (bookPlan && bookPlan.book_name)
      || (bookDiscovery && bookDiscovery.book_name)
      || "";
    if (!bookId) return; // nothing to log against
    try {
      await http("POST", "/book/log/event", {
        book_id: bookId,
        book_name: bookName,
        event_type: eventType,
        detail: detail || {},
      });
    } catch (_) {
      plog("WARN", `Book event log failed for ${eventType}`);
    }
  }

  /**
   * Check backend for existing discovery state before starting fresh.
   * Returns { status: "complete"|"partial"|"none", manifest?, checkpoint? }
   */
  async function checkBackendDiscoveryState(bookId) {
    try {
      return await http("GET", `/book/${bookId}/discovery`);
    } catch (_) {
      return { status: "none" };
    }
  }

  // -- Book sweep: Discovery state machine ---------------------------

  async function continueDiscovery() {
    const bookPath = parseBookPath();
    if (!bookPath) return;

    // v5.38.0 interleaved flow: when bookPlan is active (chapter-scoped
    // capture in progress) we MUST NOT re-enter discovery, even if
    // bookDiscovery is still in storage. The capture-complete handler
    // will navigate back to the next chapter listing and clear the
    // awaiting_capture flag at the right moment.
    if (isBookCaptureActive()) {
      plog(
        "INFO",
        `continueDiscovery: bookPlan active (scope_chapter_idx=${bookPlan.scope_chapter_idx ?? "—"}) — yielding to capture`,
      );
      return;
    }
    if (bookDiscovery && bookDiscovery.awaiting_capture) {
      plog(
        "INFO",
        "continueDiscovery: discovery is awaiting_capture but no bookPlan — clearing flag and resuming",
      );
      bookDiscovery.awaiting_capture = false;
      delete bookDiscovery.awaiting_chapter_idx;
      saveBookDiscovery(bookDiscovery);
    }

    // --- INITIAL: User landed on /book/{id}/ page, no discovery active ---
    if (!bookDiscovery || !bookDiscovery.phase) {
      if (bookPath.type !== "book") return;

      // Check backend for existing discovery state (checkpoint/restart)
      const existing = await checkBackendDiscoveryState(bookPath.book_id);

      if (existing.status === "complete") {
        plog("INFO", `Book ${bookPath.book_id} already discovered — opening overlay (Cancel / Capture / Restart Discovery)`);
        showBookDiscoveryOverlay(bookPath.book_id);
        return;
      }

      // Wait for page JS to load
      await waitMs(1500);

      const chapters = extractChaptersFromDom();
      const bookName = extractBookName();
      const difficulty = extractBookDifficulty();

      if (chapters.length === 0) {
        plog("WARN", `Book ${bookPath.book_id}: no chapters found in DOM`);
        updateStatus("No chapters found on this page.", "#ff9800");
        return;
      }

      // Resume from checkpoint if partial discovery exists
      if (existing.status === "partial" && existing.checkpoint) {
        const cp = existing.checkpoint;
        // Validate checkpoint matches current book
        if (cp.book_id === bookPath.book_id && cp.chapters && cp.chapters.length > 0) {
          plog("INFO", `Resuming discovery from checkpoint: Ch.${(cp.current_chapter_idx || 0) + 1}, phase=${cp.phase}`);
          bookDiscovery = cp;
          saveBookDiscovery(cp);
          await reportDiscoveryProgress("resume", "checkpoint_loaded", {
            chapter_idx: cp.current_chapter_idx,
            page: cp.current_page,
            phase: cp.phase,
          });

          // Navigate to the right page based on checkpoint phase
          if (cp.phase === "chapter_puzzles") {
            const ch = cp.chapters[cp.current_chapter_idx];
            if (ch) {
              const delay = computeAdaptiveDelayMs();
              await waitMs(delay);
              location.href = buildChapterUrl(cp.book_id, ch.chapter_id, cp.current_page || 1);
              return;
            }
          } else if (cp.phase === "chapters") {
            // Re-fetch the book root to re-scrape chapter list
            location.href = `https://www.101weiqi.com/book/${cp.book_id}/`;
            return;
          }
          // If phase is "done" or unknown, fall through to fresh discovery
        }
      }

      const disc = {
        phase: "chapter_puzzles",
        book_id: bookPath.book_id,
        book_name: bookName,
        difficulty: difficulty,
        chapters: chapters.map((c, i) => {
          const ch = {
            chapter_id: c.chapter_id,
            chapter_number: i + 1,
            name: c.name,
            puzzle_ids: [],
            declared_count: c.declared_count | 0,
          };
          // Pre-skip chapters the book listing already declared empty
          // (nodecount === 0). This avoids a wasteful navigate→render→
          // chapter_empty_attempt round-trip and the threshold-bump
          // wait-loop that previously stalled discovery on books like
          // 5120 (chapters 18, 19, 112). The R2a skip block in the
          // chapter-puzzle handler honours skip_status and walks past.
          if (ch.declared_count === 0) {
            ch.skip_status = "declared_empty";
            ch.skip_reason = "book listing reports nodecount=0";
          }
          return ch;
        }),
        current_chapter_idx: 0,
        current_page: 1,
        started_at: new Date().toISOString(),
      };
      const declaredEmpty = disc.chapters.filter(
        (c) => c.skip_status === "declared_empty",
      );
      if (declaredEmpty.length > 0) {
        const labels = declaredEmpty
          .map((c) => "Ch." + c.chapter_number)
          .join(", ");
        plog(
          "INFO",
          `Pre-skipping ${declaredEmpty.length} chapter(s) with declared nodecount=0: ${labels}`,
        );
      }

      saveBookDiscovery(disc);
      plog("LOAD", `Book "${bookName}" — ${chapters.length} chapters found, starting discovery`);
      updateStatus(
        `Discovering "${bookName}" — ${chapters.length} chapters`,
        "#4fc3f7"
      );

      // Telemetry: discovery started — include the full chapter list so
      // the FIRST line in capture-log.jsonl identifies every discovered
      // chapter (id + name) rather than just a count. (Bug C, 2026-04-24.)
      await reportDiscoveryProgress("chapter_puzzles", "discovery_started", {
        book_name: bookName,
        chapter_count: chapters.length,
        difficulty: difficulty,
        chapter_ids: chapters.map((c) => c.chapter_id),
        chapters: chapters.map((c, i) => ({
          chapter_number: i + 1,
          chapter_id: c.chapter_id,
          name: c.name,
        })),
      });

      // Navigate to first chapter
      const ch = disc.chapters[0];
      const delay = computeAdaptiveDelayMs();
      plog("WAIT", `${(delay / 1000).toFixed(1)}s before Ch.1 "${ch.name}"`);
      await waitMs(delay);
      plog("NEXT", `-> Ch.1 "${ch.name}" (${ch.chapter_id})`);
      location.href = buildChapterUrl(disc.book_id, ch.chapter_id);
      return;
    }

    // --- CHAPTER PUZZLE SCRAPING ---
    if (bookDiscovery.phase === "chapter_puzzles" && bookPath.type === "chapter") {
      await waitMs(1500); // let page JS settle

      const ch = bookDiscovery.chapters[bookDiscovery.current_chapter_idx];
      const chNum = ch ? ch.chapter_number : "?";

      // R2a: hard skip if this chapter is flagged.
      // ----------------------------------------------------------
      // The server flips `skip_status` to:
      //   - "auto_empty" after EMPTY_ATTEMPT_THRESHOLD page-1 renders
      //     produced zero puzzles (likely a deleted/broken chapter), OR
      //   - "manual" when the user runs `skip-chapter` CLI.
      // Either way we walk forward to the next non-skipped chapter
      // without touching the network for this one.
      if (ch && ch.skip_status) {
        plog(
          "SKIP",
          `Ch.${chNum} flagged ${ch.skip_status}` +
          (ch.skip_reason ? ` (${ch.skip_reason})` : "") +
          ` — jumping past`,
        );
        await reportDiscoveryProgress("chapter_puzzles", "chapter_skipped", {
          chapter_idx: bookDiscovery.current_chapter_idx,
          chapter_id: ch.chapter_id,
          chapter_number: ch.chapter_number,
          chapter_name: ch.name || "",
          reason: ch.skip_status,
        });
        if (bookDiscovery.current_chapter_idx < bookDiscovery.chapters.length - 1) {
          bookDiscovery.current_chapter_idx += 1;
          bookDiscovery.current_page = 1;
          saveBookDiscovery(bookDiscovery);
          const next = bookDiscovery.chapters[bookDiscovery.current_chapter_idx];
          const delay = computeAdaptiveDelayMs();
          await waitMs(delay);
          // No `running` guard here on purpose: discovery is page-load
          // driven and the state has already been advanced + persisted.
          // Bailing out without navigating leaves the tab parked on a
          // skipped chapter, which is exactly the "why does it pause?"
          // bug we hit before. The `running` flag is a capture-loop
          // concept and does not apply to discovery navigation.
          plog("NEXT", `-> Ch.${next.chapter_number} "${next.name}" (post-skip)`);
          location.href = buildChapterUrl(bookDiscovery.book_id, next.chapter_id);
          return;
        }
        // No more chapters — fall through to the "all done" branch.
      }

      // R2b chapter-jump resume
      // ----------------------------------------------------------
      // If this chapter was fully scraped on a previous run we can
      // skip past it without re-scraping every page. Each chapter
      // tracks `scraped_pages` (set of page numbers we've completed)
      // plus `max_page_seen`. When all pages in 1..max_page_seen are
      // already scraped we navigate straight to the next chapter.
      // This makes re-running a partially complete discovery cheap
      // (one page-load per skipped chapter, not maxPage page-loads).
      if (ch && Array.isArray(ch.scraped_pages) && ch.max_page_seen > 0) {
        const allDone = ch.scraped_pages.length >= ch.max_page_seen;
        if (allDone) {
          plog("SKIP", `Ch.${chNum} already fully scraped (${ch.puzzle_ids.length} ids, ${ch.max_page_seen} pages) — jumping to next chapter`);
          await reportDiscoveryProgress("chapter_puzzles", "chapter_skipped", {
            chapter_idx: bookDiscovery.current_chapter_idx,
            chapter_name: ch.name || "",
            puzzle_count: ch.puzzle_ids.length,
          });
          if (bookDiscovery.current_chapter_idx < bookDiscovery.chapters.length - 1) {
            bookDiscovery.current_chapter_idx += 1;
            bookDiscovery.current_page = 1;
            saveBookDiscovery(bookDiscovery);
            const next = bookDiscovery.chapters[bookDiscovery.current_chapter_idx];
            const delay = computeAdaptiveDelayMs();
            await waitMs(delay);
            // No `running` guard — see post-skip note above.
            plog("NEXT", `-> Ch.${next.chapter_number} "${next.name}" (skip-ahead)`);
            location.href = buildChapterUrl(bookDiscovery.book_id, next.chapter_id);
            return;
          }
          // No more chapters — fall through into the "all done" branch below by faking maxPage state
        }
      }

      const entries = extractPuzzleEntriesFromDom();
      const ids = entries.map((e) => e.id);

      // Capture chapter number from page's pagedata.number (site-assigned)
      const pageChapterNum = extractChapterNumber();
      if (ch && pageChapterNum > 0) {
        ch.site_chapter_number = pageChapterNum;
      }

      // Empty-page detection: if page 1 of a chapter renders with zero
      // puzzle entries AND the pager reports ≤1 page, this is almost
      // certainly a broken/deleted chapter on 101weiqi (chapters 18 &
      // 19 of book 5120 are the canonical example). Tell the receiver
      // so it can bump the cross-run empty-attempt counter; after the
      // threshold the chapter gets `skip_status="auto_empty"` and the
      // R2a guard above stops re-visiting it on subsequent runs.
      const earlyMaxPage = extractMaxPage();
      if (
        ch
        && entries.length === 0
        && (bookDiscovery.current_page || 1) === 1
        && earlyMaxPage <= 1
      ) {
        plog(
          "WARN",
          `Ch.${chNum} rendered empty on page 1 (maxPage=${earlyMaxPage}) ` +
          `— reporting empty attempt`,
        );
        const resp = await reportDiscoveryProgress(
          "chapter_puzzles",
          "chapter_empty_attempt",
          {
            chapter_idx: bookDiscovery.current_chapter_idx,
            chapter_id: ch.chapter_id,
            chapter_number: ch.chapter_number,
            chapter_name: ch.name || "",
            max_page: earlyMaxPage,
          },
        );
        // The receiver echoes updated skip_status; if this attempt was
        // the one that crossed the threshold, ch.skip_status is now
        // set and the next iteration will follow the R2a fast-skip.
        // Either way, advance to the next chapter rather than
        // pointlessly paging through a known-empty one.
        if (
          bookDiscovery.current_chapter_idx <
          bookDiscovery.chapters.length - 1
        ) {
          bookDiscovery.current_chapter_idx += 1;
          bookDiscovery.current_page = 1;
          saveBookDiscovery(bookDiscovery);
          const next =
            bookDiscovery.chapters[bookDiscovery.current_chapter_idx];
          const delay = computeAdaptiveDelayMs();
          await waitMs(delay);
          // No `running` guard — see post-skip note above.
          plog(
            "NEXT",
            `-> Ch.${next.chapter_number} "${next.name}" (after-empty)`,
          );
          location.href = buildChapterUrl(bookDiscovery.book_id, next.chapter_id);
          return;
        }
        // Last chapter and it's empty — fall through into the done
        // branch by treating maxPage as 0 (no further pages).
      }

      if (ch) {
        // Initialize puzzle_positions map if missing
        if (!ch.puzzle_positions) ch.puzzle_positions = {};

        // Merge IDs (dedup, preserve order) and record per-chapter qindex
        const existing = new Set(ch.puzzle_ids);
        for (const entry of entries) {
          if (!existing.has(entry.id)) {
            ch.puzzle_ids.push(entry.id);
            existing.add(entry.id);
          }
          // Record per-chapter position (qindex from chapter page)
          if (entry.qindex > 0) {
            ch.puzzle_positions[entry.id] = entry.qindex;
          }
        }
      }

      const maxPage = extractMaxPage();
      // Determine the page actually rendered (which may differ from
      // bookDiscovery.current_page when the site overrides our request,
      // e.g. landing on the last page when ?page= is omitted).
      const actualPage =
        inferRenderedPage(entries, maxPage) ||
        bookPath.page ||
        bookDiscovery.current_page ||
        1;
      if (actualPage !== bookDiscovery.current_page) {
        plog(
          "WARN",
          `Ch.${chNum}: requested p.${bookDiscovery.current_page} but server rendered p.${actualPage} (inferred from qindex)`
        );
      }
      // Record this page as scraped + remember the chapter's max page.
      // Used by the R2 skip-ahead at the top of this handler on re-runs.
      if (ch) {
        if (!Array.isArray(ch.scraped_pages)) ch.scraped_pages = [];
        if (!ch.scraped_pages.includes(actualPage)) {
          ch.scraped_pages.push(actualPage);
        }
        if (maxPage > (ch.max_page_seen || 0)) ch.max_page_seen = maxPage;
      }
      plog(
        "GRAB",
        `Ch.${chNum} p.${actualPage}/${maxPage}: ${ids.length} IDs (total: ${ch ? ch.puzzle_ids.length : 0})`
      );

      // Telemetry: report chapter page progress
      await reportDiscoveryProgress("chapter_puzzles", "page_scraped", {
        chapter_idx: bookDiscovery.current_chapter_idx,
        chapter_name: ch ? ch.name : "",
        page: actualPage,
        requested_page: bookDiscovery.current_page,
        max_page: maxPage,
        ids_on_page: ids.length,
        ids_in_chapter: ch ? ch.puzzle_ids.length : 0,
      });

      // Decide next page using actualPage + scraped set (forward, then backward)
      const nextPage = pickNextChapterPage(
        ch ? ch.scraped_pages : [actualPage],
        maxPage,
        actualPage
      );

      if (nextPage != null) {
        // Still pages left in this chapter
        bookDiscovery.current_page = nextPage;
        saveBookDiscovery(bookDiscovery);
        const delay = computeAdaptiveDelayMs();
        const dir = nextPage > actualPage ? "forward" : "backward";
        plog(
          "WAIT",
          `${(delay / 1000).toFixed(1)}s before Ch.${chNum} p.${nextPage} (${dir} from p.${actualPage})`
        );
        await waitMs(delay);
        location.href = buildChapterUrl(bookDiscovery.book_id, ch.chapter_id, nextPage);
      } else if (bookDiscovery.current_chapter_idx < bookDiscovery.chapters.length - 1) {
        // Chapter just finished. Under the v5.38.0 interleaved flow we
        // submit a partial manifest containing every chapter discovered
        // so far, hand off to chapter-scoped capture for the chapter
        // we just completed, and let the capture-complete handler
        // resume discovery on the next chapter.
        const completedIdx = bookDiscovery.current_chapter_idx;
        const completedCh = bookDiscovery.chapters[completedIdx];
        plog(
          "DONE",
          `Ch.${completedCh.chapter_number} "${completedCh.name}" discovered ` +
          `(${(completedCh.puzzle_ids || []).length} ids) — ` +
          `submitting partial manifest and starting capture`,
        );
        await reportDiscoveryProgress("chapter_puzzles", "chapter_complete", {
          chapter_idx: completedIdx,
          chapter_id: completedCh.chapter_id,
          chapter_number: completedCh.chapter_number,
          chapter_name: completedCh.name || "",
          puzzle_count: (completedCh.puzzle_ids || []).length,
        });
        // Mark discovery as awaiting capture so a page reload doesn't
        // re-enter continueDiscovery while bookPlan is active.
        bookDiscovery.awaiting_capture = true;
        bookDiscovery.awaiting_chapter_idx = completedIdx;
        saveBookDiscovery(bookDiscovery);
        await submitBookManifest(bookDiscovery, {
          partial: true,
          scopeChapterId: completedCh.chapter_id,
        });
        return;
      } else {
        // Last chapter just finished. Submit final (partial:false) manifest
        // and hand off to chapter-scoped capture for the last chapter.
        const completedIdx = bookDiscovery.current_chapter_idx;
        const completedCh = bookDiscovery.chapters[completedIdx];
        const totalChapterIds = bookDiscovery.chapters.reduce((s, c) => s + c.puzzle_ids.length, 0);
        plog(
          "DONE",
          `Final chapter (Ch.${completedCh.chapter_number} "${completedCh.name}") discovered — ` +
          `submitting full manifest (${totalChapterIds} ids across ${bookDiscovery.chapters.length} chapters) ` +
          `and starting capture`,
        );
        bookDiscovery.phase = "done";
        bookDiscovery.awaiting_capture = true;
        bookDiscovery.awaiting_chapter_idx = completedIdx;
        saveBookDiscovery(bookDiscovery);

        await reportDiscoveryProgress("chapter_puzzles", "phase_complete", {
          chapter_count: bookDiscovery.chapters.length,
          total_ids: totalChapterIds,
        });
        await reportDiscoveryProgress("done", "discovery_complete", {
          chapter_count: bookDiscovery.chapters.length,
          chapter_ids: totalChapterIds,
        });

        await submitBookManifest(bookDiscovery, {
          partial: false,
          scopeChapterId: completedCh.chapter_id,
        });
      }
      return;
    }
  }

  async function submitBookManifest(disc, opts = {}) {
    // opts:
    //   partial            — bool, default false. When true, server merges
    //                        chapters by chapter_id and keeps discovery
    //                        status as "in_progress".
    //   scopeChapterId     — int|null. When set, after manifest is saved
    //                        startChapterCapture is invoked with that
    //                        chapter as its sole capture scope (interleaved
    //                        discovery↔capture flow).
    const partial = !!opts.partial;
    const scopeChapterId = (opts.scopeChapterId == null)
      ? null : Number(opts.scopeChapterId);

    const totalIds = disc.chapters.reduce((s, c) => s + (c.puzzle_ids || []).length, 0);
    const manifest = {
      book_id: disc.book_id,
      book_name: disc.book_name,
      difficulty: disc.difficulty || "",
      chapters: disc.chapters,
      partial: partial,
      discovered_at: new Date().toISOString(),
    };

    const tag = partial ? "partial" : "final";
    plog("SEND", `Submitting ${tag} manifest for book ${disc.book_id} "${disc.book_name}" (${disc.chapters.length} chapters / ${totalIds} ids)`);
    updateStatus(
      partial
        ? `Saving partial manifest (${disc.chapters.length} chapters)...`
        : "Saving final book manifest to backend...",
      "#4fc3f7",
    );

    let result;
    try {
      result = await http("POST", "/book/manifest", manifest);
    } catch (err) {
      plog("ERR", `Manifest POST failed: ${err.message}`);
      updateStatus("Manifest save failed — is receiver running?", "#f44336");
      return;
    }
    if (result && result.error) {
      plog("ERR", `Manifest save failed: ${result.error}`);
      updateStatus(`Manifest error: ${result.error}`, "#f44336");
      return;
    }
    plog("DONE", `Manifest saved (${tag}): ${result.path || "(ok)"}`);

    // Hand off to chapter-scoped capture if requested. We do NOT clear
    // bookDiscovery here — the capture-complete handler reads it back to
    // resume discovery on the next chapter.
    if (scopeChapterId != null) {
      await startChapterCapture(disc.book_id, 0, {
        scopeChapterId: scopeChapterId,
      });
      return;
    }

    // Legacy / non-interleaved final-only path (kept for compat with
    // any caller that wants a single end-of-discovery handoff).
    updateStatus(
      `Manifest saved for "${disc.book_name}" — ready to capture`,
      "#4caf50",
    );
    GM_notification({
      text: `Book "${disc.book_name}" discovered! ${totalIds} puzzles. Starting capture...`,
      title: "YenGo",
      timeout: 10000,
    });
    clearBookDiscovery();
    await startChapterCapture(disc.book_id);
  }

  //#endregion 5. BOOK DISCOVERY

  //#region 6. BOOK CAPTURE
  // -- Chapter capture: walk manifest.chapters[].puzzle_ids in order ----
  //
  // Why chapter mode (and not level-order):
  //   * 101weiqi's level-order ranking is recomputed periodically as
  //     users solve puzzles, so a saved `levelorder_ids` array can drift
  //     out of sync with the live page. Chapter membership and intra-
  //     chapter order are stable.
  //   * Output organization (chapter N, puzzle M) matches the source
  //     book's pedagogical structure, which is what humans expect when
  //     browsing the imported collection later.
  //
  // Resume rule (per user spec): walk the flattened sequence and start
  // at the first puzzle whose id is NOT in known_ids. If everything is
  // already captured, abort with a friendly message.

  /**
   * v5.38.0 interleaved-flow helper.
   *
   * Called when a chapter-scoped capture finishes (either because every
   * puzzle in the scoped chapter is captured, or because the chapter
   * was already complete on entry). Tears down the chapter scope flag
   * on bookDiscovery, advances the discovery cursor past the chapters
   * we've already swept, and either:
   *   (a) navigates to the next undiscovered chapter's listing page
   *       (continueDiscovery picks up from the page-load), OR
   *   (b) emits the final completion notification when every chapter
   *       in the book has been discovered AND captured.
   */
  async function _resumeDiscoveryAfterChapter(completedChapterId) {
    if (!bookDiscovery || !Array.isArray(bookDiscovery.chapters)) {
      plog(
        "INFO",
        "_resumeDiscoveryAfterChapter: no bookDiscovery state — nothing to resume",
      );
      return;
    }

    // Clear the awaiting_capture latch — discovery is in charge again.
    bookDiscovery.awaiting_capture = false;
    delete bookDiscovery.awaiting_chapter_idx;

    // Find the index of the chapter we just captured so we can advance
    // past it. Match by chapter_id (stable identity).
    const completedIdx = bookDiscovery.chapters.findIndex(
      (c) => Number(c.chapter_id) === Number(completedChapterId),
    );
    const totalChapters = bookDiscovery.chapters.length;

    if (completedIdx < 0) {
      plog(
        "WARN",
        `_resumeDiscoveryAfterChapter: chapter_id=${completedChapterId} not in bookDiscovery.chapters — abandoning interleave`,
      );
      clearBookDiscovery();
      return;
    }

    if (completedIdx >= totalChapters - 1) {
      // Last chapter — book is fully discovered AND captured.
      // This is the only place stopRunning() should fire in the
      // interleaved flow; intermediate chapter handoffs keep the
      // session alive so autoStart's explicit-resume guard doesn't
      // bail after the next page reload.
      const name = bookDiscovery.book_name || `Book ${bookDiscovery.book_id}`;
      const total = bookDiscovery.chapters.reduce(
        (s, c) => s + (c.puzzle_ids || []).length, 0,
      );
      plog("DONE", `Book "${name}" fully discovered + captured (${total} puzzles across ${totalChapters} chapters)`);
      // Post-capture session summary for full-book completion.
      {
        const summaryDurationMs = bookPlan && bookPlan.started_at
          ? Date.now() - new Date(bookPlan.started_at).getTime() : 0;
        const summaryDurationMin = (summaryDurationMs / 60000).toFixed(1);
        plog("SUMMARY", "\u2550\u2550\u2550 Session Summary \u2550\u2550\u2550");
        plog("SUMMARY", `Captured: ${stats.ok}, Skipped: ${stats.skipped}, Errors: ${stats.error}`);
        plog("SUMMARY", `Duration: ${summaryDurationMin} min`);
        reportBookEvent("session_summary", {
          captured: stats.ok || 0,
          skipped: stats.skipped || 0,
          errors: stats.error || 0,
          duration_ms: summaryDurationMs,
          total_in_manifest: total,
          start_idx: 0,
          end_idx: total,
        });
      }
      updateStatus(`"${name}" — book complete (${total} puzzles)`, "#4caf50");
      GM_notification({
        text: `Book "${name}" complete: ${total} puzzles across ${totalChapters} chapters.`,
        title: "YenGo",
        timeout: 15000,
      });
      stopRunning();
      clearBookDiscovery();
      return;
    }

    // Advance discovery cursor to the next chapter and navigate.
    bookDiscovery.current_chapter_idx = completedIdx + 1;
    bookDiscovery.current_page = 1;
    saveBookDiscovery(bookDiscovery);

    const next = bookDiscovery.chapters[bookDiscovery.current_chapter_idx];
    const delay = computeAdaptiveDelayMs();
    plog(
      "WAIT",
      `${(delay / 1000).toFixed(1)}s before resuming discovery on Ch.${next.chapter_number} "${next.name}"`,
    );
    updateStatus(
      `Discovering Ch.${next.chapter_number}/${totalChapters} "${next.name}"`,
      "#4fc3f7",
    );
    await waitMs(delay);
    plog(
      "NEXT",
      `-> Ch.${next.chapter_number} "${next.name}" (${next.chapter_id}) (post-capture)`,
    );
    location.href = buildChapterUrl(bookDiscovery.book_id, next.chapter_id);
  }

  async function startChapterCapture(bookId, requestedSeqIdx, opts = {}) {
    // opts.scopeChapterId — when set, restrict chapter_seq to puzzles
    // belonging to that single chapter_id (interleaved discovery↔
    // capture flow, v5.38.0). Discovery state is preserved so the
    // capture-complete handler can resume on the next chapter.
    // Identity uses chapter_id (not index) because manifest order may
    // differ from discovery order after server-side merging.
    const scopeChapterId = (opts.scopeChapterId == null)
      ? null : Number(opts.scopeChapterId);

    clearQdayPlan();
    if (scopeChapterId == null) {
      // Legacy full-book capture path: discovery is finished and we
      // own the whole sweep, so the discovery checkpoint can be
      // dropped to keep storage tidy.
      clearBookDiscovery();
    }

    // Stop server-side queue to avoid auto-detection conflict.
    try { await http("GET", "/queue/stop"); } catch (_) {}

    let manifest;
    try {
      manifest = await http("GET", `/book/${bookId}/manifest`);
    } catch (err) {
      plog("ERR", `Cannot load manifest for chapter capture: ${err.message}`);
      updateStatus("Manifest fetch failed \u2014 is receiver running?", "#f44336");
      return;
    }
    if (!manifest || manifest.error) {
      plog("ERR", `Manifest missing for book ${bookId} \u2014 cannot start chapter capture`);
      updateStatus(`No manifest for book ${bookId} \u2014 run discovery first`, "#f44336");
      return;
    }

    const chapters = manifest.chapters || [];
    if (chapters.length === 0) {
      plog("ERR", `Manifest for book ${bookId} has no chapters \u2014 cannot capture (re-run discovery)`);
      updateStatus(`No chapters for book ${bookId} \u2014 re-run discovery`, "#f44336");
      return;
    }

    // Pre-capture chapter audit: show per-chapter captured/remaining counts.
    const chapterAudit = manifest.chapter_audit || [];
    if (chapterAudit.length > 0) {
      plog("AUDIT", "\u2550\u2550\u2550 Pre-capture chapter audit \u2550\u2550\u2550");
      let totalRemaining = 0;
      chapterAudit.forEach((ca) => {
        const status = ca.remaining === 0
          ? "\u2713 complete"
          : `${ca.remaining} remaining`;
        const pidsHint = (ca.remaining > 0 && ca.remaining <= 5)
          ? ` (pids: ${ca.remaining_pids.join(", ")})`
          : "";
        plog("AUDIT",
          `  Ch.${ca.chapter_number}: "${ca.chapter_name}" \u2014 ` +
          `${ca.total} total, ${ca.captured} captured, ${status}${pidsHint}`
        );
        totalRemaining += ca.remaining;
      });
      plog("AUDIT", `Total remaining: ${totalRemaining}`);
    }

    // Flatten chapters into a single sequence of (chapter_idx, pos, pid).
    // We intentionally store chapter_name pre-translated by the receiver
    // so the userscript never has to call the translator itself.
    // chapter_id is REQUIRED here — chapter capture navigates via the
    // chapter-listing URL (/book/{book_id}/{chapter_id}/) and clicks the
    // puzzle entry inside, never via direct /q/{pid}/ jumps (which look
    // like bot behavior to the site and trigger throttling).
    const chapterSeq = [];
    chapters.forEach((ch, chIdx) => {
      const pids = ch.puzzle_ids || [];
      pids.forEach((pid, posIdx) => {
        chapterSeq.push({
          pid: Number(pid),
          chapter_idx: chIdx,
          chapter_id: Number(ch.chapter_id) || null,
          chapter_number: ch.chapter_number || (chIdx + 1),
          chapter_name: ch.name || "",
          pos_in_chapter: posIdx + 1,
          // 1-based position across the (chapter-ordered) sequence.
          // Matches book.json `pos` when there are no cross-chapter
          // pid duplicates, which is the overwhelming common case.
          global_pos: chapterSeq.length + 1,
        });
      });
    });

    if (chapterSeq.length === 0) {
      plog("ERR", "Manifest chapters have no puzzle_ids \u2014 cannot start");
      updateStatus("Manifest chapters are empty \u2014 re-run discovery", "#f44336");
      return;
    }

    // v5.38.0 interleaved flow: when scopeChapterId is set, restrict
    // the working sequence to that single chapter so the capture loop
    // stops at chapter boundary and hands control back to discovery.
    let workingSeq = chapterSeq;
    if (scopeChapterId != null) {
      workingSeq = chapterSeq.filter((e) => e.chapter_id === scopeChapterId);
      if (workingSeq.length === 0) {
        plog(
          "ERR",
          `startChapterCapture: scope chapter_id=${scopeChapterId} has no puzzles in manifest — cannot start`,
        );
        updateStatus(
          `Scope chapter ${scopeChapterId} has no puzzles — re-run discovery`,
          "#f44336",
        );
        return;
      }
      plog(
        "INFO",
        `Chapter-scoped capture: chapter_id=${scopeChapterId} ` +
        `(${workingSeq.length} puzzles)`,
      );
    }

    const knownIds = new Set((manifest.known_ids || []).map(Number));
    const bookName = manifest.book_name || `Book ${bookId}`;

    // Pick start index: the later of caller-requested and first uncaptured.
    let firstUncap = -1;
    for (let i = 0; i < workingSeq.length; i++) {
      if (!knownIds.has(workingSeq[i].pid)) { firstUncap = i; break; }
    }
    if (firstUncap === -1) {
      if (scopeChapterId != null) {
        // Whole chapter is already captured (e.g. previous run finished
        // the chapter before crashing). Skip directly to next-chapter
        // resume rather than alerting.
        plog(
          "INFO",
          `Scope chapter_id=${scopeChapterId} already fully captured ` +
          `(${workingSeq.length} puzzles) — resuming discovery on next chapter`,
        );
        updateStatus(
          `Chapter ${scopeChapterId} already complete — resuming discovery`,
          "#4caf50",
        );
        await _resumeDiscoveryAfterChapter(scopeChapterId);
        return;
      }
      alert(`Book "${bookName}" is already fully captured! (${knownIds.size}/${workingSeq.length})`);
      updateStatus(`"${bookName}" \u2014 already complete`, "#4caf50");
      return;
    }
    const startIdx = Math.max(requestedSeqIdx || 0, firstUncap);

    const startEntry = workingSeq[startIdx];
    const plan = {
      active: true,
      mode: "chapter",
      book_id: bookId,
      book_name: bookName,
      chapter_seq: workingSeq,
      current_seq_idx: startIdx,
      total_puzzles: workingSeq.length,
      captured_ids: [...knownIds],
      captured_count: knownIds.size,
      started_at: new Date().toISOString(),
      // v5.38.0 interleave bookkeeping:
      scope_chapter_id: scopeChapterId,
      // Shape compat with manifest-mode consumers:
      puzzle_ids: workingSeq.map((e) => e.pid),
      puzzle_lookup: {},
      current_idx: startIdx,
    };

    saveBookPlan(plan);
    claimOwnership();
    if (!startRunning()) return;

    const remaining = chapterSeq.length - knownIds.size;
    plog("START", "════════════ SESSION START ════════════");
    plog("START", `Mode: chapter | Book: "${bookName}" (id=${bookId})`);
    plog("START", `Start: Ch.${startEntry.chapter_number} "${startEntry.chapter_name}" pos ${startEntry.pos_in_chapter} (pid=${startEntry.pid})`);
    plog("START", `Progress: ${knownIds.size}/${chapterSeq.length} captured, ${remaining} remaining`);
    updateStatus(
      `Chapter capture: "${bookName}" — Ch.${startEntry.chapter_number} pos ${startEntry.pos_in_chapter} (${knownIds.size}/${chapterSeq.length})`,
      "#4fc3f7",
    );

    // Entry point: navigate to the chapter LISTING page of the start
    // entry's chapter. The chapter-listing handler in autoStart() will
    // then locate the puzzle's <a> link and click it — producing a real
    // navigation with a chapter-page Referer, which is how a human
    // browses the book. We DO NOT use buildBookPuzzleUrl(pid) here
    // because direct /q/{pid}/ hits without a chapter Referer get
    // throttled by 101weiqi.
    const curBp = parseBookPath();
    const onTargetChapter =
      curBp
      && curBp.type === "chapter"
      && curBp.book_id === bookId
      && curBp.chapter_id === startEntry.chapter_id;
    if (onTargetChapter) {
      // Already on the right chapter page — the autoStart handler
      // (called by capture-loop bootstrap) will click the entry.
      await clickPuzzleInChapterListing(startEntry.pid);
      return;
    }
    if (!startEntry.chapter_id) {
      // Manifest is missing chapter_id — most likely it was discovered
      // before this field was required. Tell the user to re-discover.
      plog("ERR", `Manifest for book ${bookId} has no chapter_id — cannot start chapter capture`);
      updateStatus(`Manifest missing chapter_id — re-run discovery`, "#f44336");
      stopRunning();
      return;
    }
    const startPage = chapterUsesFallbackPagination(startEntry.chapter_id)
      ? 1
      : targetChapterPageForEntry(startEntry);
    location.href = buildChapterUrl(bookId, startEntry.chapter_id, startPage);
  }

  /**
   * Locate a puzzle's anchor in the current chapter-listing page and
   * click it (with a brief human-like delay + scroll-into-view). If the
   * puzzle is not on the current page, paginate to the next chapter
   * page and recurse. Used by chapter-capture mode in place of direct
   * /q/{pid}/ navigation.
   */
  async function clickPuzzleInChapterListing(pid) {
    await waitMs(1200); // let chapter-page Alpine state hydrate
    if (!running) { plog("INFO", "clickPuzzle: paused before scan"); return; }

    const entries = extractPuzzleEntriesFromDom();
    const onPage = entries.some((e) => Number(e.id) === Number(pid));
    const bp = parseBookPath();
    if (!bp || bp.type !== "chapter") {
      plog("WARN", `clickPuzzle: not on a chapter listing (path=${location.pathname})`);
      return;
    }

    if (!onPage) {
      const maxPage = extractMaxPage();
      const currentPage = bp.page || 1;

      // Learn the live page size from DOM (B's self-correcting half).
      // Only revises upward on the last page to avoid undercounting.
      if (entries.length > 0) {
        recordObservedPerPage(entries.length, currentPage, maxPage);
      }

      // Page-math sanity check (C-as-fallback). If the live DOM has
      // entries but ZERO of them match any pid this chapter expects
      // (per chapter_seq), then our targetPage computation pointed us
      // at the wrong page. Don't prune (would falsely discard valid
      // pending pids). Instead enable sequential-pagination fallback
      // for this chapter and head back to page 1 to walk forward.
      if (
        entries.length > 0 &&
        bookPlan && Array.isArray(bookPlan.chapter_seq) &&
        !chapterUsesFallbackPagination(bp.chapter_id)
      ) {
        const visiblePidsAll = new Set(entries.map((e) => Number(e.id)));
        const chapterSeqPids = bookPlan.chapter_seq
          .filter((e) => e.chapter_id === bp.chapter_id)
          .map((e) => Number(e.pid));
        if (chapterSeqPids.length > 0) {
          const overlap = chapterSeqPids.filter((p) => visiblePidsAll.has(p)).length;
          if (overlap === 0) {
            markChapterFallbackPagination(bp.chapter_id);
            const delay = computeAdaptiveDelayMs();
            plog("WARN", `clickPuzzle: page math mismatch on Ch.${bp.chapter_id} p.${currentPage} (visible=${entries.length}, none of ${chapterSeqPids.length} expected pids present) — switching to sequential pagination, restarting at page 1`);
            updateStatus(`Page math wrong on Ch.${bp.chapter_id} — falling back`, "#ff9800");
            await waitMs(delay);
            if (!running) return;
            if (currentPage !== 1) {
              location.href = buildChapterUrl(bp.book_id, bp.chapter_id, 1);
            } else {
              // Already on page 1 with no overlap — chapter genuinely
              // doesn't contain our pids on its first page; let the
              // existing flow prune/advance from here.
              setTimeout(() => { try { autoStart(); } catch (_) {} }, 500);
            }
            return;
          }
        }
      }

      // Bulk-prune any chapter_seq entries that should be on the CURRENT
      // listing page (per manifest pos_in_chapter -> page mapping) but
      // are missing from the live DOM. Those are deleted on the site.
      // Without this, every gap costs ~1.5s of "skip then re-resume".
      if (bookPlan && Array.isArray(bookPlan.chapter_seq) && entries.length > 0) {
        const visiblePids = new Set(entries.map((e) => Number(e.id)));
        const seq = bookPlan.chapter_seq;
        let scan = bookPlan.current_seq_idx || 0;
        let prunedHere = 0;
        while (scan < seq.length) {
          const e = seq[scan];
          if (e.chapter_id !== bp.chapter_id) break;
          const ePage = chapterPageForPosition(e.pos_in_chapter || 0);
          if (ePage !== currentPage) break; // stop at first entry off this page
          if (visiblePids.has(Number(e.pid))) break; // hit a real one — let normal flow handle it
          scan++;
          prunedHere++;
        }
        if (prunedHere > 0) {
          bookPlan.current_seq_idx = scan;
          bookPlan.current_idx = scan;
          saveBookPlan(bookPlan);
          plog("WARN", `clickPuzzle: bulk-pruned ${prunedHere} entr${prunedHere === 1 ? "y" : "ies"} missing from Ch.${bp.chapter_id} p.${currentPage} DOM (visible=${visiblePids.size})`);
          updateStatus(`Pruned ${prunedHere} stale Ch.${bp.chapter_id} p.${currentPage} entries`, "#ff9800");
          setTimeout(() => { try { autoStart(); } catch (_) {} }, 800);
          return;
        }
      }

      // Prefer a direct jump to the page containing the target puzzle
      // (computed from the manifest's per-chapter position) instead of
      // walking one page at a time. Falls back to single-step pagination
      // when we have no manifest hint or when the computed page is
      // already the current page (something else is off — try +1).
      let targetPage = 0;
      if (bookPlan && Array.isArray(bookPlan.chapter_seq)) {
        // Restrict to the chapter we're currently navigating; pid alone
        // is ambiguous when the manifest contains cross-chapter duplicate
        // pids (book 5120 has 40 such duplicates) and Array.find returns
        // the first match, which can point at an unrelated chapter.
        const seqEntry = bookPlan.chapter_seq.find(
          (e) =>
            Number(e.pid) === Number(pid) &&
            (!bp.chapter_id || e.chapter_id === bp.chapter_id)
        );
        if (seqEntry) {
          // Honour per-chapter fallback flag: when set, disable the
          // page-jump optimisation and let the step+1 fallback below
          // walk pages sequentially for the rest of this chapter.
          targetPage = chapterUsesFallbackPagination(bp.chapter_id)
            ? 0
            : targetChapterPageForEntry(seqEntry);
        }
      }
      const fallbackPage = (bp.page || 1) + 1;
      const nextPage = targetPage && targetPage !== (bp.page || 1)
        ? targetPage
        : fallbackPage;
      if (nextPage > maxPage) {
        // Bulk-prune ALL stale entries for this chapter in one pass.
        // The chapter listing has at most `maxPage * effectivePerPage()`
        // slots, so any chapter_seq entry with pos_in_chapter beyond that
        // can't possibly exist on the live site.
        // Additionally, collect pids visible in the current DOM and prune
        // any entry pointing to this chapter whose pid we've never seen.
        // (Per-pid skipping for entries within range is handled below.)
        const ccap = maxPage * effectivePerPage();
        let pruned = 0;
        if (bookPlan && Array.isArray(bookPlan.chapter_seq)) {
          const seq = bookPlan.chapter_seq;
          const startIdx = bookPlan.current_seq_idx || 0;
          // Single per-pid bump (the one we were trying to click).
          // Forward search constrained to the current chapter to avoid
          // cross-chapter false matches on duplicate pids.
          let missingIdx = -1;
          for (let i = startIdx; i < seq.length; i++) {
            if (
              Number(seq[i].pid) === Number(pid) &&
              (!bp.chapter_id || seq[i].chapter_id === bp.chapter_id)
            ) {
              missingIdx = i;
              break;
            }
          }
          if (missingIdx >= 0) {
            bookPlan.current_seq_idx = missingIdx + 1;
            bookPlan.current_idx = missingIdx + 1;
            pruned++;
          }
          // Bulk-bump any *contiguous-by-chapter* tail with pos beyond cap.
          let scan = bookPlan.current_seq_idx || 0;
          while (
            scan < seq.length &&
            seq[scan].chapter_id === bp.chapter_id &&
            (seq[scan].pos_in_chapter || 0) > ccap
          ) {
            scan++;
            pruned++;
          }
          if (scan !== (bookPlan.current_seq_idx || 0)) {
            bookPlan.current_seq_idx = scan;
            bookPlan.current_idx = scan;
          }
          saveBookPlan(bookPlan);
        }
        plog("WARN", `clickPuzzle: pid ${pid} absent on Ch.${bp.chapter_id} (maxPage=${maxPage}, cap=${ccap}); pruned ${pruned} stale entr${pruned === 1 ? "y" : "ies"} -> seq idx ${bookPlan.current_seq_idx}`);
        updateStatus(`Pruned ${pruned} stale Ch.${bp.chapter_id} entries — advancing`, "#ff9800");
        setTimeout(() => { try { autoStart(); } catch (_) {} }, 1500);
        return;
      }
      const delay = computeAdaptiveDelayMs();
      const hint = targetPage ? "manifest hint" : "step+1";
      plog("WAIT", `${(delay / 1000).toFixed(1)}s before chapter page ${nextPage} (${hint}, looking for ${pid})`);
      await waitMs(delay);
      if (!running) return;
      location.href = buildChapterUrl(bp.book_id, bp.chapter_id, nextPage);
      return;
    }

    // Try selector variants. The site's chapter-listing anchors use
    // /book/{book_id}/{chapter_id}/{anchor_id}/ format where anchor_id
    // is the puzzle's `qid` (NOT publicid). For most books qid==publicid
    // so they look identical, but books like 25369 have a separate qid
    // namespace (qid 295990 -> publicid 261436). We resolve the anchor
    // id from the live DOM entry whose publicid matches our target pid.
    // We try most-specific first and fall back to broader matches.
    const matchingEntry = entries.find((e) => Number(e.id) === Number(pid));
    const anchorId = matchingEntry && matchingEntry.anchorId
      ? matchingEntry.anchorId
      : pid;
    const chapterPrefix = `/book/${bp.book_id}/${bp.chapter_id}/${anchorId}`;
    const candidates = [
      `a[href="${chapterPrefix}/"]`,
      `a[href="${chapterPrefix}"]`,
      `a[href*="${chapterPrefix}/"]`,
      `a[href*="${chapterPrefix}"]`,
      // Legacy fallback in case the site changes back to /q/ format.
      // Try both anchor and public ids; either may resolve.
      `a[href="/q/${anchorId}/"]`,
      `a[href*="/q/${anchorId}/"]`,
      `a[href="/q/${pid}/"]`,
      `a[href*="/q/${pid}/"]`,
    ];
    let link = null;
    for (const sel of candidates) {
      link = document.querySelector(sel);
      if (link) break;
    }
    if (!link) {
      const idHint = anchorId !== pid ? `pid=${pid} anchor=${anchorId}` : `pid=${pid}`;
      plog("WARN", `clickPuzzle: no anchor (${idHint}) on Ch.${bp.chapter_id} p.${bp.page || 1} — DOM has ${entries.length} entries; tried ${candidates.length} selectors`);
      updateStatus(`Anchor missing for ${pid} — retry in 3s`, "#ff9800");
      // Don't silently freeze — re-tick so resume can either retry or
      // bump past the entry on next pass.
      setTimeout(() => { try { autoStart(); } catch (_) {} }, 3000);
      return;
    }

    // Human-like: scroll, wait, click.
    try { link.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (_) {}
    const clickDelay = randomBetween(700, 1700);
    await waitMs(clickDelay);
    if (!running) { plog("INFO", "clickPuzzle: paused before click"); return; }
    plog("CLICK", `Clicking puzzle ${pid} from chapter listing (Ch.${bp.chapter_id})`);
    link.click();
  }

  // -- Book sweep: Confirmation overlay for /book/ pages -------------

  async function showBookDiscoveryOverlay(bookId) {
    if (document.getElementById("yengo-book-overlay")) return;

    const bookName = extractBookName() || `Book ${bookId}`;
    const chapters = extractChaptersFromDom();

    // Check backend for existing discovery state
    const existing = await checkBackendDiscoveryState(bookId);

    const overlay = document.createElement("div");
    overlay.id = "yengo-book-overlay";
    overlay.style.cssText =
      "position:fixed;top:0;left:0;right:0;bottom:0;z-index:1000000;" +
      "background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;";

    const dialog = document.createElement("div");
    dialog.style.cssText =
      "background:#1e1e2e;color:#e0e0e0;border-radius:8px;padding:20px;max-width:500px;" +
      "width:90%;font:14px/1.6 monospace;";

    const title = document.createElement("h2");
    title.style.cssText = "margin:0 0 12px;color:#4fc3f7;";
    title.textContent = "Discover Book for YenGo?";
    dialog.appendChild(title);

    const info = document.createElement("p");
    info.style.cssText = "color:#ccc;margin:0 0 8px;";
    info.textContent = `"${bookName}" — ${chapters.length} chapters detected`;
    dialog.appendChild(info);

    // Show existing backend state if any
    if (existing.status === "complete") {
      const existInfo = document.createElement("p");
      existInfo.style.cssText = "color:#4caf50;margin:0 0 8px;font-size:12px;";
      const m = existing.manifest;
      const chCount = (m.chapters || []).length;
      const totalIds = (m.chapters || []).reduce((s, c) => s + (c.puzzle_ids || []).length, 0);
      existInfo.textContent = `Already discovered: ${chCount} chapters, ${totalIds} puzzle IDs. You can skip to capture.`;
      dialog.appendChild(existInfo);
    } else if (existing.status === "partial") {
      const existInfo = document.createElement("p");
      existInfo.style.cssText = "color:#ff9800;margin:0 0 8px;font-size:12px;";
      const cp = existing.checkpoint;
      existInfo.textContent = `Partial discovery found (phase: ${cp.phase}, Ch.${(cp.current_chapter_idx || 0) + 1}). Can resume from checkpoint.`;
      dialog.appendChild(existInfo);
    }

    const desc = document.createElement("p");
    desc.style.cssText = "color:#888;margin:0 0 16px;font-size:12px;";
    desc.textContent = "Phase 1: Navigate chapters to build manifest. Phase 2: Capture each puzzle in chapter order.";
    dialog.appendChild(desc);

    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:12px;justify-content:flex-end;flex-wrap:wrap;";

    const btnStyle =
      "padding:8px 16px;border:none;border-radius:4px;cursor:pointer;font:14px monospace;";

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.style.cssText = btnStyle + "background:#333;color:#e0e0e0;";
    cancelBtn.onclick = () => overlay.remove();
    btnRow.appendChild(cancelBtn);

    // If already discovered, offer "Capture (chapter mode)".
    if (existing.status === "complete") {
      const m = existing.manifest || {};
      const hasChapters = Array.isArray(m.chapters) && m.chapters.length > 0
        && m.chapters.some((c) => Array.isArray(c.puzzle_ids) && c.puzzle_ids.length > 0);

      if (hasChapters) {
        const chapterBtn = document.createElement("button");
        chapterBtn.textContent = "Capture (chapter mode)";
        chapterBtn.title = "Walk chapters in order via AJAX Next within each chapter, navigating to chapter listings only at boundaries";
        chapterBtn.style.cssText = btnStyle + "background:#ba68c8;color:#1a1a2e;font-weight:bold;";
        chapterBtn.onclick = () => {
          overlay.remove();
          startChapterCapture(bookId);
        };
        btnRow.appendChild(chapterBtn);
      }
    }

    // If partial, offer "Resume" button
    if (existing.status === "partial") {
      const resumeBtn = document.createElement("button");
      resumeBtn.textContent = "Resume Discovery";
      resumeBtn.style.cssText = btnStyle + "background:#ff9800;color:#1a1a2e;font-weight:bold;";
      resumeBtn.onclick = () => {
        overlay.remove();
        // continueDiscovery will detect checkpoint and resume
        continueDiscovery();
      };
      btnRow.appendChild(resumeBtn);
    }

    const startBtn = document.createElement("button");
    startBtn.textContent = existing.status !== "none" ? "Restart Discovery" : "Start Discovery";
    startBtn.style.cssText = btnStyle + "background:#4fc3f7;color:#1a1a2e;font-weight:bold;";
    startBtn.onclick = () => {
      overlay.remove();
      clearBookDiscovery();
      clearBookPlan();
      continueDiscovery();
    };
    btnRow.appendChild(startBtn);

    dialog.appendChild(btnRow);
    overlay.appendChild(dialog);
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    document.body.appendChild(overlay);
  }
  function getQqdata() {
    // Alpine store is the authoritative source during SPA navigation
    try {
      const qipan = unsafeWindow.Alpine && unsafeWindow.Alpine.store("qipan");
      if (qipan && qipan.qqdata && qipan.qqdata.publicid) {
        return qipan.qqdata;
      }
    } catch (_) {}
    // Fall back to global qqdata (set on full page load)
    if (typeof unsafeWindow.qqdata !== "undefined") {
      return unsafeWindow.qqdata;
    }
    return null;
  }

  function isQqdataReady() {
    const qq = getQqdata();
    if (!qq) return false;
    // Accept if content field is available (decoded array or encoded string)
    if (Array.isArray(qq.content) && qq.content.length >= 2
        && Array.isArray(qq.content[0]) && qq.content[0].length > 0) return true;
    if (typeof qq.content === "string" && qq.content.length > 10) return true;
    // Fallback: non-empty prepos
    if (qq.prepos && Array.isArray(qq.prepos) && qq.prepos.length >= 2
        && (qq.prepos[0].length > 0 || qq.prepos[1].length > 0)) return true;
    return false;
  }

  // -- CAPTCHA / error detection (querySelector, no innerHTML) ----
  function isCaptcha() {
    if (getQqdata()) return false;
    return !!(
      document.querySelector('script[src*="TCaptcha"]') ||
      document.querySelector('script[src*="turing.captcha.qcloud.com"]')
    );
  }

  function isLogin() {
    if (getQqdata()) return false;
    return !!(
      document.querySelector('#login-form') ||
      document.querySelector('a[href*="/accounts/signin"]') ||
      document.querySelector('[action*="denglu"], [href*="denglu"]') ||
      (document.body.textContent && document.body.textContent.includes("denglu"))
    );
  }

  //#endregion 6. BOOK CAPTURE

  //#region 7. NAVIGATION
  // -- Navigate to next (prefer site's AJAX Next, fallback to URL) -
  async function goNext() {
    if (!isOwnerTab()) return;
    // Hard stop — if the user paused/stopped before we even started
    // navigating, do nothing. Every `await` point inside this function
    // re-checks `running` so a pause mid-wait aborts the navigation
    // before any URL change or AJAX click happens.
    if (!running) {
      plog("INFO", "goNext: not running — navigation suppressed");
      return;
    }

    // ── Chapter mode: walk pre-flattened chapter_seq in order ──
    // Skip-list resume: any pid already in captured_ids is jumped over
    // without navigating, so re-runs cost only the cost of advancing
    // the index. The actual next puzzle is the first uncaptured one
    // strictly after the current index.
    if (isBookCaptureActive() && isChapterMode()) {
      // Mark current puzzle as captured. IDENTITY: captured_ids is a
      // dedup set keyed by publicid (matches manifest pid).
      const curId = Number(getPublicId());
      if (curId && !bookPlan.captured_ids.includes(curId)) {
        bookPlan.captured_ids.push(curId);
        bookPlan.captured_count = bookPlan.captured_ids.length;
      }

      // Periodic captured_ids refresh from server manifest.
      // Catches cross-book duplicates captured during this session
      // (e.g. another book containing the same pid was completed
      // since session start). Cheap: manifest endpoint is local and
      // only does a disk scan. Frequency = every N puzzles processed.
      const REFRESH_EVERY = 25;
      const processed = (bookPlan.captured_ids || []).length;
      if (processed > 0 && processed % REFRESH_EVERY === 0) {
        try {
          const fresh = await http(
            "GET",
            `/book/${bookPlan.book_id}/manifest`,
          );
          const freshKnown = (fresh && fresh.known_ids) || [];
          if (Array.isArray(freshKnown) && freshKnown.length) {
            const merged = new Set(
              (bookPlan.captured_ids || []).map(Number),
            );
            let added = 0;
            for (const pid of freshKnown) {
              const n = Number(pid);
              if (!merged.has(n)) { merged.add(n); added++; }
            }
            if (added > 0) {
              bookPlan.captured_ids = [...merged];
              bookPlan.captured_count = bookPlan.captured_ids.length;
              plog(
                "SKIP",
                `Refreshed captured_ids: +${added} from server (now ${merged.size}/${bookPlan.total_puzzles})`,
              );
            }
          }
        } catch (e) {
          plog("WARN", `captured_ids refresh failed: ${e.message}`);
        }
      }

      // Find next uncaptured entry strictly after current index.
      // Treat both successfully-captured and permanently-failed pids as
      // "do not retry". failed_ids is populated by capture() when the
      // receiver returns 422 with a known puzzle_id (typically a
      // validation error that won't resolve on retry, e.g. invalid
      // board size). Without this, those puzzles never enter known_ids
      // and the skip-walk loops forever on the same end-of-chapter
      // target (observed: book 5120 ch12 pos59 / new_index: 395).
      const captured = new Set((bookPlan.captured_ids || []).map(Number));
      const failed = new Set((bookPlan.failed_ids || []).map(Number));
      let nextIdx = (bookPlan.current_seq_idx || 0) + 1;
      let skipped = 0;
      while (
        nextIdx < bookPlan.chapter_seq.length &&
        (captured.has(Number(bookPlan.chapter_seq[nextIdx].pid)) ||
          failed.has(Number(bookPlan.chapter_seq[nextIdx].pid)))
      ) {
        nextIdx++;
        skipped++;
      }
      if (skipped > 0) {
        plog("SKIP", `Chapter mode: skipped ${skipped} already-captured puzzle(s)`);
        // Awaited so a downstream stopRunning()/abort doesn't cancel
        // the in-flight POST and emit a misleading "Book event log
        // failed for chapter_mode_skipped" warning.
        await reportBookEvent("chapter_mode_skipped", {
          skipped,
          new_index: nextIdx,
        });
      }

      // ─── P1: end-of-chapter retry pass (v5.37.0) ───────────────
      // Pending entries (e.g. those refused by the readiness gate
      // for `publicid_unsettled`) leave gaps in `captured_ids` while
      // current_seq_idx marches forward. Without a revisit hook the
      // gap was permanent: the cursor only moved forward, and each
      // gap meant a hand-edit of book.json or a full re-run.
      //
      // Hook: when about to cross a chapter boundary (or hit the end
      // of chapter_seq), scan the chapter we're leaving for any pids
      // that are neither captured nor permanently failed. If any
      // exist AND we haven't already retried this chapter, redirect
      // nextIdx to the first such pid. The chapter is marked retried
      // unconditionally \u2014 strictly one-shot, never an infinite loop.
      const curForBoundary = bookPlan.chapter_seq[bookPlan.current_seq_idx || 0];
      const nextForBoundary = nextIdx < bookPlan.chapter_seq.length
        ? bookPlan.chapter_seq[nextIdx]
        : null;
      const leavingChapter = curForBoundary
        && (!nextForBoundary || curForBoundary.chapter_idx !== nextForBoundary.chapter_idx);
      if (leavingChapter) {
        const retried = new Set(bookPlan.retried_chapter_idxs || []);
        if (!retried.has(curForBoundary.chapter_idx)) {
          let pendingIdx = -1;
          let pendingCount = 0;
          for (let i = 0; i < bookPlan.chapter_seq.length; i++) {
            const e = bookPlan.chapter_seq[i];
            if (e.chapter_idx !== curForBoundary.chapter_idx) continue;
            const pidn = Number(e.pid);
            if (captured.has(pidn) || failed.has(pidn)) continue;
            pendingCount++;
            if (pendingIdx < 0) pendingIdx = i;
          }
          retried.add(curForBoundary.chapter_idx);
          bookPlan.retried_chapter_idxs = [...retried];
          if (pendingIdx >= 0) {
            plog(
              "INFO",
              `Chapter ${curForBoundary.chapter_number} retry pass: ${pendingCount} pending puzzle(s) \u2014 redirecting to first (idx ${pendingIdx})`,
            );
            reportBookEvent("chapter_retry_pass", {
              chapter_number: curForBoundary.chapter_number,
              chapter_idx: curForBoundary.chapter_idx,
              pending_count: pendingCount,
              redirect_idx: pendingIdx,
            });
            nextIdx = pendingIdx;
          }
          // Persist retried set even when no pending found, so we
          // don't waste a scan next chapter boundary.
          saveBookPlan(bookPlan);
        }
      }

      if (nextIdx >= bookPlan.chapter_seq.length) {
        const name = bookPlan.book_name || `Book ${bookPlan.book_id}`;
        const count = bookPlan.captured_count || 0;
        const scopeChapterId = bookPlan.scope_chapter_id != null
          ? Number(bookPlan.scope_chapter_id) : null;

        if (scopeChapterId != null) {
          // v5.38.0 interleaved flow: this was a chapter-scoped capture.
          // Tear down bookPlan and hand control back to discovery so
          // the next chapter can be discovered + captured.
          //
          // CRITICAL: do NOT call stopRunning() here. The session is
          // still alive — discovery is about to drive the next chapter
          // navigation. Calling stopRunning() flips `running=false`
          // (persisted to GM), and after the upcoming page reload
          // autoStart's "explicit-resume-only" guard would silently
          // bail with "Discovery state loaded — use [Control] Resume".
          // _resumeDiscoveryAfterChapter performs the navigation
          // itself; the next-page autoStart sees running=true and
          // re-enters continueDiscovery automatically. Stopping
          // happens for real only on the FINAL chapter, inside
          // _resumeDiscoveryAfterChapter.
          plog(
            "DONE",
            `Chapter ${scopeChapterId} scoped capture complete: ` +
            `"${name}" — ${count} captured. Resuming discovery.`,
          );
          clearBookPlan();
          updateStatus(
            `Chapter done — resuming discovery on next chapter`,
            "#4caf50",
          );
          await _resumeDiscoveryAfterChapter(scopeChapterId);
          return;
        }

        plog("DONE", `Chapter sweep complete: "${name}" — ${count} captured`);
        // Post-capture session summary for chapter completion.
        {
          const summaryDurationMs = bookPlan.started_at
            ? Date.now() - new Date(bookPlan.started_at).getTime() : 0;
          const summaryDurationMin = (summaryDurationMs / 60000).toFixed(1);
          plog("SUMMARY", "\u2550\u2550\u2550 Session Summary \u2550\u2550\u2550");
          plog("SUMMARY", `Captured: ${stats.ok}, Skipped: ${stats.skipped}, Errors: ${stats.error}`);
          plog("SUMMARY", `Duration: ${summaryDurationMin} min`);
          reportBookEvent("session_summary", {
            captured: stats.ok || 0,
            skipped: stats.skipped || 0,
            errors: stats.error || 0,
            duration_ms: summaryDurationMs,
            total_in_manifest: bookPlan.total_puzzles || 0,
            start_idx: bookPlan._start_idx || 0,
            end_idx: bookPlan.current_seq_idx || 0,
          });
        }
        stopRunning();
        clearBookPlan();
        updateStatus(`Chapter done: "${name}" — ${count} captured`, "#4caf50");
        GM_notification({
          text: `Chapter sweep complete: "${name}" — ${count} puzzles.`,
          title: "YenGo",
          timeout: 15000,
        });
        return;
      }

      const next = bookPlan.chapter_seq[nextIdx];
      bookPlan.current_seq_idx = nextIdx;
      bookPlan.current_idx = nextIdx; // shape compat
      saveBookPlan(bookPlan);

      // Optional session break to mimic human behavior.
      const totalCaptures = stats.ok + stats.skipped;
      if (totalCaptures > 0 && totalCaptures % CHAPTER_SESSION_BREAK_EVERY === 0) {
        const breakMs = randomBetween(CHAPTER_SESSION_BREAK_MIN_MS, CHAPTER_SESSION_BREAK_MAX_MS);
        const breakMin = (breakMs / 60000).toFixed(1);
        plog("WAIT", `Session break: ${breakMin} min pause (${totalCaptures} puzzles done)`);
        updateStatus(`Taking a break... ${breakMin} min (${totalCaptures} done)`, "#888");
        await waitMs(breakMs);
        if (!running) { plog("INFO", "goNext: paused during chapter session break — abort"); return; }
      }

      // Pacing: chapter mode interval, minus elapsed since capture.
      const targetInterval = randomBetween(CHAPTER_INTERVAL_MIN_MS, CHAPTER_INTERVAL_MAX_MS);
      const elapsed = Date.now() - captureStartedAt;
      const remainingWait = Math.max(3000, targetInterval - elapsed);
      const waitSec = (remainingWait / 1000).toFixed(0);
      // Unified shape: see puzzleLabel(). Same prefix in [WAIT]/[NEXT]
      // /[OK]/[SKIP] so a single grep gives the full puzzle timeline.
      const nextLabel = puzzleLabel({
        pid: next.pid,
        chapter_number: next.chapter_number,
        chapter_position: next.pos_in_chapter,
        progress: `${bookPlan.captured_count}/${bookPlan.total_puzzles}`,
      });
      // Legacy short form retained for downstream `[NEXT]` lines that
      // mix human + technical context (AJAX vs chapter-listing path).
      const progressStr = `Ch.${next.chapter_number} pos ${next.pos_in_chapter} (${bookPlan.captured_count}/${bookPlan.total_puzzles})`;
      plog("WAIT", `${waitSec}s -> ${nextLabel}`);
      updateStatus(`Chapter next in ${waitSec}s -> ${progressStr}`, "#81c784");
      await waitMs(remainingWait);
      if (!running) {
        plog("INFO", "goNext: paused mid-interval (chapter) — abort");
        return;
      }

      // Navigation policy: AJAX Next is the primary mechanism — it's
      // exactly what a human clicks ("Next" button on the puzzle page).
      // We only navigate to a chapter listing when the next puzzle is
      // in a different chapter than the one we're currently in (chapter
      // boundary). The site's AJAX Next at end-of-chapter sometimes
      // jumps to recommended puzzles outside the current chapter; we
      // detect that via the manifest's per-chapter pid set and recover
      // by going to the next chapter's listing page.

      // Find current entry by the pid actually on the page.
      // We previously did a global Array.find by pid here, but that
      // returns the FIRST occurrence — which is wrong when the manifest
      // has cross-chapter duplicate pids (book 5120 has 40). The wrong
      // chapter_idx then makes sameChapter false-negative and triggers
      // a spurious chapter-listing navigation, or rewinds the cursor.
      // IDENTITY: chapter_seq[].pid is publicid; we must compare
      // against publicid, not URL pid (which may be qid).
      const curPidForNav = Number(getPublicId());
      const curIdxHint = bookPlan.current_seq_idx || 0;
      const hintEntry = bookPlan.chapter_seq[curIdxHint];
      let curEntry = null;
      // Primary: trust the cursor — it was set to the entry we were
      // navigating to before this capture cycle started.
      if (hintEntry && Number(hintEntry.pid) === curPidForNav) {
        curEntry = hintEntry;
      }
      // Fallback A: forward search from the hint (handles intra-chapter
      // AJAX skips that landed on a later same-chapter pid).
      if (!curEntry) {
        for (let i = curIdxHint + 1; i < bookPlan.chapter_seq.length; i++) {
          if (Number(bookPlan.chapter_seq[i].pid) === curPidForNav) {
            curEntry = bookPlan.chapter_seq[i];
            break;
          }
        }
      }
      // Fallback B: backward, but only within the hint's chapter to
      // avoid cross-chapter rewinds on duplicate pids.
      if (!curEntry && hintEntry) {
        for (let i = curIdxHint - 1; i >= 0; i--) {
          const e = bookPlan.chapter_seq[i];
          if (e.chapter_idx !== hintEntry.chapter_idx) break;
          if (Number(e.pid) === curPidForNav) { curEntry = e; break; }
        }
      }
      if (!curEntry) {
        curEntry = hintEntry || bookPlan.chapter_seq[0];
        plog("WARN", `goNext: pid ${curPidForNav} not in chapter_seq near idx ${curIdxHint} — falling back to seq[idx]`);
      }
      const sameChapter = curEntry && curEntry.chapter_idx === next.chapter_idx;
      // Adjacency gate: site's Next button always advances by exactly
      // +1 in the chapter's natural order. It has no knowledge of our
      // skip-list, so AJAX is only safe when the manifest cursor is
      // also moving by +1. Any other jump (skipped already-captured
      // positions, or chapter boundary) MUST go through the chapter
      // listing — that's the only surface where we can address an
      // arbitrary puzzle by anchor click. See memory note
      // weiqi101-browser-capture.md (v5.36.0).
      const adjacent =
        sameChapter &&
        curEntry &&
        Number(next.pos_in_chapter) === Number(curEntry.pos_in_chapter) + 1;
      plog("DEBUG", `goNext: cur=Ch.${curEntry && curEntry.chapter_number}/pos${curEntry && curEntry.pos_in_chapter} (pid ${curPidForNav}) -> next=Ch.${next.chapter_number}/pos${next.pos_in_chapter} (pid ${next.pid}) sameChapter=${sameChapter} adjacent=${adjacent}`);

      if (adjacent) {
        const ajaxOk = await triggerSiteNext();
        if (ajaxOk) {
          // IDENTITY: compare landed publicid against next.pid (publicid).
          const landedPid = Number(getPublicId());
          if (landedPid === next.pid) {
            plog("NEXT", `-> ${progressStr} via AJAX (puzzle ${landedPid})`);
            capture();
            return;
          }
          // AJAX advanced by +1 in site order but landed somewhere else
          // — site order disagrees with manifest order at this seam.
          // Fall through to chapter listing for an authoritative click.
          plog("WARN", `AJAX next landed on ${landedPid} (expected ${next.pid}) — navigating to chapter listing`);
        } else {
          plog("WARN", `AJAX next failed (triggerSiteNext returned false) inside Ch.${next.chapter_number} — falling back to chapter listing`);
        }
      } else if (sameChapter) {
        // Non-adjacent same-chapter jump (skipped already-captured positions).
        plog("INFO", `Non-adjacent jump in Ch.${next.chapter_number}: pos ${curEntry && curEntry.pos_in_chapter} -> ${next.pos_in_chapter} — using chapter listing`);
      } else {
        // Different chapter — navigate to its listing.
        plog("INFO", `Chapter boundary: Ch.${curEntry && curEntry.chapter_number} -> Ch.${next.chapter_number}`);
      }

      // Chapter boundary or AJAX recovery: navigate to chapter listing.
      // The autoStart handler will click the entry on landing.
      if (!next.chapter_id) {
        plog("ERR", `Next entry (pid=${next.pid}) has no chapter_id — manifest needs re-discovery`);
        stopRunning();
        return;
      }
      // Land directly on the listing page that contains the target puzzle
      // instead of always page 1 (avoids N-1 wasted paginations per puzzle).
      const nextChapterPage = targetChapterPageForEntry(next);
      plog("NEXT", `-> ${progressStr} via chapter listing (Ch.${next.chapter_id} p.${nextChapterPage})`);
      location.href = buildChapterUrl(bookPlan.book_id, next.chapter_id, nextChapterPage);
      return;
    }

    // ── Other capture flows (qday, etc.): dual-wait behavior ──
    lastCaptureWasDuplicate = false;

    // Human-like behavior: think time + session breaks + scroll noise
    await simulateHumanBehavior();

    const wait = computeAdaptiveDelayMs();
    const waitSec = (wait / 1000).toFixed(1);

    if (isQdaySweepActive()) {
      syncQdayPlanFromPage();
      const nextPlan = computeNextQdayPlan(qdayPlan);
      if (!nextPlan) {
        const finalDate = qdayPlan.targetDate;
        stopRunning("qday sweep complete");
        clearQdayPlan();
        plog("END", `Qday sweep complete through ${finalDate}`);
        updateStatus(`Qday sweep done through ${finalDate}.`, "#4caf50");
        GM_notification({
          text: `Qday sweep complete through ${finalDate}.`,
          title: "YenGo",
          timeout: 15000,
        });
        return;
      }

      saveQdayPlan(nextPlan);
      plog("WAIT", `${waitSec}s delay before ${nextPlan.currentDate} #${nextPlan.currentNum}`);
      updateStatus(
        `Qday next in ${waitSec}s -> ${nextPlan.currentDate} #${nextPlan.currentNum}`,
        "#81c784"
      );
      await waitMs(wait);

      // Try site's AJAX Next button first (no page reload)
      const ajaxOk = await triggerSiteNext();
      if (ajaxOk) {
        // AJAX navigation succeeded — puzzle loaded in-place.
        // Sync plan from the new page state and re-capture.
        syncQdayPlanFromPage();
        capture();
        return;
      }

      // Fallback: full page navigation
      plog("NEXT", `-> ${nextPlan.currentDate} #${nextPlan.currentNum} (full nav)`);
      location.href = buildQdayUrl(nextPlan.currentDate, nextPlan.currentNum);
      return;
    }

    plog("WAIT", `${waitSec}s delay before asking server for next puzzle`);
    updateStatus(`Asking server for next puzzle in ${waitSec}s...`, "#81c784");
    await waitMs(wait);

    try {
      const next = await http("GET", "/next");
      if (next.status === "ok") {
        plog("NEXT", `-> puzzle ${next.puzzle_id} (${next.visited}/${next.total}, ${next.remaining} remaining)`);
        updateStatus(`Next: ${next.puzzle_id} (${next.remaining} left)`, "#81c784");
        location.href = next.url;
      } else if (next.status === "done") {
        plog("END", `Queue complete: ${next.visited} puzzles visited`);
        stopRunning("queue complete");
        updateStatus(`Done! ${next.visited} puzzles visited.`, "#4caf50");
        GM_notification({ text: `Queue complete! ${next.visited} puzzles.`, title: "YenGo", timeout: 15000 });
      } else {
        stopRunning("no queue active");
        plog("WARN", "No queue active on server");
        updateStatus("No queue active. Pick a book to start.", "#ff9800");
      }
    } catch (err) {
      issueStreak += 1;
      plog("ERR", `Server unreachable: ${err.message}, stopping`);
      stopRunning("server unreachable");
      updateStatus("Server unreachable! Is 'receive' running?", "#f44336");
    }
  }

  // ─────────────────────────────────────────────────────────────
  // PAGE FACT HARVESTING (multi-layer identity)
  //
  // A puzzle page exposes book/chapter/pid via several independent
  // channels. We collect all of them and let a reconciler pick the
  // most trustworthy values — far more resilient than trusting any
  // single channel.
  //
  //   L1 URL path        — /book/{book_id}/{chapter_id}/{pid}/
  //   L2 qqdata          — Alpine store: publicid, bookinfos[]
  //   L3 Breadcrumb      — DOM <a> + "No.K" position text
  //   L4 Included-in     — DOM list of additional book memberships
  //   L5 <title>         — "Question {N} - {chapter_name} - 101WEIQI"
  //   L6 Visible ID      — DOM text "ID：Q-{pid}"
  //
  // Trust order (user-defined): qqdata > DOM > URL.
  // Pid quorum: qqdata.publicid PLUS at least one of (URL pid, visible
  // pid). Without qqdata there is no puzzle data to save.
  // ─────────────────────────────────────────────────────────────

  function parseUrlPath(pathname) {
    const p = pathname || location.pathname;
    // /book/{book_id}/{chapter_id}/{pid}/
    let m = p.match(/^\/book\/(\d+)\/(\d+)\/(\d+)\/?$/);
    if (m) return { book_id: parseInt(m[1], 10), chapter_id: parseInt(m[2], 10), pid: parseInt(m[3], 10) };
    // /book/{book_id}/{chapter_id}/
    m = p.match(/^\/book\/(\d+)\/(\d+)\/?$/);
    if (m) return { book_id: parseInt(m[1], 10), chapter_id: parseInt(m[2], 10), pid: null };
    // /q/{pid}/ or /chessmanual/{pid}/
    m = p.match(/^\/(?:q|chessmanual)\/(\d+)/);
    if (m) return { book_id: null, chapter_id: null, pid: parseInt(m[1], 10) };
    return { book_id: null, chapter_id: null, pid: null };
  }

  function scrapeBreadcrumb() {
    // Verified against /book/5120/45791/68168/:
    //   <a href="/book/5120/">叶老师围棋初级A</a> / <a href="/book/5120/45791/">作业</a> / No.27
    const out = { book_id: null, book_name: "", chapter_id: null, chapter_name: "", position: null };
    try {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
      let posNode = null;
      while (walker.nextNode()) {
        const t = walker.currentNode.textContent.trim();
        const pm = t.match(/^No\.(\d+)$/i) || t.match(/^第(\d+)题$/);
        if (!pm) continue;
        // Verify ancestor contains book links (rules out random "No.X" text)
        let p = walker.currentNode.parentElement;
        for (let depth = 0; depth < 4 && p; depth++, p = p.parentElement) {
          if (p.querySelectorAll('a[href^="/book/"]').length >= 2) {
            posNode = { container: p, position: parseInt(pm[1], 10) };
            break;
          }
        }
        if (posNode) break;
      }
      if (posNode) {
        out.position = posNode.position;
        for (const a of posNode.container.querySelectorAll('a[href^="/book/"]')) {
          const href = a.getAttribute("href") || "";
          const bm = href.match(/^\/book\/(\d+)\/?$/);
          const cm = href.match(/^\/book\/(\d+)\/(\d+)\/?$/);
          if (bm && out.book_id == null) {
            out.book_id = parseInt(bm[1], 10);
            out.book_name = (a.textContent || "").trim();
          } else if (cm && out.chapter_id == null) {
            out.chapter_id = parseInt(cm[2], 10);
            out.chapter_name = (a.textContent || "").trim();
          }
        }
      }
    } catch (_) {}
    return out;
  }

  function extractTitleFacts() {
    // Page <title>: "Question 27 - 作业 - 101WEIQI"
    const out = { position: null, chapter_name: "" };
    try {
      const t = (document.title || "").trim();
      const m = t.match(/^(?:Question|第)\s*(\d+)\s*[\u9898\-—]\s*(.+?)\s*-\s*101WEIQI/i);
      if (m) {
        out.position = parseInt(m[1], 10);
        out.chapter_name = (m[2] || "").trim();
      }
    } catch (_) {}
    return out;
  }

  function extractVisiblePid() {
    // Visible "ID：Q-{pid}" label on the puzzle info area.
    try {
      const text = document.body && document.body.innerText || "";
      const m = text.match(/ID[\uFF1A:]\s*Q-(\d+)/);
      if (m) return parseInt(m[1], 10);
    } catch (_) {}
    return null;
  }

  function harvestPageFacts() {
    const url = parseUrlPath(location.pathname);
    const qq = getQqdata() || {};
    const qqdata = {
      pid: qq.publicid != null ? Number(qq.publicid) : null,
      qqdata_id: qq.id != null ? Number(qq.id) : null,
      bookinfos: Array.isArray(qq.bookinfos) ? qq.bookinfos.map(function (b) {
        return {
          book_id: Number(b && (b.book_id || b.id || 0)) || null,
          name: String((b && (b.name || b.book_name)) || "").trim(),
        };
      }).filter(function (b) { return b.book_id; }) : [],
    };
    const breadcrumb = scrapeBreadcrumb();
    const included = (typeof scrapePageBooks === "function") ? scrapePageBooks() : [];
    const title = extractTitleFacts();
    const visiblePid = extractVisiblePid();
    return { url: url, qqdata: qqdata, breadcrumb: breadcrumb, included: included, title: title, visiblePid: visiblePid };
  }

  // ─────────────────────────────────────────────────────────────
  // RECONCILERS — pure functions, easy to self-test.
  // ─────────────────────────────────────────────────────────────

  function reconcilePid(facts) {
    // IDENTITY RULE: qqdata.publicid is canonical. URL pid is a routing
    // token (may be qid ≠ publicid for some books) and is NOT part of
    // the identity quorum. Visible "ID：Q-NNN" is an advisory cross-
    // check: same namespace as publicid, useful for detecting a stale
    // DOM, but never a tiebreaker that overrides qqdata.
    const candidates = {
      qqdata: facts.qqdata && facts.qqdata.pid != null ? Number(facts.qqdata.pid) : null,
      url: facts.url && facts.url.pid != null ? Number(facts.url.pid) : null,        // routing token, telemetry only
      visible: facts.visiblePid != null ? Number(facts.visiblePid) : null,           // advisory only
    };
    if (candidates.qqdata == null) {
      return { ok: false, pid: null, reason: "no_qqdata_pid", agreed_layers: [], conflicts: [], candidates: candidates };
    }
    const pid = candidates.qqdata;
    const agreed = ["qqdata"];
    const conflicts = [];
    if (candidates.visible != null) {
      if (candidates.visible === pid) agreed.push("visible");
      else conflicts.push({ layer: "visible", value: candidates.visible });
    }
    // URL pid: never part of quorum; surface in conflicts only when it
    // disagrees AND is in a comparable namespace (best-effort: we have
    // no way to know namespace from the value alone, so log silently).
    if (candidates.url != null && candidates.url !== pid) {
      conflicts.push({ layer: "url", value: candidates.url, advisory: true });
    }
    return { ok: true, pid: pid, reason: "qqdata_canonical", agreed_layers: agreed, conflicts: conflicts, candidates: candidates };
  }

  function reconcileAttribution(facts, opts) {
    opts = opts || {};
    const activeBookId = opts.activeBookId || null;
    const manifestSeq = Array.isArray(opts.manifestSeq) ? opts.manifestSeq : null;
    const r = {
      book_id: null, book_name: "", book_source: "none",
      chapter_id: null, chapter_name: "", chapter_source: "none",
      chapter_number: 0, chapter_number_source: "none",
      position: null, position_source: "none",
      global_position: 0,
      all_known_books: [], drift_from_active: false,
    };
    const qqBooks = (facts.qqdata && facts.qqdata.bookinfos) || [];
    const breadId = facts.breadcrumb && facts.breadcrumb.book_id;
    const incBooks = (facts.included || []);
    const urlBookId = facts.url && facts.url.book_id;

    // BOOK selection (priority: qqdata cross-confirmed > qqdata > breadcrumb > included > url)
    let chosen = null;
    let src = "none";
    if (breadId && qqBooks.some(function (b) { return b.book_id === breadId; })) {
      chosen = qqBooks.find(function (b) { return b.book_id === breadId; });
      src = "qqdata+breadcrumb";
    } else if (activeBookId && qqBooks.some(function (b) { return b.book_id === activeBookId; })) {
      chosen = qqBooks.find(function (b) { return b.book_id === activeBookId; });
      src = "qqdata+active";
    } else if (breadId) {
      chosen = { book_id: breadId, name: facts.breadcrumb.book_name };
      src = "breadcrumb";
    } else if (qqBooks.length > 0) {
      chosen = qqBooks[0]; src = "qqdata";
    } else if (incBooks.length > 0) {
      chosen = incBooks[0]; src = "included";
    } else if (urlBookId) {
      chosen = { book_id: urlBookId, name: "" }; src = "url";
    }
    if (chosen) {
      r.book_id = chosen.book_id;
      r.book_name = chosen.name || "";
      r.book_source = src;
    }

    // Aggregate all known book memberships for provenance
    const seen = new Set();
    function pushBook(b) {
      if (b && b.book_id && !seen.has(b.book_id)) {
        seen.add(b.book_id);
        r.all_known_books.push({ book_id: b.book_id, name: b.name || "" });
      }
    }
    qqBooks.forEach(pushBook);
    incBooks.forEach(pushBook);
    if (breadId) pushBook({ book_id: breadId, name: facts.breadcrumb.book_name });
    if (urlBookId) pushBook({ book_id: urlBookId, name: "" });

    // CHAPTER (breadcrumb is rendered with the page → most trustworthy)
    if (facts.breadcrumb && facts.breadcrumb.chapter_id) {
      r.chapter_id = facts.breadcrumb.chapter_id;
      r.chapter_name = facts.breadcrumb.chapter_name || "";
      r.chapter_source = "breadcrumb";
    } else if (urlBookId && facts.url && facts.url.chapter_id) {
      r.chapter_id = facts.url.chapter_id;
      r.chapter_source = "url";
    }

    // POSITION (within chapter)
    if (facts.breadcrumb && facts.breadcrumb.position) {
      r.position = facts.breadcrumb.position;
      r.position_source = "breadcrumb";
    } else if (facts.title && facts.title.position) {
      r.position = facts.title.position;
      r.position_source = "title";
      if (!r.chapter_name) r.chapter_name = facts.title.chapter_name || "";
    }

    // Manifest cross-reference: chapter_number + global_position when
    // we have a manifest for the *active* book that contains this pid
    // or chapter_id. Only applies when reconciled book == active book.
    if (manifestSeq && r.book_id && activeBookId && Number(r.book_id) === Number(activeBookId)) {
      // Prefer pid match (handles case where chapter_id missing from breadcrumb)
      const pid = facts.qqdata && facts.qqdata.pid;
      if (pid != null) {
        for (const e of manifestSeq) {
          if (Number(e.pid) === Number(pid)) {
            r.chapter_number = Number(e.chapter_number) || 0;
            r.chapter_number_source = "manifest+pid";
            r.global_position = Number(e.global_pos) || 0;
            if (!r.chapter_id && e.chapter_id) r.chapter_id = Number(e.chapter_id);
            if (!r.chapter_name && e.chapter_name) r.chapter_name = e.chapter_name;
            if (!r.position && e.pos_in_chapter) {
              r.position = Number(e.pos_in_chapter);
              r.position_source = "manifest+pid";
            }
            break;
          }
        }
      }
      // Fall back to chapter_id match for chapter_number
      if (!r.chapter_number && r.chapter_id) {
        for (const e of manifestSeq) {
          if (Number(e.chapter_id) === Number(r.chapter_id)) {
            r.chapter_number = Number(e.chapter_number) || 0;
            r.chapter_number_source = "manifest+chapter";
            if (!r.chapter_name && e.chapter_name) r.chapter_name = e.chapter_name;
            break;
          }
        }
      }
    }

    if (activeBookId && r.book_id && Number(r.book_id) !== Number(activeBookId)) {
      r.drift_from_active = true;
    }
    return r;
  }

  // Self-tests — run only when ?yengo_selftest=1 is in the URL.
  if (typeof location !== "undefined" && location.search && location.search.indexOf("yengo_selftest=1") >= 0) (function _testReconcilers() {
    // Under the publicid-only identity rule, reconcilePid is `ok`
    // whenever qqdata.publicid is present. URL pid disagreement is
    // tolerated (it may be qid). Visible disagreement is recorded as
    // a non-blocking conflict for diagnostics.
    const cases = [
      { name: "all-agree", facts: { qqdata: { pid: 100 }, url: { pid: 100 }, visiblePid: 100 }, ok: true, pid: 100 },
      { name: "qq+url", facts: { qqdata: { pid: 100 }, url: { pid: 100 }, visiblePid: null }, ok: true, pid: 100 },
      { name: "qq-only", facts: { qqdata: { pid: 100 }, url: { pid: null }, visiblePid: null }, ok: true, pid: 100 },
      { name: "no-qq", facts: { qqdata: { pid: null }, url: { pid: 100 }, visiblePid: 100 }, ok: false },
      { name: "qq+visible-vs-url", facts: { qqdata: { pid: 100 }, url: { pid: 200 }, visiblePid: 100 }, ok: true, pid: 100 },
      // Book 25369 case: URL is qid (different namespace from publicid).
      // qqdata still wins; visible matches qqdata; URL goes into conflicts as advisory.
      { name: "book-25369-qid-differs", facts: { qqdata: { pid: 261436 }, url: { pid: 295990 }, visiblePid: 261436 }, ok: true, pid: 261436 },
    ];
    for (const c of cases) {
      const r = reconcilePid(c.facts);
      if (r.ok !== c.ok) log("WARN", `[selftest] reconcilePid '${c.name}': ok=${r.ok} want=${c.ok}`);
      else if (r.ok && r.pid !== c.pid) log("WARN", `[selftest] reconcilePid '${c.name}': pid=${r.pid} want=${c.pid}`);
    }
    const a1 = reconcileAttribution({
      qqdata: { pid: 100, bookinfos: [{ book_id: 5120, name: "A" }] },
      url: { book_id: 5120, chapter_id: 45791, pid: 100 },
      breadcrumb: { book_id: 5120, book_name: "A", chapter_id: 45791, chapter_name: "Ch1", position: 27 },
      included: [{ book_id: 5120, name: "A" }], title: { position: 27, chapter_name: "Ch1" }, visiblePid: 100,
    }, { activeBookId: 5120 });
    if (a1.book_id !== 5120 || a1.chapter_id !== 45791 || a1.position !== 27 || a1.drift_from_active) {
      log("WARN", "[selftest] reconcileAttribution all-agree failed", a1);
    }
    const a2 = reconcileAttribution({
      qqdata: { pid: 999, bookinfos: [{ book_id: 9999, name: "Other" }] },
      url: { book_id: 9999, chapter_id: 7000, pid: 999 },
      breadcrumb: { book_id: 9999, book_name: "Other", chapter_id: 7000, chapter_name: "X", position: 1 },
      included: [], title: { position: 1, chapter_name: "X" }, visiblePid: 999,
    }, { activeBookId: 5120 });
    if (a2.book_id !== 9999 || !a2.drift_from_active) {
      log("WARN", "[selftest] reconcileAttribution drift case failed", a2);
    }
  })();

  // CAPTURE READINESS GATE — publicid-only model.
  //
  // The ONLY identity contract: `qqdata.publicid` is canonical. URL
  // pid is a routing token, in a different namespace for some books
  // (e.g. 25369: URL=qid=295990, publicid=261436). Comparing them is
  // a category error and produced spurious `url_data_mismatch`
  // refusals on every capture in such books.
  //
  // New gate contract:
  //   1. Wait until `qqdata.publicid` is present.
  //   2. SETTLING CHECK: require the same publicid on TWO consecutive
  //      polls. This is what catches the AJAX race we used to catch
  //      via `urlPid === dataPid`: mid-`gotopic` swap, qqdata briefly
  //      holds the previous puzzle's publicid before flipping to the
  //      new one. One settled tick proves the swap completed.
  //   3. Optional `expectedPid` (chapter-mode manifest cursor): if
  //      provided, require `dataPid === expectedPid`. Otherwise the
  //      capture is for whatever the live page shows.
  //
  // URL pid is NOT consulted. `reconcilePid` enforces identity quorum
  // separately on the captured payload.
  // ────────────────────────────────────────────────────────────

  function evaluateCaptureReadiness({ dataPid, settledPid, expectedPid = null }) {
    const ids = { dataPid, settledPid, expectedPid };
    if (dataPid == null) return { ok: false, reason: "no_data_pid", ids };
    if (settledPid == null || Number(settledPid) !== Number(dataPid)) {
      return { ok: false, reason: "publicid_unsettled", ids };
    }
    if (expectedPid != null && Number(dataPid) !== Number(expectedPid)) {
      return { ok: false, reason: "manifest_mismatch", ids };
    }
    return { ok: true, ids };
  }

  async function awaitCaptureReadiness({
    timeoutMs = 8000,
    pollMs = 150,
    expectedPid = null,
  } = {}) {
    const start = Date.now();
    const signal = currentSignal();
    let prev = null;
    let last = { ok: false, reason: "no_data_pid", ids: { dataPid: null, settledPid: null, expectedPid } };
    while (Date.now() - start < timeoutMs) {
      if (signal.aborted) return last;
      const qq = getQqdata();
      const dataPid = qq && qq.publicid != null ? Number(qq.publicid) : null;
      last = evaluateCaptureReadiness({ dataPid, settledPid: prev, expectedPid });
      if (last.ok) return last;
      prev = dataPid;
      const wait = await waitMs(pollMs);
      if (wait === "aborted" || !running) return last;
    }
    return last;
  }

  // Self-tests — run only when ?yengo_selftest=1 is in the URL. The
  // previous unconditional run-on-load fired on every page navigation
  // and surfaced no output unless WARN was emitted. Tests are stable
  // pure-function logic; promote to a real test harness in Phase 3.
  if (typeof location !== "undefined" && location.search && location.search.indexOf("yengo_selftest=1") >= 0) (function _testCaptureReadiness() {
    const cases = [
      // Settled, no manifest cursor.
      { input: { dataPid: 137, settledPid: 137 }, want: "ok" },
      { input: { dataPid: 137, settledPid: 137, expectedPid: 137 }, want: "ok" },
      // String/number tolerance.
      { input: { dataPid: "137", settledPid: 137 }, want: "ok" },
      // Manifest mismatch (qqdata published a different puzzle than the cursor).
      { input: { dataPid: 137, settledPid: 137, expectedPid: 138 }, want: "manifest_mismatch" },
      // Unsettled (publicid changed between polls — AJAX swap mid-flight).
      { input: { dataPid: 137, settledPid: 136 }, want: "publicid_unsettled" },
      // First poll (no prior value yet) — must wait for next tick.
      { input: { dataPid: 137, settledPid: null }, want: "publicid_unsettled" },
      // No qqdata at all.
      { input: { dataPid: null, settledPid: null }, want: "no_data_pid" },
      // Book 25369 case: URL pid is irrelevant. Settled publicid matches manifest -> ok.
      { input: { dataPid: 261436, settledPid: 261436, expectedPid: 261436 }, want: "ok" },
    ];
    for (const c of cases) {
      const r = evaluateCaptureReadiness(c.input);
      const got = r.ok ? "ok" : r.reason;
      if (got !== c.want) {
        console.warn(
          `[YENGO][readiness-self-test] FAIL ${JSON.stringify(c.input)} -> ${got} (expected ${c.want})`,
        );
      }
    }
  })();

  // -- Wait for qqdata (may load async) ---------------------------
  function waitForQqdata() {
    return new Promise((resolve) => {
      const signal = currentSignal();
      if (signal.aborted) return resolve(!!getQqdata());
      if (isQqdataReady()) return resolve(true);
      let elapsed = 0;
      const iv = setInterval(() => {
        if (signal.aborted) {
          clearInterval(iv);
          return resolve(!!getQqdata());
        }
        elapsed += QQDATA_POLL_MS;
        if (isQqdataReady()) {
          clearInterval(iv);
          resolve(true);
        } else if (elapsed >= QQDATA_MAX_WAIT) {
          clearInterval(iv);
          // Fall back: accept qqdata even without content (validator will catch)
          resolve(!!getQqdata());
        }
      }, QQDATA_POLL_MS);
    });
  }

  // -- DOM scraping: "Included in" book links ----------------------
  // Puzzle pages may list which books contain the puzzle.  The qqdata
  // `bookinfos` field is almost always empty, so we scrape the page
  // DOM for book links instead.  Returns an array of
  // {book_id, name} objects (empty array if none found).

  // Multiple URL patterns for book links (101weiqi uses several)
  const BOOK_URL_PATTERNS = [
    /\/book(\d+)\//, // /book123/chapter/
    /\/book\/(\d+)/, // /book/123/...
    /\/chessbook\/(\d+)/, // /chessbook/123/...
    /\/bookinfo\/(\d+)/, // /bookinfo/123/...
    /book_?id[=:](\d+)/i, // ?book_id=123 or bookid=123
  ];

  function extractBookIdFromHref(href) {
    for (const pat of BOOK_URL_PATTERNS) {
      const m = href.match(pat);
      if (m) return parseInt(m[1], 10);
    }
    return null;
  }

  function scrapePageBooks() {
    const books = [];
    const seen = new Set();

    // Strategy 1: Find the "Included in" / "收录于" section by text content.
    // Walk up from the text node to find the parent container, then grab
    // all links within it.
    const walker = document.createTreeWalker(
      document.body, NodeFilter.SHOW_TEXT, null
    );
    let sectionContainer = null;
    while (walker.nextNode()) {
      const text = walker.currentNode.textContent.trim();
      if (text === "Included in:" || text === "Included in\uFF1A" ||
          text === "\u6536\u5F55\u4E8E\uFF1A" || text === "\u6536\u5F55\u4E8E:" ||
          text.startsWith("Included in") || text.startsWith("\u6536\u5F55\u4E8E")) {
        // Walk up to the parent element that contains both the label
        // and the book links (usually a div or section)
        sectionContainer = walker.currentNode.parentElement;
        // If the parent is too narrow (e.g. a <strong>), go up one more
        if (sectionContainer && sectionContainer.querySelectorAll("a").length === 0) {
          sectionContainer = sectionContainer.parentElement;
        }
        if (sectionContainer && sectionContainer.querySelectorAll("a").length === 0) {
          sectionContainer = sectionContainer.parentElement;
        }
        break;
      }
    }

    if (sectionContainer) {
      const anchors = sectionContainer.querySelectorAll("a");
      log("INFO", `DOM scrape: found "Included in" section with ${anchors.length} link(s)`);
      for (const a of anchors) {
        const href = a.href || "";
        const bookId = extractBookIdFromHref(href);
        if (bookId && !seen.has(bookId)) {
          seen.add(bookId);
          books.push({
            book_id: bookId,
            name: (a.textContent || "").trim(),
          });
        }
        // Log unmatched hrefs for diagnostics
        if (!bookId && href) {
          log("INFO", `DOM scrape: unmatched href in section: ${href}`);
        }
      }
    } else {
      log("INFO", "DOM scrape: no 'Included in' section found in page");
    }

    // Strategy 2 (fallback): Broad scan for any /book{id}/ links
    // in case the section text differs from what we expect.
    if (books.length === 0) {
      const allAnchors = document.querySelectorAll('a[href*="book"]');
      for (const a of allAnchors) {
        const href = a.href || "";
        const bookId = extractBookIdFromHref(href);
        if (bookId && !seen.has(bookId)) {
          // Filter out navigation/UI links -- book links are usually in
          // the sidebar or puzzle info area, with Chinese text content
          const text = (a.textContent || "").trim();
          if (text.length > 1 && !/^(Pick|Choose|Browse|My|Add)/i.test(text)) {
            seen.add(bookId);
            books.push({ book_id: bookId, name: text });
          }
        }
      }
    }

    if (books.length > 0) {
      log("INFO", `DOM scrape: found ${books.length} book link(s)`, books);
    }
    return books;
  }

  // Wait for the "Included in" section to appear in the DOM.
  // Uses textContent (not innerHTML) to avoid serializing HTML tags.
  function waitForBookSection(timeoutMs = 3000) {
    return new Promise((resolve) => {
      const signal = currentSignal();
      if (signal.aborted) return resolve(false);
      const check = () => {
        const text = document.body.textContent;
        return text.includes("Included in") || text.includes("\u6536\u5F55\u4E8E");
      };
      if (check()) return resolve(true);
      let elapsed = 0;
      const interval = 500;
      const iv = setInterval(() => {
        if (signal.aborted) { clearInterval(iv); return resolve(false); }
        elapsed += interval;
        if (check()) { clearInterval(iv); resolve(true); }
        else if (elapsed >= timeoutMs) { clearInterval(iv); resolve(false); }
      }, interval);
    });
  }

  // -- Main capture logic -----------------------------------------
  // _capturing: in-flight guard. capture() is invoked from the
  // navigation watcher, autoStart resume cases, the CAPTCHA poll, and
  // recursive goNext()->capture() chains. Concurrent invocations were
  // racing each other and double-advancing current_seq_idx. The guard
  // is a single boolean cleared in finally; pause/stop is handled by
  // the existing `running` checks inside the function.
  let _capturing = false;
  async function capture() {
    if (_capturing) {
      plog("INFO", "capture() suppressed: already in flight");
      return;
    }
    _capturing = true;
    try {
      await _captureImpl();
    } catch (e) {
      // AbortError is the expected outcome when stopRunning() fires
      // mid-capture: we don't want to count it as a real failure or
      // double-advance via failAndAdvance(). Swallow it quietly and
      // let the loop unwind. Anything else still propagates to the
      // outer error path (currently rethrown by callers).
      if (e && (e.name === "AbortError" || e.kind === "abort")) {
        plog("INFO", `capture() aborted: ${e.message}`);
      } else {
        throw e;
      }
    } finally {
      _capturing = false;
    }
  }

  async function _captureImpl() {
    // Pause is atomic: once running=false, no new captures fire even if
    // the navigation watcher or a deferred handler queued one. Without
    // this gate, Resume often produced double-captures (one from a stale
    // scheduled capture(), one from autoStart→Case1) which raced goNext
    // and double-advanced current_seq_idx.
    if (!running && (isBookCaptureActive() || isQdaySweepActive())) {
      plog("INFO", "capture() suppressed: paused");
      return;
    }
    captureStartedAt = Date.now(); // Track start for interval-based pacing
    // Per-puzzle recovery flag is set only by a successful retry below;
    // clear at entry so a stale flag from a prior capture cannot leak
    // into this one.
    _pendingRecoveryAttempts = 0;
    // Label only — may be null pre-qqdata-load. Falls back to URL token
    // for diagnostics. IDENTITY-bearing decisions use getPublicId() below.
    const pageId = getPublicId() || getUrlRouteToken();
    const qday = isQdaySweepActive();
    const book = isBookCaptureActive();
    const label = qday
      ? `qday ${qdayPlan.currentDate} #${qdayPlan.currentNum}`
      : book
        ? `book "${bookPlan.book_name}" puzzle ${pageId} (${bookPlan.captured_count || bookPlan.captured_ids.length}/${bookPlan.total_puzzles || bookPlan.puzzle_ids.length || '?'})`
        : (pageId ? `puzzle ${pageId}` : location.pathname);
    plog("LOAD", `${label} — waiting for data`);

    // CAPTCHA. We track the wait-poll on the module-level _captchaPoll
    // handle so stopRunning() can clear it. Clearing any prior poll
    // here too defends against rapid back-to-back CAPTCHAs.
    if (isCaptcha()) {
      stats.captcha = (stats.captcha || 0) + 1;
      issueStreak += 1;
      GM_setValue(KEY_STATS, stats);
      plog("WARN", `${label} — CAPTCHA detected, pausing until solved`);
      updateStatus("CAPTCHA! Solve it manually -- will auto-resume.", "#f44336");
      GM_notification({ text: "CAPTCHA -- solve to continue", title: "YenGo", timeout: 10000 });
      if (_captchaPoll) {
        try { clearInterval(_captchaPoll); } catch (e) { log("DEBUG", "clearInterval(captchaPoll) failed: " + e.message); }
      }
      _captchaPoll = setInterval(() => {
        if (!running) {
          // Stopped while waiting on CAPTCHA — don't auto-resume.
          clearInterval(_captchaPoll);
          _captchaPoll = null;
          return;
        }
        if (getQqdata()) {
          clearInterval(_captchaPoll);
          _captchaPoll = null;
          capture();
        }
      }, 5000);
      return;
    }

    // Login
    if (isLogin()) {
      issueStreak += 1;
      plog("ERR", `${label} — login required, sweep stopped`);
      stopRunning("login required");
      updateStatus("Login required! Log in, then reload.", "#f44336");
      return;
    }

    // Wait for qqdata (may load async, e.g. /qday/ pages)
    if (!isQqdataReady()) {
      plog("LOAD", `${label} — qqdata not ready, polling (max ${QQDATA_MAX_WAIT / 1000}s)`);
      updateStatus("Waiting for puzzle data...", "#4fc3f7");
      const found = await waitForQqdata();
      if (!found) {
        stats.notfound = (stats.notfound || 0) + 1;
        failAndAdvance({
          logMsg: `${label} — no qqdata after ${QQDATA_MAX_WAIT / 1000}s, skipping`,
          statusText: "No puzzle data found. Skipping.",
        });
        return;
      }
    }

    // Capture readiness gate: wait for qqdata.publicid to settle (same
    // value across two consecutive polls — proves the AJAX gotopic swap
    // completed). In chapter mode, also require the settled publicid to
    // match the manifest cursor (`expectedPid`). URL pid is NOT consulted
    // — it may be qid (≠ publicid) for some books.
    let expectedPid = null;
    if (
      isBookCaptureActive()
      && isChapterMode()
      && bookPlan
      && Array.isArray(bookPlan.chapter_seq)
      && bookPlan.chapter_seq[bookPlan.current_seq_idx || 0]
    ) {
      expectedPid = Number(bookPlan.chapter_seq[bookPlan.current_seq_idx || 0].pid);
    }
    let gate = await awaitCaptureReadiness({ expectedPid });

    // ── Recovery for transient race ───────────────────────────────
    // `publicid_unsettled` after the default budget almost always
    // means qqdata simply landed late after the AJAX gotopic swap
    // (verified for book 25369 pos 14: ~7 s to settle vs default 5 s).
    // Other refusal reasons (no_data_pid, manifest_mismatch) are real
    // problems — don't retry those.
    if (!gate.ok && gate.reason === "publicid_unsettled") {
      const ent = currentChapterEntry();
      const retryLabel = puzzleLabel({
        pid: expectedPid,
        chapter_number: ent && ent.chapter_number,
        chapter_position: ent && ent.pos_in_chapter,
        progress: bookPlan
          && `${bookPlan.captured_count}/${bookPlan.total_puzzles}`,
      }) || label;
      plog("INFO", `${retryLabel} — readiness gate refused (publicid_unsettled); extended retry up to 12s`);
      reportBookEvent("puzzle_retry", {
        reason: gate.reason,
        attempt: 1,
        pid: expectedPid,
        chapter_number: ent && ent.chapter_number,
        chapter_position: ent && ent.pos_in_chapter,
        ids: gate.ids,
      });
      gate = await awaitCaptureReadiness({ expectedPid, timeoutMs: 12000 });
      // If the retry succeeded, mark this capture as recovered so the
      // receiver can stamp `recovered=true` on the [SAVED] line. The
      // flag is consumed (cleared) when we attach _capture_meta below.
      if (gate.ok) _pendingRecoveryAttempts = 2;
    }

    if (!gate.ok) {
      const ids = gate.ids;
      const ent = currentChapterEntry();
      const skipLabel = puzzleLabel({
        pid: expectedPid,
        chapter_number: ent && ent.chapter_number,
        chapter_position: ent && ent.pos_in_chapter,
        progress: bookPlan
          && `${bookPlan.captured_count}/${bookPlan.total_puzzles}`,
      }) || label;
      // Fire-and-forget: receiver records this in capture-log.jsonl
      // and emits a single `[CAPTURE-SKIP] book=… Ch.X pos.Y pid=…
      // reason=…` line so a dropped puzzle is no longer
      // browser-console-only. `attempts` reflects the readiness-gate
      // attempts (1 = no retry, 2 = retried once and still failed).
      const attemptsTried = _pendingRecoveryAttempts > 0 ? _pendingRecoveryAttempts : 1;
      _pendingRecoveryAttempts = 0; // clear: this puzzle is being skipped
      reportBookEvent("puzzle_skipped", {
        reason: gate.reason,
        pid: expectedPid,
        chapter_number: ent && ent.chapter_number,
        chapter_position: ent && ent.pos_in_chapter,
        attempts: attemptsTried,
        ids,
      });
      failAndAdvance({
        logMsg: `${skipLabel} — capture refused: ${gate.reason} (data=${ids.dataPid} settled=${ids.settledPid} expected=${ids.expectedPid}). Skipping.`,
        statusText: `Skipped (${gate.reason})`,
      });
      return;
    }

    // Decode content field in JS (same algorithm as the site's own JS)
    // Clone qqdata to avoid mutating the page's runtime object
    const qq = getQqdata();
    if (!qq) {
      log("ERROR", "No qqdata available after readiness check");
      failAndAdvance({
        phase: "ERR",
        logMsg: `${label} — no qqdata after readiness check`,
        statusText: "No puzzle data. Skipping.",
      });
      return;
    }
    // Clone qqdata safely.
    // Try JSON.parse(JSON.stringify(qq)) FIRST: Alpine reactive proxies
    // are JSON-shaped (plain enumerables) and serialize cleanly, while
    // structuredClone can choke on the proxy machinery on some Vue/
    // Alpine builds. Fall back to structuredClone for any non-JSON-
    // safe shapes (Dates, BigInts, Maps).
    let payload;
    try {
      payload = JSON.parse(JSON.stringify(qq));
    } catch (e1) {
      try {
        payload = structuredClone(qq);
      } catch (e2) {
        failAndAdvance({
          phase: "ERR",
          logMsg: `${label} — cannot clone qqdata: ${e1.message} / ${e2.message}`,
          statusText: "Cannot read puzzle data. Skipping.",
          statusColor: "#f44336",
        });
        return;
      }
    }

    // IDENTITY: by this point qqdata is ready (post readiness gate),
    // so getPublicId() returns the canonical pid. Status bar shows
    // the same number as the saved filename.
    const pid = getPublicId();
    plog("GRAB", `${label} — decoding puzzle data`);
    updateStatus(`Capturing ${pid}...`, "#4fc3f7");

    try {
      // Decode all encoded fields on the clone (content, ok_answers, etc.)
      decodeEncodedFields(payload);
      const stones = decodeContentField(payload);
      if (stones) {
        payload.content = stones;
        plog("GRAB", `${label} — decoded ${stones[0].length}B + ${stones[1].length}W stones`);
      } else {
        plog("WARN", `${label} — no content decoded, falling back to prepos`);
      }

      // Scrape book links from the page DOM (fallback for empty bookinfos).
      // Wait briefly for the "Included in" section to render (it may load async).
      await waitForBookSection(3000);
      const pageBooks = scrapePageBooks();

      // Multi-layer harvest + reconciliation. Replaces the old strict
      // url==data==expected gate with quorum + best-effort attribution.
      // Result: never throw away a successful fetch — file the captured
      // puzzle under whatever book/chapter the page actually displayed,
      // not whatever the manifest cursor expected.
      const facts = harvestPageFacts();
      const pidResult = reconcilePid(facts);
      if (!pidResult.ok) {
        const c = pidResult.candidates;
        failAndAdvance({
          logMsg: `${label} — pid quorum failed (${pidResult.reason}): qq=${c.qqdata} url=${c.url} visible=${c.visible}. Skipping.`,
          statusText: "Skipped (pid_quorum)",
        });
        return;
      }
      const reconciledPid = pidResult.pid;
      const activeBookId = (bookPlan && bookPlan.book_id) || null;
      const manifestSeq = (bookPlan && bookPlan.chapter_seq) || null;
      const att = reconcileAttribution(facts, {
        activeBookId: activeBookId,
        manifestSeq: manifestSeq,
      });

      // What did the manifest cursor expect? Used for provenance only.
      let expectedPidFromManifest = null;
      if (isChapterMode() && Array.isArray(manifestSeq)) {
        const _e = manifestSeq[(bookPlan && bookPlan.current_seq_idx) || 0];
        if (_e && _e.pid) expectedPidFromManifest = Number(_e.pid);
      }

      // Drift detection: 3 consecutive captures landing on a different
      // book than the active capture target → log ERR but continue.
      // (User-confirmed policy: salvage rather than stop.)
      if (att.drift_from_active) {
        driftBookStreak += 1;
        if (driftBookStreak >= 3) {
          plog(
            "ERR",
            `Capture drift: ${driftBookStreak} consecutive captures routed to ` +
              `book ${att.book_id} (active=${activeBookId}). Saving anyway; review log.`,
          );
        }
      } else if (isBookCaptureActive()) {
        driftBookStreak = 0;
      }

      plog("SEND", `${label} — posting to backend`);
      const capturePayload = {
        qqdata: payload,
        url: location.href,
        captured_at: new Date().toISOString(),
      };
      if (pageBooks.length > 0) {
        capturePayload._page_books = pageBooks;
      }

      // Build _book_context from reconciled attribution. We use the
      // *detected* book — not the active book — so the receiver routes
      // cross-book salvages into the correct book directory (auto-
      // creating it if unknown via _resolve_book_dir).
      if (att.book_id) {
        const bookNameVisible = (typeof document !== "undefined" && document.title)
          ? document.title.replace(/\s*-\s*101WEIQI.*$/i, "").trim()
          : (att.book_name || "");
        capturePayload._book_context = {
          book_id: att.book_id,
          book_name: att.book_name || (bookPlan && bookPlan.book_name) || "",
          book_name_raw: att.book_name || (bookPlan && bookPlan.book_name) || "",
          book_name_visible: bookNameVisible,
          chapter_id: att.chapter_id || 0,
          chapter_number: att.chapter_number || 0,
          chapter_name: att.chapter_name || "",
          chapter_name_raw: att.chapter_name || "",
          chapter_name_visible: att.chapter_name || "",
          chapter_position: att.position || 0,
          global_position: att.global_position || 0,
          puzzle_id: reconciledPid,
          // Use chapter-style naming whenever we have a chapter id —
          // even for cross-book salvages — so the file lands at
          // chXX_PPP_slug_pid.sgf and is easy to re-file later.
          capture_mode: att.chapter_id ? "chapter" : (isChapterMode() ? "chapter" : "book"),
        };
      }

      // Always attach provenance — auditable record of which layers
      // agreed, which conflicted, and what the routing decision was.
      // Receiver appends this to capture-log.jsonl.
      capturePayload._capture_provenance = {
        reconciled_pid: reconciledPid,
        pid_agreed_layers: pidResult.agreed_layers,
        pid_conflicts: pidResult.conflicts,
        pid_candidates: pidResult.candidates,
        book_id: att.book_id,
        book_source: att.book_source,
        chapter_id: att.chapter_id,
        chapter_source: att.chapter_source,
        chapter_number: att.chapter_number,
        chapter_number_source: att.chapter_number_source,
        position: att.position,
        position_source: att.position_source,
        all_known_books: att.all_known_books,
        active_book_id: activeBookId,
        expected_pid_from_manifest: expectedPidFromManifest,
        drift_from_active: att.drift_from_active,
        drift_streak: driftBookStreak,
      };
      // Carry per-puzzle recovery signal so the receiver's [SAVED]
      // line can flag puzzles that landed only after a readiness-gate
      // retry. Cleared after attach so it's strictly per-puzzle.
      if (_pendingRecoveryAttempts > 0) {
        capturePayload._capture_meta = {
          recovered: true,
          attempts: _pendingRecoveryAttempts,
        };
        _pendingRecoveryAttempts = 0;
      }
      const result = await http("POST", "/capture", capturePayload);
      if (result.status === "ok") {
        issueStreak = 0;
        stats.ok++;
        lastCaptureWasDuplicate = false;
        plog("DONE", `${label} — saved as ${result.puzzle_id} (ok:${stats.ok} skip:${stats.skipped} err:${stats.error})`);
        updateStatus(`Saved ${result.puzzle_id}`, "#81c784");
      } else if (result.status === "skipped") {
        issueStreak = 0;
        stats.skipped++;
        lastCaptureWasDuplicate = true;
        // Surface the same context the backend now logs to the JSONL so
        // the in-page console matches the source-of-truth log.
        const ctx = capturePayload._book_context || {};
        const ctxParts = [];
        if (ctx.book_id) {
          ctxParts.push(`book=${ctx.book_id}`);
        }
        if (ctx.chapter_number) {
          ctxParts.push(`ch${ctx.chapter_number}${ctx.chapter_name ? ` '${ctx.chapter_name}'` : ""}`);
        }
        if (ctx.section_id) {
          ctxParts.push(`sec=${ctx.section_id}${ctx.section_name ? ` '${ctx.section_name}'` : ""}`);
        }
        if (ctx.chapter_position) {
          ctxParts.push(`ch_pos=${ctx.chapter_position}`);
        }
        if (ctx.section_position) {
          ctxParts.push(`sec_pos=${ctx.section_position}`);
        }
        if (ctx.global_position) {
          ctxParts.push(`gpos=${ctx.global_position}`);
        }
        const ctxStr = ctxParts.length ? ` [${ctxParts.join(" ")}]` : "";
        const reason = result.message || "duplicate";
        plog("SKIP", `${label} — ${reason} ${result.puzzle_id}${ctxStr} (ok:${stats.ok} skip:${stats.skipped} err:${stats.error})`);
        updateStatus(`Skipped ${result.puzzle_id} (${reason})`, "#ffb74d");
      } else {
        issueStreak += 1;
        stats.error++;
        lastCaptureWasDuplicate = false;
        plog("ERR", `${label} — server error: ${result.message}`);
        updateStatus(`Error: ${result.message}`, "#f44336");
        // Mark the pid as permanently failed for this book so the
        // chapter-mode skip-walk advances past it. Without this the
        // walk re-targets the same uncaptured pid forever (typically
        // the last entry in its chapter), producing the observed
        // "stuck on Ch.X pos N" loop.
        //
        // Trust the receiver's explicit `permanent` flag (added with
        // the validation-rejection path). Fall back to the implicit
        // rule (non-null puzzle_id ⇒ parsed-then-rejected ⇒ permanent)
        // for backward compat with older receiver versions.
        const isPermanent = (typeof result.permanent === "boolean")
          ? result.permanent
          : Boolean(result.puzzle_id);
        if (isPermanent && result.puzzle_id && bookPlan && bookPlan.book_id) {
          bookPlan.failed_ids = bookPlan.failed_ids || [];
          if (!bookPlan.failed_ids.includes(Number(result.puzzle_id))) {
            bookPlan.failed_ids.push(Number(result.puzzle_id));
            saveBookPlan(bookPlan);
            plog("SKIP", `Marked pid ${result.puzzle_id} as permanently failed (will skip future occurrences)`);
          }
        }
      }
    } catch (err) {
      issueStreak += 1;
      stats.error++;
      lastCaptureWasDuplicate = false;
      plog("ERR", `${label} — capture failed: ${err.message}, stopping`);
      stopRunning("server unreachable");
      updateStatus("Server unreachable! Start: python -m tools.weiqi101 receive", "#f44336");
      GM_setValue(KEY_STATS, stats);
      return;
    }

    GM_setValue(KEY_STATS, stats);
    // Track last captured page for navigation detection
    lastCapturedUrl = location.href;
    // IDENTITY: lastCapturedId is compared to alpineId (publicid) by the
    // navigation watcher; both must be the canonical publicid.
    lastCapturedId = getPublicId();
    lastTitle = document.title;
    if (isQdaySweepActive()) {
      syncQdayPlanFromPage();
    }
    if (running) goNext();
  }

  // -- Book picker UI ---------------------------------------------
  async function showBookPicker() {
    updateStatus("Loading book list from server...", "#4fc3f7");

    let books;
    try {
      const resp = await http("GET", "/books");
      books = resp.books;
    } catch (err) {
      log("ERROR", "Can't fetch books: " + err.message);
      updateStatus("Server unreachable!", "#f44336");
      return;
    }

    if (!books || books.length === 0) {
      alert(
        "No books discovered yet.\n\n" +
        "Run this in terminal first:\n" +
        "  python -m tools.weiqi101 discover-book-ids --book-id 197 --by-chapter\n\n" +
        "Replace 197 with the book ID you want."
      );
      return;
    }

    // Build a picker dialog
    const overlay = document.createElement("div");
    overlay.id = "yengo-picker";
    overlay.style.cssText =
      "position:fixed;top:0;left:0;right:0;bottom:0;z-index:1000000;" +
      "background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;";

    const dialog = document.createElement("div");
    dialog.style.cssText =
      "background:#1e1e2e;color:#e0e0e0;border-radius:8px;padding:20px;max-width:700px;" +
      "width:90%;max-height:80vh;overflow-y:auto;font:14px/1.6 monospace;";

    let html = `<h2 style="margin:0 0 12px;color:#4fc3f7;">Pick a Book to Download</h2>`;
    html += `<p style="color:#888;margin:0 0 12px;">${books.length} books available. Click one to start downloading.</p>`;
    html += `<table style="width:100%;border-collapse:collapse;">`;
    html += `<tr style="color:#888;text-align:left;border-bottom:1px solid #333;">` +
      `<th style="padding:4px 8px;">ID</th>` +
      `<th style="padding:4px 8px;">Name</th>` +
      `<th style="padding:4px 8px;">Diff</th>` +
      `<th style="padding:4px 8px;text-align:right;">Done</th>` +
      `<th style="padding:4px 8px;text-align:right;">Left</th>` +
      `<th style="padding:4px 8px;text-align:right;">Total</th></tr>`;

    for (const b of books) {
      const color = b.complete ? "#4caf50" : b.downloaded > 0 ? "#ffb74d" : "#e0e0e0";
      const statusIcon = b.complete ? "DONE" : b.downloaded > 0 ? "PARTIAL" : "";
      html += `<tr class="yengo-book-row" data-id="${b.book_id}" ` +
        `style="cursor:pointer;border-bottom:1px solid #222;" ` +
        `onmouseover="this.style.background='#2a2a3e'" onmouseout="this.style.background='none'">` +
        `<td style="padding:6px 8px;color:#888;">${b.book_id}</td>` +
        `<td style="padding:6px 8px;color:${color};">${b.name || b.name_cn} ` +
        `<span style="color:#555;font-size:11px;">${statusIcon}</span></td>` +
        `<td style="padding:6px 8px;color:#888;">${b.difficulty}</td>` +
        `<td style="padding:6px 8px;text-align:right;color:#4caf50;">${b.downloaded}</td>` +
        `<td style="padding:6px 8px;text-align:right;color:${b.remaining > 0 ? '#ff9800' : '#4caf50'};">${b.remaining}</td>` +
        `<td style="padding:6px 8px;text-align:right;color:#888;">${b.total}</td></tr>`;
    }
    html += `</table>`;
    html += `<p style="margin:16px 0 0;text-align:right;">` +
      `<button id="yengo-close" style="background:#333;color:#e0e0e0;border:none;padding:8px 16px;` +
      `border-radius:4px;cursor:pointer;font:14px monospace;">Cancel</button></p>`;

    dialog.innerHTML = html;
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Event handlers
    document.getElementById("yengo-close").onclick = () => overlay.remove();
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    dialog.querySelectorAll(".yengo-book-row").forEach((row) => {
      row.onclick = async () => {
        const bookId = parseInt(row.dataset.id, 10);
        overlay.remove();
        await startBook(bookId);
      };
    });
  }

  async function startBook(bookId) {
    // startBook always claims — it's an explicit user action in this tab
    clearQdayPlan();
    clearBookDiscovery();
    clearBookPlan();
    issueStreak = 0;

    // Capture current page before navigating away (don't lose it)
    if (isQqdataReady() && !running) {
      log("INFO", "Capturing current page before starting book...");
      await capture();
    }

    log("INFO", `Starting book download: ${bookId}`);
    updateStatus(`Loading book ${bookId}...`, "#4fc3f7");

    try {
      const result = await http("POST", "/queue/book", { book_id: bookId });
      if (result.error) {
        log("ERROR", result.error);
        updateStatus("Error: " + result.error, "#f44336");
        alert("Error: " + result.error);
        return;
      }

      log("INFO", `Book ${bookId} loaded: ${result.pending} pending, ${result.already_downloaded} done`, result);
      updateStatus(
        `Book: "${result.book_name}" -- ${result.pending} to go (${result.already_downloaded} already done)`,
        "#4fc3f7"
      );

      claimOwnership();  // Explicit user action — force-claim this tab
      startRunning();

      const next = await http("GET", "/next");
      if (next.status === "ok") {
        location.href = next.url;
      } else {
        updateStatus("Book fully downloaded already!", "#4caf50");
        stopRunning("book already downloaded");
      }
    } catch (err) {
      log("ERROR", err.message);
      updateStatus("Server error: " + err.message, "#f44336");
    }
  }

  // -- Auto-detect: check server queue on page load ---------------
  let lastCapturedUrl = null;
  let lastCapturedId = null;
  let lastCaptureWasDuplicate = false; // Fast-skip flag for goNext()

  async function autoStart(opts = {}) {
    const userInitiated = !!opts.userInitiated;

    // v5.37.0: EXPLICIT-RESUME-ONLY MODEL.
    //
    // After [Control] Pause / [Control] Stop, we NEVER auto-resume in
    // any tab \u2014 the user must explicitly click [Control] Resume (or
    // [Control] Take Ownership). This prevents two failure modes that
    // both used to silently restart capture in the wrong tab:
    //
    //   1. User stops the sweep in Tab A, opens any /q/{pid}/ URL in
    //      Tab B for troubleshooting \u2192 Tab B used to claim ownership
    //      and resume against the (still-active) bookPlan.
    //   2. Tab A crashes, heartbeat goes stale, user opens Tab B \u2192
    //      Tab B used to silently take over a stale lock.
    //
    // Both paths now require an explicit menu action. Same-tab
    // navigation within an active session still works because we
    // already own the lock and `running` is still true.
    if (isUserPaused() && !userInitiated) {
      updateStatus("Paused \u2014 use [Control] Resume to continue.", "#ff9800");
      return;
    }

    // Tab ownership check: only the owner tab drives sweep/queue.
    // Non-owner tabs just capture the current page passively.
    const currentOwner = GM_getValue(KEY_OWNER_TAB, null);
    const ownerIsOther = currentOwner && currentOwner !== TAB_ID && !isOwnerStale();

    // Auto-resume an active session is allowed only when:
    //   (a) the call is explicitly user-initiated (menu Resume / Take
    //       Ownership), OR
    //   (b) we already own the lock AND `running` is true \u2014 i.e. this
    //       is a same-tab navigation continuing a live session.
    // Never auto-claim a vacant or stale lock; that was the Tab B
    // auto-resume bug (v5.37.0).
    const canAutoResume = userInitiated || (running && isOwnerTab());

    if (isQdaySweepActive()) {
      if (ownerIsOther) {
        updateStatus(`Observing \u2014 sweep running in another tab`, "#888");
        return;
      }
      if (!canAutoResume) {
        updateStatus("Qday plan loaded \u2014 use [Control] Resume to start.", "#888");
        return;
      }
      if (userInitiated && !startRunning()) return;
      const planUrl = buildQdayUrl(qdayPlan.currentDate, qdayPlan.currentNum);
      if (location.href !== planUrl) {
        updateStatus(`Resuming qday sweep at ${qdayPlan.currentDate} #${qdayPlan.currentNum}`, "#4fc3f7");
        location.href = planUrl;
        return;
      }
    }

    // Book discovery: continue navigating book/chapter pages.
    // v5.38.0 interleaved flow: capture takes precedence over
    // discovery when both are in storage (discovery is paused via
    // bookDiscovery.awaiting_capture and resumes after capture
    // completes the current chapter scope).
    if (isBookDiscoveryActive() && isBookPage() && !isBookCaptureActive()) {
      if (ownerIsOther) {
        updateStatus(`Observing \u2014 discovery running in another tab`, "#888");
        return;
      }
      if (!canAutoResume) {
        updateStatus("Discovery state loaded \u2014 use [Control] Resume to continue.", "#888");
        return;
      }
      if (userInitiated) claimOwnership();
      continueDiscovery();
      return;
    }

    // Book page with no active discovery: do NOT auto-popup any modal.
    // The user explicitly requested that capture only starts when they
    // click "[Book] Start / Resume" from the menu — no nag dialogs on
    // page navigation. We just leave a passive status badge and store the
    // current book_id so the menu command can pick it up without
    // re-prompting.
    if (isBookPage() && !isBookDiscoveryActive() && !isBookCaptureActive()) {
      const bookPath = parseBookPath();
      if (bookPath && bookPath.book_id) {
        try { GM_setValue("pendingBookId", bookPath.book_id); } catch (_) {}
        updateStatus(
          `Idle on book ${bookPath.book_id} — use [Book] Start / Resume in menu`,
          "#888"
        );
      }
      return;
    }

    // Book capture: resume
    if (isBookCaptureActive()) {
      if (ownerIsOther) {
        updateStatus(`Observing \u2014 book capture running in another tab`, "#888");
        return;
      }
      if (!canAutoResume) {
        const name = bookPlan.book_name || `Book ${bookPlan.book_id}`;
        updateStatus(`Book "${name}" loaded \u2014 use [Control] Resume to continue.`, "#888");
        return;
      }
      if (userInitiated && !startRunning()) return;

      if (isChapterMode()) {
        // Chapter mode: skip already-captured entries from the saved
        // index forward, then resume via the chapter-listing route.
        // We never use /q/{pid}/ directly (see clickPuzzleInChapterListing).
        const captured = new Set((bookPlan.captured_ids || []).map(Number));
        let idx = bookPlan.current_seq_idx || 0;
        while (
          idx < bookPlan.chapter_seq.length &&
          captured.has(Number(bookPlan.chapter_seq[idx].pid))
        ) {
          idx++;
        }
        if (idx >= bookPlan.chapter_seq.length) {
          const name = bookPlan.book_name || `Book ${bookPlan.book_id}`;
          plog("DONE", `Chapter capture: "${name}" already complete`);
          updateStatus(`"${name}" — already complete`, "#4caf50");
          stopRunning();
          clearBookPlan();
          return;
        }
        if (idx !== bookPlan.current_seq_idx) {
          bookPlan.current_seq_idx = idx;
          bookPlan.current_idx = idx;
          saveBookPlan(bookPlan);
        }
        const entry = bookPlan.chapter_seq[idx];
        const progressStr = `Ch.${entry.chapter_number} pos ${entry.pos_in_chapter} (${bookPlan.captured_count || 0}/${bookPlan.total_puzzles})`;
        const bp = parseBookPath();

        // Case 1: already on any puzzle page within the right book+chapter.
        // Identity (publicid) is verified by awaitCaptureReadiness inside
        // capture(); we only check book+chapter routing here. URL pid is
        // not consulted (it may be qid ≠ publicid). See banner at top.
        const onPuzzlePageInRightChapter =
          bp
          && bp.type === "puzzle"
          && bp.book_id === bookPlan.book_id
          && bp.chapter_id === entry.chapter_id;
        if (onPuzzlePageInRightChapter) {
          plog("RESUME", `[case1/on-puzzle] Ch.${entry.chapter_id} expected publicid=${entry.pid} (gate will verify) — capturing`);
          updateStatus(`Resuming chapter at ${progressStr}`, "#4fc3f7");
          capture();
          return;
        }

        // Case 2: on the right chapter listing — click the entry.
        if (
          bp
          && bp.type === "chapter"
          && bp.book_id === bookPlan.book_id
          && bp.chapter_id === entry.chapter_id
        ) {
          plog("RESUME", `[case2/on-listing] Ch.${entry.chapter_id} p.${bp.page || 1} — clicking pid ${entry.pid} (${progressStr})`);
          updateStatus(`Resuming chapter at ${progressStr}`, "#4fc3f7");
          await clickPuzzleInChapterListing(entry.pid);
          return;
        }

        // Case 3: anywhere else — navigate to the chapter listing first.
        if (!entry.chapter_id) {
          plog("ERR", `Entry pid=${entry.pid} has no chapter_id — manifest needs re-discovery`);
          stopRunning();
          return;
        }
        const resumePage = targetChapterPageForEntry(entry);
        plog("RESUME", `[case3/elsewhere] navigating to Ch.${entry.chapter_id} p.${resumePage} for ${progressStr} (from ${location.pathname})`);
        updateStatus(`Resuming chapter at ${progressStr}`, "#4fc3f7");
        location.href = buildChapterUrl(bookPlan.book_id, entry.chapter_id, resumePage);
        return;
      }
    }

    // ─── Idle path (v5.37.0) ────────────────────────────────────
    // We get here when no qday/discovery/book-capture plan is active.
    // The previous behaviour was:
    //   1. Poll /queue/status \u2014 if the backend reported a queue, call
    //      startRunning() automatically (silent auto-start).
    //   2. Unconditionally `capture()` whatever puzzle the page shows.
    //
    // Both behaviours violated the "never auto-start without an
    // explicit user action" rule the moment the user pasted a fresh
    // script onto a /book/ or /q/ page.
    //
    // New rule: capture() only fires when ONE of:
    //   * userInitiated (menu Resume / Take Ownership)
    //   * we already own the lock AND `running` is true (i.e. an
    //     in-session SPA/AJAX navigation calling autoStart() to
    //     re-route)
    //   * another tab owns the lock (we're a passive observer that
    //     shouldn't disturb their session)
    //
    // The /queue/status auto-start is gated behind userInitiated as
    // well \u2014 the backend-driven flow is "user clicks Resume, we
    // pick up whatever the receiver has queued."
    if (running && isOwnerTab()) {
      capture();
      return;
    }
    if (ownerIsOther) {
      // Another tab owns \u2014 capture this page passively (read-only).
      capture();
      return;
    }
    if (userInitiated) {
      try {
        const q = await http("GET", "/queue/status");
        if (q.active && q.pending > 0) {
          log("INFO", `Server has active queue: ${q.pending} pending, auto-starting`);
          if (!startRunning()) return;
          updateStatus(
            `Auto-detected queue: ${q.book_name || q.source || "custom"} -- ${q.pending} pending`,
            "#4fc3f7"
          );
          capture();
          return;
        }
      } catch {
        // Server not running -- that's fine.
      }
      capture();
      return;
    }
    // Fresh boot, no active session, no user action: idle.
    updateStatus("Idle \u2014 use [Book] Start / Resume or [Control] Resume to begin.", "#888");
  }

  //#endregion 7. NAVIGATION

  //#region 8. CAPTURE LOOP
  // -- Navigation watcher (SPA detection) -------------------------
  // The site's next/prev buttons load new puzzles via AJAX without
  // changing the URL.  Three independent signals detect this:
  //   1. document.title  ("第1题" -> "第2题")  -- most reliable
  //   2. Alpine.store('qipan').qqdata.publicid  -- direct puzzle ID
  //   3. location.href  -- fallback for full-page navigations
  // Any ONE changing triggers a debounced re-capture.

  let navDebounce = null;
  let lastTitle = null;

  function startNavigationWatcher() {
    lastTitle = document.title;

    setInterval(() => {
      if (running) return; // Queue mode handles its own navigation
      if (lastCapturedUrl === null) return; // Initial capture not done

      // Signal 1: page title change (always accessible, no sandbox issues)
      const titleChanged = document.title !== lastTitle;

      // Signal 2: Alpine store puzzle ID change
      let alpineIdChanged = false;
      try {
        const qipan = unsafeWindow.Alpine && unsafeWindow.Alpine.store("qipan");
        const alpineId = qipan && qipan.qqdata && parseInt(qipan.qqdata.publicid, 10);
        if (alpineId && alpineId !== lastCapturedId) {
          alpineIdChanged = true;
        }
      } catch (_) {}

      // Signal 3: URL change (full-page navigation on /q/ pages)
      const urlChanged = location.href !== lastCapturedUrl;

      if (!titleChanged && !alpineIdChanged && !urlChanged) return;

      log("INFO", `Navigation detected: title=${titleChanged} alpine_id=${alpineIdChanged} url=${urlChanged} "${lastTitle}" -> "${document.title}"`);

      // Advance change-detection state IMMEDIATELY (not inside the
      // debounced callback). The interval period (1000ms) is shorter
      // than the debounce window (1500ms); if we waited to update
      // lastTitle until the timer fired, every interval tick would
      // re-clear and re-arm the timer, the timer would never fire,
      // and the log would spam forever after a manual stop+navigate.
      // The debounce only needs to coalesce capture() calls — the
      // "is this still the same page?" state can advance eagerly.
      lastTitle = document.title;
      lastCapturedUrl = location.href;
      try {
        const qipan = unsafeWindow.Alpine && unsafeWindow.Alpine.store("qipan");
        const alpineId = qipan && qipan.qqdata && parseInt(qipan.qqdata.publicid, 10);
        if (alpineId) lastCapturedId = alpineId;
      } catch (_) {}

      // Debounce: wait for the page to settle before capturing
      if (navDebounce) clearTimeout(navDebounce);
      navDebounce = setTimeout(async () => {
        navDebounce = null;
        await waitForQqdata();
        capture();
      }, 1500);
    }, 1000);
  }

  //#endregion 8. CAPTURE LOOP

  //#region 9. MENU COMMANDS
  // -- Menu commands (consolidated) --------------------------------
  // Grouped: Book | Daily | Control | Settings

  // --- BOOK ---
  GM_registerMenuCommand("[Book] Start / Resume", () => {
    if (isBookCaptureActive()) {
      // Already capturing — offer to resume
      const progress = isChapterMode()
        ? `Ch.${(chapterPlanCurrentEntry(bookPlan) || {}).chapter_number || "?"} pos ${(chapterPlanCurrentEntry(bookPlan) || {}).pos_in_chapter || "?"}, ${bookPlan.captured_count || bookPlan.captured_ids.length}/${bookPlan.total_puzzles}`
        : `${bookPlan.captured_ids.length} captured`;
      const ok = confirm(
        `Chapter capture active: "${bookPlan.book_name}"\n` +
        `${progress}\n\n` +
        `Click OK to resume, Cancel to pick a new book.`
      );
      if (ok) { capture(); return; }
      clearBookPlan();
    }
    if (isBookDiscoveryActive()) {
      const ok = confirm(
        `Discovery in progress: "${bookDiscovery.book_name}"\n` +
        `Phase: ${bookDiscovery.phase}\n\n` +
        `Click OK to resume, Cancel to start fresh.`
      );
      if (ok) { continueDiscovery(); return; }
      clearBookDiscovery();
    }
    // Context-aware: if we're already on a /book/ page, open the
    // discovery overlay directly without re-prompting.
    const onPagePath = parseBookPath();
    if (onPagePath && onPagePath.book_id) {
      clearBookDiscovery();
      clearBookPlan();
      clearQdayPlan();
      showBookDiscoveryOverlay(onPagePath.book_id);
      return;
    }
    // Fallback: prompt for book ID or show picker
    const bookId = prompt("Enter 101weiqi book ID (e.g., 5121)\nor leave blank to browse:");
    if (bookId === null) return; // cancelled
    if (bookId.trim() === "") {
      showBookPicker();
      return;
    }
    const id = parseInt(bookId, 10);
    if (isNaN(id)) { alert("Invalid book ID"); return; }
    clearBookDiscovery();
    clearBookPlan();
    clearQdayPlan();
    location.href = `https://www.101weiqi.com/book/${id}/`;
  });

  GM_registerMenuCommand("[Book] Skip to Capture", async () => {
    const bookId = prompt("Enter book ID to resume capture (manifest must exist).\nThis starts CHAPTER mode (walks chapters in order, skips already-captured puzzles):");
    if (!bookId || isNaN(parseInt(bookId, 10))) return;
    await startChapterCapture(parseInt(bookId, 10));
  });

  GM_registerMenuCommand("[Book] Chapter Capture", async () => {
    const input = prompt("Enter book ID for chapter-mode capture\n(reads manifest.chapters[].puzzle_ids and walks them in order):");
    if (!input || isNaN(parseInt(input, 10))) return;
    const id = parseInt(input, 10);
    clearBookDiscovery();
    clearBookPlan();
    clearQdayPlan();
    await startChapterCapture(id);
  });

  GM_registerMenuCommand("[Book] Jump To Chapter…", async () => {
    // Manual override:
    //   - In chapter-capture mode: jump current_seq_idx to the first
    //     puzzle of the requested chapter number.
    //   - In discovery mode: set current_chapter_idx and navigate to
    //     that chapter's page 1 (skipping any chapters in between).
    if (isBookCaptureActive() && isChapterMode() && Array.isArray(bookPlan.chapter_seq)) {
      const chapters = [...new Set(bookPlan.chapter_seq.map((e) => e.chapter_number))].sort((a, b) => a - b);
      const input = prompt(
        `Chapter capture active for "${bookPlan.book_name}".\n` +
        `Available chapters: ${chapters.join(", ")}\n\n` +
        `Enter chapter number to jump to:`
      );
      if (input === null) return;
      const target = parseInt(input, 10);
      if (isNaN(target)) { alert("Invalid chapter number"); return; }
      const idx = bookPlan.chapter_seq.findIndex((e) => e.chapter_number === target);
      if (idx < 0) { alert(`Chapter ${target} not found in this book`); return; }
      bookPlan.current_seq_idx = idx;
      bookPlan.current_idx = idx;
      saveBookPlan(bookPlan);
      const entry = bookPlan.chapter_seq[idx];
      plog("JUMP", `Manual jump -> Ch.${entry.chapter_number} pos ${entry.pos_in_chapter} (pid=${entry.pid})`);
      updateStatus(`Jumping to Ch.${entry.chapter_number} pos ${entry.pos_in_chapter}`, "#ffb74d");
      // Navigate via the chapter listing (autoStart will click the entry).
      // Direct /q/{pid}/ jumps look like bot behavior — see startChapterCapture.
      if (!entry.chapter_id) {
        alert("This manifest is missing chapter_id; please re-run discovery before using Jump To Chapter.");
        return;
      }
      const jumpPage = targetChapterPageForEntry(entry);
      location.href = buildChapterUrl(bookPlan.book_id, entry.chapter_id, jumpPage);
      return;
    }
    if (isBookDiscoveryActive() && Array.isArray(bookDiscovery.chapters)) {
      const chapters = bookDiscovery.chapters.map((c) => c.chapter_number);
      const input = prompt(
        `Discovery active for "${bookDiscovery.book_name}".\n` +
        `Available chapters: ${chapters.join(", ")}\n\n` +
        `Enter chapter number to jump to (will skip past earlier chapters):`
      );
      if (input === null) return;
      const target = parseInt(input, 10);
      if (isNaN(target)) { alert("Invalid chapter number"); return; }
      const idx = bookDiscovery.chapters.findIndex((c) => c.chapter_number === target);
      if (idx < 0) { alert(`Chapter ${target} not found`); return; }
      bookDiscovery.current_chapter_idx = idx;
      bookDiscovery.current_page = 1;
      bookDiscovery.phase = "chapter_puzzles";
      saveBookDiscovery(bookDiscovery);
      const ch = bookDiscovery.chapters[idx];
      plog("JUMP", `Manual jump -> discovery Ch.${ch.chapter_number} "${ch.name}"`);
      updateStatus(`Jumping discovery to Ch.${ch.chapter_number}`, "#ffb74d");
      location.href = buildChapterUrl(bookDiscovery.book_id, ch.chapter_id, 1);
      return;
    }
    alert("No active book capture or discovery to jump within.\nStart a capture/discovery first, then use this command.");
  });

  // --- BOOK: destructive resets (explicit confirmation required) ---
  // [Control] Stop preserves state. These commands exist for the
  // (rare) case where the user wants to throw the saved checkpoint
  // away and start over from scratch.

  GM_registerMenuCommand("[Book] Force Rediscovery", () => {
    // Need a book id from one of: active discovery, active capture,
    // current /book/ page, or user prompt.
    let bookId = null;
    let bookName = "";
    if (bookDiscovery && bookDiscovery.book_id) {
      bookId = bookDiscovery.book_id;
      bookName = bookDiscovery.book_name || `Book ${bookId}`;
    } else if (bookPlan && bookPlan.book_id) {
      bookId = bookPlan.book_id;
      bookName = bookPlan.book_name || `Book ${bookId}`;
    } else {
      const bp = parseBookPath();
      if (bp && bp.book_id) {
        bookId = bp.book_id;
        bookName = `Book ${bookId} (current page)`;
      }
    }
    if (!bookId) {
      const input = prompt("Enter book ID to force-rediscover (will discard backend checkpoint):");
      if (!input) return;
      bookId = parseId(input);
      if (!bookId) { alert("Invalid book ID"); return; }
      bookName = `Book ${bookId}`;
    }
    const ok = confirm(
      `Force rediscovery of "${bookName}"?\n\n` +
      `This will:\n` +
      `  \u2022 Discard the in-memory discovery checkpoint\n` +
      `  \u2022 Discard the in-memory capture plan (if any)\n` +
      `  \u2022 Re-scan every chapter page from scratch\n\n` +
      `Existing captured puzzles on disk are NOT touched.\n` +
      `Backend manifest will be overwritten when discovery completes.`,
    );
    if (!ok) return;
    stopRunning("force rediscovery");
    clearBookDiscovery();
    clearBookPlan();
    GM_notification({ text: `Force rediscovery: "${bookName}"`, title: "YenGo", timeout: 5000 });
    plog("WARN", `\u2550\u2550\u2550 FORCE REDISCOVERY: "${bookName}" \u2550\u2550\u2550`);
    location.href = `https://www.101weiqi.com/book/${bookId}/`;
  });

  GM_registerMenuCommand("[Book] Force Recapture", async () => {
    // Force a chapter-mode capture restart from the manifest. Wipes
    // in-memory bookPlan (which holds captured_ids/failed_ids/cursor)
    // but keeps the backend manifest \u2014 this is NOT a re-discovery.
    // Useful when the cursor got stuck and you want to walk the
    // already-discovered manifest again. The skip-list rebuilds from
    // server-side known_ids on startChapterCapture(), so already-
    // saved puzzles are automatically skipped.
    let bookId = null;
    let bookName = "";
    if (bookPlan && bookPlan.book_id) {
      bookId = bookPlan.book_id;
      bookName = bookPlan.book_name || `Book ${bookId}`;
    } else if (bookDiscovery && bookDiscovery.book_id) {
      bookId = bookDiscovery.book_id;
      bookName = bookDiscovery.book_name || `Book ${bookId}`;
    } else {
      const bp = parseBookPath();
      if (bp && bp.book_id) {
        bookId = bp.book_id;
        bookName = `Book ${bookId} (current page)`;
      }
    }
    if (!bookId) {
      const input = prompt("Enter book ID to force-recapture (manifest must exist on backend):");
      if (!input) return;
      bookId = parseId(input);
      if (!bookId) { alert("Invalid book ID"); return; }
      bookName = `Book ${bookId}`;
    }
    const ok = confirm(
      `Force recapture of "${bookName}"?\n\n` +
      `This will:\n` +
      `  \u2022 Discard the in-memory capture cursor (current_seq_idx, captured_ids, failed_ids)\n` +
      `  \u2022 Reload the manifest from the backend\n` +
      `  \u2022 Restart chapter walk from the first uncaptured puzzle\n\n` +
      `Existing captured puzzles on disk are NOT re-fetched (skip-list rebuilds from backend).\n` +
      `The backend manifest is NOT changed (use Force Rediscovery for that).`,
    );
    if (!ok) return;
    stopRunning("force recapture");
    clearBookPlan();
    GM_notification({ text: `Force recapture: "${bookName}"`, title: "YenGo", timeout: 5000 });
    plog("WARN", `\u2550\u2550\u2550 FORCE RECAPTURE: "${bookName}" \u2550\u2550\u2550`);
    await startChapterCapture(bookId);
  });

  // --- DAILY ---
  GM_registerMenuCommand("[Daily] Start Sweep", () => {
    const order = prompt("Enter sweep order:\n  1 = ascending (1→8)\n  2 = descending (8→1)", "2");
    if (order === null) return;
    startQdaySweep(order === "1" ? "asc" : "desc");
  });

  // --- STATUS (combined) ---
  GM_registerMenuCommand("[Status] Show All", async () => {
    let msg = "";

    // Book state
    if (isBookDiscoveryActive()) {
      const d = bookDiscovery;
      const totalIds = d.chapters.reduce((s, c) => s + c.puzzle_ids.length, 0);
      msg += `── Book Discovery ──\n` +
        `"${d.book_name}" (ID: ${d.book_id})\n` +
        `Phase: ${d.phase}  Ch: ${d.current_chapter_idx + 1}/${d.chapters.length}\n` +
        `Chapter IDs: ${totalIds}\n\n`;
    } else if (isBookCaptureActive()) {
      const cur = chapterPlanCurrentEntry(bookPlan) || {};
      const total = bookPlan.total_puzzles || (bookPlan.chapter_seq || []).length;
      msg += `── Chapter Capture ──\n` +
        `"${bookPlan.book_name}" (ID: ${bookPlan.book_id})\n` +
        `Ch.${cur.chapter_number || "?"} pos ${cur.pos_in_chapter || "?"} (pid=${cur.pid || "?"})\n` +
        `Captured: ${bookPlan.captured_count || bookPlan.captured_ids.length}/${total}\n` +
        `Started: ${bookPlan.started_at}\n\n`;
    }

    // Daily state
    if (isQdaySweepActive()) {
      msg += `── Daily Sweep ──\n` +
        `Date: ${qdayPlan.currentDate}  Puzzle: ${qdayPlan.currentNum}\n` +
        `Target: ${qdayPlan.targetDate}  Order: ${qdayPlan.order === "desc" ? "8→1" : "1→8"}\n\n`;
    }

    // Session stats
    msg += `── Session ──\n` +
      `OK: ${stats.ok}  Skip: ${stats.skipped}  Err: ${stats.error}  CAPTCHA: ${stats.captcha || 0}\n` +
      `Running: ${running}  Owner: ${isOwnerTab() ? "this tab" : "other"}\n` +
      `Wake lock: ${wakeLockEnabled ? "on" : "off"}\n`;

    // Server telemetry
    try {
      const t = await http("GET", "/telemetry");
      msg += `\n── Server ──\n` +
        `Total: ${t.total_processed}  Avg: ${t.avg_duration_ms}ms\n`;
    } catch (_) {
      msg += `\n── Server: unreachable ──\n`;
    }

    alert(msg || "Nothing active.");
  });

  // --- CONTROL ---
  // ─── Pause / Stop / Resume (v5.37.0) ────────────────────────────
  // Three menu commands, two semantically distinct operations:
  //   [Control] Pause  \u2014 halt the loop, preserve plan, mark user-paused.
  //   [Control] Stop   \u2014 same as Pause, plus tells the backend
  //                       /queue/stop. Functionally equivalent for
  //                       the userscript's own state machine.
  //   [Control] Resume \u2014 the ONLY way to restart the loop after
  //                       Pause/Stop. Clears the user-pause flag,
  //                       claims ownership in *this* tab, and kicks
  //                       autoStart({userInitiated: true}).
  //
  // EXPLICIT-RESUME-ONLY rule (v5.37.0): no tab \u2014 not the original
  // owner, not a fresh tab opened on a /q/ URL \u2014 will ever
  // auto-resume after Pause/Stop. The user must consciously click
  // Resume. See the long comment in autoStart() for rationale.
  function _pauseCommon(reasonLabel, opts = {}) {
    const notifyServer = !!opts.notifyServer;
    if (bookPlan && bookPlan.active) {
      const durationMs = bookPlan.started_at
        ? Date.now() - new Date(bookPlan.started_at).getTime() : 0;
      const durationMin = (durationMs / 60000).toFixed(1);
      const cur = chapterPlanCurrentEntry(bookPlan) || {};
      plog("END", `\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 SESSION ${reasonLabel.toUpperCase()} \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`);
      plog("END", `Book: "${bookPlan.book_name}" \u2014 ${reasonLabel} (state preserved)`);
      plog("END", `Last: Ch.${cur.chapter_number || "?"} pos ${cur.pos_in_chapter || "?"} (pid=${cur.pid || "?"})`);
      plog("END", `Captured: ${stats.ok}, Skipped: ${stats.skipped}, Errors: ${stats.error}`);
      plog("END", `Duration: ${durationMin} min | Time: ${new Date().toISOString()}`);
    } else if (bookDiscovery) {
      plog("END", `\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550 DISCOVERY ${reasonLabel.toUpperCase()} \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550`);
      plog("END", `Book: "${bookDiscovery.book_name}" \u2014 ${reasonLabel} at Ch.${(bookDiscovery.current_chapter_idx || 0) + 1}/${bookDiscovery.chapters.length} (state preserved)`);
    }
    setUserPaused(true);
    stopRunning(`user ${reasonLabel}`);
    if (notifyServer) {
      // Best-effort: don't block.
      http("GET", "/queue/stop").catch(() => {});
    }
    reportBookEvent("session_paused", {
      reason: reasonLabel,
      captured_count: bookPlan ? (bookPlan.captured_count || 0) : 0,
      total: bookPlan ? (bookPlan.total_puzzles || null) : null,
    });
    // Post-capture session summary: structured event for capture-log.jsonl.
    if (bookPlan && bookPlan.active) {
      const summaryDurationMs = bookPlan.started_at
        ? Date.now() - new Date(bookPlan.started_at).getTime() : 0;
      reportBookEvent("session_summary", {
        captured: stats.ok || 0,
        skipped: stats.skipped || 0,
        errors: stats.error || 0,
        duration_ms: summaryDurationMs,
        total_in_manifest: bookPlan.total_puzzles || 0,
        start_idx: bookPlan._start_idx || 0,
        end_idx: bookPlan.current_seq_idx || 0,
      });
    }
    updateStatus(`${reasonLabel === "stopped" ? "Stopped" : "Paused"} (state preserved). Use [Control] Resume to continue.`, "#ff9800");
  }

  GM_registerMenuCommand("[Control] Pause", () => {
    _pauseCommon("paused");
  });

  GM_registerMenuCommand("[Control] Resume", () => {
    // BACKEND RECOVERY: if there is no in-memory plan at all (e.g.
    // after a fresh refresh, or after a pre-v5.30.1 destructive
    // Stop), and we're sitting on a /book/ page, route through the
    // discovery-overlay flow instead of no-op'ing the resume.
    if (!bookPlan && !bookDiscovery && !qdayPlan) {
      const bp = parseBookPath();
      if (bp && bp.book_id) {
        plog(
          "INFO",
          `[Resume] No in-memory state \u2014 attempting backend recovery for book ${bp.book_id}`,
        );
        updateStatus("Recovering state from backend\u2026", "#4fc3f7");
        setUserPaused(false);
        if (bp.type === "book") {
          showBookDiscoveryOverlay(bp.book_id);
        } else {
          location.href = `https://www.101weiqi.com/book/${bp.book_id}/`;
        }
        return;
      }
      updateStatus("Nothing to resume. Use [Book] Start / Resume.", "#ff9800");
      plog(
        "WARN",
        "[Resume] No in-memory state and not on a /book/ page \u2014 cannot recover. Use [Book] Start / Resume.",
      );
      return;
    }
    if (running && isOwnerTab()) {
      updateStatus("Already running in this tab.", "#4caf50");
      return;
    }
    if (!startRunning()) return; // also clears KEY_USER_PAUSED
    updateStatus("Resumed.", "#4fc3f7");
    plog("INFO", "\u2550\u2550\u2550 RESUMED \u2014 capture loop restarting \u2550\u2550\u2550");
    try {
      if (!bookPlan && !bookDiscovery && !qdayPlan) {
        plog(
          "RESUME",
          `state: page=${location.pathname} \u2014 no plan loaded ` +
            `(use [Book] Start / Resume or browse to a /book/ page to seed state)`,
        );
      } else if (bookDiscovery) {
        plog(
          "RESUME",
          `state: page=${location.pathname} discovery="${bookDiscovery.book_name}" ` +
            `phase=${bookDiscovery.phase} ch=${(bookDiscovery.current_chapter_idx || 0) + 1}/${bookDiscovery.chapters.length}`,
        );
      } else if (bookPlan) {
        const cur = chapterPlanCurrentEntry(bookPlan) || {};
        plog(
          "RESUME",
          `state: page=${location.pathname} urlToken=${getUrlRouteToken()} publicid=${getPublicId()} ` +
            `idx=${bookPlan.current_seq_idx} ` +
            `captured=${(bookPlan.captured_ids || []).length} ` +
            `target=Ch.${cur.chapter_number || "?"}/p${cur.pos_in_chapter || "?"}/pid${cur.pid || "?"}`,
        );
      } else if (qdayPlan) {
        plog("RESUME", `state: qday ${qdayPlan.currentDate} #${qdayPlan.currentNum}`);
      }
    } catch (e) {
      log("DEBUG", "RESUME diagnostic failed: " + e.message);
    }
    reportBookEvent("session_resumed", {});
    autoStart({ userInitiated: true });
  });

  GM_registerMenuCommand("[Control] Stop", () => {
    // Same state-preserving semantics as [Control] Pause, plus a
    // best-effort signal to the backend's queue. Kept as a separate
    // menu entry for the operator who thinks of "stop" as more
    // emphatic than "pause" \u2014 there's no functional difference for
    // the userscript itself.
    _pauseCommon("stopped", { notifyServer: true });
  });

  GM_registerMenuCommand("[Control] Take Ownership", () => {
    // Explicit user action \u2014 clears any pending pause flag and
    // claims ownership in this tab. Restarts the loop only if a
    // session was already marked running.
    setUserPaused(false);
    claimOwnership();
    if (GM_getValue(KEY_RUNNING, false)) {
      running = true;
      if (wakeLockEnabled) acquireWakeLock();
      updateStatus(`This tab (${TAB_ID}) is now the active runner \u2014 resuming...`, "#4fc3f7");
      capture();
    } else {
      updateStatus(`This tab (${TAB_ID}) claimed ownership (idle).`, "#4fc3f7");
    }
  });

  // --- SETTINGS ---
  GM_registerMenuCommand("[Settings] Toggle Wake Lock", () => {
    wakeLockEnabled = !wakeLockEnabled;
    GM_setValue(KEY_WAKE_LOCK, wakeLockEnabled);
    if (wakeLockEnabled && running) {
      acquireWakeLock();
    } else if (!wakeLockEnabled) {
      releaseWakeLock();
    }
    updateStatus(`Wake lock ${wakeLockEnabled ? "enabled" : "disabled"}`, "#4fc3f7");
  });

  GM_registerMenuCommand("[Settings] Reset Stats", () => {
    stats = { ...DEFAULT_STATS, session_start: new Date().toISOString() };
    GM_setValue(KEY_STATS, stats);
    _logTrail.length = 0;
    _renderLogTrail();
    updateStatus("Stats & log reset.", "#4fc3f7");
  });

  GM_registerMenuCommand("[Settings] Reset Delay (4.5s)", () => {
    setBaseDelay(DEFAULT_BASE_DELAY_MS);
    updateStatus(`Base delay reset to ${(DEFAULT_BASE_DELAY_MS / 1000).toFixed(1)}s`, "#4fc3f7");
  });

  // -- Boot -------------------------------------------------------
  log("INFO", `Script loaded: tab=${TAB_ID}, running=${running}, publicid=${getPublicId()}, urlToken=${getUrlRouteToken()}, owner=${GM_getValue(KEY_OWNER_TAB, null)}, bookDisc=${isBookDiscoveryActive()}, bookCap=${isBookCaptureActive()}`);
  // Pacing summary so users can quickly see what to expect from the
  // adaptive wait. Helps debug "why is it slow / fast" complaints
  // without diving into the constants block.
  (function _logPacingSummary() {
    const base = getBaseDelay();
    const lo = Math.max(1200, Math.round(base * (1 - JITTER_RATIO)));
    const hi = Math.round(base * (1 + JITTER_RATIO));
    const burstHi = hi + BURST_COOLDOWN_MAX_MS;
    const perMinLo = Math.round(60000 / hi);
    const perMinHi = Math.round(60000 / lo);
    log("INFO", `Pacing: base=${base}ms wait=${lo}-${hi}ms (burst peak ~${burstHi}ms every ${BURST_COOLDOWN_EVERY}); throughput ≈ ${perMinLo}-${perMinHi} puzzles/min (qday/general). Chapter mode uses ${CHAPTER_INTERVAL_MIN_MS}-${CHAPTER_INTERVAL_MAX_MS}ms target interval.`);
  })();
  setTimeout(autoStart, 500);
  startNavigationWatcher();

  // Re-acquire wake lock when tab becomes visible again (browser releases it on hide)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && running && isOwnerTab() && wakeLockEnabled && !wakeLockSentinel) {
      log("INFO", "Tab visible again, re-acquiring wake lock");
      acquireWakeLock();
    }
  });
  //#endregion 9. MENU COMMANDS
})();
