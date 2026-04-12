/**
 * FilterDropdown — categorized dropdown for selecting from many options.
 * @module components/shared/FilterDropdown
 *
 * Pill-style trigger that expands into a categorized listbox.
 * Designed for tags (28+ options grouped by objective/tesuji/technique).
 *
 * Accessibility: role="listbox", aria-expanded, aria-labelledby, aria-selected,
 * Escape to close, arrow-key navigation, focus trap (WCAG 2.1 AA combobox).
 *
 * Spec: plan-compact-schema-filtering.md §5.3 FilterDropdown
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'preact/hooks';
import type { FunctionalComponent, JSX } from 'preact';
import { ChevronDownIcon, CheckIcon } from './icons';

// Monotonic counter for unique IDs when testId is not provided (Finding 2)
let dropdownIdCounter = 0;

// ============================================================================
// Types
// ============================================================================

/** A single selectable option in the dropdown. */
export interface DropdownOption {
  /** Unique option ID (passed to onChange). */
  readonly id: string;
  /** Display label. */
  readonly label: string;
  /** Optional count badge (e.g., puzzle count from master index). */
  readonly count?: number;
}

/** A named group of options (e.g., "Objectives", "Tesuji Patterns"). */
export interface DropdownOptionGroup {
  /** Category header label (rendered uppercase). */
  readonly label: string;
  /** Options within this category. */
  readonly options: readonly DropdownOption[];
}

export interface FilterDropdownProps {
  /** Accessible label for the dropdown. */
  readonly label: string;
  /** Idle trigger text (e.g., "Filter by technique"). */
  readonly placeholder: string;
  /** Grouped options rendered under category headers. */
  readonly groups: readonly DropdownOptionGroup[];
  /** Currently selected option ID, or null for "All". */
  readonly selected: string | null;
  /** Called when user selects an option. null = "All". */
  readonly onChange: (id: string | null) => void;
  /** Optional CSS class for the container. */
  readonly className?: string;
  /** Optional test ID prefix. */
  readonly testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const FilterDropdown: FunctionalComponent<FilterDropdownProps> = ({
  label,
  placeholder,
  groups,
  selected,
  onChange,
  className = '',
  testId,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);
  const [focusIndex, setFocusIndex] = useState(-1);
  const focusIndexRef = useRef(focusIndex);
  focusIndexRef.current = focusIndex;

  // Build flat list of selectable option IDs for arrow-key nav (memoized)
  const allOptionIds = useMemo(() => buildOptionIds(groups), [groups]);

  // Pre-compute ID → index map for O(1) lookup (Finding 23)
  const optionIndexMap = useMemo(() => {
    const map = new Map<string, number>();
    allOptionIds.forEach((id, i) => map.set(id, i));
    return map;
  }, [allOptionIds]);

  // Find selected option for trigger text (memoized)
  const selectedOption = useMemo(
    () => (selected ? findOption(groups, selected) : null),
    [groups, selected]
  );

  // ── Escape key closes dropdown (Finding 6 — only attach when open) ──
  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  // Reset focus index when dropdown opens/closes (Finding 7 — include all deps)
  useEffect(() => {
    if (isOpen) {
      // Focus the selected item, or "All" (index 0) if nothing selected
      const idx = selected ? allOptionIds.indexOf(selected) : -1;
      setFocusIndex(idx >= 0 ? idx + 1 : 0); // +1 because index 0 = "All"
    } else {
      setFocusIndex(-1);
    }
  }, [isOpen, selected, allOptionIds]);

  // Auto-focus listbox when dropdown opens
  useEffect(() => {
    if (isOpen) {
      // Slight delay to ensure DOM is ready
      requestAnimationFrame(() => {
        listboxRef.current?.focus();
      });
    }
  }, [isOpen]);

  // ── Keyboard navigation inside listbox ───────────────────────────
  // F5: Helper to check if item at given index is disabled (count=0)
  const isItemDisabled = useCallback(
    (idx: number): boolean => {
      if (idx === 0) return false; // "All" is never disabled
      const optId = allOptionIds[idx - 1];
      if (!optId) return false;
      const opt = findOption(groups, optId);
      return opt?.count === 0;
    },
    [allOptionIds, groups]
  );

  const handleListboxKeyDown = useCallback(
    (e: JSX.TargetedKeyboardEvent<HTMLDivElement>) => {
      // Total selectable items = 1 ("All") + allOptionIds.length
      const totalItems = 1 + allOptionIds.length;

      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault();
          setFocusIndex((prev) => {
            let next = (prev + 1) % totalItems;
            // F5: Skip disabled items
            let attempts = 0;
            while (isItemDisabled(next) && attempts < totalItems) {
              next = (next + 1) % totalItems;
              attempts++;
            }
            return next;
          });
          break;
        }
        case 'ArrowUp': {
          e.preventDefault();
          setFocusIndex((prev) => {
            let next = (prev - 1 + totalItems) % totalItems;
            // F5: Skip disabled items
            let attempts = 0;
            while (isItemDisabled(next) && attempts < totalItems) {
              next = (next - 1 + totalItems) % totalItems;
              attempts++;
            }
            return next;
          });
          break;
        }
        case 'Home': {
          e.preventDefault();
          setFocusIndex(0);
          break;
        }
        case 'End': {
          e.preventDefault();
          setFocusIndex(totalItems - 1);
          break;
        }
        case 'Enter':
        case ' ': {
          e.preventDefault();
          const currentIdx = focusIndexRef.current;
          let didSelect = false;
          if (currentIdx === 0) {
            onChange(null);
            didSelect = true;
          } else {
            const optId = allOptionIds[currentIdx - 1];
            if (optId !== undefined) {
              // F4+F15: Skip disabled (zero-count) options — don't close
              const opt = findOption(groups, optId);
              if (opt && opt.count !== 0) {
                onChange(optId);
                didSelect = true;
              }
            }
          }
          if (didSelect) {
            setIsOpen(false);
            triggerRef.current?.focus();
          }
          break;
        }
        case 'Tab': {
          // Close dropdown and let browser handle natural Tab focus flow
          setIsOpen(false);
          break;
        }
      }
    },
    [allOptionIds, onChange, groups, isItemDisabled]
  );

  // ── Scroll focused item into view ────────────────────────────────
  useEffect(() => {
    if (!isOpen || focusIndex < 0) return;
    const listbox = listboxRef.current;
    if (!listbox) return;
    const focusedEl = listbox.querySelector(`[data-focus-index="${focusIndex}"]`);
    if (focusedEl && typeof (focusedEl as HTMLElement).scrollIntoView === 'function') {
      (focusedEl as HTMLElement).scrollIntoView({ block: 'nearest' });
    }
  }, [focusIndex, isOpen]);

  const toggleOpen = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const handleSelect = useCallback(
    (optionId: string | null) => {
      // PURSIG Finding 15: Don't fire onChange for disabled (zero-count) options
      if (optionId !== null) {
        const opt = findOption(groups, optionId);
        if (opt && opt.count === 0) return;
      }
      onChange(optionId);
      setIsOpen(false);
      triggerRef.current?.focus();
    },
    [onChange, groups]
  );

  const triggerId = testId ? `${testId}-trigger` : undefined;
  // Stable unique ID for listbox (Finding 2 — avoid collisions when testId is omitted)
  const stableIdRef = useRef(`filter-dropdown-${++dropdownIdCounter}`);
  const listboxId = testId ? `${testId}-listbox` : stableIdRef.current;

  // Active descendant ID for screen reader focus tracking (Finding 6)
  const activeDescendantId = focusIndex >= 0 ? `${listboxId}-opt-${focusIndex}` : undefined;

  return (
    <div className={`relative ${className}`} data-testid={testId}>
      {/* ── Trigger (pill-style, matches FilterBar pills) ─────────── */}
      <button
        ref={triggerRef}
        type="button"
        id={triggerId}
        onClick={toggleOpen}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={label}
        className="inline-flex min-h-[44px] cursor-pointer items-center gap-2 rounded-full px-4 text-sm transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
        style={
          selected
            ? {
                backgroundColor: 'var(--color-accent, #059669)',
                color: 'var(--color-bg-panel, #fff)',
                fontWeight: 600,
                border: '1px solid var(--color-accent, #059669)',
              }
            : {
                backgroundColor: 'var(--color-bg-elevated, #fff)',
                color: 'var(--color-text-primary, #2C1810)',
                fontWeight: 500,
                border: '1px solid var(--color-border, #d4c9b8)',
              }
        }
        data-testid={triggerId}
      >
        <span>
          {selectedOption
            ? `${selectedOption.label}${selectedOption.count != null ? ` (${selectedOption.count})` : ''}`
            : placeholder}
        </span>
        <ChevronDownIcon
          size={14}
          className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* ── Dropdown panel ──────────────────────────────────────────── */}
      {isOpen && (
        <>
          {/* Backdrop — click-to-close (same pattern as SettingsGear) */}
          <div
            className="fixed inset-0 z-[var(--z-dropdown,50)]"
            onClick={() => {
              setIsOpen(false);
              triggerRef.current?.focus();
            }}
            aria-hidden="true"
          />

          {/* Listbox panel — fixed position to escape all stacking contexts (Apple popover pattern) */}
          <div
            ref={listboxRef}
            role="listbox"
            id={listboxId}
            aria-label={label}
            aria-activedescendant={activeDescendantId}
            tabIndex={0}
            onKeyDown={handleListboxKeyDown}
            className="fixed z-[calc(var(--z-dropdown,50)_+_1)] w-64 overflow-y-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] shadow-2xl focus:outline-none"
            style={{
              maxHeight: '400px',
              top: triggerRef.current
                ? `${triggerRef.current.getBoundingClientRect().bottom + 8}px`
                : undefined,
              left: triggerRef.current
                ? `${triggerRef.current.getBoundingClientRect().left}px`
                : undefined,
            }}
            data-testid={testId ? `${testId}-panel` : undefined}
          >
            {/* "All" option */}
            <DropdownItem
              label="All"
              isSelected={selected === null}
              isFocused={focusIndex === 0}
              focusIndex={0}
              itemId={`${listboxId}-opt-0`}
              onClick={() => handleSelect(null)}
              testId={testId ? `${testId}-option-all` : undefined}
            />

            {/* Categorized groups */}
            {groups.map((group) => (
              <div
                key={group.label}
                role="group"
                aria-labelledby={`${listboxId}-group-${group.label.replace(/\s+/g, '-').toLowerCase()}`}
              >
                {/* Category header — F6: visible to assistive technology */}
                <div
                  id={`${listboxId}-group-${group.label.replace(/\s+/g, '-').toLowerCase()}`}
                  className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)]"
                  role="presentation"
                >
                  {group.label}
                </div>
                {/* Options */}
                {group.options.map((opt) => {
                  const itemIndex = (optionIndexMap.get(opt.id) ?? -1) + 1; // +1 for "All"
                  return (
                    <DropdownItem
                      key={opt.id}
                      label={opt.label}
                      count={opt.count}
                      isSelected={opt.id === selected}
                      isFocused={focusIndex === itemIndex}
                      focusIndex={itemIndex}
                      itemId={`${listboxId}-opt-${itemIndex}`}
                      onClick={() => handleSelect(opt.id)}
                      testId={testId ? `${testId}-option-${opt.id}` : undefined}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

// ============================================================================
// Internal: DropdownItem
// ============================================================================

interface DropdownItemProps {
  readonly label: string;
  readonly count?: number | undefined;
  readonly isSelected: boolean;
  readonly isFocused: boolean;
  readonly focusIndex: number;
  /** Unique DOM id for aria-activedescendant referencing (Finding 6). */
  readonly itemId: string;
  readonly onClick: () => void;
  readonly testId?: string | undefined;
}

function DropdownItem({
  label,
  count,
  isSelected,
  isFocused,
  focusIndex,
  itemId,
  onClick,
  testId,
}: DropdownItemProps): JSX.Element {
  // PURSIG Finding 15: Disable zero-count options (parity with FilterBar)
  const isDisabled = count === 0;
  return (
    <div
      role="option"
      id={itemId}
      aria-selected={isSelected}
      aria-disabled={isDisabled || undefined}
      tabIndex={-1}
      onClick={() => {
        if (!isDisabled) onClick();
      }}
      data-focus-index={focusIndex}
      className={`flex min-h-[44px] items-center justify-between px-4 py-2.5 text-sm transition-colors ${
        isFocused ? 'bg-[var(--color-bg-elevated)]' : ''
      } ${isDisabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      style={{
        color: isDisabled
          ? 'var(--color-text-muted, #999)'
          : isSelected
            ? 'var(--color-accent, #059669)'
            : 'var(--color-text-primary, #2C1810)',
        fontWeight: isSelected ? 600 : 400,
      }}
      data-testid={testId}
    >
      <span className="flex items-center gap-2">
        {isSelected && <CheckIcon size={14} />}
        {label}
      </span>
      {count != null && <span className="text-xs text-[var(--color-text-muted)]">{count}</span>}
    </div>
  );
}

// ============================================================================
// Helpers
// ============================================================================

/** Flatten all option IDs from groups into a single ordered array. */
function buildOptionIds(groups: readonly DropdownOptionGroup[]): string[] {
  const ids: string[] = [];
  for (const group of groups) {
    for (const opt of group.options) {
      ids.push(opt.id);
    }
  }
  return ids;
}

/** Find an option by ID across all groups. */
function findOption(
  groups: readonly DropdownOptionGroup[],
  id: string
): DropdownOption | undefined {
  for (const group of groups) {
    for (const opt of group.options) {
      if (opt.id === id) return opt;
    }
  }
  return undefined;
}

export default FilterDropdown;
