"""Reads provider API keys from the environment. Never returns secret values."""

from __future__ import annotations

import os
from typing import Any, Dict, List

PROVIDERS: List[Dict[str, Any]] = [
    {
        "name": "GMI_API_KEY",
        "purpose": "GMI Cloud inference. Sent as Authorization: Bearer.",
    },
    {
        "name": "LOVABLE_API_KEY",
        "purpose": "Lovable workspace API. Sent as Lovable-API-Key.",
    },
    {
        "name": "COMPOUND_API_KEY",
        "purpose": "Compound.mov token, if issued. The local EDL runbook works without it.",
    },
    {
        "name": "ANTHROPIC_API_KEY",
        "purpose": "Anthropic API. Sent as x-api-key.",
    },
    {
        "name": "ORIANE_API_KEY",
        "purpose": "Live Oriane visual search. The yield matrix uses fixtures when this is blank.",
    },
    {
        "name": "YOUTUBE_API_KEY",
        "purpose": "YouTube Data API for live Shorts search. Catalog fixtures work without it.",
    },
]


def _set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def provider_flags() -> Dict[str, str]:
    return {item["name"]: "set" if _set(item["name"]) else "missing" for item in PROVIDERS}


def secrets_catalog() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in PROVIDERS:
        rows.append(
            {
                "name": item["name"],
                "required": False,
                "set": _set(item["name"]),
                "purpose": item["purpose"],
            }
        )
    rows.extend(
        [
            {
                "name": "GMI_BASE_URL",
                "required": False,
                "set": True,
                "value": os.getenv("GMI_BASE_URL", "https://api.gmi-serving.com/v1"),
                "purpose": "GMI Cloud inference base.",
            },
            {
                "name": "LOVABLE_BASE_URL",
                "required": False,
                "set": True,
                "value": os.getenv("LOVABLE_BASE_URL", "https://api.lovable.dev"),
                "purpose": "Lovable API base.",
            },
            {
                "name": "ANTHROPIC_BASE_URL",
                "required": False,
                "set": True,
                "value": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                "purpose": "Anthropic API base.",
            },
            {
                "name": "ORIANE_BASE_URL",
                "required": False,
                "set": True,
                "value": os.getenv("ORIANE_BASE_URL", "https://connect.oriane.xyz"),
                "purpose": "Oriane REST base.",
            },
        ]
    )
    return rows
