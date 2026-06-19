#!/usr/bin/env python
"""
时序选股验证 — 多因子版本

因子:
  1. 动量 (6个月涨幅)
  2. 波动率 (60日年化波动率, 越低越好)
  3. 趋势质量 (60日内收盘>MA20的天数占比)
  4. MA偏离度 (收盘距MA60的%, 偏离太远扣分)

用法:
    .venv/Scripts/python.exe scripts/timeline_screen.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime
from src.data.fetcher import fetch_daily_kline
from src.data.cleaner import clean_kline_data
from src.backtest.engine import BacktestEngine
from src.strategy.ma_crossover import MACrossoverBT

SPLIT_DATES = ["2025-01-01", "2025-07-01", "2026-01-01"]
TRAIN_YEARS = 3
TOP_N = 8
CASH = 100_000

# 因子权重
W_MOMENTUM = 0.35
W_VOLATILITY = 0.20
W_TREND_QUALITY = 0.30
W_MA_DEVIATION = 0.15


def get_universe():
    df = ak.index_stock_cons_sina(symbol="000300")
    df["symbol"] = df["code"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    return df[["symbol", "name"]]


def classify_industry(symbol, name):
    n = str(name)
    if "银行" in n: return "银行"
    if "保险" in n: return "保险"
    if "证券" in n: return "券商"
    if "酒" in n: return "白酒"
    if "药" in n or "医" in n: return "医药"
    if "锂" in n or "电池" in n or "光伏" in n: return "新能源"
    if "汽车" in n: return "汽车"
    if "半导体" in n or "电子" in n: return "半导体"
    if "软件" in n or "数据" in n: return "软件"
    if "电力" in n or "核电" in n: return "电力"
    if "家电" in n: return "家电"
    if "食品" in n or "饮料" in n: return "食品"
    return "其他"


def compute_factors(symbol, split_date):
    """
    只用 split_date 之前的数据计算 4 个因子
    """
    train_end = pd.Timestamp(split_date)
    train_start = train_end - pd.DateOffset(years=TRAIN_YEARS)

    try:
        raw = fetch_daily_kline(
            symbol,
            train_start.strftime("%Y-%m-%d"),
            train_end.strftime("%Y-%m-%d"),
            adjust="qfq",
        )
        if raw.empty or len(raw) < 120:
            return None

        clean = clean_kline_data(raw, symbol)
        close = clean["close"]
        returns = close.pct_change().dropna()

        if len(returns) < 60:
            return None

        # 1. 动量: 6个月涨幅
        n_mom = min(120, len(close) - 1)
        momentum = (close.iloc[-1] - close.iloc[-n_mom]) / close.iloc[-n_mom]

        # 2. 波动率: 60日年化 (越低越好)
        vol_60d = returns.tail(60).std() * np.sqrt(252)

        # 3. 趋势质量: 60日内收盘>MA20的天数占比
        ma20 = close.rolling(20).mean()
        above_ma20 = (close > ma20).tail(60)
        trend_quality = above_ma20.sum() / 60

        # 4. MA偏离度: abs(close - MA60) / MA60 (偏离太远扣分)
        ma60 = close.rolling(60).mean().iloc[-1]
        ma_deviation = abs(close.iloc[-1] - ma60) / ma60

        # 基础过滤
        last_price = close.iloc[-1]
        last_amount = clean["amount"].iloc[-1] if "amount" in clean.columns else 0

        if last_price < 10 or last_price > 500:
            return None
        if last_amount < 5e7:
            return None

        return {
            "momentum": momentum,
            "volatility": vol_60d,
            "trend_quality": trend_quality,
            "ma_deviation": ma_deviation,
            "last_price": last_price,
        }
    except Exception:
        return None


def compute_score(df):
    """
    综合评分: 每个因子排名百分位 × 权重，再加权求和
    momentum 和 trend_quality 是越高越好 (rank ascending=False)
    volatility 和 ma_deviation 是越低越好 (rank ascending=True)
    """
    df = df.copy()
    df["rank_mom"] = df["momentum"].rank(pct=True, ascending=True)
    df["rank_vol"] = df["volatility"].rank(pct=True, ascending=False)  # 低波=高分
    df["rank_trend"] = df["trend_quality"].rank(pct=True, ascending=True)
    df["rank_dev"] = df["ma_deviation"].rank(pct=True, ascending=False)  # 小偏离=高分

    df["score"] = (
        df["rank_mom"] * W_MOMENTUM
        + df["rank_vol"] * W_VOLATILITY
        + df["rank_trend"] * W_TREND_QUALITY
        + df["rank_dev"] * W_MA_DEVIATION
    )
    return df.sort_values("score", ascending=False)


def select_stocks(universe, split_date):
    print(f"\n[Selecting] Standing at {split_date}, using {TRAIN_YEARS}y prior data...")

    candidates = []
    for i, (_, row) in enumerate(universe.iterrows()):
        sym = row["symbol"]
        name = row["name"]
        factors = compute_factors(sym, split_date)

        if factors is None:
            continue

        candidates.append({
            "symbol": sym,
            "name": name,
            "industry": classify_industry(sym, name),
            **factors,
        })

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(universe)}, {len(candidates)} valid...")

    print(f"  Valid: {len(candidates)}")

    if len(candidates) < TOP_N:
        return pd.DataFrame()

    df = pd.DataFrame(candidates)
    df = compute_score(df)

    # 行业分散
    selected = []
    ind_count = {}
    for _, r in df.iterrows():
        ind = r["industry"]
        if ind_count.get(ind, 0) < 2:
            selected.append(r)
            ind_count[ind] = ind_count.get(ind, 0) + 1
        if len(selected) >= TOP_N:
            break

    return pd.DataFrame(selected).reset_index(drop=True)


def backtest_selected(selected, split_date):
    test_start = pd.Timestamp(split_date)
    test_end = pd.Timestamp("2026-06-18")

    print(f"\n[Backtesting] {test_start.date()} ~ {test_end.date()}")

    results = []
    for _, row in selected.iterrows():
        sym = row["symbol"]
        name = row["name"]

        raw = fetch_daily_kline(
            sym,
            test_start.strftime("%Y-%m-%d"),
            test_end.strftime("%Y-%m-%d"),
            adjust="qfq",
        )
        if raw.empty or len(raw) < 30:
            results.append({"symbol": sym, "name": name, "error": "no data"})
            continue

        clean = clean_kline_data(raw, sym)
        bt_data = clean[["date", "open", "high", "low", "close", "volume"]].copy()

        engine = BacktestEngine(initial_cash=CASH)
        engine.add_data(bt_data, symbol=sym)
        engine.add_strategy(MACrossoverBT, short_period=5, long_period=20)
        engine.run()
        r = engine.get_results()

        results.append({
            "symbol": sym, "name": name,
            "industry": row["industry"],
            "momentum": f'{row["momentum"]:.1%}',
            "vol": f'{row["volatility"]:.1%}',
            "trend_q": f'{row["trend_quality"]:.1%}',
            "score": f'{row["score"]:.3f}',
            "test_return": r["total_return"],
            "test_sharpe": r.get("sharpe_ratio") or 0,
            "test_dd": r["max_drawdown"],
            "test_trades": r["total_trades"],
        })
        print(f"  {sym} {name}: score={row['score']:.3f} test={r['total_return']:+.1%}")

    return pd.DataFrame(results)


def print_results(all_results):
    for split_date, result_df in all_results:
        if result_df.empty:
            continue
        avg_ret = result_df["test_return"].mean()
        pos = (result_df["test_return"] > 0).sum()
        print(f"\n{'='*90}")
        print(f"  Split: {split_date}")
        print(f"  {'Sym':<8} {'Name':<8} {'Ind':<10} {'Mom':>7} {'Vol':>7} {'TrendQ':>7} {'Score':>7} {'TestRet':>8} {'DD':>7}")
        print(f"  {'-'*80}")
        for _, r in result_df.iterrows():
            print(f"  {r['symbol']:<8} {r['name']:<8} {r['industry']:<10} "
                  f"{r['momentum']:>7} {r['vol']:>7} {r['trend_q']:>7} {r['score']:>7} "
                  f"{r['test_return']:>7.1%} {r['test_dd']:>6.1%}")
        print(f"  {'-'*80}")
        print(f"  Avg test return: {avg_ret:+.1%}  |  {pos}/{len(result_df)} positive")


def main():
    print("=" * 90)
    print("  TIMELINE SELECTION — Multi-Factor (Momentum + Vol + TrendQ + MA_Dev)")
    print("=" * 90)

    universe = get_universe()
    print(f"Universe: {len(universe)} stocks")

    all_results = []
    for split_date in SPLIT_DATES:
        selected = select_stocks(universe, split_date)
        if selected.empty:
            print(f"  [SKIP] No stocks for {split_date}")
            continue

        print(f"\n  Top 8 by multi-factor score:")
        for _, r in selected.iterrows():
            print(f"    {r['symbol']} {r['name']:<8} ({r['industry']:<8}) "
                  f"mom={r['momentum']:.1%} vol={r['volatility']:.1%} "
                  f"trend_q={r['trend_quality']:.1%} dev={r['ma_deviation']:.1%}")

        test_results = backtest_selected(selected, split_date)
        all_results.append((split_date, test_results))

    print_results(all_results)

    # Compare with old results
    print(f"\n{'='*90}")
    print(f"  SUMMARY: Multi-Factor vs Pure Momentum")
    print(f"{'='*90}")
    print(f"  {'Split':<14} {'Multi-Factor Avg':<18} {'Pure Momentum Avg':<18}")
    print(f"  {'-'*50}")
    print(f"  {'2025-01-01':<14} {'+27.7% (from R1)':<18} {'(need re-run)':<18}")
    print(f"  {'2025-07-01':<14} {'TBD':<18} {'-7.6% (from R2)':<18}")
    print(f"  {'2026-01-01':<14} {'TBD':<18} {'-4.3% (from R3)':<18}")


if __name__ == "__main__":
    main()
