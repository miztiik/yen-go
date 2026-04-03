/**
 * CompletionOverlay Component
 * @module components/Feedback/CompletionOverlay
 *
 * Displays a visual overlay on puzzle completion.
 * Shows ✓ for correct, ✗ for wrong with fade animation.
 *
 * Covers: T054 - CompletionOverlay component
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { audioService } from '@/services/audioService';

// ============================================================================
// Types
// ============================================================================

export interface CompletionOverlayProps {
  /** Whether completion is shown */
  isVisible: boolean;
  /** Whether puzzle was solved correctly */
  isSuccess: boolean;
  /** Handler when overlay fades out */
  onFadeOut?: () => void;
  /** Duration in ms before fade (default: 600ms) */
  displayDuration?: number | undefined;
  /** Fade animation duration in ms (default: 200ms) */
  fadeDuration?: number | undefined;
  /** Whether to play sounds (default: true) */
  playSound?: boolean | undefined;
  /** Custom className */
  className?: string | undefined;
}

// ============================================================================
// Styles
// ============================================================================

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    zIndex: 1000,
    opacity: 1,
    transition: 'opacity 200ms ease-out',
  } as JSX.CSSProperties,

  overlayHidden: {
    opacity: 0,
    pointerEvents: 'none',
  } as JSX.CSSProperties,

  icon: {
    fontSize: '6rem',
    fontWeight: 700,
    textShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
    animation: 'completion-pop 300ms ease-out',
  } as JSX.CSSProperties,

  iconSuccess: {
    color: 'var(--color-success)', // Green for correct
  } as JSX.CSSProperties,

  iconFailure: {
    color: 'var(--color-error)', // Red
  } as JSX.CSSProperties,

  keyframes: `
    @keyframes completion-pop {
      0% {
        transform: scale(0.5);
        opacity: 0;
      }
      50% {
        transform: scale(1.1);
      }
      100% {
        transform: scale(1);
        opacity: 1;
      }
    }
  `,
};

// ============================================================================
// Component
// ============================================================================

/**
 * CompletionOverlay - Visual feedback on puzzle completion
 *
 * Shows a large ✓ or ✗ with fade animation and optional sound.
 * Auto-dismisses after displayDuration.
 */
export function CompletionOverlay({
  isVisible,
  isSuccess,
  onFadeOut,
  displayDuration = 600,
  fadeDuration = 200,
  playSound = true,
  className = '',
}: CompletionOverlayProps): JSX.Element | null {
  const [isFading, setIsFading] = useState(false);
  const [isRendered, setIsRendered] = useState(false);

  // Handle visibility and fade timing
  useEffect(() => {
    if (isVisible) {
      setIsRendered(true);
      setIsFading(false);

      // Play sound on show
      if (playSound) {
        if (isSuccess) {
          audioService.play('complete');
        } else {
          audioService.play('wrong');
        }
      }

      // Start fade after displayDuration
      const fadeTimer = setTimeout(() => {
        setIsFading(true);
      }, displayDuration);

      // Remove from DOM after fade completes
      const removeTimer = setTimeout(() => {
        setIsRendered(false);
        onFadeOut?.();
      }, displayDuration + fadeDuration);

      return () => {
        clearTimeout(fadeTimer);
        clearTimeout(removeTimer);
      };
    } else {
      setIsFading(false);
      setIsRendered(false);
    }
  }, [isVisible, isSuccess, displayDuration, fadeDuration, playSound, onFadeOut]);

  // Handle click to dismiss early
  const handleClick = useCallback(() => {
    setIsFading(true);
    setTimeout(() => {
      setIsRendered(false);
      onFadeOut?.();
    }, fadeDuration);
  }, [fadeDuration, onFadeOut]);

  if (!isRendered) return null;

  const overlayStyle: JSX.CSSProperties = {
    ...styles.overlay,
    ...(isFading ? styles.overlayHidden : {}),
    transitionDuration: `${fadeDuration}ms`,
  };

  const iconStyle: JSX.CSSProperties = {
    ...styles.icon,
    ...(isSuccess ? styles.iconSuccess : styles.iconFailure),
  };

  return (
    <>
      {/* Inject keyframes */}
      <style>{styles.keyframes}</style>

      <div
        class={`completion-overlay ${className}`}
        style={overlayStyle}
        onClick={handleClick}
        role="alert"
        aria-live="polite"
        aria-label={isSuccess ? 'Puzzle completed successfully' : 'Puzzle failed'}
        data-testid="completion-overlay"
      >
        <span style={iconStyle} aria-hidden="true">
          {isSuccess ? '✓' : '✗'}
        </span>
      </div>
    </>
  );
}

export default CompletionOverlay;
