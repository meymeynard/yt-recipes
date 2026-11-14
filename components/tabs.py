"""Tab panel and tab content FastHTML UI components."""

import urllib.parse
from typing import Any, Dict, List
from fasthtml.common import A, Button, Div, Form, H3, Input, Label, Option, P, Select, Span

from services import (
    ITEMS_PER_PAGE,
    get_library_recipes_data,
    get_matched_recipes_data,
    get_search_results_data,
)
from .common import badge, empty_state, pagination, recipe_card


def matched_tab(min_match: int = 30, max_missing: int = 4, assume_staples: bool = True, page: int = 1):
    """Render the Matched Recipes tab with filter sliders and ranked recipe cards."""
    data = get_matched_recipes_data(min_match, max_missing, assume_staples, page)

    filter_form = Form(
        Input(type="hidden", name="submitted", value="1"),
        Div(
            Div(
                Div(
                    Span("Min Match %", cls="field-label"),
                    Span(f"{min_match}%", id="min-match-val", cls="range-val"),
                    cls="range-header",
                ),
                Input(
                    type="range", name="min_match", min="10", max="100", step="10", value=str(min_match),
                    oninput="document.getElementById('min-match-val').textContent = this.value + '%'",
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change",
                ),
            ),
            Div(
                Div(
                    Span("Max Missing", cls="field-label"),
                    Span(f"{max_missing}", id="max-missing-val", cls="range-val"),
                    cls="range-header",
                ),
                Input(
                    type="range", name="max_missing", min="0", max="10", step="1", value=str(max_missing),
                    oninput="document.getElementById('max-missing-val').textContent = this.value",
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change",
                ),
            ),
            Label(
                Input(
                    type="checkbox", name="assume_staples", value="true", checked=assume_staples,
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change",
                ),
                Span("Assume basic staples (oil, salt, pepper, water)"),
                cls="staples-check",
            ),
            cls="filter-bar",
        ),
        id="matched-filter-form",
    )

    if not data["has_recipes"]:
        body = empty_state(
            "🍳",
            "No recipes indexed yet",
            "Use 'Channel Sync' in the sidebar or 'Live YouTube Search' to build your recipe database.",
        )
        return Div(filter_form, body, id="matched-content")

    if data["total_items"] == 0:
        empty_msg = (
            "Select a few ingredients in the Pantry sidebar to see recipes you can cook."
            if not data["has_pantry"]
            else "Try lowering Min Match % or increasing Max Missing ingredients."
        )
        return Div(filter_form, empty_state("🥗", "No matching recipes found", empty_msg), id="matched-content")

    cards = []
    for r in data["items"]:
        badge_cls = (
            "badge-green" if r["match_percentage"] >= 80
            else ("badge-yellow" if r["match_percentage"] >= 50 else "badge-gray")
        )
        cookable = badge("🎉 Ready to Cook", "green") if r["is_cookable"] else None
        matched_badges = [badge(f"✓ {i}", "green") for i in r["matched"]]
        missing_badges = [badge(f"✗ {i}", "missing") for i in r["missing"]]
        desc_text = r["raw_ingredients_text"] if r["raw_ingredients_text"] else r["description"][:1000]
        yt_url = f"https://www.youtube.com/watch?v={r['video_id']}"

        body_rows: List[Any] = []
        if matched_badges:
            body_rows.append(Div(Span("In pantry:", cls="ing-row-label"), *matched_badges, cls="ing-row"))
        if missing_badges:
            body_rows.append(Div(Span("Missing:", cls="ing-row-label"), *missing_badges, cls="ing-row"))

        cards.append(
            recipe_card(
                title=r["title"],
                yt_url=yt_url,
                thumbnail_url=r["thumbnail_url"],
                channel_name=r["channel_name"],
                overlay_badge=Span(f"{r['match_percentage']}% Match", cls=f"thumb-overlay-badge {badge_cls}"),
                extra_badges=[cookable],
                body_rows=body_rows,
                details_summary="📖 View Recipe Ingredients & Instructions",
                details_text=desc_text,
                actions=[A("▶ Watch on YouTube", href=yt_url, target="_blank", cls="btn btn-secondary btn-sm")],
            )
        )

    base_url = (
        f"/tab/matched?submitted=1&min_match={min_match}"
        f"&max_missing={max_missing}&assume_staples={'true' if assume_staples else 'false'}"
    )
    total_items = data["total_items"]
    return Div(
        filter_form,
        Div(H3(f"Found {total_items} Matching Recipe{'s' if total_items != 1 else ''}"), cls="results-meta"),
        *cards,
        pagination(data["page"], total_items, ITEMS_PER_PAGE, base_url),
        id="matched-content",
    )


def library_tab(q: str = "", channel: str = "All Channels", page: int = 1):
    """Render the Recipe Library tab with search, channel filter, and delete actions."""
    data = get_library_recipes_data(q, channel, page)

    if data["total_library"] == 0:
        return Div(
            empty_state(
                "📚",
                "Your Recipe Library is empty",
                "Use 'Channel Sync' in the sidebar or 'Live YouTube Search' to add cooking videos.",
            ),
            id="library-content",
        )

    filter_form = Form(
        Input(type="hidden", name="submitted", value="1"),
        Div(
            Label(
                "Search Library by title or ingredient",
                Input(
                    type="search", name="q", value=q, placeholder="e.g. adobo, ampalaya, chicken",
                    cls="input",
                    hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#library-filter-form", hx_trigger="keyup changed delay:300ms, search",
                ),
                cls="field-label",
            ),
            Label(
                "Filter by Channel",
                Select(
                    *[Option(c, value=c, selected=(c == channel)) for c in data["available_channels"]],
                    name="channel",
                    cls="select",
                    hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#library-filter-form", hx_trigger="change",
                ),
                cls="field-label",
            ),
            cls="filter-bar",
        ),
        id="library-filter-form",
    )

    cards = []
    for r in data["items"]:
        yt_url = f"https://www.youtube.com/watch?v={r['video_id']}"
        ings = r.get("ingredients", [])
        ing_badges = [badge(i, "green") for i in ings]
        desc_text = r["raw_ingredients_text"] if r["raw_ingredients_text"] else r["description"][:1000]

        ing_row = (
            Div(Span(f"Ingredients ({len(ings)}):", cls="ing-row-label"), *ing_badges, cls="ing-row")
            if ings
            else P("No specific ingredients parsed.", style="font-size: 0.85rem; color: var(--text-muted); margin: 0;")
        )

        cards.append(
            recipe_card(
                card_id=f"lib-card-{r['video_id']}",
                title=r["title"],
                yt_url=yt_url,
                thumbnail_url=r["thumbnail_url"],
                channel_name=r["channel_name"],
                body_rows=[ing_row],
                details_summary="📖 View Recipe Description",
                details_text=desc_text,
                actions=[
                    A("▶ Watch on YouTube", href=yt_url, target="_blank", cls="btn btn-secondary btn-sm"),
                    Button(
                        "🗑️ Remove",
                        cls="btn btn-danger-ghost btn-sm",
                        hx_delete=f"/library/{r['video_id']}",
                        hx_target=f"#lib-card-{r['video_id']}",
                        hx_swap="outerHTML",
                    ),
                ],
            )
        )

    body_content = cards if cards else [
        empty_state("🔎", "No recipes match your filter", "Try clearing your search query or selecting 'All Channels'.")
    ]
    base_url = f"/tab/library?q={urllib.parse.quote(q)}&channel={urllib.parse.quote(channel)}"
    return Div(
        filter_form,
        Div(
            H3(f"📚 Recipe Library ({data['total_library']} Total)"),
            Span(f"Showing {data['total_items']} of {data['total_library']}"),
            cls="results-meta",
        ),
        *body_content,
        pagination(data["page"], data["total_items"], ITEMS_PER_PAGE, base_url),
        id="library-content",
    )


def search_tab(page: int = 1):
    """Render the Live YouTube Search tab with on-demand search and save buttons."""
    data = get_search_results_data(page)

    search_form = Form(
        Div(
            Label(
                "Search YouTube for a recipe or ingredient combo",
                Input(type="text", name="q", value=data["query"], placeholder="e.g. Chicken Sayote", required=True, cls="input"),
                cls="field-label",
            ),
            Button("🔍 Search YouTube", Span(" ⏳", cls="htmx-indicator"), type="submit", cls="btn btn-primary"),
            cls="filter-bar",
            style="grid-template-columns: 1fr auto;",
        ),
        hx_post="/search",
        hx_target="#tab-panel",
        hx_swap="outerHTML",
    )

    if data["total_items"] == 0:
        return Div(
            search_form,
            empty_state(
                "🎬",
                "Search YouTube On-Demand",
                "Enter a dish or ingredient combo above to fetch recipes from YouTube and save them to your library.",
            ),
            id="search-content",
        )

    saved_ids = data["saved_ids"]
    cards = []
    for item in data["items"]:
        vid = item["video_id"]
        is_saved = vid in saved_ids
        yt_url = f"https://www.youtube.com/watch?v={vid}"
        ing_names = [i["name"] for i in item["parsed_ings"]]

        saved_badge = badge("✓ In Library", "green") if is_saved else None
        action_btn = (
            Button("✅ Already in Database", disabled=True, cls="btn btn-secondary btn-sm")
            if is_saved
            else Button(
                "💾 Save to Database",
                cls="btn btn-primary btn-sm",
                hx_post=f"/search/save/{vid}",
                hx_target=f"#save-wrap-{vid}",
                hx_swap="outerHTML",
            )
        )

        ing_pills = (
            [badge(name, "gray") for name in ing_names]
            if ing_names
            else [Span("None detected", style="color: var(--text-muted); font-size: 0.84rem;")]
        )

        cards.append(
            recipe_card(
                title=item["title"],
                yt_url=yt_url,
                thumbnail_url=item["thumbnail_url"],
                channel_name=item["channel_name"],
                extra_badges=[saved_badge],
                body_rows=[Div(Span(f"Parsed Ingredients ({len(ing_names)}):", cls="ing-row-label"), *ing_pills, cls="ing-row")],
                actions=[
                    Div(action_btn, id=f"save-wrap-{vid}"),
                    A("▶ Watch on YouTube", href=yt_url, target="_blank", cls="btn btn-secondary btn-sm"),
                ],
            )
        )

    return Div(
        search_form,
        Div(H3(f"Results for “{data['query']}”"), Span(f"{data['total_items']} videos found"), cls="results-meta"),
        *cards,
        pagination(data["page"], data["total_items"], ITEMS_PER_PAGE, "/tab/search?x=1"),
        id="search-content",
    )


def tab_panel(active_tab: str, **kwargs: Any):
    """Render the segmented tab bar and active tab content inside #tab-panel."""
    tabs_nav = Div(
        Input(type="hidden", id="active-tab-input", name="tab", value=active_tab),
        Button(
            "✨ Matched Recipes",
            cls=f"tab-btn {'active' if active_tab == 'matched' else ''}",
            hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
        ),
        Button(
            "📚 Recipe Library",
            cls=f"tab-btn {'active' if active_tab == 'library' else ''}",
            hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
        ),
        Button(
            "🔍 Live YouTube Search",
            cls=f"tab-btn {'active' if active_tab == 'search' else ''}",
            hx_get="/tab/search", hx_target="#tab-panel", hx_swap="outerHTML",
        ),
        cls="tabs",
    )

    if active_tab == "library":
        content = library_tab(
            q=kwargs.get("q", ""),
            channel=kwargs.get("channel", "All Channels"),
            page=kwargs.get("page", 1),
        )
    elif active_tab == "search":
        content = search_tab(page=kwargs.get("page", 1))
    else:
        content = matched_tab(
            min_match=kwargs.get("min_match", 30),
            max_missing=kwargs.get("max_missing", 4),
            assume_staples=kwargs.get("assume_staples", True),
            page=kwargs.get("page", 1),
        )

    return Div(tabs_nav, content, id="tab-panel")
