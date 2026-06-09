# 数据源说明 | Data Sources

## Kaggle 源数据 (主要来源)

### 1. LLM Benchmark Wars 2025-2026 | 24 Models Compared
- **Kaggle地址:** https://www.kaggle.com/datasets/alitaqishah/llm-benchmark-wars-2025-2026-24-models-compared
- **原始文件:** `kaggle_raw/llm_benchmark_comparison_2025_2026.csv`
- **数据规模:** 24个模型 × 31个维度
- **覆盖范围:**
  - 10家组织: OpenAI, Anthropic, Google DeepMind, Meta, DeepSeek, Alibaba, xAI, Mistral, IBM, Zhipu AI
  - 6大基准: MMLU, HumanEval, GPQA Diamond, SWE-Bench, HellaSwag, AIME 2025
  - 价格/速度/上下文窗口/许可证等维度
- **数据时间:** 2025-2026

### 2. 其他 Kaggle 数据源 (参考)
- LLM Showdown: 220+ AI Models | 57 Metrics — https://www.kaggle.com/datasets/rudrakumargupta/llm-showdown-200-ai-models-57-metrics
- LLM Benchmark Leaderboard Dataset (2024-2026) — https://www.kaggle.com/datasets/prajitdatta/llm-benchmark-leaderboard-dataset-20242026

## 分析用综合数据

> 以下CSV基于上述Kaggle源数据 + LMSYS Chatbot Arena + Artificial Analysis + SWE-Bench/AgentBench 综合整理

| 文件 | 说明 | 来源 |
|------|------|------|
| llm_benchmark_comparison.csv | 20款主流大模型(国际10+国内10)14维度对比 | Kaggle LLM Benchmark Wars |
| agent_capability_comparison.csv | 7款模型Agent能力6维度评估 | SWE-Bench + AgentBench + 综合评测 |

## 数据引用格式 (PPT最后一页建议)
```
数据来源:
- Kaggle: LLM Benchmark Wars 2025-2026 (alitaqishah)
  → 24 Models from OpenAI, Anthropic, Google, Meta, DeepSeek, Alibaba, etc.
- LMSYS Chatbot Arena (Chatbot Arena Elo Ratings)
- Artificial Analysis (API Pricing & Speed benchmarks)
- SWE-Bench + AgentBench (Agent capability evaluation)
```
