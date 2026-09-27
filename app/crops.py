"""Hover info text for ingredients, built from the stored crop data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.catalog import DATA_DIR

NO_INFO = "No info available"
SEASONS = ("Spring", "Summer", "Autumn", "Winter")


def build_crop_info(crops: list[dict]) -> dict[str, str]:
    seasons: dict[str, set[str]] = {}
    stores: dict[str, list[str]] = {}
    rare_bases: dict[str, str] = {}
    for crop in crops:
        name = crop["name"]
        seasons.setdefault(name, set()).add(crop["season"])
        crop_stores = stores.setdefault(name, [])
        for store in crop["seed_stores"]:
            if store not in crop_stores:
                crop_stores.append(store)
        if crop.get("rare_variety"):
            rare_bases[crop["rare_variety"]] = name
    season_text = {name: ", ".join(sorted(s, key=SEASONS.index)) for name, s in seasons.items()}
    info = {name: f"Season: {season_text[name]}; Purchase at {', '.join(stores[name])}" for name in seasons}
    for rare, base in rare_bases.items():
        info[rare] = f"Season: {season_text[base]}; Rare variety of {base}"
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
