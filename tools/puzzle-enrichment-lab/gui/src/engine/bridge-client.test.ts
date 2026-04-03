import { describe, it, expect, vi, afterEach } from 'vitest';
import { getEngineStatus, analyzePython } from './bridge-client';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

afterEach(() => {
  mockFetch.mockReset();
});

describe('getEngineStatus', () => {
  it('returns parsed health response', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ backend: 'katago', modelName: 'b6c96' }),
    });

    const result = await getEngineStatus();
    expect(result.backend).toBe('katago');
    expect(result.modelName).toBe('b6c96');
    expect(mockFetch).toHaveBeenCalledWith('/api/health');
  });
});

describe('analyzePython', () => {
  it('serializes board and returns normalized result', async () => {
    const moveData = {
      rootScoreLead: 3.0,
      rootVisits: 200,
      rootWinRate: 0.6,
      rootScoreSelfplay: 3.0,
      rootScoreStdev: 1.0,
      moves: [
        { x: 2, y: 2, prior: 0.3, winRate: 0.62, winRateLost: 0.01, scoreLead: 3.1, scoreSelfplay: 3.0, scoreStdev: 1.0, visits: 100, pointsLost: 0.1, relativePointsLost: 0.05, order: 0, pv: ['cc'] },
      ],
      ownership: [],
      ownershipStdev: [],
      policy: [],
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(moveData),
      text: () => Promise.resolve(''),
    });

    const board = [[null, null], [null, 'black']] as any;
    const result = await analyzePython({
      board,
      currentPlayer: 'black',
      moveHistory: [],
      komi: 6.5,
      visits: 500,
    });
    expect(result.rootInfo.scoreLead).toBe(3.0);
    expect(result.moveInfos).toHaveLength(1);
    expect(result.moveInfos[0].move).toBe('cc');
  });
});
