/**
 * QualityFilter Component Tests
 * @module tests/unit/qualityFilter.test
 *
 * Tests for T043: QualityFilter component
 * Tests for T044: Quality filtering logic
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/preact';
import {
  QualityFilter,

  filterByQuality,
  getMinLevelForFilter,
  QualityFilterOption,
} from '@components/QualityFilter';

// Mock qualityConfig service
// New quality scale: level 1 = Unverified (worst), level 5 = Premium (best)
const mockConfig = {
  levels: {
    1: { name: 'Unverified', stars: 1, color: '#D3D3D3' },
    2: { name: 'Basic', stars: 2, color: '#808080' },
    3: { name: 'Standard', stars: 3, color: '#CD7F32' },
    4: { name: 'High', stars: 4, color: '#C0C0C0' },
    5: { name: 'Premium', stars: 5, color: '#FFD700' },
  },
};

vi.mock('@services/qualityConfig', () => ({
  loadQualityConfig: vi.fn(() => Promise.resolve(mockConfig)),
}));

describe('QualityFilter Component (T043)', () => {
  afterEach(() => {
    cleanup();
  });

  describe('Rendering', () => {
    it('should render with default label', () => {
      const onChange = vi.fn();
      render(<QualityFilter value="all" onChange={onChange} />);
      
      expect(screen.getByText('Quality')).toBeDefined();
    });

    it('should render with custom label', () => {
      const onChange = vi.fn();
      render(<QualityFilter value="all" onChange={onChange} label="Filter by Quality" />);
      
      expect(screen.getByText('Filter by Quality')).toBeDefined();
    });

    it('should render all filter options', () => {
      const onChange = vi.fn();
      render(<QualityFilter value="all" onChange={onChange} />);
      
      const select = screen.getByRole('combobox');
      expect(select).toBeDefined();
      
      // Check all options exist
      expect(screen.getByText('All')).toBeDefined();
      expect(screen.getByText('Premium + High')).toBeDefined();
      expect(screen.getByText('Standard+')).toBeDefined();
      expect(screen.getByText('Verified')).toBeDefined();
    });

    it('should show counts when levelCounts provided', () => {
      const onChange = vi.fn();
      // New scale: level 1 = Unverified, level 5 = Premium
      const levelCounts = { 1: 50, 2: 40, 3: 30, 4: 20, 5: 10 } as Record<1 | 2 | 3 | 4 | 5, number>;
      
      render(<QualityFilter value="all" onChange={onChange} levelCounts={levelCounts} />);
      
      // "All" should show total count (150)
      expect(screen.getByText(/All.*150/)).toBeDefined();
      // "Premium + High" should show levels 4-5 (30)
      expect(screen.getByText(/Premium \+ High.*30/)).toBeDefined();
      // "Standard+" should show levels 3-5 (60)
      expect(screen.getByText(/Standard\+.*60/)).toBeDefined();
      // "Verified" should show levels 2-5 (100)
      expect(screen.getByText(/Verified.*100/)).toBeDefined();
    });

    it('should render in compact mode', () => {
      const onChange = vi.fn();
      render(<QualityFilter value="all" onChange={onChange} compact />);
      
      // In compact mode, the label is aria-label, not visible text
      const select = screen.getByRole('combobox');
      expect(select).toBeDefined();
      expect(select.getAttribute('aria-label')).toBe('Quality');
    });

    it('should apply custom className', () => {
      const onChange = vi.fn();
      const { container } = render(
        <QualityFilter value="all" onChange={onChange} className="custom-class" />
      );
      
      expect(container.querySelector('.quality-filter.custom-class')).toBeDefined();
    });
  });

  describe('Interaction', () => {
    it('should call onChange when filter is changed', () => {
      // Use native event dispatch to properly trigger Preact's onChange
      const onChange = vi.fn();
      render(<QualityFilter value="all" onChange={onChange} />);
      
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      
      // Set the value and dispatch input event (Preact uses onInput internally)
      select.value = 'premium-high';
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      
      expect(onChange).toHaveBeenCalledWith('premium-high');
    });

    it('should reflect current value in dropdown', () => {
      const onChange = vi.fn();
      render(<QualityFilter value="standard-plus" onChange={onChange} />);
      
      const select = screen.getByRole('combobox') as HTMLSelectElement;
      expect(select.value).toBe('standard-plus');
    });
  });
});

describe('filterByQuality Function (T044)', () => {
  // New scale: level 1 = Unverified (worst), level 5 = Premium (best)
  const mockPuzzles = [
    { id: 'p1', qualityLevel: 1 }, // Unverified
    { id: 'p2', qualityLevel: 2 }, // Basic
    { id: 'p3', qualityLevel: 3 }, // Standard
    { id: 'p4', qualityLevel: 4 }, // High
    { id: 'p5', qualityLevel: 5 }, // Premium
    { id: 'p6' }, // No quality level (unverified, treated as level 1)
  ];

  it('should return all puzzles when filter is "all"', () => {
    const result = filterByQuality(mockPuzzles, 'all');
    expect(result.length).toBe(6);
  });

  it('should filter to premium-high (levels 4-5)', () => {
    const result = filterByQuality(mockPuzzles, 'premium-high');
    expect(result.length).toBe(2);
    expect(result.map((p) => p.id)).toEqual(['p4', 'p5']);
  });

  it('should filter to standard-plus (levels 3-5)', () => {
    const result = filterByQuality(mockPuzzles, 'standard-plus');
    expect(result.length).toBe(3);
    expect(result.map((p) => p.id)).toEqual(['p3', 'p4', 'p5']);
  });

  it('should filter to verified (levels 2-5)', () => {
    const result = filterByQuality(mockPuzzles, 'verified');
    expect(result.length).toBe(4);
    expect(result.map((p) => p.id)).toEqual(['p2', 'p3', 'p4', 'p5']);
  });

  it('should treat missing qualityLevel as level 1 (unverified)', () => {
    const result = filterByQuality(mockPuzzles, 'verified');
    // p6 has no qualityLevel, treated as level 1 (Unverified), should be excluded
    expect(result.find((p) => p.id === 'p6')).toBeUndefined();
  });

  it('should handle empty array', () => {
    const result = filterByQuality([], 'premium-high');
    expect(result).toEqual([]);
  });

  it('should handle array with all same level', () => {
    // Level 3 = Standard
    const sameLevelPuzzles = [
      { id: 'a', qualityLevel: 3 },
      { id: 'b', qualityLevel: 3 },
      { id: 'c', qualityLevel: 3 },
    ];
    
    // premium-high requires level 4-5, so level 3 puzzles excluded
    const premiumHigh = filterByQuality(sameLevelPuzzles, 'premium-high');
    expect(premiumHigh.length).toBe(0);
    
    // standard-plus requires level 3-5, so level 3 puzzles included
    const standardPlus = filterByQuality(sameLevelPuzzles, 'standard-plus');
    expect(standardPlus.length).toBe(3);
  });
});

describe('getMinLevelForFilter Function', () => {
  // Note: With new scale (1=worst, 5=best), filters return MIN level threshold
  // premium-high: level >= 4, standard-plus: level >= 3, verified: level >= 2
  it('should return null for "all" filter', () => {
    expect(getMinLevelForFilter('all')).toBeNull();
  });

  it('should return 4 for "premium-high" filter', () => {
    expect(getMinLevelForFilter('premium-high')).toBe(4);
  });

  it('should return 3 for "standard-plus" filter', () => {
    expect(getMinLevelForFilter('standard-plus')).toBe(3);
  });

  it('should return 2 for "verified" filter', () => {
    expect(getMinLevelForFilter('verified')).toBe(2);
  });

  it('should return the level directly for numeric level filter', () => {
    expect(getMinLevelForFilter(1 as QualityFilterOption)).toBe(1);
    expect(getMinLevelForFilter(3 as QualityFilterOption)).toBe(3);
    expect(getMinLevelForFilter(5 as QualityFilterOption)).toBe(5);
  });
});
