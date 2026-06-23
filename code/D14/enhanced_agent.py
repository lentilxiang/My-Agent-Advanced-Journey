"""
D14：增强版 Agent — 第 2 周收官
=================================
Plan-and-Execute + Reflection 组合，6 个工具，包含 Python 执行器和文件 I/O。

用法：
    export OPENAI_API_KEY="sk-xxx"
    python enhanced_agent.py
"""

import json
import ast
import math
import operator
import traceback
import subprocess
import tempfile
import os
from datetime import datetime
from typing import Optional


# ============================================================
# 1. 工具注册（复用 D10 体系，新增 3 个工具）
# ============================================================

class ToolError(Exception):
    def __init__(self, msg, retryable=False):
        self.message = msg
        self.retryable = retryable


class Tool:
    def __init__(self, name, description, params_schema, executor, category="general", confirm=False):
        self.name = name
        self.description = description
        self.params_schema = params_schema
        self.executor = executor
        self.category = category
        self.require_confirmation = confirm

    def validate(self, args: dict) -> dict:
        for key in self.params_schema.get("required", []):
            if key not in args or args[key] in (None, ""):
                raise ToolError(f"缺少必填参数 '{key}'", retryable=True)
        return args

    def execute(self, args: dict) -> str:
        self.validate(args)
        return self.executor(**args)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name, description, params_schema, category="general", confirm=False):
        def dec(fn):
            self._tools[name] = Tool(name, description, params_schema, fn, category, confirm)
            return fn
        return dec

    def get(self, name): return self._tools.get(name)
    def list_all(self): return list(self._tools.values())

    def to_openai(self):
        return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.params_schema}} for t in self._tools.values()]

    def filter_by_query(self, query, top_k=5):
        qw = set(query.lower().split())
        scored = [(t, sum(1 for w in qw if w in (t.name + t.description).lower())) for t in self._tools.values()]
        return [t for t, s in sorted(scored, key=lambda x: -x[1])[:top_k] if s > 0] or self.list_all()[:top_k]


registry = ToolRegistry()

# ── 工具 1: web_search ──
@registry.register("web_search",
    description="搜索互联网信息。适用: 需要最新数据、事实验证。不适用: 已知常识。返回搜索结果摘要。",
    params_schema={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "搜索查询词"}},
        "required": ["query"]
    }, category="info")
def web_search(query: str) -> str:
    mock = {
        "二分查找": "二分查找(Binary Search)在有序数组中查找目标值。时间复杂度O(log n)。关键: left<=right, mid避免溢出用 left+(right-left)//2。",
        "快速排序": "快速排序(Quick Sort)是分治算法。选基准→分区→递归。平均O(n log n)，最坏O(n²)。Python sorted()用Timsort。",
        "decorator": "Python装饰器是修改函数行为的可调用对象。@decorator语法糖。用functools.wraps保留元数据。",
        "xss": "XSS(跨站脚本攻击)通过在网页注入恶意脚本窃取用户数据。防护: HTML实体编码、CSP头、输入过滤。",
        "api": "REST API设计原则: 资源用名词、HTTP动词表示操作、状态码语义化、分页、版本控制。",
    }
    for k, v in mock.items():
        if k in query.lower(): return f"搜索结果: {v}"
    return f"搜索结果: 关于'{query}'，搜索完成（模拟）。"

# ── 工具 2: calculator ──
@registry.register("calculator",
    description="安全数学计算。支持 + - * / ** sqrt sin cos log abs。适用: 数学运算。",
    params_schema={
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "如 '32-28' 或 'sqrt(144)'"}},
        "required": ["expression"]
    }, category="math")
def calculator(expression: str) -> str:
    _ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
            ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}
    _funcs = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "abs": abs, "round": round, "pi": math.pi}

    def _eval(node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.BinOp): return _ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp): return _ops[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else "?"
            if name not in _funcs: raise ValueError(f"不允许: {name}")
            return _funcs[name](*[_eval(a) for a in node.args])
        if isinstance(node, ast.Name) and node.id in _funcs: return _funcs[node.id]
        raise ValueError(f"不支持: {type(node)}")

    return f"计算结果: {_eval(ast.parse(expression.strip(), mode='eval').body)}"

# ── 工具 3: get_datetime ──
@registry.register("get_datetime",
    description="获取当前日期时间。不需要参数。",
    params_schema={"type": "object", "properties": {}, "required": []}, category="info")
def get_datetime() -> str:
    now = datetime.now()
    days = ['一','二','三','四','五','六','日']
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} 星期{days[now.weekday()]}"

# ── 工具 4: python_executor（新增）──
@registry.register("python_executor",
    description="在安全沙箱中执行 Python 代码。适用: 运行代码验证结果、数据处理。不适用: 需要外部API的操作。超时10秒。",
    params_schema={
        "type": "object",
        "properties": {"code": {"type": "string", "description": "要执行的 Python 代码"}},
        "required": ["code"]
    }, category="code")
def python_executor(code: str) -> str:
    # 安全检查
    forbidden = ["os.system", "subprocess", "__import__", "eval(", "exec(", "open(",
                 "shutil", "import os", "import sys", "socket", "requests"]
    code_lower = code.lower()
    for f in forbidden:
        if f in code_lower:
            return f"安全错误: 代码中包含禁止的操作 '{f}'。请使用安全的替代方案。"

    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True, text=True, timeout=10,
            cwd=tempfile.gettempdir(),
        )
        out = (result.stdout + result.stderr).strip()
        return f"执行结果:\n{out}" if out else "执行完成（无输出）"
    except subprocess.TimeoutExpired:
        return "执行超时（>10秒），请检查代码是否有死循环。"
    except Exception as e:
        return f"执行异常: {e}"

# ── 工具 5: file_reader（新增）──
@registry.register("file_reader",
    description="读取本地文件内容。适用: 查看代码、配置、日志文件。",
    params_schema={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "文件路径"}},
        "required": ["path"]
    }, category="io")
def file_reader(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read(3000)
        return f"[{path}] 文件内容 ({len(content)}字符):\n{content}{'...(截断)' if len(content)>=3000 else ''}"
    except FileNotFoundError:
        raise ToolError(f"文件不存在: {path}")
    except PermissionError:
        raise ToolError(f"无权限读取: {path}")

# ── 工具 6: file_writer（新增，需确认）──
@registry.register("file_writer",
    description="写入内容到文件。⚠️破坏性操作，需确认。适用: 保存代码、报告。",
    params_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"}
        },
        "required": ["path", "content"]
    }, category="io", confirm=True)
def file_writer(path: str, content: str) -> str:
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return f"已写入 {len(content)} 字符到 {path}"


# ============================================================
# 2. 增强版 Agent：Plan-and-Execute + Reflection
# ============================================================

class EnhancedAgent:
    """
    Plan-and-Execute（顶层编排）+ Reflection（终端打磨）+ 6 工具
    """

    def __init__(self, max_steps_per_task: int = 4, max_reflection_rounds: int = 2):
        self.max_steps = max_steps_per_task
        self.max_reflect = max_reflection_rounds
        self.executor = ToolExecutor(registry)

    def run(self, task: str, verbose: bool = True) -> str:
        if verbose:
            print("=" * 60)
            print("  🧠 D14 增强版 Agent")
            print(f"  工具: {[t.name for t in registry.list_all()]}")

        # ═══ Phase 1: Plan ═══
        if verbose: print(f"\n{'='*60}\n  📋 Planner — 分解任务\n{'='*60}")

        plan_data = self._plan(task)
        steps = plan_data.get("steps", [{"id": 1, "goal": task, "expected_output": "完成"}])
        if verbose:
            for s in steps:
                print(f"    Step {s['id']}: {s['goal']}")

        # ═══ Phase 2: Execute ═══
        results = {}
        for step in steps[:self.max_steps]:
            if verbose:
                print(f"\n  {'─'*50}\n  ⚡ Step {step['id']}/{len(steps)}: {step['goal']}\n  {'─'*50}")

            result = self._execute_step(step, results, verbose)
            results[step["id"]] = result
            if verbose:
                print(f"  📄 结果: {result[:150]}...")

        # ═══ Phase 3: Synthesize ═══
        draft = self._synthesize(task, results)
        if verbose:
            print(f"\n{'='*60}\n  📝 初稿合成\n{'='*60}")
            print(f"  {draft[:300]}...")

        # ═══ Phase 4: Reflection ═══
        final = self._reflect(task, draft, verbose)

        return final

    def _plan(self, task: str) -> dict:
        from openai import OpenAI
        resp = OpenAI().chat.completions.create(
            model="gpt-4o-mini", temperature=0.0,
            messages=[
                {"role": "system", "content": f"将任务分解为{self.max_steps}个以内的有序步骤。输出JSON: {{\"steps\":[{{\"id\":1,\"goal\":\"...\"}}]}}"},
                {"role": "user", "content": task},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)

    def _execute_step(self, step: dict, context: dict, verbose: bool) -> str:
        from openai import OpenAI
        client = OpenAI()

        ctx_text = "\n".join(f"  Step{k}: {v}" for k, v in context.items()) if context else "无"
        tools = registry.filter_by_query(step["goal"], top_k=4)

        system = f"""你是步骤执行器。完成当前步骤的子目标。
工具: {', '.join(t.name for t in tools)}
输出JSON: {{"thought":"...","action":"tool_name或Finish","action_input":{{...}}}}"""

        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"目标: {step['goal']}\n前面步骤: {ctx_text}\n使用工具或直接完成。"},
        ]

        for t in range(self.max_steps):
            resp = client.chat.completions.create(
                model="gpt-4o-mini", messages=msgs, temperature=0.0,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(resp.choices[0].message.content)

            if parsed.get("action") == "Finish":
                return parsed.get("action_input", "完成")

            result = self.executor.execute(parsed.get("action", ""), parsed.get("action_input", {}))
            if verbose:
                print(f"    🔧 {parsed.get('action','?')}: {result[:100]}")
            msgs += [
                {"role": "assistant", "content": resp.choices[0].message.content},
                {"role": "user", "content": f"Observation: {result}"},
            ]
        return "步骤未完成"

    def _synthesize(self, task: str, results: dict) -> str:
        from openai import OpenAI
        ctx = "\n".join(f"Step{k}: {v}" for k, v in sorted(results.items()))
        resp = OpenAI().chat.completions.create(
            model="gpt-4o-mini", temperature=0.0,
            messages=[
                {"role": "system", "content": "根据各步骤结果生成完整回答。"},
                {"role": "user", "content": f"任务: {task}\n步骤结果:\n{ctx}"},
            ],
        )
        return resp.choices[0].message.content

    def _reflect(self, task: str, draft: str, verbose: bool) -> str:
        from openai import OpenAI
        client = OpenAI()

        for r in range(self.max_reflect + 1):
            if verbose:
                print(f"\n{'='*60}\n  🔍 Reflection 第 {r+1} 轮\n{'='*60}")

            # Critic
            resp = client.chat.completions.create(
                model="gpt-4o-mini", temperature=0.0,
                messages=[
                    {"role": "system", "content": """审查输出质量。输出JSON:
{"passed":bool,"issues":[{"problem":"...","suggestion":"..."}]}"""},
                    {"role": "user", "content": f"任务: {task}\n输出:\n{draft}"},
                ],
                response_format={"type": "json_object"},
            )
            critique = json.loads(resp.choices[0].message.content)

            if verbose:
                print(f"  passed: {critique.get('passed')}")
                for i in critique.get("issues", []):
                    print(f"    ❌ {i.get('problem','')[:100]}")

            if critique.get("passed") or not critique.get("issues"):
                if verbose: print("  ✅ 审查通过")
                return draft

            # Revise
            feedback = "\n".join(f"- {i.get('problem')} → {i.get('suggestion')}" for i in critique.get("issues", []))
            resp2 = client.chat.completions.create(
                model="gpt-4o-mini", temperature=0.0,
                messages=[
                    {"role": "system", "content": f"根据审查意见修改。只改被指出的问题。\n意见:\n{feedback}"},
                    {"role": "user", "content": f"原始:\n{draft}\n\n输出修改后的完整版本:"},
                ],
            )
            draft = resp2.choices[0].message.content
            if verbose: print(f"  🔧 修改后: {draft[:150]}...")

        return draft


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(self, name: str, args: dict) -> str:
        tool = self.registry.get(name)
        if not tool:
            return f"未知工具: {name}。可用: {[t.name for t in self.registry.list_all()]}"
        try:
            if tool.require_confirmation:
                return f"⚠️ 操作 '{name}' 需要人工确认。内容预览:\n{json.dumps(args, ensure_ascii=False, indent=2)}\n请在控制台输入 yes 确认执行:"
            return tool.execute(args)
        except ToolError as e:
            return f"工具错误: {e.message}"
        except Exception as e:
            return f"执行异常: {e}"


# ============================================================
# 3. Demo
# ============================================================

if __name__ == "__main__":
    agent = EnhancedAgent()

    demos = [
        "帮我写一个 Python 二分查找函数（包含注释和测试用例），保存到 search_demo.py",
        "计算 1 到 100 的所有质数之和，并解释计算过程",
    ]

    print("D14: 增强版 Agent (Plan&Execute + Reflection + 6 tools)")
    print("=" * 60)
    for i, t in enumerate(demos, 1):
        print(f"  {i}. {t}")
    print()

    try:
        choice = input("  选一个 (1/2) 或自定义: ").strip()
        task = demos[int(choice)-1] if choice in ("1","2") else (choice or demos[0])
        result = agent.run(task)
        print(f"\n\n  {'='*60}\n  📝 最终输出:\n\n{result}")
    except (EOFError, KeyboardInterrupt):
        print("\n  再见！")
