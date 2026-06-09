import os
import shutil
import json

from .pull_items_wiki import WikiItem, get_item_urls
from .pull_items_dragon import DragonItem
from collections import OrderedDict

def main():
    directory = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))
    if not os.path.exists(os.path.join(directory, "items")):
        os.mkdir(os.path.join(directory, "items"))

    if os.path.exists(os.path.join(directory, "__wiki__")):
        shutil.rmtree(os.path.join(directory, "__wiki__"))

    if not os.path.exists(os.path.join(directory, "__wiki__")):
        os.mkdir(os.path.join(directory, "__wiki__"))
    cdragon = DragonItem.get_cdragon()
    wikiItems = get_item_urls(False)

    jsons = {}
    for name,data in wikiItems.items():
        item = None
        if "id" in data:
          print(data["id"], name)
        else: 
          print(name)
        l = [x for x in cdragon if "id" in data and x["id"] == data["id"]]

        for i in l:

            try:
                cdrag_item = DragonItem.get_item_cdragon(i)
            except Exception as e:
                # Resilience: a transient CDragon fetch (e.g. a non-JSON response
                # for a single item) must not abort the entire items scrape.
                print(f"SKIP-AND-WARN: item '{name}' ({data.get('id')}) cdragon fetch failed: {type(e).__name__}: {e}")
                continue
            wiki_item = WikiItem._parse_item_data(data,name,wikiItems)
            item = wiki_item
            item.icon = cdrag_item.icon
            item.id = int(cdrag_item.id)
            item.builds_from = cdrag_item.builds_from
            item.builds_into = cdrag_item.builds_into
            item.simple_description = cdrag_item.simple_description
            item.required_ally = cdrag_item.required_ally
            item.required_champion = cdrag_item.required_champion
            item.shop.purchasable = cdrag_item.shop.purchasable
            item.special_recipe = cdrag_item.special_recipe
            if item.iconOverlay == True:
                item.iconOverlay = (
                    "http://raw.communitydragon.org/latest/game/data/items/icons2d/bordertreatmentornn.png"
                )
            else:
                item.iconOverlay = False
            if item is not None:
                jsonfn = os.path.join(directory, "items", str(item.id) + ".json")
                with open(jsonfn, "w", encoding="utf8") as f:
                    j = item.__json__(indent=2, ensure_ascii=False)
                    f.write(j)
                jsons[int(item.id)] = json.loads(item.__json__(ensure_ascii=False))
    if os.path.exists(os.path.join(directory, "__wiki__")):
        shutil.rmtree(os.path.join(directory, "__wiki__"))

    # Combine cost (recipe gold): the wiki only provides the total `buy` price,
    # so the parser left `combined` at 0. Derive it the way the in-game shop
    # does — total minus the totals of the components the item builds from (a
    # base component with no recipe is its own combine cost). Post-pass because
    # all component prices are only known once every item is parsed.
    item_totals = {
        iid: ((it.get("shop") or {}).get("prices") or {}).get("total", 0)
        for iid, it in jsons.items()
    }
    for it in jsons.values():
        prices = (it.get("shop") or {}).get("prices")
        if not prices:
            continue
        components = it.get("buildsFrom") or []
        prices["combined"] = max(
            0, prices.get("total", 0) - sum(item_totals.get(c, 0) for c in components)
        )

    # Sanity gate: if the scrape produced far too few items, a transient CDragon/
    # network failure (or rate-limit) skipped most of them. Abort non-zero BEFORE
    # writing, so a near-empty items.json is never written over good data or
    # uploaded by the publish step. League always has well over 200 items.
    if len(jsons) < 200:
        raise SystemExit(
            f"FATAL: only {len(jsons)} items parsed (expected ~320+) — likely a "
            "transient CDragon/network failure or rate-limit. Aborting before write."
        )

    jsonfn = os.path.join(directory, "items.json")
    jsons = OrderedDict(sorted(jsons.items(), key=lambda x: x[1]["id"]))
    with open(jsonfn, "w", encoding="utf8") as f:
        json.dump(jsons, f, indent=2, ensure_ascii=False)
    del jsons


if __name__ == "__main__":
    main()
    print("Hello! What a surprise, it worked!")
