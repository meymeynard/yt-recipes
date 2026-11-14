"""Top-level page shell FastHTML component."""

from typing import Dict, List
from fasthtml.common import Button, Div, H1, Header, Main, P, Span, Title

from .sidebar import pantry_chips, sidebar
from .tabs import tab_panel


def app_page(
    *,
    pantry: List[str],
    saved_pantry: set,
    categories: Dict[str, List[str]],
    stats: Dict[str, int],
):
    """Render the full Pantry Chef application shell."""
    return Title("Pantry Chef | YouTube Recipe Aggregator"), Div(
        Div(id="sidebar-backdrop", cls="sidebar-backdrop", onclick="toggleSidebar(false)"),
        Header(
            Span("🍳 Pantry Chef", cls="mobile-brand"),
            Button("🧺 Pantry", cls="btn btn-secondary btn-sm", type="button", onclick="toggleSidebar(true)"),
            cls="mobile-header",
        ),
        Div(
            sidebar(categories=categories, saved_pantry=saved_pantry, stats=stats),
            Main(
                Div(
                    H1("What Can I Cook Today?", cls="hero-title"),
                    P("Match your kitchen ingredients against your indexed YouTube recipe library.", cls="hero-subtitle"),
                    cls="hero-header",
                ),
                pantry_chips(pantry),
                tab_panel("matched"),
                cls="main-content",
            ),
            cls="app-layout",
            id="app-shell",
        ),
    )
