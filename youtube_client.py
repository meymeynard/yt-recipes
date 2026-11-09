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
        "channel_id": "UC_j7xjUSs8b9Zc89qA4L9qA",
        "uploads_playlist_id": "UU_j7xjUSs8b9Zc89qA4L9qA"
    },
    {
        "name": "Simpol (Chef Tatung)",
        "channel_id": "UCt4nI4bH-Wv_9l5s_8p36Lw",
        # Simpol's upload playlist can be derived or fetched dynamically
        "handle": "Simpol"
    },
    {
        "name": "Kuya Fern's Cooking",
        "handle": "Kuya Fern's Cooking"
    }
]

def resolve_channel_uploads_id(channel_query: str) -> Optional[Dict[str, str]]:
    """Resolves a channel name, handle, or ID to its upload playlist ID."""
    yt = get_youtube()
    
    # If standard channel ID (starts with UC)
    if channel_query.startswith("UC") and len(channel_query) == 24:
        return {
            "channel_id": channel_query,
            "uploads_playlist_id": "UU" + channel_query[2:],
            "name": channel_query
        }

    # Search for the channel
    resp = yt.search().list(
        q=channel_query,
        type="channel",
        part="snippet",
        maxResults=1
    ).execute()

    items = resp.get("items", [])
    if not items:
        return None

    channel_id = items[0]["id"]["channelId"]
    channel_title = items[0]["snippet"]["title"]

    # Get uploads playlist ID from channels endpoint
    ch_resp = yt.channels().list(
        id=channel_id,
        part="contentDetails,snippet"
    ).execute()

    ch_items = ch_resp.get("items", [])
    if not ch_items:
        return None

    uploads_id = ch_items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    return {
        "channel_id": channel_id,
        "uploads_playlist_id": uploads_id,
        "name": channel_title
    }

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
