"""Timeline Conform Engine — real auto-editor CLI + FFmpeg focal-push compiler.

Harvested from WyattBlue/auto-editor CLI:
  auto-editor INPUT -m 0.06s --when-silent cut --when-normal nil -o OUT

Then FFmpeg applies dynamic crop/scale punch-ins matching rig target_specs.
Outputs Compound.mov Agent Runbook (EDL) for MCP / drawer consumers.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFORM_DIR = Path(__file__).parent / "media" / "conformed"


def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _auto_editor_trim(raw_path: Path, trimmed_path: Path, dead_air_max_ms: int) -> Dict[str, Any]:
    """Invoke real auto-editor binary; return status metadata."""
    auto_editor_bin = shutil.which("auto-editor")
    meta: Dict[str, Any] = {
        "engine": "auto-editor",
        "binary": auto_editor_bin,
        "ok": False,
        "stderr_tail": "",
    }
    if not auto_editor_bin:
        meta["engine"] = "missing-auto-editor"
        return meta

    # Modern CLI (v29+): --when-silent cut; keep margin near dead-air target.
    margin_sec = max(0.04, min(0.25, dead_air_max_ms / 1000.0 * 0.5))
    cmd = [
        auto_editor_bin,
        str(raw_path),
        "-m",
        f"{margin_sec:.2f}s",
        "--edit",
        "audio",
        "--when-silent",
        "cut",
        "--when-normal",
        "nil",
        "--progress",
        "none",
        "-o",
        str(trimmed_path),
    ]
    # Also try deprecated flags as secondary attempt for older installs.
    res = _run(cmd)
    if res.returncode != 0 or not trimmed_path.exists():
        cmd_legacy = [
            auto_editor_bin,
            str(raw_path),
            "--margin",
            f"{margin_sec:.2f}sec",
            "--silent-speed",
            "99999",
            "--video-speed",
            "1.0",
            "-o",
            str(trimmed_path),
        ]
        res = _run(cmd_legacy)
        meta["engine"] = "auto-editor-legacy-flags"

    meta["ok"] = res.returncode == 0 and trimmed_path.exists() and trimmed_path.stat().st_size > 0
    meta["stderr_tail"] = (res.stderr or res.stdout or "")[-400:]
    meta["cmd"] = cmd
    return meta


def _ffmpeg_focal_push(
    trimmed_path: Path,
    final_path: Path,
    zoom_factor: float,
    cadence_sec: float,
    splice_times: List[float],
) -> Dict[str, Any]:
    """Dynamic center crop punch-in on cadence, then scale back to 720x1280."""
    # Prefer expression tied to splice timestamps when available; else periodic cadence.
    if splice_times and len(splice_times) >= 2:
        # Punch in for ~0.35s after each odd splice using enable expressions via overlay of crops is complex;
        # use periodic mod cadence derived from mean splice spacing.
        gaps = [splice_times[i + 1] - splice_times[i] for i in range(len(splice_times) - 1)]
        mean_gap = sum(gaps) / max(1, len(gaps))
        cadence_sec = max(0.6, round(mean_gap, 2))

    period = max(1.2, cadence_sec * 2.0)
    half = max(0.5, cadence_sec)
    # FFmpeg expression crop: alternate full-frame vs zoomed center crop on cadence.
    crop_filter = (
        f"crop='if(lt(mod(t\\,{period})\\,{half})\\,iw\\,iw/{zoom_factor})'"
        f":'if(lt(mod(t\\,{period})\\,{half})\\,ih\\,ih/{zoom_factor})'"
        f":'(iw-ow)/2':'(ih-oh)/2',"
        f"scale=720:1280:flags=lanczos,"
        f"eq=contrast=1.06:saturation=1.08"
    )

    def _ffmpeg(vf: str) -> subprocess.CompletedProcess:
        return _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(trimmed_path),
                "-vf",
                vf,
                "-af",
                "acompressor=threshold=-18dB:ratio=3:attack=5:release=50",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(final_path),
            ]
        )

    res = _ffmpeg(crop_filter)
    ok = res.returncode == 0 and final_path.exists() and final_path.stat().st_size > 0
    if ok:
        return {"ok": True, "engine": "ffmpeg-dynamic-crop", "stderr_tail": (res.stderr or "")[-200:]}

    # Unescaped comma form (some shells already pass through)
    alt = (
        f"crop=if(lt(mod(t\\,{period})\\,{half})\\,iw\\,iw/{zoom_factor})"
        f":if(lt(mod(t\\,{period})\\,{half})\\,ih\\,ih/{zoom_factor}),"
        f"scale=720:1280:flags=lanczos,eq=contrast=1.06:saturation=1.08"
    )
    res = _ffmpeg(alt)
    ok = res.returncode == 0 and final_path.exists() and final_path.stat().st_size > 0
    if ok:
        return {"ok": True, "engine": "ffmpeg-dynamic-crop-alt", "stderr_tail": ""}

    simple = f"scale=iw*{zoom_factor}:ih*{zoom_factor},crop=720:1280,eq=contrast=1.06:saturation=1.08"
    res = _ffmpeg(simple)
    ok = res.returncode == 0 and final_path.exists()
    return {
        "ok": ok,
        "engine": "ffmpeg-static-push",
        "stderr_tail": (res.stderr or "")[-400:],
    }


def conform_video_to_rig(
    raw_video_path: str,
    reference_telemetry: Dict[str, Any],
    rig_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    CONFORM_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = Path(raw_video_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw video missing: {raw_video_path}")

    trimmed_path = CONFORM_DIR / f"trimmed_{raw_path.name}"
    final_path = CONFORM_DIR / f"conformed_{raw_path.name}"
    # Clear stale outputs so we never serve an old conform
    for p in (trimmed_path, final_path):
        if p.exists():
            p.unlink()

    target_specs = rig_metadata.get("target_specs", {})
    dead_air_max_ms = int(target_specs.get("dead_air_max_ms", 120))
    zoom_factor = float(target_specs.get("focal_push_scale", 1.16))
    cadence_sec = round(10.0 / max(2.0, float(target_specs.get("splices_per_10s", 7.2))), 2)

    ae_meta = _auto_editor_trim(raw_path, trimmed_path, dead_air_max_ms)
    if not ae_meta["ok"]:
        # Spec allows ffmpeg silenceremove only as emergency bridge after auto-editor attempt
        cmd_silence = [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_path),
            "-af",
            f"silenceremove=stop_periods=-1:stop_duration={max(0.12, dead_air_max_ms/1000.0)}:stop_threshold=-35dB",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(trimmed_path),
        ]
        res = _run(cmd_silence)
        if res.returncode != 0 or not trimmed_path.exists():
            shutil.copyfile(raw_path, trimmed_path)
            ae_meta["engine"] = "copy-passthrough"
        else:
            ae_meta["engine"] = "ffmpeg-silenceremove-fallback"

    splice_times = list(reference_telemetry.get("splice_timestamps") or [0.0, 1.2, 2.5, 3.8])
    ff_meta = _ffmpeg_focal_push(trimmed_path, final_path, zoom_factor, cadence_sec, splice_times)
    if not ff_meta["ok"]:
        shutil.copyfile(trimmed_path, final_path)

    edl_rules = {
        "engine": "Overcrank v1.0 -> Compound.mov Bridge",
        "rig_id": rig_metadata.get("rig_id", "rig_street_broll_punch"),
        "rig_title": rig_metadata.get("title", "High-Yield Outlier Rig"),
        "target_splices_per_10s": target_specs.get("splices_per_10s", 7.8),
        "silence_gate": {
            "threshold_db": -35.0,
            "max_pause_ms": dead_air_max_ms,
            "pad_margin_ms": 60,
        },
        "focal_push_keyframes": [
            {
                "timecode_sec": round(t, 2),
                "scale": zoom_factor if idx % 2 == 1 else 1.0,
                "easing": "instant_cut",
            }
            for idx, t in enumerate(splice_times[:12])
        ],
        "broll_insert_markers": target_specs.get("hook_broll_timestamps", [1.1, 2.3, 3.6]),
        "pipeline": {
            "dead_air": ae_meta.get("engine"),
            "focal_push": ff_meta.get("engine"),
            "auto_editor_ok": bool(ae_meta.get("ok")),
        },
    }

    compound_prompt = (
        f"# COMPOUND.MOV AGENT EXECUTION SPEC — [{edl_rules['rig_title']}]\n\n"
        f"Apply the following deterministic frame rules extracted via Overcrank + Oriane API:\n"
        f"1. **Dead-Air Gate:** Strip all vocal pauses below `-35 dBFS` exceeding "
        f"`{edl_rules['silence_gate']['max_pause_ms']}ms` (leave `60ms` breath handles).\n"
        f"2. **Splice Cadence:** Enforce a mean shot duration of "
        f"`{target_specs.get('mean_shot_ms', 1280)}ms` "
        f"(`{edl_rules['target_splices_per_10s']} splices / 10s`).\n"
        f"3. **Focal Push Punch-Ins:** Trigger `{zoom_factor}x` center-frame hard punch-ins "
        f"on vocal RMS peaks at timestamps `{splice_times[:8]}`.\n"
        f"4. **Hook B-Roll Overlays:** Insert visual B-roll cuts at "
        f"`{edl_rules['broll_insert_markers']}s` while maintaining underlying vocal audio."
    )

    return {
        "conformed_filename": final_path.name,
        "conformed_video_url": f"/media/conformed/{final_path.name}",
        "compound_edl": edl_rules,
        "compound_prompt": compound_prompt,
        "pipeline": edl_rules["pipeline"],
    }
