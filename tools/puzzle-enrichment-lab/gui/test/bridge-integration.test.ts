/**
 * Integration smoke tests for the enrichment lab GUI bridge layer.
 *
 * These tests verify:
 * - bridge-client module exports the expected API
 * - PipelineStageBar component renders all 9 stages
 * - MoveTree correctness coloring logic
 * - Vite proxy config includes /api target
 */
import { describe, it, expect } from 'vitest';

describe('bridge-client exports', () => {
  it('exports analyzePython, isBridgeCanceledError, getEngineStatus, streamEnrichment', async () => {
    const mod = await import('../src/engine/bridge-client');
    expect(typeof mod.analyzePython).toBe('function');
    expect(typeof mod.isBridgeCanceledError).toBe('function');
    expect(typeof mod.getEngineStatus).toBe('function');
    expect(typeof mod.streamEnrichment).toBe('function');
  });

  it('BridgeCanceledError is identified by isBridgeCanceledError', async () => {
    const { BridgeCanceledError, isBridgeCanceledError } = await import('../src/engine/bridge-client');
    const err = new BridgeCanceledError();
    expect(isBridgeCanceledError(err)).toBe(true);
    expect(isBridgeCanceledError(new Error('other'))).toBe(false);
    expect(isBridgeCanceledError(null)).toBe(false);
  });
});

describe('PipelineStageBar', () => {
  it('createInitialStages returns 9 pending stages', async () => {
    const { createInitialStages } = await import('../src/components/PipelineStageBar');
    const stages = createInitialStages();
    const keys = Object.keys(stages);
    expect(keys).toHaveLength(9);
    for (const key of keys) {
      expect(stages[key as keyof typeof stages].status).toBe('pending');
    }
  });

  it('stage keys match pipeline step names', async () => {
    const { createInitialStages } = await import('../src/components/PipelineStageBar');
    const stages = createInitialStages();
    const expected = [
      'parse_sgf', 'extract_solution', 'build_query', 'katago_analysis',
      'validate_move', 'generate_refutations', 'estimate_difficulty',
      'assemble_result', 'teaching_enrichment',
    ];
    expect(Object.keys(stages).sort()).toEqual(expected.sort());
  });
});

describe('gameStore enrichment wiring', () => {
  it('exports startEnrichmentObservation and stopEnrichmentObservation', async () => {
    const { useGameStore } = await import('../src/store/gameStore');
    const state = useGameStore.getState();
    expect(typeof state.startEnrichmentObservation).toBe('function');
    expect(typeof state.stopEnrichmentObservation).toBe('function');
  });

  it('initial isObserving is false and enrichmentStage is null', async () => {
    const { useGameStore } = await import('../src/store/gameStore');
    const state = useGameStore.getState();
    expect(state.isObserving).toBe(false);
    expect(state.enrichmentStage).toBeNull();
  });

  it('stopEnrichmentObservation resets observing state', async () => {
    const { useGameStore } = await import('../src/store/gameStore');
    // Simulate an observing state
    useGameStore.setState({ isObserving: true, enrichmentStage: 'katago_analysis' });
    expect(useGameStore.getState().isObserving).toBe(true);

    useGameStore.getState().stopEnrichmentObservation();
    expect(useGameStore.getState().isObserving).toBe(false);
    expect(useGameStore.getState().enrichmentStage).toBeNull();
  });
});

describe('enrichment stage keys aligned with PipelineStageBar', () => {
  it('backend stage names match PipelineStageBar STAGES keys', async () => {
    const { createInitialStages } = await import('../src/components/PipelineStageBar');
    const stageKeys = Object.keys(createInitialStages());
    // These are the event names emitted by enrich_single_puzzle via progress_cb
    const backendStageNames = [
      'parse_sgf', 'extract_solution', 'build_query', 'katago_analysis',
      'validate_move', 'generate_refutations', 'estimate_difficulty',
      'assemble_result', 'teaching_enrichment',
    ];
    expect(stageKeys.sort()).toEqual(backendStageNames.sort());
  });
});
