# 第 029 课：RAG chunk 切分参数与 overlap

## 1. 为什么 chunk 切分很重要

RAG 不是直接把整篇文档丢给模型。

通常流程是：

```text
长文档 -> 切成 chunks -> 检索 top-k chunks -> 组织证据 -> 生成回答
```

chunk 切得不好，后面的检索、证据抽取、引用校验都会受影响。

## 2. chunk 太大和太小的问题

chunk 太大：

- 一个 chunk 里混入太多无关内容。
- 检索分数不够精确。
- 传给 LLM 时浪费上下文窗口。

chunk 太小：

- 单个 chunk 缺少上下文。
- 句子之间的因果关系可能被切断。
- 引用校验时 evidence 可能不完整。

所以 chunk size 是召回质量和上下文完整性的折中。

## 3. overlap 是什么

overlap 指相邻 chunk 之间保留一小段重复文本。

例如：

```text
chunk 1: ... citation hallucination is a legal risk
chunk 2: legal risk when reports cite unsupported sources ...
```

这样即使关键含义跨越边界，也不容易在切分时丢掉。

但 overlap 也不能太大。太大会让重复文本变多，检索结果看起来很多，实际信息增量很少。

## 4. 当前项目怎么配置

新增两个环境变量：

```env
RESEARCHOS_RETRIEVAL_CHUNK_CHARS=600
RESEARCHOS_RETRIEVAL_CHUNK_OVERLAP_CHARS=0
```

对应代码：

```text
Settings.retrieval_chunk_chars
Settings.retrieval_chunk_overlap_chars
```

服务组装时传给：

```text
build_retriever(...)
```

然后 keyword 和 BM25 retriever 都会使用同一套 chunk 参数。

## 5. 为什么 keyword 和 BM25 共用 chunk 参数

chunking 是检索前的数据预处理。

keyword 和 BM25 是排序策略。

它们应该共享同一套切分输入，否则我们很难比较：

```text
到底是切分策略影响结果，还是检索算法影响结果？
```

所以当前设计是：

```text
chunking config -> retriever -> ranking strategy
```

## 6. 面试怎么说

可以这样回答：

> RAG 的质量不只取决于模型，也取决于文档如何切分。我把 chunk size 和 overlap 做成配置项，并让 keyword 与 BM25 共用同一套切分参数。chunk size 控制单个证据片段的上下文范围，overlap 用来降低关键信息跨 chunk 边界时被切断的风险。这样后续比较 keyword、BM25、embedding 和 reranker 时，可以把切分策略和排序策略分开分析。

这个回答体现：

- 你理解 RAG 的输入质量会影响最终答案。
- 你知道 chunk size 和 overlap 的取舍。
- 你能把“切分策略”和“检索排序策略”分开讲。
