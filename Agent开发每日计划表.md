# Agent 开发每日学习计划表

> 10周，70天，每天编号可追踪进度。代码实践 : 理论学习 = 6:4。

---

## 第1周：LLM API + Function Calling 上手

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D01 | 周一 | 注册 API，跑通第一个 LLM 调用 | 可用的 API Key | [OpenAI 文档](https://platform.openai.com/docs/) / [Claude 文档](https://docs.anthropic.com/) |
| D02 | 周二 | 理解 System/User/Assistant 三种消息角色，调 Temperature/Top-p | 角色扮演 demo | [Anthropic Prompt Guide](https://docs.anthropic.com/claude/docs/prompt-engineering) |
| D03 | 周三 | Structured Output：JSON mode，用 Pydantic 校验 | 结构化输出代码 | [OpenAI JSON Mode](https://platform.openai.com/docs/guides/structured-outputs) |
| D04 | 周四 | Function Calling 入门：定义工具、让 LLM 决定调哪个 | "查天气" demo | [Function Calling 专题](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md) |
| D05 | 周五 | Streaming 输出 + 错误处理（超时/限流/重试） | LLM Client 工具类 | [OpenAI Cookbook](https://cookbook.openai.com/) |
| D06 | 周六 | 练习：用 Function Calling 做一个可调用 5 个工具的 Agent | 多工具调用 Agent | [Anthropic Tool Use](https://docs.anthropic.com/claude/docs/tool-use) |
| D07 | 周日 | 复习总结，整理 API 调用速查笔记 | 速查笔记 | — |

---

## 第2周：Agent 设计模式——纯代码手写

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D08 | 周一 | 理解 ReAct 循环：Thought→Action→Observation，画流程图 | ReAct 流程图 | [Agent 核心概念与设计模式](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) |
| D09 | 周二 | 纯 Python 实现 ReAct Agent（3 个工具） | ReAct Agent 代码 | [ReAct 论文](https://arxiv.org/abs/2210.03629) / [Lilian Weng](https://lilianweng.github.io/posts/2023-06-23-agent/) |
| D10 | 周三 | 工具系统设计：注册机制、描述模板、参数校验、多工具选择 | 工具系统 | [Function Calling 专题](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md) |
| D11 | 周四 | 实现 Plan-and-Execute 模式：分解→执行→调整 | Plan-Execute Agent | [Plan-Execute 论文](https://arxiv.org/abs/2305.04091) |
| D12 | 周五 | 实现 Reflection 模式：生成→反思→修改 | Reflection Agent | [Reflexion 论文](https://arxiv.org/abs/2303.11366) |
| D13 | 周六 | 画 3 种模式架构对比图，总结优劣和适用场景 | 对比分析文档 | [Anthropic - Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) |
| D14 | 周日 | 选一个模式，加入更多工具（搜索、Python执行、文件读写） | 增强版 Agent | — |

---

## 第3周：多 Agent + 记忆系统

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D15 | 周一 | 实现 Supervisor 多 Agent：主 Agent 分配任务给 N 个 Worker | Supervisor Agent | [Agent 核心概念](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) |
| D16 | 周二 | Agent 间通信：共享状态 vs 消息传递 vs 事件驱动 | 2 Agent 协作 demo | [LangGraph Multi-Agent](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/) |
| D17 | 周三 | 短期记忆：对话历史管理 + 滑动窗口 + 递进式摘要 | 带记忆的 Agent | [Context Engineering](../agent-interview-hub/通用知识/Context%20Engineering上下文工程.md) |
| D18 | 周四 | 长期记忆：向量数据库存储历史 + 关键事实提取 + 记忆检索 | 长期记忆模块 | [Chroma](https://docs.trychroma.com/) / [Mem0](https://github.com/mem0ai/mem0) |
| D19 | 周五 | Agent 循环控制：最大步数、死循环检测、Token 预算、超时 | 循环控制模块 | — |
| D20 | 周六 | 综合实战：做一个"带记忆的研究助手 Agent" | 研究助手 Agent | — |
| D21 | 周日 | 复习本周代码，写 Agent 开发笔记 | 笔记 | — |

---

## 第4周：RAG 全链路

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D22 | 周一 | 文档加载（PDF/MD/HTML）+ 文本分割，对比 Chunk Size | 文档处理 pipeline | [LangChain Text Splitters](https://python.langchain.com/docs/concepts/text_splitters/) |
| D23 | 周二 | Embedding 选型对比 + Chroma 向量数据库实操 | Naive RAG 代码 | [RAG 核心知识](../agent-interview-hub/通用知识/RAG核心知识与面试题.md) |
| D24 | 周三 | 混合检索：BM25 + 向量 + RRF 融合 | 混合检索 demo | [LlamaIndex Hybrid Search](https://docs.llamaindex.ai/) |
| D25 | 周四 | Re-ranking（BGE-Reranker）+ 查询改写（Multi-Query/HyDE） | 进阶检索 | [BGE-Reranker](https://huggingface.co/BAAI/bge-reranker-v2-m3) |
| D26 | 周五 | RAG 评估：构建测试集 + RAGAs（Faithfulness/Relevance） | 评估报告 | [RAGAs](https://docs.ragas.io/) |
| D27 | 周六 | 把 RAG 包装成 Agent 的 Tool，Agent 决定何时检索 | Agent + RAG | [Agentic RAG](../agent-interview-hub/通用知识/Agentic%20RAG与GraphRAG深度解析.md) |
| D28 | 周日 | 复习 + Bad Case 分析 | 优化清单 | — |

---

## 第5周：RAG 进阶 + Context Engineering

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D29 | 周一 | Agentic RAG：Agent 驱动检索决策（简单答 vs 多步检索） | Agentic RAG demo | [Agentic RAG](../agent-interview-hub/通用知识/Agentic%20RAG与GraphRAG深度解析.md) |
| D30 | 周二 | GraphRAG 入门：用微软 GraphRAG 跑中文 demo | GraphRAG demo | [GraphRAG GitHub](https://github.com/microsoft/graphrag) |
| D31 | 周三 | Context 组装策略：哪些信息放入上下文？ | 上下文组装方案 | [Context Engineering](../agent-interview-hub/通用知识/Context%20Engineering上下文工程.md) |
| D32 | 周四 | Token 预算管理：各模块分配 + 动态调整 | Token 管理模块 | [tiktoken](https://github.com/openai/tiktoken) |
| D33 | 周五 | 多轮 RAG：对话历史 + 指代消解 + Follow-up 处理 | 多轮 RAG | [LangChain RAG Tutorial](https://python.langchain.com/docs/tutorials/rag/) |
| D34 | 周六 | 综合实战："企业文档智能问答 Agent" | 综合 RAG Agent | — |
| D35 | 周日 | 写 RAG 技术总结文档 | 总结文档 | — |

---

## 第6周：LangGraph 框架精通

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D36 | 周一 | State / Node / Edge 核心概念，跑通 Quick Start | 基础 demo | [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/) |
| D37 | 周二 | 用 LangGraph 重构 ReAct Agent | LangGraph ReAct | [LangGraph Quick Start](https://langchain-ai.github.io/langgraph/tutorials/introduction/) |
| D38 | 周三 | Supervisor 多 Agent：LangGraph 实现 | Supervisor Agent | [LangGraph Multi-Agent](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/) |
| D39 | 周四 | Human-in-the-Loop：interrupt() + 审批节点 | HITL Agent | [LangGraph HITL](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) |
| D40 | 周五 | Checkpointing（中断恢复）+ Streaming（流式输出） | 持久化 Agent | [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/) |
| D41 | 周六 | 项目："代码审查 Agent"（读代码→分析→建议→确认） | 代码审查 Agent | [LangChain 深度解析](../agent-interview-hub/通用知识/LangChain与LangGraph深度解析.md) |
| D42 | 周日 | 整理 LangGraph Pattern 代码模板 | 代码模板 | — |

---

## 第7周：MCP + 工具生态

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D43 | 周一 | MCP 架构理解：Host→Client→Server，跑通官方 demo | MCP demo | [MCP 官方文档](https://modelcontextprotocol.io/) |
| D44 | 周二 | 开发自定义 MCP Server（文件管理工具） | MCP Server 代码 | [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) |
| D45 | 周三 | MCP + LangChain/LangGraph 集成，权限控制 | 集成方案 | [MCP 与工具生态](../agent-interview-hub/通用知识/MCP与工具生态.md) |
| D46 | 周四 | CrewAI 上手：角色+目标+工具+Task | CrewAI demo | [CrewAI 文档](https://docs.crewai.com/) |
| D47 | 周五 | Dify 搭建 RAG 应用 + A2A 协议了解 | Dify RAG | [Dify 文档](https://docs.dify.ai/) / [Agent 框架全景](../agent-interview-hub/通用知识/Agent框架全景.md) |
| D48 | 周六 | 框架选型对比：LangGraph vs CrewAI vs Dify | 对比文档 | [Agent 框架全景](../agent-interview-hub/通用知识/Agent框架全景.md) |
| D49 | 周日 | 复习 + 整理 MCP 最佳实践 | 最佳实践笔记 | — |

---

## 第8周：安全 + 评估 + 可观测性

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D50 | 周一 | Prompt Injection 攻防：直接注入/间接注入/越狱 | 攻击演示 | [Agent 安全与评估体系](../agent-interview-hub/通用知识/Agent安全与评估体系.md) |
| D51 | 周二 | Guardrails：输入过滤 + 工具调用拦截 + 输出脱敏 | Guardrails 代码 | [Guardrails AI](https://www.guardrailsai.com/) / [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) |
| D52 | 周三 | Agent 评估：任务完成率/步骤效率/工具准确率 + Golden Test Set | 评估方案 | [LangSmith](https://docs.smith.langchain.com/) |
| D53 | 周四 | LLM-as-Judge + LangSmith/LangFuse 接入 | 自动评分系统 | [LangFuse](https://langfuse.com/) |
| D54 | 周五 | 成本优化：语义缓存 + 模型路由 + Prompt 精简 | 成本优化方案 | [GPTCache](https://github.com/zilliztech/GPTCache) |
| D55 | 周六 | 为之前的 Agent 接入安全护栏 + 评估 + 监控 | 完整 Agent 系统 | — |
| D56 | 周日 | 写 Agent 安全 Checklist | 安全 Checklist | — |

---

## 第9周：部署 + 生产化

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D57 | 周一 | FastAPI 封装 Agent 为 REST API + WebSocket 流式 | API 服务 | [FastAPI 文档](https://fastapi.tiangolo.com/) |
| D58 | 周二 | Docker 化：Dockerfile + docker-compose（Agent+Redis+向量库） | Docker 部署 | [Docker 文档](https://docs.docker.com/) |
| D59 | 周三 | 多模型路由：统一 LLM 抽象层 + 动态切换 | 模型路由模块 | [LiteLLM](https://github.com/BerriAI/litellm) |
| D60 | 周四 | 生产级记忆：Redis 短期 + PostgreSQL+pgvector 长期 | 生产记忆系统 | [pgvector](https://github.com/pgvector/pgvector) |
| D61 | 周五 | Agentic Coding 工具了解（Claude Code/Cursor 架构） | 学习笔记 | [Agentic Coding](../agent-interview-hub/通用知识/Agentic%20Coding与AI编程工具.md) |
| D62 | 周六 | 综合部署：项目服务化 + Docker + 监控 | 完整部署方案 | — |
| D63 | 周日 | 复习 + 整理生产部署 Checklist | 部署 Checklist | — |

---

## 第10周：综合项目——从零构建完整 Agent

| 编号 | 天 | 任务 | 产出 | 参考链接 |
|:----:|----|------|------|----------|
| D64 | 周一 | 选题 + 系统设计：画架构图，定技术栈 | 设计文档 | [项目实战 01](../agent-interview-hub/项目实战/01-RAG知识问答系统.md) |
| D65 | 周二 | 用 LangGraph 编排工作流，定义 Agent+工具 | 核心编排代码 | [LangGraph Tutorial](https://langchain-ai.github.io/langgraph/tutorials/) |
| D66 | 周三 | MCP 工具集成 + 记忆系统接入 | 完整后端 | [MCP 与工具生态](../agent-interview-hub/通用知识/MCP与工具生态.md) |
| D67 | 周四 | 安全护栏 + 评估测试 + Bug 修复 | 安全+测试 | [Agent 安全](../agent-interview-hub/通用知识/Agent安全与评估体系.md) |
| D68 | 周五 | Docker 部署 + API 文档 | 可部署服务 | — |
| D69 | 周六 | README（架构图+使用说明+效果展示）+ GitHub 发布 | GitHub 仓库 | — |
| D70 | 周日 | 演示录制 + 项目复盘 | ✅ 完成 | [实操考题](../agent-interview-hub/项目实战/实操考题/) |

---

## 进度总览

```
D01-D07   ▸ 第1周  LLM API + Function Calling 上手
D08-D14   ▸ 第2周  Agent 设计模式——纯代码手写
D15-D21   ▸ 第3周  多 Agent + 记忆系统
D22-D28   ▸ 第4周  RAG 全链路
D29-D35   ▸ 第5周  RAG 进阶 + Context Engineering
D36-D42   ▸ 第6周  LangGraph 框架精通
D43-D49   ▸ 第7周  MCP + 工具生态
D50-D56   ▸ 第8周  安全 + 评估 + 可观测性
D57-D63   ▸ 第9周  部署 + 生产化
D64-D70   ▸ 第10周 综合项目——从零构建完整 Agent
```

---

## 核心学习链接速查

### 本仓库文档

| 文档 | 链接 |
|------|------|
| Agent 核心概念与设计模式 | [链接](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) |
| RAG 核心知识与面试题 | [链接](../agent-interview-hub/通用知识/RAG核心知识与面试题.md) |
| Agentic RAG 与 GraphRAG | [链接](../agent-interview-hub/通用知识/Agentic%20RAG与GraphRAG深度解析.md) |
| Function Calling 专题 | [链接](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md) |
| MCP 与工具生态 | [链接](../agent-interview-hub/通用知识/MCP与工具生态.md) |
| LangChain 与 LangGraph | [链接](../agent-interview-hub/通用知识/LangChain与LangGraph深度解析.md) |
| Context Engineering | [链接](../agent-interview-hub/通用知识/Context%20Engineering上下文工程.md) |
| Agent 安全与评估体系 | [链接](../agent-interview-hub/通用知识/Agent安全与评估体系.md) |
| Agent 框架全景 | [链接](../agent-interview-hub/通用知识/Agent框架全景.md) |
| Agentic Coding | [链接](../agent-interview-hub/通用知识/Agentic%20Coding与AI编程工具.md) |
| 八股文完整答案集 | [链接](../agent-interview-hub/通用知识/八股文完整答案集.md) |

### 外部资源

| 类别 | 资源 | 链接 |
|------|------|------|
| 必读博客 | Lilian Weng - LLM Agents | https://lilianweng.github.io/posts/2023-06-23-agent/ |
| 必读博客 | Anthropic - Building Effective Agents | https://www.anthropic.com/engineering/building-effective-agents |
| 必读博客 | Cohere - Tool Use Guide | https://docs.cohere.com/docs/tool-use |
| 框架文档 | LangGraph 官方 | https://langchain-ai.github.io/langgraph/ |
| 框架文档 | MCP 官方 | https://modelcontextprotocol.io/ |
| 框架文档 | CrewAI | https://docs.crewai.com/ |
| 课程 | 吴恩达 - AI Agents in LangGraph | https://www.deeplearning.ai/short-courses/ |
| 工具 | LangSmith（可观测性） | https://docs.smith.langchain.com/ |
| 工具 | LangFuse（可观测性） | https://langfuse.com/ |
| 工具 | vLLM | https://github.com/vllm-project/vllm |
| 工具 | Dify | https://github.com/langgenius/dify |
| 论文 | ReAct | https://arxiv.org/abs/2210.03629 |
| 论文 | Reflexion | https://arxiv.org/abs/2303.11366 |

---

> **执行建议：** 每天先把代码写出来再去看理论，比例保持 6:4。周末不要赶进度，用来巩固和做项目。
