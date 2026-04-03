# Feature Specification: Score Estimation WASM

**Feature Branch**: `134-score-estimation-wasm`  
**Created**: 2026-02-11  
**Status**: Draft  
**Input**: User description: "Implement OGS Score Estimator WASM for board analysis and ownership heatmap"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Ownership Heatmap (Priority: P1)

As a user struggling with a puzzle, I want to see a visual indication of which areas of the board are considered "alive" or "dead" so I can understand the situational status.

**Why this priority**: High pedagogical value; helps users understand the "why" behind a solution or failure by visualizing control.

**Independent Test**: Can be tested by toggling an "Analyze" button on a puzzle board and observing small colored markers or alpha-overlays on empty intersections indicating predicted ownership.

**Acceptance Scenarios**:

1. **Given** a puzzle board with stones, **When** the user activates analysis mode, **Then** all empty intersections should display a subtle visual marker (e.g., small square or translucent color) indicating whether the estimator predicts it will belong to Black or White.
2. **Given** a finished puzzle, **When** analysis is active, **Then** the markers should align with the final captured/owned areas.

---

### User Story 2 - Score Lead Estimation (Priority: P2)

As a user playing through a sequence, I want to see a numerical estimate of the current score lead to gauge if my moves are improving or worsening my position compared to the optimal path.

**Why this priority**: Provides quantitative feedback on move quality, bridging the gap between "Wrong" and "Losing by 20 points."

**Independent Test**: Can be tested by checking an info panel that displays "Black +15.5" or "White +2.4" after the estimator runs.

**Acceptance Scenarios**:

1. **Given** a board state, **When** the estimator runs, **Then** an info text or badge displays the estimated lead for the current player.
2. **Given** a move is made, **When** the estimate updates, **Then** the value should update smoothly to reflect the new state.

---

### User Story 3 - Exploratory Analysis (Priority: P3)

As a curious learner, I want to make moves that are NOT in the puzzle's solution tree (off-path) and still receive estimation feedback so I can explore side variations.

**Why this priority**: Enhances the "lab" feel of the app, allowing safe exploration without a traditional backend AI.

**Independent Test**: Can be tested by playing a move that triggers "Wrong," then entering Analysis Mode to see how that "wrong" move changed the ownership heatmap.

**Acceptance Scenarios**:

1. **Given** the user has made an incorrect move, **When** they toggle Analysis, **Then** a "Monte Carlo" simulation runs in the browser and displays ownership for the current (incorrect) position.

---

### Edge Cases

- **Large Boards**: How does performance hold up on 19x19 vs 9x9?
- **Unfinished Playouts**: What happens if the user makes a move while a high-trial (e.g., 5000) simulation is still running?
- **Invalid Positions**: How does the estimator handle positions with no liberties (illegal moves potentially allowed in analysis)?

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST load the `OGSScoreEstimator.wasm` module asynchronously on demand to avoid blocking initial app load.
- **FR-002**: System MUST convert the current Board entity state into a format compatible with the WASM `HEAP32` buffer (-1 for White, 1 for Black, 0 for Empty).
- **FR-003**: System MUST provide a toggle for "Analysis Mode" that triggers a score estimation with a default of 1000 trials.
- **FR-004**: System MUST render ownership values back onto the Board UI as non-blocking visual indicators.
- **FR-005**: System MUST calculate the score lead by summing ownership values across all intersections and applying standard Komi.

### Success Criteria

- **Performance**: Analysis results (heatmap + score) for a 19x19 board must appear in under 500ms for 1000 trials.
- **Offline Reliability**: The feature must function correctly without any network connection once the WASM bundle is cached.
- **Visual Clarity**: Analysis markers must be distinguishable from actual stones (e.g., smaller, translucent, or distinct shapes).
- **Zero Impact**: Activating analysis must not modify the underlying puzzle state or change the "Solved" status of the puzzle.

## Assumptions

- We will host the `.wasm` and its `.js` glue code locally within the `frontend/public/` directory or a CDN.
- The `OGSScoreEstimator` binary version 0.7.0 is compatible with modern browsers (WASM support).
- Current Board component in `frontend/src/` is extensible enough to support an "overlay" layer for ownership markers.
- **Turn Determination**: The estimator will use the current UI `activePlayer` context. If the position is a static setup with no history or `PL` tag, it will default to **Black**.

## Key Entities

- **EstimationResult**: An object containing the 2D matrix of ownership values [-100, 100] and the calculated score lead.
- **AnalysisState**: UI state managing whether estimation is active, the number of trials, and the current toggle status.
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria _(mandatory)_

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
