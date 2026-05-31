# 第 032 课：RAG reranker、候选召回与二次排序

## 1. retriever 和 reranker 为什么要分开

真实 RAG 通常不是一步检索结束。

常见流程是：

```text
retriever 召回候选 chunks -> reranker 二次排序 -> 取最终 top-k 作为证据
```

retriever 关注“召回”：尽量不要漏掉可能相关的内容。

reranker 关注“排序”：在候选里更精细地判断哪些最适合进入证据链。

## 2. 本课新增了什么

新增：

```text
Reranker
NoopReranker
TermOverlapReranker
```

配置项：

```env
RESEARCHOS_RETRIEVAL_TOP_K=3
RESEARCHOS_RETRIEVAL_CANDIDATE_LIMIT=6
RESEARCHOS_RETRIEVAL_RERANKER=none
```

当启用：

```env
RESEARCHOS_RETRIEVAL_RERANKER=term_overlap
```

流程变成：

```text
先召回 candidate_limit 个候选
再 rerank 成最终 top_k 个证据 chunk
```

## 3. 为什么默认是 NoopReranker

默认配置：

```text
RESEARCHOS_RETRIEVAL_RERANKER=none
```

这样不会改变之前 keyword、BM25、embedding 的默认行为。

这是一种安全演进方式：

```text
先加抽象和诊断能力，再逐步启用更复杂排序模型。
```

## 4. 当前 reranker 是最终方案吗

不是。

当前 `TermOverlapReranker` 是本地 deterministic reranker，适合学习和测试。

未来可以替换为：

- cross-encoder reranker
- embedding reranker
- LLM reranker
- 云厂商 rerank API

由于 workflow 依赖的是 `Reranker` 抽象，后续替换实现不需要重写 run lifecycle。

## 5. 面试怎么说

可以这样回答：

> 我把 RAG 检索拆成 retriever 和 reranker 两层。retriever 先用 keyword、BM25 或 embedding 召回候选 chunks，reranker 再对候选做二次排序，最后取 top-k 进入 evidence graph。这样做的好处是召回和排序职责分离，后续可以把本地 deterministic reranker 替换成 cross-encoder、LLM reranker 或云端 rerank API，而 workflow 和 artifact 结构不用重写。

这个回答体现：

- 你知道 RAG 不只是一次 top-k 检索。
- 你理解召回和排序的职责差异。
- 你能说明为什么要先抽象接口，再接复杂模型。
