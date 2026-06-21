# D04：Function Calling 工具调用入门

> 目标：理解 Function Calling 完整流程，实现多工具调用的 Agent 雏形（查天气 + 计算 + 搜索 + 翻译）。

---

## 1. 核心概念：模型不执行函数

### 1.1 一个最常见的误解

```
❌ 误解：LLM 调用了我的函数
✅ 真相：LLM 只输出了"我想调用某个函数"的 JSON 指令，
        你的代码解析这个指令、执行函数、把结果还给 LLM
```

### 1.2 完整的调用循环

```
┌─────────────────────────────────────────────────────────┐
│               Function Calling 五步循环                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ① 用户提问 + 工具列表                                    │
│     "北京今天天气怎么样？"  +  [get_weather, get_time, ...]  │
│     ↓                                                   │
│  ② LLM 决策：需要天气数据 → 输出 tool_calls                 │
│     { "id": "call_abc", "function": {                   │
│         "name": "get_weather",                          │
│         "arguments": "{\"city\": \"北京\"}"              │
│     }}                                                  │
│     ↓                                                   │
│  ③ 你的代码解析 → 执行 → 拿到结果                          │
│     get_weather(city="北京") → "25°C，晴"                │
│     ↓                                                   │
│  ④ 把结果作为 tool message 还给 LLM                       │
│     { "role": "tool",                                   │
│       "tool_call_id": "call_abc",                       │
│       "content": "25°C，晴" }                            │
│     ↓                                                   │
│  ⑤ LLM 基于工具结果生成最终回复                            │
│     "北京今天 25°C，晴天，适合出行。"                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**类比：** LLM 是盲人指挥官，你的工具函数是他的眼睛和手——他只能发出指令，真正去看、去操作的是你的代码。

### 1.3 与 Structured Outputs 的关系

```
D03 Structured Outputs：       "请按照这个格式回答"
  → response_format=MyModel   → message.parsed
  → 用途：格式化回复内容

D04 Function Calling：         "你可以用这些工具来回答"
  → tools=[...]               → message.tool_calls
  → 用途：调用外部函数获取数据/执行操作

本质相同：底层都是 JSON Schema 约束
区别在于：一个约束"回复格式"，一个约束"调用指令格式"
```

---

## 2. OpenAI Function Calling 完整实现

### 2.1 定义工具

```python
"""
工具定义 —— 好坏定义对比
"""
# ✅ 好的工具定义：名称清晰、描述详细、参数有约束
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气。当用户询问天气、气温、是否下雨等问题时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，如'北京'、'上海'、'东京'",
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        "strict": True,  # 严格模式：参数一定符合 schema
    }
}

# ❌ 差的工具定义
BAD_TOOL = {
    "type": "function",
    "function": {
        "name": "weather",                    # 名称太简陋
        "description": "查天气",              # 没说明什么时候用
        "parameters": {
            "type": "object",
            "properties": {
                "q": {"type": "string"}       # 参数名不清晰
            }
        }
        # 没有 required、没有 strict
    }
}
```

### 2.2 工具定义速查表

| 字段 | 必须 | 说明 | 示例 |
|------|:---:|------|------|
| `type` | 是 | 固定为 `"function"` | `"function"` |
| `function.name` | 是 | 函数名，动词+名词 | `"get_weather"` |
| `function.description` | 是 | 何时用、做什么、返回什么 | `"获取指定城市实时天气..."` |
| `function.parameters` | 是 | JSON Schema | 见上面 |
| `function.strict` | 推荐 | 强制 schema 校验 | `True` |
| `function.parameters.properties.*.enum` | 推荐 | 约束可选值 | `["北京", "上海"]` |

### 2.3 第一次调用：让 LLM 决定调哪个工具

```python
from openai import OpenAI
import json

client = OpenAI()

# 工具集
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的实时天气信息。",
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取指定时区的当前时间。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "enum": ["Asia/Shanghai", "America/New_York", "Europe/London", "Asia/Tokyo"],
                        "description": "时区标识"
                    }
                },
                "required": ["timezone"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
]

# 用户问题
messages = [{"role": "user", "content": "北京现在几点了？天气怎么样？"}]

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
    # tool_choice="auto",  # 默认值：模型自行决定
)

# 检查返回
msg = response.choices[0].message
print(f"content: {msg.content}")       # 可能为 None（调用工具时不生成文本）
print(f"tool_calls: {msg.tool_calls}") # 工具调用列表

# 输出示例：
# content: None
# tool_calls: [
#   ChatCompletionMessageToolCall(
#     id='call_xxx1',
#     function=Function(name='get_time', arguments='{"timezone":"Asia/Shanghai"}')
#   ),
#   ChatCompletionMessageToolCall(
#     id='call_xxx2',
#     function=Function(name='get_weather', arguments='{"city":"北京"}')
#   )
# ]
```

### 2.4 执行工具 + 返回结果

```python
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# === 实际的工具函数（你的代码） ===
def get_weather(city: str) -> str:
    """模拟天气查询"""
    # 实际项目中这里调天气 API
    weather_data = {
        "北京": "5°C，多云，北风3级",
        "上海": "12°C，小雨",
        "东京": "8°C，晴",
    }
    return weather_data.get(city, f"未找到{city}的天气数据")

def get_time(timezone: str) -> str:
    """获取时区时间"""
    try:
        tz = ZoneInfo(timezone)
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return f"无法获取时区 {timezone} 的时间"

# === 工具执行映射 ===
TOOL_MAP = {
    "get_weather": get_weather,
    "get_time": get_time,
}

# === 执行循环 ===
messages = [{"role": "user", "content": "北京现在几点了？天气怎么样？"}]

# 第一轮：LLM 决策
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

# 把 LLM 的回复加入历史
assistant_message = response.choices[0].message
messages.append(assistant_message)

# 执行每个工具调用
for tool_call in assistant_message.tool_calls or []:
    func_name = tool_call.function.name
    func_args = json.loads(tool_call.function.arguments)

    print(f"[执行工具] {func_name}({func_args})")
    result = TOOL_MAP[func_name](**func_args)
    print(f"[工具结果] {result}")

    # 把工具结果作为 tool message 加入历史
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result,
    })

# 第二轮：LLM 基于工具结果生成最终回复
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,  # 仍然要传 tools，如果可能还需要继续调用
)

final_reply = response.choices[0].message.content
print(f"\n[最终回复] {final_reply}")
```

### 2.5 `tool_choice` 的四种模式

```python
# 1. auto（默认）—— 模型自己决定要不要调工具
tool_choice = "auto"

# 2. required —— 强制至少调一次工具
tool_choice = "required"
# 适用：明确需要工具的场景，如"帮我查..."

# 3. 强制指定工具 —— 不管用户说什么都用这个工具
tool_choice = {
    "type": "function",
    "function": {"name": "get_weather"}
}
# 适用：已知意图的 pipeline（如分类后的路由）

# 4. none —— 禁止调用工具，纯文本回复
tool_choice = "none"
# 适用：确定不需要工具的回复（如闲聊）
```

---

## 3. Anthropic (Claude) 的 Tool Use

### 3.1 关键差异

OpenAI 和 Anthropic 的核心理念一样，但格式不同：

```
            OpenAI                          Anthropic
            ──────                          ────────
工具参数     tools[].function.parameters      tools[].input_schema
调用格式     message.tool_calls[]             content block type="tool_use"
调用 ID      tool_call.id                    tool_use.id (需手动关联)
返回结果     role="tool" message              content block type="tool_result"
```

### 3.2 Claude 调用示例

```python
import anthropic

client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather",
        "description": "获取指定城市的实时天气信息。",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名"}
            },
            "required": ["city"],
        },
    }
]

# Claude 的 system prompt 是独立参数，不在 messages 里
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="你是一个天气助手。当用户问天气时，使用 get_weather 工具。",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools,
)

# Claude 的 tool_use 在 content 里，不在独立的 tool_calls 字段
for block in response.content:
    if block.type == "tool_use":
        print(f"工具调用: {block.name}({block.input})")
        print(f"ID: {block.id}")

        # 执行工具
        result = get_weather(block.input["city"])

        # 用 tool_result 返回结果
        tool_result = {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        }

        # 第二轮调用
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "北京天气怎么样？"},
                {"role": "assistant", "content": [block]},  # 上一轮的工具调用
                {"role": "user", "content": [tool_result]},  # 工具结果
            ],
            tools=tools,
        )
        print(f"\n最终回复: {response.content[0].text}")
```

### 3.3 格式差异总结

| 维度 | OpenAI | Anthropic |
|------|--------|-----------|
| Schema 字段 | `parameters` | `input_schema` |
| 调用结果位置 | `message.tool_calls` 数组 | `content` 数组中的 `tool_use` block |
| 结果返回角色 | `role: "tool"` 的 message | `role: "user"` 的 `tool_result` block |
| ID 关联 | `tool_call.id` | `tool_use.id` → `tool_use_id` |
| system prompt | messages[0] role="system" | 独立 `system` 参数 |
| `strict` | 显式 `strict: True` | 通过 prompt 约束 |

---

## 4. 实战：5 工具 Agent

### 4.1 完整实现

```python
"""
多工具 Agent —— Function Calling 的完整应用
支持：查天气、查时间、计算器、搜索、翻译
"""
from openai import OpenAI
import json
import math
from datetime import datetime
from zoneinfo import ZoneInfo

client = OpenAI()

# ============ 工具函数 ============
def get_weather(city: str) -> str:
    cities = {"北京": "5°C 多云", "上海": "12°C 小雨", "深圳": "22°C 晴"}
    return cities.get(city, f"未找到 {city} 的天气")

def get_time(timezone: str) -> str:
    tz = ZoneInfo(timezone)
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression: str) -> str:
    """安全计算：只允许数字和基本运算符"""
    import re
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%]+$', expression):
        return "表达式包含不允许的字符"
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"

def search_knowledge(query: str) -> str:
    """模拟知识库搜索"""
    kb = {
        "python": "Python 是解释型、面向对象的高级编程语言，由 Guido van Rossum 于 1991 年发布。",
        "redis": "Redis 是内存键值数据库，支持字符串、哈希、列表等数据结构。",
        "agent": "AI Agent 是能自主感知环境、做出决策、执行动作的智能体。",
    }
    for key, value in kb.items():
        if key in query.lower():
            return value
    return f"未找到关于 '{query}' 的信息"

def translate(text: str, target_lang: str) -> str:
    """模拟翻译（实际项目调翻译 API）"""
    mock = {
        ("你好", "english"): "Hello",
        ("谢谢", "english"): "Thank you",
        ("hello", "chinese"): "你好",
    }
    return mock.get((text.lower(), target_lang.lower()), f"[{target_lang}翻译] {text}")

# ============ 工具定义 ============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市实时天气",
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取指定时区当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "enum": ["Asia/Shanghai", "America/New_York", "Europe/London", "Asia/Tokyo"],
                        "description": "IANA 时区标识"
                    }
                },
                "required": ["timezone"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算，支持加减乘除和括号",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索内部知识库，当用户询问概念、技术问题时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"}
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate",
            "description": "翻译文本到目标语言",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要翻译的文本"},
                    "target_lang": {
                        "type": "string",
                        "enum": ["english", "chinese", "japanese", "french"],
                        "description": "目标语言"
                    }
                },
                "required": ["text", "target_lang"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
]

TOOL_MAP = {
    "get_weather": get_weather,
    "get_time": get_time,
    "calculate": calculate,
    "search_knowledge": search_knowledge,
    "translate": translate,
}

# ============ Agent 执行循环 ============
def run_agent(user_message: str, max_turns: int = 5):
    messages = [{"role": "user", "content": user_message}]
    turn = 0

    while turn < max_turns:
        turn += 1
        print(f"\n{'='*50}")
        print(f"第 {turn} 轮")
        print(f"{'='*50}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            temperature=0,
        )

        msg = response.choices[0].message
        messages.append(msg)

        # 如果模型想调用工具
        if msg.tool_calls:
            for tc in msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)
                print(f"🔧 调用 {func_name}({func_args})")

                result = TOOL_MAP[func_name](**func_args)
                print(f"📋 结果: {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            # 继续循环，让 LLM 决定下一步
            continue

        # 如果模型直接生成文本回复
        if msg.content:
            print(f"💬 回复: {msg.content}")
            return msg.content

        # 既没有 tool_calls 也没有 content（罕见情况）
        print("⚠️ 模型既没调工具也没回复文本")
        break

    return "达到最大轮次限制"

# ============ 测试 ============
if __name__ == "__main__":
    tests = [
        "北京现在几点了？天气怎么样？",         # 并行调用
        "计算 (123 + 456) * 7 等于多少？",      # 单工具
        "什么是 Python？请翻译成英文",           # 链式调用
        "深圳天气如何？帮我算一下 2 的 10 次方", # 并行 + 计算
    ]

    for t in tests:
        print(f"\n\n{'#'*60}")
        print(f"用户：{t}")
        print(f"{'#'*60}")
        run_agent(t)
```

### 4.2 输出示例

```
用户：北京现在几点了？天气怎么样？

第 1 轮
🔧 调用 get_time({"timezone": "Asia/Shanghai"})
📋 结果: 2026-06-18 14:30:00
🔧 调用 get_weather({"city": "北京"})
📋 结果: 5°C 多云

第 2 轮
💬 回复: 北京现在时间 14:30，天气 5°C，多云。
```

---

## 5. 工具设计最佳实践

### 5.1 黄金法则

```
① 名称 = 动词 + 名词
   get_weather ✅    weather ❌

② 描述 = 何时用 + 做什么 + 返回什么
   "当用户询问天气时，获取指定城市的实时天气信息。返回温度、天气状况。"
   而不是 "查天气"

③ 参数 = 类型 + 约束 + 说明
   "city": string, enum=[北京,上海], description="城市名"

④ 必填明确
   required: ["city"] — 不要遗漏

⑤ 数量克制
   每个请求暴露不超过 20 个工具
   功能重叠的工具合并
   动态工具集：只给当前场景需要的
```

### 5.2 常见反模式

```
❌ 工具功能重叠
   search_products / find_items / query_catalog → 合并为 search_catalog

❌ 参数不设约束
   "query": {"type": "string"} → 模型可能乱传
   改为 → "query": {"type": "string", "description": "搜索关键词，2-50字符"}

❌ 让模型填已知信息
   user_id 你已知 → 不要设为参数，后端直接注入
   只暴露用户需要选择的参数

❌ 工具太多
   一次给 50 个工具 → 模型选错概率高
   用命名空间分组 + 动态加载
```

---

## 6. 常见坑（踩过才懂）

### 坑 1：以为模型真的执行了函数

```
❌ 误区：LLM 调用了我的 get_weather() 函数
✅ 真相：LLM 只输出 {"name": "get_weather", "arguments": {...}}
        你的代码才是执行者，模型连你函数的代码都没见过
```

这是最常见的误解。Function Calling 这个名字有误导性——不是"模型调用函数"，而是"模型输出函数调用意图"。

### 坑 2：忘记把 assistant message 加入历史

```python
# ❌ 常见错误：只加了 tool result，没加 assistant message
response = client.chat.completions.create(messages=messages, tools=tools)
msg = response.choices[0].message

for tc in msg.tool_calls:
    result = execute(tc)
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

# 忘了这行 ↓
messages.append(msg)  # assistant message 必须保留！加在 tool 之前
```

**为什么要加？** 模型在第二轮看到完整历史时，需要知道"刚才谁调了工具、为什么调、调了什么参数"，否则上下文不完整，推理会出错。

### 坑 3：tool_call_id 不匹配

```python
# ❌ ID 随便写
messages.append({"role": "tool", "tool_call_id": "abc123", "content": result})

# ✅ 必须用返回的 id
messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
```

id 对不上 OpenAI 直接返回 400 错误。每个 tool_call 的 id 是唯一的，用来把结果和调用关联起来。

### 坑 4：arguments 是 JSON string，不是 dict

```python
# ❌ 直接当 dict 用
tc.function.arguments["city"]  # 报错！这是字符串不是 dict

# ✅ 先 json.loads
import json
args = json.loads(tc.function.arguments)
city = args["city"]
```

### 坑 5：没判断 tool_calls 是否存在

```python
# ❌ 直接取 tool_calls[0]，模型可能根本不调工具
msg = response.choices[0].message
tc = msg.tool_calls[0]  # tool_calls 可能是 None！

# ✅ 先判断再处理
if msg.tool_calls:
    for tc in msg.tool_calls:
        ...
elif msg.content:
    return msg.content  # 模型选择纯文本回复
```

两种情况也可能同时出现（模型边说边调工具），所以用 if/elif 而不是 if/else。

### 坑 6：第二轮调用忘记传 tools

```python
# ❌ 第二轮不传 tools
response2 = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
# 模型不知道还能继续调工具

# ✅ 仍然传 tools
response2 = client.chat.completions.create(
    model="gpt-4o-mini", messages=messages, tools=tools
)
```

模型可能需要在第二轮继续调工具（链式调用场景），不传 tools 相当于告诉它"你不能再调工具了"。

### 坑 7：并行调用的隐式依赖

```python
"""
用户："查小明的邮箱，然后给他发邮件"

模型并行返回：
  tool_calls = [
    lookup_contact("小明"),
    send_email(to="xiaoming@corp.com", ...)  # to 参数从哪来的？模型猜的！
  ]

问题：send_email 依赖 lookup_contact 的结果，但模型已经同时发出了
解决：工具设计时标注依赖关系；或者按顺序执行——先跑第一个，
     把结果注入后再让模型决定第二个
"""
```

### 坑 8：工具描述太模糊导致选错工具

```json
// ❌ 两个模糊工具放一起，模型随机选
{"name": "search", "description": "搜索东西"}
{"name": "find",   "description": "找到东西"}

// ✅ 描述清晰区分
{"name": "search_products", "description": "在商品库中按名称模糊搜索产品"}
{"name": "search_docs",     "description": "在帮助文档中全文搜索相关内容"}
```

### 坑 9：strict: true 但 schema 不完整

```python
# ❌ strict=True 要求 additionalProperties: False 和 required 显式声明
# 下面这个会报错
{
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"]
    # 缺少 "additionalProperties": False
}

# ✅ strict 模式的 schema 必须完整
{
    "type": "object",
    "properties": {"city": {"type": "string"}},
    "required": ["city"],
    "additionalProperties": False  # 必须加
}
```

### 坑 10：没有死循环保护

```python
# ❌ 没有最大轮次限制，模型可能反复调同一个工具
while True:
    response = llm(messages, tools)
    if response.tool_calls:
        ...  # 如果工具一直返回错误，模型可能反复重试同类调用

# ✅ 加最大轮次 + 重复调用检测
max_turns = 10
last_calls = None

for turn in range(max_turns):
    response = llm(messages, tools)
    msg = response.choices[0].message

    if not msg.tool_calls:
        return msg.content

    # 死循环检测：同一组调用出现了两次
    current_calls = tuple((tc.function.name, tc.function.arguments) for tc in msg.tool_calls)
    if current_calls == last_calls:
        print("[WARN] 模型重复调用了相同的工具，强制终止")
        break
    last_calls = current_calls

    ...  # 执行工具
```

### 坑 11：工具函数抛异常没被捕获

```python
# ❌ 工具抛出异常，整个 Agent 循环崩溃
result = tool_map[func_name](**func_args)  # 可能抛 KeyError、TypeError 等

# ✅ 每个工具调用都包 try/except
try:
    result = tool_map.get(func_name)
    if result is None:
        result = f"工具 '{func_name}' 不存在"
    else:
        result = result(**func_args)
except Exception as e:
    result = f"工具执行错误: {type(e).__name__}: {e}"
    # 把错误信息返回给模型，让模型决定怎么处理
    # 模型看到错误后可能会：
    #   - 用正确参数重试
    #   - 换一个工具
    #   - 告诉用户"抱歉，工具出错了"
```

---

## 7. 动手练习

```text
[ ] 练习 1：给上面的 Agent 添加第 6 个工具：
           - get_stock_price(symbol: str) → 模拟股票价格
           - 更新 TOOLS 和 TOOL_MAP
           - 测试："茅台和腾讯的股价分别是多少？"（应该并行调用）

[ ] 练习 2：实现 Anthropic 版本的天气查询
           - 用 Claude API + tool_use / tool_result
           - 对比两种 API 的代码差异

[ ] 练习 3：工具链式调用
           - 加一个 send_email(to, subject, body) 工具
           - 测试："查一下小明的邮箱，然后给他发一封会议邀请"
           - 观察需要几轮才能完成

[ ] 练习 4：错误处理
           - 让 get_weather 随机返回超时错误
           - 在 Agent 中加入重试逻辑
           - 测试 Agent 能否优雅降级

[ ] 练习 5：工具选择控制
           - 用 tool_choice="required" 强制模型必须调工具
           - 用 tool_choice={"type":"function","function":{"name":"xxx"}} 指定工具
           - 观察不同 tool_choice 下模型的行为差异
```

---

## 8. 关键收获

### 8.1 Function Calling 本质

```
LLM 就是一个 JSON 生成器：
  输入：用户问题 + 工具描述
  输出：{"name": "某工具", "arguments": {...}}

你的代码负责：
  1. 解析这个 JSON
  2. 执行真正的函数
  3. 把结果还给 LLM
  4. 循环直到任务完成
```

### 8.2 这就是 Agent 的雏形！

```
今天的代码：while 循环 + tools + LLM

while True:
    response = llm(messages, tools)
    if response.tool_calls:
        for tc in response.tool_calls:
            result = execute_tool(tc)
            messages.append(tool_result(tc.id, result))
        continue
    return response.content
                  ↑
            这就是 Agent 循环！
```

D06 和 D08-D09 会在这个循环上继续"装修"——加 ReAct 推理模式、加记忆、加循环控制。

### 8.3 D01-D04 知识链

```
D01: 调用 LLM API          → 能"说话"
D02: System Prompt 设计    → 能"扮演角色"
D03: Structured Outputs    → 能"可靠输出结构数据"
D04: Function Calling      → 能"调用外部工具"
                                ↑
                    四块积木齐了 = Agent 的基本能力
```

---

## 9. 参考

- [OpenAI Function Calling Guide](https://developers.openai.com/api/docs/guides/function-calling)
- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Function Calling 与 Tool Use 专题 - 面试题](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md)
- [Agent 核心概念与设计模式](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) — D08 预习
