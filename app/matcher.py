"""Recipe feasibility and cook-allocation checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.catalog import APPLIANCE_NAMES
from models import Recipe

MAX_COOK_CAP = 99


class CookError(ValueError):
    """User-facing cook validation failure."""


@dataclass
class MissingSlot:
    display: str
    raw: str
    quantity: int


@dataclass
class RecipeStatus:
    cookable: bool
    max_cookable: int
    missing_slots: list[MissingSlot] = field(default_factory=list)
    missing_utensil: str | None = None


def _inventory_copy(inventory: dict[str, int]) -> dict[str, int]:
    return {k: int(v) for k, v in inventory.items() if int(v) > 0}


def _sorted_slots(recipe: Recipe) -> list[tuple[int, object]]:
    indexed = list(enumerate(recipe.ingredients))
    indexed.sort(key=lambda pair: (len(pair[1].accepted), pair[1].quantity, pair[0]))
    return indexed


def utensil_owned(recipe: Recipe, appliances: dict[str, bool]) -> bool:
    if not recipe.utensil:
        return True
    return bool(appliances.get(recipe.utensil))


def _fill_need(remaining: dict[str, int], accepted: list[str], need: int) -> int:
    for item_id in accepted:
        have = remaining.get(item_id, 0)
        if have <= 0:
            continue
        take = min(need, have)
        remaining[item_id] = have - take
        need -= take
        if need == 0:
            break
    return need


def can_cook_n(
    recipe: Recipe,
    inventory: dict[str, int],
    appliances: dict[str, bool],
    n: int,
) -> bool:
    if n <= 0:
        return True
    if not utensil_owned(recipe, appliances):
        return False
    remaining = _inventory_copy(inventory)
    for _, slot in _sorted_slots(recipe):
        leftover = _fill_need(remaining, slot.accepted, slot.quantity * n)
        if leftover > 0:
            return False
    return True


def missing_for_one(
    recipe: Recipe,
    inventory: dict[str, int],
    appliances: dict[str, bool],
) -> tuple[list[MissingSlot], str | None]:
    missing_utensil = None if utensil_owned(recipe, appliances) else recipe.utensil
    missing: list[tuple[int, MissingSlot]] = []
    remaining = _inventory_copy(inventory)
    for index, slot in _sorted_slots(recipe):
        leftover = _fill_need(remaining, slot.accepted, slot.quantity)
        if leftover > 0:
            missing.append(
                (index, MissingSlot(display=slot.display, raw=slot.raw, quantity=leftover))
            )
    missing.sort(key=lambda pair: pair[0])
    return [slot for _, slot in missing], missing_utensil


def max_cookable(
    recipe: Recipe,
    inventory: dict[str, int],
    appliances: dict[str, bool],
) -> int:
    if not utensil_owned(recipe, appliances):
        return 0
    if not recipe.ingredients:
        return MAX_COOK_CAP
    lo, hi = 1, MAX_COOK_CAP
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if can_cook_n(recipe, inventory, appliances, mid):
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def evaluate(
    recipe: Recipe,
    inventory: dict[str, int],
    appliances: dict[str, bool],
) -> RecipeStatus:
    missing_slots, missing_utensil = missing_for_one(recipe, inventory, appliances)
    n = max_cookable(recipe, inventory, appliances)
    return RecipeStatus(
        cookable=n >= 1,
        max_cookable=n,
        missing_slots=missing_slots,
        missing_utensil=missing_utensil,
    )


def plan_cook(
    recipe: Recipe,
    inventory: dict[str, int],
    appliances: dict[str, bool],
    allocations: list[dict[str, int]],
    cook_count: int,
    catalog_item_ids: set[str],
) -> dict[str, int]:
    """Return a new sparse inventory after cooking. Raises CookError on failure."""
    if cook_count < 1:
        raise CookError("Cook at least one dish.")
    if not utensil_owned(recipe, appliances):
        name = APPLIANCE_NAMES.get(recipe.utensil, recipe.utensil.replace("_", " "))
        raise CookError(f"You need a {name} to cook this.")
    if len(allocations) != len(recipe.ingredients):
        raise CookError("Choose ingredients for every slot.")

    new_inv = {k: int(v) for k, v in inventory.items()}
    for slot, alloc in zip(recipe.ingredients, allocations):
        need = slot.quantity * cook_count
        used = 0
        accepted = set(slot.accepted)
        for item_id, qty in alloc.items():
            qty = int(qty)
            if qty < 0:
                raise CookError("Quantities cannot be negative.")
            if qty == 0:
                continue
            if item_id not in accepted:
                raise CookError(f"{item_id} cannot fill {slot.display}.")
            have = new_inv.get(item_id, 0)
            if qty > have:
                raise CookError("Not enough of a chosen ingredient.")
            new_inv[item_id] = have - qty
            used += qty
        if used != need:
            raise CookError(
                f"{slot.display} needs {need} item(s); assigned {used}."
            )

    if recipe.id in catalog_item_ids:
        new_inv[recipe.id] = new_inv.get(recipe.id, 0) + cook_count
    return new_inv
