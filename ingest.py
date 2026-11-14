import re
import sys
import argparse
import db
import parser
import youtube_client

NON_RECIPE_TITLE_REGEX = re.compile(
    r'\b(vlog|mukbang|q\s*&\s*a|unboxing|giveaway|announcement|kitchen\s+tour|'
    r'house\s+tour|grocery\s+haul|haul|podcast|reaction|behind\s+the\s+scenes|'
    r'trailer|teaser|live\s*stream|taste\s+test|food\s+review|restaurant\s+tour)\b',
    re.IGNORECASE,
)

RECIPE_HINT_REGEX = re.compile(
    r'\b(recipe|how\s+to\s+(?:cook|make)|ingredients|mga\s+sangkap|instructions|'
    r'procedure|tbsp|tsp|tablespoon|teaspoon|cups?|grams?|cloves?|lbs?|oz)\b',
    re.IGNORECASE,
)


def is_recipe_video(title: str, description: str, parsed_ingredients: list) -> bool:
    """Return True if a synced video looks like a recipe with actual ingredients."""
    if not parsed_ingredients:
        return False

    desc = description or ""
    desc_ingredients = [
        ing for ing in parsed_ingredients
        if not ing.get("raw_line", "").startswith("[From Title]")
    ]
    has_ing_header = bool(parser.START_REGEX.search(desc))

    if NON_RECIPE_TITLE_REGEX.search(title or "") and not (has_ing_header and len(desc_ingredients) >= 2):
        return False

    if has_ing_header:
        return True

    if len(desc_ingredients) >= 2:
        return True

    if len(desc_ingredients) == 1 and RECIPE_HINT_REGEX.search(f"{title or ''}\n{desc}"):
        return True

    return False


def ingest_channel(channel_query: str, max_videos: int = 50):
    print(f"\n[+] Resolving channel: '{channel_query}'...")
    ch_info = youtube_client.resolve_channel_uploads_id(channel_query)
    if not ch_info:
        print(f"[-] Could not find channel for: {channel_query}")
        return {"found": False, "saved": 0, "skipped": 0}

    name = ch_info["name"]
    uploads_id = ch_info["uploads_playlist_id"]
    channel_id = ch_info["channel_id"]
    print(f"[+] Found '{name}' (Uploads Playlist: {uploads_id})")
    print(f"[+] Fetching up to {max_videos} videos...")

    videos = youtube_client.fetch_channel_videos(uploads_id, max_results=max_videos)
    print(f"[+] Downloaded {len(videos)} video metadata entries. Parsing ingredients...")

    saved_count = 0
    skipped_count = 0

    for vid in videos:
        raw_section, parsed_ingredients = parser.parse_recipe_description(
            vid["title"], vid["description"]
        )

        if not is_recipe_video(vid["title"], vid["description"], parsed_ingredients):
            skipped_count += 1
            continue

        db.save_recipe(
            video_id=vid["video_id"],
            title=vid["title"],
            channel_name=vid["channel_name"],
            channel_id=vid["channel_id"],
            published_at=vid["published_at"],
            thumbnail_url=vid["thumbnail_url"],
            description=vid["description"],
            raw_ingredients_text=raw_section,
            ingredients=parsed_ingredients
        )
        saved_count += 1

    print(f"[✓] Successfully saved {saved_count} recipe videos (skipped {skipped_count} non-recipe videos).")
    return {"found": True, "saved": saved_count, "skipped": skipped_count}

def main():
    parser_cli = argparse.ArgumentParser(description="Ingest YouTube cooking channels into recipes DB")
    parser_cli.add_argument("--channel", type=str, help="Channel name or handle (e.g. 'Panlasang Pinoy')")
    parser_cli.add_argument("--limit", type=int, default=30, help="Max videos to fetch per channel")
    parser_cli.add_argument("--all-defaults", action="store_true", help="Ingest all default channels")

    args = parser_cli.parse_args()

    db.init_db()

    if args.channel:
        ingest_channel(args.channel, max_videos=args.limit)
    elif args.all_defaults:
        for ch in youtube_client.DEFAULT_CHANNELS:
            query = ch.get("channel_id") or ch.get("name")
            ingest_channel(query, max_videos=args.limit)
    else:
        # Default run: Ingest Panlasang Pinoy (the benchmark Filipino recipe channel)
        print("[*] Running default ingestion for 'Panlasang Pinoy'...")
        ingest_channel("Panlasang Pinoy", max_videos=args.limit)

    stats = db.get_stats()
    print(f"\n[Database Status] Total Recipes: {stats['recipes']} | Unique Ingredients: {stats['ingredients']}")

if __name__ == "__main__":
    main()
