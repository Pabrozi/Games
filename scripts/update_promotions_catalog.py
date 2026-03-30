from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROMOTIONS_DIR = DATA_DIR / "promotions"
PROMOTIONS_FILE = PROMOTIONS_DIR / "manifest.json"

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results/"
EPIC_FREE_GAMES_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
EPIC_BROWSE_URL = "https://store.epicgames.com/en-US/browse"

HIGH_DISCOUNT_THRESHOLD = 75
MAX_DEALS_PER_STORE = 24

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Upgrade-Insecure-Requests": "1",
}

BROKEN_TEXT_MARKERS = (
    "\u00c3",
    "\u00e2",
    "\u20ac",
    "\u2122",
    "\u0153",
    "\u00a2",
)


def fetch_text(url: str, retries: int = 5) -> str:
    attempt = 0
    while True:
        request = Request(url, headers=HEADERS)
        try:
            with urlopen(request) as response:
                return response.read().decode("utf-8", errors="ignore")
        except HTTPError as error:
            if error.code not in {403, 429} or attempt >= retries:
                raise
            time.sleep(min(20, 3 * (attempt + 1)))
            attempt += 1


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def repair_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.replace("\u00a0", " ").replace("\u00c2", "").strip()
    if any(marker in cleaned for marker in BROKEN_TEXT_MARKERS):
        try:
            cleaned = cleaned.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        except UnicodeError:
            pass
    cleaned = cleaned.replace("\u00a0", " ").strip()
    return re.sub(r"\s+", " ", cleaned).strip()


def strip_tags(value: str) -> str:
    raw = html.unescape(re.sub(r"<.*?>", "", value or "")).strip()
    return repair_text(raw) or ""


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_balanced_json(text: str, marker: str) -> dict:
    start = text.find(marker)
    if start == -1:
        raise ValueError(f"Marker not found: {marker}")

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])

    raise ValueError("Could not extract balanced JSON object.")


def choose_epic_image(element: dict) -> str | None:
    key_images = element.get("keyImages") or []
    preferred_types = [
        "OfferImageWide",
        "DieselStoreFrontWide",
        "Featured",
        "featuredMedia",
        "OfferImageTall",
        "Thumbnail",
    ]

    for image_type in preferred_types:
        for item in key_images:
            if item.get("type") == image_type and item.get("url"):
                return item["url"]

    for item in key_images:
        if item.get("url"):
            return item["url"]

    return None


def build_epic_url(element: dict) -> str | None:
    mappings = element.get("catalogNs", {}).get("mappings") or []
    offer_mappings = element.get("offerMappings") or []
    product_slug = (element.get("productSlug") or "").strip("/")
    url_slug = (element.get("urlSlug") or "").strip("/")

    if mappings and mappings[0].get("pageSlug"):
        return f"https://store.epicgames.com/en-US/p/{mappings[0]['pageSlug']}"

    if offer_mappings and offer_mappings[0].get("pageSlug"):
        return f"https://store.epicgames.com/en-US/p/{offer_mappings[0]['pageSlug']}"

    if product_slug:
        return f"https://store.epicgames.com/en-US/p/{product_slug}"

    if url_slug:
        return f"https://store.epicgames.com/en-US/p/{url_slug}"

    return None


def is_epic_base_game(element: dict) -> bool:
    categories = {item.get("path", "") for item in element.get("categories") or []}
    if "games/edition/base" in categories:
        return True
    return "games" in categories and not any("addon" in item or "demo" in item for item in categories)


def epic_price_labels(element: dict) -> tuple[str | None, str | None]:
    fmt_price = element.get("price", {}).get("totalPrice", {}).get("fmtPrice", {})
    original_price = repair_text(fmt_price.get("originalPrice"))
    discount_price = repair_text(fmt_price.get("discountPrice"))
    compact_discount = (discount_price or "").replace(" ", "")
    if compact_discount in {"0", "0.00", "0,00", "R$0.00", "R$0,00"}:
        discount_price = "Gratis"
    return original_price, discount_price


def discount_percentage(original_cents: int | None, final_cents: int | None) -> int:
    if not original_cents or final_cents is None or original_cents <= final_cents:
        return 0
    return round((1 - (final_cents / original_cents)) * 100)


def build_epic_entry(
    element: dict,
    *,
    discount_percent: int,
    original_price: str | None,
    final_price: str | None,
    starts_at: str | None,
    ends_at: str | None,
    note: str,
) -> dict:
    return {
        "name": repair_text((element.get("title") or "").strip()),
        "platform": "epic",
        "url": build_epic_url(element),
        "image_url": choose_epic_image(element),
        "discount_percent": discount_percent,
        "original_price": original_price,
        "final_price": final_price,
        "starts_at": starts_at,
        "ends_at": ends_at,
        "note": note,
    }


def fetch_epic_free_games() -> tuple[list[dict], list[dict]]:
    now = datetime.now(timezone.utc)
    params = urlencode({"locale": "pt-BR", "country": "BR", "allowCountries": "BR"})
    payload = json.loads(fetch_text(f"{EPIC_FREE_GAMES_URL}?{params}"))
    elements = payload["data"]["Catalog"]["searchStore"]["elements"]

    current_free: list[dict] = []
    upcoming_free: list[dict] = []

    for element in elements:
        if not is_epic_base_game(element):
            continue

        total_price = element.get("price", {}).get("totalPrice", {})
        original_price, final_price = epic_price_labels(element)
        promotions = element.get("promotions") or {}

        for group in promotions.get("promotionalOffers") or []:
            for offer in group.get("promotionalOffers") or []:
                start_at = parse_iso_datetime(offer.get("startDate"))
                end_at = parse_iso_datetime(offer.get("endDate"))
                if not start_at or not end_at:
                    continue
                if start_at <= now < end_at and total_price.get("discountPrice") == 0 and total_price.get("originalPrice", 0) > 0:
                    current_free.append(
                        build_epic_entry(
                            element,
                            discount_percent=100,
                            original_price=original_price,
                            final_price=final_price or "Gratis",
                            starts_at=None,
                            ends_at=offer.get("endDate"),
                            note="Gratis agora na Epic Games Store.",
                        )
                    )
                    break

        for group in promotions.get("upcomingPromotionalOffers") or []:
            for offer in group.get("promotionalOffers") or []:
                start_at = parse_iso_datetime(offer.get("startDate"))
                end_at = parse_iso_datetime(offer.get("endDate"))
                discount_setting = offer.get("discountSetting") or {}
                if not start_at or not end_at or start_at <= now:
                    continue
                if discount_setting.get("discountPercentage") == 0:
                    upcoming_free.append(
                        build_epic_entry(
                            element,
                            discount_percent=100,
                            original_price=None,
                            final_price="Gratis em breve",
                            starts_at=offer.get("startDate"),
                            ends_at=offer.get("endDate"),
                            note="Brinde agendado pela Epic Games Store.",
                        )
                    )
                    break

    current_free.sort(key=lambda item: item["name"].lower())
    upcoming_free.sort(key=lambda item: item.get("starts_at") or "")
    return current_free, upcoming_free


def parse_steam_rows(results_html: str) -> list[dict]:
    rows: list[dict] = []
    for href, block in re.findall(
        r'<a href="([^"]+)"[^>]*class="search_result_row[^"]*"[^>]*>(.*?)</a>',
        results_html,
        flags=re.S,
    ):
        title_match = re.search(r'<span class="title">(.*?)</span>', block, flags=re.S)
        image_match = re.search(r'<div class="search_capsule"><img src="([^"]+)"', block)
        discount_match = re.search(r'<div class="discount_pct">-?(\d+)%</div>', block)
        original_match = re.search(r'<div class="discount_original_price">(.*?)</div>', block, flags=re.S)
        final_match = re.search(r'<div class="discount_final_price(?: free)?">(.*?)</div>', block, flags=re.S)

        title = strip_tags(title_match.group(1)) if title_match else ""
        if not title:
            continue

        rows.append(
            {
                "name": title,
                "platform": "steam",
                "url": clean_url(html.unescape(href)),
                "image_url": clean_url(html.unescape(image_match.group(1))) if image_match else None,
                "discount_percent": int(discount_match.group(1)) if discount_match else 0,
                "original_price": strip_tags(original_match.group(1)) if original_match else None,
                "final_price": strip_tags(final_match.group(1)) if final_match else None,
                "starts_at": None,
                "ends_at": None,
                "note": None,
            }
        )

    return rows


def fetch_steam_page(params: dict[str, str | int]) -> dict:
    query = urlencode(params)
    return json.loads(fetch_text(f"{STEAM_SEARCH_URL}?{query}"))


def fetch_steam_free_promotions() -> list[dict]:
    freebies: list[dict] = []
    seen = set()

    for page in range(3):
        payload = fetch_steam_page(
            {
                "query": "",
                "start": page * 100,
                "count": 100,
                "dynamic_data": "",
                "sort_by": "Price_ASC",
                "specials": 1,
                "supportedlang": "english",
                "category1": 998,
                "infinite": 1,
                "ndl": 1,
            }
        )

        rows = parse_steam_rows(payload.get("results_html", ""))
        if not rows:
            break

        page_freebies = 0
        for row in rows:
            final_price = (row.get("final_price") or "").strip().lower()
            if row["discount_percent"] != 100 and final_price != "free":
                continue
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            row["note"] = "Promocao de 100% de desconto encontrada na Steam."
            freebies.append(row)
            page_freebies += 1

        if page == 0 and page_freebies == 0:
            break

    freebies.sort(key=lambda item: item["name"].lower())
    return freebies


def fetch_steam_high_discounts() -> list[dict]:
    deals: list[dict] = []
    seen = set()
    start = 0
    count = 100

    while len(deals) < MAX_DEALS_PER_STORE:
        payload = fetch_steam_page(
            {
                "query": "",
                "start": start,
                "count": count,
                "dynamic_data": "",
                "sort_by": "Discount_DESC",
                "specials": 1,
                "supportedlang": "english",
                "category1": 998,
                "infinite": 1,
                "ndl": 1,
            }
        )

        rows = parse_steam_rows(payload.get("results_html", ""))
        if not rows:
            break

        for row in rows:
            final_price = (row.get("final_price") or "").strip().lower()
            if row["discount_percent"] < HIGH_DISCOUNT_THRESHOLD or final_price == "free":
                continue
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            row["note"] = f"Desconto alto na Steam: {row['discount_percent']}%."
            deals.append(row)
            if len(deals) >= MAX_DEALS_PER_STORE:
                break

        if all(row["discount_percent"] < HIGH_DISCOUNT_THRESHOLD for row in rows):
            break

        start += count
        if start >= payload.get("total_count", 0):
            break
        time.sleep(0.2)

    return deals


def fetch_epic_discount_page(start: int, count: int = 40) -> tuple[list[dict], int]:
    params = urlencode(
        {
            "category": "Game",
            "count": count,
            "priceTier": "tierDiscouted",
            "sortBy": "releaseDate",
            "sortDir": "DESC",
            "start": start,
        }
    )
    text = fetch_text(f"{EPIC_BROWSE_URL}?{params}")
    payload = extract_balanced_json(text, '{"state":{"data":{"Catalog":{"searchStore":{"elements":')
    search_store = payload["state"]["data"]["Catalog"]["searchStore"]
    return search_store["elements"], search_store.get("paging", {}).get("total", 0)


def fetch_epic_high_discounts() -> list[dict]:
    deals: list[dict] = []
    seen = set()
    start = 0
    count = 40

    while len(deals) < MAX_DEALS_PER_STORE and start < 400:
        elements, total_count = fetch_epic_discount_page(start, count)
        if not elements:
            break

        for element in elements:
            if not is_epic_base_game(element):
                continue

            total_price = element.get("price", {}).get("totalPrice", {})
            original_cents = total_price.get("originalPrice")
            final_cents = total_price.get("discountPrice")
            pct = discount_percentage(original_cents, final_cents)
            if pct < HIGH_DISCOUNT_THRESHOLD or final_cents == 0:
                continue

            url = build_epic_url(element)
            if not url or url in seen:
                continue
            seen.add(url)

            original_price, final_price = epic_price_labels(element)
            deals.append(
                build_epic_entry(
                    element,
                    discount_percent=pct,
                    original_price=original_price,
                    final_price=final_price,
                    starts_at=None,
                    ends_at=None,
                    note=f"Desconto alto na Epic Games Store: {pct}%.",
                )
            )

            if len(deals) >= MAX_DEALS_PER_STORE:
                break

        start += count
        if start >= total_count:
            break
        time.sleep(0.2)

    deals.sort(key=lambda item: (-item["discount_percent"], item["name"].lower()))
    return deals[:MAX_DEALS_PER_STORE]


def main() -> None:
    epic_free_now, epic_free_upcoming = fetch_epic_free_games()
    steam_free_now = fetch_steam_free_promotions()
    steam_deals = fetch_steam_high_discounts()
    epic_deals = fetch_epic_high_discounts()

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": datetime.now().strftime("%Y-%m-%d"),
        "thresholds": {
            "high_discount_percent": HIGH_DISCOUNT_THRESHOLD,
        },
        "sources": {
            "epic_free_games": EPIC_FREE_GAMES_URL,
            "epic_browse": EPIC_BROWSE_URL,
            "steam_search": STEAM_SEARCH_URL,
        },
        "stats": {
            "epic_free_now": len(epic_free_now),
            "steam_free_now": len(steam_free_now),
            "epic_high_discounts": len(epic_deals),
            "steam_high_discounts": len(steam_deals),
        },
        "current_free": {
            "epic": epic_free_now,
            "steam": steam_free_now,
        },
        "upcoming_free": {
            "epic": epic_free_upcoming,
        },
        "high_discounts": {
            "steam": steam_deals,
            "epic": epic_deals,
        },
    }

    write_json(PROMOTIONS_FILE, payload)
    print(f"Saved promotions snapshot to {PROMOTIONS_FILE}")
    print(json.dumps(payload["stats"], ensure_ascii=False))


if __name__ == "__main__":
    main()
