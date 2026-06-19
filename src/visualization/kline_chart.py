"""
K线图可视化模块

基于 mplfinance 和 matplotlib，提供：
- OHLC K线图 + 成交量
- 移动平均线叠加
- 中文支持
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
from pathlib import Path
from config.settings import PLOT_STYLE, CHARTS_DIR

# 设置中文字体
plt.rcParams.update(PLOT_STYLE)


def _prepare_mpf_data(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """为 mplfinance 准备数据格式"""
    plot_df = df.set_index(date_col)
    required_cols = {"open": "Open", "close": "Close", "high": "High", "low": "Low", "volume": "Volume"}
    rename_map = {k: v for k, v in required_cols.items() if k in plot_df.columns}
    plot_df = plot_df.rename(columns=rename_map)
    return plot_df


def plot_candlestick(
    df: pd.DataFrame,
    title: str = "K线图",
    save_name: str = None,
    volume: bool = True,
    figsize: tuple = (14, 8),
) -> mpf.plot:
    """
    绘制基础 K 线图 + 成交量

    Args:
        df: 包含 OHLCV 的 DataFrame
        title: 图表标题
        save_name: 保存文件名（不含路径），None 则不保存
        volume: 是否显示成交量子图
        figsize: 图表尺寸

    Returns:
        mplfinance plot 对象
    """
    plot_df = _prepare_mpf_data(df)

    kwargs = dict(
        type="candle",
        style="charles",
        title=title,
        ylabel="Price (CNY)",
        volume=volume,
        figsize=figsize,
        mav=(5, 10, 20, 60),  # 自带 MA 叠加
        show_nontrading=True,
    )

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        kwargs["savefig"] = CHARTS_DIR / save_name

    return mpf.plot(plot_df, **kwargs)


def plot_with_ma(
    df: pd.DataFrame,
    title: str = "K线 + 移动平均线",
    ma_periods: list = None,
    save_name: str = None,
    volume: bool = True,
    figsize: tuple = (14, 8),
):
    """
    绘制 K 线图并叠加移动平均线

    Args:
        df: 包含 OHLCV 和 MA 列的 DataFrame
        title: 图表标题
        ma_periods: MA 周期列表，如 [5, 10, 20, 60]
        save_name: 保存文件名
        volume: 是否显示成交量
        figsize: 图表尺寸
    """
    if ma_periods is None:
        ma_periods = [5, 10, 20, 60]

    plot_df = _prepare_mpf_data(df)

    kwargs = dict(
        type="candle",
        style="charles",
        title=title,
        ylabel="Price (CNY)",
        volume=volume,
        figsize=figsize,
        mav=ma_periods,
        show_nontrading=True,
    )

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        kwargs["savefig"] = CHARTS_DIR / save_name

    return mpf.plot(plot_df, **kwargs)


def plot_price_line(
    df: pd.DataFrame,
    title: str = "收盘价走势",
    save_name: str = None,
    figsize: tuple = (14, 6),
):
    """
    绘制收盘价折线图（简洁版）

    Args:
        df: DataFrame
        title: 标题
        save_name: 保存文件名
        figsize: 图表尺寸
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(df["date"], df["close"], linewidth=0.8, color="black")
    ax.set_title(title)
    ax.set_xlabel("日期")
    ax.set_ylabel("价格 (元)")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, ax
