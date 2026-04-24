/**
 * BottomSheet — unit tests.
 *
 * Phase 2 (UI_FILTERS_IN_SHEET) primitive used by PuzzleSetHeader and
 * KeyboardHelp. Verifies open/close behavior, Escape handling, overlay
 * dismissal, and footer slot rendering.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/preact';
import { BottomSheet } from '@/components/shared/BottomSheet';

afterEach(() => {
  cleanup();
  document.body.style.overflow = '';
});

describe('BottomSheet', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <BottomSheet isOpen={false} onClose={() => {}} title="Hidden">
        <div>body</div>
      </BottomSheet>,
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title, body, and dismiss controls when open', () => {
    render(
      <BottomSheet isOpen onClose={() => {}} title="My Sheet" testId="sheet">
        <div data-testid="sheet-body-content">body</div>
      </BottomSheet>,
    );
    expect(screen.getByTestId('sheet')).toBeDefined();
    expect(screen.getByText('My Sheet')).toBeDefined();
    expect(screen.getByTestId('sheet-body-content')).toBeDefined();
    expect(screen.getByTestId('sheet-close')).toBeDefined();
  });

  it('calls onClose when the close button is clicked', () => {
    const handleClose = vi.fn();
    render(
      <BottomSheet isOpen onClose={handleClose} title="Sheet" testId="sheet">
        <div>body</div>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByTestId('sheet-close'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when Escape is pressed', () => {
    const handleClose = vi.fn();
    render(
      <BottomSheet isOpen onClose={handleClose} title="Sheet" testId="sheet">
        <div>body</div>
      </BottomSheet>,
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when the backdrop is clicked', () => {
    const handleClose = vi.fn();
    render(
      <BottomSheet isOpen onClose={handleClose} title="Sheet" testId="sheet">
        <div>body</div>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByTestId('sheet-overlay'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('does not call onClose when clicking inside the sheet body', () => {
    const handleClose = vi.fn();
    render(
      <BottomSheet isOpen onClose={handleClose} title="Sheet" testId="sheet">
        <button type="button" data-testid="inner-btn">
          Inner
        </button>
      </BottomSheet>,
    );
    fireEvent.click(screen.getByTestId('inner-btn'));
    expect(handleClose).not.toHaveBeenCalled();
  });

  it('renders a footer slot when provided', () => {
    render(
      <BottomSheet
        isOpen
        onClose={() => {}}
        title="Sheet"
        testId="sheet"
        footer={<button data-testid="done-btn">Done</button>}
      >
        body
      </BottomSheet>,
    );
    expect(screen.getByTestId('done-btn')).toBeDefined();
  });

  it('locks body scroll while open and restores it on close', () => {
    const { rerender } = render(
      <BottomSheet isOpen onClose={() => {}} title="Sheet">
        body
      </BottomSheet>,
    );
    expect(document.body.style.overflow).toBe('hidden');

    rerender(
      <BottomSheet isOpen={false} onClose={() => {}} title="Sheet">
        body
      </BottomSheet>,
    );
    expect(document.body.style.overflow).toBe('');
  });

  it('exposes ARIA dialog semantics', () => {
    render(
      <BottomSheet isOpen onClose={() => {}} title="Sheet" testId="sheet">
        body
      </BottomSheet>,
    );
    const dialog = screen.getByTestId('sheet');
    expect(dialog.getAttribute('role')).toBe('dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.getAttribute('aria-labelledby')).toBe('sheet-title');
  });
});
