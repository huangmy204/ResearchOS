# 第 028 课：RAG 的 top-k 多证据检索

## 1. 这一步是不是开始做完整 RAG

是，准确说是开始做完整 RAG 的第一层地基。

完整 RAG 通常包含：

```text
文档切分 -> 检索 top-k -> 可选 rerank -> 证据抽取 -> 引用校验 -> 生成报告
```

本课完成的是：

```text
检索 top-k -> 多 Source -> 多 Evidence -> 多 Claim -> 多 Verification -> 多证据报告
```

还没有做 embedding、向量库、reranker，这些是后续层。

## 2. 为什么不能只取 top 1

只取一个 chunk 的问题：

- 证据覆盖面太窄。
- 报告容易被单个片段误导。
- 后续没法做 source diversity。
- 引用校验只能验证一个 claim-evidence 对。

top-k 检索的目标是先召回多个可能相关的片段，让后面的 evidence graph 和 writer 有更多材料。

## 3. 当前代码怎么改

状态对象：

```text
WorkflowState.retrieved_chunks
WorkflowState.sources
WorkflowState.evidence_items
WorkflowState.claims
WorkflowState.verifications
```

同时保留旧字段：

```text
retrieved_chunk
source
evidence
claim
verification
```

保留旧字段是为了兼容已有节点和测试。学习阶段可以把它们理解为“主证据”，列表字段是“全部证据”。

## 4. top-k 在哪里发生

位置：

```text
RetrievalNode
```

现在调用：

```text
retrieve(..., limit=3)
```

检索器返回最多 3 个相关 chunk，然后 workflow 把它们转换为：

```text
RetrievedChunk -> Source -> Evidence -> Claim -> CitationVerification
```

## 5. Evidence Graph 有什么变化

以前是：

```text
1 source -> 1 evidence -> 1 claim
```

现在是：

```text
source_1 -> evidence_1 -> claim_1
source_2 -> evidence_2 -> claim_2
source_3 -> evidence_3 -> claim_3
```

所以如果 top-k 返回 3 个 chunk，graph 会有：

```text
9 个节点：3 source + 3 evidence + 3 claim
6 条边：3 derived_from + 3 supported_by
```

## 6. 面试怎么说

可以这样回答：

> 早期 MVP 只使用 top-1 chunk，是为了先跑通端到端链路。但真实 RAG 不能只依赖一个片段，所以我把 workflow state 从单证据扩展成多证据列表：retrieved_chunks、sources、evidence_items、claims 和 verifications。检索节点现在返回 top-k，后续节点会为每个 chunk 构建 source、evidence、claim 和 citation verification，最后报告和 evidence graph 都能展示多个证据片段。这样后续接 embedding、reranker 和 source diversity 时，数据结构已经准备好了。

这个回答体现：

- 你知道 top-k 是 RAG 的基础。
- 你理解单证据 MVP 到多证据 RAG 的演进。
- 你能说明 retrieval、evidence graph、citation verification 和 report 之间的关系。
