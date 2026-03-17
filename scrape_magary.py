import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET

URL = "https://www.sfgate.com/author/drew-magary/"
FEED_FILE = "magary-feed.xml"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

articles = []
for link in soup.find_all("a", href=True):
    href = link["href"]
    if "sfgate.com" in href or href.startswith("/"):
        if href.startswith("/"):
            href = "https://www.sfgate.com" + href
        title = link.get_text(strip=True)
        if title and len(title) > 20:
            if not any(a["url"] == href for a in articles):
                articles.append({"title": title, "url": href})

# Build RSS XML
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "Drew Magary — SFGate"
ET.SubElement(channel, "link").text = URL
ET.SubElement(channel, "description").text = "Articles by Drew Magary on SFGate"
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
