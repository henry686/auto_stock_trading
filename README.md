# Auto Stock Trading

量化交易学习项目

## 项目目标

1. 学习炒股和量化交易的基础知识
2. 逐步尝试进行量化交易
3. 以 10,000 CNY 为本金进行模拟测试

## 环境搭建

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Git Bash)
source .venv/Scripts/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

## 项目结构

```
stock_trading/
├── config/          # 配置文件（交易规则、路径等）
├── src/
│   ├── data/        # 数据获取与清洗
│   ├── indicators/  # 技术指标计算
│   ├── visualization/# 图表可视化
│   ├── strategy/    # 交易策略
│   ├── backtest/    # 回测引擎
│   ├── simulation/  # 模拟交易
│   └── utils/       # 工具模块
├── notebooks/       # Jupyter 学习笔记
├── scripts/         # CLI 脚本
├── tests/           # 单元测试
├── data/            # 数据文件（不纳入版本控制）
└── results/         # 输出结果（不纳入版本控制）
```

## 技术栈

- Python 3.14
- akshare — A 股数据获取
- backtrader — 回测引擎
- mplfinance + matplotlib — K 线图与可视化
- pandas + numpy — 数据分析
