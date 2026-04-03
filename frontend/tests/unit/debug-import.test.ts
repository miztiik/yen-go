/**
 * Debug test to isolate import hang issue
 * Testing static imports vs. dynamic imports and renderHook
 */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useTreeNavigation } from '../../src/hooks/useTreeNavigation';
import type { SolutionNode } from '../../src/types/puzzle-internal';

function createLinearTree(): SolutionNode {
  return {
    move: 'root',
    player: 'B',
    isCorrect: true,
    isUserMove: true,
    children: [
      {
        move: 'aa',
        player: 'W',
        isCorrect: true,
        isUserMove: false,
        children: [],
      },
    ],
  };
}

describe('Static Import Test', () => {
  it('should import useTreeNavigation statically', () => {
    console.log('useTreeNavigation imported:', typeof useTreeNavigation);
    expect(useTreeNavigation).toBeDefined();
    expect(typeof useTreeNavigation).toBe('function');
  });

  it('should render the hook', () => {
    console.log('Rendering hook...');
    const tree = createLinearTree();
    const { result } = renderHook(() => useTreeNavigation({ tree }));
    console.log('Hook rendered, state:', result.current.state);
    expect(result.current.state).toBeDefined();
    expect(result.current.layout).toBeDefined();
  });

  it('should navigate to next node', () => {
    const tree = createLinearTree();
    const { result } = renderHook(() => useTreeNavigation({ tree }));
    
    act(() => {
      result.current.next();
    });
    
    expect(result.current.state.current.node.move).toBe('aa');
  });
});
