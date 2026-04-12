import type { FunctionalComponent } from 'preact';
import type { SkillLevel } from '../../models/collection';
import { getSkillLevelInfo } from '../../models/collection';

export interface RushPuzzleResult {
  id: string;
  puzzleNumber: number;
  level: SkillLevel;
  tags: readonly string[];
  success: boolean;
  skipped: boolean;
  timeSpentMs: number;
}

export interface PuzzleCardProps {
  result: RushPuzzleResult;
  isCompact?: boolean;
}

/**
 * Card showing a completed puzzle result in the Rush sidebar.
 * Shows puzzle number, category tag, level, and result status.
 */
export const PuzzleCard: FunctionalComponent<PuzzleCardProps> = ({ result, isCompact = false }) => {
  const levelInfo = getSkillLevelInfo(result.level);
  const primaryTag = result.tags[0] ?? 'general';

  const statusColor = result.skipped
    ? 'var(--color-neutral-400)'
    : result.success
      ? 'var(--color-mode-rush-border)'
      : 'var(--color-error)';

  const statusIcon = result.skipped ? '⏭️' : result.success ? '✅' : '❌';

  if (isCompact) {
    return (
      <div
        className="flex items-center gap-2 px-2 py-1.5 bg-[--color-bg-panel] rounded text-xs"
        style={{ borderLeft: `3px solid ${statusColor}` }}
      >
        <span className="font-medium text-[--color-neutral-500]">#{result.puzzleNumber}</span>
        <span className="text-[--color-neutral-400]">{levelInfo?.shortName}</span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-3 px-3 py-2 bg-[--color-bg-panel] rounded-lg shadow-sm"
      style={{ borderLeft: `4px solid ${statusColor}` }}
    >
      {/* Puzzle number */}
      <div className="w-8 h-8 rounded-full bg-[--color-neutral-100] flex items-center justify-center font-semibold text-sm text-[--color-neutral-700] shrink-0">
        {result.puzzleNumber}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-[--color-neutral-700] capitalize">
            {formatTagName(primaryTag)}
          </span>
          <span className="text-[0.625rem] text-[--color-neutral-400] bg-[--color-neutral-100] px-1.5 py-0.5 rounded-full">
            {levelInfo?.shortName ?? result.level}
          </span>
        </div>
        <div className="text-[0.625rem] text-[--color-neutral-400] mt-0.5">
          {formatTime(result.timeSpentMs)}
        </div>
      </div>

      {/* Status icon */}
      <div className="text-base shrink-0">{statusIcon}</div>
    </div>
  );
};

/**
 * Format tag name for display
 */
function formatTagName(tag: string): string {
  return tag.replace(/-/g, ' ');
}

/**
 * Format time in seconds
 */
function formatTime(ms: number): string {
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export default PuzzleCard;
