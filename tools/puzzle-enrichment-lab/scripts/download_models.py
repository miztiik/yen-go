"""Download KataGo models for the Puzzle Enrichment Lab.

Downloads local engine models for the KataGo subprocess.

Usage:
    python scripts/download_models.py              # Download default model (b15c192)
    python scripts/download_models.py --small      # Download smaller b10c128
"""

import argparse
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LAB_DIR = SCRIPT_DIR.parent
MODELS_DIR = LAB_DIR / "models-data"

# Ensure lab root is importable for config resolution
if str(LAB_DIR) not in sys.path:
    sys.path.insert(0, str(LAB_DIR))

from config import load_enrichment_config as _load_cfg

_cfg = _load_cfg()

# ── Model definitions ──
# Filenames from config/katago-enrichment.json (D42); URLs are download-infrastructure.

def _model_filename(label: str) -> str:
    """Resolve model filename from config label."""
    entry = getattr(_cfg.models, label, None)
    if entry is None:
        raise ValueError(f"Model label '{label}' not found in config")
    return entry.filename

MODELS = {
    "local": {
        "name": "kata1-b15c192-s1672170752-d466197061",
        "url": "https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b15c192-s1672170752-d466197061.bin.gz",
        "filename": _model_filename("benchmark"),
        "size_mb": 40,
        "description": "b15c192 (~40MB, ~12200 Elo) — Good for most tsumego",
    },
    "local-small": {
        "name": "kata1-b10c128-s1141046784-d204142634",
        "url": "https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b10c128-s1141046784-d204142634.bin.gz",
        "filename": _model_filename("test_fast"),
        "size_mb": 15,
        "description": "b10c128 (~15MB, ~11500 Elo) — Lighter local option",
    },
}


def download_file(url: str, dest: Path, description: str, size_mb: int) -> bool:
    """Download a file with progress display."""
    if dest.exists():
        existing_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  Already exists: {dest.name} ({existing_mb:.1f} MB)")
        return True

    print(f"  Downloading {description}...")
    print(f"  URL: {url}")
    print(f"  Destination: {dest}")
    print(f"  Expected size: ~{size_mb} MB")
    print()

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://katagotraining.org/networks/",
        })

        with urllib.request.urlopen(req) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            block_size = 65536
            downloaded = 0

            with open(str(dest), "wb") as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = min(downloaded / total_size * 100, 100)
                        mb = downloaded / (1024 * 1024)
                        sys.stdout.write(f"\r  Progress: {mb:.1f} MB ({pct:.0f}%)")
                        sys.stdout.flush()

        print()  # Newline after progress

        actual_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  Done: {dest.name} ({actual_mb:.1f} MB)")
        return True

    except Exception as e:
        print(f"\n  ERROR: Automatic download failed: {e}")
        if dest.exists():
            dest.unlink()
        print()
        print("  +----------------------------------------------------------")
        print("  | MANUAL DOWNLOAD REQUIRED")
        print("  |")
        print("  | The server blocked programmatic access. Please:")
        print("  | 1. Open this URL in your browser:")
        print(f"  |    {url}")
        print("  | 2. Save the file to:")
        print(f"  |    {dest}")
        print("  |")
        print("  | Or visit https://katagotraining.org/networks/")
        print(f"  | and download a model with architecture: {description.split('(')[0].strip()}")
        print("  +----------------------------------------------------------")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download KataGo models")
    parser.add_argument("--small", action="store_true", help="Use smaller b10c128 model")
    args = parser.parse_args()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Puzzle Enrichment Lab — Model Downloader")
    print("=" * 60)
    print(f"Models directory: {MODELS_DIR}")
    print()

    model_key = "local-small" if args.small else "local"
    model = MODELS[model_key]
    print(f"Downloading: {model['description']}")
    dest = MODELS_DIR / model["filename"]
    success = download_file(model["url"], dest, model["name"], model["size_mb"])
    print()

    # Auto-update config.json if it exists (use relative path)
    config_path = LAB_DIR / "config.json"
    if config_path.exists():
        import json
        with open(config_path) as f:
            config = json.load(f)
        config["model_path"] = f"models-data/{model['filename']}"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"  Updated config.json model_path -> models-data/{model['filename']}")
    print()

    print("=" * 60)
    if success:
        print("Download complete!")
        print()
        print("Next steps:")
        print("  1. Ensure KataGo is installed: katago --version")
        print("  2. Copy config.example.json -> config.json (if not done)")
        print("  3. Set katago_path and model_path in config.json")
        print("  4. Run: python cli.py enrich --sgf <puzzle.sgf> ...")
    else:
        print("Download failed. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
