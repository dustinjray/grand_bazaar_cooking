"""Ingredient hover info text tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.catalog import get_catalog
from app.crops import NO_INFO, build_crop_info, crop_info_text, get_crop_info, load_crop_info
from app.main import slot_fillers

SAMPLE_CROPS = [
    {
        "id": "turnip",
        "name": "Turnip",
        "season": "Spring",
        "seed_stores": ["Miguel's Mercantile", "Happy Shoppe"],
        "rare_variety": "Giant Turnip",
        "source_url": "https://fogu.com/sos6/farming/crops_spring.html",
    },
    {
        "id": "rice",
        "name": "Rice",
        "season": "Spring",
        "seed_stores": ["Miguel's Mercantile"],
        "rare_variety": None,
        "source_url": "https://fogu.com/sos6/farming/crops_spring.html",
    },
]


class CropInfoTextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.info = build_crop_info(SAMPLE_CROPS)

    def test_crop_lists_season_and_stores(self) -> None:
        self.assertEqual(
            crop_info_text(self.info, "Turnip"),
            "Season: Spring; Purchase at Miguel's Mercantile, Happy Shoppe",
        )
        self.assertEqual(crop_info_text(self.info, "Rice"), "Season: Spring; Purchase at Miguel's Mercantile")

    def test_rare_variety_names_base_crop(self) -> None:
        self.assertEqual(crop_info_text(self.info, "Giant Turnip"), "Season: Spring; Rare variety of Turnip")

    def test_unknown_names_have_no_info(self) -> None:
        for name in ("Vegetable A", "Tomato", "None", ""):
            with self.subTest(name=name):
                self.assertEqual(crop_info_text(self.info, name), NO_INFO)
        self.assertEqual(NO_INFO, "No info available")


class StoredCropInfoTests(unittest.TestCase):
    def test_story_examples(self) -> None:
        info = get_crop_info()
        expected = {
            "Turnip": "Season: Spring; Purchase at Miguel's Mercantile, Happy Shoppe",
            "Asparagus": "Season: Spring; Purchase at Paradise Sundries",
            "Giant Turnip": "Season: Spring; Rare variety of Turnip",
            "Vegetable A": "No info available",
            "Tomato": "No info available",
        }
        for name, text in expected.items():
            with self.subTest(name=name):
                self.assertEqual(crop_info_text(info, name), text)

    def test_turnip_slot_fillers_carry_info(self) -> None:
        catalog = get_catalog()
        slot = catalog.recipes["turnip_salad"].ingredients[0]
        by_name = {row["name"]: row["info"] for row in slot_fillers(catalog, {}, slot)}
        self.assertEqual(
            by_name,
            {
                "Turnip": "Season: Spring; Purchase at Miguel's Mercantile, Happy Shoppe",
                "Giant Turnip": "Season: Spring; Rare variety of Turnip",
            },
        )


class UnavailableCropInfoTests(unittest.TestCase):
    def assert_no_info(self, info: dict[str, str]) -> None:
        self.assertEqual(info, {})
        for name in ("Turnip", "Giant Turnip", "Asparagus"):
            with self.subTest(name=name):
                self.assertEqual(crop_info_text(info, name), NO_INFO)

    def test_missing_file_has_no_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assert_no_info(load_crop_info(Path(tmp) / "crops.json"))

    def test_unreadable_file_has_no_info(self) -> None:
        contents = {
            "random text": "q8#zv not crop data !!".encode(),
            "invalid utf-8": b"\xff\xfe\x00garbage",
            "empty": b"",
            "object": json.dumps({"name": "Turnip"}).encode(),
            "number": b"42",
            "list of text": json.dumps(["Turnip"]).encode(),
            "missing fields": json.dumps([{"name": "Turnip"}]).encode(),
            "stores not a list": json.dumps([{"name": "Turnip", "season": "Spring", "seed_stores": 3}]).encode(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "crops.json"
            for label, data in contents.items():
                with self.subTest(contents=label):
                    path.write_bytes(data)
                    self.assert_no_info(load_crop_info(path))

    def test_valid_file_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "crops.json"
            path.write_text(json.dumps(SAMPLE_CROPS), encoding="utf-8")
            self.assertEqual(load_crop_info(path), build_crop_info(SAMPLE_CROPS))


if __name__ == "__main__":
    unittest.main()
