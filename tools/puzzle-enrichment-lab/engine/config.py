"""Engine configuration — paths, model, visit limits."""

import json
from pathlib import Path

from pydantic import BaseModel, Field


class EngineConfig(BaseModel):
    """Configuration for the KataGo engine."""
    katago_path: str = Field(
        default="katago",
        description="Path to KataGo binary (or just 'katago' if on PATH)"
    )
    model_path: str = Field(
        default="",
        description="Path to KataGo model .bin.gz file"
    )
    config_path: str = Field(
        default="",
        description="Path to KataGo analysis config file (optional)"
    )
    default_max_visits: int = Field(default=200, ge=1, le=100000)
    default_board_size: int = Field(default=19, ge=5, le=19)
    num_threads: int = Field(default=2, ge=1, le=64)

    @classmethod
    def from_file(cls, path: str | Path) -> "EngineConfig":
        """Load config from JSON file.

        Relative paths in the config are resolved against the config file's
        directory, so 'models-data/kata1-b15c192.bin.gz' works correctly
        regardless of the working directory.
        """
        config_path = Path(path).resolve()
        config_dir = config_path.parent

        with open(config_path) as f:
            data = json.load(f)

        # Resolve relative paths against config file directory
        for key in ("model_path", "config_path", "katago_path"):
            val = data.get(key, "")
            if val and not Path(val).is_absolute():
                resolved = config_dir / val
                # Only resolve if the file actually exists at the relative path;
                # otherwise keep as-is (e.g. 'katago' on PATH)
                if resolved.exists():
                    data[key] = str(resolved)

        return cls(**data)

    def to_file(self, path: str | Path) -> None:
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)
