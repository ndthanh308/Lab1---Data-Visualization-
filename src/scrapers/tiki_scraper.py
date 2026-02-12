from __future__ import annotations

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests

TIKI_API_URL = "https://tiki.vn/api/v2/products"


def _build_headers() -> Dict[str, str]:
    """Return headers that mimic a real browser."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://tiki.vn/",
    }


def _safe_get_quantity_sold(value) -> Optional[int]:
    if isinstance(value, dict):
        return value.get("value")
    return value


def _safe_get_quantity_sold_text(value) -> Optional[str]:
    if isinstance(value, dict):
        return value.get("text")
    return None


def _extract_metadata(impression_info) -> Dict[str, object]:
    if isinstance(impression_info, dict):
        return impression_info.get("metadata") or {}
    if isinstance(impression_info, list):
        for entry in impression_info:
            if isinstance(entry, dict) and entry.get("metadata"):
                return entry.get("metadata") or {}
    return {}


def _extract_seller(item: Dict[str, object]) -> Dict[str, object]:
    seller = item.get("seller") or {}
    if not isinstance(seller, dict):
        seller = {}
    return {
        "seller_id": item.get("seller_id") or seller.get("id"),
        "seller_name": item.get("seller_name") or seller.get("name"),
        "seller_type": seller.get("seller_type"),
        "seller_logo": seller.get("logo"),
        "seller_rating": seller.get("average_rating"),
        "seller_reviews": seller.get("review_count"),
        "seller_followers": seller.get("followers"),
    }


def _extract_category(item: Dict[str, object]) -> Dict[str, object]:
    category = item.get("category")
    categories = item.get("categories")

    if isinstance(category, dict):
        return {
            "category_id": category.get("id"),
            "category_name": category.get("name"),
        }

    if isinstance(categories, list) and categories:
        first = categories[0] if isinstance(categories[0], dict) else {}
        return {
            "category_id": first.get("id"),
            "category_name": first.get("name"),
        }

    return {"category_id": None, "category_name": None}


def _extract_stock(item: Dict[str, object]) -> Dict[str, object]:
    stock = item.get("stock_item") or {}
    if not isinstance(stock, dict):
        stock = {}
    return {
        "stock_qty": stock.get("qty"),
        "stock_available": stock.get("available"),
        "stock_preorder": stock.get("preorder"),
        "stock_min_sale_qty": stock.get("min_sale_qty"),
        "stock_max_sale_qty": stock.get("max_sale_qty"),
    }


def _extract_badges(item: Dict[str, object]) -> str:
    badges = item.get("badges")
    if not isinstance(badges, list):
        return ""
    names = []
    for badge in badges:
        if isinstance(badge, dict):
            names.append(badge.get("code") or badge.get("title") or "")
    return ";".join([n for n in names if n])


def _extract_metadata(impression_info) -> Dict[str, object]:
    if isinstance(impression_info, dict):
        return impression_info.get("metadata") or {}
    if isinstance(impression_info, list):
        for entry in impression_info:
            if isinstance(entry, dict) and entry.get("metadata"):
                return entry.get("metadata") or {}
    return {}


def fetch_tiki_products(
    keyword: str,
    pages: int = 5,
    limit: int = 40,
    sleep_seconds: float = 2.0,
    timeout: int = 20,
) -> pd.DataFrame:
    """
    Crawl multiple pages of Tiki products for a keyword and return a DataFrame.
    """
    headers = _build_headers()
    rows: List[Dict[str, object]] = []

    for page in range(1, pages + 1):
        params = {"q": keyword, "limit": limit, "page": page}
        try:
            response = requests.get(
                TIKI_API_URL, headers=headers, params=params, timeout=timeout
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("data", [])
        except requests.RequestException as exc:
            print(f"[WARN] Page {page} failed: {exc}")
            time.sleep(sleep_seconds)
            continue

        for item in items:
            metadata = _extract_metadata(item.get("impression_info"))
            seller_info = _extract_seller(item)
            category_info = _extract_category(item)
            stock_info = _extract_stock(item)
            url_path = item.get("url_path")
            product_url = f"https://tiki.vn/{url_path}" if url_path else None

            rows.append(
                {
                    "id": item.get("id"),
                    "product_id": item.get("product_id"),
                    "tiki_product_id": item.get("tiki_product_id"),
                    "seller_product_id": item.get("seller_product_id"),
                    "sku": item.get("sku"),
                    "name": item.get("name"),
                    "short_description": item.get("short_description"),
                    "type": item.get("type"),
                    "brand_name": item.get("brand_name"),
                    "brand_id": item.get("brand_id"),
                    "price": item.get("price"),
                    "list_price": item.get("list_price"),
                    "original_price": item.get("original_price"),
                    "market_price": item.get("market_price"),
                    "discount": item.get("discount"),
                    "discount_rate": item.get("discount_rate"),
                    "rating_average": item.get("rating_average"),
                    "review_count": item.get("review_count"),
                    "quantity_sold": _safe_get_quantity_sold(item.get("quantity_sold")),
                    "quantity_sold_text": _safe_get_quantity_sold_text(
                        item.get("quantity_sold")
                    ),
                    "is_official_store": metadata.get("is_official_store"),
                    "is_freeship": item.get("is_freeship")
                    or item.get("is_free_ship"),
                    "inventory_status": item.get("inventory_status"),
                    "is_tikinow": item.get("is_tikinow"),
                    "tikinow_time": item.get("tikinow_time"),
                    "thumbnail_url": item.get("thumbnail_url"),
                    "product_url": product_url,
                    "badges": _extract_badges(item),
                    **seller_info,
                    **category_info,
                    **stock_info,
                }
            )

        time.sleep(sleep_seconds)

    return pd.DataFrame(rows)


def save_with_timestamp(
    df: pd.DataFrame,
    keyword: str,
    out_dir: str | Path = "../data/raw",
) -> Path:
    """Save DataFrame to CSV with a date-stamped filename and return the path."""
    safe_keyword = re.sub(r"\s+", "_", keyword.strip().lower())
    ts = datetime.now().strftime("%Y%m%d")
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"tiki_{safe_keyword}_{ts}.csv"
    df.to_csv(file_path, index=False)
    return file_path
