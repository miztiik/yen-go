/**
 * AchievementList Component Integration Tests
 * @module tests/integration/achievementList
 *
 * Tests for achievement list display, filtering, and notifications (FR-042 to FR-044)
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/preact';
import {
  AchievementList,
  AchievementToast,
  AchievementToastContainer,
} from '../../src/components/Progress/AchievementList';
import type { UserProgress, Achievement } from '../../src/models/progress';
import type { AchievementNotification, AchievementId } from '../../src/models/achievement';
import { ACHIEVEMENT_DEFINITIONS, getAchievementDefinition } from '../../src/models/achievement';

// Mock user progress with some achievements
const createMockProgress = (achievements: Achievement[] = []): UserProgress => ({
  version: 1,
  completedPuzzles: [],
  unlockedLevels: ['level-1'],
  statistics: {
    totalSolved: achievements.length > 0 ? 10 : 0,
    totalAttempts: achievements.length > 0 ? 15 : 0,
    perfectSolves: 0,
    hintsUsed: 0,
    totalTimeMs: 0,
    averageTimeMs: 0,
    byDifficulty: {
      beginner: { solved: 5, avgTimeMs: 0, perfectSolves: 0 },
      intermediate: { solved: 3, avgTimeMs: 0, perfectSolves: 0 },
      advanced: { solved: 2, avgTimeMs: 0, perfectSolves: 0 },
    },
  },
  currentStreak: 0,
  longestStreak: 0,
  achievements,
  settings: {
    soundEnabled: true,
    notificationsEnabled: true,
    theme: 'system',
  },
});

describe('AchievementList Component', () => {
  afterEach(cleanup);

  describe('Rendering', () => {
    it('should render achievement list container', () => {
      render(<AchievementList progress={null} />);
      expect(screen.getByRole('region', { name: /achievements/i })).toBeDefined();
    });

    it('should display achievement summary with totals', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      // Should show total count
      const totalCount = ACHIEVEMENT_DEFINITIONS.length;
      expect(screen.getByText(totalCount.toString())).toBeDefined();
      expect(screen.getByText('Total')).toBeDefined();
      expect(screen.getByText('Unlocked')).toBeDefined();
    });

    it('should display all category filter buttons', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      expect(screen.getByRole('tab', { name: /all/i })).toBeDefined();
      expect(screen.getByRole('tab', { name: /puzzles/i })).toBeDefined();
      expect(screen.getByRole('tab', { name: /streaks/i })).toBeDefined();
      expect(screen.getByRole('tab', { name: /rush/i })).toBeDefined();
      expect(screen.getByRole('tab', { name: /mastery/i })).toBeDefined();
      expect(screen.getByRole('tab', { name: /collection/i })).toBeDefined();
      expect(screen.getByRole('tab', { name: /special/i })).toBeDefined();
    });

    it('should render all achievements from definitions', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      // Check that some key achievements are rendered
      expect(screen.getByText('First Steps')).toBeDefined();
      expect(screen.getByText('Weekly Warrior')).toBeDefined();
      expect(screen.getByText('Century Solver')).toBeDefined();
    });

    it('should apply custom className', () => {
      render(<AchievementList progress={createMockProgress()} className="custom-class" />);
      const container = screen.getByRole('region', { name: /achievements/i });
      expect(container.className).toContain('custom-class');
    });
  });

  describe('Achievement Progress (FR-042, FR-043)', () => {
    it('should display unlocked achievement with unlock date', () => {
      const progress = createMockProgress([
        {
          id: 'first_puzzle',
          name: 'First Steps',
          description: 'Solve your first puzzle',
          unlockedAt: '2024-01-15T10:30:00Z',
          progress: 1,
          target: 1,
        },
      ]);

      render(<AchievementList progress={progress} />);
      
      // Check for unlock date display (using getAllByText since "Unlocked" appears in summary too)
      const unlockElements = screen.getAllByText(/unlocked/i);
      expect(unlockElements.length).toBeGreaterThan(1); // Summary + achievement card
    });

    it('should display locked achievement with progress bar', () => {
      const progress = createMockProgress([]);
      render(<AchievementList progress={progress} />);
      
      // Check for progress bars on locked achievements
      const progressBars = screen.getAllByRole('progressbar');
      expect(progressBars.length).toBeGreaterThan(0);
    });

    it('should show correct progress percentage', () => {
      const progress = createMockProgress([
        {
          id: 'hundred_puzzles',
          name: 'Century Solver',
          description: 'Solve 100 puzzles',
          progress: 50,
          target: 100,
        },
      ]);

      render(<AchievementList progress={progress} />);
      
      // Should show 50/100 progress
      expect(screen.getByText('50 / 100')).toBeDefined();
    });

    it('should sort unlocked achievements first', () => {
      const progress = createMockProgress([
        {
          id: 'hundred_puzzles',
          name: 'Century Solver',
          description: 'Solve 100 puzzles',
          unlockedAt: '2024-01-15T10:30:00Z',
          progress: 100,
          target: 100,
        },
      ]);

      render(<AchievementList progress={progress} />);
      
      const cards = screen.getAllByRole('button');
      // Filter to just achievement cards (not category buttons)
      const achievementCards = cards.filter(c => c.className.includes('achievement-card'));
      // First card should be unlocked
      expect(achievementCards[0].className).toContain('unlocked');
    });

    it('should display tier badges', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      // Check for tier badges
      expect(screen.getAllByText('Bronze').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Silver').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Gold').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0);
    });

    it('should display emoji icon for unlocked achievements', () => {
      const progress = createMockProgress([
        {
          id: 'first_puzzle',
          name: 'First Steps',
          description: 'Solve your first puzzle',
          unlockedAt: '2024-01-15T10:30:00Z',
          progress: 1,
          target: 1,
        },
      ]);

      render(<AchievementList progress={progress} />);
      
      // Should show the achievement icon
      expect(screen.getByText('🎯')).toBeDefined();
    });

    it('should display lock icon for locked achievements', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      // Should show lock icons for locked achievements
      const locks = screen.getAllByText('🔒');
      expect(locks.length).toBeGreaterThan(0);
    });
  });

  describe('Category Filtering', () => {
    it('should filter by puzzle category', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      const puzzlesTab = screen.getByRole('tab', { name: /puzzles/i });
      fireEvent.click(puzzlesTab);
      
      // Should show puzzle achievements
      expect(screen.getByText('First Steps')).toBeDefined();
      expect(screen.getByText('Century Solver')).toBeDefined();
    });

    it('should filter by streaks category', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      const streaksTab = screen.getByRole('tab', { name: /streaks/i });
      fireEvent.click(streaksTab);
      
      // Should show streak achievements
      expect(screen.getByText('Weekly Warrior')).toBeDefined();
      expect(screen.getByText('Monthly Master')).toBeDefined();
    });

    it('should filter by rush category', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      const rushTab = screen.getByRole('tab', { name: /rush/i });
      fireEvent.click(rushTab);
      
      // Should show rush achievements
      expect(screen.getByText('Rush Hour')).toBeDefined();
      expect(screen.getByText('Rush Champion')).toBeDefined();
    });

    it('should update active tab styling', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      const allTab = screen.getByRole('tab', { name: /all/i });
      expect(allTab.getAttribute('aria-selected')).toBe('true');
      expect(allTab.className).toContain('active');
      
      const puzzlesTab = screen.getByRole('tab', { name: /puzzles/i });
      fireEvent.click(puzzlesTab);
      
      expect(puzzlesTab.getAttribute('aria-selected')).toBe('true');
      expect(puzzlesTab.className).toContain('active');
      expect(allTab.getAttribute('aria-selected')).toBe('false');
    });

    it('should return to all achievements when All is clicked', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      // First filter to puzzles
      const puzzlesTab = screen.getByRole('tab', { name: /puzzles/i });
      fireEvent.click(puzzlesTab);
      
      // Then click All
      const allTab = screen.getByRole('tab', { name: /all/i });
      fireEvent.click(allTab);
      
      // Should show all achievements again
      expect(screen.getByText('Weekly Warrior')).toBeDefined(); // Streaks
      expect(screen.getByText('First Steps')).toBeDefined(); // Puzzles
    });
  });

  describe('Achievement Click Handler', () => {
    it('should call onAchievementClick when achievement is clicked', () => {
      const handleClick = vi.fn();
      render(
        <AchievementList
          progress={createMockProgress()}
          onAchievementClick={handleClick}
        />
      );
      
      const firstSteps = screen.getByText('First Steps').closest('[role="button"]');
      fireEvent.click(firstSteps!);
      
      expect(handleClick).toHaveBeenCalledWith('first_puzzle');
    });

    it('should support keyboard navigation', () => {
      const handleClick = vi.fn();
      render(
        <AchievementList
          progress={createMockProgress()}
          onAchievementClick={handleClick}
        />
      );
      
      const firstSteps = screen.getByText('First Steps').closest('[role="button"]');
      fireEvent.keyDown(firstSteps!, { key: 'Enter' });
      
      expect(handleClick).toHaveBeenCalledWith('first_puzzle');
    });

    it('should support space key for activation', () => {
      const handleClick = vi.fn();
      render(
        <AchievementList
          progress={createMockProgress()}
          onAchievementClick={handleClick}
        />
      );
      
      const firstSteps = screen.getByText('First Steps').closest('[role="button"]');
      fireEvent.keyDown(firstSteps!, { key: ' ' });
      
      expect(handleClick).toHaveBeenCalledWith('first_puzzle');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA roles', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      expect(screen.getByRole('region', { name: /achievements/i })).toBeDefined();
      expect(screen.getByRole('region', { name: /achievement summary/i })).toBeDefined();
      expect(screen.getByRole('tablist', { name: /achievement categories/i })).toBeDefined();
      expect(screen.getByRole('list')).toBeDefined();
    });

    it('should have focusable achievement cards', () => {
      render(<AchievementList progress={createMockProgress()} />);
      
      const buttons = screen.getAllByRole('button');
      const cards = buttons.filter(b => b.className.includes('achievement-card'));
      cards.forEach((card) => {
        expect(card.getAttribute('tabindex')).toBe('0');
      });
    });

    it('should announce achievement status in card label', () => {
      const progress = createMockProgress([
        {
          id: 'first_puzzle',
          name: 'First Steps',
          description: 'Solve your first puzzle',
          unlockedAt: '2024-01-15T10:30:00Z',
          progress: 1,
          target: 1,
        },
      ]);

      render(<AchievementList progress={progress} />);
      
      const card = screen.getByRole('button', { name: /first steps.*unlocked/i });
      expect(card).toBeDefined();
    });
  });
});

describe('AchievementToast Component (FR-044)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  const createNotification = (id: AchievementId = 'first_puzzle'): AchievementNotification => {
    const definition = getAchievementDefinition(id)!;
    return {
      achievement: definition,
      unlockedAt: new Date().toISOString(),
      isNew: true,
    };
  };

  it('should render toast with achievement info', () => {
    const notification = createNotification('first_puzzle');
    const onDismiss = vi.fn();

    render(<AchievementToast notification={notification} onDismiss={onDismiss} />);

    expect(screen.getByRole('alert')).toBeDefined();
    expect(screen.getByText('🎉 Achievement Unlocked!')).toBeDefined();
    expect(screen.getByText('First Steps')).toBeDefined();
    expect(screen.getByText('Solve your first puzzle')).toBeDefined();
    expect(screen.getByText('🎯')).toBeDefined();
  });

  it('should auto-dismiss after timeout', () => {
    const notification = createNotification();
    const onDismiss = vi.fn();

    render(
      <AchievementToast
        notification={notification}
        onDismiss={onDismiss}
        autoDismissMs={5000}
      />
    );

    expect(onDismiss).not.toHaveBeenCalled();

    vi.advanceTimersByTime(5000);

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('should dismiss immediately when X button clicked', () => {
    const notification = createNotification();
    const onDismiss = vi.fn();

    render(<AchievementToast notification={notification} onDismiss={onDismiss} />);

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButton);

    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('should clear timeout when manually dismissed', () => {
    const notification = createNotification();
    const onDismiss = vi.fn();

    render(
      <AchievementToast
        notification={notification}
        onDismiss={onDismiss}
        autoDismissMs={5000}
      />
    );

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButton);

    // Should only be called once (from manual dismiss, not timer)
    vi.advanceTimersByTime(5000);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it('should not auto-dismiss if autoDismissMs is 0', () => {
    const notification = createNotification();
    const onDismiss = vi.fn();

    render(
      <AchievementToast
        notification={notification}
        onDismiss={onDismiss}
        autoDismissMs={0}
      />
    );

    vi.advanceTimersByTime(10000);
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it('should have proper tier styling', () => {
    const notification = createNotification('thousand_puzzles'); // Platinum tier
    const onDismiss = vi.fn();

    const { container } = render(
      <AchievementToast notification={notification} onDismiss={onDismiss} />
    );

    const toast = container.querySelector('.achievement-toast');
    expect(toast).toBeDefined();
    expect(toast?.getAttribute('style')).toContain('--tier-color');
  });
});

describe('AchievementToastContainer', () => {
  afterEach(cleanup);

  const createNotifications = (): AchievementNotification[] => [
    {
      achievement: getAchievementDefinition('first_puzzle')!,
      unlockedAt: new Date().toISOString(),
      isNew: true,
    },
    {
      achievement: getAchievementDefinition('streak_7')!,
      unlockedAt: new Date().toISOString(),
      isNew: true,
    },
  ];

  it('should render nothing when no notifications', () => {
    const { container } = render(
      <AchievementToastContainer notifications={[]} onDismiss={() => {}} />
    );

    expect(container.querySelector('.achievement-toast-container')).toBeNull();
  });

  it('should render multiple toasts', () => {
    const notifications = createNotifications();
    const onDismiss = vi.fn();

    render(
      <AchievementToastContainer notifications={notifications} onDismiss={onDismiss} />
    );

    expect(screen.getAllByRole('alert')).toHaveLength(2);
    expect(screen.getByText('First Steps')).toBeDefined();
    expect(screen.getByText('Weekly Warrior')).toBeDefined();
  });

  it('should call onDismiss with correct achievement ID', () => {
    const notifications = createNotifications();
    const onDismiss = vi.fn();

    render(
      <AchievementToastContainer notifications={notifications} onDismiss={onDismiss} />
    );

    const dismissButtons = screen.getAllByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButtons[0]);

    expect(onDismiss).toHaveBeenCalledWith('first_puzzle');
  });

  it('should have proper container styling', () => {
    const notifications = createNotifications();
    const { container } = render(
      <AchievementToastContainer notifications={notifications} onDismiss={() => {}} />
    );

    const toastContainer = container.querySelector('.achievement-toast-container');
    expect(toastContainer).toBeDefined();
    expect(toastContainer?.getAttribute('aria-label')).toBe('Achievement notifications');
  });
});

describe('Integration: AchievementList with Notifications', () => {
  afterEach(cleanup);

  it('should display notifications passed to AchievementList', () => {
    const notification: AchievementNotification = {
      achievement: getAchievementDefinition('first_puzzle')!,
      unlockedAt: new Date().toISOString(),
      isNew: true,
    };

    render(
      <AchievementList
        progress={createMockProgress()}
        newAchievements={[notification]}
        onNotificationDismiss={() => {}}
      />
    );

    // Both the list item and toast should be present
    expect(screen.getByRole('alert')).toBeDefined();
    expect(screen.getByText('🎉 Achievement Unlocked!')).toBeDefined();
  });

  it('should call onNotificationDismiss when toast is dismissed', () => {
    const notification: AchievementNotification = {
      achievement: getAchievementDefinition('first_puzzle')!,
      unlockedAt: new Date().toISOString(),
      isNew: true,
    };
    const onDismiss = vi.fn();

    render(
      <AchievementList
        progress={createMockProgress()}
        newAchievements={[notification]}
        onNotificationDismiss={onDismiss}
      />
    );

    const dismissButton = screen.getByRole('button', { name: /dismiss/i });
    fireEvent.click(dismissButton);

    expect(onDismiss).toHaveBeenCalledWith('first_puzzle');
  });
});

describe('Hidden Achievements', () => {
  afterEach(cleanup);

  it('should show ??? for hidden locked achievements', () => {
    // comeback_kid is a hidden achievement
    render(<AchievementList progress={createMockProgress()} />);
    
    const specialTab = screen.getByRole('tab', { name: /special/i });
    fireEvent.click(specialTab);
    
    // Hidden achievements should show ??? when locked
    expect(screen.getByText('???')).toBeDefined();
  });

  it('should reveal hidden achievement name when unlocked', () => {
    const progress = createMockProgress([
      {
        id: 'comeback_kid',
        name: 'Comeback Kid',
        description: 'Return after breaking a streak and start a new one',
        unlockedAt: '2024-01-15T10:30:00Z',
        progress: 1,
        target: 1,
      },
    ]);

    render(<AchievementList progress={progress} />);
    
    const specialTab = screen.getByRole('tab', { name: /special/i });
    fireEvent.click(specialTab);
    
    // Should show the real name now
    expect(screen.getByText('Comeback Kid')).toBeDefined();
  });
});
