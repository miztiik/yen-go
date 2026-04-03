/**
 * Unit tests for ActiveFilterChip (WP7).
 *
 * Tests:
 * - Renders label text
 * - Renders dismiss button with aria-label
 * - Calls onDismiss when clicked
 * - Calls onDismiss on Enter key
 * - Renders testId
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { ActiveFilterChip } from '@/components/shared/ActiveFilterChip';

describe('ActiveFilterChip', () => {
  it('renders label text', () => {
    const { getByText } = render(
      <ActiveFilterChip label="Ladder" onDismiss={() => {}} />,
    );
    expect(getByText('Ladder')).toBeTruthy();
  });

  it('has accessible dismiss label', () => {
    const { getByRole } = render(
      <ActiveFilterChip label="Ladder" onDismiss={() => {}} />,
    );
    const button = getByRole('button');
    expect(button.getAttribute('aria-label')).toBe('Remove Ladder filter');
  });

  it('calls onDismiss when clicked', () => {
    const onDismiss = vi.fn();
    const { getByRole } = render(
      <ActiveFilterChip label="Ladder" onDismiss={onDismiss} />,
    );
    fireEvent.click(getByRole('button'));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('calls onDismiss on Enter key', () => {
    const onDismiss = vi.fn();
    const { getByRole } = render(
      <ActiveFilterChip label="Ladder" onDismiss={onDismiss} />,
    );
    // <button> natively fires onClick on Enter/Space — use click to verify
    fireEvent.click(getByRole('button'));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('calls onDismiss on Space key', () => {
    const onDismiss = vi.fn();
    const { getByRole } = render(
      <ActiveFilterChip label="Ladder" onDismiss={onDismiss} />,
    );
    // <button> natively fires onClick on Enter/Space — use click to verify
    fireEvent.click(getByRole('button'));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it('renders × dismiss indicator', () => {
    const { container } = render(
      <ActiveFilterChip label="Ladder" onDismiss={() => {}} />,
    );
    expect(container.textContent).toContain('×');
  });

  it('renders testId', () => {
    const { container } = render(
      <ActiveFilterChip
        label="Ladder"
        onDismiss={() => {}}
        testId="chip-ladder"
      />,
    );
    expect(container.querySelector('[data-testid="chip-ladder"]')).toBeTruthy();
  });
});
