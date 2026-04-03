/**
 * Move Comment Display Component
 * @module components/Review/MoveCommentDisplay
 *
 * Displays SGF comments associated with moves (FR-022, FR-023, FR-024).
 * Shows both node comments (C[]) and move descriptions.
 *
 * Constitution Compliance:
 * - IX. Accessibility: Readable text, proper ARIA labels
 * - X. Design Philosophy: Contextual information without clutter
 */

import type { JSX } from 'preact';
import type { MoveComment } from '@models/SolutionPresentation';

/**
 * Props for MoveCommentDisplay component.
 */
export interface MoveCommentDisplayProps {
  /** Comments for the current position */
  comments: readonly MoveComment[];
  /** Current move number (for context) */
  currentMoveNumber?: number;
  /** Maximum height before scrolling */
  maxHeight?: number;
  /** CSS class override */
  className?: string;
  /** Whether to show move number badge */
  showMoveNumber?: boolean;
}

/**
 * Format comment text with basic parsing.
 * Handles line breaks and common SGF escape sequences.
 */
function formatCommentText(text: string): string[] {
  // Replace SGF escape sequences
  const formatted = text
    .replace(/\\]/g, ']')
    .replace(/\\\\/g, '\\')
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '');

  // Split into paragraphs
  return formatted
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

/**
 * Detect comment type and return appropriate styling hint.
 */
function detectCommentType(comment: MoveComment): 'variation' | 'note' | 'question' | 'default' {
  const text = comment.text.toLowerCase();

  if (text.includes('variation') || text.includes('alternative')) {
    return 'variation';
  }
  if (text.includes('?') || text.includes('why')) {
    return 'question';
  }
  if (text.includes('note:') || text.includes('hint:')) {
    return 'note';
  }
  return 'default';
}

/**
 * Get icon for comment type.
 */
function getCommentIcon(type: string): string {
  switch (type) {
    case 'variation':
      return '⤴';
    case 'question':
      return '?';
    case 'note':
      return '📝';
    default:
      return '💬';
  }
}

/**
 * Single comment display.
 */
function CommentItem({
  comment,
  showMoveNumber,
}: {
  comment: MoveComment;
  showMoveNumber: boolean;
}): JSX.Element {
  const type = detectCommentType(comment);
  const icon = getCommentIcon(type);
  const paragraphs = formatCommentText(comment.text);

  return (
    <div className={`move-comment move-comment--${type}`} role="article">
      <div className="move-comment__header">
        <span className="move-comment__icon" aria-hidden="true">
          {icon}
        </span>
        {showMoveNumber && comment.moveNumber !== undefined && (
          <span className="move-comment__move-number">
            Move {comment.moveNumber}
          </span>
        )}
      </div>
      <div className="move-comment__body">
        {paragraphs.map((paragraph, idx) => (
          <p key={idx} className="move-comment__paragraph">
            {paragraph}
          </p>
        ))}
      </div>
    </div>
  );
}

/**
 * MoveCommentDisplay component - shows comments for current position.
 */
export function MoveCommentDisplay({
  comments,
  currentMoveNumber,
  maxHeight = 200,
  className,
  showMoveNumber = true,
}: MoveCommentDisplayProps): JSX.Element | null {
  if (comments.length === 0) {
    return null;
  }

  return (
    <div
      className={`move-comment-display ${className ?? ''}`}
      style={{ maxHeight: `${maxHeight}px` }}
      role="region"
      aria-label={
        currentMoveNumber !== undefined
          ? `Comments for move ${currentMoveNumber}`
          : 'Position comments'
      }
    >
      {comments.map((comment, idx) => (
        <CommentItem
          key={`comment-${comment.moveNumber ?? idx}`}
          comment={comment}
          showMoveNumber={showMoveNumber && comments.length > 1}
        />
      ))}
    </div>
  );
}

/**
 * Compact comment display - single line preview with expand.
 */
export function CompactCommentDisplay({
  comment,
  maxLength = 100,
  className,
}: {
  comment: MoveComment;
  maxLength?: number;
  className?: string;
}): JSX.Element {
  const text = formatCommentText(comment.text).join(' ');
  const truncated = text.length > maxLength;
  const displayText = truncated ? `${text.substring(0, maxLength)}...` : text;

  return (
    <div
      className={`compact-comment ${className ?? ''}`}
      title={truncated ? text : undefined}
      aria-label={`Comment: ${text}`}
    >
      <span className="compact-comment__icon" aria-hidden="true">
        💬
      </span>
      <span className="compact-comment__text">{displayText}</span>
    </div>
  );
}

export default MoveCommentDisplay;
