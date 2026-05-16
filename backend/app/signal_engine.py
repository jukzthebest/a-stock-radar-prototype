from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import numpy as np
import pandas as pd

from .config import StrategyConfig


@dataclass
class TechnicalSignal:
    passed: bool
    score: int
    status: str
    reasons: list[str]
    bottom_position: float | None = None
    limit_up_date: str | None = None
    consolidation_days: int | None = None
    resistance: float | None = None
    breakout_price: float | None = None
    stop_loss: float | None = None
    first_take_profit: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def board_limit_pct(code: str, cfg: StrategyConfig) -> float:
    if code.startswith(("300", "301", "688")):
        return cfg.limit_up_pct_chinext
    if code.startswith(("8", "4", "920")):
        return 29.0
    return cfg.limit_up_pct_main


def _latest_float(series: pd.Series) -> float | None:
    if series.empty:
        return None
    value = series.iloc[-1]
    if pd.isna(value):
        return None
    return float(value)


def evaluate_technical_pattern(code: str, hist: pd.DataFrame, cfg: StrategyConfig) -> TechnicalSignal:
    reasons: list[str] = []
    if hist is None or len(hist) < 80:
        return TechnicalSignal(False, 0, "history_insufficient", ["历史K线不足，无法计算形态"])

    hist = hist.copy().reset_index(drop=True)
    close = _latest_float(hist["close"])
    if close is None:
        return TechnicalSignal(False, 0, "invalid_history", ["最新收盘价缺失"])

    lookback = min(len(hist), 250)
    low_250 = float(hist["low"].tail(lookback).min())
    high_250 = float(hist["high"].tail(lookback).max())
    bottom_position = None if high_250 <= low_250 else (close - low_250) / (high_250 - low_250)
    score = 0

    if bottom_position is not None and bottom_position <= cfg.bottom_position_threshold:
        score += 15
        reasons.append(f"近一年价格位置 {bottom_position:.1%}，处于底部区域")
    else:
        return TechnicalSignal(False, score, "not_bottom", reasons or ["不在近一年底部区域"], bottom_position=bottom_position)

    hist["avg_vol20"] = hist["volume"].rolling(20).mean()
    recent = hist.tail(cfg.limit_up_lookback).copy()
    limit_pct = board_limit_pct(code, cfg)
    limit_up_mask = (recent["pct_chg"] >= limit_pct) & (recent["volume"] >= recent["avg_vol20"] * cfg.limit_up_volume_multiple)
    if not limit_up_mask.any():
        return TechnicalSignal(False, score, "no_volume_limit_up", reasons + ["近15日未出现放量涨停"] , bottom_position=bottom_position)

    limit_idx = int(limit_up_mask[limit_up_mask].index[-1])
    limit_row = hist.loc[limit_idx]
    limit_date = str(limit_row["date"])
    limit_close = float(limit_row["close"])
    limit_volume = float(limit_row["volume"])
    score += 15
    reasons.append(f"{limit_date} 出现放量涨停")

    days_after = len(hist) - limit_idx - 1
    if cfg.consolidation_min_days <= days_after <= cfg.consolidation_max_days:
        after = hist.iloc[limit_idx + 1:]
        min_close = float(after["close"].min()) if not after.empty else limit_close
        max_close = float(after["close"].max()) if not after.empty else limit_close
        avg_after_volume = float(after["volume"].mean()) if not after.empty else limit_volume
        drawdown_ok = min_close >= limit_close * (1 - cfg.consolidation_max_drawdown)
        range_ok = max_close <= limit_close * 1.12
        volume_ok = avg_after_volume <= limit_volume * 1.2
        if drawdown_ok and range_ok:
            score += 15
            reasons.append(f"涨停后高位整理 {days_after} 日，未明显破位")
            if volume_ok:
                score += 5
                reasons.append("整理期量能可接受")
        else:
            return TechnicalSignal(False, score, "consolidation_failed", reasons + ["涨停后整理区间破坏"], bottom_position=bottom_position, limit_up_date=limit_date, consolidation_days=days_after)
    else:
        return TechnicalSignal(False, score, "waiting_consolidation", reasons + [f"涨停后已过 {days_after} 日，未处于3-5日整理窗口"], bottom_position=bottom_position, limit_up_date=limit_date, consolidation_days=days_after)

    resistance_slice = hist.iloc[max(0, len(hist) - cfg.breakout_lookback - 1):-1]
    resistance = float(resistance_slice["high"].max()) if not resistance_slice.empty else float(hist["high"].iloc[:-1].max())
    latest = hist.iloc[-1]
    avg_vol5 = float(hist["volume"].rolling(5).mean().iloc[-1])
    breakout = float(latest["close"]) > resistance * (1 + cfg.breakout_buffer)
    volume_break = avg_vol5 > 0 and float(latest["volume"]) >= avg_vol5 * cfg.breakout_volume_multiple

    breakout_price = resistance * (1 + cfg.breakout_buffer)
    stop_loss = max(resistance * 0.95, float(hist.iloc[limit_idx:]["low"].min()) * 0.97)
    first_take_profit = breakout_price * 1.16

    if breakout and volume_break:
        score += 25
        reasons.append("已放量突破前期阻力位")
        return TechnicalSignal(True, score, "breakout_triggered", reasons, bottom_position, limit_date, days_after, resistance, breakout_price, stop_loss, first_take_profit)

    if breakout:
        score += 10
        reasons.append("价格突破但量能未达到倍量标准")
        return TechnicalSignal(False, score, "breakout_without_volume", reasons, bottom_position, limit_date, days_after, resistance, breakout_price, stop_loss, first_take_profit)

    return TechnicalSignal(False, score, "watching_breakout", reasons + ["仍在等待放量突破"], bottom_position, limit_date, days_after, resistance, breakout_price, stop_loss, first_take_profit)


def score_stock(row: pd.Series, tech: TechnicalSignal, cfg: StrategyConfig) -> dict[str, Any]:
    name = str(row.get("name", ""))
    industry = str(row.get("industry", ""))
    risk_flags = []
    if "ST" in name.upper() or "退" in name:
        risk_flags.append("ST/退市风险名称")
    amount = float(row.get("amount") or 0)
    if amount < cfg.min_amount:
        risk_flags.append("成交额不足")
    float_cap_raw = row.get("float_market_cap")
    float_cap = float(float_cap_raw) if float_cap_raw is not None and not pd.isna(float_cap_raw) else 0.0
    if float_cap <= 0:
        risk_flags.append("流通市值缺失：当前行情源无法校验300亿条件")
    elif float_cap > cfg.max_float_market_cap:
        risk_flags.append("流通市值超过300亿")

    theme_hit = any(theme.lower() in (industry + name).lower() for theme in cfg.policy_themes)
    total = tech.score + (15 if theme_hit else 0) + (10 if amount >= cfg.min_amount else 0)
    return {
        "code": str(row.get("code", "")).zfill(6),
        "name": name,
        "industry": industry if industry != "nan" else "",
        "price": float(row.get("price") or 0),
        "pct_chg": float(row.get("pct_chg") or 0),
        "amount": amount,
        "volume_ratio": float(row.get("volume_ratio") or 0),
        "turnover_rate": float(row.get("turnover_rate") or 0),
        "float_market_cap": float_cap,
        "theme_hit": theme_hit,
        "score": total,
        "risk_flags": risk_flags,
        "technical": tech.to_dict(),
    }
