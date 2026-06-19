"""
共享数据类型

定义模拟交易系统使用的核心数据类:
- Order: 订单
- Position: 持仓
- Trade: 已完成交易
- AccountState: 账户快照
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: str                  # 'buy' | 'sell'
    quantity: int              # 目标数量（股）
    order_type: str = "market" # 'market' | 'limit'
    limit_price: float = 0.0   # 限价（仅 limit 订单有效）
    status: str = "pending"    # 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected'
    filled_quantity: int = 0   # 已成交数量
    filled_price: float = 0.0  # 成交均价
    created_at: date = None
    filled_at: date = None
    reject_reason: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = date.today()


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int              # 持仓数量（股）
    avg_cost: float            # 平均成本价
    current_price: float = 0.0 # 当前市价
    market_value: float = 0.0  # 市值
    unrealized_pnl: float = 0.0 # 浮动盈亏
    buy_dates: list = field(default_factory=list)  # FIFO: 每笔买入的日期列表

    def update_price(self, price: float):
        """更新市价和浮动盈亏"""
        self.current_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = self.market_value - self.quantity * self.avg_cost


@dataclass
class Trade:
    """已完成的交易记录"""
    trade_id: str
    order_id: str
    symbol: str
    side: str           # 'buy' | 'sell'
    quantity: int
    price: float
    amount: float       # 成交金额
    commission: float   # 佣金
    stamp_duty: float   # 印花税
    transfer_fee: float # 过户费
    total_fee: float    # 总费用
    timestamp: date


@dataclass
class AccountState:
    """账户状态快照"""
    date: date
    cash: float                 # 可用现金
    positions: dict             # symbol -> Position
    total_value: float          # 总资产 (现金 + 持仓市值)
    total_cost: float           # 总成本
    total_pnl: float            # 总盈亏
    pnl_pct: float              # 收益率
