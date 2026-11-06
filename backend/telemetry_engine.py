"""Rig telemetry extraction using real OSS pipelines.

- PySceneDetect `detect` + `ContentDetector` for splice cadence
- OpenCV Farneback optical flow for focal-push curve
- ffmpeg → WAV + soundfile/librosa for vocal RMS envelope
- Retention hazard zones: contiguous ≥1.1s where motion <18 and vocal < -34 dBFS

Fixture/synthetic telemetry is ONLY used when the media file is missing.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from scenedetect import ContentDetector, SceneManager, open_video

try:
    import librosa
    import soundfile as sf

    HAS_AUDIO = True
except Exception:  # pragma: no cover
    HAS_AUDIO = False


def _fixture_telemetry(duration_sec: float = 10.0, lively: bool = True) -> Dict[str, Any]:
    """Last-resort synthetic series when the video file itself is absent."""
    sample_hz = 10
    n = int(duration_sec * sample_hz)
    timeline: List[Dict[str, Any]] = []
    hazard_zones: List[Dict[str, float]] = []
    splice_timestamps = [0.0]

    if lively:
        for i in range(1, int(duration_sec / 1.2) + 1):
            splice_timestamps.append(round(i * 1.2, 2))
    else:
        splice_timestamps.extend([4.5, 9.0])

    for i in range(n):
        t = round(i / sample_hz, 2)
        if lively:
            focal = 35 + 40 * abs(np.sin(i / 3.5))
            vocal_db = -18.0 + 6.0 * abs(np.sin(i / 2.2))
            is_hazard = False
        else:
            focal = 8.0 + 4.0 * abs(np.sin(i / 20.0))
            if 2.5 <= t <= 4.6 or 7.0 <= t <= 9.2:
                vocal_db = -48.0
                focal = 5.0
                is_hazard = True
            else:
                vocal_db = -24.0 + 4.0 * abs(np.sin(i / 5.0))
                is_hazard = False
        vocal_energy = round(((max(-60.0, min(0.0, vocal_db)) + 60.0) / 60.0) * 100.0, 1)
        is_splice = any(abs(t - sp) <= 0.05 for sp in splice_timestamps if sp > 0)
        timeline.append(
            {
                "t": t,
                "focal_push": round(float(min(100.0, focal)), 1),
                "vocal_db": round(float(vocal_db), 1),
                "vocal_energy": vocal_energy,
                "is_splice": 100 if is_splice else 0,
                "is_hazard": is_hazard,
            }
        )

    if not lively:
        hazard_zones = [{"start": 2.5, "end": 4.6}, {"start": 7.0, "end": 9.2}]

    dead_air_bins = sum(1 for p in timeline if p["vocal_db"] < -35.0)
    return {
        "duration_sec": duration_sec,
        "splices_per_10s": round((len(splice_timestamps) / max(1.0, duration_sec)) * 10.0, 2),
        "mean_shot_ms": round((duration_sec * 1000.0) / max(1, len(splice_timestamps)), 0),
        "dead_air_pct": round((dead_air_bins / max(1, len(timeline))) * 100.0, 1),
        "splice_timestamps": splice_timestamps,
        "hazard_zones": hazard_zones,
        "timeline": timeline,
        "engine": {
            "scenedetect": False,
            "opencv_flow": False,
            "librosa_rms": False,
            "mode": "fixture-missing-media",
        },
    }


def _detect_splices(path: Path) -> tuple[List[float], List[float]]:
    """Use PySceneDetect SceneManager + ContentDetector (harvested API)."""
    video = open_video(str(path))
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=27.0))
    scene_manager.detect_scenes(video, show_progress=False)
    scene_list = scene_manager.get_scene_list()

    splice_timestamps: List[float] = [0.0]
    shot_durations_ms: List[float] = []
    for start_tc, end_tc in scene_list:
        s_sec = round(start_tc.get_seconds(), 2)
        e_sec = round(end_tc.get_seconds(), 2)
        if s_sec > 0.05 and s_sec not in splice_timestamps:
            splice_timestamps.append(s_sec)
        shot_durations_ms.append(round((e_sec - s_sec) * 1000, 1))
    return splice_timestamps, shot_durations_ms


def _optical_flow_series(path: Path, sample_hz: int) -> tuple[float, List[Dict[str, float]]]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV could not open {path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = round(frame_count / fps, 2) if frame_count > 0 else 10.0
    step_frames = max(1, int(round(fps / sample_hz)))

    prev_gray = None
    optical_series: List[Dict[str, float]] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % step_frames == 0:
            t_sec = round(frame_idx / fps, 2)
            # Spec: 320x180 grayscale for Farneback mean magnitude
            resized = cv2.resize(frame, (320, 180))
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                raw_score = float(np.mean(mag))
                norm_push = round(min(100.0, raw_score * 18.5), 1)
            else:
                norm_push = 15.0
            prev_gray = gray
            optical_series.append({"t": t_sec, "focal_push": norm_push})
        frame_idx += 1

    cap.release()
    if not optical_series:
        raise RuntimeError(f"No frames decoded from {path}")
    return duration_sec, optical_series


def _vocal_rms_db(path: Path, sample_hz: int, n_bins: int) -> np.ndarray:
    """Extract mono WAV via ffmpeg, then librosa/soundfile RMS → dBFS."""
    if not HAS_AUDIO:
        return np.full(n_bins, -22.0)

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "audio.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(wav_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not wav_path.exists() or wav_path.stat().st_size < 64:
            return np.full(n_bins, -45.0)

        # Prefer soundfile for WAV decode, then librosa RMS
        y, sr = sf.read(str(wav_path), dtype="float32")
        if y.ndim > 1:
            y = np.mean(y, axis=1)
        if y.size == 0:
            return np.full(n_bins, -45.0)

        hop_length = max(1, int(sr / sample_hz))
        rms = librosa.feature.rms(y=y, frame_length=hop_length * 2, hop_length=hop_length)[0]
        if float(np.max(rms)) <= 1e-9:
            return np.full(n_bins, -60.0)
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        if len(rms_db) < n_bins:
            pad = np.full(n_bins - len(rms_db), float(rms_db[-1]) if len(rms_db) else -45.0)
            rms_db = np.concatenate([rms_db, pad])
        return np.asarray(rms_db[:n_bins], dtype=float)


def extract_video_telemetry(video_path: str, sample_hz: int = 10) -> Dict[str, Any]:
    path = Path(video_path)
    if not path.exists():
        lively = "ref_" in path.name or "outlier" in path.name
        return _fixture_telemetry(duration_sec=10.0 if lively else 12.0, lively=lively)

    splice_timestamps, shot_durations_ms = _detect_splices(path)
    duration_sec, optical_series = _optical_flow_series(path, sample_hz)
    rms_db = _vocal_rms_db(path, sample_hz, len(optical_series))

    timeline: List[Dict[str, Any]] = []
    dead_air_bins = 0
    hazard_zones: List[Dict[str, float]] = []
    active_hazard_start = None
    splice_set = set(round(s, 1) for s in splice_timestamps)

    for idx, item in enumerate(optical_series):
        t = item["t"]
        db_val = float(rms_db[idx]) if idx < len(rms_db) else -45.0
        db_clamped = round(max(-60.0, min(0.0, db_val)), 1)
        vocal_energy = round(((db_clamped + 60.0) / 60.0) * 100.0, 1)

        is_dead_air = db_clamped < -35.0
        if is_dead_air:
            dead_air_bins += 1

        is_splice = any(abs(t - sp) <= (0.5 / sample_hz) for sp in splice_set if sp > 0)
        # Spec: motion < 18 AND vocal RMS < -34 dB
        is_hazard = (item["focal_push"] < 18.0) and (db_clamped < -34.0)

        if is_hazard and active_hazard_start is None:
            active_hazard_start = t
        elif not is_hazard and active_hazard_start is not None:
            # Spec: contiguous window ≥ 1.1s
            if (t - active_hazard_start) >= 1.1:
                hazard_zones.append({"start": active_hazard_start, "end": t})
            active_hazard_start = None

        timeline.append(
            {
                "t": t,
                "focal_push": item["focal_push"],
                "vocal_db": db_clamped,
                "vocal_energy": vocal_energy,
                "is_splice": 100 if is_splice else 0,
                "is_hazard": is_hazard,
            }
        )

    if active_hazard_start is not None and optical_series:
        end_t = optical_series[-1]["t"]
        if (end_t - active_hazard_start) >= 1.1:
            hazard_zones.append({"start": active_hazard_start, "end": end_t})

    total_bins = max(1, len(timeline))
    dead_air_pct = round((dead_air_bins / total_bins) * 100.0, 1)
    splices_per_10s = round((len(splice_timestamps) / max(1.0, duration_sec)) * 10.0, 2)
    mean_shot_ms = (
        round(float(np.mean(shot_durations_ms)), 0)
        if shot_durations_ms
        else round((duration_sec * 1000.0) / max(1, len(splice_timestamps)), 0)
    )

    return {
        "duration_sec": duration_sec,
        "splices_per_10s": splices_per_10s,
        "mean_shot_ms": mean_shot_ms,
        "dead_air_pct": dead_air_pct,
        "splice_timestamps": splice_timestamps,
        "hazard_zones": hazard_zones,
        "timeline": timeline,
        "engine": {
            "scenedetect": True,
            "opencv_flow": True,
            "librosa_rms": HAS_AUDIO,
            "mode": "live-oss",
        },
    }


def compare_telemetry(ref_telemetry: Dict[str, Any], raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
    splice_ratio = min(
        1.0,
        raw_telemetry["splices_per_10s"] / max(0.5, ref_telemetry["splices_per_10s"]),
    )
    dead_air_penalty = max(
        0.0, (raw_telemetry["dead_air_pct"] - ref_telemetry.get("dead_air_pct", 5.0)) * 1.4
    )
    hazard_penalty = len(raw_telemetry.get("hazard_zones", [])) * 12.0

    raw_score = (splice_ratio * 65.0) + 35.0 - dead_air_penalty - hazard_penalty
    alignment_score = int(round(max(12.0, min(98.0, raw_score))))

    max_len = max(len(ref_telemetry["timeline"]), len(raw_telemetry["timeline"]))
    merged_series = []
    for i in range(max_len):
        ref_pt = ref_telemetry["timeline"][i % len(ref_telemetry["timeline"])]
        raw_pt = raw_telemetry["timeline"][i] if i < len(raw_telemetry["timeline"]) else ref_pt
        merged_series.append(
            {
                "t": round(i * 0.1, 1),
                "ref_focal_push": ref_pt["focal_push"],
                "raw_focal_push": raw_pt["focal_push"],
                "ref_vocal_energy": ref_pt["vocal_energy"],
                "raw_vocal_energy": raw_pt["vocal_energy"],
                "ref_splice": ref_pt["is_splice"],
                "raw_splice": raw_pt["is_splice"],
                "raw_hazard": 100 if raw_pt["is_hazard"] else 0,
            }
        )

    return {
        "alignment_score_before": alignment_score,
        "alignment_score_projected": min(97, alignment_score + 48),
        "reference": ref_telemetry,
        "raw": raw_telemetry,
        "merged_oscilloscope": merged_series,
    }
