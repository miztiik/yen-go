// ==UserScript==
// @name         101weiqi Puzzle Capture for YenGo
// @namespace    https://github.com/yengo
// @version      4.5.5
// @description  Auto-captures puzzle data from 101weiqi.com and sends to local YenGo receiver. Start server, browse any puzzle page, it just works.
// @match        https://www.101weiqi.com/q/*
// @match        https://www.101weiqi.com/chessmanual/*
// @match        https://www.101weiqi.com/qday/*
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
  const ERROR_BACKOFF_MAX_MS = 90000;
  const HTTP_TIMEOUT_MS = 15000;
  const QQDATA_POLL_MS = 1000;
  const QQDATA_MAX_WAIT = 10000;
  const DAILY_MIN_NUM = 1;
  const DAILY_MAX_NUM = 8;

  // -- State ------------------------------------------------------
  const KEY_RUNNING = "yengo_running";
  const KEY_STATS = "yengo_stats";
  const KEY_QDAY_PLAN = "yengo_qday_plan";
  const KEY_BASE_DELAY = "yengo_base_delay";
  const KEY_WAKE_LOCK = "yengo_wake_lock";
  const KEY_OWNER_TAB = "yengo_owner_tab";
  const KEY_OWNER_HEARTBEAT = "yengo_owner_hb";

  const HEARTBEAT_INTERVAL_MS = 5000; // 10s
  const OWNER_STALE_MS = 30000; // 30s before declaring owner dead

  // Stable tab ID that survives same-tab navigations (location.href).
  // sessionStorage can be unreliable in Tampermonkey's sandbox across
  // navigations, so we also persist the ID in window.name (which is
  // guaranteed per-spec to survive same-tab navigations).
  const TAB_ID = (() => {
    // 1. Try sessionStorage first (fastest, usually works)
    let id = sessionStorage.getItem("yengo_tab_id");
    if (id) return id;
    // 2. Fallback: window.name persists across navigations per spec
    const m = (window.name || "").match(/yengo_tab=([a-z0-9]+)/);
    if (m) {
      id = m[1];
      sessionStorage.setItem("yengo_tab_id", id);
      return id;
    }
    // 3. New tab — generate fresh ID, store in both places
    id = Math.random().toString(36).slice(2, 8);
    sessionStorage.setItem("yengo_tab_id", id);
    window.name = ((window.name || "") + " yengo_tab=" + id).trim();
    return id;
  })();

  const DEFAULT_STATS = {
    ok: 0, skipped: 0, error: 0, captcha: 0, notfound: 0,
  };

  let running = GM_getValue(KEY_RUNNING, false);
  let qdayPlan = GM_getValue(KEY_QDAY_PLAN, null);
  let issueStreak = 0;
  let stats = { ...DEFAULT_STATS, ...GM_getValue(KEY_STATS, {}), session_start: new Date().toISOString() };
  let wakeLockEnabled = GM_getValue(KEY_WAKE_LOCK, false);
  let wakeLockSentinel = null;

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

  const _PHASE_ICONS = {
    WAIT: "\u23F3", LOAD: "\uD83D\uDD04", GRAB: "\uD83D\uDCE5",
    SEND: "\uD83D\uDCE4", DONE: "\u2705", NEXT: "\u23ED\uFE0F",
    SKIP: "\u23E9", WARN: "\u26A0\uFE0F", ERR: "\u274C",
    END: "\uD83C\uDFC1",
  };

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
  const ENCODED_FIELDS = [
    "content", "ok_answers", "change_answers",
    "fail_answers", "clone_pos", "clone_prepos",
  ];

  function decodeEncodedFields(obj) {
    const ru = obj.ru;
    if (ru !== 1 && ru !== 2) return;
    const key = deriveXorKey(ru);
    for (const field of ENCODED_FIELDS) {
      if (typeof obj[field] === "string" && obj[field].length > 10) {
        try {
          const decoded = JSON.parse(xorDecode(obj[field], key));
          obj[field] = decoded;
        } catch (_) {
          // leave as-is if decode fails
        }
      }
    }
  }

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
      const mode = isQdaySweepActive() ? "QDAY" : "QUEUE";
      _barStatsEl.textContent =
        `OK:${stats.ok} Skip:${stats.skipped} Err:${stats.error} ` +
        `CAPTCHA:${stats.captcha||0} 404:${stats.notfound||0} Total:${t}` +
        ` | ${running ? `RUNNING:${mode}` : "IDLE"}`;
    }
  }

  // -- HTTP helpers -----------------------------------------------
  function http(method, path, body) {
    return new Promise((resolve, reject) => {
      const opts = {
        method,
        url: RECEIVER + path,
        timeout: HTTP_TIMEOUT_MS,
        onload: (r) => {
          try { resolve(JSON.parse(r.responseText)); }
          catch { reject(new Error("Bad response: " + path)); }
        },
        onerror: () => reject(new Error("Server unreachable")),
        ontimeout: () => reject(new Error("Server timeout: " + path)),
      };
      if (body) {
        opts.headers = { "Content-Type": "application/json" };
        opts.data = JSON.stringify(body);
      }
      GM_xmlhttpRequest(opts);
    });
  }

  function getPuzzleId() {
    // /q/12345/ or /chessmanual/12345/
    const m = location.pathname.match(/\/(?:q|chessmanual)\/(\d+)/);
    if (m) return parseInt(m[1], 10);
    // Alpine store (most reliable during SPA navigation)
    try {
      const qipan = unsafeWindow.Alpine && unsafeWindow.Alpine.store("qipan");
      if (qipan && qipan.qqdata && qipan.qqdata.publicid) {
        return parseInt(qipan.qqdata.publicid, 10);
      }
    } catch (_) {}
    // /qday/ pages: ID comes from qqdata, not URL
    if (typeof unsafeWindow.qqdata !== "undefined" && unsafeWindow.qqdata.publicid) {
      return parseInt(unsafeWindow.qqdata.publicid, 10);
    }
    return null;
  }

  function randomBetween(min, max) {
    return min + Math.random() * (max - min);
  }

  function waitMs(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
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

  // -- Wake Lock (sleep prevention) --------------------------------
  async function acquireWakeLock() {
    if (!wakeLockEnabled) return;
    if (!("wakeLock" in navigator)) {
      log("WARN", "Wake Lock API not available in this browser");
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

  // -- Centralized state transitions (with tab ownership) ----------
  function startRunning() {
    const currentOwner = GM_getValue(KEY_OWNER_TAB, null);
    if (currentOwner && currentOwner !== TAB_ID && !isOwnerStale()) {
      log("WARN", `Another tab (${currentOwner}) is already running`);
      updateStatus(`Observing \u2014 another tab is running the sweep`, "#888");
      return false;
    }
    running = true;
    GM_setValue(KEY_RUNNING, true);
    claimOwnership();
    if (wakeLockEnabled) acquireWakeLock();
    return true;
  }

  function stopRunning(reason) {
    running = false;
    GM_setValue(KEY_RUNNING, false);
    releaseOwnership();
    releaseWakeLock();
    if (reason) log("INFO", `Stopped: ${reason}`);
  }

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

  // -- qqdata readiness check --------------------------------------
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

  // -- Navigate to next (always asks server) ----------------------
  async function goNext() {
    if (!isOwnerTab()) return;
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
      plog("NEXT", `-> ${nextPlan.currentDate} #${nextPlan.currentNum}`);
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

  // -- Wait for qqdata (may load async) ---------------------------
  function waitForQqdata() {
    return new Promise((resolve) => {
      if (isQqdataReady()) return resolve(true);
      let elapsed = 0;
      const iv = setInterval(() => {
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
      const check = () => {
        const text = document.body.textContent;
        return text.includes("Included in") || text.includes("\u6536\u5F55\u4E8E");
      };
      if (check()) return resolve(true);
      let elapsed = 0;
      const interval = 500;
      const iv = setInterval(() => {
        elapsed += interval;
        if (check()) { clearInterval(iv); resolve(true); }
        else if (elapsed >= timeoutMs) { clearInterval(iv); resolve(false); }
      }, interval);
    });
  }

  // -- Main capture logic -----------------------------------------
  async function capture() {
    const pageId = getPuzzleId();
    const qday = isQdaySweepActive();
    const label = qday
      ? `qday ${qdayPlan.currentDate} #${qdayPlan.currentNum}`
      : (pageId ? `puzzle ${pageId}` : location.pathname);
    plog("LOAD", `${label} — waiting for data`);

    // CAPTCHA
    if (isCaptcha()) {
      issueStreak += 1;
      stats.captcha = (stats.captcha || 0) + 1;
      GM_setValue(KEY_STATS, stats);
      plog("WARN", `${label} — CAPTCHA detected, pausing until solved`);
      updateStatus("CAPTCHA! Solve it manually -- will auto-resume.", "#f44336");
      GM_notification({ text: "CAPTCHA -- solve to continue", title: "YenGo", timeout: 10000 });
      const poll = setInterval(() => {
        if (getQqdata()) { clearInterval(poll); capture(); }
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
        issueStreak += 1;
        stats.notfound = (stats.notfound || 0) + 1;
        stats.error++;
        GM_setValue(KEY_STATS, stats);
        plog("WARN", `${label} — no qqdata after ${QQDATA_MAX_WAIT / 1000}s, skipping`);
        updateStatus("No puzzle data found. Skipping.", "#ff9800");
        if (running) goNext();
        return;
      }
    }

    // Decode content field in JS (same algorithm as the site's own JS)
    // Clone qqdata to avoid mutating the page's runtime object
    const qq = getQqdata();
    if (!qq) {
      issueStreak += 1;
      log("ERROR", "No qqdata available after readiness check");
      if (running) goNext();
      return;
    }
    // Clone qqdata safely -- Alpine proxies may not be structuredClone-able
    let payload;
    try {
      payload = structuredClone(qq);
    } catch (_) {
      try {
        payload = JSON.parse(JSON.stringify(qq));
      } catch (e) {
        issueStreak += 1;
        stats.error++;
        plog("ERR", `${label} — cannot clone qqdata: ${e.message}`);
        updateStatus("Cannot read puzzle data. Skipping.", "#f44336");
        GM_setValue(KEY_STATS, stats);
        if (running) goNext();
        return;
      }
    }

    const pid = getPuzzleId();
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

      plog("SEND", `${label} — posting to backend`);
      const capturePayload = {
        qqdata: payload,
        url: location.href,
        captured_at: new Date().toISOString(),
      };
      if (pageBooks.length > 0) {
        capturePayload._page_books = pageBooks;
      }
      const result = await http("POST", "/capture", capturePayload);
      if (result.status === "ok") {
        issueStreak = 0;
        stats.ok++;
        plog("DONE", `${label} — saved as ${result.puzzle_id} (ok:${stats.ok} skip:${stats.skipped} err:${stats.error})`);
        updateStatus(`Saved ${result.puzzle_id}`, "#81c784");
      } else if (result.status === "skipped") {
        issueStreak = 0;
        stats.skipped++;
        plog("SKIP", `${label} — duplicate ${result.puzzle_id} (ok:${stats.ok} skip:${stats.skipped} err:${stats.error})`);
        updateStatus(`Skipped ${result.puzzle_id} (duplicate)`, "#ffb74d");
      } else {
        issueStreak += 1;
        stats.error++;
        plog("ERR", `${label} — server error: ${result.message}`);
        updateStatus(`Error: ${result.message}`, "#f44336");
      }
    } catch (err) {
      issueStreak += 1;
      stats.error++;
      plog("ERR", `${label} — capture failed: ${err.message}, stopping`);
      stopRunning("server unreachable");
      updateStatus("Server unreachable! Start: python -m tools.weiqi101 receive", "#f44336");
      GM_setValue(KEY_STATS, stats);
      return;
    }

    GM_setValue(KEY_STATS, stats);
    // Track last captured page for navigation detection
    lastCapturedUrl = location.href;
    lastCapturedId = getPuzzleId();
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

  async function autoStart() {
    // Tab ownership check: only the owner tab drives sweep/queue.
    // Non-owner tabs just capture the current page passively.
    const currentOwner = GM_getValue(KEY_OWNER_TAB, null);
    const ownerIsOther = currentOwner && currentOwner !== TAB_ID && !isOwnerStale();

    if (isQdaySweepActive()) {
      if (ownerIsOther) {
        updateStatus(`Observing \u2014 sweep running in another tab`, "#888");
        return;
      }
      if (!startRunning()) return;
      const planUrl = buildQdayUrl(qdayPlan.currentDate, qdayPlan.currentNum);
      if (location.href !== planUrl) {
        updateStatus(`Resuming qday sweep at ${qdayPlan.currentDate} #${qdayPlan.currentNum}`, "#4fc3f7");
        location.href = planUrl;
        return;
      }
    }

    if (!running) {
      if (ownerIsOther) {
        // Another tab owns the queue — just capture this page passively
        capture();
        return;
      }
      // Check if server has an active queue (e.g. started with --book-id)
      try {
        const q = await http("GET", "/queue/status");
        if (q.active && q.pending > 0) {
          log("INFO", `Server has active queue: ${q.pending} pending, auto-starting`);
          if (!startRunning()) return;
          updateStatus(
            `Auto-detected queue: ${q.book_name || q.source || "custom"} -- ${q.pending} pending`,
            "#4fc3f7"
          );
        }
      } catch {
        // Server not running -- that's fine, just capture this page only
      }
    }
    // Always capture the current page
    capture();
  }

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

      // Debounce: wait for the page to settle before capturing
      if (navDebounce) clearTimeout(navDebounce);
      navDebounce = setTimeout(async () => {
        navDebounce = null;
        lastTitle = document.title;
        await waitForQqdata();
        capture();
      }, 1500);
    }, 1000);
  }

  // -- Menu commands (simple) -------------------------------------

  GM_registerMenuCommand("Pick a Book", showBookPicker);
  GM_registerMenuCommand("Start Daily Sweep to Today (1->8)", () => startQdaySweep("asc"));
  GM_registerMenuCommand("Start Daily Sweep to Today (8->1)", () => startQdaySweep("desc"));
  GM_registerMenuCommand("Show Daily Sweep State", () => {
    if (!isQdaySweepActive()) {
      alert("Daily sweep is not active.");
      return;
    }
    alert(
      `Daily sweep active\n` +
      `Date: ${qdayPlan.currentDate}\n` +
      `Puzzle: ${qdayPlan.currentNum}\n` +
      `Target: ${qdayPlan.targetDate}\n` +
      `Order: ${qdayPlan.order === "desc" ? "8->1" : "1->8"}\n` +
      `Direction: ${qdayPlan.dateDirection}`
    );
  });

  GM_registerMenuCommand("Stop", () => {
    clearQdayPlan();
    stopRunning("user stopped");
    http("GET", "/queue/stop").catch(() => {});
    updateStatus("Stopped.", "#ff9800");
  });

  GM_registerMenuCommand("Take Control in This Tab", () => {
    claimOwnership();
    if (GM_getValue(KEY_RUNNING, false)) {
      running = true;
      if (wakeLockEnabled) acquireWakeLock();
      updateStatus(`This tab (${TAB_ID}) is now the active runner — resuming...`, "#4fc3f7");
      // Actually resume the sweep loop
      capture();
    } else {
      updateStatus(`This tab (${TAB_ID}) claimed ownership (idle).`, "#4fc3f7");
    }
  });

  GM_registerMenuCommand("Show Telemetry", async () => {
    try {
      const t = await http("GET", "/telemetry");
      alert(
        `Session: ${t.started_at}\n` +
        `Book: ${t.book_name || "(none)"}\n` +
        `OK: ${t.counts.ok}  Skip: ${t.counts.skipped}  Err: ${t.counts.error}\n` +
        `Total: ${t.total_processed}  Avg: ${t.avg_duration_ms}ms\n` +
        `Errors: ${t.recent_errors.length}`
      );
    } catch (err) {
      alert("Server unreachable: " + err.message);
    }
  });

  GM_registerMenuCommand("Reset Stats & Log", () => {
    stats = { ...DEFAULT_STATS, session_start: new Date().toISOString() };
    GM_setValue(KEY_STATS, stats);
    _logTrail.length = 0;
    _renderLogTrail();
    updateStatus("Stats & log reset.", "#4fc3f7");
  });

  GM_registerMenuCommand("Toggle Wake Lock", () => {
    wakeLockEnabled = !wakeLockEnabled;
    GM_setValue(KEY_WAKE_LOCK, wakeLockEnabled);
    if (wakeLockEnabled && running) {
      acquireWakeLock();
    } else if (!wakeLockEnabled) {
      releaseWakeLock();
    }
    updateStatus(`Wake lock ${wakeLockEnabled ? "enabled" : "disabled"}`, "#4fc3f7");
  });

  GM_registerMenuCommand("Reset Delay to Default (4.5s)", () => {
    setBaseDelay(DEFAULT_BASE_DELAY_MS);
    updateStatus(`Base delay reset to ${(DEFAULT_BASE_DELAY_MS / 1000).toFixed(1)}s`, "#4fc3f7");
  });

  // -- Boot -------------------------------------------------------
  log("INFO", `Script loaded: tab=${TAB_ID}, running=${running}, puzzle=${getPuzzleId()}, owner=${GM_getValue(KEY_OWNER_TAB, null)}`);
  setTimeout(autoStart, 500);
  startNavigationWatcher();

  // Re-acquire wake lock when tab becomes visible again (browser releases it on hide)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && running && isOwnerTab() && wakeLockEnabled && !wakeLockSentinel) {
      log("INFO", "Tab visible again, re-acquiring wake lock");
      acquireWakeLock();
    }
  });
})();
