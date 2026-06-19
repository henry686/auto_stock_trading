#!/usr/bin/env python
"""
运行模拟交易

用法:
    cd project_root
    .venv/Scripts/python.exe scripts/run_simulation.py

    # 可选参数
    .venv/Scripts/python.exe scripts/run_simulation.py --symbol 600036 --cash 10000
"""
import sys
from pathlib import Path
import argparse

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.storage import load_from_parquet
from src.indicators.calculator import add_all_indicators
from src.strategy.ma_crossover import MACrossoverStrategy
from src.simulation.trading_engine import SimulationEngine
from src.backtest.analyzers import print_metrics_report
from src.visualization.performance import plot_equity_curve, plot_drawdown
from config.settings import INITIAL_CAPITAL


def run_simulation(
    symbol: str = "600036",
    short_period: int = 5,
    long_period: int = 20,
    initial_cash: float = INITIAL_CAPITAL,
):
    # 1. 加载数据
    df = load_from_parquet(symbol)
    print(f"Data: {len(df)} rows ({df['date'].min().date()} ~ {df['date'].max().date()})")

    # 2. 添加指标
    df = add_all_indicators(df)

    # 3. 创建策略
    strategy = MACrossoverStrategy(
        short_period=short_period,
        long_period=long_period,
        ma_type="sma",
    )

    # 4. 创建模拟引擎
    engine = SimulationEngine(initial_cash=initial_cash)
    engine.load_data(symbol, df)
    engine.add_strategy(strategy)

    # 5. 运行模拟
    report = engine.run()

    # 6. 打印结果
    engine.print_summary()

    # 7. 绘制图表
    equity = engine.get_equity_curve()
    if not equity.empty:
        plot_equity_curve(equity, title=f"{symbol} Simulation Equity Curve", save_name=f"sim_{symbol}_equity.png")
        plot_drawdown(equity, title=f"{symbol} Simulation Drawdown", save_name=f"sim_{symbol}_drawdown.png")
        print("Charts saved to results/charts/")

    # 8. 详细指标
    if report.get("metrics"):
        print_metrics_report(report["metrics"])

    return report


def main():
    parser = argparse.ArgumentParser(description="Run Simulation Trading")
    parser.add_argument("--symbol", default="600036", help="Stock symbol")
    parser.add_argument("--short", type=int, default=5, help="Short MA period")
    parser.add_argument("--long", type=int, default=20, help="Long MA period")
    parser.add_argument("--cash", type=float, default=INITIAL_CAPITAL, help="Initial cash")

    args = parser.parse_args()
    run_simulation(
        symbol=args.symbol,
        short_period=args.short,
        long_period=args.long,
        initial_cash=args.cash,
    )


if __name__ == "__main__":
    main()
