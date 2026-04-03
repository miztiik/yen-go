/**
 * engine.worker.ts — Web Worker for in-browser KataGo via TF.js.
 * Adapted from yen-go-sensei for the enrichment lab GUI.
 *
 * Messages:
 *   → { type: 'init', preferredBackend?: string }
 *   ← { type: 'ready', backend: string }
 *
 *   → { type: 'load-model', modelUrl: string }
 *   ← { type: 'model-loaded', backend: string, modelName: string }
 *   ← { type: 'error', message: string }
 *
 *   → { type: 'analyze', id: number, board: BoardState, currentPlayer: Player,
 *       komi: number, rules?: GameRules, visits: number, topK?: number }
 *   ← { type: 'analysis', id: number, result: AnalysisPayload }
 *   ← { type: 'error', message: string, id?: number }
 *
 *   → { type: 'cancel', id: number }
 *   ← { type: 'cancelled', id: number }
 */

import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-backend-webgl';
import '@tensorflow/tfjs-backend-wasm';
import { setThreadsCount, setWasmPaths } from '@tensorflow/tfjs-backend-wasm';
import pako from 'pako';

import { parseKataGoModelV8 } from './katago/loadModelV8';
import { KataGoModelV8Tf } from './katago/modelV8';
import { MctsSearch } from './katago/analyzeMcts';
import { setBoardSize } from './katago/fastBoard';
import type { BoardState, GameRules, Player } from '../types';

let model: KataGoModelV8Tf | null = null;
let backendPromise: Promise<void> | null = null;
let activeBackend = 'cpu';

async function initBackend(preferred?: string): Promise<void> {
  if (preferred && preferred !== 'auto') {
    try {
      if (preferred === 'wasm') {
        setWasmPaths('/tfjs-wasm/');
      }
      await tf.setBackend(preferred);
      await tf.ready();
      activeBackend = tf.getBackend();
      return;
    } catch {
      // fall through to cascade
    }
  }

  // WebGPU → WebGL → WASM → CPU cascade (matches goproblems.com)
  for (const backend of ['webgpu', 'webgl', 'wasm', 'cpu']) {
    try {
      if (backend === 'wasm') {
        setWasmPaths('/tfjs-wasm/');
        const isCrossOriginIsolated = (globalThis as unknown as { crossOriginIsolated?: boolean }).crossOriginIsolated === true;
        if (isCrossOriginIsolated) {
          const hc = (globalThis as unknown as { navigator?: { hardwareConcurrency?: number } }).navigator?.hardwareConcurrency ?? 1;
          setThreadsCount(Math.max(1, Math.min(8, Math.floor(hc))));
        }
      }
      await tf.setBackend(backend);
      await tf.ready();
      activeBackend = tf.getBackend();
      return;
    } catch {
      continue;
    }
  }
}

async function ensureBackend(preferred?: string): Promise<void> {
  if (!backendPromise) {
    backendPromise = initBackend(preferred)
      .then(() => tf.enableProdMode())
      .catch((err) => {
        backendPromise = null;
        throw err;
      });
  }
  await backendPromise;
}

export interface AnalysisPayload {
  rootWinRate: number;
  rootScoreLead: number;
  rootVisits: number;
  ownership: number[];
  policy: number[];
  moves: Array<{
    x: number;
    y: number;
    winRate: number;
    scoreLead: number;
    visits: number;
    order: number;
    prior: number;
    pv: string[];
  }>;
}

self.onmessage = async (e: MessageEvent) => {
  const msg = e.data;

  if (msg.type === 'init') {
    try {
      await ensureBackend(msg.preferredBackend);
      post({ type: 'ready', backend: activeBackend });
    } catch (err: any) {
      post({ type: 'error', message: `Backend init failed: ${err.message}` });
    }
    return;
  }

  if (msg.type === 'load-model') {
    try {
      await ensureBackend();
      const resp = await fetch(msg.modelUrl);
      if (!resp.ok) throw new Error(`Fetch failed: ${resp.status}`);
      const buf = new Uint8Array(await resp.arrayBuffer());

      let data = buf;
      if (buf.length >= 2 && buf[0] === 0x1f && buf[1] === 0x8b) {
        data = pako.ungzip(buf);
      }

      const parsed = parseKataGoModelV8(data);
      if (model) model.dispose();
      model = new KataGoModelV8Tf(parsed);

      // Warmup
      const spatial = tf.zeros([1, 19, 19, 22], 'float32') as tf.Tensor4D;
      const global = tf.zeros([1, 19], 'float32') as tf.Tensor2D;
      const out = model.forwardValueOnly(spatial, global);
      await Promise.all([out.value.data(), out.scoreValue.data()]);
      spatial.dispose(); global.dispose();
      out.value.dispose(); out.scoreValue.dispose();

      post({ type: 'model-loaded', backend: activeBackend, modelName: parsed.modelName });
    } catch (err: any) {
      post({ type: 'error', message: `Model load failed: ${err.message}` });
    }
    return;
  }

  if (msg.type === 'analyze') {
    if (!model) {
      post({ type: 'error', message: 'Model not loaded', id: msg.id });
      return;
    }

    const bs = msg.boardSize ?? 19;
    setBoardSize(bs);

    const board: BoardState = msg.board;
    const rules: GameRules = msg.rules ?? 'japanese';

    try {
      const search = await MctsSearch.create({
        model,
        board,
        previousBoard: undefined,
        previousPreviousBoard: undefined,
        currentPlayer: msg.currentPlayer as Player,
        moveHistory: [],
        komi: msg.komi ?? 6.5,
        rules,
        nnRandomize: false,
        conservativePass: true,
        maxChildren: Math.max(8, msg.topK ?? 10),
        ownershipMode: 'root',
        wideRootNoise: 0.04,
        regionOfInterest: null,
      });

      // Time-sliced streaming: run MCTS in 250ms chunks, send progress updates
      const totalVisits = msg.visits ?? 500;
      const batchSize = activeBackend === 'webgpu' ? 16 : 4;
      let completed = 0;
      while (completed < totalVisits) {
        const chunkVisits = Math.min(totalVisits - completed, Math.max(batchSize * 10, 50));
        await search.run({
          visits: chunkVisits,
          maxTimeMs: 250,
          batchSize,
          shouldAbort: () => false,
        });
        // Send progress update
        const progressAnalysis = search.getAnalysis({
          topK: msg.topK ?? 10,
          includeMovesOwnership: false,
          analysisPvLen: 15,
          cloneBuffers: true,
        });
        completed = progressAnalysis.rootVisits ?? (completed + chunkVisits);
        const progressPayload: AnalysisPayload = {
          rootWinRate: progressAnalysis.rootWinRate,
          rootScoreLead: progressAnalysis.rootScoreLead,
          rootVisits: completed,
          ownership: Array.from(progressAnalysis.ownership),
          policy: progressAnalysis.policy ? Array.from(progressAnalysis.policy) : [],
          moves: progressAnalysis.moves.map(m => ({
            x: m.x,
            y: m.y,
            winRate: m.winRate,
            scoreLead: m.scoreLead,
            visits: m.visits,
            order: m.order,
            prior: m.prior ?? 0,
            pv: m.pv ?? [],
          })),
        };
        post({ type: 'progress', id: msg.id, result: progressPayload, visits: completed, total: totalVisits });

        if (completed >= totalVisits) break;
      }

      const analysis = search.getAnalysis({
        topK: msg.topK ?? 10,
        includeMovesOwnership: false,
        analysisPvLen: 15,
        cloneBuffers: true,
      });

      const payload: AnalysisPayload = {
        rootWinRate: analysis.rootWinRate,
        rootScoreLead: analysis.rootScoreLead,
        rootVisits: analysis.rootVisits ?? totalVisits,
        ownership: Array.from(analysis.ownership),
        policy: analysis.policy ? Array.from(analysis.policy) : [],
        moves: analysis.moves.map(m => ({
          x: m.x,
          y: m.y,
          winRate: m.winRate,
          scoreLead: m.scoreLead,
          visits: m.visits,
          order: m.order,
          prior: m.prior ?? 0,
          pv: m.pv ?? [],
        })),
      };

      post({ type: 'analysis', id: msg.id, result: payload });
    } catch (err: any) {
      post({ type: 'error', message: `Analysis failed: ${err.message}`, id: msg.id });
    }
    return;
  }

  if (msg.type === 'cancel') {
    post({ type: 'cancelled', id: msg.id });
    return;
  }
};

function post(data: unknown): void {
  self.postMessage(data);
}
