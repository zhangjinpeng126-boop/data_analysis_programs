"""评测引擎 — 批量评测调度与结果管理

================================================================================
这是评测流程的「调度中心」，负责：
  1. 从 data/prompts/ 加载所有 Prompt 数据集
  2. 将 Prompt × 模型 的组合分发给线程池并发执行
  3. 收集所有评测结果并保存为 JSON
  4. 提供结果加载接口供报告/可视化模块使用

并发模型：ThreadPoolExecutor（线程池）
  - I/O 密集型任务（API 调用）适合用多线程
  - max_workers 控制最大并发数，避免同时发送太多请求
================================================================================
"""

import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .api_clients import BaseClient, ModelResponse, create_clients
from .metrics import compute_scores


# ---- 路径常量 ----
# __file__ 是 src/evaluator.py，向上一级(dirname)得到项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
PROMPTS_DIR = os.path.join(_PROJECT_ROOT, "data", "prompts")
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "data", "evaluation_results")


# ============================================================================
#  1. 加载 Prompt 数据集
# ============================================================================

def load_all_prompts() -> list[dict]:
    """加载 data/prompts/ 目录下所有 JSON 文件中的 Prompt

    每个 JSON 文件对应一个场景分类（如 qa.json → 问答类），
    文件内部是一个 Prompt 列表，每个 Prompt 包含：
      - id: 唯一标识，如 "QA-001"
      - category: 分类，如 "问答"
      - difficulty: 难度（easy / medium / hard）
      - prompt: 实际发送给模型的文本
      - eval_weight: 评分权重，如 {"准确性": 0.5, "逻辑性": 0.3, "安全性": 0.2}
      - reference_facts / expected_length / eval_criteria: 评分参考信息

    返回:
        所有 Prompt 字典的列表（跨文件合并）
    """
    all_prompts = []
    for filename in sorted(os.listdir(PROMPTS_DIR)):
        if filename.endswith(".json"):
            filepath = os.path.join(PROMPTS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                # 记录来源文件（不含扩展名），如 "qa"、"code"，方便追溯
                for p in prompts:
                    p["source_file"] = filename.replace(".json", "")
                all_prompts.extend(prompts)
    return all_prompts


# ============================================================================
#  2. 单次评测
# ============================================================================

def run_single_eval(client: BaseClient, prompt: dict) -> dict:
    """对单个 Prompt 使用单个模型进行一次评测

    这是评测的最小执行单元。流程：
      1. 调用 client.generate() 获取模型回答
      2. 调用 metrics.compute_scores() 对回答打分
      3. 打包为结果字典返回

    参数:
        client: 模型客户端（MockClient 或真实 API 客户端）
        prompt: Prompt 数据字典

    返回:
        评测结果字典，包含 prompt 信息、模型名、回答内容、各维度评分等
    """
    start = time.time()
    response = client.generate(prompt["id"], prompt["prompt"])
    elapsed = time.time() - start

    # 调用评分模块，对回答进行五维打分
    scores = compute_scores(response.content, prompt)

    return {
        # ---- 题目信息 ----
        "prompt_id": prompt["id"],
        "prompt_title": prompt["title"],
        "category": prompt["category"],
        "difficulty": prompt["difficulty"],
        # ---- 模型信息 ----
        "model": client.model_name,
        "response": response.content,
        "latency_ms": round(response.latency_ms or elapsed * 1000, 0),
        "tokens_used": response.tokens_used,
        # ---- 评分结果 ----
        "scores": scores,
        "eval_time": datetime.now().isoformat(),
    }


# ============================================================================
#  3. 批量评测（核心流程）
# ============================================================================

def run_batch_evaluation(clients: list[BaseClient] | None = None,
                         prompts: list[dict] | None = None,
                         max_workers: int = 3,
                         verbose: bool = True) -> list[dict]:
    """批量评测主流程 — 并发执行所有 Prompt × Model 组合

    执行逻辑：
      1. 生成所有 (模型, Prompt) 的笛卡尔积
      2. 提交给线程池并发执行
      3. 使用 as_completed() 实时收集完成的结果（先完成的先处理）
      4. 每次完成打印一行进度

    参数:
        clients: 模型客户端列表，默认用 mock 模式
        prompts: Prompt 列表，默认加载所有
        max_workers: 线程池最大并发数（默认 3，避免对 API 服务器造成太大压力）
        verbose: 是否打印进度信息

    返回:
        所有评测结果的列表
    """
    # 默认值处理
    if clients is None:
        clients = create_clients("mock")
    if prompts is None:
        prompts = load_all_prompts()

    total = len(prompts) * len(clients)
    if verbose:
        print(f"开始批量评测: {len(prompts)} 个 Prompt × {len(clients)} 个模型 = {total} 次评测\n")

    results = []
    completed = 0

    # ThreadPoolExecutor 创建一个线程池，max_workers 控制同时运行的线程数
    # 每个线程执行一次 run_single_eval(client, prompt)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}  # Future → (模型名, prompt_id) 的映射，方便追

        # ---- 提交所有任务 ----
        for client in clients:
            for prompt in prompts:
                # submit() 不会阻塞，立即返回一个 Future 对象
                future = executor.submit(run_single_eval, client, prompt)
                futures[future] = (client.model_name, prompt["id"])

        # ---- 收集结果 ----
        # as_completed() 是一个迭代器：哪个任务先完成就先 yield 哪个
        for future in as_completed(futures):
            model, pid = futures[future]
            try:
                result = future.result()  # 获取 run_single_eval 的返回值
                results.append(result)
                completed += 1
                if verbose:
                    scores = result["scores"]
                    # 打印一行简洁的进度信息
                    print(f"[{completed}/{total}] {model} × {pid} ({result['category']}) "
                          f"→ 综合: {scores['综合分']:.1f} | "
                          f"准确:{scores['准确性']} 逻辑:{scores['逻辑性']} "
                          f"安全:{scores['安全性']}")
            except Exception as e:
                if verbose:
                    print(f"[{completed}/{total}] {model} × {pid} 失败: {e}")
                completed += 1  # 失败的也计入完成数

    return results


# ============================================================================
#  4. 结果持久化
# ============================================================================

def save_results(results: list[dict], filename: str = "evaluation_results.json") -> str:
    """将评测结果保存为 JSON 文件

    除了 results 数组，还会自动生成 meta 元信息（总数、时间等），
    方便后续加载时快速了解评测规模。

    参数:
        results: run_batch_evaluation() 的返回值
        filename: 输出文件名（默认 evaluation_results.json）

    返回:
        保存的文件路径
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    output = {
        "meta": {
            "total_prompts": len(set(r["prompt_id"] for r in results)),
            "total_models": len(set(r["model"] for r in results)),
            "total_evals": len(results),
            "eval_time": datetime.now().isoformat(),
        },
        "results": results,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n评测结果已保存至: {filepath}")
    return filepath


def load_results(filepath: Optional[str] = None) -> dict:
    """加载已保存的评测结果

    参数:
        filepath: JSON 文件路径，默认读取 data/evaluation_results/evaluation_results.json

    返回:
        {"meta": {...}, "results": [...]} 字典
    """
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "evaluation_results.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"评测结果文件不存在: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
