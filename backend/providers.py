"""Soft-fail provider probes. Never raise — demo stays online if a key/API fails."""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx


def _flag(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "1").strip().lower() in {"1", "true", "yes", "on"}


async def probe_providers() -> Dict[str, Any]:
    """Return non-secret status for each configured provider."""
    out: Dict[str, Any] = {
        "gmi": {"configured": _flag("GMI_API_KEY"), "ok": False, "detail": "skipped"},
        "anthropic": {"configured": _flag("ANTHROPIC_API_KEY"), "ok": False, "detail": "skipped"},
        "lovable": {"configured": _flag("LOVABLE_API_KEY"), "ok": False, "detail": "skipped"},
        "oriane": {"configured": _flag("ORIANE_API_KEY"), "ok": False, "detail": "skipped"},
        "youtube": {"configured": _flag("YOUTUBE_API_KEY"), "ok": False, "detail": "skipped"},
        "compound": {
            "configured": _flag("COMPOUND_API_KEY"),
            "ok": True,
            "detail": "local EDL + MCP bridge (API key optional)",
        },
    }

    if demo_mode():
        for k in ("gmi", "anthropic", "lovable", "oriane", "youtube"):
            if out[k]["configured"]:
                out[k]["detail"] = "configured · DEMO_MODE uses fixtures"
            else:
                out[k]["detail"] = "empty · fixtures active"
        return out

    timeout = httpx.Timeout(6.0)

    # GMI
    if out["gmi"]["configured"]:
        try:
            base = os.getenv("GMI_BASE_URL", "https://api.gmi-serving.com/v1").rstrip("/")
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    f"{base}/models",
                    headers={"Authorization": f"Bearer {os.environ['GMI_API_KEY']}"},
                )
            out["gmi"]["ok"] = r.status_code == 200
            out["gmi"]["detail"] = f"HTTP {r.status_code}"
        except Exception as exc:
            out["gmi"]["detail"] = f"unreachable ({type(exc).__name__})"

    # Anthropic
    if out["anthropic"]["configured"]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                        "anthropic-version": "2023-06-01",
                    },
                )
            out["anthropic"]["ok"] = r.status_code == 200
            out["anthropic"]["detail"] = f"HTTP {r.status_code}"
        except Exception as exc:
            out["anthropic"]["detail"] = f"unreachable ({type(exc).__name__})"

    # Lovable
    if out["lovable"]["configured"]:
        try:
            base = os.getenv("LOVABLE_BASE_URL", "https://api.lovable.dev").rstrip("/")
            ver = os.getenv("LOVABLE_API_VERSION", "2026-09-11")
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    f"{base}/v1/workspaces",
                    headers={
                        "Lovable-API-Key": os.environ["LOVABLE_API_KEY"],
                        "Lovable-Version": ver,
                        "Accept": "application/json",
                    },
                )
            out["lovable"]["ok"] = r.status_code == 200
            out["lovable"]["detail"] = f"HTTP {r.status_code}"
        except Exception as exc:
            out["lovable"]["detail"] = f"unreachable ({type(exc).__name__})"

    # Oriane
    if out["oriane"]["configured"]:
        try:
            base = os.getenv("ORIANE_BASE_URL", "https://connect.oriane.xyz").rstrip("/")
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.get(
                    base,
                    headers={"Authorization": f"Bearer {os.environ['ORIANE_API_KEY']}"},
                )
            out["oriane"]["ok"] = r.status_code < 500
            out["oriane"]["detail"] = f"HTTP {r.status_code}"
        except Exception as exc:
            out["oriane"]["detail"] = f"unreachable ({type(exc).__name__})"

    # YouTube
    if out["youtube"]["configured"]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": "shorts",
                        "type": "video",
                        "maxResults": 1,
                        "key": os.environ["YOUTUBE_API_KEY"],
                    },
                )
            out["youtube"]["ok"] = r.status_code == 200
            out["youtube"]["detail"] = f"HTTP {r.status_code}"
        except Exception as exc:
            out["youtube"]["detail"] = f"unreachable ({type(exc).__name__})"

    return out


async def polish_compound_prompt(prompt: str, rig_title: str) -> str:
    """Optionally tighten the Compound runbook with Anthropic. Falls back to original."""
    if demo_mode() or not _flag("ANTHROPIC_API_KEY"):
        return prompt
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-5",
                    "max_tokens": 700,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Tighten this Compound.mov agent runbook. Keep every number and "
                                f"timestamp. Title context: {rig_title}. Return markdown only.\n\n"
                                f"{prompt}"
                            ),
                        }
                    ],
                },
            )
        if r.status_code != 200:
            return prompt
        data = r.json()
        parts = data.get("content") or []
        text = "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
        return text or prompt
    except Exception:
        return prompt
