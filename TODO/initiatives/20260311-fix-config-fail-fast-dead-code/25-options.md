# Options

**Last Updated**: 2026-03-11

## Option A: Fail-Fast Config + Dead Code Removal (Selected)

**Selection rationale**: User explicitly constrained direction — "config not existing is big failure fallback should be loud error." Only one viable approach: align with existing `ConfigLoader._load_json()` fail-fast pattern.

### Approach
- Raise `ConfigFileNotFoundError` / `ConfigurationError` on config load failure
- Remove dead TECHNIQUE_HINTS tuple[0] fallback paths
- Update `generate_yh2()` to use config for hint text

### Why no alternatives
- Silent fallback was explicitly rejected by user
- Warning-only (no raise) would still allow degraded pipeline execution
- The established pattern in the codebase (`ConfigLoader._load_json()`) already demonstrates the correct approach
