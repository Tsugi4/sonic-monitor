import json
import os
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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

    if "smyths" not in seen:
        seen["smyths"] = None

    return seen


def save_seen(seen):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def check_banba():
    products = set()

    base_url = (
        "https://banbatoys.ie/search?sort_by=relevance&q=Sonic"
        "&type=product&filter.v.availability=1"
        "&filter.v.price.gte=&filter.v.price.lte="
    )

    for page in range(1, 4):
        url = base_url + f"&page={page}"

        response = requests.get(url, headers=headers, timeout=30)

        print(f"Banba page {page}: {response.status_code}")

        if response.status_code != 200:
            print("Banba page failed.")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if "/products/" in href:
                product_path = href.split("?")[0]
                products.add(product_path)

    return sorted(products)


def check_arnotts():
    products = []

    url = (
        "https://www.arnotts.ie/search/"
        "?q=Sonic&srule=SF%20new%20in&start=0&sz=48"
    )

    response = requests.get(url, headers=headers, timeout=30)

    print(f"Arnotts: {response.status_code}")

    if response.status_code != 200:
        print("Arnotts page failed.")
        return products

    ids = re.findall(r"id:\s*'(\d+)'", response.text)

    for product_id in ids:
        if product_id not in products:
            products.append(product_id)

    return products


def check_smyths():
    url = (
        "https://www.smythstoys.com/ie/en-ie/search"
        "?text=Sonic&sort=creationDate_dt+desc"
    )

    products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-IE",
            timezone_id="Europe/Dublin",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        print("Opening Smyths...")

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(5000)

            print("Smyths title:", page.title())

            for selector in [
                "button:has-text('Accept')",
                "button:has-text('Accept All')",
                "button:has-text('I Accept')"
            ]:
                try:
                    button = page.locator(selector).first

                    if button.is_visible(timeout=1000):
                        button.click()
                        page.wait_for_timeout(1000)
                        break

                except Exception:
                    pass

            links = page.locator("a[href]")
            count = links.count()

            for i in range(count):
                link = links.nth(i)

                try:
                    href = link.get_attribute("href")

                    if not href or "/p/" not in href:
                        continue

                    if "sonic" not in href.lower():
                        continue

                    match = re.search(r"/p/(\d+)", href)

                    if not match:
                        continue

                    product_id = match.group(1)

                    if product_id not in products:
                        products.append(product_id)

                except Exception:
                    pass

            print(f"Smyths products found: {len(products)}")

            browser.close()

            return products

        except Exception as e:
            print("Smyths check failed:", e)

            browser.close()

            return None


def main():
    dublin_time = datetime.now(ZoneInfo("Europe/Dublin"))

    print(
        "Dublin time:",
        dublin_time.strftime("%Y-%m-%d %H:%M:%S")
    )

    if dublin_time.hour != 11:
        print("Not 11am in Dublin. Skipping check.")
        return

    seen = load_seen()

    print("\nChecking Smyths...")

    smyths_products = check_smyths()

    if smyths_products is None:
        print("Smyths check failed. Keeping existing history.")

    elif seen["smyths"] is None:
        print(
            f"Smyths baseline established with "
            f"{len(smyths_products)} products."
        )

        seen["smyths"] = sorted(smyths_products)

    else:
        new_smyths = [
            product
            for product in smyths_products
            if product not in seen["smyths"]
        ]

        print(f"New Smyths products: {len(new_smyths)}")

        if new_smyths:
            count = len(new_smyths)

            if count == 1:
                message = (
                    "A new listing at "
                    "[**Smyths Toys!!**](<"
                    "https://www.smythstoys.com/ie/en-ie/search"
                    "?text=Sonic&sort=creationDate_dt+desc"
                    ">) beebeebee"
                )
            else:
                message = (
                    f"{count} new listings at "
                    "[**Smyths Toys!!**](<"
                    "https://www.smythstoys.com/ie/en-ie/search"
                    "?text=Sonic&sort=creationDate_dt+desc"
                    ">) beebeebee"
                )

            send_discord(message)

        seen["smyths"] = sorted(
            set(seen["smyths"]) | set(smyths_products)
        )

    print("\nChecking Banba...")

    banba_products = check_banba()

    print(f"Banba products found: {len(banba_products)}")

    new_banba = [
        product
        for product in banba_products
        if product not in seen["banba"]
    ]

    print(f"New Banba products: {len(new_banba)}")

    if new_banba:
        count = len(new_banba)

        if count == 1:
            message = (
                "A new listing at "
                "[**Banba Toys!!**](<"
                "https://banbatoys.ie/search?sort_by=relevance&q=Sonic"
                "&type=product&filter.v.availability=1"
                "&filter.v.price.gte=&filter.v.price.lte="
                ">) BEE"
            )
        else:
            message = (
                f"{count} new listings at "
                "[**Banba Toys!!**](<"
                "https://banbatoys.ie/search?sort_by=relevance&q=Sonic"
                "&type=product&filter.v.availability=1"
                "&filter.v.price.gte=&filter.v.price.lte="
                ">) BEE"
            )

        send_discord(message)

    print("\nChecking Arnotts...")

    arnotts_products = check_arnotts()

    print(f"Arnotts products found: {len(arnotts_products)}")

    new_arnotts = [
        product
        for product in arnotts_products
        if product not in seen["arnotts"]
    ]

    print(f"New Arnotts products: {len(new_arnotts)}")

    if new_arnotts:
        count = len(new_arnotts)

        if count == 1:
            message = (
                "A new listing at "
                "[**Arnotts!!**](<"
                "https://www.arnotts.ie/search/"
                "?q=Sonic&srule=SF%20new%20in&start=0&sz=48"
                ">) buzz"
            )
        else:
            message = (
                f"{count} new listings at "
                "[**Arnotts!!**](<"
                "https://www.arnotts.ie/search/"
                "?q=Sonic&srule=SF%20new%20in&start=0&sz=48"
                ">) buzz"
            )

        send_discord(message)

    seen["banba"] = sorted(
        set(seen["banba"]) | set(banba_products)
    )

    seen["arnotts"] = sorted(
        set(seen["arnotts"]) | set(arnotts_products)
    )

    save_seen(seen)

    print("\nDone.")
    print("Saved product history to:", DATA_FILE)


if __name__ == "__main__":
    main()
