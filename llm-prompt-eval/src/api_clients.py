"""API 客户端封装 — 统一的模型调用接口

================================================================================
设计模式：策略模式 (Strategy Pattern)
  - BaseClient 定义统一接口 generate()
  - 每个具体客户端（MockClient / DeepSeekClient / OpenAIClient / ClaudeClient）
    实现自己的调用逻辑，但对外暴露完全相同的调用方式
  - 工厂函数 create_clients() 根据模式参数自动选择用哪些客户端

这样上层代码（evaluator.py）只需要调用 client.generate(prompt_id, text)
而不用关心底层是 mock 数据还是真实 API 请求。
================================================================================
"""

import json
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
#  数据类：模型响应
# ============================================================================
# dataclass 是 Python 的轻量级数据容器，自动生成 __init__、__repr__ 等方法
# 作用类似一个结构体，用于在各模块间传递「一次 API 调用的完整结果」

@dataclass
class ModelResponse:
    """封装一次模型调用的完整结果"""
    model_name: str        # 模型名称，如 "ChatGPT-4o"、"Claude-4-Sonnet"
    prompt_id: str         # 对应的 Prompt 编号，如 "QA-001"
    content: str           # 模型返回的文本内容
    latency_ms: float = 0.0  # 响应延迟（毫秒）
    tokens_used: int = 0     # 消耗的 token 数量


# ============================================================================
#  抽象基类 — 定义所有客户端的统一接口
# ============================================================================

class BaseClient(ABC):
    """所有模型客户端的抽象基类

    任何新模型的客户端只需继承此类并实现 generate() 方法即可接入评测框架。
    """

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        """调用模型生成回答（子类必须实现）

        参数:
            prompt_id: Prompt 编号（如 "QA-001"），用于关联结果
            prompt_text: 完整的 Prompt 文本

        返回:
            ModelResponse 对象，包含回答内容和调用元信息
        """
        ...


# ============================================================================
#  Mock 客户端 — 用于离线测试，无需 API Key
# ============================================================================
# 模拟数据从 data/evaluation_results/mock_responses.json 加载
# 该文件包含了预先写好的"模拟回答"，这样就可在没有网络/API Key 的情况下
# 完整跑通评测流程、验证代码逻辑

_MOCK_RESPONSES: dict[str, dict[str, str]] = {}


def _load_mock_responses():
    """加载模拟评测数据（惰性加载，只在第一次使用时读取文件）"""
    global _MOCK_RESPONSES
    # 从 src/api_clients.py 向上一级到项目根目录，再进入 data/evaluation_results/
    mock_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "evaluation_results", "mock_responses.json"
    )
    if os.path.exists(mock_path):
        with open(mock_path, "r", encoding="utf-8") as f:
            _MOCK_RESPONSES = json.load(f)
    else:
        _MOCK_RESPONSES = {}


class MockClient(BaseClient):
    """模拟客户端 — 从预置 JSON 加载回答，用于离线流程测试

    与真实客户端的区别：
      - 不会发送网络请求
      - 返回的数据来自 mock_responses.json
      - 延迟和 token 数随机生成（模拟真实场景的数值范围）
    """

    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        # 惰性加载：只在第一次调用时读取 mock 数据文件
        if not _MOCK_RESPONSES:
            _load_mock_responses()

        # 从 mock 数据中查找对应 prompt_id 和模型名的预设回答
        content = _MOCK_RESPONSES.get(prompt_id, {}).get(
            self.model_name,
            # 如果找不到对应的 mock 数据，返回一个占位文本
            f"[模拟] {self.model_name} 对 {prompt_id} 的占位响应。"
        )
        return ModelResponse(
            model_name=self.model_name,
            prompt_id=prompt_id,
            content=content,
            # 模拟真实 API 的延迟范围：800ms ~ 5000ms
            latency_ms=random.uniform(800, 5000),
            # 模拟真实 API 的 token 消耗范围：100 ~ 1000
            tokens_used=random.randint(100, 1000),
        )


# ============================================================================
#  真实 API 客户端
# ============================================================================
# 三个客户端的设计非常相似，核心流程：
#   1. 构造 HTTP 请求（Headers + JSON Body）
#   2. 发送 POST 请求到各厂商的 API 端点
#   3. 解析 JSON 响应，提取回答文本
#   4. 包装为 ModelResponse 返回
#
# 全部使用 Python 标准库 urllib，无需安装任何第三方 SDK。

class DeepSeekClient(BaseClient):
    """DeepSeek API 客户端

    使用方式：
      1. 在 DeepSeek 官网获取 API Key
      2. 设置环境变量：export DEEPSEEK_API_KEY="sk-..."
      3. 运行 python main.py --real
    """

    BASE_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        super().__init__(f"DeepSeek ({model})")
        # 优先使用传入的 key，否则从环境变量读取
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.model = model

    def generate(self, prompt_id: str, prompt_text: str) -> ModelResponse:
        import time
        import urllib.request

        # 没有 API Key 时返回错误提示，而不是崩溃
        if not self.api_key:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[错误] DeepSeek API key 未配置，请设置环境变量 DEEPSEEK_API_KEY"
            )

        # ---- 构造 HTTP 请求 ----
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
            "temperature": 0.7,   # 0.7 是通用任务的常用值（平衡创造性和确定性）
            "max_tokens": 2048,   # 最大输出长度
        }).encode("utf-8")

        # ---- 发送请求并计时 ----
        start = time.time()
        req = urllib.request.Request(self.BASE_URL, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # 从 DeepSeek 的响应格式中提取文本
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=content,
                latency_ms=(time.time() - start) * 1000,  # 转为毫秒
                tokens_used=usage.get("total_tokens", 0),
            )
        except Exception as e:
            # 网络错误、超时等异常不会中断整个评测流程
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[API 调用失败] {e}",
            )


class OpenAIClient(BaseClient):
    """OpenAI (ChatGPT) API 客户端

    使用方式：
      1. 在 OpenAI 官网获取 API Key
      2. 设置环境变量：export OPENAI_API_KEY="sk-..."
      3. 运行 python main.py --real
    """

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
    """Anthropic Claude API 客户端

    注意：Claude 的 API 格式与 OpenAI/DeepSeek 不同：
      - 请求头使用 x-api-key 而非 Authorization: Bearer
      - 需要 anthropic-version 头
      - 响应内容在 content 数组的 text 字段中（而非 choices[0].message.content）
      - System prompt 使用独立的 system 字段而非 messages 中的 role

    使用方式：
      1. 在 Anthropic Console 获取 API Key
      2. 设置环境变量：export ANTHROPIC_API_KEY="sk-ant-..."
      3. 运行 python main.py --real
    """

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

        # Claude 使用 x-api-key 而非 Bearer Token
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",  # 指定 API 版本
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
            # Claude 的响应格式：content 是一个数组，每项的 text 字段是文本片段
            content = "".join(
                block.get("text", "") for block in data.get("content", [])
            )
            usage = data.get("usage", {})
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=content,
                latency_ms=(time.time() - start) * 1000,
                # Claude 将 input 和 output token 分开计算
                tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            )
        except Exception as e:
            return ModelResponse(
                model_name=self.model_name, prompt_id=prompt_id,
                content=f"[API 调用失败] {e}",
            )


# ============================================================================
#  工厂函数 — 根据运行模式创建对应的客户端列表
# ============================================================================

def create_clients(mode: str = "mock",
                   deepseek_key: Optional[str] = None,
                   openai_key: Optional[str] = None,
                   anthropic_key: Optional[str] = None):
    """创建模型客户端列表（工厂函数）

    参数:
        mode: "mock" → 返回三个 MockClient（离线测试）
              "real" → 根据配置了哪些 API Key 来决定启用哪些真实客户端
        deepseek_key / openai_key / anthropic_key: 可选的 API Key（优先级高于环境变量）

    返回:
        BaseClient 列表，如 [MockClient("DeepSeek-V3"), MockClient("ChatGPT-4o"), ...]

    用法:
        clients = create_clients("mock")                # 全 mock
        clients = create_clients("real")                # 根据环境变量自动选择
        clients = create_clients("real", openai_key="sk-xxx")  # 指定 key
    """
    if mode == "mock":
        return [
            MockClient("DeepSeek-V3"),
            MockClient("ChatGPT-4o"),
            MockClient("Claude-4-Sonnet"),
        ]

    # 真实模式：哪个 Key 配了就用哪个，没配的不启用
    clients = []
    if deepseek_key or os.environ.get("DEEPSEEK_API_KEY"):
        clients.append(DeepSeekClient(deepseek_key))
    if openai_key or os.environ.get("OPENAI_API_KEY"):
        clients.append(OpenAIClient(openai_key))
    if anthropic_key or os.environ.get("ANTHROPIC_API_KEY"):
        clients.append(ClaudeClient(anthropic_key))

    # 如果一个真实客户端都没配，自动回退到 mock 模式
    return clients or [
        MockClient("DeepSeek-V3"),
        MockClient("ChatGPT-4o"),
        MockClient("Claude-4-Sonnet"),
    ]
