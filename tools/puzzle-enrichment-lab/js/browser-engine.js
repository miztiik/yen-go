/**
 * Browser KataGo Engine — WASM Integration
 *
 * Loads katago.wasm (compiled via Emscripten) and a .bin.gz model,
 * then communicates via the KataGo analysis JSON protocol over
 * emulated stdin/stdout.
 *
 * Usage:
 *   await BrowserEngine.init({ modelUrl: 'models-data/model.bin.gz' });
 *   var result = await BrowserEngine.analyze(sgf, maxVisits);
 */
(function () {
    'use strict';

    var BrowserEngine = window.BrowserEngine = {};

    // ── State ──
    var _module = null;       // Emscripten Module
    var _ready = false;
    var _loading = false;
    var _stdinBuffer = [];    // Queue of lines to feed to KataGo's stdin
    var _stdoutBuffer = '';   // Accumulated stdout output
    var _responseResolve = null; // Promise resolve for current pending response
    var _modelUrl = '';

    /**
     * Initialize the WASM engine.
     * @param {Object} options
     * @param {string} options.modelUrl - Path to .bin.gz model file
     * @param {function} [options.onProgress] - Progress callback(pct, msg)
     * @returns {Promise<Object>} { status, error }
     */
    BrowserEngine.init = async function (options) {
        options = options || {};
        if (_ready) return { status: 'ready' };
        if (_loading) return { status: 'loading' };
        _loading = true;

        var onProgress = options.onProgress || function () {};
        _modelUrl = options.modelUrl || 'models-data/g170e-b10c128-s1141046784-d204142634.bin.gz';

        try {
            // Step 1: Fetch the model file
            onProgress(10, 'Downloading model: ' + _modelUrl.split('/').pop() + '...');
            var modelResponse = await fetch(_modelUrl);
            if (!modelResponse.ok) {
                _loading = false;
                return { status: 'error', error: 'Model not found: ' + _modelUrl };
            }
            var modelData = new Uint8Array(await modelResponse.arrayBuffer());
            onProgress(40, 'Model loaded (' + (modelData.length / 1048576).toFixed(1) + 'MB)');

            // Step 2: Build a minimal analysis config
            var configText = [
                'logToStderr = false',
                'maxVisits = 200',
                'numAnalysisThreads = 1',
                'numSearchThreadsPerAnalysisThread = 1',
                'nnMaxBatchSize = 1',
                'nnCacheSizePowerOfTwo = 16',
                'nnMutexPoolSizePowerOfTwo = 12',
                'nnRandomize = true',
                'reportAnalysisWinratesAs = BLACK',
                'analysisPVLen = 10',
                'wideRootNoise = 0.01',
                'conservativePass = true',
                'ignorePreRootHistory = true',
            ].join('\n');

            // Step 3: Load the Emscripten module
            onProgress(50, 'Loading WASM engine (47MB)...');

            // The compiled katago.js uses global `Module` (not MODULARIZE mode)
            // We need to configure Module BEFORE loading the script
            window.Module = {
                noInitialRun: true,

                // Virtual filesystem: embed model and config
                preRun: [function () {
                    Module.FS.writeFile('/model.bin.gz', modelData);
                    Module.FS.writeFile('/analysis.cfg', configText);
                }],

                // Redirect stdout: accumulate and parse JSON responses
                print: function (text) {
                    _stdoutBuffer += text;
                    try {
                        var data = JSON.parse(text);
                        if (_responseResolve && data.id) {
                            _responseResolve(data);
                            _responseResolve = null;
                        }
                    } catch (e) { /* not JSON */ }
                },

                // Redirect stderr to console
                printErr: function (text) {
                    console.log('[KataGo WASM]', text);
                    // Update progress on initialization messages
                    if (text.indexOf('Loaded model') !== -1 || text.indexOf('NN eval') !== -1) {
                        onProgress(85, text.substring(0, 60));
                    }
                },

                // Locate the .wasm file
                locateFile: function (path) {
                    if (path.endsWith('.wasm')) {
                        return 'vendor/katago-wasm/katago.wasm';
                    }
                    return path;
                }
            };

            // Load the script (it will use window.Module)
            await _loadScript('vendor/katago-wasm/katago.js');

            // Wait for the module to be ready
            if (typeof Module.onRuntimeInitialized === 'undefined') {
                // Module may already be initialized
                onProgress(70, 'WASM module loaded, waiting for runtime...');
            }

            _module = Module;

            onProgress(80, 'Starting KataGo analysis mode...');

            // Run KataGo in analysis mode
            try {
                _module.callMain(['analysis', '-model', '/model.bin.gz', '-config', '/analysis.cfg']);
            } catch (e) {
                // Emscripten may throw on exit if noExitRuntime is set
                if (e.message && e.message.indexOf('unwind') === -1) {
                    console.warn('KataGo main() threw:', e.message);
                }
            }

            _ready = true;
            _loading = false;
            onProgress(100, 'Browser WASM engine ready');
            return { status: 'ready' };

        } catch (e) {
            _loading = false;
            console.error('WASM init failed:', e);
            return { status: 'error', error: e.message };
        }
    };

    /**
     * Send an analysis query and wait for response.
     * @param {string} queryJson - JSON string of KataGo analysis query
     * @param {number} [timeoutMs] - Timeout in ms (default 30000)
     * @returns {Promise<Object>} KataGo analysis response
     */
    BrowserEngine.query = function (queryJson, timeoutMs) {
        if (!_ready) {
            return Promise.reject(new Error('Engine not initialized'));
        }

        timeoutMs = timeoutMs || 30000;

        return new Promise(function (resolve, reject) {
            _responseResolve = resolve;

            // Feed the query as a line to stdin
            var line = queryJson + '\n';
            for (var i = 0; i < line.length; i++) {
                _stdinBuffer.push(line.charCodeAt(i));
            }

            // Timeout
            setTimeout(function () {
                if (_responseResolve === resolve) {
                    _responseResolve = null;
                    reject(new Error('Analysis timed out after ' + timeoutMs + 'ms'));
                }
            }, timeoutMs);
        });
    };

    /**
     * Analyze an SGF position.
     * @param {string} sgf - SGF string
     * @param {number} [maxVisits] - Max MCTS visits
     * @returns {Promise<Object>} Analysis result
     */
    BrowserEngine.analyzeFromSgf = async function (sgf, maxVisits) {
        maxVisits = maxVisits || 100;

        // Parse SGF to extract position
        var pos = _parseSgfPosition(sgf);
        if (!pos) throw new Error('Could not parse SGF');

        var query = {
            id: 'browser_' + Date.now(),
            initialStones: [],
            moves: [],
            rules: 'chinese',
            komi: 7.5,
            boardXSize: pos.boardSize,
            boardYSize: pos.boardSize,
            analyzeTurns: [0],
            maxVisits: maxVisits,
            includeOwnership: true,
            initialPlayer: pos.playerToMove
        };

        // Add stones
        var GTP = 'ABCDEFGHJKLMNOPQRST';
        pos.blackStones.forEach(function (s) {
            query.initialStones.push(['B', GTP[s[0]] + (pos.boardSize - s[1])]);
        });
        pos.whiteStones.forEach(function (s) {
            query.initialStones.push(['W', GTP[s[0]] + (pos.boardSize - s[1])]);
        });

        var response = await BrowserEngine.query(JSON.stringify(query));
        return response;
    };

    /**
     * Check engine status.
     */
    BrowserEngine.health = function () {
        return {
            engine: 'browser-wasm',
            status: _ready ? 'ready' : (_loading ? 'loading' : 'not_initialized'),
            model: _modelUrl ? _modelUrl.split('/').pop() : 'none'
        };
    };

    // ── Helpers ──

    function _parseSgfPosition(sgf) {
        if (!sgf) return null;
        var boardSize = 19;
        var szMatch = sgf.match(/SZ\[(\d+)/);
        if (szMatch) boardSize = parseInt(szMatch[1], 10);

        var playerToMove = 'B';
        var plMatch = sgf.match(/PL\[([BW])\]/);
        if (plMatch) playerToMove = plMatch[1];

        var blackStones = [], whiteStones = [];

        var abMatches = sgf.match(/AB(\[[a-s]{2}\])+/g);
        if (abMatches) {
            abMatches.forEach(function (m) {
                var coords = m.match(/\[([a-s]{2})\]/g);
                if (coords) coords.forEach(function (c) {
                    blackStones.push([c.charCodeAt(1) - 97, c.charCodeAt(2) - 97]);
                });
            });
        }

        var awMatches = sgf.match(/AW(\[[a-s]{2}\])+/g);
        if (awMatches) {
            awMatches.forEach(function (m) {
                var coords = m.match(/\[([a-s]{2})\]/g);
                if (coords) coords.forEach(function (c) {
                    whiteStones.push([c.charCodeAt(1) - 97, c.charCodeAt(2) - 97]);
                });
            });
        }

        return { boardSize: boardSize, blackStones: blackStones, whiteStones: whiteStones, playerToMove: playerToMove };
    }

    function _loadScript(url) {
        return new Promise(function (resolve, reject) {
            var s = document.createElement('script');
            s.src = url;
            s.onload = resolve;
            s.onerror = function () { reject(new Error('Failed to load: ' + url)); };
            document.head.appendChild(s);
        });
    }

})();
