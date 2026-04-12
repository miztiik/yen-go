/**
 * SGF Parser
 * @module lib/sgf/parser
 *
 * Parses SGF (Smart Game Format) files into structured data.
 * Supports standard FF4 properties and YenGo custom extensions.
 *
 * Constitution Compliance:
 * - V. No Browser AI: Parser only extracts data, no move generation
 * - VII. Deterministic: Same input always produces same output
 */

import type {
  SGFProperties,
  SGFNode,
  GameInfo,
  ParsedSGF,
  SGFParseError,
  ISGFParser,
} from './types';
import { isValidPlayer } from './types';

// ============================================================================
// Parser Error
// ============================================================================

/**
 * Custom error class for SGF parsing errors.
 */
export class SGFParseErrorImpl extends Error implements SGFParseError {
  position: number | undefined;
  line: number | undefined;

  constructor(message: string, position?: number, line?: number) {
    super(message);
    this.name = 'SGFParseError';
    this.position = position;
    this.line = line;
  }
}

// ============================================================================
// Parser State
// ============================================================================

interface ParserState {
  input: string;
  pos: number;
  length: number;
}

// ============================================================================
// Parsing Utilities
// ============================================================================

/**
 * Calculate line number from position.
 */
function getLineNumber(input: string, position: number): number {
  let line = 1;
  for (let i = 0; i < position && i < input.length; i++) {
    if (input[i] === '\n') {
      line++;
    }
  }
  return line;
}

/**
 * Skip whitespace characters.
 */
function skipWhitespace(state: ParserState): void {
  while (state.pos < state.length) {
    const char = state.input[state.pos];
    if (char === ' ' || char === '\t' || char === '\n' || char === '\r') {
      state.pos++;
    } else {
      break;
    }
  }
}

/**
 * Peek at current character without advancing.
 */
function peek(state: ParserState): string | null {
  if (state.pos >= state.length) {
    return null;
  }
  return state.input[state.pos] ?? null;
}

/**
 * Consume and return current character.
 */
function consume(state: ParserState): string | null {
  if (state.pos >= state.length) {
    return null;
  }
  return state.input[state.pos++] ?? null;
}

/**
 * Expect a specific character, throw if not found.
 */
function expect(state: ParserState, expected: string): void {
  skipWhitespace(state);
  const char = consume(state);
  if (char !== expected) {
    throw new SGFParseErrorImpl(
      `Expected '${expected}' but found '${char ?? 'EOF'}'`,
      state.pos - 1,
      getLineNumber(state.input, state.pos - 1)
    );
  }
}

// ============================================================================
// Property Parsing
// ============================================================================

/**
 * Parse a property identifier (e.g., "AB", "SZ", "YG").
 */
function parsePropertyId(state: ParserState): string {
  skipWhitespace(state);
  let id = '';

  while (state.pos < state.length) {
    const char = state.input[state.pos];
    if (char === undefined) {
      break;
    }
    if (char >= 'A' && char <= 'Z') {
      id += char;
      state.pos++;
    } else if (char >= 'a' && char <= 'z') {
      // Lowercase also allowed (some SGF files have this)
      id += char.toUpperCase();
      state.pos++;
    } else if (id.length > 0 && char >= '0' && char <= '9') {
      // Digits allowed after first character (for YenGo properties like YH1, YH2, YH3)
      id += char;
      state.pos++;
    } else {
      break;
    }
  }

  return id;
}

/**
 * Parse a property value (content between [ and ]).
 */
function parsePropertyValue(state: ParserState): string {
  skipWhitespace(state);
  expect(state, '[');

  let value = '';
  let escaped = false;

  while (state.pos < state.length) {
    const char = state.input[state.pos];

    if (escaped) {
      // Handle escaped characters
      if (char === '\n' || char === '\r') {
        // Escaped newline - skip it
        state.pos++;
        if (char === '\r' && peek(state) === '\n') {
          state.pos++;
        }
      } else {
        value += char;
        state.pos++;
      }
      escaped = false;
    } else if (char === '\\') {
      escaped = true;
      state.pos++;
    } else if (char === ']') {
      state.pos++;
      return value;
    } else {
      value += char;
      state.pos++;
    }
  }

  throw new SGFParseErrorImpl(
    'Unclosed property value bracket',
    state.pos,
    getLineNumber(state.input, state.pos)
  );
}

/**
 * Parse all values for a property (handles AB[aa][ba][ca] format).
 */
function parsePropertyValues(state: ParserState): string[] {
  const values: string[] = [];

  skipWhitespace(state);
  while (peek(state) === '[') {
    values.push(parsePropertyValue(state));
    skipWhitespace(state);
  }

  return values;
}

// ============================================================================
// Node Parsing
// ============================================================================

/**
 * Parse a single SGF node (;properties...).
 */
function parseNode(state: ParserState): SGFNode {
  expect(state, ';');

  const properties: SGFProperties = {};
  const children: SGFNode[] = [];

  skipWhitespace(state);

  // Parse properties until we hit (, ), or ;
  while (state.pos < state.length) {
    const char = peek(state);

    if (char === '(' || char === ')' || char === ';') {
      break;
    }

    if (char === null) {
      break;
    }

    // Parse property
    const propId = parsePropertyId(state);
    if (!propId) {
      break;
    }

    const values = parsePropertyValues(state);

    // Store property (array for multi-value, string for single)
    if (
      propId === 'AB' ||
      propId === 'AW' ||
      propId === 'LB' ||
      propId === 'TR' ||
      propId === 'SQ' ||
      propId === 'CR' ||
      propId === 'MA'
    ) {
      // Stone setup and markup properties are always arrays
      properties[propId] = values;
    } else if (values.length === 1) {
      // Single value
      (properties as Record<string, unknown>)[propId] = values[0];
    } else if (values.length > 1) {
      // Multiple values
      (properties as Record<string, unknown>)[propId] = values;
    }

    skipWhitespace(state);
  }

  return { properties, children };
}

/**
 * Parse a game tree (sequence of nodes, possibly with variations).
 */
function parseGameTree(state: ParserState): SGFNode | null {
  skipWhitespace(state);

  if (peek(state) !== '(') {
    return null;
  }

  expect(state, '(');
  skipWhitespace(state);

  // Must start with a node
  if (peek(state) !== ';') {
    throw new SGFParseErrorImpl(
      'Game tree must start with a node (;)',
      state.pos,
      getLineNumber(state.input, state.pos)
    );
  }

  // Parse first node (root)
  const root = parseNode(state);
  let currentNode = root;

  // Parse remaining content
  skipWhitespace(state);

  while (state.pos < state.length && peek(state) !== ')') {
    const char = peek(state);

    if (char === ';') {
      // Sequential node - becomes child of current
      const node = parseNode(state);
      currentNode.children.push(node);
      currentNode = node;
    } else if (char === '(') {
      // Variation - parse subtree and add as child
      const variation = parseGameTree(state);
      if (variation) {
        currentNode.children.push(variation);
      }
    } else {
      break;
    }

    skipWhitespace(state);
  }

  expect(state, ')');
  return root;
}

// ============================================================================
// Game Info Extraction
// ============================================================================

/**
 * Extract game info from root node.
 */
function extractGameInfo(root: SGFNode): GameInfo {
  const props = root.properties;

  // Board size (default to 19 if not specified)
  const boardSize = props.SZ ? parseInt(props.SZ, 10) : 19;
  if (isNaN(boardSize) || boardSize < 1 || boardSize > 19) {
    throw new SGFParseErrorImpl(`Invalid board size: ${props.SZ}`);
  }

  // Initial stones
  const blackStones = props.AB ?? [];
  const whiteStones = props.AW ?? [];

  // Side to move (default to Black)
  let sideToMove: 'B' | 'W' = 'B';
  if (props.PL) {
    if (isValidPlayer(props.PL)) {
      sideToMove = props.PL;
    } else {
      throw new SGFParseErrorImpl(`Invalid player: ${String(props.PL)}`);
    }
  }

  return {
    boardSize,
    blackStones,
    whiteStones,
    sideToMove,
  };
}

// ============================================================================
// Main Parser Functions
// ============================================================================

/**
 * Validate SGF content without full parse.
 * Performs lightweight structural check.
 *
 * @param content - Raw SGF string
 * @returns true if structurally valid
 */
export function validateSGF(content: string): boolean {
  if (!content || typeof content !== 'string') {
    return false;
  }

  const trimmed = content.trim();

  // Must start with ( and end with )
  if (!trimmed.startsWith('(') || !trimmed.endsWith(')')) {
    return false;
  }

  // Must contain at least one node marker
  if (!trimmed.includes(';')) {
    return false;
  }

  // Check balanced parentheses and brackets
  let parenDepth = 0;
  let inBracket = false;
  let escaped = false;

  for (const char of trimmed) {
    if (escaped) {
      escaped = false;
      continue;
    }

    if (char === '\\') {
      escaped = true;
      continue;
    }

    if (inBracket) {
      if (char === ']') {
        inBracket = false;
      } else if (char === '(' || char === ')') {
        // Parentheses inside brackets are invalid (usually indicates unclosed bracket)
        // A valid SGF shouldn't have unescaped ) inside []
        // However, we'll be lenient here and just check balanced
      }
    } else {
      if (char === '[') {
        inBracket = true;
      } else if (char === '(') {
        parenDepth++;
      } else if (char === ')') {
        parenDepth--;
        if (parenDepth < 0) {
          return false;
        }
      }
    }
  }

  // Must not end while inside a bracket
  if (inBracket) {
    return false;
  }

  return parenDepth === 0;
}

/**
 * Parse SGF content into structured tree.
 *
 * @param content - Raw SGF string
 * @returns Parsed SGF with root node and game info
 * @throws SGFParseError on invalid input
 */
export function parseSGF(content: string): ParsedSGF {
  if (!content || typeof content !== 'string') {
    throw new SGFParseErrorImpl('Empty or invalid input');
  }

  const trimmed = content.trim();

  if (!trimmed.startsWith('(')) {
    throw new SGFParseErrorImpl('SGF must start with (', 0, 1);
  }

  const state: ParserState = {
    input: trimmed,
    pos: 0,
    length: trimmed.length,
  };

  const root = parseGameTree(state);

  if (!root) {
    throw new SGFParseErrorImpl('Failed to parse game tree');
  }

  const gameInfo = extractGameInfo(root);

  return {
    root,
    gameInfo,
  };
}

// ============================================================================
// Parser Class Implementation
// ============================================================================

/**
 * SGF Parser class implementing ISGFParser interface.
 */
export class SGFParser implements ISGFParser {
  parse(content: string): ParsedSGF {
    return parseSGF(content);
  }

  extractGameInfo(node: SGFNode): GameInfo {
    return extractGameInfo(node);
  }

  validate(content: string): boolean {
    return validateSGF(content);
  }
}

// Default parser instance
export const defaultParser = new SGFParser();

// ============================================================================
// Label Parsing Utilities
// ============================================================================

/**
 * Parsed board label from SGF LB[] property.
 */
export interface ParsedBoardLabel {
  /** SGF coordinate (e.g., "cd") */
  coord: string;
  /** Label text (e.g., "A", "1") */
  text: string;
}

/**
 * Parse LB[] property values into structured labels.
 * LB property format is "coord:text" (e.g., "cd:A", "ef:B").
 *
 * @param lbValues - Array of LB property values from SGF
 * @returns Array of parsed labels
 *
 * @example
 * ```ts
 * const labels = parseLBProperty(['cd:A', 'ef:B']);
 * // labels = [{ coord: 'cd', text: 'A' }, { coord: 'ef', text: 'B' }]
 * ```
 */
export function parseLBProperty(lbValues: string[] | undefined): ParsedBoardLabel[] {
  if (!lbValues || !Array.isArray(lbValues)) {
    return [];
  }

  const labels: ParsedBoardLabel[] = [];

  for (const value of lbValues) {
    const colonIndex = value.indexOf(':');
    if (colonIndex >= 2) {
      // Format: "coord:text"
      const coord = value.substring(0, colonIndex);
      const text = value.substring(colonIndex + 1);
      if (coord && text) {
        labels.push({ coord, text });
      }
    }
  }

  return labels;
}

/**
 * Convert SGF coordinate to numeric x,y.
 * SGF uses 'a'-'s' for 1-19 (skipping 'i' is NOT standard in SGF, only in display).
 *
 * @param sgfCoord - Two-letter SGF coordinate (e.g., "cd")
 * @returns Object with x, y (0-indexed) or null if invalid
 */
export function sgfCoordToXY(sgfCoord: string): { x: number; y: number } | null {
  if (!sgfCoord || sgfCoord.length < 2) {
    return null;
  }

  const x = sgfCoord.charCodeAt(0) - 'a'.charCodeAt(0);
  const y = sgfCoord.charCodeAt(1) - 'a'.charCodeAt(0);

  if (x < 0 || x > 18 || y < 0 || y > 18) {
    return null;
  }

  return { x, y };
}
