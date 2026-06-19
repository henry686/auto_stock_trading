"""
全局配置 — 路径、观察池、可视化参数
交易规则常量请见 ashare_rules.py
"""
from pathlib import Path
from .ashare_rules import INITIAL_CAPITAL  # 单一数据源

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"

# 结果输出目录
RESULTS_DIR = PROJECT_ROOT / "results"
CHARTS_DIR = RESULTS_DIR / "charts"
REPORTS_DIR = RESULTS_DIR / "reports"

# 默认日期范围
DEFAULT_START_DATE = "2022-01-01"
DEFAULT_END_DATE = "2026-12-31"

# 观察池 — 2026-06 选股
WATCHLIST = [
    ("600036", "招商银行"),   # 金融-银行
    ("600030", "中信证券"),   # 金融-券商
    ("600276", "恒瑞医药"),   # 医药
    ("002460", "赣锋锂业"),   # 新能源-锂
    ("601633", "长城汽车"),   # 汽车
    ("600570", "恒生电子"),   # 科技-金融软件
    ("600900", "长江电力"),   # 公用事业-电力
    ("600809", "山西汾酒"),   # 消费-白酒
    ("000300", "沪深300"),    # 指数择时
]

# 仅用于图表参考的高价股（不参与回测）
BENCHMARK_STOCKS = [
    ("600519", "贵州茅台"),
]

# 基准指数
BENCHMARK_INDEX = "000300"  # 沪深300

# 数据源配置
# akshare 无需 token，免费使用

# matplotlib 中文配置
PLOT_STYLE = {
    "font.sans-serif": ["SimHei", "Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
}

# 日志配置
LOG_LEVEL = "INFO"
LOG_FILE = PROJECT_ROOT / "app.log"
