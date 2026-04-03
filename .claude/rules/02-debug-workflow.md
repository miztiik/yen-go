# Debug Workflow

> This document standardizes the process of investigating bugs and issues for AI Agents.
> It enforces the `Reproduce -> Root Object Identification -> Fix -> Confirm` cycle.

---

## 1. 7-Step Debug Cycle

### Step 1: Clarify Symptoms

- **When**: After which action?
- **Where**: Which screen/panel or backend stage?
- **What**: Error log? UI breaking? Freeze?
- **Expected**: How should it have behaved?

### Step 2: Establish MRE (Minimal Reproducible Example)

Write down reproducible steps:

1. Start / Load module X
2. Input Y
3. Run command Z
4. Resulting error

### Step 3: Gather Telemetry

Request or find:

- Terminal output (Stack traces)
- Pipeline logs
- UI console errors (if Frontend)
- Input configs (e.g. specific SGFs or JSON files)

### Step 4: Candidate Causes Structuring

Organize hypotheses before jumping into code blocks:
| Hypothesis | Probability | Verification Method |
|------------|-------------|---------------------|
| UI formatting bug | High | Tweak CSS/JSX to test |
| Pipeline State Corrupt | Medium | Check runtime logs / wipe cache |
| Parsing Engine Error | Low | Test with standard SGF |

### Step 5: Fix Policy & Level Assignment

Determine Correction Level (from 01-correction-levels.md):

- Declare intent (e.g., Level 2 Fix).

### Step 6: Execute & Verify

1. Agent implements patch
2. Re-run MRE to verify resolution
3. Ensure no regressions in adjacent code

### Step 7: (Optional) Handover Memo

If the session gets too long or requires another PR review, output a `Debug Handover Memo`.

---

## 2. Handover Memo Template

Use this format when pausing debug or handing off:

```markdown
## Debug Handover - YYYY-MM-DD

### 1. Target

- Context (e.g. Backend extraction pipeline)

### 2. Status

- Expected:
- Actual:

### 3. Repro Steps

1.
2.

### 4. Candidates

- Primary:
- Secondary:

### 5. Level & Flow

- Level: LvX

### 6. Fix Attempted

- Changes tried:

### 7. Results

- Repro Status: NG / OK
- Next Steps:
```

---

## 3. Temporary Debug Logging Rules

When adding logs dynamically to debug issues:

1. **Prefix**: ALWAYS prefix with `[DEBUG]` to make it distinct from prod logs.

   ```python
   print(f"[DEBUG] graph states: {state}")
   console.log("[DEBUG] loaded SGF", sgfContent);
   ```

2. **Clean-up**: Before finalizing the code/PR, agent must self-verify (grep) all `[DEBUG]` statements are removed.
   - Run grep for `[DEBUG]`
   - Delete temporary dump prints
   - Verify tests still pass
