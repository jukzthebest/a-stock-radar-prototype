# AKShare Backend

FastAPI backend for the AI A股策略雷达 MVP.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /api/health`
- `GET /api/market/snapshot?limit=50&refresh=true`
- `GET /api/stocks/{code}/history?days=280`
- `GET /api/stocks/{code}/signal`
- `GET /api/limit-up-pool`
- `GET /api/candidates/today?scan_limit=120&limit=30`
- `GET /api/strategy/config`

## Notes

- This is a research MVP, not trading advice.
- AKShare is a free public-data aggregation library with no SLA.
- `candidates/today` intentionally scans a bounded subset for latency. Production should persist scheduled scans.
