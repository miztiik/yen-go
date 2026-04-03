# Options: Enrichment Lab No-Solution Resilience

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Last Updated:** 2026-03-07  
**Planning Confidence Score:** 88 (post-research)  
**Risk Level:** low  
**Research Invoked:** Yes — Feature-Researcher (WebKatrain comparison, 15-research.md)

---

## Context

Two bugs in `enrich_single_puzzle()` hard-reject puzzles that lack solution trees, discarding all potential enrichment. Research confirmed that WebKaTrain has no classification gate — KataGo ALWAYS returns useful move data. Our failure is in our own classification pipeline, not in KataGo.

Three root causes:

1. `ai_solve.enabled=false` config gate blocks position-only SGFs from ever reaching KataGo
2. `confirmation_min_policy=0.03` pre-filter in `analyze_position_candidates()` can exclude all candidates
3. `root_winrate` derived from `move_infos[0].winrate` instead of `AnalysisResponse.root_winrate`

---

## Options Comparison

| OPT-ID | Option                                          | Approach                                                                                                                                                                                           | Complexity                         | Migration Risk                        |
| ------ | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------- |
| OPT-1  | **Soft-Downgrade with Position Scan**           | Remove hard exits. For position-only + no-ai_solve: run lightweight KataGo scan. For no-correct-found: reuse existing analysis. Both return `enrichment_tier=1`. Fix `root_winrate` derivation.    | Medium (3 files, ~80 lines)        | Low                                   |
| OPT-2  | **Always-Analyze with Graceful Fallback**       | Remove hard exits. ALWAYS run KataGo analysis regardless of `ai_solve` flag. Decouple "position analysis" from "solution tree building". Use top move as pseudo-correct for all enrichment stages. | Medium-Large (4 files, ~120 lines) | Medium — changes `ai_solve` semantics |
| OPT-3  | **Minimal: Fix Classification + Fallback Only** | Fix `root_winrate` derivation (CA-1). Fix pre-filter to always keep top-1 by visits. Replace hard exits with error-tier result. No new KataGo calls for Bug A path.                                | Small (2 files, ~40 lines)         | Very Low                              |

---

## OPT-1: Soft-Downgrade with Position Scan

### Approach

1. **Fix CA-1** (`solve_position.py`): Use `AnalysisResponse.root_winrate` directly instead of deriving from `move_infos[0].winrate`
2. **Bug A** (`enrich_single.py:546`): Replace hard-exit with a new "position scan" path:
   - Run KataGo at low visits (100–200, configurable via `partial_enrichment_scan_visits`)
   - Use response for: difficulty estimation (policy-only), technique classification, hint generation
   - Return `AiAnalysisResult` with `enrichment_tier=1`, no solution tree injection, `ac:0`
3. **Bug B** (`enrich_single.py:598`): Replace hard-exit with partial enrichment:
   - Reuse `pos_analysis` data already obtained from KataGo
   - Pass to difficulty estimators using top move by visits as "pseudo-correct"
   - Return `AiAnalysisResult` with `enrichment_tier=1`
4. **Model change** (`ai_analysis_result.py`): Add `enrichment_tier: int = 3` field (backward compat default)

### Benefits

- Converts 100% of currently-rejected SGFs into partially-enriched outputs
- KataGo call always produces useful data (matches WebKaTrain philosophy)
- Clear tier system for downstream consumers (pipeline integration-ready)
- `enrichment_tier` field tells `backend/puzzle_manager` exactly what to trust

### Drawbacks

- Adds a KataGo call for every position-only SGF (when ai_solve is off)
- Slight complexity: two different partial-enrichment paths (Bug A vs Bug B)

### Risks

- New KataGo call could fail if engine not started → mitigate: wrap in try/except, return tier-1 without KataGo data
- Volume impact if many position-only SGFs → mitigate: scan at low visits (100), configurable

### SOLID/DRY/KISS/YAGNI

- **SRP**: Position scan is a coherent new responsibility
- **DRY**: Both partial paths share tier-1 assembly logic (extract to helper)
- **KISS**: Simple fallthrough, no new abstractions
- **YAGNI**: Only adds `enrichment_tier` field and scan visits config — nothing speculative

---

## OPT-2: Always-Analyze with Graceful Fallback

### Approach

1. **Fix CA-1** (same as OPT-1)
2. **Decouple analysis from ai_solve**: Move KataGo position analysis OUTSIDE the `ai_solve` gate. Every puzzle gets analyzed regardless of `ai_solve.enabled`:
   - Step 2 in `enrich_single_puzzle()` always runs KataGo analysis
   - `ai_solve` flag only controls whether to BUILD a solution tree from the analysis
   - Solution tree building requires `ai_solve.enabled=true` AND `correct_moves` found
3. **Bug A**: No longer exists — KataGo analysis always runs
4. **Bug B**: Falls through to partial enrichment using analysis data
5. **Model change**: Same as OPT-1

### Benefits

- Cleanest architecture: single analysis path, `ai_solve` only gates tree construction
- Eliminates the concept of "position-only rejection" entirely
- Every puzzle gets at least tier-1 enrichment
- Most future-proof for pipeline integration

### Drawbacks

- **Changes `ai_solve` semantics**: Currently `ai_solve.enabled=false` means "no KataGo analysis for position-only SGFs." This changes it to "no tree building, but always analyze."
- More refactoring: restructure the entire Step 2 control flow
- Risk of subtle regressions in existing has-solution path

### Risks

- Has-solution path (line 753) depends on pre-analysis from the ai_solve block. Restructuring could break this.
- More code movement = more merge conflicts with concurrent work
- Semantic change to `ai_solve` config requires documentation update

### SOLID/DRY/KISS/YAGNI

- **SRP**: Better — analysis separated from tree building
- **DRY**: Single analysis path instead of two
- **KISS**: Moderate — more restructuring, but simpler end state
- **YAGNI**: Slightly over-engineered — we don't need "always analyze" today if we just fix the two bugs

---

## OPT-3: Minimal — Fix Classification + Fallback Only

### Approach

1. **Fix CA-1** (`solve_position.py`): Use `AnalysisResponse.root_winrate`
2. **Fix pre-filter** (`solve_position.py`): Always keep the top-1 move by visits in `candidates_for_confirmation`, even if below `confirmation_min_policy`. This guarantees at least one candidate.
3. **Bug A** (`enrich_single.py:546`): Replace `_make_error_result()` with a minimal fallback:
   - Return `AiAnalysisResult` with `enrichment_tier=1`, `status=FLAGGED` (not REJECTED)
   - No KataGo call, no difficulty estimation — just technique tags from stone patterns
   - Set `ac:0`
4. **Bug B** (`enrich_single.py:598`): Same as OPT-1 — reuse existing `pos_analysis`

### Benefits

- Smallest change footprint (2 files, ~40 lines)
- No new KataGo calls
- Pre-filter fix prevents "zero correct moves" from ever happening when ai_solve IS active
- Lowest regression risk

### Drawbacks

- **Bug A path gets NO KataGo data**: Position-only SGFs without ai_solve get technique tags from stone patterns only — no policy-based difficulty, no winrate-based analysis
- Tier-1 output for Bug A is very sparse — limited value for downstream pipeline
- Does NOT match the WebKaTrain insight (always analyze)

### Risks

- Minimal risk — very localized changes

### SOLID/DRY/KISS/YAGNI

- **SRP**: Minimal impact
- **DRY**: Fine
- **KISS**: Simplest possible fix
- **YAGNI**: Arguably TOO minimal — Bug A path produces low-value output

---

## Recommendation

**OPT-1 (Soft-Downgrade with Position Scan)** is recommended.

| Criterion                               | OPT-1  | OPT-2        | OPT-3                    |
| --------------------------------------- | ------ | ------------ | ------------------------ |
| Fixes both bugs                         | ✅     | ✅           | ✅ (partially)           |
| KataGo data for all paths               | ✅     | ✅           | ❌ (Bug A has no KataGo) |
| Regression risk                         | Low    | Medium       | Very Low                 |
| Pipeline integration readiness          | High   | High         | Low                      |
| Change footprint                        | Medium | Medium-Large | Small                    |
| `ai_solve` semantics preserved          | ✅     | ❌           | ✅                       |
| WebKaTrain insight captured             | ✅     | ✅           | ❌                       |
| Future-proofing for backend integration | ✅     | ✅           | ❌                       |

OPT-1 captures the WebKaTrain insight (always get KataGo data) without restructuring the entire control flow. It preserves `ai_solve` semantics (on/off for tree building) while adding a lightweight scan path for position-only SGFs. The `enrichment_tier` field gives `backend/puzzle_manager` a clean contract for future integration.

OPT-3 is too minimal — it doesn't solve the user's core complaint that "we're not doing enrichment when there's no solution." OPT-2 is architecturally cleaner but changes `ai_solve` semantics, which creates documentation debt and subtle behavioral changes for existing users.
