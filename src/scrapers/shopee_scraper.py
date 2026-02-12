from __future__ import annotations

import random
import re
import time
from urllib.parse import quote
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import requests

SEARCH_API = "https://shopee.vn/api/v4/search/search_items"
DETAIL_API = "https://shopee.vn/api/v4/item/get"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/144.0.0.0 Safari/537.36"
    ),
    "af-ac-enc-dat": "5e40808d1c7bbe81",
    "x-api-source": "pc",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


def _normalize_keyword(keyword: str) -> str:
    return re.sub(r"\s+", " ", keyword.strip())


def _sleep_polite(min_s: float = 3.0, max_s: float = 6.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _collect_item_pairs(
    keyword: str,
    headers: Dict[str, str],
    offsets: Iterable[int],
    limit: int = 60,
    timeout: int = 20,
) -> List[Tuple[int, int]]:
    pairs: List[Tuple[int, int]] = []
    for offset in offsets:
        params = {"keyword": keyword, "limit": limit, "newest": offset}
        try:
            response = requests.get(
                SEARCH_API, headers=headers, params=params, timeout=timeout
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            print(f"[WARN] Search offset {offset} failed: {exc}")
            _sleep_polite()
            continue

        items = payload.get("items", []) or []
        if not items:
            err = payload.get("error") or payload.get("error_msg") or "no_items"
            print(f"[WARN] Empty search results at offset {offset}: {err}")
        for entry in items:
            basic = entry.get("item_basic") or {}
            itemid = basic.get("itemid")
            shopid = basic.get("shopid")
            if itemid and shopid:
                pairs.append((int(itemid), int(shopid)))
        _sleep_polite()
    return pairs


def _attributes_to_dict(attributes: List[Dict[str, object]]) -> Dict[str, object]:
    attr_map: Dict[str, object] = {}
    for attr in attributes or []:
        name = attr.get("name")
        value = attr.get("value")
        if name:
            attr_map[str(name)] = value
    return attr_map


def fetch_shopee_products(
    keyword: str,
    offsets: Iterable[int] = (0, 60, 120),
    limit: int = 60,
    cookie: str = "",
    checkpoint_every: int = 10,
    out_dir: str | Path = "../data/raw",
    timeout: int = 20,
) -> pd.DataFrame:
    """
    Two-step pipeline:
    1) Search API -> itemid/shopid pairs
    2) Detail API -> deep attributes and product fields
    """
    headers = dict(DEFAULT_HEADERS)
    if cookie:
        safe_cookie = cookie.strip().replace("\n", "").replace("\r", "")
        headers["Cookie"] = safe_cookie
    headers["Referer"] = f"https://shopee.vn/search?keyword={quote(keyword)}"

    keyword = _normalize_keyword(keyword)
    pairs = _collect_item_pairs(keyword, headers, offsets, limit=limit, timeout=timeout)

    if not pairs:
        raise ValueError(
            "Khong tim thay itemid/shopid. Cookie co the da het han hoac keyword khong hop le."
        )

    rows: List[Dict[str, object]] = []
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    safe_keyword = re.sub(r"\s+", "_", keyword.strip().lower())
    checkpoint_path = out_path / f"shopee_{safe_keyword}_checkpoint.csv"

    for idx, (itemid, shopid) in enumerate(pairs, start=1):
        params = {"itemid": itemid, "shopid": shopid}
        try:
            response = requests.get(
                DETAIL_API, headers=headers, params=params, timeout=timeout
            )
            response.raise_for_status()
            payload = response.json()
            item = payload.get("item") or {}
        except requests.RequestException as exc:
            print(f"[WARN] Detail failed for item {itemid}: {exc}")
            _sleep_polite()
            continue

        attributes = _attributes_to_dict(item.get("attributes") or [])

        row = {
            "itemid": itemid,
            "shopid": shopid,
            "name": item.get("name"),
            "description": item.get("description"),
            "price": (item.get("price") or 0) / 100000,
            "price_before_discount": (item.get("price_before_discount") or 0) / 100000,
            "discount": item.get("discount"),
            "historical_sold": item.get("historical_sold"),
            "rating_star": (item.get("item_rating") or {}).get("rating_star"),
            "stock": item.get("stock"),
            "brand": item.get("brand"),
            "category_id": item.get("catid"),
            "shop_location": item.get("shop_location"),
            "is_official_shop": item.get("is_official_shop"),
            "is_preferred_plus_seller": item.get("is_preferred_plus_seller"),
            "liked_count": item.get("liked_count"),
            "cmt_count": item.get("cmt_count"),
            **attributes,
        }

        rows.append(row)

        if checkpoint_every and idx % checkpoint_every == 0:
            pd.DataFrame(rows).to_csv(checkpoint_path, index=False, encoding="utf-8-sig")

        _sleep_polite()

    return pd.DataFrame(rows)


def save_full_dataset(df: pd.DataFrame, keyword: str, out_dir: str | Path = "../data/raw") -> Path:
    safe_keyword = re.sub(r"\s+", "_", keyword.strip().lower())
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"shopee_{safe_keyword}_full.csv"
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    return file_path
