#!/usr/bin/env python
"""
运行回测

用法:
    cd project_root
    .venv/Scripts/python.exe scripts/run_backtest.py

    # 可选参数
    .venv/Scripts/python.exe scripts/run_backtest.py --symbol 600519 --short 5 --long 20 --cash 10000
"""
import sys
from pathlib import Path
import argparse

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.storage import load_from_parquet
from src.backtest.engine import BacktestEngine
from src.backtest.reporter import generate_report, save_report_json
from src.strategy.ma_crossover import MACrossoverBT
from config.settings import INITIAL_CAPITAL


def run_backtest(
    symbol: str = "600519",
    short_period: int = 5,
    long_period: int = 20,
    initial_cash: float = INITIAL_CAPITAL,
):
    print(f"\n{'='*60}")
    print(f"  MA Crossover Backtest: {symbol}")
    print(f"  Period: {short_period}/{long_period} | Cash: {initial_cash:,.0f} CNY")
    print(f"{'='*60}")

    # 1. 加载数据
    df = load_from_parquet(symbol)
    print(f"  Data: {len(df)} rows ({df['date'].min().date()} ~ {df['date'].max().date()})")

    # 2. 准备数据（确保列为 backtrader 需要格式）
    bt_data = df[["date", "open", "high", "low", "close", "volume"]].copy()
    # backtrader PandasData needs datetime as a column, not index

    # 3. 创建回测引擎
    engine = BacktestEngine(initial_cash=initial_cash)
    engine.add_data(bt_data, symbol=symbol, name=symbol)

    # 4. 添加策略
    engine.add_strategy(MACrossoverBT, short_period=short_period, long_period=long_period)

    # 5. 运行回测
    results = engine.run()

    # 6. 打印和保存结果
    engine.print_summary()
    bt_results = engine.get_results()

    # 7. 保存报告
    report = generate_report(
        results=bt_results,
        metadata={
            "strategy": "MACrossover",
            "symbol": symbol,
            "short_period": short_period,
            "long_period": long_period,
            "initial_cash": initial_cash,
            "date_range": f"{df['date'].min().date()} ~ {df['date'].max().date()}",
        },
    )
    save_report_json(report)

    return results


def main():
    parser = argparse.ArgumentParser(description="Run MA Crossover Backtest")
    parser.add_argument("--symbol", default="600519", help="Stock symbol (default: 600519)")
    parser.add_argument("--short", type=int, default=5, help="Short MA period (default: 5)")
    parser.add_argument("--long", type=int, default=20, help="Long MA period (default: 20)")
    parser.add_argument("--cash", type=float, default=INITIAL_CAPITAL, help=f"Initial cash (default: {INITIAL_CAPITAL})")

    args = parser.parse_args()
    run_backtest(
        symbol=args.symbol,
        short_period=args.short,
        long_period=args.long,
        initial_cash=args.cash,
    )


if __name__ == "__main__":
    main()
