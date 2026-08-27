import json
import os
import re
import smtplib
import urllib.request
from email.message import EmailMessage

PAGE_URL = "https://www.americisss.it/news/"
STATE_FILE = "last_news.json"

GMAIL_USERNAME = os.environ["GMAIL_USERNAME"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT = "2fagiani@gmail.com"

MONTHS = {
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
    "dicembre": 12,
}

DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+"
    r"(gennaio|febbraio|marzo|aprile|maggio|giugno|"
    r"luglio|agosto|settembre|ottobre|novembre|dicembre)"
    r"\s+(\d{4})\b",
    re.IGNORECASE
)


def get_page():

    request = urllib.request.Request(
        PAGE_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return response.read().decode(
            "utf-8",
            errors="ignore"
        )


def get_latest_date():

    html = get_page()

    dates = DATE_PATTERN.findall(html)

    if not dates:
        print("ERRORE: nessuna data trovata nella pagina.")
        return None

    found = []

    for day, month, year in dates:

        date_string = f"{day} {month} {year}"

        date_value = (
            int(year),
            MONTHS[month.lower()],
            int(day)
        )

        found.append(
            (date_value, date_string)
        )

    # Prende la data più recente
    found.sort(
        reverse=True
    )

    latest = found[0][1]

    print("Date trovate:")

    for _, date in found[:10]:
        print(" -", date)

    print("")
    print("ULTIMA DATA:", latest)

    return latest


def load_state():

    if not os.path.exists(STATE_FILE):
        return None

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_state(date):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {"date": date},
            file,
            ensure_ascii=False,
            indent=2
        )


def send_email(date):

    message = EmailMessage()

    message["Subject"] = (
        f"Nuova notizia su Americisss: {date}"
    )

    message["From"] = GMAIL_USERNAME
    message["To"] = RECIPIENT

    message.set_content(
        f"""È stata pubblicata una nuova notizia
sulla pagina News di Americisss.

Data della nuova notizia:
{date}

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

    latest_date = get_latest_date()

    if latest_date is None:
        return

    previous = load_state()

    # Prima esecuzione
    if previous is None:

        print(
            "Prima esecuzione: salvo la data "
            "senza inviare email."
        )

        save_state(latest_date)
        return

    previous_date = previous.get("date")

    print(
        "Data precedente:",
        previous_date
    )

    # Nessuna novità
    if latest_date == previous_date:

        print(
            "Nessuna nuova notizia."
        )

        return

    # Nuova data
    print(
        "NUOVA NOTIZIA TROVATA!"
    )

    send_email(
        latest_date
    )

    save_state(
        latest_date
    )

    print(
        "Email inviata."
    )


if __name__ == "__main__":
    main()
