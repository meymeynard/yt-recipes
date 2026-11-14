"""Sidebar and pantry-chip FastHTML UI components."""

import json
from typing import Dict, List
from fasthtml.common import (
    Aside, Button, Details, Div, Form, H3, H4, Input, Label, Option, Select, Span, Strong, Summary
)

from .common import badge


def pantry_chips(pantry: List[str], oob: bool = False):
    """Render the active pantry ingredient summary card."""
    attrs = {"id": "pantry-chips", "cls": "pantry-summary"}
    if oob:
        attrs["hx_swap_oob"] = "true"

    if pantry:
        return Div(
            Div(
                Span("Selected Pantry: ", Strong(f"{len(pantry)} ingredient{'s' if len(pantry) != 1 else ''}")),
                Button(
                    "Clear all",
                    cls="btn btn-ghost btn-sm",
                    hx_post="/pantry/clear",
                    hx_include="#active-tab-input, #matched-filter-form",
                    hx_swap="none",
                ),
                cls="pantry-summary-head",
            ),
            Div(*[badge(f"✓ {item}", "green") for item in sorted(pantry)], cls="chips-wrap"),
            **attrs,
        )

    return Div(
        Div(Span("Selected Pantry: ", Strong("0 ingredients")), cls="pantry-summary-head"),
        Div(
            badge("Your pantry is empty — check ingredients in the sidebar to match recipes.", "gray"),
            cls="chips-wrap",
        ),
        **attrs,
    )


def db_stats(recipes_count: int, ingredients_count: int, oob: bool = False):
    """Render the indexed recipes and unique ingredients stat boxes."""
    attrs = {"id": "db-stats", "cls": "stats-grid"}
    if oob:
        attrs["hx_swap_oob"] = "true"

    return Div(
        Div(Span(str(recipes_count), cls="stat-num"), Span("Recipes", cls="stat-label"), cls="stat-box"),
        Div(Span(str(ingredients_count), cls="stat-num"), Span("Ingredients", cls="stat-label"), cls="stat-box"),
        **attrs,
    )


def sidebar_categories(categories: Dict[str, List[str]], saved_pantry: set, oob: bool = False):
    """Render collapsible ingredient category accordions with checkable pills."""
    attrs = {"id": "sidebar-categories"}
    if oob:
        attrs["hx_swap_oob"] = "true"

    accordions = []
    for cat_name, items in categories.items():
        if not items:
            continue
        is_open = cat_name in ["🥩 Proteins", "🥦 Vegetables"]
        selected_count = sum(1 for item in items if item in saved_pantry)
        count_cls = "cat-count has-selected" if selected_count > 0 else "cat-count"
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
                Span(item.title()),
                cls="ing-pill",
            )
            for item in items
        ]
        accordions.append(
            Details(
                Summary(
                    Span(cat_name),
                    Span(f"{selected_count}/{len(items)}", cls=count_cls),
                ),
                Div(Div(*checkboxes, cls="cat-list"), cls="accordion-body"),
                cls="accordion",
                open=is_open,
            )
        )
    return Div(*accordions, **attrs)


def sidebar(
    categories: Dict[str, List[str]],
    saved_pantry: set,
    stats: Dict[str, int],
    oob: bool = False,
):
    """Render the full Pantry Chef sidebar (filter, categories, add ingredient, channel sync)."""
    attrs = {"id": "sidebar-panel", "cls": "sidebar"}
    if oob:
        attrs["hx_swap_oob"] = "true"

    return Aside(
        Div(
            H3("🍳 Pantry Chef", cls="sidebar-title"),
            Button(
                "✕",
                cls="btn btn-ghost btn-sm sidebar-close-btn",
                type="button",
                onclick="toggleSidebar(false)",
                aria_label="Close pantry sidebar",
            ),
            cls="sidebar-brand",
        ),
        Input(
            type="search",
            placeholder="Filter ingredients (e.g. garlic, pork)...",
            cls="input pantry-filter-input",
            oninput="filterPantryIngredients(this.value)",
            aria_label="Filter pantry ingredients",
        ),
        Div(
            Button(
                "🗑️ Clear Pantry",
                cls="btn btn-secondary btn-sm btn-full",
                hx_post="/pantry/clear",
                hx_include="#active-tab-input, #matched-filter-form",
                hx_swap="none",
            ),
            cls="sidebar-actions",
        ),
        sidebar_categories(categories, saved_pantry),
        Details(
            Summary(Span("➕ Add Custom Ingredient"), Span("+", cls="cat-count")),
            Div(
                Form(
                    Label(
                        "Category",
                        Select(
                            *[Option(c, value=c) for c in categories.keys()],
                            name="category",
                            cls="select",
                        ),
                        cls="field-label",
                    ),
                    Label(
                        "Ingredient Name",
                        Input(type="text", name="name", placeholder="e.g. Coconut milk", required=True, cls="input"),
                        cls="field-label",
                        style="margin-top: 0.5rem;",
                    ),
                    Button("Add to Pantry", type="submit", cls="btn btn-primary btn-sm btn-full", style="margin-top: 0.65rem;"),
                    hx_post="/pantry/add",
                    hx_include="#active-tab-input, #matched-filter-form",
                    hx_swap="none",
                ),
                cls="accordion-body",
            ),
            cls="accordion",
        ),
        Div(
            H4("⚙️ Channel Sync"),
            Form(
                Label(
                    "Channel URL, @Handle, or Name",
                    Input(
                        type="text",
                        name="channel",
                        value="https://www.youtube.com/@PanlasangPinoy",
                        placeholder="URL, @handle, or name",
                        required=True,
                        cls="input",
                    ),
                    cls="field-label",
                ),
                Label(
                    "Videos to fetch",
                    Select(
                        *[Option(str(n), value=str(n), selected=(n == 30)) for n in [10, 20, 30, 40, 50, 60]],
                        name="limit",
                        cls="select",
                    ),
                    cls="field-label",
                    style="margin-top: 0.5rem;",
                ),
                Button(
                    "📥 Sync Channel",
                    Span(" ⏳", cls="htmx-indicator"),
                    type="submit",
                    cls="btn btn-primary btn-sm btn-full",
                    style="margin-top: 0.65rem;",
                ),
                Div(id="sync-status", style="margin-top: 0.45rem; font-size: 0.84rem;"),
                hx_post="/sync",
                hx_target="#sync-status",
                hx_include="#active-tab-input, #matched-filter-form",
            ),
            db_stats(stats["recipes"], stats["ingredients"]),
            cls="sidebar-card",
        ),
        **attrs,
    )
