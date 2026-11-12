"""Topic → short-form discovery.

No LLM. YouTube Data API ranks by view count. Public web search finds TikTok
and Instagram URLs, which are embedded directly. Clips are grouped into styles.
Falls back to the local catalog if both sources fail.
"""

from __future__ import annotations

import asyncio
import html
import json
import os
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from oriane_client import DEFAULT_COHORTS

CATALOG_PATH = Path(__file__).parent / "fixtures" / "shortform_catalog.json"


def _load_catalog() -> List[Dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    return list(json.loads(CATALOG_PATH.read_text()).get("clips", []))


def _tokens(query: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9+#]+", query.lower()) if len(t) >= 2]


def _score_clip(clip: Dict[str, Any], tokens: List[str]) -> float:
    if not tokens:
        return 0.15
    hay = " ".join(
        [
            clip.get("title", ""),
            clip.get("creator", ""),
            " ".join(clip.get("topics", [])),
            clip.get("rig_id", ""),
            clip.get("platform", ""),
        ]
    ).lower()
    hits = sum(1 for t in tokens if t in hay)
    topic_hits = sum(1 for t in tokens if t in [x.lower() for x in clip.get("topics", [])])
    yield_boost = float(clip.get("yield_multiplier", 1.0)) * 0.08
    return hits * 1.4 + topic_hits * 2.2 + yield_boost


def embed_and_watch(platform: str, video_id: str) -> Tuple[str, str]:
    if platform == "youtube":
        # mute=1 is required for browser autoplay; playlist=id enables loop
        qs = (
            f"autoplay=1&mute=1&loop=1&playlist={video_id}"
            f"&controls=0&rel=0&modestbranding=1&playsinline=1&enablejsapi=1"
        )
        return (
            f"https://www.youtube.com/embed/{video_id}?{qs}",
            f"https://www.youtube.com/shorts/{video_id}",
        )
    if platform == "tiktok":
        return (
            f"https://www.tiktok.com/embed/v2/{video_id}?autoplay=1",
            f"https://www.tiktok.com/@overcrank/video/{video_id}",
        )
    return (
        f"https://www.instagram.com/reel/{video_id}/embed",
        f"https://www.instagram.com/reel/{video_id}/",
    )


def _live_shortform_enabled() -> bool:
    """Web search needs no key. Set SHORTFORM_LIVE=0 to force the local catalog."""
    flag = os.getenv("SHORTFORM_LIVE", "").strip().lower()
    return flag not in {"0", "false", "no", "off"}


# Each style is searched on its own so the card is a group of alike videos.
# rig_id matches a cohort rig so Align / Conform still have cut targets.
_STYLES: List[Dict[str, str]] = [
    {
        "rig_id": "rig_street_broll_punch",
        "headline": "Street walk-and-talk",
        "plain_why": "Face in frame, phone in hand, moving on a street while you talk.",
        "yt_query": "{topic} street interview",
        "web_query": "{topic} street interview",
    },
    {
        "rig_id": "rig_whiteboard_kinetic",
        "headline": "Screen or whiteboard",
        "plain_why": "The idea is on a screen or board while you explain it.",
        "yt_query": "{topic} whiteboard",
        "web_query": "{topic} whiteboard",
    },
    {
        "rig_id": "rig_desk_monologue_ungraded",
        "headline": "Face to camera",
        "plain_why": "You stay close to the lens and talk straight into it.",
        "yt_query": "{topic} talking to camera",
        "web_query": "{topic} talking to camera",
    },
]


def _normalize_clip(raw: Dict[str, Any], source: str, score: float = 0.0) -> Dict[str, Any]:
    platform = raw.get("platform", "youtube")
    video_id = raw.get("video_id") or raw.get("id") or ""
    embed_url, watch_url = embed_and_watch(platform, video_id)
    if raw.get("watch_url"):
        watch_url = str(raw["watch_url"])
    local = (raw.get("local_video") or "").strip()
    # Live clips must not force local demo media
    use_local = bool(local) and source in {"catalog", "catalog-fallback"}
    local_video_url = f"/media/{local}" if use_local else None
    thumb = raw.get("thumbnail_url")
    if not thumb and platform == "youtube" and video_id and not use_local:
        thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return {
        "clip_id": raw.get("clip_id") or f"{platform}_{video_id}",
        "platform": platform,
        "title": raw.get("title") or "Short-form clip",
        "creator": raw.get("creator") or "Unknown",
        "topics": raw.get("topics") or [],
        "video_id": video_id,
        "embed_url": embed_url,
        "watch_url": watch_url,
        "local_video_url": local_video_url,
        "thumbnail_url": thumb,
        "views": int(raw.get("views") or 0),
        "yield_multiplier": float(raw.get("yield_multiplier") or 1.0),
        "saturation_pct": float(raw.get("saturation_pct") or 10.0),
        "rig_id": raw.get("rig_id") or "rig_street_broll_punch",
        "source": source,
        "score": round(score, 3),
    }


def _cohort_rig(rig_id: str) -> Dict[str, Any]:
    for rig in DEFAULT_COHORTS["sf_founder_interviews"]["rigs"]:
        if rig["rig_id"] == rig_id:
            return deepcopy(rig)
    return deepcopy(DEFAULT_COHORTS["sf_founder_interviews"]["rigs"][0])


def _clean_title(raw: str, platform: str) -> str:
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw or ""))).strip()
    text = re.sub(r"^\d{6,}\s*", "", text)
    if "›" in text:
        text = text.split("›")[-1].strip(" |")
    text = re.sub(r"\s*\|\s*(?:TikTok|Instagram|YouTube)\s*$", "", text, flags=re.I).strip(" |")
    text = re.sub(rf"^(?:{platform}|tiktok|instagram|youtube)\s+", "", text, flags=re.I).strip()
    return text[:140] or f"{platform} video"


def _parse_public_video_url(url: str) -> Optional[Dict[str, str]]:
    """Keep direct public video URLs. Skip profiles, tags, and homepages."""
    try:
        parsed = urlparse(url.split("?")[0])
    except Exception:
        return None
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path
    if host == "tiktok.com":
        doubled = re.search(r"/@/@([^/]+)/video/(\d+)", path)
        plain = re.search(r"/@([^/]*)/video/(\d+)", path)
        bare = re.search(r"/video/(\d+)", path)
        if doubled:
            user, video_id = doubled.group(1), doubled.group(2)
        elif plain and plain.group(2):
            user, video_id = plain.group(1), plain.group(2)
        elif bare:
            user, video_id = "", bare.group(1)
        else:
            return None
        creator = f"@{user}" if user else "TikTok"
        watch = (
            f"https://www.tiktok.com/@{user}/video/{video_id}"
            if user
            else f"https://www.tiktok.com/video/{video_id}"
        )
        return {
            "platform": "tiktok",
            "video_id": video_id,
            "creator": creator,
            "watch_url": watch,
        }
    if host == "instagram.com":
        match = re.search(r"/reel/([A-Za-z0-9_-]{5,})", path)
        if not match:
            return None
        code = match.group(1)
        return {
            "platform": "instagram",
            "video_id": code,
            "creator": "Instagram",
            "watch_url": f"https://www.instagram.com/reel/{code}/",
        }
    if host == "youtube.com":
        match = re.search(r"/shorts/([A-Za-z0-9_-]{6,})", path)
        if not match:
            return None
        vid = match.group(1)
        return {
            "platform": "youtube",
            "video_id": vid,
            "creator": "YouTube",
            "watch_url": f"https://www.youtube.com/shorts/{vid}",
        }
    return None


def _on_topic(text: str, topic: str) -> bool:
    tokens = _tokens(topic)
    if not tokens:
        return True
    hay = text.lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", hay) for token in tokens)


async def _youtube_ranked(query: str, topic: str, rig_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Shorts-length YouTube videos, ordered by real view count."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key or not query.strip():
        return []
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            ids: List[str] = []
            # Relevance keeps the style and topic. View count is applied after,
            # so a loosely related viral video does not outrank a real match.
            for order in ("relevance",):
                search = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": f"{query} shorts",
                        "type": "video",
                        "videoDuration": "short",
                        "order": order,
                        "maxResults": min(max(limit, 5), 8),
                        "key": api_key,
                        "safeSearch": "moderate",
                        "relevanceLanguage": "en",
                    },
                )
                if search.status_code != 200:
                    print(f"[shortform] YouTube HTTP {search.status_code}")
                    return []
                ids = [
                    (item.get("id") or {}).get("videoId")
                    for item in search.json().get("items", [])
                    if (item.get("id") or {}).get("videoId")
                ]
                if ids:
                    break
            if not ids:
                return []
            stats = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "statistics,snippet",
                    "id": ",".join(ids),
                    "key": api_key,
                },
            )
            if stats.status_code != 200:
                print(f"[shortform] YouTube stats HTTP {stats.status_code}")
                return []
            items = stats.json().get("items", [])
            id_order = {vid: i for i, vid in enumerate(ids)}
    except Exception as exc:
        print(f"[shortform] YouTube search failed: {exc}")
        return []

    ranked: List[Dict[str, Any]] = []
    for item in items:
        vid = item.get("id") or ""
        sn = item.get("snippet") or {}
        numbers = item.get("statistics") or {}
        views = int(numbers.get("viewCount") or 0)
        likes = int(numbers.get("likeCount") or 0)
        thumbs = sn.get("thumbnails") or {}
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        ranked.append(
            _normalize_clip(
                {
                    "clip_id": f"yt_{rig_id}_{vid}",
                    "platform": "youtube",
                    "title": sn.get("title") or "YouTube Short",
                    "creator": f"@{sn.get('channelTitle', 'youtube')}",
                    "topics": _tokens(query),
                    "video_id": vid,
                    "thumbnail_url": thumb,
                    "views": views,
                    "yield_multiplier": round(max(views, 1) / 100000, 2),
                    "saturation_pct": 0,
                    "rig_id": rig_id,
                },
                source="youtube",
                score=float(views + likes * 10),
            )
        )
    ranked.sort(key=lambda clip: id_order.get(clip["video_id"], 99))
    on_topic = [clip for clip in ranked if _on_topic(f"{clip['title']} {clip['creator']}", topic)]
    other = [clip for clip in ranked if clip not in on_topic]
    on_topic.sort(key=lambda clip: clip["views"], reverse=True)
    # Performance rank only inside videos that actually match the topic.
    return (on_topic or other)[:limit]


_WEB_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_WEB_CACHE_TTL = 600.0

# Title words that place a web result into a style. Checked in this order.
_STYLE_WORDS: Dict[str, Tuple[str, ...]] = {
    "rig_street_broll_punch": ("street", "walk", "walking", "sidewalk", "outdoor", "interview"),
    "rig_whiteboard_kinetic": ("whiteboard", "screen", "tutorial", "coding", "code", "demo", "laptop", "diagram"),
    "rig_desk_monologue_ungraded": ("talking", "camera", "face", "podcast", "explain"),
}


def _unwrap_search_href(href: str) -> str:
    href = html.unescape(href or "").strip()
    if href.startswith("//"):
        href = "https:" + href
    if "uddg=" not in href:
        return href
    try:
        wrapped = href if href.startswith("http") else "https:" + href
        target = parse_qs(urlparse(wrapped).query).get("uddg", [""])[0]
        return unquote(target) or href
    except Exception:
        return href


def _clips_from_search_html(page: str, topic: str) -> List[Dict[str, Any]]:
    """Pull TikTok and Instagram video links out of a search results page."""
    anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S)
    raw_urls = re.findall(
        r"https://www\.(?:tiktok\.com/@[^\"'\s<>]+/video/\d+|instagram\.com/reel/[A-Za-z0-9_-]{5,})",
        page,
    )
    pairs: List[Tuple[str, str]] = [(href, inner) for href, inner in anchors]
    pairs.extend((url, "") for url in raw_urls)

    found: List[Dict[str, Any]] = []
    seen = set()
    for href, inner in pairs:
        parsed = _parse_public_video_url(_unwrap_search_href(href))
        if not parsed:
            continue
        key = (parsed["platform"], parsed["video_id"])
        if key in seen:
            continue
        seen.add(key)
        title = _clean_title(inner, parsed["platform"]) if inner else f"{parsed['platform']} video"
        if title.startswith(parsed["video_id"]):
            title = title[len(parsed["video_id"]) :].strip(" |-") or title
        found.append(
            _normalize_clip(
                {
                    "clip_id": f"web_{parsed['platform']}_{parsed['video_id']}",
                    "platform": parsed["platform"],
                    "title": title,
                    "creator": parsed["creator"],
                    "topics": _tokens(topic),
                    "video_id": parsed["video_id"],
                    "watch_url": parsed["watch_url"],
                    "views": 0,
                    "yield_multiplier": 1.0,
                    "saturation_pct": 0,
                    "rig_id": "",
                },
                source="web",
                score=float(max(0, 20 - len(found))),
            )
        )
    found.sort(
        key=lambda clip: (_on_topic(f"{clip['title']} {clip['creator']}", topic), clip["score"]),
        reverse=True,
    )
    # Keep both platforms. Anchors from one site often appear first and would crowd the other out.
    balanced: List[Dict[str, Any]] = []
    per_platform = {"tiktok": 0, "instagram": 0}
    for clip in found:
        platform = clip["platform"]
        if per_platform.get(platform, 0) >= 6:
            continue
        per_platform[platform] = per_platform.get(platform, 0) + 1
        balanced.append(clip)
    return balanced


async def _web_pool(topic: str) -> List[Dict[str, Any]]:
    """One public web search for TikTok and Instagram. Cached so a refresh does not get rate-limited."""
    key = topic.strip().lower()
    cached = _WEB_CACHE.get(key)
    if cached and time.time() - cached[0] < _WEB_CACHE_TTL:
        return [dict(clip) for clip in cached[1]]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    queries = (
        f"{topic} site:tiktok.com/@",
        f"{topic} site:instagram.com/reel",
    )
    pages: List[str] = []
    try:
        async with httpx.AsyncClient(timeout=14.0, headers=headers, follow_redirects=True) as client:
            for query in queries:
                brave = await client.get(
                    "https://search.brave.com/search",
                    params={"q": query, "source": "web"},
                )
                if brave.status_code == 200:
                    pages.append(brave.text)
                else:
                    print(f"[shortform] Brave HTTP {brave.status_code}")
                    ddg = await client.get(
                        "https://html.duckduckgo.com/html/",
                        params={"q": query},
                    )
                    if ddg.status_code == 200:
                        pages.append(ddg.text)
                    else:
                        print(f"[shortform] DuckDuckGo HTTP {ddg.status_code}")
    except Exception as exc:
        print(f"[shortform] Web search failed: {exc}")
        return []

    clips = _clips_from_search_html("\n".join(pages), topic)
    if clips:
        _WEB_CACHE[key] = (time.time(), clips)
    return clips


def _style_for_clip(clip: Dict[str, Any]) -> Optional[str]:
    hay = f"{clip.get('title', '')} {clip.get('creator', '')}".lower()
    for rig_id, words in _STYLE_WORDS.items():
        if any(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", hay) for word in words):
            return rig_id
    # Most unmatched short-form hits are a person talking to camera.
    return "rig_desk_monologue_ungraded"


def _style_rig(style: Dict[str, str], clips: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
    base = _cohort_rig(style["rig_id"])
    best_views = max(int(c.get("views") or 0) for c in clips)
    base.update(
        {
            "headline": style["headline"],
            "plain_why": style["plain_why"],
            "title": style["headline"],
            "visual_query": style["yt_query"].format(topic=topic),
            "sample_count": len(clips),
            "mean_views": best_views,
            "yield_multiplier": round(max(best_views, 1) / 100000, 2),
            "saturation_pct": 0,
            "quadrant": "HIGH_YIELD_UNSATURATED",
            "reference_creator": clips[0].get("creator") or base.get("reference_creator"),
            "data_source": "style-group",
        }
    )
    return base


def _take_web_clip(clip: Dict[str, Any], rig_id: str) -> Dict[str, Any]:
    clip["_used"] = True
    clone = {k: v for k, v in clip.items() if k != "_used"}
    clone["rig_id"] = rig_id
    clone["clip_id"] = f"{clone['clip_id']}_{rig_id[-6:]}"
    return clone


def _web_for_style(pool: List[Dict[str, Any]], rig_id: str, limit: int = 2) -> List[Dict[str, Any]]:
    candidates = [
        clip for clip in pool if not clip.get("_used") and _style_for_clip(clip) == rig_id
    ]
    picked: List[Dict[str, Any]] = []
    # One TikTok and one Instagram when the style has both, so neither site crowds the other out.
    for platform in ("tiktok", "instagram"):
        for clip in candidates:
            if clip.get("_used") or clip["platform"] != platform:
                continue
            picked.append(_take_web_clip(clip, rig_id))
            break
        if len(picked) >= limit:
            return picked
    for clip in candidates:
        if clip.get("_used"):
            continue
        picked.append(_take_web_clip(clip, rig_id))
        if len(picked) >= limit:
            break
    return picked


async def _style_group(
    style: Dict[str, str], topic: str, web_pool: List[Dict[str, Any]]
) -> Optional[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    yt_query = style["yt_query"].format(topic=topic)
    youtube = await _youtube_ranked(yt_query, topic, style["rig_id"], limit=3)
    web = _web_for_style(web_pool, style["rig_id"], limit=2)
    merged: List[Dict[str, Any]] = []
    seen = set()
    for clip in youtube + web:
        key = f"{clip['platform']}:{clip['video_id']}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(clip)
    if not merged:
        return None
    # Known view counts first. Web results with no public count keep search order after those.
    merged.sort(key=lambda clip: (int(clip.get("views") or 0) > 0, int(clip.get("views") or 0), clip.get("score") or 0), reverse=True)
    return _style_rig(style, merged, topic), merged[:4]


def _matrix_from_rigs(topic: str, rigs: List[Dict[str, Any]], cohort_id: str) -> Dict[str, Any]:
    base = deepcopy(DEFAULT_COHORTS.get(cohort_id, DEFAULT_COHORTS["sf_founder_interviews"]))
    base["topic"] = topic
    base["oriane_mode"] = "style-groups"
    base["rigs"] = rigs
    return base


def _catalog_matches(query: str, limit: int, platform_filter: set) -> List[Dict[str, Any]]:
    tokens = _tokens(query)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for clip in _load_catalog():
        if platform_filter and clip.get("platform") not in platform_filter:
            continue
        score = _score_clip(clip, tokens)
        if tokens and score < 1.2:
            continue
        scored.append((score, clip))
    scored.sort(key=lambda pair: (-pair[0], -float(pair[1].get("yield_multiplier", 0))))
    return [_normalize_clip(c, source="catalog", score=s) for s, c in scored[:limit]]


def _catalog_groups(query: str, limit: int, platform_filter: set, cohort_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Last resort: local clips bucketed by the rig they were filmed in."""
    catalog = _catalog_matches(query, limit=max(limit, 8), platform_filter=platform_filter)
    if not catalog:
        fallback = sorted(_load_catalog(), key=lambda c: float(c.get("views") or 0), reverse=True)[:limit]
        catalog = [_normalize_clip(c, source="catalog-fallback", score=0.5) for c in fallback]
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for clip in catalog:
        buckets.setdefault(clip.get("rig_id") or "rig_street_broll_punch", []).append(clip)
    rigs: List[Dict[str, Any]] = []
    clips: List[Dict[str, Any]] = []
    for rig_id, group in buckets.items():
        group.sort(key=lambda c: int(c.get("views") or 0), reverse=True)
        style = next((s for s in _STYLES if s["rig_id"] == rig_id), None)
        if style is None:
            base = _cohort_rig(rig_id)
            style = {
                "rig_id": rig_id,
                "headline": base.get("title", "This style"),
                "plain_why": "Shot the same way as the videos in this group.",
                "yt_query": "{topic}",
            }
        rigs.append(_style_rig(style, group, query))
        clips.extend(group[:4])
    rigs.sort(key=lambda r: int(r.get("mean_views") or 0), reverse=True)
    return rigs, clips


async def discover_shortform(
    query: str,
    limit: int = 8,
    platforms: Optional[List[str]] = None,
    cohort_id: str = "sf_founder_interviews",
) -> Dict[str, Any]:
    platform_filter = {p.lower() for p in (platforms or []) if p}
    rigs: List[Dict[str, Any]] = []
    clips: List[Dict[str, Any]] = []
    mode = "catalog"

    if _live_shortform_enabled():
        # One web search for the whole topic. Three Brave calls was what got rate-limited.
        web_pool = await _web_pool(query)
        groups = []
        for style in _STYLES:
            groups.append(await _style_group(style, query, web_pool))
        for group in groups:
            if not group:
                continue
            rig, group_clips = group
            if platform_filter:
                group_clips = [c for c in group_clips if c["platform"] in platform_filter]
                if not group_clips:
                    continue
                rig = _style_rig(
                    next(s for s in _STYLES if s["rig_id"] == rig["rig_id"]),
                    group_clips,
                    query,
                )
            rigs.append(rig)
            clips.extend(group_clips)
        if rigs:
            rigs.sort(key=lambda r: int(r.get("mean_views") or 0), reverse=True)
            mode = "web+youtube"

    if not clips:
        rigs, clips = _catalog_groups(query, limit, platform_filter, cohort_id)
        mode = "catalog"

    by_platform: Dict[str, int] = {}
    for c in clips:
        by_platform[c["platform"]] = by_platform.get(c["platform"], 0) + 1

    return {
        "query": query,
        "mode": mode,
        "total": len(clips),
        "platforms": by_platform,
        "clips": clips,
        "matrix": _matrix_from_rigs(query, rigs, cohort_id),
    }
