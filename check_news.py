import json
import os
import re
import smtplib
import urllib.request
from email.message import EmailMessage
from html.parser import HTMLParser
from urllib.parse import urljoin

PAGE_URL = "https://www.americisss.it/news/"
STATE_FILE = "last_news.json"

GMAIL_USERNAME = os.environ["GMAIL_USERNAME"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT = "2fagiani@gmail.com"


class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_heading = False
        self.current_heading = []
        self.current_href = None
        self.current_link_text = []
        self.articles = []
        self.current_article = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # I titoli delle news sono heading H2
        if tag == "h2":
            self.in_heading = True
            self.current_heading = []

        # Memorizziamo il link "Leggi di più"
        if tag == "a":
            href = attrs.get("href")

            if href:
                self.current_href = urljoin(PAGE_URL, href)
                self.current_link_text = []

    def handle_data(self, data):
        text = " ".join(data.split())

        if self.in_heading and text:
            self.current_heading.append(text)

        if self.current_href and text:
            self.current_link_text.append(text)

    def handle_endtag(self, tag):
        if tag == "h2":
            title = " ".join(self.current_heading).strip()

            # Le date delle news hanno questa forma:
            # 23 agosto 2026
            if re.match(
                r"^\d{1,2}\s+"
                r"(gennaio|febbraio|marzo|aprile|maggio|giugno|"
                r"luglio|agosto|settembre|ottobre|novembre|dicembre)"
                r"\s+\d{4}$",
                title,
                re.IGNORECASE
            ):
                self.current_article = {
                    "date": title,
                    "url": None
                }

            self.in_heading = False
            self.current_heading = []

        if tag == "a" and self.current_href:
            link_text = " ".join(self.current_link_text).strip()

            if (
                self.current_article
                and link_text.lower() == "leggi di più"
            ):
                self.current_article["url"] = self.current_href
                self.articles.append(self.current_article)
                self.current_article = None

            self.current_href = None
            self.current_link_text = []


def get_news():
    request = urllib.request.Request(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")

    parser = NewsParser()
    parser.feed(html)

    return parser.articles


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

    message["Subject"] = f"Nuova notizia Americisss: {news['date']}"
    message["From"] = GMAIL_USERNAME
    message["To"] = RECIPIENT

    message.set_content(
        f"""È stata pubblicata una nuova notizia sul sito Americisss.

Data:
{news["date"]}

Link alla notizia:
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
        print("ERRORE: nessuna notizia trovata.")
        return

    latest = news[0]

    print("Ultima notizia:")
    print(f"Data: {latest['date']}")
    print(f"Link: {latest['url']}")

    previous = load_state()

    if previous is None:
        print("Prima esecuzione: salvo lo stato senza inviare email.")
        save_state(latest)
        return

    if (
        latest["date"] == previous["date"]
        and latest["url"] == previous["url"]
    ):
        print("Nessuna nuova notizia.")
        return

    print("NUOVA NOTIZIA TROVATA!")

    send_email(latest)
    save_state(latest)

    print("Email inviata.")


if __name__ == "__main__":
    main()
