"""
均线交叉策略 (Moving Average Crossover)

双均线金叉/死叉策略：
- 金叉: 短期均线上穿长期均线 → 买入
- 死叉: 短期均线下穿长期均线 → 卖出

提供两种实现：
1. pandas 向量化版本（快速验证）
2. backtrader Strategy 版本（真实回测）
"""
import pandas as pd
import numpy as np
from .base import BaseStrategy
from src.indicators.calculator import calc_sma, calc_ema


class MACrossoverStrategy(BaseStrategy):
    """
    均线交叉策略（pandas 向量化版本）

    Parameters:
        short_period: 短期均线周期（默认 5）
        long_period: 长期均线周期（默认 20）
        ma_type: 均线类型 'sma' 或 'ema'
        use_shift: 是否使用 shift 避免未来函数（默认 True）
    """

    def __init__(
        self,
        short_period: int = 5,
        long_period: int = 20,
        ma_type: str = "sma",
        use_shift: bool = True,
    ):
        super().__init__(
            name="MACrossover",
            short_period=short_period,
            long_period=long_period,
            ma_type=ma_type,
            use_shift=use_shift,
        )
        self.short_period = short_period
        self.long_period = long_period
        self.ma_type = ma_type
        self.use_shift = use_shift

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号

        信号逻辑:
        - 短期 MA > 长期 MA 且前一天短期 MA <= 长期 MA → 金叉买入 (signal=1)
        - 短期 MA < 长期 MA 且前一天短期 MA >= 长期 MA → 死叉卖出 (signal=-1)
        - 其他情况 → 持有 (signal=0)

        Args:
            df: 包含 'close' 列的 DataFrame

        Returns:
            添加了 'signal' 和均线列的 DataFrame
        """
        df = df.copy()

        # 计算均线
        ma_func = calc_sma if self.ma_type == "sma" else calc_ema
        short_ma = ma_func(df, self.short_period)
        long_ma = ma_func(df, self.long_period)

        df[f"ma_{self.short_period}"] = short_ma
        df[f"ma_{self.long_period}"] = long_ma

        # 当前关系
        short_above = short_ma > long_ma

        # 前一天关系（避免未来函数）
        if self.use_shift:
            prev_short_above = short_above.shift(1)
        else:
            prev_short_above = short_ma.shift(1) > long_ma.shift(1)

        # 填充 NaN 避免 ~ 运算符错误
        short_above = short_above.fillna(False)
        prev_short_above = prev_short_above.fillna(False)

        # 金叉: 今天短期>长期 AND 昨天短期<=长期
        golden_cross = short_above & ~prev_short_above

        # 死叉: 今天短期<长期 AND 昨天短期>=长期
        death_cross = ~short_above & prev_short_above

        # 初始化信号列
        df["signal"] = 0
        df.loc[golden_cross, "signal"] = 1
        df.loc[death_cross, "signal"] = -1

        return df

    def get_positions(self, df: pd.DataFrame) -> pd.Series:
        """
        根据信号生成持仓状态

        持仓逻辑:
        - 出现买入信号后一直持有，直到卖出信号
        - 允许连续持仓（第一个信号为买、最后一个信号为卖）

        Returns:
            持仓状态序列: 1=持仓, 0=空仓
        """
        signals = self.generate_signals(df)
        position = 0
        positions = np.zeros(len(signals), dtype=int)

        for i, sig in enumerate(signals["signal"]):
            if sig == 1:
                position = 1
            elif sig == -1:
                position = 0
            positions[i] = position

        return pd.Series(positions, index=df.index)


# ============================================================
# backtrader 版本
# ============================================================

try:
    import backtrader as bt

    class MACrossoverBT(bt.Strategy):
        """
        均线交叉策略 (backtrader 版本)

        用法:
            cerebro.addstrategy(MACrossoverBT, short_period=5, long_period=20)
        """
        params = (
            ("short_period", 5),
            ("long_period", 20),
        )

        def __init__(self):
            # 计算均线
            self.short_ma = bt.indicators.SMA(
                self.data.close, period=self.params.short_period
            )
            self.long_ma = bt.indicators.SMA(
                self.data.close, period=self.params.long_period
            )
            self.crossover = bt.indicators.CrossOver(self.short_ma, self.long_ma)

            # 记录交易
            self.order = None
            self.buy_count = 0
            self.sell_count = 0

        def log(self, txt, dt=None):
            """日志"""
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()} {txt}")

        def notify_order(self, order):
            """订单状态通知"""
            if order.status in [order.Submitted, order.Accepted]:
                return

            if order.status in [order.Completed]:
                if order.isbuy():
                    self.buy_count += 1
                    self.log(
                        f"BUY  {order.executed.size} shares @ {order.executed.price:.2f}"
                    )
                else:
                    self.sell_count += 1
                    self.log(
                        f"SELL {order.executed.size} shares @ {order.executed.price:.2f}"
                    )

            self.order = None

        def next(self):
            """每个 bar 调用一次"""

            # 检查是否有未完成订单
            if self.order:
                return

            # 金叉买入
            if self.crossover > 0:
                if not self.position:
                    self.order = self.buy()

            # 死叉卖出
            elif self.crossover < 0:
                if self.position:
                    self.order = self.sell()

except ImportError:
    MACrossoverBT = None
    print("[Warning] backtrader not available, MACrossoverBT is None")
