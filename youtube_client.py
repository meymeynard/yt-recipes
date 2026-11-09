import re
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
import config

_youtube = None

def get_youtube():
    global _youtube
    if _youtube is None:
        api_key = config.get_youtube_api_key()
        _youtube = build("youtube", "v3", developerKey=api_key)
    return _youtube

# Popular cooking channels to index
DEFAULT_CHANNELS = [
    {
        "name": "Panlasang Pinoy",
        "channel_id": "UCIjw46txjW6oD4NU6FHaj_w",
        "uploads_playlist_id": "UUIjw46txjW6oD4NU6FHaj_w"
    },
    {
        "name": "Simpol (Chef Tatung)",
        "channel_id": "UCVFRkFnGiYDKvHmtotmaAXw",
        "uploads_playlist_id": "UUVFRkFnGiYDKvHmtotmaAXw"
    },
    {
        "name": "Kuya Fern's Cooking",
        "handle": "Kuya Fern's Cooking"
    }
]

def resolve_channel_uploads_id(channel_query: str) -> Optional[Dict[str, str]]:
    """
    Resolves a channel name, handle, channel ID, or full YouTube URL to its upload playlist ID.
    Supports:
    - https://www.youtube.com/@Handle
    - https://www.youtube.com/channel/UCxxxxxxxxxxxx
    - https://www.youtube.com/c/CustomName or /user/Name
    - @Handle or raw UCxxxxxxxxxxxx ID
    - Channel name search query (e.g. 'Panlasang Pinoy')
    """
    yt = get_youtube()
    clean = channel_query.strip()
    
    channel_id = None
    handle = None

    # 1. Parse URL patterns
    if "youtube.com" in clean or "youtu.be" in clean:
        ch_match = re.search(r'channel/(UC[a-zA-Z0-9_-]{22})', clean)
        if ch_match:
            channel_id = ch_match.group(1)
        else:
            handle_match = re.search(r'@([a-zA-Z0-9_.-]+)', clean)
            if handle_match:
                handle = handle_match.group(1)
            else:
                path_match = re.search(r'youtube\.com/(?:c/|user/)?([a-zA-Z0-9_.-]+)', clean)
                if path_match:
                    clean = path_match.group(1)
    elif clean.startswith("@"):
        handle = clean[1:]
    elif clean.startswith("UC") and len(clean) == 24:
        channel_id = clean

    # 2. Try looking up directly by channel_id (costs 1 unit)
    if channel_id:
        try:
            resp = yt.channels().list(id=channel_id, part="contentDetails,snippet").execute()
            items = resp.get("items", [])
            if items:
                item = items[0]
                return {
                    "channel_id": channel_id,
                    "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
                    "name": item["snippet"]["title"]
                }
        except Exception:
            pass

    # 3. Try looking up directly by handle (costs 1 unit)
    if handle:
        try:
            resp = yt.channels().list(forHandle=handle, part="contentDetails,snippet").execute()
            items = resp.get("items", [])
            if items:
                item = items[0]
                return {
                    "channel_id": item["id"],
                    "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
                    "name": item["snippet"]["title"]
                }
        except Exception:
            pass
        # Fall back to searching by handle text
        clean = handle

    # 4. Fallback: Search for the channel by query / name
    try:
        resp = yt.search().list(
            q=clean,
            type="channel",
            part="snippet",
            maxResults=1
        ).execute()

        items = resp.get("items", [])
        if items:
            ch_id = items[0]["id"]["channelId"]
            title = items[0]["snippet"]["title"]

            ch_resp = yt.channels().list(
                id=ch_id,
                part="contentDetails"
            ).execute()

            ch_items = ch_resp.get("items", [])
            if ch_items:
                return {
                    "channel_id": ch_id,
                    "uploads_playlist_id": ch_items[0]["contentDetails"]["relatedPlaylists"]["uploads"],
                    "name": title
                }
    except Exception as e:
        print(f"Error resolving channel query: {e}")

    return None

def fetch_channel_videos(uploads_playlist_id: str, max_results: int = 40) -> List[Dict[str, Any]]:
    """
    Fetches videos from a channel's upload playlist.
    Uses playlistItems.list which costs only 1 quota unit for up to 50 items.
    """
    yt = get_youtube()
    videos = []
    page_token = None
    remaining = max_results

    while remaining > 0:
        fetch_count = min(remaining, 50)
        req = yt.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=fetch_count,
            pageToken=page_token
        )
        resp = req.execute()

        items = resp.get("items", [])
        if not items:
            break

        for item in items:
            snippet = item["snippet"]
            video_id = snippet.get("resourceId", {}).get("videoId") or item["contentDetails"].get("videoId")
            if not video_id:
                continue

            # Thumbnails fallback
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
                or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            )

            videos.append({
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel_name": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": thumb_url
            })

        remaining -= len(items)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return videos

def search_youtube_recipes(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Live on-demand search. Costs 100 units.
    Fetches matching videos and their full descriptions.
    """
    yt = get_youtube()
    search_resp = yt.search().list(
        q=f"{query} recipe",
        type="video",
        part="snippet",
        maxResults=max_results
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_resp.get("items", []) if "videoId" in item.get("id", {})]
    if not video_ids:
        return []

    # Batch fetch full descriptions (1 unit)
    video_resp = yt.videos().list(
        part="snippet,contentDetails",
        id=",".join(video_ids)
    ).execute()

    results = []
    for item in video_resp.get("items", []):
        snippet = item["snippet"]
        video_id = item["id"]
        thumbnails = snippet.get("thumbnails", {})
        thumb_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )
        results.append({
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel_name": snippet.get("channelTitle", ""),
            "channel_id": snippet.get("channelId", ""),
            "published_at": snippet.get("publishedAt", ""),
            "description": snippet.get("description", ""),
            "thumbnail_url": thumb_url
        })
    return results
