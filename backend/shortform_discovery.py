"""Topic → short-form discovery.

Uses Claude to interpret the topic into Shorts search queries, then YouTube Data API
to fetch real embeddable videos. Falls back to local catalog clips if APIs fail.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

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
    """Prefer real YouTube embeds whenever keys exist (even if DEMO_MODE=1 for other systems)."""
    flag = os.getenv("SHORTFORM_LIVE", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    return bool(os.getenv("YOUTUBE_API_KEY", "").strip() or os.getenv("ANTHROPIC_API_KEY", "").strip())


def _normalize_clip(raw: Dict[str, Any], source: str, score: float = 0.0) -> Dict[str, Any]:
    platform = raw.get("platform", "youtube")
    video_id = raw.get("video_id") or raw.get("id") or ""
    embed_url, watch_url = embed_and_watch(platform, video_id)
    local = (raw.get("local_video") or "").strip()
    # Live YouTube clips must not force local demo media
    use_local = bool(local) and not source.startswith("youtube") and not source.startswith("claude")
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


async def _claude_search_queries(topic: str) -> List[str]:
    """Ask Claude for corrected YouTube Shorts search queries for this topic."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or not topic.strip():
        return [topic.strip()]

    prompt = (
        "You help find viral YouTube Shorts. Given a user topic (may have typos), "
        "return ONLY a JSON array of 3 short search strings for YouTube Shorts. "
        "Focus on founder interviews, street mic, AI startups, salary, whiteboard, coding demos when relevant. "
        "No markdown, no commentary.\n\n"
        f"Topic: {topic}"
    )
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if resp.status_code != 200:
            print(f"[shortform] Claude HTTP {resp.status_code}")
            return [topic.strip()]
        data = resp.json()
        text = "".join(
            p.get("text", "") for p in (data.get("content") or []) if p.get("type") == "text"
        ).strip()
        # Extract JSON array even if wrapped in fences
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return [topic.strip()]
        parsed = json.loads(match.group(0))
        queries = [str(q).strip() for q in parsed if str(q).strip()]
        return queries[:4] or [topic.strip()]
    except Exception as exc:
        print(f"[shortform] Claude query expand failed: {exc}")
        return [topic.strip()]


async def _youtube_search(query: str, limit: int = 6) -> List[Dict[str, Any]]:
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key or not query.strip():
        return []
    params = {
        "part": "snippet",
        "q": f"{query} shorts",
        "type": "video",
        "videoDuration": "short",
        "maxResults": min(limit, 10),
        "key": api_key,
        "safeSearch": "moderate",
        "relevanceLanguage": "en",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get("https://www.googleapis.com/youtube/v3/search", params=params)
            if resp.status_code != 200:
                print(f"[shortform] YouTube HTTP {resp.status_code}: {resp.text[:200]}")
                return []
            items = resp.json().get("items", [])
    except Exception as exc:
        print(f"[shortform] YouTube search failed: {exc}")
        return []

    out: List[Dict[str, Any]] = []
    for item in items:
        vid = (item.get("id") or {}).get("videoId")
        sn = item.get("snippet") or {}
        if not vid:
            continue
        thumbs = sn.get("thumbnails") or {}
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        out.append(
            _normalize_clip(
                {
                    "clip_id": f"yt_live_{vid}",
                    "platform": "youtube",
                    "title": sn.get("title") or "YouTube Short",
                    "creator": f"@{sn.get('channelTitle', 'youtube')}",
                    "topics": _tokens(query),
                    "video_id": vid,
                    "thumbnail_url": thumb,
                    "views": 0,
                    "yield_multiplier": 2.8,
                    "saturation_pct": 2.5,
                    "rig_id": "rig_street_broll_punch",
                },
                source="claude+youtube",
                score=4.0,
            )
        )
    return out


async def _live_clips_via_claude(topic: str, limit: int) -> List[Dict[str, Any]]:
    if not _live_shortform_enabled():
        return []
    queries = await _claude_search_queries(topic)
    merged: List[Dict[str, Any]] = []
    seen = set()
    for q in queries:
        batch = await _youtube_search(q, limit=max(3, limit))
        for clip in batch:
            key = clip["video_id"]
            if key in seen:
                continue
            seen.add(key)
            merged.append(clip)
            if len(merged) >= limit:
                return merged
    return merged


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


async def discover_shortform(
    query: str,
    limit: int = 8,
    platforms: Optional[List[str]] = None,
) -> Dict[str, Any]:
    platform_filter = {p.lower() for p in (platforms or []) if p}
    live: List[Dict[str, Any]] = []
    if not platform_filter or "youtube" in platform_filter:
        live = await _live_clips_via_claude(query, limit=limit)

    catalog = _catalog_matches(query, limit=limit, platform_filter=platform_filter)

    merged: List[Dict[str, Any]] = []
    seen = set()
    for clip in live + catalog:
        key = f"{clip['platform']}:{clip['video_id']}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(clip)
        if len(merged) >= limit:
            break

    if not merged:
        fallback = sorted(
            _load_catalog(),
            key=lambda c: float(c.get("yield_multiplier", 0)),
            reverse=True,
        )[:limit]
        merged = [_normalize_clip(c, source="catalog-fallback", score=0.5) for c in fallback]

    by_platform: Dict[str, int] = {}
    for c in merged:
        by_platform[c["platform"]] = by_platform.get(c["platform"], 0) + 1

    mode = "claude+youtube" if live else "catalog"
    return {
        "query": query,
        "mode": mode,
        "total": len(merged),
        "platforms": by_platform,
        "clips": merged,
    }
