# 第 022 课：节点化 Workflow 重构

## 1. 这一阶段改了什么

这次不是新增一个小功能，而是重构 workflow 的运行结构。

原来：

```text
ResearchWorkflow.run()
  一个长函数串完所有步骤
```

现在：

```text
ResearchWorkflow.run()
  -> PlanningNode
  -> RetrievalNode
  -> ReadingNode
  -> EvidenceExtractionNode
  -> VerificationNode
  -> ReportWritingNode
  -> EvaluationNode
```

新增文件：

```text
src/researchos/runtime/state.py
src/researchos/runtime/nodes.py
```

新增 artifact：

```text
traces/workflow_trace.json
```

## 2. 为什么要做节点化

长函数的问题是：

- 每个阶段的职责混在一起。
- 后续接 LangGraph 时不好迁移。
- 节点耗时、产物、事件不好单独记录。
- 单个节点替换成本高。

节点化后，每个节点只负责一件事：

| 节点 | 职责 |
| --- | --- |
| PlanningNode | 生成 research plan |
| RetrievalNode | 检索最相关文档片段 |
| ReadingNode | 记录读取阶段事件 |
| EvidenceExtractionNode | 构造 evidence 和 claim |
| VerificationNode | 校验证据是否支持 claim |
| ReportWritingNode | 写 report 和 evidence artifacts |
| EvaluationNode | 写 eval artifacts |

## 3. WorkflowState 是什么

`WorkflowState` 是节点之间共享的运行上下文。

它保存：

```text
run
plan
retrieved_chunk
source
evidence
claim
verification
report
```

可以理解为：

```text
一次 research run 在 workflow 内部流动的“状态包”
```

节点读取它，也会把自己的产物写回它。

## 4. NodeResult 是什么

`NodeResult` 是每个节点执行后的标准结果。

它包含：

```text
node_name
status
step_name
completed_steps
event_type
payload
artifacts
```

workflow 用它统一做三件事：

```text
更新 run 状态
写事件 event
写 workflow trace
```

这样节点只关心业务逻辑，workflow 负责统一推进状态。

## 5. workflow_trace.json 有什么用

每次 run 会写：

```text
traces/workflow_trace.json
```

里面记录每个节点：

```text
node
status
step_name
duration_ms
event_type
artifacts
```

它的价值：

- 调试时知道卡在哪个节点。
- 面试演示时能展示完整执行路径。
- 后续做性能分析可以看节点耗时。
- 接 LangGraph 后可以对照每个 graph node 的执行结果。

## 6. 和 LangGraph 的关系

当前还没有正式接 LangGraph，但结构已经更接近 LangGraph：

```text
WorkflowState  -> Graph State
WorkflowNode   -> Graph Node
NodeResult     -> Node output / trace metadata
```

这一步的意义是降低后续迁移成本。

不是直接上 LangGraph，是因为我们先要把自己的业务边界拆清楚。

## 7. 面试怎么讲

可以这样说：

> 一开始 workflow 是一个线性长函数，适合快速做 MVP，但后续接 LangGraph 和多 Agent 节点时会变得难维护。所以我把 workflow 重构成节点化结构，每个节点只负责 planning、retrieval、verification、report writing 等单一职责。节点之间通过 WorkflowState 传递上下文，每个节点返回 NodeResult，workflow 统一更新 run 状态、写事件和 trace。这样既保留了原来的 API 行为，又为后续图编排做了工程铺垫。

这个回答能体现：

- 你知道 MVP 和工程化结构的区别。
- 你会识别长函数的问题。
- 你能把 Agent 流程拆成节点。
- 你理解 LangGraph 不是魔法，而是状态和节点的编排。
