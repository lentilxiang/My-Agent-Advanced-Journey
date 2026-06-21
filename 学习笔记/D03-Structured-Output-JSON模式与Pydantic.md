# D03：Structured Output —— JSON Schema + Pydantic 校验

> 目标：掌握三种结构化输出方式，理解为什么 Structured Outputs 是 Agent 的基建，完成数据提取与分类的实战代码。

---

## 1. 为什么 Agent 需要结构化输出？

### 1.1 Agent 的核心痛：不可靠的输出

```
传统 LLM 输出（自由文本）
  ↓
Agent 代码需要解析这些文本来决策
  ↓
"嗯，大概是这样吧..."、"推荐方案 A"、"答案是 42"
  ↓
正则匹配？if "推荐" in text？
  ↓
💥 脆弱、不可维护、一换模型就挂
```

**结构化输出解决的就是这个问题：让 LLM 的输出可以被代码可靠地消费。**

### 1.2 Agent 的决策链依赖结构化

```
                    ┌──────────────────┐
                    │   用户输入        │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  LLM 结构化输出    │  ← D03 今天的重点
                    │  { action: "search",│
                    │    query: "天气" }  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  代码安全解析      │  ← 不需要正则，直接 JSON
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  执行工具调用      │
                    └──────────────────┘
```

---

## 2. 三种结构化输出方式

### 2.1 方式一：Prompt 约束（最原始）

```python
# ❌ 不可靠：模型可能在 JSON 前后加废话
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{
        "role": "system",
        "content": "返回 JSON 格式，不要加其他内容。格式：{\"name\": \"...\", \"age\": ...}"
    }, {
        "role": "user",
        "content": "张三，28岁"
    }]
)
# 可能返回：好的，这是结果：\n{"name": "张三", "age": 28}\n希望有帮助！
# 你需要自己 strip + try/except json.loads
```

**问题：**
- 模型可能加前后废话
- JSON 可能包含注释或非法字符
- 可能漏字段、加字段、类型错误
- 每次都要手写解析+校验

### 2.2 方式二：JSON Mode（有进步但仍不够）

```python
# ⚠️ JSON Mode：保证是合法 JSON，但不保证字段结构
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{
        "role": "system",
        "content": "从文本中提取姓名和年龄。"
    }, {
        "role": "user",
        "content": "张三，28岁，工程师"
    }],
    response_format={"type": "json_object"}  # ← JSON Mode
)
# 保证了输出是合法 JSON
# 但不保证一定有 name 字段，也不保证 age 是 int
# 可能返回：{"full_name": "张三", "years": 28, "job": "工程师"}
```

**JSON Mode 的保证：** 输出是合法 JSON。
**JSON Mode 不保证的：** 字段名、字段类型、必填字段。

### 2.3 方式三：Structured Outputs（真正的类型安全）

```python
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class Person(BaseModel):
    name: str
    age: int

# ✅ Structured Outputs：字段名、类型、必填都保证
completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "从文本中提取姓名和年龄。"},
        {"role": "user", "content": "张三，28岁，工程师"}
    ],
    response_format=Person,  # ← 直接传 Pydantic 模型
)

# message.parsed 已经是 Pydantic 对象，类型安全！
person = completion.choices[0].message.parsed
print(person.name)  # "张三"  — IDE 有自动补全
print(person.age)   # 28       — 一定是 int
print(type(person)) # <class 'Person'>
```

**三种方式的对比：**

| 方式 | 保证合法 JSON | 保证字段结构 | 保证类型 | 代码量 |
|------|:---:|:---:|:---:|:---:|
| Prompt 约束 | 否 | 否 | 否 | 多（正则+校验） |
| JSON Mode | 是 | 否 | 否 | 中（json.loads+校验） |
| Structured Outputs | 是 | **是** | **是** | **少（Pydantic 自动）** |

---

## 3. Structured Outputs 核心机制

### 3.1 工作原理

```
你定义的 Pydantic Model           OpenAI SDK 做的事
─────────────────────              ─────────────────
class Person(BaseModel):           自动生成 JSON Schema →
    name: str                      { "type": "object",
    age: int                        "properties": {
                                    "name": {"type": "string"},
                                    "age": {"type": "integer"}
                                  },
                                  "required": ["name", "age"],
                                  "additionalProperties": false }
                                        ↓
                                  传给 API：response_format={
                                    "type": "json_schema",
                                    "json_schema": {
                                      "name": "Person",
                                      "strict": true,
                                      "schema": {...}
                                    }
                                  }
                                        ↓
                                  API 保证输出符合 schema
                                        ↓
                                  SDK 自动 Pydantic 校验
                                  → message.parsed = Person(name="张三", age=28)
```

### 3.2 `parse()` 方法 vs 手动写法

```python
# 推荐：用 parse() 方法，一行搞定
completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[...],
    response_format=Person,
)
person = completion.choices[0].message.parsed

# 等价的手动写法（不推荐，因为要自己处理 JSON）
completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                },
                "required": ["name", "age"],
                "additionalProperties": False,
            }
        }
    }
)
import json
person = Person(**json.loads(completion.choices[0].message.content))
```

### 3.3 Pydantic 支持的字段类型

```python
from pydantic import BaseModel
from typing import Optional, Literal, Union
from enum import Enum

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class Subtask(BaseModel):
    """支持嵌套"""
    title: str
    done: bool

class Task(BaseModel):
    title: str                              # 基础类型
    priority: int                           # 整数
    tags: list[str]                         # 列表
    status: TaskStatus                      # 枚举 → 自动约束可选值
    owner: Optional[str] = None             # 可选字段
    subtasks: list[Subtask] = []            # 嵌套模型列表
    deadline: Optional[str] = None          # 日期（用 str 接收）
```

**模型会自动生成这样的约束：**
- `title` — 必填 string，不能缺失
- `priority` — 必填 integer
- `tags` — 必填 array of strings
- `status` — 必填，只能是 "todo" / "in_progress" / "done"
- `owner` — 可选，可以是 null
- `subtasks` — 对象数组，每个对象有 title 和 done 字段

---

## 4. 实战案例

### 4.1 案例一：文本结构化提取

```python
"""
从非结构化文本中提取结构化信息
"""
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class CompanyInfo(BaseModel):
    name: str
    industry: str
    founded_year: int
    headquarters: str
    key_products: list[str]

text = """
小米科技有限责任公司成立于2010年3月，总部位于北京。
主要产品包括小米手机、小米电视、米家智能家居系列。
2021年宣布进军智能电动汽车领域。
"""

completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "从文本中提取公司信息。"},
        {"role": "user", "content": text},
    ],
    response_format=CompanyInfo,
)

info = completion.choices[0].message.parsed
print(f"公司：{info.name}")
print(f"行业：{info.industry}")
print(f"成立：{info.founded_year}年")
print(f"总部：{info.headquarters}")
print(f"产品：{', '.join(info.key_products)}")
```

### 4.2 案例二：Chain-of-Thought 数学推理

```python
"""
让模型展示推理步骤，同时输出结构化的最终答案
"""
from pydantic import BaseModel

class Step(BaseModel):
    explanation: str
    output: str

class MathSolution(BaseModel):
    steps: list[Step]
    final_answer: str

completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "逐步解数学题，每步给出解释和输出。"},
        {"role": "user", "content": "解方程：8x + 7 = -23"},
    ],
    response_format=MathSolution,
)

solution = completion.choices[0].message.parsed
for i, step in enumerate(solution.steps, 1):
    print(f"步骤 {i}：{step.explanation}")
    print(f"  → {step.output}")
print(f"\n最终答案：{solution.final_answer}")
```

**输出示例：**
```
步骤 1：两边同时减7，得到 8x = -30
  → 8x = -30
步骤 2：两边同时除以8，得到 x = -3.75
  → x = -3.75

最终答案：x = -3.75
```

### 4.3 案例三：智能分类器（Agent 中常用）

```python
"""
用户意图分类 — Agent 路由的基础
"""
from enum import Enum
from typing import Optional

class Intent(str, Enum):
    SEARCH = "search"         # 搜索知识库
    CALCULATE = "calculate"   # 数学计算
    CODE = "code"             # 写代码
    CHAT = "chat"             # 普通聊天

class UserIntent(BaseModel):
    intent: Intent
    confidence: float          # 0.0 ~ 1.0
    reason: str
    extracted_entities: Optional[list[str]] = None

def classify_intent(user_message: str) -> UserIntent:
    completion = client.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """
            分析用户消息的意图。
            - search: 需要查找信息、搜索资料
            - calculate: 数学计算
            - code: 编程相关
            - chat: 闲聊、打招呼
            """},
            {"role": "user", "content": user_message},
        ],
        response_format=UserIntent,
        temperature=0,  # 分类任务用 0
    )
    return completion.choices[0].message.parsed

# 测试
for msg in [
    "帮我查一下 Redis 怎么配置持久化",
    "123 * 456 等于多少",
    "用 Python 写一个快排",
    "你好啊今天天气不错",
]:
    intent = classify_intent(msg)
    print(f"「{msg}」")
    print(f"  → {intent.intent.value} (置信度: {intent.confidence})")
    print()
```

---

## 5. 拒绝检测 —— Structured Outputs 的重要能力

### 5.1 什么时候模型会拒绝？

模型可能因安全策略拒绝回答某些问题。用 Structured Outputs 时，拒绝是**可编程检测的**：

```python
completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "提取用户提到的产品名称。"},
        {"role": "user", "content": "请告诉我如何制作危险物品"},
    ],
    response_format=ProductList,
)

# Structured Outputs 的 refusals 检测
message = completion.choices[0].message
if message.refusal is not None:
    print(f"模型拒绝回答：{message.refusal}")
    # 在 Agent 中可以走 fallback 逻辑
elif message.parsed is not None:
    print(f"正常输出：{message.parsed}")
```

**三种状态（互斥）：**

```
message.parsed  → 非 None  = 正常返回 Pydantic 对象
message.refusal → 非 None  = 模型拒绝了请求
两者都为 None              = 不应该出现的情况（需要排查）
```

### 5.2 Agent 中的优雅处理

```python
def safe_parse(completion) -> Optional[BaseModel]:
    """Agent 中安全获取结构化输出"""
    message = completion.choices[0].message

    if message.refusal:
        # 日志记录拒绝原因，返回 None 让上层处理
        print(f"[REFUSAL] {message.refusal}")
        return None

    if message.parsed:
        return message.parsed

    # 理论上不会到这里
    print(f"[ERROR] 既无 parsed 也无 refusal：{message.content}")
    return None
```

---

## 6. Structured Outputs vs Function Calling

**D04 预告**——这是最容易被混淆的两个概念：

```
Structured Outputs（D03 今天学的）
  → 用于模型回答用户时，输出结构化的回复内容
  → response_format=YourPydanticModel
  → 典型场景：数据提取、分类、格式化的分析报告

Function Calling（D04 明天要学的）
  → 用于模型需要调用外部工具时，输出工具调用指令
  → tools=[{"type": "function", ...}]
  → 典型场景：搜索、查天气、执行代码、操作数据库
```

**两者的关系：**
```
Function Calling 本质上也是结构化输出——
模型输出的是 {name: "get_weather", arguments: {...}}
只是它的 Schema 是你定义的工具描述，而不是你的数据模型。

底层的约束机制是一样的：JSON Schema + strict mode
```

| | Structured Outputs | Function Calling |
|---|---|---|
| 用途 | 格式化回复内容 | 调用外部工具 |
| SDK 参数 | `response_format` | `tools` |
| 结果位置 | `message.parsed` | `message.tool_calls` |
| Schema 来源 | 你定义的 Pydantic 模型 | 工具定义的 parameters |
| 典型场景 | 提取、分类、格式化 | 搜索、计算、数据库 |

---

## 7. 动手练习

```text
[ ] 练习 1：定义一个 Pydantic 模型，从一段招聘文案中提取：
           - 职位名称、薪资范围、技能要求（list）、工作地点
           然后用 client.chat.completions.parse() 提取

[ ] 练习 2：做一个"日志分析器"
           输入：一段服务器错误日志
           输出：{error_type, severity(1-5), affected_service, suggested_fix}
           用 Pydantic + parse()

[ ] 练习 3：实现一个完整分类 pipeline
           - 先分类 intent（用 IntentClassifier）
           - 根据 intent 提取对应的 entities
           - 对于 unknown intent，走 fallback

[ ] 练习 4：对比 JSON Mode vs Structured Outputs
           用同一个任务分别调两次
           观察：字段名是否一致？类型是否正确？有没有多余字段？

[ ] 练习 5：处理 refusal 场景
           故意问一个边界问题，让模型拒绝
           实现：检测 refusal → 走 fallback 逻辑（返回默认分类）
```

---

## 8. 关键收获

### 8.1 选型决策

```
你要的输出是...              用什么...

有固定字段的数据              Structured Outputs (parse + Pydantic)
简单 JSON，字段不确定          JSON Mode
纯文本                      默认（不用 response_format）
模型要调用你的函数            Function Calling（明天学）
```

### 8.2 核心 API 速查

```python
# 定义 Schema
from pydantic import BaseModel
class MyOutput(BaseModel):
    field1: str
    field2: int
    field3: list[str]

# 调用
completion = client.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[...],
    response_format=MyOutput,
    temperature=0,  # 结构化输出推荐用 0
)

# 获取结果
result = completion.choices[0].message.parsed     # Pydantic 对象
refusal = completion.choices[0].message.refusal   # None 或 拒绝原因

# 检查
if result is not None:
    print(result.field1)  # IDE 有自动补全，类型安全
```

### 8.3 D02 → D03 知识递进

```
D02：写好 System Prompt  → 让模型扮演正确角色
D03：定义 Structured Output → 让模型输出正确格式

两者结合：
  System Prompt 控制"说话风格"（软约束）
  Structured Outputs 控制"数据格式"（硬约束）
  → 实现了对 LLM 的完全可控
```

---

## 参考

- [OpenAI Structured Outputs Guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Agent 核心概念](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) — 理解结构化输出在 Agent 中的位置
- [Function Calling 专题](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md) — D04 预习
