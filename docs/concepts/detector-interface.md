# Technique Detector Interface

**Last Updated**: 2026-03-14

## Overview

Each technique detector is a standalone class that identifies a specific Go technique from puzzle analysis data. The system supports 28 technique tags, grouped by detection frequency from high-frequency to heuristic-only.

## Protocol

All detectors implement the `TechniqueDetector` protocol:

```python
class TechniqueDetector(Protocol):
    def detect(
        self,
        position: Position,
        analysis: AnalysisResponse,
        solution_tree: SolutionNode | None,
        config: EnrichmentConfig,
    ) -> DetectionResult: ...
```

## DetectionResult

```python
@dataclass
class DetectionResult:
    detected: bool        # Was the technique found?
    confidence: float     # 0.0-1.0 confidence level
    tag_slug: str         # Matches config/tags.json slug
    evidence: str         # Human-readable explanation
```

## Adding a New Detector

1. Create a file in `analyzers/detectors/your_detector.py`
2. Define a class implementing `TechniqueDetector`
3. Add it to the `_load_detector_classes()` list in `technique_classifier.py`
4. Add tests in `tests/test_detectors_*.py`
5. The detector will be called automatically during enrichment via `get_all_detectors()`

## Detector Inventory (28 tags)

| Frequency Tier | Detectors | Test File |
|----------------|-----------|----------|
| High Frequency | life-and-death, ko, ladder, snapback | `test_detectors_high_frequency.py` |
| Common | capture-race, connection, cutting, throw-in, net | `test_detectors_common.py` |
| Intermediate | seki, nakade, double-atari, sacrifice, escape | `test_detectors_intermediate.py` |
| Lower Frequency | eye-shape, vital-point, liberty-shortage, dead-shapes, clamp | `test_detectors_lower_frequency.py` |
| Context-Dependent | living, corner, shape, endgame, tesuji, under-the-stones, connect-and-die | `test_detectors_lower_frequency.py` |
| Heuristic | joseki, fuseki | `test_detectors_lower_frequency.py` |

## Architecture Rules

- No detector may import from stages
- No detector may import from other detectors
- Detectors import from `models/` and `config` only
- Each detector is independently testable
- **No backend imports** — `TestNoBackendImports` guard enforces that the enrichment lab never imports from `backend.puzzle_manager`

> **See also**:
>
> - [Concepts: Technique Detection](technique-detection.md) — Detection architecture
> - [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md) — Thresholds
