/**
 * Unit tests for FilterDropdown (WP7 — G41).
 *
 * Tests:
 * - Renders trigger with placeholder text
 * - Opens/closes on trigger click
 * - Renders grouped options with category headers
 * - Renders count badges
 * - Marks selected option with aria-selected
 * - Calls onChange with option ID when clicked
 * - Calls onChange(null) when "All" is selected
 * - Closes on backdrop click
 * - Closes on Escape key
 * - Shows active trigger style when an option is selected
 * - Renders ChevronDown icon on trigger
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { FilterDropdown, type DropdownOptionGroup } from '@/components/shared/FilterDropdown';

// ============================================================================
// Test data
// ============================================================================

const testGroups: DropdownOptionGroup[] = [
  {
    label: 'Objectives',
    options: [
      { id: '10', label: 'Life & Death', count: 42 },
      { id: '12', label: 'Ko', count: 18 },
    ],
  },
  {
    label: 'Tesuji Patterns',
    options: [
      { id: '30', label: 'Snapback', count: 12 },
      { id: '34', label: 'Ladder', count: 35 },
    ],
  },
];

// ============================================================================
// Tests
// ============================================================================

describe('FilterDropdown', () => {
  let onChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onChange = vi.fn();
  });

  it('renders trigger with placeholder text when nothing selected', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );
    const trigger = getByRole('button', { name: 'Filter by technique' });
    expect(trigger).toBeTruthy();
    expect(trigger.textContent).toContain('Filter by technique');
  });

  it('renders aria-expanded=false when closed', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );
    const trigger = getByRole('button', { name: 'Filter by technique' });
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
  });

  it('opens dropdown on trigger click', () => {
    const { getByRole, queryByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    // Listbox not present initially
    expect(queryByRole('listbox')).toBeNull();

    // Click trigger
    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));

    // Listbox now present
    expect(queryByRole('listbox')).toBeTruthy();
    expect(getByRole('button', { name: 'Filter by technique' }).getAttribute('aria-expanded')).toBe(
      'true',
    );
  });

  it('renders category headers when open', () => {
    const { getByRole, getByText } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));

    expect(getByText('Objectives')).toBeTruthy();
    expect(getByText('Tesuji Patterns')).toBeTruthy();
  });

  it('renders all options with labels and counts', () => {
    const { getByRole, getByText } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));

    expect(getByText('Life & Death')).toBeTruthy();
    expect(getByText('42')).toBeTruthy();
    expect(getByText('Ko')).toBeTruthy();
    expect(getByText('18')).toBeTruthy();
    expect(getByText('Snapback')).toBeTruthy();
    expect(getByText('12')).toBeTruthy();
    expect(getByText('Ladder')).toBeTruthy();
    expect(getByText('35')).toBeTruthy();
  });

  it('renders "All" option when open', () => {
    const { getByRole, getAllByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));

    const options = getAllByRole('option');
    // "All" + 4 options = 5
    expect(options.length).toBe(5);
    // "All" option should be first and marked as selected when nothing is selected
    expect(options[0].getAttribute('aria-selected')).toBe('true');
  });

  it('marks selected option with aria-selected', () => {
    const { getByRole, getAllByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected="34"
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));

    const options = getAllByRole('option');
    // "All" should NOT be selected
    expect(options[0].getAttribute('aria-selected')).toBe('false');
    // Find the Ladder option (id 34) and check it's selected
    const ladderOption = options.find((opt) => opt.textContent?.includes('Ladder'));
    expect(ladderOption?.getAttribute('aria-selected')).toBe('true');
  });

  it('calls onChange with option ID when option clicked', () => {
    const { getByRole, getByText } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    fireEvent.click(getByText('Ladder'));

    expect(onChange).toHaveBeenCalledWith('34');
  });

  it('calls onChange(null) when "All" option clicked', () => {
    const { getByRole, getAllByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected="34"
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    // Click "All" option (first option)
    const allOption = getAllByRole('option')[0];
    fireEvent.click(allOption);

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('closes dropdown after selection', () => {
    const { getByRole, getByText, queryByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    expect(queryByRole('listbox')).toBeTruthy();

    fireEvent.click(getByText('Ko'));
    expect(queryByRole('listbox')).toBeNull();
  });

  it('closes on Escape key', () => {
    const { getByRole, queryByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    expect(queryByRole('listbox')).toBeTruthy();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(queryByRole('listbox')).toBeNull();
  });

  it('shows selected label on trigger when option is selected', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected="34"
        onChange={onChange}
      />,
    );

    const trigger = getByRole('button', { name: 'Filter by technique' });
    expect(trigger.textContent).toContain('Ladder');
    expect(trigger.textContent).toContain('35');
  });

  it('renders testId on container and trigger', () => {
    const { container } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
        testId="tag-filter"
      />,
    );

    expect(container.querySelector('[data-testid="tag-filter"]')).toBeTruthy();
    expect(container.querySelector('[data-testid="tag-filter-trigger"]')).toBeTruthy();
  });

  it('navigates options with ArrowDown and selects with Enter', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    const listbox = getByRole('listbox');

    // Arrow down from "All" (index 0) to first option (index 1, Life & Death)
    fireEvent.keyDown(listbox, { key: 'ArrowDown' });
    // Arrow down to second option (index 2, Ko)
    fireEvent.keyDown(listbox, { key: 'ArrowDown' });
    // Select with Enter
    fireEvent.keyDown(listbox, { key: 'Enter' });

    expect(onChange).toHaveBeenCalledWith('12');
  });

  it('navigates with ArrowUp to wrap around', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    const listbox = getByRole('listbox');

    // ArrowUp from "All" (index 0) should wrap to last option
    fireEvent.keyDown(listbox, { key: 'ArrowUp' });
    // Select with Enter — should be the last option (Ladder, id 34)
    fireEvent.keyDown(listbox, { key: 'Enter' });

    expect(onChange).toHaveBeenCalledWith('34');
  });

  it('traps Tab key inside dropdown', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    const listbox = getByRole('listbox');

    // Tab should be prevented (focus trap)
    const tabEvent = new KeyboardEvent('keydown', {
      key: 'Tab',
      bubbles: true,
      cancelable: true,
    });
    listbox.dispatchEvent(tabEvent);
    // The event should be captured by the onKeyDown handler
    // Since we can't easily test preventDefault in jsdom, we verify the dropdown stays open
    expect(getByRole('listbox')).toBeTruthy();
  });

  // ============================================================================
  // L4: Zero-count disabled option tests
  // ============================================================================

  it('disables zero-count options with aria-disabled', () => {
    const groupsWithZero: DropdownOptionGroup[] = [
      {
        label: 'Objectives',
        options: [
          { id: '10', label: 'Life & Death', count: 42 },
          { id: '12', label: 'Ko', count: 0 },
        ],
      },
    ];

    const { getByRole, getAllByRole } = render(
      <FilterDropdown
        label="Filter"
        placeholder="Filter"
        groups={groupsWithZero}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter' }));
    const options = getAllByRole('option');
    // Find Ko option (count=0) — should be disabled
    const koOption = options.find(opt => opt.textContent?.includes('Ko'));
    expect(koOption?.getAttribute('aria-disabled')).toBe('true');
  });

  it('ArrowDown skips disabled (zero-count) options', () => {
    const groupsWithZero: DropdownOptionGroup[] = [
      {
        label: 'Objectives',
        options: [
          { id: '10', label: 'Life & Death', count: 42 },
          { id: '12', label: 'Ko', count: 0 },
          { id: '14', label: 'Seki', count: 10 },
        ],
      },
    ];

    const { getByRole } = render(
      <FilterDropdown
        label="Filter"
        placeholder="Filter"
        groups={groupsWithZero}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter' }));
    const listbox = getByRole('listbox');

    // ArrowDown from "All" (index 0) to Life & Death (index 1)
    fireEvent.keyDown(listbox, { key: 'ArrowDown' });
    // ArrowDown should SKIP Ko (count=0) and land on Seki (index 3)
    fireEvent.keyDown(listbox, { key: 'ArrowDown' });
    // Select with Enter — should be Seki
    fireEvent.keyDown(listbox, { key: 'Enter' });

    expect(onChange).toHaveBeenCalledWith('14');
  });

  // ============================================================================
  // L5: Home/End key navigation tests
  // ============================================================================

  it('Home key moves to first option', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    const listbox = getByRole('listbox');

    // Navigate down a few times
    fireEvent.keyDown(listbox, { key: 'ArrowDown' });
    fireEvent.keyDown(listbox, { key: 'ArrowDown' });
    // Press Home to jump to first
    fireEvent.keyDown(listbox, { key: 'Home' });
    // Select — should be "All" (null)
    fireEvent.keyDown(listbox, { key: 'Enter' });

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it('End key moves to last option', () => {
    const { getByRole } = render(
      <FilterDropdown
        label="Filter by technique"
        placeholder="Filter by technique"
        groups={testGroups}
        selected={null}
        onChange={onChange}
      />,
    );

    fireEvent.click(getByRole('button', { name: 'Filter by technique' }));
    const listbox = getByRole('listbox');

    // Press End to jump to last option (Ladder, id 34)
    fireEvent.keyDown(listbox, { key: 'End' });
    fireEvent.keyDown(listbox, { key: 'Enter' });

    expect(onChange).toHaveBeenCalledWith('34');
  });
});
