"""Topic → editing-format cards (the 4 options under the Shorts rail).

Uses Claude to invent topic-specific formats, then Oriane (when keyed) to score
yield / supply. Falls back to fixture rigs retitled for the topic.
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

import httpx

from oriane_client import DEFAULT_COHORTS, OrianeClient, _live_yield_enabled, _terms_from_text

# Plain-language archetypes we always try to cover for any topic.
_ARCHETYPE_HINTS = [
    "high-energy outdoor / street interview with fast B-roll inserts",
    "over-shoulder screen or whiteboard demo with punch-in zooms",
    "split screen: product/UI on top, talking head on bottom",
    "static talking-head desk take (usually oversaturated — show as caution)",
]


async def _claude_formats(topic: str) -> List[Dict[str, Any]]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or not topic.strip():
        return []

    prompt = (
        "You design short-form video EDITING FORMATS for creators.\n"
        f"Topic: {topic}\n\n"
        "Return ONLY a JSON array of exactly 4 objects. No markdown.\n"
        "Each object fields:\n"
        '- "headline": short plain name a non-editor understands (max 6 words), e.g. "Street mic walk-and-talk"\n'
        '- "plain_why": one sentence: when to pick this format for THIS topic\n'
        '- "title": technical edit label with timing, e.g. "Walking Street Mic + 1.1s B-Roll Flash (0-4s)"\n'
        '- "visual_query": 8-14 words describing the visual setup for search\n'
        '- "quadrant": "HIGH_YIELD_UNSATURATED" for the first 3, "OVERSATURATED_LOW_YIELD" for the last (caution)\n'
        '- "splices_per_10s": number (high ~7-8, caution ~1.5-2.5)\n'
        '- "mean_shot_ms": number\n'
        '- "dead_air_max_ms": number\n'
        '- "focal_push_scale": number 1.0-1.2\n'
        '- "hook_broll_timestamps": array of 0-3 floats in seconds\n'
        "Make formats SPECIFIC to the topic — not generic. Archetypes to cover:\n"
        + "\n".join(f"- {h}" for h in _ARCHETYPE_HINTS)
    )
    try:
        async with httpx.AsyncClient(timeout=22.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 900,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if resp.status_code != 200:
            print(f"[formats] Claude HTTP {resp.status_code}")
            return []
        text = "".join(
            p.get("text", "") for p in (resp.json().get("content") or []) if p.get("type") == "text"
        )
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        parsed = json.loads(match.group(0))
        return [x for x in parsed if isinstance(x, dict)][:4]
    except Exception as exc:
        print(f"[formats] Claude failed: {exc}")
        return []


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return (s[:40] or "format")


def _fixture_formats_for_topic(topic: str, cohort_id: str) -> List[Dict[str, Any]]:
    """Retitle cohort fixtures so they at least feel topic-tied when Claude is down."""
    cohort = deepcopy(DEFAULT_COHORTS.get(cohort_id, DEFAULT_COHORTS["sf_founder_interviews"]))
    topic_label = (topic or "this topic").strip()[:40]
    labels = [
        ("Street interview energy", f"Best outdoor hook style for “{topic_label}”"),
        ("Screen / whiteboard demo", f"Show the idea visually while talking about “{topic_label}”"),
        ("Split UI + face cam", f"Product or chart on top, you reacting — works for “{topic_label}”"),
        ("Static desk monologue", f"Caution: overused for “{topic_label}” — usually low yield"),
    ]
    out: List[Dict[str, Any]] = []
    for i, rig in enumerate(cohort["rigs"][:4]):
        headline, why = labels[i] if i < len(labels) else (rig["title"], "Editing format option")
        out.append(
            {
                **rig,
                "headline": headline,
                "plain_why": why,
                "data_source": "fixture",
            }
        )
    return out


def _rig_from_claude(raw: Dict[str, Any], idx: int) -> Dict[str, Any]:
    headline = str(raw.get("headline") or f"Format {idx + 1}").strip()
    title = str(raw.get("title") or headline).strip()
    visual = str(raw.get("visual_query") or headline).strip()
    quadrant = str(raw.get("quadrant") or "MID_YIELD")
    splices = float(raw.get("splices_per_10s") or (7.5 if idx < 3 else 2.0))
    mean_shot = float(raw.get("mean_shot_ms") or (1300 if idx < 3 else 4800))
    dead = float(raw.get("dead_air_max_ms") or (120 if idx < 3 else 450))
    zoom = float(raw.get("focal_push_scale") or (1.16 if idx < 3 else 1.0))
    hooks = raw.get("hook_broll_timestamps") or ([1.1, 2.3, 3.6] if idx < 3 else [])
    # Seed metrics — Oriane overwrites when live
    high = idx < 3
    return {
        "rig_id": f"rig_topic_{_slug(headline)}_{idx}",
        "headline": headline,
        "plain_why": str(raw.get("plain_why") or "").strip(),
        "title": title,
        "visual_query": visual,
        "saturation_pct": 2.0 + idx * 1.2 if high else 36.0,
        "yield_multiplier": round(3.2 - idx * 0.25, 2) if high else 0.68,
        "quadrant": quadrant,
        "sample_count": 200 + idx * 80,
        "mean_views": 300000 - idx * 40000 if high else 22000,
        "reference_video": "ref_hippolyte_outlier.mp4",
        "reference_creator": "@live",
        "data_source": "claude",
        "target_specs": {
            "splices_per_10s": splices,
            "mean_shot_ms": mean_shot,
            "dead_air_max_ms": dead,
            "focal_push_scale": zoom,
            "hook_broll_timestamps": hooks,
        },
    }


async def _enrich_with_oriane(oriane: OrianeClient, rig: Dict[str, Any], cohort: Dict[str, Any]) -> Dict[str, Any]:
    if not _live_yield_enabled() or not oriane.connected:
        return rig
    try:
        terms = _terms_from_text(rig.get("visual_query") or rig.get("title") or "")
        payload, source = await oriane.search_contents(
            visual_query=rig["visual_query"],
            caption_terms=terms or None,
            transcript_terms=terms or None,
            limit=20,
            min_visual_score=0.72,
        )
        live = oriane._map_hits_to_rig(rig["visual_query"], payload, cohort)
        if not live:
            return {**rig, "data_source": rig.get("data_source", "claude")}
        enriched = deepcopy(rig)
        enriched.update(
            {
                "saturation_pct": live["saturation_pct"],
                "yield_multiplier": live["yield_multiplier"],
                "sample_count": live["sample_count"],
                "mean_views": live["mean_views"],
                "reference_creator": live.get("reference_creator") or enriched.get("reference_creator"),
                "quadrant": live.get("quadrant") or enriched.get("quadrant"),
                "data_source": f"oriane:{source}",
                "oriane_source": True,
            }
        )
        # Keep headline/title/plain_why from Claude; adopt splice hints if present
        specs = enriched.get("target_specs") or {}
        live_specs = live.get("target_specs") or {}
        if live_specs.get("splices_per_10s"):
            specs["splices_per_10s"] = live_specs["splices_per_10s"]
            specs["mean_shot_ms"] = live_specs.get("mean_shot_ms", specs.get("mean_shot_ms"))
        enriched["target_specs"] = specs
        return enriched
    except Exception as exc:
        print(f"[formats] Oriane enrich failed: {exc}")
        return rig


async def build_topic_formats(
    topic: str,
    cohort_id: str = "sf_founder_interviews",
    oriane: Optional[OrianeClient] = None,
) -> Dict[str, Any]:
    """Return a yield-matrix shaped payload whose rigs are topic-specific."""
    client = oriane or OrianeClient()
    base = deepcopy(DEFAULT_COHORTS.get(cohort_id, DEFAULT_COHORTS["sf_founder_interviews"]))
    claude_raw = await _claude_formats(topic)
    if claude_raw:
        rigs = [_rig_from_claude(r, i) for i, r in enumerate(claude_raw)]
        mode = "claude"
    else:
        rigs = _fixture_formats_for_topic(topic, cohort_id)
        mode = "fixture-adapted"

    enriched: List[Dict[str, Any]] = []
    for rig in rigs:
        enriched.append(await _enrich_with_oriane(client, rig, base))

    # High-yield first; keep "usually avoid" / oversaturated formats at the bottom
    def _sort_key(r: Dict[str, Any]) -> tuple:
        caution = 1 if "OVERSATURATED" in str(r.get("quadrant") or "") else 0
        return (caution, -float(r.get("yield_multiplier") or 0))

    enriched.sort(key=_sort_key)
    sources = {r.get("data_source", "?") for r in enriched}
    if any(str(s).startswith("oriane") for s in sources):
        mode = "claude+oriane" if mode == "claude" else "oriane"

    base["rigs"] = enriched
    base["oriane_mode"] = mode
    base["oriane_connected"] = client.connected
    base["topic"] = topic
    base["label"] = f"Formats for “{topic.strip()[:48]}”"
    return base
