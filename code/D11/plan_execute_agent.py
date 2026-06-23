"""
D11：Plan-and-Execute Agent
============================
Planner → Executor → Replanner 三步架构。

用法：
    export OPENAI_API_KEY="sk-xxx"
    python plan_execute_agent.py
"""

import json
import sys
sys.path.insert(0, '..')
from D10.tool_system import ToolRegistry, ToolExecutor, ToolError, ErrorCategory


# ============================================================
# 1. 工具（复用 D10 工具系统）
# ============================================================

registry = ToolRegistry()


@registry.register(category="info")
def web_search(query: str) -> str:
    """搜索互联网信息。适用: 需要最新数据时。不适用: 已知常识、数学。

    :param query: 搜索查询词
    """
    mock = {
        "ai agent 定义": "AI Agent 是能感知环境、推理决策、执行行动的自主AI系统。核心特征：自主性、闭环反馈、工具使用。",
        "ai agent 核心技术 react": "ReAct(Reasoning+Acting)由Yao et al. 2022提出。交替推理和行动。Thought→Action→Observation循环。",
        "ai agent 多智能体": "多Agent协作包括Supervisor模式、Debate模式、Pipeline模式。代表框架: LangGraph、CrewAI。",
        "ai agent 记忆系统": "Agent记忆分短期(上下文)、工作(中间状态)、长期(向量库)、情景(经验案例)。四层架构。",
        "ai agent 市场 2024 2025": "2024-2025年AI Agent市场快速增长。代表: ChatGPT、Claude Code、Devin。企业级Agent平台融资活跃。",
        "ai agent 应用场景": "客服Agent、代码Agent、研究Agent、自动化Agent。2025年企业采用率预计超60%。",
        "苹果 营收 2022": "苹果2022财年营收3943亿美元。",
        "苹果 营收 2023": "苹果2023财年营收3833亿美元，同比下降2.8%。",
        "苹果 营收 2024": "苹果2024财年营收3910亿美元，同比增长2.0%。",
        "agent 安全 prompt injection": "Agent安全核心挑战: Prompt注入、工具越权、数据泄露。防护: 输入过滤、工具白名单、沙箱执行。",
    }
    for k, v in mock.items():
        if all(w in query.lower() for w in k.split()):
            return f"搜索结果: {v}"
    return f"搜索结果: 关于'{query}'，找到了一些相关信息（模拟）。"


@registry.register(category="math")
def calculator(expression: str) -> str:
    """安全计算。支持 + - * / ** sqrt等。

    :param expression: 数学表达式
    """
    import ast, math, operator as op
    _ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow}
    _funcs = {"sqrt": math.sqrt, "abs": abs, "round": round}
    def _eval(n):
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.BinOp): return _ops[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.Call):
            name = n.func.id if isinstance(n.func, ast.Name) else "?"
            return _funcs.get(name, lambda *a: 0)(*[_eval(a) for a in n.args])
        raise ValueError(f"不支持: {type(n)}")
    return f"计算结果: {_eval(ast.parse(expression.strip(), mode='eval').body)}"


# ============================================================
# 2. Planner — 分解任务
# ============================================================

PLANNER_PROMPT = """你是一个任务规划专家。将用户任务分解为有序的执行步骤。

每个步骤包含:
- goal: 步骤目标（一句话）
- expected_output: 预期产出（一句话）
- depends_on: 依赖的前置步骤ID列表（空列表=无依赖）

输出 JSON:
{
  "overall_goal": "任务总目标",
  "steps": [
    {"id": 1, "goal": "...", "expected_output": "...", "depends_on": []},
    {"id": 2, "goal": "...", "expected_output": "...", "depends_on": [1]},
    ...
  ]
}

规则:
- 步骤数 3-7 个
- 每步目标明确、可独立执行
- 最后一步是综合汇总
- 步骤间有逻辑顺序"""


def plan(task: str, model: str = "gpt-4o-mini") -> dict:
    """Planner: 将任务分解为有序步骤列表"""
    from openai import OpenAI
    client = OpenAI()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": task},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    plan_data = json.loads(resp.choices[0].message.content)
    return plan_data


# ============================================================
# 3. Executor — 执行单个步骤（迷你 ReAct）
# ============================================================

EXECUTOR_PROMPT = """你是一个执行助手。你的任务很明确：完成当前这一步的子目标。

可用工具:
{tools_desc}

输出 JSON:
{{"thought": "<推理>", "action": "<tool_name>", "action_input": {{...}}}}
完成时: {{"thought": "...", "action": "Finish", "action_input": "<本步骤的结果>"}}

规则: 目标明确，不需要做步骤之外的事。步骤目标: {step_goal}"""


def execute_step(step: dict, context: list[str], max_turns: int = 4) -> str:
    """Executor: 执行单个步骤（迷你 ReAct 循环）"""
    from openai import OpenAI
    client = OpenAI()
    executor = ToolExecutor(registry)

    tools_desc = "\n".join(
        f"  {t.name}: {t.description[:80]}"
        for t in registry.list_all()
    )

    context_text = "\n".join(f"  步骤{i+1}结果: {r}" for i, r in enumerate(context)) if context else "无"

    system = EXECUTOR_PROMPT.format(
        tools_desc=tools_desc,
        step_goal=step["goal"],
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"执行此步骤: {step['goal']}\n预期产出: {step['expected_output']}\n前面步骤的结果: {context_text}"},
    ]

    for turn in range(max_turns):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(resp.choices[0].message.content)

        if parsed.get("action") == "Finish":
            return parsed.get("action_input", "步骤完成")

        result = executor.execute(
            parsed.get("action", ""),
            parsed.get("action_input", {}),
        )
        messages.append({"role": "assistant", "content": resp.choices[0].message.content})
        messages.append({"role": "user", "content": f"Observation: {result}"})

    return "[未完成] 达到最大步数"


# ============================================================
# 4. Replanner — 条件调整计划
# ============================================================

def maybe_replan(original_plan: dict, step_id: int, step_result: str) -> list:
    """Replanner: 检查是否需要调整剩余计划"""
    # 只处理明显异常：步骤结果为空、失败
    if "未完成" not in step_result and "错误" not in step_result:
        return original_plan["steps"]  # 不需要调整

    # 需要调整时（生产环境这里再调一次 LLM 做 replan）
    # 简化版：标记当前步骤需要重试
    print(f"  ⚠️ Replanner: Step {step_id} 执行异常，标记需要重试")
    return original_plan["steps"]


# ============================================================
# 5. Plan-and-Execute 主循环
# ============================================================

class PlanAndExecuteAgent:
    """Plan-and-Execute Agent = Planner + Executor + Replanner"""

    def __init__(self, planner_model: str = "gpt-4o-mini"):
        self.planner_model = planner_model

    def run(self, task: str, verbose: bool = True) -> str:
        # Phase 1: Plan
        if verbose:
            print("=" * 60)
            print("  📋 Phase 1: Planner — 分解任务")
            print("=" * 60)

        plan_data = plan(task, model=self.planner_model)

        if verbose:
            print(f"  总目标: {plan_data['overall_goal']}")
            print(f"  步骤数: {len(plan_data['steps'])}")
            for s in plan_data["steps"]:
                deps = f" (依赖: {s['depends_on']})" if s.get("depends_on") else ""
                print(f"    Step {s['id']}: {s['goal']}{deps}")

        # Phase 2: Execute
        steps = plan_data["steps"]
        results = {}

        for i, step in enumerate(steps):
            if verbose:
                print(f"\n  {'='*60}")
                print(f"  ⚡ Phase 2: Executor — Step {step['id']}/{len(steps)}")
                print(f"    目标: {step['goal']}")
                print(f"  {'='*60}")

            # 收集依赖步骤的结果
            context = []
            for dep_id in step.get("depends_on", []):
                if dep_id in results:
                    context.append(results[dep_id])

            # 执行
            step_result = execute_step(step, context)

            if verbose:
                print(f"  📄 Step {step['id']} 结果: {step_result[:200]}...")

            results[step["id"]] = step_result

            # Phase 3: Replan（条件触发）
            steps = maybe_replan(plan_data, step["id"], step_result)

        # Phase 4: Synthesize
        if verbose:
            print(f"\n  {'='*60}")
            print(f"  📝 Phase 3: Synthesizer — 综合汇总")
            print(f"  {'='*60}")

        synthesis = self._synthesize(task, results)

        return synthesis

    def _synthesize(self, task: str, results: dict) -> str:
        """Synthesizer: 汇总所有步骤结果"""
        from openai import OpenAI
        client = OpenAI()

        results_text = "\n".join(f"步骤{k}: {v}" for k, v in sorted(results.items()))

        resp = client.chat.completions.create(
            model=self.planner_model,
            messages=[
                {"role": "system", "content": "你是一个报告撰写助手。根据各步骤的执行结果，生成最终的综合回答。"},
                {"role": "user", "content": f"原始任务: {task}\n\n各步骤结果:\n{results_text}\n\n请生成最终的综合回答。"},
            ],
            temperature=0.0,
        )
        return resp.choices[0].message.content


# ============================================================
# 6. Demo
# ============================================================

if __name__ == "__main__":
    agent = PlanAndExecuteAgent()

    tasks = [
        "写一份简短的 AI Agent 发展报告（包含核心技术和应用场景）",
        "苹果公司2022-2024年营收变化分析",
    ]

    print("D11: Plan-and-Execute Agent")
    print("=" * 60)
    print("  示例任务:")
    for i, t in enumerate(tasks, 1):
        print(f"    {i}. {t}")
    print()

    try:
        choice = input("  选一个任务 (1/2) 或输入自定义任务: ").strip()
        if choice == "1":
            task = tasks[0]
        elif choice == "2":
            task = tasks[1]
        else:
            task = choice

        if not task:
            task = tasks[0]

        answer = agent.run(task)
        print(f"\n\n  📝 最终输出:\n{answer}")
    except (EOFError, KeyboardInterrupt):
        print("\n  再见！")
