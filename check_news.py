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


MONTHS = (
    "gennaio|febbraio|marzo|aprile|maggio|giugno|"
    "luglio|agosto|settembre|ottobre|novembre|dicembre"
)

DATE_PATTERN = re.compile(
    rf"\b(\d{{1,2}})\s+({MONTHS})\s+(\d{{4}})\b",
    re.IGNORECASE
)


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
                self.current_href = urljoin(PAGE_URL, href)
                self.current_text = []

    def handle_data(self, data):

        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):

        if tag == "a" and self.current_href:

            text = " ".join(
                " ".join(self.current_text).split()
            )

            self.links.append({
                "text": text,
                "url": self.current_href
            })

            self.current_href = None
            self.current_text = []


def get_page():

    request = urllib.request.Request(
        PAGE_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="ignore"
        )


def get_news():

    html = get_page()

    parser = NewsParser()
    parser.feed(html)

    # Troviamo tutte le date presenti nella pagina.
    dates = list(
        DATE_PATTERN.finditer(html)
    )

    if not dates:

        print("ERRORE: nessuna data trovata.")
        return []

    print("DATE TROVATE:")

    for match in dates[:20]:
        print(
            " -",
            match.group(0)
        )

    news = []

    # Le date compaiono due volte:
    # una volta come data dell'articolo
    # e una volta vicino a "Leggi di più".
    #
    # Prendiamo quindi solo le date che hanno
    # un link "Leggi di più" nelle vicinanze.

    for match in dates:

        date_text = match.group(0)

        # Porzione di HTML successiva alla data.
        start = match.end()

        nearby = html[start:start + 3000]

        # Cerchiamo "Leggi di più".
        leggi = re.search(
            r'Leggi\s+di\s+più',
            nearby,
            re.IGNORECASE
        )

        if not leggi:
            continue

        # Cerchiamo il primo href dopo la data.
        href_match = re.search(
            r'href=["\']([^"\']+)["\']',
            nearby[:leggi.end() + 500],
            re.IGNORECASE
        )

        if not href_match:
            continue

        url = urljoin(
            PAGE_URL,
            href_match.group(1)
        )

        # Evitiamo duplicati.
        if any(
            item["url"] == url
            for item in news
        ):
            continue

        news.append({
            "date": date_text,
            "url": url
        })

    return news


def date_key(date_text):

    months = {
        "gennaio": 1,
        "febbraio": 2,
        "marzo": 3,
        "aprile": 4,
        "maggio": 5,
        "giugno": 6,
        "luglio": 7,
        "agosto": 8,
        "settembre": 9,
        "ottobre": 10,
        "novembre": 11,
        "dicembre": 12
    }

    match = DATE_PATTERN.search(
        date_text
    )

    if not match:
        return (0, 0, 0)

    day = int(match.group(1))
    month = months[
        match.group(2).lower()
    ]
    year = int(match.group(3))

    return (
        year,
        month,
        day
    )


def load_state():

    if not os.path.exists(
        STATE_FILE
    ):
        return None

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_state(news):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            news,
            f,
            ensure_ascii=False,
            indent=2
        )


def send_email(news):

    message = EmailMessage()

    message["Subject"] = (
        f"Nuova notizia Americisss: "
        f"{news['date']}"
    )

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

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465
    ) as smtp:

        smtp.login(
            GMAIL_USERNAME,
            GMAIL_APP_PASSWORD
        )

        smtp.send_message(
            message
        )


def main():

    news = get_news()

    if not news:

        print(
            "ERRORE: nessuna notizia identificata."
        )

        return

    # Ordina dalla più recente alla più vecchia.
    news.sort(
        key=lambda item: date_key(
            item["date"]
        ),
        reverse=True
    )

    latest = news[0]

    print("")
    print("ULTIMA NEWS:")
    print(
        "Data:",
        latest["date"]
    )
    print(
        "Link:",
        latest["url"]
    )

    previous = load_state()

    # Prima esecuzione:
    # memorizziamo la news attuale senza inviare email.
    if previous is None:

        print(
            "Prima esecuzione: "
            "salvo lo stato senza inviare email."
        )

        save_state(
            latest
        )

        return

    # Controlliamo data + URL.
    if (
        latest["date"] == previous.get("date")
        and
        latest["url"] == previous.get("url")
    ):

        print(
            "Nessuna nuova notizia."
        )

        return

    print(
        "NUOVA NOTIZIA TROVATA!"
    )

    send_email(
        latest
    )

    save_state(
        latest
    )

    print(
        "Email inviata."
    )


if __name__ == "__main__":
    main()
