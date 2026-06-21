# D02：System Prompt 设计与参数调优

> 目标：掌握 System Prompt 的设计技巧，理解 Temperature/Top-p 的实际效果，完成一个角色扮演 Demo。

---

## 1. System Prompt 设计精要

D01 讲了三种消息角色**是什么**——今天聚焦**怎么写好 System Prompt**。

### 1.1 角色设定的四个要素

一个好的 System Prompt 包含四个要素：

```
┌─────────────────────────────────────────────────────────┐
│                   System Prompt 四要素                    │
├──────────────┬──────────────────────────────────────────┤
│ ① 角色定位    │ "你是鲁迅，用白话文风格对话"              │
│ ② 行为约束    │ "回答控制在200字以内"                    │
│ ③ 输出格式    │ "用纯文本，不要用 markdown"               │
│ ④ 边界规则    │ "不知道就说不知道，不要编造"              │
└──────────────┴──────────────────────────────────────────┘
```

### 1.2 好 Prompt vs 坏 Prompt

用 Anthropic 官方建议的核心原则——**像给新员工布置任务一样写 prompt**：

**坏 Prompt（模糊、缺约束）：**

```text
你是一个助手，帮我回答问题。
```

**好 Prompt（清晰、有边界）：**

```text
你是鲁迅（1881-1936），中国现代文学奠基人。
- 用白话文风格对话，偶尔夹杂文言词汇
- 回答控制在 150 字以内
- 当涉及你死后发生的事情时，回答"这我不清楚了"
- 保持批判性思维，但不要过于尖刻
```

**对比效果：**

| 问题 | 坏 Prompt 的回答 | 好 Prompt 的回答 |
|------|-----------------|-----------------|
| "怎么看AI写文章" | "AI写文章是很好的工具..."（通用回答） | "机器作文章？这倒是新鲜事。不过文章贵在有魂，机器的魂在哪里？" |

### 1.3 XML 标签结构化 Prompt

从 Anthropic 最佳实践中提取的核心技巧——用 XML 标签分隔不同类型的指令：

```python
system_prompt = """
<role>
你是资深 Python 技术面试官，在字节跳动工作了 5 年。
</role>

<behavior>
- 每次只问一个问题，根据回答决定下一问
- 回答正确就追问更深一层，回答错误就给提示
- 不要一次问太多，像真实面试一样循序渐进
</behavior>

<format>
- 用口语化中文
- 代码用 ```python 代码块
- 评价放在 <evaluation> 标签内
</format>

<boundaries>
- 不知道答案时诚实说"这个我不确定"
- 不要给出危险代码（rm -rf、eval 等）
</boundaries>
"""

# 调用
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "我准备好了，开始面试吧"}
    ],
    temperature=0.7
)
print(response.choices[0].message.content)
```

**XML 标签的核心价值：** 帮助模型清晰区分"角色定义"和"格式要求"，减少模型把格式指令混入角色行为的概率。

### 1.4 添加示例（Few-shot）

Anthropic 强调：**示例是最可靠的输出控制手段之一**。给模型 3-5 个示例，它能准确复现你想要的格式和风格。

```python
system_prompt = """
你是鲁迅。用白话文风格对话。

<examples>
用户：你好，鲁迅先生。
鲁迅：你好。这世道，能说上话的人不多了。

用户：您怎么看待年轻人躺平？
鲁迅：躺平？地上凉，躺久了要生病的。年轻人还是该起来走走，看看外面的世界。不过话又说回来，若这地上连站的地方都没有了，那也不是年轻人的错。
</examples>

请用上述风格回答用户。
"""
```

**示例设计三原则（来自 Anthropic）：**
1. **相关** — 示例要和实际场景贴近
2. **多样** — 覆盖边界情况，避免模型学到不该学的模式
3. **结构化** — 用 `<examples>` / `<example>` 标签包裹

### 1.5 比"角色扮演"更进一步：角色 + 任务 + 工具

```
纯角色扮演：  "你是鲁迅"
角色 + 任务：  "你是鲁迅，帮我改这篇文章"
角色 + 任务 + 工具："你是鲁迅，用 search 工具查资料后，帮我改文章"
                                    ↑
                              这就是 Agent
```

---

## 2. Temperature 实战实验

D01 讲了 Temperature 的理论（0=确定，0.7=自然，2.0=混乱），今天做**同 prompt 不同 temperature 的对比实验**。

### 2.1 实验：同一 prompt，5 个 temperature

```python
"""
Temperature 对比实验：
同一个 prompt，观察不同 temperature 下输出的变化
"""
from openai import OpenAI

client = OpenAI()

system_prompt = "你是一个创意写手。给一个故事的三种不同开头，每种30字以内。"
user_prompt = "主题：雨夜，一个陌生人敲响了门"

temperatures = [0, 0.3, 0.7, 1.0, 1.5]

for t in temperatures:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=t,
        seed=42  # 固定随机种子，让结果可复现
    )
    print(f"\n{'='*50}")
    print(f"Temperature = {t}")
    print(f"{'='*50}")
    print(response.choices[0].message.content)
```

**典型输出对比：**

| Temp | 第一个开头 | 观察 |
|:----:|-----------|------|
| 0 | "雨声淅沥，门铃突然响起，门外站着一个浑身湿透的女人。" | 保守、安全、每次都一样 |
| 0.3 | "那夜的雨格外大，敲门声混在雷声里，几乎听不真切。" | 稍有变化，仍然稳健 |
| 0.7 | "闪电劈开夜幕的瞬间，他看见门外影子手里握着一把旧伞。" | 有画面感、有悬念 |
| 1.0 | "门缝下渗进来的不只有雨水，还有一缕暗红色的液体。" | 大胆、悬疑感强 |
| 1.5 | "他想不起自己何时装了门铃，但这声音确实是从自家门上传来的。" | 超现实、可能跑偏 |

### 2.2 Temperature 的本质：logits 缩放

Temperature 不是开关，是概率分布的"缩放旋钮"：

```
原始 logits → softmax → 概率分布

temperature 的作用：在 softmax 之前，把所有 logits 除以 T

T = 0.1：差异被放大 10 倍
  logits [2.0, 1.0, 0.5]
  → 除以0.1 [20.0, 10.0, 5.0]
  → softmax → [0.999, 0.001, ~0]
  → 几乎总是选第一个 token

T = 1.0：原始分布
  → softmax → [0.58, 0.24, 0.18]
  → 按概率采样

T = 2.0：差异被压缩
  → 除以2.0 [1.0, 0.5, 0.25]
  → softmax → [0.44, 0.33, 0.23]
  → 三个 token 概率差不多，接近随机
```

### 2.3 Top-p 深入理解

Temperature 控制的是**概率分布的形状**，Top-p 控制的是**候选范围**：

```
top_p = 0.1（极窄）
  只从概率最高的 token 中选，加到累计 10%
  用于：极度保守、确定性最强的场景
  ⚠️ 注意：0.1 太极端，可能只选 1-2 个 token，输出会重复

top_p = 0.9（推荐）
  从累加到 90% 的 token 中选
  有选择但过滤掉低概率的"垃圾"token

top_p = 1.0（全部）
  不限制，和只用 temperature 效果一样
```

**Temperature 和 Top-p 的配合逻辑：**

```
第一步：Temperature 缩放概率分布（压扁或拉尖）
第二步：Top-p 裁掉低概率尾巴
第三步：从剩余 token 中采样

推荐组合：
  精确任务 → temperature=0（此时 top_p 无效，因为只选最高的）
  创意任务 → temperature=0.7~0.9 + top_p=0.9~0.95
```

### 2.4 什么时候调哪个参数？

```
你要的是：
  稳定、可复现 → 只调 temperature，降到 0
  多样但不离谱 → temperature=0.7, top_p 默认
  多样但有质量底线 → 提高 temperature 到 1.0，设 top_p=0.9
  极致创意 → temperature=1.2+, top_p=0.95+

经验法则：
  先调 temperature，效果不够再加 top_p
  不要两个都调到极端值
```

---

## 3. 角色扮演 Demo 完整实现

### 3.1 Demo 1：鲁迅风格对话

```python
"""
角色扮演 Demo：鲁迅风格对话
运行后会进入交互式对话模式
"""
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
<role>
你是鲁迅（周树人），中国现代文学奠基人。你的语言风格：
- 以白话文为主，偶尔使用文言词汇如"大抵""罢了""之乎者也"
- 语气冷静克制但暗藏批判
- 善用反讽和隐喻
- 回答简短，通常不超过 100 字
</role>

<behavior>
- 当涉及 1936 年之后的事件时，说"这我无从知晓了"
- 保持知识分子的尊严，不接受无聊的闲聊
- 如果有人请你写代码，你会说"我只会写文章，代码不是我的本行"
</behavior>

<examples>
用户：鲁迅先生好。
鲁迅：你也好。有什么事就直说吧，不必客气。

用户：怎么看现在的社会？
鲁迅：横眉冷对千夫指，俯首甘为孺子牛。这句话放到今天，也不过时。
</examples>
"""

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
]

print("=== 鲁迅风格对话 ===")
print("输入 'quit' 退出\n")

while True:
    user_input = input("你：")
    if user_input.lower() == "quit":
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,  # 稍高，让风格更自然
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    print(f"鲁迅：{reply}\n")
```

### 3.2 Demo 2：技术面试官（带评分）

```python
"""
角色扮演 Demo：Python 技术面试官
每轮面试后给出评分
"""
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
<role>
你是阿里 Python 后端面试官，面试经验 8 年。
面试难度：P6（高级工程师）
</role>

<interview_rules>
1. 每次只问一个问题，难度逐步递增
2. 候选人答对了，追问更深一层
3. 候选人答错了，给出提示，允许再答一次
4. 面试 5 个问题后给出综合评分
5. 问题涵盖：Python 基础 → 并发编程 → 系统设计 → 数据库 → 项目经验
</interview_rules>

<evaluation_format>
每轮回答后用 <evaluation> 标签给出评价：
<evaluation>
正确性：X/10
深度：X/10
建议：[一句话建议]
</evaluation>
</evaluation_format>
"""

messages = [{"role": "system", "content": SYSTEM_PROMPT}]

print("=== 阿里 Python 面试模拟 ===")
print("输入 'quit' 退出\n")

question_count = 0

# 面试官先问第一个问题
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages + [
        {"role": "user", "content": "面试可以开始了，请出第一题。"}
    ],
    temperature=0,
)
first_q = response.choices[0].message.content
print(f"面试官：{first_q}\n")
messages.append({"role": "assistant", "content": first_q})
question_count = 1

while question_count <= 5:
    user_input = input("你：")
    if user_input.lower() == "quit":
        break

    messages.append({"role": "user", "content": user_input})

    # temperature=0 保证评分客观一致
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0,
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    print(f"面试官：{reply}\n")
    question_count += 1
```

### 3.3 Demo 3：多角色切换

```python
"""
角色切换：一个对话，三种角色
演示 System Prompt 动态切换
"""
from openai import OpenAI

client = OpenAI()

ROLES = {
    "鲁迅": """
你是鲁迅。用白话文，偶尔夹杂文言。回答简短（100字内），
保持批判性。涉及1936年后的事说"这我无从知晓"。
""",
    "李白": """
你是唐代诗人李白。洒脱豪放，好饮酒作诗。
回答时可以用诗句表达，不拘小节。
涉及唐代之后的事说"这我不知何物"。
""",
    "福尔摩斯": """
你是夏洛克·福尔摩斯。观察力超凡，逻辑严密。
说话简洁，先指出对方言辞中的细节，再推理。
回答用"我观察到..."开头。
""",
}


def chat_with_role(role_name: str, user_input: str) -> str:
    """用指定角色对话"""
    system_prompt = ROLES.get(role_name, "你是普通助手。")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0.8,  # 角色扮演需要自然感
    )
    return response.choices[0].message.content


# 同一句话，问三个角色
question = "你怎么看 ChatGPT？"

print("=== 同一问题，不同角色 ===\n")
for name in ROLES:
    reply = chat_with_role(name, question)
    print(f"【{name}】\n{reply}\n{'-'*40}\n")
```

**预期输出差异：**
- 鲁迅：批判 AI 的"灵魂"问题
- 李白：把 ChatGPT 比作某种仙术
- 福尔摩斯：分析提问者的用词细节

---

## 4. 动手练习

```text
[ ] 练习 1：写一个"毒舌书评人"的 System Prompt，让 AI 用刻薄幽默的风格评价书籍
           要求：包含角色、行为、格式、边界四个要素

[ ] 练习 2：用相同的 prompt，跑 temperature = 0 / 0.5 / 1.0 / 1.5，对比输出
           观察：哪个 temperature 最适合你的书评人？

[ ] 练习 3：给一个 System Prompt 加上 <examples> 标签，放 3 个对话示例
           对比：加示例前后，回答风格有没有更贴近你的预期？

[ ] 练习 4：选一个你喜欢的角色（历史人物/虚构角色），写完整 System Prompt
           要求：让人看不出是 AI 在扮演

[ ] 练习 5：试试 temperature=0 和 temperature=0.9 分别跑面试官 demo
           观察：temperature 对评分一致性有什么影响？
```

---

## 5. 关键收获

### 5.1 System Prompt 设计法则

| 原则 | 说明 | 来源 |
|------|------|------|
| **像给新人布置任务** | 清晰、具体、有边界 | Anthropic |
| **四要素齐全** | 角色 + 行为 + 格式 + 边界 | 实战总结 |
| **XML 标签分隔** | `<role>` `<behavior>` `<format>` | Anthropic 推荐 |
| **加 3-5 个示例** | Few-shot 最可靠 | Anthropic 推荐 |
| **放前面** | System Prompt 放在 messages 最前面 | API 设计 |

### 5.2 Temperature 选择口诀

```
能确定下来的任务 → temperature = 0
  代码、分类、数据提取、数学

需要一点点变化的 → temperature = 0.3~0.5
  正式文案、商务邮件

自然对话 → temperature = 0.7~0.9
  聊天、角色扮演、客服

创意脑暴 → temperature = 1.0~1.2
  写小说、头脑风暴、点子发散
```

### 5.3 D01 → D02 知识递进

```
D01：消息角色是什么 → D02：怎么写好 System Prompt
D01：Temperature 概念 → D02：Temperature 实验 + Top-p 配合
D01：调用 API 跑通   → D02：用 API 做出可控的角色扮演
```

---

## 参考

- [Anthropic Prompt Engineering Best Practices](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Anthropic Prompt Engineering Overview](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-engineering/overview)
- [OpenAI Text Generation Guide](https://platform.openai.com/docs/guides/text-generation)
