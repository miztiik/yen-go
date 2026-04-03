/**
 * EngineSettings.tsx — Model selector dropdown + visits input + engine mode toggle.
 */

import { engineMode, modelName, visitCount, modelStatus } from '../store/state';

const MODELS = [
  { id: 'b6c96', name: 'b6c96 (~3.7MB)', url: '/models/kata1-b6c96-s175395328-d26788732.bin.gz' },
  { id: 'b10c128', name: 'b10c128 (~11.5MB)', url: '/models/kata1-b10c128-s114046784-d204142634.bin.gz' },
];

export function EngineSettings() {
  return (
    <div class="engine-settings">
      <h3>Engine Settings</h3>

      <div class="setting-row">
        <label>Engine Mode:</label>
        <select
          value={engineMode.value}
          onChange={(e) => { engineMode.value = (e.target as HTMLSelectElement).value as 'browser' | 'bridge'; }}
        >
          <option value="browser">Browser (TF.js)</option>
          <option value="bridge">Bridge (Python KataGo)</option>
        </select>
      </div>

      {engineMode.value === 'browser' && (
        <div class="setting-row">
          <label>Model:</label>
          <select
            value={modelName.value}
            onChange={(e) => { modelName.value = (e.target as HTMLSelectElement).value; }}
          >
            {MODELS.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
      )}

      {engineMode.value === 'browser' && (
        <div class="setting-row model-status-row">
          <label>Status:</label>
          <span
            class="model-status-dot"
            style={{
              display: 'inline-block',
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              flexShrink: 0,
              background:
                modelStatus.value === 'ready' ? '#22c55e' :
                modelStatus.value === 'loading' ? '#eab308' :
                modelStatus.value === 'error' ? '#ef4444' : '#666',
              boxShadow:
                modelStatus.value === 'ready' ? '0 0 6px #22c55e' :
                modelStatus.value === 'loading' ? '0 0 6px #eab308' :
                modelStatus.value === 'error' ? '0 0 6px #ef4444' : 'none',
            }}
          />
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            {modelStatus.value === 'ready' ? 'Model loaded' :
             modelStatus.value === 'loading' ? 'Loading model...' :
             modelStatus.value === 'error' ? 'Load failed' : 'Not loaded'}
          </span>
        </div>
      )}

      <div class="setting-row">
        <label>Max Visits:</label>
        <input
          type="number"
          min={1}
          max={10000}
          value={visitCount.value}
          onChange={(e) => {
            const v = parseInt((e.target as HTMLInputElement).value, 10);
            if (v > 0) visitCount.value = v;
          }}
        />
      </div>
    </div>
  );
}
