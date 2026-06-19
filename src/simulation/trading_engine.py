"""
模拟交易引擎

逐日循环模拟交易：
for each trading day:
    1. 获取当日价格
    2. 更新持仓市值
    3. 策略生成信号
    4. 提交订单
    5. 撮合成交
    6. 记录账户快照
"""
import pandas as pd
from datetime import date, timedelta
from src.utils.types_ import AccountState
from src.utils.calendar import get_calendar
from src.simulation.account import VirtualAccount
from src.simulation.order_manager import OrderManager
from src.strategy.ma_crossover import MACrossoverStrategy
from config.ashare_rules import INITIAL_CAPITAL, LOT_SIZE, calculate_total_fee


class SimulationEngine:
    """
    模拟交易引擎

    用法:
        engine = SimulationEngine(initial_cash=10000.0)
        engine.load_data('600036', df)
        engine.add_strategy(MACrossoverStrategy(short_period=5, long_period=20))
        report = engine.run()
    """

    def __init__(self, initial_cash: float = INITIAL_CAPITAL):
        self.account = VirtualAccount(initial_cash)
        self.order_manager = OrderManager()
        self.calendar = get_calendar()
        self.strategy = None
        self.data: dict[str, pd.DataFrame] = {}  # symbol -> DataFrame
        self.current_day: date = None
        self.report: dict = {}

    def load_data(self, symbol: str, df: pd.DataFrame):
        """
        加载股票历史数据

        Args:
            symbol: 股票代码
            df: 包含 date, open, high, low, close, volume 的 DataFrame
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df.sort_values("date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        self.data[symbol] = df

    def add_strategy(self, strategy):
        """添加交易策略"""
        self.strategy = strategy

    def run(self, start_date: str = None, end_date: str = None) -> dict:
        """
        运行模拟交易

        Args:
            start_date: 开始日期 'YYYY-MM-DD'（默认使用数据起始日）
            end_date: 结束日期 'YYYY-MM-DD'（默认使用数据结束日）

        Returns:
            报告 dict
        """
        if not self.data:
            print("[Error] No data loaded")
            return {}

        if not self.strategy:
            print("[Error] No strategy added")
            return {}

        # 取所有数据的日期范围
        all_dates = []
        for symbol, df in self.data.items():
            all_dates.extend(df["date"].tolist())
        all_dates = sorted(set(all_dates))

        if start_date:
            all_dates = [d for d in all_dates if d >= pd.Timestamp(start_date)]
        if end_date:
            all_dates = [d for d in all_dates if d <= pd.Timestamp(end_date)]

        print(f"\n{'='*60}")
        print(f"  Simulation Starting")
        print(f"  Strategy: {self.strategy}")
        print(f"  Initial Cash: {self.account.initial_cash:,.2f} CNY")
        print(f"  Date Range: {all_dates[0].date()} ~ {all_dates[-1].date()}")
        print(f"  Trading Days: {len(all_dates)}")
        print(f"{'='*60}")

        # 逐日循环
        for i, dt in enumerate(all_dates):
            self.current_day = dt.date() if hasattr(dt, "date") else dt

            # 获取当日价格
            prices = {}
            day_data = {}
            for symbol, df in self.data.items():
                row = df[df["date"] == dt]
                if not row.empty:
                    prices[symbol] = row["close"].iloc[0]
                    day_data[symbol] = row.iloc[0]

            if not prices:
                continue

            # 更新持仓市值
            self.account.update_position_prices(prices)

            # 策略生成信号（使用截止到当日的所有历史数据）
            for symbol in day_data:
                symbol_df = self.data[symbol]
                hist_data = symbol_df[symbol_df["date"] <= dt].copy()

                if len(hist_data) < 30:  # 需要足够的历史数据
                    continue

                # 生成信号
                signals = self.strategy.generate_signals(hist_data)
                if signals.empty:
                    continue

                latest_signal = signals["signal"].iloc[-1]

                if latest_signal == 1:  # 买入信号
                    price = prices[symbol]
                    # 计算可买数量
                    from config.ashare_rules import max_affordable_shares
                    max_shares = max_affordable_shares(
                        price, self.account.available_cash, symbol
                    )
                    if max_shares > 0:
                        self.order_manager.submit_order(
                            self.account,
                            symbol,
                            "buy",
                            max_shares,
                            price,
                            self.current_day,
                        )

                elif latest_signal == -1:  # 卖出信号
                    pos = self.account.get_position(symbol)
                    if pos and pos.quantity > 0:
                        self.order_manager.submit_order(
                            self.account,
                            symbol,
                            "sell",
                            pos.quantity,  # 全仓卖出
                            prices[symbol],
                            self.current_day,
                        )

            # 记录账户快照
            self.account.record_snapshot(self.current_day, prices)

            # 定期输出
            if (i + 1) % 100 == 0 or i == 0:
                summary = self.account.summary(prices)
                print(f"  [{self.current_day}] {summary}")

        # 最终状态
        print(f"\n{'='*60}")
        print(f"  Simulation Complete")
        print(f"  {self.account.summary()}")
        print(f"  Trades: {len(self.order_manager.trades)}")
        print(f"{'='*60}")

        return self._generate_report()

    def _generate_report(self) -> dict:
        """生成模拟报告"""
        snapshots = self.account.daily_snapshots
        if not snapshots:
            return {}

        equity = pd.Series(
            [s.total_value for s in snapshots],
            index=pd.DatetimeIndex([s.date for s in snapshots]),
        )

        # 计算指标
        from src.backtest.analyzers import calculate_all_metrics

        trades_dicts = [
            {
                "pnl": t.amount * (1 if t.side == "sell" else -1),
                "fee": t.total_fee,
            }
            for t in self.order_manager.trades
        ]

        metrics = calculate_all_metrics(equity, trades_dicts)

        self.report = {
            "initial_cash": self.account.initial_cash,
            "final_value": snapshots[-1].total_value,
            "total_return": (snapshots[-1].total_value - self.account.initial_cash)
            / self.account.initial_cash,
            "total_trades": len(self.order_manager.trades),
            "metrics": metrics,
            "equity_curve": equity,
            "snapshots": snapshots,
            "trades": self.order_manager.trades,
        }
        return self.report

    def get_equity_curve(self) -> pd.Series:
        """获取权益曲线"""
        if self.report:
            return self.report.get("equity_curve", pd.Series())
        snapshots = self.account.daily_snapshots
        if not snapshots:
            return pd.Series()
        return pd.Series(
            [s.total_value for s in snapshots],
            index=pd.DatetimeIndex([s.date for s in snapshots]),
        )

    def print_summary(self):
        """打印模拟交易摘要"""
        if not self.report:
            self._generate_report()

        print("\n" + "=" * 60)
        print("  SIMULATION TRADING REPORT")
        print("=" * 60)
        print(f"  Initial Cash:     {self.account.initial_cash:>12,.2f} CNY")
        final = self.report.get("final_value", 0)
        print(f"  Final Value:      {final:>12,.2f} CNY")
        ret = self.report.get("total_return", 0)
        print(f"  Total Return:     {ret:>11.2%}")
        print(f"  Total Trades:     {self.report.get('total_trades', 0):>12}")
        print(f"  Trade History:    {len(self.order_manager.trades)} completed")

        # 持仓
        if self.account.positions:
            print(f"\n  --- Current Positions ---")
            for sym, pos in self.account.positions.items():
                print(f"  {sym}: {pos.quantity} shares, "
                      f"avg cost={pos.avg_cost:.2f}, "
                      f"P&L={pos.unrealized_pnl:+.2f}")

        # 最近5笔交易
        if self.order_manager.trades:
            print(f"\n  --- Recent Trades ---")
            for t in self.order_manager.trades[-5:]:
                print(f"  {t.timestamp} {t.side.upper():4s} {t.symbol} "
                      f"{t.quantity}@{t.price:.2f} | "
                      f"amt={t.amount:,.0f} fee={t.total_fee:.2f}")

        print("=" * 60)
