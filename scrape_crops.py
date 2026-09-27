"""Scrape Grand Bazaar crop info (seasons, seed stores, rare varieties) from fogu.com's four season pages into JSON."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from scrape_recipes import CACHE_DIR, REQUEST_DELAY_SEC, USER_AGENT, slugify

SEASON_PAGES = [
    ("Spring", "https://fogu.com/sos6/farming/crops_spring.html"),
    ("Summer", "https://fogu.com/sos6/farming/crops_summer.html"),
    ("Autumn", "https://fogu.com/sos6/farming/crops_autumn.html"),
    ("Winter", "https://fogu.com/sos6/farming/crops_winter.html"),
]

STORE_NAME_FIXES = {
    "Happe Shoppe": "Happy Shoppe",
    "Miguel's Mercantitle": "Miguel's Mercantile",
    "Miguel's Mercantie": "Miguel's Mercantile",
}

STORE_LOCATIONS = {"town", "bazaar"}


def _text(tag: Tag) -> str:
    return re.sub(r"\s+", " ", tag.get_text(" ")).replace("\xa0", " ").strip()


def _drop_parentheticals(text: str) -> str:
    return re.sub(r"\([^)]*\)", "", text)


def _field(lines: list[str], label: str) -> str | None:
    prefix = label.lower() + ":"
    for line in lines:
        if line.lower().startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _is_location(part: str) -> bool:
    words = [w.strip().lower() for w in re.split(r"\s+or\s+", part, flags=re.I)]
    return bool(words) and all(w in STORE_LOCATIONS for w in words)


def parse_seed_stores(text: str) -> list[str]:
    stores: list[str] = []
    for part in _drop_parentheticals(text).split(","):
        name = re.sub(r"\s+", " ", part).strip(" .")
        if not name or _is_location(name):
            continue
        name = STORE_NAME_FIXES.get(name, name)
        if name not in stores:
            stores.append(name)
    return stores


def parse_rare_variety(text: str) -> str | None:
    name = re.sub(r"\s+", " ", _drop_parentheticals(text)).strip(" .")
    if not name or name.lower() == "none":
        return None
    return name


def parse_crop_page(html: str, season: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    crops: list[dict] = []
    current: dict | None = None
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if not cells:
            continue
        head = cells[0]
        bold = head.find("b")
        if head.has_attr("rowspan") and bold:
            name = re.sub(r"\s+", " ", bold.get_text()).strip()
            titles = [img.get("title") or img.get("alt") or "" for img in head.find_all("img")]
            current = {
                "id": slugify(name),
                "name": name,
                "season": season,
                "seed_stores": [],
                "rare_variety": None,
                "_image_titles": [t.strip() for t in titles if t.strip()],
            }
            crops.append(current)
            continue
        if current is None or not head.has_attr("colspan"):
            continue
        lines = [_text(p) for p in head.find_all("p")] or [_text(head)]
        stores = _field(lines, "Seed Locations")
        if stores is not None:
            current["seed_stores"] = parse_seed_stores(stores)
        rare = _field(lines, "Rare Variety")
        if rare is not None:
            current["rare_variety"] = parse_rare_variety(rare)
        elif len(current["_image_titles"]) > 1:
            current["rare_variety"] = current["_image_titles"][1]
    for crop in crops:
        crop.pop("_image_titles", None)
    return crops


def fetch(session: requests.Session, url: str) -> str | None:
    cache = CACHE_DIR / url.rstrip("/").rsplit("/", 1)[-1]
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"WARN: failed to fetch {url}: {exc}")
        return None
    CACHE_DIR.mkdir(exist_ok=True)
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape fogu Grand Bazaar crop info")
    parser.add_argument("--out", type=Path, default=Path("data/crops.json"))
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SEC)
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    crops: list[dict] = []
    for i, (season, url) in enumerate(SEASON_PAGES):
        html = fetch(session, url)
        if html is None:
            raise SystemExit(f"No HTML for {url}; data/crops.json left unchanged")
        page_crops = parse_crop_page(html, season)
        if not page_crops:
            raise SystemExit(f"No crops parsed from {url}; data/crops.json left unchanged")
        for crop in page_crops:
            crop["source_url"] = url
            if not crop["seed_stores"]:
                print(f"WARN: {crop['name']}: no seed stores parsed")
        crops.extend(page_crops)
        if i < len(SEASON_PAGES) - 1:
            time.sleep(args.delay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(crops, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(crops)} crops)")


if __name__ == "__main__":
    main()
