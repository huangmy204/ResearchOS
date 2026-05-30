# 第 012 课：Retriever 抽象与 Chunk 策略

## 1. 为什么抽象 `Retriever`

当前 workflow 不应该关心底层到底用哪种检索算法。

所以我们拆出：

```text
Retriever
  -> LocalKeywordRetriever
```

`Retriever` 定义统一接口：

```python
retrieve(query, documents, limit=3) -> list[RetrievedChunk]
```

workflow 只调用这个接口。

好处：

- 当前可以用关键词检索。
- 后续可以换 BM25。
- 再后续可以换 embedding + vector DB。
- workflow 不需要大改。

## 2. 当前 `RetrievedChunk` 表达什么

一个检索结果包含：

```text
document_index
title
text
score
url
```

这些字段回答：

- 来自哪个文档。
- 文档标题是什么。
- 命中的文本片段是什么。
- 和 query 的相关分数是多少。
- 原始 URL 是什么。

## 3. Chunk 为什么重要

RAG 不能总是把整篇文档塞进去。

原因：

- 文档可能很长。
- 模型上下文有限。
- 整篇文档会稀释相关信息。
- 检索需要更小的匹配单位。

所以要先把文档切成 chunk。

## 4. 几种 chunk 策略对比

### 固定长度切分

例子：

```text
每 500 个字符切一块
```

优点：

- 实现简单。
- chunk 大小稳定。

缺点：

- 可能从句子中间切断。
- 语义完整性差。

适合：

- 快速原型。
- 对文本结构不敏感的场景。

### 按段落切分

例子：

```text
按空行分段
```

优点：

- 保留自然段语义。
- 对报告、文章、README 比较友好。

缺点：

- 有的段落很长。
- 如果原文没有空行，效果差。

适合：

- Markdown。
- 文档。
- 简单网页正文。

### 按句子边界切分

例子：

```text
段落太长时，再按句号、问号、感叹号切
```

优点：

- 比固定长度更保留语义。
- 比纯段落切分更能控制大小。

缺点：

- 句子识别在多语言环境里会复杂。
- 法律、论文里的长句可能仍然很长。

当前项目选择：

```text
先按段落切；段落太长，再按句子边界切。
```

原因：

- 实现轻量。
- 不引入额外依赖。
- 对 MVP 文本资料已经足够。

## 5. 几种检索技术对比

### 关键词重合

当前实现：

```text
query terms 和 chunk terms 计算重合度
```

优点：

- 无依赖。
- 结果容易解释。
- 测试稳定。
- 适合教学和 MVP。

缺点：

- 不理解同义词。
- 不理解语义相似。
- 对措辞变化敏感。

为什么当前选它：

> 我们现在优先验证 RAG 数据流，不优先追求检索效果上限。

### BM25

BM25 是更成熟的关键词检索算法。

优点：

- 比简单关键词重合更可靠。
- 会考虑词频和文档长度。
- 不需要 embedding。

缺点：

- 仍然不是真正语义检索。
- 需要引入依赖或自己实现。

适合下一步：

```text
LocalKeywordRetriever -> BM25Retriever
```

### Embedding + Vector DB

流程：

```text
chunk -> embedding -> vector index -> similarity search
```

优点：

- 能捕捉语义相似。
- 适合大规模文档。
- 是现代 RAG 常见方案。

缺点：

- 需要 embedding 模型。
- 需要向量库或向量索引。
- 成本、延迟、评测复杂度更高。
- 可解释性比关键词弱一些。

适合后续：

```text
Qdrant / FAISS / pgvector
```

## 6. 当前为什么不直接上向量库

不是因为向量库不好，而是因为阶段不对。

现在更重要的是先跑通：

```text
document -> chunk -> retrieve -> evidence -> claim -> report -> eval
```

等这个链路稳定后，再替换检索算法。

这样面试里也更好讲：

> 我先用可解释的关键词检索完成 RAG 数据流，再通过 Retriever 抽象给 BM25 和向量检索留出扩展点。

## 7. 面试表达

可以这样说：

> 我没有一开始就把向量数据库接进去，而是先抽象了 Retriever 接口，并实现了 LocalKeywordRetriever。当前 chunk 策略是先按段落切，段落过长再按句子边界切，这样兼顾语义完整性和 chunk 大小控制。关键词检索虽然效果不如 embedding，但它无依赖、可解释、测试稳定，适合先验证 RAG 的数据流。后续可以在不改 workflow 的情况下替换成 BM25 或 embedding + vector DB。
