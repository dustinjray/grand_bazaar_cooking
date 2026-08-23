"""Data model for Grand Bazaar cooking recipes and inventory items."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() in {"(none)", "none", "-"}:
        return None
    return stripped


@dataclass
class Item:
    """A concrete inventory item that can fill recipe slots."""

    id: str
    name: str
    family: str | None = None
    variant: str | None = None
    is_plus: bool = False
    fills: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.fills:
            self.fills = [self.id]
        else:
            self.fills = list(dict.fromkeys(self.fills))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Item:
        return cls(
            id=data["id"],
            name=data["name"],
            family=data.get("family"),
            variant=data.get("variant"),
            is_plus=bool(data.get("is_plus", False)),
            fills=list(data.get("fills") or [data["id"]]),
        )


@dataclass
class IngredientSlot:
    """One required ingredient slot on a recipe, with expanded accept list."""

    quantity: int
    accepted: list[str]
    display: str
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IngredientSlot:
        return cls(
            quantity=int(data.get("quantity", 1)),
            accepted=list(data.get("accepted") or []),
            display=data.get("display") or "",
            raw=data.get("raw") or "",
        )


@dataclass
class Recipe:
    id: str
    name: str
    category: str
    utensil: str | None
    sale_price: int | None
    meal_power: str | None
    obtain: str
    ingredients: list[IngredientSlot]
    adapt: list[str]
    source_url: str

    def __post_init__(self) -> None:
        self.utensil = _none_if_blank(self.utensil)
        self.meal_power = _none_if_blank(self.meal_power)
        self.obtain = (self.obtain or "").strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "utensil": self.utensil,
            "sale_price": self.sale_price,
            "meal_power": self.meal_power,
            "obtain": self.obtain,
            "ingredients": [slot.to_dict() for slot in self.ingredients],
            "adapt": list(self.adapt),
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Recipe:
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            utensil=data.get("utensil"),
            sale_price=data.get("sale_price"),
            meal_power=data.get("meal_power"),
            obtain=data.get("obtain") or "",
            ingredients=[IngredientSlot.from_dict(s) for s in data.get("ingredients") or []],
            adapt=list(data.get("adapt") or []),
            source_url=data.get("source_url") or "",
        )
