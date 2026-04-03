/**
 * RandomPage Tests
 * @module tests/unit/RandomPage.test
 *
 * Spec 129, Phase 10 — T089
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { RandomPage, type RandomPageProps } from '@/pages/RandomPage';

vi.mock('@/services/puzzleQueryService', () => ({
  getFilterCounts: () => ({ levels: {}, tags: {}, collections: {}, depthPresets: {} }),
}));

describe('RandomPage', () => {
  const defaultProps: RandomPageProps = {
    onSelectRandomPuzzle: vi.fn(),
    onNavigateHome: vi.fn(),
  };

  beforeEach(() => {
    // Clear localStorage mock
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null);
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders page title', () => {
    render(<RandomPage {...defaultProps} />);
    expect(screen.getByText('Random')).toBeDefined();
  });

  it('renders random page with test id', () => {
    render(<RandomPage {...defaultProps} />);
    expect(screen.getByTestId('random-page')).toBeDefined();
  });

  it('renders category filter bar', () => {
    render(<RandomPage {...defaultProps} />);
    expect(screen.getByTestId('category-filter')).toBeDefined();
  });

  it('renders stats bar', () => {
    render(<RandomPage {...defaultProps} />);
    expect(screen.getByTestId('page-stats')).toBeDefined();
  });

  it('renders random button', () => {
    render(<RandomPage {...defaultProps} />);
    expect(screen.getByTestId('random-button')).toBeDefined();
  });

  it('renders back button', () => {
    render(<RandomPage {...defaultProps} />);
    // Back button is now in PageHeader, find by text
    expect(screen.getByText('Back')).toBeDefined();
  });

  it('calls onNavigateHome when back button clicked', () => {
    render(<RandomPage {...defaultProps} />);
    const backButton = screen.getByText('Back');
    fireEvent.click(backButton);
    expect(defaultProps.onNavigateHome).toHaveBeenCalled();
  });

  it('calls onSelectRandomPuzzle when random button clicked', () => {
    render(<RandomPage {...defaultProps} />);
    const randomButton = screen.getByTestId('random-button');
    fireEvent.click(randomButton);
    expect(defaultProps.onSelectRandomPuzzle).toHaveBeenCalled();
  });

  it('filters to beginner levels when Beginner category selected', () => {
    render(<RandomPage {...defaultProps} />);
    const beginnerFilter = screen.getByTestId('category-filter-beginner');
    fireEvent.click(beginnerFilter);

    // Should show only beginner levels (novice, beginner, elementary)
    expect(screen.getByTestId('level-card-novice')).toBeDefined();
    expect(screen.getByTestId('level-card-beginner')).toBeDefined();
    expect(screen.getByTestId('level-card-elementary')).toBeDefined();

    // Should not show advanced levels
    expect(screen.queryByTestId('level-card-expert')).toBeNull();
    expect(screen.queryByTestId('level-card-high-dan')).toBeNull();
  });

  it('filters to advanced levels when Advanced category selected', () => {
    render(<RandomPage {...defaultProps} />);
    const advancedFilter = screen.getByTestId('category-filter-advanced');
    fireEvent.click(advancedFilter);

    // Should show only advanced levels
    expect(screen.getByTestId('level-card-low-dan')).toBeDefined();
    expect(screen.getByTestId('level-card-high-dan')).toBeDefined();
    expect(screen.getByTestId('level-card-expert')).toBeDefined();

    // Should not show beginner levels
    expect(screen.queryByTestId('level-card-novice')).toBeNull();
    expect(screen.queryByTestId('level-card-beginner')).toBeNull();
  });

  it('shows all 9 levels when All Levels selected', () => {
    render(<RandomPage {...defaultProps} />);
    const allFilter = screen.getByTestId('category-filter-all');
    fireEvent.click(allFilter);

    // Should show all levels
    expect(screen.getByTestId('level-card-novice')).toBeDefined();
    expect(screen.getByTestId('level-card-beginner')).toBeDefined();
    expect(screen.getByTestId('level-card-elementary')).toBeDefined();
    expect(screen.getByTestId('level-card-intermediate')).toBeDefined();
    expect(screen.getByTestId('level-card-upper-intermediate')).toBeDefined();
    expect(screen.getByTestId('level-card-advanced')).toBeDefined();
    expect(screen.getByTestId('level-card-low-dan')).toBeDefined();
    expect(screen.getByTestId('level-card-high-dan')).toBeDefined();
    expect(screen.getByTestId('level-card-expert')).toBeDefined();
  });

  it('calls onSelectRandomPuzzle when level card clicked', () => {
    render(<RandomPage {...defaultProps} />);
    const beginnerCard = screen.getByTestId('level-card-beginner');
    fireEvent.click(beginnerCard);
    expect(defaultProps.onSelectRandomPuzzle).toHaveBeenCalled();
  });

  it('displays session stats in stats bar', () => {
    render(<RandomPage {...defaultProps} />);

    // Stats are now rendered in PageHeader via page-stats testId
    const statsBar = screen.getByTestId('page-stats');
    expect(statsBar.textContent).toContain('Puzzles');
    expect(statsBar.textContent).toContain('Correct');
    expect(statsBar.textContent).toContain('Accuracy');
  });

  it('shows level filter options for selected category', () => {
    render(<RandomPage {...defaultProps} />);
    
    // Select intermediate category
    const intermediateFilter = screen.getByTestId('category-filter-intermediate');
    fireEvent.click(intermediateFilter);

    // Check level filter has the right options
    const levelFilter = screen.getByTestId('level-filter');
    expect(levelFilter).toBeDefined();
    expect(screen.getByTestId('level-filter-any')).toBeDefined();
    expect(screen.getByTestId('level-filter-intermediate')).toBeDefined();
    expect(screen.getByTestId('level-filter-upper-intermediate')).toBeDefined();
    expect(screen.getByTestId('level-filter-advanced')).toBeDefined();
  });
});
