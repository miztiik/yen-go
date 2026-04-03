# Options — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22

## Option A: Delete Sprint Files (REJECTED)

**Description:** Delete all 5 `test_sprint[1-5]_fixes.py` files outright, relying on `test_remediation_sprints.py` for coverage.

| Dimension | Assessment |
|-----------|------------|
| Coverage Risk | **CRITICAL** — Sprint files test 72 unique functions with gap IDs (P0.x/G.x) that are completely absent from the remediation file. Deleting would destroy 72 tests with zero backup. |
| Effort | Trivial (5 file deletions) |
| Maintenance | Short term: reduced file count. Long term: lost regression safety. |

**Verdict:** REJECTED by CR-ALPHA (6 critical findings). The initial premise was factually incorrect.

---

## Option B: Migrate Sprint Tests to Domain Files (SELECTED)

**Description:** Move each test class from sprint files into its natural domain test file, preserving docstrings and gap IDs. Then delete the empty sprint files 5 atomic commits.

| Dimension | Assessment |
|-----------|------------|
| Coverage Risk | **NONE** — tests are relocated, not deleted |
| Effort | Medium (18 class moves across 13 target files, 5 commits) |
| Maintenance | Domain-organized tests are easier to discover and maintain |
| Naming | Sprint-process names eliminated; tests live where they logically belong |

**Lane ordering:** L2 (trivial rename) → L3 (sys.path cleanup) → L1 (migration) → L4 (perf helpers)

**Verdict:** SELECTED — approved by both CR-ALPHA and CR-BETA with conditions (docstring preservation, zero assertion changes).

---

## Option C: Rename Sprint Files by Domain (Considered)

**Description:** Keep sprint files intact but rename them by domain (e.g., `test_sprint1_fixes.py` → `test_coordinate_conversion_regression.py`).

| Dimension | Assessment |
|-----------|------------|
| Coverage Risk | **NONE** — files unchanged |
| Effort | Low (5 renames) |
| Maintenance | Better naming but files remain single-concern — some test classes in a sprint file don't share a domain |
| Problem | Sprint1 has 6 test classes across 4 different domains — no single domain name fits |

**Verdict:** REJECTED — doesn't solve the multi-domain problem. Sprint1 alone tests: tree validation, throw-in detection, difficulty weights, YX fields, model rename, and engine comparison. No single domain name fits.

---

## Option Election

| Option | Votes (CR-A / CR-B / GV Panel) | Selected |
|--------|---------------------------------|----------|
| A: Delete | REJECTED / REJECTED / — | No |
| B: Migrate to domain | APPROVED / APPROVED / APPROVED (with RCs) | **YES** |
| C: Rename files | — / — / Not evaluated | No |

**Selected: OPT-B** — Migrate sprint test classes to domain files with atomic commits, docstring preservation, and zero assertion changes.
