/**
 * HomePage - Main landing page with challenge list
 * @module pages/HomePage
 *
 * Covers: US2 (Browse and Select Daily Challenges), US4 (Daily Streaks)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Page composes ChallengeList components
 * - IV. Local-First: Uses localStorage progress data
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback, useMemo } from 'preact/hooks';
import {
  ChallengeList,
  ChallengeDetail,
  type ChallengeSummary,
  type ChallengeDetailData,
} from '../components/ChallengeList';
import { StreakDisplay, MilestoneCelebration } from '../components/Streak';
import type { StreakData } from '../models/progress';
import { loadProgress } from '../services/progressTracker';
import { checkStreakResetStatus, type StreakResetInfo } from '../lib/streak';

/**
 * Props for HomePage
 */
export interface HomePageProps {
  /** Callback when a puzzle is selected */
  readonly onSelectPuzzle: (challengeId: string, puzzleId: string) => void;
  /** Challenge data loaded from manifest */
  readonly challenges: readonly ChallengeSummary[];
  /** Function to load detailed challenge data */
  readonly loadChallengeDetail?: (challengeId: string) => Promise<ChallengeDetailData | null>;
  /** Whether challenges are loading */
  readonly isLoading?: boolean;
  /** Optional CSS class */
  readonly className?: string;
  /** Callback when a milestone is reached (for celebration) */
  readonly onMilestoneReached?: (milestone: number) => void;
}

/**
 * Styles for HomePage
 */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100%',
    background: 'linear-gradient(135deg, #f5f0e8 0%, #e8e0d5 50%, #f0e8dc 100%)',
  },
  header: {
    padding: '1.5rem 1rem 1rem',
    textAlign: 'center',
    background: 'transparent',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'flex-end',
    padding: '0.5rem 1rem 0',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'baseline',
    justifyContent: 'center',
    gap: '0.75rem',
    flexWrap: 'wrap',
  },
  title: {
    margin: 0,
    fontSize: '2.5rem',
    fontWeight: '300',
    letterSpacing: '0.12em',
    color: '#2C1810',
    fontFamily: '"Cormorant Garamond", "Playfair Display", Georgia, serif',
    textTransform: 'lowercase',
  },
  titleAccent: {
    color: '#C9A66B',
    fontWeight: '300',
  },
  subtitle: {
    margin: '0.5rem 0 0',
    fontSize: '0.85rem',
    color: '#8B7355',
    fontWeight: '400',
    letterSpacing: '0.02em',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    padding: '0 0.5rem 1rem',
    maxWidth: '600px',
    margin: '0 auto',
    width: '100%',
  },
  listContainer: {
    flex: 1,
    background: '#FFFEFA',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
    overflow: 'hidden',
  },
  detailContainer: {
    flex: 1,
    background: '#FFFEFA',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
    overflow: 'hidden',
  },
};

/**
 * Get today's date in YYYY-MM-DD format
 */
function getTodayDate(): string {
  return new Date().toISOString().split('T')[0] as string;
}

/**
 * Default streak data for fallback.
 */
const DEFAULT_STREAK: StreakData = {
  currentStreak: 0,
  longestStreak: 0,
  lastPlayedDate: null,
  streakStartDate: null,
};

/**
 * HomePage - Main landing page showing challenge list
 */
export function HomePage({
  onSelectPuzzle,
  challenges,
  loadChallengeDetail,
  isLoading = false,
  className,
  onMilestoneReached,
}: HomePageProps): JSX.Element {
  const [selectedChallengeId, setSelectedChallengeId] = useState<string | null>(null);
  const [challengeDetail, setChallengeDetail] = useState<ChallengeDetailData | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [streakData, setStreakData] = useState<StreakData>(DEFAULT_STREAK);
  const [streakResetInfo, setStreakResetInfo] = useState<StreakResetInfo | null>(null);
  const [showMilestoneCelebration, setShowMilestoneCelebration] = useState<number | null>(null);

  // Load streak data on mount
  useEffect(() => {
    const result = loadProgress();
    if (result.success && result.data) {
      setStreakData(result.data.streakData);

      // Check if streak will be reset on next completion
      const resetInfo = checkStreakResetStatus(result.data.streakData);
      if (resetInfo.willReset) {
        setStreakResetInfo(resetInfo);
      }
    }
  }, []);

  // Handle milestone celebration dismissal
  const handleMilestoneDismiss = useCallback(() => {
    setShowMilestoneCelebration(null);
  }, []);

  // Callback for milestone reached (from puzzle completion)
  useEffect(() => {
    if (onMilestoneReached) {
      // This would be called from parent when puzzle completes
    }
  }, [onMilestoneReached]);

  // Sort challenges with today first, then by date descending
  const sortedChallenges = useMemo(() => {
    const today = getTodayDate();
    return [...challenges].sort((a, b) => {
      // Today first
      if (a.date === today && b.date !== today) return -1;
      if (b.date === today && a.date !== today) return 1;
      // Then by date descending
      return b.date.localeCompare(a.date);
    });
  }, [challenges]);

  // Load challenge detail when selected
  useEffect(() => {
    if (!selectedChallengeId || !loadChallengeDetail) {
      setChallengeDetail(null);
      return;
    }

    let cancelled = false;
    setIsLoadingDetail(true);

    void loadChallengeDetail(selectedChallengeId)
      .then((detail) => {
        if (!cancelled && detail) {
          setChallengeDetail(detail);
        }
      })
      .catch((error) => {
        console.error('Failed to load challenge detail:', error);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingDetail(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedChallengeId, loadChallengeDetail]);

  const handleSelectChallenge = useCallback((challengeId: string) => {
    setSelectedChallengeId(challengeId);
  }, []);

  const handleBack = useCallback(() => {
    setSelectedChallengeId(null);
    setChallengeDetail(null);
  }, []);

  const handleSelectPuzzle = useCallback(
    (puzzleId: string) => {
      if (selectedChallengeId) {
        onSelectPuzzle(selectedChallengeId, puzzleId);
      }
    },
    [selectedChallengeId, onSelectPuzzle]
  );

  // Show challenge detail if selected and loaded
  if (selectedChallengeId && challengeDetail) {
    return (
      <div style={styles.container} className={className}>
        <div style={styles.header}>
          <div style={styles.titleRow}>
            <h1 style={styles.title}>
              yen<span style={styles.titleAccent}>-</span>go
            </h1>
          </div>
        </div>
        <div style={styles.main}>
          <div style={styles.detailContainer}>
            <ChallengeDetail
              challenge={challengeDetail}
              onSelectPuzzle={handleSelectPuzzle}
              onBack={handleBack}
            />
          </div>
        </div>
      </div>
    );
  }

  // Show challenge list
  return (
    <div style={styles.container} className={className}>
      {/* Streak Display - top right */}
      <div style={styles.headerTop}>
        <StreakDisplay streakData={streakData} size="small" showWarning={true} />
      </div>
      <div style={styles.header}>
        <div style={styles.titleRow}>
          <h1 style={styles.title}>
            yen<span style={styles.titleAccent}>-</span>go
          </h1>
        </div>
        <p style={styles.subtitle}>Daily Go Puzzles</p>
      </div>
      <div style={styles.main}>
        <div style={styles.listContainer}>
          <ChallengeList
            challenges={sortedChallenges}
            selectedId={selectedChallengeId ?? undefined}
            onSelect={handleSelectChallenge}
            isLoading={isLoading || isLoadingDetail}
          />
        </div>
      </div>
      {/* Milestone celebration modal */}
      {showMilestoneCelebration !== null && (
        <MilestoneCelebration
          milestone={showMilestoneCelebration}
          onDismiss={handleMilestoneDismiss}
        />
      )}
      {/* Streak reset notification (shown once per session) */}
      {streakResetInfo && streakResetInfo.willReset && streakResetInfo.previousStreak > 0 && (
        <div
          style={{
            position: 'fixed',
            bottom: '1rem',
            left: '50%',
            transform: 'translateX(-50%)',
            background: '#FEF3C7',
            border: '1px solid #F59E0B',
            borderRadius: '8px',
            padding: '0.75rem 1.5rem',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 100,
            maxWidth: '90vw',
            textAlign: 'center',
          }}
          role="alert"
          aria-live="polite"
        >
          <p style={{ margin: 0, color: '#92400E', fontWeight: 500 }}>{streakResetInfo.message}</p>
          <button
            onClick={() => setStreakResetInfo(null)}
            style={{
              marginTop: '0.5rem',
              background: '#F59E0B',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '0.25rem 0.75rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
            }}
            type="button"
          >
            Got it
          </button>
        </div>
      )}
    </div>
  );
}

export default HomePage;
