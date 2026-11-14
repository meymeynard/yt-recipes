"""Application services for pantry state, recipe matching, library filtering, and YouTube search."""

import math
from typing import Any, Dict, List, Tuple

import db
import matcher
import parser
import youtube_client

ITEMS_PER_PAGE = 10

BASE_CATEGORIES: Dict[str, List[str]] = {
    "🥩 Proteins": [
        "chicken breast", "chicken", "ground pork", "pork", "egg",
        "salted egg", "ground beef", "beef", "shrimp", "tofu"
    ],
    "🥦 Vegetables": [
        "ampalaya", "okra", "sayote", "carrots", "green peas", "chickpeas",
        "corn", "red bell pepper", "mushroom", "tomato", "potato", "cabbage",
        "eggplant", "sitaw", "kangkong", "bok choy"
    ],
    "🧄 Aromatics & Citrus": [
        "garlic", "white onion", "red onion", "ginger", "calamansi", "lemon", "scallions"
    ],
    "🧂 Sauces & Seasonings": [
        "soy sauce", "oyster sauce", "fish sauce", "vinegar", "sesame oil",
        "cooking oil", "salt", "black pepper", "sugar", "cornstarch", "tomato sauce"
    ],
    "✨ Other / Custom": []
}

# In-memory cache for live YouTube search results (per single-user instance)
LIVE_SEARCH_CACHE: Dict[str, Any] = {
    "query": "",
    "results": []
}


def get_categories() -> Dict[str, List[str]]:
    """Return base ingredient categories merged with user-defined custom ingredients."""
    custom_data = db.get_custom_ingredients()
    categories = {cat: list(items) for cat, items in BASE_CATEGORIES.items()}
    for cat, items in custom_data.items():
        if cat not in categories:
            categories[cat] = []
        for item in items:
            if item not in categories[cat]:
                categories[cat].append(item)
            parser.register_custom_ingredient(item)
    return categories


def add_pantry_ingredient(category: str, name: str) -> None:
    """Persist a custom ingredient, register it in the parser, and mark it active."""
    clean_name = name.lower().strip()
    if not clean_name:
        return
    db.add_custom_ingredient(category, clean_name)
    parser.register_custom_ingredient(clean_name)
    db.toggle_user_pantry_item(clean_name, True)


def paginate(items: List[Any], page: int, per_page: int = ITEMS_PER_PAGE) -> Tuple[List[Any], int, int, int]:
    """Slice a list for the requested page and return (page_items, clamped_page, total_items, total_pages)."""
    total_items = len(items)
    total_pages = max(1, math.ceil(total_items / per_page))
    clamped_page = max(1, min(page, total_pages))
    start = (clamped_page - 1) * per_page
    return items[start : start + per_page], clamped_page, total_items, total_pages


def get_matched_recipes_data(min_match: int, max_missing: int, assume_staples: bool, page: int) -> Dict[str, Any]:
    """Fetch, rank, and paginate recipes matching the user's current pantry."""
    recipes = db.get_all_recipes_with_ingredients()
    pantry = db.get_user_pantry()
    if not recipes:
        return {"has_recipes": False, "has_pantry": bool(pantry), "items": [], "page": 1, "total_items": 0}

    results = matcher.rank_recipes(
        recipes=recipes,
        user_pantry=pantry,
        min_match_pct=min_match,
        max_missing=max_missing,
        assume_staples=assume_staples,
    )
    page_items, clamped_page, total_items, _ = paginate(results, page)
    return {
        "has_recipes": True,
        "has_pantry": bool(pantry),
        "items": page_items,
        "page": clamped_page,
        "total_items": total_items,
    }


def get_library_recipes_data(q: str, channel: str, page: int) -> Dict[str, Any]:
    """Fetch, filter, and paginate all indexed recipes in the library."""
    library_recipes = db.get_all_recipes_with_ingredients()
    available_channels = ["All Channels"] + sorted(
        {r["channel_name"] for r in library_recipes if r.get("channel_name")}
    )

    filtered = library_recipes
    if channel != "All Channels":
        filtered = [r for r in filtered if r.get("channel_name") == channel]
    if q.strip():
        ql = q.lower().strip()
        filtered = [
            r for r in filtered
            if ql in r["title"].lower() or any(ql in ing.lower() for ing in r.get("ingredients", []))
        ]

    page_items, clamped_page, total_items, _ = paginate(filtered, page)
    return {
        "total_library": len(library_recipes),
        "available_channels": available_channels,
        "items": page_items,
        "page": clamped_page,
        "total_items": total_items,
    }


def perform_live_search(query: str) -> None:
    """Query YouTube Data API, parse descriptions, and store results in LIVE_SEARCH_CACHE."""
    fetched = youtube_client.search_youtube_recipes(query, max_results=20)
    processed = []
    for item in fetched:
        raw_text, parsed_ings = parser.parse_recipe_description(item["title"], item["description"])
        processed.append({**item, "raw_text": raw_text, "parsed_ings": parsed_ings})
    LIVE_SEARCH_CACHE["query"] = query
    LIVE_SEARCH_CACHE["results"] = processed


def get_search_results_data(page: int) -> Dict[str, Any]:
    """Return paginated cached YouTube search results and saved video IDs."""
    results = LIVE_SEARCH_CACHE.get("results", [])
    last_q = LIVE_SEARCH_CACHE.get("query", "") or "Chicken Sayote"
    page_items, clamped_page, total_items, _ = paginate(results, page)
    return {
        "query": last_q,
        "items": page_items,
        "page": clamped_page,
        "total_items": total_items,
        "saved_ids": db.get_saved_video_ids() if results else set(),
    }


def save_cached_search_video(video_id: str) -> None:
    """Persist a video from LIVE_SEARCH_CACHE into the SQLite recipe library."""
    target = next((r for r in LIVE_SEARCH_CACHE.get("results", []) if r["video_id"] == video_id), None)
    if not target:
        return
    db.save_recipe(
        video_id=target["video_id"],
        title=target["title"],
        channel_name=target["channel_name"],
        channel_id=target["channel_id"],
        published_at=target["published_at"],
        thumbnail_url=target["thumbnail_url"],
        description=target["description"],
        raw_ingredients_text=target["raw_text"],
        ingredients=target["parsed_ings"],
    )
