/**
 * Sidebar Section Component
 * @module pages/PuzzleView/SidebarSection
 *
 * The side panel with controls, stats, solution tree, and comments.
 * Extracted from PuzzleView.tsx for better modularity.
 */

import type { JSX } from 'preact';
import type { PuzzleTag } from '../../types';
import type { BoardRotation } from '../../components/Board/rotation';
import type { SolutionNode } from '../../types/puzzle-internal';
import type { TraversalState } from '../../lib/solver/traversal';
import type { CompletionResult } from '../../lib/solver/completion';
import type { FeedbackType } from '../../components/Puzzle/FeedbackOverlay';
import type { PuzzleStatus } from '../../components/ProblemNav/ProblemNav';
import type { HistoryManager } from '../../lib/solver/history';

import { QuickControls } from '../../components/QuickControls/QuickControls';
import { ProblemNav } from '../../components/ProblemNav/ProblemNav';
import { SolutionTreeView } from '../../components/SolutionTree/SolutionTreeView';
import { CommentPanel } from '../../components/SolutionTree/CommentPanel';
import { SideToMove } from '../../components/shared/SideToMove';
import { formatElapsedTime } from '../../lib/progress';
import { theme } from './utils';

export interface SidebarSectionProps {
  puzzleLevel: string;
  puzzleTags?: readonly PuzzleTag[];
  currentColor: 'black' | 'white';
  boardRotation: BoardRotation;
  solutionTree: SolutionNode;
  currentNodeId: string;
  currentNodeInfo: { comment: string | null; isCorrect: boolean; move: string; moveNumber: number } | null;
  traversalState: TraversalState;
  historyManager: HistoryManager;
  feedback: { type: FeedbackType; message: string } | null;
  showSuccess: boolean;
  showFailure: boolean;
  completionResult: CompletionResult | null;
  hintsRemaining: number;
  currentHintText: string | null;
  elapsedTime: number;
  hintsUsed: number;
  puzzleHintCount: number;
  autoAdvance: boolean;
  autoAdvanceDelay: number;
  isMobileView: boolean;
  onRotate: () => void;
  onUndo: () => void;
  onReset: () => void;
  onHint: () => void;
  onTreeNodeSelect: (treeNodeId: string, node: SolutionNode) => void;
  onShowSuccess: (show: boolean) => void;
  onShowFailure: (show: boolean) => void;
  onRevealFullTree: (reveal: boolean) => void;
  onFeedbackDismiss: () => void;
  onNextPuzzle?: () => void;
  // Puzzle navigation
  puzzleSetNavigation?: {
    totalPuzzles: number;
    currentIndex: number;
    statuses: PuzzleStatus[];
    onNavigate: (index: number) => void;
    currentStreak?: number | undefined;
  };
  onPrevPuzzle: () => void;
  // Explore mode
  isExploreMode: boolean;
  onToggleExploreMode: () => void;
}

export function SidebarSection({
  puzzleLevel,
  puzzleTags,
  currentColor,
  boardRotation,
  solutionTree,
  currentNodeId,
  currentNodeInfo,
  traversalState,
  historyManager,
  feedback,
  showSuccess,
  showFailure,
  completionResult,
  hintsRemaining,
  currentHintText,
  elapsedTime,
  hintsUsed,
  puzzleHintCount,
  autoAdvance,
  autoAdvanceDelay,
  isMobileView,
  onRotate,
  onUndo,
  onReset,
  onHint,
  onTreeNodeSelect,
  onShowSuccess,
  onShowFailure,
  onRevealFullTree,
  onFeedbackDismiss,
  onNextPuzzle,
  puzzleSetNavigation,
  onPrevPuzzle,
  isExploreMode,
  onToggleExploreMode,
}: SidebarSectionProps): JSX.Element | null {
  // Hide on mobile
  if (isMobileView) return null;

  // Styles
  const sideColumnStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    flex: '0 0 320px',
    width: '320px',
    gap: '0',
    backgroundColor: theme.bgWhite,
    borderRadius: '12px',
    border: `1px solid ${theme.border}`,
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    overflow: 'hidden',
    maxHeight: '100vh',
  };

  /** Sticky top: controls, stats, nav — always visible */
  const stickyTopStyle: JSX.CSSProperties = {
    flexShrink: 0,
  };

  /** Scrollable bottom: solution tree, comments */
  const scrollAreaStyle: JSX.CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    minHeight: 0,
  };

  const sidePanelSectionStyle: JSX.CSSProperties = {
    padding: '16px',
    borderBottom: `1px solid ${theme.borderLight}`,
  };

  return (
    <aside style={sideColumnStyle}>
      {/* ── Sticky Top: always visible ── */}
      <div style={stickyTopStyle}>

      {/* Puzzle Context — Level + Tags (moved from board header per T11.3) */}
      <div style={{
        ...sidePanelSectionStyle,
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        flexWrap: 'wrap',
      }}>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          backgroundColor: theme.primary,
          color: 'var(--color-text-inverse)',
          padding: '3px 10px',
          borderRadius: '6px',
          fontSize: '12px',
          fontWeight: 600,
          textTransform: 'capitalize',
          boxShadow: 'var(--shadow-sm)',
        }}>
          {puzzleLevel}
        </span>
        {puzzleTags && puzzleTags.length > 0 && puzzleTags.map(tag => (
          <span
            key={tag}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              backgroundColor: 'var(--color-bg-secondary)',
              color: 'var(--color-text-secondary)',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 500,
            }}
          >
            {tag.replace(/-/g, ' ')}
          </span>
        ))}
      </div>

      {/* Feedback Section */}
      {feedback && (
        <div style={{
          ...sidePanelSectionStyle,
          backgroundColor: feedback.type === 'correct' ? 'var(--color-success-bg)' : 
                          feedback.type === 'incorrect' ? 'var(--color-error-bg)' : 
                          'var(--color-warning-bg)',
          borderLeft: `4px solid ${
            feedback.type === 'correct' ? theme.success : 
            feedback.type === 'incorrect' ? theme.error : 
            theme.warning
          }`,
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          cursor: 'pointer',
          animation: 'slideIn 0.2s ease-out',
        }} onClick={onFeedbackDismiss}>
          <span style={{ fontSize: '20px' }}>
            {feedback.type === 'correct' ? '✓' : 
             feedback.type === 'incorrect' ? '✗' : '⚠'}
          </span>
          <span style={{ 
            flex: 1, 
            fontSize: '14px',
            color: feedback.type === 'correct' ? 'var(--color-success)' : 
                   feedback.type === 'incorrect' ? 'var(--color-error)' : 
                   'var(--color-warning)',
            fontWeight: 500,
          }}>
            {feedback.message}
          </span>
          <span style={{ fontSize: '12px', opacity: 0.6 }}>×</span>
        </div>
      )}

      {/* Hints Section */}
      {currentHintText && (
        <div style={{
          ...sidePanelSectionStyle,
          backgroundColor: 'var(--color-warning-bg)',
          borderLeft: `4px solid ${theme.warning}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <span style={{ fontSize: '18px' }}>💡</span>
            <div>
              <h4 style={{ margin: '0 0 4px 0', fontSize: '13px', fontWeight: 600, color: 'var(--color-warning)' }}>
                Hint
              </h4>
              <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                {currentHintText}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Player Status: stats + side to move (T11.10: before actions) */}
      <div style={{
        ...sidePanelSectionStyle,
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '8px',
      }}>
        <div style={{ textAlign: 'center', padding: '8px' }}>
          <SideToMove
            color={currentColor}
            size="small"
            showIcon={true}
          />
        </div>
        <div style={{ textAlign: 'center', padding: '8px' }}>
          <div style={{ fontSize: '18px', fontWeight: 700, color: theme.text }}>
            {formatElapsedTime(elapsedTime)}
          </div>
          <div style={{ fontSize: '11px', color: theme.textMuted, marginTop: '2px' }}>Time</div>
        </div>
        <div style={{ textAlign: 'center', padding: '8px' }}>
          <div style={{ fontSize: '18px', fontWeight: 700, color: theme.text }}>
            {hintsUsed}/{puzzleHintCount}
          </div>
          <div style={{ fontSize: '11px', color: theme.textMuted, marginTop: '2px' }}>Hints</div>
        </div>
        <div style={{ textAlign: 'center', padding: '8px' }}>
          <div style={{ fontSize: '18px', fontWeight: 700, color: traversalState.wrongAttempts > 0 ? theme.error : theme.text }}>
            {traversalState.wrongAttempts}
          </div>
          <div style={{ fontSize: '11px', color: theme.textMuted, marginTop: '2px' }}>Wrong</div>
        </div>
      </div>

      {/* Actions: controls (T11.10: after player status) */}
      <div style={sidePanelSectionStyle}>
        <QuickControls
          onRotate={onRotate}
          onUndo={onUndo}
          onReset={onReset}
          onHint={onHint}
          onToggleExplore={onToggleExploreMode}
          isExploreMode={isExploreMode}
          hasTree={solutionTree.children.length > 0}
          canUndo={historyManager.canUndo()}
          hintsRemaining={hintsRemaining}
          rotationAngle={boardRotation}
          enableKeyboard={true}
        />
      </div>

      </div>{/* end stickyTop */}

      {/* ── Scrollable Bottom: nav, results, tree, comments ── */}
      <div style={scrollAreaStyle}>

      {/* ProblemNav component with progress */}
      {puzzleSetNavigation && (
        <div style={sidePanelSectionStyle}>
          <h3 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 600, color: theme.textMuted, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Problems
          </h3>
          <ProblemNav
            totalProblems={puzzleSetNavigation.totalPuzzles}
            currentIndex={puzzleSetNavigation.currentIndex}
            statuses={puzzleSetNavigation.statuses}
            onNavigate={puzzleSetNavigation.onNavigate}
            onPrev={onPrevPuzzle}
            onNext={onNextPuzzle ?? (() => {})}
            enableKeyboard={false}
            currentStreak={puzzleSetNavigation.currentStreak}
          />
        </div>
      )}

      {/* Success/Failure result */}
      {(showSuccess || showFailure) && completionResult && (
        <div style={{
          padding: '16px',
          backgroundColor: showSuccess ? 'var(--color-success-bg)' : 'var(--color-error-bg)',
          borderRadius: '8px',
          textAlign: 'center',
          border: `2px solid ${showSuccess ? theme.success : theme.error}`,
        }}>
          <div style={{ 
            fontSize: '18px', 
            fontWeight: 700, 
            color: showSuccess ? 'var(--color-success)' : 'var(--color-error)',
            marginBottom: '4px',
          }}>
            {showSuccess ? 'Correct!' : 'Not quite...'}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', marginBottom: '12px' }}>
            {showSuccess 
              ? formatElapsedTime(completionResult.timeTaken ?? 0)
              : 'Try again or view the solution'
            }
            {autoAdvance && onNextPuzzle && (
              <span style={{ display: 'block', fontSize: '11px', color: theme.textMuted, marginTop: '4px' }}>
                Next puzzle in {Math.round(autoAdvanceDelay / 1000)}s...
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
            <button
              onClick={onReset}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                border: `1px solid ${theme.border}`,
                backgroundColor: theme.bgWhite,
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 500,
              }}
            >
              {showSuccess ? 'Try Again' : 'Retry'}
            </button>
            {showSuccess ? (
              <button
                onClick={() => onShowSuccess(false)}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: theme.primary,
                  color: 'var(--color-text-inverse)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                Review
              </button>
            ) : (
              <button
                onClick={() => {
                  onShowFailure(false);
                  onRevealFullTree(true);
                }}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: theme.primary,
                  color: 'var(--color-text-inverse)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                Show Solution
              </button>
            )}
            {onNextPuzzle && (
              <button
                onClick={onNextPuzzle}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: theme.success,
                  color: 'var(--color-text-inverse)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                Next →
              </button>
            )}
          </div>
        </div>
      )}

      {/* Solution Tree (shown when explore is active via QuickControls) */}
      {solutionTree.children.length > 0 && !showSuccess && !showFailure && isExploreMode && (
        <div style={{ 
          padding: '12px',
          backgroundColor: theme.bgWhite,
          borderRadius: '8px',
          border: `1px solid ${theme.borderLight}`,
        }}>
          <div style={{ 
            minHeight: '150px',
            maxHeight: '250px',
            overflow: 'auto',
          }}>
            <SolutionTreeView
              tree={solutionTree}
              currentNodeId={currentNodeId}
              onNodeSelect={onTreeNodeSelect}
              showCorrectness={true}
              scale={0.25}
              className="desktop-solution-tree"
            />
          </div>
        </div>
      )}

      {/* CommentPanel for current node */}
      {currentNodeInfo?.comment && !showSuccess && !showFailure && (
        <div style={{ 
          padding: '12px',
          backgroundColor: theme.bgWhite,
          borderRadius: '8px',
          border: `1px solid ${theme.borderLight}`,
        }}>
          <CommentPanel
            comment={currentNodeInfo.comment}
            {...(currentNodeInfo.move ? { moveCoordinate: currentNodeInfo.move } : {})}
            {...(currentNodeInfo.moveNumber !== undefined ? { moveNumber: currentNodeInfo.moveNumber } : {})}
            {...(currentNodeInfo.isCorrect !== undefined ? { isCorrectMove: currentNodeInfo.isCorrect } : {})}
          />
        </div>
      )}

      </div>{/* end scrollArea */}
    </aside>
  );
}
