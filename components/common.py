"""Shared, reusable FastHTML UI components."""

import math
from typing import Any, List, Optional
from fasthtml.common import A, Button, Details, Div, H4, Img, P, Pre, Span, Strong, Summary


def badge(text: str, variant: str = "gray"):
    """Render a pill badge ('green', 'yellow', 'gray', 'missing')."""
    return Span(text, cls=f"badge badge-{variant}")


def empty_state(icon: str, title: str, message: str):
    """Render a centered empty-state placeholder card."""
    return Div(
        Div(icon, cls="empty-state-icon"),
        H4(title),
        P(message),
        cls="empty-state",
    )


def pagination(
    current_page: int,
    total_items: int,
    items_per_page: int,
    base_url: str,
    include_selector: str = "",
):
    """Render pagination controls targeting #tab-panel."""
    total_pages = max(1, math.ceil(total_items / items_per_page))
    if total_pages <= 1:
        return Div()

    start_idx = (current_page - 1) * items_per_page + 1
    end_idx = min(current_page * items_per_page, total_items)

    prev_attrs = {
        "cls": "btn btn-secondary btn-sm",
        "disabled": (current_page <= 1),
        "hx_get": f"{base_url}&page={max(1, current_page - 1)}",
        "hx_target": "#tab-panel",
        "hx_swap": "outerHTML",
    }
    next_attrs = {
        "cls": "btn btn-secondary btn-sm",
        "disabled": (current_page >= total_pages),
        "hx_get": f"{base_url}&page={min(total_pages, current_page + 1)}",
        "hx_target": "#tab-panel",
        "hx_swap": "outerHTML",
    }
    if include_selector:
        prev_attrs["hx_include"] = include_selector
        next_attrs["hx_include"] = include_selector

    return Div(
        Button("← Previous", **prev_attrs),
        Span(
            Strong(f"Page {current_page} of {total_pages}"),
            f" · Showing {start_idx}–{end_idx} of {total_items}",
            cls="pagination-info",
        ),
        Button("Next →", **next_attrs),
        cls="pagination",
    )


def recipe_card(
    *,
    title: str,
    yt_url: str,
    thumbnail_url: str,
    channel_name: str,
    overlay_badge: Optional[Any] = None,
    extra_badges: Optional[List[Any]] = None,
    body_rows: Optional[List[Any]] = None,
    details_summary: Optional[str] = None,
    details_text: Optional[str] = None,
    actions: Optional[List[Any]] = None,
    card_id: Optional[str] = None,
):
    """Render a unified recipe card used across Matched, Library, and Search tabs."""
    thumb_children = [
        Img(src=thumbnail_url, alt=title, cls="recipe-thumb", loading="lazy")
    ]
    if overlay_badge is not None:
        thumb_children.append(overlay_badge)

    badges_list = [badge(channel_name, "gray")]
    if extra_badges:
        badges_list.extend(b for b in extra_badges if b is not None)

    card_body_children: List[Any] = [
        H4(A(title, href=yt_url, target="_blank"), cls="card-title"),
        Div(*badges_list, cls="card-badges"),
    ]
    if body_rows:
        card_body_children.extend(row for row in body_rows if row is not None)

    if details_summary and details_text is not None:
        card_body_children.append(
            Details(
                Summary(details_summary),
                Pre(details_text, cls="recipe-pre"),
                cls="recipe-details",
            )
        )

    if actions:
        card_body_children.append(Div(*actions, cls="card-actions"))

    card_attrs = {"cls": "recipe-card"}
    if card_id:
        card_attrs["id"] = card_id

    return Div(
        Div(*thumb_children, cls="thumb-wrap"),
        Div(*card_body_children, cls="card-body"),
        **card_attrs,
    )
