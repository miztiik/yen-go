/**
 * GoTipDisplay — unit tests.
 *
 * T054: Verify GoTipDisplay renders immediately with 0ms delay.
 * Spec 131: FR-023
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/preact';
import { GoTipDisplay, type GoTip } from '../../src/components/Loading/GoTipDisplay';

const SAMPLE_TIPS: GoTip[] = [
  { text: 'Capture the cutting stones', category: 'tip', levels: ['beginner'] },
];

describe('GoTipDisplay', () => {
  it('renders tip text immediately without artificial delay', () => {
    vi.useFakeTimers();
    render(<GoTipDisplay tips={SAMPLE_TIPS} level="beginner" />);

    // Tip should be visible immediately — no 800ms wait
    expect(screen.getByText(/Capture the cutting stones/)).toBeTruthy();
    vi.useRealTimers();
  });

  it('fades out when dataReady is true (no minimum timer blocking)', () => {
    vi.useFakeTimers();
    const { rerender } = render(
      <GoTipDisplay tips={SAMPLE_TIPS} level="beginner" dataReady={false} />,
    );

    // Advance microtasks so useEffect fires
    act(() => { vi.advanceTimersByTime(0); });

    rerender(<GoTipDisplay tips={SAMPLE_TIPS} level="beginner" dataReady={true} />);
    act(() => { vi.advanceTimersByTime(0); });

    // After dataReady, the container should have opacity 0 (fading out)
    const tipEl = screen.getByText(/Capture the cutting stones/);
    const container = tipEl.closest('[style]') as HTMLElement;
    expect(container?.style.opacity).toBe('0');

    vi.useRealTimers();
  });

  it('returns null when tips array is empty', () => {
    const { container } = render(<GoTipDisplay tips={[]} />);
    expect(container.innerHTML).toBe('');
  });
});
