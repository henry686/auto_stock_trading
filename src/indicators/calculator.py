"""
技术指标计算模块

纯 pandas/numpy 实现，不依赖 TA-Lib 或 pandas-ta。
每个指标的算法注释中标注了参考来源。

指标列表:
- SMA / EMA: 简单/指数移动平均
- MACD: 异同移动平均线
- RSI: 相对强弱指标
- KDJ: 随机指标
- Bollinger Bands: 布林带
- ATR: 平均真实波幅
- Volume MA: 成交量均线
"""
import pandas as pd
import numpy as np


# ============================================================
# 移动平均线 (Moving Averages)
# ============================================================

def calc_sma(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """
    简单移动平均 (Simple Moving Average)

    公式: SMA = sum(close[t-period+1:t]) / period

    Args:
        df: 包含价格数据的 DataFrame
        period: 周期（默认 20）
        column: 计算列名

    Returns:
        SMA 序列
    """
    return df[column].rolling(window=period, min_periods=period).mean()


def calc_ema(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
    """
    指数移动平均 (Exponential Moving Average)

    公式: EMA[t] = alpha * close[t] + (1-alpha) * EMA[t-1]
    其中 alpha = 2 / (period + 1)

    Args:
        df: 包含价格数据的 DataFrame
        period: 周期（默认 20）
        column: 计算列名

    Returns:
        EMA 序列
    """
    return df[column].ewm(span=period, adjust=False, min_periods=period).mean()


# ============================================================
# MACD (异同移动平均线)
# ============================================================

def calc_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close",
) -> pd.DataFrame:
    """
    MACD 指标

    公式:
        DIF = EMA(fast) - EMA(slow)
        DEA = EMA(DIF, signal)   (即 Signal Line)
        MACD柱 = 2 * (DIF - DEA)  (即 Histogram)

    Args:
        df: 包含价格数据的 DataFrame
        fast: 快线周期（默认 12）
        slow: 慢线周期（默认 26）
        signal: 信号线周期（默认 9）
        column: 计算列名

    Returns:
        DataFrame with columns: dif, dea, macd (histogram)
    """
    ema_fast = calc_ema(df, fast, column)
    ema_slow = calc_ema(df, slow, column)

    result = pd.DataFrame(index=df.index)
    result["dif"] = ema_fast - ema_slow
    result["dea"] = result["dif"].ewm(span=signal, adjust=False, min_periods=signal).mean()
    result["macd"] = 2 * (result["dif"] - result["dea"])
    return result


# ============================================================
# RSI (相对强弱指标)
# ============================================================

def calc_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """
    RSI (Relative Strength Index)

    公式:
        RS = avg_gain / avg_loss
        RSI = 100 - 100 / (1 + RS)

    使用 Wilder's smoothing 方法（与主流平台一致）

    Args:
        df: 包含价格数据的 DataFrame
        period: 周期（默认 14）
        column: 计算列名

    Returns:
        RSI 序列 (0-100)
    """
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothing: EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ============================================================
# KDJ (随机指标)
# ============================================================

def calc_kdj(
    df: pd.DataFrame,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> pd.DataFrame:
    """
    KDJ 随机指标

    公式:
        RSV = (close - L_n) / (H_n - L_n) * 100
        K = 2/3 * prev_K + 1/3 * RSV    (或 m1 日 SMA(RSV))
        D = 2/3 * prev_D + 1/3 * K      (或 m2 日 SMA(K))
        J = 3 * K - 2 * D

    注: 国内常用 SMA 方式计算 K/D，而非 EMA 方式

    Args:
        df: 包含 OHLC 的 DataFrame
        n: RSV 周期（默认 9）
        m1: K 平滑周期（默认 3）
        m2: D 平滑周期（默认 3）

    Returns:
        DataFrame with columns: k, d, j
    """
    low_n = df["low"].rolling(window=n, min_periods=n).min()
    high_n = df["high"].rolling(window=n, min_periods=n).max()

    rsv = (df["close"] - low_n) / (high_n - low_n).replace(0, np.nan) * 100

    result = pd.DataFrame(index=df.index)
    # SMA smoothing for K and D (国内常用方式)
    result["k"] = rsv.rolling(window=m1, min_periods=m1).mean()
    result["d"] = result["k"].rolling(window=m2, min_periods=m2).mean()
    result["j"] = 3 * result["k"] - 2 * result["d"]
    return result


# ============================================================
# 布林带 (Bollinger Bands)
# ============================================================

def calc_bollinger(
    df: pd.DataFrame,
    period: int = 20,
    std_multiplier: float = 2.0,
    column: str = "close",
) -> pd.DataFrame:
    """
    布林带 (Bollinger Bands)

    公式:
        middle = SMA(period)
        upper = middle + std_multiplier * std(period)
        lower = middle - std_multiplier * std(period)
        bandwidth = (upper - lower) / middle
        %b = (close - lower) / (upper - lower)

    Args:
        df: 包含价格数据的 DataFrame
        period: 中轨周期（默认 20）
        std_multiplier: 标准差倍数（默认 2）
        column: 计算列名

    Returns:
        DataFrame with columns: upper, middle, lower, bandwidth, pct_b
    """
    result = pd.DataFrame(index=df.index)
    result["middle"] = df[column].rolling(window=period, min_periods=period).mean()
    rolling_std = df[column].rolling(window=period, min_periods=period).std()

    result["upper"] = result["middle"] + std_multiplier * rolling_std
    result["lower"] = result["middle"] - std_multiplier * rolling_std

    # 带宽
    result["bandwidth"] = (result["upper"] - result["lower"]) / result["middle"].replace(0, np.nan)

    # %b 指标（价格在带内的相对位置）
    band_diff = result["upper"] - result["lower"]
    result["pct_b"] = (df[column] - result["lower"]) / band_diff.replace(0, np.nan)

    return result


# ============================================================
# ATR (平均真实波幅)
# ============================================================

def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    平均真实波幅 (Average True Range)

    真实波幅 TR = max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close)
    )
    ATR = TR 的 period 日移动平均

    Args:
        df: 包含 OHLC 的 DataFrame
        period: 周期（默认 14）

    Returns:
        ATR 序列
    """
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing (same as RSI)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return atr


# ============================================================
# 成交量指标
# ============================================================

def calc_volume_ma(df: pd.DataFrame, period: int = 20, column: str = "volume") -> pd.Series:
    """
    成交量移动平均

    Args:
        df: 包含成交量数据的 DataFrame
        period: 周期（默认 20）
        column: 计算列名

    Returns:
        成交量 MA 序列
    """
    return df[column].rolling(window=period, min_periods=period).mean()


# ============================================================
# 批量计算
# ============================================================

def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    为 DataFrame 添加所有常用技术指标

    Args:
        df: 包含 OHLCV 的清洗后 DataFrame

    Returns:
        添加了所有指标列的 DataFrame
    """
    df = df.copy()

    # 移动平均线
    for period in [5, 10, 20, 60]:
        df[f"ma_{period}"] = calc_sma(df, period)
        df[f"ema_{period}"] = calc_ema(df, period)

    # MACD
    macd = calc_macd(df)
    df["macd_dif"] = macd["dif"]
    df["macd_dea"] = macd["dea"]
    df["macd_hist"] = macd["macd"]

    # RSI
    df["rsi_14"] = calc_rsi(df)

    # KDJ
    kdj = calc_kdj(df)
    df["kdj_k"] = kdj["k"]
    df["kdj_d"] = kdj["d"]
    df["kdj_j"] = kdj["j"]

    # 布林带
    boll = calc_bollinger(df)
    df["boll_upper"] = boll["upper"]
    df["boll_middle"] = boll["middle"]
    df["boll_lower"] = boll["lower"]

    # ATR
    df["atr_14"] = calc_atr(df)

    # 成交量均线
    df["volume_ma_20"] = calc_volume_ma(df)

    return df
