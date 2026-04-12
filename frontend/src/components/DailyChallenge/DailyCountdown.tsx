/**
 * DailyCountdown Component
 * @module components/DailyChallenge/DailyCountdown
 *
 * Countdown timer showing time until next daily challenge.
 *
 * Covers: FR-034
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { calculateCountdown, formatCountdown } from '@/services/dailyChallengeService';
import type { DailyCountdown as DailyCountdownType } from '@/models/dailyChallenge';

export interface DailyCountdownProps {
  /** Callback when countdown reaches zero */
  onReady?: () => void;
  /** Show seconds (more frequent updates) */
  showSeconds?: boolean | undefined;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg' | undefined;
  /** Custom className */
  className?: string | undefined;
}

const sizeClasses: Record<'sm' | 'md' | 'lg', { text: string; gap: string }> = {
  sm: { text: 'text-sm', gap: 'gap-1' },
  md: { text: 'text-base', gap: 'gap-2' },
  lg: { text: 'text-xl', gap: 'gap-3' },
};

/**
 * DailyCountdown - Shows time until next daily challenge
 */
export function DailyCountdown({
  onReady,
  showSeconds = true,
  size = 'md',
  className = '',
}: DailyCountdownProps): JSX.Element {
  const [countdown, setCountdown] = useState<DailyCountdownType>(calculateCountdown);
  const [hasNotified, setHasNotified] = useState(false);

  const updateCountdown = useCallback(() => {
    const newCountdown = calculateCountdown();
    setCountdown(newCountdown);

    if (newCountdown.isReady && !hasNotified) {
      setHasNotified(true);
      onReady?.();
    }
  }, [onReady, hasNotified]);

  useEffect(() => {
    updateCountdown();
    const interval = setInterval(updateCountdown, showSeconds ? 1000 : 60000);
    return () => clearInterval(interval);
  }, [updateCountdown, showSeconds]);

  const classes = sizeClasses[size];

  if (countdown.isReady) {
    return (
      <div
        class={`daily-countdown flex items-center justify-center text-[--color-neutral-600] ${classes.text} ${className}`}
      >
        <span className="text-[--color-mode-daily-text] font-semibold">
          New challenge available!
        </span>
      </div>
    );
  }

  // Simple inline display
  if (size === 'sm') {
    return (
      <div
        class={`daily-countdown flex items-center justify-center text-[--color-neutral-600] ${classes.text} ${className}`}
      >
        <span className="mr-2 font-medium">Next in:</span>
        <span className="font-mono font-semibold text-[--color-neutral-900]">
          {formatCountdown(countdown)}
        </span>
      </div>
    );
  }

  // Block display with separate time units
  const pad = (n: number): string => n.toString().padStart(2, '0');

  return (
    <div
      class={`daily-countdown flex items-center justify-center text-[--color-neutral-600] ${classes.text} ${classes.gap} ${className}`}
    >
      <div className="flex flex-col items-center px-2 py-1 bg-[--color-neutral-100] rounded-md min-w-[48px]">
        <span className={`font-mono font-bold text-[--color-neutral-900] ${classes.text}`}>
          {pad(countdown.hours)}
        </span>
        <span className="text-[0.625rem] text-[--color-neutral-500] uppercase tracking-wider">
          Hours
        </span>
      </div>
      <span className="mx-1 font-bold text-[--color-neutral-400]">:</span>
      <div className="flex flex-col items-center px-2 py-1 bg-[--color-neutral-100] rounded-md min-w-[48px]">
        <span className={`font-mono font-bold text-[--color-neutral-900] ${classes.text}`}>
          {pad(countdown.minutes)}
        </span>
        <span className="text-[0.625rem] text-[--color-neutral-500] uppercase tracking-wider">
          Min
        </span>
      </div>
      {showSeconds && (
        <>
          <span className="mx-1 font-bold text-[--color-neutral-400]">:</span>
          <div className="flex flex-col items-center px-2 py-1 bg-[--color-neutral-100] rounded-md min-w-[48px]">
            <span className={`font-mono font-bold text-[--color-neutral-900] ${classes.text}`}>
              {pad(countdown.seconds)}
            </span>
            <span className="text-[0.625rem] text-[--color-neutral-500] uppercase tracking-wider">
              Sec
            </span>
          </div>
        </>
      )}
    </div>
  );
}

export default DailyCountdown;
