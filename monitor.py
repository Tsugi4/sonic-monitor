```python
import json
import os
import requests
import re
from bs4 import BeautifulSoup


DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
DATA_FILE = "seen_products.json"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/140.0.0.0 Safari/537.36"
}


def send_discord(message):
    response = requests.post(
        DISCORD_WEBHOOK,
        json={"content": message},
        timeout=30
    )

    print(f"Discord: {response.status_code}")

    if response.status_code not in (200, 204):
        print("Discord message failed.")


def load_seen():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            seen = json.load(f)
    else:
        seen = {
            "banba": [],
            "arnotts": []
        }

    return seen


def save_seen(seen):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def check_banba():
    products = set()

    url = (
        "https://banbatoys.ie/search?sort_by=relevance&q=Sonic"
        "&type=product&filter.v.availability=1"
        "&filter.v.price.gte=&filter.v.price.lte="
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print(f"Banba page 1: {response.status_code}")

    if response.status_code != 200:
        print("Banba page failed.")
        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for link in soup.find_all("a", href=True):
        href = link["href"]

        if "/products/" in href:
            product_path = href.split("?")[0]

            match = re.search(
                r"/products/[^/]*?(\d+)$",
                product_path
            )

            if match:
                products.add(match.group(1))

    return sorted(products)


def check_arnotts():
    products = []

    url = (
        "https://www.arnotts.ie/sea
```
