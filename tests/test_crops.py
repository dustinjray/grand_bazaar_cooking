"""Crop scraping and stored crop data tests."""

from __future__ import annotations

import json
import unittest

from app.catalog import DATA_DIR

try:
    from scripts.scrape_crops import SEASON_PAGES, parse_crop_page, parse_rare_variety, parse_seed_stores
except ImportError:
    HAVE_SCRAPER = False
else:
    HAVE_SCRAPER = True

needs_scraper = unittest.skipUnless(HAVE_SCRAPER, "requires requirements-scripts.txt")

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

SEASON_URLS = {
    "Spring": "https://fogu.com/sos6/farming/crops_spring.html",
    "Summer": "https://fogu.com/sos6/farming/crops_summer.html",
    "Autumn": "https://fogu.com/sos6/farming/crops_autumn.html",
    "Winter": "https://fogu.com/sos6/farming/crops_winter.html",
}

MIGUEL = ["Miguel's Mercantile"]
MIGUEL_HAPPY = ["Miguel's Mercantile", "Happy Shoppe"]
PARADISE = ["Paradise Sundries"]

EXPECTED = {
    "Turnip": (["Spring"], MIGUEL_HAPPY, "Giant Turnip"),
    "Strawberry": (["Spring"], MIGUEL_HAPPY, "Golden Strawberry"),
    "Asparagus": (["Spring"], PARADISE, "Twisted Asparagus"),
    "Garlic": (["Spring"], PARADISE, "Golden Garlic"),
    "Rice": (["Spring", "Summer", "Autumn"], MIGUEL_HAPPY, None),
    "Soybean": (["Spring", "Summer", "Autumn"], MIGUEL_HAPPY, None),
    "Potato": (["Spring", "Summer", "Winter"], MIGUEL, "Star Potato"),
    "Onion": (["Spring", "Summer"], MIGUEL, "Brawny Onion"),
    "Radish": (["Spring", "Summer", "Autumn"], MIGUEL, "Calabash Radish"),
    "Cabbage": (["Spring", "Winter"], MIGUEL, "Giant Cabbage"),
    "Daikon Radish": (["Spring", "Winter"], MIGUEL, "Fork-Root Daikon"),
    "Broccoli": (["Spring", "Winter"], MIGUEL, "Pom-pom Broccoli"),
    "Pumpkin": (["Summer"], MIGUEL, "Giant Pumpkin"),
    "Watermelon": (["Summer"], MIGUEL_HAPPY, "Heart Watermelon"),
    "Corn": (["Summer"], PARADISE, "Mosaic Corn"),
    "Pineapple": (["Summer"], MIGUEL, "Jewel Pineapple"),
    "Red Bell Pepper": (["Summer"], PARADISE, "Dancing Red Bell Pepper"),
    "Summer Tea Leaves": (["Summer"], MIGUEL_HAPPY, None),
    "Melon": (["Summer", "Autumn"], MIGUEL, "Jewel Melon"),
    "Cucumber": (["Summer", "Autumn"], MIGUEL, "Wavy Cucumber"),
    "Tomato": (["Summer", "Autumn"], MIGUEL, "Giant Tomato"),
    "Eggplant": (["Summer", "Autumn"], PARADISE, "Ball Eggplant"),
    "Green Bell Pepper": (["Summer", "Autumn"], MIGUEL, "Dancing Green Bell Pepper"),
    "Cauliflower": (["Autumn"], MIGUEL, "Purple Cauliflower"),
    "Spinach": (["Autumn"], MIGUEL, "Heart Spinach"),
    "Chili Pepper": (["Autumn"], MIGUEL, "Curled Chili Pepper"),
    "Sweet Potato": (["Autumn"], MIGUEL, "Giant Sweet Potato"),
    "Carrot": (["Autumn", "Winter"], PARADISE, "Three-Forked Carrot"),
    "Bok Choy": (["Autumn", "Winter"], PARADISE, "Golden Bok Choy"),
    "Napa Cabbage": (["Winter"], ["Paradise Sundries", "Happy Shoppe"], "Golden Napa Cabbage"),
    "Green Onion": (["Winter"], PARADISE, "Brawny Green Onion"),
    "Burdock": (["Winter"], MIGUEL_HAPPY, "Twisted Burdock"),
}


@needs_scraper
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

    def test_fixes_mercantie_typo(self) -> None:
        self.assertEqual(parse_seed_stores("Miguel's Mercantie, Bazaar (168 G)"), ["Miguel's Mercantile"])


@needs_scraper
class RareVarietyParseTests(unittest.TestCase):
    def test_strips_prices(self) -> None:
        self.assertEqual(parse_rare_variety("Brawny Onion (938 G, 1200, 2250 G)"), "Brawny Onion")

    def test_none_means_no_rare_variety(self) -> None:
        self.assertIsNone(parse_rare_variety("None "))


@needs_scraper
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


@needs_scraper
class SeasonPageTests(unittest.TestCase):
    def test_scrapes_all_four_season_pages(self) -> None:
        self.assertEqual(dict(SEASON_PAGES), SEASON_URLS)


class StoredCropTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
        items = json.loads((DATA_DIR / "items.json").read_text(encoding="utf-8"))
        self.item_names = {i["name"] for i in items}

    def test_ingredient_crops_match_fogu(self) -> None:
        for name, (seasons, stores, rare) in EXPECTED.items():
            with self.subTest(name=name):
                entries = [c for c in self.raw if c["name"] == name]
                self.assertEqual([c["season"] for c in entries], seasons)
                for crop in entries:
                    self.assertEqual(crop["source_url"], SEASON_URLS[crop["season"]])
                    self.assertEqual(crop["seed_stores"], stores)
                    self.assertEqual(crop["rare_variety"], rare)

    def test_every_season_page_is_stored(self) -> None:
        self.assertEqual({c["season"] for c in self.raw}, set(SEASON_URLS))

    def test_ingredient_crops_and_rare_varieties_are_catalog_items(self) -> None:
        stored = {c["name"] for c in self.raw if c["name"] in self.item_names}
        rares = {c["rare_variety"] for c in self.raw if c["rare_variety"] in self.item_names}
        self.assertEqual(stored, set(EXPECTED))
        self.assertEqual(rares, {r for _, _, r in EXPECTED.values() if r})


if __name__ == "__main__":
    unittest.main()
