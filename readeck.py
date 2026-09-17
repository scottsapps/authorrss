import os
import requests

READECK_URL = "https://read.angstreich.net"


def save_article(url, title=None, content=None):
    """Save an article to Readeck. Returns True on success, False on failure."""
    try:
        payload = {"url": url}
        if title:
            payload["title"] = title
        if content:
            payload["html"] = content

        resp = requests.post(
            f"{READECK_URL}/api/bookmarks",
            json=payload,
            headers={"Authorization": f"Bearer {os.environ['READECK_API_TOKEN']}"},
            timeout=15,
        )
        # 202 = accepted, Readeck processes the bookmark asynchronously
        if resp.status_code == 202:
            return True
        print(f"  Readeck error {resp.status_code} for {url}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"  Readeck exception for {url}: {e}")
        return False
