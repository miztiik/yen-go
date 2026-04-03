# Clarifications — KataGo .cfg Audit & Fix

**Initiative ID**: `20260320-2200-feature-katago-cfg-audit-fix`
**Status**: approved

---

## Blocking Questions

No blocking questions identified. The expert audit provided complete, unambiguous instructions for all parameter changes.

## Resolved Clarifications

| q_id | question | resolution | resolved_by |
|------|----------|------------|-------------|
| Q1 | Should `cpuctExplorationAtRoot` be replaced or just deleted? | Delete only — not a valid KataGo key | KataGo-Engine-Expert |
| Q2 | What value for `rootPolicyTemperatureEarly`? | 1.5 (tsumego-optimized) vs 1.0 (safe default) — expert recommends 1.5 | KataGo-Tsumego-Expert |
| Q3 | Should `dynamicScoreUtilityFactor` be changed? | No — existing value 0.1 is correct | KataGo-Engine-Expert |
| Q4 | Backward compatibility required? | No — config changes affect future runs only; published SGFs are immutable | Planning decision |
