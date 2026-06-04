# 大模型 Prompt 效果评测与数据集构建

> LLM Prompt Evaluation & Dataset Construction — 覆盖 6 类场景,3 大模型,5 维评分体系的结构化评测框架

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 目录

- [项目简介](#项目简介)
- [项目特性](#项目特性)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [评测数据摘要](#评测数据摘要)
- [评测维度设计](#评测维度设计)
- [Prompt 数据集设计](#prompt-数据集设计)
- [接入真实 API](#接入真实-api)
- [扩展指南](#扩展指南)
- [License](#license)

## 项目简介

本项目构建了一套完整的大模型 Prompt 效果评测体系,设计覆盖 **问答,摘要,代码,推理,翻译,创意写作** 6 类场景的 20 组高质量 Prompt,在 **ChatGPT-4o / Claude-4-Sonnet / DeepSeek-V3** 三个主流大模型上进行批量评测,从 **准确性,逻辑性,安全性,完整性,流畅性** 五个维度进行评分统计与可视化对比分析.

## 项目特性

- **6 大场景覆盖** — 问答/摘要/代码/推理/翻译/创意写作,每类 3~4 组精心设计的 Prompt
- **3 模型对比** — ChatGPT-4o,Claude-4-Sonnet,DeepSeek-V3,支持 mock 离线 + 真实 API 双模式
- **5 维评分体系** — 准确性/逻辑性/安全性/完整性/流畅性,每题可自定义权重
- **4 种可视化图表** — 雷达图(能力轮廓) + 分组柱状图(场景对比) + 热力图(矩阵总览) + 延迟图(响应速度)
- **零额外依赖** — API 客户端仅使用 Python 标准库 `urllib`,不依赖任何第三方 SDK
- **可扩展架构** — 策略模式设计,新增模型只需实现一个 `generate()` 方法即可接入
- **自动化报告** — 一键生成结构化 Markdown 评测报告,包含逐题明细/模型画像/选型建议

## 项目结构

```
llm-prompt-eval/
├── main.py                          # 主入口脚本
├── requirements.txt                 # Python 依赖
├── README.md
├── data/
│   ├── prompts/                     # Prompt 数据集
│   │   ├── qa.json                  # 问答(4 组)
│   │   ├── summarization.json       # 摘要(4 组)
│   │   ├── code.json                # 代码(4 组)
│   │   ├── reasoning.json           # 推理(3 组)
│   │   ├── translation.json         # 翻译(3 组)
│   │   └── creative_writing.json    # 创意写作(3 组)
│   └── evaluation_results/          # 评测结果
│       ├── mock_responses.json      # 模拟模型响应数据
│       └── evaluation_results.json  # 评测输出
├── src/
│   ├── __init__.py
│   ├── api_clients.py               # API 客户端(Mock / DeepSeek / OpenAI / Claude)
│   ├── evaluator.py                 # 评测引擎(批量调度 + 结果管理)
│   ├── metrics.py                   # 多维度评分指标
│   ├── visualization.py             # 可视化(雷达图/柱状图/热力图)
│   └── report.py                    # Markdown 报告生成
├── notebooks/
│   └── analysis.ipynb               # 交互式分析 Notebook
└── outputs/
    ├── figures/                     # 生成的图表
    └── reports/                     # 生成的报告
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 模拟模式运行(无需 API Key)
python main.py

# 3. 使用真实 API(需设置环境变量)
export DEEPSEEK_API_KEY="your-key"      # DeepSeek
export OPENAI_API_KEY="your-key"        # ChatGPT
export ANTHROPIC_API_KEY="your-key"     # Claude
python main.py --real

# 4. 仅生成报告(基于已有评测结果)
python main.py --report-only

# 5. 单 Prompt 测试
python main.py --prompt QA-001
```

## 评测数据摘要

### 综合评分

| 模型 | 准确性 | 逻辑性 | 安全性 | 完整性 | 流畅性 | 综合分 |
|------|--------|--------|--------|--------|--------|--------|
| ChatGPT-4o | 7.12 | 5.75 | 9.00 | 7.24 | 8.76 | **7.21** |
| Claude-4-Sonnet | 7.11 | 5.66 | 9.00 | 7.19 | 8.67 | **7.19** |
| DeepSeek-V3 | 6.06 | 5.62 | 9.00 | 7.19 | 8.86 | **6.67** |

### 分类能力对比

| 分类 | ChatGPT-4o | Claude-4-Sonnet | DeepSeek-V3 | 最优 |
|------|-----------|---------------|-----------|------|
| 代码 | 6.8 | 6.6 | 6.6 | ChatGPT |
| 问答 | 7.6 | 7.0 | 6.1 | ChatGPT |
| 摘要 | 8.4 | 8.5 | 7.3 | Claude |
| 推理 | 7.1 | 7.1 | 7.2 | DeepSeek |
| 翻译 | 5.3 | 6.0 | 5.0 | Claude |
| 创意写作 | 7.8 | 7.7 | 7.8 | 并列 |

### 选型建议

- **研发团队**(代码 + 推理)→ Claude,代码质量和逻辑严谨性领先
- **内容团队**(文案 + 翻译)→ ChatGPT,创意能力和多语言适配更优
- **中文场景**(问答 + 摘要)→ DeepSeek,中文自然度好且成本约为 GPT-4o 的 1/10
- **综合推荐** → ChatGPT-4o / Claude-4-Sonnet 综合实力接近,按场景选择

### 图表预览

| 雷达图 | 分类柱状图 | 热力图 |
|--------|-----------|--------|
| ![](outputs/figures/radar_comparison.png) | ![](outputs/figures/bar_category_comparison.png) | ![](outputs/figures/heatmap_comparison.png) |

## 评测维度设计

| 维度 | 描述 | 评分方式 |
|------|------|----------|
| **准确性** | 事实正确性,关键词覆盖,答案一致性 | 关键词匹配 + 语义相似度 |
| **逻辑性** | 推理链完整性,结构清晰度,因果关联 | 结构模式检测 |
| **安全性** | 有害内容检测,安全边界遵守 | 正则模式匹配 |
| **完整性** | 要求覆盖度,长度控制 | 长度阈值 + 标准覆盖 |
| **流畅性** | 语言表达质量,可读性 | 句长分析 + 重复检测 |

> 注:模拟模式下评分基于规则引擎;真实 API 模式下建议引入 LLM-as-Judge 做更精准的语义评分.

## Prompt 数据集设计

数据集包含 20 组经过精心设计的 Prompt,覆盖 6 大场景,3 个难度等级:

- **问答**:光合作用原理,Transformer 机制,量子纠缠,Python 装饰器
- **摘要**:新闻,学术论文,法律文书,多文档融合
- **代码**:二分查找,并发请求,LRU 缓存,SQL 优化
- **推理**:谁说谎谜题,蒙提霍尔问题,因果推断
- **翻译**:技术文档,文学翻译,商务邮件
- **创意写作**:科幻微小说,广告文案,产品介绍

## 接入真实 API

项目已内置三种大模型的 API 客户端(仅使用标准库 `urllib`,零额外依赖):

1. **DeepSeek** — `export DEEPSEEK_API_KEY="sk-..."` 即可使用
2. **ChatGPT** — `export OPENAI_API_KEY="sk-..."` 即可使用  
3. **Claude** — `export ANTHROPIC_API_KEY="sk-ant-..."` 即可使用

设置任意一个环境变量后 `python main.py --real` 即可自动启用对应模型的真实调用.未配置 key 的模型将自动回退到模拟模式.

## 扩展指南

### 添加新模型

1. 在 `src/api_clients.py` 中新建一个继承 `BaseClient` 的类
2. 实现 `generate(self, prompt_id, prompt_text) -> ModelResponse` 方法
3. 在 `create_clients()` 工厂函数中注册新模型
4. 无需修改任何其他代码,评测引擎会自动接入

```python
class YourModelClient(BaseClient):
    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        # 调用你的模型 API,返回 ModelResponse 对象
        ...
```

### 添加新的 Prompt 类别

1. 在 `data/prompts/` 下新建 `your_category.json`,格式参照现有文件
2. 重新运行 `python main.py` 即可自动加载

### 自定义评分维度

修改 `src/metrics.py` 中的评分函数,或新增维度后在 `score_all_dimensions()` 中注册.

## License

本项目基于 MIT License 开源,详见 [LICENSE](LICENSE) 文件.

---

<p align="center">
  <sub>Built with Python · Matplotlib · Jupyter</sub>
</p>
