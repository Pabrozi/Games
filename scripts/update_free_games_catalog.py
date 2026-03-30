from __future__ import annotations

import html
import json
import re
import shutil
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
CATALOG_DIR = DATA_DIR / "free-games"
ALIASES_FILE = CONFIG_DIR / "free-games-aliases.json"
CATALOG_PAGE_SIZE = 250

STEAM_SEARCH_URL = "https://store.steampowered.com/search/results/"
EPIC_BROWSE_URL = "https://store.epicgames.com/en-US/browse"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass
class StoreGame:
    name: str
    url: str
    platform: str
    image_url: str | None
    genres: list[str]


def fetch_text(url: str, retries: int = 6) -> str:
    attempt = 0
    while True:
        request = Request(url, headers=HEADERS)
        try:
            with urlopen(request) as response:
                return response.read().decode("utf-8", errors="ignore")
        except HTTPError as error:
            if error.code != 429 or attempt >= retries:
                raise
            sleep_seconds = min(60, 10 * (attempt + 1))
            time.sleep(sleep_seconds)
            attempt += 1


def normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


def tokenize_name(name: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return [token for token in normalized.split() if token]


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


GENRE_LABELS = [
    "Action",
    "Adventure",
    "Shooter",
    "RPG",
    "Strategy",
    "Simulation",
    "Casual",
    "Puzzle",
    "Platformer",
    "Horror",
    "Survival",
    "Racing",
    "Sports",
    "Fighting",
    "MMO",
    "Visual Novel",
    "Arcade",
    "Outros",
]

GENRE_RULES = {
    "Action": {
        "Action",
        "Action-Adventure",
        "Hack and Slash",
        "Beat 'em up",
        "Character Action Game",
    },
    "Adventure": {
        "Adventure",
        "Exploration",
        "Interactive Fiction",
        "Story Rich",
    },
    "Shooter": {
        "Shooter",
        "First-Person",
        "Third-Person Shooter",
        "Twin Stick Shooter",
        "Arena Shooter",
        "Boomer Shooter",
        "Looter Shooter",
    },
    "RPG": {
        "RPG",
        "JRPG",
        "Action RPG",
        "Dungeon Crawler",
        "Party-Based RPG",
        "CRPG",
        "Rogue-like",
        "Rogue-lite",
    },
    "Strategy": {
        "Strategy",
        "RTS",
        "Turn-Based Strategy",
        "4X",
        "Tower Defense",
        "Grand Strategy",
        "Auto Battler",
        "Card Battler",
        "City Builder",
    },
    "Simulation": {
        "Simulation",
        "Life Sim",
        "Farming Sim",
        "Management",
        "Sandbox",
        "Immersive Sim",
        "Automation",
        "Building",
    },
    "Casual": {
        "Casual",
        "Hidden Object",
        "Trivia",
        "Word Game",
        "Board Game",
        "Card Game",
        "Idler",
        "Clicker",
        "Family Friendly",
    },
    "Puzzle": {
        "Puzzle",
        "Match 3",
        "Logic",
        "Puzzle Platformer",
    },
    "Platformer": {
        "Platformer",
        "Precision Platformer",
        "Metroidvania",
    },
    "Horror": {
        "Horror",
        "Psychological Horror",
        "Survival Horror",
    },
    "Survival": {
        "Survival",
        "Open World Survival Craft",
        "Crafting",
    },
    "Racing": {
        "Racing",
        "Driving",
        "Automobile Sim",
        "Vehicular Combat",
    },
    "Sports": {
        "Sports",
        "Fishing",
        "Hunting",
        "Skating",
        "BMX",
    },
    "Fighting": {
        "Fighting",
        "2D Fighter",
        "Martial Arts",
    },
    "MMO": {
        "Massively Multiplayer",
        "MMORPG",
        "MOBA",
        "Battle Royale",
    },
    "Visual Novel": {
        "Visual Novel",
    },
    "Arcade": {
        "Arcade",
    },
}


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def normalize_genres(raw_genres: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen = set()

    for raw in raw_genres:
        clean = raw.strip()
        if not clean:
            continue
        for label, matches in GENRE_RULES.items():
            if clean in matches and label not in seen:
                normalized.append(label)
                seen.add(label)
                break

    if not normalized:
        return ["Outros"]

    ordered = [label for label in GENRE_LABELS if label in seen]
    return ordered


def load_aliases() -> dict[str, str]:
    if not ALIASES_FILE.exists():
        return {}

    aliases = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    canonical_map: dict[str, str] = {}

    for alias, canonical in aliases.items():
        alias_key = normalize_name(alias)
        canonical_key = normalize_name(canonical)
        if alias_key and canonical_key:
            canonical_map[alias_key] = canonical_key

    return canonical_map


def canonical_key(name: str, aliases: dict[str, str]) -> str:
    normalized = normalize_name(name)
    return aliases.get(normalized, normalized)


def choose_epic_image(element: dict) -> str | None:
    key_images = element.get("keyImages") or []
    preferred_types = [
        "OfferImageWide",
        "DieselStoreFrontWide",
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


def fetch_steam_tag_names() -> dict[int, str]:
    payload = json.loads(fetch_text("https://store.steampowered.com/tagdata/populartags/english"))
    return {
        int(item["tagid"]): item["name"]
        for item in payload
        if "tagid" in item and "name" in item
    }


def classify_steam_genres(tag_ids: list[int], tag_name_map: dict[int, str]) -> list[str]:
    raw_genres = [tag_name_map[tag_id] for tag_id in tag_ids if tag_id in tag_name_map]
    return normalize_genres(raw_genres)


def fetch_steam_games(tag_name_map: dict[int, str]) -> List[StoreGame]:
    start = 0
    count = 100
    games: List[StoreGame] = []

    while True:
        params = urlencode(
            {
                "query": "",
                "start": start,
                "count": count,
                "dynamic_data": "",
                "sort_by": "_ASC",
                "supportedlang": "english",
                "maxprice": "free",
                "category1": "998",
                "infinite": 1,
            }
        )
        payload = json.loads(fetch_text(f"{STEAM_SEARCH_URL}?{params}"))
        matches = re.findall(
            r'<a href="([^"]+)"[^>]*data-ds-tagids="([^"]+)"[^>]*>.*?<div class="search_capsule"><img src="([^"]+)".*?<span class="title">(.*?)</span>',
            payload["results_html"],
            flags=re.S,
        )
        if not matches:
            break

        for href, tag_ids_raw, image_url, title in matches:
            tag_ids = [int(value) for value in re.findall(r"\d+", tag_ids_raw)]
            games.append(
                StoreGame(
                    name=html.unescape(title).strip(),
                    url=clean_url(html.unescape(href).strip()),
                    platform="steam",
                    image_url=clean_url(html.unescape(image_url).strip()),
                    genres=classify_steam_genres(tag_ids, tag_name_map),
                )
            )

        start += count
        if start >= payload.get("total_count", 0):
            break
        time.sleep(0.2)

    return games


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


def build_epic_url(element: dict) -> str | None:
    mappings = element.get("catalogNs", {}).get("mappings") or []
    offer_mappings = element.get("offerMappings") or []
    page_slug = None

    if mappings:
        page_slug = mappings[0].get("pageSlug")
    elif offer_mappings:
        page_slug = offer_mappings[0].get("pageSlug")

    if not page_slug:
        return None
    return f"https://store.epicgames.com/en-US/p/{page_slug}"


def is_epic_base_game(element: dict) -> bool:
    categories = {item.get("path", "") for item in element.get("categories") or []}
    if "games/edition/base" in categories:
        return True
    return "games" in categories and not any("addon" in item or "demo" in item for item in categories)


def fetch_epic_page_genres(url: str) -> list[str]:
    text = fetch_text(url)
    match = re.search(r'"genres":(\[.*?\]),"platforms"', text)
    if not match:
        return ["Outros"]

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ["Outros"]

    raw_genres = [
        item.get("name", "").strip()
        for item in payload
        if isinstance(item, dict) and item.get("name")
    ]
    return normalize_genres(raw_genres)


def fetch_epic_games() -> List[StoreGame]:
    start = 0
    count = 40
    games: List[StoreGame] = []

    while True:
        params = urlencode(
            {
                "category": "Game",
                "count": count,
                "priceTier": "tierFree",
                "sortBy": "releaseDate",
                "sortDir": "DESC",
                "start": start,
            }
        )
        text = fetch_text(f"{EPIC_BROWSE_URL}?{params}")
        payload = extract_balanced_json(text, '{"state":{"data":{"Catalog":{"searchStore":{"elements":')
        search_store = payload["state"]["data"]["Catalog"]["searchStore"]
        elements = search_store["elements"]

        if not elements:
            break

        for element in elements:
            if not is_epic_base_game(element):
                continue

            url = build_epic_url(element)
            if not url:
                continue

            games.append(
                StoreGame(
                    name=(element.get("title") or "").strip(),
                    url=url,
                    platform="epic",
                    image_url=choose_epic_image(element),
                    genres=fetch_epic_page_genres(url),
                )
            )

        start += count
        if start >= search_store.get("paging", {}).get("total", 0):
            break
        time.sleep(0.2)

    return games


def merge_games(steam_games: List[StoreGame], epic_games: List[StoreGame], aliases: dict[str, str]) -> tuple[list[dict], dict]:
    merged: Dict[str, dict] = {}
    alias_match_count = 0

    for game in steam_games + epic_games:
        normalized = normalize_name(game.name)
        key = canonical_key(game.name, aliases)
        if not key:
            continue

        if normalized != key:
            alias_match_count += 1

        entry = merged.setdefault(
            key,
            {
                "name": game.name,
                "normalized_name": key,
                "search_text": " ".join(tokenize_name(game.name)),
                "genres": [],
                "genre_slugs": [],
                "steam_url": None,
                "epic_url": None,
                "steam_image_url": None,
                "epic_image_url": None,
            },
        )

        if len(game.name) < len(entry["name"]):
            entry["name"] = game.name
            entry["search_text"] = " ".join(tokenize_name(game.name))

        for genre in game.genres:
            if genre not in entry["genres"]:
                entry["genres"].append(genre)

        if game.platform == "steam":
            entry["steam_url"] = game.url
            entry["steam_image_url"] = game.image_url
        elif game.platform == "epic":
            entry["epic_url"] = game.url
            entry["epic_image_url"] = game.image_url

    catalog = []
    both_count = 0

    for item in merged.values():
        item["genres"] = [genre for genre in GENRE_LABELS if genre in item["genres"]] or ["Outros"]
        item["genre_slugs"] = [slugify(genre) for genre in item["genres"]]
        platforms = []
        if item["steam_url"]:
            platforms.append("Steam")
        if item["epic_url"]:
            platforms.append("Epic")
        if len(platforms) == 2:
            both_count += 1
        catalog.append(
            {
                "name": item["name"],
                "normalized_name": item["normalized_name"],
                "search_text": item["search_text"],
                "genres": item["genres"],
                "genre_slugs": item["genre_slugs"],
                "steam_url": item["steam_url"],
                "epic_url": item["epic_url"],
                "image_url": item["steam_image_url"] or item["epic_image_url"],
                "steam_image_url": item["steam_image_url"],
                "epic_image_url": item["epic_image_url"],
                "platforms": platforms,
            }
        )

    catalog.sort(key=lambda item: item["name"].lower())

    stats = {
        "steam_count": len(steam_games),
        "epic_count": len(epic_games),
        "merged_count": len(catalog),
        "both_platforms_count": both_count,
        "alias_match_count": alias_match_count,
    }
    return catalog, stats


def reset_catalog_dir() -> None:
    if CATALOG_DIR.exists():
        shutil.rmtree(CATALOG_DIR)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def paginate_games(games: list[dict], view_name: str) -> dict:
    base_dir = CATALOG_DIR / "browse" / view_name
    base_dir.mkdir(parents=True, exist_ok=True)

    page_count = (len(games) + CATALOG_PAGE_SIZE - 1) // CATALOG_PAGE_SIZE
    manifest = {
        "page_size": CATALOG_PAGE_SIZE,
        "page_count": page_count,
        "total_games": len(games),
        "pages": [],
    }

    for index in range(page_count):
        page_number = index + 1
        start = index * CATALOG_PAGE_SIZE
        end = start + CATALOG_PAGE_SIZE
        page_games = games[start:end]
        filename = f"browse/{view_name}/page-{page_number:03}.json"
        payload = {
            "page": page_number,
            "page_size": CATALOG_PAGE_SIZE,
            "games": page_games,
        }
        write_json(CATALOG_DIR / filename, payload)
        manifest["pages"].append(filename.replace("\\", "/"))

    return manifest


def add_to_index(index: dict[str, dict[str, dict]], key: str, game: dict) -> None:
    bucket = index.setdefault(key, {})
    bucket[game["normalized_name"]] = game


def index_games_by_token_prefix(games: Iterable[dict]) -> dict[str, dict[str, dict[str, dict]]]:
    one_char: dict[str, dict[str, dict]] = {}
    two_char: dict[str, dict[str, dict]] = {}

    for game in games:
        tokens = set(game.get("search_text", "").split())
        for token in tokens:
            if not token:
                continue
            add_to_index(one_char, token[0], game)
            if len(token) >= 2:
                add_to_index(two_char, token[:2], game)

    return {"one": one_char, "two": two_char}


def write_search_indexes(games: list[dict]) -> dict:
    indexed = index_games_by_token_prefix(games)
    one_dir = CATALOG_DIR / "search" / "one"
    two_dir = CATALOG_DIR / "search" / "two"
    one_dir.mkdir(parents=True, exist_ok=True)
    two_dir.mkdir(parents=True, exist_ok=True)

    one_char_keys = sorted(indexed["one"].keys())
    two_char_keys = sorted(indexed["two"].keys())

    for key in one_char_keys:
        payload = {
            "key": key,
            "games": list(indexed["one"][key].values()),
        }
        write_json(one_dir / f"{key}.json", payload)

    for key in two_char_keys:
        payload = {
            "key": key,
            "games": list(indexed["two"][key].values()),
        }
        write_json(two_dir / f"{key}.json", payload)

    return {
        "strategy": "token-prefix-index",
        "one_char_dir": "search/one",
        "two_char_dir": "search/two",
        "one_char_keys": one_char_keys,
        "two_char_keys": two_char_keys,
    }


def write_genre_indexes(games: list[dict]) -> dict:
    genre_dir = CATALOG_DIR / "genres"
    genre_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, str] = {}
    options: list[dict] = []

    for label in GENRE_LABELS:
        slug = slugify(label)
        genre_games = [game for game in games if slug in game.get("genre_slugs", [])]
        if not genre_games:
            continue

        filename = f"genres/{slug}.json"
        write_json(CATALOG_DIR / filename, {"genre": label, "games": genre_games})
        files[slug] = filename
        options.append(
            {
                "slug": slug,
                "label": label,
                "count": len(genre_games),
            }
        )

    return {
        "files": files,
        "options": options,
    }


def main() -> None:
    aliases = load_aliases()
    steam_tag_map = fetch_steam_tag_names()

    steam_games = fetch_steam_games(steam_tag_map)
    epic_games = fetch_epic_games()
    catalog, stats = merge_games(steam_games, epic_games, aliases)

    reset_catalog_dir()

    browse_views = {
        "all": catalog,
        "steam": [game for game in catalog if game["steam_url"]],
        "epic": [game for game in catalog if game["epic_url"]],
        "both": [game for game in catalog if game["steam_url"] and game["epic_url"]],
    }

    browse_manifest = {
        view_name: paginate_games(view_games, view_name)
        for view_name, view_games in browse_views.items()
    }

    search_manifest = write_search_indexes(catalog)
    genre_manifest = write_genre_indexes(catalog)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_date": datetime.now().strftime("%Y-%m-%d"),
        "merge_method": "alias-aware-exact-normalized-title-match",
        "alias_file": str(ALIASES_FILE.relative_to(ROOT)).replace("\\", "/"),
        "sources": {
            "steam": "https://store.steampowered.com/search/results/",
            "epic": "https://store.epicgames.com/en-US/browse",
        },
        "stats": stats,
        "browse": browse_manifest,
        "search": search_manifest,
        "genres": genre_manifest,
    }

    write_json(CATALOG_DIR / "manifest.json", manifest)

    print(f"Saved catalog to {CATALOG_DIR}")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
