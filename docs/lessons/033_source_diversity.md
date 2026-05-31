# 第 033 课：Source Diversity 与多来源证据控制

## 1. 为什么需要 source diversity

RAG top-k 有一个常见问题：

```text
top-k 全部来自同一个文档
```

这会让报告看起来有多个证据，实际却只是同一个来源的多个片段。

复杂研究任务通常需要多来源交叉支撑，所以要控制最终证据来源的多样性。

## 2. 本课新增了什么

新增：

```text
SourceDiversityPolicy
```

配置项：

```env
RESEARCHOS_RETRIEVAL_MAX_CHUNKS_PER_SOURCE=0
```

默认 `0` 表示不限制，保持旧行为。

如果设置为：

```env
RESEARCHOS_RETRIEVAL_MAX_CHUNKS_PER_SOURCE=1
```

最终 top-k 中同一个文档最多只能出现一个 chunk。

## 3. 当前 retrieval 流程

现在流程是：

```text
retriever 召回 candidates
reranker 重排 reranked_candidates
source diversity 选择最终 top-k
```

也就是：

```text
candidates -> reranked_candidates -> final evidence chunks
```

source diversity 放在 reranker 后面，因为它应该基于已经排序过的候选结果做最终选择。

## 4. diagnostics 里有什么

`sources/retrieval_diagnostics.json` 新增：

```text
source_diversity.enabled
source_diversity.max_chunks_per_source
source_diversity.selected_source_count
```

这样可以看出本次 run 是否启用了多来源控制。

## 5. 面试怎么说

可以这样回答：

> 我在 reranker 后面加了一层 source diversity policy。retriever 负责召回候选，reranker 负责排序，diversity policy 负责限制最终 top-k 中每个来源最多出现几个 chunk。这样可以避免 evidence bundle 被同一个文档的多个片段占满，提高证据来源多样性。默认不开启限制，保证兼容；需要更强多来源约束时，可以通过配置启用。

这个回答体现：

- 你知道 top-k 分数高不代表来源足够多样。
- 你理解召回、排序、来源控制是三个不同职责。
- 你能说明为什么默认关闭、配置启用。
