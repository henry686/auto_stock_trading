"""
虚拟账户模块

管理现金和持仓，初始资金 10,000 CNY。
"""
from datetime import date
from collections import defaultdict
from src.utils.types_ import Position, AccountState
from config.ashare_rules import INITIAL_CAPITAL


class VirtualAccount:
    """
    虚拟交易账户

    管理:
    - 现金余额
    - 持仓列表
    - 交易历史
    - 账户状态快照
    """

    def __init__(self, initial_cash: float = INITIAL_CAPITAL):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.trade_history: list = []
        self.daily_snapshots: list[AccountState] = []
        self._frozen_cash: float = 0.0  # 冻结资金（挂单中）

    @property
    def available_cash(self) -> float:
        """可用资金"""
        return self.cash - self._frozen_cash

    def get_position(self, symbol: str) -> Position:
        """获取某只股票的持仓"""
        return self.positions.get(symbol)

    def get_total_value(self, current_prices: dict[str, float]) -> float:
        """
        计算总资产

        Args:
            current_prices: {symbol: current_price}
        """
        total = self.cash
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.current_price)
            total += pos.quantity * price
        return total

    def get_total_pnl(self, current_prices: dict[str, float]) -> float:
        """总盈亏"""
        return self.get_total_value(current_prices) - self.initial_cash

    def update_position_prices(self, current_prices: dict[str, float]):
        """更新所有持仓的市价"""
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                pos.update_price(current_prices[symbol])

    def record_snapshot(self, dt: date, current_prices: dict[str, float]):
        """记录账户状态快照"""
        total_value = self.get_total_value(current_prices)
        state = AccountState(
            date=dt,
            cash=self.cash,
            positions={s: Position(
                symbol=p.symbol,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                current_price=p.current_price,
                market_value=p.market_value,
                unrealized_pnl=p.unrealized_pnl,
            ) for s, p in self.positions.items()},
            total_value=total_value,
            total_cost=self.initial_cash,
            total_pnl=total_value - self.initial_cash,
            pnl_pct=(total_value - self.initial_cash) / self.initial_cash,
        )
        self.daily_snapshots.append(state)

    def freeze_cash(self, amount: float):
        """冻结资金（挂单时）"""
        self._frozen_cash += amount

    def unfreeze_cash(self, amount: float):
        """解冻资金"""
        self._frozen_cash = max(0, self._frozen_cash - amount)

    def deduct_cash(self, amount: float):
        """扣除现金（成交时）"""
        self.cash -= amount

    def add_cash(self, amount: float):
        """增加现金（卖出成交时）"""
        self.cash += amount

    def add_position(self, symbol: str, quantity: int, price: float, buy_date: date):
        """增加持仓"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_cost = pos.avg_cost * pos.quantity + price * quantity
            pos.quantity += quantity
            pos.avg_cost = total_cost / pos.quantity if pos.quantity > 0 else 0
            pos.buy_dates.append(buy_date)
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=price,
                current_price=price,
                market_value=quantity * price,
                buy_dates=[buy_date],
            )

    def remove_position(self, symbol: str, quantity: int, price: float):
        """
        减少持仓（FIFO: 先买入的先卖出）

        Args:
            symbol: 股票代码
            quantity: 卖出数量
            price: 卖出价格

        Returns:
            realized_pnl: 已实现盈亏
        """
        pos = self.positions[symbol]
        if quantity > pos.quantity:
            raise ValueError(f"Insufficient position: {pos.quantity} < {quantity}")

        # FIFO: 最早买入的优先卖出
        buy_dates = pos.buy_dates

        # 计算已实现盈亏
        realized_pnl = (price - pos.avg_cost) * quantity

        pos.quantity -= quantity
        if pos.quantity <= 0:
            del self.positions[symbol]
        else:
            # 移除最早买入的记录
            remaining = quantity
            while remaining > 0 and buy_dates:
                buy_dates.pop(0)  # FIFO: 移除最早的
                remaining -= 1
            # 简化：实际应按批次计算

        return realized_pnl

    def summary(self, current_prices: dict[str, float] = None) -> str:
        """账户摘要"""
        if current_prices is None:
            current_prices = {}
        total_value = self.get_total_value(current_prices)
        total_pnl = total_value - self.initial_cash
        return (
            f"Cash: {self.cash:,.2f} | "
            f"Positions: {len(self.positions)} | "
            f"Total Value: {total_value:,.2f} | "
            f"P&L: {total_pnl:+,.2f} ({total_pnl/self.initial_cash:+.2%})"
        )
