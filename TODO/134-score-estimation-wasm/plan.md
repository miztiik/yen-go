# Implementation Plan: Score Estimation WASM (Feature 134)

## Overview

Integrate the OGS Score Estimator WASM to provide ownership heatmaps and score lead estimation within the Yen-Go frontend. This follows a "Zero Backend" approach by running Monte Carlo simulations entirely in the browser.

## Tech Stack & Libraries

- **WASM**: `OGSScoreEstimator-0.7.0.wasm`
- **JS Infrastructure**: Emscripten-generated glue code (`OGSScoreEstimator-0.7.0.js`)
- **Frontend**: Preact, TypeScript, Vite
- **Storage**: `frontend/public/wasm/` for static assets

## Project Structure Changes

- `frontend/public/wasm/`: Storage for WASM binary and JS glue.
- `frontend/src/services/scoreEstimationService.ts`: Singleton service to manage WASM lifecycle (loading, memory allocation, execution).
- `frontend/src/types/scoreEstimation.ts`: Type definitions for estimation results and board states.
- `frontend/src/components/GobanBoard/OwnershipOverlay.tsx`: New component to render ownership markers.
- `frontend/src/hooks/useScoreEstimation.ts`: Domain hook to trigger estimations and manage results state.

## Implementation Strategy

1. **Infrastructure (Setup)**: Place WASM/JS files in public directory.
2. **Service Layer**: Implement the Emscripten wrapper. This involves `Module.cwrap` and manual memory management (`_malloc`, `_free`) to pass the board state (1, 0, -1) to the WASM.
3. **UI Layer (Overlay)**: Create a React/Preact overlay for the board that renders different markers based on ownership percentage (-100 to 100).
4. **Integration**: Connect the board state to the estimation service. When "Analysis" is toggled, capture the current board state, run the estimator (1000 trials), and update the overlay.

## Performance Considerations

- Estimation should run in a Web Worker (optional but recommended for large boards) to avoid freezing the UI.
- Use `1000 trials` as a default to balance speed and accuracy.
- Throttle recalculations during active play.

## Testing Strategy

- **Unit Tests**: Test the bit-conversion logic (Board state -> Int32Array).
- **Integration Tests**: Verify that the Emscripten module loads correctly in a browser environment.
- **Manual QA**: Compare ownership heatmap against known finished positions.
