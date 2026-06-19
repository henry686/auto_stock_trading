#!/usr/bin/env python
"""
每周模拟跟踪器

用法:
    .venv/Scripts/python.exe scripts/weekly_tracker.py

功能:
    1. 对观察池每只股票跑模拟交易
    2. 记录本周结果到跟踪表
    3. 输出汇总报告

数据存储在: results/weekly_logs/
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import json
from datetime import datetime, date

from src.data.storage import load_from_parquet
from src.indicators.calculator import add_all_indicators
from src.strategy.ma_crossover import MACrossoverStrategy
from src.simulation.trading_engine import SimulationEngine
from config.settings import WATCHLIST


REPORT_DIR = Path("results/weekly_logs")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def run_weekly_simulation(symbol, name, cash=100_000):
    """跑单只股票模拟并返回摘要"""
    df = load_from_parquet(symbol)
    df = add_all_indicators(df)

    strategy = MACrossoverStrategy(short_period=5, long_period=20)
    engine = SimulationEngine(initial_cash=cash)
    engine.load_data(symbol, df)
    engine.add_strategy(strategy)
    engine.run()

    snapshots = engine.account.daily_snapshots
    if not snapshots:
        return None

    first = snapshots[0]
    last = snapshots[-1]

    # 计算本周
    week_ago = last.date - pd.Timedelta(days=7)
    week_snapshots = [s for s in snapshots if s.date >= week_ago]
    week_start = week_snapshots[0] if week_snapshots else last

    return {
        "symbol": symbol,
        "name": name,
        "initial_value": first.total_value,
        "current_value": last.total_value,
        "total_return": (last.total_value - first.total_value) / first.total_value,
        "max_drawdown": min(s.total_pnl / s.total_cost for s in snapshots),
        "week_return": (last.total_value - week_start.total_value) / week_start.total_value,
        "trades": len(engine.order_manager.trades),
        "current_cash": engine.account.cash,
        "positions": {s: p.quantity for s, p in engine.account.positions.items()},
        "last_signal": _get_last_signal(df, strategy),
        "last_update": datetime.now().isoformat(),
    }


def _get_last_signal(df, strategy):
    """获取最近一次信号"""
    signals = strategy.generate_signals(df)
    recent = signals[signals["signal"] != 0]
    if recent.empty:
        return "无信号"
    last = recent.iloc[-1]
    sig = "买入" if last["signal"] == 1 else "卖出"
    return f"{last['date'].date()} {sig}"


def print_tracker(records):
    """打印跟踪表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*100}")
    print(f"  WEEKLY TRACKER — {now}")
    print(f"{'='*100}")
    h = f"  {'Symbol':<8} {'Name':<10} {'Value':>10} {'Return':>8} {'WkChg':>7} {'MaxDD':>7} {'Trades':>6} {'Last Signal':<22} {'Pos':>6}"
    print(h)
    print(f"  {'-'*85}")

    total_value = 0
    total_initial = 0
    for r in records:
        if r is None:
            continue
        total_value += r["current_value"]
        total_initial += r["initial_value"]
        pos_str = ",".join(f"{s}:{q}" for s, q in r["positions"].items()) or "空仓"
        print(f"  {r['symbol']:<8} {r['name']:<10} {r['current_value']:>10,.0f} "
              f"{r['total_return']:>7.1%} {r['week_return']:>6.1%} "
              f"{r['max_drawdown']:>6.1%} {r['trades']:>6} "
              f"{r['last_signal']:<22} {pos_str:>6}")

    if total_initial > 0:
        total_ret = (total_value - total_initial) / total_initial
        print(f"  {'-'*85}")
        print(f"  {'合计':<18} {total_value:>10,.0f} {total_ret:>7.1%}")
    print(f"{'='*100}")


def save_log(records):
    """保存本周记录"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filepath = REPORT_DIR / f"tracker_{timestamp}.json"

    # Convert to serializable dicts
    clean = []
    for r in records:
        if r is None:
            continue
        d = dict(r)
        d.pop("positions", None)  # positions need special handling
        clean.append(d)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n[Log saved] {filepath}")
    return filepath


def main():
    print("=" * 100)
    print("  WEEKLY SIMULATION TRACKER")
    print("=" * 100)

    records = []
    for symbol, name in WATCHLIST:
        try:
            print(f"\nRunning {symbol} {name}...")
            r = run_weekly_simulation(symbol, name, cash=100_000)
            records.append(r)
        except Exception as e:
            print(f"  [SKIP] {symbol} {name}: {e}")
            records.append(None)

    print_tracker(records)
    save_log(records)

    # Also save CSV for easy tracking
    csv_data = []
    for r in records:
        if r is None:
            continue
        csv_data.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbol": r["symbol"],
            "name": r["name"],
            "current_value": r["current_value"],
            "total_return_pct": r["total_return"] * 100,
            "max_drawdown_pct": r["max_drawdown"] * 100,
            "total_trades": r["trades"],
            "last_signal": r["last_signal"],
        })

    csv_path = REPORT_DIR / "tracker_history.csv"
    df_new = pd.DataFrame(csv_data)

    if csv_path.exists():
        df_old = pd.read_csv(csv_path)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[CSV updated] {csv_path}")


if __name__ == "__main__":
    main()
