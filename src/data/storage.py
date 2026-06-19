"""
数据存储模块

支持 CSV（原始数据归档）和 Parquet（高效读写）格式。
"""
import pandas as pd
from pathlib import Path
from config.settings import DATA_RAW_DIR, DATA_PROCESSED_DIR


def save_to_csv(df: pd.DataFrame, filename: str, directory: Path = DATA_RAW_DIR) -> Path:
    """
    保存 DataFrame 为 CSV 文件

    Args:
        df: 数据
        filename: 文件名（不含路径），如 '600519.csv'
        directory: 保存目录

    Returns:
        保存的文件路径
    """
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / filename
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"[Save] CSV -> {filepath}")
    return filepath


def save_to_parquet(df: pd.DataFrame, symbol: str, directory: Path = DATA_PROCESSED_DIR) -> Path:
    """
    保存清洗后的数据为 Parquet 格式

    Args:
        df: 数据（须已包含 date 列）
        symbol: 股票代码，用作文件名
        directory: 保存目录

    Returns:
        保存的文件路径
    """
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / f"{symbol}.parquet"
    df.to_parquet(filepath, index=False)
    print(f"[Save] Parquet -> {filepath}")
    return filepath


def load_from_parquet(symbol: str, directory: Path = DATA_PROCESSED_DIR) -> pd.DataFrame:
    """
    从 Parquet 文件加载数据

    Args:
        symbol: 股票代码
        directory: 目录

    Returns:
        DataFrame
    """
    filepath = directory / f"{symbol}.parquet"
    if not filepath.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    return pd.read_parquet(filepath)


