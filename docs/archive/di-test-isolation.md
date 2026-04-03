> ⚠️ **ARCHIVED** — This document describes a dependency-injection approach to test isolation
> (spec 044) that was reverted as over-engineered. The simpler `YENGO_RUNTIME_DIR` environment
> variable approach replaced it. Kept for historical reference only.

---

# Dependency Injection for Test Isolation (Failed Experiment)

## The Problem

Tests were accidentally writing files to `yengo-puzzle-collections/` (the production output directory), leaving 98 untracked files after test runs. Test isolation required a way to redirect output paths to temporary directories.

## What Was Tried

Spec 044 proposed replacing all global path functions (`get_output_dir()`, `get_pm_staging_dir()`) with mandatory constructor injection:

- Every class that writes files must receive its output paths via constructor
- No default paths — only the CLI entry point resolves production paths
- A `RuntimePaths` class encapsulated all directory paths as a single injectable dependency
- Tests would pass `tmp_path`-based `RuntimePaths` to every component

## Why It Failed

- **Viral API changes**: Every function and class in the call chain needed a `RuntimePaths` parameter, creating massive signature churn across dozens of files
- **Over-engineered**: The real problem was "tests write to the wrong directory." DI solved it by restructuring the entire codebase — a disproportionate response
- **Test friction**: Every test needed to construct a `RuntimePaths` object even when it didn't use file I/O

## What Replaced It

Spec 046 reverted the DI changes and introduced:

1. **`YENGO_RUNTIME_DIR` environment variable** — Set in test fixtures to redirect all runtime output to a temporary directory
2. **`.pm-runtime/` directory convention** — All runtime artifacts (staging, state, logs) live under a single root that can be pointed anywhere via the env var
3. **`paths.py` module** — Centralized path resolution that checks `YENGO_RUNTIME_DIR` first, falls back to `.pm-runtime/` at the project root

The `RuntimePaths` class was deleted. Path resolution is now in `backend/puzzle_manager/paths.py` with a `reset_path_cache()` function for test cleanup.

## Lesson

When tests have side effects, fix the side effects at the boundary (environment variable + path resolution) rather than restructuring internal APIs. The fix should be proportional to the problem.
