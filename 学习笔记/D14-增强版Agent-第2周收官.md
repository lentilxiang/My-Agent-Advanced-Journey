# D14：增强版 Agent —— 第 2 周收官

> 目标：选用 Plan-and-Execute + Reflection 组合模式，接入 6 个工具，做一个能写代码、能读文件、能搜索的完整 Agent。

---

## 1. 为什么选 Plan-and-Execute 做基础？

```
第 2 周的三个模式各有擅长：
  ReAct             → 探索性任务（不知道几步）
  Plan-and-Execute  → 结构性任务（可分解步骤）
  Reflection        → 有质量标准的任务（需要打磨）

D14 做一个"AI 编程助手"——需要搜资料、读代码、写代码、检查输出。
这个任务天然适合 Plan-and-Execute：
  ① Planner 分解：搜资料 → 读文件 → 写代码 → 测试 → 审查
  ② Executor 执行每步（内部用 ReAct 搜/读/写）
  ③ Reflection 打磨最终代码
```

---

## 2. 6 个工具

```
工具清单（比 D10 多了 3 个）：
  1. web_search       → 搜索互联网信息
  2. calculator       → 数学计算
  3. python_executor  → 在沙箱中执行 Python 代码（新增）
  4. file_reader      → 读取本地文件内容（新增）
  5. file_writer      → 写入文件到磁盘（新增，需确认）
  6. get_datetime     → 获取当前时间
```

---

## 3. 架构：Plan-and-Execute + Reflection 叠加

```
  用户任务
     │
     ▼
  Planner ──→ [Step1, Step2, Step3, ...]
     │
     ▼
  Executor（每步 = 迷你 ReAct）
     │  工具: search / python_exec / file_rw / calculator
     │
     ▼
  每步结果汇总
     │
     ▼
  Reflection（对最终输出做审查+修改）
     │
     ▼
  最终输出
```

---

## 4. 关键设计决策

```
1. Python 执行器必须沙箱化
   - 独立进程执行，超时 10 秒
   - 禁用 os.system / subprocess / __import__
   - 只允许内置安全函数

2. 文件写入需确认
   - require_confirmation=True
   - Agent 在写文件前展示内容，等待人工确认

3. 每步 Executor 的 max_turns=3
   - 步骤目标窄，不需要太多子循环
   - 减少 token 消耗
```

---

## 5. 第 2 周总结

```
D08  ReAct 循环原理        → 理解 Thought→Action→Observation
D09  纯 Python 实现 ReAct  → 手写文本协议 + JSON 模式
D10  工具系统设计          → 注册/描述/校验/选择/容错
D11  Plan-and-Execute     → Planner + Executor + Replanner
D12  Reflection           → Generator + Critic + Reviser
D13  三种模式对比          → 选型决策框架
D14  增强版 Agent          → 组合模式 + 6 工具实战

第 2 周核心收获：
  Agent 不是调 API，而是设计循环。
  ReAct 是骨架，Plan-and-Execute 是大脑，Reflection 是质检员。
  工具系统是基础设施——决定 Agent 能做什么。
```

---

## 参考

- [D10：工具系统设计](./D10-工具系统设计.md)
- [D11：Plan-and-Execute 模式](./D11-Plan-and-Execute模式.md)
- [D12：Reflection 模式](./D12-Reflection模式.md)
- [Anthropic - Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
