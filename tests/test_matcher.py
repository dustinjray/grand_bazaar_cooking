"""Matcher and cook-allocation tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.catalog import DATA_DIR, get_catalog
from app.db import connect, get_appliances, get_inventory, set_appliance, set_count, apply_inventory
from app.main import recipe_uses_items, sort_recipe_rows
from app.matcher import CookError, MissingSlot, RecipeStatus, evaluate, plan_cook
from models import IngredientSlot, Recipe


def _recipe(**kwargs) -> Recipe:
    defaults = {
        "id": "test_dish",
        "name": "Test Dish",
        "category": "salads",
        "utensil": None,
        "sale_price": 10,
        "meal_power": None,
        "obtain": "",
        "ingredients": [],
        "adapt": [],
        "source_url": "",
    }
    defaults.update(kwargs)
    return Recipe(**defaults)


class HerbSaladTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recipe = get_catalog().recipes["herb_salad"]

    def test_one_mint_and_one_lavender_can_cook(self) -> None:
        status = evaluate(self.recipe, {"mint": 1, "lavender": 1}, {})
        self.assertTrue(status.cookable)
        self.assertEqual(status.max_cookable, 1)
        self.assertEqual(status.missing_slots, [])
        self.assertIsNone(status.missing_utensil)

    def test_one_mint_cannot_cook(self) -> None:
        status = evaluate(self.recipe, {"mint": 1}, {})
        self.assertFalse(status.cookable)
        self.assertEqual(status.max_cookable, 0)
        self.assertEqual(len(status.missing_slots), 1)
        self.assertEqual(status.missing_slots[0].quantity, 1)

    def test_mixed_allocation_consumes_both_herbs(self) -> None:
        new_inv = plan_cook(
            self.recipe,
            {"mint": 1, "lavender": 1, "chamomile": 4},
            {},
            [{"mint": 1, "lavender": 1}],
            1,
            set(),
        )
        self.assertEqual(new_inv["mint"], 0)
        self.assertEqual(new_inv["lavender"], 0)
        self.assertEqual(new_inv["chamomile"], 4)


class ApplianceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recipe = get_catalog().recipes["asparagus_soup"]
        self.inventory = {"asparagus": 1, "milk": 1, "oil": 1, "onion": 1}

    def test_unowned_pot_blocks_cook(self) -> None:
        status = evaluate(self.recipe, self.inventory, {"pot": False})
        self.assertFalse(status.cookable)
        self.assertEqual(status.missing_utensil, "pot")
        with self.assertRaises(CookError):
            plan_cook(
                self.recipe,
                self.inventory,
                {"pot": False},
                [{"asparagus": 1}, {"milk": 1}, {"oil": 1}, {"onion": 1}],
                1,
                set(),
            )

    def test_owned_pot_allows_cook_and_is_not_consumed(self) -> None:
        status = evaluate(self.recipe, self.inventory, {"pot": True})
        self.assertTrue(status.cookable)
        plan_cook(
            self.recipe,
            self.inventory,
            {"pot": True},
            [{"asparagus": 1}, {"milk": 1}, {"oil": 1}, {"onion": 1}],
            1,
            set(),
        )
        self.assertTrue(status.cookable)


class AllocationTests(unittest.TestCase):
    def test_over_allocation_across_shared_items_rejected(self) -> None:
        recipe = _recipe(
            ingredients=[
                IngredientSlot(1, ["egg"], "Egg", "egg"),
                IngredientSlot(1, ["egg", "egg_plus"], "Any Egg", "egg"),
            ]
        )
        with self.assertRaises(CookError):
            plan_cook(
                recipe,
                {"egg": 1, "egg_plus": 0},
                {},
                [{"egg": 1}, {"egg": 1}],
                1,
                set(),
            )

    def test_specific_then_plus_is_valid(self) -> None:
        recipe = _recipe(
            ingredients=[
                IngredientSlot(1, ["egg"], "Egg", "egg"),
                IngredientSlot(1, ["egg", "egg_plus"], "Any Egg", "egg"),
            ]
        )
        new_inv = plan_cook(
            recipe,
            {"egg": 1, "egg_plus": 1},
            {},
            [{"egg": 1}, {"egg_plus": 1}],
            1,
            set(),
        )
        self.assertEqual(new_inv["egg"], 0)
        self.assertEqual(new_inv["egg_plus"], 0)

    def test_wrong_item_for_slot_rejected(self) -> None:
        recipe = _recipe(
            ingredients=[IngredientSlot(1, ["cheese_plus"], "Cheese+", "cheese+")]
        )
        with self.assertRaises(CookError):
            plan_cook(recipe, {"cheese": 2, "cheese_plus": 0}, {}, [{"cheese": 1}], 1, set())

    def test_short_assignment_rejected(self) -> None:
        recipe = get_catalog().recipes["herb_salad"]
        with self.assertRaises(CookError):
            plan_cook(recipe, {"mint": 2}, {}, [{"mint": 1}], 1, set())


class ProducedDishTests(unittest.TestCase):
    def test_omelet_added_when_recipe_is_an_item(self) -> None:
        catalog = get_catalog()
        recipe = catalog.recipes["omelet"]
        new_inv = plan_cook(
            recipe,
            {"egg": 1, "butter": 1},
            {},
            [{"egg": 1}, {"butter": 1}],
            1,
            set(catalog.items),
        )
        self.assertEqual(new_inv["egg"], 0)
        self.assertEqual(new_inv["butter"], 0)
        self.assertEqual(new_inv["omelet"], 1)

    def test_two_omelets_use_two_each(self) -> None:
        catalog = get_catalog()
        recipe = catalog.recipes["omelet"]
        new_inv = plan_cook(
            recipe,
            {"egg": 2, "butter": 2},
            {},
            [{"egg": 2}, {"butter": 2}],
            2,
            set(catalog.items),
        )
        self.assertEqual(new_inv["omelet"], 2)


class RareCropTests(unittest.TestCase):
    def test_giant_pumpkin_fills_pumpkin_slot(self) -> None:
        catalog = get_catalog()
        pumpkin = catalog.items["giant_pumpkin"]
        self.assertIn("pumpkin", pumpkin.fills)
        self.assertIn("vegetable_a", pumpkin.fills)
        recipe = catalog.recipes["pumpkin_soup"]
        self.assertIn("giant_pumpkin", recipe.ingredients[0].accepted)
        status = evaluate(
            recipe,
            {"giant_pumpkin": 1, "milk": 1, "onion": 1},
            {"pot": True},
        )
        self.assertTrue(status.cookable)

    def test_calabash_radish_fills_radish_slot(self) -> None:
        catalog = get_catalog()
        self.assertIn("radish", catalog.items["calabash_radish"].fills)
        recipe = catalog.recipes["radish_soup"]
        self.assertIn("calabash_radish", recipe.ingredients[0].accepted)
        status = evaluate(recipe, {"calabash_radish": 1, "milk": 1, "salt": 1}, {})
        self.assertTrue(status.cookable)

    def test_regular_pumpkin_cannot_fill_giant_only_slot(self) -> None:
        recipe = _recipe(
            ingredients=[
                IngredientSlot(1, ["giant_pumpkin"], "Giant Pumpkin", "Giant Pumpkin")
            ]
        )
        status = evaluate(recipe, {"pumpkin": 1}, {})
        self.assertFalse(status.cookable)
        status = evaluate(recipe, {"giant_pumpkin": 1}, {})
        self.assertTrue(status.cookable)


class StoreTests(unittest.TestCase):
    def test_appliances_persist_and_inventory_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.db"
            conn = connect(path)
            self.assertFalse(get_appliances(conn)["pot"])
            set_appliance(conn, "pot", True)
            set_count(conn, "mint", 2)
            conn.close()

            conn = connect(path)
            self.assertTrue(get_appliances(conn)["pot"])
            self.assertEqual(get_inventory(conn)["mint"], 2)
            apply_inventory(conn, {"mint": 0, "lavender": 1})
            conn.close()

            conn = connect(path)
            self.assertTrue(get_appliances(conn)["pot"])
            self.assertEqual(get_inventory(conn).get("mint", 0), 0)
            self.assertEqual(get_inventory(conn)["lavender"], 1)
            conn.close()


class RecipeSortTests(unittest.TestCase):
    def _row(self, name: str, price: int | None, missing: int) -> dict:
        recipe = _recipe(id=name.lower().replace(" ", "_"), name=name, sale_price=price)
        slots = [MissingSlot("X", "x", missing)] if missing else []
        status = RecipeStatus(
            cookable=missing == 0,
            max_cookable=1 if missing == 0 else 0,
            missing_slots=slots,
        )
        return {"recipe": recipe, "status": status}

    def test_name_a_to_z(self) -> None:
        rows = [self._row("Zucchini Soup", 10, 0), self._row("Apple Pie", 50, 1)]
        names = [row["recipe"].name for row in sort_recipe_rows(rows, "name")]
        self.assertEqual(names, ["Apple Pie", "Zucchini Soup"])

    def test_price_high_to_low(self) -> None:
        rows = [
            self._row("Cheap", 10, 0),
            self._row("Unknown", None, 0),
            self._row("Pricey", 500, 2),
        ]
        names = [row["recipe"].name for row in sort_recipe_rows(rows, "price")]
        self.assertEqual(names, ["Pricey", "Cheap", "Unknown"])

    def test_missing_then_price_descending(self) -> None:
        rows = [
            self._row("Two Low", 100, 2),
            self._row("Two High", 400, 2),
            self._row("One Miss", 50, 1),
            self._row("Ready Cheap", 20, 0),
            self._row("Ready Pricey", 300, 0),
        ]
        names = [row["recipe"].name for row in sort_recipe_rows(rows, "missing")]
        self.assertEqual(
            names,
            ["Ready Pricey", "Ready Cheap", "One Miss", "Two High", "Two Low"],
        )

    def test_unknown_sort_falls_back_to_name(self) -> None:
        rows = [self._row("Beta", 1, 0), self._row("Alpha", 9, 0)]
        names = [row["recipe"].name for row in sort_recipe_rows(rows, "nope")]
        self.assertEqual(names, ["Alpha", "Beta"])


class UseSoonTests(unittest.TestCase):
    def test_pumpkin_soup_matches_pumpkin_variants_not_mint(self) -> None:
        soup = get_catalog().recipes["pumpkin_soup"]
        self.assertTrue(recipe_uses_items(soup, {"pumpkin"}))
        self.assertTrue(recipe_uses_items(soup, {"giant_pumpkin"}))
        self.assertFalse(recipe_uses_items(soup, {"mint"}))

    def test_herb_salad_matches_mint_even_with_extra_picks(self) -> None:
        salad = get_catalog().recipes["herb_salad"]
        self.assertTrue(recipe_uses_items(salad, {"mint"}))
        self.assertTrue(recipe_uses_items(salad, {"mint", "pumpkin"}))
        self.assertFalse(recipe_uses_items(salad, {"pumpkin"}))

    def test_empty_selection_does_not_match(self) -> None:
        soup = get_catalog().recipes["pumpkin_soup"]
        self.assertFalse(recipe_uses_items(soup, set()))


LETTER_GROUP_DISPLAYS = {
    "Fish A",
    "Fish B",
    "Fish C",
    "Fish D",
    "Fish E",
    "Vegetable A",
    "Vegetable B",
    "Vegetable C",
    "Vegetable D",
    "Vegetable E",
    "Fruit A",
    "Fruit B",
}

# Wiki letter-group assignments (GameRant / ranchstory).
EXPECTED_LETTER_SLOTS = {
    "mixed_salad": ["Vegetable A"],
    "fish_chips": ["Fish A"],
    "shumai_dumplings": ["Fish B"],
    "sashimi": ["Fish C"],
    "fish_cake": ["Fish C"],
    "stew": ["Vegetable B"],
    "hot_pot": ["Fish D"],
    "ukha": ["Fish D"],
    "marinated_fish": ["Fish D"],
    "spahgetti_soup": ["Fish E"],
    "carpaccio": ["Fish A"],
    "cheese_fondue": ["Vegetable C"],
    "spicy_curry": ["Vegetable D"],
    "seaweed_curry": ["Vegetable D"],
    "milk_curry": ["Vegetable D"],
    "burgundy_fondue": ["Vegetable C"],
    "tempura": ["Vegetable E"],
    "paella": ["Fish E"],
    "meuniere_fish": ["Fish E"],
    "pink_fondue": ["Vegetable C"],
    "curry_rice": ["Vegetable D"],
    "vegetable_curry": ["Vegetable A"],
    "bouillabaisse": ["Fish E"],
    "tomato_fondue": ["Vegetable C"],
    "fruit_sandwich": ["Fruit A", "Fruit A"],
    "simmered_fish": ["Fish B"],
    "grilled_fish": ["Fish C"],
    "trifle": ["Fruit A"],
    "fruit_dumplings": ["Fruit A", "Fruit A"],
    "chocolate_fondue": ["Fruit B"],
    "happy_fruit_platter": ["Fruit A", "Fruit B"],
    "happy_chef_salad": ["Vegetable A"],
}


class LetterGroupSlotTests(unittest.TestCase):
    FISH_A = {
        "yellow_perch",
        "snakehead",
        "masu_trout",
        "char",
        "salmon",
        "icefish",
        "cherry_salmon",
    }

    def test_fish_chips_is_fish_a(self) -> None:
        slot = get_catalog().recipes["fish_chips"].ingredients[0]
        self.assertEqual(slot.display, "Fish A")
        self.assertEqual(set(slot.accepted), self.FISH_A)
        self.assertNotIn("dace", slot.accepted)

    def test_happy_fruit_platter_fruit_a_then_fruit_b(self) -> None:
        fruits = [
            slot
            for slot in get_catalog().recipes["happy_fruit_platter"].ingredients
            if slot.display in {"Fruit A", "Fruit B"}
        ]
        self.assertEqual([slot.display for slot in fruits], ["Fruit A", "Fruit B"])
        self.assertIn("cherry", fruits[0].accepted)
        self.assertNotIn("apple", fruits[0].accepted)
        self.assertIn("apple", fruits[1].accepted)
        self.assertNotIn("cherry", fruits[1].accepted)

    def test_recipe_override_keys_match_recipe_ids(self) -> None:
        groups = json.loads((DATA_DIR / "groups.json").read_text(encoding="utf-8"))
        recipes = get_catalog().recipes
        missing = sorted(
            key for key in groups["recipe_overrides"] if key not in recipes
        )
        self.assertEqual(missing, [])

    def test_letter_group_displays_match_wiki(self) -> None:
        catalog = get_catalog()
        for recipe_id, expected in EXPECTED_LETTER_SLOTS.items():
            with self.subTest(recipe_id):
                displays = [
                    slot.display
                    for slot in catalog.recipes[recipe_id].ingredients
                    if slot.display in LETTER_GROUP_DISPLAYS
                ]
                self.assertEqual(displays, expected)


if __name__ == "__main__":
    unittest.main()
