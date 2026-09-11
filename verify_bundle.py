"""Verify that a packaged or development resource tree is usable."""

from __future__ import annotations

import argparse
from pathlib import Path

from utils import resource_path

REQUIRED_PATHS = (
    "config/captcha.json",
    "config/websites.json",
    "config/youtube_channels.json",
    "config/distractions.json",
    "assets/audio",
    "assets/captcha",
    "assets/icons",
)


def verify_bundle(root: Path | None = None) -> None:
    """Check that required bundled configuration and asset directories exist."""
    missing = []
    for relative_path in REQUIRED_PATHS:
        path = (root / relative_path) if root else resource_path(relative_path)
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise FileNotFoundError("Missing bundled resources:\n" + "\n".join(missing))
    print("Bundle resource verification: passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify packaged resources.")
    parser.add_argument("--root", type=Path, help="Bundle root to inspect instead of the current application root.")
    verify_bundle(parser.parse_args().root)
