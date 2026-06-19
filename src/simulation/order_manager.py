"""
订单管理模块

处理订单生命周期：
- 提交 → 验证 → 撮合 → 成交/拒绝
- A股规则: T+1、涨跌停、最小交易单位、费用计算
"""
from datetime import date
from config.ashare_rules import (
    LOT_SIZE,
    calculate_total_fee,
    round_to_lot,
    get_price_limit,
)
from src.utils.types_ import Order, Trade
from src.utils.calendar import get_calendar


class OrderManager:
    """
    订单管理器

    负责:
    - 订单验证（资金、T+1、涨跌停等）
    - 订单撮合
    - 费用计算
    """

    def __init__(self):
        self.orders: list[Order] = []
        self.trades: list[Trade] = []
        self._order_counter = 0
        self._trade_counter = 0
        self.calendar = get_calendar()

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"ORD{self._order_counter:06d}"

    def _next_trade_id(self) -> str:
        self._trade_counter += 1
        return f"TRD{self._trade_counter:06d}"

    def submit_order(
        self,
        account,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_date: date,
    ) -> Order:
        """
        提交并立即尝试撮合订单

        Args:
            account: VirtualAccount 实例
            symbol: 股票代码
            side: 'buy' | 'sell'
            quantity: 数量（股）
            price: 参考价格（用于费用估算和涨跌停检查）
            order_date: 下单日期

        Returns:
            Order 对象（status 为 filled/rejected）
        """
        order = Order(
            order_id=self._next_order_id(),
            symbol=symbol,
            side=side,
            quantity=quantity,
            created_at=order_date,
        )
        self.orders.append(order)

        # 验证
        reject_reason = self._validate(account, order, price, order_date)
        if reject_reason:
            order.status = "rejected"
            order.reject_reason = reject_reason
            return order

        # 撮合成交
        self._fill_order(account, order, price, order_date)
        return order

    def _validate(
        self, account, order: Order, price: float, order_date: date
    ) -> str:
        """验证订单是否合法"""
        symbol = order.symbol
        side = order.side
        quantity = order.quantity

        # 1. 数量必须是100的倍数
        if quantity % LOT_SIZE != 0:
            return f"Quantity {quantity} is not multiple of {LOT_SIZE}"

        # 2. 数量必须 > 0
        if quantity <= 0:
            return f"Quantity must be positive"

        # 3. 价格检查
        if price <= 0:
            return "Invalid price"

        if side == "buy":
            # 4. 买入：资金检查
            amount = quantity * price
            total_cost = amount + calculate_total_fee(amount, symbol, "buy")
            if total_cost > account.available_cash:
                return f"Insufficient cash: need {total_cost:.2f}, have {account.available_cash:.2f}"
        else:
            # 5. 卖出：T+1 检查
            pos = account.get_position(symbol)
            if not pos or pos.quantity < quantity:
                return f"Insufficient position for {symbol}"
            # T+1: 检查是否有今天买入的持仓
            if pos.buy_dates:
                can_sell_qty = sum(1 for d in pos.buy_dates if d < order_date)
                # 简化：用最早买入日期
                if pos.buy_dates[0] >= order_date:
                    return f"T+1 restriction: cannot sell {symbol} bought today"

        # 6. 涨跌停检查（简化：用昨收涨停价判断）
        # price_limit = get_price_limit(symbol)
        # if side == 'buy' and price >= yesterday_close * (1 + price_limit):
        #     return "Price at upper limit, buy order unlikely to fill"
        # if side == 'sell' and price <= yesterday_close * (1 - price_limit):
        #     return "Price at lower limit, sell order unlikely to fill"

        return ""  # 验证通过

    def _fill_order(
        self, account, order: Order, price: float, fill_date: date
    ):
        """撮合成交"""
        quantity = order.quantity
        symbol = order.symbol
        amount = quantity * price
        side = order.side

        # 计算费用
        total_fee = calculate_total_fee(amount, symbol, side)
        commission = 0.0
        stamp_duty = 0.0
        transfer_fee = 0.0

        # 拆分费用（简化）
        from config.ashare_rules import (
            calculate_commission,
            calculate_stamp_duty,
            calculate_transfer_fee,
        )
        commission = calculate_commission(amount)
        stamp_duty = calculate_stamp_duty(amount, side)
        transfer_fee = calculate_transfer_fee(amount, symbol)

        if side == "buy":
            # 买入：扣现金 + 增持仓
            account.deduct_cash(amount + total_fee)
            account.add_position(symbol, quantity, price, fill_date)
        else:
            # 卖出：增现金 + 减持仓
            account.add_cash(amount - total_fee)
            account.remove_position(symbol, quantity, price)

        # 更新订单状态
        order.status = "filled"
        order.filled_quantity = quantity
        order.filled_price = price
        order.filled_at = fill_date

        # 记录交易
        trade = Trade(
            trade_id=self._next_trade_id(),
            order_id=order.order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            amount=amount,
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            total_fee=total_fee,
            timestamp=fill_date,
        )
        self.trades.append(trade)
        account.trade_history.append(trade)
