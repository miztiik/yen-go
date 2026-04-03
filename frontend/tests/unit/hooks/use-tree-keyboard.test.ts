/**
 * Unit tests for useTreeKeyboard hook
 * @module tests/unit/hooks/use-tree-keyboard.test
 *
 * Tests keyboard navigation for the solution tree.
 * Spec: 122-frontend-comprehensive-refactor
 * Task: T6.1
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/preact';
import { useTreeKeyboard, type UseTreeKeyboardOptions } from '../../../src/hooks/useTreeKeyboard';
import type { VisualTreeNode, TreeLayoutResult } from '../../../src/types/tree';

/**
 * Create a mock VisualTreeNode for testing
 */
function createMockNode(
  id: string,
  children: VisualTreeNode[] = [],
  parent: VisualTreeNode | null = null
): VisualTreeNode {
  const node: VisualTreeNode = {
    id,
    move: id === 'root' ? '' : 'ab',
    color: id === 'root' ? 'empty' : (id.charCodeAt(0) % 2 === 0 ? 'black' : 'white'),
    x: 0,
    y: 0,
    isMainLine: true,
    depth: parent ? parent.depth + 1 : 0,
    children,
    parent,
    originalNode: {
      id,
      move: 'ab',
      color: 'B',
      comment: null,
      isCorrect: true,
      children: [],
    },
  };
  
  // Set parent reference for all children
  for (const child of children) {
    child.parent = node;
  }
  
  return node;
}

/**
 * Create a mock TreeLayoutResult for testing
 */
function createMockLayout(root: VisualTreeNode): TreeLayoutResult {
  const nodes: VisualTreeNode[] = [];
  
  function collectNodes(node: VisualTreeNode): void {
    nodes.push(node);
    for (const child of node.children) {
      collectNodes(child);
    }
  }
  
  collectNodes(root);
  
  return {
    nodes,
    root,  // Include root reference for Home navigation
    width: 100,
    height: 100,
    nodeSize: 24,
  };
}

/**
 * Create a keyboard event for testing
 */
function createKeyboardEvent(key: string, options: Partial<KeyboardEvent> = {}): KeyboardEvent {
  return {
    key,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    ...options,
  } as unknown as KeyboardEvent;
}

describe('useTreeKeyboard', () => {
  let mockOnNavigate: ReturnType<typeof vi.fn>;
  let mockOnSelect: ReturnType<typeof vi.fn>;
  
  beforeEach(() => {
    mockOnNavigate = vi.fn();
    mockOnSelect = vi.fn();
  });

  describe('basic navigation', () => {
    it('should navigate to first child on ArrowRight', () => {
      // Create tree: root -> child1
      const child1 = createMockNode('child1');
      const root = createMockNode('root', [child1]);
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowRight'));
      
      expect(mockOnNavigate).toHaveBeenCalledWith(child1);
    });

    it('should navigate to parent on ArrowLeft', () => {
      const child1 = createMockNode('child1');
      const root = createMockNode('root', [child1]);
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: child1,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowLeft'));
      
      expect(mockOnNavigate).toHaveBeenCalledWith(root);
    });

    it('should navigate down in depth-first order on ArrowDown', () => {
      // Tree: root -> child1 -> grandchild1
      const grandchild1 = createMockNode('grandchild1');
      const child1 = createMockNode('child1', [grandchild1]);
      const root = createMockNode('root', [child1]);
      grandchild1.parent = child1;
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowDown'));
      
      expect(mockOnNavigate).toHaveBeenCalledWith(child1);
    });

    it('should navigate up in depth-first order on ArrowUp', () => {
      const grandchild1 = createMockNode('grandchild1');
      const child1 = createMockNode('child1', [grandchild1]);
      const root = createMockNode('root', [child1]);
      grandchild1.parent = child1;
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: grandchild1,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowUp'));
      
      expect(mockOnNavigate).toHaveBeenCalledWith(child1);
    });
  });

  describe('Home/End navigation', () => {
    it('should navigate to root on Home', () => {
      const grandchild1 = createMockNode('grandchild1');
      const child1 = createMockNode('child1', [grandchild1]);
      const root = createMockNode('root', [child1]);
      grandchild1.parent = child1;
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: grandchild1,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('Home'));
      
      expect(mockOnNavigate).toHaveBeenCalledWith(root);
    });

    it('should navigate to last node on End', () => {
      const grandchild1 = createMockNode('grandchild1');
      const child1 = createMockNode('child1', [grandchild1]);
      const root = createMockNode('root', [child1]);
      grandchild1.parent = child1;
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('End'));
      
      expect(mockOnNavigate).toHaveBeenCalledWith(grandchild1);
    });
  });

  describe('selection', () => {
    it('should call onSelect on Enter', () => {
      const root = createMockNode('root');
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
          onSelect: mockOnSelect,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('Enter'));
      
      expect(mockOnSelect).toHaveBeenCalledWith(root);
    });

    it('should call onSelect on Space', () => {
      const root = createMockNode('root');
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
          onSelect: mockOnSelect,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent(' '));
      
      expect(mockOnSelect).toHaveBeenCalledWith(root);
    });
  });

  describe('event handling', () => {
    it('should prevent default and stop propagation for handled keys', () => {
      const root = createMockNode('root', [createMockNode('child1')]);
      root.children[0].parent = root;
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      const event = createKeyboardEvent('ArrowRight');
      result.current.handleKeyDown(event);
      
      expect(event.preventDefault).toHaveBeenCalled();
      expect(event.stopPropagation).toHaveBeenCalled();
    });

    it('should ignore modifier key combinations', () => {
      const root = createMockNode('root');
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      // Ctrl+ArrowRight should be ignored
      const event = createKeyboardEvent('ArrowRight', { ctrlKey: true });
      result.current.handleKeyDown(event);
      
      expect(mockOnNavigate).not.toHaveBeenCalled();
    });

    it('should not navigate when disabled', () => {
      const root = createMockNode('root', [createMockNode('child1')]);
      root.children[0].parent = root;
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
          enabled: false,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowRight'));
      
      expect(mockOnNavigate).not.toHaveBeenCalled();
    });
  });

  describe('edge cases', () => {
    it('should not navigate if at root and pressing ArrowLeft', () => {
      const root = createMockNode('root');
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowLeft'));
      
      expect(mockOnNavigate).not.toHaveBeenCalled();
    });

    it('should not navigate if at leaf and pressing ArrowRight', () => {
      const child1 = createMockNode('child1');
      const root = createMockNode('root', [child1]);
      child1.parent = root;
      
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: child1,
          onNavigate: mockOnNavigate,
        })
      );

      result.current.handleKeyDown(createKeyboardEvent('ArrowRight'));
      
      expect(mockOnNavigate).not.toHaveBeenCalled();
    });
  });

  describe('focus management', () => {
    it('should provide a focus function', () => {
      const root = createMockNode('root');
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      expect(typeof result.current.focus).toBe('function');
    });

    it('should provide a containerRef', () => {
      const root = createMockNode('root');
      const layout = createMockLayout(root);
      
      const { result } = renderHook(() =>
        useTreeKeyboard({
          layout,
          currentNode: root,
          onNavigate: mockOnNavigate,
        })
      );

      expect(result.current.containerRef).toBeDefined();
    });
  });
});
