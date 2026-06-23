"""
D10：生产级工具系统
===================
装饰器注册 · 自动 Schema 生成 · Pydantic 校验 · 错误分级 · 多工具选择

用法：
    from tool_system import ToolRegistry, ToolError, with_retry

    registry = ToolRegistry()

    @registry.register
    def web_search(query: str) -> str:
        '''在互联网上搜索实时信息。
        适用：需要最新数据（新闻、价格、天气）。
        不适用：已知常识、数学计算。'''
        ...

    # 导出为 OpenAI / Anthropic 格式
    openai_tools = registry.to_openai_format()

    # 多工具筛选
    relevant = registry.filter_by_query("查天气", top_k=5)
"""

import re
import time
import inspect
import functools
from typing import Callable, get_type_hints, get_origin, get_args, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# 1. 错误体系
# ============================================================

class ErrorCategory(Enum):
    PARAM = "param"        # 参数错误：类型不对、缺字段 → 让 LLM 修正
    BUSINESS = "business"  # 业务错误：用户不存在、权限不足 → LLM 换策略
    TRANSIENT = "transient"  # 瞬时错误：超时、限流 → 自动重试
    SYSTEM = "system"      # 系统错误：服务挂了 → 降级告知用户


class ToolError(Exception):
    """工具错误，包含分类信息"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.BUSINESS):
        self.message = message
        self.category = category
        super().__init__(message)

    @property
    def retryable(self) -> bool:
        return self.category == ErrorCategory.TRANSIENT


# ============================================================
# 2. 工具模型
# ============================================================

@dataclass
class Tool:
    """工具的完整定义"""
    name: str
    description: str
    parameters: dict  # JSON Schema
    executor: Callable
    category: str = "general"  # 工具分类，用于路由
    require_confirmation: bool = False  # 破坏性操作需人工确认
    tags: list[str] = field(default_factory=list)  # 用于语义检索

    def validate(self, args: dict) -> dict:
        """校验参数，返回清洗后的参数或抛出 ToolError"""
        # 检查必填字段
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})

        for key in required:
            if key not in args or args[key] is None or args[key] == "":
                raise ToolError(
                    f"工具 '{self.name}' 缺少必填参数 '{key}'。"
                    f"参数说明: {properties.get(key, {}).get('description', '无')}",
                    category=ErrorCategory.PARAM,
                )

        # 类型检查
        for key, value in args.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "number" and not isinstance(value, (int, float)):
                    raise ToolError(
                        f"参数 '{key}' 类型错误：期望 number，实际 {type(value).__name__}",
                        category=ErrorCategory.PARAM,
                    )

        return args

    def execute(self, args: dict) -> str:
        """执行工具：先校验 → 再调用"""
        cleaned = self.validate(args)
        try:
            return self.executor(**cleaned)
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"工具 '{self.name}' 执行异常: {e}", category=ErrorCategory.BUSINESS)


# ============================================================
# 3. type hints → JSON Schema
# ============================================================

_PY_TO_JSON = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

def _extract_param_desc(doc: str, param_name: str) -> str:
    """从 docstring 中提取参数说明"""
    if not doc:
        return ""
    # 匹配 :param name: description 或 Args 块中的 name: description
    patterns = [
        rf":param\s+{param_name}\s*:\s*(.+?)(?:\n|$)",
        rf"{param_name}\s*[：:]\s*(.+?)(?:\n|$)",
    ]
    for pat in patterns:
        m = re.search(pat, doc)
        if m:
            return m.group(1).strip()
    return ""


def _extract_return_desc(doc: str) -> str:
    """从 docstring 提取返回值说明"""
    if not doc:
        return ""
    m = re.search(r":returns?\s*:\s*(.+?)(?:\n|$)", doc)
    return m.group(1).strip() if m else ""


def function_to_tool(func: Callable, name: str = None, category: str = "general") -> Tool:
    """
    从 Python 函数自动生成 Tool 对象。

    提取以下信息：
      - 函数名 → tool name
      - docstring → tool description
      - type hints → JSON Schema (参数类型、必填项)
      - :param xxx: → 参数描述
      - :returns: → 返回值描述
    """
    hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""

    # 提取函数描述（docstring 第一段）
    desc_parts = [p.strip() for p in doc.split("\n\n") if p.strip()]
    func_desc = desc_parts[0] if desc_parts else func.__name__

    # 追加返回值描述
    return_desc = _extract_return_desc(doc)
    if return_desc:
        func_desc += f" 返回: {return_desc}"

    # 构建参数 schema
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        py_type = hints.get(param_name, str)
        json_type = "string"

        # 处理 Optional[X] / X | None → 可选
        origin = get_origin(py_type)
        args = get_args(py_type)

        is_optional = False
        if origin is not None and type(None) in args:
            is_optional = True
            # 取非 None 的类型
            non_none = [a for a in args if a is not type(None)]
            if non_none:
                py_type = non_none[0]

        # 映射 Python 类型 → JSON 类型
        if py_type in _PY_TO_JSON:
            json_type = _PY_TO_JSON[py_type]

        param_desc = _extract_param_desc(doc, param_name) or f"{param_name} 参数"

        properties[param_name] = {
            "type": json_type,
            "description": param_desc,
        }

        # 判断是否必填
        if not is_optional and param.default is inspect.Parameter.empty:
            required.append(param_name)

    # 如果只有一个参数且名字是通用的，加示例
    if len(properties) == 1:
        key = list(properties.keys())[0]
        if properties[key]["description"] == f"{key} 参数":
            properties[key]["description"] = f"{key} 参数，如示例值"

    return Tool(
        name=name or func.__name__,
        description=func_desc,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required,
        },
        executor=func,
        category=category,
        tags=[func.__name__, category],
    )


# ============================================================
# 4. 工具注册表
# ============================================================

class ToolRegistry:
    """工具注册中心——支持装饰器注册、查询、导出、筛选"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    # ── 注册 ──────────────────────────────

    def register(self, func=None, *, name: str = None, category: str = "general", require_confirmation: bool = False):
        """
        装饰器方式注册工具。

        用法:
            @registry.register
            def search(query: str) -> str: ...

            @registry.register(name="add", category="math")
            def calculate(expression: str) -> str: ...
        """
        def decorator(fn):
            tool = function_to_tool(fn, name=name, category=category)
            tool.require_confirmation = require_confirmation
            if fn.__doc__:
                # 从 docstring 提取 tags
                tool.tags.extend(
                    w.lower() for w in re.findall(r'[\u4e00-\u9fff\w]{2,}', fn.__doc__)
                    if w.lower() not in ('param', 'returns', 'return')
                )
            self._tools[tool.name] = tool
            return fn
        return decorator(func) if func else decorator

    # ── 查询 ──────────────────────────────

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())

    def list_by_category(self, category: str) -> list[Tool]:
        return [t for t in self._tools.values() if t.category == category]

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    @property
    def categories(self) -> list[str]:
        return list(set(t.category for t in self._tools.values()))

    # ── 筛选（多工具选择）─────────────────

    def filter_by_query(self, query: str, top_k: int = 5) -> list[Tool]:
        """
        基于关键词匹配的工具筛选。

        生产环境中这里应该用 embedding + 语义检索。
        这里用关键词匹配作为简单实现。
        """
        query_lower = query.lower()
        scored = []

        for tool in self._tools.values():
            score = 0
            # 名称匹配
            if any(w in tool.name.lower() for w in query_lower.split()):
                score += 10
            # 描述匹配
            desc_lower = tool.description.lower()
            score += sum(1 for w in query_lower.split() if w in desc_lower)
            # 标签匹配
            score += sum(1 for tag in tool.tags if tag in query_lower)

            if score > 0:
                scored.append((tool, score))

        scored.sort(key=lambda x: -x[1])
        return [t for t, _ in scored[:top_k]] if scored else self.list_all()[:top_k]

    def filter_by_category(self, category: str) -> list[Tool]:
        """按分类筛选，用于分类路由策略"""
        return self.list_by_category(category)

    # ── 导出 ──────────────────────────────

    def to_openai_format(self, tools: list[Tool] = None) -> list[dict]:
        """导出为 OpenAI Function Calling 格式"""
        if tools is None:
            tools = self.list_all()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                }
            }
            for t in tools
        ]

    def to_anthropic_format(self, tools: list[Tool] = None) -> list[dict]:
        """导出为 Anthropic Tool Use 格式"""
        if tools is None:
            tools = self.list_all()
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    # ── 统计 ──────────────────────────────

    def stats(self) -> dict:
        cats = {}
        for t in self._tools.values():
            cats.setdefault(t.category, 0)
            cats[t.category] += 1
        return {
            "total": len(self._tools),
            "by_category": cats,
            "names": list(self._tools.keys()),
        }


# ============================================================
# 5. 重试装饰器
# ============================================================

def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    工具调用重试装饰器。

    只重试瞬时错误（TRANSIENT），参数错误和业务错误立即抛出。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ToolError as e:
                    if not e.retryable:
                        raise  # 不可重试，直接抛
                    last_error = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
            raise ToolError(
                f"重试 {max_retries} 次后仍失败: {last_error.message}",
                category=ErrorCategory.SYSTEM,
            )
        return wrapper
    return decorator


# ============================================================
# 6. 工具执行器（Agent 用）
# ============================================================

class ToolExecutor:
    """统一的工具执行入口——校验 + 重试 + 错误格式化"""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(self, tool_name: str, args: dict) -> str:
        """执行工具，返回格式化结果"""
        tool = self.registry.get(tool_name)
        if not tool:
            available = ", ".join(self.registry.list_all())
            return f"错误: 未知工具 '{tool_name}'。可用: {available}"

        try:
            result = tool.execute(args)
            return result
        except ToolError as e:
            if e.category == ErrorCategory.PARAM:
                # 参数错误 → 返回详细错误 + 正确格式提示
                return (
                    f"参数错误: {e.message}\n"
                    f"正确的参数格式: {tool.parameters}"
                )
            elif e.category == ErrorCategory.TRANSIENT:
                return f"工具暂时不可用（瞬时错误），请稍后重试: {e.message}"
            elif e.category == ErrorCategory.SYSTEM:
                return f"系统错误，请告知用户稍后重试: {e.message}"
            else:
                return f"工具执行失败: {e.message}"

    def needs_confirmation(self, tool_name: str) -> bool:
        """检查是否需要人工确认"""
        tool = self.registry.get(tool_name)
        return tool.require_confirmation if tool else False
