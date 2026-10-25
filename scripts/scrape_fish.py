"""Scrape Grand Bazaar fish catch info from fogu.com into JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from scripts.scrape_recipes import CACHE_DIR, USER_AGENT, slugify

FISH_PAGE = "https://fogu.com/sos6/activities/fishing.html"
SEASON_TOKENS = {"spring", "summer", "autumn", "winter"}
TIME_IN_PARENS = re.compile(r"\(([^)]*\d:[^)]*)\)")


def _text(tag: Tag) -> str:
    return re.sub(r"\s+", " ", tag.get_text(" ")).replace("\xa0", " ").strip()


def _lines(tag: Tag) -> list[str]:
    for br in tag.find_all("br"):
        br.replace_with("\n")
    text = tag.get_text().replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


def parse_season_weather(lines: list[str]) -> tuple[list[str], list[str]]:
    seasons: list[str] = []
    weather: list[str] = []
    for line in lines:
        key = line.lower()
        if key.startswith("all season") or key in SEASON_TOKENS:
            seasons.append(line)
        else:
            weather.append(line)
    return seasons, weather


def parse_locations(lines: list[str]) -> tuple[list[str], str | None]:
    locations: list[str] = []
    time: str | None = None
    for line in lines:
        match = TIME_IN_PARENS.search(line)
        if match:
            raw = re.sub(r"\s+only$", "", match.group(1).strip(), flags=re.I)
            time = re.sub(r"\s+", " ", raw).strip()
            line = TIME_IN_PARENS.sub("", line)
        name = re.sub(r"\s+", " ", line).strip(" .")
        if name:
            locations.append(name)
    return locations, time


def parse_fish_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    heading = None
    for tag in soup.find_all(["h1", "h2"]):
        if "encyclopedia" in _text(tag).lower():
            heading = tag
            break
    tables = heading.find_all_next("table") if heading else soup.find_all("table")
    fish: list[dict] = []
    seen: set[str] = set()
    for table in tables:
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue
            name = ""
            bold = cells[0].find("b")
            if bold:
                name = re.sub(r"\s+", " ", bold.get_text()).strip()
            if not name:
                img = cells[0].find("img")
                name = (img.get("title") or img.get("alt") or "").strip() if img else ""
            if not name:
                name = _text(cells[0])
            if not name or name in seen:
                continue
            seasons, weather = parse_season_weather(_lines(cells[2]))
            locations, time = parse_locations(_lines(cells[3]))
            seen.add(name)
            fish.append(
                {
                    "id": slugify(name),
                    "name": name,
                    "seasons": seasons,
                    "weather": weather,
                    "locations": locations,
                    "rod": _text(cells[1]),
                    "time": time,
                }
            )
    return fish


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
    parser = argparse.ArgumentParser(description="Scrape fogu Grand Bazaar fish catch info")
    parser.add_argument("--out", type=Path, default=Path("data/fish.json"))
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    html = fetch(session, FISH_PAGE)
    if html is None:
        raise SystemExit(f"No HTML for {FISH_PAGE}; data/fish.json left unchanged")
    page_fish = parse_fish_page(html)
    if not page_fish:
        raise SystemExit(f"No fish parsed from {FISH_PAGE}; data/fish.json left unchanged")
    for row in page_fish:
        row["source_url"] = FISH_PAGE
        if not row["seasons"] or not row["weather"] or not row["locations"] or not row["rod"]:
            print(f"WARN: {row['name']}: incomplete catch fields")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(page_fish, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out} ({len(page_fish)} fish)")


if __name__ == "__main__":
    main()
