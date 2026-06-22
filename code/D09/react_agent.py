"""
D09：纯 Python 实现显式 ReAct Agent
====================================
不用 Function Calling API，用文本协议 Thought/Action/Action Input 实现 ReAct 循环。

用法：
    # 设置 API Key
    export OPENAI_API_KEY="sk-xxx"

    # 运行
    python react_agent.py

    # 交互模式输入问题，输入 quit 退出

依赖：pip install openai
"""

import re
import json
import math
import ast
import operator
from datetime import datetime
from typing import Optional

# ============================================================
# 1. 工具系统
# ============================================================

class Tool:
    """工具基类"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def execute(self, input_str: str) -> str:
        raise NotImplementedError


class SearchTool(Tool):
    """模拟搜索工具——返回预定义的搜索结果"""

    # 模拟的搜索索引
    _INDEX = {
        "北京温度": "北京当前气温 32°C（摄氏度），晴，湿度 45%，体感温度 35°C。",
        "北京天气": "北京今天晴转多云，25°C ~ 33°C，东南风 2-3 级。",
        "东京温度": "东京当前气温 28°C（摄氏度），多云，湿度 65%，体感温度 30°C。",
        "东京天气": "东京今天阵雨，22°C ~ 28°C，南风 3-4 级。",
        "马斯克 zip2": "Zip2 由伊隆·马斯克与金巴尔·马斯克于 1996 年 2 月创立，是一家在线城市指南软件公司。",
        "马斯克第一家公司": "马斯克的第一家公司是 Zip2，创立于 1996 年。",
        "马斯克出生": "伊隆·马斯克出生于 1971 年 6 月 28 日，南非比勒陀利亚。",
        "贝佐斯 amazon": "Amazon（亚马逊）由杰夫·贝佐斯于 1994 年 7 月 5 日创立，最初是在线书店。",
        "贝佐斯第一家公司": "贝佐斯的第一家公司是 Amazon（亚马逊），创立于 1994 年。",
        "贝佐斯出生": "杰夫·贝佐斯出生于 1964 年 1 月 12 日，美国新墨西哥州阿尔伯克基。",
        "诺贝尔奖 2024 物理学": "2024 年诺贝尔物理学奖授予 John Hopfield 和 Geoffrey Hinton，表彰他们在人工神经网络机器学习方面的基础性发现与发明。",
        "python": "Python 由 Guido van Rossum 于 1991 年首次发布，是一种广泛使用的高级编程语言。",
    }

    def __init__(self):
        super().__init__(
            name="search",
            description="search(query: str) - 在互联网上搜索信息。输入搜索关键词，返回相关结果。"
        )

    def execute(self, input_str: str) -> str:
        query = input_str.strip().lower()
        # 模糊匹配
        for key, result in self._INDEX.items():
            if all(word in query for word in key.split()):
                return f"搜索结果: {result}"
        # 部分匹配
        for key, result in self._INDEX.items():
            if any(word in query for word in key.split()):
                return f"搜索结果: {result}"
        return f"搜索结果: 未找到与 '{input_str}' 直接相关的结果。请尝试更具体的关键词。"


class CalculatorTool(Tool):
    """安全计算器——用 AST 解析数学表达式，避免 eval 的安全风险"""

    # 允许的运算符
    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # 允许的函数
    _FUNCTIONS = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "abs": abs,
        "round": round,
        "pi": math.pi,
        "e": math.e,
    }

    def __init__(self):
        super().__init__(
            name="calculator",
            description="calculator(expr: str) - 安全计算数学表达式。支持 + - * / ** sqrt sin cos log。"
        )

    def _safe_eval(self, node):
        """递归求值 AST 节点，只允许安全的操作"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不允许的运算符: {op_type}")
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            return self._OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"不允许的一元运算符: {op_type}")
            return self._OPERATORS[op_type](self._safe_eval(node.operand))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self._FUNCTIONS:
                args = [self._safe_eval(a) for a in node.args]
                return self._FUNCTIONS[node.func.id](*args)
            raise ValueError(f"不允许的函数调用: {node.func.id if isinstance(node.func, ast.Name) else '?'}")
        elif isinstance(node, ast.Name):
            if node.id in self._FUNCTIONS:
                return self._FUNCTIONS[node.id]
            raise ValueError(f"未定义的变量: {node.id}")
        else:
            raise ValueError(f"不支持的表达式类型: {type(node)}")

    def execute(self, input_str: str) -> str:
        try:
            expr = input_str.strip()
            tree = ast.parse(expr, mode="eval")
            result = self._safe_eval(tree.body)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {e}"


class DateTimeTool(Tool):
    """获取当前日期时间"""

    def __init__(self):
        super().__init__(
            name="datetime",
            description="datetime() - 获取当前日期和时间。返回年-月-日 时:分:秒 格式。"
        )

    def execute(self, input_str: str = "") -> str:
        now = datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}（星期{['一','二','三','四','五','六','日'][now.weekday()]}）"


# ============================================================
# 2. Prompt 构建
# ============================================================

def build_system_prompt(tools: list[Tool]) -> str:
    """构建 System Prompt，把工具描述用自然语言写入"""
    tool_descriptions = "\n".join(
        f"  {i+1}. {tool.description}" for i, tool in enumerate(tools)
    )

    return f"""You are a helpful AI assistant that uses the ReAct (Reasoning + Acting) framework to solve problems.

You have access to the following tools:
{tool_descriptions}

Use the following format EXACTLY for each step:

Thought: <your reasoning about what you need to do next>
Action: <tool_name>
Action Input: <the input to the tool>

When you have gathered enough information to answer the user's question, respond with:

Thought: I now have all the information I need to answer.
Action: Finish
Action Input: <your complete answer to the user>

Rules:
- Think step by step before taking any action.
- After each tool call, you will receive an Observation. Use it to decide your next step.
- Do NOT repeat the same action if the tool returns no useful result. Try a different approach.
- Always respond in Chinese if the user asks in Chinese.
- Call exactly ONE tool per response. Do not try to call multiple tools at once.

Let's begin!"""


# ============================================================
# 3. 文本解析（核心——这也是"脆弱"的部分）
# ============================================================

def parse_react_output(text: str) -> dict:
    """
    从 LLM 输出的文本中解析 Thought / Action / Action Input。

    这是显式 ReAct 最脆弱的一环——LLM 输出的格式稍有偏差，正则就匹配失败。
    实际工程中 FC 彻底解决了这个问题。
    """
    # 先尝试严格的格式
    thought_match = re.search(r"Thought:\s*(.+?)(?=\n\s*(?:Action|$)|\Z)", text, re.DOTALL | re.IGNORECASE)
    action_match = re.search(r"Action:\s*(\S[^\n]*)", text, re.IGNORECASE)
    action_input_match = re.search(r"Action Input:\s*(.+)", text, re.DOTALL | re.IGNORECASE)

    thought = thought_match.group(1).strip() if thought_match else None
    action = action_match.group(1).strip() if action_match else None
    action_input = action_input_match.group(1).strip() if action_input_match else None

    # 宽松回退——有些模型会在 Thought 里换行
    if not thought:
        # 尝试匹配 "Thought：xxx"（中文冒号）
        thought_match = re.search(r"Thought[：:]\s*(.+?)(?=\n\s*(?:Action|$)|\Z)", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None

    if not action:
        # 尝试 "Action：xxx" 或 "Finish"
        action_match = re.search(r"Action[：:]\s*(\S[^\n]*)", text)
        action = action_match.group(1).strip() if action_match else None

    return {
        "thought": thought,
        "action": action,
        "action_input": action_input,
    }


# ============================================================
# 4. ReAct 主循环
# ============================================================

class ReActAgent:
    """
    显式 ReAct Agent

    不用 Function Calling API，而是：
    1. 通过 System Prompt 教模型输出 Thought/Action/Action Input 格式
    2. 用正则解析文本拿到 Action 和参数
    3. 执行工具，把结果以 Observation 形式拼回上下文
    4. 循环直到模型输出 Action: Finish
    """

    FINAL_ACTION = "Finish"

    def __init__(self, tools: list[Tool], max_turns: int = 10):
        self.tools = {tool.name: tool for tool in tools}
        self.max_turns = max_turns
        self.system_prompt = build_system_prompt(tools)

        # 延迟导入，避免没装 openai 时启动就报错
        from openai import OpenAI
        self.client = OpenAI()

    def _execute_action(self, action: str, action_input: str) -> str:
        """根据 Action 名字执行对应工具"""
        tool = self.tools.get(action)
        if not tool:
            return f"错误: 未知工具 '{action}'。可用工具: {list(self.tools.keys())}"
        try:
            return tool.execute(action_input)
        except Exception as e:
            return f"工具执行错误: {e}"

    def _should_stop(self, history_actions: list[str], repeat_threshold: int = 3) -> bool:
        """检测是否陷入重复循环"""
        if len(history_actions) < repeat_threshold:
            return False
        recent = history_actions[-repeat_threshold:]
        return len(set(recent)) == 1  # 最近 N 步调用同一工具

    def run(self, question: str, verbose: bool = True) -> str:
        """执行 ReAct 循环，返回最终答案"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question},
        ]

        action_history = []

        for turn in range(1, self.max_turns + 1):
            if verbose:
                print(f"\n{'='*60}")
                print(f"  Round {turn}")
                print(f"{'='*60}")

            # ① 调 LLM（不用 tools 参数！）
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 用小模型即可，显式 ReAct 对推理要求不高
                messages=messages,
                temperature=0.0,
            )
            llm_output = response.choices[0].message.content

            # ② 解析 Thought / Action / Action Input
            parsed = parse_react_output(llm_output)

            if verbose:
                print(f"  LLM 原始输出:\n    {llm_output[:200]}...")
                print(f"  解析结果:")
                print(f"    Thought:      {parsed['thought']}")
                print(f"    Action:       {parsed['action']}")
                print(f"    Action Input: {parsed['action_input'][:100] if parsed['action_input'] else None}")

            # ③ 终止判断
            if parsed["action"] and parsed["action"].lower() == self.FINAL_ACTION.lower():
                if verbose:
                    print(f"\n  ✅ Agent 完成，总轮次: {turn}")
                return parsed["action_input"] or "抱歉，我无法回答这个问题。"

            # ④ 执行工具
            if not parsed["action"]:
                # 解析失败——提示模型重新输出
                if verbose:
                    print("  ⚠️ 解析失败，提示模型重新输出...")
                messages.append({"role": "assistant", "content": llm_output})
                messages.append({
                    "role": "user",
                    "content": "Your last response was not in the correct format. "
                               "Please use EXACTLY:\nThought: <reasoning>\nAction: <tool_name>\nAction Input: <input>"
                })
                continue

            result = self._execute_action(parsed["action"], parsed["action_input"])

            if verbose:
                print(f"  Observation: {result}")

            # ⑤ 重复检测
            action_history.append(parsed["action"])
            if self._should_stop(action_history):
                if verbose:
                    print("  ⚠️ 检测到重复循环，强制终止")
                return "抱歉，Agent 陷入循环，无法完成该任务。请尝试换个问法。"

            # ⑥ 把 LLM 输出和 Observation 追加到上下文
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({"role": "user", "content": f"Observation: {result}"})

        return "抱歉，已达到最大推理轮次，任务未完成。"


# ============================================================
# 5. 入口
# ============================================================

def main():
    # 注册工具
    tools = [
        SearchTool(),
        CalculatorTool(),
        DateTimeTool(),
    ]

    print("=" * 60)
    print("  D09：显式 ReAct Agent（纯文本协议，不用 Function Calling）")
    print("=" * 60)
    print(f"  可用工具: {', '.join(t.name for t in tools)}")
    print("  输入 quit 退出")
    print()

    agent = ReActAgent(tools=tools, max_turns=8)

    # 示例问题
    demo_questions = [
        "北京和东京现在的温差是多少？",
        "马斯克和贝佐斯谁更早创立第一家公司？",
    ]
    print("  试试这些示例问题:")
    for i, q in enumerate(demo_questions, 1):
        print(f"    {i}. {q}")
    print()

    while True:
        try:
            question = input("  你的问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见！")
            break

        if question.lower() in ("quit", "exit", "q"):
            print("  再见！")
            break

        if not question:
            continue

        answer = agent.run(question, verbose=True)
        print(f"\n  📝 最终答案: {answer}\n")


if __name__ == "__main__":
    main()
