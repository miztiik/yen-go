# Clarifications: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Last Updated**: 2026-03-08

---

## Clarification Rounds

### Round 1 (2026-03-08)

| q_id | question                                       | options                                                                                           | recommended          | user_response                                                                            | status      |
| ---- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------- | ----------- |
| Q1   | Ko threats module: include now or defer?       | A: Include as optional module / B: Defer / C: Other                                               | A — modular add-on   | **A — Include ko threats**                                                               | ✅ resolved |
| Q2   | `offence_to_win` parameter: which default?     | A: 10 (ghostban) / B: 5 (KaTrain) / C: Configurable, default 10 / D: Other                        | C — configurable     | **C — Configurable, default 10**                                                         | ✅ resolved |
| Q3   | Orientation normalization (snap+flip+rotate)?  | A: Full normalize→frame→denormalize / B: Frame in-place / C: Other                                | A — simplifies logic | **A — Full normalize pipeline**                                                          | ✅ resolved |
| Q4   | Module location for new code?                  | A: Same file replace / B: Package `analyzers/frame/` / C: Single file, clean functions / D: Other | C — single file      | **C — Replace existing single file, clean function decomposition**                       | ✅ resolved |
| Q5   | Naming convention?                             | A: `tsumego_frame_v2` / B: Custom name / C: Keep `tsumego_frame`                                  | Keep `tsumego_frame` | **Keep `tsumego_frame` — no version suffix, industry-standard name, git tracks history** | ✅ resolved |
| Q6   | Wire new capabilities into `query_builder.py`? | A: Yes, thread ko_type / B: Keep as-is / C: Other                                                 | A — natural          | **A — Wire up, query_builder already knows ko_type**                                     | ✅ resolved |

### Round 1b — Backward Compatibility (2026-03-08)

| q_id | question                                                        | options                                                    | recommended       | user_response                                                                                           | status      |
| ---- | --------------------------------------------------------------- | ---------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------- | ----------- |
| Q-BC | Is backward compatibility required? Should old code be removed? | A: BC required, keep old / B: No BC, remove old / C: Other | B — clean rewrite | **B — No backward compatibility. Delete old code entirely. Keep anything useful, throw away the rest.** | ✅ resolved |

### Round 1c — Naming Convention (2026-03-08)

| q_id | question                                                                       | options                                         | recommended        | user_response                                                                      | status      |
| ---- | ------------------------------------------------------------------------------ | ----------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------- | ----------- |
| Q-NC | Python code should use snake_case (e.g., `apply_tsumego_frame`) not camelCase? | A: snake_case (PEP 8) / B: camelCase / C: Other | A — PEP 8 standard | **A — snake_case for Python. camelCase only for future JS/TS port. Follow PEP 8.** | ✅ resolved |

## Key Decisions Locked

1. **No backward compatibility** — V1 code is deleted and replaced
2. **`tsumego_frame`** — name stays, no version suffix
3. **snake_case** in Python, camelCase only when ported to JS/TS
4. **Single file** with clean function decomposition and typed payloads
5. **Ko threats included** as optional module (gated on `ko_type`)
6. **`offence_to_win = 10`** as default, configurable
7. **Full normalization** (normalize→frame→denormalize)
8. **Wire into `query_builder.py`** to pass `ko_type` through

## Open Items

None — all clarifications resolved.
