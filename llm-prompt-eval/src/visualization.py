"""可视化分析 - 雷达图、柱状图、热力图、综合对比"""

import json
import os
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DIMENSIONS = ["准确性", "逻辑性", "安全性", "完整性", "流畅性"]
COLORS = {"ChatGPT-4o": "#10a37f", "Claude-4-Sonnet": "#d97706",
          "DeepSeek-V3": "#4b6bfb"}
CATEGORY_NAMES = {"qa": "问答", "summarization": "摘要", "code": "代码",
                  "reasoning": "推理", "translation": "翻译",
                  "creative_writing": "创意写作"}


def _prepare_data(results: list[dict]) -> tuple[dict, dict, dict]:
    """整理评测结果为模型维度平均分、分类维度分、分类模型分"""
    models = sorted(set(r["model"] for r in results))
    categories = sorted(set(r["category"] for r in results))

    model_dim_avg: dict[str, dict[str, float]] = {m: {d: 0.0 for d in DIMENSIONS} for m in models}
    model_dim_count: dict[str, dict[str, int]] = {m: {d: 0 for d in DIMENSIONS} for m in models}
    cat_model_avg: dict[str, dict[str, float]] = {c: {m: 0.0 for m in models} for c in categories}
    cat_model_count: dict[str, dict[str, int]] = {c: {m: 0 for m in models} for c in categories}

    for r in results:
        m = r["model"]
        c = r["category"]
        scores = r.get("scores", {})
        for dim in DIMENSIONS:
            if dim in scores:
                model_dim_avg[m][dim] += scores[dim]
                model_dim_count[m][dim] += 1
        if "综合分" in scores:
            cat_model_avg[c][m] += scores["综合分"]
            cat_model_count[c][m] += 1

    for m in models:
        for d in DIMENSIONS:
            if model_dim_count[m][d] > 0:
                model_dim_avg[m][d] /= model_dim_count[m][d]
    for c in categories:
        for m in models:
            if cat_model_count[c][m] > 0:
                cat_model_avg[c][m] /= cat_model_count[c][m]

    return model_dim_avg, cat_model_avg, {"models": models, "categories": categories}


def plot_radar(results: list[dict], save_path: Optional[str] = None) -> str:
    """多模型雷达图 - 各维度能力对比"""
    model_dim_avg, _, meta = _prepare_data(results)
    models = meta["models"]

    n_dims = len(DIMENSIONS)
    angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    for model in models:
        values = [model_dim_avg[model].get(d, 0) for d in DIMENSIONS]
        values += values[:1]
        color = COLORS.get(model, "#888888")
        ax.fill(angles, values, alpha=0.1, color=color)
        ax.plot(angles, values, "o-", linewidth=2, color=color, label=model, markersize=5)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(DIMENSIONS, fontsize=12)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=8)
    ax.set_title("模型多维度能力雷达图", fontsize=15, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)

    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "radar_comparison.png")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return save_path


def plot_bar_comparison(results: list[dict], save_path: Optional[str] = None) -> str:
    """分组柱状图 - 各分类综合分对比"""
    _, cat_model_avg, meta = _prepare_data(results)
    models = meta["models"]
    categories = meta["categories"]

    x = np.arange(len(categories))
    n_models = len(models)
    width = 0.8 / n_models

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, model in enumerate(models):
        values = [cat_model_avg[c].get(model, 0) for c in categories]
        bars = ax.bar(x + i * width, values, width, label=model,
                      color=COLORS.get(model, "#888888"), alpha=0.85, edgecolor="white")
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                    f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8)

    ax.set_xlabel("评测分类", fontsize=12)
    ax.set_ylabel("综合评分", fontsize=12)
    ax.set_title("各分类模型综合评分对比", fontsize=15, fontweight="bold")
    ax.set_xticks(x + width * (n_models - 1) / 2)
    ax.set_xticklabels([CATEGORY_NAMES.get(c, c) for c in categories], fontsize=11)
    ax.set_ylim(0, 11)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "bar_category_comparison.png")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


def plot_heatmap(results: list[dict], save_path: Optional[str] = None) -> str:
    """热力图 - 模型×分类 综合评分矩阵"""
    _, cat_model_avg, meta = _prepare_data(results)
    models = meta["models"]
    categories = meta["categories"]

    data = []
    for c in categories:
        row = [cat_model_avg[c].get(m, 0) for m in models]
        data.append(row)
    data = np.array(data)

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=4, vmax=10)

    for i in range(len(categories)):
        for j in range(len(models)):
            ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    color="white" if data[i, j] < 7.5 else "black")

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, fontsize=10)
    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels([CATEGORY_NAMES.get(c, c) for c in categories], fontsize=10)
    ax.set_title("模型 × 分类 综合评分热力图", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.8, label="综合评分")

    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "heatmap_comparison.png")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


def plot_latency(results: list[dict], save_path: Optional[str] = None) -> str:
    """响应速度对比 - 平均延迟柱状图"""
    models = sorted(set(r["model"] for r in results))
    avg_latency = {}
    counts = {}
    for r in results:
        m = r["model"]
        avg_latency[m] = avg_latency.get(m, 0) + r.get("latency_ms", 0)
        counts[m] = counts.get(m, 0) + 1
    for m in models:
        avg_latency[m] /= counts[m]

    fig, ax = plt.subplots(figsize=(7, 5))
    colors_list = [COLORS.get(m, "#888888") for m in models]
    bars = ax.bar(models, [avg_latency[m] for m in models],
                  color=colors_list, alpha=0.8, edgecolor="white")
    for bar, model in zip(bars, models):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
                f"{avg_latency[model]:.0f}ms", ha="center", fontsize=11, fontweight="bold")

    ax.set_ylabel("平均响应时间 (ms)", fontsize=11)
    ax.set_title("模型平均响应速度对比", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "latency_comparison.png")
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


def plot_all(results: list[dict]) -> list[str]:
    """生成全部可视化图表"""
    paths = [
        plot_radar(results),
        plot_bar_comparison(results),
        plot_heatmap(results),
        plot_latency(results),
    ]
    print(f"已生成 {len(paths)} 张可视化图表")
    for p in paths:
        print(f"  → {p}")
    return paths
