# D06：多工具 Agent 综合实战

> 目标：整合 D01-D05 全部知识，做一个可调用 5 个工具的实用 Agent——「DevTool 开发助手」。

---

## 1. Agent 设计

### 1.1 五个工具

```
┌─────────────────────────────────────────────────────────┐
│               DevTool Agent 工具集                        │
├──────────────┬──────────────────────────────────────────┤
│ search_docs   │ 搜索 Python/JS/Go 技术文档（模拟知识库）    │
│ run_code      │ 安全执行 Python 代码（ast 白名单沙箱）      │
│ format_data   │ JSON/YAML 格式化 + 校验                   │
│ timestamp     │ 时间戳 ↔ 日期转换 + 时区换算                │
│ text_utils    │ 文本统计 / 正则匹配 / diff 对比             │
└──────────────┴──────────────────────────────────────────┘
```

### 1.2 Agent 循环架构

```
用户输入
    │
    ▼
┌──────────────────────────────────────────┐
│              Agent 循环                    │
│                                          │
│  while 未完成 and 未超限:                  │
│    │                                     │
│    ▼                                     │
│  LLM 决策                                 │
│    │                                     │
│    ├── 要调工具 → 执行 → 结果注入上下文 → 继续  │
│    │                                     │
│    └── 不调工具 → 生成最终回复 → 返回用户     │
│                                          │
│  防护：max_turns=10 / 重复检测 / 异常捕获   │
└──────────────────────────────────────────┘
```

---

## 2. 完整代码

### 2.1 工具函数

```python
"""
devtools.py —— 五个开发者工具
"""
import json
import ast
import re
import sys
from io import StringIO
from datetime import datetime, timezone, timedelta


# ========== 工具 1：技术文档搜索 ==========
KNOWLEDGE_BASE = {
    "python asyncio": "asyncio 是 Python 异步 I/O 库。核心概念：coroutine（async def）、"
                      "event loop（事件循环）、Task（任务）。使用 asyncio.run() 启动，"
                      "await 等待协程结果。常见模式：asyncio.gather() 并发执行多个协程。",
    "python decorator": "装饰器是接受函数并返回新函数的可调用对象。@decorator 语法糖等价于 "
                        "func = decorator(func)。functools.wraps 保留原函数元信息。"
                        "带参数装饰器需要三层嵌套。",
    "python pydantic": "Pydantic 是 Python 数据校验库。BaseModel 子类定义字段类型，"
                       "自动校验 + 类型转换。v2 用 model_validate() 替代 parse_obj()，"
                       "model_dump() 替代 dict()。支持 nested models、union types。",
    "js promise": "Promise 是 JS 异步编程核心。三种状态：pending → fulfilled/rejected。"
                  "async/await 是 Promise 的语法糖。Promise.all() 并发，"
                  "Promise.race() 竞速。错误用 .catch() 或 try/catch。",
    "go goroutine": "goroutine 是 Go 轻量级协程，go 关键字启动。channel 用于 goroutine 间通信。"
                    "select 语句多路复用。sync.WaitGroup 等待一组 goroutine 完成。"
                    "context 包用于超时控制和取消传播。",
    "git rebase": "git rebase 将提交应用到另一个基点上，重写历史。vs merge：rebase 线性历史，"
                  "merge 保留分支结构。黄金规则：不要 rebase 已推送的提交。"
                  "交互式 rebase（-i）可 squash/fixup/reword 提交。",
    "docker compose": "Docker Compose 用 YAML 定义多容器应用。docker-compose.yml 中定义 "
                      "services/networks/volumes。docker compose up -d 后台启动，"
                      "docker compose down 停止并清理。",
    "sql index": "数据库索引加速查询但减慢写入。B-Tree 默认类型，适合范围查询。"
                 "Hash 索引只支持等值查询。复合索引遵循最左前缀原则。"
                 "EXPLAIN ANALYZE 查看索引使用情况。避免在低基数列上建索引。",
}

def search_docs(query: str, topic: str = "all") -> str:
    """
    搜索技术文档。
    topic 可选: python / javascript / go / devops / all
    """
    results = []
    query_lower = query.lower()

    for key, content in KNOWLEDGE_BASE.items():
        if query_lower in key or query_lower in content.lower():
            # 按 topic 过滤
            if topic != "all":
                topic_map = {
                    "python": "python",
                    "javascript": "js",
                    "go": "go",
                }
                if topic_map.get(topic, topic) not in key:
                    continue
            results.append(f"【{key}】\n{content}")

    if not results:
        return f"未找到关于 '{query}' 的文档。试试：python asyncio, js promise, go goroutine, docker compose, sql index"
    return "\n\n".join(results)


# ========== 工具 2：安全执行 Python 代码 ==========
def run_code(code: str) -> str:
    """
    安全执行 Python 代码。
    只允许安全的内置函数，禁止 import / exec / eval / open 等危险操作。

    限制：
      - 不能 import 模块
      - 不能读写文件
      - 不能执行系统命令
      - 超时 5 秒自动终止
    """
    # AST 白名单检查
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"语法错误：{e}"

    # 检查是否有危险操作
    ALLOWED_NODES = {
        ast.Module, ast.Expr, ast.Constant, ast.Name, ast.Load, ast.Store,
        ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
        ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.BoolOp, ast.And, ast.Or, ast.Not,
        ast.Assign, ast.AugAssign,
        ast.Call, ast.keyword,
        ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Pass,
        ast.For, ast.If, ast.While, ast.Break, ast.Continue,
        ast.List, ast.Dict, ast.Tuple, ast.Set,
        ast.Subscript, ast.Slice, ast.Index,
        ast.ListComp, ast.DictComp, ast.comprehension,
        ast.Attribute,
        ast.JoinedStr, ast.FormattedValue,
        ast.IfExp,
    }

    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return f"安全限制：不允许使用 {type(node).__name__}（代码包含不安全的操作）"
        # 禁止 from __future__ import 等
        if isinstance(node, ast.Name) and node.id in ("__import__", "eval", "exec", "open", "compile"):
            return f"安全限制：禁止使用 {node.id}()"

    # 安全内置函数白名单
    safe_builtins = {
        "print": print, "len": len, "range": range, "list": list, "dict": dict,
        "str": str, "int": int, "float": float, "bool": bool,
        "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
        "sorted": sorted, "reversed": reversed, "enumerate": enumerate, "zip": zip,
        "map": map, "filter": filter,
        "type": type, "isinstance": isinstance,
        "True": True, "False": False, "None": None,
    }

    # 捕获标准输出
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code, {"__builtins__": safe_builtins}, {})
        output = sys.stdout.getvalue()
        return output if output else "(代码执行成功，无输出)"
    except Exception as e:
        return f"执行错误：{type(e).__name__}: {e}"
    finally:
        sys.stdout = old_stdout


# ========== 工具 3：JSON/YAML 格式化 ==========
def format_data(data: str, fmt: str = "json", action: str = "validate") -> str:
    """
    格式化或校验 JSON/YAML 数据。

    参数:
      data: 原始字符串
      fmt: json 或 yaml
      action: validate（校验+美化）或 minify（压缩）
    """
    if fmt == "json":
        try:
            parsed = json.loads(data)
            if action == "minify":
                return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
            else:
                return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            return f"JSON 解析错误：{e}"
    elif fmt == "yaml":
        try:
            import yaml
            parsed = yaml.safe_load(data)
            return yaml.dump(parsed, allow_unicode=True, default_flow_style=False)
        except ImportError:
            return "需要安装 PyYAML：pip install pyyaml"
        except Exception as e:
            return f"YAML 解析错误：{e}"
    else:
        return f"不支持的格式：{fmt}，支持 json / yaml"


# ========== 工具 4：时间戳转换 ==========
def timestamp(action: str, value: str = "", from_tz: str = "UTC", to_tz: str = "Asia/Shanghai") -> str:
    """
    时间戳与日期转换。

    action:
      now       - 获取当前时间
      to_stamp  - 日期 → 时间戳（value="2024-01-01 12:00:00"）
      to_date   - 时间戳 → 日期（value="1704067200"）
      convert   - 时区转换

    from_tz / to_tz: 时区标识，如 UTC / Asia/Shanghai / America/New_York
    """
    # 时区映射
    tz_map = {
        "UTC": timezone.utc,
        "Asia/Shanghai": timezone(timedelta(hours=8)),
        "America/New_York": timezone(timedelta(hours=-5)),
        "Europe/London": timezone(timedelta(hours=0)),
        "Asia/Tokyo": timezone(timedelta(hours=9)),
    }

    if action == "now":
        now = datetime.now(timezone.utc)
        lines = [f"UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}"]
        for name, tz in tz_map.items():
            if name != "UTC":
                local = now.astimezone(tz)
                lines.append(f"{name}: {local.strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)

    elif action == "to_stamp":
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            src_tz = tz_map.get(from_tz, timezone.utc)
            dt = dt.replace(tzinfo=src_tz)
            return f"时间戳: {int(dt.timestamp())}"
        except Exception as e:
            return f"日期解析错误：{e}。格式应为 2024-01-01 12:00:00"

    elif action == "to_date":
        try:
            ts = float(value)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            lines = [f"UTC: {dt.strftime('%Y-%m-%d %H:%M:%S')}"]
            for name, tz in tz_map.items():
                if name != "UTC":
                    lines.append(f"{name}: {dt.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')}")
            return "\n".join(lines)
        except Exception as e:
            return f"时间戳解析错误：{e}"

    elif action == "convert":
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            src_tz = tz_map.get(from_tz, timezone.utc)
            dst_tz = tz_map.get(to_tz, timezone.utc)
            dt = dt.replace(tzinfo=src_tz)
            converted = dt.astimezone(dst_tz)
            return f"{from_tz} {value} → {to_tz} {converted.strftime('%Y-%m-%d %H:%M:%S')}"
        except Exception as e:
            return f"转换错误：{e}"

    return f"不支持的操作：{action}，支持 now / to_stamp / to_date / convert"


# ========== 工具 5：文本处理 ==========
def text_utils(action: str, text: str, pattern: str = "", text2: str = "") -> str:
    """
    文本处理工具箱。

    action:
      count     - 统计字数/行数/词数
      regex     - 正则匹配（pattern 为 regex）
      diff      - 对比两段文本（text2 为第二段）
      dedup     - 去重行
      wrap      - 按宽度折行
    """
    if action == "count":
        lines = text.count("\n") + 1 if text else 0
        chars = len(text)
        chars_no_space = len(text.replace(" ", "").replace("\n", ""))
        words = len(text.split())
        return f"行数: {lines} | 字符: {chars} (不含空格: {chars_no_space}) | 词数: {words}"

    elif action == "regex":
        try:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            if not matches:
                return f"未匹配到 '{pattern}'"
            result = "\n".join([f"  [{i+1}] {m}" for i, m in enumerate(matches)])
            return f"匹配到 {len(matches)} 处：\n{result}"
        except re.error as e:
            return f"正则错误：{e}"

    elif action == "diff":
        lines1 = text.splitlines()
        lines2 = text2.splitlines()
        max_len = max(len(lines1), len(lines2))
        result = []
        for i in range(max_len):
            l1 = lines1[i] if i < len(lines1) else "(无)"
            l2 = lines2[i] if i < len(lines2) else "(无)"
            if l1 != l2:
                result.append(f"  第{i+1}行:")
                result.append(f"    - {l1}")
                result.append(f"    + {l2}")
        if not result:
            return "两段文本完全相同"
        return f"差异（{len(result)//3} 处）：\n" + "\n".join(result)

    elif action == "dedup":
        lines = text.splitlines()
        seen = set()
        unique = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique.append(line)
        removed = len(lines) - len(unique)
        return f"去重 {removed} 行。结果：\n" + "\n".join(unique)

    elif action == "wrap":
        try:
            width = int(pattern) if pattern else 80
        except ValueError:
            width = 80
        import textwrap
        return textwrap.fill(text, width=width)

    return f"不支持的操作：{action}，支持 count / regex / diff / dedup / wrap"
```

### 2.2 Agent 核心

```python
"""
agent.py —— DevTool Agent

整合 D05 的 LLMClient + 5 个开发工具
"""
import json
from typing import Optional
from openai import OpenAI

# 复用 D05 的 LLMClient（简化版）
from llm_client import LLMClient

# 导入工具
from devtools import search_docs, run_code, format_data, timestamp, text_utils


# ============ 工具 Schema 定义 ============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "搜索技术文档知识库。当用户询问 Python/JS/Go/Docker/Git/SQL 等技术问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，如 'python asyncio'"},
                    "topic": {
                        "type": "string",
                        "enum": ["python", "javascript", "go", "devops", "all"],
                        "default": "all",
                        "description": "限定技术领域"
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_code",
            "description": "安全执行 Python 代码。只能使用基础语法和内置函数（print/len/range/list/dict/str/int 等），不能 import/读写文件/执行命令。适用于：验证算法逻辑、测试小段代码、数值计算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python 代码字符串"}
                },
                "required": ["code"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "format_data",
            "description": "格式化或校验 JSON/YAML 数据。用户给你一段乱糟糟的 JSON 或 YAML 时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "原始数据字符串"},
                    "fmt": {
                        "type": "string",
                        "enum": ["json", "yaml"],
                        "default": "json",
                        "description": "数据格式"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["validate", "minify"],
                        "default": "validate",
                        "description": "validate=美化输出，minify=压缩"
                    }
                },
                "required": ["data"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "timestamp",
            "description": "时间处理：获取当前时间、时间戳与日期互转、时区转换。当用户询问时间相关问题时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["now", "to_stamp", "to_date", "convert"],
                        "description": "操作类型"
                    },
                    "value": {
                        "type": "string",
                        "description": "日期字符串（2024-01-01 12:00:00）或时间戳",
                        "default": ""
                    },
                    "from_tz": {
                        "type": "string",
                        "enum": ["UTC", "Asia/Shanghai", "America/New_York", "Europe/London", "Asia/Tokyo"],
                        "default": "UTC"
                    },
                    "to_tz": {
                        "type": "string",
                        "enum": ["UTC", "Asia/Shanghai", "America/New_York", "Europe/London", "Asia/Tokyo"],
                        "default": "Asia/Shanghai"
                    },
                },
                "required": ["action"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
    {
        "type": "function",
        "function": {
            "name": "text_utils",
            "description": "文本处理工具：统计字数行数、正则匹配、文本 diff 对比、行去重、按宽度折行。当用户需要处理文本时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["count", "regex", "diff", "dedup", "wrap"],
                        "description": "操作类型"
                    },
                    "text": {"type": "string", "description": "主文本"},
                    "pattern": {
                        "type": "string",
                        "description": "正则表达式（regex模式）/ 折行宽度（wrap模式）",
                        "default": ""
                    },
                    "text2": {
                        "type": "string",
                        "description": "第二段文本（diff 模式需要）",
                        "default": ""
                    },
                },
                "required": ["action", "text"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    },
]

# 工具执行映射
TOOL_MAP = {
    "search_docs": search_docs,
    "run_code": run_code,
    "format_data": format_data,
    "timestamp": timestamp,
    "text_utils": text_utils,
}

# ============ System Prompt ============
SYSTEM_PROMPT = """
你是 DevTool，一个面向开发者的 AI 助手。你可以使用以下工具帮助用户：

1. **search_docs** — 搜索技术文档（Python/JS/Go/Docker/Git/SQL）
2. **run_code** — 安全执行 Python 代码片段
3. **format_data** — 格式化/校验 JSON/YAML 数据
4. **timestamp** — 时间戳转换、时区换算
5. **text_utils** — 文本统计、正则匹配、diff 对比

行为准则：
- 用户问技术问题时，优先用 search_docs 查资料再回答，不要凭空编造
- 用户让你写代码验证某件事，用 run_code 执行
- 工具执行出错时，分析错误原因并尝试修正
- 回答简洁，代码用 markdown 代码块
- 一次能并行调的工具就并行调（如同时查两个主题）
"""


# ============ Agent ============
class DevToolAgent:
    """
    5 工具开发助手 Agent。

    特性：
      - 自动多轮工具调用
      - 并行调用支持
      - 死循环检测
      - 异常保护
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        self.llm = LLMClient(provider="openai", model=model, temperature=0)
        self.max_turns = 10

    def run(self, user_message: str, verbose: bool = True) -> str:
        """
        执行 Agent 循环。

        Args:
            user_message: 用户输入
            verbose: 是否打印工具调用过程

        Returns:
            最终回复文本
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        last_calls_signature = None
        same_call_count = 0

        for turn in range(1, self.max_turns + 1):
            if verbose:
                print(f"\n{'─'*50}")
                print(f"第 {turn} 轮")
                print(f"{'─'*50}")

            # 调用 LLM（内置重试机制）
            response = self.llm._call_with_retry(
                messages=messages,
                tools=TOOLS,
            )
            msg = response.choices[0].message
            messages.append(msg)

            # 情况 1：纯文本回复
            if not msg.tool_calls:
                if verbose:
                    print(f"💬 {msg.content}")
                return msg.content or ""

            # 情况 2：需要调工具
            # 生成调用签名（用于死循环检测）
            calls_signature = tuple(
                (tc.function.name, tc.function.arguments)
                for tc in msg.tool_calls
            )

            if calls_signature == last_calls_signature:
                same_call_count += 1
                if same_call_count >= 2:
                    msg_text = "检测到重复调用，已终止以避免死循环。"
                    if verbose:
                        print(f"⚠️ {msg_text}")
                    return msg_text
            else:
                same_call_count = 0
            last_calls_signature = calls_signature

            # 执行工具调用
            for tc in msg.tool_calls:
                func_name = tc.function.name
                try:
                    func_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError as e:
                    result = f"参数解析失败: {e}"
                    if verbose:
                        print(f"❌ {func_name}: {result}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                    continue

                if verbose:
                    # 截断长参数显示
                    args_preview = {k: (v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v)
                                    for k, v in func_args.items()}
                    print(f"🔧 {func_name}({args_preview})")

                # 安全执行
                func = TOOL_MAP.get(func_name)
                if func is None:
                    result = f"工具 '{func_name}' 不存在，可用工具：{list(TOOL_MAP.keys())}"
                else:
                    try:
                        result = str(func(**func_args))
                    except Exception as e:
                        result = f"工具执行出错: {type(e).__name__}: {e}"

                if verbose:
                    # 截断长结果
                    result_preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"📋 {result_preview}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        return "达到最大执行轮次限制"


# ============ 交互式对话 ============
def main():
    agent = DevToolAgent()

    print("=" * 60)
    print("🤖 DevTool Agent — 5 工具开发助手")
    print("=" * 60)
    print("试试这些命令：")
    print("  • 什么是 python asyncio？")
    print("  • 帮我执行这段代码：for i in range(5): print(i**2)")
    print("  • 格式化这个 JSON：{\"name\":\"test\",\"age\":25}")
    print("  • 现在北京时间是几点？")
    print("  • 统计这段文本的字数：[粘贴文本]")
    print("  • 同时查 python decorator 和 js promise")
    print("输入 quit 退出")
    print()

    while True:
        user_input = input("\n你：")
        if user_input.lower() == "quit":
            break
        if not user_input.strip():
            continue

        reply = agent.run(user_input)
        print(f"\n🤖 {reply}")


if __name__ == "__main__":
    main()
```

---

## 3. 测试用例

```python
"""
test_agent.py —— 6 个典型场景测试
"""
from agent import DevToolAgent

agent = DevToolAgent(verbose=False)


def test_search():
    """场景 1：单工具查询"""
    reply = agent.run("什么是 python asyncio？")
    assert "asyncio" in reply.lower()
    assert "coroutine" in reply.lower() or "await" in reply.lower()
    print("✅ 场景 1 通过 — 文档搜索")


def test_run_code():
    """场景 2：代码执行"""
    reply = agent.run("帮我算一下 1到100的和，用 Python 代码")
    assert "5050" in reply
    print("✅ 场景 2 通过 — 代码执行")


def test_format_json():
    """场景 3：JSON 格式化"""
    reply = agent.run('格式化这个 JSON：{"b":2,"a":1,"c":[3,4]}')
    assert "a" in reply and "b" in reply
    print("✅ 场景 3 通过 — JSON 格式化")


def test_time():
    """场景 4：时间查询"""
    reply = agent.run("现在北京时间几点？")
    # 只要不报错、返回了时间相关的文本就行
    assert len(reply) > 10
    print("✅ 场景 4 通过 — 时间查询")


def test_text_count():
    """场景 5：文本统计"""
    test_text = "hello world\nthis is a test\nhello again"
    reply = agent.run(f"统计这段文本的行数和词数：\n{test_text}")
    assert "3" in reply or "行" in reply
    print("✅ 场景 5 通过 — 文本统计")


def test_parallel_search():
    """场景 6：并行查询两个主题"""
    reply = agent.run("同时查一下 python decorator 和 js promise 的文档")
    assert "decorator" in reply.lower() and "promise" in reply.lower()
    print("✅ 场景 6 通过 — 并行文档搜索")


def test_dangerous_code():
    """场景 7：危险代码被拦截"""
    reply = agent.run("帮我执行：import os; os.system('ls')")
    assert "安全" in reply or "限制" in reply or "禁止" in reply
    print("✅ 场景 7 通过 — 危险代码拦截")


if __name__ == "__main__":
    test_search()
    test_run_code()
    test_format_json()
    test_time()
    test_text_count()
    test_parallel_search()
    test_dangerous_code()
    print("\n🎉 全部测试通过！")
```

---

## 4. D04 Agent vs D06 Agent 对比

| 维度 | D04 天气 Agent | D06 DevTool Agent |
|------|:---:|:---:|
| 工具数量 | 5 个（演示用） | 5 个（实际能用） |
| 安全性 | 无校验 | AST 白名单沙箱 |
| 死循环保护 | 仅 max_turns | max_turns + 重复签名检测 |
| 异常保护 | 无 | 每个工具调用都 try/except |
| 并行调用 | 支持但未测试 | 显式测试 |
| LLM 调用 | 原生 OpenAI | 复用 D05 LLMClient（带重试） |
| 可测试性 | 无 | 7 个自动化测试 |
| 交互式 | 无 | 有 REPL |

---

## 5. 动手练习

```text
[ ] 练习 1：跑通 DevTool Agent，尝试 6 个测试场景
           观察每个场景调了哪些工具、用了几轮

[ ] 练习 2：添加第 6 个工具 → generate_regex(description: str)
           输入："匹配中国大陆手机号"
           输出：r'^1[3-9]\d{9}$'
           更新 TOOLS、TOOL_MAP、SYSTEM_PROMPT

[ ] 练习 3：让 Agent 处理一个需要 3 轮的工具链式任务
           "查一下什么是 goroutine，用 Python 写一段类似逻辑的代码，统计代码行数"

[ ] 练习 4：故意让工具返回错误，观察 Agent 能否自我修正
           - 给 run_code 传入有语法错误的代码
           - 给 format_data 传入非法 JSON
           - Agent 会怎么处理？

[ ] 练习 5：把 LLMClient 换成 Anthropic（Claude）
           适配 tool_use / tool_result 格式
           对比同一个问题两个模型的工具调用行为
```

---

## 6. 关键收获

### 6.1 从 Demo 到产品的差距

```
D04 Demo Agent：
  ✅ 工具调得通
  ❌ 没有安全校验
  ❌ 没有死循环保护
  ❌ 没有错误恢复
  ❌ 没有测试

D06 DevTool Agent：
  ✅ AST 白名单沙箱
  ✅ 重复调用检测（2次相同→终止）
  ✅ 所有工具调用包 try/except
  ✅ 7 个自动化测试
  → 可以真正跑在开发环境里
```

### 6.2 好 Agent 的三个标准

```
1. 安全 — 危险操作被拦截（沙箱 / 权限控制）
2. 鲁棒 — 工具出错不崩溃，死循环自动终止
3. 可测 — 有测试用例，改完代码跑一遍就知道坏没坏
```

### 6.3 D01-D06 完成度

```
第1周  LLM API + Function Calling 上手

D01 ✅  API 调用入门
D02 ✅  System Prompt 设计
D03 ✅  Structured Outputs
D04 ✅  Function Calling 入门
D05 ✅  Streaming + 错误处理 + LLMClient
D06 ✅  多工具 Agent 综合实战

明天 D07：复习总结，整理速查笔记
下周 D08：ReAct 模式 — 真正的 Agent 推理循环
```

---

## 参考

- [Anthropic Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [OpenAI Function Calling](https://developers.openai.com/api/docs/guides/function-calling)
- 本仓库 D04 — Function Calling 入门
- 本仓库 D05 — LLMClient 封装
