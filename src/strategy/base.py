"""
交易策略抽象基类

所有策略必须实现 generate_signals 方法。
"""
from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """
    策略基类

    子类需要实现:
    - generate_signals(df): 生成交易信号
    """

    def __init__(self, name: str = "BaseStrategy", **params):
        self.name = name
        self.params = params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据历史数据生成交易信号

        Args:
            df: 包含 OHLCV 和指标列的 DataFrame

        Returns:
            添加了 'signal' 列的 DataFrame:
                1  = 买入信号
                -1 = 卖出信号
                0  = 持有/无操作
        """
        pass

    def __repr__(self):
        params_str = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.name}({params_str})"
