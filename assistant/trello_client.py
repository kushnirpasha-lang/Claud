import os
import time
import requests

BASE = "https://api.trello.com/1"

# Board state cache — refresh every 5 minutes
_cache: dict = {}
_cache_ts: float = 0
_CACHE_TTL = 300


def _auth():
    return {
        "key": os.environ["TRELLO_API_KEY"],
        "token": os.environ["TRELLO_TOKEN"],
    }


def board_id() -> str:
    return os.environ.get("TRELLO_BOARD_ID", "")


def get_boards() -> list[dict]:
    r = requests.get(f"{BASE}/members/me/boards", params={**_auth(), "fields": "name,id,closed"}, timeout=10)
    r.raise_for_status()
    return [b for b in r.json() if not b.get("closed")]


def _fetch_board() -> dict:
    bid = board_id()
    lists_r = requests.get(f"{BASE}/boards/{bid}/lists", params={**_auth(), "fields": "name,id"}, timeout=10)
    cards_r = requests.get(f"{BASE}/boards/{bid}/cards", params={
        **_auth(), "fields": "name,idList,due,desc,shortUrl,id"
    }, timeout=10)
    lists_r.raise_for_status()
    cards_r.raise_for_status()
    return {"lists": lists_r.json(), "cards": cards_r.json()}


def get_board_data(force: bool = False) -> dict:
    global _cache, _cache_ts
    if force or not _cache or time.time() - _cache_ts > _CACHE_TTL:
        _cache = _fetch_board()
        _cache_ts = time.time()
    return _cache


def invalidate_cache():
    global _cache_ts
    _cache_ts = 0


def get_board_summary(force: bool = False) -> str:
    data = get_board_data(force)
    lists = data["lists"]
    cards = data["cards"]
    list_map = {l["id"]: l["name"] for l in lists}
    lines = []
    for lst in lists:
        lst_cards = [c for c in cards if c["idList"] == lst["id"]]
        lines.append(f"\n[{lst['name']}] ({len(lst_cards)} карточек)")
        for c in lst_cards:
            due = f" | срок: {c['due'][:10]}" if c.get("due") else ""
            lines.append(f"  - {c['name']}{due} | id:{c['id'][:8]}")
    return "\n".join(lines)


def create_card(list_name: str, name: str, desc: str = "", due: str = "") -> dict:
    data = get_board_data()
    lst = next((l for l in data["lists"] if list_name.lower() in l["name"].lower()), None)
    if not lst:
        lst = data["lists"][0]
    params = {**_auth(), "idList": lst["id"], "name": name}
    if desc:
        params["desc"] = desc
    if due:
        params["due"] = due
    r = requests.post(f"{BASE}/cards", params=params, timeout=10)
    r.raise_for_status()
    invalidate_cache()
    return r.json()


def move_card(card_name: str, to_list_name: str) -> bool:
    data = get_board_data()
    card = next((c for c in data["cards"] if card_name.lower() in c["name"].lower()), None)
    lst = next((l for l in data["lists"] if to_list_name.lower() in l["name"].lower()), None)
    if not card or not lst:
        return False
    r = requests.put(f"{BASE}/cards/{card['id']}", params={**_auth(), "idList": lst["id"]}, timeout=10)
    r.raise_for_status()
    invalidate_cache()
    return True


def delete_card(card_name: str) -> bool:
    data = get_board_data()
    card = next((c for c in data["cards"] if card_name.lower() in c["name"].lower()), None)
    if not card:
        return False
    r = requests.delete(f"{BASE}/cards/{card['id']}", params=_auth(), timeout=10)
    r.raise_for_status()
    invalidate_cache()
    return True
