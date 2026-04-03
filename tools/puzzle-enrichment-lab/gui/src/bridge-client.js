/**
 * bridge-client.js — HTTP + SSE client for bridge.py API.
 *
 * analyzePython()      → POST /api/analyze → AnalysisResult
 * streamEnrichment()   → POST /api/enrich  → async generator of SSE events
 * cancelEnrichment()   → POST /api/cancel
 * getHealth()          → GET  /api/health
 */

let currentAbort = null;

/**
 * Send a position to KataGo for analysis via the bridge.
 * Cancel-previous pattern: aborts any in-flight analysis request.
 */
export async function analyzePython(board, currentPlayer, options = {}) {
  if (currentAbort) currentAbort.abort();
  const abort = new AbortController();
  currentAbort = abort;

  const body = {
    board,
    currentPlayer,
    komi: options.komi ?? 0.0,
    rules: options.rules ?? 'chinese',
    visits: options.visits ?? 200,
    includeMovesOwnership: false,
    ownershipMode: 'root',
  };

  try {
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: abort.signal,
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`Analysis failed (${resp.status}): ${text}`);
    }
    return await resp.json();
  } finally {
    if (currentAbort === abort) currentAbort = null;
  }
}

/**
 * Start enrichment pipeline via SSE. Yields { event, data } objects.
 * @param {string} sgfText - Raw SGF string
 * @param {AbortSignal} [signal] - Optional abort signal
 */
export async function* streamEnrichment(sgfText, signal, configOverrides) {
  const body = { sgf: sgfText };
  if (configOverrides && Object.keys(configOverrides).length > 0) {
    body.config_overrides = configOverrides;
  }
  const resp = await fetch('/api/enrich', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`Enrich failed (${resp.status}): ${text}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse SSE frames: "event: <name>\ndata: <json>\n\n"
    const frames = buffer.split('\n\n');
    buffer = frames.pop(); // keep incomplete frame

    for (const frame of frames) {
      if (!frame.trim()) continue;
      let eventName = 'message';
      let dataStr = '';
      for (const line of frame.split('\n')) {
        if (line.startsWith('event: ')) eventName = line.slice(7).trim();
        else if (line.startsWith('data: ')) dataStr = line.slice(6);
      }
      if (eventName === 'heartbeat') continue;
      try {
        yield { event: eventName, data: JSON.parse(dataStr) };
      } catch {
        yield { event: eventName, data: dataStr };
      }
    }
  }
}

/** Cancel any running enrichment. */
export async function cancelEnrichment() {
  try {
    await fetch('/api/cancel', { method: 'POST' });
  } catch { /* ignore */ }
}

/** Fetch current config defaults from server. */
export async function getConfig() {
  const resp = await fetch('/api/config');
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`Config fetch failed (${resp.status}): ${text}`);
  }
  return await resp.json();
}

/** Check engine health. */
export async function getHealth() {
  try {
    const resp = await fetch('/api/health');
    return await resp.json();
  } catch {
    return { status: 'unreachable' };
  }
}
