# Research: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Last Updated**: 2026-03-08

---

## Research Summary

Extensive prior research was conducted in the research initiative:  
**`TODO/initiatives/2026-03-08-research-goproblems-tsumego-frame/15-research.md`**

That document contains:

- §1: KaTrain verbatim source (MIT, SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`)
- §2: Our V1 code analysis (15 bugs found)
- §3: ghostban verbatim JS from goproblems.com bundle `920.ed9fa994.js`
- §3.5: ghostban GitHub (`https://github.com/goproblems/ghostban`, MIT, v3.0.0-alpha.155)
- §4-§7: Three-way comparison, recommendations, merged algorithm design
- R-1 through R-63: Individual research findings

### Planning Confidence

| Metric                    | Value                                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| Planning Confidence Score | **100**                                                                                               |
| Risk Level                | **low**                                                                                               |
| Research invoked?         | **No** (prior research sufficient — 63 findings, verbatim MIT sources from both KaTrain and ghostban) |

### Key Research Findings for This Initiative

| ID  | Finding                                                             | Source                  | Impact                  |
| --- | ------------------------------------------------------------------- | ----------------------- | ----------------------- |
| R-1 | Attacker color is the side building the wall (not defender)         | KaTrain verbatim        | Critical bug fix        |
| R-2 | `guess_black_to_attack()` uses edge-proximity heuristic             | KaTrain                 | Core algorithm          |
| R-3 | Count-based half/half fill (not 50% checkerboard)                   | KaTrain + ghostban      | Density fix             |
| R-4 | `offence_to_win = 10` works well with small models                  | ghostban/goproblems.com | Territory balance       |
| R-5 | Border on non-board-edge sides only                                 | ghostban                | More principled framing |
| R-6 | `snap()` and `flip_stones()` normalize to TL corner                 | KaTrain                 | Normalization pipeline  |
| R-7 | Ko threats use fixed ASCII patterns near puzzle                     | KaTrain                 | Ko module               |
| R-8 | `defense_area = floor((361 - bbox_area)/2) - komi - offence_to_win` | ghostban                | Territory formula       |

### No Additional Research Needed

All trigger conditions evaluated:

- ✅ Architecture seams clear (single file replacement)
- ✅ Approach tradeoffs resolved (merged design selected)
- ✅ External precedent obtained (verbatim MIT sources)
- ✅ Quality impact understood (15 V1 bugs → specific fixes)
- ✅ Test strategy clear (acceptance criteria defined)
- ✅ Rollout simple (replace file, update callers)
