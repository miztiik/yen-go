# Hinting Unification Transition Plan — v1

**Last Updated:** 2026-03-04  
**Status:** Draft for approval  
**Scope:**

- `tools/puzzle-enrichment-lab/` (lab hint generator + AI-solve integration path)
- `backend/puzzle_manager/core/enrichment/` (production hint generator)
- Shared docs and parity test strategy

---

## Objective

Prepare both hinting systems for a **clean future replacement** by a single engine-driven hinting mechanism, while keeping them independent for now.

### Non-Negotiable Direction

1. **Future state:** one canonical hinting system in pipeline.
2. **Current state:** lab and backend remain independent.
3. **Transition requirement:** integration must be smooth, low-risk, and non-overlapping.
4. **No dual-ownership ambiguity:** each system has explicit boundaries and compatibility contracts.

---

## Review Panel (Required for Every Phase)

This plan uses the same governance style as the AI-Solve v3 plan.

| Member                         | Domain              | Review Focus                                                                     |
| ------------------------------ | ------------------- | -------------------------------------------------------------------------------- |
| **Cho Chikun** (9p)            | Tsumego pedagogy    | Hint correctness, concept-first progression, no misleading teaching              |
| **Lee Sedol** (9p)             | Tactical creativity | Coverage of alternatives, robustness when multiple plausible continuations exist |
| **Shin Jinseo** (9p)           | AI-era Go           | Engine-aligned hint confidence, practical trust thresholds                       |
| **Ke Jie** (9p)                | Learning value      | Hint usefulness under imperfect certainty                                        |
| **Principal Staff Engineer A** | Architecture        | Isolation boundaries, replacement readiness, contract stability                  |
| **Principal Staff Engineer B** | Data/pipeline       | Determinism, observability, rollout safety, regression control                   |

### Gate Protocol (All Phases)

A phase is complete only when all conditions pass:

1. **Implementation complete** for that phase scope.
2. **Tests pass** (new + existing relevant suites).
3. **Documentation updated** for behavioral and contract changes.
4. **Review Panel sign-off** confirms no shortcut/band-aid approach.

---

## Key Transition Design Decisions

### DD-1: Contract-First Integration

Define a shared hint contract (schema + semantics) before touching behavior.

### DD-2: Independence with Parity

Both systems stay separate; parity is enforced by test fixtures and behavior expectations.

### DD-3: Single Source of Taxonomy Truth

Tag priority, aliases, and hint tier semantics are centralized as policy (not duplicated free-form logic).

### DD-4: Confidence-Gated Semantics

Technique/reasoning hints are emitted only under policy-approved confidence conditions; otherwise degrade safely.

### DD-5: Coordinate Token Consistency

Both systems must produce transform-safe coordinate hints consistently (`{!xy}` semantics and board-size correctness).

### DD-6: Replacement Readiness Metric

Introduce explicit readiness score for eventual swap: contract coverage, parity pass rate, drift rate, and unresolved deltas.

---

## Scope Boundaries (No Overlap)

### Backend (production) owns

- Runtime/pipeline hint behavior for published artifacts.
- SGF-aware semantics and production safety constraints.

### Lab owns

- Engine-driven experimentation, rapid heuristic iteration, calibration exploration.
- Candidate logic that can graduate via explicit contract checks.

### Shared (policy/docs/tests) owns

- Taxonomy map, hint tier semantics, fallback ladder, and parity fixture protocol.

---

## Phased Sequence (Actions by Step)

## Phase 1 — Baseline Inventory & Drift Map

**Goal:** Precisely enumerate where both systems differ today.

**Actions:**

1. Build a structured comparison matrix:
   - tag coverage
   - primary-tag selection
   - fallback rules
   - coordinate conversion rules
   - YH tier formatting
2. Classify each difference as:
   - intentional
   - accidental drift
   - unresolved ambiguity
3. Create “drift severity” levels:
   - pedagogical risk
   - correctness risk
   - replacement-blocking risk

**Deliverables:**

- Drift matrix document in `TODO/`.
- Prioritized drift backlog with owner (lab/backend/shared).

**Tests/Validation:**

- Golden fixture sample run across both systems.
- Baseline mismatch report archived.

**Gate:** Panel confirms inventory is complete and correctly prioritized.

---

## Phase 2 — Shared Hint Contract Spec

**Goal:** Define the compatibility contract that both implementations must satisfy.

**Actions:**

1. Specify canonical contract for:
   - input fields
   - output tiers (`YH1/YH2/YH3`) semantics
   - fallback ladder behavior
   - confidence/degrade rules
2. Specify compatibility profiles:
   - strict parity fields (must match)
   - tolerant fields (wording may differ)
3. Define contract versioning and deprecation policy.

**Deliverables:**

- Contract spec doc under `docs/reference/`.
- Versioned changelog section for hint contract.

**Tests/Validation:**

- Contract schema test vectors.
- Validation checklist for both implementations.

**Gate:** Panel signs off that contract is replacement-safe and unambiguous.

---

## Phase 3 — Taxonomy & Priority Harmonization

**Goal:** Eliminate semantic drift from tags/aliases/priority ordering.

**Actions:**

1. Define canonical tag alias map (single policy source).
2. Define deterministic primary-tag selection policy.
3. Mark unsupported/legacy tags with explicit behavior.
4. Add policy docs for secondary-tag usage in reasoning hints.

**Deliverables:**

- Taxonomy policy doc under `docs/concepts/`.
- Migration notes for both implementations.

**Tests/Validation:**

- Cross-system tag normalization tests.
- Priority determinism tests for mixed-tag inputs.

**Gate:** Panel confirms no hidden tag ambiguity remains.

---

## Phase 4 — Fallback Ladder Alignment

**Goal:** Make degradation behavior safe, deterministic, and convergent.

**Actions:**

1. Standardize fallback ladder:
   - atari relevance gate
   - tag-priority technique mapping
   - solution-aware/engine-aware inference
   - analysis-metric generic reasoning
   - coordinate-only final fallback
2. Define “do no harm” suppression rules (when not to emit technique/reasoning).
3. Define confidence thresholds and minimum evidence requirements.

**Deliverables:**

- Fallback policy spec.
- Decision table with examples and expected outputs.

**Tests/Validation:**

- Scenario-based fallback tests.
- False-positive suppression tests.

**Gate:** Panel confirms pedagogical safety under uncertain positions.

---

## Phase 5 — Coordinate & Token Semantics Alignment

**Goal:** Ensure both systems are transform-safe and board-size correct.

**Actions:**

1. Standardize coordinate token requirements (`{!xy}` only in final hints).
2. Define conversion policy for GTP↔SGF with explicit board-size behavior.
3. Add edge-case policy for pass/invalid coordinates.

**Deliverables:**

- Coordinate semantics reference in `docs/reference/`.

**Tests/Validation:**

- 9x9/13x13/19x19 coordinate conversion suite.
- Token roundtrip and transform-safety tests.

**Gate:** Panel confirms no board-size or transform ambiguity.

---

## Phase 6 — Dual-Track Implementation (Independent Changes)

**Goal:** Apply agreed policies independently to lab and backend without coupling.

**Actions (Lab track):**

1. Refactor lab hint generator to satisfy contract + taxonomy + fallback policy.
2. Keep AI-solve/analysis-driven strengths; enforce confidence-gated emissions.
3. Emit structured observability fields for parity diagnostics.

**Actions (Backend track):**

1. Refactor production hint generator to same contract and policy behavior.
2. Preserve SGF-aware safety constraints and production defaults.
3. Add compatibility logging for drift diagnostics.

**Deliverables:**

- Independent implementation updates with explicit compliance checklist.

**Tests/Validation:**

- Each track passes its own full suite.
- Shared parity suite passes agreed threshold.

**Gate:** Panel confirms both tracks are compliant and still independent.

---

## Phase 7 — Parity Harness & Drift Budgets

**Goal:** Continuously detect and limit cross-system divergence.

**Actions:**

1. Build parity harness that executes both implementations on the same fixtures.
2. Define mismatch categories:
   - hard fail (contract violation)
   - soft fail (tolerable wording variance)
3. Introduce drift budgets and CI threshold gates.

**Deliverables:**

- Parity test module under each subsystem’s test strategy.
- Drift dashboard/log artifact spec.

**Tests/Validation:**

- CI parity gate for critical fixtures.
- Trend report showing drift reduction over time.

**Gate:** Panel approves drift thresholds for replacement readiness.

---

## Phase 8 — Documentation Convergence Package

**Goal:** Make migration and future replacement operationally clear.

**Actions:**

1. Update architecture docs with dual-track now / single-engine later roadmap.
2. Add how-to docs for adding new hint rules without introducing overlap.
3. Add reference docs for contract, taxonomy, fallback ladder, coordinate semantics.
4. Add troubleshooting guide for parity failures.

**Deliverables (minimum):**

- `docs/architecture/...` migration architecture update
- `docs/how-to/...` authoring + validation workflow
- `docs/concepts/...` taxonomy and pedagogy semantics
- `docs/reference/...` contract and thresholds

**Tests/Validation:**

- Documentation link validation.
- “Can a new contributor implement a compliant hint rule?” walkthrough.

**Gate:** Panel confirms docs are sufficient for safe implementation.

---

## Phase 9 — Replacement Readiness Assessment (No Swap Yet)

**Goal:** Determine whether both systems are ready for eventual one-system replacement.

**Actions:**

1. Define readiness scorecard:
   - contract conformance rate
   - parity pass rate
   - unresolved drift count
   - confidence policy adherence
   - production incident risk
2. Produce go/no-go recommendation for future replacement phase.
3. List blocking items and required remediation if no-go.

**Deliverables:**

- Readiness report in `TODO/`.

**Tests/Validation:**

- Final parity + regression run.
- Targeted pedagogical review sample by panel.

**Gate:** Panel issues replacement recommendation (prepare/hold).

---

## Test Strategy (Required)

### A. Shared Contract Tests

- Schema conformance
- Required/optional field behavior
- Version compatibility checks

### B. Taxonomy Tests

- Alias normalization
- Priority determinism
- Unsupported tag behavior

### C. Fallback Safety Tests

- Confidence-gated emission behavior
- Coordinate-only degradation correctness
- “Do No Harm” suppression in ambiguous contexts

### D. Coordinate Tests

- 9x9/13x13/19x19 conversion
- Pass/invalid handling
- Token transform invariance expectations

### E. Parity Tests

- Fixture-based cross-implementation comparison
- Hard/soft mismatch categorization
- Drift trend regression

### F. Regression Tests

- Existing backend hint behavior invariants where required
- Existing lab behavior invariants where required

---

## Validation & Quality Gates

Each phase must include:

1. Unit test pass
2. Integration/parity pass (where applicable)
3. Determinism check (repeat runs stable)
4. Documentation completeness check
5. Review Panel sign-off

---

## Risks and Mitigations

| Risk                                                 | Severity | Mitigation                                              |
| ---------------------------------------------------- | -------- | ------------------------------------------------------- |
| Hidden taxonomy drift keeps reappearing              | High     | Single policy source + parity CI gate                   |
| Over-coupling lab and backend during transition      | High     | Strict ownership boundaries + contract-only integration |
| Misleading hints under low-confidence engine outputs | High     | Confidence-gated fallback + suppression policy          |
| Coordinate mistakes on non-19 boards                 | Medium   | Mandatory board-size test matrix                        |
| Wording churn causes noisy parity failures           | Medium   | Hard vs soft mismatch categories                        |
| Replacement decision made without evidence           | High     | Readiness scorecard + final panel gate                  |

---

## Non-Goals

- Immediate unification into one module now.
- Runtime backend architectural changes outside hinting scope.
- UI/UX redesign of hint presentation.
- Any bypass of Review Panel phase gates.

---

## Proposed Next Decision (for your approval)

1. Approve this plan structure and phase gates.
2. Start with **Phase 1** artifacts only (inventory + drift map), no code changes.
3. Review drift severity results before approving Phase 2 contract spec.

---

## Version History

| Version | Date       | Change                                                                               |
| ------- | ---------- | ------------------------------------------------------------------------------------ |
| v1      | 2026-03-04 | Initial transition plan for dual-track hinting convergence and replacement readiness |
