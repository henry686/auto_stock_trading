#!/usr/bin/env python
"""
指数策略验证 — 用 MA5/20 交易沪深300

不选股，只做择时：金叉买入、死叉卖出。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from src.data.storage import load_from_parquet
from src.strategy.ma_crossover import MACrossoverStrategy

# 加载沪深300
df = load_from_parquet("000300")
df = df[df["date"] >= "2022-01-01"].copy()
print(f"CSI 300 data: {len(df)} rows, {df['date'].min().date()} ~ {df['date'].max().date()}")

# 生成信号
strategy = MACrossoverStrategy(short_period=5, long_period=20)
signals = strategy.generate_signals(df)

# 模拟交易 (忽略手数，直接按涨跌算)
# 信号=1 → 满仓买入，信号=-1 → 全仓卖出
positions = strategy.get_positions(df)

# 日收益率
daily_ret = df["close"].pct_change().fillna(0)
strategy_ret = daily_ret * positions.shift(1).fillna(0)

# 权益曲线
strategy_equity = (1 + strategy_ret).cumprod() * 100_000
buy_hold_equity = (1 + daily_ret).cumprod() * 100_000

# 绩效
total_ret = (strategy_equity.iloc[-1] - 100_000) / 100_000
bh_ret = (buy_hold_equity.iloc[-1] - 100_000) / 100_000
sharpe = strategy_ret.mean() / strategy_ret.std() * np.sqrt(252) if strategy_ret.std() > 0 else 0
peak = strategy_equity.expanding().max()
dd = ((strategy_equity - peak) / peak).min()

# 交易统计
buy_count = (signals["signal"] == 1).sum()
sell_count = (signals["signal"] == -1).sum()

# 手续费估算 (万2.5，每次换手)
turnovers = (positions.diff().abs() > 0).sum()
fees = turnovers * 0.00025 * 100_000  # 万2.5 佣金

print(f"\n{'='*60}")
print(f"  CSI 300 INDEX STRATEGY (MA5/20)")
print(f"{'='*60}")
print(f"  Strategy return:  {total_ret:+.1%}")
print(f"  Buy & Hold:       {bh_ret:+.1%}")
print(f"  Sharpe:           {sharpe:.2f}")
print(f"  Max Drawdown:     {dd:.1%}")
print(f"  Buy signals:      {buy_count}")
print(f"  Sell signals:     {sell_count}")
print(f"  Turnovers:        {turnovers}")
print(f"  Est. fees:        {fees:,.0f}")
print(f"{'='*60}")

# 分年表现
df["year"] = df["date"].dt.year
df["strategy_ret"] = strategy_ret
yearly = df.groupby("year")["strategy_ret"].apply(lambda x: (1 + x).prod() - 1)
bh_yearly = df.groupby("year")["close"].apply(lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0])

print(f"\n  Yearly returns:")
print(f"  {'Year':<8} {'Strategy':>10} {'Buy&Hold':>10}")
for y in yearly.index:
    print(f"  {y:<8} {yearly[y]:>9.1%} {bh_yearly[y]:>9.1%}")
