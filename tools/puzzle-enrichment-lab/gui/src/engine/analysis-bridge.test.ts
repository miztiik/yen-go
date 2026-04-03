import { describe, it, expect } from 'vitest';
import { normalizeWorkerAnalysis, gtpToSgf } from './analysis-bridge';

describe('gtpToSgf', () => {
  it('converts standard GTP coord to SGF', () => {
    // D4 on 19x19: col D=3→d, row 4→19-4=15→p
    expect(gtpToSgf('D4', 19)).toBe('dp');
  });

  it('skips I in GTP column (J→i in SGF)', () => {
    // J5 on 19x19: col J (skip I, so index 8)→i, row 5→19-5=14→o
    expect(gtpToSgf('J5', 19)).toBe('io');
  });

  it('converts corner coords A1 → as on 19x19', () => {
    // A1: col A=0→a, row 1→19-1=18→s
    expect(gtpToSgf('A1', 19)).toBe('as');
  });

  it('handles pass', () => {
    expect(gtpToSgf('pass', 19)).toBe('tt');
  });

  it('converts on 9x9 board', () => {
    // E5 on 9x9: col E=4→e, row 5→9-5=4→e
    expect(gtpToSgf('E5', 9)).toBe('ee');
  });

  it('converts E17 on 19x19', () => {
    expect(gtpToSgf('E17', 19)).toBe('ec');
  });
});

describe('normalizeWorkerAnalysis', () => {
  it('converts worker AnalysisPayload to GUI AnalysisResult', () => {
    const payload = {
      rootWinRate: 0.65,
      rootScoreLead: 5.2,
      rootVisits: 100,
      ownership: new Array(361).fill(0),
      policy: new Array(362).fill(0),
      moves: [
        {
          x: 3,
          y: 3,
          winRate: 0.7,
          scoreLead: 5.5,
          visits: 50,
          order: 0,
          prior: 0.45,
          pv: ['dd', 'ee', 'ff'],
        },
      ],
    };

    const result = normalizeWorkerAnalysis(payload, 19);
    expect(result.rootInfo.scoreLead).toBe(5.2);
    expect(result.rootInfo.visits).toBe(100);
    expect(result.rootInfo.winrate).toBe(0.65);
    expect(result.moveInfos).toHaveLength(1);
    expect(result.moveInfos[0].move).toBe('dd'); // x=3 → 'd', y=3 → 'd'
    expect(result.moveInfos[0].x).toBe(3);
    expect(result.moveInfos[0].y).toBe(3);
    expect(result.moveInfos[0].winrate).toBe(0.7);
    expect(result.moveInfos[0].prior).toBe(0.45);
    expect(result.moveInfos[0].pv).toEqual(['dd', 'ee', 'ff']);
  });

  it('handles empty moves array', () => {
    const payload = {
      rootWinRate: 0.5,
      rootScoreLead: 0,
      rootVisits: 0,
      ownership: [],
      policy: [],
      moves: [],
    };
    const result = normalizeWorkerAnalysis(payload, 19);
    expect(result.moveInfos).toHaveLength(0);
  });
});
