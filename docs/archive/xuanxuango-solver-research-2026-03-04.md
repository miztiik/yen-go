# XuanXuanGo Solver Research (2026-03-04)

## Scope

- Target page: http://www.xuanxuango.com/solver.htm
- Goal: find source code, infer algorithm used, and extract lessons for `tools/puzzle-enrichment-lab`.
- Constraint followed: no code/repo changes; research-only note created in `TODO/`.

## Executive Summary

- No public source code for XuanXuanGo's life-and-death solver was found.
- The website appears to be classic static HTML with no browser-side solver scripts; solver runs in a downloadable desktop executable.
- Algorithm details are not disclosed at implementation level. The site provides only high-level behavioral claims (fixed-area scope, boundary assumptions, heavy dependence on empty-point count, explicit handling of ko/seki outcomes).
- Their claim that GoProblems puzzles can be solved "directly" appears to mean opening SGF files as-is inside their desktop app and pressing Solve, not a public API/code integration.

## Findings Table

| Question                                    | What we found                                                                                                             | Evidence observed                                                                                                                                                         | Confidence  | What this means for puzzle-enrichment-lab                                                           |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------- |
| What code does the website use for solving? | No web solver code is exposed on `solver.htm`; page is content/docs only.                                                 | Raw HTML showed stylesheet link and page links, but no `<script src=...>` solver assets and no WASM indicators.                                                           | High        | Treat XuanXuanGo as a closed desktop engine, not a reusable web library/service.                    |
| Is source code available publicly?          | No source-code download, repo, or public implementation found for solver.                                                 | Download page links point to setup archives (`XuanXuan11_Setup.zip`, `XuanXuanOFL_Setup.zip`) that each contain only an `.exe` payload.                                   | High        | No direct code reuse path; focus on black-box benchmarking and idea extraction only.                |
| Are there related open-source components?   | Yes, but for computer-Go engine mode (GNU-Go), not necessarily their L&D solver core.                                     | `download.htm` and `um5.htm` mention GNU-Go and GPL/open-source in computer-go context.                                                                                   | High        | Do not confuse GNU-Go integration with proprietary tsumego solver internals.                        |
| What algorithm do they describe?            | High-level search/recognition framing only; no formal algorithm name disclosed (no minimax/PN-search/alpha-beta details). | `solver.htm` describes "fixed-area problems," boundary/outer-stone assumptions, exponential hardness with empty points, and outcomes (live/die/seki/double-ko/cyclic-ko). | Medium-High | Their practical recipe is domain-constrained search + outcome taxonomy + cycle/ko-aware evaluation. |
| Can it solve GoProblems puzzles directly?   | Claimed yes for SGFs in original form, within solvable scope.                                                             | `solver.htm` states GoProblems SGFs can be opened and solved directly by pressing Solve.                                                                                  | Medium-High | Good benchmark target: parse raw SGFs and solve without manual normalization where possible.        |
| What are explicit limitations?              | Not all problems; especially weak when too many empty points or boundary classification is wrong.                         | `solver.htm` gives estimated solve coverage and multiple failure modes from inner/outer misclassification.                                                                | High        | Build confidence metrics and fallback paths for low-confidence topology detection.                  |

## Inferred Algorithmic Pattern (Evidence-based, not source-confirmed)

Likely architecture from observed behavior:

1. **Region/boundary detection**: classify inner vs outer stones and determine a local search region.
2. **Constrained game-tree search**: explore tactical lines primarily inside the region; treat off-region moves as pass/irrelevant in many contexts.
3. **Outcome lattice evaluation**: rank outcomes beyond binary win/loss (unconditional life/death, ko variants, seki, etc.).
4. **Cycle-sensitive handling**: special recognition for double-ko/cyclic states and ko-context outcomes.
5. **Interactive continuation**: after initial solve, respond quickly to user variations using cached/partial analysis state.

## Practical Lessons for `tools/puzzle-enrichment-lab`

| Area                  | Lesson from XuanXuanGo                                               | Suggested application in puzzle-enrichment-lab                                                                  |
| --------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Problem framing       | Domain narrowing makes solving tractable.                            | Keep strict "local tactical puzzle" assumptions configurable and explicit in metadata.                          |
| Difficulty prediction | Empty-point count is a major runtime driver.                         | Add/strengthen features that predict solve cost from local empties/liberty topology, not only branching factor. |
| Result richness       | Users value nuanced outcomes (ko/seki classes), not just pass/fail.  | Extend result schema to preserve tactical outcome class and confidence score where available.                   |
| Reliability           | Mis-detected boundaries create false results or huge runtime spikes. | Add boundary-quality checks and a "low confidence" gate before trusting enrichment outputs.                     |
| UX for analysis       | Fast interactive re-analysis is highly useful.                       | For lab tooling, prioritize cached reruns and differential analysis for nearby position edits.                  |
| Claims vs reality     | Solvable-in-practice depends on tight scope assumptions.             | Report capability envelope clearly in docs/tests; avoid broad solve-rate claims without benchmark protocol.     |

## Proposed Benchmark Ideas (for later, no code changes here)

- Build a **black-box benchmark set** from GoProblems-like SGFs:
  - bucket by estimated empty-point count,
  - bucket by boundary clarity,
  - bucket by ko/seki complexity.
- Compare:
  - solve success rate,
  - time-to-first-solution,
  - outcome-class agreement,
  - confidence calibration.
- Add a "failure taxonomy" dashboard:
  - boundary misclassification,
  - timeout/expansion blowup,
  - ambiguous/cycle-heavy outcomes.

## Evidence Notes (research log)

- `solver.htm` contains solver claims, scope, and limitation narrative.
- `download.htm` provides installer archives; package inspection showed `.exe` payloads only for current setup zips.
- `um5.htm` open-source/GPL mentions refer to GNU-Go in computer-go feature area.
- No public repository/source link was found in scanned site pages.

## Additional Verification (requested follow-up)

### 1) Did we actually download ZIP and inspect inside?

- Yes. `XuanXuan11_Setup.zip` and `XuanXuanOFL_Setup.zip` were downloaded to temp and inspected as ZIP containers.
- Entry listing results:
  - `XuanXuan11_Setup.zip` -> single entry: `Setup.exe` (4,487,955 bytes)
  - `XuanXuanOFL_Setup.zip` -> single entry: `Setup.exe` (9,413,017 bytes)
- No `.c/.cpp/.h/.cs/.java/.py` or any source-like files were present in those archives.

### 2) Did we check GitHub directly?

- Yes, via GitHub API and profile inspection.
- `search/repositories?q=xuanxuango` returned 0 relevant search hits in the generic API search check.
- Direct account check for `xuanxuango` found exactly 1 public repo: `xuanxuango/java`.
- Repo inspection shows it is effectively empty/test-like (`aa.txt`, `bb.txt`, `cc.txt`), no solver code.

### 3) Did we try to inspect/decode the EXE?

- We extracted `Setup.exe` from ZIP successfully.
- A deeper byte-level read was blocked by local Windows security with: "file contains a virus or potentially unwanted software".
- So static string/packer fingerprinting could not be completed in this environment without changing local security policy.

### 4) Can EXE be decompiled to source code?

- **Technically:** partial reverse engineering is often possible (disassembly/decompilation), but this does **not** recover original high-level source faithfully.
- **Practically:** installer EXEs often contain packed/compiled binaries and resources; output is usually assembly or low-level pseudocode.
- **Reliability:** algorithm inference from decompiled binaries is time-consuming and uncertain, especially for optimized/native code.
- **Legal/Ethical:** may be constrained by license/EULA and jurisdiction.

## Download Page Link-Mining (follow-up)

### What was extracted directly from `download.htm`

- Absolute external URLs found in page text/markup:
  - `https://zero.sjeng.org/`
  - `http://www.miibeian.gov.cn`
- Artifact/link targets found:
  - `XuanXuan11_Setup.zip`
  - `XuanXuanOFL_Setup.zip`
  - `XuanXuan8.rar`
  - `XuanXuan7.rar`
  - `Engines.zip`
  - `ff4_ex.zip`

### Live availability check results

- Available now (HTTP 200):
  - `XuanXuan11_Setup.zip`
  - `XuanXuanOFL_Setup.zip`
  - `ff4_ex.zip`
- Not available now (HTTP 404):
  - `XuanXuan8.rar`
  - `XuanXuan7.rar`
  - `Engines.zip`
  - tested guessed historical names (`XuanXuan6.rar`, `XuanXuan5.rar`, `XuanXuan9.rar`, `XuanXuan10_Setup.zip`) also 404.

### Wayback/archive checks

- Archived snapshot exists for `download.htm` itself.
- No retrievable snapshots were found for direct binary URLs tested (`XuanXuan8.rar`, `XuanXuan7.rar`, `Engines.zip`, and setup zip direct paths) via Wayback availability/CDX checks in this session.

### Practical implication

- Mining the page text was useful and done; it currently points only to official host artifacts and one unrelated external engine site (`zero.sjeng.org`), not to SourceForge/GitHub mirrors of XuanXuanGo solver source.

## Confidence and Caveats

- Confidence is high on **"no public source visible"** and **"desktop binary distribution"**.
- Confidence is medium-high on algorithm inference because it is based on behavioral descriptions, not implementation code.
- A deeper reverse-engineering pass (outside scope here) could reveal more, but that would be a separate legal/ethical and technical exercise.
