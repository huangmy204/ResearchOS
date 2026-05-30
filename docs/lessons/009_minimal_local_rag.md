# 第 009 课：最小本地 RAG

## 1. RAG 的核心链路

RAG 是 Retrieval-Augmented Generation。

核心不是“直接让模型回答”，而是：

```text
用户问题
  -> 检索相关资料
  -> 抽取 evidence
  -> 基于 evidence 写报告
```

当前实现的是最小本地 RAG：

```text
query
  -> documents
  -> chunk
  -> keyword scoring
  -> top evidence
  -> report artifacts
```

## 2. 为什么先不用向量库

向量库不是 RAG 的第一步。

学习顺序应该是：

1. 先理解资料如何进入系统。
2. 再理解文本如何切 chunk。
3. 再理解 query 如何找到相关 chunk。
4. 再理解 evidence 如何进入报告。
5. 最后再把关键词检索替换成 embedding + vector DB。

当前代码先完成前四步。

## 3. 新增输入字段

创建 run 时可以传：

```json
{
  "query": "legal research citation risk",
  "documents": [
    {
      "title": "Legal AI memo",
      "text": "AI agents can reduce legal research time..."
    }
  ]
}
```

`documents` 是本地文本资料。

## 4. 检索器做了什么

相关文件：

```text
src/researchos/retrieval/local_text.py
```

它做三件事：

1. 把文档按段落和长度切成 chunk。
2. 把 query 和 chunk 都 tokenize。
3. 按关键词重合度打分，选出 top chunk。

这是关键词检索，不是向量检索。

## 5. Workflow 如何使用检索结果

相关文件：

```text
src/researchos/runtime/workflow.py
```

如果 run 带 documents：

```text
retrieve_local_text(...)
  -> Source(source_type="file")
  -> Evidence(text=top_chunk.text)
  -> Claim(...)
  -> CitationVerification(...)
  -> report.md
```

如果 run 不带 documents：

```text
继续使用 synthetic MVP fallback
```

这样新功能不会破坏旧行为。

## 6. 新增 artifact

本地 RAG 会额外生成：

```text
sources/parsed/retrieval_results.json
```

它记录：

- 选中了哪个文档。
- 选中的 chunk 文本。
- 检索分数。

这个文件适合调试 retrieval 是否选对了证据。

## 7. 当前局限

当前还不是完整生产级 RAG。

局限：

- 只支持请求体里的本地文本。
- 只用关键词重合度。
- 没有 embedding。
- 没有 vector DB。
- 没有 LLM writer。

但它已经具备 RAG 的核心形状：先检索证据，再基于证据生成报告。

## 8. 面试怎么讲

可以这样说：

> 我先实现了一个最小本地 RAG，不直接上向量数据库。用户创建 run 时可以带 documents，系统会对文档切 chunk，根据 query 做关键词打分，选择最相关片段作为 evidence，再生成 source、claim、citation verification 和 report artifacts。这样先把 RAG 的数据流跑通，后续可以把关键词检索替换成 embedding 检索和向量数据库。
