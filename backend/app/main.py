from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .akshare_client import AKSHARE_IMPORT_ERROR, get_history, get_spot_snapshot, get_zt_pool
from .config import get_strategy_config
from .signal_engine import evaluate_technical_pattern, score_stock

app = FastAPI(
    title="AI A股策略雷达 AKShare API",
    version="0.1.0",
    description="MVP backend for A-share signal screening. Research only, not investment advice.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit:
        df = df.head(limit)
    return df.where(pd.notnull(df), None).to_dict(orient="records")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": AKSHARE_IMPORT_ERROR is None,
        "service": "a-stock-radar-akshare-api",
        "time": datetime.now().isoformat(timespec="seconds"),
        "akshare_import_error": repr(AKSHARE_IMPORT_ERROR) if AKSHARE_IMPORT_ERROR else None,
        "disclaimer": "研究原型，不构成投资建议；免费数据源无SLA，实盘前需复核。",
    }


@app.get("/api/market/snapshot")
def market_snapshot(limit: int = Query(50, ge=1, le=500), refresh: bool = False) -> dict[str, Any]:
    try:
        df = get_spot_snapshot(refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AKShare realtime snapshot failed: {exc}") from exc
    cols = [c for c in ["code", "name", "price", "pct_chg", "amount", "volume_ratio", "turnover_rate", "total_market_cap", "float_market_cap"] if c in df.columns]
    df = df[cols].sort_values("amount", ascending=False)
    return {"count": len(df), "items": _records(df, limit)}


@app.get("/api/stocks/{code}/history")
def stock_history(code: str, days: int = Query(280, ge=60, le=600)) -> dict[str, Any]:
    try:
        hist = get_history(code, days=days)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AKShare history failed for {code}: {exc}") from exc
    return {"code": code, "count": len(hist), "items": _records(hist)}


@app.get("/api/stocks/{code}/signal")
def stock_signal(code: str, days: int = Query(280, ge=80, le=600)) -> dict[str, Any]:
    cfg = get_strategy_config()
    try:
        hist = get_history(code, days=days)
        tech = evaluate_technical_pattern(code, hist, cfg)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Signal evaluation failed for {code}: {exc}") from exc
    return {"code": code, "technical": tech.to_dict()}


@app.get("/api/limit-up-pool")
def limit_up_pool(date: str | None = None, limit: int = Query(100, ge=1, le=500)) -> dict[str, Any]:
    try:
        df = get_zt_pool(date=date)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AKShare limit-up pool failed: {exc}") from exc
    return {"date": date or datetime.now().strftime("%Y%m%d"), "count": len(df), "items": _records(df, limit)}


@app.get("/api/candidates/today")
def candidates_today(
    limit: int = Query(30, ge=1, le=100),
    scan_limit: int = Query(120, ge=10, le=600),
    refresh: bool = False,
) -> dict[str, Any]:
    """Scan a liquid, small-float subset and evaluate the MVP technical pattern.

    This endpoint intentionally scans only a bounded subset for MVP responsiveness.
    For production, move the scan into a scheduled worker and persist results.
    """
    cfg = get_strategy_config()
    try:
        spot = get_spot_snapshot(refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AKShare snapshot failed: {exc}") from exc

    required = {"code", "name", "amount", "float_market_cap"}
    if not required.issubset(set(spot.columns)):
        raise HTTPException(status_code=500, detail=f"Spot data missing columns: {sorted(required - set(spot.columns))}")

    universe = spot.copy()
    universe = universe[~universe["name"].astype(str).str.upper().str.contains("ST", na=False)]
    universe = universe[~universe["name"].astype(str).str.contains("退", na=False)]
    # Eastmoney snapshot has float market cap; Sina fallback does not. When missing,
    # keep the endpoint usable but mark candidates with a risk flag later.
    has_float_cap = universe["float_market_cap"].notna().any() and (universe["float_market_cap"].fillna(0) > 0).any()
    if has_float_cap:
        universe = universe[(universe["float_market_cap"] > 0) & (universe["float_market_cap"] <= cfg.max_float_market_cap)]
    universe = universe[universe["amount"] >= cfg.min_amount]
    universe = universe.sort_values("amount", ascending=False).head(scan_limit)

    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for _, row in universe.iterrows():
        code = str(row["code"]).zfill(6)
        try:
            hist = get_history(code, days=cfg.history_days)
            tech = evaluate_technical_pattern(code, hist, cfg)
            scored = score_stock(row, tech, cfg)
            if scored["score"] >= 35 or tech.status in {"breakout_triggered", "watching_breakout", "breakout_without_volume"}:
                candidates.append(scored)
        except Exception as exc:
            if len(errors) < 10:
                errors.append({"code": code, "error": str(exc)[:180]})
            continue

    candidates.sort(key=lambda item: (item["technical"]["passed"], item["score"], item["amount"]), reverse=True)
    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "universe_scanned": len(universe),
        "count": len(candidates[:limit]),
        "items": candidates[:limit],
        "errors_sample": errors,
        "disclaimer": "MVP规则筛选结果，仅作研究线索；免费数据源和形态信号必须人工复核。",
    }


@app.get("/api/strategy/config")
def strategy_config() -> dict[str, Any]:
    return get_strategy_config().model_dump()
