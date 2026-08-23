"""Emit data/groups.json from the curated Grand Bazaar ingredient catalog."""

from __future__ import annotations

import json
from pathlib import Path


def slug(name: str) -> str:
    s = name.strip().lower().replace("+", "_plus").replace("'", "")
    out = []
    prev_us = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    return "".join(out).strip("_")


def add_item(
    items: dict,
    name: str,
    *,
    family: str | None = None,
    variant: str | None = None,
    is_plus: bool = False,
    fills: list[str] | None = None,
    item_id: str | None = None,
    groups: list[str] | None = None,
) -> str:
    iid = item_id or slug(name)
    fill = list(fills or [iid])
    for g in groups or []:
        if g not in fill:
            fill.append(g)
    if iid not in fill:
        fill.append(iid)
    if iid in items:
        prev = items[iid]
        fill = list(dict.fromkeys([*prev.get("fills", []), *fill]))
        family = family or prev.get("family")
        variant = variant or prev.get("variant")
        is_plus = is_plus or bool(prev.get("is_plus"))
        name = prev.get("name") or name
    items[iid] = {
        "name": name,
        "family": family,
        "variant": variant,
        "is_plus": is_plus,
        "fills": list(dict.fromkeys(fill)),
    }
    return iid


def plus_line(
    items: dict,
    base_name: str,
    family: str,
    *,
    variant: str | None = None,
    extra_fills: list[str] | None = None,
    plus_also_fills: list[str] | None = None,
    groups: list[str] | None = None,
) -> tuple[str, str]:
    base_id = add_item(
        items,
        base_name,
        family=family,
        variant=variant,
        fills=[slug(base_name), *(extra_fills or [])],
        groups=groups,
    )
    plus_fills = [base_id, f"{base_id}_plus", *(extra_fills or []), *(plus_also_fills or [])]
    plus_id = add_item(
        items,
        f"{base_name}+",
        family=family,
        variant=variant,
        is_plus=True,
        fills=plus_fills,
        groups=groups,
        item_id=f"{base_id}_plus",
    )
    return base_id, plus_id


def main() -> None:
    items: dict[str, dict] = {}

    # --- Eggs ---
    add_item(items, "Egg", family="egg", variant="chicken", fills=["egg"])
    add_item(items, "Egg+", family="egg", variant="chicken", is_plus=True, fills=["egg", "egg_plus"])
    add_item(items, "Silkie Egg", family="egg", variant="silkie", fills=["egg", "silkie_egg"])
    add_item(
        items,
        "Silkie Egg+",
        family="egg",
        variant="silkie",
        is_plus=True,
        fills=["egg", "egg_plus", "silkie_egg", "silkie_egg_plus"],
    )

    # --- Milk ---
    add_item(items, "Milk", family="milk", variant="cow", fills=["milk"])
    add_item(items, "Milk+", family="milk", variant="cow", is_plus=True, fills=["milk", "milk_plus"])
    add_item(items, "Buffalo Milk", family="milk", variant="buffalo", fills=["milk", "buffalo_milk"])
    add_item(
        items,
        "Buffalo Milk+",
        family="milk",
        variant="buffalo",
        is_plus=True,
        fills=["milk", "milk_plus", "buffalo_milk", "buffalo_milk_plus"],
    )

    # --- Cheese / butter / mayo / yogurt ---
    add_item(items, "Cheese", family="cheese", fills=["cheese"])
    add_item(items, "Cheese+", family="cheese", is_plus=True, fills=["cheese", "cheese_plus"])
    add_item(items, "Herb Cheese", family="cheese", variant="herb", fills=["cheese", "herb_cheese"])
    add_item(items, "Butter", family="butter", fills=["butter"])
    add_item(items, "Butter+", family="butter", is_plus=True, fills=["butter", "butter_plus"])
    add_item(items, "Herb Butter", family="butter", variant="herb", fills=["butter", "herb_butter"])
    add_item(items, "Mayonnaise", family="mayonnaise", fills=["mayonnaise"])
    add_item(items, "Mayonnaise+", family="mayonnaise", is_plus=True, fills=["mayonnaise", "mayonnaise_plus"])
    add_item(items, "Herb Mayonnaise", family="mayonnaise", variant="herb", fills=["mayonnaise", "herb_mayonnaise"])
    add_item(items, "Yogurt", family="yogurt", fills=["yogurt"])
    add_item(items, "Yogurt+", family="yogurt", is_plus=True, fills=["yogurt", "yogurt_plus"])

    # --- Honey ---
    add_item(items, "Honey", family="honey", fills=["honey"])
    add_item(items, "Invigorating Honey", family="honey", variant="invigorating", fills=["honey", "invigorating_honey"])
    add_item(items, "Mellow Honey", family="honey", variant="mellow", fills=["honey", "mellow_honey"])
    add_item(items, "Royal Honey", family="honey", variant="royal", fills=["honey", "royal_honey"])

    # --- Oils ---
    for oil_name, iid in [
        ("Oil", "oil"),
        ("Nut Oil", "nut_oil"),
        ("Herb Oil", "herb_oil"),
        ("Olive Oil", "olive_oil"),
        ("Grape Oil", "grape_oil"),
    ]:
        fills = ["oil"] if iid == "oil" else ["oil", iid]
        add_item(items, oil_name, family="oil", fills=fills, item_id=iid)

    # --- Mushrooms ---
    mushrooms = [
        ("Common Mushroom", "common_mushroom"),
        ("Shiitake", "shiitake"),
        ("Shimeji", "shimeji"),
        ("Porcini", "porcini"),
        ("Morel", "morel"),
        ("Matsutake", "matsutake"),
        ("Monarch Mushroom", "monarch_mushroom"),
    ]
    for name, iid in mushrooms:
        groups = ["mushroom"]
        if iid == "common_mushroom":
            groups.append("vegetable_c")
        if iid == "shiitake":
            groups.append("vegetable_e")
        add_item(items, name, family="mushroom", fills=[iid], groups=groups, item_id=iid)

    # --- Herbs ---
    for herb in ["Mint", "Chamomile", "Lavender"]:
        add_item(items, herb, family="herb", fills=[slug(herb)])

    # --- Breads ---
    add_item(items, "Bread", family="bread", fills=["bread", "bread_toast"])
    add_item(items, "White Bread", family="bread", fills=["bread", "white_bread", "bread_toast"])
    add_item(items, "Baguette", family="bread", fills=["bread", "baguette"])
    add_item(items, "Focaccia", family="bread", fills=["bread", "focaccia"])
    add_item(items, "Breadcrumbs", family="breadcrumb", fills=["breadcrumbs"])
    add_item(items, "White Breadcrumbs", family="breadcrumb", fills=["breadcrumbs", "white_breadcrumbs"])

    # --- Flours ---
    add_item(items, "Wheat Flour", family="flour", fills=["wheat_flour", "flour"])
    add_item(items, "Rice Flour", family="flour", fills=["rice_flour", "flour"])
    add_item(items, "Buckwheat Flour", fills=["buckwheat_flour"])
    add_item(items, "Refined Rice Flour", fills=["refined_rice_flour"])
    add_item(items, "Soybean Flour", fills=["soybean_flour"])

    # --- Jams ---
    for jam_name in ["Apple Jam", "Strawberry Jam", "Grape Jam", "Blueberry Jam"]:
        add_item(items, jam_name, family="jam", fills=[slug(jam_name), "jam"])

    # Crops / produce
    veg_a = ["Cucumber", "Onion", "Asparagus", "Tomato", "Red Bell Pepper", "Carrot", "Turnip", "Sweet Potato", "Pumpkin", "Eggplant"]
    veg_b = ["Potato", "Asparagus", "Carrot", "Cabbage", "Turnip", "Cauliflower"]
    veg_c = ["Broccoli", "Potato", "Asparagus", "Red Bell Pepper", "Carrot", "Pumpkin"]
    veg_d = ["Potato", "Carrot", "Onion"]
    veg_e = ["Pumpkin", "Eggplant", "Sweet Potato"]
    fruit_a = ["Cherry", "Blueberry", "Green Grape", "Strawberry", "Mango", "Pineapple", "Banana", "Peach", "Orange", "Melon"]
    fruit_b = ["Apple", "Red Grape", "Green Grape", "Strawberry", "Mango", "Pineapple", "Banana", "Peach", "Orange", "Melon"]

    produce = [
        "Cucumber", "Onion", "Asparagus", "Tomato", "Red Bell Pepper", "Green Bell Pepper",
        "Carrot", "Turnip", "Sweet Potato", "Pumpkin", "Eggplant", "Potato", "Cabbage",
        "Cauliflower", "Broccoli", "Napa Cabbage", "Bok Choy", "Spinach", "Garlic",
        "Chili Pepper", "Green Onion", "Daikon Radish", "Radish", "Burdock", "Corn",
        "Avocado", "Lemon", "Apple", "Cherry", "Blueberry", "Green Grape", "Red Grape",
        "Strawberry", "Mango", "Pineapple", "Banana", "Peach", "Orange", "Melon",
        "Watermelon", "Chestnut", "Olive", "Almond", "Coffee Bean",
    ]
    group_map = {}
    for n in veg_a:
        group_map.setdefault(n, []).append("vegetable_a")
    for n in veg_b:
        group_map.setdefault(n, []).append("vegetable_b")
    for n in veg_c:
        group_map.setdefault(n, []).append("vegetable_c")
    for n in veg_d:
        group_map.setdefault(n, []).append("vegetable_d")
    for n in veg_e:
        group_map.setdefault(n, []).append("vegetable_e")
    for n in fruit_a:
        group_map.setdefault(n, []).append("fruit_a")
    for n in fruit_b:
        group_map.setdefault(n, []).append("fruit_b")

    # Rare/mutant crop -> base crop. Rares copy the base's vegetable/fruit groups.
    mutants = {
        "Ball Eggplant": "Eggplant",
        "Brawny Green Onion": "Green Onion",
        "Brawny Onion": "Onion",
        "Calabash Radish": "Radish",
        "Chicken Mango": "Mango",
        "Curled Chili Pepper": "Chili Pepper",
        "Dancing Green Bell Pepper": "Green Bell Pepper",
        "Dancing Red Bell Pepper": "Red Bell Pepper",
        "Finger Green Grapes": "Green Grape",
        "Finger Red Grapes": "Red Grape",
        "Flower Blueberry": "Blueberry",
        "Fork-Root Daikon": "Daikon Radish",
        "Giant Avocado": "Avocado",
        "Giant Cabbage": "Cabbage",
        "Giant Pumpkin": "Pumpkin",
        "Giant Sweet Potato": "Sweet Potato",
        "Giant Tomato": "Tomato",
        "Giant Turnip": "Turnip",
        "Golden Apple": "Apple",
        "Golden Banana": "Banana",
        "Golden Bok Choy": "Bok Choy",
        "Golden Cacao Bean": "Cacao Bean",
        "Golden Coffee Bean": "Coffee Bean",
        "Golden Garlic": "Garlic",
        "Golden Napa Cabbage": "Napa Cabbage",
        "Golden Olive": "Olive",
        "Golden Peach": "Peach",
        "Golden Strawberry": "Strawberry",
        "Heart Cherry": "Cherry",
        "Heart Lemon": "Lemon",
        "Heart Spinach": "Spinach",
        "Heart Watermelon": "Watermelon",
        "Jewel Almond": "Almond",
        "Jewel Melon": "Melon",
        "Jewel Pineapple": "Pineapple",
        "Lumpy Orange": "Orange",
        "Mosaic Corn": "Corn",
        "Pom-pom Broccoli": "Broccoli",
        "Purple Cauliflower": "Cauliflower",
        "Star Potato": "Potato",
        "Three-Forked Carrot": "Carrot",
        "Twisted Asparagus": "Asparagus",
        "Twisted Burdock": "Burdock",
        "Wavy Cucumber": "Cucumber",
    }

    for name in produce:
        extra = group_map.get(name, [])
        add_item(items, name, fills=[slug(name)], groups=extra)

    for rare_name, base_name in mutants.items():
        extra = group_map.get(base_name, [])
        base_id = slug(base_name)
        add_item(items, rare_name, fills=[base_id, slug(rare_name)], groups=extra)

    # Icefish / pond smelt also veg E
    fish_a = ["Yellow Perch", "Snakehead", "Masu Trout", "Char", "Salmon", "Icefish", "Cherry Salmon"]
    fish_b = ["Bluegill", "Willow Shiner", "Killifish", "Stone Moroko", "Pond Smelt", "Sweetfish", "Eel", "Marbled Eel", "Goldfish", "Crucian Carp"]
    fish_c = ["Amur Minnow", "Dace", "Pale Chub", "Sculpin", "Dark Chub", "Bitterling", "Tamoroko", "Rainbow Trout", "Silver Carp", "Basa"]
    fish_d = ["Nile Perch", "Salmon", "Masu Trout", "Cherry Salmon", "Brown Trout", "Yellow Perch", "Sweetfish"]
    fish_e = ["Grayling", "Bighead Carp", "Nile Perch", "Barbel Steed", "Three-Lips Carp", "Brown Trout", "Black Bass", "Mugitsuku"]

    def fish_groups(name: str) -> list[str]:
        g = []
        if name in fish_a:
            g.append("fish_a")
        if name in fish_b:
            g.append("fish_b")
        if name in fish_c:
            g.append("fish_c")
        if name in fish_d:
            g.append("fish_d")
        if name in fish_e:
            g.append("fish_e")
        if name in {"Eel", "Marbled Eel"}:
            g.append("eel")
        if name in {"Icefish", "Pond Smelt"}:
            g.append("vegetable_e")
        return g

    for name in dict.fromkeys(fish_a + fish_b + fish_c + fish_d + fish_e):
        add_item(items, name, family="fish", fills=[slug(name)], groups=fish_groups(name))

    # Tofu family extras for miso soup
    add_item(items, "Tofu", fills=["tofu", "tofu_miso"])
    add_item(items, "Fried Tofu", fills=["fried_tofu", "tofu_miso"])
    add_item(items, "Fish Cake", fills=["fish_cake"])
    add_item(items, "Seaweed", fills=["seaweed"])
    add_item(items, "Urchin", fills=["urchin"])
    add_item(items, "Miso", fills=["miso"])
    add_item(items, "Soy Sauce", fills=["soy_sauce"])
    add_item(items, "Sugar", fills=["sugar"])
    add_item(items, "Salt", fills=["salt"])
    add_item(items, "Pepper", fills=["pepper"])
    add_item(items, "Vinegar", fills=["vinegar"])
    add_item(items, "Spice", fills=["spice"])
    add_item(items, "Curry Powder", fills=["curry_powder"])
    add_item(items, "Soybean", fills=["soybean"])
    add_item(items, "Soy Milk", fills=["soy_milk"])
    add_item(items, "Chocolate", fills=["chocolate"])
    add_item(items, "Walnut", fills=["walnut"])
    add_item(items, "Cacao Bean", fills=["cacao_bean"])
    add_item(items, "Coffee Pack", fills=["coffee_pack"])
    add_item(items, "Hot Coffee", fills=["hot_coffee"])
    add_item(items, "Pasta", fills=["pasta"])
    add_item(items, "Herb Pasta", fills=["herb_pasta"])
    add_item(items, "Penne Pasta", fills=["penne_pasta"])
    add_item(items, "Rice", fills=["rice"])
    add_item(items, "Cooked Rice", fills=["cooked_rice"])
    add_item(items, "Sashimi", fills=["sashimi"])
    add_item(items, "Tempura", fills=["tempura"])
    add_item(items, "Omelet", fills=["omelet"])
    add_item(items, "Onigiri", fills=["onigiri"])
    add_item(items, "Mixed Salad", fills=["mixed_salad"])
    add_item(items, "Castella", fills=["castella"])
    add_item(items, "Mochi", fills=["mochi"])
    add_item(items, "Bottled Chestnuts", fills=["bottled_chestnuts"])
    add_item(items, "Bottled Walnuts", fills=["bottled_walnuts"])
    add_item(items, "Cookies", fills=["cookies"])
    add_item(items, "Curry Rice", fills=["curry_rice"])
    add_item(items, "Supreme Curry", fills=["supreme_curry"])
    add_item(items, "Summer Tea Leaves", fills=["summer_tea_leaves"])
    add_item(items, "Ice Cream", fills=["ice_cream"])

    tea_tins = [
        "Black Tea Tin", "Summer Blend Tea Can", "Golden Blend Tea Tin", "Watermelon Tea Tin",
        "Melon Tea Tin", "Pineapple Tea Tin", "Spring Blend Tea Tin", "Strawberry Tea Tin",
        "Sencha Tea Tin", "Pu'er Tea Tin", "Oolong Tea Tin", "Matcha Tea Tin", "Mint Tea Tin",
        "Chamomile Tea Tin", "Lavender Tea Tin", "Green Tea Tin", "Autumn Blend Tea Tin",
        "Banana Tea Tin", "Mango Tea Tin", "Green Grape Tea Tin", "Red Grape Tea Tin",
        "Apple Tea Tin", "Cherry Tea Tin", "Peach Tea Tin", "Orange Tea Tin", "Lemon Tea Tin",
        "Blueberry Tea Tin", "Olive Tea Tin",
    ]
    for name in tea_tins:
        add_item(items, name)

    juices = [
        "Banana Juice", "Peach Juice", "Lemon Juice", "Strawberry Juice", "Orange Juice",
        "Cherry Juice", "Grape Juice", "Blueberry Juice", "Apple Juice", "Spring Juice",
        "Summer Juice", "Autumn Juice",
    ]
    for name in juices:
        add_item(items, name)

    add_item(items, "Black Tea", fills=["black_tea"])

    families = {
        "egg": {"display": "Any Egg", "bases": ["egg"]},
        "milk": {"display": "Any Milk", "bases": ["milk"]},
        "cheese": {"display": "Any Cheese", "bases": ["cheese"]},
        "butter": {"display": "Any Butter", "bases": ["butter"]},
        "mayonnaise": {"display": "Any Mayonnaise", "bases": ["mayonnaise"]},
        "yogurt": {"display": "Any Yogurt", "bases": ["yogurt"]},
        "honey": {"display": "Any Honey", "bases": ["honey"]},
        "oil": {"display": "Any Oil", "bases": ["oil"]},
        "mushroom": {"display": "Any Mushroom", "bases": ["mushroom"]},
        "herb": {"display": "Any Herb", "bases": ["mint", "chamomile", "lavender"]},
        "bread": {"display": "Any Bread", "bases": ["bread"]},
        "bread_toast": {"display": "Bread or White Bread", "bases": ["bread_toast"]},
        "breadcrumb": {"display": "Any Breadcrumbs", "bases": ["breadcrumbs"]},
        "flour": {"display": "Wheat or Rice Flour", "bases": ["flour"]},
        "jam": {"display": "Any Jam", "bases": ["jam"]},
        "vegetable_a": {"display": "Vegetable A", "bases": ["vegetable_a"]},
        "vegetable_b": {"display": "Vegetable B", "bases": ["vegetable_b"]},
        "vegetable_c": {"display": "Vegetable C", "bases": ["vegetable_c"]},
        "vegetable_d": {"display": "Vegetable D", "bases": ["vegetable_d"]},
        "vegetable_e": {"display": "Vegetable E", "bases": ["vegetable_e"]},
        "fruit_a": {"display": "Fruit A", "bases": ["fruit_a"]},
        "fruit_b": {"display": "Fruit B", "bases": ["fruit_b"]},
        "fish_a": {"display": "Fish A", "bases": ["fish_a"]},
        "fish_b": {"display": "Fish B", "bases": ["fish_b"]},
        "fish_c": {"display": "Fish C", "bases": ["fish_c"]},
        "fish_d": {"display": "Fish D", "bases": ["fish_d"]},
        "fish_e": {"display": "Fish E", "bases": ["fish_e"]},
        "eel": {"display": "Eel", "bases": ["eel"]},
        "tofu_miso": {"display": "Miso Soup extra", "bases": ["tofu_miso"]},
    }

    aliases = {
        # families (lowercase fogu shorthand)
        "egg": {"family": "egg"},
        "eggs": {"family": "egg"},
        "milk": {"family": "milk"},
        "cheese": {"family": "cheese"},
        "butter": {"family": "butter"},
        "mayo": {"family": "mayonnaise"},
        "mayoonaise": {"family": "mayonnaise"},
        "mayonnaise": {"family": "mayonnaise"},
        "yogurt": {"family": "yogurt"},
        "yoghurt": {"family": "yogurt"},
        "honey": {"family": "honey"},
        "oil": {"family": "oil"},
        "oils": {"family": "oil"},
        "mushroom": {"family": "mushroom"},
        "mushrooms": {"family": "mushroom"},
        "bread": {"family": "bread"},
        "breadcrumbs": {"family": "breadcrumb"},
        "jam": {"family": "jam"},
        "(jam)": {"family": "jam"},
        "(fruit)": {"family": "fruit_a"},
        "(veggie)": {"family": "vegetable_a"},
        "(veggies)": {"family": "vegetable_c"},
        "(wild herb)": {"family": "herb"},
        "(fish)": {"family": "fish_e"},
        "fish": {"family": "fish_c"},
        "1 additional crop": {"family": "vegetable_a"},
        "1 additional crop": {"family": "vegetable_a"},
        "herbs": {"family": "herb"},
        "wild herb": {"family": "herb"},
        # plus / specific
        "egg+": {"item": "egg_plus"},
        "egg +": {"item": "egg_plus"},
        "silkie egg": {"item": "silkie_egg"},
        "silkie egg+": {"item": "silkie_egg_plus"},
        "milk+": {"item": "milk_plus"},
        "buffalo milk": {"item": "buffalo_milk"},
        "buffalo milk+": {"item": "buffalo_milk_plus"},
        "cheese+": {"item": "cheese_plus"},
        "butter+": {"item": "butter_plus"},
        "mayonnaise+": {"item": "mayonnaise_plus"},
        "yogurt+": {"item": "yogurt_plus"},
        "herb butter": {"item": "herb_butter"},
        "olive oil": {"item": "olive_oil"},
        "royal honey": {"item": "royal_honey"},
        "wheat flour": {"item": "wheat_flour"},
        "rice flour": {"item": "rice_flour"},
        "wheat or rice flour": {"family": "flour"},
        "wheat/rice flour": {"family": "flour"},
        "wheat/rice flour": {"family": "flour"},
        "(wheat or rice flour)": {"family": "flour"},
        "bread or white bread": {"family": "bread_toast"},
        "mint or chamomile or lavender": {"family": "herb"},
        "mint or chamomile or lavender": {"family": "herb"},
        # typos / fogu names
        "lavendar": {"item": "lavender"},
        "lavender": {"item": "lavender"},
        "caulflower": {"item": "cauliflower"},
        "cauliflower": {"item": "cauliflower"},
        "onon": {"item": "onion"},
        "refuned rice flour": {"item": "refined_rice_flour"},
        "castellla": {"item": "castella"},
        "castellla": {"item": "castella"},
        "shiitake": {"item": "shiitake"},
        "shimeji": {"item": "shimeji"},
        "matsutake": {"item": "matsutake"},
        "morel": {"item": "morel"},
        "porcini": {"item": "porcini"},
        "soybeans": {"item": "soybean"},
        "red grapes": {"item": "red_grape"},
        "green grapes": {"item": "green_grape"},
        "baguettes": {"item": "baguette"},
        "baguette": {"item": "baguette"},
        "common mush": {"item": "common_mushroom"},
        "common mushroom": {"item": "common_mushroom"},
        "monarch mushroom": {"item": "monarch_mushroom"},
        "three-forked carrot": {"item": "three_forked_carrot"},
        "jewel pineapple": {"item": "jewel_pineapple"},
        "heart lemon": {"item": "heart_lemon"},
        "heart watermelon": {"item": "heart_watermelon"},
        "star potato": {"item": "star_potato"},
        "giant tomato": {"item": "giant_tomato"},
        "curled chili pepper": {"item": "curled_chili_pepper"},
        "green onion": {"item": "green_onion"},
        "napa cabbage": {"item": "napa_cabbage"},
        "bok choy": {"item": "bok_choy"},
        "fried tofu": {"item": "fried_tofu"},
        "fish cake": {"item": "fish_cake"},
        "cooked rice": {"item": "cooked_rice"},
        "hot coffee": {"item": "hot_coffee"},
        "coffee pack": {"item": "coffee_pack"},
        "black tea tin": {"item": "black_tea_tin"},
        "black tea": {"item": "black_tea"},
        "summer blend tea can": {"item": "summer_blend_tea_can"},
        "bottled chestnuts": {"item": "bottled_chestnuts"},
        "bottled walnuts": {"item": "bottled_walnuts"},
        "refined rice flour": {"item": "refined_rice_flour"},
        "buckwheat flour": {"item": "buckwheat_flour"},
        "soybean flour": {"item": "soybean_flour"},
        "herb pasta": {"item": "herb_pasta"},
        "penne pasta": {"item": "penne_pasta"},
        "sashimi": {"item": "sashimi"},
        "tempura": {"item": "tempura"},
        "omelet": {"item": "omelet"},
        "onigiri": {"item": "onigiri"},
        "mixed salad": {"item": "mixed_salad"},
        "chocolate": {"item": "chocolate"},
        "soy milk": {"item": "soy_milk"},
        "soy sauce": {"item": "soy_sauce"},
        "curry powder": {"item": "curry_powder"},
        "curry rice": {"item": "curry_rice"},
        "supreme curry": {"item": "supreme_curry"},
        "mochi": {"item": "mochi"},
        "urchin": {"item": "urchin"},
        "seaweed": {"item": "seaweed"},
        "miso": {"item": "miso"},
        "spice": {"item": "spice"},
        "vinegar": {"item": "vinegar"},
        "salt": {"item": "salt"},
        "pepper": {"item": "pepper"},
        "sugar": {"item": "sugar"},
        "walnut": {"item": "walnut"},
        "chestnut": {"item": "chestnut"},
        "cacao bean": {"item": "cacao_bean"},
        "ice cream": {"item": "ice_cream"},
        "cookies": {"item": "cookies"},
        "summer tea leaves": {"item": "summer_tea_leaves"},
        "pasta": {"item": "pasta"},
        "rice": {"item": "rice"},
        "tofu": {"item": "tofu"},
        "salmon": {"item": "salmon"},
        # parenthetical groups
        "(asparagus, carrot, potato, cabbage, cauliflower, or turnip)": {"family": "vegetable_b"},
        "(tofu, green onion, fried tofu, potato, or shimeji)": {"family": "tofu_miso"},
        "(eel or marbled eel)": {"family": "eel"},
        "(melon, strawberry, or tree fruit)": {"family": "fruit_a"},
        "(shiitake, pumpkin, eggplant, etc.)": {"family": "vegetable_e"},
        "(root veggie)": {"family": "vegetable_d"},
        "(assorted veggies)": {"family": "vegetable_c"},
        "(veggies or common mush)": {"family": "vegetable_c"},
        "vegetables (broccoli, carrot, etc.)": {"family": "vegetable_c"},
        "(sweetfish, yellow perch, etc.)": {"family": "fish_d"},
        "fish (sweetfish, yellow perch, etc.)": {"family": "fish_d"},
        "fish (black bass, grayling, etc.)": {"family": "fish_e"},
        "fish (char, masu trout, etc.)": {"family": "fish_a"},
        "(black bass, barbel steel, etc.)": {"family": "fish_e"},
        "(black bass, bighead carp, etc.)": {"family": "fish_e"},
        "(bluegill, killifish, etc.)": {"family": "fish_b"},
        "(dark chub, dace, sulipin, etc.)": {"family": "fish_c"},
        "2 herbs (chamomile, lavender, or mint)": {"family": "herb", "quantity": 2},
        "2 herbs (chamomile, lavender, or mint)": {"family": "herb", "quantity": 2},
    }

    # every item name is also an alias
    for iid, meta in items.items():
        aliases.setdefault(meta["name"].lower(), {"item": iid})
        aliases.setdefault(iid.replace("_", " "), {"item": iid})

    recipe_overrides = {
        "sashimi": {"fish": {"family": "fish_c"}},
        "fish_cake": {"fish": {"family": "fish_c"}},
        "shumai_dumplings": {"fish": {"family": "fish_b"}},
        "fish_and_chips": {"fish": {"family": "fish_a"}},
        "paella": {"(fish)": {"family": "fish_e"}, "fish": {"family": "fish_e"}},
        "warm_milk": {"milk": {"item": "milk"}},
        "honey_cake": {"honey": {"item": "honey"}},
        "cheese_bun": {"buffalo milk": {"item": "buffalo_milk"}},
        "herb_bread": {"herb butter": {"item": "herb_butter"}},
        "royal_milk_tea": {"milk+": {"item": "milk_plus"}},
        "happy_fruit_platter": {
            "(fruit)": {"family": "fruit_a"},
        },
        "chocolate_fondue": {"(fruit)": {"family": "fruit_b"}},
        "mixed_salad": {"1 additional crop": {"family": "vegetable_a"}},
        "vegetable_curry": {"(veggies)": {"family": "vegetable_a"}},
        "tomato_fondue": {"(veggies)": {"family": "vegetable_c"}},
        "toast": {"bread or white bread": {"family": "bread_toast"}},
        "french_toast": {"bread or white bread": {"family": "bread_toast"}},
    }

    # second fruit slot on happy platter is fruit B — handled in scraper by occurrence index
    payload = {
        "families": families,
        "items": items,
        "aliases": aliases,
        "recipe_overrides": recipe_overrides,
        "multi_slot_aliases": {
            "happy_fruit_platter": [
                {"raw_contains": "(fruit)", "family": "fruit_a"},
                {"raw_contains": "(fruit)", "family": "fruit_b"},
            ]
        },
    }
    out = Path("data/groups.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} items={len(items)} aliases={len(aliases)}")


if __name__ == "__main__":
    main()
