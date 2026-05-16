from __future__ import annotations

from functools import lru_cache
from pydantic import BaseModel


class StrategyConfig(BaseModel):
    max_float_market_cap: float = 30_000_000_000  # 300 亿元
    min_amount: float = 50_000_000               # 5000 万成交额
    bottom_position_threshold: float = 0.35
    limit_up_lookback: int = 15
    limit_up_pct_main: float = 9.8
    limit_up_pct_chinext: float = 19.5
    limit_up_volume_multiple: float = 2.0
    consolidation_min_days: int = 3
    consolidation_max_days: int = 5
    consolidation_max_drawdown: float = 0.12
    breakout_lookback: int = 60
    breakout_buffer: float = 0.01
    breakout_volume_multiple: float = 2.0
    history_days: int = 280

    policy_themes: tuple[str, ...] = (
        "人工智能", "AI", "算力", "半导体", "国产替代", "机器人", "低空经济",
        "商业航天", "新能源汽车", "固态电池", "储能", "光伏", "风电",
        "创新药", "医疗器械", "军工", "网络安全", "数据要素", "工业母机",
        "新材料", "稀土", "核电",
    )


@lru_cache(maxsize=1)
def get_strategy_config() -> StrategyConfig:
    return StrategyConfig()
