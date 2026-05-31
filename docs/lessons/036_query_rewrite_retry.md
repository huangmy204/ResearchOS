# 036 Query Rewrite 与检索重试

## 这一步解决什么问题

普通 RAG 常见流程是：用户问题 -> 检索 -> 生成答案。问题在于，第一次检索失败不一定代表知识库没有答案，也可能是 query 表达方式不适合当前检索器。

所以这一步加入了一个很小但很关键的 agentic 能力：

```text
retrieval 质量不达标 -> query_rewrite -> retrieval 再试一次 -> 再决定继续或失败
```

这里的重点不是“字符串替换”，而是 workflow 开始具备反馈、重试和分支能力。

## 主要代码位置

```text
src/researchos/runtime/engine.py
```

负责 LangGraph 条件边：

- `retrieval` 后检查 `retrieval_quality`
- 第一次失败走 `query_rewrite`
- 改写后回到 `retrieval`
- 第二次仍失败才走 `insufficient_evidence_report`

```text
src/researchos/runtime/nodes.py
```

负责节点实现：

- `RetrievalNode` 使用 `state.retrieval_query` 作为当前检索 query
- `QueryRewriteNode` 生成新 query，并记录 retry 次数
- `InsufficientEvidenceReportNode` 在最终证据不足时生成降级报告

```text
src/researchos/retrieval/query_rewrite.py
```

负责 query 改写策略：

- 当前是 `RuleBasedQueryRewriter`
- 它根据原 query、领域词扩展、文档标题词生成新 query
- 后续可以替换成 LLM query rewriter

## 为什么先做规则改写，不直接上 LLM

面试里可以这样讲：

“我先用 rule-based query rewriter 是因为它稳定、可测试、成本低，适合验证 workflow 闭环。等流程跑通后，再把它替换成 LLM rewriter 或 hybrid rewriter。”

常见选择对比：

| 方案 | 优点 | 缺点 | 适合阶段 |
| --- | --- | --- | --- |
| 规则改写 | 稳定、便宜、容易测 | 泛化能力弱 | MVP、流程验证 |
| LLM 改写 | 表达能力强，能理解语义 | 成本高，输出不稳定，需要约束 | 中后期增强 |
| 多 query expansion | 召回更强 | 检索成本上升，需要合并去重 | 知识库较大时 |
| HyDE | 对语义检索友好 | 会生成假想答案，需要防幻觉 | embedding RAG 优化 |

当前项目选择规则改写，是为了把“失败后重试”这个 agentic workflow 机制先建立起来。

## WorkflowState 新增字段

```text
retrieval_query
query_rewrites
retrieval_retry_count
```

它们的分工：

- `retrieval_query`：当前实际用于检索的 query。第一次为空时使用原始 `run.query`。
- `query_rewrites`：记录每次改写，方便调试、评测和面试讲解。
- `retrieval_retry_count`：防止无限循环，当前只允许重试一次。

## 为什么要限制重试次数

Agentic workflow 里的循环很有用，但也危险。

如果没有限制，可能出现：

- query 一直改写但永远检索不到
- LLM agent 不断调用工具造成成本失控
- workflow 卡住，API 请求迟迟没有结果

所以当前用 `retrieval_retry_count < 1` 控制最多重试一次。后续可以改成配置项，例如：

```text
RESEARCHOS_RETRIEVAL_MAX_RETRIES=2
```

## 这和完整 RAG 的关系

这一步还不是完整 RAG 的全部，但已经进入 RAG 的关键细节区：

- chunk 切分决定候选材料粒度
- retriever 决定召回范围
- reranker 决定候选排序
- quality gate 决定证据是否够用
- query rewrite 决定失败后如何自我修正

完整 RAG 不是“接一个向量库”就结束，而是这些模块一起形成可观测、可评测、可降级的链路。

## 面试回答模板

30 秒版：

“我们的 RAG workflow 在检索后会进入质量门。如果证据数量或质量不达标，系统不会立刻生成答案，而是先进入 query rewrite 节点改写检索词，再回到 retrieval 重试一次。如果仍然不达标，就生成证据不足报告，避免强行回答导致幻觉。”

2 分钟版：

“这个设计体现了从普通 RAG 到 agentic workflow 的演进。普通 RAG 是线性的，检索一次就生成；而我们的流程在 LangGraph 中用条件边把 retrieval 后的状态分成三类：证据足够就继续 reading、extraction、verification、report writing；第一次质量不达标就进入 query_rewrite，然后回到 retrieval；如果重试后仍不达标，则进入 insufficient_evidence_report。这样既增加了自我修正能力，又通过 retry count 防止无限循环。”

深入追问：

“为什么不直接 LLM 改写 query？因为当前阶段更重视工程可控性。规则改写可以稳定复现，适合测试 workflow 机制。后续可以把 `QueryRewriter` 作为接口替换成 LLM rewriter，甚至做多 query expansion 或 HyDE，但底层 workflow 不需要重写。”
