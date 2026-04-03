# 009 — Principal Review Gap Plan (KataGo Tsumego Enrichment)

Last Updated: 2026-03-02

## Scope

Read-only architecture and implementation review of `tools/puzzle-enrichment-lab` against the 5 promised outcomes:

1. Validate correct first move
2. Build refutation tree for wrong moves
3. Estimate difficulty (novice → expert)
4. Generate teaching comments
5. Generate hints

Constraint honored: **no runtime code changes in this review**.

---

## Executive Verdict

The system is **real but uneven**:

- Core end-to-end orchestration is implemented and test-covered.
- Item (1) is implemented but algorithmically weaker than advertised for life/death correctness.
- Item (2) is only partially implemented (single principal variation lines, not robust tactical tree exploration).
- Item (3) is implemented but some configured factors are not actually used in scoring.
- Items (4) and (5) are implemented but are mostly template/heuristic quality, with board-size edge-case bug risk for hint coordinates.

Bottom line: your doubt is justified. This is not fake, but it is **not yet strong enough to claim reliable tsumego-grade engine enrichment**.

---

## Findings by Golden Rule

### 1) Validate correct first move (KataGo agreement)

**Status:** Implemented, but method mismatch vs strong tsumego expectations.

**What exists**

- Validation pipeline in `analyzers/validate_correct_move.py` with ko branch integration.
- Candidate move selection and top-move agreement checks.

**Main gap**

- Current acceptance logic is dominated by rank/winrate proxies and disagreement thresholds.
- Config/docs imply stronger life/death target-outcome validation, but ownership-threshold style checks are not effectively enforced in the acceptance decision.

**Impact**

- Can accept/reject moves based on broad engine preference rather than explicit local life/death truth.
- Vulnerable on ko, seki, sacrifice tesuji, and low-prior but correct tactical moves.

---

### 2) Refutations tree for wrong moves

**Status:** Partial.

**What exists**

- Wrong-move candidate extraction + response generation in `analyzers/generate_refutations.py`.
- Produces wrong-move entries and short punishment lines.

**Main gap**

- Not a real branching refutation tree; mostly shallow PV extraction per wrong move.
- Curated enrichment can still emit empty/weak PV outcomes.

**Impact**

- Looks like refutation output, but tactical completeness is insufficient for many tsumego traps.

---

### 3) Difficulty estimation (novice → expert)

**Status:** Implemented, calibration fragile.

**What exists**

- Scoring logic in `analyzers/estimate_difficulty.py`, level mapping through configured thresholds.

**Main gaps**

- Structural score path does not fully use configured structural-weight controls.
- Some intended factors (local candidate/refutation counts) are underutilized in final score.
- `visits_to_solve` can be misleading as a hardness proxy for tsumego (policy-biased easy/hard inversions).

**Impact**

- Difficulty labels may be directionally okay, but unstable at boundaries and untrustworthy for fine granularity.

---

### 4) Teaching comments

**Status:** Implemented, moderate quality ceiling.

**What exists**

- `analyzers/teaching_comments.py` generates correct/wrong/summary comments.

**Main gap**

- Largely template-driven with limited deep tactical grounding from engine signals.

**Impact**

- Useful baseline pedagogically, but often generic for stronger users.

---

### 5) Hints

**Status:** Implemented, notable correctness bug risk.

**What exists**

- Tiered hint generation in `analyzers/hint_generator.py`, including compact SGF token formatting.

**Main gap**

- Coordinate conversion path assumes 19x19 behavior in helper logic, risking wrong coordinates on 9x9/13x13 puzzles.

**Impact**

- Hints can point to wrong board locations on non-19 boards.

---

## Why KataGo May Seem “Not Performing Well”

1. **Validation objective mismatch:** engine preference ≠ local life/death truth.
2. **Refutation depth too shallow:** single-line PV misses many tactical branches.
3. **Mode/config fragility:** referee-only paths can hard-fail without complete model setup.
4. **Calibration weakness:** tests/sampling are not yet strong enough to lock thresholds confidently.
5. **Determinism/variance not characterized:** results can drift run-to-run without explicit tolerance policy.

---

## Prioritized Plan for Next Agent

### P0 (must fix first)

1. **Rebuild first-move validator around local life/death outcomes**
   - Target files:
     - `tools/puzzle-enrichment-lab/analyzers/validate_correct_move.py`
     - `tools/puzzle-enrichment-lab/analyzers/ko_validation.py`
     - `config/katago-enrichment.json`
   - Direction:
     - Promote ownership/target-group outcome checks to first-class acceptance criteria.
     - Keep rank/winrate as secondary tie-break signals.

2. **Harden engine mode fallback to avoid referee-only dead paths**
   - Target files:
     - `tools/puzzle-enrichment-lab/analyzers/dual_engine.py`
     - `tools/puzzle-enrichment-lab/cli.py`
     - `tools/puzzle-enrichment-lab/config.py`
   - Direction:
     - Validate model availability up front; deterministic fallback strategy with explicit warnings.

3. **Fix non-19 board coordinate hint conversion**
   - Target file:
     - `tools/puzzle-enrichment-lab/analyzers/hint_generator.py`
   - Direction:
     - Board-size-aware conversion and tests for 9/13/19.

### P1 (algorithmic quality uplift)

4. **Upgrade from shallow refutation lines to bounded tactical refutation tree**
   - Target file:
     - `tools/puzzle-enrichment-lab/analyzers/generate_refutations.py`
   - Direction:
     - Multi-branch exploration per wrong first move (depth + breadth caps).
     - Store confidence/coverage metadata per branch.

5. **Make difficulty model configuration-consistent and observable**
   - Target files:
     - `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`
     - `config/katago-enrichment.json`
   - Direction:
     - Ensure configured structural weights are actually used.
     - Add score decomposition fields to outputs for auditability.

6. **Improve technique detection robustness**
   - Target file:
     - `tools/puzzle-enrichment-lab/analyzers/technique_classifier.py`
   - Direction:
     - Board-geometry-aware heuristics and explicit evidence extraction from PV/ownership deltas.

### P2 (hardening + product quality)

7. **Raise teaching comments from template-only to evidence-backed explanations**
   - Target file:
     - `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py`
   - Direction:
     - Tie explanation snippets to concrete engine evidence (policy delta, tactical threat, liberties swing).

8. **Define determinism and stability policy**
   - Target files:
     - `tools/puzzle-enrichment-lab/scripts/run_calibration.py`
     - `tools/puzzle-enrichment-lab/tests/test_calibration.py`
     - docs under `docs/architecture/tools/`
   - Direction:
     - Repeat-run variance checks with acceptance thresholds for status/level/refutation consistency.

---

## Verification Plan (Next Agent)

### A. Correctness (golden rules)

- Build a curated benchmark set split by motif:
  - life/death, ko, seki, semeai, snapback, ladder, throw-in.
- Measure:
  - First-move acceptance precision/recall.
  - Refutation branch tactical validity.
  - Difficulty rank correlation vs curated human labels.
  - Teaching/hint human review score.

### B. Regression tests

- Add/extend tests under `tools/puzzle-enrichment-lab/tests/`:
  - board-size coordinate tests (9/13/19)
  - validator edge cases (ko, seki, sacrifice)
  - refutation branching coverage tests
  - score decomposition invariants for difficulty

### C. Performance + repeatability

- Run repeated fixed-seed/fixed-config batches and report variance.
- Keep operational time bounds (single puzzle and batch) with alerts on outliers.

---

## Definition of Done for Next Agent

A change is accepted only if all are true:

1. Golden Rules 1–5 are demonstrably met by tests and benchmark artifacts.
2. Refutation output is branch-aware (not single-line only) with bounded complexity.
3. Difficulty score components are transparent and configuration-faithful.
4. 9x9/13x13/19x19 coordinate correctness is validated.
5. Documentation is updated with method assumptions and known failure modes.

---

## Suggested Handoff Order

1. P0.1 validator rewrite
2. P0.3 hint coordinate fix
3. P0.2 engine mode hardening
4. P1.4 refutation tree
5. P1.5 difficulty model consistency
6. P1.6 technique robustness
7. P2 hardening and calibration

This order maximizes correctness first, then tactical depth, then model quality and operational resilience.
