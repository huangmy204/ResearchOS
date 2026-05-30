# 面试讲解 001：Research Run 运行链路

## 一句话介绍项目

ResearchOS 是一个 evidence-first、run-oriented 的 Deep Research Agent Runtime，用来把复杂研究任务拆成可追踪、可恢复、可审计的运行流程，并输出带证据链和引用校验的结构化报告。

面试里可以这样说：

> 我做的不是一个简单 RAG 问答 Demo，而是一个面向长任务研究流程的 Agent Runtime。它把每次研究任务抽象成一个 research run，系统会记录状态、事件、证据、引用关系和最终报告，让整个研究过程可以追踪和复盘。

## 为什么是 run-oriented 架构

普通问答系统通常是“一问一答”，但 deep research 任务不是一次模型调用能完成的。它需要规划、搜索、阅读、抽取证据、校验引用、写报告和评审。

所以系统把一次任务建模成 `ResearchRun`。

这个设计解决三个问题：

1. 长任务可追踪：前端可以查询 run 状态，也可以订阅事件流。
2. 结果可审计：证据、claim、citation、report 都落到 run 目录下。
3. 后续可扩展：未来可以接 LangGraph、数据库、队列、沙箱和评测系统。

## 当前请求链路

当前 MVP 的主链路是：

```text
POST /v1/research-runs
  -> routes_runs.create_research_run
  -> RunStore.create
  -> Workspace.ensure_run_layout
  -> EventStore.append("run.created")
  -> asyncio.create_task(ResearchWorkflow.run)
  -> 返回 run_id / events_url / artifacts_url
```

这条链路里，API 不直接生成报告，而是先创建 run，再把后台 workflow 启动起来。

这样做的原因是：research run 是长任务，HTTP 请求不应该一直阻塞到报告生成完成。

## Workflow 运行链路

当前 workflow 是 deterministic MVP，也就是确定性的模拟流程。

状态顺序：

```text
created
planning
searching
reading
extracting_evidence
verifying
writing
reviewing
completed
```

每进入一个阶段，workflow 会做两件事：

1. 更新 run 状态。
2. 写入一条 event。

核心方法是 `_advance`：

```text
RunStore.update(...)
EventStore.append(...)
```

这让状态查询和事件流保持一致。

## Store 分工

### `Workspace`

负责 run 的目录结构和路径安全。

目录形状：

```text
workspace/tenants/<tenant_id>/users/<user_id>/sessions/<session_id>/runs/<run_id>/
```

面试表达：

> Workspace 是隔离边界。每个 run 的输入、证据、输出、trace、eval 都放在自己的目录里，避免不同任务互相污染。

### `RunStore`

负责创建、读取、更新 run 状态。

当前 MVP 用文件保存到：

```text
inputs/task.json
```

面试表达：

> RunStore 是任务状态中心。后续如果接 Postgres，只需要替换 Store 实现，API 和 workflow 的抽象可以保持不变。

### `EventStore`

负责追加事件。

当前写入：

```text
traces/events.jsonl
```

面试表达：

> EventStore 让系统具备可观测性。前端 timeline、调试、审计和失败复盘都依赖事件日志。

### `ArtifactStore`

负责写入、列出、读取产物。

当前产物包括：

```text
outputs/report.md
outputs/report.json
outputs/executive_summary.md
evidence/sources.json
evidence/evidence.json
evidence/claims.json
evidence/evidence_graph.json
evidence/citation_verification.json
evals/eval_result.json
evals/eval_report.md
```

面试表达：

> ArtifactStore 把 Agent 的中间结果和最终结果都沉淀下来。这样报告不是凭空生成的，而是能追溯到 sources、evidence 和 claims。

## SSE 怎么讲

SSE 是 Server-Sent Events，适合服务端持续推送长任务进度。

当前接口：

```text
GET /v1/research-runs/{run_id}/events
```

返回事件格式：

```text
id: 1
event: plan.created
data: {...}
```

面试表达：

> 我用 SSE 做 run timeline，因为 research task 是长任务。相比 WebSocket，SSE 更轻量，浏览器原生支持，服务端只需要持续 yield 事件流。

## 为什么当前 workflow 是 deterministic MVP

当前 workflow 没有接真实 LLM 和搜索，而是用固定数据模拟完整流程。

这是有意设计：

1. 先验证 API 契约。
2. 先验证状态流转。
3. 先验证 workspace 和 artifact 结构。
4. 先验证 SSE 和查询接口。
5. 降低早期调试复杂度。

面试表达：

> 我先做 deterministic workflow，是为了把 runtime contract 跑通。Agent 的智能部分后续可以替换，但 run lifecycle、event streaming、artifact persistence 这些工程边界要先稳定。

## 30 秒版回答

ResearchOS 是一个面向 deep research 的 Agent Runtime。我把每次研究任务抽象成一个 research run，通过 FastAPI 创建任务，然后后台 workflow 按规划、搜索、阅读、证据抽取、引用校验、写报告的阶段推进。系统会用 RunStore 记录状态，用 EventStore 记录事件流，用 ArtifactStore 保存证据和报告，用 Workspace 保证每个任务隔离。这样项目不是简单返回一个答案，而是把研究过程做成可追踪、可审计、可扩展的运行系统。

## 2 分钟版回答

这个项目的核心是 run-oriented 和 evidence-first。Deep research 任务通常是长流程，不适合一次 HTTP 请求里直接等模型生成答案，所以我设计了 `ResearchRun` 作为核心对象。

用户调用 `POST /v1/research-runs` 后，API 会创建 run，初始化 workspace，记录 `run.created` 事件，然后用后台任务启动 workflow。workflow 会按 planning、searching、reading、extracting_evidence、verifying、writing、reviewing、completed 推进。每一步都会更新状态，并写入事件，所以前端可以通过 SSE 看到 timeline。

结果层面，系统会把 sources、evidence、claims、citation verification 和 report 都保存为 artifact。这样报告里的结论能追溯到证据，而不是只有一段自然语言回答。

当前 MVP 用 deterministic workflow，是为了先稳定工程边界。后续接 LangGraph、真实搜索、LLM verifier、Docker sandbox、evaluation harness 时，可以复用同一套 run lifecycle、event streaming 和 artifact API。

## 深入追问版

如果面试官问“为什么不用普通同步接口”：

> 因为 deep research 是长任务，可能需要多轮搜索和校验。同步接口容易超时，也无法实时展示进度。run-oriented 架构可以把创建任务、查询状态、订阅事件、下载产物拆开。

如果面试官问“为什么先用文件存储”：

> MVP 阶段文件存储更容易验证数据结构和目录隔离。Store 层已经做了抽象，后续替换成 Postgres、Redis 或对象存储时，不需要重写 API 层。

如果面试官问“怎么保证结果可审计”：

> 每个 run 都会保存 evidence、claim、citation verification、report 和 event trace。最终报告不是孤立文本，可以回溯到证据图和事件日志。

如果面试官问“这个项目最有价值的工程点是什么”：

> 我认为是把 Agent 从聊天式回答提升成可运行的工作流系统。重点不是单次生成，而是状态管理、事件流、证据链、artifact 管理和评测闭环。
