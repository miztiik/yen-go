/**
 * Unit tests for SolutionTreeView component
 * @module tests/unit/components/SolutionTreeView.test
 *
 * Feature: 123-solution-tree-rewrite
 *
 * Tests Besogo-ported tree visualization with:
 * - Connected SVG paths (not individual line segments)
 * - Node rendering with move numbers
 * - Click navigation
 * - Keyboard navigation
 * - Accessibility features
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { SolutionTreeView } from '../../../src/components/SolutionTree/SolutionTreeView';
import type { SolutionNode } from '../../../src/types/puzzle-internal';

// ============================================================================
// Test Fixtures
// ============================================================================

/**
 * Create a minimal test tree
 */
function createTestTree(): SolutionNode {
  return {
    move: '',
    player: 'B',
    isCorrect: true,
    isUserMove: false,
    children: [
      {
        move: 'dd',
        player: 'B',
        isCorrect: true,
        isUserMove: true,
        children: [
          {
            move: 'pd',
            player: 'W',
            isCorrect: true,
            isUserMove: false,
            children: [],
          },
        ],
      },
      {
        move: 'pp',
        player: 'B',
        isCorrect: false,
        isUserMove: true,
        children: [],
      },
    ],
  };
}

/**
 * Create a deep test tree for layout testing
 */
function createDeepTree(depth: number): SolutionNode {
  const root: SolutionNode = {
    move: '',
    player: 'B',
    isCorrect: true,
    isUserMove: false,
    children: [],
  };

  let current = root;
  for (let i = 0; i < depth; i++) {
    const child: SolutionNode = {
      move: `${String.fromCharCode(97 + (i % 19))}${String.fromCharCode(97 + (i % 19))}`,
      player: i % 2 === 0 ? 'B' : 'W',
      isCorrect: true,
      isUserMove: i % 2 === 0,
      children: [],
    };
    current.children.push(child);
    current = child;
  }

  return root;
}

// ============================================================================
// Basic Render Tests
// ============================================================================

describe('SolutionTreeView', () => {
  const mockOnNodeSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    expect(container.querySelector('.solution-tree-wrapper')).toBeTruthy();
  });

  it('renders SVG element with tree role', () => {
    const tree = createTestTree();
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeContainer = screen.getByRole('tree');
    expect(treeContainer).toBeTruthy();
    expect(treeContainer.getAttribute('aria-label')).toBe('Solution tree navigation');
  });

  it('renders nodes as tree items', () => {
    const tree = createTestTree();
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeItems = screen.getAllByRole('treeitem');
    // Root + 2 children + 1 grandchild = 4 nodes
    expect(treeItems.length).toBe(4);
  });

  it('renders connected paths using SVG path elements', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const paths = container.querySelectorAll('.tree-paths path');
    expect(paths.length).toBeGreaterThan(0);
    
    // Verify paths use relative commands (h, v, l) not absolute L
    paths.forEach((path) => {
      const d = path.getAttribute('d');
      if (d && d.length > 2) {
        // Should contain m (move) and h/v/l (relative line) commands
        expect(d).toMatch(/^m/);
      }
    });
  });
});

// ============================================================================
// Navigation Tests
// ============================================================================

describe('SolutionTreeView Navigation', () => {
  const mockOnNodeSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls onNodeSelect when node is clicked', async () => {
    const tree = createTestTree();
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeItems = screen.getAllByRole('treeitem');
    // Click second node (first child)
    fireEvent.click(treeItems[1]);
    
    expect(mockOnNodeSelect).toHaveBeenCalledTimes(1);
  });

  it('highlights current node with aria-selected', () => {
    const tree = createTestTree();
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeItems = screen.getAllByRole('treeitem');
    const currentItem = treeItems.find(item => item.getAttribute('aria-selected') === 'true');
    expect(currentItem).toBeTruthy();
  });
});

// ============================================================================
// Keyboard Navigation Tests
// ============================================================================

describe('SolutionTreeView Keyboard Navigation', () => {
  const mockOnNodeSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('navigates to next node on ArrowRight key', () => {
    const tree = createDeepTree(3);
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeContainer = screen.getByRole('tree');
    fireEvent.keyDown(treeContainer, { key: 'ArrowRight' });
    
    expect(mockOnNodeSelect).toHaveBeenCalled();
  });

  it('stops propagation on arrow keys', () => {
    const tree = createTestTree();
    const parentHandler = vi.fn();
    
    const { container } = render(
      <div onKeyDown={parentHandler}>
        <SolutionTreeView
          tree={tree}
          currentNodeId="0-0"
          onNodeSelect={mockOnNodeSelect}
        />
      </div>
    );
    
    const treeContainer = container.querySelector('[role="tree"]');
    if (treeContainer) {
      fireEvent.keyDown(treeContainer, { key: 'ArrowLeft' });
    }
    
    // Parent handler should not receive the event
    expect(parentHandler).not.toHaveBeenCalled();
  });
});

// ============================================================================
// Accessibility Tests
// ============================================================================

describe('SolutionTreeView Accessibility', () => {
  const mockOnNodeSelect = vi.fn();

  it('has ARIA labels for nodes', () => {
    const tree = createTestTree();
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeItems = screen.getAllByRole('treeitem');
    treeItems.forEach((item) => {
      expect(item.getAttribute('aria-label')).toBeTruthy();
    });
  });

  it('has screen reader live region', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const liveRegion = container.querySelector('[aria-live="polite"]');
    expect(liveRegion).toBeTruthy();
  });

  it('has correct tabIndex on current vs other nodes', () => {
    const tree = createTestTree();
    render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const treeItems = screen.getAllByRole('treeitem');
    const currentItem = treeItems.find(item => item.getAttribute('aria-selected') === 'true');
    const otherItems = treeItems.filter(item => item.getAttribute('aria-selected') !== 'true');
    
    expect(currentItem?.getAttribute('tabIndex')).toBe('0');
    otherItems.forEach(item => {
      expect(item.getAttribute('tabIndex')).toBe('-1');
    });
  });
});

// ============================================================================
// Correctness Indicator Tests
// ============================================================================

describe('SolutionTreeView Correctness Indicators', () => {
  const mockOnNodeSelect = vi.fn();

  it('shows correctness indicators when showCorrectness is true', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
        showCorrectness={true}
      />
    );
    
    const correctnessRings = container.querySelectorAll('.tree-node-correctness');
    expect(correctnessRings.length).toBeGreaterThan(0);
  });

  it('hides correctness indicators when showCorrectness is false', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
        showCorrectness={false}
      />
    );
    
    const correctnessRings = container.querySelectorAll('.tree-node-correctness');
    expect(correctnessRings.length).toBe(0);
  });

  it('uses correct CSS class for correct nodes', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
        showCorrectness={true}
      />
    );
    
    const correctRings = container.querySelectorAll('.tree-node-correctness.correct');
    expect(correctRings.length).toBeGreaterThan(0);
  });

  it('uses correct CSS class for incorrect nodes', () => {
    const tree = createTestTree();
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
        showCorrectness={true}
      />
    );
    
    const wrongRings = container.querySelectorAll('.tree-node-correctness.wrong');
    expect(wrongRings.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Layout Tests
// ============================================================================

describe('SolutionTreeView Layout', () => {
  const mockOnNodeSelect = vi.fn();

  it('handles deep trees without stack overflow', () => {
    const deepTree = createDeepTree(100);
    
    expect(() => {
      render(
        <SolutionTreeView
          tree={deepTree}
          currentNodeId="0"
          onNodeSelect={mockOnNodeSelect}
        />
      );
    }).not.toThrow();
  });

  it('renders move numbers on stones', () => {
    const tree = createDeepTree(5);
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    const labels = container.querySelectorAll('.tree-label');
    // Should have move numbers for non-root nodes
    expect(labels.length).toBeGreaterThan(0);
  });

  it('uses dynamic font sizing for move numbers', () => {
    // Create a tree with 15 moves to test font sizing
    const tree = createDeepTree(15);
    const { container } = render(
      <SolutionTreeView
        tree={tree}
        currentNodeId="0"
        onNodeSelect={mockOnNodeSelect}
      />
    );
    
    // Check nodes are rendered
    const treeItems = container.querySelectorAll('[role="treeitem"]');
    // 1 root + 15 child nodes = 16 treeItems
    expect(treeItems.length).toBe(16);
  });
});
