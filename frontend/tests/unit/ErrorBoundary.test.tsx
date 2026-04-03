/**
 * ErrorBoundary tests (T024)
 *
 * Spec 129 — FR-028, FR-014
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/preact';
import { ErrorBoundary } from '../../src/components/shared/ErrorBoundary';
import { h } from 'preact';

// Component that throws on render
function BrokenComponent(): never {
  throw new Error('Render error!');
}

function GoodComponent() {
  return h('div', null, 'Hello World');
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress console.error for expected errors
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('should render children when no error', () => {
    const { container } = render(
      h(ErrorBoundary, null, h(GoodComponent, null)),
    );
    expect(container.textContent).toContain('Hello World');
  });

  it('should show default fallback when error occurs', () => {
    const { container } = render(
      h(ErrorBoundary, null, h(BrokenComponent, null)),
    );
    expect(container.textContent).toContain('Something went wrong');
    expect(container.textContent).toContain('Try again');
  });

  it('should show custom fallback when provided', () => {
    const fallback = h('div', null, 'Custom error UI');
    const { container } = render(
      h(ErrorBoundary, { fallback }, h(BrokenComponent, null)),
    );
    expect(container.textContent).toContain('Custom error UI');
  });

  it('should call onError callback when error occurs', () => {
    const onError = vi.fn();
    render(
      h(ErrorBoundary, { onError }, h(BrokenComponent, null)),
    );
    expect(onError).toHaveBeenCalledOnce();
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({}),
    );
  });

  it('should have role="alert" on fallback', () => {
    const { container } = render(
      h(ErrorBoundary, null, h(BrokenComponent, null)),
    );
    expect(container.querySelector('[role="alert"]')).toBeTruthy();
  });
});
