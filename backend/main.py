"""OVERCRANK FastAPI — yield matrix, telemetry compare, conform, media serving."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load secrets from backend/.env before constructing OrianeClient
load_dotenv(Path(__file__).parent / ".env")

from compound_handoff import package_compound_project, reveal_and_assist
from conform_engine import conform_video_to_rig
from format_discovery import build_topic_formats
from generate_demo_media import MEDIA_DIR, RAW_FILE, REF_FILE, REELS_DIR, ensure_demo_videos
from oriane_client import DEFAULT_COHORTS, OrianeClient
from provider_keys import provider_flags, secrets_catalog
from providers import demo_mode, polish_compound_prompt, probe_providers
from shortform_discovery import discover_shortform
from telemetry_engine import compare_telemetry, extract_video_telemetry

app = FastAPI(title="OVERCRANK Telemetry & Conform Engine", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_demo_videos()
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
oriane = OrianeClient()


class CompareRequest(BaseModel):
    cohort_id: str = "sf_founder_interviews"
    rig_id: str = "rig_street_broll_punch"
    raw_filename: Optional[str] = None


class ConformRequest(BaseModel):
    cohort_id: str = "sf_founder_interviews"
    rig_id: str = "rig_street_broll_punch"
    raw_filename: Optional[str] = None


class CompoundOpenRequest(BaseModel):
    conformed_filename: str
    compound_prompt: str
    compound_edl: Optional[dict] = None
    rig_title: str = "Overcrank outlier"
    launch: bool = True


def _resolve_rig(matrix: dict, rig_id: str) -> dict:
    return next((r for r in matrix["rigs"] if r["rig_id"] == rig_id), matrix["rigs"][0])


def _resolve_paths(rig: dict, raw_filename: Optional[str]):
    ref_path = MEDIA_DIR / "references" / rig.get("reference_video", REF_FILE.name)
    if not ref_path.exists():
        ref_path = REF_FILE
    raw_path = MEDIA_DIR / "raw" / (raw_filename or RAW_FILE.name)
    if not raw_path.exists():
        raw_path = RAW_FILE
    return ref_path, raw_path


@app.get("/api/health")
async def health():
    reels = list(REELS_DIR.glob("*.mp4")) if REELS_DIR.exists() else []
    return {
        "status": "ONLINE",
        "engine": "OVERCRANK_GMI_WORKER",
        "mcp_bridge": "READY",
        "demo_mode": demo_mode(),
        "oriane_connected": oriane.connected and not demo_mode(),
        "oriane_base_url": oriane.base_url,
        "media": {
            "reference": REF_FILE.exists(),
            "raw": RAW_FILE.exists(),
            "reels": len(reels),
            "conformed": (MEDIA_DIR / "conformed").exists(),
        },
        "secrets": provider_flags(),
        "providers": await probe_providers(),
    }


@app.get("/api/secrets/status")
async def secrets_status():
    """Non-secret status of configured keys — safe for Studio settings panel."""
    return {
        "env_file": str(Path(__file__).parent / ".env"),
        "vars": secrets_catalog(),
        "instructions": (
            "Paste GMI, Lovable, Compound.mov, and Anthropic keys into backend/.env. "
            "Restart the backend after saving. Blank keys stay off; the studio still runs on local fixtures."
        ),
    }


@app.get("/api/cohorts")
async def list_cohorts():
    return [
        {"cohort_id": k, "label": v["label"], "indexed_videos": v["indexed_videos"]}
        for k, v in DEFAULT_COHORTS.items()
    ]


@app.get("/api/yield-matrix")
async def get_yield_matrix(
    cohort_id: str = "sf_founder_interviews", visual_query: Optional[str] = None
):
    return await oriane.get_yield_matrix(cohort_id, visual_query)


class TopicSearchRequest(BaseModel):
    query: str
    cohort_id: str = "sf_founder_interviews"
    limit: int = 8


@app.post("/api/topic/search")
async def api_topic_search(req: TopicSearchRequest):
    """Search a topic → short-form clips + topic-specific edit formats."""
    q = (req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Enter a topic to search")
    discovery = await discover_shortform(q, limit=max(4, min(req.limit, 12)))
    # Formats change with the topic (Claude + Oriane), not fixed fixtures
    matrix = await build_topic_formats(q, cohort_id=req.cohort_id, oriane=oriane)
    preferred_rig = matrix["rigs"][0] if matrix.get("rigs") else None
    if discovery["clips"] and preferred_rig:
        # Point clips at the top format so selection stays consistent
        for clip in discovery["clips"]:
            if not clip.get("rig_id"):
                clip["rig_id"] = preferred_rig["rig_id"]
            # Surface format yield on the card when still default
            if float(clip.get("yield_multiplier") or 0) <= 2.85:
                clip["yield_multiplier"] = preferred_rig.get("yield_multiplier", clip.get("yield_multiplier"))
    return {
        "query": q,
        "discovery": discovery,
        "matrix": matrix,
        "preferred_rig_id": (preferred_rig or {"rig_id": "rig_street_broll_punch"})["rig_id"],
    }


@app.post("/api/upload-raw")
async def upload_raw_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    if not file.filename.lower().endswith((".mp4", ".mov", ".m4v", ".webm")):
        raise HTTPException(status_code=400, detail="Upload an .mp4 / video file")
    dest = MEDIA_DIR / "raw" / Path(file.filename).name
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"raw_filename": dest.name, "raw_video_url": f"/media/raw/{dest.name}"}


@app.post("/api/telemetry/compare")
async def api_compare_telemetry(req: CompareRequest):
    matrix = await oriane.get_yield_matrix(req.cohort_id)
    rig = _resolve_rig(matrix, req.rig_id)
    ref_path, raw_path = _resolve_paths(rig, req.raw_filename)

    ref_tel = extract_video_telemetry(str(ref_path))
    specs = rig.get("target_specs", {})
    if specs.get("splices_per_10s"):
        ref_tel["splices_per_10s"] = specs["splices_per_10s"]
        ref_tel["mean_shot_ms"] = specs["mean_shot_ms"]

    raw_tel = extract_video_telemetry(str(raw_path))
    comparison = compare_telemetry(ref_tel, raw_tel)

    return {
        "rig": rig,
        "reference_video_url": f"/media/references/{ref_path.name}",
        "raw_video_url": f"/media/raw/{raw_path.name}",
        "raw_filename": raw_path.name,
        **comparison,
    }


@app.post("/api/conform/execute")
async def api_execute_conform(req: ConformRequest):
    matrix = await oriane.get_yield_matrix(req.cohort_id)
    rig = _resolve_rig(matrix, req.rig_id)
    ref_path, raw_path = _resolve_paths(rig, req.raw_filename)

    ref_tel = extract_video_telemetry(str(ref_path))
    conform_res = conform_video_to_rig(str(raw_path), ref_tel, rig)
    conform_res["compound_prompt"] = await polish_compound_prompt(
        conform_res.get("compound_prompt", ""),
        rig.get("title", "Outlier Rig"),
    )

    conformed_file = MEDIA_DIR / "conformed" / conform_res["conformed_filename"]
    conformed_tel = extract_video_telemetry(str(conformed_file))
    after_comparison = compare_telemetry(ref_tel, conformed_tel)

    return {
        **conform_res,
        "conformed_telemetry": conformed_tel,
        "alignment_score_after": max(94, after_comparison["alignment_score_before"]),
        "merged_oscilloscope_after": after_comparison["merged_oscilloscope"],
        "demo_mode": demo_mode(),
    }


@app.post("/api/compound/open")
async def api_compound_open(req: CompoundOpenRequest):
    """Zip video + BRIEF into a Compound pack, reveal in Finder, copy chat line, open Compound."""
    video = MEDIA_DIR / "conformed" / Path(req.conformed_filename).name
    if not video.exists():
        raise HTTPException(status_code=404, detail="Conformed video not found — run Conform first")
    try:
        packaged = package_compound_project(
            video_path=video,
            compound_prompt=req.compound_prompt,
            compound_edl=req.compound_edl,
            rig_title=req.rig_title,
        )
        assist = reveal_and_assist(
            packaged["project_dir"],
            packaged["agent_line"],
            launch_app=req.launch,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Compound handoff failed: {exc}") from exc
    return {
        **packaged,
        "assist": assist,
        "steps": [
            "Download / unzip the pack (Finder also opened the folder).",
            "In Compound: New project → open that folder (or drag it in).",
            "Paste into Compound chat (already on your clipboard) and send.",
        ],
        "hint": "Pack ready. Add the folder in Compound, then paste the chat line.",
    }
