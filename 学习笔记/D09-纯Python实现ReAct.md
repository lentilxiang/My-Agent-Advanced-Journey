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

## 2. 两种实现方案：文本 vs JSON

D09 代码支持两种模式，`--mode` 参数切换。默认用 Level 2。

### Level 1 (TEXT)：文本协议 —— 2023 年 ReAct 论文的原版做法

**做法：** System Prompt 教模型输出纯文本 `Thought: ... Action: ...` 格式，开发者用正则解析。

```
Prompt 教模型：
  "When you need to use a tool, output EXACTLY:
   Thought: <your reasoning>
   Action: <tool_name>
   Action Input: <parameters>"

模型输出（纯文本）：
  Thought: 需要查北京温度
  Action: search
  Action Input: 北京温度

开发者用正则解析：
  thought = re.search(r"Thought:\s*(.+?)(?=\nAction:)", text)
  action = re.search(r"Action:\s*(\S+)", text)
  ...

问题：
  - 模型可能多写个空格、换行、中文冒号 → 正则匹配失败
  - Action Input 里含换行 → DOTALL 标记易遗漏
  - 每次解析失败就浪费一轮 token
  - 这是 2023 年所有 Agent 框架最头疼的部分
```

### Level 2 (JSON)：结构化输出 —— 你应该用的方式

**做法：** Prompt 要求模型输出 JSON，用 `response_format={"type": "json_object"}` 保证合法性，`json.loads()` 解析。

```
Prompt 教模型：
  "You MUST respond with a valid JSON object:
   {"thought": "<reasoning>", "action": "<tool_name>", "action_input": "<params>"}"

模型输出（JSON）：
  {"thought": "需要查北京温度", "action": "search", "action_input": "北京温度"}

开发者用 json.loads() 解析：
  parsed = json.loads(text)
  action = parsed["action"]

对比：
  - 不需要正则可维护 ← 一行 json.loads() 搞定
  - API 的 response_format 保证输出合法 JSON ← 成功率接近 100%
  - 完全不需要兼容中文冒号、多余空格、换行等边界情况
```

**核心洞察：为什么 Level 2 能工作且更好？**

```
模型不需要 FC 训练就能输出 JSON。
因为 "输出 JSON" 是一个通用能力（模型训练时见过海量 JSON 数据），
不是 FC 专属能力。

FC 训练给模型的额外能力是：
  "识别 tools 参数 + 按 schema 填充 name/arguments 到 tool_calls 字段"
这是特定输出格式的训练，跟会不会输出 JSON 无关。

所以：
  模型支持 FC → 直接用 FC（最省事，连解析都不需要）
  模型不支持 FC → 但支持 JSON → 用 Level 2（json.loads 解析）
  模型连 JSON 都不支持 → 用 Level 1（正则兜底，现在几乎不会遇到）
```

---

## 3. 核心代码结构

```
react_agent.py
├── Tool 类                  → 工具基类：name, description, params_schema, execute()
├── 3 个工具                 → SearchTool, CalculatorTool, DateTimeTool
├── build_text_prompt()      → Level 1 的 System Prompt（教模型输出纯文本格式）
├── build_json_prompt()      → Level 2 的 System Prompt（教模型输出 JSON）
├── parse_text_output()      → 正则提取 Thought/Action/Action Input
├── parse_json_output()      → json.loads() 解析，处理 markdown 包裹
├── ReActAgent               → mode="json"|"text" 切换两种方案
│   ├── _call_llm()          → json 模式加 response_format={"type":"json_object"}
│   ├── _execute_action()    → 根据 action 名字找工具并执行
│   └── run()                → 主循环：调 LLM → 解析 → 执行工具 → 拼回 → 循环
└── main()                   → 入口，--mode json|text 参数切换
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
