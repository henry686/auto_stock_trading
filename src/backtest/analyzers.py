"""
绩效分析模块

计算回测/模拟的核心绩效指标：
- 总收益率 / 年化收益率
- 夏普比率
- 最大回撤
- 胜率 / 盈亏比
- 交易次数
"""
import numpy as np
import pandas as pd


def calculate_all_metrics(
    equity_series: pd.Series,
    trades: list = None,
    risk_free_rate: float = 0.02,
) -> dict:
    """
    计算所有绩效指标

    Args:
        equity_series: 权益序列（index 为日期）
        trades: 交易记录列表，每条包含 pnl 字段
        risk_free_rate: 无风险利率（默认 2%）

    Returns:
        dict with all metrics
    """
    metrics = {}

    if len(equity_series) < 2:
        return metrics

    initial_value = equity_series.iloc[0]
    final_value = equity_series.iloc[-1]

    # 总收益率
    total_return = (final_value - initial_value) / initial_value
    metrics["total_return"] = total_return

    # 日收益率
    daily_returns = equity_series.pct_change().dropna()
    if len(daily_returns) == 0:
        return metrics

    # 年化收益率（假设 252 个交易日）
    trading_days = len(daily_returns)
    if trading_days > 0:
        annualized_return = (1 + total_return) ** (252 / trading_days) - 1
    else:
        annualized_return = 0.0
    metrics["annualized_return"] = annualized_return

    # 年化波动率
    annualized_vol = daily_returns.std() * np.sqrt(252)
    metrics["annualized_volatility"] = annualized_vol

    # 夏普比率
    excess_return = daily_returns.mean() - risk_free_rate / 252
    if daily_returns.std() > 0:
        sharpe = excess_return / daily_returns.std() * np.sqrt(252)
    else:
        sharpe = 0.0
    metrics["sharpe_ratio"] = sharpe

    # 最大回撤
    peak = equity_series.expanding().max()
    drawdown = (equity_series - peak) / peak
    max_dd = drawdown.min()
    max_dd_date = drawdown.idxmin() if not drawdown.empty else None
    metrics["max_drawdown"] = abs(max_dd) if max_dd < 0 else 0.0
    metrics["max_drawdown_date"] = max_dd_date

    # 最大回撤持续天数
    if max_dd < 0:
        dd_start = drawdown[drawdown == 0].index
        if not dd_start.empty:
            try:
                dd_end = max_dd_date
                closest_start = dd_start[dd_start < dd_end]
                if not closest_start.empty:
                    metrics["max_drawdown_days"] = (dd_end - closest_start[-1]).days
                else:
                    metrics["max_drawdown_days"] = 0
            except Exception:
                metrics["max_drawdown_days"] = 0
        else:
            metrics["max_drawdown_days"] = 0
    else:
        metrics["max_drawdown_days"] = 0

    # 卡尔玛比率（年化收益/最大回撤）
    if metrics["max_drawdown"] > 0:
        metrics["calmar_ratio"] = annualized_return / metrics["max_drawdown"]
    else:
        metrics["calmar_ratio"] = float("inf") if annualized_return > 0 else 0.0

    # 交易统计
    if trades:
        pnls = [t.get("pnl", 0) for t in trades if "pnl" in t]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p < 0]

        metrics["total_trades"] = len(pnls)
        metrics["winning_trades"] = len(winning)
        metrics["losing_trades"] = len(losing)
        metrics["win_rate"] = len(winning) / len(pnls) if pnls else 0.0

        avg_win = np.mean(winning) if winning else 0
        avg_loss = abs(np.mean(losing)) if losing else 0
        metrics["avg_win"] = avg_win
        metrics["avg_loss"] = avg_loss
        metrics["profit_factor"] = (sum(winning) / abs(sum(losing))) if losing else float("inf")

        # 总盈亏
        metrics["total_pnl"] = sum(pnls)
        metrics["total_fees"] = sum(t.get("fee", 0) for t in trades)
    else:
        metrics["total_trades"] = 0
        metrics["win_rate"] = 0.0

    return metrics


def print_metrics_report(metrics: dict):
    """格式化打印绩效指标"""
    print("\n" + "=" * 60)
    print("  PERFORMANCE METRICS")
    print("=" * 60)

    def print_row(label, value, fmt=",}"):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            value_str = "N/A"
        elif fmt == ".2%":
            value_str = f"{value:>12.2%}"
        elif fmt == ".2f":
            value_str = f"{value:>12.2f}"
        elif fmt == ",.2f":
            value_str = f"{value:>12,.2f}"
        elif fmt == "d":
            value_str = f"{value:>12d}"
        else:
            value_str = f"{value:>12}"
        print(f"  {label:<20} {value_str}")

    print_row("Total Return", metrics.get("total_return"), ".2%")
    print_row("Annualized Return", metrics.get("annualized_return"), ".2%")
    print_row("Annualized Vol", metrics.get("annualized_volatility"), ".2%")
    print_row("Sharpe Ratio", metrics.get("sharpe_ratio"), ".2f")
    print_row("Calmar Ratio", metrics.get("calmar_ratio"), ".2f")
    print_row("Max Drawdown", -metrics.get("max_drawdown", 0), ".2%")
    if metrics.get("max_drawdown_days"):
        print_row("Max DD Days", metrics["max_drawdown_days"], "d")
    print_row("Total Trades", metrics.get("total_trades"), "d")
    print_row("Win Rate", metrics.get("win_rate"), ".2%")
    print_row("Win/Loss", f"{metrics.get('winning_trades',0)}/{metrics.get('losing_trades',0)}", "")
    print_row("Profit Factor", metrics.get("profit_factor"), ".2f")
    print_row("Total P&L", metrics.get("total_pnl"), ",.2f")
    print_row("Total Fees", metrics.get("total_fees"), ",.2f")
    print("=" * 60)
