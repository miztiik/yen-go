/**
 * SGF Metadata Extractor — tree-based, no regex.
 *
 * Uses a proper recursive-descent SGF parser (`parseSgfToTree`) to read
 * YenGo custom properties from the parsed tree. This module exists ONLY
 * for sidebar metadata (level, tags, hints, collections).
 *
 * Also provides the canonical `parseSgfToTree()` used by `sgf-to-puzzle.ts`
 * for PuzzleObject conversion (DRY — single parser).
 *
 * Pipeline:
 *   Raw SGF → sgfToPuzzle() → PuzzleObject → goban   (board, stones, tree, puzzle mechanics)
 *   Raw SGF → parseSgfToTree() → metadata            (level, tags, hints, collections for sidebar)
 *
 * @module lib/sgf-metadata
 */

import { FALLBACK_LEVEL } from './levels/level-defaults';
import { contentTypeIdToSlug } from '../services/configService';

// ---------------------------------------------------------------------------
// Internal SGF Tree Representation
// ---------------------------------------------------------------------------

export interface SgfNode {
  properties: Record<string, string[]>;
  children: SgfNode[];
}

// ---------------------------------------------------------------------------
// SGF Parser — proper recursive descent (NOT regex)
// ---------------------------------------------------------------------------

/**
 * Parse an SGF string into an internal tree of SgfNode objects.
 *
 * Handles:
 * - Multi-value properties: AB[aa][bb][cc]
 * - Escaped characters within values: C[text with \] bracket]
 * - Nested variations: (;B[aa](;W[bb])(;W[cc]))
 * - Comments on nodes: C[Good move!]
 * - ALL properties preserved (YG, YT, YH, YC, YL, BM, etc.)
 */
export function parseSgfToTree(sgf: string): SgfNode | null {
  let pos = 0;

  function skipWhitespace(): void {
    while (pos < sgf.length && /\s/.test(sgf[pos]!)) pos++;
  }

  function parseValue(): string {
    if (sgf[pos] !== '[') return '';
    pos++; // skip '['
    let value = '';
    while (pos < sgf.length) {
      const ch = sgf[pos]!;
      if (ch === '\\' && pos + 1 < sgf.length) {
        // SGF FF[4] escape: \] → ], \\ → \
        const next = sgf[pos + 1]!;
        if (next === ']' || next === '\\') {
          value += next;
          pos += 2;
        } else {
          value += ch + next;
          pos += 2;
        }
      } else if (ch === ']') {
        pos++; // skip ']'
        return value;
      } else {
        value += ch;
        pos++;
      }
    }
    return value;
  }

  function parseNode(): SgfNode {
    const node: SgfNode = { properties: {}, children: [] };

    if (sgf[pos] === ';') pos++;

    skipWhitespace();
    while (pos < sgf.length) {
      const ch = sgf[pos]!;
      if (ch === ';' || ch === '(' || ch === ')') break;

      if (ch >= 'A' && ch <= 'Z') {
        let propName = '';
        while (pos < sgf.length && sgf[pos]! >= 'A' && sgf[pos]! <= 'Z') {
          propName += sgf[pos]!;
          pos++;
        }

        const values: string[] = [];
        skipWhitespace();
        while (pos < sgf.length && sgf[pos] === '[') {
          values.push(parseValue());
          skipWhitespace();
        }

        if (propName && values.length > 0) {
          node.properties[propName] = values;
        }
      } else {
        pos++;
      }
      skipWhitespace();
    }

    return node;
  }

  function parseSequence(): SgfNode[] {
    const nodes: SgfNode[] = [];
    skipWhitespace();

    while (pos < sgf.length) {
      const ch = sgf[pos]!;
      if (ch === ';') {
        nodes.push(parseNode());
        skipWhitespace();
      } else if (ch === '(' || ch === ')') {
        break;
      } else {
        pos++;
        skipWhitespace();
      }
    }

    return nodes;
  }

  function parseGameTree(): SgfNode | null {
    skipWhitespace();
    if (pos >= sgf.length || sgf[pos] !== '(') return null;
    pos++; // skip '('

    const sequence = parseSequence();
    if (sequence.length === 0) {
      while (pos < sgf.length && sgf[pos] !== ')') pos++;
      if (pos < sgf.length) pos++;
      return null;
    }

    // Link sequence nodes
    for (let i = 0; i < sequence.length - 1; i++) {
      sequence[i]!.children.push(sequence[i + 1]!);
    }

    // Parse child variations
    const lastNode = sequence[sequence.length - 1]!;
    skipWhitespace();
    while (pos < sgf.length && sgf[pos] === '(') {
      const childTree = parseGameTree();
      if (childTree) {
        lastNode.children.push(childTree);
      }
      skipWhitespace();
    }

    if (pos < sgf.length && sgf[pos] === ')') pos++;

    return sequence[0]!;
  }

  return parseGameTree();
}

// ---------------------------------------------------------------------------
// Tree-based Metadata Extraction
// ---------------------------------------------------------------------------

/**
 * Read a single property value from a parsed SgfNode.
 */
function readProperty(node: SgfNode, key: string): string | undefined {
  return node.properties[key]?.[0];
}

/**
 * Parse comma-separated string → sorted deduplicated array.
 */
function parseCommaSeparated(value: string): string[] {
  const items = value.split(',').map(s => s.trim()).filter(Boolean);
  return [...new Set(items)].sort();
}

/** Structured collection membership parsed from a YL entry. */
export interface CollectionMembership {
  /** Collection slug (without chapter/position suffix). */
  readonly slug: string;
  /** Chapter string (empty = no chapter, "0" = chapterless sentinel). */
  readonly chapter: string;
  /** Position within chapter (0 = no position info). */
  readonly position: number;
}

/**
 * Parse YL property into bare slugs and structured memberships.
 *
 * Handles all YL formats:
 * - `slug`              -> { slug, chapter: '', position: 0 }
 * - `slug:42`           -> { slug, chapter: '', position: 42 }
 * - `slug:3/12`         -> { slug, chapter: '3', position: 12 }
 * - `slug:seki/3`       -> { slug, chapter: 'seki', position: 3 }
 *
 * Multiple entries are comma-separated.
 */
function parseCollectionsWithChapters(rawYL: string): {
  slugs: readonly string[];
  memberships: readonly CollectionMembership[];
} {
  const items = rawYL.split(',').map(s => s.trim()).filter(Boolean);
  const slugs: string[] = [];
  const memberships: CollectionMembership[] = [];
  const seen = new Set<string>();

  for (const item of items) {
    const colonIdx = item.indexOf(':');
    if (colonIdx === -1) {
      // Bare slug: "life-and-death"
      if (!seen.has(item)) {
        seen.add(item);
        slugs.push(item);
        memberships.push({ slug: item, chapter: '', position: 0 });
      }
    } else {
      const slug = item.substring(0, colonIdx);
      const suffix = item.substring(colonIdx + 1);
      const slashIdx = suffix.indexOf('/');

      let chapter = '';
      let position = 0;

      if (slashIdx === -1) {
        // Position only: "slug:42"
        position = parseInt(suffix, 10) || 0;
      } else {
        // Chapter/position: "slug:3/12" or "slug:seki/3"
        chapter = suffix.substring(0, slashIdx);
        position = parseInt(suffix.substring(slashIdx + 1), 10) || 0;
      }

      if (!seen.has(slug)) {
        seen.add(slug);
        slugs.push(slug);
      }
      memberships.push({ slug, chapter, position });
    }
  }

  return { slugs: slugs.sort(), memberships };
}

/**
 * Parse pipe-delimited string → array (max 3 items).
 */
function parsePipeDelimited(value: string, max = 3): string[] {
  return value.split('|').map(s => s.trim()).filter(Boolean).slice(0, max);
}

/**
 * Extract the first correct move from the parsed SGF tree.
 *
 * Walks child nodes looking for the first `B[]` or `W[]` move
 * that is NOT marked with `BM[]` (bad move).
 */
function extractFirstCorrectMoveFromTree(rootNode: SgfNode): string | null {
  // Look at direct children of the root
  for (const child of rootNode.children) {
    const bMove = child.properties['B']?.[0];
    const wMove = child.properties['W']?.[0];
    const moveCoord = bMove ?? wMove;

    if (moveCoord === undefined) continue;

    // Skip pass moves
    if (moveCoord === '' || moveCoord === 'tt') continue;

    // Skip moves marked as bad (BM[])
    if (child.properties['BM']) continue;

    return moveCoord;
  }

  // If all children have BM, no correct first move
  return null;
}

/**
 * Extract YenGo metadata from a parsed SGF tree.
 *
 * Reads properties directly from the root node — no regex needed.
 * Properties that goban doesn't understand (YG, YT, YH, YK, YO, YL, YC)
 * are read here for sidebar display.
 */

export function extractMetadataFromTree(
  rootNode: SgfNode,
): {
  level: string;
  tags: readonly string[];
  hints: readonly string[];
  koContext: string;
  moveOrder: string;
  collections: readonly string[];
  collectionMemberships: readonly CollectionMembership[];
  firstCorrectMove: string | null;
  cornerPosition: string | undefined;
  quality: number;
  contentType: 'curated' | 'practice' | 'training';
} {
  const rawLevel = readProperty(rootNode, 'YG');
  const rawTags = readProperty(rootNode, 'YT');
  const rawHints = readProperty(rootNode, 'YH');
  const rawKo = readProperty(rootNode, 'YK');
  const rawMoveOrder = readProperty(rootNode, 'YO');
  const rawCollections = readProperty(rootNode, 'YL');
  const rawCorner = readProperty(rootNode, 'YC');
  const rawQuality = readProperty(rootNode, 'YQ');
  const rawMeta = readProperty(rootNode, 'YM');

  const level = rawLevel ?? FALLBACK_LEVEL;
  const tags = rawTags ? parseCommaSeparated(rawTags) : [];
  const hints = rawHints ? parsePipeDelimited(rawHints) : [];
  const { slugs: collections, memberships: collectionMemberships } =
    rawCollections ? parseCollectionsWithChapters(rawCollections) : { slugs: [] as string[], memberships: [] as CollectionMembership[] };

  // Ko context validation
  const koContext = (rawKo === 'none' || rawKo === 'direct' || rawKo === 'approach')
    ? rawKo : 'none';

  // Move order validation
  const moveOrder = (rawMoveOrder === 'strict' || rawMoveOrder === 'flexible')
    ? rawMoveOrder : 'flexible';

  const firstCorrectMove = extractFirstCorrectMoveFromTree(rootNode);

  // Quality from YQ: extract q:{N} value (1-5). Default 0 (unscored).
  let quality = 0;
  if (rawQuality) {
    const qMatch = rawQuality.match(/q:(\d)/);
    if (qMatch) quality = parseInt(qMatch[1]!, 10);
  }

  // Content type from YM JSON: extract ct field. Default 'practice'.
  let contentType: 'curated' | 'practice' | 'training' = 'practice';
  if (rawMeta) {
    try {
      const meta = JSON.parse(rawMeta) as Record<string, unknown>;
      if (typeof meta.ct === 'number') {
        const slug = contentTypeIdToSlug(meta.ct);
        if (slug) contentType = slug;
      }
    } catch {
      // Invalid JSON in YM — use default
    }
  }

  return {
    level,
    tags,
    hints,
    koContext,
    moveOrder,
    collections,
    collectionMemberships,
    firstCorrectMove,
    cornerPosition: rawCorner,
    quality,
    contentType,
  };
}
