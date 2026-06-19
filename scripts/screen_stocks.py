#!/usr/bin/env python
"""
选股筛选器 — 分层漏斗

Layer 1: 排除 ST、低价、低流动性 → ~200只
Layer 2: 精确动量验证（仅对前30只）→ ~15只
Layer 3: 行业分散 → 最终5-10只

用法:
    .venv/Scripts/python.exe scripts/screen_stocks.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
import time

# ============================================================
# 配置
# ============================================================
MIN_PRICE = 20.0
MIN_DAILY_AMOUNT = 10_0000_0000
MOMENTUM_CANDIDATES = 50      # Layer 2 精确验证的候选数
FINAL_POOL_SIZE = 15
MAX_PER_INDUSTRY = 3


def get_stock_universe():
    """获取全市场股票 (Sina源)"""
    print("[Layer 0] Fetching A-share universe...")
    df = ak.stock_zh_a_spot()

    result = pd.DataFrame()
    raw_code = df.iloc[:, 0].astype(str).str.strip()
    result["symbol"] = raw_code.str[2:]  # sh600519→600519
    result["name"] = df.iloc[:, 1].astype(str).str.strip()
    result["latest_price"] = pd.to_numeric(df.iloc[:, 2], errors="coerce")
    result["pct_change_today"] = pd.to_numeric(df.iloc[:, 3], errors="coerce")
    result["volume"] = pd.to_numeric(df.iloc[:, 11], errors="coerce")
    result["amount"] = pd.to_numeric(df.iloc[:, 12], errors="coerce")
    result["turnover_rate"] = pd.to_numeric(df.iloc[:, 5], errors="coerce")

    print(f"  Total: {len(result)} stocks")
    return result


def layer_one_filter(df):
    """
    Layer 1: 基础排除
    - 排除 ST
    - 股价 > 20
    - 日成交额 > 100亿
    """
    before = len(df)

    st = df["name"].str.contains("ST", na=False)
    print(f"  ST removed: {st.sum()}")
    df = df[~st]

    low_price = df["latest_price"] < MIN_PRICE
    print(f"  Price < {MIN_PRICE}: {low_price.sum()}")
    df = df[~low_price]

    low_amt = df["amount"] < MIN_DAILY_AMOUNT
    print(f"  Amount < {MIN_DAILY_AMOUNT/1e8:.0f}B: {low_amt.sum()}")
    df = df[~low_amt]

    # 排除无数据
    df = df[df["amount"].notna() & (df["amount"] > 0)]
    df = df.reset_index(drop=True)

    after = len(df)
    print(f"  Layer 1: {before} → {after}")
    return df


def rough_score(df):
    """
    Layer 2 粗筛：用行情数据做粗略动量评分（不拉历史数据）

    得分 = 今日涨幅排名分 + 换手率排名分
    """
    # 今日涨幅排名（百分位）
    df["pct_rank"] = df["pct_change_today"].rank(pct=True)
    # 换手率排名（百分位，代表活跃度）
    df["turnover_rank"] = df["turnover_rate"].rank(pct=True)

    # 综合得分（排除跌的）
    df["rough_score"] = (
        df["pct_rank"] * 0.6
        + df["turnover_rank"] * 0.4
    )
    # 今日下跌的扣分
    df.loc[df["pct_change_today"] < 0, "rough_score"] *= 0.5

    return df.sort_values("rough_score", ascending=False)


def fetch_momentum_batch(symbols):
    """
    批量获取精确动量数据（价格在MA60上方 + 近120日涨幅）

    对少量候选股票获取历史K线
    """
    print(f"\n[Layer 2-verify] Fetching momentum for top {len(symbols)} candidates...")
    results = {}

    for i, sym in enumerate(symbols):
        try:
            prefix = "sh" if sym.startswith("6") else "sz"
            raw = ak.stock_zh_a_daily(
                symbol=f"{prefix}{sym}",
                start_date=(datetime.now() - timedelta(days=200)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )

            if raw.empty or len(raw) < 60:
                continue

            close = pd.to_numeric(raw["close"], errors="coerce")
            volume = pd.to_numeric(raw["volume"], errors="coerce")

            # 动量: 近120日收益率
            n = min(120, len(close) - 1)
            momentum = (close.iloc[-1] - close.iloc[-n]) / close.iloc[-n]

            # MA60
            ma60 = close.rolling(60).mean().iloc[-1]
            above_ma60 = close.iloc[-1] > ma60

            # 量比
            vol_5 = volume.tail(5).mean()
            vol_20 = volume.tail(20).mean()
            vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 0

            results[sym] = {
                "momentum": momentum,
                "above_ma60": above_ma60,
                "volume_ratio": vol_ratio,
            }

            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(symbols)}...")
            time.sleep(0.3)  # 避免请求过快

        except Exception:
            continue

    print(f"  Got data for {len(results)}/{len(symbols)}")
    return results


def classify_industry(symbol, name):
    """简单行业分类"""
    code = str(symbol).strip()
    name = str(name)

    if "银行" in name: return "金融-银行"
    if "保险" in name: return "金融-保险"
    if "证券" in name or "券" in name: return "金融-券商"
    if "酒" in name: return "消费-白酒"
    if "药" in name or "医" in name or "生物" in name: return "医药"
    if "锂" in name or "电池" in name or "光伏" in name or "风电" in name: return "新能源"
    if "汽车" in name or "车" in name: return "汽车"
    if "软件" in name or "数据" in name or "AI" in name: return "科技-AI"
    if "电子" in name or "半导体" in name or "芯片" in name: return "科技-半导体"
    if "电力" in name: return "公用事业"
    if "地产" in name: return "房地产"
    if "家电" in name: return "消费-家电"
    if "食品" in name or "饮料" in name: return "消费-食品"
    if "通信" in name or "5G" in name: return "科技-通信"
    if "军工" in name or "航天" in name: return "军工"

    if code.startswith("600") or code.startswith("601"): return "上海主板"
    if code.startswith("000") or code.startswith("002"): return "深圳主板"
    if code.startswith("300"): return "创业板"
    if code.startswith("688"): return "科创板"
    return "其他"


def layer_three_diversify(df):
    """Layer 3: 行业分散"""
    df["industry"] = df.apply(lambda r: classify_industry(r["symbol"], r["name"]), axis=1)

    final = []
    ind_count = {}
    for _, row in df.iterrows():
        ind = row["industry"]
        if ind_count.get(ind, 0) < MAX_PER_INDUSTRY:
            final.append(row)
            ind_count[ind] = ind_count.get(ind, 0) + 1
        if len(final) >= FINAL_POOL_SIZE:
            break

    result = pd.DataFrame(final).reset_index(drop=True)
    print(f"\n  Layer 3 final: {len(result)} stocks, {len(ind_count)} industries")
    for ind, cnt in sorted(ind_count.items(), key=lambda x: -x[1]):
        print(f"    {ind}: {cnt}")
    return result


def print_results(df):
    """打印最终结果"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*100}")
    print(f"  FINAL CANDIDATE POOL — {now}")
    print(f"{'='*100}")
    header = f"  {'#':<4} {'Code':<8} {'Name':<10} {'Price':>8} {'Today':>7} {'Mom':>8} {'MA60':>5} {'Ind':<18}"
    print(header)
    print(f"  {'-'*80}")
    for i, (_, r) in enumerate(df.iterrows()):
        mom = r.get("momentum", np.nan)
        mom_str = f"{mom:.1%}" if not (isinstance(mom, float) and np.isnan(mom)) else "N/A"
        ma60 = "Y" if r.get("above_ma60") else "N"
        print(f"  {i+1:<4} {r['symbol']:<8} {r['name']:<10} {r['latest_price']:>8.2f} "
              f"{r['pct_change_today']:>6.1f}% {mom_str:>8} {ma60:>5} {r.get('industry',''):<18}")
    print(f"{'='*100}")


def main():
    print("=" * 100)
    print("  STOCK SCREENER — 3-Layer Funnel")
    print("=" * 100)
    print(f"  Filters: Price>{MIN_PRICE} | DailyAmount>{MIN_DAILY_AMOUNT/1e8:.0f}B | No ST")
    print()

    # Layer 0: Universe
    universe = get_stock_universe()

    # Layer 1: Basic filters
    print(f"\n--- Layer 1: Basic Filters ---")
    candidates = layer_one_filter(universe)

    # Layer 2 rough: Score by spot data
    print(f"\n--- Layer 2: Rough Ranking (spot data) ---")
    ranked = rough_score(candidates)
    print(f"  Top 5 by rough score:")
    for _, r in ranked.head(5).iterrows():
        print(f"    {r['symbol']} {r['name']}: price={r['latest_price']:.1f} "
              f"today={r['pct_change_today']:.1f}% turnover={r['turnover_rate']:.1f}%")

    # Layer 2 verify: Precise momentum for top candidates
    top_n = min(MOMENTUM_CANDIDATES, len(ranked))
    verify_symbols = ranked.head(top_n)["symbol"].tolist()
    momentum = fetch_momentum_batch(verify_symbols)

    # Merge momentum back
    ranked["momentum"] = ranked["symbol"].map(lambda s: momentum.get(s, {}).get("momentum"))
    ranked["above_ma60"] = ranked["symbol"].map(lambda s: momentum.get(s, {}).get("above_ma60", False))
    ranked["volume_ratio"] = ranked["symbol"].map(lambda s: momentum.get(s, {}).get("volume_ratio", 0))

    # Final ranking: momentum + MA60 + volume
    has_mom = ranked["momentum"].notna()
    print(f"\n  Has momentum data: {has_mom.sum()}/{len(ranked)}")

    # Sort by momentum descending, prefer above MA60
    ranked["final_score"] = (
        ranked["momentum"].fillna(-1).rank(pct=True) * 0.5
        + ranked["above_ma60"].astype(float) * 0.3
        + ranked["volume_ratio"].fillna(0).clip(0, 3).rank(pct=True) * 0.2
    )
    ranked = ranked.sort_values("final_score", ascending=False)

    # Layer 3: Diversify
    print(f"\n--- Layer 3: Industry Diversification ---")
    final_pool = layer_three_diversify(ranked)

    # Output
    print_results(final_pool)

    # Save
    output = Path("results") / f"screen_{datetime.now().strftime('%Y%m%d')}.csv"
    output.parent.mkdir(exist_ok=True)
    final_pool.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\n[Save] {output}")


if __name__ == "__main__":
    main()
