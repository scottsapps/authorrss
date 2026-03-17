import requests
import xml.etree.ElementTree as ET
from datetime import datetime

FEEDS = [
    "https://www.sfgate.com/rss/feed/business-and-technology-news-448.php",
    "https://www.sfgate.com/rss/feed/culture-530.php",
    "https://www.sfgate.com/rss/feed/food-dining-550.php",
    "https://www.sfgate.com/rss/feed/top-sports-stories-rss-feed-487.php",
]

AUTHOR = "drew magary"
FEED_FILE = "magary-feed.xml"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

articles = []

for feed_url in FEEDS:
    try:
        response = requests.get(feed_url, headers=headers, timeout=10)
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
                pub_date = item.findtext("pubDate", "").strip()
                guid = item.findtext("guid", link).strip()

                if link and not any(a["url"] == link for a in articles):
                    articles.append({
                        "title": title,
                        "url": link,
                        "pub_date": pub_date,
                        "guid": guid,
                    })
    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")

# Build RSS XML
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "Drew Magary — SFGate"
ET.SubElement(channel, "link").text = "https://www.sfgate.com/author/drew-magary/"
ET.SubElement(channel, "description").text = "Articles by Drew Magary on SFGate"
ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

for article in articles[:30]:
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = article["title"]
    ET.SubElement(item, "link").text = article["url"]
    ET.SubElement(item, "guid").text = article["guid"]
    if article["pub_date"]:
        ET.SubElement(item, "pubDate").text = article["pub_date"]

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ")
tree.write(FEED_FILE, encoding="unicode", xml_declaration=True)
print(f"Feed written with {len(articles)} articles.")
