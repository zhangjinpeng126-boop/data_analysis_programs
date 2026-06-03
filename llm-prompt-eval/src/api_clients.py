"""API 客户端封装 - 支持模拟模式与真实 API 调用"""

import json
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelResponse:
    model_name: str
    prompt_id: str
    content: str
    latency_ms: float = 0.0
    tokens_used: int = 0


class BaseClient(ABC):
    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        ...


# ---------------------------------------------------------------------------
# Mock 数据 - 模拟三个模型对不同 prompt 的响应
# ---------------------------------------------------------------------------

_MOCK_RESPONSES: dict[str, dict[str, str]] = {}


def _load_mock_responses():
    """加载模拟评测数据"""
    global _MOCK_RESPONSES
    mock_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "data", "evaluation_results", "mock_responses.json")
    if os.path.exists(mock_path):
        with open(mock_path, "r", encoding="utf-8") as f:
            _MOCK_RESPONSES = json.load(f)
    else:
        _MOCK_RESPONSES = {}


class MockClient(BaseClient):
    """模拟客户端 - 用于离线测试框架"""

    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        if not _MOCK_RESPONSES:
            _load_mock_responses()
        content = _MOCK_RESPONSES.get(prompt_id, {}).get(
            self.model_name,
            f"[模拟] {self.model_name} 对 {prompt_id} 的占位响应。"
        )
        return ModelResponse(
            model_name=self.model_name,
            prompt_id=prompt_id,
            content=content,
            latency_ms=random.uniform(800, 5000),
            tokens_used=random.randint(100, 1000),
        )


# ---------------------------------------------------------------------------
# 真实 API 客户端
# ---------------------------------------------------------------------------

class DeepSeekClient(BaseClient):
    """DeepSeek API 客户端"""

    BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        super().__init__(f"DeepSeek ({model})")
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model

    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        import time
        import urllib.request

        if not self.api_key:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[错误] DeepSeek API key 未配置，请设置环境变量 DEEPSEEK_API_KEY"
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个有帮助的 AI 助手。"},
                {"role": "user", "content": prompt_text},
            ],
            "temperature": 0.7,
            "max_tokens": 2048,
        }).encode("utf-8")

        start = time.time()
        req = urllib.request.Request(self.BASE_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=content,
                latency_ms=(time.time() - start) * 1000,
                tokens_used=usage.get("total_tokens", 0),
            )
        except Exception as e:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[API 调用失败] {e}",
            )


class OpenAIClient(BaseClient):
    """OpenAI (ChatGPT) API 客户端"""

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        super().__init__(f"ChatGPT ({model})")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model

    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        import time
        import urllib.request

        if not self.api_key:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[配置提示] 请设置 OPENAI_API_KEY 环境变量后重试。"
            )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }).encode("utf-8")

        start = time.time()
        req = urllib.request.Request(self.BASE_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=content,
                latency_ms=(time.time() - start) * 1000,
                tokens_used=usage.get("total_tokens", 0),
            )
        except Exception as e:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[API 调用失败] {e}",
            )


class ClaudeClient(BaseClient):
    """Anthropic Claude API 客户端"""

    BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        super().__init__(f"Claude ({model})")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model

    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        import time
        import urllib.request

        if not self.api_key:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[配置提示] 请设置 ANTHROPIC_API_KEY 环境变量后重试。"
            )

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        payload = json.dumps({
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt_text}],
        }).encode("utf-8")

        start = time.time()
        req = urllib.request.Request(self.BASE_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = "".join(block.get("text", "") for block in data.get("content", []))
            usage = data.get("usage", {})
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=content,
                latency_ms=(time.time() - start) * 1000,
                tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            )
        except Exception as e:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[API 调用失败] {e}",
            )


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def create_clients(mode: str = "mock", deepseek_key: Optional[str] = None,
                   openai_key: Optional[str] = None, anthropic_key: Optional[str] = None):
    """创建模型客户端列表"""
    if mode == "mock":
        return [
            MockClient("DeepSeek-V3"),
            MockClient("ChatGPT-4o"),
            MockClient("Claude-4-Sonnet"),
        ]
    clients = []
    if deepseek_key or os.environ.get("DEEPSEEK_API_KEY"):
        clients.append(DeepSeekClient(deepseek_key))
    if openai_key or os.environ.get("OPENAI_API_KEY"):
        clients.append(OpenAIClient(openai_key))
    if anthropic_key or os.environ.get("ANTHROPIC_API_KEY"):
        clients.append(ClaudeClient(anthropic_key))
    return clients or [MockClient("DeepSeek-V3"), MockClient("ChatGPT-4o"), MockClient("Claude-4-Sonnet")]
