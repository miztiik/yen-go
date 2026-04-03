/**
 * PuzzleSidebar — unit tests.
 * T133: Verify metadata renders in correct order (identity → tools → content).
 * T134: Verify collection name renders as navigable <a> link.
 * Spec 132 US11
 */
import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/preact';
import { PuzzleSidebar, type PuzzleSidebarProps } from '../../src/components/Puzzle/PuzzleSidebar';

// Stub child components to isolate PuzzleSidebar rendering
vi.mock('../../src/components/Transforms', () => ({
  TransformBar: (props: Record<string, unknown>) => <div data-testid="transform-bar" data-disabled={String(props.disabled)} />,
}));
vi.mock('../../src/components/SolutionTree', () => ({
  SolutionTreePanel: () => <div data-testid="solution-tree-panel" />,
  BreadcrumbTrail: () => <div data-testid="breadcrumb-trail" />,
  CommentPanel: () => <div data-testid="comment-panel" />,
  TreeControls: () => <div data-testid="tree-controls" />,
}));

/** Default props with all required fields. */
function makeProps(overrides: Partial<PuzzleSidebarProps> = {}): PuzzleSidebarProps {
  return {
    status: 'playing',
    isReviewMode: false,
    gobanRef: { current: null },
    treeContainerRef: { current: null },
    transformSettings: {
      flipH: false,
      flipV: false,
      flipDiagonal: false,
      swapColors: false,
      zoom: false,
    },
    onToggleFlipH: vi.fn(),
    onToggleFlipV: vi.fn(),
    onToggleFlipDiagonal: vi.fn(),
    onToggleSwapColors: vi.fn(),
    onToggleZoom: vi.fn(),
    onRandomize: vi.fn(),
    onResetTransforms: vi.fn(),
    currentHintTier: 0,
    hints: [],
    ...overrides,
  };
}

describe('PuzzleSidebar', () => {
  // ── T133: Section ordering ──

  describe('section ordering (T133)', () => {
    it('renders identity section before tools section before content section', () => {
      const { container } = render(<PuzzleSidebar {...makeProps({ skillLevel: 'beginner', isReviewMode: true })} />);
      const sidebar = container.querySelector('[data-testid="puzzle-sidebar"]')!;
      const children = Array.from(sidebar.children);

      // Find section indices by data-testid or heading text content
      const metadataIdx = children.findIndex(el => el.getAttribute('data-testid') === 'puzzle-metadata');
      const transformIdx = children.findIndex(el => el.textContent?.includes('Transforms'));
      const solutionTreeIdx = children.findIndex(el => el.textContent?.includes('Solution Tree'));

      expect(metadataIdx).toBeGreaterThanOrEqual(0);
      expect(transformIdx).toBeGreaterThanOrEqual(0);
      expect(solutionTreeIdx).toBeGreaterThanOrEqual(0);

      // Identity (metadata) appears before Tools (transforms)
      expect(metadataIdx).toBeLessThan(transformIdx);
      // Tools (transforms) appears before Content (solution tree)
      expect(transformIdx).toBeLessThan(solutionTreeIdx);
    });

    it('renders metadata section as the first child', () => {
      const { getByTestId } = render(<PuzzleSidebar {...makeProps()} />);
      const sidebar = getByTestId('puzzle-sidebar');
      const firstChild = sidebar.children[0];
      expect(firstChild?.getAttribute('data-testid')).toBe('puzzle-metadata');
    });
  });

  // ── T134: Collection link rendering ──

  describe('collection link (T134)', () => {
    it('renders collection name as a navigable <a> link when collection prop is provided', () => {
      const { container } = render(
        <PuzzleSidebar {...makeProps({ collection: { id: 'cho-elementary', name: 'Cho Elementary' } })} />,
      );
      const link = container.querySelector('a[href="/collections/cho-elementary"]');
      expect(link).not.toBeNull();
      expect(link!.textContent).toBe('Cho Elementary');
    });

    it('omits collection when collection prop is undefined', () => {
      const { container } = render(
        <PuzzleSidebar {...makeProps({ collection: undefined })} />,
      );
      const links = container.querySelectorAll('a');
      // No collection link should exist
      const collectionLinks = Array.from(links).filter(a =>
        a.getAttribute('href')?.startsWith('/collections/'),
      );
      expect(collectionLinks).toHaveLength(0);
    });

    it('collection link has correct href format', () => {
      const { container } = render(
        <PuzzleSidebar {...makeProps({ collection: { id: 'life-death-beginner', name: 'Life & Death Beginner' } })} />,
      );
      const link = container.querySelector('a');
      expect(link?.getAttribute('href')).toBe('/collections/life-death-beginner');
    });
  });

  // ── Additional coverage ──

  describe('identity section metadata', () => {
    it('renders skill level when provided', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ skillLevel: 'intermediate' })} />,
      );
      expect(getByText('intermediate')).toBeTruthy();
    });

    it('renders tags when provided', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ tags: ['life-and-death', 'ko'] })} />,
      );
      expect(getByText('life-and-death')).toBeTruthy();
      expect(getByText('ko')).toBeTruthy();
    });

    it('renders ko context badge for simple ko', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ koContext: 'simple' })} />,
      );
      expect(getByText('Simple Ko')).toBeTruthy();
    });

    it('does not render ko badge for "none" context', () => {
      const { queryByText } = render(
        <PuzzleSidebar {...makeProps({ koContext: 'none' })} />,
      );
      expect(queryByText('Simple Ko')).toBeNull();
      expect(queryByText('Complex Ko')).toBeNull();
    });

    it('renders corner position when not center', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ cornerPosition: 'TR' })} />,
      );
      expect(getByText('TR')).toBeTruthy();
    });

    it('does not render corner position for center (C)', () => {
      const { queryByText } = render(
        <PuzzleSidebar {...makeProps({ cornerPosition: 'C' })} />,
      );
      // "C" alone should not appear as a corner label
      const cornerLabel = queryByText('C');
      // Note: "C" might appear in other text. Check specifically the corner row
      // The sidebar shows "Corner:" label only when position !== 'C'
      expect(queryByText('Corner:')).toBeNull();
    });

    it('shows hint count when hints available', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ hints: ['Focus on the corner', 'Look for the ko'] })} />,
      );
      expect(getByText('2 available')).toBeTruthy();
    });

    it('shows "None" when no hints', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ hints: [] })} />,
      );
      expect(getByText('None')).toBeTruthy();
    });
  });

  describe('content section modes', () => {
    it('shows review mode content (tree controls) when isReviewMode is true', () => {
      const { getByTestId } = render(
        <PuzzleSidebar {...makeProps({ isReviewMode: true })} />,
      );
      expect(getByTestId('tree-controls')).toBeTruthy();
      expect(getByTestId('solution-tree-panel')).toBeTruthy();
    });

    it('shows solving mode placeholder when not in review mode and no comment/hint', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({ isReviewMode: false, currentHintTier: 0 })} />,
      );
      expect(getByText(/Make your move/)).toBeTruthy();
    });

    it('shows hint text when currentHintTier > 0', () => {
      const { getByText } = render(
        <PuzzleSidebar {...makeProps({
          isReviewMode: false,
          currentHintTier: 1,
          hints: ['Focus on corner stones'],
        })} />,
      );
      expect(getByText('Focus on corner stones')).toBeTruthy();
    });

    it('tree container is hidden when not in review mode', () => {
      const { getByTestId } = render(
        <PuzzleSidebar {...makeProps({ isReviewMode: false })} />,
      );
      const treeContainer = getByTestId('tree-container');
      expect(treeContainer.className).toContain('hidden');
    });

    it('tree container is visible when in review mode', () => {
      const { getByTestId } = render(
        <PuzzleSidebar {...makeProps({ isReviewMode: true })} />,
      );
      const treeContainer = getByTestId('tree-container');
      expect(treeContainer.className).toContain('block');
      expect(treeContainer.className).not.toContain('hidden');
    });
  });
});
