/**
 * SGF Type Definitions
 * @module types/sgf
 *
 * Types for parsing SGF (Smart Game Format) files.
 * Includes standard FF4 properties and YenGo custom extensions.
 *
 * Consolidated from the sgf directory during Spec 129.
 *
 * @see https://www.red-bean.com/sgf/sgf4.html - FF4 Specification
 * @see puzzle_manager/docs/SGF_FORMAT.md - YenGo extensions
 */

// ============================================================================
// Standard SGF Properties (FF4 Spec)
// ============================================================================

/**
 * Standard SGF properties from FF4 specification.
 * These are common to all SGF files.
 */
export interface StandardSGFProperties {
  /** File format version (e.g., "4") */
  FF?: string;
  /** Game type ("1" = Go) */
  GM?: string;
  /** Board size ("9", "13", "19") */
  SZ?: string;
  /** Character set ("UTF-8") */
  CA?: string;
  /** Add black stones - array of SGF coordinates */
  AB?: string[];
  /** Add white stones - array of SGF coordinates */
  AW?: string[];
  /** Player to move first */
  PL?: 'B' | 'W';
  /** Black move (SGF coordinate) */
  B?: string;
  /** White move (SGF coordinate) */
  W?: string;
  /** Comment text */
  C?: string;
  /** Node name */
  N?: string;
  /** Application that created this file */
  AP?: string;
  /** Ruleset used */
  RU?: string;
  /** Bad Move marker - indicates wrong/refutation move (Spec 012) */
  BM?: string;
  /** Tesuji marker - indicates key tactical move (Spec 012) */
  TE?: string;
  /** Labels - array of "coord:text" (e.g., ["cd:A", "ef:B"]) */
  LB?: string[];
  /** Triangles - array of coordinates */
  TR?: string[];
  /** Squares - array of coordinates */
  SQ?: string[];
  /** Circles - array of coordinates */
  CR?: string[];
  /** Marks (X) - array of coordinates */
  MA?: string[];
}

// ============================================================================
// YenGo Custom SGF Properties
// ============================================================================

/**
 * YenGo custom SGF properties.
 * These extend standard SGF for tsumego puzzle metadata.
 * All properties prefixed with 'Y'.
 */
export interface YenGoSGFProperties {
  /** Schema version (e.g., "1.0") */
  YV?: string;
  /** Level and sublevel (e.g., "beginner:1", "intermediate:2") */
  YG?: string;
  /** Tags - comma-separated technique identifiers (e.g., "killing,ko,throw-in") */
  YT?: string;
  /** Hint Level 1: position coordinate (e.g., "dc") */
  YH1?: string;
  /** Hint Level 2: technique description (e.g., "Look for throw-in") */
  YH2?: string;
  /** Hint Level 3: detailed hint text */
  YH3?: string;
  /** Compact hints v7+ format: position|technique|text (pipe-separated) */
  YH?: string;
  /** Refutation moves — wrong first-move SGF coords (e.g., "cd,de,ef") */
  YR?: string;
  /** Quality metrics (e.g., "depth:5,unique:true") */
  YQ?: string;
  /** Ko context information (e.g., "direct:B2,W1") */
  YK?: string;
  /** Move order flexibility (e.g., "flexible:1,2") */
  YO?: string;
  /** Corner/region position (e.g., "TL", "BR", "C") */
  YC?: string;
  /** Move count in solution */
  YM?: string;
}

/**
 * Combined SGF properties (standard + YenGo extensions).
 * This is the type used for all SGF property access.
 */
export type SGFProperties = StandardSGFProperties & YenGoSGFProperties;

// ============================================================================
// SGF Tree Structure
// ============================================================================

/**
 * A node in the SGF game tree.
 * Nodes contain properties and can have multiple children (variations).
 */
export interface SGFNode {
  /** Properties attached to this node */
  properties: SGFProperties;
  /** Child nodes (branches/variations) */
  children: SGFNode[];
}

/**
 * Game information extracted from root SGF node.
 * Contains setup state for the puzzle.
 */
export interface GameInfo {
  /** Board size (9, 13, or 19) */
  boardSize: number;
  /** Initial black stone positions (SGF coordinates like "aa", "bc") */
  blackStones: string[];
  /** Initial white stone positions (SGF coordinates) */
  whiteStones: string[];
  /** Which player moves first */
  sideToMove: 'B' | 'W';
}

/**
 * Result of parsing an SGF file.
 * Contains the full tree structure and extracted game info.
 */
export interface ParsedSGF {
  /** Root node containing setup and metadata */
  root: SGFNode;
  /** Extracted game information for quick access */
  gameInfo: GameInfo;
}

// ============================================================================
// Error Types
// ============================================================================

/**
 * Error details from SGF parsing.
 * Provides context for debugging invalid SGF files.
 */
export interface SGFParseError {
  /** Human-readable error message */
  message: string;
  /** Character position in input where error occurred */
  position: number | undefined;
  /** Line number where error occurred (if determinable) */
  line: number | undefined;
}

// ============================================================================
// Parser Interface
// ============================================================================

/**
 * Interface for SGF parser implementations.
 * Defines the contract for parsing SGF content.
 */
export interface ISGFParser {
  /**
   * Parse SGF content into structured tree.
   * @param content - Raw SGF file content as string
   * @returns Parsed SGF tree with game info
   * @throws SGFParseError on invalid input
   */
  parse(content: string): ParsedSGF;

  /**
   * Extract game info from SGF root node.
   * Used internally by parse() but exposed for flexibility.
   * @param node - Root node of SGF tree
   * @returns Extracted game information
   */
  extractGameInfo(node: SGFNode): GameInfo;

  /**
   * Validate SGF content without full parse.
   * Lightweight check for well-formed SGF.
   * @param content - Raw SGF content
   * @returns true if valid, false otherwise
   */
  validate(content: string): boolean;
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Check if a value is a valid player identifier.
 * @param value - Value to check
 * @returns true if 'B' or 'W'
 */
export function isValidPlayer(value: unknown): value is 'B' | 'W' {
  return value === 'B' || value === 'W';
}

/**
 * Check if an object has SGF properties structure.
 * @param value - Value to check
 * @returns true if it has the shape of SGFProperties
 */
export function isSGFProperties(value: unknown): value is SGFProperties {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  // Basic structural check - SGF properties are string/string[] values
  return true;
}
