/**
 * DailyBrowsePage — Full-page Daily Challenge browse experience.
 * @module pages/DailyBrowsePage
 *
 * Proposal A: Two direct-action cards (Standard / Timed) + 7-day strip.
 * Single tap on a card starts the challenge. No intermediate "Start" button.
 *
 * Completed dates show a green checkmark on the day strip.
 *
 * Spec 132, Phase 8A — T-U04 (Redesigned)
 */

import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useMemo, useCallback } from 'preact/hooks';
import { PageLayout } from '@/components/Layout/PageLayout';
import { PageHeader } from '@/components/shared/PageHeader';
import { CalendarIcon, LightningIcon } from '@/components/shared/icons';
import { getTodaysChallenge, getAvailableChallenges, getChallenge, getPuzzleCount } from '@/services/dailyChallengeService';
import { getDailyProgress } from '@/services/progress';
import { init as initDb } from '@/services/sqliteService';
import { DayStrip, buildDayInfos } from '@/components/DailyChallenge/DayStrip';
import type { DailyChallengeMode } from '@/models/dailyChallenge';

// ============================================================================
// Types
// ============================================================================

export interface DailyBrowsePageProps {
  /** Called when user starts a challenge */
  onStartChallenge: (mode: DailyChallengeMode, date: string) => void;
  /** Called when user goes back home */
  onNavigateHome: () => void;
}

// ============================================================================
// Constants
// ============================================================================

const ACCENT = {
  text: 'var(--color-accent, var(--color-mode-daily-text))',
  light: 'var(--color-accent-light, var(--color-mode-daily-light))',
  bg: 'var(--color-accent-bg, var(--color-mode-daily-bg))',
  border: 'var(--color-accent-border, var(--color-mode-daily-border))',
} as const;

function getTodayDate(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// ============================================================================
// Component
// ============================================================================

export const DailyBrowsePage: FunctionalComponent<DailyBrowsePageProps> = ({
  onStartChallenge,
  onNavigateHome,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [standardCount, setStandardCount] = useState(0);
  const [timedCount, setTimedCount] = useState(0);
  const [todayStandardCount, setTodayStandardCount] = useState(0);
  const [todayTimedCount, setTodayTimedCount] = useState(0);
  const [availableDates, setAvailableDates] = useState<ReadonlySet<string>>(new Set());
  const [completedDates, setCompletedDates] = useState<ReadonlySet<string>>(new Set());
  const todayDate = useMemo(() => getTodayDate(), []);
  const [selectedDate, setSelectedDate] = useState(todayDate);

  // Load challenge data
  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        // Ensure SQLite DB is initialized before any queries
        await initDb();
      } catch {
        setIsLoading(false);
        return;
      }

      // Load puzzle counts (critical path — must not be blocked by date strip)
      try {
        const result = getTodaysChallenge();
        if (result.success && result.data) {
          const sc = getPuzzleCount(result.data, 'standard');
          const tc = getPuzzleCount(result.data, 'timed');
          setStandardCount(sc);
          setTimedCount(tc);
          setTodayStandardCount(sc);
          setTodayTimedCount(tc);
        }
      } catch { /* counts stay at 0 */ }

      // Load date strip data (non-critical)
      try {
        const available = getAvailableChallenges(7);
        const availSet = new Set(available.success && available.data ? available.data : [todayDate]);
        setAvailableDates(availSet);

        // Check completed dates from localStorage
        const completed = new Set<string>();
        for (const dateStr of availSet) {
          const progress = getDailyProgress(dateStr);
          if (progress.success && progress.data && progress.data.completed.length > 0) {
            completed.add(dateStr);
          }
        }
        setCompletedDates(completed);
      } catch { /* date strip stays at defaults */ }

      setIsLoading(false);
    };
    void load();
  }, [todayDate]);

  // Load puzzle counts when selected date changes
  useEffect(() => {
    if (selectedDate === todayDate) {
      // Restore today's cached counts
      setStandardCount(todayStandardCount);
      setTimedCount(todayTimedCount);
      return;
    }
    const loadDate = () => {
      try {
        const result = getChallenge(selectedDate);
        if (result.success && result.data) {
          setStandardCount(getPuzzleCount(result.data, 'standard'));
          setTimedCount(getPuzzleCount(result.data, 'timed'));
        } else {
          setStandardCount(0);
          setTimedCount(0);
        }
      } catch {
        setStandardCount(0);
        setTimedCount(0);
      }
    };
    loadDate();
  }, [selectedDate, todayDate, todayStandardCount, todayTimedCount]);

  const handleStartStandard = useCallback(() => {
    onStartChallenge('standard', selectedDate);
  }, [selectedDate, onStartChallenge]);

  const handleStartTimed = useCallback(() => {
    onStartChallenge('timed', selectedDate);
  }, [selectedDate, onStartChallenge]);

  const formattedDate = useMemo(() => {
    const d = new Date(selectedDate + 'T00:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
  }, [selectedDate]);

  const days = useMemo(
    () => buildDayInfos(7, availableDates, completedDates),
    [availableDates, completedDates],
  );

  const stats = useMemo(() => {
    const items: { label: string; value: number }[] = [];
    if (standardCount > 0) items.push({ label: 'Puzzles', value: standardCount });
    return items;
  }, [standardCount]);

  return (
    <PageLayout variant="single-column" mode="daily">
      <PageLayout.Content>
        {/* Header */}
        <PageHeader
          title="Daily Challenge"
          subtitle={formattedDate}
          icon={<CalendarIcon size={36} />}
          stats={stats}
          onBack={onNavigateHome}
          accent={ACCENT}
          testId="daily-header"
        />

        {/* Accent divider */}
        <div
          className="h-[3px]"
          style={{ backgroundColor: ACCENT.border }}
        />

        {/* Day Strip — 7-day date selector */}
        <DayStrip
          days={days}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
        />

        {/* Content */}
        <div className="mx-auto w-full max-w-5xl flex-1 p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12 text-[var(--color-text-muted)]">
              Loading today's challenge...
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* Standard Card */}
              <button
                type="button"
                onClick={handleStartStandard}
                disabled={standardCount === 0}
                className="group flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-transparent bg-[var(--color-bg-panel)] p-6 text-center shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--color-accent-border,var(--color-mode-daily-border))] hover:shadow-lg active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
                data-testid="daily-standard-card"
              >
                <div
                  className="flex h-14 w-14 items-center justify-center rounded-2xl"
                  style={{ backgroundColor: ACCENT.bg }}
                >
                  <CalendarIcon size={28} />
                </div>
                <h2 className="m-0 text-lg font-bold text-[var(--color-text-primary)]">
                  Standard
                </h2>
                <p className="m-0 text-sm text-[var(--color-text-muted)]">
                  {standardCount > 0
                    ? `${standardCount} puzzle${standardCount !== 1 ? 's' : ''}`
                    : 'No puzzles available'}
                </p>
                <p className="m-0 text-xs text-[var(--color-text-muted)]">
                  Solve at your own pace
                </p>
                <span
                  className="mt-1 rounded-lg px-4 py-1.5 text-sm font-bold uppercase tracking-wider transition-colors duration-200 group-hover:brightness-110"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  Play
                </span>
              </button>

              {/* Timed Card */}
              <button
                type="button"
                onClick={handleStartTimed}
                disabled={standardCount === 0}
                className="group flex cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-transparent bg-[var(--color-bg-panel)] p-6 text-center shadow-md transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--color-accent-border,var(--color-mode-daily-border))] hover:shadow-lg active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
                data-testid="daily-timed-card"
              >
                <div
                  className="flex h-14 w-14 items-center justify-center rounded-2xl"
                  style={{ backgroundColor: 'var(--color-warning-bg, #FFEFD0)' }}
                >
                  <LightningIcon size={28} color="var(--color-warning, #7C5800)" />
                </div>
                <h2 className="m-0 text-lg font-bold text-[var(--color-text-primary)]">
                  Timed
                </h2>
                <p className="m-0 text-sm text-[var(--color-text-muted)]">
                  {timedCount > 0
                    ? `${timedCount} puzzle${timedCount !== 1 ? 's' : ''}`
                    : 'Blitz mode'}
                </p>
                <p className="m-0 text-xs text-[var(--color-text-muted)]">
                  Race against the clock
                </p>
                <span
                  className="mt-1 rounded-lg px-4 py-1.5 text-sm font-bold uppercase tracking-wider transition-colors duration-200 group-hover:brightness-110"
                  style={{ backgroundColor: 'var(--color-warning-bg, #FFEFD0)', color: 'var(--color-warning, #7C5800)' }}
                >
                  Play
                </span>
              </button>
            </div>
          )}
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
};

export default DailyBrowsePage;
