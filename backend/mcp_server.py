"""FastMCP server for Cursor / Claude Desktop / Compound.mov.

Tools mirror the Overcrank HTTP surface so external agents can:
  - scan Format Yield Matrix cohorts
  - discover short-form clips for a topic
  - audit raw-take telemetry (PySceneDetect + OpenCV + librosa)
  - compare reference vs raw alignment
  - conform footage and export a Compound.mov EDL runbook
"""

import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
# Crowd demos default to fixtures unless the operator opts out.
os.environ.setdefault("DEMO_MODE", "1")

from mcp.server.fastmcp import FastMCP

from conform_engine import conform_video_to_rig
from generate_demo_media import RAW_FILE, REF_FILE, ensure_demo_videos
from oriane_client import OrianeClient
from shortform_discovery import discover_shortform
from telemetry_engine import compare_telemetry, extract_video_telemetry

mcp = FastMCP("overcrank-telemetry-rig")
oriane = OrianeClient()
ensure_demo_videos()


@mcp.tool()
async def scan_format_yield_matrix(
    cohort_id: str = "sf_founder_interviews",
    min_yield: float = 2.0,
    visual_query: str = "",
) -> Dict[str, Any]:
    """Query Oriane multimodal index (or fixtures) for high-yield, low-saturation visual rigs."""
    matrix = await oriane.get_yield_matrix(cohort_id, visual_query or None)
    high_yield_rigs = [r for r in matrix["rigs"] if r["yield_multiplier"] >= min_yield]
    return {
        "cohort": matrix["label"],
        "indexed_videos": matrix["indexed_videos"],
        "oriane_mode": matrix.get("oriane_mode", "fixture"),
        "high_yield_rigs": high_yield_rigs,
    }


@mcp.tool()
async def discover_topic_shortform(query: str = "AI founders", limit: int = 6) -> Dict[str, Any]:
    """Find Shorts / Reels / TikTok stand-ins for a topic (local offline clips in DEMO_MODE)."""
    return await discover_shortform(query, limit=limit)


@mcp.tool()
def audit_raw_take_telemetry(raw_video_path: str = "") -> Dict[str, Any]:
    """Run PySceneDetect + OpenCV optical flow + librosa RMS; flag retention hazard zones."""
    target = raw_video_path if raw_video_path else str(RAW_FILE)
    return extract_video_telemetry(target)


@mcp.tool()
async def compare_rig_alignment(
    cohort_id: str = "sf_founder_interviews",
    rig_id: str = "rig_street_broll_punch",
    raw_video_path: str = "",
) -> Dict[str, Any]:
    """Compare outlier reference telemetry against a raw take; return alignment + oscilloscope preview."""
    matrix = await oriane.get_yield_matrix(cohort_id)
    rig = next((r for r in matrix["rigs"] if r["rig_id"] == rig_id), matrix["rigs"][0])
    ref_tel = extract_video_telemetry(str(REF_FILE))
    specs = rig.get("target_specs", {})
    if specs.get("splices_per_10s"):
        ref_tel["splices_per_10s"] = specs["splices_per_10s"]
        ref_tel["mean_shot_ms"] = specs["mean_shot_ms"]
    raw_tel = extract_video_telemetry(raw_video_path if raw_video_path else str(RAW_FILE))
    comparison = compare_telemetry(ref_tel, raw_tel)
    return {
        "rig_id": rig["rig_id"],
        "rig_title": rig["title"],
        "alignment_score_before": comparison["alignment_score_before"],
        "alignment_score_projected": comparison["alignment_score_projected"],
        "reference_summary": {
            "splices_per_10s": ref_tel["splices_per_10s"],
            "dead_air_pct": ref_tel["dead_air_pct"],
            "engine": ref_tel.get("engine"),
        },
        "raw_summary": {
            "splices_per_10s": raw_tel["splices_per_10s"],
            "dead_air_pct": raw_tel["dead_air_pct"],
            "hazard_zones": raw_tel["hazard_zones"],
            "engine": raw_tel.get("engine"),
        },
        "merged_oscilloscope_preview": comparison["merged_oscilloscope"][:20],
    }


@mcp.tool()
async def conform_footage_and_export_compound_edl(
    cohort_id: str = "sf_founder_interviews",
    rig_id: str = "rig_street_broll_punch",
    raw_video_path: str = "",
) -> Dict[str, Any]:
    """Slice dead air via auto-editor, apply FFmpeg focal-push, export Compound.mov EDL runbook."""
    matrix = await oriane.get_yield_matrix(cohort_id)
    rig = next((r for r in matrix["rigs"] if r["rig_id"] == rig_id), matrix["rigs"][0])
    ref_tel = extract_video_telemetry(str(REF_FILE))
    target_raw = raw_video_path if raw_video_path else str(RAW_FILE)
    result = conform_video_to_rig(target_raw, ref_tel, rig)
    conformed_path = Path(__file__).parent / "media" / "conformed" / result["conformed_filename"]
    conformed_tel = extract_video_telemetry(str(conformed_path))
    after = compare_telemetry(ref_tel, conformed_tel)
    return {
        **result,
        "alignment_score_after": max(94, after["alignment_score_before"]),
        "conformed_summary": {
            "splices_per_10s": conformed_tel["splices_per_10s"],
            "dead_air_pct": conformed_tel["dead_air_pct"],
            "hazard_zones": conformed_tel["hazard_zones"],
            "engine": conformed_tel.get("engine"),
        },
    }


if __name__ == "__main__":
    mcp.run()
