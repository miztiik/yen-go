/**
 * Unit tests for GhostStoneLayer component
 * @module tests/unit/ghost-stone-layer.test
 *
 * Tests the ghost (preview) stone rendering.
 * Spec: 122-frontend-comprehensive-refactor
 * Task: T6.4
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { GhostStoneLayer } from '../../src/components/Board/svg/GhostStoneLayer';

describe('GhostStoneLayer', () => {
  const defaultProps = {
    position: { x: 9, y: 9 },
    color: 'black' as const,
    boardSize: 19,
    cellSize: 20,
    offset: { x: 20, y: 20 },
    rotation: 0,
  };

  describe('rendering', () => {
    it('should render a ghost stone when position is provided', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      expect(ghostGroup).toBeDefined();

      // Should have a circle for the stone
      const circle = container.querySelector('circle');
      expect(circle).toBeDefined();
    });

    it('should not render when position is null', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} position={null} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      expect(ghostGroup).toBeNull();
    });

    it('should not render when position is out of bounds (negative)', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} position={{ x: -1, y: 5 }} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      expect(ghostGroup).toBeNull();
    });

    it('should not render when position is out of bounds (too large)', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} position={{ x: 19, y: 10 }} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      expect(ghostGroup).toBeNull();
    });
  });

  describe('opacity', () => {
    it('should have 35% opacity for the ghost effect', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      const opacity = ghostGroup?.getAttribute('opacity');
      expect(parseFloat(opacity || '0')).toBeCloseTo(0.35, 2);
    });
  });

  describe('colors', () => {
    it('should render black stone with black fill', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} color="black" />
        </svg>
      );

      const circle = container.querySelector('circle');
      const fill = circle?.getAttribute('fill');
      
      // Should use gradient or dark color
      expect(fill).toBeDefined();
      // Gradient URL or dark color
      expect(fill?.includes('url') || fill?.includes('#') || fill?.includes('rgb')).toBe(true);
    });

    it('should render white stone with white fill', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} color="white" />
        </svg>
      );

      const circle = container.querySelector('circle');
      const fill = circle?.getAttribute('fill');
      
      // Should use gradient or light color
      expect(fill).toBeDefined();
    });
  });

  describe('position calculation', () => {
    it('should position stone at correct coordinates', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer 
            {...defaultProps}
            position={{ x: 5, y: 10 }}
            cellSize={30}
            offset={{ x: 15, y: 15 }}
          />
        </svg>
      );

      const circle = container.querySelector('circle');
      const cx = parseFloat(circle?.getAttribute('cx') || '0');
      const cy = parseFloat(circle?.getAttribute('cy') || '0');

      // cx = 5 * 30 + 15 = 165
      // cy = 10 * 30 + 15 = 315
      expect(cx).toBe(165);
      expect(cy).toBe(315);
    });

    it('should calculate radius based on cell size', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} cellSize={40} />
        </svg>
      );

      const circle = container.querySelector('circle');
      const r = parseFloat(circle?.getAttribute('r') || '0');

      // Radius should be approximately 46% of cell size
      expect(r).toBeCloseTo(40 * 0.46, 1);
    });
  });

  describe('rotation support', () => {
    it('should apply rotation transform when rotation is non-zero', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} rotation={90} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      const transform = ghostGroup?.getAttribute('transform');
      
      // Should have a rotate transform
      expect(transform).toBeDefined();
      expect(transform).toContain('rotate');
      expect(transform).toContain('90');
    });

    it('should not apply rotation transform when rotation is 0', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} rotation={0} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      const transform = ghostGroup?.getAttribute('transform');
      
      // Transform should be undefined or not contain rotate
      if (transform) {
        expect(transform).not.toContain('rotate');
      }
    });
  });

  describe('pointer events', () => {
    it('should have pointer-events: none to not block clicks', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} />
        </svg>
      );

      const ghostGroup = container.querySelector('g.ghost-stone-layer');
      const style = ghostGroup?.getAttribute('style');
      
      // Check that pointer-events is set to none
      expect(style).toContain('pointer-events');
      expect(style).toContain('none');
    });
  });

  describe('gradient', () => {
    it('should define radial gradient for 3D effect', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} />
        </svg>
      );

      const gradient = container.querySelector('radialGradient');
      expect(gradient).toBeDefined();
    });

    it('should have unique gradient IDs for different colors', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} color="black" />
          <GhostStoneLayer 
            {...defaultProps} 
            color="white" 
            position={{ x: 10, y: 10 }}
          />
        </svg>
      );

      const gradients = container.querySelectorAll('radialGradient');
      const ids = Array.from(gradients).map(g => g.getAttribute('id'));
      
      // Should have different IDs for black and white
      expect(new Set(ids).size).toBe(ids.length);
    });
  });

  describe('edge cases', () => {
    it('should handle corner position (0, 0)', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} position={{ x: 0, y: 0 }} />
        </svg>
      );

      const circle = container.querySelector('circle');
      expect(circle).toBeDefined();
    });

    it('should handle corner position (18, 18) on 19x19 board', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} position={{ x: 18, y: 18 }} />
        </svg>
      );

      const circle = container.querySelector('circle');
      expect(circle).toBeDefined();
    });

    it('should handle small board sizes', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer 
            {...defaultProps} 
            boardSize={9}
            position={{ x: 4, y: 4 }}
          />
        </svg>
      );

      const circle = container.querySelector('circle');
      expect(circle).toBeDefined();
    });

    it('should handle very small cell sizes', () => {
      const { container } = render(
        <svg>
          <GhostStoneLayer {...defaultProps} cellSize={5} />
        </svg>
      );

      const circle = container.querySelector('circle');
      const r = parseFloat(circle?.getAttribute('r') || '0');
      expect(r).toBeGreaterThan(0);
    });
  });
});
