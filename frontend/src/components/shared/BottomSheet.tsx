/**
 * BottomSheet — accessible slide-up dialog.
 * @module components/shared/BottomSheet
 *
 * Mobile  : full-width sheet anchored to the bottom of the viewport, rounded
 *           top corners, sticky header with title + close, optional sticky
 *           footer for primary actions.
 * Desktop : centered popover (max-width 480px), same chrome.
 *
 * Behavior:
 * - Closes on Escape, overlay click, and the close button.
 * - Locks body scroll while open.
 * - Restores focus to the trigger element on close.
 * - Focus trap inside the sheet (Tab cycles).
 *
 * Phase 2 of the mobile-usability redesign — see featureFlags.UI_FILTERS_IN_SHEET.
 */

import type { JSX, ComponentChildren } from 'preact';
import { useEffect, useRef, useCallback } from 'preact/hooks';

export interface BottomSheetProps {
  /** Controls visibility. */
  isOpen: boolean;
  /** Called when the sheet should close (Esc, overlay, close button). */
  onClose: () => void;
  /** Heading shown in the sticky header. */
  title: string;
  /** Sheet body. */
  children: ComponentChildren;
  /** Optional sticky footer (e.g. Reset / Done buttons). */
  footer?: ComponentChildren;
  /** Test id (defaults to `bottom-sheet`). */
  testId?: string;
}

/**
 * Slide-up sheet that doubles as a centered popover on desktop.
 * Pure presentation — owners control content and footer.
 */
export function BottomSheet({
  isOpen,
  onClose,
  title,
  children,
  footer,
  testId = 'bottom-sheet',
}: BottomSheetProps): JSX.Element | null {
  const sheetRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<Element | null>(null);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key === 'Tab' && sheetRef.current) {
        const focusable = sheetRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first || !last) return;
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (!isOpen) return;
    previousFocus.current = document.activeElement;

    // Focus first focusable element.
    const id = window.setTimeout(() => {
      const focusable = sheetRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable && focusable.length > 0) {
        focusable[0]?.focus();
      } else {
        sheetRef.current?.focus();
      }
    }, 0);

    document.addEventListener('keydown', handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      window.clearTimeout(id);
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      if (previousFocus.current instanceof HTMLElement) {
        previousFocus.current.focus();
      }
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const titleId = `${testId}-title`;

  const handleOverlayClick = (event: MouseEvent): void => {
    if (event.target === event.currentTarget) onClose();
  };

  return (
    <div
      role="presentation"
      data-testid={`${testId}-overlay`}
      onClick={handleOverlayClick as unknown as JSX.MouseEventHandler<HTMLDivElement>}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.45)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'center',
      }}
    >
      <div
        ref={sheetRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        data-testid={testId}
        className="bottom-sheet-panel"
      >
        {/* Drag handle (mobile affordance — purely decorative) */}
        <div className="bottom-sheet-handle" aria-hidden="true" />

        {/* Sticky header */}
        <div className="bottom-sheet-header">
          <h2 id={titleId} className="bottom-sheet-title">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            data-testid={`${testId}-close`}
            className="bottom-sheet-close"
          >
            ✕
          </button>
        </div>

        {/* Scrollable body */}
        <div className="bottom-sheet-body">{children}</div>

        {/* Sticky footer */}
        {footer && <div className="bottom-sheet-footer">{footer}</div>}
      </div>
    </div>
  );
}

export default BottomSheet;
