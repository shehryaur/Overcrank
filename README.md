# OVERCRANK

Broadcast frame-telemetry, format arbitrage, and automated timeline conforming engine.

## Stack

- **Oriane API** — visual rig indexing (live key optional; fixtures always work)
- **GMI Cloud style backend** — FastAPI + OpenCV + PySceneDetect + auto-editor + FFmpeg
- **Lovable/React** — Vite + Tailwind + Recharts broadcast studio UI
- **Compound.mov** — FastMCP bridge + EDL runbook drawer

## Quick start

```bash
make media          # synthesize demo MP4s via ffmpeg
make backend        # FastAPI on :8000
make frontend       # Vite on :5173
```

## Secrets (paste after demo)

```bash
cp backend/.env.example backend/.env
# edit backend/.env — set ORIANE_API_KEY, keep ORIANE_BASE_URL=https://connect.oriane.xyz
# restart: make backend
```

| Variable | Required | Purpose |
|---|---|---|
| `ORIANE_API_KEY` | No | Bearer token for live Oriane search (`connect.oriane.xyz`). Fixtures work without it. |
| `ORIANE_BASE_URL` | No | Default `https://connect.oriane.xyz` (harvested real base). |
| `ORIANE_CACHE_TTL_HOURS` | No | Disk/memory cache TTL for Oriane HTTP (default 24). |

Studio also has a **Secrets** panel (header) that shows which keys are set — never paste secrets into chat.

## API smoke

```bash
curl http://localhost:8000/api/health
curl 'http://localhost:8000/api/yield-matrix?cohort_id=sf_founder_interviews'
curl -X POST http://localhost:8000/api/telemetry/compare \
  -H 'Content-Type: application/json' \
  -d '{"cohort_id":"sf_founder_interviews","rig_id":"rig_street_broll_punch"}'
curl -X POST http://localhost:8000/api/conform/execute \
  -H 'Content-Type: application/json' \
  -d '{"cohort_id":"sf_founder_interviews","rig_id":"rig_street_broll_punch"}'
```
