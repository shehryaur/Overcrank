"""One-shot crowd-demo prep: media + warm conform so the first click is fast."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from conform_engine import conform_video_to_rig
from generate_demo_media import MEDIA_DIR, RAW_FILE, REF_FILE, REELS_DIR, ensure_demo_videos
from oriane_client import OrianeClient
from telemetry_engine import extract_video_telemetry


def main() -> None:
    print("== Overcrank demo prep ==")
    ensure_demo_videos(force=False)
    print(f"  ref: {REF_FILE} ({REF_FILE.stat().st_size} bytes)")
    print(f"  raw: {RAW_FILE} ({RAW_FILE.stat().st_size} bytes)")
    reels = sorted(REELS_DIR.glob("*.mp4"))
    print(f"  reels: {len(reels)}")
    for p in reels:
        print(f"    - {p.name} ({p.stat().st_size})")

    oriane = OrianeClient()
    # sync call into async client helper via fixture path
    import asyncio

    matrix = asyncio.run(oriane.get_yield_matrix("sf_founder_interviews"))
    rig = matrix["rigs"][0]
    ref_tel = extract_video_telemetry(str(REF_FILE))
    print("  warming conform…")
    result = conform_video_to_rig(str(RAW_FILE), ref_tel, rig)
    out = MEDIA_DIR / "conformed" / result["conformed_filename"]
    print(f"  conformed: {out} ({out.stat().st_size if out.exists() else 0} bytes)")
    print("Demo ready. Start with: make backend && make frontend")


if __name__ == "__main__":
    main()
