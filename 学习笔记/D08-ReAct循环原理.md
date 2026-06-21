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

### 4.2 显式 ReAct vs 隐式 ReAct

```
隐式 ReAct（D06、Function Calling 原生）：
  LLM 内部推理 + 直接输出 tool_calls
  优点：简单，利用原生 API
  缺点：推理过程不可见，难调试

显式 ReAct（传统 ReAct 论文风格）：
  LLM 输出 Thought: ... \n Action: ... \n Action Input: ...
  优点：推理过程完全可见，可解释
  缺点：需要自己解析文本，不用 Function Calling API
```

### 4.3 为什么 Function Calling 出现后很多人"跳过"了显式 ReAct？

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

## 8. 关键收获

### 8.1 ReAct 一句话

```
ReAct = 让 LLM 在"思考→行动→观察→再思考"的循环中自主解决问题，
       而不是一次性给出答案。
```

### 8.2 你已经会 ReAct 了

```
D04 的 Agent 循环 = 隐式 ReAct
D06 的 DevTool Agent = 隐式 ReAct + 安全防护

明天 D09：用纯 Python 手写显式 ReAct（不用 Function Calling API）
   → 你会看到 Thought/Action/Observation 作为文本输出的完整过程
   → 理解了底层，再用 Function Calling 就知其所以然
```

### 8.3 知识定位

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
