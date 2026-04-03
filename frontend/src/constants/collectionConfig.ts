import type { CollectionType } from '@/models/collection';

/**
 * Per-collection-type shuffle policy.
 * true = randomize puzzle order per session (for practice/training variety)
 * false = preserve author's intended sequence order (for books/graded study)
 * Toggleable backend config — not user-facing.
 */
export const SHUFFLE_POLICY: Record<CollectionType, boolean> = {
  graded: false,    // Learning Paths: preserve difficulty ordering
  author: false,    // Books: preserve author's sequence
  technique: true,  // Practice: randomize per session
  reference: true,  // Practice: randomize per session
  system: false,
};

/**
 * Fisher-Yates (Knuth) shuffle — returns a new shuffled copy of the array.
 * Does not mutate the original array.
 */
export function shuffleArray<T>(arr: readonly T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j]!, shuffled[i]!];
  }
  return shuffled;
}
