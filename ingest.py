import sys
import argparse
import db
import parser
import youtube_client

def ingest_channel(channel_query: str, max_videos: int = 50):
    print(f"\n[+] Resolving channel: '{channel_query}'...")
    ch_info = youtube_client.resolve_channel_uploads_id(channel_query)
    if not ch_info:
        print(f"[-] Could not find channel for: {channel_query}")
        return 0

    name = ch_info["name"]
    uploads_id = ch_info["uploads_playlist_id"]
    channel_id = ch_info["channel_id"]
    print(f"[+] Found '{name}' (Uploads Playlist: {uploads_id})")
    print(f"[+] Fetching up to {max_videos} videos...")

    videos = youtube_client.fetch_channel_videos(uploads_id, max_results=max_videos)
    print(f"[+] Downloaded {len(videos)} video metadata entries. Parsing ingredients...")

    saved_count = 0
    with_ingredients_count = 0

    for vid in videos:
        raw_section, parsed_ingredients = parser.parse_recipe_description(
            vid["title"], vid["description"]
        )

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
        if parsed_ingredients:
            with_ingredients_count += 1

    print(f"[✓] Successfully saved {saved_count} videos ({with_ingredients_count} parsed with ingredients) into database.")
    return saved_count

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
