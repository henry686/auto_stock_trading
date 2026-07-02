#!/usr/bin/env python
"""交易日志 — 记录每次操作，跟踪持仓和现金"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime
from src.strategy.ma_crossover import MACrossoverStrategy
from src.data.storage import load_from_parquet

LOG_FILE = Path("results/trade_log.json")
CASH = 100_000

STOCKS = [("600036","招商银行"), ("600030","中信证券"), ("600276","恒瑞医药"),
          ("002460","赣锋锂业"), ("601633","长城汽车"), ("600570","恒生电子"),
          ("600900","长江电力"), ("600809","山西汾酒")]
INDEX = ("000300", "沪深300")

strategy = MACrossoverStrategy(short_period=5, long_period=20)

# 加载日志（或初始化）
if LOG_FILE.exists():
    log = json.load(open(LOG_FILE, encoding="utf-8"))
    if "available_cash" not in log:
        log["available_cash"] = CASH
else:
    log = {"available_cash": CASH, "positions": {}, "history": []}

available = log["available_cash"]

# 获取今日信号
signals = {}
for sym, nam in STOCKS + [INDEX]:
    df = load_from_parquet(sym)
    sig_df = strategy.generate_signals(df)
    sig = int(sig_df.iloc[-1]["signal"])
    price = sig_df.iloc[-1]["close"]
    signals[sym] = {"name": nam, "signal": sig, "price": price}

# 先处理卖出（释放现金）
today = datetime.now().strftime("%Y-%m-%d")
for sym, info in signals.items():
    if info["signal"] == -1:
        pos = log["positions"].get(sym)
        if pos:
            proceeds = pos["shares"] * info["price"] if pos["shares"] > 0 else pos["cost"]
            available += proceeds
            print(f"  SELL {sym} {info['name']:<8} {pos['shares']} shares → {proceeds:,.0f} CNY")
            log["positions"].pop(sym)

# 计算新买入的资金分配
new_buys = [s for s, v in signals.items()
            if v["signal"] == 1 and s not in log["positions"]]
per_buy = available / max(len(new_buys), 1) if new_buys else 0

# 处理买入
for sym in new_buys:
    info = signals[sym]
    price, name = info["price"], info["name"]

    if sym == "000300":
        cost = per_buy
        log["positions"][sym] = {"name": name, "shares": 0, "cost": cost, "price": price, "date": today}
        available -= cost
        print(f"  BUY  {sym} {name:<8} index allocation = {cost:,.0f} CNY")
    else:
        shares = int(per_buy / price / 100) * 100
        if shares > 0:
            cost = shares * price
            log["positions"][sym] = {"name": name, "shares": shares, "cost": cost, "price": price, "date": today}
            available -= cost
            print(f"  BUY  {sym} {name:<8} {shares} shares @ {price:.2f} = {cost:,.0f} CNY")
        else:
            print(f"  SKIP {sym} {name:<8} cash {per_buy:,.0f} < 1 lot ({price*100:,.0f})")

# 现有持仓：只报状态
for sym, pos in log["positions"].items():
    info = signals.get(sym, {})
    price = info.get("price", pos["price"])
    shares = pos["shares"]
    if shares > 0:
        value = shares * price
        pnl = value - pos["cost"]
        print(f"  HOLD {sym} {pos['name']:<8} {shares} shares  value={value:,.0f}  P&L={pnl:+,.0f}")
    else:
        print(f"  HOLD {sym} {pos['name']:<8} index alloc = {pos['cost']:,.0f} CNY")

# 保存
log["available_cash"] = available
log["history"].append({"date": today, "positions": dict(log["positions"]), "available_cash": available})
log["last_update"] = today

# 计算总资产
total = available
for pos in log["positions"].values():
    info = signals.get(pos.get("sym", ""), {})
    price = info.get("price", pos["price"]) if info else pos["price"]
    total += pos["shares"] * price if pos["shares"] > 0 else pos["cost"]

json.dump(log, open(LOG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"\n  Portfolio {today}")
print(f"  Available cash: {available:,.0f} CNY")
print(f"  Total assets:   {total:,.0f} CNY")
print(f"  Return:         {(total - CASH) / CASH:+.1%}")
