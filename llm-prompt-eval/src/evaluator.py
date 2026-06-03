"""评测引擎 - 批量评测调度与结果管理"""

import json
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from .api_clients import BaseClient, ModelResponse, create_clients
from .metrics import compute_scores

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "prompts")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "evaluation_results")


def load_all_prompts() -> list[dict]:
    """加载所有 prompt 数据集"""
    all_prompts = []
    for filename in sorted(os.listdir(PROMPTS_DIR)):
        if filename.endswith(".json"):
            filepath = os.path.join(PROMPTS_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                for p in prompts:
                    p["source_file"] = filename.replace(".json", "")
                all_prompts.extend(prompts)
    return all_prompts


def run_single_eval(client: BaseClient, prompt: dict) -> dict:
    """对单个 prompt 的单个模型进行评测"""
    start = time.time()
    response = client.generate(prompt["id"], prompt["prompt"])
    elapsed = time.time() - start

    scores = compute_scores(response.content, prompt)

    return {
        "prompt_id": prompt["id"],
        "prompt_title": prompt["title"],
        "category": prompt["category"],
        "difficulty": prompt["difficulty"],
        "model": client.model_name,
        "response": response.content,
        "latency_ms": round(response.latency_ms or elapsed * 1000, 0),
        "tokens_used": response.tokens_used,
        "scores": scores,
        "eval_time": datetime.now().isoformat(),
    }


def run_batch_evaluation(clients: list[BaseClient] | None = None,
                         prompts: list[dict] | None = None,
                         max_workers: int = 3,
                         verbose: bool = True) -> list[dict]:
    """批量评测主流程"""
    if clients is None:
        clients = create_clients("mock")
    if prompts is None:
        prompts = load_all_prompts()

    total = len(prompts) * len(clients)
    if verbose:
        print(f"开始批量评测: {len(prompts)} 个 Prompt × {len(clients)} 个模型 = {total} 次评测\n")

    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for client in clients:
            for prompt in prompts:
                future = executor.submit(run_single_eval, client, prompt)
                futures[future] = (client.model_name, prompt["id"])

        for future in as_completed(futures):
            model, pid = futures[future]
            try:
                result = future.result()
                results.append(result)
                completed += 1
                if verbose:
                    scores = result["scores"]
                    print(f"[{completed}/{total}] {model} × {pid} ({result['category']}) "
                          f"→ 综合: {scores['综合分']:.1f} | "
                          f"准确:{scores['准确性']} 逻辑:{scores['逻辑性']} "
                          f"安全:{scores['安全性']}")
            except Exception as e:
                if verbose:
                    print(f"[{completed}/{total}] {model} × {pid} 失败: {e}")
                completed += 1

    return results


def save_results(results: list[dict], filename: str = "evaluation_results.json") -> str:
    """保存评测结果"""
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
    """加载已保存的评测结果"""
    if filepath is None:
        filepath = os.path.join(OUTPUT_DIR, "evaluation_results.json")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"评测结果文件不存在: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
