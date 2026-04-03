# Tasks

**Last Updated**: 2026-03-12

| id | task | depends_on | parallel | status |
|----|------|------------|----------|--------|
| T1 | Replace `_bfs_fill()` skip logic: connectivity-preserving BFS with counter-based eye holes, Manhattan≤1 near-boundary | — | — | completed |
| T2 | Remove multi-seed fallback in `fill_territory()` | T1 | — | completed |
| T3 | Update test assertions: density threshold, eye guard test, score balance test | T1,T2 | — | completed |
| T4 | Run test suite: `pytest tests/test_tsumego_frame.py` — 87 passed, 0 failed | T3 | — | completed |
| T5 | Visual verification with `probe_frame.py` — 5/5 clean connected regions | T4 | — | completed |
| T6 | Verify metrics: frame components=1/color (18/18), eyes in range (18/18), density improved but above target | T4 | — | completed |
