"""Synthesize offline-ready 9:16 demo media for crowd demos.

Creates:
  - references/ref_hippolyte_outlier.mp4  (high-cadence outlier)
  - raw/raw_founder_take.mp4              (slow take + dead-air hazards)
  - reels/*.mp4                           (local Shorts/Reels/TikTok stand-ins)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

MEDIA_DIR = Path(__file__).parent / "media"
REF_FILE = MEDIA_DIR / "references" / "ref_hippolyte_outlier.mp4"
RAW_FILE = MEDIA_DIR / "raw" / "raw_founder_take.mp4"
REELS_DIR = MEDIA_DIR / "reels"

# Local stand-ins for YouTube Shorts / TikTok / Instagram Reels (offline embeds).
DEMO_REELS = [
    {
        "filename": "reel_street_mic.mp4",
        "label": "STREET MIC",
        "color": "0x0f766e",
        "accent": "0x34d399",
        "duration": 6,
        "lively": True,
    },
    {
        "filename": "reel_ai_agent.mp4",
        "label": "AI AGENT",
        "color": "0x1e3a5f",
        "accent": "0x60a5fa",
        "duration": 6,
        "lively": True,
    },
    {
        "filename": "reel_whiteboard.mp4",
        "label": "WHITEBOARD",
        "color": "0x3b0764",
        "accent": "0xc084fc",
        "duration": 6,
        "lively": True,
    },
    {
        "filename": "reel_salary.mp4",
        "label": "SALARY CARD",
        "color": "0x422006",
        "accent": "0xfbbf24",
        "duration": 5,
        "lively": True,
    },
    {
        "filename": "reel_terminal.mp4",
        "label": "TERMINAL",
        "color": "0x052e16",
        "accent": "0x4ade80",
        "duration": 6,
        "lively": True,
    },
    {
        "filename": "reel_podcast.mp4",
        "label": "PODCAST",
        "color": "0x1c1917",
        "accent": "0xa8a29e",
        "duration": 7,
        "lively": False,
    },
]


def _run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {(res.stderr or res.stdout)[-500:]}")


def _make_reel(spec: dict) -> Path:
    out = REELS_DIR / spec["filename"]
    if out.exists() and out.stat().st_size > 8_000:
        return out

    dur = float(spec["duration"])
    label = spec["label"].replace(":", "\\:")
    color = spec["color"]
    accent = spec["accent"]
    lively = bool(spec["lively"])

    _ = label
    if lively:
        video_src = f"testsrc2=size=720x1280:rate=30:duration={dur}"
        af = (
            f"aevalsrc='0.4*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*4.5*t))'"
            f":s=16000:d={dur}"
        )
    else:
        video_src = f"color=c={color}:size=720x1280:rate=30:duration={dur}"
        af = (
            f"aevalsrc='if(between(t,2.0,3.5),0.0001,"
            f"0.28*sin(2*PI*160*t)*(0.5+0.5*sin(2*PI*1.5*t)))':s=16000:d={dur}"
        )

    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            video_src,
            "-f",
            "lavfi",
            "-i",
            af,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
    )
    return out


def ensure_demo_reels(force: bool = False) -> list[Path]:
    REELS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for spec in DEMO_REELS:
        out = REELS_DIR / spec["filename"]
        if force and out.exists():
            out.unlink()
        paths.append(_make_reel(spec))
    return paths


def ensure_demo_videos(force: bool = False) -> None:
    (MEDIA_DIR / "references").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "conformed").mkdir(parents=True, exist_ok=True)

    if force or not REF_FILE.exists() or REF_FILE.stat().st_size < 10_000:
        parts = []
        colors = ["red", "blue", "green", "yellow", "magenta", "cyan", "orange", "violet"]
        tmp_dir = MEDIA_DIR / "references" / "_tmp_parts"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        for i, color in enumerate(colors):
            part = tmp_dir / f"p{i}.mp4"
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c={color}:size=720x1280:rate=30:duration=1.25,"
                    f"drawtext=text='RIG CUT {i+1}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                    "-f",
                    "lavfi",
                    "-i",
                    f"aevalsrc='0.45*sin(2*PI*{180+i*40}*t)*(0.55+0.45*sin(2*PI*5*t))':s=16000:d=1.25",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(part),
                ]
            )
            parts.append(part)

        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text("".join(f"file '{p.name}'\n" for p in parts))
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(REF_FILE),
            ]
        )
        for p in parts:
            p.unlink(missing_ok=True)
        concat_list.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except OSError:
            pass

    if force or not RAW_FILE.exists() or RAW_FILE.stat().st_size < 10_000:
        audio_expr = (
            "aevalsrc='if(between(t,2.5,4.6)+between(t,7.0,9.2), 0.0001, "
            "0.35*sin(2*PI*180*t)*(0.5+0.5*sin(2*PI*2*t)))':s=16000:d=12"
        )
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=0x181b24:size=720x1280:rate=30:duration=12,"
                "drawgrid=w=120:h=120:t=2:c=0x2e3446,"
                "drawtext=text='RAW TAKE':fontsize=42:fontcolor=0x8899aa:x=(w-text_w)/2:y=120",
                "-f",
                "lavfi",
                "-i",
                audio_expr,
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(RAW_FILE),
            ]
        )

    ensure_demo_reels(force=force)


if __name__ == "__main__":
    ensure_demo_videos(force=False)
    print(f"REF exists={REF_FILE.exists()} size={REF_FILE.stat().st_size if REF_FILE.exists() else 0}")
    print(f"RAW exists={RAW_FILE.exists()} size={RAW_FILE.stat().st_size if RAW_FILE.exists() else 0}")
    for p in sorted(REELS_DIR.glob("*.mp4")):
        print(f"REEL {p.name} size={p.stat().st_size}")
