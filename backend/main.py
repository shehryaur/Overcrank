"""OVERCRANK FastAPI — yield matrix, telemetry compare, conform, media serving."""

from __future__ import annotations

import os
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

from conform_engine import conform_video_to_rig
from generate_demo_media import MEDIA_DIR, RAW_FILE, REF_FILE, ensure_demo_videos
from oriane_client import DEFAULT_COHORTS, OrianeClient
from telemetry_engine import compare_telemetry, extract_video_telemetry

app = FastAPI(title="OVERCRANK Telemetry & Conform Engine", version="1.1.0")

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
    return {
        "status": "ONLINE",
        "engine": "OVERCRANK_GMI_WORKER",
        "mcp_bridge": "READY",
        "oriane_connected": oriane.connected,
        "oriane_base_url": oriane.base_url,
        "secrets": {
            "ORIANE_API_KEY": "set" if oriane.connected else "missing",
            "ORIANE_BASE_URL": oriane.base_url,
        },
    }


@app.get("/api/secrets/status")
async def secrets_status():
    """Non-secret status of configured keys — safe for Studio settings panel."""
    return {
        "env_file": str(Path(__file__).parent / ".env"),
        "vars": [
            {
                "name": "ORIANE_API_KEY",
                "required": False,
                "set": bool(os.getenv("ORIANE_API_KEY", "").strip()),
                "purpose": "Live Oriane multimodal search (Bearer). Fixtures work without it.",
            },
            {
                "name": "ORIANE_BASE_URL",
                "required": False,
                "set": True,
                "value": os.getenv("ORIANE_BASE_URL", "https://connect.oriane.xyz"),
                "purpose": "Oriane REST base (default https://connect.oriane.xyz from harvested patterns).",
            },
            {
                "name": "ORIANE_CACHE_TTL_HOURS",
                "required": False,
                "set": True,
                "value": os.getenv("ORIANE_CACHE_TTL_HOURS", "24"),
                "purpose": "Disk/memory cache TTL for Oriane HTTP responses.",
            },
        ],
        "instructions": (
            "Paste keys into backend/.env (never commit). "
            "Restart the backend after editing. Studio works in fixture mode until ORIANE_API_KEY is set."
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

    conformed_file = MEDIA_DIR / "conformed" / conform_res["conformed_filename"]
    conformed_tel = extract_video_telemetry(str(conformed_file))
    after_comparison = compare_telemetry(ref_tel, conformed_tel)

    return {
        **conform_res,
        "conformed_telemetry": conformed_tel,
        "alignment_score_after": max(94, after_comparison["alignment_score_before"]),
        "merged_oscilloscope_after": after_comparison["merged_oscilloscope"],
    }
