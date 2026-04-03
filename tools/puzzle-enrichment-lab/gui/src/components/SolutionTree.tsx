/**
 * SolutionTree.tsx — Interactive SVG tree display for solution variations.
 * Click nodes to navigate. Correct paths highlighted green, wrong red.
 */

import { useRef, useCallback } from 'preact/hooks';
import { solutionTree, currentNode } from '../store/state';
import type { TreeNode } from '../types';

interface Props {
  onNodeClick?: (node: TreeNode) => void;
}

const NODE_R = 10;
const LEVEL_W = 36;
const SIBLING_H = 32;

interface LayoutNode {
  node: TreeNode;
  x: number;
  y: number;
  children: LayoutNode[];
}

/** Lay out a tree left-to-right for SVG rendering (GoProblems-style) */
function layoutTree(node: TreeNode, x: number, y: number): LayoutNode {
  const children: LayoutNode[] = [];
  let offset = y - ((node.children.length - 1) * SIBLING_H) / 2;
  for (const child of node.children) {
    children.push(layoutTree(child, x + LEVEL_W, offset));
    offset += SIBLING_H;
  }
  return { node, x, y, children };
}

function flattenLayout(ln: LayoutNode): LayoutNode[] {
  const result: LayoutNode[] = [ln];
  for (const c of ln.children) {
    result.push(...flattenLayout(c));
  }
  return result;
}

function nodeColor(node: TreeNode): string {
  if (node.isCorrect === true) return '#22c55e';
  if (node.isCorrect === false) return '#ef4444';
  return '#6b7280';
}

export function SolutionTree({ onNodeClick }: Props) {
  const tree = solutionTree.value;
  const autoPlayRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopAutoPlay = useCallback(() => {
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
  }, []);

  const startAutoPlay = useCallback(() => {
    stopAutoPlay();
    autoPlayRef.current = setInterval(() => {
      const node = currentNode.value;
      if (!node || node.children.length === 0) {
        stopAutoPlay();
        return;
      }
      // Walk the first (main) variation
      const next = node.children[0];
      onNodeClick?.(next);
    }, 800);
  }, [onNodeClick, stopAutoPlay]);

  if (!tree) {
    return <div class="solution-tree-empty">No solution tree loaded</div>;
  }

  const layout = layoutTree(tree, 24, 100);
  const all = flattenLayout(layout);

  // Calculate SVG bounds for horizontal (left-to-right) layout
  const xs = all.map(n => n.x);
  const ys = all.map(n => n.y);
  const width = Math.max(200, Math.max(...xs) + 40);
  const height = Math.max(60, (Math.max(...ys) - Math.min(...ys)) + 60);
  const offsetY = -Math.min(...ys) + 30;

  return (
    <div class="solution-tree-container">
      <div class="solution-tree-header">
        <h3>Solution Tree</h3>
        <div class="solution-tree-controls">
          <button onClick={startAutoPlay} class="btn-sm" title="Auto-play main line">
            ▶ Play
          </button>
          <button onClick={stopAutoPlay} class="btn-sm" title="Stop auto-play">
            ■ Stop
          </button>
        </div>
      </div>
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        class="solution-tree-svg"
      >
        {/* Edges */}
        {all.map(ln =>
          ln.children.map(child => (
            <line
              key={`${ln.node.id}-${child.node.id}`}
              x1={ln.x}
              y1={ln.y + offsetY}
              x2={child.x}
              y2={child.y + offsetY}
              stroke="#555"
              stroke-width={1.5}
            />
          ))
        )}
        {/* Nodes */}
        {all.map(ln => {
          const isCurrent = currentNode.value?.id === ln.node.id;
          return (
            <g
              key={ln.node.id}
              onClick={() => onNodeClick?.(ln.node)}
              style={{ cursor: 'pointer' }}
            >
              <circle
                cx={ln.x}
                cy={ln.y + offsetY}
                r={NODE_R}
                fill={nodeColor(ln.node)}
                stroke={isCurrent ? '#fff' : 'none'}
                stroke-width={isCurrent ? 3 : 0}
              />
              {ln.node.move && (
                <text
                  x={ln.x}
                  y={ln.y + offsetY + 3.5}
                  text-anchor="middle"
                  fill="#fff"
                  font-size="9"
                  font-weight="bold"
                >
                  {ln.node.move.player}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
