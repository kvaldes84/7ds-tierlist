import json
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "https://gamewith.jp/7taizai/article/show/158813"

def fetch_with_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ja-JP",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        # Hide webdriver flag
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
        print(f"Navigating to {URL}")

        # Use domcontentloaded — less strict, less likely to timeout or trigger bot detection
        response = page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        print(f"HTTP status: {response.status if response else 'unknown'}")

        # Scroll to trigger lazy-load
        page.wait_for_timeout(2000)
        page.evaluate("""
            () => {
                return new Promise(resolve => {
                    let total = document.body.scrollHeight;
                    let current = 0;
                    let step = 400;
                    let timer = setInterval(() => {
                        window.scrollBy(0, step);
                        current += step;
                        if (current >= total) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()
        print(f"HTML length: {len(html)}")
        return html, response.status if response else 0

def parse(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        print("WARNING: No <table> elements found.")
        # Log a snippet to help debug structure
        print("Body snippet:", soup.get_text()[:500])
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
                src = img.get("src", "")
                data_src = img.get("data-src") or img.get("data-original") or ""
                # Prefer whichever is not a placeholder
                img_src = src if (src and "transparent" not in src) else (data_src if data_src else None)
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
        html, status = fetch_with_playwright()
    except Exception as e:
        print(f"Fetch failed: {e}")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump({
                "updated": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "rows": []
            }, f, ensure_ascii=False, indent=2)
        return

    if status == 403:
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump({
                "updated": datetime.now(timezone.utc).isoformat(),
                "error": f"HTTP 403 — GameWith blocked the request even with headless browser.",
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
