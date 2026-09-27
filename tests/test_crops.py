"""Spring crop scraping and stored crop data tests."""

from __future__ import annotations

import json
import unittest

from app.catalog import DATA_DIR
from scrape_crops import parse_crop_page, parse_rare_variety, parse_seed_stores

SAMPLE_PAGE = """
<table class="data">
<tr><th>Name</th><th>Growth</th><th>Crops per<br>Harvest</th><th>Sell Price</th></tr>
<tr><td rowspan="2">
    <img src="crop_turnip.webp" alt="" title="Turnip">
    <p><b>Turnip</b></p>
    <img src="crop_turnip_giant.webp" alt="" title="Giant Turnip">
    </td><td>1x: 4 Days</td><td>1 to 2</td><td>250 G</td></tr>
<tr><td colspan="3">
    <p>Seed Locations: Miguel's Mercantile, Town (154 G), Happe Shoppe (1000 HE, Bazaar Rank 2)</p>
    <p>Rare Variety: Giant Turnip (750 G, 960 G, 1800 G)</p>
    <p>Regrows?: No</p>
</td></tr>
<tr><td rowspan="2">
    <img src="crop_rice.webp" alt="" title="Rice">
    <p><b>Rice</b></p>
    </td><td>1x: 11 Days</td><td>5</td><td>88 G</td></tr>
<tr><td colspan="3">
    <p>Seed Locations: Miguel's Mercantitle, Bazaar (154 G)</p>
    <p>Rare Variety: None</p>
</td></tr>
<tr><td rowspan="2">
    <img src="crop_x.webp" alt="" title="Cabbage">
    <p><b>Cabbage</b></p>
    <img src="crop_x_giant.webp" alt="Giant Cabbage">
    </td><td>1x: 7 Days</td><td>1 to 2</td><td>588 G</td></tr>
<tr><td colspan="3">
    <p>Seed Locations: Miguel's Mercantile, Town or Bazaar (308 G)</p>
</td></tr>
</table>
"""

EXPECTED_SPRING = {
    "Turnip": (["Miguel's Mercantile", "Happy Shoppe"], "Giant Turnip"),
    "Strawberry": (["Miguel's Mercantile", "Happy Shoppe"], "Golden Strawberry"),
    "Rice": (["Miguel's Mercantile", "Happy Shoppe"], None),
    "Soybean": (["Miguel's Mercantile", "Happy Shoppe"], None),
    "Asparagus": (["Paradise Sundries"], "Twisted Asparagus"),
    "Garlic": (["Paradise Sundries"], "Golden Garlic"),
    "Cabbage": (["Miguel's Mercantile"], "Giant Cabbage"),
    "Potato": (["Miguel's Mercantile"], "Star Potato"),
    "Onion": (["Miguel's Mercantile"], "Brawny Onion"),
    "Radish": (["Miguel's Mercantile"], "Calabash Radish"),
    "Daikon Radish": (["Miguel's Mercantile"], "Fork-Root Daikon"),
    "Broccoli": (["Miguel's Mercantile"], "Pom-pom Broccoli"),
}


class SeedStoreParseTests(unittest.TestCase):
    def test_drops_locations_prices_and_fixes_typos(self) -> None:
        self.assertEqual(
            parse_seed_stores("Miguel's Mercantitle, Bazaar (154 G), Happe Shoppe (1000 HE, Bazaar Rank 2)"),
            ["Miguel's Mercantile", "Happy Shoppe"],
        )

    def test_town_or_bazaar_is_a_location(self) -> None:
        self.assertEqual(parse_seed_stores("Miguel's Mercantile, Town or Bazaar (126 G)"), ["Miguel's Mercantile"])

    def test_store_without_location(self) -> None:
        self.assertEqual(parse_seed_stores("Paradise Sundries (210 G, Bazaar Rank 4)"), ["Paradise Sundries"])


class RareVarietyParseTests(unittest.TestCase):
    def test_strips_prices(self) -> None:
        self.assertEqual(parse_rare_variety("Brawny Onion (938 G, 1200, 2250 G)"), "Brawny Onion")

    def test_none_means_no_rare_variety(self) -> None:
        self.assertIsNone(parse_rare_variety("None "))


class CropPageParseTests(unittest.TestCase):
    def test_parses_each_crop(self) -> None:
        crops = {c["name"]: c for c in parse_crop_page(SAMPLE_PAGE, "Spring")}
        self.assertEqual(list(crops), ["Turnip", "Rice", "Cabbage"])
        self.assertEqual(crops["Turnip"]["id"], "turnip")
        self.assertEqual(crops["Turnip"]["season"], "Spring")
        self.assertEqual(crops["Turnip"]["seed_stores"], ["Miguel's Mercantile", "Happy Shoppe"])
        self.assertEqual(crops["Turnip"]["rare_variety"], "Giant Turnip")
        self.assertEqual(crops["Rice"]["seed_stores"], ["Miguel's Mercantile"])
        self.assertIsNone(crops["Rice"]["rare_variety"])

    def test_rare_variety_falls_back_to_image_hover_text(self) -> None:
        crops = {c["name"]: c for c in parse_crop_page(SAMPLE_PAGE, "Spring")}
        self.assertEqual(crops["Cabbage"]["rare_variety"], "Giant Cabbage")


class StoredSpringCropTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
        self.crops = {c["name"]: c for c in raw}
        items = json.loads((DATA_DIR / "items.json").read_text(encoding="utf-8"))
        self.item_names = {i["name"] for i in items}

    def test_spring_ingredient_crops_match_fogu(self) -> None:
        for name, (stores, rare) in EXPECTED_SPRING.items():
            with self.subTest(name=name):
                crop = self.crops[name]
                self.assertEqual(crop["season"], "Spring")
                self.assertEqual(crop["seed_stores"], stores)
                self.assertEqual(crop["rare_variety"], rare)

    def test_ingredient_crops_and_rare_varieties_are_catalog_items(self) -> None:
        stored = {n for n, c in self.crops.items() if n in self.item_names}
        rares = {c["rare_variety"] for c in self.crops.values() if c["rare_variety"] in self.item_names}
        self.assertEqual(stored, set(EXPECTED_SPRING))
        self.assertEqual(rares, {r for _, r in EXPECTED_SPRING.values() if r})


if __name__ == "__main__":
    unittest.main()
