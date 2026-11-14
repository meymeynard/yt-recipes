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
    --bg-canvas: #faf8f5;
    --bg-surface: #ffffff;
    --bg-subtle: #f3efe8;
    --bg-hover: #efe9df;
    --border: #e6dfd5;
    --border-strong: #d4cabd;
    --text-primary: #1c1917;
    --text-secondary: #57534e;
    --text-muted: #78716c;
    --accent: #d94e28;
    --accent-hover: #b83d1b;
    --accent-soft: #fff1ec;
    --green-bg: #dcfce7;
    --green-text: #166534;
    --green-border: #86efac;
    --amber-bg: #fef3c7;
    --amber-text: #92400e;
    --amber-border: #fcd34d;
    --red-bg: #fee2e2;
    --red-text: #991b1b;
    --red-border: #fca5a5;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 2px rgba(28, 25, 23, 0.05);
    --shadow-md: 0 4px 14px rgba(28, 25, 23, 0.07);
    --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-display: 'Fraunces', Georgia, serif;
}

*, *::before, *::after {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    background: var(--bg-canvas);
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}

a {
    color: var(--accent);
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}

button, input, select {
    font-family: inherit;
    font-size: 0.92rem;
}

button:focus-visible, input:focus-visible, select:focus-visible, summary:focus-visible, a:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

/* App Shell */
.app-layout {
    display: grid;
    grid-template-columns: 330px minmax(0, 1fr);
    min-height: 100vh;
}

/* Mobile Header */
.mobile-header {
    display: none;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1.15rem;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 30;
}
.mobile-brand {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 1.2rem;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 0.45rem;
}
.sidebar-backdrop {
    display: none;
}

/* Sidebar */
.sidebar {
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    padding: 1.35rem 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}
.sidebar-brand {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}
.sidebar-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
}
.sidebar-close-btn {
    display: none;
}

@media (max-width: 960px) {
    .app-layout {
        grid-template-columns: 1fr;
    }
    .mobile-header {
        display: flex;
    }
    .sidebar {
        position: fixed;
        top: 0;
        left: 0;
        bottom: 0;
        width: min(340px, 88vw);
        z-index: 50;
        transform: translateX(-105%);
        transition: transform 0.22s ease;
        box-shadow: var(--shadow-md);
    }
    .sidebar.open {
        transform: translateX(0);
    }
    .sidebar-backdrop.open {
        display: block;
        position: fixed;
        inset: 0;
        background: rgba(28, 25, 23, 0.45);
        z-index: 40;
    }
    .sidebar-close-btn {
        display: inline-flex;
    }
}

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    padding: 0.55rem 1rem;
    border-radius: var(--radius-sm);
    font-weight: 600;
    font-size: 0.88rem;
    cursor: pointer;
    border: 1px solid transparent;
    transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, transform 0.1s ease;
    text-decoration: none !important;
    line-height: 1.25;
}
.btn:active:not(:disabled) {
    transform: translateY(1px);
}
.btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}
.btn-primary {
    background: var(--accent);
    color: #ffffff;
}
.btn-primary:hover:not(:disabled) {
    background: var(--accent-hover);
}
.btn-secondary {
    background: var(--bg-surface);
    color: var(--text-primary);
    border-color: var(--border-strong);
}
.btn-secondary:hover:not(:disabled) {
    background: var(--bg-subtle);
}
.btn-ghost {
    background: transparent;
    color: var(--text-secondary);
    border-color: var(--border);
}
.btn-ghost:hover:not(:disabled) {
    background: var(--bg-subtle);
    color: var(--text-primary);
}
.btn-danger-ghost {
    background: transparent;
    color: var(--red-text);
    border-color: var(--red-border);
}
.btn-danger-ghost:hover:not(:disabled) {
    background: var(--red-bg);
}
.btn-sm {
    padding: 0.4rem 0.78rem;
    font-size: 0.82rem;
}
.btn-full {
    width: 100%;
}

/* Inputs & Form Controls */
.input, .select {
    width: 100%;
    padding: 0.55rem 0.75rem;
    background: var(--bg-surface);
    color: var(--text-primary);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.input:focus, .select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(217, 78, 40, 0.14);
}
.field-label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-secondary);
}

/* Sidebar Sections */
.sidebar-actions {
    display: flex;
    gap: 0.5rem;
}
.pantry-filter-input {
    padding: 0.48rem 0.75rem;
    font-size: 0.86rem;
    background: var(--bg-canvas);
}
.accordion {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-surface);
    margin-bottom: 0.55rem;
    overflow: hidden;
}
.accordion summary {
    list-style: none;
    padding: 0.6rem 0.8rem;
    cursor: pointer;
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--bg-canvas);
    user-select: none;
}
.accordion summary::-webkit-details-marker {
    display: none;
}
.accordion summary:hover {
    background: var(--bg-subtle);
}
.accordion-body {
    padding: 0.65rem 0.75rem;
    border-top: 1px solid var(--border);
}
.cat-count {
    font-size: 0.74rem;
    font-weight: 600;
    padding: 0.1rem 0.5rem;
    border-radius: 999px;
    background: var(--bg-subtle);
    color: var(--text-secondary);
}
.cat-count.has-selected {
    background: var(--green-bg);
    color: var(--green-text);
}
.cat-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}
.ing-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.65rem;
    border-radius: 999px;
    border: 1px solid var(--border-strong);
    background: var(--bg-surface);
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.14s ease;
    user-select: none;
}
.ing-pill:hover {
    border-color: var(--accent);
    color: var(--text-primary);
}
.ing-pill input[type="checkbox"] {
    accent-color: var(--green-text);
    width: 14px;
    height: 14px;
    margin: 0;
    cursor: pointer;
}
.ing-pill:has(input:checked) {
    background: var(--green-bg);
    border-color: var(--green-border);
    color: var(--green-text);
    font-weight: 600;
}

.sidebar-card {
    background: var(--bg-canvas);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.9rem;
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
}
.sidebar-card h4 {
    margin: 0;
    font-size: 0.95rem;
    color: var(--text-primary);
}
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
}
.stat-box {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.55rem 0.65rem;
    text-align: center;
}
.stat-num {
    display: block;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text-primary);
}
.stat-label {
    font-size: 0.72rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Main Content */
.main-content {
    padding: 1.75rem 2.25rem 3rem;
    max-width: 1140px;
    width: 100%;
    margin: 0 auto;
}
@media (max-width: 640px) {
    .main-content {
        padding: 1.15rem 1rem 2.5rem;
    }
}

.hero-header {
    margin-bottom: 1.25rem;
}
.hero-title {
    margin: 0 0 0.35rem 0;
    font-family: var(--font-display);
    font-size: clamp(1.65rem, 2.5vw, 2.2rem);
    font-weight: 700;
    letter-spacing: -0.025em;
    color: var(--text-primary);
}
.hero-subtitle {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.95rem;
}

/* Pantry Chips Card */
.pantry-summary {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 0.95rem 1.15rem;
    margin-bottom: 1.35rem;
    box-shadow: var(--shadow-sm);
}
.pantry-summary-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.55rem;
    font-size: 0.9rem;
    color: var(--text-secondary);
}
.chips-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}

/* Badges */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 600;
    border: 1px solid transparent;
    line-height: 1.35;
}
.badge-green { background: var(--green-bg); color: var(--green-text); border-color: var(--green-border); }
.badge-yellow { background: var(--amber-bg); color: var(--amber-text); border-color: var(--amber-border); }
.badge-gray { background: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border); }
.badge-missing { background: var(--red-bg); color: var(--red-text); border-color: var(--red-border); }

/* Tabs */
.tabs {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    background: var(--bg-subtle);
    padding: 0.35rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    margin-bottom: 1.25rem;
}
.tab-btn {
    background: transparent;
    border: none;
    border-radius: var(--radius-sm);
    padding: 0.52rem 1rem;
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
}
.tab-btn:hover {
    color: var(--text-primary);
    background: rgba(255,255,255,0.55);
}
.tab-btn.active {
    background: var(--bg-surface);
    color: var(--accent);
    box-shadow: var(--shadow-sm);
}

/* Filter Bar */
.filter-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 1rem 1.15rem;
    margin-bottom: 1.15rem;
    align-items: end;
    box-shadow: var(--shadow-sm);
}
.range-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
}
.range-val {
    font-weight: 700;
    color: var(--accent);
    background: var(--accent-soft);
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    font-size: 0.78rem;
}
input[type="range"] {
    width: 100%;
    accent-color: var(--accent);
    cursor: pointer;
}
.staples-check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-primary);
    padding: 0.45rem 0.65rem;
    background: var(--bg-canvas);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    cursor: pointer;
}
.staples-check input[type="checkbox"] {
    accent-color: var(--accent);
    width: 16px;
    height: 16px;
    margin: 0;
}

.results-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.9rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
}
.results-meta h3 {
    margin: 0;
    font-size: 1.05rem;
    color: var(--text-primary);
}

/* Recipe Cards */
.recipe-card {
    display: grid;
    grid-template-columns: 270px minmax(0, 1fr);
    gap: 1.35rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.1rem;
    margin-bottom: 1rem;
    box-shadow: var(--shadow-sm);
    transition: box-shadow 0.18s ease, border-color 0.18s ease;
}
.recipe-card:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--border-strong);
}
@media (max-width: 720px) {
    .recipe-card {
        grid-template-columns: 1fr;
        gap: 0.9rem;
    }
}
.thumb-wrap {
    position: relative;
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--bg-subtle);
    aspect-ratio: 16 / 9;
    align-self: start;
}
.recipe-thumb {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
    transition: transform 0.25s ease;
}
.recipe-card:hover .recipe-thumb {
    transform: scale(1.03);
}
.thumb-overlay-badge {
    position: absolute;
    top: 0.55rem;
    left: 0.55rem;
    padding: 0.24rem 0.65rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 700;
    box-shadow: 0 2px 6px rgba(0,0,0,0.18);
}
.card-body {
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    min-width: 0;
}
.card-title {
    margin: 0;
    font-size: 1.08rem;
    font-weight: 700;
    line-height: 1.35;
}
.card-title a {
    color: var(--text-primary);
}
.card-title a:hover {
    color: var(--accent);
    text-decoration: none;
}
.card-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
}
.ing-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.84rem;
}
.ing-row-label {
    font-weight: 600;
    color: var(--text-secondary);
    margin-right: 0.2rem;
}
.recipe-details {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-canvas);
    margin-top: 0.2rem;
}
.recipe-details summary {
    padding: 0.45rem 0.75rem;
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
}
.recipe-details summary:hover {
    color: var(--text-primary);
}
.recipe-pre {
    margin: 0;
    padding: 0.75rem;
    border-top: 1px solid var(--border);
    white-space: pre-wrap;
    word-break: break-word;
    font-family: var(--font-sans);
    font-size: 0.84rem;
    line-height: 1.55;
    color: var(--text-secondary);
    max-height: 240px;
    overflow-y: auto;
    background: var(--bg-surface);
    border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}
.card-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 0.25rem;
}

/* Empty States */
.empty-state {
    background: var(--bg-surface);
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius-lg);
    padding: 2.25rem 1.5rem;
    text-align: center;
    color: var(--text-secondary);
}
.empty-state-icon {
    font-size: 2.2rem;
    margin-bottom: 0.5rem;
}
.empty-state h4 {
    margin: 0 0 0.35rem 0;
    color: var(--text-primary);
    font-size: 1.05rem;
}
.empty-state p {
    margin: 0;
    font-size: 0.9rem;
}

/* Pagination */
.pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
}
.pagination-info {
    font-size: 0.86rem;
    color: var(--text-secondary);
}

/* Loading indicator */
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator,
.htmx-request.htmx-indicator { display: inline-block; }
""")

CLIENT_JS = Script("""
function toggleSidebar(forceOpen) {
    const sb = document.getElementById('sidebar-panel');
    const bd = document.getElementById('sidebar-backdrop');
    if (!sb || !bd) return;
    const isOpen = typeof forceOpen === 'boolean' ? forceOpen : !sb.classList.contains('open');
    sb.classList.toggle('open', isOpen);
    bd.classList.toggle('open', isOpen);
}
function filterPantryIngredients(query) {
    const q = (query || '').toLowerCase().trim();
    const accordions = document.querySelectorAll('#sidebar-categories details.accordion');
    accordions.forEach(acc => {
        let visibleCount = 0;
        const pills = acc.querySelectorAll('.ing-pill');
        pills.forEach(pill => {
            const text = pill.textContent.toLowerCase();
            const match = !q || text.includes(q);
            pill.style.display = match ? 'inline-flex' : 'none';
            if (match) visibleCount++;
        });
        acc.style.display = visibleCount > 0 ? 'block' : 'none';
        if (q && visibleCount > 0) acc.open = true;
    });
}
""")

app, rt = fast_app(
    pico=False,
    hdrs=(
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="theme-color", content="#d94e28"),
        Link(rel="manifest", href="/manifest.json"),
        Link(rel="icon", href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍳</text></svg>"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin="anonymous"),
        Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"),
        CUSTOM_CSS,
        CLIENT_JS,
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
                cls="pantry-summary-head"
            ),
            Div(*[Span(f"✓ {item}", cls="badge badge-green") for item in sorted(pantry)], cls="chips-wrap"),
            **attrs
        )
    return Div(
        Div(
            Span("Selected Pantry: ", Strong("0 ingredients")),
            cls="pantry-summary-head"
        ),
        Div(
            Span("Your pantry is empty — check ingredients in the sidebar to match recipes.", cls="badge badge-gray"),
            cls="chips-wrap"
        ),
        **attrs
    )


def render_stats(oob: bool = False):
    stats = db.get_stats()
    attrs = {"id": "db-stats", "cls": "stats-grid"}
    if oob:
        attrs["hx_swap_oob"] = "true"
    return Div(
        Div(Span(str(stats["recipes"]), cls="stat-num"), Span("Recipes", cls="stat-label"), cls="stat-box"),
        Div(Span(str(stats["ingredients"]), cls="stat-num"), Span("Ingredients", cls="stat-label"), cls="stat-box"),
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
                cls="ing-pill"
            )
            for item in items
        ]
        accordions.append(
            Details(
                Summary(
                    Span(cat_name),
                    Span(f"{selected_count}/{len(items)}", cls=count_cls)
                ),
                Div(Div(*checkboxes, cls="cat-list"), cls="accordion-body"),
                cls="accordion",
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
        Div(
            H3("🍳 Pantry Chef", cls="sidebar-title"),
            Button("✕", cls="btn btn-ghost btn-sm sidebar-close-btn", type="button", onclick="toggleSidebar(false)", aria_label="Close pantry sidebar"),
            cls="sidebar-brand"
        ),
        Input(
            type="search",
            placeholder="Filter ingredients (e.g. garlic, pork)...",
            cls="input pantry-filter-input",
            oninput="filterPantryIngredients(this.value)",
            aria_label="Filter pantry ingredients"
        ),
        Div(
            Button(
                "🗑️ Clear Pantry",
                cls="btn btn-secondary btn-sm btn-full",
                hx_post="/pantry/clear",
                hx_include="#active-tab-input, #matched-filter-form",
                hx_swap="none",
            ),
            cls="sidebar-actions"
        ),
        render_sidebar_categories(categories, saved_pantry),
        Details(
            Summary(Span("➕ Add Custom Ingredient"), Span("+", cls="cat-count")),
            Div(
                Form(
                    Label(
                        "Category",
                        Select(
                            *[Option(c, value=c) for c in categories.keys()],
                            name="category",
                            cls="select"
                        ),
                        cls="field-label"
                    ),
                    Label(
                        "Ingredient Name",
                        Input(type="text", name="name", placeholder="e.g. Coconut milk", required=True, cls="input"),
                        cls="field-label",
                        style="margin-top: 0.5rem;"
                    ),
                    Button("Add to Pantry", type="submit", cls="btn btn-primary btn-sm btn-full", style="margin-top: 0.65rem;"),
                    hx_post="/pantry/add",
                    hx_include="#active-tab-input, #matched-filter-form",
                    hx_swap="none",
                ),
                cls="accordion-body"
            ),
            cls="accordion"
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
                        cls="input"
                    ),
                    cls="field-label"
                ),
                Label(
                    "Videos to fetch",
                    Select(
                        *[Option(str(n), value=str(n), selected=(n == 30)) for n in [10, 20, 30, 40, 50, 60]],
                        name="limit",
                        cls="select"
                    ),
                    cls="field-label",
                    style="margin-top: 0.5rem;"
                ),
                Button(
                    "📥 Sync Channel",
                    Span(" ⏳", cls="htmx-indicator"),
                    type="submit",
                    cls="btn btn-primary btn-sm btn-full",
                    style="margin-top: 0.65rem;"
                ),
                Div(id="sync-status", style="margin-top: 0.45rem; font-size: 0.84rem;"),
                hx_post="/sync",
                hx_target="#sync-status",
                hx_include="#active-tab-input, #matched-filter-form",
            ),
            render_stats(),
            cls="sidebar-card"
        ),
        **attrs
    )


def render_pagination(current_page: int, total_items: int, items_per_page: int, base_url: str, include_selector: str = ""):
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
            cls="pagination-info"
        ),
        Button("Next →", **next_attrs),
        cls="pagination"
    )


def render_matched_tab(min_match: int = 30, max_missing: int = 4, assume_staples: bool = True, page: int = 1):
    recipes = db.get_all_recipes_with_ingredients()
    pantry = db.get_user_pantry()

    filter_form = Form(
        Input(type="hidden", name="submitted", value="1"),
        Div(
            Div(
                Div(Span("Min Match %", cls="field-label"), Span(f"{min_match}%", id="min-match-val", cls="range-val"), cls="range-header"),
                Input(
                    type="range", name="min_match", min="10", max="100", step="10", value=str(min_match),
                    oninput="document.getElementById('min-match-val').textContent = this.value + '%'",
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change"
                ),
            ),
            Div(
                Div(Span("Max Missing", cls="field-label"), Span(f"{max_missing}", id="max-missing-val", cls="range-val"), cls="range-header"),
                Input(
                    type="range", name="max_missing", min="0", max="10", step="1", value=str(max_missing),
                    oninput="document.getElementById('max-missing-val').textContent = this.value",
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change"
                ),
            ),
            Label(
                Input(
                    type="checkbox", name="assume_staples", value="true", checked=assume_staples,
                    hx_get="/tab/matched", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#matched-filter-form", hx_trigger="change"
                ),
                Span("Assume basic staples (oil, salt, pepper, water)"),
                cls="staples-check"
            ),
            cls="filter-bar"
        ),
        id="matched-filter-form"
    )

    if not recipes:
        body = Div(
            Div("🍳", cls="empty-state-icon"),
            H4("No recipes indexed yet"),
            P("Use 'Channel Sync' in the sidebar or 'Live YouTube Search' to build your recipe database."),
            cls="empty-state"
        )
        return Div(filter_form, body, id="matched-content")

    results = matcher.rank_recipes(
        recipes=recipes,
        user_pantry=pantry,
        min_match_pct=min_match,
        max_missing=max_missing,
        assume_staples=assume_staples
    )

    total_items = len(results)
    if total_items == 0:
        empty_msg = (
            "Select a few ingredients in the Pantry sidebar to see recipes you can cook."
            if not pantry
            else "Try lowering Min Match % or increasing Max Missing ingredients."
        )
        body = Div(
            Div("🥗", cls="empty-state-icon"),
            H4("No matching recipes found"),
            P(empty_msg),
            cls="empty-state"
        )
        return Div(filter_form, body, id="matched-content")

    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))
    page = max(1, min(page, total_pages))
    page_items = results[(page - 1) * ITEMS_PER_PAGE : page * ITEMS_PER_PAGE]

    cards = []
    for r in page_items:
        badge_cls = "badge-green" if r["match_percentage"] >= 80 else ("badge-yellow" if r["match_percentage"] >= 50 else "badge-gray")
        cookable = Span("🎉 Ready to Cook", cls="badge badge-green") if r["is_cookable"] else ""
        matched_badges = [Span(f"✓ {i}", cls="badge badge-green") for i in r["matched"]]
        missing_badges = [Span(f"✗ {i}", cls="badge badge-missing") for i in r["missing"]]

        desc_text = r["raw_ingredients_text"] if r["raw_ingredients_text"] else r["description"][:1000]
        yt_url = f"https://www.youtube.com/watch?v={r['video_id']}"

        cards.append(
            Div(
                Div(
                    Img(src=r["thumbnail_url"], alt=r["title"], cls="recipe-thumb", loading="lazy"),
                    Span(f"{r['match_percentage']}% Match", cls=f"thumb-overlay-badge {badge_cls}"),
                    cls="thumb-wrap"
                ),
                Div(
                    H4(A(r["title"], href=yt_url, target="_blank"), cls="card-title"),
                    Div(
                        Span(r["channel_name"], cls="badge badge-gray"),
                        cookable,
                        cls="card-badges"
                    ),
                    Div(Span("In pantry:", cls="ing-row-label"), *matched_badges, cls="ing-row") if matched_badges else "",
                    Div(Span("Missing:", cls="ing-row-label"), *missing_badges, cls="ing-row") if missing_badges else "",
                    Details(
                        Summary("📖 View Recipe Ingredients & Instructions"),
                        Pre(desc_text, cls="recipe-pre"),
                        cls="recipe-details"
                    ),
                    Div(
                        A("▶ Watch on YouTube", href=yt_url, target="_blank", cls="btn btn-secondary btn-sm"),
                        cls="card-actions"
                    ),
                    cls="card-body"
                ),
                cls="recipe-card"
            )
        )

    base_url = f"/tab/matched?submitted=1&min_match={min_match}&max_missing={max_missing}&assume_staples={'true' if assume_staples else 'false'}"
    return Div(
        filter_form,
        Div(H3(f"Found {total_items} Matching Recipe{'s' if total_items != 1 else ''}"), cls="results-meta"),
        *cards,
        render_pagination(page, total_items, ITEMS_PER_PAGE, base_url),
        id="matched-content"
    )


def render_library_tab(q: str = "", channel: str = "All Channels", page: int = 1):
    library_recipes = db.get_all_recipes_with_ingredients()

    if not library_recipes:
        return Div(
            Div(
                Div("📚", cls="empty-state-icon"),
                H4("Your Recipe Library is empty"),
                P("Use 'Channel Sync' in the sidebar or 'Live YouTube Search' to add cooking videos."),
                cls="empty-state"
            ),
            id="library-content"
        )

    available_channels = ["All Channels"] + sorted({r["channel_name"] for r in library_recipes if r.get("channel_name")})

    filter_form = Form(
        Input(type="hidden", name="submitted", value="1"),
        Div(
            Label(
                "Search Library by title or ingredient",
                Input(
                    type="search", name="q", value=q, placeholder="e.g. adobo, ampalaya, chicken",
                    cls="input",
                    hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#library-filter-form", hx_trigger="keyup changed delay:300ms, search"
                ),
                cls="field-label"
            ),
            Label(
                "Filter by Channel",
                Select(
                    *[Option(c, value=c, selected=(c == channel)) for c in available_channels],
                    name="channel",
                    cls="select",
                    hx_get="/tab/library", hx_target="#tab-panel", hx_swap="outerHTML",
                    hx_include="#library-filter-form", hx_trigger="change"
                ),
                cls="field-label"
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
                Div(
                    Img(src=r["thumbnail_url"], alt=r["title"], cls="recipe-thumb", loading="lazy"),
                    cls="thumb-wrap"
                ),
                Div(
                    H4(A(r["title"], href=yt_url, target="_blank"), cls="card-title"),
                    Div(Span(r["channel_name"], cls="badge badge-gray"), cls="card-badges"),
                    Div(Span(f"Ingredients ({len(ings)}):", cls="ing-row-label"), *ing_badges, cls="ing-row") if ings else P("No specific ingredients parsed.", style="font-size: 0.85rem; color: var(--text-muted); margin: 0;"),
                    Details(
                        Summary("📖 View Recipe Description"),
                        Pre(desc_text, cls="recipe-pre"),
                        cls="recipe-details"
                    ),
                    Div(
                        A("▶ Watch on YouTube", href=yt_url, target="_blank", cls="btn btn-secondary btn-sm"),
                        Button(
                            "🗑️ Remove",
                            cls="btn btn-danger-ghost btn-sm",
                            hx_delete=f"/library/{r['video_id']}",
                            hx_target=f"#lib-card-{r['video_id']}",
                            hx_swap="outerHTML",
                        ),
                        cls="card-actions"
                    ),
                    cls="card-body"
                ),
                id=f"lib-card-{r['video_id']}",
                cls="recipe-card"
            )
        )

    import urllib.parse
    base_url = f"/tab/library?q={urllib.parse.quote(q)}&channel={urllib.parse.quote(channel)}"
    body_content = cards if cards else [
        Div(
            Div("🔎", cls="empty-state-icon"),
            H4("No recipes match your filter"),
            P("Try clearing your search query or selecting 'All Channels'."),
            cls="empty-state"
        )
    ]
    return Div(
        filter_form,
        Div(
            H3(f"📚 Recipe Library ({len(library_recipes)} Total)"),
            Span(f"Showing {total_items} of {len(library_recipes)}"),
            cls="results-meta"
        ),
        *body_content,
        render_pagination(page, total_items, ITEMS_PER_PAGE, base_url),
        id="library-content"
    )


def render_search_tab(page: int = 1):
    results = LIVE_SEARCH_CACHE.get("results", [])
    last_q = LIVE_SEARCH_CACHE.get("query", "") or "Chicken Sayote"

    search_form = Form(
        Div(
            Label(
                "Search YouTube for a recipe or ingredient combo",
                Input(type="text", name="q", value=last_q, placeholder="e.g. Chicken Sayote", required=True, cls="input"),
                cls="field-label"
            ),
            Button("🔍 Search YouTube", Span(" ⏳", cls="htmx-indicator"), type="submit", cls="btn btn-primary"),
            cls="filter-bar",
            style="grid-template-columns: 1fr auto;"
        ),
        hx_post="/search",
        hx_target="#tab-panel",
        hx_swap="outerHTML",
    )

    if not results:
        return Div(
            search_form,
            Div(
                Div("🎬", cls="empty-state-icon"),
                H4("Search YouTube On-Demand"),
                P("Enter a dish or ingredient combo above to fetch recipes from YouTube and save them to your library."),
                cls="empty-state"
            ),
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

        cards.append(
            Div(
                Div(
                    Img(src=item["thumbnail_url"], alt=item["title"], cls="recipe-thumb", loading="lazy"),
                    cls="thumb-wrap"
                ),
                Div(
                    H4(A(item["title"], href=yt_url, target="_blank"), cls="card-title"),
                    Div(
                        Span(item["channel_name"], cls="badge badge-gray"),
                        saved_badge,
                        cls="card-badges"
                    ),
                    Div(
                        Span(f"Parsed Ingredients ({len(ing_names)}):", cls="ing-row-label"),
                        *([Span(name, cls="badge badge-gray") for name in ing_names] if ing_names else [Span("None detected", style="color: var(--text-muted); font-size: 0.84rem;")]),
                        cls="ing-row"
                    ),
                    Div(
                        Div(action_btn, id=f"save-wrap-{vid}"),
                        A("▶ Watch on YouTube", href=yt_url, target="_blank", cls="btn btn-secondary btn-sm"),
                        cls="card-actions"
                    ),
                    cls="card-body"
                ),
                cls="recipe-card"
            )
        )

    return Div(
        search_form,
        Div(
            H3(f"Results for “{last_q}”"),
            Span(f"{total_items} videos found"),
            cls="results-meta"
        ),
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
        Div(id="sidebar-backdrop", cls="sidebar-backdrop", onclick="toggleSidebar(false)"),
        Header(
            Span("🍳 Pantry Chef", cls="mobile-brand"),
            Button("🧺 Pantry", cls="btn btn-secondary btn-sm", type="button", onclick="toggleSidebar(true)"),
            cls="mobile-header"
        ),
        Div(
            render_sidebar(),
            Main(
                Div(
                    H1("What Can I Cook Today?", cls="hero-title"),
                    P("Match your kitchen ingredients against your indexed YouTube recipe library.", cls="hero-subtitle"),
                    cls="hero-header"
                ),
                render_pantry_chips(pantry),
                render_tab_panel("matched"),
                cls="main-content"
            ),
            cls="app-layout",
            id="app-shell"
        )
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
        "background_color": "#faf8f5",
        "theme_color": "#d94e28",
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
    btn = Div(Button("✅ Already in Database", disabled=True, cls="btn btn-secondary btn-sm"), id=f"save-wrap-{video_id}")
    return btn, stats_oob


@rt("/library/{video_id}")
def delete(video_id: str):
    db.delete_recipe(video_id)
    stats_oob = render_stats(oob=True)
    return stats_oob


if __name__ == "__main__":
    serve(host="0.0.0.0", port=int(os.environ.get("PORT", 8501)))
