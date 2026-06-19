#!/usr/bin/env python
"""
批量下载精选股票和指数数据

用法:
    cd d:/xiaotian/workspace/vscode/stock_trading
    .venv/Scripts/python.exe scripts/fetch_all.py

下载内容:
    - WATCHLIST 中的精选股票（日K线，前复权）
    - 沪深300 指数数据
"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import WATCHLIST, BENCHMARK_INDEX, DEFAULT_START_DATE, DEFAULT_END_DATE
from src.data.fetcher import fetch_daily_kline, fetch_index_daily
from src.data.cleaner import clean_kline_data, validate_data, add_return_columns
from src.data.storage import save_to_csv, save_to_parquet
import pandas as pd


def download_stock(symbol: str, name: str) -> pd.DataFrame:
    """下载并清洗单只股票数据"""
    print(f"\n{'='*50}")
    print(f"Downloading: {symbol} {name}")
    print(f"Date range: {DEFAULT_START_DATE} ~ {DEFAULT_END_DATE}")

    # 1. 下载原始数据
    raw_df = fetch_daily_kline(symbol, DEFAULT_START_DATE, DEFAULT_END_DATE, adjust="qfq")
    print(f"  Raw data: {len(raw_df)} rows")

    # 2. 保存原始 CSV
    save_to_csv(raw_df, f"{symbol}_{name}.csv")

    # 3. 清洗数据
    clean_df = clean_kline_data(raw_df, symbol)

    # 4. 添加收益率列
    clean_df = add_return_columns(clean_df)

    # 5. 验证数据
    report = validate_data(clean_df, symbol)
    print(f"  Cleaned: {report['total_rows']} rows")
    print(f"  Date range: {report['date_range'][0]} ~ {report['date_range'][1]}")
    print(f"  Abnormal OHLC: {report['abnormal_ohlc']} rows")
    print(f"  Suspended days: {report['flat_days']} rows")

    # 6. 保存清洗后的 Parquet
    save_to_parquet(clean_df, symbol)
    print(f"  [OK] {symbol} {name} done")

    return clean_df


def download_benchmark() -> pd.DataFrame:
    """下载沪深300指数数据"""
    print(f"\n{'='*50}")
    print(f"Downloading: CSI 300 Index ({BENCHMARK_INDEX})")
    print(f"Date range: {DEFAULT_START_DATE} ~ {DEFAULT_END_DATE}")

    df = fetch_index_daily(BENCHMARK_INDEX, DEFAULT_START_DATE, DEFAULT_END_DATE)
    print(f"  Raw data: {len(df)} rows")

    # 保存
    save_to_csv(df, f"index_{BENCHMARK_INDEX}.csv")
    save_to_parquet(df, BENCHMARK_INDEX)
    print(f"  [OK] CSI 300 Index done")

    return df


def main():
    print("=" * 60)
    print("   A-Share Data Batch Downloader")
    print("=" * 60)
    print(f"   Stocks: {len(WATCHLIST)}")
    print(f"   Date: {DEFAULT_START_DATE} ~ {DEFAULT_END_DATE}")
    print(f"   Adjust: Forward-adjusted (qfq)")

    # 下载股票数据
    results = {}
    for symbol, name in WATCHLIST:
        try:
            df = download_stock(symbol, name)
            results[symbol] = {"name": name, "rows": len(df), "ok": True}
        except Exception as e:
            print(f"  [FAIL] {symbol} {name}: {e}")
            results[symbol] = {"name": name, "rows": 0, "ok": False}

    # 下载指数数据
    try:
        benchmark_df = download_benchmark()
    except Exception as e:
        print(f"  [FAIL] CSI 300: {e}")
        benchmark_df = None

    # 汇总报告
    print(f"\n{'='*60}")
    print("   Summary")
    print(f"{'='*60}")
    for symbol, info in results.items():
        status = "OK" if info["ok"] else "FAIL"
        print(f"  [{status}] {symbol} {info['name']}: {info['rows']} rows")

    if benchmark_df is not None:
        print(f"  [OK]  CSI 300 ({BENCHMARK_INDEX}): {len(benchmark_df)} rows")

    print(f"\nAll data saved to data/ directory")


if __name__ == "__main__":
    main()
