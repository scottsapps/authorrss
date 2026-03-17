import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
import os

URL = "https://www.newyorker.com/contributors/isaac-chotiner"
FEED_FILE = "feed.xml"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

articles = []
for link in soup.find_all("a", href=True):
    href = link["href"]
    # New Yorker articles have paths like /magazine/... or /news/...
    if href.startswith("/") and any(href.startswith(p) for p in [
        "/magazine", "/news", "/culture", "/humor", "/science", "/politics", "/books"
    ]):
        title = link.get_text(strip=True)
        if title and len(title) > 20:  # skip nav links etc
            full_url = "https://www.newyorker.com" + href
            if not any(a["url"] == full_url for a in articles):
                articles.append({"title": title, "url": full_url})

# Build RSS XML
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "Isaac Chotiner — The New Yorker"
ET.SubElement(channel, "link").text = URL
ET.SubElement(channel, "description").text = "Articles by Isaac Chotiner in The New Yorker"
ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

for article in articles[:30]:
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = article["title"]
    ET.SubElement(item, "link").text = article["url"]
    ET.SubElement(item, "guid").text = article["url"]

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ")
tree.write(FEED_FILE, encoding="unicode", xml_declaration=True)
print(f"Feed written with {len(articles)} articles.")
