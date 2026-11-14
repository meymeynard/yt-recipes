import os
import json
import math
from typing import List, Dict, Any
from fasthtml.common import *

import db
import parser
import matcher
import youtube_client
import ingest

ITEMS_PER_PAGE = 10

BASE_CATEGORIES = {
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

# Initialize DB on startup
db.init_db()

# In-memory cache for live YouTube search results (per single-user instance)
LIVE_SEARCH_CACHE: Dict[str, Any] = {
    "query": "",
    "results": []
}

CUSTOM_CSS = Style("""
:root {
    --pico-font-size: 15px;
    --pico-spacing: 0.75rem;
}
body {
    margin: 0;
    background: #f8fafc;
    color: #1e293b;
}
.app-layout {
    display: grid;
    grid-template-columns: 320px 1fr;
    min-height: 100vh;
}
@media (max-width: 900px) {
    .app-layout { grid-template-columns: 1fr; }
}
.sidebar {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
    padding: 1.25rem;
}
.main-content {
    padding: 1.5rem 2rem;
    max-width: 1100px;
    width: 100%;
    box-sizing: border-box;
}
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 2px 4px 2px 0;
}
.badge-green { background: #d1fae5; color: #065f46; border: 1px solid #34d399; }
.badge-yellow { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
.badge-gray { background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; }
.badge-missing { background: #fee2e2; color: #991b1b; border: 1px solid #f87171; }
.recipe-card {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 1.25rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
@media (max-width: 700px) {
    .recipe-card { grid-template-columns: 1fr; }
}
.recipe-thumb {
    width: 100%;
    border-radius: 8px;
    object-fit: cover;
    aspect-ratio: 16/9;
}
.tabs {
    display: flex;
    gap: 0.5rem;
    border-bottom: 2px solid #e2e8f0;
    margin-bottom: 1.25rem;
}
.tab-btn {
    background: transparent !important;
    border: none !important;
    border-bottom: 3px solid transparent !important;
    border-radius: 0 !important;
    padding: 0.6rem 1rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    cursor: pointer;
    margin: 0 0 -2px 0 !important;
    width: auto !important;
    box-shadow: none !important;
}
.tab-btn.active {
    color: #0f172a !important;
    border-bottom-color: #ef4444 !important;
}
.pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid #e2e8f0;
}
.pagination button {
    width: auto !important;
    margin: 0 !important;
    padding: 0.45rem 1rem !important;
}
.cat-list label {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.35rem;
    font-size: 0.92rem;
    cursor: pointer;
}
.cat-list input[type="checkbox"] {
    margin: 0;
}
.btn-inline {
    width: auto !important;
    display: inline-block !important;
    padding: 0.4rem 0.85rem !important;
    font-size: 0.85rem !important;
    margin: 0.25rem 0.5rem 0.25rem 0 !important;
}
.filter-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-bottom: 1rem;
    align-items: end;
}
.filter-bar label {
    margin-bottom: 0;
    font-size: 0.85rem;
}
.filter-bar input, .filter-bar select {
    margin-bottom: 0 !important;
}
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator { display: inline-block; }
""")

app, rt = fast_app(
    pico=True,
    hdrs=(
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="theme-color", content="#ef4444"),
        Link(rel="manifest", href="/manifest.json"),
        CUSTOM_CSS,
    )
)


def get_categories() -> Dict[str, List[str]]:
    custom_data = db.get_custom_ingredients()
    categories = {cat: list(items) for cat, items in BASE_CATEGORIES.items()}
    for cat, items in custom_data.items():
        if cat not in categories:
            categories[cat] = []
        for it in items:
            if it not in categories[cat]:
                categories[cat].append(it)
            parser.register_custom_ingredient(it)
    return categories


def render_pantry_chips(pantry: List[str], oob: bool = False):
    attrs = {"id": "pantry-chips"}
    if oob:
        attrs["hx_swap_oob"] = "true"
    if pantry:
        return Div(
            P(f"You have ", Strong(f"{len(pantry)} ingredients"), " selected in your pantry."),
            Div(*[Span(f"✓ {item}", cls="badge badge-green") for item in sorted(pantry)]),
            **attrs
        )
    return Div(
        P("You have ", Strong("0 ingredients"), " selected in your pantry."),
        Div("Your pantry is empty! Select ingredients in the sidebar checklist.", cls="badge badge-gray"),
        **attrs
    )


def render_stats(oob: bool = False):
    stats = db.get_stats()
    attrs = {"id": "db-stats", "style": "font-size: 0.85rem; color: #64748b; margin-top: 0.5rem;"}
    if oob:
        attrs["hx_swap_oob"] = "true"
    return Div(
        "📊 Indexed Recipes: ", Strong(str(stats["recipes"])),
        " | Unique Ingredients: ", Strong(str(stats["ingredients"])),
        **attrs
    )


def render_sidebar_categories(categories: Dict[str, List[str]], saved_pantry: set, oob: bool = False):
    attrs = {"id": "sidebar-categories"}
    if oob:
        attrs["hx_swap_oob"] = "true"

    accordions = []
    for cat_name, items in categories.items():
        if not items:
            continue
        is_open = cat_name in ["🥩 Proteins", "🥦 Vegetables"]
        checkboxes = [
            Label(
                Input(
                    type="checkbox",
                    name="active",
                    value="true",
                    checked=(item in saved_pantry),
                    hx_post="/pantry/toggle",
                    hx_vals=json.dumps({"item": item}),
                    hx_include="#active-tab-input, #matched-filter-form",
                    hx_swap="none",
                ),
                item.title()
            )
            for item in items
        ]
        accordions.append(
            Details(
                Summary(Strong(cat_name)),
                Div(*checkboxes, cls="cat-list"),
                open=is_open
            )
        )
    return Div(*accordions, **attrs)


def render_sidebar(oob: bool = False):
    categories = get_categories()
    saved_pantry = db.get_user_pantry()

    attrs = {"id": "sidebar-panel", "cls": "sidebar"}
    if oob:
        attrs["hx_swap_oob"] = "true"

    return Aside(
        H3("🍳 Pantry Inventory", style="margin-bottom: 0.75rem;"),
        Button(
            "🗑️ Clear All",
            cls="outline secondary",
            style="width: 100%; margin-bottom: 0.75rem;",
            hx_post="/pantry/clear",
            hx_include="#active-tab-input, #matched-filter-form",
            hx_swap="none",
        ),
        Details(
            Summary("➕ Add Ingredient to Category"),
            Form(
                Label(
                    "Category",
                    Select(
                        *[Option(c, value=c) for c in categories.keys()],
                        name="category"
                    )
                ),
                Label(
                    "Ingredient Name",
                    Input(type="text", name="name", placeholder="e.g. Coconut milk, Pork belly", required=True)
                ),
                Button("Add Ingredient", type="submit", style="width: 100%;"),
                hx_post="/pantry/add",
                hx_include="#active-tab-input, #matched-filter-form",
                hx_swap="none",
            ),
            style="margin-bottom: 0.75rem;"
        ),
        render_sidebar_categories(categories, saved_pantry),
        Hr(),
        H4("⚙️ Channel Sync", style="margin-bottom: 0.5rem;"),
        Form(
            Label(
                "YouTube Channel Link, @Handle, or Name",
                Input(
                    type="text",
                    name="channel",
                    value="https://www.youtube.com/@PanlasangPinoy",
                    placeholder="URL, @handle, or name",
                    required=True
                )
            ),
            Label(
                "Videos to fetch",
                Select(
                    *[Option(str(n), value=str(n), selected=(n == 30)) for n in [10, 20, 30, 40, 50, 60]],
                    name="limit"
                )
            ),
            Button(
                "📥 Sync Channel to Database",
                Span(" ⏳", cls="htmx-indicator"),
                type="submit",
                style="width: 100%;"
            ),
            Div(id="sync-status", style="margin-top: 0.5rem; font-size: 0.85rem;"),
            hx_post="/sync",
            hx_target="#sync-status",
            hx_include="#active-tab-input, #matched-filter-form",
        ),
        render_stats(),
        **attrs
    )


def render_pagination(current_page: int, total_items: int, items_per_page: int, base_url: str, include_selector: str = ""):
    total_pages = max(1, math.ceil(total_items / items_per_page))
    if total_pages <= 1:
        return Div()

    start_idx = (current_page - 1) * items_per_page + 1
    end_idx = min(current_page * items_per_page, total_items)

    prev_attrs = {
        "cls": "outline",
        "disabled": (current_page <= 1),
        "hx_get": f"{base_url}&page={max(1, current_page - 1)}",
        "hx_target": "#tab-panel",
        "hx_swap": "outerHTML",
    }
    next_attrs = {
        "cls": "outline",
        "disabled": (current_page >= total_pages),
        "hx_get": f"{base_url}&page={min(total_pages, current_page + 1)}",
        "hx_target": "#tab-panel",
        "hx_swap": "outerHTML",
    }
    if include_selector:
        prev_attrs["hx_include"] = include_selector
        next_attrs["hx_include"] = include_selector

    return Div(
        Button("⬅️ Previous", **prev_attrs),
        Span(
            Strong(f"Page {current_page} of {total_pages}"),
            f" (Showing {start_idx}–{end_idx} of {total_items})",
            style="font-size: 0.9rem; color: #475569;"
        ),
        Button("Next ➡️", **next_attrs),
        cls="pagination"
    )


def render_matched_tab(min_match: int = 30, max_missing: int = 4, assume_staples: bool = True, page: int = 1):
    recipes = db.get_all_recipes_with_ingredients()
    pantry = db.get_user_pantry()

    filter_form = Form(
        Input(type="hidden", name="submitted", value="1"),
        Div(
            Label(
                f"Min Match % ({min_match}%)",
                Input(
                    type="range", name="min_match", min="10", max="100", step="10", value=str(min_match),
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change"
                )
            ),
            Label(
                f"Max Missing ({max_missing})",
                Input(
                    type="range", name="max_missing", min="0", max="10", step="1", value=str(max_missing),
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change"
                )
            ),
            Label(
                Input(
                    type="checkbox", name="assume_staples", value="true", checked=assume_staples,
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change"
                ),
                " Assume basic staples (oil, salt, pepper, water)",
                style="display: flex; align-items: center; gap: 0.4rem; padding-bottom: 0.4rem;"
            ),
            cls="filter-bar"
        ),
        id="matched-filter-form"
    )

    if not recipes:
        body = P("No recipes in local database yet! Click 'Sync Channel to Database' in the sidebar.", cls="badge badge-yellow")
        return Div(filter_form, body, id="matched-content")

    results = matcher.rank_recipes(
        recipes=recipes,
        user_pantry=pantry,
        min_match_pct=min_match,
        max_missing=max_missing,
        assume_staples=assume_staples
    )

    total_items = len(results)
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
    page = max(1, min(page, total_pages))
    page_items = results[(page - 1) * ITEMS_PER_PAGE : page * ITEMS_PER_PAGE]

    cards = []
    for r in page_items:
        badge_cls = "badge-green" if r["match_percentage"] >= 80 else ("badge-yellow" if r["match_percentage"] >= 50 else "badge-gray")
        cookable = Span("🎉 Ready to Cook!", cls="badge badge-green") if r["is_cookable"] else ""
        matched_badges = [Span(f"✓ {i}", cls="badge badge-green") for i in r["matched"]]
        missing_badges = [Span(f"✗ {i}", cls="badge badge-missing") for i in r["missing"]]

        desc_text = r["raw_ingredients_text"] if r["raw_ingredients_text"] else r["description"][:1000]
        yt_url = f"https://www.youtube.com/watch?v={r['video_id']}"

        cards.append(
            Div(
                Img(src=r["thumbnail_url"], alt=r["title"], cls="recipe-thumb"),
                Div(
                    H4(A(r["title"], href=yt_url, target="_blank"), style="margin-bottom: 0.35rem;"),
                    Div(
                        Span(f"{r['match_percentage']}% Match", cls=f"badge {badge_cls}"),
                        Span(r["channel_name"], cls="badge badge-gray"),
                        cookable,
                        style="margin-bottom: 0.5rem;"
                    ),
                    Div(Strong("In your pantry: "), *matched_badges) if matched_badges else "",
                    Div(Strong("Missing: "), *missing_badges) if missing_badges else "",
                    Details(
                        Summary("📖 View Recipe Ingredients & Instructions"),
                        Pre(desc_text, style="white-space: pre-wrap; font-size: 0.85rem; background: #f8fafc; padding: 0.75rem; border-radius: 6px;"),
                        style="margin-top: 0.5rem;"
                    ),
                    A("▶️ Watch Video on YouTube", href=yt_url, target="_blank", role="button", cls="outline btn-inline"),
                ),
                cls="recipe-card"
            )
        )

    base_url = f"/tab/matched?submitted=1&min_match={min_match}&max_missing={max_missing}&assume_staples={'true' if assume_staples else 'false'}"
    return Div(
        filter_form,
        H4(f"Found {total_items} Matching Recipes", style="margin-bottom: 0.75rem;"),
        *cards,
        render_pagination(page, total_items, ITEMS_PER_PAGE, base_url),
        id="matched-content"
    )


def render_library_tab(q: str = "", channel: str = "All Channels", page: int = 1):
    library_recipes = db.get_all_recipes_with_ingredients()

    if not library_recipes:
        return Div(
            H4("📚 Recipe Library (0 Total)"),
            P("No recipes in your library yet! Use the sidebar 'Channel Sync' or 'Live YouTube Search' tab to add some.")
        )

    available_channels = ["All Channels"] + sorted({r["channel_name"] for r in library_recipes if r.get("channel_name")})

    filter_form = Form(
        Input(type="hidden", name="submitted", value="1"),
        Div(
            Label(
                "Search Library by title or ingredient",
                Input(
                    type="search", name="q", value=q, placeholder="e.g. adobo, ampalaya, chicken",
                    hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#library-filter-form", hx_trigger="keyup changed delay:300ms, search"
                )
            ),
            Label(
                "Filter by Channel",
                Select(
                    *[Option(c, value=c, selected=(c == channel)) for c in available_channels],
                    name="channel",
                    hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#library-filter-form", hx_trigger="change"
                )
            ),
            cls="filter-bar"
        ),
        id="library-filter-form"
    )

    display_recipes = library_recipes
    if channel != "All Channels":
        display_recipes = [r for r in display_recipes if r.get("channel_name") == channel]
    if q.strip():
        ql = q.lower().strip()
        display_recipes = [
            r for r in display_recipes
            if ql in r["title"].lower() or any(ql in ing.lower() for ing in r.get("ingredients", []))
        ]

    total_items = len(display_recipes)
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
    page = max(1, min(page, total_pages))
    page_items = display_recipes[(page - 1) * ITEMS_PER_PAGE : page * ITEMS_PER_PAGE]

    cards = []
    for r in page_items:
        yt_url = f"https://www.youtube.com/watch?v={r['video_id']}"
        ings = r.get("ingredients", [])
        ing_badges = [Span(i, cls="badge badge-green") for i in ings]
        desc_text = r["raw_ingredients_text"] if r["raw_ingredients_text"] else r["description"][:1000]

        cards.append(
            Div(
                Img(src=r["thumbnail_url"], alt=r["title"], cls="recipe-thumb"),
                Div(
                    H4(A(r["title"], href=yt_url, target="_blank"), style="margin-bottom: 0.35rem;"),
                    Span(r["channel_name"], cls="badge badge-gray"),
                    Div(Strong(f"Ingredients ({len(ings)}): "), *ing_badges, style="margin-top: 0.4rem;") if ings else P("No specific ingredients parsed.", style="font-size: 0.85rem; color: #64748b;"),
                    Details(
                        Summary("📖 View Recipe Description"),
                        Pre(desc_text, style="white-space: pre-wrap; font-size: 0.85rem; background: #f8fafc; padding: 0.75rem; border-radius: 6px;"),
                        style="margin-top: 0.5rem;"
                    ),
                    Div(
                        A("▶️ Watch Video on YouTube", href=yt_url, target="_blank", role="button", cls="outline btn-inline"),
                        Button(
                            "🗑️ Remove",
                            cls="outline secondary btn-inline",
                            hx_delete=f"/library/{r['video_id']}",
                            hx_target=f"#lib-card-{r['video_id']}",
                            hx_swap="outerHTML",
                        ),
                        style="margin-top: 0.5rem;"
                    )
                ),
                id=f"lib-card-{r['video_id']}",
                cls="recipe-card"
            )
        )

    import urllib.parse
    base_url = f"/tab/library?q={urllib.parse.quote(q)}&channel={urllib.parse.quote(channel)}"
    return Div(
        H4(f"📚 Recipe Library ({len(library_recipes)} Total)", style="margin-bottom: 0.25rem;"),
        P("Browse and search all cooking videos currently indexed in your database.", style="color: #64748b; font-size: 0.9rem;"),
        filter_form,
        P(f"Showing ", Strong(str(total_items)), f" of {len(library_recipes)} recipes (10 per page)", style="font-size: 0.88rem; color: #64748b;"),
        *cards,
        render_pagination(page, total_items, ITEMS_PER_PAGE, base_url),
        id="library-content"
    )


def render_search_tab(page: int = 1):
    results = LIVE_SEARCH_CACHE.get("results", [])
    last_q = LIVE_SEARCH_CACHE.get("query", "") or "Chicken Sayote"

    search_form = Form(
        Div(
            Label(
                "Search query",
                Input(type="text", name="q", value=last_q, placeholder="e.g. Chicken Sayote", required=True)
            ),
            Button("🔍 Search YouTube", Span(" ⏳", cls="htmx-indicator"), type="submit", style="width: auto; margin: 0;"),
            cls="filter-bar",
            style="grid-template-columns: 1fr auto;"
        ),
        hx_post="/search",
        hx_target="#tab-panel",
        hx_swap="outerHTML",
    )

    if not results:
        return Div(
            H4("Query YouTube Data API On-Demand", style="margin-bottom: 0.25rem;"),
            P("Search for any specific recipe or ingredient combo and import it directly into your database.", style="color: #64748b; font-size: 0.9rem;"),
            search_form,
            id="search-content"
        )

    saved_ids = db.get_saved_video_ids()
    total_items = len(results)
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
    page = max(1, min(page, total_pages))
    page_items = results[(page - 1) * ITEMS_PER_PAGE : page * ITEMS_PER_PAGE]

    cards = []
    for item in page_items:
        vid = item["video_id"]
        is_saved = vid in saved_ids
        yt_url = f"https://www.youtube.com/watch?v={vid}"
        ing_names = [i["name"] for i in item["parsed_ings"]]

        saved_badge = Span("✓ In Library", cls="badge badge-green") if is_saved else ""
        action_btn = (
            Button("✅ Already in Database", disabled=True, cls="btn-inline secondary")
            if is_saved
            else Button(
                "💾 Save to Database",
                cls="btn-inline",
                hx_post=f"/search/save/{vid}",
                hx_target=f"#save-wrap-{vid}",
                hx_swap="outerHTML",
            )
        )

        cards.append(
            Div(
                Img(src=item["thumbnail_url"], alt=item["title"], cls="recipe-thumb"),
                Div(
                    H4(A(item["title"], href=yt_url, target="_blank"), " ", saved_badge, style="margin-bottom: 0.25rem;"),
                    P(f"Channel: {item['channel_name']}", style="font-size: 0.85rem; color: #64748b; margin-bottom: 0.4rem;"),
                    P(Strong(f"Parsed Ingredients ({len(ing_names)}): "), ", ".join(ing_names) if ing_names else "None detected", style="font-size: 0.9rem;"),
                    Div(action_btn, id=f"save-wrap-{vid}"),
                ),
                cls="recipe-card"
            )
        )

    return Div(
        H4("Query YouTube Data API On-Demand", style="margin-bottom: 0.25rem;"),
        P("Search for any specific recipe or ingredient combo and import it directly into your database.", style="color: #64748b; font-size: 0.9rem;"),
        search_form,
        P(f"Showing results for: ", Strong(last_q), f" ({total_items} videos found, 10 per page)", style="font-size: 0.9rem;"),
        *cards,
        render_pagination(page, total_items, ITEMS_PER_PAGE, "/tab/search?x=1"),
        id="search-content"
    )


def render_tab_panel(active_tab: str, **kwargs):
    tabs_nav = Div(
        Input(type="hidden", id="active-tab-input", name="tab", value=active_tab),
        Button(
            "✨ Matched Recipes",
            cls=f"tab-btn {'active' if active_tab == 'matched' else ''}",
            hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML"
        ),
        Button(
            "📚 Recipe Library",
            cls=f"tab-btn {'active' if active_tab == 'library' else ''}",
            hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML"
        ),
        Button(
            "🔍 Live YouTube Search",
            cls=f"tab-btn {'active' if active_tab == 'search' else ''}",
            hx_get="/tab/search", hx_target="#tab-panel", hx_swap="outerHTML"
        ),
        cls="tabs"
    )

    if active_tab == "library":
        content = render_library_tab(
            q=kwargs.get("q", ""),
            channel=kwargs.get("channel", "All Channels"),
            page=kwargs.get("page", 1)
        )
    elif active_tab == "search":
        content = render_search_tab(page=kwargs.get("page", 1))
    else:
        content = render_matched_tab(
            min_match=kwargs.get("min_match", 30),
            max_missing=kwargs.get("max_missing", 4),
            assume_staples=kwargs.get("assume_staples", True),
            page=kwargs.get("page", 1)
        )

    return Div(tabs_nav, content, id="tab-panel")


@rt("/")
def get():
    pantry = sorted(list(db.get_user_pantry()))
    return Title("Pantry Chef | YouTube Recipe Aggregator"), Div(
        render_sidebar(),
        Main(
            H1("🍳 What Can I Cook Today?", style="margin-bottom: 0.5rem;"),
            render_pantry_chips(pantry),
            Br(),
            render_tab_panel("matched"),
            cls="main-content"
        ),
        cls="app-layout",
        id="app-shell"
    )


@rt("/health")
def health():
    return Response("ok", media_type="text/plain")


@rt("/manifest.json")
def manifest():
    return JSONResponse({
        "name": "Pantry Chef | YouTube Recipe Aggregator",
        "short_name": "Pantry Chef",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f8fafc",
        "theme_color": "#ef4444",
    })


@rt("/tab/matched")
def tab_matched(min_match: int = 30, max_missing: int = 4, assume_staples: str = "", submitted: str = "", page: int = 1):
    is_staples = (assume_staples == "true") if submitted else True
    return render_tab_panel("matched", min_match=min_match, max_missing=max_missing, assume_staples=is_staples, page=page)


@rt("/tab/library")
def tab_library(q: str = "", channel: str = "All Channels", page: int = 1):
    return render_tab_panel("library", q=q, channel=channel, page=page)


@rt("/tab/search")
def tab_search(page: int = 1):
    return render_tab_panel("search", page=page)


@rt("/pantry/toggle")
def post(item: str, active: str = "", tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    db.toggle_user_pantry_item(item, active == "true")
    pantry = sorted(list(db.get_user_pantry()))
    chips_oob = render_pantry_chips(pantry, oob=True)

    if tab == "matched":
        is_staples = (assume_staples == "true")
        matched_oob = render_matched_tab(min_match=min_match, max_missing=max_missing, assume_staples=is_staples, page=1)
        matched_oob.attrs["hx_swap_oob"] = "true"
        return chips_oob, matched_oob
    return chips_oob


@rt("/pantry/clear")
def post(tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    db.clear_user_pantry()
    categories = get_categories()
    sidebar_cats_oob = render_sidebar_categories(categories, set(), oob=True)
    chips_oob = render_pantry_chips([], oob=True)

    if tab == "matched":
        is_staples = (assume_staples == "true")
        matched_oob = render_matched_tab(min_match=min_match, max_missing=max_missing, assume_staples=is_staples, page=1)
        matched_oob.attrs["hx_swap_oob"] = "true"
        return sidebar_cats_oob, chips_oob, matched_oob
    return sidebar_cats_oob, chips_oob


@rt("/pantry/add")
def post(category: str, name: str, tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    clean_name = name.lower().strip()
    if clean_name:
        db.add_custom_ingredient(category, clean_name)
        parser.register_custom_ingredient(clean_name)
        db.toggle_user_pantry_item(clean_name, True)

    categories = get_categories()
    saved_pantry = db.get_user_pantry()
    sidebar_cats_oob = render_sidebar_categories(categories, saved_pantry, oob=True)
    chips_oob = render_pantry_chips(sorted(list(saved_pantry)), oob=True)

    if tab == "matched":
        is_staples = (assume_staples == "true")
        matched_oob = render_matched_tab(min_match=min_match, max_missing=max_missing, assume_staples=is_staples, page=1)
        matched_oob.attrs["hx_swap_oob"] = "true"
        return sidebar_cats_oob, chips_oob, matched_oob
    return sidebar_cats_oob, chips_oob


@rt("/sync")
def post(channel: str, limit: int = 30, tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    count = ingest.ingest_channel(channel, max_videos=limit)
    stats_oob = render_stats(oob=True)
    if count > 0:
        msg = Span(f"✅ Synced {count} videos into database!", cls="badge badge-green")
    else:
        msg = Span(f"❌ Could not find channel: '{channel}'", cls="badge badge-missing")

    if tab == "matched":
        is_staples = (assume_staples == "true")
        matched_oob = render_matched_tab(min_match=min_match, max_missing=max_missing, assume_staples=is_staples, page=1)
        matched_oob.attrs["hx_swap_oob"] = "true"
        return msg, stats_oob, matched_oob
    return msg, stats_oob


@rt("/search")
def post(q: str):
    fetched_videos = youtube_client.search_youtube_recipes(q, max_results=20)
    processed_results = []
    for item in fetched_videos:
        raw_text, parsed_ings = parser.parse_recipe_description(item["title"], item["description"])
        processed_results.append({
            **item,
            "raw_text": raw_text,
            "parsed_ings": parsed_ings
        })
    LIVE_SEARCH_CACHE["query"] = q
    LIVE_SEARCH_CACHE["results"] = processed_results
    return render_tab_panel("search", page=1)


@rt("/search/save/{video_id}")
def post(video_id: str):
    results = LIVE_SEARCH_CACHE.get("results", [])
    target = next((r for r in results if r["video_id"] == video_id), None)
    if target:
        db.save_recipe(
            video_id=target["video_id"],
            title=target["title"],
            channel_name=target["channel_name"],
            channel_id=target["channel_id"],
            published_at=target["published_at"],
            thumbnail_url=target["thumbnail_url"],
            description=target["description"],
            raw_ingredients_text=target["raw_text"],
            ingredients=target["parsed_ings"]
        )
    stats_oob = render_stats(oob=True)
    btn = Div(Button("✅ Already in Database", disabled=True, cls="btn-inline secondary"), id=f"save-wrap-{video_id}")
    return btn, stats_oob


@rt("/library/{video_id}")
def delete(video_id: str):
    db.delete_recipe(video_id)
    stats_oob = render_stats(oob=True)
    return stats_oob


if __name__ == "__main__":
    serve(host="0.0.0.0", port=int(os.environ.get("PORT", 8501)))
