# D12：Reflection 模式

> 目标：理解 Reflection 模式——生成后自我检查并迭代改进，解决 ReAct 的"错误传播"问题。

---

## 1. 问题：ReAct 的错误会传播

D08 提到 ReAct 的三个局限之一：**"第 2 步推理错了 → 第 3 步基于错误推理继续 → 第 5 步完全偏离"**。

```
ReAct 的问题：做完就完了，不检查。

  用户："写一个二分查找的 Python 实现"
  
  ReAct 的做法：
    Thought: 二分查找很简单
    Action: Finish
    Action Input: "def binary_search(arr, target):
                      left, right = 0, len(arr)
                      while left < right:
                          mid = (left + right) // 2
                          if arr[mid] < target: left = mid + 1
                          else: right = mid
                      return left"
    → 这段代码有 bug（right=len(arr) 应该是 len(arr)-1）
    → ReAct 没有检查机制，直接输出有问题的代码

  Reflection 的做法：
    ① Generate: 生成初始代码（同上）
    ② Critic: "检查这段代码：1. 边界条件 len(arr) 不应该是 len(arr)-1 吗？
                2. 循环条件 left < right 和 left <= right 哪个对？
                3. 当 target 不在数组中时返回什么？"
    ③ Revise: 根据 Review 修改代码
    ④ Critic: "修改后的代码: right初始化为len(arr)-1，循环条件 left<=right，
                未找到返回 -1。逻辑正确。"
    ⑤ 输出经过审查的代码
    → 通过"做→查→改"循环，避免低级错误
```

---

## 2. Reflection 架构

### 2.1 核心循环

```
                    ┌─────────────┐
                    │   用户任务    │
                    └──────┬──────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │     Reflection 循环           │
            │                              │
            │  ┌──────────┐                │
            │  │① Generator│ ← 生成初始答案 │
            │  └────┬─────┘                │
            │       │ 初稿                  │
            │       ▼                      │
            │  ┌──────────┐                │
            │  │ ② Critic │ ← 评估质量      │
            │  │ (可以是LLM自身)│ 找出问题    │
            │  └────┬─────┘                │
            │       │ 通过？                │
            │    ┌──┴──┐                   │
            │    │     │                   │
            │   通过   不通过                │
            │    │     │                   │
            │    │     ▼                   │
            │    │  ┌──────────┐           │
            │    │  │③ Reviser │ ← 根据反馈改│
            │    │  └────┬─────┘           │
            │    │       │ 改后版本          │
            │    │       └────→ 回到 ②      │
            │    │                         │
            └────┼─────────────────────────┘
                 ▼
            最终输出
```

### 2.2 和 ReAct 的对比

```
ReAct 循环：                    Reflection 循环：
  Thought → Action → Obs          Generate → Critique → Revise
  边想边做，每步产出一个结果       做完后回头检查，不满意就改

ReAct 的 Action 是调工具          Reflection 的 Action 是修改输出
ReAct 的 Observation 是外部数据    Reflection 的 Critique 是内部评价

关键差异：
  ReAct：横向探索（信息收集）→ 多步积累信息
  Reflection：纵向打磨（质量提升）→ 同一份输出多轮迭代
```

---

## 3. 三个组件的设计

### 3.1 Generator：生成初始答案

```
Generator 可以用任意方式生成初稿：
  - 纯 LLM 生成（简单任务）
  - ReAct 循环生成（需要搜索的任务）
  - 模板填充（结构化任务）

关键：初稿不需要完美——Reflection 的价值就在于此。
      放手让 Generator 生成，Critic 会找出问题。
```

### 3.2 Critic：评估输出质量

```
Critic 是 Reflection 的核心——它决定了"改什么"和"改对没有"。

评估维度（可按任务定制）：
  ① 正确性：逻辑有无错误、事实有无幻觉
  ② 完整性：是否覆盖了所有要求
  ③ 清晰度：表达是否清晰、结构是否合理
  ④ 安全性：代码有无漏洞、回答有无风险

Critic 的 Prompt 设计：
  "你是一个严格的审查员。请审查以下输出，从正确性、完整性、清晰度三个维度评估。
  
  对每个维度：
  - 如果通过，标注 [PASS]
  - 如果发现问题，标注 [FAIL] 并说明具体问题和改进建议
  
  如果所有维度都 PASS，标注 OVERALL: PASS。
  否则标注 OVERALL: FAIL，并给出具体的修改建议。"
```

### 3.3 Reviser：根据反馈修改

```
Reviser 拿到 Critic 的反馈后，逐条针对性修改。

关键设计：
  - 不能盲目全改 → 可能把对的改错（过度修改）
  - 要保留 Critic 认可的部分 → 只改有问题的部分
  - 改完后 Critic 再审查 → 形成闭环

Prompt 示例：
  "根据以下审查意见修改输出。只修改被指出的问题，保留其他部分不变。
  
  审查意见: {critique}
  原始输出: {original_output}
  
  请输出修改后的完整版本。"
```

---

## 4. 实现细节

### 4.1 终止条件

```
Reflection 的终止条件比 ReAct 复杂——什么时候算"足够好"？

方案 A：Critic 全部 PASS → 终止
方案 B：达到最大轮次（如 3 轮）→ 输出当前最佳版本
方案 C：连续两轮无实质性修改 → 终止（避免来回改）
方案 D：新版本比旧版本更差 → 回退到旧版本并终止（防止越改越差）

生产推荐：A + B + D 组合
  - 优先用 A（Critic PASS）
  - 最多 3 轮（B，控制成本）
  - 检测退化时回退（D，保证质量不降）
```

### 4.2 防止过度修改

```
Reflection 的风险之一：越改越差。

原因：
  - Critic 的审查意见本身可能有误（LLM 评判 LLM → 不可靠）
  - Reviser 在修改时可能引入新问题
  - 多轮迭代使输出偏离原始意图

对策：
  ① 保留每个版本 → 最终输出选 Critic 评分最高的
  ② 每次只改 Critic 指出的具体问题 → 不改其他部分
  ③ 限制修改轮次 → 最多 2-3 轮
```

---

## 5. 三种模式对比

```
              ReAct           Plan-and-Execute     Reflection
  ────────    ─────────────   ─────────────────    ───────────────
  核心动作     思考→行动→观察   规划→执行→调整        生成→审查→修改
  方向        横向（广度）     纵向→横向             纵向（深度）
  适用         探索性任务      结构性任务            有质量标准的任务
  输出特点     每步产出碎片     每步产出段落           同一份输出多轮打磨
  成本         中             高（双重LLM）          高（多轮重复）
  最怕         走弯路          规划不准              越改越差
  典型场景     多步搜索问答     写报告/做项目          写代码/写文章
```

---

## 6. 动手练习

```text
[ ] 练习 1：让 Generator 写一段有 bug 的代码
           Critic 能否发现所有问题？
           记录发现的问题数量和类型

[ ] 练习 2：对比 Reflection 1 轮 vs 3 轮
           同一任务：初始输出 → 1轮审查修改 → 3轮审查修改
           输出质量提升多少？成本增加了多少？

[ ] 练习 3：Critic 用强模型 vs 弱模型
           GPT-4 做审查 vs GPT-4o-mini 做审查
           审查意见的准确度有没有明显差异？

[ ] 练习 4：检测过度修改
           连续 5 轮 Reflection，观察输出变化轨迹
           有没有出现"第 3 轮改对了、第 4 轮又改错了"的情况？
```

---

## 7. 关键收获

```
Reflection = Generator（生成） + Critic（审查） + Reviser（修改）

它是"纵向打磨"的模式：
  ReAct 解决"信息不够" → 调工具拿信息
  Reflection 解决"质量不够" → 自查自改

三种模式互补：
  Plan-and-Execute 给方向（宏观）
  ReAct 给信息（中观）
  Reflection 给质量（微观）

明天 D13：三种模式完整对比 + 选型决策框架。
```

---

## 参考

- [Reflexion 论文](https://arxiv.org/abs/2303.11366)
- [Agent 核心概念与设计模式 - Reflection](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md)
- [D08：ReAct 循环原理](./D08-ReAct循环原理.md)
- [D11：Plan-and-Execute 模式](./D11-Plan-and-Execute模式.md)
