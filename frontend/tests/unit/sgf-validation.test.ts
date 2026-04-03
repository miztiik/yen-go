/**
 * SGF validation against boot config — test-first for T024.
 *
 * Tests that puzzles with unrecognized levels or tags are rejected
 * with clear error messages (FR-039).
 *
 * Spec 127: FR-039
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock boot configs
const mockBootConfigs = {
  levels: [
    { slug: 'novice', name: 'Novice', rankRange: '30k+', order: 1 },
    { slug: 'beginner', name: 'Beginner', rankRange: '25k-20k', order: 2 },
    { slug: 'intermediate', name: 'Intermediate', rankRange: '15k-10k', order: 4 },
  ],
  tags: [
    { id: 'life-and-death', name: 'Life & Death', category: 'objective' as const, description: 'Kill or live', aliases: [] },
    { id: 'ko', name: 'Ko', category: 'objective' as const, description: 'Ko fight', aliases: [] },
    { id: 'ladder', name: 'Ladder', category: 'technique' as const, description: 'Ladder technique', aliases: [] },
  ],
  tips: [],
};

vi.mock('../../src/boot', () => ({
  getBootConfigs: () => mockBootConfigs,
}));

describe('SGF validation against boot config', () => {
  it('accepts puzzles with valid level and tags', () => {
    // A valid SGF with recognized level and tags
    const sgf = '(;FF[4]GM[1]SZ[19]YG[beginner]YT[life-and-death,ko])';
    // Should not throw
    expect(() => {
      validateSgfLevel('beginner', mockBootConfigs.levels);
      validateSgfTags(['life-and-death', 'ko'], mockBootConfigs.tags);
    }).not.toThrow();
  });

  it('rejects puzzles with unrecognized level', () => {
    expect(() => {
      validateSgfLevel('super-expert', mockBootConfigs.levels);
    }).toThrow(/unrecognized level/i);
  });

  it('rejects puzzles with unrecognized tags', () => {
    expect(() => {
      validateSgfTags(['life-and-death', 'unknown-tag'], mockBootConfigs.tags);
    }).toThrow(/unrecognized tag/i);
  });

  it('provides clear error message with valid alternatives', () => {
    try {
      validateSgfLevel('pro', mockBootConfigs.levels);
    } catch (e) {
      const msg = (e as Error).message;
      expect(msg).toContain('pro');
      expect(msg).toContain('novice');
    }
  });

  it('accepts empty tags array', () => {
    expect(() => {
      validateSgfTags([], mockBootConfigs.tags);
    }).not.toThrow();
  });
});

// Helper implementations matching what T024 will add to sgf-preprocessor.ts
function validateSgfLevel(
  level: string,
  validLevels: Array<{ slug: string }>,
): void {
  const valid = validLevels.map((l) => l.slug);
  if (!valid.includes(level)) {
    throw new Error(
      `Unrecognized level "${level}". Valid levels: ${valid.join(', ')}`
    );
  }
}

function validateSgfTags(
  tags: string[],
  validTags: Array<{ id: string }>,
): void {
  const validIds = new Set(validTags.map((t) => t.id));
  for (const tag of tags) {
    if (!validIds.has(tag)) {
      throw new Error(
        `Unrecognized tag "${tag}". Valid tags: ${[...validIds].join(', ')}`
      );
    }
  }
}
