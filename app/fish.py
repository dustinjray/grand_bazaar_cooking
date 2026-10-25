"""Hover info text for fish ingredients, built from the stored fish data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.catalog import DATA_DIR

KEEP_WEATHER = {"all weather": "All weather", "any weather": "Any weather"}


def _format_seasons(seasons: list[str]) -> str:
    if any(value.lower().startswith("all season") for value in seasons):
        return "All seasons"
    return ", ".join(seasons)


def _format_weather_token(token: str) -> str:
    key = token.lower()
    kept = KEEP_WEATHER.get(key)
    if kept:
        return kept
    if key.endswith(" weather"):
        token = token[: -len(" weather")].strip()
    return token


def _format_weather(weather: list[str]) -> str:
    tokens = [_format_weather_token(item) for item in weather]
    text = ", ".join(tokens)
    parts = text.split(" ", 1)
    if len(parts) == 1:
        return text
    return f"{parts[0]} {parts[1].lower()}"


def format_fish_info(fish: dict) -> str:
    parts = [
        f"Seasons: {_format_seasons(fish['seasons'])}",
        f"Weather: {_format_weather(fish['weather'])}",
        f"Locations: {', '.join(fish['locations'])}",
    ]
    if fish.get("time"):
        parts.append(f"Time: {fish['time']}")
    parts.append(f"Rod: {fish['rod']}")
    return "; ".join(parts)


def build_fish_info(fish_rows: list[dict]) -> dict[str, str]:
    return {row["name"]: format_fish_info(row) for row in fish_rows}


def fish_info_text(info: dict[str, str], name: str) -> str:
    return info.get(name, "No info available")


def load_fish_info(path: Path) -> dict[str, str]:
    try:
        return build_fish_info(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {}


@lru_cache(maxsize=1)
def get_fish_info() -> dict[str, str]:
    return load_fish_info(DATA_DIR / "fish.json")
