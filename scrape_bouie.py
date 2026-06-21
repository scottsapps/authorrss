import os
import re
import requests
from bs4 import BeautifulSoup
import trafilatura

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

WALLABAG_ENABLED = bool(os.environ.get("WALLABAG_CLIENT_ID"))
if WALLABAG_ENABLED:
    from wallabag import save_article

AUTHOR_URL = "https://www.nytimes.com/by/jamelle-bouie"

# A logged-in NYT subscriber cookie is required to fetch full article text past
# the paywall. Provide it via the NYT_COOKIE env var / GitHub Actions secret as
# the raw Cookie header string copied from a signed-in browser session.
NYT_COOKIE = os.environ.get("NYT_COOKIE", "")

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
if NYT_COOKIE:
    headers["Cookie"] = NYT_COOKIE

# NYT article paths look like /2026/06/18/opinion/slug.html
ARTICLE_PATH_RE = re.compile(r"^/20\d{2}/\d{2}/\d{2}/.+\.html$")


def strip_html_wrappers(html):
    """Strip outer <html>, <head>, and <body> wrappers from extracted HTML."""
    html = re.sub(r"<!DOCTYPE[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"</?html[^>]*>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<head[^>]*>.*?</head>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"</?body[^>]*>", "", html, flags=re.IGNORECASE)
    return html.strip()


def fetch_article_content(url):
    """Fetch a NYT article (with subscriber cookie) and return cleaned HTML.

    Returns empty string if the page cannot be fetched or parsed.
    """
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        html_content = trafilatura.extract(
            resp.text,
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


# --- Scrape author page for article links ---

if not NYT_COOKIE:
    print("Warning: NYT_COOKIE not set — full text will likely be paywalled.")

try:
    response = requests.get(AUTHOR_URL, headers=headers, timeout=20)
    response.raise_for_status()
except Exception as e:
    print(f"Error fetching author page: {e}")
    exit(1)

soup = BeautifulSoup(response.text, "html.parser")

articles = []
for link in soup.find_all("a", href=True):
    href = link["href"].split("?")[0].split("#")[0]
    # Normalize absolute NYT URLs to a leading path for matching.
    path = href
    if href.startswith("https://www.nytimes.com"):
        path = href[len("https://www.nytimes.com"):]
    if not ARTICLE_PATH_RE.match(path):
        continue

    full_url = "https://www.nytimes.com" + path
    title = link.get_text(strip=True)
    if not any(a["url"] == full_url for a in articles):
        articles.append({"title": title, "url": full_url})

print(f"Found {len(articles)} article links by Jamelle Bouie. Fetching content...")

# --- Fetch full content and push to Wallabag ---

for i, article in enumerate(articles[:30]):
    print(f"  Fetching {i + 1}/{min(len(articles), 30)}: {(article['title'] or article['url'])[:60]}...")
    article["content"] = fetch_article_content(article["url"])

if WALLABAG_ENABLED:
    print("Pushing articles to Wallabag...")
    for article in articles[:30]:
        ok = save_article(
            article["url"],
            title=article["title"] or None,
            content=article.get("content") or None,
        )
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {(article['title'] or article['url'])[:60]}")
else:
    print("WALLABAG_CLIENT_ID not set — skipping Wallabag push.")
