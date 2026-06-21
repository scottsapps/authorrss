import os
import requests
import xml.etree.ElementTree as ET
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

FEEDS = [
    "https://www.sfgate.com/rss/feed/business-and-technology-news-448.php",
    "https://www.sfgate.com/rss/feed/culture-530.php",
    "https://www.sfgate.com/rss/feed/food-dining-550.php",
    "https://www.sfgate.com/rss/feed/top-sports-stories-rss-feed-487.php",
]

AUTHOR = "drew magary"

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

    SFGate is heavily JavaScript-dependent, so letting Wallabag fetch the bare
    URL yields a "required part of this site couldn't load" shell. We extract
    the article text ourselves and hand the content to Wallabag instead.

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


# --- Collect articles from SFGate RSS feeds ---

articles = []

for feed_url in FEEDS:
    try:
        response = requests.get(feed_url, headers=headers, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        channel = root.find("channel")
        if channel is None:
            continue
        for item in channel.findall("item"):
            # Check all possible author fields
            author = ""
            author_el = item.find("author")
            if author_el is not None and author_el.text:
                author = author_el.text.lower()
            # Also check dc:creator
            dc_creator = item.find("{http://purl.org/dc/elements/1.1/}creator")
            if dc_creator is not None and dc_creator.text:
                author = dc_creator.text.lower()

            if AUTHOR in author:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()

                if link and not any(a["url"] == link for a in articles):
                    articles.append({"title": title, "url": link})
    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")

print(f"Found {len(articles)} articles by {AUTHOR}. Fetching content...")

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
