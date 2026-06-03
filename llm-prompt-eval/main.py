#!/usr/bin/env python3
"""大模型 Prompt 效果评测 — 主入口

用法:
    python main.py                    # 模拟模式运行全流程
    python main.py --real             # 使用真实 API（需设置环境变量）
    python main.py --report-only      # 仅从已有结果生成报告和图表
    python main.py --prompt QA-001    # 单 prompt 快速测试
"""

import argparse
import os
import sys

# 确保 src 在路径中
sys.path.insert(0, os.path.dirname(__file__))

from src.api_clients import create_clients
from src.evaluator import load_all_prompts, run_batch_evaluation, save_results, load_results
from src.visualization import plot_all
from src.report import generate_report


def main():
    parser = argparse.ArgumentParser(description="大模型 Prompt 效果评测工具")
    parser.add_argument("--real", action="store_true", help="使用真实 API（需设置环境变量）")
    parser.add_argument("--report-only", action="store_true", help="仅从已有结果生成报告")
    parser.add_argument("--prompt", type=str, help="仅测试指定 prompt ID")
    parser.add_argument("--max-workers", type=int, default=3, help="并发数")
    args = parser.parse_args()

    # 仅生成报告模式
    if args.report_only:
        print("=" * 60)
        print("  仅报告模式 — 从已有评测结果生成图表和报告")
        print("=" * 60)
        data = load_results()
        results = data["results"]
        plot_all(results)
        generate_report()
        print("\n✓ 报告生成完成！请查看 outputs/ 目录。")
        return

    # 加载 prompts
    all_prompts = load_all_prompts()
    if args.prompt:
        all_prompts = [p for p in all_prompts if p["id"] == args.prompt]
        if not all_prompts:
            print(f"未找到 Prompt: {args.prompt}")
            sys.exit(1)

    print("=" * 60)
    print("  大模型 Prompt 效果评测与数据集构建")
    print("=" * 60)
    print(f"\n加载了 {len(all_prompts)} 个 Prompt")
    print(f"覆盖分类: {sorted(set(p['category'] for p in all_prompts))}")

    # 创建客户端
    mode = "real" if args.real else "mock"
    clients = create_clients(mode)
    print(f"\n模式: {mode.upper()}")
    print(f"模型: {', '.join(c.model_name for c in clients)}")

    # 执行评测
    print(f"\n{'—' * 60}")
    results = run_batch_evaluation(clients, all_prompts, max_workers=args.max_workers)

    # 保存结果
    save_results(results)

    # 生成可视化
    print(f"\n{'—' * 60}")
    plot_all(results)

    # 生成报告
    generate_report()  # 从保存的结果文件加载

    print(f"\n{'=' * 60}")
    print("  评测完成！")
    print(f"  结果数据: data/evaluation_results/evaluation_results.json")
    print(f"  可视化图表: outputs/figures/")
    print(f"  评测报告: outputs/reports/evaluation_report.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
