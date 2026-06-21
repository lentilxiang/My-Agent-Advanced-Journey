# D07：第1周复习总结 —— LLM API 速查笔记

> 目标：把 D01-D06 的知识压缩成一页速查，以后调 API 直接看这个。

---

## 1. API 调用速查

### 1.1 OpenAI 单次调用

```python
from openai import OpenAI
client = OpenAI()  # 自动读 OPENAI_API_KEY

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "你是 Python 专家"},
        {"role": "user", "content": "你好"},
    ],
    temperature=0,
    max_tokens=4096,
)
print(response.choices[0].message.content)
print(response.usage.total_tokens)  # token 用量
```

### 1.2 Claude 单次调用

```python
import anthropic
client = anthropic.Anthropic()  # 自动读 ANTHROPIC_API_KEY

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system="你是 Python 专家",
    messages=[{"role": "user", "content": "你好"}],
)
print(response.content[0].text)
```

### 1.3 OpenAI vs Claude 关键差异

```
                 OpenAI                   Claude
                 ──────                   ──────
system prompt    messages[0].role         独立 system 参数
max_tokens       可选                      必填
content 位置     choices[0].message        content[0].text
stream           参数 stream=True          方法 client.messages.stream()
tool schema      function.parameters       input_schema
tool 结果        role="tool" message       role="user" + tool_result block
```

---

## 2. 消息角色速查

```python
# 三种角色，一个模板
messages = [
    {
        "role": "system",
        "content": """
<role>你是 XXX</role>
<behavior>规则1 / 规则2</behavior>
<format>输出格式要求</format>
<boundaries>什么不能做</boundaries>
        """
    },
    {"role": "user", "content": "用户说的话"},
    {"role": "assistant", "content": "上一轮你说的"},      # 多轮对话才有
]
```

---

## 3. 参数速查

### 3.1 Temperature 选择

```
temperature = 0     → 代码、分类、提取、数学（确定性）
temperature = 0.3   → 正式文案、商务邮件
temperature = 0.7   → 聊天、角色扮演（默认推荐）
temperature = 1.0   → 创意写作、头脑风暴
temperature > 1.0   → 基本不用，输出不可控
```

### 3.2 其他关键参数

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",   # 性价比最高
    temperature=0,          # 精确任务用0
    top_p=0.9,              # 配合 temperature 使用
    max_tokens=4096,        # 输出最大 token 数
    seed=42,                # 固定随机种子（可复现）
    timeout=30,             # 超时秒数
    # stream=True,          # 需要打字机效果时
    # stream_options={"include_usage": True},  # 流式拿 token 用量
)
```

---

## 4. Structured Outputs 速查

```python
from pydantic import BaseModel
from openai import OpenAI
client = OpenAI()

# 1. 定义 Schema
class MyOutput(BaseModel):
    field1: str
    field2: int
    field3: list[str]

# 2. 调用
completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "..."}],
    response_format=MyOutput,  # 直接传 Pydantic 模型
    temperature=0,  # 结构化输出必须用 0
)

# 3. 拿到结果
result = completion.choices[0].message.parsed   # Pydantic 对象
refusal = completion.choices[0].message.refusal  # None 或拒绝原因

if result:
    print(result.field1)
elif refusal:
    print(f"模型拒绝: {refusal}")
```

### LangChain 跨模型版本

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)  # 一切换

structured_llm = llm.with_structured_output(MyOutput)
result = structured_llm.invoke([HumanMessage(content="...")])
# → MyOutput 对象，和上面一样
```

---

## 5. Function Calling 速查

### 5.1 完整流程模板

```python
import json
from openai import OpenAI
client = OpenAI()

# ===== Step 1: 定义工具 =====
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"}
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        "strict": True,
    }
}]

# ===== Step 2: 工具函数 =====
def get_weather(city: str) -> str:
    return f"{city}: 25°C，晴"

TOOL_MAP = {"get_weather": get_weather}

# ===== Step 3: Agent 循环 =====
def run_agent(user_msg, max_turns=10):
    messages = [{"role": "user", "content": user_msg}]

    for turn in range(max_turns):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            temperature=0,
        )
        msg = response.choices[0].message
        messages.append(msg)  # ← 别忘！

        if not msg.tool_calls:    # 不调工具 → 返回文本
            return msg.content

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)  # ← 别忘了 json.loads
            result = TOOL_MAP[tc.function.name](**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,  # ← id 必须匹配
                "content": str(result),
            })

    return "达到最大轮次"
```

### 5.2 tool_choice 四种模式

```python
tool_choice="auto"                                     # 默认，模型自己决定
tool_choice="required"                                 # 必须调工具
tool_choice={"type":"function","function":{"name":"x"}}# 强制调指定工具
tool_choice="none"                                     # 禁止调工具
```

### 5.3 常见坑速查

| 坑 | 解决 |
|----|------|
| arguments 当 dict | `json.loads(tc.function.arguments)` |
| 忘加 assistant msg | `messages.append(msg)` 在 tool 之前 |
| tool_call_id 乱写 | 必须用 `tc.id` |
| 忘传 tools 第二轮 | 每轮都传 `tools=TOOLS` |
| 没判断 tool_calls | `if msg.tool_calls:` 先判断 |
| 无死循环保护 | `max_turns=10` + 重复签名检测 |
| 工具异常崩溃 | 每个调用包 `try/except` |

---

## 6. Streaming 速查

```python
# 非流式（Agent 内部用）
response = client.chat.completions.create(...)
text = response.choices[0].message.content

# 流式（用户界面用）
stream = client.chat.completions.create(..., stream=True)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)

# 流式 + token 用量
stream = client.chat.completions.create(
    ..., stream=True,
    stream_options={"include_usage": True}  # ← 最后一个 chunk 有 usage
)
for chunk in stream:
    if chunk.usage:
        print(chunk.usage.total_tokens)
```

---

## 7. 错误处理速查

### 7.1 什么时候重试

```
401 → 不重试，检查 API Key
403 → 不重试，检查权限
429 → 重试，指数退避
500 → 重试，指数退避
Timeout → 重试
Connection Error → 重试
400(content) → 不重试，清洗输入
400(token) → 不重试，截断上下文
```

### 7.2 重试模板（无依赖版）

```python
import time, random
from openai import RateLimitError, APITimeoutError, APIConnectionError, InternalServerError

RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)

def api_call_with_retry(messages, max_retries=3):
    delay = 1.0
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, timeout=30
            )
        except RETRYABLE as e:
            if attempt == max_retries:
                raise
            time.sleep(delay + random.uniform(0, delay * 0.3))
            delay = min(delay * 2, 30)
```

---

## 8. LLMClient 速查

```python
from llm_client import LLMClient  # D05 封装的

llm = LLMClient(provider="openai", model="gpt-4o-mini", temperature=0.7)

# 5 个方法覆盖所有场景
reply = llm.chat("你好")                                    # 基础对话
result = llm.chat_structured("张三28岁", schema=Person)     # 结构化输出
reply = llm.agent_loop("北京天气？", tools, tool_map)       # 多轮工具调用
for t in llm.chat_stream("讲故事"):                         # 流式输出
    print(t, end="")

print(llm.usage_summary)  # 累计 token 用量
```

---

## 9. 开发流程速查

```
写一个 LLM 功能的标准流程：

1. System Prompt → 用 D02 四要素模板写
2. 如果输出有固定结构 → D03 Structured Outputs
3. 如果需要外部数据 → D04 Function Calling
4. 用户可见 → D05 Streaming
5. 包 try/except + 重试 → D05 错误处理
6. 多轮工具调用 → D06 Agent 循环
```

---

## 10. 自检清单

```
[ ] 能不用查文档写出 OpenAI 调用代码
[ ] 能写出含四要素的 System Prompt
[ ] 知道 Temperature 0 / 0.7 / 1.0 分别用于什么场景
[ ] 知道 JSON Mode 和 Structured Outputs 的区别
[ ] 能用 Pydantic 定义 Schema、用 parse() 获取结构化输出
[ ] 能写出工具定义（含 strict + additionalProperties）
[ ] 能写出完整的 Agent 循环（调工具 → 返回结果 → 继续）
[ ] 知道 5 个常见 Function Calling 的坑
[ ] 知道 429/500/timeout 该不该重试
[ ] 能手写指数退避（三行核心代码）
[ ] 会用 LLMClient 替代原生 SDK 做日常调用
[ ] 能区分什么时候用流式、什么时候用非流式
```

---

## 11. 面试高频题（第1周知识点）

### 12.1 第1梯队（必问）

**Q1: Function Calling 工作原理——模型真的执行了函数吗？**

```
标准答案：不执行。模型只输出结构化的 JSON 意图（函数名 + 参数），
应用层解析后执行函数，结果返回模型，模型基于结果生成最终回复。
模型是"决策者"，代码是"执行者"。

每一轮流程：
  用户提问 → LLM输出 {"name":"get_weather","arguments":{"city":"北京"}}
  → 你的代码执行 get_weather("北京") → 结果注入上下文
  → LLM 生成 "北京今天25°C，晴"
```

**Q2: 三种消息角色各自作用？为什么不拼成一串文本？**

```
System  = 导演给演员的指令——定义行为规则、角色人设
User    = 观众说的话——用户输入
Assistant = 演员上一句台词——模型的历史回复

拼成一串的问题：
  模型无法区分"指令"和"对话内容"，优先级混乱
  用户输入里可能包含和 system prompt 冲突的内容
  角色分离让模型知道"哪些是规则必须遵守、哪些是对话可以回应"
```

**Q3: Temperature 控制什么？0 和 0.7 的区别？**

```
Temperature 控制随机度，不是聪明度。

0   → 每步选概率最高的 token，结果确定可复现
      适合：代码、分类、提取、数学
0.7 → 在 TOP token 中按概率采样，结果多样自然
      适合：聊天、角色扮演、写作
>1  → 接近随机，输出不可控，基本不用

追问："temperature=0 就一定正确吗？"
答：不一定。0 保证确定性（同样的输入同样的输出），
   但不保证正确性。正确性靠 system prompt + 测试 + 校验保证。
```

### 12.2 第2梯队（常问）

**Q4: Token 是什么？上下文窗口超了怎么办？**

```
Token = 模型处理文本的最小单位（不是"字"，中文约1字≈1.5-2 token）

窗口超限的三种策略：
  滑动窗口：保留最近 N 轮对话，丢弃更早的
  摘要压缩：用 LLM 把历史总结成一段摘要，替代原文
  优先级保留：System Prompt（永远保留）+ 重要信息 + 最近对话

追问："怎么估算一次请求消耗多少 token？"
答：用 tiktoken 库预计算，或从 API 返回的 response.usage 获取
    （prompt_tokens + completion_tokens + total_tokens）
```

**Q5: Structured Outputs 和 JSON Mode 有什么区别？**

```
JSON Mode (response_format={"type":"json_object"})：
  只保证输出是合法 JSON
  不保证字段名、类型、必填字段符合预期

Structured Outputs (response_format={"type":"json_schema",...})：
  保证字段名、类型、必填全部符合 Schema
  支持 Pydantic 自动校验（client.chat.completions.parse()）
  支持 refusal 检测（message.refusal）
  推荐：生产环境用 Structured Outputs
```

**Q6: Agent 内部为什么用非流式？**

```
Agent 内部需要解析完整的工具调用 JSON：
  → {"name":"search","args":{"query":"xxx"}}
  → 流式拿到一半 {"name":"search","args":{"qu 没法用

用户界面用流式：
  → 打字机效果，用户感知延迟低
  → 不需要解析，直接展示 token

结论：Agent 内部非流式，用户界面流式，两者不矛盾。
```

### 12.3 第3梯队（答出来加分）

**Q7: 429 限流 / 500 错误怎么处理？**

```
401/403 → 不重试，检查 Key/权限
429 → 重试，指数退避 + 随机抖动
500 → 重试，指数退避
Timeout → 重试，检查超时设置

指数退避原理：
  等1s → 重试 → 等2s → 重试 → 等4s → 重试 ...
  加 random jitter 防止所有客户端同时重试（惊群效应）
```

**Q8: OpenAI 和 Claude API 的关键差异？**

```
               OpenAI                    Claude
System prompt   messages[0].role          独立 system 参数
max_tokens      可选                      必填
工具 schema      function.parameters       input_schema
调用结果        message.tool_calls         content 中 tool_use block
结果返回        role="tool" message        role="user" + tool_result
streaming       stream=True 参数          .stream() 方法
```

### 12.4 面试官爱追问的角度

```
Function Calling：
  "模型传了错误的参数怎么办？"
  → 应用层校验参数 → 把错误信息返回给模型 → 模型自己修正重试

Token：
  "一个中文字大概多少 token？"
  → 约 1.5-2 个 token，英文约 0.75 token/词

Temperature：
  "Top-p 和 Temperature 怎么配合？"
  → Temperature 缩放概率分布（拉尖或压扁）
  → Top-p 裁掉低概率尾巴
  → 先调 temperature，效果不够再加 top_p
```

---

## 12. LangChain 对照速查（第1周原生 API → LangChain）

学原生 API 是为了理解底层，但生产项目推荐用 LangChain——跨模型、少写代码。

### 12.1 基础调用对比

```python
# ===== 原生 OpenAI =====
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "你好"}],
    temperature=0,
)
print(response.choices[0].message.content)

# ===== LangChain（换个模型只改两行）=====
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
response = llm.invoke([HumanMessage(content="你好")])
print(response.content)
```

### 12.2 切换模型

```python
# 原生：换模型 = 换 SDK + 改 API 字段名
# OpenAI: client.chat.completions.create(messages=[...])
# Claude:  client.messages.create(system="...", messages=[...])

# LangChain：换模型 = 改两行导入
from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

response = llm.invoke([HumanMessage(content="你好")])
# ↑ 调用代码完全不变
print(response.content)
```

### 12.3 System Prompt

```python
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

response = llm.invoke([
    SystemMessage(content="你是鲁迅，用白话文风格对话。回答150字以内。"),
    HumanMessage(content="怎么看AI写文章？"),
])
print(response.content)
```

### 12.4 Structured Outputs

```python
# 原生：
# completion = client.chat.completions.parse(
#     model="gpt-4o-mini",
#     messages=[...],
#     response_format=Person,
# )
# result = completion.choices[0].message.parsed

# LangChain（一行 with_structured_output）：
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_llm = llm.with_structured_output(Person)
result = structured_llm.invoke([HumanMessage(content="张三，28岁")])
# → Person(name='张三', age=28)
```

### 12.5 Function Calling / Tool Use

```python
# 原生：定义 dict schema + 手动 json.loads + while 循环
# LangChain：@tool 装饰器 + bind_tools + 自动解析

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage

# 1. 用装饰器定义工具（不用手写 JSON Schema！）
@tool
def get_weather(city: str) -> str:
    """获取指定城市的实时天气信息。"""
    return f"{city}: 25°C，晴"

@tool
def calculate(expression: str) -> str:
    """执行数学计算。"""
    return str(eval(expression))

# 2. 绑定工具到 LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools([get_weather, calculate])

# 3. 调用
messages = [HumanMessage(content="北京天气怎么样？")]
response = llm_with_tools.invoke(messages)

# 4. response.tool_calls 已经是解析好的
print(response.tool_calls)
# → [{'name': 'get_weather', 'args': {'city': '北京'}, 'id': 'call_xxx'}]

# 5. Agent 循环
messages.append(response)
for tc in response.tool_calls:
    if tc["name"] == "get_weather":
        result = get_weather.invoke(tc["args"])
    messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

final = llm_with_tools.invoke(messages)
print(final.content)
```

### 12.6 LangChain 的代价

```
LangChain 帮你做了什么：
  ✅ 跨模型统一接口（换模型只改两行）
  ✅ @tool 装饰器自动生成 JSON Schema
  ✅ bind_tools() 自动处理 tool_choice
  ✅ with_structured_output() 一行搞定 Pydantic 输出
  ✅ ToolMessage 封装 tool_call_id 关联
  ✅ 流式/非流式统一 .stream() 方法

LangChain 的代价：
  ❌ 多一层抽象，调试比原生难
  ❌ 版本升级经常 breaking change
  ❌ 简单任务杀鸡用牛刀
  ❌ 出了 bug 要查两层（SDK + LangChain）
```

### 12.7 什么时候用哪个

```
学的时候：     原生 SDK → 理解底层
快速原型：     原生 SDK → 最直接
单模型项目：   原生 SDK → 没必要加 LangChain
多模型切换：   LangChain → 换模型成本极低
复杂 Agent：   LangGraph（第6周学）→ 比 LangChain 更适合 Agent
团队项目：     LangChain/LangGraph → 统一接口减少团队争论
```

---

## 13. 下周预告

```
第2周：Agent 设计模式——纯代码手写

D08 理解 ReAct 循环：Thought→Action→Observation
D09 纯 Python 实现 ReAct Agent（3 个工具）
D10 工具系统设计：注册机制、描述模板、参数校验
D11 实现 Plan-and-Execute 模式
D12 实现 Reflection 模式
D13 3 种模式对比分析
D14 增强版 Agent（更多工具）

关键转变：
  第1周：学会调 API → "能用 LLM"
  第2周：学会设计 Agent 推理循环 → "会做 Agent"
```

---

## 参考

- D01-D06 学习笔记（完整知识点）
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Anthropic API Reference](https://docs.anthropic.com/en/api)
- [agent-interview-hub 知识库](../agent-interview-hub/)
