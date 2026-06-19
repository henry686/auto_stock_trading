"""
绩效可视化模块

绘制回测/模拟交易的绩效图表：
- 权益曲线
- 回撤图
- 月度/年度收益热力图
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from config.settings import PLOT_STYLE, CHARTS_DIR

plt.rcParams.update(PLOT_STYLE)


def plot_equity_curve(
    equity_series: pd.Series,
    benchmark_series: pd.Series = None,
    title: str = "权益曲线",
    figsize: tuple = (14, 6),
    save_name: str = None,
):
    """
    绘制权益曲线

    Args:
        equity_series: 权益序列（index 为日期）
        benchmark_series: 基准序列（可选，用于对比）
        title: 图表标题
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        fig, ax
    """
    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(equity_series.index, equity_series.values, color="blue", linewidth=1.0, label="Strategy Equity")

    if benchmark_series is not None:
        # 归一化对齐
        norm_benchmark = benchmark_series / benchmark_series.iloc[0] * equity_series.iloc[0]
        ax.plot(norm_benchmark.index, norm_benchmark.values, color="gray", linewidth=0.8, linestyle="--", label="Benchmark")

    ax.axhline(y=equity_series.iloc[0], color="black", linewidth=0.5, linestyle="-", alpha=0.5)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity (CNY)")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, ax


def plot_drawdown(
    equity_series: pd.Series,
    title: str = "回撤分析",
    figsize: tuple = (14, 8),
    save_name: str = None,
):
    """
    绘制权益曲线 + 回撤子图

    Args:
        equity_series: 权益序列
        title: 图表标题
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        fig, (ax1, ax2)
    """
    # 计算回撤
    peak = equity_series.expanding().max()
    drawdown = (equity_series - peak) / peak * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [2, 1]})

    # 权益曲线
    ax1.plot(equity_series.index, equity_series.values, color="blue", linewidth=0.8)
    ax1.fill_between(equity_series.index, equity_series.values, equity_series.iloc[0], alpha=0.1, color="blue")
    ax1.set_title(title)
    ax1.set_ylabel("Equity (CNY)")
    ax1.grid(True, alpha=0.3)

    # 回撤
    ax2.fill_between(drawdown.index, drawdown.values, 0, color="red", alpha=0.3)
    ax2.plot(drawdown.index, drawdown.values, color="red", linewidth=0.5)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)

    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, (ax1, ax2)


def plot_monthly_returns(
    equity_series: pd.Series,
    title: str = "月度收益率热力图",
    figsize: tuple = (12, 8),
    save_name: str = None,
):
    """
    绘制月度收益率热力图

    Args:
        equity_series: 权益序列
        title: 标题
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        fig, ax
    """
    # 计算日收益率
    daily_returns = equity_series.pct_change()

    # 转换为月度收益率
    monthly = daily_returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    monthly_table = monthly.groupby([monthly.index.year, monthly.index.month]).first().unstack()
    monthly_table.index.name = "Year"
    monthly_table.columns = [f"{m:02d}" for m in range(1, 13)]

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(monthly_table * 100, cmap="RdYlGn", aspect="auto", vmin=-15, vmax=15)

    # 标注数值
    for i in range(monthly_table.shape[0]):
        for j in range(monthly_table.shape[1]):
            val = monthly_table.iloc[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val*100:.1f}%", ha="center", va="center", fontsize=8,
                        color="black" if abs(val) < 0.1 else "white")

    ax.set_xticks(range(12))
    ax.set_xticklabels([f"{m:02d}" for m in range(1, 13)])
    ax.set_yticks(range(len(monthly_table.index)))
    ax.set_yticklabels(monthly_table.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="Return (%)")

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, ax
