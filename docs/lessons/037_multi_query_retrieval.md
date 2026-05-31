# 037 多查询检索策略

## 为什么需要多查询

用户提出的问题通常不是最适合检索的 query。

例如：

```text
原问题：大模型生成法律引用时有什么风险？
```

这个问题可以拆成几种检索视角：

- 原问题：保留用户真实意图。
- 重写问题：补充领域词，例如 citation、verification、unsupported。
- 子问题：把复杂问题拆成更小的检索目标。
- 问题升阶：从具体问题升到背景、上下文、概览层面。

多查询检索的目标是提高召回率，也就是尽量把可能有用的材料先找出来。

## 当前实现

主要文件：

```text
src/researchos/retrieval/query_plan.py
src/researchos/retrieval/multi_query.py
src/researchos/runtime/nodes.py
```

`query_plan.py` 负责生成 query variants：

- `active`：当前实际 query。第一次是原问题；重试时是改写后的问题。
- `original`：用户原始问题。
- `subquestion`：把问题切成较小片段。
- `upshift`：加入 overview、background、context 这类上位视角。

`multi_query.py` 负责执行多路检索：

```text
query variants -> retriever.retrieve 多次 -> 合并候选 -> 按 chunk 去重 -> 交给 reranker
```

`nodes.py` 里的 `RetrievalNode` 负责把这两层串起来。

## 为什么不把多查询写进 Retriever

因为 retriever 应该保持简单：

```text
一个 query + 一组 documents -> 一批 RetrievedChunk
```

多查询属于检索编排策略，不属于底层检索器本身。

这样设计的好处：

- keyword、BM25、embedding retriever 都可以复用同一套 multi-query 逻辑。
- 后续换向量库时，不需要重写 query planning。
- 单元测试更清晰：retriever 测相关性，multi-query 测合并去重。

## 几种策略对比

| 策略 | 作用 | 风险 |
| --- | --- | --- |
| 原问题检索 | 保留用户意图 | 表达不适合检索时召回差 |
| 规则重写 | 稳定补充关键词 | 泛化能力有限 |
| LLM 重写 | 语义理解更强 | 成本更高，可能漂移 |
| 子问题检索 | 覆盖复杂问题的不同部分 | 子问题切错会引入噪声 |
| 问题升阶 | 找背景、概览、定义类材料 | 可能召回太宽 |
| HyDE | 先生成假想答案再检索 | 需要控制幻觉和成本 |

当前项目先实现规则版 multi-query，是为了让链路稳定可测。后续可以把 `QueryPlanner` 换成 LLM planner。

## 和 query rewrite 的关系

multi-query 和 query rewrite 不是一回事。

multi-query 是一次检索尝试内部的多个视角：

```text
retrieval attempt 1:
  active/original/subquestion/upshift
```

query rewrite 是一次检索失败后的反馈动作：

```text
retrieval failed -> query_rewrite -> retrieval attempt 2
```

所以完整链路是：

```text
第一次多查询检索
  -> 质量门失败
  -> 改写 query
  -> 第二次多查询检索
  -> 继续生成或证据不足降级
```

## 面试表达

可以这样说：

“我们没有把 RAG 简化成一次向量检索，而是在 retrieval node 里加入了 query planning。一次检索会同时使用原问题、当前问题、子问题和上位问题生成多个 query variants，再把结果合并去重后交给 reranker。这样底层 retriever 仍然保持单一职责，而检索策略可以独立演进。后续如果要接 LLM query planner 或 HyDE，只需要替换 `QueryPlanner`，不需要重写整个 workflow。”
