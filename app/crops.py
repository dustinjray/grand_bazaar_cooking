"""Hover info text for ingredients, built from the stored crop data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.catalog import DATA_DIR

NO_INFO = "No info available"


def build_crop_info(crops: list[dict]) -> dict[str, str]:
    info: dict[str, str] = {}
    for crop in crops:
        season = crop["season"]
        info[crop["name"]] = f"Season: {season}; Purchase at {', '.join(crop['seed_stores'])}"
        if crop.get("rare_variety"):
            info[crop["rare_variety"]] = f"Season: {season}; Rare variety of {crop['name']}"
    return info


def crop_info_text(info: dict[str, str], name: str) -> str:
    return info.get(name, NO_INFO)


def load_crop_info(path: Path) -> dict[str, str]:
    try:
        return build_crop_info(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {}


@lru_cache(maxsize=1)
def get_crop_info() -> dict[str, str]:
    return load_crop_info(DATA_DIR / "crops.json")
