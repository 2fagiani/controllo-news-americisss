import json
import os
import re
import smtplib
import urllib.request
from email.message import EmailMessage
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


PAGE_URL = "https://www.americisss.it/news/"
STATE_FILE = "last_news.json"

GMAIL_USERNAME = os.environ["GMAIL_USERNAME"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT = "2fagiani@gmail.com"


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
                self.links.append(
                    (
                        text,
                        urljoin(PAGE_URL, self.current_href)
                    )
                )

            self.current_href = None
            self.current_text = []


def get_news():
    request = urllib.request.Request(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = NewsParser()
    parser.feed(html)

    result = []
    seen = set()

    for title, url in parser.links:
        parsed = urlparse(url)

        # Deve essere una pagina del sito
        if parsed.netloc not in ("www.americisss.it", "americisss.it"):
            continue

        # Ignora ancore (#content, #menu, ecc.)
        if parsed.fragment:
            continue

        # Ignora la pagina principale delle news
        if url.rstrip("/") == PAGE_URL.rstrip("/"):
            continue

        # Ignora link generici del sito
        ignored = [
            "contatti",
            "privacy",
            "cookie",
            "login",
            "accessibilita",
            "accessibilità"
        ]

        title_lower = title.lower()

        if any(word in title_lower for word in ignored):
            continue

        # Titoli troppo brevi non sono probabilmente notizie
        if len(title.strip()) < 10:
            continue

        if url not in seen:
            seen.add(url)

            result.append({
                "title": title.strip(),
                "url": url
            })

    return result


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(news):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def send_email(news):
    message = EmailMessage()

    message["Subject"] = "Nuova notizia su Americisss"
    message["From"] = GMAIL_USERNAME
    message["To"] = RECIPIENT

    message.set_content(
        f"""È stata pubblicata una nuova notizia sul sito Americisss.

Titolo:
{news["title"]}

Link:
{news["url"]}

Pagina News:
{PAGE_URL}
"""
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USERNAME, GMAIL_APP_PASSWORD)
        smtp.send_message(message)


def main():
    news = get_news()

    if not news:
        print("Nessuna notizia trovata.")
        return

    latest = news[0]

    print("Ultima notizia trovata:")
    print(latest["title"])
    print(latest["url"])

    previous = load_state()

    if previous is None:
        print("Prima esecuzione: salvo lo stato senza inviare email.")
        save_state(latest)
        return

    if latest["url"] == previous["url"]:
        print("Nessuna nuova notizia.")
        return

    print("NUOVA NOTIZIA TROVATA!")

    send_email(latest)
    save_state(latest)

    print("Email inviata.")


if __name__ == "__main__":
    main()
