"""可视化分析  -  雷达图,柱状图,热力图,延迟对比

================================================================================
生成 4 种图表(均保存为 PNG + 在 notebook 中可直接显示):
  1. 雷达图     -  多模型在五个维度上的能力轮廓对比
  2. 分组柱状图  -  各分类场景下模型综合分对比
  3. 热力图     -  模型 × 分类 的综合分矩阵
  4. 延迟对比图  -  各模型平均响应时间对比

所有图片输出到 outputs/figures/ 目录.
================================================================================
"""

import json
import os
from typing import Optional

# matplotlib 配置
import matplotlib
matplotlib.use("Agg")  # 使用非交互式后端(在命令行环境也可生成图片)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---- 中文字体配置 ----
# Windows 用 Microsoft YaHei,macOS/Linux 回退到 SimHei 或默认字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False  # 让负号正常显示(不被显示为方块)

# ---- 路径与常量 ----
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "outputs", "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)  # 确保输出目录存在

# 五个评分维度(顺序固定,雷达图按此排列)
DIMENSIONS = ["准确性", "逻辑性", "安全性", "完整性", "流畅性"]

# 每个模型对应的品牌色(视觉上容易区分)
COLORS = {
    "ChatGPT-4o": "#10a37f",     # OpenAI 绿
    "Claude-4-Sonnet": "#d97706", # Anthropic 橙
    "DeepSeek-V3": "#4b6bfb",    # DeepSeek 蓝
}

# 分类代码 → 中文显示名
CATEGORY_NAMES = {
    "qa": "问答",
    "summarization": "摘要",
    "code": "代码",
    "reasoning": "推理",
    "translation": "翻译",
    "creative_writing": "创意写作",
}


# ============================================================================
#  数据预处理  -  将所有图表需要的数据结构统一计算出来
# ============================================================================

def _prepare_data(results: list[dict]) -> tuple[dict, dict, dict]:
    """从原始评测结果中提取/聚合出三个数据结构:

    1. model_dim_avg: {模型: {维度: 平均分}}
       用于雷达图  -  看每个模型在各维度的表现
       例: {"ChatGPT-4o": {"准确性": 7.1, "逻辑性": 5.8, ...}}

    2. cat_model_avg: {分类: {模型: 平均综合分}}
       用于柱状图和热力图  -  看每个模型在各场景的强弱
       例: {"问答": {"ChatGPT-4o": 7.6, "Claude-4-Sonnet": 7.0, ...}}

    3. meta: 包含 models 和 categories 列表
    """
    models = sorted(set(r["model"] for r in results))
    categories = sorted(set(r["category"] for r in results))

    # 初始化累加器和计数器(分开存储,最后相除得平均值)
    model_dim_avg: dict[str, dict[str, float]] = {
        m: {d: 0.0 for d in DIMENSIONS} for m in models
    }
    model_dim_count: dict[str, dict[str, int]] = {
        m: {d: 0 for d in DIMENSIONS} for m in models
    }
    cat_model_avg: dict[str, dict[str, float]] = {
        c: {m: 0.0 for m in models} for c in categories
    }
    cat_model_count: dict[str, dict[str, int]] = {
        c: {m: 0 for m in models} for c in categories
    }

    # 遍历所有评测结果,累加分数
    for r in results:
        m = r["model"]
        c = r["category"]
        scores = r.get("scores", {})

        # 累加五维分数
        for dim in DIMENSIONS:
            if dim in scores:
                model_dim_avg[m][dim] += scores[dim]
                model_dim_count[m][dim] += 1
        # 累加综合分
        if "综合分" in scores:
            cat_model_avg[c][m] += scores["综合分"]
            cat_model_count[c][m] += 1

    # 计算平均值
    for m in models:
        for d in DIMENSIONS:
            if model_dim_count[m][d] > 0:
                model_dim_avg[m][d] /= model_dim_count[m][d]
    for c in categories:
        for m in models:
            if cat_model_count[c][m] > 0:
                cat_model_avg[c][m] /= cat_model_count[c][m]

    return model_dim_avg, cat_model_avg, {"models": models, "categories": categories}


# ============================================================================
#  图表 1:雷达图  -  多模型多维度能力对比
# ============================================================================

def plot_radar(results: list[dict], save_path: Optional[str] = None) -> str:
    """绘制多模型能力雷达图

    雷达图的每个轴代表一个评分维度,越靠近外圈(10分)越好.
    适合直观比较不同模型的"形状" - 某个模型是全面型还是偏科型.

    参数:
        results: 评测结果列表
        save_path: 图片保存路径(默认 outputs/figures/radar_comparison.png)

    返回:
        保存的图片路径
    """
    model_dim_avg, _, meta = _prepare_data(results)
    models = meta["models"]

    n_dims = len(DIMENSIONS)
    # 计算每个轴的角度(等分圆周)
    angles = np.linspace(0, 2 * np.pi, n_dims, endpoint=False).tolist()
    angles += angles[:1]  # 首尾相连形成闭合多边形

    # 创建极坐标子图
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)   # 让第一个轴在顶部(12点钟方向)
    ax.set_theta_direction(-1)       # 顺时针排列

    for model in models:
        # 按 DIMENSIONS 的顺序取出该模型各维度得分
        values = [model_dim_avg[model].get(d, 0) for d in DIMENSIONS]
        values += values[:1]  # 闭合
        color = COLORS.get(model, "#888888")
        ax.fill(angles, values, alpha=0.1, color=color)  # 半透明填充
        ax.plot(angles, values, "o-", linewidth=2,
                color=color, label=model, markersize=5)

    # 设置轴标签和刻度
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
    plt.close(fig)  # 关闭图形释放内存
    return save_path


# ============================================================================
#  图表 2:分组柱状图  -  各分类下模型综合分对比
# ============================================================================

def plot_bar_comparison(results: list[dict], save_path: Optional[str] = None) -> str:
    """绘制分组柱状图

    X 轴 = 评测分类(问答/代码/推理...)
    每组 = 3 根柱子分别代表 3 个模型
    Y 轴 = 该分类下的平均综合分

    参数:
        results: 评测结果列表
        save_path: 图片保存路径

    返回:
        保存的图片路径
    """
    _, cat_model_avg, meta = _prepare_data(results)
    models = meta["models"]
    categories = meta["categories"]

    x = np.arange(len(categories))  # X 轴位置:[0, 1, 2, 3, 4, 5]
    n_models = len(models)
    width = 0.8 / n_models  # 每根柱子的宽度(等分可用空间)

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, model in enumerate(models):
        values = [cat_model_avg[c].get(model, 0) for c in categories]
        bars = ax.bar(x + i * width, values, width, label=model,
                      color=COLORS.get(model, "#888888"),
                      alpha=0.85, edgecolor="white")
        # 在每根柱子上方标注数值
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    f"{bar.get_height():.1f}",
                    ha="center", va="bottom", fontsize=8)

    # 轴标签和标题
    ax.set_xlabel("评测分类", fontsize=12)
    ax.set_ylabel("综合评分", fontsize=12)
    ax.set_title("各分类模型综合评分对比", fontsize=15, fontweight="bold")
    # 将 X 轴刻度放在每组柱子中间
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


# ============================================================================
#  图表 3:热力图  -  模型 × 分类 评分矩阵
# ============================================================================

def plot_heatmap(results: list[dict], save_path: Optional[str] = None) -> str:
    """绘制热力图

    行为分类(问答,代码...),列为模型(ChatGPT,Claude,DeepSeek)
    颜色深浅代表综合分高低(深红 = 高分,浅黄 = 低分)

    参数:
        results: 评测结果列表
        save_path: 图片保存路径

    返回:
        保存的图片路径
    """
    _, cat_model_avg, meta = _prepare_data(results)
    models = meta["models"]
    categories = meta["categories"]

    # 构建二维数组 data[row][col] = 综合分
    data = []
    for c in categories:
        row = [cat_model_avg[c].get(m, 0) for m in models]
        data.append(row)
    data = np.array(data)

    fig, ax = plt.subplots(figsize=(8, 5))
    # YlOrRd 配色:黄色→橙色→红色渐变
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=4, vmax=10)

    # 在每个单元格中显示数值
    for i in range(len(categories)):
        for j in range(len(models)):
            ax.text(j, i, f"{data[i, j]:.1f}",
                    ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    # 深色背景用白字,浅色背景用黑字(阈值 7.5)
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


# ============================================================================
#  图表 4:延迟对比图  -  各模型平均响应速度
# ============================================================================

def plot_latency(results: list[dict], save_path: Optional[str] = None) -> str:
    """绘制模型平均响应延迟对比柱状图

    延迟 = 从发送请求到收到完整回答的时间(毫秒).
    这个指标反映模型的推理速度,对需要实时响应的场景很重要.

    参数:
        results: 评测结果列表
        save_path: 图片保存路径

    返回:
        保存的图片路径
    """
    models = sorted(set(r["model"] for r in results))

    # 计算每个模型的平均延迟
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

    # 在柱子上方标注具体毫秒数
    for bar, model in zip(bars, models):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 30,
                f"{avg_latency[model]:.0f}ms",
                ha="center", fontsize=11, fontweight="bold")

    ax.set_ylabel("平均响应时间 (ms)", fontsize=11)
    ax.set_title("模型平均响应速度对比", fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    if save_path is None:
        save_path = os.path.join(OUTPUT_DIR, "latency_comparison.png")
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


# ============================================================================
#  批量生成所有图表
# ============================================================================

def plot_all(results: list[dict]) -> list[str]:
    """一次生成全部 4 种可视化图表

    参数:
        results: 评测结果列表

    返回:
        所有图片路径的列表
    """
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
