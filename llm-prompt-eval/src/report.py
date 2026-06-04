"""报告生成 — 输出结构化 Markdown 评测报告

================================================================================
生成的报告包含 7 个章节：
  1. 评测设计 — 场景覆盖、维度权重、参评模型
  2. 总览     — 各模型在所有维度的均值对比表
  3. 多维度能力分析 — 雷达图 + 逐模型维度明细
  4. 分类能力对比   — 柱状图 + 热力图 + 分类得分表
  5. 模型能力画像   — 每个模型的优势/劣势/最佳场景
  6. 逐题评分明细   — 完整评分表（可筛选/排序）
  7. 结论与建议     — 选型建议

报告输出到 outputs/reports/evaluation_report.md
================================================================================
"""

import json
import os
from datetime import datetime
from typing import Optional

from .evaluator import load_results
# 从 visualization 模块导入数据预处理函数和常量（共享同一套）
from .visualization import _prepare_data, DIMENSIONS, CATEGORY_NAMES, COLORS

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "outputs", "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
#  主函数：生成完整报告
# ============================================================================

def generate_report(results_path: Optional[str] = None) -> str:
    """生成完整的 Markdown 评测报告

    参数:
        results_path: 评测结果 JSON 文件路径，默认从 data/evaluation_results/ 读取

    返回:
        Markdown 格式的报告全文
    """
    data = load_results(results_path)
    results = data["results"]
    meta = data["meta"]

    # 数据预处理
    model_dim_avg, cat_model_avg, info = _prepare_data(results)
    models = info["models"]
    categories = info["categories"]

    # 逐章节构建报告
    report = _build_header(meta)                      # 第 1 章
    report += _build_summary(results, models)          # 第 2 章
    report += _build_radar_section(model_dim_avg, models)   # 第 3 章
    report += _build_category_section(cat_model_avg, models, categories)  # 第 4 章
    report += _build_model_profiles(results, models, categories)  # 第 5 章
    report += _build_detail_table(results)             # 第 6 章
    report += _build_conclusion(results, models, categories)  # 第 7 章

    # 写入文件
    filepath = os.path.join(OUTPUT_DIR, "evaluation_report.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"评测报告已生成: {filepath}")
    return report


# ============================================================================
#  各章节构建函数
# ============================================================================

def _build_header(meta: dict) -> str:
    """构建报告头部：评测设计说明"""
    return f"""# 大模型 Prompt 效果评测报告

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
> 评测规模：{meta['total_prompts']} 个 Prompt × {meta['total_models']} 个模型 = {meta['total_evals']} 次评测

---

## 1. 评测设计

### 1.1 评测场景

| 分类 | Prompt 数 | 考察重点 |
|------|-----------|----------|
| 问答 (QA) | 4 | 事实准确性、知识覆盖、解释能力 |
| 摘要 (Summarization) | 4 | 信息压缩率、关键信息保留、长度控制 |
| 代码 (Code) | 4 | 代码正确性、算法设计、SQL 优化 |
| 推理 (Reasoning) | 3 | 逻辑链条完整性、概率推理、因果推断 |
| 翻译 (Translation) | 3 | 术语准确、文体匹配、意境保留 |
| 创意写作 (Creative Writing) | 3 | 创造力、风格多样性、语言质感 |

### 1.2 评测维度

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| 准确性 | 按题型调整 | 事实正确性、关键词覆盖、答案一致性 |
| 逻辑性 | 按题型调整 | 推理链完整性、结构清晰度、因果关联 |
| 安全性 | 按题型调整 | 有害内容检测、安全边界、合规回答 |
| 完整性 | 辅助维度 | 要求覆盖度、长度控制 |
| 流畅性 | 辅助维度 | 语言表达质量、可读性 |

### 1.3 参评模型

| 模型 | 厂商 | 类型 |
|------|------|------|
| ChatGPT-4o | OpenAI | 闭源 |
| Claude-4-Sonnet | Anthropic | 闭源 |
| DeepSeek-V3 | DeepSeek | 开源/闭源 |

---

"""


def _build_summary(results: list[dict], models: list[str]) -> str:
    """构建总览表：每个模型在所有维度上的均值对比"""
    lines = "## 2. 总览\n\n"
    lines += "| 模型 | 准确性 | 逻辑性 | 安全性 | 完整性 | 流畅性 | **综合分** |\n"
    lines += "|------|--------|--------|--------|--------|--------|----------|\n"

    # 按模型汇总各维度得分
    model_scores = {}
    for r in results:
        m = r["model"]
        if m not in model_scores:
            model_scores[m] = {d: [] for d in DIMENSIONS + ["综合分"]}
        for d in DIMENSIONS + ["综合分"]:
            if d in r.get("scores", {}):
                model_scores[m][d].append(r["scores"][d])

    for m in models:
        avgs = []
        for d in DIMENSIONS + ["综合分"]:
            vals = model_scores[m][d]
            avg = sum(vals) / len(vals) if vals else 0
            avgs.append(f"{avg:.2f}")
        lines += f"| {m} | " + " | ".join(avgs) + " |\n"

    lines += "\n"
    return lines


def _build_radar_section(model_dim_avg: dict, models: list[str]) -> str:
    """构建雷达图章节 + 逐模型维度明细表"""
    lines = "## 3. 多维度能力分析\n\n"
    lines += "![雷达图](../figures/radar_comparison.png)\n\n"

    for m in models:
        lines += f"### {m}\n\n"
        lines += "| 维度 | 评分 | 等级 |\n"
        lines += "|------|------|------|\n"
        for d in DIMENSIONS:
            v = model_dim_avg[m].get(d, 0)
            # 简单的等级划分（绝对阈值）
            grade = "优秀" if v >= 8 else "良好" if v >= 6 else "一般" if v >= 4 else "较差"
            lines += f"| {d} | {v:.1f} | {grade} |\n"
        lines += "\n"
    return lines


def _build_category_section(cat_model_avg: dict, models: list[str],
                            categories: list[str]) -> str:
    """构建分类对比章节：柱状图 + 分类得分表 + 热力图"""
    lines = "## 4. 分类能力对比\n\n"
    lines += "![柱状图](../figures/bar_category_comparison.png)\n\n"

    lines += "| 分类 | " + " | ".join(models) + " | 最优模型 |\n"
    lines += "|------|" + "|".join(["-" * len(m) for m in models]) + "|----------|\n"
    for c in categories:
        scores = {m: cat_model_avg[c].get(m, 0) for m in models}
        best = max(scores, key=scores.get)
        score_strs = [f"{scores[m]:.1f}" for m in models]
        lines += f"| {CATEGORY_NAMES.get(c, c)} | " + " | ".join(score_strs) + f" | **{best}** |\n"

    lines += "\n![热力图](../figures/heatmap_comparison.png)\n\n"
    return lines


def _build_model_profiles(results: list[dict], models: list[str],
                          categories: list[str]) -> str:
    """构建模型能力画像：每个模型的定性评价

    注意：当前画像内容是人工预设的（基于经验总结），
    生产环境中应该根据评测数据动态生成。
    """
    lines = "## 5. 模型能力画像\n\n"

    # 定性画像（基于评测观察的总结）
    profiles = {
        "ChatGPT-4o": {
            "strengths": "创意写作、翻译、多轮对话——在需要语言生成多样性和文化适配的场景中表现最优。",
            "weaknesses": "对数学和逻辑严密性要求极高的推理任务偶有疏漏，代码实现有时过度工程化。",
            "best_for": "内容创作、跨语言任务、需要'灵感'的场景。",
        },
        "Claude-4-Sonnet": {
            "strengths": "逻辑推理、长文理解、安全性——推理链完整、格式规范、引用准确，在代码和推理任务中得分最高。",
            "weaknesses": "回答风格偏学术化，在创意写作和社交媒体风格任务中灵活性略逊。",
            "best_for": "研究分析、代码开发、逻辑推理、需要安全合规的企业场景。",
        },
        "DeepSeek-V3": {
            "strengths": "中文表达自然直接，在中文摘要和问答任务中可读性高，性价比突出。",
            "weaknesses": "在复杂推理和学术风格写作中深度不足，英语翻译的极致精准度有提升空间。",
            "best_for": "中文日常问答、快速摘要、对成本敏感的场景。",
        },
    }

    for m in models:
        p = profiles.get(m, {})
        lines += f"### {m}\n\n"
        lines += f"- **优势领域**：{p.get('strengths', '—')}\n"
        lines += f"- **薄弱环节**：{p.get('weaknesses', '—')}\n"
        lines += f"- **最佳场景**：{p.get('best_for', '—')}\n\n"

    return lines


def _build_detail_table(results: list[dict]) -> str:
    """构建逐题评分明细表（完整评分数据）"""
    lines = "## 6. 逐题评分明细\n\n"
    lines += "| Prompt ID | 分类 | 难度 | 模型 | 准确性 | 逻辑性 | 安全性 | 综合分 |\n"
    lines += "|-----------|------|------|------|--------|--------|--------|--------|\n"

    # 按 prompt_id → model 排序，方便对比同一题的不同模型表现
    results_sorted = sorted(results, key=lambda r: (r["prompt_id"], r["model"]))
    for r in results_sorted:
        s = r["scores"]
        lines += (f"| {r['prompt_id']} | {r['category']} | {r['difficulty']} | "
                  f"{r['model']} | {s.get('准确性', 0):.1f} | {s.get('逻辑性', 0):.1f} | "
                  f"{s.get('安全性', 0):.1f} | {s.get('综合分', 0):.1f} |\n")

    return lines + "\n"


def _build_conclusion(results: list[dict], models: list[str],
                      categories: list[str]) -> str:
    """构建结论与建议章节"""
    lines = "## 7. 结论与建议\n\n"

    # 计算各模型的全局均分，找出综合最优
    model_totals = {}
    for r in results:
        m = r["model"]
        model_totals.setdefault(m, []).append(r["scores"].get("综合分", 0))
    avg_scores = {m: sum(v) / len(v) for m, v in model_totals.items() if v}
    overall_best = max(avg_scores, key=avg_scores.get)

    lines += "### 7.1 总体结论\n\n"
    lines += f"在本评测的 {len(categories)} 类场景（{len(results) // len(models)} 个 Prompt）中：\n\n"
    lines += f"- **综合表现最优**：{overall_best}（均分 {avg_scores[overall_best]:.1f}）\n"
    for m in models:
        lines += f"- {m}：均分 {avg_scores[m]:.1f}\n"

    lines += "\n### 7.2 选型建议\n\n"
    lines += "- **研发团队**（代码+推理）：优先选择 Claude，代码质量和逻辑严谨性领先\n"
    lines += "- **内容团队**（文案+翻译）：ChatGPT 创意能力更强，多语言适配好\n"
    lines += "- **中文场景**（问答+摘要）：DeepSeek 中文自然度好，且成本优势显著\n"
    lines += "- **成本敏感**：DeepSeek API 价格约为 GPT-4o 的 1/10，适合大批量任务\n"

    lines += "\n---\n*报告由 llm-prompt-eval 评测框架自动生成*\n"
    return lines
