/**
 * Go Quote Display Component
 * @module components/shared/GoQuote
 *
 * Displays inspirational Go proverbs and wisdom.
 * Used for empty states and motivational messages.
 *
 * Covers: FR-047 (Empty states with Go quotes)
 */

import type { JSX } from 'preact';
import { useMemo } from 'preact/hooks';
import type { GoQuote as GoQuoteType } from '@/constants/goQuotes';
import { getRandomQuote, getTodayQuote, getQuoteByDate } from '@/constants/goQuotes';

export interface GoQuoteProps {
  /** Quote to display (if not provided, shows today's quote) */
  quote?: GoQuoteType;
  /** Mode: 'daily' for consistent daily quote, 'random' for random each render */
  mode?: 'daily' | 'random' | 'date';
  /** Date string for date-based quote (YYYY-MM-DD) */
  date?: string;
  /** Show author attribution */
  showAuthor?: boolean;
  /** Custom className */
  className?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses: Record<'sm' | 'md' | 'lg', { text: string; author: string }> = {
  sm: { text: 'text-sm', author: 'text-xs' },
  md: { text: 'text-base', author: 'text-sm' },
  lg: { text: 'text-xl', author: 'text-base' },
};

/**
 * Display a Go proverb or wisdom quote
 */
export function GoQuote({
  quote: providedQuote,
  mode = 'daily',
  date,
  showAuthor = false,
  className = '',
  size = 'md',
}: GoQuoteProps): JSX.Element {
  const quote = useMemo(() => {
    if (providedQuote) {
      return providedQuote;
    }
    switch (mode) {
      case 'random':
        return getRandomQuote();
      case 'date':
        return getQuoteByDate(date ?? new Date().toISOString().split('T')[0] as string);
      case 'daily':
      default:
        return getTodayQuote();
    }
  }, [providedQuote, mode, date]);

  const classes = sizeClasses[size];

  return (
    <div class={`go-quote text-center p-4 italic ${className}`}>
      <p className={`${classes.text} leading-relaxed text-[var(--color-neutral-600)] m-0`}>"{quote.text}"</p>
      {showAuthor && (
        <p className={`${classes.author} text-[var(--color-neutral-500)] mt-2 not-italic`}>— {quote.author}</p>
      )}
    </div>
  );
}

/**
 * Empty state component with Go quote
 */
export interface EmptyStateProps {
  /** Message to display above the quote */
  message?: string;
  /** Quote mode */
  quoteMode?: 'daily' | 'random';
  /** Custom className */
  className?: string;
  /** Optional action button */
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({
  message,
  quoteMode = 'daily',
  className = '',
  action,
}: EmptyStateProps): JSX.Element {
  return (
    <div class={`empty-state flex flex-col items-center justify-center p-8 min-h-[200px] text-center ${className}`}>
      {message && <p className="text-lg text-[var(--color-neutral-800)] mb-4 font-medium">{message}</p>}
      <GoQuote mode={quoteMode} size="md" showAuthor={false} />
      {action && (
        <button
          type="button"
          className="mt-4 px-6 py-2 bg-[var(--color-info-solid)] text-[var(--color-bg-panel)] border-none rounded-md cursor-pointer text-sm font-medium"
          onClick={action.onClick}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

export default GoQuote;
