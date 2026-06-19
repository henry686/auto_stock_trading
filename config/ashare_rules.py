"""
A股交易规则常量

集中管理所有 A 股交易相关规则，当政策变化时只需修改此文件。
"""

# ============================================================
# 资金相关
# ============================================================
INITIAL_CAPITAL = 100_000.0  # 初始本金 (CNY)

# ============================================================
# 交易单位
# ============================================================
LOT_SIZE = 100  # 最小交易单位（1手 = 100股）

# ============================================================
# 交易费用
# ============================================================

# 印花税：卖出时征收，税率 0.05%
STAMP_DUTY_RATE = 0.0005  # 仅卖出

# 佣金：证券公司收取，费率万2.5（0.025%）
COMMISSION_RATE = 0.00025  # 双向（买入和卖出）
MIN_COMMISSION = 5.0  # 最低佣金 5 元/笔

# 过户费：中国结算收取，费率 0.001%
# 沪市（6开头）双向收取，深市（0、3开头）暂免
TRANSFER_FEE_RATE = 0.00001

# ============================================================
# 涨跌停限制
# ============================================================
PRICE_LIMIT_MAIN = 0.10  # 主板 ±10%
PRICE_LIMIT_GEM = 0.20  # 创业板(30xxxx) / 科创板(688xxx) ±20%
PRICE_LIMIT_ST = 0.05  # ST 股票 ±5%

# 可转债涨跌停（与正股不同）
PRICE_LIMIT_CB_NEW = 0.573  # 新上市转债首日最高 57.3%
PRICE_LIMIT_CB_MAIN = 0.20  # 次日起 ±20%

# ============================================================
# T+1 制度
# ============================================================
# 当天买入的股票最早只能在下一个交易日卖出
# 融券（卖空）对普通散户不可用，本项目不涉及

# ============================================================
# 交易时间（日内数据时使用）
# ============================================================
# 9:15-9:25  集合竞价
# 9:30-11:30 上午连续竞价
# 13:00-15:00 下午连续竞价
# 14:57-15:00 深市收盘集合竞价

# ============================================================
# 辅助函数
# ============================================================

def get_price_limit(symbol: str) -> float:
    """
    根据股票代码返回涨跌停幅度

    Args:
        symbol: 股票代码，如 '600519'

    Returns:
        涨跌停幅度（小数）
    """
    code = symbol.strip()
    if code.startswith("30") or code.startswith("688"):
        return PRICE_LIMIT_GEM
    elif code.startswith("8") or code.startswith("4"):
        # 新三板（北交所）：±30%
        return 0.30
    else:
        return PRICE_LIMIT_MAIN


def is_shanghai(symbol: str) -> bool:
    """判断是否为上海交易所股票（6开头）"""
    return symbol.strip().startswith("6")


def calculate_commission(amount: float) -> float:
    """
    计算佣金（双向）

    Args:
        amount: 成交金额

    Returns:
        佣金金额
    """
    return max(amount * COMMISSION_RATE, MIN_COMMISSION)


def calculate_stamp_duty(amount: float, side: str) -> float:
    """
    计算印花税（仅卖出）

    Args:
        amount: 成交金额
        side: 'buy' 或 'sell'

    Returns:
        印花税金额
    """
    if side == "sell":
        return amount * STAMP_DUTY_RATE
    return 0.0


def calculate_transfer_fee(amount: float, symbol: str) -> float:
    """
    计算过户费（沪市双向，深市暂免）

    Args:
        amount: 成交金额
        symbol: 股票代码

    Returns:
        过户费金额
    """
    if is_shanghai(symbol):
        return amount * TRANSFER_FEE_RATE
    return 0.0


def calculate_total_fee(amount: float, symbol: str, side: str) -> float:
    """
    计算总交易费用

    Args:
        amount: 成交金额
        symbol: 股票代码
        side: 'buy' 或 'sell'

    Returns:
        总费用
    """
    commission = calculate_commission(amount)
    stamp_duty = calculate_stamp_duty(amount, side)
    transfer_fee = calculate_transfer_fee(amount, symbol)
    return commission + stamp_duty + transfer_fee


def round_to_lot(quantity: int) -> int:
    """将股数向下取整到手的倍数"""
    return (quantity // LOT_SIZE) * LOT_SIZE


def max_affordable_shares(price: float, available_cash: float, symbol: str) -> int:
    """
    计算给定价格下最大可买入股数（考虑手续费）

    Args:
        price: 每股价格
        available_cash: 可用资金
        symbol: 股票代码

    Returns:
        可买入股数（已取整到手的倍数）
    """
    if price <= 0:
        return 0

    # 逐步逼近：计算买 N 股的总成本（含手续费）
    max_lots = int(available_cash / (price * LOT_SIZE))

    for lots in range(max_lots, 0, -1):
        shares = lots * LOT_SIZE
        amount = shares * price
        total_cost = amount + calculate_total_fee(amount, symbol, "buy")
        if total_cost <= available_cash:
            return shares

    return 0
