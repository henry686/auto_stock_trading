"""
全局配置
"""
from pathlib import Path

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

# 初始资金 (CNY)
INITIAL_CAPITAL = 100_000.0

# 精选观察股票列表
# 选择标准: 10万本金能买至少1手(100股), 行业分散, 流动性好
WATCHLIST = [
    ("600036", "招商银行"),   # 金融-银行
    ("002594", "比亚迪"),     # 新能源-汽车
    ("300750", "宁德时代"),   # 新能源-电池
    ("601318", "中国平安"),   # 金融-保险
    ("000858", "五粮液"),     # 消费-白酒
    ("600900", "长江电力"),   # 公用事业-电力
    ("002415", "海康威视"),   # 科技-安防AI
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
