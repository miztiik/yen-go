# Options - Enrichment Lab Production Gap Closure

## Option Set

| OPT-ID | title | approach_summary | benefits | drawbacks | risks | complexity | test_impact | rollback_implication | architecture_policy_notes | recommendation_candidate |
|---|---|---|---|---|---|---|---|---|---|---|
| OPT-1 | Production Hardening First | Focus on objective-verifiable hardening only: finalize observability propagation checks, close test gaps (multi-orientation target), and align docs/governance records for production run readiness. | Lowest regression risk, fastest to production confidence, aligns with strict closure bar and no-compatibility direction. | Defers new learning-signal features that may improve pedagogy. | Medium risk of under-delivering innovation; low runtime risk. | Medium | High test additions, low behavior churn. | Simple rollback (revert accretive hardening patches). | Strongly aligned with C1-C4 and user quality bar (Q4). | ✅ yes |
| OPT-2 | Balanced Hardening + Signal Enrichment | Deliver hardening plus 1-2 bounded signal improvements (e.g., trap-move ordering and policy-entropy-backed ranking) behind config flags. | Better pedagogical output and hardening together; still bounded scope. | More moving parts, higher validation burden, potential metric drift. | Medium-high behavior risk if thresholds are unstable. | High | High test matrix expansion (behavior + backward output assertions). | Moderate rollback complexity due mixed behavior and tooling changes. | Allowed under boundaries if scoped to enrichment-lab and fully tested. | no |
| OPT-3 | Feature-Forward Enrichment Expansion | Prioritize deferred concept activation (NG-1/NG-3 style schema/observability additions) plus hardening baseline. | Maximum functional gain and future-proofing. | Highest complexity, elevated schema and consumer compatibility risk, larger blast radius near release. | High release risk and schedule risk. | High | Very high; requires extensive regression and calibration proofs. | Hard rollback due schema and data-flow changes. | Weak fit for production-final closure timeline; conflicts with low-risk intent. | no |

## Evaluation Criteria

| CRT-ID | criterion | weight | notes |
|---|---|---|---|
| CRT-1 | Production readiness confidence | 35 | Must satisfy code+tests+config wired objective closure |
| CRT-2 | Regression risk | 25 | Prefer low blast radius near final production run |
| CRT-3 | User-request alignment | 20 | Must honor Q1-Q5 decisions and NG-4 deprioritization |
| CRT-4 | Governance traceability and rollback clarity | 10 | Must produce clean plan/tasks with explicit rollback |
| CRT-5 | Accretive value | 10 | Add meaningful benefit without architectural churn |

## Weighted Comparison

| CMP-ID | option | CRT-1 | CRT-2 | CRT-3 | CRT-4 | CRT-5 | total/100 |
|---|---|---:|---:|---:|---:|---:|---:|
| CMP-1 | OPT-1 | 33 | 22 | 20 | 10 | 7 | 92 |
| CMP-2 | OPT-2 | 27 | 16 | 17 | 8 | 9 | 77 |
| CMP-3 | OPT-3 | 18 | 10 | 12 | 6 | 10 | 56 |

## Recommendation

| REC-ID | recommended_option | rationale |
|---|---|---|
| REC-1 | OPT-1 | Best fit for production-final objective closure: highest confidence, lowest risk, and directly aligned with user's strict fully-wired completion standard. |

## Must-Hold Constraints for Election

| MHC-ID | constraint |
|---|---|
| MHC-1 | No backward compatibility path; legacy removal allowed (Q1/C1). |
| MHC-2 | Objective completion must be code+tests+config fully wired, not document-only. |
| MHC-3 | Keep scope centered on tools/puzzle-enrichment-lab; cross-module work only if mandatory. |
| MHC-4 | NG-4 taxonomy expansion remains out unless extraordinary evidence emerges. |
| MHC-5 | Plan must include rollback and documentation tasks as first-class scope. |
