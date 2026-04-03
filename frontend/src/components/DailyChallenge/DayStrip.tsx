/**
 * DayStrip — Horizontal date selector for daily challenges.
 * @module components/DailyChallenge/DayStrip
 *
 * Shows 7 days ending at today. Each day is a tappable pill with
 * weekday abbreviation + day number. Completed days show a checkmark.
 * Today is pre-selected.
 */

import type { FunctionalComponent } from 'preact';
import { CheckIcon } from '@/components/shared/icons';

// ============================================================================
// Types
// ============================================================================

export interface DayInfo {
  /** YYYY-MM-DD */
  date: string;
  /** Day of month (e.g., 16) */
  day: number;
  /** Abbreviated weekday (e.g., "Mon") */
  weekday: string;
  /** Whether this date has available puzzles */
  available: boolean;
  /** Whether the user has completed this day's challenge */
  completed: boolean;
  /** Whether this is today */
  isToday: boolean;
}

export interface DayStripProps {
  /** Array of 7 day objects (oldest → newest, today last) */
  days: readonly DayInfo[];
  /** Currently selected date (YYYY-MM-DD) */
  selectedDate: string;
  /** Called when a day is tapped */
  onSelectDate: (date: string) => void;
}

// ============================================================================
// Component
// ============================================================================

export const DayStrip: FunctionalComponent<DayStripProps> = ({
  days,
  selectedDate,
  onSelectDate,
}) => {
  return (
    <div
      className="flex items-center justify-center gap-1.5 overflow-x-auto px-4 py-3 sm:gap-2"
      role="listbox"
      aria-label="Select challenge date"
    >
      {days.map((day) => {
        const isSelected = day.date === selectedDate;
        const isDisabled = !day.available;

        return (
          <button
            key={day.date}
            type="button"
            role="option"
            aria-selected={isSelected}
            aria-label={`${day.weekday} ${day.day}${day.isToday ? ' (Today)' : ''}${day.completed ? ' — completed' : ''}`}
            disabled={isDisabled}
            onClick={() => onSelectDate(day.date)}
            className={`
              relative flex min-w-[3rem] cursor-pointer flex-col items-center gap-0.5 rounded-xl
              border-2 px-2 py-1.5 text-center transition-all duration-200
              ${isSelected
                ? 'border-[var(--color-accent-border,var(--color-mode-daily-border))] bg-[var(--color-accent-container,var(--color-mode-daily-bg))] shadow-sm'
                : 'border-transparent bg-[var(--color-bg-panel)] hover:bg-[var(--color-bg-secondary)]'
              }
              ${isDisabled ? 'cursor-not-allowed opacity-40' : ''}
            `}
          >
            <span className={`text-[10px] font-medium uppercase leading-none ${
              isSelected
                ? 'text-[var(--color-on-accent-container,var(--color-mode-daily-text))]'
                : 'text-[var(--color-text-muted)]'
            }`}>
              {day.weekday}
            </span>
            <span className={`text-base font-bold leading-none ${
              isSelected
                ? 'text-[var(--color-on-accent-container,var(--color-mode-daily-text))]'
                : 'text-[var(--color-text-primary)]'
            }`}>
              {day.day}
            </span>

            {/* Completed checkmark badge */}
            {day.completed && (
              <span
                className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--color-success)] text-white"
                aria-hidden="true"
              >
                <CheckIcon size={10} />
              </span>
            )}

            {/* Today indicator dot */}
            {day.isToday && !day.completed && (
              <span
                className="absolute -bottom-0.5 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full"
                style={{ backgroundColor: 'var(--color-accent-border, var(--color-mode-daily-border))' }}
                aria-hidden="true"
              />
            )}
          </button>
        );
      })}
    </div>
  );
};

// ============================================================================
// Helper: Build DayInfo array for the past N days
// ============================================================================

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;

/**
 * Build an array of DayInfo objects for the past `count` days (today inclusive).
 *
 * @param count - Number of days to show (default 7)
 * @param availableDates - Set of dates that have daily challenges
 * @param completedDates - Set of dates the user has completed
 */
export function buildDayInfos(
  count: number = 7,
  availableDates: ReadonlySet<string>,
  completedDates: ReadonlySet<string>,
): DayInfo[] {
  const today = new Date();
  const todayStr = formatDateStr(today);
  const days: DayInfo[] = [];

  for (let i = count - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = formatDateStr(d);

    days.push({
      date: dateStr,
      day: d.getDate(),
      weekday: WEEKDAYS[d.getDay()]!,
      available: availableDates.has(dateStr),
      completed: completedDates.has(dateStr),
      isToday: dateStr === todayStr,
    });
  }

  return days;
}

function formatDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
