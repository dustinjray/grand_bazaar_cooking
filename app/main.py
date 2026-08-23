"""FastAPI app: inventory editor and cookable recipe list."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app import db
from app.catalog import APPLIANCES, CATEGORIES, CATEGORY_NAMES, get_catalog
from app.matcher import CookError, RecipeStatus, evaluate, plan_cook

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Grand Bazaar Cooking")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


class CountBody(BaseModel):
    count: int = Field(ge=0)


class OwnedBody(BaseModel):
    owned: bool


class CookBody(BaseModel):
    quantity: int = Field(ge=1)
    slots: list[dict[str, int]]


SORT_MODES = ("name", "price", "missing")
SORT_LABELS: tuple[tuple[str, str], ...] = (
    ("name", "Name (A–Z)"),
    ("price", "Sell price (high to low)"),
    ("missing", "Fewest missing"),
)


def _conn():
    return db.connect()


def _sale_price(recipe) -> int:
    return int(recipe.sale_price or 0)


def missing_ingredient_count(status: RecipeStatus) -> int:
    return sum(slot.quantity for slot in status.missing_slots)


def sort_recipe_rows(rows: list[dict], sort: str) -> list[dict]:
    mode = sort if sort in SORT_MODES else "name"
    if mode == "price":
        rows.sort(key=lambda row: (-_sale_price(row["recipe"]), row["recipe"].name.lower()))
    elif mode == "missing":
        rows.sort(
            key=lambda row: (
                missing_ingredient_count(row["status"]),
                -_sale_price(row["recipe"]),
                row["recipe"].name.lower(),
            )
        )
    else:
        rows.sort(key=lambda row: row["recipe"].name.lower())
    return rows


def _view_recipes(
    catalog,
    inventory,
    appliances,
    q: str,
    category: str,
    cookable_only: bool,
    sort: str = "name",
):
    q_norm = q.strip().lower()
    rows = []
    for recipe in catalog.recipes.values():
        if category and recipe.category != category:
            continue
        if q_norm and q_norm not in recipe.name.lower():
            continue
        status = evaluate(recipe, inventory, appliances)
        if cookable_only and not status.cookable:
            continue
        rows.append(
            {
                "recipe": recipe,
                "status": status,
                "category_label": CATEGORY_NAMES.get(recipe.category, recipe.category),
                "utensil_label": catalog.appliance_name(recipe.utensil),
            }
        )
    return sort_recipe_rows(rows, sort)


@app.get("/", response_class=HTMLResponse)
def recipes_page(
    request: Request,
    q: str = "",
    category: str = "",
    cookable: bool = Query(False),
    sort: str = "name",
):
    catalog = get_catalog()
    conn = _conn()
    try:
        inventory = db.get_inventory(conn)
        appliances = db.get_appliances(conn)
    finally:
        conn.close()
    if sort not in SORT_MODES:
        sort = "name"
    rows = _view_recipes(catalog, inventory, appliances, q, category, cookable, sort)
    cookable_count = sum(
        1
        for recipe in catalog.recipes.values()
        if evaluate(recipe, inventory, appliances).cookable
    )
    return templates.TemplateResponse(
        request=request,
        name="recipes.html",
        context={
            "page": "recipes",
            "rows": rows,
            "q": q,
            "category": category,
            "cookable": cookable,
            "sort": sort,
            "sort_options": SORT_LABELS,
            "categories": CATEGORIES,
            "cookable_count": cookable_count,
        },
    )


@app.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request, q: str = ""):
    catalog = get_catalog()
    conn = _conn()
    try:
        inventory = db.get_inventory(conn)
        appliances = db.get_appliances(conn)
    finally:
        conn.close()
    q_norm = q.strip().lower()
    items = []
    for item in catalog.items.values():
        if q_norm and q_norm not in item.name.lower() and q_norm not in item.id:
            continue
        items.append(
            {
                "id": item.id,
                "name": item.name,
                "family": item.family,
                "count": inventory.get(item.id, 0),
            }
        )
    items.sort(key=lambda row: row["name"].lower())
    appliance_rows = [
        {"id": aid, "name": name, "owned": appliances.get(aid, False)}
        for aid, name in APPLIANCES
    ]
    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context={
            "page": "inventory",
            "items": items,
            "appliances": appliance_rows,
            "q": q,
        },
    )


@app.post("/api/inventory/{item_id}")
def api_set_inventory(item_id: str, body: CountBody):
    catalog = get_catalog()
    if item_id not in catalog.items:
        raise HTTPException(status_code=404, detail="Unknown item")
    conn = _conn()
    try:
        count = db.set_count(conn, item_id, body.count)
    finally:
        conn.close()
    return {"id": item_id, "count": count}


@app.post("/api/appliances/{appliance_id}")
def api_set_appliance(appliance_id: str, body: OwnedBody):
    conn = _conn()
    try:
        owned = db.set_appliance(conn, appliance_id, body.owned)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        conn.close()
    return {"id": appliance_id, "owned": owned}


@app.get("/api/recipes/{recipe_id}/cook")
def api_cook_preview(recipe_id: str):
    catalog = get_catalog()
    recipe = catalog.recipes.get(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Unknown recipe")
    conn = _conn()
    try:
        inventory = db.get_inventory(conn)
        appliances = db.get_appliances(conn)
    finally:
        conn.close()
    status = evaluate(recipe, inventory, appliances)
    if not status.cookable:
        raise HTTPException(status_code=400, detail="Not enough ingredients or missing appliance.")
    slots = []
    for slot in recipe.ingredients:
        options = []
        for item_id in slot.accepted:
            have = inventory.get(item_id, 0)
            if have <= 0:
                continue
            options.append(
                {"id": item_id, "name": catalog.item_name(item_id), "have": have}
            )
        slots.append(
            {
                "display": slot.display,
                "quantity": slot.quantity,
                "options": options,
            }
        )
    return {
        "id": recipe.id,
        "name": recipe.name,
        "max_cookable": status.max_cookable,
        "utensil": catalog.appliance_name(recipe.utensil),
        "slots": slots,
    }


@app.post("/api/recipes/{recipe_id}/cook")
def api_cook(recipe_id: str, body: CookBody):
    catalog = get_catalog()
    recipe = catalog.recipes.get(recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Unknown recipe")
    conn = _conn()
    try:
        inventory = db.get_inventory(conn)
        appliances = db.get_appliances(conn)
        new_inv = plan_cook(
            recipe,
            inventory,
            appliances,
            body.slots,
            body.quantity,
            set(catalog.items),
        )
        db.apply_inventory(conn, new_inv)
    except CookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        conn.close()
    produced = recipe.id in catalog.items
    return {
        "ok": True,
        "name": recipe.name,
        "quantity": body.quantity,
        "produced": catalog.item_name(recipe.id) if produced else None,
    }
