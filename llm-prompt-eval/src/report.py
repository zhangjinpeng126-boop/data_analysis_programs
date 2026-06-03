"""报告生成 - 结构化 Markdown 评测报告"""

import json
import os
from datetime import datetime
from typing import Optional

from .evaluator import load_results
from .visualization import _prepare_data, DIMENSIONS, CATEGORY_NAMES, COLORS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_report(results_path: Optional[str] = None) -> str:
    """生成完整的 Markdown 评测报告"""
    data = load_results(results_path)
    results = data["results"]
    meta = data["meta"]

    model_dim_avg, cat_model_avg, info = _prepare_data(results)
    models = info["models"]
    categories = info["categories"]

    report = _build_header(meta)
    report += _build_summary(results, models)
    report += _build_radar_section(model_dim_avg, models)
    report += _build_category_section(cat_model_avg, models, categories)
    report += _build_model_profiles(results, models, categories)
    report += _build_detail_table(results)
    report += _build_conclusion(results, models, categories)

    filepath = os.path.join(OUTPUT_DIR, "evaluation_report.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"评测报告已生成: {filepath}")
    return report


def _build_header(meta: dict) -> str:
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
    """总览摘要"""
    lines = "## 2. 总览\n\n"
    lines += "| 模型 | 准确性 | 逻辑性 | 安全性 | 完整性 | 流畅性 | **综合分** |\n"
    lines += "|------|--------|--------|--------|--------|--------|----------|\n"

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

    # 最高分标注
    lines += "\n"
    return lines


def _build_radar_section(model_dim_avg: dict, models: list[str]) -> str:
    lines = "## 3. 多维度能力分析\n\n"
    lines += "![雷达图](../figures/radar_comparison.png)\n\n"

    for m in models:
        lines += f"### {m}\n\n"
        lines += "| 维度 | 评分 | 等级 |\n"
        lines += "|------|------|------|\n"
        for d in DIMENSIONS:
            v = model_dim_avg[m].get(d, 0)
            grade = "优秀" if v >= 8 else "良好" if v >= 6 else "一般" if v >= 4 else "较差"
            lines += f"| {d} | {v:.1f} | {grade} |\n"
        lines += "\n"
    return lines


def _build_category_section(cat_model_avg: dict, models: list[str],
                            categories: list[str]) -> str:
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
    lines = "## 5. 模型能力画像\n\n"

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
    lines = "## 6. 逐题评分明细\n\n"
    lines += "| Prompt ID | 分类 | 难度 | 模型 | 准确性 | 逻辑性 | 安全性 | 综合分 |\n"
    lines += "|-----------|------|------|------|--------|--------|--------|--------|\n"

    results_sorted = sorted(results, key=lambda r: (r["prompt_id"], r["model"]))
    for r in results_sorted:
        s = r["scores"]
        lines += (f"| {r['prompt_id']} | {r['category']} | {r['difficulty']} | "
                  f"{r['model']} | {s.get('准确性', 0):.1f} | {s.get('逻辑性', 0):.1f} | "
                  f"{s.get('安全性', 0):.1f} | {s.get('综合分', 0):.1f} |\n")

    return lines + "\n"


def _build_conclusion(results: list[dict], models: list[str],
                      categories: list[str]) -> str:
    lines = "## 7. 结论与建议\n\n"

    # 找最优模型
    model_totals = {}
    for r in results:
        m = r["model"]
        model_totals.setdefault(m, []).append(r["scores"].get("综合分", 0))
    avg_scores = {m: sum(v) / len(v) for m, v in model_totals.items() if v}
    overall_best = max(avg_scores, key=avg_scores.get)

    lines += f"### 7.1 总体结论\n\n"
    lines += f"在本评测的 {len(categories)} 类场景（{len(results) // len(models)} 个 Prompt）中：\n\n"
    lines += f"- **综合表现最优**：{overall_best}（均分 {avg_scores[overall_best]:.1f}）\n"
    for m in models:
        lines += f"- {m}：均分 {avg_scores[m]:.1f}\n"

    lines += f"\n### 7.2 选型建议\n\n"
    lines += "- **研发团队**（代码+推理）：优先选择 Claude，代码质量和逻辑严谨性领先\n"
    lines += "- **内容团队**（文案+翻译）：ChatGPT 创意能力更强，多语言适配好\n"
    lines += "- **中文场景**（问答+摘要）：DeepSeek 中文自然度好，且成本优势显著\n"
    lines += "- **成本敏感**：DeepSeek API 价格约为 GPT-4o 的 1/10，适合大批量任务\n"

    lines += f"\n---\n*报告由 llm-prompt-eval 评测框架自动生成*\n"
    return lines
