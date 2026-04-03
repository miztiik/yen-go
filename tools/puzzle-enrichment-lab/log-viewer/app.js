(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════════════
  // Inline sample data (file:// protocol does not support fetch)
  // ═══════════════════════════════════════════════════════════════
  var SAMPLE_JSONL = [
    '{"msg":"session_start","trace_id":"a1b2c3d4e5f60001","source_file":"cho_elem_001.sgf","run_id":"20260321-121346-6340cae7","config_hash":"a3f8c2e1","timestamp":"2026-03-21T12:13:46.123Z"}',
    '{"msg":"enrichment_begin","puzzle_id":"cho_elem_001","trace_id":"a1b2c3d4e5f60001","source_file":"cho_elem_001.sgf","timestamp":"2026-03-21T12:13:46.130Z"}',
    '{"msg":"parse_sgf","trace_id":"a1b2c3d4e5f60001","stage":"parse_sgf","board_size":19,"tags":["life-and-death"],"corner":"TR","ko":"none","sgf_length":342,"timestamp":"2026-03-21T12:13:46.145Z"}',
    '{"msg":"katago_analysis","trace_id":"a1b2c3d4e5f60001","stage":"analyze","correct_move":"S14","winrate":0.892,"policy":0.4312,"visits":2000,"top_move":"S14","model":"b18c384","timestamp":"2026-03-21T12:13:46.260Z"}',
    '{"msg":"original_sgf: (;FF[4]GM[1]SZ[19]AB[qd][qe][re]AW[pd][pe][qf];B[rf];W[rd])","trace_id":"a1b2c3d4e5f60001","timestamp":"2026-03-21T12:13:46.146Z"}',
    '{"msg":"extract_solution","trace_id":"a1b2c3d4e5f60001","stage":"parse_sgf","correct_move_sgf":"rf","has_solution":true,"timestamp":"2026-03-21T12:13:46.150Z"}',
    '{"msg":"validate_move","trace_id":"a1b2c3d4e5f60001","stage":"validate_move","katago_agrees":true,"status":"valid","tree_validation":"pass","curated_wrongs":0,"curated_corrects":1,"flags":[],"timestamp":"2026-03-21T12:13:46.268Z"}',
    '{"msg":"framed_sgf: (;FF[4]GM[1]SZ[9]AB[gd][ge][he]AW[fd][fe][gf];B[hf];W[hd])","trace_id":"a1b2c3d4e5f60001","timestamp":"2026-03-21T12:13:46.270Z"}',
    '{"msg":"generate_refutations","trace_id":"a1b2c3d4e5f60001","stage":"generate_refutations","refutation_count":3,"pv_mode":"standard","escalation_used":false,"timestamp":"2026-03-21T12:13:46.313Z"}',
    '{"msg":"estimate_difficulty","trace_id":"a1b2c3d4e5f60001","stage":"estimate_difficulty","estimated_level":"intermediate","raw_score":0.62,"confidence":"high","policy_entropy":2.14,"correct_move_rank":1,"timestamp":"2026-03-21T12:13:46.325Z"}',
    '{"msg":"technique_classification","trace_id":"a1b2c3d4e5f60001","stage":"technique_classification","technique_tags":["life-and-death","ladder"],"detector_count":28,"positive_count":2,"timestamp":"2026-03-21T12:13:46.359Z"}',
    '{"msg":"instinct_classification","trace_id":"a1b2c3d4e5f60001","stage":"instinct_classification","instinct_count":2,"instincts":["attack","surround"],"timestamp":"2026-03-21T12:13:46.367Z"}',
    '{"msg":"teaching_enrichment","trace_id":"a1b2c3d4e5f60001","stage":"teaching_enrichment","technique_tags":["life-and-death","ladder"],"hints_count":3,"hints_text":["Focus on the corner stones","The ladder works here","First move at the vital point"],"teaching_comments":2,"timestamp":"2026-03-21T12:13:46.434Z"}',
    '{"msg":"enriched_sgf","trace_id":"a1b2c3d4e5f60001","stage":"sgf_writeback","sgf_length":587,"timestamp":"2026-03-21T12:13:46.450Z"}',
    '{"msg":"enriched_sgf_content: (;FF[4]GM[1]SZ[19]YV[15]YG[intermediate]YT[ladder,life-and-death]YH[Focus on the corner stones|The ladder works here|First move at the vital point]AB[qd][qe][re]AW[pd][pe][qf];B[rf];W[rd])","trace_id":"a1b2c3d4e5f60001","timestamp":"2026-03-21T12:13:46.451Z"}',
    '{"msg":"enrichment_complete","puzzle_id":"cho_elem_001","trace_id":"a1b2c3d4e5f60001","status":"accepted","refutations":3,"level":"intermediate","technique_tags":["life-and-death","ladder"],"hints_count":3,"hints_text":["Focus on the corner stones","The ladder works here","First move at the vital point"],"phase_timings":{"parse_sgf":0.015,"solve_paths":0.008,"analyze":2.345,"validate_move":0.123,"generate_refutations":0.045,"estimate_difficulty":0.012,"assemble_result":0.005,"technique_classification":0.034,"instinct_classification":0.008,"teaching_enrichment":0.067,"sgf_writeback":0.015},"queries_used":4,"queries_by_stage":{"solve_paths":2,"analyze":1,"refutations":1},"total_visits":2028,"enrichment_tier":3,"correct_move_sgf":"rf","correct_move_gtp":"S14","goal":"kill","goal_confidence":"high","ac_level":2,"timestamp":"2026-03-21T12:13:48.807Z"}',
    '{"msg":"enrichment_end","trace_id":"a1b2c3d4e5f60001","puzzle_id":"cho_elem_001","source_file":"cho_elem_001.sgf","status":"accepted","elapsed_s":"2.677","timestamp":"2026-03-21T12:13:48.810Z"}',
    '{"msg":"session_start","trace_id":"a1b2c3d4e5f60002","source_file":"collection/goproblems/flag_test_002.sgf","run_id":"20260321-121346-6340cae7","config_hash":"a3f8c2e1","timestamp":"2026-03-21T12:13:49.001Z"}',
    '{"msg":"enrichment_begin","puzzle_id":"flag_test_002","trace_id":"a1b2c3d4e5f60002","source_file":"collection/goproblems/flag_test_002.sgf","timestamp":"2026-03-21T12:13:49.010Z"}',
    '{"msg":"parse_sgf","trace_id":"a1b2c3d4e5f60002","stage":"parse_sgf","board_size":19,"tags":["ko"],"corner":"BL","ko":"direct","sgf_length":289,"timestamp":"2026-03-21T12:13:49.025Z"}',
    '{"msg":"original_sgf: (;FF[4]GM[1]SZ[19]AB[cp][dp][ep]AW[co][do][eo];B[cn];W[dn])","trace_id":"a1b2c3d4e5f60002","timestamp":"2026-03-21T12:13:49.026Z"}',
    '{"msg":"extract_solution","trace_id":"a1b2c3d4e5f60002","stage":"parse_sgf","correct_move_sgf":"cn","has_solution":true,"timestamp":"2026-03-21T12:13:49.030Z"}',
    '{"msg":"katago_analysis","trace_id":"a1b2c3d4e5f60002","stage":"analyze","correct_move":"C6","winrate":0.341,"policy":0.1823,"visits":2000,"top_move":"D6","model":"b18c384","timestamp":"2026-03-21T12:13:49.100Z"}',
    '{"msg":"validate_move","trace_id":"a1b2c3d4e5f60002","stage":"validate_move","katago_agrees":false,"status":"disagreement","tree_validation":"pass","curated_wrongs":1,"curated_corrects":1,"flags":["katago_disagrees"],"timestamp":"2026-03-21T12:13:49.108Z"}',
    '{"msg":"estimate_difficulty","trace_id":"a1b2c3d4e5f60002","stage":"estimate_difficulty","estimated_level":"elementary","raw_score":0.35,"confidence":"medium","policy_entropy":1.82,"correct_move_rank":2,"timestamp":"2026-03-21T12:13:49.117Z"}',
    '{"msg":"technique_classification","trace_id":"a1b2c3d4e5f60002","stage":"technique_classification","technique_tags":["ko","snapback"],"detector_count":28,"positive_count":2,"timestamp":"2026-03-21T12:13:49.145Z"}',
    '{"msg":"instinct_classification","trace_id":"a1b2c3d4e5f60002","stage":"instinct_classification","instinct_count":1,"instincts":["capture"],"timestamp":"2026-03-21T12:13:49.151Z"}',
    '{"msg":"teaching_enrichment","trace_id":"a1b2c3d4e5f60002","stage":"teaching_enrichment","technique_tags":["ko","snapback"],"hints_count":2,"hints_text":["Watch for the ko threat","Snapback is the key"],"teaching_comments":1,"timestamp":"2026-03-21T12:13:49.170Z"}',
    '{"msg":"enrichment_complete","puzzle_id":"flag_test_002","trace_id":"a1b2c3d4e5f60002","status":"flagged","refutations":1,"level":"elementary","technique_tags":["ko","snapback"],"hints_count":2,"hints_text":["Watch for the ko threat","Snapback is the key"],"phase_timings":{"parse_sgf":0.012,"solve_paths":0.007,"analyze":1.890,"validate_move":0.098,"generate_refutations":0.031,"estimate_difficulty":0.009,"assemble_result":0.004,"technique_classification":0.028,"instinct_classification":0.006,"teaching_enrichment":0.041,"sgf_writeback":0.012},"queries_used":3,"queries_by_stage":{"solve_paths":1,"analyze":1,"refutations":1},"enrichment_tier":2,"correct_move_sgf":"cn","correct_move_gtp":"C6","goal":"live","goal_confidence":"medium","ac_level":1,"timestamp":"2026-03-21T12:13:51.148Z"}',
    '{"msg":"enrichment_end","trace_id":"a1b2c3d4e5f60002","puzzle_id":"flag_test_002","source_file":"collection/goproblems/flag_test_002.sgf","status":"flagged","elapsed_s":"2.138","timestamp":"2026-03-21T12:13:51.150Z"}',
    '{"msg":"session_start","trace_id":"a1b2c3d4e5f60003","source_file":"reject_003.sgf","run_id":"20260321-121346-6340cae7","config_hash":"a3f8c2e1","timestamp":"2026-03-21T12:13:52.001Z"}',
    '{"msg":"enrichment_begin","puzzle_id":"reject_003","trace_id":"a1b2c3d4e5f60003","source_file":"reject_003.sgf","timestamp":"2026-03-21T12:13:52.010Z"}',
    '{"msg":"validate_move","trace_id":"a1b2c3d4e5f60003","stage":"validate_move","katago_agrees":false,"status":"no_solution","tree_validation":"fail","curated_wrongs":0,"curated_corrects":0,"flags":["no_solution_tree","ambiguous"],"timestamp":"2026-03-21T12:13:52.155Z"}',
    '{"msg":"estimate_difficulty","trace_id":"a1b2c3d4e5f60003","stage":"estimate_difficulty","estimated_level":"beginner","raw_score":0.18,"confidence":"low","policy_entropy":0.92,"correct_move_rank":3,"timestamp":"2026-03-21T12:13:52.167Z"}',
    '{"msg":"enrichment_complete","puzzle_id":"reject_003","trace_id":"a1b2c3d4e5f60003","status":"rejected","refutations":0,"level":"beginner","technique_tags":["life-and-death"],"hints_count":1,"hints_text":["Look at the vital point"],"phase_timings":{"parse_sgf":0.014,"solve_paths":0.006,"analyze":3.412,"validate_move":0.145},"queries_used":5,"enrichment_tier":1,"correct_move_sgf":null,"correct_move_gtp":null,"goal":null,"goal_confidence":null,"ac_level":0,"timestamp":"2026-03-21T12:13:55.587Z"}',
    '{"msg":"enrichment_end","trace_id":"a1b2c3d4e5f60003","puzzle_id":"reject_003","source_file":"reject_003.sgf","status":"rejected","elapsed_s":"3.577","timestamp":"2026-03-21T12:13:55.590Z"}',
    '{"msg":"session_start","trace_id":"a1b2c3d4e5f60004","source_file":"error_004.sgf","run_id":"20260321-121346-6340cae7","config_hash":"a3f8c2e1","timestamp":"2026-03-21T12:13:56.001Z"}',
    '{"msg":"enrichment_begin","puzzle_id":"error_004","trace_id":"a1b2c3d4e5f60004","source_file":"error_004.sgf","timestamp":"2026-03-21T12:13:56.010Z"}',
    '{"msg":"enrichment_complete","puzzle_id":"error_004","trace_id":"a1b2c3d4e5f60004","status":"error","refutations":0,"level":null,"technique_tags":[],"hints_count":0,"hints_text":[],"phase_timings":{"parse_sgf":0.018},"queries_used":0,"enrichment_tier":0,"correct_move_sgf":null,"correct_move_gtp":null,"goal":null,"goal_confidence":null,"ac_level":null,"error_message":"SGF parse error: no solution tree found","timestamp":"2026-03-21T12:13:56.028Z"}',
    '{"msg":"enrichment_end","trace_id":"a1b2c3d4e5f60004","puzzle_id":"error_004","source_file":"error_004.sgf","status":"error","elapsed_s":"0.028","timestamp":"2026-03-21T12:13:56.030Z"}',
    '{"msg":"session_start","trace_id":"a1b2c3d4e5f60005","source_file":"minimal_005.sgf","run_id":"20260321-121346-6340cae7","config_hash":"a3f8c2e1","timestamp":"2026-03-21T12:13:57.001Z"}',
    '{"msg":"enrichment_begin","puzzle_id":"minimal_005","trace_id":"a1b2c3d4e5f60005","source_file":"minimal_005.sgf","timestamp":"2026-03-21T12:13:57.010Z"}',
    '{"msg":"enrichment_end","trace_id":"a1b2c3d4e5f60005","puzzle_id":"minimal_005","source_file":"minimal_005.sgf","status":"accepted","elapsed_s":"1.523","timestamp":"2026-03-21T12:13:58.533Z"}'
  ].join('\n');

  // ═══════════════════════════════════════════════════════════════
  // Constants
  // ═══════════════════════════════════════════════════════════════
  var PIPELINE_STAGES = [
    { key: 'parse_sgf', label: 'Parse' },
    { key: 'solve_paths', label: 'Solve-Path' },
    { key: 'analyze', label: 'Analyze' },
    { key: 'validate_move', label: 'Validate' },
    { key: 'generate_refutations', label: 'Refutation' },
    { key: 'estimate_difficulty', label: 'Difficulty' },
    { key: 'assemble_result', label: 'Assembly' },
    { key: 'technique_classification', label: 'Technique' },
    { key: 'instinct_classification', label: 'Instinct' },
    { key: 'teaching_enrichment', label: 'Teaching' },
    { key: 'sgf_writeback', label: 'SGF-Write' }
  ];

  var TIER_DESCRIPTIONS = {
    0: { badge: '\u2014', label: 'Unknown', description: 'No enrichment data available' },
    1: { badge: 'Bare', label: 'Tier 1 \u2014 Bare Minimum', description: 'Stones and basic structure only' },
    2: { badge: 'Structural', label: 'Tier 2 \u2014 Structural', description: 'Partial KataGo analysis (position + validation)' },
    3: { badge: 'Full', label: 'Tier 3 \u2014 Full Analysis', description: 'Refutations + difficulty + teaching comments' }
  };

  // Semantic colors for enrichment tiers (0=unknown/gray, 1=bare/red, 2=structural/amber, 3=full/green)
  var TIER_COLORS = {
    0: { bg: 'var(--chart-error)', label: 'var(--accent-gray)' },
    1: { bg: 'var(--chart-rejected)', label: 'var(--accent-red)' },
    2: { bg: 'var(--chart-flagged)', label: 'var(--accent-amber)' },
    3: { bg: 'var(--chart-accepted)', label: 'var(--accent-green)' }
  };

  var TIER_BADGE_CLASSES = {
    0: 'badge badge-tier-0',
    1: 'badge badge-tier-1',
    2: 'badge badge-tier-2',
    3: 'badge badge-tier-3'
  };

  var PHASE_COLORS = [
    '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
    '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac', '#86bcb6'
  ];

  var MAX_SEARCH_RESULTS = 200;
  var SEARCH_DEBOUNCE_MS = 300;
  var HISTORY_KEY = 'enrichment-log-viewer-history';
  var MAX_HISTORY_ITEMS = 10;

  // Track chart instances for cleanup
  var chartInstances = [];

  // Active search trigger (set by renderSearch, used by pipeline click)
  var triggerSearch = null;

  // ═══════════════════════════════════════════════════════════════
  // File History (localStorage)
  // ═══════════════════════════════════════════════════════════════

  function loadHistory() {
    try {
      var data = localStorage.getItem(HISTORY_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) { return []; }
  }

  function saveHistory(history) {
    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history)); } catch (e) { /* quota */ }
  }

  function addToHistory(fileName, content, stats) {
    var history = loadHistory();
    // Remove existing entry for same filename
    history = history.filter(function (h) { return h.name !== fileName; });
    history.unshift({
      name: fileName,
      content: content,
      loadedAt: new Date().toISOString(),
      puzzleCount: stats.totalPuzzles,
      accepted: stats.accepted,
      flagged: stats.flagged,
      rejected: stats.rejected,
      errors: stats.errors
    });
    // Cap to MAX_HISTORY_ITEMS
    if (history.length > MAX_HISTORY_ITEMS) history = history.slice(0, MAX_HISTORY_ITEMS);
    saveHistory(history);
  }

  function clearHistory() {
    try { localStorage.removeItem(HISTORY_KEY); } catch (e) { /* ignore */ }
  }

  function renderSidebar(activeFileName) {
    var listEl = document.getElementById('sidebar-list');
    if (!listEl) return;
    listEl.textContent = '';

    var history = loadHistory();
    if (history.length === 0) {
      var empty = el('p', { className: 'sidebar-empty' }, 'No logs loaded yet');
      listEl.appendChild(empty);
      return;
    }

    history.forEach(function (entry) {
      var btn = el('button', { className: 'sidebar-item' + (entry.name === activeFileName ? ' active' : '') });
      var nameSpan = el('span', { className: 'sidebar-item-name' });
      nameSpan.textContent = formatSidebarName(entry.name);
      nameSpan.title = entry.name;
      btn.appendChild(nameSpan);

      var meta = el('span', { className: 'sidebar-item-meta' });
      var parts = [entry.puzzleCount + ' puzzles'];
      if (entry.flagged > 0) parts.push(entry.flagged + ' flagged');
      if (entry.rejected > 0) parts.push(entry.rejected + ' rejected');
      meta.textContent = parts.join(' \u00b7 ');
      btn.appendChild(meta);

      btn.addEventListener('click', function () {
        if (entry.content) {
          handleFileContent(entry.content, entry.name);
        }
      });

      listEl.appendChild(btn);
    });
  }

  function formatSidebarName(name) {
    // Strip common prefixes/extensions for concise display
    return name.replace(/\.jsonl$/i, '').replace(/\.log$/i, '');
  }

  // ═══════════════════════════════════════════════════════════════
  // Utility Functions
  // ═══════════════════════════════════════════════════════════════

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDuration(seconds) {
    if (seconds == null || isNaN(seconds)) return '\u2014';
    if (seconds < 0.001) return '<1ms';
    if (seconds < 1) return (seconds * 1000).toFixed(0) + 'ms';
    if (seconds < 60) return seconds.toFixed(2) + 's';
    var m = Math.floor(seconds / 60);
    var s = (seconds % 60).toFixed(1);
    return m + 'm ' + s + 's';
  }

  function formatTimestamp(ts) {
    if (!ts) return '\u2014';
    try {
      var d = new Date(ts);
      return d.toLocaleString();
    } catch (e) {
      return String(ts);
    }
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === 'className') node.className = attrs[k];
        else if (k === 'textContent') node.textContent = attrs[k];
        else if (k === 'innerHTML') node.innerHTML = attrs[k]; // Only for trusted static content
        else node.setAttribute(k, attrs[k]);
      });
    }
    if (children) {
      (Array.isArray(children) ? children : [children]).forEach(function (c) {
        if (typeof c === 'string') node.appendChild(document.createTextNode(c));
        else if (c) node.appendChild(c);
      });
    }
    return node;
  }

  var STATUS_TOOLTIPS = {
    accepted: 'Passed all quality gates. Ready for publication.',
    flagged: 'KataGo disagrees with expected answer or quality is borderline. Needs review.',
    rejected: 'Failed validation (high delta_wr, no solution tree, ambiguous answer).',
    error: 'Pipeline error prevented analysis (parse failure, engine timeout).'
  };

  function statusBadgeClass(status) {
    var map = { accepted: 'badge-accepted', flagged: 'badge-flagged', rejected: 'badge-rejected', error: 'badge-error' };
    return 'badge ' + (map[status] || 'badge-error');
  }

  function getCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function destroyCharts() {
    chartInstances.forEach(function (c) { try { c.destroy(); } catch (e) { /* ignore */ } });
    chartInstances = [];
  }

  // ═══════════════════════════════════════════════════════════════
  // JSONL Parser (T2)
  // ═══════════════════════════════════════════════════════════════

  function parseJSONL(text) {
    var events = [];
    var lines = text.split('\n');
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (!line) continue;
      try {
        var ev = JSON.parse(line);
        // Normalize: production logs use "ts", demo data uses "timestamp"
        if (ev.ts && !ev.timestamp) ev.timestamp = ev.ts;
        events.push(ev);
      } catch (e) {
        // Skip invalid JSON lines
      }
    }
    return events;
  }

  var STAGE_EVENT_MSGS = {
    'parse_sgf': true, 'extract_solution': true, 'validate_move': true,
    'generate_refutations': true, 'estimate_difficulty': true, 'assemble_result': true,
    'technique_classification': true, 'instinct_classification': true,
    'teaching_enrichment': true, 'enriched_sgf': true
  };

  // SGF content is logged as msg text (e.g. "original_sgf: (;FF[4]...)")
  // We capture these separately by prefix matching
  var SGF_MSG_PREFIXES = {
    'original_sgf: ': 'original',
    'framed_sgf: ': 'framed',
    'enriched_sgf_content: ': 'enriched'
  };

  function buildEventStore(events, fileName) {
    var puzzles = new Map();
    var runId = null;
    var sessionStart = null;
    var sessionEnd = null;
    var configHash = null;
    var configDump = null;
    var modelsUsed = {};      // model arch -> count
    var visitsUsed = {};      // visits value -> count
    var escalationCount = 0;

    // Index events by trace_id
    events.forEach(function (ev) {
      var tid = ev.trace_id;
      if (!tid) return;

      if (!runId && ev.run_id) runId = ev.run_id;
      if (!configHash && ev.config_hash) configHash = ev.config_hash;

      // Capture full config dump (emitted once per puzzle, keep first)
      if (ev.msg === 'config_dump' && ev.config && !configDump) {
        configDump = ev.config;
      }

      // Extract model info from katago_analysis events
      if (ev.msg === 'katago_analysis' && ev.model) {
        modelsUsed[ev.model] = (modelsUsed[ev.model] || 0) + 1;
        if (ev.visits) visitsUsed[ev.visits] = (visitsUsed[ev.visits] || 0) + 1;
      }

      // Track escalations
      if (ev.msg === 'generate_refutations' && ev.escalation_used) {
        escalationCount++;
      }

      // Ensure puzzle entry exists
      if (!puzzles.has(tid)) {
        puzzles.set(tid, {
          traceId: tid, puzzleId: null, sourceFile: null,
          status: null, level: null, tags: [], hintsCount: 0, hintsText: [],
          refutations: 0, correctMoveSgf: null, correctMoveGtp: null,
          goal: null, goalConfidence: null, acLevel: null,
          phaseTimings: null, queriesUsed: 0, enrichmentTier: null,
          startEvent: null, completeEvent: null, endEvent: null, errorMessage: null,
          stageDetails: {},
          sgfContent: { original: null, framed: null, enriched: null }
        });
      }
      var p = puzzles.get(tid);

      if (ev.msg === 'session_start') {
        var evTs = ev.timestamp || ev.ts;
        if (evTs && (!sessionStart || evTs < sessionStart)) sessionStart = evTs;
        p.startEvent = ev;
        if (ev.source_file) p.sourceFile = ev.source_file;
      }

      if (ev.msg === 'enrichment_begin') {
        if (ev.puzzle_id) p.puzzleId = ev.puzzle_id;
        if (ev.source_file) p.sourceFile = ev.source_file;
      }

      // Capture stage-specific events
      if (STAGE_EVENT_MSGS[ev.msg]) {
        p.stageDetails[ev.msg] = ev;
      }

      // Capture SGF content from msg text (e.g. "original_sgf: (;FF[4]...)")
      if (ev.msg) {
        var prefixKeys = Object.keys(SGF_MSG_PREFIXES);
        for (var pi = 0; pi < prefixKeys.length; pi++) {
          if (ev.msg.indexOf(prefixKeys[pi]) === 0) {
            var sgfType = SGF_MSG_PREFIXES[prefixKeys[pi]];
            p.sgfContent[sgfType] = ev.msg.substring(prefixKeys[pi].length);
            break;
          }
        }
      }

      if (ev.msg === 'enrichment_complete') {
        p.completeEvent = ev;
        if (ev.puzzle_id) p.puzzleId = ev.puzzle_id;
        p.status = ev.status || null;
        p.level = ev.level || null;
        p.tags = ev.technique_tags || [];
        p.hintsCount = ev.hints_count || 0;
        p.hintsText = ev.hints_text || [];
        p.refutations = ev.refutations || 0;
        p.phaseTimings = ev.phase_timings || null;
        p.queriesUsed = ev.queries_used || 0;
        p.queriesByStage = ev.queries_by_stage || null;
        p.totalVisits = ev.total_visits != null ? ev.total_visits : null;
        p.enrichmentTier = ev.enrichment_tier != null ? ev.enrichment_tier : null;
        p.errorMessage = ev.error_message || null;
        p.correctMoveSgf = ev.correct_move_sgf || null;
        p.correctMoveGtp = ev.correct_move_gtp || null;
        p.goal = ev.goal || null;
        p.goalConfidence = ev.goal_confidence != null ? ev.goal_confidence : null;
        p.acLevel = ev.ac_level != null ? ev.ac_level : null;
      }

      if (ev.msg === 'enrichment_end') {
        var endTs = ev.timestamp || ev.ts;
        if (endTs && (!sessionEnd || endTs > sessionEnd)) sessionEnd = endTs;
        p.endEvent = ev;
        if (ev.puzzle_id && !p.puzzleId) p.puzzleId = ev.puzzle_id;
        if (ev.status && !p.status) p.status = ev.status;
        if (ev.source_file && !p.sourceFile) p.sourceFile = ev.source_file;
      }
    });

    // Compute aggregate statistics
    var stats = {
      totalPuzzles: puzzles.size,
      accepted: 0, flagged: 0, rejected: 0, errors: 0,
      totalDuration: 0, avgDuration: 0,
      totalQueries: 0, avgQueries: 0,
      levelDistribution: {},
      tagDistribution: {},
      tierDistribution: {},
      stageTimingAggregates: {}
    };

    var durationCount = 0;

    puzzles.forEach(function (p) {
      if (p.status === 'accepted') stats.accepted++;
      else if (p.status === 'flagged') stats.flagged++;
      else if (p.status === 'rejected') stats.rejected++;
      else stats.errors++;

      // Duration from endEvent elapsed_s or phaseTimings.total
      var dur = 0;
      if (p.endEvent && p.endEvent.elapsed_s) dur = parseFloat(p.endEvent.elapsed_s);
      else if (p.phaseTimings && p.phaseTimings.total) dur = p.phaseTimings.total;
      if (dur > 0) { stats.totalDuration += dur; durationCount++; }

      stats.totalQueries += p.queriesUsed;

      if (p.level) {
        stats.levelDistribution[p.level] = (stats.levelDistribution[p.level] || 0) + 1;
      }

      (p.tags || []).forEach(function (t) {
        stats.tagDistribution[t] = (stats.tagDistribution[t] || 0) + 1;
      });

      var tier = p.enrichmentTier != null ? p.enrichmentTier : -1;
      if (tier >= 0) {
        stats.tierDistribution[tier] = (stats.tierDistribution[tier] || 0) + 1;
      }

      // Aggregate phase timings
      if (p.phaseTimings) {
        Object.keys(p.phaseTimings).forEach(function (stage) {
          if (stage === 'total') return;
          if (!stats.stageTimingAggregates[stage]) {
            stats.stageTimingAggregates[stage] = { total: 0, count: 0, max: 0 };
          }
          var agg = stats.stageTimingAggregates[stage];
          var val = p.phaseTimings[stage];
          agg.total += val;
          agg.count++;
          if (val > agg.max) agg.max = val;
        });
      }
    });

    if (durationCount > 0) stats.avgDuration = stats.totalDuration / durationCount;
    if (stats.totalPuzzles > 0) stats.avgQueries = stats.totalQueries / stats.totalPuzzles;

    // Compute avg for stage timing aggregates
    Object.keys(stats.stageTimingAggregates).forEach(function (k) {
      var a = stats.stageTimingAggregates[k];
      a.avg = a.count > 0 ? a.total / a.count : 0;
      a.pct = stats.totalDuration > 0 ? (a.total / stats.totalDuration * 100) : 0;
    });

    return {
      events: events,
      puzzles: puzzles,
      stats: stats,
      runId: runId,
      sessionStart: sessionStart,
      sessionEnd: sessionEnd,
      fileName: fileName || 'unknown',
      modelConfig: {
        configHash: configHash,
        configDump: configDump,
        models: modelsUsed,
        visits: visitsUsed,
        escalations: escalationCount
      }
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // S1: Header Section (T3)
  // ═══════════════════════════════════════════════════════════════

  function renderHeader(store, container) {
    container.textContent = '';
    var title = el('h2', { className: 'section-title' }, 'Run Overview');
    var grid = el('div', { className: 'header-grid' });

    var cards = [
      { label: 'File', value: store.fileName },
      { label: 'Run ID', value: store.runId || '\u2014' },
      { label: 'Session Start', value: formatTimestamp(store.sessionStart) },
      { label: 'Puzzles', value: String(store.stats.totalPuzzles) },
      { label: 'Total Duration', value: formatDuration(store.stats.totalDuration) },
      { label: 'Avg Duration', value: formatDuration(store.stats.avgDuration) },
      { label: 'Total Queries', value: String(store.stats.totalQueries) },
      { label: 'Avg Queries', value: store.stats.avgQueries.toFixed(1) }
    ];

    cards.forEach(function (c) {
      var card = el('div', { className: 'header-card' });
      var lbl = el('div', { className: 'header-card-label' });
      lbl.textContent = c.label;
      var val = el('div', { className: 'header-card-value' });
      val.textContent = c.value;
      card.appendChild(lbl);
      card.appendChild(val);
      grid.appendChild(card);
    });

    container.appendChild(title);
    container.appendChild(grid);

    // ── Model Configuration sub-section ──
    var mc = store.modelConfig;
    var modelKeys = Object.keys(mc.models);
    var visitKeys = Object.keys(mc.visits);
    var hasModelData = modelKeys.length > 0 || mc.configHash;

    if (hasModelData) {
      var mcSection = el('div', { className: 'model-config-section' });
      var mcTitle = el('div', { className: 'model-config-title' });
      mcTitle.textContent = 'Model Configuration';
      mcSection.appendChild(mcTitle);

      var mcGrid = el('div', { className: 'model-config-grid' });

      // Models used
      if (modelKeys.length > 0) {
        modelKeys.forEach(function (arch) {
          var item = el('div', { className: 'model-config-item' });
          var lbl = el('div', { className: 'model-config-label' });
          lbl.textContent = 'Model';
          var val = el('div', { className: 'model-config-value' });
          val.textContent = arch;
          if (mc.models[arch] > 1) {
            var count = el('span', { className: 'model-config-count' });
            count.textContent = '\u00d7' + mc.models[arch];
            val.appendChild(count);
          }
          item.appendChild(lbl);
          item.appendChild(val);
          mcGrid.appendChild(item);
        });
      }

      // Visit tiers observed
      if (visitKeys.length > 0) {
        var visitItem = el('div', { className: 'model-config-item' });
        var visitLbl = el('div', { className: 'model-config-label' });
        visitLbl.textContent = 'Visit Budgets';
        var visitVal = el('div', { className: 'model-config-value' });
        visitVal.textContent = visitKeys.sort(function (a, b) { return Number(a) - Number(b); }).join(', ');
        visitItem.appendChild(visitLbl);
        visitItem.appendChild(visitVal);
        mcGrid.appendChild(visitItem);
      }

      // Escalations
      if (mc.escalations > 0) {
        var escItem = el('div', { className: 'model-config-item' });
        var escLbl = el('div', { className: 'model-config-label' });
        escLbl.textContent = 'Escalations';
        var escVal = el('div', { className: 'model-config-value' });
        escVal.textContent = String(mc.escalations);
        escItem.appendChild(escLbl);
        escItem.appendChild(escVal);
        mcGrid.appendChild(escItem);
      }

      // Config hash
      if (mc.configHash) {
        var hashItem = el('div', { className: 'model-config-item' });
        var hashLbl = el('div', { className: 'model-config-label' });
        hashLbl.textContent = 'Config Hash';
        var hashVal = el('div', { className: 'model-config-value is-code' });
        hashVal.textContent = mc.configHash;
        hashItem.appendChild(hashLbl);
        hashItem.appendChild(hashVal);
        mcGrid.appendChild(hashItem);
      }

      mcSection.appendChild(mcGrid);
      container.appendChild(mcSection);
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // S2: Summary Section (T3)
  // ═══════════════════════════════════════════════════════════════

  function renderSummary(store, container) {
    container.textContent = '';
    var title = el('h2', { className: 'section-title' }, 'Summary');
    container.appendChild(title);

    var grid = el('div', { className: 'summary-grid' });

    // Status doughnut
    var statusBox = el('div');
    var statusLabel = el('h3', {}, 'Status Distribution');
    statusBox.appendChild(statusLabel);

    if (store.stats.totalPuzzles > 0 && typeof Chart !== 'undefined') {
      var statusCanvas = el('canvas');
      var statusWrap = el('div', { className: 'chart-container' }, statusCanvas);
      statusBox.appendChild(statusWrap);
      grid.appendChild(statusBox);

      requestAnimationFrame(function () {
        var ch = new Chart(statusCanvas.getContext('2d'), {
          type: 'doughnut',
          data: {
            labels: ['Accepted', 'Flagged', 'Rejected', 'Error'],
            datasets: [{
              data: [store.stats.accepted, store.stats.flagged, store.stats.rejected, store.stats.errors],
              backgroundColor: [getCssVar('--chart-accepted'), getCssVar('--chart-flagged'), getCssVar('--chart-rejected'), getCssVar('--chart-error')]
            }]
          },
          options: {
            responsive: true, maintainAspectRatio: true,
            plugins: { legend: { position: 'bottom', labels: { color: getCssVar('--text-primary') } } }
          }
        });
        chartInstances.push(ch);
      });
    } else {
      var statusTable = buildStatusTable(store.stats);
      statusBox.appendChild(statusTable);
      grid.appendChild(statusBox);
    }

    // Level distribution bar chart
    var levelKeys = Object.keys(store.stats.levelDistribution);
    if (levelKeys.length > 0) {
      var levelBox = el('div');
      levelBox.appendChild(el('h3', {}, 'Level Distribution'));

      if (typeof Chart !== 'undefined') {
        var levelCanvas = el('canvas');
        levelBox.appendChild(el('div', { className: 'chart-container' }, levelCanvas));
        grid.appendChild(levelBox);

        requestAnimationFrame(function () {
          var ch = new Chart(levelCanvas.getContext('2d'), {
            type: 'bar',
            data: {
              labels: levelKeys,
              datasets: [{ label: 'Puzzles', data: levelKeys.map(function (k) { return store.stats.levelDistribution[k]; }), backgroundColor: getCssVar('--accent-blue') }]
            },
            options: {
              responsive: true, maintainAspectRatio: true, indexAxis: 'y',
              plugins: { legend: { display: false } },
              scales: { x: { ticks: { color: getCssVar('--text-secondary') } }, y: { ticks: { color: getCssVar('--text-primary') } } }
            }
          });
          chartInstances.push(ch);
        });
      } else {
        levelBox.appendChild(buildDistributionTable(store.stats.levelDistribution, 'Level'));
        grid.appendChild(levelBox);
      }
    }

    // Tag frequency bar chart (top 15)
    var tagKeys = Object.keys(store.stats.tagDistribution).sort(function (a, b) {
      return store.stats.tagDistribution[b] - store.stats.tagDistribution[a];
    }).slice(0, 15);

    if (tagKeys.length > 0) {
      var tagBox = el('div');
      tagBox.appendChild(el('h3', {}, 'Top Tags'));

      if (typeof Chart !== 'undefined') {
        var tagCanvas = el('canvas');
        tagBox.appendChild(el('div', { className: 'chart-container' }, tagCanvas));
        grid.appendChild(tagBox);

        requestAnimationFrame(function () {
          var ch = new Chart(tagCanvas.getContext('2d'), {
            type: 'bar',
            data: {
              labels: tagKeys,
              datasets: [{ label: 'Count', data: tagKeys.map(function (k) { return store.stats.tagDistribution[k]; }), backgroundColor: getCssVar('--accent-green') }]
            },
            options: {
              responsive: true, maintainAspectRatio: true, indexAxis: 'y',
              plugins: { legend: { display: false } },
              scales: { x: { ticks: { color: getCssVar('--text-secondary') } }, y: { ticks: { color: getCssVar('--text-primary') } } }
            }
          });
          chartInstances.push(ch);
        });
      } else {
        tagBox.appendChild(buildDistributionTable(store.stats.tagDistribution, 'Tag'));
        grid.appendChild(tagBox);
      }
    }

    // Tier distribution — stacked horizontal bar chart
    var tierKeys = Object.keys(store.stats.tierDistribution);
    if (tierKeys.length > 0) {
      var tierBox = el('div');
      tierBox.appendChild(el('h3', {}, 'Enrichment Tiers'));

      if (typeof Chart !== 'undefined') {
        var tierCanvas = el('canvas');
        tierBox.appendChild(el('div', { className: 'chart-container' }, tierCanvas));
        grid.appendChild(tierBox);

        requestAnimationFrame(function () {
          // Build one dataset per tier for stacked bar (each tier = one colored segment)
          var allTiers = [0, 1, 2, 3];
          var total = store.stats.totalPuzzles || 1;
          var datasets = allTiers.filter(function (t) {
            return store.stats.tierDistribution[t] > 0;
          }).map(function (t) {
            var desc = TIER_DESCRIPTIONS[t] || TIER_DESCRIPTIONS[0];
            var count = store.stats.tierDistribution[t] || 0;
            var pct = (count / total * 100).toFixed(1);
            return {
              label: desc.badge + ' (' + count + ', ' + pct + '%)',
              data: [count],
              backgroundColor: getCssVar(TIER_COLORS[t].bg.replace('var(', '').replace(')', '')),
              borderWidth: 0
            };
          });

          var ch = new Chart(tierCanvas.getContext('2d'), {
            type: 'bar',
            data: {
              labels: ['Tiers'],
              datasets: datasets
            },
            options: {
              responsive: true, maintainAspectRatio: true, indexAxis: 'y',
              scales: {
                x: { stacked: true, ticks: { color: getCssVar('--text-secondary') }, title: { display: true, text: 'Puzzles', color: getCssVar('--text-secondary') } },
                y: { stacked: true, display: false }
              },
              plugins: {
                legend: { position: 'bottom', labels: { color: getCssVar('--text-primary'), usePointStyle: true, pointStyle: 'rect' } },
                tooltip: {
                  callbacks: {
                    label: function (ctx) {
                      var tierIdx = allTiers.filter(function (t) { return store.stats.tierDistribution[t] > 0; })[ctx.datasetIndex];
                      var desc = TIER_DESCRIPTIONS[tierIdx] || TIER_DESCRIPTIONS[0];
                      var count = ctx.raw;
                      var pct = (count / total * 100).toFixed(1);
                      return desc.label + ': ' + count + ' (' + pct + '%) \u2014 ' + desc.description;
                    }
                  }
                }
              }
            }
          });
          chartInstances.push(ch);
        });
      } else {
        // Fallback: list with semantic badges when Chart.js unavailable
        var tierList = el('ul', { className: 'tier-list' });
        tierKeys.sort().forEach(function (t) {
          var desc = TIER_DESCRIPTIONS[t] || TIER_DESCRIPTIONS[0];
          var badgeCls = TIER_BADGE_CLASSES[t] || 'badge badge-tier-0';
          var li = el('li');
          var badge = el('span', { className: badgeCls, title: desc.description, tabindex: '0' });
          badge.textContent = desc.badge;
          li.appendChild(badge);
          var count = store.stats.tierDistribution[t];
          var pct = store.stats.totalPuzzles > 0 ? (count / store.stats.totalPuzzles * 100).toFixed(1) : '0.0';
          var text = el('span');
          text.textContent = desc.label + ' \u2014 ' + count + ' puzzle(s) (' + pct + '%)';
          li.appendChild(text);
          tierList.appendChild(li);
        });
        tierBox.appendChild(tierList);
        grid.appendChild(tierBox);
      }
    }

    container.appendChild(grid);
  }

  function buildStatusTable(stats) {
    var tbl = el('table', { className: 'timing-table' });
    var thead = el('thead');
    var hr = el('tr');
    ['Status', 'Count'].forEach(function (h) { var th = el('th'); th.textContent = h; hr.appendChild(th); });
    thead.appendChild(hr);
    tbl.appendChild(thead);
    var tbody = el('tbody');
    [['Accepted', stats.accepted], ['Flagged', stats.flagged], ['Rejected', stats.rejected], ['Error', stats.errors]].forEach(function (row) {
      var tr = el('tr');
      row.forEach(function (val) { var td = el('td'); td.textContent = String(val); tr.appendChild(td); });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    return tbl;
  }

  function buildDistributionTable(dist, label) {
    var tbl = el('table', { className: 'timing-table' });
    var thead = el('thead');
    var hr = el('tr');
    [label, 'Count'].forEach(function (h) { var th = el('th'); th.textContent = h; hr.appendChild(th); });
    thead.appendChild(hr);
    tbl.appendChild(thead);
    var tbody = el('tbody');
    Object.keys(dist).forEach(function (k) {
      var tr = el('tr');
      var td1 = el('td'); td1.textContent = k; tr.appendChild(td1);
      var td2 = el('td'); td2.textContent = String(dist[k]); tr.appendChild(td2);
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    return tbl;
  }

  // ═══════════════════════════════════════════════════════════════
  // S3: Timing Section (T4)
  // ═══════════════════════════════════════════════════════════════

  function renderTiming(store, container) {
    container.textContent = '';

    var totalDur = store.stats.totalDuration;
    var title = el('h2', { className: 'section-title' },
      'Timing' + (totalDur > 0 ? ' (' + formatDuration(totalDur) + ' total)' : ''));
    container.appendChild(title);

    var stages = Object.keys(store.stats.stageTimingAggregates);
    if (stages.length === 0) {
      container.appendChild(el('div', { className: 'cta-box', textContent: 'No phase timing data available. Run enrichment with --verbose to capture per-phase timings.' }));
      return;
    }

    // Map stages to their PIPELINE_STAGES index for consistent coloring
    function stageColorIndex(key) {
      for (var i = 0; i < PIPELINE_STAGES.length; i++) {
        if (PIPELINE_STAGES[i].key === key) return i;
      }
      return stages.indexOf(key);
    }

    // Build segments sorted by percentage descending for the stacked bar,
    // but keep original pipeline order for the bar rendering
    var segments = [];
    var grandTotal = 0;
    stages.forEach(function (s) {
      grandTotal += store.stats.stageTimingAggregates[s].total;
    });

    // Use pipeline stage order for bar, keeping only those with data
    var orderedStages = [];
    PIPELINE_STAGES.forEach(function (ps) {
      if (store.stats.stageTimingAggregates[ps.key]) {
        orderedStages.push(ps.key);
      }
    });
    // Add any stages not in PIPELINE_STAGES (custom keys)
    stages.forEach(function (s) {
      if (orderedStages.indexOf(s) === -1) orderedStages.push(s);
    });

    orderedStages.forEach(function (s) {
      var agg = store.stats.stageTimingAggregates[s];
      var pct = grandTotal > 0 ? (agg.total / grandTotal * 100) : 0;
      segments.push({
        key: s,
        total: agg.total,
        pct: pct,
        colorIdx: stageColorIndex(s)
      });
    });

    // Proportional stacked horizontal bar
    var bar = el('div', { className: 'timing-waterfall' });
    segments.forEach(function (seg) {
      if (seg.pct < 0.3) return; // skip tiny slices from the bar
      var segEl = el('div', { className: 'timing-waterfall-seg' });
      segEl.style.width = Math.max(seg.pct, 0.5) + '%';
      segEl.style.backgroundColor = PHASE_COLORS[seg.colorIdx % PHASE_COLORS.length];
      // Show label only if segment is wide enough
      if (seg.pct >= 8) {
        var label = el('span', { className: 'timing-waterfall-label' });
        label.textContent = seg.key;
        segEl.appendChild(label);
      }
      segEl.setAttribute('title', seg.key + ': ' + formatDuration(seg.total) + ' (' + seg.pct.toFixed(1) + '%)');
      bar.appendChild(segEl);
    });
    container.appendChild(bar);

    // Legend with all stages (wrapping like the screenshot)
    var legend = el('div', { className: 'timing-waterfall-legend' });
    segments.forEach(function (seg) {
      var item = el('span', { className: 'timing-waterfall-legend-item' });
      var dot = el('span', { className: 'timing-waterfall-legend-dot' });
      dot.style.backgroundColor = PHASE_COLORS[seg.colorIdx % PHASE_COLORS.length];
      item.appendChild(dot);
      var text = document.createTextNode(
        seg.key + ' ' + formatDuration(seg.total) + ' (' + seg.pct.toFixed(1) + '%)'
      );
      item.appendChild(text);
      legend.appendChild(item);
    });
    container.appendChild(legend);
  }

  // ═══════════════════════════════════════════════════════════════
  // S4: Pipeline Journey (T5)
  // ═══════════════════════════════════════════════════════════════

  function renderPipelineJourney(store, container) {
    container.textContent = '';

    var isBatch = store.stats.totalPuzzles > 1;

    // Compute per-stage aggregate status (needed for both views)
    var stageStats = {};
    PIPELINE_STAGES.forEach(function (s) {
      stageStats[s.key] = { completed: 0, failed: 0, skipped: 0, noData: 0 };
    });

    var total = store.stats.totalPuzzles;

    store.puzzles.forEach(function (p) {
      var timings = p.phaseTimings;
      var hitFailure = false;

      PIPELINE_STAGES.forEach(function (s) {
        var stat = stageStats[s.key];
        if (!timings) {
          stat.noData++;
          return;
        }
        if (hitFailure) {
          stat.skipped++;
          return;
        }
        // Flexible match: exact key OR any timing key containing the stage key
        var found = timings[s.key] != null;
        if (!found) {
          var timingKeys = Object.keys(timings);
          for (var k = 0; k < timingKeys.length; k++) {
            if (timingKeys[k].indexOf(s.key) !== -1) { found = true; break; }
          }
        }
        if (found) {
          stat.completed++;
        } else if (p.status === 'error') {
          stat.failed++;
          hitFailure = true;
        } else {
          stat.skipped++;
        }
      });
    });

    // For batch mode: wrap in collapsible details with health digest
    var contentTarget = container;
    if (isBatch) {
      var fullyCompleted = 0;
      PIPELINE_STAGES.forEach(function (s) {
        if (stageStats[s.key].completed === total && total > 0) fullyCompleted++;
      });
      var healthColor = fullyCompleted === PIPELINE_STAGES.length ? '--accent-green'
        : fullyCompleted >= PIPELINE_STAGES.length * 0.7 ? '--accent-amber'
        : '--accent-red';
      var healthLabel = fullyCompleted === PIPELINE_STAGES.length ? 'Healthy'
        : fullyCompleted >= PIPELINE_STAGES.length * 0.7 ? 'Partial'
        : 'Issues';

      var details = el('details', { className: 'pipeline-collapse' });
      var summary = el('summary', { className: 'pipeline-collapse-summary' });
      var summaryTitle = el('span', { className: 'pipeline-collapse-title' });
      summaryTitle.textContent = 'Pipeline Journey';
      summary.appendChild(summaryTitle);

      var summaryDigest = el('span', { className: 'pipeline-collapse-digest' });
      var badge = el('span', { className: 'pipeline-health-badge' });
      badge.style.backgroundColor = getCssVar(healthColor);
      badge.textContent = healthLabel;
      summaryDigest.appendChild(badge);
      summaryDigest.appendChild(document.createTextNode(
        ' \u00b7 ' + fullyCompleted + '/' + PIPELINE_STAGES.length + ' stages complete \u00b7 ' + total + ' puzzles'
      ));
      summary.appendChild(summaryDigest);
      details.appendChild(summary);
      container.appendChild(details);
      contentTarget = details;
    } else {
      var title = el('h2', { className: 'section-title' }, 'Pipeline Journey');
      container.appendChild(title);
    }

    // Build SVG
    var nodeW = 80, nodeH = 44, gap = 6, pad = 16;
    var svgW = pad * 2 + PIPELINE_STAGES.length * (nodeW + gap) - gap;
    var svgH = 100;

    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 ' + svgW + ' ' + svgH);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', svgH);
    svg.style.maxWidth = svgW + 'px';

    PIPELINE_STAGES.forEach(function (s, i) {
      var x = pad + i * (nodeW + gap);
      var y = 12;
      var stat = stageStats[s.key];

      // Determine color
      var color, textColor;
      if (stat.completed === total && total > 0) {
        color = getCssVar('--accent-green'); textColor = '#fff';
      } else if (stat.failed > 0) {
        color = getCssVar('--accent-red'); textColor = '#fff';
      } else if (stat.completed > 0) {
        color = getCssVar('--accent-amber'); textColor = '#000';
      } else if (stat.noData === total) {
        color = getCssVar('--text-muted'); textColor = '#fff';
      } else {
        color = getCssVar('--accent-gray'); textColor = '#fff';
      }

      // Connecting line
      if (i > 0) {
        var line = document.createElementNS(svgNS, 'line');
        line.setAttribute('x1', String(x - gap));
        line.setAttribute('y1', String(y + nodeH / 2));
        line.setAttribute('x2', String(x));
        line.setAttribute('y2', String(y + nodeH / 2));
        line.setAttribute('stroke', getCssVar('--border-color'));
        line.setAttribute('stroke-width', '2');
        if (stat.noData === total) line.setAttribute('stroke-dasharray', '4,3');
        svg.appendChild(line);
      }

      // Node rect
      var rect = document.createElementNS(svgNS, 'rect');
      rect.setAttribute('x', String(x));
      rect.setAttribute('y', String(y));
      rect.setAttribute('width', String(nodeW));
      rect.setAttribute('height', String(nodeH));
      rect.setAttribute('rx', '6');
      rect.setAttribute('fill', color);
      rect.setAttribute('data-stage-key', s.key);
      rect.addEventListener('click', (function (stageKey) {
        return function () {
          if (triggerSearch) {
            triggerSearch(stageKey);
            var searchSection = document.getElementById('s6-search');
            if (searchSection) searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        };
      })(s.key));
      svg.appendChild(rect);

      // Stage label
      var text = document.createElementNS(svgNS, 'text');
      text.setAttribute('x', String(x + nodeW / 2));
      text.setAttribute('y', String(y + 17));
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('fill', textColor);
      text.setAttribute('font-size', '10');
      text.setAttribute('font-family', 'sans-serif');
      text.textContent = s.label;
      svg.appendChild(text);

      // Status indicator — clearer icons
      var icon;
      if (stat.completed === total && total > 0) icon = '\u2713';  // checkmark
      else if (stat.failed > 0) icon = '\u2717';                    // X
      else if (stat.noData === total) icon = '\u00b7';              // middle dot
      else icon = '\u2013';                                         // en-dash (skipped)

      var statusText = document.createElementNS(svgNS, 'text');
      statusText.setAttribute('x', String(x + nodeW / 2));
      statusText.setAttribute('y', String(y + 34));
      statusText.setAttribute('text-anchor', 'middle');
      statusText.setAttribute('fill', textColor);
      statusText.setAttribute('font-size', '13');
      statusText.textContent = icon;
      svg.appendChild(statusText);

      // Percentage below node (batch mode)
      if (total > 1) {
        var pctText = document.createElementNS(svgNS, 'text');
        pctText.setAttribute('x', String(x + nodeW / 2));
        pctText.setAttribute('y', String(y + nodeH + 16));
        pctText.setAttribute('text-anchor', 'middle');
        pctText.setAttribute('fill', getCssVar('--text-secondary'));
        pctText.setAttribute('font-size', '10');
        var pct = total > 0 ? Math.round(stat.completed / total * 100) : 0;
        pctText.textContent = pct + '%';
        svg.appendChild(pctText);
      }
    });

    var svgContainer = el('div', { className: 'pipeline-svg-container' });
    svgContainer.appendChild(svg);
    contentTarget.appendChild(svgContainer);

    // Legend
    var legend = el('div', { className: 'pipeline-legend' });
    [
      { color: getCssVar('--accent-green'), label: 'Completed' },
      { color: getCssVar('--accent-amber'), label: 'Partial' },
      { color: getCssVar('--accent-red'), label: 'Failed' },
      { color: getCssVar('--accent-gray'), label: 'Not reached' },
      { color: getCssVar('--text-muted'), label: 'No timing data' }
    ].forEach(function (item) {
      var li = el('span', { className: 'pipeline-legend-item' });
      var dot = el('span', { className: 'pipeline-legend-dot' });
      dot.style.backgroundColor = item.color;
      li.appendChild(dot);
      li.appendChild(document.createTextNode(item.label));
      legend.appendChild(li);
    });
    contentTarget.appendChild(legend);
  }

  // ═══════════════════════════════════════════════════════════════
  // S5: Puzzle Details (T7) — v6 6-zone layout
  // ═══════════════════════════════════════════════════════════════

  // Clipboard copy helper with "Copied!" feedback
  function copyToClipboard(text, btnEl) {
    if (!text) return;
    var orig = btnEl.textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        btnEl.textContent = '\u2713 Copied';
        btnEl.classList.add('sgf-btn-copied');
        setTimeout(function () { btnEl.textContent = orig; btnEl.classList.remove('sgf-btn-copied'); }, 1500);
      });
    } else {
      // Fallback for file:// protocol
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (e) { /* ignore */ }
      document.body.removeChild(ta);
      btnEl.textContent = '\u2713 Copied';
      btnEl.classList.add('sgf-btn-copied');
      setTimeout(function () { btnEl.textContent = orig; btnEl.classList.remove('sgf-btn-copied'); }, 1500);
    }
  }

  // Normalize confidence from string ("high"/"medium"/"low") or number (0-1)
  // REC-3: low maps to 0.2 (not 0.0) because even low-confidence results carry
  // some signal — zero would imply "no information" whereas low means "uncertain
  // but still attempted". This preserves visibility in bar/sparkline charts.
  var CONFIDENCE_MAP = { high: 1.0, medium: 0.5, low: 0.2 };
  var CONFIDENCE_LABELS = { high: 'high', medium: 'medium', low: 'low' };
  var CONFIDENCE_TIPS = {
    high: 'KataGo agrees with the puzzle\u2019s correct move (top-ranked)',
    medium: 'KataGo agrees but solution depth is 0 (single-move puzzle)',
    low: 'KataGo\u2019s top move differs from the puzzle\u2019s correct move'
  };
  function normalizeConfidence(raw) {
    if (raw == null) return null;
    if (typeof raw === 'string' && CONFIDENCE_MAP[raw] !== undefined) return { label: CONFIDENCE_LABELS[raw], numeric: CONFIDENCE_MAP[raw], tip: CONFIDENCE_TIPS[raw] };
    var n = typeof raw === 'string' ? parseFloat(raw) : raw;
    if (isNaN(n)) return null;
    var label = n >= 0.8 ? 'high' : n >= 0.5 ? 'medium' : 'low';
    return { label: label, numeric: n, tip: CONFIDENCE_TIPS[label] };
  }

  // Determine semantic class for a value
  function signalClass(key, value) {
    if (key === 'katago_agrees') return value === true || value === 'Yes' ? 'is-ok' : 'is-error';
    if (key === 'confidence') {
      var c = normalizeConfidence(value);
      if (!c) return 'is-error';
      if (c.numeric >= 0.8) return 'is-ok';
      if (c.numeric >= 0.5) return 'is-warn';
      return 'is-error';
    }
    if (key === 'tree_validation') {
      if (value === 'pass') return 'is-ok';
      if (value === 'skipped_confident') return 'is-warn';
      return 'is-error';
    }
    if (key === 'status') {
      var statusStr = typeof value === 'string' ? value.replace('ValidationStatus.', '').toLowerCase() : '';
      if (statusStr === 'accepted') return 'is-ok';
      if (statusStr === 'flagged') return 'is-warn';
      if (statusStr === 'rejected' || statusStr === 'no_solution' || statusStr === 'disagreement') return 'is-error';
    }
    if (key === 'ac_level') {
      var n = typeof value === 'string' ? parseInt(value, 10) : value;
      if (n >= 2) return 'is-ok';
      if (n === 1) return 'is-warn';
      return 'is-error';
    }
    return '';
  }

  // Navigate to a Signal Quality reference card
  function navigateToSignalQualityRef(anchorId) {
    var refSection = document.getElementById('s7-reference');
    var refDetails = refSection ? refSection.querySelector('.ref-details') : null;
    if (refDetails) refDetails.open = true;
    var sqTabBtn = refSection ? refSection.querySelector('[data-tab="signal-quality"]') : null;
    if (sqTabBtn) sqTabBtn.click();
    var target = document.getElementById(anchorId);
    if (target) setTimeout(function () { target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 50);
  }

  // Build a stage-kv row with optional semantic coloring
  function stageKvRow(label, value, opts) {
    opts = opts || {};
    var row = el('div', { className: 'stage-kv' });
    row.appendChild(el('span', { className: 'stage-kv-label', textContent: label }));
    var valEl = el('span', { className: 'stage-kv-value' + (opts.mono ? ' is-code' : '') });
    var sigCls = opts.signalKey ? signalClass(opts.signalKey, opts.signalValue !== undefined ? opts.signalValue : value) : '';
    if (sigCls) valEl.className += ' ' + sigCls;
    valEl.textContent = value;
    // Apply tooltip to value element (not the row)
    if (opts.valueTip) valEl.title = opts.valueTip;
    // Make signal values clickable to search
    else if (opts.signalKey && value && value !== '\u2014') {
      valEl.classList.add('is-searchable');
      valEl.title = 'Click to search: ' + opts.signalKey + ' + ' + value;
      valEl.addEventListener('click', function () {
        if (triggerSearch) {
          triggerSearch(opts.signalKey + ' + ' + value);
          var searchSection = document.getElementById('s6-search');
          if (searchSection) searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    }
    row.appendChild(valEl);
    // Cross-reference link to Signal Quality tab — sits in grid column 3
    if (!opts.refAnchor) {
      // No icon: let the value span columns 2-3 for clean right-alignment
      valEl.style.gridColumn = '2 / -1';
    } else {
      var refLink = el('span', { className: 'ref-link-icon', title: opts.refTip || 'View reference' });
      refLink.textContent = '?';
      refLink.addEventListener('click', function (e) {
        e.stopPropagation();
        navigateToSignalQualityRef(opts.refAnchor);
      });
      row.appendChild(refLink);
    }
    return row;
  }

  // Determine if a puzzle has any warning signals for summary badge
  function hasWarningSignals(p) {
    var sd = p.stageDetails;
    if (sd.validate_move) {
      if (sd.validate_move.katago_agrees === false) return true;
      if (sd.validate_move.flags && sd.validate_move.flags.length > 0) return true;
    }
    if (sd.estimate_difficulty && sd.estimate_difficulty.confidence != null) {
      var c = normalizeConfidence(sd.estimate_difficulty.confidence);
      if (c && c.numeric < 0.5) return true;
    }
    if (p.status === 'flagged' || p.status === 'rejected') return true;
    return false;
  }

  function renderPuzzleDetails(store, container) {
    container.textContent = '';
    var title = el('h2', { className: 'section-title' }, 'Puzzle Details');
    container.appendChild(title);

    if (store.puzzles.size === 0) {
      container.appendChild(el('div', { className: 'cta-box', textContent: 'No puzzle data found in this log file.' }));
      return;
    }

    var entries = Array.from(store.puzzles.values());

    entries.forEach(function (p) {
      var details = document.createElement('details');
      details.className = 'puzzle-card';
      details.id = 'puzzle-' + (p.traceId || '');

      var summary = document.createElement('summary');
      var idText = document.createTextNode((p.puzzleId || p.traceId || 'unknown') + ' ');
      summary.appendChild(idText);
      if (p.status) {
        var sBadge = el('span', {
          className: statusBadgeClass(p.status),
          title: (STATUS_TOOLTIPS[p.status] || p.status) + ' \u2014 click to filter by this status'
        });
        sBadge.textContent = p.status;
        sBadge.addEventListener('click', function (e) {
          e.preventDefault();
          e.stopPropagation();
          if (triggerSearch) {
            triggerSearch('"status":"' + p.status + '"');
            var searchSection = document.getElementById('s6-search');
            if (searchSection) searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        });
        summary.appendChild(sBadge);
      }
      if (p.level) {
        var lBadge = el('span', { className: 'badge badge-level' });
        lBadge.textContent = p.level;
        summary.appendChild(lBadge);
      }
      if (p.enrichmentTier != null) {
        var tDesc = TIER_DESCRIPTIONS[p.enrichmentTier] || TIER_DESCRIPTIONS[0];
        var tBadgeCls = TIER_BADGE_CLASSES[p.enrichmentTier] || 'badge badge-tier-0';
        var tBadge = el('span', { className: tBadgeCls, title: tDesc.description });
        tBadge.textContent = 'T' + p.enrichmentTier;
        summary.appendChild(tBadge);
      }
      // Warning indicator in summary
      if (hasWarningSignals(p)) {
        var warnBadge = el('span', { className: 'badge badge-warn-signal', title: 'Has warning signals — expand for details' });
        warnBadge.textContent = '\u26A0';
        summary.appendChild(warnBadge);
      }
      details.appendChild(summary);

      // Lazy content rendering
      var loaded = false;
      details.addEventListener('toggle', function () {
        if (!details.open || loaded) return;
        loaded = true;
        var body = el('div', { className: 'puzzle-detail-body' });

        // ── ZONE A: Compact metadata strip (3-column) ──
        var metaStrip = el('div', { className: 'zone-meta-strip' });

        var metaRow = el('div', { className: 'meta-row-3col' });

        // Column 1: Source
        var srcItem = el('div', { className: 'meta-item' });
        srcItem.appendChild(el('div', { className: 'meta-label', textContent: 'SOURCE' }));
        var srcVal = el('div', { className: 'meta-value meta-value-truncate', title: p.sourceFile || '\u2014' });
        srcVal.textContent = p.sourceFile || '\u2014';
        srcItem.appendChild(srcVal);
        metaRow.appendChild(srcItem);

        // Column 2: Trace ID
        var traceItem = el('div', { className: 'meta-item' });
        traceItem.appendChild(el('div', { className: 'meta-label', textContent: 'TRACE ID' }));
        var traceVal = el('div', { className: 'meta-value meta-value-truncate' });
        if (p.traceId) {
          var traceLink = el('span', { className: 'trace-link', title: p.traceId + ' \u2014 click to search' });
          traceLink.textContent = p.traceId;
          traceLink.addEventListener('click', function () {
            if (triggerSearch) {
              triggerSearch(p.traceId);
              var searchSection = document.getElementById('s6-search');
              if (searchSection) searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          });
          traceVal.appendChild(traceLink);
        } else {
          traceVal.textContent = '\u2014';
        }
        traceItem.appendChild(traceVal);
        metaRow.appendChild(traceItem);

        // Column 3: Stats (2×2 mini-grid)
        var statsItem = el('div', { className: 'meta-item' });
        var statsGrid = el('div', { className: 'meta-stats-grid' });
        var numericItems = [
          { label: 'Queries', value: (function() { var q = p.queriesByStage ? Object.values(p.queriesByStage).reduce(function(a,b){return a+b;},0) : p.queriesUsed; return q > 0 ? String(q) : '\u2014'; }()), title: p.queriesByStage ? 'Per stage: ' + Object.entries(p.queriesByStage).map(function(e) { return e[0] + '=' + e[1]; }).join(', ') : 'KataGo API calls (all stages)' },
          { label: 'Total Visits', value: p.totalVisits != null ? p.totalVisits.toLocaleString() : '\u2014', title: 'Sum of all KataGo visits across every query for this puzzle (solve-paths + analyze + refutations)' },
          { label: 'Tier', value: p.enrichmentTier != null ? (TIER_DESCRIPTIONS[p.enrichmentTier] || TIER_DESCRIPTIONS[0]).label : '\u2014' },
          { label: 'Duration', value: (p.endEvent && p.endEvent.elapsed_s) ? formatDuration(parseFloat(p.endEvent.elapsed_s)) : '\u2014' },
          { label: 'AC Level', value: p.acLevel != null ? String(p.acLevel) : '\u2014' }
        ];
        numericItems.forEach(function (m) {
          var cell = el('div', { className: 'meta-cell' });
          cell.appendChild(el('div', { className: 'meta-label', textContent: m.label }));
          var val = el('div', { className: 'meta-value is-code', textContent: m.value });
          if (m.title) val.title = m.title;
          cell.appendChild(val);
          statsGrid.appendChild(cell);
        });
        statsItem.appendChild(statsGrid);
        metaRow.appendChild(statsItem);

        metaStrip.appendChild(metaRow);

        if (p.errorMessage) {
          var errRow = el('div', { className: 'meta-error-row' });
          errRow.appendChild(el('span', { className: 'meta-label', textContent: 'ERROR' }));
          errRow.appendChild(el('span', { className: 'meta-value is-error-text', textContent: p.errorMessage }));
          metaStrip.appendChild(errRow);
        }

        body.appendChild(metaStrip);

        // ── ZONE B: Tags ──
        if (p.tags && p.tags.length > 0) {
          var chips = el('div', { className: 'tag-chips' });
          p.tags.forEach(function (t) {
            var chip = el('span', { className: 'tag-chip' });
            chip.textContent = t;
            chips.appendChild(chip);
          });
          body.appendChild(chips);
        }

        // ── ZONE C: SGF Toolbar (click-to-copy buttons) ──
        var hasSgf = p.sgfContent.original || p.sgfContent.framed || p.sgfContent.enriched;
        if (hasSgf) {
          var sgfToolbar = el('div', { className: 'sgf-toolbar' });
          sgfToolbar.appendChild(el('span', { className: 'sgf-toolbar-label', textContent: 'SGF' }));
          var sgfTypes = [
            { key: 'original', label: '\u2398 Original' },
            { key: 'framed', label: '\u2398 Framed' },
            { key: 'enriched', label: '\u2398 Enriched' }
          ];
          sgfTypes.forEach(function (st) {
            var content = p.sgfContent[st.key];
            var btn = el('button', { className: 'sgf-copy-btn' + (content ? '' : ' sgf-btn-disabled') });
            btn.textContent = st.label;
            if (content) {
              btn.title = 'Click to copy ' + st.key + ' SGF (' + content.length + ' chars)';
              btn.addEventListener('click', function () { copyToClipboard(content, btn); });
            } else {
              btn.title = 'Not available in this log';
              btn.disabled = true;
            }
            sgfToolbar.appendChild(btn);
          });
          body.appendChild(sgfToolbar);
        }

        // ── ZONE D: Solution bar (compact inline) ──
        var hasSolution = p.correctMoveSgf || p.correctMoveGtp || p.goal;
        var sd = p.stageDetails;
        if (!hasSolution && sd.extract_solution) {
          hasSolution = sd.extract_solution.correct_move_sgf || sd.extract_solution.has_solution;
        }
        if (hasSolution) {
          var solBar = el('div', { className: 'solution-bar' });

          var moveSgf = p.correctMoveSgf || (sd.extract_solution ? sd.extract_solution.correct_move_sgf : null);
          var moveGtp = p.correctMoveGtp || null;
          if (moveSgf || moveGtp) {
            var moveChip = el('span', { className: 'solution-chip' });
            moveChip.appendChild(el('span', { className: 'solution-chip-label', textContent: 'Move' }));
            var moveText = [];
            if (moveGtp) moveText.push(moveGtp);
            if (moveSgf) moveText.push('(' + moveSgf + ')');
            moveChip.appendChild(el('span', { className: 'solution-chip-value is-code', textContent: moveText.join(' ') }));
            solBar.appendChild(moveChip);
          }

          if (p.goal) {
            var goalChip = el('span', { className: 'solution-chip' });
            goalChip.appendChild(el('span', { className: 'solution-chip-label', textContent: 'Goal' }));
            goalChip.appendChild(el('span', { className: 'solution-chip-value', textContent: p.goal + (p.goalConfidence != null ? ' (' + p.goalConfidence + ')' : '') }));
            solBar.appendChild(goalChip);
          }

          if (p.refutations > 0) {
            var refChip = el('span', { className: 'solution-chip' });
            refChip.appendChild(el('span', { className: 'solution-chip-label', textContent: 'Wrong' }));
            refChip.appendChild(el('span', { className: 'solution-chip-value', textContent: String(p.refutations) + ' refutation' + (p.refutations !== 1 ? 's' : '') }));
            solBar.appendChild(refChip);
          }

          body.appendChild(solBar);
        }

        // (Hints are now rendered inside the Teaching card in Zone E)

        // ── ZONE E: Stage detail cards (2 groups) ──
        var hasStageData = Object.keys(sd).length > 0;

        if (hasStageData) {
          // Group 1: Input Quality
          var hasInputGroup = sd.parse_sgf || sd.extract_solution || sd.validate_move;
          if (hasInputGroup) {
            var inputGroup = el('div', { className: 'stage-group' });
            inputGroup.appendChild(el('div', { className: 'stage-group-title', textContent: 'Input Quality' }));
            var inputGrid = el('div', { className: 'stage-detail-grid' });

            // Parse SGF (input-only metrics)
            if (sd.parse_sgf) {
              var parse = sd.parse_sgf;
              var parseCard = el('div', { className: 'stage-detail-card' });
              parseCard.appendChild(el('h4', { textContent: 'Parse' }));
              parseCard.appendChild(stageKvRow('Board Size', parse.board_size != null ? String(parse.board_size) : '\u2014', { mono: true }));
              parseCard.appendChild(stageKvRow('Corner', parse.corner || '\u2014'));
              parseCard.appendChild(stageKvRow('Ko', parse.ko || '\u2014'));
              parseCard.appendChild(stageKvRow('SGF Length', parse.sgf_length != null ? String(parse.sgf_length) + ' chars' : '\u2014', { mono: true }));
              // Curated branch counts (data comes from validate_move stage but is an input property)
              var valData = sd.validate_move;
              if (valData) {
                parseCard.appendChild(stageKvRow('Curated Corrects', valData.curated_corrects != null ? String(valData.curated_corrects) : '\u2014', { mono: true }));
                parseCard.appendChild(stageKvRow('Curated Wrongs', valData.curated_wrongs != null ? String(valData.curated_wrongs) : '\u2014', { mono: true }));
              }
              inputGrid.appendChild(parseCard);
            }

            // Validation
            if (sd.validate_move) {
              var valEv = sd.validate_move;
              var valCard = el('div', { className: 'stage-detail-card' + (valEv.katago_agrees === false ? ' card-warn' : '') });
              valCard.appendChild(el('h4', { textContent: 'Validation' }));
              var katagoAgreesVal = valEv.katago_agrees != null ? (valEv.katago_agrees ? 'Yes' : 'No') : '\u2014';
              valCard.appendChild(stageKvRow('KataGo Agrees', katagoAgreesVal, { signalKey: 'katago_agrees', signalValue: valEv.katago_agrees, refAnchor: 'ref-sq-validation', refTip: 'Whether KataGo\u2019s top-ranked move matches the puzzle\u2019s correct move \u2014 click to see validation reference' }));
              var statusDisplayVal = valEv.status || '\u2014';
              var statusTipMap = { 'ValidationStatus.ACCEPTED': 'Passed all quality gates \u2014 ready for publication', 'ValidationStatus.FLAGGED': 'Borderline quality or KataGo disagrees \u2014 needs manual review', 'ValidationStatus.REJECTED': 'Failed validation: high winrate delta, ambiguous answer, or no solution tree', accepted: 'Passed all quality gates \u2014 ready for publication', flagged: 'Borderline quality or KataGo disagrees \u2014 needs manual review', rejected: 'Failed validation: high winrate delta, ambiguous answer, or no solution tree' };
              // Build status row with pill badge (strips ValidationStatus. prefix, uses badge color)
              (function () {
                var statusRow = el('div', { className: 'stage-kv' });
                statusRow.appendChild(el('span', { className: 'stage-kv-label', textContent: 'Status' }));
                var rawStatus = (valEv.status || '').replace('ValidationStatus.', '').toLowerCase();
                var badgeLabel = rawStatus ? rawStatus.charAt(0).toUpperCase() + rawStatus.slice(1) : '\u2014';
                var badgeCls = { accepted: 'badge-accepted', flagged: 'badge-flagged', rejected: 'badge-rejected', error: 'badge-error' }[rawStatus] || 'badge-error';
                var statusBadge = el('span', { className: 'stage-kv-status-badge badge ' + badgeCls, title: statusTipMap[statusDisplayVal] || '' });
                statusBadge.textContent = badgeLabel;
                statusRow.appendChild(statusBadge);
                var refLink2 = el('span', { className: 'ref-link-icon', title: 'Validation outcome \u2014 click to see accepted / flagged / rejected rules in Signal Quality reference' });
                refLink2.textContent = '?';
                refLink2.addEventListener('click', function (e) { e.stopPropagation(); navigateToSignalQualityRef('ref-sq-validation'); });
                statusRow.appendChild(refLink2);
                valCard.appendChild(statusRow);
              }());
              var tvVal = valEv.tree_validation || '\u2014';
              var tvTip = { pass: 'Solution tree fully validated against KataGo', fail: 'Solution tree has incorrect branches', skipped_confident: 'Tree validation skipped \u2014 KataGo very confident the first move is correct (high policy + top rank), so full tree traversal was unnecessary', partial: 'Partial tree validation completed' };
              var tvRow = stageKvRow('Tree Validation', tvVal, { signalKey: 'tree_validation', signalValue: valEv.tree_validation });
              tvRow.title = tvTip[tvVal] || '';
              valCard.appendChild(tvRow);
              // Policy Entropy & Move Rank from difficulty stage (validation-relevant signals)
              var diff = sd.estimate_difficulty;
              if (diff) {
                valCard.appendChild(stageKvRow('Policy Entropy', diff.policy_entropy != null && !isNaN(diff.policy_entropy) ? diff.policy_entropy.toFixed(2) : '\u2014', { mono: true }));
                valCard.appendChild(stageKvRow('KataGo Move Rank', diff.correct_move_rank != null ? '#' + diff.correct_move_rank : '\u2014', { mono: true }));
              }
              if (valEv.flags && valEv.flags.length > 0) {
                var flagsLabel = el('div', { className: 'stage-kv' });
                flagsLabel.appendChild(el('span', { className: 'stage-kv-label', textContent: 'Flags' }));
                var flagsContainer = el('div', { className: 'flag-chips' });
                // Flag tooltip descriptions
                var FLAG_TIPS = {
                  connection: 'Puzzle type: correct move achieves group connectivity (connecting/cutting)',
                  tree_validation_fail: 'Solution tree validation failed \u2014 depth_X/Y means X of Y expected moves validated correctly by KataGo',
                  tree_validation_partial: 'Solution tree partially validated \u2014 depth_X/Y means X of Y moves confirmed',
                  ko_type: 'Ko context detected in this puzzle',
                  winrate_rescue_auto_accepted: 'Auto-accepted despite disagreement: correct move has viable winrate',
                  katago_disagrees: 'KataGo\u2019s top move differs from the puzzle\u2019s intended correct move'
                };
                var REASON_TIPS = {
                  top_move_low_winrate: 'KataGo agrees on the move but the position winrate is very low',
                  in_top_n_uncertain_winrate: 'Correct move is in KataGo\u2019s top-N but with uncertain winrate',
                  not_in_top_n_low_winrate: 'Correct move is NOT in KataGo\u2019s top-N and has low winrate'
                };
                valEv.flags.forEach(function (f) {
                  var chip = el('span', { className: 'flag-chip' });
                  // Humanize tree_validation depth flags for display
                  var displayText = f;
                  var depthMatch = f.match(/^tree_validation_(fail|partial):depth_(\d+)\/(\d+)$/);
                  if (depthMatch) {
                    displayText = 'tree_validation_' + depthMatch[1] + ' (' + depthMatch[2] + '/' + depthMatch[3] + ' moves validated)';
                  }
                  chip.appendChild(document.createTextNode(displayText));
                  // Extract flag name for reference link (e.g., "reason:top_move_low_winrate" -> "top_move_low_winrate")
                  var flagName = f.indexOf(':') !== -1 ? f.split(':')[0] === 'reason' ? f.split(':')[1] : f.split(':')[0] : f;
                  // Build tooltip from flag tips
                  var tipText = '';
                  if (f.indexOf('reason:') === 0) tipText = REASON_TIPS[f.split(':')[1]] || '';
                  else if (f.indexOf('tree_validation_fail:') === 0) tipText = FLAG_TIPS.tree_validation_fail;
                  else if (f.indexOf('tree_validation_partial:') === 0) tipText = FLAG_TIPS.tree_validation_partial;
                  else tipText = FLAG_TIPS[flagName] || '';
                  if (tipText) chip.title = tipText;
                  var helpLink = el('span', { className: 'flag-chip-help', title: tipText || ('View definition for ' + flagName) });
                  helpLink.textContent = '?';
                  helpLink.addEventListener('click', function (e) {
                    e.stopPropagation();
                    // Try reference anchor first
                    var refEl = document.getElementById('ref-flag-' + flagName);
                    if (refEl) {
                      var refSection = document.getElementById('s7-reference');
                      var refDetails = refSection ? refSection.querySelector('.ref-details') : null;
                      if (refDetails) refDetails.open = true;
                      // Switch to flags tab
                      var flagsTabBtn = refSection ? refSection.querySelector('[data-tab="flags"]') : null;
                      if (flagsTabBtn) flagsTabBtn.click();
                      refEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } else if (triggerSearch) {
                      triggerSearch(flagName);
                      var searchSection = document.getElementById('s6-search');
                      if (searchSection) searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                  });
                  chip.appendChild(helpLink);
                  flagsContainer.appendChild(chip);
                });
                flagsLabel.appendChild(flagsContainer);
                valCard.appendChild(flagsLabel);
              }
              inputGrid.appendChild(valCard);
            }

            inputGroup.appendChild(inputGrid);
            body.appendChild(inputGroup);
          }

          // Group 2: Enrichment Output
          var hasOutputGroup = sd.estimate_difficulty || sd.technique_classification || sd.instinct_classification || sd.generate_refutations || sd.teaching_enrichment;
          if (hasOutputGroup) {
            var outputGroup = el('div', { className: 'stage-group' });
            outputGroup.appendChild(el('div', { className: 'stage-group-title', textContent: 'Enrichment Output' }));
            var outputGrid = el('div', { className: 'stage-detail-grid' });

            // Difficulty
            if (sd.estimate_difficulty) {
              var diff = sd.estimate_difficulty;
              var confNorm = normalizeConfidence(diff.confidence);
              var lowConf = confNorm && confNorm.numeric < 0.5;
              var diffCard = el('div', { className: 'stage-detail-card' + (lowConf ? ' card-warn' : '') });
              diffCard.appendChild(el('h4', { textContent: 'Difficulty Estimation' }));
              diffCard.appendChild(stageKvRow('Level', diff.estimated_level || '\u2014'));
              var confDisplay = confNorm ? confNorm.label : '\u2014';
              var confRow = stageKvRow('Confidence', confDisplay, { mono: true, signalKey: 'confidence', signalValue: diff.confidence, valueTip: confNorm ? confNorm.tip : '', refAnchor: 'ref-sq-difficulty' });
              diffCard.appendChild(confRow);
              diffCard.appendChild(stageKvRow('Raw Score', diff.raw_score != null && !isNaN(diff.raw_score) ? diff.raw_score.toFixed(3) : '\u2014', { mono: true }));
              outputGrid.appendChild(diffCard);
            }

            // Technique
            if (sd.technique_classification) {
              var tech = sd.technique_classification;
              var techCard = el('div', { className: 'stage-detail-card' });
              techCard.appendChild(el('h4', { textContent: 'Technique' }));
              techCard.appendChild(stageKvRow('Detectors Run', tech.detector_count != null ? String(tech.detector_count) : '\u2014', { mono: true }));
              techCard.appendChild(stageKvRow('Positive', tech.positive_count != null ? String(tech.positive_count) : '\u2014', { mono: true }));
              techCard.appendChild(stageKvRow('Tags', tech.technique_tags ? tech.technique_tags.join(', ') : '\u2014'));
              outputGrid.appendChild(techCard);
            }

            // Instinct
            if (sd.instinct_classification) {
              var inst = sd.instinct_classification;
              var instCard = el('div', { className: 'stage-detail-card' });
              instCard.appendChild(el('h4', { textContent: 'Instinct' }));
              instCard.appendChild(stageKvRow('Count', inst.instinct_count != null ? String(inst.instinct_count) : '\u2014', { mono: true }));
              instCard.appendChild(stageKvRow('Instincts', inst.instincts ? inst.instincts.join(', ') : '\u2014'));
              outputGrid.appendChild(instCard);
            }

            // Refutations
            if (sd.generate_refutations) {
              var ref = sd.generate_refutations;
              var refCard = el('div', { className: 'stage-detail-card' });
              refCard.appendChild(el('h4', { textContent: 'Refutations' }));
              refCard.appendChild(stageKvRow('Count', ref.refutation_count != null ? String(ref.refutation_count) : '\u2014', { mono: true }));
              refCard.appendChild(stageKvRow('PV Mode', ref.pv_mode || '\u2014'));
              refCard.appendChild(stageKvRow('Escalation', ref.escalation_used != null ? (ref.escalation_used ? 'Yes' : 'No') : '\u2014'));
              outputGrid.appendChild(refCard);
            }

            // Teaching (with hints embedded)
            if (sd.teaching_enrichment) {
              var teach = sd.teaching_enrichment;
              var teachCard = el('div', { className: 'stage-detail-card' });
              teachCard.appendChild(el('h4', { textContent: 'Teaching' }));
              teachCard.appendChild(stageKvRow('Hints', teach.hints_count != null ? String(teach.hints_count) : '\u2014', { mono: true }));
              teachCard.appendChild(stageKvRow('Comments', teach.teaching_comments != null ? String(teach.teaching_comments) : '\u2014', { mono: true }));
              // Expandable hints text
              var hintsText = p.hintsText && p.hintsText.length > 0 ? p.hintsText : (teach.hints_text ? teach.hints_text : null);
              if (hintsText && hintsText.length > 0) {
                var hintsToggle = el('div', { className: 'hints-toggle', textContent: '\u25B6 Show ' + hintsText.length + ' hint' + (hintsText.length !== 1 ? 's' : '') });
                var hintsList = el('ol', { className: 'hints-list hints-collapsed' });
                hintsText.forEach(function (h) {
                  var li = el('li', { className: 'hint-item' });
                  li.textContent = h;
                  hintsList.appendChild(li);
                });
                hintsToggle.addEventListener('click', function () {
                  var collapsed = hintsList.classList.toggle('hints-collapsed');
                  hintsToggle.textContent = (collapsed ? '\u25B6 Show ' : '\u25BC Hide ') + hintsText.length + ' hint' + (hintsText.length !== 1 ? 's' : '');
                });
                teachCard.appendChild(hintsToggle);
                teachCard.appendChild(hintsList);
              }
              outputGrid.appendChild(teachCard);
            }

            // SGF Transform (input → output size)
            var inputLen = sd.parse_sgf ? sd.parse_sgf.sgf_length : null;
            var outputLen = p.sgfContent.enriched ? p.sgfContent.enriched.length : null;
            if (inputLen != null || outputLen != null) {
              var sgfCard = el('div', { className: 'stage-detail-card' });
              sgfCard.appendChild(el('h4', { textContent: 'SGF Transform' }));
              sgfCard.appendChild(stageKvRow('Input', inputLen != null ? String(inputLen) + ' chars' : '\u2014', { mono: true }));
              sgfCard.appendChild(stageKvRow('Output', outputLen != null ? String(outputLen) + ' chars' : '\u2014', { mono: true }));
              if (inputLen != null && outputLen != null && inputLen > 0) {
                var inflation = ((outputLen - inputLen) / inputLen * 100).toFixed(0);
                var inflRow = stageKvRow('Inflation', '+' + inflation + '%', { mono: true });
                if (Math.abs(parseInt(inflation)) > 400) {
                  inflRow.querySelector('.stage-kv-value').classList.add('is-warn');
                }
                sgfCard.appendChild(inflRow);
              }
              outputGrid.appendChild(sgfCard);
            }

            outputGroup.appendChild(outputGrid);
            body.appendChild(outputGroup);
          }
        }

        // ── ZONE F: Phase timing bar with legend ──
        if (p.phaseTimings) {
          var total = 0;
          var segments = [];
          PIPELINE_STAGES.forEach(function (s, i) {
            var val = p.phaseTimings[s.key];
            if (val != null && val > 0) {
              total += val;
              segments.push({ key: s.label, val: val, color: PHASE_COLORS[i % PHASE_COLORS.length] });
            }
          });

          if (total > 0) {
            var barLabel = el('div', { className: 'meta-label', textContent: 'STAGE TIMING (' + formatDuration(total) + ' total)' });
            barLabel.style.marginTop = '8px';
            body.appendChild(barLabel);

            var bar = el('div', { className: 'phase-bar' });
            segments.forEach(function (seg) {
              var pct = (seg.val / total * 100).toFixed(1);
              var segEl = el('div', { className: 'phase-bar-segment' });
              segEl.style.width = Math.max(parseFloat(pct), 0.5) + '%';
              segEl.style.backgroundColor = seg.color;
              segEl.setAttribute('data-label', seg.key + ': ' + formatDuration(seg.val));
              bar.appendChild(segEl);
            });
            body.appendChild(bar);

            var legend = el('div', { className: 'phase-bar-legend' });
            segments.forEach(function (seg) {
              var item = el('span', { className: 'phase-bar-legend-item' });
              var dot = el('span', { className: 'phase-bar-legend-dot' });
              dot.style.backgroundColor = seg.color;
              item.appendChild(dot);
              var pct = (seg.val / total * 100).toFixed(1);
              item.appendChild(document.createTextNode(seg.key + ' ' + pct + '%'));
              legend.appendChild(item);
            });
            body.appendChild(legend);
          }
        }

        details.appendChild(body);
      });

      container.appendChild(details);
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // S6: Search Section (T6)
  // ═══════════════════════════════════════════════════════════════

  function renderSearch(store, container) {
    container.textContent = '';
    var title = el('h2', { className: 'section-title' }, 'Log Search');
    container.appendChild(title);

    var inputWrap = el('div', { className: 'search-input-wrapper' });
    var input = el('input', { className: 'search-input', type: 'text', placeholder: 'fail + katago_agrees | "tree_validation"' });
    inputWrap.appendChild(input);
    var countEl = el('div', { className: 'search-count' });
    inputWrap.appendChild(countEl);
    container.appendChild(inputWrap);
    var hintEl = el('div', { className: 'search-hint' });
    hintEl.textContent = 'Syntax: word = contains \u2022 a + b = AND \u2022 a | b = OR \u2022 "exact phrase" = literal';
    container.appendChild(hintEl);

    var resultsEl = el('div', { className: 'search-results' });
    container.appendChild(resultsEl);

    // Pre-index: stringify each event for search
    var indexed = store.events.map(function (ev, i) {
      return { line: i + 1, event: ev, text: JSON.stringify(ev).toLowerCase() };
    });

    var debounceTimer = null;

    // Parse query into OR-groups of AND-terms.
    // Syntax: term + term = AND, term | term = OR, "quoted phrase" = literal
    // Example: fail + katago | "tree_validation" = (fail AND katago) OR (tree_validation)
    function parseQuery(raw) {
      var orGroups = raw.split(/\s*\|\s*/);
      return orGroups.map(function (group) {
        var terms = [];
        // Extract quoted phrases first, then split remainder on +
        var remainder = group.replace(/"([^"]+)"/g, function (_, phrase) {
          terms.push(phrase.trim().toLowerCase());
          return '';
        });
        remainder.split(/\s*\+\s*/).forEach(function (t) {
          t = t.trim().toLowerCase();
          if (t) terms.push(t);
        });
        return terms;
      }).filter(function (g) { return g.length > 0; });
    }

    // Test if text matches parsed query (OR of AND groups)
    function matchesQuery(text, orGroups) {
      for (var i = 0; i < orGroups.length; i++) {
        var andTerms = orGroups[i];
        var allMatch = true;
        for (var j = 0; j < andTerms.length; j++) {
          if (text.indexOf(andTerms[j]) === -1) { allMatch = false; break; }
        }
        if (allMatch) return true;
      }
      return false;
    }

    // Collect all unique terms for highlighting
    function allTerms(orGroups) {
      var seen = {};
      var result = [];
      orGroups.forEach(function (g) {
        g.forEach(function (t) {
          if (!seen[t]) { seen[t] = true; result.push(t); }
        });
      });
      return result;
    }

    function doSearch() {
      clearTimeout(debounceTimer);
      var query = input.value.trim();
      resultsEl.textContent = '';
      if (!query) { countEl.textContent = ''; return; }

      var orGroups = parseQuery(query);
      if (orGroups.length === 0) { countEl.textContent = ''; return; }

      var matches = [];
      for (var i = 0; i < indexed.length && matches.length < MAX_SEARCH_RESULTS; i++) {
        if (matchesQuery(indexed[i].text, orGroups)) {
          matches.push(indexed[i]);
        }
      }

      var totalMatches = 0;
      for (var j = 0; j < indexed.length; j++) {
        if (matchesQuery(indexed[j].text, orGroups)) totalMatches++;
      }

      countEl.textContent = 'Showing ' + matches.length + ' of ' + totalMatches + ' matches';

      // Build highlight regex from all unique terms
      var terms = allTerms(orGroups);
      var hlParts = terms.map(function (t) { return escapeHtml(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
      var hlRe = hlParts.length > 0 ? new RegExp('(' + hlParts.join('|') + ')', 'gi') : null;

      matches.forEach(function (m) {
        var item = el('div', { className: 'search-result-item' });
        var lineSpan = el('span', { className: 'search-result-line' });
        lineSpan.textContent = 'L' + m.line;
        item.appendChild(lineSpan);

        // Highlight all matched terms in display text
        var displayText = JSON.stringify(m.event);
        var safeDisplay = escapeHtml(displayText);
        // Use innerHTML only with fully escaped content + safe markup
        var span = el('span');
        span.innerHTML = hlRe ? safeDisplay.replace(hlRe, '<span class="search-highlight">$1</span>') : safeDisplay;
        item.appendChild(span);

        // Click to expand puzzle
        var traceId = m.event.trace_id;
        if (traceId) {
          item.style.cursor = 'pointer';
          item.addEventListener('click', function () {
            var puzzleEl = document.getElementById('puzzle-' + traceId);
            if (puzzleEl) {
              puzzleEl.open = true;
              puzzleEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
        }

        resultsEl.appendChild(item);
      });
    }

    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doSearch, SEARCH_DEBOUNCE_MS);
    });

    // Expose trigger for pipeline stage clicks
    triggerSearch = function (query) {
      input.value = query;
      doSearch();
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // S7: Reference Section (T8)
  // ═══════════════════════════════════════════════════════════════

  function renderReference(container) {
    container.textContent = '';

    // Wrap in collapsible details
    var details = document.createElement('details');
    details.className = 'ref-details';
    var summary = document.createElement('summary');
    summary.className = 'section-title ref-summary';
    summary.textContent = 'Reference';
    details.appendChild(summary);

    // Tab navigation
    var tabNav = el('div', { className: 'ref-tabs-nav' });

    var tabs = [
      { key: 'status', label: 'Status' },
      { key: 'tiers', label: 'Tiers' },
      { key: 'pipeline', label: 'Pipeline Stages' },
      { key: 'metrics', label: 'Metrics' },
      { key: 'signal-quality', label: 'Signal Quality' },
      { key: 'flags', label: 'Flags' },
      { key: 'jsonl', label: 'JSONL Format' }
    ];

    var panels = {};

    tabs.forEach(function (tab, i) {
      var btn = el('button', { className: 'ref-tab-btn' + (i === 0 ? ' active' : ''), 'data-tab': tab.key });
      btn.textContent = tab.label;
      btn.addEventListener('click', function () {
        tabNav.querySelectorAll('.ref-tab-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        Object.keys(panels).forEach(function (k) { panels[k].classList.remove('active'); });
        panels[tab.key].classList.add('active');
      });
      tabNav.appendChild(btn);

      var panel = el('div', { className: 'ref-tab-panel' + (i === 0 ? ' active' : ''), 'data-tab-panel': tab.key });
      panels[tab.key] = panel;
    });

    details.appendChild(tabNav);

    // Reference search filter
    var refSearchWrap = el('div', { className: 'ref-search-wrapper' });
    var refSearchInput = el('input', {
      className: 'ref-search-input',
      type: 'text',
      placeholder: 'Filter reference terms\u2026'
    });
    refSearchWrap.appendChild(refSearchInput);
    details.appendChild(refSearchWrap);

    refSearchInput.addEventListener('input', function () {
      var query = refSearchInput.value.trim().toLowerCase();
      // Filter across ALL panels (show matching terms, switch to tab with results)
      var anyVisible = {};
      tabs.forEach(function (tab) { anyVisible[tab.key] = false; });

      tabs.forEach(function (tab) {
        var terms = panels[tab.key].querySelectorAll('.ref-term');
        terms.forEach(function (term) {
          var text = (term.textContent || '').toLowerCase();
          var match = !query || text.indexOf(query) !== -1;
          if (match) {
            term.classList.remove('ref-hidden');
            anyVisible[tab.key] = true;
          } else {
            term.classList.add('ref-hidden');
          }
        });
      });

      // If active tab has no results, switch to first tab with results
      if (query) {
        var activeTab = tabNav.querySelector('.ref-tab-btn.active');
        var activeKey = activeTab ? activeTab.getAttribute('data-tab') : '';
        if (!anyVisible[activeKey]) {
          for (var i = 0; i < tabs.length; i++) {
            if (anyVisible[tabs[i].key]) {
              tabNav.querySelectorAll('.ref-tab-btn').forEach(function (b) { b.classList.remove('active'); });
              tabNav.querySelector('[data-tab="' + tabs[i].key + '"]').classList.add('active');
              Object.keys(panels).forEach(function (k) { panels[k].classList.remove('active'); });
              panels[tabs[i].key].classList.add('active');
              break;
            }
          }
        }
      }
    });

    // Status panel
    var statusGroup = el('div', { className: 'ref-group' });
    [
      { id: 'ref-accepted', term: 'Accepted', def: 'Puzzle passed all quality gates. Ready for publication.' },
      { id: 'ref-flagged', term: 'Flagged', def: 'KataGo disagrees with the expected answer or quality is borderline. Needs human review.' },
      { id: 'ref-rejected', term: 'Rejected', def: 'Puzzle failed validation (high delta_wr, no solution tree, ambiguous answer).' },
      { id: 'ref-error', term: 'Error', def: 'Pipeline error prevented analysis (SGF parse failure, engine timeout, etc.).' }
    ].forEach(function (t) {
      var dl = el('dl', { className: 'ref-term', id: t.id });
      var dt = el('dt'); dt.textContent = t.term; dl.appendChild(dt);
      var dd = el('dd'); dd.textContent = t.def; dl.appendChild(dd);
      statusGroup.appendChild(dl);
    });
    panels.status.appendChild(statusGroup);

    // Tiers panel — progression strip + accented cards
    (function buildTiersPanel() {
      // Horizontal progression strip showing 4 tiers
      var strip = el('div', { className: 'ref-tier-strip' });
      [0, 1, 2, 3].forEach(function (t) {
        var desc = TIER_DESCRIPTIONS[t];
        var cell = el('div', { className: 'ref-tier-strip-cell ref-tier-strip-cell-' + t });
        cell.appendChild(el('span', { className: 'ref-tier-strip-num', textContent: t === 0 ? '?' : String(t) }));
        cell.appendChild(el('span', { className: 'ref-tier-strip-label', textContent: desc.badge }));
        strip.appendChild(cell);
      });
      panels.tiers.appendChild(strip);

      // Tier description cards with left-border accent
      [0, 1, 2, 3].forEach(function (t) {
        var desc = TIER_DESCRIPTIONS[t];
        var card = el('div', { className: 'ref-tier-card ref-tier-card-' + t, id: 'ref-tier-' + t });
        var title = el('div', { className: 'ref-tier-card-title' });
        title.appendChild(el('span', { className: TIER_BADGE_CLASSES[t], textContent: desc.badge }));
        title.appendChild(document.createTextNode(' ' + desc.label));
        card.appendChild(title);
        card.appendChild(el('div', { className: 'ref-tier-card-desc', textContent: desc.description }));
        card.appendChild(el('div', { className: 'ref-tier-card-example', textContent: [
          'No enrichment data — raw import only.',
          'Stones parsed, basic structure validated. No KataGo analysis.',
          'KataGo position analysis + move validation. Missing refutations/hints.',
          'Complete: refutations, difficulty, techniques, hints, teaching comments.'
        ][t] }));
        panels.tiers.appendChild(card);
      });
    })();

    // Pipeline panel
    var pipeGroup = el('div', { className: 'ref-group' });
    var stageTerms = [
      { id: 'ref-parse', term: 'Parse', def: 'Extract SGF tree, board position, and metadata from the input file.' },
      { id: 'ref-solve-path', term: 'Solve-Path', def: 'Choose the analysis path: position-only, has-solution, or standard (with move tree).' },
      { id: 'ref-analyze', term: 'Analyze', def: 'Send position to KataGo engine and collect win-rate/policy analysis.' },
      { id: 'ref-validate', term: 'Validate', def: 'Verify the correct move exists and aligns with SGF solution tree.' },
      { id: 'ref-refutation', term: 'Refutation', def: 'Generate wrong-move branches to show why other first moves fail.' },
      { id: 'ref-difficulty', term: 'Difficulty', def: 'Estimate puzzle difficulty from PV depth, policy score, and read complexity.' },
      { id: 'ref-assembly', term: 'Assembly', def: 'Collect all analysis outputs into the final AiAnalysisResult object.' },
      { id: 'ref-technique', term: 'Technique', def: 'Run 28 technique detectors to identify tags (ladder, ko, snapback, etc.).' },
      { id: 'ref-instinct', term: 'Instinct', def: 'Classify move intent from position geometry (e.g., attack, defend, connect).' },
      { id: 'ref-teaching', term: 'Teaching', def: 'Generate progressive hints and teaching comments for the puzzle.' },
      { id: 'ref-sgf-writeback', term: 'SGF-Write', def: 'Write enrichment results (YG, YT, YH, YQ, YR, YX) back to the SGF file.' }
    ];
    stageTerms.forEach(function (t) {
      var dl = el('dl', { className: 'ref-term', id: t.id });
      var dt = el('dt'); dt.textContent = t.term; dl.appendChild(dt);
      var dd = el('dd'); dd.textContent = t.def; dl.appendChild(dd);
      pipeGroup.appendChild(dl);
    });
    panels.pipeline.appendChild(pipeGroup);

    // Metrics panel — grouped by category with h4 headers
    (function buildMetricsPanel() {
      var groups = [
        { heading: 'Engine Signals', items: [
          { id: 'ref-policy-prior', term: 'Policy Prior', def: 'Neural network\'s initial probability for a move before search. Higher = more "obvious".', sqLink: '#ref-sq-technique' },
          { id: 'ref-policy-entropy', term: 'Policy Entropy / Entropy', def: 'Measure of uncertainty in the policy distribution. High entropy = many plausible moves, low entropy = one dominant candidate.', sqLink: '#ref-sq-difficulty' },
          { id: 'ref-winrate', term: 'Winrate / Win Rate', def: 'Probability (0\u2013100%) of winning after a given move, as estimated by KataGo\'s neural network + MCTS search. Low winrate on the "correct" move triggers a flag.', sqLink: '#ref-sq-validation' },
          { id: 'ref-pv', term: 'PV (Principal Variation)', def: 'The best-move sequence KataGo computed from the current position. PV Mode: "multi_query" means multiple analysis calls are used to build the refutation tree; "single" means one call suffices.' },
          { id: 'ref-correct-move-rank', term: 'KataGo Move Rank / Correct Move Rank', def: 'Position of the SGF\'s marked correct answer in KataGo\'s ranked move list. Rank #1 means KataGo agrees it is the best move; higher ranks indicate disagreement.', sqLink: '#ref-sq-validation' },
          { id: 'ref-top-n', term: 'top_n', def: 'Number of top candidate moves evaluated by KataGo during analysis. A flag value like "top_n:20" means 20 moves were considered.' }
        ]},
        { heading: 'Difficulty Estimation', items: [
          { id: 'ref-composite-score', term: 'Composite Score / Raw Score', def: 'Weighted combination of difficulty signals used for final level assignment.', sqLink: '#ref-sq-quality' },
          { id: 'ref-solution-depth', term: 'Solution Depth', def: 'Number of moves in the correct solution sequence.' },
          { id: 'ref-confidence', term: 'Confidence', def: 'Difficulty confidence (high / medium / low). See Signal Quality tab for thresholds, measurement methodology, and comparison with other pipeline signals.', sqLink: '#ref-sq-difficulty' }
        ]},
        { heading: 'Enrichment Output', items: [
          { id: 'ref-refutation-metric', term: 'Refutation', def: 'Wrong first-move branch showing why an alternative fails. Count indicates puzzle complexity.' },
          { id: 'ref-co-correct', term: 'Co-correct', def: 'Alternative first move that also solves the puzzle (detected during validation).', sqLink: '#ref-sq-ai-solve' },
          { id: 'ref-technique-tags', term: 'Technique Tags', def: 'Go/tsumego tags detected by 28 specialized detectors (e.g., ladder, ko, snapback).', sqLink: '#ref-sq-technique' },
          { id: 'ref-sgf-inflation', term: 'SGF Inflation', def: 'Percentage increase in SGF file size after enrichment. Normal enrichment adds 50\u2013200% (YG, YT, YH, YQ properties). Over 400% may indicate a bug.' }
        ]},
        { heading: 'Session', items: [
          { id: 'ref-phase-timing', term: 'Phase Timing', def: 'Wall-clock time spent in each pipeline stage, measured in seconds.' },
          { id: 'ref-trace-id', term: 'Trace ID', def: '16-char hex identifier linking all log events for a single puzzle enrichment run.' },
          { id: 'ref-run-id', term: 'Run ID', def: 'Timestamp-based identifier for an entire enrichment CLI invocation.' }
        ]}
      ];

      groups.forEach(function (g) {
        var section = el('div', { className: 'ref-metric-section' });
        section.appendChild(el('h4', { textContent: g.heading, className: 'ref-metric-heading' }));
        g.items.forEach(function (t) {
          var dl = el('dl', { className: 'ref-term', id: t.id });
          var dt = el('dt'); dt.textContent = t.term; dl.appendChild(dt);
          var dd = el('dd');
          dd.textContent = t.def;
          if (t.sqLink) {
            dd.appendChild(document.createTextNode(' '));
            var link = el('a', { href: t.sqLink, className: 'ref-sq-xref', textContent: '\u2197 Signal Quality' });
            link.addEventListener('click', function (e) {
              e.preventDefault();
              // Switch to Signal Quality tab and scroll
              var sqBtn = container.querySelector('.ref-tab-btn[data-tab="signal-quality"]');
              if (sqBtn) sqBtn.click();
              setTimeout(function () {
                var target = container.querySelector(t.sqLink);
                if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }, 100);
            });
            dd.appendChild(link);
          }
          dl.appendChild(dd);
          section.appendChild(dl);
        });
        panels.metrics.appendChild(section);
      });
    })();

    // Flags panel — grouped by severity with colored code badges
    (function buildFlagsPanel() {
      var severities = [
        { heading: 'Hard Flags (causes rejection)', severity: 'hard', items: [
          { id: 'ref-flag-no_solution_tree', term: 'no_solution_tree', def: 'The SGF file has no branching answer sequence. The puzzle lacks a proper solution tree showing correct and incorrect variations.' },
          { id: 'ref-flag-ambiguous', term: 'ambiguous', def: 'Multiple first moves have close win-rate deltas, making it hard to distinguish the single "correct" answer. May need human review.' }
        ]},
        { heading: 'Soft Flags (flagged for review)', severity: 'soft', items: [
          { id: 'ref-flag-top_move_low_winrate', term: 'top_move_low_winrate', def: 'KataGo\'s top-ranked move has a low win-rate, suggesting the position may be ambiguous or the correct answer is unclear. The puzzle\'s marked answer may not be the engine\'s preferred move.' },
          { id: 'ref-flag-katago_disagrees', term: 'katago_disagrees', def: 'KataGo\'s top move differs from the SGF\'s marked correct move. The puzzle\'s intended answer may be incorrect or there\'s a co-correct move the engine prefers.' },
          { id: 'ref-flag-low_confidence', term: 'low_confidence', def: 'The difficulty estimation confidence is below 50%. The assigned level may not be accurate.' },
          { id: 'ref-flag-high_inflation', term: 'high_inflation', def: 'The enriched SGF is 4x+ larger than the original. May indicate duplicate moves or unbounded hint generation.' }
        ]},
        { heading: 'Parameter Flags (informational)', severity: 'param', items: [
          { id: 'ref-flag-rank', term: 'rank (flag parameter)', def: 'Position of the correct move in KataGo\'s ranked candidate list. "rank:1" means it\'s the top choice; "rank:5" means 4 other moves were preferred.' },
          { id: 'ref-flag-winrate', term: 'winrate (flag parameter)', def: 'Win-rate value associated with a flag. "winrate:0.000" means the move has ~0% win probability according to KataGo, often indicating a severe disagreement.' },
          { id: 'ref-flag-top_n', term: 'top_n (flag parameter)', def: 'Number of candidate moves considered. "top_n:20" means 20 top moves were evaluated during analysis.' },
          { id: 'ref-flag-reason', term: 'reason (flag prefix)', def: 'The "reason:" prefix identifies the specific validation rule that triggered the flag. E.g., "reason:top_move_low_winrate".' }
        ]}
      ];

      severities.forEach(function (g) {
        var section = el('div', { className: 'ref-flag-section ref-flag-section-' + g.severity });
        section.appendChild(el('h4', { textContent: g.heading, className: 'ref-flag-heading ref-flag-heading-' + g.severity }));
        g.items.forEach(function (t) {
          var dl = el('dl', { className: 'ref-term', id: t.id });
          var dt = el('dt');
          dt.appendChild(el('code', { textContent: t.term, className: 'ref-flag-code ref-flag-code-' + g.severity }));
          dl.appendChild(dt);
          var dd = el('dd'); dd.textContent = t.def; dl.appendChild(dd);
          section.appendChild(dl);
        });
        panels.flags.appendChild(section);
      });
    })();

    // JSONL Format panel
    var formatGroup = el('div', { className: 'ref-group' });
    [
      { id: 'ref-session-start', term: 'session_start', def: 'Emitted when enrichment begins for a puzzle. Contains trace_id, source_file, run_id.' },
      { id: 'ref-enrichment-begin', term: 'enrichment_begin', def: 'Marks the start of pipeline processing. Contains puzzle_id, trace_id.' },
      { id: 'ref-enrichment-complete', term: 'enrichment_complete', def: 'Contains full results: status, level, tags, phase_timings, refutations, hints_count, enrichment_tier.' },
      { id: 'ref-enrichment-end', term: 'enrichment_end', def: 'Final event per puzzle. Contains elapsed_s total duration and final status.' }
    ].forEach(function (t) {
      var dl = el('dl', { className: 'ref-term', id: t.id });
      var dt = el('dt');
      dt.appendChild(el('code', { textContent: t.term }));
      dl.appendChild(dt);
      var dd = el('dd'); dd.textContent = t.def; dl.appendChild(dd);
      formatGroup.appendChild(dl);
    });
    panels.jsonl.appendChild(formatGroup);

    // Signal Quality panel (T8b) — 6 signal types with Measures / Values / Worry-when
    (function buildSignalQualityPanel() {
      var sqPanel = panels['signal-quality'];

      // Scan hint
      var hint = el('div', { className: 'ref-sq-scan-hint' });
      hint.innerHTML = 'Start with <strong>Move Validation</strong> (gate decision) and <strong>Quality Score</strong> (composite) when investigating unexpected outcomes. Technique and Instinct scores are detector activations \u2014 rarely the root debugging target.';
      sqPanel.appendChild(hint);

      // Helper to build a threshold strip for float scores
      function thresholdStrip() {
        var strip = el('div', { className: 'ref-sq-threshold-strip' });
        strip.appendChild(el('div', { className: 'zone-weak' }));
        strip.appendChild(el('div', { className: 'zone-medium' }));
        strip.appendChild(el('div', { className: 'zone-strong' }));
        var labels = el('div', { className: 'ref-sq-threshold-labels' });
        labels.appendChild(el('span', { textContent: '0.0 (weak)' }));
        labels.appendChild(el('span', { textContent: '0.35' }));
        labels.appendChild(el('span', { textContent: '0.65' }));
        labels.appendChild(el('span', { textContent: '1.0 (strong)' }));
        var wrap = document.createDocumentFragment();
        wrap.appendChild(strip);
        wrap.appendChild(labels);
        return wrap;
      }

      // Helper to build value badges
      function valueBadges(items) {
        var container = el('div', { className: 'ref-sq-value-badges' });
        items.forEach(function (item) {
          var badge = el('span', { className: 'ref-sq-vb ref-sq-vb-' + item.color, textContent: item.text });
          if (item.title) badge.title = item.title;
          container.appendChild(badge);
        });
        return container;
      }

      // Helper to build a signal quality card
      function sqCard(opts) {
        var card = el('div', { className: 'ref-sq-card ref-term', id: opts.id });
        // Header
        var header = el('div', { className: 'ref-sq-card-header' });
        var titleEl = el('span', { className: 'ref-sq-card-title' });
        titleEl.appendChild(el('span', { className: 'ref-sq-card-number', textContent: '#' + opts.number }));
        titleEl.appendChild(document.createTextNode(opts.title));
        header.appendChild(titleEl);
        header.appendChild(el('span', { className: 'ref-sq-type-badge', textContent: opts.typeBadge }));
        card.appendChild(header);
        // Measures row
        var measuresRow = el('div', { className: 'ref-sq-row' });
        measuresRow.appendChild(el('span', { className: 'ref-sq-row-label', textContent: 'Measures' }));
        var measVal = el('span', { className: 'ref-sq-row-value' });
        if (typeof opts.measures === 'string') { measVal.textContent = opts.measures; }
        else { measVal.appendChild(opts.measures); }
        measuresRow.appendChild(measVal);
        card.appendChild(measuresRow);
        // Values row
        var valuesRow = el('div', { className: 'ref-sq-row' });
        valuesRow.appendChild(el('span', { className: 'ref-sq-row-label', textContent: 'Values' }));
        var valVal = el('span', { className: 'ref-sq-row-value' });
        if (typeof opts.values === 'string') { valVal.textContent = opts.values; }
        else { valVal.appendChild(opts.values); }
        valuesRow.appendChild(valVal);
        card.appendChild(valuesRow);
        // Worry row
        var worryRow = el('div', { className: 'ref-sq-row ref-sq-worry' });
        worryRow.appendChild(el('span', { className: 'ref-sq-row-label', textContent: '\u26A0 Worry' }));
        var worryVal = el('span', { className: 'ref-sq-row-value' });
        worryVal.textContent = opts.worry;
        worryRow.appendChild(worryVal);
        card.appendChild(worryRow);
        return card;
      }

      // Card 1: Move Validation
      sqPanel.appendChild(sqCard({
        id: 'ref-sq-validation',
        number: 1,
        title: 'Move Validation',
        typeBadge: 'gate decision',
        measures: 'SGF\u2019s marked correct move compared against KataGo engine\u2019s ranked move list. Also confirms goal (kill/live) via goal_confidence.',
        values: valueBadges([
          { text: 'ACCEPTED', color: 'green', title: 'KataGo agrees with the correct move' },
          { text: 'FLAGGED', color: 'amber', title: 'KataGo disagrees or quality is borderline' },
          { text: 'REJECTED', color: 'red', title: 'Puzzle failed validation' }
        ]),
        worry: 'FLAGGED \u2192 correct move needs human review; KataGo may prefer a different first move. REJECTED \u2192 puzzle excluded from publication. goal_confidence=low \u2192 kill/live classification may be wrong.'
      }));

      // Card 2: Quality Score
      sqPanel.appendChild(sqCard({
        id: 'ref-sq-quality',
        number: 2,
        title: 'Quality Score (qk)',
        typeBadge: 'composite 0\u20135',
        measures: 'Multi-signal weighted composite: move validation result + difficulty confidence + technique detector coverage + enrichment completeness (ac_level).',
        values: valueBadges([
          { text: '5', color: 'green', title: 'Excellent \u2014 all signals agree' },
          { text: '4', color: 'green', title: 'Good \u2014 minor signal gaps' },
          { text: '3', color: 'blue', title: 'Acceptable \u2014 some concerns' },
          { text: '2', color: 'amber', title: 'Low \u2014 multiple weak signals' },
          { text: '1', color: 'amber', title: 'Poor \u2014 significant issues' },
          { text: '0', color: 'red', title: 'Failed \u2014 unusable' }
        ]),
        worry: 'Score \u2264 2 \u2192 puzzle likely has validation issues or missing enrichment data. Score 0 typically means the pipeline errored before completing analysis.'
      }));

      // Card 3: Difficulty Estimation
      sqPanel.appendChild(sqCard({
        id: 'ref-sq-difficulty',
        number: 3,
        title: 'Difficulty Estimation',
        typeBadge: 'string confidence',
        measures: 'Composite model combining policy entropy (how many plausible moves exist), correct move rank in KataGo\u2019s list, and principal variation depth.',
        values: valueBadges([
          { text: 'high', color: 'green', title: 'KataGo agrees with the correct move (top-ranked)' },
          { text: 'medium', color: 'amber', title: 'KataGo agrees but solution depth is 0 (single-move puzzle)' },
          { text: 'low', color: 'red', title: 'KataGo\u2019s top move differs from the puzzle\u2019s correct move' }
        ]),
        worry: 'low confidence \u2192 the assigned difficulty level may be wrong. Often means the puzzle is too obvious for its assigned rank (e.g., labeled "intermediate" but correct move is rank #1 with low entropy), or KataGo disagrees with the answer entirely.'
      }));

      // Card 4: AI Solve Quality
      var aiSolveValuesFragment = document.createDocumentFragment();
      var aiSolveBadges = valueBadges([
        { text: 'TE', color: 'green', title: 'Top Engine \u2014 the move KataGo considers best' },
        { text: 'NEUTRAL', color: 'blue', title: 'Acceptable move \u2014 not best, not bad' },
        { text: 'BM', color: 'amber', title: 'Bad Move \u2014 engine prefers a different answer' },
        { text: 'BM_HO', color: 'red', title: 'Clear blunder \u2014 may be a broken puzzle' }
      ]);
      aiSolveValuesFragment.appendChild(aiSolveBadges);
      var aiSolveGloss = el('div', { className: 'ref-sq-row-value' });
      aiSolveGloss.style.fontSize = '11px';
      aiSolveGloss.style.marginTop = '4px';
      aiSolveGloss.style.color = 'var(--text-muted)';
      aiSolveGloss.innerHTML = '<strong>TE</strong> = Top Engine move (KataGo agrees strongly) &middot; <strong>NEUTRAL</strong> = acceptable alternative &middot; <strong>BM</strong> = Bad Move (engine prefers another answer) &middot; <strong>BM_HO</strong> = clear blunder (likely a broken puzzle)';
      aiSolveValuesFragment.appendChild(aiSolveGloss);

      sqPanel.appendChild(sqCard({
        id: 'ref-sq-ai-solve',
        number: 4,
        title: 'AI Solve Quality',
        typeBadge: 'delta-based enum',
        measures: 'KataGo winrate delta between the best engine move and the puzzle\u2019s marked correct move. Larger delta = bigger disagreement.',
        values: aiSolveValuesFragment,
        worry: 'BM \u2192 KataGo considers the intended answer a bad move; check if there\u2019s a co-correct move. BM_HO \u2192 the puzzle\u2019s correct move is likely wrong \u2014 may be a source data error, not a real tesuji.'
      }));

      // Card 5: Technique Detection
      var techValuesFragment = document.createDocumentFragment();
      techValuesFragment.appendChild(document.createTextNode('Per-detector activation score (28 detectors: ladder, ko, snapback, connect, etc.)'));
      techValuesFragment.appendChild(thresholdStrip());

      sqPanel.appendChild(sqCard({
        id: 'ref-sq-technique',
        number: 5,
        title: 'Technique Detection',
        typeBadge: 'float 0.0\u20131.0',
        measures: '28 pattern detectors run on position geometry. Each detector checks for a specific Go technique (ladder, ko, snapback, net, etc.) and outputs an activation score.',
        values: techValuesFragment,
        worry: 'Score < 0.35 \u2192 detector did not fire (technique not present). All detectors below 0.35 \u2192 technique tags are unreliable; puzzle may be mis-tagged.'
      }));

      // Card 6: Instinct Classification
      var instValuesFragment = document.createDocumentFragment();
      instValuesFragment.appendChild(document.createTextNode('Per-instinct classification score (attack, defend, connect, cut, etc.)'));
      instValuesFragment.appendChild(thresholdStrip());

      sqPanel.appendChild(sqCard({
        id: 'ref-sq-instinct',
        number: 6,
        title: 'Instinct Classification',
        typeBadge: 'float 0.0\u20131.0',
        measures: 'Position feature extractors classify the move\u2019s strategic intent from board geometry. Identifies categories like attack, defend, connect, kill, live.',
        values: instValuesFragment,
        worry: 'Score < 0.35 \u2192 classification is weak for that instinct. All instincts below 0.35 \u2192 no clear strategic intent detected; puzzle may have unusual shape.'
      }));
    })();

    // Append panels to details
    tabs.forEach(function (tab) {
      details.appendChild(panels[tab.key]);
    });

    container.appendChild(details);
  }

  // ═══════════════════════════════════════════════════════════════
  // Dashboard Orchestrator (T10)
  // ═══════════════════════════════════════════════════════════════

  function renderDashboard(store) {
    destroyCharts();

    var dashboard = document.getElementById('dashboard');
    dashboard.classList.remove('hidden');

    var nav = document.getElementById('section-nav');
    nav.classList.remove('hidden');

    renderHeader(store, document.getElementById('s1-header'));
    renderSummary(store, document.getElementById('s2-summary'));
    renderTiming(store, document.getElementById('s3-timing'));
    renderPipelineJourney(store, document.getElementById('s4-pipeline'));
    renderPuzzleDetails(store, document.getElementById('s5-details'));
    renderSearch(store, document.getElementById('s6-search'));
    renderReference(document.getElementById('s7-reference'));
  }

  // ═══════════════════════════════════════════════════════════════
  // File Handling (T2 + T10)
  // ═══════════════════════════════════════════════════════════════

  function handleFileContent(text, fileName) {
    var errorBanner = document.getElementById('error-banner');
    errorBanner.classList.add('hidden');

    try {
      var events = parseJSONL(text);
      if (events.length === 0) {
        showError('No valid JSON lines found in the file. Ensure the file contains one JSON object per line.');
        return;
      }
      var store = buildEventStore(events, fileName);
      addToHistory(fileName, text, store.stats);
      collapseDropZone(fileName);
      renderDashboard(store);
      renderSidebar(fileName);
    } catch (e) {
      showError('Failed to parse log file: ' + e.message);
    }
  }

  function showError(message) {
    var errorBanner = document.getElementById('error-banner');
    errorBanner.textContent = message;
    errorBanner.classList.remove('hidden');
  }

  function collapseDropZone(fileName) {
    var dropZone = document.getElementById('drop-zone');
    dropZone.classList.add('hidden');

    var loadAnother = document.getElementById('btn-load-another');
    loadAnother.classList.remove('hidden');
  }

  function resetToDropZone() {
    destroyCharts();
    document.getElementById('drop-zone').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('section-nav').classList.add('hidden');
    document.getElementById('btn-load-another').classList.add('hidden');
    document.getElementById('error-banner').classList.add('hidden');
  }

  function initDropZone() {
    var dropZone = document.getElementById('drop-zone');
    var fileInput = document.getElementById('file-input');
    var btnBrowse = document.getElementById('btn-browse');
    var btnSample = document.getElementById('btn-sample');
    var btnLoadAnother = document.getElementById('btn-load-another');
    var btnScrollTop = document.getElementById('btn-scroll-top');

    // Drag and drop
    dropZone.addEventListener('dragover', function (e) {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    dropZone.addEventListener('dragleave', function () {
      dropZone.classList.remove('drag-over');
    });
    dropZone.addEventListener('drop', function (e) {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      var files = e.dataTransfer.files;
      if (files.length > 0) {
        readFile(files[0]);
      }
    });

    // Browse button
    btnBrowse.addEventListener('click', function () {
      fileInput.click();
    });
    fileInput.addEventListener('change', function () {
      if (fileInput.files.length > 0) {
        readFile(fileInput.files[0]);
        fileInput.value = '';
      }
    });

    // Load sample
    btnSample.addEventListener('click', function () {
      handleFileContent(SAMPLE_JSONL, 'sample.jsonl (built-in demo)');
    });

    // Load another
    btnLoadAnother.addEventListener('click', function () {
      resetToDropZone();
    });

    // Scroll to top
    btnScrollTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  function readFile(file) {
    var reader = new FileReader();
    reader.onload = function (e) {
      handleFileContent(e.target.result, file.name);
    };
    reader.onerror = function () {
      showError('Failed to read file: ' + file.name);
    };
    reader.readAsText(file);
  }

  // ═══════════════════════════════════════════════════════════════
  // Theme Toggle
  // ═══════════════════════════════════════════════════════════════

  var THEME_KEY = 'enrichment-log-viewer-theme';

  function getPreferredTheme() {
    try {
      var saved = localStorage.getItem(THEME_KEY);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (e) { /* ignore */ }
    // Fall back to system preference
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    var btn = document.getElementById('btn-theme-toggle');
    if (btn) {
      btn.textContent = theme === 'dark' ? '\u2600' : '\u263D'; // sun or moon
      btn.title = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
    }
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    var next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* quota */ }
    // Re-render charts if dashboard is visible
    destroyCharts();
    var dashboard = document.getElementById('dashboard');
    if (dashboard && !dashboard.classList.contains('hidden')) {
      // Charts need to be recreated with new colors — handled on next load
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // Initialization
  // ═══════════════════════════════════════════════════════════════

  document.addEventListener('DOMContentLoaded', function () {
    // Apply theme before anything renders
    applyTheme(getPreferredTheme());

    initDropZone();
    renderSidebar(null);

    // Theme toggle
    var btnTheme = document.getElementById('btn-theme-toggle');
    if (btnTheme) {
      btnTheme.addEventListener('click', toggleTheme);
    }

    // Clear history button
    var btnClear = document.getElementById('btn-clear-history');
    if (btnClear) {
      btnClear.addEventListener('click', function () {
        clearHistory();
        renderSidebar(null);
      });
    }
  });

})();
