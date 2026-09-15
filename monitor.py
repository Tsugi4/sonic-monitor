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
            return json.load(f)

    return {
        "banba": [],
        "arnotts": []
    }


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
        "https://www.arnotts.ie/search/"
        "?q=Sonic&srule=SF%20new%20in&start=0&sz=48"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print(f"Arnotts: {response.status_code}")

    if response.status_code != 200:
        print("Arnotts page failed.")
        return products

    ids = re.findall(
        r"id:\s*'(\d+)'",
        response.text
    )

    for product_id in ids:
        if product_id not in products:
            products.append(product_id)

    return products


def main():
    seen = load_seen()

    print("\nChecking Banba...")

    banba_products = check_banba()

    print(
        f"Banba products found: "
        f"{len(banba_products)}"
    )

    new_banba = [
        product
        for product in banba_products
        if product not in seen["banba"]
    ]

    print(
        f"New Banba products: "
        f"{len(new_banba)}"
    )

    if new_banba:
        count = len(new_banba)

        if count == 1:
            message = (
                "A new listing at "
                "[**Banba Toys!!**](<"
                "https://banbatoys.ie/search"
                "?sort_by=relevance&q=Sonic"
                "&type=product"
                "&filter.v.availability=1"
                "&filter.v.price.gte="
                "&filter.v.price.lte="
                ">) BEE"
            )
        else:
            message = (
                f"{count} new listings at "
                "[**Banba Toys!!**](<"
                "https://banbatoys.ie/search"
                "?sort_by=relevance&q=Sonic"
                "&type=product"
                "&filter.v.availability=1"
                "&filter.v.price.gte="
                "&filter.v.price.lte="
                ">) BEE"
            )

        send_discord(message)

    print("\nChecking Arnotts...")

    arnotts_products = check_arnotts()

    print(
        f"Arnotts products found: "
        f"{len(arnotts_products)}"
    )

    new_arnotts = [
        product
        for product in arnotts_products
        if product not in seen["arnotts"]
    ]

    print(
        f"New Arnotts products: "
        f"{len(new_arnotts)}"
    )

    if new_arnotts:
        count = len(new_arnotts)

        if count == 1:
            message = (
                "A new listing at "
                "[**Arnotts!!**](<"
                "https://www.arnotts.ie/search/"
                "?q=Sonic"
                "&srule=SF%20new%20in"
                "&start=0"
                "&sz=48"
                ">) buzz"
            )
        else:
            message = (
                f"{count} new listings at "
                "[**Arnotts!!**](<"
                "https://www.arnotts.ie/search/"
                "?q=Sonic"
                "&srule=SF%20new%20in"
                "&start=0"
                "&sz=48"
                ">) buzz"
            )

        send_discord(message)

    seen["banba"] = sorted(
        set(banba_products)
    )

    seen["arnotts"] = sorted(
        set(seen["arnotts"])
        | set(arnotts_products)
    )

    save_seen(seen)

    print("\nDone.")
    print(
        "Saved product history to:",
        DATA_FILE
    )


if __name__ == "__main__":
    main()
