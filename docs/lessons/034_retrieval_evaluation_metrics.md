# 第 034 课：Retrieval Evaluation 与 RAG 质量指标

## 1. 为什么要做 retrieval evaluation

RAG 的失败不一定发生在最终写报告阶段。

很多问题其实来自：

```text
没有召回相关 chunk
召回结果都来自同一个来源
reranker 排序不合理
证据数量不足
引用校验不通过
```

所以 eval 不能只看最终 markdown 写得像不像，还要评估检索阶段和证据阶段。

## 2. 本课做了什么

新增：

```text
src/researchos/evals/metrics.py
```

它把 workflow 内部评测和 dataset eval harness 的指标计算统一起来。

`evals/eval_result.json` 现在包含：

```text
metrics
dimensions
verdict
regression
```

其中 `dimensions` 会记录 retrieval、evidence、report 三个维度。

## 3. 新增了哪些 RAG 指标

核心指标包括：

```text
retrieval_recall
retrieved_count
candidate_count
evidence_count
source_count
source_diversity_ratio
average_retrieval_score
max_retrieval_score
min_retrieval_score
reranker_applied
source_diversity_enabled
```

这些指标来自：

```text
sources/retrieval_diagnostics.json
workflow state
report artifact
evidence artifact
```

## 4. retrieval diagnostics 和 eval 的关系

`retrieval_diagnostics.json` 是过程记录。

`eval_result.json` 是质量判断。

可以这样理解：

```text
diagnostics 解释发生了什么
eval metrics 判断做得怎么样
```

例如 diagnostics 记录 top-k 结果和分数，eval 会进一步计算：

```text
average_retrieval_score
source_diversity_ratio
retrieved_count
```

## 5. verdict 怎么判断

当前规则是工程 MVP 版本：

```text
没有检索结果 -> needs_evidence
引用或 claim 支持率太低 -> fail
报告不完整 -> incomplete
其他情况 -> pass
```

后续可以替换为更复杂的 eval rubric 或 LLM judge。

## 6. 面试怎么说

可以这样回答：

> 我把 RAG 的评测从“最终报告是否生成”扩展到了 retrieval、evidence 和 report 三个维度。retrieval diagnostics 记录过程，eval metrics 基于 diagnostics 计算 retrieved_count、average score、source diversity、reranker 是否启用等指标。这样我们能定位质量问题到底来自召回、排序、证据构建还是写作阶段，而不是只看最终 markdown。

这个回答体现：

- 你知道 RAG 需要分阶段评估。
- 你理解 diagnostics 和 metrics 的区别。
- 你能把评测设计和工程可观察性联系起来。
