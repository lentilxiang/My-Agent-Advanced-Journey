"""
D10 工具系统 Demo：用 D10 的工具系统改造 D09 的 ReAct Agent。

展示：
  1. 装饰器注册工具 → 自动生成 schema
  2. 参数校验 → 调用前拦截错误参数
  3. 多工具筛选 → filter_by_query 减少候选
  4. 错误处理 → ToolError 分类 + 重试
  5. 确认机制 → require_confirmation

用法：
    export OPENAI_API_KEY="sk-xxx"
    python demo.py
"""

from tool_system import ToolRegistry, ToolExecutor, ToolError, ErrorCategory, with_retry

# ============================================================
# 1. 用装饰器注册工具（自动生成 schema）
# ============================================================

registry = ToolRegistry()


@registry.register(category="info")
def web_search(query: str) -> str:
    """在互联网上搜索实时信息。
    适用场景：需要最新数据（新闻、价格、天气、事件）。
    不适用场景：已知常识、数学计算、代码生成。
    返回: 搜索结果摘要。

    :param query: 搜索查询词，应具体且信息丰富。如 '2024诺贝尔物理学奖' 而非 '诺贝尔奖'
    :returns: 匹配的搜索结果文本
    """
    # 模拟搜索
    mock_results = {
        "北京温度": "北京当前气温 32°C，晴，湿度 45%。",
        "北京天气": "北京今天晴转多云，25°C ~ 33°C。",
        "东京温度": "东京当前气温 28°C，多云。",
        "东京天气": "东京今天阵雨，22°C ~ 28°C。",
        "马斯克": "伊隆·马斯克，Zip2 创立于 1996 年，出生于 1971 年。",
        "贝佐斯": "杰夫·贝佐斯，Amazon 创立于 1994 年，出生于 1964 年。",
        "诺贝尔奖": "2024 年诺贝尔物理学奖授予 John Hopfield 和 Geoffrey Hinton。",
    }
    for key, result in mock_results.items():
        if key in query:
            return f"搜索结果: {result}"
    return f"搜索结果: 关于 '{query}'，未找到直接匹配。请尝试更具体的关键词。"


@registry.register(category="math")
def calculator(expression: str) -> str:
    """安全计算数学表达式。支持 + - * / ** sqrt sin cos log 等运算。
    适用场景：数学计算、单位换算、统计。
    不适用场景：需要搜索实时信息。

    :param expression: 数学表达式，如 '32 - 28' 或 'sqrt(144)'
    :returns: 计算结果
    """
    import ast
    import math
    import operator as op

    _safe_ops = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        ast.Div: op.truediv, ast.Pow: op.pow,
        ast.USub: op.neg, ast.UAdd: op.pos,
    }
    _safe_funcs = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "abs": abs,
        "round": round, "pi": math.pi, "e": math.e,
    }

    def _eval(node):
        if isinstance(node, ast.Constant): return node.value
        if isinstance(node, ast.BinOp):
            if type(node.op) not in _safe_ops:
                raise ToolError(f"不允许的运算符: {type(node.op).__name__}", ErrorCategory.PARAM)
            return _safe_ops[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            return _safe_ops[type(node.op)](_eval(node.operand))
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else "?"
            if name not in _safe_funcs:
                raise ToolError(f"不允许的函数: {name}", ErrorCategory.PARAM)
            return _safe_funcs[name](*[_eval(a) for a in node.args])
        if isinstance(node, ast.Name):
            if node.id in _safe_funcs: return _safe_funcs[node.id]
            raise ToolError(f"未定义的变量: {node.id}", ErrorCategory.PARAM)
        raise ToolError(f"不支持的表达式", ErrorCategory.PARAM)

    try:
        tree = ast.parse(expression.strip(), mode="eval")
        return f"计算结果: {_eval(tree.body)}"
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"表达式错误: {e}", ErrorCategory.PARAM)


@registry.register(category="info")
def get_datetime(ignored: str = "") -> str:
    """获取当前日期和时间。不需要参数。

    :param ignored: 不需要传值，传空字符串即可
    :returns: 当前日期时间字符串
    """
    from datetime import datetime
    now = datetime.now()
    days = ['一', '二', '三', '四', '五', '六', '日']
    return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}（星期{days[now.weekday()]}）"


@registry.register(category="action", require_confirmation=True)
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件。破坏性操作，需要人工确认。
    适用场景：用户明确要求发送邮件。

    :param to: 收件人邮箱地址，如 user@example.com
    :param subject: 邮件主题
    :param body: 邮件正文内容
    :returns: 发送结果
    """
    # 模拟发送（生产环境调 SMTP API）
    return f"邮件已发送至 {to}，主题: {subject}"


@registry.register(category="io")
def read_file(filepath: str) -> str:
    """读取本地文件内容。
    适用场景：用户要求查看文件内容。
    不适用场景：搜索互联网信息。

    :param filepath: 文件路径，如 /path/to/file.txt
    :returns: 文件内容
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read(500)
        return f"文件内容（前 500 字符）:\n{content}"
    except FileNotFoundError:
        raise ToolError(f"文件不存在: {filepath}", ErrorCategory.BUSINESS)
    except PermissionError:
        raise ToolError(f"没有权限读取文件: {filepath}", ErrorCategory.BUSINESS)


# ============================================================
# 2. 展示工具系统的核心能力
# ============================================================

def demo_tool_system():
    print("=" * 60)
    print("  D10 工具系统 Demo")
    print("=" * 60)

    # ① 查看所有注册的工具
    print("\n  ① 注册表概览:")
    for name, tool in registry._tools.items():
        params = list(tool.parameters.get("properties", {}).keys())
        confirm = " ⚠️需确认" if tool.require_confirmation else ""
        print(f"    [{tool.category}] {name}({', '.join(params)}){confirm}")
    print(f"    共 {registry.tool_count} 个工具，{len(registry.categories)} 个分类")

    # ② 自动生成的 OpenAI 格式
    print("\n  ② 自动生成的 OpenAI tools 格式:")
    openai_tools = registry.to_openai_format()
    for t in openai_tools:
        f = t["function"]
        desc = f["description"][:80]
        required = f["parameters"].get("required", [])
        print(f"    name={f['name']}, required={required}")
        print(f"    description={desc}...")

    # ③ 多工具筛选
    print("\n  ③ 多工具筛选:")
    queries = ["查一下天气", "算个数学题", "发邮件", "当前时间"]
    for q in queries:
        filtered = registry.filter_by_query(q, top_k=3)
        print(f"    '{q}' → {[t.name for t in filtered]}")

    # ④ 参数校验演示
    executor = ToolExecutor(registry)
    print("\n  ④ 参数校验:")
    # 正确参数
    result = executor.execute("calculator", {"expression": "32 - 28"})
    print(f"    ✅ 正确参数: {result}")
    # 缺少必填参数
    result = executor.execute("calculator", {})
    print(f"    ❌ 缺参数: {result}")
    # 错误类型
    result = executor.execute("calculator", {"expression": ""})
    print(f"    ❌ 空值: {result}")

    # ⑤ 确认机制
    print("\n  ⑤ 确认机制:")
    print(f"    send_email 需要确认: {executor.needs_confirmation('send_email')}")
    print(f"    web_search 需要确认: {executor.needs_confirmation('web_search')}")

    # ⑥ 分类路由
    print("\n  ⑥ 分类路由:")
    for cat in registry.categories:
        tools = registry.list_by_category(cat)
        print(f"    [{cat}] → {[t.name for t in tools]}")

    print("\n" + "=" * 60)
    print("  ✅ 工具系统就绪，可接入任意 Agent 循环")
    print("=" * 60)


# ============================================================
# 3. 接入 ReAct Agent（展示工具系统如何被 Agent 使用）
# ============================================================

def react_agent_with_tool_system(question: str):
    """用 D10 工具系统驱动的 ReAct Agent"""
    from openai import OpenAI
    client = OpenAI()
    executor = ToolExecutor(registry)

    # 用工具系统的导出能力生成 prompt
    tools_desc = "\n".join(
        f"  {t.name}: {t.description[:100]}"
        for t in registry.list_all()
    )

    system_prompt = f"""You are a helpful assistant. Use the ReAct framework.

Available tools:
{tools_desc}

Respond with JSON: {{"thought": "...", "action": "<tool_name>", "action_input": {{...}}}}
Or to finish: {{"thought": "...", "action": "Finish", "action_input": "<answer>"}}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    for turn in range(1, 8):
        print(f"\n  --- Round {turn} ---")

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        import json
        parsed = json.loads(resp.choices[0].message.content)

        print(f"  Thought: {parsed.get('thought', '')[:100]}")
        print(f"  Action: {parsed.get('action', '')}")

        if parsed.get("action") == "Finish":
            print(f"\n  ✅ 最终答案: {parsed.get('action_input', '')}")
            return

        # 用 D10 的 ToolExecutor 执行（含校验 + 错误处理）
        result = executor.execute(
            parsed.get("action", ""),
            parsed.get("action_input", {}),
        )
        print(f"  Observation: {result}")

        messages.append({"role": "assistant", "content": resp.choices[0].message.content})
        messages.append({"role": "user", "content": f"Observation: {result}"})


if __name__ == "__main__":
    demo_tool_system()

    print("\n\n  试试用这个工具系统跑一个 ReAct Agent:\n")
    try:
        react_agent_with_tool_system("北京和东京现在的温差是多少？")
    except Exception as e:
        print(f"  运行 Agent 需要设置 OPENAI_API_KEY: {e}")
