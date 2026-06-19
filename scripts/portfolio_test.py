#!/usr/bin/env python
"""
真实投资测试 — 10万本金，分到多个标的，一个总账户

假设: 等权分配，每只标的独立运行，最后加总
这等价于把 10 万分成 9 份，每份独立交易
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from src.data.storage import load_from_parquet
from src.indicators.calculator import add_all_indicators
from src.strategy.ma_crossover import MACrossoverStrategy
from src.simulation.trading_engine import SimulationEngine
from config.settings import WATCHLIST

TOTAL_CASH = 100_000
N_ASSETS = len(WATCHLIST)
CASH_PER = TOTAL_CASH / N_ASSETS  # 每只约 11,111

print(f"Total cash: {TOTAL_CASH:,.0f}")
print(f"Assets: {N_ASSETS}")
print(f"Per asset: {CASH_PER:,.0f}\n")

results = []
for symbol, name in WATCHLIST:
    print(f"{symbol} {name}...", end=" ", flush=True)

    df = load_from_parquet(symbol)

    if symbol == "000300":
        # 指数简化版: 按信号直接算收益
        strategy = MACrossoverStrategy(short_period=5, long_period=20)
        signals = strategy.generate_signals(df)
        positions = strategy.get_positions(df)
        daily_ret = df["close"].pct_change().fillna(0)
        strategy_ret = daily_ret * positions.shift(1).fillna(0)
        equity = (1 + strategy_ret).cumprod() * CASH_PER
        final_val = equity.iloc[-1]
        max_dd = ((equity - equity.expanding().max()) / equity.expanding().max()).min()
        trades = (signals["signal"] != 0).sum()
    else:
        df = add_all_indicators(df)
        strategy = MACrossoverStrategy(short_period=5, long_period=20)
        engine = SimulationEngine(initial_cash=CASH_PER)
        engine.load_data(symbol, df)
        engine.add_strategy(strategy)
        engine.run()
        snapshots = engine.account.daily_snapshots
        if not snapshots:
            final_val = CASH_PER
            max_dd = 0
            trades = 0
        else:
            final_val = snapshots[-1].total_value
            equity = pd.Series([s.total_value for s in snapshots])
            max_dd = ((equity - equity.expanding().max()) / equity.expanding().max()).min()
            trades = len(engine.order_manager.trades)

    pnl = final_val - CASH_PER
    print(f"{final_val:>10,.0f}  ({pnl:+.1%})")
    results.append({"symbol": symbol, "name": name, "invested": CASH_PER,
                    "final": final_val, "pnl": pnl, "dd": max_dd, "trades": trades})

# 汇总
total_final = sum(r["final"] for r in results)
total_return = (total_final - TOTAL_CASH) / TOTAL_CASH
total_pnl = total_final - TOTAL_CASH

print(f"\n{'='*65}")
print(f"  PORTFOLIO RESULT")
print(f"{'='*65}")
print(f"  {'Asset':<15} {'Invested':>10} {'Final':>10} {'P&L':>10}")
print(f"  {'-'*50}")
for r in results:
    print(f"  {r['symbol']+' '+r['name']:<15} {r['invested']:>10,.0f} {r['final']:>10,.0f} {r['pnl']:>+10,.0f}")
print(f"  {'-'*50}")
print(f"  {'TOTAL':<15} {TOTAL_CASH:>10,.0f} {total_final:>10,.0f} {total_pnl:>+10,.0f}")
print(f"{'='*65}")
print(f"  Return: {total_return:+.1%}")
print(f"  Max individual DD: {min(r['dd'] for r in results):.1%}")
print(f"  Total trades: {sum(r['trades'] for r in results)}")
