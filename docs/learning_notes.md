# ResearchOS 学习约定

## 构建节奏

1. 每次只推进一个小目标，例如一个模型、一个 Store、一个 API 路由或一个测试。
2. 写代码前先说明本次要解决的问题。
3. 写完后先解释关键代码，再继续下一步。
4. 不一次性铺太多文件，除非它们属于同一个最小闭环。
5. 功能代码、测试、文档尽量分成清晰的小批次。

## 面试导向

1. 每个阶段都要沉淀三件事：技术理解、项目表达、Git 操作点。
2. 技术理解回答“这个模块怎么工作”。
3. 项目表达回答“为什么这样设计，以及它解决了什么问题”。
4. Git 操作点回答“这次改动在版本管理里应该如何看、如何提交、如何回滚”。
5. 面试文档放在 `docs/interview/`，用于整理可直接复述的项目讲法。

## 长期技术方向

1. 项目后续要从普通 RAG workflow 演进到 agentic workflow。
2. agentic workflow 的重点不是简单串联节点，而是让节点具备规划、工具选择、反思、重试、分支和循环能力。
3. 后续讲解 LangGraph、RAG、检索、验证和报告生成时，都要说明它们如何服务于 agentic workflow。
4. 面试表达里要能讲清楚：当前 MVP 是稳定工程底座，后续 agentic workflow 是在这个底座上增加自主决策能力。

## 讲义风格

1. 全部使用中文。
2. 重点讲技术知识点，少写过程性描述。
3. 优先解释：概念、代码结构、为什么这样设计、常见坑。
4. 每篇讲义尽量短，围绕一个主题。
5. Git 教程穿插在实际操作里，不做空泛介绍。

## 当前学习路线

1. Python 项目结构与依赖管理。
2. FastAPI 的应用、路由、依赖注入。
3. Pydantic 数据模型。
4. 文件型 Store 与 workspace 隔离。
5. SSE 事件流。
6. Artifact API 与路径安全。
7. 测试与 Git 小步提交。
8. RAG 检索、证据图、引用校验与评测。
9. Model Router 与 LLM Client。
10. 真实 LLM API 配置、密钥管理与错误处理。
11. `.env` 本地密钥文件与环境变量优先级。
12. LLM writer、prompt 约束与 fallback 降级。
13. LLM verifier、结构化 JSON 输出与证据支持判断。
14. LLM planner、结构化计划与 LangGraph 前置设计。
15. 节点化 workflow、WorkflowState、NodeResult 与 trace。
16. Workflow Trace API 与可观察性。
17. WorkflowEngine 抽象与 LangGraph 替换点。
18. 最小 LangGraph engine 与顺序图映射。
19. 通过配置切换 workflow engine。
20. LangGraph 条件边与证据不足分支。
21. RAG top-k 多证据检索与 evidence bundle。
22. RAG chunk 切分参数、overlap 与召回质量。
23. Embedding Retriever、向量表示与 cosine similarity。
24. Retrieval diagnostics、检索策略对比与可观察性。
25. LangGraph checkpoint 与复杂编排。
26. Docker 沙箱与部署。

## 文档目录

```text
docs/lessons/     技术知识点讲义
docs/interview/   面试表达与项目讲法
```
