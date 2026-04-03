/**
 * Unit tests for shared components (T075b).
 *
 * Tests:
 * - PuzzleCollectionCard: render, progress, empty state, keyboard activation
 * - StatsBar: render with various stat values
 * - FilterBar: pill selection, ARIA, keyboard navigation
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { PuzzleCollectionCard } from '@/components/shared/PuzzleCollectionCard';
import { StatsBar } from '@/components/shared/StatsBar';
import { FilterBar } from '@/components/shared/FilterBar';
import { FilterDropdown } from '@/components/shared/FilterDropdown';

// ============================================================================
// PuzzleCollectionCard
// ============================================================================

describe('PuzzleCollectionCard', () => {
  it('renders title', () => {
    const { getByText } = render(
      <PuzzleCollectionCard title="Snapback" />
    );
    expect(getByText('Snapback')).toBeTruthy();
  });

  it('renders subtitle if provided', () => {
    const { getByText } = render(
      <PuzzleCollectionCard title="Snapback" subtitle="Tesuji pattern" />
    );
    expect(getByText('Tesuji pattern')).toBeTruthy();
  });

  it('renders tags limited to 3 with overflow indicator', () => {
    const { getByText } = render(
      <PuzzleCollectionCard
        title="Mixed"
        tags={['ko', 'ladder', 'net', 'snapback', 'connect']}
      />
    );
    expect(getByText('ko')).toBeTruthy();
    expect(getByText('ladder')).toBeTruthy();
    expect(getByText('net')).toBeTruthy();
    expect(getByText('+2')).toBeTruthy();
  });

  it('renders progress bar with correct fraction', () => {
    const { getByText } = render(
      <PuzzleCollectionCard
        title="Life and Death"
        progress={{ completed: 5, total: 20 }}
      />
    );
    expect(getByText('5 of 20 solved')).toBeTruthy();
  });

  it('renders empty state when progress total is 0', () => {
    const { getByText } = render(
      <PuzzleCollectionCard
        title="Empty"
        progress={{ completed: 0, total: 0 }}
      />
    );
    expect(getByText('Ready to begin')).toBeTruthy();
  });

  it('renders mastery badge', () => {
    const { getByText } = render(
      <PuzzleCollectionCard title="Ladder" mastery="proficient" />
    );
    expect(getByText('Proficient')).toBeTruthy();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    const { getByRole } = render(
      <PuzzleCollectionCard title="Click me" onClick={onClick} />
    );
    fireEvent.click(getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('activates on Enter key', () => {
    const onClick = vi.fn();
    const { getByRole } = render(
      <PuzzleCollectionCard title="Enter me" onClick={onClick} />
    );
    fireEvent.keyDown(getByRole('button'), { key: 'Enter' });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('activates on Space key', () => {
    const onClick = vi.fn();
    const { getByRole } = render(
      <PuzzleCollectionCard title="Space me" onClick={onClick} />
    );
    fireEvent.keyDown(getByRole('button'), { key: ' ' });
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('has accessible label with progress info', () => {
    const { getByRole } = render(
      <PuzzleCollectionCard
        title="Test"
        progress={{ completed: 3, total: 10 }}
        onClick={() => {}}
      />
    );
    const btn = getByRole('button');
    expect(btn.getAttribute('aria-label')).toContain('3 of 10 solved');
  });
});

// ============================================================================
// StatsBar
// ============================================================================

describe('StatsBar', () => {
  it('renders stat values and labels', () => {
    const { getByText } = render(
      <StatsBar
        stats={[
          { value: 42, label: 'Techniques' },
          { value: '85%', label: 'Accuracy' },
        ]}
      />
    );
    expect(getByText('42')).toBeTruthy();
    expect(getByText('Techniques')).toBeTruthy();
    expect(getByText('85%')).toBeTruthy();
    expect(getByText('Accuracy')).toBeTruthy();
  });

  it('renders nothing when stats are empty and no children', () => {
    const { container } = render(<StatsBar stats={[]} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders with testId', () => {
    const { container } = render(
      <StatsBar
        stats={[{ value: 1, label: 'Test' }]}
        testId="my-stats"
      />
    );
    expect(container.querySelector('[data-testid="my-stats"]')).toBeTruthy();
  });
});

// ============================================================================
// FilterBar
// ============================================================================

describe('FilterBar', () => {
  const options = [
    { id: 'all', label: 'All' },
    { id: 'tesuji', label: 'Tesuji' },
    { id: 'technique', label: 'Techniques' },
  ];

  it('renders all pill options', () => {
    const { getByText } = render(
      <FilterBar label="Category" options={options} selected="all" onChange={() => {}} />
    );
    expect(getByText('All')).toBeTruthy();
    expect(getByText('Tesuji')).toBeTruthy();
    expect(getByText('Techniques')).toBeTruthy();
  });

  it('marks active pill with aria-checked', () => {
    const { getByText } = render(
      <FilterBar label="Category" options={options} selected="tesuji" onChange={() => {}} />
    );
    expect(getByText('Tesuji').getAttribute('aria-checked')).toBe('true');
    expect(getByText('All').getAttribute('aria-checked')).toBe('false');
  });

  it('calls onChange when pill is clicked', () => {
    const onChange = vi.fn();
    const { getByText } = render(
      <FilterBar label="Category" options={options} selected="all" onChange={onChange} />
    );
    fireEvent.click(getByText('Tesuji'));
    expect(onChange).toHaveBeenCalledWith('tesuji');
  });

  it('calls onChange on Enter key', () => {
    const onChange = vi.fn();
    const { getByText } = render(
      <FilterBar label="Category" options={options} selected="all" onChange={onChange} />
    );
    fireEvent.keyDown(getByText('Techniques'), { key: 'Enter' });
    expect(onChange).toHaveBeenCalledWith('technique');
  });

  it('calls onChange on Space key', () => {
    const onChange = vi.fn();
    const { getByText } = render(
      <FilterBar label="Category" options={options} selected="all" onChange={onChange} />
    );
    fireEvent.keyDown(getByText('All'), { key: ' ' });
    expect(onChange).toHaveBeenCalledWith('all');
  });

  it('renders with radiogroup role and aria-label', () => {
    const { container } = render(
      <FilterBar label="Filter by tag" options={options} selected="all" onChange={() => {}} />
    );
    const group = container.querySelector('[role="radiogroup"]');
    expect(group).toBeTruthy();
    expect(group!.getAttribute('aria-label')).toBe('Filter by tag');
  });

  it('renders test IDs on pills', () => {
    const { container } = render(
      <FilterBar
        label="Category"
        options={options}
        selected="all"
        onChange={() => {}}
        testId="cat"
      />
    );
    expect(container.querySelector('[data-testid="cat-all"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="cat-tesuji"]')).toBeTruthy();
  });

  // F17: Disabled pill behavior (count=0)
  describe('disabled pills (count=0)', () => {
    const optionsWithZero = [
      { id: 'all', label: 'All', count: 10 },
      { id: 'ko', label: 'Ko', count: 0 },
      { id: 'ladder', label: 'Ladder', count: 5 },
    ];

    it('does not call onChange when disabled pill is clicked', () => {
      const onChange = vi.fn();
      const { getByText } = render(
        <FilterBar label="Tag" options={optionsWithZero} selected="all" onChange={onChange} />
      );
      fireEvent.click(getByText('Ko'));
      expect(onChange).not.toHaveBeenCalled();
    });

    it('renders disabled pill with disabled attribute', () => {
      const { getByText } = render(
        <FilterBar label="Tag" options={optionsWithZero} selected="all" onChange={() => {}} />
      );
      expect((getByText('Ko') as HTMLButtonElement).disabled).toBe(true);
    });

    it('skips disabled pills in arrow key navigation', () => {
      const onChange = vi.fn();
      const { getByText } = render(
        <FilterBar label="Tag" options={optionsWithZero} selected="all" onChange={onChange} />
      );
      // Press ArrowRight from 'All' — should skip 'Ko' (count=0) and land on 'Ladder'
      fireEvent.keyDown(getByText('All'), { key: 'ArrowRight' });
      expect(onChange).toHaveBeenCalledWith('ladder');
    });
  });
});

// ============================================================================
// FilterDropdown
// ============================================================================

describe('FilterDropdown', () => {
  const groups = [
    {
      label: 'Objectives',
      options: [
        { id: '10', label: 'Life and Death', count: 42 },
        { id: '11', label: 'Capture', count: 0 },
      ],
    },
    {
      label: 'Tesuji',
      options: [
        { id: '30', label: 'Ladder', count: 15 },
      ],
    },
  ];

  it('renders trigger with placeholder text when nothing selected', () => {
    const { getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={() => {}} />
    );
    expect(getByText('All Tags')).toBeTruthy();
  });

  it('renders trigger with selected option label', () => {
    const { getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected="10" onChange={() => {}} />
    );
    expect(getByText('Life and Death (42)')).toBeTruthy();
  });

  it('opens listbox panel on trigger click', () => {
    const { getByLabelText, container } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={() => {}} testId="dd" />
    );
    fireEvent.click(getByLabelText('Tag'));
    expect(container.querySelector('[role="listbox"]')).toBeTruthy();
  });

  it('shows category group headers in open panel', () => {
    const { getByLabelText, getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={() => {}} />
    );
    fireEvent.click(getByLabelText('Tag'));
    expect(getByText('Objectives')).toBeTruthy();
    expect(getByText('Tesuji')).toBeTruthy();
  });

  it('calls onChange with null when "All" is clicked', () => {
    const onChange = vi.fn();
    const { getByLabelText, getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected="10" onChange={onChange} />
    );
    fireEvent.click(getByLabelText('Tag'));
    fireEvent.click(getByText('All'));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('calls onChange with option ID when option is clicked', () => {
    const onChange = vi.fn();
    const { getByLabelText, getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={onChange} />
    );
    fireEvent.click(getByLabelText('Tag'));
    fireEvent.click(getByText('Ladder'));
    expect(onChange).toHaveBeenCalledWith('30');
  });

  it('does not call onChange when disabled option (count=0) is clicked', () => {
    const onChange = vi.fn();
    const { getByLabelText, getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={onChange} />
    );
    fireEvent.click(getByLabelText('Tag'));
    fireEvent.click(getByText('Capture'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('closes on Escape key', () => {
    const { getByLabelText, container } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={() => {}} />
    );
    fireEvent.click(getByLabelText('Tag'));
    expect(container.querySelector('[role="listbox"]')).toBeTruthy();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(container.querySelector('[role="listbox"]')).toBeFalsy();
  });

  it('sets aria-expanded on trigger', () => {
    const { getByLabelText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={() => {}} />
    );
    const trigger = getByLabelText('Tag');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(trigger);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
  });

  it('marks disabled option with aria-disabled', () => {
    const { getByLabelText, getByText } = render(
      <FilterDropdown label="Tag" placeholder="All Tags" groups={groups} selected={null} onChange={() => {}} />
    );
    fireEvent.click(getByLabelText('Tag'));
    expect(getByText('Capture').closest('[role="option"]')?.getAttribute('aria-disabled')).toBe('true');
  });
});
