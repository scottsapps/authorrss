import os
import requests
from bs4 import BeautifulSoup
import trafilatura
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

WALLABAG_ENABLED = bool(os.environ.get("WALLABAG_CLIENT_ID"))
if WALLABAG_ENABLED:
    from wallabag import save_article

URL = "https://www.newyorker.com/contributors/isaac-chotiner"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def strip_html_wrappers(html):
    """Strip outer <html>, <head>, and <body> wrappers from extracted HTML."""
    html = re.sub(r"<!DOCTYPE[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"</?html[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<head[^>]*>.*?</head>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"</?body[^>]*>", "", html, flags=re.IGNORECASE)
    return html.strip()


def fetch_article_content(url):
    """Fetch an article URL and return cleaned HTML content via trafilatura.

    Returns empty string if the page cannot be fetched or parsed.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""

        html_content = trafilatura.extract(
            downloaded,
            output_format="html",
            include_formatting=True,
            include_links=True,
            include_images=True,
            no_fallback=False,
        )
        if html_content:
            return strip_html_wrappers(html_content)
        return ""
    except Exception as e:
        print(f"  Warning: could not fetch {url}: {e}")
        return ""


# --- Scrape contributor page for article links ---

try:
    response = requests.get(URL, headers=headers, timeout=15)
    response.raise_for_status()
except Exception as e:
    print(f"Error fetching contributor page: {e}")
    exit(1)

soup = BeautifulSoup(response.text, "html.parser")

articles = []
for link in soup.find_all("a", href=True):
    href = link["href"]
    if href.startswith("/") and any(href.startswith(p) for p in [
        "/magazine", "/news", "/culture", "/humor", "/science", "/politics", "/books"
    ]):
        title = link.get_text(strip=True)
        if title and len(title) > 20:
            full_url = "https://www.newyorker.com" + href
            if not any(a["url"] == full_url for a in articles):
                articles.append({"title": title, "url": full_url})

print(f"Found {len(articles)} article links. Fetching content...")

# --- Fetch full content and push to Wallabag ---

for i, article in enumerate(articles[:30]):
    print(f"  Fetching {i + 1}/{min(len(articles), 30)}: {article['title'][:60]}...")
    article["content"] = fetch_article_content(article["url"])

if WALLABAG_ENABLED:
    print("Pushing articles to Wallabag...")
    for article in articles[:30]:
        ok = save_article(article["url"], title=article["title"], content=article.get("content") or None)
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {article['title'][:60]}")
else:
    print("WALLABAG_CLIENT_ID not set — skipping Wallabag push.")
