import json
import os
import urllib.request
from html.parser import HTMLParser

URL = "https://www.americisss.it/news/"
STATE_FILE = "last_news.json"


class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            href = attrs.get("href")
            if href:
                self.current_href = href
                self.current_text = []

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_href:
            text = " ".join(" ".join(self.current_text).split())
            if text:
                self.links.append((text, self.current_href))
            self.current_href = None
            self.current_text = []


def get_news():
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = NewsParser()
    parser.feed(html)

    # Prendiamo i link che sembrano appartenere alle notizie
    news = []
    for title, link in parser.links:
        if link.startswith("/"):
            link = "https://www.americisss.it" + link

        if "americisss.it" in link and title:
            news.append({
                "title": title,
                "url": link
            })

    # elimina duplicati
    unique = []
    seen = set()

    for item in news:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)

    return unique


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(item):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(item, f, ensure_ascii=False, indent=2)


news = get_news()

if not news:
    print("Nessuna notizia trovata.")
    exit(0)

latest = news[0]
previous = load_state()

print("Ultima notizia:", latest)

if previous is None:
    print("Prima esecuzione: salvo lo stato senza inviare email.")
    save_state(latest)

elif latest["url"] != previous["url"]:
    print("NUOVA NOTIZIA!")
    print(latest["title"])
    print(latest["url"])

    # L'invio email verrà aggiunto nel prossimo passo.
    save_state(latest)

else:
    print("Nessuna nuova notizia.")
