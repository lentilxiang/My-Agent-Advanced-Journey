# D09：纯 Python 实现显式 ReAct

> 目标：不用 Function Calling API，手写 ReAct 循环，理解 Thought→Action→Observation 的底层机制。

---

## 1. 为什么要手写显式 ReAct？

D04/D06 的 Agent 用的是 Function Calling——模型内部推理，直接输出结构化 `tool_calls`，开发只需要读 `response.tool_calls` 字段。

```
D08 学了理论 → D09 手写底层实现 → 彻底理解循环怎么运转
```

**手写一遍的收获：**

```
1. 你会看到 Thought 以明文形式出现在 LLM 输出里
   - FC 模式下这个被隐藏了，你只能看到 tool_call JSON
   - 手写模式，每一步推理过程都写在文本里

2. 你会自己写解析器把 "Action: search" 从文本中提取出来
   - 这是 FC 出现之前所有 Agent 框架做的事
   - 理解了文本解析的脆弱性，才懂 FC 为什么是革命性的

3. 循环控制的实现：max_turns、重复检测、终止判断
   - 这些在 FC 模式下也存在，只是被框架隐藏了
   - 手写一遍，以后用 LangGraph 就知其所以然
```

---

## 2. 显式 ReAct 的协议设计

### 2.1 让 LLM 按格式输出

```
通过 System Prompt 教模型按固定格式输出：

  "You have access to the following tools:
   1. search(query) - search the web
   2. calculator(expr) - evaluate math expression
   3. datetime() - get current date and time

   When you need to use a tool, output EXACTLY:
   Thought: <your reasoning about what to do next>
   Action: <tool_name>
   Action Input: <parameters>

   When you have the final answer, output EXACTLY:
   Thought: I now have all the information needed.
   Action: Finish
   Action Input: <final answer to the user>"
```

### 2.2 LLM 会输出的文本格式

```
一轮对话中 LLM 的典型输出：

  Thought: 用户想知道北京现在的温度。我需要搜索最新天气数据。
  Action: search
  Action Input: 北京 2025年6月 当前温度

  Thought: 搜索结果显示北京现在 32°C。信息够了，可以回答。
  Action: Finish
  Action Input: 北京当前温度是 32°C，体感较热，建议做好防晒。
```

### 2.3 开发者需要做的解析

```python
import re

def parse_react_output(text: str) -> dict:
    """从 LLM 输出的文本中提取 Thought / Action / Action Input"""
    thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", text, re.DOTALL)
    action_match = re.search(r"Action:\s*(.+?)(?=\nAction Input:|\Z)", text)
    action_input_match = re.search(r"Action Input:\s*(.+)", text, re.DOTALL)

    return {
        "thought": thought_match.group(1).strip() if thought_match else None,
        "action": action_match.group(1).strip() if action_match else None,
        "action_input": action_input_match.group(1).strip() if action_input_match else None
    }
```

---

## 3. 核心代码结构

```
react_agent.py
├── Tool 类              → 工具基类：name, description, execute()
├── 3 个工具             → search, calculator, datetime
├── build_prompt()       → 组装 System Prompt + 工具列表 + 对话历史
├── parse_react_output() → 正则提取 Thought / Action / Action Input
├── execute_action()     → 根据 Action 名字找到工具并执行
├── react_loop()         → 主循环：调 LLM → 解析 → 执行工具 → 拼回结果 → 循环
└── main()               → 入口，交互式对话
```

---

## 4. 关键实现细节

### 4.1 怎么把工具信息传给不支持 FC 的模型？

```
FC 模式：
  client.chat.completions.create(
      model="gpt-4",
      messages=[...],
      tools=[{"type": "function", "function": {"name": "search", ...}}]  ← API 原生支持
  )

显式 ReAct 模式：
  直接把工具描述以自然语言写在 System Prompt 里：
  system_prompt = """
  You have the following tools:
  1. search(query: str) - Search the web for information. Use when you need real-time data.
  2. calculator(expr: str) - Evaluate a math expression. Use for calculations.
  3. datetime() - Get current date and time.
  ...
  """
  client.chat.completions.create(
      model="gpt-4",
      messages=[{"role": "system", "content": system_prompt}, ...]
      # 没有 tools 参数！
  )
```

### 4.2 解析的脆弱性——为什么 FC 是革命性的

```
文本解析的常见坑：

模型输出不按格式：
  ❌ "Action:search"          ← 少了冒号后的空格，正则就匹配失败
  ❌ "Action: search\nInput: x" ← 写成了 Input 而不是 Action Input
  ❌ "Thought: ... \nAction: ... \n" ← 多了一个空行
  ❌ Action Input 里包含换行，正则的 .* 没开 DOTALL

Function Calling 彻底解决了这个问题：
  tool_calls 是结构化的 JSON → 永远不需要正则
  格式错误率为零（由 API 保证）
```

### 4.3 循环控制

```python
def react_loop(question, max_turns=10):
    messages = [{"role": "system", "content": build_system_prompt()}]
    messages.append({"role": "user", "content": question})

    for turn in range(max_turns):
        response = llm.chat(messages)           # ① 调 LLM
        parsed = parse_react_output(response)   # ② 解析文本

        print(f"Thought: {parsed['thought']}")  # ③ 打印 Thought（可见！）

        if parsed["action"] == "Finish":        # ④ 终止判断
            return parsed["action_input"]

        result = execute_action(parsed)          # ⑤ 执行工具
        print(f"Observation: {result}")

        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"Observation: {result}"})
        # ⑥ 拼回上下文，进入下一轮

    return "达到最大轮次，任务未完成"
```

---

## 5. 和 D04/D06 FC 模式的对比

```
              D04/D06 (隐式 ReAct)        D09 (显式 ReAct)
  ──────────  ────────────────────────    ─────────────────────
  LLM 输出     结构化 tool_calls JSON      纯文本 "Action: xxx"
  解析方式     读 response.tool_calls      正则匹配文本
  格式稳定性   100%（API保证）              可能解析失败
  Thought     不可见（模型内部）            明文可见
  代码量       少                          多（需自己写解析+循环）
  学习价值     会用                         知道为什么这么设计
```

---

## 6. 动手练习

```text
[ ] 练习 1：跑通 D09 的 react_agent.py
           用 "北京和东京现在的温差是多少？" 测试
           观察每轮的 Thought / Action / Observation 输出

[ ] 练习 2：故意给模型一个格式错误的 prompt，观察解析失败的情况
           体会为什么 FC 比文本解析可靠

[ ] 练习 3：新增一个工具（比如翻译工具）
           在 tools 列表里注册 → prompt 里加描述 → 解析器不动

[ ] 练习 4：对比 D09 的显式 ReAct 和 D06 的 FC Agent
           关键差异：代码量？可靠性？调试体验？
```

---

## 7. 关键收获

```
显式 ReAct 让你看到 Agent 循环的全貌：
  Thought（模型想什么）→ Action（模型决定调什么）
  → Observation（工具返回什么）→ 再 Thought → ...

Function Calling 把这些都隐藏成了结构化 API 调用。
手写一遍显式 ReAct，以后用任何 Agent 框架，
你都知道底层在做什么——不是在调"黑盒 API"，而是在跑 ReAct 循环。
```

---

## 参考

- [ReAct 论文 (Yao et al., 2023)](https://arxiv.org/abs/2210.03629)
- [Lilian Weng - LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)
- [D08：ReAct 循环原理](./D08-ReAct循环原理.md)
- [实操考题 - 03-ReAct模式Agent](../agent-interview-hub/项目实战/实操考题/03-ReAct模式Agent.md)
