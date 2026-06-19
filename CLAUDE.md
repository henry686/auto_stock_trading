# Auto Stock Trading

量化交易学习项目。用 Python + akshare + backtrader 做 A 股策略研究。

## 常用命令

```bash
# 环境
source .venv/Scripts/activate

# 更新数据
python scripts/fetch_all.py

# 周一信号面板（最重要）
python scripts/signal_panel.py

# 回测 & 模拟
python scripts/run_backtest.py --symbol 600036 --cash 100000
python scripts/run_simulation.py --symbol 600036 --cash 100000

# 周度跟踪
python scripts/weekly_tracker.py

# 10万真实投资测试
python scripts/portfolio_test.py
```

## 项目结构

```
config/          — 交易规则 + 全局设置
src/data/        — 数据获取(akshare) + 清洗 + 存储
src/indicators/  — 技术指标(手写, 不依赖 pandas-ta)
src/strategy/    — 策略(MACrossover)
src/backtest/    — 回测引擎(backtrader)
src/simulation/  — 自建模拟交易引擎
src/visualization/ — K线图 + 指标图
scripts/         — 可执行脚本
notebooks/       — Jupyter 学习笔记
```

## 当前组合 (2026-06)

8 只个股 + 沪深300: 招商银行/中信证券/恒瑞医药/赣锋锂业/长城汽车/恒生电子/长江电力/山西汾酒/沪深300

策略: MA5/20 金叉买死叉卖，100,000 本金等权分配。

## 关键规则

- 10 行能写完不写 20 行
- 不知道就说不知道
- 每次改动后跑验证
- 数据不在 data/ 和 results/ 中（gitignore）
