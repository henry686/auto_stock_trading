"""
技术指标叠加可视化

在 K 线图上叠加/并列显示各种技术指标。
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
from config.settings import PLOT_STYLE, CHARTS_DIR

plt.rcParams.update(PLOT_STYLE)

# 颜色方案
COLORS = {
    "price": "black",
    "ma_5": "blue",
    "ma_10": "orange",
    "ma_20": "purple",
    "ma_60": "green",
    "dif": "white",
    "dea": "yellow",
    "macd_pos": "red",
    "macd_neg": "green",
    "rsi": "blue",
    "rsi_ob": "red",
    "rsi_os": "green",
    "k": "blue",
    "d": "orange",
    "j": "magenta",
    "boll_upper": "red",
    "boll_middle": "blue",
    "boll_lower": "green",
    "volume": "blue",
    "volume_ma": "orange",
}


def plot_macd(df: pd.DataFrame, figsize: tuple = (14, 8), save_name: str = None):
    """
    绘制 MACD 子图

    Args:
        df: 包含 close, macd_dif, macd_dea, macd_hist 的 DataFrame
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        (fig, (ax1, ax2))
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    # 上：价格 + 均线
    ax1.plot(df["date"], df["close"], color=COLORS["price"], linewidth=0.8, label="Close")
    if "ma_20" in df.columns:
        ax1.plot(df["date"], df["ma_20"], color=COLORS["ma_20"], linewidth=0.8, label="MA20")
    if "ma_60" in df.columns:
        ax1.plot(df["date"], df["ma_60"], color=COLORS["ma_60"], linewidth=0.8, label="MA60")
    ax1.set_ylabel("Price (CNY)")
    ax1.set_title("MACD 指标")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # 下：MACD
    dif = df.get("macd_dif", pd.Series(index=df.index))
    dea = df.get("macd_dea", pd.Series(index=df.index))
    hist = df.get("macd_hist", pd.Series(index=df.index))

    ax2.plot(df["date"], dif, color=COLORS["dif"], linewidth=0.8, label="DIF")
    ax2.plot(df["date"], dea, color=COLORS["dea"], linewidth=0.8, label="DEA")

    # MACD 柱状图（红涨绿跌）
    pos_mask = hist >= 0
    if pos_mask.any():
        ax2.bar(df["date"][pos_mask], hist[pos_mask], color=COLORS["macd_pos"], width=0.8, label="MACD (+)")
    neg_mask = hist < 0
    if neg_mask.any():
        ax2.bar(df["date"][neg_mask], hist[neg_mask], color=COLORS["macd_neg"], width=0.8, label="MACD (-)")

    ax2.set_ylabel("MACD")
    ax2.axhline(y=0, color="gray", linewidth=0.5, linestyle="--")
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.3)

    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, (ax1, ax2)


def plot_rsi(df: pd.DataFrame, period: int = 14, figsize: tuple = (14, 8), save_name: str = None):
    """
    绘制 RSI 子图

    Args:
        df: 包含 close 和 rsi_{period} 的 DataFrame
        period: RSI 周期
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        (fig, (ax1, ax2))
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    rsi_col = f"rsi_{period}"

    # 上：价格
    ax1.plot(df["date"], df["close"], color=COLORS["price"], linewidth=0.8, label="Close")
    ax1.set_ylabel("Price (CNY)")
    ax1.set_title(f"RSI({period}) 指标")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # 下：RSI
    if rsi_col in df.columns:
        ax2.plot(df["date"], df[rsi_col], color=COLORS["rsi"], linewidth=0.8, label=f"RSI({period})")
    ax2.axhline(y=70, color=COLORS["rsi_ob"], linewidth=0.8, linestyle="--", label="Overbought (70)")
    ax2.axhline(y=30, color=COLORS["rsi_os"], linewidth=0.8, linestyle="--", label="Oversold (30)")
    ax2.axhline(y=50, color="gray", linewidth=0.5, linestyle="-")
    ax2.set_ylabel("RSI")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.3)

    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, (ax1, ax2)


def plot_kdj(df: pd.DataFrame, figsize: tuple = (14, 8), save_name: str = None):
    """
    绘制 KDJ 子图

    Args:
        df: 包含 close, kdj_k, kdj_d, kdj_j 的 DataFrame
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        (fig, (ax1, ax2))
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    # 上：价格
    ax1.plot(df["date"], df["close"], color=COLORS["price"], linewidth=0.8, label="Close")
    ax1.set_ylabel("Price (CNY)")
    ax1.set_title("KDJ 随机指标")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # 下：KDJ
    for col, label, color in [
        ("kdj_k", "K", COLORS["k"]),
        ("kdj_d", "D", COLORS["d"]),
        ("kdj_j", "J", COLORS["j"]),
    ]:
        if col in df.columns:
            ax2.plot(df["date"], df[col], color=color, linewidth=0.8, label=label)

    ax2.axhline(y=80, color="red", linewidth=0.8, linestyle="--", label="Overbought (80)")
    ax2.axhline(y=20, color="green", linewidth=0.8, linestyle="--", label="Oversold (20)")
    ax2.set_ylabel("KDJ")
    ax2.set_ylim(0, 100)
    ax2.legend(loc="upper left", fontsize=8)
    ax2.grid(True, alpha=0.3)

    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, (ax1, ax2)


def plot_bollinger(df: pd.DataFrame, figsize: tuple = (14, 8), save_name: str = None):
    """
    绘制布林带

    Args:
        df: 包含 close, boll_upper, boll_middle, boll_lower 的 DataFrame
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        (fig, (ax1, ax2))
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True, gridspec_kw={"height_ratios": [3, 1]})

    # 上：价格 + 布林带
    ax1.plot(df["date"], df["close"], color=COLORS["price"], linewidth=0.8, label="Close")
    ax1.plot(df["date"], df["boll_upper"], color=COLORS["boll_upper"], linewidth=0.6, linestyle="--", label="Upper Band")
    ax1.plot(df["date"], df["boll_middle"], color=COLORS["boll_middle"], linewidth=0.6, linestyle="-", label="Middle (MA20)")
    ax1.plot(df["date"], df["boll_lower"], color=COLORS["boll_lower"], linewidth=0.6, linestyle="--", label="Lower Band")

    # 填充布林带区域
    ax1.fill_between(df["date"], df["boll_upper"], df["boll_lower"], alpha=0.1, color="blue")

    ax1.set_ylabel("Price (CNY)")
    ax1.set_title("布林带 (Bollinger Bands)")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # 下：成交量
    if "volume_lots" in df.columns:
        ax2.bar(df["date"], df["volume_lots"], color=COLORS["volume"], width=0.8)
        if "volume_ma_20" in df.columns:
            ax2.plot(df["date"], df["volume_ma_20"] / 100, color=COLORS["volume_ma"], linewidth=0.8, label="Volume MA20")
        ax2.set_ylabel("Volume (Lots)")
        ax2.legend(loc="upper left", fontsize=8)
        ax2.grid(True, alpha=0.3)

    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, (ax1, ax2)


def plot_full_dashboard(
    df: pd.DataFrame,
    title: str = "技术分析仪表盘",
    figsize: tuple = (16, 12),
    save_name: str = None,
):
    """
    绘制综合分析仪表盘

    包含：K线+布林带、成交量、MACD、RSI、KDJ

    Args:
        df: 包含所有指标列的 DataFrame（需先调用 add_all_indicators）
        title: 标题
        figsize: 图表尺寸
        save_name: 保存文件名

    Returns:
        fig, axes
    """
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title, fontsize=14, fontweight="bold")

    gs = fig.add_gridspec(5, 1, height_ratios=[3, 1, 1, 1, 1], hspace=0.3)

    # Panel 1: Price + Bollinger + MA
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df["date"], df["close"], color=COLORS["price"], linewidth=0.8, label="Close")
    if "ma_20" in df.columns:
        ax1.plot(df["date"], df["ma_20"], color=COLORS["ma_20"], linewidth=0.8, alpha=0.5, label="MA20")
    if "boll_upper" in df.columns:
        ax1.plot(df["date"], df["boll_upper"], color=COLORS["boll_upper"], linewidth=0.5, linestyle="--", alpha=0.5)
        ax1.plot(df["date"], df["boll_lower"], color=COLORS["boll_lower"], linewidth=0.5, linestyle="--", alpha=0.5)
        ax1.fill_between(df["date"], df["boll_upper"], df["boll_lower"], alpha=0.05, color="blue")
    ax1.set_ylabel("Price")
    ax1.legend(loc="upper left", fontsize=7, ncol=2)
    ax1.grid(True, alpha=0.3)

    # Panel 2: Volume
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    if "volume_lots" in df.columns:
        ax2.bar(df["date"], df["volume_lots"], color=COLORS["volume"], width=0.8, alpha=0.6)
    if "volume_ma_20" in df.columns:
        ax2.plot(df["date"], df["volume_ma_20"] / 100, color=COLORS["volume_ma"], linewidth=0.8)
    ax2.set_ylabel("Volume")
    ax2.grid(True, alpha=0.3)

    # Panel 3: MACD
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    if "macd_dif" in df.columns:
        ax3.plot(df["date"], df["macd_dif"], color=COLORS["dif"], linewidth=0.8, label="DIF")
        ax3.plot(df["date"], df["macd_dea"], color=COLORS["dea"], linewidth=0.8, label="DEA")
        hist = df["macd_hist"]
        pos = hist >= 0
        if pos.any():
            ax3.bar(df["date"][pos], hist[pos], color=COLORS["macd_pos"], width=0.8, alpha=0.7)
        if (~pos).any():
            ax3.bar(df["date"][~pos], hist[~pos], color=COLORS["macd_neg"], width=0.8, alpha=0.7)
    ax3.axhline(y=0, color="gray", linewidth=0.5)
    ax3.set_ylabel("MACD")
    ax3.legend(loc="upper left", fontsize=7)
    ax3.grid(True, alpha=0.3)

    # Panel 4: RSI
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    if "rsi_14" in df.columns:
        ax4.plot(df["date"], df["rsi_14"], color=COLORS["rsi"], linewidth=0.8)
    ax4.axhline(y=70, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax4.axhline(y=30, color="green", linewidth=0.5, linestyle="--", alpha=0.5)
    ax4.set_ylim(0, 100)
    ax4.set_ylabel("RSI(14)")
    ax4.grid(True, alpha=0.3)

    # Panel 5: KDJ
    ax5 = fig.add_subplot(gs[4], sharex=ax1)
    for col, label, color in [("kdj_k", "K", COLORS["k"]), ("kdj_d", "D", COLORS["d"]), ("kdj_j", "J", COLORS["j"])]:
        if col in df.columns:
            ax5.plot(df["date"], df[col], color=color, linewidth=0.8, label=label)
    ax5.axhline(y=80, color="red", linewidth=0.5, linestyle="--", alpha=0.5)
    ax5.axhline(y=20, color="green", linewidth=0.5, linestyle="--", alpha=0.5)
    ax5.set_ylim(0, 100)
    ax5.set_ylabel("KDJ")
    ax5.legend(loc="upper left", fontsize=7)
    ax5.grid(True, alpha=0.3)

    fig.autofmt_xdate()

    if save_name:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(CHARTS_DIR / save_name, dpi=150, bbox_inches="tight")

    return fig, (ax1, ax2, ax3, ax4, ax5)
