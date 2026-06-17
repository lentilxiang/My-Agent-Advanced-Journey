# Agent 开发专项学习计划

> 聚焦 Agent 开发核心技能，跳过 LLM 训练/微调/推理优化等底层。轻理论、重实战。

---

## 能力模型（Agent 开发向）

```
┌──────────────────────────────────────────────┐
│           Agent 开发者能力模型                  │
├────────────┬────────────┬────────────────────┤
│ 基础认知 20% │ 核心技能 50% │ 工程落地 30%       │
├────────────┼────────────┼────────────────────┤
│ LLM 基本原理 │ Agent 设计模式 │ 生产级部署        │
│ Prompt 工程  │ RAG 检索增强  │ 安全与护栏        │
│ API 调用     │ 工具/Function Call │ 评估与监控   │
│ Context 管理 │ 多 Agent 协作  │ 记忆系统          │
└────────────┴────────────┴────────────────────┘
```

---

## 学习阶段（10周，可压缩到 6-8 周）

| 阶段 | 周期 | 主题 |
|------|------|------|
| 一 | 第1周 | LLM 基础认知 + API 上手 |
| 二 | 第2-3周 | Agent 设计模式 + 纯代码手写 |
| 三 | 第4-5周 | RAG 全链路（Agent 必备技能） |
| 四 | 第6-7周 | LangGraph 框架 + MCP 协议 |
| 五 | 第8-9周 | 生产级能力：记忆、安全、评估、部署 |
| 六 | 第10周 | 综合项目：从零构建完整 Agent 应用 |

---

## 第1周：LLM 基础认知 + API 上手

> 目标：理解 LLM 能做什么、怎么调用、怎么控制输出。

### 周一
- [ ] 了解主流模型能力边界：GPT-4o / Claude / Qwen / DeepSeek 各擅长什么
- [ ] 注册 API，跑通第一个调用（Python）
- [ ] 理解 token 概念、上下文窗口限制

### 周二
- [ ] System Prompt vs User Message vs Assistant Message 的角色
- [ ] Temperature / Top-p / Max Tokens 参数实验
- [ ] 写一个简单的"角色扮演"prompt 并测试

### 周三
- [ ] Structured Output：让模型输出合法 JSON
- [ ] JSON mode / JSON Schema 约束
- [ ] 用 Pydantic 校验输出

### 周四
- [ ] Function Calling 入门：让 LLM 决定调用哪个函数
- [ ] 定义工具描述（name、description、parameters schema）
- [ ] 跑通"查天气"demo

### 周五
- [ ] Streaming 输出
- [ ] 错误处理：超时、限流、格式错误的重试策略
- [ ] 封装一个 LLM Client 工具类

### 周末
- [ ] 整理 LLM API 调用速查笔记
- [ ] 阅读 [Anthropic Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- 📖 参考：[Function Calling 与 Tool Use 专题](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md)

---

## 第2周：Agent 设计模式（上）—— 纯代码手写

> 目标：不用任何 Agent 框架，纯 Python 实现核心 Agent 模式。理解原理再学框架。

### 周一 — ReAct 模式原理
- [ ] 理解 ReAct 循环：Thought → Action → Observation
- [ ] 读 [ReAct 论文](https://arxiv.org/abs/2210.03629) 摘要和核心图
- [ ] 手画 ReAct 流程图
- 📖 参考：[Agent 核心概念与设计模式](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md)

### 周二 — 纯 Python 实现 ReAct Agent
- [ ] 定义工具（计算器 + 搜索模拟 + 时间查询，3个即可）
- [ ] 实现核心循环：
  ```python
  while step < max_steps:
      thought = llm.think(messages, tools)
      if thought.is_final:
          return thought.answer
      result = execute_tool(thought.action, thought.input)
      messages.append(observation(result))
  ```
- [ ] ✅ 产出：ReAct Agent（~200行代码）

### 周三 — 工具系统设计
- [ ] 工具注册机制（Tool Registry）
- [ ] 工具描述模板（让 LLM 能理解工具用途）
- [ ] 参数校验 + 错误返回
- [ ] 多工具选择策略：如何从 10+ 工具中选对？

### 周四 — Plan-and-Execute 模式
- [ ] 实现计划生成：LLM 分解任务为步骤列表
- [ ] 执行器：按序执行，失败时重新规划
- [ ] 对比 ReAct vs Plan-Execute 的适用场景
- [ ] ✅ 产出：Plan-Execute Agent

### 周五 — Reflection 模式
- [ ] 实现生成-反思循环
- [ ] 反思 Prompt："请检查你的回答是否有以下问题：事实错误、逻辑矛盾、遗漏信息"
- [ ] 迭代修改直到满意或达到上限
- [ ] ✅ 产出：Reflection Agent

### 周末
- [ ] 画出 3 种模式架构对比图
- [ ] 写总结：每种模式的优劣和适用场景
- [ ] 阅读 [Anthropic - Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)

---

## 第3周：Agent 设计模式（下）—— 多 Agent + 记忆

### 周一 — Supervisor 多 Agent 模式
- [ ] 纯代码实现 Supervisor Agent
- [ ] 任务分配 → Worker 执行 → 结果汇总
- [ ] 条件路由：根据任务类型分配给不同 Worker

### 周二 — 多 Agent 通信
- [ ] 共享状态 vs 消息传递 vs 事件驱动
- [ ] Agent 间上下文传递（不是自由文本，要结构化）
- [ ] ✅ 产出：2 个 Agent 协作完成任务

### 周三 — Agent 记忆系统（短期）
- [ ] 对话历史管理：保留最近 N 轮 + 摘要旧内容
- [ ] 滑动窗口 + 递进式摘要
- [ ] ✅ 产出：带记忆的 Agent

### 周四 — Agent 记忆系统（长期）
- [ ] 向量数据库存储历史交互
- [ ] 关键事实提取：自动识别该记住的信息
- [ ] 记忆检索：相关记忆注入当前上下文
- [ ] ✅ 产出：长期记忆模块

### 周五 — Agent 循环控制
- [ ] 最大步数限制
- [ ] 死循环检测（相似输出检测）
- [ ] Token 预算管理：快用完时触发摘要或终止
- [ ] 超时机制

### 周末
- [ ] 综合实战：做一个能记住用户偏好的研究助手 Agent
- [ ] 阅读 [Lilian Weng - LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/)

---

## 第4周：RAG 全链路（Agent 必备技能）

> 目标：RAG 是 Agent 最常用的能力。掌握从文档到答案的完整链路。

### 周一 — 文档处理
- [ ] 多格式加载：PDF / Markdown / HTML
- [ ] 文本分割：RecursiveCharacterTextSplitter
- [ ] Chunk Size 实验：256 vs 512 vs 1024 对检索效果的影响
- [ ] ✅ 产出：文档处理 pipeline

### 周二 — Embedding + 向量检索
- [ ] 选型对比：BGE-M3 vs GTE vs OpenAI Embedding
- [ ] 向量数据库：Chroma（本地） / Milvus（生产）
- [ ] 跑通：文档 → Embedding → 存储 → 检索
- [ ] ✅ 产出：Naive RAG

### 周三 — 混合检索 + 重排序
- [ ] BM25 关键词检索
- [ ] 向量 + BM25 → RRF 融合
- [ ] BGE-Reranker 精排
- [ ] 对比纯向量 vs 混合检索的效果

### 周四 — 查询优化
- [ ] 查询改写：模糊问题 → 精确检索词
- [ ] Multi-Query：一条问题拆成多条检索
- [ ] HyDE：先生成假设答案再检索
- [ ] 上下文组装：排序（Lost in the Middle）+ 压缩

### 周五 — RAG 评估
- [ ] 构建 50+ 测试 Q&A pair
- [ ] RAGAs 评估：Faithfulness / Relevance / Precision / Recall
- [ ] Bad Case 分析：为什么检索不到？为什么回答错？

### 周末
- [ ] 把 RAG 包装成 Agent 的 Tool
- [ ] Agent 自主决定是否检索、检索什么
- 📖 参考：[RAG 核心知识与面试题](../agent-interview-hub/通用知识/RAG核心知识与面试题.md)
- 📖 参考：[Agentic RAG 与 GraphRAG 深度解析](../agent-interview-hub/通用知识/Agentic%20RAG与GraphRAG深度解析.md)

---

## 第5周：RAG 进阶 + Context Engineering

### 周一 — Agentic RAG
- [ ] Agent 驱动检索决策：简单问题直接答、复杂问题多步检索
- [ ] 查询路由：判断去哪检索（知识库 / 数据库 / 互联网）
- [ ] ✅ 产出：Agentic RAG demo

### 周二 — GraphRAG 入门
- [ ] 理解知识图谱 + RAG 结合的原理
- [ ] 用微软 GraphRAG 跑一个中文 demo
- [ ] 对比 Vector RAG vs GraphRAG 的适用场景

### 周三 — Context Engineering 实践
- [ ] 上下文组装策略：哪些信息放入上下文？
- [ ] 上下文压缩：长文档摘要后再注入
- [ ] 上下文排序：关键信息放首尾
- 📖 参考：[Context Engineering 上下文工程](../agent-interview-hub/通用知识/Context%20Engineering上下文工程.md)

### 周四 — Context Window 管理
- [ ] Token 计数与预算分配
- [ ] System Prompt / Tools / Messages / RAG 结果各占多少 token
- [ ] 动态调整策略

### 周五 — 多轮 RAG 对话
- [ ] 对话历史管理
- [ ] 指代消解："上一个"、"它"指的是什么
- [ ] Follow-up 问题处理

### 周末 — 综合实战
- [ ] 做一个"企业文档智能问答"Agent
- [ ] 包含：混合检索 + 多轮对话 + 引用溯源

---

## 第6周：LangGraph 框架精通

> 目标：掌握工业级 Agent 编排框架，能搭建生产可用的 Agent 系统。

### 周一 — LangGraph 核心概念
- [ ] State：状态定义（TypedDict / Pydantic）
- [ ] Node：每个节点的处理逻辑
- [ ] Edge：普通边 + 条件边
- [ ] 跑通官方 Quick Start
- 📖 参考：[LangChain 与 LangGraph 深度解析](../agent-interview-hub/通用知识/LangChain与LangGraph深度解析.md)

### 周二 — 用 LangGraph 重构 ReAct Agent
- [ ] 定义 AgentState（messages + 中间结果）
- [ ] Model Node → Tool Node → 条件边
- [ ] 对比纯 Python 实现 vs LangGraph 实现的差异

### 周三 — Supervisor Multi-Agent
- [ ] 用 LangGraph 实现 Supervisor 模式
- [ ] 多个 Worker Agent 各有不同工具
- [ ] ✅ 产出：Supervisor Multi-Agent

### 周四 — Human-in-the-Loop
- [ ] 实现审批节点：关键操作暂停等人工确认
- [ ] interrupt() + Command(resume=...) 模式
- [ ] 适用场景：删除确认、发送前审核、高风险操作

### 周五 — Checkpointing + 流式
- [ ] 状态持久化：中断后可从 checkpoint 恢复
- [ ] Streaming：节点级别的流式输出
- [ ] 错误恢复：节点失败后的重试策略

### 周末
- [ ] 综合项目：用 LangGraph 做一个"代码审查 Agent"
- [ ] 包含：读取代码 → 分析 → 提建议 → 人工确认 → 修改
- [ ] 阅读 [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)

---

## 第7周：MCP + 工具生态 + 其他框架

### 周一 — MCP 协议深入
- [ ] 理解 MCP 架构：Host → Client → Server
- [ ] Server 三种能力：Tools / Resources / Prompts
- [ ] 传输方式：stdio（本地） vs SSE/HTTP（远程）
- [ ] 跑通官方 MCP Server demo
- 📖 参考：[MCP 与工具生态](../agent-interview-hub/通用知识/MCP与工具生态.md)

### 周二 — 开发 MCP Server
- [ ] 实现一个自定义 MCP Server：（如：本地文件管理工具）
- [ ] 定义 Tools（读取/写入/列出文件）
- [ ] 在 Claude Desktop 或其他 MCP Client 中测试
- [ ] ✅ 产出：自定义 MCP Server

### 周三 — MCP 生产实践
- [ ] 工具权限控制
- [ ] 错误处理和重试
- [ ] 多 Server 管理
- [ ] MCP 与 LangChain/LangGraph 的集成方式

### 周四 — CrewAI 快速上手
- [ ] 安装 CrewAI，跑通 Quick Start
- [ ] 定义角色 + 目标 + 工具 + Task
- [ ] 对比 LangGraph vs CrewAI 的优劣

### 周五 — Dify + A2A 了解
- [ ] Dify 搭建 RAG 应用（低代码方式）
- [ ] 了解 A2A 协议：Agent 发现、能力声明、任务委托
- [ ] 了解 AutoGen 的设计思路

### 周末
- [ ] 框架选型总结：什么时候用哪个？
- [ ] 总结 MCP 最佳实践
- 📖 参考：[Agent 框架全景](../agent-interview-hub/通用知识/Agent框架全景.md)

---

## 第8周：生产级能力（上）—— 安全 + 评估

### 周一 — Prompt Injection 攻防
- [ ] 学习常见攻击手法：
  - 直接注入："忽略之前的指令..."
  - 间接注入：恶意内容藏在文档/网页中
  - 越狱攻击
- [ ] 防护方案：输入过滤 + 指令隔离 + 输出校验
- 📖 参考：[Agent 安全与评估体系](../agent-interview-hub/通用知识/Agent安全与评估体系.md)

### 周二 — Guardrails 实现
- [ ] 输入层护栏：检测恶意 prompt
- [ ] 工具调用层护栏：高危操作拦截
- [ ] 输出层护栏：PII 脱敏、有害内容过滤
- [ ] 了解 Guardrails AI / NeMo Guardrails

### 周三 — Agent 评估体系
- [ ] 评估维度：任务完成率、步骤效率、工具调用准确率
- [ ] LLM-as-Judge：用 GPT-4 给 Agent 输出打分
- [ ] 构建 Golden Test Set
- 📖 参考：[系统设计面试题 - 进阶篇](../agent-interview-hub/通用知识/系统设计面试题-进阶篇.md)

### 周四 — 可观测性
- [ ] LangSmith / LangFuse 接入
- [ ] 全链路 Trace：每个 Thought / Action / Observation
- [ ] 成本追踪：token 消耗、API 费用
- [ ] 异常告警

### 周五 — 成本优化
- [ ] 语义缓存（GPTCache）：相似问题直接返回
- [ ] 模型路由：简单任务用便宜模型、复杂任务用强模型
- [ ] Prompt 精简：token 消耗降低 30-50%
- [ ] 批处理：非实时任务合并处理

### 周末
- [ ] 为之前的 Agent 项目接入评估 + 监控
- [ ] 写一份 Agent 安全 Checklist

---

## 第9周：生产级能力（下）—— 部署 + 实战

### 周一 — FastAPI 服务化
- [ ] FastAPI 封装 Agent 为 REST API
- [ ] 请求/响应 Schema 设计
- [ ] 异步处理（长任务后台执行）
- [ ] WebSocket 流式输出

### 周二 — Docker 部署
- [ ] 编写 Dockerfile
- [ ] docker-compose 编排（Agent + Redis + 向量数据库）
- [ ] 环境变量管理、密钥管理

### 周三 — 多模型路由
- [ ] 实现统一的 LLM 抽象层
- [ ] 适配 OpenAI / Claude / 国产模型 API
- [ ] 动态模型切换：根据任务选择模型

### 周四 — Agent 记忆系统（生产级）
- [ ] Redis：短期会话状态
- [ ] PostgreSQL + pgvector：长期记忆 + 向量检索
- [ ] 记忆检索策略：语义相似 + 时间衰减

### 周五 — Agentic Coding 工具了解
- [ ] 深入了解 Claude Code / Cursor / Copilot 的技术架构
- [ ] 理解 Agent Loop 在编程场景的应用
- 📖 参考：[Agentic Coding 与 AI 编程工具](../agent-interview-hub/通用知识/Agentic%20Coding与AI编程工具.md)

### 周末
- [ ] 综合实战：把之前的 Agent 项目服务化 + Docker 部署
- [ ] 加监控 + 日志 + 错误告警

---

## 第10周：综合项目——从零构建完整 Agent 应用

> 目标：整合所有技能，完成一个可展示的完整项目。

### 选题建议（选一个）

**A. 个人研究助手 Agent**
- 多 Agent：研究员 + 分析师 + 写手 + 审核员
- 工具：搜索 + RAG + Python REPL
- 记忆：记住用户研究方向偏好
- 安全：高风险操作审批

**B. 智能客服 Agent**
- 意图识别 + 知识库 RAG
- 多轮对话 + 上下文管理
- 自动升级人工
- 安全护栏

**C. 代码助手 Agent**
- 读代码 → 理解 → 修改建议 → 写测试
- CLI 交互
- Git 操作集成

### 周一-周二：系统设计
- [ ] 确定选题，画架构图
- [ ] 定义 Agent 角色 + 工具集
- [ ] 确定技术栈

### 周三-周五：核心开发
- [ ] 用 LangGraph 编排 Agent 工作流
- [ ] 集成 MCP 工具
- [ ] 实现记忆系统

### 周六：打磨
- [ ] 安全护栏接入
- [ ] 评估测试
- [ ] Docker 部署

### 周日：文档
- [ ] README（架构图 + 使用说明 + 效果展示）
- [ ] GitHub 发布
- [ ] ✅ 项目完成！

---

## 核心资源速查

### 本仓库必读文档（按优先级）

| 优先级 | 文档 | 
|:------:|------|
| ⭐⭐⭐ | [Agent 核心概念与设计模式](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) |
| ⭐⭐⭐ | [RAG 核心知识与面试题](../agent-interview-hub/通用知识/RAG核心知识与面试题.md) |
| ⭐⭐⭐ | [Function Calling 与 Tool Use 专题](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md) |
| ⭐⭐⭐ | [MCP 与工具生态](../agent-interview-hub/通用知识/MCP与工具生态.md) |
| ⭐⭐ | [LangChain 与 LangGraph 深度解析](../agent-interview-hub/通用知识/LangChain与LangGraph深度解析.md) |
| ⭐⭐ | [Context Engineering 上下文工程](../agent-interview-hub/通用知识/Context%20Engineering上下文工程.md) |
| ⭐⭐ | [Agent 安全与评估体系](../agent-interview-hub/通用知识/Agent安全与评估体系.md) |
| ⭐⭐ | [Agent 框架全景](../agent-interview-hub/通用知识/Agent框架全景.md) |
| ⭐ | [Agentic RAG 与 GraphRAG 深度解析](../agent-interview-hub/通用知识/Agentic%20RAG与GraphRAG深度解析.md) |
| ⭐ | [Agentic Coding 与 AI 编程工具](../agent-interview-hub/通用知识/Agentic%20Coding与AI编程工具.md) |

### 必读外部资源

| 资源 | 链接 |
|------|------|
| Lilian Weng - LLM Agents | https://lilianweng.github.io/posts/2023-06-23-agent/ |
| Anthropic - Building Effective Agents | https://www.anthropic.com/engineering/building-effective-agents |
| LangGraph 官方文档 | https://langchain-ai.github.io/langgraph/ |
| MCP 官方文档 | https://modelcontextprotocol.io/ |
| 吴恩达 - AI Agents in LangGraph | https://www.deeplearning.ai/short-courses/ |

### 必刷开源项目

| 项目 | GitHub | 学习重点 |
|------|--------|---------|
| LangGraph | https://github.com/langchain-ai/langgraph | Agent 编排 |
| Dify | https://github.com/langgenius/dify | 可视化搭建 |
| CrewAI | https://github.com/crewAIInc/crewAI | 多角色协作 |
| Open Interpreter | https://github.com/OpenInterpreter/open-interpreter | Agent 设计 |

---

## 与完整版的区别

| 主题 | 完整版 | Agent 开发专项 | 原因 |
|------|:------:|:--------------:|------|
| Transformer 深入 | ✅ 1周 | ❌ 跳过 | Agent 开发不需要手写注意力机制 |
| LLM 预训练 | ✅ 1周 | ❌ 跳过 | 用 API，不需要懂训练 |
| 模型微调 LoRA/QLoRA | ✅ 2周 | ❌ 跳过 | 这不是 Agent 开发的核心 |
| RLHF/DPO/GRPO | ✅ 1周 | ❌ 跳过 | 对齐训练是算法岗的事 |
| 推理优化 vLLM/量化 | ✅ 1周 | ❌ 跳过 | 模型部署不是 Agent 开发重点 |
| **Agent 设计模式** | ✅ 2周 | ✅ **3周（加深）** | **核心+核心** |
| **RAG 全链路** | ✅ 2周 | ✅ **2周** | **Agent 必备** |
| **LangGraph** | ✅ 1周 | ✅ **1周** | **主力框架** |
| **MCP 协议** | ✅ 0.5周 | ✅ **1周（加深）** | **工具集成核心** |
| **安全 + 评估** | ✅ 1周 | ✅ **1周** | **生产必备** |
| **综合项目** | 3个 | 1个（深度打磨） | **质量 > 数量** |

---

> **一句话：Agent 开发的核心是——会调用模型、会设计 Agent 循环、会集成工具、会搭 RAG、会处理上下文、会安全保障。不需要会训练模型。**
