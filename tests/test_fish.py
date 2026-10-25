"""Fish scraping and stored fish data tests."""

from __future__ import annotations

import json
import unittest

from app.catalog import DATA_DIR, get_catalog

try:
    from scripts.scrape_fish import parse_fish_page, parse_locations, parse_season_weather
except ImportError:
    HAVE_SCRAPER = False
else:
    HAVE_SCRAPER = True

needs_scraper = unittest.skipUnless(HAVE_SCRAPER, "requires requirements-scripts.txt")

SAMPLE_PAGE = """
<h2>Fish Encyclopedia</h2>
<table class="data center">
<tr><th>Name</th><th>Rod Lvl</th><th>Season/<br>Weather</th><th>Location</th><th>Profit</th></tr>
<tr><td style="text-align:center;">
    <img src="fish01.webp" title="Pale Chub"><br>
    <b>Pale Chub</b></td>
<td>All</td>
<td>All Seasons<br><br>All weather</td>
<td>Equestrian Park<br>Mountain Bridge</td>
<td>42 G</td></tr>
<tr><td style="text-align:center;">
    <img src="fish03.webp" title="Bitterling"><br>
    <b>Bitterling</b></td>
<td>All</td>
<td>All Season<br><br>All weather</td>
<td>Mountain Hilltop</td>
<td>54 G</td></tr>
<tr><td style="text-align:center;">
    <img src="fish12.webp" title="Sweetfish"><br>
    Sweetfish</b></td>
<td>Copper</td>
<td>Summer<br>Autumn<br><br>All weather</td>
<td>Mountain Bridge<br>Zephyr Town</td>
<td>120 G</td></tr>
</table>
<table class="data center">
<tr><th>Name</th><th>Rod Lvl</th><th>Season/<br>Weather</th><th>Location</th><th>Profit</th></tr>
<tr><td style="text-align:center;">
    <img src="fish43.webp" title="Shining Fish"><br>
    <b>Shining Fish</b></td>
<td>Orichalcum</td>
<td>Autumn<br><br>Sunny weather<br>No Wind</td>
<td>Mountain Hilltop<br>(12:00 pm to 5:00 pm only)</td>
<td>3300 G</td></tr>
</table>
"""

INGREDIENT_FISH = {
    "Pale Chub",
    "Bluegill",
    "Bitterling",
    "Tamoroko",
    "Mugitsuku",
    "Dark Chub",
    "Stone Moroko",
    "Amur Minnow",
    "Goldfish",
    "Icefish",
    "Sweetfish",
    "Killifish",
    "Sculpin",
    "Pond Smelt",
    "Willow Shiner",
    "Cherry Salmon",
    "Brown Trout",
    "Rainbow Trout",
    "Snakehead",
    "Dace",
    "Crucian Carp",
    "Masu Trout",
    "Char",
    "Black Bass",
    "Grayling",
    "Three-Lips Carp",
    "Eel",
    "Barbel Steed",
    "Bighead Carp",
    "Silver Carp",
    "Basa",
    "Yellow Perch",
    "Nile Perch",
    "Salmon",
    "Marbled Eel",
}

NON_INGREDIENT_FISH = {
    "Loach",
    "Dark Sleeper",
    "Wels Catfish",
    "Catfish",
    "Black Carp",
    "Grass Carp",
    "Northern Pike",
    "Shining Fish",
    "Peacock Bass",
    "Koi",
}


@needs_scraper
class SeasonWeatherParseTests(unittest.TestCase):
    def test_splits_seasons_from_weather(self) -> None:
        self.assertEqual(
            parse_season_weather(["Spring", "Summer", "All weather"]),
            (["Spring", "Summer"], ["All weather"]),
        )

    def test_keeps_all_season_typo_for_later_wording(self) -> None:
        self.assertEqual(
            parse_season_weather(["All Season", "All weather"]),
            (["All Season"], ["All weather"]),
        )


@needs_scraper
class LocationParseTests(unittest.TestCase):
    def test_strips_time_parenthetical(self) -> None:
        locations, time = parse_locations(["Mountain Hilltop", "(12:00 pm to 5:00 pm only)"])
        self.assertEqual(locations, ["Mountain Hilltop"])
        self.assertEqual(time, "12:00 pm to 5:00 pm")


@needs_scraper
class FishPageParseTests(unittest.TestCase):
    def test_parses_each_fish(self) -> None:
        fish = {row["name"]: row for row in parse_fish_page(SAMPLE_PAGE)}
        self.assertEqual(list(fish), ["Pale Chub", "Bitterling", "Sweetfish", "Shining Fish"])
        self.assertEqual(fish["Pale Chub"]["id"], "pale_chub")
        self.assertEqual(fish["Pale Chub"]["rod"], "All")
        self.assertEqual(fish["Pale Chub"]["seasons"], ["All Seasons"])
        self.assertEqual(fish["Pale Chub"]["weather"], ["All weather"])
        self.assertEqual(fish["Pale Chub"]["locations"], ["Equestrian Park", "Mountain Bridge"])
        self.assertIsNone(fish["Pale Chub"]["time"])

    def test_name_falls_back_to_image_title_when_bold_is_broken(self) -> None:
        fish = {row["name"]: row for row in parse_fish_page(SAMPLE_PAGE)}
        self.assertEqual(fish["Sweetfish"]["rod"], "Copper")
        self.assertEqual(fish["Sweetfish"]["seasons"], ["Summer", "Autumn"])

    def test_extracts_time_and_drops_it_from_locations(self) -> None:
        fish = {row["name"]: row for row in parse_fish_page(SAMPLE_PAGE)}
        self.assertEqual(fish["Shining Fish"]["locations"], ["Mountain Hilltop"])
        self.assertEqual(fish["Shining Fish"]["time"], "12:00 pm to 5:00 pm")
        self.assertEqual(fish["Shining Fish"]["weather"], ["Sunny weather", "No Wind"])


class StoredFishTests(unittest.TestCase):
    def setUp(self) -> None:
        raw = json.loads((DATA_DIR / "fish.json").read_text(encoding="utf-8"))
        self.fish = {row["name"]: row for row in raw}

    def test_keeps_all_forty_five_species(self) -> None:
        self.assertEqual(len(self.fish), 45)
        self.assertEqual(set(self.fish), INGREDIENT_FISH | NON_INGREDIENT_FISH)

    def test_ingredient_fish_are_catalog_items(self) -> None:
        item_names = {item.name for item in get_catalog().items.values()}
        self.assertEqual(INGREDIENT_FISH, INGREDIENT_FISH & item_names)
        self.assertFalse(NON_INGREDIENT_FISH & item_names)


if __name__ == "__main__":
    unittest.main()
