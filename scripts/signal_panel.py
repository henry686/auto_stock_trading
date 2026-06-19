#!/usr/bin/env python
"""周一信号面板 — 看一眼就知道该买什么卖什么"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.data.fetcher import fetch_daily_kline, fetch_index_daily
from src.data.cleaner import clean_kline_data
from src.data.storage import save_to_parquet, load_from_parquet
from src.strategy.ma_crossover import MACrossoverStrategy

CASH = 100_000
STOCKS = [("600036","招商银行"), ("600030","中信证券"), ("600276","恒瑞医药"),
          ("002460","赣锋锂业"), ("601633","长城汽车"), ("600570","恒生电子"),
          ("600900","长江电力"), ("600809","山西汾酒")]
INDEX = ("000300", "沪深300")

# 更新数据
print("Updating data...")
for sym, _ in STOCKS:
    raw = fetch_daily_kline(sym, "2022-01-01", "2026-12-31", adjust="qfq")
    clean = clean_kline_data(raw, sym)
    save_to_parquet(clean, sym)
# 指数用单独的函数
raw_idx = fetch_index_daily(INDEX[0], "2022-01-01", "2026-12-31")
save_to_parquet(raw_idx, INDEX[0])

# 生成信号
strategy = MACrossoverStrategy(short_period=5, long_period=20)
signals_list = []
all_assets = STOCKS + [INDEX]
for sym, nam in all_assets:
    df = load_from_parquet(sym)
    sig_df = strategy.generate_signals(df)
    latest = sig_df.iloc[-1]
    signals_list.append({
        "sym": sym, "name": nam, "close": latest["close"],
        "ma5": latest.get("ma_5", 0), "ma20": latest.get("ma_20", 0),
        "signal": latest["signal"],
    })

signals_df = pd.DataFrame(signals_list)
buy_count = (signals_df["signal"] == 1).sum()
per_buy = CASH / max(buy_count, 1)

# 打印
print(f"\n  SIGNAL PANEL — {pd.Timestamp.now().strftime('%Y-%m-%d %A')}")
print(f"  Strategy: MA5/20  |  Cash: {CASH:,}  |  Per buy: {per_buy:,.0f}")
print()
print(f"  {'Asset':<16} {'Price':>8} {'MA5':>8} {'MA20':>8} {'Signal':>8}  {'Action':<25}")
print(f"  {'-'*85}")

for _, r in signals_df.iterrows():
    sig = int(r["signal"])
    sym, nam, close = r["sym"], r["name"], r["close"]

    if sig == 1:
        if sym == "000300":
            action = f"ALLOCATE {per_buy:,.0f} CNY (index)"
        else:
            shares = int(per_buy / close / 100) * 100
            action = f"BUY  {shares} shares = {shares*close:,.0f} CNY"
    elif sig == -1:
        action = "SELL all"
    else:
        action = "HOLD"

    sig_str = {1: "BUY", -1: "SELL", 0: "HOLD"}[sig]
    print(f"  {sym} {nam:<10} {close:>8.2f} {r['ma5']:>8.2f} {r['ma20']:>8.2f} {sig_str:>8}  {action:<25}")

total_buy = sum(
    int(per_buy / r["close"] / 100) * 100 * r["close"]
    for _, r in signals_df.iterrows()
    if r["signal"] == 1 and r["sym"] != "000300"
)
idx_buy = signals_df[signals_df["sym"] == "000300"]["signal"].values
if len(idx_buy) > 0 and idx_buy[0] == 1:
    total_buy += per_buy
print(f"  {'-'*85}")
print(f"  Cash needed: ~{total_buy:,.0f} CNY")
print(f"  Remaining:   ~{CASH - total_buy:,.0f} CNY (hold for future signals)")
