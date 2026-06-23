"""
D12：Reflection Agent
=====================
Generator（生成）→ Critic（审查）→ Reviser（修改）→ 循环直到 PASS

用法：
    export OPENAI_API_KEY="sk-xxx"
    python reflection_agent.py
"""

import json
from dataclasses import dataclass, field


# ============================================================
# 1. 数据结构
# ============================================================

@dataclass
class CritiqueResult:
    """审查结果"""
    passed: bool
    dimensions: dict[str, bool]  # {维度名: 是否通过}
    issues: list[dict]  # [{"dimension": ..., "problem": ..., "suggestion": ...}]
    overall_feedback: str


@dataclass
class ReflectionState:
    """Reflection 状态——保留每轮版本，防止退化"""
    task: str
    versions: list[str] = field(default_factory=list)
    critiques: list[CritiqueResult] = field(default_factory=list)
    best_version: str = ""
    best_score: int = 0
    round: int = 0


# ============================================================
# 2. Generator — 生成初始答案（可内置 ReAct）
# ============================================================

GENERATOR_PROMPT = """你是一个内容生成助手。根据用户任务生成高质量的回答。

如果任务需要代码，生成带注释的完整代码。
如果任务需要分析，给出结构化的分析。
如果任务需要写作，给出清晰的文章。"""


def generate(task: str, tools: list = None) -> str:
    """Generator: 生成初始答案。tools 可选，如需搜索可传入工具并走迷你 ReAct。"""
    from openai import OpenAI
    client = OpenAI()

    # 简单任务：纯 LLM 生成
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": GENERATOR_PROMPT},
            {"role": "user", "content": task},
        ],
        temperature=0.3,  # 稍高温度，让输出有"改进空间"
    )
    return resp.choices[0].message.content


# ============================================================
# 3. Critic — 多维度审查
# ============================================================

CRITIC_PROMPT = """你是一个严格的审查员。从以下维度审查输出：

1. 正确性 (correctness): 逻辑是否正确、事实是否准确、代码有无 bug
2. 完整性 (completeness): 是否覆盖了所有要求、有无遗漏
3. 清晰度 (clarity): 结构是否清晰、表达是否易懂
4. 安全性 (safety): 代码有无安全漏洞、回答有无风险内容

对每个维度：[PASS] 或 [FAIL]，如果 FAIL 说明具体问题和修改建议。

输出 JSON:
{
  "dimensions": {
    "correctness": {"passed": true|false, "comment": "..."},
    "completeness": {"passed": true|false, "comment": "..."},
    "clarity": {"passed": true|false, "comment": "..."},
    "safety": {"passed": true|false, "comment": "..."}
  },
  "overall_pass": true|false,
  "overall_feedback": "总评，如全部 PASS 则写 '审查通过，无需修改'",
  "issues": [
    {"dimension": "correctness", "problem": "具体问题", "suggestion": "修改建议"},
    ...
  ],
  "key_strengths": ["优点1", "优点2"]
}

审查规则：
- 不吹毛求疵——小问题如果是风格偏好，可以 PASS
- 代码的逻辑错误、边界条件遗漏必须指出来
- 如果所有维度都 PASS，overall_pass 为 true，issues 为空"""


def critique(output: str, task: str) -> CritiqueResult:
    """Critic: 多维度审查输出质量"""
    from openai import OpenAI
    client = OpenAI()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": f"任务: {task}\n\n待审查的输出:\n{output}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )

    data = json.loads(resp.choices[0].message.content)

    passed = data.get("overall_pass", False)
    dimensions = {
        k: v.get("passed", False)
        for k, v in data.get("dimensions", {}).items()
    }

    return CritiqueResult(
        passed=passed,
        dimensions=dimensions,
        issues=data.get("issues", []),
        overall_feedback=data.get("overall_feedback", ""),
    )


# ============================================================
# 4. Reviser — 根据反馈修改
# ============================================================

REVISER_PROMPT = """你是一个修改助手。根据审查意见修改输出。

修改原则：
1. 只修改被指出的问题，保留审查认可的部分
2. 逐条处理审查意见中的每个 issue
3. 修改后输出完整的新版本（不是只输出修改的部分）
4. 在代码块中用注释标注修改了哪里（如 # [FIXED] 修复了边界条件）

审查意见: {feedback}
原始任务: {task}"""


def revise(original: str, critique_result: CritiqueResult, task: str) -> str:
    """Reviser: 根据 Critic 反馈修改输出"""
    from openai import OpenAI
    client = OpenAI()

    feedback_text = "\n".join(
        f"[{i.get('dimension','')}] {i.get('problem','')} → 建议: {i.get('suggestion','')}"
        for i in critique_result.issues
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": REVISER_PROMPT.format(feedback=feedback_text, task=task)},
            {"role": "user", "content": f"原始输出:\n{original}\n\n请输出修改后的完整版本:"},
        ],
        temperature=0.0,
    )
    return resp.choices[0].message.content


# ============================================================
# 5. Reflection 主循环
# ============================================================

class ReflectionAgent:
    """
    Reflection Agent = Generator + Critic + Reviser 循环

    每轮：生成/修改 → 审查 → 通过则输出，不通过则修改后继续
    """

    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds

    def run(self, task: str, tools: list = None, verbose: bool = True) -> str:
        state = ReflectionState(task=task)

        # ① Generate
        if verbose:
            print("=" * 60)
            print("  ✍️  第 1 轮：Generator — 生成初始答案")

        current = generate(task, tools)
        state.versions.append(current)
        state.best_version = current

        if verbose:
            print(f"  初始输出 ({len(current)} 字符):")
            print(f"  {current[:200]}...")

        for round_num in range(1, self.max_rounds + 1):
            if verbose:
                print(f"\n  {'='*60}")
                print(f"  🔍 第 {round_num} 轮：Critic — 审查")

            # ② Critique
            result = critique(current, task)
            state.critiques.append(result)

            dim_status = " ".join(
                f"{k}:{'✅' if v else '❌'}"
                for k, v in result.dimensions.items()
            )
            if verbose:
                print(f"  {dim_status}")
                print(f"  overall_pass: {result.passed}")
                if result.issues:
                    for issue in result.issues:
                        print(f"    ❌ [{issue['dimension']}] {issue['problem'][:100]}")

            # 通过 → 输出
            if result.passed:
                if verbose:
                    print(f"\n  ✅ 全部 PASS，输出最终版本（共 {round_num} 轮）")
                return current

            # ③ Revise
            if verbose:
                print(f"\n  🔧 第 {round_num} 轮：Reviser — 根据反馈修改")

            revised = revise(current, result, task)
            state.versions.append(revised)

            # ④ 检测退化（新版本更短很多 = 可能丢失了内容）
            if len(revised) < len(current) * 0.3:
                if verbose:
                    print("  ⚠️ 检测到严重退化（新版本大幅缩水），回退到上一版本并终止")
                return current

            current = revised
            state.round = round_num

            if verbose:
                print(f"  修改后 ({len(revised)} 字符):")
                print(f"  {revised[:200]}...")

        if verbose:
            print(f"\n  ⚠️ 达到最大轮次 ({self.max_rounds})，输出当前版本")
        return current


# ============================================================
# 6. Demo
# ============================================================

if __name__ == "__main__":
    agent = ReflectionAgent(max_rounds=3)

    tasks = [
        "写一个 Python 二分查找函数 binary_search(arr, target)，返回索引，未找到返回 -1",
        "用 100 字以内解释什么是机器学习",
        "写一个安全的用户输入处理函数 sanitize_input(text)，防止 XSS 攻击",
    ]

    print("D12: Reflection Agent (Generator → Critic → Reviser)")
    print("=" * 60)
    print("  示例任务:")
    for i, t in enumerate(tasks, 1):
        print(f"    {i}. {t}")
    print()

    try:
        choice = input("  选一个任务 (1/2/3) 或输入自定义: ").strip()
        if choice in ("1", "2", "3"):
            task = tasks[int(choice) - 1]
        elif choice:
            task = choice
        else:
            task = tasks[0]

        result = agent.run(task)
        print(f"\n\n  {'='*60}")
        print(f"  📝 最终输出:\n")
        print(result)
    except (EOFError, KeyboardInterrupt):
        print("\n  再见！")
