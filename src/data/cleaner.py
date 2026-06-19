"""
数据清洗模块

将 akshare（新浪源）的原始数据标准化：
- 类型转换
- 日期排序
- 缺失值处理
- 异常值检测
- 收益率计算
"""
import pandas as pd
import numpy as np


def clean_kline_data(df: pd.DataFrame, symbol: str = "") -> pd.DataFrame:
    """
    清洗日K线数据（基于 stock_zh_a_daily 返回格式）

    akshare 返回列名已经为英文: date, open, high, low, close, volume, amount,
    outstanding_share, turnover

    处理步骤：
    1. 转换数据类型
    2. 按日期排序
    3. 检测异常值
    4. 标记停牌日

    Args:
        df: akshare 返回的原始 DataFrame
        symbol: 股票代码（用于日志）

    Returns:
        清洗后的 DataFrame
    """
    if df.empty:
        return df

    df = df.copy()

    # 1. 确保所有关键列存在
    required_cols = ["date", "open", "close", "high", "low", "volume"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"数据缺少必要列: {missing_cols}. 现有列: {df.columns.tolist()}")

    # 2. 转换日期列
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")

    # 3. 转换价格和成交量为数值类型
    numeric_cols = ["open", "close", "high", "low", "volume", "amount", "turnover"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. 按日期排序
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 5. 标记异常值：价格为 0 或为负
    for col in ["open", "close", "high", "low"]:
        if col in df.columns:
            bad_mask = df[col] <= 0
            if bad_mask.any():
                print(f"[Warning] {symbol} {col} 有 {bad_mask.sum()} 条非正价格")
                df.loc[bad_mask, col] = np.nan

    # 6. 向前填充缺失值（处理停牌日）
    if "close" in df.columns:
        df["close"] = df["close"].ffill()

    # 7. 标记可能的停牌日（价格连续相同 + 成交量为0或极低）
    df["is_suspended"] = False
    if "close" in df.columns and "volume" in df.columns:
        price_flat = df["close"].diff().abs() < 0.01
        no_volume = df["volume"] == 0
        df["is_suspended"] = price_flat & no_volume

    # 8. 成交量单位：akshare 返回的 volume 是「股」
    if "volume" in df.columns:
        df["volume_lots"] = df["volume"] / 100  # 转为手

    return df


def validate_data(df: pd.DataFrame, symbol: str = "") -> dict:
    """
    验证清洗后的数据质量

    Returns:
        dict with:
            - symbol: 股票代码
            - total_rows: 总行数
            - null_count: 缺失值统计
            - date_range: 日期范围
            - abnormal_ohlc: 价格异常行数
            - flat_days: 完全不变的天数
    """
    report = {
        "symbol": symbol,
        "total_rows": len(df),
        "null_count": df.isnull().sum().to_dict(),
        "date_range": (
            df["date"].min().strftime("%Y-%m-%d") if not df.empty else None,
            df["date"].max().strftime("%Y-%m-%d") if not df.empty else None,
        ),
        "abnormal_ohlc": 0,
        "flat_days": 0,
    }

    if df.empty:
        return report

    # 检查 OHLC 关系: high >= max(open, close) >= min(open, close) >= low
    try:
        abnormal = (
            (df["high"] < df[["open", "close"]].max(axis=1))
            | (df["low"] > df[["open", "close"]].min(axis=1))
            | (df["high"] < df["low"])
        )
        report["abnormal_ohlc"] = int(abnormal.sum())
    except Exception:
        report["abnormal_ohlc"] = -1

    # 检测完全不变的日子
    ohlc_cols = ["open", "close", "high", "low"]
    if all(c in df.columns for c in ohlc_cols):
        ohlc = df[ohlc_cols]
        report["flat_days"] = int((ohlc.diff().sum(axis=1) == 0).sum())

    return report


def add_return_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加收益率相关列

    Args:
        df: 清洗后的 DataFrame (必须包含 close)

    Returns:
        增加列: daily_return, cumulative_return, log_return
    """
    df = df.copy()
    df["daily_return"] = df["close"].pct_change()
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["cumulative_return"] = (1 + df["daily_return"]).cumprod() - 1
    return df
