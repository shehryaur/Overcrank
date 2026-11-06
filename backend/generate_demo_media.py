"""Synthesize visually distinct 9:16 demo MP4s with hard scene cuts + dead-air gaps.

Reference outlier: hard color cuts every ~1.2s + lively audio (no dead air).
Raw founder take: mostly static framing + two multi-second silent hazard windows.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

MEDIA_DIR = Path(__file__).parent / "media"
REF_FILE = MEDIA_DIR / "references" / "ref_hippolyte_outlier.mp4"
RAW_FILE = MEDIA_DIR / "raw" / "raw_founder_take.mp4"


def _run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {res.stderr[-500:]}")


def ensure_demo_videos(force: bool = False) -> None:
    (MEDIA_DIR / "references").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / "conformed").mkdir(parents=True, exist_ok=True)

    if force or not REF_FILE.exists() or REF_FILE.stat().st_size < 10_000:
        # Build 8 hard-cut segments (~1.25s each) so ContentDetector finds real splices.
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


if __name__ == "__main__":
    ensure_demo_videos(force=False)
    print(f"REF exists={REF_FILE.exists()} size={REF_FILE.stat().st_size if REF_FILE.exists() else 0}")
    print(f"RAW exists={RAW_FILE.exists()} size={RAW_FILE.stat().st_size if RAW_FILE.exists() else 0}")
