"""Load scraped recipe/item JSON and appliance labels."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from models import Item, Recipe

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

APPLIANCES: tuple[tuple[str, str], ...] = (
    ("pot", "Pot"),
    ("frying_pan", "Frying Pan"),
    ("oven", "Oven"),
)

APPLIANCE_IDS: tuple[str, ...] = tuple(aid for aid, _ in APPLIANCES)
APPLIANCE_NAMES: dict[str, str] = dict(APPLIANCES)

CATEGORIES: tuple[tuple[str, str], ...] = (
    ("salads", "Salads"),
    ("soups", "Soups"),
    ("sides", "Sides"),
    ("main_dishes", "Main dishes"),
    ("desserts", "Desserts"),
    ("others", "Others"),
)

CATEGORY_NAMES: dict[str, str] = dict(CATEGORIES)


class Catalog:
    def __init__(self, items: dict[str, Item], recipes: dict[str, Recipe]) -> None:
        self.items = items
        self.recipes = recipes

    def item_name(self, item_id: str) -> str:
        item = self.items.get(item_id)
        return item.name if item else item_id.replace("_", " ").title()

    def appliance_name(self, appliance_id: str | None) -> str | None:
        if not appliance_id:
            return None
        return APPLIANCE_NAMES.get(appliance_id, appliance_id.replace("_", " ").title())


def _load_catalog() -> Catalog:
    import json

    items_raw = json.loads((DATA_DIR / "items.json").read_text(encoding="utf-8"))
    recipes_raw = json.loads((DATA_DIR / "recipes.json").read_text(encoding="utf-8"))
    items = {row["id"]: Item.from_dict(row) for row in items_raw}
    recipes = {row["id"]: Recipe.from_dict(row) for row in recipes_raw}
    return Catalog(items, recipes)


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return _load_catalog()
