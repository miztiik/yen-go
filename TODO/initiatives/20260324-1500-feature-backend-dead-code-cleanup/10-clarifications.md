# Clarifications — Backend Dead Code Cleanup

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Last Updated**: 2026-03-24

---

## Research Summary (from `15-research.md` — 2 passes consolidated)

The Feature-Researcher found across two deep passes:

### Pass 1 — Dead Code Audit
- **~3,225 lines of dead production code** across 13 files (shard/snapshot system, trace_registry, dedup_registry, runtime.py, logging.py, maintenance/*, level_mapper, position_fingerprint)
- **~5,695 lines of orphan test code** that only test the dead modules
- **Dual adapter registry** creating 5 invisible adapters (blacktoplay, gogameguru, goproblems, ogs, url)
- **4 duplicated adapters** existing in both flat-file and subdirectory format

### Pass 2 — Documentation Audit (65 files scanned)
- **5 entirely obsolete docs** (snapshot-deployment-topology, snapshot-shard-terminology, view-index-pagination, view-index-segmentation, STAGES.md)
- **13 docs with critical stale content** (dead imports, wrong schema versions, missing CLI commands, wrong directory structures)
- **5 docs with medium stale content** (minor reference updates needed)
- **AGENTS.md says "Typer CLI" but `cli.py` actually uses `argparse`** — confirmed by reading the source

### Combined Scope
~48 files, ~13,390 lines of dead/obsolete content across code + tests + docs.

Planning Confidence Score: **95** (post-both-passes)
Risk Level: **medium** — broad deletion scope, but all dead code verified via grep.

---

## Clarification Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Is backward compatibility required?** Should old code be preserved in any form, or can we rely on git history for recovery? | A: Yes, preserve backward compat shims / B: No, delete everything dead (git history is sufficient) / C: Other | **B** | **B** — "Delete everything, no technical debt required because commit history is there." | ✅ resolved |
| Q2 | **What should we do with the 5 orphaned adapters** (blacktoplay, gogameguru, goproblems, ogs, url) that are registered into the dead registry and thus invisible to production? | A: Delete them entirely / B: Migrate to subdir format / C: Migrate only specific ones / D: Other | **A** | **A** — "Delete them if they are orphaned. The adapter code is moved to tools now. Will consolidate future but not required now." | ✅ resolved |
| Q3 | **Should old code removal happen?** Remove `base.py`, `registry.py` (the old adapter infrastructure)? | A: Yes, remove all old duplicates / B: No / C: Other | **A** | **A** — "No need for dual registry. We have moved away from the old one." | ✅ resolved |
| Q4 | **Keep `position_fingerprint.py` (rotation-aware dedup, never used)?** | A: Delete (recoverable from git) / B: Keep / C: Other | **A** | **A** — "Remove." | ✅ resolved |
| Q5 | **Include documentation fixes in this initiative?** | A: Include / B: Separate initiative / C: Other | **A** | **A** — "Yes, include documentation fixes if required." | ✅ resolved |
| Q6 | **Phase strategy: single PR or phased?** | A: Single atomic PR / B: 2 phases / C: 3+ phases / D: Other | **B** | **C/D** — "Make it multiple phases as required." | ✅ resolved |
| Q7 | **External dependency on `trace_registry.py` or `DedupRegistry`?** | A: No, safe to delete / B: Yes (specify) / C: Unsure | **A** | **A** — "No external tooling depends on trace registry. Remove." | ✅ resolved |
| Q8 | **Should `docs/STAGES.md`** (massively outdated) **be deleted?** | A: Delete / B: Move to archive / C: Other | **A** | **A** — "Delete." | ✅ resolved |
| Q9 | **Should `docs/guides/adapter-development.md`** be consolidated or removed? | A: Update / B: Redirect to how-to / C: Delete | **B** | **C/B** — "Consolidate or even remove. Wherever required, simplify." | ✅ resolved |
| Q10 | **AGENTS.md says "Typer CLI" but `cli.py` uses `argparse`.** Fix docs? | A: Fix docs to say argparse / B: Other | **A** | **A** — "Fix what is required. We are using argparse." | ✅ resolved |
| Q11 | **Confirm `adapters/__init__.py` edit in Phase 2** (remove `UrlAdapter` import line 27 + `__all__` entry)? Governance RC-1 requirement. | A: Yes / B: No | **A** — Required to prevent ImportError when `url.py` deleted | **A** — Auto-resolved per governance RC-1 (blocking) | ✅ resolved |
| Q12 | **Confirm AGENTS.md `url/` ghost reference fix** in Phase 3? Governance RC-3 item. | A: Yes / B: No | **A** — Part of docs accuracy sweep | **A** — Auto-resolved per governance RC-3 | ✅ resolved |

---

## Policy Source Reference

**Q1 Follow-up**: The "Delete, don't deprecate" policy is defined in two canonical locations:
1. `.github/copilot-instructions.md` line 441: `- **Dead code policy** — Delete, don't deprecate. Git history preserves everything.`
2. `frontend/CLAUDE.md` line 185: `6. **Dead code policy** — Delete, don't deprecate. Git history preserves everything.`

To change this policy in the future, update both files (and any CLAUDE.md files that reference it).

---

## Answers Log

All 12 questions resolved on 2026-03-24. Summary:
- **Backward compat**: Not required. Delete aggressively.
- **Orphaned adapters**: Delete (moved to tools/).
- **Old registry**: Delete (canonical is `_base.py` / `_registry.py`).
- **position_fingerprint**: Delete (YAGNI, recoverable from git).
- **Docs**: Include fixes in this initiative.
- **Phases**: Multiple phases as needed.
- **Trace registry/DedupRegistry**: No external deps, safe to delete.
- **STAGES.md**: Delete.
- **adapter-development.md**: Consolidate/simplify.
- **AGENTS.md Typer claim**: Fix to say argparse.
- **`adapters/__init__.py` edit**: Yes, required in Phase 2 (governance RC-1).
- **AGENTS.md `url/` ghost fix**: Yes, in Phase 3 (governance RC-3).
