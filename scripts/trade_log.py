#!/usr/bin/env python
"""交易日志 — 记录每次操作，跟踪持仓"""
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

# 加载上次日志
if LOG_FILE.exists():
    log = json.load(open(LOG_FILE, encoding="utf-8"))
else:
    log = {"cash": CASH, "total_invested": 0, "positions": {}, "history": []}

# 获取信号
signals = {}
for sym, nam in STOCKS + [INDEX]:
    df = load_from_parquet(sym)
    sig_df = strategy.generate_signals(df)
    sig = int(sig_df.iloc[-1]["signal"])
    price = sig_df.iloc[-1]["close"]
    signals[sym] = {"name": nam, "signal": sig, "price": price}

# 计算可分配资金
buy_list = [s for s, v in signals.items() if v["signal"] == 1]
per_buy = CASH / max(len(buy_list), 1)
if log["positions"]:
    # 如果已有持仓，用实际的剩余现金
    invested = sum(p["cost"] for p in log["positions"].values())
    per_buy = (CASH - invested) / max(len(buy_list), 1)

today = datetime.now().strftime("%Y-%m-%d")
actions = []
total_spent = 0

for sym, info in signals.items():
    sig = info["signal"]
    name = info["name"]
    price = info["price"]
    current_pos = log["positions"].get(sym)

    if sig == 1:  # BUY
        if current_pos:
            action = f"HOLD (already holding)"
        elif sym == "000300":
            log["positions"][sym] = {"name": name, "shares": 0, "cost": per_buy, "price": price, "date": today}
            total_spent += per_buy
            action = f"BUY  index allocation = {per_buy:,.0f} CNY"
        else:
            shares = int(per_buy / price / 100) * 100
            if shares > 0:
                cost = shares * price
                log["positions"][sym] = {"name": name, "shares": shares, "cost": cost, "price": price, "date": today}
                total_spent += cost
                action = f"BUY  {shares} shares @ {price:.2f} = {cost:,.0f} CNY"
            else:
                action = f"SKIP (insufficient cash for 1 lot)"

    elif sig == -1:  # SELL
        if current_pos:
            action = f"SELL {current_pos['shares']} shares (was {current_pos['cost']:,.0f} CNY)"
            log["positions"].pop(sym)
        else:
            action = "— (not holding)"

    else:  # HOLD
        if current_pos:
            value = current_pos["shares"] * price if current_pos["shares"] > 0 else current_pos["cost"]
            pnl = value - current_pos["cost"]
            action = f"HOLD  current value: {value:,.0f} CNY  (P&L: {pnl:+,.0f})"
        else:
            action = "— (no position)"

    print(f"  {sym} {name:<8} {'BUY' if sig==1 else 'SELL' if sig==-1 else 'HOLD':>5}  {action}")

# 计算总资产
total_value = total_spent  # 今天新买的
for sym, pos in log["positions"].items():
    if pos["date"] != today:
        total_value += pos.get("cost", 0)  # 旧的按成本计

# 保存
log["history"].append({"date": today, "actions": actions, "cash": CASH})
log["last_update"] = today
json.dump(log, open(LOG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"\n  Portfolio as of {today}:")
print(f"  Positions: {len(log['positions'])} assets")
for sym, pos in log["positions"].items():
    print(f"    {sym} {pos['name']}: {pos.get('shares','index')} {'shares' if pos.get('shares',0)>0 else ''} @ {pos['price']:.2f} = {pos['cost']:,.0f} CNY")
