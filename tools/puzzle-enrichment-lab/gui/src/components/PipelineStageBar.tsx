import React from 'react';

// 10 pipeline stages matching enrich_single_puzzle step names
const STAGES = [
  { key: 'parse_sgf', label: 'Parse' },
  { key: 'extract_solution', label: 'Solution' },
  { key: 'build_query', label: 'Query' },
  { key: 'katago_analysis', label: 'Analyze' },
  { key: 'validate_move', label: 'Validate' },
  { key: 'generate_refutations', label: 'Refute' },
  { key: 'estimate_difficulty', label: 'Difficulty' },
  { key: 'assemble_result', label: 'Assemble' },
  { key: 'teaching_enrichment', label: 'Teaching' },
  { key: 'enriched_sgf', label: 'Enrich SGF' },
] as const;

export type StageKey = (typeof STAGES)[number]['key'];

export type StageStatus = 'pending' | 'active' | 'complete' | 'error';

export interface StageState {
  status: StageStatus;
  /** Elapsed time in ms, set when complete */
  elapsedMs?: number;
  /** Error message, set when error */
  error?: string;
}

export interface PipelineStageBarProps {
  stages: Record<StageKey, StageState>;
  onStageClick?: (key: StageKey) => void;
}

function formatTiming(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

const statusClasses: Record<StageStatus, string> = {
  pending: 'bg-gray-700 text-gray-400',
  active: 'bg-blue-600 text-white animate-pulse',
  complete: 'bg-green-700 text-green-100',
  error: 'bg-red-700 text-red-100',
};

const statusIcon: Record<StageStatus, string> = {
  pending: '',
  active: '⟳',
  complete: '✓',
  error: '✗',
};

export const PipelineStageBar: React.FC<PipelineStageBarProps> = ({
  stages,
  onStageClick,
}) => {
  return (
    <div className="flex items-center gap-1 px-2 py-1 bg-gray-900 border-b border-gray-700 overflow-x-auto">
      {STAGES.map(({ key, label }) => {
        const state = stages[key] ?? { status: 'pending' as const };
        return (
          <button
            key={key}
            type="button"
            className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono whitespace-nowrap transition-colors ${statusClasses[state.status]}`}
            onClick={() => onStageClick?.(key)}
            title={state.error ?? (state.elapsedMs != null ? formatTiming(state.elapsedMs) : key)}
          >
            {statusIcon[state.status] && (
              <span className="text-[10px]">{statusIcon[state.status]}</span>
            )}
            <span>{label}</span>
            {state.status === 'complete' && state.elapsedMs != null && (
              <span className="text-[10px] opacity-70">{formatTiming(state.elapsedMs)}</span>
            )}
          </button>
        );
      })}
    </div>
  );
};

/** Create an initial stage map with all stages pending */
export function createInitialStages(): Record<StageKey, StageState> {
  const map = {} as Record<StageKey, StageState>;
  for (const { key } of STAGES) {
    map[key] = { status: 'pending' };
  }
  return map;
}
