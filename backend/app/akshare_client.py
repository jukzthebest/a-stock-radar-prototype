from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

import pandas as pd

try:
    import akshare as ak
except Exception as exc:  # pragma: no cover
    ak = None
    AKSHARE_IMPORT_ERROR = exc
else:
    AKSHARE_IMPORT_ERROR = None


def require_akshare():
    if ak is None:
        raise RuntimeError(f"AKShare import failed: {AKSHARE_IMPORT_ERROR!r}")
    return ak


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def normalize_spot(df: pd.DataFrame) -> pd.DataFrame:
    rename = {
        "代码": "code", "名称": "name", "最新价": "price", "涨跌幅": "pct_chg",
        "成交量": "volume", "成交额": "amount", "量比": "volume_ratio", "换手率": "turnover_rate",
        "总市值": "total_market_cap", "流通市值": "float_market_cap", "最高": "high", "最低": "low",
        "今开": "open", "昨收": "pre_close", "所属行业": "industry",
    }
    out = df.rename(columns=rename).copy()
    for col in ["price", "pct_chg", "volume", "amount", "volume_ratio", "turnover_rate", "total_market_cap", "float_market_cap", "high", "low", "open", "pre_close"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    if "code" in out.columns:
        # AKShare Sina fallback returns codes like sh600000 / sz000001 / bj920001.
        out["code"] = out["code"].astype(str).str.extract(r"(\d{6})", expand=False).fillna(out["code"].astype(str)).str.zfill(6)
    for optional in ["volume_ratio", "turnover_rate", "total_market_cap", "float_market_cap", "industry"]:
        if optional not in out.columns:
            out[optional] = None
    return out


@lru_cache(maxsize=1)
def get_spot_snapshot_cached() -> pd.DataFrame:
    ak_mod = require_akshare()
    try:
        df = ak_mod.stock_zh_a_spot_em()
        out = normalize_spot(df)
        out["source"] = "eastmoney"
        return out
    except Exception as em_exc:
        # Fallback is slower and lacks market-cap/turnover fields, but keeps the MVP usable
        # when Eastmoney pages/proxies fail.
        df = ak_mod.stock_zh_a_spot()
        out = normalize_spot(df)
        out["source"] = f"sina_fallback_after_em_error: {type(em_exc).__name__}"
        return out


def get_spot_snapshot(refresh: bool = False) -> pd.DataFrame:
    if refresh:
        get_spot_snapshot_cached.cache_clear()
    return get_spot_snapshot_cached().copy()


def get_history(symbol: str, days: int = 280) -> pd.DataFrame:
    ak_mod = require_akshare()
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=max(days * 2, 420))).strftime("%Y%m%d")
    try:
        df = ak_mod.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start, end_date=end, adjust="qfq")
        rename = {
            "日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
            "成交量": "volume", "成交额": "amount", "振幅": "amplitude", "涨跌幅": "pct_chg",
            "涨跌额": "change", "换手率": "turnover_rate",
        }
        out = df.rename(columns=rename).copy()
    except Exception:
        # Sina fallback avoids Eastmoney history failures in some network/proxy environments.
        prefix = "sh" if symbol.startswith(("6", "9")) else "bj" if symbol.startswith(("4", "8")) else "sz"
        df = ak_mod.stock_zh_a_daily(symbol=f"{prefix}{symbol}", start_date=start, end_date=end, adjust="qfq")
        out = df.rename(columns={"turnover": "turnover_rate"}).copy()
        out["pct_chg"] = out["close"].pct_change() * 100
        out["change"] = out["close"].diff()
        out["amplitude"] = (out["high"] - out["low"]) / out["close"].shift(1) * 100
        if "turnover_rate" in out.columns:
            out["turnover_rate"] = out["turnover_rate"] * 100
    if "date" in out.columns:
        out["date"] = out["date"].astype(str)
    for col in ["open", "close", "high", "low", "volume", "amount", "amplitude", "pct_chg", "change", "turnover_rate"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.dropna(subset=["close"]).tail(days).reset_index(drop=True)


def get_zt_pool(date: str | None = None) -> pd.DataFrame:
    ak_mod = require_akshare()
    date = date or datetime.now().strftime("%Y%m%d")
    df = ak_mod.stock_zt_pool_em(date=date)
    return normalize_spot(df)
