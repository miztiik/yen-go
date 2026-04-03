/**
 * Puzzle Enrichment Lab — Main Application Controller
 * 
 * Orchestrates the UI: source SGF input, BesoGo viewers (source + enriched),
 * engine selection (local KataGo), analysis, and result display.
 */
(function() {
    'use strict';

    // ── State ──
    var state = {
        sourceEditor: null,      // BesoGo editor for source SGF
        resultEditor: null,      // BesoGo editor for enriched SGF
        abortController: null,   // For cancelling in-flight requests
        lastResult: null,        // Last analysis result
        isAnalyzing: false
    };

    // ── DOM References ──
    var dom = {};

    // ── Sample SGF for testing ──
    var SAMPLE_SGF = '(;FF[4]GM[1]SZ[19]PL[B]' +
        'AB[cp][dp][ep][fp][cq][eq][cr][er][cs][ds]' +
        'AW[gp][dq][fq][gq][dr][fr][gr][es][fs]' +
        'C[Black to play and live. Find the vital point.]' +
        ';B[ds]C[Correct! D1 is the vital point - it creates two eyes for the black group.]' +
        '(;W[es]C[White tries to reduce eye space but Black is already alive with two eyes.])' +
        ')';

    // ── Initialization ──
    document.addEventListener('DOMContentLoaded', function() {
        cacheDomReferences();
        bindEvents();
        initViewers();
        updateAnalyzeButton();
    });

    function cacheDomReferences() {
        dom.sgfInput = document.getElementById('sgf-input');
        dom.sgfOutput = document.getElementById('sgf-output');
        dom.sourceViewer = document.getElementById('source-viewer');
        dom.resultViewer = document.getElementById('result-viewer');
        // Local engine
        dom.btnAnalyze = document.getElementById('btn-analyze');
        dom.btnStop = document.getElementById('btn-stop');
        dom.btnHealth = document.getElementById('btn-health');
        dom.btnStartEngine = document.getElementById('btn-start-engine');
        dom.btnStopEngine = document.getElementById('btn-stop-engine');
        dom.modelSelect = document.getElementById('model-select');
        dom.localEngineControls = document.getElementById('local-engine-controls');
        dom.bridgeUrl = document.getElementById('bridge-url');
        dom.maxVisits = document.getElementById('max-visits');
        dom.localStatusDot = document.getElementById('local-status-dot');
        dom.localStatusText = document.getElementById('local-status-text');
        // Shared
        dom.btnLoadSample = document.getElementById('btn-load-sample');
        dom.btnClearSource = document.getElementById('btn-clear-source');
        dom.btnCopyEnriched = document.getElementById('btn-copy-enriched');
        dom.btnDownloadEnriched = document.getElementById('btn-download-enriched');
        dom.maxRefutations = document.getElementById('max-refutations');
        dom.minPolicy = document.getElementById('min-policy');
        dom.statusDot = document.getElementById('status-dot');
        dom.statusText = document.getElementById('status-text');
        dom.progressArea = document.getElementById('progress-area');
        dom.progressFill = document.getElementById('progress-fill');
        dom.progressText = document.getElementById('progress-text');
        dom.resultsSummary = document.getElementById('results-summary');
        dom.validationIcon = document.getElementById('validation-icon');
        dom.validationBody = document.getElementById('validation-body');
        dom.refutationsBody = document.getElementById('refutations-body');
        dom.difficultyBody = document.getElementById('difficulty-body');
    }

    function bindEvents() {
        dom.sgfInput.addEventListener('input', function() {
            updateAnalyzeButton();
            loadSourceSgf();
        });
        dom.sgfOutput.addEventListener('input', function() {
            loadResultSgfFromTextarea();
        });
        // Local engine buttons
        dom.btnAnalyze.addEventListener('click', function() { runLocalAnalysis(dom.sgfInput.value.trim()); });
        dom.btnStop.addEventListener('click', stopAnalysis);
        dom.btnHealth.addEventListener('click', checkLocalHealth);
        dom.btnStartEngine.addEventListener('click', startEngine);
        dom.btnStopEngine.addEventListener('click', stopEngine);
        // Common
        dom.btnLoadSample.addEventListener('click', loadSample);
        dom.btnClearSource.addEventListener('click', clearSource);
        dom.btnCopyEnriched.addEventListener('click', copyEnriched);
        dom.btnDownloadEnriched.addEventListener('click', downloadEnriched);

        // Load model list on startup
        loadModelList();
    }

    // ── Engine Control ──
    async function loadModelList() {
        try {
            var response = await fetch(dom.bridgeUrl.value + '/models');
            if (!response.ok) throw new Error('Failed to fetch models');
            var data = await response.json();
            dom.modelSelect.innerHTML = '';

            if (data.models.length === 0) {
                var opt = document.createElement('option');
                opt.value = '';
                opt.textContent = 'No models found in models-data/';
                dom.modelSelect.appendChild(opt);
                return;
            }

            data.models.forEach(function(m) {
                var opt = document.createElement('option');
                opt.value = m.path;
                opt.textContent = m.filename + ' (' + m.size_mb + ' MB)' + (m.active ? ' [active]' : '');
                if (m.active) opt.selected = true;
                dom.modelSelect.appendChild(opt);
            });
        } catch (e) {
            dom.modelSelect.innerHTML = '<option value="">Bridge not running</option>';
        }
    }

    async function startEngine() {
        var modelPath = dom.modelSelect.value;
        if (!modelPath) {
            setStatus('offline', 'No model selected');
            return;
        }

        dom.btnStartEngine.disabled = true;
        setStatus('connecting', 'Starting engine...');
        showProgress('Starting KataGo with ' + modelPath.split('/').pop() + '...');

        try {
            var response = await fetch(dom.bridgeUrl.value + '/engine/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_path: modelPath })
            });
            var data = await response.json();

            if (response.ok) {
                setStatus('online', data.model || 'Engine started');
                updateProgress(100, 'Engine started: ' + (data.model || modelPath));
                dom.btnStartEngine.disabled = false;
                dom.btnStopEngine.disabled = false;
                loadModelList();  // refresh active marker
            } else {
                setStatus('offline', data.detail || 'Start failed');
                updateProgress(0, data.detail || 'Start failed');
                dom.btnStartEngine.disabled = false;
            }
        } catch (e) {
            setStatus('offline', 'Bridge not running: ' + e.message);
            updateProgress(0, 'Could not connect to bridge server');
            dom.btnStartEngine.disabled = false;
        }
    }

    async function stopEngine() {
        dom.btnStopEngine.disabled = true;
        setStatus('connecting', 'Stopping engine...');

        try {
            var response = await fetch(dom.bridgeUrl.value + '/engine/stop', { method: 'POST' });
            var data = await response.json();
            setStatus('offline', 'Engine stopped');
            updateProgress(0, 'Engine stopped');
            dom.btnStopEngine.disabled = true;
            loadModelList();
        } catch (e) {
            setStatus('offline', 'Error: ' + e.message);
        }
    }

    // ── BesoGo Viewer Setup ──
    function initViewers() {
        // Source viewer: board + control + tool + tree + comment
        besogo.create(dom.sourceViewer, {
            panels: 'control+tool+comment+tree',
            tool: 'auto',
            coord: 'western',
            resize: 'fill'
        });
        state.sourceEditor = dom.sourceViewer.besogoEditor;

        // Result viewer: board + control + tool + tree + comment
        besogo.create(dom.resultViewer, {
            panels: 'control+tool+comment+tree',
            tool: 'auto',
            coord: 'western',
            resize: 'fill'
        });
        state.resultEditor = dom.resultViewer.besogoEditor;
    }

    function loadSourceSgf() {
        var sgfText = dom.sgfInput.value.trim();
        if (!sgfText) return;
        try {
            var parsed = besogo.parseSgf(sgfText);
            besogo.loadSgf(parsed, state.sourceEditor);
        } catch (e) {
            console.warn('SGF parse error:', e.message);
        }
    }

    function loadResultSgf(sgfText) {
        if (!sgfText) return;
        try {
            var parsed = besogo.parseSgf(sgfText);
            besogo.loadSgf(parsed, state.resultEditor);
            dom.btnCopyEnriched.disabled = false;
            dom.btnDownloadEnriched.disabled = false;
        } catch (e) {
            console.warn('Result SGF parse error:', e.message);
        }
    }

    function loadResultSgfFromTextarea() {
        var sgfText = dom.sgfOutput.value.trim();
        if (sgfText) {
            loadResultSgf(sgfText);
        }
    }

    // ── Button Handlers ──
    function loadSample() {
        dom.sgfInput.value = SAMPLE_SGF;
        updateAnalyzeButton();
        loadSourceSgf();
    }

    function clearSource() {
        dom.sgfInput.value = '';
        updateAnalyzeButton();
        // Reset source viewer to empty board
        state.sourceEditor.loadRoot(besogo.makeGameRoot(19, 19));
    }

    function copyEnriched() {
        var text = dom.sgfOutput.value;
        if (!text) return;
        navigator.clipboard.writeText(text)
            .then(function() { flashButton(dom.btnCopyEnriched, 'Copied!'); })
            .catch(function() { alert('Failed to copy to clipboard'); });
    }

    function downloadEnriched() {
        var text = dom.sgfOutput.value;
        if (!text) return;
        var blob = new Blob([text], { type: 'text/plain' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'enriched.sgf';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    }

    function updateAnalyzeButton() {
        var hasSgf = dom.sgfInput.value.trim().length > 0;
        dom.btnAnalyze.disabled = !hasSgf || state.isAnalyzing;
    }

    function flashButton(btn, text) {
        var original = btn.textContent;
        btn.textContent = text;
        setTimeout(function() { btn.textContent = original; }, 1500);
    }

    // ── Local Engine Health ──
    async function checkLocalHealth() {
        setLocalStatus('connecting', 'Checking...');
        try {
            var result = await KataGoClient.health(dom.bridgeUrl.value);
            if (result.status === 'ready') {
                setLocalStatus('online', result.model || 'Ready');
            } else {
                setLocalStatus('offline', result.message || 'Not running');
            }
        } catch (e) {
            var msg = e.message || '';
            if (msg.indexOf('Failed to fetch') !== -1) msg = 'Bridge not running';
            setLocalStatus('offline', msg);
        }
    }

    function setLocalStatus(state, text) {
        dom.localStatusDot.className = 'status-dot ' + state;
        dom.localStatusText.textContent = text;
    }

    function setStatus(st, text) {
        dom.statusDot.className = 'status-dot ' + st;
        dom.statusText.textContent = text;
    }

    // ── Browser Engine Init ──
    // ── Local Engine Analysis ──
    async function runLocalAnalysis(sgf) {
        if (!sgf) return;

        state.isAnalyzing = true;
        state.abortController = new AbortController();
        dom.btnAnalyze.disabled = true;
        dom.btnStop.disabled = false;
        dom.resultsSummary.classList.add('hidden');

        showProgress('Sending to local KataGo...');

        try {
            setStatus('connecting', 'Analyzing...');
            updateProgress(10, 'Connecting to engine...');

            var result = await KataGoClient.analyze(
                dom.bridgeUrl.value,
                {
                    sgf: sgf,
                    max_visits: parseInt(dom.maxVisits.value, 10),
                    max_refutations: parseInt(dom.maxRefutations.value, 10),
                    min_policy: parseFloat(dom.minPolicy.value)
                },
                state.abortController.signal
            );

            updateProgress(100, 'Complete');
            state.lastResult = result;

            // Display results
            renderValidation(result.validation);
            renderRefutations(result.refutations);
            renderDifficulty(result.difficulty);
            dom.resultsSummary.classList.remove('hidden');

            // Load enriched SGF into result viewer
            if (result.enriched_sgf) {
                dom.sgfOutput.value = result.enriched_sgf;
                loadResultSgf(result.enriched_sgf);
                dom.btnCopyEnriched.disabled = false;
                dom.btnDownloadEnriched.disabled = false;
            }

            setStatus('online', 'Analysis complete');
            setLocalStatus('online', 'Analysis complete');

        } catch (e) {
            if (e.name === 'AbortError') {
                updateProgress(0, 'Cancelled');
                setLocalStatus('offline', 'Cancelled');
            } else {
                updateProgress(0, 'Error: ' + e.message);
                setLocalStatus('offline', 'Error: ' + e.message);
                console.error('Analysis error:', e);
            }
        }

        state.isAnalyzing = false;
        state.abortController = null;
        dom.btnAnalyze.disabled = false;
        dom.btnStop.disabled = true;
        updateAnalyzeButton();
    }

    function stopAnalysis() {
        if (state.abortController) {
            state.abortController.abort();
        }
    }

    // ── Progress ──
    function showProgress(text) {
        dom.progressArea.classList.remove('hidden');
        dom.progressFill.style.width = '0%';
        dom.progressText.textContent = text || '';
    }

    function updateProgress(percent, text) {
        dom.progressFill.style.width = percent + '%';
        if (text) dom.progressText.textContent = text;
    }

    // ── Result Rendering ──
    function renderValidation(v) {
        if (!v) {
            dom.validationBody.innerHTML = '<em>No validation data</em>';
            dom.validationIcon.textContent = '?';
            return;
        }

        var icon = v.katago_agrees ? '\u2714' : '\u2718';  // ✔ or ✘
        var iconClass = v.katago_agrees ? 'correct' : 'wrong';
        dom.validationIcon.textContent = icon;
        dom.validationIcon.className = 'result-icon ' + iconClass;

        var h = KataGoClient.sgfToHuman;
        var html = '';
        html += row('Correct Move', h(v.correct_move), 'correct');
        html += row('KataGo Top Move', h(v.katago_top_move) + ' (policy ' + pct(v.katago_top_move_policy) + ')');
        html += row('Correct Move Policy', pct(v.correct_move_policy));
        html += row('Winrate After Correct', pct(v.correct_move_winrate), v.correct_move_winrate > 0.8 ? 'correct' : 'warn');
        html += row('Visits Used', v.visits_used);
        html += row('Confidence', v.confidence);
        if (v.flags && v.flags.length > 0) {
            html += row('Flags', v.flags.join(', '), 'warn');
        }
        dom.validationBody.innerHTML = html;
    }

    function renderRefutations(r) {
        if (!r || !r.refutations || r.refutations.length === 0) {
            dom.refutationsBody.innerHTML = '<em>No refutations found</em>';
            return;
        }

        var h = KataGoClient.sgfToHuman;
        var html = '';
        for (var i = 0; i < r.refutations.length; i++) {
            var ref = r.refutations[i];
            var pvStr = ref.refutation_sequence.map(function(m) { return h(m); }).join(' \u2192 ');
            html += '<div class="refutation-entry">';
            html += '<div><span class="refutation-move">' + (i + 1) + '. ' + h(ref.wrong_move) + '</span>';
            html += ' <span class="refutation-policy">(policy ' + pct(ref.wrong_move_policy) + ')</span></div>';
            html += '<div class="refutation-pv">Refutation: ' + pvStr + '</div>';
            html += '<div class="result-row"><span class="result-label">Winrate after</span>';
            html += '<span class="result-value wrong">' + pct(ref.winrate_after_wrong) + '</span></div>';
            html += '<div class="result-row"><span class="result-label">Winrate drop</span>';
            html += '<span class="result-value wrong">\u0394 ' + pct(ref.winrate_delta) + '</span></div>';
            html += '</div>';
        }
        html += '<div style="margin-top:6px;font-size:12px;color:var(--text-muted)">';
        html += 'Evaluated ' + r.total_candidates_evaluated + ' candidates (' + r.visits_per_candidate + ' visits each)';
        html += '</div>';
        dom.refutationsBody.innerHTML = html;
    }

    function renderDifficulty(d) {
        if (!d) {
            dom.difficultyBody.innerHTML = '<em>No difficulty data</em>';
            return;
        }

        var levelSlug = (d.estimated_level || 'unknown').replace(/\s+/g, '-').toLowerCase();
        var html = '';
        html += '<div style="margin-bottom:8px">';
        html += '<span class="difficulty-badge ' + levelSlug + '">' + d.estimated_level + '</span>';
        html += '</div>';
        html += row('Policy Prior', pct(d.policy_prior));
        html += row('Visits to Solve', d.visits_to_solve);
        html += row('Solution Depth', d.solution_depth + ' moves');
        html += row('Refutation Count', d.refutation_count);
        html += row('Raw Score', d.raw_difficulty_score.toFixed(1) + ' / 100');
        html += row('Confidence', d.confidence);
        dom.difficultyBody.innerHTML = html;
    }

    // ── Helpers ──
    function row(label, value, cls) {
        return '<div class="result-row">' +
            '<span class="result-label">' + label + '</span>' +
            '<span class="result-value' + (cls ? ' ' + cls : '') + '">' + value + '</span>' +
            '</div>';
    }

    function pct(val) {
        if (typeof val !== 'number') return val || '?';
        return (val * 100).toFixed(1) + '%';
    }

    // ── Browser engine helpers ──

    function _extractCorrectMoveFromSgf(sgf) {
        // Find first move after root: ;B[xy] or ;W[xy]
        var match = sgf.match(/\)\s*$/) ? null : null; // just to reset
        // Look for the first B[] or W[] after setup properties
        var parts = sgf.split(';');
        for (var i = 1; i < parts.length; i++) {
            var bMatch = parts[i].match(/^B\[([a-s]{2})\]/);
            var wMatch = parts[i].match(/^W\[([a-s]{2})\]/);
            if (bMatch) return bMatch[1];
            if (wMatch) return wMatch[1];
        }
        return null;
    }

    function _sgfToGtp(sgfCoord) {
        if (!sgfCoord || sgfCoord.length < 2) return 'pass';
        var letters = 'ABCDEFGHJKLMNOPQRST';
        var col = sgfCoord.charCodeAt(0) - 97;
        var row = sgfCoord.charCodeAt(1) - 97;
        return letters[col] + (19 - row);
    }

    function _gtpToSgf(gtpCoord) {
        if (!gtpCoord || gtpCoord.toLowerCase() === 'pass') return '';
        var letters = 'ABCDEFGHJKLMNOPQRST';
        var col = letters.indexOf(gtpCoord[0].toUpperCase());
        var row = 19 - parseInt(gtpCoord.substring(1), 10);
        if (col < 0 || isNaN(row)) return '';
        return String.fromCharCode(97 + col) + String.fromCharCode(97 + row);
    }

    function _scoreToLevel(score) {
        if (score <= 10) return 'novice';
        if (score <= 20) return 'beginner';
        if (score <= 30) return 'elementary';
        if (score <= 42) return 'intermediate';
        if (score <= 55) return 'upper-intermediate';
        if (score <= 68) return 'advanced';
        if (score <= 78) return 'low-dan';
        if (score <= 88) return 'high-dan';
        return 'expert';
    }

})();
