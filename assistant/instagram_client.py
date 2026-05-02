import os
import requests

BASE = "https://graph.instagram.com/v21.0"


def _token():
    return os.environ["INSTAGRAM_ACCESS_TOKEN"]


def _user_id():
    return os.environ["INSTAGRAM_USER_ID"]


def post_photo(image_url: str, caption: str = "") -> dict:
    """Publish a photo to Instagram. image_url must be publicly accessible."""
    uid = _user_id()

    # Step 1: create media container
    r = requests.post(
        f"{BASE}/{uid}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": _token(),
        },
        timeout=30,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    # Step 2: publish
    r2 = requests.post(
        f"{BASE}/{uid}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": _token(),
        },
        timeout=30,
    )
    r2.raise_for_status()
    return r2.json()


def post_reel(video_url: str, caption: str = "") -> dict:
    """Publish a Reel to Instagram. video_url must be publicly accessible."""
    uid = _user_id()

    r = requests.post(
        f"{BASE}/{uid}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": _token(),
        },
        timeout=30,
    )
    r.raise_for_status()
    container_id = r.json()["id"]

    r2 = requests.post(
        f"{BASE}/{uid}/media_publish",
        params={
            "creation_id": container_id,
            "access_token": _token(),
        },
        timeout=60,
    )
    r2.raise_for_status()
    return r2.json()


def get_account_info() -> dict:
    r = requests.get(
        f"{BASE}/{_user_id()}",
        params={
            "fields": "username,media_count,followers_count",
            "access_token": _token(),
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()
