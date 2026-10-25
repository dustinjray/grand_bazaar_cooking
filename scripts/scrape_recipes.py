"""Scrape Grand Bazaar cooking recipes from fogu.com into structured JSON."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from models import IngredientSlot, Item, Recipe

BASE_URL = "https://fogu.com/sos6/farming/cooking.html"
USER_AGENT = "GrandBazaarCookingScraper/1.0 (local research; +https://fogu.com/sos6)"
REQUEST_DELAY_SEC = 1.0
CACHE_DIR = Path("tmp")

UTENSIL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bFRYI?ING\s+PAN\b", re.I), "frying_pan"),
    (re.compile(r"\bCOOKING\s+POT\b", re.I), "pot"),
    (re.compile(r"\bPOT\b"), "pot"),
    (re.compile(r"\bOVEN\b"), "oven"),
]

FALLBACK_PAGES = [
    ("salads", "https://fogu.com/sos6/farming/recipes_salads.html"),
    ("soups", "https://fogu.com/sos6/farming/recipes_soups.html"),
    ("sides", "https://fogu.com/sos6/farming/recipes_sides.html"),
    ("main_dishes", "https://fogu.com/sos6/farming/recipes_maindishes.html"),
    ("desserts", "https://fogu.com/sos6/farming/recipes_desserts.html"),
    ("others", "https://fogu.com/sos6/farming/recipes_others.html"),
]

CATEGORY_HINTS = [
    ("salad", "salads"),
    ("soup", "soups"),
    ("side", "sides"),
    ("main", "main_dishes"),
    ("dessert", "desserts"),
    ("other", "others"),
]

TYPO_NORMALIZATION = {
    "lavendar": "lavender",
    "lavender": "lavender",
    "caulflower": "cauliflower",
    "cauliflower": "cauliflower",
    "onon": "onion",
    "mayoonaise": "mayonnaise",
    "refuned rice flour": "refined rice flour",
    "castellla": "castella",
    "castellla": "castella",
    "sulipin": "sweetfish",
    "kilifish": "killifish",
    "barbel steel": "barbel steed",
}


def slugify(name: str) -> str:
    s = name.strip().lower().replace("+", "_plus").replace("'", "")
    out: list[str] = []
    prev_us = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    return "".join(out).strip("_")


def cell_text(cell: Tag) -> str:
    for br in cell.find_all("br"):
        br.replace_with("\n")
    return re.sub(r"[ \t]+", " ", cell.get_text()).replace("\xa0", " ").strip()


def split_or_list(text: str) -> list[str]:
    t = text.strip().strip("()")
    t = re.sub(r"\s+or\s+", ",", t, flags=re.I)
    parts = [p.strip(" .") for p in t.split(",") if p.strip() and p.strip().lower() != "etc."]
    return [p for p in parts if p]


def extract_quantity(token: str) -> tuple[int, str]:
    t = token.strip()
    qty = 1
    m = re.search(r"\(x\s*(\d+)\)", t, re.I)
    if m:
        qty = int(m.group(1))
        t = (t[: m.start()] + t[m.end() :]).strip()
    m = re.match(r"^(\d+)\s+(.*)$", t)
    if m:
        qty = int(m.group(1))
        t = m.group(2).strip()
    return qty, t


def protect_plus(text: str) -> str:
    return re.sub(r"(?<=\w)\+", "{PLUS}", text)


def restore_plus(text: str) -> str:
    return text.replace("{PLUS}", "+")


def split_ingredient_tokens(required: str) -> list[str]:
    parts = re.split(r"\s*\+\s*", protect_plus(required))
    return [restore_plus(p).strip(" \n\t") for p in parts if restore_plus(p).strip(" \n\t")]


def extract_utensil(text: str) -> tuple[str | None, str]:
    utensil = None
    remaining = text
    for pattern, value in UTENSIL_PATTERNS:
        if pattern.search(remaining):
            utensil = value
            remaining = pattern.sub(" ", remaining)
    remaining = re.sub(r"\s+\+\s+$", "", remaining)
    remaining = re.sub(r"^\s*\+\s+", "", remaining)
    remaining = re.sub(r"\s{2,}", " ", remaining).strip()
    return utensil, remaining


def parse_adapt(adapt_text: str) -> list[str]:
    if not adapt_text.strip():
        return []
    return [p.strip() for p in adapt_text.split(",") if p.strip()]


def parse_price(text: str) -> int | None:
    m = re.search(r"([\d,]+)\s*G", text, re.I)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def category_from_url(url: str) -> str:
    lower = url.lower()
    for hint, cat in CATEGORY_HINTS:
        if hint in lower:
            return cat
    return "others"


class Catalog:
    def __init__(self, raw: dict) -> None:
        self.families: dict = raw["families"]
        self.aliases: dict = {self._norm_key(k): v for k, v in raw.get("aliases", {}).items()}
        self.overrides: dict = raw.get("recipe_overrides") or raw.get("recipe_overrides", {})
        self.multi_slot = raw.get("multi_slot_aliases") or raw.get("multi_slot_aliases", {})
        self.items: dict[str, Item] = {
            iid: Item(
                id=iid,
                name=meta["name"],
                family=meta.get("family"),
                variant=meta.get("variant"),
                is_plus=bool(meta.get("is_plus", False)),
                fills=list(meta.get("fills") or [iid]),
            )
            for iid, meta in raw.get("items", {}).items()
        }
        self._patch_groups()
        self.unknown_tokens: Counter[str] = Counter()
        self.auto_created: list[str] = []

    def _patch_groups(self) -> None:
        extra = {
            "pumpkin": ["vegetable_e"],
            "eggplant": ["vegetable_e"],
            "sweet_potato": ["vegetable_e"],
            "shiitake": ["vegetable_e"],
            "potato": ["tofu_miso"],
            "green_onion": ["tofu_miso"],
            "shimeji": ["tofu_miso"],
        }
        for iid, groups in extra.items():
            item = self.items.get(iid)
            if not item:
                continue
            for g in groups:
                if g not in item.fills:
                    item.fills.append(g)

    @staticmethod
    def _norm_key(token: str) -> str:
        t = token.strip().lower()
        t = t.replace("{plus}", "+")
        t = re.sub(r"\s+", " ", t)
        t = TYPO_NORMALIZATION.get(t, t)
        for src, dst in TYPO_NORMALIZATION.items():
            t = t.replace(src, dst)
        return t.strip(" .")

    def ensure_item(self, name: str, item_id: str | None = None) -> Item:
        iid = item_id or slugify(name)
        if iid in self.items:
            return self.items[iid]
        item = Item(id=iid, name=name.strip() or iid.replace("_", " ").title(), fills=[iid])
        self.items[iid] = item
        self.auto_created.append(iid)
        return item

    def expand(self, req: dict) -> tuple[list[str], str]:
        if "accepted" in req:
            return list(dict.fromkeys(req["accepted"])), req.get("display") or ", ".join(req["accepted"])
        if "family" in req:
            fam = self.families[req["family"]]
            bases = list(fam["bases"])
            accepted = [iid for iid, item in self.items.items() if any(b in item.fills for b in bases)]
            if not accepted:
                accepted = list(bases)
            return accepted, fam["display"]
        if "item" in req:
            rid = req["item"]
            if rid not in self.items:
                self.ensure_item(rid.replace("_", " "), rid)
            target = self.items[rid]
            if req.get("exact"):
                accepted = [
                    iid
                    for iid, item in self.items.items()
                    if rid in item.fills and item.variant == target.variant
                ]
            else:
                accepted = [iid for iid, item in self.items.items() if rid in item.fills]
            return accepted, target.name
        return [], "Unknown"

    def resolve_token(self, token: str, recipe_slug: str, occurrence: int) -> tuple[dict, str]:
        raw = token.strip()
        key = self._norm_key(raw)
        override = self.overrides.get(recipe_slug, {})
        if key in override:
            return override[key], raw
        if raw in override:
            return override[raw], raw
        multi = self.multi_slot.get(recipe_slug)
        if multi:
            hits = [rule for rule in multi if rule["raw_contains"].lower() in key]
            if 0 <= occurrence < len(hits):
                return {"family": hits[occurrence]["family"]}, raw
        if key in self.aliases:
            return self.aliases[key], raw
        inner = re.fullmatch(r"\((.+)\)", key)
        if inner:
            parts = split_or_list(inner.group(1))
            accepted: list[str] = []
            labels: list[str] = []
            for part in parts:
                req, _ = self.resolve_token(part, recipe_slug, 0)
                acc, lab = self.expand(req)
                accepted.extend(acc)
                labels.append(lab)
            return {"accepted": list(dict.fromkeys(accepted)), "display": " or ".join(labels)}, raw
        prefixed = re.fullmatch(r"(.+?)\s*\((.+)\)", key)
        if prefixed and 'herb' in prefixed.group(1):
            return {"family": "herb"}, raw
        if prefixed:
            req, _ = self.resolve_token('(' + prefixed.group(2) + ')', recipe_slug, 0)
            return req, raw
        if 'additional crop' in key:
            return {"family": "vegetable_a"}, raw
        if " or " in key and not key.startswith("wheat or"):
            parts = split_or_list(key)
            if len(parts) > 1:
                accepted = []
                labels = []
                for part in parts:
                    req, _ = self.resolve_token(part, recipe_slug, 0)
                    acc, lab = self.expand(req)
                    accepted.extend(acc)
                    labels.append(lab)
                return {"accepted": list(dict.fromkeys(accepted)), "display": " or ".join(labels)}, raw
        if key.endswith("+"):
            iid = slugify(key[:-1]) + "_plus"
        else:
            iid = slugify(key)
        if iid in self.items:
            return {"item": iid}, raw
        pretty = raw.strip("() ")
        self.unknown_tokens[raw] += 1
        self.ensure_item(pretty, iid)
        return {"item": iid}, raw


class Scraper:
    def __init__(self, catalog: Catalog, delay: float = REQUEST_DELAY_SEC) -> None:
        self.catalog = catalog
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.missing_prices: list[str] = []
        self.empty_slots: list[str] = []
        self.pages_fetched: list[str] = []

    def fetch(self, url: str) -> str | None:
        name = url.rstrip("/").rsplit("/", 1)[-1]
        cache = CACHE_DIR / name
        if cache.exists():
            return cache.read_text(encoding="utf-8", errors="replace")
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            CACHE_DIR.mkdir(exist_ok=True)
            cache.write_text(resp.text, encoding="utf-8")
            return resp.text
        except requests.RequestException as exc:
            print(f"WARN: failed to fetch {url}: {exc}")
            return None

    def discover_pages(self, index_html: str | None) -> list[tuple[str, str]]:
        found: dict[str, str] = {}
        if index_html:
            soup = BeautifulSoup(index_html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "recipe" not in href.lower():
                    continue
                url = urljoin(BASE_URL, href)
                found[url] = category_from_url(url)
        for cat, url in FALLBACK_PAGES:
            found.setdefault(url, cat)
        return [(cat, url) for url, cat in found.items()]

    def parse_page(self, html: str, url: str, category: str) -> list[Recipe]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return []
        recipes: list[Recipe] = []
        current: Recipe | None = None
        for tr in table.find_all("tr"):
            if tr.find("th") and not tr.find("td"):
                continue
            cells = tr.find_all("td")
            if not cells:
                continue
            if len(cells) == 1 or (cells[0].has_attr("colspan") and len(cells) < 4):
                alt = cell_text(cells[0])
                if current and alt:
                    extra = alt if alt.lower().startswith("alt") else f"Alt: {alt}"
                    if extra not in current.obtain:
                        current.obtain = f"{current.obtain}; {extra}".strip("; ")
                continue
            if len(cells) < 5:
                continue
            name_cell, ing_cell, obtain_cell, power_cell, price_cell = cells[:5]
            bold = name_cell.find("b")
            name = bold.get_text(strip=True) if bold else cell_text(name_cell)
            name = re.sub(r"\s+", " ", name).strip()
            if not name:
                continue
            recipe = self._parse_recipe(
                name=name,
                ingredient_html=ing_cell,
                obtain=cell_text(obtain_cell),
                meal_power=cell_text(power_cell),
                price_text=cell_text(price_cell),
                category=category,
                url=url,
            )
            recipes.append(recipe)
            current = recipe
        return recipes

    def _parse_recipe(
        self,
        name: str,
        ingredient_html: Tag,
        obtain: str,
        meal_power: str,
        price_text: str,
        category: str,
        url: str,
    ) -> Recipe:
        rid = slugify(name)
        ing_text = cell_text(ingredient_html)
        parts = re.split(r"(?i)\badapt\s*:", ing_text, maxsplit=1)
        required = parts[0].strip()
        adapt = parse_adapt(parts[1]) if len(parts) > 1 else []
        utensil, required = extract_utensil(required)
        tokens = split_ingredient_tokens(required)
        slots: list[IngredientSlot] = []
        family_occ: Counter[str] = Counter()
        for token in tokens:
            qty, body = extract_quantity(token)
            occ_key = self.catalog._norm_key(body)
            occ = family_occ[occ_key]
            family_occ[occ_key] += 1
            req, raw = self.catalog.resolve_token(body, rid, occ)
            if req.get("quantity"):
                qty = int(req["quantity"])
            accepted, display = self.catalog.expand(req)
            slot = IngredientSlot(quantity=qty, accepted=accepted, display=display, raw=raw)
            slots.append(slot)
            if not accepted:
                self.empty_slots.append(f"{name}: {raw}")
        price = parse_price(price_text)
        if price is None:
            self.missing_prices.append(name)
        return Recipe(
            id=rid,
            name=name,
            category=category,
            utensil=utensil,
            sale_price=price,
            meal_power=meal_power,
            obtain=obtain,
            ingredients=slots,
            adapt=adapt,
            source_url=url,
        )

    def run(self) -> list[Recipe]:
        recipes: list[Recipe] = []
        index_html = self.fetch(BASE_URL)
        time.sleep(self.delay)
        pages = self.discover_pages(index_html)
        for i, (category, url) in enumerate(pages):
            html = self.fetch(url)
            if html is None:
                continue
            self.pages_fetched.append(url)
            recipes.extend(self.parse_page(html, url, category))
            if i < len(pages) - 1:
                time.sleep(self.delay)
        uniq: dict[str, Recipe] = {}
        for rec in recipes:
            uniq.setdefault(rec.id, rec)
        return list(uniq.values())


def write_report(path: Path, scraper: Scraper, recipes: list[Recipe]) -> None:
    lines = [
        f"pages_fetched: {len(scraper.pages_fetched)}",
        f"recipes: {len(recipes)}",
        f"items: {len(scraper.catalog.items)}",
        f"auto_created_items: {len(scraper.catalog.auto_created)}",
        f"unknown_tokens: {len(scraper.catalog.unknown_tokens)}",
        f"missing_prices: {len(scraper.missing_prices)}",
        f"empty_slots: {len(scraper.empty_slots)}",
        "",
        "== unknown tokens ==",
    ]
    for tok, n in scraper.catalog.unknown_tokens.most_common():
        lines.append(f"  {n:3d}  {tok}")
    lines.append("\n== auto-created items ==")
    for iid in scraper.catalog.auto_created:
        lines.append(f"  {iid}")
    lines.append("\n== missing prices ==")
    for name in scraper.missing_prices:
        lines.append(f"  {name}")
    lines.append("\n== empty accepted lists ==")
    for row in scraper.empty_slots:
        lines.append(f"  {row}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape fogu Grand Bazaar cooking recipes")
    parser.add_argument("--groups", type=Path, default=Path("data/groups.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("data"))
    parser.add_argument("--delay", type=float, default=REQUEST_DELAY_SEC)
    args = parser.parse_args()

    raw = json.loads(args.groups.read_text(encoding="utf-8"))
    catalog = Catalog(raw)
    scraper = Scraper(catalog, delay=args.delay)
    recipes = scraper.run()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    recipes_path = args.out_dir / "recipes.json"
    items_path = args.out_dir / "items.json"
    report_path = args.out_dir / "parse_report.txt"
    recipes_path.write_text(
        json.dumps([r.to_dict() for r in recipes], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    items_out = [item.to_dict() for _, item in sorted(catalog.items.items())]
    items_path.write_text(json.dumps(items_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(report_path, scraper, recipes)
    print(f"Wrote {recipes_path} ({len(recipes)} recipes)")
    print(f"Wrote {items_path} ({len(items_out)} items)")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
