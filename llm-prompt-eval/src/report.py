"""报告生成  -  输出结构化 Markdown 评测报告

================================================================================
生成的报告包含 7 个章节:
  1. 评测设计  -  场景覆盖,维度权重,参评模型
  2. 总览      -  各模型在所有维度的均值对比表
  3. 多维度能力分析  -  雷达图 + 逐模型维度明细
  4. 分类能力对比    -  柱状图 + 热力图 + 分类得分表
  5. 模型能力画像    -  每个模型的优势/劣势/最佳场景
  6. 逐题评分明细    -  完整评分表(可筛选/排序)
  7. 结论与建议      -  选型建议

报告输出到 outputs/reports/evaluation_report.md
================================================================================
"""

import json
import os
from datetime import datetime
from typing import Optional

from .evaluator import load_results
# 从 visualization 模块导入数据预处理函数和常量(共享同一套)
from .visualization import _prepare_data, DIMENSIONS, CATEGORY_NAMES, COLORS

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "outputs", "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
#  主函数:生成完整报告
# ============================================================================

def generate_report(results_path: Optional[str] = None) -> str:
    """生成完整的 Markdown 评测报告

    参数:
        results_path: 评测结果 JSON 文件路径,默认从 data/evaluation_results/ 读取

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

    # 确保 meta 包含实际模型列表(动态生成,非硬编码)
    meta["models"] = info["models"]

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

# 模型元信息(用于报告中的厂商/类型标注)
# 只包含已知模型,未知模型会显示为"自定义"
_MODEL_META = {
    "DeepSeek": {"vendor": "DeepSeek", "type": "API 服务"},
    "ChatGPT": {"vendor": "OpenAI", "type": "闭源 API"},
    "Claude": {"vendor": "Anthropic", "type": "闭源 API"},
}


def _get_model_meta(model_name: str) -> dict:
    """根据模型名称匹配厂商和类型信息"""
    for key, meta in _MODEL_META.items():
        if key.lower() in model_name.lower():
            return meta
    return {"vendor": "自定义", "type": "API 服务"}


def _build_header(meta: dict) -> str:
    """构建报告头部:评测设计说明(参评模型根据实际数据动态生成)"""
    # 从实际评估结果中提取模型列表(而非硬编码)
    return f"""# 大模型 Prompt 效果评测报告

> 生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M')}
> 评测规模:{meta['total_prompts']} 个 Prompt x {meta['total_models']} 个模型 = {meta['total_evals']} 次评测

---

## 1. 评测设计

### 1.1 评测场景

| 分类 | Prompt 数 | 考察重点 |
|------|-----------|----------|
| 问答 (QA) | 4 | 事实准确性,知识覆盖,解释能力 |
| 摘要 (Summarization) | 4 | 信息压缩率,关键信息保留,长度控制 |
| 代码 (Code) | 4 | 代码正确性,算法设计,SQL 优化 |
| 推理 (Reasoning) | 3 | 逻辑链条完整性,概率推理,因果推断 |
| 翻译 (Translation) | 3 | 术语准确,文体匹配,意境保留 |
| 创意写作 (Creative Writing) | 3 | 创造力,风格多样性,语言质感 |

### 1.2 评测维度

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| 准确性 | 按题型调整 | 事实正确性,关键词覆盖,答案一致性 |
| 逻辑性 | 按题型调整 | 推理链完整性,结构清晰度,因果关联 |
| 安全性 | 按题型调整 | 有害内容检测,安全边界,合规回答 |
| 完整性 | 辅助维度 | 要求覆盖度,长度控制 |
| 流畅性 | 辅助维度 | 语言表达质量,可读性 |

### 1.3 参评模型

(以下列表由实际评测数据自动生成,非硬编码)

| 模型 | 厂商 | 类型 |
|------|------|------|
""" + "\n".join(
    f"| {m} | {_get_model_meta(m)['vendor']} | {_get_model_meta(m)['type']} |"
    for m in sorted(meta.get("models", []))
) + "\n\n---\n\n"


def _build_summary(results: list[dict], models: list[str]) -> str:
    """构建总览表:每个模型在所有维度上的均值对比"""
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
            # 简单的等级划分(绝对阈值)
            grade = "优秀" if v >= 8 else "良好" if v >= 6 else "一般" if v >= 4 else "较差"
            lines += f"| {d} | {v:.1f} | {grade} |\n"
        lines += "\n"
    return lines


def _build_category_section(cat_model_avg: dict, models: list[str],
                            categories: list[str]) -> str:
    """构建分类对比章节:柱状图 + 分类得分表 + 热力图"""
    lines = "## 4. 分类能力对比\n\n"
    lines += "![柱状图](../figures/bar_category_comparison.png)\n\n"

    # 多模型时显示"最优模型"列才有意义,单模型时省略
    multi_model = len(models) > 1
    if multi_model:
        lines += "| 分类 | " + " | ".join(models) + " | 最优模型 |\n"
        lines += "|------|" + "|".join(["-" * len(m) for m in models]) + "|----------|\n"
    else:
        lines += "| 分类 | " + " | ".join(models) + " |\n"
        lines += "|------|" + "|".join(["-" * len(m) for m in models]) + "|\n"
    for c in categories:
        scores = {m: cat_model_avg[c].get(m, 0) for m in models}
        best = max(scores, key=scores.get)
        score_strs = [f"{scores[m]:.1f}" for m in models]
        row = f"| {CATEGORY_NAMES.get(c, c)} | " + " | ".join(score_strs)
        if multi_model:
            row += f" | **{best}**"
        row += " |\n"
        lines += row

    lines += "\n![热力图](../figures/heatmap_comparison.png)\n\n"
    return lines


def _build_model_profiles(results: list[dict], models: list[str],
                          categories: list[str]) -> str:
    """构建模型能力画像:基于实际评测数据动态生成

    每个模型的画像完全由评分数据驱动,不包含任何硬编码/预设评价.
    """
    lines = "## 5. 模型能力画像\n\n"

    # 按模型聚合各分类的综合分
    model_cat_scores: dict[str, dict[str, float]] = {
        m: {c: 0.0 for c in categories} for m in models
    }
    cat_counts: dict[str, dict[str, int]] = {
        m: {c: 0 for c in categories} for m in models
    }
    for r in results:
        m = r["model"]
        c = r["category"]
        if "综合分" in r.get("scores", {}):
            model_cat_scores[m][c] += r["scores"]["综合分"]
            cat_counts[m][c] += 1
    for m in models:
        for c in categories:
            if cat_counts[m][c] > 0:
                model_cat_scores[m][c] /= cat_counts[m][c]

    # 按维度聚合
    dim_scores: dict[str, dict[str, float]] = {m: {d: 0.0 for d in DIMENSIONS} for m in models}
    dim_counts: dict[str, dict[str, int]] = {m: {d: 0 for d in DIMENSIONS} for m in models}
    for r in results:
        m = r["model"]
        s = r.get("scores", {})
        for d in DIMENSIONS:
            if d in s:
                dim_scores[m][d] += s[d]
                dim_counts[m][d] += 1
    for m in models:
        for d in DIMENSIONS:
            if dim_counts[m][d] > 0:
                dim_scores[m][d] /= dim_counts[m][d]

    for m in models:
        # 找出该模型得分最高和最低的场景
        cat_avgs = model_cat_scores[m]
        if cat_avgs:
            best_cat = max(cat_avgs, key=cat_avgs.get)
            worst_cat = min(cat_avgs, key=cat_avgs.get)
            best_name = CATEGORY_NAMES.get(best_cat, best_cat)
            worst_name = CATEGORY_NAMES.get(worst_cat, worst_cat)
        else:
            best_name = worst_name = "暂无数据"

        # 找出该模型得分最高和最低的维度
        dim_avgs = dim_scores[m]
        if dim_avgs:
            best_dim = max(dim_avgs, key=dim_avgs.get)
            worst_dim = min(dim_avgs, key=dim_avgs.get)
        else:
            best_dim = worst_dim = "暂无数据"

        lines += f"### {m}\n\n"
        lines += f"- **优势场景**:{best_name} (均分 {cat_avgs.get(best_cat, 0):.1f})\n"
        lines += f"- **劣势场景**:{worst_name} (均分 {cat_avgs.get(worst_cat, 0):.1f})\n"
        lines += f"- **最强维度**:{best_dim} ({dim_avgs.get(best_dim, 0):.1f}/10)\n"
        lines += f"- **最弱维度**:{worst_dim} ({dim_avgs.get(worst_dim, 0):.1f}/10)\n"
        lines += "\n"

    lines += (
        "> 注意:以上画像完全由规则引擎自动生成,基于关键词匹配+正则+文本统计的评分方式 "
        "存在语义理解局限.如需更精准的能力评估,建议引入 LLM-as-Judge 作为补充.\n\n"
    )
    return lines


def _build_detail_table(results: list[dict]) -> str:
    """构建逐题评分明细表(完整评分数据)"""
    lines = "## 6. 逐题评分明细\n\n"
    lines += "| Prompt ID | 分类 | 难度 | 模型 | 准确性 | 逻辑性 | 安全性 | 综合分 |\n"
    lines += "|-----------|------|------|------|--------|--------|--------|--------|\n"

    # 按 prompt_id → model 排序,方便对比同一题的不同模型表现
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

    # 计算各模型的全局均分,找出综合最优
    model_totals = {}
    for r in results:
        m = r["model"]
        model_totals.setdefault(m, []).append(r["scores"].get("综合分", 0))
    avg_scores = {m: sum(v) / len(v) for m, v in model_totals.items() if v}
    overall_best = max(avg_scores, key=avg_scores.get)

    lines += "### 7.1 总体结论\n\n"
    lines += f"在本评测的 {len(categories)} 类场景({len(results) // len(models)} 个 Prompt)中:\n\n"
    lines += f"- **综合表现最优**:{overall_best}(均分 {avg_scores[overall_best]:.1f})\n"
    for m in models:
        lines += f"- {m}:均分 {avg_scores[m]:.1f}\n"

    lines += "\n### 7.2 后续方向\n\n"
    # 单模型评测时,不做跨模型选型建议(那需要真实的多模型对比数据)
    if len(models) > 1:
        lines += "- 本报告包含多个模型的对比评测数据,可根据各场景得分进行选型决策.\n"
    else:
        lines += "- 当前评测仅包含 {models[0]} (单模型).要获得跨模型对比结论,需配置其他模型的 API Key 后重新运行.\n".format(models=models)
    lines += "- **规则引擎局限**:当前评分基于关键词匹配和正则规则,翻译和创意写作类评分准确性有限.\n"
    lines += "- **扩展建议**:引入 LLM-as-Judge 方案可显著提升语义评估质量,尤其适合翻译质量,创意内容等场景.\n"
    lines += "- **持续评测**:Prompt 效果会随模型版本更新而变化,建议建立定期评测机制跟踪模型能力变迁.\n"

    lines += "\n---\n*报告由 llm-prompt-eval 评测框架自动生成*\n"
    return lines
