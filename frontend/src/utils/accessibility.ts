/**
 * Accessibility Utilities
 * @module utils/accessibility
 *
 * WCAG 2.1 AA compliant utilities for icons, focus, and screen readers.
 * Covers: NFR-015, NFR-016, NFR-017
 */

/**
 * Status icon with accessible fallback text
 * Provides both emoji icon and screen-reader accessible text
 */
export interface StatusIconProps {
  status: 'success' | 'error' | 'skipped' | 'neutral';
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const STATUS_ICONS = {
  success: { icon: '✅', text: 'Correct', color: '#10b981' },
  error: { icon: '❌', text: 'Wrong', color: '#ef4444' },
  skipped: { icon: '⏭️', text: 'Skipped', color: '#9ca3af' },
  neutral: { icon: '⚪', text: 'Pending', color: '#d1d5db' },
} as const;

/**
 * Get status display with icon and accessible text
 */
export function getStatusDisplay(status: keyof typeof STATUS_ICONS): {
  icon: string;
  text: string;
  color: string;
  ariaLabel: string;
} {
  const data = STATUS_ICONS[status];
  return {
    ...data,
    ariaLabel: data.text,
  };
}

/**
 * Generate visible focus outline styles (WCAG 2.1 AA minimum 3:1 contrast)
 */
export function getFocusStyles(variant: 'light' | 'dark' = 'light'): {
  outline: string;
  outlineOffset: string;
} {
  return {
    outline:
      variant === 'light'
        ? '2px solid #2563eb' // Blue-600, good contrast on white
        : '2px solid #60a5fa', // Blue-400, good contrast on dark
    outlineOffset: '2px',
  };
}

/**
 * Standard focus visible styles for components
 */
export const focusVisibleStyles = `
  &:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }
`;

/**
 * Generate skip link styles for keyboard navigation
 */
export function getSkipLinkStyles(): Record<string, string | number> {
  return {
    position: 'absolute',
    top: '-40px',
    left: 0,
    background: '#1f2937',
    color: '#ffffff',
    padding: '8px 16px',
    zIndex: 100,
    transition: 'top 0.2s ease-in-out',
  };
}

/**
 * Screen reader only styles (visually hidden but accessible)
 */
export const srOnlyStyles: Record<string, string | number> = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

/**
 * Color contrast pairs that meet WCAG 2.1 AA requirements (4.5:1 for normal text)
 */
export const accessibleColorPairs = {
  // Light backgrounds
  onWhite: {
    primary: '#1f2937', // gray-800, 12.6:1 contrast
    secondary: '#4b5563', // gray-600, 6.0:1 contrast
    success: '#047857', // emerald-700, 4.6:1 contrast
    error: '#b91c1c', // red-700, 5.5:1 contrast
    warning: '#92400e', // amber-800, 5.4:1 contrast
  },
  // Dark backgrounds
  onDark: {
    primary: '#f9fafb', // gray-50, high contrast
    secondary: '#d1d5db', // gray-300, good contrast
    success: '#34d399', // emerald-400
    error: '#f87171', // red-400
    warning: '#fbbf24', // amber-400
  },
} as const;

/**
 * Get accessible text color for a background
 */
export function getAccessibleTextColor(backgroundColor: string): string {
  // Simple luminance check (not perfect but good enough for common colors)
  const hex = backgroundColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Calculate relative luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

  return luminance > 0.5 ? '#1f2937' : '#f9fafb';
}

/**
 * Announce message to screen readers
 */
export function announceToScreenReader(
  message: string,
  priority: 'polite' | 'assertive' = 'polite'
): void {
  const announcer = document.createElement('div');
  announcer.setAttribute('role', 'status');
  announcer.setAttribute('aria-live', priority);
  announcer.setAttribute('aria-atomic', 'true');
  Object.assign(announcer.style, srOnlyStyles);

  document.body.appendChild(announcer);

  // Small delay ensures screen reader picks up the change
  setTimeout(() => {
    announcer.textContent = message;
  }, 100);

  // Clean up after announcement
  setTimeout(() => {
    document.body.removeChild(announcer);
  }, 1000);
}

/**
 * Focus trap utility for modals
 */
export function createFocusTrap(container: HTMLElement): () => void {
  const focusableElements = container.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );

  const firstFocusable = focusableElements[0];
  const lastFocusable = focusableElements[focusableElements.length - 1];

  const handleKeyDown = (e: KeyboardEvent): void => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      if (document.activeElement === firstFocusable) {
        lastFocusable?.focus();
        e.preventDefault();
      }
    } else {
      if (document.activeElement === lastFocusable) {
        firstFocusable?.focus();
        e.preventDefault();
      }
    }
  };

  container.addEventListener('keydown', handleKeyDown);
  firstFocusable?.focus();

  return () => {
    container.removeEventListener('keydown', handleKeyDown);
  };
}
