# 我的 Agent 进阶历程

> 基于 [agent-interview-hub](../agent-interview-hub/) 整理的学习计划。**主攻 Agent 开发方向**，跳过 LLM 训练/微调/推理优化。

---

## 两条学习路径

| 路径 | 文档 | 时长 | 适合人群 |
|------|------|:----:|------|
| 🎯 **Agent 开发专项（推荐）** | [Agent开发专项学习计划](./Agent开发专项学习计划.md) | 10周 | 聚焦 Agent 开发，用 API 不训练模型 |
| 📚 完整 AI Agent 工程师 | 见下方六阶段 | 16周 | 全栈方向，含微调/RLHF/推理优化 |

---

## Agent 开发者能力模型

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

## Agent 开发专项（10周速览）

| 阶段 | 周期 | 主题 |
|------|------|------|
| 一 | 第1周 | LLM 基础认知 + API 上手 + Function Calling |
| 二 | 第2-3周 | Agent 设计模式：纯代码手写 ReAct / Plan-Execute / Reflection |
| 三 | 第4-5周 | RAG 全链路 + Context Engineering |
| 四 | 第6-7周 | LangGraph 框架 + MCP 协议实战 |
| 五 | 第8-9周 | 生产级能力：记忆 / 安全 / 评估 / 部署 |
| 六 | 第10周 | 综合项目：从零构建完整 Agent 应用 |

👉 **详细每日计划见：[Agent开发专项学习计划](./Agent开发专项学习计划.md)**

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [Agent开发专项学习计划](./Agent开发专项学习计划.md) | 🔥 **主推**：Agent 开发专项，10周 |
| [每日学习计划](./每日学习计划.md) | 完整版 16 周每日计划 |
| [01-基础理论篇](./01-基础理论篇.md) | Transformer + LLM 基础 |
| [02-核心技能篇](./02-核心技能篇.md) | Prompt + RAG + Agent 设计模式 |
| [03-框架实战篇](./03-框架实战篇.md) | LangGraph + MCP + CrewAI + Dify |
| [04-进阶深入篇](./04-进阶深入篇.md) | 微调 + RLHF + 推理优化 + 安全 |
| [05-项目实战篇](./05-项目实战篇.md) | 3 个项目 + 6 道实操考题 |
| [06-面试冲刺篇](./06-面试冲刺篇.md) | 高频题 + 系统设计 + 大厂面经 |
| [学习资源索引](./学习资源索引.md) | 所有学习链接汇总 |

---

## 知识体系速览

```
AI Agent 工程师知识体系
│
├── 🧱 基础层
│   ├── Transformer 架构与注意力机制
│   ├── LLM 原理 / Tokenization / Embedding
│   └── Prompt Engineering 基础
│
├── 🔧 核心层
│   ├── Agent 设计模式（ReAct / Plan-and-Execute / Multi-Agent）
│   ├── RAG 全链路（检索 / 分块 / 重排 / 生成）
│   ├── Function Calling / Tool Use
│   ├── MCP（Model Context Protocol）
│   ├── 主流框架（LangChain / LangGraph / AutoGen）
│   └── Context Engineering 上下文工程
│
├── 🚀 进阶层
│   ├── Agentic RAG / GraphRAG
│   ├── Agentic Coding 与 AI 编程工具
│   ├── 模型微调 / 推理优化 / 量化部署
│   └── Agent 安全、评估与对齐
│
└── 💼 实战层
    ├── 系统设计与项目经验
    ├── 大厂岗位要求解读
    └── 面试技巧与真实面经
```

---

## 核心学习资源入口

| 类别 | 资源 | 路径 |
|------|------|------|
| 学习路线图 | Agent 工程师学习路线图 | [链接](../agent-interview-hub/Agent工程师学习路线图.md) |
| 核心概念 | Agent 核心概念与设计模式 | [链接](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md) |
| 框架 | Agent 框架全景 | [链接](../agent-interview-hub/通用知识/Agent框架全景.md) |
| RAG | RAG 核心知识与面试题 | [链接](../agent-interview-hub/通用知识/RAG核心知识与面试题.md) |
| 面试 | 八股文完整答案集（69题） | [链接](../agent-interview-hub/通用知识/八股文完整答案集.md) |
| 面经 | 高频拷打题 - 牛客热帖 | [链接](../agent-interview-hub/通用知识/高频拷打题-牛客热帖.md) |
| 安全 | Agent 安全与评估体系 | [链接](../agent-interview-hub/通用知识/Agent安全与评估体系.md) |
| 推理 | 大模型推理优化与部署 | [链接](../agent-interview-hub/通用知识/大模型推理优化与部署.md) |
| 微调 | 模型微调完全指南 | [链接](../agent-interview-hub/通用知识/模型微调完全指南.md) |
| 上下文 | Context Engineering 上下文工程 | [链接](../agent-interview-hub/通用知识/Context Engineering上下文工程.md) |
| MCP | MCP 与工具生态 | [链接](../agent-interview-hub/通用知识/MCP与工具生态.md) |
| Function Call | Function Calling 与 Tool Use 专题 | [链接](../agent-interview-hub/通用知识/Function Calling与Tool Use专题.md) |

---

## 推荐阅读顺序

1. 先看 [Agent工程师学习路线图](../agent-interview-hub/Agent工程师学习路线图.md)，了解全局
2. 通读 [Agent 核心概念与设计模式](../agent-interview-hub/通用知识/Agent核心概念与设计模式.md)
3. 深入 [RAG 核心知识](../agent-interview-hub/通用知识/RAG核心知识与面试题.md) 和 [LangChain/LangGraph](../agent-interview-hub/通用知识/LangChain与LangGraph深度解析.md)
4. 掌握 [Function Calling](../agent-interview-hub/通用知识/Function%20Calling与Tool%20Use专题.md) 和 [MCP](../agent-interview-hub/通用知识/MCP与工具生态.md)（2025 高频新考点）
5. 刷 [八股文完整答案集](../agent-interview-hub/通用知识/八股文完整答案集.md)
6. 针对目标公司看对应面经（`agent-interview-hub/` 下各公司目录）
7. 最后用 [高频拷打题](../agent-interview-hub/通用知识/高频拷打题-牛客热帖.md) 查漏补缺

---

## 每日学习建议

| 时间段 | 工作日 | 周末 |
|--------|--------|------|
| 早上 | 30min 论文/博客阅读 | 2h 深度学习/实践 |
| 午休 | 20min 刷面试题 | — |
| 晚上 | 2-3h 代码实践 | 4-6h 项目开发 |
| 睡前 | 15min 复习笔记 | 30min 总结 |

---

## GitHub 仓库组织建议

```
your-github/
├── ai-agent-learning/          # 学习笔记和实验
│   ├── transformer/            # Transformer 实现
│   ├── tokenizer/              # BPE 实现
│   ├── rag-experiments/        # RAG 实验
│   └── agent-patterns/         # Agent 模式实现
├── rag-qa-system/              # 项目一：RAG 知识问答
├── multi-agent-research/       # 项目二：多 Agent 研究助手
├── production-agent/           # 项目三：生产级 Agent
└── interview-notes/            # 面试题整理
```

---

> 完整学习资源索引见 [学习资源索引](./学习资源索引.md)
>
> 最后更新：2025年
