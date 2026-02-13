from __future__ import annotations

from pathlib import Path
import os
import re
import sys
import unicodedata

import pandas as pd


def _norm(s: str) -> str:
    s = (s or "").replace("\xa0", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = s.replace("đ", "d")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    links_path = project_root / "data" / "processed" / "links_p7.csv"
    if not links_path.exists():
        raise FileNotFoundError(f"Missing: {links_path}")

    links_df = pd.read_csv(links_path)
    detail_urls = links_df.get("detail_url")
    if detail_urls is None:
        raise KeyError("links_p7.csv must contain column 'detail_url'")

    detail_urls = links_df["detail_url"].dropna().astype(str).tolist()
    if not detail_urls:
        print("No urls found")
        return 2

    url = detail_urls[0]
    print("URL:", url)

    import src.scrapers.batdongsan_scraper as bds

    bds._ensure_windows_proactor_policy()

    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    cookie = os.getenv("BDS_COOKIE")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=bds.DEFAULT_HEADERS["User-Agent"])
        extra_headers = {"Referer": bds.BASE_URL}
        if cookie:
            extra_headers["Cookie"] = cookie
        context.set_extra_http_headers(extra_headers)

        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # Wait for common content
        for sel, to in [(".re__pr-specs", 12_000), (".re__pr-short-info", 12_000), (".re__pr-listing-verified-section", 6_000)]:
            try:
                page.wait_for_selector(sel, timeout=to)
                print("wait ok:", sel)
            except PlaywrightTimeoutError:
                print("wait timeout:", sel)

        # Give time for late text rendering
        page.wait_for_timeout(1500)

        html = page.content() or ""

        # Some content may not appear in HTML; compare with visible text
        try:
            body_text = page.inner_text("body") or ""
        except Exception as e:
            print("inner_text(body) failed:", repr(e))
            body_text = ""

        title = ""
        try:
            title = page.title() or ""
        except Exception:
            pass

        context.close()
        browser.close()

    debug_dir = project_root / "data" / "processed" / "debug_html"
    debug_dir.mkdir(parents=True, exist_ok=True)
    out_html = debug_dir / "detail_first_url.html"
    out_html.write_text(html, encoding="utf-8")

    phrase_raw = "Batdongsan.com.vn đã xác thực"
    pat = r"batdongsan\.com\.vn.{0,120}da xac thuc"

    html_norm = _norm(html)
    text_norm = _norm(body_text)

    print("\nTitle:", title[:200])
    print("HTML chars:", len(html), "| body_text chars:", len(body_text))
    print("Saved HTML:", out_html)

    print("\nRaw contains phrase in html?", phrase_raw in html)
    print("Raw contains phrase in body_text?", phrase_raw in body_text)
    print("Regex match in html_norm?", bool(re.search(pat, html_norm)))
    print("Regex match in text_norm?", bool(re.search(pat, text_norm)))

    # Cloudflare strings can exist in normal pages; use stronger signals for blocks.
    blocked = (
        ("just a moment" in title.lower())
        or ("attention required" in title.lower())
        or ("cf-error" in html.lower())
        or ("cf-chl" in html.lower())
    )
    print("Blocked heuristics:", blocked)

    # Print a window around match if present
    m = re.search(pat, html_norm)
    if m:
        a = max(0, m.start() - 120)
        b = min(len(html_norm), m.end() + 120)
        print("\nHTML_NORM window:\n", html_norm[a:b])
    else:
        print("\nNo match in HTML_NORM")

    m2 = re.search(pat, text_norm)
    if m2:
        a = max(0, m2.start() - 120)
        b = min(len(text_norm), m2.end() + 120)
        print("\nTEXT_NORM window:\n", text_norm[a:b])
    else:
        print("\nNo match in TEXT_NORM")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
