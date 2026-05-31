# 第 027 课：LangGraph 条件边与证据不足分支

## 1. 为什么要加条件边

顺序 workflow 的问题是：每个节点都会执行。

但真实 Agent 不应该在没有证据时继续抽取 claim、做 citation verification、写“有依据”的报告。

所以 LangGraph 这一步加入第一个条件分支：

```text
retrieval
  -> 有证据：reading -> evidence_extraction -> verification -> report_writing
  -> 无证据：insufficient_evidence_report
```

这就是图编排比普通顺序函数更有价值的地方。

## 2. 条件判断用什么状态

判断依据是：

```text
WorkflowState.retrieved_chunk
```

在 `RetrievalNode` 中：

```text
检索到 chunk    -> state.retrieved_chunk = chunk
没有检索到结果  -> state.retrieved_chunk = None
```

LangGraph 的条件函数只看这个状态，不直接重新检索。

## 3. 新增节点

新增：

```text
InsufficientEvidenceReportNode
```

位置：

```text
src/researchos/runtime/nodes.py
```

它负责生成三类产物：

```text
outputs/report.md
outputs/report.json
outputs/executive_summary.md
```

但不会生成 claim、evidence、citation verification。

原因是：没有证据时继续生成 claim，会制造“伪证据链”。

## 4. Evaluation 怎么变化

`EvaluationNode` 现在会检查：

```text
state.evidence is not None
```

有证据时：

```text
verdict = pass
```

无证据时：

```text
verdict = needs_evidence
retrieval_recall = 0.0
claim_support_rate = 0.0
```

这让评测结果能反映真实质量，而不是所有 run 都默认满分。

## 5. 为什么只改 LangGraph 路径

默认 `sequential` 仍保持原来的 MVP 行为。

这一步的目标不是大范围重构，而是先证明：

```text
LangGraph 可以根据运行状态选择不同节点路径。
```

等这个分支稳定后，再考虑把更多复杂编排迁移进去。

## 6. 面试怎么说

可以这样回答：

> 我在 LangGraph engine 中加入了第一个条件边。检索节点执行后，系统会根据 `WorkflowState.retrieved_chunk` 判断是否找到了证据。如果有证据，就继续阅读、抽取证据、验证引用、写报告；如果没有证据，就跳到 `InsufficientEvidenceReportNode`，生成证据不足报告，并在评测中标记 `needs_evidence`。这样避免了没有证据还硬生成 claim 的问题，也体现了 LangGraph 的图编排价值。

这个回答重点体现：

- 你理解 Agent workflow 不是固定流水线。
- 你知道证据不足时应该停止生成“伪结论”。
- 你能说明 LangGraph 条件边和 `WorkflowState` 的关系。
