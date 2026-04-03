/**
 * lib/frame.ts — Tsumego frame: compute puzzle region + fill non-puzzle areas
 * with attacker/defender stones so KataGo focuses analysis on the puzzle.
 *
 * Ported from analyzers/tsumego_frame.py (KaTrain + ghostban algorithm).
 * Board matrix convention: 1=black, -1=white, 0=empty, mat[row][col].
 */

/**
 * Compute a boolean mask of the "problem frame" — the minimal bounding
 * region containing all stones plus a margin.
 *
 * @param mat Board matrix (Ki values: 1=black, -1=white, 0=empty)
 * @param margin Number of empty intersections to pad around stones
 * @returns 2D boolean array where true = inside frame
 */
export function computeFrame(mat: number[][], margin: number = 2): boolean[][] {
  const size = mat.length;
  if (size === 0) return [];

  // Find bounding box of all stones
  let minX = size, maxX = -1, minY = size, maxY = -1;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (mat[y][x] !== 0) {
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
  }

  if (maxX < 0) {
    // No stones — full board
    return Array.from({ length: size }, () => Array(size).fill(true));
  }

  // Expand bounding box by margin, clamped to board edges
  minX = Math.max(0, minX - margin);
  maxX = Math.min(size - 1, maxX + margin);
  minY = Math.max(0, minY - margin);
  maxY = Math.min(size - 1, maxY + margin);

  // Snap to edges if close (within 2 of edge)
  if (minX <= 2) minX = 0;
  if (maxX >= size - 3) maxX = size - 1;
  if (minY <= 2) minY = 0;
  if (maxY >= size - 3) maxY = size - 1;

  const frame: boolean[][] = Array.from({ length: size }, () => Array(size).fill(false));
  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      frame[y][x] = true;
    }
  }

  return frame;
}

/**
 * Convert frame mask to a GhostBan-compatible visible area matrix.
 * Visible area uses 1 for visible, 0 for hidden.
 */
export function frameToVisibleArea(frame: boolean[][]): number[][] {
  return frame.map(row => row.map(v => v ? 1 : 0));
}

// ---------------------------------------------------------------------------
// Tsumego frame fill — port of analyzers/tsumego_frame.py
// ---------------------------------------------------------------------------

/** Infer attacker color: stone-count + edge-proximity heuristic. */
export function guessAttacker(mat: number[][]): 1 | -1 {
  const bs = mat.length;
  let nb = 0, nw = 0;
  const blackStones: [number, number][] = [];
  const whiteStones: [number, number][] = [];

  for (let y = 0; y < bs; y++) {
    for (let x = 0; x < bs; x++) {
      if (mat[y][x] === 1) { nb++; blackStones.push([x, y]); }
      else if (mat[y][x] === -1) { nw++; whiteStones.push([x, y]); }
    }
  }

  // Heavy imbalance: majority forms the enclosure → attacker
  if (nb > 0 && nw > 0) {
    const ratio = Math.max(nb, nw) / Math.min(nb, nw);
    if (ratio >= 3.0) return nb > nw ? 1 : -1;
  }

  const avgEdgeDist = (stones: [number, number][]) => {
    if (stones.length === 0) return Infinity;
    let total = 0;
    for (const [x, y] of stones) {
      total += Math.min(x, y, bs - 1 - x, bs - 1 - y);
    }
    return total / stones.length;
  };

  const bd = avgEdgeDist(blackStones);
  const wd = avgEdgeDist(whiteStones);

  if (bd < wd) return -1;  // Black closer to edge → defends → White attacks
  if (wd < bd) return 1;   // White closer to edge → defends → Black attacks
  return 1;                 // Tie-break: Black attacks
}

interface FrameRegions {
  bbox: [number, number, number, number]; // minX, minY, maxX, maxY
  puzzleRegion: Set<string>;              // "x,y" keys
  occupied: Set<string>;
  edgeSides: Set<string>;                 // "left"|"top"|"right"|"bottom"
  defenseArea: number;
  offenseArea: number;
}

function key(x: number, y: number): string { return `${x},${y}`; }

function computeRegions(mat: number[][], margin: number, offenceToWin: number): FrameRegions {
  const bs = mat.length;
  const occupied = new Set<string>();
  const stones: [number, number][] = [];

  for (let y = 0; y < bs; y++) {
    for (let x = 0; x < bs; x++) {
      if (mat[y][x] !== 0) {
        occupied.add(key(x, y));
        stones.push([x, y]);
      }
    }
  }

  if (stones.length === 0) {
    return {
      bbox: [0, 0, 0, 0], puzzleRegion: new Set(), occupied,
      edgeSides: new Set(), defenseArea: 0, offenseArea: 0,
    };
  }

  let minX = bs, maxX = -1, minY = bs, maxY = -1;
  for (const [x, y] of stones) {
    minX = Math.min(minX, x); maxX = Math.max(maxX, x);
    minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }

  // Puzzle region = bbox + margin
  const pMinX = Math.max(0, minX - margin);
  const pMaxX = Math.min(bs - 1, maxX + margin);
  const pMinY = Math.max(0, minY - margin);
  const pMaxY = Math.min(bs - 1, maxY + margin);

  const puzzleRegion = new Set<string>();
  for (let y = pMinY; y <= pMaxY; y++) {
    for (let x = pMinX; x <= pMaxX; x++) {
      puzzleRegion.add(key(x, y));
    }
  }

  // Edge sides
  const edgeSides = new Set<string>();
  if (minX <= margin) edgeSides.add('left');
  if (minY <= margin) edgeSides.add('top');
  if (maxX >= bs - 1 - margin) edgeSides.add('right');
  if (maxY >= bs - 1 - margin) edgeSides.add('bottom');

  // Territory calculation (ghostban formula)
  const totalArea = bs * bs;
  const frameable = totalArea - puzzleRegion.size;
  const refArea = 19 * 19;
  const scaledOtw = Math.max(1, Math.round(offenceToWin * totalArea / refArea));
  const defenseArea = Math.max(0, Math.floor(frameable / 2) - scaledOtw);
  const offenseArea = Math.max(0, frameable - defenseArea);

  return {
    bbox: [minX, minY, maxX, maxY], puzzleRegion, occupied,
    edgeSides, defenseArea, offenseArea,
  };
}

/**
 * Zone-based fill matching Python tsumego_frame.py (KaTrain approach):
 * iterate row-major, first defense_area cells → defender, rest → attacker.
 * Two solid colour zones separated by a dense seam.
 * Checkerboard holes punched only far from the zone boundary for liberty safety.
 */
function fillTerritory(
  mat: number[][], regions: FrameRegions, attacker: 1 | -1,
): [number, number, number][] {  // [x, y, color]
  const bs = mat.length;
  const defender = -attacker as 1 | -1;

  const result: [number, number, number][] = [];
  let count = 0;
  const defenseArea = regions.defenseArea;

  // Row-major iteration matching Python's put_outside
  for (let y = 0; y < bs; y++) {
    for (let x = 0; x < bs; x++) {
      if (regions.occupied.has(key(x, y)) || regions.puzzleRegion.has(key(x, y))) {
        continue;
      }
      count++;

      // Zone-based colour: first defenseArea cells are defender,
      // the rest are attacker — produces two solid blocks.
      const isAttacker = count > defenseArea;

      // Checkerboard holes far from the zone boundary for liberty
      // safety (KaTrain: abs(count - defenseArea) > boardSize).
      const farFromSeam = Math.abs(count - defenseArea) > bs;
      const emptyHole = (x + y) % 2 === 0 && farFromSeam;
      if (emptyHole) continue;

      const color = isAttacker ? attacker : defender;
      result.push([x, y, color]);
    }
  }

  return result;
}

function placeBorder(
  bs: number, regions: FrameRegions, attacker: 1 | -1,
): [number, number, number][] {
  const avoid = new Set([...regions.occupied, ...regions.puzzleRegion]);
  const cells: [number, number][] = [];

  // Right border
  if (!regions.edgeSides.has('right') && regions.puzzleRegion.size > 0) {
    let pMaxX = 0;
    for (const k of regions.puzzleRegion) { const x = parseInt(k); if (x > pMaxX) pMaxX = x; }
    const col = pMaxX + 1;
    if (col < bs) {
      for (let y = 0; y < bs; y++) if (!avoid.has(key(col, y))) cells.push([col, y]);
    }
  }

  // Bottom border
  if (!regions.edgeSides.has('bottom') && regions.puzzleRegion.size > 0) {
    let pMaxY = 0;
    for (const k of regions.puzzleRegion) { const y = parseInt(k.split(',')[1]); if (y > pMaxY) pMaxY = y; }
    const row = pMaxY + 1;
    if (row < bs) {
      for (let x = 0; x < bs; x++) if (!avoid.has(key(x, row))) cells.push([x, row]);
    }
  }

  // Left border
  if (!regions.edgeSides.has('left') && regions.puzzleRegion.size > 0) {
    let pMinX = bs;
    for (const k of regions.puzzleRegion) { const x = parseInt(k); if (x < pMinX) pMinX = x; }
    const col = pMinX - 1;
    if (col >= 0) {
      for (let y = 0; y < bs; y++) if (!avoid.has(key(col, y))) cells.push([col, y]);
    }
  }

  // Top border
  if (!regions.edgeSides.has('top') && regions.puzzleRegion.size > 0) {
    let pMinY = bs;
    for (const k of regions.puzzleRegion) { const y = parseInt(k.split(',')[1]); if (y < pMinY) pMinY = y; }
    const row = pMinY - 1;
    if (row >= 0) {
      for (let x = 0; x < bs; x++) if (!avoid.has(key(x, row))) cells.push([x, row]);
    }
  }

  // Deduplicate
  const seen = new Set<string>();
  const result: [number, number, number][] = [];
  for (const [x, y] of cells) {
    const k = key(x, y);
    if (!seen.has(k)) { seen.add(k); result.push([x, y, attacker]); }
  }
  return result;
}

/**
 * Normalize board so puzzle stones are in the top-left quadrant.
 * Returns the flipped matrix and flip flags for denormalization.
 */
function normalizeToTL(mat: number[][]): { mat: number[][]; flipX: boolean; flipY: boolean } {
  const bs = mat.length;
  let cx = 0, cy = 0, count = 0;
  for (let y = 0; y < bs; y++) {
    for (let x = 0; x < bs; x++) {
      if (mat[y][x] !== 0) { cx += x; cy += y; count++; }
    }
  }
  if (count === 0) return { mat: mat.map(r => [...r]), flipX: false, flipY: false };

  cx /= count;
  cy /= count;
  const mid = (bs - 1) / 2.0;
  const flipX = cx > mid;
  const flipY = cy > mid;

  if (!flipX && !flipY) return { mat: mat.map(r => [...r]), flipX: false, flipY: false };

  const result = Array.from({ length: bs }, () => Array(bs).fill(0));
  for (let y = 0; y < bs; y++) {
    for (let x = 0; x < bs; x++) {
      const nx = flipX ? bs - 1 - x : x;
      const ny = flipY ? bs - 1 - y : y;
      result[ny][nx] = mat[y][x];
    }
  }
  return { mat: result, flipX, flipY };
}

/** Reverse the flips applied by normalizeToTL. */
function denormalize(mat: number[][], flipX: boolean, flipY: boolean): number[][] {
  if (!flipX && !flipY) return mat.map(r => [...r]);
  const bs = mat.length;
  const result = Array.from({ length: bs }, () => Array(bs).fill(0));
  for (let y = 0; y < bs; y++) {
    for (let x = 0; x < bs; x++) {
      const nx = flipX ? bs - 1 - x : x;
      const ny = flipY ? bs - 1 - y : y;
      result[ny][nx] = mat[y][x];
    }
  }
  return result;
}

// Ko-threat patterns (KaTrain): 2 fixed 4-stone groups
const KO_THREAT_OFFENSE = [[0,0],[2,0],[1,1],[0,2]] as const;
const KO_THREAT_DEFENSE = [[0,0],[1,0],[0,1],[2,1]] as const;

function placeKoThreats(
  bs: number,
  regions: FrameRegions,
  attacker: 1 | -1,
  koType: string,
  playerToMove: 1 | -1,
): [number, number, number][] {
  if (koType === 'none') return [];

  const defender = -attacker as 1 | -1;
  const avoid = new Set([...regions.occupied, ...regions.puzzleRegion]);

  const blackAttacks = attacker === 1;
  const blackPlays = playerToMove === 1;
  const koP = koType === 'direct';
  // KaTrain formula: for_offense = xor(ko, xor(black_attacks, black_plays))
  const forOffense = (koP ? 1 : 0) ^ ((blackAttacks ? 1 : 0) ^ (blackPlays ? 1 : 0));

  const pattern1 = forOffense ? KO_THREAT_OFFENSE : KO_THREAT_DEFENSE;
  const color1 = forOffense ? attacker : defender;
  const pattern2 = forOffense ? KO_THREAT_DEFENSE : KO_THREAT_OFFENSE;
  const color2 = forOffense ? defender : attacker;

  const stones: [number, number, number][] = [];

  function tryPlace(
    pattern: readonly (readonly [number, number])[],
    color: 1 | -1,
    sx: number, sy: number,
  ): boolean {
    const cells = pattern.map(([dx, dy]) => [sx + dx, sy + dy] as const);
    for (const [cx, cy] of cells) {
      if (cx < 0 || cx >= bs || cy < 0 || cy >= bs) return false;
      if (avoid.has(key(cx, cy))) return false;
    }
    for (const [cx, cy] of cells) {
      stones.push([cx, cy, color]);
      avoid.add(key(cx, cy));
    }
    return true;
  }

  const farStarts: [number, number][] = [
    [bs - 4, bs - 4], [bs - 4, 0], [0, bs - 4],
    [bs - 7, bs - 4], [bs - 4, bs - 7],
  ];

  let placed1 = false, placed2 = false;
  for (const [sx, sy] of farStarts) {
    if (!placed1 && tryPlace(pattern1, color1, sx, sy)) placed1 = true;
    else if (!placed2 && tryPlace(pattern2, color2, sx, sy)) placed2 = true;
    if (placed1 && placed2) break;
  }

  return stones;
}

/**
 * Apply tsumego frame to a board matrix: fill non-puzzle areas with
 * attacker/defender stones so the engine focuses on the puzzle region.
 *
 * @param mat Board matrix (1=black, -1=white, 0=empty), mat[row][col]
 * @param margin Margin around puzzle stones (default 2)
 * @param offenceToWin Territory advantage for attacker (default 10)
 * @param koType Ko context: "none", "direct", or "approach" (default "none")
 * @param playerToMove 1=black, -1=white (default 1, used for ko threats)
 * @returns New board matrix with frame stones added
 */
export function applyTsumegoFrame(
  mat: number[][],
  margin = 2,
  offenceToWin = 10,
  koType = 'none',
  playerToMove: 1 | -1 = 1,
): number[][] {
  const bs = mat.length;
  if (bs < 5 || mat.every(row => row.every(c => c === 0))) {
    return mat.map(row => [...row]);
  }

  // Normalize to TL corner for consistent framing
  const norm = normalizeToTL(mat);
  const normMat = norm.mat;

  const attacker = guessAttacker(normMat);
  const regions = computeRegions(normMat, margin, offenceToWin);

  // Border FIRST: solid attacker wall before fill, so fill flows around it
  // (prevents alternating attacker/defender atari in the border zone)
  const borderStones = placeBorder(bs, regions, attacker);

  // Fill territory, treating border cells as occupied so fill skips them
  const borderOccupied = new Set(regions.occupied);
  for (const [x, y] of borderStones) borderOccupied.add(key(x, y));
  const fillRegions: FrameRegions = { ...regions, occupied: borderOccupied };
  const fillStones = fillTerritory(normMat, fillRegions, attacker);

  // Update occupied for ko placement
  const allOccupied = new Set(borderOccupied);
  for (const [x, y] of fillStones) allOccupied.add(key(x, y));

  const koRegions: FrameRegions = {
    ...regions,
    occupied: allOccupied,
  };
  const koStones = placeKoThreats(bs, koRegions, attacker, koType, playerToMove);

  // Build result matrix in normalized space
  const normResult = normMat.map(row => [...row]);
  for (const [x, y, color] of [...fillStones, ...borderStones, ...koStones]) {
    normResult[y][x] = color;
  }

  // Denormalize back to original orientation
  return denormalize(normResult, norm.flipX, norm.flipY);
}
