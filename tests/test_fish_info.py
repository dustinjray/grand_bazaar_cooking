"""Fish hover info text tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.catalog import get_catalog
from app.crops import crop_info_text
from app.fish import build_fish_info, fish_info_text, format_fish_info, get_fish_info, load_fish_info
from app.main import slot_fillers

SAMPLE_FISH = [
    {
        "id": "salmon",
        "name": "Salmon",
        "seasons": ["Autumn", "Winter"],
        "weather": ["All weather"],
        "locations": ["Mountain Hilltop"],
        "rod": "Gold",
        "time": None,
        "source_url": "https://fogu.com/sos6/activities/fishing.html",
    },
    {
        "id": "eel",
        "name": "Eel",
        "seasons": ["Autumn", "Winter"],
        "weather": ["Not Sunny", "Not Cloudy"],
        "locations": ["Gabriel's House", "Zephyr Town"],
        "rod": "Copper",
        "time": None,
        "source_url": "https://fogu.com/sos6/activities/fishing.html",
    },
    {
        "id": "shining_fish",
        "name": "Shining Fish",
        "seasons": ["Autumn"],
        "weather": ["Sunny weather", "No Wind"],
        "locations": ["Mountain Hilltop"],
        "rod": "Orichalcum",
        "time": "12:00 pm to 5:00 pm",
        "source_url": "https://fogu.com/sos6/activities/fishing.html",
    },
    {
        "id": "bitterling",
        "name": "Bitterling",
        "seasons": ["All Season"],
        "weather": ["All weather"],
        "locations": ["Mountain Hilltop"],
        "rod": "All",
        "time": None,
        "source_url": "https://fogu.com/sos6/activities/fishing.html",
    },
]


class FishInfoTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.info = build_fish_info(SAMPLE_FISH)

    def test_story_wording_examples(self) -> None:
        self.assertEqual(
            fish_info_text(self.info, "Salmon"),
            "Seasons: Autumn, Winter; Weather: All weather; Locations: Mountain Hilltop; Rod: Gold",
        )
        self.assertEqual(
            fish_info_text(self.info, "Eel"),
            "Seasons: Autumn, Winter; Weather: Not sunny, not cloudy; Locations: Gabriel's House, Zephyr Town; Rod: Copper",
        )
        self.assertEqual(
            fish_info_text(self.info, "Shining Fish"),
            "Seasons: Autumn; Weather: Sunny, no wind; Locations: Mountain Hilltop; Time: 12:00 pm to 5:00 pm; Rod: Orichalcum",
        )

    def test_all_season_typo_becomes_all_seasons(self) -> None:
        self.assertEqual(
            fish_info_text(self.info, "Bitterling"),
            "Seasons: All seasons; Weather: All weather; Locations: Mountain Hilltop; Rod: All",
        )

    def test_any_weather_is_kept(self) -> None:
        text = format_fish_info(
            {
                "name": "Wels Catfish",
                "seasons": ["Spring"],
                "weather": ["Any weather"],
                "locations": ["Mountain Bridge"],
                "rod": "Orichalcum",
                "time": None,
            }
        )
        self.assertEqual(
            text,
            "Seasons: Spring; Weather: Any weather; Locations: Mountain Bridge; Rod: Orichalcum",
        )


class StoredFishInfoTests(unittest.TestCase):
    def test_poke_salmon_slot_fillers_carry_info(self) -> None:
        catalog = get_catalog()
        slot = catalog.recipes["poke"].ingredients[1]
        by_name = {row["name"]: row["info"] for row in slot_fillers(catalog, {}, slot)}
        self.assertEqual(
            by_name,
            {
                "Salmon": "Seasons: Autumn, Winter; Weather: All weather; Locations: Mountain Hilltop; Rod: Gold",
            },
        )

    def test_fish_chips_fish_a_fillers_carry_icefish_and_salmon_info(self) -> None:
        catalog = get_catalog()
        slot = catalog.recipes["fish_chips"].ingredients[0]
        self.assertEqual(slot.display, "Fish A")
        by_name = {row["name"]: row["info"] for row in slot_fillers(catalog, {}, slot)}
        self.assertEqual(
            by_name["Icefish"],
            "Seasons: Spring, Winter; Weather: All weather; Locations: Bazaar, Gabriel's House; Rod: Gold",
        )
        self.assertEqual(
            by_name["Salmon"],
            "Seasons: Autumn, Winter; Weather: All weather; Locations: Mountain Hilltop; Rod: Gold",
        )

    def test_steamed_egg_custard_fish_cake_filler_has_no_info(self) -> None:
        catalog = get_catalog()
        slot = catalog.recipes["steamed_egg_custard"].ingredients[2]
        self.assertEqual(slot.display, "Fish Cake")
        by_name = {row["name"]: row["info"] for row in slot_fillers(catalog, {}, slot)}
        self.assertEqual(by_name, {"Fish Cake": "No info available"})

    def test_unadon_marbled_eel_filler_uses_its_own_info(self) -> None:
        catalog = get_catalog()
        slot = catalog.recipes["unadon"].ingredients[1]
        self.assertEqual(slot.display, "Eel")
        by_name = {row["name"]: row["info"] for row in slot_fillers(catalog, {}, slot)}
        eel = "Seasons: Autumn, Winter; Weather: Not sunny, not cloudy; Locations: Gabriel's House, Zephyr Town; Rod: Copper"
        marbled = "Seasons: Autumn, Winter; Weather: Heavy rain, stormy; Locations: Zephyr Town; Rod: Copper+"
        self.assertEqual(by_name["Eel"], eel)
        self.assertEqual(by_name["Marbled Eel"], marbled)
        self.assertNotEqual(by_name["Marbled Eel"], by_name["Eel"])

    def test_named_fish_slot_uses_fish_text_not_crop_fallback(self) -> None:
        info = get_fish_info()
        self.assertEqual(
            crop_info_text(info, "Salmon"),
            "Seasons: Autumn, Winter; Weather: All weather; Locations: Mountain Hilltop; Rod: Gold",
        )
        self.assertEqual(crop_info_text(info, "Fish A"), "No info available")

    def test_ingredient_and_non_ingredient_texts_match_story_tables(self) -> None:
        info = get_fish_info()
        expected = {
            "Pale Chub": "Seasons: All seasons; Weather: All weather; Locations: Equestrian Park, Mountain Bridge, Gabriel's House, Zephyr Town; Rod: All",
            "Bluegill": "Seasons: All seasons; Weather: Not sunny; Locations: Gabriel's House, Zephyr Town; Rod: Copper",
            "Bitterling": "Seasons: All seasons; Weather: All weather; Locations: Mountain Hilltop; Rod: All",
            "Tamoroko": "Seasons: Spring; Weather: All weather; Locations: Gabriel's House, Yellow Windmill, Zephyr Town; Rod: All",
            "Mugitsuku": "Seasons: Spring; Weather: All weather; Locations: Bazaar, Zephyr Town; Rod: Silver",
            "Dark Chub": "Seasons: Spring, Summer; Weather: All weather; Locations: Gabriel's House, Yellow Windmill, Zephyr Town; Rod: All",
            "Stone Moroko": "Seasons: Spring, Autumn, Winter; Weather: All weather; Locations: Bazaar, Equestrian Park, Zephyr Town; Rod: Copper",
            "Amur Minnow": "Seasons: Spring, Autumn, Winter; Weather: Not cloudy; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream, Yellow Windmill; Rod: All",
            "Goldfish": "Seasons: Spring, Winter; Weather: All weather; Locations: Gabriel's House, Yellow Windmill; Rod: Copper",
            "Icefish": "Seasons: Spring, Winter; Weather: All weather; Locations: Bazaar, Gabriel's House; Rod: Gold",
            "Sweetfish": "Seasons: Summer, Autumn; Weather: All weather; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream, Yellow Windmill, Zephyr Town; Rod: Copper",
            "Killifish": "Seasons: Summer, Autumn; Weather: Sunny, cloudy; Locations: Bazaar, Mountain Bridge, Gabriel's House; Rod: Copper",
            "Sculpin": "Seasons: Summer, Autumn, Winter; Weather: All weather; Locations: Equestrian Park, Mountain Hilltop, Yellow Windmill, Zephyr Town; Rod: All",
            "Pond Smelt": "Seasons: Winter; Weather: All weather; Locations: Gabriel's House, Zephyr Town; Rod: Copper",
            "Willow Shiner": "Seasons: Winter; Weather: Not sunny; Locations: Mountain Hilltop; Rod: Copper",
            "Cherry Salmon": "Seasons: Spring, Summer; Weather: All weather; Locations: Yellow Windmill; Rod: Gold",
            "Brown Trout": "Seasons: Spring, Summer, Autumn; Weather: All weather; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream; Rod: Silver",
            "Rainbow Trout": "Seasons: Spring, Summer, Autumn; Weather: All weather; Locations: Mountain Stream, Yellow Windmill; Rod: All",
            "Snakehead": "Seasons: Spring, Autumn, Winter; Weather: Sunny, cloudy; Locations: Zephyr Town; Rod: Gold",
            "Dace": "Seasons: All seasons; Weather: All weather; Locations: Yellow Windmill, Zephyr Town; Rod: All",
            "Crucian Carp": "Seasons: Spring, Summer, Winter; Weather: All weather; Locations: Equestrian Park; Rod: Copper",
            "Masu Trout": "Seasons: Spring, Summer; Weather: Rainy, stormy; Locations: Bazaar, Yellow Windmill; Rod: Gold",
            "Char": "Seasons: Spring, Summer, Autumn; Weather: Not sunny; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream, Yellow Windmill; Rod: Gold",
            "Black Bass": "Seasons: Spring, Summer, Winter; Weather: Not sunny; Locations: Equestrian Park, Mountain Bridge, Mountain Hilltop, Mountain Stream, Yellow Windmill, Zephyr Town; Rod: Silver",
            "Grayling": "Seasons: Spring, Summer; Weather: Not stormy, not heavy rain; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream; Rod: Silver",
            "Three-Lips Carp": "Seasons: Summer; Weather: All weather; Locations: Yellow Windmill, Zephyr Town; Rod: Silver",
            "Eel": "Seasons: Autumn, Winter; Weather: Not sunny, not cloudy; Locations: Gabriel's House, Zephyr Town; Rod: Copper",
            "Barbel Steed": "Seasons: Autumn, Winter; Weather: Not sunny, not cloudy; Locations: Gabriel's House, Zephyr Town; Rod: Silver",
            "Bighead Carp": "Seasons: All seasons; Weather: All weather; Locations: Bazaar, Yellow Windmill, Zephyr Town; Rod: Silver",
            "Silver Carp": "Seasons: All seasons; Weather: All weather; Locations: Mountain Stream, Yellow Windmill, Zephyr Town; Rod: All",
            "Basa": "Seasons: All seasons; Weather: All weather; Locations: Mountain Bridge; Rod: All",
            "Yellow Perch": "Seasons: Summer, Autumn; Weather: All weather; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream; Rod: Gold",
            "Nile Perch": "Seasons: Summer, Autumn; Weather: All weather; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream; Rod: Silver",
            "Salmon": "Seasons: Autumn, Winter; Weather: All weather; Locations: Mountain Hilltop; Rod: Gold",
            "Marbled Eel": "Seasons: Autumn, Winter; Weather: Heavy rain, stormy; Locations: Zephyr Town; Rod: Copper+",
            "Loach": "Seasons: Spring, Summer; Weather: All weather; Locations: Mountain Bridge, Mountain Hilltop, Mountain Stream; Rod: All",
            "Dark Sleeper": "Seasons: Autumn, Winter; Weather: All weather; Locations: Bazaar, Equestrian Park, Zephyr Town; Rod: All",
            "Wels Catfish": "Seasons: Spring; Weather: Any weather; Locations: Mountain Bridge; Rod: Orichalcum",
            "Catfish": "Seasons: Spring, Summer; Weather: Rainy, stormy; Locations: Zephyr Town; Rod: Gold",
            "Black Carp": "Seasons: Spring, Autumn; Weather: Any weather; Locations: Yellow Windmill, Zephyr Town; Rod: Gold",
            "Grass Carp": "Seasons: Summer, Autumn; Weather: Any weather; Locations: Gabriel's House, Zephyr Town; Rod: Gold",
            "Northern Pike": "Seasons: Autumn; Weather: Any weather; Locations: Gabriel's House; Rod: Orichalcum",
            "Shining Fish": "Seasons: Autumn; Weather: Sunny, no wind; Locations: Mountain Hilltop; Time: 12:00 pm to 5:00 pm; Rod: Orichalcum",
            "Peacock Bass": "Seasons: Winter; Weather: Any weather; Locations: Equestrian Park; Rod: Orichalcum",
            "Koi": "Seasons: Winter; Weather: Sunny, cloudy; Locations: Yellow Windmill; Rod: Gold",
        }
        self.assertEqual(set(info), set(expected))
        for name, text in expected.items():
            with self.subTest(name=name):
                self.assertEqual(info[name], text)


class UnavailableFishInfoTests(unittest.TestCase):
    def assert_no_info(self, info: dict[str, str]) -> None:
        self.assertEqual(info, {})
        for name in ("Salmon", "Eel", "Icefish"):
            with self.subTest(name=name):
                self.assertEqual(fish_info_text(info, name), "No info available")

    def test_missing_file_has_no_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_no_info(load_fish_info(Path(tmp) / "fish.json"))

    def test_unreadable_file_has_no_info(self) -> None:
        contents = {
            "random text": "q8#zv not fish data !!".encode(),
            "invalid utf-8": b"\xff\xfe\x00garbage",
            "empty": b"",
            "object": json.dumps({"name": "Salmon"}).encode(),
            "number": b"42",
            "list of text": json.dumps(["Salmon"]).encode(),
            "missing fields": json.dumps([{"name": "Salmon"}]).encode(),
            "locations not a list": json.dumps(
                [{"name": "Salmon", "seasons": ["Autumn"], "weather": ["All weather"], "locations": 3, "rod": "Gold"}]
            ).encode(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fish.json"
            for label, data in contents.items():
                with self.subTest(contents=label):
                    path.write_bytes(data)
                    self.assert_no_info(load_fish_info(path))

    def test_valid_file_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fish.json"
            path.write_text(json.dumps(SAMPLE_FISH), encoding="utf-8")
            self.assertEqual(load_fish_info(path), build_fish_info(SAMPLE_FISH))


if __name__ == "__main__":
    unittest.main()
