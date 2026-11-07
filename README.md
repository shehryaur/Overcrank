# OVERCRANK

Broadcast frame-telemetry, format arbitrage, and automated timeline conforming.

## Stack

- **Oriane API** — visual rig indexing (optional; fixtures always work)
- **GMI / Anthropic / Lovable** — optional keys in `backend/.env`
- **FastAPI** — OpenCV + PySceneDetect + auto-editor + FFmpeg
- **React** — minimal Search → Reels → Align → Conform studio
- **Compound.mov** — FastMCP tools + EDL runbook (Cursor bridge)

## Crowd demo (offline-safe)

```bash
make install
make demo          # generate local reels + warm conform
make backend       # :8000
make frontend      # :5173
```

Open `http://127.0.0.1:5173`. With `DEMO_MODE=1` (default), topic search and reels use local MP4s — no internet required.

Suggested demo path: **AI founders** → pick a reel → Continue → Conform → Copy runbook.

## Keys (env only)

```bash
cp backend/.env.example backend/.env
# paste keys, keep DEMO_MODE=1 for crowd demos
```

| Variable | Required | Purpose |
|---|---|---|
| `DEMO_MODE` | No | `1` = fixtures only (crowd default) |
| `GMI_API_KEY` | No | GMI Cloud inference |
| `LOVABLE_API_KEY` | No | Lovable workspace API (`lov_` keys from Business+) |
| `COMPOUND_API_KEY` | No | Optional; EDL/MCP work without it |
| `ANTHROPIC_API_KEY` | No | Optional Compound prompt polish |
| `ORIANE_API_KEY` | No | Live Oriane search when `DEMO_MODE=0` |
| `YOUTUBE_API_KEY` | No | Live Shorts search when `DEMO_MODE=0` |

Lovable keys: Workspace settings → API keys & OAuth → Workspace access tokens ([docs](https://docs.lovable.dev/features/api-keys)). Not required for the Overcrank demo.

## Cursor ↔ Compound.mov MCP

Project config is in `.cursor/mcp.json`. Reload MCP in Cursor Settings → MCP. Tools:

- `scan_format_yield_matrix`
- `discover_topic_shortform`
- `audit_raw_take_telemetry`
- `compare_rig_alignment`
- `conform_footage_and_export_compound_edl`

## API smoke

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/topic/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"AI founders"}'
curl -X POST http://localhost:8000/api/telemetry/compare \
  -H 'Content-Type: application/json' \
  -d '{"cohort_id":"sf_founder_interviews","rig_id":"rig_street_broll_punch"}'
curl -X POST http://localhost:8000/api/conform/execute \
  -H 'Content-Type: application/json' \
  -d '{"cohort_id":"sf_founder_interviews","rig_id":"rig_street_broll_punch"}'
```
