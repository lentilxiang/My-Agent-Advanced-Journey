# D11：Plan-and-Execute 模式

> 目标：理解 Plan-and-Execute 的架构——先规划后执行，对比 ReAct 的边走边想，知道什么时候用哪种。

---

## 1. 问题：ReAct 什么时候不够？

D08 讲了 ReAct 的三个局限，其中最关键的一个：**"需要全局规划的任务，ReAct 会走到哪算哪"**。

```
任务："写一篇关于 AI Agent 发展现状的调研报告，包含引言、技术分析、市场现状、总结"

ReAct 的方式（边走边想）：
  Thought: 先搜一下 AI Agent
  Action: search("AI Agent")
  Observation: 一堆搜索结果...
  Thought: 再看看技术架构
  Action: search("Agent 架构")
  Observation: 又是很多内容...
  Thought: 应该够了，写吧 → Action: Finish
  → 没有大纲，想到哪写到哪，结构松散

Plan-and-Execute 的方式（先规划后执行）：
  ① Planner: 分析任务 → 生成步骤：
     Step 1: 收集 AI Agent 定义与发展历程
     Step 2: 调研核心技术（ReAct/多Agent/记忆）
     Step 3: 调研市场现状和代表产品
     Step 4: 综合撰写报告（引言→分析→市场→总结）
  ② Executor: 逐步执行每个 Step，每步内部是一个小 ReAct
  ③ Replanner: 第 2 步发现"记忆系统"值得展开 → 调整 Step 2-3
  ④ 全部执行完 → 综合输出
  → 有骨架，不跑偏，每步有明确目标
```

**核心差异：**

```
ReAct：              Plan-and-Execute：
  边走边想              先画地图再走
  灵活但容易绕路         方向明确不走偏
  适合探索性任务         适合结构性任务
  不知道要走几步         知道大概几步
```

---

## 2. Plan-and-Execute 架构

### 2.1 三组件

```
                    ┌─────────────┐
                    │   用户任务    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  ① Planner  │ ← LLM：分解任务 → 生成步骤列表
                    │  强模型      │   每个步骤有明确的目标和预期产出
                    └──────┬──────┘
                           │
                           ▼   Plan: [Step1, Step2, Step3, Step4]
                    ┌─────────────┐
                    │ ② Executor  │ ← 逐步执行，每步是 ReAct 子循环
                    │  可以是弱模型  │   步骤结果存入 scratchpad
                    └──────┬──────┘
                           │
                           ▼   Results: [R1, R2, R3, R4]
              ┌────────────┴────────────┐
              │                        │
              ▼                        ▼
      ┌─────────────┐          ┌─────────────┐
      │③ Replanner  │          │④ Synthesizer│
      │ 每步后检查：  │          │ 汇总所有结果 │
      │ 后续计划是否  │          │ 生成最终输出 │
      │ 需要调整？    │          └─────────────┘
      └─────────────┘

  关键设计：
  - Planner 用强模型（需要全局视野和任务分解能力）
  - Executor 可以用弱模型（每步目标明确，推理负担小）
  - Replanner 是可选的——简单任务的计划不需要调整
```

### 2.2 和 ReAct 的循环结构对比

```
ReAct 循环（D08/D09）：
            ┌──────────────────────────┐
            │  Thought → Action → Obs  │ → 循环，直到 Finish
            └──────────────────────────┘
  每步决策粒度：下一个工具调用是什么


Plan-and-Execute：
  ┌─────────┐     ┌──────────────────────┐
  │ Planner │ →   │ Step 1: Thought→Act→Obs │
  │ (一次)   │     │ Step 2: Thought→Act→Obs │ → Replanner(可选)
  │         │     │ Step 3: Thought→Act→Obs │
  └─────────┘     └──────────────────────┘
  每步决策粒度：这一步的目标是什么
```

---

## 3. Planner：如何分解任务？

### 3.1 Planner 的 Prompt 设计

```
关键：让 LLM 输出结构化的步骤列表，每个步骤要包含：
  ① 步骤目标：这一步要完成什么
  ② 预期产出：这一步结束时应该有什么
  ③ 依赖关系：这一步依赖前面哪些步骤的结果

Prompt 模板：
  "你是一个任务规划专家。请将以下任务分解为有序的执行步骤。

  每个步骤包含：
  - goal: 步骤目标（一句话描述要完成什么）
  - expected_output: 预期产出（这一步结束时要有什么）
  - depends_on: 依赖的前置步骤编号（空列表=无依赖）

  输出 JSON 格式：
  {
    "overall_goal": "任务总目标",
    "steps": [
      {"id": 1, "goal": "...", "expected_output": "...", "depends_on": []},
      {"id": 2, "goal": "...", "expected_output": "...", "depends_on": [1]},
      ...
    ]
  }

  规则：
  - 步骤数控制在 3-7 个
  - 每个步骤目标明确、可独立执行
  - 步骤间有逻辑顺序
  - 最后一步是综合汇总"
```

### 3.2 好计划 vs 差计划

```
❌ 差计划（太粗，无法执行）：
  Step 1: 调研
  Step 2: 写报告
  → 每个步骤目标模糊，执行时还是"走到哪算哪"

✅ 好计划（目标明确）：
  Step 1: 收集 AI Agent 的定义、核心特征、与传统LLM的区别
         预期产出: 3-5个要点的结构化笔记
  Step 2: 调研 ReAct/多Agent/记忆三大核心技术
         预期产出: 每项技术的原理描述 + 代表产品
  Step 3: 调研市场现状：主要玩家、融资情况、应用场景
         预期产出: 3-5个代表公司的简要分析
  Step 4: 综合撰写报告（引言→技术→市场→总结）
         预期产出: 完整的调研报告（依赖 Step 1-3 的结果）
  → 每步有明确的"做完"标准，Executor 不会迷失
```

---

## 4. Executor：如何执行一个步骤？

每个步骤的内部是一个**迷你 ReAct 循环**——因为单个步骤内仍然可能需要多步搜索。

```
Executor 执行 Step 2 "调研三大核心技术"：

  子 Thought: 先查 ReAct 论文和最新进展
  子 Action: search("ReAct agent 2024 2025")
  子 Observation: "ReAct 由 Yao et al. 提出..."

  子 Thought: 再查多 Agent 协作
  子 Action: search("multi agent collaboration 2025")
  子 Observation: "多 Agent 包括 Supervisor、Debate..."

  子 Thought: 最后查记忆系统
  子 Action: search("agent memory system 2025")
  子 Observation: "记忆分短期/工作/长期..."

  子 Thought: 三大技术都查完了，汇总
  子 Action: Finish
  子 Action Input: "ReAct: ...\n多Agent: ...\n记忆: ..."

关键：Executor 的 max_turns 要比纯 ReAct 少
  - 每个步骤内 max_turns=3~5（步骤目标窄，不需要太多步）
  - 而不是整体的 max_turns=10+
```

---

## 5. Replanner：什么时候需要调整计划？

```
Replanner 不是每次都跑——只在以下条件触发：

触发条件 1：步骤执行结果和预期不符
  例：Step 2 搜不到信息 → Replanner: "原计划需要调整，先加一步补充搜索"

触发条件 2：执行结果超出预期（发现新方向）
  例：Step 3 发现"安全"是个重要子话题 → Replanner: "在原 Step 3 后加 Step 3.5：Agent 安全"

触发条件 3：依赖步骤失败
  例：Step 1 失败 → 跳过依赖 Step 1 的 Step 2-3 → Replanner 重新规划

Replanner 的实现：
  def maybe_replan(plan, completed, current_result) -> list:
      # 把已完成的步骤结果 + 当前计划剩余部分传给 LLM
      # LLM 判断：剩余计划是否仍然合适？需要增/删/改哪些？
      prompt = f"原计划剩余: {plan.remaining}\n已完成: {completed}\n当前结果: {current_result}\n是否需要调整？"
      revised = llm.generate(prompt)
      return revised if revised.needs_change else plan.remaining
```

---

## 6. Plan-and-Execute vs ReAct 完整对比

```
              ReAct                    Plan-and-Execute
  ──────────  ─────────────────────    ────────────────────────
  比喻        边走边问路                先看地图再走
  规划时机     每步即时规划              先全局规划
  LLM 调用     每步 1 次                规划 1 次 + 每步 1-3 次
  步骤可见性   不可见（走到哪是哪）       完全可见（Plan 明文）
  适用任务     探索性、不确定几步         结构性、可分解
  灵活性       高（遇变即调）            中（需 Replanner 调整）
  成本         低（步骤少时）            高（Planner + Executor 双重调用）
  风险         走弯路、死循环             初始计划不准，执行全错
  例子         "A和B谁更早创业？"        "写一篇 AI Agent 调研报告"
```

---

## 7. 动手练习

```text
[ ] 练习 1：给两个任务分别用 ReAct 和 Plan-and-Execute 跑一遍
           "苹果公司过去3年每年的营收增长率是多少？"
           "写一份 AI Agent 学习路线规划"
           对比两种模式的步骤数和输出质量

[ ] 练习 2：观察 Planner 的分解质量
           同一个任务，让 LLM 分解 3 次，看看计划是否一致
           分析：什么类型的任务分解容易不一致？

[ ] 练习 3：触发 Replanner
           在 Executor 某一步故意返回"信息不足"
           观察 Replanner 是否调整了后续计划

[ ] 练习 4：对比 Planner 用强模型 vs 弱模型
           GPT-4 做规划 vs GPT-4o-mini 做规划
           对比计划质量（合理性、可执行性、粒度）
```

---

## 8. 关键收获

```
Plan-and-Execute = Planner（规划） + Executor（执行） + Replanner（调整）

核心思想：
  ReAct 的"边走边想"适合探索，但缺乏全局视野。
  Plan-and-Execute 先把任务看清楚再动手，每步有明确目标。

和 ReAct 的关系：
  不是替代，是升级——Plan 给方向，ReAct 给灵活。
  生产级 Agent = Plan-and-Execute 做顶层编排 + ReAct 做每步执行。

明天 D12：Reflection 模式——做完了还要自我检查，提升输出质量。
```

---

## 参考

- [Plan-and-Execute 论文](https://arxiv.org/abs/2305.04091)
- [Agent 核心概念与设计模式 - Plan-and-Execute](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md)
- [D08：ReAct 循环原理](./D08-ReAct循环原理.md)
- [D10：工具系统设计](./D10-工具系统设计.md)
