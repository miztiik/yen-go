/**
 * Accessible Modal Component
 * @module components/shared/Modal
 *
 * Covers: FR-046 (ARIA labels), US9
 *
 * Constitution Compliance:
 * - IX. Accessibility: WCAG 2.1 AA, focus trap, screen reader support
 */

import type { JSX, ComponentChildren } from 'preact';
import { useEffect, useRef, useCallback } from 'preact/hooks';
import { Button } from './Button';

export interface ModalProps {
  /** Whether modal is open */
  isOpen: boolean;
  /** Callback when modal should close */
  onClose: () => void;
  /** Modal title */
  title: string;
  /** Modal content */
  children: ComponentChildren;
  /** Whether to show close button */
  showCloseButton?: boolean;
  /** Whether clicking overlay closes modal */
  closeOnOverlayClick?: boolean;
  /** Whether pressing Escape closes modal */
  closeOnEscape?: boolean;
  /** Footer content (e.g., action buttons) */
  footer?: ComponentChildren;
  /** Size of the modal */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class name */
  className?: string;
  /** Accessible description */
  'aria-describedby'?: string;
}

const sizeStyles: Record<'sm' | 'md' | 'lg', JSX.CSSProperties> = {
  sm: { maxWidth: '400px' },
  md: { maxWidth: '600px' },
  lg: { maxWidth: '800px' },
};

/**
 * Accessible modal dialog with focus trap and keyboard navigation
 * Meets WCAG 2.1 AA requirements for dialogs
 */
export function Modal({
  isOpen,
  onClose,
  title,
  children,
  showCloseButton = true,
  closeOnOverlayClick = true,
  closeOnEscape = true,
  footer,
  size = 'md',
  className,
  'aria-describedby': ariaDescribedBy,
}: ModalProps): JSX.Element | null {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<Element | null>(null);

  // Handle escape key
  const handleKeyDown = useCallback(
    (event: KeyboardEvent): void => {
      if (event.key === 'Escape' && closeOnEscape) {
        event.preventDefault();
        onClose();
      }

      // Focus trap: Tab key cycles through focusable elements
      if (event.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (!firstElement || !lastElement) return;

        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    },
    [closeOnEscape, onClose]
  );

  // Handle overlay click
  const handleOverlayClick = useCallback(
    (event: MouseEvent): void => {
      if (closeOnOverlayClick && event.target === event.currentTarget) {
        onClose();
      }
    },
    [closeOnOverlayClick, onClose]
  );

  // Focus management
  useEffect(() => {
    if (isOpen) {
      // Store current active element
      previousActiveElement.current = document.activeElement;

      // Focus the modal
      setTimeout(() => {
        const focusableElements = modalRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements && focusableElements.length > 0) {
          focusableElements[0]?.focus();
        } else {
          modalRef.current?.focus();
        }
      }, 0);

      // Add keyboard listener
      document.addEventListener('keydown', handleKeyDown);

      // Prevent body scroll
      document.body.style.overflow = 'hidden';

      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        document.body.style.overflow = '';

        // Restore focus
        if (previousActiveElement.current instanceof HTMLElement) {
          previousActiveElement.current.focus();
        }
      };
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  const modalId = `modal-${title.replace(/\s+/g, '-').toLowerCase()}`;
  const titleId = `${modalId}-title`;

  return (
    <div
      className={`modal-overlay ${className ?? ''}`}
      role="presentation"
      onClick={handleOverlayClick as unknown as JSX.MouseEventHandler<HTMLDivElement>}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 'var(--spacing-md, 1rem)',
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={ariaDescribedBy}
        tabIndex={-1}
        style={{
          backgroundColor: 'var(--color-bg-primary)',
          borderRadius: '16px',
          padding: 'var(--spacing-lg, 1.5rem)',
          width: '100%',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
          maxHeight: '90vh',
          overflowY: 'auto',
          ...sizeStyles[size],
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--spacing-md, 1rem)',
          }}
        >
          <h2
            id={titleId}
            style={{
              margin: 0,
              fontSize: 'var(--font-size-xl, 1.5rem)',
              fontWeight: 700,
              color: 'var(--color-neutral-800)',
            }}
          >
            {title}
          </h2>
          {showCloseButton && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="Close dialog"
              style={{ padding: '0.5rem', color: 'var(--color-text-muted)' }}
            >
              ✕
            </Button>
          )}
        </div>

        {/* Content */}
        <div
          style={{
            color: 'var(--color-neutral-700)',
            lineHeight: 1.6,
          }}
        >
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div
            style={{
              marginTop: 'var(--spacing-lg, 1.5rem)',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 'var(--spacing-sm, 0.5rem)',
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
