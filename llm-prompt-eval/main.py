#!/usr/bin/env python3
"""大模型 Prompt 效果评测 — 主入口

================================================================================
  这个文件是整个项目的启动入口。它把所有模块串联起来，形成一条完整的流水线：

    加载 Prompt → 调用模型 → 评分 → 保存结果 → 可视化 → 生成报告

  支持 4 种运行模式（通过命令行参数切换）：

    python main.py                    模拟模式：使用预置 mock 数据跑通全流程
    python main.py --real             真实模式：调用 DeepSeek / OpenAI / Claude API
    python main.py --report-only      报告模式：跳过评测，仅从已有结果生成图表和报告
    python main.py --prompt QA-001    单题模式：只测试指定的一个 Prompt

  环境变量配置（真实模式需要）：
    DEEPSEEK_API_KEY    DeepSeek API 密钥
    OPENAI_API_KEY      OpenAI API 密钥
    ANTHROPIC_API_KEY   Anthropic (Claude) API 密钥
    配了哪个就用哪个，没配的自动跳过。
================================================================================
"""

import argparse
import os
import sys

# 确保 src 目录在 Python 的模块搜索路径中
# 这样 import src.xxx 时 Python 能找到对应的 .py 文件
sys.path.insert(0, os.path.dirname(__file__))

from src.api_clients import create_clients
from src.evaluator import load_all_prompts, run_batch_evaluation, save_results, load_results
from src.visualization import plot_all
from src.report import generate_report


def main():
    """主函数 — 解析命令行参数并执行对应的评测流程"""

    # ---- 1. 解析命令行参数 ----
    parser = argparse.ArgumentParser(
        description="大模型 Prompt 效果评测工具 — 多模型 × 多场景 × 多维评分"
    )
    parser.add_argument(
        "--real", action="store_true",
        help="使用真实 API 进行评测（需提前设置环境变量: DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY）"
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="仅从已有的评测结果 JSON 重新生成图表和报告（不重新评测）"
    )
    parser.add_argument(
        "--prompt", type=str,
        help="仅测试指定的 Prompt ID（如 QA-001），用于单题快速验证"
    )
    parser.add_argument(
        "--max-workers", type=int, default=3,
        help="并发线程数（默认 3，真实 API 模式建议不要设太高以免触发限流）"
    )
    args = parser.parse_args()

    # ---- 2. 报告模式：跳过评测，直接生成报告 ----
    if args.report_only:
        print("=" * 60)
        print("  仅报告模式 — 从已有评测结果生成图表和报告")
        print("=" * 60)
        data = load_results()          # 加载之前保存的评测结果
        results = data["results"]
        plot_all(results)              # 重新生成 4 张图表
        generate_report()              # 重新生成 Markdown 报告
        print("\n✓ 报告生成完成！请查看 outputs/ 目录。")
        return

    # ---- 3. 加载 Prompt 数据集 ----
    all_prompts = load_all_prompts()
    if args.prompt:
        # 单题模式：只保留匹配 ID 的 Prompt
        all_prompts = [p for p in all_prompts if p["id"] == args.prompt]
        if not all_prompts:
            print(f"未找到 Prompt: {args.prompt}")
            sys.exit(1)

    print("=" * 60)
    print("  大模型 Prompt 效果评测与数据集构建")
    print("=" * 60)
    print(f"\n加载了 {len(all_prompts)} 个 Prompt")
    print(f"覆盖分类: {sorted(set(p['category'] for p in all_prompts))}")

    # ---- 4. 创建模型客户端 ----
    mode = "real" if args.real else "mock"
    clients = create_clients(mode)
    print(f"\n模式: {mode.upper()}")
    print(f"模型: {', '.join(c.model_name for c in clients)}")

    # ---- 5. 执行批量评测（核心步骤）----
    print(f"\n{'—' * 60}")
    results = run_batch_evaluation(
        clients, all_prompts,
        max_workers=args.max_workers
    )

    # ---- 6. 保存结果到 JSON ----
    save_results(results)

    # ---- 7. 生成可视化图表 ----
    print(f"\n{'—' * 60}")
    plot_all(results)

    # ---- 8. 生成 Markdown 报告 ----
    generate_report()  # 内部会从保存的 JSON 文件加载

    # ---- 9. 完成提示 ----
    print(f"\n{'=' * 60}")
    print("  评测完成！")
    print(f"  结果数据: data/evaluation_results/evaluation_results.json")
    print(f"  可视化图表: outputs/figures/")
    print(f"  评测报告: outputs/reports/evaluation_report.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
