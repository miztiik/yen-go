# Research Synthesis - Enrichment Lab Production Gap Closure

## Inputs Reviewed

| SRC-ID | source | focus | outcome |
|---|---|---|---|
| SRC-1 | TODO/initiatives/20260315-research-gogogo-tactics-patterns/15-research.md | NG/F finding set and deferred rationale | Baseline mapping for NG-1..NG-5 and candidate accretive items |
| SRC-2 | TODO/ai-solve-enrichment-plan-v3.md | Unified enrichment target model | Captured intended end-state and known gap statements |
| SRC-3 | TODO/ai-solve-remediation-sprints.md | Gap closure claims and sprint completion statements | Cross-checked claims vs current config/code references |
| SRC-4 | TODO/kishimoto-mueller-search-optimizations.md | Search optimization scope and deferred techniques | Used for superseded/implemented state checks |
| SRC-5 | TODO/hinting-unification-transition-plan-v1.md | Hinting boundary and unification path | Used for non-goal boundary enforcement |
| SRC-6 | tools/puzzle-enrichment-lab/AGENTS.md | Current implementation architecture and known gotchas | Source of truth for active wiring and config flags |
| SRC-7 | config/katago-enrichment.json | Active schema and feature flags | Confirms shipped config fields through v1.21 |

## Objective Status Snapshot

| OBJ-ID | objective | status | evidence | note |
|---|---|---|---|---|
| OBJ-1 | Refutation quality phases A-D controls available in config | fully_met | `config/katago-enrichment.json` v1.18-v1.21 keys present | Functional wiring still needs runtime regression confirmation in execution phase |
| OBJ-2 | AI-solve unification baselines (depth profiles, alternatives, observability keys) | fully_met | `ai_solve` block present with expected sections | Plan artifacts claim completion; execution verification remains separate |
| OBJ-3 | NG-1 priority/urgency schema extension | not_met | No urgency field in current models documented by AGENTS map | Candidate accretive feature; schema impact medium |
| OBJ-4 | NG-2 static life/death heuristic formula | superseded | KataGo ownership-based detectors active; heuristic formula explicitly rejected | Keep rejected unless calibration evidence changes |
| OBJ-5 | NG-3 feature-plane style multi-layer debug output | partially_met | Detector system exists; no dedicated activation matrix artifact | Could be added as debug-only observability without NN coupling |
| OBJ-6 | NG-5 alpha-beta capture engine integration | superseded | KataGo-driven tactical analysis architecture in place | Not recommended for production scope |

## Planning Confidence and Risk

| MET-ID | metric | value | rationale |
|---|---|---|---|
| MET-1 | planning_confidence_score | 70 | Broad corpus alignment is good, but multiple accretive options remain with tradeoff uncertainty |
| MET-2 | risk_level | medium | Behavior and observability changes can affect quality metrics and release confidence |
| MET-3 | research_invoked | yes | Triggered due medium risk + evidence harmonization need |

## Key Research Outcome

- The current enrichment implementation appears broadly aligned with major plan tracks.
- The remaining useful work is accretive hardening, not foundational redesign.
- Highest-value remaining opportunities are in objective-verifiable observability/test rigor and selective signal enrichment.
