"""
A股数据获取模块

基于 akshare (新浪源 + 腾讯源) 封装，提供：
- 股票列表获取
- 历史日K线数据下载（前复权）
- 指数数据下载
- 交易日历
"""
import pandas as pd
import akshare as ak
from config.settings import DEFAULT_START_DATE, DEFAULT_END_DATE


def _to_symbol_with_prefix(symbol: str, is_index: bool = False) -> str:
    """
    给股票代码加上交易所前缀 (sh/sz/bj)

    Args:
        symbol: 原始代码
        is_index: 是否为指数（指数 000xxx 归类为上交所）
    """
    code = symbol.strip()
    if code.startswith("6") or code.startswith("9"):
        return f"sh{code}"
    elif code.startswith("000") and is_index:
        # 指数 000xxx 属于上交所
        return f"sh{code}"
    elif code.startswith("399") and is_index:
        # 指数 399xxx 属于深交所
        return f"sz{code}"
    elif code.startswith(("0", "3", "2")):
        return f"sz{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"bj{code}"
    else:
        return f"sz{code}"


def _format_date(date_str: str) -> str:
    """将 YYYY-MM-DD 转为 YYYYMMDD"""
    return date_str.replace("-", "")


def get_stock_list() -> pd.DataFrame:
    """
    获取 A 股股票列表

    Returns:
        DataFrame with columns: symbol, name, market
    """
    try:
        df = ak.stock_zh_a_spot_em()
        result = pd.DataFrame()
        result["symbol"] = df["代码"]
        result["name"] = df["名称"]
        result["market"] = result["symbol"].apply(_classify_market)
        return result
    except Exception as e:
        print(f"[Warning] 获取股票列表失败: {e}")
        raise


def fetch_daily_kline(
    symbol: str,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    下载单只股票的历史日K线数据 (新浪源)

    Args:
        symbol: 股票代码，如 '600519'
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'
        adjust: 复权方式
            - 'qfq': 前复权 (默认，推荐用于回测)
            - 'hfq': 后复权
            - '': 不复权

    Returns:
        DataFrame columns: date, open, high, low, close, volume, amount,
                           outstanding_share, turnover
    """
    try:
        prefixed = _to_symbol_with_prefix(symbol)
        start = _format_date(start_date)
        end = _format_date(end_date)

        df = ak.stock_zh_a_daily(
            symbol=prefixed,
            start_date=start,
            end_date=end,
            adjust=adjust,
        )
        if df.empty:
            print(f"[Warning] {symbol} 在 {start_date}~{end_date} 无数据")
        return df
    except Exception as e:
        print(f"[Error] 下载 {symbol} 数据失败: {e}")
        raise


def fetch_index_daily(
    index_code: str = "000300",
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
) -> pd.DataFrame:
    """
    下载指数日线数据（腾讯财经，按年分页）

    Args:
        index_code: 指数代码
            - '000300': 沪深300
            - '000001': 上证指数
            - '399001': 深证成指
            - '399006': 创业板指
        start_date: 开始日期 'YYYY-MM-DD'
        end_date: 结束日期 'YYYY-MM-DD'

    Returns:
        DataFrame columns: date, open, close, high, low, amount
    """
    import requests

    try:
        prefixed = _to_symbol_with_prefix(index_code, is_index=True)
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        all_data = []
        url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

        for year in range(start_dt.year, end_dt.year + 1):
            params = {
                "param": f"{prefixed},day,{year}-01-01,{year}-12-31,640,qfq",
            }
            r = requests.get(url, params=params, timeout=30)
            data = r.json()

            raw_data = data.get("data", {}).get(prefixed, {})
            if "day" in raw_data:
                klines = raw_data["day"]
            elif "qfqday" in raw_data:
                klines = raw_data["qfqday"]
            else:
                continue

            if not klines:
                continue

            year_df = pd.DataFrame(klines)
            if year_df.empty:
                continue

            year_df.columns = ["date", "open", "close", "high", "low", "amount"]
            all_data.append(year_df)

        if not all_data:
            print(f"[Warning] Index {index_code} has no data in {start_date}~{end_date}")
            return pd.DataFrame()

        df = pd.concat(all_data, ignore_index=True)

        for col in ["open", "close", "high", "low", "amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["date"] = pd.to_datetime(df["date"])
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)

        if df.empty:
            print(f"[Warning] Index {index_code} has no data in {start_date}~{end_date}")
        return df

    except Exception as e:
        print(f"[Error] Download index {index_code} failed: {e}")
        raise


def get_trade_date_hist(
    start_date: str = "20200101",
    end_date: str = "20251231",
) -> list:
    """
    获取 A 股交易日历

    Returns:
        交易日日期列表
    """
    try:
        df = ak.tool_trade_date_hist_sina()
        df = df[(df["trade_date"] >= start_date) & (df["trade_date"] <= end_date)]
        return df["trade_date"].tolist()
    except Exception as e:
        print(f"[Error] 获取交易日历失败: {e}")
        raise


def _classify_market(symbol: str) -> str:
    """根据股票代码判断所属市场"""
    code = str(symbol).strip()
    if code.startswith("6"):
        return "上海"
    elif code.startswith(("0", "3", "2")):
        return "深圳"
    elif code.startswith("8") or code.startswith("4"):
        return "北京"
    else:
        return "未知"
