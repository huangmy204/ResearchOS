# 038 本地语料接入

## 这一步在主线里的位置

ResearchOS 的主线是检索系统，不是单纯聊天应用。

检索系统至少要有三层：

```text
数据接入 -> 检索与排序 -> 带证据生成
```

之前我们主要在做第二层和第三层：chunk、retriever、multi-query、reranker、quality gate、report writer。

这一步开始补第一层：让系统能从本地语料目录读取 `.md/.txt` 文件，并把它们变成一次 research run 的 documents。

## 主要代码

```text
src/researchos/ingestion/local_corpus.py
```

负责读取本地语料：

- 支持 `.md` 和 `.txt`
- Markdown 文件优先用一级标题作为 title
- 生成 `ResearchDocument`
- 用 `corpus://relative/path` 标记来源
- 拒绝路径穿越，例如 `../secret.txt`

```text
src/researchos/api/routes_runs.py
```

负责在创建 run 时判断是否加载 corpus：

```json
{
  "query": "legal citation risk",
  "options": {
    "include_corpus": true
  }
}
```

也可以只加载部分文件：

```json
{
  "query": "legal citation risk",
  "options": {
    "corpus_paths": ["legal/citation.md"]
  }
}
```

```text
inputs/corpus_manifest.json
```

记录本次 run 实际加载了哪些 corpus 文件。

## 为什么先做本地语料

专业数据库接入最终会很复杂，例如 PubMed、Semantic Scholar、SEC EDGAR、企业内部文档库。

但它们进入系统后的结构应该一致：

```text
外部来源 -> 清洗 -> ResearchDocument -> chunk -> retrieval
```

所以我们先做本地 corpus，是为了验证最小的数据接入接口。后续接专业数据库时，不需要重写 RAG workflow，只需要新增 connector。

## 和专业数据库的关系

本地 corpus loader 是最小 connector。

后续可以扩展成：

```text
src/researchos/ingestion/
  local_corpus.py
  semantic_scholar.py
  pubmed.py
  sec_edgar.py
```

这些 connector 都输出同一种结构：

```text
ResearchDocument(title, text, url)
```

上层检索逻辑不关心文档来自哪里，只关心它能不能被检索、能不能提供证据。

## 面试表达

可以这样讲：

“为了让系统从 demo 变成真正的检索系统，我把数据接入从 run 请求里拆出来，新增了本地 corpus ingestion。用户可以把 Markdown 或 TXT 放到 corpus 目录，创建 run 时通过 `include_corpus=true` 加载。系统会记录 corpus manifest，保证本次回答用到了哪些输入文件是可追踪的。这个设计后续可以扩展到 PubMed、Semantic Scholar 或企业内部知识库，因为它们最终都会被统一成 ResearchDocument，再进入同一套 RAG workflow。”

## 当前限制

当前还没有做：

- PDF 解析
- Word 文档解析
- HTML 清洗
- 增量索引
- 向量库持久化
- 外部数据库 connector

这些是后续 ingestion pipeline 的扩展点。
