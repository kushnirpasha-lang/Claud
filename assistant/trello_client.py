import os
import requests

BASE = "https://api.trello.com/1"


def _auth():
    return {
        "key": os.environ["TRELLO_API_KEY"],
        "token": os.environ["TRELLO_TOKEN"],
    }


def get_boards() -> list[dict]:
    r = requests.get(f"{BASE}/members/me/boards", params={**_auth(), "fields": "name,id,closed"})
    r.raise_for_status()
    return [b for b in r.json() if not b.get("closed")]


def get_lists(board_id: str) -> list[dict]:
    r = requests.get(f"{BASE}/boards/{board_id}/lists", params={**_auth(), "fields": "name,id"})
    r.raise_for_status()
    return r.json()


def get_cards(board_id: str) -> list[dict]:
    r = requests.get(f"{BASE}/boards/{board_id}/cards", params={
        **_auth(), "fields": "name,idList,due,desc,shortUrl"
    })
    r.raise_for_status()
    return r.json()


def create_card(list_id: str, name: str, desc: str = "", due: str = "") -> dict:
    params = {**_auth(), "idList": list_id, "name": name}
    if desc:
        params["desc"] = desc
    if due:
        params["due"] = due
    r = requests.post(f"{BASE}/cards", params=params)
    r.raise_for_status()
    return r.json()


def move_card(card_id: str, list_id: str) -> dict:
    r = requests.put(f"{BASE}/cards/{card_id}", params={**_auth(), "idList": list_id})
    r.raise_for_status()
    return r.json()


def get_board_summary(board_id: str) -> str:
    """Returns a text summary of the board for Claude context."""
    lists = get_lists(board_id)
    cards = get_cards(board_id)

    list_map = {l["id"]: l["name"] for l in lists}
    lines = []
    for lst in lists:
        lst_cards = [c for c in cards if c["idList"] == lst["id"]]
        lines.append(f"\n[{lst['name']}] ({len(lst_cards)} карточек)")
        for c in lst_cards[:10]:
            due = f" | срок: {c['due'][:10]}" if c.get("due") else ""
            lines.append(f"  - {c['name']}{due} | {c['shortUrl']}")
    return "\n".join(lines)
