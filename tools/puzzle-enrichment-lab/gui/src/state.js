/**
 * state.js — Simple observable state atoms (no framework).
 *
 * Each atom: { get(), set(v), subscribe(fn) → unsubscribe }
 * GhostBan and BesoGo use global namespace; app modules use ES module imports.
 */

export function createState(initial) {
  let value = initial;
  const subs = new Set();
  return {
    get: () => value,
    set: (v) => { value = v; subs.forEach(fn => fn(value)); },
    subscribe: (fn) => { subs.add(fn); return () => subs.delete(fn); },
  };
}

/** Board position: { boardSize, blackStones:[[x,y],...], whiteStones, currentPlayer } */
export const boardState = createState(null);

/** KataGo analysis result: { moveInfos[], rootInfo } */
export const analysisResult = createState(null);

/** Pipeline stages: [{ id, label, status:'pending'|'active'|'complete'|'error' }] */
export const pipelineStages = createState([]);

/** Log lines: string[] */
export const logLines = createState([]);

/** Full AiAnalysisResult from 'complete' SSE event */
export const enrichResult = createState(null);

/** Current SGF text (default: sample tsumego for quick testing) */
export const sgfText = createState('(;GM[1]FF[3]SZ[19]AB[il][kl][kj][hj][ii]AW[jk]PL[W];W[jj];B[ki];W[ik];B[hl];W[ji];B[jh];W[ih];B[kk];W[hi];B[ij];W[hk])');

/** Run metadata: { run_id, trace_id, ac_level } */
export const runInfo = createState(null);

/** Enrichment run status: 'idle' | 'running' | 'cancelling' */
export const isEnriching = createState('idle');

/** Whether analysis is in progress */
export const isAnalyzing = createState(false);

/** Engine lifecycle status: 'not_started' | 'starting' | 'ready' | 'error' */
export const engineStatus = createState('not_started');

/** Config defaults from server (GET /api/config) */
export const configDefaults = createState(null);

/** User config overrides — dotted-path → value */
export const configOverrides = createState({});

/** Analyze visits dropdown selection */
export const analyzeVisits = createState(200);
