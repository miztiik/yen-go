/**
 * engine-manager.ts — Dual-engine selector: browser (TF.js) vs bridge (Python backend).
 * Provides a common `analyze()` interface regardless of engine mode.
 */

import { engineMode, modelName, visitCount, isAnalyzing, analysisResult, engineError, modelStatus } from '../store/state';
import { analyzePython } from './bridge-client';
import { normalizeWorkerAnalysis } from './analysis-bridge';
import type { AnalysisResult, BoardState, Player } from '../types';
import type { AnalysisPayload } from './engine.worker';

let worker: Worker | null = null;
let nextId = 1;
let pendingResolve: Map<number, (result: AnalysisResult) => void> = new Map();
let pendingReject: Map<number, (err: Error) => void> = new Map();
let modelLoaded = false;

const MODELS: Record<string, string> = {
  b6c96: '/models/kata1-b6c96-s175395328-d26788732.bin.gz',
  b10c128: '/models/kata1-b10c128-s1141046784-d204142634.bin.gz',
};

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL('./engine.worker.ts', import.meta.url), { type: 'module' });
    worker.onmessage = (e: MessageEvent) => {
      const msg = e.data;
      if (msg.type === 'analysis' && msg.id != null) {
        const resolve = pendingResolve.get(msg.id);
        if (resolve) {
          pendingResolve.delete(msg.id);
          pendingReject.delete(msg.id);
          resolve(normalizeWorkerAnalysis(msg.result));
        }
      }
      if (msg.type === 'progress' && msg.id != null) {
        // Update analysis result with streaming progress
        analysisResult.value = normalizeWorkerAnalysis(msg.result);
      }
      if (msg.type === 'error' && msg.id != null) {
        const reject = pendingReject.get(msg.id);
        if (reject) {
          pendingResolve.delete(msg.id);
          pendingReject.delete(msg.id);
          reject(new Error(msg.message));
        }
      }
    };
  }
  return worker;
}

/** Initialize the browser engine (TF.js backend + model load) */
export async function initBrowserEngine(modelUrl: string): Promise<{ backend: string }> {
  const w = getWorker();
  return new Promise((resolve, reject) => {
    const handler = (e: MessageEvent) => {
      if (e.data.type === 'ready') {
        w.postMessage({ type: 'load-model', modelUrl });
      } else if (e.data.type === 'model-loaded') {
        w.removeEventListener('message', handler);
        resolve({ backend: e.data.backend });
      } else if (e.data.type === 'error') {
        w.removeEventListener('message', handler);
        reject(new Error(e.data.message));
      }
    };
    w.addEventListener('message', handler);
    w.postMessage({ type: 'init' });
  });
}

/** Analyze a position using the currently selected engine */
export async function analyze(
  board: BoardState,
  currentPlayer: Player,
  boardSizeVal: number,
  komi: number = 6.5,
): Promise<AnalysisResult> {
  isAnalyzing.value = true;
  engineError.value = null;
  try {
    let result: AnalysisResult;
    if (engineMode.value === 'browser') {
      // Auto-init model if not loaded
      if (!modelLoaded) {
        const url = MODELS[modelName.value] ?? MODELS.b6c96;
        modelStatus.value = 'loading';
        try {
          await initBrowserEngine(url);
          modelLoaded = true;
          modelStatus.value = 'ready';
        } catch (err) {
          modelStatus.value = 'error';
          throw err;
        }
      }
      result = await analyzeBrowser(board, currentPlayer, boardSizeVal, komi);
    } else {
      const bridgeResult = await analyzePython({
        board,
        currentPlayer,
        moveHistory: [],
        komi,
        visits: visitCount.value,
      });
      // analyzePython already returns normalized AnalysisResult
      result = bridgeResult;
    }
    analysisResult.value = result;
    return result;
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    engineError.value = `Analysis failed: ${msg}`;
    throw err;
  } finally {
    isAnalyzing.value = false;
  }
}

async function analyzeBrowser(
  board: BoardState,
  currentPlayer: Player,
  boardSizeVal: number,
  komi: number,
): Promise<AnalysisResult> {
  const w = getWorker();
  const id = nextId++;
  return new Promise((resolve, reject) => {
    pendingResolve.set(id, resolve);
    pendingReject.set(id, reject);
    w.postMessage({
      type: 'analyze',
      id,
      board,
      currentPlayer,
      boardSize: boardSizeVal,
      komi,
      visits: visitCount.value,
      topK: 10,
    });
  });
}

/** Cancel ongoing analysis */
export function cancelAnalysis(): void {
  if (worker) {
    // Cancel all pending
    for (const [id, reject] of pendingReject) {
      reject(new Error('Cancelled'));
    }
    pendingResolve.clear();
    pendingReject.clear();
  }
  isAnalyzing.value = false;
  analysisResult.value = null;
}
