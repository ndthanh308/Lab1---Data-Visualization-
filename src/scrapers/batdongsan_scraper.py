import asyncio
import concurrent.futures
import os
import random
import re
import sys
import time
import unicodedata
from typing import Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup

BASE_URL = "https://batdongsan.com.vn/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _ensure_windows_proactor_policy() -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        policy = asyncio.get_event_loop_policy()
        if policy.__class__.__name__ == "WindowsProactorEventLoopPolicy":
            return
        proactor_policy = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
        if proactor_policy is not None:
            asyncio.set_event_loop_policy(proactor_policy())
    except Exception:
        return


def _safe_text(element) -> Optional[str]:
    return element.get_text(strip=True) if element else None


def _normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.lower()


def _extract_number(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:[\.,]\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    normalized = _normalize_text(text)
    if "thoa thuan" in normalized:
        return None
    value = _extract_number(normalized)
    if value is None:
        return None
    if "ty" in normalized:
        return value * 1_000_000_000
    if "trieu" in normalized:
        return value * 1_000_000
    if "nghin" in normalized or "ngan" in normalized:
        return value * 1_000
    return value


def parse_area(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    normalized = _normalize_text(text)
    return _extract_number(normalized)


def parse_integer(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    normalized = _normalize_text(text)
    match = re.search(r"(\d+)", normalized)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def parse_location_vn(text: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Parse Vietnamese location into (street, ward, district, city)."""

    if not text:
        return None, None, None, None
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return None, None, None, None

    # Heuristic: last component is city for common cities.
    city = None
    if len(parts) >= 2:
        last = parts[-1].lower()
        if any(
            key in last
            for key in [
                "ho chi minh",
                "hồ chí minh",
                "ha noi",
                "hà nội",
                "da nang",
                "đà nẵng",
            ]
        ):
            city = parts[-1]
            parts = parts[:-1]

    if len(parts) == 1:
        return None, None, parts[0], city
    if len(parts) == 2:
        return None, None, parts[0], city or parts[1]

    street = ", ".join(parts[:-2])
    ward = parts[-2]
    district = parts[-1]
    return street or None, ward or None, district or None, city


def _has_red_book(description: Optional[str]) -> bool:
    normalized = _normalize_text(description)
    return any(keyword in normalized for keyword in ["so hong", "so do"])


def _get_text_safe(card, selector: str) -> Optional[str]:
    try:
        return _safe_text(card.select_one(selector))
    except Exception:
        return None


def _get_text_or_aria(card, selector: str) -> Optional[str]:
    try:
        element = card.select_one(selector)
    except Exception:
        return None
    if not element:
        return None
    text = _safe_text(element)
    if text:
        return text
    return element.get("aria-label")


def _parse_card(card, source_url: str) -> Dict[str, Optional[object]]:
    price_text = _get_text_safe(card, "span.re__card-config-price")
    area_text = _get_text_safe(card, "span.re__card-config-area")
    price_per_m2_text = _get_text_safe(card, "span.re__card-config-price_per_m2")
    bedrooms_text = _get_text_or_aria(card, "span.re__card-config-bedroom")
    toilets_text = _get_text_or_aria(card, "span.re__card-config-toilet")
    location_text = _get_text_safe(card, "div.re__card-location")
    title_text = _get_text_safe(card, "h3.re__card-title")
    description_text = _get_text_safe(card, "div.re__card-description")
    contact_name_text = _get_text_safe(card, ".re__contact-name")

    street, ward, district, city = parse_location_vn(location_text)

    return {
        "price": parse_price(price_text),
        "area": parse_area(area_text),
        "price_per_m2": parse_price(price_per_m2_text),
        "bedrooms": parse_integer(bedrooms_text),
        "toilets": parse_integer(toilets_text),
        "street": street,
        "ward": ward,
        "district": district,
        "city": city,
        "title": title_text,
        "description": description_text,
        "has_red_book": _has_red_book(description_text),
        "contact_name": contact_name_text,
        "source_url": source_url,
    }


def _parse_cards_from_html(html: str, source_url: str) -> List[Dict[str, Optional[object]]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.re__card-info")
    return [_parse_card(card, source_url) for card in cards]


def _scrape_properties_with_playwright_sync(
    urls: Iterable[str],
    sleep_range: Tuple[float, float],
    timeout: int,
    cookies: Optional[str],
    headless: bool,
) -> List[Dict[str, Optional[object]]]:
    _ensure_windows_proactor_policy()

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            "Playwright is required. Install with: pip install playwright; playwright install"
        ) from exc

    url_list = list(urls)
    all_rows: List[Dict[str, Optional[object]]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"])

        extra_headers = {"Referer": BASE_URL}
        cookie_header = cookies or os.getenv("BDS_COOKIE")
        if cookie_header:
            extra_headers["Cookie"] = cookie_header
        context.set_extra_http_headers(extra_headers)

        page = context.new_page()

        for index, url in enumerate(url_list):
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            try:
                page.wait_for_selector("div.re__card-info", timeout=timeout * 1000)
            except PlaywrightTimeoutError:
                pass

            html = page.content()
            all_rows.extend(_parse_cards_from_html(html, url))

            if index < len(url_list) - 1:
                time.sleep(random.uniform(*sleep_range))

        context.close()
        browser.close()

    return all_rows


def scrape_properties_with_playwright_threaded(
    urls: Iterable[str],
    sleep_range: Tuple[float, float] = (1.5, 3.5),
    timeout: int = 30,
    cookies: Optional[str] = None,
    headless: bool = True,
) -> List[Dict[str, Optional[object]]]:
    """Used by the notebook 'Playwright fallback' cell."""

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _scrape_properties_with_playwright_sync,
            urls,
            sleep_range,
            timeout,
            cookies,
            headless,
        )
        return future.result()
