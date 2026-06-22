# D08：ReAct 循环原理

> 目标：理解 ReAct 的 Thought→Action→Observation 循环，知道它解决了什么问题，能画出完整流程图。

---

## 1. 问题：纯 LLM 为什么不够？

### 1.1 一个需要多步推理的问题

```
用户："马斯克和贝佐斯谁更早创立了自己的第一家公司？两人相差多少岁？"

这个任务需要：
  步骤1：查马斯克第一家公司创立时间 → 需要搜索
  步骤2：查贝佐斯第一家公司创立时间 → 需要搜索
  步骤3：查两人出生日期 → 需要搜索
  步骤4：计算时间差 → 需要数学
  步骤5：综合回答
```

### 1.2 三种做法对比

```
做法 A：纯 LLM（无工具）
  LLM 凭记忆直接回答
  → 可能记得大概但数字不准确
  → 可能产生幻觉（马斯克第一家公司是 X.com？Zip2？记不清）

做法 B：单次 LLM + 单次工具调用（第1周的 D04 模式）
  问 → LLM 调 search("马斯克") → 返回结果 → LLM 回答
  → 信息不够，需要多步搜索
  → 一次调用只能解决一部分

做法 C：ReAct（推理 + 行动循环）
  问 → Thought: 先查马斯克 → Action: search("马斯克第一家公司")
     → Observation: "Zip2, 1996年" → Thought: 再查贝佐斯
     → Action: search("贝佐斯第一家公司") → Observation: "Amazon, 1994年"
     → Thought: 还差年龄 → Action: search("马斯克出生日期")
     → ... → Thought: 信息够了 → Action: Finish
  → 每一步都基于上一步的发现，动态调整策略
```

**核心差异：** 纯 LLM 是"一次思考"，ReAct 是"边想边做、边做边想"。

### 1.3 CoT（Chain-of-Thought）详解 —— 理解了 CoT，才能理解 ReAct 为什么多了一步

**CoT 是什么？**

```
CoT = Chain-of-Thought = 思维链

一句话：让 LLM 把推理过程"一步步写出来"，而不是直接给答案。

没有 CoT：       有 CoT：
  用户："1+2+3=?"   用户："1+2+3=?"
  LLM："6"          LLM："1+2=3，3+3=6，答案是 6。"
                   ↑ 中间推理步骤被显式写出来了
```

**为什么 CoT 能提升准确率？**

```
问题："一个房间里有 3 个人，每个人有 2 个苹果，每人吃掉 1 个后，
       又买来 4 个苹果，现在共有几个苹果？"

无 CoT（直接回答）：
  LLM："7个"  ← 可能算错，也没有推算过程可检查

有 CoT（逐步推理）：
  LLM："一开始：3人 × 2个 = 6个苹果
        吃掉：3人 × 1个 = 3个苹果，剩余 6-3=3个
        又买：3+4=7个苹果
        答案是 7 个。"
  → 每一步推理可见，错了能定位
```

**CoT 的核心价值：把隐式推理变成显式推理**

```
LLM 的推理本质上是"前向传播一次，输出下一个 token"。
不写 CoT 时，所有中间推理都在模型内部完成，对外黑盒。
写了 CoT 时，模型把中间步骤作为 token 逐个生成出来，
每个 token 都能"看到"前面已写出的推理步骤 →
后面的推理建立在前面已写出的结论之上，形成递进的逻辑链。

这就像考试做数学题：
  不写过程 = 心算 → 容易错，错了也不知道哪步错了
  写过程 = 每步写下来 → 逻辑更清晰，容易检查
```

**CoT 的三种形式：**

```
① Zero-shot CoT（零样本，最常用）
  只加一句魔法提示词：
  "Let's think step by step." / "让我们一步步思考。"
  → 无需示例，通用性强

② Few-shot CoT（少样本）
  在 prompt 里给 2-3 个示例，展示"问题→逐步推理→答案"的格式
  → 模型模仿示例的推理风格

③ Auto-CoT（自动生成）
  让 LLM 自动生成推理示例，再聚类选代表，喂给最终 prompt
  → 减少人工写示例的工作量
```

**CoT 进化的分支（和 ReAct 对比的关键背景）：**

```
CoT（基础版）
  Thought₁ → Thought₂ → Thought₃ → Answer
  纯推理链，不动手，只动脑

Tree-of-Thought（ToT，思维树）
         ┌─ Thought A ─ Thought A₁ ─ ...
  Start ─┼─ Thought B ─ Thought B₁ ─ ...
         └─ Thought C ─ ...
  多条推理路径同时探索，每条评估打分，选最优路径
  相当于"头脑风暴"——同时想几个方案，挑最好的

Graph-of-Thought（GoT，思维图）
  推理节点可以分叉、合并、回溯
  比树更灵活——不同路径的中间结论可以互相借鉴

ReAct（推理 + 行动）
  Thought₁ → Action₁ → Observation₁ → Thought₂ → Action₂ → ...
  纯推理 CoT 的问题：每一步都是模型"猜"的，没有外部验证
  ReAct 的改进：每步推理后可以调工具获取真实数据，作为下一步推理的锚点
```

**CoT vs ReAct 一句话总结：**

```
CoT = 把推理写出来，但所有信息靠模型自己的知识（可能幻觉）
ReAct = 把推理写出来，且每步可以用工具拿到真实信息（Observation 锚定事实）

CoT 是"闭卷考试，但要求写计算过程"
ReAct 是"开卷考试，可以查资料，也要写计算过程"

两者不是互斥的：
  ReAct 的 Thought 步骤本质上就是 CoT
  可以把 ReAct 理解为 "CoT + 工具调用的能力"
```

---

## 2. ReAct 三要素

### 2.1 Thought（思考）

```
Thought 是什么？
  不是代码注释，是模型"自言自语"的推理过程
  
  形式：一段自然语言文本
  作用：分析当前状态、规划下一步、判断是否完成
  
  示例：
    "我需要先找到马斯克的第一家公司成立年份。应该搜索'马斯克 第一家公司 Zip2 成立'。"
    
    "搜索结果说是 1996 年。我还需要贝佐斯的数据才能比较。"
    
    "两人数据都有了。马斯克 1996 年，贝佐斯 1994 年。贝佐斯更早。"
    "现在需要算年龄差。我已知道两人出生年份..."
    
    "所有信息齐了，可以给出最终答案。"
```

### 2.2 Action（行动）

```
Action 是什么？
  模型决定要做的事——调用哪个工具、传什么参数

  形式（OpenAI FC）：{"name": "search", "arguments": {"query": "马斯克 Zip2 成立"}}
  形式（文本协议）：Action: search\nAction Input: 马斯克最早的公司 Zip2 成立

  和第1周 Function Calling 的关系：
    Function Calling 是 Action 的实现方式
    D04 的 tool_calls 就是 ReAct 的 Action 步骤
    只是 D04 没显式要求模型输出 Thought
```

### 2.3 Observation（观察）

```
Observation 是什么？
  工具执行后的返回结果——Agent "看到的"环境反馈

  形式：工具返回的字符串
  作用：更新 Agent 对世界的认知，影响下一步决策

  示例：
    Observation: "搜索结果：Zip2 由伊隆·马斯克与金巴尔·马斯克于 1996 年 2 月创立"
    
    Agent 的认知更新：
    "马斯克第一家公司 = Zip2 = 1996年 ✓"
    "还差贝佐斯的数据 → 下一个 Action: search('贝佐斯第一家公司')"
```

---

## 3. 完整流程图

### 3.1 宏观循环

```
                                    开始
                                     │
                                     ▼
                          ┌─────────────────────┐
                          │  System Prompt +     │
                          │  工具列表 + 用户问题  │
                          └──────────┬──────────┘
                                     │
                                     ▼
┌───────────────────────────────────────────────────────────────┐
│                        ReAct 循环                               │
│                                                               │
│         ┌──────────────────────────────────────┐              │
│         │         ① Thought（思考）              │              │
│         │    "当前情况是 X，下一步该做 Y"          │              │
│         │    这步是 ReAct 的核心——显式推理         │              │
│         └──────────────┬───────────────────────┘              │
│                        │                                      │
│                        ▼                                      │
│         ┌──────────────────────────────────────┐              │
│         │         ② Action（行动）              │              │
│         │    调用工具：search("...")            │              │
│         │    或 FINISH：生成最终答案            │              │
│         └──────────────┬───────────────────────┘              │
│                        │                                      │
│              ┌─────────┴──────────┐                           │
│              │                    │                           │
│         调工具                FINISH                           │
│              │                    │                           │
│              ▼                    ▼                           │
│  ┌────────────────────┐    ┌──────────┐                      │
│  │ ③ Observation      │    │ 返回用户  │                      │
│  │ "执行结果: ..."     │    └──────────┘                      │
│  └────────┬───────────┘                                       │
│           │                                                   │
│           ▼                                                   │
│     将 Observation 加入上下文                                   │
│           │                                                   │
│           └──────────────────→ 回到 ① Thought                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 具体示例走一遍

```
轮次 1:
  ┌─────────────────────────────────┐
  │ Thought: 需要查马斯克第一家公司   │
  │ Action: search("马斯克 Zip2 成立") │
  │ Observation: "Zip2, 1996年2月"   │
  └─────────────────────────────────┘

轮次 2:
  ┌─────────────────────────────────┐
  │ Thought: 拿到马斯克的了，还差贝佐斯 │
  │ Action: search("贝佐斯 Amazon 创立")│
  │ Observation: "Amazon, 1994年7月" │
  └─────────────────────────────────┘

轮次 3:
  ┌─────────────────────────────────┐
  │ Thought: 创业时间贝佐斯更早。     │
  │   现在需要两人出生日期算年龄差     │
  │ Action: search("马斯克出生日期")  │
  │ Observation: "1971年6月28日"     │
  └─────────────────────────────────┘

轮次 4:
  ┌─────────────────────────────────┐
  │ Thought: 查贝佐斯出生日期         │
  │ Action: search("贝佐斯出生日期")  │
  │ Observation: "1964年1月12日"     │
  └─────────────────────────────────┘

轮次 5:
  ┌─────────────────────────────────┐
  │ Thought: 数据齐了。              │
  │   贝佐斯 1994 年早于马斯克 1996， │
  │   贝佐斯年长马斯克 7 岁。         │
  │   Action: FINISH                │
  │   最终回答给用户                  │
  └─────────────────────────────────┘
```

---

## 4. ReAct 和 D06 Agent 的关系

### 4.1 D06 的 Agent 其实已经是"隐式 ReAct"

```python
# D06 的循环
for turn in range(max_turns):
    response = llm(messages, tools)  # ← LLM 内部做了 Thought + Action
    if not msg.tool_calls:
        return msg.content           # ← FINISH
    for tc in msg.tool_calls:
        result = execute(tc)         # ← Observation
        messages.append(tool_msg)

# 区别：D06 没有显式的 Thought
# LLM 在 tool_calls 产生之前内部"想了一下"
# 但那个"想"对外不可见
```

### 4.2 显式 ReAct vs 隐式 ReAct —— "调用哪个工具"是怎么来的？

**关键问题：模型怎么决定调哪个工具、传什么参数？**

两种方式的核心区别在于**模型"说出"工具调用的形式**不同。

```
方式 A：隐式 ReAct（Function Calling 原生）

  模型是怎么做到的？
    → 模型在训练阶段学习了 Function Calling 能力
    → 前向传播时，模型内部计算后，直接输出结构化的 tool_calls token
    → API 返回的不是纯文本，而是带 tool_calls 字段的结构化响应：
        {
          "role": "assistant",
          "tool_calls": [{
            "id": "call_xxx",
            "function": {"name": "search", "arguments": "{\"query\":\"马斯克 Zip2\"}"}
          }]
        }
    → 开发者代码读取 response.choices[0].message.tool_calls
    → 根据 name 找到对应函数，json.loads(arguments) 拿到参数
    → 执行函数，把结果返回给模型

  一句话：模型训练过"输出 tool_calls"，API 直接给你结构化的工具名+参数。


方式 B：显式 ReAct（文本协议，传统论文风格）

  模型是怎么做到的？
    → 模型没有被训练过 Function Calling
    → 靠 prompt 工程教模型按特定格式输出文本：
        "When you need a tool, output:
         Thought: <your reasoning>
         Action: <tool_name>
         Action Input: <parameters>"
    → 模型输出纯文本：
        Thought: 需要查马斯克第一家公司
        Action: search
        Action Input: 马斯克 Zip2 成立
    → 开发者代码用正则/解析器从文本中提取 Action 和 Action Input
    → 找到对应函数，传入参数，执行
    → 把结果拼成 Observation 文本，追加到 messages 里

  一句话：模型没训练过 FC，靠 prompt 教它"按格式写出来"，开发者自己解析文本。
```

```
对比总结：

  核心区别不在"传不传 tools 描述"——两种方式都会把工具信息传给模型。
  区别在于模型被训练时，有没有学过"识别 tools 定义并输出 tool_calls"这个能力。

  什么叫"训练时学过 Function Calling"？
    OpenAI/Anthropic 在模型微调阶段，喂了大量这样的训练样本：
      输入：system prompt 含 tools 定义 + 用户问"北京天气"
      期望输出：assistant 返回 tool_calls: [{name:"get_weather", arguments:{"city":"北京"}}]
    模型学到的不是"执行函数"，而是输出格式：
    "当我看到 tools 定义，且用户问题需要调用工具时，
     我应该输出一个 tool_calls 字段，里面放工具名+JSON参数。"
    这个能力写在了模型权重里。

  什么叫"没学过 Function Calling"？
    模型的训练数据里从来没有出现过 tool_calls 这种输出格式。
    你把 tools 定义写在 prompt 里，模型只会当普通文字来读，
    它不会输出 tool_calls，只会输出普通文本。
    你只能教它按 "Action: xxx" 的文本格式写出来，然后自己解析。

               隐式 ReAct (FC)                    显式 ReAct (文本协议)
  ──────────  ──────────────────────────────    ─────────────────────────
  传 tools 给   通过 API 的 tools 参数传入         写在 prompt 正文里当自然语言
  模型的方式   (模型识别这是工具定义)                (模型当普通指令读)

  模型输出     tool_calls 结构化字段              纯文本 "Action: xxx"
              (模型权重里有这个输出能力)             (模型只会输出文本)

  怎么拿到     开发者读 response.tool_calls        开发者手写正则解析文本
  工具名+参数  API 已解析好 name + arguments       自己提取 Action + Action Input

  推理可见性   不可见                              完全可见
              (模型内部计算后直接出 tool_calls)     (Thought 以明文输出)

  优点        简单，原生 API 支持                  可解释、可调试、兼容所有模型
  缺点        只有特定模型支持                     格式不稳定，解析易出错
```

**追问：格式不稳定、解析易出错——能不能让模型输出结构化 JSON 来解决？**

```
完全可以。这恰好在"纯文本解析"和"原生 FC"之间，有三个阶梯：

  Level 1：纯文本解析（最原始）
    模型输出: "Action: search\nAction Input: 马斯克 Zip2"
    → 正则提取，容易因为模型多写个空格/换行就解析失败

  Level 2：JSON Mode / Structured Output（中间方案）
    要求模型输出: {"thought": "...", "action": "search", "action_input": "..."}
    → json.loads() 解析，比正则可靠得多
    → 模型不需要 FC 训练，只需要支持 JSON 输出
    → D03 学的 Structured Output 就在这里用上了

  Level 3：原生 Function Calling（最优方案）
    API 返回的 tool_calls 已经是解析好的 name + arguments
    → 不需要任何解析代码，直接读字段
    → 最稳定，但需要模型支持 FC 训练

所以实际工程中：
  支持 FC → 用 Level 3（隐式 ReAct）
  不支持 FC 但支持 JSON → 用 Level 2（半结构化显式 ReAct）
  都不支持 → 用 Level 1（纯文本解析，兜底）
```

```
一张图总结两种实现的关系：

  ┌──────────────────────────────────────────────────┐
  │              ReAct 模式（设计模式层）               │
  │     Thought → Action → Observation → 循环         │
  │     这个循环逻辑是不变的，是所有 Agent 的骨架         │
  └──────────────────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
  ┌──────────────────┐     ┌──────────────────┐
  │  隐式 ReAct       │     │  显式 ReAct       │
  │  Action 用 FC 实现 │     │  Action 用文本实现 │
  │  模型输出 tool_calls│    │  模型输出 "Action:" │
  │  GPT-4/Claude 等  │     │  不支持 FC 的模型   │
  └──────────────────┘     └──────────────────┘

  不是"FC vs ReAct"二选一，而是 ReAct 是设计模式，FC 是实现方式。
  就像 MVC 是设计模式，具体可以用 Django 或 Spring 来实现——模式是思想，实现是工具。
```

### 4.3 常见困惑：显式 ReAct 为什么不能直接把 tools 描述传给模型？

**你的直觉是对的：如果模型支持 Function Calling，直接把 tools 描述传进去就行，不需要显式 ReAct。**

```
问题：显式 ReAct 用 "Thought: xxx\nAction: xxx" 文本协议，
     为什么不直接把 FC 的 tools 定义传给模型？

答案：取决于模型有没有被训练过 Function Calling。

  情况 1：模型支持 FC（GPT-4、Claude、Qwen 等）
    → 直接把 tools 描述传进去 ✓
    → 模型输出结构化 tool_calls，不用手动解析
    → 这就是 D04/D06 的做法 = 隐式 ReAct
    → 显式 ReAct 在这种情况下是多余的

  情况 2：模型不支持 FC（2023年的 GPT-3、部分开源模型）
    → tools 描述只能以自然语言形式写在 prompt 里：
        "You have the following tools:
         1. search(query) - search the web
         2. calculator(expr) - do math
         When using a tool, output: Action: tool_name\nAction Input: params"
    → 模型输出纯文本 "Action: search\nAction Input: 马斯克"
    → 开发者必须手动正则解析这段文本，才知道调哪个工具
    → 这就是显式 ReAct 存在的唯一原因
```

**那为什么 D08/D09 还要学显式 ReAct？**

```
① 教学价值：把 Thought→Action→Observation 拆开让你看到
   Function Calling 模式下，Thought 在模型内部不可见
   显式 ReAct 把每一步思考都打印出来，理解底层机制

② 兼容性：不是所有模型都支持 FC
   开源模型、微调模型可能没有 FC 训练
   此时显式 ReAct 是唯一选择

③ 可控性：某些场景需要完全掌控输出格式
   Thought 明文输出 = 可审计、可打断、可干预

一句话：Function Calling 是"高级模式"，显式 ReAct 是"手动档"。
学了手动档，开自动档更懂原理；但日常开自动档就够了。
```

### 4.4 为什么 Function Calling 出现后很多人"跳过"了显式 ReAct？

```
2023年：没有原生 Function Calling
  → 所有工具调用靠 prompt 工程
  → 必须用 Thought/Action/Observation 文本协议
  → ReAct 是当时的最佳实践

2025年：OpenAI/Anthropic 原生 Function Calling
  → LLM 内部推理 + 输出结构化 tool_calls
  → Thought 变成了模型的内部思考
  → 但对开发者来说，循环结构完全一样
```

**结论：** Function Calling 没有替代 ReAct，而是让 ReAct 的 Action 步骤变成了结构化的 API 调用，但 Thought→Action→Observation 的循环逻辑不变。

---

## 5. 三种主流 Agent 模式总览

### 5.1 一张图看懂区别

```
ReAct                    Plan-and-Execute            Reflection
────                     ────────────────            ──────────

边想边做                  先规划后执行                 做→评→改

Thought: A怎么做          ① 先分析任务整体              ① 生成答案
   ↓                     ② 列出步骤 Plan               ② 反思："这里有问题"
Action: 做A              ③ 逐步执行                    ③ 修改
   ↓                     ④ 检查结果                    ④ 重新生成
Observation: 结果                               
   ↓                                           
Thought: 下一步做B          
   ↓
Action: 做B
   ↓
...直到完成
```

### 5.2 三种模式对比

| | ReAct | Plan-and-Execute | Reflection |
|------|------|------|------|
| 规划时机 | 每步即时规划 | 先全局规划再执行 | 生成后反思再改 |
| 适用任务 | 需要逐步探索、不确定几步 | 任务可预先分解 | 有明确质量标准需多轮打磨 |
| 效率 | 灵活但可能绕路 | 直指目标但遇变不灵 | 多轮消耗大但质量高 |
| 举例 | 研究"X和Y谁先X" | 写一篇大纲→引言→正文→结语 | 写代码→review→改→再review |
| 代表产品 | **ChatGPT Deep Research**<br>多步搜索+综合推理<br>**Claude + Tool Use**<br>边想边调工具<br>**Perplexity Pro**<br>搜索→阅读→追问→总结 | **MetaGPT**<br>模拟PM→架构师→工程师流水线<br>**AutoGPT**<br>目标分解→逐步执行→检查<br>**CrewAI Hierarchical**<br>Supervisor分配→Executor执行 | **Claude Code**<br>生成代码→自审→修改→再审<br>**OpenAI o1/o3**<br>内部CoT+自我纠正<br>**Cursor Agent**<br>写代码→lint检查→修复 |

### 5.3 Tool-Use 模式（工具使用基础模式）

最基础的 Agent 模式——Agent 动态选择和调用工具完成子任务。所有其他 Agent 模式都建立在 Tool-Use 之上。

```
工作流程：
  ① 接收任务描述
  ② LLM 根据任务 + 可用工具列表，决定是否需要调用工具
  ③ 如需调用 → 生成工具名和参数 → 执行 → 获取结果
  ④ LLM 根据结果决定下一步（继续调用工具 or 输出答案）

和 ReAct 的关系：
  显式 ReAct：模型输出 Thought（文本）→ Action（文本）→ Observation（工具返回）
  隐式 ReAct（Tool-Use/FC）：
    模型不输出 Thought 文本，直接产出结构化的 tool_call
    推理发生在模型内部（前向传播时决定了调哪个工具、传什么参数），
    但这一步推理没有以"Thought:"的形式作为文本输出
    → 对外只看到 Action（tool_call JSON），看不到思考过程
  
  本质上是同一回事——D04/D06 的 Agent = Tool-Use 模式 = 隐式 ReAct
```

**关键设计点：**

```
1. 工具描述质量直接影响 Agent 决策准确率
   ❌ {"name": "search", "description": "搜索"}
   ✅ {"name": "web_search",
       "description": "在互联网上搜索实时信息。适用于需要最新数据时。
                      不适用于：已知常识、数学计算。",
       "parameters": {"query": {"type": "string",
                                "description": "搜索查询词，如'2024诺贝尔物理学奖'"}}}

2. 工具数量控制在 10-20 个以内，过多会降低选择准确率

3. 需要处理工具调用失败：重试（指数退避）+ 回退（备用工具）
```

---

### 5.4 Multi-Agent 模式（多智能体协作）

多个 Agent 分工协作，每个 Agent 专注特定领域，共享任务上下文。

```
四种常见架构：

① Supervisor（调度模式）
         ┌─────────┐
         │Supervisor│ ← 任务分解、分配、结果汇总
         └────┬────┘
        ┌─────┼─────┐
   ┌────▼─┐┌──▼──┐┌─▼────┐
   │Agent1││Agent2││Agent3│  ← 各自专注：搜索/写作/代码
   └──────┘└─────┘└──────┘

② Pipeline（流水线模式）
   Agent1 → Agent2 → Agent3
   研究     写初稿    审校
   适用于有明显阶段划分的任务

③ Debate（辩论模式）
   多个 Agent 独立回答 → 互相审查 → 多轮辩论 → 收敛到最佳答案
   适用于高准确性要求、有争议的判断类任务

④ Peer-to-Peer（对等模式）
   Agent 间平等协作，通过共享内存或消息传递通信
   无中心控制节点，去中心化、容错性要求高的场景
```

**多 Agent 系统的关键设计问题：**

```
通信机制：共享内存 / 消息队列 / 函数调用
状态管理：全局状态 vs 局部状态，并发冲突处理
冲突解决：当 Agent 意见不一致时如何决策（投票/仲裁/置信度加权）
成本控制：多 Agent = 多倍 Token 消耗，需要预算控制
```

**选择建议：** 先用单 Agent 解决，确认瓶颈后再拆分为多 Agent。多 Agent 意味多倍成本 + 调试复杂度急剧上升。

---

### 5.5 Human-in-the-Loop 模式（人机协作）

在关键决策点暂停，等待人工审批后继续。解决 Agent 可控性和安全性问题。

```
三种实现方式：

① 审批门（Approval Gate）
   Agent 执行高风险操作前暂停：
   "即将发送邮件给 1000 人，内容如下：... 确认发送？"
   → 等待人工确认 → 继续执行 或 中止操作

② 置信度触发
   当 Agent 对决策的置信度 < 阈值时，主动请求人类介入：
   "我不太确定这个解释是否正确，请帮我确认：..."

③ 定期检查点
   每执行 N 步暂停一次，让人审查当前进度和方向
   发现偏离及时纠正，避免越跑越偏
```

**什么时候必须用 Human-in-the-Loop？**

```
涉及不可逆操作：资金转账、生产环境变更、数据删除
合规行业：金融交易、医疗诊断、法律意见
Agent 能力边界外：主观判断、伦理决策、创造性工作
上线初期：建立信任，积累反馈数据
```

---

### 5.6 CodeAct 模式（代码即行动）

不预定义工具集，Agent 直接生成并执行代码来完成任务。由论文 *CodeAct* 和 Anthropic 的 *Computer Use* 推广。

```
工作流程：
  ① Agent 分析任务 → 生成 Python 代码
  ② 代码在安全沙箱中执行
  ③ Agent 观察执行结果（stdout / stderr）
  ④ 根据结果继续写代码 或 给出最终答案
```

```
和 Function Calling 的对比：

  Function Calling：预定义工具集 → LLM 选工具 → 填 JSON 参数 → 执行
  CodeAct：无预定义工具 → LLM 写代码 → 沙箱执行 → 观察结果

  CodeAct 优势：
    灵活性极高，不受预定义工具集限制
    LLM 天然擅长生成代码，比填 JSON 参数更自然
    可以用循环/条件/变量，表达能力远超单次函数调用
  
  CodeAct 劣势：
    安全风险大（必须严格沙箱隔离）
    执行不确定性（代码可能报错、死循环）
    调试困难（不知道是推理错了还是代码写错了）
  
  适用场景：数据分析、自动化脚本、开发类任务
  不适用：调用特定外部 API（不如 FC 直接）、安全敏感环境
```

---

### 5.7 七种模式速查：什么时候用哪种？

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 需要多步搜索 + 动态推理 | **ReAct** | 边想边做，每步根据上一步结果调整 |
| 任务可预先分解（写报告/做项目） | **Plan-and-Execute** | 全局规划，步骤清晰可追踪 |
| 需要高质量输出（写代码/写文章） | **Reflection** | 自我审查 + 迭代改进 |
| 基础工具调用（搜索/计算/API） | **Tool-Use** | 最轻量，所有 Agent 的底层模式 |
| 需要多领域专业分工 | **Multi-Agent** | 并行处理，各司其职 |
| 涉及高风险不可逆操作 | **Human-in-the-Loop** | 人工把关，安全可控 |
| 灵活数据分析/自动化脚本 | **CodeAct** | 代码表达力强，不限于预定义工具 |

> **组合使用才是常态：** 生产级 Agent 通常是多种模式的组合。比如：Plan-and-Execute 做顶层规划，每个步骤内部用 ReAct 执行，关键操作加 Human-in-the-Loop 审批，输出阶段用 Reflection 打磨质量。

---

## 6. ReAct 的局限

### 6.1 什么时候 ReAct 不好用

```
1. 任务非常简单，一步就能完成
   用户："1+1等于几？"
   ReAct 思考一堆再调计算器 → 浪费
   直接用 LLM 回答 "2" 就行

2. 需要全局规划的任务
   用户："写一个操作系统内核"
   边走边想 → 会走到哪算哪，缺乏整体架构
   应该先 Plan-and-Execute

3. 步骤太多容易走偏
   第3步的小错误 → 第5步放大 → 第10步完全偏离
   ReAct 没有纠错机制（Reflection 模式解决了这个）
```

### 6.2 ReAct 的核心风险

```
风险一：无限循环
  模型反复调同一个工具却得不到有用结果
  → 解决：max_turns + 重复检测（D06 已实现）

风险二：上下文膨胀
  每轮都加 Thought + Action + Observation，token 疯涨
  → 解决：摘要压缩（第3周 D17）

风险三：推理错误传播
  第2步推理错了，第3步基于错误推理继续，越来越离谱
  → 解决：Reflection 模式（第2周 D12）
```

---

## 7. 动手练习

```text
[ ] 练习 1：手动画一遍 ReAct 流程图
           任务："北京和东京现在的温差是多少？"
           标注每一步的 Thought / Action / Observation

[ ] 练习 2：对比 D06 Agent 和 ReAct 的区别
           找出 D06 agent.py 中哪些地方对应 Thought、Action、Observation

[ ] 练习 3：分析一个你常用的 AI 产品
           它用的是纯 LLM 回复，还是 Agent 循环？
           如果是 Agent，能识别出 Thought-Action-Observation 吗？

[ ] 练习 4：用 curl 或 Python 观察一次真实的 ReAct 过程
           给 LLM 一个需要搜索的问题
           打印每一轮的 messages
           观察上下文是如何逐轮增长的
```

---

## 8. 面试题精选

> 以下题目来自 agent-interview-hub 中阿里巴巴、美团、华为、字节等公司真实面经的高频考题，与 D08 知识直接对应。

---

### 8.1 高频题一：ReAct 框架工作原理

**真题来源：** 阿里巴巴、美团（二面）、华为

**题目：** "ReAct 框架详细讲讲，它的工作流程是怎样的？"

**参考答案：**

```
ReAct = Reasoning（推理）+ Acting（行动），交替进行思考和行动。

工作循环：Thought → Action → Observation → 循环直到结束

具体流程：
  Thought 1: 分析当前状况，决定需要什么信息
  Action 1: 调用工具（搜索/计算/API）
  Observation 1: 接收工具返回结果
  Thought 2: 基于结果继续推理，判断下一步
  Action 2: 继续调用工具 或 FINISH 输出答案
  ...直到信息足够给出最终答案

三要素：
  ① Thought：LLM 用自然语言"自言自语"，分析状态、规划下一步
  ② Action：选择工具 + 填写参数，或 FINISH 输出最终答案
  ③ Observation：工具执行结果，更新 Agent 对世界的认知
```

**追问常考：和 CoT（Chain-of-Thought）有什么区别？**

```
CoT = 纯推理，不调用工具，容易产生幻觉（凭记忆编造）
ReAct = 推理 + 行动，通过工具获取真实信息，有 Observation 锚定事实

举例：
  CoT 回答"2024年诺贝尔物理学奖得主"：
    → 凭记忆推理，可能记错或编造

  ReAct 回答同一问题：
    → Thought: 需要查最新数据
    → Action: search("2024诺贝尔物理学奖")
    → Observation: "John Hopfield 和 Geoffrey Hinton..."
    → 基于真实数据回答，避免幻觉

数据对比：ReAct 在 HotpotQA 上比 CoT 提升约 6%，在 FEVER 上提升约 10%
```

> 详见：[Agent核心概念与设计模式 - Q4](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md)、[八股文完整答案集 - Q34](../agent-interview-hub/通用知识/八股文完整答案集.md)

---

### 8.2 高频题二：Function Calling 和 ReAct 的关系

**真题来源：** 字节跳动、2025 高频新题

**题目：** "Function Calling 和 ReAct 有什么关系？是互斥的还是互补的？"

**参考答案：**

```
是互补关系，解决不同层次的问题：

  Function Calling → "能力层"（怎么调用工具）
    让 LLM 输出结构化的工具调用指令 {name: "search", arguments: {...}}
    解决的是"工具调用的格式和协议"问题

  ReAct → "策略层"（什么时候调、调哪个、结果怎么用）
    定义 Agent 的决策循环 Thought → Action → Observation
    解决的是"如何根据当前状态决定下一步"问题

关系类比：
  ReAct 是"大脑"（做决策：我需要查天气）
  Function Calling 是"手"（执行操作：生成 get_weather(city='北京')）

工程实现中它们总是一起出现：
  LangChain AgentExecutor → ReAct 决策循环
  底层调用 → OpenAI Function Calling API 执行工具
```

> 详见：[高频面试新题-2025](../agent-interview-hub/通用知识/高频面试新题-2025.md)

---

### 8.3 高频题三：Agent 任务规划——ReAct vs Plan-Execute 怎么选？

**真题来源：** 百度（二面）、牛客高频拷打题

**题目：** "Agent 怎么做任务规划的？什么时候用 ReAct，什么时候用 Plan-Execute？"

**参考答案：**

```
两种策略各有适用场景：

  ReAct（边走边想）：
    适用 → 探索性任务，不确定需要几步完成
    优点 → 灵活，能应对意外情况
    缺点 → 可能走弯路，步骤多时上下文膨胀
    举例 → "马斯克和贝佐斯谁先创业？两人差几岁？"

  Plan-and-Execute（先规划后执行）：
    适用 → 结构化任务，可以预先分解步骤
    优点 → LLM 调用次数少，进度可见，支持人工审批
    缺点 → 初始计划可能不准，遇到变化不灵活
    举例 → "帮我订机票+酒店+安排3天北京行程"

  生产实践 → 混合方案（Adaptive Planning）：
    ① 先粗粒度 Plan（顶层分几步）
    ② 每步内部用 ReAct 动态执行
    ③ 遇到异常时 Replan（调整后续计划）

  一句话：Plan 给方向，ReAct 给灵活，两者组合才是生产级方案。
```

> 详见：[高频拷打题-牛客热帖 - Q4](../agent-interview-hub/通用知识/高频拷打题-牛客热帖.md)

---

### 8.4 高频题四：ReAct 的常见问题和解决方案

**真题来源：** 美团、蚂蚁、通用八股文

**题目：** "ReAct 框架有什么缺陷？怎么解决？"

**参考答案：**

```
问题一：无限循环
  现象：模型反复调用同一工具却得不到有用结果
  场景：搜索结果不对 → 换词再搜 → 还是不对 → 再搜...
  解决：max_turns 硬限制 + 重复检测（最近 N 步行动去重 < 2 种 → 强制切换策略）

问题二：上下文膨胀
  现象：每轮 Thought+Action+Observation 累加，token 疯涨
  场景：20 轮对话后 context 接近极限，后续推理质量下降
  解决：摘要压缩（LLM 压缩历史）、滑动窗口（只保留最近 K 轮原文）

问题三：推理错误传播
  现象：第 2 步推理错了 → 第 3 步基于错误继续 → 第 5 步完全偏离
  场景：搜索到错误信息 → 当作事实继续推理 → 得出结论完全错误
  解决：Reflection 模式（执行后自我检查）、关键步骤交叉验证

问题四：工具选择错误
  现象：该用计算器却用了搜索，参数填错格式
  解决：优化工具描述（含适用/不适用场景 + 参数示例）、
        Few-shot 示例、参数校验 + 重试
```

---

### 8.5 高频题五：Agent Loop 的核心设计考量

**真题来源：** 百度（社招二面，系统设计题）

**题目：** "从零设计一个 Agent 系统，Agent Loop 要考虑哪些点？"

**参考答案：**

```
核心设计考量：

① 终止条件（必须有明确的退出机制）
  - max_steps：硬限制最大步数
  - 目标达成判断：LLM 自主输出 FINISH
  - 用户中断：支持手动停止

② 上下文管理（防止 token 爆炸）
  - 滑动窗口：保留最近 K 轮完整内容
  - 摘要压缩：更早内容用 LLM 摘要
  - 策略：系统提示 + 最近 K 轮原文 + 历史摘要

③ 错误处理（每层都要兜底）
  - 工具层：重试（指数退避）+ 回退（备用工具）
  - 推理层：循环检测 + 死胡同检测
  - 任务层：总超时 + Token 预算上限

④ 状态管理（记住中间结果）
  - 工作记忆：当前任务的中间变量
  - 避免重复工作：已获取的信息不要重复搜索

⑤ 可观测性（出问题能定位）
  - 每步记录 Thought / Action / Observation
  - 追踪 Token 消耗和延迟
  - 支持单步回放调试
```

---

### 8.6 实操考题：手写 ReAct Agent

**来源：** agent-interview-hub 项目实战题库

**题目：** 实现一个遵循 ReAct 模式的 AI Agent，通过 Thought → Action → Observation 循环解决问题。

**核心要求：**

```
1. ReAct 循环：Thought（推理当前状态）→ Action（调用工具）→ Observation（观察结果）→ 更新思考

2. 工具集成（至少 2 个）：搜索工具 + 计算器工具，Agent 自主选择

3. 多轮交互：维护上下文，支持用户追问

4. 完成判断：有明确机制判断任务何时完成，输出最终答案

加分项：错误恢复、记忆管理、Guardrails、Web 界面
```

> 详见：[实操考题 - 03-ReAct模式Agent](../agent-interview-hub/项目实战/实操考题/03-ReAct模式Agent.md)

---

## 9. 关键收获

### 9.1 ReAct 一句话

```
ReAct = 让 LLM 在"思考→行动→观察→再思考"的循环中自主解决问题，
       而不是一次性给出答案。
```

### 9.2 你已经会 ReAct 了

```
D04 的 Agent 循环 = 隐式 ReAct
D06 的 DevTool Agent = 隐式 ReAct + 安全防护

明天 D09：用纯 Python 手写显式 ReAct（不用 Function Calling API）
   → 你会看到 Thought/Action/Observation 作为文本输出的完整过程
   → 理解了底层，再用 Function Calling 就知其所以然
```

### 9.3 知识定位

```
第1周：怎么调 API、怎么用工具          → "会开汽车"
第2周：理解 Agent 的推理循环           → "懂发动机怎么工作"
   D08：ReAct 原理（今天）
   D09：纯 Python 实现 ReAct
   D10：工具系统设计
   D11：Plan-and-Execute
   D12：Reflection
   D13：三种模式对比
```

---

## 参考

- [ReAct 论文 (Yao et al., 2023)](https://arxiv.org/abs/2210.03629)
- [Lilian Weng - LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)
- [Agent 核心概念与设计模式](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md)
- [Anthropic - Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
