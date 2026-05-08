# KataGo Enrichment Status

> **See also**:
>
> - [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) — design decisions and system boundaries
>
> - [How-To: Enrichment Lab](../how-to/tools/katago-enrichment-lab.md) — local workflow and commands
>
> - [Reference: KataGo Enrichment Config](./katago-enrichment-config.md) — runtime configuration surface
>
> - [Reference: Consolidated Backlog](./consolidated-backlog.md) — still-open follow-through themes

**Last Updated**: 2026-05-08

This page is the canonical current-state lookup for the KataGo enrichment system. It replaces the retired enrichment planning bundle as the docs-native summary of what is shipped, what is experimental, and what still needs follow-through.

## Runtime Posture

| Area | Current State | Canonical Notes |
| --- | --- | --- |
| Local KataGo enrichment | Primary and only production-quality enrichment path | Runs through `tools/puzzle-enrichment-lab/` and the local engine flow. |
| AI-solve for position-only puzzles | Implemented | Core remediation landed. The planned live calibration sweep was retired under current scope, so threshold defaults remain unvalidated by a live sweep. |
| Phase B teaching, technique, and hints | Implemented in the lab pipeline | Backend and lab hinting alignment remains an active transition area. |
| KM search optimizations | Canonical design captured | Follow-through remains active where budget policy and review-driven heuristics still need closing work. |
| Browser-side analysis | Experimental only | Not part of the production enrichment contract or the pipeline-facing path. |

## Shipped Vs Experimental

| Track | Status | Scope |
| --- | --- | --- |
| SGF enrichment and writeback | Shipped | Validation, refutations, difficulty, tags, comments, hints, and SGF property updates via the local engine path. |
| Bridge and lab UI | Shipped as lab tooling | Supports local workflow, inspection, and manual runs. |
| Browser prototype under `tools/puzzle-enrichment-lab/js/` | Experimental | Surviving prototype work exists, but it is optional lab code and not a committed product surface. |
| Browser engine graduation | Undecided | Requires an explicit keep, retire, or remove decision before it should be treated as product direction. |

## Durable Follow-through

| Theme | What remains canonical |
| --- | --- |
| AI-solve hardening | Keep validator behavior, fallback semantics, tier semantics, and docs aligned with the implemented design. |
| Hinting transition | Align lab-produced hinting signals with backend hint behavior without duplicating logic or source-of-truth docs. |
| KM follow-through | Keep budget-saving heuristics, verification rules, and observability aligned with the documented design. |
| Browser prototype posture | Preserve the experimental prototype as optional lab work until a dedicated graduation or retirement decision is made. |

## Accepted Limitations

| Area | Current Decision |
| --- | --- |
| AI-solve threshold calibration | No live KataGo calibration sweep is planned for this track. Threshold defaults remain unvalidated by a live sweep and should be treated as implementation defaults, not calibrated guarantees. |

## Historical Planning Retirement

The former enrichment planning bundle has been decomposed into canonical documentation:

- Design rationale and long-term constraints belong in [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md).
- Operational workflow belongs in [How-To: Enrichment Lab](../how-to/tools/katago-enrichment-lab.md).
- Runtime knobs belong in [Reference: KataGo Enrichment Config](./katago-enrichment-config.md).
- Still-open work themes belong in [Reference: Consolidated Backlog](./consolidated-backlog.md).

No active repository memory should depend on the retired planning bundle.
