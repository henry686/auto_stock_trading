"""
A股交易日历

获取和管理 A 股交易日历，用于：
- 判断某日是否为交易日
- 计算下一/上一交易日
- T+1 结算日期计算
"""
import pandas as pd
from datetime import date, timedelta
from functools import lru_cache


class TradingCalendar:
    """
    交易日历

    用法:
        cal = TradingCalendar()
        cal.is_trading_day(date.today())
        cal.next_trading_day()
    """

    def __init__(self):
        self._trading_days: set = None
        self._trading_days_list: list = None

    def _load(self):
        """延迟加载交易日历"""
        if self._trading_days is not None:
            return
        try:
            import akshare as ak
            df = ak.tool_trade_date_hist_sina()
            dates = pd.to_datetime(df["trade_date"]).dt.date.tolist()
            self._trading_days = set(dates)
            self._trading_days_list = sorted(dates)
        except Exception:
            # Fallback: 使用简单的周一到周五（不含假期）
            print("[Warning] Failed to load trading calendar, using weekday fallback")
            self._trading_days = None
            self._trading_days_list = None

    def is_trading_day(self, dt: date) -> bool:
        """判断是否为交易日"""
        self._load()
        if self._trading_days is not None:
            return dt in self._trading_days
        # Fallback: 周一到周五
        return dt.weekday() < 5

    def next_trading_day(self, dt: date = None) -> date:
        """下一个交易日"""
        if dt is None:
            dt = date.today()
        dt = dt + timedelta(days=1)
        while not self.is_trading_day(dt):
            dt = dt + timedelta(days=1)
        return dt

    def prev_trading_day(self, dt: date = None) -> date:
        """上一个交易日"""
        if dt is None:
            dt = date.today()
        dt = dt - timedelta(days=1)
        while not self.is_trading_day(dt):
            dt = dt - timedelta(days=1)
        return dt

    def trading_days_between(self, start: date, end: date) -> list:
        """获取两个日期之间的交易日列表"""
        self._load()
        if self._trading_days_list is not None:
            return [d for d in self._trading_days_list if start <= d <= end]
        # Fallback
        days = []
        current = start
        while current <= end:
            if self.is_trading_day(current):
                days.append(current)
            current += timedelta(days=1)
        return days

    def t_plus_n(self, dt: date, n: int = 1) -> date:
        """计算 T+N 结算日"""
        result = dt
        for _ in range(n):
            result = self.next_trading_day(result)
        return result


# 全局单例
_calendar_instance = None


def get_calendar() -> TradingCalendar:
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = TradingCalendar()
    return _calendar_instance
