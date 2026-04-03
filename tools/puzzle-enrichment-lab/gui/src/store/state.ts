import { signal, computed } from '@preact/signals';
import type { AnalysisResult, TreeNode, EnrichStage, EnrichResult } from '../types';
import { applyTsumegoFrame } from '../lib/frame';

// ── Core board state ──
export const sgfText = signal<string>('');
export const boardMat = signal<number[][]>([]);
export const boardSize = signal<number>(19);
export const currentPlayer = signal<'B' | 'W'>('B');

// ── Solution tree ──
export const solutionTree = signal<TreeNode | null>(null);
export const currentNode = signal<TreeNode | null>(null);

// ── Analysis state ──
export const analysisResult = signal<AnalysisResult | null>(null);
export const isAnalyzing = signal<boolean>(false);
export const showAnalysis = signal<boolean>(false);
export const showFrame = signal<boolean>(false);
export const hoveredPV = signal<string[]>([]);

// ── Engine settings ──
export const engineMode = signal<'browser' | 'bridge'>('browser');
export const modelName = signal<string>('b6c96');
export const visitCount = signal<number>(500);
export const engineError = signal<string | null>(null);
export const modelStatus = signal<'idle' | 'loading' | 'ready' | 'error'>('idle');

// ── Enrichment pipeline ──
export const enrichStages = signal<EnrichStage[]>([]);
export const enrichResult = signal<EnrichResult | null>(null);
export const isEnriching = signal<boolean>(false);

// ── Derived signals ──
export const framedMat = computed(() => {
  const mat = boardMat.value;
  if (!showFrame.value || mat.length === 0) return mat;
  return applyTsumegoFrame(mat);
});
export const rootScoreLead = computed(() => analysisResult.value?.rootInfo.scoreLead ?? null);
export const rootVisits = computed(() => analysisResult.value?.rootInfo.visits ?? 0);
export const rootWinrate = computed(() => analysisResult.value?.rootInfo.winrate ?? null);
export const candidateMoves = computed(() => analysisResult.value?.moveInfos ?? []);
