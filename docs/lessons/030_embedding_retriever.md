# 第 030 课：Embedding Retriever 与向量检索

## 1. 这一步做了什么

新增：

```text
EmbeddingRetriever
```

它支持：

```env
RESEARCHOS_RETRIEVAL_STRATEGY=embedding
```

当前版本使用本地 deterministic embedding，不调用外部模型。

## 2. 什么是 embedding

embedding 是把文本变成数字向量。

可以把它理解成：

```text
文本 -> [0.12, -0.03, 0.88, ...]
```

向量检索的基本流程是：

```text
query -> query vector
chunk -> chunk vector
比较 query vector 和 chunk vector 的相似度
返回最相似的 top-k chunks
```

## 3. cosine similarity 是什么

cosine similarity 用来比较两个向量方向是否接近。

在 RAG 里：

```text
query 向量和 chunk 向量越接近，说明 chunk 越可能相关
```

它关注方向，不直接关注向量长度。

这比简单关键词匹配更接近语义检索的思路。

## 4. 为什么先做 deterministic embedding

真实 embedding 通常需要调用外部 API，比如阿里云、OpenAI 或其他模型服务。

但我们现在先不接 API，原因是：

- 先把工程结构跑通。
- 测试结果必须稳定。
- 不依赖网络和 API key。
- 你可以先理解向量检索逻辑。

当前 `DeterministicHashEmbeddingModel` 会把 token 稳定映射到固定维度的向量里。

它不是高质量语义模型，但适合做本地教学和测试。

## 5. 和 keyword、BM25 的对比

keyword：

```text
看 query 和 chunk 有多少词重合。
```

优点是简单直观，缺点是不理解词频和语义。

BM25：

```text
考虑词频、逆文档频率和长度归一化。
```

比 keyword 更像传统搜索引擎，但仍主要依赖词面匹配。

embedding：

```text
把 query 和 chunk 都变成向量，再按向量相似度排序。
```

真实 embedding 可以捕捉同义表达和语义相近关系。

当前 deterministic embedding 只是工程占位，后续可以替换成真实 embedding client。

## 6. 面试怎么说

可以这样回答：

> 我把检索层设计成可插拔策略，目前支持 keyword、BM25 和 embedding。embedding retriever 会把 query 和 chunk 转成向量，然后用 cosine similarity 做 top-k 排序。为了保证本地测试稳定，我先实现了 deterministic hash embedding，它不是最终语义模型，但能跑通向量检索的工程结构。后续接真实 embedding API 时，只需要替换 EmbeddingModel 实现，retriever、workflow、artifact 和 evidence bundle 都不用重写。

这个回答体现：

- 你知道向量检索的核心流程。
- 你理解 mock/deterministic 实现和真实模型的区别。
- 你能解释为什么先抽象接口，再接外部 API。
