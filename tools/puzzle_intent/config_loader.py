"""Load puzzle objectives from config/puzzle-objectives.json.

Provides cached loading and alias index building for matchers.
Config path follows project convention: config/ is source of truth.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

from .models import Objective, ObjectiveCategory


def _get_default_config_path() -> Path:
    """Resolve config/puzzle-objectives.json relative to project root."""
    return Path(__file__).parent.parent.parent / "config" / "puzzle-objectives.json"


@lru_cache(maxsize=1)
def load_objectives(config_path: Path | None = None) -> tuple[Objective, ...]:
    """Load objectives from config/puzzle-objectives.json.

    Returns an immutable tuple for safe caching and sharing.
    Cached after first call (same config_path).
    """
    path = config_path or _get_default_config_path()

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    objectives: list[Objective] = []
    for obj_id, obj_data in data["objectives"].items():
        objectives.append(
            Objective(
                objective_id=obj_id,
                slug=obj_data["slug"],
                name=obj_data["name"],
                category=ObjectiveCategory(obj_data["category"]),
                side=obj_data["side"],
                objective_type=obj_data["objective_type"],
                result_condition=obj_data["result_condition"],
                engine_verifiable=obj_data["engine_verifiable"],
                aliases=tuple(obj_data["aliases"]),
            )
        )

    return tuple(objectives)


def build_alias_index(objectives: tuple[Objective, ...]) -> OrderedDict[str, Objective]:
    """Build normalized alias -> Objective lookup, sorted longest-first.

    Longest aliases come first so greedy matching prefers more specific matches.
    All aliases are lowercased for case-insensitive matching.

    Returns:
        OrderedDict mapping normalized alias string -> Objective.
    """
    pairs: list[tuple[str, Objective]] = []
    for obj in objectives:
        for alias in obj.aliases:
            pairs.append((alias.lower().strip(), obj))

    # Sort longest-first for greedy matching
    pairs.sort(key=lambda p: len(p[0]), reverse=True)

    return OrderedDict(pairs)
