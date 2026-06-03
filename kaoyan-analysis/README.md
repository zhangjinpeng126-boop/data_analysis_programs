# 2025 年全国硕士研究生招生考试数据分析

基于 pandas + numpy + matplotlib 对 2025 年考研数据进行全流程数据分析，涵盖报名趋势、录取率、专硕/学硕结构、国家线变化等维度。

## 数据概览

| 数据集 | 说明 |
|--------|------|
| `registration.csv` | 2018-2025 年考研报名人数及同比变化 |
| `admission.csv` | 2021-2025 年录取人数、专硕/学硕分布、报录比 |
| `score_lines.csv` | 2024 vs 2025 年各学科 A 类国家线及变化 |

## 核心结论

- **报名人数连降两年**：2023 年达到 474 万峰值后持续下降，2025 年降至 388 万，降幅 11.4%
- **录取率触底回升**：2024 年仅 19.6%，2025 年回升至 22.5%，统考报录比约 4.45:1
- **专硕成绝对主力**：专硕占比从 2021 年的不到 50% 飙升至 2025 年的 69%
- **国家线全线下降**：13 个学科门类平均下降 10.2 分，经济学降幅最大（↓15 分）

## 图表输出

| 图表 | 文件 |
|------|------|
| 报名人数趋势（柱状图+折线图） | `output_registration_trend.png` |
| 录取率变化（折线图） | `output_admission_rate.png` |
| 专硕 vs 学硕结构（面积图+饼图） | `output_master_structure.png` |
| 各学科国家线变化（水平条形图） | `output_score_lines.png` |
| 2024 vs 2025 国家线对比（分组柱状图） | `output_score_comparison.png` |

## 技术栈

- **数据处理**：pandas（读写 CSV、清洗、聚合、统计分析）
- **数值计算**：numpy（数组操作、统计计算）
- **可视化**：matplotlib（柱状图、折线图、饼图、双 Y 轴、堆叠面积图、水平条形图）
- **环境**：Jupyter Notebook

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Jasper126/kaoyan-analysis.git
cd kaoyan-analysis

# 2. 安装依赖
pip install pandas numpy matplotlib jupyter

# 3. 启动 Jupyter
jupyter notebook kaoyan_2025_analysis.ipynb
```

## 项目结构

```
kaoyan-analysis/
├── kaoyan_2025_analysis.ipynb   # 主分析笔记本
├── 0A NumPy完整教程.ipynb       # NumPy 课件
├── 0B Pandas完整教程.ipynb      # Pandas 课件
├── 0C Matplotlib_终极复习.ipynb # Matplotlib 课件
├── 0D Seaborn_终极复习.ipynb    # Seaborn 课件
├── registration.csv             # 报名人数数据
├── admission.csv                # 录取情况数据
├── score_lines.csv              # 国家线数据
└── output_*.png                 # 分析图表输出
```

## 数据来源

教育部、研招网公开数据整理

## License

MIT
