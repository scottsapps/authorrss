import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from html import escape
import trafilatura
from trafilatura.metadata import extract_metadata as trafilatura_metadata
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
FEED_FILE = "chotiner-feed.xml"

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
    """Fetch an article URL and return (pub_date_str, html_content) via trafilatura.

    Returns (None, None) if the page cannot be fetched or parsed.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None, None

        html_content = trafilatura.extract(
            downloaded,
            output_format="html",
            include_formatting=True,
            include_links=True,
            include_images=True,
            no_fallback=False,
        )
        if html_content:
            html_content = strip_html_wrappers(html_content)

        pub_date = None
        try:
            meta = trafilatura_metadata(downloaded)
            if meta and meta.date:
                pub_date = meta.date
        except Exception:
            pass

        return pub_date, html_content
    except Exception as e:
        print(f"  Warning: could not fetch {url}: {e}")
        return None, None


def make_description(html_content, max_len=300):
    """Extract a plain-text excerpt from HTML content."""
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def format_rfc2822(date_str):
    """Convert a YYYY-MM-DD date string to RFC 2822 format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except Exception:
        return None


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

# --- Fetch full content for each article ---

for i, article in enumerate(articles[:30]):
    print(f"  Fetching {i + 1}/{min(len(articles), 30)}: {article['title'][:60]}...")
    pub_date, html_content = fetch_article_content(article["url"])
    article["pub_date"] = pub_date
    article["content"] = html_content or ""
    article["description"] = make_description(article["content"]) if article["content"] else ""

# --- Build RSS XML ---

now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

item_blocks = []
for article in articles[:30]:
    pub_date_xml = ""
    if article.get("pub_date"):
        rfc_date = format_rfc2822(article["pub_date"])
        if rfc_date:
            pub_date_xml = f"\n      <pubDate>{rfc_date}</pubDate>"

    desc = escape(article.get("description", ""))
    content = article.get("content", "")

    item_blocks.append(
        f"""    <item>
      <title>{escape(article['title'])}</title>
      <link>{escape(article['url'])}</link>
      <guid isPermaLink="true">{escape(article['url'])}</guid>{pub_date_xml}
      <author>Isaac Chotiner</author>
      <description>{desc}</description>
      <content:encoded><![CDATA[{content}]]></content:encoded>
    </item>"""
    )

items_xml = "\n".join(item_blocks)

rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Isaac Chotiner — The New Yorker</title>
    <link>{escape(URL)}</link>
    <description>Articles by Isaac Chotiner in The New Yorker</description>
    <lastBuildDate>{now_rfc}</lastBuildDate>
{items_xml}
  </channel>
</rss>"""

with open(FEED_FILE, "w", encoding="utf-8") as f:
    f.write(rss_xml)

print(f"Feed written with {min(len(articles), 30)} articles.")

# --- Push to Wallabag ---

if WALLABAG_ENABLED:
    print("Pushing articles to Wallabag...")
    for article in articles[:30]:
        ok = save_article(article["url"], title=article["title"], content=article.get("content") or None)
        status = "OK" if ok else "FAILED"
        print(f"  [{status}] {article['title'][:60]}")
else:
    print("WALLABAG_CLIENT_ID not set — skipping Wallabag push.")
