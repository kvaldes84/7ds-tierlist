import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone

URL = "https://gamewith.jp/7taizai/article/show/158813"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

def fetch():
    session = requests.Session()
    # Prime session with a root visit first (reduces bot detection)
    try:
        session.get("https://gamewith.jp", headers=HEADERS, timeout=15)
    except Exception:
        pass
    r = session.get(URL, headers=HEADERS, timeout=15)
    print(f"HTTP {r.status_code}")
    r.raise_for_status()
    return r.text

def parse(html):
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    if not tables:
        print("WARNING: No <table> elements found.")
        return []

    # Use largest table
    target = max(tables, key=lambda t: len(str(t)))
    rows_out = []

    for tr in target.find_all("tr"):
        cells_out = []
        is_header = bool(tr.find("th"))
        for cell in tr.find_all(["td", "th"]):
            img = cell.find("img")
            img_src = None
            if img:
                img_src = img.get("data-src") or img.get("src")
                # Make absolute
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
        html = fetch()
    except Exception as e:
        print(f"Fetch failed: {e}")
        # Write error state so Apps Script knows
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
