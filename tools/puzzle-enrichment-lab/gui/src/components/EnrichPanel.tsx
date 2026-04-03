/**
 * EnrichPanel.tsx — Permanent collapsible panel for enrichment pipeline.
 * Shows stage progress, results, and save button.
 */

import { useState } from 'preact/hooks';
import { enrichStages, enrichResult, isEnriching, sgfText } from '../store/state';
import { streamEnrichment } from '../engine/bridge-client';
import type { EnrichStage, EnrichResult } from '../types';

function stageIcon(status: EnrichStage['status']): string {
  switch (status) {
    case 'done': return '\u2713';    // checkmark
    case 'running': return '\u25CB'; // circle
    case 'error': return '\u2717';   // cross
    default: return '\u2022';        // bullet
  }
}

function stageClass(status: EnrichStage['status']): string {
  switch (status) {
    case 'done': return 'stage-done';
    case 'running': return 'stage-running';
    case 'error': return 'stage-error';
    default: return 'stage-pending';
  }
}

export function EnrichPanel() {
  const [collapsed, setCollapsed] = useState(false);
  let enrichAbort: AbortController | null = null;

  const handleEnrich = async () => {
    const sgf = sgfText.value;
    if (!sgf) return;

    isEnriching.value = true;
    enrichStages.value = [];
    enrichResult.value = null;
    enrichAbort = new AbortController();

    try {
      const partial: Partial<EnrichResult> = { sgf };
      for await (const event of streamEnrichment(sgf, enrichAbort.signal)) {
        const stage: EnrichStage = {
          name: event.stage,
          status: (event.payload as any).status === 'error' ? 'error' : 
                  (event.payload as any).status === 'done' ? 'done' : 'running',
          message: (event.payload as any).message,
        };
        enrichStages.value = [...enrichStages.value.filter(s => s.name !== stage.name), stage];
        // Accumulate final results from stage payloads
        if ((event.payload as any).level) partial.level = (event.payload as any).level;
        if ((event.payload as any).tags) partial.tags = (event.payload as any).tags;
        if ((event.payload as any).quality) partial.quality = (event.payload as any).quality;
        if ((event.payload as any).complexity) partial.complexity = (event.payload as any).complexity;
        if ((event.payload as any).hints) partial.hints = (event.payload as any).hints;
        if ((event.payload as any).sgf) partial.sgf = (event.payload as any).sgf;
      }
      enrichResult.value = partial as EnrichResult;
      if (partial.sgf) sgfText.value = partial.sgf;
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        enrichStages.value = [
          ...enrichStages.value,
          { name: 'error', status: 'error', message: err.message },
        ];
      }
    } finally {
      isEnriching.value = false;
      enrichAbort = null;
    }
  };

  const handleCancel = () => {
    enrichAbort?.abort();
    isEnriching.value = false;
  };

  const handleSave = () => {
    const result = enrichResult.value;
    if (!result?.sgf) return;
    // Download enriched SGF as file
    const blob = new Blob([result.sgf], { type: 'application/x-go-sgf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'enriched-puzzle.sgf';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div class="enrich-panel">
      <div class="enrich-header" onClick={() => setCollapsed(!collapsed)}>
        <h3>Enrichment Pipeline {collapsed ? '\u25B6' : '\u25BC'}</h3>
      </div>

      {!collapsed && (
        <div class="enrich-body">
          <div class="enrich-actions">
            <button
              onClick={handleEnrich}
              disabled={isEnriching.value || !sgfText.value}
              class="btn btn-primary"
            >
              {isEnriching.value ? 'Enriching...' : 'Enrich Puzzle'}
            </button>
            {isEnriching.value && (
              <button onClick={handleCancel} class="btn btn-danger">Cancel</button>
            )}
          </div>

          {/* Stage progress */}
          {enrichStages.value.length > 0 && (
            <div class="enrich-stages">
              {enrichStages.value.map(stage => (
                <div key={stage.name} class={`enrich-stage ${stageClass(stage.status)}`}>
                  <span class="stage-icon">{stageIcon(stage.status)}</span>
                  <span class="stage-name">{stage.name}</span>
                  {stage.message && <span class="stage-msg">{stage.message}</span>}
                </div>
              ))}
            </div>
          )}

          {/* Enrichment results */}
          {enrichResult.value && (
            <div class="enrich-results">
              <h4>Results</h4>
              {enrichResult.value.level && (
                <div><strong>Level (YG):</strong> {enrichResult.value.level}</div>
              )}
              {enrichResult.value.tags && enrichResult.value.tags.length > 0 && (
                <div><strong>Tags (YT):</strong> {enrichResult.value.tags.join(', ')}</div>
              )}
              {enrichResult.value.quality && (
                <div><strong>Quality (YQ):</strong> {enrichResult.value.quality}</div>
              )}
              {enrichResult.value.complexity && (
                <div><strong>Complexity (YX):</strong> {enrichResult.value.complexity}</div>
              )}
              {enrichResult.value.hints && enrichResult.value.hints.length > 0 && (
                <div><strong>Hints (YH):</strong> {enrichResult.value.hints.join(' | ')}</div>
              )}
              <button onClick={handleSave} class="btn btn-primary" style={{ marginTop: '8px' }}>
                Save Enriched SGF
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
