# 第 031 课：Retrieval Diagnostics 与检索可观察性

## 1. 为什么需要 retrieval diagnostics

RAG 不能只看最终报告。

如果报告质量不好，我们要能回答：

```text
用了哪种检索策略？
chunk size 是多少？
overlap 是多少？
top-k 返回了哪些 chunk？
每个 chunk 的分数是多少？
```

这些信息就是 retrieval diagnostics。

## 2. 本课新增了什么 artifact

新增文件：

```text
sources/retrieval_diagnostics.json
```

它会在 retrieval 节点执行后写入。

内容包括：

```text
strategy
score_type
limit
document_count
retrieved_count
chunking
results
```

## 3. diagnostics 和 evidence 的区别

`evidence/*.json` 关注最终进入证据链的内容。

`sources/retrieval_diagnostics.json` 关注检索过程本身。

可以这样区分：

```text
retrieval diagnostics: 为什么这些 chunk 被选中
evidence bundle: 这些 chunk 如何变成证据、claim 和 citation
```

## 4. 三种检索策略怎么对比

keyword：

```text
strategy = keyword
score_type = term_overlap
```

适合做 baseline，容易解释。

BM25：

```text
strategy = bm25
score_type = bm25
```

更接近传统搜索排序，考虑词频、逆文档频率和长度归一化。

embedding：

```text
strategy = embedding
score_type = cosine_similarity
```

真实 embedding 场景下更适合语义相似度检索。当前项目先用 deterministic embedding 跑通结构。

## 5. 面试怎么说

可以这样回答：

> 我给 retrieval 节点增加了 diagnostics artifact。每次 run 都会记录当前检索策略、score 类型、chunk 参数、top-k 返回结果和分数。这样我们不只保存最终 evidence，还能回看检索阶段为什么选中这些 chunk。这个设计对 RAG 调试很重要，因为很多回答质量问题其实来自召回阶段，而不是 writer 模型本身。

这个回答体现：

- 你理解 RAG 的错误可能来自检索阶段。
- 你知道系统需要可观察性，而不是只看最终答案。
- 你能比较 keyword、BM25、embedding 的分数含义。
