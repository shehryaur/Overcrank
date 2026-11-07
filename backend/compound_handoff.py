"""Package an Overcrank conform into a Compound.mov project + zip for download.

Compound does not auto-ingest a folder when you only launch the app. The reliable
handoff is: zip (video + BRIEF + index.tsx) → user adds that folder in Compound
→ paste the agent line (copied for them).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

HANDOFF_ROOT = Path(__file__).parent / "media" / "compound_handoffs"


def _compound_app_name() -> str:
    override = os.getenv("COMPOUND_APP_NAME", "").strip()
    if override:
        return override
    for name in ("Compound Beta", "Compound"):
        if Path(f"/Applications/{name}.app").exists():
            return name
    return "Compound Beta"


def _index_tsx(video_rel: str, title: str) -> str:
    safe_title = title.replace("`", "'").replace('"', "'")[:80]
    return f"""/* Overcrank → Compound project
 * Drop this whole folder into Compound (New project / Open folder).
 * Then paste the line from START_HERE.txt into Compound chat.
 */
export default function OvercrankHandoff() {{
  return (
    <stage>
      <scene name="{safe_title}" width={{1080}} height={{1920}} fill="black" active>
        <sequence name="A-roll" main>
          <video
            id="take"
            src="{video_rel}"
            width={{1080}}
            height={{1920}}
            volume={{0}}
          />
        </sequence>
      </scene>
    </stage>
  );
}}
"""


def _start_here(display_name: str, video_name: str, agent_line: str) -> str:
    return (
        f"OVERCRANK → COMPOUND PACK\n"
        f"========================\n\n"
        f"Project: {display_name}\n"
        f"Video:   {video_name}\n\n"
        f"What to do (30 seconds):\n"
        f"1. Unzip this pack if you downloaded the .zip\n"
        f"2. In Compound: New project → Open / add this folder\n"
        f"   (or drag the folder onto Compound)\n"
        f"3. Paste this into Compound chat and send:\n\n"
        f"   {agent_line}\n\n"
        f"Files inside:\n"
        f"  - {video_name}     your conformed take\n"
        f"  - BRIEF.md         full edit rules\n"
        f"  - index.tsx        starter Compound timeline\n"
        f"  - package.json     project name\n"
    )


def package_compound_project(
    *,
    video_path: Path,
    compound_prompt: str,
    compound_edl: Optional[Dict[str, Any]] = None,
    rig_title: str = "Overcrank outlier",
) -> Dict[str, Any]:
    if not video_path.exists():
        raise FileNotFoundError(f"Video missing: {video_path}")

    HANDOFF_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    folder_name = f"overcrank_{stamp}"
    project_dir = HANDOFF_ROOT / folder_name
    project_dir.mkdir(parents=True, exist_ok=False)

    dest_video = project_dir / video_path.name
    shutil.copy2(video_path, dest_video)

    display_name = f"Overcrank · {rig_title}"[:60]
    agent_line = (
        "Read BRIEF.md in this project and apply every rule to the take on the timeline. "
        "Export a vertical 1080x1920 short when done."
    )

    brief = (
        f"# Overcrank → Compound brief\n\n"
        f"You are editing **{display_name}** inside Compound.mov.\n"
        f"Source clip: `{dest_video.name}` (on the main sequence in `index.tsx`).\n\n"
        f"{compound_prompt.strip()}\n\n"
        f"When finished, export a vertical 1080×1920 short ready to post.\n"
    )
    (project_dir / "BRIEF.md").write_text(brief)
    (project_dir / "START_HERE.txt").write_text(
        _start_here(display_name, dest_video.name, agent_line)
    )
    (project_dir / "index.tsx").write_text(_index_tsx(dest_video.name, rig_title))
    if compound_edl:
        (project_dir / "overcrank_edl.json").write_text(json.dumps(compound_edl, indent=2))

    package = {
        "name": f"overcrank-{stamp}",
        "displayName": display_name,
        "main": "index.tsx",
        "private": True,
    }
    (project_dir / "package.json").write_text(json.dumps(package, indent=2))

    zip_path = HANDOFF_ROOT / f"{folder_name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in project_dir.rglob("*"):
            if path.is_file():
                zf.write(path, arcname=str(Path(folder_name) / path.relative_to(project_dir)))

    return {
        "project_dir": str(project_dir.resolve()),
        "zip_path": str(zip_path.resolve()),
        "zip_url": f"/media/compound_handoffs/{zip_path.name}",
        "folder_url": f"/media/compound_handoffs/{folder_name}/",
        "video_filename": dest_video.name,
        "brief_path": str((project_dir / "BRIEF.md").resolve()),
        "display_name": display_name,
        "agent_line": agent_line,
        "agent_prompt": brief,
    }


def reveal_and_assist(project_dir: str, agent_line: str, launch_app: bool = True) -> Dict[str, Any]:
    """Reveal folder in Finder, copy agent line, optionally open Compound."""
    path = Path(project_dir)
    if not path.is_dir():
        raise FileNotFoundError(project_dir)

    meta: Dict[str, Any] = {"project_dir": str(path), "finder": False, "clipboard": False, "app": None}

    # Finder reveal — most reliable “here’s the folder” signal on macOS
    finder = subprocess.run(["open", "-R", str(path)], capture_output=True, text=True)
    meta["finder"] = finder.returncode == 0

    # Copy paste-ready Compound chat line
    try:
        proc = subprocess.run(["pbcopy"], input=agent_line, text=True, capture_output=True)
        meta["clipboard"] = proc.returncode == 0
    except Exception:
        meta["clipboard"] = False

    if launch_app:
        app = _compound_app_name()
        launched = subprocess.run(["open", "-a", app], capture_output=True, text=True)
        meta["app"] = app
        meta["app_ok"] = launched.returncode == 0
    return meta
