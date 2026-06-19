"""
回测报告模块

生成回测报告：控制台输出、JSON 导出。
"""
import json
from pathlib import Path
from datetime import datetime
from config.settings import REPORTS_DIR


def generate_report(results: dict, metadata: dict = None) -> dict:
    """
    生成完整回测报告

    Args:
        results: 绩效指标 dict
        metadata: 回测元数据（策略名、参数、日期等）

    Returns:
        完整报告 dict
    """
    report = {
        "generated_at": datetime.now().isoformat(),
        "metadata": metadata or {},
        "performance": results,
    }
    return report


def save_report_json(report: dict, filename: str = None) -> Path:
    """
    保存报告为 JSON 文件

    Args:
        report: 报告 dict
        filename: 文件名（不含路径），默认自动生成时间戳文件名

    Returns:
        保存路径
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy = report.get("metadata", {}).get("strategy", "unknown")
        filename = f"{timestamp}_{strategy}.json"

    filepath = REPORTS_DIR / filename

    # 处理 numpy 类型
    def convert_types(obj):
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=convert_types)

    print(f"[Report] Saved to {filepath}")
    return filepath


def print_report(report: dict):
    """打印完整报告到控制台"""
    meta = report.get("metadata", {})
    perf = report.get("performance", {})

    print("\n" + "=" * 60)
    print("  BACKTEST REPORT")
    print("=" * 60)

    # 元数据
    print("\n--- Metadata ---")
    for key, value in meta.items():
        print(f"  {key}: {value}")

    # 绩效
    print("\n--- Performance ---")
    for key, value in perf.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    print("=" * 60)
