# Clarifications — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Date**: 2026-03-20

---

## Clarification Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required for enrichment outputs? (i.e., must already-enriched puzzles remain valid, or can they be re-enriched?) | A: Yes, existing outputs must remain valid / B: No, re-enrichment is acceptable / C: Partial — config bump version but tolerate output drift | B: No — re-enrichment is acceptable. Config changes don't affect already-published SGFs (SGF properties are written at publish time, not runtime). Threshold changes affect FUTURE enrichment runs only. | Inferred B | ✅ resolved |
| Q2 | Should old config values be preserved as comments/fallback, or cleanly replaced? | A: Clean replace (config version bump) / B: Preserve old values as `_previous` keys / C: Other | A: Clean replace with version bump to v1.26. Changelog documents all changes. | Inferred A | ✅ resolved |
| Q3 | Should the adaptive-boost-override code fix (S-1) be included in this initiative, or tracked separately? | A: Include it (config + code in one initiative) / B: Separate initiative for code fix / C: Other | A: Include it — the code fix directly relates to the config values being tuned (corner_visit_boost, ladder_visit_boost are meaningless without the fix). | A | ✅ resolved |
| Q4 | What is the acceptable compute cost increase per batch? The visit budget changes (R-9, R-11, R-12, R-13) add ~15% compute time (~26 min per 1000 puzzles). | A: Accept ~15% increase / B: Budget-neutral only (reject visit increases) / C: Accept up to 25% increase / D: Other | A: Accept ~15% increase — accuracy improvement justifies the compute cost for an offline pipeline. | A | ✅ resolved |
| Q5 | Should calibration.sample_size be raised to 15 (TS recommendation, keeps it as smoke test) or 30 (ENG recommendation, makes it statistically meaningful)? | A: 15 (faster smoke test) / B: 20 (compromise) / C: 30 (matches ai_solve.calibration.min_samples_per_class) / D: Other | B: 20 — meaningful F1 estimation while keeping test runtime under control | B | ✅ resolved |
| Q6 | The seki_detection.winrate_band widening (0.45-0.55 → 0.43-0.57) is only recommended by one expert (TS). Should it be included? | A: Include it / B: Skip it — insufficient consensus / C: Other | B: Skip — single-source recommendation with medium confidence. Can be added in a future calibration cycle. | B | ✅ resolved |

---

## Decisions Captured

| D-ID | Decision | Value | Rationale |
|------|----------|-------|-----------|
| D-1 | Backward compatibility | Not required | Config changes affect future runs only. Published SGFs are immutable static files. |
| D-2 | Legacy removal | Clean replace | v1.26 config version bump with full changelog entry. No backward-compat shim needed. |
| D-3 | S-1 design intent resolution | Change from "override" to "compound" | AGENTS.md L248 documented the adaptive override as "by design" at v1.19 design time. However, adaptive mode was not activated until v1.24 (PI-2 feature activation). At v1.19, the override was latent — it only became a behavioral issue when adaptive mode went live. The original design intent was for adaptive allocation to control visit budgets, but it did not anticipate the interaction with edge-case boosts (which were already active since v1.14). Now that both features are active (v1.24), the correct behavior is compounding: `effective_visits = branch_visits * boost`. This preserves adaptive allocation's control while respecting edge-case boost intent. AGENTS.md will be updated to reflect the new compounding behavior. |
| D-4 | C9 threshold conservation | Satisfied | C9 from v1.23 applies to feature-gated thresholds activated in that release (PI-1/PI-3/PI-10/PI-11/PI-5/PI-6). The parameters being tuned in this initiative predate v1.23 feature gates or are general config values. No C9-protected thresholds are modified. |
| D-5 | Option selection | Option A: Full Consensus | 4-expert agreement on all 14 parameters. 15% compute increase acceptable for offline pipeline. Dead code fix critical for corner/ladder puzzle quality. |
