import json
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "https://gamewith.jp/7taizai/article/show/158813"

def fetch_with_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP",
            extra_http_headers={"Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8"}
        )
        page = context.new_page()
        print(f"Navigating to {URL}")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        # Wait for images to lazy-load
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
        print(f"Page fetched. HTML length: {len(html)}")
        return html

def parse(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        print("WARNING: No <table> elements found.")
        return []

    target = max(tables, key=lambda t: len(str(t)))
    rows_out = []

    for tr in target.find_all("tr"):
        cells_out = []
        is_header = bool(tr.find("th"))
        for cell in tr.find_all(["td", "th"]):
            img = cell.find("img")
            img_src = None
            if img:
                # Prefer src over data-src since page is fully rendered
                img_src = img.get("src") or img.get("data-src")
                if img_src and "transparent" in img_src:
                    img_src = img.get("data-src") or img.get("data-original") or None
                if img_src and img_src.startswith("//"):
                    img_src = "https:" + img_src
                elif img_src and img_src.startswith("/"):
                    img_src = "https://gamewith.jp" + img_src

            text = cell.get_text(separator=" ", strip=True)
            cells_out.append({"text": text, "imgSrc": img_src})

        if cells_out:
            rows_out.append({"cells": cells_out, "isHeader": is_header})

    return rows_out

def main():
    try:
        html = fetch_with_playwright()
    except Exception as e:
        print(f"Fetch failed: {e}")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump({
                "updated": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "rows": []
            }, f, ensure_ascii=False, indent=2)
        return

    rows = parse(html)
    print(f"Parsed {len(rows)} rows")

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": URL,
        "rows": rows
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("data.json written.")

if __name__ == "__main__":
    main()
