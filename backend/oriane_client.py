"""Oriane HTTP client for OVERCRANK.

Harvested request patterns from open-source Oriane adapters (connect.oriane.xyz):
  - Auth: Authorization: Bearer <ORIANE_API_KEY>
  - POST /rest/assets  (text → visual asset id)
  - POST /rest/contents/search  (caption/transcript + visualSimilarity)

All response mapping uses Overcrank schema only (VisualRig / saturation_pct /
yield_multiplier). No third-party product names appear in routes or payloads.
"""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "yield_matrix_cache.json"
ORIANE_CACHE_DIR = Path(__file__).parent / "fixtures" / "oriane_http_cache"
ORIANE_ASSETS_PATH = Path(__file__).parent / "fixtures" / "oriane_assets.json"

DEFAULT_BASE = "https://connect.oriane.xyz"

DEFAULT_COHORTS: Dict[str, Any] = {
    "sf_founder_interviews": {
        "cohort_id": "sf_founder_interviews",
        "label": "SF AI & Founder Interviews (@hippodupac Benchmark)",
        "indexed_videos": 14820,
        "baseline_er": 0.042,
        "rigs": [
            {
                "rig_id": "rig_street_broll_punch",
                "title": "Walking Street Mic + 1.1s B-Roll Flash (0-4s)",
                "visual_query": "person holding wireless mic outdoors street walking fast cut overlay",
                "saturation_pct": 1.6,
                "yield_multiplier": 3.45,
                "quadrant": "HIGH_YIELD_UNSATURATED",
                "sample_count": 237,
                "mean_views": 412000,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "@hippodupac",
                "target_specs": {
                    "splices_per_10s": 7.8,
                    "mean_shot_ms": 1280,
                    "dead_air_max_ms": 120,
                    "focal_push_scale": 1.16,
                    "hook_broll_timestamps": [1.1, 2.3, 3.6],
                },
            },
            {
                "rig_id": "rig_whiteboard_kinetic",
                "title": "Over-Shoulder Diagram Draw + Rapid 1.18x Punch",
                "visual_query": "hand drawing architecture diagram whiteboard marker closeup zoom",
                "saturation_pct": 2.4,
                "yield_multiplier": 2.95,
                "quadrant": "HIGH_YIELD_UNSATURATED",
                "sample_count": 355,
                "mean_views": 289000,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "@databysumit",
                "target_specs": {
                    "splices_per_10s": 6.9,
                    "mean_shot_ms": 1450,
                    "dead_air_max_ms": 140,
                    "focal_push_scale": 1.18,
                    "hook_broll_timestamps": [0.9, 2.5, 4.1],
                },
            },
            {
                "rig_id": "rig_dual_telemetry_split",
                "title": "Live Terminal / Chart Top-Half + Face Cam Bottom",
                "visual_query": "vertical split screen code terminal dashboard top talking head bottom",
                "saturation_pct": 4.1,
                "yield_multiplier": 2.60,
                "quadrant": "HIGH_YIELD_UNSATURATED",
                "sample_count": 607,
                "mean_views": 215000,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "@jeanklee",
                "target_specs": {
                    "splices_per_10s": 6.2,
                    "mean_shot_ms": 1610,
                    "dead_air_max_ms": 150,
                    "focal_push_scale": 1.14,
                    "hook_broll_timestamps": [1.4, 3.0],
                },
            },
            {
                "rig_id": "rig_static_podcast_couch",
                "title": "Static Two-Shot Couch / Studio Podcast Mic",
                "visual_query": "two people sitting on couch studio microphone static camera",
                "saturation_pct": 48.5,
                "yield_multiplier": 0.58,
                "quadrant": "OVERSATURATED_LOW_YIELD",
                "sample_count": 7187,
                "mean_views": 19400,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "Cohort Median",
                "target_specs": {
                    "splices_per_10s": 2.1,
                    "mean_shot_ms": 4760,
                    "dead_air_max_ms": 520,
                    "focal_push_scale": 1.0,
                    "hook_broll_timestamps": [],
                },
            },
            {
                "rig_id": "rig_desk_monologue_ungraded",
                "title": "Un-cut Desk Monologue (Zero Push First 5s)",
                "visual_query": "single person sitting at desk talking to webcam static frame",
                "saturation_pct": 34.2,
                "yield_multiplier": 0.71,
                "quadrant": "OVERSATURATED_LOW_YIELD",
                "sample_count": 5068,
                "mean_views": 24100,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "Cohort Median",
                "target_specs": {
                    "splices_per_10s": 1.8,
                    "mean_shot_ms": 5500,
                    "dead_air_max_ms": 480,
                    "focal_push_scale": 1.02,
                    "hook_broll_timestamps": [],
                },
            },
        ],
    },
    "eng_career_playbooks": {
        "cohort_id": "eng_career_playbooks",
        "label": "Software Eng & Growth Playbooks (@jeanklee / @datawithamney)",
        "indexed_videos": 19340,
        "baseline_er": 0.051,
        "rigs": [
            {
                "rig_id": "rig_salary_receipt_hook",
                "title": "0.8s Compensation/Metric Card Flash + Hard Cut",
                "visual_query": "close up screen metric chart number overlay fast zoom talking head",
                "saturation_pct": 1.9,
                "yield_multiplier": 3.72,
                "quadrant": "HIGH_YIELD_UNSATURATED",
                "sample_count": 367,
                "mean_views": 380000,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "@jeanklee",
                "target_specs": {
                    "splices_per_10s": 8.1,
                    "mean_shot_ms": 1230,
                    "dead_air_max_ms": 110,
                    "focal_push_scale": 1.17,
                    "hook_broll_timestamps": [0.8, 1.9, 3.2],
                },
            },
            {
                "rig_id": "rig_green_screen_point",
                "title": "Static Green Screen Head Floating Over Article",
                "visual_query": "green screen talking head bottom corner news article background",
                "saturation_pct": 41.0,
                "yield_multiplier": 0.64,
                "quadrant": "OVERSATURATED_LOW_YIELD",
                "sample_count": 7929,
                "mean_views": 21000,
                "reference_video": "ref_hippolyte_outlier.mp4",
                "reference_creator": "Cohort Median",
                "target_specs": {
                    "splices_per_10s": 2.4,
                    "mean_shot_ms": 4100,
                    "dead_air_max_ms": 430,
                    "focal_push_scale": 1.0,
                    "hook_broll_timestamps": [],
                },
            },
        ],
    },
}


def _stable_hash(path: str, query: dict, body: dict) -> str:
    blob = json.dumps({"path": path, "query": query, "body": body}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:20]


def _engagement_score(video: dict) -> float:
    views = float(video.get("viewsCount") or 0)
    if views <= 0:
        return 0.0
    likes = float(video.get("likesCount") or 0)
    comments = float(video.get("commentsCount") or 0)
    shares = float(video.get("sharesCount") or 0)
    return (likes + comments * 2.0 + shares * 3.0) / views


class OrianeClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("ORIANE_API_KEY", "").strip()
        # Prefer real connect.oriane.xyz; allow override for staging.
        self.base_url = os.getenv("ORIANE_BASE_URL", DEFAULT_BASE).rstrip("/")
        self.cache_ttl_hours = float(os.getenv("ORIANE_CACHE_TTL_HOURS", "24"))
        self._memory: Dict[str, Dict[str, Any]] = {}
        self._ensure_cache()

    def _ensure_cache(self) -> None:
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ORIANE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not FIXTURE_PATH.exists():
            FIXTURE_PATH.write_text(json.dumps(DEFAULT_COHORTS, indent=2))
        if not ORIANE_ASSETS_PATH.exists():
            ORIANE_ASSETS_PATH.write_text("{}")

    @property
    def connected(self) -> bool:
        return bool(self.api_key)

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _read_disk_cache(self, key: str) -> Optional[Dict[str, Any]]:
        path = ORIANE_CACHE_DIR / f"{key}.json"
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text())
            if not raw.get("response", {}).get("data"):
                return None
            return raw
        except Exception:
            return None

    def _write_disk_cache(self, key: str, request: dict, response: dict) -> None:
        path = ORIANE_CACHE_DIR / f"{key}.json"
        path.write_text(
            json.dumps(
                {
                    "request": request,
                    "status": 200,
                    "fetchedAt": datetime.now(timezone.utc).isoformat(),
                    "response": response,
                },
                indent=2,
            )
        )

    def _cache_fresh(self, entry: dict) -> bool:
        try:
            fetched = datetime.fromisoformat(entry["fetchedAt"].replace("Z", "+00:00"))
            return datetime.now(timezone.utc) - fetched < timedelta(hours=self.cache_ttl_hours)
        except Exception:
            return False

    async def _post_json(
        self, path: str, *, query: Optional[dict] = None, body: dict, timeout: float = 25.0
    ) -> Tuple[dict, str]:
        """POST to Oriane with memory→disk→live cascade. Returns (response_json, source)."""
        query = query or {}
        key = _stable_hash(path, query, body)

        mem = self._memory.get(key)
        if mem and self._cache_fresh(mem):
            return mem["response"], "cache"

        disk = self._read_disk_cache(key)
        if disk and self._cache_fresh(disk):
            self._memory[key] = disk
            return disk["response"], "cache"

        if not self.api_key:
            if disk:
                self._memory[key] = disk
                return disk["response"], "stale-cache"
            raise RuntimeError("ORIANE_API_KEY missing and no cached Oriane response")

        qs = "&".join(f"{k}={v}" for k, v in query.items())
        url = f"{self.base_url}{path}" + (f"?{qs}" if qs else "")

        last_err: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, 4):
                try:
                    resp = await client.post(url, headers=self._auth_headers(), json=body)
                    payload = resp.json() if resp.content else {}
                    if resp.is_success and isinstance(payload, dict) and payload.get("data") is not None:
                        entry = {
                            "response": payload,
                            "fetchedAt": datetime.now(timezone.utc).isoformat(),
                        }
                        self._memory[key] = entry
                        self._write_disk_cache(key, {"path": path, "query": query, "body": body}, payload)
                        return payload, "live"
                    if attempt < 3 and resp.status_code in {429, 500, 502, 503, 504}:
                        continue
                    raise RuntimeError(
                        f"Oriane {path} failed ({payload.get('error', {}).get('code', resp.status_code)})"
                    )
                except Exception as exc:
                    last_err = exc
                    if attempt == 3:
                        break

        if disk:
            self._memory[key] = disk
            return disk["response"], "stale-cache"
        raise RuntimeError(f"Oriane request failed: {last_err}")

    async def create_text_asset(self, text: str) -> str:
        assets = json.loads(ORIANE_ASSETS_PATH.read_text() or "{}")
        if text in assets:
            return assets[text]
        payload, _src = await self._post_json(
            "/rest/assets",
            body={"type": "text", "text": text},
            timeout=20.0,
        )
        asset_id = payload.get("data", {}).get("id")
        if not asset_id:
            raise RuntimeError("Oriane asset creation returned no id")
        assets[text] = asset_id
        ORIANE_ASSETS_PATH.write_text(json.dumps(assets, indent=2))
        return asset_id

    async def search_contents(
        self,
        *,
        visual_query: Optional[str] = None,
        transcript_terms: Optional[List[str]] = None,
        caption_terms: Optional[List[str]] = None,
        limit: int = 25,
        min_visual_score: float = 0.78,
        projection: str = "full",
        sort: str = "engagementRatePerViews:desc",
    ) -> Tuple[dict, str]:
        """Live multimodal search: visual asset + caption/transcript filters."""
        after = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%d")
        before = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        filters: Dict[str, Any] = {
            "format": {"includes": ["video"]},
            "publishedAt": {"after": after, "before": before},
        }

        if visual_query:
            asset_id = await self.create_text_asset(visual_query)
            filters["visualSimilarity"] = {
                "includes": {
                    "values": [{"assetId": asset_id, "minScore": min_visual_score}],
                    "operator": "or",
                }
            }

        nested: List[dict] = []
        if caption_terms:
            nested.append(
                {
                    "operator": "or",
                    "filters": {
                        "caption": {
                            "includesExactly": {"values": caption_terms, "operator": "or"}
                        }
                    },
                }
            )
        if transcript_terms:
            nested.append(
                {
                    "operator": "or",
                    "filters": {
                        "transcript": {
                            "includesExactly": {"values": transcript_terms, "operator": "or"}
                        },
                        "caption": {
                            "includesExactly": {"values": transcript_terms, "operator": "or"}
                        },
                    },
                }
            )

        body: Dict[str, Any] = {"operator": "and", "filters": filters}
        if nested:
            body["queries"] = nested

        return await self._post_json(
            "/rest/contents/search",
            query={
                "limit": limit,
                "offset": 0,
                "projection": projection,
                "sort": sort,
            },
            body=body,
        )

    def _map_hits_to_rig(
        self,
        visual_query: str,
        payload: dict,
        cohort_data: dict,
    ) -> Optional[dict]:
        data = payload.get("data") or {}
        results = data.get("results") or []
        if not results:
            return None

        pagination = (payload.get("metadata") or {}).get("pagination") or {}
        total_count = int(pagination.get("totalCount") or len(results))
        indexed = max(1, int(cohort_data.get("indexed_videos") or 1))
        # Supply saturation as share of cohort index (scaled to percent of indexed set).
        saturation_pct = round(max(0.4, min(55.0, (total_count / indexed) * 100.0)), 2)

        scores = [_engagement_score(v) for v in results]
        mean_rig = sum(scores) / max(1, len(scores))
        baseline = float(cohort_data.get("baseline_er") or 0.04)
        yield_multiplier = round(max(0.2, mean_rig / max(1e-6, baseline)), 2)

        mean_views = int(
            round(sum(float(v.get("viewsCount") or 0) for v in results) / max(1, len(results)))
        )
        top = results[0]
        creator = f"@{top.get('profileHandle')}" if top.get("profileHandle") else "Oriane Live Index"

        # Derive rough splice/focal targets from transcript chunk density when available.
        chunks = top.get("transcriptChunks") or []
        duration = float(top.get("duration") or 10.0) or 10.0
        if chunks:
            splices = round(min(12.0, max(4.0, (len(chunks) / duration) * 10.0)), 1)
            mean_shot = round((duration * 1000.0) / max(1, len(chunks)), 0)
        else:
            splices = 7.5
            mean_shot = 1330

        quadrant = (
            "HIGH_YIELD_UNSATURATED"
            if yield_multiplier >= 2.0 and saturation_pct < 10.0
            else "OVERSATURATED_LOW_YIELD"
            if yield_multiplier < 1.0
            else "MID_YIELD"
        )

        return {
            "rig_id": "rig_live_oriane_query",
            "title": f"Live Oriane Rig: {visual_query[:38]}",
            "visual_query": visual_query,
            "saturation_pct": saturation_pct,
            "yield_multiplier": yield_multiplier,
            "quadrant": quadrant,
            "sample_count": total_count,
            "mean_views": mean_views,
            "reference_video": "ref_hippolyte_outlier.mp4",
            "reference_creator": creator,
            "oriane_source": True,
            "oriane_top_transcript": (top.get("transcript") or "")[:280],
            "target_specs": {
                "splices_per_10s": splices,
                "mean_shot_ms": mean_shot,
                "dead_air_max_ms": 125,
                "focal_push_scale": 1.16,
                "hook_broll_timestamps": [1.0, 2.2, 3.5],
            },
        }

    async def get_yield_matrix(
        self, cohort_id: str, live_visual_query: Optional[str] = None
    ) -> Dict[str, Any]:
        cached = json.loads(FIXTURE_PATH.read_text())
        cohort_data = deepcopy(cached.get(cohort_id, cached["sf_founder_interviews"]))
        cohort_data["rigs"] = list(cohort_data.get("rigs", []))
        cohort_data["oriane_mode"] = "fixture"
        cohort_data["oriane_connected"] = self.connected

        if live_visual_query and (self.api_key or any(ORIANE_CACHE_DIR.glob("*.json"))):
            try:
                terms = [t for t in live_visual_query.lower().split() if len(t) > 3][:6]
                payload, source = await self.search_contents(
                    visual_query=live_visual_query,
                    caption_terms=terms or None,
                    transcript_terms=terms or None,
                    limit=25,
                    min_visual_score=0.78,
                )
                live_rig = self._map_hits_to_rig(live_visual_query, payload, cohort_data)
                if live_rig:
                    cohort_data["rigs"].insert(0, live_rig)
                    cohort_data["oriane_mode"] = source
            except Exception as exc:
                print(f"[OrianeClient] Falling back to cohort fixture ({exc})")
                cohort_data["oriane_mode"] = "fixture-fallback"

        return cohort_data
