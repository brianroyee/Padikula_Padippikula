from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def application_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parent


def resource_path(relative_path: str | Path) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return application_root() / path


def load_json(relative_path: str | Path, *, default: Any = None) -> Any:
    path = resource_path(relative_path)
    try:
        with path.open("r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        LOGGER.warning("JSON file not found: %s", path)
    except (OSError, json.JSONDecodeError) as error:
        LOGGER.warning("Unable to load JSON file %s: %s", path, error)
    return default


def asset_path(relative_path: str | Path) -> Path:
    return resource_path(Path("assets") / relative_path)