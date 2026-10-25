# Grand Bazaar cooking

A local companion app for **Story of Seasons: Grand Bazaar** on Nintendo Switch. Enter what's in your inventory and which kitchen appliances you own, see which dishes you can cook right now (and what you're missing for the rest), and deduct ingredients when you cook. Ingredients show where to get them: seasons and seed stores for crops, and season, weather, location, rod and time of day for fish.

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
- **Recipes** — cookable dishes are highlighted. For the rest, missing slots (and a missing appliance) are listed. Hover or click an ingredient to see its crop or fish info.
- **Cook** — enter how many you made, then pick which inventory items fill each slot. Cooking consumes those items. If the dish itself is a catalog item (Omelet, Mixed Salad, …), that many are added to inventory. Appliances are never consumed.

## Tests

```bash
python -m unittest
```

The HTML parser tests for the data scripts are skipped unless the script dependencies (`requirements-scripts.txt`) are installed.

## Game data

All game data ships with the app in `data/`, so the app works offline and never contacts any website. Recipe, crop and fish data was compiled from the Grand Bazaar guide at [fogu.com](https://fogu.com/sos6/).

## Updating game data (maintainers)

The tools in `scripts/` regenerate `data/` and are not needed to run the app. Install their extra dependencies and run them from the repo root:

```bash
python -m pip install -r requirements-scripts.txt
python -m scripts.build_groups
python -m scripts.scrape_recipes
python -m scripts.scrape_crops
python -m scripts.scrape_fish
```

`scrape_recipes` reads fogu's [cooking index](https://fogu.com/sos6/farming/cooking.html) plus the six category pages (salads, soups, sides, main dishes, desserts, others), with a 1 second delay between requests. `scrape_crops` reads the [spring](https://fogu.com/sos6/farming/crops_spring.html), [summer](https://fogu.com/sos6/farming/crops_summer.html), [autumn](https://fogu.com/sos6/farming/crops_autumn.html), and [winter](https://fogu.com/sos6/farming/crops_winter.html) crop pages, and `scrape_fish` reads the [fishing page](https://fogu.com/sos6/activities/fishing.html). Cached HTML is stored under `tmp/` so reruns do not hit the network.

Run `build_groups` before `scrape_recipes` after editing the curated catalog, since `scrape_recipes` reads `groups.json`.

Outputs (under `data/`):

| File | Role |
| --- | --- |
| `groups.json` | Curated families, plus/mutant upgrades, and fogu token aliases (from `build_groups`, input to `scrape_recipes`) |
| `recipes.json` | All recipes with expanded `accepted` item ids per slot |
| `items.json` | Inventory catalog: each item lists the slot bases it `fills` |
| `parse_report.txt` | Unknown tokens, missing prices, empty slots |
| `crops.json` | Crops from each season page: season, seed store names, rare variety (from `scrape_crops`) |
| `fish.json` | Fish catch info: seasons, weather, locations, rod, time of day (from `scrape_fish`) |

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
- `app/` — local FastAPI companion UI
- `scripts/` — offline data tools (optional dependencies):
  - `build_groups.py` — writes `data/groups.json`
  - `scrape_recipes.py` — fetch, parse, expand, write recipe and item JSON
  - `scrape_crops.py` — crop info from all four season pages into `data/crops.json`
  - `scrape_fish.py` — fish catch info into `data/fish.json`
