"""Pantry Chef FastHTML application entrypoint and HTTP route handlers."""

import os
from pathlib import Path
from fasthtml.common import (
    Button, Div, FileResponse, JSONResponse, Link, Meta, Response, Script, fast_app, serve
)

import db
import ingest
import services
from components import (
    app_page, badge, db_stats, matched_tab, pantry_chips, sidebar_categories, tab_panel
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

db.init_db()

app, rt = fast_app(
    pico=False,
    hdrs=(
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="theme-color", content="#d94e28"),
        Link(rel="manifest", href="/manifest.json"),
        Link(
            rel="icon",
            href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🍳</text></svg>",
        ),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin="anonymous"),
        Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
        ),
        Link(rel="stylesheet", href="/static/styles.css"),
        Script(src="/static/app.js", defer=True),
    ),
)


def _matched_oob(min_match: int, max_missing: int, assume_staples: str):
    el = matched_tab(
        min_match=min_match,
        max_missing=max_missing,
        assume_staples=(assume_staples == "true"),
        page=1,
    )
    el.attrs["hx_swap_oob"] = "true"
    return el


def _stats_oob():
    stats = db.get_stats()
    return db_stats(stats["recipes"], stats["ingredients"], oob=True)


@rt("/static/{fname:path}")
def static_file(fname: str):
    target = (STATIC_DIR / fname).resolve()
    if STATIC_DIR not in target.parents or not target.is_file():
        return Response("Not Found", status_code=404)
    return FileResponse(target)


@rt("/")
def get():
    saved_pantry = db.get_user_pantry()
    return app_page(
        pantry=sorted(list(saved_pantry)),
        saved_pantry=saved_pantry,
        categories=services.get_categories(),
        stats=db.get_stats(),
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
    return tab_panel("matched", min_match=min_match, max_missing=max_missing, assume_staples=is_staples, page=page)


@rt("/tab/library")
def tab_library(q: str = "", channel: str = "All Channels", page: int = 1):
    return tab_panel("library", q=q, channel=channel, page=page)


@rt("/tab/search")
def tab_search(page: int = 1):
    return tab_panel("search", page=page)


@rt("/pantry/toggle")
def post(item: str, active: str = "", tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    db.toggle_user_pantry_item(item, active == "true")
    chips_oob = pantry_chips(sorted(list(db.get_user_pantry())), oob=True)
    if tab == "matched":
        return chips_oob, _matched_oob(min_match, max_missing, assume_staples)
    return chips_oob


@rt("/pantry/clear")
def post(tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    db.clear_user_pantry()
    cats_oob = sidebar_categories(services.get_categories(), set(), oob=True)
    chips_oob = pantry_chips([], oob=True)
    if tab == "matched":
        return cats_oob, chips_oob, _matched_oob(min_match, max_missing, assume_staples)
    return cats_oob, chips_oob


@rt("/pantry/add")
def post(category: str, name: str, tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    services.add_pantry_ingredient(category, name)
    saved_pantry = db.get_user_pantry()
    cats_oob = sidebar_categories(services.get_categories(), saved_pantry, oob=True)
    chips_oob = pantry_chips(sorted(list(saved_pantry)), oob=True)
    if tab == "matched":
        return cats_oob, chips_oob, _matched_oob(min_match, max_missing, assume_staples)
    return cats_oob, chips_oob


@rt("/sync")
def post(channel: str, limit: int = 30, tab: str = "matched", min_match: int = 30, max_missing: int = 4, assume_staples: str = ""):
    result = ingest.ingest_channel(channel, max_videos=limit)
    if not result["found"]:
        msg = badge(f"❌ Could not find channel: '{channel}'", "missing")
    else:
        saved = result["saved"]
        skipped = result["skipped"]
        detail = f" (skipped {skipped} non-recipe)" if skipped else ""
        msg = badge(f"✅ Synced {saved} recipe{'s' if saved != 1 else ''}{detail}", "green")
    if tab == "matched":
        return msg, _stats_oob(), _matched_oob(min_match, max_missing, assume_staples)
    return msg, _stats_oob()


@rt("/search")
def post(q: str):
    services.perform_live_search(q)
    return tab_panel("search", page=1)


@rt("/search/save/{video_id}")
def post(video_id: str):
    services.save_cached_search_video(video_id)
    btn = Div(Button("✅ Already in Database", disabled=True, cls="btn btn-secondary btn-sm"), id=f"save-wrap-{video_id}")
    return btn, _stats_oob()


@rt("/library/{video_id}")
def delete(video_id: str):
    db.delete_recipe(video_id)
    return _stats_oob()


if __name__ == "__main__":
    serve(host="0.0.0.0", port=int(os.environ.get("PORT", 8501)))
