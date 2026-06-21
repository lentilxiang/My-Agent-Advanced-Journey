# D05：Streaming 进阶 + 错误处理体系 + LLM Client 封装

> 目标：掌握生产级 Streaming 模式、系统化错误处理策略，封装一个可复用的 LLM Client 工具类。

---

## 1. Streaming 进阶

D01 讲了 Streaming 的基本概念（打字机效果、Agent 内部 vs UI），今天深入生产落地。

### 1.1 三种 Streaming 模式

```
模式一：同步迭代（D01 学的）
  for chunk in stream:
      print(chunk.choices[0].delta.content)
  → 简单直接，适合命令行 script

模式二：异步迭代（FastAPI / WebSocket）
  async for chunk in async_stream:
      yield chunk
  → 适合 Web 服务，不阻塞事件循环

模式三：回调模式（SDK 高级 API）
  stream.text_stream  # 只给文本 chunk
  stream.event_stream # 完整事件（含 tool_call）
```

### 1.2 Claude 的流式 API 更优雅

```python
"""
Claude SDK 的 stream 方法比 OpenAI 的 stream=True 更友好
"""
import anthropic

client = anthropic.Anthropic()

# Claude 的流式 API 有专门的 .stream() 方法
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "讲个故事"}],
) as stream:
    # text_stream 自动过滤，只给文本
    for text in stream.text_stream:
        print(text, end="", flush=True)

# 好处：
# 1. text_stream 自动处理 delta 拼接
# 2. 不需要手动判断 chunk.delta.content 是否为 None
# 3. with 语句自动管理连接
```

### 1.3 生产级 Streaming：FastAPI SSE

```python
"""
Web 应用中常用 Server-Sent Events (SSE) 推送 token
"""
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import OpenAI

app = FastAPI()
client = OpenAI()

@app.get("/chat/stream")
async def chat_stream(message: str):
    """SSE 流式返回"""

    async def generate():
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": message}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                # SSE 格式：data: xxx\n\n
                yield f"data: {delta.content}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )
```

### 1.4 Streaming + Tool Calls 处理

```python
"""
流式模式下处理工具调用 —— 需要拼接 delta
"""
import json

def stream_with_tools(messages: list, tools: list):
    """流式调用，同时正确处理 tool_calls"""

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        stream=True,
    )

    # 收集器
    content_parts = []
    tool_calls_acc = {}  # {index: {id, name, arguments_parts}}

    for chunk in stream:
        delta = chunk.choices[0].delta

        # 文本内容
        if delta.content:
            content_parts.append(delta.content)
            print(delta.content, end="", flush=True)  # 打字机效果

        # 工具调用 —— 需要累积
        for tc_delta in delta.tool_calls or []:
            idx = tc_delta.index

            if idx not in tool_calls_acc:
                tool_calls_acc[idx] = {
                    "id": "",
                    "function": {"name": "", "arguments": ""}
                }

            acc = tool_calls_acc[idx]
            if tc_delta.id:
                acc["id"] = tc_delta.id
            if tc_delta.function and tc_delta.function.name:
                acc["function"]["name"] += tc_delta.function.name
            if tc_delta.function and tc_delta.function.arguments:
                acc["function"]["arguments"] += tc_delta.function.arguments

    # 拼接完成，可以执行工具了
    if tool_calls_acc:
        print(f"\n\n[工具调用] {len(tool_calls_acc)} 个")
        for idx, tc in tool_calls_acc.items():
            args = json.loads(tc["function"]["arguments"])
            print(f"  → {tc['function']['name']}({args})")

    return {
        "content": "".join(content_parts),
        "tool_calls": list(tool_calls_acc.values()),
    }

# 测试
response = stream_with_tools(
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=WEATHER_TOOL,
)
```

### 1.5 流式拿 Token 用量

```python
# OpenAI 流式获取 usage
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    stream=True,
    stream_options={"include_usage": True},  # ← 关键！
)

for chunk in stream:
    if chunk.usage:
        print(f"输入: {chunk.usage.prompt_tokens}")
        print(f"输出: {chunk.usage.completion_tokens}")
        print(f"总计: {chunk.usage.total_tokens}")
    # usage 只在最后一个 chunk 里有值
```

---

## 2. 错误处理体系

### 2.1 错误分类速查

```
API 调用的五类错误

┌───────────────┬──────────┬──────────────┬────────────────────────┐
│    错误类型    │ HTTP码   │ 含义          │ 你的处理策略            │
├───────────────┼──────────┼──────────────┼────────────────────────┤
│ 认证错误       │ 401      │ Key 无效/过期 │ ❌ 不重试，检查配置     │
│ 权限不足       │ 403      │ 区域/模型限制  │ ❌ 不重试，检查权限     │
│ 限流           │ 429      │ 请求太快/太多  │ ✅ 重试，指数退避      │
│ 服务器错误     │ 500/502  │ OpenAI 挂了    │ ✅ 重试，指数退避      │
│ 超时           │ 无       │ 请求没响应     │ ✅ 重试，设 timeout     │
│ 连接错误       │ 无       │ 网络断开       │ ✅ 重试                │
│ 内容过滤       │ 400      │ 内容被审查     │ ❌ 不重试，清洗输入     │
│ Token 超限     │ 400      │ 超过上下文窗口 │ ❌ 不重试，截断上下文   │
└───────────────┴──────────┴──────────────┴────────────────────────┘
```

### 2.2 指数退避（Exponential Backoff）

```
为什么是指数退避而不是固定间隔？

固定间隔 3s 重试：
  0s → 等3s → 重试 → 等3s → 重试 → 等3s → 重试
  → 如果服务器正在恢复，3s 可能不够

指数退避 + 随机抖动：
  0s → 等1s → 重试 → 等2s → 重试 → 等4s → 重试 → ...
  → 给服务器越来越长的恢复时间
  → 加随机抖动防止"惊群效应"（所有客户端同时重试）
```

### 2.3 手工实现（无依赖）

```python
import time
import random
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError, InternalServerError

client = OpenAI()

# 可重试的错误类型
RETRYABLE_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

def call_llm_with_retry(
    messages,
    tools=None,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
) -> dict:
    """
    带指数退避的 LLM 调用

    Args:
        max_retries: 最大重试次数
        initial_delay: 初始等待秒数
        max_delay: 最大等待秒数（防止无限等待）
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                timeout=30,  # 超时设置
            )
            return response  # 成功，直接返回

        except RateLimitError as e:
            if attempt == max_retries:
                raise  # 重试耗尽
            print(f"[429 限流] 第 {attempt+1} 次重试，等待 {delay:.1f}s")
            time.sleep(delay + random.uniform(0, delay * 0.5))  # +50% 抖动
            delay = min(delay * 2, max_delay)  # 翻倍，但不超上限

        except (APITimeoutError, APIConnectionError, InternalServerError) as e:
            if attempt == max_retries:
                raise
            print(f"[{type(e).__name__}] 第 {attempt+1} 次重试，等待 {delay:.1f}s")
            time.sleep(delay)
            delay = min(delay * 2, max_delay)

        except Exception as e:
            # 不可重试的错误（401, 400 等）
            print(f"[不可重试] {type(e).__name__}: {e}")
            raise

    raise RuntimeError("不应该到这里")
```

### 2.4 使用 Tenacity 库（生产推荐）

```python
"""
Tenacity：Python 重试库，比手写更灵活
pip install tenacity
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from openai import RateLimitError, APITimeoutError, APIConnectionError, InternalServerError
import logging

logger = logging.getLogger(__name__)

RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

@retry(
    retry=retry_if_exception_type(RETRYABLE),
    wait=wait_exponential(multiplier=1, min=1, max=60),  # 1s → 2s → 4s → ... 最多60s
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(logger, logging.WARNING),  # 自动记日志
)
def call_llm(messages, tools=None):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        timeout=30,
    )

# 调用时完全不需要写重试代码
response = call_llm([{"role": "user", "content": "你好"}])
```

### 2.5 使用 backoff 库（另一种选择）

```python
"""
backoff：更轻量的重试库
pip install backoff
"""
import backoff

@backoff.on_exception(
    backoff.expo,                    # 指数退避
    (RateLimitError, APITimeoutError),
    max_tries=5,
    max_time=120,                    # 总共最多 120s
)
def call_llm_backoff(messages):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        timeout=30,
    )
```

---

## 3. LLM Client 工具类封装

合并 D01-D05 所有知识，封装一个**生产可用的 LLM Client**。

### 3.1 完整实现

```python
"""
llm_client.py —— 生产级 LLM Client 工具类

特性：
  - 统一 OpenAI / Anthropic 接口
  - 非流式 + 流式
  - 指数退避重试
  - 超时控制
  - 错误分类
  - Token 用量追踪
  - 结构化输出支持
  - Function Calling 支持
"""
import time
import random
import json
from typing import Optional, Iterator, Literal
from pydantic import BaseModel
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError, InternalServerError

RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)


class LLMClient:
    """
    生产级 LLM 客户端

    使用示例：
        client = LLMClient(provider="openai", model="gpt-4o-mini")
        reply = client.chat("你好")
        reply = client.chat_with_tools("北京天气", tools=[...])
        person = client.chat_structured("张三28岁", schema=Person)
        for chunk in client.chat_stream("讲个故事"):
            print(chunk, end="")
    """

    def __init__(
        self,
        provider: Literal["openai", "anthropic"] = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0,
        max_tokens: int = 4096,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries

        if provider == "openai":
            self._client = OpenAI(timeout=timeout)
        elif provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic(timeout=timeout)
        else:
            raise ValueError(f"不支持的 provider: {provider}")

        # 用量统计
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    # ======== 核心调用 ========

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """基础对话 —— 发一句话，收回一句话"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = self._call_with_retry(messages=messages, temperature=temperature)
        return response.choices[0].message.content

    def chat_structured(
        self,
        user_message: str,
        schema: type[BaseModel],
        system_prompt: Optional[str] = None,
    ):
        """结构化输出 —— D03 的 parse() 封装"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = self._client.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=schema,
            temperature=0,  # 结构化强制用 0
        )
        self._update_usage(response.usage)
        return response.choices[0].message.parsed

    def chat_with_tools(
        self,
        user_message: str,
        tools: list[dict],
        system_prompt: Optional[str] = None,
        tool_choice: str = "auto",
    ) -> dict:
        """
        带工具调用的对话 —— D04 的 Function Calling 封装
        返回 {"content": str|None, "tool_calls": list}
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = self._call_with_retry(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )

        msg = response.choices[0].message
        result = {
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in (msg.tool_calls or [])
            ],
        }
        return result

    def chat_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
    ) -> Iterator[str]:
        """流式对话 —— 返回 token 迭代器"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        for chunk in stream:
            if chunk.usage:
                self._update_usage(chunk.usage)
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    # ======== Agent 循环 ========

    def agent_loop(
        self,
        user_message: str,
        tools: list[dict],
        tool_map: dict,
        system_prompt: Optional[str] = None,
        max_turns: int = 10,
    ) -> str:
        """
        Agent 执行循环 —— 自动处理多轮工具调用
        这是 D04 的 agent 循环的封装版本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        for turn in range(max_turns):
            response = self._call_with_retry(messages=messages, tools=tools)
            msg = response.choices[0].message
            messages.append(msg)

            # 没有工具调用 → 返回文本
            if not msg.tool_calls:
                return msg.content or ""

            # 执行工具调用
            for tc in msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)
                print(f"  🔧 {func_name}({func_args})")

                func = tool_map.get(func_name)
                if func is None:
                    result = f"工具 {func_name} 不存在"
                else:
                    try:
                        result = func(**func_args)
                    except Exception as e:
                        result = f"工具执行错误: {e}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

        return "达到最大轮次限制"

    # ======== 内部方法 ========

    def _call_with_retry(self, messages, tools=None, tool_choice=None, temperature=None):
        """带重试的底层调用"""
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            try:
                kwargs = dict(
                    model=self.model,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.temperature,
                    max_tokens=self.max_tokens,
                )
                if tools:
                    kwargs["tools"] = tools
                if tool_choice:
                    kwargs["tool_choice"] = tool_choice

                response = self._client.chat.completions.create(**kwargs)
                if response.usage:
                    self._update_usage(response.usage)
                return response

            except RETRYABLE as e:
                if attempt == self.max_retries:
                    raise
                print(f"[重试 {attempt+1}/{self.max_retries}] {type(e).__name__}，等待 {delay:.1f}s")
                time.sleep(delay + random.uniform(0, delay * 0.3))
                delay = min(delay * 2, 30)

    def _update_usage(self, usage):
        """累计 token 用量"""
        if usage:
            self.total_prompt_tokens += usage.prompt_tokens or 0
            self.total_completion_tokens += usage.completion_tokens or 0

    @property
    def usage_summary(self) -> dict:
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }


# ============ 使用示例 ============
if __name__ == "__main__":
    llm = LLMClient(provider="openai", model="gpt-4o-mini", temperature=0.7)

    # 1. 基础对话
    print(llm.chat("用一句话介绍 Python"))

    # 2. 结构化输出
    from pydantic import BaseModel
    class Person(BaseModel):
        name: str
        age: int
    person = llm.chat_structured("张三今年28岁", schema=Person)
    print(f"{person.name}, {person.age}岁")

    # 3. 流式输出
    print("流式: ", end="")
    for token in llm.chat_stream("写一首关于编程的短诗"):
        print(token, end="", flush=True)
    print()

    # 4. 用量统计
    print(f"用量: {llm.usage_summary}")

    # 5. Agent 循环
    reply = llm.agent_loop(
        user_message="北京天气怎么样？",
        tools=TOOLS,       # 来自 D04
        tool_map=TOOL_MAP, # 来自 D04
    )
    print(reply)
```

### 3.2 选择建议

```python
"""
什么时候用哪种方式？

单纯聊天：         llm.chat("你好")
结构化输出：        llm.chat_structured("...", schema=MyModel)
工具调用（单次）：   llm.chat_with_tools("...", tools=[...])
工具调用（多轮）：   llm.agent_loop("...", tools=[...], tool_map={...})
用户可见的流式：    for t in llm.chat_stream("..."):
                       print(t)

生产环境：用上面的 LLMClient 类
快速原型：直接用 OpenAI SDK（D01-D04 的做法）
"""
```

---

## 4. 动手练习

```text
[ ] 练习 1：完善 LLMClient，加入 Anthropic provider 支持
           - chat() / chat_stream() / chat_with_tools() 三个方法
           - 适配 Claude 的 tool_use / tool_result 格式

[ ] 练习 2：给 LLMClient 加一个"熔断器"
           - 连续失败 5 次 → 熔断 30 秒
           - 30 秒后尝试一次，成功则恢复，失败则继续熔断

[ ] 练习 3：写一个 load_test 脚本
           - 并发 10 个请求
           - 观察哪些被限流，哪些成功
           - 验证指数退避是否有效

[ ] 练习 4：实现 streaming 的断线重连
           - 流式输出中断后，从已接收的 token 处恢复
           - 提示：需要记录已接收的 token 数，重新请求时跳过

[ ] 练习 5：在 LLMClient 中加入 logging
           - 记录每次 API 调用的模型、耗时、token 用量、是否重试
           - 用 structlog 或 logging 库
```

---

## 5. 关键收获

### 5.1 错误处理决策树

```
API 返回错误了 →
  ├── 401/403 → 不重试，检查 Key / 权限
  ├── 429 → 重试 + 指数退避 + jitter
  ├── 500/502 → 重试 + 指数退避
  ├── Timeout → 重试，检查 timeout 设置是否合理
  ├── 400 (content filter) → 不重试，清洗输入
  └── 400 (token limit) → 不重试，截断上下文
```

### 5.2 LLMClient 是你后续所有 Agent 的底座

```
D06 周六：用 LLMClient + Function Calling 做一个可调用 5 个工具的 Agent
  → 直接用 llm.agent_loop(...)
  → 你不需要再写重试、错误处理、streaming
  → 专注于工具设计和 prompt 优化即可
```

### 5.3 D01-D05 完整能力链

```
D01: 调用 API            → 能"说话"
D02: System Prompt       → 能"扮演"
D03: Structured Outputs  → 能"可靠输出"
D04: Function Calling    → 能"用工具"
D05: LLMClient 封装      → 能"稳定运行"
                              ↑
                    五块积木 = 生产级 Agent 的基础
                    
明天 D06：把零部件组装成完整的 Agent！
```

---

## 参考

- [OpenAI Rate Limits Guide](https://developers.openai.com/api/docs/guides/rate-limits)
- [OpenAI Production Best Practices](https://developers.openai.com/api/docs/guides/production-best-practices)
- [OpenAI Streaming Guide](https://developers.openai.com/api/docs/guides/streaming-responses)
- [Anthropic Streaming Guide](https://docs.anthropic.com/en/docs/build-with-claude/streaming)
- [Tenacity 文档](https://tenacity.readthedocs.io/)
