# Options — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-10

## Context

This initiative consolidates all pending enrichment-lab work. The scope is approved (charter G1-G10). The primary architectural decision is the **execution strategy** — how to sequence and integrate 10 goals spanning new algorithms, fixes, governance reviews, docs, and cleanup.

## Option Comparison

### OPT-1: Algorithm-First Depth Sequence

**Approach:** Execute in strict dependency order: new algorithms (Benson + interior-point) → fixes (ko, logging, dead code) → individual reviews (KM + remediation) → sgfmill replacement → documentation.

| Dimension | Assessment |
|-----------|-----------|
| **Benefits** | Highest-value work (Benson gate) done first. Each phase builds on stable foundation. Reviews happen after all code is stable. sgfmill replacement is last, so it can be dropped if time pressure. |
| **Drawbacks** | Docs are last — knowledge capture delayed. Reviews delayed (26 individual reviews happen after all code changes, risk of review fatigue). |
| **Risks** | Benson gate implementation may surface unexpected issues that force fixes rework. Reviews at end may find gaps requiring code changes in already-"complete" phases. |
| **Complexity** | Medium — straightforward linear sequence. |
| **Test impact** | New tests per phase. Existing 220+ tests maintained throughout. |
| **Rollback** | Phase-granular — each phase is independently revertible. |
| **Architecture compliance** | ✅ Follows dependency inversion (Benson as pre-query gate). |

### OPT-2: Fix-First Breadth Sequence

**Approach:** Close all existing gaps first (perspective fixes, ko fix, dead code, logging) → then governance reviews (KM + remediation) → then new algorithms (Benson + interior-point) → sgfmill → docs throughout.

| Dimension | Assessment |
|-----------|-----------|
| **Benefits** | Cleans up technical debt before adding new features. Governance reviews happen on a fully-stable codebase. Docs written alongside each phase (not deferred). |
| **Drawbacks** | High-value algorithmic work (Benson) is delayed. If initiative runs out of budget, the most impactful items are the ones unfinished. |
| **Risks** | Low — fixes are all small (1-20 lines each). Reviews on stable code reduce review fatigue. |
| **Complexity** | Low — fixes are well-defined with specific line targets. |
| **Test impact** | Same test maintenance pattern. |
| **Rollback** | Phase-granular. |
| **Architecture compliance** | ✅ Clean foundation before new features. |

### OPT-3: Interleaved Priority Sequence (Recommended)

**Approach:** Execute in priority-weighted interleaved order:
1. **Phase A (Foundation)**: Close 5 perspective gaps + ko capture verification + dead code removal (small, well-defined, stabilizes codebase)
2. **Phase B (Algorithms)**: Benson gate + interior-point exit (highest impact new work)
3. **Phase C (Reviews)**: 6 KM gate reviews + 20 remediation sign-offs (individual, on fully stable code)
4. **Phase D (Replacement)**: sgfmill evaluation and conditional replacement
5. **Phase E (Documentation)**: All doc deliverables + global doc updates (written last when all code is final, but doc STUBS created in Phase A)

| Dimension | Assessment |
|-----------|-----------|
| **Benefits** | Fixes first ensure stable integration baseline for Benson gate. New algorithms come before reviews (so reviews cover the full codebase state). sgfmill is appropriately last. Doc stubs in Phase A prevent knowledge loss. |
| **Drawbacks** | More complex sequencing than pure linear. |
| **Risks** | Low — each phase is 5-15 tasks, well-bounded. |
| **Complexity** | Medium — interleaving adds coordination overhead but each phase is self-contained. |
| **Test impact** | New tests in Phases A and B. Review tasks in Phase C may identify gaps requiring additional tests. |
| **Rollback** | Phase-granular. Phases A-E are independently revertible. |
| **Architecture compliance** | ✅ Clean foundation → new algorithms → verification → documentation. Follows the project's "Red-Green-Refactor" principle. |

## Tradeoff Matrix

| OPT-ID | title | time-to-value | risk | review quality | doc quality | rollback |
|--------|-------|---------------|------|----------------|-------------|----------|
| OPT-1 | Algorithm-First | Fast (Benson first) | Medium (reviews find late gaps) | Lower (fatigued, all at end) | Lower (docs last) | Phase-granular |
| OPT-2 | Fix-First | Slow (Benson last) | Low | Higher (stable base) | Higher (throughout) | Phase-granular |
| OPT-3 | Interleaved Priority | Balanced | Low | Highest (reviews on full code) | High (stubs early, full at end) | Phase-granular |

## Recommendation

**OPT-3 (Interleaved Priority)** — fixes first to stabilize, then high-value algorithms, then reviews on the complete codebase, then sgfmill, then final documentation. This ensures:
1. Reviews cover ALL changes (fixes + algorithms), not just legacy code
2. Benson gate integrates into a clean codebase
3. sgfmill replacement can be dropped without affecting core goals
4. Documentation captures the final state, not an intermediate one
