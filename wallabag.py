import os
import requests

WALLABAG_URL = "https://read.angstreich.net"
_token_cache = {}


def _get_token():
    if _token_cache.get("token"):
        return _token_cache["token"]

    resp = requests.post(
        f"{WALLABAG_URL}/oauth/v2/token",
        json={
            "grant_type": "password",
            "client_id": os.environ["WALLABAG_CLIENT_ID"],
            "client_secret": os.environ["WALLABAG_CLIENT_SECRET"],
            "username": os.environ["WALLABAG_USERNAME"],
            "password": os.environ["WALLABAG_PASSWORD"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    _token_cache["token"] = resp.json()["access_token"]
    return _token_cache["token"]


def save_article(url, title=None, content=None):
    """Save an article to Wallabag. Returns True on success, False on failure."""
    try:
        token = _get_token()
        payload = {"url": url}
        if title:
            payload["title"] = title
        if content:
            payload["content"] = content

        resp = requests.post(
            f"{WALLABAG_URL}/api/entries.json",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        # 200 = created, 304 = already exists (both are fine)
        if resp.status_code in (200, 304):
            return True
        print(f"  Wallabag error {resp.status_code} for {url}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"  Wallabag exception for {url}: {e}")
        return False
