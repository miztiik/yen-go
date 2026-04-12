/**
 * Solution Tree Error Boundary
 * @module components/SolutionTree/SolutionTreeErrorBoundary
 *
 * Error boundary for graceful failure handling in solution tree rendering.
 *
 * FR-011: Handle malformed SGF gracefully
 * Edge Case: Show "Unable to parse puzzle" for malformed SGF
 *
 * Covers: T018, T019
 */

import type { JSX, ComponentChildren } from 'preact';
import { Component } from 'preact';
import { WarningIcon } from '../shared/icons/WarningIcon';

/**
 * Props for SolutionTreeErrorBoundary.
 */
export interface SolutionTreeErrorBoundaryProps {
  /** Child components to render */
  children: ComponentChildren;
  /** Optional callback when error occurs */
  onError?: ((error: Error, errorInfo: string) => void) | undefined;
  /** Custom fallback UI */
  fallback?: ComponentChildren;
}

/**
 * State for error boundary.
 */
interface ErrorBoundaryState {
  /** Whether an error has been caught */
  hasError: boolean;
  /** The caught error */
  error: Error | null;
}

/**
 * Error boundary component for Solution Tree.
 *
 * Catches render errors in the tree component and displays
 * a user-friendly fallback UI instead of crashing the app.
 *
 * @example
 * ```tsx
 * <SolutionTreeErrorBoundary>
 *   <SolutionTree tree={tree} currentPath={path} />
 * </SolutionTreeErrorBoundary>
 * ```
 */
export class SolutionTreeErrorBoundary extends Component<
  SolutionTreeErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: SolutionTreeErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  /**
   * Update state when an error is caught.
   */
  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  /**
   * Log error details and call optional callback.
   */
  componentDidCatch(error: Error, errorInfo: { componentStack: string }): void {
    console.error('[SolutionTree] Render error:', error);
    console.error('[SolutionTree] Component stack:', errorInfo.componentStack);

    this.props.onError?.(error, errorInfo.componentStack);
  }

  /**
   * Reset error state to allow retry.
   */
  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ComponentChildren {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div
          className="solution-tree-error"
          role="alert"
          aria-live="polite"
          data-testid="solution-tree-error"
        >
          <div className="error-icon" aria-hidden="true">
            <WarningIcon size={20} />
          </div>
          <h3 className="error-title">Unable to display solution tree</h3>
          <p className="error-message">
            {this.state.error?.message || 'An unexpected error occurred while rendering the tree.'}
          </p>
          <button type="button" className="error-retry-button" onClick={this.handleRetry}>
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Default fallback component for empty or invalid trees.
 *
 * FR-003 edge case: "Empty puzzle" for trees with only root node.
 */
export function EmptyTreeFallback(): JSX.Element {
  return (
    <div
      className="solution-tree-empty"
      role="status"
      aria-label="Empty puzzle"
      data-testid="solution-tree-empty"
    >
      <div className="empty-icon" aria-hidden="true">
        📋
      </div>
      <p className="empty-message">Empty puzzle - no moves to display</p>
    </div>
  );
}

/**
 * Loading skeleton for tree while data is being processed.
 */
export function TreeLoadingSkeleton(): JSX.Element {
  return (
    <div
      className="solution-tree-loading"
      role="status"
      aria-label="Loading solution tree"
      aria-busy="true"
      data-testid="solution-tree-loading"
    >
      <div className="skeleton-node" />
      <div className="skeleton-node" style={{ marginLeft: '1.25rem' }} />
      <div className="skeleton-node" style={{ marginLeft: '2.5rem' }} />
      <div className="skeleton-node" style={{ marginLeft: '1.25rem' }} />
    </div>
  );
}

export default SolutionTreeErrorBoundary;
