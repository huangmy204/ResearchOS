# 039 Corpus API 与当前系统主线

## 现在系统到底分几层

当前 ResearchOS 可以按三层理解：

```text
1. 数据接入层 ingestion
   本地 corpus 文件 -> ResearchDocument

2. 检索层 retrieval
   query planning -> multi-query retrieval -> rerank -> quality gate

3. 研究运行层 workflow
   planning -> retrieval -> evidence extraction -> verification -> report
```

你现在容易混乱，是因为我们刚从第 2 层切到了第 1 层。它们不是两条线，而是一条线的前后关系。

## 新增的 Corpus API

```text
GET /v1/corpus
```

作用：列出系统当前能看到的本地语料文件。

它不会启动 research run，也不会生成报告，只是帮你确认：

- corpus 根目录在哪里
- 有哪些 `.md` / `.txt` 文件
- 每个文件的 title、path、size、suffix 是什么

## 和创建 run 的关系

查看 corpus：

```text
GET /v1/corpus
```

基于 corpus 创建一次研究：

```text
POST /v1/research-runs
```

请求体里加：

```json
{
  "query": "legal citation risk",
  "options": {
    "include_corpus": true
  }
}
```

系统会做：

```text
读取 corpus 文件
-> 合并到 run.documents
-> workflow 开始检索
-> 生成 evidence / report / eval
```

## 为什么要有这个 API

因为真实检索系统里，用户需要先知道“系统能检索什么”。

如果没有 corpus API，用户只能直接启动 run，然后猜测系统有没有读到文件。这样不利于调试，也不利于面试表达。

有了 corpus API 后，链路更清楚：

```text
先看资料库 -> 再创建研究任务 -> 再看证据和报告
```

## 面试表达

可以这样讲：

“我把数据接入和研究运行解耦了。`GET /v1/corpus` 用来查看当前本地知识库有哪些文件，`POST /v1/research-runs` 才是启动一次研究。当请求里设置 `include_corpus=true` 时，系统把 corpus 文件加载成统一的 `ResearchDocument`，再进入同一套 RAG workflow。这个设计让后续接 PubMed、Semantic Scholar 或企业知识库时，只需要新增 connector，而不需要改 retrieval 和 workflow 主链路。”
