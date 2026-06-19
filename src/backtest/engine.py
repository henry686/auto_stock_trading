"""
回测引擎封装

基于 backtrader 的 Cerebro 封装，提供简洁的 API。
"""
import backtrader as bt
import pandas as pd
from datetime import datetime
from pathlib import Path
from config.ashare_rules import INITIAL_CAPITAL
from .ashares_broker import AShareCommission


class BacktestEngine:
    """
    回测引擎

    封装 backtrader Cerebro，简化回测流程。

    用法:
        engine = BacktestEngine(initial_cash=10000.0)
        engine.add_data(df, symbol='600519')
        engine.add_strategy(SomeStrategy, param1=10)
        results = engine.run()
        engine.print_summary()
    """

    def __init__(self, initial_cash: float = INITIAL_CAPITAL):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.broker.set_coc(True)  # Cheat-on-Close: 当日收盘价成交

        # 添加 A 股佣金方案
        comminfo = AShareCommission()
        self.cerebro.broker.addcommissioninfo(comminfo)

        # 仓位管理: 自定义 Sizer，用 95% 资金
        # 注意: A股最小1手=100股，但10k本金对于高价股买不起1手
        # 这里在回测中允许不满1手的交易（仅用于策略验证）
        class ASharesSizer(bt.Sizer):
            params = (('percents', 95),)
            def _getsizing(self, comminfo, cash, data, isbuy):
                if not isbuy:
                    pos = self.broker.getposition(data)
                    return pos.size  # 全仓卖出
                max_cash = cash * self.p.percents / 100
                size = int(max_cash / data.close[0])
                # 至少买100股，如果资金不够则买最大可买股数
                if size < 100:
                    return 0  # 买不起1手，不买
                return int(size / 100) * 100

        self.cerebro.addsizer(ASharesSizer)

        self._results = None
        self._strategies = []

    def add_data(self, df: pd.DataFrame, symbol: str = "", name: str = ""):
        """
        添加数据源

        Args:
            df: 包含 date, open, high, low, close, volume 的 DataFrame
            symbol: 股票代码
            name: 股票名称
        """
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=0,    # 第0列: date
            open=1,        # 第1列: open
            high=2,        # 第2列: high
            low=3,         # 第3列: low
            close=4,       # 第4列: close
            volume=5,      # 第5列: volume
            openinterest=-1,
        )
        self.cerebro.adddata(data, name=symbol or name)

    def add_strategy(self, strategy_class, **params):
        """添加策略"""
        self.cerebro.addstrategy(strategy_class, **params)

    def add_analyzer(self, analyzer_class, **kwargs):
        """添加分析器"""
        self.cerebro.addanalyzer(analyzer_class, **kwargs)

    def run(self) -> list:
        """
        运行回测

        Returns:
            策略实例列表
        """
        # 添加默认分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        print(f"Starting Portfolio Value: {self.cerebro.broker.getvalue():.2f}")
        self._strategies = self.cerebro.run()
        print(f"Final Portfolio Value: {self.cerebro.broker.getvalue():.2f}")
        return self._strategies

    def get_results(self) -> dict:
        """获取回测结果摘要"""
        if not self._strategies:
            return {}

        strat = self._strategies[0]
        results = {
            "initial_value": self.cerebro.broker.startingcash,
            "final_value": self.cerebro.broker.getvalue(),
            "total_return": 0.0,
            "sharpe_ratio": None,
            "max_drawdown": 0.0,
            "max_drawdown_len": 0,
            "win_rate": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
        }

        # 总收益率
        results["total_return"] = (results["final_value"] - results["initial_value"]) / results["initial_value"]

        # Sharpe 比率
        try:
            sharpe = strat.analyzers.sharpe.get_analysis()
            if sharpe:
                results["sharpe_ratio"] = sharpe.get("sharperatio", None)
        except Exception:
            pass

        # 最大回撤 (backtrader 返回百分比数值，如 24.74 表示 24.74%)
        try:
            dd = strat.analyzers.drawdown.get_analysis()
            if dd:
                raw_dd = dd.get("max", {}).get("drawdown", 0.0)
                results["max_drawdown"] = raw_dd / 100.0  # 转为小数 (0.2474)
                results["max_drawdown_len"] = dd.get("max", {}).get("len", 0)
        except Exception:
            pass

        # 交易统计
        try:
            trades = strat.analyzers.trades.get_analysis()
            results["total_trades"] = trades.get("total", {}).get("total", 0)
            results["winning_trades"] = trades.get("won", {}).get("total", 0)
            results["losing_trades"] = trades.get("lost", {}).get("total", 0)

            total_closed = results["winning_trades"] + results["losing_trades"]
            if total_closed > 0:
                results["win_rate"] = results["winning_trades"] / total_closed
        except Exception:
            pass

        return results

    def plot(self, **kwargs):
        """绘制回测结果"""
        self.cerebro.plot(**kwargs)

    def print_summary(self):
        """打印回测摘要"""
        results = self.get_results()
        print("\n" + "=" * 60)
        print("  BACKTEST RESULTS")
        print("=" * 60)
        print(f"  Initial Capital:   {results['initial_value']:>12,.2f} CNY")
        print(f"  Final Value:       {results['final_value']:>12,.2f} CNY")
        print(f"  Total Return:      {results['total_return']:>11.2%}")
        if results["sharpe_ratio"] is not None:
            print(f"  Sharpe Ratio:      {results['sharpe_ratio']:>12.2f}")
        print(f"  Max Drawdown:      {results['max_drawdown']:>11.2%}")
        print(f"  Max DD Days:       {results['max_drawdown_len']:>12}")
        print(f"  Total Trades:      {results['total_trades']:>12}")
        print(f"  Win Rate:          {results['win_rate']:>11.2%}")
        print(f"  Winning/Losing:    {results['winning_trades']}/{results['losing_trades']}")
        print("=" * 60)

    def get_equity_curve(self) -> pd.DataFrame:
        """获取权益曲线"""
        if not self._strategies:
            return pd.DataFrame()

        strat = self._strategies[0]
        equity = []
        for analyzer in strat.analyzers:
            try:
                analysis = analyzer.get_analysis()
                if "rtn" in str(analysis):
                    continue
            except Exception:
                pass

        return pd.DataFrame()
