"""
D09：纯 Python 实现显式 ReAct Agent
====================================
不用 Function Calling API，实现 ReAct 循环。

支持两种模式：
  Level 1 (TEXT)  — 文本协议，正则解析（教学用，体会"脆弱性"）
  Level 2 (JSON)  — JSON 结构化输出，json.loads() 解析（工程推荐，默认）

用法：
    # 设置 API Key
    export OPENAI_API_KEY="sk-xxx"

    # Level 2（默认，推荐）：JSON 结构化输出
    python react_agent.py

    # Level 1（教学）：纯文本协议
    python react_agent.py --mode text

依赖：pip install openai
"""

import re
import json
import math
import ast
import operator
import argparse
from datetime import datetime
from typing import Optional, Literal

# ============================================================
# 1. 工具系统（两种模式共用）
# ============================================================

class Tool:
    """工具基类"""
    def __init__(self, name: str, description: str, params_schema: str = ""):
        self.name = name
        self.description = description
        self.params_schema = params_schema

    def execute(self, input_str: str) -> str:
        raise NotImplementedError


class SearchTool(Tool):
    """模拟搜索工具——返回预定义的搜索结果"""

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
            description="在互联网上搜索信息。输入搜索关键词，返回相关结果。",
            params_schema='{"query": "搜索关键词，如 北京温度"}',
        )

    def execute(self, input_str: str) -> str:
        query = input_str.strip().lower()
        for key, result in self._INDEX.items():
            if all(word in query for word in key.split()):
                return f"搜索结果: {result}"
        for key, result in self._INDEX.items():
            if any(word in query for word in key.split()):
                return f"搜索结果: {result}"
        return f"搜索结果: 未找到与 '{input_str}' 直接相关的结果。请尝试更具体的关键词。"


class CalculatorTool(Tool):
    """安全计算器——用 AST 解析数学表达式，避免 eval 的安全风险"""

    _OPERATORS = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
    }

    _FUNCTIONS = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "abs": abs, "round": round, "pi": math.pi, "e": math.e,
    }

    def __init__(self):
        super().__init__(
            name="calculator",
            description="安全计算数学表达式。支持 + - * / ** sqrt sin cos log 等。",
            params_schema='{"expression": "数学表达式，如 32 - 28"}',
        )

    def _safe_eval(self, node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.BinOp):
            if type(node.op) not in self._OPERATORS: raise ValueError(f"不允许的运算符: {type(node.op)}")
            return self._OPERATORS[type(node.op)](self._safe_eval(node.left), self._safe_eval(node.right))
        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in self._OPERATORS: raise ValueError(f"不允许的一元运算符: {type(node.op)}")
            return self._OPERATORS[type(node.op)](self._safe_eval(node.operand))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self._FUNCTIONS:
                return self._FUNCTIONS[node.func.id](*[self._safe_eval(a) for a in node.args])
            raise ValueError(f"不允许的函数: {node.func.id if isinstance(node.func, ast.Name) else '?'}")
        if isinstance(node, ast.Name):
            if node.id in self._FUNCTIONS: return self._FUNCTIONS[node.id]
            raise ValueError(f"未定义的变量: {node.id}")
        raise ValueError(f"不支持的表达式类型: {type(node)}")

    def execute(self, input_str: str) -> str:
        try:
            tree = ast.parse(input_str.strip(), mode="eval")
            return f"计算结果: {self._safe_eval(tree.body)}"
        except Exception as e:
            return f"计算错误: {e}"


class DateTimeTool(Tool):
    def __init__(self):
        super().__init__(
            name="datetime",
            description="获取当前日期和时间。",
            params_schema='{"ignored": "不需要参数，传空字符串即可"}',
        )

    def execute(self, input_str: str = "") -> str:
        now = datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}（星期{['一','二','三','四','五','六','日'][now.weekday()]}）"


# ============================================================
# 2. Prompt 构建
# ============================================================

def build_text_prompt(tools: list[Tool]) -> str:
    """Level 1 (TEXT)：教模型按 Thought/Action/Action Input 文本格式输出"""
    tool_list = "\n".join(
        f"  {i+1}. {t.name}: {t.description} 参数: {t.params_schema}"
        for i, t in enumerate(tools)
    )
    return f"""You are a helpful AI assistant using the ReAct framework.

Available tools:
{tool_list}

For each step, output EXACTLY in this format:
Thought: <your reasoning about what to do next>
Action: <tool_name>
Action Input: <the input to the tool>

When ready to answer, output:
Thought: I have all the information needed.
Action: Finish
Action Input: <your complete answer>

Rules:
- Think step by step. One tool per response.
- Do NOT repeat the same action if it returned no useful result.
- Respond in Chinese if the user asks in Chinese."""


def build_json_prompt(tools: list[Tool]) -> str:
    """Level 2 (JSON)：教模型输出结构化 JSON，彻底消灭解析问题"""
    tool_list = "\n".join(
        f'  {i+1}. {t.name}: {t.description} 参数: {t.params_schema}'
        for i, t in enumerate(tools)
    )
    return f"""You are a helpful AI assistant using the ReAct framework.

Available tools:
{tool_list}

You MUST respond with a valid JSON object for EVERY step. Use this exact structure:

If you need to use a tool:
{{"thought": "<your reasoning>", "action": "<tool_name>", "action_input": "<parameters>"}}

If you are ready to give the final answer:
{{"thought": "<final reasoning>", "action": "Finish", "action_input": "<your complete answer to the user>"}}

CRITICAL RULES:
- Your entire response must be a single valid JSON object. Nothing else.
- Do NOT wrap the JSON in markdown code blocks.
- Use double quotes for all keys and string values.
- One tool call per response.
- Respond in Chinese if the user asks in Chinese."""


# ============================================================
# 3. 输出解析
# ============================================================

def parse_text_output(text: str) -> dict:
    """
    Level 1 (TEXT)：正则解析。

    这正是显式 ReAct 最脆弱的一环——LLM 输出稍有偏差就解析失败。
    2023 年之前所有 Agent 框架都在和这个斗智斗勇。
    """
    result = {"thought": None, "action": None, "action_input": None}

    thought_m = re.search(r"Thought[：:]\s*(.+?)(?=\n\s*(?:Action|$)|\Z)", text, re.DOTALL | re.IGNORECASE)
    action_m = re.search(r"Action[：:]\s*(\S[^\n]*)", text, re.IGNORECASE)
    input_m = re.search(r"Action\s*Input[：:]\s*(.+)", text, re.DOTALL | re.IGNORECASE)

    if thought_m: result["thought"] = thought_m.group(1).strip()
    if action_m: result["action"] = action_m.group(1).strip()
    if input_m: result["action_input"] = input_m.group(1).strip()
    return result


def parse_json_output(text: str) -> dict:
    """
    Level 2 (JSON)：json.loads() 解析。

    对比文本解析：
      - 不需要正则可维护
      - 解析成功率高（除非模型输出了非法 JSON）
      - 即使模型包裹了 ```json ... ``` 也能处理
    """
    # 处理模型可能包裹的 markdown 代码块
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        return {
            "thought": data.get("thought"),
            "action": data.get("action"),
            "action_input": data.get("action_input"),
        }
    except json.JSONDecodeError:
        return {"thought": None, "action": None, "action_input": None, "parse_error": True}


# ============================================================
# 4. ReAct 主循环
# ============================================================

ParseMode = Literal["json", "text"]

class ReActAgent:
    """
    显式 ReAct Agent

    mode="json" (默认)：JSON 结构化输出 → json.loads() 解析 → 稳定
    mode="text"：        文本协议 → 正则解析 → 教学用，体会脆弱性
    """

    FINAL_ACTION = "Finish"

    def __init__(self, tools: list[Tool], mode: ParseMode = "json", max_turns: int = 10):
        self.tools = {t.name: t for t in tools}
        self.mode = mode
        self.max_turns = max_turns

        if mode == "json":
            self.system_prompt = build_json_prompt(tools)
            self.parse = parse_json_output
        else:
            self.system_prompt = build_text_prompt(tools)
            self.parse = parse_text_output

        from openai import OpenAI
        self.client = OpenAI()

    def _execute_action(self, action: str, action_input: str) -> str:
        tool = self.tools.get(action)
        if not tool:
            return f"错误: 未知工具 '{action}'。可用工具: {list(self.tools.keys())}"
        try:
            return tool.execute(action_input)
        except Exception as e:
            return f"工具执行错误: {e}"

    def _should_stop(self, history: list[str], threshold: int = 3) -> bool:
        if len(history) < threshold:
            return False
        return len(set(history[-threshold:])) == 1

    def _call_llm(self, messages: list) -> str:
        """调 LLM——json 模式用 response_format 确保输出合法 JSON"""
        kwargs = dict(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
        )
        if self.mode == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def run(self, question: str, verbose: bool = True) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question},
        ]
        action_history = []

        for turn in range(1, self.max_turns + 1):
            if verbose:
                print(f"\n{'='*60}")
                print(f"  Round {turn}  [mode={self.mode}]")
                print(f"{'='*60}")

            # ① 调 LLM（不用 tools 参数）
            llm_output = self._call_llm(messages)

            # ② 解析
            parsed = self.parse(llm_output)

            if verbose:
                print(f"  LLM 原始输出:\n    {llm_output[:300]}")
                print(f"  解析结果:")
                print(f"    Thought:      {parsed.get('thought', '')}")
                print(f"    Action:       {parsed.get('action', '')}")
                print(f"    Action Input: {str(parsed.get('action_input', ''))[:100]}")

            # ③ 终止判断
            if parsed.get("action") and parsed["action"].lower() == self.FINAL_ACTION.lower():
                if verbose:
                    print(f"\n  ✅ Agent 完成，总轮次: {turn}")
                return parsed.get("action_input") or "抱歉，我无法回答这个问题。"

            # ④ 解析失败处理
            if not parsed.get("action") or parsed.get("parse_error"):
                if verbose:
                    print(f"  ⚠️ {'JSON解析失败' if parsed.get('parse_error') else '未解析到 Action'}，提示模型重新输出...")
                messages.append({"role": "assistant", "content": llm_output})
                hint = (
                    "Your response was not valid JSON. Please output ONLY a JSON object: "
                    '{"thought": "...", "action": "...", "action_input": "..."}'
                ) if self.mode == "json" else (
                    "Please use the EXACT format:\nThought: <reasoning>\nAction: <tool_name>\nAction Input: <input>"
                )
                messages.append({"role": "user", "content": hint})
                continue

            # ⑤ 执行工具
            result = self._execute_action(parsed["action"], parsed.get("action_input", ""))
            if verbose:
                print(f"  Observation: {result}")

            # ⑥ 重复检测
            action_history.append(parsed["action"])
            if self._should_stop(action_history):
                if verbose:
                    print("  ⚠️ 检测到重复循环，强制终止")
                return "抱歉，Agent 陷入循环，无法完成该任务。"

            # ⑦ 拼回上下文
            messages.append({"role": "assistant", "content": llm_output})
            messages.append({"role": "user", "content": f"Observation: {result}"})

        return "抱歉，已达到最大推理轮次，任务未完成。"


# ============================================================
# 5. 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="D09 ReAct Agent")
    parser.add_argument("--mode", choices=["json", "text"], default="json",
                        help="json=结构化输出(默认,推荐) | text=文本协议(教学)")
    args = parser.parse_args()

    tools = [SearchTool(), CalculatorTool(), DateTimeTool()]

    print("=" * 60)
    print(f"  D09：显式 ReAct Agent")
    print(f"  模式: {'JSON 结构化输出 (Level 2)' if args.mode == 'json' else '文本协议 (Level 1)'}")
    print(f"  可用工具: {', '.join(t.name for t in tools)}")
    print("=" * 60)
    print()

    if args.mode == "text":
        print("  ⚠️  Level 1 文本模式：依赖正则解析，格式稍有偏差就会失败。")
        print("     这是 2023 年 ReAct 原始论文的做法，用于理解底层机制。")
        print("     工程中请用 --mode json（Level 2）。")

    agent = ReActAgent(tools=tools, mode=args.mode, max_turns=8)

    demo_questions = [
        "北京和东京现在的温差是多少？",
        "马斯克和贝佐斯谁更早创立第一家公司？",
    ]
    print("\n  试试这些示例问题:")
    for i, q in enumerate(demo_questions, 1):
        print(f"    {i}. {q}")

    while True:
        try:
            question = input("\n  你的问题: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见！")
            break

        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        answer = agent.run(question, verbose=True)
        print(f"\n  📝 最终答案: {answer}")


if __name__ == "__main__":
    main()
