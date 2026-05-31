# 第 035 课：Retrieval Quality Gate 与 Agentic Workflow 分支

## 1. 为什么需要 quality gate

普通 RAG 流水线经常是：

```text
检索 -> 抽取证据 -> 写报告
```

但如果检索质量不够，继续写报告会产生两个问题：

- 证据数量太少，报告支撑不足。
- 系统可能为了完成任务而生成看似合理但证据不足的结论。

quality gate 的作用是：

```text
先判断检索结果是否足够，再决定下一步走哪条路径。
```

这就是从固定 RAG workflow 走向 agentic workflow 的关键一步。

## 2. 本课新增了什么

新增配置：

```env
RESEARCHOS_RETRIEVAL_MIN_EVIDENCE_COUNT=1
```

默认值是 1，不改变旧行为。

如果设置为 2，而本次 run 只召回 1 条最终证据，quality gate 会失败。

## 3. LangGraph 怎么使用 quality gate

`RetrievalNode` 会写入：

```text
state.retrieval_quality
```

格式类似：

```json
{
  "passed": false,
  "min_evidence_count": 2,
  "retrieved_count": 1,
  "reason": "retrieved_count_below_minimum:1<2"
}
```

LangGraph 在 `retrieval` 后读取这个状态：

```text
quality gate pass -> reading
quality gate fail -> insufficient_evidence_report
```

## 4. diagnostics 和 eval 中有什么变化

`sources/retrieval_diagnostics.json` 新增：

```text
quality_gate
```

`evals/eval_result.json` 新增：

```text
retrieval_quality_gate_passed
dimensions.retrieval.quality_gate
```

这样可以看到本次 run 是不是因为质量门失败而进入证据不足路径。

## 5. 面试怎么说

可以这样回答：

> 我在 retrieval 后加入了 quality gate。检索节点会根据最终 evidence chunk 数量生成质量判断，LangGraph 根据这个判断决定是否继续阅读、抽取和写报告。如果检索结果低于最小证据数量，workflow 会进入 insufficient evidence 分支，而不是硬生成报告。这个设计把 RAG 的质量指标接回了 agentic workflow，让系统能根据中间结果改变执行路径。

这个回答体现：

- 你不是只做固定流水线。
- 你知道 RAG 需要质量门控。
- 你能把 diagnostics、eval metrics 和 LangGraph 分支串起来。
