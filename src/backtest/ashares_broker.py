"""
A股交易费用模型

自定义 backtrader 佣金方案，实现：
- 佣金：万2.5（最低5元），双向
- 印花税：0.05%，仅卖出
- 过户费：0.001%，仅沪市（6开头），双向
- T+1 卖出限制（通过 observer + 策略配合）
"""
import backtrader as bt
from config.ashare_rules import (
    COMMISSION_RATE,
    MIN_COMMISSION,
    STAMP_DUTY_RATE,
    TRANSFER_FEE_RATE,
)


class AShareCommission(bt.CommInfoBase):
    """
    A股佣金方案

    覆盖 backtrader 的默认佣金计算：
    - 买入: 佣金 + 过户费(沪市)
    - 卖出: 佣金 + 印花税 + 过户费(沪市)
    """

    params = (
        ("commission", COMMISSION_RATE),  # 万2.5
        ("stamp_duty", STAMP_DUTY_RATE),  # 0.05%
        ("transfer_fee", TRANSFER_FEE_RATE),  # 0.001%
        ("min_commission", MIN_COMMISSION),  # 最低5元
        ("stocklike", True),
        ("commtype", bt.CommInfoBase.COMM_PERC),
        ("percabs", False),  # 不要自动取绝对值
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        计算单边佣金

        Args:
            size: 交易数量（股）
            price: 成交价格
            pseudoexec: 是否模拟执行

        Returns:
            佣金金额
        """
        amount = abs(size) * price
        commission = amount * self.p.commission
        return max(commission, self.p.min_commission)

    def get_stamp_duty(self, size, price):
        """计算印花税（仅卖出）"""
        if size < 0:  # 卖出
            return abs(size) * price * self.p.stamp_duty
        return 0.0

    def get_transfer_fee(self, size, price, symbol=""):
        """计算过户费（沪市双向）"""
        if symbol and str(symbol).startswith("6"):
            return abs(size) * price * self.p.transfer_fee
        return 0.0

    def get_total_fee(self, size, price, symbol=""):
        """计算总费用"""
        commission = self._getcommission(size, price, pseudoexec=False)
        stamp = self.get_stamp_duty(size, price)
        transfer = self.get_transfer_fee(size, price, symbol)
        return commission + stamp + transfer


class T1Observer(bt.Observer):
    """
    T+1 卖出限制观察器

    记录当天是否买入，用于阻止当天卖出。
    注意：backtrader 本身不强制执行 T+1，需要通过策略配合使用。

    推荐做法：在策略的 next() 中检查此 observer 的值，
    如果当天有新买入，则跳过卖出信号。
    """

    lines = ("can_sell",)
    plotinfo = dict(plot=False)

    def next(self):
        # 检查是否有新买入（今天买入的不能在今天卖出）
        # 简化处理：如果持仓量的变化是增加，说明今天有买入
        pos = self._owner.getposition(self.data)
        if len(self.data) > 0:
            # 比较今天和昨天的持仓
            today_size = pos.size
            yesterday_size = getattr(self, "_yesterday_size", 0)

            if today_size > yesterday_size:
                # 今天有净买入 -> T+1 限制明天才能卖出
                self.lines.can_sell[0] = 0
            else:
                self.lines.can_sell[0] = 1

            self._yesterday_size = today_size
        else:
            self.lines.can_sell[0] = 1
