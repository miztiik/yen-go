/**
 * Bridge client: replaces the TF.js in-browser KataGo engine with HTTP calls
 * to the Python FastAPI bridge server (bridge.py).
 *
 * Drop-in replacement for getKataGoEngineClient() — gameStore.ts calls
 * analyzePython() instead of client.analyze().
 */

import type {
  BoardState,
  Player,
  GameRules,
  Move,
  AnalysisResult,
  CandidateMove,
  FloatArray,
  RegionOfInterest,
} from '../types';

// ---------------------------------------------------------------------------
// Error type (replaces KataGoCanceledError)
// ---------------------------------------------------------------------------

export class BridgeCanceledError extends Error {
  readonly canceled = true;
  constructor(message = 'Analysis canceled') {
    super(message);
    this.name = 'BridgeCanceledError';
  }
}

export const isBridgeCanceledError = (err: unknown): err is BridgeCanceledError => {
  if (!err || typeof err !== 'object') return false;
  return (err as { canceled?: boolean }).canceled === true;
};

// ---------------------------------------------------------------------------
// Request / Response shapes (matches bridge.py)
// ---------------------------------------------------------------------------

interface BridgeAnalyzeRequest {
  board: BoardState;
  currentPlayer: Player;
  moveHistory: Move[];
  komi: number;
  rules?: GameRules;
  regionOfInterest?: RegionOfInterest | null;
  visits?: number;
  maxTimeMs?: number;
  topK?: number;
  analysisPvLen?: number;
  includeMovesOwnership?: boolean;
  ownershipMode?: 'none' | 'root' | 'tree';
}

interface BridgeMoveInfo {
  x: number;
  y: number;
  winRate: number;
  winRateLost: number;
  scoreLead: number;
  scoreSelfplay: number;
  scoreStdev: number;
  visits: number;
  pointsLost: number;
  relativePointsLost: number;
  order: number;
  prior: number;
  pv: string[];
  ownership?: number[];
}

interface BridgeAnalyzeResponse {
  rootWinRate: number;
  rootScoreLead: number;
  rootScoreSelfplay: number;
  rootScoreStdev: number;
  rootVisits: number;
  ownership: number[];
  ownershipStdev: number[];
  policy: number[];
  moves: BridgeMoveInfo[];
}

// In-flight abort controller for cancel-previous pattern (ADR D12)
let currentAbort: AbortController | null = null;

// ---------------------------------------------------------------------------
// Core analyze function
// ---------------------------------------------------------------------------

/**
 * Send a position to the Python bridge for KataGo analysis.
 * Returns the same AnalysisResult shape the UI expects.
 */
export async function analyzePython(args: {
  board: BoardState;
  currentPlayer: Player;
  moveHistory: Move[];
  komi: number;
  rules?: GameRules;
  regionOfInterest?: RegionOfInterest | null;
  visits?: number;
  maxTimeMs?: number;
  topK?: number;
  analysisPvLen?: number;
  includeMovesOwnership?: boolean;
  ownershipMode?: 'none' | 'root' | 'tree';
}): Promise<AnalysisResult> {
  // Cancel any in-flight request (ADR D12: cancel-previous)
  if (currentAbort) {
    currentAbort.abort();
  }
  const abort = new AbortController();
  currentAbort = abort;

  const request: BridgeAnalyzeRequest = {
    board: args.board,
    currentPlayer: args.currentPlayer,
    moveHistory: args.moveHistory,
    komi: args.komi,
    rules: args.rules,
    regionOfInterest: args.regionOfInterest,
    visits: args.visits,
    maxTimeMs: args.maxTimeMs,
    topK: args.topK,
    analysisPvLen: args.analysisPvLen,
    includeMovesOwnership: args.includeMovesOwnership,
    ownershipMode: args.ownershipMode,
  };

  let resp: Response;
  try {
    resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: abort.signal,
    });
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new BridgeCanceledError();
    }
    throw err;
  } finally {
    if (currentAbort === abort) {
      currentAbort = null;
    }
  }

  if (!resp.ok) {
    let detail = 'Unknown error';
    try {
      const body = await resp.text();
      // FastAPI returns JSON {detail: "..."} for HTTPException
      const parsed = JSON.parse(body) as { detail?: unknown };
      detail = typeof parsed.detail === 'string' ? parsed.detail : body || detail;
    } catch {
      // non-JSON body or network error from Vite proxy — keep default
    }
    throw new Error(`Bridge analyze failed (${resp.status}): ${detail}`);
  }

  const data: BridgeAnalyzeResponse = await resp.json();
  return mapBridgeResponseToAnalysisResult(data, args.board.length);
}

// ---------------------------------------------------------------------------
// Response mapping
// ---------------------------------------------------------------------------

function mapBridgeResponseToAnalysisResult(
  data: BridgeAnalyzeResponse,
  boardSize: number,
): AnalysisResult {
  const moveInfos: CandidateMove[] = data.moves.map((m, i) => ({
    move: String.fromCharCode(97 + m.x) + String.fromCharCode(97 + m.y),
    x: m.x,
    y: m.y,
    prior: m.prior,
    winrate: m.winRate,
    scoreLead: m.scoreLead,
    visits: m.visits,
    order: m.order ?? i,
    pv: m.pv,
  }));

  // Convert flat ownership array to 1D for AnalysisResult.ownership
  const ownership = data.ownership?.length ? Array.from(data.ownership) : undefined;
  const policy = data.policy?.length ? Array.from(data.policy) : undefined;

  return {
    moveInfos,
    rootInfo: {
      currentPlayer: 'B',
      scoreLead: data.rootScoreLead,
      visits: data.rootVisits,
      winrate: data.rootWinRate,
    },
    ownership,
    policy,
  };
}

// ---------------------------------------------------------------------------
// Engine status / info (for UI status display)
// ---------------------------------------------------------------------------

export async function getEngineStatus(): Promise<{
  backend: string | null;
  modelName: string | null;
}> {
  try {
    const resp = await fetch('/api/health');
    if (!resp.ok) return { backend: null, modelName: null };
    const data = await resp.json();
    return {
      backend: data.backend ?? 'python-bridge',
      modelName: data.modelName ?? null,
    };
  } catch {
    return { backend: null, modelName: null };
  }
}

// ---------------------------------------------------------------------------
// Enrichment SSE stream
// ---------------------------------------------------------------------------

export interface EnrichmentStageEvent {
  stage: string;
  payload: Record<string, unknown>;
}

/**
 * Start an enrichment pipeline run via SSE. Returns an async generator
 * yielding stage events as they arrive from the bridge.
 */
export async function* streamEnrichment(
  sgfText: string,
  signal?: AbortSignal,
): AsyncGenerator<EnrichmentStageEvent> {
  const resp = await fetch('/api/enrich', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sgf: sgfText }),
    signal,
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => 'Unknown error');
    throw new Error(`Bridge enrich failed (${resp.status}): ${text}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      if (!part.trim()) continue;
      let eventType = 'message';
      let eventData = '';
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          eventData = line.slice(6);
        }
      }
      if (eventType === 'heartbeat') continue;
      if (eventData) {
        try {
          yield { stage: eventType, payload: JSON.parse(eventData) };
        } catch {
          yield { stage: eventType, payload: { raw: eventData } };
        }
      }
    }
  }
}
