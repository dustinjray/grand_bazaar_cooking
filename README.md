# Grand Bazaar cooking

Scrapes cooking recipes from [fogu.com](https://fogu.com/sos6/farming/cooking.html) into JSON, then serves a local kitchen app: enter inventory, highlight dishes you can cook, and deduct ingredients when you mark a recipe cooked.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Local app

```bash
python -m app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Ingredient counts and owned appliances are stored in `data/inventory.db` (created on first run).

- **Inventory** — check Pot / Frying Pan / Oven if they are installed at home. Set item counts with +/−.
- **Recipes** — cookable dishes are highlighted. For the rest, missing slots (and a missing appliance) are listed.
- **Cook** — enter how many you made, then pick which inventory items fill each slot. Cooking consumes those items. If the dish itself is a catalog item (Omelet, Mixed Salad, …), that many are added to inventory. Appliances are never consumed.

```bash
python -m unittest tests.test_matcher
```

## Scrape

```bash
python scrape_recipes.py
```

This fetches the cooking index plus the six category pages (salads, soups, sides, main dishes, desserts, others), with a 1 second delay between requests. Cached HTML is stored under `tmp/` so reruns do not hit the network.

Outputs (under `data/`):

| File | Role |
| --- | --- |
| `groups.json` | Curated families, plus/mutant upgrades, and fogu token aliases (input) |
| `recipes.json` | All recipes with expanded `accepted` item ids per slot |
| `items.json` | Inventory catalog: each item lists the slot bases it `fills` |
| `parse_report.txt` | Unknown tokens, missing prices, empty slots |
| `crops.json` | Crops from each season page: season, seed store names, rare variety (from `scrape_crops.py`) |

Crop info comes from fogu's [spring](https://fogu.com/sos6/farming/crops_spring.html), [summer](https://fogu.com/sos6/farming/crops_summer.html), [autumn](https://fogu.com/sos6/farming/crops_autumn.html), and [winter](https://fogu.com/sos6/farming/crops_winter.html) crop pages and is collected separately into `data/crops.json`, so the app never needs to contact fogu:

```bash
python scrape_crops.py
```

Regenerate `groups.json` after catalog edits:

```bash
python build_groups.py
python scrape_recipes.py
```

## Data shape

Inventory is `item_id -> count` (`egg: 2`, `silkie_egg_plus: 1`).

Each recipe slot stores the **fully expanded** list of item ids that can fill it:

- **Family** (`egg`, `mayo`, `oil`) accepts every item whose `fills` includes that family base (Egg, Egg+, Silkie Egg, Silkie Egg+).
- **Specific** (`Silkie Egg`) accepts that line and its plus (`silkie_egg`, `silkie_egg_plus`). Regular eggs cannot fill it.
- **Plus** (`Cheese+`, `Egg+`) accepts plus-tier items that fill that id. Regular cheese cannot fill Cheese+. `Egg+` also accepts `Silkie Egg+`.
- **Mutants** (Giant Tomato, Three-Forked Carrot, Heart Lemon, …) can fill their base crop slots.
- Utensils (`POT`, `FRYING PAN`, `OVEN`) are home appliances (owned or not), not inventory stacks.
- `adapt` extras are optional star-rank boosters and are **not** required to cook.
- `sale_price` is fogu's 1-star value (first number in Profit 1/4/7).

When matching, fill the most specific slots first (fewest `accepted` ids) so a Silkie Egg+ is not spent on an Any Egg slot.

## Layout

- `models.py` — `Item`, `IngredientSlot`, `Recipe`
- `build_groups.py` — writes `data/groups.json`
- `scrape_recipes.py` — fetch, parse, expand, write JSON
- `scrape_crops.py` — fetch and parse crop info from all four season pages into `data/crops.json`
- `app/` — local FastAPI kitchen UI
